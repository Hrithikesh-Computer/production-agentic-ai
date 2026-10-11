from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
sys.path[:0] = [
    str(TESTS_DIR),
    str(ROOT / "prototypes" / "crm_operational_copilot"),
    str(ROOT / "04-reference-implementation"),
]
import test_crm_validation_scenarios as scenarios  # noqa: E402
from variants.store_layout import (  # noqa: E402
    SingleFileApprovalsStore,
    SingleFileAuditStore,
    SingleFileCRMStore,
    SingleFileExecutionService,
    reset_shared_connections,
)
from variants.store_layout_fixed import (  # noqa: E402
    SingleFileExecutionServiceWithAtomicReview,
)

REVIEWER = "reviewer"
REVIEWER_SCOPE = "approve:crm-writes"


def _patched_stores(service_type):
    return patch.multiple(
        scenarios,
        ApprovalsStore=SingleFileApprovalsStore,
        CRMStore=SingleFileCRMStore,
        AuditStore=SingleFileAuditStore,
        CRMExecutionService=service_type,
    )


def _safe_failed_review(approvals, audit) -> None:
    approval = approvals.get("approval-1")
    assert approval is not None and approval.state == "PENDING"
    assert audit.events_for_approval("approval-1") == []


def _review(service, *, approve=True):
    return service.review(
        "approval-1",
        reviewer_id=REVIEWER,
        approve=approve,
        reviewer_scope=REVIEWER_SCOPE,
    )


def test_fixed_review_with_healthy_audit_persists_state_and_event(
    tmp_path: Path,
) -> None:
    reset_shared_connections()
    try:
        with _patched_stores(SingleFileExecutionServiceWithAtomicReview):
            service, approvals, crm, audit, *_ = scenarios._system(
                tmp_path, state="PENDING"
            )

            result = _review(service)

            approval = approvals.get("approval-1")
            events = audit.events_for_approval("approval-1")
            assert result.status == "completed"
            assert approval is not None and approval.state == "APPROVED"
            assert [event.event_type for event in events] == ["approval_approved"]
    finally:
        reset_shared_connections()


def test_fixed_review_audit_failure_rolls_back_and_cannot_execute(
    tmp_path: Path,
) -> None:
    """I1b: staged approval state and audit share one SQLite commit boundary."""
    reset_shared_connections()
    try:
        with _patched_stores(SingleFileExecutionServiceWithAtomicReview):
            service, approvals, crm, audit, *_ = scenarios._system(
                tmp_path, state="PENDING"
            )
            audit.fail_next_write = True

            result = _review(service)
            execution = scenarios._execute(service)

            assert result.status == "unresolved"
            _safe_failed_review(approvals, audit)
            assert execution.status == "pending"
            assert crm.ledger_rows() == []
            assert audit.for_execution(execution.execution_id or "") == []
    finally:
        reset_shared_connections()


@pytest.mark.parametrize("approve", [True, False], ids=["approve", "reject"])
@pytest.mark.parametrize("raise_after_insert", [False, True], ids=["before", "after"])
def test_fixed_review_failure_is_retryable_without_partial_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approve: bool,
    raise_after_insert: bool,
) -> None:
    reset_shared_connections()
    try:
        with _patched_stores(SingleFileExecutionServiceWithAtomicReview):
            service, approvals, crm, audit, *_ = scenarios._system(
                tmp_path, state="PENDING"
            )
            original_write = audit.write
            if raise_after_insert:
                def write_then_raise(event):
                    original_write(event)
                    raise OSError("injected error after staged audit insert")

                monkeypatch.setattr(audit, "write", write_then_raise)
            else:
                audit.fail_next_write = True

            failed = _review(service, approve=approve)
            assert failed.audit_error is not None
            assert failed.status == "unresolved"
            _safe_failed_review(approvals, audit)
            assert crm.ledger_rows() == []
            assert scenarios._execute(service).status == "pending"

            monkeypatch.setattr(audit, "write", original_write)
            retried = _review(service, approve=approve)

            assert retried.status == ("completed" if approve else "rejected")
            approval = approvals.get("approval-1")
            assert approval is not None
            assert approval.state == ("APPROVED" if approve else "REJECTED")
            events = audit.events_for_approval("approval-1")
            assert [event.event_type for event in events] == [
                "approval_approved" if approve else "approval_rejected"
            ]
            assert crm.ledger_rows() == []
    finally:
        reset_shared_connections()


def test_separate_store_review_failure_stays_blocked_until_recovery(
    tmp_path: Path,
) -> None:
    """Separate stores require an explicit recover step after audit failure."""
    reset_shared_connections()
    try:
        with _patched_stores(SingleFileExecutionService):
            service, approvals, crm, audit, *_ = scenarios._system(
                tmp_path, state="PENDING"
            )
            audit.fail_next_write = True

            result = _review(service)

            approval = approvals.get("approval-1")
            assert result.status == "unresolved"
            assert approval is not None and approval.state == "AUDIT_PENDING"
            assert audit.events_for_approval("approval-1") == []
            assert scenarios._execute(service).status == "unresolved"
            assert crm.get_record("CUST-1").record_version == 1
            recovered = service.recover()
            approval = approvals.get("approval-1")
            events = audit.events_for_approval("approval-1")
            assert recovered[0].status == "completed"
            assert approval is not None and approval.state == "APPROVED"
            assert [event.event_type for event in events] == ["approval_approved"]
    finally:
        reset_shared_connections()