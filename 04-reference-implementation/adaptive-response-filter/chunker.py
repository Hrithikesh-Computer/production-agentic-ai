"""
Chunking logic — turns a serialized payload into a list of byte
chunks along semantically meaningful boundaries where possible.

Boundary preference order: JSON object boundaries > tool output
boundaries > citation blocks > paragraph boundaries > fixed-size
byte fallback. This reference implements top-level JSON object and
tool-call list boundaries, then fixed-size fallback.
"""

from __future__ import annotations

import json


class UnsplittableValueError(ValueError):
    """Raised when a semantic JSON value cannot fit within the chunk cap."""


def is_json_object(payload: bytes) -> bool:
    """Return whether UTF-8 payload is a JSON object, not another JSON type."""
    try:
        return isinstance(json.loads(payload), dict)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def semantic_split(payload: bytes, max_chunk_bytes: int) -> list[bytes]:
    if isinstance(max_chunk_bytes, bool) or not isinstance(max_chunk_bytes, int):
        raise TypeError("max_chunk_bytes must be an integer")
    if max_chunk_bytes <= 0:
        raise ValueError("max_chunk_bytes must be positive")

    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _fixed_size_split(payload, max_chunk_bytes)

    if isinstance(parsed, dict):
        json_boundary_error = None
        try:
            chunks = _split_by_top_level_keys(parsed, max_chunk_bytes)
        except UnsplittableValueError as error:
            json_boundary_error = error
            chunks = []
        if chunks:
            return chunks

        tool_chunks = _split_by_tool_boundaries(parsed, max_chunk_bytes)
        if tool_chunks:
            return tool_chunks
        if json_boundary_error is not None:
            raise json_boundary_error

    return _fixed_size_split(payload, max_chunk_bytes)


def _split_by_top_level_keys(obj: dict, max_chunk_bytes: int) -> list[bytes]:
    """
    Pack top-level keys into chunks up to max_chunk_bytes, never
    splitting inside a single key's value (a tool result, a citation
    list, etc. always stays intact within one chunk).
    """
    if not obj:
        empty_object = b"{}"
        if len(empty_object) > max_chunk_bytes:
            raise UnsplittableValueError(
                f"empty JSON object requires {len(empty_object)} bytes; "
                f"limit is {max_chunk_bytes}"
            )
        return [empty_object]

    chunks: list[bytes] = []
    current: dict = {}
    current_size = 2

    for key, value in obj.items():
        encoded_key = json.dumps(key, ensure_ascii=False).encode("utf-8")
        encoded_value = json.dumps(value, ensure_ascii=False).encode("utf-8")
        pair_size = len(encoded_key) + 1 + len(encoded_value)
        standalone_size = pair_size + 2

        if standalone_size > max_chunk_bytes:
            raise UnsplittableValueError(
                f"JSON value for key {key!r} requires {standalone_size} bytes; "
                f"limit is {max_chunk_bytes}"
            )

        additional_size = pair_size + (1 if current else 0)
        if current and current_size + additional_size > max_chunk_bytes:
            chunks.append(
                json.dumps(current, ensure_ascii=False, separators=(",", ":"))
                .encode("utf-8")
            )
            current = {}
            current_size = 2

        current[key] = value
        current_size += pair_size + (1 if len(current) > 1 else 0)

    if current:
        chunks.append(
            json.dumps(current, ensure_ascii=False, separators=(",", ":"))
            .encode("utf-8")
        )

    return chunks


def _split_by_tool_boundaries(
    obj: dict,
    max_chunk_bytes: int,
) -> list[bytes] | None:
    """Split an oversized tool_calls list only between complete tool records.

    The canonical JSON serialization is concatenated by the receiver, so
    fragments remain an exact, syntactically complete JSON document on merge.
    """
    tool_calls = obj.get("tool_calls")
    if not isinstance(tool_calls, list) or len(tool_calls) < 2:
        return None

    units: list[bytes] = [b"{"]
    for key, value in obj.items():
        if units != [b"{"]:
            units.append(b",")
        key_bytes = json.dumps(key, ensure_ascii=False).encode("utf-8")
        if key == "tool_calls":
            units.extend([key_bytes + b":["])
            for index, tool_call in enumerate(tool_calls):
                prefix = b"," if index else b""
                units.append(
                    prefix
                    + json.dumps(
                        tool_call,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
            units.append(b"]")
        else:
            units.append(
                key_bytes
                + b":"
                + json.dumps(
                    value,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
    units.append(b"}")

    if any(len(unit) > max_chunk_bytes for unit in units):
        return None

    chunks: list[bytes] = []
    current = bytearray()
    for unit in units:
        if current and len(current) + len(unit) > max_chunk_bytes:
            chunks.append(bytes(current))
            current.clear()
        current.extend(unit)
    if current:
        chunks.append(bytes(current))
    if len(chunks) < 2:
        return None
    return chunks


def _fixed_size_split(payload: bytes, max_chunk_bytes: int) -> list[bytes]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("payload must contain valid UTF-8") from error

    chunks: list[bytes] = []
    current_characters: list[str] = []
    current_size = 0

    for character in text:
        character_bytes = character.encode("utf-8")
        character_size = len(character_bytes)
        if character_size > max_chunk_bytes:
            raise UnsplittableValueError(
                f"UTF-8 code point requires {character_size} bytes; "
                f"limit is {max_chunk_bytes}"
            )

        if current_characters and current_size + character_size > max_chunk_bytes:
            chunks.append("".join(current_characters).encode("utf-8"))
            current_characters = []
            current_size = 0

        current_characters.append(character)
        current_size += character_size

    if current_characters:
        chunks.append("".join(current_characters).encode("utf-8"))
    elif not chunks:
        chunks.append(b"")

    return chunks
