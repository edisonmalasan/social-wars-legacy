/**
 * The content bundle: a typed, validated, reproducible view of the game data.
 *
 * Source of truth: `upstream/socialwarriors/config/main.json` (the 29-Aug-2012
 * capture of the original server's configuration) plus the five JSON-Patch
 * deltas in `upstream/socialwarriors/config/patch/`.
 *
 * The build is deliberately strict. A content bundle that cannot be validated
 * is worse than no bundle: the rules engine would fail at runtime, in
 * production, on a machine nobody can reproduce. So the build fails on:
 *
 *   - an unknown top-level section
 *   - a duplicate item id
 *   - a dangling reference (a building that trains a missing unit, an offer
 *     pack that gives a missing item, a collection that contains a missing
 *     item)
 *   - an item with an unknown `properties` key
 *   - an item with an unknown `subcat_functional`
 *   - an item that resolves to no asset
 */

export interface ContentItem {
  id: number;
  name: string;
  /** 'b' building, 'u' unit. */
  type: string;
  category_id: number;
  subcategory_id: number;
  subcat_functional: number;
  img_name: string;
  attack: number;
  defense: number;
  life: number;
  attack_range: number;
  /** Attack interval in FRAMES at 30 fps, not seconds. */
  attack_interval: number;
  population: number;
  /** The legacy single-resource cost. The config leaves it at 0; `costs` is real. */
  cost: number;
  /** The legacy single-resource cost type. Always null in the shipped config. */
  cost_type: string | null;
  /** The build cost, by resource key: `{ w: 125 }`. */
  costs: Record<string, number>;
  /** The `properties` JSON blob, parsed. */
  properties: Record<string, unknown>;
  /** The `best_against` fighting-type key, or null. */
  best_against: string | null;
  best_against_mult: number;
  /** The unit this building trains, if any. */
  trains_ids: number[];
  /** The next tier of this building, if any. */
  upgrades_to: number | null;
  unit_capacity: number;
  building_limit_same_id: number;
  building_limit_same_scf: number;
  /** The footprint, in tiles. */
  width: number;
  height: number;
  /** The level the player must be at to build or buy it. */
  min_level: number;
  /** Seconds to build. */
  build_time: number;
  /** How many clicks the build needs. 0 means instant. */
  clicks_to_build: number;
  /** Seconds to train one unit. */
  training_time: number;
  /** The XP granted by building or training this. */
  xp: number;
  /** Seconds before a collectable building can be harvested. */
  activation: number;
  /** The base amount per collection cycle. */
  collect: number;
  /** The resource produced: g, w, o or s. */
  collect_type: string;
  /** The XP granted by a collection. */
  collect_xp: number;
  /** How many times the building can be harvested. */
  max_collects: number;
  /** The building group: ACADEMY, BUNKER, COMMAND_CENTER, WALL, ... */
  group_type: string;
  /** The faction: 'h' human, '-' neutral. */
  race: string;
  /** Whether it can be bought in the store. */
  in_store: boolean;
  /** Whether it can be gifted. */
  giftable: boolean;
  /** The gift level required. */
  gift_level: number;
  /** The cost of one unit in cash, for the units that cost cash. */
  cost_unit_cash: number;
  /** The volume a unit needs to enter a container. */
  volume: number;
  /** The maximum volume a container accepts. */
  max_elem_vol: number;
  /** The inventory items the building holds, by inventory id. */
  inventory_ids: Record<string, number>;
  /** The cash cost of a premium upgrade, if it has one. */
  premium_upgrade_costs: Record<string, number>;
  /** The raw `properties` string, preserved verbatim. */
  properties_raw: string;
  /** Everything else the config carried, preserved verbatim. */
  extra: Record<string, unknown>;
}

export interface ContentLevel {
  index: number;
  name: string;
  exp_required: number;
  reward_type: string;
  reward_amount: number;
}

export interface ContentGoal {
  id: number;
  title: string;
  description: string;
  hint: string;
  reward: unknown;
}

export interface ContentBundle {
  /** Bumped when the bundle shape changes. */
  formatVersion: 1;
  /** The build id: the SHA-256 of the canonical bundle JSON. */
  buildId: string;
  /** The upstream commit the content was vendored from. */
  upstreamCommit: string;
  /** The patches that were applied, in order. */
  patchesApplied: string[];
  items: ContentItem[];
  levels: ContentLevel[];
  goals: ContentGoal[];
  globals: Record<string, unknown>;
  collections: unknown[];
  inventoryItems: Record<string, unknown>;
  offerPacks: unknown[];
  socialItems: unknown[];
  images: Record<string, string>;
  sounds: unknown[];
  dartsItems: unknown[];
  unitCollectionCategories: Record<string, unknown>;
  magics: unknown[];
  expansionPrices: unknown[];
  neighborAssists: unknown[];
  townPrices: unknown[];
  mapPrices: unknown[];
  findableItems: unknown[];
  levelRankingReward: unknown[];
  categories: Record<string, unknown>;
  /** Items the client knows but the config does not. */
  clientOnlyItemIds: number[];
  /** Items that resolved to no asset file. */
  assetlessItemIds: number[];
  /** The distinct `properties` keys seen, with their usage counts. */
  propertyKeys: Record<string, number>;
  /** The distinct `subcat_functional` values seen, with their usage counts. */
  subcatFunctionals: Record<string, number>;
}
