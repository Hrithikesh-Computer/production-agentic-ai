"""Single-file SQLite layout variant with one three-table transaction."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, cast

from approvals_store import ApprovalsStore
from audit_store import AuditStore
from crm_store import CRMStore, LedgerResult
from execution_service import CRMExecutionService


class DeferredConnection:
    """Share one SQLite connection and defer commits during execute()."""

    def __init__(self, path: Path) -> None:
        self.raw = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self.raw.row_factory = sqlite3.Row
        self.defer_commits = False
        self.savepoint_open = False

    @property
    def row_factory(self) -> Any:
        return self.raw.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self.raw.row_factory = value

    @property
    def in_transaction(self) -> bool:
        return self.raw.in_transaction

    def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
        if sql.strip().upper() == "BEGIN IMMEDIATE" and self.raw.in_transaction:
            self.raw.execute("SAVEPOINT crm_write")
            self.savepoint_open = True
            return self.raw.execute("SELECT 1")
        return self.raw.execute(sql, parameters)

    def executescript(self, sql: str) -> sqlite3.Cursor:
        return self.raw.executescript(sql)

    def commit(self) -> None:
        if self.savepoint_open:
            self.raw.execute("RELEASE SAVEPOINT crm_write")
            self.savepoint_open = False
        elif not self.defer_commits:
            self.raw.commit()

    def rollback(self) -> None:
        if self.savepoint_open:
            self.raw.execute("ROLLBACK TO SAVEPOINT crm_write")
            self.raw.execute("RELEASE SAVEPOINT crm_write")
            self.savepoint_open = False
        else:
            self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


_shared_connections: dict[tuple[str, int], DeferredConnection] = {}
_shared_lock = threading.Lock()


def _shared_connection(path: str | Path) -> DeferredConnection:
    key = (
        str((Path(path).parent / "crm-variant.sqlite").resolve()),
        threading.get_ident(),
    )
    with _shared_lock:
        connection = _shared_connections.get(key)
        if connection is None:
            connection = DeferredConnection(Path(key[0]))
            _shared_connections[key] = connection
        return connection


class SingleFileApprovalsStore(ApprovalsStore):
    """Approvals adapter sharing the variant's single SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(Path(path).parent / "crm-variant.sqlite")
        self.connection = _shared_connection(path)  # type: ignore[assignment]
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
                    'expired','stale','revoked','policy_changed','scope')),
                execution_id TEXT NULL UNIQUE,
                approval_version INTEGER NOT NULL DEFAULT 1
            )"""
        )
        self.connection.commit()

    def close(self) -> None:
        return None


class SingleFileCRMStore(CRMStore):
    """Store CRM records and ledger entries as typed rows in one table."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(Path(path).parent / "crm-variant.sqlite")
        self.connection = _shared_connection(path)  # type: ignore[assignment]
        self.connection.executescript(
            """CREATE TABLE IF NOT EXISTS crm_data (
                row_kind TEXT NOT NULL CHECK(row_kind IN ('record','ledger')),
                customer_id TEXT NULL, record_version INTEGER NOT NULL,
                field_name TEXT NOT NULL, field_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL, execution_id TEXT NULL,
                approval_id TEXT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS crm_record_key
                ON crm_data(customer_id) WHERE row_kind = 'record';
            CREATE UNIQUE INDEX IF NOT EXISTS crm_execution_key
                ON crm_data(execution_id) WHERE row_kind = 'ledger';
            CREATE VIEW IF NOT EXISTS crm_records AS
                SELECT customer_id, record_version, field_name, field_value,
                       updated_at FROM crm_data WHERE row_kind = 'record';
            CREATE VIEW IF NOT EXISTS execution_ledger AS
                SELECT execution_id, approval_id, customer_id, record_version,
                       field_name, field_value, updated_at FROM crm_data
                WHERE row_kind = 'ledger';"""
        )
        self.connection.commit()

    def seed(
        self, customer_id: str, field_name: str, field_value: str, at: int
    ) -> None:
        existing = self.connection.execute(
            "SELECT 1 FROM crm_records WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        if existing is None:
            self.connection.execute(
                """INSERT INTO crm_data
                (row_kind, customer_id, record_version, field_name, field_value,
                 updated_at) VALUES ('record', ?, 1, ?, ?, ?)""",
                (customer_id, field_name, field_value, at),
            )
        self.connection.commit()

    def execute_write(
        self,
        *,
        execution_id: str,
        approval_id: str,
        customer_id: str,
        field_name: str,
        proposed_value: str,
        expected_version: int,
        at: int,
        approval_state: str,
    ) -> LedgerResult | None:
        existing = self.connection.execute(
            "SELECT * FROM execution_ledger WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        if existing is not None:
            return self._ledger_result(existing, approval_state, replayed=True)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = self.connection.execute(
                """UPDATE crm_data SET record_version = record_version + 1,
                field_value = ?, updated_at = ?
                WHERE row_kind = 'record' AND customer_id = ?
                  AND field_name = ? AND record_version = ?""",
                (proposed_value, at, customer_id, field_name, expected_version),
            )
            if cursor.rowcount != 1:
                self.connection.rollback()
                return None
            record = self.get_record(customer_id, field_name)
            assert record is not None
            self.connection.execute(
                """INSERT INTO crm_data
                (row_kind, customer_id, record_version, field_name, field_value,
                 updated_at, execution_id, approval_id)
                VALUES ('ledger', ?, ?, ?, ?, ?, ?, ?)""",
                (customer_id, record.record_version, field_name, proposed_value,
                 at, execution_id, approval_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        row = self.connection.execute(
            "SELECT * FROM execution_ledger WHERE execution_id = ?", (execution_id,)
        ).fetchone()
        assert row is not None
        return self._ledger_result(row, approval_state, replayed=False)

    def close(self) -> None:
        return None


class SingleFileAuditStore(AuditStore):
    """Audit adapter sharing the variant's single SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(Path(path).parent / "crm-variant.sqlite")
        self.connection = _shared_connection(path)  # type: ignore[assignment]
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS audit_events (
                audit_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL,
                execution_id TEXT NULL, event_type TEXT NOT NULL,
                event_ts INTEGER NOT NULL, crm_customer_id TEXT NULL,
                crm_record_version INTEGER NULL, state_before TEXT NULL,
                state_after TEXT NULL, reason TEXT NULL,
                reconciled INTEGER NOT NULL DEFAULT 0)"""
        )
        self.connection.commit()
        self.fail_next_write = False

    def close(self) -> None:
        return None


class SingleFileExecutionService(CRMExecutionService):
    """Commit the shared CRM, ledger, and audit writes as one transaction."""

    def execute(self, approval_id: str, **kwargs: Any):
        connection = cast(DeferredConnection, self.approvals.connection)
        connection.defer_commits = True
        try:
            result = super().execute(approval_id, **kwargs)
            if result.status == "unresolved":
                connection.rollback()
            else:
                connection.defer_commits = False
                connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.defer_commits = False


def reset_shared_connections() -> None:
    """Close adapter connections between isolated scenario runs."""
    with _shared_lock:
        for connection in _shared_connections.values():
            connection.close()
        _shared_connections.clear()