# Repository Evaluation: Second Pass

**Reviewed:** 2026-10-04
**Scope:** Repository design and local evidence at the review snapshot. This is not a customer, deployment, or production assessment.

## Assessment

The repository is now a well-structured research handbook with a proposed CRM architecture bundle, a deterministic in-memory approval simulation, reproducible local benchmarks, and CI checks for tests, lint, typing, links, and benchmark figures. Those improvements strengthen the portfolio and its evidence discipline; they do not establish production readiness.

The principal gap remains proof at real identity, CRM, persistence, concurrency, and operations boundaries. The approval workflow demonstrates serial in-process behavior only. Browser measurements are synthetic and runtime-dependent, with no representative CRM payloads or customer clients. Current trends, deployment, customer, and cost evidence remain unverified.

## Findings

1. **Proposed architecture is not implemented capability.** There is no deployed application, real CRM, identity provider, durable queue, or production audit store. The architecture documents state this boundary ([solution overview](../architecture/00-solution-overview.md), [CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md)).
2. **Approval controls are not atomic or authenticated.** Principals and scopes are caller-supplied; state is in memory; and no transaction protects approval consumption, record mutation, or audit. Sequential tests cover useful boundaries, but not concurrent races, audit-sink failure, or crash recovery ([workflow](../prototypes/crm_operational_copilot/approval_workflow.py), [workflow tests](../prototypes/crm_operational_copilot/test_approval_workflow.py)).
3. **Delivery evidence supports candidates, not a universal choice.** The matched synthetic runs show runtime-dependent first-visible and completion behavior. A second browser engine, parse-once-per-frame variant, representative CRM payloads, and client decompression measurements are absent ([ADR-001](../architecture/02-decisions/ADR-001-response-delivery.md), [browser evidence](../benchmarks/response-delivery/browser-matrix-evidence.md)).
4. **Operational and market evidence is still missing.** Sizing is illustrative, prices and customer inputs are TBD, and a deployment/runbook, customer validation, and current external industry research are not present ([NFR worksheet](../architecture/05-nfr-and-sizing.md), [cost model](../architecture/07-cost-model.md)).

## Portfolio Scores

| Lens | Handbook fit | Portfolio design | Evidence strength |
|---|---:|---:|---:|
| Solution Architect | 4/5 | 4/5 | 3/5 |
| Real-World Trends | 3/5 | 2/5 | 1/5 |
| Presales | 4/5 | 4/5 | 1/5 |
| Forward Deployed | 4/5 | 3/5 | 2/5 |
| Mathematics | 4/5 | 3/5 | 3/5 |
| Philosophy/Psychology | 4/5 | 3/5 | 2/5 |

Handbook fit, portfolio design, and evidence strength are separate measures. Prior portfolio scores are retrospective, low-confidence estimates; score changes are judgments, not measured progress. No evidence score exceeds 3, and trends remain unverified. The rubric and rationale are recorded in the [review evidence log](review-evidence-2026-10-04.md).

## Verification

The reviewed source snapshot is tagged `review-2026-10-04`. Local checks on CPython 3.10.20 with the project's `.[dev]` dependencies report 127 passing tests, Ruff success, whole-repository mypy success in 27 source files, and clean Markdown-link and benchmark-figure guards. The CI workflow also defines Python 3.10/3.14, test, lint, typing, and evidence-guard jobs. GitHub-hosted Ubuntu has not run this workflow; pushing the branch and inspecting the Actions result remain necessary.

Per-commit results, import provenance, link history, benchmark CSV comparison, mutation/coverage scope, and browser provenance are kept in the [review evidence log](review-evidence-2026-10-04.md).

## Highest-Value Open Work

1. Validate one bounded workflow in a non-production customer environment with real identity, conditional CRM writes, durable audit, rollback, telemetry, and named operational ownership.
2. Fix identity binding, atomic state consumption, audit-failure recovery, and bounded proposal state; add concurrency and sink-failure tests.
3. Rerun delivery comparisons with representative CRM payloads, named clients, a second browser engine, and parse-once-per-animation-frame handling; measure client decompression cost and choose an explicit success metric.
4. Add a coverage step and independent mutation evidence. The Python 3.10/3.14 CI matrix, whole-repository mypy, Markdown-link guard, and README/CSV figure guard are already configured.
5. Source current primary industry references; complete customer discovery, cost inputs, and operational runbook evidence.

Hosted CI, customer/cloud/production validation, representative CRM payloads, client decompression cost, independent mutation evidence, coverage, concurrency tests, and a second browser engine remain open.