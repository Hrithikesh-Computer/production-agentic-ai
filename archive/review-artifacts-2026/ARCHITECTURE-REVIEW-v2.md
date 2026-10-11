# Architecture Review v2

## TL;DR

The repo is not a fake “nothing exists” case; it is a real local reference slice with implemented tests and a deterministic execution path. The surviving problems are not “no implementation,” they are two concrete integrity gaps: a CRM write can outlive its audit record, and tenant identity can be shadowed by principal name. Everything else in the earlier review is a boundary issue or a benchmark limitation, not a reproduced code defect.

## Baseline status

The baseline below is anchored to the current checked-in code and the local validation runs, not to claims about a production deployment.

| Area | Previous status | Current status | Evidence | Assessment |
|---|---|---|---|---|
| Local implementation maturity | Weak | Solid local slice | [README.md](../../README.md#L21-L47), [prototypes/crm_operational_copilot/execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L44-L241), [prototypes/crm_operational_copilot/validation_harness.py](../../prototypes/crm_operational_copilot/validation_harness.py#L1-L120) | The repository now contains an executable reference flow and deterministic checks. |
| Approval integrity | Unclear / broken | Fragile but fail-closed for replay | [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176), [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L99-L168) | Replay and stale checks are enforced; audit-commit ordering is the main gap. |
| Tenant / identity boundary | Unproven | Broken in current local model | [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L25-L57) | Same principal name can shadow across tenants because identity keys are principal-only. |
| Evidence discipline | Mixed | Good boundary discipline | [EVIDENCE.md](../../EVIDENCE.md#L1-L43), [README.md](../../README.md#L21-L47) | The repo clearly distinguishes local evidence from production evidence. |
| Production readiness | Not met | Not met | [README.md](../../README.md#L15-L17), [VALIDATION-CONTRACT.md](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L36-L53) | Still not a deployment claim. |

## Findings that do not survive

### 1) “The architecture is not implemented capability.”

Dropped.

Why it does not hold:
- The repository now includes an executable local CRM workflow and a deterministic approval path in [prototypes/crm_operational_copilot/execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L44-L241).
- The repo explicitly says the current design is local and not production in [README.md](../../README.md#L21-L47) and [REPO-MAP.md](../../REPO-MAP.md#L1-L83).
- This is a scope boundary statement, not a current defect. The earlier claim was directionally correct in 2026-10-04, but it is obsolete for the current codebase.

### 2) “Approval controls are not atomic or authenticated.”

Partially true, but not a clean finding as written.

What survives:
- The local model is not production-authenticated and does not claim cross-store atomicity; see [VALIDATION-CONTRACT.md](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L18-L22) and [VALIDATION-CONTRACT.md](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L104-L134).

What does not survive:
- The claim that the workflow is “not atomic” is true only in the stronger cross-store sense, not as a local replay bug. The practical replay and stale checks are enforced by [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176) and [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L72-L126).
- The current code does not allow the same approval to execute twice sequentially; the scratch repro returned one completed result and a later denied result.

### 3) “The repo has no real double-execution protection.”

Dropped.

The code does protect against repeated execution in the common path:
- approvals claim is conditional on state = APPROVED and expires_at > at in [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176)
- if a ledger row exists for an unresolved execution, the service returns `execution_outcome_unresolved` in [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L72-L126)
- the scratch repro showed: first = completed; second = denied; no duplicate ledger row

This is not a surviving architecture finding.

## New findings ranked by severity

### 1) Critical — CRM mutation can persist before durable audit reconciliation

Proof:
- The execution path writes the CRM ledger before the audit event in [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L168-L241).
- The audit write can fail and the code sets approval state to `AUDIT_PENDING` while leaving the ledger row persisted in [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L199-L214).
- Reproduced scratch result:
  - `{ "status": "unresolved", "reason": "audit_pending", "approval_state": "AUDIT_PENDING", "ledger_rows": 1, "audit_count": 0 }`

Why this matters:
- The invariant “no write without durable audit” is not satisfied by the current three-store design.
- The system can persist a mutation and still report an unresolved result, which is acceptable for recovery-only semantics but not acceptable as a single durable write contract.

Fix:
- Use one atomic commit boundary for the three related writes, or a durable outbox pattern that records a pending write before the CRM mutation and emits the audit row in the same transaction boundary.
- If the code stays split across SQLite files, then the approval state machine must explicitly treat the ledger as the write authority and never present the operation as success until the audit row is durable.

### 2) High — tenant isolation is not enforced by the identity model

Proof:
- `LocalIdentityProvider` stores identities keyed only by principal in [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L25-L57).
- The same principal can be reinserted for a second tenant and the later tenant wins.
- Reproduced scratch result:
  - `{ "resolved": "tenant-b", "allowed": true }`

Why this matters:
- The identity security boundary is tenant-blind. This is a real auth bug in the local model.
- It is not a hypothetical issue; it is reproducible with a synthetic identity collision.

Fix:
- Key identities by `(tenant, principal)` and include tenant in the lookup and authorization path.
- Decision functions should reject identities whose tenant does not match the requested authorization context.

### 3) Medium — repo-level evidence gaps remain, but they are boundary gaps, not code-path breakages

Proof:
- The repo documents the boundary explicitly in [README.md](../../README.md#L21-L47), [REPO-MAP.md](../../REPO-MAP.md#L1-L83), and [VALIDATION-CONTRACT.md](../../prototypes/crm_operational_copilot/VALIDATION-CONTRACT.md#L36-L53).
- The benchmark layer remains local and synthetic in [EVIDENCE.md](../../EVIDENCE.md#L8-L29).

Why this matters:
- This is not a broken execution path; it is a lack of external validation evidence.
- It matters for customer-facing claims, but it should not be framed as a runtime integrity exploit.

Fix:
- Treat it as a roadmap item: add a bounded non-production validation with real identity, CRM, and durable audit semantics before any L3 or L4 claim.

## Anchored scorecard

The scale is anchored as follows: 3 = significant gaps, 5 = fragile, 7 = solid with gaps, 9 = proven.

| Dimension | Score | Delta | Rationale |
|---|---:|---:|---|
| Local implementation completeness | 7 | +2 | The repo now has a real local executable workflow and deterministic checks. |
| Safety and integrity under failure | 4 | -1 | Two real issues remain: audit-after-write and tenant shadowing. |
| Evidence maturity | 6 | +1 | The repository is explicit about local evidence boundaries and no longer overclaims. |
| Production readiness | 2 | 0 | Still not presented as deployable or customer-validated. |
| Architecture credibility | 6 | +2 | The repo now tells the truth about scope and evidence boundaries. |

## Roadmap

### Near term (1–2 weeks)
- Enforce tenant as part of the identity key in [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L25-L57).
- Add a deterministic test proving one approved approval cannot be executed twice across a repeated call path.
- Add a failing test for the audit-lag case so the invariants are encoded as executable requirements.

### Mid term (2–6 weeks)
- Rework the write path into a single atomic state machine or durable outbox across approval, CRM, and audit rows.
- Add a recovery test suite covering crash-after-claim, CRM-write failure, and audit-store failure.
- Document the exact fail-closed semantics for `EXECUTING`, `AUDIT_PENDING`, and recovery.

### Longer term
- Move from synthetic and local evidence to a bounded non-production validation with real identity and durable writes.
- Only then consider an L3 or L4 status claim.

## Single highest-leverage change

The highest-leverage change is to make the approval lifecycle a single durable state machine with one authoritative commit boundary across approval, CRM mutation, and audit persistence. Right now the design is split across three SQLite files and the ledger can outlive the audit, while tenant identity is keyed only by principal. Fixing those two path-level issues would move the repo from “interesting local reference” to “credible fail-closed model,” without pretending it is a production system.

## Final assessment

The current repository is materially stronger than the earlier review posture. The surviving findings are not “nothing is implemented” or “double execution is unguarded.” The real code-level issues are: (1) the gap between CRM mutation and durable audit, and (2) the tenant-shadow vulnerability in the identity model. Everything else remains a scope, evidence, or benchmark limitation rather than a reproduced runtime defect.
