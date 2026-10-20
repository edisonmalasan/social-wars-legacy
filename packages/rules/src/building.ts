/**
 * Building: costs, durations, upgrades and limits.
 *
 * Ported from the client. The upstream Python server implements **none** of
 * this — its `buy` handler checks the level and the gold and then trusts
 * whatever resource delta the client declared, and the training queue and
 * the build timers live entirely in the client. A server-authoritative
 * clone has to own all of it.
 */

/**
 * The fraction of a building's cost that is refunded when it is replaced
 * by an upgrade.
 *
 * `Config.DIVISOR_SELL = 20` — the old building is refunded at 1/20 of
 * what it cost.
 */
export const DIVISOR_SELL = 20;

/** The part of a building a content item describes. */
export interface BuildingData {
  id: number;
  name: string;
  /** The build cost, by resource key. Cash is NOT in here. */
  costs: Record<string, number>;
  /** The cash price of one unit trained in this building. */
  costUnitCash: number;
  /** Seconds to construct. */
  buildTime: number;
  /** Seconds to train one unit. */
  trainingTime: number;
  /** How many friend clicks the build needs. 0 means instant. */
  clicksToBuild: number;
  /** The minimum player level. */
  minLevel: number;
  /** The next tier, if any. */
  upgradesTo: number | null;
  /** How many units fit inside. */
  unitCapacity: number;
  /** The population the building or unit costs. */
  population: number;
  /** The maximum copies of this exact building. -1 means unlimited. */
  buildingLimitSameId: number;
  /** The maximum copies per sub-category. -1 means unlimited. */
  buildingLimitSameScf: number;
  /** The cash cost of a premium upgrade, if it has one. */
  premiumUpgradeCosts: Record<string, number>;
}

/** The build cost, in resources. */
export function buildCost(building: BuildingData): Record<string, number> {
  return { ...building.costs };
}

/** How long the build takes, in milliseconds. */
export function buildDurationMs(building: BuildingData): number {
  return building.buildTime * 1000;
}

/** How long training one unit takes, in milliseconds. */
export function trainingDurationMs(building: BuildingData): number {
  return building.trainingTime * 1000;
}

/** How many friend clicks the build needs. */
export function clicksToBuild(building: BuildingData): number {
  return building.clicksToBuild;
}

/**
 * The cost of upgrading a building.
 *
 * The old building is removed and the new one added. The old building's
 * cost is refunded at **1/20** (`Config.DIVISOR_SELL = 20`), and the new
 * building's `costs` are charged.
 */
export function upgradeCost(
  oldBuilding: BuildingData,
  newBuilding: BuildingData,
): Record<string, number> {
  const cost: Record<string, number> = { ...newBuilding.costs };
  for (const [resource, amount] of Object.entries(oldBuilding.costs)) {
    const refund = Math.floor(amount / DIVISOR_SELL);
    cost[resource] = (cost[resource] ?? 0) - refund;
  }
  // A refunded cost can go negative; the client treats that as a gain, but
  // the net charge is what matters and it is never below zero.
  for (const resource of Object.keys(cost)) {
    if (cost[resource]! < 0) cost[resource] = 0;
  }
  return cost;
}

/** The pricing for a premium (cash) upgrade. */
export interface UpgradeSpeedupPricing {
  /** The minutes per cash unit. */
  minutesPerUnit: number;
  /** The cash per unit. */
  cashPerUnit: number;
}

/**
 * The cash cost of a premium upgrade.
 *
 * `ceil(build_time / 60 / UPGRADE_SPEEDUP_PRICING[0]) * UPGRADE_SPEEDUP_PRICING[1]`
 * — with the shipped `[5, 1]`, that is one cash per five minutes of build time.
 */
export function premiumUpgradeCost(
  building: BuildingData,
  pricing: UpgradeSpeedupPricing,
): number {
  const minutes = building.buildTime / 60;
  return Math.ceil(minutes / pricing.minutesPerUnit) * pricing.cashPerUnit;
}

/** The hurry-up (speed-up) rules. */
export interface SpeedupRules {
  /** The minimum time that must remain for a speed-up to be offered. */
  minRemainingMs: number;
  /** The cash cost of a speed-up. */
  cost: number;
}

/**
 * The cash cost of hurrying a build up, or null when it is not allowed.
 *
 * A speed-up is only offered when more than `minRemainingMs` is left,
 * so the client never lets a player pay to hurry a build that is
 * nearly done.
 */
export function speedUpCost(
  remainingMs: number,
  rules: SpeedupRules,
): number | null {
  if (remainingMs < rules.minRemainingMs) return null;
  return rules.cost;
}

/** Why a building cannot be placed. */
export type PlacementRefusal =
  | 'level'
  | 'population'
  | 'same-id-limit'
  | 'same-group-limit'
  | 'no-free-tile';

/** The player's state, for a placement check. */
export interface PlacementState {
  level: number;
  /** The population the player is using. */
  populationUsed: number;
  /** The population ceiling. */
  populationMax: number;
  /** How many copies of each building id are already placed. */
  sameIdCounts: Record<string, number>;
  /** How many copies of each sub-category are already placed. */
  sameGroupCounts: Record<string, number>;
  /** The sub-category of the building being placed. */
  subcategoryId: number;
  /** Is there a free tile? */
  hasFreeTile: boolean;
}

/**
 * Can this building be placed?
 *
 * The checks are the client's, in order: the level, the population, the
 * per-id limit, the per-group limit, and a free tile.
 */
export function canPlaceBuilding(
  building: BuildingData,
  state: PlacementState,
): { ok: true } | { ok: false; reason: PlacementRefusal } {
  if (state.level < building.minLevel) return { ok: false, reason: 'level' };
  if (state.populationUsed + building.population > state.populationMax) {
    return { ok: false, reason: 'population' };
  }
  const sameId = state.sameIdCounts[String(building.id)] ?? 0;
  if (
    building.buildingLimitSameId >= 0 &&
    sameId >= building.buildingLimitSameId
  ) {
    return { ok: false, reason: 'same-id-limit' };
  }
  const sameGroup = state.sameGroupCounts[String(state.subcategoryId)] ?? 0;
  if (
    building.buildingLimitSameScf >= 0 &&
    sameGroup >= building.buildingLimitSameScf
  ) {
    return { ok: false, reason: 'same-group-limit' };
  }
  if (!state.hasFreeTile) return { ok: false, reason: 'no-free-tile' };
  return { ok: true };
}

/**
 * Can this building be upgraded to?
 *
 * The target's own `min_level` applies, and there must be a free tile.
 */
export function canUpgrade(
  newBuilding: BuildingData,
  playerLevel: number,
  hasFreeTile: boolean,
): { ok: true } | { ok: false; reason: 'level' | 'no-free-tile' } {
  if (playerLevel < newBuilding.minLevel) return { ok: false, reason: 'level' };
  if (!hasFreeTile) return { ok: false, reason: 'no-free-tile' };
  return { ok: true };
}
