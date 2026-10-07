from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parents[3] / "tests"
sys.path.insert(0, str(TESTS_DIR))
import test_crm_validation_scenarios as baseline_scenarios  # noqa: E402

from variants.recovery import RecoveryInvalidationApprovalsStore  # noqa: E402


def test_s10_no_write_recovery_invalidates_and_requires_fresh_review(
    tmp_path: Path,
) -> None:
    with patch.multiple(
        baseline_scenarios,
        ApprovalsStore=RecoveryInvalidationApprovalsStore,
    ):
        service, approvals, crm, audit, *_ = baseline_scenarios._system(tmp_path)
        assert approvals.claim("approval-1", "crashed", 150)
        result = service.recover()[0]
        approval = approvals.get("approval-1")
        assert result.reason == "recovered_without_crm_write"
        assert approval is not None
        assert approval.state == "INVALIDATED"
        assert approval.reason == "crash_no_write"
        assert approval.execution_id is None
        assert crm.ledger_rows() == []
        assert audit.count() == 0