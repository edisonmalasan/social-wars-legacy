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
  ArmyUnitView,
  BuildingInfoView,
  BuildMenuItem,
  HudInput,
  HudRules,
  ItemPopulation,
  NativeCommand,
  QuestViewOptions,
  StoredItemView,
  RecruitView,
  ResourcePanel,
  UnitCard,
  UnitPanel,
  WorldSnapshot,
} from '@swl/client';
import {
  armyView,
  buildingInfoView,
  completeGoal,
  expand,
  itemType,
  levelOf,
  ownedExpansions,
  productionState,
  resourcePanel,
  storedItems,
  trainingView,
  unitPanel,
} from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';
import { MULTIPLIER_PEASANTS, QUEST_IDS, getQuestSpec } from '@swl/rules';

/** The categories, as the build menu's tabs read them. */
export type Categories = Record<
  string,
  { id: number; name: string; sub?: { id: number; name: string }[] }
>;

/** A finite number from the content's untyped rows, or null. */
function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

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

/**
 * The stored items the inventory draws.
 *
 * The bridge is thin: the model reads the server's `maps[0].store`, and the
 * content supplies the names and the wire types. Nothing about ownership or
 * quantity is decided here.
 */
export function inventoryItems(bundle: ContentBundle, world: WorldSnapshot): StoredItemView[] {
  return storedItems(
    world,
    (bundle.items ?? []).map((item) => ({
      id: item.id,
      name: item.name,
      type: item.type,
      categoryId: item.category_id,
    })),
  );
}

/**
 * The army the base panel draws.
 *
 * The bridge is thin: the model reads the server's store, placed units and
 * finished training queues; the content supplies the names, group types and
 * training times. A caller hosting a team quest may pass that quest's excluded
 * group types so the panel can grey out units the quest will not accept.
 */
export function armyPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  now: number,
  excludedGroupTypes: readonly string[] = [],
): ArmyUnitView[] {
  return armyView(
    world,
    (bundle.items ?? []).map((item) => ({
      id: item.id,
      name: item.name,
      type: item.type,
      groupType: item.group_type ?? '',
      trainingTime: item.training_time ?? 0,
    })),
    now,
    excludedGroupTypes,
  );
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
      // The buy request needs the item's own type. Hardcoding 'b' here is
      // what made a unit bought from the menu be requested as a building.
      type: itemType(item.type),
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

/** A goal, as the goal panel reads it. */
export interface GoalEntry {
  /** The goal's index in the goal list. */
  index: number;
  /** The goal's id. */
  id: number;
  /** The goal's title. */
  title: string;
  /** Whether the player has opened the goal's popup. */
  visited: boolean;
  /** Whether the goal is completed. */
  completed: boolean;
  /**
   * The claim a click on this goal sends, or null when there is none.
   *
   * Every drawn goal carries a claim, complete or not: the client asks and
   * the server decides what its own goal state allows. Only an invalid id
   * or a locally recorded award suppresses it, because re-claiming a paid
   * goal would only earn a refusal.
   */
  command: NativeCommand | null;
}

/** A record, or null. */
function recordOrNull(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

/**
 * The player's goals.
 *
 * The goals themselves are the **content's** — the definitions and their
 * titles — and the player's progress is the **server's**: the goal state
 * in the private state says which goals have been visited and which are
 * complete.
 */
export function goalList(bundle: ContentBundle, world: WorldSnapshot): GoalEntry[] {
  const state = recordOrNull(world.privateState?.['goalState']);
  const visited = recordOrNull(state?.['visited']);
  const completed = recordOrNull(state?.['completed']);
  const awarded = recordOrNull(state?.['awarded']);
  return (bundle.goals ?? []).map((goal, index) => {
    const done = completed?.[String(goal.id)] === true;
    // The server owns completion (awardGoal reads its own progress), so
    // the client must send the claim for an incomplete goal too — that is
    // the gesture the panel draws. Only a goal it cannot name, or one it
    // has already been paid for, has nothing worth sending.
    const canClaim =
      Number.isFinite(goal.id) && awarded?.[String(goal.id)] !== true;
    return {
      index,
      id: goal.id,
      title: goal.title,
      visited: visited?.[String(goal.id)] === true,
      completed: done,
      command: canClaim ? completeGoal(goal.id) : null,
    };
  });
}

/**
 * The player's quest ranks.
 *
 * The ranks are the **server's** — the player's `privateState.questsRank`,
 * the field the upstream writes — and they are keyed by the quest's
 * index, which is its position in the quest list.
 */
export function questRanks(world: WorldSnapshot): Record<number, number> {
  const ranks = world.privateState['questsRank'];
  if (typeof ranks !== 'object' || ranks === null) return {};
  const out: Record<number, number> = {};
  for (const [index, rank] of Object.entries(ranks)) {
    const at = Number(index);
    const value = Number(rank);
    if (Number.isFinite(at) && Number.isFinite(value)) out[at] = value;
  }
  return out;
}

/**
 * The level each quest unlocks at, by the quest's index.
 *
 * The content's global is keyed by the quest's **id**, so the ids are
 * looked up in the quest list: the weekly quest is at the front of the
 * list and the story quests follow it, one-based.
 */
export function questMinLevels(bundle: ContentBundle): Record<number, number> {
  const raw = bundle.globals?.['QUESTS_MIN_LEVELS'];
  if (typeof raw !== 'object' || raw === null) return {};
  const out: Record<number, number> = {};
  for (const [id, level] of Object.entries(raw as Record<string, unknown>)) {
    const index = QUEST_IDS.indexOf(id);
    if (index <= 0) continue;
    if (typeof level === 'number' && Number.isFinite(level)) out[index] = level;
  }
  return out;
}

/**
 * The rules and content a quest's combat panel reads.
 *
 * The losing refs and the event channel are the rules' and the bundle's —
 * neither is a client guess. The labels are the content's item names, used
 * only to name a button; the HP, counters and kills still come from the
 * server's world.
 */
export function questViewOptions(bundle: ContentBundle, questId: string): QuestViewOptions {
  const spec = getQuestSpec(questId);
  const event = bundle.questEvents?.[questId];
  const labels: Record<string, string> = {};
  for (const element of spec?.elements ?? []) {
    const item = (bundle.items ?? []).find((entry) => entry.id === element.itemId);
    if (item) labels[element.ref] = item.name;
  }
  if (event) {
    for (const ref of event.refs) {
      if (labels[ref]) continue;
      const itemId = Number(ref.replace(/^item:/, ''));
      const item = (bundle.items ?? []).find((entry) => entry.id === itemId);
      if (item) labels[ref] = item.name;
    }
  }
  return {
    keyRefs: spec?.keyElementRefs ?? [],
    labels,
    ...(event ? { event } : {}),
  };
}

/**
 * A building's info panel.
 *
 * The model is the client's own (`packages/client/src/tooltips.ts`), and
 * the building is the content's — its name, the resource it produces
 * and the amount it earns per cycle.
 */
export function infoPanel(
  bundle: ContentBundle,
  itemId: number | null,
): ResourcePanel | null {
  if (itemId === null) return null;
  const item = bundle.items?.find((entry) => entry.id === itemId);
  if (!item) return null;
  // Only a building that produces something has the resource panel.
  if (!item.collect_type || !item.collect) return null;
  return resourcePanel({
    name: item.name,
    collect_type: item.collect_type,
    collect: item.collect,
  });
}

/**
 * A unit's info panel.
 *
 * The model is the client's own (`packages/client/src/tooltips.ts`), and
 * the unit is the content's — its statistics are the game's own. The
 * client shows the unit's **effective** attack against what it is aimed
 * at, and the clone has no target, so it shows the base attack: the
 * model's own fallback.
 */
export function unitInfoPanel(
  bundle: ContentBundle,
  itemId: number | null,
): UnitPanel | null {
  if (itemId === null) return null;
  const item = bundle.items?.find((entry) => entry.id === itemId);
  if (!item || item.type !== 'u') return null;
  return unitPanel({
    name: item.name,
    attack: item.attack,
    life: item.life,
    attack_interval: item.attack_interval,
    attack_range: item.attack_range,
    velocity: item.velocity,
    population: item.population,
    best_against_mult: item.best_against_mult,
  });
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

/* -------------------------------------------------------------------------
 * Building management and recruitment
 *
 * These are the bridge between the server's map item, the content and the
 * pure view models in `packages/client/src/management.ts`. They read values;
 * they never build a command or decide an outcome.
 * ---------------------------------------------------------------------- */

/** The map item the player selected, from the server's answer. */
function selectedItem(
  world: WorldSnapshot,
  isoId: number | null,
): readonly number[] | null {
  if (isoId === null) return null;
  return world.maps[0]?.items?.[String(isoId)] ?? null;
}

/** The attribute bag in a map item, or null when there is none. */
function attributesOf(tuple: readonly number[]): Readonly<Record<string, unknown>> | null {
  const attrs: unknown = tuple[6];
  return typeof attrs === 'object' && attrs !== null
    ? (attrs as Record<string, unknown>)
    : null;
}

/**
 * A building's info view, for every building — not only the ones that
 * produce a resource. The name is the content's, the level and the build
 * timestamp are the server's, and the upgrade/hurry views only restate
 * content numbers.
 */
export function buildingInfo(
  bundle: ContentBundle,
  world: WorldSnapshot,
  isoId: number | null,
  now: number,
): BuildingInfoView | null {
  const tuple = selectedItem(world, isoId);
  if (!tuple) return null;
  const item = (bundle.items ?? []).find((entry) => entry.id === Number(tuple[0]));
  if (!item || item.type !== 'b') return null;
  const next = item.upgrades_to === null
    ? null
    : (bundle.items ?? []).find((entry) => entry.id === item.upgrades_to) ?? null;
  return buildingInfoView({
    name: item.name,
    nextName: next?.name ?? null,
    nextMinLevel: next?.min_level ?? null,
    playerLevel: levelOf(world),
    startedAt: Number(tuple[3]),
    buildTime: item.build_time,
    clicksToBuild: item.clicks_to_build,
    now,
  });
}

/** One of the content's four collection periods, as a button. */
export interface ProductionOption {
  /** The 1-based wire value the `activate` command carries. */
  readonly period: number;
  /** The wait, from the content's `COLLECT_MINUTES`. */
  readonly minutes: number;
  /** The payout factor, from the content's `COLLECT_MULTIPLIER`. */
  readonly multiplier: number;
  /**
   * The payout the server's own formula predicts from its stored production
   * state (including any peasant bonus), shown only — never paid here.
   */
  readonly amount: number;
  /** Whether the server's current `cp` is this period. */
  readonly active: boolean;
}

/** The production selector, read from the server's save and the content. */
export interface ProductionPanelView {
  /** The selected building's id, used by the request. */
  readonly isoId: number;
  /** The content's name of the building. */
  readonly name: string;
  /** The resource the building produces. */
  readonly resource: string;
  /** The active period, 1-based; the one-hour period until one is chosen. */
  readonly period: number;
  /** The server's cycle start, zero when the building has never accrued. */
  readonly startedAt: number;
  /** Seconds left by the server's timestamp; presentation only. */
  readonly secondsRemaining: number;
  /** Whether the server already considers this cycle complete. */
  readonly due: boolean;
  /** The four periods the content offers, in their content order. */
  readonly options: readonly ProductionOption[];
}

const FALLBACK_MINUTES = [5, 60, 240, 480];
const FALLBACK_MULTIPLIER = [0.25, 1, 2, 3];

/** A tuple of positive numbers from a global, or the game's own tuple. */
function positiveTuple(value: unknown, fallback: readonly number[]): number[] {
  if (!Array.isArray(value) || value.length < fallback.length) return [...fallback];
  const tuple = value.slice(0, fallback.length);
  const valid = tuple.every(
    (entry) => typeof entry === 'number' && Number.isFinite(entry) && entry > 0,
  );
  return valid ? (tuple as number[]) : [...fallback];
}

/**
 * The server's payout formula (`packages/rules/src/economy.ts:collect`), for
 * display only. The stored `collect` and `unitsInside` are the server's; the
 * content base is used only when a fresh building has no stored amount yet.
 * A building that cannot hold extra units gets no peasant bonus.
 */
function predictedAmount(
  collect: number | null,
  unitsInside: number | null,
  unitCapacity: number | null,
  contentCollect: number,
  multiplier: number,
): number {
  const base = Math.floor(collect ?? contentCollect);
  const extra =
    unitCapacity !== null && unitCapacity > 1
      ? Math.max(0, (unitsInside ?? 0) - 1)
      : 0;
  const raw = extra > 0 ? base + extra * base * MULTIPLIER_PEASANTS : base;
  return Math.floor(Math.floor(raw) * multiplier);
}

/**
 * A multi-collectable building's production panel.
 *
 * The **choices** are the content's (their durations and multipliers) and the
 * **cycle** is the server's (`cp` and `lastAccruedAt` in the item's attribute
 * bag). The countdown is a reading of the server's timestamp against the
 * client's clock; it is presentation only, because the server decides when a
 * collection is due. Nothing here can grant a resource or choose a multiplier.
 */
export function productionPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  isoId: number | null,
  now: number,
): ProductionPanelView | null {
  if (isoId === null) return null;
  const tuple = selectedItem(world, isoId);
  if (!tuple) return null;
  const item = (bundle.items ?? []).find((entry) => entry.id === Number(tuple[0]));
  if (!item || item.type !== 'b') return null;
  if (!item.collect_type || !(item.collect > 0)) return null;
  if ((item.properties as Record<string, unknown> | undefined)?.multiCollectable !== 1) {
    return null;
  }

  const minutes = positiveTuple(bundle.globals?.['COLLECT_MINUTES'], FALLBACK_MINUTES);
  const multipliers = positiveTuple(
    bundle.globals?.['COLLECT_MULTIPLIER'],
    FALLBACK_MULTIPLIER,
  );
  const state = productionState(world, isoId);
  if (!state) return null;
  // buildingState() defaults cp to 1 on the server, so an unchosen period is
  // the 5-minute cycle there. The display must mark that same option active.
  const period = state.period !== null && minutes[state.period - 1] !== undefined
    ? state.period
    : 1;
  const startedAt = state.startedAt !== null && state.startedAt > 0 ? state.startedAt : 0;
  const secondsRemaining = startedAt > 0
    ? Math.max(0, startedAt + minutes[period - 1]! * 60 - now)
    : 0;

  return {
    isoId,
    name: item.name,
    resource: item.collect_type,
    period,
    startedAt,
    secondsRemaining,
    due: secondsRemaining === 0,
    options: minutes.map((value, index) => ({
      period: index + 1,
      minutes: value,
      multiplier: multipliers[index]!,
      amount: predictedAmount(
        state.collect,
        state.unitsInside,
        state.unitCapacity,
        item.collect ?? 0,
        multipliers[index]!,
      ),
      active: index + 1 === period,
    })),
  };
}

/**
 * A training building's recruit view.
 *
 * The trainable units and their names are the content's; the queue count,
 * start time and unit id are the server's, read from the attribute bag. A
 * building with no units listed but a live queue is still shown, so the
 * player can take a unit the server already finished.
 */
export function recruitView(
  bundle: ContentBundle,
  world: WorldSnapshot,
  isoId: number | null,
  now: number,
): RecruitView | null {
  const tuple = selectedItem(world, isoId);
  if (!tuple) return null;
  const item = (bundle.items ?? []).find((entry) => entry.id === Number(tuple[0]));
  if (!item || item.type !== 'b') return null;
  const queue = trainingView(attributesOf(tuple), item.training_time, now);
  if (item.trains_ids.length === 0 && queue.queued <= 0) return null;

  const byId = new Map((bundle.items ?? []).map((entry) => [entry.id, entry]));
  const units: UnitCard[] = [];
  for (const id of item.trains_ids) {
    const unit = byId.get(id);
    if (unit) units.push({ itemId: id, name: unit.name });
  }
  return { buildingName: item.name, units, queue };
}

/* -------------------------------------------------------------------------
 * Expansion
 * ---------------------------------------------------------------------- */

/**
 * The expansion purchase the interface offers.
 *
 * The owned count is the **server's** (its save's expansion list) and the
 * price is the **content's** row at that ordinal. This bridge only reads them.
 * The tile id is a deterministic identifier that is not already owned; the
 * server decides whether that tile may actually be bought, so a refusal is
 * shown through the feedback channel rather than hidden here. A row whose
 * prices are not finite is not a price at all, so the control is hidden rather
 * than drawing a fabricated 0/0.
 */
export interface ExpansionPanelView {
  /** How many tiles the server says the town owns. */
  readonly owned: number;
  /** The gold price, from the content row at the owned ordinal. */
  readonly coins: number;
  /** The cash price, from that same row. */
  readonly cash: number;
  /** A deterministic tile identifier that is not in the server's owned list. */
  readonly tileId: number;
  /** The native command a click sends; the server decides acceptance. */
  readonly command: NativeCommand;
}

/** The expansion view, from the server's owned count and the content's prices. */
export function expansionPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
): ExpansionPanelView | null {
  const owned = ownedExpansions(world);
  const row = recordOrNull((bundle.expansionPrices ?? [])[owned.length]);
  if (!row) return null;
  const coins = finite(row['coins']);
  const cash = finite(row['cash']);
  if (coins === null || cash === null) return null;
  const tileId = Math.floor(Math.max(0, ...owned)) + 1;
  return {
    owned: owned.length,
    coins,
    cash,
    tileId,
    command: expand(tileId),
  };
}
