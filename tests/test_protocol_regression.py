import inspect
import sys
from pathlib import Path

import pytest

PACKAGE = (
    Path(__file__).resolve().parents[1]
    / "04-reference-implementation"
    / "adaptive-response-filter"
)
sys.path.insert(0, str(PACKAGE))

from envelope import WireEnvelope  # noqa: E402
from filter import AdaptiveResponseFilter  # noqa: E402
from ndjson_stream import NDJSONDecoder, NDJSONError, RecordTooLargeError  # noqa: E402
from policy import DeliveryPolicy  # noqa: E402
from reassembler import Reassembler, ReassemblySessionManager  # noqa: E402

AUTH_KEY = b"desired-regression-auth-key"


def build_envelope(
    *,
    message_id: str,
    sequence: int = 0,
    total_chunks: int = 2,
    payload: bytes = b"payload",
) -> WireEnvelope:
    return WireEnvelope.from_bytes(
        sequence=sequence,
        total_chunks=total_chunks,
        payload=payload,
        is_final=sequence == total_chunks - 1,
        message_id=message_id,
        authentication_key=AUTH_KEY,
        merge_mode="concat",
    )


def make_manager(*, clock=lambda: 0.0, policy=None, **kwargs):
    return ReassemblySessionManager(
        authentication_key=AUTH_KEY,
        request_retry=lambda _message_id, _missing: None,
        request_full_buffer=lambda _message_id: b"fallback",
        clock=clock,
        policy=policy or DeliveryPolicy(timeout_seconds=2.0, max_retries=1),
        **kwargs,
    )


# R1: authenticate before manager insertion so an invalid tag retains no session.
def test_bad_tag_leaves_no_session_in_manager():
    manager = make_manager()
    envelope = build_envelope(message_id="bad-tag").to_dict()
    envelope["auth_tag"] = "0" * 64

    with pytest.raises(ValueError, match="authentication failed"):
        manager.add_chunk(envelope)

    assert len(manager.sessions) == 0


# R2: add and enforce max_sessions before admitting a cap+1 distinct message.
def test_manager_rejects_sessions_beyond_cap():
    parameters = inspect.signature(ReassemblySessionManager).parameters
    assert "max_sessions" in parameters, (
        "ReassemblySessionManager has no max_sessions constructor parameter"
    )

    cap = 2
    manager = make_manager(max_sessions=cap)
    for index in range(cap):
        assert (
            manager.add_chunk(
                build_envelope(message_id=f"cap-{index}", sequence=0, total_chunks=2)
            )
            is None
        )

    with pytest.raises(ValueError, match="session|maximum|cap"):
        manager.add_chunk(
            build_envelope(message_id="over-cap", sequence=0, total_chunks=2)
        )
    assert len(manager.sessions) == cap


# R3: evict expired incomplete sessions lazily during the next manager intake.
def test_abandoned_sessions_are_evicted_after_ttl():
    now = [0.0]
    manager = make_manager(clock=lambda: now[0], session_ttl_seconds=2.0)
    assert (
        manager.add_chunk(
            build_envelope(message_id="abandoned", sequence=0, total_chunks=2)
        )
        is None
    )
    assert "abandoned" in manager.sessions

    now[0] = 3.0
    manager.add_chunk(
        build_envelope(message_id="new-message", sequence=0, total_chunks=2)
    )

    assert "abandoned" not in manager.sessions


# R4: bind chunks to one logical message so ID reuse cannot mix payload fragments.
@pytest.mark.xfail(strict=True, reason="needs lifecycle work / protocol decision")
def test_reused_message_id_cannot_mix_payloads():
    manager = make_manager()
    first = build_envelope(
        message_id="reused", sequence=0, total_chunks=2, payload=b"old-"
    )
    second = build_envelope(
        message_id="reused", sequence=1, total_chunks=2, payload=b"new"
    )

    assert manager.add_chunk(first) is None
    try:
        result = manager.add_chunk(second)
    except ValueError:
        return

    assert result != b"old-new", "distinct logical messages were silently combined"


# R5: interpret threshold equality as chunked, matching should_chunk's >= predicate.
def test_threshold_boundary_is_documented_behavior():
    result = AdaptiveResponseFilter(
        threshold_bytes=4,
        max_chunk_bytes=2,
        authentication_key=AUTH_KEY,
    ).build("abcd")

    assert result.mode == "chunked"
    assert result.chunks


# R6: reject keys shorter than the assumed minimum of 16 bytes.
def test_short_key_is_rejected():
    with pytest.raises(ValueError, match="16|key|authentication"):
        Reassembler(authentication_key=b"x")


# R7: process oversized feeds incrementally so pending never exceeds the record cap.
def test_feed_large_input_never_buffers_more_than_max_record_bytes():
    high_water = []

    class TrackingBytearray(bytearray):
        def extend(self, data):
            super().extend(data)
            high_water.append(len(self))

    decoder = NDJSONDecoder()
    decoder._pending = TrackingBytearray()
    data = b"x" * (10 * 1024 * 1024)

    with pytest.raises(RecordTooLargeError):
        decoder.feed(data)

    measured = max(high_water, default=0)
    assert measured <= decoder._max, (
        f"pending high-water was {measured}, limit is {decoder._max}"
    )


# R8: reject Python's non-standard NaN and infinity constants at the NDJSON boundary.
def test_decoder_rejects_nonstandard_json_constants():
    accepted = []
    for token in ("NaN", "Infinity", "-Infinity"):
        decoder = NDJSONDecoder()
        try:
            decoder.feed((f'{{"value":{token}}}\n').encode("ascii"))
        except NDJSONError:
            continue
        accepted.append(token)

    assert not accepted, f"accepted non-standard JSON constants: {accepted}"


# R9: reject duplicate object names instead of silently selecting the last value.
def test_decoder_rejects_duplicate_object_names():
    decoder = NDJSONDecoder()
    with pytest.raises(NDJSONError):
        decoder.feed(b'{"a":1,"a":2}\n')


# R10: normalize extreme nesting failures into the decoder's NDJSON error family.
def test_deep_nesting_raises_ndjson_error_not_recursion_error():
    decoder = NDJSONDecoder()
    record = b"[" * 100_000 + b"0" + b"]" * 100_000 + b"\n"

    with pytest.raises(NDJSONError) as caught:
        decoder.feed(record)

    assert not isinstance(caught.value, RecursionError)
    assert decoder.failed
