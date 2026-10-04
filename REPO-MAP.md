# Repository Map

Inventory snapshot: 2026-10-03. Active material is listed first; archive contents are historical and are not current guidance.

Tags describe the repository evidence currently present, not production readiness:

- `[doc-only]`: Markdown content without a matching local executable implementation.
- `[tested local reference]`: bounded executable behavior with local tests; not a production service.
- `[partial mock prototype]`: limited local mock behavior; no claim of live integration or production readiness.

## Active Research and Implementation

1. [Adaptive response delivery](03-production-lessons/01-adaptive-response-delivery.md) — research note, local envelope timings, standalone three-mode baseline, and separate Electron four-mode follow-up; no production latency evidence.
2. [Context lifecycle](02-context-and-memory/01-beyond-token-windows.md) — research hypothesis; no local implementation or benchmark.
3. [Authority and intent](01-agent-architecture/01-agent-authority-and-intent.md) — research hypothesis; a bounded time-window/priority evaluator exists, but no semantic-alignment mechanism.
4. [Reference implementation](04-reference-implementation/) — adaptive response filter, bounded authority policy evaluator, and incremental NDJSON decoder, with tests and evidence boundaries.

The out-of-scope [EMR-to-PostgreSQL architecture analysis](archive/design-sketches-2026/02-emr-to-postgresql-ingestion-architecture.md) is archived, not active research.

## Historical Archives

- [Design sketches, archived 2026-10](archive/design-sketches-2026/) — enterprise pattern notes and the relocated EMR stub.
- [Evaluations and review artifacts, archived 2026-10](archive/review-artifacts-2026/) — internal evaluation, dated reconciliation, authority, cost/performance, audit, and summary records.
- [Security mappings](archive/review-artifacts-2026/security-mappings/) — evidence audits for archived designs and the local CRM mock.

## Root

- `CONTRIBUTING.md` [doc-only]
- `LICENSE` (not Markdown)
- `README.md` [entry point]
- `ROADMAP.md` [doc-only]
- `STYLE_GUIDE.md` [doc-only]
- `CONTEXT-LIFECYCLE-DECISION.md` [doc-only]
- `EVIDENCE.md` [doc-only]
- `mutation_check.py` [temporary-copy mutation runner for authority, NDJSON, and CRM workflow tests]
- `pyproject.toml` (Python project configuration)

## `01-agent-architecture/`

- `01-agent-authority-and-intent.md` [doc-only]

The former EMR analysis and design sketches 02-10 are archived in `archive/design-sketches-2026/`; the CRM mock prototype remains under `prototypes/crm_operational_copilot/` with its own evidence boundary.

No source files were found in this directory.

## `02-context-and-memory/`

- `01-beyond-token-windows.md` [doc-only]

No source files were found in this directory.

## `05-field-notes/`

The directory exists but is currently empty.

## `03-production-lessons/`

- `01-adaptive-response-delivery.md` [research note; standalone loopback baseline plus a separately labeled Electron four-mode follow-up]

The EMR article is archived under `archive/design-sketches-2026/` because it does not meet the current Scope Guard.

## `04-reference-implementation/`

- `README.md` [tested local reference]
- `authority_policy.py` [bounded local principal/action/time-window and policy-priority evaluator]
- `ndjson_stream.py` [incremental object-record decoder with bounded record size and failure-state tests]

### `04-reference-implementation/adaptive-response-filter/`

- `chunker.py`, `envelope.py`, `filter.py`, `middleware.py`, `policy.py`, `reassembler.py`, `metrics.py`, `demo.py` [tested local reference]
- `test_chunker.py`, `test_envelope.py`, `test_reassembler.py`, `test_reassembly_session.py` [local tests]
- `EVIDENCE.md` [scope, observed behavior, and remaining evidence requirements]

## `prototypes/crm_operational_copilot/`

- `README.md`, `crm_copilot.py`, `test_crm_copilot.py`, `approval_workflow.py`, `test_approval_workflow.py`, `EVIDENCE.md` [partial mock prototype; the approval workflow is a separate in-memory simulation]

The existing prototype is a mock-data, read-only implementation. It is backing code for Action 2, so do not scaffold a parallel implementation.

## `tests/`

- `test_authority_policy.py`, `test_authority_referral.py` [authority evaluator and referral behavior; no semantic-alignment or production authorization claim]
- `test_ndjson_stream.py`, `test_ndjson_guards.py` [incremental NDJSON parser and input/failure guards]

## `benchmarks/`

- `response-delivery/` [matched-payload local overhead benchmark; standalone `browser_results.json` and separate Electron `browser_results_compression.json`; no production-network evidence]

## `diagrams/`

### `diagrams/adaptive-response-delivery/`

These diagrams document the separate authenticated-envelope/reassembly protocol example, not the article's selected single-response NDJSON experiment.

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
