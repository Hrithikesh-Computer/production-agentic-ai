"""Run contract scenarios and write deterministic results plus run metadata."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).with_name("VALIDATION-CONTRACT.md")
SCENARIO_TEST_PATH = (
    "tests/test_crm_validation_scenarios.py::"
    "test_contract_scenario_ids_persist_expected_state"
)
CONCURRENCY_TEST_PATH = (
    "tests/test_crm_validation_scenarios.py::"
    "test_s09_fifty_separate_processes_have_exactly_one_persisted_claim_winner"
)
EXPECTED_SCENARIO_IDS = tuple(f"S{number:02d}" for number in range(1, 18))
FIXED_CLOCK = 150


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    setup: str
    expected_persisted_state: str


def read_contract_scenarios(path: Path = CONTRACT) -> list[Scenario]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_matrix = False
    scenarios: list[Scenario] = []
    for line in lines:
        if line.strip() == "## Scenario matrix":
            in_matrix = True
            continue
        if in_matrix and line.startswith("## "):
            break
        if not in_matrix or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] == "Scenario ID" or set("".join(cells)) <= {"-", ":"}:
            continue
        if len(cells) != 3:
            raise ValueError(f"Malformed scenario matrix row: {line}")
        scenario_id = cells[0].strip("`")
        scenarios.append(
            Scenario(
                scenario_id=scenario_id,
                setup=cells[1],
                expected_persisted_state=cells[2],
            )
        )

    actual_ids = tuple(scenario.scenario_id for scenario in scenarios)
    if actual_ids != EXPECTED_SCENARIO_IDS:
        raise ValueError(
            "Contract scenario IDs must be exactly S01-S17 in order; "
            f"found {actual_ids!r}"
        )
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("Contract scenario IDs must not be duplicated")
    return scenarios


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _commit_hash() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _run_scenarios(scenarios: list[Scenario]) -> tuple[list[dict[str, str]], int, str]:
    with tempfile.TemporaryDirectory(prefix="crm-validation-") as temporary_directory:
        junit_path = Path(temporary_directory) / "junit.xml"
        selectors = [
            f"{SCENARIO_TEST_PATH}[{scenario.scenario_id}]"
            for scenario in scenarios
        ]
        selectors.append(CONCURRENCY_TEST_PATH)
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--junitxml",
            str(junit_path),
            *selectors,
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        junit_root = ET.parse(junit_path).getroot() if junit_path.is_file() else None
        test_results: dict[str, list[bool]] = {}
        if junit_root is not None:
            for case in junit_root.iter("testcase"):
                test_name = case.attrib.get("name", "")
                scenario_id = next(
                    (
                        candidate
                        for candidate in EXPECTED_SCENARIO_IDS
                        if f"[{candidate}]" in test_name
                    ),
                    None,
                )
                if scenario_id is not None:
                    test_results.setdefault(scenario_id, []).append(
                        not any(
                            child.tag in {"failure", "error", "skipped"}
                            for child in case
                        )
                    )
                elif "test_s09_fifty_separate_processes" in test_name:
                    test_results.setdefault("S09_STRESS", []).append(
                        not any(
                            child.tag in {"failure", "error", "skipped"}
                            for child in case
                        )
                    )

        rows: list[dict[str, str]] = []
        for scenario in scenarios:
            passed = test_results.get(scenario.scenario_id, [])
            if scenario.scenario_id == "S09":
                stress = test_results.get("S09_STRESS", [])
                success = (
                    len(passed) == 1
                    and passed[0]
                    and len(stress) == 5
                    and all(stress)
                )
            else:
                success = len(passed) == 1 and passed[0]
            rows.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "status": "passed" if success else "failed",
                }
            )
        return rows, result.returncode, result.stdout + result.stderr


def run(output_directory: Path) -> int:
    started_at = _utc_now()
    scenarios = read_contract_scenarios()
    rows, return_code, output = _run_scenarios(scenarios)
    completed_at = _utc_now()

    output_directory.mkdir(parents=True, exist_ok=True)
    results = {
        "schema_version": 1,
        "fixed_clock": FIXED_CLOCK,
        "id_strategy": "fixed per-scenario execution/audit counters",
        "scenarios": rows,
    }
    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_directory / "scenario-matrix.csv").open(
        "w", encoding="utf-8", newline=""
    ) as result_file:
        writer = csv.DictWriter(
            result_file,
            fieldnames=(
                "scenario_id",
                "setup",
                "expected_persisted_state",
                "status",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for scenario, row in zip(scenarios, rows, strict=True):
            writer.writerow(
                {
                    **asdict(scenario),
                    "status": row["status"],
                }
            )

    environment = {
        "commit": _commit_hash(),
        "python_version": platform.python_version(),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
    }
    (output_directory / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    failed_ids = [row["scenario_id"] for row in rows if row["status"] != "passed"]
    print(f"scenario_rows={len(rows)} expected_rows=17")
    print(f"passed={len(rows) - len(failed_ids)} failed={len(failed_ids)}")
    print(f"results={output_directory / 'results.json'}")
    print(f"matrix={output_directory / 'scenario-matrix.csv'}")
    print(f"environment={output_directory / 'environment.json'}")
    if return_code != 0 or failed_ids:
        print(f"failed_scenario_ids={','.join(failed_ids)}")
        print(output[-4000:])
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "crm-validation",
    )
    args = parser.parse_args()
    return run(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
