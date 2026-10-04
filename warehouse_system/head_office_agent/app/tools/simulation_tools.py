from typing import Dict, Any
import copy
from state.manager import StateManager
from state.models import NetworkState

class SimulationTools:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def simulate_action(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate an action without mutating the real state."""
        # 1. Copy current state
        current_state = self.state_manager.get_network_state()
        simulated_state = copy.deepcopy(current_state)

        # 2. Apply hypothetical change
        # Simple simulation: if scenario specifies demand_change_percent
        wh_id = scenario.get("warehouse")
        before = current_state.warehouses.get(wh_id) if wh_id else None
        if wh_id and wh_id in simulated_state.warehouses:
            wh = simulated_state.warehouses[wh_id]
            change_percent = scenario.get("demand_change_percent", 0)
            wh.orders = int(wh.orders * (1 + change_percent / 100))
            # Demand scales required workforce; utilization grows with orders
            wh.workers_required = max(1, int(round(wh.workers_required * (1 + change_percent / 100))))
            wh.capacity_utilization = min(1.0, round(wh.capacity_utilization * (1 + change_percent / 200), 3))
            wh.risk_score = min(1.0, round(wh.risk_score + (change_percent / 100) * 0.3, 3))

            impact_analysis = (
                f"At {wh_id}, a {change_percent}% demand change projects orders "
                f"{before.orders if before else '?'} -> {wh.orders}, required workers "
                f"{before.workers_required if before else '?'} -> {wh.workers_required}, "
                f"capacity utilization {before.capacity_utilization if before else '?'} -> "
                f"{wh.capacity_utilization}, risk score -> {wh.risk_score}."
            )
        else:
            impact_analysis = f"Warehouse '{wh_id}' not found in network state; nothing simulated."

        return {
            "scenario": scenario,
            "simulated_network_state": simulated_state.model_dump(),
            "impact_analysis": impact_analysis
        }
