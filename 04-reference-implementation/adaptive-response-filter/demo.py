from __future__ import annotations

from filter import AdaptiveResponseFilter


def build_sample_payload(size: int) -> str:
    return "A" * size


if __name__ == "__main__":
    filter = AdaptiveResponseFilter(threshold_bytes=2_000, max_chunk_chars=400)

    small_payload = build_sample_payload(300)
    large_payload = build_sample_payload(3_000)

    small_result = filter.build(small_payload)
    large_result = filter.build(large_payload)

    print("Small payload ->", small_result.mode, "size=", len(small_payload.encode("utf-8")))
    print("Large payload ->", large_result.mode, "chunks=", len(large_result.chunks))

    if large_result.chunks:
        first_chunk = large_result.chunks[0]
        last_chunk = large_result.chunks[-1]
        print("First chunk checksum:", first_chunk.checksum)
        print("Last chunk checksum:", last_chunk.checksum)
        print("Final chunk:", last_chunk.is_final)
