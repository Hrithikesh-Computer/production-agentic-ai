# Evidence map

This document maps the repository's major claims to the implementation, tests, benchmark evidence, and remaining limits.

## Evidence model

Each major claim in the repository falls into one of four categories:

- implemented and tested
- conceptual and architecture-level
- benchmarked locally under controlled conditions
- missing evidence / future research

## Claim map

| Claim / article area | Implementation | Tests / benchmark | What is proven | Remaining limits |
|---|---|---|---|---|
| Adaptive response delivery is a valid production bottleneck concept | `04-reference-implementation/adaptive-response-filter` | `benchmarks/response-delivery/benchmark.py` | The local one-message delivery policy and reassembly logic behave correctly under controlled payload sizes | Not a deployed browser or production service benchmark |
| Context lifecycle matters as a design problem | conceptual architecture and local policy logic | `benchmarks/context-lifecycle/benchmark.py` | Synthetic retention policies can be compared under fixed conditions | No production memory workload evidence |
| Authority / intent require more than identity and permissions | conceptual authority model | `benchmarks/authority-conformance/test_authority_conformance.py` | The local reasoning model enforces expected outcomes for a small set of scenarios | Not a full runtime authorization or security system |
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
