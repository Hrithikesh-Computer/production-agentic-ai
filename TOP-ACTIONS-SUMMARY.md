# Top Actions Summary

Snapshot date: 2026-10-01. “Complete” below means the requested repository artifact or local behavior was produced and verified; it does not imply production readiness. Evidence gaps stay explicit.

## Action 0 — Repository map: Complete

Produced [REPO-MAP.md](REPO-MAP.md) from current paths. It lists the docs, source files, tests, diagrams, and evidence classifications found. The canonical EMR architecture is under `01-agent-architecture/`; the old `03-production-lessons/` path still contains a moved-file stub. Both exist, and the old stub is `UU` in the pre-existing worktree state. Neither was deleted or resolved.

## Action 1 — Adaptive response reference: Partially complete

Updated `04-reference-implementation/adaptive-response-filter/` with:

- Per-envelope HMAC-SHA256 bound to content, sequence metadata, merge mode, and message ID; receiver verification; tampering test including CRC recomputation.
- `tool_calls` boundary splitting after top-level JSON splitting cannot succeed, with a round-trip/fallthrough test.
- Policy-configured timeout and retry behavior, then a caller-provided full-buffer fallback, with deterministic missing-chunk tests.
- `ReassemblySessionManager` keyed by message ID; interleaved responses remain isolated in a test.
- [EVIDENCE.md](04-reference-implementation/adaptive-response-filter/EVIDENCE.md) with observed before/after behavior, local test results, threat model, and production evidence gaps.

The local test, lint, and type checks pass. Production message-collision exposure could not be confirmed from this repository: `EVIDENCE REQUIRED: target client concurrency, transport correlation, and in-flight traces`. Retry/fallback callbacks are not connected to a real transport. Key generation/provisioning/rotation, replay policy, and representative security/performance measurements remain outstanding. Heading, paragraph, sentence, and citation-block splitting remain unimplemented.

## Action 2 — CRM prototype: Partially complete

Extended the pre-existing code rather than creating a second prototype: [crm_copilot.py](prototypes/crm_operational_copilot/crm_copilot.py). It has mock read-only account/opportunity tools, deterministic mock action selection, local scope and action allowlists, an environment-based credential presence/length check, and structured logging for successful and failed runs. Added focused tests, usage docs, and [EVIDENCE.md](prototypes/crm_operational_copilot/EVIDENCE.md).

Three actual local end-to-end timings are recorded in the evidence file. They measure static mock data and no model/network calls. Live Salesforce/REST access, real credential verification and CRM-side authorization, an LLM provider/action-selection policy, production audit retention, and write/workflow approval controls remain `EVIDENCE REQUIRED`. The CRM architecture article's stale “no implementation” statement was corrected; its broader design remains conceptual.

## Action 3 — Documents 04 and 07: Partially complete

Produced [04-07-RECONCILIATION.md](04-07-RECONCILIATION.md), recommending a conceptual merge with 04 as the workflow container and 07's hybrid retrieval as a subsystem. It enumerates overlap, differences, and what would be dropped from duplicate framing without discarding retrieval capabilities. The originals were not edited. **Human product/architecture owner sign-off is required** before editing, merging, or retiring either source document.

## Action 4 — Security maps: Partially complete

Produced [SECURITY-03.md](SECURITY-03.md), [SECURITY-04.md](SECURITY-04.md), and [SECURITY-09.md](SECURITY-09.md). Only local CRM controls with code and tests are marked implemented. WalkMe and governance/security controls remain design intent or `EVIDENCE REQUIRED`; the CRM local token check is not proof of real CRM authentication.

## Action 5 — Authority maps: Partially complete

Produced [04-AUTHORITY-ADDENDUM.md](04-AUTHORITY-ADDENDUM.md) and [09-AUTHORITY-ADDENDUM.md](09-AUTHORITY-ADDENDUM.md), mapping described actions to all eight layers in document 01. The CRM addendum separates local input/scope/action checks from missing production authority. Delegation provenance, structural derivability, priority/defeat, runtime revalidation, semantic alignment, and production decision policies remain evidence-pending where not locally demonstrated.

## Action 6 — Cost/performance plans: Partially complete

Produced [COST-PERF-07.md](COST-PERF-07.md) and [COST-PERF-08.md](COST-PERF-08.md), citing official Azure and Neo4j pricing pages checked 2026-10-01. They include variable-only cost formulas and measurement plans for p50/p95/p99, retrieval accuracy, and graph traversal depth. Published starting rates are not customer estimates. Selected region, tier, product/model, contract, and workload data are required before calculating project cost or setting performance thresholds.

## Action 7 — Context lifecycle: Complete as a deferral decision

Produced [CONTEXT-LIFECYCLE-DECISION.md](CONTEXT-LIFECYCLE-DECISION.md). A prototype is deferred because current multi-step agent documents have no runtime and the CRM prototype is stateless per request. Revisit when CRM gains multi-turn sessions or another implemented agent demonstrates persistent-context failure.

## Evidence still required across actions

- Production HMAC key lifecycle, transport/replay controls, retry/fallback endpoint integration, throughput/memory measurements, and client concurrency traces.
- Live CRM endpoint/test account, real credential/identity-to-scope validation, model/provider and action evaluation, production logging/retention, and future write approval policy.
- Product/architecture owner sign-off on 04/07 reconciliation and governance workflow boundaries.
- Production identity, authorization, provenance, freshness, conflict resolution, semantic alignment, and audit evidence for 03/04/09 agents.
- Selected vendor tiers, regions, models, source stores, customer agreements, workload shape, labeled retrieval/graph benchmarks, and reproducible performance traces for 07/08.
- Multi-turn context data and an approved retention/deletion policy before a context-management prototype is justified.

No credentials, customer environment, production traces, or source datasets were available in this workspace. Pricing sources are public and cited in the cost plans; no deployment-specific quote was available.

## Final validation

- Both test directories explicitly run together: `55 passed`.
- Ruff on the response-filter and CRM slices: passed.
- Mypy on both slices: no issues in 14 source files.
- Response-filter demo: ran successfully and emitted chunk metadata.

The default `pytest -q` uses the repository's configured `testpaths`, which includes the response-filter tests but excludes `prototypes/`; the 55-test result explicitly names both directories.
