from __future__ import annotations

import multiprocessing
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from approvals_store import Approval, ApprovalsStore
from audit_store import AuditStore
from authority_policy import AggregationConstraint, Grant, PolicyRule
from crm_store import CRMStore
from execution_service import CRMExecutionService
from identity_provider import Identity, LocalIdentityProvider
from policy_snapshot import policy_hash

ACTION = "write:accounts"
REQUESTER = "requester"
REVIEWER = "reviewer"
REQUESTER_SCOPE = "write:accounts"
REVIEWER_SCOPE = "approve:crm-writes"
SCENARIO_IDS = tuple(f"S{number:02d}" for number in range(1, 18))


def _system(
    tmp_path: Path,
    *,
    state: str = "APPROVED",
    expires_at: int = 200,
    execution_ids: tuple[str, ...] = ("execution-1", "execution-2"),
) -> tuple[Any, ...]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    now = 150
    rules = [PolicyRule(ACTION, "allow", 10)]
    constraints = [
        AggregationConstraint(frozenset({ACTION, "export"}), "restricted pair")
    ]
    requester_grant = Grant(REQUESTER, ACTION, 0, 300)
    reviewer_grant = Grant(REVIEWER, ACTION, 0, 300)
    grants = {
        (REQUESTER, ACTION): requester_grant,
        (REVIEWER, ACTION): reviewer_grant,
    }
    snapshot = policy_hash(
        action=ACTION,
        requester_grant=requester_grant,
        reviewer_grant=reviewer_grant,
        rules=rules,
        aggregation_constraints=constraints,
    )
    identities = LocalIdentityProvider(
        [
            Identity(REQUESTER, "tenant-a", frozenset({REQUESTER_SCOPE})),
            Identity(REVIEWER, "tenant-a", frozenset({REVIEWER_SCOPE})),
        ],
        clock=lambda: now,
    )
    approvals = ApprovalsStore(tmp_path / "approvals.sqlite")
    crm = CRMStore(tmp_path / "crm.sqlite")
    audit = AuditStore(tmp_path / "audit.sqlite")
    crm.seed("CUST-1", "account_owner", "A. Singh", 100)
    approvals.create(
        Approval(
            approval_id="approval-1",
            proposal_id="proposal-1",
            requester_id=REQUESTER,
            reviewer_id=REVIEWER,
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            previous_value="A. Singh",
            record_version=1,
            policy_hash=snapshot,
            created_at=100,
            expires_at=expires_at,
            approved_at=120 if state != "PENDING" else None,
            state=state,  # type: ignore[arg-type]
        )
    )
    ids = iter(execution_ids)
    service = CRMExecutionService(
        identities=identities,
        approvals=approvals,
        crm=crm,
        audit=audit,
        rules=rules,
        grants=grants,
        aggregation_constraints=constraints,
        clock=lambda: now,
        execution_id_factory=lambda: next(ids),
        audit_id_factory=lambda: f"audit-{audit.count() + 1}",
    )
    return service, approvals, crm, audit, identities, rules


def _execute(service: CRMExecutionService, approval_id: str = "approval-1"):
    return service.execute(
        approval_id,
        requester_id=REQUESTER,
        reviewer_id=REVIEWER,
        action=ACTION,
        requester_scope=REQUESTER_SCOPE,
        reviewer_scope=REVIEWER_SCOPE,
    )


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS, ids=SCENARIO_IDS)
def test_contract_scenario_ids_persist_expected_state(
    scenario_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = "PENDING" if scenario_id in {"S02", "S14", "S15"} else "APPROVED"
    expiry = 149 if scenario_id == "S06" else 200
    service, approvals, crm, audit, identities, rules = _system(
        tmp_path, state=state, expires_at=expiry
    )

    if scenario_id == "S01":
        result = _execute(service, "missing")
        assert result.status == "missing"
        assert approvals.get("approval-1").state == "APPROVED"
        assert crm.get_record("CUST-1").record_version == 1
        assert audit.count() == 0
    elif scenario_id == "S02":
        result = _execute(service)
        assert result.status == "pending"
        assert approvals.get("approval-1").state == "PENDING"
        assert crm.get_record("CUST-1").record_version == 1
        assert audit.count() == 0
    elif scenario_id == "S03":
        identities.put(Identity(REQUESTER, "tenant-a", frozenset()))
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "scope"
        assert approvals.get("approval-1").reason == "scope"
    elif scenario_id == "S04":
        identities.put(Identity(REQUESTER, "tenant-a", frozenset(), "revoked"))
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "revoked"
        assert approvals.get("approval-1").reason == "revoked"
    elif scenario_id == "S05":
        identities.put(Identity(REVIEWER, "tenant-a", frozenset(), "revoked"))
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "revoked"
        assert approvals.get("approval-1").reason == "revoked"
    elif scenario_id == "S06":
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "expired"
        assert approvals.get("approval-1").reason == "expired"
    elif scenario_id == "S07":
        assert crm.execute_write(
            execution_id="external-update",
            approval_id="external-approval",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="S. Lee",
            expected_version=1,
            at=140,
            approval_state="COMPLETED",
        ) is not None
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "stale"
        assert crm.get_record("CUST-1").record_version == 2
    elif scenario_id == "S08":
        rules[:] = [PolicyRule(ACTION, "deny", 10)]
        result = _execute(service)
        assert result.status == "invalidated" and result.reason == "policy_changed"
        assert crm.get_record("CUST-1").record_version == 1
    elif scenario_id == "S09":
        assert approvals.claim("approval-1", "race-winner", 150)
        assert not approvals.claim("approval-1", "race-loser", 150)
        assert crm.ledger_rows() == []
    elif scenario_id == "S10":
        assert approvals.claim("approval-1", "crash-before-write", 150)
        result = service.recover()[0]
        approval = approvals.get("approval-1")
        assert result.reason == "recovered_without_crm_write"
        assert approval.state == "APPROVED" and approval.execution_id is None
        assert crm.ledger_rows() == [] and audit.count() == 0
    elif scenario_id == "S11":
        original_set_state = approvals.set_state

        def fail_completed(approval_id, new_state, *, reason=None):
            if new_state == "COMPLETED":
                raise OSError("injected approvals-store outage")
            return original_set_state(approval_id, new_state, reason=reason)

        monkeypatch.setattr(approvals, "set_state", fail_completed)
        result = _execute(service)
        assert result.status == "unresolved"
        assert approvals.get("approval-1").state == "EXECUTING"
        assert len(crm.ledger_rows()) == 1 and audit.count() == 1
        monkeypatch.setattr(approvals, "set_state", original_set_state)
        assert service.recover()[0].status == "completed"
        assert approvals.get("approval-1").state == "COMPLETED"
    elif scenario_id == "S12":
        audit.fail_next_write = True
        result = _execute(service)
        assert result.status == "unresolved"
        assert approvals.get("approval-1").state == "AUDIT_PENDING"
        assert crm.get_record("CUST-1").record_version == 2
        assert service.recover()[0].status == "completed"
        assert audit.count() == 1
    elif scenario_id == "S13":
        assert approvals.claim("approval-1", "duplicate-execution", 150)
        assert crm.execute_write(
            execution_id="duplicate-execution",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=1,
            at=150,
            approval_state="EXECUTING",
        ) is not None
        result = _execute(service)
        assert result.status == "unresolved"
        assert crm.get_record("CUST-1").record_version == 2
        assert len(crm.ledger_rows()) == 1
    elif scenario_id == "S14":
        result = service.review(
            "approval-1", reviewer_id=REVIEWER, approve=False,
            reviewer_scope=REVIEWER_SCOPE,
        )
        assert result.status == "rejected"
        assert approvals.get("approval-1").state == "REJECTED"
        assert crm.get_record("CUST-1").record_version == 1
        assert audit.count() == 1
    elif scenario_id == "S15":
        audit.fail_next_write = True
        result = service.review(
            "approval-1", reviewer_id=REVIEWER, approve=False,
            reviewer_scope=REVIEWER_SCOPE,
        )
        assert result.status == "rejected"
        assert result.audit_error is not None
        assert approvals.get("approval-1").state == "REJECTED"
        assert crm.get_record("CUST-1").record_version == 1
        assert audit.count() == 0
    elif scenario_id == "S16":
        result = _execute(service)
        approval = approvals.get("approval-1")
        ledger = crm.ledger_rows()
        events = audit.events_for_approval("approval-1")
        assert result.status == "completed"
        assert approval.state == "COMPLETED"
        assert len(ledger) == 1 and len(events) == 1
        assert ledger[0]["execution_id"] == approval.execution_id
        assert events[0].execution_id == approval.execution_id
    elif scenario_id == "S17":
        assert _execute(service).status == "completed"
        result = _execute(service)
        assert result.status == "denied" and result.reason == "approval_completed"
        assert approvals.get("approval-1").state == "COMPLETED"
        assert crm.get_record("CUST-1").record_version == 2
        assert len(crm.ledger_rows()) == 1 and audit.count() == 1
    else:
        pytest.fail(f"scenario not implemented: {scenario_id}")


def _execution_worker(
    directory: str, start: Any, output: Any, worker_number: int
) -> None:
    path = Path(directory)
    approvals = ApprovalsStore(path / "approvals.sqlite")
    crm = CRMStore(path / "crm.sqlite")
    audit = AuditStore(path / "audit.sqlite")
    rules = [PolicyRule(ACTION, "allow", 10)]
    constraints = [
        AggregationConstraint(frozenset({ACTION, "export"}), "restricted pair")
    ]
    grants = {
        (REQUESTER, ACTION): Grant(REQUESTER, ACTION, 0, 300),
        (REVIEWER, ACTION): Grant(REVIEWER, ACTION, 0, 300),
    }
    identities = LocalIdentityProvider(
        [
            Identity(REQUESTER, "tenant-a", frozenset({REQUESTER_SCOPE})),
            Identity(REVIEWER, "tenant-a", frozenset({REVIEWER_SCOPE})),
        ],
        clock=lambda: 150,
    )
    service = CRMExecutionService(
        identities=identities,
        approvals=approvals,
        crm=crm,
        audit=audit,
        rules=rules,
        grants=grants,
        aggregation_constraints=constraints,
        clock=lambda: 150,
        execution_id_factory=lambda: f"worker-execution-{worker_number}",
        audit_id_factory=lambda: f"worker-audit-{worker_number}",
    )
    try:
        start.wait(timeout=60)
        result = service.execute(
            "approval-race",
            requester_id=REQUESTER,
            reviewer_id=REVIEWER,
            action=ACTION,
            requester_scope=REQUESTER_SCOPE,
            reviewer_scope=REVIEWER_SCOPE,
        )
        output.put(result.status)
    finally:
        approvals.close()
        crm.close()
        audit.close()


@pytest.mark.parametrize(
    "round_number", range(5), ids=lambda value: f"round-{value + 1}"
)
def test_s09_fifty_separate_processes_have_exactly_one_persisted_claim_winner(
    tmp_path: Path, round_number: int
) -> None:
    del round_number
    with (
        ApprovalsStore(tmp_path / "approvals.sqlite") as approvals,
        CRMStore(tmp_path / "crm.sqlite") as crm,
        AuditStore(tmp_path / "audit.sqlite") as audit,
    ):
        constraints = [
            AggregationConstraint(frozenset({ACTION, "export"}), "restricted pair")
        ]
        grants = {
            (REQUESTER, ACTION): Grant(REQUESTER, ACTION, 0, 300),
            (REVIEWER, ACTION): Grant(REVIEWER, ACTION, 0, 300),
        }
        snapshot = policy_hash(
            action=ACTION,
            requester_grant=grants[(REQUESTER, ACTION)],
            reviewer_grant=grants[(REVIEWER, ACTION)],
            rules=[PolicyRule(ACTION, "allow", 10)],
            aggregation_constraints=constraints,
        )
        approvals.create(
            Approval(
                approval_id="approval-race",
                proposal_id="proposal-race",
                requester_id=REQUESTER,
                reviewer_id=REVIEWER,
                customer_id="CUST-1",
                field_name="account_owner",
                proposed_value="M. Chen",
                previous_value="A. Singh",
                record_version=1,
                policy_hash=snapshot,
                created_at=100,
                expires_at=200,
                approved_at=120,
                state="APPROVED",
            )
        )
        crm.seed("CUST-1", "account_owner", "A. Singh", 100)
    context = multiprocessing.get_context("spawn")
    start = context.Barrier(50)
    output = context.Queue()
    processes = [
        context.Process(
            target=_execution_worker,
            args=(str(tmp_path), start, output, index),
        )
        for index in range(50)
    ]
    for process in processes:
        process.start()
    outcomes = [output.get(timeout=180) for _ in processes]
    for process in processes:
        process.join(timeout=180)
    assert all(process.exitcode == 0 for process in processes)
    assert outcomes.count("completed") == 1
    assert outcomes.count("unresolved") + outcomes.count("denied") == 49
    with (
        ApprovalsStore(tmp_path / "approvals.sqlite") as store,
        CRMStore(tmp_path / "crm.sqlite") as crm,
        AuditStore(tmp_path / "audit.sqlite") as audit,
    ):
        approval = store.get("approval-race")
        record = crm.get_record("CUST-1")
        assert approval is not None and approval.state == "COMPLETED"
        assert approval.execution_id is not None
        assert record is not None and record.record_version == 2
        assert len(crm.ledger_rows()) == 1
        assert len(audit.events_for_approval("approval-race")) == 1


def test_failure_injection_crm_transaction_rolls_back_record_and_ledger(
    tmp_path: Path,
) -> None:
    _service, _approvals, crm, _audit, *_ = _system(tmp_path)
    crm.connection.execute(
        """CREATE TRIGGER fail_ledger_insert
BEFORE INSERT ON execution_ledger
BEGIN
    SELECT RAISE(ABORT, 'injected CRM ledger failure');
END;"""
    )
    with pytest.raises(sqlite3.IntegrityError, match="injected CRM ledger failure"):
        crm.execute_write(
            execution_id="crash-atomicity",
            approval_id="approval-1",
            customer_id="CUST-1",
            field_name="account_owner",
            proposed_value="M. Chen",
            expected_version=1,
            at=150,
            approval_state="EXECUTING",
        )
    record = crm.get_record("CUST-1")
    assert record is not None and record.record_version == 1
    assert crm.ledger_rows() == []


def test_failure_injection_approvals_claim_failure_prevents_crm_write(
    tmp_path: Path,
) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path)
    approvals.connection.execute(
        """CREATE TRIGGER fail_approval_claim
BEFORE UPDATE OF state ON approvals
WHEN NEW.state = 'EXECUTING'
BEGIN
    SELECT RAISE(ABORT, 'injected approvals-store failure');
END;"""
    )

    result = _execute(service)

    assert result.status == "unresolved"
    assert result.reason.startswith("approvals_store_failure:")
    approval = approvals.get("approval-1")
    record = crm.get_record("CUST-1")
    assert approval is not None and approval.state == "APPROVED"
    assert record is not None and record.record_version == 1
    assert crm.ledger_rows() == []
    assert audit.count() == 0
