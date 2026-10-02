# Authority-Layer Addendum: Document 09

Source: `01-agent-architecture/09-crm-operational-copilot-salesforce-agentforce-poc.md`. The eight layer names and questions follow `01-agent-architecture/01-agent-authority-and-intent.md`. This maps both the article's intended actions and the narrower implementation in `prototypes/crm_operational_copilot/`; local mock behavior is not evidence of Salesforce production authority.

## Action-to-layer mapping

| Implied action | Identity / trust | Scope / capability | Delegation provenance | Structural derivability | Priority / defeat | Runtime validity | Semantic alignment | Decision policy |
|---|---|---|---|---|---|---|---|---|
| Retrieve customer and opportunity context | Article: not addressed. Prototype: rejects missing/short token; no real principal authentication. | Article: says bounded tools/access controls. Prototype: enforces `read:accounts` and `read:opportunities` on mock adapter methods. | Not addressed in article or prototype. | Not addressed. | Not addressed. | No token expiry/revocation or remote authorization check; static local data only. | User query maps to a customer ID; broader intent match is not defined. | Invalid input and unlisted actions fail in prototype; data-access uncertainty rules are absent. |
| Summarize account history | Model identity/trust not addressed; prototype does not call a model. | Local summary reads only mock account/opportunity fields. | Source lineage into the summary is not retained as structured provenance. | Summary arithmetic/rules are deterministic locally, but no completeness or derivation contract is defined. | Conflicting records/overrides not addressed. | Data freshness is not checked; records are static. | Summary relevance to user intent is not evaluated beyond valid customer ID. | Prototype returns deterministic output; confidence, referral, or review policy is absent. |
| Suggest next actions | Article: suggests recommendations but no verification boundary. Prototype: deterministic rule-based recommendation only. | Suggestions are not executable capabilities in the prototype. | Not addressed. | Rule-to-recommendation derivation is present in code but is not tied to cited business policy. | Policy conflicts/overrides not addressed. | No current-state validation before recommendation. | No explicit test that recommendation matches the user's intended outcome. | No uncertainty/review threshold. |
| Trigger validated workflows / update CRM state | Article: mentions validated workflow triggers, but does not define them. Prototype: no write or trigger method exists. | No write scope or operation allowlist exists; current prototype is read-only. | Approval/delegation chain not addressed. | Validation predicate and permitted state transition are not specified. | Conflict with existing CRM state or policy not addressed. | No pre-write revalidation, idempotency, or revocation check. | No confirmation that the workflow action matches user intent. | Approval/escalation criteria are not specified; no action executes. |

## Eight-layer status

- Identity and trust: prototype has a local credential presence/length check; actual CRM identity is `EVIDENCE REQUIRED`.
- Scope and capability: prototype enforces local read scopes and an action allowlist; remote tenant/record-level authorization is `EVIDENCE REQUIRED`.
- Delegation provenance: not addressed.
- Structural derivability: local summary rules exist; evidence lineage and policy-backed derivation are not addressed.
- Priority and defeat: not addressed.
- Runtime validity: not addressed beyond local input validation; credential expiration, revocation, and record freshness are `EVIDENCE REQUIRED`.
- Semantic alignment: not addressed beyond requiring a customer ID; intent-to-action verification is `EVIDENCE REQUIRED`.
- Decision policy: the mock returns a deterministic summary and fails invalid/unlisted actions; uncertainty thresholds, approvals, and production deny/refer policy are `EVIDENCE REQUIRED`.

The HMAC-SHA256 envelope added to the response-filter reference authenticates chunks to a shared key and rejects tampering. It is not the answer for CRM authority: this workflow needs verified user/service identities, remote least privilege, provenance from CRM records to recommendations, and explicit policy around any future writes.
