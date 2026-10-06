from __future__ import annotations

from pathlib import Path

import pytest
from validation_harness import EXPECTED_SCENARIO_IDS, read_contract_scenarios


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
