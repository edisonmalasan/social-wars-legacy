#!/usr/bin/env node
/**
 * Multi-resolution emulated-phone layout verification.
 *
 * **This is EMULATION, not device verification.** A real Chromium browser is
 * driven over the DevTools protocol with `Emulation.setDeviceMetricsOverride`
 * (a matrix of CSS-pixel phone viewports plus the original 760x600 stage, each
 * at its own device pixel ratio) and `Emulation.setTouchEmulationEnabled`. No
 * Android/iOS build, emulator, real phone, Firefox or Safari is involved, and
 * nothing here claims any of them ran. No physical touch device is used: the
 * "touch" is a CDP-enabled synthetic `pointerType: 'touch'` gesture.
 *
 * Every viewport in the matrix gets the same assertions as the original
 * single-viewport harness:
 *
 * 1. the client's own status is `started`;
 * 2. the `#stage` transform scale equals `stageScale({width,height})` from the
 *    shared model, read from the running page;
 * 3. the HUD, goals, inventory and chapter panels are inside the stage and do
 *    not overlap one another;
 * 4. `window.__swl.visibleSprites()` is positive;
 * 5. a touch tap (pointerdown then pointerup) on the canvas selects a building.
 *
 * A browser that is not installed is reported as **NOT RUN**, not as a
 * failure. The script fails only when a drivable browser fails an assertion,
 * or when no browser ran at all — the same rule as the existing harnesses.
 *
 * Usage:
 *   node scripts/e2e-mobile-layout.mjs
 *   node scripts/e2e-mobile-layout.mjs --browser chrome
 */
import { spawn } from 'node:child_process';
import {
  createReadStream,
  existsSync,
  mkdtempSync,
  statSync,
} from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

import { stageScale } from '../packages/client/src/stage.ts';

const ROOT = process.cwd();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Chrome keeps profile files briefly after exit; retry the temp cleanup. */
async function removeTemp(directory) {
  for (let attempt = 0; attempt < 8; attempt++) {
    try {
      await rm(directory, { recursive: true, force: true });
      return;
    } catch {
      await sleep(250);
    }
  }
}

/**
 * The emulated viewports: several phone sizes plus the game's original
 * 760x600 stage. Each entry is EMULATED in a real browser — never a device.
 * `slug` is used to give each viewport its own server-issued session.
 */
const VIEWPORTS = [
  { name: '390x844 @dpr2', slug: '390x844-2', width: 390, height: 844, deviceScaleFactor: 2 },
  { name: '360x640 @dpr2', slug: '360x640-2', width: 360, height: 640, deviceScaleFactor: 2 },
  { name: '414x896 @dpr3', slug: '414x896-3', width: 414, height: 896, deviceScaleFactor: 3 },
  { name: '320x568 @dpr2', slug: '320x568-2', width: 320, height: 568, deviceScaleFactor: 2 },
  { name: '760x600 @dpr1', slug: '760x600-1', width: 760, height: 600, deviceScaleFactor: 1 },
];

/** The panels whose layout is checked inside the stage. */
const PANELS = [
  ['hud', '#ui .swl-hud'],
  ['goals', '#ui .swl-goals'],
  ['inventory', '#ui .swl-inventory'],
  ['chapters', '#ui .swl-chapters'],
];

/** Where the browsers are looked for (the same table as e2e-test.mjs). */
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

const ROOTS = [
  path.join(ROOT, 'apps/client/dist'),
  path.join(ROOT, 'apps/client/public'),
  path.join(ROOT, '.work/frames'),
];

function findBrowser(name) {
  const entry = BROWSERS.find((browser) => browser.name === name);
  if (!entry) return null;
  for (const candidate of entry.paths) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/**
 * Take a currently-free localhost port. Nothing about a run is on a fixed
 * port (the old harness hardcoded DevTools to 9544): the server, the client
 * proxy and each browser's debugging endpoint get their own, so concurrent
 * browser runs — and the other harnesses — cannot collide.
 */
const usedPorts = new Set();
async function nextPort() {
  for (;;) {
    const probe = createServer();
    await new Promise((resolve) => probe.listen(0, '127.0.0.1', resolve));
    const address = probe.address();
    await new Promise((resolve) => probe.close(resolve));
    if (!address || typeof address === 'string' || usedPorts.has(address.port)) continue;
    usedPorts.add(address.port);
    return address.port;
  }
}

/** Static files for the client, with the API proxied to the real server. */
async function serve(port, apiPort) {
  const server = createServer((request, response) => {
    const url = (request.url ?? '/').split('?')[0];
    if (url.startsWith('/api/') || url === '/health') {
      const chunks = [];
      request.on('data', (chunk) => chunks.push(chunk));
      request.on('end', async () => {
        try {
          const headers = {
            'content-type': request.headers['content-type'] ?? 'application/json',
          };
          if (request.headers['authorization']) {
            headers.authorization = request.headers['authorization'];
          }
          const upstream = await fetch(`http://127.0.0.1:${apiPort}${url}`, {
            method: request.method,
            headers,
            body: chunks.length ? Buffer.concat(chunks) : undefined,
          });
          response.writeHead(upstream.status, {
            'content-type': upstream.headers.get('content-type') ?? 'application/json',
          });
          response.end(Buffer.from(await upstream.arrayBuffer()));
        } catch {
          response.writeHead(502, { 'content-type': 'application/json' });
          response.end(JSON.stringify({ error: 'the server is not reachable' }));
        }
      });
      return;
    }
    const relative = url.replace(/^\/+/, '') || 'index.html';
    for (const root of ROOTS) {
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

async function waitForDevTools(port, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return;
    } catch {
      // Not up yet.
    }
    await sleep(150);
  }
  throw new Error('the browser did not open its debugging port');
}

/** A page, driven over the DevTools protocol (the e2e-test.mjs pattern). */
class Page {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      const resolver = this.pending.get(message.id);
      if (resolver) {
        this.pending.delete(message.id);
        resolver(message);
      }
    });
  }

  static async openBlank(devToolsPort) {
    const target = await (
      await fetch(`http://127.0.0.1:${devToolsPort}/json/new?about:blank`, {
        method: 'PUT',
      })
    ).json();
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });
    const page = new Page(socket);
    page.targetId = target.id;
    await page.send('Runtime.enable', {});
    await page.send('Page.enable', {});
    return page;
  }

  send(method, params) {
    return new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const answer = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (answer.result?.exceptionDetails) {
      throw new Error(
        answer.result.exceptionDetails.exception?.description ??
          answer.result.exceptionDetails.text,
      );
    }
    return answer.result?.result?.value;
  }

  /** Poll the address/document, as the existing harness does. */
  async waitForLoad(timeoutMs = 30_000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      try {
        const where = await this.evaluate('location.href');
        if (typeof where === 'string' && where.startsWith('http://127.0.0.1:')) {
          const state = await this.evaluate('document.readyState');
          if (state === 'complete' || state === 'interactive') return;
        }
      } catch {
        // The document is not there yet.
      }
      await sleep(100);
    }
    throw new Error('the page did not load');
  }

  /** Reload and wait for the new document. */
  async reload() {
    await this.send('Page.reload', {});
    await this.waitForLoad();
  }

  async waitForStatus(states, timeoutMs = 60_000) {
    const deadline = Date.now() + timeoutMs;
    let last = '';
    while (Date.now() < deadline) {
      last = await this.evaluate(
        "(() => { const e = document.getElementById('status');" +
          " return e ? e.getAttribute('data-state') + '|' + e.textContent : 'missing'; })()",
      );
      const state = String(last).split('|')[0];
      if (states.includes(state)) return String(last);
      await sleep(200);
    }
    return String(last);
  }

  async close(devToolsPort) {
    try {
      this.socket.close();
    } catch {
      // Already closed.
    }
    await fetch(`http://127.0.0.1:${devToolsPort}/json/close/${this.targetId}`).catch(
      () => {},
    );
  }
}

/** Start the real server the emulated client talks to. */
async function startServer(dataDir, port) {
  const env = { ...process.env, SWL_DATA_DIR: dataDir, PORT: String(port) };
  const child = spawn(process.execPath, ['apps/server/src/main.ts'], {
    cwd: ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let output = '';
  child.stdout.on('data', (chunk) => { output += String(chunk); });
  child.stderr.on('data', (chunk) => { output += String(chunk); });
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`);
      if (response.ok) return child;
    } catch {
      // Not up yet.
    }
    await sleep(200);
  }
  child.kill();
  throw new Error(`the server did not start:\n${output}`);
}

async function register(port, playerId) {
  const response = await fetch(`http://127.0.0.1:${port}/api/account`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playerId, password: 'correct horse' }),
  });
  if (response.status !== 201) {
    throw new Error(`the account was not created: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

/** Two rectangles overlap when neither is entirely to one side of the other. */
function overlaps(a, b) {
  return !(
    a.right <= b.left + 0.5 ||
    b.right <= a.left + 0.5 ||
    a.bottom <= b.top + 0.5 ||
    b.bottom <= a.top + 0.5
  );
}

/** Read the emulated page's geometry, in CSS pixels after the stage transform. */
async function readGeometry(page) {
  return page.evaluate(
    `(() => {
       const rect = (selector) => {
         const e = document.querySelector(selector);
         if (!e) return null;
         const r = e.getBoundingClientRect();
         return {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
       };
       const stage = document.querySelector('#stage');
       return {
         innerWidth: window.innerWidth,
         innerHeight: window.innerHeight,
         dpr: window.devicePixelRatio,
         transform: stage ? getComputedStyle(stage).transform : null,
         stage: rect('#stage'),
         panels: {
           hud: rect('#ui .swl-hud'),
           goals: rect('#ui .swl-goals'),
           inventory: rect('#ui .swl-inventory'),
           chapters: rect('#ui .swl-chapters'),
         },
       };
     })()`,
  );
}

/** All the phone assertions for one drivable browser and one emulated viewport. */
async function verifyEmulatedPhone(page, name, serverPort, session, failures, viewport) {
  const label = `${name} ${viewport.name}`;
  const expectedScale = stageScale({ width: viewport.width, height: viewport.height });
  const fail = (message) => {
    failures.push(`${label}: ${message}`);
    console.log(`  FAILED (${message})`);
  };

  // The client signs in with the session the real server issued.
  await page.evaluate(
    `window.localStorage.setItem('swl.session', ${JSON.stringify(
      JSON.stringify({
        token: session.token,
        playerId: session.playerId,
        expiresAt: session.expiresAt,
      }),
    )})`,
  );
  await page.reload();

  // 1. The client's own status.
  const status = await page.waitForStatus(['started', 'failed']);
  const [state, detail = ''] = String(status).split('|');
  if (state !== 'started') {
    fail(`the client said "${state}" (${detail})`);
    return;
  }
  console.log(`  EMULATION ${label}: client status started (${detail})`);

  // The fresh player's tutorial is closed through its rendered button, so
  // the layout measured below is the ordinary play layout, not the overlay.
  const skipped = await page.evaluate(
    `(() => {
       const button = document.querySelector('#ui .swl-tutorial-skip');
       if (!button) return true;
       button.click();
       return true;
     })()`,
  );
  if (!skipped) {
    fail('the rendered tutorial Skip button could not be clicked');
    return;
  }
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline && await page.evaluate("!!document.querySelector('#ui .swl-tutorial')")) {
    await sleep(100);
  }
  if (await page.evaluate("!!document.querySelector('#ui .swl-tutorial')")) {
    fail('the tutorial overlay did not close');
    return;
  }

  // 2. The emulated viewport is really in force, and the stage scale is the
  //    shared model's answer for it. The scale is the `a` term of the CSS
  //    matrix the renderer wrote; the model is imported from stage.ts.
  const geometry = await readGeometry(page);
  if (geometry?.innerWidth !== viewport.width || geometry?.innerHeight !== viewport.height) {
    fail(
      `the browser reported ${geometry?.innerWidth}x${geometry?.innerHeight}, ` +
        `not ${viewport.width}x${viewport.height}`,
    );
    return;
  }
  if (Number(geometry.dpr) !== viewport.deviceScaleFactor) {
    fail(`the browser reported dpr ${geometry.dpr}, not ${viewport.deviceScaleFactor}`);
    return;
  }
  const match = /matrix\(\s*([-\d.]+)/.exec(String(geometry.transform ?? ''));
  const applied = match ? Number(match[1]) : NaN;
  if (!Number.isFinite(applied) || Math.abs(applied - expectedScale) > 0.001) {
    fail(
      `the #stage transform scale is ${String(geometry.transform)}, ` +
        `but stageScale({${viewport.width},${viewport.height}}) is ${expectedScale}`,
    );
    return;
  }
  console.log(
    `  EMULATION ${label}: ${geometry.innerWidth}x${geometry.innerHeight} @dpr ${geometry.dpr}; ` +
      `#stage scale ${applied} = stageScale({${viewport.width},${viewport.height}}) ${expectedScale}`,
  );

  // 3. Every named panel is inside the transformed stage and the four do not
  //    overlap one another. Rectangles are read from the live page, so this is
  //    the emulated layout and not an assumption from the CSS.
  if (!geometry.stage) {
    fail('the #stage element is missing');
    return;
  }
  const rects = [];
  for (const [panel, selector] of PANELS) {
    const rect = geometry.panels?.[panel];
    if (!rect) {
      fail(`the ${panel} panel is missing`);
      return;
    }
    if (
      rect.left < geometry.stage.left - 0.5 ||
      rect.top < geometry.stage.top - 0.5 ||
      rect.right > geometry.stage.right + 0.5 ||
      rect.bottom > geometry.stage.bottom + 0.5
    ) {
      fail(`the ${panel} panel falls outside the stage: ${JSON.stringify(rect)}`);
      return;
    }
    rects.push([panel, rect]);
  }
  for (let i = 0; i < rects.length; i++) {
    for (let j = i + 1; j < rects.length; j++) {
      if (overlaps(rects[i][1], rects[j][1])) {
        fail(
          `the ${rects[i][0]} panel overlaps the ${rects[j][0]} panel: ` +
            `${JSON.stringify(rects[i][1])} / ${JSON.stringify(rects[j][1])}`,
        );
        return;
      }
    }
  }
  console.log(
    `  EMULATION ${label}: hud/goals/inventory/chapters are inside the stage ` +
      `(${geometry.stage.left.toFixed(1)},${geometry.stage.top.toFixed(1)} to ` +
      `${geometry.stage.right.toFixed(1)},${geometry.stage.bottom.toFixed(1)}) and do not overlap`,
  );

  // 4. The town is drawn on the screen at the emulated viewport.
  const visible = await page.evaluate(
    '(() => { const h = window.__swl; return h ? h.visibleSprites() : 0; })()',
  );
  if (!Number.isFinite(Number(visible)) || Number(visible) < 1) {
    fail(`the town is not on the screen (${visible} visible sprite(s))`);
    return;
  }
  console.log(`  EMULATION ${label}: ${visible} sprite(s) visible on the emulated screen`);

  // 5. A touch tap on the canvas selects a building. Touch input is deferred
  //    to release by the shared client's gesture guard, so a real tap is a
  //    pointerdown **and** a pointerup with pointerType 'touch'. The bare
  //    pointerdown must not select on its own: that is the duplicate-command
  //    guard, not a missing assertion.
  const picked = await page.evaluate(
    `(() => {
       const canvas = document.querySelector('#game canvas');
       if (!canvas) return {error: 'the client has no canvas'};
       const rect = canvas.getBoundingClientRect();
       const x = rect.left + rect.width / 2;
       const y = rect.top + rect.height / 2;
       const base = {
         clientX: x, clientY: y, bubbles: true, cancelable: true,
         pointerId: 7, isPrimary: true, pointerType: 'touch',
       };
       const handle = window.__swl;
       const before = handle ? handle.selectedItem() : null;
       canvas.dispatchEvent(new PointerEvent('pointerdown', base));
       const afterDown = handle ? handle.selectedItem() : null;
       canvas.dispatchEvent(new PointerEvent('pointerup', base));
       const afterUp = handle ? handle.selectedItem() : null;
       return {before, afterDown, afterUp};
     })()`,
  );
  if (!picked || picked.error) {
    fail(picked?.error ?? 'the touch gesture did not answer');
    return;
  }
  if (!Number.isInteger(picked.afterUp)) {
    fail(`the touch tap selected no building: ${JSON.stringify(picked)}`);
    return;
  }
  if (picked.before === null && picked.afterDown !== null) {
    fail(`the touch pointerdown selected before release: ${JSON.stringify(picked)}`);
    return;
  }
  console.log(
    `  EMULATION ${label}: a touch pointerdown+pointerup selected building item ` +
      `${picked.afterUp} (the pointerdown alone selected ${JSON.stringify(picked.afterDown)})`,
  );

  // The server is still the authority: selection was a read of the client's
  // own world, which was fetched from this server with the issued token.
  const world = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
    headers: { authorization: `Bearer ${session.token}` },
  }).then((response) => response.json());
  if (!world?.maps?.[0]?.items || Object.keys(world.maps[0].items).length === 0) {
    fail('the server did not own the town the emulated client rendered');
    return;
  }
  console.log(`  EMULATION ${label}: the selected town came from the real server's save`);
}

async function main() {
  const only = process.argv.includes('--browser')
    ? process.argv[process.argv.indexOf('--browser') + 1]
    : null;

  if (!existsSync(path.join(ROOT, 'apps/client/dist/index.html'))) {
    console.error('the client has not been built. Run:');
    console.error('  pnpm --filter @swl/app-client build');
    process.exit(2);
  }

  // A distinct temp-data prefix and no fixed ports, so concurrent browser
  // runs (and the other CDP harnesses) cannot collide.
  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'swl-mobile-matrix-'));
  const serverPort = await nextPort();
  const clientPort = await nextPort();
  const server = await startServer(dataDir, serverPort);
  const client = await serve(clientPort, serverPort);

  const failures = [];
  const ran = [];
  const notRun = [];
  const profiles = [];
  const browsers = [];

  console.log('  EMULATION: multi-resolution matrix (CDP device-metrics override, never a device):');
  for (const viewport of VIEWPORTS) {
    console.log(
      `    ${viewport.name}: ${viewport.width}x${viewport.height} CSS pixels ` +
        `@dpr ${viewport.deviceScaleFactor}; expected #stage scale ` +
        `${stageScale({ width: viewport.width, height: viewport.height })} ` +
        `from packages/client/src/stage.ts`,
    );
  }

  try {
    for (const entry of BROWSERS) {
      if (only && entry.name !== only) continue;
      const browser = findBrowser(entry.name);
      if (!browser) {
        notRun.push(entry.name);
        continue;
      }
      console.log(`  EMULATION ${entry.name}:`);
      ran.push(entry.name);
      const profile = mkdtempSync(path.join(os.tmpdir(), 'swl-mobile-matrix-profile-'));
      profiles.push(profile);
      const devToolsPort = await nextPort();
      const child = spawn(
        browser,
        [
          '--headless=new',
          '--disable-gpu',
          '--no-sandbox',
          '--disable-dev-shm-usage',
          '--no-first-run',
          '--no-default-browser-check',
          `--user-data-dir=${profile}`,
          `--remote-debugging-port=${devToolsPort}`,
          'about:blank',
        ],
        { stdio: 'ignore' },
      );
      browsers.push(child);
      let page = null;
      let currentLabel = entry.name;
      try {
        await waitForDevTools(devToolsPort);
        page = await Page.openBlank(devToolsPort);
        for (const viewport of VIEWPORTS) {
          currentLabel = `${entry.name} ${viewport.name}`;
          console.log(`  EMULATION ${currentLabel}:`);
          // Each viewport gets its own server-issued session, so a fresh
          // player/tutorial is measured exactly as in the original harness.
          const session = await register(
            serverPort,
            `mobile-${entry.name.toLowerCase()}-${viewport.slug}`,
          );
          // The CDP emulation. These two calls are the whole device story:
          // everything below ran in a real browser at an emulated viewport.
          // Apply them before navigation, so the client's viewport meta tag
          // is parsed against the emulated phone from the first layout.
          // `mobile: false` is deliberate. In headless Chromium, `mobile: true`
          // makes `window.innerWidth` disagree with the layout viewport (it
          // reported 575/690 instead of 390 at the first phone size), which
          // would drive the client's fit to the wrong size and make the
          // assertion meaningless. Without mobile mode the CSS viewport is
          // exactly the emulated size; touch is still enabled by the next
          // call, so the gestures are emulated touch, not a device.
          await page.send('Emulation.setDeviceMetricsOverride', {
            width: viewport.width,
            height: viewport.height,
            deviceScaleFactor: viewport.deviceScaleFactor,
            mobile: false,
          });
          await page.send('Emulation.setTouchEmulationEnabled', {
            enabled: true,
            maxTouchPoints: 1,
          });
          await page.send('Page.navigate', { url: `http://127.0.0.1:${clientPort}/` });
          await page.waitForLoad();
          await verifyEmulatedPhone(page, entry.name, serverPort, session, failures, viewport);
        }
      } catch (error) {
        failures.push(`${currentLabel}: ${error?.message ?? String(error)}`);
        console.log(`  FAILED (${error?.message ?? String(error)})`);
      } finally {
        if (page) await page.close(devToolsPort);
      }
    }
  } finally {
    for (const child of browsers) child.kill();
    client.close();
    server.kill();
    await removeTemp(dataDir);
    for (const profile of profiles) await removeTemp(profile);
  }

  console.log('');
  console.log(`  the browsers that ran: ${ran.length ? ran.join(', ') : 'none'}`);
  if (notRun.length) {
    console.log(`  the browsers NOT RUN: ${notRun.join(', ')}`);
  }
  if (failures.length) {
    console.error('');
    console.error('the emulated-phone verification failed:');
    for (const failure of failures) console.error(`  ${failure}`);
    process.exit(1);
  }
  if (ran.length === 0) {
    console.error('');
    console.error('no browser was available for emulation.');
    process.exit(2);
  }
  console.log(
    `OK: the ${VIEWPORTS.length}-viewport layout matrix ` +
      `(${VIEWPORTS.map((viewport) => viewport.name).join(', ')}) was verified by ` +
      'EMULATION in a real Chromium browser. No device, Android/iOS build, emulator, ' +
      'Firefox or Safari was used or claimed, and the touch gesture was a CDP-enabled ' +
      'synthetic pointer event, not a physical touch device.',
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
