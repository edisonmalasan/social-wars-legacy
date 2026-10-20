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
  createGoalState,
  dailyBonusReadiness,
  dailyBonusReward,
  collect as collectProduction,
  awardQuest,
  emptyQuestProgress,
  assaultLoot,
  conquestGold,
  stolenGold,
  speedUpCost,
  type CollectPeriods,
  type DailyBonusRules,
  type GoalRuntimeState,
  type QuestProgress,
} from '@swl/rules';

import type { CommandApplier, CommandOutcome, ShimWorld } from './shim.ts';

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
  /** The content items, by id, for the costs the content drives. */
  items?: Map<number, { costs: Record<string, number>; buildTime: number }>;
  /** The hurry-up rules, for finishing a building early. */
  speedup?: { minRemainingMs: number; cost: number };
  /** The discount the reactivate-a-wonder price carries. */
  reactivateWonderDiscount?: number;
  /** Resolves an attack from the server's own simulation. */
  resolveBattle?: BattleResolver;
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
      case 'collect':
        return collectCommand(world, command.args, deps);
      case 'complete_goal':
        return completeGoalCommand(world, command.args, deps);
      case 'win_daily_bonus':
        return dailyBonusCommand(world, command.args, deps);
      case 'reset_collect':
        return resetCollectCommand(world, command.args, deps);
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

  // The amount comes from the building's own production state, through the
  // rules engine. The client declares nothing.
  const result = collectProduction(
    {
      collect: state.collect,
      unitCapacity: state.unitCapacity,
      unitsInside: state.unitsInside,
    },
    state.cp,
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

  // The production is reset and the timer restamped.
  writeBuildingState(attrs, { ...state, collect: 0, lastAccruedAt: deps.now() });
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
