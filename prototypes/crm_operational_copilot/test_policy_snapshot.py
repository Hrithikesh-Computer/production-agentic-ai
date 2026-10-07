from __future__ import annotations

from typing import Any

from authority_policy import AggregationConstraint, Grant, PolicyRule
from policy_snapshot import policy_hash, policy_snapshot_payload

ACTION = "write:accounts"


def _snapshot_inputs() -> dict[str, Any]:
    return {
        "action": ACTION,
        "requester_grant": Grant("requester", ACTION, 10, 200),
        "reviewer_grant": Grant("reviewer", ACTION, 20, 200),
        "rules": [PolicyRule(ACTION, "allow", 10)],
        "aggregation_constraints": [
            AggregationConstraint(frozenset({ACTION, "export"}), "restricted pair")
        ],
    }


def test_policy_snapshot_hash_is_order_independent_and_deterministic() -> None:
    inputs = _snapshot_inputs()
    assert policy_hash(**inputs) == policy_hash(**inputs)
    reversed_inputs = inputs | {
        "rules": list(reversed(inputs["rules"])),
        "aggregation_constraints": list(reversed(inputs["aggregation_constraints"])),
    }
    assert policy_hash(**inputs) == policy_hash(**reversed_inputs)


def test_policy_snapshot_hash_includes_relevant_policy_grant_and_constraint_fields(
) -> None:
    inputs = _snapshot_inputs()
    original = policy_hash(**inputs)
    changed = inputs | {
        "rules": [PolicyRule(ACTION, "refer", 10)],
    }
    assert policy_hash(**changed) != original
    changed = inputs | {
        "requester_grant": Grant("requester", ACTION, 10, 201),
    }
    assert policy_hash(**changed) != original
    changed = inputs | {
        "aggregation_constraints": [
            AggregationConstraint(frozenset({ACTION, "export"}), "changed reason")
        ],
    }
    assert policy_hash(**changed) != original


def test_policy_snapshot_excludes_unrelated_grants_and_has_exact_shape() -> None:
    inputs = _snapshot_inputs()
    payload = policy_snapshot_payload(**inputs)
    inputs["requester_grant"] = Grant("requester", "read:accounts", 0, 999)
    inputs["reviewer_grant"] = Grant("reviewer", ACTION, 20, 200)
    unrelated_hash = policy_hash(**inputs)

    baseline_inputs = _snapshot_inputs()
    baseline_inputs["requester_grant"] = None
    assert unrelated_hash == policy_hash(**baseline_inputs)
    assert set(payload) == {"rules", "grants", "aggregation_constraints"}
    assert set(payload["grants"][0]) == {
        "principal",
        "action",
        "not_before",
        "expires_at",
        "revoked_at",
    }