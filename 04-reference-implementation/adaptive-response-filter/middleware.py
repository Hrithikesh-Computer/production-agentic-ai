"""
Adaptive Response Delivery — middleware entry point.

This sits between a response builder and the HTTP response writer.
It applies the delivery policy, invokes the chunker when needed,
attaches wire metadata, and records delivery metrics. This is the
file referenced as `filter_response()` in the article.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

from chunker import semantic_split
from metrics import DeliveryMetrics, Timer, emit
from policy import DeliveryPolicy
from reassembler import checksum


def filter_response(
    response: Any,
    policy: DeliveryPolicy | None = None,
) -> Iterator[dict]:
    """
    Decide whether to return `response` whole or split into chunks,
    yielding wire-ready envelopes either way.
    """
    policy = policy or DeliveryPolicy()
    timer = Timer()
    payload = json.dumps(response).encode("utf-8")
    serialization_ms = timer.elapsed_ms()

    if not policy.should_chunk(payload):
        emit(DeliveryMetrics(
            payload_size=len(payload),
            chunk_count=1,
            serialization_ms=serialization_ms,
        ))
        yield _envelope(sequence=0, total=1, payload=payload, is_final=True)
        return

    chunks = semantic_split(payload, policy.max_chunk_bytes)
    total = len(chunks)

    emit(DeliveryMetrics(
        payload_size=len(payload),
        chunk_count=total,
        serialization_ms=serialization_ms,
    ))

    for index, chunk_bytes in enumerate(chunks):
        yield _envelope(
            sequence=index,
            total=total,
            payload=chunk_bytes,
            is_final=(index == total - 1),
        )


def _envelope(sequence: int, total: int, payload: bytes, is_final: bool) -> dict:
    return {
        "sequence": sequence,
        "total_chunks": total,
        "checksum": checksum(payload),
        "is_final": is_final,
        "payload": payload.decode("utf-8", errors="replace"),
    }


if __name__ == "__main__":
    from policy import DeliveryPolicy
    from reassembler import Reassembler

    example_response = {
        "plan": {"steps": ["retrieve", "summarize", "cite"]},
        "tool_output": {"result": "..." * 5000},
        "citations": [{"source": "doc-1", "span": [0, 120]}],
        "metadata": {"model": "example", "latency_ms": 812},
    }

    small_chunk_policy = DeliveryPolicy(threshold_bytes=200, max_chunk_bytes=4_000)
    wire_chunks = list(filter_response(example_response, small_chunk_policy))

    reassembler = Reassembler()
    result = None
    for wire_chunk in wire_chunks:
        result = reassembler.add_chunk(wire_chunk)

    assert result is not None
    print(f"sent {len(wire_chunks)} chunk(s), reassembled {len(result)} bytes")
