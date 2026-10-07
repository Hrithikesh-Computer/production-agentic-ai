from __future__ import annotations

import pytest
from audit_store import AuditEvent, AuditStore


def _event(audit_id: str = "audit-1") -> AuditEvent:
    return AuditEvent(
        audit_id=audit_id,
        approval_id="approval-1",
        execution_id="execution-1",
        event_type="execution_succeeded",
        event_ts=123,
        crm_customer_id="CUST-1",
        crm_record_version=2,
        state_before="EXECUTING",
        state_after="COMPLETED",
    )


def test_audit_store_round_trip_and_reconciliation(tmp_path) -> None:
    with AuditStore(tmp_path / "audit.sqlite") as store:
        store.write(_event())
        assert store.get("audit-1") == _event()
        assert store.events_for_approval("approval-1") == [_event()]
        assert store.mark_reconciled("audit-1")
        event = store.get("audit-1")
        assert event is not None and event.reconciled
        assert store.count() == 1
        assert store.count("approval-1") == 1


def test_audit_store_injects_one_write_failure_without_persisting(tmp_path) -> None:
    with AuditStore(tmp_path / "audit.sqlite") as store:
        store.fail_next_write = True
        with pytest.raises(OSError, match="injected audit-store write failure"):
            store.write(_event())
        assert store.count() == 0
        store.write(_event())
        assert store.count("approval-1") == 1