# ADR-001: Response Delivery for the CRM Copilot

- **Status:** Proposed
- **Date:** 2026-10-03
- **Decision owner:** Architecture owner to be assigned

## Context

The repository contains two distinct local response-delivery examples: an authenticated chunk-envelope/reassembly reference and a browser experiment using one ordered NDJSON-over-HTTP response. They are not integrated. The envelope reference builds the complete response before yielding; the browser harness demonstrates earlier first-batch visibility only under synthetic loopback pacing, with a larger framed body and later full completion in tested cases. Neither is a production transport.

For the proposed CRM workflow, users may benefit from seeing completed read-result records before the entire response finishes. The customer UI, payload shape, gateway buffering behavior, and production network are unknown.

## Options

1. Full JSON response: simplest compatibility and atomic parsing; no partial results.
2. One ordered NDJSON HTTP response: progressive records with a streaming client; partial UI state must be discarded on failure and the request retried.
3. Authenticated chunk envelopes: per-fragment integrity metadata, reordering/duplicate handling, and session reassembly; more protocol and state complexity, but still requires a transport adapter and currently buffers before emission.

## Decision

For the proposed user-facing read flow, evaluate **one ordered NDJSON HTTP response** as the first streaming candidate, while retaining full JSON as the fallback until the customer UI demonstrates a need for progressive delivery. Do not combine it with the envelope/retry protocol in the first integration.

This is a design choice for a proposed experiment, not a production decision validated against a customer environment. The actual choice remains conditional on end-to-end measurements and client/API compatibility.

## Consequences

- The browser client must parse complete records incrementally and clearly distinguish partial from complete results.
- On interrupted or invalid streams, discard partial state and retry the whole idempotent read request; writes must not be retried under this policy without idempotency design.
- Measure first-visible content, completion time, payload bytes, and client rendering on representative payloads. Do not claim a universal threshold from the repository's synthetic sweep.
- Reopen this decision if independent fragment retransmission, cross-transport delivery, or per-fragment authentication is a proven requirement.

## Evidence and gaps

- [Repository delivery experiment](../../03-production-lessons/01-adaptive-response-delivery.md) and [benchmark evidence](../../benchmarks/response-delivery/README.md).
- [Envelope reference boundary](../../04-reference-implementation/README.md).
- Customer payloads, API contract, client capability, proxy buffering, network profile, retry semantics, and target SLOs: **not found in repo; discovery required**.
