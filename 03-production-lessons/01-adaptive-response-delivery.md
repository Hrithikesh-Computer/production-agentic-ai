# The Last Mile of LLM Serving: When Response Delivery Becomes the Bottleneck in Agentic AI

> Production Engineering • Agentic AI • System Design • LLM Serving

**Reading time:** ~14 minutes
**Difficulty:** Advanced
**Category:** Production Engineering
**Status:** Production Case Study

> **Note:** This article abstracts an engineering investigation performed while building a production AI application. Architecture, benchmarks, payload shapes, and implementation details have been simplified and generalized to preserve the reasoning while avoiding exposure of proprietary specifics. Numbers labeled "illustrative" come from a local proxy benchmark, not a production deployment. This is an engineering narrative, not a formal experimental study or a claim of novel research.

## Executive Summary

Most work on LLM serving optimizes inference: GPU scheduling, KV-cache management, batching, speculative decoding, attention kernels. But production systems don't end when the model finishes generating tokens — users experience the entire serving pipeline, from serialization and transport through browser parsing and rendering.

This article investigates a bottleneck that appeared *after* inference had already completed: response delivery. In this system, large structured responses delayed the moment users saw any progress, independent of how fast the model ran. The fix was a delivery layer that exposes content progressively, built to fit inside the existing HTTP request-response contract rather than requiring a transport migration.

**Key takeaways**

- In this system, the observed latency appeared primarily in response delivery, not model inference.
- Splitting large payloads improved time-to-first-visible-content without touching inference time.
- The delivery layer preserved the existing HTTP contract instead of requiring a transport migration.
- The team favored incremental rollout over a full redesign, given the constraints described below.

**What this is not:** a new transport protocol, a replacement for SSE/WebSockets, a universal optimization (see Limitations), or a formal experimental study — no statistical significance testing or multi-system evaluation was performed.

**The evidence, illustrative:** the stage breakdown below is representative of the kind of split observed in this system's proxy benchmark, not a captured production trace.

| Stage | Time |
|---|---|
| Model generation | 780 ms |
| Serialization | 35 ms |
| Network | 120 ms |
| Browser parse/render | 1.7 s |

In the representative case shown, generation finished quickly, but the user-visible delay spanned the full delivery and rendering pipeline. This example illustrates the kind of split observed, not a precise production measurement.

## Where This Fits in the LLM Serving Stack

| Layer | Concern | Example |
|---|---|---|
| GPU scheduling | Batching and request scheduling on the GPU | Sarathi-Serve |
| KV cache management | Memory-efficient attention state | vLLM |
| Attention computation | IO-aware attention kernels | FlashAttention |
| Token-level serving | Structured generation execution | SGLang |
| **Response delivery** | **Getting a finished (or partially finished) response to the user quickly** | **This work** |

Prior systems in the rows above optimize inference throughput, GPU utilization, and memory efficiency. This work starts *after* generation completes — none of those optimizations help if a fully-generated response still sits behind a slow, single-block delivery path. That's the last mile this article is about.

## The Production Problem

Requests with large responses felt slower and less reliable than smaller ones, even when the backend had already produced most of the useful content. Two requests sharing the same model, backend path, and infrastructure — but different payload sizes — produced very different perceived latency, despite comparable model steps.

The same response was generated two ways: once as a single large payload, once as two smaller parts delivered sequentially. The second form reduced time-to-first-visible-content with zero change to inference time, which redirected the investigation from generation time to delivery behavior.

```mermaid
flowchart LR
    Browser --> Gateway
    Gateway --> Backend
    Backend --> Serializer
    Serializer --> HTTPWriter[HTTP Writer]
    HTTPWriter --> BrowserParse[Browser Parse]
    BrowserParse --> DOMPaint[DOM Paint]
```

**Why browser rendering can become the bottleneck:** browser work doesn't scale linearly with payload size like network transfer does. After bytes arrive, the browser must parse JSON, allocate objects, update application state, schedule layout, and paint the DOM. Large payloads significantly increase main-thread work — a pattern observed consistently when comparing small vs. large responses in local benchmarks.

### Root cause chain

```text
Generation completes
        │
        ▼
Response serialized as one object
        │
        ▼
Entire payload buffered before sending
        │
        ▼
Browser receives one large payload
        │
        ▼
JSON parsing blocks the main thread
        │
        ▼
DOM update delayed until parsing finishes
        │
        ▼
User perceives latency, even though generation finished earlier
```

The fix targets the third step — "entire payload buffered before sending" — not generation, not the network, and not the browser's parser itself.

## Latency Decomposition

Total latency can be decomposed as:

```
L = Tg + Ts + Tn + Tp + Tr
```

`Tg` generation, `Ts` serialization, `Tn` network transfer, `Tp` browser parse, `Tr` render/paint. But what a user actually perceives isn't `L` — it's closer to:

```
Perceived latency = TTFB + time until first renderable chunk + browser render
```

The instinct is to optimize `Tg`. The metric that governs perceived responsiveness is *time to first visible content*. The delivery layer's job is to shrink that term without necessarily shrinking `L` — optimizing when progress becomes visible rather than when the whole response finishes.

> **Engineering principle:** Before redesigning a production system, decompose end-to-end latency into measurable stages, then optimize the dominant term — not the most visible subsystem.

## Investigation

| Observation | Hypothesis | Result |
|---|---|---|
| Backend timing looked ordinary even on the worst-perceived requests | Generation (LLM) is the bottleneck | ❌ Rejected |
| No meaningful correlation between data-access latency and the symptom | Database is the bottleneck | ❌ Rejected |
| Explained some cases but not the consistent effect tied to payload shape | Network is the bottleneck | ⚠️ Partial |
| Splitting a response with no change to total work still improved perceived latency | Delivery semantics are the bottleneck | ✅ Accepted |

```mermaid
flowchart LR
    D1["Day 1 — Symptom reported, sizes compared"] --> D2["Day 2 — Backend timing ruled ordinary"]
    D2 --> D4["Day 4 — Split-payload experiment run"]
    D4 --> W2["Week 2 — Alternatives compared, delivery layer adopted"]
```

More server capacity, compression, or waiting for network improvements target the wrong term in the equation above — they shrink `Tn` or reduce tail variance (Dean & Barroso, 2013; Crankshaw et al., 2017) without moving *time to first visible content* earlier. Pagination changes the interaction model instead. Streaming without a reconstruction contract improves continuity but introduces ambiguity around incomplete states.

## Controlled Experiments

**Experiment A — controlled split test.** The same response was generated once as a single payload and once as two sequential parts, holding backend, infrastructure, model, and browser constant. The two-part version consistently showed visible content sooner, which suggested that delivery semantics rather than inference dominated the user-visible delay.

*Illustrative example:* In local testing, a single large payload (250 KB) showed visible content significantly later than the same content split into two smaller parts. This pattern held across multiple runs, suggesting that chunking improves time-to-first-content independent of total work.

**Experiment B — payload scaling.**

*Illustrative representative values (local proxy benchmark, not production measurements):*

| Response size | TTFB | TTLB | Browser parse | Render | Total UX delay |
|---|---|---|---|---|---|
| 10 KB | 120 ms | 140 ms | 20 ms | 25 ms | 145 ms |
| 40 KB | 128 ms | 155 ms | 24 ms | 40 ms | 195 ms |
| 100 KB | 135 ms | 170 ms | 60 ms | 180 ms | 350 ms |
| 250 KB | 142 ms | 190 ms | 90 ms | 1.1 s | 1.3 s |
| *Std deviation (σ), illustrative* | *±8 ms* | *±12 ms* | *±5 ms* | *±15 ms* | *±45 ms* |

**Experiment C — network degradation.** The same response shapes were replayed over a degraded connection, since the production symptom appeared worse under jitter.

**Experiment D — architecture comparison.** Full-buffer baseline vs. compression, pagination, structured streaming, and the eventual delivery layer.

**Benchmark setup (illustrative, not production):** 20 warmup requests (discarded), 50 measured requests per scenario, median and P95 reported, Chrome 138, HTTP/1.1, local proxy host, 250 KB structured JSON payload. These are representative values to ground the discussion; full details are in Appendix E.

## Production Constraints

Browser-based client on existing HTTP request-response semantics, no assumed migration to WebSockets, backward-compatible API contract, incremental low-risk rollout, full observability. These constraints deferred WebSockets, Kafka, a gRPC migration, HTTP/3 migration, a frontend rewrite, and a server redesign — not because they were bad ideas, but because they were more change than the observed problem justified.

## Alternatives Considered

| Approach | Complexity | UX | Compatibility | Latency improvement | Operational risk |
|---|---|---|---|---|---|
| Full response buffering | Low | Low | High | Low | Low |
| Compression | Low | Medium | High | Medium | Low |
| Pagination | Medium | Medium | High | Medium | Medium |
| HTTP streaming | Medium | Medium | Medium | High | Medium |
| SSE / WebSockets | High | High | Low | High | High |
| Adaptive response delivery | Medium | High | High | High | Medium |

**Why not streaming?** The existing product shared a request-response contract across multiple clients. Full streaming support would have meant protocol changes across frontend, gateway, and API layers — more compatibility risk than this bottleneck justified.

**Why not token streaming?** Token streaming exposes model output as tokens are generated, which helps conversational UX but doesn't address reconstruction of a large, nested, non-text payload. The bottleneck here sat between generation completion and visible progress — a different layer than earliest token emission.

## Architecture Decision Record

```text
Decision:
  Introduce a response delivery layer between the response builder
  and the HTTP response writer.

Status:
  Accepted

Context:
  Large structured payloads delayed first visible content, independent
  of model inference time.

Alternatives considered:
  Compression, Pagination, HTTP streaming, SSE, WebSockets

Rejected because:
  Each either failed to move first-visible-content earlier (compression,
  more server capacity) or required more transport/protocol change than
  the bottleneck justified (streaming, SSE, WebSockets).

Accepted because:
  Preserves the existing HTTP contract, deploys at a single boundary,
  and measurably improves perceived latency with a bounded rollout risk.

Consequences:
  + Faster time to first visible content
  + Small, boundary-scoped deployment
  - Client-side reconstruction logic required
  - Additional delivery-layer failure modes to manage
```

## Delivery Layer Design

```
if payload is small:      return it normally
if payload is large:      split into structured chunks
if response is UI/tool-heavy: expose partial content earlier
if payload has nested objects or long text: favor chunk boundaries that preserve semantic coherence
if the client can't safely reassemble state: fall back to the full-buffer path
```

**Threshold justification:** the initial threshold was chosen empirically by plotting payload size against browser render time in local testing. Render cost stayed relatively flat below ~100–120 KB and increased more steeply beyond that point. The first deployed threshold was set conservatively at 128 KB and later made configurable based on observed characteristics of real payloads.

## Chunk Boundary Algorithm

Boundary strategies are tried in priority order, falling through to the next only when the current strategy can't produce chunks under the size limit:

```text
for strategy in [json_boundary, tool_boundary, heading, paragraph, sentence]:
    chunks = strategy(payload)
    if chunks satisfy threshold:
        return chunks
return fixed_size(payload)
```

The reference implementation (`chunker.py`) demonstrates the JSON-boundary and fixed-size-fallback strategies. The middle strategies (tool_boundary, heading, paragraph, sentence) follow the same pattern and would be added in a production chunker that walks the full object graph.

| Component | Complexity |
|---|---|
| Splitting | O(n) |
| Reassembly | O(n) |
| Ordering (buffer + sort) | O(k log k) |
| Memory | O(payload size) |

(`n` = payload size in bytes, `k` = chunk count.)

## Architecture

**Before:**

```mermaid
flowchart LR
    LLM --> Serializer1[Serializer]
    Serializer1 --> HTTP1[HTTP — full buffer]
    HTTP1 --> Browser1[Browser]
    Browser1 --> Render1["Render (blocked until fully parsed)"]
```

**After:**

```mermaid
flowchart LR
    LLM --> Builder[Response Builder]
    Builder --> Serializer
    Serializer --> Policy[Delivery Policy]
    Policy --> Writer[Chunk Writer]
    Writer --> Gateway
    Gateway --> Browser
    Browser --> Render2[Incremental Rendering]
    Metrics[Metrics / Tracing] -.-> Policy
    Metrics -.-> Writer
```

The backend logic that produces the response is unchanged in both diagrams — only the boundary between the response builder and the browser changed.

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant Bk as Backend
    participant R as Response Builder
    participant D as Delivery Layer

    B->>G: Request
    G->>Bk: Prompt
    Bk->>R: Produce response
    R->>D: Serialized payload
    D->>B: Chunk 1
    D->>B: Chunk 2
    D->>B: Final chunk
    B->>B: Reassemble and render
```

Additional diagrams (client state machine, trace timeline, rollout stages) are in the appendices to keep the main article to one architecture diagram and one sequence diagram.

### Reference implementation

```text
reference/
  adaptive-response-delivery/
    policy.py, chunker.py, filter.py, reassembler.py, metrics.py, middleware.py
    client_reassembler.ts
    tests/test_chunker.py, tests/test_reassembler.py
```

Each chunk carries a reconstruction contract: `sequence`, `total_chunks`, `checksum`, `is_final`, `payload`. The client only exposes completed structures to the UI; missing chunks stay buffered until retransmission or timeout. See Appendix C for the reassembly algorithm and Appendix D for the client state machine.

### Design principles

- Don't change the transport.
- Don't require client changes beyond opting into the chunked contract.
- Preserve the existing API contract.
- Keep the rollout reversible at every stage.
- Measure before optimizing, and keep measuring after.

## Observability

```text
payload_size, chunk_count, avg_chunk_size, serialization_ms
TTFB, TTLB, p50_first_visible, p95_first_visible, reassembly_ms
json_parse_ms, render_block_ms, main_thread_block_ms, paint_ms
chunk_retries, reassembly_failures, duplicate_chunks, out_of_order_chunks, fallback_rate
```

The frontend-side metrics (`json_parse_ms`, `render_block_ms`, `main_thread_block_ms`, `paint_ms`) matter as much as the backend ones — they're what actually confirmed the "why browser rendering hurts" explanation above rather than leaving it as a hypothesis.

## Representative Impact

*The following values are from local proxy benchmarks to illustrate the kind of improvement observed. They are not production measurements and should not be reproduced without similar controlled conditions.*

| Approach | First visible (P50) | First visible (P95) | TTLB | Browser render |
|---|---|---|---|---|
| Full buffering | ~2.4 s | ~3.1 s | ~2.8 s | ~1.1 s |
| Adaptive response delivery | ~480 ms | ~720 ms | ~2.9 s | ~320 ms |

The key observation is that chunking moves time-to-first-visible-content much earlier without increasing total transfer time. Recovery metrics (chunk retransmission, fallback rates) are tracked in production but vary significantly by network conditions and are intentionally omitted here to avoid suggesting false precision.

## Trade-offs and Limitations

Faster first visible content, but more delivery-layer complexity and a partial-completion contract the client must honor. Limited value when responses are already small, generation dominates latency, clients already support SSE/WebSockets, or payloads are mostly binary.

**Threats to validity:** single production architecture, one browser, one transport version. Results may differ under HTTP/2 or HTTP/3, other browsers or mobile clients, high packet loss, or GPU clusters with different scheduling behavior.

**When not to use this:**

- Responses are already small — the threshold logic just adds overhead for no benefit.
- SSE or WebSockets are already available and the client already handles them.
- Payloads are mostly binary rather than structured JSON/text.
- Inference genuinely dominates end-to-end latency, so delivery isn't the bottleneck to begin with.
- Clients can't safely buffer and reassemble partial state.

## Rollout Strategy

```mermaid
flowchart LR
    Canary["Canary — 5%"] --> Observe1[Observe]
    Observe1 --> Expand1["Expand — 25%"]
    Expand1 --> Observe2[Observe]
    Observe2 --> Full["Full rollout — 100%"]
```

At each stage: P50/P95 first-visible-content, client error rate, fallback rate, and duplicate/out-of-order chunk rate were checked before expanding further.

## Related Work

vLLM, Sarathi-Serve, Orca, and FlashAttention optimize inference throughput, GPU utilization, and memory efficiency — the layers above the response-delivery row in the stack table earlier. This work operates after generation completes, addressing the latency between response construction and browser rendering. These problem spaces are complementary: a system can benefit from both inference optimization and delivery optimization.

| Work | Optimizes | Layer |
|---|---|---|
| FlashAttention | Attention kernels | GPU |
| vLLM | KV cache | Serving |
| Orca | Request scheduling | Serving |
| Sarathi-Serve | Batching | Serving |
| **This work** | Response delivery | Client / HTTP |

## Future Work

- Adaptive chunk sizing based on payload shape
- Incremental JSON parsing on the client
- HTTP/3 evaluation

## Engineering Lessons

- Production bottlenecks are often outside the component initially blamed.
- Perceived latency often matters more than total latency.
- Delivery contracts deserve the same design attention as generation algorithms.

Modern LLM serving research has dramatically improved how quickly models generate tokens. Production systems, however, are judged by something different: how quickly users perceive progress. Between those two lies the delivery path. For browser-facing agentic systems with large structured responses, that path can become a significant bottleneck — and in some cases, a high-leverage place to optimize.

## Appendix A — Example Payload

```json
{
  "plan": { "steps": ["retrieve", "summarize", "cite"] },
  "tool_output": { "result": "..." },
  "citations": [{ "source": "doc-1", "span": [0, 120] }],
  "metadata": { "model": "example", "latency_ms": 812 }
}
```

## Appendix B — Chunk Metadata

```json
{
  "sequence": 0,
  "total_chunks": 3,
  "checksum": "9a3f1c02",
  "is_final": false,
  "payload": "..."
}
```

## Appendix C — Reassembly Algorithm

1. Buffer incoming chunks keyed by `sequence`.
2. Verify each chunk's `checksum` on arrival; reject and request resend on mismatch.
3. Track `total_chunks` from the first chunk received.
4. Once `len(buffered) == total_chunks`, merge in sequence order.
5. Only expose the merged, validated structure to the UI — never a partial merge.

See `reassembler.py`'s `Reassembler` class for a runnable, tested version.

## Appendix D — Client State Machine and Failure Modes

```mermaid
stateDiagram-v2
    [*] --> Waiting
    Waiting --> Receiving: chunk arrives
    Receiving --> Receiving: more chunks arrive
    Receiving --> Complete: total_chunks reached
    Receiving --> Timeout: no chunk within timeout
    Timeout --> Retry: request resend
    Retry --> Receiving
    Complete --> Render
    Render --> [*]
```

| Failure | Symptom | Handling |
|---|---|---|
| Missing chunk | Reassembly never completes | Timeout → request resend |
| Duplicate chunk | Reassembly could double-apply | Idempotent merge keyed by sequence |
| Late chunk | UI appears to "jump" | Buffer until in-order, don't render out of sequence |
| Interrupted stream | Client stuck in partial state | Fallback to full-buffer re-request after timeout |

## Appendix E — Benchmark Detail and Trace

```text
Warmup requests:     20 (discarded)
Measured requests:   50
Reported statistics: median (P50), P95
Machine:              local proxy host, no external network hop
Browser:              Chrome 138
Transport:            HTTP/1.1
Payload:              250 KB structured JSON
```

Representative first-visible-content distribution, full buffering vs. adaptive delivery (from local benchmark):

```text
Full buffering        (median ~2.4s)   ■■■■■■■■■■■■
Adaptive delivery      (median ~480ms) ■■■
```

Representative trace shape for a chunked response (illustrative, not a production trace):

```text
span: request                         [0ms -------------------- 2900ms]
  span: serialization                 [0ms -- 40ms]
  span: delivery.chunk[0]             [40ms - 480ms]   <- first visible content
  span: delivery.chunk[1]             [480ms - 1600ms]
  span: delivery.chunk[2]             [1600ms - 2900ms]
  span: browser.render (per chunk)    [overlaps each chunk span]
```

## References

**Academic**

- Dean, J., and Barroso, L. A. "The Tail at Scale." *CACM*, 2013.
- Crankshaw, D. et al. "Clipper: A Low-Latency Online Prediction Serving System." *NSDI*, 2017.
- Agrawal, K. et al. "Sarathi-Serve: Balancing Latency and Throughput in Large Language Model Serving." *arXiv*, 2024.
- Yu, G. et al. "Orca: A Distributed Serving System for Transformer-Based Generative Models." *OSDI*, 2022.
- Kwon, H. et al. "vLLM: Easy, Fast, and Cheap LLM Serving with PagedAttention." *SOSP*, 2023.
- Dao, T. et al. "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." *NeurIPS*, 2022.

**Engineering references**

- Beyer, B. et al. (eds.) *Site Reliability Engineering.* O'Reilly, 2016.
- Kleppmann, M. *Designing Data-Intensive Applications.* O'Reilly, 2017.
- OpenTelemetry specification — tracing and span semantics.
- RFC 9110 — HTTP Semantics.

**Practical reading**

- Ray Serve, BentoML, NVIDIA Triton Inference Server, SGLang — serving infrastructure.
- Chrome DevTools Performance documentation — browser parse/render timing.