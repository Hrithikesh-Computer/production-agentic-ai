import json

import pytest
from chunker import UnsplittableValueError, semantic_split
from policy import DeliveryPolicy


def test_small_payload_stays_whole():
    payload = json.dumps({"a": 1}).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=10_000)
    assert len(chunks) == 1
    assert json.loads(chunks[0]) == {"a": 1}


def test_large_payload_splits_by_top_level_keys():
    payload = json.dumps({
        "a": "x" * 100,
        "b": "y" * 100,
        "c": "z" * 100,
    }).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=120)
    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
    # every key must survive intact in exactly one chunk
    merged = {}
    for chunk in chunks:
        merged.update(json.loads(chunk))
    assert merged == json.loads(payload)


def test_oversized_tool_calls_fall_through_to_tool_boundaries():
    payload = json.dumps(
        {
            "status": "ok",
            "tool_calls": [
                {"name": "lookup", "result": "x" * 45},
                {"name": "summarize", "result": "y" * 45},
                {"name": "recommend", "result": "z" * 45},
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")

    chunks = semantic_split(payload, max_chunk_bytes=90)

    assert len(chunks) > 1
    assert all(len(chunk) <= 90 for chunk in chunks)
    assert json.loads(b"".join(chunks)) == json.loads(payload)
    assert all(b'"name"' not in chunk or b'"result"' in chunk for chunk in chunks)


def test_non_json_falls_back_to_fixed_size():
    payload = b"not json at all" * 50
    chunks = semantic_split(payload, max_chunk_bytes=100)
    assert b"".join(chunks) == payload
    assert all(len(c) <= 100 for c in chunks)


def test_oversized_single_value_respects_limit_or_fails():
    payload = json.dumps({"text": "x" * 100}).encode("utf-8")

    with pytest.raises(UnsplittableValueError):
        semantic_split(payload, max_chunk_bytes=10)


def test_multibyte_text_survives_chunk_round_trip():
    payload = "A🙂BC🙂D".encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=5)

    assert all(len(chunk) <= 5 for chunk in chunks)
    assert all(chunk.decode("utf-8") for chunk in chunks)
    assert b"".join(chunks) == payload


def test_single_code_point_larger_than_limit_fails_deliberately():
    with pytest.raises(UnsplittableValueError, match="code point"):
        semantic_split("🙂".encode("utf-8"), max_chunk_bytes=2)


def test_delivery_policy_rejects_invalid_limits():
    with pytest.raises(ValueError, match="threshold_bytes"):
        DeliveryPolicy(threshold_bytes=-1)
    with pytest.raises(ValueError, match="max_chunk_bytes"):
        DeliveryPolicy(max_chunk_bytes=0)


def test_delivery_policy_chunks_at_threshold():
    policy = DeliveryPolicy(threshold_bytes=10)

    assert not policy.should_chunk(b"123456789")
    assert policy.should_chunk(b"1234567890")


@pytest.mark.parametrize("max_chunk_bytes", [0, -1])
def test_chunker_rejects_nonpositive_chunk_size(max_chunk_bytes):
    with pytest.raises(ValueError, match="max_chunk_bytes"):
        semantic_split(b"payload", max_chunk_bytes)


def test_chunker_rejects_noninteger_chunk_size():
    with pytest.raises(TypeError, match="max_chunk_bytes"):
        semantic_split(b"payload", True)


@pytest.mark.parametrize(
    "payload",
    [
        b'["alpha", "beta", {"nested": true}]',
        b"1234567890",
        b'"plain scalar text"',
    ],
)
def test_non_object_json_round_trips_exact_bytes(payload):
    chunks = semantic_split(payload, max_chunk_bytes=7)

    assert len(chunks) > 1
    assert all(len(chunk) <= 7 for chunk in chunks)
    assert b"".join(chunks) == payload


if __name__ == "__main__":
    test_small_payload_stays_whole()
    test_large_payload_splits_by_top_level_keys()
    test_non_json_falls_back_to_fixed_size()
    print("all chunker tests passed")
