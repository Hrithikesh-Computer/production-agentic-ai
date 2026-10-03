#!/usr/bin/env python3
"""Local mock of an approval-gated CRM update workflow.

This is a deterministic prototype. It uses in-memory CRM data and the local
reference authority evaluator; it does not call a model, IdP, queue, or live CRM.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_IMPLEMENTATION = REPOSITORY_ROOT / "04-reference-implementation"
PROTOTYPE_DIRECTORY = Path(__file__).resolve().parent
for import_path in (REFERENCE_IMPLEMENTATION, PROTOTYPE_DIRECTORY):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from authority_policy import (  # noqa: E402
    Decision,
    Grant,
    PolicyRule,
    evaluate_authority,
)
from crm_copilot import DEFAULT_CUSTOMERS, RunLogger  # noqa: E402

WRITE_SCOPE = "write:accounts"
APPROVE_SCOPE = "approve:crm-writes"
ALLOWED_UPDATE_FIELDS = frozenset({"account_owner", "health"})
ProposalStatus = Literal[
    "pending", "approved", "rejected", "expired", "executed", "denied", "stale"
]
AuditSink = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class AccountUpdateProposal:
    proposal_id: str
    requester: str
    customer_id: str
    field: str
    proposed_value: str
    previous_value: str
    expected_record_version: int
    created_at: int
    expires_at: int


@dataclass
class _ApprovalRecord:
    proposal: AccountUpdateProposal
    status: ProposalStatus = "pending"
    reviewer: str | None = None


class StaleRecordError(RuntimeError):
    """Raised when the CRM record changed after proposal review."""


class MockAuthorityGateway:
    """Apply current principal scopes through the bounded authority evaluator."""

    def __init__(self, scopes_by_principal: dict[str, set[str]]):
        self.scopes_by_principal = {
            principal: set(scopes) for principal, scopes in scopes_by_principal.items()
        }

    def set_scopes(self, principal: str, scopes: set[str]) -> None:
        """Replace a principal's current scopes to model policy changes/revocation."""
        self.scopes_by_principal[principal] = set(scopes)

    def decide(self, principal: str, action: str, at: int) -> Decision:
        has_scope = action in self.scopes_by_principal.get(principal, set())
        grant = (
            Grant(principal, action, not_before=0, expires_at=at + 1)
            if has_scope
            else None
        )
        return evaluate_authority(
            grant=grant,
            principal=principal,
            action=action,
            at=at,
            rules=[
                PolicyRule(
                    action,
                    "refer" if action == WRITE_SCOPE else "allow",
                    10,
                )
            ],
        )


class MockCRMConnector:
    """Isolated mutable copy of mock CRM records with version-checked writes."""

    def __init__(self, authority: MockAuthorityGateway):
        self.authority = authority
        self._accounts = deepcopy(DEFAULT_CUSTOMERS)
        self._versions = {customer_id: 1 for customer_id in self._accounts}

    def read_account(self, actor: str, customer_id: str) -> dict[str, Any]:
        decision = self.authority.decide(actor, "read:accounts", at=0)
        if decision.effect != "allow":
            raise PermissionError(decision.reason)
        account = self._accounts.get(customer_id)
        if account is None:
            raise KeyError(f"Customer {customer_id} not found in mock CRM dataset.")
        return deepcopy(account)

    def update_account(
        self,
        *,
        actor: str,
        customer_id: str,
        field: str,
        value: str,
        expected_version: int,
        at: int,
        approval_record: _ApprovalRecord | None,
    ) -> dict[str, Any]:
        if (
            approval_record is None
            or approval_record.status != "approved"
            or approval_record.reviewer is None
            or approval_record.reviewer == actor
        ):
            raise PermissionError("a distinct human approval is required")
        proposal = approval_record.proposal
        if (
            proposal.requester != actor
            or proposal.customer_id != customer_id
            or proposal.field != field
            or proposal.proposed_value != value
            or proposal.expected_record_version != expected_version
        ):
            raise PermissionError("approval does not match the requested CRM update")

        decision = self.authority.decide(actor, WRITE_SCOPE, at)
        if decision.effect == "deny":
            raise PermissionError(decision.reason)
        reviewer_decision = self.authority.decide(
            approval_record.reviewer, APPROVE_SCOPE, at
        )
        if reviewer_decision.effect != "allow":
            raise PermissionError("reviewer approval authority is no longer valid")
        if field not in ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field '{field}' cannot be updated by this prototype.")
        account = self._accounts.get(customer_id)
        if account is None:
            raise KeyError(f"Customer {customer_id} not found in mock CRM dataset.")
        if self._versions[customer_id] != expected_version:
            raise StaleRecordError("CRM record changed after the proposal was created.")
        account[field] = value
        self._versions[customer_id] += 1
        return deepcopy(account)

    def record_version(self, customer_id: str) -> int:
        if customer_id not in self._versions:
            raise KeyError(f"Customer {customer_id} not found in mock CRM dataset.")
        return self._versions[customer_id]

    def simulate_external_update(
        self, customer_id: str, field: str, value: str
    ) -> None:
        """Simulate an out-of-band CRM update for stale-record tests and demos."""
        if field not in ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field '{field}' cannot be updated by this prototype.")
        account = self._accounts.get(customer_id)
        if account is None:
            raise KeyError(f"Customer {customer_id} not found in mock CRM dataset.")
        account[field] = value
        self._versions[customer_id] += 1


class ApprovalWorkflow:
    """Coordinate proposal, separate approval, recheck, mock write, and audit."""

    def __init__(
        self,
        *,
        scopes_by_principal: dict[str, set[str]],
        audit_sink: AuditSink,
        proposal_ttl_seconds: int = 600,
        clock: Callable[[], int] = lambda: int(time.time()),
    ):
        if proposal_ttl_seconds <= 0:
            raise ValueError("proposal_ttl_seconds must be positive")
        self.authority = MockAuthorityGateway(scopes_by_principal)
        self.crm = MockCRMConnector(self.authority)
        self.audit_sink = audit_sink
        self.proposal_ttl_seconds = proposal_ttl_seconds
        self.clock = clock
        self._records: dict[str, _ApprovalRecord] = {}

    def _now(self, at: int | None) -> int:
        current = self.clock() if at is None else at
        if current < 0:
            raise ValueError("time must be nonnegative")
        return current

    def _audit(
        self,
        event: str,
        *,
        actor: str,
        proposal: AccountUpdateProposal | None = None,
        reason: str | None = None,
        at: int | None = None,
        reviewer: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "event": event,
            "actor": actor,
            "timestamp": self._now(at),
        }
        if proposal is not None:
            record.update(
                {
                    "proposal_id": proposal.proposal_id,
                    "requester": proposal.requester,
                    "customer_id": proposal.customer_id,
                    "action": WRITE_SCOPE,
                    "field": proposal.field,
                    "record_version": proposal.expected_record_version,
                }
            )
        if reason is not None:
            record["reason"] = reason
        if reviewer is not None:
            record["reviewer"] = reviewer
        self.audit_sink(record)

    def _require_decision(
        self,
        principal: str,
        action: str,
        at: int,
        *,
        allow_referral: bool = False,
        approval_record: _ApprovalRecord | None = None,
    ) -> Decision:
        decision = self.authority.decide(principal, action, at)
        if decision.effect == "deny":
            self._audit(
                "authorization_denied",
                actor=principal,
                reason=decision.reason,
                at=at,
            )
            raise PermissionError(decision.reason)
        if decision.effect == "refer":
            if allow_referral:
                return decision
            proposal = approval_record.proposal if approval_record is not None else None
            if (
                approval_record is None
                or approval_record.status != "approved"
                or approval_record.reviewer is None
                or approval_record.reviewer == principal
            ):
                self._audit(
                    "human_review_required",
                    actor=principal,
                    proposal=proposal,
                    reason=decision.reason,
                    at=at,
                )
                raise PermissionError("human review required")

            reviewer_decision = self.authority.decide(
                approval_record.reviewer, APPROVE_SCOPE, at
            )
            if reviewer_decision.effect != "allow":
                self._audit(
                    "authorization_denied",
                    actor=principal,
                    proposal=approval_record.proposal,
                    reason="reviewer approval authority is no longer valid",
                    at=at,
                )
                raise PermissionError("reviewer approval authority is no longer valid")
            self._audit(
                "human_review_satisfied",
                actor=principal,
                proposal=approval_record.proposal,
                reason=decision.reason,
                at=at,
                reviewer=approval_record.reviewer,
            )
            return Decision("allow", "human review satisfied")
        return decision

    def submit_update(
        self,
        *,
        requester: str,
        customer_id: str,
        field: str,
        proposed_value: str,
        at: int | None = None,
    ) -> AccountUpdateProposal:
        current = self._now(at)
        if field not in ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field '{field}' cannot be updated by this prototype.")
        if not isinstance(proposed_value, str) or not proposed_value.strip():
            raise ValueError("proposed_value must be a non-empty string")
        if len(proposed_value) > 128:
            raise ValueError("proposed_value exceeds 128 characters")

        decision = self._require_decision(
            requester, WRITE_SCOPE, current, allow_referral=True
        )
        account = self.crm.read_account(requester, customer_id)
        previous_value = account.get(field)
        if not isinstance(previous_value, str):
            raise ValueError("The selected account field is not a string.")
        if previous_value == proposed_value:
            raise ValueError("The proposed value matches the current value.")

        proposal = AccountUpdateProposal(
            proposal_id=uuid.uuid4().hex,
            requester=requester,
            customer_id=customer_id,
            field=field,
            proposed_value=proposed_value,
            previous_value=previous_value,
            expected_record_version=self.crm.record_version(customer_id),
            created_at=current,
            expires_at=current + self.proposal_ttl_seconds,
        )
        self._audit("proposal_created", actor=requester, proposal=proposal, at=current)
        self._records[proposal.proposal_id] = _ApprovalRecord(proposal=proposal)
        if decision.effect == "refer":
            self._audit(
                "human_review_required",
                actor=requester,
                proposal=proposal,
                reason=decision.reason,
                at=current,
            )
        return proposal

    def review(
        self,
        proposal_id: str,
        *,
        reviewer: str,
        approve: bool,
        at: int | None = None,
    ) -> ProposalStatus:
        current = self._now(at)
        record = self._get_record(proposal_id)
        proposal = record.proposal
        if record.status != "pending":
            raise ValueError(f"proposal is {record.status}, not pending")
        if current >= proposal.expires_at:
            record.status = "expired"
            self._audit(
                "proposal_expired", actor=reviewer, proposal=proposal, at=current
            )
            raise PermissionError("proposal expired")
        if reviewer == proposal.requester:
            self._audit(
                "approval_denied",
                actor=reviewer,
                proposal=proposal,
                reason="requester cannot approve their own proposal",
                at=current,
            )
            raise PermissionError("requester cannot approve their own proposal")
        self._require_decision(reviewer, APPROVE_SCOPE, current)

        record.reviewer = reviewer
        record.status = "approved" if approve else "rejected"
        self._audit(
            "proposal_approved" if approve else "proposal_rejected",
            actor=reviewer,
            proposal=proposal,
            at=current,
        )
        return record.status

    def execute(
        self, proposal_id: str, *, actor: str, at: int | None = None
    ) -> dict[str, Any]:
        current = self._now(at)
        record = self._get_record(proposal_id)
        proposal = record.proposal
        if actor != proposal.requester:
            self._audit(
                "execution_denied",
                actor=actor,
                proposal=proposal,
                reason="execution actor does not match requester",
                at=current,
            )
            raise PermissionError("execution actor does not match requester")
        if record.status != "approved":
            self._audit(
                "execution_denied",
                actor=actor,
                proposal=proposal,
                reason=f"proposal is {record.status}, not approved",
                at=current,
            )
            raise PermissionError(f"proposal is {record.status}, not approved")
        if current >= proposal.expires_at:
            record.status = "expired"
            self._audit(
                "proposal_expired", actor=actor, proposal=proposal, at=current
            )
            raise PermissionError("proposal expired")
        self._require_decision(
            actor, WRITE_SCOPE, current, approval_record=record
        )

        if (
            self.crm.record_version(proposal.customer_id)
            != proposal.expected_record_version
        ):
            record.status = "stale"
            self._audit(
                "execution_denied",
                actor=actor,
                proposal=proposal,
                reason="CRM record changed after approval",
                at=current,
            )
            raise StaleRecordError("CRM record changed after approval; review again.")

        self._audit("execution_started", actor=actor, proposal=proposal, at=current)
        try:
            updated = self.crm.update_account(
                actor=actor,
                customer_id=proposal.customer_id,
                field=proposal.field,
                value=proposal.proposed_value,
                expected_version=proposal.expected_record_version,
                at=current,
                approval_record=record,
            )
        except StaleRecordError as error:
            record.status = "stale"
            self._audit(
                "execution_denied",
                actor=actor,
                proposal=proposal,
                reason=str(error),
                at=current,
            )
            raise
        except PermissionError as error:
            record.status = "denied"
            self._audit(
                "execution_denied",
                actor=actor,
                proposal=proposal,
                reason=str(error),
                at=current,
            )
            raise

        record.status = "executed"
        self._audit("execution_succeeded", actor=actor, proposal=proposal, at=current)
        return updated

    def status(self, proposal_id: str) -> ProposalStatus:
        return self._get_record(proposal_id).status

    def _get_record(self, proposal_id: str) -> _ApprovalRecord:
        try:
            return self._records[proposal_id]
        except KeyError as error:
            raise KeyError(f"Unknown proposal: {proposal_id}") from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local, approval-gated CRM workflow demonstration."
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path(tempfile.gettempdir()) / "crm-approval-workflow.jsonl",
        help="JSONL audit path (default: system temporary directory)",
    )
    args = parser.parse_args()

    logger = RunLogger(args.log_path)
    workflow = ApprovalWorkflow(
        scopes_by_principal={
            "account-user": {"read:accounts", WRITE_SCOPE},
            "compliance-reviewer": {APPROVE_SCOPE},
        },
        audit_sink=logger.log,
    )
    proposal = workflow.submit_update(
        requester="account-user",
        customer_id="CUST-1001",
        field="account_owner",
        proposed_value="M. Chen",
    )
    workflow.review(proposal.proposal_id, reviewer="compliance-reviewer", approve=True)
    updated = workflow.execute(proposal.proposal_id, actor="account-user")
    print(
        json.dumps(
            {
                "proposal_id": proposal.proposal_id,
                "status": workflow.status(proposal.proposal_id),
                "updated_account": updated,
                "audit_path": str(args.log_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
