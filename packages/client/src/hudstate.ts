/**
 * The HUD's state, read from the server's answer.
 *
 * The server owns the world: the resources, the level, the XP and the
 * placed buildings all come from **its** answer, and the client draws
 * them. What the client adds is the *interpretation*: the storage
 * limits, the energy cap and the population rule are in the **content**,
 * which is the game's own configuration, and the HUD is their reading
 * of a world.
 *
 * This module is a model, like `hud.ts`: it turns the server's answer
 * into the state the HUD draws, and it is tested without a browser.
 *
 * ## The storage limits
 *
 * The limits are the content's `globals.BASE_RESOURCE_LIMITS` — 20 000
 * of each of gold, oil, steel and wood — and **cash and mana are
 * uncapped**. The original's silos raise the real cap, but the client
 * never sees it: `Base.Player.getResourceLimitsMap()` returns only the
 * base limits, so the HUD shows the base cap, exactly as the original
 * does (`re/docs/03-commands-quests-economy.md`).
 */
import type { HudState } from './hud.ts';
import type { WorldSnapshot } from './session.ts';

/** The rules the HUD reads out of the content's globals. */
export interface HudRules {
  /** The base storage limit, by resource key. */
  baseResourceLimits: Readonly<Record<string, number>>;
  /** The most free energy a player may hold. */
  maxEnergy: number;
  /** The population a first-level player may hold. */
  startMaxPopulation: number;
  /** The most population any level may hold. */
  maxPopulationCap: number;
  /** The extra population each level allows. */
  maxPopulationPerLevel: number;
}

/** What the HUD needs to know to draw itself. */
export interface HudInput {
  /** The server's answer. */
  world: WorldSnapshot;
  /** The population each item costs, by item id. */
  populationByItem: ReadonlyMap<number, number>;
  /** The content's rules. */
  rules: HudRules;
  /** The XP each level needs, by level index. */
  expRequiredByLevel: ReadonlyMap<number, number>;
}

/**
 * The player's level.
 *
 * The level is the **map's** own field, the way the original keeps it.
 * A world without one is a first-level world.
 */
export function levelOf(world: WorldSnapshot): number {
  const level = world.maps[0]?.level;
  if (typeof level !== 'number' || !Number.isFinite(level)) return 1;
  return Math.max(1, Math.floor(level));
}

/**
 * The population the player's own items use.
 *
 * It is the sum of the placed items' population, which is what the
 * server's own rule does (`packages/server/src/apply.ts`).
 */
export function populationOf(
  world: WorldSnapshot,
  populationByItem: ReadonlyMap<number, number>,
): number {
  let used = 0;
  for (const tuple of Object.values(world.maps[0]?.items ?? {})) {
    used += populationByItem.get(Number(tuple[0])) ?? 0;
  }
  return used;
}

/**
 * The population the player's level allows.
 *
 * The ceiling grows with the level and stops at the absolute cap: the
 * content's `START_MAX_POPULATION`, `MAX_POPULATION_PER_LEVEL` and
 * `MAX_POPULATION_CAP`.
 */
export function populationLimit(level: number, rules: HudRules): number {
  return Math.min(
    rules.maxPopulationCap,
    rules.startMaxPopulation + rules.maxPopulationPerLevel * level,
  );
}

/**
 * The XP the player's next level needs.
 *
 * The server's own rule is the authority: to reach level *n* the player
 * needs the XP that level asks for, so the next level's row is the one
 * that counts.
 */
export function expRequired(input: HudInput, level: number): number {
  const required = input.expRequiredByLevel.get(level + 1);
  if (typeof required !== 'number') {
    // Nothing to ask for: the player is as far as the content knows.
    return input.world.maps[0]?.xp ?? 0;
  }
  return required;
}

/** The HUD's state. */
export function hudState(input: HudInput): HudState {
  const { world, rules } = input;
  const resources = world.resources;
  const level = levelOf(world);
  const limit = rules.baseResourceLimits;
  return {
    gold: resources['g'] ?? 0,
    maxGold: limit['g'] ?? 0,
    wood: resources['w'] ?? 0,
    maxWood: limit['w'] ?? 0,
    oil: resources['o'] ?? 0,
    maxOil: limit['o'] ?? 0,
    steel: resources['s'] ?? 0,
    maxSteel: limit['s'] ?? 0,
    cash: resources['c'] ?? 0,
    population: populationOf(world, input.populationByItem),
    populationMaxCurrent: populationLimit(level, rules),
    populationMaxAllowed: rules.maxPopulationCap,
    level,
    experience: world.maps[0]?.xp ?? 0,
    expRequired: expRequired(input, level),
    energy: resources['e'] ?? 0,
    maxEnergy: rules.maxEnergy,
  };
}
