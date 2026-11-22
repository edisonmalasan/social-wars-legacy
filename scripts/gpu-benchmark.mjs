#!/usr/bin/env node
/**
 * Hardware-accelerated large-battle frame timing.
 *
 * This script does **not** guess that a GPU is usable because a GPU exists.
 * It checks three layers and reports all three verbatim:
 *
 *   1. `nvidia-smi` (an NVIDIA card, if the tool is present);
 *   2. the system's video controllers (`wmic`, or PowerShell on Windows);
 *   3. the renderer string WebGL actually gives the browser — this is the
 *      deciding one, because frame timing only means anything if the client
 *      is really drawing through an accelerated renderer.
 *
 * If the browser renderer is SwiftShader / llvmpipe / WARP / "Basic Render
 * Driver" or otherwise unknown, the script **skips** with an explicit reason
 * and prints "NOT A PERFORMANCE RESULT". It does not run the frame loop at all
 * in that case, so a software run can never be mistaken for a GPU number.
 *
 * When acceleration is real, a deterministic fixture (150 + 150 units from
 * the real content bundle) is served to the **built client** in a real
 * browser, and `requestAnimationFrame` deltas are measured there. The client
 * and the fixture are both the repository's own code; no new dependencies.
 *
 * Usage:
 *   node scripts/gpu-benchmark.mjs
 *   node scripts/gpu-benchmark.mjs --json --out report.json
 *   node scripts/gpu-benchmark.mjs --seed repeatable --army-size 200 --frames 300
 *   node scripts/gpu-benchmark.mjs --fixture-only       # no browser at all
 */

import { spawn, spawnSync } from 'node:child_process';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { mkdtemp } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

import {
  createBattleFixture,
  DEFAULT_ARMY_SIZE,
  DEFAULT_SEED,
} from './lib/battle-fixture.mjs';

const ROOT = process.cwd();
const BUNDLE = path.join(ROOT, 'apps/client/public/content-bundle.json');
const DIST = path.join(ROOT, 'apps/client/dist');
const PUBLIC = path.join(ROOT, 'apps/client/public');
const FRAMES = path.join(ROOT, '.work/frames');
const INDEX = path.join(DIST, 'index.html');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.wasm': 'application/wasm',
  '.svg': 'image/svg+xml',
};

const BROWSERS = [
  {
    name: 'chrome',
    paths: [
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      '/usr/bin/google-chrome',
      '/usr/bin/chromium',
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ],
  },
  {
    name: 'edge',
    paths: [
      'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
      'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
      '/usr/bin/microsoft-edge',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    ],
  },
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Run a command without throwing; keep both streams for the report. */
function run(command, args, timeoutMs = 15_000) {
  try {
    const result = spawnSync(command, args, {
      encoding: 'utf8',
      timeout: timeoutMs,
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    });
    return {
      ok: result.status === 0 && !result.error,
      stdout: String(result.stdout ?? ''),
      stderr: String(result.stderr ?? ''),
      error: result.error ? String(result.error.message ?? result.error) : null,
    };
  } catch (error) {
    return { ok: false, stdout: '', stderr: '', error: String(error) };
  }
}

/** Layer 1: the driver tool's own view of the card. */
function nvidiaDetection() {
  const result = run('nvidia-smi', [
    '--query-gpu=name,driver_version',
    '--format=csv,noheader',
  ]);
  const raw = `${result.stdout}${result.stderr}`.trim();
  return {
    available: result.ok,
    raw: raw || null,
    gpus: result.ok
      ? raw.split('\n').map((line) => line.trim()).filter(Boolean)
      : [],
  };
}

/** Layer 2: the OS's video controllers. `wmic` is gone on newer Windows. */
function systemGpuDetection() {
  if (process.platform === 'win32') {
    const wmic = run('wmic', [
      'path', 'win32_VideoController', 'get', 'name', '/value',
    ]);
    if (wmic.ok) {
      const names = wmic.stdout
        .split('\n')
        .map((line) => line.trim().replace(/^Name=/, ''))
        .filter(Boolean);
      return { source: 'wmic', available: true, raw: wmic.stdout.trim(), names };
    }
    const ps = run('powershell', [
      '-NoProfile', '-Command',
      'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name',
    ], 20_000);
    const names = ps.ok
      ? ps.stdout.split('\n').map((line) => line.trim()).filter(Boolean)
      : [];
    return {
      source: 'powershell Get-CimInstance Win32_VideoController',
      available: ps.ok,
      raw: `${ps.stdout}${ps.stderr}`.trim() || null,
      names,
    };
  }
  const lspci = run('lspci', ['-nnk']);
  return {
    source: 'lspci -nnk',
    available: lspci.ok,
    raw: lspci.ok ? lspci.stdout.trim() : null,
    names: [],
  };
}

function findBrowser(preferred) {
  const entries = preferred
    ? BROWSERS.filter((entry) => entry.name === preferred)
    : BROWSERS;
  for (const entry of entries) {
    for (const candidate of entry.paths) {
      if (existsSync(candidate)) {
        return { name: entry.name, path: candidate };
      }
    }
  }
  return null;
}

/** Launch a browser with acceleration **enabled** (no `--disable-gpu`). */
function launchBrowser(browser, port) {
  const args = [
    '--headless=new',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--no-first-run',
    '--no-default-browser-check',
    '--ignore-gpu-blocklist',
    '--enable-gpu',
  ];
  if (process.platform === 'win32') args.push('--use-angle=d3d11');
  return spawn(browser.path, [...args, `--remote-debugging-port=${port}`, 'about:blank'], {
    stdio: 'ignore',
    windowsHide: true,
  });
}

/** Wait for the DevTools endpoint to answer. */
async function waitForDevTools(port, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return await response.json();
    } catch {
      // Not up yet.
    }
    await sleep(150);
  }
  throw new Error('the browser did not open its debugging port');
}

/** A page's WebGL renderer, read from the browser itself. */
const RENDERER_EXPRESSION = `(() => {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
  if (!gl) return { renderer: null, vendor: null, webgl2: false };
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    renderer: String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)),
    vendor: ext ? String(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL)) : null,
    webgl2: typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext,
    unmasked: Boolean(ext),
  };
})()`;

/** Software renderers are real, but they are not a GPU result. */
function classifyRenderer(renderer) {
  if (!renderer) return { accelerated: false, kind: 'none' };
  const software =
    /swiftshader|llvmpipe|softpipe|lavapipe|software|warp|basic render|microsoft basic|mesa offscreen/i;
  const hardware =
    /nvidia|geforce|quadro|rtx\b|gtx\b|amd|radeon|intel|iris|uhd graphics|arc\b|apple m[1-9]|d3d11|metal/i;
  if (software.test(renderer)) return { accelerated: false, kind: 'software' };
  if (hardware.test(renderer)) return { accelerated: true, kind: 'hardware' };
  return { accelerated: false, kind: 'unknown' };
}

/** Open a tab over the DevTools protocol and return a command sender. */
async function openSession(port, url) {
  const target = await (
    await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, {
      method: 'PUT',
    })
  ).json();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });

  let nextId = 1;
  const pending = new Map();
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data));
    const resolver = pending.get(message.id);
    if (resolver) {
      pending.delete(message.id);
      resolver(message);
    }
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = nextId++;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`DevTools ${method} timed out`));
      }, 120_000);
      pending.set(id, (message) => {
        clearTimeout(timer);
        resolve(message);
      });
      socket.send(JSON.stringify({ id, method, params }));
    });

  await send('Runtime.enable', {});
  await send('Page.enable', {});
  return {
    send,
    close: async () => {
      socket.close();
      await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`).catch(() => {});
    },
  };
}

/** Wait until the page is really the client's, and has loaded. */
async function waitForThePage(send, url, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const answer = await send('Runtime.evaluate', {
        expression: 'location.href',
        returnByValue: true,
      });
      const where = answer.result?.result?.value;
      if (typeof where === 'string' && where.startsWith('http://127.0.0.1:')) {
        const state = await send('Runtime.evaluate', {
          expression: 'document.readyState',
          returnByValue: true,
        });
        if (['complete', 'interactive'].includes(state.result?.result?.value)) return;
      }
    } catch {
      // The document is not there yet.
    }
    await sleep(100);
  }
  throw new Error('the page did not load');
}

/** Wait for the client's own status marker, not merely a loaded document. */
async function waitForClient(send, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  let last = 'missing|';
  while (Date.now() < deadline) {
    const answer = await send('Runtime.evaluate', {
      expression:
        "(() => { const e = document.getElementById('status');" +
        " return e ? e.getAttribute('data-state') + '|' + e.textContent : 'missing'; })()",
      returnByValue: true,
    });
    last = String(answer.result?.result?.value ?? 'missing');
    const state = last.split('|')[0];
    if (state === 'started') return { started: true, status: last };
    if (state === 'failed') break;
    await sleep(250);
  }
  return { started: false, status: last };
}

/** Measure requestAnimationFrame deltas inside the page. */
async function measureFrames(send, frames) {
  const expression = `(async () => {
    const deltas = [];
    let last = performance.now();
    for (let i = 0; i < ${frames + 1}; i++) {
      await new Promise((resolve) => requestAnimationFrame((t) => {
        deltas.push(t - last); last = t; resolve();
      }));
    }
    const xs = deltas.slice(1).sort((a, b) => a - b);
    const sum = xs.reduce((a, b) => a + b, 0);
    const q = (p) => xs[Math.min(xs.length - 1, Math.floor(p * xs.length))];
    const meanMs = sum / xs.length;
    return {
      frames: xs.length,
      meanMs,
      medianMs: q(0.5),
      p95Ms: q(0.95),
      minMs: xs[0],
      maxMs: xs[xs.length - 1],
      fps: 1000 / meanMs,
    };
  })()`;
  const answer = await send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (answer.result?.exceptionDetails) {
    throw new Error(String(answer.result.exceptionDetails.text ?? 'frame sampling failed'));
  }
  return answer.result?.result?.value ?? null;
}

/** Serve the built client, with the fixture standing in for the world. */
async function serve(port, fixture, session) {
  const { createServer: httpServer } = await import('node:http');
  const server = httpServer((request, response) => {
    const url = (request.url ?? '/').split('?')[0];
    const relative = url.replace(/^\/+/, '') || 'index.html';

    if (relative === 'api/world') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify(fixture.world));
      return;
    }
    if (relative === 'api/session') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify(session));
      return;
    }
    for (const root of [DIST, PUBLIC, FRAMES]) {
      const file = path.resolve(root, relative);
      if (!file.startsWith(path.resolve(root))) continue;
      if (!existsSync(file) || !statSync(file).isFile()) continue;
      response.writeHead(200, {
        'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream',
      });
      createReadStream(file).pipe(response);
      return;
    }
    response.writeHead(404, { 'content-type': 'text/plain' });
    response.end('not found');
  });
  await new Promise((resolve) => server.listen(port, '127.0.0.1', resolve));
  return server;
}

function parseArgs(argv) {
  const args = {
    json: false,
    out: null,
    seed: DEFAULT_SEED,
    armySize: DEFAULT_ARMY_SIZE,
    frames: 240,
    browser: null,
    fixtureOnly: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === '--json') args.json = true;
    else if (flag === '--out') args.out = argv[++i] ?? null;
    else if (flag === '--seed') args.seed = argv[++i] ?? DEFAULT_SEED;
    else if (flag === '--army-size') args.armySize = Number(argv[++i]);
    else if (flag === '--frames') args.frames = Number(argv[++i]);
    else if (flag === '--browser') args.browser = argv[++i] ?? null;
    else if (flag === '--fixture-only') args.fixtureOnly = true;
    else if (flag === '--help' || flag === '-h') args.help = true;
    else throw new Error(`unknown argument: ${flag}`);
  }
  if (!Number.isInteger(args.armySize) || args.armySize < 1) {
    throw new Error('--army-size must be a positive integer');
  }
  if (!Number.isInteger(args.frames) || args.frames < 10) {
    throw new Error('--frames must be an integer of at least 10');
  }
  return args;
}

/** Write the report and present it the same way for every outcome. */
async function finish(report, args) {
  if (report.status !== 'MEASURED') {
    report.note = 'NOT A PERFORMANCE RESULT: no frame timing was measured.';
  }
  if (args.out) {
    await (await import('node:fs/promises')).writeFile(
      path.resolve(args.out),
      `${JSON.stringify(report, null, 2)}\n`,
      'utf8',
    );
  }
  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  console.log('GPU benchmark');
  console.log(`  nvidia-smi: ${report.detection.nvidiaSmi.available ? report.detection.nvidiaSmi.gpus.join('; ') : 'not available'}`);
  console.log(`  system GPUs: ${report.detection.systemGpus.names.join('; ') || 'none reported'}`);
  console.log(`  browser renderer: ${report.detection.browser?.renderer ?? 'unavailable'}`);
  console.log(`  accelerated: ${report.detection.accelerated}`);
  if (report.status === 'MEASURED') {
    const m = report.measurement;
    console.log(`  frames: ${m.frames}`);
    console.log(`  mean: ${m.meanMs.toFixed(3)} ms  median: ${m.medianMs.toFixed(3)} ms  p95: ${m.p95Ms.toFixed(3)} ms`);
    console.log(`  fps (from mean): ${m.fps.toFixed(2)}`);
    console.log('  These are frame timings on this host only, not a release performance result.');
  } else {
    console.log(`  SKIPPED (${report.reason})`);
    console.log(`  ${report.note}`);
    for (const warning of report.warnings) console.log(`  - ${warning}`);
  }
  if (args.out) console.log(`  report written to ${path.resolve(args.out)}`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node scripts/gpu-benchmark.mjs [--json] [--out <file>] [--fixture-only]');
    console.log('       [--seed <s>] [--army-size <n>] [--frames <n>] [--browser chrome|edge]');
    return;
  }

  if (!existsSync(BUNDLE)) {
    throw new Error('the content bundle is missing: run pnpm build:content first');
  }
  const content = JSON.parse(await (await import('node:fs/promises')).readFile(BUNDLE, 'utf8')).items;
  const fixture = createBattleFixture({
    seed: args.seed,
    content,
    armySize: args.armySize,
  });

  const report = {
    schemaVersion: 1,
    tool: 'scripts/gpu-benchmark.mjs',
    fixture: {
      seed: fixture.seed,
      armySize: fixture.armySize,
      combatantCount: fixture.combatantCount,
      fingerprint: fixture.fingerprint,
    },
    detection: {
      nvidiaSmi: nvidiaDetection(),
      systemGpus: systemGpuDetection(),
      browser: null,
      accelerated: false,
    },
    status: 'SKIPPED',
    reason: null,
    performanceResult: false,
    measurement: null,
    warnings: [],
  };

  if (args.fixtureOnly) {
    report.reason = 'FIXTURE_ONLY';
    report.warnings.push('no browser was opened and no frames were measured');
    return finish(report, args);
  }

  const browser = findBrowser(args.browser);
  if (!browser) {
    report.reason = 'NO_BROWSER';
    report.warnings.push('no Chrome or Edge installation was found; WebGL cannot be probed');
    return finish(report, args);
  }

  // The browser's debugging port and the static server's port must differ:
  // they are two different listeners on the same loopback address.
  const port = 9600 + Math.floor(Math.random() * 200);
  const serverPort = port + 1000;
  const child = launchBrowser(browser, port);
  let server = null;
  let session = null;
  try {
    const version = await waitForDevTools(port);
    session = await openSession(port, 'about:blank');
    const probe = await session.send('Runtime.evaluate', {
      expression: RENDERER_EXPRESSION,
      returnByValue: true,
    });
    const info = probe.result?.result?.value ?? {};
    const classification = classifyRenderer(info.renderer ?? null);
    report.detection.browser = {
      name: browser.name,
      path: browser.path,
      version: version.Browser,
      ...info,
      classification: classification.kind,
    };
    report.detection.accelerated = classification.accelerated;

    if (!classification.accelerated) {
      report.reason = classification.kind === 'none' ? 'NO_WEBGL' : 'NO_HARDWARE_ACCELERATION';
      report.warnings.push(
        `the browser renderer is ${info.renderer ?? 'unavailable'}; no frame loop was run`,
      );
      return finish(report, args);
    }

    // Acceleration exists, but a frame number needs the real built client.
    if (!existsSync(INDEX)) {
      report.reason = 'CLIENT_NOT_BUILT';
      report.warnings.push(
        'the browser is accelerated but apps/client/dist/index.html is missing; ' +
          'run pnpm --filter @swl/app-client build',
      );
      return finish(report, args);
    }

    const url = `http://127.0.0.1:${serverPort}/`;
    // A fixed, far-future expiry keeps the harness deterministic: it does not
    // depend on the wall clock, and the client accepts the session.
    const stubSession = {
      token: 'gpu-benchmark-token',
      playerId: 'gpu-benchmark',
      issuedAt: 1,
      expiresAt: 4102444800, // 2100-01-01
    };
    server = await serve(serverPort, fixture, stubSession);

    // The probe tab was opened at about:blank (it needs no origin). Navigate
    // it to the served client before touching localStorage.
    await session.send('Page.navigate', { url });
    await waitForThePage(session.send, url);
    await session.send('Runtime.evaluate', {
      expression: `window.localStorage.setItem('swl.session', ${JSON.stringify(
        JSON.stringify({
          token: stubSession.token,
          playerId: stubSession.playerId,
          expiresAt: stubSession.expiresAt,
        }),
      )})`,
      returnByValue: true,
    });
    await session.send('Page.reload', {});
    await waitForThePage(session.send, url);

    const started = await waitForClient(session.send);
    if (!started.started) {
      report.reason = 'CLIENT_DID_NOT_START';
      report.warnings.push(`the client's status was ${started.status}`);
      return finish(report, args);
    }

    // Re-read the renderer **in the client page**: a tab can fall back to a
    // software renderer after navigation, and that would invalidate the run.
    const pageProbe = await session.send('Runtime.evaluate', {
      expression: RENDERER_EXPRESSION,
      returnByValue: true,
    });
    const pageInfo = pageProbe.result?.result?.value ?? {};
    const pageClass = classifyRenderer(pageInfo.renderer ?? null);
    report.detection.browser.clientPage = {
      renderer: pageInfo.renderer ?? null,
      classification: pageClass.kind,
    };
    if (!pageClass.accelerated) {
      report.reason = 'RENDERER_CHANGED';
      report.warnings.push(
        `the client page renderer became ${pageInfo.renderer ?? 'unavailable'}; no frame loop was run`,
      );
      return finish(report, args);
    }

    const sampled = await measureFrames(session.send, args.frames);
    if (!sampled || sampled.frames < 10) {
      report.reason = 'SAMPLING_FAILED';
      report.warnings.push('the page did not deliver enough animation frames');
      return finish(report, args);
    }

    report.status = 'MEASURED';
    report.reason = 'HARDWARE_ACCELERATION';
    report.measurement = {
      ...sampled,
      clientStatus: started.status,
      renderer: pageInfo.renderer,
      note: 'requestAnimationFrame deltas on this host only; not a release performance result',
    };
  } finally {
    if (session) await session.close().catch(() => {});
    if (server) server.close();
    child.kill();
  }

  return finish(report, args);
}

main().catch((error) => {
  console.error(`gpu-benchmark: ${String(error)}`);
  process.exit(1);
});
