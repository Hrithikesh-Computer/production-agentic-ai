# Solution Overview: CRM Operations Copilot

**Status:** Proposed architecture for discovery; not implemented or customer-validated.
**Scenario:** An enterprise wants account teams to use an AI assistant to retrieve CRM context and prepare operational actions, while keeping authority with the employee and requiring human approval before any write or workflow-triggering action.

## Problem

Account work often involves gathering account and opportunity context before taking an operational action. A copilot could make that investigation easier, but a model-generated recommendation must not itself be treated as permission to read or change customer records.

The design question is how to bind an employee's identity, approved scope, current CRM state, proposed action, and human approval at execution time, while leaving a reviewable audit trail.

## Intended outcome

- Employees can request account summaries based on CRM data their identity is allowed to read.
- The agent can propose a bounded action, but cannot execute a write until a named reviewer approves the exact action and the authority gateway rechecks policy immediately before execution.
- Reviewers can inspect the request, evidence references, proposed change, policy result, and execution outcome.
- Denials, approval decisions, tool calls, and failures have correlated audit events with explicit retention and access rules defined by the customer.

These are target outcomes, not demonstrated repository capabilities.

## Scope

**In scope for this design:** one CRM, one employee-facing workflow, read-only data gathering, action proposal, human approval for writes, policy decision, controlled CRM execution, and audit.

**Out of scope for the first design increment:** autonomous writes, broad multi-agent delegation, cross-CRM transactions, context/memory persistence, customer-facing actions, and an assumed cloud vendor. Select those only after discovery.

## Repository evidence versus target design

The original CRM CLI has static mock records, deterministic action selection, local read-scope checks, read-only behavior, and JSONL run logging. A separate local simulation now exercises a bounded in-memory write proposal, `refer` policy outcome, distinct reviewer method, fresh scope checks, and audit events. Neither has a real CRM/REST integration, LLM, authenticated identity-to-scope mapping, or durable approval workflow ([prototype README](../prototypes/crm_operational_copilot/README.md), [evidence](../prototypes/crm_operational_copilot/EVIDENCE.md)). The authority evaluator is a separate bounded library used by the simulation, not a production policy service ([authority evaluator](../04-reference-implementation/authority_policy.py)).

The C4 views and subsequent decisions describe a **proposed target**. The local simulation demonstrates only a narrow in-process sequence; the durable approval queue, deployed authority gateway, live CRM connector, identity provider, model service, and durable audit store are target containers or external systems, not implemented components in the repository.

## Primary flow

1. Employee authenticates with the enterprise identity provider and submits a CRM question.
2. The agent service obtains an identity-bound, least-privilege decision for each requested read and retrieves data through the CRM connector.
3. The model receives only authorized, task-scoped evidence and returns a response plus, where relevant, a structured action proposal.
4. Read results are returned to the employee. A write proposal is submitted to the approval workflow and is not executable merely because the model proposed it.
5. An authorized reviewer approves or rejects the exact proposed action. The authority gateway rechecks the approver, actor, target, action, current policy, and current CRM state at execution time.
6. The CRM connector executes an approved action; the system records correlated decision, approval, tool, and outcome events.

A timeout, denial, stale approval, changed CRM state, or audit-write failure must not silently become an allow. Exact fail-open/fail-closed behavior and availability objectives remain discovery decisions.

## Initial acceptance questions

- Which CRM objects and fields can this workflow read or propose to change?
- Which actions always require approval, and who can approve them?
- Does the CRM enforce the same user identity and row/field-level permissions?
- What constitutes a stale approval if the record changes after review?
- Which evidence may be sent to a model provider, and under what retention terms?
- What audit events, retention duration, access controls, and deletion/legal-hold rules apply?
- What are the required latency, availability, throughput, and recovery targets?

No numeric SLO, deployment topology, cost, compliance mapping, or customer commitment is asserted in this overview.

## Related artifacts

- [Architecture bundle index](README.md)
- [C4 context and container views](01-context-and-containers.md)
- [Options analysis](03-options-analysis.md)
- [STRIDE threat model](04-threat-model.md)
- [NFR and illustrative sizing](05-nfr-and-sizing.md)
- [AWS deployment candidate](06-deployment-views.md)
- [Cost model worksheet](07-cost-model.md)
- [Customer discovery questionnaire](09-discovery-questionnaire.md)
- [ADR-001: Response delivery](02-decisions/ADR-001-response-delivery.md)
- [ADR-002: Approval evidence and signing](02-decisions/ADR-002-approval-signing.md)
- [ADR-003: Context lifecycle deferral](02-decisions/ADR-003-context-lifecycle-deferral.md)
