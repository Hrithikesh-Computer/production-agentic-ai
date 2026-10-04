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
    assert set(manager.sessions) == {"response-a", "response-b"}


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
