"""SQLite CRM records and transactional execution ledger."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CRMRecord:
    customer_id: str
    record_version: int
    field_name: str
    field_value: str
    updated_at: int


@dataclass(frozen=True)
class LedgerResult:
    execution_id: str
    approval_id: str
    customer_id: str
    record_version: int
    field_name: str
    field_value: str
    updated_at: int
    unresolved: bool
    replayed: bool = False


class CRMStore:
    """Own one SQLite connection for CRM records and their write ledger."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS crm_records (
                customer_id TEXT PRIMARY KEY,
                record_version INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS execution_ledger (
                execution_id TEXT NOT NULL UNIQUE,
                approval_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                record_version INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> CRMStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def seed(
        self, customer_id: str, field_name: str, field_value: str, at: int
    ) -> None:
        self.connection.execute(
            """INSERT INTO crm_records
            (customer_id, record_version, field_name, field_value, updated_at)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(customer_id) DO NOTHING""",
            (customer_id, field_name, field_value, at),
        )
        self.connection.commit()

    def get_record(
        self, customer_id: str, field_name: str | None = None
    ) -> CRMRecord | None:
        if field_name is None:
            row = self.connection.execute(
                "SELECT * FROM crm_records WHERE customer_id = ?", (customer_id,)
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT * FROM crm_records WHERE customer_id = ? AND field_name = ?",
                (customer_id, field_name),
            ).fetchone()
        return CRMRecord(**dict(row)) if row is not None else None

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
            "SELECT * FROM execution_ledger WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        if existing is not None:
            return self._ledger_result(existing, approval_state, replayed=True)

        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = self.connection.execute(
                """UPDATE crm_records
SET record_version = record_version + 1, field_value = ?, updated_at = ?
WHERE customer_id = ? AND field_name = ? AND record_version = ?;""",
                (proposed_value, at, customer_id, field_name, expected_version),
            )
            if cursor.rowcount != 1:
                self.connection.rollback()
                return None
            record = self.get_record(customer_id, field_name)
            assert record is not None
            self.connection.execute(
                """INSERT INTO execution_ledger
(execution_id, approval_id, customer_id, record_version, field_name,
 field_value, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?);""",
                (
                    execution_id,
                    approval_id,
                    customer_id,
                    record.record_version,
                    field_name,
                    proposed_value,
                    at,
                ),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        row = self.connection.execute(
            "SELECT * FROM execution_ledger WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        assert row is not None
        return self._ledger_result(row, approval_state, replayed=False)

    def ledger_result(
        self, execution_id: str, approval_state: str
    ) -> LedgerResult | None:
        row = self.connection.execute(
            "SELECT * FROM execution_ledger WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        return self._ledger_result(row, approval_state, replayed=True) if row else None

    def ledger_rows(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM execution_ledger ORDER BY execution_id"
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _ledger_result(
        row: sqlite3.Row,
        approval_state: str,
        *,
        replayed: bool,
    ) -> LedgerResult:
        unresolved = approval_state in {"EXECUTING", "AUDIT_PENDING"}
        return LedgerResult(
            execution_id=row["execution_id"],
            approval_id=row["approval_id"],
            customer_id=row["customer_id"],
            record_version=row["record_version"],
            field_name=row["field_name"],
            field_value=row["field_value"],
            updated_at=row["updated_at"],
            unresolved=unresolved,
            replayed=replayed,
        )

    def export_state(self) -> str:
        records = [dict(row) for row in self.connection.execute(
            "SELECT * FROM crm_records ORDER BY customer_id"
        )]
        ledger = self.ledger_rows()
        return json.dumps({"records": records, "ledger": ledger}, sort_keys=True)