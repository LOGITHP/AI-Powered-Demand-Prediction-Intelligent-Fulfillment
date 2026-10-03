from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # MANAGER, WORKER, INBOUND, OUTBOUND, ADMIN
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
    status = Column(String) # PRESENT, ABSENT
    login_time = Column(DateTime, default=func.now())
    logout_time = Column(DateTime, nullable=True)
    date = Column(DateTime, default=func.now())

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(String, primary_key=True, index=True)
    capacity = Column(String)
    efficiency_multiplier = Column(Float)

class OperationalEvent(Base):
    __tablename__ = "operational_events"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String, index=True)
    event_type = Column(String)
    description = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=func.now())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String)
    process_type = Column(String) # PICKING, PACKING, RECEIVING
    priority = Column(String)
    status = Column(String) # PENDING, IN_PROGRESS, COMPLETED
    assigned_worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True)
    instructions = Column(String)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) # INFO, WARNING, CRITICAL, TASK, APPROVAL_REQUIRED, HEAD_OFFICE
    message = Column(String)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())

class AgentAction(Base):
    __tablename__ = "agent_actions"
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String)
    warehouse_id = Column(String)
    trigger = Column(String)
    tool_called = Column(String)
    input_summary = Column(Text)
    recommendation = Column(Text)
    manager_approval = Column(String, default="NOT_REQUIRED") # NOT_REQUIRED, PENDING, APPROVED, REJECTED
    execution_result = Column(Text)
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

# Basic representations for inbound/outbound queues for simulation
class WorkloadQueue(Base):
    __tablename__ = "workload_queue"
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(String)
    process_type = Column(String)
    volume = Column(Integer)
    timestamp = Column(DateTime, default=func.now())
