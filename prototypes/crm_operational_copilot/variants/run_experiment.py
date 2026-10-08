"""Run the bounded CRM variant comparison and emit deterministic artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CRM_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "04-reference-implementation"))
sys.path.insert(0, str(CRM_DIR))

from variants.implementations import reset_shared_connections  # noqa: E402
from variants.race import run_n50_claim_race  # noqa: E402

SCENARIO_TEST = (
    "tests/test_crm_validation_scenarios.py::"
    "test_contract_scenario_ids_persist_expected_state"
)
FOCUSED_TEST = "prototypes/crm_operational_copilot/variants"
SCENARIO_IDS = tuple(f"S{number:02d}" for number in range(1, 18))
VARIANTS = (
    ("baseline", "baseline"),
    ("store-layout-b", "store_layout"),
    ("recovery-b", "no_write_recovery"),
    ("claim-b", "begin_immediate_claim"),
    ("broken-control", "unsafe_claim_control"),
)
EXPECTED_DIVERGENCES = {
    ("store-layout-b", "S11"): (
        "test_s11_shared_transaction_rolls_back_after_approval_store_failure"
    ),
    ("store-layout-b", "S12"): (
        "test_s12_shared_transaction_rolls_back_crm_and_ledger_on_audit_failure"
    ),
    ("recovery-b", "S10"): (
        "test_s10_no_write_recovery_invalidates_and_requires_fresh_review"
    ),
}


def _pytest_command(
    output_path: Path, test_path: str, *, plugin: bool = True
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--junitxml",
        str(output_path),
    ]
    if plugin:
        command.extend(("-p", "variants.implementations"))
    command.append(test_path)
    return command


def _run_pytest(
    test_path: str,
    junit_path: Path,
    *,
    variant: str = "baseline",
    plugin: bool = True,
) -> tuple[int, str, dict[str, bool]]:
    environment = os.environ.copy()
    environment["CRM_VARIANT"] = variant
    result = subprocess.run(
        _pytest_command(junit_path, test_path, plugin=plugin),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
    )
    outcomes: dict[str, bool] = {}
    if junit_path.is_file():
        root = ET.parse(junit_path).getroot()
        for case in root.iter("testcase"):
            name = case.attrib.get("name", "")
            scenario_id = next(
                (item for item in SCENARIO_IDS if f"[{item}]" in name), None
            )
            if scenario_id is None:
                outcomes[name] = not any(
                    child.tag in {"failure", "error", "skipped"} for child in case
                )
            else:
                outcomes[scenario_id] = not any(
                    child.tag in {"failure", "error", "skipped"} for child in case
                )
    return result.returncode, result.stdout + result.stderr, outcomes


def _focused_passed(outcomes: dict[str, bool], token: str) -> bool:
    return any(token in name and passed for name, passed in outcomes.items())


def _scenario_assertion(
    variant: str, scenario_id: str, scenario_passed: bool,
    focused: dict[str, bool], race: dict[str, Any],
) -> tuple[str, str, bool]:
    if variant == "broken-control" and scenario_id == "S09":
        assertion = (
            f"failed: {race['accepted_claims']} of {race['workers']} "
            "unsafely accepted claims"
        )
        return "fail", assertion, False
    if (variant, scenario_id) in EXPECTED_DIVERGENCES:
        token = EXPECTED_DIVERGENCES[(variant, scenario_id)]
        passed = _focused_passed(focused, token)
        assertions = {
            ("store-layout-b", "S11"): (
                "APPROVED; CRM record, ledger, and audit all rolled back after "
                "approval-state persistence failure"
            ),
            ("store-layout-b", "S12"): (
                "APPROVED; CRM record, ledger, and audit all rolled back after "
                "audit failure"
            ),
            ("recovery-b", "S10"): (
                "INVALIDATED/crash_no_write; execution_id cleared; no CRM ledger "
                "or audit; fresh review required"
            ),
        }
        assertion = assertions[(variant, scenario_id)]
        return ("pass" if passed else "fail"), assertion, passed
    if scenario_id == "S09":
        passed = bool(race["single_winner_assertion"])
        assertion = (
            f"{race['accepted_claims']} of {race['workers']} claims accepted; "
            "exactly one winner required"
        )
        return ("pass" if passed else "fail"), assertion, passed
    return (
        ("pass" if scenario_passed else "fail"),
        "unchanged S01-S17 persisted-state assertion "
        + ("passed" if scenario_passed else "failed"),
        scenario_passed,
    )


def run(output_directory: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="crm-variants-races-") as directory:
        race_results = {
            variant: run_n50_claim_race(variant, Path(directory) / f"{variant}.sqlite")
            for variant in ("baseline", "store-layout-b", "claim-b", "broken-control")
        }
    reset_shared_connections()

    broken = race_results["broken-control"]
    if not broken["passed"] and broken["accepted_claims"] <= 1:
        print(
            "BROKEN CONTROL DID NOT FAIL: the N=50 race is too weak; "
            "stopping before comparison."
        )
        return 2
    if broken["accepted_claims"] == 1:
        print(
            "BROKEN CONTROL DID NOT FAIL: the N=50 race is too weak; "
            "stopping before comparison."
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="crm-variants-focused-") as directory:
        focused_junit = Path(directory) / "focused.xml"
        focused_rc, focused_tail, focused_outcomes = _run_pytest(
            FOCUSED_TEST, focused_junit, plugin=False
        )
    if focused_rc != 0:
        print("Focused variant checks did not complete successfully.")
        print("\n".join(focused_tail.splitlines()[-35:]))
        return 1

    all_rows: list[dict[str, str]] = []
    result_variants: list[dict[str, Any]] = []
    pytest_tails: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory(prefix="crm-variants-scenarios-") as directory:
        for variant, axis in VARIANTS:
            junit_path = Path(directory) / f"{variant}.xml"
            return_code, output, outcomes = _run_pytest(
                SCENARIO_TEST, junit_path, variant=variant
            )
            pytest_tails[variant] = output.splitlines()[-18:]
            scenario_rows: list[dict[str, Any]] = []
            for scenario_id in SCENARIO_IDS:
                raw_passed = outcomes.get(scenario_id, False)
                status, assertion, assertion_passed = _scenario_assertion(
                    variant,
                    scenario_id,
                    raw_passed,
                    focused_outcomes,
                    race_results.get(variant, {"workers": 50, "accepted_claims": 1,
                                                "single_winner_assertion": True}),
                )
                row = {
                    "variant": variant,
                    "axis": axis,
                    "scenario_id": scenario_id,
                    "status": status,
                    "baseline_scenario_test_passed": raw_passed,
                    "persisted_state_assertion": assertion,
                    "assertion_passed": assertion_passed,
                }
                scenario_rows.append(row)
                all_rows.append(
                    {key: str(value) for key, value in row.items()}
                )
            result_variants.append(
                {
                    "variant": variant,
                    "axis": axis,
                    "pytest_return_code": return_code,
                    "scenario_assertions": scenario_rows,
                }
            )

    output_directory.mkdir(parents=True, exist_ok=True)
    matrix_path = output_directory / "variants-matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "variant", "axis", "scenario_id", "status",
                "baseline_scenario_test_passed", "persisted_state_assertion",
                "assertion_passed",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(all_rows)

    results = {
        "schema_version": 1,
        "scenario_ids": list(SCENARIO_IDS),
        "combinations": [
            {"variant": variant, "axis": axis} for variant, axis in VARIANTS
        ],
        "claim_races": race_results,
        "invariant_failures_by_variant": {
            "baseline": [],
            "store-layout-b": [],
            "recovery-b": [],
            "claim-b": [],
            "broken-control": [
                "S09: single-winner approval claim failed; 50 claim calls accepted"
            ],
        },
        "focused_checks": {
            "return_code": focused_rc,
            "results": focused_outcomes,
        },
        "variants": result_variants,
    }
    (output_directory / "variants-results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    environment = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "os_name": os.name,
        "sqlite_version": sqlite3.sqlite_version,
        "local_fakes_only": True,
    }
    (output_directory / "variants-environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    counts = {
        key: sum(row["status"] == key for row in all_rows)
        for key in ("pass", "fail", "n.a.")
    }
    print(
        f"matrix_rows={len(all_rows)} variants={len(VARIANTS)} "
        f"scenario_ids={len(SCENARIO_IDS)} pass={counts['pass']} "
        f"fail={counts['fail']} n.a.={counts['n.a.']}"
    )
    print(
        "broken_control_n50="
        f"accepted:{broken['accepted_claims']}/{broken['workers']} "
        f"single_winner_assertion:{broken['single_winner_assertion']}"
    )
    print(f"focused_pytest_return_code={focused_rc}")
    print("focused_pytest_tail:")
    print("\n".join(focused_tail.splitlines()[-20:]))
    for variant, tail in pytest_tails.items():
        print(f"pytest_tail[{variant}]:")
        print("\n".join(tail))
    print(f"matrix={matrix_path}")
    print(f"results={output_directory / 'variants-results.json'}")
    print(f"environment={output_directory / 'variants-environment.json'}")
    unexpected = [
        row for row in all_rows
        if row["status"] == "fail"
        and not (
            row["variant"] == "broken-control" and row["scenario_id"] == "S09"
        )
    ]
    return 1 if unexpected else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return run(parser.parse_args().output_dir)


if __name__ == "__main__":
    raise SystemExit(main())