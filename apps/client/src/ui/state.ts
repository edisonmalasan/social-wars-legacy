/**
 * The interface's state.
 *
 * The server's answer and the **content** are the two things the
 * interface draws, and this module is the bridge between them: the
 * content bundle is the game's configuration, and the models in
 * `packages/client` are what the interface draws. The bridge is here
 * because the models do not know the content's shape — the content
 * bundle's fields are `snake_case` and its globals are untyped — and
 * because the interface must not draw a number the content does not
 * have.
 *
 * It is a `.ts` module and not a `.tsx` one, so it can be tested
 * without a browser: the tests are in `state.test.ts`.
 */
import type {
  BuildMenuItem,
  HudInput,
  HudRules,
  ItemPopulation,
  WorldSnapshot,
} from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';

/** The categories, as the build menu's tabs read them. */
export type Categories = Record<
  string,
  { id: number; name: string; sub?: { id: number; name: string }[] }
>;

/** A number in the content's globals, or the fallback. */
function numberAt(globals: Record<string, unknown>, key: string, fallback: number): number {
  const value = globals[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/** A record of numbers in the content's globals, or an empty record. */
function numbersAt(
  globals: Record<string, unknown>,
  key: string,
): Record<string, number> {
  const value = globals[key];
  if (typeof value !== 'object' || value === null) return {};
  const out: Record<string, number> = {};
  for (const [name, amount] of Object.entries(value as Record<string, unknown>)) {
    if (typeof amount === 'number' && Number.isFinite(amount)) out[name] = amount;
  }
  return out;
}

/**
 * The rules the HUD reads out of the content's globals.
 *
 * They are the content's own numbers: the storage limits, the energy
 * cap and the population rule. The fallbacks are the same numbers, so a
 * bundle that has lost a global still draws the game's own limits
 * rather than zeroes.
 */
export function hudRules(bundle: ContentBundle): HudRules {
  const globals = bundle.globals;
  return {
    baseResourceLimits: numbersAt(globals, 'BASE_RESOURCE_LIMITS'),
    maxEnergy: numberAt(globals, 'ENERGY_MAX_REGULAR_VALUE', 30),
    startMaxPopulation: numberAt(globals, 'START_MAX_POPULATION', 20),
    maxPopulationCap: numberAt(globals, 'MAX_POPULATION_CAP', 175),
    maxPopulationPerLevel: numberAt(globals, 'MAX_POPULATION_PER_LEVEL', 3),
  };
}

/** What each item does to the population, by item id. */
export function populationItems(bundle: ContentBundle): Map<number, ItemPopulation> {
  const out = new Map<number, ItemPopulation>();
  for (const item of bundle.items) {
    const properties = item.properties ?? {};
    out.set(item.id, {
      population: item.population ?? 0,
      type: item.type,
      grants: properties['grants_population'] !== undefined,
    });
  }
  return out;
}

/** The XP each level needs, by level index. */
export function expRequiredByLevel(bundle: ContentBundle): Map<number, number> {
  const out = new Map<number, number>();
  for (const level of bundle.levels) out.set(level.index, level.exp_required);
  return out;
}

/** What the HUD needs to draw itself. */
export function hudInput(bundle: ContentBundle, world: WorldSnapshot): HudInput {
  return {
    world,
    items: populationItems(bundle),
    rules: hudRules(bundle),
    expRequiredByLevel: expRequiredByLevel(bundle),
  };
}

/**
 * The build menu's items.
 *
 * The content's items are the game's own, and the menu is the client's
 * own: this is the mapping between them. The items that are **not**
 * buildings or units — the decorations and the tokens — are left out,
 * because the original's build window does not sell them.
 */
export function buildItems(bundle: ContentBundle): BuildMenuItem[] {
  const items: BuildMenuItem[] = [];
  for (const item of bundle.items) {
    if (!buildable(item)) continue;
    items.push({
      id: item.id,
      name: item.name,
      categoryId: item.category_id,
      subcategoryId: item.subcategory_id,
      displayOrder: item.display_order,
      minLevel: item.min_level,
      costs: item.costs ?? {},
      buildTime: item.build_time,
      clicksToBuild: item.clicks_to_build,
      inStore: item.in_store,
    });
  }
  return items;
}

/**
 * Whether the build window offers this item.
 *
 * The original's window lists the buildings and the units, and the
 * content's `type` says which is which: `'b'` is a building and `'u'` is
 * a unit.
 */
function buildable(item: ContentItem): boolean {
  return item.type === 'b' || item.type === 'u';
}

/**
 * The categories, as the tabs read them.
 *
 * The content's categories are untyped, so they are read carefully: a
 * category without an id or a name is not a tab.
 */
export function categories(bundle: ContentBundle): Categories {
  const out: Categories = {};
  for (const [key, value] of Object.entries(bundle.categories)) {
    if (typeof value !== 'object' || value === null) continue;
    const category = value as {
      id?: unknown;
      name?: unknown;
      sub?: unknown;
    };
    if (typeof category.id !== 'number' || typeof category.name !== 'string') continue;
    const sub: { id: number; name: string }[] = [];
    if (Array.isArray(category.sub)) {
      for (const entry of category.sub) {
        if (typeof entry !== 'object' || entry === null) continue;
        const one = entry as { id?: unknown; name?: unknown };
        if (typeof one.id !== 'number' || typeof one.name !== 'string') continue;
        sub.push({ id: one.id, name: one.name });
      }
    }
    out[key] = { id: category.id, name: category.name, sub };
  }
  return out;
}
