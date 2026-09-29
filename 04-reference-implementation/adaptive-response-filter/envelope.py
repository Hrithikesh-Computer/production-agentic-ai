"""Validated wire envelope shared by response producers and consumers."""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Mapping

MAX_ENVELOPE_CHUNKS = 10_000
MAX_ENVELOPE_PAYLOAD_BYTES = 16_000_000


def checksum(payload: bytes) -> str:
    """Return the canonical eight-character CRC32 checksum."""
    return f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}"


@dataclass(frozen=True)
class WireEnvelope:
    """One validated chunk in the response-delivery wire protocol.

    ``merge_mode`` is ``"concat"`` for byte fragments and
    ``"json-object"`` for independently serialized object fragments
    that the receiver merges by top-level key.
    """

    sequence: int
    total_chunks: int
    checksum: str
    is_final: bool
    payload: str
    merge_mode: str = "concat"

    def __post_init__(self) -> None:
        if isinstance(self.total_chunks, bool) or not isinstance(
            self.total_chunks, int
        ):
            raise TypeError("total_chunks must be an integer")
        if self.total_chunks <= 0:
            raise ValueError("total_chunks must be positive")
        if self.total_chunks > MAX_ENVELOPE_CHUNKS:
            raise ValueError(
                f"total_chunks exceeds protocol maximum of {MAX_ENVELOPE_CHUNKS}"
            )
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("sequence must be an integer")
        if not 0 <= self.sequence < self.total_chunks:
            raise ValueError("sequence must be in [0, total_chunks)")
        if not isinstance(self.is_final, bool):
            raise TypeError("is_final must be a boolean")
        if self.is_final != (self.sequence == self.total_chunks - 1):
            raise ValueError("is_final must match the final sequence")
        if not isinstance(self.payload, str):
            raise TypeError("payload must be a UTF-8 string")
        try:
            payload_bytes = self.payload.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("payload must contain valid UTF-8 text") from error
        if len(payload_bytes) > MAX_ENVELOPE_PAYLOAD_BYTES:
            raise ValueError(
                "payload exceeds protocol maximum of "
                f"{MAX_ENVELOPE_PAYLOAD_BYTES} bytes"
            )
        if not isinstance(self.checksum, str) or len(self.checksum) != 8:
            raise ValueError("checksum must be an eight-character CRC32 hex string")
        if any(
            character not in "0123456789abcdefABCDEF"
            for character in self.checksum
        ):
            raise ValueError("checksum must contain only hexadecimal characters")
        if not isinstance(self.merge_mode, str):
            raise TypeError("merge_mode must be a string")
        if self.merge_mode not in {"concat", "json-object"}:
            raise ValueError("merge_mode must be 'concat' or 'json-object'")

    @property
    def index(self) -> int:
        """Compatibility alias for the earlier ``Chunk.index`` field."""
        return self.sequence

    @classmethod
    def from_bytes(
        cls,
        *,
        sequence: int,
        total_chunks: int,
        payload: bytes,
        is_final: bool,
        merge_mode: str = "concat",
    ) -> WireEnvelope:
        """Build a checksummed envelope, rejecting invalid UTF-8 bytes."""
        return cls(
            sequence=sequence,
            total_chunks=total_chunks,
            checksum=checksum(payload),
            is_final=is_final,
            payload=payload.decode("utf-8"),
            merge_mode=merge_mode,
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> WireEnvelope:
        """Validate a decoded wire mapping before it enters reassembly."""
        required = {"sequence", "total_chunks", "checksum", "is_final", "payload"}
        missing = required.difference(data)
        if missing:
            raise ValueError(f"missing envelope fields: {', '.join(sorted(missing))}")

        merge_mode = data.get("merge_mode", "concat")
        if not isinstance(merge_mode, str):
            raise TypeError("merge_mode must be a string")

        sequence = data["sequence"]
        total_chunks = data["total_chunks"]
        checksum_value = data["checksum"]
        is_final = data["is_final"]
        payload = data["payload"]
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise TypeError("sequence must be an integer")
        if isinstance(total_chunks, bool) or not isinstance(total_chunks, int):
            raise TypeError("total_chunks must be an integer")
        if not isinstance(checksum_value, str):
            raise TypeError("checksum must be a string")
        if not isinstance(is_final, bool):
            raise TypeError("is_final must be a boolean")
        if not isinstance(payload, str):
            raise TypeError("payload must be a UTF-8 string")

        return cls(
            sequence=sequence,
            total_chunks=total_chunks,
            checksum=checksum_value,
            is_final=is_final,
            payload=payload,
            merge_mode=merge_mode,
        )

    def to_dict(self) -> dict[str, int | str | bool]:
        """Return the JSON-compatible representation used by middleware."""
        return {
            "sequence": self.sequence,
            "total_chunks": self.total_chunks,
            "checksum": self.checksum,
            "is_final": self.is_final,
            "payload": self.payload,
            "merge_mode": self.merge_mode,
        }

    def payload_bytes(self) -> bytes:
        """Encode payload exactly as checksummed by the producer."""
        return self.payload.encode("utf-8")