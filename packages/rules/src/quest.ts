/**
 * The quest system: a deterministic, server-runnable state machine.
 *
 * The assault missions ("quests") are scripted content in the **client**. The
 * decompiled client (`.work/as/basesec/scripts/quest/`, 23 concrete quest
 * classes plus `AbstractQuest`, `QuestHardcore` and the `Quest` dispatcher) is
 * the specification — `re/docs/12-quest-system.md` and `re/data/quests.json`
 * reduce it to data. This module turns that data into pure functions a server
 * can run:
 *
 * - the quest lifecycle: `prepareInit` → `start` → `mapLoaded` → simulate →
 *   `end` / `defeat`, plus the `difficulty` getter/setter;
 * - the chapter / objective state machine (`idSimpleChapter`, `set_quest_var`);
 * - per-quest win and fail conditions, as pure predicates over a quest state;
 * - the reward table, the once-only award, and the unit recovery.
 *
 * Everything here is pure: no `Date.now()`, no `Math.random()`, no I/O. Time is
 * always an explicit parameter.
 *
 * ## Discrepancies found against `re/data/quests.json`
 *
 * The spec is right about the quests but wrong about three *implemented* win
 * conditions. The client is the specification (`AGENTS.md` →
 * *Architecture Non-Negotiables* #2), so the corrected behaviour is what is
 * implemented here.
 *
 * 1. **`Quest10SpecialOps` (100000010) and `Quest14Spy2` (100000014).** The
 *    spec says the win needs "every bastard dead **and** the commando in the
 *    computer / prison area". There is no such conjunction in the code:
 *    `bastardKilled` fires the end scene as soon as the `bastards` dictionary
 *    is empty (`quest/Quest10SpecialOps.as:520-534`,
 *    `quest/Quest14Spy2.as:473-485`), and `commandoArrived` only *starts* that
 *    same end scene when the dictionary is *already* empty
 *    (`quest/Quest10SpecialOps.as:545-559`, `quest/Quest14Spy2.as:507-521`).
 *    Reaching the area raises a confirm popup; it is not part of the win
 *    condition. Implemented as "every bastard is dead".
 *
 * 2. **`Quest02CentralNuclear` (100000002).** The spec calls the objective
 *    "strictly ordered: the plant must be destroyed before the command centre
 *    can be attacked". There is no ordering check in the code: the plant's
 *    `onKill` only deactivates the towers
 *    (`quest/Quest02CentralNuclear.as:156-165, 178-196`) and the command
 *    centre's `onKill` always plays the victory scene
 *    (`quest/Quest02CentralNuclear.as:142-149`). Implemented as "destroy the
 *    command centre"; the plant is a scripted step, not a gate.
 *
 * 3. **`Quest06Airstrike` (100000006).** The spec's two-step objective is not
 *    gated either (`quest/Quest06Airstrike.as:130-143`): clearing the radio
 *    station's defenders triggers the airstrike, and destroying the command
 *    centre is the win. Both steps are modelled; only the second one is a win
 *    condition.
 *
 * ## Preserved caveats
 *
 * The 14 UNVERIFIED items of `re/docs/12-quest-system.md` §7 are **not**
 * resolved here. The ones that touch this module stay caveats:
 *
 * - **#1** the `setDifficulty` handler of `popups/PopupLoadingQuest.as:138-150`
 *   only handles `star1`, so the shipped client could only ever play
 *   difficulty 1. The difficulty-2/3 rules exist in
 *   `quest/AbstractQuest.as:382-423` and are implemented, but they are
 *   unreachable in the shipped client.
 * - **#2** the difficulty gate reads
 *   `Base.Player.questsRank[Base.Main.currentFriend]` while `questsRank` is
 *   keyed by the numeric quest index, so the gate is broken in the client.
 * - **#3** `Quest08Rocket` declares its objective with `canDie: false`, which
 *   clamps the launcher's health to 1
 *   (`core/isoengine/IsoFightingElement.as:508-518`), so the `onKill` victory
 *   callback can never fire and the quest is unwinnable by the client's own
 *   code path. The predicate is implemented; `victoryReachable` is `false`.
 * - **#4** the static reward row is *positional*
 *   (`globals.REWARDS_QUESTS[questIds.indexOf(id)]`, `quest/AbstractQuest.as:449`).
 *   Here the row is pinned **by id**, so re-ordering the catalogue cannot
 *   silently change the rewards.
 * - **#5** `Quest03DefendConvoyAuto`'s description says "defeat all enemies";
 *   the code implements "get 3 trucks to the exit"
 *   (`quest/Quest03DefendConvoyAuto.as:175-189`). The code wins.
 * - **#6** the convoy quest's "No flying units allowed" is *not* enforced
 *   client-side; only `Quest07Ship`, `Quest08Rocket` and `Quest09Laboratories`
 *   set `unitTypesExcluded` (`quest/AbstractQuest.as:488-494`).
 * - **#8** `Base.Items.globals.MAX_GOLD_QUEST` does not exist in the shipped
 *   config, so the client's gold cap never fires. No cap is applied here.
 * - **#11 / #12** `100000023`, `100000024`, `100000027`, `100000028` and
 *   `100000100` have no client class, no map and no upstream map file. They
 *   are not quests and are not in the catalogue.
 * - **#13** `QuestWeekly01` sends `end_quest` with `"win": 1` **always**
 *   (`popups/PopupWeeklyQuestFinished.as:94`). The weekly quest's real outcome
 *   is computed here from the bot counter and the timer, never trusted.
 */

import type { Random } from './random.ts';

// ---------------------------------------------------------------------------
// Catalogue
// ---------------------------------------------------------------------------

/** The quest ids, as the client spells them (`quest/Quest.as:57-107`). */
export const QUEST_ID_WEEKLY_01 = '100000049';
export const QUEST_ID_01_BAZOOKA = '100000001';
export const QUEST_ID_02_CENTRAL_NUCLEAR = '100000002';
export const QUEST_ID_03_DEFEND_CONVOY_AUTO = '100000003';
export const QUEST_ID_04_SUPERTANK = '100000004';
export const QUEST_ID_05_ASSAULT_CONVOY = '100000005';
export const QUEST_ID_06_AIRSTRIKE = '100000006';
export const QUEST_ID_07_SHIP = '100000007';
export const QUEST_ID_08_ROCKET = '100000008';
export const QUEST_ID_09_LABORATORIES = '100000009';
export const QUEST_ID_10_SPECIAL_OPS = '100000010';
export const QUEST_ID_11_SAVE_VILLAGES = '100000011';
export const QUEST_ID_12_TANKBOSS = '100000012';
export const QUEST_ID_13_TYRANNOSAURUS = '100000013';
export const QUEST_ID_14_SPY_2 = '100000014';
export const QUEST_ID_15_HARDCORE1 = '100000017';
export const QUEST_ID_16_HARDCORE2 = '100000018';
export const QUEST_ID_17_HARDCORE3 = '100000019';
export const QUEST_ID_18_HARDCORE4 = '100000020';
export const QUEST_ID_19_HARDCORE5 = '100000021';
export const QUEST_ID_20_HARDCORE6 = '100000022';
export const QUEST_ID_22_HARDCORE9 = '100000026';
export const QUEST_ID_23_HARDCORE10 = '100000025';

/**
 * The client's play order (`quest/Quest.as:192`).
 *
 * The index is load-bearing: it is the quest's *rank key*
 * (`Base.Player.questsRank[Quest.iQuest]`) **and** the index into the
 * positional reward table `globals.REWARDS_QUESTS`
 * (`quest/AbstractQuest.as:449`). Index 0 is the weekly quest, which is
 * excluded from `Quest.numQuests` (`quest/Quest.as:239-243`).
 */
export const QUEST_IDS: readonly string[] = [
  QUEST_ID_WEEKLY_01,
  QUEST_ID_01_BAZOOKA,
  QUEST_ID_06_AIRSTRIKE,
  QUEST_ID_03_DEFEND_CONVOY_AUTO,
  QUEST_ID_04_SUPERTANK,
  QUEST_ID_05_ASSAULT_CONVOY,
  QUEST_ID_02_CENTRAL_NUCLEAR,
  QUEST_ID_07_SHIP,
  QUEST_ID_08_ROCKET,
  QUEST_ID_09_LABORATORIES,
  QUEST_ID_10_SPECIAL_OPS,
  QUEST_ID_11_SAVE_VILLAGES,
  QUEST_ID_12_TANKBOSS,
  QUEST_ID_13_TYRANNOSAURUS,
  QUEST_ID_14_SPY_2,
  QUEST_ID_15_HARDCORE1,
  QUEST_ID_16_HARDCORE2,
  QUEST_ID_17_HARDCORE3,
  QUEST_ID_18_HARDCORE4,
  QUEST_ID_19_HARDCORE5,
  QUEST_ID_20_HARDCORE6,
  QUEST_ID_22_HARDCORE9,
  QUEST_ID_23_HARDCORE10,
];

/** How many quests the client offers (`Quest.numQuests` = `questIds.length - 1`). */
export const NUM_STORY_QUESTS = QUEST_IDS.length - 1;

/** The difficulty the player picks in `PopupLoadingQuest` (1–3 stars). */
export type QuestDifficulty = 1 | 2 | 3;

/**
 * The reward keys, in the order the client's reward objects declare them.
 *
 * These are the client's cost keys (`core/Constants.as`: `COST_GOLD = "g"`,
 * `COST_XP = "x"`, `COST_WOOD = "w"`, `COST_OIL = "o"`, `COST_STEEL = "s"`,
 * `COST_CASH = "c"`), which is also what the `end_quest` command carries.
 */
export type QuestRewardKey = 'g' | 'x' | 'w' | 'o' | 's' | 'c';

/** The reward keys, in the client's declaration order. */
export const REWARD_KEY_ORDER: readonly QuestRewardKey[] = ['g', 'x', 'w', 'o', 's', 'c'];

/**
 * The trigger a scripted element carries.
 *
 * | trigger | fires when |
 * |---|---|
 * | `onKill` | the element is destroyed (`chapters/Chapter.as:939-942`) |
 * | `onNearDeath` | its health crosses 10 % of max life (`core/isoengine/IsoFightingElement.as:469-472`) |
 * | `onKillDefenders` | every unit defending it is dead |
 */
export type QuestElementTrigger = 'onKill' | 'onNearDeath' | 'onKillDefenders' | 'none';

/** A scripted element of a quest (the client's `importantIds` dictionary). */
export interface QuestElementSpec {
  /**
   * How the element is addressed in a quest state.
   *
   * It is the chapter id when the element has one (the handle the cutscenes
   * use), and `item:<itemId>` otherwise. Only `Quest03DefendConvoyAuto`'s
   * truck lacks a chapter id.
   */
  readonly ref: string;
  /** The item id of the element. */
  readonly itemId: number;
  /** The chapter id, when the element has one. */
  readonly chapterId: string | null;
  /** The trigger the element carries. */
  readonly trigger: QuestElementTrigger;
  /**
   * Whether the element may die.
   *
   * `false` clamps the element's health to 1
   * (`core/isoengine/IsoFightingElement.as:508-518`), so it never fires
   * `onKill` — but it *can* still reach near death.
   */
  readonly canDie: boolean;
}

/** A win condition, as data. */
export type QuestWinCondition =
  /** Every listed element must have been destroyed. */
  | { readonly kind: 'destroyAll'; readonly elements: readonly string[] }
  /** Every listed element must have reached near death. */
  | { readonly kind: 'nearDeathAll'; readonly elements: readonly string[] }
  /** The defenders of every listed element must be dead. */
  | { readonly kind: 'defendersClearedAll'; readonly elements: readonly string[] }
  /** Every listed counter must have reached its threshold. */
  | {
      readonly kind: 'countersAtLeast';
      readonly counters: readonly { readonly name: string; readonly atLeast: number }[];
    }
  /** Every listed counter must be zero. */
  | { readonly kind: 'countersZero'; readonly counters: readonly string[] }
  /** Every listed condition must hold. */
  | { readonly kind: 'all'; readonly of: readonly QuestWinCondition[] };

/** A loss condition, as data. */
export type QuestFailCondition =
  /** A key ("losing") element was destroyed. */
  | { readonly kind: 'keyElementDestroyed' }
  /** The mission timer ran out. */
  | { readonly kind: 'timerExpired' }
  /** The player's army was wiped out. */
  | { readonly kind: 'armyWipedOut' }
  /** The listed counter fell to (or below) the threshold. */
  | { readonly kind: 'counterAtMost'; readonly counter: string; readonly atMost: number };

/** One quest of the catalogue. */
export interface QuestSpec {
  /** The quest id, as a string. */
  readonly id: string;
  /** The client's constant name, e.g. `QUEST_01_BAZOOKA`. */
  readonly constantName: string;
  /** The client's class name, e.g. `Quest01Bazooka`. */
  readonly className: string;
  /** The display title (`literals[Quest.QUEST_TITLE]`). */
  readonly title: string;
  /** The display subtitle (`literals[Quest.QUEST_SUBTITLE]`). */
  readonly subtitle: string;
  /** The terrain map id (`MapManager.MAP_*`, `managers/MapManager.as:14-62`). */
  readonly mapId: number;
  /** The index in the client's play order; also the reward-table index. */
  readonly playIndex: number;
  /**
   * The client's `levelRequired` getter.
   *
   * Vestigial: nothing in the client reads it, and the real gate is the
   * server's `globals.QUESTS_MIN_LEVELS` (level 40 for the four team quests).
   */
  readonly levelRequired: number;
  /** The difficulty the quest starts at. */
  readonly defaultDifficulty: QuestDifficulty;
  /**
   * True when the quest overrides the difficulty setter with a no-op.
   *
   * Only `Quest13Tyrannosaurus` does (`quest/Quest13Tyrannosaurus.as:239-247`),
   * so difficulty has no gameplay effect there.
   */
  readonly difficultyIsNoOp: boolean;
  /** The scripted elements (the client's `importantIds`). */
  readonly elements: readonly QuestElementSpec[];
  /** The losing elements (the client's `keyIds`), by ref. */
  readonly keyElementRefs: readonly string[];
  /**
   * True when a wiped-out army ends the quest.
   *
   * `AbstractQuest.prepareQuestEnd` returns early when `keyIds` is non-empty
   * and `alwaysEndIfMyUnitsDie` is false (`quest/AbstractQuest.as:284-304`),
   * so a quest with key elements does *not* lose on an army wipe — unless it
   * sets `alwaysEndIfMyUnitsDie` (only `Quest07Ship` does).
   */
  readonly armyWipeEndsQuest: boolean;
  /**
   * True when a wiped-out army resolves the quest at once.
   *
   * `Quest11SaveVillages` overrides `prepareQuestEnd` to run the airstrike
   * immediately (`quest/Quest11SaveVillages.as:388-391`); the airstrike wins
   * if every civilian is already out and loses otherwise.
   */
  readonly armyWipeResolvesImmediately: boolean;
  /** The mission timer, in seconds. `null` when the quest has none. */
  readonly timeLimitSeconds: number | null;
  /** When the mission timer starts counting. */
  readonly timeLimitStartsAt: 'prepared' | 'started';
  /** The static win reward row (`globals.REWARDS_QUESTS`). */
  readonly reward: Readonly<Partial<Record<QuestRewardKey, number>>>;
  /** The percentage of killed units recovered after the quest (60 for all). */
  readonly recoveredPercent: number;
  readonly playerUnitCountOverride: number | null;
  /**
   * Counters the quest starts with.
   *
   * A counter that is *absent* never satisfies a `countersZero` condition, so
   * a quest that needs "no civilians left" cannot be won before the map has
   * been counted.
   */
  readonly initialCounters: Readonly<Record<string, number>>;
  /**
   * The unit `group_type`s the player may not bring.
   *
   * Only three quests filter the player's army, and all three exclude
   * `AIR_VEHICLE`: `Quest07Ship` (`:81-83`), `Quest08Rocket` (`:88-90`) and
   * `Quest09Laboratories` (`:95-97`). `Quest03DefendConvoyAuto` claims the
   * same restriction in its description but never sets it
   * (`re/docs/12-quest-system.md` §7 item #6).
   */
  readonly excludedUnitGroupTypes: readonly string[];
  /** The win condition. */
  readonly win: QuestWinCondition;
  /** The loss conditions. */
  readonly defeat: readonly QuestFailCondition[];
  /** Quest-specific loss rules the generic conditions cannot express. */
  readonly customDefeat?: (state: QuestState) => boolean;
  /**
   * False when the client's own code path cannot reach the win.
   *
   * `Quest08Rocket`'s objective is declared `canDie: false`, so it can never
   * be destroyed and its `onKill` victory callback can never fire
   * (`re/docs/12-quest-system.md` §7 item #3).
   */
  readonly victoryReachable: boolean;
}

/** Item ids the quests name. From `core/Constants.as` (and `constants.py`). */
const ITEM = {
  goodBoy: 1017,
  truck1: 1013,
  truck2: 1035,
  truck3: 1032,
  ship: 1019,
  zodiac: 1018,
  specialOps: 1052,
  worker3: 1040,
  orcBoss: 1108,
  orcBossJeep: 1131,
  orcHelicopter: 1110,
  megatank: 1037,
  trex: 1057,
  fireTrex: 1093,
  orcSwordman: 1123,
  bossGolem: 1053,
  gunbot: 1061,
  bumblebee: 1062,
  dreadnought: 1084,
  nuclearPlant: 89,
  orcHq: 195,
  orcRiderAcademy: 180,
  disabledAmmoI: 115,
  disabledAmmoII: 116,
  disabledOrcTank: 204,
  radioStation: 121,
  smallHarbour: 907,
  orcBunker: 201,
  orcBossAcademy: 179,
  orcFlamethrowerAcademy: 182,
  trexCageGreen: 958,
  trexCageRed: 959,
  prison: 19,
  rocketLauncher: 128,
  laboratory: 118,
} as const;

/** `Constants.GROUP_TYPE_AIR_VEHICLE` — the group type three quests exclude. */
export const GROUP_TYPE_AIR_VEHICLE = 'AIR_VEHICLE';

/**
 * The army the weekly quest spawns for the player.
 *
 * Ported from `quest/QuestWeekly01.as:48, 100-117`: the player's own army is
 * discarded (`Quest.setPlayerUnits([])`, `:80`) and the quest puts four units
 * on the map at its init tile — two Bumblebees and two Dreadnoughts.
 */
export const WEEKLY_PLAYER_ARMY: readonly number[] = [
  ITEM.bumblebee,
  ITEM.bumblebee,
  ITEM.dreadnought,
  ITEM.dreadnought,
];

/** Build an element spec. */
function el(
  chapterId: string | null,
  itemId: number,
  trigger: QuestElementTrigger,
  canDie = true,
): QuestElementSpec {
  return { ref: chapterId ?? `item:${itemId}`, itemId, chapterId, trigger, canDie };
}

/**
 * The five laboratories of `Quest09Laboratories`.
 *
 * The client identifies them only by their tile coordinates — the airstrike
 * target lists are hard-coded (`quest/Quest09Laboratories.as:107-114`). The
 * item id is `ID_BUILDING_LABORATORY` (118) from the shipped constants; the
 * client never names it.
 */
export const LABORATORY_REFS: readonly string[] = [
  'lab@49,60',
  'lab@52,35',
  'lab@80,83',
  'lab@86,53',
  'lab@86,19',
];

const LAB_ELEMENTS: readonly QuestElementSpec[] = LABORATORY_REFS.map((ref) => ({
  ref,
  itemId: ITEM.laboratory,
  chapterId: null,
  trigger: 'onKill' as const,
  canDie: true,
}));

function spec(
  partial: Omit<
    QuestSpec,
    | 'recoveredPercent'
    | 'victoryReachable'
    | 'playerUnitCountOverride'
    | 'initialCounters'
    | 'excludedUnitGroupTypes'
  > &
    Partial<
      Pick<
        QuestSpec,
        | 'recoveredPercent'
        | 'victoryReachable'
        | 'playerUnitCountOverride'
        | 'initialCounters'
        | 'excludedUnitGroupTypes'
      >
    >,
): QuestSpec {
  return {
    recoveredPercent: 60,
    victoryReachable: true,
    playerUnitCountOverride: null,
    initialCounters: {},
    excludedUnitGroupTypes: [],
    ...partial,
  };
}

/**
 * The quest catalogue.
 *
 * The reward rows are pinned **by id**, not by index, so the catalogue can be
 * reordered without silently changing what a quest pays
 * (`re/docs/12-quest-system.md` §7 item #4).
 */
export const QUESTS: readonly QuestSpec[] = [
  // -- 0: the weekly mission ------------------------------------------------
  spec({
    id: QUEST_ID_WEEKLY_01,
    constantName: 'QUEST_WEEKLY_01',
    className: 'QuestWeekly01',
    title: 'Weekly Mission!',
    subtitle: 'Need some cash?? Kill all Gun Bots!',
    mapId: 149,
    playIndex: 0,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    playerUnitCountOverride: WEEKLY_PLAYER_ARMY.length,
    initialCounters: { questUnitsAlive: WEEKLY_PLAYER_ARMY.length },
    timeLimitSeconds: 90,
    timeLimitStartsAt: 'prepared',
    reward: {},
    win: { kind: 'countersAtLeast', counters: [{ name: 'botsKilled', atLeast: 5 }] },
    defeat: [
      { kind: 'timerExpired' },
      { kind: 'counterAtMost', counter: 'questUnitsAlive', atMost: 0 },
    ],
  }),

  // -- 1: DEFEAT THE ENEMY ---------------------------------------------------
  spec({
    id: QUEST_ID_01_BAZOOKA,
    constantName: 'QUEST_01_BAZOOKA',
    className: 'Quest01Bazooka',
    title: 'DEFEAT THE ENEMY',
    subtitle: 'Defeat the Orc Commander!',
    mapId: 101,
    playIndex: 1,
    levelRequired: 1,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      // The Good Boy is declared `canDie: false` and re-enabled in mapLoaded
      // (quest/Quest01Bazooka.as:326-332), so it can be killed — and killing
      // it loses the quest.
      el('general', ITEM.goodBoy, 'none'),
      el('boss1', ITEM.orcBoss, 'onNearDeath', false),
      el('parkedJeep', ITEM.orcRiderAcademy, 'none', false),
      el('ship', ITEM.ship, 'none', false),
      // Spawned by the stage-1 scene (quest/Quest01Bazooka.as:173-184).
      el('jeep', ITEM.orcBossJeep, 'onNearDeath', false),
    ],
    keyElementRefs: ['general'],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 1500, w: 400 },
    win: {
      kind: 'all',
      of: [
        { kind: 'nearDeathAll', elements: ['boss1'] },
        { kind: 'nearDeathAll', elements: ['jeep'] },
      ],
    },
    defeat: [{ kind: 'keyElementDestroyed' }],
  }),

  // -- 2: AIRSTRIKE! --------------------------------------------------------
  spec({
    id: QUEST_ID_06_AIRSTRIKE,
    constantName: 'QUEST_06_AIRSTRIKE',
    className: 'Quest06Airstrike',
    title: 'AIRSTRIKE!',
    subtitle: 'Call air reinforcements and witness how the enemy camp is destroyed!',
    mapId: 106,
    playIndex: 2,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('radioStation', ITEM.radioStation, 'onKillDefenders'),
      el('enemyCommandCenter', ITEM.orcHq, 'onKill'),
    ],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 2000, w: 600 },
    win: {
      kind: 'all',
      of: [
        { kind: 'defendersClearedAll', elements: ['radioStation'] },
        { kind: 'destroyAll', elements: ['enemyCommandCenter'] },
      ],
    },
    defeat: [{ kind: 'armyWipedOut' }],
  }),

  // -- 3: DEFEND THE CONVOY -------------------------------------------------
  spec({
    id: QUEST_ID_03_DEFEND_CONVOY_AUTO,
    constantName: 'QUEST_03_DEFEND_CONVOY_AUTO',
    className: 'Quest03DefendConvoyAuto',
    title: 'DEFEND THE CONVOY',
    subtitle:
      'Defeat all enemies before they destroy the allied convoy! No flying units allowed on this quest!',
    mapId: 103,
    playIndex: 3,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [el('colonel', ITEM.goodBoy, 'none')],
    // The truck is a key element but has no chapter id, so it is addressed
    // by its item id (quest/Quest03DefendConvoyAuto.as:96, 101).
    keyElementRefs: [`item:${ITEM.truck1}`],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 2500, o: 800 },
    // The implemented win is "get all 3 trucks to the exit", not the
    // description's "defeat all enemies" (re/docs/12-quest-system.md §7 #5).
    win: { kind: 'countersAtLeast', counters: [{ name: 'trucksArrived', atLeast: 3 }] },
    defeat: [{ kind: 'keyElementDestroyed' }],
  }),

  // -- 4: STOP THE BIG WEAPON ----------------------------------------------
  spec({
    id: QUEST_ID_04_SUPERTANK,
    constantName: 'QUEST_04_SUPERTANK',
    className: 'Quest04Supertank',
    title: 'STOP THE BIG WEAPON',
    subtitle: 'Destroy the tank weapons and then the tank itself before they assemble it',
    mapId: 104,
    playIndex: 4,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('piece_1', ITEM.disabledAmmoI, 'onNearDeath', false),
      el('piece_2', ITEM.disabledAmmoII, 'onNearDeath', false),
      el('disabledTank', ITEM.disabledOrcTank, 'onNearDeath', false),
      el('redChopper', ITEM.orcHelicopter, 'none', false),
      // Spawned once both ammo pieces are gone (quest/Quest04Supertank.as:223-249).
      el('boss', ITEM.megatank, 'onNearDeath'),
    ],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 3000, s: 1000 },
    win: {
      kind: 'all',
      of: [
        { kind: 'nearDeathAll', elements: ['piece_1', 'piece_2'] },
        { kind: 'nearDeathAll', elements: ['boss'] },
      ],
    },
    defeat: [{ kind: 'armyWipedOut' }],
    // Attacking the disabled tank before both ammo pieces are gone is the
    // trap: its near-death callback plays the "it was a fake" scene and ends
    // the quest as a loss (quest/Quest04Supertank.as:263-273).
    customDefeat: (state) =>
      state.script.nearDeath.includes('disabledTank') &&
      !(
        state.script.nearDeath.includes('piece_1') &&
        state.script.nearDeath.includes('piece_2')
      ),
  }),

  // -- 5: DESTROY THE TRUCK -------------------------------------------------
  spec({
    id: QUEST_ID_05_ASSAULT_CONVOY,
    constantName: 'QUEST_05_ASSAULT_CONVOY',
    className: 'Quest05AssaultConvoy',
    title: 'DESTROY THE TRUCK',
    subtitle: 'Eliminate the truck before it leaves the zone!',
    mapId: 105,
    playIndex: 5,
    levelRequired: 1,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [el('truck', ITEM.truck3, 'onKill')],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    // The countdown starts in the intro cutscene's `moveConvoy` callback
    // (quest/Quest05AssaultConvoy.as:273-284).
    timeLimitSeconds: 120,
    timeLimitStartsAt: 'started',
    reward: { g: 3500, w: 1200 },
    win: { kind: 'destroyAll', elements: ['truck'] },
    defeat: [{ kind: 'timerExpired' }, { kind: 'armyWipedOut' }],
  }),

  // -- 6: BLOW THE POWER PLANT ---------------------------------------------
  spec({
    id: QUEST_ID_02_CENTRAL_NUCLEAR,
    constantName: 'QUEST_02_CENTRAL_NUCLEAR',
    className: 'Quest02CentralNuclear',
    title: 'BLOW THE POWER PLANT',
    subtitle: 'Blow up the Nuclear Plant and then the Command Center!',
    mapId: 102,
    playIndex: 6,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('goodBoy', ITEM.goodBoy, 'none'),
      el('centralNuclear', ITEM.nuclearPlant, 'onKill'),
      el('commandCenter', ITEM.orcHq, 'onKill'),
      el('truck', ITEM.truck2, 'none'),
    ],
    keyElementRefs: ['goodBoy'],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 4000, o: 1400 },
    // No ordering gate in the client: destroying the plant only turns the
    // towers off (quest/Quest02CentralNuclear.as:178-196).
    win: { kind: 'destroyAll', elements: ['commandCenter'] },
    defeat: [{ kind: 'keyElementDestroyed' }],
  }),

  // -- 7: V.I.P ENEMY -------------------------------------------------------
  spec({
    id: QUEST_ID_07_SHIP,
    constantName: 'QUEST_07_SHIP',
    className: 'Quest07Ship',
    title: 'V.I.P ENEMY',
    subtitle: 'Steal the ship and attack the command center where enemy is hidden.',
    mapId: 107,
    playIndex: 7,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('general', ITEM.goodBoy, 'none'),
      el('harbour', ITEM.smallHarbour, 'onKillDefenders'),
      el('ship', ITEM.ship, 'onKill'),
      el('commandCenter', ITEM.orcHq, 'onKill'),
    ],
    // Both the harbour and the ship are losing elements
    // (quest/Quest07Ship.as:179-180).
    keyElementRefs: ['harbour', 'ship'],
    excludedUnitGroupTypes: [GROUP_TYPE_AIR_VEHICLE],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 4500, s: 1600 },
    win: {
      kind: 'all',
      of: [
        { kind: 'defendersClearedAll', elements: ['harbour'] },
        { kind: 'destroyAll', elements: ['commandCenter'] },
      ],
    },
    defeat: [{ kind: 'keyElementDestroyed' }, { kind: 'armyWipedOut' }],
  }),

  // -- 8: Dangerous rocket! -------------------------------------------------
  spec({
    id: QUEST_ID_08_ROCKET,
    constantName: 'QUEST_08_ROCKET',
    className: 'Quest08Rocket',
    title: 'Dangerous rocket!',
    subtitle: "Don't let the enemy launch the rocket! No flying units allowed on this quest!",
    mapId: 108,
    playIndex: 8,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('general', ITEM.goodBoy, 'none'),
      // `canDie: false` — the launcher can never be destroyed, so the
      // `onKill` victory callback cannot fire (re/docs/12-quest-system.md §7 #3).
      el('commandCenter', ITEM.rocketLauncher, 'onKill', false),
    ],
    keyElementRefs: [],
    excludedUnitGroupTypes: [GROUP_TYPE_AIR_VEHICLE],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: 600,
    timeLimitStartsAt: 'started',
    reward: { g: 5000, o: 1800 },
    win: { kind: 'destroyAll', elements: ['commandCenter'] },
    defeat: [{ kind: 'timerExpired' }, { kind: 'armyWipedOut' }],
    victoryReachable: false,
  }),

  // -- 9: Destroy all the labs ---------------------------------------------
  spec({
    id: QUEST_ID_09_LABORATORIES,
    constantName: 'QUEST_09_LABORATORIES',
    className: 'Quest09Laboratories',
    title: 'Destroy all the labs',
    subtitle:
      'Get the radio and call air reinforcements to destroy the labs. No flying units allowed on this quest!',
    mapId: 109,
    playIndex: 9,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [el('radioStation', ITEM.radioStation, 'onKillDefenders'), ...LAB_ELEMENTS],
    keyElementRefs: [],
    excludedUnitGroupTypes: [GROUP_TYPE_AIR_VEHICLE],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 5500, s: 2000 },
    win: {
      kind: 'all',
      of: [
        { kind: 'defendersClearedAll', elements: ['radioStation'] },
        { kind: 'destroyAll', elements: LABORATORY_REFS },
      ],
    },
    defeat: [{ kind: 'armyWipedOut' }],
  }),

  // -- 10: STEAL THE LAPTOP -------------------------------------------------
  spec({
    id: QUEST_ID_10_SPECIAL_OPS,
    constantName: 'QUEST_10_SPECIAL_OPS',
    className: 'Quest10SpecialOps',
    title: 'STEAL THE LAPTOP',
    subtitle: 'Steal the laptop from the bunker. Kill everyone first!',
    mapId: 110,
    playIndex: 10,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('commando', ITEM.specialOps, 'none'),
      el('zodiac', ITEM.zodiac, 'none'),
      el('bunker', ITEM.orcBunker, 'none'),
    ],
    keyElementRefs: ['commando'],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 6000, w: 2200 },
    // The "bastards" are every enemy unit whose group_type is LONG_RANGE,
    // SHORT_RANGE or LAND_VEHICLE (quest/Quest10SpecialOps.as:459-474).
    win: { kind: 'countersZero', counters: ['bastardsAlive'] },
    defeat: [{ kind: 'keyElementDestroyed' }],
  }),

  // -- 11: RESCUE THE ALLIES ------------------------------------------------
  spec({
    id: QUEST_ID_11_SAVE_VILLAGES,
    constantName: 'QUEST_11_SAVE_VILLAGES',
    className: 'Quest11SaveVillages',
    title: 'RESCUE THE ALLIES',
    subtitle: 'Steal the cargo ships and rescue your allies before the airstrike!.',
    mapId: 111,
    playIndex: 11,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('bazookaAcademy', ITEM.orcBossAcademy, 'onKillDefenders'),
      el('academy', ITEM.orcFlamethrowerAcademy, 'onKillDefenders'),
      el('newWestBoat', ITEM.ship, 'none', false),
      el('newEastBoat', ITEM.ship, 'none', false),
    ],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: true,
    timeLimitSeconds: 240,
    timeLimitStartsAt: 'started',
    reward: { g: 6500, o: 2400 },
    // Every civilian must be out of both friendly areas
    // (quest/Quest11SaveVillages.as:617-627, 629-668).
    win: { kind: 'countersZero', counters: ['workersInVillages'] },
    defeat: [{ kind: 'timerExpired' }, { kind: 'armyWipedOut' }],
  }),

  // -- 12: THE MECHANICAL MENACE -------------------------------------------
  spec({
    id: QUEST_ID_12_TANKBOSS,
    constantName: 'QUEST_12_TANKBOSS',
    className: 'Quest12TankBoss',
    title: 'THE MECHANICAL MENACE',
    subtitle: 'Something wierd happend that destoryed the advanced guard post',
    mapId: 112,
    playIndex: 12,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [el('golem', ITEM.bossGolem, 'onKill')],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 7000, s: 2600 },
    win: { kind: 'destroyAll', elements: ['golem'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),

  // -- 13: DEFEAT THE DINOSAURS --------------------------------------------
  spec({
    id: QUEST_ID_13_TYRANNOSAURUS,
    constantName: 'QUEST_13_TYRANNOSAURUS',
    className: 'Quest13Tyrannosaurus',
    title: 'DEFEAT THE DINOSAURS',
    subtitle: 'Defeat some T-Rexes!',
    mapId: 113,
    playIndex: 13,
    levelRequired: 1,
    defaultDifficulty: 1,
    // The difficulty setter is a no-op here, so difficulty changes nothing.
    difficultyIsNoOp: true,
    elements: [
      el('cage1', ITEM.trexCageGreen, 'onKillDefenders', false),
      el('cage2', ITEM.trexCageRed, 'onKillDefenders', false),
      el('ship', ITEM.ship, 'none', false),
      el('boss1', ITEM.orcSwordman, 'none', false),
      el('trex1', ITEM.trex, 'onKill'),
      el('trex2', ITEM.fireTrex, 'onKill'),
    ],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 7500, w: 2800 },
    win: {
      kind: 'all',
      of: [
        { kind: 'destroyAll', elements: ['trex1'] },
        { kind: 'destroyAll', elements: ['trex2'] },
      ],
    },
    defeat: [{ kind: 'armyWipedOut' }],
  }),

  // -- 14: The River --------------------------------------------------------
  spec({
    id: QUEST_ID_14_SPY_2,
    constantName: 'QUEST_14_SPY_2',
    className: 'Quest14Spy2',
    title: 'The River',
    subtitle: 'This is a stealth mission. You must survive with only one spy!',
    mapId: 114,
    playIndex: 14,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [
      el('commando', ITEM.specialOps, 'none'),
      el('ship', ITEM.ship, 'none'),
      el('harbour', ITEM.smallHarbour, 'none'),
      el('prison', ITEM.prison, 'none'),
    ],
    keyElementRefs: ['commando', 'ship'],
    armyWipeEndsQuest: false,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 8000, o: 3000 },
    win: { kind: 'countersZero', counters: ['bastardsAlive'] },
    defeat: [{ kind: 'keyElementDestroyed' }],
  }),

  // -- 15..22: the hardcore quests -----------------------------------------
  spec({
    id: QUEST_ID_15_HARDCORE1,
    constantName: 'QUEST_15_HARDCORE1',
    className: 'Quest15HCCrusaderBase1',
    title: 'VIKINGS BEACHHEAD',
    subtitle: 'Outsider Vikings base found, leave none of them alive!',
    mapId: 117,
    playIndex: 15,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 10000, s: 3200 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_16_HARDCORE2,
    constantName: 'QUEST_16_HARDCORE2',
    className: 'Quest16HCAliens',
    title: 'KILL THE ALIENS',
    subtitle: 'Fight this threat from outer space!',
    mapId: 118,
    playIndex: 16,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 12000, w: 3500 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_17_HARDCORE3,
    constantName: 'QUEST_17_HARDCORE3',
    className: 'Quest17HCArachnids',
    title: 'ARACHNID MENACE',
    subtitle: 'The arachnids are spoiling our land!',
    mapId: 119,
    playIndex: 17,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 14000, o: 3500 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_18_HARDCORE4,
    constantName: 'QUEST_18_HARDCORE4',
    className: 'Quest18HCDragons',
    title: 'ERRADICATE THE DRAGONS',
    subtitle: "We've found a dragon nest, it needs to be cleansed!",
    mapId: 120,
    playIndex: 18,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 16000, s: 3500 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_19_HARDCORE5,
    constantName: 'QUEST_19_HARDCORE5',
    className: 'Quest19HC',
    title: "DR.SHOCK'S MECH ARMY",
    subtitle: 'DEFEAT THE WICKED ROBOTS, LEAVE NONE OF THEM ALIVE!',
    mapId: 121,
    playIndex: 19,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 18000, w: 3800 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_20_HARDCORE6,
    constantName: 'QUEST_20_HARDCORE6',
    className: 'Quest20HC',
    title: "DR.SHOCK'S MONSTERS",
    subtitle: 'DEFEAT DOCTOR SHOCK AND HIS ARMY OF MONSTERS!',
    mapId: 122,
    playIndex: 20,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 20000, o: 4000 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_22_HARDCORE9,
    constantName: 'QUEST_22_HARDCORE9',
    className: 'Quest23HC',
    title: 'THE WICKED NEBULARS',
    subtitle: 'THE WICKED NEBULARS',
    mapId: 126,
    playIndex: 21,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 22000, s: 4000 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
  spec({
    id: QUEST_ID_23_HARDCORE10,
    constantName: 'QUEST_23_HARDCORE10',
    className: 'Quest24HC',
    title: 'DR. SHOCK STRIKES BACK',
    subtitle: 'DR. SHOCK STRIKES BACK',
    mapId: 125,
    playIndex: 22,
    levelRequired: 0,
    defaultDifficulty: 1,
    difficultyIsNoOp: false,
    elements: [],
    keyElementRefs: [],
    armyWipeEndsQuest: true,
    armyWipeResolvesImmediately: false,
    timeLimitSeconds: null,
    timeLimitStartsAt: 'started',
    reward: { g: 24000, w: 4200 },
    win: { kind: 'countersZero', counters: ['enemiesAlive'] },
    defeat: [{ kind: 'armyWipedOut' }],
  }),
];

const QUESTS_BY_ID: ReadonlyMap<string, QuestSpec> = new Map(
  QUESTS.map((quest) => [quest.id, quest]),
);

/** Look a quest up by id. */
export function getQuestSpec(questId: string): QuestSpec | undefined {
  return QUESTS_BY_ID.get(questId);
}

/**
 * The client's constant name of a quest, e.g. `QUEST_01_BAZOOKA`.
 *
 * **This is the corrected id → name mapping.** `upstream/socialwarriors/constants.py`
 * has three duplicate dictionary keys, so Python keeps the *last* occurrence
 * and reports `100000024 → "QUEST: ISLA_RUBEN3D"`, `100000025 → "QUEST: ISLA_KASPAR"`
 * and `100000026 → "QUEST: ISLA_EGG2"`, hiding the real
 * `HARDCORE8 / HARDCORE10 / HARDCORE9` names. The client's factory
 * (`quest/Quest.as:145-167`), its map ids (`quest/Quest.as:169-191`) and the
 * upstream map filenames agree with the table above
 * (`re/docs/12-quest-system.md` §1.2).
 */
export function questConstantName(questId: string): string | undefined {
  return getQuestSpec(questId)?.constantName;
}

/** The display title of a quest. */
export function questTitle(questId: string): string | undefined {
  return getQuestSpec(questId)?.title;
}

/**
 * The quest's index in the client's play order.
 *
 * This is also the reward-table index and the rank key
 * (`Base.Player.questsRank[Quest.iQuest]`).
 */
export function questPlayIndex(questId: string): number | undefined {
  return getQuestSpec(questId)?.playIndex;
}

// ---------------------------------------------------------------------------
// The chapter / objective state machine
// ---------------------------------------------------------------------------

/** A tile coordinate. */
export interface QuestTile {
  readonly x: number;
  readonly y: number;
}

/**
 * The chapter status — the shape the server stores in `map.currentQuestVars`.
 *
 * Ported from `Chapter.createEmptyStatus` (`chapters/Chapter.as:151-163`).
 */
export interface ChapterStatus {
  /** The chapter id this status belongs to. */
  readonly id: number;
  /** The chapter was actually placed on the map. */
  readonly spawned: boolean;
  /** The chapter was completed. */
  readonly ended: boolean;
  /** The player has been here before. */
  readonly visited: boolean;
  /** The chapter-segment ids whose activator was collected. */
  readonly activators: readonly number[];
  /** The indices into `arBosses` of the killed bosses. */
  readonly boss: readonly number[];
  /** The indices into `arTreasures` of the collected treasures. */
  readonly treasure: readonly number[];
  /** The chapter element ids that were already killed. */
  readonly killed: readonly string[];
  /** The chapter's localisable string table. */
  readonly translation?: unknown;
  /** The current *simple* (endless) chapter id. */
  readonly idSimpleChapter?: number;
  /** The level the simple chapter was generated for. */
  readonly playerLevel?: number;
  /** The tile the simple chapter was generated for. */
  readonly startTile?: QuestTile;
}

/** The chapter id a quest's own chapter uses (`new Chapter(-1)`). */
export const QUEST_CHAPTER_ID = -1;

/** Create an empty chapter status (`chapters/Chapter.as:151-163`). */
export function createEmptyChapterStatus(id: number): ChapterStatus {
  return {
    id,
    spawned: false,
    ended: false,
    visited: false,
    activators: [],
    boss: [],
    treasure: [],
    killed: [],
  };
}

/**
 * Reuse the stored chapter status when it belongs to the same chapter and is
 * not finished; otherwise start from an empty one.
 *
 * Ported from `Chapter.prepareChapterStatus` (`chapters/Chapter.as:203-230`).
 */
export function prepareChapterStatus(
  stored: ChapterStatus | null | undefined,
  id: number,
): ChapterStatus {
  if (!stored || stored.spawned === undefined || stored.ended || stored.id !== id) {
    return createEmptyChapterStatus(id);
  }
  return stored;
}

/** Mark the chapter as spawned (`chapters/Chapter.as:1080-1082`). */
export function markChapterSpawned(status: ChapterStatus): ChapterStatus {
  return { ...status, spawned: true };
}

/** Mark the chapter as ended (`chapters/ChapterManager.finalizeChapter`). */
export function markChapterEnded(status: ChapterStatus): ChapterStatus {
  return { ...status, ended: true };
}

/** Mark the chapter as visited (`chapters/Chapter.as`, `visited` flag). */
export function markChapterVisited(status: ChapterStatus): ChapterStatus {
  return { ...status, visited: true };
}

/**
 * Record that an activator was collected.
 *
 * Ported from `Chapter.onActivatorCollected` (`chapters/Chapter.as:527`): the
 * chapter-segment id is pushed once.
 */
export function recordActivatorCollected(
  status: ChapterStatus,
  segmentId: number,
): ChapterStatus {
  if (status.activators.includes(segmentId)) return status;
  return { ...status, activators: [...status.activators, segmentId] };
}

/** Record that a boss was killed (`chapters/Chapter.as:578-584`). */
export function recordBossKilled(status: ChapterStatus, bossIndex: number): ChapterStatus {
  if (status.boss.includes(bossIndex)) return status;
  return { ...status, boss: [...status.boss, bossIndex] };
}

/** Record that a treasure was collected (`chapters/Chapter.as:531-538`). */
export function recordTreasureCollected(
  status: ChapterStatus,
  treasureIndex: number,
): ChapterStatus {
  if (status.treasure.includes(treasureIndex)) return status;
  return { ...status, treasure: [...status.treasure, treasureIndex] };
}

/**
 * Record that a chapter element was killed.
 *
 * Ported from `Chapter.saveElementKilled` (`chapters/Chapter.as:547-559`): the
 * chapter id is pushed once, so a re-entered chapter does not respawn it.
 * The return value says whether the kill was new.
 */
export function recordChapterElementKilled(
  status: ChapterStatus,
  chapterId: string,
): { readonly status: ChapterStatus; readonly newlyKilled: boolean } {
  if (status.killed.includes(chapterId)) {
    return { status, newlyKilled: false };
  }
  return { status: { ...status, killed: [...status.killed, chapterId] }, newlyKilled: true };
}

/** How many activators, treasures and bosses a chapter needs. */
export interface ChapterObjectives {
  readonly numActivators: number;
  readonly numTreasures: number;
  readonly numBosses: number;
}

/**
 * Whether the chapter's objectives are all done.
 *
 * Ported from `chapters/Chapter.as:523-526` and the `activatorsDone`,
 * `treasureDone` and `bossDone` getters (`:631-644`).
 */
export function chapterObjectivesComplete(
  status: ChapterStatus,
  objectives: ChapterObjectives,
): boolean {
  return (
    status.activators.length >= objectives.numActivators &&
    status.boss.length >= objectives.numBosses &&
    status.treasure.length >= objectives.numTreasures
  );
}

/**
 * Record the identity of the current simple (endless) chapter.
 *
 * Ported from `SimpleChapter.init` (`chapters/SimpleChapter.as:105-113`): the
 * chapter id, the player level and the start tile are stored together so the
 * same map is regenerated on re-entry.
 */
export function advanceSimpleChapter(
  status: ChapterStatus,
  simple: { readonly chapterId: number; readonly playerLevel: number; readonly startTile: QuestTile },
): ChapterStatus {
  return {
    ...status,
    idSimpleChapter: simple.chapterId,
    playerLevel: simple.playerLevel,
    startTile: simple.startTile,
  };
}

// ---------------------------------------------------------------------------
// `set_quest_var`
// ---------------------------------------------------------------------------

/**
 * The quest-variable keys the client writes.
 *
 * Ported from `Chapter.saveChapterStatus` (`chapters/Chapter.as:662-666`) and
 * `SimpleChapter.init` (`chapters/SimpleChapter.as:105-113`).
 *
 * `set_quest_var` is **unauthenticated** — the client can write any of these,
 * including `id` and `ended` — so a server must whitelist the keys and the
 * value shapes (`re/docs/03-commands-quests-economy.md` §9, item 20).
 */
export const QUEST_VAR_KEYS: readonly string[] = [
  'id',
  'spawned',
  'ended',
  'visited',
  'activators',
  'boss',
  'treasure',
  'killed',
  'translation',
  'idSimpleChapter',
  'playerLevel',
  'startTile',
];

/** Whether a key is one the client is allowed to write. */
export function isQuestVarKey(key: string): boolean {
  return QUEST_VAR_KEYS.includes(key);
}

/** The wire form of a `set_quest_var` command (`commands/CmdSetQuestVar.as:8-13`). */
export interface SetQuestVarCommand {
  readonly command: 'set_quest_var';
  /** `args[0]` is the key, `args[1]` the JSON-encoded value. */
  readonly args: readonly [string, string];
}

/** Build the `set_quest_var` command for a key and a value. */
export function questVarCommand(key: string, value: unknown): SetQuestVarCommand {
  return { command: 'set_quest_var', args: [key, JSON.stringify(value)] };
}

/** The result of applying a `set_quest_var` write. */
export interface ApplyQuestVarResult {
  /** The new quest variables. */
  readonly vars: Readonly<Record<string, unknown>>;
  /** The chapter id the client claims is current, when the `id` key was written. */
  readonly currentMissionId?: number;
  /** True when the write was rejected because the key is not whitelisted. */
  readonly rejected: boolean;
  /** True when the write was accepted but deliberately not applied. */
  readonly ignored: boolean;
}

/**
 * Apply a `set_quest_var` write.
 *
 * The upstream server **ignores** `idSimpleChapter` so that the endless
 * chapter can be replayed past chapter 99
 * (`upstream/socialwarriors/command.py:91-95`). That behaviour is reproduced
 * by default; a server that wants the endless chapter to advance must pass
 * `honourSimpleChapter: true`.
 */
export function applyQuestVar(
  vars: Readonly<Record<string, unknown>>,
  key: string,
  value: unknown,
  options: { readonly honourSimpleChapter?: boolean } = {},
): ApplyQuestVarResult {
  if (!isQuestVarKey(key)) {
    return { vars, rejected: true, ignored: false };
  }
  if (key === 'idSimpleChapter' && options.honourSimpleChapter !== true) {
    return { vars, rejected: false, ignored: true };
  }
  const next = { ...vars, [key]: value };
  const result: ApplyQuestVarResult =
    key === 'id' && typeof value === 'number'
      ? { vars: next, currentMissionId: value, rejected: false, ignored: false }
      : { vars: next, rejected: false, ignored: false };
  return result;
}

// ---------------------------------------------------------------------------
// The quest state machine
// ---------------------------------------------------------------------------

/** Where the quest is in its lifecycle. */
export type QuestPhase = 'prepared' | 'started' | 'map-loaded' | 'finished';

/** The scripted state of a quest. */
export interface QuestScriptState {
  /** The elements that have been destroyed. */
  readonly destroyed: readonly string[];
  /** The elements that have reached near death (<= 10 % of max life). */
  readonly nearDeath: readonly string[];
  /** The elements whose defenders have all been killed. */
  readonly defendersCleared: readonly string[];
  /** The key ("losing") elements that have been destroyed. */
  readonly keyElementsLost: readonly string[];
  /** Named counters: `botsKilled`, `trucksArrived`, `enemiesAlive`, ... */
  readonly counters: Readonly<Record<string, number>>;
  /**
   * True while a scripted airstrike is running.
   *
   * `Quest06Airstrike` and `Quest09Laboratories` override `elementKilled` to
   * return `[0, 0]` while the airstrike runs
   * (`quest/Quest06Airstrike.as:386-393`,
   * `quest/Quest09Laboratories.as:424-431`): the bombs award no gold and no
   * XP, and the remaining-foe counter does not move.
   */
  readonly suppressed: boolean;
}

/** The state of a quest in progress. */
export interface QuestState {
  /** The quest being played. */
  readonly questId: string;
  /** Where the quest is in its lifecycle. */
  readonly phase: QuestPhase;
  /** The chosen difficulty. */
  readonly difficulty: QuestDifficulty;
  /** Seconds since the quest was prepared. */
  readonly elapsedSeconds: number;
  /** The gold the player has earned by killing things. */
  readonly gold: number;
  /** The XP the player has earned by killing things. */
  readonly xp: number;
  /** The player's living units. Healers are excluded. */
  readonly playerUnitsAlive: number;
  /** True once the player's army has been wiped out. */
  readonly armyWipedOut: boolean;
  /** The enemy units that are still alive (the client's `remainingFoes`). */
  readonly remainingFoes: number;
  /** The scripted objective state. */
  readonly script: QuestScriptState;
  /** The quest's chapter status. */
  readonly chapter: ChapterStatus;
  /** The second at which a pending army-wipe loss fires. */
  readonly lossArmedAt: number | null;
  /** The mission timer, in seconds, or `null` when the quest has none. */
  readonly timeRemaining: number | null;
  /** Set once the quest has been resolved. */
  readonly result: 'win' | 'loss' | null;
}

/** The player affiliation of a map element. */
export type QuestAffiliation = 'self' | 'enemy' | 'neutral';

/** A map element, as the quest state machine sees it. */
export interface QuestElement {
  /** The item id. */
  readonly itemId: number;
  /** How the element is addressed: the chapter id, or `item:<id>`. */
  readonly ref: string;
  /** The affiliation the quest assigned to the element. */
  readonly affiliation: QuestAffiliation;
  /** Units count towards `remainingFoes`; buildings do not. */
  readonly isUnit: boolean;
  /** Healers are excluded from the player's living-unit count. */
  readonly isHealer?: boolean;
  /** A value above 0 means the element awards gold when it is killed. */
  readonly attack?: number;
  /** The element's `subcat_functional`; 221 is a wall. */
  readonly subcatFunctional?: number;
  /** Summoned elements award nothing at all (`quest/Quest.as:369-371`). */
  readonly summoned?: boolean;
}

/** `Constants.SUBCATFUNC_BUILDING_WALL`. */
export const SUBCATFUNC_BUILDING_WALL = 221;

/**
 * Whether the player may bring a unit of this `group_type` into the quest.
 *
 * Ported from `IsoEngine.getCurrentFilteredArmy`
 * (`core/isoengine/IsoEngine.as:3205-3214`): a unit is kept when it is *not*
 * in the excluded dictionary (or there is none) **and** it is in the included
 * dictionary (or there is none).
 *
 * Note that the client's own helper is misnamed: `AbstractQuest.isUnitExcluded`
 * (`quest/AbstractQuest.as:488-494`) returns *true* when the unit is kept, and
 * the same inverted expression is inlined in `getCurrentFilteredArmy`. The
 * behaviour is what this function implements.
 *
 * The client also has an `unitTypesIncluded` dictionary, but no quest ever
 * sets it, so only the excluded list matters.
 */
export function isUnitAllowedInQuest(groupType: string, questSpec: QuestSpec): boolean {
  const excluded = questSpec.excludedUnitGroupTypes.includes(groupType);
  return !excluded;
}

/**
 * The gold an enemy element awards when it is killed.
 *
 * Ported from `AbstractQuest.elementKilled` (`quest/AbstractQuest.as:252-265`):
 * 5 gold for anything that can attack, 0 for anything that cannot.
 */
export const GOLD_PER_ATTACKING_KILL = 5;

/**
 * The XP an enemy element awards when it is killed.
 *
 * Ported from `AbstractQuest.elementKilled` (`quest/AbstractQuest.as:252-265`):
 * `ceil(gold * 0.05)`, and at least 1 for anything that is not a wall.
 */
export function xpForKill(gold: number, subcatFunctional?: number): number {
  const xp = Math.ceil(gold * 0.05);
  if (xp === 0 && subcatFunctional !== SUBCATFUNC_BUILDING_WALL) return 1;
  return xp;
}

/** Options for `prepareQuest`. */
export interface PrepareQuestOptions {
  /** The player's army: unit id and count. */
  readonly army?: readonly { readonly unitId: number; readonly count: number }[];
  /** The difficulty the quest starts at. */
  readonly difficulty?: QuestDifficulty;
  /** Whether the player already has a rank for this quest. */
  readonly hasRank?: boolean;
  /** The stored quest variables, so the quest's chapter can be resumed. */
  readonly questVars?: Readonly<Record<string, unknown>>;
}

/**
 * Build the initial state of a quest — the client's `prepareInit`.
 *
 * Ported from `Quest.prepareInit` (`quest/Quest.as:290-319`) and
 * `AbstractQuest.prepareInit` (`quest/AbstractQuest.as:82-103`): the result
 * counters are reset, the army is captured and a fresh chapter is created.
 */
export function prepareQuest(questId: string, options: PrepareQuestOptions = {}): QuestState {
  const questSpec = getQuestSpec(questId);
  if (!questSpec) {
    throw new Error(`unknown quest id: ${questId}`);
  }
  const armySize =
    questSpec.playerUnitCountOverride ??
    (options.army ?? []).reduce((sum, entry) => sum + entry.count, 0);
  const chapter = prepareChapterStatus(
    readChapterStatus(options.questVars),
    QUEST_CHAPTER_ID,
  );
  const difficulty = options.difficulty ?? questSpec.defaultDifficulty;
  const timeRemaining =
    questSpec.timeLimitSeconds !== null && questSpec.timeLimitStartsAt === 'prepared'
      ? questSpec.timeLimitSeconds
      : null;
  return {
    questId,
    phase: 'prepared',
    difficulty,
    elapsedSeconds: 0,
    gold: 0,
    xp: 0,
    playerUnitsAlive: armySize,
    armyWipedOut: false,
    remainingFoes: 0,
    script: {
      destroyed: [],
      nearDeath: [],
      defendersCleared: [],
      keyElementsLost: [],
      counters: { ...questSpec.initialCounters },
      suppressed: false,
    },
    chapter: options.hasRank ? markChapterVisited(chapter) : chapter,
    lossArmedAt: null,
    timeRemaining,
    result: null,
  };
}

/**
 * Read a chapter status out of the stored quest variables.
 *
 * The stored value is untrusted, so anything malformed is ignored.
 */
export function readChapterStatus(
  vars: Readonly<Record<string, unknown>> | null | undefined,
): ChapterStatus | null {
  if (!vars) return null;
  const id = vars['id'];
  if (typeof id !== 'number') return null;
  const asArray = (value: unknown): number[] =>
    Array.isArray(value) ? value.filter((entry): entry is number => typeof entry === 'number') : [];
  const asStrings = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
  const status: ChapterStatus = {
    id,
    spawned: vars['spawned'] === true,
    ended: vars['ended'] === true,
    visited: vars['visited'] === true,
    activators: asArray(vars['activators']),
    boss: asArray(vars['boss']),
    treasure: asArray(vars['treasure']),
    killed: asStrings(vars['killed']),
  };
  const simpleChapter = vars['idSimpleChapter'];
  const playerLevel = vars['playerLevel'];
  const startTile = vars['startTile'];
  const extra: {
    idSimpleChapter?: number;
    playerLevel?: number;
    startTile?: QuestTile;
  } = {};
  if (typeof simpleChapter === 'number') extra.idSimpleChapter = simpleChapter;
  if (typeof playerLevel === 'number') extra.playerLevel = playerLevel;
  if (
    typeof startTile === 'object' &&
    startTile !== null &&
    typeof (startTile as { x?: unknown }).x === 'number' &&
    typeof (startTile as { y?: unknown }).y === 'number'
  ) {
    extra.startTile = {
      x: (startTile as { x: number }).x,
      y: (startTile as { y: number }).y,
    };
  }
  return { ...status, ...extra };
}

/**
 * The difficulty setter.
 *
 * Ported from `AbstractQuest.difficulty` (`quest/AbstractQuest.as:382-423`):
 * setting the difficulty re-scans the map and duplicates every enemy unit —
 * one extra copy at difficulty 2, two at difficulty 3. The setter is a
 * *mutation of the map*, not a scalar.
 *
 * `Quest13Tyrannosaurus` overrides the setter with a no-op
 * (`quest/Quest13Tyrannosaurus.as:239-247`), so its difficulty has no effect.
 *
 * The copies are placed on a free neighbouring tile, which the client finds
 * with `Base.Iso.encontrarTileProximaLibre` — a random search. A
 * server-authoritative implementation must place them from the server's seed
 * instead; this function only reports how many copies each enemy gets.
 */
export function difficultyEnemyCopies(questId: string, difficulty: QuestDifficulty): number {
  const questSpec = getQuestSpec(questId);
  if (!questSpec) return 0;
  if (questSpec.difficultyIsNoOp) return 0;
  return Math.max(0, difficulty - 1);
}

/** An enemy unit on the quest map, before scaling. */
export interface EnemyUnit {
  /** The item id of the unit. */
  readonly unitId: number;
  /** The tile the unit stands on. */
  readonly tile: QuestTile;
}

/** The result of scaling a quest map's enemy roster. */
export interface ScaledRoster {
  /** The original units. */
  readonly original: readonly EnemyUnit[];
  /** The extra copies the difficulty added. */
  readonly copies: readonly EnemyUnit[];
  /** How many copies each enemy got. */
  readonly copiesPerEnemy: number;
}

/**
 * Scale the enemy roster by the difficulty.
 *
 * The copies are *not* placed here: the client puts each copy on a free
 * neighbouring tile, chosen at random. A server implementation resolves the
 * placement from its own seed, so only the count is decided here.
 */
export function scaleEnemyRoster(
  questId: string,
  difficulty: QuestDifficulty,
  enemies: readonly EnemyUnit[],
): ScaledRoster {
  const copiesPerEnemy = difficultyEnemyCopies(questId, difficulty);
  const copies: EnemyUnit[] = [];
  for (const enemy of enemies) {
    for (let index = 0; index < copiesPerEnemy; index += 1) {
      copies.push(enemy);
    }
  }
  return { original: enemies, copies, copiesPerEnemy };
}

/**
 * The difficulty setter.
 *
 * The client's setter is a *mutation of the map*, not a scalar: it re-scans
 * `Base.Main.buildingArray` and duplicates every enemy unit
 * (`quest/AbstractQuest.as:382-423`). This function records the chosen
 * difficulty on the state; `scaleEnemyRoster` reports how many copies each
 * enemy gets, and the caller places them.
 *
 * The setter runs **once**, when the player picks a star in
 * `PopupLoadingQuest` (`popups/PopupLoadingQuest.as:132-136`), so units that
 * spawn later — the convoy waves, the airstrike planes, the kamikaze rows —
 * are never scaled.
 */
export function setQuestDifficulty(
  state: QuestState,
  difficulty: QuestDifficulty,
): QuestState {
  return { ...state, difficulty };
}

/**
 * Start the quest — the client's `Quest.start()`.
 *
 * The mission timer starts counting here, except for the weekly quest, whose
 * countdown is armed in `prepareInit` (`quest/QuestWeekly01.as:83-86`).
 */
export function startQuest(state: QuestState): QuestState {
  const questSpec = getQuestSpec(state.questId);
  if (!questSpec) throw new Error(`unknown quest id: ${state.questId}`);
  const timeRemaining =
    questSpec.timeLimitSeconds !== null && questSpec.timeLimitStartsAt === 'started'
      ? questSpec.timeLimitSeconds
      : state.timeRemaining;
  return { ...state, phase: 'started', timeRemaining };
}

/**
 * Load the quest map — the client's `mapLoaded`.
 *
 * Ported from `AbstractQuest.mapLoaded` (`quest/AbstractQuest.as:105-180`): the
 * map is walked once and every unit is classified, so the player's living
 * units and the remaining foes are known.
 */
export function loadQuestMap(state: QuestState, elements: readonly QuestElement[]): QuestState {
  let friendlyUnitsOnMap = 0;
  let remainingFoes = 0;
  let enemiesAlive = 0;
  for (const element of elements) {
    if (!element.isUnit) continue;
    if (element.affiliation === 'self') {
      // The player's own army is not part of `Base.Main.buildingArray`; only
      // the friendly units that stand on the quest map are counted here
      // (quest/AbstractQuest.as:165-175).
      if (!element.isHealer) friendlyUnitsOnMap += 1;
    } else {
      remainingFoes += 1;
    }
    if (element.affiliation === 'enemy') enemiesAlive += 1;
  }
  return {
    ...state,
    phase: 'map-loaded',
    playerUnitsAlive: state.playerUnitsAlive + friendlyUnitsOnMap,
    remainingFoes,
    // `QuestHardcore` counts every enemy *unit* on the map — not just the
    // ones in the chapter — and decrements the counter on every kill
    // (`quest/QuestHardcore.as:87-106`).
    script: {
      ...state.script,
      counters: { ...state.script.counters, enemiesAlive },
    },
  };
}

/**
 * Advance the quest clock.
 *
 * The client's timers are `flash.utils.Timer`s; here time is explicit. When
 * the mission timer reaches zero the quest is lost
 * (`quest/Quest05AssaultConvoy.as:277-278`, `quest/Quest08Rocket.as:94-96,
 * 160-169`, `quest/Quest11SaveVillages.as:159, 603-615`,
 * `quest/QuestWeekly01.as:85-86, 95-98`).
 */
export function tickQuest(state: QuestState, seconds: number): QuestState {
  if (state.phase === 'finished' || seconds <= 0) return state;
  const elapsedSeconds = state.elapsedSeconds + seconds;
  let timeRemaining = state.timeRemaining;
  let result = state.result;
  if (timeRemaining !== null) {
    timeRemaining = Math.max(0, timeRemaining - seconds);
    if (timeRemaining === 0 && result === null) {
      result = 'loss';
    }
  }
  // The client's army-wipe loss runs on a 3-second timer
  // (`quest/AbstractQuest.as:284-304`).
  if (state.lossArmedAt !== null && elapsedSeconds >= state.lossArmedAt && result === null) {
    result = 'loss';
  }
  return {
    ...state,
    elapsedSeconds,
    timeRemaining,
    result,
    phase: result === null ? state.phase : 'finished',
  };
}

/** The result of killing an element. */
export interface KillResult {
  /** The new state. */
  readonly state: QuestState;
  /** The gold the kill awarded. */
  readonly gold: number;
  /** The XP the kill awarded. */
  readonly xp: number;
}

/**
 * Kill a map element — the client's `elementKilled`.
 *
 * Ported from `AbstractQuest.elementKilled` (`quest/AbstractQuest.as:232-282`):
 *
 * - a key element is destroyed → the quest is lost;
 * - a friendly unit dies → the player's living-unit count drops;
 * - an enemy dies → 5 gold if it can attack, plus `ceil(gold * 0.05)` XP (at
 *   least 1 XP unless it is a wall), and the remaining-foe counter drops;
 * - when the player's army is wiped out the 3-second loss timer is armed,
 *   unless the quest has key elements and does not set
 *   `alwaysEndIfMyUnitsDie`.
 */
export function killQuestElement(state: QuestState, element: QuestElement): KillResult {
  const questSpec = getQuestSpec(state.questId);
  if (!questSpec) throw new Error(`unknown quest id: ${state.questId}`);

  let gold = 0;
  let xp = 0;
  let playerUnitsAlive = state.playerUnitsAlive;
  let remainingFoes = state.remainingFoes;
  let script = state.script;
  let result = state.result;

  // Every destroyed element is recorded. The chapter's `onKill` fires from
  // the element's own `killed` signal (chapters/Chapter.as:939-942), so the
  // objective advances even when the quest's accounting is skipped.
  if (!script.destroyed.includes(element.ref)) {
    script = { ...script, destroyed: [...script.destroyed, element.ref] };
  }

  // A summoned element (`quest/Quest.as:369-371`) and any element that dies
  // during a scripted airstrike (`quest/Quest06Airstrike.as:386-393`,
  // `quest/Quest09Laboratories.as:424-431`) award nothing and do not move
  // the counters.
  if (element.summoned || script.suppressed) {
    return { state: { ...state, script }, gold: 0, xp: 0 };
  }

  const isKeyElement = questSpec.keyElementRefs.includes(element.ref);
  if (isKeyElement) {
    // `defeat()` is called before the affiliation switch, so the kill awards
    // nothing (`quest/AbstractQuest.as:237-242`).
    script = {
      ...script,
      keyElementsLost: [...script.keyElementsLost, element.ref],
    };
    result = result ?? 'loss';
  }

  if (element.affiliation === 'self') {
    if (!element.isHealer) playerUnitsAlive = Math.max(0, playerUnitsAlive - 1);
  } else if (element.affiliation === 'enemy') {
    gold = (element.attack ?? 0) > 0 ? GOLD_PER_ATTACKING_KILL : 0;
    xp = xpForKill(gold, element.subcatFunctional);
    if (element.isUnit) {
      remainingFoes = Math.max(0, remainingFoes - 1);
      // `QuestHardcore` keeps its own counter of the enemy units that are
      // still alive and decrements it on every kill
      // (`quest/QuestHardcore.as:110-123`).
      if ('enemiesAlive' in script.counters) {
        script = {
          ...script,
          counters: {
            ...script.counters,
            enemiesAlive: Math.max(0, (script.counters['enemiesAlive'] ?? 0) - 1),
          },
        };
      }
    }
  }

  const armyWipedOut = state.armyWipedOut || playerUnitsAlive === 0;
  let lossArmedAt = state.lossArmedAt;
  if (armyWipedOut && questSpec.armyWipeEndsQuest && lossArmedAt === null) {
    if (questSpec.armyWipeResolvesImmediately) {
      // `Quest11SaveVillages` overrides `prepareQuestEnd` to run the airstrike
      // at once (`quest/Quest11SaveVillages.as:388-391`). The airstrike wins
      // when every civilian is already out of the villages.
      const workers = script.counters['workersInVillages'] ?? 0;
      result = result ?? (workers <= 0 ? 'win' : 'loss');
    } else {
      lossArmedAt = state.elapsedSeconds + 3;
    }
  }

  return {
    state: {
      ...state,
      gold: state.gold + gold,
      xp: state.xp + xp,
      playerUnitsAlive,
      armyWipedOut,
      remainingFoes,
      script,
      lossArmedAt,
      result,
      phase: result === null ? state.phase : 'finished',
    },
    gold,
    xp,
  };
}

/**
 * Report that an element reached near death (10 % of max life).
 *
 * The client's `onNearDeath` fires when an element's health crosses the
 * threshold (`core/isoengine/IsoFightingElement.as:469-472`). It is the
 * trigger of several quest objectives.
 */
export function nearDeathQuestElement(state: QuestState, ref: string): QuestState {
  if (state.script.nearDeath.includes(ref)) return state;
  return {
    ...state,
    script: { ...state.script, nearDeath: [...state.script.nearDeath, ref] },
  };
}

/**
 * Report that every defender of an element is dead.
 *
 * The client's `onKillDefenders` fires when the element has no living
 * defenders left (`chapters/Chapter.as:770-779`).
 */
export function defendersClearedQuestElement(state: QuestState, ref: string): QuestState {
  if (state.script.defendersCleared.includes(ref)) return state;
  return {
    ...state,
    script: { ...state.script, defendersCleared: [...state.script.defendersCleared, ref] },
  };
}

/**
 * Arm or disarm the scripted airstrike.
 *
 * While it is armed, every kill awards no gold and no XP and does not move
 * the remaining-foe counter — the client overrides `elementKilled` for
 * exactly that reason (`quest/Quest06Airstrike.as:386-393`,
 * `quest/Quest09Laboratories.as:424-431`).
 */
export function suppressQuestKills(state: QuestState, suppressed: boolean): QuestState {
  return { ...state, script: { ...state.script, suppressed } };
}

/** Set a named counter. */
export function setQuestCounter(state: QuestState, name: string, value: number): QuestState {
  return {
    ...state,
    script: { ...state.script, counters: { ...state.script.counters, [name]: value } },
  };
}

/** Add to a named counter. */
export function addQuestCounter(state: QuestState, name: string, delta: number): QuestState {
  const current = state.script.counters[name] ?? 0;
  return setQuestCounter(state, name, current + delta);
}

/**
 * Whether the quest's win condition holds.
 *
 * Pure predicate over the state; it does not mutate anything.
 */
export function isQuestVictory(state: QuestState): boolean {
  const questSpec = getQuestSpec(state.questId);
  if (!questSpec) return false;
  return evaluateWin(questSpec.win, state.script);
}

/**
 * Whether the quest's loss conditions hold.
 *
 * Pure predicate over the state; it does not mutate anything.
 */
export function isQuestDefeat(state: QuestState): boolean {
  const questSpec = getQuestSpec(state.questId);
  if (!questSpec) return false;
  for (const condition of questSpec.defeat) {
    if (evaluateFail(condition, state)) return true;
  }
  return questSpec.customDefeat ? questSpec.customDefeat(state) : false;
}

function evaluateWin(condition: QuestWinCondition, script: QuestScriptState): boolean {
  switch (condition.kind) {
    case 'destroyAll':
      return condition.elements.every((ref) => script.destroyed.includes(ref));
    case 'nearDeathAll':
      return condition.elements.every((ref) => script.nearDeath.includes(ref));
    case 'defendersClearedAll':
      return condition.elements.every((ref) => script.defendersCleared.includes(ref));
    case 'countersAtLeast':
      return condition.counters.every(
        (counter) => (script.counters[counter.name] ?? 0) >= counter.atLeast,
      );
    case 'countersZero':
      return condition.counters.every(
        (counter) => counter in script.counters && (script.counters[counter] ?? 0) <= 0,
      );
    case 'all':
      return condition.of.every((inner) => evaluateWin(inner, script));
  }
}

function evaluateFail(condition: QuestFailCondition, state: QuestState): boolean {
  switch (condition.kind) {
    case 'keyElementDestroyed':
      return state.script.keyElementsLost.length > 0;
    case 'timerExpired':
      return state.timeRemaining !== null && state.timeRemaining <= 0;
    case 'armyWipedOut':
      return state.armyWipedOut;
    case 'counterAtMost':
      return (
        condition.counter in state.script.counters &&
        (state.script.counters[condition.counter] ?? 0) <= condition.atMost
      );
  }
}

// ---------------------------------------------------------------------------
// Rewards
// ---------------------------------------------------------------------------

/** One reward entry. */
export interface QuestReward {
  readonly key: QuestRewardKey;
  readonly amount: number;
}

/**
 * The rewards of a finished quest.
 *
 * Ported from `AbstractQuest.sendResults` (`quest/AbstractQuest.as:430-461`):
 * the gold and the XP the player earned are always granted; the static win
 * reward row is granted **only on a win**.
 *
 * On a win the client's reward list also carries an extra XP entry for the
 * gold row: `min(round(gold / 4), exp_required / 3)`. The client does not
 * floor that value; a server that grants whole resources must decide what to
 * do with the fraction.
 */
export function questRewards(
  questSpec: QuestSpec,
  gold: number,
  xp: number,
  win: boolean,
  context: { readonly expRequired: number },
): QuestReward[] {
  const rewards: QuestReward[] = [
    { key: 'g', amount: gold },
    { key: 'x', amount: xp },
  ];
  if (!win) return rewards;
  for (const key of REWARD_KEY_ORDER) {
    const value = questSpec.reward[key];
    if (value === undefined) continue;
    if (key === 'g') {
      rewards.push({
        key: 'x',
        amount: Math.min(Math.round(value / 4), context.expRequired / 3),
      });
    }
    rewards.push({ key, amount: value });
  }
  return rewards;
}

/**
 * The XP a finished quest grants.
 *
 * Ported from `Quest.end` (`quest/Quest.as:412-415`): the XP is clamped to
 * half the gold gained. The client's setter truncates the value to an int, so
 * the clamp is `floor(gold / 2)`.
 */
export function clampQuestXp(gold: number, xp: number): number {
  const cap = Math.floor(gold / 2);
  return xp > cap ? cap : xp;
}

/**
 * The weekly quest's reward: 1 cash per gun bot killed.
 *
 * Ported from `popups/PopupWeeklyQuestFinished.as:24, 100`: the static row is
 * empty (`globals.REWARDS_QUESTS[0] = {}`) and the whole reward is
 * `RewardResource(COST_CASH, botsKilled)`.
 */
export const WEEKLY_CASH_PER_BOT = 1;

/** The weekly quest's end reasons (`quest/QuestWeekly01.as:24-30`). */
export const WEEKLY_END_REASON = {
  allBotsKilled: 'allBotsKilled',
  timerEnd: 'timerEnd',
  armyKilled: 'armyKilled',
  playerLeft: 'playerLeft',
} as const;

/** One of the weekly quest's end reasons. */
export type WeeklyEndReason = (typeof WEEKLY_END_REASON)[keyof typeof WEEKLY_END_REASON];

/** The result of a finished quest. */
export interface QuestOutcome {
  /** The quest id. */
  readonly questId: string;
  /** Whether the player won. */
  readonly win: boolean;
  /** The difficulty the quest was played at. */
  readonly difficulty: QuestDifficulty;
  /** How long the quest took, in seconds. */
  readonly durationSeconds: number;
  /** The gold the player earned. */
  readonly gold: number;
  /** The XP the player earned, after the clamp. */
  readonly xp: number;
  /** The reward list. */
  readonly rewards: readonly QuestReward[];
  /** The weekly quest's end reason, when it is the weekly quest. */
  readonly weeklyReason?: WeeklyEndReason;
}

/**
 * Finish the quest — the client's `Quest.end()` plus `sendResults()`.
 *
 * The XP is clamped to half the gold (`quest/Quest.as:412-415`) and the
 * reward list is built (`quest/AbstractQuest.as:443-458`).
 */
export function finishQuest(
  state: QuestState,
  win: boolean,
  context: { readonly expRequired: number },
): QuestOutcome {
  const questSpec = getQuestSpec(state.questId);
  if (!questSpec) throw new Error(`unknown quest id: ${state.questId}`);
  const xp = clampQuestXp(state.gold, state.xp);
  const rewards = questRewards(questSpec, state.gold, xp, win, context);
  const outcome: QuestOutcome = {
    questId: state.questId,
    win,
    difficulty: state.difficulty,
    durationSeconds: Math.round(state.elapsedSeconds),
    gold: state.gold,
    xp,
    rewards,
  };
  if (state.questId === QUEST_ID_WEEKLY_01) {
    const botsKilled = state.script.counters['botsKilled'] ?? 0;
    const reason: WeeklyEndReason = win
      ? WEEKLY_END_REASON.allBotsKilled
      : state.timeRemaining === 0
        ? WEEKLY_END_REASON.timerEnd
        : WEEKLY_END_REASON.armyKilled;
    return {
      ...outcome,
      rewards: [
        { key: 'g', amount: state.gold },
        { key: 'x', amount: xp },
        { key: 'c', amount: botsKilled * WEEKLY_CASH_PER_BOT },
      ],
      weeklyReason: reason,
    };
  }
  return outcome;
}

// ---------------------------------------------------------------------------
// The once-only award
// ---------------------------------------------------------------------------

/**
 * One entry of the player's army, as the client's counted array holds it.
 *
 * The client's array entries are `[itemId, init, killed, recovered]`
 * (`battle/Assault.as:106-110`): `sent` is `FIELD_INIT`, `killed` is
 * `FIELD_KILLED` and `recovered` is `FIELD_RECOVERED`.
 */
export interface QuestArmyEntry {
  readonly unitId: number;
  /** How many of this unit went to battle. */
  readonly sent: number;
  /** How many of this unit died. */
  readonly killed: number;
  /** How many of this unit come back. */
  readonly recovered: number;
}

/** The result of recovering the army. */
export interface RecoveryResult {
  /** The army, with the `recovered` counts filled in. */
  readonly army: readonly QuestArmyEntry[];
  /** How many units were lost for good. */
  readonly lost: number;
  /** How many units come back. */
  readonly recovered: number;
}

/**
 * Recover the units the player lost in the quest.
 *
 * Ported from `Quest.recoverUnits` (`quest/Quest.as:452-481`): every killed
 * unit is recovered first, then
 * `lost = totalKilled - ceil(totalKilled * percent / 100)` units are taken
 * away again, at random, with **at most 50 attempts**. The client uses
 * `Math.random()`; here the choice comes from the caller's seeded generator,
 * so the result is reproducible.
 *
 * The client recovers the units **once** per quest: `Quest.end()` guards the
 * call with the `recovered` flag (`quest/Quest.as:416-429`), because `end()`
 * runs again when the result is sent.
 */
export function recoverQuestUnits(
  army: readonly QuestArmyEntry[],
  percent: number,
  random: Random,
): RecoveryResult {
  interface Mutable {
    unitId: number;
    sent: number;
    killed: number;
    recovered: number;
  }
  const entries: Mutable[] = army.map((entry) => ({
    unitId: entry.unitId,
    sent: entry.sent,
    killed: entry.killed,
    recovered: entry.killed,
  }));
  const totalKilled = entries.reduce((sum, entry) => sum + entry.killed, 0);
  const target = totalKilled - Math.ceil(totalKilled * (percent / 100));
  let removed = 0;
  let attempts = 0;
  while (removed < target && attempts < 50 && entries.length > 0) {
    const index = Math.floor(random.next() * entries.length);
    const entry = entries[index];
    // `Utils.RemoveFromCountedArray` fails when the entry has nothing left
    // to recover, and the attempt is then wasted.
    if (entry && entry.recovered > 0) {
      entry.recovered -= 1;
      removed += 1;
    }
    attempts += 1;
  }
  return {
    army: entries.map((entry) => ({ ...entry })),
    lost: removed,
    recovered: totalKilled - removed,
  };
}

/**
 * The player's quest progress.
 *
 * `ranks` is the client's `Base.Player.questsRank`
 * (`managers/PlayerStatus.as:564-578`), keyed by the quest's **play index**,
 * and it holds the best difficulty reached. `awarded` records the quests whose
 * completion reward has already been granted.
 */
export interface QuestProgress {
  readonly ranks: Readonly<Record<string, number>>;
  readonly awarded: readonly string[];
}

/** An empty progress record. */
export function emptyQuestProgress(): QuestProgress {
  return { ranks: {}, awarded: [] };
}

/** The outcome of awarding a quest. */
export interface QuestAward {
  /** The rewards that were granted. Empty when the quest was already awarded. */
  readonly rewards: readonly QuestReward[];
  /** False when the quest had already been awarded and nothing was granted. */
  readonly awarded: boolean;
  /** The quest's rank after the award. */
  readonly rank: number;
}

/**
 * Award a finished quest.
 *
 * The rank follows `Base.Player.updateQuestRank`
 * (`managers/PlayerStatus.as:564-578`): it keeps the **highest** difficulty
 * the player has reached, and it is only updated on a win
 * (`quest/AbstractQuest.as:445-448`).
 *
 * The reward itself is granted **once per quest**. The client has no such
 * check — it re-grants the static row on every win — but it does treat a
 * quest with a rank as *done*: `GoalCompleteQuest` short-circuits when
 * `Base.Player.questsRank[questIds.indexOf(questId)]` already exists
 * (`core/goals/GoalCompleteQuest.as:28-34`), and `AbstractQuest.prepareInit`
 * marks the chapter as visited in the same case
 * (`quest/AbstractQuest.as:98-101`). A server-authoritative implementation
 * must not let a replayed quest pay out twice
 * (`AGENTS.md` → *Architecture Non-Negotiables* #3).
 */
export function awardQuest(
  progress: QuestProgress,
  outcome: QuestOutcome,
): { readonly progress: QuestProgress; readonly award: QuestAward } {
  const questSpec = getQuestSpec(outcome.questId);
  if (!questSpec) throw new Error(`unknown quest id: ${outcome.questId}`);
  const rankKey = String(questSpec.playIndex);
  const previousRank = progress.ranks[rankKey] ?? 0;
  const rank = outcome.win ? Math.max(previousRank, outcome.difficulty) : previousRank;
  const ranks = { ...progress.ranks, [rankKey]: rank };

  if (progress.awarded.includes(outcome.questId)) {
    return {
      progress: { ranks, awarded: progress.awarded },
      award: { rewards: [], awarded: false, rank },
    };
  }

  return {
    progress: { ranks, awarded: [...progress.awarded, outcome.questId] },
    award: {
      rewards: outcome.rewards,
      awarded: true,
      rank,
    },
  };
}
