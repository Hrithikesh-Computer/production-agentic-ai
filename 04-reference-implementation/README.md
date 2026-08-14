# Reference implementation

This folder contains a small Python reference implementation for the adaptive response filtering idea described in the production investigation article.

The goal is not to provide a production-ready transport layer. It is to make the decision policy and the chunking behavior concrete enough to reason about, benchmark, and extend.

## Contents

- [adaptive-response-filter/filter.py](./adaptive-response-filter/filter.py) — a minimal implementation of the delivery-layer filter
- [adaptive-response-filter/demo.py](./adaptive-response-filter/demo.py) — a simple script that demonstrates the full-buffer and chunked paths

## How to run

From the repository root:

```bash
python 04-reference-implementation/adaptive-response-filter/demo.py
```
