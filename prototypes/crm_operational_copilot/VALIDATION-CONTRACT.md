# CRM write validation contract

This document is a local deterministic validation contract for the CRM approval workflow. It is intentionally scoped to the repository's existing evidence model and is not production evidence.

## Objective

Validate the claim under test:

> A consequential CRM write executes at most once, only under currently valid identity, authority, policy and record version, and always leaves a recoverable audit trail. Validated locally with deterministic fakes only. This is not production evidence.

The test objective is to make the core write path observable, replay-safe, and fail-closed under local deterministic conditions without claiming customer or production behavior.

## Boundary

### Implemented locally

- Python standard library only, specifically `sqlite3`
- Three separate SQLite files with separate connections: approvals, CRM, and audit
- `authority_policy.py` as the local evaluator for grant, time bounds, revocation, policy priority, aggregation, and referral semantics
- A local identity provider as the source of current authority; caller and proposal are never treated as authority
- Deterministic identities, scopes, policy snapshots, and mock CRM data
- An explicit `recover()` routine invoked by tests and the harness
- Local multiprocess concurrency against SQLite with separate connections

### Out of scope

- Real enterprise identity provider integration, CRM vendor APIs, customer data, or customer permission models
- Model-driven action generation
- Production audit retention, tamper resistance, legal hold, deployment, telemetry, or operational ownership
- Distributed coordination, multi-host consensus, queues, cross-node orchestration, or cloud deployment
- `use_ticket()`, `evaluate_in_session()`, `prior_actions`, and ticket `ttl`; this CRM workflow uses neither ticket nor session evaluation. These inputs are outside the workflow and its policy hash.

## Repository evidence definitions to preserve

The repository defines the evidence levels as follows in [README.md](../../README.md):

> "L0 — Conceptual | Analysis, hypothesis, or proposed architecture; no executable behavior for the claim"
>
> "L1 — Executable | A local reference implementation exists"
>
> "L2 — Reproducible | Local tests or benchmarks reproduce the bounded behavior under stated conditions"
>
> "L3 — Environment validated | Tested against representative external systems in a bounded non-production environment"
>
> "L4 — Operational | Deployed with telemetry, failure handling, and named operational ownership"
>
> "L5 — Production validated | Evidence from an actual production or customer setting, with scope and conditions recorded"

The current CRM workflow is explicitly described as:

> `"| CRM approval workflow | L2 | [Proposed architecture](./architecture/00-solution-overview.md) → [approval decision](./architecture/02-decisions/ADR-002-approval-signing.md) → [in-memory simulation and tests](./prototypes/crm_operational_copilot/approval_workflow.py) → [evidence and limitations](./prototypes/crm_operational_copilot/EVIDENCE.md). The simulation is serial and uses caller-supplied identities and in-memory state; concurrency, sink-failure recovery, and external integration remain unvalidated. |"`

Working repository links: [proposed architecture](../../architecture/00-solution-overview.md), [approval decision](../../architecture/02-decisions/ADR-002-approval-signing.md), [in-memory simulation and tests](approval_workflow.py), and [evidence and limitations](EVIDENCE.md).

This contract specifies a stronger local deterministic proof pattern; it is not production evidence and does not change the repository's stated evidence level.

## Invariants under test

1. No valid approval means no mutation.
2. Revoked requester or reviewer authority at execution means no mutation.
3. Missing or wrong requester or reviewer scope means no mutation.
4. Expired approval means no mutation.
5. A stale CRM record version means no mutation.
6. The approval-time policy snapshot is compared with current policy rules, the requester and reviewer grants, and aggregation constraints; changed or denying policy means no mutation.
7. A successful execution consumes its approval and is bound to one `execution_id`.
8. A successful CRM mutation has a matching audit row, or remains unresolved until `recover()` reconciles it.
9. Audit failure never reports full success.
10. Replaying an `execution_id` or approval never causes a second CRM mutation.

## State machine

The approval states are exactly:

- `PENDING`
- `APPROVED`
- `EXECUTING`
- `COMPLETED`
- `AUDIT_PENDING`
- `REJECTED`
- `INVALIDATED`

The only invalidation reasons are `expired`, `stale`, `revoked`, `policy_changed`, and `scope`. There is no `crash_no_write` reason.

State semantics:

- `PENDING`: awaiting human review; cannot execute.
- `APPROVED`: reviewed and eligible for execution subject to current checks.
- `EXECUTING`: claimed; outcome unresolved until the CRM ledger is checked.
- `COMPLETED`: CRM mutation and audit are both committed.
- `AUDIT_PENDING`: CRM mutation committed; audit unresolved; not full success.
- `REJECTED`: reviewer rejected; terminal for this approval.
- `INVALIDATED`: execution checks failed; terminal for this approval, with one of the listed reasons. A fresh approval is required for another attempt.

## Atomic claim and recovery

The claim is one conditional `UPDATE` on the approvals row:

```sql
UPDATE approvals
SET state = 'EXECUTING', execution_id = ?
WHERE approval_id = ?
  AND state = 'APPROVED'
  AND expires_at > ?;
```

The claim succeeds only when `rowcount == 1`. SQLite provides the single-winner behavior; no Python locks, reservation table, or explicit row lock is used. Assertions concern persisted outcomes and row counts, never which worker wins.

`recover()` is explicitly invoked by tests and the harness; there is no scheduler or background process.

- `EXECUTING` with a matching CRM ledger row: rebuild a missing audit row from CRM facts and set `COMPLETED`; if rebuilding fails, set `AUDIT_PENDING`.
- `EXECUTING` with no CRM ledger row: no CRM mutation occurred; return the approval to `APPROVED`. Any retry reruns every execution-time check and uses a new `execution_id`.
- CRM write failure after claim: the approval stays `EXECUTING` until `recover()`; because there is no CRM ledger row, `recover()` returns it to `APPROVED`.
- `AUDIT_PENDING`: rebuild audit from the CRM ledger and set `COMPLETED`; if recovery cannot complete, retain unresolved state and claim no success.
- Approvals-store failure after a successful CRM write: the persisted approval may remain `EXECUTING`; report unresolved, then recover from the CRM ledger when the approvals store is available.

## Failure table

“Same approval retriable?” refers only to retrying the same approval row; “No; a new approval is required” means the requested action needs fresh review.

| Failure cause | Approval state / reason | Same approval retriable? | CRM store | Audit store |
|---|---|---|---|---|
| Approval is `PENDING`, not approved | `PENDING`, no state change | No; approval must first be approved | No mutation | No success event |
| Missing approval row | No state change; no row to invalidate | No | No mutation | No success event |
| Wrong scope at execution | `INVALIDATED` / `scope` | No; a new approval is required | No mutation | Denial event if audit write succeeds |
| Requester or reviewer revoked | `INVALIDATED` / `revoked` | No; a new approval is required | No mutation | Denial event if audit write succeeds |
| Expired approval | `INVALIDATED` / `expired` | No; a new approval is required | No mutation | Denial event if audit write succeeds |
| Stale record version | `INVALIDATED` / `stale` | No; a new approval is required | No mutation | Denial event if audit write succeeds |
| Policy changed since approval | `INVALIDATED` / `policy_changed` | No; a new approval is required | No mutation | Denial event if audit write succeeds |
| Crash between claim and CRM write | `EXECUTING`, then `APPROVED` after `recover()` if no CRM ledger row | Yes, after recovery and all checks rerun, using new `execution_id` | No mutation; no ledger row for that execution | No success event |
| CRM write failure after claim | Stays `EXECUTING` until `recover()`, then `APPROVED` when no CRM ledger row exists | Yes, after recovery and all checks rerun, using new `execution_id` | No committed mutation or ledger row | No success event |
| Approvals-store failure after CRM write | Remains `EXECUTING` until recoverable | Yes, via `recover()`; result unresolved until then | Mutation and ledger committed with `execution_id` and `approval_id` | Success audit may be absent |
| Audit-store failure after CRM write | `AUDIT_PENDING` until recovery | Yes, via `recover()`; not caller-reported success before resolution | Mutation and ledger committed | Missing or incomplete audit row |
| Duplicate `execution_id` replay | Existing state; no second mutation | No new execution | Exactly one mutation and ledger row | Existing audit state; no duplicate success event. If the existing state is `EXECUTING` or `AUDIT_PENDING`, caller receives `unresolved`, never success. |
| New `execution_id` against a `COMPLETED` approval | `COMPLETED` unchanged; new execution rejected | No; a new approval is required | No additional mutation or ledger row | Existing success audit only |
| Concurrent workers on one approval | One claim winner; other claims fail | No additional execution | At most one mutation | One success audit or unresolved audit state |
| Reviewer denial | `REJECTED` | No; a new approval is required | No mutation | Rejection audit event if audit write succeeds |
| Denial-audit write failure | `REJECTED`; rejection outcome unchanged | No; a new approval is required | No mutation | Denial audit absent; failure is reported separately |

## Store schemas

### Approvals store

- `approval_id` TEXT PRIMARY KEY
- `proposal_id` TEXT NOT NULL
- `requester_id` TEXT NOT NULL
- `reviewer_id` TEXT NOT NULL
- `customer_id` TEXT NOT NULL
- `field_name` TEXT NOT NULL
- `proposed_value` TEXT NOT NULL
- `previous_value` TEXT NOT NULL
- `record_version` INTEGER NOT NULL
- `policy_hash` TEXT NOT NULL
- `created_at` INTEGER NOT NULL
- `expires_at` INTEGER NOT NULL
- `approved_at` INTEGER NULL
- `state` TEXT NOT NULL CHECK(state IN ('PENDING','APPROVED','EXECUTING','COMPLETED','AUDIT_PENDING','REJECTED','INVALIDATED'))
- `reason` TEXT NULL CHECK(reason IN ('expired','stale','revoked','policy_changed','scope'))
- `execution_id` TEXT NULL UNIQUE
- `approval_version` INTEGER NOT NULL DEFAULT 1

### CRM store

- CRM record fields include `customer_id`, `record_version`, `field_name`, `field_value`, and `updated_at`.
- The CRM ledger has `execution_id` TEXT UNIQUE and `approval_id` TEXT.
- The record mutation and ledger row commit in the same CRM-store transaction; the ledger is the source of truth for whether a write happened.

### Audit store

- Audit events include `audit_id`, `approval_id`, `execution_id`, `event_type`, `event_ts`, `crm_customer_id`, `crm_record_version`, `state_before`, `state_after`, `reason`, and `reconciled`.
- Audit is a recoverable record, not the authority for whether the CRM mutation occurred.

## Policy hash and live authorization inputs

Provider identity, status, and scope are checked live at the identity and scope steps and are NOT part of the policy hash. The injected clock `at` is an evaluation input, not part of the policy snapshot.

The canonical policy-hash input contains exactly:

- `PolicyRule`: `action`, `effect`, `priority`
- The `Grant` records for the requester and reviewer on the requested action: `principal`, `action`, `not_before`, `expires_at`, `revoked_at`. Do not hash grants for unrelated principals or actions.
- `AggregationConstraint`: `actions`, `reason`

There is no referral field in `authority_policy.py`; referral is represented by a `PolicyRule.effect` value of `refer`. Referral behavior is therefore covered by hashing the rule effects. The hash covers only these policy rules, the two relevant grants, and aggregation constraints.

For this workflow, `use_ticket()`, `evaluate_in_session()`, `prior_actions`, and ticket `ttl` are out of scope. The workflow does not issue or consume authority tickets and does not evaluate accumulated session actions; none of those inputs are included in the hash.

## Execution-time check order

1. Resolve requester and reviewer identities from the local identity provider.
2. Check current provider status and scope for requester and reviewer.
3. Check approval presence and require state `APPROVED`.
4. Check approval expiry.
5. Check CRM record version against the approved version.
6. Compare the policy hash and re-evaluate current policy using the evaluation-time clock.
7. Atomically claim the approval with the conditional update.
8. Perform the version-checked CRM write and insert its ledger row in one CRM transaction.
9. Write the audit event; if unresolved after a committed CRM mutation, retain `AUDIT_PENDING` or `EXECUTING` until recovery.

## Scenario matrix

| Scenario ID | Setup | Expected persisted state |
|---|---|---|
| S01 | Missing approval row | Approvals unchanged; CRM unchanged; no success audit |
| S02 | PENDING approval execution attempt | Approval remains `PENDING`; CRM unchanged; no success audit |
| S03 | Wrong scope at execution | `INVALIDATED` / `scope`; CRM unchanged; denial audit if available |
| S04 | Requester revoked before execution | `INVALIDATED` / `revoked`; CRM unchanged |
| S05 | Reviewer revoked before execution | `INVALIDATED` / `revoked`; CRM unchanged |
| S06 | Expired approval | `INVALIDATED` / `expired`; CRM unchanged |
| S07 | Stale record version | `INVALIDATED` / `stale`; CRM unchanged |
| S08 | Policy drift | `INVALIDATED` / `policy_changed`; CRM unchanged |
| S09 | Concurrent workers on one approval | One conditional claim wins; at most one CRM mutation |
| S10 | Crash or CRM write failure after claim with no ledger row | Approval stays `EXECUTING` until `recover()`, then becomes `APPROVED`; no mutation; retry uses a new execution ID and reruns checks |
| S11 | Approvals-store failure after CRM write | CRM mutation and ledger committed; approval may remain `EXECUTING`; report unresolved and recover later |
| S12 | Audit-store failure after CRM write | CRM mutation and ledger committed; approval is or remains unresolved (`AUDIT_PENDING` when writable); recover audit from ledger |
| S13 | Duplicate `execution_id` replay | Existing state; one mutation and one ledger row only; if state is `EXECUTING` or `AUDIT_PENDING`, caller receives `unresolved`, never success |
| S14 | Reviewer denial | Approval `REJECTED`; CRM unchanged; rejection audit if available |
| S15 | Denial-audit failure | Approval remains `REJECTED`; CRM unchanged; rejection outcome unchanged |
| S16 | Successful execution | Approval `COMPLETED`; CRM row, ledger, and audit share the same approval and execution IDs |
| S17 | New `execution_id` against a `COMPLETED` approval | Execution rejected; approval remains `COMPLETED`; no additional CRM mutation or ledger row |

## Evidence-level assessment

This assessment applies to the proposed deterministic SQLite design, not to the current in-memory implementation, and does not change any repository-level field.

| Level | Status | Reason |
|---|---|---|
| L1 — Executable | pending implementation | The SQLite-backed design has not yet been implemented as executable evidence. |
| L2 — Reproducible | pending implementation | Deterministic local tests must reproduce the bounded behavior before this design earns L2 evidence. The existing CRM workflow remains at L2. |
| L3 — Environment validated | not met | No representative external CRM, real identity provider, or bounded non-production environment is included. Deterministic fakes alone are not L3 evidence. |
| L4 — Operational | not met | No deployment with telemetry, failure handling, and named operational ownership is evidenced. |
| L5 — Production validated | not met | No production or customer evidence is included. |

The repository's current CRM workflow stays at L2; these documents do not change its evidence-level field.

## What this does NOT guarantee

- Cross-store atomicity across approvals, CRM, and audit
- Tamper-proof or immutable audit
- Distributed concurrency or coordination across hosts
- Real identity-provider or CRM behavior
- Production readiness, production operation, or customer results

## Evidence criteria

A scenario requires its stable scenario ID, explicit identity/provider/scope and policy snapshots, approval and execution record versions, CRM pre-state and post-state, approval and ledger binding, audit/recovery outcome, persisted-state assertions, and raw command output. Pytest function names are not scenario identifiers.

The repository's CRM workflow remains at L2. This design does not change a repository evidence-level field and does not claim L3, L4, L5, production readiness, or customer results. Cross-store atomicity, tamper-proof audit, distributed coordination, real identity-provider semantics, and live CRM behavior are not guaranteed.
