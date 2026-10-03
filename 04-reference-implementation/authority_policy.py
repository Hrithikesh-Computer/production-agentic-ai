from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Effect = Literal["allow", "deny", "refer"]


@dataclass(frozen=True)
class Grant:
    principal: str
    action: str
    not_before: int
    expires_at: int
    revoked_at: int | None = None


@dataclass(frozen=True)
class PolicyRule:
    action: str
    effect: Effect
    priority: int


@dataclass(frozen=True)
class Decision:
    effect: Effect
    reason: str


@dataclass(frozen=True)
class AggregationConstraint:
    actions: frozenset[str]
    reason: str


def evaluate_authority(
    *,
    grant: Grant | None,
    principal: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
) -> Decision:
    """Evaluate one time-bounded grant against action-scoped priority rules."""
    if grant is None:
        return Decision("deny", "no grant")
    if grant.principal != principal:
        return Decision("deny", "principal mismatch")
    if grant.action != action:
        return Decision("deny", "action mismatch")
    if at < grant.not_before:
        return Decision("deny", "grant not yet valid")
    if at >= grant.expires_at:
        return Decision("deny", "grant expired")
    if grant.revoked_at is not None and at >= grant.revoked_at:
        return Decision("deny", "grant revoked")

    applicable = [rule for rule in rules if rule.action == action]
    if not applicable:
        return Decision("deny", "no applicable policy")

    highest_priority = max(rule.priority for rule in applicable)
    winning_effects = {
        rule.effect for rule in applicable if rule.priority == highest_priority
    }
    if "deny" in winning_effects:
        return Decision("deny", f"priority {highest_priority} policy denies")
    if "refer" in winning_effects:
        return Decision(
            "refer", f"priority {highest_priority} policy refers for review"
        )
    return Decision("allow", f"priority {highest_priority} policy allows")


def evaluate_aggregate_authority(
    *,
    grants_by_action: dict[str, Grant],
    principal: str,
    actions: set[str],
    at: int,
    rules: list[PolicyRule],
    aggregation_constraints: list[AggregationConstraint],
) -> Decision:
    """Require each action decision and deny prohibited action combinations.

    A refer decision propagates to the caller unless a denial or aggregation
    constraint requires a stronger fail-closed result.
    """
    if not actions:
        return Decision("deny", "no actions requested")

    referral: Decision | None = None
    for action in sorted(actions):
        decision = evaluate_authority(
            grant=grants_by_action.get(action),
            principal=principal,
            action=action,
            at=at,
            rules=rules,
        )
        if decision.effect == "deny":
            return decision
        if decision.effect == "refer":
            referral = decision

    for constraint in aggregation_constraints:
        if constraint.actions.issubset(actions):
            return Decision("deny", constraint.reason)

    if referral is not None:
        return referral

    return Decision("allow", "all action grants and aggregation constraints allow")


@dataclass(frozen=True)
class Ticket:
    """A time-limited record that an action was allowed at issue time.

    A ticket is evidence of a past decision, not authority. It never grants
    anything by itself: use_ticket() re-evaluates against *current* grant state.
    """

    principal: str
    action: str
    issued_at: int
    expires_at: int


def issue_ticket(
    *,
    grant: Grant | None,
    principal: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
    ttl: int,
) -> Ticket | Decision:
    """Return a Ticket only for allow; return deny or refer decisions unchanged."""
    if ttl <= 0:
        raise ValueError("ttl must be positive")
    decision = evaluate_authority(
        grant=grant, principal=principal, action=action, at=at, rules=rules
    )
    if decision.effect != "allow":
        return decision
    return Ticket(principal, action, issued_at=at, expires_at=at + ttl)


def use_ticket(
    *,
    ticket: Ticket,
    current_grant: Grant | None,
    principal: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
) -> Decision:
    """Authorize execution: bind the ticket, then re-check current state."""
    if ticket.principal != principal or ticket.action != action:
        return Decision("deny", "ticket does not match request")
    if at < ticket.issued_at:
        return Decision("deny", "ticket used before issue time")

    current_decision = evaluate_authority(
        grant=current_grant, principal=principal, action=action, at=at, rules=rules
    )
    if current_decision.effect == "deny":
        return current_decision
    if at >= ticket.expires_at:
        return Decision("deny", "ticket expired")
    return current_decision


def evaluate_in_session(
    *,
    grant: Grant | None,
    principal: str,
    action: str,
    at: int,
    rules: list[PolicyRule],
    prior_actions: frozenset[str],
    aggregation_constraints: list[AggregationConstraint],
) -> Decision:
    """Evaluate one step given the actions already performed in this session.

    Each step can be individually allowed while the accumulated set is not.
    A step is denied when it completes a prohibited combination. A refer
    decision remains a referral and must not be treated as execution authority.
    """
    decision = evaluate_authority(
        grant=grant, principal=principal, action=action, at=at, rules=rules
    )
    if decision.effect == "deny":
        return decision
    combined = prior_actions | {action}
    for constraint in aggregation_constraints:
        if action in constraint.actions and constraint.actions <= combined:
            return Decision("deny", constraint.reason)
    return decision
