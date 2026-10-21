/**
 * The client's session.
 *
 * The client signs in with a **credential**, and the server issues a
 * **session token**:
 *
 * ```http
 * POST /api/session
 * {"playerId": "p1", "password": "..."}
 * ```
 *
 * ```json
 * {"token": "...", "playerId": "p1", "issuedAt": 1700000000, "expiresAt": 1702592000}
 * ```
 *
 * The token goes in the `Authorization` header, and it is **revocable**
 * and it **expires** — the server owns both, and the client only has to
 * notice when the server says no.
 *
 * The session is **remembered** in the browser's storage, so a player
 * does not sign in on every visit. That is a convenience, not a
 * requirement: the token is worthless without the server's agreement.
 */
import type { Resources } from '@swl/rules';

/** The session the server issues. */
export interface ServerSession {
  /** The session token. */
  token: string;
  /** The player it belongs to. */
  playerId: string;
  /** When it was issued, in seconds. */
  issuedAt: number;
  /** When it expires, in seconds. */
  expiresAt: number;
}

/** The client's own session. */
export interface ClientSession {
  /** The session token. */
  token: string;
  /** The player it belongs to. */
  playerId: string;
  /** When it expires, in seconds. */
  expiresAt: number;
}

/** Where the session is kept between visits. */
export const SESSION_KEY = 'swl.session';

/** How long the client waits before it stops using a session, in seconds. */
export const EXPIRY_MARGIN_SECONDS = 60;

/**
 * Whether a session has expired.
 *
 * The margin is there so that a session does not expire **in the middle**
 * of a request: a token that is good for another thirty seconds is
 * treated as good.
 */
export function isExpired(session: ClientSession, now: number): boolean {
  return session.expiresAt - EXPIRY_MARGIN_SECONDS <= now;
}

/** The client's session from the server's answer. */
export function fromServerSession(session: ServerSession): ClientSession {
  return {
    token: session.token,
    playerId: session.playerId,
    expiresAt: session.expiresAt,
  };
}

/**
 * The session, read out of the browser's storage.
 *
 * A storage that is not there, or that holds something odd, is treated
 * as no session at all — the client signs in again rather than sending
 * something it does not understand.
 */
export function readSession(storage: Storage | null): ClientSession | null {
  if (!storage) return null;
  let raw: string | null;
  try {
    raw = storage.getItem(SESSION_KEY);
  } catch {
    // A storage that refuses to be read is a storage that is not there.
    return null;
  }
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<ClientSession>;
    if (typeof parsed.token !== 'string' || typeof parsed.playerId !== 'string') {
      return null;
    }
    const expiresAt = Number(parsed.expiresAt);
    if (!Number.isFinite(expiresAt)) return null;
    return { token: parsed.token, playerId: parsed.playerId, expiresAt };
  } catch {
    return null;
  }
}

/** The session, written to the browser's storage. */
export function rememberSession(
  storage: Storage | null,
  session: ClientSession,
): void {
  if (!storage) return;
  try {
    storage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // A storage that refuses to be written is not a reason to fail.
  }
}

/** The session, forgotten. */
export function forgetSession(storage: Storage | null): void {
  if (!storage) return;
  try {
    storage.removeItem(SESSION_KEY);
  } catch {
    // As above.
  }
}

/** The header the token travels in. */
export function authorizationHeader(session: ClientSession): string {
  return `Bearer ${session.token}`;
}

/** The result of a sign-in. */
export type SignInResult =
  | { ok: true; session: ClientSession }
  | { ok: false; reason: 'invalid-credentials' | 'unknown-player' | 'network' };

/**
 * Sign in.
 *
 * The server's answer is the authority: a wrong password and an unknown
 * player are told apart, because the player needs to know which.
 */
export async function signIn(
  url: string,
  playerId: string,
  password: string,
  fetchImpl: typeof fetch = fetch,
): Promise<SignInResult> {
  let response: Response;
  try {
    response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ playerId, password }),
    });
  } catch {
    return { ok: false, reason: 'network' };
  }
  if (response.status === 404) return { ok: false, reason: 'unknown-player' };
  if (response.status === 401) return { ok: false, reason: 'invalid-credentials' };
  if (!response.ok) return { ok: false, reason: 'network' };
  try {
    const body = (await response.json()) as ServerSession;
    if (typeof body.token !== 'string' || !body.token) {
      return { ok: false, reason: 'network' };
    }
    return { ok: true, session: fromServerSession(body) };
  } catch {
    return { ok: false, reason: 'network' };
  }
}

/** The player's wallet, as the server sends it. */
export interface WorldSnapshot {
  maps: {
    id: number;
    items: Record<string, number[]>;
    /** The player's level. The original keeps it on the map. */
    level?: number;
    /** The XP the player has. */
    xp?: number;
    /** The extra population the map's expansions grant. */
    increasedPopulation?: number;
  }[];
  privateState: Record<string, unknown>;
  resources: Resources;
}
