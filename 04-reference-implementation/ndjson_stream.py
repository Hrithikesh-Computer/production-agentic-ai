from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from receiver_outcomes import ReceiverOutcome, emit_receiver_outcome

DEFAULT_MAX_RECORD_BYTES = 1_048_576


class NDJSONError(ValueError):
    """Base class for NDJSON stream failures."""


class IncompleteRecordError(NDJSONError):
    """Raised when a stream ends with an unterminated NDJSON record."""


class RecordTooLargeError(NDJSONError):
    """Raised when one record exceeds the configured size limit."""


class DecoderFailedError(NDJSONError):
    """Raised when a decoder is used after a failure or discard."""


def _reject_nonstandard_json_constant(value: str) -> Any:
    raise NDJSONError(f"non-standard JSON constant: {value}")


def _reject_duplicate_object_names(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NDJSONError(f"duplicate JSON object name: {key!r}")
        result[key] = value
    return result


class NDJSONDecoder:
    """Incrementally decode newline-delimited JSON objects from UTF-8 bytes.

    Failure policy (matches "discard partial state, retry the whole request"):
    any error poisons the decoder. Records parsed earlier in the same feed()
    call are not returned, and the caller must discard everything it has
    already received for this response. Nothing is skipped silently.
    """

    def __init__(self, max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> None:
        if max_record_bytes <= 0:
            raise ValueError("max_record_bytes must be positive")
        self._max = max_record_bytes
        self._pending = bytearray()
        self._finished = False
        self._failed = False

    @property
    def failed(self) -> bool:
        return self._failed

    def _fail(self) -> None:
        self._failed = True
        self._pending.clear()

    def _poison(self) -> None:
        self._fail()
        emit_receiver_outcome(ReceiverOutcome.NDJSON_DECODER_POISONED)

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        if self._failed:
            raise DecoderFailedError("decoder failed; discard the response and retry")
        if self._finished:
            raise ValueError("decoder is finished")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        records: list[dict[str, Any]] = []
        offset = 0
        try:
            while offset < len(data):
                delimiter = data.find(b"\n", offset)
                if delimiter < 0:
                    fragment = data[offset:]
                    if len(fragment) > self._max - len(self._pending):
                        raise RecordTooLargeError("record exceeds size limit")
                    self._pending.extend(fragment)
                    break
                fragment = data[offset:delimiter]
                if len(fragment) > self._max - len(self._pending):
                    raise RecordTooLargeError("record exceeds size limit")
                self._pending.extend(fragment)
                line = bytes(self._pending)
                self._pending.clear()
                offset = delimiter + 1
                if not line.strip():
                    continue
                value = json.loads(
                    line.decode("utf-8"),
                    parse_constant=_reject_nonstandard_json_constant,
                    object_pairs_hook=_reject_duplicate_object_names,
                )
                if not isinstance(value, dict):
                    raise NDJSONError("NDJSON records must be JSON objects")
                records.append(value)
        except RecursionError as error:
            self._poison()
            raise NDJSONError("JSON nesting exceeds decoder capacity") from error
        except Exception:
            self._poison()
            raise
        return records

    def finish(self) -> None:
        if self._failed:
            raise DecoderFailedError("decoder failed; discard the response and retry")
        if self._finished:
            return
        self._finished = True
        if self._pending:
            self._poison()
            raise IncompleteRecordError("stream ended inside an NDJSON record")

    def discard(self) -> None:
        """Abandon an incomplete response after transport failure."""
        self._fail()
        self._finished = True


def encode_record(value: Mapping[str, object]) -> bytes:
    """Encode one JSON object as an NDJSON record including its delimiter."""
    if not isinstance(value, Mapping):
        raise TypeError("NDJSON records must be mappings")
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8") + b"\n"


def encode_records(values: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(encode_record(value) for value in values)
