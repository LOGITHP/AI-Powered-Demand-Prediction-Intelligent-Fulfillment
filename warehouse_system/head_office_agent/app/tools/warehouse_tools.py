from typing import Dict, Any, List
from state.manager import StateManager
from communication.interface import CommunicationAdapter, MessageType

class WarehouseTools:
    def __init__(self, state_manager: StateManager, comm_adapter: CommunicationAdapter):
        self.state_manager = state_manager
        self.comm_adapter = comm_adapter

    def get_warehouse_state(self, warehouse_id: str) -> Dict[str, Any]:
        """Returns the state of a specific warehouse."""
        wh_state = self.state_manager.get_warehouse_state(warehouse_id)
        if not wh_state:
            return {"error": f"Warehouse {warehouse_id} not found."}
        return wh_state.model_dump()

    def get_high_risk_warehouses(self) -> List[Dict[str, Any]]:
        """Returns warehouses with a risk score above a certain threshold (e.g., 0.7)."""
        state = self.state_manager.get_network_state()
        return [
            {"warehouse_id": wh_id, "risk_score": wh_state.risk_score}
            for wh_id, wh_state in state.warehouses.items()
            if wh_state.risk_score > 0.7
        ]

    def send_message_to_warehouse(self, warehouse_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a specific message/command to a warehouse."""
        try:
            m_type = MessageType(message_type)
        except ValueError:
            return {"error": f"Invalid message type: {message_type}"}
        
        return self.comm_adapter.send_message_to_warehouse(warehouse_id, m_type, payload)

    def request_warehouse_update(self, warehouse_id: str) -> Dict[str, Any]:
        """Requests an immediate status update from a warehouse."""
        return self.send_message_to_warehouse(warehouse_id, "STATUS_REQUEST", {})
