import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { costContentFrom } from '@swl/rules';

import { LegacyIdentityBridge, SessionStore } from '@swl/server';
import { framePayload, SERVER_KEYS } from '@swl/protocol';

import { createApp, ERROR_CODES, type AppOptions, type AppRequest } from './app.ts';
import { MemoryPlayerStore, cloneWorld } from './store.ts';
import { DEFAULT_LIMITS, RateLimiter, parseForm } from './limits.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function costContent() {
  const bundle = JSON.parse(
    await readFile(path.join(repoRoot(), 'packages/content/dist/content-bundle.json'), 'utf8'),
  ) as Parameters<typeof costContentFrom>[0];
  return costContentFrom(bundle);
}

const LEGACY_USER_ID = 'legacy-player-1';

function world(over: Record<string, unknown> = {}) {
  return {
    save: { playerInfo: { name: 'me' }, maps: [{ id: 1 }], privateState: { energy: 30 } },
    resources: { g: 1000, w: 1000, o: 1000, s: 1000, c: 1000, e: 100, x: 0, m: 0 },
    nextCommandNumber: 1,
    ...over,
  };
}

async function app(over: Partial<AppOptions> = {}) {
  const sessions = new SessionStore();
  sessions.addPlayer('p1', 'correct horse');
  const identity = new LegacyIdentityBridge();
  identity.allowLegacyIdentity();
  identity.bind(LEGACY_USER_ID, 'p1');
  const store = new MemoryPlayerStore([{ playerId: 'p1', world: world() }]);
  const content = await costContent();

  const options: AppOptions = {
    store,
    sessions,
    identity,
    content,
    contentBundle: { items: [], globals: {} },
    now: () => 1_700_000_000,
    nowMs: () => 1_700_000_000_000,
    applyCommand: (w, command) => ({ applied: true, world: w }),
    ...over,
  };
  // A real session, so the token in the request is a real token.
  const issued = sessions.authenticate('p1', 'correct horse', 1_700_000_000);
  if (!issued.ok) throw new Error('the test player could not authenticate');
  return {
    handle: createApp(options),
    options,
    // The store the application actually uses, which a caller may have
    // replaced through `over`.
    store: options.store,
    sessions,
    token: issued.session.token,
  };
}

function request(
  method: string,
  path: string,
  body = '',
  headers: Record<string, string | undefined> = {},
): AppRequest {
  return { method, path, headers, body };
}

const form = (fields: Record<string, string>): Record<string, string> => ({
  'content-type': 'application/x-www-form-urlencoded',
});

/**
 * A legacy request: the body is form-encoded, exactly as the client sends
 * it. The upstream reads `request.values['USERID']`, which merges the form
 * fields and the query string - never the headers.
 */
function legacyRequest(path: string, fields: Record<string, string>): AppRequest {
  const body = Object.entries(fields)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&');
  return { method: 'POST', path, headers: form({}), body };
}

describe('the form parser', () => {
  it('decodes the fields', () => {
    assert.deepEqual(parseForm('a=1&b=two'), { a: '1', b: 'two' });
    assert.deepEqual(parseForm('a=hello%20world'), { a: 'hello world' });
    assert.deepEqual(parseForm('a=1+2'), { a: '1 2' });
  });

  it('keeps a malformed escape rather than throwing', () => {
    assert.deepEqual(parseForm('a=%zz'), { a: '%zz' });
  });
});

describe('the rate limiter', () => {
  it('allows a burst and then refuses', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 3, windowSeconds: 60 });
    assert.equal(limiter.check('a', 0), 0);
    assert.equal(limiter.check('a', 1), 0);
    assert.equal(limiter.check('a', 2), 0);
    assert.ok(limiter.check('a', 3) > 0);
  });

  it('resets when the window rolls over', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 1, windowSeconds: 60 });
    assert.equal(limiter.check('a', 0), 0);
    assert.ok(limiter.check('a', 1) > 0);
    assert.equal(limiter.check('a', 61), 0);
  });

  it('keeps clients apart', () => {
    const limiter = new RateLimiter({ ...DEFAULT_LIMITS, requestsPerWindow: 1 });
    assert.equal(limiter.check('a', 0), 0);
    assert.equal(limiter.check('b', 0), 0);
  });
});

describe('the store', () => {
  it('hands out copies, so a caller cannot mutate the save behind its back', () => {
    const store = new MemoryPlayerStore([{ playerId: 'p1', world: world() }]);
    const first = store.get('p1')!;
    first.world.resources['g'] = 0;
    assert.equal(store.get('p1')!.world.resources['g'], 1000);
  });

  it('commits a transaction', () => {
    const store = new MemoryPlayerStore([{ playerId: 'p1', world: world() }]);
    store.transact('p1', (w) => ({ ...w, resources: { ...w.resources, g: 5 } }));
    assert.equal(store.get('p1')!.world.resources['g'], 5);
  });

  it('leaves the save untouched when a transaction throws', () => {
    const store = new MemoryPlayerStore([{ playerId: 'p1', world: world() }]);
    assert.throws(() =>
      store.transact('p1', (w) => {
        w.resources['g'] = 0;
        throw new Error('boom');
      }),
    );
    assert.equal(store.get('p1')!.world.resources['g'], 1000);
  });

  it('clones a world deeply enough', () => {
    const original = world();
    const copy = cloneWorld(original);
    copy.resources['g'] = 1;
    copy.save.playerInfo['name'] = 'other';
    assert.equal(original.resources['g'], 1000);
    assert.equal(original.save.playerInfo['name'], 'me');
  });
});

describe('the health check', () => {
  it('answers', async () => {
    const { handle } = await app();
    const response = handle(request('GET', '/health'));
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), { status: 'ok', protocol: 1 });
  });

  it('refuses a POST', async () => {
    const { handle } = await app();
    assert.equal(handle(request('POST', '/health')).status, 405);
  });
});

describe('the session endpoints', () => {
  it('issues a token for a correct credential', async () => {
    const { handle } = await app();
    const response = handle(
      request('POST', '/api/session', JSON.stringify({ playerId: 'p1', password: 'correct horse' }), {
        'content-type': 'application/json',
      }),
    );
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body);
    assert.ok(body.token);
    assert.equal(body.playerId, 'p1');
  });

  it('refuses a wrong password with a typed error, never a 500', async () => {
    const { handle } = await app();
    const response = handle(
      request('POST', '/api/session', JSON.stringify({ playerId: 'p1', password: 'wrong' }), {
        'content-type': 'application/json',
      }),
    );
    assert.equal(response.status, 401);
    assert.equal(JSON.parse(response.body).error, 'invalid-credentials');
  });

  it('refuses a malformed body with a typed error', async () => {
    const { handle } = await app();
    const response = handle(request('POST', '/api/session', 'not json', {
      'content-type': 'application/json',
    }));
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.body).error, 'malformed-json');
  });

  it('refuses missing credentials', async () => {
    const { handle } = await app();
    const response = handle(request('POST', '/api/session', '{}', {
      'content-type': 'application/json',
    }));
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.body).error, 'missing-credentials');
  });

  it('revokes a token', async () => {
    const { handle, sessions } = await app();
    const created = handle(
      request('POST', '/api/session', JSON.stringify({ playerId: 'p1', password: 'correct horse' }), {
        'content-type': 'application/json',
      }),
    );
    const token = JSON.parse(created.body).token;
    assert.ok(sessions.resolve(token, 1_700_000_000));
    const deleted = handle(request('DELETE', '/api/session', '', { authorization: `Bearer ${token}` }));
    assert.equal(JSON.parse(deleted.body).revoked, true);
    assert.equal(sessions.resolve(token, 1_700_000_000), null);
  });

  it('every error code has a message', () => {
    for (const [code, message] of Object.entries(ERROR_CODES)) {
      assert.ok(message.length > 0, `${code} has no message`);
    }
  });
});

describe('the legacy command endpoint', () => {
  const payload = (first: number, commands: unknown[]) =>
    JSON.stringify({ first_number: first, commands, tries: 1 });

  it('applies an authenticated batch', async () => {
    const { handle, store } = await app();
    const frame = framePayload(payload(1, []), SERVER_KEYS.current);
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }),
    );
    assert.equal(response.status, 200);
    // The client expects exactly {"result": "success"}, and nothing else.
    assert.deepEqual(JSON.parse(response.body), { result: 'success' });
    assert.equal(store.get('p1')!.world.nextCommandNumber, 1);
  });

  it('refuses an unauthenticated batch with a typed error', async () => {
    const { handle } = await app();
    const frame = framePayload(payload(1, []), SERVER_KEYS.current);
    const response = handle(legacyRequest('/command.php', { data: frame }));
    assert.equal(response.status, 401);
    assert.equal(JSON.parse(response.body).error, 'unknown-player');
  });

  it('refuses a body signed with the wrong key', async () => {
    const { handle } = await app();
    const frame = framePayload(payload(1, []), 'not-a-key');
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }),
    );
    assert.equal(response.status, 403);
  });

  it('refuses a malformed body', async () => {
    const { handle } = await app();
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: 'notframed' }),
    );
    assert.equal(response.status, 400);
  });

  it('computes the cost and ignores the declared delta', async () => {
    const { handle, store } = await app();
    const frame = framePayload(
      payload(1, [[1, 'buy', [1, 1007, 0, 0, 1, 0, 0], [0, 0, 999999, 0, 0, 0, 0, 0]]]),
      SERVER_KEYS.current,
    );
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }),
    );
    assert.equal(response.status, 200);
    // The Soldier costs 30 gold and 60 steel. The client claimed a million.
    assert.equal(store.get('p1')!.world.resources['g'], 1000 - 30);
    assert.equal(store.get('p1')!.world.resources['s'], 1000 - 60);
  });

  it('leaves the save untouched when a command throws', async () => {
    const { handle, store } = await app({
      applyCommand: () => {
        throw new Error('boom');
      },
    });
    const frame = framePayload(
      payload(1, [[1, 'buy', [1, 1007, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]]),
      SERVER_KEYS.current,
    );
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }),
    );
    // The failure is caught at the edge, and the save is unchanged.
    assert.equal(response.status, 500);
    assert.equal(store.get('p1')!.world.resources['g'], 1000);
  });

  it('refuses a body that is too large', async () => {
    const { handle } = await app({ limits: { ...DEFAULT_LIMITS, maxBodyBytes: 10 } });
    const frame = framePayload(payload(1, []), SERVER_KEYS.current);
    const response = handle(
      legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }),
    );
    assert.equal(response.status, 413);
    assert.equal(JSON.parse(response.body).error, 'body-too-large');
  });

  it('rate limits', async () => {
    const { handle } = await app({
      limits: { ...DEFAULT_LIMITS, requestsPerWindow: 2, windowSeconds: 60 },
    });
    const frame = framePayload(payload(1, []), SERVER_KEYS.current);
    const send = () =>
      handle(legacyRequest('/command.php', { USERID: LEGACY_USER_ID, data: frame }));
    assert.equal(send().status, 200);
    assert.equal(send().status, 200);
    const limited = send();
    assert.equal(limited.status, 429);
    assert.equal(JSON.parse(limited.body).error, 'rate-limited');
    assert.ok(limited.headers['retry-after']);
  });
});

describe('the native command endpoint', () => {
  const native = (token: string, id: string, commands: unknown[]) => ({
    method: 'POST',
    path: '/api/command',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ v: 1, id, token, commands }),
  });

  it('applies a valid request', async () => {
    const { handle, token } = await app();
    const response = handle(native(token, 'req-1', []));
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body);
    assert.equal(body.v, 1);
    assert.equal(body.id, 'req-1');
    assert.equal(body.ok, true);
    assert.deepEqual(body.outcomes, []);
  });

  it('refuses an unauthenticated request', async () => {
    const { handle } = await app();
    const response = handle({
      method: 'POST',
      path: '/api/command',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ v: 1, id: 'req-1', token: 'good', commands: [] }),
    });
    assert.equal(response.status, 401);
  });

  it('refuses a malformed body with a typed error', async () => {
    const { handle, token } = await app();
    const response = handle({
      method: 'POST',
      path: '/api/command',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
      body: 'not json',
    });
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.body).error, 'malformed-json');
  });

  it('refuses an unsupported protocol version', async () => {
    const { handle, token } = await app();
    const response = handle({
      method: 'POST',
      path: '/api/command',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
      body: JSON.stringify({ v: 99, id: 'req-1', token, commands: [] }),
    });
    assert.equal(response.status, 400);
    const body = JSON.parse(response.body);
    assert.equal(body.ok, false);
    assert.ok(body.errors.length > 0);
    assert.equal(body.errors[0].code, 'unsupported-protocol-version');
  });

  it('refuses a command that is not in the vocabulary', async () => {
    const { handle, token } = await app();
    const response = handle(native(token, 'req-1', [{ map: 0, name: 'not_a_command', args: [] }]));
    assert.equal(response.status, 400);
    const body = JSON.parse(response.body);
    assert.equal(body.errors[0].code, 'unknown-command');
  });

  it('does not apply a retried request twice', async () => {
    let applied = 0;
    const { handle, token } = await app({
      applyCommand: (w) => {
        applied += 1;
        return { applied: true, world: w };
      },
    });
    const first = handle(
      native(token, 'req-1', [{ map: 0, name: 'move', args: [1, 2, 3, 0, 'test'] }]),
    );
    assert.equal(first.status, 200);
    assert.equal(applied, 1);

    // The same request id: the retry of a request that was lost in flight.
    const second = handle(
      native(token, 'req-1', [{ map: 0, name: 'move', args: [1, 2, 3, 0, 'test'] }]),
    );
    assert.equal(second.status, 200);
    assert.equal(applied, 1, 'the retried request was applied again');
    // The answer is the same one.
    assert.deepEqual(JSON.parse(second.body), JSON.parse(first.body));
  });

  it('computes the cost itself', async () => {
    const { handle, store, token } = await app();
    const response = handle(
      native(token, 'req-1', [{ map: 0, name: 'buy', args: [1, 1007, 0, 0, 1, 0, 0, 'u'] }]),
    );
    assert.equal(response.status, 200);
    // The Soldier costs 30 gold and 60 steel, and the native envelope has
    // nowhere to put a client's own figure.
    assert.equal(store.get('p1')!.world.resources['g'], 1000 - 30);
    assert.equal(store.get('p1')!.world.resources['s'], 1000 - 60);
  });

  it('refuses a command the player cannot afford, without touching the rest', async () => {
    const { handle, store, token } = await app({
      store: new MemoryPlayerStore([
        { playerId: 'p1', world: { ...world(), resources: { g: 1, w: 0, o: 0, s: 0, c: 0, e: 100, x: 0, m: 0 } } },
      ]),
    });
    const response = handle(
      native(token, 'req-1', [{ map: 0, name: 'buy', args: [1, 1007, 0, 0, 1, 0, 0, 'u'] }]),
    );
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body);
    assert.equal(body.ok, false);
    assert.equal(body.outcomes[0].error.code, 'insufficient-resources');
    assert.equal(store.get('p1')!.world.resources['g'], 1);
  });
});

describe('the legacy config and player endpoints', () => {
  it('serves the content bundle', async () => {
    const { handle } = await app({ contentBundle: { items: [1, 2, 3], globals: { a: 1 } } });
    const response = handle(request('POST', '/get_game_config.php', ''));
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), { items: [1, 2, 3], globals: { a: 1 } });
  });

  it('serves the player own info', async () => {
    const { handle } = await app();
    const response = handle(
      legacyRequest('/get_player_info.php', { USERID: LEGACY_USER_ID }),
    );
    assert.equal(response.status, 200);
    const body = JSON.parse(response.body);
    assert.equal(body.result, 'ok');
    assert.deepEqual(body.playerInfo, { name: 'me' });
  });

  it('refuses an unauthenticated player info request', async () => {
    const { handle } = await app();
    assert.equal(handle(legacyRequest('/get_player_info.php', {})).status, 401);
  });
});

describe('the router', () => {
  it('answers 404 for an unknown endpoint', async () => {
    const { handle } = await app();
    const response = handle(request('GET', '/nope'));
    assert.equal(response.status, 404);
    assert.equal(JSON.parse(response.body).error, 'not-found');
  });

  it('answers 405 for the wrong method', async () => {
    const { handle } = await app();
    assert.equal(handle(request('GET', '/command.php')).status, 405);
  });
});
