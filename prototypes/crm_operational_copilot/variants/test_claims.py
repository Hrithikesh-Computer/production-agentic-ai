from __future__ import annotations

from pathlib import Path

from variants.race import run_n50_claim_race


def test_n50_claim_race_passes_for_atomic_claim_variants(tmp_path: Path) -> None:
    for variant in ("baseline", "store-layout-b", "claim-b"):
        outcome = run_n50_claim_race(variant, tmp_path / f"{variant}.sqlite")
        assert outcome["accepted_claims"] == 1
        assert outcome["single_winner_assertion"]


def test_n50_single_winner_assertion_fails_on_broken_control(tmp_path: Path) -> None:
    outcome = run_n50_claim_race("broken-control", tmp_path / "broken.sqlite")
    assert outcome["accepted_claims"] > 1
    assert not outcome["single_winner_assertion"]