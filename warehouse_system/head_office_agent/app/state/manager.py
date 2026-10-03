from state.models import NetworkState, WarehouseUpdate, WarehouseState
from state.repository import NetworkStateRepository

class StateManager:
    def __init__(self, repository: NetworkStateRepository):
        self.repository = repository

    def get_network_state(self) -> NetworkState:
        return self.repository.get_state()

    def get_warehouse_state(self, warehouse_id: str) -> WarehouseState | None:
        state = self.repository.get_state()
        return state.warehouses.get(warehouse_id)

    def process_warehouse_update(self, update: WarehouseUpdate) -> None:
        state = self.repository.get_state()
        
        # Convert update to warehouse state
        wh_state = WarehouseState(
            status="ACTIVE",
            orders=update.operational_state.orders,
            workers=update.operational_state.workers,
            workers_required=update.predictions.workers_required,
            capacity_utilization=update.operational_state.capacity_utilization,
            risk_score=update.predictions.risk_score,
            predicted_workload=update.predictions.workload
        )
        
        state.warehouses[update.warehouse_id] = wh_state
        self.repository.save_state(state)
