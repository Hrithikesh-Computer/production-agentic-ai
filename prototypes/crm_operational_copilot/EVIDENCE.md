# CRM Operational Copilot Evidence

## Scope

Evidence here is for the local prototype and its static mock dataset only. This is not a Salesforce or REST integration, and it does not use an LLM. `MockReasoningModel` deterministically selects two allowed read actions; the local summarizer computes a rule-based summary.

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

Focused tests observed 6 passing CRM cases after these controls were added. The prototype and its test file pass Ruff and mypy.

## Evidence required

- `EVIDENCE REQUIRED: live CRM/REST endpoint, credential format, and an authorized non-production test account` to validate real authentication and API behavior.
- `EVIDENCE REQUIRED: identity-to-scope mapping and server-enforced least-privilege policy`; current scopes are a local allowlist, not an identity-aware authorization decision.
- `EVIDENCE REQUIRED: model/provider, prompt, action-selection policy, and evaluation results`; current action selection and summarization are deterministic and contain no model call.
- `EVIDENCE REQUIRED: production audit retention, access control, redaction, and tamper-resistance requirements`.
- `EVIDENCE REQUIRED: representative CRM data and end-to-end timings with network and model calls`.
- `EVIDENCE REQUIRED: human approval criteria for any future write or workflow-triggering operation`; no writes or workflow updates are implemented.
