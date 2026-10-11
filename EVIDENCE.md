# Evidence map

This document maps the repository's major claims to the implementation, tests, benchmark evidence, and remaining limits.

## Evidence model

Each claim is categorized as one of the following:

- measured locally under controlled conditions
- missing evidence / future research

## Claim map

| Claim / article area | Implementation | Tests / benchmark | What is proven | Remaining limits |
|---|---|---|---|---|
| Adaptive response-delivery implementation overhead | `04-reference-implementation/adaptive-response-filter` | [`benchmark.py`](benchmarks/response-delivery/benchmark.py) and local tests | Matched payloads are passed through both local policies; chunked envelopes are authenticated and reassembled in reverse arrival order | Local implementation timings only; not end-to-end delivery measurements |
| Framed HTTP first-visible delivery under paced synthetic workloads | [`browser_benchmark.py`](benchmarks/response-delivery/browser_benchmark.py) | [`browser_results.json`](benchmarks/response-delivery/browser_results.json) | Standalone HeadlessChrome 154 tested structured and text-like generated payloads at four rates. The server records request/header/first-write/completion timestamps; the detected 120 ms positive control validates Long Task observation for this artifact. | CPython 3.14.6 on Windows 11; loopback, generated list UI, nominal server pacing, one browser build; first-visible is an animation-frame proxy, not compositor paint. No production-network or representative CRM payload evidence. |
| Compression and gzip-framed delivery under paced synthetic workloads | [`browser_benchmark.py`](benchmarks/response-delivery/browser_benchmark.py) | [`browser_results_compression.json`](benchmarks/response-delivery/browser_results_compression.json) | Electron-embedded four-mode run covers full JSON, gzip full JSON, NDJSON, and gzip NDJSON across the generated matrix; 384 server timing records are saved. Gzip levels 1, 3, 6, and 9 record resulting ratios and process CPU averaged over 100 compression repetitions. | Electron-embedded Chrome; the 120 ms Long Task positive control was not detected. The run is not a standalone-Chrome comparison; bodies are generated, gzip is precomputed, and no representative CRM corpus is included. |
| Basic time-bounded authority policy and referral behavior | [`authority_policy.py`](04-reference-implementation/authority_policy.py) | [`test_authority_policy.py`](tests/test_authority_policy.py) and [`test_authority_referral.py`](tests/test_authority_referral.py) | Tests cover matching principal/action, grant bounds, revocation, priority precedence, deny-on-tie, referral propagation through aggregate/session/ticket paths, and no ticket issuance for `refer`. | No agent runtime, delegated authority, multi-hop derivation, or semantic-alignment implementation. |
| Incremental NDJSON record decoding | [`ndjson_stream.py`](04-reference-implementation/ndjson_stream.py) | [`test_ndjson_stream.py`](tests/test_ndjson_stream.py) and [`test_ndjson_guards.py`](tests/test_ndjson_guards.py) | Local tests exercise incremental records, size limits, invalid data, and failure-state behavior. | No production browser adapter or server integration; browser JavaScript parsing is exercised by the separate loopback harness only. |
| Approval-gated CRM workflow | [`identity_provider.py`](prototypes/crm_operational_copilot/identity_provider.py), the SQLite stores, and [`execution_service.py`](prototypes/crm_operational_copilot/execution_service.py) | [`test_crm_validation_scenarios.py`](tests/test_crm_validation_scenarios.py), CRM unit tests, the deterministic harness, and [`mutation_check.py`](mutation_check.py) | Local identity/scope rechecks, conditional claims, version-checked CRM writes with a transactional ledger, audit recovery, 17 contract scenarios, and local 50-process concurrency are exercised. | Deterministic local SQLite only; no real identity provider, CRM, distributed coordination, deployment, telemetry, or customer evidence. |
| Context lifecycle | No implementation or benchmark | None | No context lifecycle behavior is verified in this repository | Representative workflow and retention policy experiment remain future work |
| Local protocol invariants are valid | `WireEnvelope`, `Reassembler`, `DeliveryPolicy` | unit tests under `04-reference-implementation/...` | CRC, auth/validation, ordering, retry behavior, and reassembly are exercised locally | Not a network transport or multi-service deployment |

## Evidence posture

This repository is strongest when it presents local, reproducible evidence. It is weaker when it treats architectural reasoning as if it were a production deployment result. The benchmark layer exists to make the strongest claims more explicit and more testable while preserving the repository's honest boundary.

## Qualifying language to prefer

- "local controlled experiment"
- "conceptual architecture"
- "reference implementation"
- "illustrative benchmark"
- "not yet production-validated"
- "future research opportunity"

## Explicitly excluded claims

The repository does not claim:

- a production deployment stack
- a deployed browser-optimized transport
- a secure production authorization system
- real production customer telemetry
- production SLA evidence

## CRM Approval/Audit Repair Verification (2026-10-09)

This local verification updates the previous CRM approval/audit review. It does not change the repository's evidence levels: results below are measured locally under controlled conditions; broader operational behavior remains missing evidence / future research.

### Environment and baseline

- Environment: Windows, repository `.venv`, CPython 3.14.6, pytest 9.1.1, Ruff 0.16.10, mypy 2.4.0.
- Baseline contract command: `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe -m pytest -q tests/test_audit_temporal_ordering.py tests/test_variant_review_coverage_fixed.py tests/test_crm_decision_contracts.py`.
- Baseline result: `12 passed, 9 xfailed`.
- Baseline fault command: `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe scripts/fault_injection_approval_audit_extended.py`.
- Baseline harness summary: current `2 FAIL-OPEN / 2 FAIL-CLOSED / 1 FAIL-SILENT`; fixed `0 FAIL-OPEN / 4 FAIL-CLOSED / 1 FAIL-SILENT`.
- Baseline harness classifications were not all semantically accurate. The post-write exception left the current variant's approval and audit committed, while fixed rolled both back. The corruption point damaged the variants' shared approvals/CRM/audit database, not an audit-only database. The former clock-skew point rewrote the event timestamp inside the audit writer after service timestamp generation; it did not set the service clock backward.
- At initial `git status --short`, pre-existing modifications were `artifacts/crm-variants/variants-environment.json`, `artifacts/crm-variants/variants-matrix.csv`, `artifacts/crm-variants/variants-results.json`, and `prototypes/crm_operational_copilot/variants/run_experiment.py`. Pre-existing untracked files included the October dossier/review documents, `D11-RISK-ROW.md`, `REEVALUATION-REPORT-2026-10-09.md`, `coverage.json`, `prototypes/crm_operational_copilot/variants/store_layout_fixed.py`, the approval/audit harnesses, and the related CRM tests. These were preserved. At that baseline, the fault CSV was ignored by `.gitignore` (`artifacts/*`); the hygiene pass below makes this evidence file visible to Git without staging it.

### Changes and fresh results

- `CRMExecutionService.review()` now uses `max(service_clock, approval.created_at)` for the approval transition and its audit event. The regression runs against both current and fixed variants and checks both persisted `approved_at` and `event_ts`.
- The fixed variant retains the shared SQLite transaction boundary but no longer duplicates timestamp normalization by monkeypatching the service clock and audit writer.
- Fixed review recovery is explicit: on audit failure, the shared transaction rolls back to `PENDING`; execution remains blocked; no CRM ledger row or approval audit event remains. A new review retry after the transient fault clears commits exactly one decision/event. Tests cover approve/reject, failure before audit insertion, and failure after the insert is staged.
- Final CRM test command: `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe -m pytest -q tests/test_audit_temporal_ordering.py tests/test_variant_review_coverage.py tests/test_variant_review_coverage_fixed.py tests/test_crm_decision_contracts.py`.
- Final CRM test result: `20 passed, 8 xfailed`. The remaining xfails are retained contract gaps; no test was deleted or weakened for this repair.
- Final harness command: `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe scripts/fault_injection_approval_audit_extended.py`; campaign `durability-20261009-repair-03` appended 12 rows to the ignored local CSV.
- Final harness, current variant: `3 RECOVERABLE_FAIL_CLOSED`, `1 FAIL-SILENT`, `1 INVARIANT_HELD`, `1 UNAVAILABLE_UNRECOVERED`; zero `FAIL-OPEN` in these six injected points.
- Final harness, fixed variant: `3 RECOVERABLE_FAIL_CLOSED`, `1 FAIL-SILENT`, `1 INVARIANT_HELD`, `1 UNAVAILABLE_UNRECOVERED`; zero `FAIL-OPEN` in these six injected points.
- For the current variant, actual child-process exit and ENOSPC leave a durable `AUDIT_PENDING` review with no audit event; execution remains unresolved and does not mutate CRM. Explicit `recover()` reconstructs the missing event and finalizes the approval. When the event was inserted before the injected post-write exception, recovery recognizes and reconciles it without duplication. For the fixed variant, the shared transaction rolls the three review failures back to `PENDING`; a new review after restart completes with one approval event and no CRM mutation. This is local SQLite/process-exit evidence, not power-loss evidence.
- The service-clock rollback case (`clock=90`, `created_at=100`) now persists `approved_at=100` and `event_ts=100` in both variants. The regression passes.
- The audit-writer backdating case still persists an approval event with `event_ts=90 < created_at=100` and returns completed; the harness detects it by comparing the persisted event to the approval. The service does not provide runtime monitoring or protection against an audit adapter that rewrites event contents after receiving them. This remains a fail-silent integrity limitation, not a failure of the service-clock regression.
- Shared database corruption leaves approval, CRM, and audit state unavailable (`UNKNOWN`); execution and retry cannot proceed. No backup/restore recovery was tested or implemented.
- The post-write “fsync hook” is a Python exception injected after `AuditStore.write`, not an OS fsync, storage-controller, or power-loss test. The current variant reports unresolved until explicit recovery reconciles the committed event; the fixed variant rolls the transaction back and is recoverable by review retry.
- Ruff command: `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe -m ruff check prototypes/crm_operational_copilot/execution_service.py prototypes/crm_operational_copilot/variants/store_layout_fixed.py tests/test_audit_temporal_ordering.py tests/test_variant_review_coverage_fixed.py scripts/fault_injection_approval_audit_extended.py`; result: `All checks passed!`. Mypy command used `$env:MYPYPATH='04-reference-implementation'` followed by `c:/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe -m mypy` over those same five Python paths; result: `Success: no issues found in 5 source files`. Editor diagnostics reported no errors in the changed Python files.

These results support a local D11 service-clock fix and bounded, retryable fixed-variant review semantics. They do not support a general durability guarantee, audit-writer integrity guarantee, backup/recovery guarantee, or production-readiness claim.

## Repository Hygiene Pass (2026-10-09)

- Baseline branch: `article-crm-local-evidence`; no staged changes. The worktree already contained user-owned modified and untracked CRM evidence, scripts, tests, reports, and artifact files. No pre-existing work was removed or reset.
- The complete pre-cleanup test suite passed: `297 passed, 9 xfailed`; the CI coverage gate passed at 93.19% against 90%. It emitted 105 warnings, predominantly `ResourceWarning`s for unclosed SQLite connections in the CRM prototype tests. This pass did not change test markers or address those resource warnings.
- Post-cleanup full suite: `297 passed, 9 xfailed in 63.31s`; no tests were skipped. The strict expected failures and their explanations remain present.
- Baseline repository-wide Ruff reported 15 formatting/import findings across `scripts/fault_injection_approval_audit.py`, `scripts/normalize_variant_artifacts.py`, `tests/test_crm_decision_contracts.py`, and `tests/test_variant_review_coverage.py`. Cleanup removed only unused imports and adjusted wrapping/import spacing; xfail reasons and assertions were preserved. Final repository-wide Ruff: `All checks passed!`.
- Final repository-wide mypy: `Success: no issues found in 69 source files`. The initial parallel mypy capture was interleaved with other terminal output, so a trustworthy repository-wide baseline result is unavailable; targeted CI mypy did report 15 source files clean. The CI Markdown checker reports all relative links in 61 files resolve.
- `scripts/check_crm_validation_evidence.py` regenerated and compared temporary outputs: 17 scenarios, 17 expected rows, zero failures, deterministic evidence match. `scripts/check_crm_variants.py` was invoked during baseline; it produced no diagnostic output. (Its final exit status was not separately captured.)
- README maintenance distinguishes the in-memory workflow demonstration from the separate experimental SQLite variants, links the bounded evidence and known failures, and describes the test directory accurately. No maturity level was increased.
- `.gitignore` now exempts only `artifacts/fault-injection-approval-audit.csv` from the broad artifact ignore. This file contains historical and repaired approval/audit campaign rows and is reproducibility evidence, so it should be visible for review. The authorized cleanup removed 163 ignored Python/test/lint/type cache and bytecode files, five generated `adaptive_response_reference.egg-info` files, one generated `.coverage` file, and the empty `build/bdist.win-amd64` directory tree. No source, tests, benchmark inputs/results, dated dossiers, archives, ZIP/PDF evidence, or user-created `coverage.json` were deleted. `.venv` was retained.
- No implementation behavior, public API, dependency, test contract, evidence level, or architecture was changed as part of this hygiene pass. Python edits were limited to lint-only import and line-wrapping cleanup.
