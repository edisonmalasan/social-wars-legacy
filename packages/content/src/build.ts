/**
 * The content build.
 *
 * Input   upstream/socialwarriors/config/main.json        (the 2012 capture)
 *         upstream/socialwarriors/config/patch/patches.txt (the patch order)
 *         upstream/socialwarriors/config/patch/*.json     (the five deltas)
 * Output  packages/content/dist/content-bundle.json       (canonical, hashed)
 *
 * Design notes
 *
 * - **Reproducible.** The bundle contains no wall-clock values. The darts
 *   schedule is rotated at *runtime* (see `packages/rules/src/darts.ts`),
 *   because a build that depends on "now" cannot be hashed or diffed.
 * - **Strict.** The build fails on a duplicate id, a dangling reference, an
 *   unknown section, an unknown `properties` key or an item with no asset.
 *   A content bundle that only fails at runtime, in production, is worse
 *   than no bundle at all.
 * - **Provenance.** Every build records the upstream commit, the patches
 *   applied and their order, and the build id (the SHA-256 of the
 *   canonical bundle bytes).
 */

import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { applyPatch, type JsonObject, type JsonValue, type PatchOperation } from './patch.ts';
import type {
  ContentBundle,
  ContentGoal,
  ContentItem,
  ContentLevel,
} from './schema.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../../..');
const CONFIG_DIR = path.join(REPO_ROOT, 'upstream/socialwarriors/config');
const PATCH_DIR = path.join(CONFIG_DIR, 'patch');
const ASSETS_DIR = path.join(REPO_ROOT, 'upstream/socialwarriors/assets');
const OUT_DIR = path.join(REPO_ROOT, 'packages/content/dist');

export const UPSTREAM_COMMIT = 'c3fceeb1f8e93734a293b9bc25ae6025656f6822';

/** The sections the bundle knows about. Anything else is an error. */
const KNOWN_SECTIONS = [
  'categories',
  'items',
  'inventory_items',
  'expansion_prices',
  'levels',
  'neighbor_assists',
  'town_prices',
  'map_prices',
  'findable_items',
  'goals',
  'offer_packs',
  'social_items',
  'globals',
  'images',
  'sounds',
  'collections',
  'level_ranking_reward',
  'darts_items',
  'units_collections_categories',
  'magics',
] as const;

/**
 * The `properties` keys the shipped content uses.
 *
 * These are the 41 distinct keys across the 900 post-patch items. They are
 * listed so the build can report a key it has never seen before — the sign of
 * a content change that the rules engine has not been taught.
 */
const KNOWN_PROPERTY_KEYS = new Set([
  'allows_spy',
  'animal',
  'animated',
  'auto_activable',
  'bulldozable',
  'bunker',
  'chained',
  'decoration',
  'demolishable',
  'depot',
  'explosive',
  'farm',
  'fireman',
  'friend_assistable',
  'ft_armored',
  'ft_building',
  'ft_flying',
  'ft_ground',
  'grants_population',
  'harvester',
  'healer',
  'hq',
  'human',
  'lost_item',
  'mechanic',
  'multiCollectable',
  'pickable',
  'raisePopulationCap',
  'regenerating',
  'resource',
  'resurrectable',
  'seeStealthUnits',
  'silo',
  'tower',
  'training_queue',
  'usable',
  'walkable',
  'wall',
  'waterborne',
  'wonder',
  'worker',
]);

export class ContentBuildError extends Error {
  readonly problems: string[];

  constructor(message: string, problems: string[] = []) {
    super(problems.length ? `${message}\n  - ${problems.join('\n  - ')}` : message);
    this.name = 'ContentBuildError';
    this.problems = problems;
  }
}

async function exists(p: string): Promise<boolean> {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function readJson<T>(file: string): Promise<T> {
  return JSON.parse(await readFile(file, 'utf8')) as T;
}

/** The patch order, read from `patches.txt` (comments and blanks ignored). */
async function readPatchOrder(): Promise<string[]> {
  const text = await readFile(path.join(PATCH_DIR, 'patches.txt'), 'utf8');
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '' && !line.startsWith('#'))
    .map((line) => line.replace(/\.json$/, ''));
}

/** Canonical JSON: sorted keys, no whitespace surprises, stable bytes. */
export function canonicalise(value: unknown): string {
  const seen = new WeakSet<object>();
  const walk = (v: unknown): unknown => {
    if (v === null || typeof v !== 'object') return v;
    if (seen.has(v as object)) throw new Error('circular structure in the content');
    seen.add(v as object);
    if (Array.isArray(v)) return v.map(walk);
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(v as Record<string, unknown>).sort()) {
      out[key] = walk((v as Record<string, unknown>)[key]);
    }
    return out;
  };
  return JSON.stringify(walk(value));
}

function parseProperties(raw: unknown): Record<string, unknown> {
  if (typeof raw !== 'string' || raw === '') return {};
  try {
    const parsed: unknown = JSON.parse(raw);
    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function asInt(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

/** Normalise one raw config item into the bundle's item shape. */
function toContentItem(raw: JsonObject): ContentItem {
  const known = new Set([
    'id', 'name', 'type', 'category_id', 'subcategory_id', 'subcat_functional',
    'img_name', 'attack', 'defense', 'life', 'attack_range', 'attack_interval',
    'population', 'cost', 'cost_type', 'costs', 'properties', 'best_against',
    'best_against_mult', 'trains_ids', 'upgrades_to', 'unit_capacity',
    'building_limit_same_id', 'building_limit_same_scf',
  ]);
  const extra: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (!known.has(key)) extra[key] = value;
  }
  const trains = asArray(raw['trains_ids']).map((v) => asInt(v));
  return {
    id: asInt(raw['id']),
    name: asString(raw['name']),
    type: asString(raw['type']),
    category_id: asInt(raw['category_id']),
    subcategory_id: asInt(raw['subcategory_id']),
    subcat_functional: asInt(raw['subcat_functional']),
    img_name: asString(raw['img_name']),
    attack: asInt(raw['attack']),
    defense: asInt(raw['defense']),
    life: asInt(raw['life']),
    attack_range: asInt(raw['attack_range']),
    attack_interval: asInt(raw['attack_interval']),
    population: asInt(raw['population']),
    cost: asInt(raw['cost']),
    cost_type: asString(raw['cost_type']),
    costs: asRecord(raw['costs']) as Record<string, number>,
    properties: parseProperties(raw['properties']),
    best_against:
      typeof raw['best_against'] === 'string' ? (raw['best_against'] as string) : null,
    best_against_mult: asInt(raw['best_against_mult'], 1),
    trains_ids: trains,
    upgrades_to:
      typeof raw['upgrades_to'] === 'number' ? (raw['upgrades_to'] as number) : null,
    unit_capacity: asInt(raw['unit_capacity']),
    building_limit_same_id: asInt(raw['building_limit_same_id']),
    building_limit_same_scf: asInt(raw['building_limit_same_scf']),
    properties_raw: asString(raw['properties']),
    extra,
  };
}

/** The asset a config item resolves to, following the upstream naming rules. */
export function assetCandidates(item: ContentItem): string[] {
  const out: string[] = [];
  // `img_name` is a comma-separated variant list for the five gendered units.
  for (const variant of item.img_name.split(',').map((v) => v.trim()).filter(Boolean)) {
    out.push(path.join(ASSETS_DIR, 'sprites', `${variant}.swf`));
    out.push(path.join(ASSETS_DIR, 'thumbs', `${variant}.jpg`));
  }
  return out;
}

export interface BuildResult {
  bundle: ContentBundle;
  problems: string[];
  warnings: string[];
}

export async function buildContent(): Promise<BuildResult> {
  const problems: string[] = [];
  const warnings: string[] = [];

  // 1. Load the base config.
  const base = (await readJson<JsonObject>(path.join(CONFIG_DIR, 'main.json'))) as JsonValue;

  // 2. Apply the patches, in the documented order.
  const patchOrder = await readPatchOrder();
  let config = base;
  for (const name of patchOrder) {
    const file = path.join(PATCH_DIR, `${name}.json`);
    if (!(await exists(file))) {
      problems.push(`patch listed in patches.txt is missing: ${name}.json`);
      continue;
    }
    const patch = (await readJson<PatchOperation[]>(file)) as PatchOperation[];
    config = applyPatch(config, patch);
  }

  const doc = config as JsonObject;

  // 3. Unknown sections are a hard error: the bundle must not silently drop data.
  for (const key of Object.keys(doc)) {
    if (!(KNOWN_SECTIONS as readonly string[]).includes(key)) {
      problems.push(`unknown top-level section in the config: ${key}`);
    }
  }

  // 4. Items, with duplicate detection (the upstream server also de-duplicates).
  const rawItems = asArray(doc['items']).filter(
    (v): v is JsonObject => v !== null && typeof v === 'object' && !Array.isArray(v),
  );
  const seenIds = new Set<number>();
  const items: ContentItem[] = [];
  for (const raw of rawItems) {
    const item = toContentItem(raw);
    if (seenIds.has(item.id)) {
      problems.push(`duplicate item id: ${item.id} (${item.name})`);
      continue;
    }
    seenIds.add(item.id);
    items.push(item);
  }
  items.sort((a, b) => a.id - b.id);

  // 5. Dangling references.
  for (const item of items) {
    for (const trained of item.trains_ids) {
      if (!seenIds.has(trained)) {
        problems.push(`item ${item.id} (${item.name}) trains missing unit ${trained}`);
      }
    }
    if (item.upgrades_to !== null && !seenIds.has(item.upgrades_to)) {
      problems.push(
        `item ${item.id} (${item.name}) upgrades to missing item ${item.upgrades_to}`,
      );
    }
  }

  // 6. The known property keys, counted.
  const propertyKeys: Record<string, number> = {};
  const subcatFunctionals: Record<string, number> = {};
  for (const item of items) {
    for (const key of Object.keys(item.properties)) {
      propertyKeys[key] = (propertyKeys[key] ?? 0) + 1;
      if (!KNOWN_PROPERTY_KEYS.has(key)) {
        warnings.push(`item ${item.id} has an unknown properties key: ${key}`);
      }
    }
    const scf = String(item.subcat_functional);
    subcatFunctionals[scf] = (subcatFunctionals[scf] ?? 0) + 1;
  }

  // 7. Asset resolution.
  const assetlessItemIds: number[] = [];
  for (const item of items) {
    if (item.img_name === '') continue;
    const candidates = assetCandidates(item);
    let found = false;
    for (const candidate of candidates) {
      if (await exists(candidate)) {
        found = true;
        break;
      }
    }
    if (!found) assetlessItemIds.push(item.id);
  }

  // 8. Levels and goals.
  const levels: ContentLevel[] = asArray(doc['levels']).map((v, index) => {
    const raw = asRecord(v);
    return {
      index,
      name: asString(raw['name']),
      exp_required: asInt(raw['exp_required']),
      reward_type: asString(raw['reward_type']),
      reward_amount: asInt(raw['reward_amount']),
    };
  });
  const goals: ContentGoal[] = asArray(doc['goals']).map((v) => {
    const raw = asRecord(v);
    return {
      id: asInt(raw['id']),
      title: asString(raw['title']),
      description: asString(raw['description']),
      hint: asString(raw['hint']),
      reward: raw['reward'],
    };
  });

  // 9. The client-only items, from the behaviour tables.
  let clientOnlyItemIds: number[] = [];
  const mapFile = path.join(REPO_ROOT, 're/data/item-delegate-map.json');
  if (await exists(mapFile)) {
    const map = (await readJson<{ items: { itemId: number }[] }>(mapFile)) as {
      items: { itemId: number }[];
    };
    clientOnlyItemIds = map.items
      .map((i) => i.itemId)
      .filter((id) => !seenIds.has(id))
      .sort((a, b) => a - b);
  } else {
    warnings.push('re/data/item-delegate-map.json is missing; client-only items not reconciled');
  }

  const bundle: ContentBundle = {
    formatVersion: 1,
    buildId: '',
    upstreamCommit: UPSTREAM_COMMIT,
    patchesApplied: patchOrder,
    items,
    levels,
    goals,
    globals: asRecord(doc['globals']),
    collections: asArray(doc['collections']),
    inventoryItems: asRecord(doc['inventory_items']),
    offerPacks: asArray(doc['offer_packs']),
    socialItems: asArray(doc['social_items']),
    images: asRecord(doc['images']) as Record<string, string>,
    sounds: asArray(doc['sounds']),
    dartsItems: asArray(doc['darts_items']),
    unitCollectionCategories: asRecord(doc['units_collections_categories']),
    magics: asArray(doc['magics']),
    expansionPrices: asArray(doc['expansion_prices']),
    neighborAssists: asArray(doc['neighbor_assists']),
    townPrices: asArray(doc['town_prices']),
    mapPrices: asArray(doc['map_prices']),
    findableItems: asArray(doc['findable_items']),
    levelRankingReward: asArray(doc['level_ranking_reward']),
    categories: asRecord(doc['categories']),
    clientOnlyItemIds,
    assetlessItemIds,
    propertyKeys,
    subcatFunctionals,
  };

  bundle.buildId = createHash('sha256').update(canonicalise(bundle)).digest('hex');

  return { bundle, problems, warnings };
}

export async function writeBundle(bundle: ContentBundle, outFile?: string): Promise<string> {
  const file = outFile ?? path.join(OUT_DIR, 'content-bundle.json');
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, canonicalise(bundle) + '\n', 'utf8');
  return file;
}

export { OUT_DIR, CONFIG_DIR, PATCH_DIR, ASSETS_DIR, REPO_ROOT };
