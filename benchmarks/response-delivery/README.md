# Response delivery benchmark

This local benchmark exercises the repository's response-delivery reference implementation in `04-reference-implementation/adaptive-response-filter`.

## What it measures

For each generated JSON payload, the script measures both full-buffer policy construction and chunked-envelope construction on the same payload. It then feeds chunked envelopes to the actual `Reassembler` in reverse arrival order.

Measured fields:

- payload size
- chunk count
- median and maximum local policy-build time after five warmup runs
- median and maximum authenticated reassembly time for chunked payloads
- chunk count and payload correctness (pass-through for full mode; semantic reassembly for chunked mode)

## What it does not measure

The Python benchmark timings cover local code only. They do not measure time-to-first-visible content, browser parsing or rendering, network transfer, TLS, a deployed service, or production behavior. The full-buffer path has no receiver reassembly step, so its reassembly time is not applicable. Both policy modes process identical payloads, but the full path returns the original payload while the chunked path builds and authenticates envelopes; this measures implementation overhead, not equivalent end-to-end delivery work.

## How to run

```bash
python benchmarks/response-delivery/benchmark.py
```

## Interpretation

In the latest local run, the 300 KB payload's full-policy build median/max was 1.69/2.92 ms. Chunked-envelope build was 22.70/28.77 ms, and authenticated reassembly was 5.87/8.27 ms. These are machine- and interpreter-specific implementation timings; use the medians, not cross-size mean comparisons. They are not a delivery-latency benefit. See [`results.csv`](results.csv), [`EVIDENCE.md`](../../EVIDENCE.md), and the related [article](../../03-production-lessons/01-adaptive-response-delivery.md).

## Browser Experiment

Run `python benchmarks/response-delivery/browser_benchmark.py`, then use a second terminal to run `node benchmarks/response-delivery/run_standalone_cdp.mjs`. The CDP runner launches standalone Chrome with a fresh profile and awaits `window.__experimentComplete`; it refuses to overwrite the standalone result artifact. Set `CHROME_PATH` to select another Chrome executable. The matrix uses generated payloads targeting 90 KB and 300 KB at nominal server pacing rates of 0.512, 2, 10, and 50 MB/s. It has one warmup and five measured runs per mode and cell. The browser compares `full`, `gzip_full`, `framed_http`, and `gzip_framed`; the last mode sends a precompressed NDJSON body using gzip content encoding and chunked HTTP transfer. Gzip compression is prepared before per-request timings.

The harness records request receipt, response headers, scheduled and actual first write, body completion, first received byte, first visible content, and full client completion. Results are correlated by request ID. Full mode's first-visible time follows parsing and appending the entire object; framed modes report after the first complete received record batch. The timestamp is a `requestAnimationFrame` callback after the DOM update, not a compositor-confirmed paint.

At module startup the harness also sweeps gzip levels 1, 3, 6, and 9 for full JSON and framed NDJSON across both generated payload kinds and target sizes. It records the resulting compressed-size ratios and mean process CPU time over 100 compression repetitions. This CPU measurement is separate from per-request delivery timing and does not represent a production compressor or streaming flush cost.

The original [`browser_results.json`](browser_results.json) is the legacy standalone HeadlessChrome baseline with three modes. Its nominal 300,000-byte text-like case is actually 306,891 bytes. The Electron [`browser_results_compression.json`](browser_results_compression.json) and fresh-profile CDP [`browser_results_standalone_compression.json`](browser_results_standalone_compression.json) are four-mode runs with 384 server timing records each; their payload byte sizes match exactly. The clean four-mode standalone Long Task control was detected at 121 ms; the legacy standalone control was also detected, while Electron's was not. The Electron artifact has no run timestamp or harness hash, so retain that provenance caveat even though its payloads now match the clean standalone run. The gzip CPU sweep measures server-side compression only, not client decompression/rendering. Both four-mode runs use generated synthetic payloads and establish no production threshold or customer-network behavior. Detailed P50 timing tables and compression break-even analysis are in [`browser-matrix-evidence.md`](browser-matrix-evidence.md).
