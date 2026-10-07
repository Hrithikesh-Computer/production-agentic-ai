from __future__ import annotations

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


def _service(tmp_path):
    rules = [PolicyRule(ACTION, "allow", 10)]
    constraints = [
        AggregationConstraint(frozenset({ACTION, "export"}), "restricted pair")
    ]
    grants = {
        (REQUESTER, ACTION): Grant(REQUESTER, ACTION, 0, 300),
        (REVIEWER, ACTION): Grant(REVIEWER, ACTION, 0, 300),
    }
    digest = policy_hash(
        action=ACTION,
        requester_grant=grants[(REQUESTER, ACTION)],
        reviewer_grant=grants[(REVIEWER, ACTION)],
        rules=rules,
        aggregation_constraints=constraints,
    )
    identities = LocalIdentityProvider(
        [
            Identity(REQUESTER, "tenant-a", frozenset({REQUESTER_SCOPE})),
            Identity(REVIEWER, "tenant-a", frozenset({REVIEWER_SCOPE})),
        ],
        clock=lambda: 150,
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
            expires_at=200,
            approved_at=120,
            state="APPROVED",
        )
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
        execution_id_factory=lambda: "execution-1",
        audit_id_factory=lambda: "audit-1",
    )
    return service, approvals, crm, audit


def _execute(service):
    return service.execute(
        "approval-1",
        requester_id=REQUESTER,
        reviewer_id=REVIEWER,
        action=ACTION,
        requester_scope=REQUESTER_SCOPE,
        reviewer_scope=REVIEWER_SCOPE,
    )


def test_crm_write_failure_after_claim_recovers_without_mutation(tmp_path) -> None:
    service, approvals, crm, audit = _service(tmp_path)
    try:
        crm.connection.executescript(
            """CREATE TRIGGER fail_ledger_insert
BEFORE INSERT ON execution_ledger
BEGIN
    SELECT RAISE(ABORT, 'injected CRM write failure');
END;"""
        )

        result = _execute(service)

        assert result.status == "unresolved"
        assert result.reason.startswith("crm_store_failure:")
        approval = approvals.get("approval-1")
        record = crm.get_record("CUST-1")
        assert approval is not None and approval.state == "EXECUTING"
        assert record is not None and record.record_version == 1
        assert crm.ledger_rows() == []
        assert audit.count() == 0

        crm.connection.execute("DROP TRIGGER fail_ledger_insert")
        crm.connection.commit()
        recovered = service.recover()

        approval = approvals.get("approval-1")
        assert recovered[0].reason == "recovered_without_crm_write"
        assert approval is not None and approval.state == "APPROVED"
        assert approval.execution_id is None
        assert crm.get_record("CUST-1").record_version == 1
        assert crm.ledger_rows() == []
        assert audit.count() == 0
    finally:
        approvals.close()
        crm.close()
        audit.close()


def test_allowed_policy_change_still_invalidates_approval(tmp_path) -> None:
    service, approvals, crm, audit = _service(tmp_path)
    try:
        service.rules[:] = [PolicyRule(ACTION, "allow", 11)]

        result = _execute(service)

        assert result.status == "invalidated"
        assert result.reason == "policy_changed"
        approval = approvals.get("approval-1")
        record = crm.get_record("CUST-1")
        assert approval is not None and approval.state == "INVALIDATED"
        assert approval.reason == "policy_changed"
        assert record is not None and record.record_version == 1
        assert crm.ledger_rows() == []
        assert audit.count() == 1
    finally:
        approvals.close()
        crm.close()
        audit.close()