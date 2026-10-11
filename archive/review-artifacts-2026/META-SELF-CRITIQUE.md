# Meta Self-Critique: Decision Assessment Lineage

This note critiques both the reviewer framing that led to the current request and the claims in [FINAL-DOSSIER-2026-10-09.md](FINAL-DOSSIER-2026-10-09.md). It is not deployment evidence.

## 1. Three Weakest Claims in the Meta-Assessment Lineage

The “meta-assessment” means the successive review prompts and prioritizations that framed the repository defects and asked for increasingly decision-grade evidence.

| Claim in assessment lineage | Strongest counter-argument | Treatment |
|---|---|---|
| “D1 tenant collision should be the single first risk.” | Tenant scope was never supplied; if the actual workflow is single-tenant, D1 may not be applicable, while an audited write workflow can still have D9/D2 exposure. | **Downgrade to conditional, medium confidence.** D1 is first only after product confirms multi-tenancy. The source proves principal-only storage, not that a production identity namespace collides. |
| “D9 is a fail-open authorization risk.” | The fault campaign uses a valid configured reviewer; it does not show an unauthorized identity can approve. It shows an approved state can remain executable without its approval audit evidence. | **Correct terminology.** Call it “approval-evidence fail-open” or “approval-state/audit inconsistency,” not an authentication bypass. A security test with an unauthorized reviewer and a real IdP is needed to establish any authorization bypass. |
| “The fixed deferred transaction is a credible real-system pattern.” | It is a one-SQLite-connection pattern; it cannot directly enlist an external CRM REST API or audit service and did not test power loss. | **Retain only as a design input, low external confidence.** It proves local staging/rollback behavior, not global transaction semantics. Resolve by topology-specific non-production tests. |

## 2. Three FINAL-DOSSIER Claims Most Likely to Be Wrong

| Claim | Evidence that would falsify it | Cheap way to obtain that evidence |
|---|---|---|
| The fixed review variant closes I1b for its local SQLite boundary. | A reproducible test where an injected failure leaves persisted `APPROVED`, emits no approval audit event, and later execution succeeds. A likely boundary to probe is exception/crash after SQLite commit returns but before caller receives the result. | Add a targeted process test around final commit/acknowledgment and reopen the exact database; compare approval row and audit event. Existing test is [test_variant_review_coverage_fixed.py](../../tests/test_variant_review_coverage_fixed.py#L79). |
| D10 is resolved for the current Windows environment. | A clean second regeneration produces any byte difference, or the checker exits nonzero. Cross-platform variation would falsify the broader portability interpretation, not the measured Windows result. | Run the recorded [regeneration script](../../scripts/regenerate_variant_artifacts.sh) twice in a fresh Windows CI job and once in POSIX CI; preserve exit and hashes. |
| Actual child-process exit leaves the current approval `APPROVED` while the fixed variant returns `PENDING`. | Repeating the child-process boundary test under a different SQLite journal/synchronous mode, or on a filesystem where process exit rolls back/commits differently, gives another state. | Run the extended campaign with each supported SQLite durability configuration and reopen the file; inspect `journal_mode` and `synchronous`. |

These are falsifiers for bounded local statements, not claims that alternative results are expected.

## 3. UNKNOWNs Previously Treated as Low Risk

- **Production likelihood:** The 2/5 and 4/5 figures count deliberately selected fault points; they are not probability estimates. The final dossier now labels production frequency UNKNOWN. Resolve with observed dependency failures and representative fault injection.
- **Audit severity:** D4/D9 business impact depends on regulatory and customer control requirements. Do not infer low impact from local recoverability. Resolve with audit/compliance control mapping and data classification.
- **D10 cross-platform behavior:** Windows regeneration passed twice after explicit LF handling; Linux/macOS CI was not run. The dossier states local resolution only. Resolve with matrix CI.
- **Power-loss durability:** A real child-process exit is stronger than injected `SystemExit`, but neither simulates power loss or storage-controller cache loss. This remains UNKNOWN and is explicitly not downgraded.
- **Vendor/native alternatives and ROI:** No capabilities, quotes, workload values, or customer outcomes were verified. They remain UNKNOWN, not zero-cost or low-risk.

## 4. Fixed-Variant Generalization Audit

The fixed variant claim is limited to same-process, shared SQLite connection behavior for `review()` and the tested injected faults. It is not a guarantee for:

- separate approval/CRM/audit databases;
- networked or non-transactional CRM APIs;
- successful commit followed by process death before acknowledgment;
- filesystem/power-loss durability;
- event timestamp correctness (the campaign found an event timestamp 60 seconds earlier than the approval state timestamp); or
- tamper-resistant audit retention.

The fixed variant does catch the tested state/audit rollback failures and prevents subsequent execution when approval remains pending, as evidenced by [its test](../../tests/test_variant_review_coverage_fixed.py#L79). Any broader language in earlier work is narrowed here.

## 5. Current-Variant Severity Audit

The 4/5 base and 2/5 extended fail-open counts are **not likelihood probabilities**. They enumerate different deliberate conditions. Extended probes found current FAIL-OPEN for OS child-process exit and ENOSPC; a simulated post-write fsync-hook exception was FAIL-CLOSED because the audit event persisted before the injected error; corruption was fail-closed for execution but made state UNKNOWN; clock skew was FAIL-SILENT with respect to chronology validation. These results strengthen reachability evidence but do not establish production frequency, harm, or all crash windows. The final dossier uses those bounded descriptions.

## 6. Self-Audit of This Run

- **Overclaim risk:** The extended script labels corruption as FAIL-CLOSED when execute fails, even though approval state is UNKNOWN because the database cannot reopen. This is fail-closed for the observed attempt, not proof of safe state. The dossier explicitly states state UNKNOWN and the classification definition is scoped to execution; retain a separate unresolved-state alert requirement.
- **Overclaim risk:** `audit_write_then_fsync_hook_raises` is not an OS fsync hook. The script raises after `AuditStore.write()` returns, which on this SQLite wrapper commits; it only simulates an error at that named boundary. The dossier says this and leaves power-loss UNKNOWN.
- **Campaign semantics:** The clock-skew row is classified FAIL-SILENT because invalid chronology was not rejected/flagged; the event itself exists. This is not “audit absent.” It is an audit-quality validation gap, distinct from D9 fail-open.
- **Coverage limit:** The full repository pytest suite and cross-platform artifact CI were not run. The final dossier claims only the focused suites and two local regeneration runs.

## 7. Evidence Classes

- **Verified in this environment:** final focused run 38 passed, 8 xfailed, 5 deselected; 17 S01–S17 scenarios passed; two artifact regeneration/checker runs exited 0 with byte equality; extended campaign wrote ten rows, including child `os._exit(87)` results; writer source explicitly pins LF.
- **Verified in prior run, not re-run here:** the separate 12-combination principal/tenant sweep and the prior base five-point count. The current source and preserved CSV are inspectable, but the sweep/count was not separately re-executed in this turn.
- **INFERENCE:** priority ordering, topology fitness, and conditional adapt/build choices. Each remains conditional on business requirements and is labeled in the dossier.
- **UNKNOWN with resolving question:** production IdP/CRM/audit behavior, audit failure probability, power-loss durability, RPO/RTO, regulatory scope, business value, TCO, vendor capabilities, and non-Windows artifact reproduction. Each has an owner/action in the final dossier’s Open Questions section.

**Correction to final recommendation:** “Adapt as reference only” is a recommendation about how to use this repository, not a selection of implementation topology. Confidence is high that the local tests are not production evidence; confidence is medium that a real workflow should begin by evaluating existing native controls, because actual context and alternatives are unknown.