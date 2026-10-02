import envelope
import pytest
from envelope import WireEnvelope, checksum

AUTH_KEY = b"unit-test-authentication-key"
MESSAGE_ID = "test-message"


def test_valid_envelope_round_trips_through_mapping():
    payload = "hello 🙂".encode("utf-8")
    envelope = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=payload,
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    )

    assert envelope.checksum == checksum(payload)
    assert envelope.verify_authentication(AUTH_KEY)
    assert WireEnvelope.from_mapping(envelope.to_dict()) == envelope


def test_envelope_mapping_has_wire_contract_fields():
    envelope = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=b"payload",
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    )

    assert envelope.to_dict() == {
        "sequence": 0,
        "total_chunks": 1,
        "checksum": checksum(b"payload"),
        "is_final": True,
        "payload": "payload",
        "message_id": MESSAGE_ID,
        "auth_tag": envelope.auth_tag,
        "merge_mode": "concat",
    }


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"sequence": 1}, ValueError, "sequence"),
        ({"total_chunks": 0}, ValueError, "total_chunks"),
        ({"is_final": False}, ValueError, "is_final"),
        ({"merge_mode": "unknown"}, ValueError, "merge_mode"),
        ({"checksum": "not-hex!"}, ValueError, "checksum"),
        ({"payload": 1}, TypeError, "payload"),
    ],
)
def test_envelope_rejects_invalid_fields(changes, error, message):
    values = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=b"payload",
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    ).to_dict()
    values.update(changes)

    with pytest.raises(error, match=message):
        WireEnvelope(**values)


def test_envelope_rejects_invalid_utf8_bytes():
    with pytest.raises(UnicodeDecodeError):
        WireEnvelope.from_bytes(
            sequence=0,
            total_chunks=1,
            payload=b"\xff",
            is_final=True,
            message_id=MESSAGE_ID,
            authentication_key=AUTH_KEY,
        )


def test_envelope_rejects_protocol_size_limits(monkeypatch):
    monkeypatch.setattr(envelope, "MAX_ENVELOPE_CHUNKS", 2)
    with pytest.raises(ValueError, match="protocol maximum"):
        WireEnvelope(
            sequence=0,
            total_chunks=3,
            checksum=checksum(b""),
            is_final=False,
            payload="",
            message_id=MESSAGE_ID,
            auth_tag="0" * 64,
        )

    monkeypatch.setattr(envelope, "MAX_ENVELOPE_PAYLOAD_BYTES", 2)
    with pytest.raises(ValueError, match="protocol maximum"):
        WireEnvelope(
            sequence=0,
            total_chunks=1,
            checksum=checksum(b"abc"),
            is_final=True,
            payload="abc",
            message_id=MESSAGE_ID,
            auth_tag="0" * 64,
        )