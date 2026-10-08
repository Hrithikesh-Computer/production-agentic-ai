"""Pytest adapter for selecting one isolated CRM variant at a time."""

from __future__ import annotations

import os
from typing import Any

import pytest
from approvals_store import ApprovalsStore
from audit_store import AuditStore
from crm_store import CRMStore
from execution_service import CRMExecutionService

from variants.claims import (
    BrokenReadThenWriteApprovalsStore,
    ImmediateClaimApprovalsStore,
)
from variants.recovery import RecoveryInvalidationApprovalsStore
from variants.store_layout import (
    SingleFileApprovalsStore,
    SingleFileAuditStore,
    SingleFileCRMStore,
    SingleFileExecutionService,
    reset_shared_connections,
)


def variant_components(name: str) -> tuple[type, type, type, type]:
    if name == "store-layout-b":
        return (
            SingleFileApprovalsStore,
            SingleFileCRMStore,
            SingleFileAuditStore,
            SingleFileExecutionService,
        )
    if name == "recovery-b":
        return (
            RecoveryInvalidationApprovalsStore,
            CRMStore,
            AuditStore,
            CRMExecutionService,
        )
    if name == "claim-b":
        return (
            ImmediateClaimApprovalsStore,
            CRMStore,
            AuditStore,
            CRMExecutionService,
        )
    if name == "broken-control":
        return (
            BrokenReadThenWriteApprovalsStore,
            CRMStore,
            AuditStore,
            CRMExecutionService,
        )
    return (ApprovalsStore, CRMStore, AuditStore, CRMExecutionService)


def pytest_collection_modifyitems(items: list[Any]) -> None:
    """Inject selected adapters into the baseline scenario module at collection."""
    name = os.environ.get("CRM_VARIANT", "baseline")
    components = variant_components(name)
    for item in items:
        module = getattr(item, "module", None)
        if module is None or module.__name__ != "test_crm_validation_scenarios":
            continue
        (
            module.ApprovalsStore,
            module.CRMStore,
            module.AuditStore,
            module.CRMExecutionService,
        ) = components
        if (
            name == "broken-control"
            and "test_s09_fifty_separate_processes" in item.name
        ):
            item.add_marker(
                pytest.mark.skip(reason="variant race is checked with a thread barrier")
            )


def pytest_runtest_teardown(item: Any, nextitem: Any) -> None:
    del nextitem
    if (
        getattr(item, "module", None) is not None
        and os.environ.get("CRM_VARIANT") == "store-layout-b"
    ):
        reset_shared_connections()