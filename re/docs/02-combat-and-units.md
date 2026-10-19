<!--
  Generated investigation artifact.
  Source of truth for the details inside is the file it was produced from:
  decompiled ActionScript 3 (FFDec 26.3.0) of assets/flash/Basesec_1.5.4.swf,
  the Python server sources, and live traffic captured from a real Adobe Flash
  Player session against the local server.
-->

# Combat, Unit Stats & Progression

> **Scope:** Static decompilation of the AS3 client cross-referenced against config/main.json item stats.
>
> **Method:** Static decompilation of the AS3 client cross-referenced against config/main.json item stats.
>
> **Subject:** damage pipeline, damage types, special attacks, unit XP, combat trust boundary
>
> Part of the Social Wars reverse-engineering report set. See [`../README.md`](../README.md)
> for the document map and [`../docs/00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the
> cross-cutting conclusions.

---

# Social Wars (Zynga) — Combat, Unit Stats & Progression: Reverse-Engineering Report

**Scope:** combat resolution, unit/building stats, unit progression, and the client/server trust
boundary of the Flash (ActionScript 3) client.

**Primary sources**

| Source | Path |
| --- | --- |
| Decompiled AS3 client | `<as3-root>` (all `file:line` refs below are relative to this root) |
| Game data config | `<upstream-repo>\config\main.json` (`items[]`, `globals{}`) |
| Reference server | `<upstream-repo>\command.py` |

**Note on naming:** the shipped build identifies itself as `Config.GAME_NAME = "SexWars"`
(`scripts/core/Config.as:70`) and `Config.VERSION = "1.5.4"` (`scripts/core/Config.as:8`) — this is the
open-source re-skin of Social Wars. Gameplay data (`main.json`) is essentially the original SW data set.

---

## 1. Stat fields: config → AS3 property mapping

### 1.1 Where config stats are read

`main.json` `items[]` is a flat array of 778 objects (469 `type:"b"` buildings, 308 `type:"u"` units,
1 `type:"l"`). **Every item carries the same 57 fields**, so buildings and units share one schema.

The canonical read site is `scripts/core/isoengine/IsoElement.as:264-275`:

```
264:  if(this is IsoFightingElement)
265:  {
266:     IsoFightingElement(this).iHealth       = this.buildingReference.building.life;
267:     IsoFightingElement(this).uiAttack      = this.buildingReference.building.attack;
268:     IsoFightingElement(this).uiDefense     = this.buildingReference.building.defense;
269:     IsoFightingElement(this).iAttackInterval = this.buildingReference.building.attack_interval;
270:     IsoFightingElement(this).iAttackRange  = this.buildingReference.building.attack_range;
271:  }
272:  if(this is IsoUnit)
273:  {
274:     IsoUnit(this).uiSpeed = this.buildingReference.building.velocity;
275:  }
```

`maxLife` is set separately in the `IsoFightingElement` constructor
(`scripts/core/isoengine/IsoFightingElement.as:165-166`):
`this.maxLife = this.buildingReference.building.life; this.iHealth = this.maxLife;`

### 1.2 Full config field → meaning table (all 57 `items[]` fields)

| Config key | Read by (AS3) | Meaning / how it is used |
| --- | --- | --- |
| `id` | `IsoElement.iID` (`IsoElement.as:196`) | Item id. `Constants.getId()` is identity (`Constants.as:2209-2212`), so `Constants.ID_UNIT_SOLDIER_1 == 1007`. |
| `name` | `IsoElement.sName` (`IsoElement.as:197`) | Display name. |
| `type` | `Constants.TYPE_BUILDING "b"` / `TYPE_UNIT "u"` (`Constants.as:1666,1668`) | Decides unit vs building. |
| `cost` / `cost_type` | — | Legacy/unused for combat. |
| `costs` | `IsoBuilding.upgrade()` (`IsoBuilding.as:566`) | JSON string `{"w":50,"g":10,...}`; build/upgrade cost per resource. |
| `xp` | `IsoFightingElement.die` (`IsoFightingElement.as:692`) | XP token dropped when an enemy unit dies (`parseInt(building.collect_xp)` is used for units). |
| `display_order` | UI only | Store ordering. |
| `activation` | `IsoElement.activation` (`IsoElement.as:198-234`) | **Seconds** until a resource building can be collected again. `collected_at >= activation` ⇒ collectable. |
| `inventory_ids` | `IsoElement.as:246`, `IsoBuilding.as:997` | `null` = instant build; non-null = must be *activated* by a click after the build timer. |
| `expiration` | `IsoElement.expiration` | Cosmetic/chapter expiry. |
| `collect` | `IsoBuilding.collect` (`IsoBuilding.as:1181`) | Base resources produced per collection tick. |
| `max_collects` | `IsoElement.as:221-230` | Number of collections before the building stops producing. |
| `collect_type` | `IsoBuilding.canCollect` (`IsoBuilding.as:1047-1063`) | `w`/`g`/`o`/`s`/`c` — which silo/resource is consumed. |
| `collect_xp` | `IsoFightingElement.die` (`IsoFightingElement.as:692`) | XP granted when the unit dies. |
| `category_id` / `subcategory_id` / `subcat_functional` | `Constants.SUBCATFUNC_*` | Functional class. **Combat-relevant**: `81` = siege, `80` = archer, `71` = peasant/worker, `135` = town hall, `211`/`231` = turret/fortress. |
| `min_level` | `IsoBuilding.upgrade` (`IsoBuilding.as:572`) | Player level required to build/upgrade. |
| `width` / `height` | `IsoEngine.distance` (`IsoEngine.as:2023-2033`) | Footprint in tiles. Affects target distance (centre = `tx - floor((width-1)/2)`) and effective attack range. |
| `giftable`, `gift_level` | gift flow | Not combat. |
| `max_frame` | animation | Not combat. |
| `img_name` | graphics | Not combat. |
| `elevation` | z-order | Not combat. |
| `unit_capacity` | `IsoInteractiveElement.iUnitCapacity` (`IsoInteractiveElement.as:85`), `IsoFightingElement.uiAttack` getter (`:1324`) | How many units fit inside. **Also divides the building's own attack** (see §2.6). |
| **`attack`** | `uiAttack` (`IsoElement.as:267`) | Raw attack power before multipliers. |
| **`defense`** | `uiDefense` (`IsoElement.as:268`) | Flat damage subtraction in `calculateDamage`. In the shipped data every non-decorative item has `defense = 1` (640 items at 1, 138 at 0). |
| **`life`** | `iHealth`/`maxLife` (`IsoElement.as:266`, `IsoFightingElement.as:165`) | Hit points. Unit life ranges 25 → 15000. |
| **`velocity`** | `uiSpeed` (`IsoElement.as:274`) | Movement speed in **pixels per frame** (tile = 108×54 px, `Config.as:106-107`). 5 px/frame ≈ 1 tile / 21.6 frames @30 fps. Not a combat stat. |
| **`attack_range`** | `iAttackRange` (`IsoElement.as:270`) | Attack range in tiles. |
| **`attack_interval`** | `iAttackInterval` (`IsoElement.as:269`) | **Frames** between attacks (30 fps ⇒ 35 frames ≈ 1.167 s). Unit values observed: 25, 30, 35, 40, 45, 60, 90, 110, 180, 20, 50, 1. |
| `new_item` | UI | — |
| **`population`** | `IsoUnit.iPopulationCount` (`IsoUnit.as:304`), `IsoBuilding.uiPopulationGranted` (`IsoBuilding.as:119`) | Population consumed. Also gates `stun` (see §3.8). |
| `giftable`/`gift_level` | — | — |
| `cost_unit_cash` | `IsoBuilding.UnitTrainingStart` (`IsoBuilding.as:282`) | Cash cost to *instant-train* one unit. |
| `race` | `Constants.isEnemyId` (`Constants.as:2219-2227`) | Faction. |
| `clicks_to_build` | `IsoElement.currentBuildingStep` (`IsoElement.as:239-246`) | Number of build clicks; 0 = instant. |
| `trains_ids` | `IsoBuilding.iIDUnitTrained` (`IsoBuilding.as:125`) | Item id this building trains. `-1` = none. |
| `upgrades_to` | `IsoBuilding.getUpgradeBuilding` (`IsoBuilding.as:704`) | Next-tier item id. |
| **`best_against`** | `IsoFightingElement.recibirAtaque` (`IsoFightingElement.as:422`) | **Property name** of the *target* that this unit is strong against. Values in data: `ft_ground` (195 items), `ft_armored` (79), `ft_flying` (47), `ft_building` (20), `-1` (138, = none). |
| **`best_against_mult`** | `IsoFightingElement.as:424` | Damage multiplier applied when the target matches `best_against`. Mostly `1`; counter units use `2, 5, 10, 15, 20`. |
| `properties` | `PropertyManager` (`scripts/core/isoengine/PropertyManager.as`) | JSON blob of flags: `ft_ground`, `ft_armored`, `ft_flying`, `ft_building`, `healer`, `harvester`, `mechanic`, `human`, `animal`, `worker`, `fireman`, `boss`, `resurrectable`, `explosive`, `bulldozable`, `demolishable`, `tower`, `bunker`, `depot`, `farm`, `hq`, `silo`, `seeStealthUnits`, `waterborne`, `regenerating`, `chained`, `multiCollectable`, `auto_activable`, `raisePopulationCap`, `grants_population`, `resource`, `collectable`, `pickable`, `usable`, `activator`, `training_queue`, `wall`, `wonder`, `harvester`, `healer`, `friend_assistable`, `animated`, `ft__armored`(**never present**), `allows_spy`, `walkable`. |
| `syringes` | `PopupHospital` (`scripts/popups/PopupHospital.as:190`) | Cost in syringe items to resurrect this unit type. |
| `volume` | `AbstractDelegate.canGetInside` (`AbstractDelegate.as:109`) | Volume needed to enter a container. |
| `max_elem_vol` | `AbstractDelegate.canGetInside` | Max volume the container accepts. |
| `building_limit_same_id` / `building_limit_same_scf` | placement limits | Not combat. |
| `group_type` | `IsoFightingElement.shootProjectile` (`:327`), `CheckFunctions.inGroup` | `WATER_VEHICLE` etc. |
| `training_time` | `IsoBuilding.uiTrainingTime = training_time * 1000` (`IsoBuilding.as:122`) | **Milliseconds** to train one unit. |
| `premium_upgrade_costs` | `IsoBuilding.upgrade` (`IsoBuilding.as:574`) | Cash premium-upgrade costs. |
| `build_time` | build timer | Not combat. |

### 1.3 Notable stat relationships found in the shipped data

* **Counter units** (`best_against_mult` ≠ 1 and `best_against` ≠ `-1`) — only 4 exist:
  `Mortar Thrower` (id 1060) **10× vs `ft_building`**, `Antiaircraft battery` (1065) **20× vs `ft_flying`**,
  `B52` (1068) **5× vs `ft_building`**, `Demolition Tank` (1069) **15× vs `ft_building`**.
* `best_against` is a **property name**, not a class: the code calls
  `Base.Properties.elementHasProperty(this.iID, attacker.building.best_against)`
  (`IsoFightingElement.as:422`) — i.e. the *target item* must carry the flag.
* **Bug (verified):** `PropertyManager.FIGHTING_TYPE_ARMORED = "ft__armored"` (double underscore,
  `PropertyManager.as:18`) but the data uses `ft_armored` (single underscore) — `ft__armored` occurs
  **0 times** in `main.json`. Therefore the armoured checks in
  `ElectricDragonDelegate.as:165` and `MetallicDragonDelegate.as:199` **always fail** in this build.
* **Bug (verified):** `Constants.SUBCATFUNC_UNIT_SIEGE = 81` (`Constants.as:202`) but **no item in
  `main.json` has `subcat_functional == 81`**, so the siege damage modifiers (§2.5) are inert here.
  All 228 combat units are `scf = 80` ("archer"); the 6 peasants/workers are `scf = 71`.
* All 43 combat-capable buildings have `defense = 1`.

---

## 2. The attack resolution algorithm

### 2.1 Frame loop and attack cadence

* The stage runs at **30 fps** (`scripts/core/Base.as:110` — `[SWF(... frameRate="30")]`).
* `IsoEngine.Update()` increments `uiGameFrame` once per frame and pushes it to every element
  (`scripts/core/isoengine/IsoEngine.as:290-315`).
* `IsoUnit.Update(frame)` (`scripts/core/isoengine/IsoUnit.as:509-556`):
  * `iaIA.Update(frame)` (the AI/targeting) runs only every **61 frames** (`IsoUnit.as:512,527`).
  * `updateAttack(frame)` runs only when `(frame + iDelayAttack) % 5 == 0` and the unit is attacking
    (`IsoUnit.as:513,529-531`).
* `iDelayAttack = Math.floor(Math.random() * 5)` is drawn once per unit at construction
  (`IsoFightingElement.as:171`) ⇒ each unit has a random **phase offset of 0–4 frames**.
* The actual attack fires when `(frame + iDelayAttack) % iAttackInterval == 0`
  (`IsoUnit.as:653-659`). All shipped `attack_interval` values are multiples of 5, so the `%5` gate
  never suppresses a legitimate attack.

> **Effective DPS ≈ `attack × 30 / attack_interval`**, before defense/crit/variance, and assuming one
> damage instance per attack cycle (see §2.7 — machinegun streams only damage on the *first* bullet).

### 2.2 Range check

`IsoUnit.updateAttack` (`IsoUnit.as:638-660`):

```
640:  _loc3_ = Base.Iso.distance(this, this.TargetElement);       // euclidean tile distance (centres)
641:  _loc4_ = this.TargetElement.buildingReference.building.width - this.iAttackRange * 2;
642:  if(_loc4_ < 0) _loc4_ = 0;
646:  if(_loc3_[0] <= this.iAttackRange + _loc4_ && (…not moving…)) { … delegate.onAttack(); }
```

`distance()` (`IsoEngine.as:2017-2035`) computes the euclidean distance between **building centres**
(`tx - floor((width-1)/2)`), truncated to an int.

⇒ **Effective attack range = `iAttackRange + max(0, targetWidth − 2·iAttackRange)`.**
For unit targets (width 1) this is simply `iAttackRange`. For a wide building with a small
`attack_range` the range is widened to the building's footprint.

### 2.3 Targeting

`IsoFightingElement.acquireNewTargetFromElem` (`:946-955`) → `IsoEngine.getNearestTarget`
(`IsoEngine.as:1612-1684`):

* Search radius = `max(Config.AGGRO_RANGE = 10, iAttackRange)` (`IsoFightingElement.as:950`).
  (`Config.AGGRO_RANGE` = 10, `scripts/core/Config.as:116`.)
* Candidate pool = all *enemy* `IsoFightingElement`s (`arEnemyIsoFightingElements` /
  `arPlayerIsoFightingElements`, `IsoEngine.as:1646-1653`).
* Distance metric (`bucleNearestUnits`, `IsoEngine.as:1686-1721`): euclidean centre distance; if the
  candidate's `attack == 0` the distance is penalised by `+Config.AGGRO_RANGE`.
* **Score** (`getElementScore`, `IsoEngine.as:1723-1747`) — an `if / else if` chain, first match wins:
  `score = 1000 − distance`, then `+150` if the candidate is a **unit**, `+100` if it is the
  **town hall** (`scf == 135`), `+75` if `collect > 0` (resource building), `+50` if `uiAttack > 0`;
  **otherwise `score = −1` ⇒ never targeted**. ⇒ A plain non-town-hall building with
  `attack == 0` **and** `collect == 0` is untargetable; a depot/factory (`collect > 0`) *is* targetable
  (it is worth raiding for resources) but is penalised by `+AGGRO_RANGE` distance (§ below).
* Candidates are sorted by `score` desc, then `sort` (distance) asc; the first one passing the
  filter wins (`IsoEngine.as:1655-1678`).
* Filter `fCheckNearestTarget` (`IsoEngine.as:1913-1920`): target is an `IsoFightingElement`, is an
  enemy, is not dead, `canBeTargeted`, passes `attacker.canAttackElement(target)`
  (`IsoFightingElement.as:1246-1258` — attacker is not `blind`, target is not `stealth` unless the
  attacker has `seeStealthUnits`, target is `attackable`), and **if the target is a unit it must not
  be inside a container** (`eContainer == null`) ⇒ *units garrisoned in a bunker cannot be targeted*.
* `fCheckBattleUnit` (used for AoE queries, `IsoEngine.as:1931-1938`) additionally requires
  `uiAttack > 0` and `subcat_functional != 71` (peasants are not combat targets).
* Healer units instead pick the **most wounded** ally within `AGGRO_RANGE × 1.5`
  (`scripts/battle/IA.as:185-217`, `HealerDelegate.fCheckToHeal` at
  `scripts/core/isoengine/delegates/units/HealerDelegate.as:49-52`).

### 2.4 Damage pipeline — `IsoFightingElement.recibirAtaque` (`:399-610`)

This single function is the heart of the combat maths. In order:

| # | Step | Code | Formula |
| --- | --- | --- | --- |
| 1 | Shield multiplier | `:414` | `_ataque *= this._shieldMultiplier` (default 1; `activateShield(ms, mult)` at `:1392-1411`) |
| 2 | Delegate veto | `:415-418` | `if(!delegate.receiveAttack(dmg, attacker)) return 0;` — e.g. `AbstractBuildingDelegate.receiveAttack` multiplies by **50** for "vulnerable" attackers (`AbstractBuildingDelegate.as:39-57`) |
| 3 | `best_against` bonus | `:422-425` | `if(target has property attacker.best_against) nAtaque *= attacker.best_against_mult` |
| 4 | Stats modifiers | `:426-429` | `nAtaque *= sm.attackModifier` for every `StatsModifier` on the attacker (e.g. `DefaultStatsModifier(1.5, 1)` for "enlarge", `IsoUnit.as:35`) |
| 5 | Global multipliers | `:430-437` | `multiplierDamageDone` if the attacker is the player, else `multiplierDamageTaken` (both static, default 1 — `IsoFightingElement.as:51-53`) |
| 6 | Unit-XP flat attack bonus | `:438-441` | `nAtaque += attacker.buildingReference.unitXPLevel.extraAttack` |
| 7 | Siege modifiers | `:451-458` | attacker is siege → `nAtaque = ceil(nAtaque/2)`; target is siege → `nAtaque = ceil(nAtaque × 1.25)` (**inert in this build**, see §1.3) |
| 8 | Tutorial mode | `:459-465` | if the **player** is the target → `nAtaque /= 2` |
| 9 | `calculateDamage` | `:468`, impl `:222-252` | see below |
| 10 | Apply | `:473-476` | `if(!this.isInvincible) this.iHealth -= arAttack[0]` |
| 11 | XP grant to attacker | `:477-480` | `attacker.unitXPLevel.onDamageMade(arAttack[0])` — **only if the target is a unit** (`building.type == "u"`) |
| 12 | Death | `:508-518, 537-544` | if `iHealth <= 0`: `canDie`/`bDebugCanDie` false ⇒ clamp to 1, else `iHealth = 0` and `die(attacker)` |
| 13 | Call for help | `:559-596` | all allies within a **4-ring square** (Chebyshev radius 4) get `NearbyAllyAttacked` |

**`calculateDamage(base)` — `IsoFightingElement.as:222-252` (verbatim semantics):**

```
crit        = (Math.random() * 100 < 10)                       // PERCENT_CRIT  = 10   (:55)
variance    = Math.random() * 8 - 4                            // VARIANCE_DAMAGE = 8 (:59)  → [-4, +4)
raw         = crit ? (base + |variance|) * 1.5                 // CRIT_MULTIPLIER = 1.5 (:57)
                       : (base + variance)
raw        -= absorbed (always 0 in this build, :240-244)      // "armor" slot, hard-coded 0
dealt       = Math.round(raw - this.uiDefense)                 // flat defense subtraction
if(dealt < 1) dealt = 1                                         // MINIMUM DAMAGE = 1
return [dealt, crit, absorbed]
```

Consequences:
* **Minimum damage is 1** — no attack ever does 0.
* Variance is `±4` (uniform, from `Math.random()*8-4`), applied *before* defense.
* **Crits**: 10 % chance; damage becomes `(base + |variance|) × 1.5`. Because the variance term is
  absolute, a crit *always* deals at least `base × 1.5`.
* Defense is subtracted from the **final** number and the result is rounded; `defense = 1` in all
  shipped content, so defense is effectively a flat −1.
* `uiAttack` is *not* rounded anywhere; the whole chain is `Number` until `Math.round`.

**`uiAttack` getter (`IsoFightingElement.as:1317-1330`) — a building-specific twist:**

```
attack  = __uiAttack.value                    // config `attack`
if (bDead) return attack
cap     = building.unit_capacity
if (vUnitsContained && cap > 0) attack *= vUnitsContained.length / cap
return attack + __uiAttackExtra.value
```

⇒ **A building's own attack is proportional to how full it is.** A *Mega Bunker*
(`attack 18, unit_capacity 10`) deals 18 damage per shot with 10 troops inside, 9 with 5, 0 with 0.
`uiAttackExtra` is a runtime buff slot (set by spells).

**`maxLife` getter (`IsoFightingElement.as:1357-1365`):** `maxLife = __maxLife + unitXPLevel.extraLife`.

### 2.5 Where the attack value comes from (per delegate type)

| Delegate | Attack delivery | Citation |
| --- | --- | --- |
| `MeleeDelegate` | `target.recibirAtaque(self.uiAttack, self)` at the animation frame (optionally delayed by `args.delay` frames) | `delegates/units/MeleeDelegate.as:13-19`; registered for `ID_UNIT_ROBO_SWORDSMAN`, `ID_UNIT_ORC_SWORDMAN`, `ID_UNIT_ALIEN_CLAWS`, `ID_UNIT_DWARF_AXE`, `ID_UNIT_SAMURAI_MINIBOT`, `ID_UNIT_NEBULAR_MONSTER_MINI` (`DelegatesManager.as:1318, 1421, 1486, 1576`) |
| `ProjectileDelegate` | spawns a projectile with `attack = uiAttack`; on landing `target.recibirAtaque(projectile.attack, shooter)` | `delegates/units/ProjectileDelegate.as:11-17`; `IsoFightingElement.as:322-350, 357-373` |
| `MachinegunDelegate` | `addMachinegun(...)` — **only the first bullet deals damage** | `delegates/units/MachinegunDelegate.as:27-33`; `managers/ProjectileManager.as:460-473`; `battle/projectiles/Machinegun.as:59-75` |
| `DoubleMachinegunDelegate` | two machinegun streams (`projectilePoint`, `projectilePoint2`), `bulletInterval` frames apart | `delegates/units/DoubleMachinegunDelegate.as:28-35` |
| `MultiShotDelegate` | N projectiles every `interval` frames; **only the first has `doDamage=true`** | `delegates/units/MultiShotDelegate.as:38-76` |
| `HealerDelegate` / `MedicDelegate` | `target.recibirVida(self.uiAttack, self)` — **heals**, does not damage | `delegates/units/HealerDelegate.as:36-47` |
| `DroneDelegate` | fires one projectile per listed animation frame (`frames` array) | `delegates/units/DroneDelegate.as:18-30`; e.g. `Drone Master 2 Suppressor Gunner Drone` with `frames:[1,3]` (`DelegatesManager.as:971-974`) |
| `FlamethrowerDelegate` | machinegun + `incinerate(self, 5, 5, 1000)` on the target (5 dmg × 5 ticks, 1 s apart) | `delegates/units/FlamethrowerDelegate.as:30-59` |
| `KamikazeDelegate` | deals `maxLife × 2` to itself, then AoE `uiAttack` to ≤4 enemies in radius 2 + pushes them | `delegates/units/KamikazeDelegate.as:24-68` |
| `MortarDelegate` | 3 shots at animation frames 22/25/28, first one damaging | `delegates/units/MortarDelegate.as:25-60` |
| `PhalanxDroneDelegate` | `delegates/units/PhalanxDroneDelegate.as:39-48` | Applies `activateShield(shieldTime, shieldMultiplier)` to up to `numUnits` allies — a **damage-reduction buff** (e.g. 0.5 for 2 s) | `PhalanxDrone` (`Drone Master 2`, `DelegatesManager.as:977-983`) |
| `MachinegunTowerDelegate` / tower delegates | same as machinegun but from the tower | `delegates/buildings/MachinegunTowerDelegate.as:25-30` |
| `BasicFortressDelegate` (turrets/fortresses/bunkers) | one weapon per *attack point* facing the target, capped by `maxShooters` | `delegates/buildings/BasicFortressDelegate.as:50-84` |

**Machinegun detail (important):** `ProjectileManager.addMachinegun` (`:460-473`) creates the stream and
calls `shootProjectile(pDef, point, doDamage=true)` for the **first** projectile only
(`IsoFightingElement.shootProjectile` sets `projectile.attack = this.uiAttack` and wires
`landed → doProjectileDamage` only when `doDamage` is true, `:344-348`). The follow-up bullets emitted
by `Machinegun.tick()` (`battle/projectiles/Machinegun.as:67-74`) are created with
`ProjectileManager.addProjectile(...)` and **never get `attack` set nor a damage listener** — they are
purely visual. ⇒ *One machinegun attack cycle = exactly one `uiAttack` hit.*

### 2.6 Buildings as attackers

**Buildings have their OWN attack scheduler** — `IsoBuilding.Update(frame)`
(`scripts/core/isoengine/IsoBuilding.as:475-517`) — which differs from the unit scheduler in three
important ways:

```
486:  if (frame % this.iAttackInterval == 0
          && this.PlayerID != Constants.PLAYER_NEUTRAL
          && (scf == SUBCATFUNC_BUILDING_TOWER(211) || scf == SUBCATFUNC_BUILDING_CASTLE(231)
              || scf == SUBCATFUNC_BUILDING_TOWNHALL(135))
          && building.id != ID_BUILDING_COMMAND_CENTER_1)
```

1. **No `% 5` gate** and **no `iDelayAttack` phase** ⇒ *all* towers fire on the exact same frame
   (`frame % attack_interval == 0`), in lockstep. Unit attack intervals that are not multiples of 5
   (e.g. `attack_interval = 42` for the Mind Control Laboratory) therefore work for buildings but
   would be throttled for units.
2. Only `scf ∈ {211 TOWER, 231 CASTLE, 135 TOWNHALL}` buildings ever attack; the Command Center I
   (`id 26`) is explicitly excluded even though it is a town hall.
3. The range test is `Base.Iso.distance(this, target)[0] >= iAttackRange → drop the target`
   (`IsoBuilding.as:490`) — **centre-to-centre with no width adjustment**, so a tower's effective
   range is exactly `attack_range`. Unit targets (width 1) are therefore *harder* to hit than by a
   unit of the same range, because the unit's rule widens the range by the target's footprint.
4. Target acquisition uses `acquireNewTarget(tx − floor((width−1)/2), ty − floor((height−1)/2),
   iAttackRange)` (`IsoBuilding.as:505`) ⇒ the search radius is exactly `attack_range`, **not**
   `max(AGGRO_RANGE, attack_range)` as for units.
5. A tower whose 8 neighbours are all towers will not re-acquire a target
   (`isSorroundedByTowers`, `IsoBuilding.as:438-473`; only kicks in when
   `Base.Main.towersCount >= Config.NEW_TOWER_IA_TOWER_COUNT = 100`).

* `TowerDelegate` picks the weapon facing the target via `getTXTYTargetOrientation()`
  (`delegates/buildings/TowerDelegate.as:46-69`).
* `BasicFortressDelegate.onAttack` slices `attackPoints[orientation]` to `maxShooters` and fires one
  weapon per point (`BasicFortressDelegate.as:50-71`).
* `BunkerDelegate.onAttack` sets `maxShooters = self.vUnitsContained.length`
  (`delegates/buildings/BunkerDelegate.as:71-75`) ⇒ **a bunker fires once per garrisoned unit**
  (up to the number of attack points), each bullet carrying the *scaled* `uiAttack` from §2.4.
* `TowerDelegate.hasReachedConstructionLimit` uses
  `INITIAL_PER_LEVEL_TOWER + LIMIT_PER_LEVEL_TOWER × playerLevel` (`TowerDelegate.as:119-133`).
* `AbstractBuildingDelegate.receiveAttack` can multiply incoming damage by **50** when the attacker id
  is in the `vulnerableTo` dictionary (`AbstractBuildingDelegate.as:39-57, 157-176`).

### 2.7 `velocity`

`velocity` is **movement speed only** (pixels/frame). It is copied to `IsoUnit.uiSpeed`
(`IsoElement.as:274`) and consumed in `IsoUnit.updateMove` (`IsoUnit.as:770, 874-897`).
It never enters the damage formula. It *does* matter tactically: a slower unit reaches a contested
tile later, and `stun`/`pushInAir` disable movement.

---

## 3. Damage classes

Two parallel damage frameworks exist. The **new** one (`core/generalAttacks/`) is the one used by all
modern content; the **legacy** one (`core/attacks/`) survives for a handful of older delegates.

### 3.1 `core/generalAttacks/AbstractDamage.as` (base)

* `attacker: IsoFightingElement` (`:10`, `:20-25`).
* `numTargets: int = 1` (`:14`) — the **divisor** for splash damage. `SimpleDamage.apply` does
  `target.recibirAtaque(this.damage / numTargets, attacker)` (`:23`).
* `sharedDamage: Boolean` (`:16`) — when set, AoE specials set `numTargets = number of targets`
  so the *total* damage is split between them (e.g. `AreaDamageSpecialAttack.as:95-102`).
* `filterFunction` (`:18`) — optional extra predicate, called as `filterFunction(target, -1)`.
* `canBeApply(target): Boolean` (`:31-34`) — default `true`; overridden per class.
* `apply(target)` (`:27-29`) — default no-op.
* `sigFinished: Signal(IsoUnit)` (`:12`) — fired when the damage lifecycle ends; used by
  `SequencedDamage` to chain.

### 3.2 `core/generalAttacks/damages/*` — the ten damage classes

| Class | File:line | Constructor | Effect | Lifetime |
| --- | --- | --- | --- | --- |
| **`SimpleDamage`** | `damages/SimpleDamage.as:7-36` | `(attacker, damage:int)` | `target.recibirAtaque(damage / numTargets, attacker)` | instant |
| **`BleedingDamage`** | `damages/BleedingDamage.as:10-60` | `(attacker, damage:int, time:int, color:int = -1)` | `target.receiveDamageOverTime(attacker, damage/numTargets/(time/1000), time/1000)` — damage per **second**, and a colour pulse tween | `time` **milliseconds** (e.g. `new BleedingDamage(self, 600, 2500)` ⇒ 2.5 s, 240 dmg/s) |
| **`DelayedDamage`** | `damages/DelayedDamage.as:9-50` | `(attacker, inner:AbstractDamage, delay:uint)` | wraps another damage; fires it after `delay` ms; if the target dies first, dispatches `sigFinished` without damage | `delay` ms |
| **`DizzyDamage`** | `damages/DizzyDamage.as:10-143` | `(attacker, damage:int, duration:int = 6, numTicks:int = 5, colors:Array = null, numColorChanges:int = 1)` | `petrify(duration*1000, color, 0.5, 1)` — the unit is **Incapacitated** (cannot move/act) and colour-cycled; `damagePerTick = damage / numTicks` applied every `duration*1000/numTicks` ms | `duration` **seconds** (default 6 s); ticks = `numTicks` (default 5) |
| **`IncinerateDamage`** | `damages/IncinerateDamage.as:8-51` | `(attacker, damagePerTick:Number, ticks:int, ticksInterval:int, unitCT, flameCT)` | `target.incinerate(attacker, damagePerTick/numTargets, ticks, ticksInterval, ...)`; sets `isBurning`; blocked if `!target.canBeIncinerated` | `ticks × ticksInterval` ms (e.g. `incinerate(self, 5, 5, 1000)` = 5 s, 5 dmg/s) |
| **`PushInAirDamage`** | `damages/PushInAirDamage.as:8-43` | `(attacker, damage:int, tiles:int)` | damage **then** `target.pushInAir(attackerTile, tiles)` — the target is knocked `tiles` tiles away and **Incapacitated** for the flight; blocked if `!target.canBePushedInAir` | instant damage + ~1 s knock-back animation (`IsoUnit.pushInAir`, `IsoUnit.as:1828-1919`); bosses immune (`PropertyManager.BOSS`) |
| **`SequencedDamage`** | `damages/SequencedDamage.as:8-68` | `(attacker)` + `.addDamage(AbstractDamage)` | chains damages: each sub-damage's `sigFinished` advances to the next; `numTargets` is propagated to each sub-damage | until the chain completes |
| **`DirectKillDamage`** | `damages/DirectKillDamage.as:7-60` | `(attacker, maxLife:Number = -1)` | `target.Incapacitated = true; target.kill(attacker)` — instant kill. If `maxLife != -1` it only applies when `target.iHealth <= maxLife` | instant |
| **`BleedingDamage`** (see above) | — | — | — | — |
| **`SimpleDamage`** (see above) | — | — | — | — |
| *(`BleedingDamage`/`DelayedDamage`/`DizzyDamage`/`IncinerateDamage`/`PushInAirDamage`/`SequencedDamage`/`DirectKillDamage`/`SimpleDamage` = 8 in `generalAttacks/damages/`)* | | | | |
| **`DamageOverTime`** (legacy) | `core/attacks/damages/DamageOverTime.as:6-28` | `(attacker, totalDamage:int, numTicks:int, tickInterval:int = 1000)` | `target.receiveDamageOverTime(attacker, totalDamage/numTicks, numTicks, tickInterval)` | `numTicks × tickInterval` ms (default 1 s) |
| **`DirectDamage`** (legacy) | `core/attacks/damages/DirectDamage.as:6-25` | `(attacker, damage:int, displayParticles:Boolean = true)` | `target.recibirAtaque(damage, attacker, displayParticles)` | instant |

**Supporting "status" mechanics on `IsoUnit`:**

* `stun(element, frames = 4, stunMs = -1)` — `IsoUnit.as:2130-2203`: sets `Incapacitated = true`,
  plays a fall animation; only if `building.population < param2` and not `BOSS`; auto-unincapacitates
  after `stunMs`.
* `petrify(ms, color, grey, alpha)` — `IsoUnit.as:2205-2237`: `Incapacitated = true` + colour
  transform for `ms`; re-enables movement when the timer fires.
* `incinerate(attacker, dmg, ticks, interval, ...)` — `IsoUnit.as:2239-2294`: `Timer(interval, ticks)`;
  each tick `recibirAtaque(fireDamage, null)` (**attacker = null**, so burning damage gets **no
  `best_against` bonus** and generates **no XP**); `isBurning` flag blocks re-ignition.
* `poison(attacker, dmg, ticks, infects, ...)` — `IsoUnit.as:2310-2349`: `Timer(3000, ticks)` ⇒ a tick
  every **3 s**; re-poisoning is blocked while `isPoisoned`.
* `receiveDamageOverTime(attacker, dmgPerTick, numTicks, interval = 1000)` —
  `IsoFightingElement.as:1012-1038`: a single `Timer`; a new DOT is **ignored** while one is running.
* `receiveLifeOverTime(attacker, healPerTick, numTicks, interval = 1000)` — `IsoFightingElement.as:1040-1066`.
* `activateShield(ms, multiplier)` — `IsoFightingElement.as:1392-1411`: multiplies *incoming* damage.

---

## 4. Special attacks

### 4.1 Trigger machinery

`AbstractUnitHeroDelegate` (`scripts/core/isoengine/delegates/AbstractUnitHeroDelegate.as`):

* Hero delegates register 4 (index 0..3) `SpecialUnitAttack` objects via
  `addSpecialUnitAttack(new SpecialUnitAttackCreator(id)…)` (`:45-48`).
* `SpecialUnitAttackCreator` (`scripts/core/generalAttacks/SpecialUnitAttackCreator.as`) is a builder:
  `withNumAttacks`, `withCastTime`, `withCoolDownTime` (default **24 s**, `:14`),
  `withAttackName`, `withImageThumbName`, `withCantMessage`, `withOnAttack`, `withCanAttack`.
* `SpecialUnitAttack` (`scripts/core/SpecialUnitAttack.as:34-133`) holds
  `iNumAttacks` (−1 = unlimited), `iCastTime` (seconds), `iCoolDown` (seconds), `onAttack`,
  `canAttack` (defaults to `fCheckAlwaysCan` → `true`).
* `doAttack(id)` (`AbstractUnitHeroDelegate.as:70-98`): only from `SU_STATE_IDLE`; checks
  `canAttack()`; decrements `numAttacks` if > 0; state → `SU_STATE_CASTING` for `castTime` seconds
  (ticked by a 1 s timer, `:141-172`), then `onAttack()` fires, then `SU_STATE_COOLDOWN` for
  `coolDown` seconds, then back to `SU_STATE_IDLE`.
* `SpecialUnitAttackLimit` (`scripts/core/SpecialUnitAttackLimit.as`): charged by damage dealt —
  `unit.damageDone.add(damageDone)` (`:31`), `currentCharge += damage` (`:43`), usable when
  `currentCharge >= MAX_LIMIT_CHARGE (1000)` (`:11, :47-50`); `cast()` resets the charge (`:57-61`).
* `SpecialUnitAttackSpawn` (`scripts/core/SpecialUnitAttackSpawn.as`): additionally disabled when the
  spawned unit id is excluded by the current quest (`:26-33`).
* **The player presses a button in the unit portrait** — `AbstractUnitHeroDelegate.checkTargetInRange`
  (`:210-236`) re-acquires a target within `iAttackRange` before casting.

> ⚠️ **Everything about a special attack is client-side.** The condition check, the damage, the
> cooldown, and the charge all run in the client. The server never sees them.

### 4.2 Attack conditions — `scripts/core/generalAttacks/attackConditions/`

| Class | File:line | Constructor | `evaluate()` | Error message |
| --- | --- | --- | --- | --- |
| `EnemyInRadius` | `EnemyInRadius.as:7-28` | `(unit, range:int, maxLife:int = -1)` | `unit.getCloseEnemmiesInRadius(range, null, maxLife).length > 0` | "No targets in range" |
| `EnemyInFront` | `EnemyInFront.as:10-32` | `(unit, range:int, maxLife:int = -1)` | same, but the search centre is `tile + directionVector(currentDirection) × range` | "No targets in front of you" |
| `LifeCondition` | `LifeCondition.as:9-38` | `(unit, life:int, range:int)` | exists an enemy unit in `range` with `maxLife < life` | "No targets available" |
| `DestinationInFront` | `DestinationInFront.as:9-27` | `(unit, range:int)` | `AbstractUnitDelegate.getDirectionalTile(iAttackRange × range) != null` (a free tile to charge/jump into) | "No place to jump" |
| `DeployMineCondition` | `DeployMineCondition.as:8-25` | `(unit, attack:DeployMineSpecialAttack)` | `attack.currentMinesLenght < attack.maxNumMines` | "#0# Mines Max" |
| `SpawnDroneCondition` | `SpawnDroneCondition.as:8-25` | `(unit, attack:SpawnDroneSpecialAttack)` | `attack.currentDronesLenght < attack.maxDrones` | "#0# Drone Max" |

### 4.3 The 15 special-attack classes — `scripts/core/generalAttacks/specials/`

| Class | File:line | Effect | Units using it (examples) |
| --- | --- | --- | --- |
| `RegularShootSpecialAttack` | `RegularShootSpecialAttack.as:12-122` | Fires one projectile per muzzle point at given animation frames; on impact applies the wrapped damage, else `recibirAtaque(uiAttack / frames / points)`. Can leave the unit `Incapacitated`. | the *normal* attack of most hero units — `BlueAnvilDelegate.as:69`, `IgnitionDelegate.as:66`, `BonecrushaDelegate.as:64`, `CrimsonCenturionDelegate.as:75`, `AgamemnonFortressDelegate.as:75`, `BushwackerDelegate.as:70` |
| `AreaDamageSpecialAttack` | `AreaDamageSpecialAttack.as:13-143` | AoE around the unit (or around a projectile point, if `withUseProjectilePointAsReferencePoint(true)`); `numUnits` cap; `SimpleDamage` auto-shares damage across all hit units; can incapacitate until the animation ends. | `BonecrushaDelegate.as:65-67`, `AtomicBonecrushaDelegate.as:65-67`, `BushwackerDelegate.as:75`, `BrawlerDelegate.as:65-69`, `ChemicalGunnerDelegate.as:70-72`, `IgnitionDelegate.as:72` |
| `MeleeSpecialAttack` | `MeleeSpecialAttack.as:9-53` | Applies the wrapped damage to the current target at the animation frame; fallback `recibirAtaque(uiAttack / frames)`. | (used by melee-style heroes) |
| `ChargeAttack` | `ChargeAttack.as:17-116` | Moves the unit `iAttackRange × rangeModifier` tiles toward the target (1 s tween) and applies AoE damage every **100 ms** along the way (`_numUnits` cap). | `BlueAnvilDelegate.as:73` |
| `GoEnemyAndComeBackSpecialAttack` | `GoEnemyAndComeBackSpecialAttack.as:16-143` | Runs to the nearest enemy (0.25 s tween), attacks, returns home (0.25 s). | `BlueAnvilDelegate.as:71` |
| `ApproachEnemySpecialAttack` | `ApproachEnemySpecialAttack.as:13-96` | Teleports the unit next to the nearest enemy (updating `buildingReference.tx/ty`!) and then AoE-damages. | `IgnitionDelegate.as:68` |
| `SpawnDroneSpecialAttack` | `SpawnDroneSpecialAttack.as:15-136` | Summons up to `maxMinions` drones (min `minMinions`, optional random extra); spawn tile = ±4 tiles random, clamped to the map; `withDamageOwnerOnDead(percent)` deals `percent × minion.maxLife` to the owner when a minion dies. | `DroneMasterDelegate.as:56-58`, `DroneMaster2Delegate.as:56-59`, `BlueAnvilDelegate.as:76`, `IgnitionDelegate.as:73` |
| `DeployMineSpecialAttack` | `DeployMineSpecialAttack.as:15-82` | Places a **neutral** mine unit next to the owner, up to `maxNumMines`. | `BushwackerDelegate.as:76` |
| `EatSpecialAttack` | `EatSpecialAttack.as:12-127` | Grabs up to `_grabPoints.length` enemy units whose `maxLife < _maxLife`, swallows them (damage = `_maxLife`). | large-eater units |
| `BeamAndEatSpecialAttack` | `BeamAndEatSpecialAttack.as:17-177` | Fires a beam at the nearest enemy in range, then drags the target to the attacker and consumes it (damage applied on release). Optional `withEatUnit(true)`, `withAnimationEndFrame`. | `CycloneMechDelegate.as:72` |
| `ShootProjectilesAttack` | `ShootProjectilesAttack.as:16-209` | Bursts of projectiles (`numProjectilesPerBurst`, `numShootingPoints`, `hitEnemyEveryN`); on landing, AoE damage in `range` around the impact point. Can fire blind (`getDirectionalTargetPoint` uses `Math.random()`). | `AgamemnonFortressDelegate.as:77,81`, `BismarkMechDelegate.as:66-68`, `BushwackerDelegate.as:72-73`, `CrimsonCenturionDelegate.as:77`, `IgnitionDelegate.as:70` |
| `ShootBombSpecialAttack` | `ShootBombSpecialAttack.as:18-205` | Lobs bombs at enemies; on landing, AoE damage of `bombRadius` around the impact, capped at `maxUnitsAfected`; supports simultaneous multi-muzzle shots and random target ordering. | `CycloneMechDelegate.as:65` |
| `MultiLaserSpecialAttack` | `MultiLaserSpecialAttack.as:12-114` | Beams up to `_unitsPerShot` enemies in `_attackRange`, each with a beam projectile. | `CrimsonCenturionDelegate.as:79`, `ChemicalGunnerDelegate.as:68`, `CentaurDelegate.as:69` |
| `VortexSpecialAttack` | `VortexSpecialAttack.as:12-107` | First frame: every 4th enemy with `iHealth <= _enemyMaxHealthToBeAbsorbed` is **deleted** (up to `_numKills`); all others take `uiAttack × 0.3` as a 10-tick DOT. Second frame: full damage to all in range. | `BlackHoleDelegate.as:74` |
| `WhirlwindSpecialAttack` | `WhirlwindSpecialAttack.as:12-79` | Ticks `_ticks` times over `_duration` seconds, damaging everything in `_range` each tick. | whirlwind units |

**Legacy system** — `scripts/core/attacks/special_attacks/`:

| Class | File:line | Effect |
| --- | --- | --- |
| `PushInArea` | `attacks/special_attacks/PushInArea.as:11-66` | Pushes up to `maxUnitsAffected` enemies within `maxRange` by `distance` tiles with `force`, and applies `DirectDamage(attacker, attacker.uiAttack)`. |
| `CircularShooting` | `attacks/special_attacks/CircularShooting.as:14-231` | Splits the 360° circle into 8 sectors and fires at each in turn; supports multiple loops. |
| `ShootProjectile` | `attacks/special_attacks/ShootProjectile.as:8-43` | Single projectile with an optional `damageModifier` on `uiAttack`. |
| `ShootProjectilesAttack` | `attacks/special_attacks/ShootProjectilesAttack.as` | Legacy multi-projectile. |
| `SpawnMinion` | `attacks/special_attacks/SpawnMinion.as:14-77` | Legacy minion spawn (no max-cap enforcement at spawn time). |

**Unit filters** — `scripts/core/generalAttacks/UnitFilters.as:15-58`:
`filterByMaxHealth`, `filterByMinHealth`, `filterByRangeHealth` — all require the target to be a
non-peasant, non-dead, container-less unit with `uiAttack > 0`. (Note: `filterByRangeHealth` at `:51`
compares `iHealth > param2[0] && iHealth < param2[0]` — an obvious bug, the upper bound is never used.)

---

## 5. Unit XP and level progression

### 5.1 Data

`main.json` `globals.UNIT_XP_LEVELS_MULTIPLIERS_10` (`main.json:47873-47934`), 10 entries
(level 0 … level 9). Each entry is `[xpMultiplier, extraAttackFlat, extraLifePercent, priceDivisor]`:

| Level | XP threshold (× base `life`) | Cumulative XP (× `life`) | `extraAttack` added at this level | `extraLife` % added at this level | Cash price to buy the level = `ceil(life / divisor)` |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 % | — |
| 1 | 5 | 5 | +2 | +20 % | `ceil(life/50)` |
| 2 | 10 | 10 | +2 | +20 % | `ceil(life/25)` |
| 3 | 20 | 20 | +3 | +20 % | `ceil(life/12)` |
| 4 | 40 | 40 | +3 | +20 % | `ceil(life/6)` |
| 5 | 65 | 65 | +4 | +20 % | `ceil(life/4)` |
| 6 | 95 | 95 | +4 | +25 % | `ceil(life/3)` |
| 7 | 125 | 125 | +4 | +25 % | `ceil(life/2.5)` |
| 8 | 160 | 160 | +4 | +25 % | `ceil(life/2)` |
| 9 | 200 | 200 | +4 | +25 % | `ceil(life/1.5)` |

`maxLevel = length − 1 = 9` (`scripts/core/UnitXPLevelInfo.as:52-55`).

### 5.2 Threshold and bonus computation

`UnitXPLevelInfo.getRequiredXpForLevel(life, level)` (`:42-50`):
`return UNIT_XP_LEVELS_MULTIPLIERS_10[level][0] * life;`  → the threshold is a **multiple of the
unit's own base HP**.

`_updateCurrentLevel()` (`:57-83`) walks levels 1…9:

```
level = 0; extraAttack = 0; extraLife = 0
for lv in 1..9:
    if (currentXP <= getRequiredXpForLevel(life, lv)) break;   // NOTE: strict '>' to advance
    level      += 1
    extraAttack += M[lv][1]                                    // flat attack
    extraLife  += life * (M[lv][2] / 100)                      // % of base life
```

⇒ **At level 9 the unit has `+30` attack and `+200 %` life (3× base HP).**
`extraAttack` is applied as a **flat** bonus in the damage pipeline (`IsoFightingElement.as:438-441`);
`extraLife` is added to `maxLife` (`IsoFightingElement.as:1357-1365`).

Accessors for the UI: `getExtraLifeForLevel` (`:144-155`), `getExtraLifePercentageForLevel`
(`:157-169`), `getExtraAttackForLevel` (`:171-183`).

### 5.3 How XP is earned

`IsoFightingElement.recibirAtaque` (`:477-480`):

```
if (attacker has unitXPLevel && target.building.type == Constants.TYPE_UNIT)
    attacker.buildingReference.unitXPLevel.onDamageMade(arAttack[0]);
```

`arAttack[0]` is the **post-defense, post-crit damage actually subtracted from HP** (§2.4 step 9/10).
⇒ **XP = damage dealt to units only** (not to buildings), and it is the *effective* damage, not the raw
attack.

`UnitXPLevelInfo.onDamageMade(xp)` (`:118-137`):

```
if (buildingReference.playerID != PLAYER_SELF) return;   // only your own units
if (!buildingReference.mc.inServer)        return;       // only units on your own (server) map
if (buildingReference.mc.bDead)            return;       // dead units stop earning XP
currentXP += xp;
_updateCurrentLevel();
if (level changed) {
    levelUpSignal.dispatch(this, false);
    mc.iHealth += getExtraLifeForLevel(currentLevel);     // instant heal on level-up
}
changeSignal.dispatch(this);
Base.Commands.addUnitXPToSend(buildingReference, xp);     // queue for the server
```

* `unitXPLevel` objects are created in `BuildingReference` for every **non-neutral unit with
  `attack > 0`**, except enemy units in normal game mode and in quest mode
  (`scripts/core/BuildingReference.as:89-95`).
* XP is **accumulated client-side and batched** to the server as `add_xp_unit` commands
  (`scripts/managers/CommandManager.as:285-323`, `scripts/commands/CmdAddUnitXP.as`).
* If the unit dies, its pending XP is dropped (`IsoFightingElement.as:720-723` →
  `removeXPToSendFromDeadUnit`).

### 5.4 Paying for a level

`levelUpForCash()` (`:94-116`):

```
price   = getPriceForLevelUp(currentLevel + 1)                // ceil(life / M[level+1][3])
required= getRequiredXpForLevel(life, currentLevel + 1) + 1   // note the +1
delta   = required - currentXP
queue CmdAddUnitXP(iIsoID, delta, price, currentLevel + 1)
currentXP = required
mc.iHealth = mc.maxLife                                      // full heal
levelUpSignal.dispatch(this, true)                           // paid = true
```

The client immediately sets `currentXP` and heals to full; the server is asked to grant the same XP.
On level-up the GUI shows the cash price (`IsoFightingElement.onUnitLevelUp`, `:180-206`).

---

## 6. Client-side vs server-side combat — the trust boundary

### 6.1 What the client does (100 % local)

Everything in §2, §3, §4 and §5 happens in the Flash client:

* Movement, pathfinding, target acquisition, range checks.
* All damage computation (crit, variance, defense, `best_against`, siege, shields, stats modifiers).
* All special attacks, their conditions, cooldowns and charges.
* Unit XP accrual and level bonuses (the client even pre-computes the level and the extra life).
* Death → `CmdKill` / `CmdKillIid` / `CmdSell` messages (`IsoFightingElement.die`, `:731-784`).

The only client→server primitives that touch combat outcomes are:

| Command | File | Payload |
| --- | --- | --- |
| `kill` | `scripts/commands/CmdKill.as` | element id + `{g: gold, x: xp}` tokens dropped |
| `kill_iid` | `scripts/commands/CmdKillIid.as` | same, for elements not on the server map |
| `sell` | `scripts/commands/CmdSell.as` | element id + reason (e.g. `SELL_REASON_KILL`) |
| `add_xp_unit` | `scripts/commands/CmdAddUnitXP.as` | `(iIsoID, xpDelta, cashPaid, targetLevel)` |
| `end_attack` | `scripts/commands/CmdEndAttack.as` | full battle report JSON (see below) |
| `end_quest` | `scripts/commands/CmdEndQuest.as` | quest result JSON |

### 6.2 `end_attack` — the entire battle report

Built in `scripts/battle/Assault.as:452-494` (`sendAssaultResults`):

```json
{
  "attacker": { "name", "level", "user_id", "world_id", "map", "race" },
  "victim":   { …opponent descriptor… },
  "resources":            { "g": goldWon, "x": xpWon },
  "resources_victim":     { "g": goldTakenFromVictim },
  "attacker_units": [ [itemId, initCount, killedCount, recoveredCount], … ],
  "victim_units":   [ [itemId, initCount, killedCount, recoveredCount], … ],
  "win": 0|1,
  "duration": seconds,
  "voluntary_end": 0|1,
  "townhall_gold": n,
  "honor": n,
  "different_island": 0|1
}
```

`CmdEndAttack` (`scripts/commands/CmdEndAttack.as:11-23`) also **optimistically mutates the local
player state** (`setResource` for gold/xp) and adds the premium bonus (50 %,
`Config.PREMIUM_ACCOUNT_BONUS_PERCENTAGE`, `Config.as:246`).

### 6.3 What the reference server does with it

`command.py` `end_attack` (`<upstream-repo>\command.py:808-884`):

* Parses the JSON, extracts the fields, **and nothing else**.
* The **only** mutation of game state is the loss of units:

```python
866:  for unit in attacker_units:
868:      lost = max(0, unit[2] - unit[3])   # killed − recovered
870:      map_lose_item(map, privateState, unit[0], lost)
```

* It prints "Won battle against X" / "Lost battle against X". The TODOs at `:822-824` state the
  intent explicitly: *"Parse more data in the future / Affect victim player save / Attack logs"*.

`command.py` `end_quest` (`:752-806`) is identical in shape: it parses `win`, `duration`, `units`,
`map`, `difficulty`, `voluntary_end`, `quest_id`, and applies **only** `lost = max(0, unit[2]-unit[3])`
unit losses.

**⇒ The reference server is a *recorder*, not an arbiter. It believes the client about who died.**

### 6.4 Trust boundary a faithful clone must define

A faithful *re-implementation of the rules* can be authoritative-server, but the original rules were
written assuming a trusting client. A clone should therefore validate at minimum:

| Must validate server-side | Why |
| --- | --- |
| That the attacker actually owns the units it claims sent, and that the counts match the garrison/`sent_to_battle` list | otherwise a client can claim 0 losses |
| That `unit[2] - unit[3]` (killed − recovered) is ≤ the number of units actually deployed, and that the *recovered* count is plausible | `recoverPlayerUnits` (`Assault.as:529-582`) only moves *killed* units back into the "recovered" bucket, so `killed ≥ recovered` always; a client can simply report `recovered == killed` to lose nothing |
| That the number of losses cannot exceed the deployed army | the current server does not check this at all |
| The resource loot (`resources.g`, `resources.x`, `townhall_gold`) against the cap `Config.MAX_GOLD_FROM_ASSAULT = 200` (`Config.as:188`) and the victim town hall's actual gold | the reference server does not check |
| Unit XP (`add_xp_unit`) against a server-side XP ledger per unit, and the level derived from the same table | the client currently decides its own level |
| Cooldowns / charges of hero special attacks | purely client-side in the original |
| Whether the attacker could have reached the target (distance, time, movement speed `velocity`) | the original never checks |

**Recommended split for the clone:** keep the *presentation* (animations, projectiles, floating
damage numbers) client-side and deterministic, but run the *simulation* (damage rolls, target
selection, special attacks, XP) on the server. The cleanest faithful approach is a **seeded,
server-authoritative simulation**: the client receives a combat seed, renders the resulting event
stream, and the server recomputes the same rolls (see §7).

---

## 7. RNG and determinism

### 7.1 The seeded RNG that exists

`scripts/utils/RandomGenerator.as` (note: `scripts/utils/`, **not** `scripts/core/utils/`):

```as
6:   public var seed:uint;                 // default 1
14:  public function nextInt():uint   { return this.gen(); }
19:  public function nextDouble():Number { return this.gen() / 2147483647; }
24:  public function nextIntRange(lo:Number, hi:Number):uint {
26:      lo -= 0.4999; hi += 0.4999;
28:      return Math.round(lo + (hi - lo) * this.nextDouble());
    }
31:  public function nextDoubleRange(lo,hi):Number { return lo + (hi-lo)*this.nextDouble(); }
36:  private function gen():uint { return this.seed = this.seed * 16807 % 2147483647; }
```

* This is the **Park–Miller minimal standard LCG** (`x' = 16807·x mod 2³¹−1`), *not* a
  Mersenne Twister.
* It is used in exactly **one** place: `GameStatic.shuffleArrayWithSeed(array, seed)`
  (`scripts/core/GameStatic.as:486-499`) — a Fisher–Yates shuffle used for cosmetics/collections.
* It is **not** used by combat.

### 7.2 The RNG that combat actually uses

**Combat uses `Math.random()` directly and is therefore non-deterministic and unseeded:**

* Crit roll: `Math.random() * 100 < 10` (`IsoFightingElement.as:230`).
* Damage variance: `Math.random() * 8 - 4` (`IsoFightingElement.as:231`).
* `iDelayAttack` phase: `Math.floor(Math.random() * 5)` (`IsoFightingElement.as:171`).
* Initial facing: `Math.floor(Math.random() * 3)` over `[4,5,8]` (`IsoUnit.as:307`).
* Machinegun stream phase: `frameCounter = Math.random() * everyNFrames`
  (`battle/projectiles/Machinegun.as:55`).
* Projectile start offsets: `Math.random()` (`battle/projectiles/AbstractProjectile.as:141`).
* Special-attack target selection: `Math.random()` (e.g. `ShootProjectilesAttack.as:193-197`,
  `ShootBombSpecialAttack.as:135, 202`, `FlamethrowerDelegate.as:48`).
* Drone spawn offsets: `Math.random() * 8` (`SpawnDroneSpecialAttack.as:98-99`).
* Random knock-back direction: `Math.random() * PI * 2` (`IsoUnit.as:1850`).
* `VortexSpecialAttack` / `AreaDamageSpecialAttack` orderings.

### 7.3 Consequences for a clone

* **Results are not reproducible.** A clone that wants replay/verification/escape-analysis must
  replace `Math.random()` with a seeded stream and record the seed.
* The natural port of the Park–Miller generator above is a drop-in, but note the clone must decide
  *which* random stream feeds *which* mechanic, because the original code interleaves many
  independent `Math.random()` call sites whose ordering is only defined by the original call order.
* **Server validation strategy:**
  1. *Authoritative simulation* — the server owns the RNG and the damage rolls; the client only
     renders. This is the only way to make the result trustworthy.
  2. *Seeded client simulation* — the server issues a per-battle seed, the client replays it, the
     server replays the same seed and compares the final casualty list. Requires a deterministic,
     order-independent simulation (fixed update tick, integer maths) — the original AS3 is *not*
     deterministic in this sense (it is frame-rate driven and uses `Timer`/`ENTER_FRAME`).
  3. *Statistical validation* — sanity-check the reported casualty counts against plausible DPS
     envelopes: `maxDamagePerUnit ≈ Σ_i (attack_i × 30/interval_i) × critExpected(1.05) ×
     bestAgainstMult`, and flag outliers.
* Frame-rate coupling is a determinism hazard in its own right: `attack_interval` is expressed in
  **frames**, and the client runs at 30 fps but `Stats.as` lets you change `stage.frameRate` at
  runtime (`scripts/core/Stats.as:154-172`). A clone should express attack cadence in **seconds**
  (`attack_interval / 30`) and tick on a fixed timestep.
* The `iDelayAttack` phase (0–4 frames) is a deliberate anti-`attack_interval`-synchronisation measure;
  a clone should keep a randomised phase per unit to avoid all units firing on the same frame.

---

## 8. Building stats and the `isoengine` delegate model

### 8.1 The delegate model

```
IsoElement                       (scripts/core/isoengine/IsoElement.as)
 └─ IsoInteractiveElement        (scripts/core/isoengine/IsoInteractiveElement.as)   ← mouse, selection, vUnitsContained
     ├─ IsoFightingElement       (scripts/core/isoengine/IsoFightingElement.as)     ← HP, attack, defense, damage
     │   ├─ IsoUnit              (scripts/core/isoengine/IsoUnit.as)                ← movement, pathfinding, statuses
     │   └─ IsoBuilding          (scripts/core/isoengine/IsoBuilding.as)            ← production, collection, upgrades
```

Every element owns a `delegate` (`Delegate` interface, `scripts/core/isoengine/delegates/Delegate.as`),
resolved by item id:

* `DelegatesManager.getDelegate(id)` returns `new delegates[id][0](delegates[id][1])` — i.e. a
  **new delegate instance per element** (`DelegatesManager.as:1731-1739`).
* `DelegatesManager.registerDelegate(cls, args, ...ids)` (`:1769-1787`) maps **both** the player id
  and the enemy id (`Constants.getId` / `Constants.getEnemyId`) to the same class + args object.
* Fallback `autoAssignDelegate(id)` (`:1751-1767`): `chained` → `OfferBuildingDelegate`;
  `decoration` → `BasicDecorationDelegate`; `trains_ids > 0` → `BaseBarrackDelegate`; else `null`.
* There are **229 unit delegates** in `delegates/units/` and **53 building delegates** in
  `delegates/buildings/`.

`Delegate` interface (`Delegate.as:8-40`): `canGetInside`, `onInit`, `onAttack`, `onControlAnimation`,
`highlight`, `unhighlight`, `click`, `receiveAttack`, `initializeExtendedPortrait`,
`getInfoButtonStore`, `selected`, `deselected`, `onUpdateAnimation`, `onFrame`, `onSetGraphic`.

`UnitDelegate` adds (`UnitDelegate.as:3-27`): `onEnterTile`, `onUpdateMove`, `onDead`, `getUnitSfx`,
`bSpecialUnit`, `projectileDelay`, `arFramesSpecialAttackingInterval/Duration`, `bHeroUnit`,
`rangedMelee`, `meleeDist`.

`BuildingDelegate` adds (`BuildingDelegate.as:3-17`): `collect`, `canBeUsed`, `canBePicked`,
`hasReachedConstructionLimit`, `onEndConstructionStep`.

### 8.2 Building lifecycle in the iso engine

1. **Construction.** `IsoElement.currentBuildingStep` (`IsoElement.as:239-246`); `inConstruction =
   currentBuildingStep >= 0 && (currentBuildingStep < clicks_to_build || inventory_ids != null)`.
   `IsoBuilding.stepConstruct` / `setConstructionStepGraphic` / `endConstructionStep`
   (`IsoBuilding.as:889-992`) drive the build animation. `clicks_to_build == 0` ⇒ instant.
2. **Activation.** If `inventory_ids != null` the building is built but must be *activated* by a click
   (`needActivation = true`, `IsoBuilding.as:1012`; `CmdActivateItemClick` at `:983`). If
   `clicks_to_build > 0` the client sends `CmdActivateItemClick` on each click (`:981-984`).
3. **Production (training).** `IsoBuilding.trainUnit` (`:243-268`): `uiTrainingTime =
   training_time × 1000` ms; `iIDUnitTrained = trains_ids`. `UnitTrainingStart` (`:270-…`) charges
   `cost_unit_cash` for an instant train and checks `Base.Player.iPopulationCurrent <
   iPopulationMaxCurrent`. `spawnUnit` (`:395-…`) creates the unit. The queue is
   `pushTrainingQueue` / `popTrainingQueue` (`:224-241`) with `maxUnitsInQueue = 5` (`:121`).
4. **Collection.** `IsoBuilding.canCollect` (`:1044-1070`): collectable iff
   `collected_at >= activation` (or a "hurry up" icon is pending) **and** the resource silo has room
   (or the building `isActivator`). `startCollection` (`:1072-1106`) → `collect(param1)` (`:1108-1202`):
   * `amount = floor(building.collect) × Base.Iso.getResourceMultiplier(this)` (`:1181`).
   * If `iUnitsContainedWhenHarvested > 1` (peasants working inside):
     `amount = floor(floor(amount + (n−1) × amount × Config.MULTIPLIER_PEASANTS) × mult)` where
     `MULTIPLIER_PEASANTS = 0.2` (`Config.as:132`) (`:1186-1189`).
   * `multiCollectable` buildings multiply by `globals.COLLECT_MULTIPLIER[cp−1]`
     (`main.json:47444-47449` = `[0.25, 1, 2, 3]`) (`:1150-1154`).
   * `collected_at` is reset to 0 and `activation` restarts the timer.
   * `CmdCollect` is sent to the server (`:1155-1158, 1194-1197`).
5. **Capacity / garrison.** `unit_capacity` ⇒ `iUnitCapacity` (`IsoInteractiveElement.as:85`).
   `AbstractDelegate.canGetInside` (`:107-110`) / `AbstractBuildingDelegate.canGetInside`
   (`:121-128`): the unit must be of the same player, have no container itself, the building must have
   room, and `building.volume <= building.max_elem_vol`. `PushUnit` / `PopUnit` / `popAll`
   (`IsoInteractiveElement.as:1119-1280`) move units in and out.
6. **Population.** `population` ⇒ `uiPopulationGranted` (`IsoBuilding.as:119`) / `iPopulationCount`
   (`IsoUnit.as:304`); `grants_population` / `raisePopulation_cap` properties trigger
   `Base.Player.updatePopulation()` (`IsoBuilding.as:986-989`).
7. **Upgrades.** `IsoBuilding.upgrade` (`:537-697`): looks up `upgrades_to`; requires
   `playerLevel >= next.min_level`; charges `next.costs` and refunds `floor(current.costs / 20)`
   (`Config.DIVISOR_SELL = 20`, `Config.as:162`); verifies the footprint fits and is walkable;
   pops garrisoned units and re-places them next to the new building; queues `CmdBuy` (or
   `CmdPremiumUpgrade`). `getUpgradeBuilding` (`:704-…`) resolves the target item.
8. **Repair.** `IsoBuilding.updateRepair(amount)` (`:217-222`) heals up to `maxLife`; `FiremanDelegate`
   repairs on the attack tick (`IsoUnit.as:533-545`).
9. **Burning.** `updateFlamesGraphics` (`:171-215`): below 34 % HP the building is on fire
   (`FLAME_MAX`); `setInFlames(true)` (`:152-169`) calls `popAll()` — **the garrison is ejected when
   the building burns**.
10. **Combat behaviour.** `TowerDelegate` rotates to face the target and picks the weapon set for that
    direction; `BasicFortressDelegate` fires one weapon per attack point; `BunkerDelegate` limits the
    number of shooters to the number of garrisoned units; `ElectricTowerDelegate` applies a beam
    colour effect; `MultiShotTowerDelegate` fires `shots` projectiles every `interval` frames.

### 8.3 The 43 combat-capable buildings (from `main.json`)

| id | name | attack | def | life | interval | range | cap | best_against |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 22 | Turret I | 5 | 1 | 300 | 35 | 8 | 0 | ft_flying |
| 39 | Turret IV | 14 | 1 | 900 | 35 | 11 | 0 | ft_flying |
| 45 | Dual-Rocket Turret | 20 | 1 | 1600 | 35 | 12 | 0 | ft_flying |
| 46 | Cannon Turret | 18 | 1 | 1500 | 35 | 12 | 0 | ft_flying |
| 49 | Turret III | 12 | 1 | 700 | 35 | 10 | 0 | ft_flying |
| 50 | Bunker I | 8 | 1 | 600 | 35 | 7 | 1 | ft_ground |
| 51 | Bunker II | 10 | 1 | 1300 | 35 | 8 | 4 | ft_ground |
| 52 | Bunker III | 14 | 1 | 800 | 35 | 9 | 6 | ft_ground |
| 53 | Mega Bunker | 18 | 1 | 2000 | 35 | 10 | 10 | ft_ground |
| 57 | Turret II | 8 | 1 | 500 | 35 | 9 | 0 | ft_flying |
| 80 | Fortress I | 18 | 1 | 4000 | 15 | 10 | 0 | ft_armored |
| 81 | Fortress II | 22 | 1 | 8000 | 15 | 11 | 0 | ft_armored |
| 82 | Rocket Fortress | 26 | 1 | 8000 | 15 | 12 | 0 | ft_armored |
| 83 | Fortress III | 26 | 1 | 10000 | 15 | 12 | 0 | ft_armored |
| 84 | Special Fortress | 22 | 1 | 5000 | 15 | 11 | 0 | ft_armored |
| 85 | Mega Fortress | 30 | 1 | 12000 | 15 | 13 | 0 | ft_armored |
| 87 | Turret VI | 18 | 1 | 1200 | 35 | 13 | 0 | ft_flying |
| 88 | Turret V | 16 | 1 | 1100 | 35 | 12 | 0 | ft_flying |
| 118 | Mind Control Laboratory | 26 | 1 | 5000 | 42 | 15 | 0 | – |
| 164 | Laser Turret | 21 | 1 | 1700 | 35 | 12 | 0 | ft_flying |
| 165 | Tesla Turret | 20 | 1 | 1550 | 30 | 10 | 0 | ft_flying |
| 185/189 | Ork Turret II / I | 23 / 22 | 1 | 1750 / 1650 | 35 | 12 / 11 | 0 | ft_flying |
| 201 | Orc Bunker | 8 | 1 | 600 | 35 | 7 | 1 | ft_ground |
| 205 | Orc Fortress | 22 | 1 | 5000 | 15 | 11 | 0 | ft_armored |
| 207/208 | Enemy Ork Turret I / II | 5 / 23 | 1 | 300 / 800 | 35 | 8 / 12 | 0 | ft_flying |
| 220/221 | Viking Turret I / II | 22 / 23 | 1 | 1600 / 1750 | 35 | 11 / 12 | 0 | ft_flying |
| 226/227 | Alien Turret I / II | 21 / 20 | 1 | 300 / 600 | 35 | 11 / 12 | 0 | ft_flying |
| 229/230 | Spider Turret I / II | 21 / 20 | 1 | 300 / 600 | 35 | 11 / 12 | 0 | ft_flying |
| 245 | Nebular Turret | 23 | 1 | 1600 | 35 | 11 | 0 | ft_flying |
| 272 | Space Elf Turret | 25 | 1 | 1700 | 35 | 11 | 0 | ft_flying |
| 294 | Andromeda Turret | 26 | 1 | 1750 | 35 | 11 | 0 | ft_flying |
| 901-905, 930, 931 | Oil / Tree decorations | 2 | 1 | 1-50 | 35 | 1-6 | 2-6 | – |

---

## 9. Energy system

**There is no per-unit or per-attack energy in the iso engine.** Energy in this build is a *player-level
building/construction resource*, handled entirely outside the combat code:

* `globals.ENERGY_MAX_REGULAR_VALUE = 30` (`main.json:47423`).
* `globals.ENERGY_INCREASE_ENERGY_INTERVAL = 300000` ms (**5 minutes**) (`main.json:47422`).
* `globals.ENERGY_CONSTRUCTION_COST = 1` (`main.json:47424`).
* `globals.ENERGY_COSTS = { "10": 10, "20": 20, "30": 30, "40": 40 }` (`main.json:47425-47430`) — the
  energy price of an instant construction at player level 10/20/30/40.
* `globals.ENERGY_ASSIST_QTY = 1` (`main.json:47450`).
* Player state: `PlayerStatus.iEnergy` (`scripts/managers/PlayerStatus.as:751-769`), stored in
  `privateState.energy` (`:312-315`).
* Regeneration: `ResourceManager` sets a `Timer` of `ENERGY_INCREASE_ENERGY_INTERVAL` that fires
  `onUpdateEnergy` (`scripts/managers/ResourceManager.as:44-70, 308-315`); the first tick is scheduled
  from `PlayerStatus.secsRemainingEnergyIncrease` so the timer survives a page reload.
* Server mutation: `CmdModifyEnergy(delta)` (`scripts/commands/CmdModifyEnergy.as`) → resource key
  `"e"` (`Constants.COST_ENERGY`, `Constants.as:1752`).
* `Config.COST_HURRY_UP = 2` (`main.json:47451`) and `globals.COST_HURRY_UP = 2` are separate
  construction speed-ups.

⇒ **Energy is irrelevant to combat maths.** It is a *build-timer skip* currency. A clone must not
confuse it with a per-attack energy cost (the `items[].syringes` field is the *resurrection* cost in
syringe items, not energy).

---

## 10. Clone-critical rules checklist

The smallest set of rules a faithful re-implementation must get right, in priority order.

### A. Damage formula (must be exact)

1. `attack` (config) → base damage; multiplied by `best_against_mult` **iff the target's item carries
   the `best_against` property** (`ft_ground` / `ft_armored` / `ft_flying` / `ft_building`).
2. Add the unit's XP flat bonus (`extraAttack`).
3. Roll crit: 10 % chance ⇒ `dmg = (base + |variance|) × 1.5`.
4. Variance: `variance = random(−4, +4)`, added to the base when not criting.
5. Subtract the target's flat `defense` (1 in all shipped content).
6. `round()`, then clamp to a **minimum of 1**.
7. Apply the attacker's `StatsModifier.attackModifier` and the `best_against` multiplier **before**
   the crit roll? — **NO**: order in the code is `best_against → statsModifiers → global multipliers
   → +extraAttack → siege → tutorial → crit/variance → −defense → min 1`. Keep this order.

### B. Attack cadence & range

8. `attack_interval` is in **frames at 30 fps** ⇒ `seconds = attack_interval / 30`.
9. Each unit has a random **phase offset of 0–4 frames** so units do not fire in lockstep.
    **Buildings have no phase offset and no `%5` gate** — every tower fires on the same global frame
    (`frame % attack_interval == 0`, `IsoBuilding.as:486`).
10. Effective range for **units** = `attack_range + max(0, targetWidth − 2·attack_range)`; distance is
    measured between **building centres**. Effective range for **buildings** = exactly
    `attack_range` (centre-to-centre, no width adjustment, `IsoBuilding.as:490`).
11. A single attack cycle deals **one** `attack` instance for machinegun/multi-shot units (follow-up
    bullets are cosmetic). Multi-shot *specials* are the exception (they explicitly divide the damage
    by the number of shots/frames).

### C. Target selection

12. Search radius = `max(10, attack_range)`.
13. Priority score: `1000 − distance`, `+150` for units, `+100` for the town hall, `+75` for resource
    buildings (`collect > 0`), `+50` for other attackers; anything else scores `-1` and is untargetable.
    Buildings with `attack == 0` also get `+10` distance penalty (`bucleNearestUnits`, `IsoEngine.as:1710-1713`).
    The duplicate `−AGGRO_RANGE` in `getNearestTarget` (`:1664-1667`) writes to a dead local
    (`_loc14_`) and has **no effect**.
14. Units inside a building (`eContainer != null`) cannot be targeted; stealth units require the
    attacker's `seeStealthUnits`; blinded attackers cannot target at all.

### D. Damage-over-time / status effects

15. Minimum damage 1 applies to every tick of every DOT as well.
16. `incinerate` and `poison` damage passes `attacker = null` ⇒ **no `best_against` bonus and no XP**.
17. `stun`/`petrify`/`pushInAir` set `Incapacitated`, which blocks movement **and** the normal attack
    tick (`IsoUnit.as:529`) but not `onFrame`-driven special attacks.
18. Only one damage-over-time timer may be active per unit at a time.

### E. Counters

19. `best_against` is a **property name** on the target, and the "counter units"
    (Mortar Thrower 10×, Antiaircraft 20×, B52 5×, Demolition Tank 15×) are the intended rock-paper-
    scissors answer to `ft_building` / `ft_flying` spam.
20. Siege units (`subcat_functional == 81`) halve their damage and take +25 % — **currently no unit in
    the data uses scf 81**; implement it only if the clone's data set contains siege units.
21. `ft__armored` (double underscore) never matches — use `ft_armored`.

### F. Unit progression

22. XP thresholds are **multiples of the unit's base `life`**: 5, 10, 20, 40, 65, 95, 125, 160, 200
    (levels 1–9).
23. XP is earned from **effective damage dealt to units only**.
24. Level bonuses: `+2, +2, +3, +3, +4, +4, +4, +4, +4` flat attack; `+20 %, +20 %, +20 %, +20 %,
    +20 %, +25 %, +25 %, +25 %, +25 %` of base life.
25. Max level 9 ⇒ `+30` attack, `3×` base HP.
26. Levelling up with cash costs `ceil(life / divisor)` with divisor `50, 25, 12, 6, 4, 3, 2.5, 2, 1.5`
    and grants exactly the missing XP plus 1.

### G. Buildings

27. A building's own `attack` is scaled by `garrisonedUnits / unit_capacity` — an empty bunker deals
    **0** damage.
28. A bunker fires once per garrisoned unit (capped by its attack points).
29. Only `scf ∈ {211 tower, 231 castle, 135 town hall}` buildings ever attack; the Command Center I
    (`id 26`) is excluded.
30. `activation` (seconds) gates collection; `max_collects` caps the number of harvests;
    `multiCollectable` buildings stack `COLLECT_MULTIPLIER` (0.25/1/2/3).
31. Peasants inside a building add `+20 %` of the yield each.
32. A building that drops below 34 % HP ignites and **ejects its garrison**.

### H. Server authority (non-negotiable for a cheat-free clone)

33. The client must not be able to choose its own casualties: the server must own the combat
    simulation, or at minimum recompute it from a server-issued seed and reject mismatches.
34. Validate: deployed-unit counts, `killed − recovered` bounds, gold/XP loot caps
    (`MAX_GOLD_FROM_ASSAULT = 200`), unit XP against a server ledger, and hero special-attack
    cooldowns/charges.
35. Keep the RNG seeded and the simulation on a **fixed timestep**; the original's frame-driven
    `attack_interval` and `Math.random()` are not reproducible as-is.

---

## Appendix A — Item id → constant mapping (spot checks)

`Constants.getId()` is the identity function (`scripts/core/Constants.as:2209-2212`), so
`Constants.ID_*` values *are* the `items[].id` values.

| Constant | id | config name |
| --- | --- | --- |
| `ID_UNIT_SOLDIER_1` | 1007 | Soldier |
| `ID_UNIT_MEDIC` | 1050 | Medic |
| `ID_UNIT_TANK_1` | 1002 | Red Tank |
| `ID_BUILDING_FORTALEZA_1` | 80 | Fortress I |
| `ID_UNIT_DRONE_MASTER` | 1370 | Drone Master |
| `ID_UNIT_REAPER` | 1375 | Reaper |
| `ID_UNIT_KNIGHT_EXOSUIT` | 1390 | Knight Exosuit |
| `ID_UNIT_DRONE_MASTER_2` | 1400 | Drone Master 2 |

## Appendix B — Files read (evidence index)

```
scripts/core/isoengine/IsoEngine.as                (3552 lines)
scripts/core/isoengine/IsoUnit.as                  (2846)
scripts/core/isoengine/IsoFightingElement.as       (1414)
scripts/core/isoengine/IsoElement.as               (1507)
scripts/core/isoengine/IsoBuilding.as              (1429)
scripts/core/isoengine/IsoInteractiveElement.as
scripts/core/isoengine/PropertyManager.as
scripts/core/isoengine/StatsModifier.as
scripts/core/isoengine/DefaultStatsModifier.as
scripts/core/isoengine/isoUtils/CheckFunctions.as
scripts/core/isoengine/delegates/{Delegate,UnitDelegate,BuildingDelegate,AbstractDelegate,
                                  AbstractUnitDelegate,AbstractUnitHeroDelegate,AbstractBuildingDelegate,
                                  DelegatesManager,ResourceDelegate}.as
scripts/core/isoengine/delegates/units/*.as        (229 files; sampled: Drone, Machinegun,
                                  MultiShot, Medic, Healer, Melee, Projectile, DelayedAttackUnit,
                                  DoubleMachinegun, Kamikaze, Flamethrower, Mortar, Ignition,
                                  BlueAnvil, Bonecrusha, AtomicBonecrusha, Bushwacker, BlackHole,
                                  AgamemnonFortress, CrimsonCenturion, ChemicalGunner, CycloneMech,
                                  Centaur, Brawler, BlackDragon)
scripts/core/isoengine/delegates/buildings/*.as    (53 files; sampled: Tower, BasicFortress, Bunker,
                                  MachinegunTower, MultiShotTower, ElectricTower)
scripts/core/generalAttacks/**                      (AbstractDamage, AbstractAttackCondition,
                                  AbstractSpecialAttack, SpecialUnitAttackCreator, UnitFilters,
                                  attackConditions/*, damages/*, specials/*)
scripts/core/attacks/**                             (AbstractDamage, AbstractSpecialAttack,
                                  damages/*, special_attacks/*)
scripts/core/{UnitXPLevelInfo,SpecialUnitAttack,SpecialUnitAttackLimit,SpecialUnitAttackSpawn,
              Key,Stats,Config,Constants,BuildingReference,GameStatic}.as
scripts/core/{isoengine,generalAttacks,attacks,UnitXPLevelInfo,Key,Stats,Config}.as
scripts/battle/{Assault,IA}.as
scripts/battle/projectiles/{AbstractProjectile,Machinegun}.as
scripts/commands/{CmdEndAttack,CmdEndQuest,CmdAddUnitXP,CmdModifyEnergy,CmdKill,CmdSell}.as
scripts/managers/{ProjectileManager,CommandManager,ResourceManager,PlayerStatus}.as
scripts/utils/RandomGenerator.as
config/main.json                                    (items[], globals{})
<upstream-repo>\command.py   (end_quest, end_attack)
```

## Appendix C — Things explicitly checked and found *not* to exist

* `scripts/core/Key.as` — keyboard input only (`isDown`, debug cheat key sequences). **No stat keys.**
* `scripts/core/Stats.as` — an FPS/memory debug overlay. **No stat logic.**
* `scripts/core/utils/RandomGenerator.as` — **does not exist**; the file is `scripts/utils/RandomGenerator.as`.
* `scripts/core/isoengine/PropertyManager.as` — holds *property-name* constants, not numeric stats.
* No per-attack or per-unit energy cost exists anywhere in the iso engine (see §9).
* `scripts/core/attacks/**` (legacy) and `scripts/core/generalAttacks/**` (current) are two parallel,
  partly-overlapping damage frameworks; only the `generalAttacks` one is used by hero units.
