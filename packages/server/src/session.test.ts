import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { SessionStore, SESSION_TTL_SECONDS } from './session.ts';

describe('the session store', () => {
  it('issues a token for a correct credential', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    const result = sessions.authenticate('p1', 'correct horse', 1_000);
    assert.equal(result.ok, true);
    assert.ok(result.ok && result.session.token.length > 0);
  });

  it('refuses a wrong password', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    const result = sessions.authenticate('p1', 'wrong horse', 1_000);
    assert.equal(result.ok, false);
    assert.equal(!result.ok && result.reason, 'bad-credential');
  });

  it('refuses an unknown player', () => {
    const sessions = new SessionStore();
    const result = sessions.authenticate('nobody', 'anything', 1_000);
    assert.equal(result.ok, false);
    assert.equal(!result.ok && result.reason, 'unknown-player');
  });

  it('does not store the password', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'correct horse');
    // The credential is a hash and a salt, and the store's own text must
    // not contain the password.
    const text = JSON.stringify([...sessions['credentials'].values()]);
    assert.ok(!text.includes('correct horse'), 'the password is in the store');
  });

  it('SCOPES the token to its player', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    sessions.addPlayer('p2', 'two');
    const first = sessions.authenticate('p1', 'one', 1_000);
    const second = sessions.authenticate('p2', 'two', 1_000);
    assert.ok(first.ok && second.ok);
    const resolved = sessions.resolve(first.session.token, 1_001);
    assert.equal(resolved?.playerId, 'p1');
    const other = sessions.resolve(second.session.token, 1_001);
    assert.equal(other?.playerId, 'p2');
  });

  it('makes a different token for each session', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    const first = sessions.authenticate('p1', 'one', 1_000);
    const second = sessions.authenticate('p1', 'one', 1_000);
    assert.ok(first.ok && second.ok);
    assert.notEqual(first.session.token, second.session.token);
  });

  it('is REVOCABLE', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    const result = sessions.authenticate('p1', 'one', 1_000);
    assert.ok(result.ok);
    assert.equal(sessions.resolve(result.session.token, 1_001)?.playerId, 'p1');
    assert.equal(sessions.revoke(result.session.token), true);
    assert.equal(sessions.resolve(result.session.token, 1_001), null);
    // Revoking it twice says so.
    assert.equal(sessions.revoke(result.session.token), false);
  });

  it('revokes every session of a player at once', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    sessions.addPlayer('p2', 'two');
    const first = sessions.authenticate('p1', 'one', 1_000);
    const second = sessions.authenticate('p1', 'one', 1_000);
    const other = sessions.authenticate('p2', 'two', 1_000);
    assert.ok(first.ok && second.ok && other.ok);
    assert.equal(sessions.revokeAllFor('p1'), 2);
    assert.equal(sessions.resolve(first.session.token, 1_001), null);
    assert.equal(sessions.resolve(second.session.token, 1_001), null);
    // The other player's session is untouched.
    assert.equal(sessions.resolve(other.session.token, 1_001)?.playerId, 'p2');
  });

  it('EXPIRES', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    const result = sessions.authenticate('p1', 'one', 1_000, 60);
    assert.ok(result.ok);
    // It is alive before the expiry and gone at it.
    assert.ok(sessions.resolve(result.session.token, 1_059));
    assert.equal(sessions.resolve(result.session.token, 1_060), null);
  });

  it('forgets an expired session', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    const result = sessions.authenticate('p1', 'one', 1_000, 60);
    assert.ok(result.ok);
    sessions.resolve(result.session.token, 2_000);
    // The expired one is dropped, not kept.
    assert.equal(sessions.size, 0);
  });

  it('has a default lifetime', () => {
    const sessions = new SessionStore();
    sessions.addPlayer('p1', 'one');
    const result = sessions.authenticate('p1', 'one', 1_000);
    assert.ok(result.ok);
    assert.equal(result.session.expiresAt, 1_000 + SESSION_TTL_SECONDS);
    // Thirty days.
    assert.equal(SESSION_TTL_SECONDS, 60 * 60 * 24 * 30);
  });

  it('resolves an unknown token to nothing', () => {
    const sessions = new SessionStore();
    assert.equal(sessions.resolve('not-a-token', 1_000), null);
  });
});
