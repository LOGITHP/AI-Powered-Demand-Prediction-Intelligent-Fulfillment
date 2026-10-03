import asyncio
import logging
import random
from typing import Callable, Any
from ..registry import BaseConnector

logger = logging.getLogger(__name__)


class MockWMSAdapter(BaseConnector):
    """
    Mock adapter representing an external WMS or legacy system.

    `flake_rate` randomly fails pushes so the reliability layer
    (retries, circuit breaker, dead-letter) can be exercised in demos.
    Call `trip(n)` to force the next n operations to fail deterministically.
    """
    def __init__(self, base_url: str, flake_rate: float = 0.0):
        self.base_url = base_url
        self.flake_rate = flake_rate
        self.forced_failures = 0

    @property
    def is_healthy(self) -> bool:
        return self.forced_failures == 0 and self.flake_rate < 1.0

    def trip(self, times: int = 3):
        """Force the next `times` operations to fail (demo/chaos testing)."""
        self.forced_failures = times

    def _maybe_fail(self):
        if self.forced_failures > 0:
            self.forced_failures -= 1
            raise ConnectionError("WMS temporarily unavailable (forced)")
        if random.random() < self.flake_rate:
            raise ConnectionError("WMS temporarily unavailable (random)")

    async def fetch(self, resource: str, since: str = None) -> list[Any]:
        logger.info(f"[WMS Adapter] Fetching {resource} from {self.base_url}")
        self._maybe_fail()
        await asyncio.sleep(0.1)
        return [{"id": "mock_1", "status": "ok"}]

    async def push(self, payload: dict, idempotency_key: str) -> bool:
        logger.info(f"[WMS Adapter] Pushing payload with key {idempotency_key}: {payload}")
        self._maybe_fail()
        await asyncio.sleep(0.1)
        return True

    async def subscribe(self, handler: Callable) -> None:
        logger.info("[WMS Adapter] Subscribing to events...")
        pass

    async def health(self) -> dict:
        return {"status": "up" if self.is_healthy else "down", "latency_ms": 120}
