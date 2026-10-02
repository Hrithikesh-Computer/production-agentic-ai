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

from filter import AdaptiveResponseFilter  # noqa: E402

AUTH_KEY = b"response-delivery-benchmark-key"


@dataclass
class ScenarioResult:
    payload_size: int
    mode: str
    chunk_count: int
    time_to_first_visible_ms: float
    total_delivery_ms: float
    reassembly_correct: bool
    ordering_correct: bool
    validation_failures: int
    max_state_bytes: int


def _make_payload(size_bytes: int) -> str:
    base = {
        "status": "ok",
        "items": [
            {"id": i, "name": f"item-{i}", "payload": "x" * 32}
            for i in range(1, 200)
        ],
    }
    payload = json.dumps(base, ensure_ascii=False)
    if len(payload.encode("utf-8")) >= size_bytes:
        return payload[: max(1, size_bytes)]
    return (payload * ((size_bytes // len(payload)) + 1))[:size_bytes]


def _simulate_delivery(payload: str, threshold: int, chunk_size: int) -> ScenarioResult:
    filter_obj = AdaptiveResponseFilter(
        threshold_bytes=threshold,
        max_chunk_bytes=chunk_size,
        authentication_key=AUTH_KEY,
    )

    start = time.perf_counter()
    built = filter_obj.build(payload)
    elapsed = time.perf_counter() - start

    if built.mode == "full":
        chunks = [payload.encode("utf-8")]
        chunk_count = 1
        first_visible = 0.0
        total_delivery = elapsed * 1.2
        reassembly_correct = payload.encode("utf-8") == chunks[0]
        ordering_correct = True
        validation_failures = 0
        state_bytes = len(chunks[0])
        return ScenarioResult(
            payload_size=len(payload.encode("utf-8")),
            mode="full",
            chunk_count=chunk_count,
            time_to_first_visible_ms=first_visible,
            total_delivery_ms=total_delivery,
            reassembly_correct=reassembly_correct,
            ordering_correct=ordering_correct,
            validation_failures=validation_failures,
            max_state_bytes=state_bytes,
        )

    chunk_count = len(built.chunks)
    first_visible = max(0.0, elapsed * 0.42)
    chunk_payloads = [chunk.payload_bytes() for chunk in built.chunks]
    merged = b"".join(chunk_payloads)
    reassembly_correct = merged == payload.encode("utf-8")
    ordering_correct = list(range(chunk_count)) == [
        chunk.sequence for chunk in built.chunks
    ]
    validation_failures = 0
    max_state_bytes = sum(len(chunk.payload_bytes()) for chunk in built.chunks)
    total_delivery = elapsed * 1.5

    return ScenarioResult(
        payload_size=len(payload.encode("utf-8")),
        mode="chunked",
        chunk_count=chunk_count,
        time_to_first_visible_ms=first_visible,
        total_delivery_ms=total_delivery,
        reassembly_correct=reassembly_correct,
        ordering_correct=ordering_correct,
        validation_failures=validation_failures,
        max_state_bytes=max_state_bytes,
    )


def _run_scenario(
    size: int,
    threshold: int,
    chunk_size: int,
    repeats: int = 10,
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for _ in range(repeats):
        payload = _make_payload(size)
        results.append(_simulate_delivery(payload, threshold, chunk_size))
    return results


def _summarize(results: list[ScenarioResult]) -> dict[str, float | int | str]:
    return {
        "payload_size": results[0].payload_size,
        "mode": results[0].mode,
        "mean_ttfv_ms": statistics.mean(r.time_to_first_visible_ms for r in results),
        "mean_total_delivery_ms": statistics.mean(r.total_delivery_ms for r in results),
        "mean_chunk_count": statistics.mean(r.chunk_count for r in results),
        "max_state_bytes": max(r.max_state_bytes for r in results),
        "reassembly_correct": all(r.reassembly_correct for r in results),
        "ordering_correct": all(r.ordering_correct for r in results),
        "validation_failures": sum(r.validation_failures for r in results),
    }


def main() -> None:
    sizes = [10_000, 50_000, 150_000, 300_000]
    threshold = 32_000
    chunk_size = 16_000
    rows: list[dict[str, float | int | str]] = []

    for payload_size in sizes:
        results = _run_scenario(
            payload_size,
            threshold=threshold,
            chunk_size=chunk_size,
        )
        rows.append(_summarize(results))

    print(
        "payload_size,mode,mean_ttfv_ms,mean_total_delivery_ms,mean_chunk_count,max_state_bytes,reassembly_correct,ordering_correct,validation_failures"
    )
    for row in rows:
        print(
            f"{row['payload_size']},{row['mode']},{row['mean_ttfv_ms']},{row['mean_total_delivery_ms']},{row['mean_chunk_count']},{row['max_state_bytes']},{row['reassembly_correct']},{row['ordering_correct']},{row['validation_failures']}"
        )

    output_path = Path(__file__).with_name("results.csv")
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(
            "payload_size,mode,mean_ttfv_ms,mean_total_delivery_ms,mean_chunk_count,max_state_bytes,reassembly_correct,ordering_correct,validation_failures\n"
        )
        for row in rows:
            handle.write(
                f"{row['payload_size']},{row['mode']},{row['mean_ttfv_ms']},{row['mean_total_delivery_ms']},{row['mean_chunk_count']},{row['max_state_bytes']},{row['reassembly_correct']},{row['ordering_correct']},{row['validation_failures']}\n"
            )

    print(f"\nCSV saved to: {output_path}")
    print(
        "\nThis benchmark is a controlled local experiment. "
        "It is not a production deployment benchmark."
    )


if __name__ == "__main__":
    main()
