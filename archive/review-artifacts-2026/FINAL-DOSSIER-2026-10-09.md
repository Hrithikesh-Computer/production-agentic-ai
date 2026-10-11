# Final Decision Dossier — Production Agentic AI Reference Repository

> **Supersedes:** [DECISION-DOSSIER-2026-10-09.md](../../archive/review-artifacts-2026/DECISION-DOSSIER-2026-10-09.md), [DECISION-DOSSIER-2026-10-09-ADDENDUM.md](../../archive/review-artifacts-2026/DECISION-DOSSIER-2026-10-09-ADDENDUM.md), and [DECISION-DOSSIER-2026-10-09-CONSOLIDATED.md](../../archive/review-artifacts-2026/DECISION-DOSSIER-2026-10-09-CONSOLIDATED.md). The earlier files are retained unchanged; this is the reconciled decision record.

**Assessment date:** 2026-10-09. Evidence scope is local Windows 11 / CPython 3.14.6 / SQLite fake-backed tests and Git for Windows Bash. No claim below is verified in deployment.

## 1. Executive Summary

This repository is a research handbook and local reference suite, not a production AI platform. Fresh local tests support the baseline concerns around tenant identity, audit ordering, manual recovery, and approval audit. A sibling fixed variant now makes the tested review approval state and audit event share a deferred SQLite transaction, and its failure witness plus unsafe control pass. An extended campaign reproduced the current review fail-open after an actual child-process exit and ENOSPC injection; the fixed path returned to `PENDING` after those cases. The campaign also found invalid audit timestamp ordering in both variants, and it did not test hardware power loss. The writer-side LF change made the canonical artifact checker pass with all three files byte-identical on a repeated run. **Recommendation: adapt as architecture/test input only, not as a production component (high confidence); build/buy/defer choice for a real workflow remains conditional (medium confidence) because business, tenant, regulatory, cost, and value inputs are UNKNOWN.**

## 2. Verified Facts vs. Inference

### Verified in this environment

- The final focused run passed 38 tests, xfailed 8 known defect witnesses, and deselected 5 stress tests; the dedicated S01–S17 state run passed 17. Raw output is in Section 7.
- `SingleFileExecutionService` wraps `execute()` only; `SingleFileExecutionServiceWithAtomicReview` adds `review()` deferral and rollback on unresolved/audit error: [original variant](../../prototypes/crm_operational_copilot/variants/store_layout.py#L229), [fixed sibling](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10).
- The fixed review test covers healthy audit, failed audit/no subsequent execution, and an unsafe control: [fixed tests](../../tests/test_variant_review_coverage_fixed.py#L58).
- The base five-point campaign reports 4/5 current FAIL-OPEN and 0/5 fixed FAIL-OPEN; extended campaign is appended under `durability-20261009-01` in [campaign CSV](../../artifacts/fault-injection-approval-audit.csv#L12).
- The extended campaign uses a real child process terminated by `os._exit(87)` after current approval state commit and before audit call; this is distinct from the earlier `SystemExit` injected in-process: [extended worker](../../scripts/fault_injection_approval_audit_extended.py#L87).
- The writer now pins LF for matrix CSV and both JSON outputs: [run_experiment.py](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L230). The regeneration script ran twice; the second run reported pre-regeneration equality, checker exit 0, and all three byte-equal results (raw output, Section 7).
- S01–S17 passed after artifact regeneration: [captured test run](#raw-output-of-every-test-and-script-run-in-this-session).

### Verified in prior run, not re-run here

- The separate 12-combination tenant witness was reported in the prior addendum, Section E; this run did not rerun that parameter sweep. The principal-only identity map remains directly visible at [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L39).
- Prior fixed review tests reported 3 passing cases; this run’s final combined test run re-ran them with 3 passes. No live identity provider, CRM, audit service, or deployment was exercised.

### INFERENCE and UNKNOWN

- **INFERENCE:** tenant identity is the first security remediation if the actual workflow is multi-tenant. **UNKNOWN:** whether the target workflow is multi-tenant; resolve through product tenancy and IdP subject/tenant design (product + security).
- **INFERENCE:** the fixed deferred-commit pattern is a useful local design input, not a service-level guarantee. **UNKNOWN:** real CRM transaction/idempotency capabilities, crash/power-loss durability, and outbox behavior; resolve through non-production integration and restore tests (CRM/data + operations).
- **UNKNOWN:** real failure likelihood, applicable compliance/audit obligations, RPO/RTO, business value, vendor capabilities, and TCO; resolve through telemetry/fault injection, compliance mapping, operations objectives, pilot measurement, and procurement evidence.

## 3. Invariant Status

Statuses: HOLDS / VIOLATED / UNTESTED / CANNOT-DETERMINE. I7 is explicitly limited to the execution-audit response contract and does not imply approval-decision audit completeness.

| ID | Invariant | Status | Evidence |
|---|---|---|---|
| I1a | Every committed CRM mutation has a matching durable audit atomically or within a bounded monitored window. | **VIOLATED** in baseline; **UNTESTED** as a real-service guarantee in the fixed SQLite topology. | Baseline failure leaves version 2, ledger 1, audit 0: [test](../../prototypes/crm_operational_copilot/test_execution_service.py#L177). Recovery is on-demand: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L291). |
| I1b | Approval/rejection state is not executable/terminal unless correlated decision audit is durable or durably pending reconciliation. | **VIOLATED** in current variant; **HOLDS locally** in fixed review failure tests. | Fixed review rollback and no-execution witness: [test](../../tests/test_variant_review_coverage_fixed.py#L79). Current method writes approval state before audit: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L244). |
| I2 | Resolution and authorization are functions of `(principal, tenant)` and reject mismatch. | **VIOLATED**. | `_identities` uses principal string and `resolve/authorize` omit tenant: [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L39). Tenant sweep is verified in prior run, not re-run here (prior addendum Section E). |
| I3 | Owned scheduled recovery meets defined RPO/RTO and unresolved work is observable. | **VIOLATED / NOT OPERATIONALIZED**. | `recover()` is explicitly on-demand: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L291); NFR recovery targets are TBD: [05-nfr-and-sizing.md](../../architecture/05-nfr-and-sizing.md#L14). |
| I6 | Consequential decisions and mutations have durable, correlated, protected audit evidence. | **VIOLATED** overall. | Approval path can omit its event; local audit lacks tamper-resistance/retention: [review code](../../prototypes/crm_operational_copilot/execution_service.py#L256), [container notes](../../architecture/01-context-and-containers.md#L26). Clock-skew campaign also emitted an event at timestamp 90 for approval timestamp 150 (Section 7). |
| I7 | Execution does not report completed if its own required execution-audit write fails. | **HOLDS locally, scoped only to execution response.** | Existing execution failure test asserts unresolved, not completed: [test](../../prototypes/crm_operational_copilot/test_execution_service.py#L177). It does not cover review audit. |

## 4. Variant × Invariant Matrix

Each cell includes a file/test citation. CLOSES is bounded to the tested local contract. MOVES means one local failure boundary is reduced but the broader invariant remains unproven. I4 is sequential at-most-once; I5 is stale record/policy binding.

| Variant | I1a | I1b | I2 | I3 | I6 | I7 | I4 | I5 |
|---|---|---|---|---|---|---|---|---|
| Three-store baseline | OPEN [audit gap](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | OPEN [review witness](../../tests/test_crm_decision_contracts.py#L207) | OPEN [principal key](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [manual recovery](../../prototypes/crm_operational_copilot/execution_service.py#L291) | OPEN [failed approval audit](../../tests/test_crm_decision_contracts.py#L231) | CLOSES [unresolved response](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | CLOSES [replay test](../../tests/test_crm_decision_contracts.py#L125) | CLOSES [stale test](../../tests/test_crm_decision_contracts.py#L162) |
| `store-layout-b` | MOVES [execute rollback only](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | OPEN [inherited review failure](../../tests/test_variant_review_coverage.py#L71) | OPEN [unchanged identity provider](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [on-demand only](../../prototypes/crm_operational_copilot/execution_service.py#L291) | OPEN [review event absent](../../tests/test_variant_review_coverage.py#L71) | CLOSES [unresolved/rollback](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | CLOSES [local S17](../../artifacts/crm-variants/variants-matrix.csv#L35) | CLOSES [local S07](../../artifacts/crm-variants/variants-matrix.csv#L25) |
| `recovery-b` | OPEN [recovery-only override](../../prototypes/crm_operational_copilot/variants/recovery.py#L38) | OPEN [base review inherited](../../prototypes/crm_operational_copilot/variants/implementations.py#L36) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [no scheduler](../../prototypes/crm_operational_copilot/execution_service.py#L291) | OPEN [base review witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [local S12](../../prototypes/crm_operational_copilot/variants/VARIANTS-FINDINGS.md#L13) | UNTESTED [not included in N=50 test](../../prototypes/crm_operational_copilot/variants/test_claims.py#L8) | CLOSES [local S07](../../artifacts/crm-variants/variants-matrix.csv#L42) |
| `claim-b` | OPEN [claim-only override](../../prototypes/crm_operational_copilot/variants/claims.py#L13) | OPEN [base review inherited](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [no scheduler](../../prototypes/crm_operational_copilot/execution_service.py#L291) | OPEN [base review witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [local S12](../../artifacts/crm-variants/variants-matrix.csv#L64) | CLOSES [N=50 test](../../prototypes/crm_operational_copilot/variants/test_claims.py#L8) | CLOSES [local S07](../../artifacts/crm-variants/variants-matrix.csv#L59) |
| `broken-control` | OPEN [claim-only negative control](../../prototypes/crm_operational_copilot/variants/claims.py#L35) | OPEN [base review inherited](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [no scheduler](../../prototypes/crm_operational_copilot/execution_service.py#L291) | OPEN [base review witness](../../tests/test_crm_decision_contracts.py#L207) | CLOSES [S12 response only](../../artifacts/crm-variants/variants-matrix.csv#L81) | OPEN [50 claims accepted](../../artifacts/crm-variants/variants-matrix.csv#L78) | CLOSES [local S07](../../artifacts/crm-variants/variants-matrix.csv#L76) |
| `store_layout_fixed` | MOVES [shared SQLite only](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10) | CLOSES [local rollback/no execute](../../tests/test_variant_review_coverage_fixed.py#L79) | OPEN [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | OPEN [manual recovery unchanged](../../prototypes/crm_operational_copilot/execution_service.py#L291) | MOVES [review only, no global audit integrity](../../tests/test_variant_review_coverage_fixed.py#L79) | CLOSES [inherited execution contract](../../prototypes/crm_operational_copilot/variants/store_layout.py#L232) | CLOSES [local replay test](../../tests/test_crm_decision_contracts.py#L125) | CLOSES [local stale check](../../tests/test_crm_decision_contracts.py#L162) |

The fixed variant is not in the committed variant matrix because the allowed code is an isolated sibling module; its dedicated test and extended campaign provide evidence. It closes I1b for the tested same-SQLite deferred transaction, not cross-service atomicity, power-loss durability, or I6 as a whole.

## 5. Risk Register D1–D10

Likelihood is local reachability where specifically stated, not a deployment probability. Priorities are conditional on the missing business context.

| ID / statement | Scope | Likelihood | Impact | Detection | Reversibility | Priority | Mitigation | Owner | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **D1:** Same principal in two tenants overwrites identity and resolves without tenant check. | Identity → authorization. | High locally; production frequency UNKNOWN. | High if multi-tenant: isolation/data disclosure. | Collision test; no runtime alert. | Low before deployment; high after disclosure. | Tenant-qualified subject key and end-to-end tenant checks; collision and mismatch tests. | Security + identity | [identity key](../../prototypes/crm_operational_copilot/identity_provider.py#L39). |
| **D2:** CRM mutation commits before independent audit; a gap remains until manual recovery. | CRM + ledger → audit. | High under injected failure; operational frequency UNKNOWN. | High for traceability/compliance/forensics. | Caller gets unresolved; no bounded monitor. | Moderate if ledger survives; high if evidence is lost. | Shared transaction only where genuinely available; otherwise durable outbox, bounded monitor, idempotent reconciliation. | CRM/data + audit + ops | [failure witness](../../prototypes/crm_operational_copilot/test_execution_service.py#L177). |
| **D3:** Recovery is manual/on-demand with no named owner or RPO/RTO. | Recovery operations. | Certain local capability gap. | High availability/audit lag risk. | Query rows manually; no automatic age alert. | Moderate while state and ledger persist. | Assign owner, schedule, RPO/RTO, backlog alert, recovery and restore runbook. | SRE/ops | [recover](../../prototypes/crm_operational_copilot/execution_service.py#L291); [NFR TBD](../../architecture/05-nfr-and-sizing.md#L14). |
| **D4:** Audit store lacks tamper evidence/retention guarantees; some state transitions survive failed audit. | Audit persistence and access. | Absence locally verified; attack frequency UNKNOWN. | High where compliance/forensic evidence is required. | Injected write errors visible; unauthorized alteration is not evidenced as detectable. | High after evidence alteration/retention loss. | Define immutable sink, access, retention/legal hold, integrity proofs; test deletion/tampering. | Audit + security/compliance | [audit limitation](../../architecture/01-context-and-containers.md#L26). |
| **D5:** Local evidence may be mistaken for deployment validation. | Claims/procurement. | Medium inference: caveats exist, but docs conflict. | High trust/procurement impact if overstated. | Cross-doc review; no single generated evidence inventory. | Moderate before claims; hard after reliance. | Canonical evidence level with commit/environment provenance and CI check. | Product + architecture | [README L3 boundary](../../README.md#L47); [EVIDENCE limits](../../prototypes/crm_operational_copilot/EVIDENCE.md#L52). |
| **D6:** Docs disagree about implementation status and inventory. | Repo map/validation contract/architecture. | High local occurrence. | Medium–High decision and maintenance risk. | Manual comparison. | Low for prose, higher for decisions made from it. | Refresh map and stale contract; add current-path consistency check. | Architecture/docs | [REPO-MAP dated snapshot](../../REPO-MAP.md#L3); [pending claim](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L226). |
| **D7:** Business differentiator/ROI has not been demonstrated. | Funding strategy. | UNKNOWN whether value exists. | Medium–High opportunity cost. | Needs real task baseline. | Low before investment, high after sunk cost. | Measure one task, review labor, rework, and 3-year cost before funding. | Product + finance | [TCO unknown](../../architecture/07-cost-model.md#L3); [no delivery benefit claim](../../benchmarks/response-delivery/README.md#L29). |
| **D8:** Local CRM schema supports one field row per customer. | CRM data model. | Certain local constraint; workflow relevance UNKNOWN. | Medium correctness/generalization risk if scope expands. | Multi-field test/schema review. | Moderate if assumptions propagate. | Confirm scope; use tenant/customer/field key before broadening. | CRM/data | [primary key](../../prototypes/crm_operational_copilot/crm_store.py#L43). |
| **D9:** Approval state can remain executable when its approval audit write fails. | `review()` → approval store → audit → `execute()`. | **4/5 FAIL-OPEN** in base five enumerated injections; extended current 2/5 FAIL-OPEN, 2/5 closed, 1/5 silent. These are fault-point counts, not event probabilities. | High conditional on approval audit as a control; not evidence of unauthorized reviewer identity. | Review returns unresolved for exception cases, but state persists and can execute; clock order anomaly is not flagged. | Before execute may be remediated; after mutation contemporaneous approval evidence is absent. | Fixed state+event transaction or durable event/outbox; block execute until valid event; timestamp/ordering validation and monitor. | Security + CRM/data + audit | [base and extended CSV](../../artifacts/fault-injection-approval-audit.csv#L2); [base review ordering](../../prototypes/crm_operational_copilot/execution_service.py#L256). |
| **D10:** Windows artifact writer previously emitted CRLF matrix while generated artifact expected LF. | Experiment tooling/artifacts. | Previously reproducible; after writer fix **resolved locally** on repeated checker runs. Other CI platforms UNKNOWN. | Low–Medium evidence reproducibility. | Checker now exits 0 and compares all files. | Low. | Keep explicit newline policy and cross-platform CI. | Build/release | [writer LF](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L230); [second-run raw output Section 7]. |

## 6. Ranked Register and If-Only-One Decision

| Rank | Risk | Rationale | Confidence |
|---:|---|---|---|
| 1 | D1/I2, if multi-tenant | Tenant omitted from identity key; direct collision witness was verified in prior run, not repeated as a separate sweep here. | Medium; actual tenant model UNKNOWN. |
| 2 | D9/I1b | Upstream of CRM write and demonstrably executable without approval event in the current variant; extended current count includes actual process exit and ENOSPC injection. | High local, medium priority order. |
| 3 | D2/I1a | Mutation may precede audit, but returns unresolved and can be manually reconciled; no bounded recovery. | High local. |
| 4 | D3/I3 | No scheduled/owned recovery. | High capability confidence. |
| 5 | D4 | Audit tamper/retention protections absent locally. | High as local absence; impact conditional. |
| 6 | D5 | Evidence boundary can be misread despite explicit caveats. | Medium. |
| 7 | D6 | Stale/conflicting documentation. | High local occurrence. |
| 8 | D7 | No measured ROI. | High as evidence gap; business impact UNKNOWN. |
| 9 | D8 | Single-field local model. | Medium, scope conditional. |
| 10 | D10 | Resolved in current environment by LF writer and regenerated artifacts. | High local. |

**D9 versus D2:** D9 leads D2 for a workflow requiring approval audit because it is upstream and leaves a nominally approved state executable without decision evidence; D2 is also serious but is surfaced as unresolved with a ledger recovery path. This ordering does not establish that a reviewer was unauthorized. **Confidence: medium, conditional on approval audit being mandatory.**

**If only one:** address D1 first only if product confirms multi-tenancy; otherwise address D9 before D2 for a write-enabled audited workflow. No unconditional risk winner is defensible until tenant and audit requirements are confirmed. **Confidence: medium.**

## 7. Fault-Injection Results

Base five-point campaign is from the prior run, verified in prior run and preserved in the campaign CSV; this run re-ran the extended campaign only. Base results were current 4/5 FAIL-OPEN, 1/5 FAIL-CLOSED, 0 FAIL-SILENT; fixed 0/5 FAIL-OPEN, 5/5 FAIL-CLOSED, 0 FAIL-SILENT (prior consolidated dossier Section 7; base rows in [CSV](../../artifacts/fault-injection-approval-audit.csv#L2)).

Extended campaign, verified in this environment:

| Variant | Process exit after state commit | ENOSPC | Commit/fsync hook proxy | Corruption on reopen | Clock skew | Totals |
|---|---|---|---|---|---|---|
| Current | FAIL-OPEN | FAIL-OPEN | FAIL-CLOSED | FAIL-CLOSED | FAIL-SILENT | **2 open / 2 closed / 1 silent** |
| Fixed | FAIL-CLOSED | FAIL-CLOSED | FAIL-CLOSED | FAIL-CLOSED | FAIL-SILENT | **0 open / 4 closed / 1 silent** |

The process-exit row uses child-process `os._exit(87)`, verified at [extended script](../../scripts/fault_injection_approval_audit_extended.py#L87). ENOSPC uses an injected `OSError(errno.ENOSPC)`. The “fsync” point is a simulated hook raised after `AuditStore.write()` returns; it is **not** a real OS fsync or power-loss test, as recorded in [campaign CSV](../../artifacts/fault-injection-approval-audit.csv#L14). Corruption is invalid bytes written into the shared SQLite file after closing connections; both variants fail to reopen and do not execute. Clock skew moves audit timestamp 60 seconds before approval state timestamp; both variants persist and execute, but the chronology defect is not rejected.

**D9 grounding:** code-path reachability and one process-restart case are now grounded. **UNKNOWN:** probability under production dependency behavior, power-loss durability, real disk-full behavior, Windows/SQLite filesystem guarantees, and cross-store atomicity in a non-SQLite topology. The 2/5 or 4/5 counts are enumerated test cases, not probabilities.

## 8. Artifact Reproducibility (D10)

**Classification: REPRODUCIBLE in this environment.** `run_experiment.py` opens the matrix and both JSON outputs with explicit `newline="\n"` [writer](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L230). The authorized scope was experiment tooling plus regenerated experiment artifacts only; no runtime code was changed. Two captured executions of [regenerate_variant_artifacts.sh](../../scripts/regenerate_variant_artifacts.sh) exited 0; the second found all three files byte-identical before rewriting, checker exit 0, and each post-run `byte_equal=true`. The first invocation through the direct terminal returned only its initial two lines; a captured Git Bash subprocess run resolved that output-capture anomaly. No semantic artifact changes were observed beyond newline normalization.

## 9. Topology Generalization Summary

Detailed discussion and falsifiable tests are in [TOPOLOGY-GENERALIZATION-NOTE.md](../../TOPOLOGY-GENERALIZATION-NOTE.md). **INFERENCE, medium confidence:**

| Topology | I1a | I1b | Decision/use condition | Falsifiable pre-adoption test |
|---|---|---|---|---|
| Transactional outbox + CDC | Pending remote CRM acknowledgment requires bounded reconciliation; atomic only for participants in local transaction. | Strong at approval/outbox boundary if both persist together. | Choose when asynchronous audit lag is acceptable and queue/CDC operation is funded; not strict global atomicity. | Crash after remote commit before acknowledgment; replay twice; prove one CRM mutation and bounded audit reconciliation. |
| 2PC / saga | 2PC only if every participant supports durable prepare/commit; saga is compensation, not atomicity. | 2PC can coordinate; saga requires durable approval intent/compensation. | 2PC for limited transactional participants and tolerable blocking; saga when compensation/reconciliation is acceptable and owned. | Kill coordinator at all prepare/commit points; verify state convergence and stuck transaction alert/RTO. |
| Event-sourced audit + at-least-once idempotent apply | Event intent is atomic to log; CRM effect needs idempotent conditional apply and monitored confirmation. | Durable approval event can precede execution. | Choose for replay/chronology needs if log operations and idempotent CRM apply are mature; not immediate global commit. | Duplicate delivery + consumer crash around CRM acknowledgment; prove no duplicate side effect and no premature success. |

The local SQLite fix proves the tested code path only; it does **not** prove real cross-service atomicity, power-loss recovery, or outbox semantics.

## 10. Vendor Comparison Matrix and Scoring Rule

No product capability is asserted. C/D are categories pending named SKUs and contract evidence. Weights total 100; score 0–5 (0 absent, 1 weak, 2 partial, 3 plausible/unverified, 4 verified for scope, 5 independently validated). Leave UNKNOWN blank, not zero, and do not total while critical evidence is missing. Gates I1a/I1b/I2/I3/I4/I5 are non-compensatory.

| Criterion | Weight | A: Adapt repo | B: Build | C: Commercial CRM-native category | D: Commercial workflow/agent category | E: Existing CRM/IdP |
|---|---:|---|---|---|---|---|
| Real authenticated IdP | 10 | UNKNOWN: local IDs only; which IdP contract? | UNKNOWN: implementation/test plan? | UNKNOWN: named SKU identity/tenant guarantees? | UNKNOWN: same? | UNKNOWN: existing claim enforcement? |
| Tenant isolation I2 | 10 | Known local failure; redesign needed. | UNKNOWN: isolation proof? | UNKNOWN: contractual tenant boundary? | UNKNOWN: contractual tenant boundary? | UNKNOWN: CRM/IdP row-level boundary? |
| CRM field enforcement | 8 | UNKNOWN for real CRM. | UNKNOWN API enforcement? | UNKNOWN object/field controls? | UNKNOWN object/field controls? | UNKNOWN current native permissions? |
| Approval binds current record/policy | 9 | Partial fake test; live semantics UNKNOWN. | UNKNOWN concurrency/version design? | UNKNOWN exact payload recheck? | UNKNOWN exact payload recheck? | UNKNOWN native version-bound approval? |
| At-most-once execution | 8 | Local only; distributed UNKNOWN. | UNKNOWN idempotency contract? | UNKNOWN API retry/idempotency? | UNKNOWN API retry/idempotency? | UNKNOWN native retry behavior? |
| Atomic/tamper-evident audit | 12 | Fixed SQLite local I1b; I1a service topology UNKNOWN. | UNKNOWN transactional/outbox design? | UNKNOWN retention/integrity contract? | UNKNOWN retention/integrity contract? | UNKNOWN audit export/immutability? |
| Recovery RPO/RTO/owner | 9 | No owner/scheduler currently. | UNKNOWN operational design? | UNKNOWN SLA/support tier? | UNKNOWN SLA/support tier? | UNKNOWN current ownership/objective? |
| Time-to-value | 5 | Reference speeds experiments; integration UNKNOWN. | UNKNOWN staff/scope estimate? | UNKNOWN SKU/configuration time? | UNKNOWN integration time? | UNKNOWN whether already licensed/configured? |
| Three-year TCO | 7 | UNKNOWN, no real volumes/prices. | UNKNOWN build/support cost? | UNKNOWN quote and services? | UNKNOWN quote and services? | UNKNOWN license/admin/manual cost? |
| Lock-in/exit | 4 | Reference portable; adapter coupling UNKNOWN. | UNKNOWN internal coupling? | UNKNOWN export/exit terms? | UNKNOWN export/exit terms? | UNKNOWN current vendor dependence? |
| Differentiation | 4 | No customer outcome evidence. | UNKNOWN proprietary value? | UNKNOWN product-specific value? | UNKNOWN product-specific value? | UNKNOWN native sufficiency? |
| Compliance posture | 8 | No production compliance evidence. | UNKNOWN controls/attestation? | UNKNOWN applicable certification/DPA/region? | UNKNOWN same? | UNKNOWN current contract/config? |
| Operational SLA/support | 6 | No deployed support model. | UNKNOWN on-call owner? | UNKNOWN contract SLA? | UNKNOWN contract SLA? | UNKNOWN existing responsibility boundary? |

**Recommendation (high confidence):** do not adopt the repo as a production platform. **Recommendation (medium confidence):** assess existing native CRM/IdP capabilities first, then named commercial candidates and build only if control gaps plus measured value justify it. Product, tenant, compliance, cost, and ROI facts remain UNKNOWN.

## 11. Re-scored Adapt Scope

- Adapt as reference/test input for I1b locally, I4 sequential replay, I5 stale-state checks, and I7 execution response behavior. Evidence is local to SQLite fakes [fixed witness](../../tests/test_variant_review_coverage_fixed.py#L79), [claim/replay test](../../tests/test_crm_decision_contracts.py#L125), [stale test](../../tests/test_crm_decision_contracts.py#L162).
- Remains open: I1a across actual CRM/audit services and power-loss; I2 tenant identity; I3 operational recovery; I6 complete, ordered, tamper-evident audit. The clock-skew result specifically shows audit chronology is not currently enforced in either local variant (Section 7).
- **Trigger to change adapt to build (medium confidence):** named CRM/IdP/native and commercial candidates fail mandatory I1a/I1b/I2/I3/I4/I5 acceptance gates, and a measured workflow benefit exceeds three-year custom-service cost. Resolve with a bounded requirements and procurement evaluation; do not infer it from the repo.

## 12. Self-Critique

### Three weakest claims in this dossier

1. **“Fixed variant closes I1b.”** It closes the tested shared-SQLite path, not real service topology. Falsify by process/power loss after commit or by running against separate remote stores. Confidence: high local, low external.
2. **D9 rate summaries.** Fault-point ratios are enumeration counts, not probability estimates. A workload-weighted or observed dependency failure campaign could materially change likelihood. Confidence: high on counts, low on production likelihood.
3. **D10 is reproducible beyond this Windows environment.** Two Windows/Bash runs passed; Linux/macOS CI could expose different path/runtime behavior. Confidence: high local, medium across platforms.

### Three weakest claims in prior runs

1. Prior D9 ranking above D2 was too unconditional; now it is conditional on mandatory approval evidence and explicitly distinguishes an unaudited valid approval from unauthorized identity.
2. Prior local recovery wording could suggest operational recovery; it was only explicit/manual `recover()`. It remains unbounded without scheduler, owner, and objective.
3. Prior shared transaction finding did not cover inherited review(); the review witness fixed that gap; the current fixed module now covers only the local `review()` transaction path.

### Unknown and confidence corrections

- Production likelihood for D1/D2/D4/D9 is UNKNOWN; a 4/5 injected-case count is not an incident probability.
- “Power loss” remains UNKNOWN: an OS process exit is not sudden power loss or storage controller failure.
- The fsync fault point is a post-`AuditStore.write()` injected hook, not an interception of SQLite’s underlying OS fsync. It is recorded as a simulation in the campaign CSV.
- Clock skew is observed as an audit event earlier than approval timestamp; FAIL-SILENT here means the invalid ordering was not rejected/reported, not that no event exists.
- No claim about vendor capabilities or business ROI is made; all are UNKNOWN pending named products, quotes, and measured workflows.

## 13. Open Questions

| UNKNOWN | Resolving action | Owner role |
|---|---|---|
| Tenant model and authoritative tenant assertion | Document IdP subject/tenant mapping and test same-name/cross-tenant denial. | Security + identity platform |
| Audit atomicity and lag tolerance | Set legal/control requirements, retention, tamper evidence, maximum lag. | Audit + compliance + product |
| CRM transaction/idempotency support | Test conditional writes, timeout-after-commit, idempotency, and reconciliation in sandbox. | CRM/data owner |
| Recovery RPO/RTO and ownership | Assign on-call, schedule, oldest-backlog alert, restore runbook and drill. | Operations/SRE |
| Crash/power-loss durability | Kill-process and restore tests, then hardware/storage durability review; do not equate OS exit with power loss. | Data platform + operations |
| Vendor/build economics and ROI | Collect named SKUs/contracts, three-year costs, task baseline and reviewer effort. | Procurement + product + finance |
| Cross-platform artifact pipeline | Run LF writer/checker on Windows and CI POSIX; enforce byte comparison. | Build/release engineering |

## 14. Recommended Next Step

Run one bounded non-production validation with synthetic data and writes disabled in the live CRM: prove tenant-qualified identity, I1b rollback, CRM conditional/idempotent behavior, audit chronology and recovery, plus named RPO/RTO ownership. Include a one-task value/TCO baseline before choosing build/buy. **Recommendation confidence: high** for this evidence step; **medium** on duration and topology until owners specify requirements.

**Stop criteria:** no write-enabled pilot if I1a/I1b/I2/I3/I4/I5 fail; stop if unresolved operations cannot be detected/reconciled within the owner-approved bound; defer investment if measured benefit does not exceed full three-year cost. Numeric thresholds are UNKNOWN until assigned by product, audit, and operations.

## Raw Output of Tests and Scripts Run in This Session

### First direct regeneration attempt

```text
interpreter=/c/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe
working_directory=/c/Users/HP/Documents/GitHub/production-agentic-ai
```

The terminal bridge returned only these two lines. This was treated as incomplete output; the captured rerun below resolved it.

### Captured regeneration/checker run (first successful run)

```text
bash_exit_code= 0
matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
broken_control_n50=accepted:50/50 single_winner_assertion:False
pre_regeneration_byte_equal=true file=variants-matrix.csv
pre_regeneration_byte_equal=true file=variants-results.json
pre_regeneration_byte_equal=true file=variants-environment.json
CRM variant evidence matches deterministic regeneration: variants-matrix.csv, variants-results.json
checker_exit_code=0
byte_equal=true file=variants-matrix.csv
byte_equal=true file=variants-results.json
byte_equal=true file=variants-environment.json
artifact_diff_exit_code=0
```

The harness also preserved expected variant-specific S10/S11/S12 baseline assertions in its captured tails: S10 expected APPROVED but recovery variant wrote INVALIDATED; S11/S12 expected baseline EXECUTING/AUDIT_PENDING but shared transaction rolled back to APPROVED. Harness return code was 0; checker return code was 0.

### Required S01–S17 post-regeneration test

```text
collected 24 items / 7 deselected / 17 selected
S01 PASSED
S02 PASSED
S03 PASSED
S04 PASSED
S05 PASSED
S06 PASSED
S07 PASSED
S08 PASSED
S09 PASSED
S10 PASSED
S11 PASSED
S12 PASSED
S13 PASSED
S14 PASSED
S15 PASSED
S16 PASSED
S17 PASSED
====================== 17 passed, 7 deselected in 0.85s =======================
```

One PowerShell invocation failed before Python started because the call operator token was rejected; retry with the fully quoted executable passed. The parser error was terminal syntax only.

```text
At line:1 char:2
+ & ".\.venv\Scripts\python.exe" -m pytest -v tests/test_crm_validatio ...
+  ~
The ampersand (&) character is not allowed. The & operator is reserved for
future use; wrap an ampersand in double quotation marks ("&") to pass it as a string.
```

### Extended fault campaign: failed attempts and final run

The first attempt failed after duplicate approval setup and then hit a Windows SQLite file lock during temp cleanup. The second attempt fixed the duplicate for normal cases but still duplicated setup in the corruption case and hit the same lock. Both were harness setup defects; neither wrote campaign rows. Their raw exception signatures were:

```text
sqlite3.IntegrityError: UNIQUE constraint failed: approvals.approval_id
PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: '...\\crm-variant.sqlite'
```

Final complete run:

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
csv_path=.../artifacts/fault-injection-approval-audit.csv
```

### Final focused pytest run

```text
x.xxxx.x......xx..............................                           [100%]
38 passed, 5 deselected, 8 xfailed in 11.61s
```

### Second regeneration/checker run (idempotence)

```text
bash_exit_code= 0
matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
pre_regeneration_byte_equal=true file=variants-matrix.csv
pre_regeneration_byte_equal=true file=variants-results.json
pre_regeneration_byte_equal=true file=variants-environment.json
CRM variant evidence matches deterministic regeneration: variants-matrix.csv, variants-results.json
checker_exit_code=0
byte_equal=true file=variants-matrix.csv
byte_equal=true file=variants-results.json
byte_equal=true file=variants-environment.json
artifact_diff_exit_code=0
```

### Shell syntax and diagnostics

```text
bash -n scripts/reproduce_variant_checker.sh: exit 0 (prior run)
Pylance: no errors in run_experiment.py, fault_injection_approval_audit_extended.py, regenerate_variant_artifacts.sh (this run).
```

## Anomaly Classification

- **D10: RESOLVED / REPRODUCIBLE locally.** Writer pins LF; two checker runs exit 0 and compare all three files byte-for-byte. Cross-platform CI remains untested.
- Initial direct regeneration bridge output was incomplete; captured subprocess run resolved the missing output. **RESOLVED.**
- Initial extended campaign setup duplicated rows and hit Windows SQLite locks; corrected setup, and final campaign completed with 10 rows. **RESOLVED harness defects.**
- Fsync/power-loss semantics remain **UNKNOWN**, not resolved by the injected post-write hook.