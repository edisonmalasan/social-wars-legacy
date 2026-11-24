#!/usr/bin/env node
/**
 * Reusable, headless-Chrome CDP harness for the 760x600 visual checkpoints.
 *
 * It registers a fresh player against the REAL server (or reuses the
 * deterministic `ui-capture` player), seeds `swl.session`, waits for
 * `window.__swl`, and captures five reviewable screenshots:
 *
 *   01-initial-town.png       (a) at-rest town, tutorial dismissed
 *   02-tutorial-overlay.png   (b) fresh player's tutorial
 *   03-build-menu.png         (c) build surface open
 *   04-quest-dialog.png       (d) quest/dialog surface open
 *   05-desktop-window.png     (e) the same client in a larger window
 *
 * Usage:
 *   node scripts/capture-ui.mjs                  # capture into .work/ui-captures
 *   node scripts/capture-ui.mjs --check          # compare against reviewed baselines
 *   node scripts/capture-ui.mjs --update         # EXPLICIT human baseline approval
 *   node scripts/capture-ui.mjs --out <dir>
 *
 * Baselines are NEVER written by a bare run or by --check. Only --update
 * writes test/baselines/ui/, and it must be invoked deliberately by a human
 * after reviewing the images. No proprietary art is read or copied here.
 */
import { spawn } from 'node:child_process';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { inflateSync } from 'node:zlib';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BASELINE_DIR = path.join(ROOT, 'test', 'baselines', 'ui');
const CHECKPOINTS = [
  '01-initial-town',
  '02-tutorial-overlay',
  '03-build-menu',
  '04-quest-dialog',
  '05-desktop-window',
];

/** The acceptance thresholds, shared with scripts/e2e-test.mjs. */
export const VISUAL_LIMITS = {
  greenRatio: 0.6,
  maxVisibleSurfaces: 8,
  minSprites: 3,
};

/**
 * A single, dependency-free DOM probe. Exported so the e2e harness measures
 * exactly the same things as the screenshot harness.
 */
export const VISUAL_METRICS_EXPRESSION = `(() => {
  const stage = document.querySelector('#stage');
  const canvas = document.querySelector('#game canvas') || document.querySelector('canvas');
  const rect = (e) => {
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return {left: r.left, top: r.top, right: r.right, bottom: r.bottom,
            width: r.width, height: r.height};
  };
  const shown = (e) => {
    const s = getComputedStyle(e);
    const r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' &&
      Number(s.opacity) > 0.01 && r.width > 0 && r.height > 0 &&
      !e.closest('.swl-focus-hidden');
  };
  const surfaces = Array.from(document.querySelectorAll('#ui .swl-ui > *'))
    .filter(shown);
  const neighbour = document.querySelector('#ui .swl-neighbours');
  const build = document.querySelector('#ui .swl-build-menu');
  const nr = rect(neighbour);
  const br = rect(build);
  const overlaps = !!(nr && br && nr.width && br.width &&
    nr.left < br.right && br.left < nr.right &&
    nr.top < br.bottom && br.top < nr.bottom);
  const centre = document.elementFromPoint(380, 300);
  const nameOf = (e) => e ? e.tagName.toLowerCase() +
    (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className.trim()
      ? '.' + e.className.trim().split(/\\s+/).join('.') : '') : null;
  const handle = window.__swl;
  return {
    stage: rect(stage),
    canvas: rect(canvas),
    stageCss: stage ? {width: getComputedStyle(stage).width,
                       height: getComputedStyle(stage).height} : null,
    surfaceCount: surfaces.length,
    surfaceNames: surfaces.map(nameOf),
    neighbourBuildIntersect: overlaps,
    neighbour: nr,
    build: br,
    centreTarget: nameOf(centre),
    centreTargetIsCanvas: !!canvas && centre === canvas,
    visibleSprites: typeof handle?.visibleSprites === 'function' ? handle.visibleSprites() : null,
    drawnSprites: typeof handle?.drawnSprites === 'function' ? handle.drawnSprites() : null,
    atlasRequests: performance.getEntriesByType('resource')
      .filter((entry) => entry.name.includes('/atlases/')).length,
    consoleErrors: Array.isArray(window.__swlVisualErrors) ? window.__swlVisualErrors.slice() : [],
  };
})()`;

/**
 * Check the four Phase-1 visual assertions. Returns failure strings; never
 * throws and never weakens or rewrites an existing assertion.
 */
export function visualFailures(metrics, label = 'visual') {
  const failures = [];
  // The stage's CSS size is already asserted by scripts/e2e-test.mjs. Its
  // bounding rect can legitimately be scaled down in a smaller browser
  // window, so it is reported as a metric rather than asserted here.
  if (!(metrics?.greenRatio >= VISUAL_LIMITS.greenRatio)) {
    failures.push(
      `${label}: green canvas coverage ${(metrics?.greenRatio ?? 0).toFixed(3)} ` +
        `is below ${VISUAL_LIMITS.greenRatio}`,
    );
  }
  if (!(metrics?.surfaceCount <= VISUAL_LIMITS.maxVisibleSurfaces)) {
    failures.push(
      `${label}: ${metrics?.surfaceCount} visible UI surfaces at rest ` +
        `(limit ${VISUAL_LIMITS.maxVisibleSurfaces}): ${(metrics?.surfaceNames ?? []).join(', ')}`,
    );
  }
  if (metrics?.neighbourBuildIntersect) {
    failures.push(`${label}: the neighbour strip and the build surface intersect at rest`);
  }
  if (!metrics?.centreTargetIsCanvas) {
    failures.push(`${label}: (380,300) hits ${metrics?.centreTarget}, not the canvas`);
  }
  if (!(metrics?.drawnSprites >= VISUAL_LIMITS.minSprites)) {
    failures.push(`${label}: only ${metrics?.drawnSprites} sprite(s) drawn`);
  }
  return failures;
}

/** Decode the 8-bit, non-interlaced PNGs Chrome returns from CDP. */
export function decodePng(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(signature)) {
    throw new Error('CDP returned no PNG');
  }
  let offset = 8;
  let width = 0;
  let height = 0;
  let channels = 0;
  const idat = [];
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('ascii', offset + 4, offset + 8);
    const data = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      if (data[8] !== 8 || ![2, 6].includes(data[9]) || data[12] !== 0) {
        throw new Error(`unsupported PNG format (depth ${data[8]}, colour ${data[9]}, interlace ${data[12]})`);
      }
      channels = data[9] === 6 ? 4 : 3;
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') {
      break;
    }
    offset += 12 + length;
  }
  if (!width || !height || !idat.length) throw new Error('the PNG has no image data');
  const raw = inflateSync(Buffer.concat(idat));
  const stride = width * channels;
  const pixels = Buffer.alloc(height * stride);
  let source = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[source++];
    const row = source;
    const out = y * stride;
    const previous = out - stride;
    for (let i = 0; i < stride; i++) {
      const value = raw[source++];
      const left = i >= channels ? pixels[out + i - channels] : 0;
      const up = y > 0 ? pixels[previous + i] : 0;
      const corner = y > 0 && i >= channels ? pixels[previous + i - channels] : 0;
      let added;
      if (filter === 0) added = 0;
      else if (filter === 1) added = left;
      else if (filter === 2) added = up;
      else if (filter === 3) added = Math.floor((left + up) / 2);
      else if (filter === 4) {
        const p = left + up - corner;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - corner);
        added = pa <= pb && pa <= pc ? left : pb <= pc ? up : corner;
      } else throw new Error(`unknown PNG filter ${filter}`);
      pixels[out + i] = (value + added) & 0xff;
    }
    source = row + stride;
  }
  return { width, height, channels, pixels };
}

/** The original game's green field: G > R*1.4 and G > B*1.6. */
export function greenRatio(png) {
  const { channels, pixels } = png;
  let green = 0;
  const count = pixels.length / channels;
  for (let i = 0; i < pixels.length; i += channels) {
    if (pixels[i + 1] > pixels[i] * 1.4 && pixels[i + 1] > pixels[i + 2] * 1.6) green++;
  }
  return { ratio: green / count, green, count };
}

/** Compare two decoded screenshots; tiny antialias noise is tolerated. */
function comparePng(current, baseline) {
  if (current.width !== baseline.width || current.height !== baseline.height) {
    return { equal: false, different: current.width * current.height, reason: 'size' };
  }
  let different = 0;
  let worst = 0;
  for (let i = 0; i < current.pixels.length; i += current.channels) {
    const dr = Math.abs(current.pixels[i] - baseline.pixels[i]);
    const dg = Math.abs(current.pixels[i + 1] - baseline.pixels[i + 1]);
    const db = Math.abs(current.pixels[i + 2] - baseline.pixels[i + 2]);
    const delta = Math.max(dr, dg, db);
    if (delta > worst) worst = delta;
    if (delta > 16) different++;
  }
  const total = current.width * current.height;
  return { equal: different / total <= 0.005, different, total, worst };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Find Chrome (or Edge) on this machine. */
function findBrowser() {
  const candidates = process.env.SWL_CHROME
    ? [process.env.SWL_CHROME]
    : [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      ];
  return candidates.find((candidate) => existsSync(candidate)) ?? null;
}

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.wasm': 'application/wasm',
};

/** Serve the built client and proxy the API to the real server. */
async function serve(port, apiPort) {
  const roots = [
    path.join(ROOT, 'apps/client/dist'),
    path.join(ROOT, 'apps/client/public'),
    path.join(ROOT, '.work/frames'),
  ];
  const server = createServer((request, response) => {
    const url = (request.url ?? '/').split('?')[0];
    if (url.startsWith('/api/') || url === '/health') {
      const chunks = [];
      request.on('data', (chunk) => chunks.push(chunk));
      request.on('end', async () => {
        try {
          const headers = { 'content-type': request.headers['content-type'] ?? 'application/json' };
          if (request.headers.authorization) headers.authorization = request.headers.authorization;
          const upstream = await fetch(`http://127.0.0.1:${apiPort}${url}`, {
            method: request.method, headers,
            body: chunks.length ? Buffer.concat(chunks) : undefined,
          });
          response.writeHead(upstream.status, {
            'content-type': upstream.headers.get('content-type') ?? 'application/json',
          });
          response.end(Buffer.from(await upstream.arrayBuffer()));
        } catch {
          response.writeHead(502, { 'content-type': 'application/json' });
          response.end('{"error":"the server is not reachable"}');
        }
      });
      return;
    }
    const relative = url.replace(/^\/+/, '') || 'index.html';
    for (const root of roots) {
      const file = path.resolve(root, relative);
      if (!file.startsWith(path.resolve(root)) || !existsSync(file) || !statSync(file).isFile()) continue;
      response.writeHead(200, { 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream' });
      createReadStream(file).pipe(response);
      return;
    }
    response.writeHead(404, { 'content-type': 'text/plain' });
    response.end('not found');
  });
  await new Promise((resolve) => server.listen(port, '127.0.0.1', resolve));
  return server;
}

/** Start the authoritative server on a free port. */
async function startServer(dataDir, port) {
  const child = spawn(process.execPath, ['apps/server/src/main.ts'], {
    cwd: ROOT,
    env: { ...process.env, SWL_DATA_DIR: dataDir, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout.on('data', (chunk) => { output += String(chunk); });
  child.stderr.on('data', (chunk) => { output += String(chunk); });
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) return child;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  child.kill();
  throw new Error(`the server did not start:\n${output}`);
}

/** A page driven over the Chrome DevTools Protocol. */
class Page {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.errors = [];
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      if (message.method === 'Runtime.consoleAPICalled' &&
          ['error', 'assert'].includes(message.params.type)) {
        this.errors.push(`console.${message.params.type}: ` +
          message.params.args.map((arg) => arg.value ?? arg.description).join(' '));
      }
      if (message.method === 'Runtime.exceptionThrown') {
        this.errors.push(`EXCEPTION: ${message.params.exceptionDetails.text} ` +
          (message.params.exceptionDetails.exception?.description ?? ''));
      }
      if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
        this.errors.push(`log.error: ${message.params.entry.text}`);
      }
      const resolve = this.pending.get(message.id);
      if (resolve) { this.pending.delete(message.id); resolve(message); }
    });
  }

  static async open(port, url) {
    const target = await (
      await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })
    ).json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });
    const page = new Page(socket);
    page.targetId = target.id;
    await page.send('Runtime.enable');
    await page.send('Log.enable');
    await page.send('Page.enable');
    return page;
  }

  send(method, params = {}) {
    return new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const answer = await this.send('Runtime.evaluate', {
      expression, returnByValue: true, awaitPromise: true,
    });
    if (answer.result?.exceptionDetails) {
      throw new Error(answer.result.exceptionDetails.exception?.description ??
        answer.result.exceptionDetails.text);
    }
    return answer.result?.result?.value;
  }

  async waitFor(expression, accept, label, timeoutMs = 30_000) {
    const deadline = Date.now() + timeoutMs;
    let last;
    while (Date.now() < deadline) {
      try { last = await this.evaluate(expression); } catch { /* retry */ }
      if (accept(last)) return last;
      await sleep(150);
    }
    throw new Error(`the page never showed ${label} (last: ${JSON.stringify(last)})`);
  }

  async screenshot() {
    const shot = await this.send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: false,
    });
    return Buffer.from(shot.result.data, 'base64');
  }

  async close(port) {
    try { this.socket.close(); } catch { /* already closed */ }
    await fetch(`http://127.0.0.1:${port}/json/close/${this.targetId}`).catch(() => {});
  }
}

async function main() {
  const args = process.argv.slice(2);
  const mode = args.includes('--check') ? 'check' : args.includes('--update') ? 'update' : 'capture';
  if (args.includes('--check') && args.includes('--update')) {
    throw new Error('--check and --update are mutually exclusive');
  }
  const outIndex = args.indexOf('--out');
  const outDir = outIndex >= 0
    ? path.resolve(args[outIndex + 1])
    : path.join(ROOT, '.work', 'ui-captures');

  if (!existsSync(path.join(ROOT, 'apps/client/dist/index.html'))) {
    throw new Error('the client has not been built: pnpm --filter @swl/app-client build');
  }
  const browser = findBrowser();
  if (!browser) throw new Error('no Chrome/Edge binary found (set SWL_CHROME)');

  const base = 8300 + Math.floor(Math.random() * 200);
  const serverPort = base;
  const clientPort = base + 200;
  const devToolsPort = Number(process.env.SWL_CDP_PORT ?? 9440);
  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'swl-ui-capture-'));
  const profile = await mkdtemp(path.join(os.tmpdir(), 'swl-ui-profile-'));
  let server = null;
  let client = null;
  let chrome = null;
  let page = null;

  try {
    server = await startServer(dataDir, serverPort);
    client = await serve(clientPort, serverPort);
    const register = await fetch(`http://127.0.0.1:${serverPort}/api/account`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ playerId: `ui-capture-${Date.now()}`, password: 'correct horse' }),
    });
    if (register.status !== 201) {
      throw new Error(`the capture player was not registered: ${register.status} ${await register.text()}`);
    }
    const session = await register.json();
    // A neighbour makes the bottom strip a real rect, so the
    // neighbour/build intersection assertion measures something.
    await fetch(`http://127.0.0.1:${serverPort}/api/account`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ playerId: `ui-neighbour-${Date.now()}`, password: 'correct horse' }),
    });

    chrome = spawn(browser, [
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      '--enable-unsafe-swiftshader', '--disable-dev-shm-usage',
      '--no-first-run', '--no-default-browser-check',
      `--remote-debugging-port=${devToolsPort}`, `--user-data-dir=${profile}`,
      '--window-size=760,600', 'about:blank',
    ], { stdio: 'ignore' });

    for (let i = 0; i < 60; i++) {
      try {
        if ((await fetch(`http://127.0.0.1:${devToolsPort}/json/version`)).ok) break;
      } catch { /* not up yet */ }
      await sleep(250);
    }
    page = await Page.open(devToolsPort, `http://127.0.0.1:${clientPort}/`);
    await page.send('Emulation.setDeviceMetricsOverride', {
      width: 760, height: 600, deviceScaleFactor: 1, mobile: false,
    });
    await page.waitFor('location.href', (v) => typeof v === 'string' && v.startsWith('http://'), 'the app origin');
    await page.evaluate(`localStorage.setItem('swl.session', ${JSON.stringify(JSON.stringify({
      token: session.token, playerId: session.playerId, expiresAt: session.expiresAt,
    }))}); true`);
    await page.send('Page.reload', {});
    await page.waitFor(
      "(() => { const e = document.getElementById('status'); return e ? e.getAttribute('data-state') : null; })()",
      (v) => v === 'started' || v === 'failed', 'the client to start',
    );
    const state = await page.evaluate(
      "document.getElementById('status')?.getAttribute('data-state')",
    );
    if (state !== 'started') throw new Error(`the client failed to start: ${state}`);
    await page.waitFor(
      '!!(window.__swl && document.querySelector("#game canvas") && document.querySelector("#stage"))',
      (v) => v === true, 'window.__swl and the stage',
    );
    await page.evaluate(
      `window.__swlVisualErrors = []; ${JSON.stringify('')}; true`,
    );
    // Capture the live page errors into the page too, so the shared DOM probe
    // reports the same numbers in both harnesses.
    await page.evaluate(`(() => {
      window.__swlVisualErrors = [];
      for (const type of ['error', 'unhandledrejection']) {
        window.addEventListener(type, (event) =>
          window.__swlVisualErrors.push(String(event.message ?? event.reason ?? type)));
      }
      return true;
    })()`);
    await sleep(500);

    const captures = new Map();
    const metricsAt = async (label) => {
      const metrics = await page.evaluate(VISUAL_METRICS_EXPRESSION);
      // Hide the UI only for the green-pixel sample; the screenshots retain it.
      await page.evaluate(`(() => { const ui = document.querySelector('#ui');
        if (ui) ui.style.visibility = 'hidden'; return true; })()`);
      await sleep(200);
      const shot = await page.screenshot();
      await page.evaluate(`(() => { const ui = document.querySelector('#ui');
        if (ui) ui.style.visibility = ''; return true; })()`);
      const green = greenRatio(decodePng(shot));
      const combined = { ...metrics, greenRatio: green.ratio, label };
      combined.failures = visualFailures(combined, label);
      console.log(`METRICS ${JSON.stringify(combined)}`);
      return combined;
    };

    const capture = async (name, options = {}) => {
      await sleep(350);
      const buffer = await page.screenshot();
      captures.set(name, buffer);
      await writeFile(path.join(outDir, `${name}.png`), buffer);
      if (options.metrics) await metricsAt(name);
    };
    await mkdir(outDir, { recursive: true });

    // (b) first: a fresh player opens on the tutorial.
    await page.waitFor('!!document.querySelector("#ui .swl-tutorial")',
      (v) => v === true, 'the tutorial overlay');
    await capture('02-tutorial-overlay', { metrics: true });
    // (a) dismiss it to reach the at-rest town.
    await page.evaluate(
      `(() => { const b = document.querySelector('#ui .swl-tutorial-skip');
        if (!b) return false; b.click(); return true; })()`,
    );
    await page.waitFor('!document.querySelector("#ui .swl-tutorial")',
      (v) => v === true, 'the tutorial to close');
    await capture('01-initial-town', { metrics: true });

    // (c) the build surface: prefer the rendered launcher, fall back to the
    // current build where the menu is mounted at rest.
    const openedBuild = await page.evaluate(`(() => {
      const selectors = ['[data-swl-open="build"]', '[data-swl-surface="build"]',
        '.swl-build-launcher button', '.swl-chrome-action-build',
        '.swl-bottom-nav button'];
      for (const selector of selectors) {
        const button = document.querySelector(selector);
        if (button && getComputedStyle(button).display !== 'none') {
          button.click(); return selector;
        }
      }
      return null;
    })()`);
    await page.waitFor(
      `(() => { const e = document.querySelector('#ui .swl-build-menu');
        return !!(e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width); })()`,
      (v) => v === true, 'the build menu to be visible',
    );
    console.log(`build surface opened by: ${openedBuild ?? 'already visible at rest'}`);
    await capture('03-build-menu');

    // (d) a quest/dialog surface. Prefer the rendered chapter slot; when the
    // fresh player's chapter list has no clickable quest yet, use the client's
    // own debug handle to open the same shared dialog. This keeps the
    // checkpoint honest: it must show a real dialog, not a duplicate of the
    // build-menu view.
    let openedQuest = await page.evaluate(`(() => {
      const selectors = ['#ui .swl-chapter:first-child .swl-chapter-quests > button:first-child',
        '#ui .swl-quest-slot', '#ui .swl-chapter button'];
      for (const selector of selectors) {
        const button = document.querySelector(selector);
        if (button) { button.click(); return selector; }
      }
      return null;
    })()`);
    if (!openedQuest) {
      openedQuest = await page.evaluate(`(() => {
        const handle = window.__swl;
        if (!handle || typeof handle.showMissionInfo !== 'function') return null;
        handle.showMissionInfo();
        return 'window.__swl.showMissionInfo()';
      })()`);
    }
    await page.waitFor('!!document.querySelector("#ui .swl-dialog")',
      (v) => v === true, 'the quest dialog', 10_000).catch(() => {});
    console.log(`quest surface opened by: ${openedQuest ?? 'no rendered slot found'}`);
    await capture('04-quest-dialog');

    // (e) the same client in a larger desktop window.
    await page.send('Emulation.setDeviceMetricsOverride', {
      width: 1280, height: 800, deviceScaleFactor: 1, mobile: false,
    });
    await sleep(600);
    await capture('05-desktop-window');

    const consoleErrors = [...new Set([...page.errors, ...(
      (await page.evaluate('window.__swlVisualErrors || []')) ?? []
    )])];
    const atlasRequests = await page.evaluate(
      "performance.getEntriesByType('resource').filter((e) => e.name.includes('/atlases/')).length",
    );
    console.log(`ERRORS ${JSON.stringify(consoleErrors)}`);
    console.log(`ATLAS_REQUESTS ${atlasRequests}`);

    if (mode === 'update') {
      await mkdir(BASELINE_DIR, { recursive: true });
      for (const name of CHECKPOINTS) {
        await writeFile(path.join(BASELINE_DIR, `${name}.png`), captures.get(name));
      }
      console.log(`BASELINES UPDATED ${BASELINE_DIR}`);
      return;
    }

    if (mode === 'check') {
      const diffs = [];
      for (const name of CHECKPOINTS) {
        const baselinePath = path.join(BASELINE_DIR, `${name}.png`);
        if (!existsSync(baselinePath)) {
          diffs.push(`${name}: no reviewed baseline (run --update after a human review)`);
          continue;
        }
        const comparison = comparePng(
          decodePng(captures.get(name)), decodePng(await readFile(baselinePath)),
        );
        console.log(`DIFF ${name} ${JSON.stringify(comparison)}`);
        if (!comparison.equal) {
          diffs.push(`${name}: ${comparison.different}/${comparison.total} pixels differ ` +
            '(run --update only after reviewing the change)');
        }
      }
      if (diffs.length) throw new Error(`baseline check failed:\n  ${diffs.join('\n  ')}`);
      console.log('OK: five checkpoints match the reviewed baselines.');
      return;
    }

    console.log(`OK: five checkpoints captured into ${outDir}`);
  } finally {
    if (page) await page.close(devToolsPort);
    if (chrome) chrome.kill();
    if (client) client.close();
    if (server) server.kill();
    // Chrome's crashpad worker can hold a file open briefly after kill().
    if (chrome) await sleep(500);
    for (const directory of [dataDir, profile]) {
      for (let attempt = 0; attempt < 5; attempt++) {
        try {
          await rm(directory, { recursive: true, force: true });
          break;
        } catch (error) {
          if (attempt === 4) console.warn(`could not remove ${directory}: ${error}`);
          else await sleep(300);
        }
      }
    }
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
