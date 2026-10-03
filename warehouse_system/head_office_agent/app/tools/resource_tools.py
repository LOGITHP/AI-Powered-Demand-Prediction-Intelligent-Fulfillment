from typing import Dict, Any, List
from state.manager import StateManager

class ResourceTools:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def find_resource_surplus(self, resource_type: str) -> List[Dict[str, Any]]:
        """Finds warehouses with a surplus of the given resource (e.g., 'workers')."""
        state = self.state_manager.get_network_state()
        surplus = []
        if resource_type == "workers":
            for wh_id, wh_state in state.warehouses.items():
                if wh_state.workers > wh_state.workers_required:
                    surplus.append({
                        "warehouse_id": wh_id,
                        "available_surplus": wh_state.workers - wh_state.workers_required
                    })
        return surplus

    def find_resource_shortage(self, resource_type: str) -> List[Dict[str, Any]]:
        """Finds warehouses with a shortage of the given resource."""
        state = self.state_manager.get_network_state()
        shortage = []
        if resource_type == "workers":
            for wh_id, wh_state in state.warehouses.items():
                if wh_state.workers < wh_state.workers_required:
                    shortage.append({
                        "warehouse_id": wh_id,
                        "shortage_amount": wh_state.workers_required - wh_state.workers
                    })
        return shortage

    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Identifies network bottlenecks."""
        shortages = self.find_resource_shortage("workers")
        return {
            "worker_bottlenecks": shortages
        }

    def create_resource_allocation_plan(self, source: str, target: str, quantity: int) -> Dict[str, Any]:
        """Drafts a plan to allocate resources between warehouses."""
        return {
            "type": "WORKER_ALLOCATION",
            "source": source,
            "target": target,
            "quantity": quantity,
            "status": "DRAFT"
        }

    def create_inventory_transfer_plan(self, source: str, target: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Drafts a plan to transfer inventory between warehouses."""
        return {
            "type": "INVENTORY_TRANSFER",
            "source": source,
            "target": target,
            "items": items,
            "status": "DRAFT"
        }
