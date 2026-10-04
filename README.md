# Production Agentic AI

Engineering analysis and reference implementations for production agentic AI reliability.

## What this is

This is a focused research and reference repository on production agentic AI reliability. It centers on two primary themes, with failure modes treated as a lens across both:

- Agent architecture, including authority and intent as research hypotheses
- Context engineering and lifecycle management

Response delivery is a production failure case used to examine reliability trade-offs, not a third standalone theme. The repository contains explicit evidence boundaries and two narrow, tested local reference slices: the `adaptive-response-filter` protocol example and the bounded authority evaluator.

## What this is not

- Not a production platform, framework, or agent runtime.
- Not a live CRM, EMR, governance, or multi-agent system.
- Not a collection of enterprise design sketches; those are retained under `archive/`.
- Does not claim production measurements or deployed results for the research notes.

## Current Implementation Boundary

The implemented slices include a local authenticated-envelope/reassembly protocol example, a bounded authority evaluator with allow/deny/refer outcomes, an incremental NDJSON decoder, a browser harness for an NDJSON-over-HTTP candidate, and a deterministic CRM approval workflow simulation. The CRM workflow uses in-memory mock records and caller-supplied identities; it is not a live CRM, identity provider, model integration, durable approval service, or production runtime.

The active runtime and dependency boundary is documented once in [ROADMAP.md](./ROADMAP.md#systemic-dependencies--future-research-context) and [04-reference-implementation/README.md](./04-reference-implementation/README.md).

## Repository Capability Statement

| Category | Status in this repo | Evidence |
|---|---|---|
| Executable implementation | Local Python reference slice for adaptive response delivery | Tests, demo, and code under [04-reference-implementation/adaptive-response-filter](04-reference-implementation/adaptive-response-filter) |
| CRM approval workflow simulation | In-memory proposal, human-review, authority recheck, mock update, and JSONL audit sequence | [approval_workflow.py](prototypes/crm_operational_copilot/approval_workflow.py) and focused tests; no live CRM, authenticated identity, or durable state |
| Research articles | Documented engineering analysis and trade-off discussions | Markdown articles and diagrams in this repository |
| Research hypotheses | Context lifecycle and authority/intent analyses | No context-lifecycle benchmark; a small time-bounded authority policy evaluator exists but does not implement semantic alignment |
| External / absent | EMR, Spark, PostgreSQL/RDS pipelines, production deployments, and cloud service stacks referenced in archived examples | Not present in the checked-in repository; not measured here |

## Start Here

- [03-production-lessons/01-adaptive-response-delivery.md](./03-production-lessons/01-adaptive-response-delivery.md) — delivery hypothesis and the local implementation boundary
- [02-context-and-memory/01-beyond-token-windows.md](./02-context-and-memory/01-beyond-token-windows.md) — lifecycle hypothesis; no local implementation or benchmark
- [01-agent-architecture/01-agent-authority-and-intent.md](./01-agent-architecture/01-agent-authority-and-intent.md) — authority and intent research note
- [04-reference-implementation/](./04-reference-implementation/) — tested `adaptive-response-filter` reference slice
- [04-reference-implementation/authority_policy.py](./04-reference-implementation/authority_policy.py) — bounded time-window and priority evaluator
- [04-reference-implementation/ndjson_stream.py](./04-reference-implementation/ndjson_stream.py) — bounded incremental NDJSON object decoder
- [architecture/](./architecture/README.md) — proposed CRM-with-human-approval architecture and its evidence boundaries
- [prototypes/crm_operational_copilot/approval_workflow.py](./prototypes/crm_operational_copilot/approval_workflow.py) — local in-memory approval workflow simulation; no live CRM, identity provider, or model
- [tests/test_authority_referral.py](./tests/test_authority_referral.py) and [prototypes/crm_operational_copilot/test_approval_workflow.py](./prototypes/crm_operational_copilot/test_approval_workflow.py) — referral and workflow behavior tests

The out-of-scope [EMR-to-PostgreSQL architecture analysis](./archive/design-sketches-2026/02-emr-to-postgresql-ingestion-architecture.md) is retained in the design archive.

Historical design sketches, evaluations, and dated review records are retained under [archive/](./archive/) and are not current project guidance.

## How to Review This in 30 Minutes

This is a proposed design plus local simulation, not a deployed CRM product. Use this path to inspect the design and verify one safety control:

1. Read the [solution overview](./architecture/00-solution-overview.md) for the problem, scope, intended outcome, and what is not implemented.
2. Open the [C4 container diagram](./architecture/diagrams/c4-containers.mmd) and follow the [context and containers notes](./architecture/01-context-and-containers.md). The identity provider, CRM, model provider, approval queue, authority gateway, and audit store are proposed components.
3. Read the [three ADRs](./architecture/02-decisions/README.md) and the [authority options analysis](./architecture/03-options-analysis.md) to see alternatives, trade-offs, and provisional choices.
4. Scan the [STRIDE threat model](./architecture/04-threat-model.md), especially the flow IDs for model prompt injection, approval replay, and the recheck-before-write boundary.
5. Run `python prototypes/crm_operational_copilot/approval_workflow.py` and `python -m pytest -q prototypes/crm_operational_copilot/test_approval_workflow.py tests/test_authority_referral.py`. The simulation uses in-memory mock records; 16 workflow test cases cover approval, binding, current requester/reviewer authority, stale records, expiry, and replay, while 7 referral tests cover evaluator, aggregate, session, and ticket behavior.

For deeper discovery, see the [NFR and sizing worksheet](./architecture/05-nfr-and-sizing.md), [AWS deployment candidate](./architecture/06-deployment-views.md), [cost model](./architecture/07-cost-model.md), and [customer questionnaire](./architecture/09-discovery-questionnaire.md). Their assumptions and numbers are provisional, not requirements or quotations.

## Repository structure

- [README.md](./README.md) — short overview and entry point
- [ROADMAP.md](./ROADMAP.md) — repository scope, standards, and publishing approach
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution process
- [03-production-lessons/](./03-production-lessons/) — production investigations and engineering case studies
- [04-reference-implementation/](./04-reference-implementation/) — code that supports the articles
- [benchmarks/](./benchmarks/) — bounded local experiments and their evidence limits
- [prototypes/](./prototypes/) — explicitly scoped mock prototypes
- [diagrams/](./diagrams/) — Mermaid source diagrams
- [prompts/](./prompts/) — reusable research and review prompts
- [templates/](./templates/) — article and engineering templates
- [tests/](./tests/) — behavior tests for the bounded authority evaluator
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
python -m mypy 04-reference-implementation/adaptive-response-filter 04-reference-implementation/authority_policy.py tests/test_authority_policy.py

# Run the authority policy evaluator tests
python -m pytest -q tests/test_authority_policy.py

# Run the local approval workflow simulation and focused tests
python prototypes/crm_operational_copilot/approval_workflow.py
python -m pytest -q prototypes/crm_operational_copilot/test_approval_workflow.py

# Run referral outcome tests
python -m pytest -q tests/test_authority_referral.py

# Run the NDJSON stream decoder tests
python -m pytest -q tests/test_ndjson_stream.py tests/test_ndjson_guards.py

# Run the reference demo
python 04-reference-implementation/adaptive-response-filter/demo.py

# Run the local evidence benchmarks
python benchmarks/response-delivery/benchmark.py

# Run the local browser delivery experiment
python benchmarks/response-delivery/browser_benchmark.py
```

## Evidence posture and benchmark layer

This repository is intentionally a reliability-first, architecture-first knowledge base and local reference implementation. It is not a framework, production runtime, or deployed AI platform.

The evidence layer under [benchmarks/README.md](./benchmarks/README.md) contains bounded local measurements and policy tests, not production deployment evidence. The response-delivery browser harness compares full JSON, gzip full JSON, NDJSON, and gzip NDJSON over server-paced loopback. It has three distinct artifacts: a legacy three-mode standalone HeadlessChrome run, a clean four-mode standalone HeadlessChrome run with a passing Long Task positive control and recorded harness provenance, and a four-mode Electron-embedded run whose Long Task control failed and whose historical provenance is incomplete. The clean standalone and Electron four-mode runs use matching payload sizes; their runtime-specific results should not be conflated. Detailed timing and compression-level results are in the [browser matrix evidence](./benchmarks/response-delivery/browser-matrix-evidence.md).

The repository's strongest local evidence is currently:

- the local adaptive response-delivery implementation and tests under [04-reference-implementation/adaptive-response-filter](./04-reference-implementation/adaptive-response-filter)
- the response-delivery benchmark under [benchmarks/response-delivery](./benchmarks/response-delivery)
- the bounded authority policy evaluator and tests under [04-reference-implementation/authority_policy.py](./04-reference-implementation/authority_policy.py) and [tests/test_authority_policy.py](./tests/test_authority_policy.py)
- the incremental NDJSON decoder and guards under [04-reference-implementation/ndjson_stream.py](./04-reference-implementation/ndjson_stream.py) and [tests/test_ndjson_stream.py](./tests/test_ndjson_stream.py)

These artifacts are intentionally narrow and reproducible. They are not presented as production telemetry, production incident data, or deployed-system benchmarks.

The repository's evidence model is:

- implemented and tested locally: real code + tests + CI
- conceptual and architecture-level: reasoning and design intent
- measured locally under controlled conditions: response-delivery implementation overhead and the paced standalone-browser harness
- no context-lifecycle behavior is currently implemented or tested
- future work / not yet evidenced: production deployment, deployed browser client, or fleet-scale data

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
