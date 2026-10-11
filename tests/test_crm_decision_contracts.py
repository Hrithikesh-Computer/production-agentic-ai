from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest
from identity_provider import Identity, LocalIdentityProvider
from test_crm_validation_scenarios import REVIEWER, REVIEWER_SCOPE, _execute, _system
from variants.race import run_n50_claim_race


@pytest.mark.xfail(
    strict=True,
    reason=(
        "I1: failed audit persistence leaves a committed CRM mutation without "
        "a bounded monitored reconciliation contract."
    ),
)
def test_i1_audit_failure_is_atomic_or_has_bounded_monitored_reconciliation(
    tmp_path: Path,
) -> None:
    service, _, crm, audit, *_ = _system(tmp_path)
    audit.fail_next_write = True

    result = _execute(service)
    recovery_window = getattr(service, "recovery_window_seconds", None)
    recovery_monitor = getattr(service, "recovery_monitor", None)

    assert not crm.ledger_rows() or audit.count() == 1 or (
        result.status == "unresolved"
        and recovery_window is not None
        and recovery_monitor is not None
    )


def test_i1_normal_mutation_has_correlated_durable_audit(tmp_path: Path) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path)

    result = _execute(service)

    events = audit.for_execution(result.execution_id)
    assert result.status == "completed"
    assert len(crm.ledger_rows()) == 1
    assert len(events) == 1
    assert events[0].approval_id == approvals.get("approval-1").approval_id


@pytest.mark.parametrize(
    ("principal", "tenant_a", "tenant_b"),
    [
        ("alice", "tenant-a", "tenant-b"),
        ("worker:17", "org:blue", "org:green"),
        ("svc_crm", "north", "south"),
    ],
    ids=("simple-name", "delimited-name", "service-name"),
)
@pytest.mark.xfail(
    strict=True,
    reason=(
        "I2: LocalIdentityProvider resolves by principal only; the "
        "tenant-qualified lookup contract is absent."
    ),
)
def test_i2_identity_resolution_is_principal_and_tenant_qualified(
    principal: str, tenant_a: str, tenant_b: str
) -> None:
    identity_a = Identity(principal, tenant_a, frozenset({"write:accounts"}))
    identity_b = Identity(principal, tenant_b, frozenset({"write:accounts"}))
    provider = LocalIdentityProvider([identity_a, identity_b])

    assert provider.resolve(principal) == identity_a


@pytest.mark.xfail(
    strict=True,
    reason=(
        "I2: generated principal/tenant pairs collide because storage has "
        "one slot per principal."
    ),
)
def test_i2_generated_principal_tenant_pairs_do_not_shadow_each_other() -> None:
    principals = ("alice", "svc:crm", "worker/17", "user@example.test")
    tenants = ("tenant-a", "tenant-b", "tenant-c")

    for principal, tenant_a, tenant_b in product(principals, tenants, tenants):
        if tenant_a == tenant_b:
            continue
        identity_a = Identity(principal, tenant_a, frozenset({"read"}))
        identity_b = Identity(principal, tenant_b, frozenset({"read"}))
        provider = LocalIdentityProvider([identity_a, identity_b])

        assert provider.resolve(principal) == identity_a


def test_i2_single_tenant_identity_authorizes_its_configured_scope() -> None:
    identity = Identity("alice", "tenant-a", frozenset({"write:accounts"}))
    provider = LocalIdentityProvider([identity])

    decision = provider.authorize("alice", "write:accounts")

    assert decision.allowed
    assert decision.identity == identity


@pytest.mark.xfail(
    strict=True,
    reason=(
        "I3: recover() is on-demand; no scheduled owner, recovery bound, or "
        "operational monitor is configured in this local service."
    ),
)
def test_i3_unresolved_execution_has_scheduled_owned_recovery_contract(
    tmp_path: Path,
) -> None:
    service, *_ = _system(tmp_path)

    assert getattr(service, "recovery_scheduler", None) is not None
    assert getattr(service, "recovery_owner", None) is not None
    assert getattr(service, "recovery_rto_seconds", None) is not None


def test_i3_manual_recovery_reconciles_audit_after_dependency_returns(
    tmp_path: Path,
) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path)
    audit.fail_next_write = True

    first = _execute(service)
    recovered = service.recover()

    assert first.status == "unresolved"
    assert recovered[0].status == "completed"
    assert approvals.get("approval-1").state == "COMPLETED"
    assert len(crm.ledger_rows()) == audit.count() == 1


def test_i4_completed_approval_replay_does_not_mutate_twice(
    tmp_path: Path,
) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path)

    first = _execute(service)
    replay = _execute(service)

    assert first.status == "completed"
    assert replay.status == "denied"
    assert approvals.get("approval-1").state == "COMPLETED"
    assert len(crm.ledger_rows()) == audit.count() == 1


def test_i4_broken_read_then_write_control_is_a_negative_race_witness(
    tmp_path: Path,
) -> None:
    outcome = run_n50_claim_race("broken-control", tmp_path / "broken.sqlite")

    assert outcome["workers"] == 50
    assert outcome["accepted_claims"] > 1
    assert not outcome["single_winner_assertion"]


def test_i5_current_approval_executes_against_its_bound_record_version(
    tmp_path: Path,
) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path)

    result = _execute(service)

    assert result.status == "completed"
    assert approvals.get("approval-1").record_version == 1
    assert crm.get_record("CUST-1", "account_owner").record_version == 2
    assert audit.for_execution(result.execution_id)[0].crm_record_version == 2


def test_i5_stale_record_is_rejected_without_a_second_mutation(
    tmp_path: Path,
) -> None:
    service, approvals, crm, *_ = _system(tmp_path)
    crm.execute_write(
        execution_id="external-update",
        approval_id="external-approval",
        customer_id="CUST-1",
        field_name="account_owner",
        proposed_value="S. Lee",
        expected_version=1,
        at=140,
        approval_state="COMPLETED",
    )

    result = _execute(service)

    assert result.status == "invalidated"
    assert result.reason == "stale"
    assert approvals.get("approval-1").state == "INVALIDATED"
    assert crm.get_record("CUST-1", "account_owner").record_version == 2
    assert len(crm.ledger_rows()) == 1


def test_i6_normal_approval_decision_is_audited(tmp_path: Path) -> None:
    service, approvals, _, audit, *_ = _system(tmp_path, state="PENDING")

    result = service.review(
        "approval-1",
        reviewer_id=REVIEWER,
        approve=True,
        reviewer_scope=REVIEWER_SCOPE,
    )

    events = audit.events_for_approval("approval-1")
    assert result.status == "completed"
    assert approvals.get("approval-1").state == "APPROVED"
    assert len(events) == 1
    assert events[0].event_type == "approval_approved"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "I6: review() persists APPROVED before its audit write; execution can "
        "proceed after the approval audit fails."
    ),
)
def test_i6_failed_approval_audit_prevents_execution_until_reconciled(
    tmp_path: Path,
) -> None:
    service, approvals, crm, audit, *_ = _system(tmp_path, state="PENDING")
    audit.fail_next_write = True

    review = service.review(
        "approval-1",
        reviewer_id=REVIEWER,
        approve=True,
        reviewer_scope=REVIEWER_SCOPE,
    )
    execution = _execute(service)

    assert review.status == "unresolved"
    assert approvals.get("approval-1").state == "PENDING"
    assert execution.status != "completed"
    assert crm.ledger_rows() == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "I6: rejection state persists although its audit event can fail and "
        "remain absent."
    ),
)
def test_i6_failed_rejection_audit_does_not_leave_unlogged_terminal_state(
    tmp_path: Path,
) -> None:
    service, approvals, _, audit, *_ = _system(tmp_path, state="PENDING")
    audit.fail_next_write = True

    result = service.review(
        "approval-1",
        reviewer_id=REVIEWER,
        approve=False,
        reviewer_scope=REVIEWER_SCOPE,
    )

    assert result.audit_error is not None
    assert approvals.get("approval-1").state == "PENDING"
    assert audit.events_for_approval("approval-1")