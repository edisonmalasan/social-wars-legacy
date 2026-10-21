#!/usr/bin/env node
/**
 * The client's smoke test.
 *
 * The client has to **run**, not merely build. A build that compiles and
 * a page that starts are two different things, and only the second one
 * matters to a player.
 *
 * So the built client is served and loaded in a **real browser**, and the
 * page's own status is read back over the **DevTools protocol**. The
 * status is written by the client itself, so the check is not "did the
 * browser not crash" but "did the client start".
 *
 * The browsers are found on the machine rather than assumed, and a
 * browser that is **not** there is reported as *not run* rather than as a
 * failure: a machine without Firefox has not failed anything.
 *
 * Usage:
 *   node scripts/smoke-test-client.mjs
 *   node scripts/smoke-test-client.mjs --browser chrome
 */
import { spawn } from 'node:child_process';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { mkdtemp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

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
  {
    name: 'firefox',
    paths: ['C:\\Program Files\\Mozilla Firefox\\firefox.exe', '/usr/bin/firefox'],
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
  '.svg': 'image/svg+xml',
};

/** Find a browser on this machine. */
function findBrowser(name) {
  const entry = BROWSERS.find((browser) => browser.name === name);
  if (!entry) return null;
  for (const candidate of entry.paths) {
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/** The files the client is served from: the build and the generated ones. */
const ROOTS = [
  path.join(ROOT, 'apps/client/dist'),
  path.join(ROOT, 'apps/client/public'),
  // The atlas pages. The client asks for them under `/atlases/`, and they
  // live in `.work/frames/atlases/`, so the root is `.work/frames`.
  path.join(ROOT, '.work/frames'),
];

/**
 * A small world for the client to draw.
 *
 * The smoke test is about the **client**, and the server is tested
 * elsewhere; so the world is a stub, and it holds a few real items so
 * that the scene is not empty.
 */
const STUB_WORLD = {
  maps: [
    {
      id: 0,
      items: {
        '1': [1, 10, 20, 0, 0, [], {}, 1],
        '2': [2, 11, 20, 0, 0, [], {}, 1],
        '3': [4, 12, 21, 0, 0, [], {}, 1],
      },
    },
  ],
  privateState: {},
  resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
};

/** The session the smoke test signs in with. */
const STUB_SESSION = {
  token: 'smoke-test-token',
  playerId: 'smoke',
  issuedAt: Math.floor(Date.now() / 1000),
  // An hour ahead, so the client does not decide it has expired.
  expiresAt: Math.floor(Date.now() / 1000) + 60 * 60,
};

/** A static server for the client's files. */
async function serve(port) {
  const { createServer } = await import('node:http');
  const server = createServer((request, response) => {
    const url = (request.url ?? '/').split('?')[0];
    // The path is **relative**: on Windows a leading slash is
    // root-relative, so `path.resolve` would look in `C:\`.
    const relative = url.replace(/^\/+/, '') || 'index.html';

    if (relative === 'api/world') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify(STUB_WORLD));
      return;
    }

    if (relative === 'api/session') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify(STUB_SESSION));
      return;
    }

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
async function waitForDevTools(port, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return await response.json();
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error('the browser did not open its debugging port');
}

/**
 * Ask a page for the client's status, over the DevTools protocol.
 *
 * The page is opened in a tab, the expression is evaluated in it, and the
 * answer is read back.
 */
async function readStatus(port, url, timeoutMs = 60_000) {
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

  const send = (method, params) =>
    new Promise((resolve) => {
      const id = nextId++;
      pending.set(id, resolve);
      socket.send(JSON.stringify({ id, method, params }));
    });

  await send('Runtime.enable', {});
  await send('Page.enable', {});

  // The client signs in, and it keeps the session between visits, so the
  // session is put in the browser's storage and the page is reloaded.
  // The client then starts without anybody typing anything.
  await send('Runtime.evaluate', {
    expression: `window.localStorage.setItem('swl.session', ${JSON.stringify(
      JSON.stringify({
        token: STUB_SESSION.token,
        playerId: STUB_SESSION.playerId,
        expiresAt: STUB_SESSION.expiresAt,
      }),
    )})`,
    returnByValue: true,
  });
  await send('Page.reload', {});

  // The client is asynchronous: it fetches the content, starts the
  // renderer and asks the server for the world. The atlas pages are
  // fetched **after** that, on demand, so the wait is until the status
  // says what happened to them.
  const deadline = Date.now() + timeoutMs;
  let last = '';
  while (Date.now() < deadline) {
    const answer = await send('Runtime.evaluate', {
      expression:
        "(() => { const e = document.getElementById('status');" +
        " return e ? e.getAttribute('data-state') + '|' + e.textContent : 'missing'; })()",
      returnByValue: true,
    });
    const value = String(answer.result?.result?.value ?? 'missing');
    last = value;
    const [state, detail = ''] = value.split('|');
    if (state === 'failed' || state === 'missing') break;
    // The client has started when the state says so. The atlas pages are
    // fetched after that, and they are a build artefact, so their absence
    // is reported rather than failed on.
    if (state === 'started') {
      if (/atlas/.test(detail)) break;
      // Give the pages a moment, and then take what there is.
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const after = await send('Runtime.evaluate', {
        expression:
          "(() => { const e = document.getElementById('status');" +
          " return e ? e.getAttribute('data-state') + '|' + e.textContent : 'missing'; })()",
        returnByValue: true,
      });
      last = String(after.result?.result?.value ?? value);
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  socket.close();
  await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`).catch(() => {});
  return last;
}

async function main() {
  const only = process.argv.includes('--browser')
    ? process.argv[process.argv.indexOf('--browser') + 1]
    : null;

  const dist = path.join(ROOT, 'apps/client/dist/index.html');
  if (!existsSync(dist)) {
    console.error('the client has not been built. Run:');
    console.error('  pnpm --filter @swl/app-client build');
    process.exit(2);
  }

  const port = 5199;
  const server = await serve(port);
  const url = `http://127.0.0.1:${port}/`;

  const ran = [];
  const notRun = [];
  const failed = [];
  let devToolsPort = 9333;

  try {
    for (const entry of BROWSERS) {
      if (only && entry.name !== only) continue;
      const browser = findBrowser(entry.name);
      if (!browser) {
        notRun.push(entry.name);
        continue;
      }

      const profile = await mkdtemp(path.join(os.tmpdir(), 'swl-smoke-'));
      process.stdout.write(`  ${entry.name}: `);

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

      try {
        await waitForDevTools(devToolsPort);
        const status = await readStatus(devToolsPort, url);
        const [state, detail] = String(status).split('|');
        if (state !== 'started') {
          failed.push(`${entry.name}: the client said "${state}" (${detail ?? ''})`);
          console.log(`FAILED (${state}: ${detail ?? ''})`);
          continue;
        }
        ran.push(entry.name);
        console.log(`started (${detail})`);
      } catch (error) {
        failed.push(`${entry.name}: ${String(error)}`);
        console.log(`FAILED (${String(error)})`);
      } finally {
        child.kill();
        devToolsPort += 1;
      }
    }
  } finally {
    server.close();
  }

  console.log('');
  console.log(`  the browsers that ran: ${ran.length ? ran.join(', ') : 'none'}`);
  if (notRun.length) {
    console.log(`  the browsers that are not on this machine: ${notRun.join(', ')}`);
  }
  if (failed.length) {
    console.error('');
    console.error('the client did not start:');
    for (const failure of failed) console.error(`  ${failure}`);
    process.exit(1);
  }
  if (ran.length === 0) {
    console.error('');
    console.error('no browser was available to run the client in.');
    process.exit(2);
  }
  console.log('OK: the client starts.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
