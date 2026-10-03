"""
Notification Service: lifecycle + escalation.

Principles (per the plan):
  - Every notification has a lifecycle and an owner; an unacknowledged
    assignment escalates automatically, never silently dropped.
  - Critical/assignment messages are template-driven; the LLM is never in
    the delivery path.
  - dedup_key makes replays safe - the same event never notifies twice.

Lifecycle: CREATED -> QUEUED -> SENT -> DELIVERED -> SEEN -> ACKNOWLEDGED.

Escalation ladder (ack-required, past ack_deadline):
  level 1: re-alert the worker (re-queue with an escalation notice)
  level 2: alert the zone supervisor / manager
  level 3: nobody can act -> auto-propose reassignment to the Action Engine
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Notification, User, Worker, Task, AgentAction

# minutes PAST the ack deadline at which each escalation level fires
ESCALATION_STEPS_MIN = {0: 2, 1: 8, 2: 10}


def create_notification(
    db: Session,
    user_id: int,
    type: str,
    message: str,
    priority: str = "medium",
    requires_ack: bool = False,
    ack_minutes: int = 5,
    dedup_key: Optional[str] = None,
    payload: Optional[dict] = None,
    correlation_id: Optional[str] = None,
    expires_minutes: Optional[int] = 120,
) -> Notification:
    """Create a notification. If dedup_key exists, return the stored one (idempotent)."""
    if dedup_key:
        existing = db.query(Notification).filter(Notification.dedup_key == dedup_key).first()
        if existing:
            return existing

    now = datetime.utcnow()
    notif = Notification(
        user_id=user_id,
        type=type,
        message=message,
        priority=priority,
        payload_json=payload,
        status="QUEUED",
        requires_ack=requires_ack,
        ack_deadline=now + timedelta(minutes=ack_minutes) if requires_ack else None,
        dedup_key=dedup_key,
        correlation_id=correlation_id,
        expires_at=now + timedelta(minutes=expires_minutes) if expires_minutes else None,
    )
    db.add(notif)
    db.flush()  # caller commits
    return notif


def acknowledge(db: Session, notification_id: int, user_id: int, status: str) -> Optional[Notification]:
    """Ack/seen: terminal states that cancel escalation (handled implicitly by tick)."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == user_id
    ).first()
    if not notif:
        return None
    notif.status = status
    if status == "ACKNOWLEDGED":
        notif.acked_at = datetime.utcnow()
    db.flush()
    return notif


def _managers_for_warehouse(db: Session, warehouse_id: str) -> list:
    return db.query(User).filter(
        User.warehouse_id == warehouse_id, User.role.in_(["MANAGER", "ADMIN"])
    ).all()


def tick_escalations(db: Session) -> dict:
    """
    Advance overdue ack-required notifications through the escalation ladder.
    Idempotent and safe to call on a timer.
    """
    now = datetime.utcnow()
    overdue = db.query(Notification).filter(
        Notification.requires_ack == True,  # noqa: E712
        Notification.status.in_(["QUEUED", "SENT", "DELIVERED", "SEEN"]),
        Notification.ack_deadline != None,  # noqa: E711
        Notification.ack_deadline < now,
    ).all()

    escalated = re_alerted = proposals = 0
    for n in overdue:
        # Superseded notifications: task already done -> drop silently
        if n.payload_json and n.payload_json.get("task_id"):
            task = db.query(Task).filter(Task.id == n.payload_json["task_id"]).first()
            if task and task.status in ("COMPLETED", "VERIFIED", "REJECTED"):
                n.status = "ACKNOWLEDGED"  # system auto-resolves, no human needed
                n.acked_at = now
                continue

        level = n.escalation_level or 0
        step = ESCALATION_STEPS_MIN.get(level)
        if step is None:
            continue  # fully escalated, nothing more to do automatically
        if now < n.ack_deadline + timedelta(minutes=step):
            continue

        owner = db.query(User).filter(User.id == n.user_id).first()
        warehouse_id = owner.warehouse_id if owner else None

        if level == 0:
            # Re-alert the worker
            n.escalation_level = 1
            n.status = "QUEUED"
            n.message = f"[REMINDER] {n.message}"
            re_alerted += 1
        elif level == 1:
            # Alert the managers/supervisors of that warehouse
            n.escalation_level = 2
            for mgr in _managers_for_warehouse(db, warehouse_id or ""):
                create_notification(
                    db,
                    user_id=mgr.id,
                    type="escalation.supervisor",
                    message=f"Worker (user {owner.username if owner else n.user_id}) has not acknowledged "
                            f"notification #{n.id} ({n.type}). Please intervene or reassign.",
                    priority="high",
                    dedup_key=f"escalation.supervisor:{n.id}:{mgr.id}",
                    payload={"original_notification_id": n.id, "worker_user_id": n.user_id},
                )
            escalated += 1
        elif level == 2:
            # Nobody acted -> propose reassignment through the Action Engine (T2, needs approval)
            n.escalation_level = 3
            task_id = (n.payload_json or {}).get("task_id")
            if task_id:
                key = f"auto-propose-reassign:{task_id}:{n.id}"
                existing = db.query(AgentAction).filter(AgentAction.idempotency_key == key).first()
                if not existing:
                    action = AgentAction(
                        agent_name="MonitoringAgent",
                        warehouse_id=warehouse_id or "WH-001",
                        trigger=f"Escalated unacknowledged notification #{n.id}",
                        tool_called="propose_reassignment",
                        action_type="REASSIGN_TASK",
                        action_payload={"task_id": task_id, "new_worker_id": None, "reason": "no acknowledgment"},
                        idempotency_key=key,
                        recommendation=f"Reassign task {task_id}: original assignee did not acknowledge.",
                        manager_approval="PENDING",
                    )
                    db.add(action)
                    proposals += 1

    db.commit()
    return {
        "checked": len(overdue),
        "re_alerted": re_alerted,
        "escalated_to_supervisor": escalated,
        "reassignment_proposals": proposals,
        "at": now.isoformat(),
    }
