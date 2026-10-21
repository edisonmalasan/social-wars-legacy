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
 * ## The native endpoints
 *
 * | Endpoint | What it does |
 * |---|---|
 * | `POST /api/account` | create a player and sign them in |
 * | `POST /api/session` | sign in |
 * | `DELETE /api/session` | sign out - the token is revoked |
 * | `POST /api/command` | apply a batch of commands |
 * | `GET /api/world` | the player's world, for the client to draw |
 * | `GET /api/metrics` | the metrics, as JSON |
 * | `GET /health` | whether the server is alive |
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
  type PlayerStore,
  type Session,
  type ShimRequest,
  type ShimResponse,
  type ShimWorld,
} from '@swl/server';
import { applyCommandCost, computeCommandCost, type CostContent } from '@swl/rules';
import { MemoryPlayerStore } from '@swl/server';
import {
  dashboardHtml,
  healthReport,
  makeCredential,
  prometheusText,
  type AlertSender,
  type CredentialStore,
} from '@swl/server';

import { handleSocialRequest, type SocialOptions } from './social.ts';
import {
  PROTOCOL_VERSION,
  successResponse,
  validateRequest,
  type CommandOutcome,
  type NativeRequest,
} from '@swl/protocol';

import { DEFAULT_LIMITS, RateLimiter, parseForm, type Limits } from './limits.ts';
import {
  Metrics,
  REQUEST_ID_HEADER,
  SILENT_LOGGER,
  initialWorld,
  newRequestId,
  seriesKey,
  snapshot,
  type Logger,
} from '@swl/server';


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
  'bad-player-id': 'the player id is too long or not allowed',
  'player-exists': 'there is already a player with that name',
  'no-credential-store': 'the server has nowhere to keep the credentials',
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
  /**
   * Where the players' credentials are kept.
   *
   * Without it the account endpoint cannot persist a player, and says
   * so rather than pretending.
   */
  credentials?: CredentialStore;
  /** The server's version, for the health report. */
  version?: string;
  /** The asset bundle's build id, for the health report. */
  assetBuildId?: string | null;
  /**
   * Where the alerts go.
   *
   * Without one the alerts are still in the report and on the
   * dashboard, but nobody is **told** — and an alert that nobody is told
   * about is not an alert.
   */
  alertSender?: AlertSender;
  /** The neighbours, for `get_player_info.php`. */
  neighbours?: Record<string, Record<string, unknown>>;
  /** The alliance and betting services, for the social endpoints. */
  social?: SocialOptions;
  /** Where the structured log goes. */
  logger?: Logger;
  /** The metrics registry. */
  metrics?: Metrics;
  /** The request id source. */
  requestId?: () => string;
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
export function createApp(
  options: AppOptions,
): (request: AppRequest) => Promise<AppResponse> {
  const logger = options.logger ?? SILENT_LOGGER;
  const metrics = options.metrics ?? new Metrics();
  // When the server started, for the uptime.
  const startedAt = options.nowMs?.() ?? Date.now();

  /**
   * What the request is about, for the log.
   *
   * The command handler fills it in, and the log line picks it up, so the
   * line says what the request did and not only that it happened.
   */
  const requestContext: Record<string, unknown> = {};
  const limits = options.limits ?? DEFAULT_LIMITS;
  const limiter = new RateLimiter(limits);

  /** The client a request came from, for the rate limit. */
  function clientKey(request: AppRequest): string {
    // The limit is **per account**, not per address.
    //
    // A player behind a shared address - a household, a school, a
    // company network, a phone carrier's NAT - would otherwise be
    // punished for the other people behind that address, and a player
    // who changed address would lose their limit. The session token
    // identifies the *player*, so the player is the key.
    //
    // A request with no session is keyed by its address, because that is
    // all there is, and a request whose token does not resolve falls
    // back to the address too - it is not signed in, so it has no
    // account to count against.
    const token = request.headers['authorization']?.replace(/^Bearer\s+/i, '');
    if (token) {
      const session = options.sessions.resolve(token, options.now());
      if (session) return `player:${session.playerId}`;
    }
    const forwarded = request.headers['x-forwarded-for'];
    if (forwarded) return `address:${forwarded.split(',')[0]?.trim() ?? 'unknown'}`;
    return `address:${request.headers['x-real-ip'] ?? 'local'}`;
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
  async function handleLegacyCommand(request: AppRequest): Promise<AppResponse> {
    const playerId = identify(request);
    if (!playerId) return fail(401, 'unknown-player');

    const fields = fieldsOf(request);
    let response: AppResponse = fail(500, 'internal-error');

    // The transaction runs against a COPY of the save. The copy is committed
    // only when the whole batch has been processed, so a disconnect or a
    // timeout leaves the save exactly as it was.
    const stored = await options.store.transact(playerId, (world) => {
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
  /**
   * `POST /api/account` - create a player and sign them in.
   *
   * The upstream server had no accounts at all: `USERID` came in the
   * request body and anybody could be anybody (finding F10). So the
   * clone has to be able to **create** a player, and the credential has
   * to be **persisted** - a player who registers can log in after the
   * server restarts.
   *
   * The password is never stored: the credential is a salt and a hash.
   */
  async function createAccount(request: AppRequest): Promise<AppResponse> {
    const store = options.credentials;
    if (!store) {
      // Without somewhere to keep the credential, a player could not log
      // in after a restart, so the account is refused rather than made.
      return fail(503, 'no-credential-store');
    }

    let body: { playerId?: string; password?: string };
    try {
      body = JSON.parse(request.body) as { playerId?: string; password?: string };
    } catch {
      return fail(400, 'malformed-json');
    }
    const playerId = String(body.playerId ?? '').trim();
    const password = String(body.password ?? '');
    if (!playerId || !password) {
      return fail(400, 'missing-credentials');
    }
    if (playerId.length > 64) {
      return fail(400, 'bad-player-id');
    }

    const existing = await store.get(playerId);
    if (existing) {
      // The account exists. The password is not checked here: telling
      // somebody that a name is taken is not a way in, and it is what
      // the client needs to know.
      return fail(409, 'player-exists');
    }

    const credential = makeCredential(playerId, password);
    await store.put(credential);
    options.sessions.load(credential);

    // The player gets their **world** too. A player who has registered
    // but has no save is not a player: the world endpoint would answer
    // that there is no such player, which is true and useless.
    await options.store.add(playerId, initialWorld(playerId));

    const result = options.sessions.authenticate(playerId, password, options.now());
    if (!result.ok) {
      return fail(500, 'internal-error');
    }
    const session = result.session;
    return json(201, {
      token: session.token,
      playerId: session.playerId,
      issuedAt: session.issuedAt,
      expiresAt: session.expiresAt,
    });
  }

  /**
   * The server's health.
   *
   * It carries the **versions in use** - the server's, the content's and
   * the assets' - so that a report says what was running, and the
   * measurements the alerts watch.
   */
  function health() {
    const bundle = options.contentBundle as { buildId?: unknown };
    const report = healthReport({
      metrics,
      activeSessions: options.sessions.size,
      elapsedSeconds: (options.nowMs?.() ?? Date.now() - startedAt) / 1000,
      version: options.version ?? '0.0.0',
      contentBuildId:
        typeof bundle.buildId === 'string' ? bundle.buildId : 'unknown',
      assetBuildId: options.assetBuildId ?? null,
    });

    // The alerts are **sent**, and the sending is not allowed to hold up
    // the answer: a server that cannot reach the alerting system must
    // still serve its players.
    if (options.alertSender) {
      const sender = options.alertSender;
      void sender.send(report).catch(() => {
        // The sender records its own failures.
      });
    }

    return report;
  }

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

  /**
   * The answers already given, by request id.
   *
   * The native protocol carries an **idempotency key**: a retry of a
   * request that was lost in flight carries the same id, and the server
   * answers with the stored response instead of applying the commands
   * twice. A command that grants or spends depends on this.
   *
   * The answers are kept per player, and the oldest are dropped when the
   * list grows past its bound, so a client cannot fill the server's memory
   * by sending retries.
   */
  const answers = new Map<string, Map<string, unknown>>();

  /** How many recent answers are kept per player. */
  const MAX_REMEMBERED_ANSWERS = 256;

  /** The answer already given for a request id, if there is one. */
  function rememberedAnswer(playerId: string, id: string): unknown | undefined {
    return answers.get(playerId)?.get(id);
  }

  /** Remember an answer, and drop the oldest when the list grows. */
  function rememberAnswer(playerId: string, id: string, answer: unknown): void {
    let playerAnswers = answers.get(playerId);
    if (!playerAnswers) {
      playerAnswers = new Map();
      answers.set(playerId, playerAnswers);
    }
    playerAnswers.set(id, answer);
    while (playerAnswers.size > MAX_REMEMBERED_ANSWERS) {
      const oldest = playerAnswers.keys().next();
      if (oldest.done) break;
      playerAnswers.delete(oldest.value);
    }
  }

  /**
   * The native command endpoint.
   *
   * The envelope has four fields and no more: the protocol version, the
   * idempotency key, the session token and the commands. There is no
   * `USERID`, no client-declared resource vector and no client-claimed
   * combat outcome, because the server computes all of them.
   */
  async function handleNativeCommand(request: AppRequest): Promise<AppResponse> {
    const playerId = identify(request);
    if (!playerId) return fail(401, 'unknown-player');

    let body: unknown;
    try {
      body = JSON.parse(request.body) as unknown;
    } catch {
      return fail(400, 'malformed-json');
    }

    const validation = validateRequest(body, { role: 'player' });
    if (!validation.ok || !validation.request) {
      const id =
        typeof (body as { id?: unknown })?.id === 'string'
          ? (body as { id: string }).id
          : '';
      return json(400, {
        v: PROTOCOL_VERSION,
        id,
        ok: false,
        outcomes: [],
        errors: validation.errors,
      });
    }

    const native = validation.request;
    const remembered = rememberedAnswer(playerId, native.id);
    if (remembered !== undefined) {
      // The retry of a request that was lost in flight. The commands were
      // already applied, so the answer is replayed rather than recomputed.
      return json(200, remembered);
    }

    const outcomes: CommandOutcome[] = [];
    const applied: string[] = [];
    const refused: string[] = [];
    const commandStartedAt = options.nowMs?.() ?? Date.now();

    const stored = await options.store.transact(playerId, (world) => {
      let current = world;
      native.commands.forEach((command, index) => {
        // The command's name, its duration and whether it was applied:
        // the metrics and the log line both need them, and the request id
        // is what ties them to the client's action.
        const startedAt = options.nowMs?.() ?? Date.now();
        metrics.increment('commands_total', { name: command.name });
        // The cost is computed by the SERVER. The native envelope has no
        // room for a client-declared delta at all.
        const cost = computeCommandCost(options.content, command.name, command.args);
        const settled = applyCommandCost(current.resources, cost);
        if (!settled.ok) {
          outcomes.push({
            index,
            ok: false,
            error: {
              code: 'insufficient-resources',
              message: 'the player cannot afford the command',
              status: 402,
              commandIndex: index,
              command: command.name,
            },
          });
          return;
        }
        const outcome = options.applyCommand(
          { ...current, resources: settled.resources },
          { name: command.name, args: [...command.args] },
        );
        current = outcome.world;
        const durationMs = (options.nowMs?.() ?? Date.now()) - startedAt;
        metrics.observe('command_duration_ms', durationMs, { name: command.name });
        metrics.observe('simulation_tick_ms', durationMs, { name: command.name });
        if (outcome.applied) {
          applied.push(command.name);
          outcomes.push({ index, ok: true, result: { kind: 'none' } });
        } else {
          refused.push(command.name);
          outcomes.push({
            index,
            ok: false,
            error: {
              code: 'command-failed',
              message: outcome.refused ?? 'the command was refused',
              status: 409,
              commandIndex: index,
              command: command.name,
            },
          });
        }
      });
      return current;
    });

    if (!stored) return fail(401, 'unknown-player');

    const response = successResponse(native.id, outcomes);
    rememberAnswer(playerId, native.id, response);

    requestContext['player'] = playerId;
    requestContext['commands'] = native.commands.map((command) => command.name);
    requestContext['applied'] = applied;
    requestContext['refused'] = refused;
    requestContext['commandDurationMs'] =
      (options.nowMs?.() ?? Date.now()) - commandStartedAt;

    return json(200, response);
  }

  /**
   * The route.
   *
   * The work: the limits, the routing and the dialects. It is separate
   * from the wrapper below so that **every** response goes through the
   * observation, and not only the early returns.
   */
  async function route(request: AppRequest): Promise<AppResponse> {
    // --- the limits, before anything else -------------------------------
    if (request.body.length > limits.maxBodyBytes) {
      return fail(413, 'body-too-large');
    }
    const wait = limiter.check(clientKey(request), options.now());    if (wait > 0) {
      return fail(429, 'rate-limited', { 'retry-after': String(wait) });
    }

    const path = request.path.split('?')[0] ?? request.path;

    try {

      // The alliance and betting services use the same envelope as
      // `command.php`, so they are dispatched before the router.
      if (options.social) {
        const social = handleSocialRequest(request, options.social);
        if (social) return social;
      }

      // --- the health check ---------------------------------------------
      // The liveness check: the smallest possible answer, for a load
      // balancer or a monitor that only wants to know the process is up.
      if (path === '/health') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        return json(200, { status: 'ok', protocol: 1 });
      }

      // --- the native session endpoints ---------------------------------
      if (path === '/api/account') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        return await createAccount(request);
      }

      if (path === '/api/session') {
        if (request.method === 'POST') return createSession(request);
        if (request.method === 'DELETE') return deleteSession(request);
        return fail(405, 'method-not-allowed');
      }

      if (path === '/api/health') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        return json(200, health());
      }

      if (path === '/dashboard') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        return {
          status: 200,
          headers: { 'content-type': 'text/html; charset=utf-8' },
          body: dashboardHtml(health()),
        };
      }

      if (path === '/api/metrics') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        // The active sessions, as a gauge rather than a counter: it goes
        // up and down.
        metrics.gauge('active_sessions', options.sessions.size);
        return json(200, snapshot(metrics));
      }

      if (path === '/metrics') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        // The **scrape** format, so any time-series database can read the
        // metrics. The JSON is at /api/metrics; this is the export.
        metrics.gauge('active_sessions', options.sessions.size);
        return {
          status: 200,
          headers: { 'content-type': 'text/plain; version=0.0.4; charset=utf-8' },
          body: prometheusText(metrics),
        };
      }

      if (path === '/api/world') {
        if (request.method !== 'GET') return fail(405, 'method-not-allowed');
        // The player's world, as the client draws it. The positions are
        // the **server's**, and the client never decides them.
        const playerId = identify(request);
        if (!playerId) return fail(401, 'unknown-player');
        const own = await options.store.get(playerId);
        if (!own) return fail(401, 'unknown-player');
        return json(200, {
          maps: own.world.save.maps,
          privateState: own.world.save.privateState,
          resources: own.world.resources,
        });
      }

      if (path === '/api/command') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        return await handleNativeCommand(request);
      }

      // --- the legacy endpoints -----------------------------------------
      if (path === '/command.php') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        // `return await`, not `return`: a returned promise escapes the
        // try block, and the rejection would not be caught.
        return await handleLegacyCommand(request);
      }
      if (path === '/get_game_config.php') {
        if (request.method !== 'POST') return fail(405, 'method-not-allowed');
        // The content is the PATCHED bundle, and the darts schedule is
        // rotated to the current week - the upstream does the same on every
        // boot, and the client's board depends on it.
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
        const own = await options.store.get(playerId);
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
      // An unexpected failure is a 500, but the details stay here - and
      // they carry the **versions in use**, so a crash report says what
      // was running when it happened.
      const bundle = options.contentBundle as { buildId?: unknown };
      logger.error('unhandled error', {
        error: String(error),
        version: options.version ?? '0.0.0',
        contentBuildId:
          typeof bundle.buildId === 'string' ? bundle.buildId : 'unknown',
        assetBuildId: options.assetBuildId ?? null,
      });
      return fail(500, 'internal-error');
    }
  }

  /**
   * The wrapper.
   *
   * Every request gets a request id, and every response goes through the
   * observation: the log line, the metrics and the `x-request-id`
   * header.
   */
  return async function handle(request: AppRequest): Promise<AppResponse> {
    // The request id. The client's own is reused when it sends one, so
    // its correlation id survives into the log; otherwise one is made.
    // It travels back in the response, so a player can quote it.
    const requestId =
      request.headers[REQUEST_ID_HEADER] ?? (options.requestId ?? newRequestId)();
    const startedAt = options.nowMs?.() ?? Date.now();

    let response: AppResponse;
    try {
      response = await route(request);
    } catch (error) {
      // The route catches its own errors, so this is a failure in the
      // observation itself. It is still a 500 with a typed body.
      logger.error('unhandled error', { error: String(error), requestId });
      response = fail(500, 'internal-error');
    }

    const durationMs = (options.nowMs?.() ?? Date.now()) - startedAt;
    const path = request.path.split('?')[0] ?? request.path;

    metrics.observe('http_request_duration_ms', durationMs, { path, method: request.method });
    metrics.increment('http_requests_total', {
      path,
      method: request.method,
      status: String(response.status),
    });
    if (response.status >= 400) {
      metrics.increment('http_errors_total', { path, status: String(response.status) });
    }

    logger.log(response.status >= 500 ? 'error' : 'info', 'request', {
      requestId,
      path,
      method: request.method,
      status: response.status,
      durationMs,
      ...requestContext,
    });

    return {
      ...response,
      headers: { ...response.headers, [REQUEST_ID_HEADER]: requestId },
    };
  };
}
