from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest
from validation_harness import EXPECTED_SCENARIO_IDS, read_contract_scenarios

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from check_crm_validation_evidence import validate_scenario_ids  # noqa: E402


def test_contract_parser_returns_exact_scenario_ids_and_expected_states() -> None:
    scenarios = read_contract_scenarios()

    assert tuple(scenario.scenario_id for scenario in scenarios) == (
        EXPECTED_SCENARIO_IDS
    )
    assert all(scenario.setup for scenario in scenarios)
    assert all(scenario.expected_persisted_state for scenario in scenarios)


def test_contract_parser_rejects_missing_duplicate_or_unrecognized_ids(
    tmp_path: Path,
) -> None:
    contract = Path(__file__).with_name("VALIDATION-CONTRACT.md").read_text(
        encoding="utf-8"
    )
    altered = contract.replace("| S17 |", "| S16 |", 1)
    path = tmp_path / "contract.md"
    path.write_text(altered, encoding="utf-8")

    with pytest.raises(ValueError, match="exactly S01-S17"):
        read_contract_scenarios(path)


@pytest.mark.parametrize(
    ("target", "scenario_ids"),
    [
        ("results", EXPECTED_SCENARIO_IDS[:-1]),
        ("results", (*EXPECTED_SCENARIO_IDS[:-1], "S16")),
        ("results", (*EXPECTED_SCENARIO_IDS[:-1], "S18")),
        ("matrix", EXPECTED_SCENARIO_IDS[:-1]),
        ("matrix", (*EXPECTED_SCENARIO_IDS[:-1], "S16")),
        ("matrix", (*EXPECTED_SCENARIO_IDS[:-1], "S18")),
    ],
    ids=(
        "results-missing",
        "results-duplicated",
        "results-not-in-contract",
        "matrix-missing",
        "matrix-duplicated",
        "matrix-not-in-contract",
    ),
)
def test_evidence_checker_rejects_invalid_result_scenario_ids(
    tmp_path: Path, target: str, scenario_ids: tuple[str, ...]
) -> None:
    result_path = tmp_path / "results.json"
    matrix_path = tmp_path / "scenario-matrix.csv"
    result_ids = scenario_ids if target == "results" else EXPECTED_SCENARIO_IDS
    matrix_ids = scenario_ids if target == "matrix" else EXPECTED_SCENARIO_IDS
    result_path.write_text(
        json.dumps(
            {
                "scenarios": [
                    {"scenario_id": item, "status": "passed"}
                    for item in result_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    with matrix_path.open("w", encoding="utf-8", newline="") as matrix_file:
        writer = csv.DictWriter(
            matrix_file, fieldnames=("scenario_id", "status")
        )
        writer.writeheader()
        writer.writerows(
            {"scenario_id": item, "status": "passed"} for item in matrix_ids
        )

    with pytest.raises(
        ValueError,
        match=(
            "results.json must contain each contract ID"
            if target == "results"
            else "scenario-matrix.csv must contain each contract ID"
        ),
    ):
        validate_scenario_ids(result_path, matrix_path, EXPECTED_SCENARIO_IDS)
