from typing import Optional, Dict
from abc import ABC, abstractmethod
from state.models import NetworkState, WarehouseState

class NetworkStateRepository(ABC):
    @abstractmethod
    def get_state(self) -> NetworkState:
        pass

    @abstractmethod
    def save_state(self, state: NetworkState) -> None:
        pass

class InMemoryNetworkStateRepository(NetworkStateRepository):
    def __init__(self):
        self._state = NetworkState()

    def get_state(self) -> NetworkState:
        return self._state

    def save_state(self, state: NetworkState) -> None:
        self._state = state
