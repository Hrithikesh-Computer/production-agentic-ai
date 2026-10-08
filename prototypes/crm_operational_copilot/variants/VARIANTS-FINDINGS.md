# CRM Variant Findings

## Scope and Method

This branch compares the unchanged SQLite baseline with one axis varied at a time: store layout, no-write crash recovery, and claim mechanism. [R] The contract defines S01-S17 and ten invariants for local deterministic fakes. [R] The experiment runs five deliberate combinations (baseline plus one B choice per axis and one broken claim control), not the cross-product. [V]

The baseline remains the default and its source, tests, contract, ADRs, and level fields are unchanged. [V] The variants are comparative evidence only, not recommendations. [R] The bounded runs use only Python standard-library SQLite and deterministic local fixtures; no external service is contacted. [V]

## Store Layout

**A: baseline, three SQLite files.** The unchanged S01-S17 scenario test passed all 17 cases. [V] Three independent stores retain the baseline's separate failure boundaries and allow CRM commit followed by audit or approval persistence failure. [R]

**B: one SQLite file, three tables, one transaction across CRM, ledger, and audit.** The same 17-ID matrix records S11 and S12 against variant-specific persisted-state assertions because their baseline expected states deliberately no longer apply. [V] Injected approval-state and audit failures both rolled back the CRM record, ledger, and audit writes; the transaction returned persisted approval state to APPROVED, and the schema contained three tables. [V] The shared-file S09 N=50 check retained exactly one claim winner. [V]

The combined-transaction behavior removes the baseline's ability to reproduce a committed CRM write with a separate audit/approval store outage: those writes now share a rollback boundary. [V] In particular, the post-CRM-commit audit-failure window is untestable with this single-file layout; injecting an audit write failure rolls the CRM mutation back in the same transaction. [V] That is less failure-injection realism for the split-store failure cases and introduces shared-connection/transaction coordination complexity. [I] Keep A as the default because B changes the failure boundary being evaluated; B is useful only as comparative evidence for a different atomicity contract. [I]

## No-Write Crash Recovery

**A: baseline.** S10 passes with recovery returning the approval to APPROVED, clearing execution_id, leaving CRM and audit unchanged, and permitting a retry subject to rechecks. [V] This matches the documented contract. [R]

**B: invalidate for fresh review.** The same S10 scenario ID passes its variant-specific persisted-state assertion: recovery writes INVALIDATED with the variant-only reason `crash_no_write`, clears execution_id, and leaves CRM and audit unchanged. [V] Its approvals table has a variant-owned reason CHECK; the baseline schema constraint remains untouched. [V]

B adds one terminal state transition and requires a new approval/review after a crash despite persisted evidence of no CRM write. [V] The policy cost is reduced reuse of the prior approval but stronger conservatism after an unresolved attempt. [I] Keep A as baseline: a no-ledger result is the contract's explicit evidence that the CRM mutation did not commit, while B is a viable policy alternative rather than a demonstrated correctness improvement. [R/I]

## Claim Mechanism

**A: conditional UPDATE.** The S09 scenario plus 50 concurrent claim calls admitted exactly one claim. [V] The baseline claim uses one conditional UPDATE and checks rowcount. [R]

**B: BEGIN IMMEDIATE around read-then-write.** The S09 scenario plus the same 50-call test admitted exactly one claim. [V] The explicit transaction serializes SQLite writers before reading the approval state. [R]

**Broken control: read then write without a transaction.** A deterministic barrier released 50 readers only after each observed APPROVED; all 50 then reported claim success, so the required single-winner assertion failed. [V] The broken control fails S09 only in this matrix; the test is not too weak for this bounded interleaving. [V]

B and A both satisfy the tested single-winner invariant locally. [V] B adds explicit transaction handling and rollback paths; A is one conditional statement with rowcount-based success. [R] No measured production latency or cross-process / multi-host comparison was performed, so complexity is the only local cost comparison recorded here. [I] Keep A as baseline because it is smaller and passed the same observed contention test; this run does not establish that either mechanism is superior under production workloads. [V/I]

## Matrix Summary

`variants-matrix.csv` contains one row for each of five combinations and each S-ID (85 rows total), including a persisted-state assertion result. [V] The regenerated matrix has 84 passing rows and one failing row: broken-control S09; four variant-specific rows reinterpret S10 for recovery B and S11/S12 for store-layout B. [V] No scenario was marked not applicable in this run. [V]

## Costs and Limits

- **Store layout B:** shared connection and transaction orchestration complexity; loses separate-store post-CRM failure injection realism for S11/S12. [V/I]
- **Recovery B:** one additional terminal transition and mandatory fresh review after a no-write crash. [V]
- **Claim B:** read, state check, update, and explicit transaction error handling are more steps than the single conditional UPDATE. [R/I]
- **Broken control:** retained only as a negative control; it violates S09 under the deliberately synchronized 50-thread interleaving. [V]

Unproven: external SQLite configurations and filesystem behavior, process crash/power-loss durability, multi-host coordination, real CRM and identity-provider behavior, workload performance, operational recovery, tamper resistance, and customer outcomes. [R] These are local deterministic results only, not production evidence and not a change to any repository evidence level. [R/V] This experiment does not establish production readiness. [R]

## Validation

The CI workflow runs `scripts/check_crm_variants.py`; it regenerates the deterministic matrix and results in a temporary directory, checks the expected 85-row/one-failure shape, and compares both files byte-for-byte with the repository artifacts. [V] `variants-environment.json` records runtime details separately and is not compared byte-for-byte. [V]