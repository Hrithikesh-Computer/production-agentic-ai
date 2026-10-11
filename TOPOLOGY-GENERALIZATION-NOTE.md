# Topology Generalization Note: Approval, CRM Mutation, and Audit

**Scope:** Translate the local deferred SQLite transaction experiment into candidate service topologies. The local fix proves code-path behavior of a shared SQLite connection, **not cross-service atomicity in a real deployment**. Local evidence: fixed review state/audit rollback tests [test_variant_review_coverage_fixed.py](tests/test_variant_review_coverage_fixed.py#L79); fixed transaction wrapper [store_layout_fixed.py](prototypes/crm_operational_copilot/variants/store_layout_fixed.py#L10). The local baseline itself uses SQLite and deterministic fake stores [prototype README](prototypes/crm_operational_copilot/README.md#L5).

Invariant shorthand:

- **I1a:** committed CRM mutation has a correlated durable audit event atomically or within a bounded, monitored reconciliation window.
- **I1b:** an approval/rejection cannot become executable/terminal without durable correlated decision evidence or a durable pending event with recovery.
- **I2:** identity resolution and authorization are tenant-qualified.
- **I3:** unresolved operations are recovered by an owned process within agreed RPO/RTO with alerting.

## Topology 1: Transactional Outbox + CDC

**Mapping.** Commit the approval decision or CRM mutation and an outbox record in the same database transaction. CDC/worker delivery publishes the event to the audit service and, where appropriate, invokes the CRM with an idempotency key. If the CRM is a separate system of record, the outbox does not magically make the CRM mutation atomic with the local database; use a command/outbox protocol with explicit pending/confirmed states and reconcile the CRM result.

**Invariants.** Can preserve I1b at the approval-state/outbox boundary and can preserve an audit intent atomically with local state. I1a is preserved only if the CRM mutation and outbox are in one transaction, or a bounded reconciliation contract bridges the CRM response and audit delivery. I2 and I3 are not provided by the outbox itself.

**Residual failures.** CDC lag, duplicate delivery, poison messages, lost/expired idempotency keys, CRM timeout after remote commit, stale record version, outbox growth, schema incompatibility, audit sink outage, retention mismatch, and tenant data leakage through a mis-keyed event remain possible.

**Operational requirements.** Set a maximum outbox age (RPO for audit delivery), end-to-end recovery-time target (RTO), per-tenant backlog limits, delivery/retry/dead-letter ownership, alerting on oldest event and count, replay controls, reconciliation reports, and tested restore of outbox and CRM idempotency state. **UNKNOWN:** actual target values; product/data owner and SRE must set them.

**Falsifiable pre-adoption claim.** With the real non-production CRM connector, inject crash after remote CRM commit but before outbox acknowledgment, replay the message at least twice, and show exactly one CRM mutation plus exactly one durable correlated audit outcome or a visible unresolved event within the approved bound.

## Topology 2: Distributed Transaction (2PC or Saga)

**Mapping.** 2PC can provide a coordinated commit only if every participant supports a compatible prepare/commit protocol and the coordinator’s log is durable. A conventional CRM REST API and an external audit service may not participate. A saga instead records forward actions and compensations; it does not make effects atomic and compensation may fail or be semantically incomplete.

**Invariants.** True 2PC across CRM, approval state, and audit could preserve I1a/I1b if all participants are transactional and recovery is durable. A saga can preserve I1b with an approval-state transaction plus durable event intent, but I1a is a reconciliation/compensation guarantee rather than strict atomicity. Neither topology provides I2 without tenant-aware identity and authorization. I3 requires an operated coordinator/saga worker.

**Residual failures.** 2PC coordinator loss can block participants, prepared transactions can consume resources, participants can time out or violate assumptions, and CRM may not support prepare. Saga compensation can fail, duplicate, or fail to reverse external side effects; concurrent updates complicate rollback. Clock/order ambiguity and audit sink unavailability remain. Availability and latency can degrade due to coordination.

**Operational requirements.** Name coordinator/saga owner; define durable decision-log retention, participant timeout and retry, prepared-transaction alarms, compensation policy, escalation and manual repair. Set RPO/RTO and maximum blocked transaction age; exercise coordinator loss and participant restore. **UNKNOWN:** whether target CRM supports distributed transactions; resolve by vendor API/contract and non-production capability test.

**Falsifiable pre-adoption claim.** Kill the coordinator after each prepare/commit boundary and separately make each participant unavailable; after restart, prove no terminal approval state conflicts with CRM and audit facts, every stuck transaction is visible, and resolution meets the selected RTO.

## Topology 3: Event-Sourced Audit + At-Least-Once Replay

**Mapping.** Persist an append-only decision/command event as the audit authority, then apply commands to CRM at least once using a stable idempotency key and conditional record version. Track projection/apply status separately from the immutable intent/decision event. A successful audit append before CRM application proves an authorized command was durably recorded, not that the CRM mutation happened; a success event must not be emitted until CRM acknowledgment is reconciled.

**Invariants.** Can preserve I1b by making approval decision event durable before enabling command application. Can preserve I1a only if the log records intent and final outcome, the CRM apply is idempotent/conditional, and the pending-to-confirmed gap is bounded and monitored; strict simultaneous commit is not provided across separate services. I2 and I3 remain separate requirements.

**Residual failures.** Duplicate replay, incorrect idempotency scope, version conflict, log/CRM divergence, consumer lag, event schema migration, replay after retention expiry, ordering/clock skew, poison command, and false success from missing CRM acknowledgment remain. At-least-once is not exactly-once; it requires idempotent application and reconciliation.

**Operational requirements.** Durable replicated log and retention policy, consumer lag and dead-letter monitoring, stable per-tenant idempotency keys, replay authorization, schema evolution, projection rebuild runbook, owner/on-call, and explicit RPO/RTO. **UNKNOWN:** acceptable event retention, traffic, latency, and replay volume; product, audit, and SRE must set them.

**Falsifiable pre-adoption claim.** Deliver the same approved command repeatedly and crash the consumer before and after CRM acknowledgment; show no duplicate mutation, no success event before confirmed apply, and a bounded visible reconciliation for every pending command.

## Decision Table

All fit statements below are **INFERENCE** until workload and service capabilities are measured. “Scale” means sustained/burst event and write volume, currently **UNKNOWN**.

| Topology | Better fit when | Less suitable when | I1a / I1b status | Cost/latency/compliance trade-off | Required decision evidence |
|---|---|---|---|---|---|
| Transactional outbox + CDC | Moderate/high event scale, asynchronous audit accepted within a defined bound, CRM supports idempotency/conditional writes, operational team can own replay. | Business requires strict simultaneous CRM+audit commit and external CRM cannot join transaction; no team for queue/CDC operations. | I1b can be strong at local approval/outbox commit. I1a is conditional on CRM transaction or reconciled remote apply. | Adds broker/CDC and operations cost; eventual audit delay adds latency to finality; can fit compliance if retention/integrity/lag evidence meet policy. | CDC lag SLO, CRM idempotency/ETag proof, recovery drill, audit retention/security review. |
| 2PC | Low/moderate participant count where every participant supports durable prepare/commit and blocking is tolerable; strict atomic commit is essential. | CRM REST/non-transactional services, high availability requirements, or broad cross-domain participants. | I1a/I1b can be preserved only across participating transactional services. Saga does not provide strict atomicity; it supplies compensation/reconciliation. | Higher coordination latency and operations complexity; 2PC can block; compliance evidence can be strong if coordinator log and participant recovery are proven. | Validate participant support and coordinator failover; test every prepare/commit crash point. |
| Event-sourced audit + idempotent apply | High auditability/replay needs, high event scale, async processing accepted, strong log operations and idempotent CRM API available. | Strict immediate CRM+audit consistency with no pending state, low ops maturity, or CRM lacks idempotency. | I1b can be satisfied by durable approval event before execution. I1a remains eventual/reconciled, not cross-service atomic, absent shared transaction. | Log/consumer/replay costs; added apply latency; strong chronology/retention potential, but only with access, retention, integrity, and schema controls. | Duplicate replay, out-of-order, crash around CRM ack, reconciliation bound and retention tests. |

**Recommendation (medium confidence):** use the local deferred-commit code only as a testable transaction pattern. Select a real topology only after CRM transaction/idempotency capabilities, audit policy, scale, latency tolerance, and operations ownership are established. The repository does not establish any of those real-service properties.