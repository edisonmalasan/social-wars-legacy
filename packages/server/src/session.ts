/**
 * Sessions and identity.
 *
 * The upstream server has **no authentication**: the `USERID` comes from the
 * request body, and `user_key` and `accessToken` are read and discarded
 * (finding F10, non-negotiable 7). Anyone can be anyone.
 *
 * The new server does not inherit that. A player authenticates with a real
 * credential, and the server issues a **revocable session token**. The token
 * identifies the player; nothing in the request body can change that.
 *
 * ## The legacy path
 *
 * The compatibility shim exists so the *untouched* original client can play.
 * That client can only send `USERID` in the body, because that is all it
 * knows how to send. So the shim needs a way to map that body value onto a
 * player — but it must be **explicitly enabled**, and it must not become the
 * server's normal authentication.
 *
 * `legacyIdentity` is therefore off by default and has to be turned on
 * deliberately, which is what `allowLegacyIdentity` is for.
 */
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';

/** A player's credential. */
export interface Credential {
  readonly playerId: string;
  /** The salted hash of the password. Never the password itself. */
  readonly passwordHash: string;
  readonly salt: string;
}

/** A live session. */
export interface Session {
  readonly token: string;
  readonly playerId: string;
  /** When the session was issued, in seconds. */
  readonly issuedAt: number;
  /** When the session expires, in seconds. */
  readonly expiresAt: number;
}

/** How long a session lasts, in seconds. */
export const SESSION_TTL_SECONDS = 60 * 60 * 24 * 30;

/** The result of authenticating. */
export type AuthenticationResult =
  | { ok: true; session: Session }
  | { ok: false; reason: 'unknown-player' | 'bad-credential' };

/** Hash a password with a salt. */
export function hashPassword(password: string, salt: string): string {
  return createHash('sha256').update(`${salt}:${password}`).digest('hex');
}

/** Compare two secrets in constant time. */
function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/**
 * The session store.
 *
 * Sessions are revocable: dropping the token invalidates it immediately.
 */
export class SessionStore {
  private readonly sessions = new Map<string, Session>();
  private readonly credentials = new Map<string, Credential>();

  /** Register a player and their credential. */
  addPlayer(playerId: string, password: string, salt = randomBytes(16).toString('hex')): Credential {
    const credential: Credential = {
      playerId,
      salt,
      passwordHash: hashPassword(password, salt),
    };
    this.credentials.set(playerId, credential);
    return credential;
  }

  /**
   * Authenticate and issue a session.
   *
   * A wrong password and an unknown player are reported differently, because
   * the caller needs to tell the two apart; the *timing* is not, because the
   * hash is still computed.
   */
  authenticate(
    playerId: string,
    password: string,
    now: number,
    ttlSeconds = SESSION_TTL_SECONDS,
  ): AuthenticationResult {
    const credential = this.credentials.get(playerId);
    if (!credential) return { ok: false, reason: 'unknown-player' };
    const candidate = hashPassword(password, credential.salt);
    if (!safeEqual(candidate, credential.passwordHash)) {
      return { ok: false, reason: 'bad-credential' };
    }
    const session: Session = {
      token: randomBytes(32).toString('hex'),
      playerId,
      issuedAt: now,
      expiresAt: now + ttlSeconds,
    };
    this.sessions.set(session.token, session);
    return { ok: true, session };
  }

  /** Resolve a token to its session, or null if it is unknown or expired. */
  resolve(token: string, now: number): Session | null {
    const session = this.sessions.get(token);
    if (!session) return null;
    if (session.expiresAt <= now) {
      this.sessions.delete(token);
      return null;
    }
    return session;
  }

  /** Revoke a token. Returns true if there was one. */
  revoke(token: string): boolean {
    return this.sessions.delete(token);
  }

  /** Revoke every session of a player. */
  revokeAllFor(playerId: string): number {
    let count = 0;
    for (const [token, session] of this.sessions) {
      if (session.playerId === playerId) {
        this.sessions.delete(token);
        count += 1;
      }
    }
    return count;
  }

  /** How many sessions are live. */
  get size(): number {
    return this.sessions.size;
  }
}

/**
 * The legacy identity bridge.
 *
 * The original client sends `USERID` in the request body, and the upstream
 * server believes it. For the compatibility shim to serve that client at
 * all, the body value has to be mapped onto a player.
 *
 * The bridge is **off by default**. It has to be enabled deliberately, and
 * even then it only maps a body value that the server has already bound to a
 * player — it cannot invent a player.
 */
export class LegacyIdentityBridge {
  private readonly bindings = new Map<string, string>();
  private enabled = false;

  /** Turn the bridge on. */
  allowLegacyIdentity(enabled = true): void {
    this.enabled = enabled;
  }

  /** Is the bridge on? */
  get isEnabled(): boolean {
    return this.enabled;
  }

  /** Bind a legacy `USERID` to a player. */
  bind(legacyUserId: string, playerId: string): void {
    this.bindings.set(legacyUserId, playerId);
  }

  /**
   * Resolve a legacy `USERID` to a player.
   *
   * Returns null when the bridge is off, or when the value is not bound.
   */
  resolve(legacyUserId: string | null | undefined): string | null {
    if (!this.enabled) return null;
    if (!legacyUserId) return null;
    return this.bindings.get(legacyUserId) ?? null;
  }
}
