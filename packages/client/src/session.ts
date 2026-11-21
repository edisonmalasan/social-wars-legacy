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

/** The result of a sign-in or a registration. */
export type SignInResult =
  | { ok: true; session: ClientSession }
  | {
      ok: false;
      reason: 'invalid-credentials' | 'unknown-player' | 'player-exists' | 'network';
    };

/** The two forms the account screen can show. */
export type AuthMode = 'sign-in' | 'register';

/**
 * The endpoint a mode uses.
 *
 * Registration creates the account and signs the player in; sign-in only
 * signs in. Both answer with the same session shape, so the client keeps one
 * session flow and chooses only the endpoint.
 */
export function authEndpoint(mode: AuthMode): string {
  return mode === 'register' ? '/api/account' : '/api/session';
}

/**
 * Authenticate in the chosen mode.
 *
 * The form never decides a credential's validity: the server's answer does.
 */
export async function authenticate(
  mode: AuthMode,
  playerId: string,
  password: string,
  fetchImpl: typeof fetch = fetch,
): Promise<SignInResult> {
  return signIn(authEndpoint(mode), playerId, password, fetchImpl);
}

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
  // The account endpoint answers 409 when the name is taken. Sign-in never
  // does, so this is harmless for it and tells a would-be registrant why.
  if (response.status === 409) return { ok: false, reason: 'player-exists' };
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
    /**
     * The bought-but-unplaced items, keyed by content id. The save keeps it
     * on the map and the world endpoint sends the map verbatim; older saves
     * have no store at all.
     */
    store?: Record<string, number>;
    /** The player's level. The original keeps it on the map. */
    level?: number;
    /** The XP the player has. */
    xp?: number;
    /**
     * The tile ids the player has bought, as the server's save keeps them.
     * The world endpoint sends the map verbatim; older saves have no field.
     * The server owns the list — the client reads it, never writes it.
     */
    expansions?: number[];
    /** The extra population the map's expansions grant. */
    increasedPopulation?: number;
    /** The rank each quest was reached at, by the quest's index. */
    questsRank?: Record<string, number>;
    /** How many market trades this period has used. */
    numTradesDone?: number;
    /** What was traded at the market, by resource key. */
    resourcesTraded?: Record<string, unknown>;
    /** When the last market trade happened. */
    timestampLastTrade?: number;
    /** The timestamps the server recorded for each quest, by quest id. */
    questTimes?: Record<string, number>;
    /** The id of the current mission. */
    idCurrentMission?: number;
    /** The current mission's variables. */
    currentQuestVars?: Record<string, unknown> | null;
  }[];
  privateState: Record<string, unknown>;
  resources: Resources;
}
