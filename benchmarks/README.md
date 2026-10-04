# Benchmarks and evidence layer

This directory hosts the repository's reproducible evidence layer. The goal is not to turn this repository into a production platform or framework; it is to make the strongest engineering claims testable under a controlled local methodology.

## Scope

The evidence artifacts are intentionally narrow:

- response-delivery local overhead and paced-browser experiments

## Benchmark command map

```bash
# response delivery
python benchmarks/response-delivery/benchmark.py
python benchmarks/response-delivery/browser_benchmark.py

# bounded authority policy evaluator tests
python -m pytest -q tests/test_authority_policy.py
```

## Evidence posture

The response-delivery script reports matched-payload local implementation timings. Its browser harness measures first-visible, full-render, and long-task behavior over a size sweep using a paced loopback server. The authority tests cover a small implemented evaluator. None of these outputs is production deployment evidence, and no context-lifecycle benchmark is currently implemented.

The response-delivery directory contains:

- a short README
- a runnable script
- methodology and interpretation notes
- clear caveats about what is and is not measured
