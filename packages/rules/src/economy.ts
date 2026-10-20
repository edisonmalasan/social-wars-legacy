/**
 * The economy: collection, population, energy and the price tables.
 *
 * Ported from the client. The upstream Python server is **not** the
 * specification here — its `collect` handler only resets the timer and awards
 * nothing, because the whole server trusts the client's declared resource
 * deltas. The client's own arithmetic is the specification, and the server
 * must reproduce it.
 *
 * Every constant comes from the content bundle's `globals`, so the rules and
 * the data cannot drift apart.
 */

/**
 * Each extra worker inside a mill adds this fraction of the base yield.
 *
 * `Config.MULTIPLIER_PEASANTS = 0.2` — a config constant, not a global.
 */
export const MULTIPLIER_PEASANTS = 0.2;

/** The four collect-period choices: the minutes, and the multiplier for each. */
export interface CollectPeriods {
  minutes: number[];
  multiplier: number[];
}

/** A building that produces a resource. */
export interface Producer {
  /** The base amount per collection cycle. */
  collect: number;
  /** How many units fit inside. */
  unitCapacity: number;
  /** How many units are inside right now. */
  unitsInside: number;
  /** A global resource multiplier. Always 1 in the shipped build. */
  resourceMultiplier?: number;
}

/** The result of a collection. */
export interface CollectionResult {
  /** The amount produced. 0 when the anti-hack guard trips. */
  amount: number;
  /** True when the guard tripped: more units inside than the capacity. */
  hacked: boolean;
}

/**
 * How much a building produces on a collection.
 *
 * ```
 * base   = floor(collect * resourceMultiplier)
 * mult   = COLLECT_MULTIPLIER[cp - 1]
 * if unitsInside > 1:
 *     amount = floor( floor( base + (unitsInside - 1) * base * 0.2 ) * mult )
 * else:
 *     amount = floor( base * mult )
 * ```
 *
 * `cp` is the collect-period index, 1..4.
 *
 * **The anti-hack guard.** If the building holds more units than its
 * capacity, the client logs `"HACK DETECTED - jsbermeo: the units in this
 * building are higher than the building capacity!"` and collects **nothing**.
 * That check is client-side only in the original — a server-authoritative
 * clone must make it server-side.
 */
export function collect(
  producer: Producer,
  collectPeriodIndex: number,
  periods: CollectPeriods,
): CollectionResult {
  if (producer.unitsInside > producer.unitCapacity) {
    return { amount: 0, hacked: true };
  }

  const multiplier = periods.multiplier[collectPeriodIndex - 1];
  if (multiplier === undefined) {
    throw new RangeError(`no collect period ${collectPeriodIndex}`);
  }

  const base = Math.floor(producer.collect * (producer.resourceMultiplier ?? 1));
  const raw =
    producer.unitsInside > 1
      ? base + (producer.unitsInside - 1) * base * MULTIPLIER_PEASANTS
      : base;

  return { amount: Math.floor(Math.floor(raw) * multiplier), hacked: false };
}

/** The player's population. */
export interface PopulationState {
  /** The population each of the player's buildings grants. */
  grantedByBuildings: number;
  /** The population of the player's units on the map. */
  unitsOnMap: number;
  /** The population of the units being trained. */
  beingTrained: number;
  /** Extra population from expansions and the like. */
  additionalPopulation: number;
  /** The player's level, which grants population per level. */
  level: number;
}

export interface PopulationRules {
  startMaxPopulation: number;
  maxPopulationCap: number;
  maxPopulationPerLevel: number;
}

/**
 * The player's current population.
 *
 * `Σ(unit population) + the population of the units being trained`.
 */
export function currentPopulation(state: PopulationState): number {
  return state.unitsOnMap + state.beingTrained;
}

/**
 * The player's population ceiling.
 *
 * ```
 * maxCurrent = min( START_MAX_POPULATION + Σ(population granted by buildings),
 *                    MAX_POPULATION_CAP + additionalPopulation )
 * ```
 *
 * The per-level grant is applied by the caller, through the buildings'
 * `grants_population` property.
 */
export function maxPopulation(state: PopulationState, rules: PopulationRules): number {
  const granted = rules.startMaxPopulation + state.grantedByBuildings;
  const capped = rules.maxPopulationCap + state.additionalPopulation;
  return Math.min(granted, capped);
}

/** Can a unit of this population be placed? */
export function canPlaceUnit(
  state: PopulationState,
  rules: PopulationRules,
  unitPopulation: number,
): boolean {
  const current = currentPopulation(state);
  const maximum = maxPopulation(state, rules);
  return current + unitPopulation <= maximum;
}

/** The player's energy. */
export interface EnergyRules {
  /** The free maximum. */
  max: number;
  /** Milliseconds per +1. */
  regenIntervalMs: number;
  /** Energy a construction costs. */
  constructionCost: number;
  /** Energy a friend assist costs. */
  assistCost: number;
}

/**
 * The energy the player has after regenerating.
 *
 * Regeneration is one point per `regenIntervalMs`, and it never goes above
 * the free maximum unless the player has bought energy.
 */
export function regenerateEnergy(
  current: number,
  elapsedMs: number,
  rules: EnergyRules,
): number {
  if (rules.regenIntervalMs <= 0) return current;
  const gained = Math.floor(elapsedMs / rules.regenIntervalMs);
  if (gained <= 0) return current;
  return Math.min(current + gained, rules.max);
}

/** A price table row: a coin price, a cash price, and a level requirement. */
export interface PriceRow {
  coins: number;
  cash: number;
  /** The neighbours needed for an expansion. */
  neighbors?: number;
  /** The level needed for a town or a map. */
  level?: number;
}

/**
 * The price of the next expansion.
 *
 * The first four rows are free — the starting 4×4 grid.
 */
export function expansionPrice(prices: readonly PriceRow[], ownedTiles: number): PriceRow | null {
  return prices[ownedTiles] ?? null;
}

/** The price of a new town or a new map. */
export function townPrice(prices: readonly PriceRow[], index: number): PriceRow | null {
  return prices[index] ?? null;
}

/** Is the player level high enough to buy this? */
export function meetsLevelRequirement(price: PriceRow, level: number): boolean {
  return price.level === undefined || level >= price.level;
}
