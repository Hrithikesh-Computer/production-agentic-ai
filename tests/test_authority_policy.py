from __future__ import annotations

from dataclasses import replace

import pytest
from authority_policy import (
    AggregationConstraint,
    Decision,
    Grant,
    PolicyRule,
    Ticket,
    evaluate_aggregate_authority,
    evaluate_authority,
    evaluate_in_session,
    issue_ticket,
    use_ticket,
)


def _grant(*, expires_at: int = 100, revoked_at: int | None = None) -> Grant:
    return Grant(
        principal="agent-1",
        action="read:account",
        not_before=10,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


def test_active_grant_and_allow_policy_allow_matching_action() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "allow"


def test_missing_grant_is_denied() -> None:
    decision = evaluate_authority(
        grant=None,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "deny"
    assert decision.reason == "no grant"


def test_grant_is_denied_before_not_before_boundary() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=9,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "deny"
    assert decision.reason == "grant not yet valid"


def test_grant_is_valid_at_not_before_boundary() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=10,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "allow"


def test_revocation_effective_at_execution_time_denies_grant() -> None:
    decision = evaluate_authority(
        grant=_grant(revoked_at=40),
        principal="agent-1",
        action="read:account",
        at=40,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "deny"
    assert decision.reason == "grant revoked"


def test_revocation_after_execution_time_does_not_retroactively_deny() -> None:
    decision = evaluate_authority(
        grant=_grant(revoked_at=60),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "allow"


def test_higher_priority_deny_overrides_lower_priority_allow() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[
            PolicyRule("read:account", "allow", 10),
            PolicyRule("read:account", "deny", 20),
        ],
    )

    assert decision.effect == "deny"
    assert decision.reason == "priority 20 policy denies"


def test_equal_priority_conflict_fails_closed() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[
            PolicyRule("read:account", "allow", 10),
            PolicyRule("read:account", "deny", 10),
        ],
    )

    assert decision.effect == "deny"


def test_expired_grant_is_denied_at_expiration_boundary() -> None:
    decision = evaluate_authority(
        grant=_grant(expires_at=50),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "allow", 10)],
    )

    assert decision.effect == "deny"
    assert decision.reason == "grant expired"


def test_missing_matching_policy_fails_closed() -> None:
    decision = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("write:account", "allow", 10)],
    )

    assert decision.effect == "deny"
    assert decision.reason == "no applicable policy"


def test_mismatched_principal_and_action_are_denied() -> None:
    wrong_principal = evaluate_authority(
        grant=_grant(),
        principal="agent-2",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "allow", 10)],
    )
    wrong_action = evaluate_authority(
        grant=_grant(),
        principal="agent-1",
        action="write:account",
        at=50,
        rules=[PolicyRule("write:account", "allow", 10)],
    )

    assert wrong_principal.reason == "principal mismatch"
    assert wrong_action.reason == "action mismatch"


def test_multi_read_aggregation_constraint_denies_combined_actions() -> None:
    actions = {"read:account", "read:notes"}
    grants = {action: Grant("agent-1", action, 10, 100) for action in actions}
    rules = [PolicyRule(action, "allow", 10) for action in actions]
    constraint = AggregationConstraint(
        actions=frozenset(actions),
        reason="account and notes cannot be aggregated",
    )

    each_read_allowed = [
        evaluate_authority(
            grant=grants[action],
            principal="agent-1",
            action=action,
            at=50,
            rules=rules,
        )
        for action in actions
    ]
    aggregate = evaluate_aggregate_authority(
        grants_by_action=grants,
        principal="agent-1",
        actions=actions,
        at=50,
        rules=rules,
        aggregation_constraints=[constraint],
    )

    assert all(decision.effect == "allow" for decision in each_read_allowed)
    assert aggregate.effect == "deny"
    assert aggregate.reason == constraint.reason


ALLOW_READ = [PolicyRule("read:account", "allow", 10)]


def _ticket(ttl: int = 20) -> Ticket:
    result = issue_ticket(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=30,
        rules=ALLOW_READ,
        ttl=ttl,
    )
    assert isinstance(result, Ticket)
    return result


def test_ticket_is_issued_for_allowed_action() -> None:
    result = _ticket()
    assert isinstance(result, Ticket)
    assert result.principal == "agent-1"
    assert result.action == "read:account"
    assert result.expires_at == 50


def test_no_ticket_is_issued_for_denied_action() -> None:
    result = issue_ticket(
        grant=None,
        principal="agent-1",
        action="read:account",
        at=30,
        rules=ALLOW_READ,
        ttl=20,
    )
    assert isinstance(result, Decision)
    assert result.effect == "deny"


def test_revocation_arriving_after_check_denies_use() -> None:
    ticket = issue_ticket(
        grant=_grant(revoked_at=60),
        principal="agent-1",
        action="read:account",
        at=30,
        rules=ALLOW_READ,
        ttl=20,
    )
    assert isinstance(ticket, Ticket)
    decision = use_ticket(
        ticket=ticket,
        current_grant=replace(_grant(revoked_at=60), revoked_at=45),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=ALLOW_READ,
    )
    assert decision.effect == "deny"
    assert decision.reason == "grant revoked"


def test_ticket_does_not_survive_when_grant_record_is_gone() -> None:
    ticket = _ticket()
    decision = use_ticket(
        ticket=ticket,
        current_grant=None,
        principal="agent-1",
        action="read:account",
        at=40,
        rules=ALLOW_READ,
    )
    assert decision.effect == "deny"
    assert decision.reason == "no grant"


def test_ticket_does_not_override_a_policy_added_after_check() -> None:
    ticket = issue_ticket(
        grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=30,
        rules=[PolicyRule("read:account", "allow", 10)],
        ttl=20,
    )
    assert isinstance(ticket, Ticket)
    decision = use_ticket(
        ticket=ticket,
        current_grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=40,
        rules=[PolicyRule("read:account", "deny", 20)],
    )
    assert decision.effect == "deny"
    assert decision.reason == "priority 20 policy denies"


def test_unchanged_state_allows_use_within_ticket_lifetime() -> None:
    ticket = _ticket(ttl=25)
    decision = use_ticket(
        ticket=ticket,
        current_grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=40,
        rules=ALLOW_READ,
    )
    assert decision.effect == "allow"


def test_expired_ticket_is_denied_at_boundary() -> None:
    ticket = _ticket(ttl=20)
    decision = use_ticket(
        ticket=ticket,
        current_grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=50,
        rules=ALLOW_READ,
    )
    assert decision.effect == "deny"
    assert decision.reason == "ticket expired"


def test_ticket_is_bound_to_principal_and_action() -> None:
    ticket = Ticket("agent-1", "read:account", issued_at=30, expires_at=100)
    wrong = use_ticket(
        ticket=ticket,
        current_grant=Grant("agent-2", "read:account", 10, 100),
        principal="agent-2",
        action="read:account",
        at=40,
        rules=ALLOW_READ,
    )
    mismatched = use_ticket(
        ticket=ticket,
        current_grant=Grant("agent-1", "write:account", 10, 100),
        principal="agent-1",
        action="write:account",
        at=40,
        rules=[PolicyRule("write:account", "allow", 10)],
    )
    assert wrong.effect == "deny"
    assert wrong.reason == "ticket does not match request"
    assert mismatched.effect == "deny"
    assert mismatched.reason == "ticket does not match request"


def test_ticket_cannot_be_used_before_issue_time() -> None:
    ticket = Ticket(
        principal="agent-1",
        action="read:account",
        issued_at=30,
        expires_at=50,
    )
    decision = use_ticket(
        ticket=ticket,
        current_grant=_grant(),
        principal="agent-1",
        action="read:account",
        at=29,
        rules=ALLOW_READ,
    )
    assert decision.effect == "deny"
    assert decision.reason == "ticket used before issue time"


def _two_read_setup() -> tuple[dict[str, Grant], list[PolicyRule]]:
    grants = {
        "read:account": Grant("agent-1", "read:account", 10, 100),
        "read:notes": Grant("agent-1", "read:notes", 10, 100),
    }
    rules = [
        PolicyRule("read:account", "allow", 10),
        PolicyRule("read:notes", "allow", 10),
    ]
    return grants, rules


def test_aggregate_requires_every_individual_grant() -> None:
    grants, rules = _two_read_setup()
    grants.pop("read:notes")
    decision = evaluate_aggregate_authority(
        grants_by_action=grants,
        principal="agent-1",
        actions={"read:account", "read:notes"},
        at=50,
        rules=rules,
        aggregation_constraints=[
            AggregationConstraint(
                frozenset({"read:account", "read:notes"}),
                "deny",
            )
        ],
    )
    assert decision.effect == "deny"


def test_aggregate_rejects_missing_action_even_without_constraint() -> None:
    grants, rules = _two_read_setup()
    grants.pop("read:notes")
    decision = evaluate_aggregate_authority(
        grants_by_action=grants,
        principal="agent-1",
        actions={"read:account", "read:notes"},
        at=50,
        rules=rules,
        aggregation_constraints=[],
    )
    assert decision.effect == "deny"
    assert decision.reason == "no grant"


def test_aggregate_empty_request_is_denied() -> None:
    decision = evaluate_aggregate_authority(
        grants_by_action={},
        principal="agent-1",
        actions=set(),
        at=50,
        rules=[],
        aggregation_constraints=[],
    )
    assert decision.effect == "deny"


def test_aggregate_constraint_requires_whole_set_not_any_member() -> None:
    grants, rules = _two_read_setup()
    decision = evaluate_aggregate_authority(
        grants_by_action=grants,
        principal="agent-1",
        actions={"read:account"},
        at=50,
        rules=rules,
        aggregation_constraints=[
            AggregationConstraint(
                frozenset({"read:account", "read:notes"}),
                "deny",
            )
        ],
    )
    assert decision.effect == "allow"


PAIR = AggregationConstraint(
    frozenset({"read:account", "read:notes"}), "account and notes cannot be combined"
)


def _step(action: str, at: int, prior: frozenset[str]) -> Decision:
    decision = evaluate_in_session(
        grant=Grant("agent-1", action, 10, 100),
        principal="agent-1",
        action=action,
        at=at,
        rules=[
            PolicyRule("read:account", "allow", 10),
            PolicyRule("read:notes", "allow", 10),
        ],
        prior_actions=prior,
        aggregation_constraints=[PAIR],
    )
    return decision


def test_session_steps_are_individually_allowed_but_combination_is_denied() -> None:
    first = _step("read:account", 50, frozenset())
    second = _step("read:notes", 90, frozenset({"read:account"}))
    assert first.effect == "allow"
    assert second.effect == "deny"
    assert second.reason == "account and notes cannot be combined"


def test_session_unrelated_history_does_not_trigger_constraint() -> None:
    decision = _step("read:notes", 90, frozenset({"read:other"}))
    assert decision.effect == "allow"


def test_session_individual_denial_takes_precedence() -> None:
    decision = evaluate_in_session(
        grant=None,
        principal="agent-1",
        action="read:notes",
        at=90,
        rules=[PolicyRule("read:notes", "allow", 10)],
        prior_actions=frozenset({"read:account"}),
        aggregation_constraints=[PAIR],
    )
    assert decision.effect == "deny"
    assert decision.reason == "no grant"


def test_ticket_ttl_must_be_positive() -> None:
    with pytest.raises(ValueError):
        issue_ticket(
            grant=_grant(),
            principal="agent-1",
            action="read:account",
            at=30,
            rules=ALLOW_READ,
            ttl=0,
        )
