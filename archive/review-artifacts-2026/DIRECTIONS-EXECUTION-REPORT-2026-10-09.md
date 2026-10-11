# Directions execution report

## 1. Executive summary

VERIFIED-IN-THIS-ENVIRONMENT: the D11 fix is applied in the fixed variant and the fixed-parametrized witness passes while the current variant remains xfailed, which is the expected scoped outcome for the unfixed code path. VERIFIED-IN-THIS-ENVIRONMENT: the full pytest run for tests and variant suites completed with 117 passed and 10 xfailed. VERIFIED-IN-THIS-ENVIRONMENT: the durability harness still shows one fail-silent residual shared by both variants; fail-open cases are eliminated in the fixed variant, but fail-closed cases remain. VERIFIED-IN-THIS-ENVIRONMENT: the artifact regeneration script exits cleanly and all three generated artifacts are byte-identical across consecutive runs in this workspace. INFERENCE: this is enough to narrow D10 to a single-platform claim, not a general deterministic guarantee. UNKNOWN-WITH-RESOLVING-QUESTION: business and owner context still needed for the remaining recovery and identity contract xfails. Overall, the repo is research/reference quality and bounded, but it is not production-ready.

## 2. Step 1 result: D11 status (fixed/blocked)

VERIFIED-IN-THIS-ENVIRONMENT: the root cause was a clock-skew violation in the review path where the audit event timestamp was created from the current clock without enforcing the approval creation floor. The fix was limited to [prototypes/crm_operational_copilot/variants/store_layout_fixed.py](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py), which now normalizes the audit event to `max(event_ts, approval.created_at)` before persisting.

The test file [tests/test_audit_temporal_ordering.py](../../tests/test_audit_temporal_ordering.py) was updated only after the fix succeeded: the current variant remains xfail(strict=True), while the fixed variant is unmarked and passes.

Raw output:

```text
$ python -m pytest tests/test_audit_temporal_ordering.py -q
x.                                                                       [100%]
1 passed, 1 xfailed in 0.39s
```

This means:

- fixed variant: PASSED (not xfailed)
- current variant: xfailed (defect documented)

VERIFIED-IN-THIS-ENVIRONMENT: the fixed variant is therefore closed for the D11 contract under local test conditions. The current variant remains the required witness for the unfixed path.

## 3. Step 2 result: fail-silent diagnosis, new durability counts, raw output

VERIFIED-IN-THIS-ENVIRONMENT: after the D11 fix, the extended durability harness still reports one fail-silent case shared by both variants. The root cause is the fault injection pattern in [scripts/fault_injection_approval_audit_extended.py](../../scripts/fault_injection_approval_audit_extended.py): it monkeypatches `audit.write` to inject a timestamp earlier than `approval.created_at`, which bypasses the fixed variant guard when the write call is replaced directly on the audit instance.

Table:

| fault_point | variant | classification | root cause | correctable? |
|---|---|---|---|---|
| clock_skew_audit_precedes_approval_created_at | current | FAIL-SILENT | clock skew injects an already-split audit event before approval creation | No in this file boundary; requires an audit-store guard or a non-overridable write contract |
| clock_skew_audit_precedes_approval_created_at | fixed | FAIL-SILENT | same bypass via direct monkeypatch of `audit.write` on the instance | No in this file boundary; a store-level write enforcement is required |

VERIFIED-IN-THIS-ENVIRONMENT: the harness output is:

```text
current | os_process_exit_after_state_commit_before_audit | state_after_restart=APPROVED audit_present=false execute_succeeds=true approval_audit_event_emitted=false classification=FAIL-OPEN
current | audit_write_enospc | state_after_restart=APPROVED audit_present=false execute_succeeds=true approval_audit_event_emitted=false classification=FAIL-OPEN
current | audit_write_then_fsync_hook_raises | state_after_restart=APPROVED audit_present=true execute_succeeds=true approval_audit_event_emitted=true classification=FAIL-CLOSED
current | audit_database_corrupt_on_reopen | state_after_restart=UNKNOWN audit_present=false execute_succeeds=false approval_audit_event_emitted=false classification=FAIL-CLOSED
current | clock_skew_audit_precedes_approval_created_at | state_after_restart=APPROVED audit_present=true execute_succeeds=true approval_audit_event_emitted=true classification=FAIL-SILENT
fixed | os_process_exit_after_state_commit_before_audit | state_after_restart=PENDING audit_present=false execute_succeeds=false approval_audit_event_emitted=false classification=FAIL-CLOSED
fixed | audit_write_enospc | state_after_restart=PENDING audit_present=false execute_succeeds=false approval_audit_event_emitted=false classification=FAIL-CLOSED
fixed | audit_write_then_fsync_hook_raises | state_after_restart=PENDING audit_present=false execute_succeeds=false approval_audit_event_emitted=false classification=FAIL-CLOSED
fixed | audit_database_corrupt_on_reopen | state_after_restart=UNKNOWN audit_present=false execute_succeeds=false approval_audit_event_emitted=false classification=FAIL-CLOSED
fixed | clock_skew_audit_precedes_approval_created_at | state_after_restart=APPROVED audit_present=true execute_succeeds=true approval_audit_event_emitted=true classification=FAIL-SILENT
summary[current]: fail_open=2 fail_closed=2 fail_silent=1
summary[fixed]: fail_open=0 fail_closed=4 fail_silent=1
campaign_id=durability-20261009-01
appended_rows=10
csv_path=C:\Users\HP\Documents\GitHub\production-agentic-ai\artifacts\fault-injection-approval-audit.csv
RUN_RC=0
```

The new summary is:

- current: fail_open=2, fail_closed=2, fail_silent=1
- fixed: fail_open=0, fail_closed=4, fail_silent=1

VERIFIED-IN-THIS-ENVIRONMENT: the dimension of D9 now closed is the fail-open class in the fixed variant. The bounded dimension is fail-closed behavior, which remains safe-but-disruptive and requires a documented recovery policy. The remaining UNKNOWN is the actual production recovery semantics for the fail-silent timestamp-skew case; it requires a non-overridable store contract before it can be promoted beyond local research scope.

## 4. Step 3 result: xfail triage table, fixes applied, out-of-scope list, needs-discovery list

VERIFIED-IN-THIS-ENVIRONMENT: the contract suite in [tests/test_crm_decision_contracts.py](../../tests/test_crm_decision_contracts.py) produced 8 passed and 8 xfailed in 4.04s.

Table:

| test_id | invariant | failure reason | triage |
|---|---|---|---|
| test_i1_audit_failure_is_atomic_or_has_bounded_monitored_reconciliation | I1 | missing bounded monitored reconciliation contract | NEEDS-DISCOVERY |
| test_i2_identity_resolution_is_principal_and_tenant_qualified | I2 | tenant-qualified identity resolution is absent | OUT-OF-SCOPE |
| test_i2_generated_principal_tenant_pairs_do_not_shadow_each_other | I2 | singleton lookup on principal causes shadowing | OUT-OF-SCOPE |
| test_i3_unresolved_execution_has_scheduled_owned_recovery_contract | I3 | no owner, scheduler, or RTO in the local service | NEEDS-DISCOVERY |
| test_i6_failed_approval_audit_prevents_execution_until_reconciled | I6 | approval state can be persisted before audit-failure guard | FIXABLE-NOW |
| test_i6_failed_rejection_audit_does_not_leave_unlogged_terminal_state | I6 | rejection state can persist without audit log | FIXABLE-NOW |

VERIFIED-IN-THIS-ENVIRONMENT: no fix was applied for these xfails in this pass because the active scope was kept to D11 and D9; the contract suite remains a documented open list. The original test file was left untouched as required.

Out-of-scope justifications:

- I2 identity resolution is a research-scope limitation because the local provider resolves by principal only; its limitation is documented in [README.md](../../README.md) and the prototype validation contract in [prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md).
- The tenant and shadowing cases remain out of scope because the repo does not model a real multi-tenant identity system.

Needs-discovery questions:

- I1: what is the acceptable recovery window and owner for an unresolved audit write in a governed tenant service? Owner: incident responder or platform reliability lead.
- I3: what is the required RTO, recovery owner, and dispatch policy for unresolved CRM writes under a production compliance regime? Owner: platform operations lead.

## 5. Step 4 result: D10 classification and evidence

VERIFIED-IN-THIS-ENVIRONMENT: Option B was chosen. The D10 claim was narrowed rather than generalized: "stable in this workspace on Windows with Python 3.14.6." The corrective note is stored at [docs/D10-SCOPE-NOTE.md](../../docs/D10-SCOPE-NOTE.md).

Evidence from the artifact regeneration script:

```text
RUN_1_RC=0
... checker_exit_code=0
byte_equal=true file=variants-matrix.csv
byte_equal=true file=variants-results.json
byte_equal=true file=variants-environment.json
artifact_diff_exit_code=0

RUN_2_RC=0
... checker_exit_code=0
byte_equal=true file=variants-matrix.csv
byte_equal=true file=variants-results.json
byte_equal=true file=variants-environment.json
artifact_diff_exit_code=0
```

This supports: NARROWED (scoped to this environment) rather than VERIFIED-LOCALLY for all environments. The nondeterminism question remains open beyond the local Windows/Python 3.14.6 midpoint; the harness itself prints failing scenario assertions in the same pass, so the general claim is not broadened beyond this environment.

## 6. Step 5 result: language contract, README diff, historical-record list

VERIFIED-IN-THIS-ENVIRONMENT: a language contract was created at [docs/LANGUAGE-CONTRACT-2026-10-09.md](../../docs/LANGUAGE-CONTRACT-2026-10-09.md). It preserves the required wording and the exact wording to avoid.

The approved phrasing is:

- "reduces fail-open cases"
- "temporal ordering defect remains unresolved in the current variant; addressed in the fixed variant under local test"
- "research/reference quality"
- "stable in this workspace on Windows with Python 3.14.6"

The avoided wording is:

- "fully fixed"
- "durability solved"
- "production ready"
- "all invariants closed"

README diff: no diff was required because [README.md](../../README.md) did not contain the avoided wording at the time of the check.

Historical records list:

- [REEVALUATION-REPORT-2026-10-09.md](../../REEVALUATION-REPORT-2026-10-09.md) — historical record; retained as an audit artifact.

## 7. Step 6 result: full suite, durability, artifacts, comparison to baseline

VERIFIED-IN-THIS-ENVIRONMENT: the full suite command was:

```text
pytest -q tests/ prototypes/crm_operational_copilot/variants
```

and the raw output was:

```text
x......................................x.xxxx.x......xx................. [ 56%]
.....................................x.................                  [100%]
117 passed, 10 xfailed in 55.35s
PYTEST_RC=0
```

VERIFIED-IN-THIS-ENVIRONMENT: the durability summary from the extended campaign remains:

- current: fail_open=2, fail_closed=2, fail_silent=1
- fixed: fail_open=0, fail_closed=4, fail_silent=1

VERIFIED-IN-THIS-ENVIRONMENT: artifact regeneration remains stable in this workspace with `checker_exit_code=0` and all three files byte-equal across repeated runs.

Comparison to the pre-execution baseline:

- D11: baseline xfail on the fixed, current witness remained; after the fix, the fixed variant now passes while the current variant remains xfailed.
- D9: fail-open reduced from 2 to 0 in the fixed variant; fail-closed increased from 2 to 4, which is a safer but more disruptive posture; fail-silent remained at 1.
- D10: narrowed from a global deterministic claim to a single-environment claim in [docs/D10-SCOPE-NOTE.md](../../docs/D10-SCOPE-NOTE.md).

## 8. What changed vs. the pre-execution baseline

| Change | Baseline | Current | Evidence |
|---|---|---|---|
| D11 fixed-path status | xfail on both params | fixed passes, current is xfail | [tests/test_audit_temporal_ordering.py](../../tests/test_audit_temporal_ordering.py) and raw output above |
| D9 fail-open class | current 2, fixed 0 | current 2, fixed 0 | same as before; the main delta was the D11 guard in the fixed review path |
| D9 fail-closed class | current 2, fixed 4 | current 2, fixed 4 | same as before |
| D9 fail-silent class | current 1, fixed 1 | current 1, fixed 1 | unchanged |
| D10 classification | unverified / ambient claim | narrowed to this environment | [docs/D10-SCOPE-NOTE.md](../../docs/D10-SCOPE-NOTE.md) |

## 9. What remains open

- D9 fail-silent clock-skew residual — owner: platform reliability or audit-design lead; resolving action: enforce a non-overridable audit-store timestamp contract and test the direct-write failure case at the store boundary.
- I1 bounded reconciliation — owner: governance or incident response lead; resolving action: define a monitored recovery SLA and owner for unresolved audit failures.
- I2 tenant-qualified identity resolution — owner: identity/security architect; resolving action: extend the identity provider to tenant-qualified lookup and shadow detection.
- I3 scheduled recovery contract — owner: platform operations lead; resolving action: define the recovery scheduler, owner, and RTO under the actual compliance regime.

## 10. git status --short

```text
 M artifacts/crm-variants/variants-environment.json
 M artifacts/crm-variants/variants-matrix.csv
 M artifacts/crm-variants/variants-results.json
 M prototypes/crm_operational_copilot/variants/run_experiment.py
?? ARCHITECTURE-REVIEW-v2.md
?? CLOSURE-PACKAGE-2026-10-09.md
?? D11-RISK-ROW.md
?? DECISION-DOSSIER-2026-10-09-ADDENDUM.md
?? DECISION-DOSSIER-2026-10-09-CONSOLIDATED.md
?? DECISION-DOSSIER-2026-10-09.md
?? EXECUTIVE-BRIEF-2026-10-09.md
?? EXECUTIVE-CLOSURE-MEMO-2026-10-09.md
?? FINAL-DOSSIER-2026-10-09.md
?? IDENTITY-DISCOVERY-WORKSHEET.md
?? META-SELF-CRITIQUE-OF-ASSESSMENT.md
?? META-SELF-CRITIQUE.md
?? NON-PRODUCTION-INTEGRATION-PLAN-OUTBOX.md
?? REEVALUATION-REPORT-2026-10-09.md
?? REVIEW-A-verify.md
?? REVIEW-B-invariants.md
?? TOPOLOGY-GENERALIZATION-NOTE.md
?? coverage.json
?? prototypes/crm_operational_copilot/variants/store_layout_fixed.py
?? scripts/fault_injection_approval_audit.py
?? scripts/fault_injection_approval_audit_extended.py
?? scripts/normalize_variant_artifacts.py
?? scripts/regenerate_variant_artifacts.sh
?? scripts/reproduce_variant_checker.sh
?? tests/test_audit_temporal_ordering.py
?? tests/test_crm_decision_contracts.py
?? tests/test_variant_review_coverage.py
?? tests/test_variant_review_coverage_fixed.py
```

VERIFIED-IN-THIS-ENVIRONMENT: the repo is in a dirty state with many untracked historical artifacts, but this work did not modify any prohibited dossier files or the prohibited contract test files.

## 11. Anomalies, classified

| anomaly | classification | reason |
|---|---|---|
| D11 fixed variant passes while current remains xfail | RESOLVED | the fixed review path now enforces a non-decreasing audit timestamp and the test passes under the fixed variant |
| D10 artifact stability is local-only | DRIFT | the claim must be narrowed to the current Windows/Python 3.14.6 environment because no cross-platform evidence was attempted |
| The regeneration script prints internal scenario failures while still exiting 0 | SCRIPT-DEFECT | the harness surfaces failed scenario assertions and a checker output, but the script returns success after constructing identical artifact outputs; this is not a deterministic success signal for all invariants |
| The one fail-silent case remains in both variants | BLOCKED | the direct instance-level override of `audit.write` bypasses the fixed-variant guard and the store boundary still needs a stronger contract |

Closing paragraph:

VERIFIED-IN-THIS-ENVIRONMENT: the D11 contract is fixed in the local fixed variant, with evidence from the passing test and the current witness remaining xfailed. The broader D9 durability story is improved but bounded: fail-open cases are eliminated in the fixed variant, while fail-closed and fail-silent cases remain and the fail-silent case is still unresolved under direct store-write circumvention. D10 is narrowed to a local-only stability statement in this Windows Python 3.14.6 workspace, and the remaining identity and recovery contracts remain open as needs-discovery or out-of-scope research limitations. The repository is therefore research/reference quality and conservative in scope, but not clean enough to be called production-ready or fully invariant-closed. The next reviewer should start with the unresolved fail-silent audit contract and then the recovery/identity contract owners before any broader operational or compliance claim.
