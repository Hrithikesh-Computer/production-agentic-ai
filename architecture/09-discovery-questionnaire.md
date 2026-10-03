# Customer Discovery Questionnaire: CRM Operations Copilot

Use this before selecting a deployment, model, policy engine, or SLO. Record the customer answer, owner, evidence/source, and unresolved follow-up; do not assume the proposed architecture reflects their environment.

## Business workflow

1. Which CRM task, users, desired outcome, and current baseline (time, rework, errors, reviewer effort) define the first use case?
2. Which outputs are advisory only, and which actions could change CRM state or trigger downstream workflows?
3. What pilot evidence and acceptance thresholds would justify continuing to production discovery?

## Data and privacy

4. Which CRM objects, fields, notes, attachments, and activities are required, prohibited, or specially classified (personal, financial, health, export-controlled, confidential)?
5. May classified CRM data be sent to an external model provider; which regions, retention/training terms, and subprocessors are acceptable?
6. What must be redacted from prompts, application logs, audit events, traces, and support bundles?
7. What retention, deletion, legal-hold, data-subject request, and backup-expiry requirements apply to each data type?

## Identity and authority

8. Which identity provider/protocol is used, and what verified identity, tenant, group, and device claims are available?
9. Should CRM calls use delegated employee identity, a service identity, or a hybrid; how are row-, object-, and field-level permissions enforced?
10. Which read/write operations are allowed, and which require review, step-up authentication, or two-person approval?
11. Must requester and reviewer differ; which roles may review each action, and how are conflicts handled?
12. What happens if user access or policy changes while a proposal is pending?

## Approval and audit

13. What proposal evidence must the reviewer see, and how long is approval valid before it expires?
14. Which CRM changes invalidate an approval; does the API support ETags/version checks, conditional writes, and idempotency?
15. What approval volumes, queue-age limits, escalation/rejection path, and out-of-hours process are required?
16. Which events must be audited, who can read/export/delete them, and what tamper-evidence/immutable-retention rules apply?

## Operations and deployment

17. What are average/peak tasks, burst concurrency, payload sizes, token distributions, and CRM API quotas?
18. What availability, p95 latency, throughput, RTO/RPO, degraded-mode, cloud/region, and network requirements apply to reads and writes?
19. What alerting, incident response, on-call/support ownership, rollback authority, and change-control process are required?

## Commercial and success criteria

20. What cost/labor baseline, acceptable reviewer minutes, dated vendor price sources, attribution method, and security/procurement go/no-go evidence will be used?

## Exit criteria for architecture discovery

Do not finalize target deployment or commit NFR values until there is an owner and sourced answer for workflow scope, data classification/provider boundary, identity and CRM authorization, approval rules, record concurrency semantics, audit retention, environment, workload profile, and measurable success criteria. Open items should remain explicit risks rather than silently becoming design assumptions.
