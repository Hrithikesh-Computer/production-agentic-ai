# Review Evidence Log: 2026-10-04

This is the verification and provenance log supporting [Repository Evaluation: Second Pass](repo-evaluation-v2.md). The evaluation keeps the findings and remaining decisions; this file retains the detailed checks and historical cleanup audit.

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
| `review-2026-10-04` | Final review tag; see this tag's target for the report/evidence cleanup, validation scripts, Python matrix, and CI workflow changes. |

The original branch snapshot was not clean; findings about first inspection are explicitly labeled as historical. It had 118 tests before the review-added tests and 127 after review edits.

## Clean-Commit Checks

The following commits were each checked in a fresh detached worktree. At each, `python -m pytest -q` reported 127 passing tests, Ruff reported all checks passed, and `python -m mypy .` reported no issues in 25 source files:

- `ae9150c`
- `c5237f4`
- `23367a3`
- `2de763f`
- Final commit referenced by `review-2026-10-04`

At `a1a71c8`, tests and Ruff passed and the focused CI mypy command reported no issues in 14 source files. Whole-repository mypy failed because `benchmarks/response-delivery/benchmark.py` and `benchmarks/context-lifecycle/benchmark.py` both mapped to module name `benchmark`. Removing the obsolete context benchmark in `ae9150c` resolved the collision.

## Python Runtime and Imports

- First-inspection environment: Windows, CPython 3.14.6; 118 tests before review additions.
- Post-review working-tree suite: 127 tests.
- Isolated CPython 3.10.20 at `23367a3`, `2de763f`, and the final review commit: 127 tests passed, Ruff passed, and whole-repository mypy reported no issues in 25 files.
- The first module-path check used the shared editable venv and was not isolated: pytest collection resolved `authority_policy` and `ndjson_stream` from the primary checkout.
- The corrected check used `uv --no-project` with `PYTHONPATH` unset in a detached checkout. Pytest collection resolved `authority_policy`, `ndjson_stream`, and `approval_workflow` from files inside that checkout.
- Python 3.10 was provisioned with `uv`; the initial check used isolated tool dependencies. The final CI-equivalent rerun uses the project `.[dev]` dependencies and is recorded below after completion.

## Link Audit By Commit

The checker scans tracked Markdown links, excludes inline/fenced code examples and external URL schemes, and accepts a directory target when the commit tracks files beneath it.

| Commit | Broken relative links | Main causes |
|---|---:|---|
| `a1a71c8` | 5 | Archive targets were not yet tracked; REPO-MAP referenced absent archive README files. |
| `0de0c92` | 5 | Same as `a1a71c8`. |
| `ae9150c` | 7 | Prior issues plus README links to removed context-lifecycle and authority-conformance benchmark directories. |
| `c5237f4` | 7 | Prior benchmark links plus stale EMR paths after archive moves. |
| `23367a3` | 3 | REPO-MAP linked to three archive README files that did not exist. |
| Final `review-2026-10-04` target | 0 | REPO-MAP now links to tracked archive directories. |

## Benchmark README And CSV

The response-delivery README cites 300 KB medians/maxima: full build 1.69/2.92 ms, chunked build 22.70/28.77 ms, and reassembly 5.87/8.27 ms.

- At `a1a71c8` and `0de0c92`, the CSV still had the older synthetic delivery-time schema, so those claims were not verifiable from the CSV.
- At `ae9150c`, `c5237f4`, `23367a3`, and the final tag, the refreshed CSV has the build/reassembly columns and the 300 KB values round to the README figures above.

## Mutation And Coverage Evidence

The custom `mutation_check.py` uses temporary copies. It killed 36/36 applicable authority mutants (one was not applicable because its source pattern had changed), 14/14 NDJSON mutants, and 15/15 workflow mutants. With the two new field-guard tests deselected, 13/15 workflow mutants were killed and both allowlist mutants survived; with those tests present, both mutants were killed. Tests and custom mutants were developed in the same round, so this is sensitivity evidence, not independent mutation evidence.

Full-suite branch coverage for the selected modules:

| File | Statements | Missed | Branches | Partial branches | Coverage |
|---|---:|---:|---:|---:|---:|
| `authority_policy.py` | 96 | 0 | 50 | 0 | 100% |
| `approval_workflow.py` | 231 | 41 | 76 | 20 | 80% |

Independent mutation testing (for example, cosmic-ray), CI mutation/coverage steps, concurrency tests, and production identity/persistence guarantees remain open.

## Browser Evidence Provenance

The legacy three-mode standalone, clean four-mode standalone, and Electron four-mode artifacts are distinct. The clean standalone has 384 request timings, a detected 121 ms Long Task control, a harness SHA-256, and a same-process compression sweep. Electron has 384 timings but its Long Task control was not detected and its saved artifact has no timestamp or harness hash. Both four-mode artifacts have matching payload sizes. Client decompression/rendering CPU and representative CRM payload behavior remain unmeasured. Detailed tables are in [browser-matrix-evidence.md](../benchmarks/response-delivery/browser-matrix-evidence.md).

## Hosted CI

The workflow now runs on every branch push and on pull requests to `main`. Its Python matrix is 3.10 and 3.14; it runs the focused and repository-wide mypy checks plus the tracked-Markdown-link and response-delivery README/CSV guards. The final clean checkout is also validated locally under CPython 3.10.20 using `uv run --with-editable ".[dev]"`; record the hosted Actions URL/result here after pushing. Local validation does not substitute for the Ubuntu runner.
