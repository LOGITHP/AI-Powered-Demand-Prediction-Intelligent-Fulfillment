"""
LangChain tool surface for the Head Office query agent.

Wraps the plain-python network/resource/simulation tools so an LLM agent can
discover and call them via bind_tools(). Every tool returns a JSON string and
never mutates network state - operational changes go through
`request_worker_allocation`, which only creates a PENDING decision that a
human must approve.
"""
import json
import uuid
from datetime import datetime

from langchain_core.tools import tool

from audit.logger import AuditLogger
from state.manager import StateManager
from tools.network_tools import NetworkTools
from tools.resource_tools import ResourceTools
from tools.simulation_tools import SimulationTools


def build_head_office_tools(state_manager: StateManager, audit_logger: AuditLogger):
    network_tools = NetworkTools(state_manager, comm_adapter=None)
    resource_tools = ResourceTools(state_manager)
    simulation_tools = SimulationTools(state_manager)

    @tool
    def get_network_state() -> str:
        """Get a snapshot of every warehouse in the network: orders, workers,
        workers_required, capacity utilization, risk score and predicted workload."""
        return json.dumps(network_tools.get_network_state())

    @tool
    def find_worker_shortages() -> str:
        """List warehouses that currently have fewer workers than required,
        with the size of each shortage."""
        return json.dumps(resource_tools.find_resource_shortage("workers"))

    @tool
    def find_worker_surpluses() -> str:
        """List warehouses with more workers than required, with the surplus amounts."""
        return json.dumps(resource_tools.find_resource_surplus("workers"))

    @tool
    def compare_warehouses() -> str:
        """Compare all warehouses on risk score, capacity utilization and
        worker coverage ratio."""
        return json.dumps(network_tools.compare_warehouses())

    @tool
    def get_active_events() -> str:
        """Get currently active network issues (worker shortages, capacity
        warnings) derived from live warehouse state."""
        return json.dumps(network_tools.get_active_events())

    @tool
    def simulate_demand_change(warehouse_id: str, demand_change_percent: float) -> str:
        """Simulate a demand change at one warehouse and report the projected
        impact on orders and required workers. Does not change real state."""
        result = simulation_tools.simulate_action({
            "warehouse": warehouse_id,
            "demand_change_percent": float(demand_change_percent),
        })
        sim = result.get("simulated_network_state", {}).get("warehouses", {}).get(warehouse_id, {})
        return json.dumps({
            "warehouse_id": warehouse_id,
            "scenario": result.get("scenario"),
            "projected_orders": sim.get("orders"),
            "projected_workers_required": sim.get("workers_required"),
            "projected_capacity_utilization": sim.get("capacity_utilization"),
        })

    @tool
    def request_worker_allocation(source_warehouse: str, target_warehouse: str,
                                  quantity: int, justification: str) -> str:
        """Propose moving workers from one warehouse to another. Creates a
        PENDING decision that a human manager must approve before execution -
        nothing changes until then."""
        quantity = int(quantity)
        if quantity <= 0:
            return json.dumps({"error": "quantity must be positive"})
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        audit_logger.log_decision(
            decision_id=decision_id,
            event="WORKER_ALLOCATION_REQUEST",
            warehouse=target_warehouse,
            tools_called=["request_worker_allocation"],
            recommendation=(f"Move {quantity} workers from {source_warehouse} "
                            f"to {target_warehouse}. Justification: {justification}"),
            reasoning=[
                f"{target_warehouse} needs {quantity} additional workers",
                f"{source_warehouse} is the proposed source",
                f"Agent justification: {justification}",
            ],
            status="PENDING_APPROVAL",
        )
        return json.dumps({
            "decision_id": decision_id,
            "status": "PENDING_APPROVAL",
            "message": (f"Proposal recorded ({decision_id}). A manager must approve it "
                        "on the AI Agent page before any workers move."),
        })

    
    @tool
    def check_fc_inventory(fc_id: str, product_id: str) -> str:
        """Check the available inventory of a product at a specific Fulfillment Center."""
        from database.core import SessionLocal
        from models.core import FCInventory
        db = SessionLocal()
        try:
            item = db.query(FCInventory).filter(FCInventory.fc_id == fc_id, FCInventory.product_id == product_id).first()
            if not item:
                return json.dumps({"status": "error", "message": "Product not found in FC"})
            return json.dumps({
                "fc_id": fc_id,
                "product_id": product_id,
                "available_quantity": item.available_quantity,
                "reserved_quantity": item.reserved_quantity,
                "incoming_quantity": item.incoming_quantity
            })
        finally:
            db.close()
    @tool
    def instruct_warehouse(warehouse_id: str, order_id: str, product_id: str, quantity: int, priority: str = "HIGH", operation: str = "PICK_PACK_SHIP") -> str:
        """Send an instruction to a specific warehouse or fulfillment center to process an order.
        You must provide the order_id, product_id, and quantity.
        """
        import requests
        import uuid
        import os
        backend_url = os.environ.get("WAREHOUSE_BACKEND_URL", "http://backend:8000")
        if warehouse_id == "WH-002":
            backend_url = os.environ.get("WAREHOUSE2_BACKEND_URL", "http://backend-2:8000")
            
        try:
            payload = {
                "instruction_id": f"INST-{uuid.uuid4().hex[:6].upper()}",
                "order_id": order_id,
                "items": [{"sku_id": product_id, "quantity": quantity}],
                "fc": "FC-CHENNAI-001",
                "priority": priority,
                "sla_hours": 24,
                "required_operation": operation
            }

            resp = requests.post(f"{backend_url}/api/head-office/instructions", headers={"x-token": "supersecret-headoffice-token"}, json=payload, timeout=5)
            if resp.status_code == 202 or resp.status_code == 200:
                # Update the order status in the DB
                from database.core import SessionLocal
                from models.core import Order
                db = SessionLocal()
                try:
                    order_obj = db.query(Order).filter(Order.order_id == order_id).first()
                    if order_obj:
                        order_obj.status = "ALLOCATED"
                        db.commit()
                finally:
                    db.close()
                return json.dumps({"status": "success", "message": f"Instruction sent to {warehouse_id} for order {order_id}"})
            return json.dumps({"status": "error", "message": f"Failed to send to warehouse: {resp.text}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Connection error: {str(e)}"})
            
    return [get_network_state, find_worker_shortages, find_worker_surpluses,
            compare_warehouses, get_active_events, simulate_demand_change,
            request_worker_allocation, check_fc_inventory, instruct_warehouse]



