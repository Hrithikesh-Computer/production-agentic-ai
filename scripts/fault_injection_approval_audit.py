"""Inject review/audit failures against current and fixed SQLite variants."""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CRM_DIR = ROOT / "prototypes" / "crm_operational_copilot"
sys.path[:0] = [
    str(ROOT / "tests"),
    str(CRM_DIR),
    str(ROOT / "04-reference-implementation"),
]

import test_crm_validation_scenarios as scenarios  # noqa: E402
from variants.store_layout import (  # noqa: E402
    SingleFileApprovalsStore,
    SingleFileAuditStore,
    SingleFileCRMStore,
    SingleFileExecutionService,
    reset_shared_connections,
)
from variants.store_layout_fixed import (  # noqa: E402
    SingleFileExecutionServiceWithAtomicReview,
)

REVIEWER = "reviewer"
REVIEWER_SCOPE = "approve:crm-writes"

FAULT_POINTS = (
    "audit_write_raises_before_atomic_commit",
    "audit_error_after_state_update",
    "audit_succeeds_but_final_commit_raises",
    "review_interrupted_after_state_update",
)
FIELDNAMES = (
    "variant",
    "fault_point",
    "state_after_review",
    "audit_present",
    "execute_succeeds",
    "audit_event_emitted",
    "classification",
    "fault_detail",
)


def _variant_context(service_type: type):
    return patch.multiple(
        scenarios,
        ApprovalsStore=SingleFileApprovalsStore,
        CRMStore=SingleFileCRMStore,
        AuditStore=SingleFileAuditStore,
        CRMExecutionService=service_type,
    )


def _inject(
    fault_point: str,
    approvals: Any,
    audit: Any,
) -> str:
    if fault_point == "audit_write_raises_before_atomic_commit":
        audit.fail_next_write = True
        return "AuditStore.write raises injected OSError before inserting event"

    if fault_point == "audit_error_after_state_update":
        original = approvals.set_review

        def update_then_raise(*args: Any, **kwargs: Any) -> bool:
            changed = original(*args, **kwargs)
            if changed:
                raise OSError("injected error after approval state update")
            return changed

        approvals.set_review = update_then_raise
        return "set_review updates, then raises before audit call"

    if fault_point == "review_interrupted_after_state_update":
        original = approvals.set_review

        def update_then_exit(*args: Any, **kwargs: Any) -> bool:
            changed = original(*args, **kwargs)
            if changed:
                raise SystemExit("simulated process death before audit call")
            return changed

        approvals.set_review = update_then_exit
        return (
            "set_review updates, then raises SystemExit before audit call; "
            "the in-process harness catches BaseException and rolls back, so "
            "this is not a process-death durability test"
        )

    if fault_point == "audit_succeeds_but_final_commit_raises":
        connection = approvals.connection
        original_commit = connection.commit
        commit_count = 0

        def fail_commit() -> None:
            nonlocal commit_count
            commit_count += 1
            if getattr(connection, "defer_commits", False):
                if commit_count >= 3:
                    raise OSError("injected final transaction commit failure")
                return original_commit()
            raise OSError("injected approval-state commit failure before audit")

        connection.commit = fail_commit
        connection._fault_campaign_original_commit = original_commit
        return (
            "fixed final commit fails after staged approval and audit; "
            "current state commit fails before audit"
        )

    raise ValueError(f"unknown fault point: {fault_point}")


def _run_one(variant: str, fault_point: str) -> dict[str, str]:
    service_type = (
        SingleFileExecutionServiceWithAtomicReview
        if variant == "fixed"
        else SingleFileExecutionService
    )
    reset_shared_connections()
    with tempfile.TemporaryDirectory(prefix="approval-audit-fault-") as temp:
        try:
            with _variant_context(service_type):
                service, approvals, crm, audit, *_ = scenarios._system(
                    Path(temp), state="PENDING"
                )
                detail = _inject(fault_point, approvals, audit)
                review_status = "raised"
                try:
                    review_result = service.review(
                        "approval-1",
                        reviewer_id=REVIEWER,
                        approve=True,
                        reviewer_scope=REVIEWER_SCOPE,
                    )
                    review_status = review_result.status
                    if review_result.audit_error:
                        detail += f"; reported audit_error={review_result.audit_error}"
                except BaseException as error:
                    review_status = f"raised:{type(error).__name__}"
                    detail += f"; review raised {type(error).__name__}: {error}"
                    try:
                        approvals.connection.rollback()
                    except Exception:
                        pass

                original_commit = getattr(
                    approvals.connection,
                    "_fault_campaign_original_commit",
                    None,
                )
                if original_commit is not None:
                    approvals.connection.commit = original_commit
                    del approvals.connection._fault_campaign_original_commit

                approval = approvals.get("approval-1")
                state_after_review = approval.state if approval else "MISSING"
                audit_after_review = audit.events_for_approval("approval-1")
                approval_event_after_review = any(
                    event.event_type == "approval_approved"
                    for event in audit_after_review
                )

                execute_result = scenarios._execute(service)
                execute_succeeds = execute_result.status == "completed"
                final_events = audit.events_for_approval("approval-1")
                approval_event_emitted = any(
                    event.event_type == "approval_approved" for event in final_events
                )

                if (
                    state_after_review == "APPROVED"
                    and not approval_event_after_review
                    and execute_succeeds
                    and not approval_event_emitted
                ):
                    classification = "FAIL-OPEN"
                elif (
                    not approval_event_after_review
                    and review_status in {"completed", "rejected"}
                ):
                    classification = "FAIL-SILENT"
                else:
                    classification = "FAIL-CLOSED"

                row = {
                    "variant": variant,
                    "fault_point": fault_point,
                    "state_after_review": state_after_review,
                    "audit_present": str(bool(audit_after_review)).lower(),
                    "execute_succeeds": str(execute_succeeds).lower(),
                    "audit_event_emitted": str(approval_event_emitted).lower(),
                    "classification": classification,
                    "fault_detail": detail,
                }
                print(
                    f"{variant} | {fault_point} | state={state_after_review} "
                    f"audit_present={row['audit_present']} "
                    f"execute_succeeds={row['execute_succeeds']} "
                    f"approval_audit_emitted={row['audit_event_emitted']} "
                    f"classification={classification}"
                )
                return row
        finally:
            reset_shared_connections()


def run(output_path: Path) -> int:
    if output_path.exists():
        raise FileExistsError(
            f"refusing to overwrite existing campaign output: {output_path}"
        )
    rows = [
        _run_one(variant, point)
        for variant in ("current", "fixed")
        for point in FAULT_POINTS
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=FIELDNAMES,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    for variant in ("current", "fixed"):
        variant_rows = [row for row in rows if row["variant"] == variant]
        fail_open = sum(row["classification"] == "FAIL-OPEN" for row in variant_rows)
        fail_closed = sum(
            row["classification"] == "FAIL-CLOSED" for row in variant_rows
        )
        fail_silent = sum(
            row["classification"] == "FAIL-SILENT" for row in variant_rows
        )
        print(
            f"summary[{variant}]: fail_open={fail_open}/{len(variant_rows)} "
            f"fail_closed={fail_closed} fail_silent={fail_silent}"
        )
    print(f"results_csv={output_path.resolve()}")
    print(f"result_rows={len(rows)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "fault-injection-approval-audit.csv",
    )
    args = parser.parse_args()
    return run(args.output)


if __name__ == "__main__":
    raise SystemExit(main())