from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class OperationalState(BaseModel):
    orders: int
    pending_orders: int
    workers: int
    capacity_utilization: float

class Predictions(BaseModel):
    workload: str | int # could be HIGH/MEDIUM/LOW or an int
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

class NetworkState(BaseModel):
    warehouses: Dict[str, WarehouseState] = {}
