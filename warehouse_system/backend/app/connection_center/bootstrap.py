"""
Connection Center bootstrap: registers the connectors for the pilot site.

Everything that enters or leaves the system (WMS, head office, LLM gateway)
is a connector listed here. Config over code: adding a second warehouse is a
new registry entry, not new code.
"""
import os
from .registry import registry, ConnectionConfig
from .adapters.wms_adapter import MockWMSAdapter


def init_default_connectors():
    wms_url = os.getenv("WMS_BASE_URL", "http://mock-wms:9000")
    registry.register(
        ConnectionConfig(
            connector_id="wms_primary",
            type="wms",
            direction="bidirectional",
            base_url=wms_url,
            auth_method="api_key",
            capabilities=["inventory.read", "tasks.read", "tasks.write", "events.subscribe"],
            limits={"rps": 20, "timeout_ms": 8000},
            status="active",
        ),
        MockWMSAdapter(wms_url),
    )
    registry.register(
        ConnectionConfig(
            connector_id="head_office",
            type="head_office",
            direction="inbound",
            base_url=os.getenv("HEAD_OFFICE_BASE_URL", "http://localhost:8001"),
            auth_method="token_header",
            capabilities=["instructions.receive"],
            limits={"rps": 10},
            status="active",
        ),
        MockWMSAdapter(os.getenv("HEAD_OFFICE_BASE_URL", "http://localhost:8001")),
    )
    registry.register(
        ConnectionConfig(
            connector_id="llm_gateway",
            type="llm",
            direction="outbound",
            base_url="https://integrate.api.nvidia.com/v1",
            auth_method="api_key",
            capabilities=["chat.completions"],
            limits={"rps": 5, "cost_cap_usd_per_day": 10},
            status="active" if os.getenv("NVIDIA_API_KEY") else "unconfigured",
        ),
        MockWMSAdapter("https://integrate.api.nvidia.com/v1"),
    )
    return registry
