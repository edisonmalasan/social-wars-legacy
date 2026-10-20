/**
 * The compatibility shim.
 *
 * This speaks the **original** `command.php` dialect, so the untouched
 * `Basesec_1.5.4.swf` can play against the new server with no client change.
 *
 * It exists to be *compatible*, not to be the server's native API. The native
 * API is versioned and typed; this is a legacy dialect with a legacy shape.
 *
 * ## What the shim does that the upstream server does not
 *
 * - **It verifies the HMAC.** The upstream server reads the 64 hex characters
 *   and throws the rest away; the digest is never checked.
 * - **It computes the resource costs.** The upstream applies the client's
 *   declared `res` vector verbatim.
 * - **It survives a replay.** The client re-sends the *same* packet when it
 *   does not get an answer (`processCommandsTimeout`), so a naive server
 *   applies the commands twice.
 * - **It tolerates a gap.** `first_number` is a **global command index**, not
 *   a batch counter, and the client can generate commands that are dropped
 *   (finding F6).
 *
 * ## The response shape
 *
 * The client expects `{"result": "success"}` with a 200. The upstream sends
 * that, unframed, and the client accepts a raw JSON body. The shim can send
 * either, and defaults to unframed, exactly like the upstream.
 */
import {
  ACCEPTED_KEYS,
  SERVER_KEYS,
  frameResponse,
  parseFrame,
  signPayload,
  verifyFrameAny,
  type ServerKey,
} from '@swl/protocol';

import { applyCommandCost, computeCommandCost, type CostContent, type Resources } from '@swl/rules';
import { LegacyIdentityBridge } from './session.ts';

/** A request, as the shim sees it. */
export interface ShimRequest {
  /** The path, e.g. `/command.php`. */
  path: string;
  /** The form fields. */
  fields: Record<string, string | undefined>;
}

/** A response. */
export interface ShimResponse {
  status: number;
  contentType: string;
  body: string;
}

/** The mutable state a command batch acts on. */
export interface ShimWorld {
  /** The player's save document. */
  save: {
    playerInfo: Record<string, unknown>;
    maps: Record<string, unknown>[];
    privateState: Record<string, unknown>;
  };
  /** The player's resources, by resource key. */
  resources: Resources;
  /**
   * The next global command index the server expects.
   *
   * The client sends `first_number`, the index of the FIRST command in the
   * batch, so a batch that continues the last one starts exactly at this
   * value.
   */
  nextCommandNumber: number;
}

/** One command from the batch. */
export interface ShimCommand {
  /** The command name. */
  name: string;
  /** The command's arguments. */
  args: unknown[];
  /** The client's declared resource delta. **Never used.** */
  declaredResources: number[];
}

/** The result of applying one command. */
export interface CommandOutcome {
  /** Whether the command was applied. */
  applied: boolean;
  /** Why it was refused, if it was. */
  refused?: string;
  /** The world after the command. */
  world: ShimWorld;
}

/** Applies one command's semantics. The shim owns the cost. */
export type CommandApplier = (
  world: ShimWorld,
  command: { name: string; args: unknown[] },
) => CommandOutcome;

/** Everything the shim needs. */
export interface ShimContext {
  /** The player's world. */
  world: ShimWorld;
  /**
   * Resolve the world of an identified player.
   *
   * When this is supplied, the shim uses **this** and never `world`: the
   * player's identity decides which save is touched, not the request body.
   * That is the whole point — the upstream server takes the `USERID` from
   * the body and believes it, so any player can act on any other player's
   * save.
   */
  worldFor?: (playerId: string) => ShimWorld;
  /** The content, for the server-computed costs. */
  content: CostContent;
  /** The current time, in seconds. */
  now: number;
  /** The legacy identity bridge. */
  identity: LegacyIdentityBridge;
  /**
   * Resolve a session token to a player.
   *
   * This is the **native** path, and it is preferred: a session token is
   * revocable and identifies exactly one player, where a legacy `USERID` is
   * a body value that only means something because the server bound it.
   */
  resolveToken?: (token: string) => string | null;
  /** Applies one command's semantics. */
  applyCommand: CommandApplier;
  /** Whether responses are framed with the HMAC. The upstream does not. */
  frameResponses?: boolean;
  /**
   * The deadline for the batch, in milliseconds since the epoch.
   *
   * The batch is checked between commands, so a batch that runs long is
   * stopped rather than allowed to hold the server. A command that has
   * already started is not interrupted — the check happens between them,
   * because a half-applied command is worse than a slow one.
   */
  deadline?: number;
  /**
   * The clock, in milliseconds since the epoch.
   *
   * `now` is the request's timestamp in **seconds**, which is fixed for the
   * whole request; the deadline needs a clock that *moves*, or it would
   * never fire.
   */
  clock?: () => number;
  /**
   * The player, when the caller has already identified them.
   *
   * The HTTP layer has to identify the player *before* it can load their
   * save, so it resolves the identity itself and hands the answer down.
   * This is the seam for that: it is never taken from the request body.
   */
  identifiedPlayerId?: string;
}

/** How a player was identified. */
export type IdentitySource = 'session-token' | 'legacy-userid';

/** The outcome of identifying the player. */
export type IdentityResult =
  | { ok: true; playerId: string; via: IdentitySource }
  | { ok: false; reason: 'unauthenticated' | 'invalid-session' };

/**
 * Identify the player behind a request.
 *
 * The **session token** is tried first, because it is the native mechanism
 * and it identifies exactly one player. The legacy `USERID` is the
 * fallback, and it only resolves when the bridge has been enabled
 * *and* the server has already bound that value to a player — the bridge
 * can never invent one.
 *
 * Nothing else identifies a player. In particular, the body cannot.
 */
export function resolveIdentity(
  request: ShimRequest,
  context: ShimContext,
): IdentityResult {
  // The caller may have identified the player already. The HTTP layer has
  // to, because it needs the identity to load the right save.
  if (context.identifiedPlayerId) {
    return { ok: true, playerId: context.identifiedPlayerId, via: 'session-token' };
  }
  const token = request.fields['token'] ?? request.fields['session_token'];
  if (token && context.resolveToken) {
    const playerId = context.resolveToken(token);
    if (playerId) return { ok: true, playerId, via: 'session-token' };
    return { ok: false, reason: 'invalid-session' };
  }
  const legacy = context.identity.resolve(request.fields['USERID']);
  if (legacy) return { ok: true, playerId: legacy, via: 'legacy-userid' };
  return { ok: false, reason: 'unauthenticated' };
}

/**
 * The world a request acts on.
 *
 * With a per-player resolver, the identity chooses the save. Without one,
 * the context's single world is used, which is only correct when the
 * caller has already established who the player is.
 */
export function worldForPlayer(playerId: string, context: ShimContext): ShimWorld {
  return context.worldFor ? context.worldFor(playerId) : context.world;
}

/** A JSON response. */
function json(status: number, body: unknown, context?: ShimContext): ShimResponse {
  const payload = JSON.stringify(body);
  const framed =
    context?.frameResponses === true
      ? frameResponse(payload, ACCEPTED_KEYS[0] ?? SERVER_KEYS.current)
      : payload;
  return { status, contentType: 'application/json', body: framed };
}

/** The outcome of a whole command batch. */
export interface BatchOutcome {
  /** The response the client gets. */
  response: ShimResponse;
  /** The world after the batch. */
  world: ShimWorld;
  /** Whether the batch was a replay of one already applied. */
  replay: boolean;
  /** Whether there was a gap in the command index. */
  gap: boolean;
  /** The commands that were refused, with the reason. */
  refused: { name: string; reason: string }[];
}

/**
 * Apply a command batch.
 *
 * The batch is the parsed `command.php` payload: `first_number`, `commands`, `tries`.
 */
export function applyBatch(
  payload: {
    first_number?: number;
    commands?: unknown[];
    tries?: number;
  },
  context: ShimContext,
): BatchOutcome {
  let world = context.world;
  const refused: { name: string; reason: string }[] = [];

  const raw = payload.commands ?? [];
  const commands: ShimCommand[] = [];
  for (const entry of raw) {
    if (!Array.isArray(entry)) continue;
    // The tuple is [map_id, cmd, args[], res[8]] (finding F2).
    const name = typeof entry[1] === 'string' ? entry[1] : '';
    const args = Array.isArray(entry[2]) ? (entry[2] as unknown[]) : [];
    const declared = Array.isArray(entry[3]) ? (entry[3] as number[]) : [];
    commands.push({ name, args, declaredResources: declared });
  }

  const first = Number(payload.first_number ?? world.nextCommandNumber);
  const end = first + commands.length;

  // A REPLAY: the client re-sends the same packet when it gets no answer.
  // The commands were already applied, so they must not be applied again.
  if (end <= world.nextCommandNumber) {
    return {
      response: json(200, { result: 'success' }, context),
      world,
      replay: true,
      gap: false,
      refused,
    };
  }

  // A GAP: the client generated commands that were dropped, so the index jumps
  // ahead. The shim tolerates it (finding F6) and resynchronises.
  const gap = first > world.nextCommandNumber;

  for (const command of commands) {
    // The deadline is checked BETWEEN commands. A command that has already
    // started is not interrupted, because a half-applied command is worse
    // than a slow one.
    if (
      context.deadline !== undefined &&
      context.clock !== undefined &&
      context.clock() > context.deadline
    ) {
      refused.push({ name: command.name, reason: 'deadline-exceeded' });
      break;
    }

    // flash_debug does not exist in the new server (non-negotiable 6).
    if (command.name === 'flash_debug') {
      refused.push({ name: command.name, reason: 'unknown-command' });
      continue;
    }

    // The cost is computed by the SERVER. The client's declared delta is
    // never read (finding F3).
    const cost = computeCommandCost(context.content, command.name, command.args);
    const settled = applyCommandCost(world.resources, cost);
    if (!settled.ok) {
      refused.push({
        name: command.name,
        reason: settled.reason ?? 'refused',
      });
      continue;
    }

    const outcome = context.applyCommand(
      { ...world, resources: settled.resources },
      { name: command.name, args: command.args },
    );
    world = outcome.world;
    if (!outcome.applied) {
      refused.push({
        name: command.name,
        reason: outcome.refused ?? 'refused',
      });
    }
  }

  world = { ...world, nextCommandNumber: end };

  return {
    response: json(200, { result: 'success' }, context),
    world,
    replay: false,
    gap,
    refused,
  };
}

/**
 * Handle `command.php`.
 *
 * The framing is verified against **both** server keys, because unmodified
 * clients of both eras exist.
 *
 * The player is identified **before** anything is applied, and the identity
 * chooses whose save is touched. The body cannot.
 */
export function handleCommandPhp(
  request: ShimRequest,
  context: ShimContext,
): ShimResponse {
  // The envelope is checked first: a malformed or unsigned body is malformed
  // whoever sent it, and refusing it before the identity is resolved keeps
  // the two failures distinguishable.
  const data = request.fields['data'];
  if (!data) {
    return json(400, { result: 'error', error: 'missing-data' });
  }

  const parsed = parseFrame(data);
  if (!parsed.framed) {
    return json(400, { result: 'error', error: 'malformed-framing' });
  }

  const key: ServerKey | null = verifyFrameAny(data, ACCEPTED_KEYS);
  if (key === null) {
    return json(403, { result: 'error', error: 'bad-signature' });
  }

  // Then the actor. The identity decides whose save is touched; the body
  // cannot.
  const identity = resolveIdentity(request, context);
  if (!identity.ok) {
    return json(401, { result: 'error', error: identity.reason });
  }

  let payload: {
    first_number?: number;
    commands?: unknown[];
    tries?: number;
  };
  try {
    payload = JSON.parse(parsed.payload) as typeof payload;
  } catch {
    return json(400, { result: 'error', error: 'malformed-payload' });
  }

  // The identity chooses the world. `context.world` is only a fallback for
  // a caller that has already established who the player is.
  const world = worldForPlayer(identity.playerId, context);
  const outcome = applyBatch(payload, { ...context, world });
  // The world the caller must persist.
  context.world = outcome.world;
  return outcome.response;
}

/**
 * Handle `get_game_config.php`.
 *
 * The content is the **patched** bundle — the base config plus the five
 * JSON-Patch deltas — and the darts schedule is rotated to the current week,
 * because the upstream rewrites the darts dates on every boot.
 */
export function handleGetGameConfig(
  request: ShimRequest,
  context: { content: Record<string, unknown>; now: number },
): ShimResponse {
  // The client asks for a language; the shipped content is English only.
  void request;
  return json(200, context.content);
}

/**
 * Handle `get_player_info.php`.
 *
 * The upstream has four flavours, chosen by the `user` field:
 *
 * - **absent** — the player's own info
 * - **`100000030` or `100000031`** — a neighbour (General Mike)
 * - **starting with `100000`** — a quest map
 * - **anything else** — a static neighbour
 */
export function handleGetPlayerInfo(
  request: ShimRequest,
  context: {
    own: Record<string, unknown>;
    neighbours: Record<string, Record<string, unknown>>;
    now: number;
  },
): ShimResponse {
  const user = request.fields['user'];
  const mapNumber = Number(request.fields['map'] ?? 0);

  if (user === undefined || user === null || user === '') {
    return json(200, {
      result: 'ok',
      processed_errors: 0,
      timestamp: context.now,
      playerInfo: context.own['playerInfo'],
      map: context.own['map'],
      privateState: context.own['privateState'],
      neighbors: context.own['neighbors'] ?? [],
    });
  }

  const neighbour = context.neighbours[user];
  if (!neighbour) {
    // The upstream answers an empty body when the neighbour is unknown.
    return { status: 200, contentType: 'application/json', body: '' };
  }

  const maps = (neighbour['maps'] as Record<string, unknown>[] | undefined) ?? [];
  const map = maps[mapNumber] ?? maps[0] ?? {};

  return json(200, {
    result: 'ok',
    processed_errors: 0,
    timestamp: context.now,
    playerInfo: neighbour['playerInfo'],
    map,
    privateState: neighbour['privateState'],
  });
}

/** The digest of a payload, for the shim's own logging. */
export function digestOf(payload: string): string {
  return signPayload(payload, ACCEPTED_KEYS[0] ?? SERVER_KEYS.current);
}
