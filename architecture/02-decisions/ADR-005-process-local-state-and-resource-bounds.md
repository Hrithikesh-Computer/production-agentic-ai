# ADR-005: Process-Local Receiver State and Resource Bounds

- **Status:** Accepted for the local reference implementation; not a production deployment decision
- **Date:** 2026-10-04
- **Decision owner:** Reference implementation maintainers; accountable owner to be assigned before a pilot

## Context

The response-delivery reference keeps incomplete sessions and replay tombstones
in Python process memory. It accepts authenticated chunks into bounded message
state and exposes a separate fail-closed NDJSON decoder. The implementation is
local and has no persistent store, background scheduler, multi-key receiver,
or cross-process coordination. This ADR records those current choices and the
defaults that make the reference reproducible; it does not select a production
transport or durability model.

## Problem

Without an explicit record, the local limits and eviction behavior can be
mistaken for deployment guarantees. A future implementation also needs clear
evidence for when process-local state, lazy cleanup, and intake-time accounting
are no longer sufficient.

## Options Considered

### Option 1: Keep the reference process-local and bounded

Pros

- Keeps the example small, deterministic, and testable without infrastructure.
- Makes memory and replay-window limits explicit and enforceable in one process.

Cons

- A process restart loses incomplete sessions and tombstones.
- State is not shared across workers, and lazy expiry does no work while idle.
- Recomputing total active payload bytes is O(number of active sessions) per intake.

### Option 2: Add durable or shared state now

Pros

- Could support restart recovery, cross-worker coordination, and durable replay state.

Cons

- Requires atomicity, acknowledgments, recovery, isolation, consistency, and
  retention decisions not evidenced by a representative workload.
- Would add infrastructure and obscure the purpose of this local reference.

## Decision

Use Option 1 for the local reference. State is process-local and volatile. The
manager is not thread-safe; callers sharing one manager across threads must
serialize access. No cross-process replay or recovery guarantee is made.

The current defaults are:

| Setting | Default | Rationale and behavior |
| --- | ---: | --- |
| Concurrent incomplete sessions | 1,024 | Bounds session objects while allowing interleaved messages in the reference. |
| Session idle TTL | 300 seconds | Releases abandoned partial messages; only a new chunk refreshes activity. |
| Tombstone TTL | 3,600 seconds | Keeps completed IDs in the local replay window. |
| Tombstone capacity | 4,096 | Bounds replay state; evict the oldest tombstone first at capacity. |
| Aggregate active memory bytes | 268,435,456 bytes (256 MiB) | Caps payload plus a fixed 96-byte charge per retained chunk. Recompute the active sum on each intake to avoid a separately maintained counter drifting on duplicates, completion, or expiry; the scan is bounded by the session cap. The charge rounds the measured maximum untracked estimate of 86.97 bytes/chunk up to a multiple of 16. |
| Per-retained-chunk aggregate charge | 96 bytes | Conservative measured Python object and container overhead estimate; applies to empty chunks too. It does not alter the per-message payload-only limit. |
| Chunks per message | 10,000 | Bounds per-message bookkeeping; a completed message leaves active session state. |
| Payload bytes per message | 16,000,000 bytes | Bounds one reassembled payload independently of the aggregate cap. |
| NDJSON record bytes | 1,048,576 bytes (1 MiB) | Bounds one decoder record before JSON parsing. |
| Chunk threshold / chunk size | 128,000 / 64,000 bytes | Local `DeliveryPolicy` defaults for choosing full versus chunked delivery and splitting chunks. |
| Retry timeout / retry count | 1.0 second / 1 | Local callback-driven retry defaults; the caller must poll, and there is no scheduler. |

Expiry is lazy: the next manager intake identifies and evicts expired sessions
and tombstones. It does not run on a timer. An individual manager is configured
with one authentication key, and session/tombstone dictionaries are keyed by
`message_id`, not `(key_id, message_id)`. IDs therefore share one namespace
within that manager. Producers must not reuse an ID while it is retained. This
does not prevent mixing chunks from distinct logical messages that reuse the
same ID; the current wire format has no full-message digest, and regression R4
remains an explicit limitation.

NDJSON decoding fails closed. Any parse, validation, size, UTF-8, or incomplete
record error poisons the decoder and clears its pending bytes. Records already
returned by earlier calls cannot be retracted, so the caller must discard the
entire response and retry it. The decoder does not scan ahead to resynchronize.
An explicit caller `discard()` also closes the decoder but is not reported as a
poisoning error.

## Trade-offs

- The defaults are conservative teaching/reference bounds, not capacity
  recommendations. Python object overhead is not covered by the payload-byte
  cap; local measurements are recorded in
  [protocol-guarantees.md](../../docs/protocol-guarantees.md).
- Lazy cleanup avoids a worker thread or scheduler but means expiry is only
  observed during later intake.
- Oldest-first tombstone eviction favors recent completions when the bounded
  replay set fills, at the cost of an earlier replay window for evicted IDs.
- ID-only keys are sufficient for the current one-key manager. A multi-key
  receiver would need an isolation decision before sharing its state namespace.
- Intake-time summation keeps accounting derived from live reassembler state,
  but cost grows linearly with the configured session cap.

## Consequences

Revisit these choices before a pilot or when evidence changes. Replace or revise
this decision if any of the following becomes true:

- A representative load test shows intake-time summation materially affects
  latency, or measured process memory approaches the deployment budget.
- Aggregate memory including the fixed per-chunk overhead exceeds the
  deployment budget.
- A pilot requires multiple workers, restart recovery, durable replay
  protection, per-principal quotas, acknowledgments, or coordinated expiry.
- The receiver accepts multiple keys or key IDs; define whether state is scoped
  by `(key_id, message_id)` and how cross-key isolation works.
- A named client requires a transport, scheduler, or different retry contract.
- A threat model or compliance requirement changes the fail-closed decoder,
  retention, deletion, or replay guarantees.

Any change to wire validity, authenticated fields, or replay semantics must be
reviewed with ADR-004 and versioned as required there. Tuning local numeric
defaults requires benchmark evidence, tests at the new boundaries, and an update
to the protocol guarantees and this ADR.