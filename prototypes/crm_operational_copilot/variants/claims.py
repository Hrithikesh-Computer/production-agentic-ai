"""Alternative and broken approval claim mechanisms."""

from __future__ import annotations

import threading

from approvals_store import ApprovalsStore


class ImmediateClaimApprovalsStore(ApprovalsStore):
    """Read-then-write claim serialized with BEGIN IMMEDIATE."""

    def claim(self, approval_id: str, execution_id: str, at: int) -> bool:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT state, expires_at FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if row is None or row["state"] != "APPROVED" or row["expires_at"] <= at:
                self.connection.rollback()
                return False
            cursor = self.connection.execute(
                "UPDATE approvals SET state = 'EXECUTING', execution_id = ? "
                "WHERE approval_id = ?",
                (execution_id, approval_id),
            )
            self.connection.commit()
            return cursor.rowcount == 1
        except Exception:
            self.connection.rollback()
            raise


class BrokenReadThenWriteApprovalsStore(ApprovalsStore):
    """Intentionally unsafe no-transaction claim used only as a control."""

    barrier: threading.Barrier | None = None

    def claim(self, approval_id: str, execution_id: str, at: int) -> bool:
        row = self.connection.execute(
            "SELECT state, expires_at FROM approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        if row is None or row["state"] != "APPROVED" or row["expires_at"] <= at:
            return False
        barrier = type(self).barrier
        if barrier is not None:
            barrier.wait(timeout=30)
        self.connection.execute(
            "UPDATE approvals SET state = 'EXECUTING', execution_id = ? "
            "WHERE approval_id = ?",
            (execution_id, approval_id),
        )
        self.connection.commit()
        return True