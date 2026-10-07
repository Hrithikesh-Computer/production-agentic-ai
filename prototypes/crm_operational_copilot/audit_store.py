"""SQLite audit persistence with deterministic write-failure injection."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuditEvent:
    audit_id: str
    approval_id: str
    execution_id: str | None
    event_type: str
    event_ts: int
    crm_customer_id: str | None
    crm_record_version: int | None
    state_before: str | None
    state_after: str | None
    reason: str | None = None
    reconciled: bool = False


class AuditStore:
    """Own one SQLite connection for audit events."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS audit_events (
                audit_id TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                execution_id TEXT NULL,
                event_type TEXT NOT NULL,
                event_ts INTEGER NOT NULL,
                crm_customer_id TEXT NULL,
                crm_record_version INTEGER NULL,
                state_before TEXT NULL,
                state_after TEXT NULL,
                reason TEXT NULL,
                reconciled INTEGER NOT NULL DEFAULT 0
            )"""
        )
        self.connection.commit()
        self.fail_next_write = False

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> AuditStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def write(self, event: AuditEvent) -> None:
        if self.fail_next_write:
            self.fail_next_write = False
            raise OSError("injected audit-store write failure")
        self.connection.execute(
            """INSERT INTO audit_events (
                audit_id, approval_id, execution_id, event_type, event_ts,
                crm_customer_id, crm_record_version, state_before, state_after,
                reason, reconciled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.audit_id,
                event.approval_id,
                event.execution_id,
                event.event_type,
                event.event_ts,
                event.crm_customer_id,
                event.crm_record_version,
                event.state_before,
                event.state_after,
                event.reason,
                int(event.reconciled),
            ),
        )
        self.connection.commit()

    def get(self, audit_id: str) -> AuditEvent | None:
        row = self.connection.execute(
            "SELECT * FROM audit_events WHERE audit_id = ?", (audit_id,)
        ).fetchone()
        if row is None:
            return None
        values = dict(row)
        values["reconciled"] = bool(values["reconciled"])
        return AuditEvent(**values)

    def events_for_approval(self, approval_id: str) -> list[AuditEvent]:
        rows = self.connection.execute(
            "SELECT * FROM audit_events WHERE approval_id = ? "
            "ORDER BY event_ts, audit_id",
            (approval_id,),
        ).fetchall()
        return [
            AuditEvent(**(dict(row) | {"reconciled": bool(row["reconciled"])}))
            for row in rows
        ]

    def for_execution(self, execution_id: str) -> list[AuditEvent]:
        rows = self.connection.execute(
            """SELECT * FROM audit_events WHERE execution_id = ?
ORDER BY event_ts, audit_id""",
            (execution_id,),
        ).fetchall()
        return [
            AuditEvent(**(dict(row) | {"reconciled": bool(row["reconciled"])}))
            for row in rows
        ]

    def mark_reconciled(self, audit_id: str) -> bool:
        cursor = self.connection.execute(
            "UPDATE audit_events SET reconciled = 1 WHERE audit_id = ?",
            (audit_id,),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def count(self, approval_id: str | None = None) -> int:
        if approval_id is None:
            row = self.connection.execute(
                "SELECT COUNT(*) AS event_count FROM audit_events"
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT COUNT(*) AS event_count FROM audit_events "
                "WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        assert row is not None
        return int(row["event_count"])