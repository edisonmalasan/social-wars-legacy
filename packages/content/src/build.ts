/**
 * The content build.
 *
 * Input   upstream/socialwarriors/config/main.json        (the 2012 capture)
 *         upstream/socialwarriors/config/patch/patches.txt (the patch order)
 *         upstream/socialwarriors/config/patch/*.json     (the five deltas)
 *         upstream/socialwarriors/villages/quest/*.json   (build-time quest maps:
 *           the hardcore rosters and the Q03/Q10/Q11/Q14 event elements)
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
  QuestEventData,
  QuestRoster,
  QuestRosterEntry,
} from './schema.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../../..');
const CONFIG_DIR = path.join(REPO_ROOT, 'upstream/socialwarriors/config');
const PATCH_DIR = path.join(CONFIG_DIR, 'patch');
const ASSETS_DIR = path.join(REPO_ROOT, 'upstream/socialwarriors/assets');
/** Vendored quest map snapshots — a build-time source only, never read at runtime. */
const QUEST_DIR = path.join(REPO_ROOT, 'upstream/socialwarriors/villages/quest');
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
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    // The values are STRINGS too - the config writes `"ft_ground":"1"`, not
    // `"ft_ground":1`. The client treats them as flags and quantities, so
    // they are normalised to numbers here.
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) {
        out[key] = Number(value);
      } else {
        out[key] = value;
      }
    }
    return out;
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

/**
 * Parse a JSON object that the config stored as a string.
 *
 * The whole item table in `config/main.json` is **stringly-typed**: every
 * value is a string, and the structured ones are JSON text inside a string.
 * `costs` is `'{"c":10}'`, `properties` is `'{"ft_ground":1}'`, and
 * `inventory_ids` is the string `'null'` or a JSON object.
 *
 * Getting this wrong is silent: a plain object cast on a string yields
 * `{}`, so every build cost in the game would simply vanish.
 */
function parseJsonObject(raw: unknown): Record<string, number> {
  if (typeof raw === 'object' && raw !== null && !Array.isArray(raw)) {
    const out: Record<string, number> = {};
    for (const [key, value] of Object.entries(raw)) out[key] = asInt(value);
    return out;
  }
  if (typeof raw !== 'string') return {};
  const trimmed = raw.trim();
  if (trimmed === '' || trimmed === 'null') return {};
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const out: Record<string, number> = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      out[key] = asInt(value);
    }
    return out;
  } catch {
    return {};
  }
}

/**
 * Parse a single id that the config stored as a string.
 *
 * `-1` and `0` both mean "none".
 */
function parseId(raw: unknown): number | null {
  const value = asInt(raw, -1);
  return value > 0 ? value : null;
}

/**
 * Parse the id list a config stored as a string.
 *
 * `trains_ids` is a single id (`'1007'`), or `'-1'` for none. It is
 * occasionally a JSON array.
 */
function parseIdList(raw: unknown): number[] {
  if (Array.isArray(raw)) return raw.map((v) => asInt(v)).filter((v) => v > 0);
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed.startsWith('[')) {
      try {
        const parsed: unknown = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed.map((v) => asInt(v)).filter((v) => v > 0);
      } catch {
        /* fall through to the single-id case */
      }
    }
  }
  const id = parseId(raw);
  return id === null ? [] : [id];
}

/** Normalise one raw config item into the bundle's item shape. */
function toContentItem(raw: JsonObject): ContentItem {
  const known = new Set([
    'id', 'name', 'type', 'category_id', 'subcategory_id', 'subcat_functional',
    'img_name', 'attack', 'defense', 'life', 'attack_range', 'attack_interval',
    'population', 'cost', 'cost_type', 'costs', 'properties', 'best_against',
    'best_against_mult', 'trains_ids', 'upgrades_to', 'unit_capacity',
    'building_limit_same_id', 'building_limit_same_scf', 'width', 'height',
    'min_level', 'build_time', 'clicks_to_build', 'training_time', 'xp',
    'activation', 'collect', 'collect_type', 'collect_xp', 'max_collects',
    'group_type', 'race', 'in_store', 'giftable', 'gift_level',
    'cost_unit_cash', 'volume', 'max_elem_vol', 'inventory_ids',
    'premium_upgrade_costs',
  ]);
  const extra: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (!known.has(key)) extra[key] = value;
  }
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
    // The unit's **movement speed**, in pixels per frame. The upstream
    // keeps it as a string; the bundle carries the number, because a
    // number is what the rules and the panel read.
    velocity: asInt(raw['velocity']),
    population: asInt(raw['population']),
    cost: asInt(raw['cost']),
    cost_type: typeof raw['cost_type'] === 'string' ? raw['cost_type'] : null,
    costs: parseJsonObject(raw['costs']),
    properties: parseProperties(raw['properties']),
    best_against:
      typeof raw['best_against'] === 'string' && raw['best_against'] !== ''
        ? (raw['best_against'] as string)
        : null,
    best_against_mult: asInt(raw['best_against_mult'], 1),
    trains_ids: parseIdList(raw['trains_ids']),
    upgrades_to: parseId(raw['upgrades_to']),
    unit_capacity: asInt(raw['unit_capacity']),
    building_limit_same_id: asInt(raw['building_limit_same_id'], -1),
    building_limit_same_scf: asInt(raw['building_limit_same_scf'], -1),
    width: asInt(raw['width'], 1),
    height: asInt(raw['height'], 1),
    min_level: asInt(raw['min_level']),
    display_order: asInt(raw['display_order']),
    build_time: asInt(raw['build_time']),
    clicks_to_build: asInt(raw['clicks_to_build']),
    training_time: asInt(raw['training_time']),
    xp: asInt(raw['xp']),
    activation: asInt(raw['activation']),
    collect: asInt(raw['collect']),
    collect_type: asString(raw['collect_type'], 'g'),
    collect_xp: asInt(raw['collect_xp']),
    max_collects: asInt(raw['max_collects']),
    group_type: asString(raw['group_type']),
    race: asString(raw['race']),
    in_store: asString(raw['in_store']) === '1',
    giftable: asString(raw['giftable']) === '1',
    gift_level: asInt(raw['gift_level']),
    cost_unit_cash: asInt(raw['cost_unit_cash']),
    volume: asInt(raw['volume']),
    max_elem_vol: asInt(raw['max_elem_vol']),
    inventory_ids: parseJsonObject(raw['inventory_ids']),
    premium_upgrade_costs: parseJsonObject(raw['premium_upgrade_costs']),
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

/**
 * The eight hardcore quests and the exact number of enemy units each snapshot
 * holds (recorded in re/docs/01-network-protocol.md §3.5). The expected count
 * is a guard: an upstream drift or a wrong filter must fail the build rather
 * than silently ship an incomplete roster.
 */
const HARDCORE_QUEST_UNITS: Readonly<Record<string, number>> = {
  '100000017': 79, // HC1
  '100000018': 122, // HC2
  '100000019': 114, // HC3
  '100000020': 45, // HC4
  '100000021': 84, // HC5
  '100000022': 153, // HC6
  '100000026': 138, // HC9
  '100000025': 46, // HC10
};

export interface QuestMapSnapshot {
  readonly playerInfo?: { readonly pid?: unknown };
  readonly maps?: readonly { readonly items?: Record<string, unknown> }[];
}

/** A deterministic string comparison, independent of the host locale. */
function compareRefs(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/**
 * Extract the hardcore quest rosters from the vendored quest map snapshots.
 *
 * A snapshot stores `maps[0].items` as an object keyed by the iso id; each
 * value is the tuple `[item_id, x, y, timestamp, frame, queue, attrs, player]`.
 * The `player` flag is 1 for every item in these snapshots, so it cannot tell
 * friend from foe — only the content item's `type === 'u'` can. Refs are the
 * object keys (`item:<isoId>`), not the tuple's item id.
 */
async function extractQuestRosters(
  itemsById: Map<number, ContentItem>,
  problems: string[],
): Promise<QuestRoster[]> {
  const rosters: QuestRoster[] = [];
  for (const [questId, expectedUnits] of Object.entries(HARDCORE_QUEST_UNITS)) {
    const file = path.join(QUEST_DIR, `${questId}.json`);
    if (!(await exists(file))) {
      problems.push(`hardcore quest roster snapshot is missing: ${questId}.json`);
      continue;
    }
    const snapshot = await readJson<QuestMapSnapshot>(file);
    const pid = snapshot.playerInfo?.pid;
    if (String(pid) !== questId) {
      problems.push(
        `hardcore quest snapshot ${questId}.json has an unexpected playerInfo.pid: ${String(pid)}`,
      );
    }
    const mapItems = asRecord(snapshot.maps?.[0]?.items ?? {});
    const entries: QuestRosterEntry[] = [];
    for (const [isoId, rawTuple] of Object.entries(mapItems)) {
      const tuple = asArray(rawTuple);
      const itemId = asInt(tuple[0], -1);
      const content = itemsById.get(itemId);
      // The snapshot's `player` flag is useless here; `type === 'u'` is the
      // only reliable enemy-unit filter. Buildings are deliberately dropped.
      if (content === undefined || content.type !== 'u') continue;
      entries.push({
        ref: `item:${isoId}`,
        itemId,
        subcatFunctional: content.subcat_functional,
      });
    }
    // Object key order comes from the file; sort explicitly so the bundle is
    // byte-identical even if a future snapshot reorders its keys.
    entries.sort((a, b) => compareRefs(a.ref, b.ref));
    if (entries.length === 0) {
      problems.push(`hardcore quest ${questId} has an empty roster`);
    }
    if (entries.length !== expectedUnits) {
      problems.push(
        `hardcore quest ${questId} roster has ${entries.length} units, expected ${expectedUnits}`,
      );
    }
    rosters.push({ questId, items: entries });
  }
  rosters.sort((a, b) => compareRefs(a.questId, b.questId));
  return rosters;
}

/**
 * The Q03 truck constants, from the decompiled client
 * (`quest/Quest03DefendConvoyAuto.as:49-51, 175-189`; recorded in
 * `re/data/quests.json`: ID_UNIT_TRUCK_1 = 1013, totalTrucksToSave = 3).
 *
 * These are server-owned constants, never values supplied by a client
 * request. Q03's trucks spawn dynamically, so its map has no static truck
 * element to extract — the ref is the item id, not a map iso id.
 */
const Q03_TRUCK_ITEM_ID = 1013;
const Q03_TRUCK_ARRIVALS = 3;

/**
 * The group types the client's `Quest10SpecialOps` / `Quest14Spy2` treat as
 * eligible enemies ("bastards") — `re/data/quests.json` Q10/Q14.
 */
const ELIGIBLE_ENEMY_GROUP_TYPES = ['LONG_RANGE', 'SHORT_RANGE', 'LAND_VEHICLE'] as const;

/** One build-time quest event source and the rule that selects its elements. */
export type QuestEventSource =
  | {
      readonly kind: 'truckArrivals';
      readonly questId: string;
      readonly itemId: number;
      readonly count: number;
    }
  | {
      readonly kind: 'eligibleEnemies';
      readonly questId: string;
      readonly groupTypes: readonly string[];
    }
  | {
      readonly kind: 'civilianEvacuations';
      readonly questId: string;
      readonly nameIncludes: string;
    };

/** The four quests whose event counters the applier cannot derive from a spec. */
const QUEST_EVENT_SOURCES: readonly QuestEventSource[] = [
  {
    questId: '100000003',
    kind: 'truckArrivals',
    itemId: Q03_TRUCK_ITEM_ID,
    count: Q03_TRUCK_ARRIVALS,
  },
  {
    questId: '100000010',
    kind: 'eligibleEnemies',
    groupTypes: ELIGIBLE_ENEMY_GROUP_TYPES,
  },
  {
    questId: '100000011',
    kind: 'civilianEvacuations',
    nameIncludes: 'worker',
  },
  {
    questId: '100000014',
    kind: 'eligibleEnemies',
    groupTypes: ELIGIBLE_ENEMY_GROUP_TYPES,
  },
];

/**
 * Extract the quest event data from the vendored map snapshots and the
 * patched content items. Pure over its arguments: no clock, no upstream read
 * inside this function, so the bundle stays byte-identical across builds.
 *
 * A missing snapshot for a configured quest id, a mismatched `playerInfo.pid`
 * or an empty selection is a build problem — shipping an empty event would
 * let a `countersZero` win fire without any gameplay.
 */
export function extractQuestEvents(
  itemsById: ReadonlyMap<number, ContentItem>,
  snapshots: ReadonlyMap<string, QuestMapSnapshot>,
  problems: string[],
  sources: readonly QuestEventSource[] = QUEST_EVENT_SOURCES,
): Record<string, QuestEventData> {
  const events: Record<string, QuestEventData> = {};
  for (const source of sources) {
    const snapshot = snapshots.get(source.questId);
    if (snapshot === undefined) {
      problems.push(`quest event source has no vendored map snapshot: ${source.questId}`);
      continue;
    }
    const pid = snapshot.playerInfo?.pid;
    if (String(pid) !== source.questId) {
      problems.push(
        `quest event snapshot ${source.questId}.json has an unexpected playerInfo.pid: ${String(pid)}`,
      );
      continue;
    }

    let refs: string[];
    let count: number;
    if (source.kind === 'truckArrivals') {
      const truck = itemsById.get(source.itemId);
      if (truck === undefined || truck.type !== 'u') {
        problems.push(`quest ${source.questId} truck item ${source.itemId} is not a content unit`);
        continue;
      }
      refs = [`item:${source.itemId}`];
      count = source.count;
    } else {
      const groupTypes =
        source.kind === 'eligibleEnemies' ? new Set(source.groupTypes) : null;
      const nameIncludes =
        source.kind === 'civilianEvacuations' ? source.nameIncludes.toLowerCase() : null;
      const mapItems = asRecord(snapshot.maps?.[0]?.items ?? {});
      refs = [];
      for (const [isoId, rawTuple] of Object.entries(mapItems)) {
        const content = itemsById.get(asInt(asArray(rawTuple)[0], -1));
        if (content === undefined || content.type !== 'u') continue;
        if (groupTypes !== null && !groupTypes.has(content.group_type)) continue;
        if (nameIncludes !== null && !content.name.toLowerCase().includes(nameIncludes)) continue;
        refs.push(`item:${isoId}`);
      }
      // Object key order comes from the file; sort explicitly so a reordered
      // snapshot cannot change the bundle bytes.
      refs.sort(compareRefs);
      count = refs.length;
    }
    if (refs.length === 0) {
      problems.push(`quest ${source.questId} has no ${source.kind} elements`);
      continue;
    }
    if (new Set(refs).size !== refs.length) {
      problems.push(`quest ${source.questId} has duplicate ${source.kind} refs`);
      continue;
    }
    events[source.questId] = { questId: source.questId, kind: source.kind, refs, count };
  }
  return events;
}

/** Read the four quest event snapshots. Build-time only; never used at runtime. */
async function readQuestEventSnapshots(problems: string[]): Promise<Map<string, QuestMapSnapshot>> {
  const snapshots = new Map<string, QuestMapSnapshot>();
  for (const source of QUEST_EVENT_SOURCES) {
    const file = path.join(QUEST_DIR, `${source.questId}.json`);
    if (!(await exists(file))) {
      problems.push(`quest event snapshot is missing: ${source.questId}.json`);
      continue;
    }
    snapshots.set(source.questId, await readJson<QuestMapSnapshot>(file));
  }
  return snapshots;
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

  // 4b. Hardcore quest rosters, extracted from the vendored map snapshots.
  //     Build-time only — the shipped bundle never reads `upstream/` again.
  const itemsById = new Map(items.map((item) => [item.id, item]));
  const questRosters = await extractQuestRosters(itemsById, problems);

  // 4c. Quest event data (Q03 trucks, Q10/Q14 eligible enemies, Q11
  //     civilians). Also build-time only: the bundle carries the extracted
  //     refs and counts, so the server needs no access to `upstream/`.
  const questEvents = extractQuestEvents(
    itemsById,
    await readQuestEventSnapshots(problems),
    problems,
  );

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
    questRosters,
    questEvents,
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
