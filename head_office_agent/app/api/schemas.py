from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from state.models import WarehouseUpdate

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    tools_used: List[str]

class SimulateRequest(BaseModel):
    scenario: Dict[str, Any]

class SimulateResponse(BaseModel):
    simulated_state: Dict[str, Any]

class ApproveDecisionRequest(BaseModel):
    decision_id: str
    approved: bool
