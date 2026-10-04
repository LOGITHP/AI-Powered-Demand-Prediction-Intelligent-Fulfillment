from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import (
    OutboundOrder, OutboundOrderItem, Product, StorageLocation,
    InventoryRecord, InventoryMovement, OperationalEvent, Task,
    Notification, User, Worker, Issue
)
from app.api.auth import get_current_user
import uuid

router = APIRouter()

WAREHOUSE_ID = settings.WAREHOUSE_ID

# ============================================================
# SCHEMAS
# ============================================================
class OrderItemCreate(BaseModel):
    product_id: int
    required_quantity: int

class OrderCreate(BaseModel):
    customer: Optional[str] = None
    priority: str = "NORMAL"
    required_dispatch_time: datetime
    items: List[OrderItemCreate]

class PickingUpdate(BaseModel):
    item_id: int
    picked_quantity: int
    pick_location_id: Optional[int] = None
    notes: Optional[str] = None

class PickingComplete(BaseModel):
    updates: List[PickingUpdate]

class PackingUpdate(BaseModel):
    item_id: int
    packed_quantity: int
    notes: Optional[str] = None

class PackingComplete(BaseModel):
    updates: List[PackingUpdate]

class LoadingUpdate(BaseModel):
    item_id: int
    loaded_quantity: int

class LoadingComplete(BaseModel):
    updates: List[LoadingUpdate]
    vehicle_reference: Optional[str] = None

class IssueReport(BaseModel):
    issue_type: str
    description: str
    severity: str = "WARNING"

# ============================================================
# HELPERS
# ============================================================
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

# ============================================================
# ENDPOINTS
# ============================================================
@router.get("/orders")
def list_orders(status_filter: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID)
    if status_filter:
        q = q.filter(OutboundOrder.status == status_filter)
    orders = q.order_by(OutboundOrder.required_dispatch_time).all()

    result = []
    for o in orders:
        delay_risk = "LOW"
        time_to_dispatch = (o.required_dispatch_time - datetime.utcnow()).total_seconds() / 3600 if o.required_dispatch_time else 99
        if time_to_dispatch < 0:
            delay_risk = "CRITICAL"
        elif time_to_dispatch < 1:
            delay_risk = "HIGH"
        elif time_to_dispatch < 2:
            delay_risk = "MEDIUM"

        workers = db.query(Worker).filter(Worker.assigned_zone.in_(["PICKING", "PACKING", "LOADING"])).count()
        result.append({
            "id": o.id,
            "order_id": o.order_id,
            "customer": o.customer,
            "priority": o.priority,
            "status": o.status,
            "total_items": o.total_items,
            "picked_items": o.picked_items,
            "packed_items": o.packed_items,
            "loaded_items": o.loaded_items,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "release_time": o.release_time.isoformat() if o.release_time else None,
            "required_dispatch_time": o.required_dispatch_time.isoformat() if o.required_dispatch_time else None,
            "actual_dispatch_time": o.actual_dispatch_time.isoformat() if o.actual_dispatch_time else None,
            "picking_started_at": o.picking_started_at.isoformat() if o.picking_started_at else None,
            "picking_completed_at": o.picking_completed_at.isoformat() if o.picking_completed_at else None,
            "packing_started_at": o.packing_started_at.isoformat() if o.packing_started_at else None,
            "packing_completed_at": o.packing_completed_at.isoformat() if o.packing_completed_at else None,
            "loading_started_at": o.loading_started_at.isoformat() if o.loading_started_at else None,
            "loading_completed_at": o.loading_completed_at.isoformat() if o.loading_completed_at else None,
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            "delay_risk": delay_risk,
            "assigned_workers": workers,
            "hours_to_dispatch": round(max(0, time_to_dispatch), 1),
        })
    return result

@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    items = []
    for item in o.items:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        inv = db.query(InventoryRecord).filter(InventoryRecord.product_id == item.product_id, InventoryRecord.warehouse_id == WAREHOUSE_ID).first()
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": prod.name if prod else "Unknown",
            "product_sku": prod.sku if prod else "N/A",
            "required_quantity": item.required_quantity,
            "picked_quantity": item.picked_quantity,
            "packed_quantity": item.packed_quantity,
            "loaded_quantity": item.loaded_quantity,
            "status": item.status,
            "available_inventory": inv.quantity - inv.reserved_quantity if inv else 0,
        })
    return {
        "order_id": o.order_id, "customer": o.customer, "priority": o.priority, "status": o.status,
        "order_date": o.order_date.isoformat() if o.order_date else None,
        "release_time": o.release_time.isoformat() if o.release_time else None,
        "required_dispatch_time": o.required_dispatch_time.isoformat() if o.required_dispatch_time else None,
        "actual_dispatch_time": o.actual_dispatch_time.isoformat() if o.actual_dispatch_time else None,
        "picking_started_at": o.picking_started_at.isoformat() if o.picking_started_at else None,
        "picking_completed_at": o.picking_completed_at.isoformat() if o.picking_completed_at else None,
        "packing_started_at": o.packing_started_at.isoformat() if o.packing_started_at else None,
        "packing_completed_at": o.packing_completed_at.isoformat() if o.packing_completed_at else None,
        "loading_started_at": o.loading_started_at.isoformat() if o.loading_started_at else None,
        "loading_completed_at": o.loading_completed_at.isoformat() if o.loading_completed_at else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        "total_items": o.total_items, "picked_items": o.picked_items,
        "packed_items": o.packed_items, "loaded_items": o.loaded_items,
        "items": items,
    }

@router.post("/orders")
def create_order(body: OrderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role not in ["MANAGER", "ADMIN", "OUTBOUND"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    oid = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    o = OutboundOrder(
        order_id=oid,
        warehouse_id=WAREHOUSE_ID,
        customer=body.customer,
        priority=body.priority,
        required_dispatch_time=body.required_dispatch_time,
        status="CREATED"
    )
    db.add(o)
    db.flush()
    total = 0
    for it in body.items:
        prod = db.query(Product).filter(Product.id == it.product_id).first()
        if not prod:
            prod = db.query(Product).first()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product {it.product_id} not found and no products exist")
            it.product_id = prod.id
        item = OutboundOrderItem(order_id=oid, product_id=it.product_id, required_quantity=it.required_quantity)
        db.add(item)
        total += it.required_quantity
    o.total_items = total
    emit_event(db, "OUTBOUND_ORDER_CREATED", f"Order {oid} created for {body.customer}", oid, {"priority": body.priority}, current_user.id)
    db.commit()
    return {"status": "created", "order_id": oid}

@router.post("/orders/{order_id}/release")
def release_order(order_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Only managers can release orders")
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status != "CREATED":
        raise HTTPException(status_code=400, detail=f"Order must be CREATED to release. Current: {o.status}")

    # Reserve inventory
    for item in o.items:
        inv = db.query(InventoryRecord).filter(InventoryRecord.product_id == item.product_id, InventoryRecord.warehouse_id == WAREHOUSE_ID).first()
        available = (inv.quantity - inv.reserved_quantity) if inv else 0
        if available < item.required_quantity:
            issue = Issue(
                warehouse_id=WAREHOUSE_ID, issue_type="INVENTORY_SHORTAGE", severity="CRITICAL",
                description=f"Insufficient inventory for product {item.product_id} in order {order_id}. Required: {item.required_quantity}, Available: {available}",
                reference_id=order_id, reference_type="ORDER", reported_by=current_user.id
            )
            db.add(issue)
            item.status = "SHORTAGE"
            notify_role(db, "MANAGER", f"INVENTORY SHORTAGE for order {order_id}: Product {item.product_id} needs {item.required_quantity} but only {available} available.", "CRITICAL")
        else:
            if inv:
                inv.reserved_quantity += item.required_quantity

    o.status = "RELEASED"
    o.release_time = datetime.utcnow()
    emit_event(db, "OUTBOUND_ORDER_RELEASED", f"Order {order_id} released to picking queue.", order_id, {"priority": o.priority}, current_user.id)
    notify_role(db, "OUTBOUND", f"New order {order_id} released. Priority: {o.priority}. Please start picking.", "INFO")
    db.commit()
    return {"status": "RELEASED", "order_id": order_id}

@router.post("/orders/{order_id}/start-picking")
def start_picking(order_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status != "RELEASED":
        raise HTTPException(status_code=400, detail=f"Order must be RELEASED to start picking. Current: {o.status}")
    o.status = "PICKING"
    o.picking_started_at = datetime.utcnow()
    o.assigned_worker_id = current_user.id
    for item in o.items:
        if item.status == "PENDING":
            item.status = "PICKING"
    emit_event(db, "OUTBOUND_PICKING_STARTED", f"Picking started for order {order_id}", order_id, {}, current_user.id)
    db.commit()
    return {"status": "PICKING", "order_id": order_id}

@router.post("/orders/{order_id}/complete-picking")
def complete_picking(order_id: str, body: PickingComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status != "PICKING":
        raise HTTPException(status_code=400, detail=f"Order must be in PICKING. Current: {o.status}")

    total_picked = 0
    for upd in body.updates:
        item = db.query(OutboundOrderItem).filter(OutboundOrderItem.id == upd.item_id, OutboundOrderItem.order_id == order_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {upd.item_id} not found")
        if upd.picked_quantity > item.required_quantity:
            raise HTTPException(status_code=400, detail=f"Picked quantity {upd.picked_quantity} exceeds required {item.required_quantity}")
        item.picked_quantity = upd.picked_quantity
        item.status = "PICKED"
        if upd.pick_location_id:
            item.pick_location_id = upd.pick_location_id
        if upd.notes:
            item.notes = upd.notes
        total_picked += upd.picked_quantity

    o.picked_items = total_picked
    o.picking_completed_at = datetime.utcnow()
    o.status = "PACKING"
    o.packing_started_at = datetime.utcnow()

    cycle_time = (o.picking_completed_at - o.picking_started_at).total_seconds() / 60.0
    emit_event(db, "OUTBOUND_PICKING_COMPLETED", f"Picking complete for {order_id}. {total_picked} items picked.", order_id, {"cycle_time_minutes": cycle_time, "picked": total_picked}, current_user.id)
    emit_event(db, "OUTBOUND_PACKING_STARTED", f"Packing started for {order_id}", order_id, {}, current_user.id)
    db.commit()
    return {"status": "PACKING", "picked": total_picked, "cycle_time_minutes": round(cycle_time, 2)}

@router.post("/orders/{order_id}/complete-packing")
def complete_packing(order_id: str, body: PackingComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status != "PACKING":
        raise HTTPException(status_code=400, detail=f"Order must be in PACKING. Current: {o.status}")

    total_packed = 0
    for upd in body.updates:
        item = db.query(OutboundOrderItem).filter(OutboundOrderItem.id == upd.item_id, OutboundOrderItem.order_id == order_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {upd.item_id} not found")
        item.packed_quantity = upd.packed_quantity
        item.status = "PACKED"
        if upd.notes:
            item.notes = upd.notes
        total_packed += upd.packed_quantity

    o.packed_items = total_packed
    o.packing_completed_at = datetime.utcnow()
    o.status = "LOADING"
    o.loading_started_at = datetime.utcnow()

    cycle_time = (o.packing_completed_at - o.packing_started_at).total_seconds() / 60.0
    emit_event(db, "OUTBOUND_PACKING_COMPLETED", f"Packing complete for {order_id}.", order_id, {"cycle_time_minutes": cycle_time}, current_user.id)
    emit_event(db, "OUTBOUND_LOADING_STARTED", f"Loading started for {order_id}", order_id, {}, current_user.id)
    db.commit()
    return {"status": "LOADING", "packed": total_packed, "cycle_time_minutes": round(cycle_time, 2)}

@router.post("/orders/{order_id}/complete-loading")
def complete_loading(order_id: str, body: LoadingComplete, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    o = db.query(OutboundOrder).filter(OutboundOrder.order_id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status != "LOADING":
        raise HTTPException(status_code=400, detail=f"Order must be in LOADING. Current: {o.status}")

    total_loaded = 0
    for upd in body.updates:
        item = db.query(OutboundOrderItem).filter(OutboundOrderItem.id == upd.item_id, OutboundOrderItem.order_id == order_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {upd.item_id} not found")

        # Deduct inventory physically
        inv = db.query(InventoryRecord).filter(InventoryRecord.product_id == item.product_id, InventoryRecord.warehouse_id == WAREHOUSE_ID).first()
        if inv:
            inv.quantity = max(0, inv.quantity - upd.loaded_quantity)
            inv.reserved_quantity = max(0, inv.reserved_quantity - item.required_quantity)

        # Record outbound movement
        mv = InventoryMovement(
            warehouse_id=WAREHOUSE_ID,
            product_id=item.product_id,
            movement_type="OUTBOUND",
            quantity=upd.loaded_quantity,
            source=f"Warehouse:{WAREHOUSE_ID}",
            destination=f"Customer:{o.customer or 'N/A'}",
            reference_id=order_id,
            operator_id=current_user.id,
            notes=body.vehicle_reference
        )
        db.add(mv)

        item.loaded_quantity = upd.loaded_quantity
        item.status = "LOADED"
        total_loaded += upd.loaded_quantity

    o.loaded_items = total_loaded
    o.loading_completed_at = datetime.utcnow()
    o.actual_dispatch_time = datetime.utcnow()
    o.status = "COMPLETED"
    o.completed_at = datetime.utcnow()

    loading_cycle = (o.loading_completed_at - o.loading_started_at).total_seconds() / 60.0
    emit_event(db, "OUTBOUND_LOADING_COMPLETED", f"Loading complete for {order_id}.", order_id, {"cycle_time_minutes": loading_cycle}, current_user.id)
    emit_event(db, "OUTBOUND_DISPATCHED", f"Order {order_id} dispatched.", order_id, {"vehicle": body.vehicle_reference}, current_user.id)
    emit_event(db, "OUTBOUND_COMPLETED", f"Order {order_id} completed.", order_id, {}, current_user.id)
    notify_role(db, "MANAGER", f"Order {order_id} dispatched and COMPLETED. {total_loaded} items shipped.", "INFO")
    db.commit()
    return {"status": "COMPLETED", "loaded": total_loaded, "loading_cycle_time_minutes": round(loading_cycle, 2)}

@router.post("/orders/{order_id}/report-issue")
def report_issue(order_id: str, body: IssueReport, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    issue = Issue(
        warehouse_id=WAREHOUSE_ID,
        issue_type=body.issue_type,
        severity=body.severity,
        description=body.description,
        reference_id=order_id,
        reference_type="ORDER",
        reported_by=current_user.id
    )
    db.add(issue)
    emit_event(db, f"OUTBOUND_ISSUE_{body.severity}", body.description, order_id, {"issue_type": body.issue_type}, current_user.id)
    notify_role(db, "MANAGER", f"Issue for order {order_id}: {body.description}", "WARNING" if body.severity != "CRITICAL" else "CRITICAL")
    db.commit()
    return {"status": "reported"}

@router.get("/kpis")
def get_outbound_kpis(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_today = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.created_at >= today_start).count()
    completed_today = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "COMPLETED", OutboundOrder.completed_at >= today_start).count()
    in_picking = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "PICKING").count()
    in_packing = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "PACKING").count()
    in_loading = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "LOADING").count()
    released = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "RELEASED").count()
    delayed = db.query(OutboundOrder).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status.notin_(["COMPLETED", "CANCELLED"]), OutboundOrder.required_dispatch_time < now).count()

    # Cycle times from events
    pick_events = db.query(OperationalEvent).filter(OperationalEvent.event_type == "OUTBOUND_PICKING_COMPLETED", OperationalEvent.timestamp >= today_start).all()
    avg_pick_ct = 0
    if pick_events:
        times = [e.details.get("cycle_time_minutes", 0) for e in pick_events if e.details]
        avg_pick_ct = round(sum(times) / len(times), 1) if times else 0

    pack_events = db.query(OperationalEvent).filter(OperationalEvent.event_type == "OUTBOUND_PACKING_COMPLETED", OperationalEvent.timestamp >= today_start).all()
    avg_pack_ct = 0
    if pack_events:
        times = [e.details.get("cycle_time_minutes", 0) for e in pack_events if e.details]
        avg_pack_ct = round(sum(times) / len(times), 1) if times else 0

    items_dispatched = db.query(func.sum(OutboundOrder.loaded_items)).filter(OutboundOrder.warehouse_id == WAREHOUSE_ID, OutboundOrder.status == "COMPLETED", OutboundOrder.completed_at >= today_start).scalar() or 0

    workers_picking = db.query(Worker).filter(Worker.assigned_zone == "PICKING", Worker.status == "ON_SHIFT").count()
    workers_packing = db.query(Worker).filter(Worker.assigned_zone == "PACKING", Worker.status == "ON_SHIFT").count()
    workers_loading = db.query(Worker).filter(Worker.assigned_zone == "LOADING", Worker.status == "ON_SHIFT").count()

    return {
        "total_orders_today": total_today,
        "completed_today": completed_today,
        "in_queue": released + in_picking + in_packing + in_loading,
        "released": released,
        "in_picking": in_picking,
        "in_packing": in_packing,
        "in_loading": in_loading,
        "delayed": delayed,
        "items_dispatched": int(items_dispatched),
        "avg_picking_cycle_time_min": avg_pick_ct,
        "avg_packing_cycle_time_min": avg_pack_ct,
        "workforce": {
            "picking": {"assigned": workers_picking, "required": max(5, in_picking * 3)},
            "packing": {"assigned": workers_packing, "required": max(3, in_packing * 2)},
            "loading": {"assigned": workers_loading, "required": max(2, in_loading * 2)},
        }
    }

@router.get("/inventory")
def get_inventory_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    records = db.query(InventoryRecord).filter(InventoryRecord.warehouse_id == WAREHOUSE_ID).all()
    result = []
    for r in records:
        prod = db.query(Product).filter(Product.id == r.product_id).first()
        result.append({
            "product_id": r.product_id,
            "product_name": prod.name if prod else "Unknown",
            "sku": prod.sku if prod else "N/A",
            "quantity": r.quantity,
            "reserved_quantity": r.reserved_quantity,
            "available": r.quantity - r.reserved_quantity,
        })
    return result
