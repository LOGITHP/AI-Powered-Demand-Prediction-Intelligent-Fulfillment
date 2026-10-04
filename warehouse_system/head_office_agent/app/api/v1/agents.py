import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.core import get_db
from models.core import WarehouseAgent, InventorySnapshot, WarehouseCapacity
from schemas.core import AgentRegisterRequest, AgentRegisterResponse, HeartbeatRequest, AgentEventRequest, CommandAckRequest
from typing import Dict, Any

router = APIRouter()

@router.post("/register", response_model=AgentRegisterResponse)
def register_agent(req: AgentRegisterRequest, db: Session = Depends(get_db)):
    agent = db.query(WarehouseAgent).filter(WarehouseAgent.agent_id == req.agent_id).first()
    if not agent:
        agent = WarehouseAgent(
            agent_id=req.agent_id,
            warehouse_id=req.warehouse_id,
            version=req.agent_version,
            capabilities=req.capabilities,
            status="ONLINE",
            last_heartbeat=datetime.datetime.utcnow()
        )
        db.add(agent)
    else:
        agent.status = "ONLINE"
        agent.last_heartbeat = datetime.datetime.utcnow()
        agent.version = req.agent_version
        agent.capabilities = req.capabilities
    
    db.commit()
    return AgentRegisterResponse(
        agent_id=agent.agent_id,
        warehouse_id=agent.warehouse_id,
        status="REGISTERED",
        heartbeat_interval=30
    )

@router.post("/heartbeat")
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)):
    agent = db.query(WarehouseAgent).filter(WarehouseAgent.agent_id == req.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not registered")
    
    agent.status = req.status
    agent.last_heartbeat = req.timestamp
    db.commit()
    return {"status": "ok"}

@router.post("/events")
def handle_event(req: AgentEventRequest, db: Session = Depends(get_db)):
    agent = db.query(WarehouseAgent).filter(WarehouseAgent.agent_id == req.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not registered")
    
    if req.event_type == "INVENTORY_UPDATED":
        # payload has product_id, available_quantity, reserved_quantity
        payload = req.payload
        product_id = payload.get("product_id")
        inv = db.query(InventorySnapshot).filter(
            InventorySnapshot.agent_id == agent.agent_id,
            InventorySnapshot.product_id == product_id
        ).first()
        
        if not inv:
            inv = InventorySnapshot(agent_id=agent.agent_id, product_id=product_id)
            db.add(inv)
        
        inv.available_quantity = payload.get("available_quantity", inv.available_quantity)
        inv.reserved_quantity = payload.get("reserved_quantity", inv.reserved_quantity)
        
    elif req.event_type == "CAPACITY_UPDATED":
        payload = req.payload
        cap = db.query(WarehouseCapacity).filter(WarehouseCapacity.agent_id == agent.agent_id).first()
        if not cap:
            cap = WarehouseCapacity(agent_id=agent.agent_id)
            db.add(cap)
            
        cap.total_capacity = payload.get("total_capacity", cap.total_capacity)
        cap.used_capacity = payload.get("used_capacity", cap.used_capacity)
        cap.workforce_total = payload.get("workforce_total", cap.workforce_total)
        cap.workforce_active = payload.get("workforce_active", cap.workforce_active)
        
    db.commit()
    return {"status": "ok"}

@router.post("/command-ack")
def command_ack(req: CommandAckRequest, db: Session = Depends(get_db)):
    # Assuming AgentCommand exists
    from models.core import AgentCommand
    cmd = db.query(AgentCommand).filter(AgentCommand.command_id == req.command_id).first()
    if cmd:
        cmd.status = req.status
        db.commit()
    return {"status": "ok"}
