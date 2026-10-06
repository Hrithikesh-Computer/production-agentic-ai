from __future__ import annotations

import sqlite3

import pytest
from approvals_store import Approval, ApprovalsStore


def _approval(approval_id: str = "approval-1") -> Approval:
    return Approval(
        approval_id=approval_id,
        proposal_id=f"proposal-{approval_id}",
        requester_id="requester",
        reviewer_id="reviewer",
        customer_id="CUST-1001",
        field_name="account_owner",
        proposed_value="M. Chen",
        previous_value="A. Singh",
        record_version=1,
        policy_hash="hash",
        created_at=100,
        expires_at=200,
        approved_at=110,
        state="APPROVED",
    )


def test_approvals_store_round_trip_and_conditional_claim(tmp_path) -> None:
    with ApprovalsStore(tmp_path / "approvals.sqlite") as store:
        store.create(_approval())
        assert store.get("approval-1") == _approval()

        assert store.claim("approval-1", "execution-1", 199)
        assert not store.claim("approval-1", "execution-2", 199)
        claimed = store.get("approval-1")
        assert claimed is not None
        assert claimed.state == "EXECUTING"
        assert claimed.execution_id == "execution-1"


def test_claim_requires_approved_state_and_strictly_future_expiry(tmp_path) -> None:
    with ApprovalsStore(tmp_path / "approvals.sqlite") as store:
        store.create(_approval())
        assert not store.claim("approval-1", "at-expiry", 200)
        assert store.set_state("approval-1", "PENDING")
        assert not store.claim("approval-1", "pending", 100)


def test_schema_checks_state_reason_and_execution_id_uniqueness(tmp_path) -> None:
    with ApprovalsStore(tmp_path / "approvals.sqlite") as store:
        store.create(_approval())
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                "UPDATE approvals SET state = 'crash_no_write' WHERE approval_id = ?",
                ("approval-1",),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                "UPDATE approvals SET reason = 'other' WHERE approval_id = ?",
                ("approval-1",),
            )
        assert store.set_state("approval-1", "APPROVED")
        assert store.claim("approval-1", "shared-execution", 150)
        store.create(_approval("approval-2"))
        with pytest.raises(sqlite3.IntegrityError):
            store.claim("approval-2", "shared-execution", 150)
