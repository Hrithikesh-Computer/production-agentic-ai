"""Write LF-normalized copies of committed CRM variant artifacts."""

from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path

ARTIFACT_NAMES = (
    "variants-matrix.csv",
    "variants-results.json",
    "variants-environment.json",
)


def _normalize_csv(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8", newline="") as source_file:
        rows = list(csv.reader(source_file))
    with destination.open("w", encoding="utf-8", newline="\n") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerows(rows)


def _normalize_text(source: Path, destination: Path) -> None:
    text = source.read_bytes().decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    with destination.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(normalized)


def _line_counts(data: bytes) -> tuple[int, int]:
    crlf_count = data.count(b"\r\n")
    lf_count = data.count(b"\n") - crlf_count
    return crlf_count, lf_count


def normalize(source_dir: Path, output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_identical = True
    print(f"source_directory={source_dir.resolve()}")
    print(f"output_directory={output_dir.resolve()}")
    for name in ARTIFACT_NAMES:
        source = source_dir / name
        destination = output_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"required artifact not found: {source}")
        original = source.read_bytes()
        if name.endswith(".csv"):
            _normalize_csv(source, destination)
        else:
            _normalize_text(source, destination)
        normalized = destination.read_bytes()
        original_crlf, original_lf = _line_counts(original)
        new_crlf, new_lf = _line_counts(normalized)
        changed = original != normalized
        all_identical &= not changed
        print(
            f"{name}: original_bytes={len(original)} new_bytes={len(normalized)} "
            f"original_crlf={original_crlf} original_lf={original_lf} "
            f"new_crlf={new_crlf} new_lf={new_lf} changed={str(changed).lower()}"
        )
    return all_identical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "artifacts" / "crm-variants",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    normalize(args.source_dir, args.output_dir)
    with tempfile.TemporaryDirectory(prefix="variant-artifact-idempotency-") as temp:
        second_output = Path(temp)
        for name in ARTIFACT_NAMES:
            first = args.output_dir / name
            if name.endswith(".csv"):
                _normalize_csv(first, second_output / name)
            else:
                _normalize_text(first, second_output / name)
            if first.read_bytes() != (second_output / name).read_bytes():
                print(f"IDEMPOTENCY FAILURE: {name}")
                return 1
        print("idempotent_second_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())