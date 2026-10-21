
/**
 * The command applier — the server's own answer to a command.
 *
 * The upstream server implements **five** of the commands that grant
 * anything, and it grants them by believing the client:
 *
 * - `collect` resets the building's timer and grants nothing. The **client**
 *   computes the amount and declares it in the `res` vector, so the player
 *   collects whatever they say.
 * - `complete_goal` prints a line. The goal's reward is never granted by the
 *   server; the client credits itself.
 * - `win_daily_bonus` takes the bonus index and the item id **from the
 *   client** and grants it. A player can claim any bonus, any day, and any
 *   unit, for ever.
 * - `end_attack` trusts the whole battle result the client sends.
 * - `end_quest` trusts the client's win.
 *
 * This module is the opposite: every grant is computed from the **server's**
 * own state, through the rules engine, with a once-only guard.
 *
 * ## The save document
 *
 * The upstream's save has 12 `playerInfo`, 28 `maps[]` and 47 `privateState`
 * fields, and the upstream's `privateState` is the record of what the
 * **client** has done. The server needs a little more than that:
 *
 * - the production state of each building, because the upstream never kept
 *   it — the client did, and the client is not trusted here;
 * - the goal runtime state, because the upstream never had one.
 *
 * Those live in the item's own attribute bag and in `privateState`, under the
 * names this module defines. A migration adds them to an upstream save.
 */
import { Random, hashSeed } from '@swl/rules';
import {
  awardGoal,
  allianceDailyBonus,
  createGoalState,
  dailyBonusReadiness,
  dailyBonusReward,
  mondayBonusReward,
  mondayBonusState,
  isDue,
  advanceTutorial,
  tutorialState,
  TUTORIAL_STATE_KEY,
  isPremiumActive,
  premiumExpiry,
  type ProductionCycle,
  collect as collectProduction,
  awardQuest,
  emptyQuestProgress,
  applyCommandCost,
  assaultLoot,
  canPlaceBuilding,
  canUpgrade,
  upgradeCost,
  conquestGold,
  stolenGold,
  speedUpCost,
  type CollectPeriods,
  type DailyBonusRules,
  type GoalRuntimeState,
  type QuestProgress,
} from '@swl/rules';

import type { CommandApplier, CommandOutcome, ShimWorld } from './shim.ts';

export type { CommandApplier, CommandOutcome, ShimWorld } from './shim.ts';

/** The map item tuple, as the upstream stores it. */
export type MapItemTuple = [
  /** The content item id. */
  itemId: number,
  /** The x position. */
  x: number,
  /** The y position. */
  y: number,
  /** The building's timestamp. */
  timestamp: number,
  /** The orientation. */
  orientation: number,
  /** The units inside. */
  store: unknown[],
  /** The attribute bag. */
  attrs: Record<string, unknown>,
  /** The owning player. 1 is the owner. */
  player: number,
];

/**
 * The production state of a building.
 *
 * The upstream keeps none of this, so it lives in the item's attribute bag
 * under these names.
 */
export interface BuildingState {
  /** The accumulated production, not yet collected. */
  collect: number;
  /** How many units fit inside. */
  unitCapacity: number;
  /** How many units are inside right now. */
  unitsInside: number;
  /** Which resource the building produces: `w`, `o`, `s` or `c`. */
  collectType: string;
  /** The collect period index, 1-based. */
  cp: number;
  /** When the production last accrued, in seconds. */
  lastAccruedAt: number;
}

/** The keys the production state uses inside the attribute bag. */
export const BUILDING_STATE_KEYS = [
  'collect',
  'unitCapacity',
  'unitsInside',
  'collectType',
  'cp',
  'lastAccruedAt',
] as const;

/** The private-state key the goal runtime state uses. */
/**
 * The period a building collects on when it does not offer the choice.
 *
 * The client's own multiplier for a building that is not
 * "multi-collectable" is 1, and that is the **one hour** period.
 */
export const DEFAULT_COLLECT_PERIOD = 2;

export const GOAL_STATE_KEY = 'goalState';
/** The private-state key the quest progress uses. */
export const QUEST_PROGRESS_KEY = 'questProgress';

/**
 * What the server's own simulation of an attack says.
 *
 * The client sends its own battle result with the `end_attack` command, and
 * the upstream believes it (finding F5). The server's answer comes from
 * `simulateBattle`, and the client's claim is only ever *compared* with it.
 */
export interface BattleResolution {
  /** Did the attackers win, by the server's own simulation? */
  won: boolean;
  /** The victim's town hall gold, which the loot percentage applies to. */
  victimTownHallGold: number;
  /** The victim's level, which a conquest's fixed gold is based on. */
  victimLevel: number;
  /** The attacker's level, which sets the gold band. */
  attackerLevel: number;
  /** Whether the attack was a conquest. */
  conquest: boolean;
  /** The XP the kills are worth. */
  xp: number;
}

/**
 * Resolves an attack from the server's own state.
 *
 * The claim is the client's battle result, and it is passed in only so the
 * server can compare it. Nothing reads it to decide anything.
 */
export type BattleResolver = (world: ShimWorld, claim: unknown) => BattleResolution;

/** What the applier needs to know about a content item. */
export interface ApplierItem {
  id: number;
  name: string;
  /** The build cost, by resource key. */
  costs: Record<string, number>;
  /** The cash price of one unit trained in this building. */
  costUnitCash: number;
  /** Seconds to construct. */
  buildTime: number;
  /** Seconds to train one unit. */
  trainingTime: number;
  /** How many friend clicks the build needs. */
  clicksToBuild: number;
  /** The minimum player level. */
  minLevel: number;
  /** How many units fit inside. */
  unitCapacity: number;
  /** The population it costs. */
  population: number;
  /** The maximum copies of this exact building. -1 means unlimited. */
  buildingLimitSameId: number;
  /** The maximum copies per sub-category. -1 means unlimited. */
  buildingLimitSameScf: number;
  /** The sub-category, for the per-sub-category limit. */
  subcategoryId: number;
  /** The footprint, in tiles. */
  width: number;
  height: number;
  /** The units this building can train. */
  trainsIds: number[];
  /** The next tier, if any. */
  upgradesTo: number | null;
  /** The cash cost of a premium upgrade to this item, if it has one. */
  premiumUpgradeCosts: Record<string, number>;
}

/** What the applier needs. */
export interface ApplierDeps {
  /** The clock, in seconds. */
  now: () => number;
  /** The player's time-zone offset, in hours. */
  tzOffsetHours: number;
  /** The collect periods: the minutes and the multipliers. */
  collectPeriods: CollectPeriods;
  /** The daily bonus rules. */
  dailyBonus: DailyBonusRules;
  /** How much a goal's reward is worth. */
  goalRewardGold?: number;
  /** The content items, by id, for the costs and the placement rules. */
  items?: Map<number, ApplierItem>;
  /** The population rules, for the population check. */
  populationRules?: {
    startMaxPopulation: number;
    maxPopulationCap: number;
    maxPopulationPerLevel: number;
  };
  /** The hurry-up rules, for finishing a building early. */
  speedup?: { minRemainingMs: number; cost: number };
  /** The discount the reactivate-a-wonder price carries. */
  reactivateWonderDiscount?: number;
  /** Resolves an attack from the server's own simulation. */
  resolveBattle?: BattleResolver;
  /** The weekly bonus's three rewards. */
  mondayBonus?: { rewards: { type: string; value: number | number[] }[] };
  /** The alliance daily bonus's tiers. */
  allianceBonus?: { rewards: { members?: number; type: string; value: number }[] };
  /** How many members the player's alliance has. */
  allianceMemberCount?: number;
  /** The premium packages, for the purchase and the expiry. */
  premiumPackages?: { price: number; time: number }[];
  /** The player's level table: the XP each level needs and its reward. */
  levels?: { index: number; exp_required: number; reward_amount: number; reward_type: string }[];
}

/** The map's items, keyed by iso id. */
export function mapItems(map: Record<string, unknown> | undefined): Record<string, MapItemTuple> {
  const items = map?.['items'];
  if (!items || typeof items !== 'object') return {};
  return items as Record<string, MapItemTuple>;
}

/** The building's production state, from its attribute bag. */
export function buildingState(attrs: Record<string, unknown>): BuildingState {
  const number = (key: string, fallback = 0): number => {
    const value = attrs[key];
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
  };
  return {
    collect: number('collect'),
    unitCapacity: number('unitCapacity'),
    unitsInside: number('unitsInside'),
    collectType: typeof attrs['collectType'] === 'string' ? attrs['collectType'] : 'w',
    cp: number('cp', 1),
    lastAccruedAt: number('lastAccruedAt'),
  };
}

/** Write the production state back into the attribute bag. */
export function writeBuildingState(
  attrs: Record<string, unknown>,
  state: BuildingState,
): void {
  attrs['collect'] = state.collect;
  attrs['unitCapacity'] = state.unitCapacity;
  attrs['unitsInside'] = state.unitsInside;
  attrs['collectType'] = state.collectType;
  attrs['cp'] = state.cp;
  attrs['lastAccruedAt'] = state.lastAccruedAt;
}

/** The goal runtime state, from the private state. */
export function goalState(privateState: Record<string, unknown>): GoalRuntimeState {
  const stored = privateState[GOAL_STATE_KEY];
  if (!stored || typeof stored !== 'object') return createGoalState();
  return stored as GoalRuntimeState;
}

/** The quest progress, from the private state. */
export function questProgress(privateState: Record<string, unknown>): QuestProgress {
  const stored = privateState[QUEST_PROGRESS_KEY];
  if (!stored || typeof stored !== 'object') return emptyQuestProgress();
  return stored as QuestProgress;
}

/** The player's own map. */
function ownMap(world: ShimWorld): Record<string, unknown> | undefined {
  return world.save.maps[0] as Record<string, unknown> | undefined;
}

/**
 * Create the applier.
 *
 * The applier mutates the world it is given. The caller hands it a **copy**,
 * so a failure part way through leaves the stored save untouched.
 */
export function createApplier(deps: ApplierDeps): CommandApplier {
  return (world, command): CommandOutcome => {
    switch (command.name) {
      case 'place_stored_item':
        return placeCommand(world, command.args, deps);
      case 'push_queue_unit':
      case 'push_queue_unit2':
        return pushQueueUnitCommand(world, command.args, deps);
      case 'pop_queue_unit':
        return popQueueUnitCommand(world, command.args, deps);
      case 'level_up':
        return levelUpCommand(world, command.args, deps);
      case 'upgrade':
        return upgradeCommand(world, command.args, deps);
      case 'buy':
        return buyCommand(world, command.args, deps);
      case 'collect':
        return collectCommand(world, command.args, deps);
      case 'complete_goal':
        return completeGoalCommand(world, command.args, deps);
      case 'complete_tutorial':
        return completeTutorialCommand(world, command.args, deps);
      case 'win_daily_bonus':
        return dailyBonusCommand(world, command.args, deps);
      case 'weekly_reward':
        return weeklyRewardCommand(world, command.args, deps);
      case 'win_alliance_daily_bonus':
        return allianceBonusCommand(world, command.args, deps);
      case 'reset_collect':
        return resetCollectCommand(world, command.args, deps);
      case 'buy_premium_account':
        return buyPremiumCommand(world, command.args, deps);
      case 'finish_building':
        return finishBuildingCommand(world, command.args, deps);
      case 'end_attack':
        return endAttackCommand(world, command.args, deps);
      case 'end_quest':
        // The client may claim a win. The server does not listen: these are
        // resolved from the server's own state by the battle and quest
        // simulators, which are not wired yet. Until they are, the claim is
        // refused rather than honoured.
        return { applied: false, refused: 'not-implemented', world };
      default:
        return { applied: false, refused: 'no-grant', world };
    }
  };
}

/**
 * `end_attack` - the server's own answer to a finished battle.
 *
 * The client sends the whole battle result and the upstream believes it.
 * The server re-simulates the fight from its own seed and computes the
 * loot itself; the client's claim is only compared, never obeyed.
 *
 * The loot rules are the client's (core/battle/Assault.as): the gold
 * comes from the victim's town hall, the XP is 5 per cent of it, and a
 * win with no loot is worth a flat 25 gold.
 */
/**
 * `buy_premium_account` - buy a premium package.
 *
 * The premium is a timestamp in the private state, and the server owns
 * it. Buying while the premium is still running **extends** it, and
 * buying after it has lapsed **starts it fresh** - the upstream's rule,
 * and the client's.
 *
 * The cash cost is computed by the cost table, from the content's
 * `PREMIUM_ACCOUNTS`, so the client cannot name its own price.
 */
function buyPremiumCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const packages = deps.premiumPackages;
  if (!packages || packages.length === 0) {
    return { applied: false, refused: 'not-implemented', world };
  }
  const index = Number(args[0]);
  if (!Number.isInteger(index) || index < 0 || index >= packages.length) {
    return { applied: false, refused: 'no-such-package', world };
  }

  const privateState = world.save.privateState;
  const now = deps.now();
  const current = Number(privateState['timeStampEndPremium'] ?? 0);
  const expiry = premiumExpiry(packages, index, now, current);

  privateState['timeStampEndPremium'] = expiry;
  return { applied: true, world };
}

/**
 * Whether the player has an active premium.
 *
 * The perks are the client's: three attacks a day instead of one, and a
 * share of the rewards in cash.
 */
export function hasActivePremium(
  world: ShimWorld,
  now: number,
): boolean {
  const expiry = Number(world.save.privateState['timeStampEndPremium'] ?? 0);
  return isPremiumActive(expiry, now);
}

function endAttackCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  if (!deps.resolveBattle) {
    // Without the server's own simulation there is no honest answer, and
    // honouring the client's claim would be the cheat.
    return { applied: false, refused: 'not-implemented', world };
  }

  // The client's claim, parsed only so it can be compared.
  let claim: unknown = null;
  const raw = args[0];
  if (typeof raw === 'string') {
    try {
      claim = JSON.parse(raw) as unknown;
    } catch {
      claim = null;
    }
  }

  const resolution = deps.resolveBattle(world, claim);

  // A conquest takes the victim's level times 100
  // (core/battle/Assault.as:252-254).
  const townHallGold = resolution.conquest
    ? conquestGold(resolution.victimLevel)
    : stolenGold(
        resolution.victimTownHallGold,
        resolution.attackerLevel,
        new Random(hashSeed(`${resolution.attackerLevel}:${resolution.victimTownHallGold}`)),
      );

  const loot = assaultLoot({
    won: resolution.won,
    townHallGold,
    xp: resolution.xp,
    attackerLevel: resolution.attackerLevel,
  });

  world.save.privateState['lastAssaultWon'] = resolution.won;

  if (!resolution.won) {
    // A loss earns nothing, but the attack is over.
    return { applied: true, world };
  }

  world.resources = {
    ...world.resources,
    g: (world.resources['g'] ?? 0) + loot.gold,
    x: (world.resources['x'] ?? 0) + loot.xp,
  };
  return { applied: true, world };
}

/** `collect` — the server computes the amount. */
/** The tiles a placed item covers. */
function coveredTiles(tuple: MapItemTuple): { x: number; y: number }[] {
  const tiles: { x: number; y: number }[] = [];
  const width = Number(tuple[6]?.['width'] ?? 1);
  const height = Number(tuple[6]?.['height'] ?? 1);
  for (let dx = 0; dx < width; dx++) {
    for (let dy = 0; dy < height; dy++) {
      tiles.push({ x: Number(tuple[1]) + dx, y: Number(tuple[2]) + dy });
    }
  }
  return tiles;
}

/** The tiles that are already taken. */
function occupiedTiles(items: Record<string, MapItemTuple>): Set<string> {
  const taken = new Set<string>();
  for (const tuple of Object.values(items)) {
    for (const tile of coveredTiles(tuple)) {
      taken.add(`${tile.x},${tile.y}`);
    }
  }
  return taken;
}

/** The player's level. */
function playerLevel(map: Record<string, unknown> | undefined): number {
  const level = map?.['level'];
  return typeof level === 'number' ? level : 1;
}

/**
 * The player's population.
 *
 * The used population is the sum of the placed items' population, and the
 * ceiling grows with the level (packages/rules/src/economy.ts).
 */
function populationOf(
  items: Record<string, MapItemTuple>,
  level: number,
  deps: ApplierDeps,
): { used: number; max: number } {
  let used = 0;
  for (const tuple of Object.values(items)) {
    const item = deps.items?.get(Number(tuple[0]));
    used += item?.population ?? 0;
  }
  const rules = deps.populationRules ?? {
    startMaxPopulation: 20,
    maxPopulationCap: 175,
    maxPopulationPerLevel: 3,
  };
  const max = Math.min(
    rules.maxPopulationCap,
    rules.startMaxPopulation + rules.maxPopulationPerLevel * level,
  );
  return { used, max };
}

/** The next free iso id for the map. */
function nextIsoId(world: ShimWorld): number {
  const items = mapItems(ownMap(world));
  let highest = 0;
  for (const key of Object.keys(items)) {
    const id = Number(key);
    if (Number.isFinite(id) && id > highest) highest = id;
  }
  const privateState = world.save.privateState;
  const remembered = Number(privateState['nextIsoId'] ?? 0);
  const next = Math.max(highest + 1, remembered || 0);
  privateState['nextIsoId'] = next + 1;
  return next;
}

/** The outcome of trying to place something. */
type PlacementResult =
  | { ok: true; tuple: MapItemTuple }
  | { ok: false; reason: string };

/**
 * Place a building on the map, if the rules allow it.
 *
 * The rules are the rules engine's `canPlaceBuilding`, plus a free tile.
 */
function placeBuilding(
  world: ShimWorld,
  item: ApplierItem,
  tx: number,
  ty: number,
  orientation: number,
  deps: ApplierDeps,
): PlacementResult {
  const map = ownMap(world);
  const items = mapItems(map);
  const level = playerLevel(map);

  const sameIdCounts: Record<string, number> = {};
  const sameGroupCounts: Record<string, number> = {};
  for (const tuple of Object.values(items)) {
    const placed = deps.items?.get(Number(tuple[0]));
    if (!placed) continue;
    sameIdCounts[String(placed.id)] = (sameIdCounts[String(placed.id)] ?? 0) + 1;
    sameGroupCounts[String(placed.subcategoryId)] =
      (sameGroupCounts[String(placed.subcategoryId)] ?? 0) + 1;
  }

  const population = populationOf(items, level, deps);
  const placement = canPlaceBuilding(
    {
      id: item.id,
      name: item.name,
      costs: item.costs,
      costUnitCash: item.costUnitCash,
      buildTime: item.buildTime,
      trainingTime: item.trainingTime,
      clicksToBuild: item.clicksToBuild,
      minLevel: item.minLevel,
      upgradesTo: null,
      unitCapacity: item.unitCapacity,
      population: item.population,
      buildingLimitSameId: item.buildingLimitSameId,
      buildingLimitSameScf: item.buildingLimitSameScf,
      premiumUpgradeCosts: {},
    },
    {
      level,
      populationUsed: population.used,
      populationMax: population.max,
      sameIdCounts,
      sameGroupCounts,
      subcategoryId: item.subcategoryId,
      hasFreeTile: true,
    },
  );
  if (!placement.ok) {
    return { ok: false, reason: placement.reason };
  }

  // The tile must be free.
  const taken = occupiedTiles(items);
  for (let dx = 0; dx < item.width; dx++) {
    for (let dy = 0; dy < item.height; dy++) {
      if (taken.has(`${tx + dx},${ty + dy}`)) {
        return { ok: false, reason: 'tile-taken' };
      }
    }
  }

  const isoId = nextIsoId(world);
  const attrs: Record<string, unknown> = {
    width: item.width,
    height: item.height,
    collect: 0,
    unitCapacity: item.unitCapacity,
    unitsInside: 0,
    collectType: '',
    cp: 1,
    lastAccruedAt: deps.now(),
    clicked: 0,
  };
  const tuple: MapItemTuple = [item.id, tx, ty, deps.now(), orientation, [], attrs, 1];
  items[String(isoId)] = tuple;
  if (map) map['items'] = items;

  return { ok: true, tuple };
}

/** `place_stored_item` — put a stored building on the map. */
function placeCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const itemId = Number(args[1]);
  const item = deps.items?.get(itemId);
  if (!item) return { applied: false, refused: 'unknown-item', world };
  const tx = Number(args[2]);
  const ty = Number(args[3]);
  if (!Number.isFinite(tx) || !Number.isFinite(ty)) {
    return { applied: false, refused: 'bad-argument', world };
  }
  const orientation = Number(args[6] ?? 0);
  const placed = placeBuilding(world, item, tx, ty, orientation, deps);
  if (!placed.ok) return { applied: false, refused: placed.reason, world };
  return { applied: true, world };
}

/** `buy` — buy a building or a unit and place it. */
function buyCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const itemId = Number(args[1]);
  const item = deps.items?.get(itemId);
  if (!item) return { applied: false, refused: 'unknown-item', world };
  const tx = Number(args[2]);
  const ty = Number(args[3]);
  if (!Number.isFinite(tx) || !Number.isFinite(ty)) {
    return { applied: false, refused: 'bad-argument', world };
  }
  const orientation = Number(args[5] ?? 0);
  const placed = placeBuilding(world, item, tx, ty, orientation, deps);
  if (!placed.ok) return { applied: false, refused: placed.reason, world };
  return { applied: true, world };
}

/**
 * The training queue of a building.
 *
 * The upstream keeps it in the building's attribute bag: `nu` is how many
 * units are queued, `ts` is when the current one started, and `ui` is
 * which unit it is.
 */
interface TrainingQueue {
  /** How many units are queued. */
  queued: number;
  /** When the current unit started, in seconds. 0 when the queue is empty. */
  startedAt: number;
  /** The unit being trained. */
  unitItemId: number;
}

/** Read a building's training queue. */
function readQueue(attrs: Record<string, unknown>): TrainingQueue {
  const queued = Number(attrs['nu'] ?? 0);
  return {
    queued: Number.isFinite(queued) ? queued : 0,
    startedAt: Number(attrs['ts'] ?? 0),
    unitItemId: Number(attrs['ui'] ?? 0),
  };
}

/** Write a building's training queue back. */
function writeQueue(attrs: Record<string, unknown>, queue: TrainingQueue): void {
  if (queue.queued > 0) {
    attrs['nu'] = queue.queued;
    attrs['ts'] = queue.startedAt;
    attrs['ui'] = queue.unitItemId;
  } else {
    delete attrs['nu'];
    delete attrs['ts'];
    delete attrs['ui'];
  }
}

/**
 * `push_queue_unit` and `push_queue_unit2` - start training a unit.
 *
 * The cost is the trained unit's own cost plus the building's cash price
 * for a unit. The client declares both; the server computes them.
 */
function pushQueueUnitCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const tuple = mapItems(ownMap(world))[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };
  const buildingId = tuple[0];
  if (typeof buildingId !== 'number') {
    return { applied: false, refused: 'unknown-building', world };
  }
  const building = deps.items?.get(buildingId);
  if (!building) return { applied: false, refused: 'unknown-building', world };

  // The unit being trained: the one the client named, or the building's
  // first.
  const named = Number(args[1]);
  const unitId =
    Number.isFinite(named) && named > 0 ? named : building.trainsIds[0] ?? 0;
  if (!unitId) return { applied: false, refused: 'nothing-to-train', world };
  const unit = deps.items?.get(unitId);
  if (!unit) return { applied: false, refused: 'unknown-item', world };

  // The cost: the unit's own, plus the building's cash price for a unit.
  const cost: Record<string, number> = { ...unit.costs };
  if (building.costUnitCash > 0) {
    cost['c'] = (cost['c'] ?? 0) + building.costUnitCash;
  }
  const settled = applyCommandCost(world.resources, { cost, gain: {} });
  if (!settled.ok) {
    return { applied: false, refused: settled.reason ?? 'insufficient-resources', world };
  }

  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  const queue = readQueue(attrs);
  queue.queued += 1;
  // Only the FIRST unit in the queue is training; the rest wait.
  if (queue.queued === 1) {
    queue.startedAt = deps.now();
    queue.unitItemId = unitId;
  }
  writeQueue(attrs, queue);

  world.resources = settled.resources;
  return { applied: true, world };
}

/**
 * `pop_queue_unit` - take the finished unit out of the queue.
 *
 * The server checks that the unit is actually finished: the client decides
 * when to pop, and the upstream does not check at all.
 */
function popQueueUnitCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const tuple = mapItems(ownMap(world))[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };
  const buildingId = tuple[0];
  if (typeof buildingId !== 'number') {
    return { applied: false, refused: 'unknown-building', world };
  }
  const building = deps.items?.get(buildingId);
  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  const queue = readQueue(attrs);
  if (queue.queued <= 0) return { applied: false, refused: 'queue-empty', world };

  // The unit must have finished training.
  const trained = deps.items?.get(queue.unitItemId);
  const trainingTime = trained?.trainingTime ?? building?.trainingTime ?? 0;
  if (deps.now() - queue.startedAt < trainingTime) {
    return { applied: false, refused: 'still-training', world };
  }

  queue.queued -= 1;
  if (queue.queued > 0) {
    // The next one starts now.
    queue.startedAt = deps.now();
  }
  writeQueue(attrs, queue);

  return { applied: true, world };
}

/**
 * `level_up` - the player's level rises.
 *
 * The server checks that the player has the XP for the level, and grants
 * the level's reward from the level table.
 */
function levelUpCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const map = ownMap(world);
  const newLevel = Number(args[0]);
  if (!Number.isFinite(newLevel)) {
    return { applied: false, refused: 'bad-argument', world };
  }
  const levels = deps.levels ?? [];
  const row = levels.find((level) => level.index === newLevel);
  if (!row) return { applied: false, refused: 'no-such-level', world };

  const current = playerLevel(map);
  if (newLevel !== current + 1) {
    // The level rises one step at a time.
    return { applied: false, refused: 'not-the-next-level', world };
  }

  const xp = Number(map?.['xp'] ?? 0);
  if (xp < row.exp_required) {
    return { applied: false, refused: 'not-enough-xp', world };
  }

  if (map) map['level'] = newLevel;
  const rewardType = row.reward_type;
  world.resources = {
    ...world.resources,
    [rewardType]: (world.resources[rewardType] ?? 0) + row.reward_amount,
  };
  return { applied: true, world };
}

/**
 * `upgrade` - replace a building with its next tier.
 *
 * The cost is the new building's cost less the refund of the old one
 * (the rules engine's `upgradeCost`), and the new building must fit on
 * free tiles.
 */
function upgradeCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const items = mapItems(ownMap(world));
  const tuple = items[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };
  const oldId = tuple[0];
  if (typeof oldId !== 'number') {
    return { applied: false, refused: 'unknown-building', world };
  }
  const oldBuilding = deps.items?.get(oldId);
  if (!oldBuilding) return { applied: false, refused: 'unknown-building', world };

  const newId = oldBuilding.upgradesTo;
  if (newId === null || newId === undefined) {
    return { applied: false, refused: 'no-upgrade', world };
  }
  const newBuilding = deps.items?.get(newId);
  if (!newBuilding) return { applied: false, refused: 'unknown-item', world };

  const map = ownMap(world);
  const level = playerLevel(map);
  const taken = occupiedTiles(items);
  // The old building's own tiles are free for the upgrade.
  for (const tile of coveredTiles(tuple)) {
    taken.delete(`${tile.x},${tile.y}`);
  }
  let hasFreeTile = true;
  for (let dx = 0; dx < newBuilding.width; dx++) {
    for (let dy = 0; dy < newBuilding.height; dy++) {
      if (taken.has(`${Number(tuple[1]) + dx},${Number(tuple[2]) + dy}`)) {
        hasFreeTile = false;
      }
    }
  }
  const permitted = canUpgrade(newBuilding, level, hasFreeTile);
  if (!permitted.ok) {
    return { applied: false, refused: permitted.reason, world };
  }

  const cost = upgradeCost(
    {
      id: oldBuilding.id,
      name: oldBuilding.name,
      costs: oldBuilding.costs,
      costUnitCash: oldBuilding.costUnitCash,
      buildTime: oldBuilding.buildTime,
      trainingTime: oldBuilding.trainingTime,
      clicksToBuild: oldBuilding.clicksToBuild,
      minLevel: oldBuilding.minLevel,
      upgradesTo: oldBuilding.upgradesTo,
      unitCapacity: oldBuilding.unitCapacity,
      population: oldBuilding.population,
      buildingLimitSameId: oldBuilding.buildingLimitSameId,
      buildingLimitSameScf: oldBuilding.buildingLimitSameScf,
      premiumUpgradeCosts: oldBuilding.premiumUpgradeCosts,
    },
    {
      id: newBuilding.id,
      name: newBuilding.name,
      costs: newBuilding.costs,
      costUnitCash: newBuilding.costUnitCash,
      buildTime: newBuilding.buildTime,
      trainingTime: newBuilding.trainingTime,
      clicksToBuild: newBuilding.clicksToBuild,
      minLevel: newBuilding.minLevel,
      upgradesTo: newBuilding.upgradesTo,
      unitCapacity: newBuilding.unitCapacity,
      population: newBuilding.population,
      buildingLimitSameId: newBuilding.buildingLimitSameId,
      buildingLimitSameScf: newBuilding.buildingLimitSameScf,
      premiumUpgradeCosts: newBuilding.premiumUpgradeCosts,
    },
  );
  const settled = applyCommandCost(world.resources, { cost, gain: {} });
  if (!settled.ok) {
    return { applied: false, refused: settled.reason ?? 'insufficient-resources', world };
  }

  // The building becomes the new tier.
  tuple[0] = newBuilding.id;
  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  attrs['width'] = newBuilding.width;
  attrs['height'] = newBuilding.height;
  attrs['unitCapacity'] = newBuilding.unitCapacity;

  world.resources = settled.resources;
  return { applied: true, world };
}

function collectCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const map = ownMap(world);
  const items = mapItems(map);
  const tuple = items[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };

  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  const state = buildingState(attrs);

  // The production cycle. The player chose a period, the countdown started
  // then, and the collection is due once it has elapsed. The upstream never
  // checks this.
  const period = state.cp > 0 ? state.cp : DEFAULT_COLLECT_PERIOD;
  const cycle: ProductionCycle = {
    period,
    startedAt: state.lastAccruedAt,
  };
  if (!isDue(cycle, deps.collectPeriods, deps.now())) {
    return {
      applied: false,
      refused: 'not-due',
      world,
    };
  }

  // The amount comes from the building's own production state, through the
  // rules engine. The client declares nothing.
  const result = collectProduction(
    {
      collect: state.collect,
      unitCapacity: state.unitCapacity,
      unitsInside: state.unitsInside,
    },
    period,
    deps.collectPeriods,
  );

  if (result.hacked) {
    // More units inside than the capacity: the client is cheating, and
    // nothing is collected. The upstream grants this happily.
    return { applied: false, refused: 'over-capacity', world };
  }

  const resource = state.collectType;
  world.resources = {
    ...world.resources,
    [resource]: (world.resources[resource] ?? 0) + result.amount,
  };

  // The production is reset and the countdown restarts.
  writeBuildingState(attrs, {
    ...state,
    collect: 0,
    cp: period,
    lastAccruedAt: deps.now(),
  });
  tuple[3] = deps.now();

  return { applied: true, world };
}

/** `complete_goal` — the server checks its own goal state. */
function completeGoalCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const goalId = Number(args[0]);
  if (!Number.isFinite(goalId)) {
    return { applied: false, refused: 'bad-argument', world };
  }
  const privateState = world.save.privateState;
  const state = goalState(privateState);
  const award = awardGoal(state, goalId);
  if (!award.ok) {
    // Either the goal is not complete, or it was already awarded. The
    // client's claim changes nothing.
    return { applied: false, refused: award.reason, world };
  }
  privateState[GOAL_STATE_KEY] = award.state;
  const gold = deps.goalRewardGold ?? 10;
  world.resources = { ...world.resources, g: (world.resources['g'] ?? 0) + gold };
  return { applied: true, world };
}

/** `win_daily_bonus` — the server computes the day and the reward. */
/**
 * `complete_tutorial` - record how far the player has got in the
 * tutorial.
 *
 * The tutorial is a scripted sequence of pointers, and the client walks
 * it. The server owns **which steps exist**, so a client cannot invent
 * one, and **how far the player has got**, which is the furthest step
 * reached - the tutorial can be walked backwards, and the furthest step
 * is the one that counts.
 *
 * The order is the client's, because the tutorial grants nothing by
 * itself: it points at the actions, and the actions are commands the
 * server already checks.
 */
function completeTutorialCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const step = Number(args[0]);
  if (!Number.isFinite(step)) {
    return { applied: false, refused: 'bad-argument', world };
  }
  const privateState = world.save.privateState;
  const advanced = advanceTutorial(tutorialState(privateState), step);
  if (!advanced.ok) {
    return { applied: false, refused: advanced.reason, world };
  }
  privateState[TUTORIAL_STATE_KEY] = advanced.state;
  return { applied: true, world };
}

function dailyBonusCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const privateState = world.save.privateState;
  const lastBonusAt = Number(privateState['timestampLastBonus'] ?? 0);
  const readiness = dailyBonusReadiness(lastBonusAt, deps.now(), deps.tzOffsetHours);
  if (!readiness.ready) {
    // The client may claim the bonus again; the server's own clock says no.
    return { applied: false, refused: 'not-ready', world };
  }

  // The bonus index is the server's: the client's `args[1]` is ignored.
  const bonusNextId = Number(privateState['bonusNextId'] ?? 0);
  const nextId = bonusNextId >= 5 ? 1 : bonusNextId + 1;
  const reward = dailyBonusReward(deps.dailyBonus, nextId);

  privateState['timestampLastBonus'] = deps.now();
  privateState['bonusNextId'] = nextId;

  if (reward.gold > 0) {
    world.resources = {
      ...world.resources,
      g: (world.resources['g'] ?? 0) + reward.gold,
    };
  }
  return { applied: true, world };
}

/**
 * `reset_collect` — re-activating a depleted wonder.
 *
 * The client computes the price and **declares** it: `CmdResetCollect` takes
 * the cash amount as a constructor argument and puts it in the delta
 * (commands/CmdResetCollect.as:12-14). The server computes it instead:
 *
 * ```
 * cashToReactivate = building.costs["c"] * REACTIVATE_WONDER_DISCOUNT
 * ```
 *
 * (core/isoengine/delegates/buildings/WonderDelegate.as:50-51)
 */
function resetCollectCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const tuple = mapItems(ownMap(world))[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };
  const itemId = tuple[0];
  if (typeof itemId !== 'number') return { applied: false, refused: 'unknown-building', world };

  const item = deps.items?.get(itemId);
  const base = item?.costs?.['c'] ?? 0;
  const discount = deps.reactivateWonderDiscount ?? 0.5;
  const cash = Math.ceil(base * discount);
  if (cash <= 0) return { applied: false, refused: 'not-reactivatable', world };

  const available = world.resources['c'] ?? 0;
  if (available < cash) {
    return { applied: false, refused: 'insufficient-resources', world };
  }
  world.resources = { ...world.resources, c: available - cash };

  // The collection is emptied and the timer restamped.
  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  const state = buildingState(attrs);
  writeBuildingState(attrs, { ...state, collect: 0, lastAccruedAt: deps.now() });
  tuple[3] = deps.now();

  return { applied: true, world };
}

/**
 * `finish_building` — hurrying a build up.
 *
 * The cost is the speed-up price, which the rules engine computes from the
 * time that is left. It is charged here rather than in the cost table,
 * because it depends on the building's own state and not on the content.
 */
function finishBuildingCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const isoId = String(args[0] ?? '');
  const tuple = mapItems(ownMap(world))[isoId];
  if (!tuple) return { applied: false, refused: 'unknown-building', world };
  const itemId = tuple[0];
  if (typeof itemId !== 'number') return { applied: false, refused: 'unknown-building', world };

  const item = deps.items?.get(itemId);
  if (!item) return { applied: false, refused: 'unknown-building', world };

  const startedAt = tuple[3];
  if (typeof startedAt !== 'number') {
    return { applied: false, refused: 'not-building', world };
  }
  const elapsedMs = Math.max(0, (deps.now() - startedAt) * 1000);
  const remainingMs = Math.max(0, item.buildTime * 1000 - elapsedMs);

  const rules = deps.speedup ?? { minRemainingMs: 10_000, cost: 2 };
  const cost = speedUpCost(remainingMs, rules);
  if (cost === null) {
    // The build is already too far along to hurry. The client offers a
    // speed-up only when more than `minRemainingMs` is left.
    return { applied: false, refused: 'too-late-to-speed-up', world };
  }

  const available = world.resources['c'] ?? 0;
  if (available < cost) {
    return { applied: false, refused: 'insufficient-resources', world };
  }
  world.resources = { ...world.resources, c: available - cost };

  // The build is finished now.
  tuple[3] = deps.now();
  const attrs = (tuple[6] ??= {}) as Record<string, unknown>;
  attrs['clicked'] = (Number(attrs['clicked'] ?? 0) + 1);

  return { applied: true, world };
}

/**
 * The player's LOCAL day of the week, 0 for Sunday.
 *
 * The client reads `Date.getDay()`, so the week day is the player's
 * local one and not UTC's. The server has to shift by the player's
 * offset to agree with it.
 */
export function localDayOfWeek(now: number, tzOffsetHours: number): number {
  return new Date((now + tzOffsetHours * 3600) * 1000).getUTCDay();
}

/** The player's LOCAL day number, so a day can be compared. */
export function localDayNumber(now: number, tzOffsetHours: number): number {
  return Math.floor((now + tzOffsetHours * 3600) / 86400);
}

/**
 * `weekly_reward` - the Monday bonus.
 *
 * It is only ready on a Monday, and only once: the private state's
 * `timeStampMondayBonus` records when it was last collected.
 */
function weeklyRewardCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const rules = deps.mondayBonus;
  if (!rules) return { applied: false, refused: 'not-implemented', world };

  const privateState = world.save.privateState;
  const now = deps.now();
  const today = localDayNumber(now, deps.tzOffsetHours);
  const lastCollected = privateState['timeStampMondayBonus'];
  const lastDay =
    typeof lastCollected === 'number' && lastCollected > 0
      ? localDayNumber(lastCollected, deps.tzOffsetHours)
      : null;

  const state = mondayBonusState(localDayOfWeek(now, deps.tzOffsetHours), lastDay, today);
  if (state !== 'ready') {
    // Either it is not Monday, or it was already collected.
    return { applied: false, refused: state, world };
  }

  const index = Number(privateState['weeklyRewardIndex'] ?? 0);
  const reward = mondayBonusReward(rules, index);

  privateState['timeStampMondayBonus'] = now;
  privateState['weeklyRewardIndex'] = index + 1;

  if (reward.type === 'g' && typeof reward.value === 'number') {
    world.resources = { ...world.resources, g: (world.resources['g'] ?? 0) + reward.value };
  } else if (reward.type === 'c' && typeof reward.value === 'number') {
    world.resources = { ...world.resources, c: (world.resources['c'] ?? 0) + reward.value };
  }
  // A unit reward goes into the store, which the store's own state holds.

  return { applied: true, world };
}

/**
 * `win_alliance_daily_bonus` - the alliance's daily bonus.
 *
 * The tier comes from the member count, and it is granted once a day.
 * The upstream credits the bonus but never sets the timer, so the
 * upstream pays it over and over.
 */
function allianceBonusCommand(
  world: ShimWorld,
  args: readonly unknown[],
  deps: ApplierDeps,
): CommandOutcome {
  const rules = deps.allianceBonus;
  if (!rules) return { applied: false, refused: 'not-implemented', world };

  const privateState = world.save.privateState;
  const now = deps.now();
  const today = localDayNumber(now, deps.tzOffsetHours);
  const lastBonus = privateState['timestampLastAllianceBonus'];
  const lastDay =
    typeof lastBonus === 'number' && lastBonus > 0
      ? localDayNumber(lastBonus, deps.tzOffsetHours)
      : null;
  if (lastDay === today) {
    // Already collected today.
    return { applied: false, refused: 'not-ready', world };
  }

  const reward = allianceDailyBonus(rules, deps.allianceMemberCount ?? 0);
  if (!reward) return { applied: false, refused: 'no-tier', world };

  privateState['timestampLastAllianceBonus'] = now;

  if (reward.type === 'g' && typeof reward.value === 'number') {
    world.resources = { ...world.resources, g: (world.resources['g'] ?? 0) + reward.value };
  } else if (reward.type === 'c' && typeof reward.value === 'number') {
    world.resources = { ...world.resources, c: (world.resources['c'] ?? 0) + reward.value };
  }

  return { applied: true, world };
}
