# Cost Model: CRM Operations Copilot

**Status:** Costing worksheet; no vendor prices, measured usage, or customer volumes are assumed. Do not use the example as a quote or savings claim.

## Cost boundary

Model the cost of one completed workflow and its monthly volume separately. The workflow has four independently variable cost areas:

1. Model input/output tokens and any repeated calls.
2. Application, authority, approval, CRM connector, queue, and network infrastructure.
3. Audit and diagnostic storage, retention, query, and export.
4. Human review time and operating/support labor.

Include failure and rework explicitly. A rejected proposal, model retry, CRM timeout with unknown outcome, or stale-record resubmission may consume tokens, API calls, compute, and reviewer time without producing a completed task.

## Formula

For a billing period:

`Total = fixed_platform + N * (C_model + C_CRM + C_compute + C_storage + C_review + C_failure)`

Where:

- `N` is attempted tasks in the period, not only successful tasks.
- `C_model = input_tokens / 1,000,000 * input_price_per_million + output_tokens / 1,000,000 * output_price_per_million`, summed across calls and retries.
- `C_CRM = CRM_API_calls * price_per_call` when the CRM meters calls; otherwise capture the allocated license/integration cost separately.
- `C_compute = vCPU_seconds * vCPU_rate + memory_GB_seconds * memory_rate + request/egress charges` for the selected platform.
- `C_storage = audit_GB_written * storage_rate + retained_GB_months * retention_rate + query/export charges`.
- `C_review = review_minutes / 60 * loaded_reviewer_hourly_cost`.
- `C_failure = failure_probability * (rework_minutes / 60 * labor_rate + incident_cost_per_failure + duplicated upstream costs)`.

Do not add a failure penalty twice if rework is already included in task volume. Keep currency, region, discount tier, tax, commitment, and license allocation explicit.

## Per-task worksheet

| Input | Customer/vendor value | Evidence source | Notes |
|---|---:|---|---|
| Average input tokens per task | TBD | Provider usage export or representative trace | Include system prompt, retrieved CRM content, and prior turns if any. |
| Average output tokens per task | TBD | Provider usage export | Separate user answer from structured proposal payload. |
| Model calls per task | TBD | Instrumented workflow | Record retries, tool-planning turns, and fallback calls. |
| Input/output price per million tokens | TBD | Selected provider price sheet and contract | Capture model, region, date, tier, and cache pricing. |
| CRM operations per task | TBD | CRM API trace | Include reads, writes, status/version checks, and retries. |
| Compute seconds and memory per task | TBD | Load test on chosen deployment | Include idle capacity and autoscaling floor separately. |
| Audit bytes/events per task | TBD | Redacted event sample | Distinguish immutable/compliance retention from diagnostic logs. |
| Reviewer minutes per proposal | TBD | Timed user study / pilot | Include queue waiting time separately from active labor. |
| Approval/rejection/stale/failure rates | TBD | Pilot workflow events | Rates change both unit cost and realized value. |
| Cost of a failed or incorrect operation | TBD | Customer risk/incident model | Must be supplied by customer; repository has no loss data. |

## Monthly worksheet

| Quantity | Formula | Value |
|---|---|---:|
| Monthly task attempts | Active users x tasks/user/day x business days | TBD |
| Monthly model tokens | Task attempts x calls/task x tokens/call, split input/output | TBD |
| Monthly CRM operations | Task attempts x operations/task | TBD |
| Monthly review hours | Proposals x review minutes/proposal / 60 | TBD |
| Monthly audit volume | Task attempts x events/task x average bytes/event | TBD |
| Fixed platform cost | Minimum replicas + shared services + licenses | TBD |
| Variable service cost | Model + CRM + compute + storage + egress | TBD |
| Failure/rework cost | Failed attempts x measured rework and incident cost | TBD |
| Total monthly cost | Fixed + variable + human review + failure/rework | TBD |
| Cost per completed task | Total monthly cost / completed tasks | TBD |

## Comparison baseline and decision rule

Compare against the customer's current workflow for the same task cohort. Measure completion rate, time-to-completion, reviewer minutes, error/rework rate, and fully loaded cost. A lower model-token bill is not a benefit if it increases manual investigation or failure risk. Do not claim ROI until the pilot includes representative users, a baseline, agreed attribution, and a sufficient observation period.

## Evidence boundary

The repository contains an illustrative workload envelope in [NFR and sizing](05-nfr-and-sizing.md), not customer traffic, vendor pricing, reviewer timing, or failure-loss data. Local benchmark timings are not service costs. All numeric inputs remain **TBD** until sourced and dated.
