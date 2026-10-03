# Threat Model: CRM Operations Copilot

**Status:** Proposed threat model for discovery; no controls below are asserted as implemented unless marked as repository evidence.
**Method:** STRIDE over the proposed containers and flows in [C4 container view](diagrams/c4-containers.mmd).
**Assets:** CRM records and credentials; employee/reviewer identity; model prompts and outputs; proposed actions and approval state; policy rules; audit events; service availability.

## Trust boundaries

1. Employee/reviewer browser to customer application (untrusted endpoint and network).
2. Application services to enterprise identity provider.
3. Agent service to external model provider (customer data leaves the application boundary unless deployment says otherwise).
4. CRM connector to customer CRM and its authorization model.
5. Application services to approval queue and audit store.
6. Agent/authority/connector service identities and private APIs inside the proposed application boundary.

The repository CRM prototype is static, deterministic, read-only, and mock-only. It has no model, real CRM, approval workflow, or production audit store. The controls below are design recommendations, not observed controls ([CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md)).

## Data-flow inventory

These IDs name the relationships in the proposed [container diagram](diagrams/c4-containers.mmd); they do not imply implemented endpoints.

| Flow | From -> to | Data / operation | Boundary |
|---|---|---|---|
| F1 | Employee or reviewer -> Web application | Request text or approval/rejection input | Browser to customer application |
| F2 | Web application -> Agent API | Authenticated request, response, or proposal status | Public edge to private application |
| F3 | Agent API -> Identity provider | Validate issuer, identity, and claims | Application to enterprise IdP |
| F4 | Agent API -> Authority gateway | Action/target context and request for policy decision | Private service boundary |
| F5 | Agent API -> CRM connector | Requested CRM operation and actor/tenant context | Private service boundary |
| F6 | CRM connector -> Authority gateway | Current action authorization check immediately before operation | Private service boundary |
| F7 | Authority gateway -> CRM connector | Action-bound allow/deny decision | Private service boundary |
| F8 | CRM connector -> Customer CRM | CRM read or approved conditional write | Application to CRM trust boundary |
| F9 | Agent API -> Model provider | Minimized prompt/context; model response/action proposal returns | Application to external provider |
| F10 | Agent API -> Approval queue | New proposal and workflow status request | Private service to durable workflow state |
| F11 | Web application -> Authority gateway -> Approval queue | Reviewer decision, approval state transition, and status | User identity to workflow trust boundary |
| F12 | Agent, authority, CRM connector -> Audit event store | Correlated request, decision, review, operation, and outcome events | Application to audit storage |

## STRIDE analysis

| ID / flow | STRIDE | Threat scenario | Impact | Proposed controls and detection | Residual question / owner |
|---|---|---|---|---|---|
| T1: F1/F2/F3 employee identity path | Spoofing | Stolen session or forged identity claims let an attacker act as an employee. | Unauthorized CRM reads or action proposals. | Validate issuer, audience, signature, expiry, nonce/state, and tenant on every session; short session lifetime; MFA/conditional access per customer policy; revoke sessions; alert on anomalous identity changes. | Which IdP, auth flow, MFA policy, device posture, and session revocation SLA? Identity owner. |
| T2: F1/F11 reviewer approval path | Spoofing | Attacker impersonates an approver or exploits a shared session to approve their own proposed write. | Unauthorized or fraudulent CRM mutation. | Strong reviewer authentication; separation of duties; prohibit self-approval for designated actions; bind approval to reviewer and proposal ID; step-up auth for high-risk actions. | Required role model and whether requester/approver must differ for every write. Business control owner. |
| T3: F1/F8 model context and response | Tampering | Prompt injection in CRM fields or user input changes the proposed action, target, or values. | Data exfiltration, incorrect recommendation, or unauthorized operation attempt. | Treat retrieved text as untrusted data; keep instructions separate; validate output against a strict action schema and allowlist; never execute model output directly; require approval for writes; adversarial tests. | Which CRM fields may contain user-authored content? Model/application security owner. |
| T4: F3/F5/F6 authority decision | Tampering | Caller alters actor, tenant, record version, requested scope, policy version, or approval state between decision and execution. | Confused-deputy access or stale/overbroad authorization. | Bind decision to canonical action digest, actor, tenant, record version, request ID, and expiry; authenticate service-to-service calls; connector performs live recheck immediately before call; use atomic approval state transition. | Can the CRM enforce conditional writes/ETags and actor identity? Authority owner. |
| T5: F9/F10/F11 approval state | Tampering / Replay | An approval is replayed, duplicated, changed, or applied to another CRM record/action. | Unauthorized repeated or misdirected write. | One-time approval state; unique proposal ID and idempotency key; immutable exact action/target/value binding; expiry; atomic consume-on-execution; reject version changes; test retries and concurrency. | CRM idempotency and approval-state consistency requirements. Workflow owner. |
| T6: F12 service to audit store | Repudiation | A user, service, or administrator disputes or deletes an action because events are missing, mutable, or not correlated. | Inability to investigate, prove approval, or meet customer audit obligations. | Correlate request/proposal/approval/policy/tool IDs; record actor, reviewer, policy version, timestamps, outcomes, and reason; restrict write/delete roles; export to separately controlled immutable retention where required; monitor gaps. | Retention, legal hold, tamper-evidence, access and export requirements. Audit/compliance owner. |
| T7: F8 agent to model provider | Information disclosure | CRM fields, user prompts, credentials, or hidden system instructions are sent to a provider or retained outside approved boundary. | Privacy, contractual, regulatory, or competitive-data exposure. | Minimize and redact context; prohibit secrets; select provider/region only after data-processing review; configure retention/training controls contractually; encrypt transport; log metadata rather than raw prompts by default. | Data classification, allowed fields, provider terms/region, and retention. Privacy/security owner. |
| T8: F12 application to audit store | Information disclosure | Logs contain full CRM content, tokens, prompts, or reviewer details and are broadly accessible. | Secondary data exposure and excessive retention. | Structured allowlisted event schema; secret/PII redaction; encryption and least-privilege access; retention/deletion policy; audit log access itself. | Which event payload fields are necessary for investigations? Data owner. |
| T9: F1/F3/F4/F8/F9/F12 | Denial of service | Request floods, oversized CRM responses, model timeouts, queue saturation, or audit-store failure exhaust resources or block work. | Copilot outage; pending approvals; unsafe retry pressure. | Per-user/tenant quotas; bounded request and response sizes; timeouts, concurrency caps, backpressure, circuit breakers, queue-age alerts, and explicit degraded states; fail closed for writes; define safe read behavior. | Expected bursts, rate limits, queue backlog tolerance, and dependency SLAs. SRE owner. |
| T10: F3/F4/F5/F7 | Elevation of privilege | Agent acts as a confused deputy, uses a broad service credential, crosses tenant boundaries, or bypasses a per-action check. | Unauthorized read/write beyond user scope. | User/tenant-scoped authorization on every operation; narrow CRM scopes; CRM-side authorization; deny by default; connector refuses calls lacking a fresh action-bound decision; tenant isolation tests. | Delegated-user versus service-account model; field/row-level scopes. IAM/CRM owner. |
| T11: F4/F7 connector to CRM | Tampering / Elevation | CRM response is stale or attacker-controlled, or a retry applies a write twice after timeout. | Bad recommendation, duplicate change, or inconsistent state. | Validate response schemas; bind proposed change to record version; use conditional writes and idempotency where supported; distinguish unknown outcome from failure; reconcile after timeout before retry. | CRM API semantics, audit trail, conditional update support. CRM integration owner. |
| T12: F3/F5/F6 policy decision | Repudiation / Elevation | Policy changes are unreviewed, incorrectly scoped, or unavailable and a permissive fallback allows execution. | Unauthorized action or inability to explain a decision. | Version and review policy bundles; test policy changes; log exact version and decision inputs safely; fail closed on write authorization dependency failure; emergency revoke/rollback procedure. | Policy owners, approval workflow, outage behavior, and emergency process. Policy owner. |

## Abuse cases that cross STRIDE categories

- **Prompt injection to confused deputy:** malicious CRM text instructs the model to request a broader read or write; output schema validation and per-action policy must prevent execution.
- **Approval race:** reviewer approves a proposal, record changes before execution, and the agent acts on stale context; bind to record version and reject/re-review on mismatch.
- **Audit failure during execution:** CRM accepts a write but audit persistence fails. Define whether the connector blocks before the write, uses a transactional outbox, or reconciles a pending audit record. Do not claim atomicity across the CRM and audit store without evidence.
- **Cross-tenant confusion:** identifiers from one tenant are replayed in another tenant's request; tenant identity must be bound at the gateway and checked at CRM access.

## Repository controls versus proposed controls

The local CRM prototype validates a customer-ID shape, checks a local read-scope allowlist, rejects unsupported actions, and logs JSONL. It has no write path. The separate authority evaluator checks principal/action/time bounds and rule priority. Neither provides the production controls in this document. The reference envelope HMAC protects fields against parties without the shared key, but key provisioning, rotation, confidentiality, endpoint compromise, and denial of service remain outside its stated scope ([CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md), [authority evaluator](../04-reference-implementation/authority_policy.py), [envelope evidence](../04-reference-implementation/adaptive-response-filter/EVIDENCE.md)).

## Required validation before a customer pilot

1. Draw actual identities, data classes, trust boundaries, network paths, and service principals with the customer.
2. Verify one negative test per threat: spoofed/expired identity, prompt-injected action, cross-tenant request, self-approval, stale/replayed approval, missing audit event, oversized payload, and dependency outage.
3. Confirm CRM permission enforcement and conditional-write/idempotency behavior against a non-production tenant.
4. Have security, privacy, compliance, CRM, and operations owners accept residual risks and retention rules.
5. Revisit this model after deployment topology and provider are selected; this document is not a security certification.
