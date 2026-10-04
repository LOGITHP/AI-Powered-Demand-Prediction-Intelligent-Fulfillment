from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
from enum import Enum

class EventType(Enum):
    WORKLOAD_SPIKE = "WORKLOAD_SPIKE"
    WORKER_SHORTAGE = "WORKER_SHORTAGE"
    CAPACITY_WARNING = "CAPACITY_WARNING"
    INVENTORY_SHORTAGE = "INVENTORY_SHORTAGE"
    PROCESSING_DELAY = "PROCESSING_DELAY"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
    ORDER_SURGE = "ORDER_SURGE"
    CUSTOMER_ORDER = "CUSTOMER_ORDER"

class NetworkEvent(BaseModel):
    event_id: str
    type: EventType
    warehouse_id: str
    timestamp: datetime
    severity: str
    payload: Dict[str, Any]

