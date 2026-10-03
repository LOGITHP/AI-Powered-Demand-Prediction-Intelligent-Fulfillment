from typing import Dict, Any, List
from state.manager import StateManager
from communication.interface import CommunicationAdapter, MessageType

class NetworkTools:
    def __init__(self, state_manager: StateManager, comm_adapter: CommunicationAdapter):
        self.state_manager = state_manager
        self.comm_adapter = comm_adapter

    def get_network_state(self) -> Dict[str, Any]:
        """Returns the current state of the entire warehouse network."""
        state = self.state_manager.get_network_state()
        return state.model_dump()

    def compare_warehouses(self) -> Dict[str, Any]:
        """Provides a comparative analysis of all warehouses in the network."""
        state = self.state_manager.get_network_state()
        comparisons = {}
        for wh_id, wh_state in state.warehouses.items():
            comparisons[wh_id] = {
                "risk_score": wh_state.risk_score,
                "utilization": wh_state.capacity_utilization,
                "worker_ratio": wh_state.workers / wh_state.workers_required if wh_state.workers_required > 0 else 1.0
            }
        return comparisons

    def get_active_events(self) -> List[Dict[str, Any]]:
        """Returns a list of currently active network-level events or issues."""
        # For simplicity, we derive active events from current state risk and shortages
        events = []
        state = self.state_manager.get_network_state()
        for wh_id, wh_state in state.warehouses.items():
            if wh_state.workers < wh_state.workers_required:
                events.append({"warehouse_id": wh_id, "type": "WORKER_SHORTAGE", "severity": "HIGH" if wh_state.risk_score > 0.7 else "MEDIUM"})
            if wh_state.capacity_utilization > 0.9:
                events.append({"warehouse_id": wh_id, "type": "CAPACITY_WARNING", "severity": "HIGH"})
        return events
