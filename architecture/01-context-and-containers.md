# Context and Containers

**Status:** Proposed target design, not an implemented or deployed architecture.
**Scenario:** CRM Operations Copilot; see the [solution overview](00-solution-overview.md).

## System Context

The employee asks for CRM analysis. The proposed copilot uses enterprise identity, a model provider, the customer's CRM, human review for writes, and a customer-controlled audit service. Trust boundaries, provider contracts, and ownership must be confirmed during discovery.

[Proposed C4 system context diagram](diagrams/c4-context.mmd)

## Containers

The proposed application separates user interaction, orchestration, policy/approval, CRM access, and audit persistence. An approval is bound to a specific action and record version; it does not become general authority. Policy is evaluated again immediately before execution.

[Proposed C4 container diagram](diagrams/c4-containers.mmd)

## Boundaries and unresolved design questions

- PROPOSED: enterprise identity assertions, CRM authorization mapping, and the production authority gateway and approval queue.
- IMPLEMENTED LOCALLY: a deterministic identity provider, SQLite approvals store, CRM records and execution ledger, and audit store used by the validation baseline. The local evaluator and execution service are not production services.
- VALIDATED LOCALLY: the contract's S01-S17 scenarios and five rounds of 50 local processes using separate SQLite connections.
- NOT VALIDATED: real identity-provider or CRM behavior, distributed coordination, network behavior, operational telemetry, customer deployment, or disaster recovery.
- The model provider is an external trust boundary. Data minimization, provider retention, regional processing, and model-evaluation requirements are unresolved.
- CRM remains the system of record and must enforce its own permissions. The proposed gateway is not a replacement for CRM authorization.
- The local audit store is not tamper-resistant and does not provide production retention controls or a customer-operated audit service.
- No cloud provider is selected in these views. Deployment mapping belongs after customer environment and procurement discovery.

See [ADR-002](02-decisions/ADR-002-approval-signing.md) for approval-evidence handling and [ADR-003](02-decisions/ADR-003-context-lifecycle-deferral.md) for context persistence.

Related design artifacts: [STRIDE threat model](04-threat-model.md), [NFR and sizing](05-nfr-and-sizing.md), and [AWS deployment candidate](06-deployment-views.md).
