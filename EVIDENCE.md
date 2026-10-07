# Evidence map

This document maps the repository's major claims to the implementation, tests, benchmark evidence, and remaining limits.

## Evidence model

Each claim is categorized as one of the following:

- measured locally under controlled conditions
- missing evidence / future research

## Claim map

| Claim / article area | Implementation | Tests / benchmark | What is proven | Remaining limits |
|---|---|---|---|---|
| Adaptive response-delivery implementation overhead | `04-reference-implementation/adaptive-response-filter` | [`benchmark.py`](benchmarks/response-delivery/benchmark.py) and local tests | Matched payloads are passed through both local policies; chunked envelopes are authenticated and reassembled in reverse arrival order | Local implementation timings only; not end-to-end delivery measurements |
| Framed HTTP first-visible delivery under paced synthetic workloads | [`browser_benchmark.py`](benchmarks/response-delivery/browser_benchmark.py) | [`browser_results.json`](benchmarks/response-delivery/browser_results.json) | Standalone HeadlessChrome 154 tested structured and text-like generated payloads at four rates. The server records request/header/first-write/completion timestamps; the detected 120 ms positive control validates Long Task observation for this artifact. | CPython 3.14.6 on Windows 11; loopback, generated list UI, nominal server pacing, one browser build; first-visible is an animation-frame proxy, not compositor paint. No production-network or representative CRM payload evidence. |
| Compression and gzip-framed delivery under paced synthetic workloads | [`browser_benchmark.py`](benchmarks/response-delivery/browser_benchmark.py) | [`browser_results_compression.json`](benchmarks/response-delivery/browser_results_compression.json) | Electron-embedded four-mode run covers full JSON, gzip full JSON, NDJSON, and gzip NDJSON across the generated matrix; 384 server timing records are saved. Gzip levels 1, 3, 6, and 9 record resulting ratios and process CPU averaged over 100 compression repetitions. | Electron-embedded Chrome; the 120 ms Long Task positive control was not detected. The run is not a standalone-Chrome comparison; bodies are generated, gzip is precomputed, and no representative CRM corpus is included. |
| Basic time-bounded authority policy and referral behavior | [`authority_policy.py`](04-reference-implementation/authority_policy.py) | [`test_authority_policy.py`](tests/test_authority_policy.py) and [`test_authority_referral.py`](tests/test_authority_referral.py) | Tests cover matching principal/action, grant bounds, revocation, priority precedence, deny-on-tie, referral propagation through aggregate/session/ticket paths, and no ticket issuance for `refer`. | No agent runtime, delegated authority, multi-hop derivation, or semantic-alignment implementation. |
| Incremental NDJSON record decoding | [`ndjson_stream.py`](04-reference-implementation/ndjson_stream.py) | [`test_ndjson_stream.py`](tests/test_ndjson_stream.py) and [`test_ndjson_guards.py`](tests/test_ndjson_guards.py) | Local tests exercise incremental records, size limits, invalid data, and failure-state behavior. | No production browser adapter or server integration; browser JavaScript parsing is exercised by the separate loopback harness only. |
| Approval-gated CRM workflow | [`identity_provider.py`](prototypes/crm_operational_copilot/identity_provider.py), the SQLite stores, and [`execution_service.py`](prototypes/crm_operational_copilot/execution_service.py) | [`test_crm_validation_scenarios.py`](tests/test_crm_validation_scenarios.py), CRM unit tests, the deterministic harness, and [`mutation_check.py`](mutation_check.py) | Local identity/scope rechecks, conditional claims, version-checked CRM writes with a transactional ledger, audit recovery, 17 contract scenarios, and local 50-process concurrency are exercised. | Deterministic local SQLite only; no real identity provider, CRM, distributed coordination, deployment, telemetry, or customer evidence. |
| Context lifecycle | No implementation or benchmark | None | No context lifecycle behavior is verified in this repository | Representative workflow and retention policy experiment remain future work |
| Local protocol invariants are valid | `WireEnvelope`, `Reassembler`, `DeliveryPolicy` | unit tests under `04-reference-implementation/...` | CRC, auth/validation, ordering, retry behavior, and reassembly are exercised locally | Not a network transport or multi-service deployment |

## Evidence posture

This repository is strongest when it presents local, reproducible evidence. It is weaker when it treats architectural reasoning as if it were a production deployment result. The benchmark layer exists to make the strongest claims more explicit and more testable while preserving the repository's honest boundary.

## Qualifying language to prefer

- "local controlled experiment"
- "conceptual architecture"
- "reference implementation"
- "illustrative benchmark"
- "not yet production-validated"
- "future research opportunity"

## Explicitly excluded claims

The repository does not claim:

- a production deployment stack
- a deployed browser-optimized transport
- a secure production authorization system
- real production customer telemetry
- production SLA evidence
