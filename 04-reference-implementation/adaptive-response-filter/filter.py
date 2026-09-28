from __future__ import annotations

from dataclasses import dataclass

from chunker import is_json_object, semantic_split
from envelope import WireEnvelope
from policy import DeliveryPolicy

Chunk = WireEnvelope


@dataclass
class FilterResult:
    mode: str
    payload: str
    chunks: list[Chunk]
    threshold_bytes: int


def build_envelopes(
    payload_bytes: bytes,
    policy: DeliveryPolicy,
) -> list[WireEnvelope]:
    """Split a payload and wrap each part in a validated envelope."""
    if not policy.should_chunk(payload_bytes):
        return [
            WireEnvelope.from_bytes(
                sequence=0,
                total_chunks=1,
                payload=payload_bytes,
                is_final=True,
            )
        ]

    chunk_bytes_list = semantic_split(payload_bytes, policy.max_chunk_bytes)
    merge_mode = "json-object" if is_json_object(payload_bytes) else "concat"
    total_chunks = len(chunk_bytes_list)
    return [
        WireEnvelope.from_bytes(
            sequence=index,
            total_chunks=total_chunks,
            payload=chunk_bytes,
            is_final=index == total_chunks - 1,
            merge_mode=merge_mode,
        )
        for index, chunk_bytes in enumerate(chunk_bytes_list)
    ]


class AdaptiveResponseFilter:
    """Choose full delivery or construct validated semantic chunks."""

    def __init__(
        self,
        threshold_bytes: int = 128_000,
        max_chunk_bytes: int = 64_000,
    ) -> None:
        self.policy = DeliveryPolicy(
            threshold_bytes=threshold_bytes,
            max_chunk_bytes=max_chunk_bytes,
        )

    @property
    def threshold_bytes(self) -> int:
        return self.policy.threshold_bytes

    @property
    def max_chunk_bytes(self) -> int:
        return self.policy.max_chunk_bytes

    def build(self, payload: str) -> FilterResult:
        payload_bytes = payload.encode("utf-8")
        envelopes = build_envelopes(payload_bytes, self.policy)
        if not self.policy.should_chunk(payload_bytes):
            return FilterResult(
                mode="full",
                payload=payload,
                chunks=[],
                threshold_bytes=self.threshold_bytes,
            )

        return FilterResult(
            mode="chunked",
            payload=payload,
            chunks=envelopes,
            threshold_bytes=self.threshold_bytes,
        )
