from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.core import get_db
from models.core import WarehouseAgent, InventorySnapshot

router = APIRouter()

@router.get("/")
def get_warehouses(db: Session = Depends(get_db)):
    agents = db.query(WarehouseAgent).all()
    res = []
    for a in agents:
        res.append({
            "warehouse_id": a.warehouse_id,
            "agent_id": a.agent_id,
            "status": a.status,
            "last_heartbeat": a.last_heartbeat,
            "capabilities": a.capabilities
        })
    return res

@router.get("/{warehouse_id}")
def get_warehouse_details(warehouse_id: str, db: Session = Depends(get_db)):
    agent = db.query(WarehouseAgent).filter(WarehouseAgent.warehouse_id == warehouse_id).first()
    if not agent:
        return {"error": "Not found"}
        
    return {
        "warehouse_id": agent.warehouse_id,
        "status": agent.status,
        "capacity": {
            "total_capacity": agent.capacity[0].total_capacity if agent.capacity else 0,
            "used_capacity": agent.capacity[0].used_capacity if agent.capacity else 0,
        }
    }

@router.get("/{warehouse_id}/operations")
def get_warehouse_operations(warehouse_id: str):
    import requests
    import os
    backend_url = os.environ.get("WAREHOUSE_BACKEND_URL", "http://backend:8000")
    if warehouse_id == "WH-002":
        backend_url = os.environ.get("WAREHOUSE2_BACKEND_URL", "http://backend-2:8000")
    
    try:
        resp = requests.get(f"{backend_url}/api/head-office/operations", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception as e:
        return []
