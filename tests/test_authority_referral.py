from authority_policy import (
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

GRANT = Grant("agent-1", "read:account", 10, 100)


def test_refer_policy_returns_explicit_human_review_decision():
    decision = evaluate_authority(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[
            PolicyRule("read:account", "allow", 10),
            PolicyRule("read:account", "refer", 20),
        ],
    )

    assert decision == Decision("refer", "priority 20 policy refers for review")


def test_deny_wins_equal_priority_conflict_with_refer():
    decision = evaluate_authority(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[
            PolicyRule("read:account", "refer", 20),
            PolicyRule("read:account", "deny", 20),
        ],
    )

    assert decision.effect == "deny"


def test_refer_wins_equal_priority_conflict_with_allow():
    decision = evaluate_authority(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[
            PolicyRule("read:account", "allow", 20),
            PolicyRule("read:account", "refer", 20),
        ],
    )

    assert decision.effect == "refer"


def test_aggregate_propagates_refer_without_authorizing_action_set():
    decision = evaluate_aggregate_authority(
        grants_by_action={"read:account": GRANT},
        principal="agent-1",
        actions={"read:account"},
        at=50,
        rules=[PolicyRule("read:account", "refer", 10)],
        aggregation_constraints=[],
    )

    assert decision.effect == "refer"


def test_ticket_is_not_issued_when_policy_requires_review():
    result = issue_ticket(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "refer", 10)],
        ttl=20,
    )

    assert result == Decision("refer", "priority 10 policy refers for review")
    assert not isinstance(result, Ticket)


def test_ticket_use_propagates_new_review_requirement():
    ticket = issue_ticket(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=30,
        rules=[PolicyRule("read:account", "allow", 10)],
        ttl=40,
    )
    assert isinstance(ticket, Ticket)

    decision = use_ticket(
        ticket=ticket,
        current_grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "refer", 10)],
    )

    assert decision.effect == "refer"


def test_session_policy_propagates_review_requirement():
    decision = evaluate_in_session(
        grant=GRANT,
        principal="agent-1",
        action="read:account",
        at=50,
        rules=[PolicyRule("read:account", "refer", 10)],
        prior_actions=frozenset(),
        aggregation_constraints=[],
    )

    assert decision.effect == "refer"
    assert decision.reason == "priority 10 policy refers for review"
