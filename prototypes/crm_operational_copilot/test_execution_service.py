from __future__ import annotations

from approvals_store import Approval, ApprovalsStore
from audit_store import AuditStore
from authority_policy import AggregationConstraint, Grant, PolicyRule
from crm_store import CRMStore
from execution_service import CRMExecutionService
from identity_provider import Identity, LocalIdentityProvider
from policy_snapshot import policy_hash

ACTION = "write:accounts"
REQUESTER_SCOPE = "write:accounts"
REVIEWER_SCOPE = "approve:crm-writes"
REQUESTER = "requester"
REVIEWER = "reviewer"


def _ready_system(tmp_path, *, expires_at: int = 200):
    tmp_path.mkdir(parents=True, exist_ok=True)
    at = 150
    constraints = [
        AggregationConstraint(
            frozenset({"write:accounts", "export"}), "restricted pair"
        )
    ]
    rules = [PolicyRule(ACTION, "allow", 10)]
    requester_grant = Grant(REQUESTER, ACTION, 0, 300)
    reviewer_grant = Grant(REVIEWER, ACTION, 0, 300)
    grant_map = {
        (REQUESTER, ACTION): requester_grant,
        (REVIEWER, ACTION): reviewer_grant,
    }
    digest = policy_hash(
        action=ACTION,
        requester_grant=requester_grant,
        reviewer_grant=reviewer_grant,
        rules=rules,
        aggregation_constraints=constraints,
    )
    provider = LocalIdentityProvider(
        [
            Identity(REQUESTER, "tenant-a", frozenset({REQUESTER_SCOPE})),
            Identity(REVIEWER, "tenant-a", frozenset({REVIEWER_SCOPE})),
        ],
        clock=lambda: at,
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
            policy_hash=digest,
            created_at=100,
            expires_at=expires_at,
            approved_at=120,
            state="APPROVED",
        )
    )
    service = CRMExecutionService(
        identities=provider,
        approvals=approvals,
        crm=crm,
        audit=audit,
        rules=rules,
        grants=grant_map,
        aggregation_constraints=constraints,
        clock=lambda: at,
        execution_id_factory=lambda: "execution-1",
        audit_id_factory=lambda: "audit-1",
    )
    return service, approvals, crm, audit, provider, rules, grant_map, constraints


def _execute(service):
    return service.execute(
        "approval-1",
        requester_id=REQUESTER,
        reviewer_id=REVIEWER,
        action=ACTION,
        requester_scope=REQUESTER_SCOPE,
        reviewer_scope=REVIEWER_SCOPE,
    )


def test_successful_execution_binds_approval_crm_ledger_and_audit(tmp_path) -> None:
    service, approvals, crm, audit, *_ = _ready_system(tmp_path)
    result = _execute(service)

    assert result.status == "completed"
    assert result.reason == "executed"
    approval = approvals.get("approval-1")
    record = crm.get_record("CUST-1")
    assert approval is not None and approval.state == "COMPLETED"
    assert record is not None and record.record_version == 2
    assert len(crm.ledger_rows()) == 1
    events = audit.events_for_approval("approval-1")
    assert len(events) == 1
    assert events[0].execution_id == approval.execution_id
    assert events[0].crm_record_version == record.record_version


def test_missing_and_pending_approval_do_not_change_any_state(tmp_path) -> None:
    service, approvals, crm, audit, *_ = _ready_system(tmp_path)
    missing = service.execute(
        "missing", requester_id=REQUESTER, reviewer_id=REVIEWER, action=ACTION,
        requester_scope=REQUESTER_SCOPE, reviewer_scope=REVIEWER_SCOPE,
    )
    assert missing.status == "missing"
    assert approvals.get("approval-1").state == "APPROVED"
    assert crm.get_record("CUST-1").record_version == 1
    assert audit.count() == 0

    approvals.set_state("approval-1", "PENDING")
    pending = _execute(service)
    assert pending.status == "pending"
    assert approvals.get("approval-1").state == "PENDING"
    assert crm.get_record("CUST-1").record_version == 1
    assert audit.count() == 0


def test_execution_checks_live_scope_and_denial_audit_failure_does_not_change_result(
    tmp_path,
) -> None:
    service, approvals, crm, audit, provider, *_ = _ready_system(tmp_path)
    provider.put(Identity(REQUESTER, "tenant-a", frozenset()))
    audit.fail_next_write = True

    result = _execute(service)

    assert result.status == "invalidated"
    assert result.reason == "scope"
    assert result.audit_error == (
        "audit_store_failure:injected audit-store write failure"
    )
    approval = approvals.get("approval-1")
    assert approval is not None and approval.state == "INVALIDATED"
    assert approval.reason == "scope"
    assert crm.get_record("CUST-1").record_version == 1
    assert audit.count() == 0


def test_execution_invalidates_expired_stale_and_policy_changed_approvals(
    tmp_path,
) -> None:
    service, approvals, crm, _audit, *_ = _ready_system(
        tmp_path / "expired", expires_at=149
    )
    assert _execute(service).reason == "expired"
    assert approvals.get("approval-1").reason == "expired"

    service, approvals, crm, _audit, *_ = _ready_system(tmp_path / "stale")
    crm.seed("CUST-1", "other", "x", 100)
    crm.execute_write(
        execution_id="external", approval_id="external-approval", customer_id="CUST-1",
        field_name="account_owner", proposed_value="S. Lee", expected_version=1,
        at=140, approval_state="COMPLETED",
    )
    assert _execute(service).reason == "stale"
    assert approvals.get("approval-1").reason == "stale"

    service, approvals, *_rest = _ready_system(tmp_path / "policy")
    service.rules[:] = [PolicyRule(ACTION, "deny", 10)]
    assert _execute(service).reason == "policy_changed"
    assert approvals.get("approval-1").reason == "policy_changed"


def test_audit_failure_after_crm_write_returns_unresolved_not_success(tmp_path) -> None:
    service, approvals, crm, audit, *_ = _ready_system(tmp_path)
    audit.fail_next_write = True

    result = _execute(service)

    assert result.status == "unresolved"
    assert result.reason == "audit_pending"
    assert approvals.get("approval-1").state == "AUDIT_PENDING"
    assert crm.get_record("CUST-1").record_version == 2
    assert len(crm.ledger_rows()) == 1
    assert audit.count() == 0