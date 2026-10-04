from __future__ import annotations

import gzip
import hashlib
import json
import os
import platform
import random
import sys
import threading
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from benchmark import _make_payload

REFERENCE_IMPL = Path(__file__).resolve().parents[2] / "04-reference-implementation"
if str(REFERENCE_IMPL) not in sys.path:
  sys.path.insert(0, str(REFERENCE_IMPL))

from ndjson_stream import encode_record  # noqa: E402

TARGET_SIZES = (90_000, 300_000)
PAYLOAD_KINDS = ("structured", "text_like")
TRANSFER_RATES = (512_000, 2_000_000, 10_000_000, 50_000_000)
FRAME_BYTES = 16_000
INITIAL_DELAY_SECONDS = 0.040
WARMUPS = 1
REPETITIONS = 5
COMPRESSION_LEVELS = (1, 3, 6, 9)
COMPRESSION_CPU_REPETITIONS = 100
REQUEST_TIMINGS: dict[str, dict[str, int | float | str]] = {}
TIMINGS_LOCK = threading.Lock()
RUN_STARTED_AT_UTC = datetime.now(timezone.utc).isoformat()
HARNESS_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SERVER_PROCESS_ID = os.getpid()
PORT = int(os.environ.get("BROWSER_BENCHMARK_PORT", "8765"))


def _make_frames(payload: Mapping[str, object]) -> list[bytes]:
    frames: list[bytes] = []
    current = bytearray()
    for key, value in payload.items():
        record = encode_record({"key": key, "value": value})
        if current and len(current) + len(record) > FRAME_BYTES:
            frames.append(bytes(current))
            current.clear()
        current.extend(record)
    if current:
        frames.append(bytes(current))
    return frames


def _make_text_like_payload(target_size: int) -> dict[str, Any]:
  adjectives = [
    "active", "annual", "available", "careful", "central", "current", "delayed",
    "direct", "early", "eligible", "external", "final", "frequent", "gradual",
    "historical", "immediate", "individual", "initial", "internal", "limited",
    "local", "monthly", "necessary", "optional", "previous", "primary", "recent",
    "regional", "relevant", "reported", "separate", "shared", "specific", "stable",
    "temporary", "typical", "updated", "valid", "verified", "weekly",
  ]
  nouns = [
    "account", "activity", "agreement", "approval", "assessment", "attachment",
    "balance", "case", "change", "claim", "comment", "contact", "customer",
    "decision", "delivery", "document", "event", "exception", "feedback", "field",
    "finding", "follow-up", "history", "incident", "instruction", "invoice", "item",
    "ledger", "message", "metric", "note", "operation", "owner", "payment", "period",
    "policy", "process", "record", "request", "review", "risk", "schedule", "service",
    "source", "status", "summary", "task", "team", "update", "user", "workflow",
  ]
  verbs = [
    "changed", "continues", "depends", "differs", "emerged",
    "explains", "follows", "includes", "increased", "indicates",
    "matches", "requires", "remains", "reported", "resulted",
    "shifted", "shows", "started", "suggests", "supports",
    "tracks", "varies", "was recorded", "was reviewed",
    "was transferred", "will continue", "will require",
  ]
  connectors = [
    "after", "although", "because", "before", "during", "if", "once", "unless",
    "while", "without", "following", "rather than", "together with", "subject to",
  ]
  outcomes = [
    "a later review", "an owner response", "additional evidence", "the active policy",
    "the next billing period", "a separate approval", "the original request",
    "a verified source", "the expected schedule", "a documented exception",
    "the current account state", "a follow-up conversation", "the reported outcome",
    "the service history", "the final recommendation", "a customer preference",
  ]
  randomizer = random.Random(4317)
  item_count = max(1, target_size // 420)
  while True:
    randomizer.seed(4317 + item_count)
    payload: dict[str, Any] = {}
    for index in range(item_count):
      sentences = []
      for _ in range(5 + index % 5):
        adjective_one, adjective_two = randomizer.sample(adjectives, 2)
        noun_one, noun_two = randomizer.sample(nouns, 2)
        verb = randomizer.choice(verbs)
        connector = randomizer.choice(connectors)
        outcome = randomizer.choice(outcomes)
        sentences.append(
          f"The {adjective_one} {noun_one} {verb} the {adjective_two} "
          f"{noun_two} {connector} {outcome}."
        )
      payload[f"case-{index:05d}"] = {
        "id": index,
        "name": f"Case review {index:05d}",
        "content": " ".join(sentences),
      }
    serialized = json.dumps(
      payload, ensure_ascii=False, separators=(",", ":")
    )
    if len(serialized.encode("utf-8")) >= target_size:
      return payload
    item_count += max(1, (target_size - len(serialized)) // 420)


CASES: dict[tuple[str, int], tuple[bytes, bytes, list[bytes], bytes]] = {}
for payload_kind in PAYLOAD_KINDS:
  for target_size in TARGET_SIZES:
    payload: dict[str, Any]
    if payload_kind == "structured":
      payload = json.loads(_make_payload(target_size))
    else:
      payload = _make_text_like_payload(target_size)
    full_body = json.dumps(
      payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    frames = _make_frames(payload)
    framed_body = b"".join(frames)
    CASES[(payload_kind, target_size)] = (
      full_body,
      gzip.compress(full_body, compresslevel=6, mtime=0),
      frames,
      gzip.compress(framed_body, compresslevel=6, mtime=0),
    )


def _compression_sweep() -> dict[str, dict[int, list[dict[str, int | float]]]]:
    sweep: dict[str, dict[int, list[dict[str, int | float]]]] = {}
    for (payload_kind, size), (full_body, _, frames, _) in CASES.items():
        framed_body = b"".join(frames)
        measurements = []
        for level in COMPRESSION_LEVELS:
            started_ns = time.process_time_ns()
            for _ in range(COMPRESSION_CPU_REPETITIONS):
                compressed_full = gzip.compress(
                    full_body, compresslevel=level, mtime=0
                )
                compressed_framed = gzip.compress(
                    framed_body, compresslevel=level, mtime=0
                )
            elapsed_ms = (
                (time.process_time_ns() - started_ns)
                / COMPRESSION_CPU_REPETITIONS
                / 1_000_000
            )
            measurements.append(
                {
                    "level": level,
                    "gzip_full_bytes": len(compressed_full),
                    "gzip_full_ratio": len(compressed_full) / len(full_body),
                    "gzip_framed_bytes": len(compressed_framed),
                    "gzip_framed_ratio": len(compressed_framed) / len(framed_body),
                    "compression_cpu_ms": elapsed_ms,
                }
            )
        sweep.setdefault(payload_kind, {})[size] = measurements
    return sweep


COMPRESSION_SWEEP = _compression_sweep()


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>Response delivery rate sweep</title>
<h1>Response delivery rate sweep</h1>
<p id="status">Running controlled loopback cases…</p>
<pre id="results"></pre>
<div id="render-root"></div>
<script>
const warmups = 1;
const repetitions = 5;
const resultsElement = document.querySelector("#results");
const root = document.querySelector("#render-root");
const status = document.querySelector("#status");
const longTasks = [];
let longTaskObserver = null;
let longTaskValidated = false;
window.__experimentComplete = new Promise(resolve => {
  window.__resolveExperiment = resolve;
});
const longTaskSupported = "PerformanceObserver" in window &&
  PerformanceObserver.supportedEntryTypes?.includes("longtask") === true;
if (longTaskSupported) {
  longTaskObserver = new PerformanceObserver(list => {
    longTasks.push(...list.getEntries());
  });
  longTaskObserver.observe({ type: "longtask", buffered: true });
}

function nextFrame() {
  return new Promise(resolve => requestAnimationFrame(resolve));
}

function appendRecords(list, entries) {
  const fragment = document.createDocumentFragment();
  for (const [key, value] of entries) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const detail = document.createElement("span");
    title.textContent = value.name;
    detail.textContent = ` ${key} · ${value.payload}`;
    item.append(title, detail);
    fragment.append(item);
  }
  list.append(fragment);
  return entries.length;
}

function summarize(values) {
  const sorted = [...values].sort((left, right) => left - right);
  return { p50: sorted[Math.floor((sorted.length - 1) / 2)], max: sorted.at(-1) };
}

async function readFullBody(response, requestId) {
  const reader = response.body.getReader();
  const chunks = [];
  let bodyBytes = 0;
  let firstByteMs = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    if (firstByteMs === null) firstByteMs = performance.now() - requestId.startedAt;
    chunks.push(value);
    bodyBytes += value.byteLength;
  }
  const bytes = new Uint8Array(bodyBytes);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return {
    payload: JSON.parse(new TextDecoder().decode(bytes)),
    bodyBytes,
    firstByteMs
  };
}

function longTasksIn(start, end) {
  if (!longTaskValidated) return null;
  longTasks.push(...longTaskObserver.takeRecords());
  return longTasks
    .filter(entry => entry.startTime < end && entry.startTime + entry.duration > start)
    .map(entry => ({ start_ms: entry.startTime, duration_ms: entry.duration }));
}

async function measure(payloadKind, size, rate, mode) {
  root.replaceChildren();
  await nextFrame();
  const startedAt = performance.now();
  const requestId = { startedAt, value: crypto.randomUUID() };
  const query = new URLSearchParams({
    payload_kind: payloadKind,
    size: String(size),
    rate: String(rate),
    mode,
    request_id: requestId.value
  });
  const response = await fetch(`/payload?${query}`, { cache: "no-store" });
  let firstByteMs = null;
  let firstVisibleMs = null;
  let firstVisibleItems = 0;
  let itemCount = 0;

  if (mode !== "framed_http" && mode !== "gzip_framed") {
    const result = await readFullBody(response, requestId);
    firstByteMs = result.firstByteMs;
    const list = document.createElement("ul");
    itemCount = appendRecords(list, Object.entries(result.payload));
    root.append(list);
    firstVisibleItems = itemCount;
    await nextFrame();
    firstVisibleMs = performance.now() - startedAt;
  } else {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    let list = null;
    let firstVisibleRecorded = false;
    while (true) {
      const { value, done } = await reader.read();
      if (value && firstByteMs === null) {
        firstByteMs = performance.now() - startedAt;
      }
      pending += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = pending.split("\n");
      pending = lines.pop();
      const entries = [];
      for (const line of lines) {
        if (line) {
          const record = JSON.parse(line);
          entries.push([record.key, record.value]);
        }
      }
      if (entries.length) {
        if (!list) {
          list = document.createElement("ul");
          root.append(list);
        }
        itemCount += appendRecords(list, entries);
        if (!firstVisibleRecorded) {
          await nextFrame();
          firstVisibleMs = performance.now() - startedAt;
          firstVisibleItems = itemCount;
          firstVisibleRecorded = true;
        }
      }
      if (done) break;
    }
    if (pending) {
      const record = JSON.parse(pending);
      if (!list) {
        list = document.createElement("ul");
        root.append(list);
      }
      itemCount += appendRecords(list, [[record.key, record.value]]);
      if (!firstVisibleRecorded) {
        await nextFrame();
        firstVisibleMs = performance.now() - startedAt;
        firstVisibleItems = itemCount;
      }
    }
  }

  const endedAt = performance.now();
  return {
    request_id: requestId.value,
    first_byte_ms: firstByteMs,
    first_visible_ms: firstVisibleMs,
    first_visible_items: firstVisibleItems,
    total_ms: endedAt - startedAt,
    item_count: itemCount,
    long_tasks: longTasksIn(startedAt, endedAt)
  };
}

function summarizeRuns(runs) {
  const firstByte = runs.map(run => run.first_byte_ms);
  const firstVisible = runs.map(run => run.first_visible_ms);
  const total = runs.map(run => run.total_ms);
  const taskCounts = runs.map(run => run.long_tasks?.length ?? null);
  return {
    first_byte_ms: summarize(firstByte),
    first_visible_ms: summarize(firstVisible),
    total_ms: summarize(total),
    first_visible_items: runs[0].first_visible_items,
    item_count: runs[0].item_count,
    long_task_count_mean: longTaskValidated
      ? taskCounts.reduce((sum, value) => sum + value, 0) / runs.length
      : null,
    long_task_count_max: longTaskValidated ? Math.max(...taskCounts) : null
  };
}

async function runLongTaskPositiveControl() {
  if (!longTaskSupported) {
    return { supported: false, detected: null, observed_duration_ms: null };
  }
  const controlStart = performance.now();
  const blockUntil = controlStart + 120;
  while (performance.now() < blockUntil) {}
  await nextFrame();
  await new Promise(resolve => setTimeout(resolve, 100));
  const controlEnd = performance.now();
  longTasks.push(...longTaskObserver.takeRecords());
  const entries = longTasks.filter(
    entry => entry.startTime < controlEnd &&
      entry.startTime + entry.duration > controlStart
  );
  const controlTask = entries.find(entry => entry.duration >= 100);
  return {
    supported: true,
    requested_block_ms: 120,
    detected: controlTask !== undefined,
    observed_duration_ms: controlTask?.duration ?? null,
    overlapping_entries: entries.map(entry => ({
      start_ms: entry.startTime,
      duration_ms: entry.duration
    }))
  };
}

(async () => {
  const metadata = await (await fetch("/metadata")).json();
  const results = {
    browser_user_agent: navigator.userAgent,
    browser_environment: navigator.userAgent.includes("HeadlessChrome")
      ? "standalone-headless-chrome"
      : navigator.userAgent.includes("Electron")
        ? "Electron-embedded"
        : "standalone-or-other",
    longtask_supported: longTaskSupported,
    longtask_positive_control: await runLongTaskPositiveControl(),
    initial_delay_ms: metadata.initial_delay_ms,
    frame_bytes: metadata.frame_bytes,
    python_version: metadata.python_version,
    python_implementation: metadata.python_implementation,
    server_platform: metadata.platform,
    transfer_rates_bytes_per_second: metadata.transfer_rates_bytes_per_second,
    payload_kinds: metadata.payload_kinds,
    target_sizes: metadata.target_sizes,
    compression_levels: metadata.compression_levels,
    compression_sweep: metadata.compression_sweep,
    warmups,
    repetitions,
    cases: {}
  };
  longTaskValidated = results.longtask_positive_control.detected === true;

  for (const payloadKind of metadata.payload_kinds) {
  results.cases[payloadKind] = {};
  for (const size of metadata.target_sizes) {
    results.cases[payloadKind][size] = {};
    for (const rate of metadata.transfer_rates_bytes_per_second) {
      const runsByMode = {
        full: [], gzip_full: [], framed_http: [], gzip_framed: []
      };
      for (let warmup = 0; warmup < warmups; warmup++) {
        await measure(payloadKind, size, rate, "full");
        await measure(payloadKind, size, rate, "gzip_full");
        await measure(payloadKind, size, rate, "framed_http");
        await measure(payloadKind, size, rate, "gzip_framed");
      }
      for (let index = 0; index < repetitions; index++) {
        const modeOrders = [
          ["full", "gzip_full", "framed_http", "gzip_framed"],
          ["gzip_full", "framed_http", "gzip_framed", "full"],
          ["framed_http", "gzip_framed", "full", "gzip_full"],
          ["gzip_framed", "full", "gzip_full", "framed_http"]
        ];
        const modes = modeOrders[index % modeOrders.length];
        for (const mode of modes) {
          runsByMode[mode].push(await measure(payloadKind, size, rate, mode));
        }
      }
      results.cases[payloadKind][size][rate] = {
        payload_bytes: metadata.cases[payloadKind][size].payload_bytes,
        gzip_bytes: metadata.cases[payloadKind][size].gzip_bytes,
        framed_body_bytes: metadata.cases[payloadKind][size].framed_body_bytes,
        gzip_framed_bytes: metadata.cases[payloadKind][size].gzip_framed_bytes,
        full: summarizeRuns(runsByMode.full),
        gzip_full: summarizeRuns(runsByMode.gzip_full),
        framed_http: summarizeRuns(runsByMode.framed_http),
        gzip_framed: summarizeRuns(runsByMode.gzip_framed),
        runs: runsByMode
      };
    }
  }
  }

  resultsElement.textContent = JSON.stringify(results, null, 2);
  await fetch("/results", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(results)
  });
  status.textContent = "Complete. Results saved; inspect pacing and support metadata.";
  window.__resolveExperiment(results);
})();
</script>
"""


def _paced_write(
    handler: BaseHTTPRequestHandler,
    segments: list[bytes],
    rate_bytes_per_second: int,
    request_timing: dict[str, int | float | str],
) -> None:
    start_ns = time.perf_counter_ns()
    body_bytes = 0
    for segment_index, segment in enumerate(segments):
        target_ns = start_ns + int(
            (body_bytes + len(segment)) / rate_bytes_per_second * 1_000_000_000
        )
        remaining_ns = target_ns - time.perf_counter_ns()
        if remaining_ns > 0:
            time.sleep(remaining_ns / 1_000_000_000)
        if segment_index == 0:
          request_timing["first_write_target_ns"] = target_ns
          request_timing["first_segment_bytes"] = len(segment)
        handler.wfile.write(segment)
        handler.wfile.flush()
        if segment_index == 0:
          request_timing["first_write_ns"] = time.perf_counter_ns()
        body_bytes += len(segment)
    request_timing["body_complete_ns"] = time.perf_counter_ns()
    request_timing["body_bytes_written"] = body_bytes


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_content_headers(
        self, content_type: str, request_id: str, request_timing: dict
    ) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Request-Id", request_id)
        self.send_header("Cache-Control", "no-store")
        request_timing["headers_started_ns"] = time.perf_counter_ns()

    def do_GET(self) -> None:
        request_ns = time.perf_counter_ns()
        request = urlsplit(self.path)
        if request.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif request.path == "/metadata":
            case_metadata = {
                payload_kind: {
                    size: {
                        "payload_bytes": len(CASES[(payload_kind, size)][0]),
                        "gzip_bytes": len(CASES[(payload_kind, size)][1]),
                        "framed_body_bytes": sum(
                            map(len, CASES[(payload_kind, size)][2])
                        ),
                        "gzip_framed_bytes": len(CASES[(payload_kind, size)][3]),
                    }
                    for size in TARGET_SIZES
                }
                for payload_kind in PAYLOAD_KINDS
            }
            body = json.dumps(
                {
                    "target_sizes": TARGET_SIZES,
                    "payload_kinds": PAYLOAD_KINDS,
                    "transfer_rates_bytes_per_second": TRANSFER_RATES,
                    "compression_levels": COMPRESSION_LEVELS,
                    "compression_sweep": COMPRESSION_SWEEP,
                    "cases": case_metadata,
                    "frame_bytes": FRAME_BYTES,
                    "initial_delay_ms": INITIAL_DELAY_SECONDS * 1000,
                    "python_version": platform.python_version(),
                    "python_implementation": platform.python_implementation(),
                    "platform": platform.platform(),
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif request.path == "/payload":
            query = parse_qs(request.query)
            try:
                payload_kind = query["payload_kind"][0]
                size = int(query["size"][0])
                rate = int(query["rate"][0])
                mode = query["mode"][0]
                request_id = query["request_id"][0]
                full_body, gzip_body, frames, gzip_framed_body = CASES[
                  (payload_kind, size)
                ]
                if rate not in TRANSFER_RATES:
                    raise ValueError("unsupported transfer rate")
                if mode not in {"full", "gzip_full", "framed_http", "gzip_framed"}:
                    raise ValueError("unsupported mode")
            except (KeyError, ValueError, IndexError):
                self.send_error(400, "valid size, rate, mode, and request id required")
                return

            timing: dict[str, int | float | str] = {
                "request_id": request_id,
                "mode": mode,
                "size": size,
                "payload_kind": payload_kind,
                "rate_bytes_per_second": rate,
                "request_received_ns": request_ns,
            }
            time.sleep(INITIAL_DELAY_SECONDS)
            if mode == "full":
                self._send_content_headers(
                    "application/json", request_id, timing
                )
                self.send_header("Content-Length", str(len(full_body)))
                self.end_headers()
                timing["headers_complete_ns"] = time.perf_counter_ns()
                _paced_write(
                    self,
                    [
                        full_body[index : index + FRAME_BYTES]
                        for index in range(0, len(full_body), FRAME_BYTES)
                    ],
                    rate,
                    timing,
                )
            elif mode == "gzip_full":
                self._send_content_headers(
                    "application/json", request_id, timing
                )
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(gzip_body)))
                self.end_headers()
                timing["headers_complete_ns"] = time.perf_counter_ns()
                _paced_write(
                    self,
                    [
                        gzip_body[index : index + FRAME_BYTES]
                        for index in range(0, len(gzip_body), FRAME_BYTES)
                    ],
                    rate,
                    timing,
                )
            else:
                self._send_content_headers(
                    "application/x-ndjson", request_id, timing
                )
                if mode == "gzip_framed":
                    self.send_header("Content-Encoding", "gzip")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                timing["headers_complete_ns"] = time.perf_counter_ns()
                if mode == "gzip_framed":
                    body_segments = [
                        gzip_framed_body[index : index + FRAME_BYTES]
                        for index in range(0, len(gzip_framed_body), FRAME_BYTES)
                    ]
                else:
                    body_segments = frames
                wire_segments = [
                    f"{len(segment):X}\r\n".encode("ascii")
                    + segment
                    + b"\r\n"
                    for segment in body_segments
                ]
                _paced_write(self, wire_segments, rate, timing)
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

            timing["request_complete_ns"] = time.perf_counter_ns()
            with TIMINGS_LOCK:
                REQUEST_TIMINGS[request_id] = timing
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/results":
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > 10_000_000:
            self.send_error(400, "invalid result size")
            return
        results = json.loads(self.rfile.read(content_length))
        with TIMINGS_LOCK:
            server_timings = dict(REQUEST_TIMINGS)
        results["server_timings"] = server_timings
        results["run_metadata"] = {
          "run_started_at_utc": RUN_STARTED_AT_UTC,
          "results_saved_at_utc": datetime.now(timezone.utc).isoformat(),
          "harness_sha256": HARNESS_SHA256,
          "server_process_id": SERVER_PROCESS_ID,
          "compression_sweep_process_id": SERVER_PROCESS_ID,
          "compression_sweep_same_process": True,
        }
        result_name = (
          "browser_results_compression.json"
          if results.get("browser_environment") == "Electron-embedded"
          else "browser_results_standalone_compression.json"
        )
        output_path = Path(__file__).with_name(result_name)
        output_path.write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
        response = b"saved"
        self.send_response(200)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format_string: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Open http://127.0.0.1:{PORT}/ in standalone Chrome to run the experiment.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()