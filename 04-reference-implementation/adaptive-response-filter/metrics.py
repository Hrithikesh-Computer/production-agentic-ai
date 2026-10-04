"""Sender metrics and fixed-cardinality receiver outcomes for the local slice."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Callable


@dataclass
class DeliveryMetrics:
    payload_size: int
    chunk_count: int
    serialization_ms: float

    def as_dict(self) -> dict:
        return asdict(self)


class ReceiverOutcome(str, Enum):
    SESSION_CAP_REJECTED = "session_cap_rejected"
    ACTIVE_PAYLOAD_CAP_REJECTED = "active_payload_cap_rejected"
    MESSAGE_LIMIT_REJECTED = "message_limit_rejected"
    SESSION_EXPIRED = "session_expired"
    TOMBSTONE_EVICTED = "tombstone_evicted"
    ENVELOPE_INTEGRITY_REJECTED = "envelope_integrity_rejected"
    AUTHENTICATION_REJECTED = "authentication_rejected"
    RETRY_CALLBACK_FAILED = "retry_callback_failed"
    FULL_BUFFER_CALLBACK_FAILED = "full_buffer_callback_failed"
    NDJSON_DECODER_POISONED = "ndjson_decoder_poisoned"


@dataclass(frozen=True)
class ReceiverOutcomeEvent:
    outcome: ReceiverOutcome

    def as_dict(self) -> dict[str, str]:
        return {"outcome": self.outcome.value}


class Timer:
    """Small helper for measuring wall-clock durations in milliseconds."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000


def emit(metrics: DeliveryMetrics, sink: Callable[[dict], None] = print) -> None:
    """Send metrics to a sink. Defaults to printing for local/dev use."""
    sink(metrics.as_dict())


def emit_receiver_outcome(
    outcome: ReceiverOutcome,
    sink: Callable[[dict[str, str]], None] = print,
) -> None:
    """Emit a fixed-cardinality receiver outcome without request data."""
    sink(ReceiverOutcomeEvent(outcome).as_dict())
