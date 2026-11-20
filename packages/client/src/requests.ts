/**
 * The client's command requests.
 *
 * Every action the player takes becomes a **request**: the client builds a
 * command, sends it with an idempotency key, and renders the server's
 * answer. It never decides the outcome itself.
 *
 * These are the builders, and they are deliberately thin. Each one produces
 * a `NativeCommand` — a name and its positional arguments, in the order
 * the command table lists them — and nothing else. There is no
 * "optimistically apply" step here, because that is the *renderer's* job
 * and it is explicitly provisional (see `predictions.ts`).
 *
 * The argument order comes from the command table, which is the
 * authority: `packages/protocol/src/commands.ts`.
 */
import type { CommandName, NativeCommand } from '@swl/protocol';
import type { MagicPayment } from '@swl/rules';
import type { Neighbour } from './neighbours.ts';
import { authorizationHeader, type ClientSession } from './session.ts';
import { requestId } from './transport.ts';

export type { CommandName, NativeCommand };

/**
 * The other players, for the neighbour strip.
 *
 * The server's answer: the names, the levels and the experience are
 * the **server's**, and the order is the store's.
 */
export async function fetchNeighbours(
  session: ClientSession,
  fetchImpl: typeof fetch = fetch,
): Promise<Neighbour[]> {
  try {
    const response = await fetchImpl('/api/neighbours', {
      headers: { authorization: authorizationHeader(session) },
    });
    if (!response.ok) return [];
    const body = (await response.json()) as { neighbours?: Neighbour[] };
    return body.neighbours ?? [];
  } catch {
    // The server could not be reached. The strip is empty, and the
    // game is still playable.
    return [];
  }
}

/** The client's own town. */
export const OWN_TOWN = 0;

/**
 * Build a command.
 *
 * The map is always the player's own town for now; the neighbouring
 * towns are reached through the assault commands, which carry the
 * victim's id in their own arguments.
 */
function command(name: CommandName, args: readonly unknown[]): NativeCommand {
  return { map: OWN_TOWN, name, args };
}

/** Buy a building or a unit and place it. */
export function buy(itemId: number, tx: number, ty: number, type: 'b' | 'u' | 'n'): NativeCommand {
  return command('buy', [0, itemId, tx, ty, 1, 0, 0, type]);
}

/** Put a stored building on the map. */
export function placeStoredItem(
  itemId: number,
  tx: number,
  ty: number,
  imgIndex = 0,
  unitLevel?: number,
  requiredXp?: number,
): NativeCommand {
  return command('place_stored_item', [
    0,
    itemId,
    tx,
    ty,
    1,
    0,
    0,
    imgIndex,
    ...(unitLevel === undefined ? [] : [unitLevel]),
    ...(requiredXp === undefined ? [] : [requiredXp]),
  ]);
}

/** Move a building or a unit to another tile. */
export function move(isoId: number, tx: number, ty: number, frame = 0): NativeCommand {
  return command('move', [isoId, tx, ty, frame, 'move']);
}

/**
 * Choose a resource building's collection period.
 *
 * The client names the building and one of the content's 1-based periods; it
 * never names a duration or a multiplier. The server checks the building's
 * eligibility and stamps the countdown from its own clock.
 */
export function activate(isoId: number, period: number): NativeCommand {
  return command('activate', [isoId, period]);
}

/**
 * Collect a building's production.
 *
 * The collect period is the **server's**: the native form carries only the
 * element's id, so the client cannot choose which period's multiplier it
 * gets. `activate` only picks which of the content's periods the server
 * should time.
 */
export function collect(isoId: number): NativeCommand {
  return command('collect', [isoId]);
}

/** Start training a unit. */
export function train(isoId: number, unitItemId?: number): NativeCommand {
  return unitItemId === undefined
    ? command('push_queue_unit', [isoId])
    : command('push_queue_unit2', [isoId, unitItemId]);
}

/** Take the finished unit out of the training queue. */
export function takeTrainedUnit(isoId: number): NativeCommand {
  return command('pop_queue_unit', [isoId]);
}

/** Upgrade a building to its next tier. */
export function upgrade(isoId: number): NativeCommand {
  return command('upgrade', [isoId]);
}

/** Level the player up. */
export function levelUp(newLevel: number): NativeCommand {
  return command('level_up', [newLevel]);
}

/** Hurry a build up. */
export function finishBuilding(isoId: number, clicksToBuild: number): NativeCommand {
  return command('finish_building', [isoId, clicksToBuild]);
}

/** Re-activate a depleted wonder. */
export function resetCollect(isoId: number): NativeCommand {
  return command('reset_collect', [isoId]);
}

/** Tell the server a goal is done. The server checks its own state. */
export function completeGoal(goalId: number): NativeCommand {
  return command('complete_goal', [goalId]);
}

/**
 * Report a tutorial step.
 *
 * The step is the one the player has **reached**, and the server keeps
 * the furthest one. The tutorial grants nothing by itself, so this is a
 * record and not a reward.
 */
export function completeTutorial(step: number): NativeCommand {
  return command('complete_tutorial', [step]);
}

/**
 * Claim the daily bonus.
 *
 * The **day** is the client's choice and it is **one-based**: the client
 * queues `CmdWinBonus(1)`, `CmdWinBonus(2)` and so on, and the command
 * reads `DAILY_GOLD_REWARDS[day - 1]`. A zero-based day would index
 * before the start of the rewards, and the protocol would refuse the
 * request - so the player could never claim the bonus.
 *
 * The **reward** is the server's: it computes the day from its own clock
 * and ignores what the client claims.
 *
 * @param day the day of the five-day cycle, 1 to 5
 * @param itemId the hero item on the fifth day, or 0 on a gold day
 */
export function claimDailyBonus(day = 1, itemId = 0): NativeCommand {
  return command('win_daily_bonus', [itemId, day]);
}

/** Claim the weekly bonus. */
export function claimWeeklyBonus(): NativeCommand {
  return command('weekly_reward', []);
}

/**
 * Finish an attack.
 *
 * The native form carries the **attack id** the server issued, not the
 * battle result: the client does not declare the outcome of a battle, it
 * names the battle. The server re-simulates it from its own seed.
 */
export function endAttack(attackId: string, voluntaryEnd: boolean): NativeCommand {
  return command('end_attack', [attackId, voluntaryEnd ? '1' : '0']);
}

/**
 * Finish a quest.
 *
 * The difficulty is the server's to award: the client sends the quest
 * and the difficulty it *was* playing, and the server checks both
 * against its own state.
 */
export function endQuest(questId: string | number, difficulty: number): NativeCommand {
  // The native argument is STR. A number is refused with a 400 by the
  // protocol's validation before the server reads its own quest state.
  return command('end_quest', [String(questId), difficulty]);
}

/**
 * Report one kill to the active quest.
 *
 * The native form is strictly **two** arguments: the `killed` key and a
 * JSON-encoded list of refs. There is no third argument — no client-declared
 * quest id, counter, amount or difficulty — because the server reads the quest
 * from its own active state and accepts a ref only once its own engagement
 * ledger marks the element dead. A forged or early ref is refused.
 */
export function reportQuestKill(ref: string): NativeCommand {
  return command('set_quest_var', ['killed', JSON.stringify([ref])]);
}

/* -------------------------------------------------------------------------
 * The native quest workflow
 *
 * Starting a quest and applying an authoritative event are not commands: they
 * are their own endpoints, because only the server may create an active quest
 * or move its ledger. The helpers below use the same authorization header as
 * every other request and carry an idempotency key, but they name neither a
 * reward nor a counter: the answer is the server's own ledger summary.
 * ---------------------------------------------------------------------- */

/** The authoritative actions a client may ask the server to apply. */
export type QuestActionRequest =
  | { type: 'strike'; ref: string }
  | { type: 'truck-arrival'; ref: string }
  | { type: 'eligible-enemy'; ref: string }
  | { type: 'civilian-evacuation'; ref: string };

/** The server's answer to a quest start. */
export interface QuestStartBody {
  readonly questId: string;
  readonly started: boolean;
}

/** One element of the server's engagement ledger, as it answers. */
export interface QuestLedgerElement {
  readonly hp: number;
  readonly alive: boolean;
}

/** The server's authoritative ledger summary. */
export interface QuestLedgerSummary {
  readonly questId: string;
  readonly phase: string;
  readonly counters: Record<string, number>;
  readonly elements: Record<string, QuestLedgerElement>;
  readonly events: string[];
}

/** A typed native result: an answer, or the reason there was none. */
export interface QuestResult<T> {
  /** Whether the server accepted the request. */
  readonly ok: boolean;
  /** The HTTP status, or 0 when the request never reached the server. */
  readonly status: number;
  /** The parsed answer, never invented when the server refused or lied. */
  readonly body: T | null;
  /** A transport-level or malformed-answer failure. */
  readonly error?: 'network' | 'bad-answer';
}

/** Read a plain record only when it really is one. */
function questRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

/** Copy only the own, finite numeric counters out of the server's answer. */
function questCounters(value: unknown): Record<string, number> | null {
  const source = questRecord(value);
  if (!source) return null;
  const out: Record<string, number> = {};
  for (const [key, entry] of Object.entries(source)) {
    if (typeof entry === 'number' && Number.isFinite(entry)) out[key] = entry;
  }
  return out;
}

/** Parse a ledger summary, returning null rather than fabricating one. */
function questSummaryBody(value: unknown): QuestLedgerSummary | null {
  const source = questRecord(value);
  const elements = questRecord(source?.['elements']);
  const counters = questCounters(source?.['counters']);
  if (!source || typeof source['questId'] !== 'string' || typeof source['phase'] !== 'string') {
    return null;
  }
  if (!elements || !counters || !Array.isArray(source['events'])) return null;
  const parsedElements: Record<string, QuestLedgerElement> = {};
  for (const [ref, entry] of Object.entries(elements)) {
    const element = questRecord(entry);
    if (!element || typeof element['hp'] !== 'number' || typeof element['alive'] !== 'boolean') {
      return null;
    }
    parsedElements[ref] = { hp: element['hp'], alive: element['alive'] };
  }
  return {
    questId: source['questId'],
    phase: source['phase'],
    counters,
    elements: parsedElements,
    events: source['events'].filter((event): event is string => typeof event === 'string'),
  };
}

/** POST a JSON body to a native quest endpoint. */
async function postQuest<T>(
  url: string,
  session: ClientSession,
  body: Record<string, unknown>,
  parse: (value: unknown) => T | null,
  fetchImpl: typeof fetch,
): Promise<QuestResult<T>> {
  let response: Response;
  try {
    response = await fetchImpl(url, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: authorizationHeader(session),
      },
      body: JSON.stringify({ id: requestId(), ...body }),
    });
  } catch {
    return { ok: false, status: 0, body: null, error: 'network' };
  }
  if (!response.ok) return { ok: false, status: response.status, body: null };
  try {
    const parsed = parse(await response.json());
    if (!parsed) return { ok: false, status: response.status, body: null, error: 'bad-answer' };
    return { ok: true, status: response.status, body: parsed };
  } catch {
    return { ok: false, status: response.status, body: null, error: 'bad-answer' };
  }
}

/** Start a quest in the server's own state. */
export async function startQuestOnServer(
  session: ClientSession,
  questId: string,
  difficulty?: number,
  fetchImpl: typeof fetch = fetch,
): Promise<QuestResult<QuestStartBody>> {
  return postQuest(
    '/api/quest/start',
    session,
    { questId, ...(difficulty === undefined ? {} : { difficulty }) },
    (value): QuestStartBody | null => {
      const source = questRecord(value);
      if (!source || typeof source['questId'] !== 'string' || source['started'] !== true) return null;
      return { questId: source['questId'], started: true };
    },
    fetchImpl,
  );
}

/** Apply one authoritative quest action on the server. */
export async function questActionOnServer(
  session: ClientSession,
  questId: string,
  action: QuestActionRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<QuestResult<QuestLedgerSummary>> {
  return postQuest(
    '/api/quest/action',
    session,
    { questId, action },
    questSummaryBody,
    fetchImpl,
  );
}

/** Trade a resource at the market. */
export function tradeResource(resource: string, selling: boolean, amount: number): NativeCommand {
  return command('trade_resource', [resource, selling ? 1 : 0, amount]);
}

/** Expand the town. */
export function expand(tileId: number): NativeCommand {
  return command('expand', [tileId]);
}

/**
 * Learn a spell, paying with gold or cash.
 *
 * The client names the spell and the resource; the **server** prices it from
 * the content. Gold respects the spell's unlock level, cash does not. A
 * purchase also grants the spell's mana cost, which the server adds.
 */
export function buyMagic(spellId: number, payment: MagicPayment): NativeCommand {
  return command('buy_magic', [spellId, payment]);
}

/**
 * Buy the fixed dark-matter pack.
 *
 * The amount and the payment resource are the client's; the price is the
 * server's, and an amount that is not the content's `MANA_PER_PURCHASE` is
 * refused.
 */
export function buyMana(amount: number, payment: MagicPayment): NativeCommand {
  return command('buy_mana_new', [amount, payment]);
}

/**
 * Cast a learned spell.
 *
 * The command carries only the spell id, as the original does. The server
 * owns the mana deduction and the use counter; the battle effect is the
 * client's rendering.
 */
export function useMagic(spellId: number): NativeCommand {
  return command('use_magic', [spellId]);
}

/** Claim the free darts shot of the day. */
export function claimFreeDarts(): NativeCommand {
  return command('darts_new_free', []);
}

/** Start a fresh darts board from the server's seed. */
export function resetDarts(seed: number): NativeCommand {
  return command('darts_reset', [seed]);
}

/**
 * Shoot one balloon.
 *
 * The only claim is whether the EXTRA prize was found. Whether the shot was
 * free is the server's decision, and the client names no prize of its own.
 */
export function shootBalloon(targetIndex: number, wonExtra: boolean): NativeCommand {
  return command('darts_shoot_balloon', [targetIndex, wonExtra ? 1 : 0]);
}

/** Buy an offer pack, naming the pack and the chosen item ids. The price is the server's. */
export function buyOfferPack(packId: number, itemIds: readonly number[]): NativeCommand {
  return command('buy_offer_pack', [packId, JSON.stringify(itemIds)]);
}

/** Buy a premium package by its index in the content's `PREMIUM_ACCOUNTS`. */
export function buyPremium(packageIndex: number): NativeCommand {
  return command('buy_premium_account', [packageIndex]);
}

/**
 * Replace a building with its upgraded version.
 *
 * Argument 0 is the OLD iso id and argument 1 the NEW one, as the table says;
 * the clicks and the price are the server's to check.
 */
export function premiumUpgrade(
  oldIsoId: number,
  newIsoId: number,
  newItemId: number,
  clicksToBuild: number,
): NativeCommand {
  return command('premium_upgrade', [oldIsoId, newIsoId, newItemId, clicksToBuild]);
}

/** Finish a chapter. The argument is the NEXT chapter id, not the one just finished. */
export function collectMission(nextChapterId: number): NativeCommand {
  return command('collect_mission', [nextChapterId]);
}

/**
 * Buy a resource pack.
 *
 * The client names the resource, the amount and the payment resource; it
 * never names a price, which the server derives from the content bundle.
 */
export function buyResources(
  resource: 'g' | 'w' | 'o' | 's',
  amount: number,
  payment: 'c' | 'g',
): NativeCommand {
  return command('buy_resources', [resource, amount, payment]);
}

/** Exchange cash for gold. The rate is the server's; the client claims no amount. */
export function exchangeCash(): NativeCommand {
  return command('exchange_cash', []);
}

/**
 * The commands the client sends, and the ones it must never send.
 *
 * `flash_debug` overwrites the whole wallet from client arguments, and
 * the new server refuses it outright (non-negotiable 6). The list is here
 * so the client's own code cannot reach for it by accident.
 */
export const FORBIDDEN_COMMANDS: readonly CommandName[] = ['flash_debug', 'set_variables'];
