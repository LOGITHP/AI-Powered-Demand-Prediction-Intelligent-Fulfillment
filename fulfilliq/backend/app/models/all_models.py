from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    STORE_MANAGER = "STORE_MANAGER"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


class StoreTypeEnum(str, enum.Enum):
    RETAIL_STORE = "RETAIL_STORE"
    DARK_STORE = "DARK_STORE"
    WAREHOUSE = "WAREHOUSE"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.CUSTOMER)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    store = relationship("Store", back_populates="manager", foreign_keys=[store_id])


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    type = Column(Enum(StoreTypeEnum), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    operating_hours = Column(String(80), default="7:00 AM – 11:00 PM")
    capacity = Column(Integer, default=1200)
    is_active = Column(Boolean, default=True)
    manager = relationship("User", back_populates="store", uselist=False, foreign_keys="User.store_id")
    inventory = relationship("Inventory", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String(40), unique=True, index=True, nullable=False)
    name = Column(String(180), index=True, nullable=False)
    category = Column(String(80), index=True, nullable=False)
    subcategory = Column(String(100))
    brand = Column(String(100))
    price = Column(Float, nullable=False)
    unit = Column(String(50), default="1 unit")
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id", name="uq_inventory_store_product"),)
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    reported_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    safety_stock = Column(Integer, default=5, nullable=False)
    inventory_accuracy = Column(Float, default=0.9, nullable=False)
    store = relationship("Store", back_populates="inventory")
    product = relationship("Product")


class InventoryEvent(Base):
    __tablename__ = "inventory_events"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    event_type = Column(String(40), nullable=False)
    source = Column(String(20), default="POS", nullable=False)
    quantity_delta = Column(Integer, nullable=False)
    reported_quantity = Column(Integer, nullable=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    customer_lat = Column(Float, nullable=False)
    customer_lng = Column(Float, nullable=False)
    status = Column(String(32), default="CONFIRMED", nullable=False)
    total_amount = Column(Float, default=0, nullable=False)
    store = relationship("Store", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    customer = relationship("User")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_time = Column(Float, nullable=False)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class HistoricalOrder(Base):
    __tablename__ = "historical_orders"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(48), index=True)
    timestamp = Column(DateTime, index=True)
    product_id = Column(Integer, index=True)
    store_id = Column(Integer, index=True)
    quantity = Column(Integer)
    customer_lat = Column(Float)
    customer_lng = Column(Float)
    hour = Column(Integer, index=True)
    day_of_week = Column(Integer)
    month = Column(Integer)
    is_weekend = Column(Boolean)
    promotion_flag = Column(Boolean)
    inventory_before_order = Column(Integer)
    inventory_after_order = Column(Integer)
    fulfilled = Column(Boolean, index=True)
    cancelled = Column(Boolean)
    stockout = Column(Boolean)
    inventory_accuracy = Column(Float, default=0.9)
    inventory_age_hours = Column(Float, default=1.0)
    sales_velocity = Column(Float, default=1.0)


class DemandPrediction(Base):
    __tablename__ = "demand_predictions"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    predicted_for = Column(DateTime, index=True)
    predicted_demand = Column(Float, nullable=False)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    model_version = Column(String(60))
    created_at = Column(DateTime, default=datetime.utcnow)


class AvailabilityPrediction(Base):
    __tablename__ = "availability_predictions"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True)
    requested_quantity = Column(Integer)
    availability_probability = Column(Float, nullable=False)
    reported_quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), index=True, nullable=False)
    action_type = Column(String(40), default="REPLENISHMENT")
    recommended_quantity = Column(Integer, nullable=False)
    deadline = Column(DateTime)
    reason = Column(Text)
    status = Column(String(24), default="PENDING", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    store = relationship("Store")
    product = relationship("Product")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    model_type = Column(String(24), index=True, nullable=False)
    version_name = Column(String(80), unique=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    dataset_size = Column(Integer, nullable=False)
    training_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    metrics = Column(Text, default="{}")
    features = Column(Text, default="[]")
    hyperparameters = Column(Text, default="{}")


class StoreTransfer(Base):
    __tablename__ = "store_transfers"
    id = Column(Integer, primary_key=True)
    from_store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    to_store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(24), default="COMPLETED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SimulationState(Base):
    __tablename__ = "simulation_state"
    id = Column(Integer, primary_key=True)
    simulated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    seed = Column(Integer, default=42, nullable=False)
    is_running = Column(Boolean, default=False, nullable=False)
    fulfillment_weights = Column(
        Text,
        default='{"availability":40,"inventory":20,"distance":20,"future_availability":10,"delivery_sla":10}',
        nullable=False,
    )
