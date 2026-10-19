# Unit & Building Behaviour Tables — the Rules-Port Specification

**Roadmap task B3.** The game's behaviour is not in the config; it is in 285 ActionScript
delegates. This document and its machine-readable tables reduce those delegates to data, so
the rules engine can be written from a specification rather than from prose.

| | |
|---|---|
| **Source** | `core/isoengine/delegates/` in the decompiled `Basesec_1.5.4.swf` (1 387 classes) |
| **Tooling** | `node scripts/decompile-client.mjs` → `node scripts/analyze-delegates.mjs` |
| **Data** | [`../data/item-delegate-map.json`](../data/item-delegate-map.json) · [`../data/unit-behaviour.json`](../data/unit-behaviour.json) · [`../data/building-behaviour.json`](../data/building-behaviour.json) |

---

## 1. How the client's behaviour is wired

Three files carry it:

| File | Role |
|---|---|
| `core/Constants.as` | **724** `ID_*` constants — the item ids the client knows |
| `core/isoengine/delegates/DelegatesManager.as` | **402** `registerDelegate(<Class>, <config>, Constants.ID_*)` calls — the authoritative **item id → behaviour class** mapping |
| `core/isoengine/delegates/{units,buildings}/*.as` | The behaviour itself (1.32 MB across 229 unit delegates + 56 building delegates) |

A delegate may serve several item ids — `BaseBarrackDelegate` alone covers ~90 academy
buildings. The mapping is therefore many-to-one, and it is the **only** place the client's
item catalogue is written down.

### Coverage

| | |
|---|---|
| Item ids mapped to a delegate | **679** of the 724 `ID_*` constants (93.8 %) |
| Delegate classes | **285** (229 unit + 56 building) |
| Delegates with special attacks | **138** |
| Special attacks declared | **478** |
| Distinct projectile definitions referenced | **92** |
| Delegates that spawn other units | **96** |
| Distinct damage classes referenced | **10** |
| Delegates with no item id | 7 (base/helper classes: `BasicButtonDelegate`, `BasicFortressDelegate`, `BasicTravelDelegate`, `DelayedAttackUnitDelegate`, `DragonDelegate`, `FortressBarrackDelegate`, `TowerDelegate`) |

## 2. The behaviour hooks a delegate can override

The base class `AbstractUnitDelegate` defines the lifecycle. How often each hook is
overridden across the 285 delegates:

| Hook | Overridden by | Meaning |
|---|---|---|
| `onAttack` | **231** | the unit's attack behaviour — nearly every unit customises it |
| `onInit` | **173** | per-frame initialisation, animation and fire timing |
| `getInfoButtonStore` | 24 | the info-button tooltip for a unit/building |
| `initializeExtendedPortrait` | 19 | the portrait shown in unit panels |
| `onControlAnimation` | 16 | animation state control |
| `onFrame` | 14 | per-animation-frame behaviour (projectile launch) |
| `onMoveStart` | 14 | movement start behaviour |
| `onDead` | 12 | death behaviour |
| `checkHasTargetInRange` | 7 | custom targeting predicate |
| `onUpdateAnimation` / `receiveAttack` | 7 / 7 | animation updates / taking a hit |
| `onUpdateMove` | 6 | movement updates |
| `highlight` / `unhighlight` | 5 / 5 | selection visuals |
| `click`, `canMove`, `canGetInside`, `hasReachedConstructionLimit` | 4 / 3 / 3 / 3 | interaction and gating |

The first two hooks carry almost all the per-unit differentiation. **A rules-engine port
that implements `onAttack` and `onInit` covers the large majority of the 1.32 MB.**

## 3. Special attacks

478 special attacks are declared across 138 delegates, in four constructor flavours:

| Constructor | Count | Signature |
|---|---|---|
| `SpecialUnitAttack` | 264 | the standard attack: cooldown, name, icon, handler |
| `SpecialUnitAttackCreator` | 176 | a **factory** that builds an attack at runtime |
| `SpecialUnitAttackSpawn` | 37 | an attack that spawns a unit |
| `SpecialUnitAttackLimit` | 1 | an attack gated by a limit |

Each attack records: the slot index (`arAttacks[n]`), the kind, the display name, the
**button icon** (which maps to `assets/thumbs/btn_<id>_<ability>.jpg`), the handler
method, and the "no target" message.

### Example — `LiquidMechDelegate` (item 1222, "Liquid Mech")

| # | Kind | Name | Icon | Handler |
|---|---|---|---|---|
| 0 | `SpecialUnitAttack` | Acid Rain | `btn_liquid_mech_acid_rain` | `acidRainAttack` |
| 1 | `SpecialUnitAttack` | Acid Balls | `btn_liquid_mech_acid_balls` | `acidBallsAttack` |
| 2 | `SpecialUnitAttack` | Clone | `btn_liquid_mech_clone` | `cloneAttack` |
| 3 | `SpecialUnitAttackSpawn` | Spawn Drone | `btn_liquid_mech_drone` | `doSpawn` (spawns `ID_UNIT_LIQUID_MECH_DRONE`) |

Projectiles: `ALIEN_FLEGMA`, `P_ACID_BLUE`, `BLAST_ACID_BLUE`, `MISC_ACID_FLOOR`,
`MISC_ACID_RAIN`.

> The `icon` field is the join key to the asset tree: the special-attack button images in
> `assets/thumbs/` are named `btn_<name>`, and the assets report already found that
> `btn_1180_hiper` is the only special-attack button with no matching file.

### Buildings have no special attacks

**0 of 56** building delegates declare a special attack. Buildings fight through their
garrison and the shared `SpecialUnitAttack` framework is unit-only. That is a useful
simplification for the rules engine: the special-attack system needs implementing for
units only.

### The damage classes

Ten distinct damage classes are referenced by the delegates:

```
SimpleDamage · AreaDamageSpecialAttack · BleedingDamage · DamageOverTime · DelayedDamage
DirectKillDamage · DizzyDamage · IncinerateDamage · PushInAirDamage · SequencedDamage
```

(`AreaDamageSpecialAttack` and `specialAttack3Damage` are the two that are not plain
damage types — the first is a special attack used as a damage source, the second is a
locally-named damage class.)

## 4. The content gap — 129 ids against the *base* config, 7 against the *shipped* one

> **Corrected.** This section originally reported **129** client-only item ids and claimed
> their stats were unrecoverable. That was measured against the **unpatched** 778-item
> config. The config that actually ships is the base **plus five JSON-Patch deltas**, and
> the `unit_patch` delta *adds the 1307–1431 wave with full stats*. The real gap is **7
> item ids and 1 sprite id**, not 129 and 123. Verified by the content build
> (`packages/content/src/build.ts`), which reproduces the upstream server's own counts.

### 4.1 How the config actually ships

`config/main.json` is the 29-Aug-2012 capture: **778 items, 104 globals**. The upstream
server then applies the five deltas in `config/patch/patches.txt`, in this order:

| Patch | Effect |
|---|---|
| `atom_fusion_item` | 1 item appended (the Atom Fusion) |
| `unit_patch` | **121 items appended** — the whole 1307–1431 mech/drone wave, **with stats** |
| `atom_fusion_items_data` | 600 property additions to items 382+ (`breeding_order`, `sm_training_time`) |
| `atom_fusion_powerup` | 1 global added (`SOUL_MIXER_POWERUPS_LEVELS`) |
| `targets` | `darts_items` replaced (the wrap fix) |

The result is the content the game actually runs on: **900 items, 105 globals, 27 darts
entries, 100 levels, 91 goals**.

### 4.2 The real gap: 7 client-known item ids, and 1 sprite id

Against the **shipped** 900-item config, the client knows 679 ids with a behaviour
delegate, and only **7** of them are absent from the config:

| Id | Constant | Delegate | Kind |
|---|---|---|---|
| 27 | `ID_BUILDING_DECO_YELLOW_FLOWERS` | `BasicDecorationDelegate` | building |
| 29 | `ID_BUILDING_INFIRMARY_1` | `BaseBarrackDelegate` | building |
| 36 | `ID_BUILDING_GARAGE_1` | `BaseBarrackDelegate` | building |
| 99 | `ID_BUILDING_DECO_PINK_FLOWERS` | `BasicDecorationDelegate` | building |
| 1359 | — | — | unit |
| 1405 | — | — | unit |
| 10130 | — | — | unit |

And exactly **one** sprite id — `199` — has no config entry at all. (The earlier report
also flagged `302`, the Soul Mixer / Atom Fusion: it is absent from the *base* config but
**added by `atom_fusion_item`**, with full stats. The live session showed the game
granting "Congratulations! You've unlocked the Atom Fusion!", so it is live content.)

### 4.3 The 1307–1431 wave — 124 items across 71 families, **with stats**

| | |
|---|---|
| Items | **124** |
| Families | **71** |
| Families shipping a unit **and** a companion drone | 58 |
| Drone-only families (`Drone Master` and its variants) | 8 |
| Distinct delegates used | 71 |

The families: `GLAIVE_STORM_MECH`, `STAMPEDE_MECH`, `HELLFIRE_MECH`, `SPLINTER_MECH`,
`ANVIL_PATTERN_MECH`, `BLADE_STORM_MECH`, `SPECTRE_MECH`, `STALKER_MECH`,
`SLAUGHTERER_MECH`, `CRUSHER_MONARCH_MECH`, `VORTEX_MECH`, `BOMBARDIER_MECH`,
`FORGELORD_MECH`, `SHREDDER_MECH`, `RAVEN_MECH`, `CYCLONE_MECH`, `YAMATO_MECH`,
`STEEL_WANDERER_MECH`, `TEMPEST_MECH`, `SERVOWORM`, `SCARAB`, `CENTAUR`,
`EVIL_SLAUGHTERER`, `BISMARK_MECH`, `BONECRUSHA`, `BRAWLER`, `HAVOC`, `HAMMERHEAD`,
`ATOMIC_BONECRUSHA`, `REAPER`, `BLACK_HOLE`, `IGNITION`, `AGAMEMNON_FORTRESS`,
`TYPHOON_SERVODRAGON`, `SCARLET_SUPERFULCRUM`, `GUARDIAN`, `KNIGHT_EXOSUIT`,
`FIRE_GAMERA`, `CYCLONE_BATTLESUIT`, `CHEMICAL_GUNNER`, `BLUE_ANVIL`, `OVERSEER`,
`URBAN_BUSTER`, `SKORPION_FORTRESS`, `PAULDRON_MECH`, `SHARKBITE`, `CRIMSON_CENTURION`,
`WARLORD`, `CYBER_INQUISITOR`, `KNUCKLEDRAGGER`, `STEELGLADIATOR`, `TARANTULA`,
`INTRUDER`, `SUPERFULCRUM_ARMOR`, `BUSHWACKER`, `BUSHWACKER_MINE`, `TEMPLAR_EXOSUIT`,
`MARAUDER_BATTLE_CHASIS`, `HARVESTER`, `DRONE_MASTER*`, `ID_DUMMY_UNIT`.

Most wave units use the shared drone delegates (`ProjectileDelegate` × 47,
`MultiShotDroneDelegate` × 6, `KamikazeDelegate` × 3, and one each of
`BombardierDroneDelegate`, `DroneMasterDelegate`, `MachinegunDelegate`,
`HealerDelegate`, `DroneMaster2Delegate`, `DroneDelegate`, `PhalanxDroneDelegate`).

**Their stats are in the shipped config.** Sampled from the built bundle:

| Id | Name | Type | Attack | Life | Range | Interval | Pop |
|---|---|---|---|---|---|---|---|
| 1307 | Glaivestorm Mech | u | 86 | 3 900 | 10 | 35 | 4 |
| 1323 | Slaughterer Mech | u | 102 | 4 700 | 10 | 35 | 4 |
| 1400 | Drone Master 2.0 | u | 178 | 8 600 | 10 | 35 | 4 |
| 1423 | Knuckledragger Drone | u | 14 | 800 | 11 | 30 | 2 |
| 1007 | Soldier | u | 8 | 50 | 5 | 35 | 1 |

### 4.4 The client has no stat table — and does not need one

`core/StaticData.as` builds every unit's stat block from an object supplied by the
**server**:

```actionscript
this.attack          = parseInt(param1.attack);
this.defense         = param1.defense;
this.life            = param1.life;
this.attack_range    = parseInt(param1.attack_range);
this.attack_interval = parseInt(param1.attack_interval);
```

There is **no hardcoded stat table anywhere in the client**, and there does not need to be:
the server supplies the stats, and the config that ships has them.

> **The content gap is therefore 7 item ids and 1 sprite id** — not 129. For those, the
> clone knows the delegate, the special attacks, the projectiles and the spawn behaviour,
> and must supply `attack`, `defense`, `life`, `attack_range`, `attack_interval`,
> `population` and `cost` itself, either by balancing from the sibling items in the same
> family or by sourcing a later config capture.

## 5. What this means for the rules engine

| Observation | Consequence |
|---|---|
| `onAttack` + `onInit` cover 231/173 of 285 delegates | implement those two hooks first; they are the bulk of the port |
| Buildings have no special attacks | the special-attack system is unit-only |
| 92 distinct projectiles, referenced by name | projectile behaviour is **data** (`ProjectileDefinition`), not code — port the definitions, not the 92 behaviours |
| 10 damage classes | a small, closed set to implement |
| 96 delegates spawn other units | spawning is driven by `Constants.ID_*` targets — the spawn graph is already in the tables |
| The item→delegate map is authoritative | the content bundle should carry the delegate reference per item, so the rules engine can look up behaviour by item id |

## 6. Reproducing this

```bash
node scripts/decompile-client.mjs        # -> .work/as/basesec/  (1 387 classes)
node scripts/analyze-delegates.mjs         # -> re/data/{item-delegate-map,unit-behaviour,building-behaviour}.json
```

The decompilation is an intermediate artefact and is git-ignored; only the derived tables
are committed.

## 7. Known limits of this extraction

* **Static, not dynamic.** The tables record what each delegate *declares*. A behaviour
  that is only reachable under a condition the extractor cannot see is still captured, but
  the *conditions* are in the handler method bodies, not in the table.
* **`SpecialUnitAttackCreator` (176 of 478) is a factory.** The table records its name and
  icon, but the attacks it builds at runtime are constructed inside the handler, so a
  factory-based attack's parameters are not in the table. This is the single largest
  residual gap in the extraction.
* **`getInfoButtonStore` and `initializeExtendedPortrait` payloads** are recorded as
  overrides but their content (tooltip text, portrait art) is not extracted.
* The 7 unmapped delegates are base classes, not content.
* The decompiler's output is occasionally imperfect; every claim here was taken from the
  literal source, and the tables are regenerable for re-checking.
