from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Task:
    name: str
    facts: list[str]
    required: list[str]
    stale: list[str]


TASKS: list[Task] = [
    Task(
        name="briefing",
        facts=[
            "The customer timezone is Pacific",
            "The original plan was rejected for budget reasons",
            "Key objective is to schedule the executive briefing",
            "A previous draft mentioned an internal escalation path",
        ],
        required=[
            "The customer timezone is Pacific",
            "Key objective is to schedule the executive briefing",
        ],
        stale=[
            "The original plan was rejected for budget reasons",
            "A previous draft mentioned an internal escalation path",
        ],
    ),
    Task(
        name="risk-review",
        facts=[
            "Risk policy version is v4",
            "A prior alternate path was rejected for missing evidence",
            "The final recommendation must cite evidence before summarizing",
            "The user asked for a short, factual summary",
        ],
        required=[
            "Risk policy version is v4",
            "The final recommendation must cite evidence before summarizing",
        ],
        stale=[
            "A prior alternate path was rejected for missing evidence",
            "The user asked for a short, factual summary",
        ],
    ),
    Task(
        name="handoff",
        facts=[
            "The reviewer requested source checks before handoff",
            "The workflow was retried after a partial failure",
            "The user wants a concise handoff summary",
            "A stale assumption previously mentioned an outdated route",
        ],
        required=[
            "The reviewer requested source checks before handoff",
            "The user wants a concise handoff summary",
        ],
        stale=[
            "The workflow was retried after a partial failure",
            "A stale assumption previously mentioned an outdated route",
        ],
    ),
]


def _history(policy: str, task: Task) -> list[str]:
    if policy == "full-history":
        return task.facts
    if policy == "sliding-window":
        return task.facts[-2:]
    return [
        fact
        for fact in task.facts
        if "rejected" not in fact.lower() and "stale" not in fact.lower()
    ]


def _score(policy: str, task: Task) -> dict[str, float | int | str]:
    history = _history(policy, task)
    required_hit = sum(1 for fact in task.required if fact in history)
    stale_hit = sum(1 for fact in task.stale if fact in history)
    success = 1 if required_hit == len(task.required) and stale_hit <= 1 else 0
    return {
        "policy": policy,
        "task": task.name,
        "required_hit": required_hit,
        "stale_hit": stale_hit,
        "success": success,
        "token_count": len(" ".join(history).split()),
    }


def main() -> None:
    policies = ["full-history", "sliding-window", "summary-hybrid"]
    rows: list[dict[str, float | int | str]] = []

    for policy in policies:
        for task in TASKS:
            rows.append(_score(policy, task))

    print("policy,task,required_hit,stale_hit,success,token_count")
    for row in rows:
        print(
            f"{row['policy']},{row['task']},{row['required_hit']},{row['stale_hit']},{row['success']},{row['token_count']}"
        )

    by_policy: dict[str, list[dict[str, float | int | str]]] = {}
    for row in rows:
        by_policy.setdefault(str(row["policy"]), []).append(row)

    print("\nPolicy summary:")
    for policy, items in by_policy.items():
        average_success = mean(float(item["success"]) for item in items)
        avg_tokens = mean(float(item["token_count"]) for item in items)
        print(f"{policy}: success={average_success:.2f}, avg_tokens={avg_tokens:.1f}")

    print(
        "\nThis benchmark compares retention policies under a small fixed set of "
        "context-lifecycle tasks; it is intentionally local and synthetic."
    )


if __name__ == "__main__":
    main()
