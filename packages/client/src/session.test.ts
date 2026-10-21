import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  EXPIRY_MARGIN_SECONDS,
  SESSION_KEY,
  authorizationHeader,
  forgetSession,
  fromServerSession,
  isExpired,
  readSession,
  rememberSession,
  signIn,
  type ClientSession,
} from './session.ts';

/** A storage that keeps things in a map. */
function memoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => [...map.keys()][index] ?? null,
    removeItem: (key: string) => {
      map.delete(key);
    },
    setItem: (key: string, value: string) => {
      map.set(key, value);
    },
  } as Storage;
}

const SERVER_SESSION = {
  token: 'abc123',
  playerId: 'p1',
  issuedAt: 1_700_000_000,
  expiresAt: 1_700_000_000 + 60 * 60 * 24 * 30,
};

describe('the client session', () => {
  it('comes from the server answer', () => {
    const session = fromServerSession(SERVER_SESSION);
    assert.equal(session.token, 'abc123');
    assert.equal(session.playerId, 'p1');
    assert.equal(session.expiresAt, SERVER_SESSION.expiresAt);
  });

  it('travels in the authorization header', () => {
    const session = fromServerSession(SERVER_SESSION);
    assert.equal(authorizationHeader(session), 'Bearer abc123');
  });

  it('expires', () => {
    const session = fromServerSession(SERVER_SESSION);
    assert.equal(isExpired(session, SERVER_SESSION.issuedAt), false);
    assert.equal(isExpired(session, SERVER_SESSION.expiresAt), true);
  });

  it('gives up a little before it expires, so a request is not cut off', () => {
    const session = fromServerSession(SERVER_SESSION);
    assert.equal(
      isExpired(session, SERVER_SESSION.expiresAt - EXPIRY_MARGIN_SECONDS - 1),
      false,
    );
    assert.equal(
      isExpired(session, SERVER_SESSION.expiresAt - EXPIRY_MARGIN_SECONDS),
      true,
    );
  });
});

describe('the remembered session', () => {
  it('is kept between visits', () => {
    const storage = memoryStorage();
    const session = fromServerSession(SERVER_SESSION);
    rememberSession(storage, session);
    assert.deepEqual(readSession(storage), session);
  });

  it('is forgotten', () => {
    const storage = memoryStorage();
    rememberSession(storage, fromServerSession(SERVER_SESSION));
    forgetSession(storage);
    assert.equal(readSession(storage), null);
  });

  it('is nothing when the storage holds something odd', () => {
    const storage = memoryStorage();
    storage.setItem(SESSION_KEY, 'not json');
    assert.equal(readSession(storage), null);
    storage.setItem(SESSION_KEY, JSON.stringify({ token: 42 }));
    assert.equal(readSession(storage), null);
    storage.setItem(SESSION_KEY, JSON.stringify({ token: 'a', playerId: 'p' }));
    assert.equal(readSession(storage), null);
  });

  it('is nothing when there is no storage', () => {
    assert.equal(readSession(null), null);
    // And writing to it does not throw.
    rememberSession(null, fromServerSession(SERVER_SESSION));
    forgetSession(null);
  });
});

describe('signing in', () => {
  it('succeeds', async () => {
    const result = await signIn('/api/session', 'p1', 'correct horse', async () =>
      new Response(JSON.stringify(SERVER_SESSION), { status: 200 }),
    );
    assert.equal(result.ok, true);
    assert.ok(result.ok && result.session.token === 'abc123');
  });

  it('tells a wrong password from an unknown player', async () => {
    const wrong = await signIn('/api/session', 'p1', 'wrong', async () =>
      new Response('{}', { status: 401 }),
    );
    assert.equal(wrong.ok, false);
    assert.equal(!wrong.ok && wrong.reason, 'invalid-credentials');

    const unknown = await signIn('/api/session', 'nobody', 'x', async () =>
      new Response('{}', { status: 404 }),
    );
    assert.equal(!unknown.ok && unknown.reason, 'unknown-player');
  });

  it('reports a network failure', async () => {
    const result = await signIn('/api/session', 'p1', 'x', async () => {
      throw new Error('offline');
    });
    assert.equal(!result.ok && result.reason, 'network');
  });

  it('reports an answer it cannot read', async () => {
    const result = await signIn('/api/session', 'p1', 'x', async () =>
      new Response('not json', { status: 200 }),
    );
    assert.equal(!result.ok && result.reason, 'network');
  });
});
