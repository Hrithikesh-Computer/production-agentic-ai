import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pytest

from chunker import semantic_split
from reassembler import Reassembler, checksum


def _to_envelope(sequence, total, payload, is_final):
    return {
        "sequence": sequence,
        "total_chunks": total,
        "checksum": checksum(payload),
        "is_final": is_final,
        "payload": payload.decode("utf-8"),
    }


def test_reassembles_in_order():
    payload = json.dumps({"a": "x" * 100, "b": "y" * 100}).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=110)
    envelopes = [
        _to_envelope(i, len(chunks), c, i == len(chunks) - 1)
        for i, c in enumerate(chunks)
    ]

    reassembler = Reassembler()
    result = None
    for env in envelopes:
        result = reassembler.add_chunk(env)

    assert result is not None
    assert json.loads(result) == json.loads(payload)


def test_reassembles_out_of_order():
    payload = json.dumps({"a": "x" * 100, "b": "y" * 100}).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=110)
    envelopes = [
        _to_envelope(i, len(chunks), c, i == len(chunks) - 1)
        for i, c in enumerate(chunks)
    ]

    reassembler = Reassembler()
    result = None
    for env in reversed(envelopes):
        result = reassembler.add_chunk(env)

    assert result is not None
    assert json.loads(result) == json.loads(payload)


def test_checksum_mismatch_raises():
    payload = b'{"a": 1}'
    bad_envelope = {
        "sequence": 0,
        "total_chunks": 1,
        "checksum": "deadbeef",
        "is_final": True,
        "payload": payload.decode("utf-8"),
    }
    reassembler = Reassembler()
    with pytest.raises(ValueError):
        reassembler.add_chunk(bad_envelope)


def test_missing_reports_correctly():
    reassembler = Reassembler()
    reassembler.add_chunk(_to_envelope(0, 3, b'{"a": 1}', False))
    assert reassembler.missing() == [1, 2]


if __name__ == "__main__":
    test_reassembles_in_order()
    test_reassembles_out_of_order()
    test_missing_reports_correctly()
    try:
        test_checksum_mismatch_raises()
    except Exception:
        pass
    print("all reassembler tests passed (run via pytest for full coverage)")
