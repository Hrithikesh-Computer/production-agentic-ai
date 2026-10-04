import { spawn } from "node:child_process";
import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const chromePath = process.env.CHROME_PATH ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const benchmarkUrl = process.env.BENCHMARK_URL ?? "http://127.0.0.1:8765/";
const debuggingPort = Number(process.env.CDP_PORT ?? 9222);
const outputPath = new URL("./browser_results_standalone_compression.json", import.meta.url);
try {
  await access(outputPath);
  throw new Error(`Refusing to overwrite ${outputPath.pathname}`);
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
const metadataResponse = await fetch(new URL("metadata", benchmarkUrl));
if (!metadataResponse.ok) {
  throw new Error(`Benchmark metadata endpoint returned ${metadataResponse.status}`);
}
await metadataResponse.arrayBuffer();
const profilePath = await mkdtemp(join(tmpdir(), "response-delivery-chrome-"));
const chrome = spawn(chromePath, [
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  "--remote-allow-origins=*",
  `--remote-debugging-port=${debuggingPort}`,
  `--user-data-dir=${profilePath}`,
  "about:blank",
], { stdio: "ignore", windowsHide: true });

let socket;
let nextId = 0;
const pending = new Map();

function send(method, params = {}, sessionId) {
  const id = ++nextId;
  const message = { id, method, params };
  if (sessionId) message.sessionId = sessionId;
  const response = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  socket.send(JSON.stringify(message));
  return response;
}

async function waitForDebugger() {
  const endpoint = `http://127.0.0.1:${debuggingPort}/json/version`;
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(endpoint);
      if (response.ok) return response.json();
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error("Chrome remote-debugging endpoint did not start");
}

async function connectDebugger(webSocketUrl) {
  socket = new WebSocket(webSocketUrl);
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    if (message.error) request.reject(new Error(message.error.message));
    else request.resolve(message.result);
  });
  socket.addEventListener("error", () => {
    for (const request of pending.values()) request.reject(new Error("CDP socket failed"));
    pending.clear();
  });
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
}

try {
  const debuggerInfo = await waitForDebugger();
  await connectDebugger(debuggerInfo.webSocketDebuggerUrl);
  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", {
    targetId,
    flatten: true,
  });
  await send("Page.enable", {}, sessionId);
  await send("Runtime.enable", {}, sessionId);
  await send("Page.navigate", { url: benchmarkUrl }, sessionId);

  const expression = `(() => new Promise((resolve, reject) => {
    const deadline = Date.now() + 900000;
    const poll = () => {
      if (window.__experimentComplete) {
        window.__experimentComplete.then(result => resolve({
          browser_environment: result.browser_environment,
          longtask_positive_control: result.longtask_positive_control,
          payload_kinds: result.payload_kinds,
          target_sizes: result.target_sizes,
          transfer_rates_bytes_per_second: result.transfer_rates_bytes_per_second,
          mode_count: Object.keys(result.cases.structured[300000][512000]).filter(
            key => ["full", "gzip_full", "framed_http", "gzip_framed"].includes(key)
          ).length
        }), reject);
        return;
      }
      if (Date.now() >= deadline) {
        reject(new Error("Timed out waiting for window.__experimentComplete"));
        return;
      }
      setTimeout(poll, 25);
    };
    poll();
  }))()`;
  const evaluation = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  }, sessionId);
  if (evaluation.exceptionDetails) {
    throw new Error(evaluation.exceptionDetails.text);
  }
  console.log(JSON.stringify(evaluation.result.value, null, 2));
  const savedArtifact = JSON.parse(await readFile(outputPath, "utf8"));
  const timingRecordCount = Object.keys(savedArtifact.server_timings).length;
  if (timingRecordCount !== 384) {
    throw new Error(`Expected 384 server timing records, got ${timingRecordCount}`);
  }
  console.log(JSON.stringify({
    artifact: outputPath.pathname,
    timing_record_count: timingRecordCount,
    run_metadata: savedArtifact.run_metadata,
  }, null, 2));
  await send("Browser.close");
} finally {
  if (socket?.readyState === WebSocket.OPEN) socket.close();
  if (chrome.exitCode === null) {
    await Promise.race([
      new Promise(resolve => chrome.once("exit", resolve)),
      new Promise(resolve => setTimeout(resolve, 5000)),
    ]);
  }
  if (chrome.exitCode === null) chrome.kill();
  await rm(profilePath, { recursive: true, force: true });
}