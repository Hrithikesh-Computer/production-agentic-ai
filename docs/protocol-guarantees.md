# Protocol Guarantees and Limits

This document describes the local Python reference protocol. It is not a
production transport or a substitute for authenticated transport, durable
state, or application-level request correlation.

## Envelope Authentication

Each envelope's HMAC-SHA256 authenticates `sequence`, `total_chunks`,
`checksum`, `is_final`, `payload`, `merge_mode`, and `message_id`. The tag is
computed with the caller-supplied shared key and compared in constant time.
CRC32 detects accidental corruption; it is not an authentication mechanism.
The key must be bytes and at least 16 bytes long.

Only these defined envelope fields are included in the canonical HMAC input.
Unknown mapping fields are ignored by the current decoder and are not
authenticated. The protocol does not provide confidentiality, key provisioning,
rotation, or protection from an authorized key holder.

## Message IDs and Replay Window

Producers must never reuse a `message_id` while an earlier message with that ID
is retained by the receiver. A message ID is authenticated per chunk, but the
protocol does not sign a full-message digest or length; reusing an ID across
different in-flight logical messages can therefore combine chunks. The receiver
rejects late chunks for completed IDs while their tombstones remain.

Completed IDs are kept in a bounded tombstone set for 3,600 seconds, with at
most 4,096 tombstones. The oldest tombstone is evicted first if the set is full.
Replay is not defended after the tombstone expires or is evicted. This is a
bounded local replay window, not durable replay protection.

## State and Payload Bounds

The session manager defaults to at most 1,024 concurrent sessions. Incomplete
sessions expire 300 seconds after their last successfully accepted new chunk;
identical duplicates do not refresh this idle timer. Expiry is lazy and runs on
the next manager intake. Active sessions share a
total payload-byte cap of 268,435,456 bytes (256 MiB). Each `Reassembler`
accepts at most 10,000 chunks and 16,000,000 payload bytes.

`ReassemblySessionManager` is not thread-safe. Concurrent calls for the same
message ID can silently lose a chunk; callers sharing one manager across
threads must serialize access.

Exceptions from `request_retry` and `request_full_buffer` propagate to the
caller. Retry counters and fallback state remain unchanged, so the next poll
invokes the callback again. Both callbacks must be idempotent.

The manager's aggregate cap charges payload bytes plus a conservative fixed
`OVERHEAD_PER_CHUNK = 96` bytes for every retained chunk, including empty
chunks. The per-message payload limit remains payload-only. The constant is
derived from measured resident-memory deltas: the largest observed
`memory_per_chunk - payload_size` for payload sizes of at least two bytes was
86.97 bytes, measured with distinct payload content per chunk for the new
8-byte and 16-byte cases, then rounded up to the next multiple of 16. This is
an empirical local estimate, not a guarantee for every Python build or host.

The following Windows/Python 3.14.6 measurements used separate processes,
prebuilt envelopes, and `GetProcessMemoryInfo` working-set readings immediately
before and after manager insertion; wall time covers only that insertion
interval. Each message declared 10,000 chunks and retained 9,999. The 8- and 32-session
16-byte runs used unique payload bytes per chunk. The earlier 1-byte and
64-byte measurements reused the same input payload object while building each
scenario; the builder still created each envelope independently.

| Scenario | Chunks held | Resident delta | Tracked payload | Resident bytes/chunk | Manager wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8 sessions × 9,999 × 16 bytes | 79,992 | 8,237,056 B | 1,279,872 B | 102.97 B | 1.821 s |
| 8 sessions × 9,999 × 8 bytes | 79,992 | 6,696,960 B | 639,936 B | 83.72 B | 1.819 s |
| 32 sessions × 9,999 × 0 bytes | 319,968 | 10,588,160 B | 0 B | 33.09 B | 8.083 s |
| 32 sessions × 9,999 × 16 bytes | 319,968 | 31,014,912 B | 5,119,488 B | 96.93 B | 8.447 s |

For deriving the charge, the prior 8-session measurements were 35.84 resident
bytes/chunk at 1 byte and 150.70 at 64 bytes. The untracked estimates were:

| Payload bytes | Resident bytes/chunk | Untracked bytes/chunk |
| ---: | ---: | ---: |
| 1 | 35.84 | 34.84 |
| 8 | 83.72 | 75.72 |
| 16 | 102.97 | 86.97 |
| 16, 32-session run | 96.93 | 80.93 |
| 64 | 150.70 | 86.70 |

Thus `U = 86.97` bytes/chunk and the implemented conservative charge is 96
bytes/chunk. At the defaults of 1,024 sessions, 9,999 retained chunks per
session, and a 268,435,456-byte aggregate cap, the attainable untracked-memory
estimate using U is:

| Payload bytes/chunk | Attainable chunks | Estimated untracked bytes | Ratio to aggregate cap |
| ---: | ---: | ---: | ---: |
| 0 | 10,238,976 | 890,519,552 | 3.317x |
| 1 | 10,238,976 | 890,519,552 | 3.317x |
| 2 | 10,238,976 | 890,519,552 | 3.317x |
| 8 | 10,238,976 | 890,519,552 | 3.317x |
| 16 | 10,238,976 | 890,519,552 | 3.317x |
| 32 | 8,388,608 | 729,586,576 | 2.718x |
| 64 | 4,194,304 | 364,793,288 | 1.359x |

The conservative pre-change gate passed: some attainable ratios exceed 2.0.
The 1,024-session estimates are theoretical; the new manager accounting also
charges the 96-byte overhead and therefore rejects chunks before reaching the
payload-only attainability limit used in this gate calculation.

These limits bound accounted retained state, not all transient Python
allocations or process memory. A sender that can authenticate requests and
abandons incomplete sessions can hold session and byte capacity until the
300-second idle TTL; the caps bound that resource use but do not prevent slot
blocking. Size container memory with headroom above `max_total_bytes` for
interpreter overhead plus up to one transient joined copy per completing
message. At the default per-message payload limit, payload plus joined output
can require about 32 MB (16 MB payload + 16 MB join), excluding Python object
and serialization overhead.

## Receiver Outcome Signals

Receiver failures and state transitions emit a structured dictionary containing
only a fixed `outcome` value: `session_cap_rejected`,
`active_payload_cap_rejected`, `message_limit_rejected`, `session_expired`,
`tombstone_evicted`, `envelope_integrity_rejected`,
`authentication_rejected`, `retry_callback_failed`,
`full_buffer_callback_failed`, or `ndjson_decoder_poisoned`. The default local
sink prints these records; the emitter accepts a sink callable for integration.
Records contain no message ID, payload, key, authentication tag, callback error
text, or configured limit values. The vocabulary and record shape therefore
have bounded cardinality and are safe to aggregate without request material.

Sink failures are intentionally isolated from protocol control flow. If a
configured outcome sink raises an ordinary `Exception`, the emitter suppresses
that sink error and continues without altering the original result, exception, or
state. `KeyboardInterrupt`, `SystemExit`, and other `BaseException` subclasses are
not suppressed.

These are local receiver outcomes, not a monitoring backend or receiver health
dashboard. A production integration must supply a sink and operational alerts.

Empty payloads are accepted. At the 10,000-chunk per-session limit, an
incomplete session can retain at most 9,999 chunks, because accepting the final
chunk completes and removes the session. The working-set measurements above
are process-local measurements, not a general memory guarantee. One
`tracemalloc` cross-check was run for the earlier smallest zero-byte scenario;
it is not used as the primary resident-memory figure.

## NDJSON Failure Contract

The NDJSON decoder accepts UTF-8, newline-delimited JSON objects, with a
1,048,576-byte maximum record. It rejects non-standard `NaN`/infinity constants,
duplicate object names, non-object records, invalid UTF-8, excessive parser
nesting, and an unterminated final record. Any decoding error poisons the
decoder. Records returned by earlier `feed()` calls cannot be retracted, so the
caller must discard every record already received for that response and retry
the whole request. Records parsed earlier in the same failing `feed()` call are
not returned.