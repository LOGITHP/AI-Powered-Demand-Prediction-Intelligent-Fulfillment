from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from ..connection_center.canonical_models import HeadOfficeInstruction
from ..planning.pipeline import PlanningPipeline
from ..db.database import get_db
from ..db.models import ConnectionMessage
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
            dedup_key=ledger_key, payload=payload.dict(), status="RECEIVED",
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

@router.post("/sync")
def trigger_sync(warehouse_id: str = "WH-001", db = Depends(get_db)):
    """
    Manually triggers a sync to the remote Head Office agent API.
    """
    success = sync_warehouse_status_to_head_office(db, warehouse_id)
    if success:
        return {"status": "success", "message": "Synced warehouse status to Head Office."}
    else:
        raise HTTPException(status_code=500, detail="Failed to sync with Head Office API. Check logs.")
