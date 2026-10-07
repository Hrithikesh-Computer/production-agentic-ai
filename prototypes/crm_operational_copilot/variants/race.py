"""Deterministic N=50 claim-race runner used by the comparison harness."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

from approvals_store import Approval, ApprovalsStore

from variants.claims import (
    BrokenReadThenWriteApprovalsStore,
    ImmediateClaimApprovalsStore,
)
from variants.store_layout import SingleFileApprovalsStore, reset_shared_connections


def run_n50_claim_race(variant: str, path: Path) -> dict[str, Any]:
    store_types = {
        "baseline": ApprovalsStore,
        "store-layout-b": SingleFileApprovalsStore,
        "claim-b": ImmediateClaimApprovalsStore,
        "broken-control": BrokenReadThenWriteApprovalsStore,
    }
    store_type = store_types[variant]
    with store_type(path) as store:
        store.create(
            Approval(
                approval_id="approval-race",
                proposal_id="proposal-race",
                requester_id="requester",
                reviewer_id="reviewer",
                customer_id="customer",
                field_name="owner",
                proposed_value="new",
                previous_value="old",
                record_version=1,
                policy_hash="snapshot",
                created_at=100,
                expires_at=200,
                approved_at=120,
                state="APPROVED",
            )
        )

    BrokenReadThenWriteApprovalsStore.barrier = (
        Barrier(50) if variant == "broken-control" else None
    )

    def attempt(worker_number: int) -> bool:
        with store_type(path) as store:
            return store.claim("approval-race", f"execution-{worker_number}", 150)

    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            outcomes = list(executor.map(attempt, range(50)))
    finally:
        BrokenReadThenWriteApprovalsStore.barrier = None
        if variant == "store-layout-b":
            reset_shared_connections()

    accepted = sum(outcomes)
    return {
        "workers": 50,
        "accepted_claims": accepted,
        "single_winner_assertion": accepted == 1,
        "passed": accepted == 1,
    }