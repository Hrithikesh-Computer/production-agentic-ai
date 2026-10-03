# CRM Operational Copilot Evidence

## Scope

Evidence here is for the local prototype and its static mock dataset only. This is not a Salesforce or REST integration, and neither example uses an LLM. The original `crm_copilot.py` remains read-only: `MockReasoningModel` deterministically selects two allowed read actions and the local summarizer computes a rule-based summary. The separate `approval_workflow.py` simulates a write against a private in-memory copy of the fixture data.

## Actual local timing samples

Captured 2026-10-01 by invoking `crm_copilot.py` three times with the local venv Python executable, `CRM_API_TOKEN` set to a non-production test value, and the mock CRM adapter. Timings are the values emitted by the prototype's `time.perf_counter()` measurement; they are not network, model, or production timings.

| Input | Result | `read_account` duration | `read_opportunities` duration | End-to-end duration |
|---|---|---:|---:|---:|
| `CUST-1001` | success | 0.006 ms | 0.004 ms | 0.210 ms |
| `CUST-1002` | success | 0.005 ms | 0.004 ms | 0.181 ms |
| `CUST-1003` | success | 0.006 ms | 0.004 ms | 0.184 ms |

These measurements include local validation, mock tool calls, deterministic action selection and summary construction, and JSONL logging performed inside the measured run. They exclude Python process startup and do not predict a live CRM or model integration.

## Security controls implemented in code

- Credential check: the adapter rejects an absent credential and values shorter than eight characters. The CLI reads the token only from `CRM_API_TOKEN`; it does not accept a token command-line option. This is a local presence/format gate, not validation of a real CRM credential.
- Scope enforcement: the adapter checks `read:accounts` and `read:opportunities` on each operation. The orchestrator allowlists only `read_account` and `read_opportunities`; unsupported actions fail before a tool call. An explicit empty scope list grants no access.
- Read-only behavior: the mock adapter exposes no write or update method.
- Audit logging: each run records timestamp, input, selected actions, tool calls and their durations, total measured duration, status, and output. Failed input, action selection, and tool errors are logged too.
- Secret handling: the CLI consumes the credential from an environment variable and does not emit it in output or the run log. Secret storage, rotation, and process-environment protections are not implemented.

## Approval workflow evidence

The separate approval-flow simulation has these locally implemented controls:

- The authority evaluator returns `refer` for the mock `write:accounts` policy. Submission records `human_review_required`; the outcome is not itself authorization to write.
- It uses the repository's bounded authority evaluator for `write:accounts` and `approve:crm-writes` decisions. Execution requires the requester to retain current write scope and the distinct reviewer to retain current approval scope.
- A proposal is bound to requester, customer ID, field, expected record version, and expiry. The proposed value is shown to the reviewer but is not written to audit events.
- The requester cannot approve their own proposal. Rejected, expired, stale, or already executed proposals cannot be executed.
- Write scope and policy are checked when proposing and checked again at execution; the mock connector verifies the approved proposal matches actor, target, field, value, and record version before changing its in-memory fixture.
- A record-version change between proposal and execution marks the proposal stale and prevents the update.
- The demonstration records proposal, approval/rejection, authorization denial, execution start, and execution result as local JSONL events.
- Focused tests cover the successful propose/refer/approve/recheck/execute path, no execution before approval, direct connector refusal without a matching approval, self-approval denial, missing write scope, requester and reviewer revocation, stale record, expiry, rejection, replay, and event timestamps. The focused workflow test file reports 10 passing tests; the separate authority referral tests cover decision propagation and ticket behavior.
- Local validation for the workflow: 10 focused pytest cases pass, Ruff passes, and mypy reports no issues in the workflow and focused test files when the repository-local import paths are configured.

These are local prototype controls, not production guarantees. Principal and reviewer names are supplied by the caller rather than authenticated; proposals, approval state, and mock CRM data are in memory; JSONL is not tamper-resistant; and a process crash between the mock write and final audit event is not transactionally recovered. The original CLI remains read-only; only the separate workflow demonstration writes to its private in-memory fixture.

Focused tests observed 6 passing CRM cases after these controls were added. The prototype and its test file pass Ruff and mypy.

## Evidence required

- `EVIDENCE REQUIRED: live CRM/REST endpoint, credential format, and an authorized non-production test account` to validate real authentication and API behavior.
- `EVIDENCE REQUIRED: identity-to-scope mapping and server-enforced least-privilege policy`; current scopes are a local allowlist, not an identity-aware authorization decision.
- `EVIDENCE REQUIRED: model/provider, prompt, action-selection policy, and evaluation results`; current action selection and summarization are deterministic and contain no model call.
- `EVIDENCE REQUIRED: production audit retention, access control, redaction, and tamper-resistance requirements`.
- `EVIDENCE REQUIRED: representative CRM data and end-to-end timings with network and model calls`.
- `EVIDENCE REQUIRED: customer identity-to-reviewer mapping, approval separation-of-duties criteria, and human approval rules` for a live integration; the local approval flow is only a deterministic simulation.
- `EVIDENCE REQUIRED: durable approval state, atomic/idempotent CRM write behavior, and audit reconciliation after process or dependency failure`.
