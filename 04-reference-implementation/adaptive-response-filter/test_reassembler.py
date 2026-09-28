import json

import pytest
from chunker import semantic_split
from envelope import checksum
from filter import AdaptiveResponseFilter
from middleware import filter_response
from policy import DeliveryPolicy
from reassembler import Reassembler


def _to_envelope(sequence, total, payload, is_final):
    return {
        "sequence": sequence,
        "total_chunks": total,
        "checksum": checksum(payload),
        "is_final": is_final,
        "payload": payload.decode("utf-8"),
        "merge_mode": "json-object",
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


def test_identical_duplicate_is_idempotent_and_conflict_is_rejected():
    reassembler = Reassembler()
    first = _to_envelope(0, 2, b'{"a": 1}', False)

    assert reassembler.add_chunk(first) is None
    assert reassembler.add_chunk(first) is None
    with pytest.raises(ValueError, match="conflicting duplicate"):
        reassembler.add_chunk(_to_envelope(0, 2, b'{"a": 2}', False))
    assert reassembler.missing() == [1]


def test_rejects_total_change_and_out_of_range_sequence():
    reassembler = Reassembler()
    reassembler.add_chunk(_to_envelope(0, 2, b'{"a": 1}', False))

    with pytest.raises(ValueError, match="total_chunks"):
        reassembler.add_chunk(_to_envelope(1, 3, b'{"b": 2}', False))

    with pytest.raises(ValueError, match="sequence"):
        Reassembler().add_chunk(_to_envelope(2, 1, b'{"a": 1}', True))


def test_rejects_invalid_merge_mode_before_storing_chunk():
    invalid = _to_envelope(0, 1, b"payload", True)
    invalid["merge_mode"] = "unknown"
    reassembler = Reassembler()

    with pytest.raises(ValueError, match="merge_mode"):
        reassembler.add_chunk(invalid)
    assert reassembler.total_chunks is None


def test_filter_api_uses_shared_crc32_contract():
    payload = "plain text with 🙂 content" * 4
    result = AdaptiveResponseFilter(
        threshold_bytes=1,
        max_chunk_bytes=16,
    ).build(payload)
    reassembler = Reassembler()

    assembled = None
    for chunk in result.chunks:
        assembled = reassembler.add_chunk(chunk)

    assert assembled == payload.encode("utf-8")


def test_filter_api_returns_full_result_below_threshold():
    result = AdaptiveResponseFilter(threshold_bytes=100).build("small")

    assert result.mode == "full"
    assert result.payload == "small"
    assert result.chunks == []


def test_middleware_full_buffer_path_emits_one_envelope():
    envelopes = list(
        filter_response("small", DeliveryPolicy(threshold_bytes=100))
    )

    assert len(envelopes) == 1
    assert envelopes[0]["total_chunks"] == 1
    assert envelopes[0]["payload"] == '"small"'


def test_middleware_emits_delivery_metrics(monkeypatch):
    emitted = []
    monkeypatch.setattr("middleware.emit", emitted.append)

    list(filter_response("small", DeliveryPolicy(threshold_bytes=100)))

    assert len(emitted) == 1
    assert emitted[0].as_dict()["payload_size"] == len(b'"small"')
    assert emitted[0].as_dict()["chunk_count"] == 1


def test_middleware_reassembles_non_object_json():
    response = ["alpha", "🙂", {"nested": True}]
    envelopes = list(
        filter_response(
            response,
            DeliveryPolicy(threshold_bytes=1, max_chunk_bytes=8),
        )
    )
    reassembler = Reassembler()

    assembled = None
    for envelope in envelopes:
        assembled = reassembler.add_chunk(envelope)

    assert assembled is not None
    assert json.loads(assembled) == response


@pytest.mark.parametrize("response", [17, True, None, "plain text 🙂"])
def test_middleware_reassembles_scalar_and_text_responses(response):
    envelopes = list(
        filter_response(
            response,
            DeliveryPolicy(threshold_bytes=1, max_chunk_bytes=5),
        )
    )
    reassembler = Reassembler()

    assembled = None
    for envelope in envelopes:
        assembled = reassembler.add_chunk(envelope)

    assert assembled == json.dumps(response, ensure_ascii=False).encode("utf-8")


def test_middleware_reassembles_json_object_fragments():
    response = {"a": "x" * 100, "b": "y" * 100}
    envelopes = list(
        filter_response(
            response,
            DeliveryPolicy(threshold_bytes=1, max_chunk_bytes=110),
        )
    )
    reassembler = Reassembler()

    assembled = None
    for envelope in envelopes:
        assembled = reassembler.add_chunk(envelope)

    assert assembled is not None
    assert json.loads(assembled) == response


def test_rejects_chunk_count_and_payload_over_configured_limits():
    oversized_count = _to_envelope(0, 2, b"x", False)
    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(max_chunks=1).add_chunk(oversized_count)

    oversized_payload = _to_envelope(0, 1, b"payload", True)
    oversized_payload["merge_mode"] = "concat"
    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(max_payload_bytes=4).add_chunk(oversized_payload)


def test_reassembler_rejects_second_message_after_completion():
    reassembler = Reassembler()
    completed_message = _to_envelope(0, 1, b'{"a": 1}', True)

    assert reassembler.add_chunk(completed_message) is not None
    with pytest.raises(ValueError, match="one message"):
        reassembler.add_chunk(completed_message)


def test_rejects_malformed_json_object_fragment():
    malformed = _to_envelope(0, 1, b"not an object", True)
    with pytest.raises(ValueError, match="invalid JSON object fragment"):
        Reassembler().add_chunk(malformed)


if __name__ == "__main__":
    test_reassembles_in_order()
    test_reassembles_out_of_order()
    test_missing_reports_correctly()
    test_checksum_mismatch_raises()
    test_rejects_total_change_and_out_of_range_sequence()
    print("all reassembler tests passed")
