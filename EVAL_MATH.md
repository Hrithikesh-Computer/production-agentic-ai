# Lens 5: Mathematics

## Score: 3/5

The local algorithmic logic is simple and mostly linear, and the benchmark results are internally consistent. The real issue is not arithmetic accuracy; it is that the repo is being used to make broader claims than its math and tests can support.

## Complexity

The main hot path is linear in payload size because it walks the serialized bytes and fragments them into chunks. The dominant algorithmic costs are:

- `semantic_split()` is O(n) in the input length
- `Reassembler.add_chunk()` is O(k) to hold and merge chunk data for k fragments
- memory is O(n + k) for the serialized payload and reassembly buffers

Local benchmark evidence:

- 10KB payload: mean delivery roughly 0.00012s
- 50KB payload: 0.0188s
- 150KB payload: 0.0525s
- 300KB payload: 0.0899s

This does not prove real traffic performance. It proves the reference logic behaves predictably under local conditions.

## Numerical and edge-case risks

- UTF-8 boundaries matter: chunking must respect code-point boundaries to avoid corruption.
- JSON top-level merge semantics must stay consistent across object fragments.
- Duplicate or conflicting totals can create deadlock in the reassembly state machine.
- No large-scale concurrency or multi-message load test exists.

## Top 3 mathematically risky spots

1. Chunk maximums and unsplittable values: a value that cannot fit the size limit can still be accepted unless the implementation is strict.
2. UTF-8 code-point splitting: byte boundaries are not the same as character boundaries.
3. Multi-message concurrency and state management: no proof under combined load.

## Invariants worth enforcing

- chunk totals must be positive and bounded
- sequence numbers must fit within `[0, total_chunks)`
- duplicate chunk payloads must be identical
- totals and merge modes must remain stable for a given message
- complete reassembly should produce exact original bytes or exact JSON object equivalence

## Verdict

The math is decent for a local reference implementation, but the repo should not be used as a capacity model or a production performance claim. It is a bounded proof-of-concept, not a performance specification.
