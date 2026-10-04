# ADR-004: Envelope Versioning, Compatibility, and Key Identification

- **Status:** Proposed; conditional on ADR-001 selecting the authenticated chunk-envelope option
- **Date:** 2026-10-04
- **Decision owner:** Security and architecture owners to be assigned

## Context

The current `WireEnvelope` has no version or key ID. Its HMAC-SHA256 input is a compact, key-sorted UTF-8 JSON object containing `sequence`, `total_chunks`, `checksum`, `is_final`, `payload`, `merge_mode`, and `message_id`; the current mapping decoder ignores fields it does not consume. These are facts about the local reference, not a compatibility promise ([envelope implementation](../../04-reference-implementation/adaptive-response-filter/envelope.py), [protocol guarantees, Envelope Authentication](../../docs/protocol-guarantees.md#envelope-authentication)).

ADR-001 has not selected the envelope for the CRM workflow; its response-delivery decision remains reopened and says not to combine streaming with the envelope in the first integration ([ADR-001, Decision](ADR-001-response-delivery.md#decision)). This ADR is conditional on a later selection. It does not alter the separate context-lifecycle deferral in [ADR-003, Decision](ADR-003-context-lifecycle-deferral.md#decision).

## Problem

A receiver needs version and key identifiers to choose a schema and a verification key before it can verify the tag. Those selectors are initially untrusted. The protocol needs bounded bootstrap parsing, authenticated selectors, explicit compatibility and downgrade rules, and key-rotation behavior. The present format supplies none of those selectors, so no implementation may imply backward compatibility across a future format change.

## Options Considered

### Option 1: Keep the unversioned format

Pros

- No wire-format or receiver changes.

Cons

- Receivers cannot select among schemas or keys from the envelope, and the current format defines no cross-version compatibility behavior.
- Key changes and schema changes remain implicit deployment coordination.

### Option 2: Add a version, with key selection out of band

Pros

- The version can identify a schema and separate one protocol version's MAC domain from another.

Cons

- Receivers still need separate out-of-band key selection or key configuration per version, complicating overlapping key rotations.

### Option 3: Add a version and a configured key ID

Pros

- The version selects a schema and MAC domain; the key ID selects among locally configured keys and permits staged rotation.
- The receiver can reject unsupported versions, keys, and downgrades before allocating message state.

Cons

- Requires a precise per-version schema, canonical MAC input, bounded pre-verification parser, and coordinated sender/receiver configuration.

## Decision

If ADR-001 later selects authenticated chunk envelopes, use Option 3. Add a version and non-secret `key_id`; both are untrusted selectors until a valid tag is checked. The receiver MUST apply a configured minimum-supported-version policy and reject a missing or unsupported version, an unknown key ID, and any version below that minimum. Such failures MUST have the same externally visible failure class as a bad tag, without exposing which selector failed.

Before creating a session, tombstone, or other message state, the receiver MUST perform only a bounded parse sufficient to identify the top-level `version` and `key_id`, validate their syntax, and look each up in local version and key configuration. The parser MUST enforce a hard envelope-size bound and reject malformed or ambiguous selector encodings. It MUST NOT trust any envelope-provided schema, key material, limits, or other field at this stage. After successful lookup, the receiver validates the selected version's complete schema and MAC before accepting a chunk into session state.

The MAC input MUST include both `version` and `key_id` and the complete signed field set defined for that version. The version is a domain separator: changing the version or key ID MUST invalidate the tag. The current implementation serializes a named JSON object using `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, then UTF-8 encodes it ([`authentication_tag`](../../04-reference-implementation/adaptive-response-filter/envelope.py)). JSON field names, quoting, and delimiters make this encoding structurally unambiguous for its current fixed object; it is not raw field concatenation. However, no versioned or cross-language canonical encoding is implemented. Each future version must normatively define its exact signed field set, canonical encoding, and treatment of omitted/default fields before implementation; interoperability across versions remains an evidence gap.

All chunks for one `message_id` MUST carry the same version and `key_id`; a mismatch rejects the chunk and MUST NOT change the established session metadata. An old but otherwise valid message within an accepted version is a replay-window concern, not a version-negotiation concern. The local reference documents a 300-second idle session TTL and a 3,600-second tombstone TTL, with at most 4,096 tombstones and oldest-first eviction at capacity; these are reference defaults, not deployment guarantees ([protocol guarantees, Message IDs and Replay Window](../../docs/protocol-guarantees.md#message-ids-and-replay-window)).

`key_id` is an identifier, not a secret. It selects only a key present in receiver-local configuration. To rotate: distribute and install the new key on receivers; switch senders to the new key ID; stop all use of the old key; allow active sessions to finish or expire under the maximum session TTL; then retire the old key by removing it from every receiver's key map. Waiting out the tombstone window is unnecessary after removal: old-key messages can no longer verify. Key provisioning, storage, and rotation are not implemented by the reference ([ADR-002, Context](ADR-002-approval-signing.md#context), [ADR-002, Options](ADR-002-approval-signing.md#options), [envelope evidence, Scope and threat model](../../04-reference-implementation/adaptive-response-filter/EVIDENCE.md#scope-and-threat-model)).

For versioned envelopes, unknown mapping fields MUST be rejected unless that version explicitly defines them as signed fields. Additive unsigned envelope fields are not allowed: the current decoder ignores unknown mapping fields and they are unsigned, which can cause sender/receiver semantic disagreement ([`from_mapping`](../../04-reference-implementation/adaptive-response-filter/envelope.py)).

An envelope change is breaking if it changes the signed field set or tag computation, chunk/reassembly semantics, or a limit in a way that changes which messages are valid. Announce breaking changes under a new version, with a changelog entry and an update to [protocol-guarantees.md](../../docs/protocol-guarantees.md). Additive data is permitted only when the selected version defines it and authenticates it.

The disposition of unversioned legacy envelopes remains an open question. A versioned receiver rejects a missing version by default; accepting legacy input would require an explicit legacy-version mapping, a stated sunset period, and a separate compatibility decision. No backward compatibility is implied in the meantime.

## Trade-offs

- The bootstrap parser and local allowlists add receiver complexity, but keep untrusted selectors bounded and prevent envelope data from creating session state before selection and authentication.
- Strict version and key rejection makes incompatible deployments fail closed; rollout therefore requires receiver configuration before sender changes.
- Shared-key HMAC does not separate verification from signing authority: every verifier holding a shared key can forge valid chunks ([ADR-002, Options](ADR-002-approval-signing.md#options)). This ADR does not change that, and asymmetric signatures are out of scope.
- The protocol provides integrity and authenticity, not confidentiality. Deployment MUST use a protected transport such as TLS; confidentiality is a transport requirement, not an envelope property ([protocol guarantees, Envelope Authentication](../../docs/protocol-guarantees.md#envelope-authentication)).

## Consequences

- This is a proposed future design, not an implementation or production key-management decision. Versioned canonicalization, parser bounds, deployment minimum-version policy, and rotation timing require specification and implementation evidence.
- The current message-ID choice remains Option A: the documented producer contract forbids reusing an ID while the receiver retains it. R4 remains a strict xfail because the current wire format has no message-level digest ([protocol guarantees, Message IDs and Replay Window](../../docs/protocol-guarantees.md#message-ids-and-replay-window), [R4 regression test](../../tests/test_protocol_regression.py)). If a message-level digest is ever adopted, it would ship under a new version and require this ADR before implementation; it is not planned.
- Future implementation gates, not tests added by this ADR: tamper with version/key ID; strip either selector; attempt downgrade; send unknown version or key ID; mix versions or key IDs within one message; and run matching mutants for those checks.
- Open questions: whether and for how long to accept unversioned legacy envelopes; whether receiver session and tombstone keys should be scoped by `(key_id, message_id)` to prevent one configured key holder from occupying another key's message ID; the normative cross-language canonical encoding and per-version signed-field rules; and deployment-specific key distribution and minimum-version rollout.
