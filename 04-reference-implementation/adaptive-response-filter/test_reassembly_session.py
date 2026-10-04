from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from envelope import WireEnvelope
from policy import DeliveryPolicy
from reassembler import ReassemblySession, ReassemblySessionManager

AUTH_KEY = b"unit-test-authentication-key"


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


def _held_payload_bytes(manager):
    return sum(
        session.reassembler._received_bytes
        for session in manager.sessions.values()
    )


def test_missing_chunk_retries_then_falls_back_to_full_buffer():
    now = [0.0]
    retry_requests = []
    full_buffer_requests = []
    session = ReassemblySession(
        message_id="response-1",
        authentication_key=AUTH_KEY,
        request_retry=lambda message_id, missing: retry_requests.append(
            (message_id, missing)
        ),
        request_full_buffer=lambda message_id: (
            full_buffer_requests.append(message_id) or b"complete response"
        ),
        policy=DeliveryPolicy(timeout_seconds=2.0, max_retries=1),
        clock=lambda: now[0],
    )

    assert session.add_chunk(_chunk("response-1", 0, 2, b"partial ")) is None
    now[0] = 2.0
    assert session.poll_timeout() is None
    assert retry_requests == [("response-1", [1])]
    assert full_buffer_requests == []

    now[0] = 4.0
    assert session.poll_timeout() == b"complete response"
    assert full_buffer_requests == ["response-1"]
    assert session.fallback_result == b"complete response"


def test_manager_keeps_two_in_flight_messages_separate():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda message_id: message_id.encode(),
    )

    assert manager.add_chunk(_chunk("response-a", 0, 2, b"A")) is None
    assert manager.add_chunk(_chunk("response-b", 0, 2, b"B")) is None
    assert manager.add_chunk(_chunk("response-a", 1, 2, b"1")) == b"A1"
    assert manager.add_chunk(_chunk("response-b", 1, 2, b"2")) == b"B2"
    assert manager.sessions == {}
    assert set(manager.tombstones) == {"response-a", "response-b"}


def test_manager_concurrent_first_chunks_can_lose_one_chunk(monkeypatch):
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
    )
    both_sessions_created = Barrier(2)
    original_post_init = ReassemblySession.__post_init__

    def synchronized_post_init(session):
        original_post_init(session)
        both_sessions_created.wait(timeout=5)

    monkeypatch.setattr(ReassemblySession, "__post_init__", synchronized_post_init)
    chunks = (
        _chunk("racing", 0, 2, b"first"),
        _chunk("racing", 1, 2, b"second"),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(manager.add_chunk, chunks))

    assert results == [None, None]
    retained = manager.sessions["racing"].reassembler.received
    assert len(retained) == 1
    assert next(iter(retained.values())) in {b"first", b"second"}


def test_manager_rejects_late_chunk_for_completed_message():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
    )
    completed = _chunk("complete", 0, 1, b"done")

    assert manager.add_chunk(completed) == b"done"
    try:
        manager.add_chunk(completed)
    except ValueError as error:
        assert "tombstoned" in str(error)
    else:
        raise AssertionError("manager accepted a late chunk for a completed id")


def test_manager_allows_message_id_after_tombstone_expiry():
    now = [0.0]
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        tombstone_ttl_seconds=5.0,
        clock=lambda: now[0],
    )
    assert manager.add_chunk(_chunk("reusable", 0, 1, b"old")) == b"old"

    now[0] = 5.0
    assert manager.add_chunk(_chunk("reusable", 0, 2, b"new-")) is None
    assert "reusable" in manager.sessions
    assert "reusable" not in manager.tombstones


def test_manager_evicts_oldest_tombstone_at_capacity():
    now = [0.0]
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_tombstones=2,
        clock=lambda: now[0],
    )

    for message_id in ("first", "second", "third"):
        assert manager.add_chunk(_chunk(message_id, 0, 1, message_id.encode()))
        now[0] += 1.0

    assert list(manager.tombstones) == ["second", "third"]
    assert len(manager.tombstones) == 2


def test_manager_growth_stays_within_session_and_tombstone_caps():
    now = [0.0]
    max_sessions = 4
    max_tombstones = 3
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_sessions=max_sessions,
        session_ttl_seconds=2.0,
        max_tombstones=max_tombstones,
        tombstone_ttl_seconds=100.0,
        clock=lambda: now[0],
    )
    peak_sessions = 0
    peak_tombstones = 0

    for index in range(max_sessions * 10):
        if len(manager.sessions) >= max_sessions:
            now[0] += 2.1

        bad = _chunk(f"bad-{index}", 0, 2, b"bad").to_dict()
        bad["auth_tag"] = "0" * 64
        try:
            manager.add_chunk(bad)
        except ValueError as error:
            assert "authentication failed" in str(error)
        else:
            raise AssertionError("manager accepted a bad-tag envelope")

        assert manager.add_chunk(_chunk(f"abandoned-{index}", 0, 2, b"part")) is None
        peak_sessions = max(peak_sessions, len(manager.sessions))
        assert len(manager.sessions) <= max_sessions
        assert len(manager.tombstones) <= max_tombstones

    now[0] += 2.1
    for index in range(max_tombstones * 10):
        message_id = f"completed-{index}"
        assert manager.add_chunk(_chunk(message_id, 0, 1, b"done")) == b"done"
        peak_sessions = max(peak_sessions, len(manager.sessions))
        peak_tombstones = max(peak_tombstones, len(manager.tombstones))
        assert len(manager.sessions) <= max_sessions
        assert len(manager.tombstones) <= max_tombstones

    assert peak_sessions == max_sessions
    assert peak_tombstones == max_tombstones


def test_manager_preserves_partial_session_after_bad_chunk_and_accepts_retry():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
    )
    first = _chunk("response-retry", 0, 2, b"old-")
    assert manager.add_chunk(first) is None

    bad_final = _chunk("response-retry", 1, 2, b"new").to_dict()
    bad_final["auth_tag"] = "0" * 64
    try:
        manager.add_chunk(bad_final)
    except ValueError as error:
        assert "authentication failed" in str(error)
    else:
        raise AssertionError("manager accepted a chunk with a bad authentication tag")

    assert set(manager.sessions) == {"response-retry"}
    assert manager.sessions["response-retry"].reassembler.received == {0: b"old-"}
    assert manager.add_chunk(_chunk("response-retry", 1, 2, b"new")) == b"old-new"


def test_manager_accepts_existing_session_when_at_capacity():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_sessions=1,
    )

    assert manager.add_chunk(_chunk("active", 0, 2, b"part-")) is None
    assert manager.add_chunk(_chunk("active", 1, 2, b"done")) == b"part-done"


def test_session_ttl_uses_last_activity_deadline():
    now = [0.0]
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        session_ttl_seconds=5.0,
        clock=lambda: now[0],
    )

    assert manager.add_chunk(_chunk("active", 0, 3, b"first")) is None
    now[0] = 4.0
    assert manager.add_chunk(_chunk("active", 1, 3, b"second")) is None
    now[0] = 8.0
    assert manager.add_chunk(_chunk("new", 0, 2, b"new")) is None
    assert "active" in manager.sessions
    now[0] = 9.0
    assert manager.add_chunk(_chunk("later", 0, 2, b"later")) is None
    assert "active" not in manager.sessions


def test_session_rejects_chunk_for_another_message():
    session = ReassemblySession(
        message_id="expected",
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
    )

    try:
        session.add_chunk(_chunk("different", 0, 1, b"payload"))
    except ValueError as error:
        assert "message_id" in str(error)
    else:
        raise AssertionError("session accepted a chunk for another message")


def test_session_rejects_empty_message_id():
    try:
        ReassemblySession(
            message_id="",
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: None,
            request_full_buffer=lambda _message_id: b"fallback",
        )
    except ValueError as error:
        assert "message_id must be non-empty" in str(error)
    else:
        raise AssertionError("session accepted an empty message_id")


def test_total_byte_cap_rejection_leaves_manager_state_unchanged():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_total_bytes=5,
        clock=lambda: 0.0,
    )
    assert manager.add_chunk(_chunk("held", 0, 2, b"1234")) is None
    sessions_before = {
        message_id: session.reassembler.received.copy()
        for message_id, session in manager.sessions.items()
    }
    activity_before = manager._session_activity.copy()
    tombstones_before = manager.tombstones.copy()

    with pytest.raises(ValueError, match="total active payload bytes"):
        manager.add_chunk(_chunk("over", 0, 2, b"xy"))

    assert _held_payload_bytes(manager) == 4
    assert {
        message_id: session.reassembler.received.copy()
        for message_id, session in manager.sessions.items()
    } == sessions_before
    assert manager._session_activity == activity_before
    assert manager.tombstones == tombstones_before


def test_total_byte_cap_retries_same_chunk_after_expiry_frees_bytes():
    now = [0.0]
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_total_bytes=5,
        session_ttl_seconds=2.0,
        clock=lambda: now[0],
    )
    assert manager.add_chunk(_chunk("held", 0, 2, b"1234")) is None
    candidate = _chunk("candidate", 0, 2, b"xy")

    with pytest.raises(ValueError, match="total active payload bytes"):
        manager.add_chunk(candidate)
    assert _held_payload_bytes(manager) == 4

    now[0] = 2.0
    assert manager.add_chunk(candidate) is None
    assert set(manager.sessions) == {"candidate"}
    assert _held_payload_bytes(manager) == 2


def test_identical_duplicate_near_total_byte_cap_does_not_count_twice():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_total_bytes=2,
        clock=lambda: 0.0,
    )
    chunk = _chunk("duplicate", 0, 2, b"xy")

    assert manager.add_chunk(chunk) is None
    assert _held_payload_bytes(manager) == 2
    assert manager.add_chunk(chunk) is None
    assert _held_payload_bytes(manager) == 2


def test_completion_releases_bytes_for_another_message():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_total_bytes=4,
        clock=lambda: 0.0,
    )

    assert manager.add_chunk(_chunk("complete", 0, 2, b"ab")) is None
    assert _held_payload_bytes(manager) == 2
    assert manager.add_chunk(_chunk("complete", 1, 2, b"cd")) == b"abcd"
    assert manager.sessions == {}
    assert _held_payload_bytes(manager) == 0
    assert manager.add_chunk(_chunk("next", 0, 1, b"1234")) == b"1234"
    assert _held_payload_bytes(manager) == 0


def test_bad_tag_does_not_change_total_payload_bytes():
    manager = ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        max_total_bytes=3,
        clock=lambda: 0.0,
    )
    assert manager.add_chunk(_chunk("valid", 0, 2, b"ab")) is None
    before = manager._session_activity.copy()
    bad = _chunk("bad", 0, 2, b"xxxx").to_dict()
    bad["auth_tag"] = "0" * 64

    with pytest.raises(ValueError, match="authentication failed"):
        manager.add_chunk(bad)

    assert _held_payload_bytes(manager) == 2
    assert set(manager.sessions) == {"valid"}
    assert manager._session_activity == before


@pytest.mark.parametrize("limit", [0, -1])
def test_manager_rejects_nonpositive_total_byte_cap(limit):
    with pytest.raises(ValueError, match="max_total_bytes must be positive"):
        ReassemblySessionManager(
            authentication_key=AUTH_KEY,
            request_retry=lambda _message_id, _missing: None,
            request_full_buffer=lambda _message_id: b"fallback",
            max_total_bytes=limit,
        )
