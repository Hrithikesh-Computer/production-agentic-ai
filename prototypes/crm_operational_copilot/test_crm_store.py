from __future__ import annotations

import sqlite3

import pytest
from crm_store import CRMStore


def test_crm_mutation_and_ledger_commit_together(tmp_path) -> None:
    with CRMStore(tmp_path / "crm.sqlite") as store:
        store.seed("CUST-1", "account_owner", "A. Singh", 100)
        result = store.execute_write(
            execution_id="execution-1",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=1,
            at=110,
            approval_state="COMPLETED",
        )
        assert result is not None
        assert not result.unresolved
        assert store.get_record("CUST-1") is not None
        record = store.get_record("CUST-1")
        assert record is not None
        assert record.record_version == 2
        assert len(store.ledger_rows()) == 1


def test_version_mismatch_does_not_mutate_or_add_ledger(tmp_path) -> None:
    with CRMStore(tmp_path / "crm.sqlite") as store:
        store.seed("CUST-1", "account_owner", "A. Singh", 100)
        result = store.execute_write(
            execution_id="execution-1",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=2,
            at=110,
            approval_state="EXECUTING",
        )
        assert result is None
        record = store.get_record("CUST-1")
        assert record is not None
        assert record.record_version == 1
        assert store.ledger_rows() == []


def test_known_execution_replay_never_mutates_again_and_reports_unresolved(
    tmp_path,
) -> None:
    with CRMStore(tmp_path / "crm.sqlite") as store:
        store.seed("CUST-1", "account_owner", "A. Singh", 100)
        first = store.execute_write(
            execution_id="execution-1",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=1,
            at=110,
            approval_state="EXECUTING",
        )
        replay = store.execute_write(
            execution_id="execution-1",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="Other",
            expected_version=1,
            at=120,
            approval_state="AUDIT_PENDING",
        )
        assert first is not None and replay is not None
        assert replay.replayed and replay.unresolved
        assert replay.field_value == "M. Chen"
        record = store.get_record("CUST-1")
        assert record is not None
        assert record.record_version == 2
        assert len(store.ledger_rows()) == 1


def test_duplicate_ledger_execution_id_is_database_constrained(tmp_path) -> None:
    with CRMStore(tmp_path / "crm.sqlite") as store:
        store.seed("CUST-1", "account_owner", "A. Singh", 100)
        store.execute_write(
            execution_id="execution-1",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=1,
            at=110,
            approval_state="COMPLETED",
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                "INSERT INTO execution_ledger VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("execution-1", "approval-2", "CUST-1", 3, "account_owner", "X", 120),
            )