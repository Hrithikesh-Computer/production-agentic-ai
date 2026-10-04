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

These limits bound tracked protocol state, not all transient Python allocations
or process memory. A sender that can authenticate requests and abandons
incomplete sessions can hold session and byte capacity until the 300-second
idle TTL; the caps bound that resource use but do not prevent slot blocking.
Completion joins the received fragments into an output buffer while the stored
fragments are still retained. For one maximum-size 16,000,000-byte message,
payload plus joined output can therefore transiently require about 32,000,000
bytes, excluding Python object and serialization overhead.

## NDJSON Failure Contract

The NDJSON decoder accepts UTF-8, newline-delimited JSON objects, with a
1,048,576-byte maximum record. It rejects non-standard `NaN`/infinity constants,
duplicate object names, non-object records, invalid UTF-8, excessive parser
nesting, and an unterminated final record. Any decoding error poisons the
decoder. Records returned by earlier `feed()` calls cannot be retracted, so the
caller must discard every record already received for that response and retry
the whole request. Records parsed earlier in the same failing `feed()` call are
not returned.