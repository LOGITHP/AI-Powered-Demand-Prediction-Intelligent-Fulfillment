import time
import requests
import random
import threading
import datetime
import os

HEAD_OFFICE_URL = os.getenv("HEAD_OFFICE_URL", "http://head-office:8000/api/v1")

AGENTS = [
    {"agent_id": "WH-CHN-AGENT-001", "warehouse_id": "WH-CHENNAI-001"},
    {"agent_id": "WH-BLR-AGENT-001", "warehouse_id": "WH-BANGALORE-001"},
    {"agent_id": "WH-BOM-AGENT-001", "warehouse_id": "WH-MUMBAI-001"}
]

def register_agent(agent):
    try:
        res = requests.post(f"{HEAD_OFFICE_URL}/agents/register", json={
            "agent_id": agent["agent_id"],
            "warehouse_id": agent["warehouse_id"],
            "agent_version": "1.0.0",
            "capabilities": ["inventory", "inbound", "outbound", "workforce"]
        })
        print(f"Registered {agent['agent_id']}: {res.status_code}")
    except Exception as e:
        print(f"Error registering {agent['agent_id']}: {e}")

def send_heartbeat(agent):
    try:
        requests.post(f"{HEAD_OFFICE_URL}/agents/heartbeat", json={
            "agent_id": agent["agent_id"],
            "warehouse_id": agent["warehouse_id"],
            "status": "ONLINE",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    except:
        pass

def send_inventory(agent, product_id, available, reserved):
    try:
        requests.post(f"{HEAD_OFFICE_URL}/agents/events", json={
            "event_id": f"evt-inv-{random.randint(1000, 9999)}",
            "agent_id": agent["agent_id"],
            "warehouse_id": agent["warehouse_id"],
            "event_type": "INVENTORY_UPDATED",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": {
                "product_id": product_id,
                "available_quantity": available,
                "reserved_quantity": reserved
            }
        })
    except:
        pass

def send_capacity(agent, total, used):
    try:
        requests.post(f"{HEAD_OFFICE_URL}/agents/events", json={
            "event_id": f"evt-cap-{random.randint(1000, 9999)}",
            "agent_id": agent["agent_id"],
            "warehouse_id": agent["warehouse_id"],
            "event_type": "CAPACITY_UPDATED",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": {
                "total_capacity": total,
                "used_capacity": used,
                "workforce_total": 50,
                "workforce_active": 45
            }
        })
    except:
        pass

def agent_loop(agent):
    time.sleep(5) # Wait for Head Office to boot
    register_agent(agent)
    
    # Initialize some mock inventory
    products = ["PROD-001", "PROD-002", "PROD-003", "Laptop", "Product X"]
    
    while True:
        send_heartbeat(agent)
        
        # Randomly update inventory for one product
        prod = random.choice(products)
        
        # Hardcode the shortage scenario from the prompt
        if prod == "Product X":
            if agent["warehouse_id"] == "WH-CHENNAI-001":
                send_inventory(agent, "Product X", 20, 0)
            elif agent["warehouse_id"] == "WH-BANGALORE-001":
                send_inventory(agent, "Product X", 30, 0)
            elif agent["warehouse_id"] == "WH-MUMBAI-001":
                send_inventory(agent, "Product X", 10, 0)
        else:
            send_inventory(agent, prod, random.randint(50, 200), random.randint(0, 20))
            
        # Update capacity
        send_capacity(agent, 1000, random.randint(300, 900))
        
        time.sleep(10)

import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI(title="Mock Warehouse Agents")

@app.post("/agents/{agent_id}/commands")
async def receive_command(agent_id: str, request: Request):
    payload = await request.json()
    print(f"[{agent_id}] Received command: {payload}")
    
    # Send ack back
    try:
        requests.post(f"{HEAD_OFFICE_URL}/agents/command-ack", json={
            "command_id": payload.get("command_id", "unknown"),
            "agent_id": agent_id,
            "status": "ACCEPTED",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": "Order allocation accepted"
        })
    except Exception as e:
        print(f"Failed to send ack: {e}")
        
    return {"status": "accepted"}

if __name__ == "__main__":
    threads = []
    for a in AGENTS:
        t = threading.Thread(target=agent_loop, args=(a,), daemon=True)
        t.start()
        threads.append(t)
        
    uvicorn.run(app, host="0.0.0.0", port=8000)
