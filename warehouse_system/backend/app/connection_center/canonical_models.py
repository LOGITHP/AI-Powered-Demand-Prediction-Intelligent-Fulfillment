from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime

class CanonicalItem(BaseModel):
    sku_id: str
    quantity: int
    
class HeadOfficeInstruction(BaseModel):
    instruction_id: str = Field(description="Unique ID from the Head Office")
    order_id: str
    items: List[CanonicalItem]
    fulfillment_center: str = Field(..., alias="fc")
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"]
    sla_hours: int
    required_operation: Literal["PICK_PACK_SHIP", "REPLENISH", "CROSS_DOCK"]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WMSInventoryUpdate(BaseModel):
    sku_id: str
    location_id: str
    quantity: int
    update_type: Literal["ADD", "REMOVE", "ADJUST"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CanonicalTask(BaseModel):
    task_id: str
    task_type: Literal["RECEIVING", "PUTAWAY", "PICKING", "PACKING", "DISPATCH", "REPLENISHMENT"]
    priority: str
    zone_id: Optional[str]
    assigned_worker_id: Optional[str]
    status: str
    deadline: Optional[datetime]
