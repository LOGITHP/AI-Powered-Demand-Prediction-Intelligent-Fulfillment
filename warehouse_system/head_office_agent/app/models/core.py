from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.core import Base

class ManagerUser(Base):
    __tablename__ = "ho_managers"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)

class WarehouseAgent(Base):
    __tablename__ = "ho_warehouse_agents"
    
    agent_id = Column(String, primary_key=True, index=True)
    warehouse_id = Column(String, unique=True, index=True)
    status = Column(String) # ONLINE, DEGRADED, OFFLINE
    last_heartbeat = Column(DateTime(timezone=True))
    version = Column(String)
    capabilities = Column(JSON) # e.g. ["inventory", "inbound"]
    
    inventory = relationship("InventorySnapshot", back_populates="agent")
    capacity = relationship("WarehouseCapacity", back_populates="agent")

class InventorySnapshot(Base):
    __tablename__ = "ho_inventory_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("ho_warehouse_agents.agent_id"))
    product_id = Column(String, index=True)
    available_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    agent = relationship("WarehouseAgent", back_populates="inventory")

class WarehouseCapacity(Base):
    __tablename__ = "ho_warehouse_capacity"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("ho_warehouse_agents.agent_id"))
    total_capacity = Column(Integer, default=0)
    used_capacity = Column(Integer, default=0)
    workforce_total = Column(Integer, default=0)
    workforce_active = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    agent = relationship("WarehouseAgent", back_populates="capacity")

class Order(Base):
    __tablename__ = "ho_orders"
    
    order_id = Column(String, primary_key=True, index=True)
    destination = Column(String)
    status = Column(String) # PENDING, ALLOCATED, COMPLETED
    priority = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrderItem(Base):
    __tablename__ = "ho_order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("ho_orders.order_id"))
    product_id = Column(String)
    quantity = Column(Integer)

class AllocationRecommendation(Base):
    __tablename__ = "ho_allocation_recommendations"
    
    recommendation_id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("ho_orders.order_id"))
    warehouse_id = Column(String)
    score = Column(Float)
    reasoning = Column(String)
    status = Column(String) # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentCommand(Base):
    __tablename__ = "ho_agent_commands"
    
    command_id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, ForeignKey("ho_warehouse_agents.agent_id"))
    command_type = Column(String)
    payload = Column(JSON)
    status = Column(String) # PENDING, SENT, ACCEPTED, REJECTED, COMPLETED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
