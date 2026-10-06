"""Buffer one message's envelopes and reconstruct its payload when complete."""

from __future__ import annotations

import json
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Mapping

from envelope import (
    MAX_ENVELOPE_CHUNKS,
    MAX_ENVELOPE_PAYLOAD_BYTES,
    MIN_AUTHENTICATION_KEY_BYTES,
    WireEnvelope,
    checksum,
)
from policy import DeliveryPolicy
from receiver_outcomes import ReceiverOutcome, emit_receiver_outcome

DEFAULT_MAX_CHUNKS = MAX_ENVELOPE_CHUNKS
DEFAULT_MAX_PAYLOAD_BYTES = MAX_ENVELOPE_PAYLOAD_BYTES
DEFAULT_MAX_TOTAL_BYTES = 268_435_456
OVERHEAD_PER_CHUNK = 96


@dataclass
class Reassembler:
    authentication_key: bytes = field(repr=False)
    total_chunks: int | None = field(default=None, init=False)
    received: dict[int, bytes] = field(default_factory=dict, init=False)
    merge_mode: str | None = field(default=None, init=False)
    message_id: str | None = field(default=None, init=False)
    max_chunks: int = DEFAULT_MAX_CHUNKS
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES
    _received_bytes: int = field(default=0, init=False, repr=False)
    _completed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authentication_key, bytes)
            or len(self.authentication_key) < MIN_AUTHENTICATION_KEY_BYTES
        ):
            raise ValueError(
                "authentication_key must be at least "
                f"{MIN_AUTHENTICATION_KEY_BYTES} bytes"
            )
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

    def _prepare_chunk(
        self, chunk: WireEnvelope | Mapping[str, object]
    ) -> tuple[WireEnvelope, bytes, int, bool]:
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
            emit_receiver_outcome(ReceiverOutcome.MESSAGE_LIMIT_REJECTED)
            raise ValueError(
                f"total_chunks exceeds configured maximum of {self.max_chunks}"
            )
        if self.total_chunks is not None and envelope.total_chunks != self.total_chunks:
            raise ValueError("total_chunks cannot change during reassembly")
        if self.merge_mode is not None and envelope.merge_mode != self.merge_mode:
            raise ValueError("merge_mode cannot change during reassembly")
        if self.message_id is not None and envelope.message_id != self.message_id:
            raise ValueError("message_id cannot change during reassembly")

        if checksum(payload) != envelope.checksum.lower():
            emit_receiver_outcome(ReceiverOutcome.ENVELOPE_INTEGRITY_REJECTED)
            raise ValueError(f"checksum mismatch on chunk {sequence}")
        if not envelope.verify_authentication(self.authentication_key):
            emit_receiver_outcome(ReceiverOutcome.AUTHENTICATION_REJECTED)
            raise ValueError(f"authentication failed on chunk {sequence}")

        existing = self.received.get(sequence)
        if existing is not None:
            if existing != payload:
                raise ValueError(f"conflicting duplicate chunk {sequence}")
            return envelope, payload, 0, True

        if self._received_bytes + len(payload) > self.max_payload_bytes:
            emit_receiver_outcome(ReceiverOutcome.MESSAGE_LIMIT_REJECTED)
            raise ValueError(
                f"reassembled payload exceeds configured maximum of "
                f"{self.max_payload_bytes} bytes"
            )

        return envelope, payload, len(payload), False

    def add_chunk(
        self, chunk: WireEnvelope | Mapping[str, object]
    ) -> bytes | None:
        envelope, payload, added_bytes, duplicate = self._prepare_chunk(chunk)
        sequence = envelope.sequence
        if duplicate:
            if len(self.received) == self.total_chunks:
                return self._reassemble()
            return None

        if self.total_chunks is None:
            self.total_chunks = envelope.total_chunks
            self.merge_mode = envelope.merge_mode
            self.message_id = envelope.message_id
        self.received[sequence] = payload
        self._received_bytes += added_bytes

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

    @property
    def completed(self) -> bool:
        return self._completed

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


@dataclass
class ReassemblySession:
    """One message's retry deadline and full-buffer fallback policy."""

    message_id: str
    authentication_key: bytes = field(repr=False)
    request_retry: Callable[[str, list[int]], None]
    request_full_buffer: Callable[[str], bytes]
    policy: DeliveryPolicy = field(default_factory=DeliveryPolicy)
    clock: Callable[[], float] = time.monotonic
    reassembler: Reassembler = field(init=False)
    retries: int = field(default=0, init=False)
    fallback_result: bytes | None = field(default=None, init=False)
    _deadline: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id must be non-empty")
        self.reassembler = Reassembler(authentication_key=self.authentication_key)
        self._deadline = self.clock() + self.policy.timeout_seconds

    def add_chunk(self, chunk: WireEnvelope | Mapping[str, object]) -> bytes | None:
        envelope = chunk
        if not isinstance(envelope, WireEnvelope):
            envelope = WireEnvelope.from_mapping(envelope)
        if envelope.message_id != self.message_id:
            raise ValueError("chunk message_id does not match session")
        result = self.reassembler.add_chunk(envelope)
        if result is None:
            self._deadline = self.clock() + self.policy.timeout_seconds
        return result

    def poll_timeout(self, now: float | None = None) -> bytes | None:
        """Retry missing chunks, then replace unsafe partial state with full data.

        Callback exceptions propagate without advancing retry or fallback state.
        A later poll invokes the callback again, so callbacks must be idempotent.
        """
        if self.fallback_result is not None or self.reassembler.completed:
            return None
        current_time = self.clock() if now is None else now
        if current_time < self._deadline:
            return None

        if self.retries < self.policy.max_retries:
            try:
                self.request_retry(self.message_id, self.reassembler.missing())
            except Exception:
                emit_receiver_outcome(ReceiverOutcome.RETRY_CALLBACK_FAILED)
                raise
            self.retries += 1
            self._deadline = current_time + self.policy.timeout_seconds
            return None

        try:
            full_payload = self.request_full_buffer(self.message_id)
        except Exception:
            emit_receiver_outcome(ReceiverOutcome.FULL_BUFFER_CALLBACK_FAILED)
            raise
        if not isinstance(full_payload, bytes):
            emit_receiver_outcome(ReceiverOutcome.FULL_BUFFER_CALLBACK_FAILED)
            raise TypeError("full-buffer callback must return bytes")
        self.fallback_result = full_payload
        return full_payload


@dataclass
class ReassemblySessionManager:
    """Route interleaved chunks to independent message-scoped sessions.

    This manager is not thread-safe. Concurrent calls for the same message ID
    can silently lose a chunk; callers sharing one manager across threads must
    serialize access.
    """

    authentication_key: bytes = field(repr=False)
    request_retry: Callable[[str, list[int]], None]
    request_full_buffer: Callable[[str], bytes]
    max_sessions: int = 1024
    session_ttl_seconds: float = 300.0
    tombstone_ttl_seconds: float = 3600.0
    max_tombstones: int = 4096
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    policy: DeliveryPolicy = field(default_factory=DeliveryPolicy)
    clock: Callable[[], float] = time.monotonic
    sessions: dict[str, ReassemblySession] = field(default_factory=dict, init=False)
    tombstones: OrderedDict[str, float] = field(default_factory=OrderedDict, init=False)
    _session_activity: dict[str, float] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        if isinstance(self.max_sessions, bool) or not isinstance(
            self.max_sessions, int
        ):
            raise TypeError("max_sessions must be an integer")
        if self.max_sessions <= 0:
            raise ValueError("max_sessions must be positive")
        if isinstance(self.session_ttl_seconds, bool) or not isinstance(
            self.session_ttl_seconds, (int, float)
        ):
            raise TypeError("session_ttl_seconds must be a number")
        if not math.isfinite(self.session_ttl_seconds) or self.session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds must be finite and positive")
        if isinstance(self.tombstone_ttl_seconds, bool) or not isinstance(
            self.tombstone_ttl_seconds, (int, float)
        ):
            raise TypeError("tombstone_ttl_seconds must be a number")
        if (
            not math.isfinite(self.tombstone_ttl_seconds)
            or self.tombstone_ttl_seconds <= 0
        ):
            raise ValueError("tombstone_ttl_seconds must be finite and positive")
        if isinstance(self.max_tombstones, bool) or not isinstance(
            self.max_tombstones, int
        ):
            raise TypeError("max_tombstones must be an integer")
        if self.max_tombstones <= 0:
            raise ValueError("max_tombstones must be positive")
        if isinstance(self.max_total_bytes, bool) or not isinstance(
            self.max_total_bytes, int
        ):
            raise TypeError("max_total_bytes must be an integer")
        if self.max_total_bytes <= 0:
            raise ValueError("max_total_bytes must be positive")

    def _expired_session_ids(self, now: float) -> set[str]:
        return {
            message_id
            for message_id, last_activity in self._session_activity.items()
            if now - last_activity >= self.session_ttl_seconds
        }

    def _evict_expired_sessions(self, now: float) -> None:
        expired = self._expired_session_ids(now)
        for message_id in expired:
            emit_receiver_outcome(ReceiverOutcome.SESSION_EXPIRED)
            self.sessions.pop(message_id, None)
            self._session_activity.pop(message_id, None)

    def _purge_expired_tombstones(self, now: float) -> None:
        expired = [
            message_id
            for message_id, expires_at in self.tombstones.items()
            if now >= expires_at
        ]
        for message_id in expired:
            self.tombstones.pop(message_id, None)

    def _remember_completed(self, message_id: str, now: float) -> None:
        while len(self.tombstones) >= self.max_tombstones:
            self.tombstones.popitem(last=False)
            emit_receiver_outcome(ReceiverOutcome.TOMBSTONE_EVICTED)
        self.tombstones[message_id] = now + self.tombstone_ttl_seconds

    @property
    def active_memory_bytes(self) -> int:
        return sum(
            session.reassembler._received_bytes
            + OVERHEAD_PER_CHUNK * len(session.reassembler.received)
            for session in self.sessions.values()
        )

    def add_chunk(self, chunk: WireEnvelope | Mapping[str, object]) -> bytes | None:
        envelope = chunk
        now = self.clock()
        if not isinstance(envelope, WireEnvelope):
            envelope = WireEnvelope.from_mapping(envelope)
        expired_sessions = self._expired_session_ids(now)
        expired_tombstones = {
            message_id
            for message_id, expires_at in self.tombstones.items()
            if now >= expires_at
        }
        if (
            envelope.message_id in self.tombstones
            and envelope.message_id not in expired_tombstones
        ):
            raise ValueError("message_id is tombstoned; replay rejected")
        session = (
            None
            if envelope.message_id in expired_sessions
            else self.sessions.get(envelope.message_id)
        )
        created = session is None
        if session is None:
            session = ReassemblySession(
                message_id=envelope.message_id,
                authentication_key=self.authentication_key,
                request_retry=self.request_retry,
                request_full_buffer=self.request_full_buffer,
                policy=self.policy,
                clock=self.clock,
            )

        _, _, added_bytes, duplicate = session.reassembler._prepare_chunk(envelope)
        active_memory_bytes = sum(
            active.reassembler._received_bytes
            + OVERHEAD_PER_CHUNK * len(active.reassembler.received)
            for message_id, active in self.sessions.items()
            if message_id not in expired_sessions
        )
        chunk_overhead_bytes = 0 if duplicate else OVERHEAD_PER_CHUNK
        if (
            active_memory_bytes + added_bytes + chunk_overhead_bytes
            > self.max_total_bytes
        ):
            emit_receiver_outcome(ReceiverOutcome.ACTIVE_PAYLOAD_CAP_REJECTED)
            raise ValueError(
                "maximum total active payload bytes exceeded "
                f"({self.max_total_bytes})"
            )

        self._evict_expired_sessions(now)
        self._purge_expired_tombstones(now)
        if created and len(self.sessions) >= self.max_sessions:
            emit_receiver_outcome(ReceiverOutcome.SESSION_CAP_REJECTED)
            raise ValueError(
                f"maximum reassembly sessions reached ({self.max_sessions})"
            )
        if created:
            self.sessions[envelope.message_id] = session
            self._session_activity[envelope.message_id] = now
        try:
            result = session.add_chunk(envelope)
            if session.reassembler.completed:
                self.sessions.pop(envelope.message_id, None)
                self._session_activity.pop(envelope.message_id, None)
                self._remember_completed(envelope.message_id, now)
            elif not duplicate:
                self._session_activity[envelope.message_id] = now
            return result
        except Exception:
            if created:
                self.sessions.pop(envelope.message_id, None)
                self._session_activity.pop(envelope.message_id, None)
            raise
