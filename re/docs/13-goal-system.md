# The Goal System — Lifecycle, Goal Types and Id Reconciliation

**Roadmap task B5 (goal specification).** The goal system is the client's
"missions" panel: a rolling set of at most five objectives that the player
completes for gold. 34 goal classes, 134 registered goal ids, and a 91-entry
goal table in the 2012 upstream config that does **not** actually describe this
game. This document reduces all of it to an implementable specification.

| | |
|---|---|
| **Source** | `core/goals/` in the decompiled `Basesec_1.5.4.swf` (31 classes) + `core/goals/rewards/` (3 classes), `managers/GoalManager.as`, `popups/PopupGoals.as`, `popups/PopupGoalComplete.as`, `commands/CmdSetGoals.as`, `commands/CmdCompleteGoal.as`, cross-referenced with `core/Constants.as`, `core/isoengine/PropertyManager.as`, `chapters/ChapterManager.as`, `quest/Quest.as` |
| **Data** | [`../data/goals.json`](../data/goals.json) — 34 goal types, 134 goals, the id reconciliation |
| **Related** | [`12-quest-system.md`](12-quest-system.md) (the assault missions), [`03-commands-quests-economy.md`](03-commands-quests-economy.md) (wire protocol), [`04-python-server-and-data.md`](04-python-server-and-data.md) (the upstream Python server) |

> All line references are to `.work/as/basesec/scripts/`. Nothing here is
> inferred from the upstream Python server; where the client and the upstream
> disagree, the client wins (`AGENTS.md` → *Architecture Non-Negotiables* #2).
> Where a completion condition cannot be determined from the code it is marked
> **UNVERIFIED** (§11) rather than guessed.

---

**Machine-readable companion:** `re/data/goals.json`
(34 goal types, 134 registered goals, full id reconciliation).

**Scope note:** this document describes the *client-side* goal system. The
upstream Python server does **not** implement any goal logic — it only stores
the progress array that the client pushes to it (§4) and prints a title from a
foreign goal table (§8). Everything in §10 is therefore a specification to
*build*, not a description of existing behaviour.

---

## 1. Where the code lives

| Path (under `.work/as/basesec/scripts/`) | Role |
| --- | --- |
| `core/goals/AbstractGoal.as` | Base class: counters, signals, persistence, reward delivery |
| `core/goals/Goal.as` | Interface that declares the contract |
| `core/goals/GoalAction.as` … `core/goals/GoalVisitNeighbour.as` | 27 concrete goal types |
| `core/goals/GoalContainer.as` | Composite goal (sub-goal aggregation) — never instantiated |
| `core/goals/GoalLiterals.as` | Holder for the 6 localized strings of a goal |
| `core/goals/TranslationGoals.as` | The 140-entry text table, keyed by goal id |
| `core/goals/rewards/AbstractReward.as` | Reward base class (a `Sprite`) |
| `core/goals/rewards/RewardElement.as` | Reward that grants a building/unit |
| `core/goals/rewards/RewardResource.as` | Reward that grants a resource amount |
| `managers/GoalManager.as` | Registers all 134 goals, owns activation and completion |
| `popups/PopupGoals.as` | The goal box UI (3 map icons + a scrolling list of 5) |
| `popups/PopupGoalComplete.as` | The "Goal achieved!" popup; calls `deliverReward()` |
| `commands/CmdSetGoals.as`, `commands/CmdCompleteGoal.as` | The two goal wire commands |

`core/goals/` contains 31 classes and `core/goals/rewards/` 3 — **34 classes in
total**. Of those, **27 are concrete, registerable goal types**; the remaining
7 are the base class, the interface, two data holders and the three reward
classes.

---

## 2. Object model

```
Goal (interface, core/goals/Goal.as)
└── AbstractGoal (core/goals/AbstractGoal.as)
    ├── GoalAction, GoalAddAllies, GoalAlliesMarketTrade,
    │   GoalAssistNeighbourBuilding, GoalAttackPlayer, GoalBuildId,
    │   GoalBuildProperty, GoalCollect, GoalCompleteChapter,
    │   GoalCompleteQuest, GoalContainer, GoalDailyBouns, GoalDoubleClick,
    │   GoalExpand, GoalHarbor, GoalMarketTrade, GoalModifyPlayerStats,
    │   GoalMove, GoalOpenPopup, GoalPopUnit, GoalPushUnit,
    │   GoalReachPopulation, GoalSelectTime, GoalSocialBuildingOpened,
    │   GoalSpy, GoalStoreItem, GoalVisitNeighbour
```

`AbstractGoal` state (`core/goals/AbstractGoal.as:17-37`):

| Field | Meaning |
| --- | --- |
| `_id` | The goal id (the key into `TranslationGoals` and into the server's `privateState.goals`) |
| `_literals` | The six localized strings for this id, from `TranslationGoals.getLiterals(id)` |
| `_steps` | Number of steps required; default **1** (`AbstractGoal.as:45`) |
| `_currentStep` | Progress counter; default **0** (`AbstractGoal.as:44`) |
| `_active` | Whether the goal is currently listening for its event |
| `_rewards` | `Vector.<AbstractReward>` — assigned by `GoalManager.addGoal` |
| `_visited` | Whether the player has opened the goal's info popup at least once |
| `progress` | `Signal(Goal)` fired on every progress change |
| `complete` | `Signal(Goal)` fired once when the goal is finished |

`isCompleted()` is `currentStep >= numSteps` (`AbstractGoal.as:89-92`).

---

## 3. Lifecycle

### 3.1 Creation

`GoalManager`'s constructor registers all 134 goals in one long sequence
(`managers/GoalManager.as:49-315`). Each call has the shape

```as3
this.addGoal(new <GoalType>(<id>, <params...>), hosts[ihost++], 10);
```

`addGoal(goal, host, reward, index = -1)` (`GoalManager.as:409-442`):

1. pushes the goal onto `goalList` (or splices it at `index`),
2. if `GoalManager.initData[goal.id] != null` it calls `goal.initialize(savedState)`,
3. assigns the **host** character (the nine `CharacterManager.getFriend(...)` portraits are
   cycled round-robin so that each goal has a different speaker),
4. parses the third argument into a `Vector.<AbstractReward>` and assigns it.

`parseReward` (`GoalManager.as:444-464`):

| Argument | Result |
| --- | --- |
| `int` | `new RewardResource(Constants.COST_GOLD, value)` |
| `AbstractReward` | used as-is |
| `Object` | one `RewardResource` **per key** (the loop overwrites `_loc2_` on every iteration, so only the last key survives — a latent bug, never triggered here) |

> **Every one of the 134 goals is registered with the literal `10`**, so every goal
> rewards **10 gold**. `re/data/goals.json` records this as
> `reward: { gold: 10, cash: 0, xp: 0, items: [] }` for every goal.

### 3.2 Activation

`GoalManager.checkAllGoals()` (`GoalManager.as:481-505`) is called once the map
is initialised (`GoalManager.as:317-327`, deferred through
`Base.Main.sigMapaInit` if the map is not ready yet). It walks `goalList` and:

* skips goals that are already complete,
* calls `activate()` on goals that are not active,
* calls `checkGoalCompleted(goal)` — which completes goals that are already
  satisfied at activation time (e.g. a quest that was finished in a previous
  session),
* for goals still incomplete, subscribes `completeGoal` to the goal's `complete`
  signal.

The loop stops after `Base.Items.globals.NUM_ACTIVE_MISSIONS` incomplete goals
have been seen — **`NUM_ACTIVE_MISSIONS` is `5`** in `config/main.json`. That
is why the goal box shows 3 icons on the map and a list of 5
(`popups/PopupGoals.as:330`, `:564`).

`activate()` is where each concrete goal subscribes to its event source
(`Base.Iso.elementBuilt`, `Base.Iso.elemCollected`, `Assault.attackEnd`, …).
`deactivate()` unsubscribes and clears the `progress` signal
(`AbstractGoal.as:115-119`).

### 3.3 Tracking

Every concrete goal follows the same shape:

```as3
private function onEvent(payload) : void
{
   if (<match>) {
      ++_currentStep;
      checkComplete();
      goalProgress();
   }
}
```

* `checkComplete()` (`AbstractGoal.as:48-58`) — if `isCompleted()`, dispatch
  `complete`, `save()` the state and `deactivate()` the goal.
* `goalProgress()` (`AbstractGoal.as:60-67`) — if `currentStep < numSteps`,
  dispatch `progress` and `save()`.

So **progress is persisted on every single increment**, one `set_goals` command
per event.

### 3.4 Completion

`GoalManager.completeGoal(goal)` (`GoalManager.as:516-524`):

1. opens `PopupGoalComplete`, whose constructor calls `goal.deliverReward()`,
2. calls `checkAllGoals()` again — this activates the next goal(s),
3. refreshes the goal box UI.

`AbstractGoal.deliverReward()` (`AbstractGoal.as:130-138`):

```as3
for each (r in this.rewards) r.deliver();
Base.Commands.queueCommand(new CmdCompleteGoal(this.id, this.rewards));
```

`CmdCompleteGoal` (`commands/CmdCompleteGoal.as:9-23`) pushes the goal id and
then calls `setResource(amount, id)` for every `RewardResource`, which adds the
amount to the command's resource-variation vector. The reward therefore travels
as a **resource delta attached to the `complete_goal` command**, not as a
separate grant.

### 3.5 The "visited" flag and the popup

`PopupGoals.launchGoal` (`popups/PopupGoals.as:245-305`):

* If the goal has **not** been visited, the goal's `INTRO` literal is shown in a
  `SpeakerBox`, `visited` is set to `true` and saved.
* Otherwise the `DESCRIPTION` / `INSTRUCTIONS` / `HINT` panel is shown.
* When that panel is closed, `currentGoal.onPopupclosed()` is called
  (`PopupGoals.as:828`, `:846`, `:957`).

`onPopupclosed()` is overridden by exactly three goals:

| Goal | Effect of closing the info popup |
| --- | --- |
| `GoalAddAllies` (id 85) | Opens the Facebook invite flow (`Base.Main.gotoInvite()`) **and completes the goal** |
| `GoalCompleteChapter` (id 17 only) | Spawns the chapter briefing (`MapInitializer.doSpawnChapter`) and opens `PopupMissionInfo` |
| `GoalHarbor` (id 26) | Spawns 12 `ID_UNIT_UN_ALLIED_1` units next to the small harbour (queued as `CmdBuy`) and plays the first-mission cutscene |

### 3.6 Reset

`resetGoal()` sets `_currentStep = 0`, clears `visited` and saves
(`AbstractGoal.as:103-108`). `finish()` sets `_currentStep = _steps` and saves
(`AbstractGoal.as:231-235`). Both are reachable only from the admin panel
(`fg`, `fgid`, `rg`, `pg` commands, `GoalManager.as:43-46`).

---

## 4. Persistence and wire format

### 4.1 Client → server

`AbstractGoal.save()` (`AbstractGoal.as:237-240`) queues

```as3
Base.Commands.queueCommand(
    new CmdSetGoals(this.id, [this.visited ? 1 : 0, this.currentStep]), true);
```

which serialises to the command `set_goals` with the arguments
`<goalId>, "<json array>"` (`commands/CmdSetGoals.as:8-12`); the trailing `true`
is the `queueCommand` "immediate" flag, not a third goal argument. The JSON
array is `[visited, currentStep]`.

### 4.2 Server → client

`GoalManager.initData` is set from the player payload:
`GoalManager.initData = param1.privateState.goals;`
(`managers/PlayerStatus.as:321`). `AbstractGoal.initialize()`
(`AbstractGoal.as:218-229`) reads the array back:

```as3
this.visited = param1[0] == 1;
this._currentStep = parseInt(param1[1]);
```

The upstream server stores this as a **sparse array indexed by goal id**,
padded with `None` as needed (`upstream/socialwarriors/engine.py:96-100`):

```python
def set_goals(privateState: dict, goal: int, progress: list):
    goals = privateState["goals"]
    while goal >= len(goals):
        goals.append(None)
    goals[goal] = progress
```

### 4.3 The `complete_goal` command

`commands/CmdCompleteGoal.as` emits the command name `complete_goal`, the goal
id, and — through `setResource` — the reward as a resource variation
(+10 gold for every goal in this client). The upstream handler for
`complete_goal` (`upstream/socialwarriors/command.py:76-79`) does **nothing but
print**; the reward is granted by the generic resource application that the
command's resource variation triggers.

### 4.4 Server-supplied goal text

`GameDataManager.load` accepts an optional `translation_goals` object
(`managers/GameDataManager.as:143-146`). It is stored in
`GameDataManager.translationGoals` but **never read anywhere else in the
decompiled client** — the effective goal text always comes from the compiled-in
`TranslationGoals` table.

---

## 5. The 34 goal types

`Steps` is the number of steps the goal requires. `Instances` is the number of
goals of that type registered in `GoalManager`.

| # | Type | Trigger | Progress metric | Completion | Steps | Instances |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `AbstractGoal` | *(base class — not a goal)* | `_currentStep` / `_steps` | `_currentStep >= _steps`; dispatches `complete`, saves, deactivates | — | base of 27 |
| 2 | `Goal` | *(interface — not a goal)* | — | — | — | 0 |
| 3 | `GoalAction` | `Base.Main.actionTriggered` (action id) | count of matching action events | `_currentStep >= _steps` | 8 (goal 6 = zoom) | 1 |
| 4 | `GoalAddAllies` | goal-info popup closed | binary | popup closed → step = 1 | 1 | 1 |
| 5 | `GoalAlliesMarketTrade` | `Base.Iso.alliesMarketTrade` | cumulative resource received from the Allies Market | *intended:* all requested amounts collected. *actual:* first collection always completes it (bug, §9) | 1 | 1 |
| 6 | `GoalAssistNeighbourBuilding` | `Base.Iso.neighbourBuildingAssisted` | count of assist events | `_currentStep >= _steps` | 5 | 1 |
| 7 | `GoalAttackPlayer` | `Assault.attackEnd` | count of qualifying assaults | `_currentStep >= numAttacks`, with voluntary / victory / friend filters | 1, 1, 3 | 3 |
| 8 | `GoalBuildId` | `Base.Iso.elementBuilt` (buildings **and** trained units) | count of built elements whose item id is in the list | `_currentStep >= _steps` | 1–20 | 68 |
| 9 | `GoalBuildProperty` | `Base.Iso.elementBuilt` | count of built elements with an item property | `_currentStep >= _steps` | 1–8 | 5 |
| 10 | `GoalCollect` | `Base.Iso.elemCollected` | count of collects matching property + `collect_type` | `_currentStep >= _steps` | 1–10 | 9 |
| 11 | `GoalCompleteChapter` | `ChapterManager.chapterFinished`, or `currentQuestId > chapterId` at activation | binary | dispatched chapter id == goal chapter id | 1 | 8 |
| 12 | `GoalCompleteQuest` | `Quest.questEnd`, or `questsRank[questIndex] != undefined` at activation | binary | quest id matches, `difficulty >= minDifficulty`, and won when `winRequired` | 1 | 11 |
| 13 | `GoalContainer` | *(composite — never instantiated)* | sum of sub-goal steps | **all** sub-goals completed | — | 0 |
| 14 | `GoalDailyBouns` | `Base.Iso.dailyBounsWon` | count of daily-bonus claims | `_currentStep >= day` (seeded at 1) | 3 | 1 |
| 15 | `GoalDoubleClick` | `Base.Iso.doubleClick` | count of double-clicks | `_currentStep >= 1` | 1 | 1 |
| 16 | `GoalExpand` | `Base.Iso.tilePurchased` | count of bought map tiles | `_currentStep >= _steps` | 1 | 1 |
| 17 | `GoalHarbor` | `Quest.questEnd`, or `questsRank[1] != undefined` at activation (index 1 of `Quest.questIds` = `QUEST_01_BAZOOKA`) | binary | **any** quest end completes it | 1 | 1 |
| 18 | `GoalLiterals` | *(data holder — not a goal)* | — | — | — | 0 |
| 19 | `GoalMarketTrade` | `Base.Iso.marketTrade` | per-resource cumulative traded volume, sign-aware | every requested amount traded in the right direction | 1 | 3 |
| 20 | `GoalModifyPlayerStats` | `Base.Resources.playerStatsModified` | per-resource cumulative delta | `statsAlreadyModified >= statsLength` | 1 | 1 |
| 21 | `GoalMove` | `Base.Iso.buildingMoved` | count of moved buildings with a property | `_currentStep >= _steps` | 1 | 1 |
| 22 | `GoalOpenPopup` | `Base.PopUp.popupOpened` | binary | opened popup class == goal popup class | 1 | 2 |
| 23 | `GoalPopUnit` | `Base.Iso.unitPopped` | count of units removed from a matching building | `_currentStep >= _steps` | 1 | 1 |
| 24 | `GoalPushUnit` | `Base.Iso.unitPushed` | count of units placed into a matching building | `_currentStep >= _steps` | 1 | 6 |
| 25 | `GoalReachPopulation` | `Base.Player.populationModified` | **absolute** current population (not a counter) | `population >= target`; only updated in `GAME_MODE_NORMAL` | 40 | 1 |
| 26 | `GoalSelectTime` | `Base.Iso.timeSelected` | count of production-time selections on a matching depot | `_currentStep >= _steps` | 1 | 3 |
| 27 | `GoalSocialBuildingOpened` | `Base.Iso.socialBuildingOpened` | binary | opened building id == goal building id | 1 | 1 |
| 28 | `GoalSpy` | `Assault.spyEnd` | count of completed spy operations | `_currentStep >= _steps` | 1 | 1 |
| 29 | `GoalStoreItem` | `Base.Iso.itemStored` | count of stored items matching property/id | `_currentStep >= _steps` | 1 | 1 |
| 30 | `GoalVisitNeighbour` | `Base.Iso.neighbourVisited` | count of visited neighbours | visited id is in the supplied list (else every visit counts) | 1 | 1 |
| 31 | `TranslationGoals` | *(static text table — not a goal)* | — | — | — | 0 |
| 32 | `rewards/AbstractReward` | *(reward base — not a goal)* | — | — | — | 0 |
| 33 | `rewards/RewardElement` | *(reward: grants a building/unit into storage)* | — | — | — | 0 |
| 34 | `rewards/RewardResource` | *(reward: grants a resource amount)* | — | — | — | 0 |

### 5.1 Match rules that a server must reproduce

* **Ownership.** `GoalBuildId`, `GoalBuildProperty`, `GoalPushUnit`,
  `GoalPopUnit` and `GoalMove` all require `PlayerID == Constants.PLAYER_SELF`.
  `GoalCollect` does **not** check the owner.
* **Item properties** come from `core/isoengine/PropertyManager.as`:
  `resource`, `depot`, `farm`, `hq`, `tower`, `wall`, `decoration`, `bunker`,
  `worker`, `ft_ground`, …
* **Resource codes** come from `core/Constants.as:1730-1752`:
  `g` gold, `c` cash, `w` wood, `o` oil, `s` steel, `x` xp, `m` mana, `e` energy
  (plus the non-wallet codes `ds`, `de`, `t`, `h`, `abs`, `zz`).
  The wire order of the wallet vector is fixed by
  `commands/Command.as:8-22` — `RESOURCE_ENERGY = 0`, `RESOURCE_XP = 1`,
  `RESOURCE_GOLD = 2`, `RESOURCE_WOOD = 3`, `RESOURCE_OIL = 4`,
  `RESOURCE_STEEL = 5`, `RESOURCE_CASH = 6`, `RESOURCE_MANA = 7` — i.e. exactly
  the project's 8-slot vector `[energy, xp, gold, wood, oil, steel, cash, mana]`.
* **Collect type.** `GoalCollect` and `GoalSelectTime` compare
  `building.collect_type` against the resource code, and `GoalSelectTime`
  additionally requires `building.loaded.attrs.cp >= timeIdx`
  (`core/goals/GoalSelectTime.as:39`).
* **`updateOnActivate`.** `GoalBuildId` re-scans the buildings already on the
  map when it activates if the flag is set, **or** if any of the target items is
  a depot, an HQ, or has `building_limit_same_id > 0`
  (`core/goals/GoalBuildId.as:48-55`). This is why e.g. goal 44 ("BUILD A
  MARKET") and goal 18 ("BUILD A WOOD FACTORY") can complete immediately if the
  building already exists.

### 5.2 The chapter and quest id spaces

**Chapters** (`chapters/ChapterManager.as:48-64`, `core/Config.as:156`) — nine
chapters exist in this client:

| Key | Constant | Class | Islands |
| --- | --- | --- | --- |
| 1 | `CHAPTER_01_KEY` | `Chapter01Key` | 1 |
| 2 | `CHAPTER_02_GUILLE` | `Chapter02Guille` | 3 |
| 3 | `CHAPTER_03_BAZOOKA` | `Chapter03Bazooka` | 2 |
| 4 | `CHAPTER_04_JEEPS` | `Chapter04Jeeps` | 1 |
| 5 | `CHAPTER_05_SIEGE_CONVENTIONAL` | `Chapter05SiegeConventional` | 3 |
| 6 | `CHAPTER_06_MEGATANK` | `Chapter06Megatank` | 2 |
| 7 | `CHAPTER_07_SIEGE_ELEPHANT` | `Chapter07SiegeElephant` | 1 |
| 8 | `CHAPTER_08_LURKER` | `Chapter08Lurker` | 3 |
| 9 | `CHAPTER_09_SIMPLE` | `SimpleChapter` | — |

`Config.NUM_CHAPTERS = 9`, and `ChapterManager.setChapter` clamps the chapter
id to it (`chapters/ChapterManager.as:162`).

**Quests** (`quest/Quest.as:57-105`) — the ids are the string map ids
`'100000001'`…`'100000026'` plus `'100000049'` (weekly). The *play order* is
`Quest.questIds` (`quest/Quest.as:192`) and differs from the constant naming
for two quests — see §9.1.

**Progress on a quest** is stored in `Base.Player.questsRank`, indexed by the
quest's position in `Quest.questIds`; `GoalCompleteQuest` looks it up with
`Quest.questIds.indexOf(this.questId)` (`core/goals/GoalCompleteQuest.as:29`).

---

## 6. The 134 registered goals

In registration order (which is also the tutorial/progression order).

| id | type | steps | parameters | title |
| --- | --- | --- | --- | --- |
| 1 | GoalBuildId | 1 | itemIds=[1] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A HOUSE |
| 18 | GoalBuildId | 1 | itemIds=[2] updateOnActivate=False storeCategory=1 storeSubcategory=12 storePosition=1 eTrainBuilding=-1 | BUILD A WOOD FACTORY |
| 6 | GoalAction | 8 | action=0 actionName=ACTION_ZOOM | LET'S ZOOM! |
| 8 | GoalBuildProperty | 2 | property=worker updateOnActivate=False | TRAIN 2 WORKERS |
| 20 | GoalPushUnit | 1 | buildingIds=[2,6,10,14] unitProperty=worker | SEND 1 WORKER TO WOOD FACTORY |
| 11 | GoalSelectTime | 1 | buildingProperty=depot resource=w timeIdx=0 | SELECT WORKING TIME |
| 23 | GoalCollect | 3 | property=resource resource=g | EXTRACT 3 GOLD |
| 9 | GoalBuildId | 1 | itemIds=[5] updateOnActivate=False storeCategory=1 storeSubcategory=12 storePosition=2 eTrainBuilding=-1 | BUILD A GOLD FACTORY |
| 10 | GoalPushUnit | 1 | buildingIds=[5,9,13,17] unitProperty=worker | SEND WORKER TO GOLD FACTORY |
| 87 | GoalSelectTime | 1 | buildingProperty=depot resource=g timeIdx=0 | SELECT WORKING TIME |
| 24 | GoalBuildId | 1 | itemIds=[31] updateOnActivate=False storeCategory=4 storeSubcategory=31 storePosition=2 eTrainBuilding=-1 | BUILD BAZOOKA ACADEMY |
| 25 | GoalBuildId | 3 | itemIds=[1008] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=31 | TRAIN 3 LIGHT BAZOOKA |
| 16 | GoalDoubleClick | 1 | - | DOUBLE CLICK |
| 17 | GoalCompleteChapter | 1 | chapterId=1 chapterConst=CHAPTER_01_KEY spawnChapter=True | RESCUE YOUR COMRADES! |
| 19 | GoalBuildProperty | 2 | property=worker updateOnActivate=False | TRAIN 2 MORE WORKERS |
| 5 | GoalCollect | 1 | property=resource resource=w | CUT TREES AND GET WOOD |
| 41 | GoalBuildId | 1 | itemIds=[4] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A STEEL FACTORY |
| 43 | GoalPushUnit | 1 | buildingIds=[4,8,12,16] unitProperty=worker | ADD WORKER TO STEEL FACTORY |
| 42 | GoalSelectTime | 1 | buildingProperty=depot resource=s timeIdx=0 | SELECT STEEL TO BUILD |
| 85 | GoalAddAllies | 1 | - | CALL YOUR ALLIES! |
| 40 | GoalVisitNeighbour | 1 | friendIds=[100000030,100000031] | VISIT YOUR GENERAL! |
| 30 | GoalBuildId | 2 | itemIds=[22] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD 2 TURRETS NEAR COMMAND CENTER |
| 31 | GoalBuildId | 1 | itemIds=[23] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A WALL |
| 32 | GoalMove | 1 | buildingProperty=wall | MOVE A WALL |
| 3 | GoalBuildProperty | 1 | property=farm updateOnActivate=False | BUILD A CORN FIELD |
| 4 | GoalPushUnit | 1 | buildingProperty=farm unitProperty=worker | SEND WORKER TO FIELD |
| 13 | GoalPopUnit | 1 | buildingIds=[5,9,13,17] unitProperty=worker | GET WORKER OUT OF GOLD FACTORY |
| 14 | GoalCollect | 3 | property=resource resource=s | EXTRACT 3 STEEL |
| 26 | GoalHarbor | 1 | - | THE BAZOOKA KILLER (MISSION 1) |
| 36 | GoalBuildId | 1 | itemIds=[50] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A BUNKER |
| 37 | GoalPushUnit | 1 | buildingProperty=bunker unitProperty=ft_ground | MOVE UNIT TO BUNKER |
| 29 | GoalCollect | 10 | property=resource resource=o | COLLECT 10 OIL |
| 22 | GoalBuildId | 4 | itemIds=[1] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD 4 MORE HOUSES |
| 27 | GoalBuildProperty | 3 | property=decoration updateOnActivate=False | BUILD 3 DECORATIONS |
| 28 | GoalCollect | 7 | property=resource resource=w | CHOP DOWN 7 MORE TREES |
| 33 | GoalBuildId | 1 | itemIds=[40] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A JEEP GARAGE |
| 34 | GoalBuildId | 3 | itemIds=[1014] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | TRAIN 3 MACHINE GUN JEEPS |
| 51 | GoalBuildId | 1 | itemIds=[3] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD AN OIL FACTORY |
| 88 | GoalPushUnit | 1 | buildingIds=[3,7,11,15] unitProperty=worker | SEND WORKER TO OIL FACTORY |
| 21 | GoalCollect | 1 | property=depot resource=g | COLLECT GOLD FACTORY |
| 39 | GoalBuildId | 1 | itemIds=[1] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | MORE SHELTER! |
| 44 | GoalBuildId | 1 | itemIds=[18] updateOnActivate=True storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A MARKET |
| 55 | GoalMarketTrade | 1 | trades={s:200} | BUY 200 STEEL ON MARKET |
| 56 | GoalMarketTrade | 1 | trades={w:100} | BUY 100 WOOD ON MARKET |
| 54 | GoalCollect | 1 | property=depot resource=o | COLLECT OIL FACTORY |
| 45 | GoalModifyPlayerStats | 1 | stats={c:-1} | SPEND 1 CASH |
| 74 | GoalCompleteChapter | 1 | chapterId=2 chapterConst=CHAPTER_02_GUILLE spawnChapter=False | RESCUE YOUR FRIEND!! (CHAPTER 2) |
| 69 | GoalBuildId | 2 | itemIds=[57] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD 2 TURRET II |
| 46 | GoalBuildId | 1 | itemIds=[932] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD A SILO |
| 47 | GoalOpenPopup | 1 | popup=PopupInventory | CHECK COLLECTIONS |
| 48 | GoalDailyBouns | 3 | day=3 | GET DAILY BONUS! |
| 49 | GoalReachPopulation | 40 | population=40 | REACH POPULATION 40 |
| 50 | GoalCollect | 10 | property=resource resource=g | HARVEST 10 GOLD VEINS |
| 110 | GoalCompleteQuest | 1 | questId=100000006 questConst=QUEST_06_AIRSTRIKE minDifficulty=1 winRequired=True | CALL FOR AIR REINFORCEMENTS (MISSION 2) |
| 59 | GoalBuildId | 1 | itemIds=[47] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD HOUSE II |
| 60 | GoalStoreItem | 1 | property=decoration | STORE A DECORATION |
| 53 | GoalCollect | 1 | property=depot resource=s | COLLECT STEEL FACTORY |
| 67 | GoalBuildId | 1 | itemIds=[41] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE SOLDIER ACADEMY |
| 61 | GoalBuildId | 1 | itemIds=[75] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | OPEN RECON CENTER |
| 152 | GoalCompleteChapter | 1 | chapterId=3 chapterConst=CHAPTER_03_BAZOOKA spawnChapter=False | RESCUE THE BAZOOKA SOLDIERS! (CHAPTER 3) |
| 62 | GoalMarketTrade | 1 | trades={w:-100} | SELL 100 WOOD ON MARKET |
| 63 | GoalExpand | 1 | - | EXPAND 1 MORE ACRE |
| 52 | GoalAttackPlayer | 1 | numAttacks=1 friends=False victoryNeeded=False | ATTACK A PLAYER! |
| 58 | GoalOpenPopup | 1 | popup=PopupAssaultHistory | CHECK ATTACKS! |
| 64 | GoalSpy | 1 | - | USE RECON CENTER |
| 89 | GoalBuildId | 1 | itemIds=[49] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | TURRET III |
| 90 | GoalCompleteQuest | 1 | questId=100000003 questConst=QUEST_03_DEFEND_CONVOY_AUTO minDifficulty=1 winRequired=True | PROTECT THE ALLIED CONVOY! (MISSION 3) |
| 91 | GoalBuildId | 1 | itemIds=[108] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | GRAPE FIELD |
| 92 | GoalBuildId | 1 | itemIds=[140] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | RECRUITMENT PRIZE |
| 70 | GoalBuildId | 20 | itemIds=[24] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD 20 WALL II |
| 93 | GoalBuildId | 1 | itemIds=[28] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | HOSPITAL |
| 65 | GoalAttackPlayer | 3 | numAttacks=3 friends=False victoryNeeded=True | DEFEAT 3 PLAYERS! |
| 72 | GoalBuildId | 1 | itemIds=[43] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE BAZOOKA ACADEMY |
| 94 | GoalCompleteChapter | 1 | chapterId=4 chapterConst=CHAPTER_04_JEEPS spawnChapter=False | RETRIEVE OUR JEEPS (CHAPTER 4) |
| 73 | GoalBuildId | 5 | itemIds=[1022] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | TRAIN 5 BAZOOKA SOLDIERS |
| 71 | GoalSocialBuildingOpened | 1 | buildingId=61 | CALL FOR REINFORCEMENTS |
| 95 | GoalBuildId | 1 | itemIds=[6] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR WOOD FACTORY II |
| 80 | GoalBuildProperty | 8 | property=tower updateOnActivate=False | BUILD 8 TURRETS |
| 96 | GoalCompleteQuest | 1 | questId=100000004 questConst=QUEST_04_SUPERTANK minDifficulty=1 winRequired=True | DESTROY THE MEGATANK (MISSION 4) |
| 79 | GoalBuildId | 1 | itemIds=[90] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR MARKET |
| 97 | GoalBuildId | 1 | itemIds=[38] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD TANK ACADEMY I |
| 81 | GoalAssistNeighbourBuilding | 5 | - | HELP A FRIEND! |
| 86 | GoalBuildId | 1 | itemIds=[74] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD AN ALLIES MARKET |
| 84 | GoalAlliesMarketTrade | 1 | trades={w:500} | OBTAIN WOOD IN THE ALLIES MARKET |
| 99 | GoalBuildId | 1 | itemIds=[9] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR GOLD FACTORY |
| 57 | GoalAttackPlayer | 1 | numAttacks=1 friends=True victoryNeeded=True | DEFEAT A FRIEND! |
| 100 | GoalBuildId | 1 | itemIds=[51] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUILD BUNKER II |
| 82 | GoalBuildId | 1 | itemIds=[58] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE CC |
| 101 | GoalCompleteQuest | 1 | questId=100000005 questConst=QUEST_05_ASSAULT_CONVOY minDifficulty=1 winRequired=True | DESTROY THE TRUCK (MISSION 5) |
| 102 | GoalBuildId | 1 | itemIds=[110] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | COW FARM |
| 103 | GoalBuildId | 1 | itemIds=[64] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | JEEP GARAGE II |
| 104 | GoalBuildId | 1 | itemIds=[8] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR STEEL FACTORY |
| 106 | GoalBuildId | 1 | itemIds=[7] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR OIL FACTORY II |
| 107 | GoalBuildId | 20 | itemIds=[25] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE TO WALL III |
| 108 | GoalBuildId | 1 | itemIds=[54] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | HELICOPTER HANGAR I |
| 109 | GoalBuildId | 1 | itemIds=[48] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | HOUSE III |
| 66 | GoalCompleteQuest | 1 | questId=100000002 questConst=QUEST_02_CENTRAL_NUCLEAR minDifficulty=1 winRequired=True | BLOW UP THE NUCLEAR PLANT! (MISSION 6) |
| 111 | GoalBuildId | 1 | itemIds=[52] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | BUNKER III |
| 112 | GoalBuildId | 1 | itemIds=[80] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | FORTRESS I |
| 113 | GoalBuildId | 1 | itemIds=[135] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | Mechanical Garage |
| 115 | GoalBuildId | 1 | itemIds=[42] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE SOLDIER ACADEMY |
| 116 | GoalBuildId | 1 | itemIds=[10] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR WOOD FACTORY |
| 117 | GoalBuildId | 1 | itemIds=[44] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE BAZOOKA ACADEMY |
| 118 | GoalCompleteQuest | 1 | questId=100000007 questConst=QUEST_07_SHIP minDifficulty=1 winRequired=True | STEAL THE SHIP! (MISSION 7) |
| 119 | GoalBuildId | 1 | itemIds=[13] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR GOLD FACTORY |
| 120 | GoalBuildId | 20 | itemIds=[78] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR WALLS |
| 121 | GoalBuildId | 1 | itemIds=[37] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | Hangar I |
| 123 | GoalBuildId | 1 | itemIds=[91] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE MARKET |
| 124 | GoalBuildId | 1 | itemIds=[59] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR CC III |
| 125 | GoalBuildId | 1 | itemIds=[12] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE STEEL FACTORY |
| 126 | GoalCompleteQuest | 1 | questId=100000008 questConst=QUEST_08_ROCKET minDifficulty=1 winRequired=True | STOP THE ROCKET LAUNCHING! (MISSION 8) |
| 127 | GoalBuildId | 1 | itemIds=[62] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR TANK ACADEMY I |
| 129 | GoalBuildId | 1 | itemIds=[55] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR HELICOPTER HANGAR |
| 130 | GoalCompleteChapter | 1 | chapterId=5 chapterConst=CHAPTER_05_SIEGE_CONVENTIONAL spawnChapter=False | DEFEND FROM ASSAULT! (CHAPTER 9) |
| 131 | GoalBuildId | 1 | itemIds=[11] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR OIL FACTORY |
| 132 | GoalBuildId | 1 | itemIds=[39] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | TURRET IV |
| 133 | GoalBuildId | 1 | itemIds=[65] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | Jeep garage III |
| 134 | GoalCompleteQuest | 1 | questId=100000009 questConst=QUEST_09_LABORATORIES minDifficulty=1 winRequired=True | DESTROY THE LABS (MISSION 9) |
| 135 | GoalBuildId | 20 | itemIds=[79] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR WALLS |
| 136 | GoalBuildId | 1 | itemIds=[76] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR HANGAR |
| 137 | GoalBuildId | 1 | itemIds=[14] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR WOOD FACTORY |
| 138 | GoalCompleteChapter | 1 | chapterId=6 chapterConst=CHAPTER_06_MEGATANK spawnChapter=False | DESTROY THE MEGATANK (CHAPTER 10) |
| 139 | GoalBuildId | 1 | itemIds=[60] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE THE COMMAND CENTER IV |
| 141 | GoalBuildId | 1 | itemIds=[63] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR TANK ACADEMY |
| 142 | GoalCompleteQuest | 1 | questId=100000010 questConst=QUEST_10_SPECIAL_OPS minDifficulty=1 winRequired=True | STEAL THE LAPTOP (MISSION 10) |
| 143 | GoalBuildId | 1 | itemIds=[17] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR GOLD FACTORY |
| 144 | GoalBuildId | 1 | itemIds=[56] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR HELICOPTER HANGAR |
| 145 | GoalCompleteChapter | 1 | chapterId=7 chapterConst=CHAPTER_07_SIEGE_ELEPHANT spawnChapter=False | ELEPHANTS COMING! (CHAPTER 11) |
| 146 | GoalBuildId | 1 | itemIds=[16] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR STEEL FACTORY |
| 147 | GoalBuildId | 1 | itemIds=[77] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR HANGAR |
| 148 | GoalBuildId | 1 | itemIds=[15] updateOnActivate=False storeCategory=-1 storeSubcategory=-1 storePosition=-1 eTrainBuilding=-1 | UPGRADE YOUR OIL FACTORY IV |
| 149 | GoalCompleteQuest | 1 | questId=100000011 questConst=QUEST_11_SAVE_VILLAGES minDifficulty=1 winRequired=True | RESCUE YOUR CITIZEN (MISSION 11) |
| 150 | GoalCompleteChapter | 1 | chapterId=8 chapterConst=CHAPTER_08_LURKER spawnChapter=False | T-REX ASSAULT! (CHAPTER 12) |
| 151 | GoalCompleteQuest | 1 | questId=100000012 questConst=QUEST_12_TANKBOSS minDifficulty=1 winRequired=True | THE KILLER ROBOT (MISSION 12) |

**Counts per type:** `GoalBuildId` 68, `GoalCompleteQuest` 11, `GoalCollect` 9,
`GoalCompleteChapter` 8, `GoalPushUnit` 6, `GoalBuildProperty` 5,
`GoalAttackPlayer` 3, `GoalMarketTrade` 3, `GoalSelectTime` 3,
`GoalOpenPopup` 2, and 16 types with exactly 1 instance each
(`GoalAction`, `GoalAddAllies`, `GoalAlliesMarketTrade`,
`GoalAssistNeighbourBuilding`, `GoalDailyBouns`, `GoalDoubleClick`,
`GoalExpand`, `GoalHarbor`, `GoalModifyPlayerStats`, `GoalMove`,
`GoalPopUnit`, `GoalReachPopulation`, `GoalSocialBuildingOpened`, `GoalSpy`,
`GoalStoreItem`, `GoalVisitNeighbour`).

---

## 7. The reward structure

| Class | Holds | `deliver()` | Used by |
| --- | --- | --- | --- |
| `rewards/AbstractReward` | — (extends `Sprite`) | no-op | base class |
| `rewards/RewardResource` | `id` (a `Constants.COST_*` code) + `amount` | shows a floating particle | **all 134 goals** |
| `rewards/RewardElement` | item `id` + `amount` | creates a `BuildingReference` and calls `Base.Main.storeItem()` (the item goes to storage) | unused by any registered goal |

* Every registered goal is created with the reward argument `10`, which
  `parseReward` turns into `RewardResource(Constants.COST_GOLD, 10)` —
  **10 gold per goal** (`managers/GoalManager.as:49-315`, `:444-464`).
* The reward text shown in the popup is `AbstractGoal.rewardInfo`
  (`AbstractGoal.as:140-152`), which joins the `info` of every reward with
  `\n`. `RewardResource.info` is not overridden, so it returns the base
  `""` — **the reward line of the completion popup is empty in this client**,
  while the "MISSION COMPLETED! … gold reward" banner in `PopupGoals` is
  hard-coded to 10 (`popups/PopupGoals.as:102`, `:893`).
* The reward is *actually* granted through the resource variation attached to
  the `complete_goal` command (`commands/CmdCompleteGoal.as:15-22` +
  `commands/Command.as:51` `setResource`).
* `RewardElement` is used elsewhere in the game (chapters, quests,
  `PopupMissionInfo`) but **never** as a goal reward in this client.
* The upstream server never grants a goal reward itself: the `complete_goal`
  handler only prints (`upstream/socialwarriors/command.py:76-79`). The
  resource variation carried by the command does the work.

---

## 8. Id reconciliation — client vs. `config/main.json`

| Set | Count |
| --- | --- |
| Goals in `upstream/socialwarriors/config/main.json` (`goals` array) | **91** (ids 1…91, contiguous) |
| Goals registered client-side (`managers/GoalManager.as:49-315`) | **134** (all ids unique) |
| In **both** | **79** |
| In the **config only** | **12** → `2, 7, 12, 15, 35, 38, 68, 75, 76, 77, 78, 83` |
| In the **client only** | **55** → `92–97, 99–104, 106–113, 115–121, 123–127, 129–139, 141–152` (see `re/data/goals.json` → `reconciliation.clientOnly`) |

Two further id sets are useful:

* `TranslationGoals` holds **140** entries — the 134 registered ids plus
  **6 ids that are never registered**: `98, 105, 114, 122, 128, 140`.
* The **12 config-only ids are exactly the ids missing from both the client
  registrations and `TranslationGoals`**. The id space is therefore shared
  between the two sources, and the client simply never implemented those 12.

### 8.1 The numeric overlap is coincidental — the config's goal table is not Social Wars content

This is the most important finding of the reconciliation and it contradicts a
naive reading of the config.

* The config's 91 goal titles talk about **villagers, trolls, sheep and cow
  ranches, wonders, acres, an archery range, a stable, a university, a
  blacksmith and a market**: `"Train another Villager"`, `"Kill 3 trolls"`,
  `"Capture a sheep"`, `"Build 2 wonders"`, `"Expand to 2 acres"`,
  `"Obtain Troll's Treasure"`.
* None of that vocabulary exists in the Social Wars client, whose goals are
  about **workers, soldiers, factories, bunkers, turrets, walls and missions**:
  `"BUILD A HOUSE"`, `"TRAIN 2 WORKERS"`, `"BUILD A BUNKER"`, `"BUILD 20 WALL II"`.
* **All 79 overlapping ids have a different title** in the two sources
  (`configTitleMatchesClient` is `false` for every one of them — see
  `re/data/goals.json`). Examples: id 1 is *"Build a farm"* in the config and
  *"BUILD A HOUSE"* in the client; id 5 is *"Cut 7 trees and collect wood"*
  versus *"CUT TREES AND GET WOOD"*; id 30 is *"Kill 7 trolls"* versus
  *"BUILD 2 TURRETS NEAR COMMAND CENTER"*.
* The **same file's `items` array *is* Social Wars content** (id 1 = "House I",
  id 2 = "Wood Factory I", id 30 = "Academy I", …), and the `globals` block is
  Social Wars too (`NUM_ACTIVE_MISSIONS`, `REWARDS_CHAPTERS`, `ALLIES_MARKET_*`).
  The `goals` array is the odd one out.
* The goals table is byte-identical in all three captured snapshots of the
  upstream config (`config/get_game_config.php_23july2012.txt`,
  `…_29august2012.txt`, `…_29august2012_nohash.txt` and `main.json`), so it is
  stable foreign data rather than a transient artefact.
* **Consequence:** the upstream server's goal handling prints the *wrong* title
  for every goal (`upstream/socialwarriors/get_game_config.py:139-150` →
  `upstream/socialwarriors/command.py:74`, `:79`).
* **Which game the table came from is UNVERIFIED.** The vocabulary
  (villager, farm, ranch, troll, wonder, acre, university, blacksmith) is
  consistent with a different Zynga farm-town title, but nothing in this
  repository identifies it.

**Recommendation:** the goal definition source of truth for the re-implementation
is the client's `GoalManager` + `TranslationGoals`, **not**
`config/main.json`'s `goals` array. The id space may be kept as-is so that the
`set_goals` / `complete_goal` wire format stays compatible with the original
client, but the goal *content* must come from the client.

### 8.2 Reward reconciliation

All 91 config goals carry `reward: 10` and all 134 client goals award 10 gold,
so the two sources agree on the reward **value** even though the goals
themselves are different.

---

## 9. Client defects found in the goal system

These are in the shipped 1.5.4 client and must be consciously decided about by
any re-implementation.

| # | Where | Defect |
| --- | --- | --- |
| 1 | `core/goals/GoalAlliesMarketTrade.as:62` | `_currentStep = param1 < this.tradesLength ? 0 : 1;` compares an **Object** with an **int**. The comparison is always false, so `_currentStep` is always `1` and goal 84 ("OBTAIN WOOD IN THE ALLIES MARKET", `{"w":500}`) completes on the **first** Allies-Market collection instead of after 500 wood. `GoalMarketTrade.as:62` has the correct form (`this.tradesAlreadyMade < this.tradesLength`). |
| 2 | `core/goals/GoalStoreItem.as:46` | `deactivate()` calls `Base.Iso.itemStored.add(this.onItemStored)` instead of `.remove(...)`. The listener is never detached and a duplicate is registered on every deactivation. |
| 3 | `core/goals/GoalModifyPlayerStats.as:56` | `this.stats[key] -= delta` runs even after the key was `delete`d, re-creating it with the value `NaN`. Benign for the single-step goal 45, but the remaining-target bookkeeping is not clean. |
| 4 | `managers/GoalManager.as:444-464` | `parseReward` overwrites the reward variable inside the `for` loop over the object's keys, so an object reward with more than one key only ever produces one `RewardResource`. Never triggered (all goals use the integer form). |
| 5 | Goal text vs. chapter registration | The client's story has **9 chapters** (`Config.NUM_CHAPTERS = 9`, `core/Config.as:156`), but the goal texts of ids **130**, **138**, **145** and **150** say *"(CHAPTER 9)"*, *"(CHAPTER 10)"*, *"(CHAPTER 11)"* and *"(CHAPTER 12)"* while the goals are bound to chapter keys **5, 6, 7, 8** (`CHAPTER_05_SIEGE_CONVENTIONAL`, `CHAPTER_06_MEGATANK`, `CHAPTER_07_SIEGE_ELEPHANT`, `CHAPTER_08_LURKER`). The texts that *do* describe the real chapters 5–8 live under the six never-registered text ids **98, 105, 114, 122, 128, 140**. A re-implementation must decide whether the goal follows the **chapter key** (what the code does) or the **chapter named in the text** (what the player is told). |
| 6 | `core/goals/GoalHarbor.as:76-81` | `onQuestEnd` completes the goal for **any** quest, without checking the quest id — so "THE BAZOOKA KILLER (MISSION 1)" completes when any quest ends. |

### 9.1 A near-miss that is **not** a defect

Goals **66** and **110** look like their mission texts are swapped: goal 110 is
titled *"(MISSION 2)"* but is registered against `QUEST_06_AIRSTRIKE`, and goal
66 is titled *"(MISSION 6)"* but is registered against `QUEST_02_CENTRAL_NUCLEAR`.
They are **not** swapped. The mission play order is `Quest.questIds`
(`quest/Quest.as:192`):

```
[0] QUEST_WEEKLY_01  [1] QUEST_01_BAZOOKA  [2] QUEST_06_AIRSTRIKE  [3] QUEST_03_DEFEND_CONVOY_AUTO
[4] QUEST_04_SUPERTANK  [5] QUEST_05_ASSAULT_CONVOY  [6] QUEST_02_CENTRAL_NUCLEAR  [7] QUEST_07_SHIP
[8] QUEST_08_ROCKET  [9] QUEST_09_LABORATORIES  [10] QUEST_10_SPECIAL_OPS  [11] QUEST_11_SAVE_VILLAGES
[12] QUEST_12_TANKBOSS  ...
```

The goal texts number the missions by **play position** (goal 110 → 2nd quest,
goal 66 → 6th quest), while the `QUEST_*` constants are named after their
**map** number (`questMaps`, `quest/Quest.as:166-190`: `QUEST_06_AIRSTRIKE` →
`MAP_06_AIRSTRIKE`). The registration is consistent with the player's
experience; only the constant names mislead.

---

## 10. What a server-side re-implementation must implement

The re-implementation must be **authoritative**: the client currently decides
completion and tells the server afterwards. Under the project's
"server is authoritative" rule (§ *Architecture Non-Negotiables* in
`AGENTS.md`), the server must own the counters and the rewards.

### 10.1 Data model

* A **goal definition table** with one row per goal id: `id`, `type`, the
  type-specific parameters, `steps`, `reward`, and the six text fields. The
  content must come from the client's `GoalManager` + `TranslationGoals`, **not**
  from `config/main.json`'s `goals` array (§8.1).
* A **per-player goal state** row per (player, goal id): `visited` (0/1),
  `currentStep`, and a `completed` flag. The upstream shape
  (`privateState.goals`, a sparse array indexed by goal id, each entry
  `[visited, currentStep]`) is a reasonable wire-compatible starting point, but
  a normalised table is better for a server that owns the state.
* The resource codes must follow the project's 8-slot vector
  `[energy, xp, gold, wood, oil, steel, cash, mana]`
  (`commands/Command.as:8-22`); the client's `Constants.COST_*` codes map onto
  it as `e, x, g, w, o, s, c, m`.

### 10.2 The event sources the rules engine must observe

| Event | Client signal | Emitted when |
| --- | --- | --- |
| build finished | `Base.Iso.elementBuilt` | a building is placed **or** a unit finishes training |
| collect | `Base.Iso.elemCollected` | the player collects from a building or a resource node |
| unit in / out | `Base.Iso.unitPushed` / `unitPopped` | a unit enters / leaves a building |
| production time set | `Base.Iso.timeSelected` | a production slot is chosen on a multi-collectable |
| building moved | `Base.Iso.buildingMoved` | a building is relocated |
| item stored | `Base.Iso.itemStored` | a building is moved to storage |
| tile bought | `Base.Iso.tilePurchased` | a map tile is bought (expansion) |
| neighbour visited | `Base.Iso.neighbourVisited` | the player enters a friend's map |
| neighbour assisted | `Base.Iso.neighbourBuildingAssisted` | the player helps a friend finish a building |
| social building opened | `Base.Iso.socialBuildingOpened` | the Allies Building / Allies Market is used |
| market trade | `Base.Iso.marketTrade` | a trade is executed on the Market |
| allies market trade | `Base.Iso.alliesMarketTrade` | the player collects from the Allies Market |
| resources changed | `Base.Resources.playerStatsModified` | any resource delta is applied |
| population changed | `Base.Player.populationModified` | the population changes |
| daily bonus won | `Base.Iso.dailyBounsWon` | the daily bonus is claimed |
| double click | `Base.Iso.doubleClick` | the player double-clicks the map |
| UI action | `Base.Main.actionTriggered` | zoom (0) or multi-select (1) |
| assault finished | `Assault.attackEnd` | an attack resolves (payload: `win`, `opponent`, `voluntary`) |
| spy finished | `Assault.spyEnd` | a spy operation ends |
| quest finished | `Quest.questEnd` | a quest/mission ends (payload: `id`, `win`, `difficulty`) |
| chapter finished | `ChapterManager.chapterFinished` | a story chapter is completed |
| popup opened | `Base.PopUp.popupOpened` | any popup opens |

For a server, four of these are **pure UI interactions** with no server-visible
equivalent in the original protocol: `doubleClick` (map double-click),
`actionTriggered` (zoom / multi-select), `popupOpened` (opening the inventory
or the assault history) and the `GoalAddAllies` invite flow. They must be
reported to the server by the new client explicitly if they are to be
preserved. The remaining events all correspond to a real mutation of the
player's state and can be derived server-side from the authoritative commands
(build, collect, push/pop unit, trade, move, store, expand, visit, assist,
attack, spy, quest end, chapter end, daily bonus, resource change).

### 10.3 Rules the engine must implement

1. **Own the counter.** Every event is applied to the active goals, the counter
   is incremented, and the new state is written back. The client must not be
   able to set its own progress.
2. **Validate the match predicates** listed in §5.1 exactly: ownership, item
   id list vs. item property, `collect_type` vs. resource code, and the
   `timeIdx` (production slot) rule.
3. **Handle the activation-time sweep** (`updateOnActivate`, and the automatic
   depot/HQ/`building_limit_same_id` rule of `GoalBuildId`): when a goal
   becomes active, the server must count the buildings that already exist and
   may have to complete the goal immediately.
4. **Handle the already-satisfied check at activation** for
   `GoalCompleteChapter` (`currentQuestId > chapterId`), `GoalCompleteQuest`
   (`questsRank`) and `GoalHarbor` (`questsRank[1]`).
5. **Award the reward server-side**, exactly once per goal, as a resource
   delta on the 8-slot vector (10 gold per goal in this content set). The
   client must not be able to trigger a reward by replaying a `complete_goal`
   command.
6. **Enforce `NUM_ACTIVE_MISSIONS = 5`** as the number of simultaneously
   visible/incomplete goals, and the "next goal starts when this one is
   completed" progression, if the original pacing is to be preserved.
7. **Decide the bug policy** for the six defects in §9. A faithful
   "playable legacy" build would reproduce them; a clean re-implementation
   would fix them and say so.
8. **Keep the rules engine deterministic and pure** — the goal counters are a
   pure function of (goal state, event, player state); no wall-clock, no
   unseeded randomness, no I/O in the evaluation path.

### 10.4 Wire compatibility

If the legacy `command.php` protocol is kept, the server must accept and
persist:

* `set_goals` — `<goalId>, "[visited, currentStep]"` — but **validated**, not
  trusted.
* `complete_goal` — `<goalId>` plus a resource variation. Under the new
  authoritative model the server should **ignore the client-supplied
  variation** and grant its own.

---

## 11. Marked UNVERIFIED

The following could not be determined from the code available in this
repository.

| Item | Why it is unverified |
| --- | --- |
| The origin game of `config/main.json`'s `goals` array | The vocabulary points at a different Zynga title, but no file in the repository identifies it. The upstream project contains no commit history or README that names it. |
| The identity of the friend ids `100000030` / `100000031` in goal 40 | They are hard-coded integers in `GoalManager.as:89`; nothing in the client maps them to a named character. |
| Whether the original Zynga server validated goal progress | The client-side counters are the only implementation found. The upstream Python server stores whatever the client sends (`engine.py:96-100`) — that is a private-server artefact, not evidence about the original service. |
| Whether `translation_goals` was ever populated by the real server | The client accepts the key (`GameDataManager.as:143-146`) but never reads the value, so a populated payload would be indistinguishable from an absent one. |
| The exact reward of a goal in the *original* service | The client hard-codes 10 gold for all 134 goals and the config agrees on 10, but the original server-side reward table is not recoverable from this repository. |
| Whether `NUM_ACTIVE_MISSIONS = 5` was the original server's value | The value comes from the captured `config/main.json` globals; the server is never seen applying it. |
| Whether `GoalContainer` was used in the shipped game | It is never instantiated in `GoalManager`; it may be dead code, or may be used by an unreferenced tutorial path. |
| The precise semantics of `building.loaded.attrs.cp` beyond "production slot index" | Only the comparison `cp >= timeIdx` is visible in `GoalSelectTime.as:39`. |
| Whether the 6 translation-only ids (98, 105, 114, 122, 128, 140) were goals in an earlier client version | They have text but no registration in 1.5.4. The version history in `re/data/client-version-history.json` was not cross-referenced for goal registration changes. |
