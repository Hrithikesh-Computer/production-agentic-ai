# Decision Dossier Addendum

**Date:** 2026-10-09  
**Scope:** Follow-up to [DECISION-DOSSIER-2026-10-09.md](DECISION-DOSSIER-2026-10-09.md). No production source or committed variant artifact was modified. Fresh local tests and a Git for Windows Bash reproduction were run; none constitute deployment evidence.

## A. Variant × Invariant Matrix

Statuses mean: **CLOSES** = tested local evidence satisfies the bounded invariant; **MOVES** = closes one tested failure boundary but leaves the invariant unproven at a different boundary; **OPEN** = direct source or witness establishes the gap; **UNTESTED** = no direct evidence for the matrix cell. I1a is execution mutation/audit consistency; I1b is review decision/audit consistency; I2 tenant-qualified identity; I3 scheduled/owned recovery; I4 sequential at-most-once replay; I5 stale-record/policy binding; I6 complete durable audit for consequential decisions; I7 the execution call does not report completed when its own required execution-audit write fails; I8 single-winner concurrent approval claim. I7 is deliberately scoped to the execution attempt; missing reviewer-decision evidence is I1b/I6.

| Variant | I1a | I1b | I2 | I3 | I4 | I5 | I6 | I7 | I8 |
|---|---|---|---|---|---|---|---|---|---|
| Current three-store baseline | OPEN [witness](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | OPEN [witness](../../tests/test_crm_decision_contracts.py#L207) | OPEN [key](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [manual recovery](../../prototypes/crm_operational_copilot/execution_service.py#L291) | CLOSES [S17](../../artifacts/crm-variants/variants-matrix.csv#L18) | CLOSES [S07](../../artifacts/crm-variants/variants-matrix.csv#L8) | OPEN [review-audit witness](../../tests/test_crm_decision_contracts.py#L231) | CLOSES [unresolved, not success](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | CLOSES [N=50](../../artifacts/crm-variants/variants-matrix.csv#L10) |
| `store-layout-b` | MOVES [execute rollback](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | OPEN [review witness](../../tests/test_variant_review_coverage.py#L71) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [no scheduler](../../prototypes/crm_operational_copilot/execution_service.py#L291) | CLOSES [S17](../../artifacts/crm-variants/variants-matrix.csv#L35) | CLOSES [S07](../../artifacts/crm-variants/variants-matrix.csv#L25) | OPEN [review-audit witness](../../tests/test_variant_review_coverage.py#L71) | CLOSES [S12 unresolved/rollback](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | CLOSES [N=50](../../artifacts/crm-variants/variants-matrix.csv#L27) |
| `recovery-b` | OPEN [recovery-only change](../../prototypes/crm_operational_copilot/variants/recovery.py#L11) | OPEN [inherits review path](../../prototypes/crm_operational_copilot/variants/implementations.py#L36) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [on-demand only](../../prototypes/crm_operational_copilot/execution_service.py#L291) | CLOSES [S17](../../artifacts/crm-variants/variants-matrix.csv#L52) | CLOSES [S07](../../artifacts/crm-variants/variants-matrix.csv#L42) | OPEN [review-audit witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [S12](../../artifacts/crm-variants/variants-matrix.csv#L47) | UNTESTED [race test omits recovery-b](../../prototypes/crm_operational_copilot/variants/test_claims.py#L9) |
| `claim-b` | OPEN [claim-only change](../../prototypes/crm_operational_copilot/variants/claims.py#L13) | OPEN [inherits review path](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [on-demand only](../../prototypes/crm_operational_copilot/execution_service.py#L291) | CLOSES [S17](../../artifacts/crm-variants/variants-matrix.csv#L69) | CLOSES [S07](../../artifacts/crm-variants/variants-matrix.csv#L59) | OPEN [review-audit witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [S12](../../artifacts/crm-variants/variants-matrix.csv#L64) | CLOSES [N=50](../../artifacts/crm-variants/variants-matrix.csv#L61) |
| `broken-control` | OPEN [claim-only negative control](../../prototypes/crm_operational_copilot/variants/claims.py#L35) | OPEN [inherits review path](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [on-demand only](../../prototypes/crm_operational_copilot/execution_service.py#L291) | CLOSES [sequential S17](../../artifacts/crm-variants/variants-matrix.csv#L86) | CLOSES [S07](../../artifacts/crm-variants/variants-matrix.csv#L76) | OPEN [review-audit witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [S12 inherited behavior](../../artifacts/crm-variants/variants-matrix.csv#L81) | OPEN [50 claims accepted](../../artifacts/crm-variants/variants-matrix.csv#L78) |

### Per-variant verdicts

- **Three-store baseline — (b) partially closes / moves.** It binds mutation and ledger in one CRM transaction and can manually reconstruct an audit event from the ledger, but the audit row is not atomic with the CRM commit and reconciliation has no bound or monitor. Reviewer state also commits independently of its audit event. Evidence: [CRM failure witness](../../prototypes/crm_operational_copilot/test_execution_service.py#L177), [review method](../../prototypes/crm_operational_copilot/execution_service.py#L244), [recovery method](../../prototypes/crm_operational_copilot/execution_service.py#L291). **Confidence: high for local behavior; low for deployment implications.**
- **`store-layout-b` — (b) partially closes / moves.** Its wrapper covers `execute()` and its injected execution failures roll back the shared SQLite transaction, but it does not override `review()`. The fresh review-path witness shows state `APPROVED`, no `approval_approved` event, and a subsequent completed execution with only `execution_succeeded` in audit. Thus it closes the tested execution transaction case but leaves I1b open. Evidence: [execute-only wrapper](../../prototypes/crm_operational_copilot/variants/store_layout.py#L229), [review witness](../../tests/test_variant_review_coverage.py#L71). **Confidence: high for the checked-in local implementation.**
- **`recovery-b` — (c) does not close I1a, I1b, I2, I3, or I6.** It changes the no-ledger recovery outcome to invalidation/fresh review; it adds neither a scheduled recovery owner nor transaction/audit behavior. Evidence: [recovery variant](../../prototypes/crm_operational_copilot/variants/recovery.py#L11), [variant mapping](../../prototypes/crm_operational_copilot/variants/implementations.py#L36). **Confidence: high locally.**
- **`claim-b` — (c) does not close I1a, I1b, I2, I3, or I6.** It changes the conditional claim strategy and locally passes the N=50 test; the CRM/audit, identity, and review/recovery contracts remain unchanged. Evidence: [claim implementation](../../prototypes/crm_operational_copilot/variants/claims.py#L11), [race tests](../../prototypes/crm_operational_copilot/variants/test_claims.py#L8). **Confidence: high locally.**
- **`broken-control` — (c) does not close the named gaps and deliberately violates I8.** The synchronized negative control admits multiple claims; it is a test control, not a candidate design. Evidence: [unsafe claim](../../prototypes/crm_operational_copilot/variants/claims.py#L35), [negative test](../../prototypes/crm_operational_copilot/variants/test_claims.py#L16). **Confidence: high locally.**

### Central inference resolved: does shared transaction cover `review()`?

**No.** `SingleFileExecutionService` overrides only `execute()` and enables deferred commits inside that method: [store-layout implementation](../../prototypes/crm_operational_copilot/variants/store_layout.py#L229). `review()` remains the inherited `CRMExecutionService.review()` path, which calls `set_review()` before `audit.write()`: [base review implementation](../../prototypes/crm_operational_copilot/execution_service.py#L244), [approval store commit](../../prototypes/crm_operational_copilot/approvals_store.py#L137). The new test directly demonstrates the resulting state and subsequent execution: [review-path witness](../../tests/test_variant_review_coverage.py#L71). **I1b × shared-transaction is OPEN, not UNTESTED.**

## B. D9 Risk Row + Revised Priority Ranking + Adapt Scope

### D9: approval-leg audit fail-open

**Formal statement:** There exists a pending approval $p$ such that `review(p, approve=True)` persists `state(p)=APPROVED`, the approval-audit write fails, and the state remains executable despite there being no durable `approval_approved` audit event. The current path persists review state first and writes audit second: [execution service](../../prototypes/crm_operational_copilot/execution_service.py#L256), [approval store](../../prototypes/crm_operational_copilot/approvals_store.py#L137). The fresh variant witness then executes the approval and finds only an execution event: [test](../../tests/test_variant_review_coverage.py#L71).

| Field | D9 assessment |
|---|---|
| Scope | `review()` → `ApprovalsStore.set_review()` → `AuditStore.write()` → later `execute()`. |
| Likelihood | **High in the local injected-failure model:** the exact ordering is deterministic and `fail_next_write` reproduces it. **UNKNOWN in deployment:** what is the real audit dependency failure rate and how often would callers retry/continue after `unresolved`? Resolve with production-like fault injection and telemetry; no deployment data exists here. |
| Impact | **High, conditional on audit being required for approval evidence:** authorization-decision traceability, audit completeness, compliance exposure, and trust. **Important qualification:** no evidence shows an unauthorized reviewer can approve; the witness uses a valid configured reviewer. The demonstrated issue is executable state without durable proof of the decision, not proof of an authorization bypass. |
| Detection | The immediate caller receives `unresolved`/`approval_audit_pending`; the persistent row remains `APPROVED` and can execute. No durable queue metric, alert, or monitor is shown. This is observable only if the caller preserves the error or an operator inspects state. |
| Reversibility | Before execution, a compensating audit event may restore evidence if the decision can be reconstructed; after CRM mutation, the original approval-time audit record cannot be made contemporaneous retroactively. **INFERENCE:** impact becomes harder to reverse after execution. |
| Priority | **Critical for write-enabled workflows requiring complete approval audit; medium confidence.** High local likelihood × high conditional impact × weak operational detection. Event rates and compliance threshold remain UNKNOWN. |
| Mitigation | In a bounded test change, make approval state and audit commit together or persist a durable approval-event/outbox record first; keep approval non-executable until the audit event is durable; add injected approval-audit failure then assert no write until successful reconciliation. Require the new test and existing approval/replay suite to pass. |
| Owner role | Security + CRM/data owner + audit owner. |

**Naming correction:** “approval-leg fail-open” is used here for an approval that is already legitimately approved but whose audit evidence failed. It must not be read as proof of unauthorized reviewer authorization. The observable fail-open is the executable state crossing the failed audit boundary.

### Revised ranking

Priority function: rank up when local likelihood and impact rise and when detection is weak; no numeric expected-loss score is justified without event rates and business impact. D10 is newly added for the verified artifact mismatch. Existing IDs D1–D8 are retained as defined in the prior dossier; D9 is the more specific upstream approval-path risk.

| Rank | Risk | Likelihood | Impact | Detection | Priority rationale / bounded mitigation |
|---:|---|---|---|---|---|
| 1 | D1 tenant identity collision | High reproducibility locally; deployment incidence **UNKNOWN**. | High if multi-tenant. | No tenant-aware lookup or alert; direct collision test detects it. | **Critical, conditional.** Key and authorize by `(principal, tenant)` and test cross-tenant same-name identities. |
| 2 | D9 approval state persists/executable despite missing approval audit | High under injected failure; deployment frequency **UNKNOWN**. | High where decision audit is mandatory; no unauthorized reviewer proven. | `unresolved` is returned, but no persistent monitor; caller may ignore it. | **Critical** for audited writes. Atomic/outbox approval event; test failed review audit blocks execution. |
| 3 | D2 CRM mutation can precede audit commit | High under injected audit failure; event rate **UNKNOWN**. | High for audit integrity and incident investigation. | Execution returns unresolved; recovery is manual and unbounded. | **Critical** if strict no-write-without-audit applies. Shared commit or durable outbox plus monitored reconciliation. |
| 4 | D3 recovery is not operationalized | Certain capability gap locally: `recover()` is on-demand, with no scheduler/owner/RPO/RTO. | High availability and audit-completeness exposure. | Unresolved rows can be queried; no automatic backlog alert. | **High.** Name owner, set RPO/RTO, alert on age/count, and test recovery after restart. |
| 5 | D4 audit is not tamper-resistant; denial/rejection state may persist if audit fails | Audit store is a writable local SQLite table; real access/threat likelihood **UNKNOWN**. | High where audit is regulatory/forensic evidence. | Injected write failure is visible; alteration/deletion has no stated detection. | **High, conditional.** Define retention/access/tamper evidence and independently test alteration detection. |
| 6 | D5 local evidence mistaken for deployment evidence | Medium: conflicting and dated documentation coexists with explicit L2/local caveats. | High trust/procurement risk if overstated. | Cross-document review can detect; no single generated evidence index. | **High.** Reconcile evidence level, commit, environment, and claims in CI. |
| 7 | D6 documentation drift | High local: REPO-MAP/VALIDATION-CONTRACT omit or contradict SQLite/variant status. | Medium–High decision and maintenance risk. | Manual comparison; checker does not validate these narrative claims. | **High.** Update canonical map and add a consistency check. |
| 8 | D7 no demonstrated differentiator or ROI | UNKNOWN: no business baseline or measured outcome. | Medium–High opportunity cost if funding proceeds without value evidence. | Not detectable from repository; requires workflow measurement. | **High before funding, not a runtime defect.** Measure one workflow against current process and fully loaded cost. |
| 9 | D8 local CRM schema allows one field row per customer | Certain local schema property; relevance to intended multi-field workflow **UNKNOWN**. | Medium correctness/generalization risk if scope expands. | Schema review/multi-field test. | **Medium, conditional.** Confirm scope; model composite tenant/customer/field identity before expanding. |
| 10 | D10 variant matrix byte drift from line-ending serialization | High in this Windows/Bash reproduction: matrix bytes differ each run; semantic content matches after CRLF normalization. Other OS behavior **UNKNOWN**. | Low–Medium: strict reproducibility checker fails, but no semantic matrix difference was found. | Highly observable: checker exits 1 and normalized diff is empty. | **Low operational priority, high reproducibility certainty in this environment.** Choose canonical CSV newline policy and regenerate/verify artifacts in a controlled CI environment; do not rewrite committed artifacts as part of this dossier. |

**Does D9 outrank D2?** **Yes, narrowly and conditionally for a write-enabled workflow with mandatory approval evidence:** D9 is upstream and can leave the action executable without a durable approval event, while D2 occurs after the mutation and is explicitly unresolved/recoverable; neither priority claim proves unauthorized approval, and both remain hard gates where complete audit is required.

**If only one risk can be addressed first:** address **D1 when the target is multi-tenant**, because the identity key demonstrably aliases tenants; for a confirmed single-tenant workflow with mandatory approval audit, address **D9 before D2** because the unaudited approval state is upstream of the write. **Confidence: medium**, conditional on context not supplied.

### Re-scored “adapt” scope

- **Adapt can reuse as design/test material (high confidence):** local patterns for I4 sequential replay, I5 stale record/policy checks, I7 unresolved-not-success behavior, and the tested single-writer claim controls. These are local evidence only, not production guarantees: [S07/S09/S17 matrix rows](../../artifacts/crm-variants/variants-matrix.csv#L8), [CRM tests](../../prototypes/crm_operational_copilot/test_execution_service.py#L95).
- **Adapt still leaves open (high confidence):** I2 tenant-qualified identity; I3 scheduled, owned recovery; I1b approval state/audit transaction; I6 end-to-end audit completeness and tamper protection. I1a is only locally moved by the shared-file variant and does not generalize to a remote CRM/audit topology: [review-path witness](../../tests/test_variant_review_coverage.py#L71), [on-demand recovery](../../prototypes/crm_operational_copilot/execution_service.py#L291), [local identity key](../../prototypes/crm_operational_copilot/identity_provider.py#L39).
- **Build becomes preferable only if (medium confidence):** after workflow and compliance requirements are fixed, native CRM/IdP and named commercial candidates fail I1a/I1b/I2/I3/I4 gates, measured user value clears an agreed threshold, and a funded team accepts security, migration, on-call, retention, and 3-year TCO ownership. Those inputs are currently **UNKNOWN**; resolve with product, security, CRM/data, operations, compliance, and procurement owners.

## C. Variant `review()` Coverage Test

Created [test_variant_review_coverage.py](../../tests/test_variant_review_coverage.py). It contains a healthy-audit positive control, an injected audit-failure witness, and an intentionally unsafe state-first implementation control. The test has no xfail: it passes by asserting the variant’s **observed defect** and proves the rollback contract assertion fails against that unsafe state. The existing contract file was not modified.

**Raw focused output (fresh run after the final witness extension):**

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1
collected 3 items

tests/test_variant_review_coverage.py::test_store_layout_review_with_healthy_audit_persists_both PASSED
tests/test_variant_review_coverage.py::test_store_layout_review_audit_failure_leaves_approved_state PASSED
tests/test_variant_review_coverage.py::test_unsafe_review_control_is_detected_by_rollback_assertion PASSED

============================== 3 passed in 0.39s ==============================
```

**Classification: OPEN.** The shared-transaction implementation covers only `execute()`; failed review audit leaves `APPROVED`, and a subsequent execute completes with no `approval_approved` event. This resolves A.3 and updates I1b × `store-layout-b` from any earlier untested status to OPEN. **Confidence: high for this local variant and test.** It is not a deployment result.

## D. POSIX-Shell Artifact Checker Reproduction

Created [reproduce_variant_checker.sh](../../scripts/reproduce_variant_checker.sh). It uses `set -euo pipefail`, prints interpreter and working directory, separately captures checker stdout/stderr, prints the checker exit code, regenerates all three artifacts in a temporary directory, compares bytes, and emits a CRLF-normalized unified diff if content differs. Temporary outputs are removed on exit; no committed artifact was changed.

**Raw reproduction output (Git for Windows Bash):**

```text
POSIX_SHELL=Git for Windows Bash
script_exit_code= 1
interpreter=/c/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe
working_directory=/c/Users/HP/Documents/GitHub/production-agentic-ai
--- checker stdout ---
CRM variant check failed: regenerated output differs from .../artifacts/crm-variants/variants-matrix.csv
checker_exit_code=1
--- harness stdout ---
matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
broken_control_n50=accepted:50/50 single_winner_assertion:False
focused_pytest_return_code=0
pytest_tail[baseline]:
.................                                                        [100%]
17 passed in 0.83s
pytest_tail[store-layout-b]:
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S11]
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S12]
2 failed, 15 passed in 0.65s
pytest_tail[recovery-b]:
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S10]
1 failed, 16 passed in 0.58s
pytest_tail[claim-b]:
.................                                                        [100%]
17 passed in 0.52s
pytest_tail[broken-control]:
.................                                                        [100%]
17 passed in 0.54s
harness_exit_code=0
CRLF-normalized unified diff: no content differences for variants-matrix.csv
BYTE-FOR-BYTE EQUAL: variants-results.json
BYTE-FOR-BYTE EQUAL: variants-environment.json
artifact_diff_exit_code=1
--- checker stderr ---
--- harness stderr ---
BYTE DRIFT: variants-matrix.csv
```

The raw pytest failure details were: store-layout S11/S12 baseline assertions expected `EXECUTING`/`AUDIT_PENDING`, while the shared transaction persists `APPROVED` and rolls CRM/ledger/audit back; recovery-b S10 baseline assertion expected `APPROVED`, while the variant intentionally persists `INVALIDATED/crash_no_write`. The variant harness reports these as expected variant-specific divergences and returns 0; its matrix has 84 expected passing assertions and the single deliberate broken-control S09 failure. See [variant test expectations](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L35) and [recorded matrix](../../artifacts/crm-variants/variants-matrix.csv#L30).

Fresh byte-count probe:

```text
variants-matrix.csv bytes=8661 CRLF=86 LF=86 CR=86
variants-results.json bytes=31831 CRLF=891 LF=891 CR=891
variants-environment.json bytes=199 CRLF=8 LF=8 CR=8
variants-matrix.csv byte_equal=False CRLF-normalized_equal=True committed_bytes=8661 generated_bytes=8575
variants-results.json byte_equal=True CRLF-normalized_equal=True committed_bytes=31831 generated_bytes=31831
variants-environment.json byte_equal=True CRLF-normalized_equal=True committed_bytes=199 generated_bytes=199
```

**Classification: DRIFT, not SCRIPT-DEFECT.** The checker is not silent under a captured POSIX invocation; it exits 1 for strict byte inequality. A fresh direct harness comparison verified `variants-results.json` and `variants-environment.json` byte-equal; `variants-matrix.csv` was 8,661 committed bytes vs 8,575 generated bytes and became byte-identical after CRLF normalization. Thus no semantic row drift was found, but byte-for-byte reproducibility fails in this environment. **Confidence: high for this Windows/Python/Bash run; UNKNOWN on other OS line-ending behavior.** The prior “silent checker” anomaly is resolved as a shell/terminal capture issue plus a reproducible newline-format drift, not a pass.

## E. Self-Critique

### Three weakest claims from the prior dossier

1. **Prior claim:** D1 should be addressed first. The prior dossier already made it conditional on multi-tenancy: [prior ranking](DECISION-DOSSIER-2026-10-09.md#L136). **Treatment: downgrade to conditional.** The local collision is directly reproduced, but production likelihood is **UNKNOWN** until tenant topology and identity namespace are supplied. If single-tenant, D9/I1b or D2/I1a may be the more material first control.
2. **Prior claim:** the CRM/audit gap is recoverable. The prior source and local tests demonstrate a manual recovery path, not an automatic or bounded one: [prior recovery statement](DECISION-DOSSIER-2026-10-09.md#L19). **Treatment: strengthen the qualification.** It is recoverable after an operator/test invokes `recover()` and the audit dependency is healthy; bounded completion, monitored backlog, and deployment recovery are **UNVERIFIED**.
3. **Prior claim:** the shared transaction “partially closes / moves” I1a. Prior evidence tested execute-side rollback but did not test inherited `review()`: [prior variant verdict](DECISION-DOSSIER-2026-10-09.md#L193). **Treatment: strengthen with a new witness.** It affects only `execute()`; I1b remains OPEN because `review()` is inherited and an approval with missing audit remains executable. The new test confirms it.

### Three weakest claims in this addendum

1. **D9 “High likelihood.”** **Treatment: scope and downgrade.** High is justified only for the deterministic local injected-failure path. The production audit-failure rate and caller behavior are **UNKNOWN**; the risk register records that explicitly. **Confidence: high locally, low externally.**
2. **D9 ranks above D2.** **Treatment: qualify.** The upstream position is factual, but the relative business impact depends on whether approval-event audit is a hard control. No unauthorized reviewer is shown; D9 is best named “approval-evidence fail-open,” not an authenticated-identity bypass. **Confidence: medium and conditional.**
3. **D10 is line-ending-only drift.** **Treatment: strengthen locally, bound globally.** Direct harness comparison found equality after CRLF normalization for matrix and exact equality for the other artifacts. This establishes the current platform cause; whether other Git/CI configurations reproduce it is **UNKNOWN**. **Confidence: high for this environment.**

### Silent-UNKNOWN and confidence corrections

- Any inference that D9 permits an unauthorized human to approve is retracted. Evidence proves valid review state persisted without its audit event and then executed; it does not show reviewer identity/scope bypass. Resolving question: can a real caller reach this path with a reviewer not authorized by the production IdP/CRM? Owner: security/identity.
- Production event likelihood for D1, D2, D4, and D9 is **UNKNOWN**; deterministic failure injection proves reachable behavior, not real-world frequency. Resolve with representative non-production fault injection and later operational telemetry. Owner: security, CRM/data, and operations.
- Prior “medium” impact for unproven ROI and local database concentration should not be read as measured risk. Business impact, cost, transaction rate, and outage tolerance are **UNKNOWN**. Resolve with workflow baseline, cost model, and business-impact analysis. Owner: product/finance/operations.
- “D9 outranks D2” is an **INFERENCE**, not a universal ordering; conditional requirement and confidence are stated above.
- Fresh raw outputs are provided for the contract suite, variant/review suite, and POSIX script. The full general repository test suite was not run in this addendum; its status remains **UNVERIFIED**. The variant checker’s subprocess tests did run and their intentional baseline-assertion divergences are preserved above, not hidden.

### Evidence classes and recommendation confidence

- **Verified in this environment:** unchanged `tests/test_crm_decision_contracts.py` → 8 passed, 8 xfailed; combined variant and review suite → 8 passed; fresh review suite → 3 passed; Git Bash reproducer → checker 1, harness 0, artifact-diff 1; matrix content is equal after CRLF normalization.
- **Verified in the prior run, not relied on as a fresh run:** the prior run reported the CRM scenario focused checks and 5 variant tests passing. This addendum independently re-ran the contract file and all variant tests.
- **INFERENCE:** D9 may rank above D2 for mandatory approval evidence because it is upstream; this is conditional and medium confidence.
- **UNKNOWN:** external identity, CRM, audit, vendor, business value, regulatory applicability, operational RPO/RTO, and non-Windows artifact behavior. Resolving questions and owner roles appear in Sections B and D.

**Recommendations:** do not treat any variant as adopted (high confidence); test/repair the review-path transaction boundary before enabling writes (high confidence for the local defect); choose canonical newline policy and reproduce in CI before claiming byte-reproducible artifacts (high confidence for this checker failure); choose D1 vs D9/D2 as first remediation only after tenant and audit requirements are confirmed (medium confidence).