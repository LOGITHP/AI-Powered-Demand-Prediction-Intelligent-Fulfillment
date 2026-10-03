from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add
from pydantic import BaseModel

class AgentState(TypedDict):
    request_id: str
    user_query: Optional[str]
    messages: Annotated[list, add]
    network_state: Dict[str, Any]
    current_event: Optional[Dict[str, Any]]
    affected_warehouses: List[str]
    observations: List[str]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    identified_problems: List[str]
    resource_shortages: List[Dict[str, Any]]
    resource_surpluses: List[Dict[str, Any]]
    candidate_actions: List[Dict[str, Any]]
    selected_action: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    approval_status: Optional[str] # PENDING_APPROVAL, APPROVED, REJECTED
    execution_result: Optional[Dict[str, Any]]
    final_response: Optional[str]
    errors: List[str]
    timestamps: Dict[str, str]
