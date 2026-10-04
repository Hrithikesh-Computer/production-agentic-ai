# Review Evidence Log: 2026-10-04

This is the verification and provenance log supporting [Repository Evaluation: Second Pass](repo-evaluation-v2.md). The report keeps the findings and remaining decisions; this file retains detailed checks and historical cleanup evidence.

## Commit Timeline

| Commit | Change |
|---|---|
| `00d7b51` | Added the evaluation report, its `.gitignore` exception, and reopened ADR-001. |
| `a1a71c8` | Published browser evidence, harness/runner, and supporting implementation/tests. |
| `0de0c92` | Corrected compression-level optima and sensitivity analysis. |
| `ae9150c` | Removed colliding benchmark fixtures, refreshed local response-delivery measurements, and fixed the duplicate-module whole-repo mypy error. |
| `c5237f4` | Archived legacy design and security documents. |
| `23367a3` | Reconciled README, EVIDENCE, REPO-MAP, ROADMAP, and research notes. |
| `2de763f` | Added whole-repository mypy to CI. |
| `9c7e480` | Added the Python 3.10/3.14 CI matrix and permanent Markdown-link and benchmark-figure guards. Tagged `review-2026-10-04`. |

The original branch snapshot was not clean; findings about first inspection are explicitly historical. It had 118 tests before review-added tests and 127 after review edits.

## Commit-Level Checks

| Commit | Tests | Ruff | Mypy | Link audit |
|---|---|---|---|---|
| `a1a71c8` | Passed | Passed | Focused CI targets: 14 files; whole-repository check failed on duplicate `benchmark` module names | 5 broken links |
| `0de0c92` | Detailed test/lint result not recorded here | Not recorded here | Not recorded here | 5 broken links |
| `ae9150c` | 127 passed | Passed | Whole repository: 25 files, no issues | 7 broken links |
| `c5237f4` | 127 passed | Passed | Whole repository: 25 files, no issues | 7 broken links |
| `23367a3` | 127 passed on CPython 3.10.20 | Passed | Whole repository: 25 files, no issues | 3 broken links |
| `2de763f` | 127 passed on CPython 3.10.20 | Passed | Whole repository: 25 files, no issues | Link audit not recorded per commit |
| `review-2026-10-04` (`9c7e480`) | 127 passed on CPython 3.10.20 | Passed | Whole repository: 27 files, no issues | 0 broken links |

Ruff passed at `a1a71c8`, `ae9150c`, `c5237f4`, `23367a3`, `2de763f`, and the final tagged snapshot. The `0de0c92` Ruff result is not asserted because it was not recorded in the audit.

## CI-Equivalent Final Run

At the final source snapshot, the project development dependencies were resolved in an isolated temporary uv environment with:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$env:TEMP\production-agentic-ai-py310-review"
uv run --python 3.10 --with-editable ".[dev]" python -m pytest -q
uv run --python 3.10 --with-editable ".[dev]" python -m ruff check .
uv run --python 3.10 --with-editable ".[dev]" python -m mypy .
uv run --python 3.10 --with-editable ".[dev]" python scripts/check_markdown_links.py
uv run --python 3.10 --with-editable ".[dev]" python scripts/check_response_delivery_evidence.py
uv run --python 3.10 --with-editable ".[dev]" python 04-reference-implementation/adaptive-response-filter/demo.py
```

Results: 127 tests passed; Ruff passed; whole-repository mypy reported no issues in 27 source files; both evidence guards passed; the reference demo completed. The focused CI mypy target also passed with no issues in 14 files. The `.[dev]` constraints are minimum versions rather than a lockfile, so this reproduces CI's dependency declaration, not necessarily the exact versions installed by GitHub Actions. The first attempt targeted the workspace `.venv` and was blocked by Windows access; the successful retry used the isolated temporary environment above.

## Python Runtime And Imports

- First-inspection environment: Windows, CPython 3.14.6; 118 tests before review additions.
- The first module-path check used the shared editable venv and was not isolated: pytest collection resolved `authority_policy` and `ndjson_stream` from the primary checkout.
- The corrected check used `uv --no-project` with `PYTHONPATH` unset in a detached checkout. Pytest collection resolved `authority_policy`, `ndjson_stream`, and `approval_workflow` from files inside that checkout.
- CPython 3.10.20 was used for checks at `23367a3`, `2de763f`, and the final tagged snapshot. The final run used `uv run --python 3.10 --with-editable ".[dev]"` so pytest, Ruff, and mypy came from the project's declared development dependency set. Its exact command results are recorded below.

## Link Audit By Commit

The checker scans tracked Markdown links, excludes inline/fenced code examples and external URL schemes, and accepts a directory target when the commit tracks files beneath it.

| Commit | Broken relative links | Main causes |
|---|---:|---|
| `a1a71c8` | 5 | Archive targets were not yet tracked; REPO-MAP referenced absent archive README files. |
| `0de0c92` | 5 | Same as `a1a71c8`. |
| `ae9150c` | 7 | Prior issues plus README links to removed context-lifecycle and authority-conformance benchmark directories. |
| `c5237f4` | 7 | Prior benchmark links plus stale EMR paths after archive moves. |
| `23367a3` | 3 | REPO-MAP linked to three archive README files that did not exist. |
| `review-2026-10-04` (`9c7e480`) | 0 | REPO-MAP now links to tracked archive directories. |

## Benchmark README And CSV

The response-delivery README cites 300 KB medians/maxima: full build 1.69/2.92 ms, chunked build 22.70/28.77 ms, and reassembly 5.87/8.27 ms.

- At `a1a71c8` and `0de0c92`, the CSV still had the older synthetic delivery-time schema, so those claims were not verifiable from the CSV.
- At `ae9150c`, `c5237f4`, `23367a3`, `2de763f`, and the final tag, the refreshed CSV has the build/reassembly columns and the 300 KB values round to the README figures above.
- `scripts/check_response_delivery_evidence.py` now enforces this comparison in CI.

## Mutation And Coverage Evidence

The custom `mutation_check.py` uses temporary copies. It killed 36/36 applicable authority mutants (one was not applicable because its source pattern had changed), 14/14 NDJSON mutants, and 15/15 workflow mutants. With the two new field-guard tests deselected, 13/15 workflow mutants were killed and both allowlist mutants survived; with those tests present, both mutants were killed. Tests and custom mutants were developed in the same round, so this is sensitivity evidence, not independent mutation evidence.

Full-suite branch coverage for the selected modules:

| File | Statements | Missed | Branches | Partial branches | Coverage |
|---|---:|---:|---:|---:|---:|
| `authority_policy.py` | 96 | 0 | 50 | 0 | 100% |
| `approval_workflow.py` | 231 | 41 | 76 | 20 | 80% |

Independent mutation testing (for example, cosmic-ray), a CI coverage step, concurrency tests, and production identity/persistence guarantees remain open. CI already has the Python 3.10/3.14 matrix, whole-repository mypy, tracked-Markdown-link guard, and README/CSV figure guard.

## Browser Evidence Provenance

The legacy three-mode standalone, clean four-mode standalone, and Electron four-mode artifacts are distinct. The clean standalone has 384 request timings, a detected 121 ms Long Task control, a harness SHA-256, and a same-process compression sweep. Electron has 384 timings but its Long Task control was not detected and its saved artifact has no timestamp or harness hash. Both four-mode artifacts have matching payload sizes. Client decompression/rendering CPU and representative CRM payload behavior remain unmeasured. Detailed tables are in [browser-matrix-evidence.md](../benchmarks/response-delivery/browser-matrix-evidence.md).

## Hosted CI

The workflow runs on every branch push and on pull requests to `main`. Its Python matrix is 3.10 and 3.14; it runs Ruff, the test suite, focused and repository-wide mypy, the tracked-Markdown-link guard, and the response-delivery README/CSV guard. The final local CPython 3.10.20 run uses the project `.[dev]` dependency set; exact results are recorded below. Hosted Ubuntu has not run this workflow because the branch has not been pushed. Record the Actions URL/result here after pushing; local validation does not substitute for the hosted runner.
