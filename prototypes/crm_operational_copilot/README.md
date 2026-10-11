# CRM operational copilot prototype

This prototype directory contains two deliberately narrow local examples:

- the original read-only CLI, with mock customer lookups, scope checks, and JSONL run logging
- a separate approval workflow demonstration that updates only an in-memory copy of mock records
- a SQLite-backed deterministic validation baseline with separate approval, CRM/ledger, and audit stores

## Scope boundary

None of these examples is a production CRM integration. The original CLI remains read-only. The separate `approval_workflow.py` example simulates a bounded account update and JSONL audit in memory. The SQLite baseline uses deterministic local identities and persists approvals, CRM state plus its ledger, and audit records in separate files; it does not provide a live CRM, authenticated enterprise identity provider, model, or distributed transaction.

The proposed target design is documented in the [solution overview](../../architecture/00-solution-overview.md), [container view](../../architecture/01-context-and-containers.md), and [threat model](../../architecture/04-threat-model.md). Only `approval_workflow.py` is the in-memory sequence; the separate SQLite validation baseline demonstrates local persisted-state and recovery behavior without claiming a live integration.

## Evidence alignment rule

This prototype follows the repository's evidence boundary strictly.

- Implemented locally: the read-only CLI, the in-memory approval flow, and the SQLite validation harness are present in this folder and backed by tests.
- Conceptual only: the broader enterprise CRM, real identity provider, production approval service, and deployment model remain architecture proposals, not live implementation.
- Historical/archived: dated review artifacts and earlier design drafts are not current guidance when they conflict with the present prototype and tests.

Any statement that reads like a live customer system, delegated production authorization service, or deployment claim is out of scope for this directory unless the relevant code, test, and evidence file are also present.

## Usage

From the repository root:

```bash
set CRM_API_TOKEN=demo-token-12345
python prototypes/crm_operational_copilot/crm_copilot.py --customer-id CUST-1001
```

Run the isolated approval-flow simulation:

```bash
python prototypes/crm_operational_copilot/approval_workflow.py
python -m pytest -q prototypes/crm_operational_copilot/test_approval_workflow.py
```

Run the local contract harness and evidence check:

```bash
python prototypes/crm_operational_copilot/validation_harness.py
python scripts/check_crm_validation_evidence.py
```

The workflow demo writes its JSONL audit output to the system temporary directory by default. Pass `--log-path` to select another local path.

Optional scope override:

```bash
python prototypes/crm_operational_copilot/crm_copilot.py --customer-id CUST-1002 --allowed-scopes read:accounts,read:opportunities
```

## Behavior

The tool enforces:

- token presence and minimum length
- allowed scopes on every read
- customer ID validation against the mock dataset
- structured logging to `run_log.jsonl` in the prototype folder

The example data is intentionally local and static, so it remains easy to inspect and test without inventing a live enterprise environment. The in-memory approval simulation starts with a private copy of those fixtures; neither it nor the SQLite validation baseline changes the read-only CLI's data or connects to a CRM.
