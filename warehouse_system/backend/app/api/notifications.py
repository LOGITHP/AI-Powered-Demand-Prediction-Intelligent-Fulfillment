import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db, SessionLocal
from app.db.models import Notification
from app.api.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class AckRequest(BaseModel):
    status: str # SEEN, ACKNOWLEDGED

class ReplyRequest(BaseModel):
    reply: str

async def notification_event_generator(user_id: int):
    """
    Background generator for Server-Sent Events (SSE).
    Polls the DB for QUEUED or SENT notifications for the specific user.
    """
    while True:
        db = SessionLocal()
        try:
            # Fetch un-delivered/un-acked notifications
            notifications = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.status.in_(["CREATED", "QUEUED", "SENT", "DELIVERED"])
            ).all()
            
            for notif in notifications:
                # If they were just sitting, mark them as SENT for SSE
                if notif.status in ["CREATED", "QUEUED"]:
                    notif.status = "SENT"
                    db.commit()
                
                payload = {
                    "id": notif.id,
                    "type": notif.type,
                    "message": notif.message,
                    "status": notif.status,
                    "payload_json": notif.payload_json
                }
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            db.close()
            
        await asyncio.sleep(2) # Polling interval

@router.get("/stream")
async def stream_notifications(current_user = Depends(get_current_user)):
    """SSE endpoint for real-time notifications"""
    return StreamingResponse(
        notification_event_generator(current_user.id),
        media_type="text/event-stream"
    )

@router.get("/")
def get_notifications(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.timestamp.desc()).all()
    return notifications

@router.post("/{notification_id}/ack")
def acknowledge_notification(notification_id: int, request: AckRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.notification_service import acknowledge
    if request.status not in ["SEEN", "ACKNOWLEDGED"]:
        raise HTTPException(status_code=400, detail="Invalid ack status")
    notif = acknowledge(db, notification_id, current_user.id, request.status)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()
    return {"status": "success", "new_state": notif.status, "acked_at": notif.acked_at}


@router.post("/escalate/tick")
def run_escalation_tick(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Advance overdue ack-required notifications through the escalation ladder.
    (Also runs automatically in the background loop; this endpoint exists for demos/tests.)"""
    from app.services.notification_service import tick_escalations
    return tick_escalations(db)


@router.get("/unacknowledged")
def list_unacknowledged(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Open ack-required notifications past their ack deadline (monitoring view)."""
    from datetime import datetime
    return db.query(Notification).filter(
        Notification.requires_ack == True,  # noqa: E712
        Notification.status.in_(["QUEUED", "SENT", "DELIVERED", "SEEN"]),
        Notification.ack_deadline != None,  # noqa: E711
        Notification.ack_deadline < datetime.utcnow(),
    ).order_by(Notification.ack_deadline.asc()).all()

@router.post("/{notification_id}/reply")
def reply_notification(notification_id: int, request: ReplyRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notif.reply_message = request.reply
    notif.status = "ACKNOWLEDGED"
    db.commit()
    
    return {"status": "success", "reply": notif.reply_message}
