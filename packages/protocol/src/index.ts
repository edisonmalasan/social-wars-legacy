export * from './commandphp.ts';
export * from './commands.ts';

/**
 * The wire protocol, as a set of types.
 *
 * Everything in this file is grounded in evidence, not inference:
 *
 *  - the resource vector order was confirmed live against a real client session
 *    (see re/docs/06-LIVE-SESSION-PROTOCOL.md);
 *  - the command vocabulary comes from the 94 `Cmd*.as` classes in the
 *    decompiled client (re/docs/03-commands-quests-economy.md);
 *  - the save document comes from the upstream schema, derived from 30+ real
 *    saves (re/docs/04-python-server-and-data.md).
 *
 * The native protocol of the new server is versioned and typed; the original
 * `command.php` dialect is spoken by the compatibility shim, not by this
 * package's runtime types.
 */

/**
 * The 8-slot resource delta carried by every command.
 *
 * ORDER IS LOAD-BEARING. The upstream client sends this vector and the
 * upstream server applies it verbatim, so a mis-ordered slot silently moves
 * gold into steel. The order below was verified live:
 *
 *   worker purchase   -> [0, 5, -10,  0, 0,  0, 0, 0]  => gold  -10
 *   Academy purchase  -> [0, 13,  0, -125, 0, 0, 0, 0]  => wood -125
 *   soldier training  -> [0,  3, -30,  0, 0, -60, 0, 0]  => gold -30, steel -60
 */
export const RESOURCE_ORDER = [
  'energy',
  'xp',
  'gold',
  'wood',
  'oil',
  'steel',
  'cash',
  'mana',
] as const;

export type ResourceName = (typeof RESOURCE_ORDER)[number];

export const RESOURCE_INDEX: Readonly<Record<ResourceName, number>> = Object.freeze(
  Object.fromEntries(RESOURCE_ORDER.map((name, i) => [name, i])) as Record<ResourceName, number>,
);

/** A resource delta, positionally aligned with {@link RESOURCE_ORDER}. */
export type ResourceVector = readonly [
  energy: number,
  xp: number,
  gold: number,
  wood: number,
  oil: number,
  steel: number,
  cash: number,
  mana: number,
];

export const ZERO_RESOURCES: ResourceVector = [0, 0, 0, 0, 0, 0, 0, 0];

export function readResource(vector: ResourceVector, name: ResourceName): number {
  return vector[RESOURCE_INDEX[name]!] ?? 0;
}

export function addResources(a: ResourceVector, b: ResourceVector): ResourceVector {
  return a.map((v, i) => v + (b[i] ?? 0)) as unknown as ResourceVector;
}

/**
 * The command names the client can send.
 *
 * The authority is the decompiled client's own command classes: every
 * `Cmd*.as`, `AdminCmd*.as` and `SystemCmd*.as` under
 * `.work/as/basesec/scripts/commands`. A class names itself in **two**
 * ways - `super("<name>")`, and `commandID = "<name>"` for a subclass
 * that overrides its parent's name - and a name may contain a **digit**:
 * `push_queue_unit2` is a real command.
 *
 * The report's catalogue in `re/docs/03-commands-quests-economy.md` agrees
 * with it **exactly**: 94 names on both sides, and the catalogue's rows
 * are numbered 1 to 94 with no gaps, so the two sources cross-validate
 * each other rather than merely agreeing in total.
 *
 * The upstream server handles 63 of the 94 and silently drops the other
 * 31. A new server must implement every name the client can send, because
 * the client assumes the ones it sends are honoured.
 *
 * Verified by `scripts/verify-command-catalogue.mjs`.
 */
export const COMMAND_NAMES = [
  'accept_collect_help',
  'activate',
  'activate_item_click',
  'add_click',
  'add_inventory_item',
  'add_xp_unit',
  'admin_set_quest_rank',
  'apply_rewards_ranking',
  'assist_neighbor',
  'assist_receive',
  'attack_player',
  'batch_remove',
  'buy',
  'buy_magic',
  'buy_mana_new',
  'buy_offer_pack',
  'buy_powerups',
  'buy_premium_account',
  'buy_resources',
  'buy_si_help',
  'buy_stored_item_cash',
  'clean_attacks',
  'clean_received_assists',
  'clear_message',
  'collect',
  'collect_mission',
  'complete_collection',
  'complete_goal',
  'complete_tutorial',
  'cross_promotion_finished',
  'darts_new_free',
  'darts_reset',
  'darts_shoot_balloon',
  'end_attack',
  'end_quest',
  'exchange_cash',
  'expand',
  'fast_forward',
  'finish_building',
  'finish_robotic_help',
  'finish_si',
  'flash_debug',
  'kill',
  'kill_iid',
  'level_up',
  'load_map',
  'modify_energy',
  'modify_position_universe',
  'move',
  'next_research_item',
  'next_research_step',
  'orient',
  'ping',
  'place_gift',
  'place_stored_item',
  'pop_queue_unit',
  'pop_unit',
  'premium_upgrade',
  'push_queue_unit',
  'push_queue_unit2',
  'push_unit',
  'remove_inventory_item',
  'research_buy_step_cash',
  'reset',
  'reset_collect',
  'reset_position_univers',
  'reset_research_item',
  'reset_world_change',
  'resurrect_hero',
  'rt_open_graph_unit',
  'save_map',
  'sell',
  'sell_gift',
  'sell_stored_item',
  'set_goals',
  'set_help_map',
  'set_quest_var',
  'set_resource_allies',
  'set_strategy',
  'set_variables',
  'soulmixer_speedup',
  'spy_player',
  'store_add_items',
  'store_item',
  'system_receive_mana',
  'system_receive_si_help',
  'system_reset_quest',
  'trade_resource',
  'unit_collections_completed',
  'upgrade',
  'use_magic',
  'weekly_reward',
  'win_alliance_daily_bonus',
  'win_daily_bonus',
] as const;



export type CommandName = (typeof COMMAND_NAMES)[number];

/** A single command inside a batch. */
export type CommandTuple = readonly [
  mapId: number,
  name: CommandName,
  args: readonly unknown[],
  resources: ResourceVector,
];

/**
 * The JSON body of the original `command.php` request.
 *
 * Field order is irrelevant (it is JSON), but the *set* of fields is exactly
 * what the client sends, and `first_number` is the **global index of the first
 * command in this batch**, not a batch counter. See
 * re/docs/06-LIVE-SESSION-PROTOCOL.md section 3.4.
 */
export interface CommandPayload {
  /** Unix seconds. */
  ts: number;
  /** Attempt counter, 1-based; the client retries up to 3. */
  tries: number;
  /** The client's version, e.g. "1.5.4". */
  flashVersion: string;
  /** Global command index of the first command in this batch. */
  first_number: number;
  /** The client's access token. The upstream server ignores it. */
  accessToken: string;
  /** "0" or "1" — a STRING, not a number. */
  publishActions: string;
  commands: CommandTuple[];
}

/**
 * The original `command.php` framing: `<64 hex chars>;<json>`.
 *
 * The hex is `HMAC-SHA256(Config.SERVER_KEY, json)` in lower case.
 *
 * The key ROTATED once, at client build 1.4.28. A compatibility shim must
 * accept both eras, because unmodified original clients exist for both.
 */
export const SERVER_KEYS = {
  /** Builds 1.4.5 - 1.4.27. */
  legacy: '3m0d3pwiupoetn7ysa02',
  /** Builds 1.4.28 - 1.5.4. Verified against a live capture. */
  current: '4vVSD8dftv6hdfb1Hnk9',
} as const;

export const DATA_SEPARATOR = ';';

/** One item placed on a map. */
export type MapItem = readonly [
  itemId: number,
  x: number,
  y: number,
  timestamp: number,
  orientation: number,
  store: readonly number[],
  attributes: Readonly<Record<string, unknown>>,
  playerId: number,
];

/** The per-item attribute keys the client uses. */
export const ITEM_ATTRIBUTE_KEYS = [
  'si', // socially-in-construction help
  'nc', // clicks still needed to build
  'cp', // activation point
  'nu', // queue length
  'ts', // queue timestamp
  'ui', // queued unit id
  'xp', // accumulated unit xp
] as const;

export type ItemAttributeKey = (typeof ITEM_ATTRIBUTE_KEYS)[number];

export interface PlayerInfo {
  pid: string | null;
  name: string;
  pic: string;
  cash: number;
  completed_tutorial: number;
  default_map: number;
  map_names: string[];
  map_sizes: number[];
  world_id: number | null;
  sp_ref_uid: number;
  sp_ref_cat_install: string;
  last_logged_in: number;
}

export interface GameMap {
  id: number;
  world_id: number;
  expansions: number[];
  timestamp: number;
  xp: number;
  level: number;
  gold: number;
  wood: number;
  oil: number;
  steel: number;
  race: string;
  skin: number;
  idCurrentTreasure: number;
  timestampLastTreasure: number;
  resourcesTraded: Record<string, unknown>;
  resourceAlliesMarket: string;
  receivedAssists: Record<string, unknown>;
  timestampLastTrade: number;
  numTradesDone: number;
  store: Record<string, number>;
  increasedPopulation: number;
  expirableUnitsTime: Record<string, unknown>;
  timestampLastChapter: number;
  questTimes: Record<string, number>;
  idCurrentMission: number;
  currentQuestVars: Record<string, unknown> | null;
  items: Record<string, MapItem>;
}

/** The 47 privateState keys the upstream server writes. */
export interface PrivateState {
  publishedOpenGraphUnit: string[];
  weeklyRewardIndex: number;
  neighborAssists: Record<string, unknown>;
  friendsHelpedCoveredItem: unknown;
  lastUpgrades: unknown[];
  timestampLastBonus: number;
  timeStampMondayBonus: number;
  timestampLastAllianceBonus: number;
  bestUnit: unknown;
  firstTimeAlliance: unknown;
  marketPlaceFirstTime: unknown;
  message: unknown;
  strategy: number;
  betWin: unknown[];
  attacksSent: unknown[];
  attacksReceived: unknown[];
  tsAttacksReset: number;
  tsSpyingsReset: number;
  attacksPack: number;
  spyings: unknown[];
  spyingsPack: number;
  deadHeroes: Record<string, number>;
  timeStampEndPremium: number;
  unlockedSkins: unknown;
  unlockedQuestIndex: number;
  questsRank: Record<string, number>;
  magics: Record<string, number>;
  timeStampDartsReset: number;
  dartsBalloonsShot: number[];
  dartsRandomSeed: number;
  dartsHasFree: boolean;
  dartsGotExtra: boolean;
  boughtUnits: number[];
  unitCollectionsCompleted: number[];
  mana: number;
  inventoryItems: Record<string, number>;
  collections: number[];
  energy: number;
  researchItemNumber: number[];
  researchStepNumber: number[];
  timeStampDoResearch: number[];
  crossPromotionsFinished: unknown[];
  helpMap: unknown[];
  worldChange: number;
  bonusNextId: number;
  goals: unknown[];
  [key: string]: unknown;
}

/** The whole save document: one player's state. */
export interface SaveDocument {
  version: string | null;
  playerInfo: PlayerInfo;
  maps: GameMap[];
  privateState: PrivateState;
}
