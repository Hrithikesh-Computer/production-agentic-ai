# Identity Discovery Worksheet: Tenant Isolation (I2)

## 1. Purpose

**No production writes.** This worksheet resolves the identity and tenancy facts required before a non-production CRM integration. The local provider currently stores identities keyed only by principal and its resolve/authorize methods do not take tenant context: [identity_provider.py](prototypes/crm_operational_copilot/identity_provider.py#L39). This is local code evidence, not proof of a production identity collision.

## 2. Questions for the Identity Owner

| ID | Question | Why it matters | Acceptable answer |
|---|---|---|---|
| Q1 | Is the target service single-tenant or multi-tenant? | Determines whether tenant isolation is a hard security boundary. | Named tenancy model, data boundary, and owner-approved scope; no assumption based only on current deployment. |
| Q2 | Is identity keyed on `(principal, tenant)` or principal alone? | Principal-only resolution permits shadowing if names repeat. | Stable authenticated subject plus authoritative tenant identifier used in lookup and authorization. |
| Q3 | Can the same principal exist in two tenants? | Collision possibility determines whether one principal string is globally unique. | Explicit IdP guarantee with documented namespace, or affirmative collision allowance and test fixtures. |
| Q4 | How is tenant context propagated to authorization? | Prevents caller-controlled or dropped tenant context from changing scope. | Signed/validated claim or server-side mapping propagated to every CRM and policy decision. |
| Q5 | What happens if tenant context is missing? | Missing context must not fall back to a principal-only allow. | Fail-closed deny with reason, correlation ID, and no side effect. |
| Q6 | Can tenant membership change during a session? | Stale claims can preserve access after membership changes. | Defined token/session lifetime, revocation propagation bound, and revalidation point before each consequential action. |
| Q7 | How are cross-tenant requests audited? | Denials and attempted escalation need reviewable evidence. | Durable denial event with subject, requested tenant, resolved tenant, reason, timestamp/sequence, and retention policy. |

## 3. Non-Production Test Plan

Run with synthetic principals and no production writes. Use real IdP test identities where available; otherwise label fakes as local simulation.

| Test | Action | Assertion | Pass criterion |
|---|---|---|---|
| Collision witness | Create same principal string in two tenants with different scopes and resolve each. | Each `(principal, tenant)` resolves only its own identity. | No overwrite or cross-tenant scope transfer; both lookups are deterministic. |
| Missing tenant context | Omit tenant claim/context on read and write authorization. | Decision is deny; no fallback lookup occurs. | Zero CRM side effects; denial is correlated and auditable. |
| Cross-tenant escalation | Authenticate as tenant A, request tenant B resource/action. | Requested tenant differs from authenticated tenant. | Fail-closed denial at both policy and CRM boundary; event captures both tenant values. |
| Mid-session mutation | Revoke or move tenant membership after token/session issue, then execute an approved action. | Current authorization is re-evaluated. | Revocation/membership change prevents mutation within the approved propagation bound. |
| Concurrent resolution | Concurrently resolve/update identical principal names in two tenants. | No race swaps identity or scope. | Every decision remains tenant-bound; no cross-tenant result across repeated runs. |
## 4. Acceptance Criteria for Closing I2

- Identity lookup key includes stable principal subject and authoritative tenant; tenant is required, not optional.
- Authorization verifies resolved tenant equals request/CRM tenant, and missing/mismatched context denies.
- CRM connector enforces tenant boundary independently of the agent’s requested scope.
- Collision, missing-context, escalation, membership mutation, and concurrency tests pass with zero cross-tenant effects.
- Denials are observable and retained under the approved audit policy.
- Identity owner, security reviewer, and CRM/data owner sign off the boundary and revocation propagation bound.

## 5. Owner Roles

- **Primary:** Security/identity owner, accountable for subject namespace, tenant claim, lifecycle, revocation, and authorization semantics.
- **Verification:** Audit/compliance owner, accountable for denial-event completeness and retention.
- **Integration:** Engineering and CRM/data owner, accountable for propagating tenant context and enforcing row/object boundaries.

## 6. Single-Tenant Qualification

A confirmed single-tenant deployment makes cross-tenant collision I2 a non-issue for that deployment scope, but does not establish principal uniqueness or future multi-tenant safety. The identity owner must confirm Q1 in writing; do not assume single tenancy from local fixtures or the repository. Any later tenant expansion reopens I2 acceptance.

**Evidence tier:** the principal-only local implementation is VERIFIED-IN-THIS-ENVIRONMENT by source inspection; the 12-combination collision sweep is VERIFIED-IN-PRIOR-RUN and was not re-run in this turn; the production tenancy model is UNKNOWN-WITH-RESOLVING-QUESTION Q1.