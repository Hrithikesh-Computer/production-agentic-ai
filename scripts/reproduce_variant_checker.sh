#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
    PYTHON_BIN="$PYTHON"
elif [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON_BIN="$ROOT/.venv/Scripts/python.exe"
else
    PYTHON_BIN="$ROOT/.venv/bin/python"
fi
CHECKER="$ROOT/scripts/check_crm_variants.py"
HARNESS="$ROOT/prototypes/crm_operational_copilot/variants/run_experiment.py"
ARTIFACTS="$ROOT/artifacts/crm-variants"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

printf 'interpreter=%s\n' "$PYTHON_BIN"
printf 'working_directory=%s\n' "$ROOT"
cd "$ROOT"

if [[ ! -x "$PYTHON_BIN" ]]; then
    printf 'ERROR: configured interpreter is missing or not executable: %s\n' "$PYTHON_BIN" >&2
    exit 127
fi

CHECKER_STDOUT="$TMP_DIR/checker.stdout"
CHECKER_STDERR="$TMP_DIR/checker.stderr"
set +e
"$PYTHON_BIN" "$CHECKER" >"$CHECKER_STDOUT" 2>"$CHECKER_STDERR"
CHECKER_STATUS=$?
set -e
printf '%s\n' '--- checker stdout ---'
cat "$CHECKER_STDOUT"
printf '%s\n' '--- checker stderr ---' >&2
cat "$CHECKER_STDERR" >&2
printf 'checker_exit_code=%s\n' "$CHECKER_STATUS"

HARNESS_STDOUT="$TMP_DIR/harness.stdout"
HARNESS_STDERR="$TMP_DIR/harness.stderr"
set +e
"$PYTHON_BIN" "$HARNESS" --output-dir "$TMP_DIR/generated" \
    >"$HARNESS_STDOUT" 2>"$HARNESS_STDERR"
HARNESS_STATUS=$?
set -e
printf '%s\n' '--- harness stdout ---'
cat "$HARNESS_STDOUT"
printf '%s\n' '--- harness stderr ---' >&2
cat "$HARNESS_STDERR" >&2
printf 'harness_exit_code=%s\n' "$HARNESS_STATUS"

DIFF_STATUS=0
for filename in variants-matrix.csv variants-results.json variants-environment.json; do
    generated="$TMP_DIR/generated/$filename"
    committed="$ARTIFACTS/$filename"
    if [[ ! -f "$generated" || ! -f "$committed" ]]; then
        printf 'MISSING artifact: generated=%s committed=%s\n' "$generated" "$committed" >&2
        DIFF_STATUS=2
        continue
    fi
    if cmp -s "$committed" "$generated"; then
        printf 'BYTE-FOR-BYTE EQUAL: %s\n' "$filename"
    else
        printf 'BYTE DRIFT: %s\n' "$filename" >&2
        if diff -u --strip-trailing-cr "$committed" "$generated"; then
            printf 'CRLF-normalized unified diff: no content differences for %s\n' "$filename"
            DIFF_STATUS=1
        else
            normalized_status=$?
            if [[ $normalized_status -eq 1 ]]; then
                printf 'CONTENT DRIFT: %s (unified diff above)\n' "$filename" >&2
                DIFF_STATUS=1
            else
                printf 'normalized diff failed for %s with exit code %s\n' \
                    "$filename" "$normalized_status" >&2
                DIFF_STATUS=2
            fi
        fi
    fi
done

printf 'artifact_diff_exit_code=%s\n' "$DIFF_STATUS"
if [[ $CHECKER_STATUS -ne 0 ]]; then
    exit "$CHECKER_STATUS"
fi
if [[ $HARNESS_STATUS -ne 0 ]]; then
    exit "$HARNESS_STATUS"
fi
exit "$DIFF_STATUS"