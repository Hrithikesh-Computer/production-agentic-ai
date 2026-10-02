# CRM operational copilot prototype

This prototype is a deliberately narrow, read-only CRM copilot that demonstrates:

- explicit authentication
- scope enforcement
- structured logging
- bounded customer lookups and opportunity reads
- no writes, no CRM updates, no live integrations

## Scope boundary

This is not a production CRM integration. It is a teaching/reference prototype for an operational workflow that keeps the tool surface constrained to read-only access and logs each run for inspection.

## Usage

From the repository root:

```bash
set CRM_API_TOKEN=demo-token-12345
python prototypes/crm_operational_copilot/crm_copilot.py --customer-id CUST-1001
```

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

The example data is intentionally local and static, so it remains easy to inspect and test without inventing a live enterprise environment.
