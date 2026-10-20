/**
 * The PostgreSQL player store.
 *
 * The in-memory store is the reference implementation, and it is what the
 * offline (PGlite) mode uses when there is no server. This is the server's
 * own store, and it is the one the roadmap's F3 asks for: "state is stored
 * in PostgreSQL with transactional command application; concurrent commands
 * cannot corrupt a player".
 *
 * ## The transaction
 *
 * A command batch is applied inside a database transaction. The row is
 * locked `FOR UPDATE` first, so two commands for the same player are
 * **serialised**: the second waits for the first to commit and then sees
 * its result. Two commands for *different* players do not wait for each
 * other.
 *
 * The save document is one `JSONB` column. The document is a tree of
 * mixed types, and the game's queries are all by player id, so a document
 * column is the honest shape: splitting it across columns would mean
 * changing the document's schema every time the client gains a field.
 */
import type { PlayerSave, PlayerStore } from './store.ts';
import type { ShimWorld } from './shim.ts';
import { migrateSave, type MigrationItem } from './migrate.ts';

/** The database the store talks to. */
export interface Database {
  /** Run a statement that returns no rows. */
  exec(sql: string): Promise<unknown>;
  /** Run a statement that returns rows. */
  query<Row = Record<string, unknown>>(
    sql: string,
    params?: readonly unknown[],
  ): Promise<{ rows: Row[]; affectedRows?: number }>;
}

/** The row the save is stored in. */
interface SaveRow {
  player_id: string;
  doc: unknown;
}

/** The options the store takes. */
export interface PostgresStoreOptions {
  /** The database. */
  db: Database;
  /** The table to use. */
  table?: string;
  /**
   * The content items, for the migration's building defaults.
   *
   * Without them the migration cannot add a building's production
   * state, so the migration is skipped and the document is stored as it
   * is. With them, an upstream save becomes a versioned one.
   */
  items?: Map<number, MigrationItem>;
}

/**
 * The player store, backed by PostgreSQL.
 */
export class PostgresPlayerStore implements PlayerStore {
  private readonly db: Database;
  private readonly table: string;
  private readonly items?: Map<number, MigrationItem>;
  private count = 0;
  /**
   * The tail of each player's transaction queue.
   *
   * A transaction waits for the previous one on the same player, so two
   * commands for one player never interleave.
   */
  private readonly queues = new Map<string, Promise<unknown>>();

  constructor(options: PostgresStoreOptions) {
    this.db = options.db;
    this.table = options.table ?? 'player_saves';
    this.items = options.items;
  }

  /**
   * Migrate a stored document to the current version.
   *
   * Returns null when the document is from a version this server does
   * not understand, which the caller refuses rather than guessing at.
   */
  private migrate(doc: unknown): Record<string, unknown> | null {
    if (!this.items) {
      // Without the content the migration cannot do its work, so the
      // document is stored as it is.
      return doc as Record<string, unknown>;
    }
    try {
      const result = migrateSave(doc, { items: this.items });
      return result.save as unknown as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  /** Create the table if it is not there. */
  async init(): Promise<void> {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS ${this.table} (
        player_id TEXT PRIMARY KEY,
        doc       JSONB NOT NULL,
        updated   TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `);
    const counted = await this.db.query<{ n: number }>(
      `SELECT count(*)::int AS n FROM ${this.table}`,
    );
    this.count = counted.rows[0]?.n ?? 0;
  }

  /** A player's save, or null if there is none. */
  async get(playerId: string): Promise<PlayerSave | null> {
    const result = await this.db.query<SaveRow>(
      `SELECT player_id, doc FROM ${this.table} WHERE player_id = $1`,
      [playerId],
    );
    const row = result.rows[0];
    if (!row) return null;
    const migrated = this.migrate(row.doc);
    if (migrated === null) {
      // A save from a version this server does not understand.
      return null;
    }
    return { playerId: row.player_id, world: toWorld(migrated) };
  }

  /** Whether the player exists. */
  async has(playerId: string): Promise<boolean> {
    const result = await this.db.query<{ n: number }>(
      `SELECT 1 AS n FROM ${this.table} WHERE player_id = $1`,
      [playerId],
    );
    return result.rows.length > 0;
  }

  /**
   * Apply a change to a player's save, atomically.
   *
   * The row is locked for the duration of the transaction, so a second
   * command for the same player waits rather than interleaving. If the
   * change throws, the transaction is rolled back and the save is exactly
   * as it was.
   */
  async transact(
    playerId: string,
    change: (world: ShimWorld) => ShimWorld | Promise<ShimWorld>,
  ): Promise<PlayerSave | null> {
    // Wait for the previous transaction on this player.
    const previous = this.queues.get(playerId) ?? Promise.resolve();
    let release: () => void = () => {};
    const mine = new Promise<void>((resolve) => {
      release = resolve;
    });
    this.queues.set(
      playerId,
      previous.then(
        () => mine,
        () => mine,
      ),
    );
    await previous.catch(() => undefined);
    try {
      return await this.runTransaction(playerId, change);
    } finally {
      release();
      // The queue is only kept while it is busy.
      if (this.queues.get(playerId) === mine) this.queues.delete(playerId);
    }
  }

  /** The transaction itself. */
  private async runTransaction(
    playerId: string,
    change: (world: ShimWorld) => ShimWorld | Promise<ShimWorld>,
  ): Promise<PlayerSave | null> {
    await this.db.exec('BEGIN');
    try {
      const locked = await this.db.query<SaveRow>(
        `SELECT player_id, doc FROM ${this.table} WHERE player_id = $1 FOR UPDATE`,
        [playerId],
      );
      const row = locked.rows[0];
      if (!row) {
        await this.db.exec('ROLLBACK');
        return null;
      }

      const migrated = this.migrate(row.doc);
      if (migrated === null) {
        await this.db.exec('ROLLBACK');
        return null;
      }
      const next = await change(toWorld(migrated));

      await this.db.query(
        `UPDATE ${this.table} SET doc = $2, updated = now() WHERE player_id = $1`,
        [playerId, JSON.stringify(next)],
      );
      await this.db.exec('COMMIT');
      return { playerId, world: next };
    } catch (error) {
      await this.db.exec('ROLLBACK');
      throw error;
    }
  }

  /** Add a player, if they are not there already. */
  async add(playerId: string, world: ShimWorld): Promise<void> {
    const migrated = this.migrate(world);
    await this.db.query(
      `INSERT INTO ${this.table} (player_id, doc) VALUES ($1, $2)
       ON CONFLICT (player_id) DO UPDATE SET doc = EXCLUDED.doc, updated = now()`,
      [playerId, JSON.stringify(migrated ?? world)],
    );
    this.count += 1;
  }

  /**
   * Store a document **without** migrating it.
   *
   * The tests need it, and so does importing an upstream save verbatim:
   * an import should store exactly what it was given, and the migration
   * should happen when it is read.
   */
  async addRaw(playerId: string, document: unknown): Promise<void> {
    await this.db.query(
      `INSERT INTO ${this.table} (player_id, doc) VALUES ($1, $2)
       ON CONFLICT (player_id) DO UPDATE SET doc = EXCLUDED.doc, updated = now()`,
      [playerId, JSON.stringify(document)],
    );
    this.count += 1;
  }

  /** How many players are stored. */
  get size(): number {
    return this.count;
  }
}

/**
 * The world's shape, as it comes back from the database.
 *
 * The database holds the WORLD, but an **imported upstream save** is the
 * DOCUMENT - the upstream's shape, with `playerInfo`, `maps` and
 * `privateState` at the top. Both are accepted, so an upstream save can
 * be imported and read back without a conversion step.
 */
function toWorld(doc: unknown): ShimWorld {
  if (!doc || typeof doc !== 'object') {
    return {
      save: { playerInfo: {}, maps: [{}], privateState: {} },
      resources: {},
      nextCommandNumber: 1,
    };
  }
  const record = doc as Record<string, unknown>;
  const wrapped = 'save' in record && typeof record['save'] === 'object';
  const save = (wrapped ? record['save'] : record) as Record<string, unknown>;
  return {
    save: {
      playerInfo: (save['playerInfo'] ?? {}) as Record<string, unknown>,
      maps: (save['maps'] ?? []) as Record<string, unknown>[],
      privateState: (save['privateState'] ?? {}) as Record<string, unknown>,
    },
    resources: (wrapped ? (record['resources'] ?? {}) : {}) as Record<string, number>,
    nextCommandNumber: Number(record['nextCommandNumber'] ?? 1),
  };
}
