/**
 * The Group G4 features, read from the server's save.
 *
 * These are **selectors**, not rules: they turn the server's answer into the
 * small pieces of state the client draws. They never decide an outcome and
 * never invent one. A save with none of a feature's keys is a world before
 * migration, and reads as `null`; a missing field inside a feature reads as
 * its empty default, never as a fabricated board, prize, price or timestamp.
 *
 * The keys are the ones the server actually writes. `questProgress` is added
 * to `privateState` by the migration; the other quest fields arrive in the
 * migrated save — `questTimes`, `idCurrentMission` and `currentQuestVars` on
 * the map, `questsRank` and `unlockedQuestIndex` in `privateState` (see the
 * vendored `villages/initial.json` and the protocol's `GameMap` /
 * `PrivateState` interfaces).
 */
import { RESOURCE_ORDER, type Reward } from '@swl/protocol';
import {
  SPECIAL_ATTACKS,
  SPECIAL_ATTACK_CLASSES,
  type SpecialAttackClass,
  type SpecialAttackShape,
  type Army,
} from '@swl/rules';

import type { WorldSnapshot } from './session.ts';

/* -------------------------------------------------------------------------
 * Reading untrusted save values
 * ---------------------------------------------------------------------- */

/** Read a record only when it really is a plain object, not an array or null. */
function record(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

/** Whether a record owns a key. Inherited keys are not server state. */
function has(source: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(source, key);
}

/** Read an echoed army, or nothing when the save does not hold a readable one. */
function armyOf(value: unknown): Army | undefined {
  if (!Array.isArray(value) || value.length === 0) return undefined;
  const out: { unitId: number; count: number }[] = [];
  for (const raw of value) {
    const entry = record(raw);
    if (!entry) return undefined;
    const unitId = entry['unitId'];
    const count = entry['count'];
    if (
      typeof unitId !== 'number' || !Number.isInteger(unitId) || unitId <= 0 ||
      typeof count !== 'number' || !Number.isInteger(count) || count <= 0
    ) {
      return undefined;
    }
    out.push({ unitId, count });
  }
  return out;
}

/** Read a number only when it is finite. */
function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** Read a boolean only when it really is one; every other value is false. */
function flag(value: unknown): boolean {
  return value === true;
}

/** Copy only the own, finite numeric values out of a record. */
function numbers(value: unknown): Record<string, number> {
  const source = record(value);
  if (!source) return {};
  const out: Record<string, number> = {};
  for (const [key, entry] of Object.entries(source)) {
    const at = number(entry);
    if (at !== null) out[key] = at;
  }
  return out;
}

/** Copy only the finite numbers out of a real array. */
function numberList(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  const out: number[] = [];
  for (const entry of value) {
    const at = number(entry);
    if (at !== null) out.push(at);
  }
  return out;
}

/** Copy only the string entries out of a real array. */
function strings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === 'string');
}

/* -------------------------------------------------------------------------
 * Darts
 * ---------------------------------------------------------------------- */

/** The darts board's state, as the server keeps it. */
export interface DartsState {
  /** The seed the board was drawn from. */
  readonly randomSeed: number | null;
  /** The balloons the server says were shot. Never a board generated here. */
  readonly balloonsShot: readonly number[];
  /** Whether a free shot is available. */
  readonly hasFree: boolean;
  /** Whether the extra prize was found. */
  readonly gotExtra: boolean;
  /** When the board was reset. */
  readonly resetAt: number | null;
  /** When the free shot was granted. */
  readonly newFreeAt: number | null;
}

const DART_KEYS = [
  'dartsRandomSeed',
  'dartsBalloonsShot',
  'dartsHasFree',
  'dartsGotExtra',
  'timeStampDartsReset',
  'timeStampDartsNewFree',
] as const;

/** Read the darts state, or `null` when the save has no darts keys. */
export function dartsState(world: WorldSnapshot): DartsState | null {
  const state = world.privateState;
  if (!DART_KEYS.some((key) => has(state, key))) return null;
  return {
    randomSeed: number(state['dartsRandomSeed']),
    balloonsShot: numberList(state['dartsBalloonsShot']),
    hasFree: flag(state['dartsHasFree']),
    gotExtra: flag(state['dartsGotExtra']),
    resetAt: number(state['timeStampDartsReset']),
    newFreeAt: number(state['timeStampDartsNewFree']),
  };
}

/* -------------------------------------------------------------------------
 * Market
 * ---------------------------------------------------------------------- */

/** The market's state, as the server keeps it. */
export interface MarketState {
  /** How many trades this period has used. */
  readonly tradesDone: number | null;
  /** What was traded, by resource key. No prices are derived here. */
  readonly resourcesTraded: Readonly<Record<string, number>>;
  /** When the last trade happened. */
  readonly lastTradeAt: number | null;
  /** The server's first-time flag, untouched. */
  readonly firstTime: unknown;
}

/** Read the market state, or `null` when the save has no market keys. */
export function marketState(world: WorldSnapshot): MarketState | null {
  const map = record(world.maps[0]);
  const state = world.privateState;
  const present =
    (map !== null &&
      (has(map, 'numTradesDone') ||
        has(map, 'resourcesTraded') ||
        has(map, 'timestampLastTrade'))) ||
    has(state, 'marketPlaceFirstTime');
  if (!present) return null;
  return {
    tradesDone: map ? number(map['numTradesDone']) : null,
    resourcesTraded: map ? numbers(map['resourcesTraded']) : {},
    lastTradeAt: map ? number(map['timestampLastTrade']) : null,
    firstTime: has(state, 'marketPlaceFirstTime') ? state['marketPlaceFirstTime'] : null,
  };
}

/* -------------------------------------------------------------------------
 * Premium
 * ---------------------------------------------------------------------- */

/** The premium state, as the server keeps it. */
export interface PremiumState {
  /** When the current premium period ends. */
  readonly endsAt: number;
}

/** Read the premium expiry, or `null` when there is none to read. */
export function premiumState(world: WorldSnapshot): PremiumState | null {
  const state = world.privateState;
  if (!has(state, 'timeStampEndPremium')) return null;
  const endsAt = number(state['timeStampEndPremium']);
  return endsAt === null ? null : { endsAt };
}

/* -------------------------------------------------------------------------
 * Bonuses
 * ---------------------------------------------------------------------- */

/** The daily and weekly bonus state, as the server keeps it. */
export interface BonusState {
  /** The index of the next weekly reward. */
  readonly weeklyIndex: number | null;
  /** When the Monday bonus was last collected. */
  readonly mondayBonusAt: number | null;
  /** The id of the next daily bonus. */
  readonly nextBonusId: number | null;
  /** When the daily bonus was last collected. */
  readonly lastBonusAt: number | null;
}

const BONUS_KEYS = [
  'weeklyRewardIndex',
  'timeStampMondayBonus',
  'bonusNextId',
  'timestampLastBonus',
] as const;

/** Read the bonus state, or `null` when the save has no bonus keys. */
export function bonusState(world: WorldSnapshot): BonusState | null {
  const state = world.privateState;
  if (!BONUS_KEYS.some((key) => has(state, key))) return null;
  return {
    weeklyIndex: number(state['weeklyRewardIndex']),
    mondayBonusAt: number(state['timeStampMondayBonus']),
    nextBonusId: number(state['bonusNextId']),
    lastBonusAt: number(state['timestampLastBonus']),
  };
}

/* -------------------------------------------------------------------------
 * Quests
 * ---------------------------------------------------------------------- */

/** The server's quest progress record. */
export interface QuestProgressState {
  /** The best difficulty reached, by quest index. */
  readonly ranks: Readonly<Record<string, number>>;
  /** The quests whose completion reward was already granted. */
  readonly awarded: readonly string[];
}

/** The quest state, gathered from the places the server actually writes. */
export interface QuestState {
  /** The server's own progress record. */
  readonly progress: QuestProgressState | null;
  /** The timestamps the server recorded, by quest. */
  readonly times: Readonly<Record<string, number>>;
  /** The current mission's id. */
  readonly currentMissionId: number | null;
  /** The current mission's variables. */
  readonly currentQuestVars: Readonly<Record<string, unknown>> | null;
  /** The index of the highest unlocked quest. */
  readonly unlockedIndex: number | null;
  /** The best rank reached, by quest index — from `privateState`. */
  readonly ranks: Readonly<Record<string, number>>;
}

const QUEST_PRIVATE_KEYS = ['questProgress', 'unlockedQuestIndex', 'questsRank'] as const;
const QUEST_MAP_KEYS = ['questTimes', 'idCurrentMission', 'currentQuestVars'] as const;

/** Read a quest progress record, without inventing ranks or awarded quests. */
function questProgressState(value: unknown): QuestProgressState | null {
  const source = record(value);
  if (!source) return null;
  return { ranks: numbers(source['ranks']), awarded: strings(source['awarded']) };
}

/** Read the quest state, or `null` when the save has no quest keys. */
export function questState(world: WorldSnapshot): QuestState | null {
  const state = world.privateState;
  const map = record(world.maps[0]);
  const present =
    QUEST_PRIVATE_KEYS.some((key) => has(state, key)) ||
    (map !== null && QUEST_MAP_KEYS.some((key) => has(map, key)));
  if (!present) return null;
  return {
    progress: has(state, 'questProgress') ? questProgressState(state['questProgress']) : null,
    times: map ? numbers(map['questTimes']) : {},
    currentMissionId: map ? number(map['idCurrentMission']) : null,
    currentQuestVars: map ? record(map['currentQuestVars']) : null,
    unlockedIndex: number(state['unlockedQuestIndex']),
    ranks: numbers(state['questsRank']),
  };
}

/* -------------------------------------------------------------------------
 * The active (authoritative) quest
 * ---------------------------------------------------------------------- */

/** One ledger element of the active quest, as the server stores it. */
export interface ActiveQuestElement {
  /** Remaining hit points, seeded from the content by the server. */
  readonly hp: number;
  /** Whether the server still considers the element alive. */
  readonly alive: boolean;
}

/**
 * The active quest, as the server owns it.
 *
 * A bare `{ questId }` seed has no ledger and reads as an empty one: it can
 * never prove a kill or a counter, so nothing here can be mistaken for the
 * server's authoritative state.
 */
export interface ActiveQuestStateView {
  /** The quest id, when the server wrote a string one. */
  readonly questId: string | null;
  /** The server-owned counters, read from where the save keeps them. */
  readonly counters: Readonly<Record<string, number>>;
  /** The engagement ledger's elements, by ref. */
  readonly elements: Readonly<Record<string, ActiveQuestElement>>;
  /** The dedupe keys of the events the server has accepted. */
  readonly events: readonly string[];
  /** The team the server bound to this quest, when one was accepted. */
  readonly team?: Army;
  /** The server's remaining mission seconds, or null when the quest has no timer. */
  readonly timeRemaining: number | null;
}

/**
 * Read the active quest, or `null` when the save has none.
 *
 * This is a selector only: it copies the server's values and invents nothing.
 */
export function activeQuestState(world: WorldSnapshot): ActiveQuestStateView | null {
  const stored = record(world.privateState['activeQuest']);
  if (!stored) return null;
  const script = record(stored['script']);
  const ledger = record(stored['ledger']);
  const elements = record(ledger?.['elements']);
  const view: Record<string, ActiveQuestElement> = {};
  if (elements) {
    for (const [ref, value] of Object.entries(elements)) {
      const element = record(value);
      const hp = element ? number(element['hp']) : null;
      if (hp === null || !element) continue;
      view[ref] = { hp, alive: flag(element['alive']) };
    }
  }
  const team = armyOf(stored['team']);
  const remaining = number(stored['timeRemaining']);
  return {
    questId: typeof stored['questId'] === 'string' ? stored['questId'] : null,
    timeRemaining: remaining === null ? null : Math.max(0, remaining),
    counters: script ? numbers(script['counters']) : {},
    elements: view,
    events: ledger ? strings(ledger['events']) : [],
    ...(team !== undefined ? { team } : {}),
  };
}

/**
 * The last quest reward the server granted, as a view of the save.
 *
 * This is a reading of a past grant, not a reward authority: nothing pays
 * from it. A reconnecting client uses it to rebuild the result screen
 * without replaying `end_quest`. An absent or malformed receipt reads as
 * `null` — the client never fabricates a row the server did not write.
 */
export interface LastQuestRewardView {
  /** The authoritative quest id that was completed. */
  readonly questId: string;
  /** The rank the server recorded for the win. */
  readonly rank: number;
  /** The exact rows the wallet received. */
  readonly rewards: readonly Reward[];
}

/** Read the persisted reward receipt, or `null` when there is none. */
export function lastQuestReward(world: WorldSnapshot): LastQuestRewardView | null {
  const stored = record(world.privateState['lastQuestReward']);
  if (!stored) return null;
  const questId = stored['questId'];
  const rank = number(stored['rank']);
  const rawRewards = stored['rewards'];
  if (typeof questId !== 'string' || questId === '' || rank === null || !Array.isArray(rawRewards)) {
    return null;
  }
  const allowed = new Set<string>(RESOURCE_ORDER);
  const rewards: Reward[] = [];
  for (const entry of rawRewards) {
    const row = record(entry);
    const resource = row?.['resource'];
    const amount = row ? number(row['amount']) : null;
    if (!row || typeof resource !== 'string' || !allowed.has(resource) || amount === null) {
      return null;
    }
    rewards.push({ resource: resource as Reward['resource'], amount });
  }
  return { questId, rank, rewards };
}

/* -------------------------------------------------------------------------
 * Production
 * ---------------------------------------------------------------------- */

/**
 * A building's production state, as the server keeps it in the map item's
 * attribute bag.
 *
 * Every value is the server's own. A missing or malformed one reads as null —
 * the client never fills in a period, a multiplier or a countdown of its own.
 */
export interface ProductionStateView {
  /** The chosen 1-based period, or null before one has been chosen. */
  readonly period: number | null;
  /** When the server started the current cycle, or null if it never did. */
  readonly startedAt: number | null;
  /** The uncollected base amount, or null when absent. */
  readonly collect: number | null;
  /** How many units fit inside, or null when absent. */
  readonly unitCapacity: number | null;
  /** How many units are inside, or null when absent. */
  readonly unitsInside: number | null;
  /** The resource produced, or null when absent. */
  readonly collectType: string | null;
}

/**
 * Read a building's production state, or null when there is no such item.
 *
 * An empty attribute bag is a fresh building, not an invented cycle: its
 * fields read as null and the selector decides what, if anything, to show.
 */
export function productionState(
  world: WorldSnapshot,
  isoId: number | null,
): ProductionStateView | null {
  if (isoId === null) return null;
  const tuple = world.maps[0]?.items?.[String(isoId)];
  if (!tuple) return null;
  const attrs = record(tuple[6]);
  return {
    period: attrs ? number(attrs['cp']) : null,
    startedAt: attrs ? number(attrs['lastAccruedAt']) : null,
    collect: attrs ? number(attrs['collect']) : null,
    unitCapacity: attrs ? number(attrs['unitCapacity']) : null,
    unitsInside: attrs ? number(attrs['unitsInside']) : null,
    collectType:
      attrs && typeof attrs['collectType'] === 'string' ? attrs['collectType'] : null,
  };
}

/* -------------------------------------------------------------------------
 * Expansion
 * ---------------------------------------------------------------------- */

/**
 * The tile ids of the expansions the server's save owns.
 *
 * The list is the **server's**: the world endpoint sends the map verbatim and
 * the applier appends to it when a purchase is accepted. This selector only
 * copies the finite numbers out of it. A save with no `expansions` field — or
 * an older world with no map at all — owns nothing, so the safe default is an
 * empty list rather than an invented set of tiles.
 */
export function ownedExpansions(world: WorldSnapshot): number[] {
  const map = record(world.maps[0]);
  return map ? numberList(map['expansions']) : [];
}

/* -------------------------------------------------------------------------
 * Assault result, battle history and the combat HUD
 * ---------------------------------------------------------------------- */

/**
 * The server's answer to the last assault, as a view of the save.
 *
 * The outcome is the `lastAssaultWon` flag the applier writes when it settles
 * `end_attack`. A richer `lastAssaultResult` receipt may carry the exact loot
 * rows and army counts the server paid; the client reads them when present and
 * draws **no** loot row at all when the server did not write one. This is a
 * reading of a past answer, never a second result authority: nothing pays
 * from it, and re-opening the popup cannot grant a resource.
 */
export interface AssaultResultView {
  /** Whether the server says the assault was won. */
  readonly won: boolean;
  /** Whether the server wrote a structured receipt, not only the win flag. */
  readonly settled: boolean;
  /** The exact rows the server recorded, in the wire's resource vocabulary. */
  readonly loot: readonly Reward[];
  /** The server's surviving unit count, or null when it did not publish one. */
  readonly unitsAlive: number | null;
  /** The server's lost unit count, or null when it did not publish one. */
  readonly unitsDead: number | null;
  /** The opponent the server named, or null when it did not. */
  readonly opponent: string | null;
  /** When the server settled the attack, or null when it did not say. */
  readonly recordedAt: number | null;
}

/**
 * Read the last assault result, or `null` when the save has no answer at all.
 *
 * A bare win flag is an honest, if thin, answer: it reads as unsettled with no
 * loot rather than as a fabricated receipt. Malformed rows are dropped, never
 * guessed at.
 */
export function lastAssaultResult(world: WorldSnapshot): AssaultResultView | null {
  const state = world.privateState;
  const stored = record(state['lastAssaultResult']);
  if (!stored && !has(state, 'lastAssaultWon')) return null;
  const win = stored && typeof stored['won'] === 'boolean'
    ? stored['won']
    : flag(state['lastAssaultWon']);

  const allowed = new Set<string>(RESOURCE_ORDER);
  const loot: Reward[] = [];
  if (Array.isArray(stored?.['rewards'])) {
    for (const entry of stored!['rewards'] as unknown[]) {
      const row = record(entry);
      const resource = row?.['resource'];
      const amount = row ? number(row['amount']) : null;
      if (!row || typeof resource !== 'string' || !allowed.has(resource) || amount === null) {
        continue;
      }
      loot.push({ resource: resource as Reward['resource'], amount });
    }
  }

  return {
    won: win,
    settled: stored !== null,
    loot,
    unitsAlive: stored ? number(stored['unitsAlive']) : null,
    unitsDead: stored ? number(stored['unitsDead']) : null,
    opponent: stored && typeof stored['opponent'] === 'string' ? stored['opponent'] : null,
    recordedAt: stored ? number(stored['recordedAt']) : null,
  };
}

/** One row of the battle history, with only the fields the server wrote. */
export interface AssaultHistoryEntry {
  /** The opponent, when the server named one. */
  readonly opponent: string | null;
  /** The outcome, when the server recorded one. */
  readonly won: boolean | null;
  /** The gold, when the server recorded an amount. */
  readonly gold: number | null;
  /** When the server recorded the battle, when it said. */
  readonly at: number | null;
}

/** The server's battle history and attack-reset timestamp. */
export interface AssaultHistoryView {
  /** The attacks the player sent. */
  readonly sent: readonly AssaultHistoryEntry[];
  /** The attacks the player received. */
  readonly received: readonly AssaultHistoryEntry[];
  /** The server's attack-reset timestamp, or null when it has none. */
  readonly resetAt: number | null;
}

/** Copy only rows that carry at least one readable, server-owned field. */
function historyRows(value: unknown): AssaultHistoryEntry[] {
  if (!Array.isArray(value)) return [];
  const out: AssaultHistoryEntry[] = [];
  for (const raw of value) {
    const row = record(raw);
    if (!row) continue;
    const opponent = typeof row['opponent'] === 'string' ? row['opponent'] : null;
    const won = typeof row['won'] === 'boolean' ? row['won'] : null;
    const gold = number(row['gold']);
    const at = number(row['at']);
    if (opponent === null && won === null && gold === null && at === null) continue;
    out.push({ opponent, won, gold, at });
  }
  return out;
}

/**
 * Read the battle history, or `null` when the save has no history keys.
 *
 * The lists are the server's (`attacksSent` and `attacksReceived` in
 * `privateState`); this selector only copies the finite and typed fields out
 * of them. An unreadable row is skipped rather than turned into an invented
 * battle.
 */
export function assaultHistory(world: WorldSnapshot): AssaultHistoryView | null {
  const state = world.privateState;
  const present =
    has(state, 'attacksSent') || has(state, 'attacksReceived') || has(state, 'tsAttacksReset');
  if (!present) return null;
  return {
    sent: historyRows(state['attacksSent']),
    received: historyRows(state['attacksReceived']),
    resetAt: number(state['tsAttacksReset']),
  };
}

/**
 * The assault countdown, from the server's `tsAttacksReset`.
 *
 * The remaining seconds are a presentation of the server's timestamp against
 * the caller's clock; the server decides when the attacks actually reset.
 */
export interface AssaultCountdownView {
  /** The server's reset timestamp. */
  readonly endsAt: number;
  /** Whole seconds left, clamped at zero. Presentation only. */
  readonly secondsRemaining: number;
}

/** Read the assault countdown, or `null` when the server published no reset. */
export function assaultCountdown(
  world: WorldSnapshot,
  now: number,
): AssaultCountdownView | null {
  const endsAt = number(world.privateState['tsAttacksReset']);
  if (endsAt === null) return null;
  return { endsAt, secondsRemaining: Math.max(0, endsAt - now) };
}

/** The defensive strategy the server owns. */
export interface BattleOptionsView {
  /** The 1-based strategy from `privateState.strategy`. */
  readonly selected: number;
}

/**
 * Read the selected defensive strategy, or `null` when the server published
 * no usable one. The four strategy names and descriptions are the client's own
 * text; the **choice** is entirely the server's.
 */
export function battleOptions(world: WorldSnapshot): BattleOptionsView | null {
  const selected = number(world.privateState['strategy']);
  if (selected === null || !Number.isInteger(selected) || selected < 1 || selected > 4) {
    return null;
  }
  return { selected };
}

/** One special-attack portrait's charge and ready state, as the server owns it. */
export interface SpecialAttackChargeView {
  /** The rules model's class name, which names the portrait. */
  readonly id: SpecialAttackClass;
  /** The rules model's shape, used only to describe the portrait. */
  readonly shape: SpecialAttackShape;
  /** The server's ready flag, or null when it published none. */
  readonly ready: boolean | null;
  /** The server's charge fraction, or null when it published none. */
  readonly charge: number | null;
  /** Whether the server marked this as the limit-gated portrait. */
  readonly limit: boolean;
}

/**
 * Read the special-attack charge HUD, in the rules' own class order.
 *
 * Only classes the server actually reports are listed, and only its own
 * ready/charge values are copied. The rules model supplies the vocabulary
 * (class and shape); it is never run here to invent a charge or a "ready"
 * state. A save with no charge record yields an empty HUD, not a full set of
 * fabricated portraits.
 */
export function specialAttackHud(world: WorldSnapshot): SpecialAttackChargeView[] {
  const charges = record(world.privateState['specialAttackCharges']);
  if (!charges) return [];
  const out: SpecialAttackChargeView[] = [];
  for (const id of SPECIAL_ATTACK_CLASSES) {
    const row = record(charges[id]);
    if (!row) continue;
    const raw = number(row['charge']);
    out.push({
      id,
      shape: SPECIAL_ATTACKS[id].shape,
      ready: typeof row['ready'] === 'boolean' ? row['ready'] : null,
      charge: raw === null ? null : Math.min(1, Math.max(0, raw)),
      limit: flag(row['limit']),
    });
  }
  return out;
}
