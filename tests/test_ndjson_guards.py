from __future__ import annotations

import pytest
from ndjson_stream import NDJSONDecoder, encode_record


def test_non_positive_record_limit_is_rejected() -> None:
    for limit in (0, -1):
        with pytest.raises(ValueError, match="positive"):
            NDJSONDecoder(max_record_bytes=limit)


def test_feeding_a_finished_decoder_raises() -> None:
    decoder = NDJSONDecoder()
    decoder.finish()
    with pytest.raises(ValueError, match="finished"):
        decoder.feed(b"{}\n")


def test_non_bytes_input_is_rejected_without_poisoning() -> None:
    decoder = NDJSONDecoder()
    with pytest.raises(TypeError, match="bytes"):
        decoder.feed("{}\n")  # type: ignore[arg-type]
    assert not decoder.failed
    assert decoder.feed(b'{"a":1}\n') == [{"a": 1}]


def test_encoder_rejects_non_mapping_values() -> None:
    for value in ([1, 2], "text", 5, None):
        with pytest.raises(TypeError, match="mappings"):
            encode_record(value)  # type: ignore[arg-type]
