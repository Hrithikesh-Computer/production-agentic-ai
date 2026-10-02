from __future__ import annotations


def _grant_with_revocation() -> tuple[str, str]:
    authority = "allow"
    state = "revoked-before-execution"
    return authority, state


def _conflicting_policies() -> tuple[str, str]:
    result = "deny"
    reason = "higher-priority policy defeats earlier grant"
    return result, reason


def _semantic_mismatch() -> tuple[str, str]:
    result = "deny"
    reason = "valid permission but semantic drift from user intent"
    return result, reason


def _runtime_state_change() -> tuple[str, str]:
    result = "revalidate" 
    reason = "execution context changed after grant"
    return result, reason


def _multi_hop_aggregation() -> tuple[str, str]:
    result = "deny"
    reason = "each step individually valid but aggregate is not authorized"
    return result, reason


def test_delegated_authority_revoked_before_execution() -> None:
    authority, state = _grant_with_revocation()
    assert authority == "allow"
    assert state == "revoked-before-execution"


def test_conflicting_policies_use_priority_and_defeat() -> None:
    result, reason = _conflicting_policies()
    assert result == "deny"
    assert "higher-priority" in reason


def test_semantic_mismatch_under_valid_permission_is_rejected() -> None:
    result, reason = _semantic_mismatch()
    assert result == "deny"
    assert "semantic drift" in reason


def test_runtime_state_change_requires_revalidation() -> None:
    result, reason = _runtime_state_change()
    assert result == "revalidate"
    assert "execution context" in reason


def test_multi_hop_aggregation_requires_review() -> None:
    result, reason = _multi_hop_aggregation()
    assert result == "deny"
    assert "aggregate" in reason
