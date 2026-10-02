# Repository Map

Inventory snapshot: 2026-10-02. Active material is listed first; archive contents are historical and are not current guidance.

Tags describe the repository evidence currently present, not production readiness:

- `[doc-only]`: Markdown content without a matching local executable implementation.
- `[tested local reference]`: bounded executable behavior with local tests; not a production service.
- `[partial mock prototype]`: limited local mock behavior; no claim of live integration or production readiness.

## Active Flagships

1. [Adaptive response delivery](03-production-lessons/01-adaptive-response-delivery.md) — investigation and tested local protocol slice.
2. [Context lifecycle](02-context-and-memory/01-beyond-token-windows.md) — research and design analysis; no production context manager is included.
3. [Authority and intent](01-agent-architecture/01-agent-authority-and-intent.md) — reasoned security architecture; no matching enforcement runtime is included.
4. [Reference implementation](04-reference-implementation/) — `adaptive-response-filter`, its tests, demo, and evidence boundary.

The [EMR-to-PostgreSQL architecture analysis](01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md) is an additional conceptual article, not a fourth flagship theme.

## Historical Archives

- [Design sketches, archived 2026-10](archive/design-sketches-2026/README.md) — enterprise pattern notes and the relocated EMR stub.
- [Evaluations, archived 2026-10](archive/evaluations-2026/README.md) — internal review/evaluation artifacts.
- [Review artifacts, archived 2026-10](archive/review-artifacts-2026/README.md) — dated reconciliation, authority, cost/performance, audit, and summary records.

## Root

- `CONTRIBUTING.md` [doc-only]
- `LICENSE` (not Markdown)
- `README.md` [entry point]
- `ROADMAP.md` [doc-only]
- `STYLE_GUIDE.md` [doc-only]
- `CONTEXT-LIFECYCLE-DECISION.md` [doc-only]
- `EVIDENCE.md` [doc-only]
- `SECURITY-03.md`, `SECURITY-04.md`, `SECURITY-09.md` [doc-only / local prototype evidence]
- `pyproject.toml` (Python project configuration)

## `01-agent-architecture/`

- `01-agent-authority-and-intent.md` [doc-only]
- `02-emr-to-postgresql-ingestion-architecture.md` [doc-only]

The former design sketches 03-10 are archived in `archive/design-sketches-2026/`; the CRM mock prototype remains under `prototypes/crm_operational_copilot/` with its own evidence boundary.

No source files were found in this directory.

## `02-context-and-memory/`

- `01-beyond-token-windows.md` [doc-only]

No source files were found in this directory.

## `03-production-lessons/`

- `01-adaptive-response-delivery.md` [documented by tested local reference]

The legacy EMR production-lessons stub has been moved to `archive/design-sketches-2026/`. The canonical architecture article remains under `01-agent-architecture/`.

## `04-reference-implementation/`

- `README.md` [tested local reference]

### `04-reference-implementation/adaptive-response-filter/`

- `chunker.py`, `envelope.py`, `filter.py`, `middleware.py`, `policy.py`, `reassembler.py`, `metrics.py`, `demo.py` [tested local reference]
- `test_chunker.py`, `test_envelope.py`, `test_reassembler.py`, `test_reassembly_session.py` [local tests]
- `EVIDENCE.md` [scope, observed behavior, and remaining evidence requirements]

## `prototypes/crm_operational_copilot/`

- `README.md`, `crm_copilot.py`, `test_crm_copilot.py`, `EVIDENCE.md` [partial mock prototype]

The existing prototype is a mock-data, read-only implementation. It is backing code for Action 2, so do not scaffold a parallel implementation.

## `diagrams/`

### `diagrams/adaptive-response-delivery/`

- `architecture.mmd` [doc-only]
- `current-flow.mmd` [doc-only]
- `decision-tree.mmd` [doc-only]
- `failure-recovery.mmd` [doc-only]
- `improved-flow.mmd` [doc-only]
- `tradeoffs.mmd` [doc-only]

### `diagrams/context-engineering/`

- `context-assembly.mmd` [doc-only]
- `context-lifecycle.mmd` [doc-only]

No additional source files were found under `diagrams/`.

## `prompts/`

- `architecture-presales-evaluation.md` [doc-only]
- `article.md` [doc-only]
- `benchmark.md` [doc-only]
- `context-engineering-research-master-prompt.md` [doc-only]
- `context-engineering-research-roadmap.md` [doc-only]
- `critique.md` [doc-only]
- `diagram.md` [doc-only]
- `implementation.md` [doc-only]
- `linkedin.md` [doc-only]
- `review.md` [doc-only]

## `templates/`

- `adr-template.md` [doc-only]
- `article-template.md` [doc-only]
- `benchmark-template.md` [doc-only]
- `experiment-template.md` [doc-only]

## `.github/`

- `.github/copilot-instructions.md` [doc-only]
- `.github/instructions/mermaid.instructions.md` [doc-only]
