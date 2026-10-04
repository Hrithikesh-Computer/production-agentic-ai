"""Verify response-delivery README figures against the committed results CSV."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

CITATION = re.compile(
    r"full-policy build median/max was ([0-9.]+)/([0-9.]+) ms\. "
    r"Chunked-envelope build was ([0-9.]+)/([0-9.]+) ms, and "
    r"authenticated reassembly was ([0-9.]+)/([0-9.]+) ms"
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    benchmark_dir = root / "benchmarks" / "response-delivery"
    readme = (benchmark_dir / "README.md").read_text(encoding="utf-8")
    csv_path = benchmark_dir / "results.csv"
    with csv_path.open(encoding="utf-8", newline="") as result_file:
        rows = list(csv.DictReader(result_file))

    citation = CITATION.search(readme)
    if citation is None:
        print("Could not find the documented 300 KB benchmark figures in README.md.")
        return 1

    full = next(
        (
            row
            for row in rows
            if row.get("payload_size") in {"300000", "300007"}
            and row.get("mode") == "full"
        ),
        None,
    )
    chunked = next(
        (
            row
            for row in rows
            if row.get("payload_size") in {"300000", "300007"}
            and row.get("mode") == "chunked"
        ),
        None,
    )
    required_full = {"median_build_ms", "max_build_ms"}
    required_chunked = {
        "median_build_ms",
        "max_build_ms",
        "median_reassembly_ms",
        "max_reassembly_ms",
    }
    if (
        full is None
        or chunked is None
        or not required_full.issubset(full)
        or not required_chunked.issubset(chunked)
    ):
        print("The CSV does not contain the 300 KB build/reassembly result fields.")
        return 1

    actual = [
        float(full["median_build_ms"] or ""),
        float(full["max_build_ms"] or ""),
        float(chunked["median_build_ms"] or ""),
        float(chunked["max_build_ms"] or ""),
        float(chunked["median_reassembly_ms"] or ""),
        float(chunked["max_reassembly_ms"] or ""),
    ]
    cited = [float(value) for value in citation.groups()]
    if any(
        f"{value:.2f}" != f"{reported:.2f}"
        for value, reported in zip(actual, cited)
    ):
        print(f"README figures {cited} do not match CSV values {actual}.")
        return 1

    print("README 300 KB build/reassembly figures match results.csv to two decimals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
