from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import AgentAction
from app.api.auth import get_current_user
from app.action_engine.engine import decide_action
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ApprovalUpdate(BaseModel):
    status: str  # APPROVED, MODIFIED, REJECTED
    payload: Optional[dict] = None  # required for MODIFIED: overrides action_payload


@router.get("/")
def get_pending_approvals(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Managers only")
    approvals = (
        db.query(AgentAction)
        .filter(AgentAction.manager_approval == "PENDING")
        .order_by(AgentAction.timestamp.desc())
        .all()
    )
    return approvals


@router.put("/{action_id}")
def update_approval(action_id: int, payload: ApprovalUpdate,
                    current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Managers only")
    action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    action = decide_action(
        db, action,
        decision=payload.status,
        decided_by_user_id=current_user.id,
        modified_payload=payload.payload,
    )
    return {
        "status": "success",
        "action_id": action.id,
        "new_status": action.manager_approval,
        "execution_result": action.execution_result,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
    }
