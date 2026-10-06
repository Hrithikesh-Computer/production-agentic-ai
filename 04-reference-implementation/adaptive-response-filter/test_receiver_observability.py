import metrics
import ndjson_stream
import pytest
import reassembler as reassembler_module
from envelope import WireEnvelope
from policy import DeliveryPolicy
from reassembler import Reassembler, ReassemblySession, ReassemblySessionManager

AUTH_KEY = b"receiver-observability-test-key"


def _snapshot_outcome_state(reassembler_state):
    return {
        "received": reassembler_state.received.copy(),
        "received_bytes": reassembler_state._received_bytes,
        "completed": reassembler_state.completed,
        "total_chunks": reassembler_state.total_chunks,
    }


def _snapshot_manager_state(manager):
    return {
        "sessions": {
            message_id: _snapshot_session_state(session)
            for message_id, session in manager.sessions.items()
        },
        "tombstones": manager.tombstones.copy(),
        "session_activity": manager._session_activity.copy(),
        "active_memory_bytes": manager.active_memory_bytes,
    }


def _snapshot_session_state(session):
    return {
        "retries": session.retries,
        "fallback_result": session.fallback_result,
        "deadline": session._deadline,
        "reassembler": _snapshot_outcome_state(session.reassembler),
    }


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


def _invoke_outcome_with_sink(sink, outcome):
    reassembler_module.emit_receiver_outcome(outcome, sink=sink)


def test_outcome_sink_failures_preserve_original_control_flow_and_state(monkeypatch):
    def fail_sink(_payload):
        raise RuntimeError("sink failed")

    original_helper = reassembler_module.emit_receiver_outcome

    def run_noop_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0])
        assert manager.add_chunk(_chunk("ok", 0, 1, b"ok")) == b"ok"
        return _snapshot_manager_state(manager)

    def run_failing_sink_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0])
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        assert manager.add_chunk(_chunk("ok", 0, 1, b"ok")) == b"ok"
        return _snapshot_manager_state(manager)

    noop_state = run_noop_case()
    failing_sink_state = run_failing_sink_case()
    assert noop_state["sessions"] == failing_sink_state["sessions"]
    assert noop_state["tombstones"] == failing_sink_state["tombstones"]
    assert noop_state["session_activity"] == failing_sink_state["session_activity"]
    assert (
        noop_state["active_memory_bytes"]
        == failing_sink_state["active_memory_bytes"]
    )

    def _state_for_session_cap(manager):
        return {
            "session_ids": tuple(manager.sessions),
            "session_state": {
                message_id: _snapshot_session_state(session)
                for message_id, session in manager.sessions.items()
            },
            "tombstones": manager.tombstones.copy(),
            "active_memory_bytes": manager.active_memory_bytes,
        }

    def run_noop_rejection_case():
        invalid = _chunk("private-message-id", 0, 2, b"private payload").to_dict()
        invalid["auth_tag"] = "0" * 64
        manager = _manager()
        with pytest.raises(ValueError, match="authentication failed"):
            manager.add_chunk(invalid)
        return _snapshot_manager_state(manager)

    def run_failing_rejection_case():
        invalid = _chunk("private-message-id", 0, 2, b"private payload").to_dict()
        invalid["auth_tag"] = "0" * 64
        manager = _manager()
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(ValueError, match="authentication failed"):
            manager.add_chunk(invalid)
        return _snapshot_manager_state(manager)

    assert run_noop_rejection_case() == run_failing_rejection_case()

    def run_session_cap_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0], max_sessions=1)
        manager.add_chunk(_chunk("held", 0, 2, b"a"))
        with pytest.raises(ValueError, match="maximum reassembly sessions reached"):
            manager.add_chunk(_chunk("other", 0, 2, b"b"))
        return _state_for_session_cap(manager)

    def run_session_cap_failing_sink_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0], max_sessions=1)
        manager.add_chunk(_chunk("held", 0, 2, b"a"))
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(ValueError, match="maximum reassembly sessions reached"):
            manager.add_chunk(_chunk("other", 0, 2, b"b"))
        return _state_for_session_cap(manager)

    assert run_session_cap_case() == run_session_cap_failing_sink_case()

    def run_limit_and_crc_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0], max_total_bytes=97)
        manager.add_chunk(_chunk("held", 0, 2, b"a"))
        with pytest.raises(ValueError, match="total active payload bytes"):
            manager.add_chunk(_chunk("over", 0, 2, b"b"))
        invalid = _chunk("checksum", 0, 2, b"payload").to_dict()
        invalid["checksum"] = "0" * 8
        with pytest.raises(ValueError, match="checksum mismatch"):
            Reassembler(authentication_key=AUTH_KEY).add_chunk(invalid)
        return _snapshot_manager_state(manager)

    def run_limit_and_crc_failing_sink_case():
        now = [0.0]
        manager = _manager(clock=lambda: now[0], max_total_bytes=97)
        manager.add_chunk(_chunk("held", 0, 2, b"a"))
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(ValueError, match="total active payload bytes"):
            manager.add_chunk(_chunk("over", 0, 2, b"b"))
        invalid = _chunk("checksum", 0, 2, b"payload").to_dict()
        invalid["checksum"] = "0" * 8
        with pytest.raises(ValueError, match="checksum mismatch"):
            Reassembler(authentication_key=AUTH_KEY).add_chunk(invalid)
        return _snapshot_manager_state(manager)

    assert run_limit_and_crc_case() == run_limit_and_crc_failing_sink_case()

    def run_ndjson_case():
        decoder = ndjson_stream.NDJSONDecoder()
        with pytest.raises(ValueError):
            decoder.feed(b"not-json\n")
        return decoder.failed, decoder._pending

    def run_ndjson_failing_sink_case():
        decoder = ndjson_stream.NDJSONDecoder()
        monkeypatch.setattr(
            ndjson_stream,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(ValueError):
            decoder.feed(b"not-json\n")
        return decoder.failed, decoder._pending

    assert run_ndjson_case() == run_ndjson_failing_sink_case()

    def run_retry_case():
        now = [0.0]
        session = ReassemblySession(
            message_id="retry-noop",
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: (_ for _ in ()).throw(
                RuntimeError("callback failed")
            ),
            request_full_buffer=lambda _message_id: b"fallback",
            policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=1),
            clock=lambda: now[0],
        )
        session.add_chunk(_chunk("retry-noop", 0, 2, b"part"))
        now[0] = 1.0
        with pytest.raises(RuntimeError, match="callback failed"):
            session.poll_timeout()
        return _snapshot_session_state(session)

    def run_retry_failing_sink_case():
        now = [0.0]
        session = ReassemblySession(
            message_id="retry-failing",
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: (_ for _ in ()).throw(
                RuntimeError("callback failed")
            ),
            request_full_buffer=lambda _message_id: b"fallback",
            policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=1),
            clock=lambda: now[0],
        )
        session.add_chunk(_chunk("retry-failing", 0, 2, b"part"))
        now[0] = 1.0
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(RuntimeError, match="callback failed"):
            session.poll_timeout()
        return _snapshot_session_state(session)

    assert run_retry_case() == run_retry_failing_sink_case()

    def run_full_buffer_case():
        now = [0.0]
        session = ReassemblySession(
            message_id="fallback-noop",
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: None,
            request_full_buffer=lambda _message_id: (_ for _ in ()).throw(
                RuntimeError("fallback failed")
            ),
            policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=0),
            clock=lambda: now[0],
        )
        session.add_chunk(_chunk("fallback-noop", 0, 2, b"part"))
        now[0] = 2.0
        with pytest.raises(RuntimeError, match="fallback failed"):
            session.poll_timeout()
        return _snapshot_session_state(session)

    def run_full_buffer_failing_sink_case():
        now = [0.0]
        session = ReassemblySession(
            message_id="fallback-failing",
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: None,
            request_full_buffer=lambda _message_id: (_ for _ in ()).throw(
                RuntimeError("fallback failed")
            ),
            policy=DeliveryPolicy(timeout_seconds=1.0, max_retries=0),
            clock=lambda: now[0],
        )
        session.add_chunk(_chunk("fallback-failing", 0, 2, b"part"))
        now[0] = 2.0
        monkeypatch.setattr(
            reassembler_module,
            "emit_receiver_outcome",
            lambda outcome, sink=fail_sink: original_helper(outcome, sink),
        )
        with pytest.raises(RuntimeError, match="fallback failed"):
            session.poll_timeout()
        return _snapshot_session_state(session)

    assert run_full_buffer_case() == run_full_buffer_failing_sink_case()


def test_outcome_sink_failures_do_not_swallow_keyboard_interrupt_or_system_exit():
    for failure in (KeyboardInterrupt("stop"), SystemExit(2)):
        with pytest.raises(type(failure), match=str(failure)):
            reassembler_module.emit_receiver_outcome(
                metrics.ReceiverOutcome.SESSION_CAP_REJECTED,
                sink=lambda _payload: (_ for _ in ()).throw(failure),
            )