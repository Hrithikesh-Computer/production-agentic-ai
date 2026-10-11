# Consolidated Decision Dossier

**As of:** 2026-10-09  
**Decision posture:** Research/reference artifact. No production adoption is recommended by this dossier.  
**Evidence scope:** Windows 11, CPython 3.14.6, repository `.venv`, SQLite fakes, Git for Windows Bash. Nothing here is deployment-verified.

## 1. Executive Summary

This repository is a research handbook with local reference implementations and a deterministic CRM workflow experiment, not a production platform. Fresh tests confirmed the baseline tenant collision, execution-audit gap, manual-only recovery, and approval-audit fail-open. An isolated fixed review service now wraps approval state and approval audit in the same deferred SQLite transaction; its healthy, injected-failure, and regression-control tests all pass. A five-point local fault campaign found 4/5 FAIL-OPEN points in the current variant and 0/5 in the fixed variant, without proving production likelihood. LF-normalized copies of the three variant artifacts match fresh generated copies byte-for-byte, but the unchanged checker still exits 1 against committed CRLF artifacts. **Recommendation: adapt as a reference only, with high confidence that it should not be adopted as-is; production build/buy choice remains conditional and medium confidence because workflow, tenant model, regulatory requirements, costs, and value are UNKNOWN.**

## 2. Verified Facts vs. Inference

### Verified in this environment

- The unchanged contract suite ran: 8 passed, 8 xfailed; the combined run across contract, prior review, fixed review, and variant tests: 19 passed, 8 xfailed. Raw output is in Section 8.
- The fixed review test passed a healthy audit path, an audit failure rollback/no-execution witness, and an unsafe implementation regression control: [fixed review tests](../../tests/test_variant_review_coverage_fixed.py#L58).
- The fault campaign wrote ten rows to [fault-injection-approval-audit.csv](../../artifacts/fault-injection-approval-audit.csv): current 4/5 FAIL-OPEN, fixed 0/5 FAIL-OPEN.
- The shared transaction implementation overrides `execute()` only; the fixed sibling adds `review()` with deferred commit and rollback on unresolved/audit errors: [current wrapper](../../prototypes/crm_operational_copilot/variants/store_layout.py#L229), [fixed wrapper](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10).
- Variant artifact normalization in temporary copies is idempotent and makes all three generated/committed normalized artifacts byte-equal. Committed artifacts were not modified. Exact output appears in Section 9.
- The POSIX checker reproduction still exits 1 against committed artifacts; strict byte drift is isolated to `variants-matrix.csv` CRLF versus LF. The checker/harness results and normalized equality appear in Section 9.

### Verified in prior run, not re-run here

- Prior addendum’s 12-combination tenant witness sweep was reported as reproduced. This run re-ran the unchanged contract file, whose tenant identity cases xfailed, but did not re-run the separate sweep count. Current identity key evidence remains directly visible in [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L39).
- Prior run reported the source-level CRM mutation/audit failure witness and local scenario outcomes. This run re-ran `test_crm_decision_contracts.py` and variant tests; no live CRM or deployment was used.

### INFERENCE / UNKNOWN

- **INFERENCE:** for a genuinely multi-tenant target, I2 deserves first remediation because tenant is absent from the local identity key and lookup. Whether the target is multi-tenant is **UNKNOWN**; resolve with the product tenancy model and identity subject/tenant claims (security + product).
- **INFERENCE:** the fixed deferred-transaction pattern is a credible local design input for a single transactional resource, not proof for remote CRM/audit services. Crash durability, power-loss semantics, backup/restore, and external outbox delivery remain **UNKNOWN**; resolve with kill/restart, restore, and real non-production adapter tests (data platform + operations).
- Production failure frequencies, RPO/RTO, audit obligations, commercial alternatives, TCO, and ROI are **UNKNOWN**; resolve through fault telemetry, control mapping, procurement evidence, and a measured task baseline (operations, audit/compliance, procurement, product/finance).

## 3. Invariant Status

| ID | Statement | Current baseline | Evidence from this run |
|---|---|---|---|
| I1a | Every committed CRM mutation has matching durable audit atomically or within a bounded, monitored reconciliation window. | **VIOLATES** | The baseline test asserts CRM version 2, ledger 1, audit 0 after audit failure: [test_execution_service.py](../../prototypes/crm_operational_copilot/test_execution_service.py#L177). Recovery exists but is explicitly on-demand: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L291). Shared variant rollback is tested only within one SQLite resource: [variant test](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55). |
| I1b | A reviewer decision cannot be executable unless its approval/rejection audit event is durably committed or durably pending reconciliation. | **Baseline VIOLATES; fixed local variant CLOSES tested path.** | Base review calls state update then audit: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L244); fixed review defers commits and rolls back on unresolved/audit error: [fixed module](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10); fresh tests pass: [fixed test](../../tests/test_variant_review_coverage_fixed.py#L79). |
| I2 | Resolution and authorization use `(principal, tenant)` and deny tenant mismatch. | **VIOLATES** | Dict and insertion key use principal alone; resolve/authorize omit tenant: [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L39). The unchanged tenant witness cases xfail in Section 8. |
| I3 | Unresolved work is recovered by an owned schedule within agreed RPO/RTO and is observable. | **VIOLATES / NOT OPERATIONALIZED** | `recover()` is on-demand, with no scheduler: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L291); RTO/RPO are TBD: [NFR worksheet](../../architecture/05-nfr-and-sizing.md#L14). |
| I6 | Every consequential authorization, approval, rejection, execution, and result has a durable, correlated, protected audit record. | **VIOLATES** | Approval/rejection state commits before audit attempt: [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L137), [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L256). Local audit has no tamper-resistance/retention contract: [container notes](../../architecture/01-context-and-containers.md#L26). |
| I7 | An execution call never returns completed when its required execution-audit write fails. This invariant is scoped only to the execution-audit response contract. | **HOLDS locally** | Failure returns `unresolved` and records audit error in the existing witness: [test_execution_service.py](../../prototypes/crm_operational_copilot/test_execution_service.py#L177); shared execute variant rolls back unresolved result: [store_layout.py](../../prototypes/crm_operational_copilot/variants/store_layout.py#L232). Does not cover review audit (I1b/I6). |
| I4 | One approval cannot cause two sequential CRM mutations. | **HOLDS locally in tested path** | Conditional approval claim: [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L153); replay test passes in final combined output; CRM ledger execution ID uniqueness and transaction: [crm_store.py](../../prototypes/crm_operational_copilot/crm_store.py#L98). Deployment remains unverified. |
| I5 | Execution rejects stale record/policy state rather than mutating against an obsolete approval. | **HOLDS locally in covered path** | Expected record version checked before execute: [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L120); final combined output includes stale-record test passing. |

## 4. Variant × Invariant Matrix

Cells use **CLOSES / MOVES / OPEN / UNTESTED / CANNOT-DETERMINE**. Each cell carries local source or test evidence. “CLOSES” is bounded to tested local semantics, never deployment.

| Variant | I1a | I1b | I2 | I3 | I6 | I7 | I4 | I5 |
|---|---|---|---|---|---|---|---|---|
| Three-store baseline | **OPEN** [failure witness](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | **OPEN** [failed approval audit witness](../../tests/test_crm_decision_contracts.py#L207) | **OPEN** [principal-only map](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [on-demand recover](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **OPEN** [review audit witness](../../tests/test_crm_decision_contracts.py#L231) | **CLOSES** [unresolved execution result witness](../../prototypes/crm_operational_copilot/test_execution_service.py#L177) | **CLOSES** [replay control passed](../../tests/test_crm_decision_contracts.py#L125) | **CLOSES** [stale version check](../../tests/test_crm_decision_contracts.py#L162) |
| `store-layout-b` | **MOVES** [execute rollback only](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | **OPEN** [review failure witness](../../tests/test_variant_review_coverage.py#L71) | **OPEN** [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [on-demand only](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **OPEN** [no approval event witness](../../tests/test_variant_review_coverage.py#L71) | **CLOSES** [S12 rollback and unresolved](../../prototypes/crm_operational_copilot/variants/test_store_layout.py#L55) | **CLOSES** [S17 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L35) | **CLOSES** [S07 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L25) |
| `recovery-b` | **OPEN** [recovery-only override](../../prototypes/crm_operational_copilot/variants/recovery.py#L38) | **OPEN** [component map inherits base review](../../prototypes/crm_operational_copilot/variants/implementations.py#L36) | **OPEN** [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [no schedule](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **OPEN** [review witness applies unchanged](../../tests/test_crm_decision_contracts.py#L207) | **CLOSES** [S12 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L47) | **UNTESTED** [N=50 test excludes recovery-b](../../prototypes/crm_operational_copilot/variants/test_claims.py#L8) | **CLOSES** [S07 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L42) |
| `claim-b` | **OPEN** [claim-only override](../../prototypes/crm_operational_copilot/variants/claims.py#L13) | **OPEN** [component map inherits base review](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | **OPEN** [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [no schedule](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **OPEN** [review witness applies unchanged](../../tests/test_crm_decision_contracts.py#L207) | **CLOSES** [S12 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L64) | **CLOSES** [N=50 claim test](../../prototypes/crm_operational_copilot/variants/test_claims.py#L8) | **CLOSES** [S07 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L59) |
| `broken-control` | **OPEN** [control only breaks claim](../../prototypes/crm_operational_copilot/variants/claims.py#L35) | **OPEN** [component map inherits base review](../../prototypes/crm_operational_copilot/variants/implementations.py#L43) | **OPEN** [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [no schedule](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **OPEN** [review witness applies unchanged](../../tests/test_crm_decision_contracts.py#L207) | **CLOSES** [S12 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L81) | **OPEN** [50 claim failures](../../artifacts/crm-variants/variants-matrix.csv#L78) | **CLOSES** [S07 matrix row](../../artifacts/crm-variants/variants-matrix.csv#L76) |
| `store_layout_fixed` | **MOVES** [inherited execute boundary](../../prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10) | **CLOSES** [audit failure rollback/no execution](../../tests/test_variant_review_coverage_fixed.py#L79) | **OPEN** [identity unchanged](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | **OPEN** [manual recovery unchanged](../../prototypes/crm_operational_copilot/execution_service.py#L291) | **MOVES** [review event rollback tested, global audit gaps remain](../../tests/test_variant_review_coverage_fixed.py#L79) | **CLOSES** [inherited execute fail-closed behavior](../../prototypes/crm_operational_copilot/variants/store_layout.py#L232) | **CLOSES** [baseline replay test passed in final run](../../tests/test_crm_decision_contracts.py#L125) | **CLOSES** [baseline stale check passed in final run](../../tests/test_crm_decision_contracts.py#L162) |

`store_layout_fixed` closes the local I1b review failure case only when approval and audit stores share the same `DeferredConnection`. I1a remains MOVES because the CRM is still a local shared SQLite representation and crash/power-loss behavior was not tested. I6 remains MOVES, not globally closed: the fixed review path is covered, but execution denials and other decision events are not transformed into an immutable production audit service. **Recommendation confidence: high** for using it as a design/test input; **low** for extrapolating its transaction semantics beyond this SQLite topology.

## 5. Risk Register D1–D10

Likelihood for software fault rows describes local reachability in tested/injected code, not production event probability. Where the event rate or business blast radius is absent, it is explicitly UNKNOWN.

| ID / formal statement | Scope | Likelihood | Impact | Detection | Reversibility | Priority | Mitigation | Owner | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **D1:** A principal collision across tenants resolves to the last stored identity rather than the requested tenant identity. | Identity resolution → authorization. | **High locally** (reproduced); deployment rate **UNKNOWN**. | **High if multi-tenant:** isolation/data disclosure. | Direct witness detects; no runtime alert. | Low before deployment; high after exposure/replication. | Use tenant-qualified immutable subject key; require tenant context end-to-end; test collision and tenant mismatch. | Security + identity | [identity provider](../../prototypes/crm_operational_copilot/identity_provider.py#L39); xfailed collision witness in final output. |
| **D2:** CRM mutation may commit before its audit event; until manual recovery, mutation exists with no matching event. | CRM transaction → independent audit store. | **High under injected audit failure**, operational incidence **UNKNOWN**. | **High** audit/compliance/forensic risk. | Caller receives unresolved; no bounded backlog alert. | Moderate if ledger remains intact; high if evidence is lost or state diverges. | Atomic shared boundary where genuinely possible; otherwise durable outbox, bounded monitor, retries, reconciliation. | CRM/data + audit + ops | [execution failure test](../../prototypes/crm_operational_copilot/test_execution_service.py#L177). |
| **D3:** Unresolved approvals depend on manual `recover()` with no owner, schedule, RPO/RTO, or alert. | Recovery operations. | **Certain capability absence locally**; real backlog incidence **UNKNOWN**. | **High** availability and audit-lag risk. | Query unresolved rows manually; no automated detection. | Moderate while ledger/audit stores survive. | Assign owner, SLO/RPO/RTO, queue-age metric, alert, runbook, restart/restore tests. | Operations/SRE | [recover docstring](../../prototypes/crm_operational_copilot/execution_service.py#L291); [NFR TBD](../../architecture/05-nfr-and-sizing.md#L14). |
| **D4:** Audit is mutable local SQLite and lacks tamper-evidence/production retention; some state changes persist when audit fails. | Audit store and decision transitions. | Local lack is **verified**; tampering likelihood **UNKNOWN**. | **High** compliance, forensics, trust. | Injected errors are observable; tampering is not detected by an evidenced control. | High after required evidence is altered/expired. | Define immutable destination, access, retention/legal hold, integrity proof, independent tamper test. | Audit + security + compliance | [audit limitation](../../architecture/01-context-and-containers.md#L26), [review path](../../prototypes/crm_operational_copilot/execution_service.py#L256). |
| **D5:** Local L1/L2 evidence may be represented as deployment validation. | Architecture/procurement communication. | **Medium inference:** docs have clear caveats but also conflicting/stale pages. | **High trust/procurement risk** if overclaimed. | Manual evidence review; no central generated status. | Moderate before external claims; harder after reliance. | Single canonical evidence table with commit/environment provenance and CI consistency checks. | Product + architecture | [README evidence levels](../../README.md#L33); [stale contract](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L226). |
| **D6:** Documentation disagrees about SQLite implementation status and inventory. | README/REPO-MAP/validation contract/variant files. | **High locally:** dated map omits variants and contract says pending. | **Medium–High** decision/maintenance risk. | Manual cross-read; no consistency guard. | Low for prose; decisions based on it less reversible. | Refresh canonical repo map and stale contract claims; CI checks current paths and evidence state. | Architecture/docs | [map snapshot](../../REPO-MAP.md#L3); [SQLite pending claim](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L226). |
| **D7:** No demonstrated customer differentiator, operational benefit, or ROI. | Funding and product strategy. | **UNKNOWN** whether value exists; repo contains no customer outcome. | **Medium–High** opportunity cost. | Requires baseline task study; not observable in repo. | Low before investment, high after sunk integration. | One-task measured pilot with agreed attribution and total cost. | Product + finance | [cost inputs TBD](../../architecture/07-cost-model.md#L38); [benchmark disclaimer](../../benchmarks/response-delivery/README.md#L29). |
| **D8:** CRM mock schema stores only one row per customer, limiting multi-field representation. | Local CRM data model. | **Certain locally**; relevance **UNKNOWN** until scope set. | **Medium** correctness/generalization. | Multi-field fixture/schema test. | Moderate if schema assumptions propagate. | Confirm field scope; use tenant/customer/field composite identity when expanding. | CRM/data | [schema key](../../prototypes/crm_operational_copilot/crm_store.py#L43). |
| **D9:** A reviewer `APPROVED` state can persist and remain executable when the approval audit write fails. | `review()` → `set_review()` → audit → later execute. | **High local reachability:** 4/5 enumerated injected points fail open in current variant; production frequency **UNKNOWN**. | **High conditional** authorization-evidence integrity, audit completeness, compliance and trust. This is not evidence that an unauthorized reviewer is accepted. | `review()` reports unresolved for audit exceptions; no persistent monitor; later execution is possible. | Before execution can compensate/re-review; after write, contemporaneous decision proof is not recoverable as-is. | Commit state+event atomically or durable outbox; block execute until decision event is durable; retain failure witness and regression control. | Security + CRM/data + audit | [campaign CSV](../../artifacts/fault-injection-approval-audit.csv#L2); [review ordering](../../prototypes/crm_operational_copilot/execution_service.py#L256); [campaign output Section 8]. |
| **D10:** Variant artifacts are not byte-reproducible on Windows because committed CSV is CRLF while regenerated CSV is LF. | Artifact generation/checker pipeline. | **High in this environment:** repeated checker exit 1; other OS behavior **UNKNOWN**. | **Low–Medium:** CI/evidence reproducibility fails; normalized contents match. | Directly detected by checker; normalization reports counts. | Low; regenerate artifacts under pinned newline policy. | Set `newline=""` on CSV open and `lineterminator="\n"`; normalize committed copies then rerun checker in CI. Tooling/artifact change only; not production runtime code. | Build/release engineering | [CSV writer](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L198); [normalizer](../../scripts/normalize_variant_artifacts.py#L18); Section 9. |

## 6. Ranked Register and “If Only One”

| Rank | Risk | Why this rank | Confidence |
|---:|---|---|---|
| 1 | D1 / I2 tenant collision | Directly reproduced identity alias; a boundary violation if tenancy applies. | Medium: tenancy scope UNKNOWN. |
| 2 | D9 / I1b approval audit fail-open | **Upstream of D2**: approval becomes executable without its audit record; local campaign reports 4/5 fail-open. | High local; medium priority ordering. |
| 3 | D2 / I1a CRM write/audit gap | Mutation precedes audit and is unresolved/recoverable manually, rather than reported full success. | High locally; medium business priority. |
| 4 | D3 / I3 unowned recovery | Definite lack of scheduling/ownership; unresolved work may remain indefinitely. | High capability confidence; impact conditional. |
| 5 | D4 audit tamper/retention gap | Local store lacks these controls; legal requirement UNKNOWN. | Medium. |
| 6 | D5 evidence overclaim risk | L2/local caveats exist, but conflicting docs create a communication hazard. | Medium. |
| 7 | D6 documentation drift | Directly visible contradictions and stale inventory. | High occurrence; medium impact. |
| 8 | D7 value/ROI unknown | Cannot establish a bet without outcomes or cost inputs. | High confidence as evidence gap. |
| 9 | D8 one-field record model | Real schema limitation; relevance depends on workflow. | Medium. |
| 10 | D10 artifact newline drift | Strict checker fails, but normalized content agrees. | High local; low operational severity. |

**D9 versus D2:** D9 should lead D2 for write-enabled workflows requiring approval evidence because it is upstream and leaves an approved state executable after audit failure, whereas D2 occurs after mutation and reports unresolved with a ledger-based manual recovery route; this is conditional on mandatory approval audit and does not establish unauthorized reviewer access. **Confidence: medium.**

**If only one risk can be addressed:** for a confirmed multi-tenant workflow, remediate D1 first because identity resolution omits tenant entirely; if single-tenant and approval audit is mandatory, remediate D9 first because it permits execution without the approval event. The missing business/tenant context prevents one unconditional answer. **Confidence: medium.**

## 7. Vendor Comparison Matrix and Scoring Rule

No vendor capability is asserted. C/D are procurement placeholders only; product editions and contracts are UNKNOWN. Candidate C means a CRM-native agent/workflow category; Candidate D means an enterprise workflow/agent platform category. E means existing CRM/IdP features with no new platform, not that those controls are sufficient.

Weights sum to 100; 0–5 scoring scale: 0 absent, 1 weak, 2 partial, 3 plausible/unverified, 4 verified for scoped requirement, 5 independently validated. Safety and identity receive the greatest weights because the candidate can write customer records. Do not score UNKNOWN as zero or compute a final weighted total until evidence exists.

| Criterion | Weight | A: Adapt repo | B: Build | C: CRM-native product category | D: Workflow/agent product category | E: Existing CRM/IdP |
|---|---:|---|---|---|---|---|
| Real authenticated IdP integration | 10 | UNKNOWN: local caller-supplied IDs; which IdP subject/revocation contracts? [README](../../README.md#L23) | UNKNOWN: which protocols/team tests? | UNKNOWN: exact product/SKU IdP guarantees? | UNKNOWN: exact product/SKU IdP guarantees? | UNKNOWN: current claim validation and lifecycle behavior? |
| Tenant isolation (I2) | 10 | Known local failure; redesign required. [identity](../../prototypes/crm_operational_copilot/identity_provider.py#L39) | UNKNOWN: tenant model and proof? | UNKNOWN: product tenant semantics and test? | UNKNOWN: product tenant semantics and test? | UNKNOWN: do current row/field permissions bind tenant? |
| Field-level CRM enforcement | 8 | UNKNOWN: fake connector only. [prototype README](../../prototypes/crm_operational_copilot/README.md#L11) | UNKNOWN: API enforcement and tests? | UNKNOWN: selected SKU/object-level controls? | UNKNOWN: selected SKU/object-level controls? | UNKNOWN: current native permissions sufficient? |
| Approval bound to current record/policy | 9 | Partial local version/hash check; live connector unknown. [execution](../../prototypes/crm_operational_copilot/execution_service.py#L120) | UNKNOWN: optimistic concurrency/approval contract? | UNKNOWN: payload/version/policy recheck? | UNKNOWN: payload/version/policy recheck? | UNKNOWN: native approval binds exact state? |
| At-most-once execution | 8 | Local conditional claim/ledger; deployment unknown. [claim](../../prototypes/crm_operational_copilot/approvals_store.py#L153) | UNKNOWN: idempotency and retries? | UNKNOWN: vendor API idempotency? | UNKNOWN: vendor API idempotency? | UNKNOWN: existing retry semantics? |
| Audit atomicity, retention, tamper evidence | 12 | Baseline gap; fixed SQLite review test only. [fixed test](../../tests/test_variant_review_coverage_fixed.py#L79) | UNKNOWN: event store/outbox and compliance controls? | UNKNOWN: exact contractual evidence/retention? | UNKNOWN: exact contractual evidence/retention? | UNKNOWN: current audit export and immutability? |
| Recovery RPO/RTO/owner | 9 | On-demand only; no owner/SLO. [recover](../../prototypes/crm_operational_copilot/execution_service.py#L291) | UNKNOWN: on-call and objective? | UNKNOWN: SLA/support tier? | UNKNOWN: SLA/support tier? | UNKNOWN: current owner and recovery objectives? |
| Time to value | 5 | Local reference speeds prototyping; integration unknown. | UNKNOWN: staffing/scope estimate? | UNKNOWN: license/configuration lead time? | UNKNOWN: lead time? | UNKNOWN: can existing stack meet need? |
| Three-year TCO | 7 | UNKNOWN: no real usage/pricing. [cost model](../../architecture/07-cost-model.md#L3) | UNKNOWN: build/support/on-call estimate? | UNKNOWN: quote/support/usage? | UNKNOWN: quote/support/usage? | UNKNOWN: license/admin/manual cost? |
| Lock-in/exit | 4 | Python reference portable; adapters unknown. | UNKNOWN: internal coupling? | UNKNOWN: export/exit terms? | UNKNOWN: export/exit terms? | UNKNOWN: existing vendor coupling? |
| Differentiation | 4 | No customer differentiation evidence. | UNKNOWN: proprietary workflow advantage? | UNKNOWN: standard vs unique feature? | UNKNOWN: standard vs unique feature? | UNKNOWN: native sufficiency? |
| Compliance posture | 8 | Known no production compliance evidence. [EVIDENCE](../../prototypes/crm_operational_copilot/EVIDENCE.md#L52) | UNKNOWN: controls/evidence owner? | UNKNOWN: applicable certifications/DPA/region? | UNKNOWN: applicable certifications/DPA/region? | UNKNOWN: existing contract/config? |
| Operations/SLA/support | 6 | No deployment or named ownership. [EVIDENCE](../../prototypes/crm_operational_copilot/EVIDENCE.md#L63) | UNKNOWN: on-call/upgrade ownership? | UNKNOWN: contractual SLA/support? | UNKNOWN: contractual SLA/support? | UNKNOWN: shared responsibility? |

**Decision rule:** do not use weighted averages to compensate for failed gates. A write-enabled candidate must demonstrate I1a, I1b, I2, I3, I4, and I5 in the actual topology, and satisfy the applicable audit/compliance contract. **Recommendation (high confidence):** do not adopt Candidate A as a production platform. **Recommendation (medium confidence):** evaluate E first, then named commercial candidates and B if native controls fail; a final choice is **UNKNOWN** until procurement, architecture, and business evidence resolve the columns.

## 8. Fault-Injection Results

**Campaign scope:** five injected review fault points × current/fixed service. “Process killed” is simulated by raising `SystemExit` after the approval-store state update, not an OS process termination. “Audit unavailable at start” is simulated as the first audit write raising; no actual network/service outage is involved. The fixed variant transaction remains one local SQLite connection. Results are in [CSV](../../artifacts/fault-injection-approval-audit.csv#L1).

| Variant | Fault point | State after review | Audit present after review | Execute succeeds | Approval event ultimately emitted | Classification |
|---|---|---|---|---|---|---|
| current | audit write raises before atomic commit | APPROVED | No | Yes | No | FAIL-OPEN |
| current | exception after state update | APPROVED | No | Yes | No | FAIL-OPEN |
| current | final commit raises | PENDING | No | No | No | FAIL-CLOSED |
| current | simulated process death after state update | APPROVED | No | Yes | No | FAIL-OPEN |
| current | audit unavailable at review attempt | APPROVED | No | Yes | No | FAIL-OPEN |
| fixed | audit write raises before atomic commit | PENDING | No | No | No | FAIL-CLOSED |
| fixed | exception after state update | PENDING | No | No | No | FAIL-CLOSED |
| fixed | final commit raises | PENDING | No | No | No | FAIL-CLOSED |
| fixed | simulated process death after state update | PENDING | No | No | No | FAIL-CLOSED |
| fixed | audit unavailable at review attempt | PENDING | No | No | No | FAIL-CLOSED |

**Observed count:** current 4/5 FAIL-OPEN; fixed 0/5 FAIL-OPEN. These are enumerated local fault cases, not a statistical estimate of real failure likelihood. **Confidence: high for campaign code/results, low for production frequency.**

Raw campaign output:

```text
current | audit_write_raises_before_atomic_commit | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_error_after_state_update | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_succeeds_but_final_commit_raises | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
current | process_killed_between_state_update_and_audit | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_unavailable_at_review_start | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
fixed | audit_write_raises_before_atomic_commit | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_error_after_state_update | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_succeeds_but_final_commit_raises | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | process_killed_between_state_update_and_audit | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_unavailable_at_review_start | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
summary[current]: fail_open=4/5 fail_closed=1 fail_silent=0
summary[fixed]: fail_open=0/5 fail_closed=5 fail_silent=0
results_csv=.../artifacts/fault-injection-approval-audit.csv
result_rows=10
```

## 9. Artifact Reproducibility Status

**Classification: STILL-DRIFT.** The copy-only normalizer writes LF copies and is idempotent; all three normalized committed copies equal all three normalized fresh-generated copies. The required checker still exits 1 against untouched committed files because the committed pipeline currently writes the matrix with CRLF on Windows while the experiment emits LF. The `run_experiment.py` CSV writer uses `newline=""` and `lineterminator="\n"`; Windows text I/O translates the LF to CRLF because `newline` is not explicitly pinned to `"\n"`: [writer](../../prototypes/crm_operational_copilot/variants/run_experiment.py#L198). The user forbids editing this source and committed artifacts, so the remediation is specified but not applied.

Exact fix required for the committed pipeline: open the CSV output with `newline="\n"` (or binary/write bytes after CSV serialization) while retaining `lineterminator="\n"`, then regenerate the committed matrix under that pinned policy. That would modify **experiment/tooling source and generated artifacts**, not production runtime source or tests. In this task, only the copy-only normalizer was added; committed artifacts and existing writer remain untouched.

Raw normalizer output:

```text
source_directory=.../artifacts/crm-variants
output_directory=.../Temp/crm-variants-lf
variants-matrix.csv: original_bytes=8661 new_bytes=8575 original_crlf=86 original_lf=0 new_crlf=0 new_lf=86 changed=true
variants-results.json: original_bytes=31831 new_bytes=30940 original_crlf=891 original_lf=0 new_crlf=0 new_lf=891 changed=true
variants-environment.json: original_bytes=199 new_bytes=191 original_crlf=8 original_lf=0 new_crlf=0 new_lf=8 changed=true
idempotent_second_pass=true
```

Raw post-normalization comparison:

```text
harness_exit_code= 0
harness_summary= matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
normalizer_exit_code= 0
idempotent_second_pass=true
normalizer_exit_code= 0
idempotent_second_pass=true
variants-matrix.csv post_normalization_byte_equal= True committed_lf_bytes= 8575 generated_lf_bytes= 8575
variants-results.json post_normalization_byte_equal= True committed_lf_bytes= 30940 generated_lf_bytes= 30940
variants-environment.json post_normalization_byte_equal= True committed_lf_bytes= 191 generated_lf_bytes= 191
```

The checker script’s raw status in this run: **script exit 1, checker exit 1, harness exit 0, artifact diff exit 1**. Results and environment compare byte-identically before normalization; matrix differs only by line endings. The full reproduction appears under “Raw output of every test and script” at the end of this report.

## 10. Re-scored Adapt Scope

- **Adapt/reference input now covers locally:** I1b review state+event rollback for the tested single-file SQLite transaction; I4 sequential replay and claim patterns; I5 stale record/policy checks; I7 unresolved-not-success for execution audit failure. Evidence: [fixed test](../../tests/test_variant_review_coverage_fixed.py#L79), [contract suite raw output](#raw-output-of-every-test-and-script-run-in-this-session).
- **Still open:** I1a outside the shared local transaction and under crash/power loss; I2 tenant binding; I3 schedule/owner/RPO/RTO; I6 durable tamper-evident audit across all consequential decisions. These are not closed by the fixed review service.
- **Recommendation (high confidence):** the corrected deferral pattern is a credible *design input* for a real system if adapted to an actual transactional resource or implemented as a durable outbox. It is not a credible production guarantee by itself; no real CRM, external audit service, process-kill durability, power-loss, backup/restore, or outbox semantics were tested.
- **Trigger to flip “adapt” to “build” (medium confidence):** only if a bounded requirements exercise proves the existing CRM/IdP/native or named commercial candidates cannot meet mandatory I1a/I1b/I2/I3/I4/I5 gates, and a measured task-value/TCO analysis supports owning a custom service. Current business context is missing, so this trigger is not met or disproven.

## 11. Self-Critique

### Three weakest claims in this consolidated dossier

1. **Fixed I1b “CLOSES.”** Strong for injected exceptions on one shared SQLite connection, but not for abrupt OS termination/power loss or a real separate audit service. Correct scope: closes the tested local review failure boundary only. **Confidence high locally, low externally.**
2. **D9 campaign count 4/5 means “high likelihood.”** It is a count of deliberately enumerated failure points, not a probability sample. Corrected: four of five local injected conditions reproduce fail-open; production likelihood remains **UNKNOWN**. **Confidence high on count, low on operational rate.**
3. **D10 root cause is Windows newline translation.** Byte probes show CRLF in committed files and LF in regenerated file; the current writer uses text mode with `newline=""`. This strongly supports the explanation, but no alternate Windows Python/build configuration was tested. **Confidence high for this environment; medium for portability claim.**

### Three weakest claims in the prior addendum

1. Prior D9 wording could sound like unauthorized identity is accepted. Retracted as that reading: the demonstrated reviewer was configured/valid; the fault is executable approval state without durable approval-event evidence.
2. Prior D9 ranking above D2 was too broad without business controls. Recast as conditional: D9 leads only for a write workflow requiring approval evidence; tenant model and audit obligation are UNKNOWN.
3. Prior “shared transaction partially closes I1a” did not address inherited `review()`. New witness resolves the gap: old variant does not cover review; new sibling does for the tested local boundary.

### Silent UNKNOWNs and confidence corrections

- Production audit failure rate, tenant topology, compliance obligations, and cost/value are UNKNOWN, not low. Resolve with fault telemetry, identity architecture, compliance mapping, and measured workflow/TCO respectively.
- “Process killed” in the campaign is simulated `SystemExit`, not an OS kill. Do not treat it as crash-durability evidence.
- The normalizer’s post-normalization equality is not a passing canonical checker. The committed writer and artifacts remain untouched; checker classification stays STILL-DRIFT.
- Full repository tests were not run in this turn; status is UNKNOWN. The focused contract/variant/fixed suites were run and raw output is below.

## 12. Open Questions

| UNKNOWN | Resolving action | Owner role |
|---|---|---|
| Is the workflow multi-tenant, and what is the authoritative tenant claim? | Document IdP subject/tenant mapping, guest/service identities, and cross-tenant denial contract; test tenant swaps. | Security + identity platform |
| Must approval audit be atomic, or is a bounded lag acceptable? | Select applicable controls, retention, tamper evidence, and maximum lag; obtain compliance approval. | Audit + compliance + product |
| Can production CRM and audit share a transaction? | Validate actual CRM API and audit sink transaction/idempotency boundaries in non-production. | CRM/data owner |
| What are recovery objectives and operations ownership? | Set RPO/RTO, unresolved backlog thresholds, schedule, alert and runbook; perform restart/restore drill. | Operations/SRE |
| What are candidate costs, licenses, and contractual support? | Obtain dated quotes/SKUs/contracts and model three-year implementation, operation, review labor, failure and exit. | Procurement + finance |
| Does the workflow produce enough value to justify build/adapt/buy? | Measure a representative task against current duration, completion, rework, and reviewer effort. | Product/business owner |
| Does fixed SQLite behavior survive abrupt process/power loss? | Kill process around staged writes, test restart and backup/restore, verify transaction state; separately test actual outbox semantics. | Data platform + operations |
| Can CI pin CSV serialization to LF and prove byte identity? | Apply `newline="\n"` in the permitted tooling change, regenerate artifacts, run checker on Windows and POSIX. | Build/release engineering |

## 13. Recommended Next Step

Run one bounded, non-production verification with synthetic data and writes disabled in the live system: validate tenant-qualified identity, the fixed review rollback, CRM conditional/idempotent writes, audit failure and reconciliation, restart/restore, and a named recovery owner with agreed RPO/RTO. Include a baseline value/TCO measurement before selecting adapt/build/buy. **Recommendation confidence: high** that this is the next evidence step; **medium** on sequencing until the actual tenant/audit requirements are supplied.

**Stop criteria:** no write-enabled pilot if I1a/I1b/I2/I3/I4/I5 fail; stop if unresolved states cannot be detected/recovered within an owner-approved bound; defer investment if measured benefit does not exceed agreed three-year total cost. Threshold values are **UNKNOWN** and must be set before the exercise.

## Raw output of every test and script run in this session

### Fixed review test

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1
collected 3 items
tests/test_variant_review_coverage_fixed.py::test_fixed_review_with_healthy_audit_persists_state_and_event PASSED
tests/test_variant_review_coverage_fixed.py::test_fixed_review_audit_failure_rolls_back_and_cannot_execute PASSED
tests/test_variant_review_coverage_fixed.py::test_unsafe_review_control_is_caught_by_fixed_contract PASSED
============================== 3 passed in 0.35s ==============================
```

### Fault campaign script

```text
current | audit_write_raises_before_atomic_commit | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_error_after_state_update | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_succeeds_but_final_commit_raises | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
current | process_killed_between_state_update_and_audit | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
current | audit_unavailable_at_review_start | state=APPROVED audit_present=false execute_succeeds=true approval_audit_emitted=false classification=FAIL-OPEN
fixed | audit_write_raises_before_atomic_commit | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_error_after_state_update | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_succeeds_but_final_commit_raises | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | process_killed_between_state_update_and_audit | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
fixed | audit_unavailable_at_review_start | state=PENDING audit_present=false execute_succeeds=false approval_audit_emitted=false classification=FAIL-CLOSED
summary[current]: fail_open=4/5 fail_closed=1 fail_silent=0
summary[fixed]: fail_open=0/5 fail_closed=5 fail_silent=0
results_csv=.../artifacts/fault-injection-approval-audit.csv
result_rows=10
```

### Artifact normalizer

```text
source_directory=.../artifacts/crm-variants
output_directory=.../Temp/crm-variants-lf
variants-matrix.csv: original_bytes=8661 new_bytes=8575 original_crlf=86 original_lf=0 new_crlf=0 new_lf=86 changed=true
variants-results.json: original_bytes=31831 new_bytes=30940 original_crlf=891 original_lf=0 new_crlf=0 new_lf=891 changed=true
variants-environment.json: original_bytes=199 new_bytes=191 original_crlf=8 original_lf=0 new_crlf=0 new_lf=8 changed=true
idempotent_second_pass=true
```

### POSIX reproducer (`scripts/reproduce_variant_checker.sh` under Git for Windows Bash)

```text
POSIX_SHELL=Git for Windows Bash
script_exit_code= 1
interpreter=/c/Users/HP/Documents/GitHub/production-agentic-ai/.venv/Scripts/python.exe
working_directory=/c/Users/HP/Documents/GitHub/production-agentic-ai
--- checker stdout ---
harness_tail:
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S12]
2 failed, 15 passed in 0.69s
pytest_tail[recovery-b]:
			assert approvals.claim("approval-1", "race-winner", 150)
			assert not approvals.claim("approval-1", "race-loser", 150)
			assert crm.ledger_rows() == []
		elif scenario_id == "S10":
			assert approvals.claim("approval-1", "crash-before-write", 150)
			result = service.recover()[0]
			approval = approvals.get("approval-1")
			assert result.reason == "recovered_without_crm_write"
>           assert approval.state == "APPROVED" and approval.execution_id is None
E           AssertionError: assert ('INVALIDATED' == 'APPROVED'
E             
E             - APPROVED
E             + INVALIDATED)

tests\\test_crm_validation_scenarios.py:176: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S10]
1 failed, 16 passed in 0.58s
pytest_tail[claim-b]:
.................                                                        [100%]
17 passed in 0.51s
pytest_tail[broken-control]:
.................                                                        [100%]
17 passed in 0.52s
matrix=C:\\Users\\HP\\AppData\\Local\\Temp\\crm-variants-check-0x5jxdly\\variants-matrix.csv
results=C:\\Users\\HP\\AppData\\Local\\Temp\\crm-variants-check-0x5jxdly\\variants-results.json
environment=C:\\Users\\HP\\AppData\\Local\\Temp\\crm-variants-check-0x5jxdly\\variants-environment.json
CRM variant check failed: regenerated output differs from C:\\Users\\HP\\Documents\\GitHub\\production-agentic-ai\\artifacts\\crm-variants\\variants-matrix.csv
checker_exit_code=1
--- checker stderr ---
--- harness stdout ---
matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
broken_control_n50=accepted:50/50 single_winner_assertion:False
focused_pytest_return_code=0
focused_pytest_tail:
.....                                                                    [100%]
5 passed in 6.45s
pytest_tail[baseline]:
.................                                                        [100%]
17 passed in 0.78s
pytest_tail[store-layout-b]:
			monkeypatch.setattr(approvals, "set_state", original_set_state)
			assert service.recover()[0].status == "completed"
			assert approvals.get("approval-1").state == "COMPLETED"
		elif scenario_id == "S12":
			audit.fail_next_write = True
			result = _execute(service)
			assert result.status == "unresolved"
>           assert approvals.get("approval-1").state == "AUDIT_PENDING"
E           AssertionError: assert 'APPROVED' == 'AUDIT_PENDING'
E             
E             - AUDIT_PENDING
E             + APPROVED

tests\\test_crm_validation_scenarios.py:198: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S11]
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S12]
2 failed, 15 passed in 0.65s
pytest_tail[recovery-b]:
			assert approvals.claim("approval-1", "race-winner", 150)
			assert not approvals.claim("approval-1", "race-loser", 150)
			assert crm.ledger_rows() == []
		elif scenario_id == "S10":
			assert approvals.claim("approval-1", "crash-before-write", 150)
			result = service.recover()[0]
			approval = approvals.get("approval-1")
			assert result.reason == "recovered_without_crm_write"
>           assert approval.state == "APPROVED" and approval.execution_id is None
E           AssertionError: assert ('INVALIDATED' == 'APPROVED'
E             
E             - APPROVED
E             + INVALIDATED)

tests\\test_crm_validation_scenarios.py:176: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_crm_validation_scenarios.py::test_contract_scenario_ids_persist_expected_state[S10]
1 failed, 16 passed in 0.55s
pytest_tail[claim-b]:
.................                                                        [100%]
17 passed in 0.51s
pytest_tail[broken-control]:
.................                                                        [100%]
17 passed in 0.56s
matrix=C:\\Users\\HP\\AppData\\Local\\Temp\\tmp.RQ2wYAEVmK\\generated\\variants-matrix.csv
results=C:\\Users\\HP\\AppData\\Local\\Temp\\tmp.RQ2wYAEVmK\\generated\\variants-results.json
environment=C:\\Users\\HP\\AppData\\Local\\Temp\\tmp.RQ2wYAEVmK\\generated\\variants-environment.json
harness_exit_code=0
CRLF-normalized unified diff: no content differences for variants-matrix.csv
BYTE-FOR-BYTE EQUAL: variants-results.json
BYTE-FOR-BYTE EQUAL: variants-environment.json
artifact_diff_exit_code=1
--- stderr raw ---
--- checker stderr ---
--- harness stderr ---
BYTE DRIFT: variants-matrix.csv
```

### Post-normalization comparison

```text
harness_exit_code= 0
harness_summary= matrix_rows=85 variants=5 scenario_ids=17 pass=84 fail=1 n.a.=0
normalizer_exit_code= 0
idempotent_second_pass=true
normalizer_exit_code= 0
idempotent_second_pass=true
variants-matrix.csv post_normalization_byte_equal= True committed_lf_bytes= 8575 generated_lf_bytes= 8575
variants-results.json post_normalization_byte_equal= True committed_lf_bytes= 30940 generated_lf_bytes= 30940
variants-environment.json post_normalization_byte_equal= True committed_lf_bytes= 191 generated_lf_bytes= 191
```

### Final focused pytest run

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1
collected 27 items
tests/test_crm_decision_contracts.py: 8 passed, 8 xfailed (0 xpass, 0 error, 0 skip)
tests/test_variant_review_coverage.py: 3 passed
tests/test_variant_review_coverage_fixed.py: 3 passed
prototypes/crm_operational_copilot/variants/: 5 passed
======================= 19 passed, 8 xfailed in 11.31s ========================
```

### Syntax and diagnostics

```text
bash_syntax_exit=0
Pylance diagnostics: no errors in store_layout_fixed.py, test_variant_review_coverage_fixed.py, normalize_variant_artifacts.py, or fault_injection_approval_audit.py.
```

### Anomalies in this session

- An initial Pylance probe omitted `tests/` from `sys.path` and failed with `ModuleNotFoundError`; after correcting the path, the fixed behavior printed `review_status=unresolved approval_state=PENDING audit_count=0`, but the probe then hit a Windows SQLite file-lock during temp cleanup. The committed test’s `finally` closes shared connections; its rerun passed. **RESOLVED test-harness issue.**
- Initial campaign attempt left its injected commit failure hook active during the later execute observation and errored. The script was corrected to restore the hook after review; the complete rerun succeeded and is the reported campaign. **RESOLVED harness issue.**
- Artifact checker exits 1 against committed CRLF matrix; temp-normalized copies match generated copies. **STILL-DRIFT**, not a checker pass. No committed file was altered.
- The full repository pytest suite was not run. **UNKNOWN**, not a pass/failure claim.