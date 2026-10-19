# The UI Screen Inventory — the Modern Client's Rebuild Backlog

**Roadmap task B6.** The original Flash UI chrome is **not in the asset tree**. The
`assets/` directory contains gameplay art (sprites, FX, characters, magic), thumbnails,
chapter images and audio — but no HUD, no panels, no buttons, no popups. A modern client
must rebuild the entire interface. This document and its table turn "rebuild the UI" from a
scaling risk into a backlog.

| | |
|---|---|
| **Source** | The decompiled client, `.work/as/basesec/scripts/` |
| **Tooling** | `node scripts/analyze-ui.mjs` → [`../data/ui-screens.json`](../data/ui-screens.json) |
| **Scale** | **260 UI classes**, **698 user-facing strings**, **122 image references** |

---

## 1. What was inventoried

| Kind | Count | Where |
|---|---|---|
| `popup` | **95** | `scripts/popups/**` |
| `gui-panel` | **57** | `scripts/GUI/**` |
| `movieclip` | **108** | top-level `*MC.as` files that are interface, not gameplay sprite |

The top level of the client holds **251** `*MC.as` files in total. The other 143 are
gameplay or effect movie clips (unit portraits, resource icons, building shells) and are
correctly *not* UI. Only the interface-bearing ones are in the table.

### The popup tree

| Directory | Popups | Subject |
|---|---|---|
| `popups/` | 70 | the core interface: buildings, quests, attacks, inventory, market, goals |
| `popups/alliances/` | 11 | alliance centre, join/create, member lists, messages |
| `popups/marketplace/` | 6 | the unit marketplace and bidding |
| `popups/cross/` | 4 | cross-promotion |
| `popups/teamSelection/` | 2 | choosing an army before an attack |
| `popups/SoulMixer/` | 1 | the Atom Fusion / Soul Mixer |
| `popups/darts/` | 1 | the darts minigame |

## 2. What each entry records

For every UI class the table captures:

| Field | Why it matters |
|---|---|
| `class`, `path` | identity |
| `kind` | popup / gui-panel / movieclip / info-button / tab / button |
| `extends` | the base class it builds on (e.g. `PopupBuildingMC`, `PopupObject`) |
| `isMovieClip` | whether the class is a timeline asset or logic |
| `literals` / `literalCount` | the **user-facing strings** — the copy that must be rewritten |
| `images` | the **image references** — the chrome that has to be recreated |
| `functions`, `overrides` | the interaction surface |
| `bytes` | the source size, a proxy for complexity |

`literalCount` sums to **698 distinct user-facing strings** across the interface. That is
the localisation surface: the modern client needs all 698 (or a decision to drop some).

`images` covers **122** referenced image assets. Since the chrome is not in the asset tree,
these are either missing, or they point at the 130 PNG / 578 JPG files that *are* present
(chapter art, intro art, news images) rather than at UI pieces.

## 3. The rebuild, grouped by what it costs

### 3.1 Gameplay-critical (must be rebuilt)

These are the screens without which the game cannot be played:

* **Building panel** (`PopupBuilding`, `PopupBuildingInventory`, `PopupBuildingInventoryItem`)
  — open a building, see its queue, upgrade it, collect from it.
* **Recruitment / training** (`PopupRecruitment`, `EPSW_MechanicTrainMC`, `EPSW_MedicTrainMC`)
  — buy and queue units.
* **Team selection** (`popups/teamSelection/*`, `PopupSelectionTeamWindow`) — choose the
  army before an attack.
* **Attack flow** (`PopUpBattleOptions`, `PopupLoadingAssault`, `PopupAttackFinished`,
  `PopUpLost`, `PopupNextIslandAttack`, `PopupAssaultHistory`) — the whole PvP loop.
* **Quest flow** (`PopupQuestsMap`, `PopupLoadingQuest`, `PopupQuestFinished`,
  `PopUpNextMission`, `PopupWeeklyQuest*`) — the chapter loop.
* **Inventory** (`PopupInventory`, `InventoryTabMC`, `InventoryItemMC`,
  `InventoryCollectionRewardMC`) — items, collections, rewards.
* **Resource / build menu** (`GuiManager`, `PopupExpand`, `StoreMC`) — spend resources,
  buy expansions, open the store.
* **Goals** (`PopupGoals`, `GoalProgressMC`, `NewGoalMC`) — the 134-goal tracker.
* **Neighbour strip / popup** (`FotoNeighbourMC`, `PopupVisit`, `PopupNeighbors`) — see and
  assist neighbours.

### 3.2 Supporting (rebuild as time allows)

* Darts minigame (`PopupDarts`, `TargetBitmap`, `popups/darts/*`)
* Marketplace and unit bidding (`popups/marketplace/*`, `PopupMarket`, `PopupMarketplaceAsset`)
* Alliances (`popups/alliances/*` — 11 classes)
* Atom Fusion / Soul Mixer (`popups/SoulMixer/*`, `EPSW_SoulMixerMC`, `PopupSoulMixer`)
* Cross-promotion (`popups/cross/*`, `CrossPromotionManager`)
* Premium account (`PopupPremiumAccount`, `premiumAccountItemMC`)
* Magic / wizardry (`PopupMagic`, `PopupWizardry`, `MagicManager`)
* Research centre (`PopupResearchCenter`, `LaboratoryTechDelegate`)
* Hospital / hero resurrection (`PopupHospital`, `PopupUnitCollectionBuyMC`)

### 3.3 Cosmetic (likely droppable)

* `SquareTool` and the debug tile overlays (`DebugTile*`, `TowerRadar`)
* Share / open-graph widgets (`rt_open_graph_unit` UI, `NewIconImg`)
* Legacy Flash-only affordances (the `spdebug` flag, the "Loading" splash variants)

## 4. What the inventory tells the client architecture

1. **The interface is logic, not art.** 260 classes, most extending a shared
   `PopupObject` / `*MC` base. The *structure* is portable; only the pixels are missing.
2. **The base classes are the reusable part.** `PopupObject` already models
   `params`, `priority`, `withGui`, `fadeIn` and `closeHandler` — a modal stack with
   priorities. That maps almost directly onto a React modal manager, and it tells us the
   original game had a **priority-ordered popup stack** that the clone should reproduce.
3. **698 strings is a real localisation job**, and it is bounded — that is good news.
4. **The 122 image references are a gap list.** Any image the interface references that
   is not in `assets/` is chrome the clone must design.
5. **The GUI folder is the HUD.** 57 classes in `GUI/` are the persistent interface
   (resource bar, minimap, tabs, portraits). This is the part that must feel right on
   desktop *and* mobile, so it should be designed once and laid out responsively.

## 5. Reproducing this

```bash
node scripts/decompile-client.mjs     # -> .work/as/basesec/
node scripts/analyze-ui.mjs           # -> re/data/ui-screens.json
```

## 6. Known limits

* The classification is **mechanical**: `kind` comes from the class name and its base
  class, not from reading what the screen does. The grouping in §3 is a reasoned
  reading of the table, not something the script asserts.
* `images` only captures literal file references (`"path/file.png"`). Art referenced
  through the SWF timeline (the `DefineShape`/`PlaceObject` data) is invisible to it —
  which is precisely the chrome that is missing.
* `literals` are the strings passed to `Language.getLiteral(...)`; strings embedded in
  the timeline text are not captured.
* The 143 top-level `*MC.as` files excluded as gameplay may still contain small UI
  elements (badges, counters). The classification boundary is a judgement call.
