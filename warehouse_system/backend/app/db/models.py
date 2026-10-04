from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # MANAGER, WORKER, INBOUND, OUTBOUND, ADMIN
    warehouse_id = Column(String, index=True)
    is_active = Column(Boolean, default=True)

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    worker_id = Column(String, unique=True, index=True)
    name = Column(String)
    warehouse_id = Column(String, index=True)
    skill_level = Column(String)
    experience_years = Column(Float)
    assigned_zone = Column(String)
    shift = Column(Integer)
    status = Column(String, default="OFF_SHIFT")

class WorkerPresence(Base):
    __tablename__ = "worker_presence"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(String, ForeignKey("workers.worker_id"))
    warehouse_id = Column(String)
    shift = Column(Integer)
    status = Column(String)
    login_time = Column(DateTime, default=func.now())
    logout_time = Column(DateTime, nullable=True)
    date = Column(DateTime, default=func.now())

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(String, primary_key=True, index=True)
    capacity = Column(String)
    efficiency_multiplier = Column(Float)

class StorageLocation(Base):
    __tablename__ = "storage_locations"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    zone = Column(String)
    aisle = Column(String)
    rack = Column(String)
    bin = Column(String)
    capacity = Column(Integer)
    current_occupancy = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

    @property
    def available_capacity(self):
        return self.capacity - self.current_occupancy

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String)
    category = Column(String)
    unit_weight = Column(Float, default=1.0)
    warehouse_id = Column(String, index=True)

class InventoryRecord(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    movement_type = Column(String)  # INBOUND, OUTBOUND, TRANSFER, ADJUSTMENT
    quantity = Column(Integer)
    source = Column(String, nullable=True)
    destination = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=func.now())
    notes = Column(String, nullable=True)

# ============================
# INBOUND MODELS
# ============================
class InboundShipment(Base):
    __tablename__ = "inbound_shipments"
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String, unique=True, index=True)
    warehouse_id = Column(String, index=True)
    supplier = Column(String)
    vehicle_number = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    expected_arrival = Column(DateTime)
    actual_arrival = Column(DateTime, nullable=True)
    status = Column(String, default="EXPECTED")  # EXPECTED, ARRIVED, RECEIVING, INSPECTION, PUTAWAY, COMPLETED, CANCELLED, DELAYED
    priority = Column(String, default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    total_items = Column(Integer, default=0)
    received_items = Column(Integer, default=0)
    damaged_items = Column(Integer, default=0)
    assigned_worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    receiving_started_at = Column(DateTime, nullable=True)
    receiving_completed_at = Column(DateTime, nullable=True)
    inspection_started_at = Column(DateTime, nullable=True)
    inspection_completed_at = Column(DateTime, nullable=True)
    putaway_started_at = Column(DateTime, nullable=True)
    putaway_completed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    items = relationship("InboundShipmentItem", back_populates="shipment")

class InboundShipmentItem(Base):
    __tablename__ = "inbound_shipment_items"
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String, ForeignKey("inbound_shipments.shipment_id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    expected_quantity = Column(Integer)
    received_quantity = Column(Integer, default=0)
    damaged_quantity = Column(Integer, default=0)
    accepted_quantity = Column(Integer, default=0)
    rejected_quantity = Column(Integer, default=0)
    inspection_status = Column(String, default="PENDING")  # PENDING, ACCEPTED, DAMAGED, REJECTED, PARTIAL
    putaway_status = Column(String, default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED
    putaway_location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    inspection_notes = Column(Text, nullable=True)
    shipment = relationship("InboundShipment", back_populates="items")

# ============================
# OUTBOUND MODELS
# ============================
class OutboundOrder(Base):
    __tablename__ = "outbound_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    warehouse_id = Column(String, index=True)
    customer = Column(String, nullable=True)
    priority = Column(String, default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    order_date = Column(DateTime, default=func.now())
    release_time = Column(DateTime, nullable=True)
    required_dispatch_time = Column(DateTime)
    actual_dispatch_time = Column(DateTime, nullable=True)
    status = Column(String, default="CREATED")  # CREATED, RELEASED, PICKING, PICKED, PACKING, PACKED, LOADING, DISPATCHED, COMPLETED, CANCELLED, DELAYED
    total_items = Column(Integer, default=0)
    picked_items = Column(Integer, default=0)
    packed_items = Column(Integer, default=0)
    loaded_items = Column(Integer, default=0)
    assigned_worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    picking_started_at = Column(DateTime, nullable=True)
    picking_completed_at = Column(DateTime, nullable=True)
    packing_started_at = Column(DateTime, nullable=True)
    packing_completed_at = Column(DateTime, nullable=True)
    loading_started_at = Column(DateTime, nullable=True)
    loading_completed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    items = relationship("OutboundOrderItem", back_populates="order")

class OutboundOrderItem(Base):
    __tablename__ = "outbound_order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("outbound_orders.order_id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    required_quantity = Column(Integer)
    picked_quantity = Column(Integer, default=0)
    packed_quantity = Column(Integer, default=0)
    loaded_quantity = Column(Integer, default=0)
    status = Column(String, default="PENDING")  # PENDING, PICKING, PICKED, PACKING, PACKED, LOADED, COMPLETED, SHORTAGE
    pick_location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=True)
    notes = Column(Text, nullable=True)
    order = relationship("OutboundOrder", back_populates="items")

# ============================
# EXISTING MODELS
# ============================
class OperationalEvent(Base):
    __tablename__ = "operational_events"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    event_type = Column(String, index=True)
    description = Column(String)
    details = Column(JSON)
    reference_id = Column(String, nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=func.now())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String)
    process_type = Column(String)
    priority = Column(String)
    status = Column(String, default="PENDING")  # PLANNED, PENDING, ASSIGNED, STARTED, COMPLETED, VERIFIED, ISSUE_REPORTED, REJECTED
    assigned_worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True)
    instructions = Column(String)
    zone = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    reference_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class LaborStandard(Base):
    """Units one worker processes per hour for a process type. Reviewable config."""
    __tablename__ = "labor_standards"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    process_type = Column(String)  # RECEIVING, INSPECTION, PUTAWAY, PICKING, PACKING, DISPATCH
    units_per_hour = Column(Float)
    productive_hours_per_shift = Column(Float, default=7.0)
    absenteeism_rate = Column(Float, default=0.08)

class VolumeHistory(Base):
    """Historical daily volume per process type. Feeds forecasting."""
    __tablename__ = "volume_history"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    process_type = Column(String, index=True)
    date = Column(DateTime, index=True)
    volume = Column(Float)

class PlanRun(Base):
    """Persisted execution trace of the planning pipeline state machine."""
    __tablename__ = "plan_runs"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String, unique=True, index=True)
    instruction_id = Column(String, nullable=True, index=True)
    warehouse_id = Column(String)
    status = Column(String, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    steps = Column(JSON, default=list)  # [{step, status, detail, at}]
    created_at = Column(DateTime, default=func.now())

class OutboxEvent(Base):
    """Outbox pattern: every approved mutation is recorded here before execution."""
    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True)
    event_type = Column(String)
    payload = Column(JSON)
    status = Column(String, default="PENDING")  # PENDING, DELIVERED, FAILED
    created_at = Column(DateTime, default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    message = Column(String)
    priority = Column(String, default="medium")  # low, medium, high, critical
    payload_json = Column(JSON, nullable=True)
    status = Column(String, default="CREATED") # CREATED, QUEUED, SENT, DELIVERED, SEEN, ACKNOWLEDGED
    requires_ack = Column(Boolean, default=False)
    ack_deadline = Column(DateTime, nullable=True)
    acked_at = Column(DateTime, nullable=True)
    reply_message = Column(String, nullable=True)
    dedup_key = Column(String, nullable=True, unique=True)
    correlation_id = Column(String, nullable=True)
    escalation_level = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=func.now())

class AgentAction(Base):
    __tablename__ = "agent_actions"
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String)
    warehouse_id = Column(String)
    trigger = Column(String)
    tool_called = Column(String)
    action_type = Column(String, nullable=True)  # REASSIGN_TASK, REDISTRIBUTE_WORKERS, MANUAL
    action_payload = Column(JSON, nullable=True)  # structured params (may be MODIFIED by manager)
    idempotency_key = Column(String, nullable=True, unique=True)
    input_summary = Column(Text)
    recommendation = Column(Text)
    manager_approval = Column(String, default="NOT_REQUIRED")  # PENDING, APPROVED, MODIFIED, REJECTED
    execution_result = Column(Text)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=func.now())

class MLPrediction(Base):
    __tablename__ = "ml_predictions"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String)
    model_name = Column(String)
    process_type = Column(String)
    prediction_value = Column(Float)
    probability = Column(Float, nullable=True)
    inputs = Column(JSON)
    timestamp = Column(DateTime, default=func.now())

class WorkloadQueue(Base):
    __tablename__ = "workload_queue"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String)
    process_type = Column(String)
    volume = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    issue_type = Column(String)  # DAMAGED_GOODS, SHORT_RECEIVED, EXCESS_RECEIVED, INSPECTION_FAILURE, MISSING_PRODUCT, STORAGE_UNAVAILABLE, PUTAWAY_DELAY, INVENTORY_SHORTAGE, PICKING_DELAY, etc.
    severity = Column(String, default="WARNING")  # INFO, WARNING, CRITICAL
    description = Column(String)
    reference_id = Column(String, nullable=True)
    reference_type = Column(String, nullable=True)  # SHIPMENT, ORDER
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())

class ConnectionMessage(Base):
    """Connection Center: inbound/outbound message ledger with dedup, retries, DLQ."""
    __tablename__ = "connection_messages"
    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(String, index=True)
    direction = Column(String)  # INBOUND, OUTBOUND
    dedup_key = Column(String, unique=True, index=True)
    payload = Column(JSON)
    status = Column(String, default="RECEIVED")  # RECEIVED, PROCESSED, PENDING, DELIVERED, FAILED, DEAD_LETTER
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
