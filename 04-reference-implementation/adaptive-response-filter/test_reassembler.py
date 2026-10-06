import json

import pytest
from chunker import semantic_split
from envelope import WireEnvelope, checksum
from filter import AdaptiveResponseFilter
from middleware import filter_response
from policy import DeliveryPolicy
from reassembler import Reassembler

AUTH_KEY = b"unit-test-authentication-key"


def _to_envelope(sequence, total, payload, is_final, merge_mode="json-object"):
    return WireEnvelope.from_bytes(
        sequence=sequence,
        total_chunks=total,
        payload=payload,
        is_final=is_final,
        message_id="test-message",
        authentication_key=AUTH_KEY,
        merge_mode=merge_mode,
    ).to_dict()


def test_reassembles_in_order():
    payload = json.dumps({"a": "x" * 100, "b": "y" * 100}).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=110)
    envelopes = [
        _to_envelope(i, len(chunks), chunk, i == len(chunks) - 1)
        for i, chunk in enumerate(chunks)
    ]

    reassembler = Reassembler(authentication_key=AUTH_KEY)
    result = None
    for envelope in envelopes:
        result = reassembler.add_chunk(envelope)

    assert result is not None
    assert json.loads(result) == json.loads(payload)


def test_reassembles_out_of_order():
    payload = json.dumps({"a": "x" * 100, "b": "y" * 100}).encode("utf-8")
    chunks = semantic_split(payload, max_chunk_bytes=110)
    envelopes = [
        _to_envelope(i, len(chunks), chunk, i == len(chunks) - 1)
        for i, chunk in enumerate(chunks)
    ]

    reassembler = Reassembler(authentication_key=AUTH_KEY)
    result = None
    for envelope in reversed(envelopes):
        result = reassembler.add_chunk(envelope)

    assert result is not None
    assert json.loads(result) == json.loads(payload)


def test_checksum_mismatch_raises():
    bad_envelope = _to_envelope(0, 1, b'{"a": 1}', True)
    bad_envelope["checksum"] = "deadbeef"

    with pytest.raises(ValueError, match="checksum mismatch"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(bad_envelope)


def test_hmac_rejects_tampering_even_if_crc_is_recomputed():
    envelope = _to_envelope(0, 1, b'{"a": 1}', True)
    envelope["payload"] = '{"a": 2}'
    envelope["checksum"] = checksum(envelope["payload"].encode("utf-8"))

    reassembler = Reassembler(authentication_key=AUTH_KEY)
    with pytest.raises(ValueError, match="authentication failed"):
        reassembler.add_chunk(envelope)
    assert reassembler.total_chunks is None


def test_hmac_rejects_message_id_tampering():
    envelope = _to_envelope(0, 1, b'{"a": 1}', True)
    envelope["message_id"] = "different-message"

    with pytest.raises(ValueError, match="authentication failed"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(envelope)


def test_reassembler_rejects_message_id_change_without_mutating_state():
    reassembler = Reassembler(authentication_key=AUTH_KEY)
    first = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=2,
        payload=b"first",
        is_final=False,
        message_id="first-message",
        authentication_key=AUTH_KEY,
        merge_mode="concat",
    )
    different_id = WireEnvelope.from_bytes(
        sequence=1,
        total_chunks=2,
        payload=b"second",
        is_final=True,
        message_id="different-message",
        authentication_key=AUTH_KEY,
        merge_mode="concat",
    )

    assert reassembler.add_chunk(first) is None
    state_before = (
        reassembler.received.copy(),
        reassembler.total_chunks,
        reassembler._received_bytes,
        reassembler.merge_mode,
        reassembler.message_id,
        reassembler.missing(),
    )

    with pytest.raises(ValueError, match="message_id"):
        reassembler.add_chunk(different_id)

    assert (
        reassembler.received,
        reassembler.total_chunks,
        reassembler._received_bytes,
        reassembler.merge_mode,
        reassembler.message_id,
        reassembler.missing(),
    ) == state_before


def test_reassembler_rejects_authentication_key_shorter_than_16_bytes():
    with pytest.raises(ValueError, match="16"):
        Reassembler(authentication_key=b"x" * 15)


@pytest.mark.parametrize(
    ("options", "error", "message"),
    [
        ({"max_chunks": True}, TypeError, "max_chunks must be an integer"),
        ({"max_chunks": 0}, ValueError, "max_chunks must be positive"),
        (
            {"max_payload_bytes": "large"},
            TypeError,
            "max_payload_bytes must be an integer",
        ),
        ({"max_payload_bytes": 0}, ValueError, "max_payload_bytes must be positive"),
    ],
)
def test_reassembler_rejects_invalid_resource_limits(options, error, message):
    with pytest.raises(error, match=message):
        Reassembler(authentication_key=AUTH_KEY, **options)


def test_missing_reports_correctly():
    reassembler = Reassembler(authentication_key=AUTH_KEY)
    reassembler.add_chunk(_to_envelope(0, 3, b'{"a": 1}', False))
    assert reassembler.missing() == [1, 2]


def test_identical_duplicate_is_idempotent_and_conflict_is_rejected():
    reassembler = Reassembler(authentication_key=AUTH_KEY)
    first = _to_envelope(0, 2, b'{"a": 1}', False)

    assert reassembler.add_chunk(first) is None
    assert reassembler.add_chunk(first) is None
    with pytest.raises(ValueError, match="conflicting duplicate"):
        reassembler.add_chunk(_to_envelope(0, 2, b'{"a": 2}', False))
    assert reassembler.missing() == [1]


def test_rejects_total_change_and_out_of_range_sequence():
    reassembler = Reassembler(authentication_key=AUTH_KEY)
    reassembler.add_chunk(_to_envelope(0, 2, b'{"a": 1}', False))

    with pytest.raises(ValueError, match="total_chunks"):
        reassembler.add_chunk(_to_envelope(1, 3, b'{"b": 2}', False))

    with pytest.raises(ValueError, match="sequence"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(
            _to_envelope(2, 1, b'{"a": 1}', True)
        )


def test_rejects_invalid_merge_mode_before_storing_chunk():
    invalid = _to_envelope(0, 1, b"payload", True)
    invalid["merge_mode"] = "unknown"
    reassembler = Reassembler(authentication_key=AUTH_KEY)

    with pytest.raises(ValueError, match="merge_mode"):
        reassembler.add_chunk(invalid)
    assert reassembler.total_chunks is None


def test_filter_api_authenticates_reassembled_payload():
    payload = "plain text with 🙂 content" * 4
    result = AdaptiveResponseFilter(
        threshold_bytes=1,
        max_chunk_bytes=16,
        authentication_key=AUTH_KEY,
    ).build(payload)
    reassembler = Reassembler(authentication_key=AUTH_KEY)

    assembled = None
    for chunk in result.chunks:
        assembled = reassembler.add_chunk(chunk)

    assert assembled == payload.encode("utf-8")


def test_filter_api_returns_full_result_below_threshold():
    result = AdaptiveResponseFilter(
        threshold_bytes=100,
        authentication_key=AUTH_KEY,
    ).build("small")

    assert result.mode == "full"
    assert result.payload == "small"
    assert result.chunks == []


def test_filter_api_threshold_boundary_modes():
    response_filter = AdaptiveResponseFilter(
        threshold_bytes=4,
        max_chunk_bytes=2,
        authentication_key=AUTH_KEY,
    )

    empty = response_filter.build("")
    below = response_filter.build("abc")
    exact = response_filter.build("abcd")
    above = response_filter.build("abcde")

    assert empty.mode == "full"
    assert below.mode == "full"
    assert exact.mode == "chunked"
    assert above.mode == "chunked"
    assert exact.chunks
    assert above.chunks


def test_middleware_full_buffer_path_emits_authenticated_envelope():
    envelopes = list(
        filter_response(
            "small",
            DeliveryPolicy(threshold_bytes=100),
            authentication_key=AUTH_KEY,
        )
    )

    assert len(envelopes) == 1
    assert envelopes[0]["total_chunks"] == 1
    assert envelopes[0]["payload"] == '"small"'
    assert envelopes[0]["auth_tag"]


def test_middleware_emits_delivery_metrics(monkeypatch):
    emitted = []
    monkeypatch.setattr("middleware.emit", emitted.append)

    list(
        filter_response(
            "small",
            DeliveryPolicy(threshold_bytes=100),
            authentication_key=AUTH_KEY,
        )
    )

    assert len(emitted) == 1
    assert emitted[0].as_dict()["payload_size"] == len(b'"small"')
    assert emitted[0].as_dict()["chunk_count"] == 1


def test_middleware_reassembles_non_object_json():
    response = ["alpha", "🙂", {"nested": True}]
    envelopes = list(
        filter_response(
            response,
            DeliveryPolicy(threshold_bytes=1, max_chunk_bytes=8),
            authentication_key=AUTH_KEY,
        )
    )
    reassembler = Reassembler(authentication_key=AUTH_KEY)

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
            authentication_key=AUTH_KEY,
        )
    )
    reassembler = Reassembler(authentication_key=AUTH_KEY)

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
            authentication_key=AUTH_KEY,
        )
    )
    reassembler = Reassembler(authentication_key=AUTH_KEY)

    assembled = None
    for envelope in envelopes:
        assembled = reassembler.add_chunk(envelope)

    assert assembled is not None
    assert json.loads(assembled) == response


def test_rejects_chunk_count_and_payload_over_configured_limits():
    oversized_count = _to_envelope(0, 2, b"x", False)
    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(authentication_key=AUTH_KEY, max_chunks=1).add_chunk(
            oversized_count
        )

    oversized_payload = _to_envelope(
        0,
        1,
        b"payload",
        True,
        merge_mode="concat",
    )
    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(
            authentication_key=AUTH_KEY,
            max_payload_bytes=4,
        ).add_chunk(oversized_payload)


def test_reassembler_rejects_second_message_after_completion():
    reassembler = Reassembler(authentication_key=AUTH_KEY)
    completed_message = _to_envelope(0, 1, b'{"a": 1}', True)

    assert reassembler.add_chunk(completed_message) is not None
    with pytest.raises(ValueError, match="one message"):
        reassembler.add_chunk(completed_message)


def test_rejects_malformed_json_object_fragment():
    malformed = _to_envelope(0, 1, b"not an object", True)
    with pytest.raises(ValueError, match="invalid JSON object fragment"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(malformed)

def test_delivery_policy_rejects_invalid_limits():
    with pytest.raises(ValueError, match="max_chunk_bytes"):
        DeliveryPolicy(max_chunk_bytes=0)

def test_delivery_policy_rejects_invalid_recovery_limits():
    with pytest.raises(ValueError, match="timeout_seconds"):
        DeliveryPolicy(timeout_seconds=0)
    with pytest.raises(ValueError, match="max_retries"):
        DeliveryPolicy(max_retries=-1)
