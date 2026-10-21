import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import { MemoryCredentialStore, PostgresCredentialStore } from '@swl/server';
import { runMigrations } from '@swl/server';
import { SCHEMA_MIGRATIONS } from '@swl/server';
import { costContentFrom } from '@swl/rules';
import { LegacyIdentityBridge, SessionStore } from '@swl/server';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

import { createApp, type AppOptions, type AppRequest } from './app.ts';
import { DEFAULT_LIMITS } from './limits.ts';

function repoRoot(): string {
  let dir = process.cwd();
  for (let i = 0; i < 8; i++) {
    if (existsSync(path.join(dir, 'pnpm-workspace.yaml'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

async function content() {
  const bundle = JSON.parse(
    await readFile(
      path.join(repoRoot(), 'packages/content/dist/content-bundle.json'),
      'utf8',
    ),
  ) as Parameters<typeof costContentFrom>[0];
  return { bundle, content: costContentFrom(bundle) };
}

/** An application with a credential store. */
async function app(
  credentials: MemoryCredentialStore | PostgresCredentialStore,
  options: Partial<AppOptions> = {},
) {
  const sessions = new SessionStore();
  const identity = new LegacyIdentityBridge();
  const { bundle, content: cost } = await content();

  const handle = createApp({
    store: {
      get: async () => null,
      has: async () => false,
      list: async () => [],
      add: async () => {},
      transact: async () => null,
      size: 0,
    },
    sessions,
    identity,
    content: cost,
    contentBundle: bundle,
    now: () => 1_700_000_000,
    nowMs: () => 1_700_000_000_000,
    applyCommand: (world, command) => ({ applied: true, world }),
    credentials,
    limits: { ...DEFAULT_LIMITS, requestsPerWindow: 1000 },
    ...options,
  });

  return { handle, sessions };
}

describe('the account endpoint', () => {
  it('creates a player and signs them in', async () => {
    const credentials = new MemoryCredentialStore();
    const { handle } = await app(credentials);

    const response = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });

    assert.equal(response.status, 201);
    const body = JSON.parse(response.body) as { token: string; playerId: string };
    assert.equal(body.playerId, 'p1');
    assert.ok(body.token.length > 0);
  });

  it('keeps the credential, and never the password', async () => {
    const credentials = new MemoryCredentialStore();
    const { handle } = await app(credentials);

    await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });

    const stored = await credentials.get('p1');
    assert.ok(stored, 'the credential was not kept');
    assert.ok(!JSON.stringify(stored).includes('correct horse'));
  });

  it('refuses a name that is taken', async () => {
    const credentials = new MemoryCredentialStore();
    const { handle } = await app(credentials);

    const first = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    assert.equal(first.status, 201);

    const second = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'another' }),
    });
    assert.equal(second.status, 409);
    assert.equal(JSON.parse(second.body).error, 'player-exists');
  });

  it('refuses a body that is not a credential', async () => {
    const { handle } = await app(new MemoryCredentialStore());
    const response = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1' }),
    });
    assert.equal(response.status, 400);
  });

  it('refuses a body it cannot read', async () => {
    const { handle } = await app(new MemoryCredentialStore());
    const response = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: 'not json',
    });
    assert.equal(response.status, 400);
  });

  it('refuses a method that is not a POST', async () => {
    const { handle } = await app(new MemoryCredentialStore());
    const response = await handle({
      method: 'GET',
      path: '/api/account',
      headers: {},
      body: '',
    });
    assert.equal(response.status, 405);
  });

  it('refuses to create a player when there is nowhere to keep the credential', async () => {
    const { handle } = await app(new MemoryCredentialStore(), {
      credentials: undefined,
    });
    const response = await handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    assert.equal(response.status, 503);
  });
});

describe('a player, over a real database', () => {
  it('registers, signs in, and signs in again after a restart', async () => {
    const db = await PGlite.create();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const credentials = new PostgresCredentialStore({ db });

    // The first run: the player registers.
    const first = await app(credentials);
    const created = await first.handle({
      method: 'POST',
      path: '/api/account',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    assert.equal(created.status, 201);

    // The second run: the server restarts, loads the credentials, and the
    // player signs in.
    const sessions = new SessionStore();
    for (const credential of await credentials.all()) {
      sessions.load(credential);
    }
    const second = await app(credentials, { sessions });
    const signedIn = await second.handle({
      method: 'POST',
      path: '/api/session',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'correct horse' }),
    });
    assert.equal(signedIn.status, 200);
    assert.ok((JSON.parse(signedIn.body) as { token: string }).token.length > 0);

    // And a wrong password is still refused.
    const wrong = await second.handle({
      method: 'POST',
      path: '/api/session',
      headers: {},
      body: JSON.stringify({ playerId: 'p1', password: 'wrong' }),
    });
    assert.equal(wrong.status, 401);

    await db.close();
  });
});
