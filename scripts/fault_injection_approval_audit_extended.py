"""Extended D9 durability probes for current and fixed SQLite variants."""

from __future__ import annotations

import argparse
import csv
import errno
import os
import sqlite3
import subprocess
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
from authority_policy import AggregationConstraint, Grant, PolicyRule  # noqa: E402
from identity_provider import Identity, LocalIdentityProvider  # noqa: E402
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

CAMPAIGN_ID = "durability-20261009-repair-03"
CSV_PATH = ROOT / "artifacts" / "fault-injection-approval-audit.csv"
FAULT_POINTS = (
    "os_process_exit_after_state_commit_before_audit",
    "audit_write_enospc",
    "audit_write_then_fsync_hook_raises",
    "shared_database_corrupt_on_reopen",
    "review_clock_before_approval_created_at",
    "audit_writer_backdates_event",
)
FIELDS = (
    "campaign_id",
    "variant",
    "fault_point",
    "state_after_restart",
    "audit_present",
    "execute_succeeds",
    "approval_audit_event_emitted",
    "classification",
    "fault_detail",
    "crm_ledger_rows_before_execution",
    "execution_status_after_review",
    "state_after_execution_attempt",
    "crm_ledger_rows_after_execution",
    "retry_review_status",
    "state_after_retry",
    "approval_audit_present_after_retry",
    "crm_ledger_rows_after_retry",
)


def _classes(variant: str):
    service_class = (
        SingleFileExecutionServiceWithAtomicReview
        if variant == "fixed"
        else SingleFileExecutionService
    )
    return service_class


def _context(service_class: type):
    return patch.multiple(
        scenarios,
        ApprovalsStore=SingleFileApprovalsStore,
        CRMStore=SingleFileCRMStore,
        AuditStore=SingleFileAuditStore,
        CRMExecutionService=service_class,
    )


def _worker_exit_after_state_commit(directory: Path, variant: str) -> int:
    service_class = _classes(variant)
    with _context(service_class):
        service, approvals, *_ = scenarios._system(directory, state="PENDING")
        original_set_review = approvals.set_review

        def commit_then_os_exit(*args: Any, **kwargs: Any) -> bool:
            changed = original_set_review(*args, **kwargs)
            if changed:
                os._exit(87)
            return changed

        approvals.set_review = commit_then_os_exit
        service.review(
            "approval-1",
            reviewer_id="reviewer",
            approve=True,
            reviewer_scope="approve:crm-writes",
        )
    return 88


def _build_existing(directory: Path, variant: str, *, at: int = 150):
    identities = LocalIdentityProvider(
        [
            Identity("requester", "tenant-a", frozenset({"write:accounts"})),
            Identity("reviewer", "tenant-a", frozenset({"approve:crm-writes"})),
        ],
        clock=lambda: at,
    )
    rules = [PolicyRule("write:accounts", "allow", 10)]
    constraints = [
        AggregationConstraint(
            frozenset({"write:accounts", "export"}), "restricted pair"
        )
    ]
    requester_grant = Grant("requester", "write:accounts", 0, 300)
    reviewer_grant = Grant("reviewer", "write:accounts", 0, 300)
    grants = {
        ("requester", "write:accounts"): requester_grant,
        ("reviewer", "write:accounts"): reviewer_grant,
    }
    approvals = SingleFileApprovalsStore(directory / "approvals.sqlite")
    crm = SingleFileCRMStore(directory / "crm.sqlite")
    audit = SingleFileAuditStore(directory / "audit.sqlite")
    service_class = _classes(variant)
    service = service_class(
        identities=identities,
        approvals=approvals,
        crm=crm,
        audit=audit,
        rules=rules,
        grants=grants,
        aggregation_constraints=constraints,
        clock=lambda: at,
        execution_id_factory=lambda: "execution-after-reopen",
        audit_id_factory=lambda: f"audit-after-reopen-{audit.count() + 1}",
    )
    return service, approvals, crm, audit


def _run_os_exit(directory: Path, variant: str) -> tuple[int, str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-variant",
        variant,
        "--worker-directory",
        str(directory),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def _initialize(directory: Path) -> None:
    with _context(SingleFileExecutionService):
        _, approvals, crm, audit, *_ = scenarios._system(directory, state="PENDING")
        del approvals, crm, audit
    reset_shared_connections()


def _campaign_one(variant: str, point: str) -> dict[str, str]:
    reset_shared_connections()
    with tempfile.TemporaryDirectory(prefix="approval-audit-durable-") as temp:
        directory = Path(temp)
        fault_detail = ""
        review_status = "not_run"
        reopen_error = ""
        retry_review_status = "not_attempted"
        approval_audit_after_retry: bool | str

        if point == "os_process_exit_after_state_commit_before_audit":
            exit_code, worker_output = _run_os_exit(directory, variant)
            review_status = f"process_exit:{exit_code}"
            fault_detail = (
                f"child OS process exited with code {exit_code}; "
                f"child_output={worker_output!r}"
            )
            reset_shared_connections()

        elif point == "shared_database_corrupt_on_reopen":
            _initialize(directory)
            (directory / "crm-variant.sqlite").write_bytes(b"corrupt-sqlite-db")
            fault_detail = (
                "overwrote the shared SQLite file for approvals, CRM, and audit "
                "with invalid bytes; "
                "all three stores become unavailable, not audit-only"
            )

        else:
            with _context(_classes(variant)):
                service, approvals, _, audit, *_ = scenarios._system(
                    directory, state="PENDING"
                )
                if point == "audit_write_enospc":
                    def enospc(_event: Any) -> None:
                        raise OSError(
                            errno.ENOSPC, "injected disk full during audit write"
                        )

                    audit.write = enospc
                    fault_detail = (
                        "simulated OSError(errno.ENOSPC) from AuditStore.write"
                    )
                elif point == "audit_write_then_fsync_hook_raises":
                    original_write = audit.write

                    def write_then_fsync_fault(event: Any) -> None:
                        original_write(event)
                        raise OSError(
                            errno.EIO,
                            "simulated failure at audit fsync boundary",
                        )

                    audit.write = write_then_fsync_fault
                    fault_detail = (
                        "simulated fsync hook raises after AuditStore.write; "
                        "not an OS fsync/power-loss test"
                    )
                elif point == "review_clock_before_approval_created_at":
                    service.clock = lambda: 90
                    fault_detail = (
                        "service clock returns 90 while approval.created_at is 100"
                    )
                elif point == "audit_writer_backdates_event":
                    original_write = audit.write

                    def write_backdated_event(event: Any) -> None:
                        from dataclasses import replace

                        original_write(replace(event, event_ts=event.event_ts - 60))

                    audit.write = write_backdated_event
                    fault_detail = (
                        "injected audit writer rewrites event_ts 60 seconds earlier "
                        "after service-level timestamp normalization"
                    )
                else:
                    raise ValueError(point)

                try:
                    result = service.review(
                        "approval-1",
                        reviewer_id="reviewer",
                        approve=True,
                        reviewer_scope="approve:crm-writes",
                    )
                    review_status = result.status
                    fault_detail += f"; review_status={result.status}"
                except BaseException as error:
                    review_status = f"raised:{type(error).__name__}"
                    fault_detail += f"; review_exception={type(error).__name__}:{error}"
            reset_shared_connections()

        if point == "shared_database_corrupt_on_reopen":
            state = "UNKNOWN"
            events = []
            execute_succeeds = False
            ledger_rows_before_execution = "unknown"
            execution_status = "unavailable"
            state_after_execution_attempt = "UNKNOWN"
            ledger_rows_after_execution = "unknown"
            state_after_retry = "unavailable"
            approval_audit_after_retry = "unavailable"
            ledger_rows_after_retry = "unknown"
            retry_review_status = "unavailable"
            try:
                service, approvals, crm, audit = _build_existing(directory, variant)
                approval = approvals.get("approval-1")
                state = approval.state if approval else "MISSING"
                events = audit.events_for_approval("approval-1")
                execution = scenarios._execute(service)
                execution_status = execution.status
                execute_succeeds = execution.status == "completed"
            except (sqlite3.DatabaseError, OSError) as error:
                reopen_error = f"{type(error).__name__}: {error}"
                fault_detail += f"; reopen_error={reopen_error}"
            finally:
                reset_shared_connections()
            classification = "UNAVAILABLE_UNRECOVERED"
        else:
            try:
                service, approvals, crm, audit = _build_existing(directory, variant)
                approval = approvals.get("approval-1")
                state = approval.state if approval else "MISSING"
                events = audit.events_for_approval("approval-1")
                audit_present = any(
                    event.event_type == "approval_approved" for event in events
                )
                approval_event_emitted = audit_present
                ledger_rows_before_execution = str(len(crm.ledger_rows()))
                execution = scenarios._execute(service)
                execution_status = execution.status
                execute_succeeds = execution.status == "completed"
                approval_after_execution = approvals.get("approval-1")
                state_after_execution_attempt = (
                    approval_after_execution.state
                    if approval_after_execution
                    else "MISSING"
                )
                ledger_rows_after_execution = str(len(crm.ledger_rows()))

                retried = False
                if state == "PENDING" and not audit_present:
                    retry = service.review(
                        "approval-1",
                        reviewer_id="reviewer",
                        approve=True,
                        reviewer_scope="approve:crm-writes",
                    )
                    retry_review_status = retry.status
                    retried = True
                elif (
                    state == "AUDIT_PENDING"
                    and approval is not None
                    and approval.execution_id is None
                ):
                    recovered = service.recover()
                    retry_review_status = (
                        recovered[0].status if recovered else "no_recovery_result"
                    )
                    retried = bool(recovered)
                if retried:
                    approval_after_retry = approvals.get("approval-1")
                    state_after_retry = (
                        approval_after_retry.state
                        if approval_after_retry
                        else "MISSING"
                    )
                    retry_events = audit.events_for_approval("approval-1")
                    approval_audit_after_retry = any(
                        event.event_type == "approval_approved"
                        for event in retry_events
                    )
                else:
                    state_after_retry = "not_attempted"
                    approval_audit_after_retry = "not_attempted"
                ledger_rows_after_retry = str(len(crm.ledger_rows()))

                if point == "audit_writer_backdates_event":
                    approval = approvals.get("approval-1")
                    approved_event = next(
                        (
                            event
                            for event in events
                            if event.event_type == "approval_approved"
                        ),
                        None,
                    )
                    if (
                        approved_event is not None
                        and approval is not None
                        and approved_event.event_ts < approval.created_at
                    ):
                        classification = "FAIL-SILENT"
                        fault_detail += (
                            f"; detected persisted event_ts={approved_event.event_ts} "
                            f"< approval.created_at={approval.created_at}"
                        )
                    else:
                        classification = "INVARIANT_HELD"
                elif point == "review_clock_before_approval_created_at":
                    approval = approvals.get("approval-1")
                    approved_event = next(
                        (
                            event
                            for event in events
                            if event.event_type == "approval_approved"
                        ),
                        None,
                    )
                    if (
                        approved_event is not None
                        and approval is not None
                        and approval.approved_at is not None
                        and approval.approved_at >= approval.created_at
                        and approved_event.event_ts >= approval.created_at
                    ):
                        classification = "INVARIANT_HELD"
                    else:
                        classification = "FAIL-SILENT"
                elif (
                    state == "APPROVED"
                    and not audit_present
                    and execute_succeeds
                    and ledger_rows_after_execution > ledger_rows_before_execution
                ):
                    classification = "FAIL-OPEN"
                elif (
                    state == "APPROVED"
                    and audit_present
                    and review_status == "unresolved"
                    and execute_succeeds
                ):
                    classification = "COMMITTED_BUT_REPORTED_UNRESOLVED"
                elif (
                    state in {"PENDING", "AUDIT_PENDING"}
                    and ledger_rows_before_execution == "0"
                    and retry_review_status in {"completed", "rejected"}
                    and state_after_retry == "APPROVED"
                    and approval_audit_after_retry
                    and ledger_rows_after_retry == "0"
                ):
                    classification = "RECOVERABLE_FAIL_CLOSED"
                else:
                    classification = "FAIL-CLOSED_UNRECOVERED"
            except (sqlite3.DatabaseError, OSError) as error:
                state = "UNKNOWN"
                audit_present = False
                execute_succeeds = False
                approval_event_emitted = False
                ledger_rows_before_execution = "unknown"
                execution_status = "unavailable"
                state_after_execution_attempt = "UNKNOWN"
                ledger_rows_after_execution = "unknown"
                state_after_retry = "unavailable"
                approval_audit_after_retry = "unavailable"
                ledger_rows_after_retry = "unknown"
                retry_review_status = "unavailable"
                classification = "UNAVAILABLE_UNRECOVERED"
                reopen_error = f"{type(error).__name__}: {error}"
                fault_detail += f"; reopen_error={reopen_error}"
            finally:
                reset_shared_connections()

        if point == "shared_database_corrupt_on_reopen":
            audit_present = False
            approval_event_emitted = False
        else:
            approval_event_emitted = approval_event_emitted or any(
                event.event_type == "approval_approved" for event in events
            )

        row = {
            "campaign_id": CAMPAIGN_ID,
            "variant": variant,
            "fault_point": point,
            "state_after_restart": state,
            "audit_present": str(audit_present).lower(),
            "execute_succeeds": str(execute_succeeds).lower(),
            "approval_audit_event_emitted": str(approval_event_emitted).lower(),
            "classification": classification,
            "fault_detail": fault_detail,
            "crm_ledger_rows_before_execution": ledger_rows_before_execution,
            "execution_status_after_review": execution_status,
            "state_after_execution_attempt": state_after_execution_attempt,
            "crm_ledger_rows_after_execution": ledger_rows_after_execution,
            "retry_review_status": retry_review_status,
            "state_after_retry": state_after_retry,
            "approval_audit_present_after_retry": (
                str(approval_audit_after_retry).lower()
                if isinstance(approval_audit_after_retry, bool)
                else approval_audit_after_retry
            ),
            "crm_ledger_rows_after_retry": ledger_rows_after_retry,
        }
        print(
            f"{variant} | {point} | state_after_restart={state} "
            f"audit_present={row['audit_present']} "
            f"ledger_before_execute={ledger_rows_before_execution} "
            f"execute_status={execution_status} "
            f"ledger_after_execute={ledger_rows_after_execution} "
            f"retry={retry_review_status} state_after_retry={state_after_retry} "
            f"classification={classification}"
        )
        return row


def _append_rows(path: Path, rows: list[dict[str, str]]) -> None:
    old_rows: list[dict[str, str]] = []
    old_fields: list[str] = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            old_fields = list(reader.fieldnames or [])
            old_rows = [dict(row) for row in reader]
    campaign_ids = {row["campaign_id"] for row in rows}
    old_rows = [row for row in old_rows if row.get("campaign_id") not in campaign_ids]
    fields = list(dict.fromkeys([*old_fields, *FIELDS]))
    if "campaign_id" not in fields:
        fields.insert(0, "campaign_id")
    if "campaign_id" not in old_fields:
        for row in old_rows:
            row["campaign_id"] = "base-5point-prior-campaign"
    temp_path = path.with_suffix(".csv.tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(old_rows)
        writer.writerows(rows)
    temp_path.replace(path)


def run() -> int:
    rows = [
        _campaign_one(variant, point)
        for variant in ("current", "fixed")
        for point in FAULT_POINTS
    ]
    _append_rows(CSV_PATH, rows)
    for variant in ("current", "fixed"):
        variant_rows = [row for row in rows if row["variant"] == variant]
        classifications = {row["classification"] for row in variant_rows}
        fail_open = sum(row["classification"] == "FAIL-OPEN" for row in variant_rows)
        fail_closed = sum(
            row["classification"]
            in {"RECOVERABLE_FAIL_CLOSED", "FAIL-CLOSED_UNRECOVERED"}
            for row in variant_rows
        )
        fail_silent = sum(
            row["classification"] == "FAIL-SILENT" for row in variant_rows
        )
        recoverable = sum(
            row["classification"] == "RECOVERABLE_FAIL_CLOSED"
            for row in variant_rows
        )
        other = sorted(
            classifications
            - {
                "FAIL-OPEN",
                "FAIL-SILENT",
                "RECOVERABLE_FAIL_CLOSED",
                "FAIL-CLOSED_UNRECOVERED",
            }
        )
        print(
            f"summary[{variant}]: "
            f"fail_open={fail_open} fail_closed={fail_closed} "
            f"fail_silent={fail_silent} recoverable_fail_closed={recoverable} "
            f"other={other}"
        )
    print(f"campaign_id={CAMPAIGN_ID}")
    print(f"replaced_campaign_rows={len(rows)}")
    print(f"csv_path={CSV_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-variant", choices=("current", "fixed"))
    parser.add_argument("--worker-directory", type=Path)
    args = parser.parse_args()
    if args.worker_variant:
        if args.worker_directory is None:
            parser.error("--worker-directory is required with --worker-variant")
        return _worker_exit_after_state_commit(
            args.worker_directory, args.worker_variant
        )
    return run()


if __name__ == "__main__":
    raise SystemExit(main())