/**
 * The goal system — the "missions" panel.
 *
 * The goal system belongs to the client. `managers/GoalManager.as` registers
 * **134** goals in one long sequence (`managers/GoalManager.as:49-315`) and
 * `core/goals/` holds the 27 concrete goal classes that decide when each one
 * completes. The upstream Python server implements none of it — it only stores
 * the progress array the client pushes to it
 * (`upstream/socialwarriors/engine.py:96-100`) — so everything here is a
 * *specification to build*, not a description of existing behaviour
 * (`re/docs/13-goal-system.md` §10).
 *
 * The clone is **server-authoritative**: the counters live here, the client
 * reports what it did, and the server decides. The reward is granted by
 * {@link awardGoal}, exactly once per goal, and never because the client
 * asked for it (the legacy `complete_goal` command carries a resource
 * variation the client chose; `re/docs/13-goal-system.md` §10.4 says to
 * ignore it and grant your own).
 *
 * ## The two rules that shape everything
 *
 * * **At most five active goals.** `GoalManager.checkAllGoals()`
 *   (`managers/GoalManager.as:481-505`) walks the registration list in order
 *   and stops after `Base.Items.globals.NUM_ACTIVE_MISSIONS` incomplete goals
 *   — **5**, from `config/main.json`. The active set is therefore always *the
 *   first five incomplete goals in registration order*, and it slides forward
 *   as goals complete. A goal outside that window is not listening for
 *   anything: events do not touch it.
 * * **The reward is awarded once.** The client dispatches `complete` exactly
 *   once (`core/goals/AbstractGoal.as:48-58`) and queues `complete_goal`; the
 *   server grants the reward itself, once, and remembers that it did.
 *
 * ## The six client defects
 *
 * `re/docs/13-goal-system.md` §9 lists six defects in the shipped 1.5.4
 * client. Each one is decided here explicitly — a faithful-but-buggy goal is
 * a defensible choice, a silent divergence is not.
 *
 * | # | What the client does | What this module does |
 * | --- | --- | --- |
 * | 1 | `GoalAlliesMarketTrade` compares an `Object` with an `int` (`param1 < this.tradesLength`, `core/goals/GoalAlliesMarketTrade.as:62`). The comparison is always false, so `_currentStep` is always 1 and goal 84 ("OBTAIN WOOD IN THE ALLIES MARKET", `{"w":500}`) completes on the **first** Allies-Market collection instead of after 500 wood. | **Fixed** by default: the goal needs the requested amount, which is also what the sibling `GoalMarketTrade` does (`core/goals/GoalMarketTrade.as:62`). Set `alliesMarketTradeCompletesOnFirstCollect` in the policy to reproduce the client. |
 * | 2 | `GoalStoreItem.deactivate()` calls `Base.Iso.itemStored.add(...)` instead of `.remove(...)` (`core/goals/GoalStoreItem.as:46`), so the listener is never detached and a duplicate is registered on every deactivation. | **Not reproduced.** It is a listener leak with no observable effect on a counter, and this module has no listeners to leak. |
 * | 3 | `GoalModifyPlayerStats` runs `this.stats[key] -= delta` after the key was deleted (`core/goals/GoalModifyPlayerStats.as:56`), re-creating it with the value `NaN`. | **Not reproduced.** The bookkeeping here is a clean monotone accumulator. The observable behaviour (goal 45 completes when the player spends 1 cash) is unchanged. |
 * | 4 | `GoalManager.parseReward` overwrites the reward variable inside the loop over the reward object's keys (`managers/GoalManager.as:444-464`), so an object reward with more than one key produces only one `RewardResource`. | **Not reproduced.** Every goal's reward comes from the definition table, which has exactly one reward per goal. |
 * | 5 | The goal texts of ids 130/138/145/150 name chapters 9/10/11/12 while the goals are bound to the chapter **keys** 5/6/7/8 (`managers/GoalManager.as:275`, `:291`, `:309`, `:313`). The texts for the real chapters 5–8 live under the six never-registered text ids 98/105/114/122/128/140. | **The code wins.** The goals stay bound to chapters 5/6/7/8, exactly as the client does. The titles are the client's own strings, so the mismatch is a text bug in the client and is reproduced verbatim rather than silently re-bound to a different chapter. |
 * | 6 | `GoalHarbor.onQuestEnd` completes the goal for **any** quest (`core/goals/GoalHarbor.as:76-81`), so "THE BAZOOKA KILLER (MISSION 1)" completes when any quest ends. | **Fixed** by default: the goal completes when the quest it is bound to (`QUEST_01_BAZOOKA`, the quest at play index 1) ends. Set `harborCompletesOnAnyQuest` in the policy to reproduce the client. |
 *
 * ## Two corrections to the written specification
 *
 * 1. `re/docs/13-goal-system.md` §5.1 lists the goals that require
 *    `PlayerID == Constants.PLAYER_SELF` and omits `GoalSelectTime` — but
 *    `core/goals/GoalSelectTime.as:38` *does* check the owner. This module
 *    enforces it, because the client does.
 * 2. `re/data/goals.json` (the `GoalLiterals` note) and the same report claim
 *    that "every HINT literal in `TranslationGoals.as` is an empty string, so
 *    the 'hint' field of the goal UI is always blank". That is **false**:
 *    goals **30** and **149** have non-empty hints, and `re/data/goals.json`'s
 *    own `goals[]` array records both of them. The note contradicts the data
 *    next to it; the data is right.
 * 3. The titles are the client's own strings, verbatim — including goal 92's
 *    misspelling "RECRUIMENT PRIZE" in `core/goals/TranslationGoals.as`.
 *
 * ## What is deliberately *not* modelled
 *
 * * The four `store*` constructor arguments of `GoalBuildId`
 *   (`storeCategory`, `storeSubcategory`, `storePosition`, `eTrainBuilding`)
 *   are UI deep-link hints with no effect on completion
 *   (`core/goals/GoalBuildId.as:37-40`). They belong to the client, not here.
 * * The `host` portrait (`managers/GoalManager.as:48`), the `visited` popup
 *   choreography and the cut-scenes are presentation. `visited` is kept
 *   because it is persisted in the `set_goals` payload.
 * * `GoalContainer` is never instantiated by `GoalManager`; it is a composite
 *   goal that exists for the tutorial chain and is not a registerable goal.
 * * `GoalAddAllies` also opens the Facebook invite flow
 *   (`core/goals/GoalAddAllies.as:22`). That is a UI side effect; the server
 *   only cares that the goal completed.
 */

/* ------------------------------------------------------------------------- *
 * Constants
 * ------------------------------------------------------------------------- */

/**
 * How many goals are active at once.
 *
 * `Base.Items.globals.NUM_ACTIVE_MISSIONS` — 5 in the captured
 * `config/main.json`. `GoalManager.checkAllGoals()` stops after that many
 * incomplete goals (`managers/GoalManager.as:487`).
 */
export const NUM_ACTIVE_GOALS = 5;

/** `Constants.PLAYER_SELF` (`core/Constants.as:2070`). */
export const PLAYER_SELF = 1;

/** `Constants.GAME_MODE_NORMAL` (`core/Constants.as:1828`). */
export const GAME_MODE_NORMAL = 1;

/** `Constants.ACTION_ZOOM` (`core/Constants.as:1918`). */
export const ACTION_ZOOM = 0;

/** `Constants.ACTION_MULTISELECT` (`core/Constants.as:1920`). */
export const ACTION_MULTISELECT = 1;

/** `Constants.COST_GOLD` (`core/Constants.as:1730`). */
export const COST_GOLD = 'g';

/** `Constants.COST_CASH` (`core/Constants.as:1732`). */
export const COST_CASH = 'c';

/** `Constants.COST_WOOD` (`core/Constants.as:1734`). */
export const COST_WOOD = 'w';

/** `Constants.COST_OIL` (`core/Constants.as:1736`). */
export const COST_OIL = 'o';

/** `Constants.COST_STEEL` (`core/Constants.as:1738`). */
export const COST_STEEL = 's';

/** `Constants.COST_XP` (`core/Constants.as:1732`). */
export const COST_XP = 'x';

/** `Constants.COST_MANA` (`core/Constants.as:1748`). */
export const COST_MANA = 'm';

/** `Constants.COST_ENERGY` (`core/Constants.as:1752`). */
export const COST_ENERGY = 'e';

/** `PropertyManager.RESOURCE` (`core/isoengine/PropertyManager.as:34`). */
export const PROPERTY_RESOURCE = 'resource';

/** `PropertyManager.DEPOT` (`core/isoengine/PropertyManager.as:44`). */
export const PROPERTY_DEPOT = 'depot';

/** `PropertyManager.HQ` (`core/isoengine/PropertyManager.as:46`). */
export const PROPERTY_HQ = 'hq';

/** `PropertyManager.FARM` (`core/isoengine/PropertyManager.as:48`). */
export const PROPERTY_FARM = 'farm';

/** `PropertyManager.TOWER` (`core/isoengine/PropertyManager.as:58`). */
export const PROPERTY_TOWER = 'tower';

/** `PropertyManager.WALL` (`core/isoengine/PropertyManager.as:66`). */
export const PROPERTY_WALL = 'wall';

/** `PropertyManager.DECORATION` (`core/isoengine/PropertyManager.as:72`). */
export const PROPERTY_DECORATION = 'decoration';

/** `PropertyManager.BUNKER` (`core/isoengine/PropertyManager.as:74`). */
export const PROPERTY_BUNKER = 'bunker';

/** `PropertyManager.WORKER` (`core/isoengine/PropertyManager.as:98`). */
export const PROPERTY_WORKER = 'worker';

/** `PropertyManager.FIGHTING_TYPE_GROUND` (`core/isoengine/PropertyManager.as:24`). */
export const PROPERTY_FT_GROUND = 'ft_ground';

/**
 * `Quest.QUEST_01_BAZOOKA` (`quest/Quest.as:57`).
 *
 * It is the quest at play index 1 of `Quest.questIds`
 * (`quest/Quest.as:192`), which is the quest `GoalHarbor` is bound to
 * (`core/goals/GoalHarbor.as:28`).
 */
export const QUEST_01_BAZOOKA = '100000001';

/* ------------------------------------------------------------------------- *
 * Goal definitions
 * ------------------------------------------------------------------------- */

/**
 * The type-specific parameters of a goal.
 *
 * One member per registerable goal class. `GoalContainer` is absent on
 * purpose: it is never instantiated by `GoalManager`, so it is not a goal the
 * server can be asked to track.
 */
export type GoalParams =
  /** Counts `Base.Main.actionTriggered` events with this action id. */
  | { readonly type: 'GoalAction'; readonly action: number }
  /** Completes when the goal-info popup is closed. */
  | { readonly type: 'GoalAddAllies' }
  /** Per-resource amounts to collect from the Allies Market. */
  | { readonly type: 'GoalAlliesMarketTrade'; readonly trades: Readonly<Record<string, number>> }
  /** Counts assist events. */
  | { readonly type: 'GoalAssistNeighbourBuilding' }
  /** Counts qualifying assaults. */
  | {
      readonly type: 'GoalAttackPlayer';
      readonly numAttacks: number;
      readonly friends: boolean;
      readonly victoryNeeded: boolean;
    }
  /** Counts built elements whose item id is in the list. */
  | { readonly type: 'GoalBuildId'; readonly itemIds: readonly number[]; readonly updateOnActivate: boolean }
  /** Counts built elements carrying the property. */
  | { readonly type: 'GoalBuildProperty'; readonly property: string; readonly updateOnActivate: boolean }
  /** Counts collects on elements with the property and the given `collect_type`. */
  | { readonly type: 'GoalCollect'; readonly property: string; readonly resource: string }
  /** Completes when the given chapter finishes. */
  | { readonly type: 'GoalCompleteChapter'; readonly chapterId: number; readonly spawnChapter: boolean }
  /** Completes when the given quest ends. */
  | {
      readonly type: 'GoalCompleteQuest';
      readonly questId: string;
      readonly minDifficulty: number;
      readonly winRequired: boolean;
    }
  /** Counts daily-bonus claims. */
  | { readonly type: 'GoalDailyBouns'; readonly day: number }
  /** Counts double-clicks on the map. */
  | { readonly type: 'GoalDoubleClick' }
  /** Counts bought map tiles. */
  | { readonly type: 'GoalExpand' }
  /** Completes when a quest ends. */
  | { readonly type: 'GoalHarbor' }
  /** Per-resource amounts to trade on the own market. */
  | { readonly type: 'GoalMarketTrade'; readonly trades: Readonly<Record<string, number>> }
  /** Per-resource deltas the wallet has to undergo. */
  | { readonly type: 'GoalModifyPlayerStats'; readonly stats: Readonly<Record<string, number>> }
  /** Counts moved buildings carrying the property. */
  | { readonly type: 'GoalMove'; readonly buildingProperty: string }
  /** Completes when the named popup is opened. */
  | { readonly type: 'GoalOpenPopup'; readonly popup: string }
  /** Counts units removed from a matching building. */
  | {
      readonly type: 'GoalPopUnit';
      readonly buildingIds?: readonly number[];
      readonly buildingProperty?: string;
      readonly unitIds?: readonly number[];
      readonly unitProperty?: string;
    }
  /** Counts units placed into a matching building. */
  | {
      readonly type: 'GoalPushUnit';
      readonly buildingIds?: readonly number[];
      readonly buildingProperty?: string;
      readonly unitIds?: readonly number[];
      readonly unitProperty?: string;
    }
  /** The absolute population the player has to reach. */
  | { readonly type: 'GoalReachPopulation'; readonly population: number }
  /** Counts production-time selections on a matching depot. */
  | { readonly type: 'GoalSelectTime'; readonly buildingProperty: string; readonly resource: string; readonly timeIdx: number }
  /** Completes when the named social building is opened. */
  | { readonly type: 'GoalSocialBuildingOpened'; readonly buildingId: number }
  /** Counts completed spy operations. */
  | { readonly type: 'GoalSpy' }
  /** Counts stored items matching the property or the id list. */
  | { readonly type: 'GoalStoreItem'; readonly property?: string; readonly itemIds?: readonly number[] }
  /** Counts visits to the listed friends. */
  | { readonly type: 'GoalVisitNeighbour'; readonly friendIds: readonly number[] };

/** The name of a registerable goal class. */
export type GoalType = GoalParams['type'];

/** A reward, as a resource code and an amount. */
export interface GoalReward {
  /** The resource code (`Constants.COST_*`). */
  readonly resource: string;
  /** How much of it. */
  readonly amount: number;
}

/**
 * The reward every registered goal carries.
 *
 * All 134 goals are created with the reward argument `10`, which
 * `GoalManager.parseReward` turns into `RewardResource(Constants.COST_GOLD, 10)`
 * (`managers/GoalManager.as:49-315`, `:444-464`). The reward travels to the
 * server as a resource delta on the `complete_goal` command
 * (`commands/CmdCompleteGoal.as:15-22`).
 */
export const GOAL_REWARD: GoalReward = Object.freeze({ resource: COST_GOLD, amount: 10 });

/** One registered goal. */
export interface GoalDefinition {
  /** The goal id — the key into `TranslationGoals` and into the server's state. */
  readonly id: number;
  /** The client's `GoalLiterals.TITLE`. */
  readonly title: string;
  /** How many steps the goal requires (`AbstractGoal._steps`). */
  readonly steps: number;
  /** The type-specific parameters. */
  readonly params: GoalParams;
  /** What completing the goal pays. */
  readonly reward: GoalReward;
}

function def(id: number, title: string, steps: number, params: GoalParams): GoalDefinition {
  return { id, title, steps, params, reward: GOAL_REWARD };
}

/**
 * The 134 registered goals, in registration order.
 *
 * Registration order is the tutorial/progression order — it is the order
 * `GoalManager`'s constructor uses (`managers/GoalManager.as:49-315`) and the
 * order the five-goal window slides along. Every entry was checked against
 * the decompiled `GoalManager.as`; the machine-readable companion is
 * `re/data/goals.json`.
 */
export const GOALS: readonly GoalDefinition[] = [
  def(1, 'BUILD A HOUSE', 1, { type: 'GoalBuildId', itemIds: [1], updateOnActivate: false }),
  def(18, 'BUILD A WOOD FACTORY', 1, { type: 'GoalBuildId', itemIds: [2], updateOnActivate: false }),
  def(6, 'LET\'S ZOOM!', 8, { type: 'GoalAction', action: ACTION_ZOOM }),
  def(8, 'TRAIN 2 WORKERS', 2, { type: 'GoalBuildProperty', property: PROPERTY_WORKER, updateOnActivate: false }),
  def(20, 'SEND 1 WORKER TO WOOD FACTORY', 1, { type: 'GoalPushUnit', buildingIds: [2, 6, 10, 14], unitProperty: PROPERTY_WORKER }),
  def(11, 'SELECT WORKING TIME', 1, { type: 'GoalSelectTime', buildingProperty: PROPERTY_DEPOT, resource: COST_WOOD, timeIdx: 0 }),
  def(23, 'EXTRACT 3 GOLD', 3, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_GOLD }),
  def(9, 'BUILD A GOLD FACTORY', 1, { type: 'GoalBuildId', itemIds: [5], updateOnActivate: false }),
  def(10, 'SEND WORKER TO GOLD FACTORY', 1, { type: 'GoalPushUnit', buildingIds: [5, 9, 13, 17], unitProperty: PROPERTY_WORKER }),
  def(87, 'SELECT WORKING TIME', 1, { type: 'GoalSelectTime', buildingProperty: PROPERTY_DEPOT, resource: COST_GOLD, timeIdx: 0 }),
  def(24, 'BUILD BAZOOKA ACADEMY', 1, { type: 'GoalBuildId', itemIds: [31], updateOnActivate: false }),
  def(25, 'TRAIN 3 LIGHT BAZOOKA', 3, { type: 'GoalBuildId', itemIds: [1008], updateOnActivate: false }),
  def(16, 'DOUBLE CLICK', 1, { type: 'GoalDoubleClick' }),
  def(17, 'RESCUE YOUR COMRADES!', 1, { type: 'GoalCompleteChapter', chapterId: 1, spawnChapter: true }),
  def(19, 'TRAIN 2 MORE WORKERS', 2, { type: 'GoalBuildProperty', property: PROPERTY_WORKER, updateOnActivate: false }),
  def(5, 'CUT TREES AND GET WOOD', 1, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_WOOD }),
  def(41, 'BUILD A STEEL FACTORY', 1, { type: 'GoalBuildId', itemIds: [4], updateOnActivate: false }),
  def(43, 'ADD WORKER TO STEEL FACTORY', 1, { type: 'GoalPushUnit', buildingIds: [4, 8, 12, 16], unitProperty: PROPERTY_WORKER }),
  def(42, 'SELECT STEEL TO BUILD', 1, { type: 'GoalSelectTime', buildingProperty: PROPERTY_DEPOT, resource: COST_STEEL, timeIdx: 0 }),
  def(85, 'CALL YOUR ALLIES!', 1, { type: 'GoalAddAllies' }),
  // Goal 40 supplies a friend-id list *and* the "any one of them" flag, so its
  // step count is 1 rather than the length of the list
  // (core/goals/GoalVisitNeighbour.as:38).
  def(40, 'VISIT YOUR GENERAL!', 1, { type: 'GoalVisitNeighbour', friendIds: [100000030, 100000031] }),
  def(30, 'BUILD 2 TURRETS NEAR COMMAND CENTER', 2, { type: 'GoalBuildId', itemIds: [22], updateOnActivate: false }),
  def(31, 'BUILD A WALL', 1, { type: 'GoalBuildId', itemIds: [23], updateOnActivate: false }),
  def(32, 'MOVE A WALL', 1, { type: 'GoalMove', buildingProperty: PROPERTY_WALL }),
  def(3, 'BUILD A CORN FIELD', 1, { type: 'GoalBuildProperty', property: PROPERTY_FARM, updateOnActivate: false }),
  def(4, 'SEND WORKER TO FIELD', 1, { type: 'GoalPushUnit', buildingProperty: PROPERTY_FARM, unitProperty: PROPERTY_WORKER }),
  def(13, 'GET WORKER OUT OF GOLD FACTORY', 1, { type: 'GoalPopUnit', buildingIds: [5, 9, 13, 17], unitProperty: PROPERTY_WORKER }),
  def(14, 'EXTRACT 3 STEEL', 3, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_STEEL }),
  def(26, 'THE BAZOOKA KILLER (MISSION 1)', 1, { type: 'GoalHarbor' }),
  def(36, 'BUILD A BUNKER', 1, { type: 'GoalBuildId', itemIds: [50], updateOnActivate: false }),
  def(37, 'MOVE UNIT TO BUNKER', 1, { type: 'GoalPushUnit', buildingProperty: PROPERTY_BUNKER, unitProperty: PROPERTY_FT_GROUND }),
  def(29, 'COLLECT 10 OIL', 10, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_OIL }),
  def(22, 'BUILD 4 MORE HOUSES', 4, { type: 'GoalBuildId', itemIds: [1], updateOnActivate: false }),
  def(27, 'BUILD 3 DECORATIONS', 3, { type: 'GoalBuildProperty', property: PROPERTY_DECORATION, updateOnActivate: false }),
  def(28, 'CHOP DOWN 7 MORE TREES', 7, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_WOOD }),
  def(33, 'BUILD A JEEP GARAGE', 1, { type: 'GoalBuildId', itemIds: [40], updateOnActivate: false }),
  def(34, 'TRAIN 3 MACHINE GUN JEEPS', 3, { type: 'GoalBuildId', itemIds: [1014], updateOnActivate: false }),
  def(51, 'BUILD AN OIL FACTORY', 1, { type: 'GoalBuildId', itemIds: [3], updateOnActivate: false }),
  def(88, 'SEND WORKER TO OIL FACTORY', 1, { type: 'GoalPushUnit', buildingIds: [3, 7, 11, 15], unitProperty: PROPERTY_WORKER }),
  def(21, 'COLLECT GOLD FACTORY', 1, { type: 'GoalCollect', property: PROPERTY_DEPOT, resource: COST_GOLD }),
  def(39, 'MORE SHELTER!', 1, { type: 'GoalBuildId', itemIds: [1], updateOnActivate: false }),
  def(44, 'BUILD A MARKET', 1, { type: 'GoalBuildId', itemIds: [18], updateOnActivate: true }),
  def(55, 'BUY 200 STEEL ON MARKET', 1, { type: 'GoalMarketTrade', trades: { [COST_STEEL]: 200 } }),
  def(56, 'BUY 100 WOOD ON MARKET', 1, { type: 'GoalMarketTrade', trades: { [COST_WOOD]: 100 } }),
  def(54, 'COLLECT OIL FACTORY', 1, { type: 'GoalCollect', property: PROPERTY_DEPOT, resource: COST_OIL }),
  def(45, 'SPEND 1 CASH', 1, { type: 'GoalModifyPlayerStats', stats: { [COST_CASH]: -1 } }),
  def(74, 'RESCUE YOUR FRIEND!! (CHAPTER 2)', 1, { type: 'GoalCompleteChapter', chapterId: 2, spawnChapter: false }),
  def(69, 'BUILD 2 TURRET II', 2, { type: 'GoalBuildId', itemIds: [57], updateOnActivate: false }),
  def(46, 'BUILD A SILO', 1, { type: 'GoalBuildId', itemIds: [932], updateOnActivate: false }),
  def(47, 'CHECK COLLECTIONS', 1, { type: 'GoalOpenPopup', popup: 'PopupInventory' }),
  def(48, 'GET DAILY BONUS!', 3, { type: 'GoalDailyBouns', day: 3 }),
  def(49, 'REACH POPULATION 40', 40, { type: 'GoalReachPopulation', population: 40 }),
  def(50, 'HARVEST 10 GOLD VEINS', 10, { type: 'GoalCollect', property: PROPERTY_RESOURCE, resource: COST_GOLD }),
  def(110, 'CALL FOR AIR REINFORCEMENTS (MISSION 2)', 1, { type: 'GoalCompleteQuest', questId: '100000006', minDifficulty: 1, winRequired: true }),
  def(59, 'BUILD HOUSE II', 1, { type: 'GoalBuildId', itemIds: [47], updateOnActivate: false }),
  def(60, 'STORE A DECORATION', 1, { type: 'GoalStoreItem', property: PROPERTY_DECORATION }),
  def(53, 'COLLECT STEEL FACTORY', 1, { type: 'GoalCollect', property: PROPERTY_DEPOT, resource: COST_STEEL }),
  def(67, 'UPGRADE THE SOLDIER ACADEMY', 1, { type: 'GoalBuildId', itemIds: [41], updateOnActivate: false }),
  def(61, 'OPEN RECON CENTER', 1, { type: 'GoalBuildId', itemIds: [75], updateOnActivate: false }),
  def(152, 'RESCUE THE BAZOOKA SOLDIERS! (CHAPTER 3)', 1, { type: 'GoalCompleteChapter', chapterId: 3, spawnChapter: false }),
  def(62, 'SELL 100 WOOD ON MARKET', 1, { type: 'GoalMarketTrade', trades: { [COST_WOOD]: -100 } }),
  def(63, 'EXPAND 1 MORE ACRE', 1, { type: 'GoalExpand' }),
  def(52, 'ATTACK A PLAYER!', 1, { type: 'GoalAttackPlayer', numAttacks: 1, friends: false, victoryNeeded: false }),
  def(58, 'CHECK ATTACKS!', 1, { type: 'GoalOpenPopup', popup: 'PopupAssaultHistory' }),
  def(64, 'USE RECON CENTER', 1, { type: 'GoalSpy' }),
  def(89, 'TURRET III', 1, { type: 'GoalBuildId', itemIds: [49], updateOnActivate: false }),
  def(90, 'PROTECT THE ALLIED CONVOY! (MISSION 3)', 1, { type: 'GoalCompleteQuest', questId: '100000003', minDifficulty: 1, winRequired: true }),
  def(91, 'GRAPE FIELD', 1, { type: 'GoalBuildId', itemIds: [108], updateOnActivate: false }),
  def(92, 'RECRUIMENT PRIZE', 1, { type: 'GoalBuildId', itemIds: [140], updateOnActivate: false }),
  def(70, 'BUILD 20 WALL II', 20, { type: 'GoalBuildId', itemIds: [24], updateOnActivate: false }),
  def(93, 'HOSPITAL', 1, { type: 'GoalBuildId', itemIds: [28], updateOnActivate: false }),
  def(65, 'DEFEAT 3 PLAYERS!', 3, { type: 'GoalAttackPlayer', numAttacks: 3, friends: false, victoryNeeded: true }),
  def(72, 'UPGRADE THE BAZOOKA ACADEMY', 1, { type: 'GoalBuildId', itemIds: [43], updateOnActivate: false }),
  def(94, 'RETRIEVE OUR JEEPS (CHAPTER 4)', 1, { type: 'GoalCompleteChapter', chapterId: 4, spawnChapter: false }),
  def(73, 'TRAIN 5 BAZOOKA SOLDIERS', 5, { type: 'GoalBuildId', itemIds: [1022], updateOnActivate: false }),
  def(71, 'CALL FOR REINFORCEMENTS', 1, { type: 'GoalSocialBuildingOpened', buildingId: 61 }),
  def(95, 'UPGRADE YOUR WOOD FACTORY II', 1, { type: 'GoalBuildId', itemIds: [6], updateOnActivate: false }),
  def(80, 'BUILD 8 TURRETS', 8, { type: 'GoalBuildProperty', property: PROPERTY_TOWER, updateOnActivate: false }),
  def(96, 'DESTROY THE MEGATANK (MISSION 4)', 1, { type: 'GoalCompleteQuest', questId: '100000004', minDifficulty: 1, winRequired: true }),
  def(79, 'UPGRADE YOUR MARKET', 1, { type: 'GoalBuildId', itemIds: [90], updateOnActivate: false }),
  def(97, 'BUILD TANK ACADEMY I', 1, { type: 'GoalBuildId', itemIds: [38], updateOnActivate: false }),
  def(81, 'HELP A FRIEND!', 5, { type: 'GoalAssistNeighbourBuilding' }),
  def(86, 'BUILD AN ALLIES MARKET', 1, { type: 'GoalBuildId', itemIds: [74], updateOnActivate: false }),
  def(84, 'OBTAIN WOOD IN THE ALLIES MARKET', 1, { type: 'GoalAlliesMarketTrade', trades: { [COST_WOOD]: 500 } }),
  def(99, 'UPGRADE YOUR GOLD FACTORY', 1, { type: 'GoalBuildId', itemIds: [9], updateOnActivate: false }),
  def(57, 'DEFEAT A FRIEND!', 1, { type: 'GoalAttackPlayer', numAttacks: 1, friends: true, victoryNeeded: true }),
  def(100, 'BUILD BUNKER II', 1, { type: 'GoalBuildId', itemIds: [51], updateOnActivate: false }),
  def(82, 'UPGRADE THE CC', 1, { type: 'GoalBuildId', itemIds: [58], updateOnActivate: false }),
  def(101, 'DESTROY THE TRUCK (MISSION 5)', 1, { type: 'GoalCompleteQuest', questId: '100000005', minDifficulty: 1, winRequired: true }),
  def(102, 'COW FARM', 1, { type: 'GoalBuildId', itemIds: [110], updateOnActivate: false }),
  def(103, 'JEEP GARAGE II', 1, { type: 'GoalBuildId', itemIds: [64], updateOnActivate: false }),
  def(104, 'UPGRADE YOUR STEEL FACTORY', 1, { type: 'GoalBuildId', itemIds: [8], updateOnActivate: false }),
  def(106, 'UPGRADE THE OIL FACTORY II', 1, { type: 'GoalBuildId', itemIds: [7], updateOnActivate: false }),
  def(107, 'UPGRADE TO WALL III', 20, { type: 'GoalBuildId', itemIds: [25], updateOnActivate: false }),
  def(108, 'HELICOPTER HANGAR I', 1, { type: 'GoalBuildId', itemIds: [54], updateOnActivate: false }),
  def(109, 'HOUSE III', 1, { type: 'GoalBuildId', itemIds: [48], updateOnActivate: false }),
  def(66, 'BLOW UP THE NUCLEAR PLANT! (MISSION 6)', 1, { type: 'GoalCompleteQuest', questId: '100000002', minDifficulty: 1, winRequired: true }),
  def(111, 'BUNKER III', 1, { type: 'GoalBuildId', itemIds: [52], updateOnActivate: false }),
  def(112, 'FORTRESS I', 1, { type: 'GoalBuildId', itemIds: [80], updateOnActivate: false }),
  def(113, 'Mechanical Garage', 1, { type: 'GoalBuildId', itemIds: [135], updateOnActivate: false }),
  def(115, 'UPGRADE THE SOLDIER ACADEMY', 1, { type: 'GoalBuildId', itemIds: [42], updateOnActivate: false }),
  def(116, 'UPGRADE YOUR WOOD FACTORY', 1, { type: 'GoalBuildId', itemIds: [10], updateOnActivate: false }),
  def(117, 'UPGRADE THE BAZOOKA ACADEMY', 1, { type: 'GoalBuildId', itemIds: [44], updateOnActivate: false }),
  def(118, 'STEAL THE SHIP! (MISSION 7)', 1, { type: 'GoalCompleteQuest', questId: '100000007', minDifficulty: 1, winRequired: true }),
  def(119, 'UPGRADE YOUR GOLD FACTORY', 1, { type: 'GoalBuildId', itemIds: [13], updateOnActivate: false }),
  def(120, 'UPGRADE YOUR WALLS', 20, { type: 'GoalBuildId', itemIds: [78], updateOnActivate: false }),
  def(121, 'Hangar I', 1, { type: 'GoalBuildId', itemIds: [37], updateOnActivate: false }),
  def(123, 'UPGRADE THE MARKET', 1, { type: 'GoalBuildId', itemIds: [91], updateOnActivate: false }),
  def(124, 'UPGRADE YOUR CC III', 1, { type: 'GoalBuildId', itemIds: [59], updateOnActivate: false }),
  def(125, 'UPGRADE THE STEEL FACTORY', 1, { type: 'GoalBuildId', itemIds: [12], updateOnActivate: false }),
  def(126, 'STOP THE ROCKET LAUNCHING! (MISSION 8)', 1, { type: 'GoalCompleteQuest', questId: '100000008', minDifficulty: 1, winRequired: true }),
  def(127, 'UPGRADE YOUR TANK ACADEMY I', 1, { type: 'GoalBuildId', itemIds: [62], updateOnActivate: false }),
  def(129, 'UPGRADE YOUR HELICOPTER HANGAR', 1, { type: 'GoalBuildId', itemIds: [55], updateOnActivate: false }),
  def(130, 'DEFEND FROM ASSAULT! (CHAPTER 9)', 1, { type: 'GoalCompleteChapter', chapterId: 5, spawnChapter: false }),
  def(131, 'UPGRADE THE OIL FACTORY', 1, { type: 'GoalBuildId', itemIds: [11], updateOnActivate: false }),
  def(132, 'TURRET IV', 1, { type: 'GoalBuildId', itemIds: [39], updateOnActivate: false }),
  def(133, 'Jeep garage III', 1, { type: 'GoalBuildId', itemIds: [65], updateOnActivate: false }),
  def(134, 'DESTROY THE LABS (MISSION 9)', 1, { type: 'GoalCompleteQuest', questId: '100000009', minDifficulty: 1, winRequired: true }),
  def(135, 'UPGRADE YOUR WALLS', 20, { type: 'GoalBuildId', itemIds: [79], updateOnActivate: false }),
  def(136, 'UPGRADE YOUR HANGAR', 1, { type: 'GoalBuildId', itemIds: [76], updateOnActivate: false }),
  def(137, 'UPGRADE YOUR WOOD FACTORY', 1, { type: 'GoalBuildId', itemIds: [14], updateOnActivate: false }),
  def(138, 'DESTROY THE MEGATANK (CHAPTER 10)', 1, { type: 'GoalCompleteChapter', chapterId: 6, spawnChapter: false }),
  def(139, 'UPGRADE THE COMMAND CENTER IV', 1, { type: 'GoalBuildId', itemIds: [60], updateOnActivate: false }),
  def(141, 'UPGRADE YOUR TANK ACADEMY', 1, { type: 'GoalBuildId', itemIds: [63], updateOnActivate: false }),
  def(142, 'STEAL THE LAPTOP (MISSION 10)', 1, { type: 'GoalCompleteQuest', questId: '100000010', minDifficulty: 1, winRequired: true }),
  def(143, 'UPGRADE YOUR GOLD FACTORY', 1, { type: 'GoalBuildId', itemIds: [17], updateOnActivate: false }),
  def(144, 'UPGRADE YOUR HELICOPTER HANGAR', 1, { type: 'GoalBuildId', itemIds: [56], updateOnActivate: false }),
  def(145, 'ELEPHANTS COMING! (CHAPTER 11)', 1, { type: 'GoalCompleteChapter', chapterId: 7, spawnChapter: false }),
  def(146, 'UPGRADE YOUR STEEL FACTORY', 1, { type: 'GoalBuildId', itemIds: [16], updateOnActivate: false }),
  def(147, 'UPGRADE THE HANGAR', 1, { type: 'GoalBuildId', itemIds: [77], updateOnActivate: false }),
  def(148, 'UPGRADE THE OIL FACTORY IV', 1, { type: 'GoalBuildId', itemIds: [15], updateOnActivate: false }),
  def(149, 'RESCUE YOUR CITIZEN (MISSION 11)', 1, { type: 'GoalCompleteQuest', questId: '100000011', minDifficulty: 1, winRequired: true }),
  def(150, 'T-REX ASSAULT! (CHAPTER 12)', 1, { type: 'GoalCompleteChapter', chapterId: 8, spawnChapter: false }),
  def(151, 'THE KILLER ROBOT (MISSION 12)', 1, { type: 'GoalCompleteQuest', questId: '100000012', minDifficulty: 1, winRequired: true }),
];

/** Every registered goal id, in registration order. */
export const REGISTERED_GOAL_IDS: readonly number[] = GOALS.map((goal) => goal.id);

/** The registered goals, keyed by id. */
export const GOAL_BY_ID: ReadonlyMap<number, GoalDefinition> = new Map(GOALS.map((goal) => [goal.id, goal]));

/** The registered goal, or undefined if the id is not one of them. */
export function getGoalDefinition(goalId: number): GoalDefinition | undefined {
  return GOAL_BY_ID.get(goalId);
}

/** How many goals of each type are registered. */
export const GOAL_TYPE_COUNTS: Readonly<Record<GoalType, number>> = Object.freeze(
  GOALS.reduce(
    (counts, goal) => {
      const type = goal.params.type;
      counts[type] = (counts[type] ?? 0) + 1;
      return counts;
    },
    {} as Record<GoalType, number>,
  ),
);

/* ------------------------------------------------------------------------- *
 * Id reconciliation
 * ------------------------------------------------------------------------- */

/**
 * The 12 ids that exist only in `config/main.json`'s goal table.
 *
 * They are exactly the ids that are missing from both the client's goal
 * registrations and from `TranslationGoals` — the client simply never
 * implemented them (`re/docs/13-goal-system.md` §8).
 */
export const CONFIG_ONLY_GOAL_IDS: readonly number[] = [
  2, 7, 12, 15, 35, 38, 68, 75, 76, 77, 78, 83,
];

/**
 * The 55 ids that exist only in the client.
 *
 * The numeric overlap between the two sources is coincidental: the config's
 * goal table is not Social Wars content — it talks about villagers, trolls
 * and sheep ranches — while the same file's `items` array *is* Social Wars
 * content (`re/docs/13-goal-system.md` §8.1). The goal content therefore comes
 * from the client, and the id space is kept so the `set_goals` /
 * `complete_goal` wire format stays compatible with the original client.
 */
export const CLIENT_ONLY_GOAL_IDS: readonly number[] = [
  92, 93, 94, 95, 96, 97, 99, 100, 101, 102, 103, 104, 106, 107, 108, 109, 110, 111, 112, 113, 115, 116, 117, 118,
  119, 120, 121, 123, 124, 125, 126, 127, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 141, 142, 143, 144,
  145, 146, 147, 148, 149, 150, 151, 152,
];

/**
 * The 6 ids that have a text in `TranslationGoals` but no registration.
 *
 * 98, 105, 114, 122, 128 and 140. They carry the texts of the real chapters
 * 5–8, which the registered chapter goals do not use (defect 5 above).
 */
export const TRANSLATION_ONLY_GOAL_IDS: readonly number[] = [98, 105, 114, 122, 128, 140];

/* ------------------------------------------------------------------------- *
 * Runtime state
 * ------------------------------------------------------------------------- */

/**
 * The per-player goal state.
 *
 * The client keeps the same facts: `_currentStep`, `_visited`, `_active` and
 * `_rewards` (`core/goals/AbstractGoal.as:17-37`). `completed` and `awarded`
 * are additions the server needs — the client can tell "the goal is done"
 * from "the reward was paid" only because it never re-dispatches `complete`.
 */
export interface GoalRuntimeState {
  /** `_currentStep` per goal id. */
  readonly progress: Readonly<Record<number, number>>;
  /** `_visited` per goal id — whether the goal's info popup was opened. */
  readonly visited: Readonly<Record<number, boolean>>;
  /** Whether the goal is complete. */
  readonly completed: Readonly<Record<number, boolean>>;
  /** Whether the goal's reward has been paid. */
  readonly awarded: Readonly<Record<number, boolean>>;
  /** `_active` per goal id — whether the goal has been activated (and swept). */
  readonly active: Readonly<Record<number, boolean>>;
  /**
   * The accumulated signed volume per goal id and resource.
   *
   * Only the three volume goals use it: `GoalMarketTrade`,
   * `GoalAlliesMarketTrade` and `GoalModifyPlayerStats`. The client keeps the
   * same thing by *mutating* its target object (`core/goals/GoalMarketTrade.as:56`);
   * that mutation is not persisted by the client, but a server has to keep it,
   * or a goal that needs 500 wood would restart from 500 every session.
   */
  readonly volumes: Readonly<Record<number, Readonly<Record<string, number>>>>;
}

/** A fresh, empty goal state. */
export function createGoalState(): GoalRuntimeState {
  return { progress: {}, visited: {}, completed: {}, awarded: {}, active: {}, volumes: {} };
}

/** The progress counter of a goal. */
export function goalProgress(state: GoalRuntimeState, goalId: number): number {
  return state.progress[goalId] ?? 0;
}

/** Is the goal complete? `AbstractGoal.isCompleted()` is `currentStep >= numSteps`. */
export function isGoalComplete(state: GoalRuntimeState, goalId: number): boolean {
  if (state.completed[goalId] === true) return true;
  const definition = getGoalDefinition(goalId);
  if (!definition) return false;
  return goalProgress(state, goalId) >= definition.steps;
}

/**
 * The `set_goals` payload for a goal.
 *
 * `AbstractGoal.save()` queues `new CmdSetGoals(id, [visited ? 1 : 0, currentStep])`
 * (`core/goals/AbstractGoal.as:237-240`, `commands/CmdSetGoals.as:8-12`).
 */
export function goalProgressEntry(state: GoalRuntimeState, goalId: number): readonly [number, number] {
  return [state.visited[goalId] === true ? 1 : 0, goalProgress(state, goalId)];
}

/** Mark the goal's info popup as opened (`PopupGoals.launchGoal`). */
export function markVisited(state: GoalRuntimeState, goalId: number): GoalRuntimeState {
  return { ...state, visited: { ...state.visited, [goalId]: true } };
}

/* ------------------------------------------------------------------------- *
 * Events
 * ------------------------------------------------------------------------- */

/**
 * Something that happened in the player's world.
 *
 * One variant per client signal the goals listen to. The names follow the
 * signals; the payload carries only what the matching goal class looks at.
 */
export type GoalEvent =
  /** `Base.Main.actionTriggered` (`core/Base.as:2411`). */
  | { readonly type: 'actionTriggered'; readonly action: number }
  /** The goal-information popup was closed (`AbstractGoal.onPopupclosed`). */
  | { readonly type: 'goalPopupClosed' }
  /** `Base.Iso.alliesMarketTrade` (`core/isoengine/IsoBuilding.as:1135`). */
  | { readonly type: 'alliesMarketTrade'; readonly volumes: Readonly<Record<string, number>> }
  /** `Base.Iso.neighbourBuildingAssisted` (`core/isoengine/IsoInteractiveElement.as:818`). */
  | { readonly type: 'neighbourBuildingAssisted' }
  /** `Assault.attackEnd` (`battle/Assault.as:430-436`). */
  | {
      readonly type: 'attackEnd';
      readonly win: boolean;
      readonly opponentId: string;
      readonly voluntary: boolean;
    }
  /** `Base.Iso.elementBuilt` (`core/isoengine/IsoEngine.as:571-579`). */
  | { readonly type: 'elementBuilt'; readonly itemId: number; readonly playerId: number }
  /** `Base.Iso.elemCollected` (`core/isoengine/IsoEngine.as:566`). */
  | { readonly type: 'elemCollected'; readonly itemId: number; readonly collectType: string }
  /** `ChapterManager.chapterFinished` (`chapters/ChapterManager.as:509`). */
  | { readonly type: 'chapterFinished'; readonly chapterId: number }
  /** `Quest.questEnd` (`quest/Quest.as:437`). */
  | { readonly type: 'questEnd'; readonly questId: string; readonly win: boolean; readonly difficulty: number }
  /** `Base.Iso.dailyBounsWon`. */
  | { readonly type: 'dailyBonusWon' }
  /** `Base.Iso.doubleClick` (`core/isoengine/IsoInteractiveElement.as:733`). */
  | { readonly type: 'doubleClick' }
  /** `Base.Iso.tilePurchased` (`core/isoengine/IsoTerrain.as:563`). */
  | { readonly type: 'tilePurchased' }
  /** `Base.Iso.marketTrade` (`popups/PopupMarket.as:101`). */
  | { readonly type: 'marketTrade'; readonly volumes: Readonly<Record<string, number>> }
  /** `Base.Resources.playerStatsModified` (`managers/ResourceManager.as:175`). */
  | { readonly type: 'playerStatsModified'; readonly volumes: Readonly<Record<string, number>> }
  /** `Base.Iso.buildingMoved` (`core/Base.as:3980`). */
  | { readonly type: 'buildingMoved'; readonly itemId: number; readonly playerId: number }
  /** `Base.PopUp.popupOpened`. */
  | { readonly type: 'popupOpened'; readonly popup: string }
  /** `Base.Iso.unitPopped` (`core/isoengine/IsoEngine.as:551`). */
  | {
      readonly type: 'unitPopped';
      readonly buildingItemId: number;
      readonly buildingPlayerId: number;
      readonly unitItemId: number;
      readonly unitPlayerId: number;
    }
  /** `Base.Iso.unitPushed` (`core/isoengine/IsoEngine.as:556`). */
  | {
      readonly type: 'unitPushed';
      readonly buildingItemId: number;
      readonly buildingPlayerId: number;
      readonly unitItemId: number;
      readonly unitPlayerId: number;
    }
  /** `Base.Player.populationModified`. */
  | { readonly type: 'populationModified'; readonly population: number; readonly gameMode: number }
  /**
   * `Base.Iso.timeSelected` (`core/isoengine/IsoEngine.as:561`).
   *
   * `collectPeriod` is the production-slot index the client reads from
   * `building.loaded.attrs.cp`. The report marks everything beyond "production
   * slot index" as UNVERIFIED, so the comparison is the only thing modelled.
   */
  | {
      readonly type: 'timeSelected';
      readonly itemId: number;
      readonly playerId: number;
      readonly collectType: string;
      readonly collectPeriod: number;
    }
  /** `Base.Iso.socialBuildingOpened`. */
  | { readonly type: 'socialBuildingOpened'; readonly itemId: number }
  /** `Assault.spyEnd` (`battle/Assault.as:667`). */
  | { readonly type: 'spyEnd'; readonly voluntary?: boolean }
  /** `Base.Iso.itemStored` (`core/Base.as:4982`). */
  | { readonly type: 'itemStored'; readonly itemId: number }
  /** `Base.Iso.neighbourVisited` (`core/Base.as:6887`). */
  | { readonly type: 'neighbourVisited'; readonly friendId: string };

/* ------------------------------------------------------------------------- *
 * The world and the policy
 * ------------------------------------------------------------------------- */

/**
 * What the server knows about the player's world that the event does not carry.
 *
 * The client reads all of this from `Base.Items.items` and `Base.Properties`
 * (`core/isoengine/PropertyManager.as`).
 */
export interface GoalWorld {
  /** The property keys each item carries. */
  readonly itemProperties?: ReadonlyMap<number, readonly string[]>;
  /** `building_limit_same_id` per item id — only a value above 0 matters. */
  readonly buildingLimitSameId?: ReadonlyMap<number, number>;
  /**
   * The item ids of the buildings already on the player's map.
   *
   * The client's activation sweep walks `Base.Main.buildingArray`, which holds
   * buildings — not trained units — so units are not swept either.
   */
  readonly playerBuildings?: readonly number[];
  /** The quests the player has already finished. */
  readonly completedQuests?: ReadonlySet<string>;
  /** `Base.Main.currentQuestId` — the chapter the player is on. */
  readonly currentQuestId?: number;
  /** The player's current population. */
  readonly population?: number;
  /** The player's friend ids (the `fbid` the client compares against). */
  readonly friendIds?: readonly string[];
}

/**
 * How the two observable client defects are treated.
 *
 * The default fixes them; flipping a flag reproduces the shipped client.
 */
export interface GoalPolicy {
  /**
   * Defect 1: `GoalAlliesMarketTrade` completes on the first collection.
   *
   * `true` reproduces `core/goals/GoalAlliesMarketTrade.as:62`.
   */
  readonly alliesMarketTradeCompletesOnFirstCollect: boolean;
  /**
   * Defect 6: `GoalHarbor` completes when *any* quest ends.
   *
   * `true` reproduces `core/goals/GoalHarbor.as:76-81`.
   */
  readonly harborCompletesOnAnyQuest: boolean;
}

/** The default policy: the two observable defects are fixed. */
export const DEFAULT_GOAL_POLICY: GoalPolicy = Object.freeze({
  alliesMarketTradeCompletesOnFirstCollect: false,
  harborCompletesOnAnyQuest: false,
});

/* ------------------------------------------------------------------------- *
 * The engine
 * ------------------------------------------------------------------------- */

/** A goal that has just been completed. */
export interface GoalCompletion {
  /** The goal id. */
  readonly goalId: number;
  /** The goal's title, for the completion popup. */
  readonly title: string;
  /** What the goal pays. */
  readonly reward: GoalReward;
}

/** The result of a state transition. */
export interface GoalTransition {
  /** The new state. */
  readonly state: GoalRuntimeState;
  /** The goals that completed, in the order they completed. */
  readonly completions: readonly GoalCompletion[];
}

/**
 * The goals that are currently active: the first `limit` incomplete goals in
 * registration order.
 *
 * `GoalManager.checkAllGoals()` walks the list and stops after
 * `NUM_ACTIVE_MISSIONS` incomplete goals (`managers/GoalManager.as:481-505`).
 */
export function activeGoalIds(state: GoalRuntimeState, limit = NUM_ACTIVE_GOALS): readonly number[] {
  const ids: number[] = [];
  for (const definition of GOALS) {
    if (ids.length >= limit) break;
    if (!isGoalComplete(state, definition.id)) ids.push(definition.id);
  }
  return ids;
}

function withProgress(state: GoalRuntimeState, goalId: number, value: number): GoalRuntimeState {
  return { ...state, progress: { ...state.progress, [goalId]: value } };
}

function withActive(state: GoalRuntimeState, goalId: number, value: boolean): GoalRuntimeState {
  return { ...state, active: { ...state.active, [goalId]: value } };
}

/** A completed goal is deactivated (`AbstractGoal.checkComplete`). */
function withCompleted(state: GoalRuntimeState, goalId: number): GoalRuntimeState {
  return {
    ...state,
    completed: { ...state.completed, [goalId]: true },
    active: { ...state.active, [goalId]: false },
  };
}

function withVolumes(
  state: GoalRuntimeState,
  goalId: number,
  volumes: Readonly<Record<string, number>>,
): GoalRuntimeState {
  return { ...state, volumes: { ...state.volumes, [goalId]: volumes } };
}

function hasProperty(world: GoalWorld, itemId: number, property: string): boolean {
  const properties = world.itemProperties?.get(itemId);
  if (!properties) return false;
  return properties.includes(property);
}

/**
 * Does the goal re-scan the buildings already on the map when it activates?
 *
 * The client does so when the flag is set, *or* when any of the target items
 * is a depot, an HQ, or has a per-id building limit
 * (`core/goals/GoalBuildId.as:48-55`).
 */
function sweepsOnActivate(definition: GoalDefinition, world: GoalWorld): boolean {
  const params = definition.params;
  if (params.type !== 'GoalBuildId') return false;
  if (params.updateOnActivate) return true;
  return params.itemIds.some(
    (itemId) =>
      hasProperty(world, itemId, PROPERTY_DEPOT) ||
      hasProperty(world, itemId, PROPERTY_HQ) ||
      (world.buildingLimitSameId?.get(itemId) ?? 0) > 0,
  );
}

/**
 * The effect of activating a goal, once.
 *
 * Everything here happens in the client's `activate()` override, i.e. exactly
 * once per goal, when the goal enters the five-goal window.
 */
function activationEffect(
  definition: GoalDefinition,
  state: GoalRuntimeState,
  world: GoalWorld,
): { readonly currentStep: number } | null {
  const params = definition.params;
  switch (params.type) {
    case 'GoalBuildId': {
      if (!sweepsOnActivate(definition, world)) return null;
      const buildings = world.playerBuildings ?? [];
      const count = buildings.filter((itemId) => params.itemIds.includes(itemId)).length;
      return count > 0 ? { currentStep: goalProgress(state, definition.id) + count } : null;
    }
    case 'GoalBuildProperty': {
      if (!params.updateOnActivate) return null;
      const buildings = world.playerBuildings ?? [];
      const count = buildings.filter((itemId) => hasProperty(world, itemId, params.property)).length;
      return count > 0 ? { currentStep: goalProgress(state, definition.id) + count } : null;
    }
    case 'GoalCompleteChapter': {
      // `Base.Main.currentQuestId > chapterId` means the chapter is behind the
      // player (core/goals/GoalCompleteChapter.as:32-40).
      if (world.currentQuestId === undefined || world.currentQuestId <= params.chapterId) return null;
      return { currentStep: 1 };
    }
    case 'GoalCompleteQuest': {
      // `Base.Player.questsRank[Quest.questIds.indexOf(questId)] != undefined`
      // (core/goals/GoalCompleteQuest.as:28-38).
      if (!world.completedQuests?.has(params.questId)) return null;
      return { currentStep: 1 };
    }
    case 'GoalHarbor': {
      // `Base.Player.questsRank[1] != undefined` — index 1 of `Quest.questIds`
      // is QUEST_01_BAZOOKA (core/goals/GoalHarbor.as:28).
      if (!world.completedQuests?.has(QUEST_01_BAZOOKA)) return null;
      return { currentStep: 1 };
    }
    case 'GoalDailyBouns': {
      // The constructor seeds `_currentStep = 1` (core/goals/GoalDailyBouns.as:14),
      // but only if the server has no stored progress for the goal — the
      // client's `initialize()` overwrites the seed with the stored value.
      return { currentStep: state.progress[definition.id] ?? 1 };
    }
    case 'GoalReachPopulation': {
      // The constructor seeds `_currentStep = Base.Player.iPopulationCurrent`
      // (core/goals/GoalReachPopulation.as:15). The client seeds it when the
      // goal manager is built, which is before the map is loaded, so the seed
      // is usually stale; a server knows the real population and seeds it
      // here, at activation, instead.
      return { currentStep: state.progress[definition.id] ?? world.population ?? 0 };
    }
    default:
      return null;
  }
}

/**
 * Accumulate a signed volume against a target.
 *
 * The client mutates its target object in place and counts how many keys it
 * has satisfied (`core/goals/GoalMarketTrade.as:47-62`). Its sign test — the
 * delta and the *remaining* target must have the same sign — is reproduced
 * here by only accumulating deltas whose sign matches the target's, which is
 * equivalent because the remaining target never changes sign.
 */
function accumulateVolumes(
  state: GoalRuntimeState,
  goalId: number,
  target: Readonly<Record<string, number>>,
  delta: Readonly<Record<string, number>>,
): { readonly state: GoalRuntimeState; readonly accumulated: Readonly<Record<string, number>> } {
  const previous = state.volumes[goalId] ?? {};
  const accumulated: Record<string, number> = { ...previous };
  for (const [resource, rawAmount] of Object.entries(delta)) {
    const wanted = target[resource];
    // A resource the goal does not ask for: the client reads `int(undefined)`
    // as NaN and its sign test then fails, so the delta is ignored.
    if (wanted === undefined) continue;
    const amount = Math.trunc(rawAmount);
    if (amount === 0) continue;
    if (Math.sign(amount) !== Math.sign(wanted)) continue;
    accumulated[resource] = (accumulated[resource] ?? 0) + amount;
  }
  return { state: withVolumes(state, goalId, accumulated), accumulated };
}

/** Has every requested amount been traded / spent? */
function allVolumesSatisfied(
  target: Readonly<Record<string, number>>,
  accumulated: Readonly<Record<string, number>>,
): boolean {
  const resources = Object.keys(target);
  // An empty target is satisfied at once: the client's `tradesAlreadyMade
  // (0) < tradesLength (0)` is false, so it sets `_currentStep = 1`.
  if (resources.length === 0) return true;
  return resources.every((resource) => {
    const wanted = target[resource] ?? 0;
    const got = accumulated[resource] ?? 0;
    return Math.abs(got) >= Math.abs(wanted);
  });
}

/** Does the unit or building match the goal's filter? */
function matchesTarget(
  world: GoalWorld,
  itemId: number,
  playerId: number,
  ids: readonly number[] | undefined,
  property: string | undefined,
): boolean {
  if (playerId !== PLAYER_SELF) return false;
  if (ids !== undefined) return ids.includes(itemId);
  if (property !== undefined) return hasProperty(world, itemId, property);
  return false;
}

/**
 * The effect of an event on one goal.
 *
 * Returns `null` when the event does not concern the goal. Otherwise it
 * returns the goal's new progress counter, and — for the volume goals — the
 * state with the accumulated volume.
 */
function evaluateEvent(
  definition: GoalDefinition,
  state: GoalRuntimeState,
  event: GoalEvent,
  world: GoalWorld,
  policy: GoalPolicy,
): { readonly state: GoalRuntimeState; readonly currentStep: number } | null {
  const params = definition.params;
  const step = goalProgress(state, definition.id);
  const increment = { state, currentStep: step + 1 };

  switch (params.type) {
    case 'GoalAction': {
      if (event.type !== 'actionTriggered') return null;
      if (event.action !== params.action) return null;
      return increment;
    }
    case 'GoalAddAllies': {
      if (event.type !== 'goalPopupClosed') return null;
      return { state, currentStep: 1 };
    }
    case 'GoalAlliesMarketTrade': {
      if (event.type !== 'alliesMarketTrade') return null;
      // Defect 1: the client sets `_currentStep = 1` on every collection,
      // whatever the amount (core/goals/GoalAlliesMarketTrade.as:62).
      if (policy.alliesMarketTradeCompletesOnFirstCollect) return { state, currentStep: 1 };
      const outcome = accumulateVolumes(state, definition.id, params.trades, event.volumes);
      const satisfied = allVolumesSatisfied(params.trades, outcome.accumulated);
      return { state: outcome.state, currentStep: satisfied ? 1 : step };
    }
    case 'GoalAssistNeighbourBuilding': {
      if (event.type !== 'neighbourBuildingAssisted') return null;
      return increment;
    }
    case 'GoalAttackPlayer': {
      if (event.type !== 'attackEnd') return null;
      // An assault the player aborted never counts
      // (core/goals/GoalAttackPlayer.as:38-41).
      if (event.voluntary) return null;
      if (params.victoryNeeded && !event.win) return null;
      if (params.friends && !(world.friendIds ?? []).includes(event.opponentId)) return null;
      return increment;
    }
    case 'GoalBuildId': {
      if (event.type !== 'elementBuilt') return null;
      if (event.playerId !== PLAYER_SELF) return null;
      if (!params.itemIds.includes(event.itemId)) return null;
      return increment;
    }
    case 'GoalBuildProperty': {
      if (event.type !== 'elementBuilt') return null;
      if (event.playerId !== PLAYER_SELF) return null;
      if (!hasProperty(world, event.itemId, params.property)) return null;
      return increment;
    }
    case 'GoalCollect': {
      if (event.type !== 'elemCollected') return null;
      // `GoalCollect` does *not* check the owner (core/goals/GoalCollect.as:38).
      if (!hasProperty(world, event.itemId, params.property)) return null;
      if (event.collectType !== params.resource) return null;
      return increment;
    }
    case 'GoalCompleteChapter': {
      if (event.type !== 'chapterFinished') return null;
      if (event.chapterId !== params.chapterId) return null;
      return { state, currentStep: 1 };
    }
    case 'GoalCompleteQuest': {
      if (event.type !== 'questEnd') return null;
      if (event.questId !== params.questId) return null;
      if (params.winRequired && !event.win) return null;
      if (event.difficulty < params.minDifficulty) return null;
      return { state, currentStep: 1 };
    }
    case 'GoalDailyBouns': {
      if (event.type !== 'dailyBonusWon') return null;
      return increment;
    }
    case 'GoalDoubleClick': {
      if (event.type !== 'doubleClick') return null;
      return increment;
    }
    case 'GoalExpand': {
      if (event.type !== 'tilePurchased') return null;
      return increment;
    }
    case 'GoalHarbor': {
      if (event.type !== 'questEnd') return null;
      // Defect 6: the client completes the goal for any quest
      // (core/goals/GoalHarbor.as:76-81).
      if (!policy.harborCompletesOnAnyQuest && event.questId !== QUEST_01_BAZOOKA) return null;
      return { state, currentStep: 1 };
    }
    case 'GoalMarketTrade': {
      if (event.type !== 'marketTrade') return null;
      const outcome = accumulateVolumes(state, definition.id, params.trades, event.volumes);
      const satisfied = allVolumesSatisfied(params.trades, outcome.accumulated);
      return { state: outcome.state, currentStep: satisfied ? 1 : step };
    }
    case 'GoalModifyPlayerStats': {
      if (event.type !== 'playerStatsModified') return null;
      const outcome = accumulateVolumes(state, definition.id, params.stats, event.volumes);
      const satisfied = allVolumesSatisfied(params.stats, outcome.accumulated);
      return { state: outcome.state, currentStep: satisfied ? 1 : step };
    }
    case 'GoalMove': {
      if (event.type !== 'buildingMoved') return null;
      if (event.playerId !== PLAYER_SELF) return null;
      if (!hasProperty(world, event.itemId, params.buildingProperty)) return null;
      return increment;
    }
    case 'GoalOpenPopup': {
      if (event.type !== 'popupOpened') return null;
      if (event.popup !== params.popup) return null;
      return { state, currentStep: 1 };
    }
    case 'GoalPopUnit': {
      if (event.type !== 'unitPopped') return null;
      if (
        !matchesTarget(world, event.buildingItemId, event.buildingPlayerId, params.buildingIds, params.buildingProperty)
      ) {
        return null;
      }
      if (!matchesTarget(world, event.unitItemId, event.unitPlayerId, params.unitIds, params.unitProperty)) return null;
      return increment;
    }
    case 'GoalPushUnit': {
      if (event.type !== 'unitPushed') return null;
      if (
        !matchesTarget(world, event.buildingItemId, event.buildingPlayerId, params.buildingIds, params.buildingProperty)
      ) {
        return null;
      }
      if (!matchesTarget(world, event.unitItemId, event.unitPlayerId, params.unitIds, params.unitProperty)) return null;
      return increment;
    }
    case 'GoalReachPopulation': {
      if (event.type !== 'populationModified') return null;
      // Only the normal game mode counts (core/goals/GoalReachPopulation.as:32).
      if (event.gameMode !== GAME_MODE_NORMAL) return null;
      // The metric is the *absolute* population, not a counter.
      return { state, currentStep: event.population };
    }
    case 'GoalSelectTime': {
      if (event.type !== 'timeSelected') return null;
      if (event.playerId !== PLAYER_SELF) return null;
      if (!hasProperty(world, event.itemId, params.buildingProperty)) return null;
      if (event.collectType !== params.resource) return null;
      if (event.collectPeriod < params.timeIdx) return null;
      return increment;
    }
    case 'GoalSocialBuildingOpened': {
      if (event.type !== 'socialBuildingOpened') return null;
      // The client does *not* check the owner (core/goals/GoalSocialBuildingOpened.as:36).
      if (event.itemId !== params.buildingId) return null;
      return { state, currentStep: 1 };
    }
    case 'GoalSpy': {
      if (event.type !== 'spyEnd') return null;
      // The spy payload is a player profile and has no `voluntary` field, so
      // in practice every spy end counts (core/goals/GoalSpy.as:31).
      if (event.voluntary === true) return null;
      return increment;
    }
    case 'GoalStoreItem': {
      if (event.type !== 'itemStored') return null;
      const matchesProperty = params.property !== undefined && hasProperty(world, event.itemId, params.property);
      const matchesIds = params.itemIds !== undefined && params.itemIds.includes(event.itemId);
      if (!matchesProperty && !matchesIds) return null;
      return increment;
    }
    case 'GoalVisitNeighbour': {
      if (event.type !== 'neighbourVisited') return null;
      if (params.friendIds.length > 0) {
        // The signal carries a String and the handler is typed `int`, so AS3
        // coerces it before the comparison (core/goals/GoalVisitNeighbour.as:50).
        const visited = Number(event.friendId);
        if (!params.friendIds.includes(visited)) return null;
      }
      return increment;
    }
    default:
      return null;
  }
}

function completionFor(definition: GoalDefinition): GoalCompletion {
  return { goalId: definition.id, title: definition.title, reward: definition.reward };
}

/**
 * One activation pass: activate the goals that are not active yet, sweep them,
 * and complete the ones that are already satisfied.
 */
function activateOnce(state: GoalRuntimeState, world: GoalWorld): GoalTransition {
  let current = state;
  const completions: GoalCompletion[] = [];
  for (const goalId of activeGoalIds(current)) {
    const definition = getGoalDefinition(goalId);
    if (!definition) continue;
    if (current.active[goalId] !== true) {
      current = withActive(current, goalId, true);
      const effect = activationEffect(definition, current, world);
      if (effect) current = withProgress(current, goalId, effect.currentStep);
    }
    if (isGoalComplete(current, goalId)) {
      current = withCompleted(current, goalId);
      completions.push(completionFor(definition));
    }
  }
  return { state: current, completions };
}

/**
 * Activate the goals, filling the five-goal window.
 *
 * `GoalManager.checkAllGoals()` (`managers/GoalManager.as:481-505`) activates
 * the goals that are not active yet, checks the ones that are already
 * satisfied, and completes them — which calls back into `checkAllGoals()`,
 * so the window keeps filling until it is stable. The client does that
 * recursively; here it is a loop until no goal completes any more.
 *
 * This is what a server runs when the player logs in.
 *
 * The policy is accepted for symmetry with {@link applyGoalEvent}; none of the
 * activation effects depends on it.
 */
export function activateGoals(
  state: GoalRuntimeState,
  world: GoalWorld,
  _policy: GoalPolicy = DEFAULT_GOAL_POLICY,
): GoalTransition {
  let current = state;
  const completions: GoalCompletion[] = [];
  // Every pass that completes a goal removes one goal from the incomplete
  // set, so this terminates; the bound is a safety net.
  for (let pass = 0; pass <= GOALS.length; pass++) {
    const result = activateOnce(current, world);
    current = result.state;
    completions.push(...result.completions);
    if (result.completions.length === 0) break;
  }
  return { state: current, completions };
}

/**
 * Apply an event to the active goals.
 *
 * Only the goals in the five-goal window react: a goal outside it is not
 * listening for anything, exactly as in the client, where `activate()` is what
 * subscribes the handler.
 *
 * When a goal completes, the window is refilled — the client does that in
 * `GoalManager.completeGoal()`, which calls `checkAllGoals()` again
 * (`managers/GoalManager.as:516-524`).
 */
export function applyGoalEvent(
  state: GoalRuntimeState,
  event: GoalEvent,
  world: GoalWorld,
  policy: GoalPolicy = DEFAULT_GOAL_POLICY,
): GoalTransition {
  // The goals in the window are activated — and therefore seeded and swept —
  // before the event is delivered. The client seeds the daily-bonus and
  // population counters in the constructor, i.e. before any event can reach
  // them, and a goal that enters the window is swept before it can react.
  const activated = activateGoals(state, world, policy);
  let current = activated.state;
  const completions: GoalCompletion[] = [...activated.completions];
  for (const goalId of activeGoalIds(current)) {
    const definition = getGoalDefinition(goalId);
    if (!definition) continue;
    const effect = evaluateEvent(definition, current, event, world, policy);
    if (!effect) continue;
    current = withProgress(effect.state, definition.id, effect.currentStep);
    if (isGoalComplete(current, definition.id)) {
      current = withCompleted(current, definition.id);
      completions.push(completionFor(definition));
    }
  }
  // A completed goal frees a slot in the window; the client refills it in
  // `GoalManager.completeGoal()` (`managers/GoalManager.as:516-524`).
  const after = activateGoals(current, world, policy);
  return { state: after.state, completions: [...completions, ...after.completions] };
}

/**
 * The result of trying to pay a goal's reward.
 */
export type GoalAward =
  | { readonly ok: true; readonly reward: GoalReward; readonly state: GoalRuntimeState }
  | { readonly ok: false; readonly reason: 'not-completed' | 'already-awarded' | 'unknown-goal' };

/**
 * Pay a completed goal's reward — once.
 *
 * The client sends `complete_goal` and the server applies the resource
 * variation the client attached to it; the upstream server does exactly that
 * (`upstream/socialwarriors/command.py:76-79`). A server-authoritative clone
 * must ignore the client's variation and grant its own reward, and it must
 * not grant it twice: a replayed `complete_goal` must not pay again.
 *
 * A goal whose stored progress already reached its step count counts as
 * complete, so a migrated player could be paid for goals they finished
 * before the migration. The server has to seed `awarded` from its own award
 * log when it migrates a legacy save.
 */
export function awardGoal(state: GoalRuntimeState, goalId: number): GoalAward {
  const definition = getGoalDefinition(goalId);
  if (!definition) return { ok: false, reason: 'unknown-goal' };
  if (state.awarded[goalId] === true) return { ok: false, reason: 'already-awarded' };
  if (!isGoalComplete(state, goalId)) return { ok: false, reason: 'not-completed' };
  return {
    ok: true,
    reward: definition.reward,
    state: { ...state, awarded: { ...state.awarded, [goalId]: true } },
  };
}
