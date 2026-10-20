import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import {
  JsonLogger,
  Metrics,
  REQUEST_ID_HEADER,
  SILENT_LOGGER,
  newRequestId,
  seriesKey,
  snapshot,
  type LogRecord,
} from '@swl/server';

import { createApp, type AppOptions, type AppRequest } from './app.ts';
import { MemoryPlayerStore } from '@swl/server';
import { LegacyIdentityBridge, SessionStore } from '@swl/server';
import { costContentFrom } from '@swl/rules';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

describe('the structured log', () => {
  it('writes one JSON line per record', () => {
    const lines: LogRecord[] = [];
    const logger = new JsonLogger({
      sink: (record) => lines.push(record),
      clock: () => 1_700_000_000_000,
    });
    logger.info('request', { requestId: 'abc', status: 200 });
    assert.equal(lines.length, 1);
    assert.equal(lines[0]!.level, 'info');
    assert.equal(lines[0]!.message, 'request');
    assert.equal(lines[0]!.requestId, 'abc');
    assert.equal(lines[0]!.time, '2023-11-14T22:13:20.000Z');
  });

  it('carries the level', () => {
    const lines: LogRecord[] = [];
    const logger = new JsonLogger({ sink: (record) => lines.push(record) });
    logger.warn('a warning');
    logger.error('an error');
    assert.equal(lines[0]!.level, 'warn');
    assert.equal(lines[1]!.level, 'error');
  });

  it('has a logger that writes nothing', () => {
    assert.doesNotThrow(() => SILENT_LOGGER.info('nothing'));
  });
});

describe('the metrics', () => {
  it('count', () => {
    const metrics = new Metrics();
    metrics.increment('commands_total', { name: 'buy' });
    metrics.increment('commands_total', { name: 'buy' });
    metrics.increment('commands_total', { name: 'sell' });
    assert.equal(metrics.counters['commands_total{name=buy}'], 2);
    assert.equal(metrics.counters['commands_total{name=sell}'], 1);
  });

  it('gauge', () => {
    const metrics = new Metrics();
    metrics.gauge('active_sessions', 7);
    assert.equal(metrics.gauges['active_sessions'], 7);
  });

  it('observe, with buckets', () => {
    const metrics = new Metrics({ buckets: [10, 100, 1000] });
    metrics.observe('latency', 5);
    metrics.observe('latency', 50);
    metrics.observe('latency', 500);
    const histogram = metrics.histograms['latency']!;
    assert.equal(histogram.count, 3);
    assert.equal(histogram.sum, 555);
    assert.equal(histogram.min, 5);
    assert.equal(histogram.max, 500);
    // The cumulative counts: five is in every bucket, fifty is in two, and
    // five hundred is in one.
    assert.equal(histogram.buckets['10'], 1);
    assert.equal(histogram.buckets['100'], 2);
    assert.equal(histogram.buckets['1000'], 3);
  });

  it('label a series by its labels, in a stable order', () => {
    assert.equal(seriesKey('a', { x: '1', y: '2' }), 'a{x=1,y=2}');
    assert.equal(seriesKey('a', { y: '2', x: '1' }), 'a{x=1,y=2}');
    assert.equal(seriesKey('a'), 'a');
    assert.equal(seriesKey('a', { x: '' }), 'a');
  });

  it('snapshot', () => {
    const metrics = new Metrics();
    metrics.increment('a');
    metrics.gauge('b', 1);
    metrics.observe('c', 2);
    const taken = snapshot(metrics);
    assert.deepEqual(taken.counters, { a: 1 });
    assert.deepEqual(taken.gauges, { b: 1 });
    assert.equal(taken.histograms['c']!.count, 1);
  });
});

describe('the request id', () => {
  it('is made when there is none', () => {
    const id = newRequestId(() => 'abcdef0123456789');
    assert.equal(id, 'abcdef0123456789');
  });

  it('is different each time', () => {
    assert.notEqual(newRequestId(), newRequestId());
  });
});

describe('the application', () => {
  /** The lines the application wrote. */
  function logger(): { sink: (record: LogRecord) => void; lines: LogRecord[] } {
    const lines: LogRecord[] = [];
    return { sink: (record) => lines.push(record), lines };
  }

  async function app(
    over: Partial<AppOptions> = {},
  ): Promise<{
    handle: (request: AppRequest) => Promise<{ status: number; headers: Record<string, string>; body: string }>;
    lines: LogRecord[];
    metrics: Metrics;
  }> {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    const identity = new LegacyIdentityBridge();
    identity.allowLegacyIdentity();
    identity.bind('legacy-player-1', 'p1');
    const store = new MemoryPlayerStore([
      {
        playerId: 'p1',
        world: {
          save: { playerInfo: { pid: 'p1', name: 'Player' }, maps: [{ id: 0, items: {} }], privateState: {} },
          resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
          nextCommandNumber: 1,
        },
      },
    ]);
    const bundle = JSON.parse(
      await readFile(
        path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
        'utf8',
      ),
    ) as Parameters<typeof costContentFrom>[0];
    const content = costContentFrom(bundle);
    const metrics = new Metrics();
    const log = logger();

    const handle = createApp({
      store,
      sessions,
      identity,
      content,
      contentBundle: bundle,
      now: () => 1_700_000_000,
      nowMs: () => 1_700_000_000_000,
      applyCommand: (world, command) => ({ applied: true, world }),
      metrics,
      logger: new JsonLogger({ sink: log.sink, clock: () => 1_700_000_000_000 }),
      requestId: () => 'the-request-id',
      ...over,
    });

    return { handle, lines: log.lines, metrics };
  }

  it('returns the request id in the response', async () => {
    const { handle } = await app();
    const response = await handle({
      method: 'GET',
      path: '/health',
      headers: {},
      body: '',
    });
    assert.equal(response.headers[REQUEST_ID_HEADER], 'the-request-id');
  });

  it('reuses the client own request id', async () => {
    const { handle } = await app();
    const response = await handle({
      method: 'GET',
      path: '/health',
      headers: { [REQUEST_ID_HEADER]: 'from-the-client' },
      body: '',
    });
    assert.equal(response.headers[REQUEST_ID_HEADER], 'from-the-client');
  });

  it('logs one line per request', async () => {
    const { handle, lines } = await app();
    await handle({ method: 'GET', path: '/health', headers: {}, body: '' });
    assert.equal(lines.length, 1);
    assert.equal(lines[0]!.requestId, 'the-request-id');
    assert.equal(lines[0]!.path, '/health');
    assert.equal(lines[0]!.status, 200);
  });

  it('logs the command the request applied', async () => {
    const { handle, lines } = await app();
    await handle({
      method: 'POST',
      path: '/api/command',
      headers: {},
      body: JSON.stringify({
        v: 1,
        id: 'req-1',
        token: 'not-a-token',
        commands: [{ name: 'buy', args: [1, 1] }],
      }),
    });
    // The request was refused for the token, but the line is still there
    // and it still carries the request id.
    assert.equal(lines.length, 1);
    assert.equal(lines[0]!.requestId, 'the-request-id');
    assert.equal(lines[0]!.path, '/api/command');
  });

  it('records the latency and the request count', async () => {
    const { handle, metrics } = await app();
    await handle({ method: 'GET', path: '/health', headers: {}, body: '' });
    assert.equal(metrics.counters['http_requests_total{method=GET,path=/health,status=200}'], 1);
    assert.equal(metrics.histograms['http_request_duration_ms{method=GET,path=/health}']!.count, 1);
  });

  it('records an error', async () => {
    const { handle, metrics } = await app();
    await handle({ method: 'GET', path: '/nothing-here', headers: {}, body: '' });
    assert.equal(metrics.counters['http_errors_total{path=/nothing-here,status=404}'], 1);
  });

  it('serves the metrics', async () => {
    const { handle } = await app();
    await handle({ method: 'GET', path: '/health', headers: {}, body: '' });
    const response = await handle({
      method: 'GET',
      path: '/api/metrics',
      headers: {},
      body: '',
    });
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body) as {
      counters: Record<string, number>;
      gauges: Record<string, number>;
    };
    assert.ok(body.counters['http_requests_total{method=GET,path=/health,status=200}']);
    // The active sessions are a gauge.
    assert.equal(typeof body.gauges['active_sessions'], 'number');
  });

  it('refuses a metrics request that is not a GET', async () => {
    const { handle } = await app();
    const response = await handle({
      method: 'POST',
      path: '/api/metrics',
      headers: {},
      body: '',
    });
    assert.equal(response.status, 405);
  });
});
