import json

import pytest
from crm_copilot import (
    AgentOrchestrator,
    AuthorizationError,
    MockCRMAdapter,
    RunLogger,
    ScopeError,
)


class UnsafeReasoner:
    def select_actions(self, _user_input):
        return ["update_account"]


def test_run_selects_read_actions_and_logs_complete_record(tmp_path):
    log_path = tmp_path / "runs.jsonl"
    orchestrator = AgentOrchestrator(
        MockCRMAdapter("test-token-123"),
        RunLogger(log_path),
    )

    result = orchestrator.run("CUST-1001")
    logged = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])

    assert result["status"] == "success"
    assert result["reasoning_mode"] == "deterministic_mock_action_selection"
    assert result["selected_actions"] == ["read_account", "read_opportunities"]
    assert [call["name"] for call in result["tool_calls"]] == [
        "read_account",
        "read_opportunities",
    ]
    assert all(call["duration_ms"] >= 0 for call in result["tool_calls"])
    assert result["total_duration_ms"] >= 0
    assert logged["timestamp"] == result["timestamp"]
    assert logged["input"] == "CUST-1001"
    assert logged["output"] == result["output"]


def test_invalid_input_is_logged_as_failed_run(tmp_path):
    log_path = tmp_path / "runs.jsonl"
    orchestrator = AgentOrchestrator(
        MockCRMAdapter("test-token-123"),
        RunLogger(log_path),
    )

    result = orchestrator.run("show me everything")
    logged = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])

    assert result["status"] == "failed"
    assert result["output"]["error_type"] == "ValueError"
    assert result["tool_calls"] == []
    assert logged["status"] == "failed"


def test_adapter_rejects_missing_or_short_credential():
    with pytest.raises(AuthorizationError):
        MockCRMAdapter("")
    with pytest.raises(AuthorizationError):
        MockCRMAdapter("short")


def test_adapter_enforces_read_scope():
    adapter = MockCRMAdapter("test-token-123", allowed_scopes=["read:accounts"])

    assert adapter.read_account("CUST-1001")["customer_id"] == "CUST-1001"
    with pytest.raises(ScopeError):
        adapter.read_opportunities("CUST-1001")


def test_empty_scope_list_does_not_restore_default_permissions():
    adapter = MockCRMAdapter("test-token-123", allowed_scopes=[])

    with pytest.raises(ScopeError):
        adapter.read_account("CUST-1001")


def test_orchestrator_rejects_unlisted_action_and_logs_failure(tmp_path):
    log_path = tmp_path / "runs.jsonl"
    orchestrator = AgentOrchestrator(
        MockCRMAdapter("test-token-123"),
        RunLogger(log_path),
        reasoner=UnsafeReasoner(),
    )

    result = orchestrator.run("CUST-1001")
    logged = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])

    assert result["status"] == "failed"
    assert result["output"]["error_type"] == "ScopeError"
    assert result["tool_calls"] == []
    assert logged["output"] == result["output"]
