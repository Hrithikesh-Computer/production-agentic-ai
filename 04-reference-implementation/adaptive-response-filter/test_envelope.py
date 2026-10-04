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


@pytest.mark.parametrize(
    ("field", "value", "error", "message"),
    [
        ("total_chunks", "one", TypeError, "total_chunks must be an integer"),
        ("sequence", True, TypeError, "sequence must be an integer"),
        ("is_final", 1, TypeError, "is_final must be a boolean"),
        ("payload", 1, TypeError, "payload must be a UTF-8 string"),
        ("payload", chr(0xD800), ValueError, "payload must contain valid UTF-8"),
        ("checksum", None, ValueError, "checksum must be an eight-character"),
        ("checksum", "bad", ValueError, "checksum must be an eight-character"),
        ("checksum", "zzzzzzzz", ValueError, "only hexadecimal characters"),
        ("merge_mode", None, TypeError, "merge_mode must be a string"),
        ("message_id", "", ValueError, "message_id must be a non-empty string"),
        ("auth_tag", "short", ValueError, "64-character HMAC-SHA256"),
        ("auth_tag", "g" * 64, ValueError, "only hexadecimal characters"),
    ],
)
def test_envelope_rejects_invalid_wire_field_values(field, value, error, message):
    values = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=b"payload",
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    ).to_dict()
    values[field] = value

    with pytest.raises(error, match=message):
        WireEnvelope(**values)


@pytest.mark.parametrize(
    ("field", "value", "error", "message"),
    [
        ("sequence", True, TypeError, "sequence must be an integer"),
        ("total_chunks", "one", TypeError, "total_chunks must be an integer"),
        ("checksum", None, TypeError, "checksum must be a string"),
        ("is_final", 1, TypeError, "is_final must be a boolean"),
        ("payload", None, TypeError, "payload must be a UTF-8 string"),
        ("message_id", 1, TypeError, "message_id must be a string"),
        ("auth_tag", None, TypeError, "auth_tag must be a string"),
        ("merge_mode", None, TypeError, "merge_mode must be a string"),
    ],
)
def test_envelope_mapping_rejects_invalid_field_types(field, value, error, message):
    mapping = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=b"payload",
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    ).to_dict()
    mapping[field] = value

    with pytest.raises(error, match=message):
        WireEnvelope.from_mapping(mapping)


def test_envelope_mapping_rejects_missing_required_field():
    mapping = WireEnvelope.from_bytes(
        sequence=0,
        total_chunks=1,
        payload=b"payload",
        is_final=True,
        message_id=MESSAGE_ID,
        authentication_key=AUTH_KEY,
    ).to_dict()
    del mapping["message_id"]

    with pytest.raises(ValueError, match="missing envelope fields: message_id"):
        WireEnvelope.from_mapping(mapping)


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


def test_envelope_builder_rejects_authentication_key_shorter_than_16_bytes():
    with pytest.raises(ValueError, match="16"):
        WireEnvelope.from_bytes(
            sequence=0,
            total_chunks=1,
            payload=b"payload",
            is_final=True,
            message_id=MESSAGE_ID,
            authentication_key=b"x" * 15,
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