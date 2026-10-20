/**
 * The HTTP application.
 *
 * The routing, the limits and the error handling, with **no** socket
 * involved: `createApp` turns a request into a response as a plain
 * function, so the whole surface can be tested without opening a port.
 *
 * ## The error contract
 *
 * Bad input produces a **typed 4xx**, never a 500 (roadmap F4). Every
 * failure the server can produce has a code and a message, and the codes are
 * listed in `ERROR_CODES`. An unexpected exception is caught at the edge and
 * turned into a 500 with a generic body — the details go to the log, not to
 * the client.
 *
 * ## The two dialects
 *
 * - the **legacy** endpoints (`command.php`, `get_game_config.php`,
 *   `get_player_info.php`) speak the original protocol, for the untouched
 *   Flash client.
 * - the **native** endpoints (`/api/...`) speak the new versioned protocol.
 *
 * Both share the same session model, the same authority layer and the same
 * limits.
 *
 * ## Atomicity
 *
 * A command batch is applied to a **copy** of the player's save, and the
 * copy replaces the save only once the whole batch has been processed. A
 * disconnect, a timeout or an exception half way through therefore leaves
 * the save exactly as it was, never half-written (roadmap F3 and F4).
 */
import {
  handleCommandPhp,
  handleGetGameConfig,
  handleGetPlayerInfo,
  LegacyIdentityBridge,
  SessionStore,
  type CommandApplier,
  type Session,
  type ShimRequest,
  type ShimResponse,
} from '@swl/server';
import type { CostContent } from '@swl/rules';

import { DEFAULT_LIMITS, RateLimiter, parseForm, type Limits } from './limits.ts';
import type { PlayerStore } from './store.ts';

/** A request, as the application sees it. */
export interface AppRequest {
  method: string;
  path: string;
  headers: Record<string, string | undefined>;
  /** The request body, already read. */
  body: string;
}

/** A response. */
export interface AppResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
}

/** The typed error codes the server can return. */
export const ERROR_CODES = {
  'not-found': 'no such endpoint',
  'method-not-allowed': 'the endpoint does not accept that method',
  'body-too-large': 'the request body is too large',
  'rate-limited': 'too many requests',
  'malformed-json': 'the body is not valid JSON',
  'missing-credentials': 'the player id or the password is missing',
  'invalid-credentials': 'the player id or the password is wrong',
  'unknown-player': 'no such player',
  'internal-error': 'the server failed to handle the request',
} as const;

export type ErrorCode = keyof typeof ERROR_CODES;

/** Everything the application needs. */
export interface AppOptions {
  /** The player store. */
  store: PlayerStore;
  /** The session store. */
  sessions: SessionStore;
  /** The legacy identity bridge. */
  identity: LegacyIdentityBridge;
  /** The content, for the server-computed costs. */
  content: CostContent;
  /** The whole content bundle, for `get_game_config.php`. */
  contentBundle: Record<string, unknown>;
  /** The clock, in seconds. */
  now: () => number;
  /** The clock, in milliseconds. */
  nowMs?: () => number;
  /** Applies one command's semantics. */
  applyCommand: CommandApplier;
  /** The limits. */
  limits?: Limits;
  /** The neighbours, for `get_player_info.php`. */
  neighbours?: Record<string, Record<string, unknown>>;
}

/** A JSON response. */
function json(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
): AppResponse {
  return {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...headers },
    body: JSON.stringify(body),
  };
}

/** A typed error response. */
function fail(
  status: number,
  code: ErrorCode,
  headers: Record<string, string> = {},
): AppResponse {
  return json(status, { result: 'error', error: code, message: ERROR_CODES[code] }, headers);
}

/** The response body for a shim response. */
function fromShim(response: ShimResponse): AppResponse {
  return {
    status: response.status,
    headers: { 'content-type': response.contentType },
    body: response.body,
  };
}

/**
 * Create the application.
 *
 * The returned function is the whole server, minus the socket.
 */
export function createApp(options: AppOptions): (request: AppRequest) => AppResponse {
  const limits = options.limits ?? DEFAULT_LIMITS;
  const limiter = new RateLimiter(limits);

  /** The client a request came from, for the rate limit. */
  function clientKey(request: AppRequest): string {
    const forwarded = request.headers['x-forwarded-for'];
    if (forwarded) return forwarded.split(',')[0]?.trim() ?? 'unknown';
    return request.headers['x-real-ip'] ?? 'local';
  }

  /** The request's fields: the query string and a form body. */
  function fieldsOf(request: AppRequest): Record<string, string> {
    const fields: Record<string, string> = {};
    const at = request.path.indexOf('?');
    if (at >= 0) {
      Object.assign(fields, parseForm(request.path.slice(at + 1)));
    }
    const contentType = request.headers['content-type'] ?? '';
    if (request.body !== '' && contentType.includes('application/x-www-form-urlencoded')) {
      Object.assign(fields, parseForm(request.body));
    }
    return fields;
  }

  /**
   * Identify the player.
   *
   * The **session token** is preferred; the legacy `USERID` is the
   * fallback, and it only resolves when the bridge has been enabled and the
   * server has already bound that value to a player.
   */
  function identify(request: AppRequest): string | null {
    const token = request.headers['authorization']?.replace(/^Bearer\s+/i, '');
    if (token) {
      const session = options.sessions.resolve(token, options.now());
      return session ? session.playerId : null;
    }
    return options.identity.resolve(fieldsOf(request)['USERID']);
  }

  /** The legacy `command.php`. */
  function handleLegacyCommand(request: AppRequest): AppResponse {
    const playerId = identify(request);
    if (!playerId) return fail(401, 'unknown-player');

    const fields = fieldsOf(request);
    let response: AppResponse = fail(500, 'internal-error');

    // The transaction runs against a COPY of the save. The copy is committed
    // only when the whole batch has been processed, so a disconnect or a
    // timeout leaves the save exactly as it was.
    const stored = options.store.transact(playerId, (world) => {
      const shimContext = {
        world,
        // The identity has already been resolved, and it is the only thing
        // that decides whose save this is.
        identifiedPlayerId: playerId,
        worldFor: () => world,
        content: options.content,
        now: options.now(),
        identity: options.identity,
        applyCommand: options.applyCommand,
        deadline:
          options.nowMs !== undefined ? options.nowMs() + limits.commandTimeoutMs : undefined,
        clock: options.nowMs,
      };
      const shim = handleCommandPhp({ path: request.path, fields }, shimContext);
      response = fromShim(shim);
      return shimContext.world;
    });

    if (!stored) return fail(401, 'unknown-player');
    return response;
  }

  /** Create a session. */
  function createSession(request: AppRequest): AppResponse {
    let body: { playerId?: string; password?: string };
    try {
      body = JSON.parse(request.body) as { playerId?: string; password?: string };
    } catch {
      return fail(400, 'malformed-json');
    }
    if (!body.playerId || !body.password) {
      return fail(400, 'missing-credentials');
    }
    const result = options.sessions.authenticate(body.playerId, body.password, options.now());
    if (!result.ok) {
      return fail(result.reason === 'unknown-player' ? 404 : 401, 'invalid-credentials');
    }
    const session: Session = result.session;
    return json(200, {
      token: session.token,
      playerId: session.playerId,
      issuedAt: session.issuedAt,
      expiresAt: session.expiresAt,
    });
  }

  /** Revoke a session. */
  function deleteSession(request: AppRequest): AppResponse {
    const token = request.headers['authorization']?.replace(/^Bearer\s+/i, '');
    if (!token) return fail(400, 'missing-credentials');
    const revoked = options.sessions.revoke(token);
    return json(200, { revoked });
  }

  return function handle(request: AppRequest): AppResponse {
    // --- the limits, before anything else -------------------------------
    if (request.body.length > limits.maxBodyBytes) {
      return fail(413, 'body-too-large');
    }
    const wait = limiter.check(clientKey(request), options.now());
    if (wait > 0) {
      return fail(429, 'rate-limited', { 'retry-after': String(wait) });
    }

    const path = request.path.split('?')[0] ?? request.path;

    try {
      // --- the health check ---------------------------------------------
      if (path === '/health' || path === '/api/health') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        return json(200, { status: 'ok', protocol: 1 });
      }

      // --- the native session endpoints ---------------------------------
      if (path === '/api/session') {
        if (request.method === 'POST') return createSession(request);
        if (request.method === 'DELETE') return deleteSession(request);
        return fail(405, 'method-not-allowed');
      }

      // --- the legacy endpoints -----------------------------------------
      if (path === '/command.php') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        return handleLegacyCommand(request);
      }
      if (path === '/get_game_config.php') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        return fromShim(
          handleGetGameConfig({ path: request.path, fields: fieldsOf(request) }, {
            content: options.contentBundle,
            now: options.now(),
          }),
        );
      }
      if (path === '/get_player_info.php') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        const playerId = identify(request);
        if (!playerId) return fail(401, 'unknown-player');
        const own = options.store.get(playerId);
        if (!own) return fail(401, 'unknown-player');
        return fromShim(
          handleGetPlayerInfo({ path: request.path, fields: fieldsOf(request) }, {
            own: {
              playerInfo: own.world.save.playerInfo,
              map: own.world.save.maps[0] ?? {},
              privateState: own.world.save.privateState,
              neighbors: [],
            },
            neighbours: options.neighbours ?? {},
            now: options.now(),
          }),
        );
      }

      return fail(404, 'not-found');
    } catch (error) {
      // An unexpected failure is a 500, but the details stay here.
      console.error('[server] unhandled error:', error);
      return fail(500, 'internal-error');
    }
  };
}
