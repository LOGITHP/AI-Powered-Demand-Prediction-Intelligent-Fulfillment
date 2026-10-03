from typing import Dict, Protocol, Any, Callable
from pydantic import BaseModel

class ConnectionConfig(BaseModel):
    connector_id: str
    type: str
    direction: str
    base_url: str
    auth_method: str
    capabilities: list[str]
    limits: dict
    status: str

class BaseConnector(Protocol):
    async def fetch(self, resource: str, since: str = None) -> list[Any]: ...
    async def push(self, payload: dict, idempotency_key: str) -> bool: ...
    async def subscribe(self, handler: Callable) -> None: ...
    async def health(self) -> dict: ...

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._configs: Dict[str, ConnectionConfig] = {}
        
    def register(self, config: ConnectionConfig, adapter: BaseConnector):
        self._configs[config.connector_id] = config
        self._connectors[config.connector_id] = adapter
        
    def get_connector(self, connector_id: str) -> BaseConnector:
        if connector_id not in self._connectors:
            raise ValueError(f"Connector {connector_id} not found")
        return self._connectors[connector_id]
        
    def get_config(self, connector_id: str) -> ConnectionConfig:
        return self._configs.get(connector_id)
        
    def list_connectors(self):
        return list(self._configs.values())

# Global registry instance
registry = ConnectorRegistry()
