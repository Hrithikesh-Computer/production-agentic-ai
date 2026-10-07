from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parents[3] / "tests"
sys.path.insert(0, str(TESTS_DIR))
import test_crm_validation_scenarios as baseline_scenarios  # noqa: E402

from variants.store_layout import (  # noqa: E402
    SingleFileApprovalsStore,
    SingleFileAuditStore,
    SingleFileCRMStore,
    SingleFileExecutionService,
    reset_shared_connections,
)


def _store_layout_system(tmp_path: Path):
    return patch.multiple(
        baseline_scenarios,
        ApprovalsStore=SingleFileApprovalsStore,
        CRMStore=SingleFileCRMStore,
        AuditStore=SingleFileAuditStore,
        CRMExecutionService=SingleFileExecutionService,
    )


def test_s11_shared_transaction_rolls_back_after_approval_store_failure(
    tmp_path: Path, monkeypatch,
) -> None:
    reset_shared_connections()
    with _store_layout_system(tmp_path):
        service, approvals, crm, audit, *_ = baseline_scenarios._system(tmp_path)
        original_set_state = approvals.set_state

        def fail_completed(approval_id: str, state: str, *, reason: str | None = None):
            if state == "COMPLETED":
                raise OSError("injected approvals-store outage")
            return original_set_state(approval_id, state, reason=reason)

        monkeypatch.setattr(approvals, "set_state", fail_completed)
        result = baseline_scenarios._execute(service)
        approval = approvals.get("approval-1")
        record = crm.get_record("CUST-1")
        assert result.status == "unresolved"
        assert approval is not None and approval.state == "APPROVED"
        assert record is not None and record.record_version == 1
        assert crm.ledger_rows() == []
        assert audit.count() == 0
    reset_shared_connections()


def test_s12_shared_transaction_rolls_back_crm_and_ledger_on_audit_failure(
    tmp_path: Path,
) -> None:
    reset_shared_connections()
    with _store_layout_system(tmp_path):
        service, approvals, crm, audit, *_ = baseline_scenarios._system(tmp_path)
        audit.fail_next_write = True
        result = baseline_scenarios._execute(service)
        approval = approvals.get("approval-1")
        record = crm.get_record("CUST-1")
        assert result.status == "unresolved"
        assert approval is not None and approval.state == "APPROVED"
        assert record is not None and record.record_version == 1
        assert crm.ledger_rows() == []
        assert audit.count() == 0
        assert approvals.connection is crm.connection is audit.connection
        assert approvals.path == crm.path == audit.path
        table_count = approvals.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]
        assert table_count == 3
    reset_shared_connections()