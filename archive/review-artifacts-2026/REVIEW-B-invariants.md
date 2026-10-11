# Review B: CRM invariant audit

## Scope and method

I traced the approve → execute → audit path through the actual code and exercised it in a scratch script outside the repository source tree at /tmp/crm_invariant_repros.py. The live execution path reviewed was:

- [prototypes/crm_operational_copilot/execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L44-L241)
- [prototypes/crm_operational_copilot/approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176)
- [prototypes/crm_operational_copilot/crm_store.py](../../prototypes/crm_operational_copilot/crm_store.py#L75-L156)
- [prototypes/crm_operational_copilot/audit_store.py](../../prototypes/crm_operational_copilot/audit_store.py#L27-L64)
- [prototypes/crm_operational_copilot/identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L16-L57)

All scratch SQLite handles were closed in finally blocks.

## Critical invariants

### 1) No write without durable audit

Relevant path:

- [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L168-L241)
- [crm_store.py](../../prototypes/crm_operational_copilot/crm_store.py#L81-L156)
- [audit_store.py](../../prototypes/crm_operational_copilot/audit_store.py#L27-L64)
- [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176)

Failure cases to check:

- process dies after CRM write succeeds but before audit write is committed
- CRM write succeeds and then audit write fails
- approval is re-run while still in EXECUTING or AUDIT_PENDING state
- concurrent workers race to claim the approval or write the ledger

Observed behavior:

- In the scratch repro, forcing the audit write to fail produced a persisted ledger row with zero audit rows:
  - status: unresolved
  - reason: audit_pending
  - approval_state: AUDIT_PENDING
  - ledger_rows: 1
  - audit_count: 0
- This is a reproduced violation of the stronger invariant “no committed CRM mutation without a durable audit record.” The code does not atomically commit both stores; it produces a durable CRM write before the audit event is persisted and then keeps the approval in an unresolved state until recovery.

Finding 1: REPRODUCED VIOLATION

- Impact: a committed CRM mutation can exist with no matching durable audit row until recover() runs.
- Proof: scratch repro output from /tmp/crm_invariant_repros.py:
  - {"status": "unresolved", "reason": "audit_pending", "approval_state": "AUDIT_PENDING", "ledger_rows": 1, "audit_count": 0}
- This is not a “success” path, but it is a real persisted inconsistency relative to the invariant.

### 2) No double execution

Relevant path:

- [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L149-L176)
- [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L72-L126)
- [crm_store.py](../../prototypes/crm_operational_copilot/crm_store.py#L81-L156)

Failure cases to check:

- same approval executed twice sequentially
- same approval executed after successful commit
- same approval while state is EXECUTING or AUDIT_PENDING
- two workers race to claim the same approval

Observed behavior:

- Sequential replay is blocked. The scratch run produced:
  - first: {"status": "completed", "reason": "executed"}
  - second: {"status": "denied", "reason": "approval_completed"}
- When the approval is already in EXECUTING with a ledger row, the rerun is also blocked:
  - status: unresolved
  - reason: execution_outcome_unresolved
  - approval_state: EXECUTING
  - ledger_rows: 1
  - audit_count: 0

This was not a violation; it was the intended fail-closed behavior.

Suspected, unproven: real multi-process race under separate OS processes

- The code path is designed to prevent it, but I did not reproduce a true simultaneous two-process race in the scratch script.
- Test that would settle it:
  - start two Python processes with a barrier, both call execute() on the same approval_id with the same requester/reviewer, and assert exactly one commit result while the other returns denied or unresolved.
  - Success condition: one ledger row total, one approval state transition, no duplicate CRM mutation.

### 3) No cross-tenant access

Relevant path:

- [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L16-L57)
- [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L44-L92)

Failure cases to check:

- same principal name appears in multiple tenants
- tenant is not part of the identity key or authorization decision
- a principal can be active in one tenant and still be authorized in another

Observed behavior:

- Reproduced in a scratch test: adding the same principal name twice with different tenant values caused the last tenant to win.
- Output:
  - {"resolved": "tenant-b", "allowed": true}

This is a reproduced violation of the invariant because tenant is ignored by the identity store. The code keys identities only by principal, and `authorize()` receives only principal + scope, not tenant.

Finding 2: REPRODUCED VIOLATION

- Impact: cross-tenant principal shadowing is possible in the local identity model, and tenant boundaries are not enforced.
- Proof: scratch repro output from /tmp/crm_invariant_repros.py:
  - {"resolved": "tenant-b", "allowed": true}
- Root cause: [identity_provider.py](../../prototypes/crm_operational_copilot/identity_provider.py#L25-L57) stores identities by principal only and ignores tenant in the authorization decision.

### 4) Approval bound to payload

Relevant path:

- [execution_service.py](../../prototypes/crm_operational_copilot/execution_service.py#L99-L168)
- [approvals_store.py](../../prototypes/crm_operational_copilot/approvals_store.py#L59-L74)

Failure cases to check:

- action mismatches the approved action
- customer_id differs from the approved target
- field/value differs from the approved payload
- record_version changed after approval
- policy hash changed since issuance

Observed behavior:

- The scratch repro with a mismatched action produced:
  - status: invalidated
  - reason: policy_changed
  - ledger_rows: 0
  - audit_count: 1
- This is the intended fail-closed path; the effect is that the approval is bound to the policy and payload represented in the stored approval row.

Suspected, unproven: stronger payload-binding checks on mutated approval rows or a swapped record from a stale approval blob

- I did not reproduce a bypass via a direct database tampering case.
- Test that would settle it:
  - mutate the approval row to a different customer_id, field_name, or proposed_value after creation, then call execute() and assert the result is invalidated with no ledger row.

## Summary of reproduced findings

1. REPRODUCED: a durable CRM write can exist before a durable audit row exists.
2. REPRODUCED: tenant boundaries are not enforced because the identity store keys on principal only and drops tenant in authorization.

## Summary of non-findings

- No double execution: the code prevented sequential replay and unresolved rerun as expected.
- Approval bound to payload: the service rejected mismatched actions and stale payloads without writing.

These were not reported as findings because the current scratch runs did not reproduce a violation. The remaining cases are classified as “suspected, unproven” and should be settled with the specific tests listed above.
