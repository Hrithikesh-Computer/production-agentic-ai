# Proposed Architecture Bundle: CRM Operations Copilot

These artifacts form a customer-world design exercise, not an implemented or deployed system. Existing repo behavior is described separately from proposed containers and controls in the [solution overview](00-solution-overview.md).

## Design sequence

1. [Solution overview](00-solution-overview.md)
2. [C4 context and containers](01-context-and-containers.md), with [context diagram source](diagrams/c4-context.mmd) and [container diagram source](diagrams/c4-containers.mmd)
3. [Authority and approval options analysis](03-options-analysis.md)
4. Proposed decisions: [response delivery](02-decisions/ADR-001-response-delivery.md), [approval evidence and signing](02-decisions/ADR-002-approval-signing.md), and [context lifecycle deferral](02-decisions/ADR-003-context-lifecycle-deferral.md)
5. [STRIDE threat model](04-threat-model.md)
6. [NFR and illustrative sizing](05-nfr-and-sizing.md)
7. [AWS deployment candidate](06-deployment-views.md) and [diagram source](diagrams/aws-deployment.mmd)
8. [Cost model](07-cost-model.md)
9. [Customer discovery questionnaire](09-discovery-questionnaire.md)
10. [30-minute review path](../README.md#how-to-review-this-in-30-minutes)

All service/vendor mappings, security controls, numeric NFR examples, and recommendations are provisional until confirmed with a customer. The CRM prototype contains a narrow in-memory approval simulation; it does not implement the proposed distributed architecture or connect to a real CRM.
