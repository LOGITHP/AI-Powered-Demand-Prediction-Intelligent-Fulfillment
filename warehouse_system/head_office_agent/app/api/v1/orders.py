import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.core import get_db
from models.core import Order, OrderItem, AllocationRecommendation, WarehouseAgent, InventorySnapshot
from schemas.core import OrderAllocateRequest, RecommendationApproveRequest
import datetime

router = APIRouter()

@router.get("/")
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return [{"order_id": o.order_id, "status": o.status, "destination": o.destination} for o in orders]

@router.post("/{order_id}/allocate")
def generate_allocation_recommendation(order_id: str, req: OrderAllocateRequest, db: Session = Depends(get_db)):
    # Create the order if it doesn't exist
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        order = Order(
            order_id=order_id,
            destination=req.destination,
            status="PENDING",
            priority=req.priority
        )
        db.add(order)
        db.commit()
        
        for item in req.items:
            db.add(OrderItem(order_id=order_id, product_id=item.product_id, quantity=item.quantity))
        db.commit()
    
    # Run the rule-based warehouse selection engine
    # We will score warehouses based on inventory availability and other factors
    agents = db.query(WarehouseAgent).filter(WarehouseAgent.status == "ONLINE").all()
    
    scored_warehouses = []
    for agent in agents:
        score = 0.0
        reasons = []
        
        # Check inventory
        has_all_items = True
        for item in req.items:
            inv = db.query(InventorySnapshot).filter(
                InventorySnapshot.agent_id == agent.agent_id,
                InventorySnapshot.product_id == item.product_id
            ).first()
            if not inv or (inv.available_quantity - inv.reserved_quantity) < item.quantity:
                has_all_items = False
                reasons.append(f"Insufficient stock for {item.product_id}")
            else:
                score += 30.0 # arbitrary inventory score
                reasons.append(f"Stock available for {item.product_id}")
                
        if has_all_items:
            # We can factor in distance, capacity etc here
            if agent.capacity:
                cap = agent.capacity[0]
                if cap.total_capacity > 0:
                    util = cap.used_capacity / cap.total_capacity
                    score += (1.0 - util) * 20.0
                    reasons.append(f"Capacity utilization {(util*100):.1f}%")
            
            scored_warehouses.append({
                "warehouse_id": agent.warehouse_id,
                "agent_id": agent.agent_id,
                "score": score,
                "reasons": reasons
            })
            
    if not scored_warehouses:
        return {"status": "FAILED", "detail": "No eligible warehouses found with sufficient inventory."}
        
    scored_warehouses.sort(key=lambda x: x["score"], reverse=True)
    best = scored_warehouses[0]
    
    rec_id = f"rec-{uuid.uuid4().hex[:8]}"
    rec = AllocationRecommendation(
        recommendation_id=rec_id,
        order_id=order_id,
        warehouse_id=best["warehouse_id"],
        score=best["score"],
        reasoning=", ".join(best["reasons"]),
        status="PENDING"
    )
    db.add(rec)
    db.commit()
    
    return {
        "recommendation_id": rec_id,
        "recommended_warehouse": best["warehouse_id"],
        "score": best["score"],
        "reasons": best["reasons"],
        "alternatives": scored_warehouses[1:]
    }

@router.post("/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: str, db: Session = Depends(get_db)):
    rec = db.query(AllocationRecommendation).filter(AllocationRecommendation.recommendation_id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
        
    rec.status = "APPROVED"
    
    order = db.query(Order).filter(Order.order_id == rec.order_id).first()
    if order:
        order.status = "ALLOCATED"
        
    # Find the agent
    agent = db.query(WarehouseAgent).filter(WarehouseAgent.warehouse_id == rec.warehouse_id).first()
    
    # Dispatch command
    if agent:
        from models.core import AgentCommand
        cmd_id = f"cmd-{uuid.uuid4().hex[:8]}"
        cmd = AgentCommand(
            command_id=cmd_id,
            agent_id=agent.agent_id,
            command_type="ALLOCATE_ORDER",
            payload={"order_id": order.order_id},
            status="PENDING"
        )
        db.add(cmd)
        
        # Send HTTP POST to Warehouse Agent
        import requests
        try:
            requests.post(f"http://backend:8000/agents/{agent.agent_id}/commands", json={
                "command_id": cmd_id,
                "command_type": "ALLOCATE_ORDER",
                "warehouse_id": agent.warehouse_id,
                "order_id": order.order_id,
                "priority": order.priority
            }, timeout=2)
            cmd.status = "SENT"
        except Exception as e:
            print(f"Failed to send command to agent: {e}")
        
    db.commit()
    return {"status": "Command Dispatched", "command_id": cmd_id if agent else None}
