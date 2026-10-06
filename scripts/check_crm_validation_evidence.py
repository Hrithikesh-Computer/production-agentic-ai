"""Regenerate CRM validation evidence and verify its contract scenario IDs."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CRM_DIR = ROOT / "prototypes" / "crm_operational_copilot"
ARTIFACT_DIR = ROOT / "artifacts" / "crm-validation"
HARNESS = CRM_DIR / "validation_harness.py"
sys.path.insert(0, str(CRM_DIR))

from validation_harness import read_contract_scenarios  # noqa: E402

COMMITTED_OUTPUTS = ("results.json", "scenario-matrix.csv")
ENVIRONMENT_FIELDS = {
    "commit",
    "python_version",
    "started_at_utc",
    "completed_at_utc",
}


def validate_scenario_ids(
    result_path: Path,
    matrix_path: Path,
    expected_ids: tuple[str, ...],
) -> None:
    results: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    result_ids = tuple(
        row.get("scenario_id") for row in results.get("scenarios", [])
    )
    if result_ids != expected_ids or len(set(result_ids)) != len(expected_ids):
        raise ValueError(
            f"results.json must contain each contract ID exactly once in order; "
            f"found {result_ids!r}"
        )

    with matrix_path.open(encoding="utf-8", newline="") as matrix_file:
        matrix_rows = list(csv.DictReader(matrix_file))
    matrix_ids = tuple(row.get("scenario_id") for row in matrix_rows)
    if matrix_ids != expected_ids or len(set(matrix_ids)) != len(expected_ids):
        raise ValueError(
            "scenario-matrix.csv must contain each contract ID exactly once "
            f"in order; found {matrix_ids!r}"
        )
    if any(row.get("status") != "passed" for row in results["scenarios"]):
        raise ValueError("results.json contains a scenario that did not pass")
    if any(row.get("status") != "passed" for row in matrix_rows):
        raise ValueError("scenario-matrix.csv contains a scenario that did not pass")


def validate_environment(path: Path) -> None:
    metadata: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if set(metadata) != ENVIRONMENT_FIELDS:
        raise ValueError(
            f"environment.json fields must be exactly {sorted(ENVIRONMENT_FIELDS)}"
        )
    if not isinstance(metadata["commit"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", metadata["commit"]
    ):
        raise ValueError("environment.json commit must be a full lowercase SHA-1")
    if not isinstance(metadata["python_version"], str) or not metadata[
        "python_version"
    ]:
        raise ValueError("environment.json python_version must be non-empty")
    for field in ("started_at_utc", "completed_at_utc"):
        value = metadata[field]
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(f"environment.json {field} must be a UTC timestamp")
        datetime.fromisoformat(value[:-1] + "+00:00")


def _run_harness(output_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(HARNESS), "--output-dir", str(output_dir)],
        cwd=ROOT,
        check=True,
        timeout=600,
    )


def main() -> int:
    try:
        expected_ids = tuple(
            scenario.scenario_id for scenario in read_contract_scenarios()
        )
        with tempfile.TemporaryDirectory(prefix="crm-evidence-check-") as directory:
            generated_dir = Path(directory)
            _run_harness(generated_dir)
            generated_results = generated_dir / "results.json"
            generated_matrix = generated_dir / "scenario-matrix.csv"
            validate_scenario_ids(
                generated_results, generated_matrix, expected_ids
            )
            validate_environment(generated_dir / "environment.json")

            for filename in COMMITTED_OUTPUTS:
                committed = ARTIFACT_DIR / filename
                regenerated = generated_dir / filename
                if not committed.is_file():
                    raise ValueError(f"committed output is missing: {committed}")
                if committed.read_text(encoding="utf-8") != regenerated.read_text(
                    encoding="utf-8"
                ):
                    raise ValueError(f"regenerated output differs from {committed}")

        validate_scenario_ids(
            ARTIFACT_DIR / "results.json",
            ARTIFACT_DIR / "scenario-matrix.csv",
            expected_ids,
        )
        validate_environment(ARTIFACT_DIR / "environment.json")
    except (
        OSError,
        ValueError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ) as error:
        print(f"CRM validation evidence check failed: {error}")
        return 1

    print(
        "CRM validation evidence matches regenerated deterministic outputs: "
        f"{len(expected_ids)} contract scenarios, each exactly once."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
