# Response delivery benchmark

This benchmark exercises the repository's real response-delivery implementation in `04-reference-implementation/adaptive-response-filter`.

## What it measures

The benchmark compares a full-buffer pathway against the chunked / adaptive delivery pathway for structured JSON payloads of different sizes.

Measured fields:

- payload size
- chunk count
- time-to-first-visible-content (simulated client timing)
- total delivery latency (simulated client timing)
- reassembly correctness
- ordering correctness
- validation failure count
- memory / state bounds under the local protocol

## What it does not measure

This is not a real browser benchmark, not a production TLS/network measurement, and not a deployed service benchmark. It is a controlled local comparison of the repository's reference delivery logic under deterministic payload sizes.

## How to run

```bash
python benchmarks/response-delivery/benchmark.py
```

## Interpretation

The script reports mean and variance across repeated runs for each size bucket. The benchmark is intended to show the relative shape of the delivery trade-off under bounded local conditions, not to claim production performance.
