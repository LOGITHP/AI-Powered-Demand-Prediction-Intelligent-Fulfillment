from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

# --- Existing Models Preserved ---
class OperationalState(BaseModel):
    orders: int
    pending_orders: int
    workers: int
    capacity_utilization: float

class Predictions(BaseModel):
    workload: str | int
    workers_required: int
    risk_score: float

class Alert(BaseModel):
    type: str
    severity: str

class WarehouseUpdate(BaseModel):
    warehouse_id: str
    timestamp: datetime
    operational_state: OperationalState
    predictions: Predictions
    alerts: List[Alert] = []

class WarehouseState(BaseModel):
    status: str
    orders: int
    workers: int
    workers_required: int
    capacity_utilization: float
    risk_score: float
    predicted_workload: str | int
# --- End Existing Models ---

# --- New Architectural Models ---
class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    INVENTORY_CHECKED = "INVENTORY_CHECKED"
    FULFILLMENT_ASSIGNED = "FULFILLMENT_ASSIGNED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"

class Order(BaseModel):
    id: str
    customer_info: Dict[str, str]
    items: List[Dict[str, Any]]
    status: OrderStatus = OrderStatus.CREATED
    assigned_fc: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Inventory(BaseModel):
    product_id: str
    warehouse_id: str
    available: int
    reserved: int
    inbound: int
    outbound: int
    reorder_threshold: int
    safety_stock: int

class ProcurementStatus(str, Enum):
    REQUEST_CREATED = "REQUEST_CREATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PURCHASE_CREATED = "PURCHASE_CREATED"
    SELLER_CONFIRMED = "SELLER_CONFIRMED"
    SHIPPED = "SHIPPED"
    RECEIVED = "RECEIVED"
    COMPLETED = "COMPLETED"

class ProcurementRequest(BaseModel):
    id: str
    product_id: str
    quantity: int
    status: ProcurementStatus = ProcurementStatus.REQUEST_CREATED
    seller_id: str
    created_at: datetime

class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"

class ExceptionRecord(BaseModel):
    id: str
    type: str
    severity: ExceptionSeverity
    source: str
    timestamp: datetime
    related_entity: Optional[str]
    description: str
    recommended_action: Optional[str]
    status: str = "OPEN"

class NetworkState(BaseModel):
    warehouses: Dict[str, WarehouseState] = {}
    orders: Dict[str, Order] = {}
    inventory: Dict[str, List[Inventory]] = {} # product_id -> List[Inventory]
    procurement_requests: Dict[str, ProcurementRequest] = {}
    exceptions: Dict[str, ExceptionRecord] = {}
