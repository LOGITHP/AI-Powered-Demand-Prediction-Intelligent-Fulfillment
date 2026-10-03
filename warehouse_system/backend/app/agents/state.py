from typing import TypedDict, Annotated, List, Dict, Any
from operator import add
from langchain_core.messages import BaseMessage

class WarehouseAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add]
    warehouse_id: str
    user_id: str
    user_role: str
    current_request: str
    
    # State tracking
    warehouse_status: Dict[str, Any]
    worker_status: Dict[str, Any]
    inbound_status: Dict[str, Any]
    outbound_status: Dict[str, Any]
    ml_predictions: Dict[str, Any]
    
    # Outcomes
    recommendations: List[str]
    pending_approval: bool
    approved_action: str
    execution_result: str
    notifications_sent: List[str]
    head_office_message: str
    agent_reasoning: str
