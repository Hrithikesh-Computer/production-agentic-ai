# Production Agentic AI

Engineering analysis and reference implementations for production agentic AI reliability.

## What this is

This is a focused research and reference repository on production agentic AI reliability. It centers on three themes:

- Response-delivery bottlenecks and adaptive chunking
- Context lifecycle management
- Authority and intent semantics beyond simple identity and authorization

It contains reasoned architecture analysis, explicit evidence boundaries, and a narrow, tested local reference implementation: `adaptive-response-filter`.

## What this is not

- Not a production platform, framework, or agent runtime.
- Not a live CRM, EMR, governance, or multi-agent system.
- Not a collection of enterprise design sketches; those are retained under `archive/`.
- Does not claim production measurements or deployed results for illustrative article numbers.

## Current Implementation Boundary

The implemented slice provides delivery policy, UTF-8-safe chunking, validated `WireEnvelope` values with CRC32 and HMAC-SHA256, bounded reassembly, message-scoped timeout/retry/fallback behavior, tests, CI, linting, type checking, and a demo. Session callbacks are local protocol behavior; they are not connected to a production transport.

There is no FastAPI server, LangGraph runtime, LLM client, database, Redis, PostgreSQL, OpenTelemetry runtime, Docker deployment, browser/client reassembler, or production transport in this repository.

## Repository Capability Statement

| Category | Status in this repo | Evidence |
|---|---|---|
| Executable implementation | Local Python reference slice for adaptive response delivery | Tests, demo, and code under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter) |
| Research articles | Documented engineering analysis and trade-off discussions | Markdown articles and diagrams in this repository |
| Conceptual architecture | Authority/intent framing and the canonical ingestion architecture | Design-only material; not backed by a matching runtime in this repo |
| External / absent | EMR, Spark, PostgreSQL/RDS pipelines, production deployments, and cloud service stacks referenced in examples | Not present in the checked-in repository; not measured here |

## Start Here

- [03-production-lessons/01-adaptive-response-delivery.md](./03-production-lessons/01-adaptive-response-delivery.md) — response-delivery bottlenecks and the local implementation boundary
- [02-context-and-memory/01-beyond-token-windows.md](./02-context-and-memory/01-beyond-token-windows.md) — context lifecycle management
- [01-agent-architecture/01-agent-authority-and-intent.md](./01-agent-architecture/01-agent-authority-and-intent.md) — authority and intent semantics
- [04-reference-implementation/](./04-reference-implementation/) — tested `adaptive-response-filter` reference slice

The [EMR-to-PostgreSQL architecture analysis](./01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md) remains available as a separate conceptual article; it is not one of the three flagship themes.

Historical design sketches, evaluations, and dated review records are retained under [archive/](./archive/) and are not current project guidance.

## Repository structure

- [README.md](./README.md) — short overview and entry point
- [ROADMAP.md](./ROADMAP.md) — repository scope, standards, and publishing approach
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution process
- [03-production-lessons/](./03-production-lessons/) — production investigations and engineering case studies
- [04-reference-implementation/](./04-reference-implementation/) — code that supports the articles
- [archive/](./archive/) — historical design sketches, internal evaluations, and review artifacts

## Quick Start

```bash
# Install development dependencies
python -m pip install -e ".[dev]"

# Run tests (pytest testpaths are configured in pyproject.toml)
python -m pytest -q

# Run lint
python -m ruff check .

# Run type checks
python -m mypy 04-reference-implementation/adaptive-response-filter

# Run the reference demo
python 04-reference-implementation/adaptive-response-filter/demo.py

# Run the local evidence benchmarks
python benchmarks/response-delivery/benchmark.py
python benchmarks/context-lifecycle/benchmark.py
python -m pytest benchmarks/authority-conformance/test_authority_conformance.py -q
```

## Evidence posture and benchmark layer

This repository is intentionally a reliability-first, architecture-first knowledge base and local reference implementation. It is not a framework, production runtime, or deployed AI platform.

The evidence layer under [benchmarks/README.md](./benchmarks/README.md) contains bounded local measurements and policy tests, not production deployment evidence. The response-delivery browser harness compares full JSON, gzip full JSON, NDJSON, and gzip NDJSON over server-paced loopback. It has three distinct artifacts: a legacy three-mode standalone HeadlessChrome run, a clean four-mode standalone HeadlessChrome run with a passing Long Task positive control and recorded harness provenance, and a four-mode Electron-embedded run whose Long Task control failed and whose historical provenance is incomplete. The clean standalone and Electron four-mode runs use matching payload sizes; their runtime-specific results should not be conflated. Detailed timing and compression-level results are in the [browser matrix evidence](./benchmarks/response-delivery/browser-matrix-evidence.md).

The repository's strongest local evidence is currently:

- the local adaptive response-delivery implementation and tests under [04-reference-implementation/adaptive-response-filter](./04-reference-implementation/adaptive-response-filter)
- the response-delivery benchmark under [benchmarks/response-delivery](./benchmarks/response-delivery)
- the context-lifecycle benchmark under [benchmarks/context-lifecycle](./benchmarks/context-lifecycle)
- the authority conformance suite under [benchmarks/authority-conformance](./benchmarks/authority-conformance)

These artifacts are intentionally narrow and reproducible. They are not presented as production telemetry, production incident data, or deployed-system benchmarks.

The repository's evidence model is:

- implemented and tested locally: real code + tests + CI
- conceptual and architecture-level: reasoning and design intent
- benchmarked locally under controlled conditions: specific benchmark suites in this repository
- future work / not yet evidenced: production deployment, browser runtime, or fleet-scale data

## Repository Packaging and Dependency Reality

This repository is intentionally not presented as a reusable installed Python package API. The editable-install metadata in [pyproject.toml](pyproject.toml) declares a lightweight project config without claiming a production runtime surface.

This matters for reading the project correctly:

- The actual executed code is the repository's local source tree, especially the modules under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter)
- The repository does not claim to ship a production Python package, a web framework, or a runtime service.
- The project is a documentation and reference-workspace repository first, with a small local implementation slice second.

## How to Read this Repository

This repository is a documentation-led engineering knowledge base. Its primary product is the article narrative, the architecture reasoning, and the evidence trail behind specific engineering decisions.

Read the articles as engineering arguments and research records, not as API documentation for a complete product. Each article describes a production problem, compares possible approaches, and records the trade-offs and evidence behind a decision.

Use the diagrams as architecture-level explanations of the system being discussed. A diagram may describe a production deployment, a proposed design, or a local simulation that is not present in the code.

The reference implementation is an isolated, pedagogical Python slice. It makes selected policies, authenticated envelopes, session recovery, and reassembly contracts executable, but it is not an operational Agentic AI service: it has no model runtime, database, browser client, or serving stack.

Important boundary rule: the repository is not a live AI product, not a deployment environment, and not a monorepo for a production stack. It is a bounded, inspectable reference implementation and a focused research archive.

### Architecture & Presales Evaluation

Any technical or customer-facing evaluation of this repository must follow the evidence-first methodology in [`prompts/architecture-presales-evaluation.md`](./prompts/architecture-presales-evaluation.md).

That document requires clear separation of:

- what is actually present and executable in the repository
- what is only documented
- what is design intent or hypothesis
- what cannot be verified from the reviewed repository

It also prevents unsupported customer claims. Research articles and architecture sketches remain research records; they are not automatically production capabilities.

A useful reading sequence is:

1. Start with the article's problem, hypothesis, evidence, and decision to understand the engineering question.
2. Read its diagrams as the article's conceptual architecture, checking the surrounding text for what is measured, what is illustrative, and what is proposed but not implemented.
3. Open the linked reference modules to inspect only the executable subset; do not infer that an article's production workflow is fully represented by the code.
4. Run the local tests and demo to verify the behavior of that subset. The tests do not reproduce the article's production benchmarks unless the article explicitly says they do.
5. Consult `ROADMAP.md` for the repository scope and the distinction between current dependencies, implemented packages, and future research context.

The repository should be read in three layers:

- Layer 1: articles and engineering analysis
- Layer 2: diagrams and architecture narratives
- Layer 3: local Python reference implementations and their tests

The layers complement each other, but they are not interchangeable. A production article may discuss a gateway, streaming UI, or data plane that is not present in the local code; the repository is intentionally bounded.

### Systemic Context vs. Active Dependencies

The repository has two different kinds of material and they should not be conflated.

Active dependencies in the local execution boundary:

- Python standard library
- pytest, ruff, and mypy for the checked-in dev workflow
- the local source tree under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter)

Systemic context or future-facing ideas that may appear in the article narrative:

- FastAPI or other web-service runtimes
- Pydantic validation layers
- Redis, Postgres, or other persistence queues
- browser client logic and TypeScript transport adapters
- Managed LLM or observability SDKs
- deployment and orchestration infrastructure

These broader possibilities are valid research ideas and architecture vocabulary, but they are not required to run the repository's local tests, demo, or lint checks. The current execution environment is intentionally small.

The current local reference slice is intentionally narrow. It can be exercised by the checked-in tests and demo without requiring external services. Its retry and fallback callbacks model local session behavior; they are not connected to a real transport.

## License

See [LICENSE](./LICENSE).
