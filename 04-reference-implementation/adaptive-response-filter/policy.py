"""
Delivery policy — decides whether a serialized payload should be
returned whole or handed to the chunker.

Kept separate from the chunker itself so the threshold/heuristics can
evolve (e.g. adaptive thresholds, payload-type-aware rules) without
touching the splitting logic.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_THRESHOLD_BYTES = 128_000
DEFAULT_MAX_CHUNK_BYTES = 64_000


@dataclass(frozen=True)
class DeliveryPolicy:
    threshold_bytes: int = DEFAULT_THRESHOLD_BYTES
    max_chunk_bytes: int = DEFAULT_MAX_CHUNK_BYTES

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

    def should_chunk(self, payload: bytes) -> bool:
        return len(payload) >= self.threshold_bytes
