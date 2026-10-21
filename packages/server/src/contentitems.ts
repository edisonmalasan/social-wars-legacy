/**
 * The content items, as the applier needs them.
 *
 * The applier checks the **rules** — the level, the population, the
 * per-id and per-group limits — and it needs the content to do it: an
 * item's cost, its duration, its limits and its population are all the
 * game's own configuration.
 *
 * The content bundle is the authority, and this is the mapping from it
 * to the applier's own shape.
 */
import type { ApplierItem } from './apply.ts';

/** A number, or the fallback. */
function numberOr(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/** A record of numbers, or an empty one. */
function costsOr(value: unknown): Record<string, number> {
  if (typeof value !== 'object' || value === null) return {};
  const out: Record<string, number> = {};
  for (const [key, amount] of Object.entries(value as Record<string, unknown>)) {
    if (typeof amount === 'number' && Number.isFinite(amount)) out[key] = amount;
  }
  return out;
}

/** Whether the item's properties carry a flag. */
function hasFlag(properties: unknown, flag: string): boolean {
  if (typeof properties !== 'object' || properties === null) return false;
  return flag in (properties as Record<string, unknown>);
}

/**
 * The content's items, by id.
 *
 * The bundle is the game's configuration, so nothing here is invented:
 * an item that is not in the bundle is not in the map ✗ (the applier
 * refuses it as an unknown item ✗).
 */
export function contentItems(bundle: { items?: unknown[] }): Map<number, ApplierItem> {
  const items = new Map<number, ApplierItem>();
  for (const raw of bundle.items ?? []) {
    if (typeof raw !== 'object' || raw === null) continue;
    const item = raw as Record<string, unknown>;
    const id = numberOr(item['id'], Number.NaN);
    if (!Number.isFinite(id)) continue;

    items.set(id, {
      id,
      name: typeof item['name'] === 'string' ? item['name'] : '',
      costs: costsOr(item['costs']),
      // The config's single-resource cost is a leftover, and the cash
      // price of a unit is not in the bundle at all.
      costUnitCash: 0,
      buildTime: numberOr(item['build_time'], 0),
      trainingTime: numberOr(item['training_time'], 0),
      clicksToBuild: numberOr(item['clicks_to_build'], 0),
      minLevel: numberOr(item['min_level'], 1),
      unitCapacity: numberOr(item['unit_capacity'], 0),
      population: numberOr(item['population'], 0),
      buildingLimitSameId: numberOr(item['building_limit_same_id'], -1),
      buildingLimitSameScf: numberOr(item['building_limit_same_scf'], -1),
      subcategoryId: numberOr(item['subcategory_id'], 0),
      width: numberOr(item['width'], 1),
      height: numberOr(item['height'], 1),
      trainsIds: Array.isArray(item['trains_ids'])
        ? (item['trains_ids'] as unknown[]).filter(
            (id): id is number => typeof id === 'number',
          )
        : [],
      upgradesTo:
        typeof item['upgrades_to'] === 'number' ? item['upgrades_to'] : null,
      premiumUpgradeCosts: {},
      // The item's kind: `'b'` is a building and `'u'` is a unit. The
      // population rule needs it, because a unit **uses** population
      // and a building **grants** it.
      type: typeof item['type'] === 'string' ? item['type'] : 'b',
      // Whether the building grants population. The flag is the
      // content's own, and it is what says which buildings count
      // towards the ceiling.
      grantsPopulation: hasFlag(item['properties'], 'grants_population'),
    });
  }
  return items;
}

/**
 * The population rules, from the content's globals.
 *
 * They are the game's own numbers, and the fallbacks are the same
 * numbers, so a bundle that has lost a global still uses the game's
 * limits.
 */
export function populationRules(globals: Record<string, unknown>): {
  startMaxPopulation: number;
  maxPopulationCap: number;
  maxPopulationPerLevel: number;
} {
  return {
    startMaxPopulation: numberOr(globals['START_MAX_POPULATION'], 20),
    maxPopulationCap: numberOr(globals['MAX_POPULATION_CAP'], 175),
    maxPopulationPerLevel: numberOr(globals['MAX_POPULATION_PER_LEVEL'], 3),
  };
}
