/**
 * The offline mode.
 *
 * The game can be played **without a server**: the same rules engine,
 * the same decisions, the same answers, against a database that is a
 * directory in the server and IndexedDB in the browser.
 *
 * That is not a second implementation. The **same applier** runs, over
 * the **same schema** — the migrations are the server's own — and the
 * results are the same, because the rules engine is pure and seeded
 * (ADR 2).
 *
 * ## What it is not
 *
 * The offline mode is **single-player**. There is no account and no
 * password, because the credential hashing is the one part of the
 * authentication that needs the platform, and an offline player has
 * nobody to authenticate to. The world is local, and it stays local.
 *
 * ## The database
 *
 * PGlite is PostgreSQL compiled to WebAssembly, so the browser runs
 * **the same database** as the server — the same SQL, the same types
 * and the same migrations. It is stored in IndexedDB.
 */
import { PGlite } from '@electric-sql/pglite';

import { createApplier } from '@swl/server/apply';
import { runMigrations } from '@swl/server/migrations';
import type { ShimWorld } from '@swl/server/apply';

import { SCHEMA_MIGRATIONS } from '@swl/server/schema';

/** How the offline mode is set up. */
export interface OfflineOptions {
  /** Where the database lives. It is IndexedDB, so it is a name. */
  name?: string;
  /** The clock, in seconds. */
  now?: () => number;
  /** The clock, in milliseconds. */
  nowMs?: () => number;
}

/** The offline mode. */
export interface OfflineMode {
  /** The database. */
  db: PGlite;
  /** The player's world. */
  world: ShimWorld;
  /** Apply a batch of commands, the way the server does. */
  apply: (
    commands: readonly { name: string; args: readonly unknown[] }[],
  ) => Promise<{ ok: boolean; outcomes: unknown[] }>;
  /** Close the database. */
  close: () => Promise<void>;
}

/** The player the offline mode plays as. */
export const OFFLINE_PLAYER = 'offline';

/**
 * The offline mode's world.
 *
 * The same shape the server's development player gets: an empty town and
 * the starting resources.
 */
export function initialOfflineWorld(): ShimWorld {
  return {
    save: {
      playerInfo: { pid: OFFLINE_PLAYER, name: 'Offline' },
      maps: [{ id: 0, items: {} }],
      privateState: {},
    },
    resources: { g: 2000, w: 2000, o: 2000, s: 2000, c: 2000, e: 50, x: 0, m: 0 },
    nextCommandNumber: 1,
  };
}

/**
 * Open the offline mode.
 *
 * The database is created if it is not there, the **server's own**
 * migrations are run over it, and the player's world is written.
 */
export async function openOffline(options: OfflineOptions = {}): Promise<OfflineMode> {
  const now = options.now ?? (() => Math.floor(Date.now() / 1000));
  const nowMs = options.nowMs ?? (() => Date.now());

  const db = await PGlite.create({ dataDir: options.name ?? 'swl-offline' });
  await runMigrations(db, SCHEMA_MIGRATIONS);

  // The world is stored in the same table the server uses, so the two
  // are the same shape and the same migrations apply.
  await db.query(
    `INSERT INTO player_saves (player_id, doc) VALUES ($1, $2)
     ON CONFLICT (player_id) DO NOTHING`,
    [OFFLINE_PLAYER, JSON.stringify(initialOfflineWorld())],
  );

  let world = initialOfflineWorld();
  const row = await db.query<{ doc: unknown }>(
    'SELECT doc FROM player_saves WHERE player_id = $1',
    [OFFLINE_PLAYER],
  );
  const stored = row.rows[0]?.doc;
  if (stored && typeof stored === 'object') {
    world = stored as ShimWorld;
  }

  const applier = createApplier({
    now,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [5, 60, 240, 480], multiplier: [0.25, 1, 2, 3] },
    dailyBonus: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1001 },
  });

  return {
    db,
    get world() {
      return world;
    },
    async apply(commands) {
      const outcomes: unknown[] = [];
      let ok = true;
      for (const command of commands) {
        const outcome = applier(world, { name: command.name as never, args: [...command.args] });
        world = outcome.world;
        if (!outcome.applied) ok = false;
        outcomes.push({
          name: command.name,
          applied: outcome.applied,
          refused: outcome.refused ?? null,
        });
      }

      // The world is written back, so the next command sees it.
      await db.query(
        'UPDATE player_saves SET doc = $2 WHERE player_id = $1',
        [OFFLINE_PLAYER, JSON.stringify(world)],
      );

      return { ok, outcomes };
    },
    async close() {
      await db.close();
    },
  };
}
