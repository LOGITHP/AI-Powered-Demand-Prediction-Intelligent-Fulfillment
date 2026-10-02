from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.all_models import RoleEnum, StoreTypeEnum

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

class UserCreate(BaseModel):
    email: str
    password: str
    role: RoleEnum = RoleEnum.CUSTOMER
    store_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    email: str
    role: RoleEnum
    store_id: Optional[int]

    class Config:
        from_attributes = True

class StoreResponse(BaseModel):
    id: int
    name: str
    type: StoreTypeEnum
    latitude: float
    longitude: float
    area: Optional[str]
    address: Optional[str]
    operating_hours: Optional[str]
    capacity: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    subcategory: Optional[str]
    brand: Optional[str]
    price: float
    unit: Optional[str]
    image_url: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    id: int
    store_id: int
    product_id: int
    reported_quantity: int
    reserved_quantity: int
    last_updated: datetime
    reorder_level: int
    safety_stock: int
    inventory_accuracy: float

    class Config:
        from_attributes = True

class MLTrainingRequest(BaseModel):
    sample_fraction: float = 1.0 # use 1.0 for all data, 0.1 for faster testing

class MLTrainingResponse(BaseModel):
    message: str
    task_status: str

class StoreRecommendationResponse(BaseModel):
    recommended_store: dict
    alternatives: List[dict]

class LocationRequest(BaseModel):
    customer_lat: float
    customer_lng: float
    product_id: int
    quantity: int
