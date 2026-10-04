from app.core.config import settings
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from ..connection_center.canonical_models import HeadOfficeInstruction
from ..planning.pipeline import PlanningPipeline
from ..db.database import get_db
from ..db.models import ConnectionMessage
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_head_office_token(x_token: Optional[str] = Header(None)):
    """Simple API gateway auth check for the Head Office connection."""
    if x_token != "supersecret-headoffice-token":
        raise HTTPException(status_code=401, detail="Unauthorized API Token")

@router.get("/status")
def get_head_office_status():
    return {"status": "ONLINE", "connection": "STABLE"}

@router.get("/metrics")
def get_metrics(db = Depends(get_db)):
    from sqlalchemy import func
    from app.db.models import Order, InboundShipment, Worker, InventoryRecord
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "PENDING").count()
    active_workers = db.query(Worker).filter(Worker.status == "ON_SHIFT").count()
    total_inventory = db.query(func.sum(InventoryRecord.quantity)).scalar() or 0
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "active_workers": active_workers,
        "total_inventory": int(total_inventory),
    }

@router.post("/instructions", status_code=202)
def receive_instruction(payload: HeadOfficeInstruction, token: None = Depends(verify_head_office_token), db = Depends(get_db)):
    """
    API Gateway -> Connection Center: receives the canonical Head Office instruction
    (Order ID, SKU, Quantity, FC, Priority, SLA, Required Operation).
    Deduped by instruction_id, then queued into the planning pipeline.
    """
    logger.info(f"Received instruction from Head Office: {payload.instruction_id}")

    # Inbound dedup: replays of the same instruction_id never execute twice
    ledger_key = f"head_office:instruction:{payload.instruction_id}"
    msg = db.query(ConnectionMessage).filter(ConnectionMessage.dedup_key == ledger_key).first()
    if msg and msg.status == "PROCESSED":
        return {"status": "Duplicate", "message": "Instruction already processed.",
                "tracking_id": payload.instruction_id}
    if not msg:
        msg = ConnectionMessage(
            connector_id="head_office", direction="INBOUND",
            dedup_key=ledger_key, payload=json.loads(payload.json()), status="RECEIVED",
        )
        db.add(msg)
        db.commit()

    try:
        pipeline = PlanningPipeline(db)
        result = pipeline.execute(payload)
    except Exception as e:
        msg.status = "FAILED"
        msg.last_error = str(e)
        db.commit()
        logger.error(f"Pipeline failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    msg.status = "PROCESSED"
    db.commit()
    return {
        "status": "Accepted",
        "message": "Instruction validated and planned.",
        "tracking_id": payload.instruction_id,
        "details": result
    }

from ..services.head_office_sync import sync_warehouse_status_to_head_office
from app.db.models import OperationalEvent

@router.get("/operations")
def get_operations(db = Depends(get_db)):
    """Return recent operational events and completed tasks for head office reporting."""
    from sqlalchemy import desc
    events = db.query(OperationalEvent).order_by(desc(OperationalEvent.created_at)).limit(50).all()
    return [
        {
            "id": e.id,
            "type": e.event_type,
            "description": e.description,
            "timestamp": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]


@router.post("/sync")
def trigger_sync(warehouse_id: str = settings.WAREHOUSE_ID, db = Depends(get_db)):
    """
    Manually triggers a sync to the remote Head Office agent API.
    """
    success = sync_warehouse_status_to_head_office(db, warehouse_id)
    if success:
        return {"status": "success", "message": "Synced warehouse status to Head Office."}
    else:
        raise HTTPException(status_code=500, detail="Failed to sync with Head Office API. Check logs.")
