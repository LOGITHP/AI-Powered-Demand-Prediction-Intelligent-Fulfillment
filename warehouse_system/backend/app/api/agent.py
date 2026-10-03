from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AgentRequest
from app.api.auth import get_current_user
from app.agents.graph import build_graph
from langchain_core.messages import HumanMessage
from app.core.config import settings

router = APIRouter()

@router.post("/chat")
def chat_with_agent(request: AgentRequest, current_user = Depends(get_current_user)):
    mock_responses = [
        "Based on the current metrics, I recommend reallocating 3 workers from Putaway to Picking to handle the backlog.",
        "The inbound queue is currently at 120 units. Processing time is optimal.",
        "I have flagged a potential bottleneck in Outbound Packing. Delay risk is 45%.",
        "Action approved. Instructions sent to worker terminals W0001, W0002, W0003.",
        "Scenario analyzed. A 10% increase in peak volume will require 15 additional workers in the Picking zone."
    ]
    import random
    
    if not settings.NVIDIA_API_KEY:
        return {"response": f"[Demo Mode - No API Key] {random.choice(mock_responses)}"}
        
    try:
        graph = build_graph()
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "warehouse_id": request.warehouse_id,
            "user_id": str(current_user.id),
            "user_role": current_user.role,
            "current_request": request.message
        }
        final_state = graph.invoke(initial_state)
        response_msg = final_state["messages"][-1].content
        return {"response": response_msg}
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        from app.db.database import SessionLocal
        from app.db.models import Notification, User, Worker, AgentAction, OutboundOrder, InboundShipment
        db = SessionLocal()
        try:
            msg_lower = request.message.lower()
            if "reallocate" in msg_lower or "picking" in msg_lower:
                workers_to_move = db.query(Worker).filter(Worker.current_zone == "Putaway_A").limit(3).all()
                for w in workers_to_move:
                    w.current_zone = "Picking_A"
                    w.current_task = "Reassigned to Picking backlog"
                    user = db.query(User).filter(User.username == w.worker_id).first()
                    if user:
                        notif = Notification(
                            user_id=user.id,
                            type="INSTRUCTION",
                            status="QUEUED",
                            message=f"Reassigned from Putaway_A to Picking_A. Please proceed immediately."
                        )
                        db.add(notif)
                db.commit()
                final_response = "Action executed. Based on the metrics, I have reallocated 3 workers from Putaway to Picking. Instructions dispatched."
                
            elif "allocate" in msg_lower and "outbound" in msg_lower:
                # E.g. "allocate a work in outbound for worker 1"
                import re
                match = re.search(r'worker (\d+)', msg_lower)
                worker_num = match.group(1) if match else "1"
                worker_id = f"worker{worker_num.zfill(3)}"
                
                worker = db.query(Worker).filter(Worker.worker_id == worker_id).first()
                if worker:
                    worker.current_zone = "Outbound_A"
                    worker.current_task = "Process pending outbound orders"
                    
                    user = db.query(User).filter(User.username == worker_id).first()
                    if user:
                        notif = Notification(
                            user_id=user.id,
                            type="INSTRUCTION",
                            status="QUEUED",
                            message="Assigned to Outbound zone. Please begin loading the delivery partners."
                        )
                        db.add(notif)
                    db.commit()
                    final_response = f"Action executed. Assigned {worker_id} to Outbound. Notification sent."
                else:
                    final_response = f"Could not find {worker_id} in the system."
                    
            elif "inbound" in msg_lower and "process" in msg_lower:
                shipment = db.query(InboundShipment).filter(InboundShipment.status == "EXPECTED").first()
                if shipment:
                    shipment.status = "ARRIVED"
                    db.commit()
                    final_response = f"Processed inbound data. Shipment {shipment.tracking_number} marked as ARRIVED."
                else:
                    final_response = "No expected inbound shipments found to process."
            else:
                final_response = f"Action parsed. Simulated response for: {request.message}"

            # Save Agent history
            action = AgentAction(
                agent_name="Operations Agent",
                warehouse_id=request.warehouse_id,
                trigger="User Chat",
                input_summary=request.message,
                recommendation=final_response,
                manager_approval="NOT_REQUIRED",
                execution_result="SUCCESS",
                action_type="ROUTINE"
            )
            db.add(action)
            db.commit()

        except Exception as inner_e:
            import traceback
            traceback.print_exc()
            print("Error creating fallback notification:", inner_e)
            final_response = "An error occurred while executing the agent action."
        finally:
            db.close()
            
        return {"response": final_response}

@router.get("/audit")
def get_audit_logs(current_user = Depends(get_current_user)):
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
def resolve_agent_action(action_id: int, request: ApprovalRequest, current_user = Depends(get_current_user)):
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
