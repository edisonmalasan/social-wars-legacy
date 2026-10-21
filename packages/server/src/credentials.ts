/**
 * The players' credentials.
 *
 * A credential is a **salt** and the **hash** of a password. The password
 * itself is never stored, and the hash is compared in constant time.
 *
 * The store is **persistent**: a player who registers can log in after the
 * server restarts. The session store keeps the credentials in memory for
 * the authentication path, and this is what the server loads them from and
 * writes them to.
 *
 * ## Why the hash is a plain salted SHA-256
 *
 * It is not a password hash in the modern sense — those are deliberately
 * slow, and deliberately expensive. This one is a salted SHA-256, which
 * is fast.
 *
 * That is a deliberate trade and it is recorded: the server is a
 * **preservation** of a 2012 game with a handful of players rather than
 * a bank, the threat is not an offline attack on a stolen table, and a
 * slow hash would make the server's own logins slow. A deployment that
 * grows players or faces a stolen table should move to a memory-hard
 * hash, and that is a change in this module alone.
 */
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';

import type { Database } from './pgstore.ts';
import { CREDENTIALS_TABLE } from './schema.ts';
import { isSafeIdentifier } from './backup.ts';

/** A player's credential. */
export interface Credential {
  /** The player's id. */
  readonly playerId: string;
  /** The salted hash of the password. Never the password itself. */
  readonly passwordHash: string;
  /** The salt. */
  readonly salt: string;
}

/** Where the credentials live. */
export interface CredentialStore {
  /** A player's credential, or null when there is none. */
  get(playerId: string): Promise<Credential | null>;
  /** Every credential. */
  all(): Promise<Credential[]>;
  /** A credential, written. */
  put(credential: Credential): Promise<void>;
  /** A credential, removed. Whether there was one. */
  remove(playerId: string): Promise<boolean>;
}

/** Hash a password with a salt. */
export function hashPassword(password: string, salt: string): string {
  return createHash('sha256').update(`${salt}:${password}`).digest('hex');
}

/** Compare two secrets in constant time. */
export function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/** A new salt. */
export function newSalt(): string {
  return randomBytes(16).toString('hex');
}

/** A credential for a password. */
export function makeCredential(
  playerId: string,
  password: string,
  salt = newSalt(),
): Credential {
  return { playerId, salt, passwordHash: hashPassword(password, salt) };
}

/** Whether a password matches a credential. */
export function credentialMatches(
  credential: Credential,
  password: string,
): boolean {
  return safeEqual(hashPassword(password, credential.salt), credential.passwordHash);
}

/** The credentials, in memory. */
export class MemoryCredentialStore implements CredentialStore {
  private readonly credentials = new Map<string, Credential>();

  async get(playerId: string): Promise<Credential | null> {
    return this.credentials.get(playerId) ?? null;
  }

  async all(): Promise<Credential[]> {
    return [...this.credentials.values()];
  }

  async put(credential: Credential): Promise<void> {
    this.credentials.set(credential.playerId, credential);
  }

  async remove(playerId: string): Promise<boolean> {
    return this.credentials.delete(playerId);
  }
}

/**
 * The players' credentials, in PostgreSQL.
 *
 * A credential is a salt and a hash, and the **password is never
 * stored** - not here and not anywhere else.
 */
export class PostgresCredentialStore implements CredentialStore {
  private readonly db: Database;
  private readonly table: string;

  constructor(options: { db: Database; table?: string }) {
    this.db = options.db;
    this.table = options.table ?? CREDENTIALS_TABLE;
    // The table name goes into the SQL, because SQL has no placeholder
    // for an identifier, so it is checked: a table name must be a plain
    // identifier and nothing else.
    if (!isSafeIdentifier(this.table)) {
      throw new Error(`the table name "${this.table}" is not a plain identifier`);
    }
  }

  /** A player's credential, or null when there is none. */
  async get(playerId: string): Promise<Credential | null> {
    const result = await this.db.query<CredentialRow>(
      `SELECT player_id, salt, password_hash FROM ${this.table} WHERE player_id = $1`,
      [playerId],
    );
    const row = result.rows[0];
    if (!row) return null;
    return {
      playerId: row.player_id,
      salt: row.salt,
      passwordHash: row.password_hash,
    };
  }

  /** Every credential. */
  async all(): Promise<Credential[]> {
    const result = await this.db.query<CredentialRow>(
      `SELECT player_id, salt, password_hash FROM ${this.table}`,
    );
    return result.rows.map((row) => ({
      playerId: row.player_id,
      salt: row.salt,
      passwordHash: row.password_hash,
    }));
  }

  /** A credential, written. */
  async put(credential: Credential): Promise<void> {
    await this.db.query(
      `INSERT INTO ${this.table} (player_id, salt, password_hash)
       VALUES ($1, $2, $3)
       ON CONFLICT (player_id) DO UPDATE
         SET salt = EXCLUDED.salt, password_hash = EXCLUDED.password_hash`,
      [credential.playerId, credential.salt, credential.passwordHash],
    );
  }

  /** A credential, removed. Whether there was one. */
  async remove(playerId: string): Promise<boolean> {
    const result = await this.db.query(
      `DELETE FROM ${this.table} WHERE player_id = $1`,
      [playerId],
    );
    return (result.affectedRows ?? 0) > 0;
  }
}

/** A row of the credentials table. */
interface CredentialRow {
  player_id: string;
  salt: string;
  password_hash: string;
}
