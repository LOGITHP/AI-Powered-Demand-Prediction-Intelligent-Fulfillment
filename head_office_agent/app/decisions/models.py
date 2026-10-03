from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class Decision(BaseModel):
    decision_id: str
    type: str
    priority: str
    affected_warehouses: List[str]
    reasoning: List[str]
    recommended_actions: List[Dict[str, Any]]
    constraints: List[str] = []
    expected_impact: Dict[str, Any] = {}
    confidence: float
    status: str = "PENDING_APPROVAL" # PENDING_APPROVAL, APPROVED, REJECTED, EXECUTED
