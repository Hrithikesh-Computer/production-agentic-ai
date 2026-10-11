from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "tests"),
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


@pytest.mark.parametrize(
    "service_type",
    [
        SingleFileExecutionService,
        SingleFileExecutionServiceWithAtomicReview,
    ],
    ids=["current", "fixed"],
)
def test_approval_audit_timestamp_is_not_before_approval_creation(
    service_type: type,
    tmp_path: Path,
) -> None:
    reset_shared_connections()
    try:
        with patch.multiple(
            scenarios,
            ApprovalsStore=SingleFileApprovalsStore,
            CRMStore=SingleFileCRMStore,
            AuditStore=SingleFileAuditStore,
            CRMExecutionService=service_type,
        ):
            service, approvals, _, audit, *_ = scenarios._system(
                tmp_path, state="PENDING"
            )
            service.clock = lambda: 90

            result = service.review(
                "approval-1",
                reviewer_id="reviewer",
                approve=True,
                reviewer_scope="approve:crm-writes",
            )

            approval = approvals.get("approval-1")
            events = [
                event
                for event in audit.events_for_approval("approval-1")
                if event.event_type == "approval_approved"
            ]
            assert result.status == "completed"
            assert approval is not None
            assert approval.approved_at is not None
            assert approval.approved_at >= approval.created_at
            assert events
            for event in events:
                assert event.event_ts >= approval.created_at
    finally:
        reset_shared_connections()