# Re-evaluation Report: prior CRM approval audit lineage

Date: 2026-10-09
Scope: evidence-first audit of the prior dossier and its strongest operational claims, without treating prior outputs as ground truth.

**Latest verification update:** the extended six-point campaign was regenerated as `durability-20261009-repair-03` after adding the review outbox state and invoking `recover()` for staged decisions. Current and fixed local variants each classify three review-failure points as `RECOVERABLE_FAIL_CLOSED`, with zero `FAIL-OPEN`; writer-side timestamp backdating remains `FAIL-SILENT`, service-clock rollback is `INVARIANT_HELD`, and shared-database corruption remains `UNAVAILABLE_UNRECOVERED`. See [EVIDENCE.md](EVIDENCE.md) and the campaign CSV for exact records.

## 1. Method and evidentiary standard

This re-evaluation used a narrow audit loop: re-read the repo and the revision lineage, re-run the relevant tests, re-run the durability harness, inspect the affected SQLite variants, and check the working tree for file-level drift or prohibited edits.

The standard applied was strict:

- Confirm only when the claim is directly supported by fresh evidence.
- Downgrade or falsify when fresh evidence contradicts the prior claim or when the claim is broader than the tested boundary.
- Treat research or local prototype claims as structurally different from production-readiness claims.

The repo itself states the primary boundary clearly in [README.md](README.md): it is a research/reference implementation, not a production platform. That boundary was respected throughout this audit.

## 2. Executive conclusion

The prior dossier is best read as a credible local reference effort with several meaningful but bounded improvements; it is not a general production certification.

The strongest revised position is:

- The fixed local review path materially improves the narrow approval/audit sequencing bug and is supported by the fixed review variant tests.
- The fixed review path now has explicit rollback-and-retry semantics for transient review audit failures. A real child-process exit test confirms the staged decision is absent after restart, execution remains blocked, and a new review retry can complete.
- The broader durability narrative remains bounded. Shared-database corruption is unrecovered, and an audit writer that rewrites event timestamps after service normalization still creates a detected fail-silent chronology violation.
- D11 is fixed for the intended service-clock-skew condition: both variants floor review timestamps at the approval's creation time, with a passing regression test.
- The repo-level claim that the system is “ready for operational deployment” remains unverified and should be treated as unsupported.

## 3. Claim-level classification

| Claim / issue | Status | Fresh evidence | Assessment |
|---|---|---|---|
| Repo is a research/reference implementation, not a production platform | Confirmed | [README.md](README.md) and the surrounding architecture docs | This is consistent with the codebase scope and was not contradicted by fresh evidence. |
| The fixed review-path variant closes the narrow I1b approval-accounting bug in the local prototype | Partially confirmed | [tests/test_variant_review_coverage_fixed.py](tests/test_variant_review_coverage_fixed.py); fixed review code in [prototypes/crm_operational_copilot/variants/store_layout_fixed.py](prototypes/crm_operational_copilot/variants/store_layout_fixed.py) | The focused test passes and confirms a specific local fix for review-stage sequencing. However, it does not establish end-to-end crash safety or deployment readiness. |
| The fixed variant fully resolves all failure modes under crash/kill conditions | Falsified / overstated | Fresh campaign `durability-20261009-repair-03` from [scripts/fault_injection_approval_audit_extended.py](scripts/fault_injection_approval_audit_extended.py) | Three tested fixed-variant commit failures recover by review retry, but shared database corruption is unrecovered and post-normalization audit-writer backdating remains fail-silent. No power-loss test was performed. |
| D9 durability is effectively solved | Partially confirmed | Fresh six-point run of the extended durability harness | Current and fixed: 3 recoverable fail-closed, 1 fail-silent, 1 invariant-held, 1 unavailable-unrecovered; zero fail-open in these injected points. This is a local review transaction result, not a general durability guarantee. |
| D10 artifacts are deterministic and byte-stable across runs | Partially confirmed at best | Local artifact generation checks and the repo’s LF-normalization fix; no broad multi-platform evidence | The prior drift issue was likely mitigated in this workspace, but the claim remains too strong without broader platform verification. |
| D11 temporal ordering is fixed under service-clock skew | Confirmed locally for the stated invariant | [tests/test_audit_temporal_ordering.py](tests/test_audit_temporal_ordering.py) and campaign `durability-20261009-repair-03` | Both variants persist `approved_at` and the approval audit `event_ts` no earlier than `created_at` when the service clock reports 90 and `created_at` is 100. This does not protect against a writer that changes the event after service normalization. |
| The approval contract suite is broadly satisfied across invariants | Partially confirmed | [tests/test_crm_decision_contracts.py](tests/test_crm_decision_contracts.py) | The relevant combined suite now reports 20 passed and 8 xfailed. The retained xfails cover other current-variant, identity, and recovery contract gaps; this is not full conformance. |
| Pre-existing worktree changes were preserved | Confirmed | Initial and final `git status --short` | Pre-existing modified and untracked files remain. The repair added only the service, fixed-variant, test, harness, and requested evidence/documentation changes; it did not revert unrelated changes. |
| The dossier is ready for operational deployment or non-research use | Unverified / unsupported | No live-system or production evidence was produced | This claim is outside the supported evidence boundary and should be treated as unverified. |

## 4. Key findings by issue

### 4.1 Research boundary is valid and important

The repo’s framing in [README.md](README.md) is consistent with the working evidence. This matters because several prior claims about durability and operational control were interpreted as if they were production-grade certifications. They were not.

### 4.2 Local review fix is real, but limited

The most credible improvement in the local prototype is the fixed review-path logic in [prototypes/crm_operational_copilot/variants/store_layout_fixed.py](prototypes/crm_operational_copilot/variants/store_layout_fixed.py). The fixed review coverage suite in [tests/test_variant_review_coverage_fixed.py](tests/test_variant_review_coverage_fixed.py) is a meaningful signal that the narrow I1b sequencing bug is addressed in the prototype environment.

However, this does not imply:

- full crash-recovery safety,
- full durability under process kill or power loss,
- or production-grade transactional semantics outside the local SQLite model.

### 4.3 Durability is improved but not solved

The revised harness records approval state, approval-audit presence, CRM ledger rows, execution result, and recovery result separately. After the baseline service adopted `AUDIT_PENDING` plus on-demand review recovery, child-process exit, ENOSPC, and a post-write exception all remain blocked at execution and recover to `APPROVED` with one audit event and no CRM mutation. The fail-silent writer-backdating case, passing service-clock invariant case, and shared-database unavailability remain.

For the fixed variant, actual child-process termination, ENOSPC before insertion, and an exception after the audit insert was staged all reopen as `PENDING`, with no approval event and no CRM ledger row. Execution returns pending. A new review after restart completes, leaving one approval event and no CRM mutation. These are recoverable fail-closed outcomes under the tested local SQLite/process model, not proof that fail-closed is inherently safe. The shared-database corruption case is unavailable and unrecovered; the writer-backdating case remains fail-silent. The hook labeled fsync is only a Python exception after the audit call, not an OS fsync or power-loss test.

### 4.4 D11 service-clock ordering is fixed; writer integrity remains open

The root cause was `CRMExecutionService.review()` using `self.clock()` directly for both the approval transition and audit event without bounding it by `approval.created_at`. The shared service now computes `max(self.clock(), approval.created_at)` after loading the approval. The redundant timestamp monkeypatches were removed from the fixed-only wrapper so the owning service enforces the invariant for both variants.

The strict xfail has been removed and the regression now passes for both variants, asserting both stored `approved_at` and audit `event_ts` are at least `created_at`. The revised harness sets the service clock to 90 against a creation time of 100 and observes both persisted timestamps at 100. Separately, a malicious/broken audit-writer injection rewrites the event after service normalization; it persists `event_ts=90` and is detected by the harness comparison, but there is no runtime integrity monitor. Therefore the service-clock defect is fixed for its intended failure model, while downstream writer integrity remains unsupported.

### 4.5 D10 is better characterized as a local normalization fix than a broad deterministic guarantee

The local artifact-generation checks and the normalization work addressed a concrete reproducibility problem. But the broader claim of universal byte-determinism across all environments remains weaker than the prior wording suggests.

The evidence supports a narrower conclusion: a local normalization fix reduced artifact drift in this workspace, but internationalization, platform-specific file handling, and environment differences were not fully audited to a general-purpose guarantee.

## 5. Practical disposition of the previous dossier

The most defensible reading of the prior dossier is:

- strong local prototype work,
- limited but useful structural fixes,
- no production-ready certificate,
- and several open or partially closed issues that remain visible under a stricter audit standard.

In other words, the work is valuable as a research and reference package, but the dossier should not be treated as a complete operational closure package.

## 6. Required wording changes for future claims

The following wording is safer and better supported by fresh evidence:

- “The local prototype fixes the narrow approval-review sequencing issue in the SQLite variant.”
- “The fixed local variant recovers from three tested review commit failures by retrying from `PENDING`; shared-database corruption and downstream audit-writer integrity remain unresolved.”
- “Review timestamps are floored at the approval creation time under service-clock skew in both local variants; downstream audit-writer integrity is not guaranteed.”
- “The codebase is research/reference quality and not yet production-certified.”

The following wording should be considered unsupported or overstated:

- “The CRM approval workflow is fully fixed.”
- “The durability issue is solved.”
- “The system is production ready.”
- “All invariants are closed.”

## 7. Final judgment

The re-evaluation supports a conservative classification:

- confirmed: scope and some narrow local fixes,
- partially confirmed: durability and contract-quality improvements,
- falsified or downgraded: the broad “fully closed” story and production-readiness claims,
- unverified: operational claims beyond the local research environment.

The primary takeaway is straightforward: the repo contains a credible prototype with meaningful local improvements, but the prior dossier’s strongest claims were broader than the available evidence justified.

## 8. Evidence list

- [README.md](README.md)
- [EVIDENCE.md](EVIDENCE.md)
- [scripts/fault_injection_approval_audit_extended.py](scripts/fault_injection_approval_audit_extended.py)
- [tests/test_variant_review_coverage_fixed.py](tests/test_variant_review_coverage_fixed.py)
- [tests/test_audit_temporal_ordering.py](tests/test_audit_temporal_ordering.py)
- [tests/test_crm_decision_contracts.py](tests/test_crm_decision_contracts.py)
- [prototypes/crm_operational_copilot/variants/store_layout_fixed.py](prototypes/crm_operational_copilot/variants/store_layout_fixed.py)
- [prototypes/crm_operational_copilot/variants/store_layout.py](prototypes/crm_operational_copilot/variants/store_layout.py)
- [artifacts/fault-injection-approval-audit.csv](artifacts/fault-injection-approval-audit.csv) (ignored local evidence; final campaign `durability-20261009-repair-03`)

This re-evaluation report is intentionally narrow, evidence-led, and limited to what the fresh verification can support.
