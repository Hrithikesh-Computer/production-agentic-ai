import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chunker import semantic_split


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
    # every key must survive intact in exactly one chunk
    merged = {}
    for chunk in chunks:
        merged.update(json.loads(chunk))
    assert merged == json.loads(payload)


def test_non_json_falls_back_to_fixed_size():
    payload = b"not json at all" * 50
    chunks = semantic_split(payload, max_chunk_bytes=100)
    assert b"".join(chunks) == payload
    assert all(len(c) <= 100 for c in chunks)


if __name__ == "__main__":
    test_small_payload_stays_whole()
    test_large_payload_splits_by_top_level_keys()
    test_non_json_falls_back_to_fixed_size()
    print("all chunker tests passed")
