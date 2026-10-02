# Cost and Performance Evidence Plan: Document 07

Source: `01-agent-architecture/07-enterprise-audit-compliance-risk-copilot.md`. The article is conceptual; this repository has no Azure AI Search, model, SQL, or enterprise corpus deployment. Pricing below is public list-price evidence only, checked 2026-10-01. It is not a quote or an estimate of this hypothetical system.

## Cost drivers and public pricing

| Cost driver | Public pricing evidence | Workload-specific inputs still required |
|---|---|---|
| Azure AI Search / Foundry IQ capacity | Microsoft's [Azure AI Search (Foundry IQ) pricing page](https://azure.microsoft.com/en-us/pricing/details/search/) shows dedicated Search Unit monthly prices by capacity/tier. Its serverless preview lists compute at `$0.2712` per Compute Unit-hour and indexed storage at `$0.246` per GB-month, with regional pricing caveats; feature charges include agentic retrieval by tokens and semantic ranker by requests. Prices may vary by region and agreement. | Region, chosen tier/SKU, index count and size, replicas/partitions or CU consumption, feature enablement, query/indexing volume. No SKU is selected in the architecture. Confirm the live calculator price for the deployment region before estimating. |
| Model reasoning / embeddings | Microsoft's [Azure OpenAI pricing page](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) publishes model/deployment-specific token rates; standard on-demand is billed by input/output token usage, while provisioned throughput has a capacity/time billing model. Batch and data-zone/global/regional options differ. | Model, API, region/deployment type, input/output tokens, caching, batch eligibility, calls per request, retry rate, and provisioned-vs-on-demand decision. No model is specified by document 07. Therefore no model rate or model dollar total is selected here. |
| SQL / structured source | The article says “SQL / structured query layer” but names no database product or hosting configuration. | Product, service tier, compute/runtime, storage, query volume, egress, and licensing. `EVIDENCE REQUIRED: selected SQL platform and current official regional price sheet`. |
| Document storage and indexing pipeline | Enterprise corpora and indexing are mentioned, but no storage or ingestion product is selected. Azure AI Search page's index storage and indexing capacity pricing apply only if that service/tier is selected; source storage is separate. | Source storage provider, retained bytes, ingestion cadence, document cracking/enrichment, embedding/indexing token volume, refresh/deletion workload. `EVIDENCE REQUIRED: source/storage design and measured corpus profile`. |
| Audit and telemetry | No logging vendor or retention target is named. Azure Monitor pricing, if selected, is usage based; its [official pricing page](https://azure.microsoft.com/en-us/pricing/details/monitor/) publishes ingestion, retention, query, and export charges. | Event volume/size, table plan, retention, query and export rates, redaction, and audit durability. `EVIDENCE REQUIRED: selected logging service and retention policy`. |
| Network, application, and human review | Not priced in the article. | Application hosting, private endpoints/network transfer, identity, reviewer time, and support. `EVIDENCE REQUIRED: deployment topology, region, concurrency, and approval workflow`. |

Public rates are reported as published by the cited pages on 2026-10-01. The vendor pages state that prices vary and are estimates rather than binding quotations; verify current prices in the vendor pricing calculator for the customer's contract and deployment region.

## Back-of-envelope cost formula

Keep quantities symbolic until workload and region are selected:

$$
C_{month} = C_{search} + C_{model} + C_{sql} + C_{source} + C_{audit} + C_{app/network} + C_{review}
$$

For a hypothetical Azure AI Search serverless component only:

$$
C_{search} = (H_{CU} \times R_{CU,region}) + (GB_{index} \times R_{storage,region}) + C_{features}
$$

The cited pricing page currently lists serverless reference rates of `$0.2712/CU-hour` and `$0.246/GB-month`; use them only after confirming the applicable region, tier availability, and pricing date. Dedicated capacity instead requires `Search Units × unit rate × billed time`, with the selected tier's actual monthly unit price. `C_features` includes any enabled agentic retrieval, semantic ranking, entity lookup, or image extraction charges.

For model usage:

$$
C_{model} = \sum_{calls} (T_{input}R_{input,model,region} + T_{cached}R_{cached,model,region} + T_{output}R_{output,model,region}) + C_{provisioned/batch/tools}
$$

No overall cost estimate is supportable until the variables above and the SQL/source/audit products are chosen.

## Performance measurement plan

1. Freeze a representative corpus, metadata/schema, source snapshot, access policy, query set, and relevance ground truth. Record document count/bytes, structured-table size, index configuration, region, model, embedding model, and software/configuration versions.
2. Compare keyword/metadata retrieval, vector retrieval, hybrid fusion, and SQL query paths independently, then evaluate the full user-question-to-cited-answer path. Hold the model and prompt constant when isolating retrieval changes.
3. Measure end-to-end and per-stage latency: query parsing, each retrieval source, fusion/reranking, SQL execution, model time-to-first-token and completion, citation validation, and human-review wait separately. Report p50, p95, and p99 from timestamped individual requests; include warm/cold behavior, concurrency, failures, timeouts, and retries.
4. Measure retrieval quality against judged relevant source records using recall@k, precision@k, MRR or nDCG@k, citation correctness, and answer support/unsupported-claim rate. Report denominators, query mix, and confidence intervals; do not infer accuracy from latency.
5. Measure cost per query and per accepted task by joining service meters/tokens/storage with the same trace IDs and workload denominator. Include indexing/reindexing and idle capacity.
6. Define workload-specific acceptance thresholds with the product owner before the experiment. This document supplies no target latency or accuracy numbers because the repository contains no customer workload or SLA.

## Evidence required

- `EVIDENCE REQUIRED: selected Azure AI Search tier/region and Azure OpenAI model/deployment`.
- `EVIDENCE REQUIRED: source corpus and SQL product, corpus size, ingestion cadence, request volume, concurrency, and retention`.
- `EVIDENCE REQUIRED: customer agreement/discounts and calculator export for the selected Azure region`.
- `EVIDENCE REQUIRED: labeled retrieval benchmark set and reproducible per-request latency/cost traces`.
- `EVIDENCE REQUIRED: reviewer labor and production audit-retention requirements`.
