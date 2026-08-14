from __future__ import annotations

from dataclasses import dataclass
from typing import List
import hashlib

from chunker import semantic_split


@dataclass
class Chunk:
    index: int
    total_chunks: int
    payload: str
    checksum: str
    is_final: bool


@dataclass
class FilterResult:
    mode: str
    payload: str
    chunks: List[Chunk]
    threshold_bytes: int


class AdaptiveResponseFilter:
    """A delivery-layer filter that uses semantic chunking.

    The policy is conservative:
    - small payloads stay on the full-buffer path
    - large payloads are split into structured chunks using semantic boundaries
    - chunks are tagged with metadata for reconstruction
    - the caller can decide whether to display them progressively or fall back
    """

    def __init__(self, threshold_bytes: int = 128_000, max_chunk_bytes: int = 64_000) -> None:
        self.threshold_bytes = threshold_bytes
        self.max_chunk_bytes = max_chunk_bytes

    def build(self, payload: str) -> FilterResult:
        payload_bytes = payload.encode("utf-8")
        if len(payload_bytes) < self.threshold_bytes:
            return FilterResult(
                mode="full",
                payload=payload,
                chunks=[],
                threshold_bytes=self.threshold_bytes,
            )

        chunks = self._chunk_payload(payload_bytes)
        return FilterResult(
            mode="chunked",
            payload=payload,
            chunks=chunks,
            threshold_bytes=self.threshold_bytes,
        )

    def _chunk_payload(self, payload_bytes: bytes) -> List[Chunk]:
        """Chunk the payload using semantic boundaries from chunker.py."""
        chunk_bytes_list = semantic_split(payload_bytes, self.max_chunk_bytes)
        total_chunks = len(chunk_bytes_list)
        chunks: List[Chunk] = []

        for index, chunk_bytes in enumerate(chunk_bytes_list):
            chunk_text = chunk_bytes.decode("utf-8", errors="replace")
            chunk = Chunk(
                index=index,
                total_chunks=total_chunks,
                payload=chunk_text,
                checksum=self._checksum(chunk_bytes),
                is_final=(index == total_chunks - 1),
            )
            chunks.append(chunk)

        return chunks

    def _checksum(self, payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()[:12]
