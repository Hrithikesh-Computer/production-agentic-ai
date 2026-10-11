"""Enforce per-module line and branch coverage thresholds."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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
    timestamp_text = report.get("meta", {}).get("timestamp")
    try:
        generated_at = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
    except (AttributeError, TypeError, ValueError):
        print(f"coverage report has missing or invalid timestamp: {report_path}")
        return 1

    newer_sources = []
    for relative_path in report.get("files", {}):
        source_path = Path(relative_path)
        if not source_path.is_absolute():
            source_path = report_path.resolve().parent / source_path
        if source_path.exists():
            modified_at = datetime.fromtimestamp(
                source_path.stat().st_mtime, tz=timezone.utc
            )
            if modified_at > generated_at:
                newer_sources.append(source_path)
    if newer_sources:
        print(
            "coverage report is stale; source files changed after its timestamp:"
        )
        for source_path in newer_sources:
            print(f"  {source_path}")
        return 1

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
