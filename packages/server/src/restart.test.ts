import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { PGlite } from '@electric-sql/pglite';

import { PostgresPlayerStore } from './pgstore.ts';
import { createApplier, localDayOfWeek } from './apply.ts';
import { runMigrations } from './migrations.ts';
import { SCHEMA_MIGRATIONS } from './schema.ts';
import { isPremiumActive } from '@swl/rules';
import type { ShimWorld } from './shim.ts';

/**
 * A restart.
 *
 * The server's state is **timestamps**: when the daily bonus was last
 * claimed, when the weekly one was, and when the premium runs out. A
 * timestamp that is not persisted is a bonus a player can claim twice
 * by restarting the server, and a premium that comes back from the
 * dead.
 *
 * So the database is a **directory**, the server is stopped, the
 * directory is opened again, and the state is checked.
 */

/** A Monday, in seconds. The first of January 2024 was a Monday. */
const MONDAY = 1_704_067_200;

/** A Tuesday, the day after. */
const TUESDAY = MONDAY + 86_400;

/** The world a new player gets. */
function world(): ShimWorld {
  return {
    save: {
      playerInfo: { pid: 'p1', name: 'me' },
      maps: [{ id: 0, items: {} }],
      privateState: {},
    },
    resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

/** The applier, with the rules the cycles need. */
function applier(now: () => number) {
  return createApplier({
    now,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
    dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
    premiumPackages: [
      { price: 500, time: 30 },
      { price: 900, time: 90 },
    ],
    mondayBonus: {
      rewards: [
        { type: 'gold', value: 1000 },
        { type: 'gold', value: 2000 },
        { type: 'gold', value: 5000 },
      ],
    },
  });
}

/** Open the database, bring the schema forward, and open the store. */
async function open(directory: string) {
  const db = await PGlite.create({ dataDir: directory });
  await runMigrations(db, SCHEMA_MIGRATIONS);
  const store = new PostgresPlayerStore({ db });
  await store.init();
  return { db, store };
}

describe('a restart', () => {
  it('keeps the daily bonus claimed', async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), 'swl-restart-'));
    try {
      // --- The first run: the bonus is claimed. -----------------------
      const first = await open(directory);
      await first.store.add('p1', world());
      const apply = applier(() => MONDAY);
      const before = await first.store.get('p1');
      assert.ok(before);
      const claimed = apply(before.world, { name: 'win_daily_bonus', args: [] });
      assert.equal(claimed.applied, true);
      await first.store.add('p1', claimed.world);
      await first.db.close();

      // --- The second run: the bonus is refused. ----------------------
      const second = await open(directory);
      const after = await second.store.get('p1');
      assert.ok(after);
      const refused = applier(() => MONDAY)(after.world, {
        name: 'win_daily_bonus',
        args: [],
      });
      assert.equal(refused.applied, false);
      assert.equal(refused.refused, 'not-ready');
      await second.db.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it('keeps the weekly bonus collected', async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), 'swl-restart-'));
    try {
      assert.equal(localDayOfWeek(MONDAY, 0), 1, 'the day under test is a Monday');

      const first = await open(directory);
      await first.store.add('p1', world());
      const apply = applier(() => MONDAY);
      const before = await first.store.get('p1');
      assert.ok(before);
      const claimed = apply(before.world, { name: 'weekly_reward', args: [] });
      assert.equal(claimed.applied, true);
      await first.store.add('p1', claimed.world);
      await first.db.close();

      const second = await open(directory);
      const after = await second.store.get('p1');
      assert.ok(after);
      const refused = applier(() => MONDAY)(after.world, {
        name: 'weekly_reward',
        args: [],
      });
      assert.equal(refused.applied, false);
      assert.equal(refused.refused, 'collected');
      await second.db.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it('keeps the premium expired', async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), 'swl-restart-'));
    try {
      const first = await open(directory);
      await first.store.add('p1', world());
      const apply = applier(() => MONDAY);
      const before = await first.store.get('p1');
      assert.ok(before);
      // The premium is bought and it runs out after a month.
      const bought = apply(before.world, { name: 'buy_premium_account', args: [0] });
      assert.equal(bought.applied, true);
      const expiry = Number(bought.world.save.privateState['timeStampEndPremium']);
      assert.ok(expiry > MONDAY, 'the premium has an end');
      assert.equal(isPremiumActive(expiry, MONDAY), true);
      await first.store.add('p1', bought.world);
      await first.db.close();

      // --- The second run: a month later the premium is still over. ---
      const second = await open(directory);
      const after = await second.store.get('p1');
      assert.ok(after);
      const expiryAfter = Number(after.world.save.privateState['timeStampEndPremium']);
      assert.equal(expiryAfter, expiry, 'the expiry survived the restart');
      assert.equal(isPremiumActive(expiryAfter, MONDAY + 40 * 86_400), false);
      await second.db.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it('lets the daily bonus be claimed again the next day', async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), 'swl-restart-'));
    try {
      const first = await open(directory);
      await first.store.add('p1', world());
      const claimed = applier(() => MONDAY)(
        (await first.store.get('p1'))!.world,
        { name: 'win_daily_bonus', args: [] },
      );
      assert.equal(claimed.applied, true);
      await first.store.add('p1', claimed.world);
      await first.db.close();

      // The next day, the bonus is ready again - the restart did not
      // freeze the cycle, it only kept the record.
      const second = await open(directory);
      const after = await second.store.get('p1');
      assert.ok(after);
      const again = applier(() => TUESDAY)(after.world, {
        name: 'win_daily_bonus',
        args: [],
      });
      assert.equal(again.applied, true);
      await second.db.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });
});
