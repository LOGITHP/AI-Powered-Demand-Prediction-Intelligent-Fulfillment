from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AgentRegisterRequest(BaseModel):
    agent_id: str
    warehouse_id: str
    agent_version: str
    capabilities: List[str]

class AgentRegisterResponse(BaseModel):
    agent_id: str
    warehouse_id: str
    status: str
    heartbeat_interval: int

class HeartbeatRequest(BaseModel):
    agent_id: str
    warehouse_id: str
    status: str
    timestamp: datetime

class AgentEventRequest(BaseModel):
    event_id: str
    agent_id: str
    warehouse_id: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]

class CommandAckRequest(BaseModel):
    command_id: str
    agent_id: str
    status: str
    timestamp: datetime
    message: Optional[str] = None

class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int

class OrderAllocateRequest(BaseModel):
    order_id: str
    destination: str
    priority: str
    items: List[OrderItemSchema]

class RecommendationApproveRequest(BaseModel):
    approved: bool
