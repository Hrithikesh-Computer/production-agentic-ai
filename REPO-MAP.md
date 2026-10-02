# Repository Map

Inventory snapshot: 2026-10-01. This map reflects files present before Actions 1-7. Generated deliverables from those actions will be appended under **Action outputs** as they are created.

Tags describe the repository evidence currently present, not production readiness:

- `[doc-only]`: Markdown content without a matching local executable implementation.
- `[has reference implementation]`: documented by or associated with checked-in executable reference code.
- `[reference implementation incomplete]`: executable code exists, but the requested boundary or behavior is still missing or unverified.

## Root

- `CONTRIBUTING.md` [doc-only]
- `LICENSE` (not Markdown)
- `README.md` [has reference implementation]
- `ROADMAP.md` [doc-only]
- `STYLE_GUIDE.md` [doc-only]
- `technical-audit-report.md` [doc-only]
- `pyproject.toml` (Python project configuration)

## `01-agent-architecture/`

- `01-agent-authority-and-intent.md` [doc-only]
- `02-emr-to-postgresql-ingestion-architecture.md` [doc-only]
- `03-walkme-workflow-automation-copilot.md` [doc-only]
- `04-fintech-governance-risk-agentic-platform.md` [doc-only]
- `05-autonomous-ingestion-data-validation-pipeline.md` [doc-only]
- `06-enterprise-operational-workflow-event-system.md` [doc-only]
- `07-enterprise-audit-compliance-risk-copilot.md` [doc-only]
- `08-sales-intelligence-knowledge-graph-copilot.md` [doc-only]
- `09-crm-operational-copilot-salesforce-agentforce-poc.md` [reference implementation incomplete]
- `10-mcp-service-integration-gateway.md` [doc-only]

No source files were found in this directory.

## `02-context-and-memory/`

- `01-beyond-token-windows.md` [doc-only]

No source files were found in this directory.

## `03-production-lessons/`

- `01-adaptive-response-delivery.md` [has reference implementation]
- `02-emr-spark-postgresql-ingestion-optimization.md` [doc-only]

No source files were found in this directory.

## `04-reference-implementation/`

- `README.md` [has reference implementation]

### `04-reference-implementation/adaptive-response-filter/`

- `chunker.py` [reference implementation incomplete]
- `demo.py` [reference implementation incomplete]
- `envelope.py` [reference implementation incomplete]
- `filter.py` [reference implementation incomplete]
- `metrics.py` [reference implementation incomplete]
- `middleware.py` [reference implementation incomplete]
- `policy.py` [reference implementation incomplete]
- `reassembler.py` [reference implementation incomplete]
- `test_reassembly_session.py` [reference implementation incomplete]
- `test_chunker.py` [reference implementation incomplete]
- `test_envelope.py` [reference implementation incomplete]
- `test_reassembler.py` [reference implementation incomplete]
- `EVIDENCE.md` [reference implementation incomplete]

## `prototypes/crm_operational_copilot/`

- `README.md` [reference implementation incomplete]
- `crm_copilot.py` [reference implementation incomplete]
- `test_crm_copilot.py` [reference implementation incomplete]
- `EVIDENCE.md` [reference implementation incomplete]

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

## EMR path hygiene

The canonical architecture document exists at `01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md`. An old-path stub remains at `03-production-lessons/02-emr-spark-postgresql-ingestion-optimization.md` and points to the canonical article. Both paths exist, so this is recorded as documentation hygiene for human review; neither file is removed or edited here. The old-path file is currently marked `UU` in the worktree, so preserve its unresolved worktree state.

## Additional action deliverables

Root-level review documents created after the initial inventory:

- `04-07-RECONCILIATION.md` [doc-only]
- `04-AUTHORITY-ADDENDUM.md` [doc-only]
- `09-AUTHORITY-ADDENDUM.md` [doc-only]
- `SECURITY-03.md` [doc-only]
- `SECURITY-04.md` [doc-only]
- `SECURITY-09.md` [reference implementation incomplete]
- `COST-PERF-07.md` [doc-only]
- `COST-PERF-08.md` [doc-only]
- `CONTEXT-LIFECYCLE-DECISION.md` [doc-only]
- `TOP-ACTIONS-SUMMARY.md` [doc-only]

The original inventory above remains the Action 0 snapshot; these entries and the updated source lists reflect Action 1-7 work. `09-crm-operational-copilot-salesforce-agentforce-poc.md` now accurately records its local reference prototype and remains incomplete relative to its live CRM/LLM design.
