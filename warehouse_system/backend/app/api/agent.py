from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AgentRequest
from app.api.auth import get_current_user
from app.agents.graph import build_graph
from langchain_core.messages import HumanMessage
from app.core.config import settings

router = APIRouter()

@router.post("/chat")
def chat_with_agent(request: AgentRequest, current_user = Depends(get_current_user)):
    if not settings.NVIDIA_API_KEY:
        raise HTTPException(status_code=500, detail="NVIDIA_API_KEY is not configured.")
        
    graph = build_graph()
    
    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "warehouse_id": request.warehouse_id,
        "user_id": str(current_user.id),
        "user_role": current_user.role,
        "current_request": request.message
    }
    
    try:
        final_state = graph.invoke(initial_state)
        response_msg = final_state["messages"][-1].content
        return {"response": response_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
