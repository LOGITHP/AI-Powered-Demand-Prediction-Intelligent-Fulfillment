from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: str
    role: str
    warehouse_id: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

class WorkerBase(BaseModel):
    worker_id: str
    name: str
    warehouse_id: str
    skill_level: str
    experience_years: float
    assigned_zone: str
    shift: int

class MLPredictionRequest(BaseModel):
    warehouse_id: str
    shift: int
    process_type: str
    workload_quantity: int
    number_of_orders: int
    number_of_items: int
    number_of_skus: int
    scheduled_workers: int
    available_workers: int
    average_worker_experience: float
    average_worker_skill: float
    equipment_available: float
    current_queue: int
    warehouse_utilization: float
    historical_productivity: float
    distance_factor: float
    task_complexity: float

class AgentRequest(BaseModel):
    message: str
    warehouse_id: str

class WorkloadRequest(BaseModel):
    process_type: str
    volume: int
    priority: str = "NORMAL"
