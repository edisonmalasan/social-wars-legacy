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
import process from 'node:process';

import { LegacyIdentityBridge, SessionStore } from '@swl/server';
import type { CostContent } from '@swl/rules';

import { createApp, type AppRequest } from './app.ts';
import { DEFAULT_LIMITS } from './limits.ts';
import { MemoryPlayerStore } from './store.ts';
import { createApplier } from '@swl/server';

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

async function main(): Promise<void> {
  const bundle = JSON.parse(await readFile(CONTENT_PATH, 'utf8')) as Record<string, unknown>;
  const items = new Map(
    (bundle['items'] as { id: number; name: string; costs: Record<string, number>; cost_unit_cash: number }[]).map(
      (item) => [
        item.id,
        { id: item.id, name: item.name, costs: item.costs, costUnitCash: item.cost_unit_cash },
      ],
    ),
  );
  const content: CostContent = {
    items,
    offerPacks: new Map(
      (bundle['offerPacks'] as { id: number; name: string; cost_cash: number; gold: number; wood: number; oil: number; steel: number; mana: number; xp: number; items: number[] }[]).map(
        (pack) => [pack.id, pack],
      ),
    ),
    globals: bundle['globals'] as Record<string, unknown>,
    expansionPrices: bundle['expansionPrices'] as { coins: number; cash: number }[],
    marketSellPercentage: (bundle['globals'] as Record<string, unknown>)['MARKET_SELL_PERCENTAGE'] as number,
    marketMaxTrades: (bundle['globals'] as Record<string, unknown>)['MARKET_MAX_NUM_TRADES'] as number,
    marketIncrement: (bundle['globals'] as Record<string, unknown>)['MARKET_INCREMENT'] as number,
    marketBaseCosts: (bundle['globals'] as Record<string, unknown>)['MARKET_BASE_COSTS'] as Record<string, number>,
  };

  const sessions = new SessionStore();
  const identity = new LegacyIdentityBridge();
  const store = new MemoryPlayerStore();

  // A development player. The real server creates players through the
  // account flow; this is the local-play convenience, and it is enabled
  // only when a password is supplied.
  const devPassword = process.env['SWL_DEV_PASSWORD'];
  if (devPassword) {
    sessions.addPlayer('dev', devPassword);
    identity.allowLegacyIdentity();
    identity.bind('dev', 'dev');
    store.add('dev', {
      save: { playerInfo: { pid: 'dev', name: 'Developer' }, maps: [{ id: 0, items: {} }], privateState: {} },
      resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
      nextCommandNumber: 1,
    });
    console.log('[server] development player "dev" is ready.');
  }

  const handle = createApp({
    store,
    sessions,
    identity,
    content,
    contentBundle: bundle,
    now: () => Math.floor(Date.now() / 1000),
    nowMs: () => Date.now(),
    applyCommand: createApplier({
      now: () => Math.floor(Date.now() / 1000),
      tzOffsetHours: 0,
      collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
      dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
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
      const result = handle(appRequest);
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
