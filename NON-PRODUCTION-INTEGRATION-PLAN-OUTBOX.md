# Non-Production Integration Plan: Transactional Outbox + CDC

## 1. Scope

**No production writes.** This is a bounded non-production design and test plan for one CRM workflow, synthetic/test records, a real or representative identity provider, a durable outbox, a CDC/consumer path, and a test audit sink. The SQLite fixed review result proves only the local shared-store code path; it does not prove outbox/CDC behavior or remote CRM atomicity. See [topology note](TOPOLOGY-GENERALIZATION-NOTE.md#topology-1-transactional-outbox--cdc).

The target contract is: approval state and approval-event intent commit in one transaction; CRM commands are conditional/idempotent; audit delivery is monitored and reconciled within an owner-approved bound. I1a is not strict cross-service atomicity when CRM is remote; it is a bounded reconciliation contract. I1b can be atomic at the approval/outbox transaction boundary.

## 2. Assumptions to Declare Before Starting

| Assumption | Why it matters | Cheap falsifier |
|---|---|---|
| Audit service accepts a stable idempotency key | CDC retries must not duplicate decision events. | Submit the same key twice in sandbox; require one logical audit event and a detectable duplicate response. |
| CRM accepts conditional writes keyed on record version/ETag | Prevents stale approval application and ambiguous retry duplicates. | Send stale ETag/version and require no mutation; replay same idempotency key after timeout. |
| CDC consumer can pause/resume without loss | Outbox lag must be recoverable rather than silently dropping audit intent. | Pause consumer, create events, restart consumer; reconcile outbox count to delivered audit IDs. |
| Outbox and approval store share one transaction boundary | Establishes I1b decision state + durable event intent. | Inject failure between approval update and outbox insert; require both commit or both absent. |
| **UNKNOWN:** the target CRM can provide an authoritative version or ETag | Needed for conditional application. | Ask CRM/data owner for API contract; test with sandbox object. |
| **UNKNOWN:** audit lag bound is acceptable to control owners | Defines I1a’s reconciliation window. | Audit/compliance owner approves a numeric maximum lag and required alert. |

## 3. Interfaces to Stub

| Interface | Shape | Controls | Observability |
|---|---|---|---|
| CRM write API | `apply(tenant, record_id, field, value, expected_version, idempotency_key) -> {record_version, operation_id}` | Tenant-bound credentials, allowlisted fields, conditional update, idempotency, timeout-after-commit behavior. | Request/operation IDs, conditional conflicts, retries, final CRM version, latency. |
| Audit write API | `append(event_id, idempotency_key, event_type, approval_id, execution_id, sequence, occurred_at) -> {event_id, accepted_at}` | Append-only authorization, idempotency, schema validation, trusted ordering token, retention. | Accepted/rejected counts, duplicate-key count, oldest unacknowledged event, sink errors. |
| Identity provider | `resolve(subject, tenant_context) -> principal, tenant, scopes, status, expiry` | Authenticated claims, tenant binding, revocation, least privilege, no fallback on missing tenant. | Subject/tenant decision IDs, deny reason, token age, revocation and clock-health signals. |
| CDC consumer | `consume(outbox_offset) -> publish + acknowledge` | At-least-once replay, stable event ID, per-tenant isolation, dead-letter/retry policy. | Consumer lag, offset, retries, poison records, replay activity, per-tenant backlog. |

## 4. Fault Points

| ID | Description | Expected invariant | Pass criterion |
|---|---|---|---|
| F1 | Audit service returns 5xx after outbox insert commits. | I1b; I1a bounded reconciliation. | Approval is not lost; outbox remains; command cannot be reported fully audited until idempotent retry succeeds; alert within bound. |
| F2 | CRM returns 5xx after outbox insert commits. | I1a, I5. | No false completed result; same idempotency key/version is retried or marked conflict; audit records final outcome or visible pending status. |
| F3 | Pause then resume CDC consumer. | I1a, I1b, I3. | All outbox events delivered once logically; backlog age/count observable; recovery completes within agreed RTO. |
| F4 | Kill process between approval/outbox transaction request and commit. | I1b. | Reopen shows either both approval+outbox committed or neither; no executable approval without durable event intent. |
| F5 | Clock skew between hosts. | I8/D11. | Trusted sequence is monotonic; write-time validation rejects or flags event time earlier than approval creation/transition. |
| F5b | Kill between audit service durable append/fsync acknowledgment and local outbox acknowledgment. | I1a, idempotency. | Replay uses identical event key, creates no duplicate logical event, and outbox is eventually acknowledged. **Decision relevance:** this is the classic uncertain-ack boundary for at-least-once CDC, so it is included. |
| F6 | Duplicate outbox delivery. | Idempotency, I1a. | One logical CRM effect and one logical audit event; duplicate attempt is recorded/observable. |
| F7 | Corrupt outbox storage/table on disk. | I3, I1a, I1b. | State is declared indeterminate, not “safe”; alert and restore/reconciliation runbook identifies missing/uncertain rows and stops writes. |

## 5. Success Criteria

- No fail-open outcome in F1–F7; approval event intent and approval state share a transaction.
- No success response before the CRM outcome and required audit state are confirmed according to the approved contract.
- RPO/RTO and maximum audit lag are set by owners before test execution and met in each injected failure.
- Event ordering is monotonic by authoritative sequence, and timestamp violations are rejected or visibly quarantined.
- Backlog, retry, dead-letter, replay, conditional conflicts, and unresolved state are observable and alerted.
- Idempotency and conditional-write tests prove duplicates/stale data do not produce extra mutations.

## 6. Stop Criteria

Stop with writes disabled if F1–F4 produce any fail-open outcome after two bounded fix attempts; if approved RPO/RTO cannot be met; if idempotency or CRM conditional writes cannot be enforced; or if the audit owner rejects the proposed bounded lag/retention semantics. Record exact state and evidence for every stop.

## 7. Owners

- CRM/data owner: conditional write contract, versions, idempotency and reconciliation.
- Security/identity owner: tenant claims, authentication, revocation and least privilege.
- Operations/SRE: CDC ownership, alerts, RPO/RTO, retries, restore and incident runbook.
- Audit/compliance owner: event schema, sequence, retention, access, legal hold, and acceptable lag.
- Product owner: workflow boundary, user impact, success measure and business stop threshold.

## 8. What This Plan Does Not Prove

It does not prove physical power-loss durability, 2PC or saga semantics, cross-region scale, a real CRM’s idempotency behavior, compliance certification, or production readiness. The local SQLite fix proves code-path behavior of deferred commits only, not cross-service atomicity. For topology alternatives and their residual failure modes, see [TOPOLOGY-GENERALIZATION-NOTE.md](TOPOLOGY-GENERALIZATION-NOTE.md).