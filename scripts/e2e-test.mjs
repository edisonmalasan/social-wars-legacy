#!/usr/bin/env node
/**
 * The end-to-end test.
 *
 * The client is driven through a **complete play session**, and every
 * layer is the real one:
 *
 * 1. the **real server** is started, with a real database;
 * 2. a player is **registered** through `POST /api/account`, and the
 *    credential is **persisted**;
 * 3. the **real client** is served and loaded in a **real browser**;
 * 4. the client **signs in** and fetches its world;
 * 5. the client sends a **command** - its own request builder, its own
 *    transport - and the **server's own rules** decide the outcome;
 * 6. the player signs in **again**, in a fresh server, from the
 *    persisted credential.
 *
 * Nothing here is a stand-in. The client is the built one, the server is
 * the built one, and the browser is a real one.
 *
 * Usage:
 *   node scripts/e2e-test.mjs
 *   node scripts/e2e-test.mjs --browser chrome
 */
import { spawn } from 'node:child_process';
import {
  createReadStream,
  existsSync,
  mkdtempSync,
  readFileSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

import { brokenBudgets } from '../packages/server/src/budgets.ts';
import { COMMAND_CENTER_TILE, STARTING_EXPANSIONS } from '../packages/server/src/starttown.ts';
import { QUESTS } from '../packages/rules/src/quest.ts';
import { tileToPixel } from '../packages/client/src/iso.ts';
import { BUILD_OUTLINE_OFFSET_Y, cameraCentredOn } from '../packages/client/src/camera.ts';

import {
  VISUAL_METRICS_EXPRESSION,
  decodePng,
  greenRatio,
  visualFailures,
} from './capture-ui.mjs';

const ROOT = process.cwd();

/** The sleep between DOM polls. */
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * The deterministic clock's control file. Created in `main()` before the
 * server starts and read by the server child through `scripts/e2e-clock.mjs`.
 * Nothing in the shipped server knows this file exists.
 */
let clockFile = null;
let clockOffset = 0;

/** Advance the server's authoritative clock, without waiting in real time. */
function advanceClock(seconds) {
  if (!clockFile) throw new Error('the e2e clock fixture was not started');
  clockOffset += seconds;
  writeFileSync(clockFile, `${clockOffset}\n`);
}

/**
 * The weekly quest, from the rules the server uses.
 *
 * A fresh save has slot 1 open, and this is the quest in it. Reading the spec
 * rather than hard-coding the id keeps the DOM scenario honest if the content
 * changes.
 */
const WEEKLY = QUESTS.find((quest) => quest.constantName === 'QUEST_WEEKLY_01');
if (!WEEKLY) throw new Error('the rules have no weekly quest');

/**
 * Q11, whose 240-second mission timer is enforced by the server clock.
 *
 * It is a level-0 quest, so a fresh e2e player may start it. The spec (not a
 * hard-coded id) supplies the limit the harness advances past, keeping the
 * expiry assertion honest if the content changes.
 */
const TIMED = QUESTS.find((quest) => quest.constantName === 'QUEST_11_SAVE_VILLAGES');
if (!TIMED || TIMED.timeLimitSeconds !== 240) {
  throw new Error('the rules have no Q11 with a 240-second timer');
}

/**
 * The four collection periods and their multipliers, from the same content
 * bundle the server reads. The DOM assertions compare the selector's buttons
 * with these numbers instead of hard-coding the game's own configuration.
 */
function collectRules() {
  const bundlePath = path.join(ROOT, 'packages/content/dist/content-bundle.json');
  if (!existsSync(bundlePath)) {
    throw new Error('the content bundle has not been built. Run: pnpm build:content');
  }
  const globals = JSON.parse(readFileSync(bundlePath, 'utf8')).globals ?? {};
  const minutes = globals.COLLECT_MINUTES;
  const multipliers = globals.COLLECT_MULTIPLIER;
  if (
    !Array.isArray(minutes) || minutes.length < 4 ||
    !Array.isArray(multipliers) || multipliers.length < 4 ||
    [...minutes.slice(0, 4), ...multipliers.slice(0, 4)].some(
      (value) => !Number.isFinite(value) || value <= 0,
    )
  ) {
    throw new Error('the content bundle has no usable collection periods');
  }
  return { minutes: minutes.slice(0, 4), multipliers: multipliers.slice(0, 4) };
}
const COLLECT = collectRules();

/**
 * The price the server will charge for a fresh save's first expansion, from
 * the same content bundle the server reads. A new town owns the seeded
 * STARTING_EXPANSIONS tiles, so the purchase is priced at that ordinal. The
 * test compares the rendered panel with these numbers instead of hard-coding
 * the game's configuration.
 */
function expansionRules() {
  const bundlePath = path.join(ROOT, 'packages/content/dist/content-bundle.json');
  if (!existsSync(bundlePath)) {
    throw new Error('the content bundle has not been built. Run: pnpm build:content');
  }
  const prices = JSON.parse(readFileSync(bundlePath, 'utf8')).expansionPrices ?? [];
  const row = prices[STARTING_EXPANSIONS.length];
  if (!row || !Number.isFinite(row.coins) || !Number.isFinite(row.cash)) {
    throw new Error('the content bundle has no usable expansion price for a fresh save');
  }
  return { coins: row.coins, cash: row.cash };
}
const EXPANSION = expansionRules();

/**
 * The wallet keys behind the protocol's resource names, from the server's
 * `QUEST_REWARD_RESOURCE` map. The result rows use the protocol vocabulary;
 * the wallet uses the short keys. This is a test-side mirror, never a client
 * or server authority.
 */
const WALLET_KEY = {
  energy: 'e', xp: 'x', gold: 'g', wood: 'w',
  oil: 'o', steel: 's', cash: 'c', mana: 'm',
};

/** The viewport a fresh player's camera opens with, for tile clicks. */
const CAMERA = cameraCentredOn(COMMAND_CENTER_TILE.x, COMMAND_CENTER_TILE.y);
const VIEWPORT = {
  topX: CAMERA.topX,
  topY: CAMERA.topY,
  buildOutlineOffsetY: BUILD_OUTLINE_OFFSET_Y,
};

/** Where the browsers are looked for. */
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

/** The content types the static server serves. */
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  // The WebAssembly must be served as WebAssembly: a browser refuses to
  // stream it as anything else, and the offline mode's database is
  // PostgreSQL compiled to WebAssembly.
  '.wasm': 'application/wasm',
};

/** The files the client is served from. */
const ROOTS = [
  path.join(ROOT, 'apps/client/dist'),
  path.join(ROOT, 'apps/client/public'),
  path.join(ROOT, '.work/frames'),
];

/** Find a browser on this machine. */
function findBrowser(name) {
  const entry = BROWSERS.find((browser) => browser.name === name);
  if (!entry) return null;
  for (const candidate of entry.paths) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/**
 * The quest with the smallest event set, read from the content the server uses.
 *
 * Not hard-coded: the bundle decides which quest is cheapest to complete, and
 * its event decides which authoritative action advances it. The refs are the
 * bundle's own, so the test cannot accidentally invent one.
 */
function smallestEventQuest() {
  const bundlePath = path.join(ROOT, 'packages/content/dist/content-bundle.json');
  if (!existsSync(bundlePath)) {
    throw new Error('the content bundle has not been built. Run: pnpm build:content');
  }
  const bundle = JSON.parse(readFileSync(bundlePath, 'utf8'));
  const events = Object.values(bundle.questEvents ?? {});
  if (events.length === 0) throw new Error('the content bundle has no event quests');
  const event = events.reduce((smallest, candidate) =>
    candidate.count < smallest.count ? candidate : smallest,
  );
  const actionTypes = {
    truckArrivals: 'truck-arrival',
    eligibleEnemies: 'eligible-enemy',
    civilianEvacuations: 'civilian-evacuation',
  };
  const counterNames = {
    truckArrivals: 'trucksArrived',
    eligibleEnemies: 'bastardsAlive',
    civilianEvacuations: 'workersInVillages',
  };
  const actionType = actionTypes[event.kind];
  if (!actionType || !event.refs?.length) {
    throw new Error(`the smallest quest event is unusable: ${JSON.stringify(event)}`);
  }
  const spec = QUESTS.find((quest) => quest.id === event.questId);
  if (!spec) throw new Error(`the rules have no spec for ${event.questId}`);
  return {
    questId: event.questId,
    playIndex: String(spec.playIndex),
    actionType,
    counterName: counterNames[event.kind],
    ref: event.refs[0],
    count: event.count,
  };
}

/**
 * A destroy-one-element quest, for proving an accepted kill report.
 *
 * The quest id, its play index and the win element's ref come from the rules
 * spec, so the test cannot invent a ref the server would not recognise.
 */
function killQuest() {
  const spec = QUESTS.find((quest) => quest.id === '100000002');
  if (!spec || spec.win.kind !== 'destroyAll' || spec.win.elements.length === 0) {
    throw new Error('the nuclear quest no longer has a single destroy-all element');
  }
  return { questId: spec.id, playIndex: String(spec.playIndex), ref: spec.win.elements[0] };
}

/** A static server for the client's files, and a proxy for the API. */
async function serve(port, apiPort) {
  const server = createServer((request, response) => {
    const url = (request.url ?? '/').split('?')[0];

    // The API goes to the **real** server, so the client is talking to
    // the server it would talk to in production.
    if (url.startsWith('/api/') || url === '/health') {
      const chunks = [];
      request.on('data', (chunk) => chunks.push(chunk));
      request.on('end', async () => {
        try {
          // The **request's** headers are what the server reads, so the
          // token has to be forwarded there.
          const requestHeaders = {
            'content-type': request.headers['content-type'] ?? 'application/json',
          };
          const authorization = request.headers['authorization'];
          if (authorization) requestHeaders['authorization'] = authorization;

          const upstream = await fetch(`http://127.0.0.1:${apiPort}${url}`, {
            method: request.method,
            headers: requestHeaders,
            body: chunks.length ? Buffer.concat(chunks) : undefined,
          });
          const body = Buffer.from(await upstream.arrayBuffer());
          response.writeHead(upstream.status, {
            'content-type': upstream.headers.get('content-type') ?? 'application/json',
          });
          response.end(body);
        } catch (error) {
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

/** Wait for the DevTools endpoint to answer. */
async function waitForDevTools(port, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return;
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error('the browser did not open its debugging port');
}

/** A page, driven over the DevTools protocol. */
class Page {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.loaded = false;
    this.loadResolvers = [];
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      if (message.method === 'Page.loadEventFired') {
        this.loaded = true;
        for (const resolve of this.loadResolvers) resolve();
        this.loadResolvers = [];
      }
      const resolver = this.pending.get(message.id);
      if (resolver) {
        this.pending.delete(message.id);
        resolver(message);
      }
    });
  }

  /**
   * Wait for the page to finish loading.
   *
   * Without it the test can evaluate its expression on the **previous**
   * document, or on one that has no origin - and a document with no
   * origin has no `localStorage`.
   *
   * The document's own state is polled rather than the load event
   * waited for, because the event can fire before the test is listening
   * for it.
   */
  async waitForLoad(timeoutMs = 30_000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      try {
        // The **address** is what matters, not the document's state: a
        // blank page is already "complete", and it has no origin, and so
        // it has no `localStorage`.
        const where = await this.evaluate('location.href');
        if (typeof where === 'string' && where.startsWith('http://127.0.0.1:')) {
          const state = await this.evaluate('document.readyState');
          if (state === 'complete' || state === 'interactive') return;
        }
      } catch {
        // The document is not there yet.
      }
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error('the page did not load');
  }

  static async open(devToolsPort, url) {
    const target = await (
      await fetch(`http://127.0.0.1:${devToolsPort}/json/new?${encodeURIComponent(url)}`, {
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
    await page.waitForLoad();
    return page;
  }

  send(method, params) {
    return new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  /** Evaluate an expression in the page and read the value back. */
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

  /** The client's status, until it settles. */
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
      await new Promise((resolve) => setTimeout(resolve, 200));
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

/** Start the real server and wait for it to answer. */
async function startServer(dataDir, port) {
  const env = { ...process.env, SWL_DATA_DIR: dataDir, PORT: String(port) };
  if (clockFile) {
    // The clock is injected into the **server child only**; the harness's
    // own timers stay real, so its timeouts remain genuine.
    const preload = pathToFileURL(path.join(ROOT, 'scripts/e2e-clock.mjs')).href;
    env.NODE_OPTIONS = [env.NODE_OPTIONS, `--import=${preload}`].filter(Boolean).join(' ');
    env.SWL_E2E_CLOCK_FILE = clockFile;
  }
  const child = spawn(
    process.execPath,
    ['apps/server/src/main.ts'],
    {
      cwd: ROOT,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );
  let output = '';
  child.stdout.on('data', (chunk) => {
    output += String(chunk);
  });
  child.stderr.on('data', (chunk) => {
    output += String(chunk);
  });

  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`);
      if (response.ok) return { child, output: () => output };
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  child.kill();
  throw new Error(`the server did not start:\n${output}`);
}

/** Register a player and return the session. */
async function register(port, playerId, password) {
  const response = await fetch(`http://127.0.0.1:${port}/api/account`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playerId, password }),
  });
  if (response.status !== 201) {
    throw new Error(`the account was not created: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

/** The server's world, with the player's own token. */
async function worldOf(port, token) {
  const response = await fetch(`http://127.0.0.1:${port}/api/world`, {
    headers: { authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`the world was not served (${response.status})`);
  return response.json();
}

/** Poll the server's world until `accept` agrees, for a gesture that is in flight. */
async function worldWait(port, token, accept, label, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    last = await worldOf(port, token);
    if (accept(last)) return last;
    await sleep(150);
  }
  throw new Error(`the world never showed ${label}`);
}

/** Evaluate an expression and hand its value back through JSON. */
async function domValue(page, expression) {
  const text = await page.evaluate(`JSON.stringify({v: (${expression})})`);
  return text ? JSON.parse(text).v : undefined;
}

/** Poll the rendered interface until `accept` agrees. */
async function domWait(page, expression, accept, label, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    last = await domValue(page, expression);
    if (accept(last)) return last;
    await sleep(150);
  }
  throw new Error(`the interface never showed ${label} (last: ${JSON.stringify(last)})`);
}

/** Click a rendered control, waiting for a named part of the interface to change. */
async function domClick(page, selector, signature, label, timeoutMs = 15_000) {
  const before = await domValue(page, signature);
  const clicked = await page.evaluate(
    `(() => { const e = document.querySelector(${JSON.stringify(selector)});` +
      ` if (!e) return {error: 'no control for ' + ${JSON.stringify(selector)}};` +
      ` e.click(); return {ok: true}; })()`,
  );
  if (!clicked || clicked.error) {
    throw new Error(clicked?.error ?? `the ${label} could not be clicked`);
  }
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const after = await domValue(page, signature);
    if (JSON.stringify(after) !== JSON.stringify(before)) return after;
    await sleep(150);
  }
  throw new Error(`the ${label} changed nothing on the interface`);
}

/** Click a rendered control without expecting the interface to redraw. */
async function domClickPlain(page, selector, label) {
  const clicked = await page.evaluate(
    `(() => { const e = document.querySelector(${JSON.stringify(selector)});` +
      ` if (!e) return {error: 'no control for ' + ${JSON.stringify(selector)}};` +
      ` e.click(); return {ok: true}; })()`,
  );
  if (!clicked || clicked.error) {
    throw new Error(clicked?.error ?? `the ${label} could not be clicked`);
  }
}

/**
 * Open one non-modal surface. Panels are no longer mounted at rest, so a step
 * that inspects a panel asks for it first through the client's own surface
 * API — the same gesture the rendered navigation control makes — and waits
 * for the real panel before reading it. Assertions downstream are unchanged.
 */
async function openSurface(page, id, selector) {
  const opened = await page.evaluate(
    `(() => {
       const handle = window.__swl;
       if (!handle || typeof handle.setActiveSurface !== 'function') {
         return {error: 'the client has no surface API'};
       }
       handle.setActiveSurface(${JSON.stringify(id)});
       return {ok: true};
     })()`,
  );
  if (!opened || opened.error) {
    throw new Error(opened?.error ?? `the ${id} surface could not be opened`);
  }
  await domWait(
    page,
    `!!document.querySelector(${JSON.stringify(selector)})`,
    (value) => value === true,
    `the ${id} surface`,
  );
}

/** Return to the at-rest surface so a canvas click is never covered. */
async function closeSurface(page) {
  await page.evaluate(`(() => { window.__swl?.setActiveSurface?.('none'); })()`);
  await domWait(
    page,
    "Array.from(document.querySelectorAll('#ui [data-swl-surface]'))" +
      ".every((b) => b.getAttribute('aria-pressed') !== 'true')",
    (value) => value === true,
    'the at-rest surface',
  );
}

/**
 * Click a map tile as a player would: the canvas's own pointer gesture, at the
 * stage pixel the client's projection gives the tile. The target has to be the
 * canvas itself — a panel over the tile would swallow a real click.
 */
async function domTileClick(page, tx, ty) {
  const pixel = tileToPixel(tx, ty, VIEWPORT);
  const result = await page.evaluate(
    `(() => {
       const canvas = document.querySelector('#game canvas');
       if (!canvas) return {error: 'the client has no canvas'};
       const rect = canvas.getBoundingClientRect();
       const x = rect.left + (${pixel.x} / canvas.width) * rect.width;
       const y = rect.top + (${pixel.y} / canvas.height) * rect.height;
       const top = document.elementFromPoint(x, y);
       if (top !== canvas) return {error: 'tile ${tx},${ty} is covered by ' + (top?.className || top?.tagName)};
       canvas.dispatchEvent(new PointerEvent('pointerdown', {
         clientX: x, clientY: y, bubbles: true, cancelable: true,
         pointerId: 1, isPrimary: true, pointerType: 'mouse',
       }));
       return {ok: true};
     })()`,
  );
  if (!result || result.error) {
    throw new Error(result?.error ?? `tile ${tx},${ty} could not be clicked`);
  }
}

/** The cash in the server's wallet, for the reward assertions. */
function cashOf(world) {
  return Number(world?.resources?.c ?? 0);
}

/**
 * The Phase-1 visual probe. The DOM metrics come from the same expression the
 * screenshot harness uses; the green ratio is sampled from a CDP screenshot
 * clipped to the canvas with the interface temporarily hidden. This only
 * reads the page: the interface is restored before any further gesture.
 */
async function visualProbe(page) {
  const metrics = await page.evaluate(VISUAL_METRICS_EXPRESSION);
  const canvasRect = await page.evaluate(
    `(() => { const canvas = document.querySelector('#game canvas');
       if (!canvas) return null;
       const r = canvas.getBoundingClientRect();
       return {x: r.left, y: r.top, width: r.width, height: r.height}; })()`,
  );
  if (!canvasRect || !canvasRect.width || !canvasRect.height) {
    return { ...metrics, greenRatio: 0 };
  }
  await page.evaluate(
    `(() => { const ui = document.querySelector('#ui');
       if (ui) ui.style.visibility = 'hidden'; return true; })()`,
  );
  let ratio = 0;
  try {
    await sleep(150);
    const shot = await page.send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: false,
      clip: { ...canvasRect, scale: 1 },
    });
    ratio = greenRatio(decodePng(Buffer.from(shot.result.data, 'base64'))).ratio;
  } finally {
    await page.evaluate(
      `(() => { const ui = document.querySelector('#ui');
         if (ui) ui.style.visibility = ''; return true; })()`,
    );
  }
  return { ...metrics, greenRatio: ratio };
}

/**
 * The whole gameplay loop, driven by the rendered interface.
 *
 * A fresh player is registered through the form, so the walk starts from a
 * new save (the weekly quest is slot 1) and has its own rate-limit key. Every
 * act below is a click on a rendered control; the client's own code turns it
 * into a request, and the server's world is the evidence of what happened.
 */
async function playThroughDom(page, serverPort, browserName) {
  const playerId = `e2e-ui-${browserName.toLowerCase()}`;

  // The rendered account form: Register mode, a name, a password, submit.
  await page.evaluate("window.localStorage.removeItem('swl.session'); true");
  page.loaded = false;
  await page.send('Page.reload', {});
  await page.waitForLoad();
  await domWait(page, "!!document.querySelector('#signin')", (v) => v === true, 'the account form');
  const submitted = await page.evaluate(
    `(() => {
       const form = document.querySelector('#signin');
       const register = form.querySelector('button[data-mode="register"]');
       if (!register) return {error: 'the form has no Register mode'};
       register.click();
       const name = form.querySelector('input[name="playerId"]');
       const secret = form.querySelector('input[name="password"]');
       if (!name || !secret) return {error: 'the form has no credential fields'};
       name.value = ${JSON.stringify(playerId)};
       secret.value = 'correct horse';
       form.requestSubmit();
       return {ok: true};
     })()`,
  );
  if (!submitted || submitted.error) {
    throw new Error(submitted?.error ?? 'the account form did not submit');
  }
  const signed = await page.waitForStatus(['started', 'failed']);
  if (!String(signed).startsWith('started')) throw new Error(`the client said "${signed}"`);
  const session = await page.evaluate(
    "JSON.parse(window.localStorage.getItem('swl.session') || 'null')",
  );
  if (!session || !session.token) throw new Error('the registration remembered no session');
  console.log(`  UI: registered "${playerId}" through the rendered form`);

  // A fresh save opens the tutorial. Skip it with the rendered Skip button.
  await domClick(
    page,
    '#ui .swl-tutorial-skip',
    "!!document.querySelector('#ui .swl-tutorial')",
    'tutorial Skip button',
  );
  await domWait(
    page,
    "!document.querySelector('#ui .swl-tutorial')",
    (v) => v === true,
    'the tutorial to close',
  );
  console.log('  UI: skipped the tutorial with its rendered button');

  // The 760x600 layout: the new HUD and inventory must not overlap. Storage
  // is a requested surface now, so open it before measuring the same rects.
  await openSurface(page, 'inventory', '#ui .swl-inventory');
  const layout = await page.evaluate(
    `(() => {
       const rect = (selector) => {
         const e = document.querySelector(selector);
         if (!e) return null;
         const r = e.getBoundingClientRect();
         return {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
       };
       const stage = document.querySelector('#stage');
       return {
         stage: rect('#stage'), hud: rect('#ui .swl-hud'), inventory: rect('#ui .swl-inventory'),
         stageCss: stage ? {
           width: getComputedStyle(stage).width, height: getComputedStyle(stage).height,
         } : null,
       };
     })()`,
  );
  if (!layout?.stage || !layout?.hud || !layout?.inventory) {
    throw new Error('the HUD or the inventory is missing from the 760x600 layout');
  }
  if (layout.stageCss?.width !== '760px' || layout.stageCss?.height !== '600px') {
    throw new Error(`the stage is not 760x600: ${JSON.stringify(layout.stageCss)}`);
  }
  const overlap = !(
    layout.hud.right <= layout.inventory.left ||
    layout.inventory.right <= layout.hud.left ||
    layout.hud.bottom <= layout.inventory.top ||
    layout.inventory.bottom <= layout.hud.top
  );
  if (overlap) throw new Error(`the HUD overlaps the inventory: ${JSON.stringify(layout)}`);
  if (
    layout.inventory.right > layout.stage.right + 0.5 ||
    layout.inventory.bottom > layout.stage.bottom + 0.5
  ) {
    throw new Error(`the inventory falls outside the stage: ${JSON.stringify(layout)}`);
  }
  console.log(
    `  UI: at 760x600 the HUD ends at y=${layout.hud.bottom.toFixed(0)} ` +
      `and the inventory starts at y=${layout.inventory.top.toFixed(0)} (no overlap)`,
  );

  // Build: pick the first unlocked item from the rendered menu, then click a
  // free tile. The server prices and places it; the client only draws it.
  await closeSurface(page);
  await openSurface(page, 'build', '#ui .swl-build-menu');
  const beforeBuild = await worldOf(serverPort, session.token);
  const beforeItems = Object.keys(beforeBuild?.maps?.[0]?.items ?? {}).length;
  await domClick(
    page,
    '#ui .swl-build-menu .swl-build-item:not(.swl-build-locked) button',
    "document.querySelector('#ui .swl-placing')?.textContent ?? ''",
    'build-menu item',
  );
  // Picking the item closes the menu again, so the tile is not covered.
  // The first unlocked item is a 4x4 Prison, so the tile has to clear the
  // Command Center's own 4x4 footprint at 48,48.
  await closeSurface(page);
  await domTileClick(page, 52, 51);
  await domWait(
    page,
    "!document.querySelector('#ui .swl-placing')",
    (v) => v === true,
    'the build to be placed',
  );
  const afterBuild = await worldOf(serverPort, session.token);
  const builtItems = Object.values(afterBuild?.maps?.[0]?.items ?? {});
  if (Object.keys(afterBuild?.maps?.[0]?.items ?? {}).length !== beforeItems + 1) {
    const feedback = await domValue(
      page,
      "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
    );
    throw new Error(
      `the rendered build did not add a building to the server's map ` +
        `(${beforeItems} -> ${Object.keys(afterBuild?.maps?.[0]?.items ?? {}).length}; ` +
        `feedback: ${JSON.stringify(feedback)})`,
    );
  }
  if (!builtItems.some((tuple) => Number(tuple[1]) === 52 && Number(tuple[2]) === 51)) {
    throw new Error('the rendered build did not place the item on the clicked tile');
  }
  console.log('  UI: picked a build-menu item and placed it on a tile through the canvas');

  // A Wood Factory I produces wood, so the Collect button has real work.
  // Its entry lives in the build surface, opened on request like any other.
  await openSurface(page, 'build', '#ui .swl-build-menu');
  const factoryPick = await page.evaluate(
    `(() => {
       const items = Array.from(document.querySelectorAll(
         '#ui .swl-build-menu .swl-build-item:not(.swl-build-locked) button'));
       const item = items.find((b) =>
         b.querySelector('.swl-build-name')?.textContent === 'Wood Factory I');
       if (!item) return {error: 'the build menu has no Wood Factory I'};
       item.click();
       return {ok: true};
     })()`,
  );
  if (!factoryPick || factoryPick.error) {
    throw new Error(factoryPick?.error ?? 'the Wood Factory could not be picked');
  }
  await domWait(
    page,
    "document.querySelector('#ui .swl-placing')?.textContent ?? ''",
    (v) => typeof v === 'string' && v.includes('Wood Factory I'),
    'the Wood Factory placement',
  );
  await closeSurface(page);
  await domTileClick(page, 46, 46);
  await domWait(
    page,
    "!document.querySelector('#ui .swl-placing')",
    (v) => v === true,
    'the Wood Factory to be placed',
  );
  const factoryWorld = await worldOf(serverPort, session.token);
  if (
    !Object.values(factoryWorld?.maps?.[0]?.items ?? {}).some(
      (tuple) => Number(tuple[0]) === 2 && Number(tuple[1]) === 46 && Number(tuple[2]) === 46,
    )
  ) {
    throw new Error('the Wood Factory was not placed by the rendered canvas click');
  }

  // Select that building on the map and collect its production.
  await closeSurface(page);
  await domTileClick(page, 46, 46);
  await domWait(
    page,
    "document.querySelector('#ui .swl-info .swl-info-name')?.textContent ?? ''",
    (v) => v === 'Wood Factory I',
    'the Wood Factory info panel',
  );
  const woodBefore = Number((await worldOf(serverPort, session.token))?.resources?.w ?? 0);
  await domClickPlain(page, '#ui .swl-info button.swl-info-collect', 'Collect button');
  const collectAnswer = await domWait(
    page,
    "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
    (v) => typeof v === 'string' && /refused|not-due|collect/i.test(v),
    'the server answer to the Collect gesture',
  );
  // A freshly built factory's chosen five-minute cycle has not elapsed, so
  // the server must refuse: a rendered Collect button cannot mint wood.
  if (!/not-due/i.test(String(collectAnswer))) {
    throw new Error(`the Collect gesture drew an unexpected answer: ${collectAnswer}`);
  }
  const afterCollect = await worldOf(serverPort, session.token);
  if (Number(afterCollect?.resources?.w ?? 0) !== woodBefore) {
    throw new Error('the client changed wood before the server said the collection was due');
  }
  console.log(
    `  UI: the rendered Collect button asked the server, which refused ` +
      `an undue cycle ("${String(collectAnswer).trim()}") and granted no wood`,
  );

  // --- G5.2: choose a collection period through the rendered selector -----
  // The old refusal above stays intact. Here the player opens the factory's
  // period dialog, checks the four content-derived choices, picks the
  // five-minute one, waits for the **server's** clock via the deterministic
  // fixture, and collects. No assertion is weakened and no real time is slept
  // away: the server's own rules still decide readiness and the amount.
  const factoryOf = (world) =>
    Object.values(world?.maps?.[0]?.items ?? {}).find(
      (tuple) => Number(tuple[0]) === 2 && Number(tuple[1]) === 46 && Number(tuple[2]) === 46,
    );

  await domClickPlain(
    page,
    '#ui .swl-info button.swl-info-period-button',
    'Choose collection period button',
  );
  await domWait(
    page,
    "document.querySelector('#ui .swl-dialog .swl-production-head')?.textContent ?? ''",
    (v) => typeof v === 'string' && /wood/i.test(v),
    'the collection-period selector',
  );
  const periodButtons = await domValue(
    page,
    `Array.from(document.querySelectorAll('#ui .swl-dialog .swl-production-option')).map((b) => ({
       wait: b.querySelector('.swl-production-wait')?.textContent ?? '',
       mult: b.querySelector('.swl-production-mult')?.textContent ?? '',
       amount: b.querySelector('.swl-production-amount')?.textContent ?? '',
       pressed: b.getAttribute('aria-pressed'),
     }))`,
  );
  if (!Array.isArray(periodButtons) || periodButtons.length !== 4) {
    throw new Error(`the selector drew ${periodButtons?.length ?? 0} periods, not four`);
  }
  const waitLabel = (minutes) =>
    minutes % 60 === 0 ? `${minutes / 60} h` : `${minutes} min`;
  for (let index = 0; index < 4; index++) {
    const button = periodButtons[index];
    if (button.wait !== waitLabel(COLLECT.minutes[index])) {
      throw new Error(`period ${index + 1} says ${button.wait}, not ${waitLabel(COLLECT.minutes[index])}`);
    }
    if (button.mult !== `×${COLLECT.multipliers[index]}`) {
      throw new Error(`period ${index + 1} says ${button.mult}, not ×${COLLECT.multipliers[index]}`);
    }
  }
  const predicted = /^\s*\+(\d+)/.exec(String(periodButtons[0].amount));
  if (!predicted) {
    throw new Error(`the five-minute option shows no server-derived amount ("${periodButtons[0].amount}")`);
  }
  const expectedWood = Number(predicted[1]);

  const woodBeforeCycle = Number((await worldOf(serverPort, session.token))?.resources?.w ?? 0);
  await domClick(
    page,
    '#ui .swl-dialog .swl-production-option:first-child',
    "!!document.querySelector('#ui .swl-dialog .swl-production')",
    'the five-minute collection period',
  );
  const cycleWorld = await worldWait(
    serverPort,
    session.token,
    (world) => {
      const factory = factoryOf(world);
      return Number(factory?.[6]?.['cp']) === 1 && Number(factory?.[6]?.['lastAccruedAt'] ?? 0) > 0;
    },
    'the server to record the chosen collection period',
  );
  const cycleStart = Number(factoryOf(cycleWorld)[6]['lastAccruedAt']);

  // Advance the server's clock by one second past the chosen five minutes.
  // This is a deterministic fixture, not a sleep: the browser keeps its own
  // clock, but the server's `deps.now()` is what decides `isDue`.
  advanceClock(COLLECT.minutes[0] * 60 + 1);
  await domClickPlain(
    page,
    '#ui .swl-info button.swl-info-period-button',
    'Choose collection period button after the clock advanced',
  );
  // The countdown is presentation only: it reads the **browser's** clock,
  // which the fixture deliberately leaves alone. Reading the server's clock
  // here would let a modified client pretend a cycle was due. Read the text
  // instead, and let the server's acceptance of the rendered Collect button
  // be the proof of readiness.
  const cycleText = await domValue(
    page,
    "document.querySelector('#ui .swl-dialog .swl-production-cycle')?.textContent ?? ''",
  );
  if (!/ready in|ready to collect/i.test(String(cycleText))) {
    throw new Error(`the production dialog drew no cycle status ("${cycleText}")`);
  }
  const pressed = await domValue(
    page,
    `Array.from(document.querySelectorAll('#ui .swl-dialog .swl-production-option'))
       .map((b) => b.getAttribute('aria-pressed'))`,
  );
  if (!Array.isArray(pressed) || pressed[0] !== 'true' || pressed.slice(1).some((v) => v !== 'false')) {
    throw new Error(`the active-period marker is wrong: ${JSON.stringify(pressed)}`);
  }
  await domClick(
    page,
    '#ui .swl-dialog button.swl-dialog-close',
    "!!document.querySelector('#ui .swl-dialog')",
    'production dialog Close button',
  );
  const feedbackBeforeCollect = await domValue(
    page,
    "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
  );
  await domClickPlain(page, '#ui .swl-info button.swl-info-collect', 'Collect button when due');
  await domWait(
    page,
    "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
    (v) => typeof v === 'string' && v !== feedbackBeforeCollect && !/not-due|refused/i.test(v),
    'the server to accept the due collection',
  );
  // The rewritten cycle timestamp, not a wallet guess, is the proof that the
  // command was applied: a freshly built producer stores a base amount of
  // zero, so the correct payment here can legitimately be zero. The exact
  // period multipliers are proved with a non-zero fixture by the unit tests.
  await worldWait(
    serverPort,
    session.token,
    (world) => {
      const factory = factoryOf(world);
      return Number(factory?.[6]?.['lastAccruedAt'] ?? 0) > cycleStart &&
        Number(factory?.[6]?.['collect']) === 0;
    },
    'the server to apply the due collection and restart the cycle',
  );
  const paidWorld = await worldOf(serverPort, session.token);
  const paidWood = Number(paidWorld?.resources?.w ?? 0) - woodBeforeCycle;
  if (paidWood !== expectedWood) {
    throw new Error(`the server paid ${paidWood} wood, but its own selector predicted ${expectedWood}`);
  }
  const nextCycle = factoryOf(paidWorld)[6];
  if (Number(nextCycle['lastAccruedAt']) <= cycleStart) {
    throw new Error('the server did not restart the cycle after collection');
  }
  if (Number(nextCycle['cp']) !== 1 || Number(nextCycle['collect']) !== 0) {
    throw new Error(`the next production state is wrong: ${JSON.stringify(nextCycle)}`);
  }
  const production = {
    cp: Number(nextCycle['cp']),
    lastAccruedAt: Number(nextCycle['lastAccruedAt']),
    collect: Number(nextCycle['collect']),
    amount: expectedWood,
  };
  console.log(
    `  UI: picked the ${COLLECT.minutes[0]}-minute period (${periodButtons[0].amount}), ` +
      `the server accepted the due Collect and paid its own ${paidWood} wood; ` +
      `the cycle restarted at ${production.lastAccruedAt}`,
  );

  // Select the Command Center, which is the training building on a fresh save.
  await closeSurface(page);
  await domTileClick(page, COMMAND_CENTER_TILE.x, COMMAND_CENTER_TILE.y);
  // Selecting a building opens its detail surface; the army controls live on
  // their own surface, so ask for that one before reading the training list.
  await openSurface(page, 'recruit', '#ui .swl-recruit');
  await domWait(
    page,
    "document.querySelector('#ui .swl-recruit .swl-recruit-title')?.textContent ?? ''",
    (v) => typeof v === 'string' && v.includes('Command Center'),
    'the Command Center recruitment panel',
  );
  await domClick(
    page,
    '#ui .swl-recruit button.swl-recruit-train',
    "document.querySelector('#ui .swl-recruit .swl-recruit-countdown')?.textContent ?? ''",
    'Train button',
  );
  const countdown = await domValue(
    page,
    "document.querySelector('#ui .swl-recruit .swl-recruit-countdown')?.textContent ?? ''",
  );
  if (!/Training|queued/i.test(String(countdown))) {
    throw new Error(`the training queue did not start ("${countdown}")`);
  }
  const trainedWorld = await worldOf(serverPort, session.token);
  const cc = Object.values(trainedWorld?.maps?.[0]?.items ?? {}).find(
    (tuple) => Number(tuple[0]) === 26,
  );
  if (!(Number(cc?.[6]?.['nu'] ?? 0) >= 1)) {
    throw new Error('the server did not record the trained unit in the queue');
  }
  console.log(`  UI: trained a unit (${countdown})`);

  // --- G5.2: the army panel shows units the server really owns ------------
  // The training queue above is not yet a unit the player can field. Buy a
  // Worker I from the rendered build menu and place it on a free tile; the
  // server's save then owns it, and the army list must name that same unit.
  await openSurface(page, 'build', '#ui .swl-build-menu');
  const workerPick = await page.evaluate(
    `(() => {
       const items = Array.from(document.querySelectorAll(
         '#ui .swl-build-menu .swl-build-item:not(.swl-build-locked) button'));
       const item = items.find((b) =>
         b.querySelector('.swl-build-name')?.textContent === 'Worker I');
       if (!item) return {error: 'the build menu has no Worker I'};
       item.click();
       return {ok: true};
     })()`,
  );
  if (!workerPick || workerPick.error) {
    throw new Error(workerPick?.error ?? 'the Worker I could not be picked');
  }
  await domWait(
    page,
    "document.querySelector('#ui .swl-placing')?.textContent ?? ''",
    (v) => typeof v === 'string' && v.includes('Worker I'),
    'the Worker I placement',
  );
  // 48,46 is a free 1x1 tile above the Command Center: the clear middle of
  // the canvas, not under the goals, chapters, inventory, build or info panels.
  await closeSurface(page);
  await domTileClick(page, 48, 46);
  await domWait(
    page,
    "!document.querySelector('#ui .swl-placing')",
    (v) => v === true,
    'the Worker I to be placed',
  );
  const armyWorld = await worldOf(serverPort, session.token);
  if (
    !Object.values(armyWorld?.maps?.[0]?.items ?? {}).some(
      (tuple) => Number(tuple[0]) === 1001,
    )
  ) {
    throw new Error('the rendered Worker I was not placed on the server\'s map');
  }
  await openSurface(page, 'inventory', '#ui .swl-inventory');
  const armyRows = await domValue(
    page,
    `Array.from(document.querySelectorAll('#ui .swl-inventory [data-swl-army] .swl-inventory-item'))
       .map((li) => ({
         name: li.querySelector('.swl-inventory-name')?.textContent ?? '',
         qty: li.querySelector('.swl-inventory-qty')?.textContent ?? '',
       }))`,
  );
  const workerRow = Array.isArray(armyRows)
    ? armyRows.find((row) => row.name === 'Worker I')
    : null;
  if (!workerRow || workerRow.qty !== '×1') {
    throw new Error(`the army panel did not show the owned unit: ${JSON.stringify(armyRows)}`);
  }
  console.log(`  UI: the army panel shows the placed Worker I (${workerRow.qty}) from the server's map`);

  // --- The expansion control: content price, native path, server's answer -
  // The panel must show the content's price at the ordinal the SERVER owns,
  // send expand(tileId) through the client's one command transport when its
  // button is clicked, and draw the server's answer in the shared feedback
  // region. A fresh save cannot afford the first tile, so the click is first
  // refused (no free tile, unchanged wallet); after legitimately earning gold
  // through the game's own daily bonus the same rendered button buys the tile
  // and pays exactly the content price. Nothing here fabricates an owned tile
  // or a price.
  await openSurface(page, 'expansion', '#ui .swl-expansion');
  const expansionView = await domValue(
    page,
    `(() => {
       const e = document.querySelector('#ui .swl-expansion');
       if (!e) return null;
       return {
         gold: e.querySelector('.swl-expansion-gold')?.textContent ?? '',
         cash: e.querySelector('.swl-expansion-cash')?.textContent ?? '',
       };
     })()`,
  );
  if (!expansionView) throw new Error('the expansion control is not rendered');
  if (expansionView.gold !== `${EXPANSION.coins} gold` ||
      expansionView.cash !== `${EXPANSION.cash} cash`) {
    throw new Error(
      `the expansion panel shows ${JSON.stringify(expansionView)}, ` +
        `not the content price (${EXPANSION.coins} gold / ${EXPANSION.cash} cash)`,
    );
  }
  const beforeExpansion = await worldOf(serverPort, session.token);
  const ownedBefore = beforeExpansion?.maps?.[0]?.expansions ?? [];
  if (ownedBefore.length !== STARTING_EXPANSIONS.length) {
    throw new Error(`a fresh save owns ${ownedBefore.length} tiles, not ${STARTING_EXPANSIONS.length}`);
  }
  const goldBeforeExpansion = Number(beforeExpansion?.resources?.g ?? 0);
  const cashBeforeExpansion = Number(beforeExpansion?.resources?.c ?? 0);
  if (goldBeforeExpansion >= EXPANSION.coins) {
    throw new Error('the e2e fixture unexpectedly starts with enough gold to afford an expansion');
  }
  // Snapshot the channel before the click: a generic "refused" left over from
  // an earlier step must not be mistaken for this click's answer.
  const feedbackBeforeExpand = await domValue(
    page,
    "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
  );
  await domClickPlain(page, '#ui .swl-expansion button.swl-expansion-buy', 'Expand button');
  const expansionRefusal = await domWait(
    page,
    "document.querySelector('#ui .swl-feedback')?.textContent ?? ''",
    (value) =>
      typeof value === 'string' && value !== feedbackBeforeExpand && /refused/i.test(value),
    'a fresh server refusal from this expansion click',
  );
  if (!/refused/i.test(String(expansionRefusal))) {
    throw new Error(`the unaffordable expansion drew no refusal: ${expansionRefusal}`);
  }
  const afterRefusal = await worldOf(serverPort, session.token);
  if ((afterRefusal?.maps?.[0]?.expansions ?? []).length !== ownedBefore.length) {
    throw new Error('the server granted a tile for an unaffordable expansion');
  }
  if (Number(afterRefusal?.resources?.g ?? -1) !== goldBeforeExpansion ||
      Number(afterRefusal?.resources?.c ?? -1) !== cashBeforeExpansion) {
    throw new Error('a refused expansion changed the wallet');
  }
  console.log(
    `  UI: the expansion panel showed ${EXPANSION.coins} gold / ${EXPANSION.cash} cash from ` +
      `the content; the click was refused ("${String(expansionRefusal).trim()}") with no tile or charge`,
  );

  // Fund the purchase the way the game itself does: the daily bonus is a real
  // command, the server picks the day from its own clock (advanced by the
  // deterministic fixture) and grants its own gold. No cheat command and no
  // minted wallet — the same authority as every other claim.
  let enriched = afterRefusal;
  for (let day = 0; day < 5 && Number(enriched?.resources?.g ?? 0) < EXPANSION.coins + 1; day++) {
    const previousGold = Number(enriched?.resources?.g ?? 0);
    advanceClock(86_400);
    await page.evaluate(`(async () => {
       const handle = window.__swl;
       if (handle) await handle.run([handle.claimDailyBonus()]);
     })()`);
    enriched = await worldWait(
      serverPort,
      session.token,
      (world) => Number(world?.resources?.g ?? 0) > previousGold,
      'the server to grant the next daily bonus',
    );
  }
  if (Number(enriched?.resources?.g ?? 0) < EXPANSION.coins + 1) {
    throw new Error('the daily bonus could not fund the expansion within five days');
  }
  console.log(
    `  UI: the server granted daily-bonus gold up to ${Number(enriched.resources.g)} ` +
      `so the rendered purchase could be afforded`,
  );
  const goldWithFunds = Number(enriched.resources.g);
  const cashWithFunds = Number(enriched.resources.c);
  await domClickPlain(page, '#ui .swl-expansion button.swl-expansion-buy', 'Expand button with funds');
  const paidExpansion = await worldWait(
    serverPort,
    session.token,
    (world) => (world?.maps?.[0]?.expansions ?? []).length === ownedBefore.length + 1,
    'the server to add the bought expansion tile',
  );
  const ownedAfter = paidExpansion?.maps?.[0]?.expansions ?? [];
  const newTile = ownedAfter.find((tile) => !ownedBefore.includes(tile));
  if (!Number.isInteger(newTile) || newTile <= 0) {
    throw new Error(`the server added no valid tile id: ${JSON.stringify(ownedAfter)}`);
  }
  const goldDelta = goldWithFunds - Number(paidExpansion.resources.g);
  const cashDelta = cashWithFunds - Number(paidExpansion.resources.c);
  if (goldDelta !== EXPANSION.coins || cashDelta !== EXPANSION.cash) {
    throw new Error(
      `the expansion charged ${goldDelta} gold / ${cashDelta} cash, ` +
        `not the content price (${EXPANSION.coins} / ${EXPANSION.cash})`,
    );
  }
  console.log(
    `  UI: the rendered Expand button bought tile ${newTile}; the server charged ` +
      `exactly ${goldDelta} gold / ${cashDelta} cash and added it to its own save`,
  );

  // A team is only accepted on the four level-40 quests. a fresh e2e player
  // cannot reach them legitimately, so the rendered briefing is checked to
  // have no team picker, and the server is checked to refuse a forged team on
  // this non-team quest. The team-selection happy path is proved by the
  // HTTP/unit suite, not by fabricating a player level here.
  const forgedTeam = await page.evaluate(
    `(async () => {
       const handle = window.__swl;
       if (!handle) return {error: 'the client has no handle'};
       const result = await handle.startQuest(${JSON.stringify(WEEKLY.id)}, 1,
         [{unitId: 1001, count: 1}]);
       return {ok: result.ok, status: result.status};
     })()`,
  );
  if (!forgedTeam || forgedTeam.error || forgedTeam.ok) {
    throw new Error(`the server accepted a forged team on a non-team quest: ${JSON.stringify(forgedTeam)}`);
  }
  console.log(`  UI: a forged team was refused on the non-team quest (HTTP ${forgedTeam.status})`);

  // Open the weekly quest from the chapter map, through the rendered slot.
  // The map is a requested surface, not an always-mounted panel.
  await openSurface(page, 'chapters', '#ui .swl-chapter');
  const slotSelector = '#ui .swl-chapter:first-child .swl-chapter-quests > button:first-child';
  const slot = await page.evaluate(
    `(() => { const e = document.querySelector(${JSON.stringify(slotSelector)});` +
      ` return e ? {tag: e.tagName, title: e.getAttribute('title')} : null; })()`,
  );
  if (!slot || slot.tag !== 'BUTTON') {
    throw new Error('the open weekly quest slot is not a rendered button');
  }
  const cashBeforeQuest = cashOf(await worldOf(serverPort, session.token));
  await domClick(
    page,
    slotSelector,
    "document.querySelector('#ui .swl-dialog-title')?.textContent ?? ''",
    'weekly quest slot',
  );
  const radios = await page.evaluate(
    "document.querySelectorAll('#ui .swl-dialog .swl-quest-difficulty input[type=radio]').length",
  );
  if (radios !== 3) throw new Error(`the briefing drew ${radios} difficulty choices, not 3`);
  // The weekly quest is not one of the four level-40 team quests, so the
  // rendered briefing must not offer a team picker for it.
  const teamPicker = await domValue(
    page,
    "!!document.querySelector('#ui .swl-dialog [data-swl-team-picker]')",
  );
  if (teamPicker !== false) {
    throw new Error('a non-team quest drew a team picker');
  }
  await domClick(
    page,
    '#ui .swl-dialog button.swl-quest-primary',
    "document.querySelectorAll('#ui .swl-dialog .swl-quest-roster .swl-quest-unit').length",
    'Start mission button',
  );
  const rosterSize = await domWait(
    page,
    "document.querySelectorAll('#ui .swl-dialog .swl-quest-roster .swl-quest-unit').length",
    (v) => v >= WEEKLY.elements.length,
    'the quest roster',
  );
  const combatSignature =
    "JSON.stringify({c: document.querySelector('#ui .swl-dialog .swl-quest-counters')?.textContent ?? '', r: document.querySelector('#ui .swl-dialog .swl-quest-roster')?.textContent ?? ''})";
  const killed = () =>
    domValue(
      page,
      `(() => {
         const rows = Array.from(document.querySelectorAll('#ui .swl-dialog .swl-quest-counter'));
         const row = rows.find((r) => r.querySelector('dt')?.textContent === 'botsKilled');
         return row ? Number(row.querySelector('dd')?.textContent ?? 0) : 0;
       })()`,
    );
  let reported = false;
  for (let guard = 0; guard < 16; guard++) {
    if ((await killed()) >= WEEKLY.elements.length) break;
    const hasKillReport = await domValue(
      page,
      "!!document.querySelector('#ui .swl-dialog button[data-swl-action=\"kill-report\"]')",
    );
    if (hasKillReport && !reported) {
      // The strictly two-argument `killed` write, from a rendered button.
      await domClickPlain(
        page,
        '#ui .swl-dialog button[data-swl-action="kill-report"]',
        'Report kill button',
      );
      await worldWait(
        serverPort,
        session.token,
        (world) =>
          (world?.privateState?.activeQuest?.script?.destroyed ?? []).length >= 1,
        'the server to record the reported kill',
      );
      reported = true;
      console.log('  UI: reported a server-verified kill with the two-argument builder');
      continue;
    }
    // Quest gestures are guarded against duplicate in-flight requests, so the
    // button is disabled until the previous strike settles. Wait for it rather
    // than racing the guard; the server still decides every outcome.
    await domWait(
      page,
      "document.querySelectorAll('#ui .swl-dialog button[data-swl-action=\"strike\"]:not([disabled])').length",
      (value) => value >= 1,
      'an enabled Strike button after the previous request settled',
    );
    await domClick(
      page,
      '#ui .swl-dialog button[data-swl-action="strike"]:not([disabled])',
      combatSignature,
      'Strike button',
    );
  }
  if (!reported) throw new Error('no dead element ever offered the two-argument Report kill');
  if ((await killed()) < WEEKLY.elements.length) {
    throw new Error('the rendered strikes did not move the server\'s kill counter to five');
  }
  console.log(`  UI: strikes on ${rosterSize} rendered roster rows moved botsKilled to five`);

  // Finish is a request. The server decides the win and pays the reward.
  // The wallet is read immediately before the click so every row in the
  // result can be checked against the exact delta that followed it.
  const walletBeforeFinish = await worldOf(serverPort, session.token);
  await domClick(
    page,
    '#ui .swl-dialog button[data-swl-action="end"]',
    "document.querySelector('#ui .swl-dialog .swl-quest-won')?.textContent ?? ''",
    'Finish quest button',
  );
  const wonText = await domValue(
    page,
    "document.querySelector('#ui .swl-dialog .swl-quest-won')?.textContent ?? ''",
  );
  if (!/server completed/i.test(String(wonText))) {
    throw new Error(`the victory dialog did not confirm the server's win: ${wonText}`);
  }
  const resultText = await domValue(
    page,
    "document.querySelector('#ui .swl-dialog')?.textContent ?? ''",
  );
  console.log(`  UI: the server's result dialog read "${String(resultText).trim()}"`);
  const awardedWorld = await worldOf(serverPort, session.token);
  const progress = awardedWorld?.privateState?.questProgress;
  if (!progress?.awarded?.includes(WEEKLY.id)) {
    throw new Error('the server did not record the weekly award');
  }
  if (!(progress.ranks?.[String(WEEKLY.playIndex)] >= 1)) {
    throw new Error('the server did not record the weekly rank');
  }
  if (!(cashOf(awardedWorld) > cashBeforeQuest)) {
    throw new Error('the server paid no cash for the weekly quest');
  }
  // Every rendered reward row must be exactly what the wallet received, and
  // the persisted receipt must hold the same rows. The client computes no
  // amount; it only formats the server's result.
  const rewardRows = await domValue(
    page,
    `Array.from(document.querySelectorAll('#ui .swl-dialog [data-swl-rewards] [data-swl-reward]'))
       .map((li) => ({
         resource: li.getAttribute('data-swl-reward'),
         text: li.textContent ?? '',
         amount: Number((li.textContent ?? '').split('+').pop().trim()),
       }))`,
  );
  if (!Array.isArray(rewardRows) || rewardRows.length === 0) {
    throw new Error('the result dialog drew no authoritative reward rows');
  }
  const walletBefore = walletBeforeFinish?.resources ?? {};
  const walletAfter = awardedWorld?.resources ?? {};
  for (const row of rewardRows) {
    const key = WALLET_KEY[row.resource];
    if (!key) throw new Error(`the result named an unknown resource: ${row.resource}`);
    if (!Number.isFinite(row.amount)) {
      throw new Error(`the ${row.resource} row has no amount: "${row.text}"`);
    }
    const delta = Number(walletAfter[key] ?? 0) - Number(walletBefore[key] ?? 0);
    if (delta !== row.amount) {
      throw new Error(
        `the ${row.resource} row says +${row.amount} but the server paid ${delta}`,
      );
    }
  }
  const receipt = awardedWorld?.privateState?.lastQuestReward;
  if (!receipt || receipt.questId !== WEEKLY.id || !Array.isArray(receipt.rewards)) {
    throw new Error(`the server kept no reward receipt: ${JSON.stringify(receipt)}`);
  }
  if (receipt.rewards.length !== rewardRows.length) {
    throw new Error('the receipt and the rendered rows disagree on their length');
  }
  for (let index = 0; index < rewardRows.length; index++) {
    const row = rewardRows[index];
    const stored = receipt.rewards[index];
    if (stored?.resource !== row.resource || Number(stored?.amount) !== row.amount) {
      throw new Error(`receipt row ${index} disagrees with the rendered row`);
    }
  }
  console.log(
    `  UI: ${rewardRows.length} reward row(s) match the wallet delta and the persisted receipt ` +
      `(${rewardRows.map((row) => `${row.resource} +${row.amount}`).join(', ')})`,
  );

  // A replay of the same quest must not pay twice. Drive it through the same
  // rendered controls, then check both the dialog and the server's wallet.
  await domClick(
    page,
    '#ui .swl-dialog button.swl-dialog-close',
    "!!document.querySelector('#ui .swl-dialog')",
    'reward dialog Close button',
  );
  const cashBeforeReplay = cashOf(await worldOf(serverPort, session.token));
  await openSurface(page, 'chapters', '#ui .swl-chapter');
  await domClick(
    page,
    slotSelector,
    "document.querySelector('#ui .swl-dialog-title')?.textContent ?? ''",
    'weekly quest slot on replay',
  );
  await domClick(
    page,
    '#ui .swl-dialog button.swl-quest-primary',
    "document.querySelectorAll('#ui .swl-dialog .swl-quest-roster .swl-quest-unit').length",
    'Start mission button on replay',
  );
  for (let guard = 0; guard < 16; guard++) {
    if ((await killed()) >= WEEKLY.elements.length) break;
    await domClick(
      page,
      '#ui .swl-dialog button[data-swl-action="strike"]:not([disabled])',
      combatSignature,
      'Strike button on replay',
    );
  }
  await domClick(
    page,
    '#ui .swl-dialog button[data-swl-action="end"]',
    "document.querySelector('#ui .swl-dialog .swl-quest-lost')?.textContent ?? ''",
    'Finish quest button on replay',
  );
  const refusal = await domValue(
    page,
    "document.querySelector('#ui .swl-dialog .swl-quest-lost')?.textContent ?? ''",
  );
  if (!/already-awarded|not finished/i.test(String(refusal))) {
    throw new Error(`the replay produced no refusal dialog ("${refusal}")`);
  }
  const afterReplay = await worldOf(serverPort, session.token);
  if (cashOf(afterReplay) !== cashBeforeReplay) {
    throw new Error(`the replay paid a second reward (${cashBeforeReplay} -> ${cashOf(afterReplay)})`);
  }
  const awards = afterReplay?.privateState?.questProgress?.awarded ?? [];
  if (awards.filter((id) => id === WEEKLY.id).length !== 1) {
    throw new Error(`the server's award list is not unique: ${JSON.stringify(awards)}`);
  }
  console.log(`  UI: replay refused with "${String(refusal).trim()}" and paid no second reward`);

  // Reload the client: the world and the quest rank have to survive it.
  page.loaded = false;
  await page.send('Page.reload', {});
  await page.waitForLoad();
  const reloaded = await page.waitForStatus(['started', 'failed']);
  if (!String(reloaded).startsWith('started')) throw new Error(`the reloaded client said "${reloaded}"`);
  // The replay's end_quest was refused, so the server still holds that active
  // quest. A reloaded client has to restore its combat panel from /api/world,
  // not from browser memory.
  const restored = await domValue(
    page,
    "!!document.querySelector('#ui .swl-dialog .swl-quest-roster')",
  );
  if (!restored) {
    throw new Error('the reloaded client did not restore the server\'s active quest');
  }
  const persisted = await worldOf(serverPort, session.token);
  if (!persisted?.privateState?.questProgress?.awarded?.includes(WEEKLY.id)) {
    throw new Error('the award did not survive the client reload');
  }
  if (!persisted?.privateState?.activeQuest) {
    throw new Error('the active quest did not survive the client reload');
  }
  console.log('  UI: after a client reload the active quest and the server award are still there');

  // --- G5.2: the receipt and the production cycle survive a reload --------
  const reloadedReceipt = persisted?.privateState?.lastQuestReward;
  if (!reloadedReceipt || reloadedReceipt.questId !== receipt.questId ||
      JSON.stringify(reloadedReceipt.rewards) !== JSON.stringify(receipt.rewards)) {
    throw new Error('the reward receipt did not survive the client reload');
  }
  const reloadedFactory = factoryOf(persisted);
  if (Number(reloadedFactory?.[6]?.['cp']) !== production.cp ||
      Number(reloadedFactory?.[6]?.['lastAccruedAt']) !== production.lastAccruedAt) {
    throw new Error('the chosen production cycle did not survive the client reload');
  }
  // The result screen can be rebuilt from the persisted receipt, without
  // replaying end_quest. The rows must still be the server's original ones.
  const rebuilt = await page.evaluate('window.__swl ? window.__swl.showLastReward() : false');
  if (rebuilt !== true) {
    throw new Error('the client could not rebuild the result from the receipt');
  }
  await domWait(
    page,
    "document.querySelectorAll('#ui .swl-dialog [data-swl-rewards] [data-swl-reward]').length",
    (v) => v === rewardRows.length,
    'the receipt-backed reward rows after reload',
  );
  const rebuiltRows = await domValue(
    page,
    `Array.from(document.querySelectorAll('#ui .swl-dialog [data-swl-rewards] [data-swl-reward]'))
       .map((li) => ({resource: li.getAttribute('data-swl-reward'),
                      amount: Number((li.textContent ?? '').split('+').pop().trim())}))`,
  );
  if (JSON.stringify(rebuiltRows) !== JSON.stringify(
      rewardRows.map((row) => ({resource: row.resource, amount: row.amount})))) {
    throw new Error('the rebuilt reward dialog differs from the one the server paid');
  }
  console.log(
    `  UI: after reload the receipt rebuilt ${rewardRows.length} reward row(s) and ` +
      `the ${production.cp === 1 ? 'five-minute' : 'chosen'} cycle is still ${production.lastAccruedAt}`,
  );

  return {
    playerId,
    password: 'correct horse',
    receipt: { questId: receipt.questId, rank: receipt.rank, rewards: receipt.rewards },
    production,
  };
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

  const QUEST = smallestEventQuest();
  const KILL = killQuest();
  console.log(
    `  quests: ${QUEST.questId} (${QUEST.actionType} × ${QUEST.count}) ` +
      `and ${KILL.questId} (kill ${KILL.ref})`,
  );

  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'swl-e2e-'));
  // The deterministic clock lives outside the database directory, so it
  // survives the server restart below and both server processes share it.
  const clockDir = await mkdtemp(path.join(os.tmpdir(), 'swl-e2e-clock-'));
  clockFile = path.join(clockDir, 'offset.txt');
  clockOffset = 0;
  writeFileSync(clockFile, '0\n');
  // **Free** ports: a stray server from an earlier run must not be able
  // to answer this one's requests, or hold the port.
  const base = 8100 + Math.floor(Math.random() * 200);
  const serverPort = base;
  const clientPort = base + 200;
  let devToolsPort = 9332;

  const server = await startServer(dataDir, serverPort);
  // Every server started in this run, so the teardown kills them all — even
  // the one that is replaced when the server is restarted for the quest.
  const serverHandles = [server];
  let questPlayer = null;
  // The players registered through the rendered form, for the restart check.
  const uiQuestPlayers = [];
  const client = await serve(clientPort, serverPort);

  const failures = [];
  const ran = [];
  const notRun = [];

  try {
    // --- 1. The player registers, through the real server ----------------
    const session = await register(serverPort, 'e2e-player', 'correct horse');
    console.log(`  registered "e2e-player"`);

    // A **second** player, so the neighbour strip has somebody in it.
    await register(serverPort, 'e2e-neighbour', 'correct horse');
    console.log('  registered "e2e-neighbour"');

    // The credential is persisted: the post-quest restart below signs the
    // browser's player in from the same database and checks the award. A
    // second server opened here would leave PGlite's data directory unable
    // to be reopened after the browser session, so there is only one restart.

    for (const entry of BROWSERS) {
      if (only && entry.name !== only) continue;
      const browser = findBrowser(entry.name);
      if (!browser) {
        notRun.push(entry.name);
        continue;
      }
      console.log(`  ${entry.name}: `);

      // A **fresh player** for each browser: the tutorial is a
      // once-per-player sequence, and a second browser over the same
      // player would correctly see no tutorial at all.
      const browserSession = await register(
        serverPort,
        `e2e-${entry.name.toLowerCase()}`,
        'correct horse',
      );

      const profile = await mkdtemp(path.join(os.tmpdir(), 'swl-e2e-'));
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

      let page = null;
      try {
        await waitForDevTools(devToolsPort);
        page = await Page.open(devToolsPort, `http://127.0.0.1:${clientPort}/`);

        // The client is signed in with the session the server issued.
        await page.evaluate(
          `window.localStorage.setItem('swl.session', ${JSON.stringify(
            JSON.stringify({
              token: browserSession.token,
              playerId: browserSession.playerId,
              expiresAt: browserSession.expiresAt,
            }),
          )})`,
        );
        page.loaded = false;
        await page.send('Page.reload', {});
        await page.waitForLoad();

        const status = await page.waitForStatus(['started', 'failed']);
        const [state, detail = ''] = String(status).split('|');
        if (state !== 'started') {
          failures.push(`${entry.name}: the client said "${state}" (${detail})`);
          console.log(`FAILED (${state}: ${detail})`);
          continue;
        }
        console.log(`started (${detail})`);

        // --- 2. The client sends a command -------------------------------
        // The client's own request builder and its own transport, and the
        // server's own rules decide the outcome. The client's `run` also
        // draws the answer, so the elapsed time is the **input-to-render
        // latency**: the time the player waits.
        const answer = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const result = await handle.run([handle.claimDailyBonus()]);
             return { ok: result.ok, latencyMs: result.latencyMs, sprites: result.sprites };
           })()`,
        );

        if (!answer || answer.error) {
          failures.push(`${entry.name}: ${answer?.error ?? 'the client sent nothing'}`);
          console.log('FAILED (the client sent nothing)');
          continue;
        }
        if (!answer.ok) {
          failures.push(`${entry.name}: the server refused the batch`);
          console.log('FAILED (the server refused the batch)');
          continue;
        }

        // The latency is measured against the budget.
        const broken = brokenBudgets({
          input_to_render_p95_ms: answer.latencyMs,
        });
        if (broken.length > 0) {
          for (const entry of broken) {
            failures.push(
              `${entry.name}: ${entry.value.toFixed(1)} ms (the limit is ${entry.limit})`,
            );
          }
          console.log(`FAILED (the latency was ${answer.latencyMs.toFixed(1)} ms)`);
          continue;
        }

        console.log(
          `the command was answered in ${answer.latencyMs.toFixed(1)} ms ` +
            `(${answer.sprites} sprite(s) drawn)`,
        );

        // The renderer has to have drawn something. A player with a town
        // sees it, and a client that draws **nothing** is a client that
        // is not playing the game.
        if (answer.sprites < 1) {
          failures.push(`${entry.name}: the client drew nothing (${answer.sprites} sprite(s))`);
          console.log('FAILED (the client drew nothing)');
          continue;
        }

        // The **interface** has to have drawn itself too. The top bar
        // shows the player's own resources, so a client that renders
        // the world and not the numbers is not playing the game either.
        const hud = await page.evaluate(
          "(() => { const bar = document.querySelector('#ui .swl-hud');" +
            " if (!bar) return { error: 'the interface drew no top bar' };" +
            " const gold = bar.querySelector('.swl-resource-gold .swl-readout-value');" +
            " return { gold: gold ? gold.textContent : '', text: bar.textContent ?? '' }; })()",
        );
        if (!hud || hud.error) {
          failures.push(`${entry.name}: ${hud?.error ?? 'the interface drew nothing'}`);
          console.log('FAILED (the interface drew nothing)');
          continue;
        }
        if (!/[\d]/.test(String(hud.gold ?? ''))) {
          failures.push(`${entry.name}: the top bar shows no gold ("${hud.gold}")`);
          console.log('FAILED (the top bar shows no numbers)');
          continue;
        }
        console.log(`  the top bar shows ${hud.gold} gold`);

        // The substitute fonts' **scale**. The client applies the
        // measured factor to the text, so the substitute occupies the
        // same width as the original did. The factor is a number, and
        // the file it comes from has to be served.
        const scale = await page.evaluate(
          `(async () => {
             const applied = getComputedStyle(document.documentElement)
               .getPropertyValue('--swl-font-scale-body').trim();
             const response = await fetch('/font-scale.json');
             const file = response.ok ? await response.json() : null;
             return {
               applied,
               served: response.ok,
               measured: file?.scales?.ArialRoundedBold ?? null,
             };
           })()`,
        );
        if (!scale || !Number.isFinite(Number(scale.applied))) {
          failures.push(`${entry.name}: the font scale is not a number ("${scale?.applied}")`);
          console.log('FAILED (the font scale is not a number)');
          continue;
        }
        if (!scale.served || !Number.isFinite(Number(scale.measured))) {
          failures.push(`${entry.name}: the measured font scale was not served`);
          console.log('FAILED (the measured font scale was not served)');
          continue;
        }
        console.log(
          `  the substitute font is scaled by ${scale.applied} (the file says ${scale.measured})`,
        );

        // The player can **build**. The server owns the rules, so the
        // command has to be checked against the content and the map:
        // a House I on a free tile, paid for in wood.
        const built = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const result = await handle.run([handle.buy(1, 60, 60, 'b')]);
             return { ok: result.ok, sprites: result.sprites };
           })()`,
        );
        if (!built || built.error || !built.ok) {
          failures.push(
            `${entry.name}: the server refused the building (${built?.error ?? 'not ok'})`,
          );
          console.log('FAILED (the server refused the building)');
          continue;
        }
        if (built.sprites < 2) {
          failures.push(
            `${entry.name}: the house was not placed (${built.sprites} sprite(s) drawn)`,
          );
          console.log('FAILED (the house was not placed)');
          continue;
        }
        console.log(`  the house was placed (${built.sprites} sprites drawn)`);

        // The town has to be **on the screen**. A sprite that is off
        // the stage is in the scene but not on the display, and a player
        // who cannot see their town cannot play.
        const visible = await page.evaluate(
          '(() => { const h = window.__swl; return h ? h.visibleSprites() : 0; })()',
        );
        if (!visible || visible < 1) {
          failures.push(`${entry.name}: the town is not on the screen (${visible} sprite(s))`);
          console.log('FAILED (the town is not on the screen)');
          continue;
        }
        console.log(`  the town is on the screen (${visible} sprite(s) visible)`);

        // A **click on the map** selects what is under it. The click
        // is a gesture: the client looks the tile up and selects the
        // building there.
        const picked = await page.evaluate(
          `(() => {
             const canvas = document.querySelector('#game canvas');
             if (!canvas) return { error: 'the client has no canvas' };
             const rect = canvas.getBoundingClientRect();
             const event = new PointerEvent('pointerdown', {
               clientX: rect.left + rect.width / 2,
               clientY: rect.top + rect.height / 2,
               bubbles: true,
             });
             canvas.dispatchEvent(event);
             const handle = window.__swl;
             return { selected: handle ? handle.selectedItem() : null };
           })()`,
        );
        if (!picked || picked.error) {
          failures.push(`${entry.name}: ${picked?.error ?? 'the click did not answer'}`);
          console.log('FAILED (the click did not answer)');
          continue;
        }
        if (!picked.selected) {
          failures.push(`${entry.name}: the click selected nothing`);
          console.log('FAILED (the click selected nothing)');
          continue;
        }
        console.log(`  the click selected the building (item ${picked.selected})`);

        // The **build menu** is wired to the placement. Picking an item
        // begins a placement; it does not build anything, and the
        // server still decides the outcome. The menu is a requested surface.
        await openSurface(page, 'build', '#ui .swl-build-item');
        const menu = await page.evaluate(
          `(() => {
             const item = document.querySelector('#ui .swl-build-item:not(.swl-build-locked) button');
             if (!item) return { error: 'the build menu has no items' };
             const name = item.querySelector('.swl-build-name');
             item.click();
             return { name: name ? name.textContent : '' };
           })()`,
        );
        if (!menu || menu.error) {
          failures.push(`${entry.name}: ${menu?.error ?? 'the build menu did not answer'}`);
          console.log('FAILED (the build menu did not answer)');
          continue;
        }
        const notice = await page.evaluate(
          "(() => { const e = document.querySelector('#ui .swl-placing'); return e ? e.textContent : ''; })()",
        );
        if (!notice) {
          failures.push(`${entry.name}: picking an item began no placement`);
          console.log('FAILED (picking an item began no placement)');
          continue;
        }
        console.log(`  picking ${menu.name} began a placement (${notice})`);

        // The **goal panel** is drawn. The goals are the content's and
        // the player's progress is the server's, so the panel shows
        // three slots with the goals' own titles. Goals are one surface.
        await openSurface(page, 'goals', '#ui .swl-goals');
        const goals = await page.evaluate(
          `(() => {
             const panel = document.querySelector('#ui .swl-goals');
             if (!panel) return { error: 'the goal panel is missing' };
             return {
               slots: panel.querySelectorAll('.swl-goal-slot').length,
               titles: Array.from(panel.querySelectorAll('.swl-goal-title'))
                 .map((e) => e.textContent),
             };
           })()`,
        );
        if (!goals || goals.error) {
          failures.push(`${entry.name}: ${goals?.error ?? 'the goal panel did not answer'}`);
          console.log('FAILED (the goal panel did not answer)');
          continue;
        }
        if (goals.slots !== 3) {
          failures.push(`${entry.name}: the goal panel has ${goals.slots} slot(s), not 3`);
          console.log('FAILED (the goal panel has the wrong number of slots)');
          continue;
        }
        console.log(`  the goal panel shows ${goals.titles.filter(Boolean).length} goal(s)`);

        // The **chapter map** is drawn: the four chapters and their
        // quest slots, with the client's own titles. One surface at a time.
        await openSurface(page, 'chapters', '#ui .swl-chapter');
        const map = await page.evaluate(
          `(() => {
             const chapters = document.querySelectorAll('#ui .swl-chapter');
             if (chapters.length === 0) return { error: 'the chapter map is missing' };
             return {
               chapters: chapters.length,
               slots: document.querySelectorAll('#ui .swl-quest-slot').length,
               titles: Array.from(document.querySelectorAll('#ui .swl-chapter-title'))
                 .map((e) => e.textContent),
             };
           })()`,
        );
        if (!map || map.error) {
          failures.push(`${entry.name}: ${map?.error ?? 'the chapter map did not answer'}`);
          console.log('FAILED (the chapter map did not answer)');
          continue;
        }
        if (map.chapters !== 4) {
          failures.push(`${entry.name}: the chapter map has ${map.chapters} chapter(s), not 4`);
          console.log('FAILED (the chapter map has the wrong number of chapters)');
          continue;
        }
        console.log(`  the chapter map shows ${map.chapters} chapters (${map.slots} slots)`);

        // The **tutorial** is drawn from the client's own steps, and its
        // progression is the server's. A new player sees the welcome,
        // the step numbers are the client's own, and walking the
        // sequence is recorded server-side rather than in the browser.
        const tutorialStart = await page.evaluate(
          `(() => {
             const box = document.querySelector('#ui .swl-tutorial');
             if (!box) return { error: 'the tutorial is missing' };
             return {
               step: window.__swl ? window.__swl.tutorialStep() : null,
               title: box.querySelector('.swl-tutorial-title')?.textContent ?? '',
               position: box.querySelector('.swl-tutorial-step')?.textContent ?? '',
             };
           })()`,
        );
        if (!tutorialStart || tutorialStart.error) {
          failures.push(
            `${entry.name}: ${tutorialStart?.error ?? 'the tutorial did not answer'}`,
          );
          console.log('FAILED (the tutorial is missing)');
          continue;
        }
        if (tutorialStart.step !== 100) {
          failures.push(
            `${entry.name}: the tutorial starts at step ${tutorialStart.step}, not 100`,
          );
          console.log('FAILED (the tutorial starts at the wrong step)');
          continue;
        }
        if (!String(tutorialStart.title).trim()) {
          failures.push(`${entry.name}: the tutorial drew no title`);
          console.log('FAILED (the tutorial drew no title)');
          continue;
        }
        console.log(
          `  the tutorial opens on "${tutorialStart.title}" (${tutorialStart.position})`,
        );

        // Walk the whole sequence. The client advances one step at a
        // time and tells the server; the server keeps the furthest step.
        const walked = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const seen = [];
             for (let guard = 0; guard < 60 && handle.tutorialStep() !== null; guard++) {
               const before = handle.tutorialStep();
               const result = await handle.advanceTutorial();
               if (!result.ok) {
                 return { error: 'the server refused step ' + before };
               }
               seen.push(before);
             }
             return { seen, step: handle.tutorialStep() };
           })()`,
        );
        if (!walked || walked.error) {
          failures.push(`${entry.name}: ${walked?.error ?? 'the tutorial did not walk'}`);
          console.log('FAILED (the tutorial did not walk)');
          continue;
        }
        if (walked.step !== null) {
          failures.push(`${entry.name}: the tutorial stopped at step ${walked.step}`);
          console.log('FAILED (the tutorial did not finish)');
          continue;
        }
        if (!Array.isArray(walked.seen) || walked.seen.length < 27) {
          failures.push(
            `${entry.name}: the tutorial walked ${walked.seen?.length ?? 0} step(s), not 27`,
          );
          console.log('FAILED (the tutorial walked too few steps)');
          continue;
        }
        // Finishing is the server's record, not the browser's.
        const afterTutorial = await fetch(
          `http://127.0.0.1:${serverPort}/api/world`,
          { headers: { authorization: `Bearer ${browserSession.token}` } },
        ).then((response) => response.json());
        const record = afterTutorial?.privateState?.tutorial;
        if (!record || record.complete !== true) {
          failures.push(`${entry.name}: the server did not record the finished tutorial`);
          console.log('FAILED (the server did not record the finished tutorial)');
          continue;
        }
        const overlayGone = await page.evaluate(
          "!document.querySelector('#ui .swl-tutorial')",
        );
        if (!overlayGone) {
          failures.push(`${entry.name}: the tutorial is still drawn after finishing`);
          console.log('FAILED (the tutorial is still drawn)');
          continue;
        }
        console.log(
          `  the tutorial walked ${walked.seen.length} steps and the server recorded it`,
        );

        // --- Phase 1: the game-first presentation, at rest ----------------
        // These are ADDITIONS. None of the gameplay checks above or below is
        // changed, skipped or relaxed. A failure is recorded and the session
        // continues, so the existing assertions still run in full.
        const visual = await visualProbe(page);
        console.log(
          `  UI visual: green ${(visual.greenRatio ?? 0).toFixed(3)}, ` +
            `${visual.surfaceCount} surface(s), sprites ${visual.drawnSprites}, ` +
            `centre ${visual.centreTarget}, rects intersect ${visual.neighbourBuildIntersect}`,
        );
        for (const problem of visualFailures(visual, entry.name)) {
          failures.push(`${entry.name}: ${problem}`);
          console.log(`FAILED (${problem})`);
        }
        if (visual.consoleErrors?.length) {
          for (const error of visual.consoleErrors) {
            failures.push(`${entry.name}: console error: ${error}`);
          }
        }

        // --- 3. The authoritative quest workflow --------------------------
        // The real client starts the smallest event quest, asks the server to
        // apply its own strike and event actions, reports a kill with its
        // two-argument builder, and asks the server to end the quest. Every
        // counter and the reward are the server's; the browser only sends
        // requests and reads answers.
        const quest = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const id = ${JSON.stringify(QUEST.questId)};
             const actionType = ${JSON.stringify(QUEST.actionType)};
             const eventRef = ${JSON.stringify(QUEST.ref)};
             const counterName = ${JSON.stringify(QUEST.counterName)};
             const count = ${QUEST.count};

             const started = await handle.startQuest(id, 1);
             if (!started.ok) {
               return { error: 'the server refused the quest start', status: started.status };
             }
             const active = handle.activeQuest();
             if (!active || active.questId !== id) {
               return { error: 'the client saw no active quest' };
             }
             const refs = Object.keys(active.elements);
             if (refs.length === 0) return { error: 'the active quest has no roster' };
             const rosterRef = refs[0];

             // A forged ref is not on the quest's event list: the server
             // refuses it rather than moving a counter for it.
             const forged = await handle.questAction(id, {
               type: actionType, ref: 'not-a-real-ref',
             });
             if (forged.ok) return { error: 'a forged event was accepted' };

             // The two-argument kill report is the client's, but roster
             // membership is not proof of a kill: the server's own ledger
             // still marks the element alive, so this write is refused.
             const early = await handle.send([handle.reportQuestKill(rosterRef)]);
             if (!early.response || early.response.ok !== false) {
               return { error: 'a kill was accepted without a server kill' };
             }

             // A server-authoritative strike on an extracted roster ref lands;
             // its damage is the server's, from its own seed.
             const strike = await handle.questAction(id, { type: 'strike', ref: rosterRef });
             if (!strike.ok || !strike.body || !strike.body.elements[rosterRef]) {
               return { error: 'the server refused a strike', status: strike.status };
             }
             const hp = strike.body.elements[rosterRef].hp;

             // The event counters are seeded and moved by the server only.
             // The client names the event's own ref, never an amount.
             let last = null;
             for (let i = 0; i < count; i++) {
               const action = await handle.questAction(id, { type: actionType, ref: eventRef });
               if (!action.ok) {
                 return { error: 'the server refused an event', status: action.status };
               }
               last = action;
             }
             const progress = last && last.body ? last.body.counters[counterName] : null;
             if (!(progress >= count)) {
               return { error: 'the server did not move its counter', counter: progress };
             }

             // Only the server decides the win and grants the reward. The
             // client sends the quest id and the difficulty it played.
             const ended = await handle.send([handle.endQuest(id, 1)]);
             if (!ended.response || !ended.response.ok) {
               return {
                 error: 'the server refused end_quest',
                 outcome: ended.response ? ended.response.outcomes[0] : ended.reason,
                 detail: ended.detail,
               };
             }
             return { questId: started.body.questId, strikeHp: hp, counter: progress };
           })()`,
        );
        if (!quest || quest.error) {
          const detail = quest?.error ?? 'the quest did not run';
          failures.push(`${entry.name}: ${detail} ${JSON.stringify(quest)}`);
          console.log(`FAILED (${detail} ${JSON.stringify(quest)})`);
          continue;
        }
        if (quest.questId !== QUEST.questId || !(quest.counter >= QUEST.count)) {
          failures.push(`${entry.name}: the quest answered ${JSON.stringify(quest)}`);
          console.log('FAILED (the quest answered wrongly)');
          continue;
        }
        console.log(
          `  the client drove ${QUEST.questId}: forged and early events refused, ` +
            `${QUEST.count} server events moved the counter to ${quest.counter}`,
        );

        // The reward is in the server's own progress record, not the
        // browser's. Read it back with the player's real token.
        const awardedWorld = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        const progress = awardedWorld?.privateState?.questProgress;
        if (!progress || !Array.isArray(progress.awarded) || !progress.awarded.includes(QUEST.questId)) {
          failures.push(`${entry.name}: the server did not record the quest award`);
          console.log('FAILED (the quest award was not recorded)');
          continue;
        }
        if (!(progress.ranks?.[QUEST.playIndex] >= 1)) {
          failures.push(`${entry.name}: the server did not record the quest rank`);
          console.log('FAILED (the quest rank was not recorded)');
          continue;
        }
        if (awardedWorld?.privateState?.activeQuest) {
          failures.push(`${entry.name}: the active quest was not cleared after the award`);
          console.log('FAILED (the active quest was not cleared)');
          continue;
        }
        console.log(`  the server awarded ${QUEST.questId} and cleared the active quest`);

        // --- 3b. An accepted two-arg kill through the real client ----------
        // The per-kill builder is strictly two arguments. The server's own
        // strikes bring a roster element down (at most four of them), and only
        // then is the same builder accepted. The quest is then completed from
        // that server-owned state.
        const kill = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const id = ${JSON.stringify(KILL.questId)};
             const ref = ${JSON.stringify(KILL.ref)};

             const started = await handle.startQuest(id, 1);
             if (!started.ok) {
               return { error: 'the server refused the kill quest start', status: started.status };
             }
             const active = handle.activeQuest();
             if (!active || active.questId !== id || !active.elements[ref]) {
               return { error: 'the client saw no killable roster element' };
             }

             // Roster membership is not a kill: the same two-argument write
             // is refused before the server's strikes bring the element down.
             const early = await handle.send([handle.reportQuestKill(ref)]);
             if (!early.response || early.response.ok !== false) {
               return { error: 'an early kill was accepted' };
             }

             let strikes = 0;
             let last = null;
             for (let guard = 0; guard < 4; guard++) {
               const action = await handle.questAction(id, { type: 'strike', ref });
               if (!action.ok) {
                 return { error: 'the server refused a strike', status: action.status };
               }
               strikes++;
               last = action;
               if (last.body && last.body.elements[ref] && last.body.elements[ref].alive === false) break;
             }
             if (!last || !last.body || !last.body.elements[ref] || last.body.elements[ref].alive !== false) {
               return { error: 'the element survived four authoritative strikes' };
             }

             // The SAME two-argument builder is accepted now, because the
             // server's ledger proves the kill.
             const reported = await handle.send([handle.reportQuestKill(ref)]);
             if (!reported.response || !reported.response.ok) {
               return {
                 error: 'the server refused the two-argument kill',
                 outcome: reported.response ? reported.response.outcomes[0] : reported.reason,
                 detail: reported.detail,
               };
             }
             return { questId: started.body.questId, strikes, ref };
           })()`,
        );
        if (!kill || kill.error || kill.questId !== KILL.questId || kill.ref !== KILL.ref ||
            !Number.isInteger(kill.strikes) || kill.strikes < 1 || kill.strikes > 4) {
          const detail = kill?.error ?? 'the kill quest did not run';
          failures.push(`${entry.name}: ${detail} ${JSON.stringify(kill)}`);
          console.log(`FAILED (${detail} ${JSON.stringify(kill)})`);
          continue;
        }

        // The kill and the strike ledger are the server's, not the browser's.
        const killWorld = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        const killActive = killWorld?.privateState?.activeQuest;
        if (!killActive || !Array.isArray(killActive.script?.destroyed) ||
            !killActive.script.destroyed.includes(KILL.ref) ||
            killActive.ledger?.elements?.[KILL.ref]?.alive !== false ||
            !(killActive.ledger?.strikes?.[KILL.ref] >= 1)) {
          failures.push(`${entry.name}: the server did not record the accepted kill`);
          console.log('FAILED (the accepted kill was not recorded)');
          continue;
        }
        if (killWorld?.privateState?.questProgress?.awarded?.includes(KILL.questId)) {
          failures.push(`${entry.name}: the reward was paid before end_quest`);
          console.log('FAILED (the reward was paid before end_quest)');
          continue;
        }
        console.log(
          `  the two-arg kill was accepted after ${kill.strikes} server strike(s); ` +
            'the ledger proves it, no reward yet',
        );

        // Finish the quest: the server decides the win and pays the reward.
        const killEnd = await page.evaluate(
          `(async () => {
             const handle = window.__swl;
             if (!handle) return { error: 'the client has no handle' };
             const ended = await handle.send([handle.endQuest(${JSON.stringify(KILL.questId)}, 1)]);
             if (!ended.response || !ended.response.ok) {
               return {
                 error: 'the server refused the kill quest end',
                 outcome: ended.response ? ended.response.outcomes[0] : ended.reason,
                 detail: ended.detail,
               };
             }
             return { ok: true };
           })()`,
        );
        if (!killEnd || killEnd.error) {
          const detail = killEnd?.error ?? 'the kill quest did not end';
          failures.push(`${entry.name}: ${detail} ${JSON.stringify(killEnd)}`);
          console.log(`FAILED (${detail} ${JSON.stringify(killEnd)})`);
          continue;
        }
        const killAwarded = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        const killProgress = killAwarded?.privateState?.questProgress;
        if (!killProgress?.awarded?.includes(KILL.questId) ||
            !(killProgress.ranks?.[KILL.playIndex] >= 1) ||
            killAwarded?.privateState?.activeQuest) {
          failures.push(`${entry.name}: the server did not award the completed kill quest`);
          console.log('FAILED (the kill quest award was not recorded)');
          continue;
        }
        console.log(`  the server awarded ${KILL.questId} from the accepted kill`);

        // --- 3d. Q11's 240s timer is enforced from the server clock ----------
        // The deterministic clock fixture changes only the SERVER's
        // `Date.now()`; the browser's own clock, the game's rules and every
        // existing assertion are untouched. The real client starts Q11 (a
        // level-0 quest, so a fresh player may), the harness advances the
        // server clock past the spec's 240s limit, and the SAME client asks
        // for an action and for end_quest. The server must answer with its
        // typed quest-lost refusal and grant nothing. No client clock is
        // trusted and no win or loss is fabricated. Leaving Q11 active is
        // safe: playThroughDom below registers its own fresh player, so its
        // weekly-quest start is unaffected.
        const timedBefore = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        const cashBeforeTimeout = cashOf(timedBefore);
        const oilBeforeTimeout = Number(timedBefore?.resources?.o ?? 0);
        if ((timedBefore?.privateState?.questProgress?.awarded ?? []).includes(TIMED.id)) {
          failures.push(`${entry.name}: the e2e player already holds the Q11 award`);
          console.log('FAILED (Q11 was already awarded)');
          continue;
        }
        const timedStart = await page.evaluate(`(async () => {
           const handle = window.__swl;
           if (!handle) return { error: 'the client has no handle' };
           const started = await handle.startQuest(${JSON.stringify(TIMED.id)}, 1);
           if (!started.ok) {
             return { error: 'the server refused the timed quest start', status: started.status };
           }
           const active = handle.activeQuest();
           if (!active || active.questId !== ${JSON.stringify(TIMED.id)}) {
             return { error: 'the client saw no active timed quest' };
           }
           return { questId: active.questId };
         })()`);
        if (!timedStart || timedStart.error) {
          const detail = timedStart?.error ?? 'the timed quest did not start';
          failures.push(`${entry.name}: ${detail} ${JSON.stringify(timedStart)}`);
          console.log(`FAILED (${detail} ${JSON.stringify(timedStart)})`);
          continue;
        }
        // The server's own save, not the browser's presentation, must hold
        // the full 240 seconds at the moment the real client started it.
        const timedStartWorld = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        if (Number(timedStartWorld?.privateState?.activeQuest?.timeRemaining) !== TIMED.timeLimitSeconds) {
          failures.push(`${entry.name}: the server did not stamp Q11's ${TIMED.timeLimitSeconds}s timer`);
          console.log(`FAILED (the server did not stamp Q11's timer)`);
          continue;
        }
        console.log(
          `  the client started ${TIMED.id} with ${TIMED.timeLimitSeconds}s on the server's clock`,
        );

        // Advance the SERVER clock past the 240-second limit. This is the
        // same fixture the collection and daily-bonus steps already use: no
        // real time is slept and no production code gets a time override.
        advanceClock(TIMED.timeLimitSeconds + 1);

        // Reload recovery restores the combat dialog from the SERVER's saved
        // active quest, never from browser memory. The player then makes the
        // real Finish gesture and sees the typed refusal in the same result
        // dialog every other quest outcome uses. The browser's own clock is
        // deliberately left alone: a stale countdown is presentation only.
        page.loaded = false;
        await page.send('Page.reload', {});
        await page.waitForLoad();
        const timedStatus = await page.waitForStatus(['started', 'failed']);
        if (!String(timedStatus).startsWith('started')) {
          failures.push(`${entry.name}: the reloaded client said "${timedStatus}"`);
          console.log(`FAILED (the reloaded client said "${timedStatus}")`);
          continue;
        }
        await domWait(
          page,
          "!!document.querySelector('#ui .swl-dialog button[data-swl-action=\"end\"]')",
          (v) => v === true,
          'the restored Q11 combat dialog',
        );

        // An action on an expired mission is refused with the typed code,
        // through the client's own quest-action request builder and transport.
        const timedAction = await page.evaluate(`(async () => {
           const handle = window.__swl;
           if (!handle) return { error: 'the client has no handle' };
           const ref = Object.keys(handle.activeQuest()?.elements || {})[0];
           const acted = ref
             ? await handle.questAction(${JSON.stringify(TIMED.id)}, { type: 'strike', ref })
             : null;
           return { ok: acted ? acted.ok : null, code: acted ? (acted.serverError ?? null) : null };
         })()`);
        if (!timedAction || timedAction.error || timedAction.ok !== false ||
            timedAction.code !== 'quest-lost') {
          const detail = `the expired quest action drew ${JSON.stringify(timedAction)}`;
          failures.push(`${entry.name}: ${detail}`);
          console.log(`FAILED (${detail})`);
          continue;
        }

        // The rendered Finish gesture is the one a player makes. The result
        // dialog must show the server's typed refusal and draw no reward row.
        await domClick(
          page,
          '#ui .swl-dialog button[data-swl-action="end"]',
          "document.querySelector('#ui .swl-dialog .swl-quest-lost')?.textContent ?? ''",
          'Finish quest button on the expired Q11',
        );
        const refusalText = await domValue(
          page,
          "document.querySelector('#ui .swl-dialog .swl-quest-lost')?.textContent ?? ''",
        );
        if (!/quest-lost/i.test(String(refusalText))) {
          failures.push(
            `${entry.name}: the expired result dialog showed no quest-lost refusal (${refusalText})`,
          );
          console.log(`FAILED (the expired result dialog showed "${refusalText}")`);
          continue;
        }
        const rewardCount = await domValue(
          page,
          "document.querySelectorAll('#ui .swl-dialog [data-swl-rewards] [data-swl-reward]').length",
        );
        if (rewardCount !== 0) {
          failures.push(`${entry.name}: the expired result dialog drew ${rewardCount} reward row(s)`);
          console.log(`FAILED (the expired result dialog drew ${rewardCount} reward rows)`);
          continue;
        }
        const timedAfter = await fetch(`http://127.0.0.1:${serverPort}/api/world`, {
          headers: { authorization: `Bearer ${browserSession.token}` },
        }).then((response) => response.json());
        if (cashOf(timedAfter) !== cashBeforeTimeout ||
            Number(timedAfter?.resources?.o ?? 0) !== oilBeforeTimeout) {
          failures.push(`${entry.name}: an expired quest changed the wallet`);
          console.log('FAILED (an expired quest changed the wallet)');
          continue;
        }
        if ((timedAfter?.privateState?.questProgress?.awarded ?? []).includes(TIMED.id)) {
          failures.push(`${entry.name}: an expired quest was awarded`);
          console.log('FAILED (an expired quest was awarded)');
          continue;
        }
        console.log(
          `  UI: after advancing the server clock ${TIMED.timeLimitSeconds + 1}s, ` +
            `${TIMED.id} showed "${String(refusalText).trim()}" and refused the strike; ` +
            `no reward row, no oil or cash`,
        );

        questPlayer = { playerId: browserSession.playerId, password: 'correct horse' };

        // The **neighbour strip** lists the other players. The strip is
        // the server's list, and the client draws it at rest: return there
        // first so no requested surface is covering the bottom of the stage.
        await closeSurface(page);
        const strip = await page.evaluate(
          `(() => {
             const entries = document.querySelectorAll('#ui .swl-neighbour');
             return {
               count: entries.length,
               names: Array.from(entries)
                 .map((e) => e.querySelector('.swl-neighbour-name'))
                 .map((e) => (e ? e.textContent : '')),
             };
           })()`,
        );
        if (!strip || strip.count < 1) {
          failures.push(`${entry.name}: the neighbour strip is empty (${strip?.count ?? 0})`);
          console.log('FAILED (the neighbour strip is empty)');
          continue;
        }
        console.log(`  the neighbour strip shows ${strip.names.join(', ')}`);

        // The render loop's rate. In a **headless** browser this is not
        // the game's real frame rate - there is no GPU and the frames are
        // throttled - but it does prove the loop is running. The rate is
        // measured over a second, so the loop is given a moment to fill
        // that window.
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const rate = await page.evaluate(
          '(() => { const h = window.__swl; return h ? h.framesPerSecond() : 0; })()',
        );
        console.log(`  the render loop is running at ${Number(rate).toFixed(0)} frames a second`);

        // --- 3c. The whole loop through the rendered interface -------------
        // A fresh player, a real registration form, rendered controls for
        // every act, and the server's world as the evidence. The earlier
        // assertions above stay intact; this is an added, stronger session.
        try {
          const uiPlayer = await playThroughDom(page, serverPort, entry.name);
          uiQuestPlayers.push(uiPlayer);
        } catch (error) {
          const detail = String(error);
          failures.push(`${entry.name}: the DOM gameplay loop: ${detail}`);
          console.log(`FAILED (the DOM gameplay loop: ${detail})`);
        }

        ran.push(entry.name);
      } catch (error) {
        // A browser that **cannot be driven** is not run rather than
        // failed: the harness speaks the Chrome DevTools Protocol, and
        // some builds of the browsers do not open its port. The session
        // needs one browser that works, and the script fails when none
        // did.
        if (String(error).includes('did not open its debugging port')) {
          notRun.push(entry.name);
          console.log('NOT RUN (the browser did not open its debugging port)');
        } else {
          failures.push(`${entry.name}: ${String(error)}`);
          console.log(`FAILED (${String(error)})`);
        }
      } finally {
        if (page) await page.close(devToolsPort);
        child.kill();
        devToolsPort += 1;
      }
    }

    // --- 4. The award survives a server restart ---------------------------
    // The real client drove the workflow above. Here the server is stopped
    // and started again over the same database, a fresh credential signs the
    // player in, and the award is read from the server's world — not from a
    // browser that might simply be remembering it.
    if (questPlayer || uiQuestPlayers.length > 0) {
      const restartPort = serverPort + 2;
      // The database allows one writer. Stop the original server and wait for
      // it to release the data directory before reopening the same database.
      if (server.child.exitCode === null && server.child.signalCode === null) {
        const exited = new Promise((resolve) => server.child.once('exit', resolve));
        server.child.kill();
        await exited;
      }
      const restarted = await startServer(dataDir, restartPort);
      serverHandles.push(restarted);
      console.log('  the server was restarted with the same database');

      // The hook-driven player's two awards, as before.
      if (questPlayer) {
        const signIn = await fetch(`http://127.0.0.1:${restartPort}/api/session`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(questPlayer),
        });
        if (signIn.status !== 200) {
          failures.push(`the quest player could not sign in after the restart: ${signIn.status}`);
          console.log(`FAILED (sign-in after restart: ${signIn.status})`);
        } else {
          const fresh = await signIn.json();
          const persisted = await fetch(`http://127.0.0.1:${restartPort}/api/world`, {
            headers: { authorization: `Bearer ${fresh.token}` },
          }).then((response) => response.json());
          const saved = persisted?.privateState?.questProgress;
          for (const award of [
            { questId: QUEST.questId, playIndex: QUEST.playIndex },
            { questId: KILL.questId, playIndex: KILL.playIndex },
          ]) {
            if (!saved || !Array.isArray(saved.awarded) || !saved.awarded.includes(award.questId)) {
              failures.push(`the ${award.questId} award did not survive the server restart`);
              console.log(`FAILED (the ${award.questId} award did not survive the restart)`);
            } else if (!(saved.ranks?.[award.playIndex] >= 1)) {
              failures.push(`the ${award.questId} rank did not survive the server restart`);
              console.log(`FAILED (the ${award.questId} rank did not survive the restart)`);
            } else {
              console.log(`  the player signed in again and ${award.questId} was still awarded`);
            }
          }
        }
      }

      // The players who played the whole loop through the rendered interface.
      for (const player of uiQuestPlayers) {
        const signIn = await fetch(`http://127.0.0.1:${restartPort}/api/session`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(player),
        });
        if (signIn.status !== 200) {
          failures.push(`the UI player ${player.playerId} could not sign in after the restart`);
          console.log(`FAILED (sign-in after restart for ${player.playerId}: ${signIn.status})`);
          continue;
        }
        const fresh = await signIn.json();
        const persisted = await fetch(`http://127.0.0.1:${restartPort}/api/world`, {
          headers: { authorization: `Bearer ${fresh.token}` },
        }).then((response) => response.json());
        const saved = persisted?.privateState?.questProgress;
        if (!saved?.awarded?.includes(WEEKLY.id) || !(saved.ranks?.[String(WEEKLY.playIndex)] >= 1)) {
          failures.push(`the ${WEEKLY.id} award from the UI loop did not survive the restart`);
          console.log(`FAILED (the UI award did not survive the restart)`);
        } else {
          console.log(`  ${player.playerId} signed in again and ${WEEKLY.id} was still awarded`);
        }
        // G5.2: the persisted receipt and the chosen production cycle must
        // also come back from the database, not from a browser that might be
        // remembering them.
        const receipt = persisted?.privateState?.lastQuestReward;
        // JSONB does not preserve property order, so compare the receipt's
        // values, not its byte layout.
        const sameReceipt =
          receipt?.questId === player.receipt.questId &&
          Number(receipt?.rank) === Number(player.receipt.rank) &&
          Array.isArray(receipt?.rewards) &&
          receipt.rewards.length === player.receipt.rewards.length &&
          receipt.rewards.every((row, index) =>
            row?.resource === player.receipt.rewards[index].resource &&
            Number(row?.amount) === Number(player.receipt.rewards[index].amount));
        if (!sameReceipt) {
          failures.push(`the reward receipt did not survive the restart for ${player.playerId}`);
          console.log(`FAILED (the reward receipt did not survive the restart)`);
        } else {
          console.log(`  ${player.playerId} signed in again with the same reward receipt`);
        }
        const factory = Object.values(persisted?.maps?.[0]?.items ?? {}).find(
          (tuple) => Number(tuple[0]) === 2 && Number(tuple[1]) === 46 && Number(tuple[2]) === 46,
        );
        if (Number(factory?.[6]?.['cp']) !== player.production.cp ||
            Number(factory?.[6]?.['lastAccruedAt']) !== player.production.lastAccruedAt ||
            Number(factory?.[6]?.['collect']) !== player.production.collect) {
          failures.push(`the production cycle did not survive the restart for ${player.playerId}`);
          console.log(`FAILED (the production cycle did not survive the restart)`);
        } else {
          console.log(`  ${player.playerId} signed in again with the same production cycle`);
        }
      }
    }
  } finally {
    client.close();
    for (const handle of serverHandles) handle.child.kill();
    await rm(dataDir, { recursive: true, force: true });
    await rm(clockDir, { recursive: true, force: true });
    clockFile = null;
  }

  console.log('');
  console.log(`  the browsers that ran: ${ran.length ? ran.join(', ') : 'none'}`);
  if (notRun.length) {
    console.log(`  the browsers that were not run: ${notRun.join(', ')}`);
  }
  if (failures.length) {
    console.error('');
    console.error('the end-to-end session failed:');
    for (const failure of failures) console.error(`  ${failure}`);
    process.exit(1);
  }
  if (ran.length === 0) {
    console.error('');
    console.error('no browser was available to play in.');
    process.exit(2);
  }
  console.log('OK: a player registers, signs in, plays, and signs in again after a restart.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
