"""SQLite persistence for approval decisions and conditional execution claims."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ApprovalState = Literal[
    "PENDING",
    "APPROVED",
    "EXECUTING",
    "COMPLETED",
    "AUDIT_PENDING",
    "REJECTED",
    "INVALIDATED",
]
InvalidationReason = Literal["expired", "stale", "revoked", "policy_changed", "scope"]


@dataclass(frozen=True)
class Approval:
    approval_id: str
    proposal_id: str
    requester_id: str
    reviewer_id: str
    customer_id: str
    field_name: str
    proposed_value: str
    previous_value: str
    record_version: int
    policy_hash: str
    created_at: int
    expires_at: int
    approved_at: int | None = None
    state: ApprovalState = "PENDING"
    reason: InvalidationReason | None = None
    execution_id: str | None = None
    approval_version: int = 1


class ApprovalsStore:
    """Own one SQLite connection for the approvals database file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                requester_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                proposed_value TEXT NOT NULL,
                previous_value TEXT NOT NULL,
                record_version INTEGER NOT NULL,
                policy_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                approved_at INTEGER NULL,
                state TEXT NOT NULL CHECK(state IN (
                    'PENDING','APPROVED','EXECUTING','COMPLETED',
                    'AUDIT_PENDING','REJECTED','INVALIDATED'
                )),
                reason TEXT NULL CHECK(reason IN (
                    'expired','stale','revoked','policy_changed','scope'
                )),
                execution_id TEXT NULL UNIQUE,
                approval_version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ApprovalsStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def create(self, approval: Approval) -> None:
        self.connection.execute(
            """
            INSERT INTO approvals (
                approval_id, proposal_id, requester_id, reviewer_id, customer_id,
                field_name, proposed_value, previous_value, record_version,
                policy_hash, created_at, expires_at, approved_at, state, reason,
                execution_id, approval_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.approval_id,
                approval.proposal_id,
                approval.requester_id,
                approval.reviewer_id,
                approval.customer_id,
                approval.field_name,
                approval.proposed_value,
                approval.previous_value,
                approval.record_version,
                approval.policy_hash,
                approval.created_at,
                approval.expires_at,
                approval.approved_at,
                approval.state,
                approval.reason,
                approval.execution_id,
                approval.approval_version,
            ),
        )
        self.connection.commit()

    def get(self, approval_id: str) -> Approval | None:
        row = self.connection.execute(
            "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()
        if row is None:
            return None
        return Approval(**dict(row))

    def set_review(
        self, approval_id: str, reviewer_id: str, at: int, approve: bool
    ) -> bool:
        state: ApprovalState = "APPROVED" if approve else "REJECTED"
        cursor = self.connection.execute(
            """
            UPDATE approvals
            SET reviewer_id = ?, approved_at = ?, state = ?,
                approval_version = approval_version + 1
            WHERE approval_id = ? AND state = 'PENDING'
            """,
            (reviewer_id, at if approve else None, state, approval_id),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def claim(self, approval_id: str, execution_id: str, at: int) -> bool:
        cursor = self.connection.execute(
            """UPDATE approvals
SET state = 'EXECUTING', execution_id = ?
WHERE approval_id = ?
  AND state = 'APPROVED'
  AND expires_at > ?;""",
            (execution_id, approval_id, at),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def set_state(
        self,
        approval_id: str,
        state: ApprovalState,
        *,
        reason: InvalidationReason | None = None,
    ) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE approvals
            SET state = ?, reason = ?, approval_version = approval_version + 1
            WHERE approval_id = ?
            """,
            (state, reason, approval_id),
        )
        self.connection.commit()
        return cursor.rowcount == 1