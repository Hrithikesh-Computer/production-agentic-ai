# Cost and Performance Evidence Plan: Document 08

Source: `01-agent-architecture/08-sales-intelligence-knowledge-graph-copilot.md`. The document is conceptual; the repository has no Neo4j database, graph dataset, vector index, or deployed model. Public prices below are from the official Neo4j pricing page checked 2026-10-01 and are list-price references, not deployment estimates.

## Cost drivers and public pricing

| Cost driver | Public pricing evidence | Workload-specific inputs still required |
|---|---|---|
| Managed graph database | Neo4j's official [Neo4j pricing page](https://neo4j.com/pricing/) lists AuraDB Professional starting at `$0.09/GB/hour` with a 1 GB minimum instance and Business Critical starting at `$0.20/GB/hour` with a 2 GB minimum instance. Free is for learning/exploration. The page notes plan and feature differences; rates/features can change. Virtual Dedicated Cloud and self-managed Enterprise are contact-sales/contract paths rather than a public fixed rate. | Cloud/region, tier, provisioned memory, hours running/paused, high availability, backup/retention needs, support, marketplace agreement, taxes/discounts, and node/relationship/storage profile. Confirm selected-region price in the Neo4j console/calculator. |
| Model reasoning | The article names an LLM but not a provider/model. | Model, input/output tokens, cache, region, deployment mode, call count, retry rate. `EVIDENCE REQUIRED: chosen model and official applicable pricing`. |
| Embeddings and vector retrieval | The design includes vector retrieval/context memory but names no embedding model or vector service. | Embedding rate, tokens/doc, refresh rate, vector index location and capacity, query volume. `EVIDENCE REQUIRED: chosen service/model and official pricing`. |
| Graph data science / algorithms | Graph analytics may be used, but no algorithm, deployment, or managed/self-hosted product is selected. Neo4j pricing page describes Aura Graph Analytics separately with consumption pricing; it is not automatically included in AuraDB. | Whether needed, product, GB-hours/algorithm consumption, data transfer, and contract. `EVIDENCE REQUIRED: selected analytics product and current price`. |
| Ingestion and application hosting | No ingestion pipeline, API, or hosting platform is selected. | Data source connectors, refresh cadence, app compute, storage, egress/network, secrets, and operations. `EVIDENCE REQUIRED: deployment bill of materials`. |
| Observability and audit | No log/metrics vendor or retention plan is named. | Trace/log volume, retention, query, export, and security controls. `EVIDENCE REQUIRED: selected monitoring service and official pricing`. |

Prices are snapshots from the public page on 2026-10-01. Neo4j says features/pricing are subject to change; region and marketplace/contract pricing may differ. Validate the actual quote for the selected cloud and region before using any rate in a business case.

## Back-of-envelope cost formula

For a managed AuraDB instance priced by provisioned GB-hours:

$$
C_{graph} = \max(GB_{provisioned}, GB_{minimum}) \times H_{billable} \times R_{tier,region} + C_{optional	ext{-}services}
$$

The pricing page's current starting references are `$0.09/GB-hour` for AuraDB Professional (minimum 1 GB) and `$0.20/GB-hour` for AuraDB Business Critical (minimum 2 GB). The formula is not a total estimate: actual sizing/tier/region/idle-pause semantics and any commercial terms must be verified.

$$
C_{month} = C_{graph} + C_{model} + C_{embedding/vector} + C_{ingestion} + C_{application/network} + C_{audit/monitoring} + C_{support}
$$

The graph-agent total cannot be calculated from this repository because its schema, graph size, selected products, query rate, and model are not defined.

## Performance measurement plan

1. Establish a versioned graph schema, representative account/contact/opportunity dataset, relationship-degree distribution, data freshness, and a fixed labeled question/query set. Record node/edge counts, properties/indexes, hardware/tier, region, and cache state.
2. For each query class, record traversal depth and branching/fan-out at each hop. Sweep explicitly defined depths from the supported minimum to the product-approved maximum, and report result count and execution plan; do not treat deeper traversal as automatically better.
3. Measure p50, p95, and p99 for graph query execution, vector retrieval, fusion, model reasoning, and end-to-end response. Capture time to first useful result if streaming is part of the eventual design. Run cold/warm cache and concurrency tests; record timeouts, retries, result truncation, and resource consumption.
4. Evaluate answer/retrieval quality against labeled ground truth: relevant-node/edge recall@k and precision@k, path correctness, citation/provenance correctness, and recommendation support rate. Report by question type and traversal depth, with denominators.
5. Compare a graph-only baseline, graph-plus-vector retrieval, and any alternative retrieval path using the same dataset, query set, tier, and model. Attribute cost by correlating query logs, model usage, graph capacity, and trace IDs.
6. Have the owner set maximum acceptable traversal depth, latency, and quality thresholds from actual use cases before testing. This article and repository provide no measured graph performance or SLA.

## Evidence required

- `EVIDENCE REQUIRED: target cloud provider/region, AuraDB tier, and contracted price`.
- `EVIDENCE REQUIRED: graph schema, node/edge counts, degree distribution, data growth, and refresh rate`.
- `EVIDENCE REQUIRED: actual traversal query set, approved depth/fan-out limits, and labeled relevance ground truth`.
- `EVIDENCE REQUIRED: model, embedding/vector products, and their current official price sheets`.
- `EVIDENCE REQUIRED: reproducible p50/p95/p99 traces, query plans, hardware/tier configuration, and cost per accepted task`.
