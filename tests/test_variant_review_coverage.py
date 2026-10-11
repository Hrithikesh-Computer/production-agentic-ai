from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from audit_store import AuditEvent

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
import test_crm_validation_scenarios as baseline_scenarios  # noqa: E402
from variants.store_layout import (  # noqa: E402
    SingleFileApprovalsStore,
    SingleFileAuditStore,
    SingleFileCRMStore,
    SingleFileExecutionService,
    reset_shared_connections,
)

REVIEWER = "reviewer"
REVIEWER_SCOPE = "approve:crm-writes"


def _store_layout_system(tmp_path: Path):
    return patch.multiple(
        baseline_scenarios,
        ApprovalsStore=SingleFileApprovalsStore,
        CRMStore=SingleFileCRMStore,
        AuditStore=SingleFileAuditStore,
        CRMExecutionService=SingleFileExecutionService,
    )


def _assert_failed_review_is_rolled_back(approvals, audit) -> None:
    approval = approvals.get("approval-1")
    assert approval is not None and approval.state == "PENDING"
    assert audit.events_for_approval("approval-1") == []


def _review(service, *, approve: bool = True):
    return service.review(
        "approval-1",
        reviewer_id=REVIEWER,
        approve=approve,
        reviewer_scope=REVIEWER_SCOPE,
    )


def test_store_layout_review_with_healthy_audit_persists_both(tmp_path: Path) -> None:
    reset_shared_connections()
    try:
        with _store_layout_system(tmp_path):
            service, approvals, _, audit, *_ = baseline_scenarios._system(
                tmp_path, state="PENDING"
            )

            result = _review(service)

            events = audit.events_for_approval("approval-1")
            approval = approvals.get("approval-1")
            assert result.status == "completed"
            assert approval is not None and approval.state == "APPROVED"
            assert len(events) == 1
            assert events[0].event_type == "approval_approved"
    finally:
        reset_shared_connections()


def test_store_layout_review_audit_failure_stays_blocked_until_recovery(
    tmp_path: Path,
) -> None:
    """Separate-store review failure remains unresolved until recovery."""
    reset_shared_connections()
    try:
        with _store_layout_system(tmp_path):
            service, approvals, _, audit, *_ = baseline_scenarios._system(
                tmp_path, state="PENDING"
            )
            audit.fail_next_write = True

            result = _review(service)

            approval = approvals.get("approval-1")
            assert result.status == "unresolved"
            assert result.reason == "approval_audit_pending"
            assert approval is not None and approval.state == "AUDIT_PENDING"
            assert audit.events_for_approval("approval-1") == []
            execution = baseline_scenarios._execute(service)
            assert execution.status == "unresolved"
            assert approvals.get("approval-1").state == "AUDIT_PENDING"
            assert audit.events_for_approval("approval-1") == []

            recovered = service.recover()
            approval = approvals.get("approval-1")
            events = audit.events_for_approval("approval-1")
            assert recovered[0].status == "completed"
            assert approval is not None and approval.state == "APPROVED"
            assert [event.event_type for event in events] == ["approval_approved"]
    finally:
        reset_shared_connections()


def test_review_audit_failure_is_not_execution_authority(
    tmp_path: Path,
) -> None:
    """Directly stage review state and verify failed audit cannot authorize."""
    reset_shared_connections()
    try:
        with _store_layout_system(tmp_path):
            service, approvals, _, audit, *_ = baseline_scenarios._system(
                tmp_path, state="PENDING"
            )
            audit.fail_next_write = True

            assert approvals.set_review("approval-1", REVIEWER, 150, True)
            with pytest.raises(OSError, match="injected audit-store write failure"):
                audit.write(
                    AuditEvent(
                        audit_id="audit-1",
                        approval_id="approval-1",
                        execution_id=None,
                        event_type="approval_approved",
                        event_ts=150,
                        crm_customer_id="CUST-1",
                        crm_record_version=1,
                        state_before="PENDING",
                        state_after="APPROVED",
                    )
                )

            approval = approvals.get("approval-1")
            assert approval is not None and approval.state == "AUDIT_PENDING"
            result = baseline_scenarios._execute(service)
            assert result.status == "unresolved"
    finally:
        reset_shared_connections()