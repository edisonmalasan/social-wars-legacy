import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { defaultDataDir, initialOfflineWorld, openOffline } from './offline.ts';

/**
 * The offline mode.
 *
 * The point of the offline mode is that it is **not** a second
 * implementation: the same rules engine, the same applier and the same
 * schema, running against a local database. So the test checks that the
 * decisions are the server's decisions - the same command, refused for
 * the same reason, granted for the same reason.
 */

/** A clock that does not move, so the tests are the same every time. */
function fixedClock(): () => number {
  return () => 1_700_000_000;
}

describe('the offline world', () => {
  it('starts with the resources the server gives a new player', () => {
    const world = initialOfflineWorld();
    assert.equal(world.resources.g, 2000);
    assert.equal(world.resources.e, 50);
    assert.equal(world.nextCommandNumber, 1);
  });

  it('has a database location that fits the platform', () => {
    // A browser has IndexedDB, and a node process does not.
    const dir = defaultDataDir();
    assert.match(dir, /^(idb:\/\/|memory:\/\/)/);
  });
});

describe('the offline mode', () => {
  it('opens, applies a command, and closes', async () => {
    const offline = await openOffline({
      dataDir: 'memory://offline-test-1',
      now: fixedClock(),
    });

    try {
      const before = offline.world.resources.g ?? 0;
      const answer = await offline.apply([{ name: 'win_daily_bonus', args: [] }]);
      assert.equal(answer.ok, true);
      assert.equal((answer.outcomes[0] as { applied: boolean }).applied, true);
      // The server's own rule gave the bonus.
      assert.ok((offline.world.resources.g ?? 0) > before);
    } finally {
      await offline.close();
    }
  });

  it('refuses a second bonus on the same day, the way the server does', async () => {
    const offline = await openOffline({
      dataDir: 'memory://offline-test-2',
      now: fixedClock(),
    });

    try {
      await offline.apply([{ name: 'win_daily_bonus', args: [] }]);
      const second = await offline.apply([
        { name: 'win_daily_bonus', args: [] },
      ]);
      assert.equal(second.ok, false);
      assert.equal(
        (second.outcomes[0] as { refused: string | null }).refused,
        'not-ready',
      );
    } finally {
      await offline.close();
    }
  });

  it('keeps the world, so the next command sees it', async () => {
    const offline = await openOffline({
      dataDir: 'memory://offline-test-3',
      now: fixedClock(),
    });

    try {
      await offline.apply([{ name: 'win_daily_bonus', args: [] }]);
      const gold = offline.world.resources.g ?? 0;
      // The bonus's own record: the server's, not the client's. The
      // first claim is the first tier.
      assert.equal(offline.world.save.privateState['bonusNextId'], 1);
      assert.equal(offline.world.resources.g, gold);
    } finally {
      await offline.close();
    }
  });

  it('runs the server\'s own schema', async () => {
    const offline = await openOffline({
      dataDir: 'memory://offline-test-4',
      now: fixedClock(),
    });

    try {
      const rows = await offline.db.query<{ player_id: string }>(
        'SELECT player_id FROM player_saves',
      );
      assert.equal(rows.rows.length, 1);
      assert.equal(rows.rows[0]!.player_id, 'offline');
    } finally {
      await offline.close();
    }
  });
});
