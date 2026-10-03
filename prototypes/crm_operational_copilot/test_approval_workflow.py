import pytest
from approval_workflow import (
    APPROVE_SCOPE,
    WRITE_SCOPE,
    ApprovalWorkflow,
    StaleRecordError,
)

BASE_SCOPES = {
    "alice": {"read:accounts", WRITE_SCOPE},
    "reviewer": {APPROVE_SCOPE},
    "reader": {"read:accounts"},
}


def _workflow():
    audit_events = []
    workflow = ApprovalWorkflow(
        scopes_by_principal=BASE_SCOPES,
        audit_sink=audit_events.append,
        proposal_ttl_seconds=30,
        clock=lambda: 100,
    )
    return workflow, audit_events


def _proposal(workflow):
    return workflow.submit_update(
        requester="alice",
        customer_id="CUST-1001",
        field="account_owner",
        proposed_value="M. Chen",
        at=100,
    )


def _account_owner(workflow):
    return workflow.crm.read_account("alice", "CUST-1001")["account_owner"]


def test_proposal_requires_distinct_human_approval_and_audits_execution():
    workflow, audit_events = _workflow()
    proposal = _proposal(workflow)

    assert workflow.status(proposal.proposal_id) == "pending"
    assert _account_owner(workflow) == "A. Singh"

    assert workflow.review(
        proposal.proposal_id, reviewer="reviewer", approve=True, at=101
    ) == "approved"
    updated = workflow.execute(proposal.proposal_id, actor="alice", at=102)

    assert updated["account_owner"] == "M. Chen"
    assert workflow.status(proposal.proposal_id) == "executed"
    assert [event["event"] for event in audit_events] == [
        "proposal_created",
        "human_review_required",
        "proposal_approved",
        "human_review_satisfied",
        "execution_started",
        "execution_succeeded",
    ]
    assert [event["timestamp"] for event in audit_events] == [
        100,
        100,
        101,
        102,
        102,
        102,
    ]
    assert "refers for review" in audit_events[1]["reason"]
    assert audit_events[3]["reviewer"] == "reviewer"
    assert "proposed_value" not in audit_events[0]


def test_write_is_not_executed_before_approval():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)

    with pytest.raises(PermissionError, match="not approved"):
        workflow.execute(proposal.proposal_id, actor="alice", at=101)

    assert _account_owner(workflow) == "A. Singh"


def test_requester_cannot_approve_own_proposal():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)

    with pytest.raises(PermissionError, match="own proposal"):
        workflow.review(proposal.proposal_id, reviewer="alice", approve=True, at=101)

    assert workflow.status(proposal.proposal_id) == "pending"


def test_connector_rejects_write_without_matching_approval_record():
    workflow, _ = _workflow()

    with pytest.raises(PermissionError, match="human approval"):
        workflow.crm.update_account(
            actor="alice",
            customer_id="CUST-1001",
            field="account_owner",
            value="M. Chen",
            expected_version=1,
            at=101,
            approval_record=None,
        )

    assert _account_owner(workflow) == "A. Singh"


def test_proposal_requires_current_write_authority():
    workflow, _ = _workflow()

    with pytest.raises(PermissionError, match="no grant"):
        workflow.submit_update(
            requester="reader",
            customer_id="CUST-1001",
            field="account_owner",
            proposed_value="M. Chen",
            at=100,
        )


def test_write_scope_revocation_after_approval_blocks_execution():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    workflow.review(proposal.proposal_id, reviewer="reviewer", approve=True, at=101)
    workflow.authority.set_scopes("alice", {"read:accounts"})

    with pytest.raises(PermissionError, match="no grant"):
        workflow.execute(proposal.proposal_id, actor="alice", at=102)

    assert _account_owner(workflow) == "A. Singh"


def test_reviewer_scope_revocation_after_approval_blocks_execution():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    workflow.review(proposal.proposal_id, reviewer="reviewer", approve=True, at=101)
    workflow.authority.set_scopes("reviewer", set())

    with pytest.raises(PermissionError, match="reviewer approval authority"):
        workflow.execute(proposal.proposal_id, actor="alice", at=102)

    assert _account_owner(workflow) == "A. Singh"


def test_changed_record_invalidates_approval():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    workflow.review(proposal.proposal_id, reviewer="reviewer", approve=True, at=101)
    workflow.crm.simulate_external_update("CUST-1001", "health", "At risk")

    with pytest.raises(StaleRecordError, match="review again"):
        workflow.execute(proposal.proposal_id, actor="alice", at=102)

    assert workflow.status(proposal.proposal_id) == "stale"
    assert _account_owner(workflow) == "A. Singh"


def test_expired_approval_and_replay_are_denied():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    workflow.review(proposal.proposal_id, reviewer="reviewer", approve=True, at=101)

    with pytest.raises(PermissionError, match="expired"):
        workflow.execute(proposal.proposal_id, actor="alice", at=130)
    assert workflow.status(proposal.proposal_id) == "expired"

    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    workflow.review(proposal.proposal_id, reviewer="reviewer", approve=True, at=101)
    workflow.execute(proposal.proposal_id, actor="alice", at=102)
    with pytest.raises(PermissionError, match="executed"):
        workflow.execute(proposal.proposal_id, actor="alice", at=103)


def test_rejected_proposal_cannot_execute():
    workflow, _ = _workflow()
    proposal = _proposal(workflow)
    assert workflow.review(
        proposal.proposal_id, reviewer="reviewer", approve=False, at=101
    ) == "rejected"

    with pytest.raises(PermissionError, match="rejected"):
        workflow.execute(proposal.proposal_id, actor="alice", at=102)
