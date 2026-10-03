import uuid
from typing import Dict, Any, List
from decisions.models import Decision
from tools.resource_tools import ResourceTools
from state.manager import StateManager

class DecisionEngine:
    def __init__(self, state_manager: StateManager, resource_tools: ResourceTools):
        self.state_manager = state_manager
        self.resource_tools = resource_tools

    def evaluate_worker_shortage(self, warehouse_id: str) -> Decision | None:
        """Evaluates a worker shortage and generates a decision recommendation."""
        state = self.state_manager.get_warehouse_state(warehouse_id)
        if not state:
            return None
            
        shortage = state.workers_required - state.workers
        if shortage <= 0:
            return None
            
        surplus_warehouses = self.resource_tools.find_resource_surplus("workers")
        
        if not surplus_warehouses:
            return Decision(
                decision_id=str(uuid.uuid4()),
                type="WORKER_ALLOCATION",
                priority="HIGH",
                affected_warehouses=[warehouse_id],
                reasoning=[f"{warehouse_id} has {shortage}-worker shortage.", "No surplus found in network."],
                recommended_actions=[],
                confidence=1.0,
                status="PENDING_APPROVAL"
            )
            
        # Simplistic logic: pick first surplus warehouse that can fulfill the shortage
        source_wh = surplus_warehouses[0]
        qty = min(shortage, source_wh["available_surplus"])
        
        recommendation = self.resource_tools.create_resource_allocation_plan(
            source=source_wh["warehouse_id"],
            target=warehouse_id,
            quantity=qty
        )
        
        reasoning = [
            f"{warehouse_id} has {shortage}-worker shortage.",
            f"{source_wh['warehouse_id']} has {source_wh['available_surplus']} potentially available workers.",
            f"{warehouse_id} has elevated operational risk ({state.risk_score})."
        ]
        
        return Decision(
            decision_id=str(uuid.uuid4()),
            type="WORKER_ALLOCATION",
            priority="HIGH",
            affected_warehouses=[warehouse_id, source_wh["warehouse_id"]],
            reasoning=reasoning,
            recommended_actions=[recommendation],
            confidence=0.85,
            status="PENDING_APPROVAL"
        )
