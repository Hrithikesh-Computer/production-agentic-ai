# CRM approval and audit design note

This note records the rationale for a local deterministic CRM approval workflow. The detailed validation contract, state and reason definitions, failure and recovery tables, SQLite schemas, policy-hash inputs, and scenario matrix are in [VALIDATION-CONTRACT.md](VALIDATION-CONTRACT.md).

## Design authority

ADR-002 governs approval semantics. Approval is evidence of a human decision, not a bearer credential and not independent authority to mutate. It binds requester, reviewer, action, target, proposed value, record version, and expiry. The execution path re-checks current identity, scope, authority, policy, and record version. This keeps the CRM boundary fail-closed when an approval is stale or no longer authorized.

The local identity provider is the source of identity, status, and scope. These are checked live during execution, not inferred from caller-supplied fields or proposal content. The existing `authority_policy.py` supplies bounded grant, rule, and aggregation decisions; it does not authenticate identity.

## Local persistence choices

The proposal uses three separate SQLite files and separate connections for approvals, CRM state and its execution ledger, and audit events. Their separation makes partial success visible: a CRM write can commit while another store is unavailable. A single cross-store transaction would hide the failure boundary the validation is intended to examine, and SQLite does not provide a transaction spanning these separate files through separate connections.

Inside the CRM store, the record mutation and its execution-ledger row commit in one transaction. The ledger is authoritative for whether a mutation happened. The audit store records and reconstructs the result, but is not the authority for CRM mutation state and is not assumed tamper-proof.

## Claim and recovery

A single conditional update moves an eligible approval from `APPROVED` to `EXECUTING`; only a row count of one claims it. This delegates the local single-winner decision to SQLite rather than a Python lock. Tests assert persisted outcomes, not which competing process wins.

A crash or write failure after claim does not create a separate failure reason. The approval stays `EXECUTING` until explicit `recover()` checks the CRM ledger. No ledger row means no committed mutation, so recovery returns the approval to `APPROVED`; a retry gets a new `execution_id` and repeats all execution-time checks. A matching ledger row means the mutation occurred; recovery reconciles the audit before reporting completion. Until that evidence is reconciled, the caller receives an unresolved result, never success.

## Policy snapshot

The policy hash is deliberately narrow and deterministic: it covers policy rules, only the requester and reviewer grants on the requested action, and aggregation constraints. Referral is represented by a rule effect. The evaluation-time clock and live provider scope/status are not policy snapshot fields. Ticket and accumulated-session evaluation are outside this workflow, so their inputs do not enter the hash.

This distinction prevents a policy fingerprint from being mistaken for a current authorization check. Current identity, provider status, scope, time validity, and record freshness are still checked in the execution path.

## Scope and evidence

The implementation target is Python standard library `sqlite3`, deterministic local fakes, and local multiprocess SQLite contention. Distributed coordination, real identity-provider or CRM integration, production deployment, and customer evidence are outside scope. This design does not raise the repository's CRM workflow evidence level: it remains L2 until implementation evidence is produced, and deterministic fakes alone do not establish L3.

The validation criteria and explicit non-guarantees are maintained in [VALIDATION-CONTRACT.md](VALIDATION-CONTRACT.md). No production readiness, customer result, tamper-proof audit, or cross-store atomicity claim follows from this local design.
