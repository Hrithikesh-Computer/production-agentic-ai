import metrics
import ndjson_stream
import pytest
import reassembler as reassembler_module
from envelope import WireEnvelope
from policy import DeliveryPolicy
from reassembler import Reassembler, ReassemblySession, ReassemblySessionManager

AUTH_KEY = b"receiver-observability-test-key"


def _chunk(message_id, sequence, total, payload):
    return WireEnvelope.from_bytes(
        sequence=sequence,
        total_chunks=total,
        payload=payload,
        is_final=sequence == total - 1,
        message_id=message_id,
        authentication_key=AUTH_KEY,
        merge_mode="concat",
    )


def _manager(**kwargs):
    return ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        **kwargs,
    )


def test_receiver_outcome_has_fixed_shape_and_bounded_values():
    event = metrics.ReceiverOutcomeEvent(
        metrics.ReceiverOutcome.AUTHENTICATION_REJECTED
    )

    assert event.as_dict() == {"outcome": "authentication_rejected"}
    assert all(isinstance(outcome.value, str) for outcome in metrics.ReceiverOutcome)


def test_session_and_payload_cap_rejections_emit_outcomes(monkeypatch):
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)
    session_limited = _manager(max_sessions=1)
    assert session_limited.add_chunk(_chunk("held", 0, 2, b"a")) is None
    with pytest.raises(ValueError, match="sessions reached"):
        session_limited.add_chunk(_chunk("other", 0, 2, b"b"))

    byte_limited = _manager(max_total_bytes=97)
    assert byte_limited.add_chunk(_chunk("held-bytes", 0, 2, b"a")) is None
    with pytest.raises(ValueError, match="total active payload bytes"):
        byte_limited.add_chunk(_chunk("over-bytes", 0, 2, b"b"))

    assert events == [
        metrics.ReceiverOutcome.SESSION_CAP_REJECTED,
        metrics.ReceiverOutcome.ACTIVE_PAYLOAD_CAP_REJECTED,
    ]


def test_reassembler_limits_emit_bounded_outcomes(monkeypatch):
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)

    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(authentication_key=AUTH_KEY, max_chunks=1).add_chunk(
            _chunk("too-many", 0, 2, b"a")
        )
    with pytest.raises(ValueError, match="configured maximum"):
        Reassembler(authentication_key=AUTH_KEY, max_payload_bytes=1).add_chunk(
            _chunk("too-large", 0, 2, b"ab")
        )

    assert events == [
        metrics.ReceiverOutcome.MESSAGE_LIMIT_REJECTED,
        metrics.ReceiverOutcome.MESSAGE_LIMIT_REJECTED,
    ]


def test_expiry_and_tombstone_eviction_emit_outcomes(monkeypatch):
    now = [0.0]
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)
    manager = _manager(
        clock=lambda: now[0],
        session_ttl_seconds=2.0,
        max_tombstones=1,
    )
    assert manager.add_chunk(_chunk("expired", 0, 2, b"part")) is None
    now[0] = 2.0
    assert manager.add_chunk(_chunk("active", 0, 2, b"part")) is None
    assert manager.add_chunk(_chunk("done-one", 0, 1, b"done")) == b"done"
    assert manager.add_chunk(_chunk("done-two", 0, 1, b"done")) == b"done"

    assert events == [
        metrics.ReceiverOutcome.SESSION_EXPIRED,
        metrics.ReceiverOutcome.TOMBSTONE_EVICTED,
    ]


def test_authentication_rejection_emits_no_envelope_data(monkeypatch):
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)
    invalid = _chunk("private-message-id", 0, 2, b"private payload").to_dict()
    invalid["auth_tag"] = "0" * 64

    with pytest.raises(ValueError, match="authentication failed"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(invalid)

    assert events == [metrics.ReceiverOutcome.AUTHENTICATION_REJECTED]


def test_tombstoned_replay_rejection_emits_no_eviction_outcome(monkeypatch):
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)
    manager = _manager()
    completed = _chunk("replay", 0, 1, b"complete")
    assert manager.add_chunk(completed) == b"complete"
    sessions_before = manager.sessions.copy()
    tombstones_before = manager.tombstones.copy()
    events.clear()

    with pytest.raises(ValueError, match="tombstoned"):
        manager.add_chunk(completed)

    assert manager.sessions == sessions_before
    assert manager.tombstones == tombstones_before
    assert events == []


def test_checksum_rejection_emits_fixed_integrity_outcome(monkeypatch):
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)
    invalid = _chunk("checksum", 0, 2, b"payload").to_dict()
    invalid["checksum"] = "0" * 8

    with pytest.raises(ValueError, match="checksum mismatch"):
        Reassembler(authentication_key=AUTH_KEY).add_chunk(invalid)

    assert events == [metrics.ReceiverOutcome.ENVELOPE_INTEGRITY_REJECTED]


def test_callback_failures_emit_outcomes_and_propagate(monkeypatch):
    now = [0.0]
    events = []
    monkeypatch.setattr(reassembler_module, "emit_receiver_outcome", events.append)

    def fail_retry(_message_id, _missing):
        raise RuntimeError("retry failed")

    retry_session = ReassemblySession(
        message_id="retry",
        authentication_key=AUTH_KEY,
        request_retry=fail_retry,
        request_full_buffer=lambda _message_id: b"fallback",
        policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=1),
        clock=lambda: now[0],
    )
    assert retry_session.add_chunk(_chunk("retry", 0, 2, b"part")) is None
    now[0] = 1.0
    with pytest.raises(RuntimeError, match="retry failed"):
        retry_session.poll_timeout()

    def fail_full_buffer(_message_id):
        raise RuntimeError("fallback failed")

    fallback_session = ReassemblySession(
        message_id="fallback",
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=fail_full_buffer,
        policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=0),
        clock=lambda: now[0],
    )
    assert fallback_session.add_chunk(_chunk("fallback", 0, 2, b"part")) is None
    now[0] = 2.0
    with pytest.raises(RuntimeError, match="fallback failed"):
        fallback_session.poll_timeout()

    assert events == [
        metrics.ReceiverOutcome.RETRY_CALLBACK_FAILED,
        metrics.ReceiverOutcome.FULL_BUFFER_CALLBACK_FAILED,
    ]


def test_decoder_poison_emits_outcome_but_discard_does_not(monkeypatch):
    events = []
    monkeypatch.setattr(ndjson_stream, "emit_receiver_outcome", events.append)
    decoder = ndjson_stream.NDJSONDecoder()
    with pytest.raises(ValueError):
        decoder.feed(b"not-json\n")
    assert decoder.failed

    ndjson_stream.NDJSONDecoder().discard()
    assert events == [metrics.ReceiverOutcome.NDJSON_DECODER_POISONED]