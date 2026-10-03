"""
Action Engine (Phase 8): human approval -> execution.

Agents and monitors only PROPOSE (T2). The manager Approves / Modifies /
Rejects in the portal, and THIS module is the only path that mutates
operational state. Every execution is:
  - idempotent (idempotency_key; re-approving is a no-op)
  - audited (AgentAction.decided_by / executed_at / execution_result)
  - journaled (OutboxEvent so write-backs / downstream fan-out survive crashes)

Supported action types:
  REASSIGN_TASK        {task_id, new_worker_id|null, reason}
  REDISTRIBUTE_WORKERS {from_zone, to_zone, count}
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import AgentAction, Task, Worker, OutboxEvent
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)

TERMINAL_STATES = {"APPROVED", "MODIFIED", "REJECTED"}


class AlreadyExecuted(Exception):
    pass


def _outbox(db: Session, action: AgentAction, result_payload: dict):
    db.add(OutboxEvent(
        idempotency_key=f"{action.idempotency_key}:executed",
        event_type=action.action_type or "MANUAL",
        payload={"action_id": action.id, **result_payload},
        status="PENDING",
    ))


def _exec_reassign_task(db: Session, action: AgentAction, payload: dict) -> dict:
    task = db.query(Task).filter(Task.id == payload.get("task_id")).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {payload.get('task_id')} not found")

    old_worker_id = task.assigned_worker_id
    new_worker_id = payload.get("new_worker_id")

    if not new_worker_id:
        # Auto-pick the best eligible worker via the assignment engine's scoring
        from app.intelligence.assignment import eligible_workers, score_pair
        candidates = eligible_workers(db, action.warehouse_id)
        candidates = [w for w in candidates if w.worker_id != old_worker_id]
        if not candidates:
            raise HTTPException(status_code=409, detail="No eligible replacement worker on shift")
        now = datetime.utcnow()
        best = max(candidates, key=lambda w: score_pair(task, w, now)["total"])
        new_worker_id = best.worker_id

    worker = db.query(Worker).filter(Worker.worker_id == new_worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {new_worker_id} not found")

    task.assigned_worker_id = new_worker_id
    task.assigned_at = datetime.utcnow()
    if task.status in ("PLANNED", "PENDING"):
        task.status = "ASSIGNED"

    # retract/supersede the old assignment and notify the new owner
    if old_worker_id:
        old = db.query(Worker).filter(Worker.worker_id == old_worker_id).first()
        if old:
            create_notification(
                db, user_id=old.user_id, type="task.reassigned_away",
                message=f"Task #{task.id} ({task.process_type}) has been reassigned. Stop work on it.",
                priority="high", requires_ack=True, ack_minutes=5,
                dedup_key=f"task.reassigned_away:{task.id}",
                payload={"task_id": task.id, "new_worker_id": new_worker_id},
                correlation_id=action.idempotency_key,
            )
    create_notification(
        db, user_id=worker.user_id, type="task.reassigned_to",
        message=f"New task: {task.process_type} · {task.instructions or ''} · zone {task.zone or task.process_type}",
        priority="high", requires_ack=True, ack_minutes=5,
        dedup_key=f"task.reassigned_to:{task.id}:{new_worker_id}",
        payload={"task_id": task.id, "deadline": task.deadline.isoformat() if task.deadline else None},
        correlation_id=action.idempotency_key,
    )
    return {"task_id": task.id, "from": old_worker_id, "to": new_worker_id}


def _exec_redistribute_workers(db: Session, action: AgentAction, payload: dict) -> dict:
    from_zone = (payload.get("from_zone") or "").upper()
    to_zone = (payload.get("to_zone") or "").upper()
    count = int(payload.get("count") or 1)
    if not from_zone or not to_zone:
        raise HTTPException(status_code=400, detail="from_zone and to_zone are required")

    candidates = (
        db.query(Worker)
        .filter(
            Worker.warehouse_id == action.warehouse_id,
            Worker.assigned_zone == from_zone,
            Worker.status == "ON_SHIFT",
        )
        # Prefer moving the least experienced workers first (keep experts anchored)
        .order_by(Worker.experience_years.asc())
        .limit(count)
        .all()
    )
    if not candidates:
        raise HTTPException(status_code=409, detail=f"No on-shift workers in zone {from_zone}")

    moved = []
    for w in candidates:
        w.assigned_zone = to_zone
        moved.append(w.worker_id)
        create_notification(
            db, user_id=w.user_id, type="zone.changed",
            message=f"You have been reassigned to {to_zone} for this shift. Please proceed to the new zone.",
            priority="high", requires_ack=True, ack_minutes=10,
            dedup_key=f"zone.changed:{w.worker_id}:{to_zone}",
            payload={"from_zone": from_zone, "to_zone": to_zone},
            correlation_id=action.idempotency_key,
        )
    return {"from_zone": from_zone, "to_zone": to_zone, "moved_workers": moved}


ACTION_EXECUTORS = {
    "REASSIGN_TASK": _exec_reassign_task,
    "REDISTRIBUTE_WORKERS": _exec_redistribute_workers,
}


def decide_action(
    db: Session,
    action: AgentAction,
    decision: str,
    decided_by_user_id: Optional[int] = None,
    modified_payload: Optional[dict] = None,
) -> AgentAction:
    """
    Approve (optionally Modify) / Reject a pending agent action and execute it.

    APPROVED -> execute the stored payload.
    MODIFIED -> manager-supplied payload overrides the stored one, then execute.
    REJECTED -> no execution, audit only.
    Idempotent: a decided action with executed_at set is never executed twice.
    """
    decision = (decision or "").upper()
    if decision not in {"APPROVED", "MODIFIED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="decision must be APPROVED, MODIFIED or REJECTED")

    if action.manager_approval not in ("PENDING", "NOT_REQUIRED") and action.executed_at:
        # idempotent no-op: already executed
        return action

    action.manager_approval = decision
    action.decided_by = decided_by_user_id

    if decision == "REJECTED":
        action.execution_result = "Rejected by manager. No changes applied."
        db.commit()
        return action

    if decision == "MODIFIED":
        if not modified_payload:
            raise HTTPException(status_code=400, detail="MODIFIED requires a payload")
        action.action_payload = {**(action.action_payload or {}), **modified_payload}

    executor = ACTION_EXECUTORS.get(action.action_type or "MANUAL")
    if executor is None:
        # unknown/manual action: audit-only, nothing to execute
        action.execution_result = "Audit-only action; nothing to execute."
        action.executed_at = datetime.utcnow()
        db.commit()
        return action

    result = executor(db, action, action.action_payload or {})
    _outbox(db, action, result)
    action.execution_result = f"Executed: {result}"
    action.executed_at = datetime.utcnow()

    db.query(OutboxEvent).filter(
        OutboxEvent.idempotency_key == f"{action.idempotency_key}:executed"
    ).update({"status": "DELIVERED"})
    db.commit()
    logger.info(f"Action {action.id} ({action.action_type}) executed: {result}")
    return action
