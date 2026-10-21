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
import { createReadStream, existsSync, mkdtempSync, statSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

import { brokenBudgets } from '../packages/server/src/budgets.ts';

const ROOT = process.cwd();

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
  const child = spawn(
    process.execPath,
    ['apps/server/src/main.ts'],
    {
      cwd: ROOT,
      env: { ...process.env, SWL_DATA_DIR: dataDir, PORT: String(port) },
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

async function main() {
  const only = process.argv.includes('--browser')
    ? process.argv[process.argv.indexOf('--browser') + 1]
    : null;

  if (!existsSync(path.join(ROOT, 'apps/client/dist/index.html'))) {
    console.error('the client has not been built. Run:');
    console.error('  pnpm --filter @swl/app-client build');
    process.exit(2);
  }

  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'swl-e2e-'));
  // **Free** ports: a stray server from an earlier run must not be able
  // to answer this one's requests, or hold the port.
  const base = 8100 + Math.floor(Math.random() * 200);
  const serverPort = base;
  const clientPort = base + 200;
  let devToolsPort = 9332;

  const server = await startServer(dataDir, serverPort);
  const client = await serve(clientPort, serverPort);

  const failures = [];
  const ran = [];
  const notRun = [];

  try {
    // --- 1. The player registers, through the real server ----------------
    const session = await register(serverPort, 'e2e-player', 'correct horse');
    console.log(`  registered "e2e-player"`);

    // The credential is persisted: a fresh server over the same database
    // can sign the player in.
    const second = await startServer(dataDir, serverPort + 1);
    try {
      const response = await fetch(`http://127.0.0.1:${serverPort + 1}/api/session`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ playerId: 'e2e-player', password: 'correct horse' }),
      });
      if (response.status !== 200) {
        failures.push(`the player could not sign in after a restart: ${response.status}`);
      } else {
        console.log('  the player signed in again after a restart');
      }
    } finally {
      second.child.kill();
    }

    for (const entry of BROWSERS) {
      if (only && entry.name !== only) continue;
      const browser = findBrowser(entry.name);
      if (!browser) {
        notRun.push(entry.name);
        continue;
      }
      console.log(`  ${entry.name}: `);

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
              token: session.token,
              playerId: session.playerId,
              expiresAt: session.expiresAt,
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

        ran.push(entry.name);
      } catch (error) {
        failures.push(`${entry.name}: ${String(error)}`);
        console.log(`FAILED (${String(error)})`);
      } finally {
        if (page) await page.close(devToolsPort);
        child.kill();
        devToolsPort += 1;
      }
    }
  } finally {
    client.close();
    server.child.kill();
    await rm(dataDir, { recursive: true, force: true });
  }

  console.log('');
  console.log(`  the browsers that ran: ${ran.length ? ran.join(', ') : 'none'}`);
  if (notRun.length) {
    console.log(`  the browsers that are not on this machine: ${notRun.join(', ')}`);
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
