"""Deterministic local identity and current-scope provider."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal

IdentityStatus = Literal["active", "revoked", "suspended"]


@dataclass(frozen=True)
class Identity:
    principal: str
    tenant: str
    scopes: frozenset[str]
    status: IdentityStatus = "active"
    revoked_at: int | None = None
    reason: str | None = None
    expires_at: int | None = None


@dataclass(frozen=True)
class IdentityDecision:
    identity: Identity | None
    allowed: bool
    reason: str


class LocalIdentityProvider:
    """Resolve identities and evaluate live status and scope with an injected clock."""

    def __init__(
        self,
        identities: list[Identity] | None = None,
        *,
        clock: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        self._identities: dict[str, Identity] = {}
        self._clock = clock
        for identity in identities or []:
            self.put(identity)

    def put(self, identity: Identity) -> None:
        if not identity.principal:
            raise ValueError("principal must be non-empty")
        if not identity.tenant:
            raise ValueError("tenant must be non-empty")
        if identity.status not in {"active", "revoked", "suspended"}:
            raise ValueError("unsupported identity status")
        self._identities[identity.principal] = identity

    def resolve(self, principal: str) -> Identity | None:
        return self._identities.get(principal)

    def authorize(
        self, principal: str, scope: str, *, at: int | None = None
    ) -> IdentityDecision:
        identity = self.resolve(principal)
        if identity is None:
            return IdentityDecision(None, False, "identity_missing")
        current = self._clock() if at is None else at
        if identity.status == "revoked" or (
            identity.revoked_at is not None and current >= identity.revoked_at
        ):
            return IdentityDecision(identity, False, identity.reason or "revoked")
        if identity.status == "suspended":
            return IdentityDecision(identity, False, identity.reason or "suspended")
        if identity.expires_at is not None and current >= identity.expires_at:
            return IdentityDecision(identity, False, identity.reason or "expired")
        if scope not in identity.scopes:
            return IdentityDecision(identity, False, "scope")
        return IdentityDecision(identity, True, "allowed")