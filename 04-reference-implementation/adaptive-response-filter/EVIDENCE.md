# Adaptive Response Filter Evidence

## Scope and threat model

This evidence applies only to the checked-in Python reference implementation and its local tests. It is not evidence of a production deployment, network transport, browser integration, or performance service level.

Each chunk now carries an HMAC-SHA256 over its payload, CRC32, sequence, chunk count, final flag, merge mode, and message ID. The receiver verifies the HMAC with a caller-supplied shared key before storing a chunk. This defends against in-transit modification and spoofed chunks by a party that does not possess the key, including metadata changes and CRC recomputation. It does not defend against a malicious authorized sender, a compromised endpoint, key theft, weak key generation, replay outside a correctly managed message/session lifetime, or denial of service. Key provisioning, rotation, storage, and transport confidentiality are outside this slice.

## Observed before/after behavior

| Item | Before, observed in this workspace | After, observed in this workspace | Evidence |
|---|---|---|---|
| Chunk authentication | The baseline suite passed 44 tests while envelopes used CRC32 only. CRC32 could detect accidental payload corruption but did not identify the sender or reject a payload modified with a recomputed CRC. | The reassembler rejects a payload changed together with a recomputed CRC because the HMAC no longer matches. Authenticated envelope and reassembly tests pass. | `test_hmac_rejects_tampering_even_if_crc_is_recomputed`; focused test run: 31 passed after HMAC integration. |
| Tool boundary | Tool-call arrays had no dedicated strategy; oversized object values fell back to fixed-size splitting or raised `UnsplittableValueError`. | An oversized top-level `tool_calls` list splits only between complete tool records after JSON-key splitting cannot satisfy the cap; concatenated chunks parse to the original JSON. | `test_oversized_tool_calls_fall_through_to_tool_boundaries`; chunker tests: 15 passed. Oversized individual tool records still do not split internally. |
| Timeout, retry, and full-buffer fallback | `Reassembler` buffered incomplete messages and reported missing sequence numbers, but did not schedule a retry or request a replacement full response. | `ReassemblySession.poll_timeout()` requests missing indexes up to the `DeliveryPolicy.max_retries` limit and then invokes the caller-provided full-buffer callback. The deterministic test observed retry request `("response-1", [1])`, followed by the returned `b"complete response"` fallback. | `test_missing_chunk_retries_then_falls_back_to_full_buffer`; `test_delivery_policy_rejects_invalid_recovery_limits`; focused session tests: 3 passed. |
| Multi-message handling | A `Reassembler` handled one message and rejected reuse after completion. Concurrent response behavior was not represented. Whether actual production clients can have two in-flight responses collide cannot be determined from this repository. | `ReassemblySessionManager` routes interleaved fragments by authenticated `message_id`; the test interleaved two responses and reconstructed `b"A1"` and `b"B2"` independently. The original single-message `Reassembler` remains available for one-message use. | `test_manager_keeps_two_in_flight_messages_separate`; manager test passes. Production collision likelihood remains `EVIDENCE REQUIRED: client request concurrency, transport correlation identifiers, and in-flight response traces from the target deployment`. |

## Verification run

After these changes, the full reference slice reported `49 passed in 0.34s`, Ruff reported `All checks passed!`, and mypy reported `Success: no issues found in 12 source files`. These are local checks, not production timing or security certification.

## Remaining evidence required

- `EVIDENCE REQUIRED: production key generation, provisioning, rotation, storage, and compromise-response design`.
- `EVIDENCE REQUIRED: target transport implementation and replay/expiry policy`.
- `EVIDENCE REQUIRED: production client concurrency and traces to determine real message-collision exposure`.
- `EVIDENCE REQUIRED: integration evidence that the retry callback maps to an actual resend endpoint and that the full-buffer callback returns the same logical response`.
- `EVIDENCE REQUIRED: measurements of timeout/retry overhead, HMAC throughput, and memory under representative production payloads and concurrency`.
- Heading, paragraph, sentence, and citation-block strategies remain unimplemented; only `tool_calls` boundary splitting was added in this action.
