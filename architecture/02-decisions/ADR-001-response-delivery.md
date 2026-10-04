# ADR-001: Response Delivery for the CRM Copilot

- **Status:** Reopened
- **Date:** 2026-10-03
- **Decision owner:** Architecture owner to be assigned

## Context

The repository contains two distinct local response-delivery examples: an authenticated chunk-envelope/reassembly reference and a browser experiment using one ordered NDJSON-over-HTTP response. They are not integrated. The envelope reference builds the complete response before yielding. Three browser artifacts now distinguish a legacy three-mode standalone HeadlessChrome run, a clean four-mode standalone HeadlessChrome run, and a four-mode Electron-embedded run. In the generated structured 300 KB case at 10 MB/s, NDJSON completion is about 87-89 ms later than full JSON in the two standalone runs and 30 ms later in Electron. This client-runtime variation means the measured penalty is not an invariant cost of NDJSON; its mechanism remains unisolated. None is a production transport.

For the proposed CRM workflow, users may benefit from seeing completed read-result records before the entire response finishes. The customer UI, payload shape, gateway buffering behavior, and production network are unknown. The benchmarked clients are standalone HeadlessChrome 154 and Electron 42's embedded Chromium; neither is established as the target CRM client. A second browser engine and a parse-once-per-animation-frame client variant remain needed to separate runtime and client-scheduling effects.

## Options

1. Full JSON response: simplest compatibility and atomic parsing; no partial results.
2. Full JSON with gzip: compatibility and atomic parsing with fewer wire bytes when payloads compress well; adds compression CPU and still waits for the full body.
3. One ordered NDJSON HTTP response: progressive records with a streaming client; partial UI state must be discarded on failure and the request retried.
4. Gzip-compressed ordered NDJSON: progressive records with reduced wire bytes. The clean four-mode standalone run and Electron run measure this arm with matching payload sizes; only the clean four-mode standalone run has both a passing Long Task control and complete harness provenance. Results vary by runtime, and compression buffering/flush behavior and per-record work may affect first visibility and completion.
5. Authenticated chunk envelopes: per-fragment integrity metadata, reordering/duplicate handling, and session reassembly; more protocol and state complexity, but still requires a transport adapter and currently buffers before emission.

## Decision

**Reopened:** retain full JSON as the compatibility baseline, but do not select a streaming candidate until the four delivery modes are tested with representative CRM payloads and named target clients. The clean four-mode standalone run provides a reproducible synthetic baseline; the Electron comparison shows that completion costs vary by runtime. Add a second browser engine and a client variant that parses once per animation frame, and compare compression-level server CPU with estimated transfer-time savings. Client decompression/rendering cost remains unmeasured. Do not combine streaming with the envelope/retry protocol in the first integration.

This is a design choice for a proposed experiment, not a production decision validated against a customer environment. The actual choice remains conditional on end-to-end measurements and client/API compatibility.

## Consequences

- The browser client must parse complete records incrementally and clearly distinguish partial from complete results.
- On interrupted or invalid streams, discard partial state and retry the whole idempotent read request; writes must not be retried under this policy without idempotency design.
- Name supported target clients and their browser/runtime versions before a pilot; measure first-visible content, completion time, actual payload bytes, server compression CPU, and client decompression/rendering cost on representative payloads across the compression-ratio sweep. Include a second browser engine and a parse-once-per-animation-frame variant. Do not claim a universal threshold from the repository's synthetic sweep.
- Keep the decision reopened if independent fragment retransmission, cross-transport delivery, or per-fragment authentication is a proven requirement; otherwise revisit only after the matched compression/framing measurements are available.

## Evidence and gaps

- [Repository delivery experiment](../../03-production-lessons/01-adaptive-response-delivery.md) and [benchmark evidence](../../benchmarks/response-delivery/README.md).
- [Envelope reference boundary](../../04-reference-implementation/README.md).
- The legacy three-mode standalone, clean four-mode standalone, and Electron four-mode artifacts are recorded separately in the [benchmark evidence](../../benchmarks/response-delivery/README.md). The clean standalone run has a passing Long Task control and recorded harness provenance; Electron has matching four-mode payload sizes but a failed Long Task control and incomplete provenance.
- Detailed P50 timing, compression-level, and break-even calculations are in the [browser matrix evidence](../../benchmarks/response-delivery/browser-matrix-evidence.md).
- Customer payloads, API contract, client capability, proxy buffering, network profile, retry semantics, and target SLOs: **not found in repo; discovery required**.
