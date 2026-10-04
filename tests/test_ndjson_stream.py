from __future__ import annotations

import pytest
from ndjson_stream import (
    DecoderFailedError,
    IncompleteRecordError,
    NDJSONDecoder,
    NDJSONError,
    RecordTooLargeError,
    encode_record,
    encode_records,
)


def test_decoder_handles_record_and_multibyte_utf8_split_across_fragments() -> None:
    encoded = encode_record({"name": "café ✓"})
    split = encoded.index("é".encode()) + 1
    decoder = NDJSONDecoder()

    assert decoder.feed(encoded[:split]) == []
    assert decoder.feed(encoded[split:]) == [{"name": "café ✓"}]


def test_every_byte_boundary_split_decodes_identically() -> None:
    records = [{"i": i, "t": "é✓" * i} for i in range(4)]
    data = encode_records(records)
    for cut in range(len(data) + 1):
        decoder = NDJSONDecoder()
        out = decoder.feed(data[:cut]) + decoder.feed(data[cut:])
        decoder.finish()
        assert out == records


def test_decoder_keeps_escaped_newlines_inside_json_strings() -> None:
    decoder = NDJSONDecoder()
    assert decoder.feed(encode_record({"text": "a\nb"})) == [{"text": "a\nb"}]


def test_finish_rejects_trailing_partial_record() -> None:
    decoder = NDJSONDecoder()
    decoder.feed(b'{"a":1')
    with pytest.raises(IncompleteRecordError):
        decoder.finish()
    assert decoder.failed


def test_malformed_line_poisons_decoder_and_never_skips_silently() -> None:
    decoder = NDJSONDecoder()
    with pytest.raises(ValueError):
        decoder.feed(b'{"a":1}\nnot json\n{"b":2}\n')
    assert decoder.failed
    with pytest.raises(DecoderFailedError):
        decoder.feed(b"")
    with pytest.raises(DecoderFailedError):
        decoder.finish()


def test_invalid_utf8_fails_closed() -> None:
    decoder = NDJSONDecoder()
    with pytest.raises(UnicodeDecodeError):
        decoder.feed(b'{"a":"\xff"}\n')
    assert decoder.failed


def test_non_object_records_are_rejected() -> None:
    for line in (b"[1,2]\n", b"5\n", b'"s"\n', b"null\n"):
        decoder = NDJSONDecoder()
        with pytest.raises(NDJSONError):
            decoder.feed(line)


def test_record_without_newline_is_bounded() -> None:
    decoder = NDJSONDecoder(max_record_bytes=1024)
    decoder.feed(b"x" * 1000)
    with pytest.raises(RecordTooLargeError):
        decoder.feed(b"x" * 100)
    assert decoder.failed


def test_five_megabyte_feed_of_small_records_is_decoded_incrementally() -> None:
    total_bytes = 5 * 1024 * 1024
    full_record = b'{"v":"' + b"x" * 91 + b'"}\n'
    final_record = b'{"v":"' + b"x" * 71 + b'"}\n'
    full_record_count, remainder = divmod(total_bytes, len(full_record))
    assert len(final_record) == remainder
    data = full_record * full_record_count + final_record
    decoder = NDJSONDecoder()

    records = decoder.feed(data)
    decoder.finish()

    assert len(records) == full_record_count + 1
    assert records[0] == {"v": "x" * 91}
    assert records[-1] == {"v": "x" * 71}


def test_oversized_complete_record_is_rejected() -> None:
    decoder = NDJSONDecoder(max_record_bytes=16)
    with pytest.raises(RecordTooLargeError):
        decoder.feed(b'{"k":"' + b"v" * 64 + b'"}\n')


def test_record_exactly_at_limit_is_accepted() -> None:
    line = b'{"a":1}'
    decoder = NDJSONDecoder(max_record_bytes=len(line))
    assert decoder.feed(line + b"\n") == [{"a": 1}]


def test_blank_lines_and_crlf_are_tolerated() -> None:
    decoder = NDJSONDecoder()
    assert decoder.feed(b'\n{"a":1}\r\n  \n{"b":2}\n') == [{"a": 1}, {"b": 2}]


def test_discard_makes_decoder_unusable() -> None:
    decoder = NDJSONDecoder()
    decoder.feed(b'{"a":')
    decoder.discard()
    with pytest.raises(DecoderFailedError):
        decoder.feed(b"1}\n")
    assert decoder.failed


def test_clean_stream_finishes_without_error() -> None:
    decoder = NDJSONDecoder()
    assert decoder.feed(encode_records([{"a": 1}, {"b": 2}])) == [{"a": 1}, {"b": 2}]
    decoder.finish()
    decoder.finish()


def test_record_at_limit_may_arrive_before_its_delimiter() -> None:
    line = b'{"a":1}'
    decoder = NDJSONDecoder(max_record_bytes=len(line))
    assert decoder.feed(line) == []
    assert decoder.feed(b"\n") == [{"a": 1}]
