"""
Reassembler — buffers incoming chunk envelopes and reconstructs the
original payload once every chunk has arrived and validated.

This is the Python-side twin of client_reassembler.ts (browser side).
It exists here mainly for testing the wire contract end-to-end and as
a readable reference for anyone porting the contract to another
language/runtime.
"""

from __future__ import annotations

import json
import zlib
from dataclasses import dataclass, field


def checksum(payload: bytes) -> str:
    return format(zlib.crc32(payload), "08x")


@dataclass
class Reassembler:
    total_chunks: int | None = None
    received: dict[int, bytes] = field(default_factory=dict)

    def add_chunk(self, chunk: dict) -> bytes | None:
        sequence = chunk["sequence"]
        payload = chunk["payload"].encode("utf-8")

        if checksum(payload) != chunk["checksum"]:
            raise ValueError(f"checksum mismatch on chunk {sequence}")

        self.total_chunks = chunk["total_chunks"]
        self.received[sequence] = payload

        if len(self.received) == self.total_chunks:
            return self._reassemble()
        return None

    def missing(self) -> list[int]:
        if self.total_chunks is None:
            return []
        return [i for i in range(self.total_chunks) if i not in self.received]

    def _reassemble(self) -> bytes:
        ordered = [self.received[i] for i in range(self.total_chunks)]
        merged: dict = {}
        for chunk_bytes in ordered:
            merged.update(json.loads(chunk_bytes))
        return json.dumps(merged).encode("utf-8")
