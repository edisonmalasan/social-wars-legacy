#!/usr/bin/env node
/**
 * The server's entry point.
 *
 * The application itself (`app.ts`) is a pure function from a request to a
 * response. This file is the thin socket around it: it reads the body with
 * a size cap, sets the socket timeouts, and hands the request over.
 *
 * The body size is capped **twice** — once here, while reading, and once in
 * the application, before anything is parsed. The first stops a huge body
 * being read at all; the second stops it being processed.
 */
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { costContentFrom } from '@swl/rules';
import process from 'node:process';

import {
  ChangeOnlyAlertSender,
  JsonLogger,
  LegacyIdentityBridge,
  MemoryCredentialStore,
  Metrics,
  PostgresCredentialStore,
  PostgresPlayerStore,
  SCHEMA_MIGRATIONS,
  SessionStore,
  WebhookAlertSender,
  runMigrations,
  type CredentialStore,
  type PlayerStore,
} from '@swl/server';
import { PGlite } from '@electric-sql/pglite';
import type { CostContent } from '@swl/rules';

import { createApp, type AppRequest } from './app.ts';
import { DEFAULT_LIMITS } from './limits.ts';
import { MemoryPlayerStore } from '@swl/server';
import { contentItems, populationRules } from '@swl/server';
import { createApplier, initialWorld, tracedDatabase } from '@swl/server';

/** The port to listen on. */
const PORT = Number(process.env['PORT'] ?? 8080);
/** The host to bind. */
const HOST = process.env['HOST'] ?? '127.0.0.1';
/** The content bundle, built by `pnpm build:content`. */
const CONTENT_PATH = path.join(process.cwd(), 'packages/content/dist/content-bundle.json');

/** Read the body, refusing anything over the limit. */
async function readBody(request: IncomingMessage, limit: number): Promise<string | null> {
  const declared = Number(request.headers['content-length'] ?? 0);
  if (declared > limit) return null;

  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = chunk as Buffer;
    size += buffer.length;
    if (size > limit) return null;
    chunks.push(buffer);
  }
  return Buffer.concat(chunks).toString('utf8');
}

/**
 * The content's globals.
 *
 * They are the game's own configuration, and the rules read them.
 */
function globalsOf(bundle: { globals?: unknown }): Record<string, unknown> {
  const globals = bundle.globals;
  return typeof globals === 'object' && globals !== null
    ? (globals as Record<string, unknown>)
    : {};
}

/**
 * The content items the save migration needs.
 *
 * The migration gives a building its production state, and it needs the
 * content to know what that state is: the base amount, the resource and
 * the capacity.
 */
function migrationItems(bundle: {
  items?: unknown[];
}): Map<number, { id: number; collect: number; collect_type: string; unit_capacity: number }> {
  const items = new Map<
    number,
    { id: number; collect: number; collect_type: string; unit_capacity: number }
  >();
  for (const raw of bundle.items ?? []) {
    const item = raw as {
      id: number;
      collect?: number;
      collect_type?: string;
      unit_capacity?: number;
    };
    items.set(item.id, {
      id: item.id,
      collect: item.collect ?? 0,
      collect_type: item.collect_type ?? 'w',
      unit_capacity: item.unit_capacity ?? 0,
    });
  }
  return items;
}

async function main(): Promise<void> {
  const bundle = JSON.parse(await readFile(CONTENT_PATH, 'utf8')) as Parameters<
    typeof costContentFrom
  >[0];
  const content = costContentFrom(bundle);

  const sessions = new SessionStore();
  const identity = new LegacyIdentityBridge();

  // The store. Without SWL_DATA_DIR the server keeps its saves in memory,
  // which is the local-play convenience. With it, the saves live in a
  // PostgreSQL database - a PGlite one, which is a directory - and the
  // **schema is brought forward before anything is served**, so a deploy
  // cannot start a server against a schema it does not understand.
  let store: PlayerStore = new MemoryPlayerStore();
  let credentials: CredentialStore = new MemoryCredentialStore();
  const dataDir = process.env['SWL_DATA_DIR'];
  if (dataDir) {
    const db = await PGlite.create({ dataDir: path.resolve(dataDir) });
    const report = await runMigrations(db, SCHEMA_MIGRATIONS);
    console.log(
      `[server] the schema is at version ${report.to} ` +
        `(${report.applied.length} migration(s) applied)`,
    );
    // The database is **traced**, so every statement becomes a span
    // under the request that made it. A slow request can then be
    // attributed - to the database or to the rules engine - rather than
    // merely observed.
    const traced = tracedDatabase(db);
    store = new PostgresPlayerStore({ db: traced, items: migrationItems(bundle) });
    credentials = new PostgresCredentialStore({ db: traced });

    // The credentials are **loaded** at boot, so a player who registered
    // before the restart can log in after it.
    for (const credential of await credentials.all()) {
      sessions.load(credential);
    }
    console.log(
      `[server] ${sessions.allCredentials().length} player(s) can sign in.`,
    );
  }

  // A development player. The real server creates players through the
  // account flow; this is the local-play convenience, and it is enabled
  // only when a password is supplied.
  const devPassword = process.env['SWL_DEV_PASSWORD'];
  if (devPassword) {
    const credential = sessions.addPlayer('dev', devPassword);
    // The development player is persisted like any other, so it survives
    // a restart too.
    await credentials.put(credential);
    identity.allowLegacyIdentity();
    identity.bind('dev', 'dev');
    if (store instanceof MemoryPlayerStore) {
      // The development player gets the **same** town a new player gets,
      // so the local game is the real game.
      const world = initialWorld('dev');
      world.save.playerInfo['name'] = 'Developer';
      store.add('dev', world);
      console.log('[server] development player "dev" is ready.');
    } else {
      // The database creates its players through the account flow, so the
      // development player is not created behind its back.
      console.log(
        '[server] a development password is set, but the database mode creates ' +
          'its players through the account flow.',
      );
    }
  }

  // The structured log: one JSON line per request, on stdout. The sink
  // is injected, so a deployment can send it somewhere else without
  // touching the application.
  const logger = new JsonLogger({
    sink: (record) => {
      process.stdout.write(`${JSON.stringify(record)}\n`);
    },
  });
  const metrics = new Metrics();

  // Where the alerts go, when there is somewhere to send them.
  const webhookUrl = process.env['SWL_ALERT_WEBHOOK'];

  const handle = createApp({
    store,
    sessions,
    identity,
    content,
    contentBundle: bundle,
    // The versions in use, for the health report and the crash reports.
    version: '0.1.0',
    assetBuildId: process.env['SWL_ASSET_BUILD_ID'] ?? null,
    // Where the alerts go. Without a webhook the alerts are still in the
    // report and on the dashboard, but nobody is **told** - and an alert
    // that nobody is told about is not an alert.
    alertSender: webhookUrl
      ? new ChangeOnlyAlertSender(
          new WebhookAlertSender({ target: { url: webhookUrl } }),
        )
      : undefined,
    logger,
    metrics,
    now: () => Math.floor(Date.now() / 1000),
    nowMs: () => Date.now(),
    credentials,
    applyCommand: createApplier({
      now: () => Math.floor(Date.now() / 1000),
      tzOffsetHours: 0,
      collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
      dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
      // The content, so the applier can check the **rules**: the level,
      // the population and the limits are all the game's own.
      items: contentItems(bundle),
      populationRules: populationRules(globalsOf(bundle)),
    }),
  });

  const server = createServer((request: IncomingMessage, response: ServerResponse) => {
    void (async () => {
      const body = await readBody(request, DEFAULT_LIMITS.maxBodyBytes);
      const appRequest: AppRequest = {
        method: request.method ?? 'GET',
        path: request.url ?? '/',
        headers: request.headers as Record<string, string | undefined>,
        body: body ?? '',
      };
      const result = await handle(appRequest);
      response.writeHead(result.status, result.headers);
      response.end(result.body);
    })().catch((error) => {
      console.error('[server] failed to handle a request:', error);
      response.writeHead(500, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ result: 'error', error: 'internal-error' }));
    });
  });

  // A socket that never answers must not hold a slot for ever.
  server.requestTimeout = 30_000;
  server.headersTimeout = 35_000;
  server.keepAliveTimeout = 10_000;

  server.listen(PORT, HOST, () => {
    console.log(`[server] listening on http://${HOST}:${PORT}`);
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
