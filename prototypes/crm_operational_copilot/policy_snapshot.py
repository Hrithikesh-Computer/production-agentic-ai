"""Canonical policy snapshot hashing for the local CRM validation workflow."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REFERENCE_IMPLEMENTATION = (
    Path(__file__).resolve().parents[2] / "04-reference-implementation"
)
if str(REFERENCE_IMPLEMENTATION) not in sys.path:
    sys.path.insert(0, str(REFERENCE_IMPLEMENTATION))

from authority_policy import (  # noqa: E402
    AggregationConstraint,
    Grant,
    PolicyRule,
    evaluate_aggregate_authority,
    evaluate_authority,
)


def policy_snapshot_payload(
    *,
    action: str,
    requester_grant: Grant | None,
    reviewer_grant: Grant | None,
    rules: list[PolicyRule],
    aggregation_constraints: list[AggregationConstraint],
) -> dict[str, Any]:
    relevant_grants = [
        grant
        for grant in (requester_grant, reviewer_grant)
        if grant is not None and grant.action == action
    ]
    return {
        "rules": sorted(
            (
                {
                    "action": rule.action,
                    "effect": rule.effect,
                    "priority": rule.priority,
                }
                for rule in rules
            ),
            key=lambda item: (item["action"], item["priority"], item["effect"]),
        ),
        "grants": sorted(
            (
                {
                    "principal": grant.principal,
                    "action": grant.action,
                    "not_before": grant.not_before,
                    "expires_at": grant.expires_at,
                    "revoked_at": grant.revoked_at,
                }
                for grant in relevant_grants
            ),
            key=lambda item: (item["principal"], item["action"]),
        ),
        "aggregation_constraints": sorted(
            (
                {"actions": sorted(constraint.actions), "reason": constraint.reason}
                for constraint in aggregation_constraints
            ),
            key=lambda item: (item["actions"], item["reason"]),
        ),
    }


def policy_hash(
    *,
    action: str,
    requester_grant: Grant | None,
    reviewer_grant: Grant | None,
    rules: list[PolicyRule],
    aggregation_constraints: list[AggregationConstraint],
) -> str:
    payload = policy_snapshot_payload(
        action=action,
        requester_grant=requester_grant,
        reviewer_grant=reviewer_grant,
        rules=rules,
        aggregation_constraints=aggregation_constraints,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_requester(
    *,
    grant: Grant | None,
    principal: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
) -> Any:
    return evaluate_authority(
        grant=grant, principal=principal, action=action, at=at, rules=rules
    )


def evaluate_requester_and_reviewer(
    *,
    requester_grant: Grant | None,
    requester: str,
    reviewer_grant: Grant | None,
    reviewer: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
    aggregation_constraints: list[AggregationConstraint],
):
    requester_result = evaluate_authority(
        grant=requester_grant,
        principal=requester,
        action=action,
        at=at,
        rules=rules,
    )
    if requester_result.effect != "allow":
        return requester_result
    return evaluate_aggregate_authority(
        grants_by_action={action: reviewer_grant} if reviewer_grant else {},
        principal=reviewer,
        actions={action},
        at=at,
        rules=rules,
        aggregation_constraints=aggregation_constraints,
    )