"""
Metrics — the small set of signals referenced in the article's
Observability section. Kept as a plain dataclass + emit function so it
can be wired into whatever metrics backend a real deployment uses
(StatsD, OpenTelemetry, Prometheus, etc.) without touching the
delivery logic itself.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Callable


@dataclass
class DeliveryMetrics:
    payload_size: int
    chunk_count: int
    serialization_ms: float

    def as_dict(self) -> dict:
        return asdict(self)


class Timer:
    """Small helper for measuring wall-clock durations in milliseconds."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000


def emit(metrics: DeliveryMetrics, sink: Callable[[dict], None] = print) -> None:
    """Send metrics to a sink. Defaults to printing for local/dev use."""
    sink(metrics.as_dict())
