# Production Agentic AI

Building reliable agentic AI systems through engineering investigation, architecture decision-making, and production evidence.

This repository is a research and engineering knowledge base for production agentic AI systems.

Its executable scope is deliberately small: research articles, conceptual Mermaid diagrams, and a tested Python reference slice for adaptive response delivery. It is not a deployed AI platform.

## Scope

This repository studies production AI engineering problems. It is not itself a production AI platform. Articles document engineering reasoning, trade-offs, and investigations. Reference implementations make selected ideas executable and testable. The implementations are intentionally smaller than the systems they represent.

## What this repository covers

- production lessons from agentic systems
- architecture decisions and trade-offs
- context, memory, and retrieval challenges
- response delivery and latency investigations
- reference implementations that accompany the writing

## Current Implementation Boundary

The implemented slice provides delivery policy, UTF-8-safe chunking, validated `WireEnvelope` values with one CRC32 implementation, bounded single-message reassembly, tests, CI, linting, type checking, and a local demo. It serializes the complete response before yielding envelopes; it does not provide true network-level streaming.

There is no FastAPI server, LangGraph runtime, LLM client, database, Redis, PostgreSQL, OpenTelemetry runtime, Docker deployment, browser/client reassembler, or production transport in this repository. Those may appear as research context or future architecture, not as current features or required dependencies.

## Recommended reading path

1. [03-production-lessons/](./03-production-lessons/) for production investigations and lessons learned
2. [01-agent-architecture/](./01-agent-architecture/) for architectural patterns and design trade-offs
3. [02-context-and-memory/](./02-context-and-memory/) for context budgeting and memory-related systems work
4. [04-reference-implementation/](./04-reference-implementation/) for the accompanying implementation examples

## Featured article

- [03-production-lessons/01-adaptive-response-delivery.md](./03-production-lessons/01-adaptive-response-delivery.md) — Large Response Delivery in Agentic AI: A Production Investigation
- [03-production-lessons/02-emr-spark-postgresql-ingestion-optimization.md](./03-production-lessons/02-emr-spark-postgresql-ingestion-optimization.md) — Architecture Optimization for EMR to PostgreSQL Ingestion

## Repository structure

- [README.md](./README.md) — short overview and entry point
- [ROADMAP.md](./ROADMAP.md) — repository scope, standards, and publishing approach
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution process
- [03-production-lessons/](./03-production-lessons/) — production investigations and engineering case studies
- [04-reference-implementation/](./04-reference-implementation/) — code that supports the articles

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
```

## Repository Packaging and Dependency Reality

This repository is intentionally not presented as a reusable installed Python package API. The editable-install metadata in [pyproject.toml](pyproject.toml) declares a lightweight project config with `dependencies = []` and `packages = []` because the code is designed to be read in-place from the repository tree, not distributed as a general-purpose library surface.

This matters for reading the project correctly:

- The actual executed code is the repository's local source tree, especially the modules under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter).
- The repository does not claim to ship a production Python package, a web framework, or a runtime service.
- The project is a documentation and reference-workspace repository first, with a small local implementation slice second.

## How to Read this Repository

This repository is a documentation-led engineering knowledge base. Its primary product is the article narrative, the architecture reasoning, and the evidence trail behind specific engineering decisions. The code in this repository is deliberately smaller than the systems described in the writing and should be read as a faithful educational slice, not a full operational deployment.

Read the articles as engineering arguments and research records, not as API documentation for a complete product. Each article describes a production problem, compares possible approaches, and records a decision. Check the article's status and evidence labels: production observations, local illustrative measurements, hypotheses, and proposed future work are different kinds of evidence and should not be treated as interchangeable.

Use the diagrams as architecture-level explanations of the system being discussed. A diagram may describe a production deployment, a proposed design, or a local simulation that is not present in the repository. Read the title, caption, and neighboring text for the boundary; an arrow to a gateway, browser, model, or external service does not mean that component is implemented here.

The reference implementation is an isolated, pedagogical Python slice. It makes selected policies and contracts executable, but it is not an operational Agentic AI service: it has no model runtime, web server, transport layer, browser client, database, auth system, retry loop, or deployment stack. The code intentionally keeps the wire contract simple for teaching purposes, including a CRC32 checksum instead of authenticated message integrity and a single-request, single-message reassembler with strict validation rules. This is a local protocol exercise, not a production protocol boundary.

Important boundary rule: the repository is not a live AI product, not a deployment environment, and not a monorepo for a production stack. It is a bounded, inspectable implementation of a protocol idea plus a written record of the broader engineering reasoning around it. Any mention of FastAPI, Redis, Pydantic, Postgres, browser clients, gateways, or TypeScript runtimes should be read as future research context or conceptual production architecture unless the file explicitly includes that technology in its current implementation boundary and configuration.

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

The layers complement each other, but they are not interchangeable. A production article may discuss a gateway, streaming UI, or data plane that is not present in the local code; the repository is intentionally an evidence-driven teaching archive rather than a runnable product system.

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

These broader possibilities are valid research ideas and architecture vocabulary, but they are not required to run the repository's local tests, demo, or lint checks. The current execution environment remains intentionally dependency-light and local-only.

The current local reference slice is intentionally narrow. It can be exercised by the checked-in tests and demo without requiring external services. That is deliberate: the repository's executable boundary is the protocol contract and validation logic, not a full platform runtime. The article narrative may describe a larger production environment, but that environment is not the local execution contract in this workspace.

## License

See [LICENSE](./LICENSE).
