from __future__ import annotations

from identity_provider import Identity, LocalIdentityProvider


def test_identity_resolution_returns_current_identity_facts() -> None:
    identity = Identity(
        principal="requester",
        tenant="tenant-a",
        scopes=frozenset({"write:accounts"}),
        reason="seeded fixture",
        expires_at=200,
    )
    provider = LocalIdentityProvider([identity], clock=lambda: 100)

    assert provider.resolve("requester") == identity
    assert provider.resolve("unknown") is None
    assert provider.authorize("requester", "write:accounts").allowed


def test_identity_scope_status_revocation_and_expiry_are_live() -> None:
    provider = LocalIdentityProvider(
        [
            Identity("revoked", "tenant-a", frozenset({"write"}), "revoked"),
            Identity("suspended", "tenant-a", frozenset({"write"}), "suspended"),
            Identity(
                "scheduled", "tenant-a", frozenset({"write"}), revoked_at=110
            ),
            Identity("expired", "tenant-a", frozenset({"write"}), expires_at=110),
            Identity("active", "tenant-a", frozenset({"read"})),
        ],
        clock=lambda: 100,
    )

    assert provider.authorize("revoked", "write").reason == "revoked"
    assert provider.authorize("suspended", "write").reason == "suspended"
    assert provider.authorize("scheduled", "write").allowed
    assert provider.authorize("scheduled", "write", at=110).reason == "revoked"
    assert provider.authorize("expired", "write", at=110).reason == "expired"
    assert provider.authorize("active", "write").reason == "scope"
    assert provider.authorize("missing", "write").reason == "identity_missing"


def test_identity_record_preserves_tenant_scope_reason_and_revocation_time() -> None:
    identity = Identity(
        "reviewer",
        "tenant-b",
        frozenset({"approve:crm-writes"}),
        revoked_at=123,
        reason="credential withdrawn",
    )
    provider = LocalIdentityProvider([identity], clock=lambda: 123)

    resolved = provider.resolve("reviewer")
    assert resolved is not None
    assert resolved.tenant == "tenant-b"
    assert resolved.scopes == frozenset({"approve:crm-writes"})
    assert resolved.revoked_at == 123
    assert resolved.reason == "credential withdrawn"
    assert provider.authorize("reviewer", "approve:crm-writes").reason == (
        "credential withdrawn"
    )