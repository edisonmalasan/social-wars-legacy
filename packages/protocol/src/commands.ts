/**
 * The native command API — the new server's own protocol.
 *
 * The original `command.php` dialect (see `./commandphp.ts`) is spoken by the
 * compatibility shim, so that the untouched `Basesec_1.5.4.swf` keeps
 * working. This module is the *other* dialect: the one the clone's own client
 * and server speak. It is versioned, typed and documented, and it exists so
 * that the clone does not inherit the original's structural defects.
 *
 * ## 1. The version
 *
 * Every request carries `v`, the protocol version. The server refuses a
 * version it does not speak, with a typed `unsupported-protocol-version`
 * error, before it looks at anything else in the body. `PROTOCOL_VERSION` is
 * the version this build speaks; `MIN_SUPPORTED_PROTOCOL_VERSION` and
 * `MAX_SUPPORTED_PROTOCOL_VERSION` are the range it accepts. A version bump
 * that only *adds* a command does not need a version bump: a command is
 * added to the table and the version stays. A version bump is needed when
 * the *shape* of the envelope changes.
 *
 * ## 2. The envelope
 *
 * A request is a JSON object:
 *
 * ```jsonc
 * {
 *   "v": 1,                       // the protocol version
 *   "id": "9f1c…",                // the client's idempotency key for this batch
 *   "token": "…",                 // the player's revocable session token
 *   "commands": [
 *     { "map": 0, "name": "buy", "args": [9001, 12, 3, 4, 1, 0, 0, "b"] }
 *   ]
 * }
 * ```
 *
 * A response is:
 *
 * ```jsonc
 * {
 *   "v": 1,
 *   "id": "9f1c…",                // echoed, so a retry can be matched
 *   "ok": true,
 *   "outcomes": [ { "index": 0, "ok": true, "result": { "kind": "state", … } } ],
 *   "errors": []
 * }
 * ```
 *
 * Three things the native envelope deliberately does **not** have, each
 * because the legacy dialect put something dangerous in it:
 *
 * - **No `USERID` in the body.** Upstream took the player identity from the
 *   request (`USERID` was a PHP session id in the query string) and trusted
 *   it. The native envelope carries a **session token** instead: revocable,
 *   issued by the server, and meaningless to anyone who does not hold it.
 *   (Non-negotiable 7; roadmap finding F10.)
 * - **No client-declared resource vector.** The legacy `comm[3]` was an
 *   8-slot delta that the upstream server applied verbatim, so a player could
 *   send `[0,0,1000000,0,0,0,0,0]` and be given a million gold. The native
 *   envelope has no field for it: there is nowhere to put it. The server
 *   computes every cost from the content bundle and the command's own
 *   arguments (`@swl/rules`' `computeCommandCost`). (Non-negotiable 3;
 *   roadmap finding F3.)
 * - **No client-declared combat outcome.** `end_quest` and `end_attack` used
 *   to carry the whole battle result, including the loot, and the server
 *   believed it. The native forms carry only the *inputs* — the quest or
 *   attack the server already knows about — and the server re-simulates from
 *   its own seed. (Non-negotiable 3; roadmap finding F5.)
 *
 * There is no `ts` either: the legacy body carried a client clock for
 * anti-time-hack checks. The native server owns the clock, and a client
 * timestamp would be a second client-declared fact to distrust.
 *
 * ## 3. The command table
 *
 * `COMMAND_TABLE` is the single shared definition of the command vocabulary:
 * the server validates against it, the client renders from it, and the
 * compatibility shim translates it into the legacy dialect. It is data, not
 * code, so that "what commands exist and what do they take" has exactly one
 * answer in the repository.
 *
 * Each entry says:
 *
 * - `args` — the positional argument list, in wire order, with a type per
 *   argument. The list is positional because the legacy one was, and the
 *   clone's client is a port of the original client.
 * - `costsResources` — the command spends resources, so the server must
 *   compute a cost and refuse it if the player cannot pay.
 * - `mutatesWorld` — the command changes state other players or the world
 *   simulation can observe (a building placed, a unit deployed, a tile
 *   bought), as opposed to state confined to the player's own save.
 * - `idempotent` — replaying the command changes nothing, because its effect
 *   is a function of the target state (set it, move it, remove it). A
 *   command that is *not* idempotent grants or spends something, so a
 *   duplicate delivery has to be suppressed by the request `id`.
 * - `result` — which typed result the command answers with.
 * - `forbidden` / `adminOnly` / `shapeKnown` — the policy switches, below.
 *
 * ### Argument shapes and the one rule they follow
 *
 * The argument list is the one in the command catalogue
 * (`re/docs/03-commands-quests-economy.md` §1), cross-checked against the
 * decompiled `Cmd*.as` classes. There is exactly one systematic difference,
 * and it follows from dropping the client-declared resource vector:
 *
 * > Where the legacy protocol expressed a **quantity**, a **payment
 * > resource** or a **price** only through the client-declared delta, the
 * > native command carries the quantity and/or the payment resource as an
 * > explicit argument, and the server derives the price from the content
 * > bundle. A client-declared *price* is never carried.
 *
 * That affects `buy_mana_new`, `buy_magic`, `trade_resource` and
 * `buy_resources`. The combat commands diverge for the other reason:
 * `end_attack` and `end_quest` carry no claimed outcome at all, and
 * `weekly_reward` carries nothing, because the server owns the reward it
 * grants. `finish_si` drops the amount the catalogue lists, because the
 * client never pushes it. Every other command keeps the catalogue's list
 * verbatim.
 *
 * ### The three policy switches
 *
 * - `forbidden` — the new server refuses the command outright.
 *   `flash_debug` overwrites the whole wallet from client arguments
 *   (non-negotiable 6, finding F4), and `set_variables` carries nothing but
 *   a client-declared delta, so it is the same defect under another name.
 * - `adminOnly` — the command is a tool, not part of the player API, so the
 *   native protocol refuses it for a player session. For most of them the
 *   client only ever sends them from its admin panel (`load_map`, `reset`,
 *   `save_map`, `system_receive_si_help`, `system_reset_quest`).
 *   `admin_set_quest_rank` is the exception: the client does send it after
 *   every quest, but the quest rank is the server’s own record of the quest
 *   it re-simulated, so the native protocol still refuses it.
 * - `shapeKnown` — false when the argument shape could not be recovered from
 *   the client. Such a command is refused rather than guessed at, because a
 *   server that accepts an argument list it cannot validate has no business
 *   accepting it at all.
 *
 * ## 4. Adding a command
 *
 * 1. Add the name to `COMMAND_NAMES` in `./index.ts`. The table is typed
 *    `Record<CommandName, CommandSpec>`, so the compiler will not let you
 *    forget the entry.
 * 2. Add the entry to `COMMAND_TABLE` here, with the argument list from the
 *    catalogue, and cite where the shape came from.
 * 3. If it spends resources, add it to `PRICED_COMMANDS` in
 *    `@swl/rules`' `commandcost.ts`, so the server can price it. A command
 *    the cost table does not price is *free*, never "whatever the client
 *    claimed".
 * 4. If the compatibility shim has to speak it to the legacy client, add
 *    the legacy wire name to the entry (`legacyWireName`) and translate to
 *    the legacy argument list there.
 * 5. Extend `commands.test.ts`. The test walks `COMMAND_NAMES` and the
 *    table and compares the key sets, so a name added in step 1 without a
 *    step-2 entry fails the build.
 */
import type { CommandName, MapItem, ResourceName } from './index.ts';

/* -------------------------------------------------------------------------
 * The version
 * ---------------------------------------------------------------------- */

/** The protocol version this build speaks. */
export const PROTOCOL_VERSION = 1;

/** The oldest protocol version this build still accepts. */
export const MIN_SUPPORTED_PROTOCOL_VERSION = 1;

/** The newest protocol version this build still accepts. */
export const MAX_SUPPORTED_PROTOCOL_VERSION = 1;

/**
 * Whether the server speaks a protocol version.
 *
 * The check is deliberately a *range*, so that a server can be rolled
 * forward one version at a time: a client on an older version is still
 * served, a client on a newer one is told to update.
 */
export function isSupportedVersion(version: number): boolean {
  return (
    Number.isInteger(version) &&
    version >= MIN_SUPPORTED_PROTOCOL_VERSION &&
    version <= MAX_SUPPORTED_PROTOCOL_VERSION
  );
}

/* -------------------------------------------------------------------------
 * The command table — the vocabulary
 * ---------------------------------------------------------------------- */

/** The families a command belongs to. */
export const COMMAND_FAMILIES = [
  'build',
  'production',
  'combat',
  'quest',
  'progression',
  'inventory',
  'unit',
  'research',
  'magic',
  'market',
  'minigame',
  'bonus',
  'map',
  'session',
  'admin',
] as const;

export type CommandFamily = (typeof COMMAND_FAMILIES)[number];

/** The kinds of typed result a command can answer with. */
export const RESULT_KINDS = [
  'none',
  'resources',
  'rewards',
  'state',
  'progress',
  'board',
  'unlock',
] as const;

export type ResultKind = (typeof RESULT_KINDS)[number];

/** The type of one positional argument. */
export type ArgType =
  | 'int'
  | 'uint'
  | 'number'
  | 'string'
  | 'boolean'
  | 'json'
  | 'array';

/** One positional argument of a command. */
export interface ArgSpec {
  /** The argument's name, as the catalogue calls it. */
  readonly name: string;
  /** The argument's type. */
  readonly type: ArgType;
  /** Whether the client may leave the argument out. */
  readonly optional?: boolean;
  /** The closed set of values the argument may take, when it has one. */
  readonly values?: readonly (string | number)[];
  /** A note about the argument's meaning or its gotcha. */
  readonly note?: string;
}

/** What one command is, and what it takes. */
export interface CommandSpec {
  /** The command's name. It is the key of the table. */
  readonly name: CommandName;
  /**
   * The name the legacy `command.php` client uses, when it differs.
   *
   * No command differs today: the table is keyed by the name in
   * `COMMAND_NAMES`, and that list now carries the client’s own spelling
   * for every command — `unit_collections_completed` is plural, as the
   * client, the catalogue and the upstream server all say. The field stays
   * for the compatibility shim, which must emit the legacy wire name; a
   * command that the clone spells differently gets its legacy name here.
   */
  readonly legacyWireName?: string;
  /** What the command does, in one line. */
  readonly summary: string;
  /** The family the command belongs to. */
  readonly family: CommandFamily;
  /** The positional arguments, in wire order. */
  readonly args: readonly ArgSpec[];
  /** The kind of result the command answers with. */
  readonly result: ResultKind;
  /** Whether the command spends resources. */
  readonly costsResources: boolean;
  /** Whether the command changes state other players can observe. */
  readonly mutatesWorld: boolean;
  /** Whether replaying the command is harmless. */
  readonly idempotent: boolean;
  /** Whether the new server refuses the command outright. */
  readonly forbidden?: boolean;
  /** Whether the command is a tool rather than part of the player API. */
  readonly adminOnly?: boolean;
  /** Whether the argument shape is known. */
  readonly shapeKnown: boolean;
  /** A note about the command's quirks or its divergence from the client. */
  readonly notes?: string;
}

const INT = (name: string, note?: string): ArgSpec => ({ name, type: 'int', note });
const UINT = (name: string, note?: string): ArgSpec => ({ name, type: 'uint', note });
const STR = (name: string, note?: string): ArgSpec => ({ name, type: 'string', note });
const JSON_ARG = (name: string, note?: string): ArgSpec => ({ name, type: 'json', note });
const ARR = (name: string, note?: string): ArgSpec => ({ name, type: 'array', note });
const INT_ENUM = (
  name: string,
  values: readonly number[],
  note?: string,
): ArgSpec => ({ name, type: 'int', values, note });
const STR_ENUM = (
  name: string,
  values: readonly string[],
  note?: string,
): ArgSpec => ({ name, type: 'string', values, note });

/**
 * The command vocabulary.
 *
 * Typed as `Record<CommandName, CommandSpec>`, so the compiler refuses to
 * let the table and `COMMAND_NAMES` drift apart: a name added to one and not
 * the other is a type error, and `commands.test.ts` checks the same thing at
 * runtime.
 */
export const COMMAND_TABLE: Readonly<Record<CommandName, CommandSpec>> = Object.freeze({
  accept_collect_help: {
    name: 'accept_collect_help',
    summary: 'Accept a friend’s help on one of your buildings.',
    family: 'production',
    args: [
      INT('isoID', 'the building reference id'),
      STR('friendId', 'the friend’s Facebook id'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the iso id and the friend’s fbid (commands/CmdAcceptCollectHelp.as:11). Each delivery is one friend’s help, so a duplicate has to be suppressed by the request id.',
  },

  activate: {
    name: 'activate',
    summary: 'Choose the collection period of a resource building.',
    family: 'production',
    args: [
      INT('isoID', 'the building reference id'),
      INT_ENUM('collectPeriod', [0, 1, 2, 3], 'the collect-period index `cp`; the server stores it in item.attr.cp and treats > 0 as activated'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the iso id and the stored collect-period index (commands/CmdActivate.as:13). The four periods are 5/60/240/480 minutes at x0.25/x1/x2/x3 (re/docs/03 §2.3).',
  },

  activate_item_click: {
    name: 'activate_item_click',
    summary: 'Click a building that is being built socially, to help it finish.',
    family: 'production',
    args: [
      INT('isoID', 'the building reference id'),
      { name: 'inventoryIds', type: 'json', optional: true, note: 'the building’s inventory_ids, JSON-encoded; sent only when the building has any' },
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'Each delivery is one friend click, so a duplicate must be suppressed by the request id.',
  },

  add_click: {
    name: 'add_click',
    summary: 'Add one friend click to a socially-built building.',
    family: 'production',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
  },

  add_inventory_item: {
    name: 'add_inventory_item',
    summary: 'Add items to the player’s inventory.',
    family: 'inventory',
    args: [INT('itemId', 'the inventory item id'), INT('quantity', 'how many')],
    result: 'rewards',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The legacy client paid cash here (qty x item.cashPrice) through the delta; the server prices it from the content bundle.',
  },

  add_xp_unit: {
    name: 'add_xp_unit',
    summary: 'Add experience to a unit, optionally levelling it up.',
    family: 'progression',
    args: [
      UINT('isoID', 'the unit iso id'),
      UINT('xp', 'the experience to add'),
      { name: 'level', type: 'uint', optional: true, note: 'the new unit level; sent only when it is not zero' },
    ],
    result: 'progress',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The legacy client paid the level-up price in cash through the delta; the server derives it from the unit’s XP table.',
  },

  admin_set_quest_rank: {
    name: 'admin_set_quest_rank',
    summary: 'Record the rank and difficulty the player finished a quest with.',
    family: 'quest',
    args: [
      STR('questIndex', 'the quest index, as a string'),
      STR_ENUM('difficulty', ['1', '2', '3'], 'the difficulty, as a string'),
    ],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    adminOnly: false,
    shapeKnown: true,
    notes:
      'The class is named `AdminCmdSetQuestRank`, so the upstream classifies it as ' +
      'administrative - but the CLIENT sends it during ordinary play: after every ' +
      'quest (quest/AbstractQuest.as:448) and after the weekly quest ' +
      '(popups/PopupWeeklyQuestFinished.as:101). Refusing it would break the quest ' +
      'flow, so it is NOT administrative here. The server still does not take the ' +
      'client difficulty on trust: the quest rank is the server own record of the ' +
      'quest it re-simulated (finding F5), and the difficulty is the one the server ' +
      'awarded.',
  },

  apply_rewards_ranking: {
    name: 'apply_rewards_ranking',
    summary: 'Take the reward of a ranking — the next-island attack.',
    family: 'bonus',
    args: [JSON_ARG('rewards', 'the reward payload, JSON-encoded by the client')],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the JSON reward payload and claims the cash in the delta (commands/CmdApplyRewardsRanking.as:12-13); the server grants the reward from its own ranking state.',
  },

  assist_neighbor: {
    name: 'assist_neighbor',
    summary: 'Help a neighbour finish a building.',
    family: 'production',
    args: [
      STR('friendId', 'the neighbour’s Facebook id'),
      JSON_ARG('clicks', 'an array of [tx, ty, buildingId] clicks, JSON-encoded by the client'),
    ],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the neighbour’s fbid and the clicked tiles (commands/CmdAssistNeighbour.as:19). Every click is worth 10 gold and 3 XP (Config.ASSIST_CLICK_REWARD_GOLD/XP); the server pays that itself.',
  },

  assist_receive: {
    name: 'assist_receive',
    summary: 'Receive the reward for a friend who helped one of your buildings.',
    family: 'production',
    args: [INT('buildingItemId', 'the content item id of the building that was helped, NOT an iso id')],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes only the building’s item id (commands/CmdAssistReceive.as:12); the reward map travelled in the client-declared delta, and the server derives the amount from its own assist state.',
  },

  attack_player: {
    name: 'attack_player',
    summary: 'Start an assault on another player.',
    family: 'combat',
    args: [STR('targetId', 'the target player’s Facebook id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the target’s fbid (commands/CmdAttackPlayer.as:9). The assault costs 30 energy (Config.COST_BUY_ATTACK); the upstream charges nothing, which is the same defect as finding F3.',
  },

  batch_remove: {
    name: 'batch_remove',
    summary: 'Remove several buildings at once.',
    family: 'map',
    args: [JSON_ARG('isoIds', 'an array of building iso ids, JSON-encoded by the client')],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
  },

  buy: {
    name: 'buy',
    summary: 'Buy a building or a unit and place it on the map.',
    family: 'build',
    args: [
      INT('isoID', 'the building reference id'),
      INT('itemId', 'the content item id'),
      INT('tx', 'the tile x'),
      INT('ty', 'the tile y'),
      INT('playerId', '1 = self, 2 = enemy, 3 = neutral'),
      INT('frame', 'the orientation frame'),
      INT_ENUM('autoActivatable', [0, 1], 'whether the building activates itself'),
      STR_ENUM('type', ['b', 'u', 'n'], 'the item type: building, unit or none'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The cost is the content item’s `costs` plus `cost_unit_cash`; the client’s claimed delta is ignored. The iso id makes a replay a no-op.',
  },

  buy_magic: {
    name: 'buy_magic',
    summary: 'Learn a magic spell.',
    family: 'magic',
    args: [
      INT('spellId', 'the magic spell id'),
      STR_ENUM('payment', ['g', 'c'], 'the resource the price is paid in: gold or cash'),
    ],
    result: 'unlock',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy args were [spellId] only (commands/CmdBuyMagic.as:11); the payment resource and the price travelled in the client-declared delta. The native form names the payment resource and the server prices the spell from the content bundle. A purchase also grants the spell’s mana cost, as the client does; cash may bypass the spell’s unlock level, gold may not.',
  },

  buy_mana_new: {
    name: 'buy_mana_new',
    summary: 'Buy mana.',
    family: 'magic',
    args: [
      INT('manaAmount', 'how much mana to buy'),
      STR_ENUM('payment', ['c', 'g'], 'the resource the price is paid in: cash or gold'),
    ],
    result: 'resources',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy command sent no arguments at all (commands/CmdBuyManaNew.as:10) — the amount, the price and the payment resource were all in the client-declared delta. The native form carries the amount and the payment resource; the server prices it from COST_MANA_CASH / COST_MANA_GOLD. There is one pack, MANA_PER_PURCHASE (5); another amount is refused.',
  },

  buy_offer_pack: {
    name: 'buy_offer_pack',
    summary: 'Buy an offer pack.',
    family: 'market',
    args: [
      INT('packId', 'the offer pack id'),
      JSON_ARG('itemIds', 'an array of item ids, JSON-encoded by the client'),
    ],
    result: 'rewards',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The price is the pack’s `cost_cash` in the content bundle; the client’s claimed delta is ignored.',
  },

  buy_powerups: {
    name: 'buy_powerups',
    summary: 'Buy a Soul Mixer power-up level.',
    family: 'build',
    args: [INT('levelIndex', 'the index into SOUL_MIXER_POWERUPS_LEVELS')],
    result: 'unlock',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
  },

  buy_premium_account: {
    name: 'buy_premium_account',
    summary: 'Buy a premium account package.',
    family: 'market',
    args: [INT_ENUM('packageIndex', [0, 1, 2, 3, 4, 5], 'the index into globals.PREMIUM_ACCOUNTS')],
    result: 'unlock',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the package index (commands/CmdBuyPremiumAccount.as:11) and claims the price in the delta; the server prices the package from PREMIUM_ACCOUNTS.',
  },

  buy_resources: {
    name: 'buy_resources',
    summary: 'Buy a resource pack from the store.',
    family: 'market',
    args: [
      STR_ENUM('resource', ['g', 'w', 'o', 's'], 'the resource the pack gives'),
      INT('amount', 'how much of it the pack gives'),
      STR_ENUM('payment', ['c', 'g'], 'the resource the price is paid in'),
    ],
    result: 'resources',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy command sent no arguments at all (commands/CmdBuyResources.as:9-16) — the gained map and the cost map were both in the client-declared delta. The native form carries the quantity and the payment resource; the server prices the pack from globals.RESOURCE_PACKS and never takes a price from the client.',
  },

  buy_si_help: {
    name: 'buy_si_help',
    summary: 'Pay cash for a friend to help finish a building.',
    family: 'production',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The price is the social item’s `worker_cost` in the content bundle.',
  },

  buy_stored_item_cash: {
    name: 'buy_stored_item_cash',
    summary: 'Buy a stored item with cash.',
    family: 'market',
    args: [INT('itemId', 'the content item id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The legacy price was in the client-declared delta only; the server prices it from the content bundle.',
  },

  clean_attacks: {
    name: 'clean_attacks',
    summary: 'Clear the list of received attacks.',
    family: 'combat',
    args: [],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client sends no arguments (commands/CmdCleanAttacks.as:8).',
  },

  clean_received_assists: {
    name: 'clean_received_assists',
    summary: 'Forget the help a neighbour gave you.',
    family: 'production',
    args: [STR('friendId', 'the neighbour’s Facebook id')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the neighbour’s fbid (commands/CmdCleanReceivedAssists.as:9).',
  },

  clear_message: {
    name: 'clear_message',
    summary: 'Dismiss the message the server left in the player’s inbox.',
    family: 'session',
    args: [],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client sends no arguments (commands/CmdClearMessage.as:8); it clears privateState.message once the popup was shown (core/Base.as:2315).',
  },

  collect: {
    name: 'collect',
    summary: 'Collect the production of a resource building.',
    family: 'production',
    args: [INT('isoID', 'the building reference id')],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The amount is computed by the server from the building’s `collect`, `collect_type` and `collect_xp`; the client’s claimed amount is ignored.',
  },

  collect_mission: {
    name: 'collect_mission',
    summary: 'Finish a chapter and collect its reward.',
    family: 'quest',
    args: [INT('nextChapterId', 'the NEXT chapter id, not the one that was finished')],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The argument is the NEXT chapter id (commands/CmdCollectChapter.as:13). The chapter reward is REWARDS_CHAPTERS[chapterId] in the content bundle.',
  },

  complete_collection: {
    name: 'complete_collection',
    summary: 'Complete an item collection, optionally buying it with cash.',
    family: 'inventory',
    args: [
      INT('collectionId', 'the collection id'),
      INT_ENUM('bought', [0, 1], '1 when the collection was bought rather than earned'),
    ],
    result: 'rewards',
    costsResources: true,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  complete_goal: {
    name: 'complete_goal',
    summary: 'Deliver a goal and take its reward.',
    family: 'progression',
    args: [INT('goalId', 'the goal id')],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The reward comes from the goal content, not from the client’s claimed delta.',
  },

  complete_tutorial: {
    name: 'complete_tutorial',
    summary: 'Mark a tutorial step as done.',
    family: 'progression',
    args: [INT('step', 'the tutorial step')],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  cross_promotion_finished: {
    name: 'cross_promotion_finished',
    summary: 'Record that a cross-promotion was finished.',
    family: 'bonus',
    args: [STR('promotionId', 'the cross-promotion id')],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the promotion id (commands/CmdCrossPromotionFinished.as:9).',
  },

  darts_new_free: {
    name: 'darts_new_free',
    summary: 'Claim the free darts shot of the day.',
    family: 'minigame',
    args: [],
    result: 'board',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  darts_reset: {
    name: 'darts_reset',
    summary: 'Start a new darts board for the week.',
    family: 'minigame',
    args: [INT('seed', 'the random seed of the new board')],
    result: 'board',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The board is drawn from the seed, so a replay with the same seed is a no-op.',
  },

  darts_shoot_balloon: {
    name: 'darts_shoot_balloon',
    summary: 'Shoot one of the 25 balloons of the darts board.',
    family: 'minigame',
    args: [
      INT_ENUM('targetIndex', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], 'the balloon that was shot'),
      INT_ENUM('wonExtra', [0, 1], '1 when the extra (major) prize was found'),
    ],
    result: 'board',
    costsResources: true,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'Argument 1 says whether the EXTRA prize was won, not whether the shot was free. The server knows whether a free shot is available; the paid shot costs DART_COST_CASH.',
  },

  end_attack: {
    name: 'end_attack',
    summary: 'Report the end of an assault on another player.',
    family: 'combat',
    args: [
      STR('attackId', 'the id of the attack the server issued'),
      { name: 'voluntaryEnd', type: 'boolean', note: 'whether the player walked away instead of finishing' },
    ],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy args were [JSON of the whole battle result, "1"|"0"] (commands/CmdEndAttack.as:14-15), i.e. the client claimed the outcome and the loot. The native form carries only the attack the server knows about; the server re-simulates from its own seed (finding F5).',
  },

  end_quest: {
    name: 'end_quest',
    summary: 'Report the end of a quest.',
    family: 'combat',
    args: [
      STR('questId', 'the quest that was played'),
      INT_ENUM('difficulty', [1, 2, 3], 'the difficulty the quest was played on'),
    ],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy arg was a JSON blob carrying the claimed outcome (units, win, duration, loot) (commands/CmdEndQuest.as:18). The native form carries only the quest and the difficulty; the server re-simulates from its own seed (finding F5).',
  },

  exchange_cash: {
    name: 'exchange_cash',
    summary: 'Exchange cash for gold.',
    family: 'market',
    args: [],
    result: 'resources',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The rate is BUY_GOLD_CASH : BUY_GOLD_GOLD (5 : 2500). The server computes it; the client never names a price.',
  },

  expand: {
    name: 'expand',
    summary: 'Buy the next tile of the town.',
    family: 'map',
    args: [INT('tileId', 'the expansion tile id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes only the tile id (commands/CmdExpand.as:10). The price comes from expansion_prices in the content bundle; the legacy client sent it in the delta.',
  },

  fast_forward: {
    name: 'fast_forward',
    summary: 'Advance the game clock. An admin tool.',
    family: 'admin',
    args: [INT('seconds', 'how far to advance the clock')],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    adminOnly: true,
    shapeKnown: true,
    notes: 'The client only ever sends this from its admin panel (AdminPanel.as:720,1410,1416).',
  },

  finish_building: {
    name: 'finish_building',
    summary: 'Finish a building that is under construction.',
    family: 'build',
    args: [
      INT('isoID', 'the building reference id'),
      INT('clicksToBuild', 'the clicks still needed, -1 when the building needs none'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client always pushes the iso id and the clicks still needed (commands/CmdFinishBuilding.as:9-10). The cash speed-up price travelled in the client-declared delta; the server derives it from the content bundle.',
  },

  finish_robotic_help: {
    name: 'finish_robotic_help',
    summary: 'Deliver the friends who helped the robotic research centre.',
    family: 'research',
    args: [JSON_ARG('friendIds', 'the friends’ Facebook ids, JSON-encoded by the client')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the JSON array of the friends who helped (commands/CmdFinishRoboticHelp.as:11). Every friend advances the research, so a duplicate has to be suppressed by the request id.',
  },

  finish_si: {
    name: 'finish_si',
    summary: 'Deliver the allies-market collection.',
    family: 'production',
    args: [
      INT('isoID', 'the building reference id'),
      { name: 'detail', type: 'int', optional: true, note: 'sent only when it is not -1' },
    ],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DISCREPANCY: the catalogue lists a third argument, the delivered amount. The client never pushes it: CmdFinishSi pushes the iso id and, at most, one more argument (commands/CmdFinishSi.as:11-14), and sends the amount and the resource type in the client-declared delta. The native server derives the amount from the allies-market state.',
  },

  flash_debug: {
    name: 'flash_debug',
    summary: 'Overwrite the whole wallet from client arguments. FORBIDDEN.',
    family: 'admin',
    args: [
      INT('cash'),
      INT('energy'),
      INT('xp'),
      INT('gold'),
      INT('oil'),
      INT('steel'),
      INT('wood'),
    ],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    forbidden: true,
    shapeKnown: true,
    notes:
      'The client sends this every twentieth command at player level 10 or above (CommandManager.as:158-161). The new server does not have it: it would overwrite the wallet from the client (non-negotiable 6, finding F4).',
  },

  kill: {
    name: 'kill',
    summary: 'Destroy a building on the map.',
    family: 'combat',
    args: [
      INT('isoID', 'the building reference id'),
      STR('buildingType', 'the item type of the building, "b" or "u"'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The loot travels in the legacy client-declared delta; the server computes it from the content bundle.',
  },

  kill_iid: {
    name: 'kill_iid',
    summary: 'Destroy a building, addressed by item id rather than by iso id.',
    family: 'combat',
    args: [
      INT('itemId', 'the content item id, NOT the iso id'),
      STR('buildingType', 'the item type of the building, "b" or "u"'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
  },

  level_up: {
    name: 'level_up',
    summary: 'Move the player to the next level.',
    family: 'progression',
    args: [INT('newLevel', 'the level the player reached')],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The level reward is the levels[] entry in the content bundle.',
  },

  load_map: {
    name: 'load_map',
    summary: 'Load a map by id. An admin tool.',
    family: 'admin',
    args: [STR('mapId', 'the map id')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    adminOnly: true,
    shapeKnown: true,
    notes: 'The client only ever sends this from its admin panel (GUI/AdminPanel.as:603).',
  },

  modify_energy: {
    name: 'modify_energy',
    summary: 'Ask the server to top the player’s energy up.',
    family: 'session',
    args: [],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client sends no arguments (commands/CmdModifyEnergy.as:10-11) — the deficit it wanted was in the client-declared delta. The server grants the energy the player is owed, up to ENERGY_MAX_REGULAR_VALUE (30), and ignores the claimed deficit.',
  },

  modify_position_universe: {
    name: 'modify_position_universe',
    summary: 'Swap the player’s position in the universe map.',
    family: 'map',
    args: [
      INT('fromPosition', 'the first continent position'),
      INT('toPosition', 'the second continent position'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client pushes two integers (commands/CmdModifyPositionUniverse.as:9); the call site swaps the player’s continent position with the next one (newTowns/ExplorationsManager.as:399).',
  },

  move: {
    name: 'move',
    summary: 'Move a building or a unit to another tile.',
    family: 'map',
    args: [
      INT('isoID', 'the building reference id'),
      INT('tx', 'the tile x'),
      INT('ty', 'the tile y'),
      INT('frame', 'the orientation frame'),
      STR('reason', 'a free-text label, e.g. "Unitat 12345"'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
  },

  next_research_item: {
    name: 'next_research_item',
    summary: 'Start the next research item of a research centre.',
    family: 'research',
    args: [UINT('researchType', '0 = Area 51, 1 = Robotic Center')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the research type (commands/CmdNextResearchItem.as:9).',
  },

  next_research_step: {
    name: 'next_research_step',
    summary: 'Complete one step of a research.',
    family: 'research',
    args: [
      UINT('researchType', '0 = Area 51, 1 = Robotic Center'),
      { name: 'restartCountdown', type: 'boolean', note: 'whether the research countdown starts again' },
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client pushes the research type and whether the countdown restarts (commands/CmdNextResearchStep.as:9-10; popups/PopupResearchCenter.as:405).',
  },

  orient: {
    name: 'orient',
    summary: 'Change the facing of a building on the map.',
    family: 'map',
    args: [
      INT('isoID', 'the building reference id'),
      INT('frame', 'the orientation frame'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the iso id and the frame (commands/CmdOrient.as:18).',
  },

  ping: {
    name: 'ping',
    summary: 'Keep the session alive.',
    family: 'session',
    args: [],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  place_gift: {
    name: 'place_gift',
    summary: 'Place a gift on the map.',
    family: 'build',
    args: [
      INT('isoID', 'the building reference id'),
      INT('itemId', 'the content item id of the gift'),
      INT('tx', 'the tile x'),
      INT('ty', 'the tile y'),
      INT('frame', 'the orientation frame'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client pushes the iso id, the item id, the tile and the frame (commands/CmdPlaceGift.as:14-17). The XP the gift is worth travelled in the client-declared delta; the server grants it.',
  },

  place_stored_item: {
    name: 'place_stored_item',
    summary: 'Place an item that is in the store onto the map.',
    family: 'build',
    args: [
      INT('isoID', 'the building reference id'),
      INT('itemId', 'the content item id'),
      INT('tx', 'the tile x'),
      INT('ty', 'the tile y'),
      INT('playerId', '1 = self, 2 = enemy, 3 = neutral'),
      INT('frame', 'the orientation frame'),
      INT_ENUM('autoActivatable', [0, 1], 'whether the building activates itself'),
      INT('imgIndex', 'the sprite variant'),
      { name: 'unitLevel', type: 'int', optional: true, note: 'the level + 1 of a marketplace-won unit' },
      { name: 'requiredXp', type: 'int', optional: true, note: 'the XP that level needs; sent together with unitLevel' },
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The last two arguments are sent together, and only for a marketplace-won unit. The client declares no cost for a placement, but the cost table charges the item’s build costs (packages/rules/src/commandcost.ts:143-148).',
  },

  premium_upgrade: {
    name: 'premium_upgrade',
    summary: 'Replace a building with its upgraded version, paying cash for the speed.',
    family: 'build',
    args: [
      INT('oldIsoID', 'the iso id of the building that is replaced'),
      INT('newIsoID', 'the iso id of the new building'),
      INT('newItemId', 'the content item id of the new building'),
      INT('clicksToBuild', 'the clicks still needed, -1 when the building needs none'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes:
      'Argument 0 is the OLD iso id and argument 1 the NEW one, so a clone must remove the old building and add the new one (commands/CmdPremiumUpgrade.as:10-13; core/isoengine/IsoBuilding.as:675).',
  },

  pop_queue_unit: {
    name: 'pop_queue_unit',
    summary: 'Take a unit out of a training queue.',
    family: 'unit',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The legacy client paid a cash surcharge here through the delta; the server prices it from the content bundle.',
  },

  pop_unit: {
    name: 'pop_unit',
    summary: 'Move a unit out of a building and onto the map.',
    family: 'unit',
    args: [
      INT('buildingIsoID', 'the building the unit comes from'),
      INT('unitIsoID', 'the unit itself'),
      INT('unitItemId', 'the content item id of the unit'),
      { name: 'x', type: 'int', optional: true, note: 'sent only in the full form' },
      { name: 'y', type: 'int', optional: true, note: 'sent only in the full form' },
      { name: 'playerId', type: 'int', optional: true, note: 'sent only in the full form' },
      { name: 'frame', type: 'int', optional: true, note: 'sent only in the full form' },
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The last four arguments are sent together, or not at all.',
  },

  push_queue_unit: {
    name: 'push_queue_unit',
    summary: 'Put a unit into a building’s training queue.',
    family: 'unit',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes: 'The unit cost travels in the legacy client-declared delta; the server prices it from the content bundle.',
  },

  push_queue_unit2: {
    name: 'push_queue_unit2',
    summary: 'Put a unit into a building\'s training queue, naming the unit.',
    family: 'unit',
    args: [
      INT('isoID', 'the building reference id'),
      INT('unitItemId', 'the id of the unit being trained'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The SM variant of push_queue_unit, and it carries the trained unit id as well ' +
      '(commands/CmdPushUnitSM.as:12-19). The name ends in a digit, which is why a ' +
      'digit-blind search over the client command classes misses it.',
  },

  push_unit: {
    name: 'push_unit',
    summary: 'Move a unit from the map into a building.',
    family: 'unit',
    args: [
      INT('unitIsoID', 'the unit itself'),
      INT('buildingIsoID', 'the building it goes into'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The order is (unit, building) (commands/CmdPushUnit.as:17) — the opposite of pop_unit (commands/CmdPopUnit.as:17-19).',
  },

  remove_inventory_item: {
    name: 'remove_inventory_item',
    summary: 'Take items out of the player’s inventory.',
    family: 'inventory',
    args: [INT('itemId', 'the inventory item id'), INT('quantity', 'how many')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  research_buy_step_cash: {
    name: 'research_buy_step_cash',
    summary: 'Buy the next step of a research with cash.',
    family: 'research',
    args: [
      INT('cashCost', 'the price the client believes it is paying'),
      UINT('researchType', '0 = Area 51, 1 = Robotic Center'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The server must NOT trust `cashCost`; it prices the step from the content bundle.',
  },

  reset: {
    name: 'reset',
    summary: 'Reset the player’s game. An admin tool.',
    family: 'admin',
    args: [],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    adminOnly: true,
    shapeKnown: true,
    notes: 'The client only ever sends this from its admin panel (GUI/AdminPanel.as:1391,1398).',
  },

  reset_collect: {
    name: 'reset_collect',
    summary: 'Reactivate a wonder, paying cash for it.',
    family: 'production',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client pushes the iso id (commands/CmdResetCollect.as:13) and claims the cash price in the delta; the server derives the price from the content bundle.',
  },

  reset_position_univers: {
    name: 'reset_position_univers',
    summary: 'Reset the player’s position in the universe map, so that they can relocate.',
    family: 'map',
    args: [],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client sends no arguments (commands/CmdResetPositionUniverse.as:8). The wire name is the client’s own misspelling of "universe".',
  },

  reset_research_item: {
    name: 'reset_research_item',
    summary: 'Reset the research of one research centre.',
    family: 'research',
    args: [UINT('researchType', '0 = Area 51, 1 = Robotic Center')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  reset_world_change: {
    name: 'reset_world_change',
    summary: 'Clear the flag that says the world changed and the island reward is due.',
    family: 'map',
    args: [],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client sends no arguments (commands/CmdResetIslandChange.as:8); it clears privateState.worldChange once the island-change reward popup was shown (newTowns/ExplorationsManager.as:438).',
  },

  resurrect_hero: {
    name: 'resurrect_hero',
    summary: 'Bring a dead hero back to life.',
    family: 'unit',
    args: [
      INT('isoID', 'the building reference id'),
      INT('itemId', 'the hero item id'),
      INT('x', 'the tile x'),
      INT('y', 'the tile y'),
      INT_ENUM('usedSyringe', [0, 1], '1 when a resurrection syringe was spent'),
    ],
    result: 'state',
    costsResources: true,
    mutatesWorld: true,
    idempotent: false,
    shapeKnown: true,
    notes: 'The syringe price travelled in the legacy client-declared delta; the server derives it from the content bundle.',
  },

  rt_open_graph_unit: {
    name: 'rt_open_graph_unit',
    summary: 'Publish a unit to the Open Graph.',
    family: 'unit',
    args: [INT('itemId', 'the content item id of the unit')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the unit’s item id (commands/CmdNewOpenGraphUnit.as:11).',
  },

  save_map: {
    name: 'save_map',
    summary: 'Save a map by id. An admin tool.',
    family: 'admin',
    args: [STR('mapId', 'the map id')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    adminOnly: true,
    shapeKnown: true,
    notes: 'The client only ever sends this from its admin panel (GUI/AdminPanel.as:592).',
  },

  sell: {
    name: 'sell',
    summary: 'Remove a building from the map and refund part of its cost.',
    family: 'build',
    args: [
      INT('isoID', 'the building reference id'),
      STR('reason', 'why it was removed: KILL, CLEAN, SQEST, CQEST, REGEN, TREAS, HARV, STABL, UPGR, FARM, BLDZE, RECDR, DEBUG, VEHIC, ACTIV, ATRZO, COLQS, BOSS, OUTOB or SUMMON'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
    notes: 'The refund is the build cost divided by DIVISOR_SELL (20), paid by the server.',
  },

  sell_gift: {
    name: 'sell_gift',
    summary: 'Sell a gift and get part of its cost back.',
    family: 'market',
    args: [INT('itemId', 'the content item id of the gift')],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the item id and claims the refund in the delta (commands/CmdSellGift.as:15); the server pays cost / DIVISOR_SELL (20).',
  },

  sell_stored_item: {
    name: 'sell_stored_item',
    summary: 'Sell a stored item and get gold for it.',
    family: 'market',
    args: [INT('itemId', 'the content item id')],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
  },

  set_goals: {
    name: 'set_goals',
    summary: 'Record the progress of a goal.',
    family: 'progression',
    args: [
      INT('goalId', 'the goal id'),
      JSON_ARG('progress', 'an array [visited ? 1 : 0, currentStep], JSON-encoded by the client'),
    ],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  set_help_map: {
    name: 'set_help_map',
    summary: 'Record which buildings the player has been asked to help with.',
    family: 'progression',
    args: [STR('helpMap', 'the serialised help map')],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  set_quest_var: {
    name: 'set_quest_var',
    summary: 'Set one key of the chapter state machine.',
    family: 'quest',
    args: [
      STR('key', 'the state key, e.g. "spawned" or "killed"'),
      JSON_ARG('value', 'the value, JSON-encoded by the client'),
    ],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  set_resource_allies: {
    name: 'set_resource_allies',
    summary: 'Say which resource the allies market currently offers.',
    family: 'production',
    args: [
      STR_ENUM('resource', ['g', 'w', 'o', 's'], 'the resource key the market offers'),
      INT('isoID', 'the building reference id'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
  },

  set_strategy: {
    name: 'set_strategy',
    summary: 'Choose the defensive strategy for the next attack.',
    family: 'combat',
    args: [INT('strategy', 'the defensive strategy')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the strategy (commands/CmdSetStrategy.as:9; popups/PopUpBattleOptions.as:108).',
  },

  set_variables: {
    name: 'set_variables',
    summary: 'Set player resources from a client-declared delta. FORBIDDEN.',
    family: 'admin',
    args: [],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    forbidden: true,
    adminOnly: true,
    shapeKnown: true,
    notes:
      'The client sends this only from its admin panel. Its entire payload is the client-declared resource delta, which is exactly what the new server must never apply (finding F3).',
  },

  soulmixer_speedup: {
    name: 'soulmixer_speedup',
    summary: 'Pay cash to speed up a Soul Mixer training.',
    family: 'build',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes: 'The legacy price travelled in the client-declared delta; the server derives it from the content bundle.',
  },

  spy_player: {
    name: 'spy_player',
    summary: 'Spy on another player.',
    family: 'combat',
    args: [STR('targetId', 'the target player’s Facebook id')],
    result: 'state',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the target’s fbid (commands/CmdSpyPlayer.as:9). Spying costs 15 energy (Config.COST_BUY_SPYINGS); the upstream charges nothing.',
  },

  store_add_items: {
    name: 'store_add_items',
    summary: 'Put items into the store.',
    family: 'inventory',
    args: [ARR('itemIds', 'the item ids; a raw array, not a JSON-encoded string')],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
  },

  store_item: {
    name: 'store_item',
    summary: 'Move a building from the map into the store.',
    family: 'inventory',
    args: [INT('isoID', 'the building reference id')],
    result: 'state',
    costsResources: false,
    mutatesWorld: true,
    idempotent: true,
    shapeKnown: true,
  },

  system_receive_mana: {
    name: 'system_receive_mana',
    summary: 'Receive mana from the server.',
    family: 'magic',
    args: [INT('amount', 'the mana received')],
    result: 'resources',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client pushes the amount and claims it in the delta (commands/CmdReceiveMana.as:11-12); the server grants the mana the player is entitled to, not the claimed amount.',
  },

  system_receive_si_help: {
    name: 'system_receive_si_help',
    summary: 'Receive a friend’s help on one of your buildings. An admin tool.',
    family: 'admin',
    args: [
      INT('isoID', 'the building reference id'),
      STR('friendId', 'the friend’s Facebook id'),
    ],
    result: 'state',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    adminOnly: true,
    shapeKnown: true,
    notes:
      'The client pushes the iso id and the friend’s fbid (commands/CmdSystemReceiveSiHelp.as:9); it is only sent from the admin panel (GUI/AdminPanel.as:992).',
  },

  system_reset_quest: {
    name: 'system_reset_quest',
    summary: 'Reset the quest progress. An admin tool.',
    family: 'admin',
    args: [],
    result: 'none',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    adminOnly: true,
    shapeKnown: true,
    notes:
      'The client sends no arguments (commands/SystemCmdResetQuest.as:8); it is only sent from the admin panel (GUI/AdminPanel.as:422).',
  },

  trade_resource: {
    name: 'trade_resource',
    summary: 'Buy or sell a resource on the player’s own market.',
    family: 'market',
    args: [
      STR_ENUM('resource', ['w', 's', 'o', 'g'], 'the resource key'),
      INT_ENUM('sell', [0, 1], '1 to sell, 0 to buy'),
      INT('amount', 'how many units are traded'),
    ],
    result: 'resources',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy args were [resource, sell] only (commands/CmdTradeResource.as:11-12) — the amount and the gold price travelled in the client-declared delta. The native form carries the amount and the server prices it with the market formula. DISCREPANCY: the upstream comment calls the second argument "1 if sold, 2 if bought", but the client sends 1 for a sale and 0 for a purchase.',
  },

  unit_collections_completed: {
    name: 'unit_collections_completed',
    summary: 'Report that a unit collection was completed.',
    family: 'inventory',
    args: [INT('collectionId', 'the collection id')],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The client, the catalogue and the upstream server all use the plural `unit_collections_completed` (commands/CmdUnitCollectionCompleted.as:10), and so does COMMAND_NAMES. The client claims one cash in the delta; the server grants the reward itself.',
  },

  upgrade: {
    name: 'upgrade',
    summary: 'Level a unit up.',
    family: 'progression',
    args: [INT('isoID', 'the unit iso id')],
    result: 'progress',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The client pushes the unit’s iso id (commands/CmdUpgrade.as:11) after it has raised the unit’s level (core/isoengine/IsoInteractiveElement.as:309-311). The level-up price is the server’s to compute.',
  },

  use_magic: {
    name: 'use_magic',
    summary: 'Cast a magic spell.',
    family: 'magic',
    args: [INT('spellId', 'the magic spell id')],
    result: 'resources',
    costsResources: true,
    mutatesWorld: false,
    idempotent: false,
    shapeKnown: true,
    notes:
      'The mana cost is the spell’s `manaCost` in the content bundle. The server checks that the spell is learned, deducts the mana and increments the use counter, which stops at `NUM_SPELL_USES_LVL3` (50). The protocol carries no target, so the battle effect itself is not server-simulated.',
  },

  win_daily_bonus: {
    name: 'win_daily_bonus',
    summary: 'Claim the daily login bonus.',
    family: 'bonus',
    args: [
      INT('itemId', 'the hero item id on the fifth day, 0 on a gold day'),
      INT_ENUM('dayIndex', [1, 2, 3, 4, 5], 'the day of the five-day cycle'),
    ],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes: 'The client pushes the item id first and the day index second (commands/CmdWinBonus.as:12). The gold of a day is DAILY_GOLD_REWARDS[dayIndex - 1] in the content bundle.',
  },

  win_alliance_daily_bonus: {
    name: 'win_alliance_daily_bonus',
    summary: 'Claim the alliance daily bonus.',
    family: 'bonus',
    args: [],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'The same shape as weekly_reward. The class does not call super() with the name: ' +
      'it extends CmdCollectMondayBonus and overrides commandID instead ' +
      '(commands/CmdCollectAlliancesBonus.as:9-12), which is the second way a command ' +
      'class names itself. The tier comes from the alliance member count, not from an ' +
      'argument.',
  },

  weekly_reward: {
    name: 'weekly_reward',
    summary: 'Claim the Monday bonus.',
    family: 'bonus',
    args: [],
    result: 'rewards',
    costsResources: false,
    mutatesWorld: false,
    idempotent: true,
    shapeKnown: true,
    notes:
      'DIVERGENCE: the legacy form sent no arguments for a resource reward, and five placement arguments for a unit reward (commands/CmdCollectMondayBonus.as:38-42); the amount and the unit travelled in the client-declared delta. The server owns the reward — it already advances weeklyRewardIndex itself — so the native form asks for nothing and answers with the reward that was granted.',
  },
} as const satisfies Readonly<Record<CommandName, CommandSpec>>);

/** The names of every command in the table. */
export function commandNames(): CommandName[] {
  return Object.keys(COMMAND_TABLE) as CommandName[];
}

/** The specification of one command, or undefined when the name is unknown. */
export function getCommandSpec(name: string): CommandSpec | undefined {
  return Object.prototype.hasOwnProperty.call(COMMAND_TABLE, name)
    ? COMMAND_TABLE[name as CommandName]
    : undefined;
}

/** The fewest arguments a command may be called with. */
export function minArgs(spec: CommandSpec): number {
  return spec.args.filter((arg) => arg.optional !== true).length;
}

/** The most arguments a command may be called with. */
export function maxArgs(spec: CommandSpec): number {
  return spec.args.length;
}

/* -------------------------------------------------------------------------
 * The request envelope
 * ---------------------------------------------------------------------- */

/**
 * One command inside a request.
 *
 * The map is the town the command applies to; 0 is the player's own town.
 * There is deliberately **no** resource vector: the server computes the cost.
 */
export interface NativeCommand {
  /** The town the command applies to. 0 is the player's own town. */
  readonly map: number;
  /** The command's name. */
  readonly name: CommandName;
  /** The positional arguments, in the order the table lists them. */
  readonly args: readonly unknown[];
}

/** A request in the native protocol. */
export interface NativeRequest {
  /** The protocol version. */
  readonly v: number;
  /**
   * The client's idempotency key for this batch.
   *
   * A retry of a request that was lost in flight carries the same `id`, and
   * the server answers with the stored response instead of applying the
   * commands twice. A command that is not idempotent — one that grants or
   * spends — depends on this.
   */
  readonly id: string;
  /**
   * The player's revocable session token.
   *
   * It identifies a *session*, not a player id, and it is the only thing in
   * the body that says who is asking. There is no `USERID`: upstream took
   * the player identity from the request and trusted it (finding F10).
   */
  readonly token: string;
  /** The commands of this batch, in order. */
  readonly commands: readonly NativeCommand[];
}

/**
 * The most commands one request may carry.
 *
 * A limit, not a rule of the game: the server may lower it. It exists so a
 * single request cannot make the server do unbounded work (roadmap F4).
 */
export const MAX_COMMANDS_PER_REQUEST = 256;

/* -------------------------------------------------------------------------
 * The response envelope
 * ---------------------------------------------------------------------- */

/** A resource delta, by resource name. */
export type ResourceDelta = Readonly<Record<ResourceName, number>>;

/** One thing the server granted. */
export interface Reward {
  /** The resource that was granted. */
  readonly resource: ResourceName;
  /** How much of it. */
  readonly amount: number;
}

/** The part of the map that changed. */
export interface StatePatch {
  /** The map the patch applies to. */
  readonly map: number;
  /** The buildings that changed, keyed by iso id. */
  readonly items?: Readonly<Record<string, MapItem>>;
  /** The iso ids of the buildings that were removed. */
  readonly removed?: readonly string[];
}

/** The progression that changed. */
export interface ProgressPatch {
  /** The goal progress, by goal id. */
  readonly goals?: Readonly<Record<string, number>>;
  /** The chapter state machine variables. */
  readonly questVars?: Readonly<Record<string, unknown>>;
  /** The tutorial step the player is on. */
  readonly tutorial?: number;
  /** The player’s level. */
  readonly level?: number;
}

/** The darts board. */
export interface DartsBoard {
  /** The seed the board was drawn from. */
  readonly seed: number;
  /** The balloons that have been shot. */
  readonly shot: readonly number[];
  /** Whether a free shot is still available. */
  readonly hasFree: boolean;
  /** Whether the extra (major) prize has been found. */
  readonly gotExtra: boolean;
}

/** The typed result of one command. */
export type CommandResult =
  | { readonly kind: 'none' }
  | { readonly kind: 'resources'; readonly delta: ResourceDelta }
  | { readonly kind: 'rewards'; readonly rewards: readonly Reward[] }
  | { readonly kind: 'state'; readonly state: StatePatch }
  | { readonly kind: 'progress'; readonly progress: ProgressPatch }
  | { readonly kind: 'board'; readonly board: DartsBoard }
  | { readonly kind: 'unlock'; readonly unlocked: readonly number[] };

/** What happened to one command of a request. */
export type CommandOutcome =
  | { readonly index: number; readonly ok: true; readonly result: CommandResult }
  | { readonly index: number; readonly ok: false; readonly error: CommandError };

/** A response in the native protocol. */
export interface NativeResponse {
  /** The protocol version the server answered with. */
  readonly v: number;
  /** The request id, echoed. */
  readonly id: string;
  /** Whether every command was applied. */
  readonly ok: boolean;
  /** One entry per command of the request, in order. */
  readonly outcomes: readonly CommandOutcome[];
  /** The errors that are not tied to a single command. */
  readonly errors: readonly CommandError[];
}

/* -------------------------------------------------------------------------
 * Errors
 * ---------------------------------------------------------------------- */

/** The typed error codes the native protocol answers with. */
export const ERROR_CODES = [
  'unsupported-protocol-version',
  'malformed-request',
  'missing-session-token',
  'invalid-session-token',
  'unknown-command',
  'forbidden-command',
  'unspecified-command',
  'invalid-argument',
  'invalid-argument-count',
  'insufficient-resources',
  'command-failed',
] as const;

export type ErrorCode = (typeof ERROR_CODES)[number];

/**
 * The HTTP status each error code answers with.
 *
 * Every one of them is a 4xx. Bad input is the client's problem, and it is
 * reported as a typed error, never as a 500 (roadmap F4).
 */
export const HTTP_STATUS: Readonly<Record<ErrorCode, number>> = Object.freeze({
  'unsupported-protocol-version': 400,
  'malformed-request': 400,
  'missing-session-token': 401,
  'invalid-session-token': 401,
  'unknown-command': 400,
  'forbidden-command': 403,
  'unspecified-command': 400,
  'invalid-argument': 400,
  'invalid-argument-count': 400,
  'insufficient-resources': 402,
  'command-failed': 409,
});

/** A typed error. */
export interface CommandError {
  /** The machine-readable code. */
  readonly code: ErrorCode;
  /** The human-readable explanation. */
  readonly message: string;
  /** The HTTP status the endpoint should answer with. */
  readonly status: number;
  /** The index of the offending command, when the error is command-scoped. */
  readonly commandIndex?: number;
  /** The name of the offending command, when the error is command-scoped. */
  readonly command?: string;
  /** The index of the offending argument, when the error is argument-scoped. */
  readonly argumentIndex?: number;
  /** What was expected, for a human-readable message. */
  readonly expected?: string;
}

function makeError(
  code: ErrorCode,
  message: string,
  extra: Partial<Omit<CommandError, 'code' | 'message' | 'status'>> = {},
): CommandError {
  return { code, message, status: HTTP_STATUS[code], ...extra };
}

/** The HTTP status an error code answers with. */
export function errorStatus(code: ErrorCode): number {
  return HTTP_STATUS[code];
}

/* -------------------------------------------------------------------------
 * Validation
 * ---------------------------------------------------------------------- */

/** Who is making the request. */
export type CallerRole = 'player' | 'admin';

/** The options of {@link validateRequest}. */
export interface ValidationOptions {
  /** The caller's role. Admin-only commands are refused for a player. */
  readonly role?: CallerRole;
}

/** What the validator found. */
export interface ValidationResult {
  /** Whether the request is well formed. */
  readonly ok: boolean;
  /** Every error found, in the order they were found. */
  readonly errors: readonly CommandError[];
  /** The request, when it is well formed enough to be used. */
  readonly request: NativeRequest | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isJsonValue(value: unknown): boolean {
  if (value === undefined) return false;
  if (typeof value === 'string') {
    try {
      JSON.parse(value);
      return true;
    } catch {
      return false;
    }
  }
  // An already-decoded JSON value.
  return (
    value === null ||
    typeof value === 'number' ||
    typeof value === 'boolean' ||
    Array.isArray(value) ||
    typeof value === 'object'
  );
}

function describeValue(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'an array';
  if (typeof value === 'object') return 'an object';
  if (typeof value === 'string') return `a string (${JSON.stringify(value)})`;
  return `${typeof value} (${String(value)})`;
}

/**
 * Check one argument against its specification.
 *
 * Returns the expected-type description when the value is wrong, or null
 * when it is right.
 */
function checkArgument(spec: ArgSpec, value: unknown): string | null {
  switch (spec.type) {
    case 'int':
      if (!Number.isInteger(value)) return 'an integer';
      break;
    case 'uint':
      if (!Number.isInteger(value) || (value as number) < 0) return 'a non-negative integer';
      break;
    case 'number':
      if (typeof value !== 'number' || !Number.isFinite(value)) return 'a finite number';
      break;
    case 'string':
      if (typeof value !== 'string') return 'a string';
      break;
    case 'boolean':
      if (typeof value !== 'boolean') return 'a boolean';
      break;
    case 'array':
      if (!Array.isArray(value)) return 'an array';
      break;
    case 'json':
      if (!isJsonValue(value)) return 'a JSON value';
      break;
  }
  if (spec.values !== undefined) {
    const allowed = spec.values;
    if (!allowed.some((candidate) => candidate === value)) {
      return `one of ${allowed.map((v) => JSON.stringify(v)).join(', ')}`;
    }
  }
  return null;
}

/**
 * Validate the arguments of one command against the table.
 *
 * The errors are returned, not thrown: a command with bad arguments is a
 * client mistake, and it has to be reported as a typed error rather than as
 * a crash.
 */
export function validateCommandArguments(
  name: string,
  args: readonly unknown[],
): CommandError[] {
  const errors: CommandError[] = [];
  const spec = getCommandSpec(name);
  if (spec === undefined) {
    errors.push(
      makeError('unknown-command', `there is no command named "${name}"`, {
        command: name,
      }),
    );
    return errors;
  }
  if (spec.forbidden === true) {
    errors.push(
      makeError('forbidden-command', `the command "${name}" is not available on this server`, {
        command: name,
      }),
    );
    return errors;
  }
  if (!spec.shapeKnown) {
    errors.push(
      makeError(
        'unspecified-command',
        `the command "${name}" has no specified argument shape and cannot be accepted`,
        { command: name },
      ),
    );
    return errors;
  }

  const least = minArgs(spec);
  const most = maxArgs(spec);
  if (args.length < least || args.length > most) {
    errors.push(
      makeError(
        'invalid-argument-count',
        `the command "${name}" takes ${least === most ? least : `${least} to ${most}`} arguments, but ${args.length} were given`,
        { command: name, expected: `${least}..${most} arguments` },
      ),
    );
    return errors;
  }

  for (let i = 0; i < args.length; i += 1) {
    const arg = spec.args[i];
    if (arg === undefined) continue;
    const value = args[i];
    const expected = checkArgument(arg, value);
    if (expected !== null) {
      errors.push(
        makeError(
          'invalid-argument',
          `argument ${i} of "${name}" (${arg.name}) must be ${expected}, but it is ${describeValue(value)}`,
          {
            command: name,
            argumentIndex: i,
            expected,
          },
        ),
      );
    }
  }
  return errors;
}

/**
 * Validate a request against the protocol version and the command table.
 *
 * The validator never throws and never rejects the request as a whole for a
 * single bad command: it collects every error, so a client learns about all
 * of its mistakes at once. Whether the server then applies *none* of the
 * commands is the server's transactional decision, not this module's.
 */
export function validateRequest(
  input: unknown,
  options: ValidationOptions = {},
): ValidationResult {
  const role: CallerRole = options.role ?? 'player';
  const errors: CommandError[] = [];

  if (!isRecord(input)) {
    errors.push(
      makeError('malformed-request', `the request body must be a JSON object, but it is ${describeValue(input)}`),
    );
    return { ok: false, errors, request: null };
  }

  const version = input['v'];
  if (typeof version !== 'number' || !Number.isInteger(version)) {
    errors.push(
      makeError(
        'unsupported-protocol-version',
        `the request must carry an integer protocol version "v", but it carries ${describeValue(version)}`,
        { expected: `an integer between ${MIN_SUPPORTED_PROTOCOL_VERSION} and ${MAX_SUPPORTED_PROTOCOL_VERSION}` },
      ),
    );
    return { ok: false, errors, request: null };
  }
  if (!isSupportedVersion(version)) {
    errors.push(
      makeError(
        'unsupported-protocol-version',
        `this server speaks protocol version ${MIN_SUPPORTED_PROTOCOL_VERSION} to ${MAX_SUPPORTED_PROTOCOL_VERSION}, but the request asks for ${version}`,
        { expected: `an integer between ${MIN_SUPPORTED_PROTOCOL_VERSION} and ${MAX_SUPPORTED_PROTOCOL_VERSION}` },
      ),
    );
    return { ok: false, errors, request: null };
  }

  const id = input['id'];
  if (typeof id !== 'string' || id.length === 0) {
    errors.push(
      makeError('malformed-request', `the request must carry a non-empty string request id "id", but it carries ${describeValue(id)}`),
    );
  }

  const token = input['token'];
  if (typeof token !== 'string' || token.length === 0) {
    errors.push(
      makeError('missing-session-token', 'the request must carry the player’s session token "token"'),
    );
  }

  const rawCommands = input['commands'];
  if (!Array.isArray(rawCommands)) {
    errors.push(
      makeError('malformed-request', `the request must carry an array of commands, but it carries ${describeValue(rawCommands)}`),
    );
    return { ok: false, errors, request: null };
  }
  if (rawCommands.length > MAX_COMMANDS_PER_REQUEST) {
    errors.push(
      makeError(
        'malformed-request',
        `the request carries ${rawCommands.length} commands, but at most ${MAX_COMMANDS_PER_REQUEST} are allowed`,
      ),
    );
  }

  const commands: NativeCommand[] = [];
  for (let index = 0; index < rawCommands.length; index += 1) {
    const raw = rawCommands[index];
    if (!isRecord(raw)) {
      errors.push(
        makeError('malformed-request', `command ${index} must be an object, but it is ${describeValue(raw)}`, {
          commandIndex: index,
        }),
      );
      continue;
    }

    const name = raw['name'];
    if (typeof name !== 'string') {
      errors.push(
        makeError('malformed-request', `command ${index} must carry a string name, but it carries ${describeValue(name)}`, {
          commandIndex: index,
        }),
      );
      continue;
    }

    const spec = getCommandSpec(name);
    if (spec === undefined) {
      errors.push(
        makeError('unknown-command', `there is no command named "${name}"`, {
          commandIndex: index,
          command: name,
        }),
      );
      continue;
    }

    const args = raw['args'];
    if (!Array.isArray(args)) {
      errors.push(
        makeError('malformed-request', `command ${index} ("${name}") must carry an array of arguments, but it carries ${describeValue(args)}`, {
          commandIndex: index,
          command: name,
        }),
      );
      continue;
    }

    const map = raw['map'];
    if (typeof map !== 'number' || !Number.isInteger(map) || map < 0) {
      errors.push(
        makeError('invalid-argument', `command ${index} ("${name}") must carry a non-negative integer map id, but it carries ${describeValue(map)}`, {
          commandIndex: index,
          command: name,
          argumentIndex: 0,
          expected: 'a non-negative integer',
        }),
      );
    }

    if (spec.forbidden === true) {
      errors.push(
        makeError('forbidden-command', `the command "${name}" is not available on this server`, {
          commandIndex: index,
          command: name,
        }),
      );
      continue;
    }
    if (spec.adminOnly === true && role !== 'admin') {
      errors.push(
        makeError('forbidden-command', `the command "${name}" is an administrative command`, {
          commandIndex: index,
          command: name,
        }),
      );
      continue;
    }
    if (!spec.shapeKnown) {
      errors.push(
        makeError(
          'unspecified-command',
          `the command "${name}" has no specified argument shape and cannot be accepted`,
          { commandIndex: index, command: name },
        ),
      );
      continue;
    }

    const least = minArgs(spec);
    const most = maxArgs(spec);
    if (args.length < least || args.length > most) {
      errors.push(
        makeError(
          'invalid-argument-count',
          `command ${index} ("${name}") takes ${least === most ? least : `${least} to ${most}`} arguments, but ${args.length} were given`,
          {
            commandIndex: index,
            command: name,
            expected: `${least}..${most} arguments`,
          },
        ),
      );
      continue;
    }

    for (let argumentIndex = 0; argumentIndex < args.length; argumentIndex += 1) {
      const arg = spec.args[argumentIndex];
      if (arg === undefined) continue;
      const value = args[argumentIndex];
      const expected = checkArgument(arg, value);
      if (expected !== null) {
        errors.push(
          makeError(
            'invalid-argument',
            `argument ${argumentIndex} of command ${index} ("${name}", ${arg.name}) must be ${expected}, but it is ${describeValue(value)}`,
            {
              commandIndex: index,
              command: name,
              argumentIndex,
              expected,
            },
          ),
        );
      }
    }

    commands.push({
      map: typeof map === 'number' && Number.isInteger(map) && map >= 0 ? map : 0,
      name: spec.name,
      args: [...args],
    });
  }

  if (errors.length > 0) {
    return { ok: false, errors, request: null };
  }

  return {
    ok: true,
    errors,
    request: {
      v: version,
      id: id as string,
      token: token as string,
      commands,
    },
  };
}

/**
 * Parse a request body and validate it.
 *
 * A body that is not JSON is a malformed request, not an exception.
 */
export function parseRequestBody(
  body: string,
  options: ValidationOptions = {},
): ValidationResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return {
      ok: false,
      errors: [makeError('malformed-request', 'the request body is not valid JSON')],
      request: null,
    };
  }
  return validateRequest(parsed, options);
}

/* -------------------------------------------------------------------------
 * Building a response
 * ---------------------------------------------------------------------- */

/** A response that reports a successful batch. */
export function successResponse(
  id: string,
  outcomes: readonly CommandOutcome[],
): NativeResponse {
  return {
    v: PROTOCOL_VERSION,
    id,
    ok: outcomes.every((outcome) => outcome.ok),
    outcomes,
    errors: [],
  };
}

/** A response that reports a failed batch. */
export function failureResponse(
  id: string,
  errors: readonly CommandError[],
  outcomes: readonly CommandOutcome[] = [],
): NativeResponse {
  return {
    v: PROTOCOL_VERSION,
    id,
    ok: false,
    outcomes,
    errors: [...errors],
  };
}

/**
 * The HTTP status a response should be sent with.
 *
 * It is the status of the worst error in the response, and it is never a
 * 5xx: the protocol's own errors are all 4xx, and a server-side failure
 * that is not the client's fault is the server's to log, not to encode in
 * the client's answer.
 */
export function responseStatus(response: NativeResponse): number {
  let status = 200;
  for (const error of response.errors) {
    if (error.status > status) status = error.status;
  }
  for (const outcome of response.outcomes) {
    if (!outcome.ok && outcome.error.status > status) status = outcome.error.status;
  }
  return status;
}
