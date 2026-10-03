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
        if wh_id and wh_id in simulated_state.warehouses:
            wh = simulated_state.warehouses[wh_id]
            change_percent = scenario.get("demand_change_percent", 0)
            wh.orders = int(wh.orders * (1 + change_percent / 100))
            # Just a mock effect: workers_required increases proportionally
            wh.workers_required = int(wh.workers_required * (1 + change_percent / 100))
            
        return {
            "scenario": scenario,
            "simulated_network_state": simulated_state.model_dump(),
            "impact_analysis": "Simulated state generated successfully."
        }
