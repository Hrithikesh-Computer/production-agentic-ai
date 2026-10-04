# Repository Evaluation: Second Pass

**Reviewed:** 2026-10-03
**Scope:** Repository state first inspected on `cleanup/dedupe`, plus explicitly labeled follow-up commits and clean-checkout validations. Final review corrections are committed after the chronological commits listed below. This is a repository-evidence review, not a customer or deployment assessment.

**Evidence labels:** **Fact** means directly observed in code, tests, docs, or command output. **Inference** means a reasoned assessment from that evidence. **Assumption** means unverified and not to be treated as a repo capability or customer requirement.

## Summary

**Fact:** The repository has matured from a handbook plus reference slices into a handbook with a proposed CRM architecture bundle and a deterministic in-memory approval simulation. The architecture labels its services as proposed; the workflow tests demonstrate useful serial-path behavior. The first-inspection working tree reported 118 tests. After review edits, the suite reported 127 tests. A clean checkout of `a1a71c8` initially had a duplicate-module whole-repository mypy failure; commit `ae9150c` removes that collision. CI now tests Python 3.10 and 3.14, runs whole-repository mypy, and checks local links plus cited benchmark figures. The workspace interpreter is Python 3.14.6.

**Inference:** The work demonstrates competent architecture decomposition and evidence discipline, but not a customer-ready solution architecture. The largest remaining gap is proof at real identity, CRM, persistence, concurrency, and operations boundaries. The approval simulation's tested sequential flow should not be read as an atomic or authenticated workflow.

| Lens | Current handbook fit | Current portfolio design / evidence |
|---|---:|---:|
| Solution Architect | 4/5 | Design 4/5; evidence 3/5 |
| Real-World Trends | 3/5 | Design 2/5; evidence 1/5 |
| Presales | 4/5 | Design 4/5; evidence 1/5 |
| Forward Deployed | 4/5 | Design 3/5; evidence 2/5 |
| Mathematics | 4/5 | Design 3/5; evidence 3/5 |
| Philosophy/Psychology | 4/5 | Design 3/5; evidence 2/5 |

The prior pass's handbook scores are being compared under the same handbook-fit question; portfolio design quality and evidence strength are separate because the earlier “product readiness” dimension is not comparable. The portfolio design scores rate the quality of the architecture artifacts; evidence scores rate how far claims are validated beyond local examples. No portfolio evidence score exceeds 3. Trends remain unverified: no current external industry research was performed for this review.

**Top risks**

1. **Proposed architecture can be mistaken for implemented capability.** The overview and architecture index state the boundary, but there is no deployed application, real CRM, IdP, durable queue, or production audit store ([solution overview](../architecture/00-solution-overview.md), [CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md)).
2. **Approval correctness is only demonstrated for a sequential in-process path.** Principals are caller-supplied, state is in memory, and no lock/atomic consume protects review, execution, record mutation, or audit from races and failures ([workflow](../prototypes/crm_operational_copilot/approval_workflow.py), [workflow tests](../prototypes/crm_operational_copilot/test_approval_workflow.py)).
3. **Operational and market evidence remain absent.** Sizing inputs are illustrative, price fields are TBD, there is no real deployment/runbook, and current industry position is unverified ([NFR worksheet](../architecture/05-nfr-and-sizing.md), [cost model](../architecture/07-cost-model.md)).

**Top next actions**

1. Add NDJSON coverage and approval-workflow mutation/concurrency checks to CI. Add fresh mutants or an independent mutation-testing run; the current custom mutants were developed alongside the tests. The Python 3.10/3.14 matrix, whole-repository mypy, and documentation/evidence guards are in CI.
2. Fix approval identity binding, atomic state consumption, audit-failure recovery, and bounded state; add concurrency and audit-sink-failure tests.
3. Rerun the four-arm matrix on representative CRM payloads and named target clients, including a second browser engine and a parse-once-per-animation-frame variant; retain the harness-hash comparison, then select a customer-pilot metric and baseline before revisiting ADR-001.

## Changes made during this review

The review adds the CRM architecture/evidence corrections, separates synthetic browser measurements from customer claims, and records the remaining approval and operational gaps. The changed-file ledger and chronological validation record are in the [review evidence log](review-evidence-2026-10-04.md).

## Evidence Status

The first-inspection suite had 118 tests; after review additions it had 127. The final tagged checkout passes the full suite, Ruff, whole-repository mypy, and both evidence guards under CPython 3.10.20. Hosted Ubuntu CI is still required. Detailed per-commit results, import provenance, link audit, benchmark README/CSV comparison, mutation scope, and the first-inspection snapshot are in the [review evidence log](review-evidence-2026-10-04.md).

## Historical Snapshot

The first-inspection Git status, commit history, prior-action table, citation spot-checks, mutation details, and branch-coverage output are preserved in the [review evidence log](review-evidence-2026-10-04.md). These are historical evidence, not statements about the final committed tree.

## 1. Architecture Bundle Review

### Overview and traceability

**Fact:** The overview identifies the user group (enterprise account teams), problem (CRM context and operational actions), desired control (human approval and fresh authorization before writes), scope, exclusions, and explicit non-implementation boundary ([overview](../architecture/00-solution-overview.md)). It is short enough for a two-minute orientation.

**Inference:** A non-engineer can broadly explain the scenario after reading it, though “authority gateway,” “action-bound,” and “record version” need plain-language explanation. The promise is design intent, not an implemented capability.

**Fact:** STRIDE F1-F12 map to the C4 container relationships: browser/request, identity, policy, connector/CRM, model, proposal/queue, reviewer decision, and audit flows. F11 composes the web-to-authority and authority-to-queue relationships; F12 names the three services that emit to audit ([threat model](../architecture/04-threat-model.md), [container diagram](../architecture/diagrams/c4-containers.mmd)). AWS mapping includes all six application containers: web/UI, agent, authority, CRM connector, approval queue/state, and audit store; IdP, CRM, and model remain external/candidate services ([AWS view](../architecture/06-deployment-views.md), [AWS diagram](../architecture/diagrams/aws-deployment.mmd)).

**Inference:** The context diagram simplifies the reviewer path as reviewer-to-approval, while the container view routes reviewer input through web-to-authority-to-queue. This is understandable abstraction, but the exact reviewer API boundary should be made explicit before implementation ([context diagram](../architecture/diagrams/c4-context.mmd), [container diagram](../architecture/diagrams/c4-containers.mmd)).

### ADRs and options

| ADR | Context/options/decision/consequences | Evidence linkage and gap |
|---|---|---|
| ADR-001 Response delivery | Has context and five options, including full-body gzip and gzip-plus-NDJSON; decision remains reopened pending representative CRM payloads and named clients. Trade-offs include partial UI state and whole-read retry versus atomic full-body delivery, compression CPU, framing costs, and runtime-dependent completion. | Links repository article, benchmark evidence, and reference boundary. The clean standalone four-mode run is a matched synthetic comparison with a passing Long Task control and recorded provenance. Electron has matching payload sizes but failed its Long Task control and lacks historical provenance. No customer measurements or second browser engine exist ([ADR-001](../architecture/02-decisions/ADR-001-response-delivery.md)). |
| ADR-002 Approval evidence/signing | Has context, HMAC/asymmetric/server-side options, a server-side action-bound decision, and consequences. It gives up reusable portable signed approval as the default. | Links authority code and envelope evidence. It does not link the approval workflow's focused tests; those tests are relevant evidence that should be added to the record ([ADR-002](../architecture/02-decisions/ADR-002-approval-signing.md)). |
| ADR-003 Context lifecycle | Has context, three options, explicit deferral decision, consequences, and evidence gaps. It gives up cross-session recall/personalization in the first increment. | Links the research note and prior deferral. No representative CRM multi-turn workload exists ([ADR-003](../architecture/02-decisions/ADR-003-context-lifecycle-deferral.md)). |

**Inference:** All three contain the requested ADR elements and do more than justify a preferred option. ADR-002 is the least connected to executable approval evidence. Decision owners are unassigned, and none is a record of a deployed decision.

**Fact:** Options analysis uses the same columns for all three options (cost to start, risk, time to first slice, operability, lock-in) and makes Option B provisional, with conditions that could retain Option A for a single-process prototype ([options analysis](../architecture/03-options-analysis.md)).

**Inference:** The recommendation is conditional and the limitations are clear. The ratings remain qualitative and are not calibrated against measured workload, customer constraints, prices, or a decision-weighting method.

### Delivery evidence and the compression alternative

**Fact:** Three artifacts must be kept distinct: the legacy standalone three-mode run (`browser_results.json`), the clean four-mode standalone run (`browser_results_standalone_compression.json`), and the Electron four-mode run (`browser_results_compression.json`). The legacy run includes `full`, `gzip_full`, and `framed_http`; both four-mode runs add `gzip_framed`. Gzip bodies are precomputed before per-request timing, so delivery timings do not include per-request server compression CPU. `framed_body_bytes` counts NDJSON application-body bytes and excludes HTTP chunk-transfer delimiters ([browser harness](../benchmarks/response-delivery/browser_benchmark.py), [legacy results](../benchmarks/response-delivery/browser_results.json), [clean standalone results](../benchmarks/response-delivery/browser_results_standalone_compression.json), [Electron results](../benchmarks/response-delivery/browser_results_compression.json)).

The legacy standalone P50s for the nominal 300 KB cases are preserved in the [browser matrix evidence](../benchmarks/response-delivery/browser-matrix-evidence.md#legacy-standalone-timings).

**Inference:** For structured data, gzip reaches first visibility 11.8-31.8 ms after framing, while at the slowest pace gzip completes 6.9x faster than framed delivery. For text-like data, gzip is 9.2 ms earlier at the slowest rate and 0.5-2.8 ms later at the other rates; at the slowest rate it completes about 10.2x faster than framing. These outcomes make compression a serious candidate when full completion matters, not a universal winner for first visibility.

**Inference:** At 10 MB/s, the structured 300 KB full-to-NDJSON completion penalty is 86.9 ms in the legacy standalone run (177.6 vs 90.7 ms), 89.4 ms in the clean four-mode standalone run (182.1 vs 92.7 ms), and 30.0 ms in Electron (123.5 vs 93.5 ms). The Electron penalty is 56.9 ms smaller than legacy and 59.4 ms smaller than the clean standalone run, despite matching structured payload sizes. The extra 55,151 application bytes in NDJSON account for about 5.5 ms at 10 MB/s; the remaining observed delay is not a universal NDJSON cost. The close legacy/clean standalone results and much smaller Electron penalty indicate runtime-dependent client delivery/parsing behavior in this harness; they do not isolate parsing as the cause. A second browser engine and a parse-once-per-animation-frame variant are needed before attributing the difference to a particular client implementation.

**Follow-up fact:** The four-arm Electron matrix contains 384 request timing records. Detailed payload sizes and saved P50 first-visible/completion values for all four modes are in the [browser matrix evidence](../benchmarks/response-delivery/browser-matrix-evidence.md#electron-four-mode-timings).

**Inference:** Gzip NDJSON reaches first-visible content earlier than full-body gzip in all eight displayed cells, by 11.1-100.7 ms (large margins in seven). Completion is close: gzip NDJSON is 1.3-16.0 ms later in five cells and 3.0-21.8 ms earlier in three. Against uncompressed NDJSON, gzip NDJSON is earlier only in the two 2 MB/s cells and later in the other six; the apparent 2 MB/s lead is not treated as a compression benefit because uncompressed NDJSON is anomalously late there. Treat gzip-plus-framing as a measured candidate that is near the best on both metrics, not a universal winner. The Electron Long Task positive control requested 120 ms was not detected; unlike both standalone artifacts, this run supports no Long Task conclusion.

**Follow-up comparison:** For the structured 300,007-byte payload, all three common arms have identical serialized sizes in the legacy standalone and Electron artifacts. The complete side-by-side P50 comparison is in the [browser matrix evidence](../benchmarks/response-delivery/browser-matrix-evidence.md#legacy-to-electron-comparison).

At 0.512 MB/s, common-arm results agree within 3.4 ms. At 2 MB/s, the uncompressed NDJSON first-visible result is 21.1 ms later in Electron, while its completion differs by only 4.0 ms. The harness pacing model predicts first-visible near $40 + 16{,}000 / 2{,}000{,}000 \times 1000 + 5 \approx 53$ ms. In the clean standalone run, uncompressed NDJSON is 52.9 ms for both payloads, close to that model; gzip NDJSON is 55.5 ms structured and 59.5 ms text-like. The Electron-only 75.2/75.0 ms deviation is consistent with browser delivery/coalescing effects, but the artifact cannot identify the cause. The apparent Electron gzip-NDJSON lead at 2 MB/s is not reproduced and should not be interpreted as a compression benefit.

**Inference:** In this Electron artifact, full-body gzip sits near 75 ms for the structured 2/10/50 MB/s cells and text-like 10/50 MB/s cells; text-like at 2 MB/s is 85.2 ms. Uncompressed NDJSON is often near 47-48 ms outside the 2 MB/s anomaly. The roughly 27 ms first-visible gap could reflect parsing the full response and constructing/appending the complete list versus rendering only initial records, but it is not isolated here as a UI cost. The clean standalone rerun does not reproduce a universal 75 ms floor, so treat this as runtime-specific; it is directionally consistent with the earlier 18 ms median list-build measurement.

**Fact / comparability limit:** Structured payload bytes match across all three artifacts, so the structured timing comparisons are like-for-like payload comparisons, though browser/runtime differences remain. The clean four-mode standalone and Electron text-like bodies also match at 443,577 B. Only the legacy text-like body is size-mismatched: it is 306,891 B, 30.8% smaller than the matched four-mode body; equivalently, the four-mode body is 44.5% larger than legacy. Its gzip body is 8,489 B (2.8%); the four-mode text-like gzip body is 70,898 B (16.0%). Both legacy and clean standalone artifacts detected their Long Task controls; Electron did not. Do not compare legacy and four-mode text-like timings as controlled payload comparisons.

**Fact / provenance limit:** The saved Electron JSON has no embedded run timestamp or harness hash. The clean four-mode standalone artifact records run/save timestamps, harness SHA-256, and process IDs, and confirms the sweep and timings shared a process. Its runner awaits the page promise and refuses to overwrite the saved result. The 100-repetition CPU sweep measures server-side gzip CPU only; browser/client decompression and rendering CPU remain unmeasured.

**Follow-up fact, clean four-mode standalone run:** The new [`browser_results_standalone_compression.json`](../benchmarks/response-delivery/browser_results_standalone_compression.json) was produced by the CDP runner in a fresh Chrome profile. It contains 384 request timing records, the 120 ms Long Task control was detected at 121 ms, the gzip sweep and browser timings share server PID `14644`, and the saved harness SHA-256 (`b9fcc9019f2b099eeb1a0d7e2df6551b274b60ca8b1836d3092ad7363164fce7`) matches the harness file. Its four-mode payload sizes match the Electron artifact. For the common structured 300,007-byte payload, the legacy and clean standalone runs agree within 3.7 ms on first-visible P50 and 4.5 ms on completion P50 across the four rates. The Electron departures therefore appear runtime-specific in this harness, although the mechanism is not isolated.

The clean four-mode standalone P50s for the same target and four modes are in the [browser matrix evidence](../benchmarks/response-delivery/browser-matrix-evidence.md#clean-four-mode-standalone-timings).

**Inference:** In the clean four-mode standalone run, gzip NDJSON reaches first visibility 1.7-111.5 ms before full-body gzip in all eight cells. Completion is payload-dependent: for structured data it is 29.0-40.2 ms later than full-body gzip in all four cells; for text-like data it ranges from 3.9 ms earlier to 4.5 ms later. Thus earlier first content does not imply equally early completion. In contrast to Electron, the 2 MB/s uncompressed NDJSON first-visible values fit the pacing model, and gzip NDJSON does not lead that arm.

**Compression-level inference:** Full sizes, paired CPU, wire-time savings, break-even rates, and best-level net values are tabulated in the [browser matrix evidence](../benchmarks/response-delivery/browser-matrix-evidence.md#compression-levels-and-estimated-break-even). Conservative break-even rates for levels 3/6/9 versus level 1 are about 6.1/2.4/0.64 MB/s for structured data and 5.6/3.3/1.6 MB/s for text-like data. Comparing all levels, structured data favors level 3 at 0.512 and 2 MB/s; text-like data favors level 6 at 0.512 MB/s and level 3 at 2 MB/s. At 2 MB/s, level 6 still beats level 1 for text-like data by about 9.2 ms net, but level 3 is better by about 3.3 ms. Level 1 is best at 10 and 50 MB/s under the measured paired-CPU model. Level 9 has positive net savings against level 1 only at 0.512 MB/s, but is never the best level because level 3 or 6 dominates it.

Halving the paired CPU to approximate full-body-only cost makes level 3 marginally positive at 10 MB/s (+0.3 ms structured, +0.4 ms text-like); for text-like data at 2 MB/s, levels 3 and 6 are nearly tied (+15.9 and +16.4 ms). At 50 MB/s, level 1 remains best. Thus the modeled advantage at 10 MB/s is under half a millisecond, and no meaningful latency gain is established at 10 MB/s or above. A tentative rule for these synthetic payloads is level 3 below roughly 6 MB/s, level 6 for text-heavy bodies only at the slowest tested link, and no use for level 9. Paired CPU compresses full plus framed bodies and is about twice full-body-only cost, so this sensitivity matters. Client decompression is excluded. If compressed bodies are cached as in the harness, request-path compression CPU vanishes and this break-even comparison does not apply.

**Assumption / limitation:** Across the clean four-mode standalone sweep, full-body gzip ratios range from 7.9-13.6% for structured payloads and 15.9-26.6% for text-like payloads. The legacy text-like payload compresses to 2.8%, while the matched four-mode text-like payload compresses to 16.0%. Representative CRM payload compression, client decompression cost, real client behavior, proxy behavior, end-to-end compression CPU, and production rates are **not found in repo**. Treat these runs as a reason to compare alternatives, not as proof that gzip is best for a customer.

**Fact, initial finding:** On first inspection, the article and legacy three-mode standalone JSON disagreed. For the structured 300 KB case at 0.512 MB/s, the article had `648.7 / 75.1 / 741.3 ms`, while the saved JSON had `647.3 / 76.1 / 745.3 ms`; other rows also differed. **Follow-up:** The article's legacy standalone ranges and examples were corrected to match [`browser_results.json`](../benchmarks/response-delivery/browser_results.json). The clean four-mode standalone and Electron four-mode artifacts remain separate and do not overwrite the legacy artifact ([article](../03-production-lessons/01-adaptive-response-delivery.md), [benchmark README](../benchmarks/response-delivery/README.md)).

**Inference:** The prior architecture assessment missed the cheapest alternative. Synthetic matched runs now compare full JSON with compression against framing, but ADR-001 still needs representative payloads, named target clients, a second browser engine, a parse-once-per-frame variant, and an explicit decision metric (first-visible versus completion).

### STRIDE, NFRs, and honesty

**Fact:** STRIDE entries provide controls and a residual question/owner role. Prompt injection, confused deputy, approval race/replay, key lifecycle, and audit tampering each have proposed controls ([threat model](../architecture/04-threat-model.md)). The document's pilot checklist calls for negative tests, but the threat rows do not map each control to an existing test or a named owning software component.

| Threat focus | Proposed control in model | Evidence/test status |
|---|---|---|
| Prompt injection | Treat CRM text as untrusted; typed/allowlisted tools; server-side action validation; reviewer and fresh authority check. | **No test.** No model/provider exists; no injection test is in the workflow suite. |
| Confused deputy / tenant crossing | User/tenant-scoped checks, narrow CRM scopes, CRM-side auth, deny-by-default. | **No tenant-isolation test.** Local scope names are caller-provided; the local fixture has no tenant boundary. |
| Approval race / replay | Atomic state transition, action/record binding, expiry, idempotency, conditional CRM write. | Sequential expiry/replay/stale tests exist; **no concurrent race, cross-action replay, or atomic consume test**. |
| Key compromise | Key ownership, rotation, and trust boundary are recognized in envelope/ADR evidence. | **No key-compromise/rotation test** and no production key service. |
| Audit tampering/failure | Restricted, correlated, immutable export proposed; audit failure behavior left to design. | **No tamper, sink-failure, or crash-recovery test**; local JSONL is mutable. |

**Fact:** The NFR worksheet labels its figures illustrative assumptions, separates candidate targets from commitments, and explicitly leaves prices/customer inputs TBD ([NFR and sizing](../architecture/05-nfr-and-sizing.md)). Recalculation using decimal units:

- Average task rate: $100 \times 2 / 3600 = 0.0556$ tasks/s; times four is $0.2222$ tasks/s. The worksheet rounds this up to $0.25$ for planning, about 12.5% above the direct result.
- At the rounded rate, serialized data is $0.25 \times 250\ KB \times 86{,}400 = 5.4\ GB/day$; audit is $0.25 \times 12 \times 2\ KB \times 86{,}400 = 518.4\ MB/day$.
- Little's Law estimate is $0.25 \times 6 = 1.5$ in-flight tasks. The separate raw-payload bound is $100 \times 16\ MB = 1.6\ GB$ before object overhead.

**Inference:** Arithmetic is consistent under decimal KB/MB/GB and continuous-peak assumptions. These are not measured capacity requirements; rounding and continuously sustained peaks should stay visible in any estimate.

The worksheet's daily-volume figures assume the peak rate persists for all 24 hours. They are conservative upper-envelope calculations, not expected daily traffic ([NFR and sizing](../architecture/05-nfr-and-sizing.md)).

**Fact:** Proposed status is explicit in the overview, C4 descriptions, threat model, AWS candidate, and bundle index. The AWS document says the mapping is not IaC or evidence of deployed services ([overview](../architecture/00-solution-overview.md), [AWS view](../architecture/06-deployment-views.md), [architecture index](../architecture/README.md)). **Inference:** The proposed/existing distinction is consistently honest; the main residual risk is readers overlooking it when viewing diagrams alone.

## 2. Approval Workflow Review

### Behavioral claims and tests

| Claim | Implementation evidence | Test evidence and assessment |
|---|---|---|
| No write before distinct human approval | `execute` requires approved state; connector checks approved record, reviewer presence, and reviewer != actor. | `test_write_is_not_executed_before_approval`, `test_requester_cannot_approve_own_proposal`, `test_connector_rejects_write_without_matching_approval_record`. **Passes for serial in-process calls.** |
| `refer` means review, not write authorization | `Effect` is `Literal["allow", "deny", "refer"]`; the evaluator returns `refer` for the winning refer rule. The CRM workflow imports `evaluate_authority` through `MockAuthorityGateway`; it does not call `issue_ticket` or `use_ticket`. Its mock policy returns `refer` for `write:accounts`; submission records `human_review_required`; execution requires approved status and revalidates the distinct reviewer's current authority. | `tests/test_authority_referral.py` covers evaluator, aggregate, ticket, and session referral behavior, including equal-priority precedence. The workflow success-path test checks the referral event/reason. **Implemented and tested locally.** ([authority policy](../04-reference-implementation/authority_policy.py), [referral tests](../tests/test_authority_referral.py), [workflow](../prototypes/crm_operational_copilot/approval_workflow.py)) |
| Fresh authority check | Requester write and reviewer approval scopes are checked at execution; connector checks again before mutation. | `test_write_scope_revocation_after_approval_blocks_execution` and `test_reviewer_scope_revocation_after_approval_blocks_execution`. **Sequential revocation covered.** |
| Record-version check | Proposal binds expected version; workflow and connector compare it before update. | `test_changed_record_invalidates_approval`. **Sequential stale update covered; concurrent TOCTOU is not.** |
| Expiry and replay | Expiry checked at review and execute; executed/rejected/expired/stale statuses cannot execute. | `test_expired_approval_and_replay_are_denied`, `test_rejected_proposal_cannot_execute`. **Serial boundary covered.** |
| Audit event order | Proposal, refer, approval, review-satisfied, execution-started, and success events are emitted. | Success-path test asserts event order and timestamps. **No sink failure, process crash, tampering, or concurrent event-order test.** |
| Exact action binding | Proposal captures requester, record, field, value, version, expiry; connector compares these to the update. | `test_connector_rejects_bound_action_substitution` covers field, value, and record substitution at the connector boundary. **Cross-proposal substitution is not demonstrated.** |

The evidence and tests are in [workflow source](../prototypes/crm_operational_copilot/approval_workflow.py), [focused tests](../prototypes/crm_operational_copilot/test_approval_workflow.py), and [CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md).

### Gaps and correctness notes

- **Identity/self-approval:** the equality check blocks the requester string from approving itself, but `requester`, `reviewer`, and scope-map keys are supplied by the caller. There is no authenticated identity binding. A caller able to choose the reviewer name can impersonate an authorized reviewer in this local API. This is not a tested production separation-of-duties control.
- **Race conditions:** workflow status checks and updates, the second record-version check and mutation, and reviewer assignment have no lock/transaction. Two concurrent execute calls could both pass the initial status check; the code does not implement the proposed atomic consume or real CRM conditional update. There are no concurrency tests.
- **Audit events can be absent:** the sink is called synchronously and exceptions are not transactionally coordinated with workflow state or CRM mutation. If `execution_succeeded` logging raises, the in-memory account has already changed and status is already `executed`, while the final audit event is missing. A crash after write has no outbox/reconciliation. The STRIDE model itself calls this unresolved ([threat model](../architecture/04-threat-model.md)).
- **Unbounded state:** `_records` grows for every proposal; neither proposals nor audit history have TTL eviction or a global cap. The reference reassembly manager likewise has no visible session cleanup. This is a memory-retention risk if reused in a long-lived process.
- **Freshness nuance:** policy and reviewer scopes are rechecked, and record version is checked sequentially. There is no atomic transaction spanning policy decision, state consume, version comparison, CRM write, and audit.
- **API boundary:** `issue_ticket` returns a ticket only for `allow`; it propagates `deny` and `refer`, and `use_ticket` re-evaluates current authority and propagates a new `refer`. The CRM workflow does not call the ticket API: it uses its own proposal binding, expiry, status, and human-review checks. Treat tickets as a separate reference example, not as the workflow's authorization contract; mutation checks now exercise both paths independently ([authority policy](../04-reference-implementation/authority_policy.py), [referral tests](../tests/test_authority_referral.py), [workflow](../prototypes/crm_operational_copilot/approval_workflow.py)).
- **Complexity:** proposal/status lookup is expected $O(1)$ by dictionary key; authority evaluation scans applicable rules, $O(R)$; record updates are constant-time for the fixed mock shape. Retained workflow memory is $O(P)$ proposals plus whatever the audit sink retains. Correctness risk is dominated by non-atomic state transitions, not algorithmic complexity.

## 3. Re-Scoring

**Scoring rubric:** Handbook fit asks how well this serves the stated research-handbook purpose (clarity, inspectability, reproducibility, and honest scope), not product readiness. Portfolio design quality rates the quality and completeness of architecture artifacts. Portfolio evidence strength rates validation: local tested examples are meaningful but do not equal customer or production validation. Scores are not capped; design quality and evidence maturity are not collapsed into one number. For handbook fit and design, 1 means absent or misleading, 2 fragmented, 3 coherent but with major gaps, 4 strong and traceable within scope with bounded gaps, and 5 independently reviewed and validated end to end. For evidence, 1 means claims are largely unsupported, 2 means local examples/tests, 3 means repeatable local measurements and broad tests, 4 means representative external/pilot validation, and 5 means repeated production outcomes. A 3-to-4 change should mean the move from major gaps to strong, traceable work, not a small numeric improvement.

**Fact:** The old report's second score was “Hypothetical product readiness,” not portfolio fit, so it is not comparable. The old report also predates the architecture bundle. The prior portfolio columns below are retrospective rescores from the old report's described evidence under this rubric; they are not the old product-readiness scores and are **low confidence** because they were assigned after the fact. The handbook scores also shifted from 3 in five lenses in the first draft to 4 here; this sensitivity shows the scale is not yet calibrated over time. Treat all score differences as provisional judgments, not measured progress.

| Lens | Prior handbook, normalized | Current handbook | Prior portfolio design (retrospective, low confidence) | Current portfolio design | Prior evidence strength (retrospective, low confidence) | Current evidence strength | Change and single next action |
|---|---:|---:|---:|---:|---:|---:|---|
| Solution Architect | 4 | 4 | 3 | 4 | 3 | 3 | Architecture bundle makes target design skill more demonstrable; validate one bounded workflow with identity, conditional CRM write, audit recovery, and operations ownership. |
| Real-World Trends | 3 | 3 | 2 | 2 | 1 | 1 | No external source work was added; add a dated primary-source comparison and distinguish standards from vendor claims. |
| Presales | 4 | 4 | 3 | 4 | 1 | 1 | Cost/discovery artifacts improve workshop structure but not customer evidence; run discovery and record sourced answers and a baseline. |
| Forward Deployed | 4 | 4 | 2 | 3 | 2 | 2 | AWS candidate and discovery steps improve design, not deployment proof; run a non-production pilot with rollback, telemetry, and named incident ownership. |
| Mathematics | 4 | 4 | 3 | 3 | 3 | 3 | Sizing and local tests remain useful but browser data drift and no property/concurrency tests limit confidence; reconcile data and add representative property/concurrency tests. |
| Philosophy/Psychology | 3 | 4 | 2 | 3 | 2 | 2 | Referral/approval and privacy trade-offs are more concrete; test reviewer comprehension and workload with realistic cases. |

**Inference:** Under a consistent handbook-fit rubric, the new architecture bundle raises portfolio design quality in Solution Architect, Presales, Forward Deployed, and Philosophy/Psychology without increasing customer-evidence scores. The local approval simulation is evidence of tested local behavior, not authenticated or deployed workflow evidence. Trends remain low because current industry practice is unverified.

## 4. Remaining Architect-Portfolio Gaps, by Value

1. **Real deployment and customer contact/validation:** highest value. The AWS view is candidate mapping, not IaC or deployment; named customer contacts, pilot results, and customer validation are **not found in repo**. A bounded non-production pilot would test whether the design survives real identity, CRM, network, and audit boundaries.
2. **Runbook and operational ownership:** an operational runbook, incident procedure, on-call owner, deployment/rollback checklist, and recovery exercise are **not found in repo**. The deployment view lists failure behaviors but does not operationalize them.
3. **Cost model with sourced values:** a worksheet and equations exist ([cost model](../architecture/07-cost-model.md)); vendor prices, measured usage, reviewer time, failure rates, and cost-per-completed-task values remain TBD/not found in repo.
4. **Risk register:** STRIDE analysis exists, but a maintained register with likelihood, impact, treatment, owner component, due date, residual-risk acceptance, and test status is **not found in repo**.
5. **Discovery record:** a 20-question questionnaire exists ([discovery questionnaire](../architecture/09-discovery-questionnaire.md)); completed customer answers, evidence sources, decision owners, and agreed acceptance thresholds are not found in repo.

## 5. A 30-Minute Reviewer Path

The architecture index already proposes a 30-minute path; this version adds explicit time boxes and evidence checks ([architecture README](../architecture/README.md)).

1. **0-4 min:** Read [solution overview](../architecture/00-solution-overview.md). State the user, problem, desired control, in-scope workflow, and exclusions. Confirm the status is proposed.
2. **4-8 min:** Compare [C4 context](../architecture/diagrams/c4-context.mmd) and [containers](../architecture/diagrams/c4-containers.mmd) with [container notes](../architecture/01-context-and-containers.md). Follow one read and one write/reviewer path; note the reviewer boundary difference.
3. **8-13 min:** Read [options analysis](../architecture/03-options-analysis.md) and all three [ADRs](../architecture/02-decisions/README.md). Identify the conditional choice, rejected options, and what evidence would reopen each decision.
4. **13-19 min:** Scan [STRIDE](../architecture/04-threat-model.md). For prompt injection, confused deputy, approval race/replay, and audit failure, ask: which component implements the control, which test proves it, and who accepts residual risk?
5. **19-23 min:** Check [NFR sizing](../architecture/05-nfr-and-sizing.md) arithmetic and the TBDs in [cost model](../architecture/07-cost-model.md). Treat all numeric workload values as illustrative.
6. **23-28 min:** Read [approval workflow](../prototypes/crm_operational_copilot/approval_workflow.py) and [focused tests](../prototypes/crm_operational_copilot/test_approval_workflow.py). Run the focused tests, then identify caller-supplied identity, state bounds, concurrency, and audit failure gaps.
7. **28-30 min:** Read [CRM evidence](../prototypes/crm_operational_copilot/EVIDENCE.md) and the [discovery questionnaire](../architecture/09-discovery-questionnaire.md). List what must be validated with a customer before calling this deployable.

## 6. Open Questions

1. Which single CRM workflow and customer environment should anchor a real pilot, and who is the customer-side decision/contact owner?
2. What identity-to-scope and reviewer role model must be enforced, including two-person approval and step-up requirements?
3. Does the target CRM support conditional writes/version tokens and idempotency, and what is the behavior after an unknown write outcome?
4. Which audit events must be durable before/after a write, what is the acceptable fail-closed behavior, and who owns reconciliation?
5. What user/data classification, model-provider terms, regions, retention, deletion, and legal-hold requirements apply?
6. Which success metric matters most: completion time, first useful content, reviewer effort, error/rework rate, or fully loaded cost?
7. Which deployment environment and operating team are realistic, and what runbook/on-call responsibilities are required?
8. Which dated standards and primary sources should define the trends review? Current external practice is **unverified** here.
9. Who owns the architecture decisions, risk acceptances, CI matrix, and ongoing evidence updates?

## Final State

The final tagged tree passed 127 tests, Ruff, whole-repository mypy, both evidence-consistency guards, and tracked Markdown link validation under isolated CPython 3.10.20. The detailed per-commit results, link/CSV audits, import provenance, mutation and coverage data, and browser provenance are in the [review evidence log](review-evidence-2026-10-04.md). Hosted Ubuntu CI is pending. Customer/cloud/production validation, representative CRM payloads, client decompression cost, independent mutation evidence, concurrency tests, and a second browser engine remain open.