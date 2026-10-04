from __future__ import annotations

import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF_IMPL = ROOT / "04-reference-implementation" / "adaptive-response-filter"
if str(REF_IMPL) not in sys.path:
    sys.path.insert(0, str(REF_IMPL))

from filter import (  # noqa: E402  # type: ignore[import-not-found]
    AdaptiveResponseFilter,
)
from reassembler import Reassembler  # noqa: E402  # type: ignore[import-not-found]

AUTH_KEY = b"response-delivery-benchmark-key"


@dataclass
class ScenarioResult:
    payload_size: int
    mode: str
    chunk_count: int
    build_ms: float
    reassembly_ms: float | None
    payload_correct: bool


def _make_payload(size_bytes: int) -> str:
    item_count = max(1, size_bytes // 90)
    while True:
        payload = {
            f"item-{index}": {
                "id": index,
                "name": f"item-{index}",
                "payload": "x" * 32,
            }
            for index in range(item_count)
        }
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) >= size_bytes:
            return serialized
        item_count += max(1, (size_bytes - len(serialized)) // 90)


def _run_case(payload: str, mode: str, chunk_size: int) -> ScenarioResult:
    payload_bytes = payload.encode("utf-8")
    threshold = len(payload_bytes) + 1 if mode == "full" else 1
    filter_obj = AdaptiveResponseFilter(
        threshold_bytes=threshold,
        max_chunk_bytes=chunk_size,
        authentication_key=AUTH_KEY,
    )

    start = time.perf_counter()
    built = filter_obj.build(payload)
    build_ms = (time.perf_counter() - start) * 1000

    if mode == "full":
        if built.mode != "full":
            raise AssertionError("full policy unexpectedly selected chunking")
        return ScenarioResult(
            payload_size=len(payload_bytes),
            mode="full",
            chunk_count=1,
            build_ms=build_ms,
            reassembly_ms=None,
            payload_correct=built.payload.encode("utf-8") == payload_bytes,
        )

    if built.mode != "chunked":
        raise AssertionError("chunked policy unexpectedly selected full delivery")
    chunk_count = len(built.chunks)
    receiver = Reassembler(authentication_key=AUTH_KEY)
    start = time.perf_counter()
    merged = None
    for chunk in reversed(built.chunks):
        merged = receiver.add_chunk(chunk)
    reassembly_ms = (time.perf_counter() - start) * 1000
    if merged is None:
        raise AssertionError("receiver did not complete after all chunks arrived")
    if built.chunks[0].merge_mode == "json-object":
        payload_correct = json.loads(merged) == json.loads(payload_bytes)
    else:
        payload_correct = merged == payload_bytes

    return ScenarioResult(
        payload_size=len(payload_bytes),
        mode="chunked",
        chunk_count=chunk_count,
        build_ms=build_ms,
        reassembly_ms=reassembly_ms,
        payload_correct=payload_correct,
    )


def _summarize(results: list[ScenarioResult]) -> dict[str, float | int | str]:
    build_times = [result.build_ms for result in results]
    reassembly_times = [
        result.reassembly_ms
        for result in results
        if result.reassembly_ms is not None
    ]
    return {
        "payload_size": results[0].payload_size,
        "mode": results[0].mode,
        "median_build_ms": statistics.median(build_times),
        "max_build_ms": max(build_times),
        "median_reassembly_ms": statistics.median(reassembly_times)
        if reassembly_times
        else "not-applicable",
        "max_reassembly_ms": max(reassembly_times)
        if reassembly_times
        else "not-applicable",
        "median_chunk_count": statistics.median(
            result.chunk_count for result in results
        ),
        "payload_correct": all(result.payload_correct for result in results),
    }


def main() -> None:
    sizes = [10_000, 50_000, 150_000, 300_000]
    chunk_size = 16_000
    rows: list[dict[str, float | int | str]] = []

    for payload_size in sizes:
        payload = _make_payload(payload_size)
        for mode in ("full", "chunked"):
            for _ in range(5):
                _run_case(payload, mode, chunk_size)
            results = [
                _run_case(payload, mode, chunk_size) for _ in range(30)
            ]
            rows.append(_summarize(results))

    print(
        "payload_size,mode,median_build_ms,max_build_ms,median_reassembly_ms,max_reassembly_ms,median_chunk_count,payload_correct"
    )
    for row in rows:
        print(
            f"{row['payload_size']},{row['mode']},{row['median_build_ms']},{row['max_build_ms']},{row['median_reassembly_ms']},{row['max_reassembly_ms']},{row['median_chunk_count']},{row['payload_correct']}"
        )

    output_path = Path(__file__).with_name("results.csv")
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(
            "payload_size,mode,median_build_ms,max_build_ms,median_reassembly_ms,max_reassembly_ms,median_chunk_count,payload_correct\n"
        )
        for row in rows:
            handle.write(
                f"{row['payload_size']},{row['mode']},{row['median_build_ms']},{row['max_build_ms']},{row['median_reassembly_ms']},{row['max_reassembly_ms']},{row['median_chunk_count']},{row['payload_correct']}\n"
            )

    print(f"\nCSV saved to: {output_path}")
    print(
        "\nPaired same-payload local policy timings only; no browser, network, "
        "or production delivery measurements."
    )


if __name__ == "__main__":
    main()
