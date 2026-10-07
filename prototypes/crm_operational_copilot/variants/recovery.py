"""No-write crash recovery variant with mandatory fresh review."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from approvals_store import ApprovalsStore


class RecoveryInvalidationApprovalsStore(ApprovalsStore):
    """Approval schema accepts the variant-only crash_no_write reason."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY, proposal_id TEXT NOT NULL,
                requester_id TEXT NOT NULL, reviewer_id TEXT NOT NULL,
                customer_id TEXT NOT NULL, field_name TEXT NOT NULL,
                proposed_value TEXT NOT NULL, previous_value TEXT NOT NULL,
                record_version INTEGER NOT NULL, policy_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                approved_at INTEGER NULL, state TEXT NOT NULL CHECK(state IN (
                    'PENDING','APPROVED','EXECUTING','COMPLETED',
                    'AUDIT_PENDING','REJECTED','INVALIDATED')),
                reason TEXT NULL CHECK(reason IN (
                    'expired','stale','revoked','policy_changed','scope',
                    'crash_no_write')),
                execution_id TEXT NULL UNIQUE,
                approval_version INTEGER NOT NULL DEFAULT 1
            )"""
        )
        self.connection.commit()

    def return_to_approved(self, approval_id: str) -> bool:
        cursor = self.connection.execute(
            """UPDATE approvals SET state = 'INVALIDATED', execution_id = NULL,
reason = 'crash_no_write', approval_version = approval_version + 1
WHERE approval_id = ? AND state = 'EXECUTING'""",
            (approval_id,),
        )
        self.connection.commit()
        return cursor.rowcount == 1