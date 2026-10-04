"""
Delivery policy — decides whether a serialized payload should be
returned whole or handed to the chunker.

Payloads at or above the byte threshold are chunked.

Kept separate from the chunker itself so the threshold/heuristics can
evolve (e.g. adaptive thresholds, payload-type-aware rules) without
touching the splitting logic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_THRESHOLD_BYTES = 128_000
DEFAULT_MAX_CHUNK_BYTES = 64_000
DEFAULT_TIMEOUT_SECONDS = 1.0
DEFAULT_MAX_RETRIES = 1


@dataclass(frozen=True)
class DeliveryPolicy:
    threshold_bytes: int = DEFAULT_THRESHOLD_BYTES
    max_chunk_bytes: int = DEFAULT_MAX_CHUNK_BYTES
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES

    def __post_init__(self) -> None:
        if isinstance(self.threshold_bytes, bool) or not isinstance(
            self.threshold_bytes, int
        ):
            raise TypeError("threshold_bytes must be an integer")
        if self.threshold_bytes < 0:
            raise ValueError("threshold_bytes must be nonnegative")
        if isinstance(self.max_chunk_bytes, bool) or not isinstance(
            self.max_chunk_bytes, int
        ):
            raise TypeError("max_chunk_bytes must be an integer")
        if self.max_chunk_bytes <= 0:
            raise ValueError("max_chunk_bytes must be positive")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise TypeError("timeout_seconds must be a number")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int):
            raise TypeError("max_retries must be an integer")
        if self.max_retries < 0:
            raise ValueError("max_retries must be nonnegative")

    def should_chunk(self, payload: bytes) -> bool:
        return len(payload) >= self.threshold_bytes
