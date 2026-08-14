"""
Chunking logic — turns a serialized payload into a list of byte
chunks along semantically meaningful boundaries where possible.

Boundary preference order: JSON object boundaries > tool output
boundaries > citation blocks > paragraph boundaries > fixed-size
byte fallback. This reference implementation only demonstrates the
first and last of these (structural top-level-key splitting and
fixed-size fallback); a production chunker would walk the full
object graph.
"""

from __future__ import annotations

import json


def semantic_split(payload: bytes, max_chunk_bytes: int) -> list[bytes]:
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _fixed_size_split(payload, max_chunk_bytes)

    if isinstance(parsed, dict):
        chunks = _split_by_top_level_keys(parsed, max_chunk_bytes)
        if chunks:
            return chunks

    return _fixed_size_split(payload, max_chunk_bytes)


def _split_by_top_level_keys(obj: dict, max_chunk_bytes: int) -> list[bytes]:
    """
    Pack top-level keys into chunks up to max_chunk_bytes, never
    splitting inside a single key's value (a tool result, a citation
    list, etc. always stays intact within one chunk).
    """
    chunks: list[bytes] = []
    current: dict = {}
    current_size = 0

    for key, value in obj.items():
        encoded = json.dumps({key: value}).encode("utf-8")
        if current and current_size + len(encoded) > max_chunk_bytes:
            chunks.append(json.dumps(current).encode("utf-8"))
            current = {}
            current_size = 0
        current[key] = value
        current_size += len(encoded)

    if current:
        chunks.append(json.dumps(current).encode("utf-8"))

    return chunks


def _fixed_size_split(payload: bytes, max_chunk_bytes: int) -> list[bytes]:
    return [
        payload[i : i + max_chunk_bytes]
        for i in range(0, len(payload), max_chunk_bytes)
    ]
