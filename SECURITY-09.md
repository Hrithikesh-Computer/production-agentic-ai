# Security Mapping: Document 09, CRM Operational Copilot

Source: `01-agent-architecture/09-crm-operational-copilot-salesforce-agentforce-poc.md`.

## Actions this agent can take

The article describes retrieving customer/opportunity context, summarizing account history, suggesting next actions, and potentially triggering validated workflows. The existing prototype in `prototypes/crm_operational_copilot/crm_copilot.py` implements only mock-data account/opportunity reads and deterministic summaries. It has no live CRM connection, no model call, and no writes, updates, or workflow trigger. The prototype tests verify that only the two read actions are allowlisted.

**Implemented:** mock `read_account`, mock `read_opportunities`, local summary, and rejection of an unlisted action. **Not implemented:** live CRM reads, workflow actions, or writes.

## Authentication

The mock adapter rejects a missing credential and values shorter than eight characters. The CLI reads `CRM_API_TOKEN` from the environment and does not accept a token CLI argument. This is a local presence/length check, not authentication against Salesforce or any identity provider.

**Implemented locally:** presence/length check, covered by `test_adapter_rejects_missing_or_short_credential`.

`EVIDENCE REQUIRED: real CRM credential validation, identity binding, token audience/scope validation, expiration/revocation behavior, and negative integration tests`.

## Authorization / least privilege

The mock adapter enforces `read:accounts` and `read:opportunities` on each method call. The orchestrator allowlists `read_account` and `read_opportunities`; an explicit empty scope list remains empty. These are local checks over mock data and a caller-supplied allowlist, not identity-aware CRM authorization.

**Implemented locally:** read-scope checks and action allowlisting, covered by `test_adapter_enforces_read_scope`, `test_empty_scope_list_does_not_restore_default_permissions`, and `test_orchestrator_rejects_unlisted_action_and_logs_failure`.

`EVIDENCE REQUIRED: CRM-side least-privilege scopes, per-user record-level authorization, and independent enforcement by the remote API`.

## Scope boundaries

The existing adapter exposes reads only, uses three static customer records, validates `CUST-####`, and provides no write/update methods. The prototype makes deterministic read/summarize behavior possible, not workflow modification.

**Implemented locally:** bounded mock dataset and read-only tool surface. **Not implemented:** live tenant/data boundaries or controls on future write-capable tools.

`EVIDENCE REQUIRED: tenant isolation, record filtering, field-level restrictions, and tests against the real CRM API`.

## Audit logging

Every run, including failures, records timestamp, input, selected actions, tool calls and durations, total duration, status, and output in JSONL. The current file logger is local append-only output; it does not provide central access control, tamper evidence, retention, or redaction policy.

**Implemented locally:** structured run logging, covered by the CRM prototype tests.

`EVIDENCE REQUIRED: production log access controls, retention, immutable storage, sensitive-field redaction, and audit completeness review`.

## Secrets / credential handling

The CLI consumes `CRM_API_TOKEN` from the environment and does not include it in its output or run record. The prototype does not use a secret manager, encrypt logs, rotate credentials, or prove protection of process environment variables.

**Implemented locally:** avoid token command-line argument and avoid token logging.

`EVIDENCE REQUIRED: managed secret storage, rotation/revocation, runtime access policy, and leak scanning`.

The HMAC-SHA256 envelope at `04-reference-implementation/adaptive-response-filter/envelope.py` is the evidence bar for a concrete, test-backed check. It protects chunk integrity/authenticity against parties without the shared key; it is not an API credential or CRM authorization control. CRM production security must instead prove credential validation, identity-to-scope binding, remote-side least privilege, and audit handling.
