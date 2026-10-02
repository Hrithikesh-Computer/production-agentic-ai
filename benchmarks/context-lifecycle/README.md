# Context lifecycle benchmark

This benchmark evaluates a small synthetic task set comparing different context retention policies.

## Policies compared

- full history
- sliding window
- summary / hybrid lifecycle policy

## Metrics

- task success rate
- token usage
- staleness errors
- repeated decisions
- reconstructability of required facts
- context noise

## What it measures

This benchmark tests whether context retention policy preserves the information that matters while avoiding stale or noisy retention. It is intentionally synthetic and fully reproducible.

## How to run

```bash
python benchmarks/context-lifecycle/benchmark.py
```

## Interpretation

This is a controlled local experiment designed to compare retention strategies under a fixed set of agent-like task conditions. It is not a production memory benchmark and should not be interpreted as proof of a deployed system's behavior.
