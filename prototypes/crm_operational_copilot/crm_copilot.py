#!/usr/bin/env python3
"""Minimal, read-only CRM operational copilot prototype.

This is intentionally narrow: it logs each run, enforces explicit auth and scope
checks, and restricts the tool adapter to read-only CRM access. It does not
implement writes, updates, or live CRM integration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_ALLOWED_SCOPES = ["read:accounts", "read:opportunities"]
DEFAULT_CUSTOMERS = {
    "CUST-1001": {
        "customer_id": "CUST-1001",
        "name": "Northwind Manufacturing",
        "account_owner": "A. Singh",
        "industry": "Manufacturing",
        "region": "North America",
        "health": "Healthy",
        "last_activity": "2026-09-18",
    },
    "CUST-1002": {
        "customer_id": "CUST-1002",
        "name": "Summit Retail Group",
        "account_owner": "J. Patel",
        "industry": "Retail",
        "region": "EMEA",
        "health": "At risk",
        "last_activity": "2026-09-02",
    },
    "CUST-1003": {
        "customer_id": "CUST-1003",
        "name": "Harbor Health Systems",
        "account_owner": "L. Costa",
        "industry": "Healthcare",
        "region": "APAC",
        "health": "Healthy",
        "last_activity": "2026-09-15",
    },
}

DEFAULT_OPPORTUNITIES = {
    "CUST-1001": [
        {
            "id": "OPP-9001",
            "stage": "Proposal",
            "amount": 180000,
            "close_date": "2026-10-15",
        },
        {
            "id": "OPP-9002",
            "stage": "Negotiation",
            "amount": 240000,
            "close_date": "2026-11-05",
        },
    ],
    "CUST-1002": [
        {
            "id": "OPP-9101",
            "stage": "At risk",
            "amount": 90000,
            "close_date": "2026-10-03",
        },
        {
            "id": "OPP-9102",
            "stage": "Discovery",
            "amount": 65000,
            "close_date": "2026-11-12",
        },
    ],
    "CUST-1003": [
        {
            "id": "OPP-9201",
            "stage": "Closed won",
            "amount": 320000,
            "close_date": "2026-09-27",
        },
    ],
}


class AuthorizationError(RuntimeError):
    pass


class ScopeError(RuntimeError):
    pass


class MockCRMAdapter:
    """Mock read-only adapter with credential-presence and scope checks."""

    def __init__(self, token: str, allowed_scopes: List[str] | None = None):
        self.token = token or ""
        self.allowed_scopes = set(
            DEFAULT_ALLOWED_SCOPES if allowed_scopes is None else allowed_scopes
        )
        self.require_auth()

    def require_auth(self) -> None:
        if not self.token or len(self.token) < 8:
            raise AuthorizationError(
                "CRM_API_TOKEN missing or invalid; "
                "this prototype rejects unauthenticated access."
            )

    def require_scope(self, scope: str) -> None:
        if scope not in self.allowed_scopes:
            raise ScopeError(f"Scope '{scope}' is not allowed for this adapter.")

    def read_account(self, customer_id: str) -> Dict[str, Any]:
        self.require_scope("read:accounts")
        account = DEFAULT_CUSTOMERS.get(customer_id)
        if account is None:
            raise KeyError(f"Customer {customer_id} not found in mock CRM dataset.")
        return account

    def read_opportunities(self, customer_id: str) -> List[Dict[str, Any]]:
        self.require_scope("read:opportunities")
        return DEFAULT_OPPORTUNITIES.get(customer_id, [])


class RunLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


class MockReasoningModel:
    """Deterministic stand-in for model action selection; makes no model call."""

    def select_actions(self, user_input: str) -> List[str]:
        if not re.fullmatch(r"\s*CUST-\d{4}\s*", user_input):
            raise ValueError("Input must be a customer ID matching CUST-####")
        return ["read_account", "read_opportunities"]


class AgentOrchestrator:
    def __init__(
        self,
        adapter: MockCRMAdapter,
        logger: RunLogger,
        reasoner: MockReasoningModel | None = None,
    ):
        self.adapter = adapter
        self.logger = logger
        self.reasoner = reasoner or MockReasoningModel()

    def _run_tool(self, tool_name: str, args: Dict[str, Any], fn) -> Any:
        started = time.perf_counter()
        try:
            result = fn(**args)
        except Exception as error:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            raise ToolExecutionError(tool_name, args, duration_ms, error) from error
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "name": tool_name,
            "args": args,
            "duration_ms": duration_ms,
            "result": result,
        }

    def _reason(
        self,
        account: Dict[str, Any],
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_value = sum(item.get("amount", 0) for item in opportunities)
        largest = max(
            opportunities,
            key=lambda item: item.get("amount", 0),
            default={"stage": "No-op", "amount": 0},
        )
        high_priority = any(
            item.get("stage", "").lower() in {"negotiation", "proposal"}
            for item in opportunities
        )
        recommendation = (
            "Routine account review"
            if not high_priority
            else "Prioritize expansion follow-up and customer executive outreach"
        )
        return {
            "customer_id": account["customer_id"],
            "account_name": account["name"],
            "health": account["health"],
            "opportunity_count": len(opportunities),
            "total_pipeline_value": total_value,
            "largest_opportunity": largest.get("id", "n/a"),
            "recommendation": recommendation,
        }

    def run(self, raw_input: str) -> Dict[str, Any]:
        started = time.perf_counter()
        tool_calls: List[Dict[str, Any]] = []
        actions: List[str] = []
        status = "success"
        try:
            customer_id = raw_input.strip()
            actions = self.reasoner.select_actions(raw_input)
            tool_map = {
                "read_account": self.adapter.read_account,
                "read_opportunities": self.adapter.read_opportunities,
            }
            tool_results: Dict[str, Any] = {}
            for action in actions:
                if action not in tool_map:
                    raise ScopeError(f"Action '{action}' is not permitted.")
                call = self._run_tool(
                    action,
                    {"customer_id": customer_id},
                    tool_map[action],
                )
                tool_calls.append(call)
                tool_results[action] = call["result"]

            output = self._reason(
                tool_results["read_account"],
                tool_results["read_opportunities"],
            )
        except ToolExecutionError as error:
            tool_calls.append(error.call_record())
            status = "failed"
            output = {
                "error": str(error.cause),
                "error_type": type(error.cause).__name__,
            }
        except Exception as error:
            status = "failed"
            output = {"error": str(error), "error_type": type(error).__name__}

        total_duration_ms = round((time.perf_counter() - started) * 1000, 3)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": raw_input,
            "status": status,
            "reasoning_mode": "deterministic_mock_action_selection",
            "selected_actions": actions,
            "tool_calls": tool_calls,
            "total_duration_ms": total_duration_ms,
            "output": output,
        }
        self.logger.log(payload)
        return payload


class ToolExecutionError(RuntimeError):
    def __init__(self, tool_name, args, duration_ms, cause):
        super().__init__(str(cause))
        self.tool_name = tool_name
        self.args = args
        self.duration_ms = duration_ms
        self.cause = cause

    def call_record(self) -> Dict[str, Any]:
        return {
            "name": self.tool_name,
            "args": self.args,
            "duration_ms": self.duration_ms,
            "error": str(self.cause),
            "error_type": type(self.cause).__name__,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal read-only CRM operational copilot prototype"
    )
    parser.add_argument(
        "--customer-id",
        required=True,
        help="Customer ID such as CUST-1001",
    )
    parser.add_argument(
        "--allowed-scopes",
        default=os.environ.get(
            "CRM_ALLOWED_SCOPES",
            "read:accounts,read:opportunities",
        ),
        help="Comma-separated allowed scopes",
    )
    parser.add_argument(
        "--log-path",
        default=str(Path(__file__).resolve().parent / "run_log.jsonl"),
        help="Path for structured run logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    allowed_scopes = [
        item.strip()
        for item in args.allowed_scopes.split(",")
        if item.strip()
    ]
    logger = RunLogger(Path(args.log_path))
    adapter = MockCRMAdapter(
        token=os.environ.get("CRM_API_TOKEN", ""),
        allowed_scopes=allowed_scopes,
    )
    orchestrator = AgentOrchestrator(adapter=adapter, logger=logger)
    run = orchestrator.run(args.customer_id)
    print(json.dumps(run, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
