# Browser Matrix Evidence

This note contains the detailed response-delivery tables supporting the repository evaluation and ADR-001. Results are synthetic, generated over paced loopback, and are not production or customer measurements. The benchmark method and limitations are described in the [benchmark README](README.md); the harness is [browser_benchmark.py](browser_benchmark.py).

## Artifact identities

| Artifact | Browser/runtime | Modes | Evidence notes |
|---|---|---|---|
| [Legacy standalone](browser_results.json) | Standalone HeadlessChrome | `full`, `gzip_full`, `framed_http` | Legacy text-like body is 306,891 B. Its Long Task control was detected. |
| [Clean four-mode standalone](browser_results_standalone_compression.json) | Standalone HeadlessChrome 154 | `full`, `gzip_full`, `framed_http`, `gzip_framed` | Fresh-profile CDP run; 384 request timings; Long Task control detected at 121 ms; harness SHA-256 `b9fcc9019f2b099eeb1a0d7e2df6551b274b60ca8b1836d3092ad7363164fce7`; timing and compression sweep share server PID `14644`. |
| [Electron four-mode](browser_results_compression.json) | Electron-embedded Chrome 148 / Electron 42.10 | `full`, `gzip_full`, `framed_http`, `gzip_framed` | 384 request timings; Long Task control was not detected; artifact has no run timestamp or harness hash. |

Both four-mode artifacts have matching payload sizes. The structured 300,007-byte payload is common to all three artifacts. The clean standalone and Electron text-like payloads are both 443,577 B; the legacy text-like payload is 306,891 B. Gzip bodies are precomputed before per-request timing, so request timings exclude server compression CPU. NDJSON body byte counts exclude HTTP chunk-transfer delimiters.

The clean standalone runner awaits `window.__experimentComplete` and refuses to overwrite its result artifact. Its compression-level sweep and browser timings share a process and saved harness hash. The 100-repetition CPU sweep is process CPU while compressing both full and framed bodies once per repetition; it is paired server-side cost, not per-mode cost. Client decompression and rendering CPU are not measured.

## Legacy standalone timings

Saved P50 values for the nominal 300 KB target. First-visible order is `full / gzip / framed`; completion order is `gzip / framed`.

| Payload / gzip-body / NDJSON-body bytes | Pace (MB/s) | First-visible P50 (ms) | Completion P50 (ms) |
|---|---:|---:|---:|
| Structured: 300,007 / 23,735 / 355,158 B | 0.512 | 647.3 / 107.9 / 76.1 | 107.9 / 745.3 |
| Structured | 2 | 213.8 / 73.6 / 54.1 | 73.6 / 252.8 |
| Structured | 10 | 90.7 / 63.3 / 51.5 | 63.3 / 177.6 |
| Structured | 50 | 66.5 / 61.4 / 46.1 | 61.4 / 75.8 |
| Text-like: 306,891 / 8,489 / 318,314 B | 0.512 | 646.8 / 65.3 / 74.5 | 65.3 / 667.0 |
| Text-like | 2 | 200.6 / 52.5 / 52.0 | 52.5 / 208.0 |
| Text-like | 10 | 78.3 / 48.4 / 45.6 | 48.4 / 85.1 |
| Text-like | 50 | 54.7 / 48.2 / 45.7 | 48.2 / 54.5 |

## Electron four-mode timings

Saved P50 values for the nominal 300 KB target. First-visible and completion order is `full / gzip full / NDJSON / gzip NDJSON`.

| Payload bytes (full / gzip / NDJSON / gzip NDJSON) | Pace (MB/s) | First-visible P50 (ms) | Completion P50 (ms) |
|---|---:|---:|---:|
| Structured: 300,007 / 23,735 / 355,158 / 24,636 B | 0.512 | 647.8 / 111.3 / 78.3 / 86.3 | 647.8 / 111.3 / 747.3 / 125.2 |
| Structured | 2 | 216.2 / 75.4 / 75.2 / 55.7 | 216.2 / 75.4 / 256.8 / 91.4 |
| Structured | 10 | 93.5 / 75.1 / 47.5 / 48.1 | 93.5 / 75.1 / 123.5 / 76.4 |
| Structured | 50 | 75.2 / 75.2 / 48.1 / 64.1 | 75.2 / 75.2 / 84.0 / 78.0 |
| Text-like: 443,577 / 70,898 / 455,000 / 71,302 B | 0.512 | 916.9 / 188.7 / 77.3 / 88.0 | 916.9 / 188.7 / 934.9 / 185.7 |
| Text-like | 2 | 272.5 / 85.2 / 75.0 / 53.1 | 272.5 / 85.2 / 272.9 / 93.1 |
| Text-like | 10 | 99.8 / 74.9 / 47.3 / 49.8 | 99.8 / 74.9 / 95.5 / 59.1 |
| Text-like | 50 | 74.6 / 74.9 / 46.5 / 49.5 | 74.6 / 74.9 / 72.2 / 53.1 |

## Legacy-to-Electron comparison

For the common structured 300,007-byte payload, each cell shows legacy standalone / Electron P50 in milliseconds, with Electron-minus-legacy in parentheses.

| Pace (MB/s) | First: full | First: gzip | First: NDJSON | Completion: full | Completion: gzip | Completion: NDJSON |
|---:|---:|---:|---:|---:|---:|---:|
| 0.512 | 647.3 / 647.8 (+0.5) | 107.9 / 111.3 (+3.4) | 76.1 / 78.3 (+2.2) | 647.3 / 647.8 (+0.5) | 107.9 / 111.3 (+3.4) | 745.3 / 747.3 (+2.0) |
| 2 | 213.8 / 216.2 (+2.4) | 73.6 / 75.4 (+1.8) | 54.1 / 75.2 (+21.1) | 213.8 / 216.2 (+2.4) | 73.6 / 75.4 (+1.8) | 252.8 / 256.8 (+4.0) |
| 10 | 90.7 / 93.5 (+2.8) | 63.3 / 75.1 (+11.8) | 51.5 / 47.5 (-4.0) | 90.7 / 93.5 (+2.8) | 63.3 / 75.1 (+11.8) | 177.6 / 123.5 (-54.1) |
| 50 | 66.5 / 75.2 (+8.7) | 61.4 / 75.2 (+13.8) | 46.1 / 48.1 (+2.0) | 66.5 / 75.2 (+8.7) | 61.4 / 75.2 (+13.8) | 75.8 / 84.0 (+8.2) |

## Clean four-mode standalone timings

Saved P50 values for the nominal 300 KB target. First-visible and completion order is `full / gzip full / NDJSON / gzip NDJSON`.

| Payload bytes (full / gzip / NDJSON / gzip NDJSON) | Pace (MB/s) | First-visible P50 (ms) | Completion P50 (ms) |
|---|---:|---:|---:|
| Structured: 300,007 / 23,735 / 355,158 / 24,636 B | 0.512 | 648.3 / 110.2 / 76.8 / 79.3 | 648.3 / 110.2 / 745.6 / 150.4 |
| Structured | 2 | 210.7 / 72.3 / 52.9 / 55.5 | 210.7 / 72.3 / 251.9 / 101.3 |
| Structured | 10 | 92.7 / 63.3 / 47.8 / 50.8 | 92.7 / 63.3 / 182.1 / 94.8 |
| Structured | 50 | 67.8 / 63.5 / 47.3 / 50.7 | 67.8 / 63.5 / 76.1 / 101.8 |
| Text-like: 443,577 / 70,898 / 455,000 / 71,302 B | 0.512 | 917.4 / 189.6 / 75.6 / 78.1 | 917.4 / 189.6 / 937.1 / 185.7 |
| Text-like | 2 | 272.0 / 84.3 / 52.9 / 59.5 | 272.0 / 84.3 / 272.6 / 84.2 |
| Text-like | 10 | 93.3 / 54.9 / 55.5 / 46.4 | 93.3 / 54.9 / 91.5 / 58.0 |
| Text-like | 50 | 57.2 / 49.9 / 52.8 / 48.2 | 57.2 / 49.9 / 60.3 / 54.4 |

## Compression levels and estimated break-even

At the nominal 300 KB target, these are clean four-mode standalone full-body gzip sizes and ratios. Paired CPU is process CPU per repetition while compressing both the full and framed body once.

| Payload | Gzip level | Full-body gzip bytes | Full-body ratio | Paired full+framed CPU (ms) |
|---|---:|---:|---:|---:|
| Structured | 1 | 40,636 | 13.55% | 1.09 |
| Structured | 3 | 23,627 | 7.88% | 3.91 |
| Structured | 6 | 23,735 | 7.91% | 8.28 |
| Structured | 9 | 28,066 | 9.36% | 20.63 |
| Text-like | 1 | 118,025 | 26.61% | 2.97 |
| Text-like | 3 | 79,291 | 17.88% | 9.84 |
| Text-like | 6 | 70,898 | 15.98% | 17.34 |
| Text-like | 9 | 70,402 | 15.87% | 31.88 |

Compared with level 1, estimated bytes saved and nominal transfer time saved are:

| Payload | Level | Bytes saved vs level 1 | Added paired CPU vs level 1 (ms) | Wire ms saved at 0.512 MB/s | at 2 MB/s | at 10 MB/s | at 50 MB/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Structured | 3 | 17,009 | 2.81 | 33.2 | 8.5 | 1.7 | 0.3 |
| Structured | 6 | 16,901 | 7.19 | 33.0 | 8.5 | 1.7 | 0.3 |
| Structured | 9 | 12,570 | 19.53 | 24.6 | 6.3 | 1.3 | 0.3 |
| Text-like | 3 | 38,734 | 6.88 | 75.7 | 19.4 | 3.9 | 0.8 |
| Text-like | 6 | 47,127 | 14.38 | 92.0 | 23.6 | 4.7 | 0.9 |
| Text-like | 9 | 47,623 | 28.91 | 93.0 | 23.8 | 4.8 | 1.0 |

For a higher level to repay its extra server CPU through wire-time savings, use the conservative paired-CPU break-even rule:

`break-even rate (MB/s) = bytes saved vs level 1 / added paired CPU vs level 1 (ms) / 1000`

| Payload | Level 3 vs 1 | Level 6 vs 1 | Level 9 vs 1 |
|---|---:|---:|---:|
| Structured | ~6.1 MB/s | ~2.4 MB/s | ~0.64 MB/s |
| Text-like | ~5.6 MB/s | ~3.3 MB/s | ~1.6 MB/s |

Below a level's break-even rate, its estimated wire-time savings exceed the paired CPU increment; above it, level 1 has the lower combined server-CPU-plus-wire-time estimate. On this model, level 1 wins at 10 and 50 MB/s for both payload kinds. At 2 MB/s, level 3 wins for both kinds; level 6 is only a narrow win for structured data (and a clearer win for text-like data). Level 9 pays off only at 0.512 MB/s. These are directional synthetic estimates, not production settings.

Three limits matter: paired CPU includes compression of both full and framed bodies, so using it against full-body byte savings is conservative; client decompression is excluded; and if precompressed bodies are cached as in this harness, compression CPU is paid outside the request path and this break-even comparison does not apply.
