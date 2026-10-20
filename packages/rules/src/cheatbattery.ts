/**
 * The cheat battery.
 *
 * The original game has no server authority: the client declares the resource
 * delta for every command, declares combat outcomes, declares goal progress,
 * and the server believes it. Roadmap Group F1 requires a battery of eleven
 * attacks that the clone either rejects or that have no effect.
 *
 * This module **is** that battery. Every entry is an attempted cheat, not a
 * description of one: the attack runs against the real authority layer —
 * `packages/protocol/src/commandphp.ts` and `packages/rules/src/commandcost.ts`,
 * `authority.ts`, `goals.ts`, `quest.ts`, `bonuses.ts`, `economy.ts` — and the
 * verification asserts that the cheat changed nothing.
 *
 * ## What is real and what is wiring
 *
 * Every function here that *decides* anything is imported from those modules.
 * The functions here that *wire* them together (the request path, the grant
 * paths) hold no authority of their own, and each says so. A battery that
 * tested a copy of the rules would prove nothing; a battery that tests these
 * modules proves the shipped authority layer defends.
 *
 * ## The structural attacks
 *
 * Two of the eleven are structural rather than behavioural, and are reported as
 * such rather than dressed up as behaviour:
 *
 * - **wrong HMAC** and **malformed framing** are refused before any state is
 *   touched: `verifyFrameAny` rejects the request, so the command path never
 *   runs. The battery proves that by showing the state is untouched *and* that
 *   the correctly framed twin of the very same request *is* accepted.
 * - **another player's `USERID`** is caught by the session model: the request
 *   carries a session token, and the player is resolved from the token, never
 *   from the body. The **server** package already models that
 *   (`packages/server/src/session.ts`, `SessionStore` and the off-by-default
 *   `LegacyIdentityBridge`) — but the shim's command path does not consult
 *   the bridge yet, so the request→player binding is still the caller's job.
 *   What this attack pins is the *contract*: the body and the query string
 *   may name any `USERID` they like, and the wallet that moves must be the
 *   session's, not the body's.
 *
 * ## What this battery does not cover
 *
 * Stated plainly, because a battery that implies more coverage than it has is
 * worse than none:
 *
 * - **The server package is not reachable from here.** `@swl/server` depends
 *   on `@swl/rules`, so the rules package cannot depend on it back. The
 *   battery therefore aims at the rules and protocol layers, and
 *   `cheatbattery.test.ts` cross-checks the wire-level attacks against the
 *   shipped shim through a test-only relative import. A grant implemented in
 *   the shim's `applyCommand` seam — the daily bonus, the goal reward, the
 *   quest reward, the assault loot, the collection — is *not* covered by the
 *   rules-layer battery; it must be implemented with the grant paths exported
 *   here.
 * - **The collect timer is not modelled.** `economy.ts` implements the
 *   over-capacity guard ("HACK DETECTED"), which is the half of over-collection
 *   the client checks. The other half — collecting again before the
 *   production cycle has elapsed — needs a timer the rules package does not
 *   have yet; the server must own it.
 * - **The weekly bonus, the alliance bonus and premium expiry have no
 *   once-only guard.** `bonuses.ts` implements the cycles, and the daily
 *   bonus's readiness check is tested here, but the cross-cycle once-only
 *   guard is roadmap F1's third bullet and is still open.
 *
 * ## Determinism
 *
 * No wall clock, no randomness, no I/O. Time is a fixture, the battle seed is
 * a fixture, and the content bundle is injected by the caller.
 */

import assert from 'node:assert/strict';

import {
  ACCEPTED_KEYS,
  RESOURCE_ORDER,
  SERVER_KEYS,
  framePayload,
  parseFrame,
  readResource,
  verifyFrame,
  verifyFrameAny,
  type CommandName,
  type CommandPayload,
  type ResourceName,
  type ResourceVector,
  type ServerKey,
} from '@swl/protocol';

import {
  PRICED_COMMANDS,
  computeCommandCost,
  settleCommand,
  type CostContent,
  type Resources,
} from './commandcost.ts';

import {
  battleSeed,
  checkClientClaim,
  resolveServerCombat,
  type Combatant,
} from './authority.ts';

import {
  applyGoalEvent,
  awardGoal,
  createGoalState,
  type GoalReward,
  type GoalRuntimeState,
  type GoalWorld,
} from './goals.ts';

import {
  awardQuest,
  emptyQuestProgress,
  finishQuest,
  getQuestSpec,
  isQuestVictory,
  nearDeathQuestElement,
  prepareQuest,
  questRewards,
  startQuest,
  type QuestProgress,
  type QuestState,
} from './quest.ts';

import {
  dailyBonusReadiness,
  dailyBonusReward,
  nextDailyBonusDay,
  type DailyBonusRules,
} from './bonuses.ts';

import { collect, type CollectPeriods, type Producer } from './economy.ts';

/* ------------------------------------------------------------------------- *
 * The wire model
 * ------------------------------------------------------------------------- */

/**
 * The rules package's short resource keys, in the protocol's wire order.
 *
 * The 8-slot order is load-bearing (non-negotiable 4): `[energy, xp, gold,
 * wood, oil, steel, cash, mana]`, verified live against a real client session
 * (`re/docs/06-LIVE-SESSION-PROTOCOL.md`).
 */
const WIRE_TO_RULE_KEY: Readonly<Record<ResourceName, string>> = Object.freeze({
  energy: 'e',
  xp: 'x',
  gold: 'g',
  wood: 'w',
  oil: 'o',
  steel: 's',
  cash: 'c',
  mana: 'm',
});

/** Build a resource vector. The slot order is load-bearing — see above. */
export function res(
  energy = 0,
  xp = 0,
  gold = 0,
  wood = 0,
  oil = 0,
  steel = 0,
  cash = 0,
  mana = 0,
): ResourceVector {
  return [energy, xp, gold, wood, oil, steel, cash, mana];
}

/** One command of a `command.php` batch: `[mapId, name, args, res]`. */
export type WireCommand = readonly [
  mapId: number,
  name: CommandName,
  args: readonly unknown[],
  res: ResourceVector,
];

/**
 * The JSON payload of a `command.php` batch.
 *
 * The client fields are the ones the original client sends
 * (`packages/protocol/src/index.ts`, `CommandPayload`). `USERID` is *not* one
 * of them: upstream sends it in the **query string**
 * (`re/evidence/live/command-payloads.txt`). It is modelled here as an
 * optional extra field because that is where a cheat would put it.
 */
export interface CheatBatch extends Omit<CommandPayload, 'commands'> {
  readonly commands: readonly WireCommand[];
  /** A `USERID` smuggled into the body. The server must never read it. */
  readonly USERID?: string;
}

/** A `command.php` HTTP request, as the original client sends it. */
export interface WireRequest {
  /** The query string, parsed. Upstream carries `USERID` and `user_key` here. */
  readonly query: Readonly<Record<string, string>>;
  /** The request body: `client_id=<n>&data=<framed json>`. */
  readonly body: string;
}

/** Options for building a request as a cheating client. */
export interface RequestOptions {
  /** The key to sign the payload with. Defaults to the live-verified key. */
  readonly key?: string;
  /** The session token the request carries. */
  readonly token?: string;
  /** The `USERID` to put in the query string, exactly as upstream does. */
  readonly userId?: string;
  /** A raw, unframed `data` value — for the malformed-framing attack. */
  readonly data?: string;
  /** The `client_id` the body carries. */
  readonly clientId?: string;
}

/** Parse a `application/x-www-form-urlencoded` body. */
export function parseFormBody(body: string): Readonly<Record<string, string>> {
  const out: Record<string, string> = {};
  for (const pair of body.split('&')) {
    if (pair === '') continue;
    const index = pair.indexOf('=');
    const rawKey = index === -1 ? pair : pair.slice(0, index);
    const rawValue = index === -1 ? '' : pair.slice(index + 1);
    try {
      out[decodeURIComponent(rawKey)] = decodeURIComponent(rawValue.replace(/\+/g, ' '));
    } catch {
      // A body that is not valid percent-encoding simply has no fields.
    }
  }
  return out;
}

/**
 * Build a `command.php` request the way the client does.
 *
 * This is the *attacker's* tool: it signs the payload with whatever key it
 * likes, puts whatever it likes in the query string, and can emit an
 * unframed body when it wants to try the `skiphash12341` bypass.
 */
export function buildRequest(batch: CheatBatch, options: RequestOptions = {}): WireRequest {
  const key = options.key ?? SERVER_KEYS.current;
  const data = options.data ?? framePayload(JSON.stringify(batch), key);
  const clientId = options.clientId ?? '343579499';
  const body = `client_id=${encodeURIComponent(clientId)}&data=${encodeURIComponent(data)}`;
  const query: Record<string, string> = { language: 'en' };
  if (options.token !== undefined) query['token'] = options.token;
  if (options.userId !== undefined) query['USERID'] = options.userId;
  return { query, body };
}

/* ------------------------------------------------------------------------- *
 * The server's request path
 *
 * Everything below is *wiring*. It decides nothing: the framing decision is
 * `verifyFrameAny`, the cost decision is `settleCommand`. It exists so the
 * battery can aim a real request at the real modules.
 * ------------------------------------------------------------------------- */

/** The verdict of the framing gate. */
export interface FrameGate {
  /** Whether the request may proceed. */
  readonly accepted: boolean;
  /** The key that matched, when one did. */
  readonly key: ServerKey | null;
  /** The decoded payload, when the request was framed correctly. */
  readonly payload: CheatBatch | null;
  /** Why the request was refused. */
  readonly reason?: string;
}

/**
 * The framing gate.
 *
 * `verifyFrameAny` is the real check (`packages/protocol/src/commandphp.ts`).
 * A request whose body is not `<64 hex>;<json>` — or whose digest does not
 * match either accepted key — is refused here, before any state is read.
 */
export function serverAcceptFrame(data: string, keys: readonly ServerKey[] = ACCEPTED_KEYS): FrameGate {
  const key = verifyFrameAny(data, keys);
  if (key === null) {
    return { accepted: false, key: null, payload: null, reason: 'bad-signature' };
  }
  const parsed = parseFrame(data);
  let decoded: unknown;
  try {
    decoded = JSON.parse(parsed.payload);
  } catch {
    return { accepted: false, key, payload: null, reason: 'bad-payload' };
  }
  // A body that is JSON but not a command batch is still malformed.
  if (typeof decoded !== 'object' || decoded === null || !Array.isArray((decoded as CheatBatch).commands)) {
    return { accepted: false, key, payload: null, reason: 'bad-payload' };
  }
  return { accepted: true, key, payload: decoded as CheatBatch };
}

/** The result of running a request through the server's command path. */
export interface ServerCommandResult {
  /** Whether the request was applied. */
  readonly accepted: boolean;
  /** Why it was refused, when it was. */
  readonly reason?: string;
  /** The player the session resolved to. */
  readonly playerId?: string;
  /** The wallet after the request. */
  readonly resources: Resources;
  /** The commands that ran. */
  readonly executed: readonly string[];
}

/**
 * Apply a list of commands to a wallet.
 *
 * The fourth slot of every command tuple — the client's declared resource
 * delta — is **not read**. There is no parameter for it here and none in
 * `settleCommand`, so there is nowhere to put it. This is wiring, not
 * authority: the cost itself comes from `settleCommand`.
 */
export function serverApplyCommands(
  content: CostContent,
  wallet: Resources,
  commands: readonly WireCommand[],
): { readonly accepted: boolean; readonly reason?: string; readonly resources: Resources } {
  let resources: Resources = { ...wallet };
  for (const command of commands) {
    const settled = settleCommand(content, resources, command[1], command[2]);
    if (!settled.ok) {
      return { accepted: false, reason: settled.reason ?? 'refused', resources };
    }
    resources = settled.resources;
  }
  return { accepted: true, resources };
}

/** The wallet of a resolved player id. */
export function walletOf(ctx: CheatContext, playerId: string): Resources {
  return playerId === ctx.victimId ? ctx.victim : ctx.attacker;
}

/**
 * The server's command path.
 *
 * The player comes from the **session token**; the `USERID` in the query
 * string (as upstream sends it) and the `USERID` in the body (as a cheat would
 * send it) are never read.
 */
export function serverCommandPath(ctx: CheatContext, request: WireRequest): ServerCommandResult {
  const form = parseFormBody(request.body);
  const data = form['data'] ?? '';
  const gate = serverAcceptFrame(data);
  if (!gate.accepted || gate.payload === null) {
    // The request never reached a wallet: the framing gate refused it first.
    return {
      accepted: false,
      reason: gate.reason ?? 'refused',
      resources: {},
      executed: [],
    };
  }
  const playerId = resolveSessionPlayer(ctx, request.query['token']);
  if (playerId === undefined) {
    return {
      accepted: false,
      reason: 'no-session',
      resources: {},
      executed: [],
    };
  }
  const applied = serverApplyCommands(ctx.content, walletOf(ctx, playerId), gate.payload.commands);
  return {
    accepted: applied.accepted,
    reason: applied.reason,
    playerId,
    resources: applied.resources,
    executed: gate.payload.commands.map((command) => command[1]),
  };
}

/**
 * Resolve a session token to a player id.
 *
 * The **server** package models the real thing
 * (`packages/server/src/session.ts`): a `SessionStore` that issues revocable
 * tokens, and a `LegacyIdentityBridge` that maps the original client's
 * `USERID` onto a player and is **off by default**. The rules package cannot
 * depend on the server package — the dependency runs the other way — so this
 * is the contract the shim's command path has to honour: the token is the
 * only input, and the body may not change it.
 */
export function resolveSessionPlayer(ctx: CheatContext, token: string | undefined): string | undefined {
  if (token === undefined) return undefined;
  if (token === ctx.attackerToken) return ctx.attackerId;
  if (token === ctx.victimToken) return ctx.victimId;
  return undefined;
}

/**
 * The upstream semantics of the declared delta.
 *
 * The upstream server applies the client's `res` vector verbatim
 * (`upstream/socialwarriors/engine.py:251-268`), which is why a cheat works
 * there. This exists **only** so the battery can say what the attack *would*
 * have achieved, and show that it did not.
 */
export function upstreamApplyResources(wallet: Resources, delta: ResourceVector): Resources {
  const out: Resources = { ...wallet };
  for (const name of RESOURCE_ORDER) {
    const amount = readResource(delta, name);
    if (amount === 0) continue;
    const key = WIRE_TO_RULE_KEY[name];
    out[key] = Math.max((out[key] ?? 0) + amount, 0);
  }
  return out;
}

/* ------------------------------------------------------------------------- *
 * The grant paths
 *
 * Also wiring: each one delegates its decision to the real module and adds no
 * rule of its own.
 * ------------------------------------------------------------------------- */

/** The player's daily-bonus state. */
export interface BonusState {
  /** When the bonus was last claimed, in seconds. 0 means never. */
  readonly lastBonusAtSeconds: number;
  /** The day of the cycle the player's streak is on, 1-based. */
  readonly dayIndex: number;
}

/** The result of a daily-bonus claim. */
export interface DailyBonusClaim {
  readonly ok: boolean;
  readonly reason?: string;
  readonly reward: { readonly gold: number; readonly heroItemId: number | null } | null;
  readonly state: BonusState;
}

/**
 * The server's daily-bonus grant path.
 *
 * The upstream server has **no** readiness check at all: `win_daily_bonus`
 * stamps `timestampLastBonus = now` and credits the client's declared delta
 * (`upstream/socialwarriors/command.py:444-463`), so it can be replayed all
 * day (`re/docs/03-commands-quests-economy.md` §11, item 11). The readiness
 * decision here is `dailyBonusReadiness`, the real module.
 */
export function claimDailyBonus(ctx: CheatContext, state: BonusState): DailyBonusClaim {
  const readiness = dailyBonusReadiness(state.lastBonusAtSeconds, ctx.nowSeconds, ctx.tzOffsetHours);
  if (!readiness.ready) {
    return { ok: false, reason: 'not-ready', reward: null, state };
  }
  const dayIndex = readiness.reset ? 1 : state.dayIndex;
  const reward = dailyBonusReward(ctx.bonusRules, dayIndex);
  return {
    ok: true,
    reward,
    state: {
      lastBonusAtSeconds: ctx.nowSeconds,
      dayIndex: nextDailyBonusDay(ctx.bonusRules, dayIndex),
    },
  };
}

/** Add a goal's reward to a wallet. */
export function applyGoalReward(wallet: Resources, reward: GoalReward): Resources {
  return { ...wallet, [reward.resource]: (wallet[reward.resource] ?? 0) + reward.amount };
}

/* ------------------------------------------------------------------------- *
 * The fixtures
 * ------------------------------------------------------------------------- */

/** The `buy` arguments of the live capture: a Worker I at tile (52, 42). */
export const BUY_WORKER_ARGS: readonly unknown[] = [41, 1001, 52, 42, 1, 0, 0, 'u'];

/** The offer pack the free-pack attack targets: the "starter pack". */
export const STARTER_PACK_ID = 1;

/** The quest the forged-`win` attack targets: "DEFEAT THE ENEMY". */
export const FORGED_WIN_QUEST_ID = '100000001';

/** Everything the attacks are aimed at. */
export interface CheatContext {
  /** The content bundle, as the cost table reads it. */
  readonly content: CostContent;
  /** The attacker's wallet. */
  readonly attacker: Resources;
  /** The victim's wallet — the one a forged `USERID` would try to touch. */
  readonly victim: Resources;
  /** The attacker's player id. */
  readonly attackerId: string;
  /** The victim's player id. */
  readonly victimId: string;
  /** The attacker's session token. */
  readonly attackerToken: string;
  /** The victim's session token. */
  readonly victimToken: string;
  /** The upstream-style `USERID` of the victim. */
  readonly victimUserId: string;
  /** The id of the assault the forged-`end_attack` attack claims to have won. */
  readonly battleId: string;
  /** The attacker, as the combat resolver sees it. */
  readonly attackerCombatant: Combatant;
  /** The defender, as the combat resolver sees it. */
  readonly defenderCombatant: Combatant;
  /** The damage the forged `end_attack` claims. */
  readonly claimedDamage: number;
  /** The goal state the server holds. */
  readonly goals: GoalRuntimeState;
  /** What the server knows about the player's world. */
  readonly goalWorld: GoalWorld;
  /** The quest the server is running. */
  readonly quest: QuestState;
  /** The player's quest progress. */
  readonly questProgress: QuestProgress;
  /** The XP the player needs — it scales one of the quest's reward rows. */
  readonly expRequired: number;
  /** The daily-bonus table. */
  readonly bonusRules: DailyBonusRules;
  /** The player's daily-bonus state. */
  readonly bonusState: BonusState;
  /** "Now", in seconds. A fixture: the battery never reads the clock. */
  readonly nowSeconds: number;
  /** The player's time-zone offset, in hours. */
  readonly tzOffsetHours: number;
  /** The four collect periods. */
  readonly collectPeriods: CollectPeriods;
  /** A producer holding more units than it can hold — the "HACK DETECTED" case. */
  readonly overfullProducer: Producer;
  /** A producer in a legal state. */
  readonly legalProducer: Producer;
}

function soldier(over: Partial<Combatant> = {}): Combatant {
  return {
    id: 'u1',
    itemId: 1007,
    attack: 8,
    defense: 1,
    life: 50,
    maxLife: 50,
    health: 50,
    attack_range: 5,
    attack_interval: 35,
    phase: 0,
    properties: {},
    best_against: null,
    best_against_mult: 1,
    x: 0,
    y: 0,
    ...over,
  };
}

/**
 * Build the fixtures.
 *
 * Every value is fixed, so the battery is deterministic and the tests can
 * assert exact numbers.
 */
export function createCheatContext(content: CostContent): CheatContext {
  const attacker: Resources = { g: 1000, x: 0, w: 500, o: 500, s: 500, c: 0, e: 100, m: 0 };
  const victim: Resources = { g: 5000, x: 0, w: 5000, o: 5000, s: 5000, c: 500, e: 100, m: 0 };
  const quest = startQuest(prepareQuest(FORGED_WIN_QUEST_ID, { army: [{ unitId: 1007, count: 10 }] }));
  return {
    content,
    attacker,
    victim,
    attackerId: 'player-attacker',
    victimId: 'player-victim',
    attackerToken: 'token-attacker',
    victimToken: 'token-victim',
    victimUserId: 'e53386db-e42c-43c4-8c5c-9ace9c81ad91',
    battleId: 'assault-0001',
    attackerCombatant: soldier({ id: 'a1', attack: 40 }),
    defenderCombatant: soldier({
      id: 'd1',
      attack: 0,
      health: 5000,
      maxLife: 5000,
      life: 5000,
    }),
    claimedDamage: 999999,
    goals: createGoalState(),
    goalWorld: { itemProperties: new Map([[1, ['building']]]) },
    quest,
    questProgress: emptyQuestProgress(),
    expRequired: 100,
    bonusRules: { goldRewards: [100, 250, 500, 1000, 0], heroItemId: 1017 },
    bonusState: { lastBonusAtSeconds: 0, dayIndex: 1 },
    // 2026-10-20T00:00:00Z, as a fixed fixture.
    nowSeconds: 1792434747,
    tzOffsetHours: 0,
    collectPeriods: { minutes: [60, 180, 360, 720], multiplier: [1, 3, 6, 12] },
    overfullProducer: { collect: 100, unitCapacity: 5, unitsInside: 50 },
    legalProducer: { collect: 100, unitCapacity: 5, unitsInside: 1 },
  };
}

/* ------------------------------------------------------------------------- *
 * The battery
 * ------------------------------------------------------------------------- */

/** The eleven attacks of roadmap Group F1. */
export type CheatId =
  | 'inflated-res'
  | 'flash-debug'
  | 'replayed-daily-bonus'
  | 'self-completed-goal'
  | 'forged-end-attack'
  | 'free-offer-pack'
  | 'wrong-hmac'
  | 'foreign-userid'
  | 'malformed-framing'
  | 'forged-win'
  | 'over-collection';

/**
 * How an attack is stopped.
 *
 * - `behavioural` — a rule of the authority layer refuses it.
 * - `structural` — the shape of the protocol refuses it, before any rule runs.
 */
export type CheatKind = 'behavioural' | 'structural';

/** What an attempt achieved. */
export interface CheatOutcome {
  /** True when the cheat got what it wanted. */
  readonly succeeded: boolean;
  /** What the server did with the attempt, in one line. */
  readonly note: string;
  /** Extra detail for the report. */
  readonly detail?: string;
}

/** One attack of the battery. */
export interface CheatAttack {
  /** The attack's id. */
  readonly id: CheatId;
  /** A short name. */
  readonly name: string;
  /** One line: what the attack does. */
  readonly description: string;
  /** Whether a rule or the protocol shape stops it. */
  readonly kind: CheatKind;
  /** Run the cheat. */
  readonly attempt: (ctx: CheatContext) => CheatOutcome;
  /**
   * Prove the cheat had no effect.
   *
   * Throws when the attack got through — including when the authority layer
   * stopped defending.
   */
  readonly verify: (ctx: CheatContext, outcome: CheatOutcome) => void;
}

/** The result of one attack. */
export interface CheatAttackResult {
  readonly id: CheatId;
  readonly name: string;
  readonly kind: CheatKind;
  /** True when the attack was stopped. */
  readonly caught: boolean;
  /** What the server did with the attempt. */
  readonly note: string;
  /** Extra detail. */
  readonly detail?: string;
  /** Why the attack got through, when it did. */
  readonly failure?: string;
}

/** The result of the whole battery. */
export interface CheatBatteryReport {
  readonly results: readonly CheatAttackResult[];
  readonly caught: readonly CheatId[];
  readonly uncaught: readonly CheatId[];
}

function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

/* -- 1. inflated `res` ---------------------------------------------------- */

/**
 * The inflated-`res` request.
 *
 * A `buy` of a Worker I that declares a million gold. The upstream server
 * applies that delta verbatim (`upstream/socialwarriors/engine.py:251-268`),
 * so this is a million free gold there.
 */
function inflatedResRequest(ctx: CheatContext): WireRequest {
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'buy', BUY_WORKER_ARGS, res(0, 0, 1_000_000)]],
    },
    { token: ctx.attackerToken },
  );
}

const inflatedResAttack: CheatAttack = {
  id: 'inflated-res',
  name: 'inflated `res`',
  description:
    'A command that declares a resource delta far bigger than the command is entitled to.',
  kind: 'behavioural',
  attempt: (ctx) => {
    const result = serverCommandPath(ctx, inflatedResRequest(ctx));
    const cheated = upstreamApplyResources(ctx.attacker, res(0, 0, 1_000_000));
    return {
      succeeded: (result.resources['g'] ?? 0) === (cheated['g'] ?? 0),
      note: `the server paid ${result.resources['g']} gold; the upstream server would have paid ${cheated['g']}`,
      detail: `declared res=[0,0,1000000,0,0,0,0,0]`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'the declared resource delta reached the wallet');

    const cost = computeCommandCost(ctx.content, 'buy', BUY_WORKER_ARGS);
    assert.notEqual(cost, null);

    // The wallet the server path actually produced. This is the assertion
    // that matters: it fails if any layer between the wire and the wallet
    // starts honouring the declared delta.
    const result = serverCommandPath(ctx, inflatedResRequest(ctx));
    assert.equal(result.accepted, true, 'the purchase itself must be allowed');
    assert.equal(
      result.resources['g'],
      (ctx.attacker['g'] ?? 0) - (cost?.cost['g'] ?? 0),
      'the wallet must reflect the server-computed cost only',
    );
    assert.notEqual(
      result.resources['g'],
      (ctx.attacker['g'] ?? 0) + 1_000_000,
      'the wallet moved by the declared delta',
    );

    // And the rule the server path delegates to.
    const settled = settleCommand(ctx.content, ctx.attacker, 'buy', BUY_WORKER_ARGS);
    assert.equal(settled.ok, true, 'the server must be able to afford its own cost');
    assert.equal(
      settled.resources['g'],
      (ctx.attacker['g'] ?? 0) - (cost?.cost['g'] ?? 0),
      'the cost table must reflect the server-computed cost only',
    );

    // The structural half: the API has nowhere to put the client's claim.
    assert.equal(settleCommand.length, 4, 'settleCommand gained a parameter for the claimed delta');
    assert.equal(
      computeCommandCost.length,
      3,
      'computeCommandCost gained a parameter for the claimed delta',
    );
  },
};

/* -- 2. forged `flash_debug` ---------------------------------------------- */

/**
 * The `flash_debug` request.
 *
 * The upstream command carries the player's **absolute** wallet, not a delta
 * (`upstream/socialwarriors/command.py:302-320`), and the upstream server
 * writes it straight into the save. The client sends it every 20th command
 * once the player is level 10 (`re/docs/03-commands-quests-economy.md` §1.1).
 */
function flashDebugRequest(ctx: CheatContext): WireRequest {
  const absolute = [999_999, 999_999, 999_999, 999_999, 999_999, 999_999, 999_999];
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'flash_debug', absolute, res()]],
    },
    { token: ctx.attackerToken },
  );
}

const flashDebugAttack: CheatAttack = {
  id: 'flash-debug',
  name: 'forged `flash_debug`',
  description: "The upstream command that overwrites the whole wallet from the client's arguments.",
  kind: 'behavioural',
  attempt: (ctx) => {
    const result = serverCommandPath(ctx, flashDebugRequest(ctx));
    const moved = Object.keys(ctx.attacker).some(
      (key) => (result.resources[key] ?? 0) !== (ctx.attacker[key] ?? 0),
    );
    return {
      succeeded: moved,
      note: moved
        ? 'the wallet was overwritten'
        : 'the wallet was left exactly as it was',
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'flash_debug overwrote the wallet');
    assert.equal(
      computeCommandCost(ctx.content, 'flash_debug', [1, 2, 3, 4, 5, 6, 7]),
      null,
      'flash_debug must not be priced',
    );
    assert.ok(
      !(PRICED_COMMANDS as readonly string[]).includes('flash_debug'),
      'flash_debug must not be in the priced command list',
    );
    const result = serverCommandPath(ctx, flashDebugRequest(ctx));
    assert.deepEqual(result.resources, ctx.attacker, 'the wallet must be byte-for-byte unchanged');
  },
};

/* -- 3. replayed `win_daily_bonus` ---------------------------------------- */

const replayedDailyBonusAttack: CheatAttack = {
  id: 'replayed-daily-bonus',
  name: 'replayed `win_daily_bonus`',
  description: 'Claiming the same daily bonus twice.',
  kind: 'behavioural',
  attempt: (ctx) => {
    const first = claimDailyBonus(ctx, ctx.bonusState);
    const replay = claimDailyBonus(ctx, first.state);
    return {
      succeeded: replay.ok,
      note: `the first claim paid ${first.reward?.gold ?? 0} gold, the replay paid ${replay.reward?.gold ?? 0}`,
      detail: replay.ok ? 'the replay was paid again' : `the replay was refused (${replay.reason})`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'the daily bonus was paid twice');

    const first = claimDailyBonus(ctx, ctx.bonusState);
    assert.equal(first.ok, true, 'the first claim of the day must succeed');
    assert.equal(first.reward?.gold, ctx.bonusRules.goldRewards[0]);

    const replay = claimDailyBonus(ctx, first.state);
    assert.equal(replay.ok, false, 'the replay of the same day must be refused');
    assert.equal(replay.reason, 'not-ready');

    // The pure guard itself: claiming twice at the same instant is not ready.
    assert.equal(
      dailyBonusReadiness(ctx.nowSeconds, ctx.nowSeconds, ctx.tzOffsetHours).ready,
      false,
      'dailyBonusReadiness must refuse a second claim on the same day',
    );
  },
};

/* -- 4. self-completed goals ---------------------------------------------- */

const selfCompletedGoalAttack: CheatAttack = {
  id: 'self-completed-goal',
  name: 'self-completed goals',
  description: "Telling the server a goal is done and asking for its reward.",
  kind: 'behavioural',
  attempt: (ctx) => {
    const forged = awardGoal(ctx.goals, 1);
    const earned = applyGoalEvent(
      ctx.goals,
      { type: 'elementBuilt', itemId: 1, playerId: 1 },
      ctx.goalWorld,
    );
    const award = awardGoal(earned.state, 1);
    const replay = award.ok ? awardGoal(award.state, 1) : null;
    return {
      succeeded: forged.ok,
      note: `the forged claim paid ${forged.ok ? '10 gold' : 'nothing'}; the earned goal paid ${award.ok ? '10 gold' : 'nothing'}; the replay paid ${replay?.ok ? '10 gold' : 'nothing'}`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'a goal the player never did was paid');

    const forged = awardGoal(ctx.goals, 1);
    if (forged.ok) throw new Error('the forged goal claim was paid');
    assert.equal(forged.reason, 'not-completed');

    // The server's own event is what completes a goal.
    const earned = applyGoalEvent(
      ctx.goals,
      { type: 'elementBuilt', itemId: 1, playerId: 1 },
      ctx.goalWorld,
    );
    assert.equal(earned.completions.length, 1, 'the server must see the goal complete');
    assert.equal(earned.completions[0]?.goalId, 1);

    const award = awardGoal(earned.state, 1);
    assert.equal(award.ok, true, 'a genuinely completed goal must be paid');
    if (!award.ok) throw new Error('unreachable');
    assert.deepEqual(award.reward, { resource: 'g', amount: 10 });

    const replay = awardGoal(award.state, 1);
    assert.equal(replay.ok, false, 'the same goal must not be paid twice');
    if (replay.ok) throw new Error('unreachable');
    assert.equal(replay.reason, 'already-awarded');

    // The wallet moves by the server's reward, exactly once.
    const wallet = applyGoalReward(ctx.attacker, award.reward);
    assert.equal(wallet['g'], (ctx.attacker['g'] ?? 0) + 10);
  },
};

/* -- 5. forged `end_attack` ----------------------------------------------- */

/**
 * The forged-`end_attack` request.
 *
 * The client reports a battle it won, with the loot attached. The upstream
 * server believes the whole payload
 * (`upstream/socialwarriors/command.py:808-884`).
 */
function forgedEndAttackRequest(ctx: CheatContext): WireRequest {
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [
        [
          0,
          'end_attack',
          [
            JSON.stringify({
              voluntary_end: 0,
              victim: { name: 'Victim' },
              attacker: { name: 'Attacker' },
              resources: { g: 50_000, x: 5_000 },
              honor: 999,
              duration: 1,
              townhall_gold: 50_000,
              win: 1,
              different_island: 0,
              victim_units: [],
              attacker_units: [],
              resources_victim: { g: 50_000 },
            }),
            '0',
          ],
          res(0, 0, 50_000, 0, 0, 0, 0, 5_000),
        ],
      ],
    },
    { token: ctx.attackerToken },
  );
}

const forgedEndAttackAttack: CheatAttack = {
  id: 'forged-end-attack',
  name: 'forged `end_attack`',
  description: 'Claiming a PvP battle was won, with the loot attached.',
  kind: 'behavioural',
  attempt: (ctx) => {
    const outcome = resolveServerCombat({
      seed: battleSeed(ctx.battleId),
      attacker: ctx.attackerCombatant,
      defender: ctx.defenderCombatant,
    });
    const claim = checkClientClaim({ damage: ctx.claimedDamage }, outcome);
    const result = serverCommandPath(ctx, forgedEndAttackRequest(ctx));
    const paid = (result.resources['g'] ?? 0) !== (ctx.attacker['g'] ?? 0);
    return {
      succeeded: paid,
      note: `the server rolled ${outcome.damage} damage and killed=${outcome.killed}; the client claimed ${ctx.claimedDamage}`,
      detail: claim.matches ? 'the claim agreed with the server' : 'the claim contradicted the server',
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'the forged assault loot was paid');

    const result = resolveServerCombat({
      seed: battleSeed(ctx.battleId),
      attacker: ctx.attackerCombatant,
      defender: ctx.defenderCombatant,
    });
    // The server's own answer, from the server-issued seed.
    assert.equal(result.killed, false, "the server's roll decided the battle was won");
    assert.ok(result.damage < ctx.claimedDamage);

    const claim = checkClientClaim({ damage: ctx.claimedDamage }, result);
    assert.equal(claim.matches, false, 'the claim must contradict the server');
    assert.equal(claim.serverDamage, result.damage);

    // The client's declared loot is not a cost the command table knows.
    assert.equal(
      computeCommandCost(ctx.content, 'end_attack', ['{}', '0']),
      null,
      'end_attack must not carry a client-supplied grant',
    );
    const settled = settleCommand(ctx.content, ctx.attacker, 'end_attack', ['{}', '0']);
    assert.equal(settled.ok, true);
    assert.deepEqual(settled.resources, ctx.attacker, 'the forged loot moved the wallet');

    // The wallet the server path produced: the loot must not be there.
    const path = serverCommandPath(ctx, forgedEndAttackRequest(ctx));
    assert.deepEqual(path.resources, ctx.attacker, 'the forged loot reached the wallet');

    // The combat API has no room for a client claim.
    assert.equal(resolveServerCombat.length, 1, 'resolveServerCombat gained a parameter');
  },
};

/* -- 6. free `buy_offer_pack` -------------------------------------------- */

/**
 * The free-offer-pack request.
 *
 * The client declares the pack's contents and *no* cash spent — the upstream
 * server credits the declared delta and never checks the cash
 * (`upstream/socialwarriors/command.py:710-718`).
 */
function freeOfferPackRequest(ctx: CheatContext): WireRequest {
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [
        [0, 'buy_offer_pack', [STARTER_PACK_ID, '[]'], res(0, 0, 5000, 5000, 5000, 5000, 0, 0)],
      ],
    },
    { token: ctx.attackerToken },
  );
}

const freeOfferPackAttack: CheatAttack = {
  id: 'free-offer-pack',
  name: 'free `buy_offer_pack`',
  description: 'Buying an offer pack without paying for it.',
  kind: 'behavioural',
  attempt: (ctx) => {
    const pack = ctx.content.offerPacks.get(STARTER_PACK_ID);
    const result = serverCommandPath(ctx, freeOfferPackRequest(ctx));
    const gained = (result.resources['g'] ?? 0) !== (ctx.attacker['g'] ?? 0);
    return {
      succeeded: gained,
      note: gained
        ? `the pack was granted for ${pack?.cost_cash ?? 0} cash`
        : `the request was refused (${result.reason ?? 'refused'})`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'the offer pack was granted without payment');

    const pack = ctx.content.offerPacks.get(STARTER_PACK_ID);
    assert.notEqual(pack, undefined, 'the starter pack must exist in the content bundle');

    const cost = computeCommandCost(ctx.content, 'buy_offer_pack', [STARTER_PACK_ID, '[]']);
    assert.notEqual(cost, null, 'an offer pack must be priced');
    assert.equal(cost?.cost['c'], pack?.cost_cash, 'the pack must cost its cash price');

    // The attacker has no cash, so the purchase must be refused outright.
    assert.ok(
      (ctx.attacker['c'] ?? 0) < (pack?.cost_cash ?? 0),
      'the fixture must not be able to afford the pack',
    );
    const settled = settleCommand(ctx.content, ctx.attacker, 'buy_offer_pack', [STARTER_PACK_ID, '[]']);
    assert.equal(settled.ok, false, 'a pack the player cannot afford must be refused');
    assert.equal(settled.reason, 'insufficient-resources');
    assert.deepEqual(settled.resources, ctx.attacker, 'a refused purchase must change nothing');

    // The wallet the server path produced: the request must be refused there
    // too, and nothing may have moved.
    const result = serverCommandPath(ctx, freeOfferPackRequest(ctx));
    assert.equal(result.accepted, false, 'the server path must refuse the purchase');
    assert.equal(result.reason, 'insufficient-resources');
    assert.deepEqual(result.resources, ctx.attacker, 'a refused purchase must change nothing');

    // The control: with the cash, the grant is exactly the server's numbers.
    const rich = settleCommand(
      ctx.content,
      { ...ctx.attacker, c: pack?.cost_cash ?? 0 },
      'buy_offer_pack',
      [STARTER_PACK_ID, '[]'],
    );
    assert.equal(rich.ok, true);
    assert.equal(rich.resources['c'], 0, 'the cash price must be charged');
    assert.equal(rich.resources['g'], (ctx.attacker['g'] ?? 0) + (pack?.gold ?? 0));
  },
};

/* -- 7. wrong HMAC -------------------------------------------------------- */

const wrongHmacAttack: CheatAttack = {
  id: 'wrong-hmac',
  name: 'wrong HMAC',
  description: "A `command.php` body signed with the wrong key.",
  kind: 'structural',
  attempt: (ctx) => {
    const request = buildRequest(
      {
        ts: ctx.nowSeconds,
        tries: 1,
        flashVersion: '1.5.4',
        first_number: 1,
        accessToken: '0000000000',
        publishActions: '0',
        commands: [[0, 'buy', BUY_WORKER_ARGS, res()]],
      },
      { key: 'not-the-server-key', token: ctx.attackerToken },
    );
    const result = serverCommandPath(ctx, request);
    return {
      succeeded: result.accepted,
      note: result.accepted
        ? 'the mis-signed request was accepted'
        : `the request was refused (${result.reason ?? 'refused'})`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'a mis-signed request was accepted');

    const batch: CheatBatch = {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'buy', BUY_WORKER_ARGS, res()]],
    };
    const payload = JSON.stringify(batch);
    const wrong = framePayload(payload, 'not-the-server-key');

    assert.equal(verifyFrame(wrong, 'not-the-server-key'), true, 'the wrong key signed it correctly');
    assert.equal(verifyFrame(wrong, SERVER_KEYS.current), false);
    assert.equal(verifyFrame(wrong, SERVER_KEYS.legacy), false);
    assert.equal(verifyFrameAny(wrong), null, 'the request must not match any accepted key');

    const gate = serverAcceptFrame(wrong);
    assert.equal(gate.accepted, false);
    assert.equal(gate.key, null);
    assert.equal(gate.payload, null);

    // The control: the same payload, signed with an accepted key, is accepted —
    // so the rejection above is about the key and not about the payload.
    for (const key of ACCEPTED_KEYS) {
      const good = serverAcceptFrame(framePayload(payload, key));
      assert.equal(good.accepted, true, `the request must be accepted when signed with ${key}`);
      assert.equal(good.key, key);
    }
  },
};

/* -- 8. another player's `USERID` ----------------------------------------- */

const foreignUserIdAttack: CheatAttack = {
  id: 'foreign-userid',
  name: "another player's `USERID`",
  description: "Using someone else's identity: `USERID` in the query string and in the body.",
  kind: 'structural',
  attempt: (ctx) => {
    const request = buildRequest(
      {
        ts: ctx.nowSeconds,
        tries: 1,
        flashVersion: '1.5.4',
        first_number: 1,
        accessToken: '0000000000',
        publishActions: '0',
        // The upstream `USERID` lives in the query string; a cheat puts it in
        // the body as well. Neither may be read.
        USERID: ctx.victimUserId,
        commands: [[0, 'buy', BUY_WORKER_ARGS, res()]],
      },
      { token: ctx.attackerToken, userId: ctx.victimUserId },
    );
    const result = serverCommandPath(ctx, request);
    return {
      succeeded: result.playerId === ctx.victimId,
      note: `the request named USERID ${ctx.victimUserId}; the server resolved ${result.playerId ?? 'nobody'}`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, "the body's USERID chose the player");

    const request = buildRequest(
      {
        ts: ctx.nowSeconds,
        tries: 1,
        flashVersion: '1.5.4',
        first_number: 1,
        accessToken: '0000000000',
        publishActions: '0',
        USERID: ctx.victimUserId,
        commands: [[0, 'buy', BUY_WORKER_ARGS, res()]],
      },
      { token: ctx.attackerToken, userId: ctx.victimUserId },
    );
    const result = serverCommandPath(ctx, request);
    assert.equal(result.playerId, ctx.attackerId, 'the session token must decide the player');
    assert.equal(result.accepted, true);

    // The victim's wallet is not the one that moved.
    const cost = computeCommandCost(ctx.content, 'buy', BUY_WORKER_ARGS);
    assert.notEqual(cost, null);
    assert.equal(
      result.resources['g'],
      (ctx.attacker['g'] ?? 0) - (cost?.cost['g'] ?? 0),
      "the attacker's wallet paid the cost",
    );
    assert.notDeepEqual(result.resources, ctx.victim, "the victim's wallet was settled against");

    // The identity is decided before the rules layer sees anything: the cost
    // API takes a wallet, not a player id.
    assert.equal(settleCommand.length, 4, 'settleCommand gained a player-identity parameter');
  },
};

/* -- 9. malformed framing ------------------------------------------------- */

const malformedFramingAttack: CheatAttack = {
  id: 'malformed-framing',
  name: 'malformed framing',
  description: 'A `data` body that is not `<64 hex>;<json>`.',
  kind: 'structural',
  attempt: (ctx) => {
    const batch: CheatBatch = {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'buy', BUY_WORKER_ARGS, res(0, 0, 1_000_000)]],
    };
    // The `skiphash12341` shape: the raw JSON, with no digest at all.
    const request = buildRequest(batch, { data: JSON.stringify(batch), token: ctx.attackerToken });
    const result = serverCommandPath(ctx, request);
    return {
      succeeded: result.accepted,
      note: result.accepted
        ? 'the unframed request was accepted'
        : `the request was refused (${result.reason ?? 'refused'})`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'an unframed request was accepted');

    const batch: CheatBatch = {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'buy', BUY_WORKER_ARGS, res(0, 0, 1_000_000)]],
    };
    const payload = JSON.stringify(batch);

    // Every malformed shape the client could send.
    const malformed: readonly string[] = [
      payload, // no digest at all — the `skiphash12341` bypass
      `${'a'.repeat(63)};${payload}`, // one hex character short
      `${'a'.repeat(64)}:${payload}`, // the wrong separator
      `${'z'.repeat(64)};${payload}`, // not hex at all
      'not a request',
      '',
    ];
    for (const data of malformed) {
      assert.equal(verifyFrameAny(data), null, `the malformed body was accepted: ${data.slice(0, 24)}`);
      const gate = serverAcceptFrame(data);
      assert.equal(gate.accepted, false);
      assert.equal(gate.payload, null);
    }

    // Correctly framed, but the payload is not a command batch.
    const notABatch = serverAcceptFrame(framePayload('{"hello":"world"}', SERVER_KEYS.current));
    assert.equal(notABatch.accepted, false, 'a payload that is not a command batch was accepted');
    assert.equal(notABatch.reason, 'bad-payload');

    // The parser takes an unframed body whole, with a null hash — and the
    // verifier still refuses it.
    assert.equal(parseFrame(payload).framed, false);
    assert.equal(parseFrame(payload).hash, null);
    assert.equal(parseFrame(payload).payload, payload);

    // The control: the correctly framed twin of the same payload is accepted.
    const good = serverAcceptFrame(framePayload(payload, SERVER_KEYS.current));
    assert.equal(good.accepted, true, 'the framed twin of the request must be accepted');
    assert.notEqual(good.payload, null);
  },
};

/* -- 10. forged `win` ----------------------------------------------------- */

/**
 * The forged-`win` request.
 *
 * The client reports `"win": 1` for a quest it did not win, with the reward
 * attached. The upstream server credits the client's declared delta
 * (`upstream/socialwarriors/command.py:752-805`).
 */
function forgedWinRequest(ctx: CheatContext): WireRequest {
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [
        [
          0,
          'end_quest',
          [
            JSON.stringify({
              map: 0,
              units: [],
              win: 1,
              duration: 1,
              voluntary_end: 0,
              quest_id: FORGED_WIN_QUEST_ID,
              difficulty: 3,
            }),
          ],
          res(0, 0, 1_000_000, 0, 0, 0, 0, 0),
        ],
      ],
    },
    { token: ctx.attackerToken },
  );
}

const forgedWinAttack: CheatAttack = {
  id: 'forged-win',
  name: 'forged `win`',
  description: "Claiming a quest was won, with the reward attached.",
  kind: 'behavioural',
  attempt: (ctx) => {
    const serverWin = isQuestVictory(ctx.quest);
    const outcome = finishQuest(ctx.quest, serverWin, { expRequired: ctx.expRequired });
    const result = serverCommandPath(ctx, forgedWinRequest(ctx));
    const paid = (result.resources['g'] ?? 0) !== (ctx.attacker['g'] ?? 0);
    return {
      succeeded: paid || outcome.win,
      note: `the server says the quest was ${outcome.win ? 'won' : 'lost'}; the client claimed a win`,
      detail: `the server's reward list: ${JSON.stringify(outcome.rewards)}`,
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'the forged quest win was accepted');

    // The server's own answer: nothing was destroyed, so nothing was won.
    assert.equal(isQuestVictory(ctx.quest), false, 'the server must not see a victory');
    const serverOutcome = finishQuest(ctx.quest, isQuestVictory(ctx.quest), {
      expRequired: ctx.expRequired,
    });
    assert.equal(serverOutcome.win, false);

    // The static win row is only granted on a win the server agrees with.
    const spec = getQuestSpec(FORGED_WIN_QUEST_ID);
    assert.notEqual(spec, undefined, 'the quest must be in the catalogue');
    const staticRow = spec?.reward['g'] ?? 0;
    assert.ok(staticRow > 0, 'the quest must have a static win row');
    const wonRewards = questRewards(spec!, 0, 0, true, { expRequired: ctx.expRequired });
    assert.ok(
      wonRewards.some((reward) => reward.amount === staticRow),
      'the static win row must be granted for a genuine win',
    );
    assert.ok(
      !serverOutcome.rewards.some((reward) => reward.amount === staticRow),
      "the quest's static win row must not be granted on a loss",
    );

    // The reward is granted once.
    const first = awardQuest(ctx.questProgress, serverOutcome);
    assert.equal(first.award.awarded, true);
    const replay = awardQuest(first.progress, serverOutcome);
    assert.equal(replay.award.awarded, false, 'the quest reward must not be granted twice');
    assert.deepEqual(replay.award.rewards, []);

    // The client's declared reward never reaches the wallet.
    const settled = settleCommand(ctx.content, ctx.attacker, 'end_quest', ['{}']);
    assert.deepEqual(settled.resources, ctx.attacker);
    const path = serverCommandPath(ctx, forgedWinRequest(ctx));
    assert.deepEqual(path.resources, ctx.attacker, 'the forged quest reward reached the wallet');
  },
};

/* -- 11. over-collection -------------------------------------------------- */

/**
 * The over-collection request.
 *
 * A `collect` against a building that is holding more units than it can
 * hold. The client logs "HACK DETECTED - jsbermeo: the units in this
 * building are higher than the building capacity!" and collects nothing —
 * but that check is **client-side only** in the original, and the upstream
 * server credits the client's declared delta anyway
 * (`upstream/socialwarriors/command.py:136-147`).
 */
function overCollectionRequest(ctx: CheatContext): WireRequest {
  return buildRequest(
    {
      ts: ctx.nowSeconds,
      tries: 1,
      flashVersion: '1.5.4',
      first_number: 1,
      accessToken: '0000000000',
      publishActions: '0',
      commands: [[0, 'collect', [7], res(0, 0, 100_000, 0, 0, 0, 0, 0)]],
    },
    { token: ctx.attackerToken },
  );
}

const overCollectionAttack: CheatAttack = {
  id: 'over-collection',
  name: 'over-collection',
  description: 'Collecting a resource more times than the building produced.',
  kind: 'behavioural',
  attempt: (ctx) => {
    const result = collect(ctx.overfullProducer, 1, ctx.collectPeriods);
    const legal = collect(ctx.legalProducer, 1, ctx.collectPeriods);
    const path = serverCommandPath(ctx, overCollectionRequest(ctx));
    const gained = (path.resources['g'] ?? 0) !== (ctx.attacker['g'] ?? 0);
    return {
      succeeded: result.amount > 0 || gained,
      note: `the over-full building produced ${result.amount}; a legal one produced ${legal.amount}`,
      detail: result.hacked ? 'the anti-hack guard tripped' : 'the anti-hack guard did not trip',
    };
  },
  verify: (ctx, outcome) => {
    assert.equal(outcome.succeeded, false, 'an over-full building still produced resources');

    const result = collect(ctx.overfullProducer, 1, ctx.collectPeriods);
    assert.equal(result.hacked, true, 'the anti-hack guard must trip');
    assert.equal(result.amount, 0, 'an over-full building must produce nothing');

    // The control: the same building in a legal state does produce.
    const legal = collect(ctx.legalProducer, 1, ctx.collectPeriods);
    assert.equal(legal.hacked, false);
    assert.ok(legal.amount > 0, 'a legal building must produce its resources');

    // The wallet the server path produced: nothing may have moved.
    const path = serverCommandPath(ctx, overCollectionRequest(ctx));
    assert.deepEqual(path.resources, ctx.attacker, 'the over-collection reached the wallet');
  },
};

/* ------------------------------------------------------------------------- *
 * The runner
 * ------------------------------------------------------------------------- */

/** Every attack, in the roadmap's order. */
export function cheatBattery(_ctx: CheatContext): readonly CheatAttack[] {
  return [
    inflatedResAttack,
    flashDebugAttack,
    replayedDailyBonusAttack,
    selfCompletedGoalAttack,
    forgedEndAttackAttack,
    freeOfferPackAttack,
    wrongHmacAttack,
    foreignUserIdAttack,
    malformedFramingAttack,
    forgedWinAttack,
    overCollectionAttack,
  ];
}

/**
 * Run one attack and report whether it was caught.
 *
 * A failed verification is reported as *not caught*, with the reason. The
 * battery never claims a defence it cannot show.
 */
export function runCheatAttack(ctx: CheatContext, attack: CheatAttack): CheatAttackResult {
  let outcome: CheatOutcome;
  try {
    outcome = attack.attempt(ctx);
  } catch (error) {
    return {
      id: attack.id,
      name: attack.name,
      kind: attack.kind,
      caught: false,
      note: 'the attempt itself failed',
      failure: messageOf(error),
    };
  }
  try {
    attack.verify(ctx, outcome);
  } catch (error) {
    return {
      id: attack.id,
      name: attack.name,
      kind: attack.kind,
      caught: false,
      note: outcome.note,
      detail: outcome.detail,
      failure: messageOf(error),
    };
  }
  return {
    id: attack.id,
    name: attack.name,
    kind: attack.kind,
    caught: true,
    note: outcome.note,
    detail: outcome.detail,
  };
}

/** Run the whole battery. */
export function runCheatBattery(
  ctx: CheatContext,
  attacks: readonly CheatAttack[] = cheatBattery(ctx),
): CheatBatteryReport {
  const results = attacks.map((attack) => runCheatAttack(ctx, attack));
  return {
    results,
    caught: results.filter((result) => result.caught).map((result) => result.id),
    uncaught: results.filter((result) => !result.caught).map((result) => result.id),
  };
}

/** Find an attack by id. */
export function findCheatAttack(ctx: CheatContext, id: CheatId): CheatAttack | undefined {
  return cheatBattery(ctx).find((attack) => attack.id === id);
}

/**
 * The quest state with its win condition met.
 *
 * The control for the forged-`win` attack: when the server's own state says
 * the quest was won, the static reward row *is* granted — so the battery
 * proves the decision comes from the server's state and not from the client.
 */
export function questWithVictory(ctx: CheatContext): QuestState {
  return nearDeathQuestElement(nearDeathQuestElement(ctx.quest, 'boss1'), 'jeep');
}
