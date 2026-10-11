from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest
import validation_harness
from validation_harness import EXPECTED_SCENARIO_IDS, read_contract_scenarios

_CHECKER_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "check_crm_validation_evidence.py"
)
_SPEC = importlib.util.spec_from_file_location("crm_evidence_checker", _CHECKER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CHECKER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECKER)
validate_environment = _CHECKER.validate_environment
validate_scenario_ids = _CHECKER.validate_scenario_ids


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


def test_source_snapshot_digest_changes_when_a_validation_input_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.py"
    source.write_text("first", encoding="utf-8")
    monkeypatch.setattr(validation_harness, "ROOT", tmp_path)
    monkeypatch.setattr(validation_harness, "VALIDATION_INPUTS", ("input.py",))
    first_digest = validation_harness.source_snapshot_sha256()

    source.write_text("second", encoding="utf-8")

    assert validation_harness.source_snapshot_sha256() != first_digest


def test_environment_checker_rejects_stale_source_snapshot(tmp_path: Path) -> None:
    environment = {
        "commit": "0" * 40,
        "python_version": "3.14.6",
        "source_snapshot_sha256": "0" * 64,
        "started_at_utc": "2026-10-09T00:00:00Z",
        "completed_at_utc": "2026-10-09T00:00:01Z",
    }
    path = tmp_path / "environment.json"
    path.write_text(json.dumps(environment), encoding="utf-8")

    with pytest.raises(ValueError, match="source snapshot does not match"):
        validate_environment(path)


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
