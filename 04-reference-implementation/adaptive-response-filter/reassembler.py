"""Buffer one message's envelopes and reconstruct its payload when complete."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping

from envelope import (
    MAX_ENVELOPE_CHUNKS,
    MAX_ENVELOPE_PAYLOAD_BYTES,
    WireEnvelope,
    checksum,
)

DEFAULT_MAX_CHUNKS = MAX_ENVELOPE_CHUNKS
DEFAULT_MAX_PAYLOAD_BYTES = MAX_ENVELOPE_PAYLOAD_BYTES


@dataclass
class Reassembler:
    total_chunks: int | None = field(default=None, init=False)
    received: dict[int, bytes] = field(default_factory=dict, init=False)
    merge_mode: str | None = field(default=None, init=False)
    max_chunks: int = DEFAULT_MAX_CHUNKS
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES
    _received_bytes: int = field(default=0, init=False, repr=False)
    _completed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.max_chunks, bool) or not isinstance(self.max_chunks, int):
            raise TypeError("max_chunks must be an integer")
        if self.max_chunks <= 0:
            raise ValueError("max_chunks must be positive")
        if isinstance(self.max_payload_bytes, bool) or not isinstance(
            self.max_payload_bytes, int
        ):
            raise TypeError("max_payload_bytes must be an integer")
        if self.max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")

    def add_chunk(
        self, chunk: WireEnvelope | Mapping[str, object]
    ) -> bytes | None:
        if self._completed:
            raise ValueError(
                "a Reassembler instance handles one message; create a new instance"
            )

        if isinstance(chunk, WireEnvelope):
            envelope = chunk
        else:
            envelope = WireEnvelope.from_mapping(chunk)
        sequence = envelope.sequence
        payload = envelope.payload_bytes()

        if envelope.total_chunks > self.max_chunks:
            raise ValueError(
                f"total_chunks exceeds configured maximum of {self.max_chunks}"
            )
        if self.total_chunks is not None and envelope.total_chunks != self.total_chunks:
            raise ValueError("total_chunks cannot change during reassembly")
        if self.merge_mode is not None and envelope.merge_mode != self.merge_mode:
            raise ValueError("merge_mode cannot change during reassembly")

        if checksum(payload) != envelope.checksum.lower():
            raise ValueError(f"checksum mismatch on chunk {sequence}")

        existing = self.received.get(sequence)
        if existing is not None:
            if existing != payload:
                raise ValueError(f"conflicting duplicate chunk {sequence}")
            if len(self.received) == self.total_chunks:
                return self._reassemble()
            return None

        if self._received_bytes + len(payload) > self.max_payload_bytes:
            raise ValueError(
                f"reassembled payload exceeds configured maximum of "
                f"{self.max_payload_bytes} bytes"
            )

        if self.total_chunks is None:
            self.total_chunks = envelope.total_chunks
            self.merge_mode = envelope.merge_mode
        self.received[sequence] = payload
        self._received_bytes += len(payload)

        if len(self.received) == self.total_chunks:
            assembled = self._reassemble()
            self._completed = True
            return assembled
        return None

    def missing(self) -> list[int]:
        total_chunks = self.total_chunks
        if total_chunks is None:
            return []
        return [
            sequence
            for sequence in range(total_chunks)
            if sequence not in self.received
        ]

    def _reassemble(self) -> bytes:
        total_chunks = self.total_chunks
        assert total_chunks is not None
        assert len(self.received) == total_chunks
        ordered = [self.received[sequence] for sequence in range(total_chunks)]

        if self.merge_mode == "concat":
            return b"".join(ordered)

        merged: dict[str, object] = {}
        for chunk_bytes in ordered:
            try:
                fragment = json.loads(chunk_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("invalid JSON object fragment") from error
            if not isinstance(fragment, dict):
                raise ValueError("json-object chunks must each contain a JSON object")
            duplicate_keys = merged.keys() & fragment.keys()
            if duplicate_keys:
                raise ValueError(
                    f"duplicate JSON object key across chunks: "
                    f"{sorted(duplicate_keys)[0]!r}"
                )
            merged.update(fragment)

        return json.dumps(merged, ensure_ascii=False).encode("utf-8")
