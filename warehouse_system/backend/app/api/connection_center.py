import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import ConnectionMessage
from app.api.auth import get_current_user
from app.connection_center.registry import registry
from app.connection_center.reliability import get_breaker, list_dead_letters, replay_dead_letter

router = APIRouter()


def _require_integration_role(current_user):
    if current_user.role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Manager/Admin only")


@router.get("/connectors")
async def list_connectors(current_user=Depends(get_current_user)):
    """Connection dashboard: config, breaker state and health per connector."""
    _require_integration_role(current_user)
    out = []
    for cfg in registry.list_connectors():
        adapter = registry.get_connector(cfg.connector_id)
        try:
            health = await adapter.health()
        except Exception as e:
            health = {"status": "unknown", "error": str(e)}
        out.append({
            "config": cfg.dict(),
            "breaker_state": get_breaker(cfg.connector_id).state,
            "health": health,
        })
    return out


@router.get("/messages/summary")
def message_summary(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Ledger rollup: counts by status/direction (data-quality + freshness view)."""
    _require_integration_role(current_user)
    rows = (
        db.query(ConnectionMessage.direction, ConnectionMessage.status, func.count())
        .group_by(ConnectionMessage.direction, ConnectionMessage.status)
        .all()
    )
    return [{"direction": d, "status": s, "count": c} for d, s, c in rows]


@router.get("/dead-letters")
def dead_letters(connector_id: str = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_integration_role(current_user)
    msgs = list_dead_letters(db, connector_id)
    return [{
        "id": m.id, "connector_id": m.connector_id, "direction": m.direction,
        "dedup_key": m.dedup_key, "attempts": m.attempts, "last_error": m.last_error,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in msgs]


@router.post("/dead-letters/{message_id}/replay")
def replay(message_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _require_integration_role(current_user)
    try:
        msg = replay_dead_letter(db, message_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "requeued", "id": msg.id, "dedup_key": msg.dedup_key}


@router.post("/connectors/{connector_id}/trip")
def trip_connector(connector_id: str, times: int = 3, current_user=Depends(get_current_user)):
    """Chaos helper: force the next `times` connector operations to fail."""
    _require_integration_role(current_user)
    adapter = registry.get_connector(connector_id)
    if not hasattr(adapter, "trip"):
        raise HTTPException(status_code=400, detail="Connector does not support trip()")
    adapter.trip(times)
    return {"status": "tripped", "connector_id": connector_id, "times": times}


@router.post("/test-push")
async def test_push(payload: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Send a payload through the full reliability path (dedup, retries, breaker, DLQ)."""
    _require_integration_role(current_user)
    import uuid as _uuid
    from app.connection_center.reliability import call_with_reliability
    adapter = registry.get_connector("wms_primary")
    key = payload.get("idempotency_key") or f"test-push:{_uuid.uuid4().hex[:8]}"
    msg = await call_with_reliability(
        db, "wms_primary", "OUTBOUND", key, payload,
        lambda: adapter.push(payload, key),
    )
    return {"dedup_key": key, "status": msg.status, "attempts": msg.attempts,
            "last_error": msg.last_error}
