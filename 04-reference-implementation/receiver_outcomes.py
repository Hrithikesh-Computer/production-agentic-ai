"""Fixed-cardinality receiver outcomes without request-specific data."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


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


def emit_receiver_outcome(
    outcome: ReceiverOutcome,
    sink: Callable[[dict[str, str]], None] = print,
) -> None:
    """Emit a fixed-cardinality receiver outcome without request data."""
    sink(ReceiverOutcomeEvent(outcome).as_dict())
