from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum

class MessageType(Enum):
    STATUS_REQUEST = "STATUS_REQUEST"
    RESOURCE_REQUEST = "RESOURCE_REQUEST"
    RESOURCE_ALLOCATION_PROPOSAL = "RESOURCE_ALLOCATION_PROPOSAL"
    INVENTORY_TRANSFER_PROPOSAL = "INVENTORY_TRANSFER_PROPOSAL"
    URGENT_ALERT = "URGENT_ALERT"
    TASK_REQUEST = "TASK_REQUEST"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    ACTION_RESULT = "ACTION_RESULT"

class CommunicationAdapter(ABC):
    @abstractmethod
    def send_message_to_warehouse(self, warehouse_id: str, message_type: MessageType, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to a warehouse and optionally return a response."""
        pass

class WarehouseAgentInterface(ABC):
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def receive_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_event(self, event: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def send_prediction(self, prediction: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def acknowledge_command(self, command_id: str) -> bool:
        pass
