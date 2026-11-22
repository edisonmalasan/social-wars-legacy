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
  AssaultCountdownView,
  AssaultHistoryView,
  AssaultResultView,
  BuildingInfoView,
  BuildMenuItem,
  BuildTab,
  CameraState,
  DialogContent,
  FeedbackMessage,
  HudInput,
  HudRules,
  ItemPopulation,
  NativeCommand,
  Popover,
  QuestBriefing,
  QuestChoice,
  QuestResultOptions,
  QuestResultView,
  QuestViewOptions,
  SpecialAttackChargeView,
  StoredItemView,
  RecruitView,
  ResourcePanel,
  TutorialStep,
  UnitCard,
  UnitPanel,
  WorldSnapshot,
} from '@swl/client';
import { DAMAGE_CLASSES } from '@swl/rules';
import {
  armyView,
  assaultCountdown,
  assaultHistory,
  battleOptions,
  buyOfferPack,
  briefingView,
  buildingInfoView,
  buildTabs,
  completeGoal,
  expand,
  lastAssaultResult,
  questResultActionChoice,
  specialAttackHud,
  tileToPixel,
  tutorialLiteral,
  viewportOf,
  itemType,
  levelOf,
  MAX_ZOOM,
  MIN_ZOOM,
  magicBook,
  magicInputFromWorld,
  magicLab,
  type MagicBookPage,
  type MagicLabPage,
  ownedExpansions,
  productionState,
  resourcePanel,
  storedItems,
  trainingView,
  unitPanel,
} from '@swl/client';
import type { ContentBundle, ContentItem } from '@swl/content';
import {
  MULTIPLIER_PEASANTS,
  QUEST_IDS,
  bonusesForLevel,
  getQuestSpec,
  levelForXp,
  maxLevel,
  parseXpTable,
  xpForLevel,
  isOfferPackAvailable,
  offerPackCandidates,
  offerPackPrice,
  offerPackShape,
  offerPackTierForCount,
  type Army,
  type OfferPackData,
  type XpLevelRow,
} from '@swl/rules';

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
  /** The client's own "buy for" prompt, from `GUI/ItemButtonLargeExpand2.as`. */
  readonly buyFor: string;
  /**
   * Display-only requirement prompts named by the content row.
   *
   * Each is the original's own literal, shown only when the server's own
   * wallet or neighbour count is short; they are **not** gates. The
   * `neighbors` and `inventory_qte` columns remain deferred server-side, and
   * the one button always sends the same expand request.
   */
  readonly prompts: readonly ExpansionPrompt[];
}

/** The client's own literals on `GUI/ItemButtonLargeExpand2.as`. */
export const EXPANSION_BUY_FOR = 'buy for';
export const EXPANSION_CASH_PROMPT =
  "Oh no! You don't have enough cash! Would you like to get some more?";
export const EXPANSION_NEIGHBOURS_PROMPT =
  'You need more neighbours to expand your base.\nWanna get some more?\n Easy, invite your friends!';
export const EXPANSION_GOLD_PROMPT =
  'You need more gold to expand your base.\n Wanna get some now?';

/** One unmet requirement the content's expansion row names, shown as a prompt. */
export interface ExpansionPrompt {
  /** Which content column names the requirement. */
  readonly kind: 'cash' | 'gold' | 'neighbours';
  /** The amount the content row names; never a client-side gate. */
  readonly needed: number;
  /** The server's own count that was compared and found short. */
  readonly have: number;
  /** The client's own literal, never a server-written message. */
  readonly text: string;
}

/**
 * The expansion view, from the server's owned count and the content's prices.
 *
 * `neighbourCount` is the server's own neighbour list length when the host has
 * fetched it; a caller that does not have it passes null and no neighbour
 * prompt is drawn, because the client must not guess a count it cannot read.
 */
export function expansionPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  neighbourCount: number | null = null,
): ExpansionPanelView | null {
  const owned = ownedExpansions(world);
  const row = recordOrNull((bundle.expansionPrices ?? [])[owned.length]);
  if (!row) return null;
  const coins = finite(row['coins']);
  const cash = finite(row['cash']);
  if (coins === null || cash === null) return null;
  const tileId = Math.floor(Math.max(0, ...owned)) + 1;
  const prompts: ExpansionPrompt[] = [];
  const gold = finite(world.resources?.['g']);
  const playerCash = finite(world.resources?.['c']);
  const short = (needed: number, have: number | null): boolean =>
    have !== null && have < needed;
  if (short(cash, playerCash) && playerCash !== null) {
    prompts.push({ kind: 'cash', needed: cash, have: playerCash, text: EXPANSION_CASH_PROMPT });
  }
  if (short(coins, gold) && gold !== null) {
    prompts.push({ kind: 'gold', needed: coins, have: gold, text: EXPANSION_GOLD_PROMPT });
  }
  const neighbours = finite(row['neighbors']);
  if (neighbours !== null && neighbours > 0 && short(neighbours, neighbourCount) && neighbourCount !== null) {
    prompts.push({
      kind: 'neighbours',
      needed: neighbours,
      have: neighbourCount,
      text: EXPANSION_NEIGHBOURS_PROMPT,
    });
  }
  return {
    owned: owned.length,
    coins,
    cash,
    tileId,
    command: expand(tileId),
    buyFor: EXPANSION_BUY_FOR,
    prompts,
  };
}

/* -------------------------------------------------------------------------
 * The post-purchase growth result
 *
 * The celebration is a reading of **two** server answers: the owned-expansion
 * list before the request and the one the server returned after it. It is
 * drawn only when the list actually grew, and the new tile ids are the tail
 * of the server's own list. Nothing here grants a tile, decides a purchase or
 * opens a second modal — the result is an inline extension of the expansion
 * control. The original's `expGen.png` art and its Share! popup are excluded.
 * ---------------------------------------------------------------------- */

/** The client's own celebration literals on `popups/PopupExpand.as`. */
export const EXPANSION_CELEBRATION_HEADING = 'Congratulations!';
export const EXPANSION_CELEBRATION_MESSAGE = 'Your empire has GROWN!';

/** The stable id of the inline growth-result region in the expansion control. */
export const EXPANSION_RESULT_ID = 'expansion-result';

/** The growth the server answered, with only values it actually published. */
export interface ExpansionResultView {
  /** The count before the accepted request, as the server had it. */
  readonly before: number;
  /** The count in the server's answer. */
  readonly after: number;
  /** The tiles the server added, in its own list order. */
  readonly tiles: readonly number[];
  /** The content price at the ordinal that was bought; display only. */
  readonly coins: number | null;
  readonly cash: number | null;
  /** The client's own celebration literals. */
  readonly heading: string;
  readonly message: string;
}

/**
 * Read the growth result, or null when the server answered no growth.
 *
 * `before` is the owned count from the world the command was sent with. A
 * refused or replayed expansion leaves the count unchanged, so no celebration
 * is drawn. A malformed new tile is dropped rather than claimed. This is a
 * reading of the server's list, never a purchase made locally.
 */
export function expansionResultPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  before: number,
): ExpansionResultView | null {
  if (!Number.isInteger(before) || before < 0) return null;
  const owned = ownedExpansions(world);
  if (owned.length <= before) return null;
  const tiles = owned.slice(before);
  if (tiles.some((tile) => !Number.isInteger(tile) || tile <= 0)) return null;
  const row = recordOrNull((bundle.expansionPrices ?? [])[before]);
  return {
    before,
    after: owned.length,
    tiles,
    coins: row ? finite(row['coins']) : null,
    cash: row ? finite(row['cash']) : null,
    heading: EXPANSION_CELEBRATION_HEADING,
    message: EXPANSION_CELEBRATION_MESSAGE,
  };
}

/* -------------------------------------------------------------------------
 * Collections
 *
 * The catalogue is the content's ten collection rows; the progress and the
 * completion state are the server's (`maps[0].store` and
 * `privateState.collections`). The prize is shown as content text only. There
 * is no claim gesture: awarding a collection prize is the server's job, and
 * this panel never pretends to have done it.
 * ---------------------------------------------------------------------- */

/** One required unit in a collection, named by content and present in the store. */
export interface CollectionItemView {
  /** The content id of the required item. */
  readonly itemId: number;
  /** The content's name, or the id when the content names none. */
  readonly name: string;
  /** The quantity the server's store holds; zero when it holds none. */
  readonly quantity: number;
}

/** One collection row as the tab draws it. */
export interface CollectionEntryView {
  /** The content's one-based collection id. */
  readonly id: number;
  readonly name: string;
  readonly description: string;
  /** The content's cash price, or null when it is not a finite number. */
  readonly cashPrice: number | null;
  /** The content's required items, with the server's held quantities. */
  readonly items: readonly CollectionItemView[];
  /** How many required items the server's store holds. */
  readonly held: number;
  /** Whether the server's `collections` list names this id. */
  readonly completed: boolean;
  /** The content's prize, rendered as text. Never a granted reward. */
  readonly prize: string;
}

/** The collections tab's body. */
export interface CollectionsPanelView {
  readonly entries: readonly CollectionEntryView[];
}

/** An integer id from the content's string-or-number fields, or null. */
function contentId(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isInteger(value) && value > 0 ? value : null;
  }
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
    const id = Number(value.trim());
    return Number.isInteger(id) && id > 0 ? id : null;
  }
  return null;
}

/** Parse a content field that holds a JSON array, or an empty array. */
function jsonIds(value: unknown): number[] {
  if (typeof value !== 'string') return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const out: number[] = [];
  for (const entry of parsed) {
    const id = contentId(entry);
    if (id !== null) out.push(id);
  }
  return out;
}

/** The items the server's store holds, by content id. */
function storedQuantities(world: WorldSnapshot): Map<number, number> {
  const out = new Map<number, number>();
  const store = world.maps[0]?.store;
  if (!store || typeof store !== 'object' || Array.isArray(store)) return out;
  for (const [key, value] of Object.entries(store)) {
    const id = contentId(key);
    const quantity = finite(value);
    if (id !== null && quantity !== null && quantity > 0) out.set(id, Math.trunc(quantity));
  }
  return out;
}

/** Render the content's prize record as names, without granting anything. */
function prizeText(
  value: unknown,
  names: Map<number, string>,
): string {
  if (typeof value !== 'string') return '';
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    return '';
  }
  const record = recordOrNull(parsed);
  if (!record) return '';
  const rows: string[] = [];
  for (const [key, amount] of Object.entries(record)) {
    const id = contentId(key);
    const quantity = finite(amount);
    if (id === null || quantity === null || quantity <= 0) continue;
    rows.push(`${names.get(id) ?? `item ${id}`} ×${Math.trunc(quantity)}`);
  }
  return rows.join(', ');
}

/**
 * The content's collections and the server's progress, in content order.
 *
 * Names, descriptions, prices, required items and prize text are the
 * content's; quantities and the completed ids are the server's. A malformed
 * content row is skipped rather than drawn as a fabricated collection, and a
 * prize is only ever rendered as text.
 */
export function collectionsPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
): CollectionsPanelView {
  const names = new Map<number, string>();
  for (const item of bundle.items ?? []) names.set(item.id, item.name);
  const quantities = storedQuantities(world);
  const completed = new Set<number>();
  const rawCompleted = world.privateState?.['collections'];
  if (Array.isArray(rawCompleted)) {
    for (const entry of rawCompleted) {
      const id = contentId(entry);
      if (id !== null) completed.add(id);
    }
  }
  const entries: CollectionEntryView[] = [];
  for (const raw of bundle.collections ?? []) {
    const row = recordOrNull(raw);
    if (!row) continue;
    const id = contentId(row['id']);
    if (id === null || typeof row['name'] !== 'string') continue;
    const itemIds = jsonIds(row['item_ids']);
    if (itemIds.length === 0) continue;
    const items = itemIds.map((itemId) => ({
      itemId,
      name: names.get(itemId) ?? `item ${itemId}`,
      quantity: quantities.get(itemId) ?? 0,
    }));
    const cash = typeof row['cashPrice'] === 'string'
      ? contentId(row['cashPrice'])
      : finite(row['cashPrice']);
    entries.push({
      id,
      name: row['name'],
      description: typeof row['description'] === 'string' ? row['description'] : '',
      cashPrice: cash,
      items,
      held: items.filter((entry) => entry.quantity > 0).length,
      completed: completed.has(id),
      prize: prizeText(row['prize'], names),
    });
  }
  return { entries };
}

/**
 * The Research LAB's page, from the server's save and the content's spells.
 *
 * The bridge only feeds the model the two sources it needs. Ordering, paging,
 * the learned/available/blocked labels and what can be afforded are the
 * model's, and buying is a request the server answers.
 */
export function magicLabPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  page: number,
): MagicLabPage {
  const input = magicInputFromWorld(
    world,
    bundle.magics ?? [],
    bundle.globals ?? {},
  );
  return magicLab(input, page);
}

/**
 * The battle spell book's page, from the server's save and the content.
 *
 * The quest's veto is passed in by the host, which owns the active quest. The
 * model decides nothing: it only lists the learned spells, their levels and
 * what the server-issued mana can pay for.
 */
export function magicBookPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  page: number,
  disabledSpells: readonly number[] = [],
): MagicBookPage {
  const input = magicInputFromWorld(
    world,
    bundle.magics ?? [],
    bundle.globals ?? {},
    disabledSpells,
  );
  return magicBook(input, page);
}

/* -------------------------------------------------------------------------
 * Assault result, history and the combat HUD
 *
 * The selectors in `packages/client/src/featurestate.ts` copy the server's
 * answer; these bridges add only the content's names, the client's own text
 * and the command a gesture sends. Nothing here settles a fight, prices loot,
 * writes a history row or decides that a special attack is charged.
 * ---------------------------------------------------------------------- */

/** The result popup's body: the server's answer and the player's army. */
export interface AssaultResultPanelView {
  /** The last outcome and the loot rows, if any, the server persisted. */
  readonly result: AssaultResultView;
  /** The roster the server's save accounts for, named by the content. */
  readonly army: readonly ArmyUnitView[];
}

/** Build the result popup's view, or null when the server answered no assault. */
export function assaultResultPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  now: number,
): AssaultResultPanelView | null {
  const result = lastAssaultResult(world);
  if (!result) return null;
  return { result, army: armyPanel(bundle, world, now) };
}

/** The history popup's body. */
export interface AssaultHistoryPanelView {
  /** The attacks the server actually answered. */
  readonly history: AssaultHistoryView;
  /** The countdown to the server's attack reset, when it published one. */
  readonly countdown: AssaultCountdownView | null;
}

/** Build the history popup's view, or null when the save has no history keys. */
export function assaultHistoryPanel(
  world: WorldSnapshot,
  now: number,
): AssaultHistoryPanelView | null {
  const history = assaultHistory(world);
  if (!history) return null;
  return { history, countdown: assaultCountdown(world, now) };
}

/** One defensive strategy the player can ask the server to adopt. */
export interface BattleStrategyOption {
  /** The 1-based wire value of the `set_strategy` command. */
  readonly strategy: number;
  /** The client's own label for the strategy. */
  readonly name: string;
  /** The client's own explanation, from the original's battle-options text. */
  readonly description: string;
  /** The request a click sends; the server decides whether it applies. */
  readonly command: NativeCommand;
}

/** The battle-options popup's body. */
export interface BattleOptionsPanelView {
  /** The server's choice, or null when the save has none to read. */
  readonly selected: number | null;
  /** The four strategies, in the original's order. */
  readonly options: readonly BattleStrategyOption[];
}

/**
 * The four defensive strategies and the server's chosen one.
 *
 * The names and descriptions are the client's text, not game state. The
 * selected strategy and the effect of a click are the server's: this bridge
 * only builds the `set_strategy` request from the command catalogue.
 */
export function battleOptionsPanel(world: WorldSnapshot): BattleOptionsPanelView {
  const descriptions: readonly string[] = [
    'All your units will hold position until approached. They will stop chasing the enemy and return to their original position in a while after the clash.',
    'All your units will hold position until a siege engine hits, then all ranged units will go and crush it.',
    'All your units will hold positions until the enemy hits. Then part of your army that equals to the enemy troops will go and chase them.',
    'All your units will attack the siege engines right from the start and will return to the empire only when all are destroyed.',
  ];
  const names: readonly string[] = [
    'Defensive',
    'Mid Defensive',
    'Mid Aggressive',
    'Aggressive',
  ];
  return {
    selected: battleOptions(world)?.selected ?? null,
    options: descriptions.map((description, index) => {
      const strategy = index + 1;
      return {
        strategy,
        name: names[index]!,
        description,
        command: { map: 0, name: 'set_strategy', args: [strategy] },
      };
    }),
  };
}

/** The combat HUD's body: the server-owned timer and charge records. */
export interface AssaultHudPanelView {
  /** Countdown to the server's attack reset, when it published one. */
  readonly countdown: AssaultCountdownView | null;
  /** Only the special attacks whose charge the server published. */
  readonly specialAttacks: readonly SpecialAttackChargeView[];
}

/** Build the combat HUD's view from the server's charge and reset state. */
export function assaultHudPanel(world: WorldSnapshot, now: number): AssaultHudPanelView {
  return {
    countdown: assaultCountdown(world, now),
    specialAttacks: specialAttackHud(world),
  };
}

/** The four panels the shared dialog can host for the assault family. */
export type AssaultPanelKind = 'result' | 'history' | 'options' | 'hud';

/** A dialog descriptor for one assault panel, for the host's one dialog slot. */
export function assaultDialog(kind: AssaultPanelKind): DialogContent {
  const titles: Record<AssaultPanelKind, string> = {
    result: 'Battle Result',
    history: 'Battle Results',
    options: 'OPTIONS',
    hud: 'Combat',
  };
  const dialogKinds: Record<AssaultPanelKind, DialogContent['kind']> = {
    result: 'result',
    history: 'alert',
    options: 'confirm',
    hud: 'combat',
  };
  return { id: `assault-${kind}`, kind: dialogKinds[kind], title: titles[kind] };
}

/* -------------------------------------------------------------------------
 * Onboarding, mission information and confirmation
 *
 * These are the client's own panels for things the server already owns: the
 * tutorial's steps, a quest's briefing, the server's next-mission reading and
 * a yes/no gate on a request. Every row below is a *reading* of the client's
 * tutorial model or of the authoritative quest models — no copy is invented
 * here, and nothing here starts, finishes or scores a mission.
 * ---------------------------------------------------------------------- */

/** One tutorial step as the intro/help panel reads it. */
export interface TutorialHelpStep {
  /** The step's identifying number, from the client's own step list. */
  readonly step: number;
  /** Its one-based place in this player's visible list. */
  readonly position: number;
  /** The client's own literal title. */
  readonly title: string;
  /** The client's own literal lesson. */
  readonly lesson: string;
  /** Whether the client allows this step to be skipped. */
  readonly skippable: boolean;
  /** Whether the tutorial is currently pointing at this step. */
  readonly current: boolean;
}

/** The intro/help panel's body. */
export interface TutorialHelpView {
  /** How many steps this player sees. */
  readonly total: number;
  /** The current step's one-based place, or 0 when there is none. */
  readonly currentPosition: number;
  /** The steps, in the client's own order. */
  readonly steps: readonly TutorialHelpStep[];
}

/**
 * The tutorial's steps as the intro/help panel shows them.
 *
 * The text comes from `tutorialLiteral` on the extracted steps, so it is the
 * client's own wording and never a paraphrase written for this panel. The
 * order is the state machine's order, and the current flag is the step number
 * the `Tutorial` instance says it is on. The player can only see a step whose
 * gate the tutorial model opened.
 */
export function tutorialHelpView(
  visible: readonly TutorialStep[],
  current: TutorialStep | null,
): TutorialHelpView {
  const currentStep = current?.step ?? null;
  const steps = visible.map((step, index) => ({
    step: step.step,
    position: index + 1,
    title: tutorialLiteral(step.title),
    lesson: tutorialLiteral(step.lesson),
    skippable: step.skippable === true,
    current: currentStep !== null && step.step === currentStep,
  }));
  return {
    total: steps.length,
    currentPosition: steps.findIndex((entry) => entry.step === currentStep) + 1,
    steps,
  };
}

/**
 * The mission-info panel's body: the same briefing the quest dialog draws.
 *
 * The title and subtitle are the content's and the rules', the army is the
 * server's save, and the difficulty is the player's own gesture. This bridge
 * only feeds `briefingView`; it never decides whether a mission may start.
 */
export function missionInfoPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  choice: QuestChoice,
  difficulty: unknown,
  now: number,
): QuestBriefing {
  return briefingView(choice, difficulty, armyPanel(bundle, world, now));
}

/** The next-mission panel's body, from the server's own answered result. */
export interface NextMissionView {
  /** The server's one-based play index for the offered mission. */
  readonly index: number;
  /** The authoritative quest id. */
  readonly questId: string;
  /** The rules' display title. */
  readonly title: string;
  /** Whether the server says the mission can be started now. */
  readonly available: boolean;
  /** The win the server answered, shown as context and never re-decided. */
  readonly won: boolean;
  /** The rank the server recorded, when it answered a win. */
  readonly rank: number | null;
  /** The exact reward rows the server paid. */
  readonly rewards: QuestResultView['rewards'];
}

/**
 * Offer the next mission only when the server's result still does.
 *
 * `questResultActionChoice` recomputes the same rank-and-unlock gate the
 * result dialog's Next button used. A result with no next mission, or one
 * whose availability has since changed, fails closed: the panel is not drawn
 * rather than offering a mission the server would refuse.
 */
export function nextMissionPanel(
  result: QuestResultView,
  options: QuestResultOptions,
): NextMissionView | null {
  const next = result.next;
  if (!next) return null;
  const choice = questResultActionChoice(result, next.questId, 'next', options);
  if (!choice) return null;
  return {
    index: choice.index,
    questId: choice.questId,
    title: choice.title,
    available: next.available && choice.unlocked,
    won: result.won,
    rank: result.rank,
    rewards: result.rewards,
  };
}

/** The client's own confirmation button texts, from `popups/PopupConfirm.as`. */
export const CONFIRM_YES = 'YES';
export const CONFIRM_NO = 'NO';
/** The client's own headings for the intro, help and confirmation panels. */
export const INTRO_TITLE = 'Welcome to Social Wars';
export const HELP_TITLE = 'HELP!';
export const CONFIRM_TITLE = 'Are you sure?';

/** The confirmation panel's body. */
export interface ConfirmView {
  /** The question, naming the request the player is being asked to send. */
  readonly message: string;
  /** The client's own affirmative label. */
  readonly yes: string;
  /** The client's own negative label. */
  readonly no: string;
}

/** A yes/no panel using the client's own button texts. */
export function confirmPanel(message: string): ConfirmView {
  return { message, yes: CONFIRM_YES, no: CONFIRM_NO };
}

/** The body hosted by the one dialog for the onboarding family. */
export type OnboardingPanelView =
  | { readonly kind: 'intro'; readonly view: TutorialHelpView }
  | { readonly kind: 'help'; readonly view: TutorialHelpView }
  | { readonly kind: 'mission'; readonly view: QuestBriefing }
  | { readonly kind: 'next'; readonly view: NextMissionView }
  | { readonly kind: 'confirm'; readonly view: ConfirmView };

/** Each onboarding screen has its own gesture and its own dialog id. */
export type OnboardingPanelKind = 'intro' | 'help' | 'mission' | 'next' | 'confirm';

/**
 * The one dialog's descriptor for an onboarding panel.
 *
 * Ids are distinct so a host can open each screen with its own gesture, but
 * the slot is still the single one in `dialogmodel.ts`: opening another panel
 * replaces this one, and no second overlay is ever created.
 */
export function onboardingDialog(kind: OnboardingPanelKind, title: string): DialogContent {
  const kinds: Record<OnboardingPanelKind, DialogContent['kind']> = {
    intro: 'alert',
    help: 'alert',
    mission: 'briefing',
    next: 'result',
    confirm: 'confirm',
  };
  return { id: `onboarding-${kind}`, kind: kinds[kind], title };
}

/* -------------------------------------------------------------------------
 * The army roster, the team thumbnails and the unit-XP display
 *
 * These three readings share one subject: the units the server's save
 * accounts for. The roster lists them (`armyView`), the thumbnails echo the
 * team the server bound to the active quest, and the XP card reads the xp the
 * server stored on a placed unit through the rules' XP table. Nothing here
 * grants, levels or fields a unit locally.
 * ---------------------------------------------------------------------- */

/** The client's own literals on `GUI/UnitXPLevelInfoDisplay.as`. */
export const UNIT_XP_LEVEL_UP = 'LEVEL UP';
export const UNIT_XP_LABEL = 'Unit Level';
export const UNIT_XP_HINT = 'Defeat enemies to level up your unit!!';

/** The XP table from the content globals, or an empty table when malformed. */
function xpTable(bundle: ContentBundle): XpLevelRow[] {
  try {
    return parseXpTable(bundle.globals?.['UNIT_XP_LEVELS_MULTIPLIERS_10']);
  } catch {
    return [];
  }
}

/**
 * The xp the server recorded on each placed unit type, by content id.
 *
 * A unit's accumulated xp is an attribute key the world sends verbatim. When
 * more than one unit of a type is placed, the highest value is the level the
 * server has actually reached for that type; summing them would invent a
 * level no single unit owns.
 */
export function unitXpByItem(world: WorldSnapshot): Map<number, number> {
  const out = new Map<number, number>();
  for (const tuple of Object.values(world.maps[0]?.items ?? {})) {
    if (!Array.isArray(tuple)) continue;
    const itemId = Number(tuple[0]);
    const attrs = tuple[6];
    if (!Number.isInteger(itemId) || itemId <= 0) continue;
    if (!attrs || typeof attrs !== 'object' || Array.isArray(attrs)) continue;
    const xp = Number((attrs as Record<string, unknown>)['xp']);
    if (!Number.isFinite(xp) || xp <= 0) continue;
    out.set(itemId, Math.max(out.get(itemId) ?? 0, Math.trunc(xp)));
  }
  return out;
}

/** One unit's XP card: the client's words and the rules' own level. */
export interface UnitXpView {
  readonly itemId: number;
  readonly name: string;
  /** The xp the server stored on the unit. */
  readonly xp: number;
  readonly level: number;
  readonly maxLevel: number;
  /** One filled star per earned level, then the empty ones. */
  readonly stars: string;
  readonly attackBonus: number;
  readonly lifeBonusPercent: number;
  /** XP the next level needs, or null once the unit is at the maximum. */
  readonly nextLevelXp: number | null;
  readonly title: string;
  readonly label: string;
  readonly hint: string;
}

/** Build a unit's XP card from the content and the server's xp, or null. */
export function unitXpPanel(
  bundle: ContentBundle,
  itemId: number,
  xp: number,
): UnitXpView | null {
  const item = (bundle.items ?? []).find((entry) => entry.id === itemId);
  if (!item || item.type !== 'u') return null;
  const table = xpTable(bundle);
  const life = Number.isFinite(item.life) && item.life > 0 ? item.life : 0;
  const earned = Number.isFinite(xp) && xp > 0 ? Math.trunc(xp) : 0;
  const highest = table.length > 1 ? maxLevel(table) : 0;
  // With no table or no base life the rules cannot compute a level, so the
  // card shows level zero rather than inventing one.
  const level = life > 0 && table.length > 1 ? levelForXp(table, life, earned) : 0;
  const bonuses = level > 0 ? bonusesForLevel(table, life, level) : null;
  const next = level < highest ? level + 1 : null;
  return {
    itemId,
    name: item.name,
    xp: earned,
    level,
    maxLevel: highest,
    stars: '★'.repeat(level) + '☆'.repeat(Math.max(0, highest - level)),
    attackBonus: bonuses?.extraAttack ?? 0,
    lifeBonusPercent: bonuses?.extraLifePercent ?? 0,
    nextLevelXp: next !== null && next < table.length ? xpForLevel(table, life, next) : null,
    title: UNIT_XP_LEVEL_UP,
    label: UNIT_XP_LABEL,
    hint: UNIT_XP_HINT,
  };
}

/** One roster row: the server's unit, named by content and levelled by rules. */
export interface RosterUnitView extends ArmyUnitView {
  /** The xp the server stored for this unit type. */
  readonly xp: number;
  /** The level the rules derive from that xp. */
  readonly level: number;
  /** The XP card drawn when this row is inspected. */
  readonly card: UnitXpView;
}

/** One thumbnail: the activate/deactivate state the original toggles. */
export interface TeamThumbView {
  readonly itemId: number;
  readonly name: string;
  readonly level: number;
  /** The count the server accepted; zero for a deactivated thumbnail. */
  readonly count: number;
  readonly active: boolean;
}

/**
 * The thumbnails for the team the server bound to the active quest.
 *
 * Every roster unit gets one: units in the accepted team are active and carry
 * the server's count, the rest are deactivated and carry zero. A world with no
 * active team produces no thumbnails at all — the client never claims a team
 * the server did not accept.
 */
export function teamThumbnails(
  roster: readonly RosterUnitView[],
  team: Army | null | undefined,
): TeamThumbView[] {
  if (!team || team.length === 0) return [];
  const accepted = new Map<number, number>();
  for (const entry of team) {
    if (!Number.isInteger(entry.unitId) || entry.unitId <= 0) continue;
    const count = Number(entry.count);
    if (!Number.isFinite(count) || count <= 0) continue;
    accepted.set(entry.unitId, Math.max(0, Math.trunc(count)));
  }
  if (accepted.size === 0) return [];
  return roster.map((unit) => ({
    itemId: unit.itemId,
    name: unit.name,
    level: unit.level,
    count: accepted.get(unit.itemId) ?? 0,
    active: (accepted.get(unit.itemId) ?? 0) > 0,
  }));
}

/** The roster panel's whole body, read from the server and the content. */
export interface RosterPanelView {
  readonly units: readonly RosterUnitView[];
  readonly thumbnails: readonly TeamThumbView[];
  /** True when the server has actually accepted a team to show. */
  readonly teamAccepted: boolean;
}

/** Build the roster, its thumbnails and every unit's XP card. */
export function rosterPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  now: number,
  team: Army | null | undefined = null,
  excludedGroupTypes: readonly string[] = [],
): RosterPanelView {
  const xpByItem = unitXpByItem(world);
  const units: RosterUnitView[] = [];
  for (const unit of armyPanel(bundle, world, now, excludedGroupTypes)) {
    const xp = xpByItem.get(unit.itemId) ?? 0;
    const card = unitXpPanel(bundle, unit.itemId, xp);
    // armyView only names content units, so a missing card means malformed
    // content. Skip it rather than draw a level the rules cannot support.
    if (!card) continue;
    units.push({ ...unit, xp, level: card.level, card });
  }
  const thumbnails = teamThumbnails(units, team);
  return { units, thumbnails, teamAccepted: thumbnails.length > 0 };
}

/** The one dialog's id for the roster panel. */
export const ROSTER_DIALOG_ID = 'roster-army';

/** The one dialog's descriptor for the roster panel. */
export function rosterDialog(): DialogContent {
  return { id: ROSTER_DIALOG_ID, kind: 'alert', title: 'Your Army' };
}

/* ----------------------------------------------------------------------
 * UI chrome
 *
 * The reusable pieces the original draws as tabs, pills, popovers, a zoom
 * slider, a speaker box, collect/hurry buttons, world-space attachables and
 * a cover. Every view here is a **reading** of the server's answer, the
 * content or the camera: the tab and pill state is UI state, the zoom is the
 * camera model, and the collect/hurry rows only describe requests the host
 * sends. None of it owns a world, a resource or an outcome.
 * -------------------------------------------------------------------- */

/** One tab or sub-category pill, with its UI-only selection and hover state. */
export interface ChromeTabView {
  readonly id: string;
  readonly label: string;
  readonly selected: boolean;
  readonly hovered: boolean;
}

/** The selection/hover state a tab strip or pill row owns. */
export interface TabStripState {
  readonly selectedId: string | null;
  readonly hoveredId: string | null;
}

/** The empty strip: nothing selected, nothing hovered. */
export const EMPTY_TAB_STRIP: TabStripState = Object.freeze({
  selectedId: null,
  hoveredId: null,
});

/** A gesture on a strip. Hovering null means the pointer left the row. */
export type TabStripAction =
  | { readonly type: 'select'; readonly id: string }
  | { readonly type: 'hover'; readonly id: string | null };

/**
 * Select or hover one entry.
 *
 * The original's `highlightTab/fadeTab` and `seleccionar/deseleccionar` are
 * one selection slot; `overPastilla/outPastilla` is one hover slot. Both are
 * replaced, never accumulated, and neither touches game state.
 */
export function tabStrip(state: TabStripState, action: TabStripAction): TabStripState {
  if (action.type === 'hover') {
    if (state.hoveredId === action.id) return state;
    return { ...state, hoveredId: action.id };
  }
  if (state.selectedId === action.id) return state;
  return { ...state, selectedId: action.id };
}

/** Pair entries with a strip's state for drawing. */
export function tabViews(
  entries: readonly { readonly id: string; readonly label: string }[],
  state: TabStripState,
): readonly ChromeTabView[] {
  return entries.map((entry) => ({
    id: entry.id,
    label: entry.label,
    selected: entry.id === state.selectedId,
    hovered: entry.id === state.hoveredId,
  }));
}

/**
 * The content's build categories as string ids, so a category and its
 * sub-categories cannot collide in one strip's state.
 */
export function chromeBuildTabs(
  categories: Categories,
): { id: string; label: string; subs: { id: string; label: string }[] }[] {
  return buildTabs(categories).map((tab: BuildTab) => ({
    id: `cat:${tab.id}`,
    label: tab.name,
    subs: tab.subcategories.map((sub) => ({ id: `sub:${sub.id}`, label: sub.name })),
  }));
}

/** The content entries a chosen category and sub-category pill show. */
export function chromeCatalogue(
  items: readonly BuildMenuItem[],
  categoryId: string | null,
  subcategoryId: string | null,
): readonly BuildMenuItem[] {
  if (categoryId === null) return [];
  const category = Number(categoryId.slice('cat:'.length));
  const sub = subcategoryId === null ? null : Number(subcategoryId.slice('sub:'.length));
  return items.filter(
    (entry) =>
      entry.categoryId === category &&
      (sub === null || entry.subcategoryId === sub),
  );
}

/** The zoom slider's reading of the camera model. */
export interface ZoomView {
  readonly zoom: number;
  /** The camera's zoom as an integer percent, for the range input. */
  readonly percent: number;
  readonly minPercent: number;
  readonly maxPercent: number;
  readonly canZoomIn: boolean;
  readonly canZoomOut: boolean;
  readonly label: string;
}

/** Read the camera's zoom without changing it. The bounds are `camera.ts`'s. */
export function zoomView(camera: CameraState): ZoomView {
  const zoom = Number.isFinite(camera.zoom)
    ? Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, camera.zoom))
    : 1;
  return {
    zoom,
    percent: Math.round(zoom * 100),
    minPercent: Math.round(MIN_ZOOM * 100),
    maxPercent: Math.round(MAX_ZOOM * 100),
    canZoomIn: zoom < MAX_ZOOM,
    canZoomOut: zoom > MIN_ZOOM,
    label: `Zoom ${Math.round(zoom * 100)}%`,
  };
}

/** A range-input percent as a camera zoom, clamped to the camera's own range. */
export function zoomFromPercent(camera: CameraState, percent: number): CameraState {
  const value = Number.isFinite(percent) ? percent / 100 : 1;
  return { ...camera, zoom: Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value)) };
}

/** The one speaker-box notice, read from the server's last answer. */
export interface SpeakerNotice {
  readonly id: string;
  readonly text: string;
  readonly tone: FeedbackMessage['tone'];
}

/** The newest feedback message as a notice, or null when the server said nothing. */
export function speakerNotice(messages: readonly FeedbackMessage[]): SpeakerNotice | null {
  const last = messages[messages.length - 1];
  if (!last || last.text.length === 0) return null;
  return { id: `${last.tone}:${last.text}`, text: last.text, tone: last.tone };
}

/** Which notices the player has acknowledged. UI state only. */
export interface NoticeState {
  readonly acknowledged: readonly string[];
}

/** Nobody has acknowledged a notice yet. */
export const NO_NOTICES: NoticeState = Object.freeze({ acknowledged: [] });

/** The OK of a speaker box records the notice's id; it does not alter a world. */
export function acknowledgeNotice(state: NoticeState, id: string): NoticeState {
  if (state.acknowledged.includes(id)) return state;
  return { acknowledged: [...state.acknowledged, id] };
}

/** Whether a notice still needs acknowledging. */
export function noticeVisible(
  notice: SpeakerNotice | null,
  state: NoticeState,
): boolean {
  return notice !== null && !state.acknowledged.includes(notice.id);
}

/** A collect or hurry-up affordance: a label and whether its request can be sent. */
export interface ChromeActionView {
  readonly kind: 'collect' | 'hurry';
  readonly label: string;
  readonly note: string;
  readonly enabled: boolean;
}

/**
 * The selected building's chrome actions.
 *
 * Collect is available only when the server's cycle is due; hurry only when
 * the server and the content say a build is still in progress. They describe
 * requests — the host sends `collect`/`finish_building` and the server still
 * decides what, if anything, is paid or finished.
 */
export function chromeActions(
  building: BuildingInfoView | null,
  production: ProductionPanelView | null,
): readonly ChromeActionView[] {
  return [
    {
      kind: 'collect',
      label: 'Collect',
      note: production ? (production.due ? 'Ready' : 'Still accruing') : 'No production',
      enabled: production?.due === true,
    },
    {
      kind: 'hurry',
      label: 'Hurry up',
      note: building?.finish
        ? `${building.finish.remainingSeconds}s · ${building.finish.clicksToBuild} clicks`
        : 'Nothing building',
      enabled: building?.finish !== null && building?.finish !== undefined,
    },
  ];
}

/** A world-space attachable, anchored to a tile the server actually owns. */
export interface ChromeAttachment {
  readonly isoId: number;
  readonly itemId: number;
  readonly name: string;
  readonly tx: number;
  readonly ty: number;
}

/** Read the selected map item's tile from the server's answer, if it is one. */
export function chromeAttachment(
  bundle: ContentBundle,
  world: WorldSnapshot,
  isoId: number | null,
): ChromeAttachment | null {
  const tuple = selectedItem(world, isoId);
  if (!tuple || isoId === null) return null;
  const itemId = Number(tuple[0]);
  const tx = Number(tuple[1]);
  const ty = Number(tuple[2]);
  if (![itemId, tx, ty].every((value) => Number.isFinite(value))) return null;
  const name = bundle.items.find((entry) => entry.id === itemId)?.name ?? '';
  return { isoId, itemId, name, tx, ty };
}

/** The attach/dettach lifecycle the original's attachables all share. */
export interface AttachmentState {
  readonly attached: ChromeAttachment | null;
}

/** Nothing is attached. */
export const NO_ATTACHMENT: AttachmentState = Object.freeze({ attached: null });

/** Attach to one world element, replacing any previous target. */
export function attachTo(state: AttachmentState, target: ChromeAttachment): AttachmentState {
  void state;
  return { attached: target };
}

/** Dettach, leaving no world-space marker behind. */
export function dettach(state: AttachmentState): AttachmentState {
  void state;
  return NO_ATTACHMENT;
}

/** Whether the marker is on this particular server element. */
export function isAttachedTo(
  state: AttachmentState,
  target: ChromeAttachment | null,
): boolean {
  return (
    state.attached !== null &&
    target !== null &&
    state.attached.isoId === target.isoId &&
    state.attached.tx === target.tx &&
    state.attached.ty === target.ty
  );
}

/** Where an attachment sits on screen, through the client's own projection. */
export function attachmentPixel(
  target: ChromeAttachment,
  camera: CameraState,
): { x: number; y: number } {
  return tileToPixel(target.tx, target.ty, viewportOf(camera));
}

/** One request for the chrome's single modal slot. */
export interface ChromePopupRequest {
  readonly id: string;
  readonly title: string;
  readonly message: string;
  /** Higher priority opens first; ties keep request order. */
  readonly priority: number;
}

/** The one open popup and the requests waiting behind it. */
export interface ChromePopupSlot {
  readonly open: ChromePopupRequest | null;
  readonly pending: readonly ChromePopupRequest[];
}

/** An empty slot: no popup, no queue. */
export const EMPTY_POPUP_SLOT: ChromePopupSlot = Object.freeze({
  open: null,
  pending: [],
});

/**
 * Ask for a popup.
 *
 * This is `PopupObject`'s priority order in the clone's **one** dialog slot:
 * a second popup never opens a second modal, it waits in `pending` until the
 * first is dismissed. The body is still hosted by `dialog.tsx`; there is no
 * second stack of DOM overlays.
 */
export function requestPopup(
  slot: ChromePopupSlot,
  request: ChromePopupRequest,
): ChromePopupSlot {
  if (!slot.open) return { open: request, pending: slot.pending };
  const pending = [...slot.pending, request].sort((a, b) => b.priority - a.priority);
  return { open: slot.open, pending };
}

/** Dismiss the open popup and promote the highest-priority waiter. */
export function dismissPopup(slot: ChromePopupSlot): ChromePopupSlot {
  if (!slot.open) return slot;
  const [next, ...rest] = slot.pending;
  return { open: next ?? null, pending: rest };
}

/** The one dialog's descriptor for a chrome popup. */
export function chromePopupDialog(request: ChromePopupRequest): DialogContent {
  return { id: request.id, kind: 'alert', title: request.title };
}

/* -------------------------------------------------------------------------
 * Character setup, late-era recovery and the attack-symbol tooltip
 *
 * Three survivors of the late-era UI that have real content behind them. The
 * gender-choice popups are deliberately NOT here: the new server has neither
 * a `hasSex` save field (see `PrivateState` and `PlayerInfo` in
 * `@swl/protocol`) nor a `set_sex_player` command — that is an upstream PHP
 * endpoint, not one of the 94 catalogue commands — so a choice panel would
 * invent a client-only character rule.
 *
 * The hospital panel below reads the server's `deadHeroes` and the content's
 * unit names and syringe costs. Its only gesture is the catalogue's existing
 * `resurrect_hero` request; a refusal or an acceptance is drawn from the
 * server's answer through the one feedback channel, never decided locally.
 *
 * The attack-symbol legend is built from the client's own `RecuadroInfo`
 * literals and the rules' own ten damage classes. Neither panel claims the
 * proprietary art, and neither keeps an outcome of its own.
 * ---------------------------------------------------------------------- */

/** The client's own literals on `popups/PopupHospital.as`. */
export const HOSPITAL_TITLE = 'Hospital';
export const HOSPITAL_DESCRIPTION =
  'This building allows you to recover units lost in battle';
export const HOSPITAL_HELP =
  "If you lose units during a combat, you can resurrect them at the Graveyard!\\n\\n A portrait of your dead units and their number is displayed.\\n Resurrecting dead units costs half of their original price.\\n Click on the right button below the portrait of the unit to resurrect it using gold, food or cash.\\n You can also resurrect units with syringes.\\n Ask your friends to send you syringes using the \\'Ask For\\' button at the lower right!";
export const HOSPITAL_SYRINGES = 'Syringes';
export const HOSPITAL_AVAILABLE = 'Available';
export const HOSPITAL_RESURRECT_FOR = 'Resurrect for';
export const HOSPITAL_RESURRECT = 'Resurrect';
export const HOSPITAL_MAX_UNITS = 'Max units reached';
export const HOSPITAL_ASK = 'Ask for more';
export const HOSPITAL_HELP_BUTTON = 'HELP!';

/**
 * `INVENTORY_ITEM_SYRINGE` from the original's `Constants.as` (35). The
 * server keeps the count in the town's store under that item id; the client
 * only reads it for display.
 */
export const SYRINGE_ITEM_ID = 35;

/** A non-negative integer from a content field, or null when it is not one. */
function contentCount(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isInteger(value) && value >= 0 ? value : null;
  }
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
    return Number(value.trim());
  }
  return null;
}

/** One dead unit the server's save accounts for, named by the content. */
export interface DeadUnitView {
  /** The content id the server's `deadHeroes` key names. */
  readonly itemId: number;
  /** The content's name for that id. */
  readonly name: string;
  /** How many the server says are waiting; never a client counter. */
  readonly count: number;
  /** The content's syringe cost for one resurrection, display only. */
  readonly syringes: number;
  /** The catalogue's `resurrect_hero` request for the resource-cost gesture. */
  readonly resurrect: NativeCommand;
  /** The same request with a syringe, or null when no cost is named. */
  readonly resurrectWithSyringe: NativeCommand | null;
}

/** The hospital panel's body. */
export interface HospitalPanelView {
  /** Only the rows the server's `deadHeroes` names. */
  readonly dead: readonly DeadUnitView[];
  /** The server's own syringe count from the store. */
  readonly syringesAvailable: number;
  /** The client's own literals. */
  readonly title: string;
  readonly description: string;
  readonly help: string;
  readonly syringesLabel: string;
  readonly availableLabel: string;
  readonly resurrectForLabel: string;
  readonly resurrectLabel: string;
  readonly maxUnitsLabel: string;
  readonly askLabel: string;
  readonly helpButtonLabel: string;
}

/**
 * Read the hospital's body from the server's save and the content.
 *
 * `deadHeroes` is one of the server's own privateState keys (a documented
 * `Record<string, number>`), and the store's syringe count is its too. The
 * names and costs are the content's. A click builds the existing
 * `resurrect_hero` command with a fresh, deterministic iso id and neutral
 * coordinates — proposals the server validates — so no unit is revived here
 * and no resource is spent locally. Malformed rows are skipped rather than
 * shown as units the server does not own.
 */
export function hospitalPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
): HospitalPanelView {
  const names = new Map<number, string>();
  const syringeCosts = new Map<number, number>();
  for (const item of bundle.items ?? []) {
    names.set(item.id, item.name);
    syringeCosts.set(item.id, contentCount(item.extra?.['syringes']) ?? 0);
  }

  let nextIsoId = 1;
  for (const key of Object.keys(world.maps[0]?.items ?? {})) {
    const id = Number(key);
    if (Number.isInteger(id) && id >= nextIsoId) nextIsoId = id + 1;
  }

  const dead: DeadUnitView[] = [];
  const raw = recordOrNull(world.privateState?.['deadHeroes']);
  if (raw) {
    for (const [key, value] of Object.entries(raw)) {
      const itemId = contentId(key);
      const count = finite(value);
      // A key the content cannot name has no honest name or syringe cost to
      // draw, so it is skipped rather than shown as a fabricated unit.
      if (itemId === null || count === null || count < 1 || !names.has(itemId)) continue;
      const isoId = nextIsoId++;
      const args = (usedSyringe: number): unknown[] => [isoId, itemId, 0, 0, usedSyringe];
      const syringes = syringeCosts.get(itemId) ?? 0;
      dead.push({
        itemId,
        name: names.get(itemId)!,
        count: Math.trunc(count),
        syringes,
        resurrect: { map: 0, name: 'resurrect_hero', args: args(0) },
        resurrectWithSyringe:
          syringes > 0
            ? { map: 0, name: 'resurrect_hero', args: args(1) }
            : null,
      });
    }
  }

  const store = recordOrNull(world.maps[0]?.store);
  const stored = store ? finite(store[String(SYRINGE_ITEM_ID)]) : null;

  return {
    dead,
    syringesAvailable: stored === null ? 0 : Math.max(0, Math.trunc(stored)),
    title: HOSPITAL_TITLE,
    description: HOSPITAL_DESCRIPTION,
    help: HOSPITAL_HELP,
    syringesLabel: HOSPITAL_SYRINGES,
    availableLabel: HOSPITAL_AVAILABLE,
    resurrectForLabel: HOSPITAL_RESURRECT_FOR,
    resurrectLabel: HOSPITAL_RESURRECT,
    maxUnitsLabel: HOSPITAL_MAX_UNITS,
    askLabel: HOSPITAL_ASK,
    helpButtonLabel: HOSPITAL_HELP_BUTTON,
  };
}

/** The client's own literals on `GUI/RecuadroInfo.as` for the attack stats. */
export const ATTACK_SYMBOL_DAMAGE = 'How hard the unit attacks with each hit';
export const ATTACK_SYMBOL_SPEED = 'How fast the unit attacks';
export const ATTACK_SYMBOL_RANGE = 'How far can the unit attack';
export const ATTACK_SYMBOL_VELOCITY = 'How fast the unit is';

/** One attack symbol: the client's own field name and its own sentence. */
export interface AttackSymbolView {
  /** The client's own field name, from `GUI/UnitTooltip.as`. */
  readonly symbol: string;
  /** The client's own explanatory literal. */
  readonly label: string;
}

/** The attack-symbol tooltip's body. */
export interface AttackSymbolsPanelView {
  /** The stat symbols and their client-owned sentences. */
  readonly stats: readonly AttackSymbolView[];
  /** The rules' own ten damage classes, verbatim. */
  readonly damageClasses: readonly string[];
  /** A neutral panel heading; no game copy is invented for the body. */
  readonly heading: string;
}

/**
 * Build the attack-symbol legend from the client's literals and the rules'
 * damage classes.
 *
 * There is no server state to read and no outcome to decide: this is the
 * vocabulary the rules already define and the sentences the client already
 * says. The original's symbol artwork is excluded; only the legend is drawn.
 */
export function attackSymbolsPanel(): AttackSymbolsPanelView {
  return {
    stats: [
      { symbol: 'uiAttack', label: ATTACK_SYMBOL_DAMAGE },
      { symbol: 'attack_interval', label: ATTACK_SYMBOL_SPEED },
      { symbol: 'attack_range', label: ATTACK_SYMBOL_RANGE },
      { symbol: 'velocity', label: ATTACK_SYMBOL_VELOCITY },
    ],
    damageClasses: [...DAMAGE_CLASSES],
    heading: 'Attack symbols',
  };
}

/** The two panels hosted by the one shared dialog. */
export type CharacterSetupPanelKind = 'hospital' | 'attack-symbols';

/** The one dialog's descriptor for a character-setup-family panel. */
export function characterSetupDialog(kind: CharacterSetupPanelKind): DialogContent {
  const titles: Record<CharacterSetupPanelKind, string> = {
    hospital: HOSPITAL_TITLE,
    'attack-symbols': 'Attack symbols',
  };
  return { id: `charactersetup-${kind}`, kind: 'alert', title: titles[kind] };
}

/* -------------------------------------------------------------------------
 * The inventory cell and the info popup
 *
 * These are the last two GUI panels whose behaviour is presentation only.
 * The inventory grid arranges the **server's** stored items into cells and
 * lets one cell be dragged onto another slot: that is `setPos` from
 * `GUI/InventoryItem.as` as UI state. It never places an item — the Place
 * gesture is unchanged and still sends `place_stored_item` through the one
 * transport, with the tile chosen on the map.
 *
 * The info popup is `GUI/InfoPopup.as`: the HUD's own `Popover` shown for a
 * client-side display lifetime, with a `reposition` that keeps the box inside
 * the viewport. It invents no readout and owns no game rule: the first and
 * warning lines are the HUD model's, verbatim.
 * ---------------------------------------------------------------------- */

/** The inventory grid's column count. UI-only layout, not a server rule. */
export const INVENTORY_GRID_COLUMNS = 2;

/** The cell order of the inventory grid. UI state, never saved to the server. */
export interface InventoryGridState {
  readonly columns: number;
  /** Content item ids, in the order their cells are drawn. */
  readonly order: readonly number[];
}

/** One stored item drawn in a grid cell, with its UI-only column and row. */
export interface InventoryCellView extends StoredItemView {
  /** The cell's linear index in the grid. */
  readonly index: number;
  readonly col: number;
  readonly row: number;
}

/**
 * Seed a grid from the server's stored items, in the order `storedItems`
 * already gives them. Unknown or duplicate ids are skipped: a cell must name
 * exactly one server-owned item.
 */
export function inventoryGrid(
  items: readonly StoredItemView[],
  columns = INVENTORY_GRID_COLUMNS,
): InventoryGridState {
  const count =
    Number.isInteger(columns) && columns > 0 ? columns : INVENTORY_GRID_COLUMNS;
  const seen = new Set<number>();
  const order: number[] = [];
  for (const entry of items) {
    if (!Number.isInteger(entry.itemId) || seen.has(entry.itemId)) continue;
    seen.add(entry.itemId);
    order.push(entry.itemId);
  }
  return { columns: count, order };
}

/**
 * Keep a layout across a new server answer: cells that still name a stored
 * item keep their relative order, vanished items drop out, and new items
 * append. The store's content is the server's; only the arrangement is ours.
 */
export function reconcileInventoryGrid(
  grid: InventoryGridState,
  items: readonly StoredItemView[],
): InventoryGridState {
  const fresh = inventoryGrid(items, grid.columns);
  const present = new Set(fresh.order);
  const kept = grid.order.filter((id) => present.has(id));
  const added = fresh.order.filter((id) => !kept.includes(id));
  return { columns: grid.columns, order: [...kept, ...added] };
}

/** Pair the stored items with their grid cells. */
export function inventoryCells(
  items: readonly StoredItemView[],
  grid: InventoryGridState,
): InventoryCellView[] {
  const byId = new Map<number, StoredItemView>();
  for (const entry of items) byId.set(entry.itemId, entry);
  const cells: InventoryCellView[] = [];
  grid.order.forEach((itemId, index) => {
    const entry = byId.get(itemId);
    if (!entry) return;
    cells.push({
      ...entry,
      index,
      col: index % grid.columns,
      row: Math.floor(index / grid.columns),
    });
  });
  return cells;
}

/** Where one item's cell currently sits, or null when it is not in the grid. */
export function inventoryCellAt(
  grid: InventoryGridState,
  itemId: number,
): { index: number; col: number; row: number } | null {
  const index = grid.order.indexOf(itemId);
  if (index < 0) return null;
  return {
    index,
    col: index % grid.columns,
    row: Math.floor(index / grid.columns),
  };
}

/**
 * The cell's `setPos`: move one item to a column and row, swapping with the
 * cell already there. The target is clamped to the grid the server's item
 * count actually fills; a malformed position or an unknown id is a no-op.
 * Nothing here places an item or changes a quantity.
 */
export function setInventoryCellPos(
  grid: InventoryGridState,
  itemId: number,
  col: number,
  row: number,
): InventoryGridState {
  const from = inventoryCellAt(grid, itemId);
  if (!from || grid.order.length === 0) return grid;
  const rows = Math.max(1, Math.ceil(grid.order.length / grid.columns));
  const wantedCol = Number.isFinite(col) ? Math.trunc(col) : from.col;
  const wantedRow = Number.isFinite(row) ? Math.trunc(row) : from.row;
  const targetCol = Math.min(grid.columns - 1, Math.max(0, wantedCol));
  const targetRow = Math.min(rows - 1, Math.max(0, wantedRow));
  const to = Math.min(
    grid.order.length - 1,
    targetRow * grid.columns + targetCol,
  );
  if (to === from.index) return grid;
  const order = [...grid.order];
  const moved = order[from.index]!;
  // A drop onto an occupied slot gives that cell the dragged cell's old
  // position: one `setPos` exchanges the two, it does not shift the row.
  order[from.index] = order[to]!;
  order[to] = moved;
  return { ...grid, order };
}

/**
 * The info popup's display lifetime in seconds. A presentation duration for
 * the tooltip, not a rule: it never gates a request or a resource.
 */
export const INFO_POPUP_LIFETIME_SECONDS = 6;

/** The readout the popup explains, with the anchor point it was opened at. */
export interface InfoPopupAnchor {
  /** Which HUD readout owns this popup; a stable UI id, not a game id. */
  readonly id: string;
  /** Viewport x of the readout's centre. */
  readonly x: number;
  /** Viewport y of the readout's bottom edge. */
  readonly y: number;
}

/** The info popup's UI state: its anchor and the time it has left. */
export interface InfoPopupState {
  readonly anchor: InfoPopupAnchor | null;
  readonly secondsRemaining: number;
}

/** Nothing open. */
export const CLOSED_INFO_POPUP: InfoPopupState = Object.freeze({
  anchor: null,
  secondsRemaining: 0,
});

/** Open a popup for one HUD readout with its full display lifetime. */
export function openInfoPopup(
  anchor: InfoPopupAnchor,
  seconds = INFO_POPUP_LIFETIME_SECONDS,
): InfoPopupState {
  if (
    typeof anchor.id !== 'string' ||
    anchor.id.length === 0 ||
    !Number.isFinite(anchor.x) ||
    !Number.isFinite(anchor.y)
  ) {
    return CLOSED_INFO_POPUP;
  }
  return { anchor, secondsRemaining: Math.max(0, seconds) };
}

/**
 * The popup's `update`/timer: advance by the elapsed seconds and close when
 * the lifetime is spent. A closed popup stays closed.
 */
export function tickInfoPopup(
  state: InfoPopupState,
  elapsedSeconds: number,
): InfoPopupState {
  if (!state.anchor) return state;
  const elapsed = Number.isFinite(elapsedSeconds)
    ? Math.max(0, elapsedSeconds)
    : 0;
  const remaining = Math.max(0, state.secondsRemaining - elapsed);
  return remaining <= 0 ? CLOSED_INFO_POPUP : { ...state, secondsRemaining: remaining };
}

/** The viewport the popup must stay inside, and the box's measured size. */
export interface InfoPopupBounds {
  readonly width: number;
  readonly height: number;
  readonly popupWidth: number;
  readonly popupHeight: number;
}

/**
 * The popup's `reposition`: centre it on its anchor, keep it inside the
 * viewport, and flip it above the readout when it would overflow below.
 * Pure geometry over the anchor and the measured box; no readout is changed.
 */
export function repositionInfoPopup(
  anchor: InfoPopupAnchor,
  bounds: InfoPopupBounds,
): { x: number; y: number } {
  const gap = 8;
  const width = Math.max(1, bounds.popupWidth);
  const height = Math.max(1, bounds.popupHeight);
  const x = Math.min(
    Math.max(0, bounds.width - width - gap),
    Math.max(gap, anchor.x - width / 2),
  );
  const below = anchor.y + gap;
  const y =
    below + height + gap <= bounds.height
      ? below
      : Math.max(gap, anchor.y - height - gap);
  return { x: Math.round(x), y: Math.round(y) };
}

/* -------------------------------------------------------------------------
 * The mystery boxes
 *
 * `popups/PopupMistery.as` is the display for pack 4, the random pack: its
 * four content candidates are labelled Rare / Uncommon / Common / Common in
 * the original. `popups/PopupSuperMistery.as` is the display for a super pack:
 * the content's three rarity rows and its three priced tiers (see
 * `re/docs/03-commands-quests-economy.md`, §2.15). Both screens only **ask**
 * the server to buy a pack: `packages/rules/src/offerpacks.ts` decides the
 * shape, tier and price, and `buyOfferPackCommand` rolls the reward from a
 * server seed and grants it into the store.
 *
 * This bridge reads the content to show what *could* be won and reads the
 * store in the server's answer to show what *was* won. It never rolls,
 * prices or grants anything itself, and the original's box art stays out.
 * ---------------------------------------------------------------------- */

/** The client's own literals on the two box popups. */
export const MYSTERY_TITLE = 'Mistery Box Pack';
export const MYSTERY_PROMPT = 'You can get one of the following!\nTest your luck!';
export const SUPER_TITLE = 'Super Mistery Box Pack';
export const SUPER_VALUE = 'BEST\nVALUE & RARE UNIT GUARANTEED';
export const SUPER_ONLY_THIS_WEEK = 'ONLY\nTHIS WEEK';
export const SUPER_STORAGE = 'You will find your prizes in your storage!';
export const MYSTERY_CONGRATULATIONS = 'CONGRATULATIONS!, You won:';
export const RARITY_RARE = 'Rare';
export const RARITY_UNCOMMON = 'Uncommon';
export const RARITY_COMMON = 'Common';
export const MYSTERY_BUY = 'Buy';
export const MYSTERY_OK = 'OK';

/** Which of the two box popups a pack belongs to. */
export type MysteryKind = 'mystery' | 'super';

/** A possible prize, named by the content. Never a granted reward. */
export interface MysteryItemView {
  readonly itemId: number;
  readonly name: string;
}

/** One rarity row the popup draws. */
export interface MysteryRarityRow {
  readonly label: string;
  readonly items: readonly MysteryItemView[];
}

/** One purchase gesture: the content's price and the request a click sends. */
export interface MysteryTierView {
  /** Selected-item count; the super tier the server reads from the request. */
  readonly count: number;
  /** The price from the content's own table, shown and never charged here. */
  readonly price: number;
  /** Presentation only: whether the server's wallet covers the price. */
  readonly affordable: boolean;
  /** The request; the server decides whether it applies. */
  readonly command: NativeCommand;
}

/** The preview a box popup draws, from the content and the client's literals. */
export interface MysteryBoxView {
  readonly kind: MysteryKind;
  readonly packId: number;
  readonly title: string;
  readonly prompt: string;
  readonly rows: readonly MysteryRarityRow[];
  readonly tiers: readonly MysteryTierView[];
  readonly banner: string | null;
  readonly weekNote: string | null;
  readonly buy: string;
}

/** A launcher for one of the two box popups, from the content's own packs. */
export interface MysteryLauncherView {
  readonly kind: MysteryKind;
  readonly packId: number;
  readonly name: string;
  readonly title: string;
  /** Whether the content currently offers this pack; never a client gate. */
  readonly available: boolean;
}

/** The purchase a click asks for, kept beside the store it may change. */
export interface MysteryPurchase {
  readonly kind: MysteryKind;
  readonly packId: number;
  readonly title: string;
  /** The tier price the content published; display only. */
  readonly price: number | null;
  readonly command: NativeCommand;
}

/** One item the server actually granted, with the store's quantity delta. */
export interface MysteryWonItemView extends MysteryItemView {
  readonly quantity: number;
}

/** The server's answer, read out of the store it granted into. */
export interface MysteryResultView {
  readonly kind: MysteryKind;
  readonly title: string;
  readonly heading: string | null;
  readonly message: string | null;
  readonly ok: string;
  readonly price: number | null;
  readonly items: readonly MysteryWonItemView[];
}

/** A content row, read as an offer pack only when it has the right shape. */
function asOfferPack(value: unknown): OfferPackData | null {
  const row = recordOrNull(value);
  if (!row) return null;
  const id = finite(row['id']);
  const name = row['name'];
  const cash = finite(row['cost_cash']);
  if (
    id === null || !Number.isInteger(id) || id <= 0 ||
    typeof name !== 'string' || name.length === 0 ||
    cash === null || cash < 0
  ) return null;
  return {
    id,
    name,
    type: typeof row['type'] === 'string' ? row['type'] : '',
    enabled: typeof row['enabled'] === 'number' ? row['enabled'] : undefined,
    position: typeof row['position'] === 'number' ? row['position'] : undefined,
    cost_cash: cash,
    gold: Number(row['gold']) || 0,
    wood: Number(row['wood']) || 0,
    oil: Number(row['oil']) || 0,
    steel: Number(row['steel']) || 0,
    mana: Number(row['mana']) || 0,
    xp: Number(row['xp']) || 0,
    items: Array.isArray(row['items']) ? (row['items'] as OfferPackData['items']) : null,
  };
}

/** A positive integer content id, or null for a malformed row. */
function packItemId(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;
}

/** The content's item names, used only to label ids the server answered. */
function mysteryNames(bundle: ContentBundle): Map<number, string> {
  const out = new Map<number, string>();
  for (const item of bundle.items ?? []) out.set(item.id, item.name);
  return out;
}

/** The one dialog descriptor for a box popup; there is no second modal. */
export function mysteryDialog(kind: MysteryKind, title: string): DialogContent {
  return { id: `mystery-${kind}`, kind: 'confirm', title };
}

/**
 * The two box popups the content can open.
 *
 * The original opens the mystery popup from pack 4, its only random pack, and
 * the super popup from a super pack. Both ids and names come from the content;
 * the titles are the popups' own literals. A hidden historical pack is still
 * listed so its screen can be seen, but a visible one is preferred as the
 * super launcher.
 */
export function mysteryBoxes(bundle: ContentBundle): readonly MysteryLauncherView[] {
  let mystery: MysteryLauncherView | null = null;
  let superBox: MysteryLauncherView | null = null;
  for (const raw of bundle.offerPacks ?? []) {
    const pack = asOfferPack(raw);
    if (!pack) continue;
    const shape = offerPackShape(pack);
    if (shape === 'random' && mystery === null) {
      mystery = {
        kind: 'mystery',
        packId: pack.id,
        name: pack.name,
        title: MYSTERY_TITLE,
        available: isOfferPackAvailable(pack),
      };
    } else if (shape === 'super') {
      const view: MysteryLauncherView = {
        kind: 'super',
        packId: pack.id,
        name: pack.name,
        title: SUPER_TITLE,
        available: isOfferPackAvailable(pack),
      };
      if (superBox === null || (!superBox.available && view.available)) superBox = view;
    }
  }
  return [mystery, superBox].filter((entry): entry is MysteryLauncherView => entry !== null);
}

/**
 * The preview a box popup draws, or null when the content has no such pack.
 *
 * The rows are the pack's own candidates, the prices are the rules' own
 * prices, and each button is only a request. A pack the content currently
 * hides still gets its preview, but no buy button: the server would refuse
 * the purchase, so the client must not offer one.
 */
export function mysteryBoxPanel(
  bundle: ContentBundle,
  packId: number,
  cash: number,
): MysteryBoxView | null {
  const pack = (bundle.offerPacks ?? [])
    .map(asOfferPack)
    .find((entry) => entry?.id === packId) ?? null;
  if (!pack) return null;
  const shape = offerPackShape(pack);
  if (shape !== 'random' && shape !== 'super') return null;
  const candidates = offerPackCandidates(pack);
  if (candidates === null || candidates.length === 0) return null;
  const names = mysteryNames(bundle);
  const item = (id: number): MysteryItemView => ({
    itemId: id,
    name: names.get(id) ?? `item ${id}`,
  });
  const available = isOfferPackAvailable(pack);

  if (shape === 'random') {
    const pairs = pack.items;
    if (!Array.isArray(pairs)) return null;
    const rows: MysteryRarityRow[] = [];
    for (const [index, pair] of pairs.entries()) {
      if (!Array.isArray(pair)) return null;
      const id = packItemId(pair[0]);
      if (id === null) return null;
      const label =
        index === 0 ? RARITY_RARE : index === 1 ? RARITY_UNCOMMON : RARITY_COMMON;
      rows.push({ label, items: [item(id)] });
    }
    const price = offerPackPrice(pack, null);
    const tiers: MysteryTierView[] =
      available && price !== null
        ? [
            {
              count: candidates.length,
              price,
              affordable: cash >= price,
              command: buyOfferPack(pack.id, candidates),
            },
          ]
        : [];
    return {
      kind: 'mystery',
      packId: pack.id,
      title: MYSTERY_TITLE,
      prompt: MYSTERY_PROMPT,
      rows,
      tiers,
      banner: null,
      weekNote: null,
      buy: MYSTERY_BUY,
    };
  }

  const items = pack.items;
  if (!Array.isArray(items) || items.length !== 3) return null;
  const labels = [RARITY_RARE, RARITY_UNCOMMON, RARITY_COMMON];
  const rows: MysteryRarityRow[] = [];
  for (const [index, row] of items.entries()) {
    if (!Array.isArray(row)) return null;
    const ids = row.map(packItemId);
    if (ids.some((id) => id === null)) return null;
    rows.push({
      label: labels[index]!,
      items: ids.map((id) => item(id!)),
    });
  }
  const tiers: MysteryTierView[] = [];
  if (available) {
    for (const count of [1, 2, 4]) {
      const tier = offerPackTierForCount(pack, count);
      const price = tier === null ? null : offerPackPrice(pack, tier);
      if (tier === null || price === null || candidates.length < count) continue;
      tiers.push({
        count,
        price,
        affordable: cash >= price,
        command: buyOfferPack(pack.id, candidates.slice(0, count)),
      });
    }
  }
  return {
    kind: 'super',
    packId: pack.id,
    title: SUPER_TITLE,
    prompt: SUPER_STORAGE,
    rows,
    tiers,
    banner: SUPER_VALUE,
    weekNote: SUPER_ONLY_THIS_WEEK,
    buy: MYSTERY_BUY,
  };
}

/** The store's quantities before a request, read from the server's world. */
export function storeQuantities(world: WorldSnapshot): Readonly<Record<string, number>> {
  const store = world.maps[0]?.store;
  const out: Record<string, number> = {};
  if (!store || typeof store !== 'object' || Array.isArray(store)) return out;
  for (const [key, value] of Object.entries(store)) {
    const itemId = contentId(key);
    const quantity = finite(value);
    if (itemId !== null && quantity !== null) out[String(itemId)] = quantity;
  }
  return out;
}

/**
 * The pack result the server answered, read as the growth of its store.
 *
 * `before` is the store in the world the buy request was sent with; the
 * quantities here are the ones in the world the server returned. Items whose
 * quantity did not grow are never claimed, so a refusal or a replay draws no
 * result. The price is the content tier the player chose, shown beside the
 * ids the server actually granted — never a locally rolled prize.
 */
export function mysteryResultPanel(
  bundle: ContentBundle,
  world: WorldSnapshot,
  before: Readonly<Record<string, number>>,
  purchase: MysteryPurchase,
): MysteryResultView | null {
  const after = storeQuantities(world);
  const names = mysteryNames(bundle);
  const items: MysteryWonItemView[] = [];
  for (const [key, quantity] of Object.entries(after)) {
    const itemId = contentId(key);
    if (itemId === null) continue;
    const gained = quantity - (finite(before[key]) ?? 0);
    if (!Number.isFinite(gained) || gained <= 0) continue;
    items.push({
      itemId,
      name: names.get(itemId) ?? `item ${itemId}`,
      quantity: Math.trunc(gained),
    });
  }
  if (items.length === 0) return null;
  const superBox = purchase.kind === 'super';
  return {
    kind: purchase.kind,
    title: purchase.title,
    heading: superBox ? MYSTERY_CONGRATULATIONS : null,
    message: superBox ? SUPER_STORAGE : null,
    ok: MYSTERY_OK,
    price: purchase.price,
    items,
  };
}

/* -------------------------------------------------------------------------
 * The soul-mixer help and turbine (presentation only)
 *
 * `popups/PopupSoulMixerHelp.as` exists to write one literal into a textfield:
 * the four numbered steps below are the decompiled copy, kept verbatim (down
 * to the stray newline before the final full stop). They are help text only —
 * the POWERUP and SPEEDUP they mention are *not* offered as working gestures:
 * buy_powerups and soulmixer_speedup have no applier case in the server, the
 * output-item derivation rule was never recovered, and soulmixer_speedup is
 * unpriced. Drawing the copy does not claim to draw the fusion.
 *
 * `popups/SoulMixer/SoulMixerTurbina.as` only has a `setState` method: its
 * timer is the server's. The bridge below reads a server-owned state if one is
 * present and otherwise reports its absence. It never computes a countdown
 * from a timestamp or a guessed training time, so the panel can never show a
 * number the server did not publish.
 * ---------------------------------------------------------------------- */

/** The four help steps, verbatim from `popups/PopupSoulMixerHelp.as`. */
export const SOUL_MIXER_HELP =
  '1. Fuse two soldiers and create a new powerful unit.\n' +
  '2. Give a BOOST to the new unit with the POWERUP button.\n' +
  '3. Start the FUSION and press the SPEEDUP button to get your unit immediately.\n' +
  '4. Take out your three soldiers and continue exploring the unique combinations\n' +
  '.';

/** The turbine's own label on the fusion screen, used as the timer heading. */
export const SOUL_MIXER_TURBINA_LABEL = 'Remaining time:';

/** Shown when the server has published no turbine state. Never a countdown. */
export const SOUL_MIXER_TURBINA_PLACEHOLDER =
  'No active fusion timer is reported by the server.';

/**
 * The server key a turbine state would be read from.
 *
 * No current server writes this key — there is no applier case for the
 * soul-mixer commands — so a fresh, unmodified world always reads as absent.
 * The selector is deliberately narrow: it consumes only values the server
 * wrote, and treats a missing or malformed record as absent.
 */
const SOUL_MIXER_STATE_KEY = 'soulMixer';

/** What the turbine can honestly say about the server's state. */
export interface SoulMixerTurbinaView {
  /** True only when the server actually published a well-formed record. */
  readonly available: boolean;
  /** The server's own state label, or null when it did not publish one. */
  readonly state: string | null;
  /** The server's own remaining seconds, verbatim; never computed here. */
  readonly remainingSeconds: number | null;
}

/**
 * Read the turbine's state from the server's world, or report its absence.
 *
 * This is a selector, not a rule: it copies two fields the server may have
 * written and invents neither a state nor a number. In particular it never
 * turns a start timestamp plus a training time into a remaining time — that
 * would need the fusion's output rule, which was never recovered.
 */
export function soulMixerTurbina(world: WorldSnapshot): SoulMixerTurbinaView {
  const raw = world.privateState[SOUL_MIXER_STATE_KEY];
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    return { available: false, state: null, remainingSeconds: null };
  }
  const record = raw as Record<string, unknown>;
  const state = typeof record['state'] === 'string' && record['state'] !== ''
    ? record['state']
    : null;
  const remaining = finite(record['remainingSeconds']);
  if (state === null && remaining === null) {
    return { available: false, state: null, remainingSeconds: null };
  }
  return {
    available: true,
    state,
    remainingSeconds: remaining === null ? null : Math.max(0, remaining),
  };
}

/** Format a server-published remaining time as mm:ss for display only. */
export function formatTurbinaRemaining(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  return `${String(minutes).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
}

/** The one dialog descriptor for the help/turbine panel. */
export function soulMixerDialog(): DialogContent {
  return { id: 'soulmixer-help', kind: 'alert', title: 'Soul Mixer Help' };
}
