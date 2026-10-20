/**
 * The social store.
 *
 * The alliance and the marketplace are **pure**: the state is passed in and
 * the new state is returned. That makes them easy to persist — the whole
 * state is one document — and it means a restart cannot half-apply a
 * change.
 *
 * The state lives in one table with a `kind` column, so the social
 * subsystem is a single row per kind rather than a table per service.
 */
import type { Database } from './pgstore.ts';
import type { Alliance } from './alliance.ts';

/** The kinds of social state there are. */
export type SocialKind = 'alliances' | 'marketplace';

/** One document of social state. */
export interface SocialRecord {
  kind: SocialKind;
  doc: unknown;
}

/** The store. */
export class SocialStore {
  private readonly db: Database;
  private readonly table: string;

  constructor(options: { db: Database; table?: string }) {
    this.db = options.db;
    this.table = options.table ?? 'social';
  }

  /** Create the table if it is not there. */
  async init(): Promise<void> {
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS ${this.table} (
        kind TEXT PRIMARY KEY,
        doc  JSONB NOT NULL,
        updated TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `);
  }

  /** Read one kind's document. */
  async load(kind: SocialKind): Promise<unknown | null> {
    const result = await this.db.query<{ doc: unknown }>(
      `SELECT doc FROM ${this.table} WHERE kind = $1`,
      [kind],
    );
    const row = result.rows[0];
    return row ? row.doc : null;
  }

  /** Write one kind's document. */
  async save(kind: SocialKind, doc: unknown): Promise<void> {
    await this.db.query(
      `INSERT INTO ${this.table} (kind, doc) VALUES ($1, $2)
       ON CONFLICT (kind) DO UPDATE SET doc = EXCLUDED.doc, updated = now()`,
      [kind, JSON.stringify(doc)],
    );
  }

  /** Read the alliances, or an empty list when there are none yet. */
  async loadAlliances(): Promise<Alliance[]> {
    const doc = await this.load('alliances');
    if (!Array.isArray(doc)) return [];
    return doc as Alliance[];
  }

  /** Write the alliances. */
  async saveAlliances(alliances: readonly Alliance[]): Promise<void> {
    await this.save('alliances', alliances);
  }

  /**
   * Read the marketplace's state.
   *
   * The marketplace's state is a record of listings by uuid, and the
   * service takes it whole.
   */
  async loadMarketplace(): Promise<Record<string, unknown>> {
    const doc = await this.load('marketplace');
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return {};
    return doc as Record<string, unknown>;
  }

  /** Write the marketplace's state. */
  async saveMarketplace(state: unknown): Promise<void> {
    await this.save('marketplace', state);
  }

  /** How many kinds of social state are stored. */
  async count(): Promise<number> {
    const result = await this.db.query<{ n: number }>(
      `SELECT count(*)::int AS n FROM ${this.table}`,
    );
    return result.rows[0]?.n ?? 0;
  }
}
