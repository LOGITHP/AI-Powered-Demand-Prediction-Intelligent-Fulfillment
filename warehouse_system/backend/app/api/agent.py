import logging
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import AgentRequest
from app.api.auth import get_current_user
from app.agents.graph import build_graph
from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import AgentAction, InboundShipment, Worker
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)
router = APIRouter()


def _audit_chat(db, warehouse_id: str, message: str, response: str,
                tools_called=(), approval: str = "NOT_REQUIRED", result: str = "SUCCESS"):
    """Every agent interaction (LLM or fallback) leaves an audit trail."""
    db.add(AgentAction(
        agent_name="WarehouseAgent",
        warehouse_id=warehouse_id,
        trigger="User Chat",
        tool_called=", ".join(tools_called) if tools_called else None,
        input_summary=message,
        recommendation=response,
        manager_approval=approval,
        execution_result=result,
        action_type="ROUTINE",
    ))
    db.commit()


def _propose(db, warehouse_id: str, action_type: str, payload: dict,
             recommendation: str, idempotency_key: str) -> AgentAction:
    """Create a PENDING action for the manager. The Action Engine is the only
    component allowed to mutate operational state after approval."""
    existing = db.query(AgentAction).filter(AgentAction.idempotency_key == idempotency_key).first()
    if existing:
        return existing
    action = AgentAction(
        agent_name="WarehouseAgent",
        warehouse_id=warehouse_id,
        trigger="User Chat (fallback parser)",
        action_type=action_type,
        action_payload=payload,
        idempotency_key=idempotency_key,
        input_summary=recommendation,
        recommendation=recommendation,
        manager_approval="PENDING",
    )
    db.add(action)
    db.commit()
    return action


def _fallback_response(db, request: AgentRequest) -> str:
    """
    Deterministic intent parser used when the LLM graph is unavailable.
    State-changing intents are PROPOSED as pending actions (manager approves
    them in the portal / via the Action Engine) - never executed directly.
    """
    msg = request.message.lower()

    if "reallocate" in msg or ("picking" in msg and "putaway" in msg):
        action = _propose(
            db, request.warehouse_id, "REDISTRIBUTE_WORKERS",
            payload={"from_zone": "PUTAWAY", "to_zone": "PICKING", "count": 3},
            recommendation="Reallocate 3 workers from PUTAWAY to PICKING to clear the picking backlog.",
            idempotency_key=f"fallback:redistribute:PUTAWAY:PICKING:{datetime.utcnow():%Y%m%d%H}",
        )
        return (f"Proposal created (action #{action.id}): move 3 workers from Putaway to Picking. "
                "It is awaiting manager approval in the Approvals portal - no changes applied yet.")

    if "allocate" in msg and "outbound" in msg:
        match = re.search(r"worker\s*(\d+)", msg)
        worker_id = f"worker{match.group(1).zfill(3)}" if match else "worker001"
        worker = db.query(Worker).filter(Worker.worker_id == worker_id).first()
        if not worker:
            return f"Could not find worker {worker_id} in the system."
        action = _propose(
            db, request.warehouse_id, "ASSIGN_WORKER_ZONE",
            payload={"worker_id": worker_id, "to_zone": "LOADING"},
            recommendation=f"Assign {worker_id} to the Outbound (Loading) zone.",
            idempotency_key=f"fallback:assign-zone:{worker_id}:LOADING",
        )
        return (f"Proposal created (action #{action.id}): assign {worker_id} to Outbound (Loading). "
                "Awaiting manager approval - no changes applied yet.")

    if "inbound" in msg and "process" in msg:
        shipment = db.query(InboundShipment).filter(InboundShipment.status == "EXPECTED").first()
        if not shipment:
            return "No expected inbound shipments found to process."
        action = _propose(
            db, request.warehouse_id, "PROCESS_INBOUND_ARRIVAL",
            payload={"tracking_number": shipment.tracking_number},
            recommendation=f"Mark inbound shipment {shipment.tracking_number} as ARRIVED.",
            idempotency_key=f"fallback:inbound-arrival:{shipment.tracking_number}",
        )
        return (f"Proposal created (action #{action.id}): mark shipment {shipment.tracking_number} as ARRIVED. "
                "Awaiting manager approval.")

    return (f"I could not reach the reasoning engine, so no live analysis is available for: "
            f"\"{request.message}\". Operational changes always require manager approval.")


@router.post("/chat")
def chat_with_agent(request: AgentRequest, current_user=Depends(get_current_user)):
    mock_responses = [
        "Based on the current metrics, I recommend reallocating 3 workers from Putaway to Picking to handle the backlog.",
        "The inbound queue is currently at 120 units. Processing time is optimal.",
        "I have flagged a potential bottleneck in Outbound Packing. Delay risk is 45%.",
        "Action approved. Instructions sent to worker terminals W0001, W0002, W0003.",
        "Scenario analyzed. A 10% increase in peak volume will require 15 additional workers in the Picking zone."
    ]
    import os
    if not os.environ.get("GOOGLE_API_KEY"):
        response = f"[Demo Mode - No API Key] {random.choice(mock_responses)}"
        db = SessionLocal()
        try:
            _audit_chat(db, request.warehouse_id, request.message, response, result="DEMO_MODE")
        finally:
            db.close()
        return {"response": response}

    try:
        graph = build_graph()
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "warehouse_id": request.warehouse_id,
            "user_id": str(current_user.id),
            "user_role": current_user.role,
            "current_request": request.message
        }
        final_state = graph.invoke(initial_state, config={"recursion_limit": 25})
        response_msg = final_state["messages"][-1].content

        tools_called = []
        for m in final_state["messages"]:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                tools_called.extend(tc["name"] for tc in m.tool_calls)

        db = SessionLocal()
        try:
            _audit_chat(db, request.warehouse_id, request.message, response_msg,
                        tools_called=tools_called, result="SUCCESS")
        finally:
            db.close()
        return {"response": response_msg, "tools_used": tools_called}
    except Exception as e:
        logger.exception("Agent graph failed, using deterministic fallback")
        db = SessionLocal()
        try:
            try:
                final_response = _fallback_response(db, request)
                _audit_chat(db, request.warehouse_id, request.message, final_response,
                            result=f"FALLBACK (graph error: {type(e).__name__})")
            except Exception:
                logger.exception("Fallback parser also failed")
                final_response = "An error occurred while executing the agent action."
        finally:
            db.close()
        return {"response": final_response}


@router.get("/audit")
def get_audit_logs(current_user=Depends(get_current_user)):
    from app.db.database import SessionLocal
    from app.db.models import AgentAction
    db = SessionLocal()
    try:
        logs = db.query(AgentAction).order_by(AgentAction.timestamp.desc()).all()
        return logs
    finally:
        db.close()

from pydantic import BaseModel
from typing import Optional
class ApprovalRequest(BaseModel):
    decision: str  # APPROVED, MODIFIED, REJECTED
    payload: Optional[dict] = None

@router.post("/audit/{action_id}/approval")
def resolve_agent_action(action_id: int, request: ApprovalRequest, current_user=Depends(get_current_user)):
    from app.db.database import SessionLocal
    from app.db.models import AgentAction
    from app.action_engine.engine import decide_action
    db = SessionLocal()
    try:
        action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")

        action = decide_action(
            db, action,
            decision=request.decision,
            decided_by_user_id=current_user.id,
            modified_payload=request.payload,
        )
        return {"status": "success", "new_state": action.manager_approval,
                "execution_result": action.execution_result}
    finally:
        db.close()
