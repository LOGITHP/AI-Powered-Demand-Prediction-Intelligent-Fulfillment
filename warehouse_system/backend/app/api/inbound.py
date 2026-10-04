from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import (
    InboundShipment, InboundShipmentItem, Product, StorageLocation,
    InventoryRecord, InventoryMovement, OperationalEvent, Task,
    Notification, User, Worker, Issue
)
from app.api.auth import get_current_user
import uuid

router = APIRouter()

# ============================================================
# SCHEMAS
# ============================================================
class ShipmentItemCreate(BaseModel):
    product_id: int
    expected_quantity: int

class ShipmentCreate(BaseModel):
    supplier: str
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    expected_arrival: datetime
    priority: str = "NORMAL"
    items: List[ShipmentItemCreate]

class ArrivalRecord(BaseModel):
    actual_arrival: Optional[datetime] = None
    notes: Optional[str] = None

class ReceivingUpdate(BaseModel):
    item_id: int
    received_quantity: int
    damaged_quantity: int
    notes: Optional[str] = None

class ReceivingComplete(BaseModel):
    updates: List[ReceivingUpdate]

class InspectionUpdate(BaseModel):
    item_id: int
    inspection_status: str  # ACCEPTED, DAMAGED, REJECTED, PARTIAL
    damaged_quantity: Optional[int] = None
    rejected_quantity: Optional[int] = None
    notes: Optional[str] = None

class InspectionComplete(BaseModel):
    updates: List[InspectionUpdate]

class PutawayAssignment(BaseModel):
    item_id: int
    location_id: int
    quantity: int

class PutawayComplete(BaseModel):
    assignments: List[PutawayAssignment]

class IssueReport(BaseModel):
    issue_type: str
    description: str
    severity: str = "WARNING"

# ============================================================
# HELPERS
# ============================================================
WAREHOUSE_ID = settings.WAREHOUSE_ID

def emit_event(db, event_type, description, reference_id=None, details=None, operator_id=None):
    ev = OperationalEvent(
        warehouse_id=WAREHOUSE_ID,
        event_type=event_type,
        description=description,
        reference_id=reference_id,
        details=details or {},
        operator_id=operator_id
    )
    db.add(ev)

def notify_role(db, role, message, notif_type="INFO"):
    users = db.query(User).filter(User.role == role, User.is_active == True).all()
    for u in users:
        n = Notification(user_id=u.id, type=notif_type, message=message)
        db.add(n)

def notify_user(db, user_id, message, notif_type="INFO"):
    n = Notification(user_id=user_id, type=notif_type, message=message)
    db.add(n)

# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/shipments")
def list_shipments(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    q = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID)
    if status_filter:
        q = q.filter(InboundShipment.status == status_filter)
    shipments = q.order_by(InboundShipment.expected_arrival).all()
    result = []
    for s in shipments:
        total_items = sum(i.expected_quantity for i in s.items) if s.items else 0
        received_items = sum(i.received_quantity for i in s.items) if s.items else 0
        damaged_items = sum(i.damaged_quantity for i in s.items) if s.items else 0

        # compute delay risk
        delay_risk = "LOW"
        if s.status == "EXPECTED" and s.expected_arrival < datetime.now(timezone.utc):
            delay_risk = "HIGH"
        elif s.status in ["RECEIVING", "INSPECTION", "PUTAWAY"]:
            hours_in_stage = (datetime.now(timezone.utc) - (s.receiving_started_at or datetime.now(timezone.utc))).total_seconds() / 3600
            if hours_in_stage > 4:
                delay_risk = "HIGH"
            elif hours_in_stage > 2:
                delay_risk = "MEDIUM"

        # assigned workers
        workers = db.query(Worker).filter(Worker.assigned_zone.in_(["RECEIVING", "INSPECTION", "PUTAWAY"])).count()

        result.append({
            "id": s.id,
            "shipment_id": s.shipment_id,
            "supplier": s.supplier,
            "vehicle_number": s.vehicle_number,
            "driver_name": s.driver_name,
            "expected_arrival": s.expected_arrival.isoformat() if s.expected_arrival else None,
            "actual_arrival": s.actual_arrival.isoformat() if s.actual_arrival else None,
            "status": s.status,
            "priority": s.priority,
            "total_items": total_items,
            "received_items": received_items,
            "damaged_items": damaged_items,
            "delay_risk": delay_risk,
            "assigned_workers": workers,
            "receiving_started_at": s.receiving_started_at.isoformat() if s.receiving_started_at else None,
            "receiving_completed_at": s.receiving_completed_at.isoformat() if s.receiving_completed_at else None,
            "inspection_started_at": s.inspection_started_at.isoformat() if s.inspection_started_at else None,
            "inspection_completed_at": s.inspection_completed_at.isoformat() if s.inspection_completed_at else None,
            "putaway_started_at": s.putaway_started_at.isoformat() if s.putaway_started_at else None,
            "putaway_completed_at": s.putaway_completed_at.isoformat() if s.putaway_completed_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return result

@router.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    items = []
    for item in s.items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": prod.name if prod else "Unknown",
            "product_sku": prod.sku if prod else "N/A",
            "expected_quantity": item.expected_quantity,
            "received_quantity": item.received_quantity,
            "damaged_quantity": item.damaged_quantity,
            "accepted_quantity": item.accepted_quantity,
            "rejected_quantity": item.rejected_quantity,
            "inspection_status": item.inspection_status,
            "putaway_status": item.putaway_status,
            "inspection_notes": item.inspection_notes,
        })
    return {
        "shipment_id": s.shipment_id,
        "supplier": s.supplier,
        "vehicle_number": s.vehicle_number,
        "driver_name": s.driver_name,
        "expected_arrival": s.expected_arrival.isoformat() if s.expected_arrival else None,
        "actual_arrival": s.actual_arrival.isoformat() if s.actual_arrival else None,
        "status": s.status,
        "priority": s.priority,
        "notes": s.notes,
        "receiving_started_at": s.receiving_started_at.isoformat() if s.receiving_started_at else None,
        "receiving_completed_at": s.receiving_completed_at.isoformat() if s.receiving_completed_at else None,
        "inspection_started_at": s.inspection_started_at.isoformat() if s.inspection_started_at else None,
        "inspection_completed_at": s.inspection_completed_at.isoformat() if s.inspection_completed_at else None,
        "putaway_started_at": s.putaway_started_at.isoformat() if s.putaway_started_at else None,
        "putaway_completed_at": s.putaway_completed_at.isoformat() if s.putaway_completed_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "items": items,
    }

@router.post("/shipments")
def create_shipment(body: ShipmentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role not in ["MANAGER", "ADMIN", "INBOUND"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    sid = f"SHP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    s = InboundShipment(
        shipment_id=sid,
        warehouse_id=WAREHOUSE_ID,
        supplier=body.supplier,
        vehicle_number=body.vehicle_number,
        driver_name=body.driver_name,
        expected_arrival=body.expected_arrival,
        priority=body.priority,
        status="EXPECTED",
    )
    db.add(s)
    db.flush()
    total = 0
    for it in body.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        if not prod:
            prod = db.query(Product).first()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product {it.product_id} not found and no products exist")
            it.product_id = prod.id
        item = InboundShipmentItem(
            shipment_id=sid,
            product_id=it.product_id,
            expected_quantity=it.expected_quantity
        )
        db.add(item)
        total += it.expected_quantity
    s.total_items = total
    emit_event(db, "INBOUND_SHIPMENT_CREATED", f"Shipment {sid} created from {body.supplier}", sid, {"priority": body.priority}, current_user.id)
    notify_role(db, "INBOUND", f"New shipment {sid} expected from {body.supplier} on {body.expected_arrival.strftime('%d/%m %H:%M')}", "INFO")
    db.commit()
    return {"status": "created", "shipment_id": sid}

@router.post("/shipments/{shipment_id}/arrive")
def record_arrival(shipment_id: str, body: ArrivalRecord, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s.status not in ["EXPECTED", "DELAYED"]:
        raise HTTPException(status_code=400, detail=f"Cannot mark arrival from status: {s.status}")
    s.actual_arrival = body.actual_arrival or datetime.now(timezone.utc)
    s.status = "ARRIVED"
    s.notes = body.notes
    # check for delay
    if s.actual_arrival > s.expected_arrival:
        issue = Issue(
            warehouse_id=WAREHOUSE_ID,
            issue_type="SHIPMENT_DELAYED",
            severity="WARNING",
            description=f"Shipment {shipment_id} arrived late. Expected: {s.expected_arrival}, Actual: {s.actual_arrival}",
            reference_id=shipment_id,
            reference_type="SHIPMENT",
            reported_by=current_user.id
        )
        db.add(issue)
    emit_event(db, "INBOUND_ARRIVAL", f"Shipment {shipment_id} arrived from {s.supplier}", shipment_id, {"actual_arrival": s.actual_arrival.isoformat()}, current_user.id)
    notify_role(db, "INBOUND", f"Shipment {shipment_id} has arrived. Start receiving.", "INFO")
    notify_role(db, "MANAGER", f"Inbound shipment {shipment_id} from {s.supplier} has arrived.", "INFO")
    db.commit()
    return {"status": "ARRIVED", "shipment_id": shipment_id}

@router.post("/shipments/{shipment_id}/start-receiving")
def start_receiving(shipment_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s.status != "ARRIVED":
        raise HTTPException(status_code=400, detail=f"Shipment must be ARRIVED to start receiving. Current: {s.status}")
    s.status = "RECEIVING"
    s.receiving_started_at = datetime.now(timezone.utc)
    s.assigned_worker_id = current_user.id
    emit_event(db, "INBOUND_RECEIVING_STARTED", f"Receiving started for {shipment_id}", shipment_id, {}, current_user.id)
    db.commit()
    return {"status": "RECEIVING", "shipment_id": shipment_id}

@router.post("/shipments/{shipment_id}/complete-receiving")
def complete_receiving(shipment_id: str, body: ReceivingComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s.status != "RECEIVING":
        raise HTTPException(status_code=400, detail=f"Shipment must be in RECEIVING. Current: {s.status}")

    total_received = 0
    total_damaged = 0
    for upd in body.updates:
        item = db.query(InboundShipmentItem).filter(InboundShipmentItem.id == upd.item_id, InboundShipmentItem.shipment_id == shipment_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {upd.item_id} not found")
        if upd.received_quantity > item.expected_quantity:
            issue = Issue(
                warehouse_id=WAREHOUSE_ID, issue_type="EXCESS_RECEIVED", severity="WARNING",
                description=f"Item {item.id} in shipment {shipment_id}: received {upd.received_quantity} > expected {item.expected_quantity}",
                reference_id=shipment_id, reference_type="SHIPMENT", reported_by=current_user.id
            )
            db.add(issue)
        if upd.damaged_quantity > 0:
            issue = Issue(
                warehouse_id=WAREHOUSE_ID, issue_type="DAMAGED_GOODS", severity="WARNING",
                description=f"Shipment {shipment_id}: {upd.damaged_quantity} damaged units for item {item.id}",
                reference_id=shipment_id, reference_type="SHIPMENT", reported_by=current_user.id
            )
            db.add(issue)
        item.received_quantity = upd.received_quantity
        item.damaged_quantity = upd.damaged_quantity
        item.accepted_quantity = max(0, upd.received_quantity - upd.damaged_quantity)
        if upd.notes:
            item.inspection_notes = upd.notes
        total_received += upd.received_quantity
        total_damaged += upd.damaged_quantity

    s.received_items = total_received
    s.damaged_items = total_damaged
    s.receiving_completed_at = datetime.now(timezone.utc)
    s.status = "INSPECTION"
    s.inspection_started_at = datetime.now(timezone.utc)

    cycle_time = (s.receiving_completed_at - s.receiving_started_at).total_seconds() / 60.0
    emit_event(db, "INBOUND_RECEIVING_COMPLETED", f"Receiving completed for {shipment_id}. {total_received} units received, {total_damaged} damaged.",
               shipment_id, {"cycle_time_minutes": cycle_time, "received": total_received, "damaged": total_damaged}, current_user.id)
    emit_event(db, "INBOUND_INSPECTION_STARTED", f"Inspection started for {shipment_id}", shipment_id, {}, current_user.id)
    notify_role(db, "MANAGER", f"Shipment {shipment_id}: Receiving complete. {total_damaged} damaged items detected.", "WARNING" if total_damaged > 0 else "INFO")
    db.commit()
    return {"status": "INSPECTION", "received": total_received, "damaged": total_damaged, "cycle_time_minutes": round(cycle_time, 2)}

@router.post("/shipments/{shipment_id}/complete-inspection")
def complete_inspection(shipment_id: str, body: InspectionComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s.status != "INSPECTION":
        raise HTTPException(status_code=400, detail=f"Shipment must be in INSPECTION. Current: {s.status}")

    for upd in body.updates:
        item = db.query(InboundShipmentItem).filter(InboundShipmentItem.id == upd.item_id, InboundShipmentItem.shipment_id == shipment_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {upd.item_id} not found")
        item.inspection_status = upd.inspection_status
        if upd.damaged_quantity is not None:
            item.damaged_quantity = upd.damaged_quantity
        if upd.rejected_quantity is not None:
            item.rejected_quantity = upd.rejected_quantity
        item.accepted_quantity = max(0, item.received_quantity - item.damaged_quantity - item.rejected_quantity)
        if upd.notes:
            item.inspection_notes = upd.notes
        if upd.inspection_status == "REJECTED":
            issue = Issue(
                warehouse_id=WAREHOUSE_ID, issue_type="INSPECTION_FAILURE", severity="CRITICAL",
                description=f"Item {item.id} in shipment {shipment_id} failed inspection and was rejected.",
                reference_id=shipment_id, reference_type="SHIPMENT", reported_by=current_user.id
            )
            db.add(issue)

    s.inspection_completed_at = datetime.now(timezone.utc)
    s.status = "PUTAWAY"
    s.putaway_started_at = datetime.now(timezone.utc)

    cycle_time = (s.inspection_completed_at - s.inspection_started_at).total_seconds() / 60.0
    emit_event(db, "INBOUND_INSPECTION_COMPLETED", f"Inspection complete for {shipment_id}.", shipment_id, {"cycle_time_minutes": cycle_time}, current_user.id)
    emit_event(db, "INBOUND_PUTAWAY_STARTED", f"Putaway started for {shipment_id}", shipment_id, {}, current_user.id)
    db.commit()
    return {"status": "PUTAWAY", "cycle_time_minutes": round(cycle_time, 2)}

@router.post("/shipments/{shipment_id}/complete-putaway")
def complete_putaway(shipment_id: str, body: PutawayComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(InboundShipment).filter(InboundShipment.shipment_id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s.status != "PUTAWAY":
        raise HTTPException(status_code=400, detail=f"Shipment must be in PUTAWAY. Current: {s.status}")

    for assign in body.assignments:
        item = db.query(InboundShipmentItem).filter(InboundShipmentItem.id == assign.item_id, InboundShipmentItem.shipment_id == shipment_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {assign.item_id} not found")
        loc = db.query(StorageLocation).filter(StorageLocation.id == assign.location_id, StorageLocation.warehouse_id == WAREHOUSE_ID).first()
        if not loc:
            raise HTTPException(status_code=404, detail=f"Storage location {assign.location_id} not found")
        if loc.available_capacity < assign.quantity:
            issue = Issue(
                warehouse_id=WAREHOUSE_ID, issue_type="STORAGE_UNAVAILABLE", severity="CRITICAL",
                description=f"Zone {loc.zone} has insufficient capacity for {assign.quantity} units.",
                reference_id=shipment_id, reference_type="SHIPMENT", reported_by=current_user.id
            )
            db.add(issue)
            raise HTTPException(status_code=400, detail=f"Insufficient capacity at location {assign.location_id}")
        if assign.quantity > item.accepted_quantity:
            raise HTTPException(status_code=400, detail=f"Cannot putaway {assign.quantity} > accepted {item.accepted_quantity}")

        # Update inventory
        inv = db.query(InventoryRecord).filter(
            InventoryRecord.product_id == item.product_id,
            InventoryRecord.warehouse_id == WAREHOUSE_ID,
            InventoryRecord.location_id == assign.location_id
        ).first()
        if inv:
            inv.quantity += assign.quantity
        else:
            inv = InventoryRecord(
                warehouse_id=WAREHOUSE_ID,
                product_id=item.product_id,
                location_id=assign.location_id,
                quantity=assign.quantity
            )
            db.add(inv)

        # Record movement
        mv = InventoryMovement(
            warehouse_id=WAREHOUSE_ID,
            product_id=item.product_id,
            movement_type="INBOUND",
            quantity=assign.quantity,
            source=f"Supplier:{s.supplier}",
            destination=f"Zone:{loc.zone} Aisle:{loc.aisle} Rack:{loc.rack}",
            reference_id=shipment_id,
            operator_id=current_user.id
        )
        db.add(mv)

        # Update location occupancy
        loc.current_occupancy += assign.quantity
        item.putaway_location_id = assign.location_id
        item.putaway_status = "COMPLETED"

    s.putaway_completed_at = datetime.now(timezone.utc)
    s.status = "COMPLETED"
    s.completed_at = datetime.now(timezone.utc)

    putaway_cycle = (s.putaway_completed_at - s.putaway_started_at).total_seconds() / 60.0
    emit_event(db, "INBOUND_PUTAWAY_COMPLETED", f"Putaway complete for {shipment_id}.", shipment_id, {"cycle_time_minutes": putaway_cycle}, current_user.id)
    emit_event(db, "INBOUND_COMPLETED", f"Shipment {shipment_id} fully completed.", shipment_id, {}, current_user.id)
    notify_role(db, "MANAGER", f"Shipment {shipment_id} is now COMPLETED and inventory has been updated.", "INFO")
    db.commit()
    return {"status": "COMPLETED", "putaway_cycle_time_minutes": round(putaway_cycle, 2)}

@router.get("/shipments/{shipment_id}/items")
def get_shipment_items(shipment_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    items = db.query(InboundShipmentItem).filter(InboundShipmentItem.shipment_id == shipment_id).all()
    result = []
    for item in items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        result.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": prod.name if prod else "Unknown",
            "product_sku": prod.sku if prod else "N/A",
            "expected_quantity": item.expected_quantity,
            "received_quantity": item.received_quantity,
            "damaged_quantity": item.damaged_quantity,
            "accepted_quantity": item.accepted_quantity,
            "rejected_quantity": item.rejected_quantity,
            "inspection_status": item.inspection_status,
            "putaway_status": item.putaway_status,
            "inspection_notes": item.inspection_notes,
        })
    return result

@router.get("/locations")
def get_storage_locations(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    locs = db.query(StorageLocation).filter(StorageLocation.warehouse_id == WAREHOUSE_ID, StorageLocation.is_available == True).all()
    return [{"id": l.id, "zone": l.zone, "aisle": l.aisle, "rack": l.rack, "bin": l.bin,
             "capacity": l.capacity, "current_occupancy": l.current_occupancy,
             "available_capacity": l.capacity - l.current_occupancy} for l in locs]

@router.get("/products")
def get_products(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    prods = db.query(Product).filter(Product.warehouse_id == WAREHOUSE_ID).all()
    return [{"id": p.id, "sku": p.sku, "name": p.name, "category": p.category} for p in prods]

@router.post("/shipments/{shipment_id}/report-issue")
def report_issue(shipment_id: str, body: IssueReport, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    issue = Issue(
        warehouse_id=WAREHOUSE_ID,
        issue_type=body.issue_type,
        severity=body.severity,
        description=body.description,
        reference_id=shipment_id,
        reference_type="SHIPMENT",
        reported_by=current_user.id
    )
    db.add(issue)
    emit_event(db, f"INBOUND_ISSUE_{body.severity}", body.description, shipment_id, {"issue_type": body.issue_type}, current_user.id)
    notify_role(db, "MANAGER", f"Issue reported for shipment {shipment_id}: {body.description}", "WARNING" if body.severity != "CRITICAL" else "CRITICAL")
    db.commit()
    return {"status": "reported"}

@router.get("/kpis")
def get_inbound_kpis(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.created_at >= today_start).count()
    completed_today = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.status == "COMPLETED", InboundShipment.completed_at >= today_start).count()
    in_receiving = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.status == "RECEIVING").count()
    in_inspection = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.status == "INSPECTION").count()
    in_putaway = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.status == "PUTAWAY").count()
    delayed = db.query(InboundShipment).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.status == "EXPECTED", InboundShipment.expected_arrival < now).count()

    # Avg cycle times from events
    from app.db.models import OperationalEvent
    recv_events = db.query(OperationalEvent).filter(OperationalEvent.event_type == "INBOUND_RECEIVING_COMPLETED", OperationalEvent.timestamp >= today_start).all()
    avg_recv_ct = 0
    if recv_events:
        times = [e.details.get("cycle_time_minutes", 0) for e in recv_events if e.details]
        avg_recv_ct = round(sum(times) / len(times), 1) if times else 0

    insp_events = db.query(OperationalEvent).filter(OperationalEvent.event_type == "INBOUND_INSPECTION_COMPLETED", OperationalEvent.timestamp >= today_start).all()
    avg_insp_ct = 0
    if insp_events:
        times = [e.details.get("cycle_time_minutes", 0) for e in insp_events if e.details]
        avg_insp_ct = round(sum(times) / len(times), 1) if times else 0

    # Receiving throughput = units received today
    items_received = db.query(func.sum(InboundShipmentItem.received_quantity)).join(InboundShipment, InboundShipmentItem.shipment_id == InboundShipment.shipment_id).filter(InboundShipment.warehouse_id == WAREHOUSE_ID, InboundShipment.receiving_completed_at >= today_start).scalar() or 0

    workers_receiving = db.query(Worker).filter(Worker.assigned_zone == "RECEIVING", Worker.status == "ON_SHIFT").count()
    workers_inspection = db.query(Worker).filter(Worker.assigned_zone == "INSPECTION", Worker.status == "ON_SHIFT").count()
    workers_putaway = db.query(Worker).filter(Worker.assigned_zone == "PUTAWAY", Worker.status == "ON_SHIFT").count()

    return {
        "total_shipments_today": total_today,
        "completed_today": completed_today,
        "in_queue": in_receiving + in_inspection + in_putaway,
        "in_receiving": in_receiving,
        "in_inspection": in_inspection,
        "in_putaway": in_putaway,
        "delayed": delayed,
        "receiving_throughput": int(items_received),
        "avg_receiving_cycle_time_min": avg_recv_ct,
        "avg_inspection_cycle_time_min": avg_insp_ct,
        "workforce": {
            "receiving": {"assigned": workers_receiving, "required": max(3, in_receiving * 2)},
            "inspection": {"assigned": workers_inspection, "required": max(2, in_inspection * 2)},
            "putaway": {"assigned": workers_putaway, "required": max(3, in_putaway * 2)},
        }
    }
