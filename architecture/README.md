# Proposed Architecture Bundle: CRM Operations Copilot

These artifacts form a customer-world design exercise, not an implemented or deployed system. Existing repo behavior is described separately from proposed containers and controls in the [solution overview](00-solution-overview.md).

## Design sequence

1. [Solution overview](00-solution-overview.md)
2. [C4 context and containers](01-context-and-containers.md), with [context diagram source](diagrams/c4-context.mmd) and [container diagram source](diagrams/c4-containers.mmd)
3. [Authority and approval options analysis](03-options-analysis.md)
4. Decision records: [response delivery](02-decisions/ADR-001-response-delivery.md), [approval evidence and signing](02-decisions/ADR-002-approval-signing.md), [context lifecycle deferral](02-decisions/ADR-003-context-lifecycle-deferral.md), [envelope versioning](02-decisions/ADR-004-envelope-versioning.md), [process-local state](02-decisions/ADR-005-process-local-state-and-resource-bounds.md), and [open owner decisions](OPEN-DECISIONS.md)
5. [STRIDE threat model](04-threat-model.md)
6. [NFR and illustrative sizing](05-nfr-and-sizing.md)
7. [AWS deployment candidate](06-deployment-views.md) and [diagram source](diagrams/aws-deployment.mmd)
8. [Cost model](07-cost-model.md)
9. [Customer discovery questionnaire](09-discovery-questionnaire.md)
10. [30-minute review guide](#how-to-review-in-30-minutes)

All service/vendor mappings, security controls, numeric NFR examples, and recommendations are provisional until confirmed with a customer. The CRM prototype contains a narrow in-memory approval simulation; it does not implement the proposed distributed architecture or connect to a real CRM.

## How to Review in 30 Minutes

This is a proposed design plus local simulation, not a deployed CRM product.

1. Read [00-solution-overview.md](00-solution-overview.md) for the scenario, scope, outcome, and evidence boundary.
2. Open [diagrams/c4-containers.mmd](diagrams/c4-containers.mmd) and read [01-context-and-containers.md](01-context-and-containers.md); treat the identity provider, CRM, model provider, approval queue, authority gateway, and audit store as proposed components.
3. Read the [decision records](02-decisions/README.md), [open owner decisions](OPEN-DECISIONS.md), and [03-options-analysis.md](03-options-analysis.md) for decisions, alternatives, and trade-offs.
4. Scan [04-threat-model.md](04-threat-model.md), especially prompt injection, approval replay, and recheck-before-write.
5. From the repository root, run `python prototypes/crm_operational_copilot/approval_workflow.py` and `python -m pytest -q prototypes/crm_operational_copilot/test_approval_workflow.py tests/test_authority_referral.py`. This is a deterministic in-memory simulation, not a live CRM or authenticated workflow.
