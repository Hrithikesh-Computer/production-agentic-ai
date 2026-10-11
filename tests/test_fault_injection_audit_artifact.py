from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_CHECKER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_fault_injection_approval_audit.py"
)
_SPEC = importlib.util.spec_from_file_location("fault_audit_checker", _CHECKER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CHECKER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECKER)
unique_rows = _CHECKER.unique_rows


def test_exact_duplicate_fault_rows_are_collapsed():
    row = {
        "campaign_id": "campaign-1",
        "variant": "fixed",
        "fault_point": "audit-write-failure",
        "classification": "RECOVERABLE_FAIL_CLOSED",
    }

    unique, duplicate_count = unique_rows([row, row.copy()])

    assert unique == [row]
    assert duplicate_count == 1


def test_conflicting_fault_rows_with_same_key_are_rejected():
    first = {
        "campaign_id": "campaign-1",
        "variant": "fixed",
        "fault_point": "audit-write-failure",
        "classification": "RECOVERABLE_FAIL_CLOSED",
    }
    second = {**first, "classification": "FAIL-OPEN"}

    with pytest.raises(ValueError, match="conflicting rows"):
        unique_rows([first, second])


def test_missing_campaign_key_is_rejected():
    with pytest.raises(ValueError, match="missing a campaign key"):
        unique_rows([{"campaign_id": "campaign-1", "variant": "fixed"}])