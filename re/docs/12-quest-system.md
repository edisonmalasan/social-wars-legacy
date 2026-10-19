# The Quest System — Lifecycle, Difficulty and Per-Quest Specifications

**Roadmap task B4 (quest half).** The assault missions ("Quests") are the largest single
family of scripted content in the client: 23 quest classes, one base class
(`QuestHardcore`), one abstract base (`AbstractQuest`) and a static dispatcher (`Quest`).
This document reduces them to an implementable specification.

| | |
|---|---|
| **Source** | `quest/` in the decompiled `Basesec_1.5.4.swf` (28 classes), cross-referenced with `core/isoengine/`, `chapters/`, `managers/MapManager.as`, `popups/` |
| **Data** | [`../data/quests.json`](../data/quests.json) — one entry per concrete quest class |
| **Related** | [`03-commands-quests-economy.md`](03-commands-quests-economy.md) §3 (wire protocol, commands), [`02-combat-and-units.md`](02-combat-and-units.md) (unit stats) |

> All line references are to `.work/as/basesec/scripts/`. All `file:line` citations were
> re-read from the decompiled source; nothing here is inferred from the upstream Python
> server. Where the client and the upstream disagree, the client wins
> (`AGENTS.md` → *Architecture Non-Negotiables* #2).

---

## 1. What a quest is

A quest is **a self-contained assault battle on its own map**. It is not a chapter:
chapters are story missions placed on the *player's* town map; quests are separate
maps reached from the "Missions World" (harbour) screen.

Three pieces of machinery make up a quest:

| Piece | File | Role |
|---|---|---|
| `Quest` | `quest/Quest.as` | static dispatcher: id ↔ class ↔ map, play order, global result state, unit recovery, result wire payload |
| `AbstractQuest` | `quest/AbstractQuest.as` | the lifecycle contract: `prepareInit` → `mapLoaded` → `start` → `elementKilled`/`elementCollected` → `end` → `sendResults` |
| `QuestInterface` | `quest/QuestInterface.as` | the 17-method interface every quest implements |

### 1.1 The quest registry

`Quest.createQuestFactory()` (`quest/Quest.as:138-193`) builds two dictionaries:

* `questFactory[questId] = <Class>` — 22 story/hardcore classes + `QuestWeekly01`.
* `questMaps[questId] = MapManager.MAP_*` — the terrain grid id (101…149).

and one array:

* `questIds` (`quest/Quest.as:192`) — the **play order**. Index 0 is the weekly quest;
  index 1…22 are the 22 story/hardcore quests. `Quest.getQuestId(index)` returns
  `questIds[index]`, and **`globals.REWARDS_QUESTS` is indexed by `questIds.indexOf(id)`**
  (`quest/AbstractQuest.as:449`). The reward table is therefore *positional*, not keyed by id.

```
[0]  QUEST_WEEKLY_01            100000049
[1]  QUEST_01_BAZOOKA           100000001
[2]  QUEST_06_AIRSTRIKE         100000006
[3]  QUEST_03_DEFEND_CONVOY_AUTO 100000003
[4]  QUEST_04_SUPERTANK         100000004
[5]  QUEST_05_ASSAULT_CONVOY    100000005
[6]  QUEST_02_CENTRAL_NUCLEAR   100000002
[7]  QUEST_07_SHIP              100000007
[8]  QUEST_08_ROCKET            100000008
[9]  QUEST_09_LABORATORIES      100000009
[10] QUEST_10_SPECIAL_OPS       100000010
[11] QUEST_11_SAVE_VILLAGES     100000011
[12] QUEST_12_TANKBOSS          100000012
[13] QUEST_13_TYRANNOSAURUS     100000013
[14] QUEST_14_SPY_2             100000014
[15] QUEST_15_HARDCORE1         100000017
[16] QUEST_16_HARDCORE2         100000018
[17] QUEST_17_HARDCORE3         100000019
[18] QUEST_18_HARDCORE4         100000020
[19] QUEST_19_HARDCORE5         100000021
[20] QUEST_20_HARDCORE6         100000022
[21] QUEST_22_HARDCORE9         100000026
[22] QUEST_23_HARDCORE10        100000025
```

`Quest.numQuests` = `questIds.length - 1` = **22** playable story/hardcore quests
(`quest/Quest.as:239-243`); index 0 (weekly) is excluded from that count but is still
reachable (`popups/PopupWeeklyQuest.as:41-43`).

### 1.2 The quest-id mapping (reconstructed)

`upstream/socialwarriors/constants.py:4-36` (`class Quests.QUEST`) contains **three
duplicate dict keys**. Python keeps the *last* occurrence, so the upstream file silently
loses three entries:

| id | `constants.py` (last wins) | Client truth | Upstream map file | Verdict |
|---|---|---|---|---|
| `100000001` | `QUEST 01: BAZOOKA` | `QUEST_01_BAZOOKA` → `Quest01Bazooka` | `villages/quest/100000001.json` | ✔ |
| `100000002` | `QUEST 02: CENTRAL_NUCLEAR` | `QUEST_02_CENTRAL_NUCLEAR` → `Quest02CentralNuclear` | ✔ | ✔ |
| `100000003` | `QUEST 03: DEFEND_CONVOY_AUTO` | `QUEST_03_DEFEND_CONVOY_AUTO` → `Quest03DefendConvoyAuto` | ✔ | ✔ |
| `100000004` | `QUEST 04: SUPERTANK` | `QUEST_04_SUPERTANK` → `Quest04Supertank` | ✔ | ✔ |
| `100000005` | `QUEST 05: ASSAULT_CONVOY` | `QUEST_05_ASSAULT_CONVOY` → `Quest05AssaultConvoy` | ✔ | ✔ |
| `100000006` | `QUEST 06: AIRSTRIKE` | `QUEST_06_AIRSTRIKE` → `Quest06Airstrike` | ✔ | ✔ |
| `100000007` | `QUEST 07: SHIP` | `QUEST_07_SHIP` → `Quest07Ship` | ✔ | ✔ |
| `100000008` | `QUEST 08: ROCKET` | `QUEST_08_ROCKET` → `Quest08Rocket` | ✔ | ✔ |
| `100000009` | `QUEST 09: LABORATORIES` | `QUEST_09_LABORATORIES` → `Quest09Laboratories` | ✔ | ✔ |
| `100000010` | `QUEST 10: SPECIAL_OPS` | `QUEST_10_SPECIAL_OPS` → `Quest10SpecialOps` | ✔ | ✔ |
| `100000011` | `QUEST 11: SAVE_VILLAGES` | `QUEST_11_SAVE_VILLAGES` → `Quest11SaveVillages` | ✔ | ✔ |
| `100000012` | `QUEST 12: TANKBOSS` | `QUEST_12_TANKBOSS` → `Quest12TankBoss` | ✔ | ✔ |
| `100000013` | `QUEST 13: TYRANNOSAURUS` | `QUEST_13_TYRANNOSAURUS` → `Quest13Tyrannosaurus` | ✔ | ✔ |
| `100000014` | `QUEST 14: SPY_2` | `QUEST_14_SPY_2` → `Quest14Spy2` | ✔ | ✔ |
| `100000017` | `QUEST 15: HARDCORE1` | `QUEST_15_HARDCORE1` → `Quest15HCCrusaderBase1` | ✔ | ✔ |
| `100000018` | `QUEST 16: HARDCORE2` | `QUEST_16_HARDCORE2` → `Quest16HCAliens` | ✔ | ✔ |
| `100000019` | `QUEST 17: HARDCORE3` | `QUEST_17_HARDCORE3` → `Quest17HCArachnids` | ✔ | ✔ |
| `100000020` | `QUEST 18: HARDCORE4` | `QUEST_18_HARDCORE4` → `Quest18HCDragons` | ✔ | ✔ |
| `100000021` | `QUEST 19: HARDCORE5` | `QUEST_19_HARDCORE5` → `Quest19HC` | ✔ | ✔ |
| `100000022` | `QUEST 20: HARDCORE6` | `QUEST_20_HARDCORE6` → `Quest20HC` | ✔ | ✔ |
| `100000023` | `QUEST 21: HARDCORE7` | *no class, no map, not playable* | — | id only |
| `100000024` | `QUEST: ISLA_RUBEN3D` (dup) | `QUEST_22_HARDCORE8` → *no class*, map 124 | — | id only |
| `100000025` | `QUEST: ISLA_KASPAR` (dup) | `QUEST_23_HARDCORE10` → `Quest24HC`, map 125 | `villages/quest/100000025.json` | **dup** |
| `100000026` | `QUEST: ISLA_EGG2` (dup) | `QUEST_22_HARDCORE9` → `Quest23HC`, map 126 | `villages/quest/100000026.json` | **dup** |
| `100000027` | `QUEST: ISLA_EGG1` | *no class, no map* | — | id only |
| `100000028` | `QUEST: BOSS_DRAGON_1` | *no class, no map* | — | id only |
| `100000049` | `QUEST: WEEKLY_01` | `QUEST_WEEKLY_01` → `QuestWeekly01`, map 149 | `villages/quest/100000049.json` | ✔ |
| `100000100` | `QUEST: DEFEND_CONVOY` | `QUEST_DEFEND_CONVOY` → *no class*; `Quest03DefendConvoyAuto` has an empty `QuestDefendConvoy()` stub (`quest/Quest03DefendConvoyAuto.as:87-89`) | — | id only |

**Reconstructed mapping (authoritative):** the client factory
(`quest/Quest.as:145-167`) plus the map ids (`quest/Quest.as:169-191`) plus the upstream
map filenames (`upstream/socialwarriors/villages/quest/*.json`) agree on:

```
100000001 Bazooka            100000014 Spy_2            100000025 Quest24HC   (HARDCORE10)
100000002 CentralNuclear     100000017 HC1 Vikings      100000026 Quest23HC   (HARDCORE9)
100000003 DefendConvoyAuto   100000018 HC2 Aliens       100000049 Weekly01
100000004 Supertank          100000019 HC3 Arachnids
100000005 AssaultConvoy      100000020 HC4 Dragons
100000006 Airstrike          100000021 HC5 Robots
100000007 Ship               100000022 HC6 Monsters
100000008 Rocket
100000009 Laboratories
100000010 SpecialOps
100000011 SaveVillages
100000012 TankBoss
100000013 Tyrannosaurus
```

**The three duplicate keys in `constants.py`** are `100000024`, `100000025`, `100000026`
(each appears twice; lines 24/32, 25/33, 26/30). The upstream file therefore reports
`100000024 → "QUEST: ISLA_RUBEN3D"`, `100000025 → "QUEST: ISLA_KASPAR"` and
`100000026 → "QUEST: ISLA_EGG2"`, hiding the real `HARDCORE8 / HARDCORE10 / HARDCORE9`
names. **The client mapping is correct** and is corroborated by three independent
sources:

1. `quest/Quest.as:165-166` — `questFactory[QUEST_22_HARDCORE9] = Quest23HC` and
   `questFactory[QUEST_23_HARDCORE10] = Quest24HC`.
2. `quest/Quest.as:189-190` — map 126 for `…HARDCORE9`, map 125 for `…HARDCORE10`.
3. `globals.REWARDS_QUESTS` is monotonic in `questIds` order
   (`{g:1500,w:400}` at index 1 … `{g:24000,w:4200}` at index 22) and
   `globals.QUESTS_MIN_LEVELS` puts the level-40 gate on `100000021`, `100000022`,
   `100000025`, `100000026` — i.e. the four *team* quests, which
   `Config.QUESTS_WITH_TEAMS` lists as `QUEST_19_HARDCORE5`, `QUEST_20_HARDCORE6`,
   `QUEST_22_HARDCORE9`, `QUEST_23_HARDCORE10` (`core/Config.as:160`).

The upstream `questTimes` block inside `villages/quest/100000049.json` lists exactly the
same 26 ids (including `100000023`, `100000024`, `100000100`), confirming the id space.

**Note the constant-name drift in the client itself:** the constant for `100000026` is
named `QUEST_22_HARDCORE9` (there is no `QUEST_21_HARDCORE9`), and `100000025`'s
constant is `QUEST_23_HARDCORE10` while its class is `Quest24HC` — the class numbering
skips 21 and 22.

---

## 2. The quest lifecycle

```
PopupQuestsMap (Missions World)
   └─ Quest.loadQuest(index [, army])            quest/Quest.as:255-265
        ├─ Quest.setQuest(questId)                quest/Quest.as:267-277   → new questFactory[id]()
        ├─ Quest.prepareInit()                    quest/Quest.as:290-319
        │     └─ currentQuest.prepareInit()       quest/AbstractQuest.as:82-103
        ├─ Base.Main.loadMap(questId, "", GAME_MODE_ASSAULT)
        └─ PopupLoadingQuest  →  user picks difficulty
              └─ Quest.currentQuest.difficulty = d  popups/PopupLoadingQuest.as:132-136
                   └─ Quest.start()                quest/Quest.as:357-361
                        └─ currentQuest.start()    quest/AbstractQuest.as:374-380  (intro cutscene)

   ── map loads ──
   Base.Main.finishMap → Quest.mapLoaded()        core/Base.as:2745-2748
        └─ currentQuest.mapLoaded()               quest/AbstractQuest.as:105-180

   ── play ──
   IsoFightingElement.onDeath
        ├─ Quest.elementKilled(el)                 quest/Quest.as:363-381
        │     └─ currentQuest.elementKilled(el)    quest/AbstractQuest.as:232-282
        └─ Quest.elementCollected(el)              quest/Quest.as:383-402
              └─ currentQuest.elementCollected(el)

   ── end ──
   cutscene/action/EndQuest.start()                cutscene/action/EndQuest.as:16-26
        ├─ Quest.bPlayerWinner = victory
        └─ Quest.end()                            quest/Quest.as:404-441
              ├─ recoverUnits(army, getRecoveredUnitsPercentage())
              ├─ add getFreeUnits() to the army
              ├─ questEnd.dispatch({id, difficulty, win})
              ├─ questFinished.dispatch(bPlayerWinner)
              └─ currentQuest.end(null)            quest/AbstractQuest.as:318-329
   └─ Quest.sendResults()                          quest/Quest.as:443-450
        └─ currentQuest.sendResults()             quest/AbstractQuest.as:430-461
             ├─ AdminCmdSetQuestRank(index, difficulty)
             └─ CmdEndQuest(json, rewards)
```

### 2.1 `prepareInit` — what a quest must set up

`AbstractQuest.prepareInit` (`quest/AbstractQuest.as:82-103`) resets the per-quest state
and captures the player's army:

* resets `friends`, `foes`, `_rewards`, `_literals`, `importantIds`, `keyIds`,
  `keyElements`, `reinforcementIds`, `remainingFoes`;
* `currentPlayerArmy = Base.Iso.getCurrentFilteredArmy(unitTypesExcluded, unitTypesIncluded)`;
* `Quest.setPlayerUnits(...)` / `Quest.setPlayerUnitsBRefs(...)` — the army the player
  brought;
* creates `qChapter = new Chapter(-1)` and makes it the current chapter.

Subclasses then add their own state. The four dictionaries are the whole quest DSL:

| Dictionary | Meaning | Effect |
|---|---|---|
| `importantIds[itemId]` | elements that participate in the scripted story | becomes a `ChapterElement` (`chapters/Chapter.as:899-945`); may set `chapterId`, `canDie`, `attackable`, `affiliation`, `onKill`, `onNearDeath`, `onKillDefenders`, `swap` |
| `keyIds[itemId]` | **losing** elements | killing one calls `defeat()` (`quest/AbstractQuest.as:237-241`); a non-empty `keyIds` also **disables the army-wipe loss** unless `alwaysEndIfMyUnitsDie` is true (`quest/AbstractQuest.as:287-295`) |
| `reinforcementIds[itemId]` | friendly elements | affiliation forced to `PLAYER_SELF`, non-selectable for buildings (`quest/AbstractQuest.as:141-163`) |
| `friendlyAreas` | rectangles converted to friendly ground | `MapInitializer.convertAreaToFriendly` at `start()` (`quest/AbstractQuest.as:376-379`) |

Two more flags matter:

* `unitTypesExcluded` / `unitTypesIncluded` filter the player's army by `group_type`
  (`quest/AbstractQuest.as:488-494`). Only three quests use it, all excluding
  `GROUP_TYPE_AIR_VEHICLE`: `Quest07Ship` (`:81-83`), `Quest08Rocket` (`:88-90`),
  `Quest09Laboratories` (`:95-97`).
* `alwaysEndIfMyUnitsDie` — only `Quest07Ship` sets it to `true` (`:178`).

### 2.2 `mapLoaded` — classifying the map

`AbstractQuest.mapLoaded` (`quest/AbstractQuest.as:105-180`) walks
`Base.Main.buildingArray` once and, for every element:

1. if its id is in `importantIds` → `qChapter.addElement(def, element)`; if the element
   is an *important item* the chapter also scans its surroundings
   (`chapter/checkSurroundings`) to find the defenders;
2. if its id is in `keyIds` → record it in `keyElements`;
3. deco / atrezzo elements → affiliation `PLAYER_NEUTRAL`;
4. units that are **not** reinforcements → affiliation `PLAYER_ENEMY`;
5. buildings that **are** reinforcements → `PLAYER_SELF`, `selectable = false`;
6. counts `Quest.numPlayerUnitsNow` (player units, healers excluded) and
   `remainingFoes` (everything else).

`uncountHealers()` (`:182-192`) removes healer units from the player's "alive" count.

### 2.3 `elementKilled` — the common result engine

`AbstractQuest.elementKilled` (`quest/AbstractQuest.as:232-282`) is the heart of the
economy:

```
if (keyIds[el.iID])  → defeat()                       // losing element destroyed
switch (el.PlayerID):
  PLAYER_SELF:  army[el.id].killed++ ; numPlayerUnitsNow--
  PLAYER_ENEMY: gold += (el.attack > 0 ? 5 : 0)
                 xp   += max(1, ceil(gold/20))   (0 for walls)
                 if (el is IsoUnit) remainingFoes-- ; updateCountdown()
                 if (remainingFoes <= 0) enableActivator()
if (numPlayerUnitsNow == 0) prepareQuestEnd(3)          // 3-second loss timer
return [gold, xp]
```

`Quest.elementKilled` (`quest/Quest.as:363-381`) wraps this: summoned units are ignored
(`[0,0]`), and the gold total is capped at `Base.Items.globals.MAX_GOLD_QUEST` — **which
does not exist in the upstream config**, so the cap never fires.

At `Quest.end()` the XP is clamped to half the gold gained
(`quest/Quest.as:412-415`).

### 2.4 `end` and `sendResults`

`Quest.end()` (`quest/Quest.as:404-441`):

1. clamp XP to `gold / 2`;
2. `recoverUnits(arPlayerUnits, getRecoveredUnitsPercentage())` — default
   `Constants.PERCENT_UNITS_RECOVERED_ISLE = 60` (`core/Constants.as:2102`).
   The algorithm (`quest/Quest.as:452-481`): `lost = totalKilled - ceil(totalKilled * pct/100)`,
   then up to 50 random units are removed from the *recovered* pool until `lost` units
   are un-recovered;
3. `getFreeUnits()` is appended to the army (every quest returns `[]`);
4. `questEnd.dispatch({id, difficulty, win})` and `questFinished.dispatch(win)`;
5. `currentQuest.end(null)` → opens `PopupQuestFinished`.

`AbstractQuest.sendResults()` (`quest/AbstractQuest.as:430-461`) builds the payload and
the reward list:

```json
{ "map": <townID>, "units": <counted army array>,
  "win": 0|1, "duration": <seconds>, "voluntary_end": 0|1,
  "quest_id": "<quest id>", "difficulty": 1|2|3 }
```

Rewards pushed: `gold = Quest.iGoldGained`, `xp = Quest.iXPGained`, and **only on a win**
the static `globals.REWARDS_QUESTS[questIds.indexOf(id)]` — plus an extra
`xp = min(round(gold/4), exp_required/3)` for the gold entry (`quest/AbstractQuest.as:449-457`).

The command is `CmdEndQuest`; the quest rank is persisted with
`AdminCmdSetQuestRank(String(Quest.iQuest), String(difficulty))`.

### 2.5 Unit recovery and free units

* `getRecoveredUnitsPercentage()` → 60 % for every quest (`quest/AbstractQuest.as:364-367`).
* `getFreeUnits()` → `[]` for every quest, including `Quest01Bazooka` which overrides it
  with an explicit `[]` (`quest/Quest01Bazooka.as:260-263`).

---

## 3. Difficulty

### 3.1 The scaling rule

`AbstractQuest.difficulty` is a **setter with side effects** (`quest/AbstractQuest.as:382-423`).
Setting it re-scans the map and duplicates enemy units:

| Difficulty | Extra enemy units added per existing enemy unit | Code |
|---|---|---|
| 1 | 0 | early `return` at `:389-392` |
| 2 | 1 | `:412-418` |
| 3 | 2 | `:402-410` (one) + `:412-418` (one) |

Each copy is placed on a free neighbouring tile found by
`Base.Iso.encontrarTileProximaLibre` and is added as `PLAYER_ENEMY`; `remainingFoes` is
incremented for each copy.

**Consequences for a server-side re-implementation:**

* The setter is a *mutation of the map*, not a scalar. The extra units are ordinary map
  elements and are killed by the same rules.
* It is applied **once**, at quest start (`popups/PopupLoadingQuest.as:132-136`). Units
  spawned later at runtime (the convoy waves, the airstrike planes, the kamikaze rows)
  are **not** scaled.
* `Quest.DIFFICULTY_MULTIPLIER = 0.5` (`quest/Quest.as:127`) is declared but never read
  anywhere in the client.
* The `DIFFICULTY_MULT_*_LIFE` / `DIFFICULTY_MULT_*_ATCK` constants in `Quest01Bazooka`
  (`:35-41`) and `Quest05AssaultConvoy` (`:27-33`) are **dead code** — no stat scaling
  is implemented anywhere. Difficulty changes the *number* of enemies, never their stats.
* `Quest13Tyrannosaurus` overrides the setter with a **no-op** (`:239-247`), so difficulty
  has no effect at all in that quest.
* `Quest01Bazooka` re-implements the setter (`:278-319`) with identical behaviour.
* `QuestWeekly01` reports difficulty 1 unconditionally
  (`popups/PopupWeeklyQuestFinished.as:98`).

### 3.2 How the difficulty is chosen and recorded

* The player picks 1–3 stars in `PopupLoadingQuest`. The highest available difficulty is
  gated by the quest rank the player has already achieved
  (`popups/PopupLoadingQuest.as:46-75`).
* The achieved difficulty is stored in `Base.Player.questsRank[questIndex]`
  (`managers/PlayerStatus.as:566-576`) and sent with `admin_set_quest_rank`.
* The rank key is the **quest index** (1…22), not the quest id.

### 3.3 Level gates

* `Config.QUESTS_MIN_LEVEL = 4` (`core/Config.as:146`) — the level needed to enter the
  Missions World / Weekly Quest at all (`core/isoengine/delegates/buildings/BasicTravelDelegate.as:30-32`,
  `GUI/GuiManager.as:1703-1720`).
* `globals.QUESTS_MIN_LEVELS = {"100000021":40, "100000022":40, "100000025":40, "100000026":40}`
  — the four team quests, read in `popups/PopupQuestsMap.as:198-202`. The value is
  **server data**, not client code.
* The `levelRequired` getter (`quest/AbstractQuest.as:463-466`) returns 0 in the base and
  is overridden to 1 in exactly three quests (`Quest01Bazooka:71-74`,
  `Quest05AssaultConvoy:102-105`, `Quest13Tyrannosaurus:51-54`). **No code anywhere reads
  it** — the real gate is `QUESTS_MIN_LEVELS`. Treat `levelRequired` as vestigial.

### 3.4 Cooldowns

* `Config.QUESTS_PERIOD_HOURS = 4` (`core/Config.as:140`). `Quest._timeForNextQuestPlay(id)`
  (`quest/Quest.as:195-206`) returns the seconds left of the 4-hour window.
* When `Base.Main.abTimerQuests` is set, the gate is **global** — the maximum over all
  quests — instead of per quest (`quest/Quest.as:208-219`, `523`).
* The weekly quest is available **only on Sunday** and at most once per 24 h
  (`quest/Quest.as:507-525`).
* The server records the last play time in `map.questTimes[questId]`
  (`upstream/socialwarriors/command.py:802`).

---

## 4. The per-quest table

| # | id | class | name | lv | victory condition (one line) | free units |
|---|---|---|---|---|---|---|
| 0 | `100000049` | `QuestWeekly01` | Weekly Mission! | 0 | Kill all 5 gun bots (each opens a chest) within 90 s | none (army is spawned by the quest) |
| 1 | `100000001` | `Quest01Bazooka` | DEFEAT THE ENEMY | 1 | Reduce the Orc Commander to near death, then his jeep to near death | `[]` |
| 2 | `100000006` | `Quest06Airstrike` | AIRSTRIKE! | 0 | Clear the radio station, call the airstrike, then destroy the enemy command centre | `[]` |
| 3 | `100000003` | `Quest03DefendConvoyAuto` | DEFEND THE CONVOY | 0 | Get all 3 allied trucks to the far side of the map alive | `[]` |
| 4 | `100000004` | `Quest04Supertank` | STOP THE BIG WEAPON | 0 | Destroy both ammo pieces, then destroy the assembled Megatank | `[]` |
| 5 | `100000005` | `Quest05AssaultConvoy` | DESTROY THE TRUCK | 1 | Destroy the enemy truck before it leaves the zone (120 s) | `[]` |
| 6 | `100000002` | `Quest02CentralNuclear` | BLOW THE POWER PLANT | 0 | Destroy the nuclear plant (towers go offline), then the command centre | `[]` |
| 7 | `100000007` | `Quest07Ship` | V.I.P ENEMY | 0 | Take the ship from the harbour, then destroy the enemy command centre | `[]` |
| 8 | `100000008` | `Quest08Rocket` | Dangerous rocket! | 0 | Destroy the enemy rocket launcher before the 600 s timer expires | `[]` |
| 9 | `100000009` | `Quest09Laboratories` | Destroy all the labs | 0 | Clear the radio station; the airstrike destroys the 5 labs | `[]` |
| 10 | `100000010` | `Quest10SpecialOps` | STEAL THE LAPTOP | 0 | Kill every enemy, then walk the commando into the bunker | `[]` |
| 11 | `100000011` | `Quest11SaveVillages` | RESCUE THE ALLIES | 0 | Move every civilian off both allied villages within 240 s | `[]` |
| 12 | `100000012` | `Quest12TankBoss` | THE MECHANICAL MENACE | 0 | Kill the two-phase Golem boss | `[]` |
| 13 | `100000013` | `Quest13Tyrannosaurus` | DEFEAT THE DINOSAURS | 1 | Kill the T-Rex, then the Fire-T-Rex | `[]` |
| 14 | `100000014` | `Quest14Spy2` | The River | 0 | Kill every enemy, then open the prison with the commando | `[]` |
| 15 | `100000017` | `Quest15HCCrusaderBase1` | VIKINGS BEACHHEAD | 0 | Kill every enemy unit on the map | `[]` |
| 16 | `100000018` | `Quest16HCAliens` | KILL THE ALIENS | 0 | Kill every enemy unit on the map | `[]` |
| 17 | `100000019` | `Quest17HCArachnids` | ARACHNID MENACE | 0 | Kill every enemy unit on the map | `[]` |
| 18 | `100000020` | `Quest18HCDragons` | ERRADICATE THE DRAGONS | 0 | Kill every enemy unit on the map | `[]` |
| 19 | `100000021` | `Quest19HC` | DR.SHOCK'S MECH ARMY | 0 | Kill every enemy unit on the map | `[]` |
| 20 | `100000022` | `Quest20HC` | DR.SHOCK'S MONSTERS | 0 | Kill every enemy unit on the map (killing a mech wakes a kamikaze row) | `[]` |
| 21 | `100000026` | `Quest23HC` | THE WICKED NEBULARS | 0 | Kill every enemy unit on the map | `[]` |
| 22 | `100000025` | `Quest24HC` | DR. SHOCK STRIKES BACK | 0 | Kill every enemy unit on the map (Dr. Shock has 5000 life) | `[]` |

Level gates from the server: `100000021`, `100000022`, `100000025`, `100000026` require
**level 40**; all others are reachable once the player is level 4 (the harbour gate).
Team selection (`Config.QUESTS_WITH_TEAMS`, `core/Config.as:160`) applies to the same
four quests.

---

## 5. The chapter / objective system

The `chapters/` package is the *campaign* system that also provides the quest
machinery. `AbstractQuest` owns a `Chapter` (`quest/AbstractQuest.as:97-102`), and the
`Chapter` class owns the persistent state machine.

### 5.1 The `Chapter` state machine

`Chapter.createEmptyStatus(id)` (`chapters/Chapter.as:151-163`) defines the canonical
status object — it is exactly the shape the server stores in `map.currentQuestVars`:

```json
{ "id": 0, "spawned": false, "ended": false, "visited": false,
  "activators": [], "boss": [], "treasure": [], "killed": [] }
```

`Chapter.prepareChapterStatus` (`:203-230`) reuses the server's copy when
`Base.Main.currentQuestProperties` still refers to the same chapter id and is not ended;
otherwise it starts from an empty status.

Every mutation is persisted by `Chapter.saveChapterStatus(key)`
(`chapters/Chapter.as:662-666`):

```actionscript
Base.Main.currentQuestProperties[key] = this.chapterStatus[key];
Base.Commands.queueCommand(new CmdSetQuestVar(key, this.chapterStatus[key]), true);
```

`CmdSetQuestVar` (`commands/CmdSetQuestVar.as:8-13`) emits the wire command
`set_quest_var` with `args[0] = key` and `args[1] = JSON(value)`.

| key | written by | meaning |
|---|---|---|
| `id` | `Chapter` on spawn (`:1082`) | the chapter id this status belongs to |
| `spawned` | on spawn (`:1081`) | the chapter was actually placed on the map |
| `ended` | `ChapterManager.finalizeChapter()` (`chapters/ChapterManager.as:504-505`) | the chapter was completed |
| `visited` | `Chapter.visited` | the player has been here before |
| `activators` | `onActivatorCollected` (`:527`) | chapter-segment ids whose activator was collected |
| `boss` | `onBossKilled` (`:584`) | indices into `arBosses` |
| `treasure` | `onTreasureCollected` (`:538`) | indices into `arTreasures` |
| `killed` | `saveElementKilled` (`:555`) | chapter element ids already killed (so a re-entered chapter does not respawn them) |
| `translation` | `checkQuestState` (`:243`) | the chapter's localisable string table |
| `idSimpleChapter` | `SimpleChapter.init` (`chapters/SimpleChapter.as:105-113`) | the current *simple* (endless) chapter id |
| `playerLevel`, `startTile` | `SimpleChapter.init` (`:109-113`) | the level/tile the simple chapter was generated for |

`Chapter.cleanChapterStatus()` (`chapters/Chapter.as:165-174`) resets every key to its
empty value and sends one `set_quest_var` per key.

### 5.2 `idSimpleChapter` — the endless chapter

`SimpleChapter` (chapter 9+, `ChapterManager.CHAPTER_09_SIMPLE`) is a procedurally
generated "enemy base detected" encounter. Its identity is stored in
`chapterStatus.idSimpleChapter`; the level and start tile are stored next to it so the
same map is regenerated on re-entry (`chapters/SimpleChapter.as:105-127`).

The upstream server **deliberately ignores** this key:

```python
if key == "idSimpleChapter":
    print(f"Ignored {key}")
    return
```
(`upstream/socialwarriors/command.py:91-95`)

so the endless chapter never advances server-side — the client keeps its own copy in
`map.currentQuestVars`, which the server *does* store generically
(`command.py:107-117`). A re-implementation must decide whether to reproduce this
behaviour or to make the server authoritative.

### 5.3 Objectives, activators and the "goal" element

`Chapter.setChapterMap` (`chapters/Chapter.as:199-201`) is overridden per chapter. The
`SimpleChapter` version (`:148-210`) builds the map from a `ChapterDefinition`:
towers, walls, the **goal** element, special foes and ordinary foes, all placed
relative to `startTile`. The goal element is neutral, has `onKillDefenders` and becomes
collectable once its defenders are dead (`:177-187`, `212-230`).

For the *quest* chapters (the ones quests use) the objectives are expressed through
`importantIds` and the `ChapterElement` vocabulary
(`chapters/ChapterElement.as:8-61`):

| `ChapterElement` field | meaning |
|---|---|
| `chapterId` | the handle used in cutscenes (`Highlight`, `MoveElement`, `RemoveElement`, `SpawnSegment`) |
| `canDie` | `false` → the element's health is clamped to 1 and it never dies |
| `attackable` | `false` → the element cannot be targeted |
| `affiliation` | override the element's `PlayerID` (`PLAYER_SELF` / `PLAYER_ENEMY` / `PLAYER_NEUTRAL`) |
| `onKill` | fired when the element is destroyed |
| `onNearDeath` | fired when the element's health crosses 10 % of max life (`core/isoengine/IsoFightingElement.as:469-472`); forces `canDie = false` (`chapters/Chapter.as:917-921`) |
| `onKillDefenders` | fired when all units defending the element are dead |
| `needs` | the element is only available while all listed chapter ids are `active` |
| `active` | the element is currently part of the objective |
| `swap` | whether the element may be swapped in a chapter segment |

Chapter completion for the *campaign* chapters is
`activatorsDone && bossDone && treasureDone` (`:523-526`, `:631-644`); the quest
chapters bypass this and end through their own cutscenes.

### 5.4 How quests and goals interact

The `core/goals/` package is the mission/objective list ("Goals"). The two goal classes
that touch quests are:

* `GoalCompleteQuest` (`core/goals/GoalCompleteQuest.as:15-56`) — subscribes to
  `Quest.questEnd` and completes when `{id, difficulty, win}` matches
  (`questId`, `minDifficulty`, `winRequired`). It also short-circuits if
  `Base.Player.questsRank[questIds.indexOf(questId)]` already exists (`:28-34`).
* `GoalCompleteChapter` (`core/goals/GoalCompleteChapter.as:17-70`) — subscribes to
  `ChapterManager.chapterFinished` and optionally spawns the chapter.

`AbstractQuest.prepareInit` marks the quest's chapter as `visited` when the player
already has a rank for it (`quest/AbstractQuest.as:98-101`).

---

## 6. What a server-side re-implementation must implement

### 6.1 The quest catalogue (data, not code)

For each of the 23 playable quests the server needs, as data:

1. **id, class-equivalent name, map id, play-order index** (the index selects the
   reward row).
2. **The victory condition** as an explicit predicate — see §4 and
   [`../data/quests.json`](../data/quests.json) (`victoryCondition`).
3. **The failure conditions** (timer expiries, key elements, army wipe).
4. **The scripted element table**: which item ids are important / key / reinforcement,
   their affiliation, and which callback (`onKill`, `onNearDeath`, `onKillDefenders`)
   fires.
5. **The map-specific constants**: init tile, timers, wave tables, patrol routes,
   airstrike target tiles, friendly areas, spawn points, script positions.
6. **Difficulty behaviour** — the enemy-duplication rule, and per-quest overrides
   (no-op for `Quest13Tyrannosaurus`).
7. **Rewards** — the static row from `globals.REWARDS_QUESTS` plus the dynamic
   per-kill gold/XP formula.

### 6.2 The rules engine

Because the whole quest system is expressed in terms of the *iso engine*
(`core/isoengine/IsoEngine.as`, `IsoFightingElement.as`, `IsoUnit.as`) and the AI
(`battle/IA.as`, `IAAttack.as`, `IAConvoy.as`), a faithful re-implementation needs:

* a deterministic, seeded simulation of unit movement (`IA_Move`), target acquisition
  (`Base.Iso.getNearestTarget` / `getNearestUnits`), attack resolution and the
  `nearDeath` threshold at 10 % health (`core/isoengine/IsoFightingElement.as:469-472`);
* the enemy-duplication pass of the difficulty setter;
* the `elementKilled` result engine (gold/XP, `remainingFoes`, `numPlayerUnitsNow`,
  key-element loss, 3-second loss timer);
* the unit-recovery pass (`60 %` recovery, random loss of up to 50 units);
* the scripted-objective interpreter (`onKill` / `onNearDeath` / `onKillDefenders` →
  next objective, spawn, timer, or win);
* the timer-driven mechanics: convoy waves and trucks, the assault-convoy countdown,
  the rocket countdown, the save-the-villages countdown and the 15-second rescue check,
  the weekly 90-second timer;
* the scripted airstrike (hard-coded bomb target tiles per quest, `int.MAX_VALUE >> 2`
  damage);
* the scripted patrol routes for the two stealth quests (25 and 21 patrol units) and
  the `IA.STATE_PATROL` behaviour;
* the scripted "kamikaze activation" of `Quest20HC`.

**Determinism requirement.** The original client is *not* deterministic: it uses
`Math.random()` for wave composition, wave spawn points, unit placement
(`encontrarTileProximaLibre`), bomb order, unit-recovery losses, patrol placement and
wall placement (`chapters/SimpleChapter.as:174`). A server-authoritative
implementation must replace every one of these with a **server-issued seed**
(`AGENTS.md` → *Architecture Non-Negotiables* #3, #8). The client is the specification
for *what* happens; the seed decides *which* variant happens.

### 6.3 The protocol

| Command | Direction | Payload |
|---|---|---|
| `end_quest` | client → server | JSON `{map, units, win, duration, voluntary_end, quest_id, difficulty}` + reward vector (`quest/AbstractQuest.as:430-459`) |
| `admin_set_quest_rank` | client → server | `[questIndex, difficulty]` (`quest/AbstractQuest.as:448`) |
| `set_quest_var` | client → server | `[key, JSON(value)]` for the chapter status machine (`commands/CmdSetQuestVar.as:8-13`) |

The upstream server's `end_quest` handler (`upstream/socialwarriors/command.py:752-806`)
is **a client-trusted stub**: it reads `win` and `difficulty` straight out of the payload,
computes the lost units from the client's own `units` array and stores
`questTimes[quest_id]`. A re-implementation must instead recompute the outcome from the
server's own simulation and reject the client's claim.

### 6.4 The parts that must **not** be re-implemented from the client

* `flash_debug`-style client-authoritative wallet writes — forbidden by
  `AGENTS.md` → *Architecture Non-Negotiables* #6.
* `USERID` from the request body — forbidden by #7; the quest result must be tied to the
  authenticated session.

---

## 7. Unresolved / UNVERIFIED

Everything in this section is stated as **UNVERIFIED** and must be resolved by
observation (the live client) or by an explicit design decision, not by reading the
decompiled code.

| # | Question | Why it is open |
|---|---|---|
| 1 | **UNVERIFIED** — the `setDifficulty` handler in `popups/PopupLoadingQuest.as:138-150` only assigns `this.difficulty = 1` for `star1`; there are no `star2` / `star3` branches. | Either an FFDec decompilation loss or a real bug. If real, the client can only ever play difficulty 1. The whole difficulty-2/3 enemy-duplication path would then be unreachable in the shipped game. |
| 2 | **UNVERIFIED** — `popups/PopupLoadingQuest.as:46, 141, 156` read `Base.Player.questsRank[Base.Main.currentFriend]`, but `currentFriend` is the *quest id string* in assault mode (`core/Base.as:6910`) while `questsRank` is keyed by the numeric quest index (`managers/PlayerStatus.as:566-576`, `popups/PopupQuestsMap.as:184-186`). | The lookup therefore yields `undefined` and the difficulty gate/`questsRank` read is broken. It is unclear whether this is the original behaviour or a client bug. |
| 3 | **UNVERIFIED** — `Quest08Rocket` declares the objective (`ID_BUILDING_ROCKET_LAUNCHER`) with `canDie: false` and an `onKill` victory callback (`quest/Quest08Rocket.as:147-152`). `Chapter.addElement` copies `canDie` onto the element (`chapters/Chapter.as:922-925`) and `IsoFightingElement` clamps the health to 1 when `canDie` is false (`core/isoengine/IsoFightingElement.as:508-518`). | By the code, the launcher can never be destroyed and the win callback can never fire — the quest would be unwinnable. Either the original relied on a different element, or this is an authoring bug. Needs live observation. |
| 4 | **UNVERIFIED** — the static win rewards are `globals.REWARDS_QUESTS[questIds.indexOf(id)]` (`quest/AbstractQuest.as:449`), i.e. positional. | If the new server re-orders the quest list, the rewards silently change. The mapping must be pinned by id, not by index. |
| 5 | **UNVERIFIED** — `Quest03DefendConvoyAuto`'s in-game description says *"Defeat all enemies before they destroy the allied convoy"*, but the implemented victory condition is *"get 3 trucks to the exit"*. There is no "all enemies dead" check in the class. | The description is player-facing text; the code is the specification. A re-implementation should implement the code, but the divergence should be confirmed against the live game. |
| 6 | **UNVERIFIED** — `Quest03DefendConvoyAuto` says "No flying units allowed on this quest!" but does not set `unitTypesExcluded`; only `Quest07Ship`, `Quest08Rocket` and `Quest09Laboratories` do. | The restriction may be enforced server-side (by the upstream's unit selection) rather than client-side. |
| 7 | **UNVERIFIED** — the exact enemy roster, the positions of the map entities, and the terrain of each quest map. | The terrain grid is in `managers/MapManager.as:120-142` (map ids 101…149), but the *buildings and units* are server map data (`upstream/socialwarriors/villages/quest/<id>.json`). The client class only names the ids it cares about. |
| 8 | **UNVERIFIED** — `Base.Items.globals.MAX_GOLD_QUEST` (the gold cap in `quest/Quest.as:373-377`) does not exist in the upstream `config/main.json`. | The cap is therefore never applied. Whether the real server had the key is unknown. |
| 9 | **UNVERIFIED** — the exact `nearDeath` threshold (10 % of max life) and the healing/armour model that feeds it. | `core/isoengine/IsoFightingElement.as:469-472` gives the threshold; the surrounding damage model is in `02-combat-and-units.md` and still needs a deterministic re-derivation. |
| 10 | **UNVERIFIED** — `Quest.setQuest` instantiates the quest class and `Quest.prepareInit` calls `currentQuest.prepareInit()`; but `AbstractQuest.prepareInit` also captures the player's army via `Base.Iso.getCurrentFilteredArmy`. | Whether the *server* is allowed to let the player choose the army at all (and which units are legal) is a product decision, not a client fact. |
| 11 | **UNVERIFIED** — the constants `QUEST_21_HARDCORE7` (`100000023`) and `QUEST_22_HARDCORE8` (`100000024`) exist in the client (`quest/Quest.as:97-99`) and in the server's `questTimes` map, but have **no class, no map and no upstream map file**. | They were presumably cut content. The re-implementation should decide explicitly whether to ship them as stubs. |
| 12 | **UNVERIFIED** — `QUEST_DEFEND_CONVOY` (`100000100`) has a constant (`quest/Quest.as:107`) and an empty `QuestDefendConvoy()` method in `Quest03DefendConvoyAuto` (`:87-89`), but no class, no map and no upstream map file. | Same as #11. |
| 13 | **UNVERIFIED** — `QuestWeekly01` sends `end_quest` with `"win": 1` **always**, even when the timer expires or the army is wiped (`popups/PopupWeeklyQuestFinished.as:94`). | The client always claims a win and reports the real outcome only in the popup text. A server-side re-implementation must not accept that. |
| 14 | **UNVERIFIED** — the exact cutscene dialogue and camera choreography of every quest. | The dialogue is in the classes and is listed per quest in `../data/quests.json`; reproducing it verbatim is a content decision, not a rules decision. |

---

## 8. Appendix — the `AbstractQuest` hook reference

| Hook | Base implementation | Quests that override it |
|---|---|---|
| `prepareInit()` | resets state, captures army, creates the chapter | all 23 |
| `mapLoaded()` | classifies the map, counts foes | `Quest01Bazooka`, `Quest09Laboratories`, `Quest10SpecialOps`, `Quest14Spy2`, `Quest20HC`, `QuestHardcore` |
| `start()` | converts `friendlyAreas` | `Quest01Bazooka`, `Quest02CentralNuclear`, `Quest03DefendConvoyAuto`, `Quest04Supertank`, `Quest05AssaultConvoy`, `Quest06Airstrike`, `Quest07Ship`, `Quest08Rocket`, `Quest09Laboratories`, `Quest10SpecialOps`, `Quest11SaveVillages`, `Quest12TankBoss`, `Quest13Tyrannosaurus`, `Quest14Spy2`, `QuestHardcore` |
| `defeat()` | `Quest.end()` (immediate loss) | `Quest01Bazooka`, `Quest02CentralNuclear`, `Quest03DefendConvoyAuto`, `Quest05AssaultConvoy`, `Quest06Airstrike`, `Quest08Rocket`, `Quest09Laboratories`, `Quest10SpecialOps`, `Quest14Spy2` |
| `elementKilled(el)` | result engine (§2.3) | `Quest03DefendConvoyAuto`, `Quest06Airstrike`, `Quest09Laboratories` |
| `elementCollected(el)` | no-op | — |
| `end(e)` | stops the timer, opens `PopupQuestFinished` | `Quest01Bazooka`, `Quest03DefendConvoyAuto`, `Quest05AssaultConvoy`, `Quest08Rocket`, `Quest09Laboratories`, `Quest10SpecialOps`, `Quest11SaveVillages`, `Quest14Spy2`, `QuestHardcore` |
| `sendResults()` | builds the payload + rewards | — |
| `prepareQuestEnd(s)` | 3 s loss timer | `Quest11SaveVillages` |
| `enableActivator()` | no-op | — |
| `updateCountdown()` | no-op | `QuestHardcore` |
| `getInitTile()` | `{tx: 60, ty: 90}` | 13 quests (see `../data/quests.json`) |
| `getTileIdForMapPosition(i)` | `1` | `Quest01Bazooka` |
| `getTerrainTileId()` | `Constants.getId(ID_LAND_EXPANDABLE)` = 925 | — |
| `getWaterTileId()` | `5` | — |
| `getFreeUnits()` | `[]` | `Quest01Bazooka` (also `[]`) |
| `getRecoveredUnitsPercentage()` | `PERCENT_UNITS_RECOVERED_ISLE` = 60 | — |
| `get levelRequired()` | `0` | `Quest01Bazooka`, `Quest05AssaultConvoy`, `Quest13Tyrannosaurus` (all `1`) |
| `get/set difficulty` | enemy-duplication setter | `Quest01Bazooka`, `Quest13Tyrannosaurus` (no-op) |
| `isUnitExcluded(id)` | group_type filter | — |
| `getVillain()` (static) | `null` | every quest (portrait in the missions map) |
