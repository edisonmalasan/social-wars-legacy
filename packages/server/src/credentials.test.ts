import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { PGlite } from '@electric-sql/pglite';

import {
  MemoryCredentialStore,
  PostgresCredentialStore,
  credentialMatches,
  hashPassword,
  makeCredential,
  newSalt,
  safeEqual,
} from './credentials.ts';
import { runMigrations } from './migrations.ts';
import { SCHEMA_MIGRATIONS } from './schema.ts';

describe('a credential', () => {
  it('never holds the password', () => {
    const credential = makeCredential('p1', 'correct horse');
    assert.equal(credential.playerId, 'p1');
    assert.ok(credential.salt.length > 0);
    assert.ok(!credential.passwordHash.includes('correct horse'));
  });

  it('matches its own password', () => {
    const credential = makeCredential('p1', 'correct horse');
    assert.equal(credentialMatches(credential, 'correct horse'), true);
    assert.equal(credentialMatches(credential, 'wrong horse'), false);
  });

  it('is salted, so the same password gives a different hash', () => {
    const first = makeCredential('p1', 'correct horse');
    const second = makeCredential('p1', 'correct horse');
    assert.notEqual(first.salt, second.salt);
    assert.notEqual(first.passwordHash, second.passwordHash);
  });

  it('hashes the same way every time', () => {
    const salt = newSalt();
    assert.equal(hashPassword('x', salt), hashPassword('x', salt));
    assert.notEqual(hashPassword('x', salt), hashPassword('y', salt));
  });

  it('compares in constant time', () => {
    // The point is the *length*, not the content: a comparison that
    // returns early leaks the length.
    assert.equal(safeEqual('abc', 'abc'), true);
    assert.equal(safeEqual('abc', 'abd'), false);
    assert.equal(safeEqual('abc', 'abcd'), false);
    assert.equal(safeEqual('', ''), true);
  });
});

describe('the memory credential store', () => {
  it('keeps, lists and removes', async () => {
    const store = new MemoryCredentialStore();
    const credential = makeCredential('p1', 'one');
    await store.put(credential);

    assert.deepEqual(await store.get('p1'), credential);
    assert.equal((await store.all()).length, 1);
    assert.equal(await store.remove('p1'), true);
    assert.equal(await store.remove('p1'), false);
    assert.equal(await store.get('p1'), null);
  });
});

describe('the Postgres credential store', () => {
  it('keeps, lists and removes', async () => {
    const db = await PGlite.create();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const store = new PostgresCredentialStore({ db });

    const credential = makeCredential('p1', 'correct horse');
    await store.put(credential);

    const loaded = await store.get('p1');
    assert.ok(loaded);
    assert.equal(loaded!.salt, credential.salt);
    assert.equal(loaded!.passwordHash, credential.passwordHash);
    assert.equal((await store.all()).length, 1);

    assert.equal(await store.remove('p1'), true);
    assert.equal(await store.get('p1'), null);

    await db.close();
  });

  it('survives a new store over the same database', async () => {
    // The point of persisting them: a player can log in after the server
    // restarts.
    const db = await PGlite.create();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const credential = makeCredential('p1', 'correct horse');
    await new PostgresCredentialStore({ db }).put(credential);

    const afterRestart = new PostgresCredentialStore({ db });
    const loaded = await afterRestart.get('p1');
    assert.ok(loaded);
    assert.equal(credentialMatches(loaded!, 'correct horse'), true);

    await db.close();
  });

  it('replaces a credential rather than refusing', async () => {
    const db = await PGlite.create();
    await runMigrations(db, SCHEMA_MIGRATIONS);
    const store = new PostgresCredentialStore({ db });

    await store.put(makeCredential('p1', 'one'));
    const second = makeCredential('p1', 'two');
    await store.put(second);

    const loaded = await store.get('p1');
    assert.equal(loaded!.passwordHash, second.passwordHash);
    assert.equal((await store.all()).length, 1);

    await db.close();
  });
});
