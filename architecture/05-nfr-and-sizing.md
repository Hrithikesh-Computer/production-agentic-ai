# Non-Functional Requirements and Sizing

**Status:** Discovery worksheet with an illustrative pilot envelope. Numeric values below are assumptions for calculation only, not customer requirements, commitments, or measured capacity.

## Candidate NFRs to agree with the customer

| Attribute | Discussion target | Measurement / acceptance method | Decision owner |
|---|---|---|---|
| Availability | Candidate pilot objective: 99.5% monthly for read interactions. Write execution must fail closed when current authorization or approval state cannot be verified. | Synthetic checks; dependency and user-visible availability separated; report maintenance and provider exclusions explicitly. | Product and SRE |
| User latency | Candidate: p95 complete read response <= 8 s; first useful result <= 3 s only if streaming is selected. Human approval time is excluded and reported separately. | End-to-end traces with model, CRM, and client timestamps; representative payload and network. | Product |
| Authorization latency | Candidate: p95 policy decision <= 200 ms within the application region. | Load test against policy service at expected peak and failover. | Security/platform |
| Throughput | Size initially from the example envelope below; confirm burst and sustained rates from CRM and user data. | Concurrent load test including CRM, model, policy, and audit dependencies. | Customer product owner / SRE |
| Approval workflow | No write without a current, action-bound approval. Queue age and stale/rejected proposals visible to operators. | Concurrency, duplicate submission, record-change, expiry, and reviewer workflow tests. | Business control owner |
| Audit | Record every authorization decision, proposal, reviewer decision, tool call, and result with correlation IDs. Retention, deletion, legal hold, and tamper-evidence are customer-defined. | Reconcile successful CRM mutations against audit records; inject audit failures and verify recovery behavior. | Compliance / data owner |
| Data protection | Minimize CRM data sent to the model; encrypt in transit/at rest; redact secrets and unnecessary personal data. Provider region, retention, and training use require contract review. | Data-flow review, provider configuration audit, redaction tests, access review. | Privacy/security |
| Recovery | RTO, RPO, queue recovery, replay, and CRM reconciliation objectives are TBD. | Failure-injection and restore exercise after target architecture is selected. | SRE / CRM owner |
| Compliance | No certification or regulatory mapping is assumed. Select controls from the customer's actual data classification and obligations. | Customer control mapping and evidence review. | Compliance |

These candidate targets are deliberately negotiable. They should be replaced after workflow, user, data, dependency, and business-impact discovery.

## Illustrative sizing envelope

The following numbers are made-up planning inputs to demonstrate sizing arithmetic, not measured CRM usage:

- 100 enabled users.
- 2 tasks per user per hour on average.
- Peak factor 4 over average.
- 5 CRM operations per task.
- 8,000 model input tokens and 1,500 output tokens per task.
- 250 KB of serialized CRM/response data per task.
- 12 audit events per task, averaging 2 KB each.

Derived planning rates:

| Quantity | Calculation | Illustrative result |
|---|---|---:|
| Average task rate | 100 users x 2 tasks/hour / 3,600 | 0.056 tasks/s |
| Peak task rate | Average x 4, rounded for planning | 0.25 tasks/s |
| Peak CRM operations | 0.25 tasks/s x 5 operations/task | 1.25 operations/s |
| Peak model input | 0.25 x 8,000 tokens | 2,000 input tokens/s |
| Peak model output | 0.25 x 1,500 tokens | 375 output tokens/s |
| Peak serialized data | 0.25 x 250 KB | 62.5 KB/s; about 5.4 GB/day if peak were sustained continuously |
| Peak audit writes | 0.25 x 12 events/s | 3 events/s, about 518 MB/day at 2 KB/event if peak were sustained continuously |
| In-flight tasks at 6 s p95 | 0.25 tasks/s x 6 s (Little's Law planning approximation) | 1.5, so test at least 2 concurrent tasks before adding headroom |

The daily volume figures intentionally multiply the peak rate by a full day and therefore are conservative upper-envelope arithmetic, not expected daily traffic. Add customer-observed burst shape, retries, model/provider tokenization, response compression, and audit indexes before making a capacity or price estimate.

## Session and memory sizing

Use measured values, not model-context token counts alone:

`resident session memory ~= active sessions x (buffered payload + parsed objects + queue/audit metadata) x implementation overhead factor`

The reference `Reassembler` limits an individual message to 10,000 chunks and 16,000,000 payload bytes by default, but the manager's session dictionary has no global session-count bound or cleanup path ([reassembler](../04-reference-implementation/adaptive-response-filter/reassembler.py)). At the individual payload cap, 100 simultaneously incomplete sessions could retain up to 1.6 GB of raw payload bytes alone before Python object, dictionary, and duplicate-representation overhead. This is a deliberately pessimistic upper bound and a reason to add expiry, quotas, and memory/load tests before any long-running reuse.

For an implementation, measure RSS and allocation peak with representative serialized payloads, parsed CRM objects, concurrent approvals, and failure/retry conditions. Set per-request byte/token caps, per-user and per-tenant concurrency, global queue limits, and session TTL based on those results.

## Cost model inputs (not priced here)

Per-task variable cost should be modeled as model input/output tokens plus CRM/API calls, compute duration, logging/storage volume, and reviewer minutes. A simple workload expression is:

`monthly cost ~= tasks x (input_tokens x input_rate + output_tokens x output_rate + CRM_calls x call_cost + compute_cost + audit_storage_cost + reviewer_minutes x labor_rate) + fixed platform cost`

Prices, provider selection, token rates, reviewer labor, failure cost, and task volumes are not found in repo. Do not turn this worksheet into a quote until sourced from the customer and selected vendors.
