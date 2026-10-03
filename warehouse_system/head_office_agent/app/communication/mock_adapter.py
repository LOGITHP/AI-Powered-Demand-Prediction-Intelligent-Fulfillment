from communication.interface import CommunicationAdapter, MessageType
from typing import Dict, Any

class MockCommunicationAdapter(CommunicationAdapter):
    def __init__(self):
        self.message_log = []

    def send_message_to_warehouse(self, warehouse_id: str, message_type: MessageType, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.message_log.append({
            "warehouse_id": warehouse_id,
            "message_type": message_type.value,
            "payload": payload
        })
        
        # Simulate an acknowledgement response
        return {
            "status": "SUCCESS",
            "message": f"Message of type {message_type.value} received by {warehouse_id}."
        }
