"""
Connection Center - reliability layer.

Wraps every connector call with:
  - dedup/idempotency (dedup_key unique in the message ledger)
  - exponential-backoff retries with jitter
  - a per-connector circuit breaker (open after N failures, half-open probe)
  - dead-lettering of exhausted messages (inspectable & replayable)
"""
import asyncio
import logging
import random
import time
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.db.models import ConnectionMessage

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
BREAKER_THRESHOLD = 5        # consecutive failures before the breaker opens
BREAKER_OPEN_SECONDS = 60


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    """Per-connector circuit breaker state (in-memory; fine for single-node pilot)."""
    def __init__(self, connector_id: str):
        self.connector_id = connector_id
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "CLOSED"
        if time.monotonic() - self.opened_at >= BREAKER_OPEN_SECONDS:
            return "HALF_OPEN"
        return "OPEN"

    def check(self):
        if self.state == "OPEN":
            raise CircuitOpenError(
                f"Circuit OPEN for connector {self.connector_id} "
                f"(cooldown {BREAKER_OPEN_SECONDS}s)"
            )
        # HALF_OPEN lets one probe through

    def record_success(self):
        self.consecutive_failures = 0
        self.opened_at = None

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= BREAKER_THRESHOLD:
            self.opened_at = time.monotonic()


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(connector_id: str) -> CircuitBreaker:
    if connector_id not in _breakers:
        _breakers[connector_id] = CircuitBreaker(connector_id)
    return _breakers[connector_id]


async def call_with_reliability(
    db: Session,
    connector_id: str,
    direction: str,
    dedup_key: str,
    payload: dict,
    call: Callable[[], "asyncio.Future"],
) -> ConnectionMessage:
    """
    Execute an outbound/inbound connector call with dedup, retries,
    circuit breaking and dead-lettering. Returns the ledger row.
    """
    # Dedup: same dedup_key is never executed twice
    msg = db.query(ConnectionMessage).filter(ConnectionMessage.dedup_key == dedup_key).first()
    if msg:
        return msg

    msg = ConnectionMessage(
        connector_id=connector_id, direction=direction,
        dedup_key=dedup_key, payload=payload, status="PENDING",
    )
    db.add(msg)
    db.commit()

    breaker = get_breaker(connector_id)
    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            breaker.check()
        except CircuitOpenError:
            msg.status = "DEAD_LETTER"
            msg.last_error = "circuit open"
            db.commit()
            return msg
        try:
            result = await call()
            breaker.record_success()
            msg.status = "DELIVERED" if direction == "OUTBOUND" else "PROCESSED"
            msg.attempts = attempt + 1
            msg.confirmed_at = datetime.utcnow()
            db.commit()
            return msg
        except Exception as e:  # retryable
            breaker.record_failure()
            attempt += 1
            msg.attempts = attempt
            msg.last_error = str(e)
            db.commit()
            if attempt > MAX_RETRIES:
                break
            backoff = min(2 ** attempt, 30) + random.uniform(0, 0.5)
            logger.warning(f"[CC] {connector_id} attempt {attempt} failed: {e}. Retry in {backoff:.1f}s")
            await asyncio.sleep(backoff)

    msg.status = "DEAD_LETTER"
    db.commit()
    logger.error(f"[CC] {connector_id} exhausted retries, message dead-lettered: {dedup_key}")
    return msg


def list_dead_letters(db: Session, connector_id: Optional[str] = None) -> list:
    q = db.query(ConnectionMessage).filter(ConnectionMessage.status == "DEAD_LETTER")
    if connector_id:
        q = q.filter(ConnectionMessage.connector_id == connector_id)
    return q.order_by(ConnectionMessage.created_at.desc()).all()


def replay_dead_letter(db: Session, message_id: int) -> ConnectionMessage:
    msg = db.query(ConnectionMessage).filter(
        ConnectionMessage.id == message_id, ConnectionMessage.status == "DEAD_LETTER"
    ).first()
    if not msg:
        raise ValueError(f"Dead-letter {message_id} not found")
    msg.status = "PENDING"
    msg.attempts = 0
    msg.last_error = None
    msg.dedup_key = f"{msg.dedup_key}:replayed:{datetime.utcnow().timestamp()}"
    db.commit()
    return msg
