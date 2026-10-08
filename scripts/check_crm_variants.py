"""Regenerate CRM variant evidence and compare deterministic artifacts."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = (
    ROOT / "prototypes" / "crm_operational_copilot" / "variants" / "run_experiment.py"
)
ARTIFACTS = ROOT / "artifacts" / "crm-variants"
DETERMINISTIC_FILES = ("variants-matrix.csv", "variants-results.json")


def _tail(output: str, lines: int = 30) -> str:
    return "\n".join(output.splitlines()[-lines:])


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="crm-variants-check-") as directory:
            generated = Path(directory)
            result = subprocess.run(
                [sys.executable, str(HARNESS), "--output-dir", str(generated)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            print("harness_tail:")
            print(_tail(result.stdout + result.stderr))
            if result.returncode != 0:
                print(f"harness_return_code={result.returncode}")
                return 1

            results = json.loads(
                (generated / "variants-results.json").read_text(encoding="utf-8")
            )
            if results["claim_races"]["broken-control"]["accepted_claims"] <= 1:
                raise ValueError(
                    "broken-control N=50 race did not produce multiple accepted claims"
                )
            with (generated / "variants-matrix.csv").open(
                encoding="utf-8", newline=""
            ) as matrix_file:
                rows = list(csv.DictReader(matrix_file))
            if len(rows) != 85:
                raise ValueError(f"expected 85 variant/S-ID rows, found {len(rows)}")
            failures = [row for row in rows if row["status"] == "fail"]
            if len(failures) != 1 or (
                failures[0]["variant"], failures[0]["scenario_id"]
            ) != ("broken-control", "S09"):
                raise ValueError(
                    "expected only the broken-control S09 claim invariant to fail"
                )

            for filename in DETERMINISTIC_FILES:
                committed = ARTIFACTS / filename
                regenerated = generated / filename
                if not committed.is_file():
                    raise ValueError(f"committed output is missing: {committed}")
                if committed.read_bytes() != regenerated.read_bytes():
                    raise ValueError(f"regenerated output differs from {committed}")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"CRM variant check failed: {error}")
        return 1

    print(
        "CRM variant evidence matches deterministic regeneration: "
        f"{', '.join(DETERMINISTIC_FILES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())