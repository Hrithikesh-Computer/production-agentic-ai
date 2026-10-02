# Production Agentic AI

Building reliable agentic AI systems through engineering investigation, architecture decision-making, and production evidence.

This repository is a research and engineering knowledge base for production agentic AI systems.

Its executable scope is deliberately small: research articles, conceptual Mermaid diagrams, and a tested Python reference slice for adaptive response delivery. It is not a deployed AI platform.

## Scope

This repository studies production AI engineering problems. It is not itself a production AI platform. Articles document engineering reasoning, trade-offs, and investigations. Reference implementations and experiments support that work without claiming to be a production platform.

## What this repository covers

- production lessons from agentic systems
- architecture decisions and trade-offs
- context, memory, and retrieval challenges
- response delivery and latency investigations
- reference implementations that accompany the writing

## Current Implementation Boundary

The implemented slice provides delivery policy, UTF-8-safe chunking, validated `WireEnvelope` values with one CRC32 implementation, bounded single-message reassembly, tests, CI, linting, type checking, and a demo. It is intentionally narrow and documentation-first.

There is no FastAPI server, LangGraph runtime, LLM client, database, Redis, PostgreSQL, OpenTelemetry runtime, Docker deployment, browser/client reassembler, or production transport in this repository.

## Repository Capability Statement

| Category | Status in this repo | Evidence |
|---|---|---|
| Executable implementation | Local Python reference slice for adaptive response delivery | Tests, demo, and code under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter) |
| Research articles | Documented engineering analysis and trade-off discussions | Markdown articles and diagrams in this repository |
| Conceptual architecture | Pattern sketches and architecture proposals | Design-only material; not backed by a matching runtime in this repo |
| External / absent | EMR, Spark, PostgreSQL/RDS pipelines, production deployments, and cloud service stacks referenced in examples | Not present in the checked-in repository; not measured here |

## Recommended reading path

1. [03-production-lessons/](./03-production-lessons/) for production investigations and lessons learned
2. [01-agent-architecture/](./01-agent-architecture/) for architectural patterns and design trade-offs
3. [01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md](./01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md) — Architecture Optimization for EMR to PostgreSQL Ingestion
4. [01-agent-architecture/03-walkme-workflow-automation-copilot.md](./01-agent-architecture/03-walkme-workflow-automation-copilot.md) — Enterprise Walkthrough & Workflow Automation Copilot
5. [01-agent-architecture/04-fintech-governance-risk-agentic-platform.md](./01-agent-architecture/04-fintech-governance-risk-agentic-platform.md) — Multi-Use Case FinTech Governance & Risk Agentic Platform
6. [02-context-and-memory/](./02-context-and-memory/) for context budgeting and memory-related systems work
7. [04-reference-implementation/](./04-reference-implementation/) for the accompanying implementation examples

## Featured article

- [03-production-lessons/01-adaptive-response-delivery.md](./03-production-lessons/01-adaptive-response-delivery.md) — Large Response Delivery in Agentic AI: A Production Investigation
- [01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md](./01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md) — Architecture Optimization for EMR to PostgreSQL Ingestion
- [01-agent-architecture/03-walkme-workflow-automation-copilot.md](./01-agent-architecture/03-walkme-workflow-automation-copilot.md) — Enterprise Walkthrough & Workflow Automation Copilot

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

# Run the local evidence benchmarks
python benchmarks/response-delivery/benchmark.py
python benchmarks/context-lifecycle/benchmark.py
python -m pytest benchmarks/authority-conformance/test_authority_conformance.py -q
```

## Evidence posture and benchmark layer

This repository is intentionally a reliability-first, architecture-first knowledge base and local reference implementation. It is not a framework, production runtime, or deployed AI platform.

The benchmark layer under [benchmarks/README.md](./benchmarks/README.md) exists to strengthen the strongest ideas without pretending they are production deployment evidence. Every benchmark is designed to be explicit about what is being measured and what remains outside the current evidence boundary.

The repository's strongest public evidence is currently:

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

The reference implementation is an isolated, pedagogical Python slice. It makes selected policies and contracts executable, but it is not an operational Agentic AI service: it has no model runtime, no database, and no serving stack.

Important boundary rule: the repository is not a live AI product, not a deployment environment, and not a monorepo for a production stack. It is a bounded, inspectable implementation of a protocol idea and a research archive.

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

The current local reference slice is intentionally narrow. It can be exercised by the checked-in tests and demo without requiring external services. That is deliberate: the repository's executable boundary is limited to a narrow protocol idea.

## License

See [LICENSE](./LICENSE).
