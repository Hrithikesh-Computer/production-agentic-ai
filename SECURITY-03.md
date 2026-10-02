# Security Mapping: Document 03, WalkMe Workflow Automation Copilot

Archived source: `archive/design-sketches-2026/03-walkme-workflow-automation-copilot.md`.

## Actions this agent can take

The document describes classifying and routing user intent, planning a workflow, showing guided UI steps, executing browser automation/clicks or backend API calls, tracking workflow state, returning evidence/status, and escalating to a human. No corresponding agent, browser automation, or workflow runtime exists in this repository. These are design-intent actions only.

**Status:** `[doc-only]`. `EVIDENCE REQUIRED: executable action inventory, target applications, and runtime traces`.

## Authentication

The document does not define user, agent, browser-extension, or backend-service authentication.

**Status:** not implemented. `EVIDENCE REQUIRED: identity provider, session/token validation, service identity, and credential validation behavior`.

## Authorization / least privilege

The document says actions should be bounded by workflow context and mentions explicit state tracking, but defines no roles, policy rules, permission checks, or least-privilege tool scopes.

**Status:** not implemented. `EVIDENCE REQUIRED: action-to-permission matrix, policy enforcement point, and denial tests`.

## Scope boundaries

The article distinguishes guided help, safe automation, backend API calls, and human escalation, but does not specify allowed browser actions, application/domain restrictions, or boundaries between read and write operations.

**Status:** design intent only. `EVIDENCE REQUIRED: allowlisted workflows, browser/API tool schemas, transaction boundaries, and prohibited-action tests`.

## Audit logging

The article refers to state tracking, execution result, evidence, and feedback, but does not specify an audit event schema, persistence, retention, or tamper resistance.

**Status:** not implemented. `EVIDENCE REQUIRED: logs from a running workflow showing actor, intent, selected action, tool input/output, approval, result, and timestamps`.

## Secrets / credential handling

The article names browser automation and backend API calls but does not explain how credentials are obtained, stored, scoped, refreshed, or redacted.

**Status:** not addressed. `EVIDENCE REQUIRED: secret-management design and tests showing secrets are not exposed in prompts, logs, browser state, or errors`.

The HMAC-SHA256 envelope in `04-reference-implementation/adaptive-response-filter/envelope.py` is a useful bar for code-backed enforcement: the receiver verifies an authenticator before accepting message data, and tampering tests cover the behavior. It is not a substitute for this workflow's different API-identity, browser-session, authorization, and secret-management controls.
