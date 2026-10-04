"""Enforce per-module line and branch coverage thresholds."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

THRESHOLDS: dict[str, tuple[float, float]] = {
    "envelope.py": (95.0, 90.0),
    "reassembler.py": (87.0, 78.0),
    "ndjson_stream.py": (95.0, 95.0),
}


def main() -> int:
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("coverage.json")
    report: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, float]] = {}
    for path, file_report in report.get("files", {}).items():
        name = Path(path).name
        if name in THRESHOLDS:
            summary = file_report["summary"]
            rows[name] = {
                "line": float(summary["percent_covered"]),
                "branch": float(summary["percent_branches_covered"]),
            }

    failed = False
    print(
        f"{'file':<20} {'line':>9} {'required':>10} "
        f"{'branch':>9} {'required':>10} result"
    )
    for name, (required_line, required_branch) in THRESHOLDS.items():
        measured = rows.get(name)
        if measured is None:
            print(
                f"{name:<20} {'MISSING':>9} {required_line:>9.1f}% "
                f"{'MISSING':>9} {required_branch:>9.1f}% FAIL"
            )
            failed = True
            continue
        passed = (
            measured["line"] >= required_line
            and measured["branch"] >= required_branch
        )
        print(
            f"{name:<20} {measured['line']:>8.2f}% {required_line:>9.1f}% "
            f"{measured['branch']:>8.2f}% {required_branch:>9.1f}% "
            f"{'PASS' if passed else 'FAIL'}"
        )
        failed = failed or not passed
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
