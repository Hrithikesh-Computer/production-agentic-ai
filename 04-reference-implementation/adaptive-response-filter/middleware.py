"""Response filter entry point that emits validated wire envelopes."""

from __future__ import annotations

import json
from typing import Any, Iterator

from filter import build_envelopes
from metrics import DeliveryMetrics, Timer, emit
from policy import DeliveryPolicy


def filter_response(
    response: Any,
    policy: DeliveryPolicy | None = None,
) -> Iterator[dict[str, int | str | bool]]:
    """Serialize a response and yield validated envelope mappings."""
    active_policy = policy if policy is not None else DeliveryPolicy()
    timer = Timer()
    payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
    serialization_ms = timer.elapsed_ms()

    envelopes = build_envelopes(payload, active_policy)
    emit(
        DeliveryMetrics(
            payload_size=len(payload),
            chunk_count=len(envelopes),
            serialization_ms=serialization_ms,
        )
    )

    yield from (envelope.to_dict() for envelope in envelopes)
