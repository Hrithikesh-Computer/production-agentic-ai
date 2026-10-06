"""Ordered, fail-closed execution path for the deterministic CRM contract."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from approvals_store import Approval, ApprovalsStore
from audit_store import AuditEvent, AuditStore
from authority_policy import (
    AggregationConstraint,
    Grant,
    PolicyRule,
    evaluate_aggregate_authority,
)
from crm_store import CRMStore, LedgerResult
from identity_provider import LocalIdentityProvider
from policy_snapshot import evaluate_requester, policy_hash

ExecutionStatus = Literal[
    "completed",
    "denied",
    "missing",
    "pending",
    "unresolved",
    "invalidated",
]


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    reason: str
    approval_id: str
    execution_id: str | None = None
    ledger: LedgerResult | None = None
    audit_error: str | None = None


class CRMExecutionService:
    """Execute reviewed CRM updates against the three independent stores."""

    def __init__(
        self,
        *,
        identities: LocalIdentityProvider,
        approvals: ApprovalsStore,
        crm: CRMStore,
        audit: AuditStore,
        rules: list[PolicyRule],
        grants: dict[tuple[str, str], Grant],
        aggregation_constraints: list[AggregationConstraint],
        clock,
        execution_id_factory=uuid.uuid4,
        audit_id_factory=uuid.uuid4,
    ) -> None:
        self.identities = identities
        self.approvals = approvals
        self.crm = crm
        self.audit = audit
        self.rules = rules
        self.grants = grants
        self.aggregation_constraints = aggregation_constraints
        self.clock = clock
        self.execution_id_factory = execution_id_factory
        self.audit_id_factory = audit_id_factory

    def execute(
        self,
        approval_id: str,
        *,
        requester_id: str,
        reviewer_id: str,
        action: str,
        requester_scope: str,
        reviewer_scope: str,
    ) -> ExecutionResult:
        at = self.clock()

        requester_identity = self.identities.authorize(
            requester_id, requester_scope, at=at
        )
        reviewer_identity = self.identities.authorize(
            reviewer_id, reviewer_scope, at=at
        )

        approval = self.approvals.get(approval_id)
        if approval is None:
            return self._result("missing", "approval_missing", approval_id)
        if approval.requester_id != requester_id or approval.reviewer_id != reviewer_id:
            return self._result("denied", "identity_mismatch", approval_id)
        if not requester_identity.allowed or not reviewer_identity.allowed:
            reason = (
                "revoked"
                if "revoked" in {requester_identity.reason, reviewer_identity.reason}
                else "scope"
            )
            return self._invalidate(approval, reason, at)
        if approval.state != "APPROVED":
            return self._result(
                "pending", f"approval_{approval.state.lower()}", approval_id
            )
        if approval.expires_at <= at:
            return self._invalidate(approval, "expired", at)

        crm_record = self.crm.get_record(approval.customer_id, approval.field_name)
        if crm_record is None or crm_record.record_version != approval.record_version:
            return self._invalidate(approval, "stale", at)

        requester_grant = self.grants.get((requester_id, action))
        reviewer_grant = self.grants.get((reviewer_id, action))
        current_hash = policy_hash(
            action=action,
            requester_grant=requester_grant,
            reviewer_grant=reviewer_grant,
            rules=self.rules,
            aggregation_constraints=self.aggregation_constraints,
        )
        if current_hash != approval.policy_hash:
            return self._invalidate(approval, "policy_changed", at)
        requester_decision = evaluate_requester(
            grant=requester_grant,
            principal=requester_id,
            action=action,
            at=at,
            rules=self.rules,
        )
        reviewer_decision = evaluate_requester(
            grant=reviewer_grant,
            principal=reviewer_id,
            action=action,
            at=at,
            rules=self.rules,
        )
        if requester_decision.effect != "allow" or reviewer_decision.effect != "allow":
            return self._invalidate(approval, "policy_changed", at)
        aggregate_decision = evaluate_aggregate_authority(
            grants_by_action={action: requester_grant}
            if requester_grant is not None
            else {},
            principal=requester_id,
            actions={action},
            at=at,
            rules=self.rules,
            aggregation_constraints=self.aggregation_constraints,
        )
        if aggregate_decision.effect != "allow":
            return self._invalidate(approval, "policy_changed", at)

        execution_id = self._new_id(self.execution_id_factory)
        try:
            if not self.approvals.claim(approval_id, execution_id, at):
                current = self.approvals.get(approval_id)
                if current is not None and current.execution_id == execution_id:
                    return self._result(
                        "unresolved", "claim_state_unknown", approval_id, execution_id
                    )
                return self._result("denied", "approval_claim_lost", approval_id)
        except Exception as error:
            return self._result(
                "unresolved",
                f"approvals_store_failure:{error}",
                approval_id,
                execution_id,
            )

        try:
            ledger = self.crm.execute_write(
                execution_id=execution_id,
                approval_id=approval_id,
                customer_id=approval.customer_id,
                field_name=approval.field_name,
                proposed_value=approval.proposed_value,
                expected_version=approval.record_version,
                at=at,
                approval_state="EXECUTING",
            )
        except Exception as error:
            return self._result(
                "unresolved", f"crm_store_failure:{error}", approval_id, execution_id
            )
        if ledger is None:
            self._invalidate(approval, "stale", at)
            return self._result("invalidated", "stale", approval_id, execution_id)

        try:
            self.audit.write(
                self._audit_event(
                    approval,
                    execution_id,
                    at,
                    event_type="execution_succeeded",
                    state_before="EXECUTING",
                    state_after="COMPLETED",
                    crm_record_version=ledger.record_version,
                )
            )
        except Exception as error:
            try:
                self.approvals.set_state(approval_id, "AUDIT_PENDING")
            except Exception:
                pass
            return self._result(
                "unresolved",
                "audit_pending",
                approval_id,
                execution_id,
                ledger=ledger,
                audit_error=str(error),
            )
        try:
            self.approvals.set_state(approval_id, "COMPLETED")
        except Exception as error:
            return self._result(
                "unresolved",
                "approvals_store_failure_after_crm_write",
                approval_id,
                execution_id,
                ledger=ledger,
                audit_error=str(error),
            )
        return self._result(
            "completed", "executed", approval_id, execution_id, ledger=ledger
        )

    def _invalidate(
        self, approval: Approval, reason: str, at: int
    ) -> ExecutionResult:
        audit_error = None
        try:
            self.approvals.set_state(approval.approval_id, "INVALIDATED", reason=reason)  # type: ignore[arg-type]
        except Exception as error:
            audit_error = f"approvals_store_failure:{error}"
        try:
            self.audit.write(
                self._audit_event(
                    approval,
                    None,
                    at,
                    event_type="execution_denied",
                    state_before=approval.state,
                    state_after="INVALIDATED",
                    reason=reason,
                    crm_record_version=approval.record_version,
                )
            )
        except Exception as error:
            audit_error = f"audit_store_failure:{error}"
        return self._result(
            "invalidated",
            reason,
            approval.approval_id,
            audit_error=audit_error,
        )

    def _audit_event(
        self,
        approval: Approval,
        execution_id: str | None,
        at: int,
        *,
        event_type: str,
        state_before: str,
        state_after: str,
        crm_record_version: int | None,
        reason: str | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            audit_id=self._new_id(self.audit_id_factory),
            approval_id=approval.approval_id,
            execution_id=execution_id,
            event_type=event_type,
            event_ts=at,
            crm_customer_id=approval.customer_id,
            crm_record_version=crm_record_version,
            state_before=state_before,
            state_after=state_after,
            reason=reason,
        )

    @staticmethod
    def _new_id(factory) -> str:
        value = factory()
        return value.hex if hasattr(value, "hex") else str(value)

    @staticmethod
    def _result(
        status: ExecutionStatus,
        reason: str,
        approval_id: str,
        execution_id: str | None = None,
        *,
        ledger: LedgerResult | None = None,
        audit_error: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=status,
            reason=reason,
            approval_id=approval_id,
            execution_id=execution_id,
            ledger=ledger,
            audit_error=audit_error,
        )