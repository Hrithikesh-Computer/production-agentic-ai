"""Validate unique campaign/fault keys in the approval-audit evidence CSV."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "artifacts" / "fault-injection-approval-audit.csv"
KEY_FIELDS = ("campaign_id", "variant", "fault_point")


def unique_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    seen: dict[tuple[str, str, str], dict[str, str]] = {}
    result: list[dict[str, str]] = []
    duplicates = 0
    for row in rows:
        campaign_id = row.get("campaign_id", "")
        variant = row.get("variant", "")
        fault_point = row.get("fault_point", "")
        key = (campaign_id, variant, fault_point)
        if not campaign_id or not variant or not fault_point:
            raise ValueError(f"row is missing a campaign key: {key!r}")
        previous = seen.get(key)
        if previous is None:
            seen[key] = row
            result.append(row)
        elif previous == row:
            duplicates += 1
        else:
            raise ValueError(f"conflicting rows share campaign key {key!r}")
    return result, duplicates


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fields = list(reader.fieldnames or [])
        if not set(KEY_FIELDS).issubset(fields):
            raise ValueError(f"CSV must contain key columns {KEY_FIELDS!r}")
        return fields, [dict(row) for row in reader]


def _write_atomically(
    path: Path, fields: list[str], rows: list[dict[str, str]]
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--deduplicate-exact",
        action="store_true",
        help="remove exact duplicate campaign rows; conflicting duplicates are refused",
    )
    args = parser.parse_args()

    try:
        fields, rows = _read(args.path)
        unique, duplicate_count = unique_rows(rows)
        if duplicate_count and not args.deduplicate_exact:
            raise ValueError(
                f"found {duplicate_count} exact duplicate campaign rows; "
                "rerun with --deduplicate-exact to remove only exact copies"
            )
        if duplicate_count:
            _write_atomically(args.path, fields, unique)
        print(
            f"fault audit rows={len(unique)} exact_duplicates_removed="
            f"{duplicate_count} path={args.path}"
        )
    except (OSError, ValueError, csv.Error) as error:
        print(f"fault-injection approval-audit check failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())