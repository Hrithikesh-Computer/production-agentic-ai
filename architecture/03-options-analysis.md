# Options Analysis: Authority and Approval Boundary

**Status:** Preliminary recommendation for the proposed CRM Operations Copilot.
**Decision to support:** Where should action-level authorization policy execute, and how should it relate to human approval and CRM-side permissions?

## Assumptions

- The first workflow is one enterprise CRM with an employee-facing copilot.
- Reads are limited to explicitly permitted objects/fields; writes require human approval.
- The CRM remains the source of truth and must enforce its own authorization.
- Multiple agent services or tenants may be future requirements, but are not evidenced today.
- No cloud, policy product, identity provider, volume, SLO, or procurement constraint is selected. Ratings below are qualitative architecture judgments, not measured cost or vendor comparisons.

## Options

| Option | Description | Cost to start | Risk | Time to first slice | Operability | Lock-in |
|---|---|---|---|---|---|---|
| A. In-application policy library | Embed policy checks in the agent service; keep CRM permissions as a second enforcement point. | Low initial infrastructure; policy maintenance cost grows with services. | Medium: policy logic can drift or be bypassed by another caller; requires strong tests and code ownership. | Fast for one service. | Simple to deploy initially; distributed policy updates and audit become harder as callers multiply. | Low platform lock-in; higher coupling to application language/runtime. |
| B. Dedicated policy decision point (OPA or Cedar) behind an authority gateway | Centralize action decisions; agent and CRM adapter call a narrow policy/approval API. Keep identity authentication and CRM authorization separate. | Medium: service/runtime, policy authoring, distribution, and operations are additional work. | Medium: consistent central decision point, but outage, stale policy, policy-authoring errors, and integration bypass remain risks. | Medium; requires API and policy model design. | Clear ownership and audit point; adds a critical service requiring availability, versioning, monitoring, and fallback rules. | Low-to-medium; depends on selected engine, policy language, and data model. |
| C. Cloud IAM-based authority gateway | Use cloud identity/IAM and API gateway controls as the primary enforcement surface, with CRM-side permissions. | Potentially low where the customer already operates the platform; unknown without a customer environment. | Medium-high for domain-specific action/aggregation and reviewer semantics if encoded only as infrastructure permissions. | Fast only if the customer's identity and cloud boundary already fit. | Convenient within one cloud; policy semantics and troubleshooting can become platform-specific. | High cloud coupling. |

“Cost” means relative engineering/operational effort under the assumptions above. No prices or staffing estimates are available in the repository. OPA/Cedar are options named for evaluation, not existing dependencies or a claim of comparative market standing.

## Recommendation

**Provisional recommendation: Option B, a dedicated policy decision point behind a narrow authority gateway, with CRM-side authorization retained.** This best separates the agent's orchestration from action authorization when the design includes multiple tools and a distinct approval boundary. Human approval remains a workflow decision, not a substitute for the policy engine. The gateway must bind approvals to one action and re-evaluate current policy immediately before writes.

For a single-process prototype, Option A is cheaper and may be sufficient to test the action model. Do not add a policy engine until the customer confirms multiple enforcement points, policy ownership, or independent policy rollout justify its operational cost. Select between OPA, Cedar, and cloud-native policy only after evaluating customer identity integration, policy authorship, decision latency/availability requirements, auditability, skill set, and procurement constraints.

## Consequences and validation

- Define a canonical action schema: actor, tenant, CRM object/record, operation, fields, proposed values, purpose, request ID, and record version.
- Define policy data ownership, rollout/reversal, decision reason codes, audit fields, and behavior when the PDP is unavailable. Defaulting an outage to allow is not acceptable for writes; exact read behavior needs risk review.
- Verify authorization again at the CRM boundary where the vendor/API permits it. A gateway allow must not grant broader rights than the authenticated CRM principal.
- Test action aggregation, revocation, stale approvals, record-version changes, retries, duplicate submissions, and policy-version changes.
- Measure decision latency, availability, policy rollout time, false allows/denies in an agreed test set, reviewer burden, and operational staffing before accepting this recommendation.

## Evidence boundary

The repository has a bounded in-process evaluator for principal/action/time grants, priority rules, and aggregation constraints ([authority policy](../04-reference-implementation/authority_policy.py)). It has no OPA/Cedar integration, cloud IAM gateway, CRM identity mapping, human-approval queue, or production policy service. The CRM prototype is static and read-only ([CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md)). Recommendation remains a design hypothesis pending customer discovery and a policy-focused proof of concept.
