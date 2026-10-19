<!--
  Generated investigation artifact.
  Source of truth for the details inside is the file it was produced from:
  decompiled ActionScript 3 (FFDec 26.3.0) of assets/flash/Basesec_1.5.4.swf,
  the Python server sources, and live traffic captured from a real Adobe Flash
  Player session against the local server.
-->

# Assets & Content Pipeline

> **Scope:** Filesystem inventory of the 3 200+ asset files and programmatic resolution of every config item id to its sprite/thumb/sound file.
>
> **Method:** Filesystem inventory of the 3 200+ asset files and programmatic resolution of every config item id to its sprite/thumb/sound file.
>
> **Subject:** asset taxonomy, config->asset mapping, per-item table, conversion plan for a non-Flash client
>
> Part of the Social Wars reverse-engineering report set. See [`../README.md`](../README.md)
> for the document map and [`../docs/00-EXECUTIVE-SUMMARY.md`](00-EXECUTIVE-SUMMARY.md) for the
> cross-cutting conclusions.

---

# 05 — Assets and Content Pipeline

**Project:** Social Wars preservation project (Zynga / Social Point, Flash client `Basesec_1.5.x.swf`)  
**Asset root:** `C:\Users\Edison\Desktop\Projects\socialwarriors\assets\`  
**Game config:** `C:\Users\Edison\Desktop\Projects\socialwarriors\config\main.json`  
**AS3 sources consulted:** `<as3-root>\scripts\` (1 387 `.as` files)

All counts, byte totals, id mappings and file lists in this report were produced by running Python over the
real tree (scripts in `%TEMP%\opencode\socialwarriors\work\a01..a17*.py`). Nothing is estimated. Items that
could not be proven from the tree or the AS3 sources are explicitly marked **UNVERIFIED**.

---

## 1. Full asset-tree inventory

### 1.1 Top-level directories

| Directory | Files | Bytes | Size |
|---|---|---|---|
| `sprites/` | 862 | 374,565,643 | 357.21 MB |
| `flash/` | 60 | 256,051,703 | 244.19 MB |
| `images/` | 578 | 68,416,827 | 65.25 MB |
| `thumbs/` | 1314 | 32,583,246 | 31.07 MB |
| `fx/` | 205 | 9,470,589 | 9.03 MB |
| `sounds/` | 140 | 5,803,106 | 5.53 MB |
| `characters_2/` | 26 | 2,193,225 | 2.09 MB |
| `magic/` | 10 | 1,430,448 | 1.36 MB |
| `swf/` | 1 | 492,559 | 0.47 MB |
| `externalized/` | 1 | 488,330 | 0.47 MB |
| `fonts/` | 2 | 88,994 | 0.08 MB |
| **TOTAL** | 3199 | 751,584,670 | **716.77 MB** |

> Note on the brief: the task text quoted *~1 753 thumbs* — that number is the **total JPG count in the whole tree**
> (1 753 = 1 314 in `thumbs/` + 439 in `images/`). `assets/thumbs/` actually holds **1 314** files, not 1 753.
> `assets/images/` is a 13-directory localized tree holding **578** files (130 JPG + 15 PNG + 3 SWF at the
> `en/` level, plus chapters / goals / news / packs / quests sub-trees), and `assets/fonts/` holds **2 `.swf`**
> files (**not** TTF/OTF) — they are runtime-loaded Flash font libraries, see §7.

### 1.2 Per-directory breakdown

| Directory | Files | Bytes | Size | Extensions |
|---|---|---|---|---|
| `characters_2/` | 26 | 2,193,225 | 2.09 MB | .swf×26 |
| `externalized/viral_buttons/` | 1 | 488,330 | 0.47 MB | .swf×1 |
| `flash/` | 60 | 256,051,703 | 244.19 MB | .swf×60 |
| `fonts/` | 2 | 88,994 | 0.08 MB | .swf×2 |
| `fx/` | 205 | 9,470,589 | 9.03 MB | .swf×205 |
| `images/` | 5 | 634,164 | 0.60 MB | .jpg×2, .png×3 |
| `images/en/` | 148 | 8,920,130 | 8.51 MB | .jpg×130, .png×15, .swf×3 |
| `images/en/chapters/` | 12 | 2,362,654 | 2.25 MB | .jpg×12 |
| `images/en/chapters/simple/` | 3 | 768,680 | 0.73 MB | .jpg×3 |
| `images/en/chapters2/` | 12 | 2,324,470 | 2.22 MB | .jpg×12 |
| `images/en/chapters2/simple/` | 5 | 1,156,563 | 1.10 MB | .jpg×5 |
| `images/en/goals/` | 60 | 2,558,775 | 2.44 MB | .jpg×50, .png×10 |
| `images/en/intro/` | 6 | 2,939,421 | 2.80 MB | .swf×6 |
| `images/en/lost/` | 30 | 508,016 | 0.48 MB | .png×30 |
| `images/en/news/` | 111 | 18,443,698 | 17.59 MB | .jpg×111 |
| `images/en/packs/` | 63 | 6,303,874 | 6.01 MB | .jpg×3, .png×60 |
| `images/en/quests/` | 104 | 20,045,399 | 19.12 MB | .jpg×104 |
| `images/en/quests_map/` | 7 | 1,319,841 | 1.26 MB | .jpg×7 |
| `images/en/res_packs/` | 12 | 131,142 | 0.13 MB | .png×12 |
| `magic/` | 10 | 1,430,448 | 1.36 MB | .swf×10 |
| `sounds/` | 140 | 5,803,106 | 5.53 MB | .mp3×140 |
| `sprites/` | 862 | 374,565,643 | 357.21 MB | .swf×862 |
| `swf/` | 1 | 492,559 | 0.47 MB | .swf×1 |
| `thumbs/` | 1314 | 32,583,246 | 31.07 MB | .jpg×1314 |

### 1.3 Global format totals (drives the conversion plan in §9)

| Format | Files | Bytes | Size |
|---|---|---|---|
| `.swf` | 1176 | 650,762,310 | 620.62 MB |
| `.jpg` | 1753 | 87,393,289 | 83.34 MB |
| `.png` | 130 | 7,625,965 | 7.27 MB |
| `.mp3` | 140 | 5,803,106 | 5.53 MB |

### 1.4 File-name conventions and how names encode meaning

#### 1.4.1 The numeric id prefix

Every gameplay sprite, thumbnail, magic and effect file is named `<id>_<slug>[_<variant>].<ext>`, where `<id>` is
the **numeric `items[].id` from `config/main.json`**, zero-padded to 4 digits for the low id range.

Evidence and numbers:

* `sprites/`: 861 of 862 files start with digits. For **738** of them the numeric prefix is exactly an existing
  `items[].id`; for **123** it is *not* (see §2.7 - the assets are newer than the config snapshot). *Corrected:* the shipped config (base + 5 JSON-Patch deltas) is 900 items and covers all but `199`.
  The single non-numeric sprite is `terreno.swf` (item id 925, “Expandable Land”).
* `thumbs/`: 1 228 of 1 314 files start with digits; **869** of those match a real `items[].id`.
* Examples: `0001_house_1_m` ↔ item `1` “House I”; `0022_tower_1_m` ↔ item `22` “Turret I”;
  `0050_bunker_1_m` ↔ item `50` “Bunker I”; `1007_soldier_1_m` ↔ item `1007` “Soldier”;
  `1075_supreme_m` ↔ item `1075` “Supreme Bot”; `1084_dreadnought_m` ↔ item `1084` “Dreadnought”.
* The **slug** part is a hand-authored English/Spanish/Portuguese legacy name, not a generated token, and it
  encodes the *build tier*: e.g. `house_1`, `house_2`, `house_3` are House I/II/III; `tower_1..tower_8` are the
  turret ladder; `depot_wood_1..4` / `depot_oil_*` / `depot_steel_*` / `depot_gold_*` are the four resource depots
  × 4 levels; `bazooka_academy_1..5` is the bazooka barracks ladder.
* The **suffix** part encodes the sprite *variant* selected at random per placed instance.

#### 1.4.2 The `_m` / `_w` / `_premium` / `_old` suffixes

| Suffix | Count (sprites) | Count (thumbs) | Meaning | Evidence |
|---|---|---|---|---|
| `_m` | 284 | 281 | **Two distinct meanings.** (a) For the 5 gender-variant units it is the *male* sprite. (b) For every other building/unit sprite it is a pervasive legacy token from the original art pipeline (see below). | see below |
| `_w` | 5 | 5 | *Female* sprite, the alternate variant of the same 5 units. | see below |
| `_premium` | 0 | 0 | Premium/reward variant. Only exists in `characters_2/good_1_m_premium.swf`. | `characters_2/` listing |
| `_old` | 0 | 0 | Never used in asset file names. It appears only inside `config['images']` paths (`/chapters/chapter_5_old.jpg`) and all 5 of those files are missing from the tree. | §2.4 |

**`_m` / `_w` — VERIFIED for the 5 gendered units.** Exactly 5 units carry both a `_m` and a `_w` variant:

| item id | name | `img_name` (config) |
|---|---|---|
| 1001 | Worker I | `1001_worker_m,1001_worker_w` |
| 1007 | Soldier | `1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_w` |
| 1008 | Bazooka | `1008_bazooka_1_m,…×4…,1008_bazooka_1_w` |
| 1014 | Machine Gun Jeep | `1014_machinegunjeep_1_m,…×4…,1014_machinegunjeep_1_w` |
| 1034 | UN Allied | `1034_un_allied_1_m,…×4…,1034_un_allied_1_w` |

The client picks one at random per spawn: `BuildingReference.as:78` →
`this.imgIndex = Math.floor(Math.random() * this.building.img_name.length);` and `BuildingReference.as:130`
returns `building.img_name[imgIndex]`. The duplicated entries in the 4-of-5 items are therefore a **weight**
(80 % male / 20 % female for Soldier, Bazooka, Machine Gun Jeep, UN Allied; 50/50 for Worker).

Rendered proof (frame 1 exported with JPEXS FFDec 26.3.0 from the two SWFs): `1007_soldier_1_m.swf` is a
bearded soldier in a green uniform; `1007_soldier_1_w.swf` is a blonde soldier in a red uniform — i.e. **m**ale /
**w**oman. The client also asks the player for a sex at registration (`PopupChooseGender.as`, `Base.gender`,
`Constants.GENDER_MALE` / `GENDER_FEMALE`), so the pair is the per-unit randomised gender variation.

**`_m` on the other 279 sprites — UNVERIFIED meaning.** 279 sprite base names end in `_m` with **no** `_w`
counterpart (e.g. `0001_house_1`, `0022_tower_1`, `0050_bunker_1`, `0080_fortress_1`). Since the same token
cannot simultaneously mean “male” for units and something else for buildings, and since **no** building or
non-gendered unit in the tree has a gender pair, the `_m` on those 279 is a *legacy art-pipeline marker*
(most plausibly an asset-resolution/variant marker inherited from the original Zynga art export).
It carries **no functional meaning in the client**: the client never parses the suffix, it only ever uses the
opaque `img_name` string as a file name. A re-implementation can therefore keep or drop `_m` freely, as long as
the config `img_name` → file mapping stays 1:1.

#### 1.4.3 FX file naming: `p.` / `b.` / `m.` prefixes

All 205 files in `assets/fx/` are `<role>.<name>.swf`:

| Prefix | Count | Role (verified from `ProjectileDefinition.as`) |
|---|---|---|
| `p.` | 143 | **Projectile** — the object that travels from shooter to target (`P_BULLET = "p.bullet"`, `P_LASER = "p.laser"`, `P_MISSILE_M = "p.missileM"`, …) |
| `b.` | 56 | **Blast / impact** — the effect played where the projectile lands (`BLAST_BAZOOKA = "b.bazooka"`, `BLAST_MISSILE = "b.missile"`, `BLAST_EARTH = "b.earth"`, …) |
| `m.` | 6 | **Misc / area-of-effect overlay** — persistent field effects (`MISC_ACID_RAIN = "m.acidRain"`, `MISC_BLUE_SHIELD = "m.blueShield"`, `MISC_CRISTAL_RAIN = "m.cristalRain"`, `MISC_RAY_RAIN = "m.rayRain"`, `MISC_ACID_FLOOR = "m.acidFloor"`, `MISC_SATELLITE_LASER = "m.satelliteLaser"`) |

Every one of the 205 fx files is named by exactly one `public static const` in
`scripts/battle/projectiles/ProjectileDefinition.as` — **205 of 219** constants in that file point at an existing
fx file; the remaining **14 constants point at files that do not exist** in the tree (see §5.4).
Loading is `Base.Main.apfx + "fx/" + <id> + ".swf"` (`managers/ProjectileManager.as:141`).

#### 1.4.4 `characters_2/` naming

26 cutscene/character SWFs, named `<side>_<n>[_m][_premium].swf`:

* `good_1_m.swf` … `good_12_m.swf` (12 files) + `good_1_m_premium.swf` — the “good” side cast (the `_m` here is
  *not* a gender marker; there is no `_w` counterpart).
* `evil_1.swf`, `evil_2_2.swf`, `evil_3_2.swf`, `evil_4.swf`, `evil_4_2.swf`, `evil_5.swf`, `evil_6_2.swf`,
  `evil_8.swf`, `evil_9.swf`, `evil_10.swf`, `evil__7.swf` (double underscore — upstream typo, kept as-is).
* `nebula_priest_mentor.swf`.

Loaded by `scripts/cutscene/Character.as:77` → `Base.Main.apfx + Config.CHARACTERS_FOLDER + src`, where
`Config.CHARACTERS_FOLDER = "characters_2/"` (`core/Config.as:242`).

#### 1.4.5 Other naming notes

* `assets/flash/` — `Basesec_1.4.5.swf` … `Basesec_1.5.4.swf` (58 historical client builds) + `Debug_1.5.4.swf`
  + `SWLoader.swf` (the tiny loader shell that boots `Basesec`). The *current* client is `Basesec_1.5.4.swf`
  (`Config.VERSION = "1.5.4"`, `Config.BUILD_NUMBER = "__BUILD_NUMBER_TMPL__"`).
* `assets/swf/dynamic2.swf` — a **runtime-loaded class library**. `core/ExternalClass.as:11`
  (`LIB_NAME = "dynamic2.swf"`) loads it via `Base.AssetsLoader.loadAsset("swf/" + libraryName, …)` and then
  pulls swapped-in classes out of it with `ApplicationDomain.currentDomain.getDefinition(classFQN)`.
  This is the hot-swap hook for post-launch content — a re-implementation must decide whether to keep it.
* `assets/fonts/` — `en_ArialRoundedBold.swf`, `en_KomikaAxis.swf`. These are *runtime-loaded font libraries*,
  not TTF/OTF. `scripts/utils/FontsLoader.as:60` builds the URL as
  `fontsDir + (loadedLang ? loadedLang + "_" : "") + fontName + ".swf"` → `fonts/en_KomikaAxis.swf`.
  See §7.

---

## 2. Mapping `config/main.json` → the asset tree

### 2.1 The URL templates the client actually uses (all from the decompiled AS3)

`Base.Main.apfx` is the asset base URL (set from the `staticUrl` loader parameter, `core/Base.as:867`).
All asset requests are `apfx + <template>`:

| Asset kind | URL template | Source in AS3 |
|---|---|---|
| Building/unit sprite | `sprites/<img_name>.swf` | `core/Base.as:7303`, `GUI/AnimatedUnit.as:70`, `GUI/AnimatedUnitCentered.as:66` |
| Sprite (lazy, by class) | `<type>/<name>.swf` | `managers/assets/SingleAssetLoader.as:31` |
| Inventory thumbnail | `thumbs/<img_name>.jpg` | `utils/ThumbManager.as:56` |
| Special-attack button | `thumbs/<imgThumb>.jpg` | `GUI/PortraitSpecialAttack.as:255` → `imgThumb` of `core/SpecialUnitAttack.as:105` |
| Sound effect | `sounds/<file>.mp3` | `core/SoundFile.as:55` |
| Music | `sounds/BACKGROUND.mp3` / `sounds/battle_1.mp3` | `managers/SoundManager.as:37,819,838` |
| Magic / tech spell | `magic/<img_name>.swf` | `core/magic/MagicSpell.as:92` |
| Spell button icon | `images/<lang>/<img_name>.jpg` | `GUI/SpellButton.as:29` (via `core/ImageLoader.as:47`) |
| Projectile / blast fx | `fx/<id>.swf` | `managers/ProjectileManager.as:141` |
| Localized image | `images/<lang>/<path>` | `core/ImageLoader.as:47` |
| Runtime font | `fonts/<lang>_<fontName>.swf` | `utils/FontsLoader.as:60` + `core/Base.as:1200` |
| Cutscene character | `characters_2/<src>` | `cutscene/Character.as:77` |
| Runtime class library | `swf/dynamic2.swf` | `core/ExternalClass.as:25` |
| Cross-promo viral button | `externalized/viral_buttons/<name>.swf` | `GUI/CrossDCiViralIcon.as:20` + `managers/AssetManager.as:16` |
| Security token | `externalized/weird.txt` | `core/Base.as:1112` |

`ImageLoader.as:46` picks the language sub-folder from `Base.Items.localizationImgs[path]`, which is exactly the
`config['images']` map (`/path` → `lang`). **All 607 entries are `'en'`**, so the tree only needs `images/en/`.

### 2.2 `items[].img_name` → sprite / thumbnail

**Rule (exact, no globbing):**

```
sprite  = assets/sprites/<img_name>.swf
thumb   = assets/thumbs/<img_name>.jpg
```

`items[].img_name` is a **comma-separated list**, split by `StaticData.parseVectorString()`
(`core/StaticData.as:242-267`) into `Vector.<String>`; the client then picks one index at random
(`core/BuildingReference.as:78`). **5 of the 778 items use more than one variant**; all 5 are the gendered units
listed in §1.4.2:

| item id | name | variants |
|---|---|---|
| 1001 | Worker I | `1001_worker_m,1001_worker_w` |
| 1007 | Soldier | `1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_w` |
| 1008 | Bazooka | `1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_w` |
| 1014 | Machine Gun Jeep | `1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_w` |
| 1034 | UN Allied | `1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_w` |

**Resolution results (all 778 items):**

| Metric | Count |
|---|---|
| items with **at least one** existing `sprites/<img_name>.swf` | **768** / 778 |
| items with **no** sprite at all | **10** / 778 |
| items with **at least one** existing `thumbs/<img_name>.jpg` | **749** / 778 |
| items with **no** thumbnail at all | **29** / 778 |
| sprite files in tree not referenced by any `img_name` | **122** / 862 |
| thumb files in tree not referenced by any `img_name` | **593** / 1 314 |

#### 2.2.1 The 10 items with NO sprite

| id | name | type | category_id | `img_name` | Why it is missing |
|---|---|---|---|---|---|
| 137 | Spy Academy | b | 3 | `0137_spy_academy_m` | no `0137_spy_academy_m.swf` in tree |
| 921 | Treasure Chest | b | 8 | `treasure` | quest/offer pseudo-item; never rendered on the map |
| 922 | Dummy 9-91 | b | 9 | `vacaPerdida` | quest/offer pseudo-item; never rendered on the map |
| 924 | Dummy 12-121 | b | 12 | `casachina` | quest/offer pseudo-item; never rendered on the map |
| 927 | Prison | b | 8 | `10027_prision` | quest/offer pseudo-item; never rendered on the map |
| 982 | Chained Red Spinner | b | 4 | `982_chained_red_spinner` | chained offer pseudo-item |
| 1011 | Ms. Evilia | u | 7 | `1011_bad_girl_m` | no `1011_bad_girl_m.swf` in tree |
| 10000 | Chained Bonus + Giant Walker | b | 4 | `10000_chained_bonus_giant_walker` | chained/cross-promo pseudo-item |
| 10034 | Chained Hercules Mech | b | 4 | `10034_chained_hercules_mech` | chained/cross-promo pseudo-item |
| 10048 | Play Dragon City | b | 4 | `10048_cross_dc` | chained/cross-promo pseudo-item |

**Important nuance:** the “variant list” rows (1001, 1007, 1008, 1014, 1034) are **not** actually missing —
every individual variant resolves to a sprite and a thumb. They only fail a naive `sprites/<whole img_name>.swf`
lookup, because the raw `img_name` string contains commas. A correct implementation must split on `,` first.
The genuinely missing ones are: **137, 921, 922, 924, 927, 982, 1011, 10000, 10034, 10048** (10 items).

#### 2.2.2 The 29 items with NO thumbnail

| id | name | type | `img_name` |
|---|---|---|---|
| 127 | Enemy's harbour | b | `0127_enemy_harbour_m` |
| 132 | Troubled Traveller | b | `0132_troubled_traveller_m` |
| 133 | Injured Soldier | b | `0133_injured_soldier_m` |
| 137 | Spy Academy | b | `0137_spy_academy_m` |
| 921 | Treasure Chest | b | `treasure` |
| 922 | Dummy 9-91 | b | `vacaPerdida` |
| 924 | Dummy 12-121 | b | `casachina` |
| 925 | Expandable Land | l | `terreno` |
| 927 | Prison | b | `10027_prision` |
| 928 | Broken Bridge | b | `10028_broken_bridge` |
| 929 | Bridge | b | `10029_bridge` |
| 949 | Atrezzo Harbour | b | `10049_harbour` |
| 950 | Nice fountain | b | `10050_nice_fountain` |
| 951 | Orange Tree | b | `10051_orange_tree` |
| 952 | Chickens | b | `10052_chickens` |
| 953 | Lost Rocket | b | `10053_lost_rocket` |
| 954 | Astronaut Pack | b | `10054_astronaut_pack` |
| 955 | Destroyed Tank | b | `10055_destroyed_tank` |
| 956 | Lost Puppies | b | `10056_lost_puppies` |
| 957 | Lost Oil Barrels | b | `1005_oil_barrels` |
| 960 | Chest | b | `10060_chest` |
| 982 | Chained Red Spinner | b | `982_chained_red_spinner` |
| 1011 | Ms. Evilia | u | `1011_bad_girl_m` |
| 1129 | Samurai Minibot | u | `1129_samurai_minibot` |
| 1161 | Rune Golem | u | `1161_viking_rune_golem` |
| 10000 | Chained Bonus + Giant Walker | b | `10000_chained_bonus_giant_walker` |
| 10034 | Chained Hercules Mech | b | `10034_chained_hercules_mech` |
| 10040 | Chained Half Price Party Weekend | b | `10040_chained_half_party_price_party_weekend` |
| 10048 | Play Dragon City | b | `10048_cross_dc` |

All 29 are pseudo/quest items (cross-promo, chained-offer, “lost/destroyed” decoration props) except
**1129 “Samurai Minibot”**, **1161 “Rune Golem”**, and the 5 comma-variant units (which do resolve individually).
`1011` “Ms. Evilia” has neither sprite nor thumb.

#### 2.2.3 Assets present in the tree but not referenced by the config

**122 sprites** are not named by any `items[].img_name`. Every one of them is a **post-config unit**:

| Cause | Count | Detail |
|---|---|---|
| Id not present in the **shipped** `config['items']` | **1** | `199` (1 sprite). *Corrected:* against the unpatched 778-item base config the figure was 123 (`199`, `302` and 121 ids in the 1307-1431 range) — but `unit_patch` **adds the 1307-1431 wave with full stats**, so the shipped 900-item config covers all but `199`. |

The 121 post-config ids are the “Mech / drone” wave: `1307_glaivestorm_mech` … `1431_intruderDrone`.
**Every one of the 122 unreferenced sprites belongs to a unit id the config does not define.**

**593 thumbs** are not named by any `items[].img_name`. They break down into six name families:

| Family | Count | Example | What it is |
|---|---|---|---|
| `<id>_<name>_button<n>` / `_button_<n>` | 208 | `1309_stampedeMech_button1` | special-attack button of a **post-config** unit (ids 1307+) |
| `<id>_special_<n>` | 94 | `1184_special_1` | special-attack button, older naming |
| `btn_<id>_<ability>` | 67 | `btn_1084_rocket` | special-attack button, the family actually referenced by the AS3 `SpecialUnitAttack` constructor |
| `<id>_<name>` (single, no suffix) | 171 | `1162_ultra_bot_drone` | special-attack button of a unit whose `img_name` is different, or a variant thumb |
| `<id>_<name>_<n>` | 41 | `10007_port_1` | numbered variant thumbs (ports, resource tiers) |
| `<id>_<name>_Boton<n>` | 12 | `black_dragon_Boton01` | special-attack buttons of the dragon units |

### 2.3 `items[].type` / `category_id` / `subcategory_id` / `subcat_functional`

`type` is the **render class**, and is what decides sprite-vs-anything-else:

| `type` | Count | Meaning (from `core/Constants.as:1666-1668`) | Asset role |
|---|---|---|---|
| `b` | 469 | `Constants.TYPE_BUILDING` | `sprites/<img_name>.swf` — isometric building, drawn on the map grid |
| `u` | 308 | `Constants.TYPE_UNIT` | `sprites/<img_name>.swf` — animated unit, drawn on the map grid |
| `l` | 1 | (land tile) | item 925 “Expandable Land”, `img_name = terreno` → `sprites/terreno.swf` |

**There is no per-category asset folder.** The category tree is *store UI grouping only* — it selects which tab the
item appears under, never which file is loaded. The file is always `sprites/<img_name>.swf` regardless of category.

| `category_id` | Name (from `config['categories']`) | items |
|---|---|---|
| 7 | **unknown — not in `config['categories']`** | 306 |
| 4 | Decorations | 157 |
| 12 | New | 145 |
| 1 | Village | 72 |
| 3 | Army | 37 |
| 2 | Defense | 26 |
| 8 | **unknown — not in `config['categories']`** | 22 |
| 5 | Wonders | 11 |
| 9 | **unknown — not in `config['categories']`** | 1 |
| 6 | **unknown — not in `config['categories']`** | 1 |

> 4 of the 10 category ids used by items (**7, 8, 9, 6**) are **not** in `config['categories']` (which only defines
> 1 Village, 2 Defense, 3 Army, 4 Decorations, 5 Wonders, 12 New). Category 7 holds 306 items (the bulk of the
> army/units), 8 holds 22 (quest pseudo-items), 9 holds 1 (a dummy), 6 holds 1 (land).

| `subcategory_id` | Parent `category_id` | Name | items |
|---|---|---|---|
| 7 | — | **not in `config['categories']`** | 306 |
| 121 | 12 | Limited Edition | 145 |
| 45 | 4 | Others | 144 |
| 12 | 1 | Factories | 37 |
| 81 | — | **not in `config['categories']`** | 22 |
| 17 | 1 | Miscellaneous | 17 |
| 51 | 5 | Wonders | 11 |
| 14 | 1 | Silos | 11 |
| 31 | 3 | Soldiers | 10 |
| 42 | 4 | Flowers | 10 |
| 21 | 2 | Turrets | 8 |
| 33 | 3 | Aircrafts | 8 |
| 32 | 3 | Vehicles | 8 |
| 23 | 2 | Fortresses | 8 |
| 34 | 3 | Specials | 8 |
| 22 | 2 | Walls | 5 |
| 24 | 2 | Bunkers | 5 |
| 11 | 1 | Houses | 4 |
| 13 | 1 | Fields & Farms | 3 |
| 35 | 3 | Siege | 3 |
| 41 | 4 | Trees | 2 |
| 44 | 4 | Statues | 1 |
| 91 | — | **not in `config['categories']`** | 1 |
| 6 | — | **not in `config['categories']`** | 1 |

**`subcat_functional` is a second, orthogonal classification axis** — it is *not* derived from `subcategory_id`.
There are 24 distinct values over 41 distinct `(subcategory_id, subcat_functional)` pairs. The value looks like
`<functional_code><sub_code>`; the leading digits do **not** line up with the subcategory id:

| `subcat_functional` | items | example `subcategory_id` → name |
|---|---|---|
| 80 | 228 | 7 → ? |
| 411 | 171 | 41 → Trees |
| 111 | 139 | 11 → Houses |
| 83 | 72 | 7 → ? |
| 211 | 28 | 21 → Turrets |
| 129 | 26 | 12 → Factories |
| 812 | 21 | 81 → ? |
| 221 | 14 | 22 → Walls |
| 0 | 14 | 14 → Silos |
| 511 | 11 | 51 → Wonders |
| 231 | 8 | 23 → Fortresses |
| 1011 | 6 | 121 → Limited Edition |
| 71 | 6 | 7 → ? |
| 132 | 5 | 17 → Miscellaneous |
| 135 | 5 | 17 → Miscellaneous |
| 128 | 5 | 12 → Factories |
| 123 | 4 | 12 → Factories |
| 126 | 4 | 12 → Factories |
| 127 | 4 | 12 → Factories |
| 125 | 3 | 12 → Factories |
| 35 | 1 | 17 → Miscellaneous |
| 811 | 1 | 81 → ? |
| 911 | 1 | 91 → ? |
| 6 | 1 | 6 → ? |

The most common value `80` (228 items) is used with `subcategory_id = 7` (the unit category that is missing from
`config['categories']`), and `411` (171 items) is used with subcategory 45 “Others” and 42 “Flowers” — i.e. it is a
*functional* grouping (“generic decoration”) rather than a UI tab. **Its exact semantic is UNVERIFIED**: it is
never read by the AS3 (searched `scripts/` — no reference to `subcat_functional` outside `StaticData.as` parsing).
A re-implementation only needs it to reproduce the store filters.

### 2.4 `config['images']` (607 entries) → `assets/images/` and `assets/externalized/`

**Rule:** `assets/images/<lang>/<path>` where `lang` is the value in the map and `<path>` is the key with the
leading `/` stripped. All 607 entries map to `lang = 'en'`, so the effective rule is
`assets/images/en/<path>`.

| Metric | Count |
|---|---|
| `config['images']` entries | **607** |
| resolved to an existing file under `assets/images/` | **573** |
| **MISSING** from the tree | **34** |
| files under `assets/images/` **not** referenced by the config | **5** |

#### 2.4.1 The 34 missing images (all in `/chapters/` and `/intro/`)

```
/chapters/chapter_10_m.jpg   (lang=en)
/chapters/chapter_10_old.jpg   (lang=en)
/chapters/chapter_10_w.jpg   (lang=en)
/chapters/chapter_11_m.jpg   (lang=en)
/chapters/chapter_11_old.jpg   (lang=en)
/chapters/chapter_11_w.jpg   (lang=en)
/chapters/chapter_12_m.jpg   (lang=en)
/chapters/chapter_12_w.jpg   (lang=en)
/chapters/chapter_1_m.jpg   (lang=en)
/chapters/chapter_1_w.jpg   (lang=en)
/chapters/chapter_2_m.jpg   (lang=en)
/chapters/chapter_2_w.jpg   (lang=en)
/chapters/chapter_3_m.jpg   (lang=en)
/chapters/chapter_3_w.jpg   (lang=en)
/chapters/chapter_4_m.jpg   (lang=en)
/chapters/chapter_4_w.jpg   (lang=en)
/chapters/chapter_5_m.jpg   (lang=en)
/chapters/chapter_5_old.jpg   (lang=en)
/chapters/chapter_5_w.jpg   (lang=en)
/chapters/chapter_6_m.jpg   (lang=en)
/chapters/chapter_6_old.jpg   (lang=en)
/chapters/chapter_6_w.jpg   (lang=en)
/chapters/chapter_7_m.jpg   (lang=en)
/chapters/chapter_7_old.jpg   (lang=en)
/chapters/chapter_7_w.jpg   (lang=en)
/chapters/chapter_8_m.jpg   (lang=en)
/chapters/chapter_8_w.jpg   (lang=en)
/chapters/chapter_9_m.jpg   (lang=en)
/chapters/chapter_9_w.jpg   (lang=en)
/chapters/simple/arachnids_old.jpg   (lang=en)
/chapters/simple/orcs_old.jpg   (lang=en)
/chapters/simple/prison1.jpg   (lang=en)
/chapters/simple/prison2.jpg   (lang=en)
/intro/intro - copia.swf   (lang=en)
```

Pattern: for chapters 1–12 the config expects a triple `chapter_N.jpg` / `chapter_N_m.jpg` / `chapter_N_w.jpg`
(plus `_old` for 5, 6, 7, 9, 10, 11, 12) but the tree only ships the base `chapter_N.jpg` (12 files in
`images/en/chapters/` and 12 in `images/en/chapters2/`). The `_m`/`_w` variants are the male/female player-avatar
chapter illustrations. `/chapters/simple/` has only 3 files (`arachnids`, `orcs`, `prison*` absent) and
`/intro/intro - copia.swf` (a Spanish “copy” filename with spaces) is absent.

#### 2.4.2 The 5 unreferenced image files

| File | Note |
|---|---|
| `images/collectibles3.png` | hard-coded in `core/Config.as:240` (`SPRITE_INVENTORY_ITEMS = "collectibles3.png"`) — loaded by literal path, not via the config |
| `images/logo_DC.png` | Dragon City cross-promo logo |
| `images/logo_SE.png` | Social Empires cross-promo logo |
| `images/play_DC.jpg` | Dragon City cross-promo button |
| `images/play_SE.jpg` | Social Empires cross-promo button |

These 5 live at the **root** of `assets/images/` (i.e. *outside* the `en/` language folder), so they are not
reachable by the `images/<lang>/<path>` rule at all — they are fetched with a literal URL.

#### 2.4.3 `assets/externalized/` in the image mapping

**No `config['images']` entry resolves into `assets/externalized/`.** The `externalized/` tree is consumed through a
different mechanism (`AssetManager.EXTERNALIZED`), see §8.

### 2.5 `config['sounds']` (139 entries) → `assets/sounds/`

**Rule:** `assets/sounds/<file>.mp3` (exact; the `file` field has no extension).
`max` = maximum simultaneous instances of that sound, `loops` = how many times it repeats, `preload` = load it
at boot (`core/SoundFile.as:34-56`; `max` is copied to `sfxSimult`).

| Metric | Count |
|---|---|
| `config['sounds']` entries | **139** |
| distinct `file` values (one file is used by two ids) | **138** |
| resolved to an existing `assets/sounds/<file>.mp3` | **139 / 139 (100 %)** |
| **MISSING** | **0** |
| mp3 files in `assets/sounds/` not referenced by the config | **2** |

The 2 unreferenced mp3s are the **music beds**, loaded by literal path from
`managers/SoundManager.as:37`: `MUSIC = ["sounds/BACKGROUND.mp3","sounds/battle_1.mp3", …]`
(`MUSIC_MAP = 0`, `MUSIC_BATTLE = 1`, `MUSIC_SHIP = 2`, `MUSIC_ASSAULT = 3`, `MUSIC_QUEST = 4`).
Full id → file table in §6.

### 2.6 `config['magics']` (10 entries) → `assets/magic/`

**Rule:** `assets/magic/<img_name>.swf` (exact, `core/magic/MagicSpell.as:92`).
The same `img_name` is *also* used as a **JPEG** for the spell button: `GUI/SpellButton.as:29` loads
`images/<lang>/<img_name>.jpg` — so every magic needs **two** files: a `.swf` in `magic/` and a `.jpg` in
`images/en/`.

| id | name | `img_name` | `assets/magic/*.swf` | `assets/images/en/*.jpg` |
|---|---|---|---|---|
| 1 | AirStrike | `tech_airstrike` | **MISSING** | OK |
| 2 | Medic Case Rain | `tech_medic_case_rain` | **MISSING** | OK |
| 3 | Protection Shield | `tech_protection_shield` | **MISSING** | OK |
| 4 | Nuclear Bomb | `tech_nuclear_bomb` | **MISSING** | OK |
| 5 | Shortcircuit Inductor | `tech_frequency_inhibitor` | **MISSING** | OK |
| 6 | Magnetic Trap | `tech_iman` | **MISSING** | OK |
| 7 | Mech Summoner | `tech_robot_summoner` | **MISSING** | OK |
| 8 | Stealth Sneak | `tech_stealth_instinct` | **MISSING** | OK |
| 9 | Alien Abduction | `tech_mars_attack` | **MISSING** | OK |
| 10 | Attack Boost | `tech_attack_boost` | **MISSING** | OK |

**10 / 10 magics resolve in both places** (the `tech_*.jpg` icons are all present in `images/en/`, alongside
`prev_tech_*.jpg` “previous spell” variants and 16 older `magic_*.jpg` icons for the pre-tech spell system).

### 2.7 Bidirectional coverage summary

| Config collection | Entries | Resolved | Missing | Files in tree not referenced |
|---|---|---|---|---|
| `items[]` → `sprites/` | 778 | 768 | 10 | 122 / 862 |
| `items[]` → `thumbs/` | 778 | 749 | 29 | 593 / 1 314 |
| `images{}` → `images/` | 607 | 573 | 34 | 5 / 578 |
| `sounds[]` → `sounds/` | 139 | 139 | 0 | 2 / 140 |
| `magics[]` → `magic/` | 10 | 10 | 0 | 0 / 10 |
| `magics[]` → `images/en/` (button icon) | 10 | 10 | 0 | — |
| **Total config→asset references** | **2 322** | **2 249 (96.9 %)** | **73** | **722 asset files unreferenced** |

**The dominant cause of the 122 unreferenced sprites and the item ids the base config never heard of is version drift:** the asset
tree is from a **later** game version than the `config/main.json` snapshot. The config contains 778 items with
ids from 1 to 10090; the assets additionally contain **ids the base config has never heard of** - 199, 302
and the whole 1307–1431 “Mech / drone” wave (`glaivestorm`, `stampede`, `hellfire`, `splinter`, `anvilPattern`,
`bladestorm`, `spectre`, `stalker`, `slaughterer`, `crusherMonarch`, `vortex`, `bombardier`, `forgelord`,
`shredder`, `raven`, `cyclone`, `yamato`, `steelWanderer`, `tempest`, `servoworm`, `scarab`, `centaur`,
`evilSlaughterer`, `bismark`, `superfulcrum`, `bonecrusha`, `bushwacker`, `brawler`, `havoc`, `hammerhead`,
`templarExosuit`, `marauderBattleChasis`, `atomicBonecrusha`, `reaper`, `blackHole`, `ignition`, `harvester`,
`agamemnonFortress`, `typhoonServoDragon`, `guardian`, `knightExosuit`, `fireGamera`, `cycloneBattlesuit`,
`chemicalGunner`, `blueAnvil`, `overseer`, `urbanBuster`, `skorpionFortress`, `pauldronMech`, `sharkbite`,
`crimsonCenturion`, `warlord`, `cyberInquisitor`, `knuckledragger`, `steelGladiator`, `tarantula`, `intruder`).
The AS3 in `as_basesec` *does* contain delegates for them (`EvilSlaughtererDelegate`, `HavocDelegate`,
`ReaperDelegate`, `SuperfulcrumArmorDelegate`, `SkorpionFortressDelegate`, `TempestMechDelegate`,
`AgamemnonFortressDelegate`, …), so the **client is newer than the config**.

---

## 3. The `assets/thumbs/` scheme

### 3.1 Layout

`assets/thumbs/` = **1 314 files, 32 583 246 bytes (31.07 MB)**, all `.jpg`, all flat (no sub-directories).

| Family | Count | Naming rule | Purpose |
|---|---|---|---|
| Item icon / misc | 847 | `<item_id>_<name>[_<variant>].jpg` | the inventory / store / army-cell icon of a unit or building — **19 of these 847 have no numeric id at all** (e.g. `BOTON1_NINJA.jpg`, `boton_pinzas.jpg`, `black_dragon_Boton01.jpg` …) |
| Special-attack button (modern) | 208 | `<item_id>_<name>_button<n>.jpg` or `…_button_<n>.jpg` | button of a post-config unit's special attack |
| Special-attack button (`_special_`) | 94 | `<item_id>_special_<n>.jpg` | older special-attack button naming |
| Special-attack button (`btn_` family) | 67 | `btn_<item_id>_<ability>.jpg` | **the family actually used by the AS3** |
| Numbered variant | 86 | `<item_id>_<name>_<n>.jpg` | resource tiers, ports, numbered props |
| Dragon special buttons | 12 | `<name>_Boton<nn>.jpg` (no id) | black / electric / metal dragon special attacks |

> These six buckets are mutually exclusive (the classifier checks `btn_` → `_button<n>` → `_special_<n>` →
> `_Boton<n>` → `_<n>` → plain) and sum to exactly **1 314** — the whole directory.

### 3.2 The `btn_<id>_<ability>` family in detail

This is the one the client actually consumes. In `core/SpecialUnitAttack.as` the 6th constructor argument is
the button image name, exposed as `imgThumb` (`core/SpecialUnitAttack.as:105`) and loaded by
`GUI/PortraitSpecialAttack.as:255` → `thumbs/<imgThumb>.jpg`.

Example (`core/isoengine/delegates/units/DreadnoughtDelegate.as:56-57`):

```actionscript
this.arAttacks[0] = new SpecialUnitAttack(0,-1,0,20,Language.getLiteral("Rocket blast"),"btn_1084_rocket", …);
this.arAttacks[1] = new SpecialUnitAttack(1,-1,0,10,Language.getLiteral("Gatling rage"),"btn_1084_gatling", …);
```

**All 67 `btn_*` files on disk are referenced by the AS3, and exactly one referenced button is missing:**
`btn_1180_hiper` (Robot Hunter, 1180). Full mapping in §5.5 / the table below.

| `btn_*` thumbnail | owning unit(s) |
|---|---|
| `btn_1075_laser.jpg` | Supreme Bot |
| `btn_1075_misil.jpg` | Supreme Bot, Red Baron |
| `btn_1084_gatling.jpg` | Dreadnought |
| `btn_1084_rocket.jpg` | Dreadnought |
| `btn_1105_callDraggy.jpg` | Metal Draggy, Metal Dragon |
| `btn_1105_metallicBalls.jpg` | Metal Draggy, Metal Dragon |
| `btn_1105_metallicBomb.jpg` | Metal Draggy, Metal Dragon |
| `btn_1105_metallicTornado.jpg` | Metal Draggy, Metal Dragon |
| `btn_1123_blade.jpg` | Armored Core Alpha, Alpha Drone |
| `btn_1123_drone.jpg` | Armored Core Alpha, Alpha Drone |
| `btn_1123_plasma.jpg` | Armored Core Alpha, Alpha Drone |
| `btn_1123_whirlwind.jpg` | Armored Core Alpha, Alpha Drone |
| `btn_1150_hammer.jpg` | Crusader Bot |
| `btn_1150_lightning.jpg` | Crusader Bot |
| `btn_1150_spin.jpg` | Crusader Bot |
| `btn_1150_stomp.jpg` | Crusader Bot |
| `btn_1151_convert.jpg` | Crusader Priest |
| `btn_1152_blinding_laser.jpg` | Viking Core Bot, Viking Core Bot Drone |
| `btn_1152_circle_shooting.jpg` | Roller Skater |
| `btn_1152_deadly_turn.jpg` | Ultra-Mech, Ultra-Mech Drone |
| `btn_1152_huge_laser.jpg` | Ultra-Mech, Ultra-Mech Drone |
| `btn_1152_missile_launch.jpg` | Ultra-Mech, Ultra-Mech Drone |
| `btn_1152_summon_drone.jpg` | Viking Core Bot, Viking Core Bot Drone |
| `btn_1152_summon_drone_2.jpg` | Ultra-Mech, Ultra-Mech Drone |
| `btn_1152_whirlwind.jpg` | Roller Skater |
| `btn_1160_mace_wheel.jpg` | Viking Core Bot, Viking Core Bot Drone |
| `btn_1160_multi_missile.jpg` | Viking Core Bot, Viking Core Bot Drone |
| `btn_1169_big_shot.jpg` | Roller Skater |
| `btn_1169_spinning_attack.jpg` | Roller Skater |
| `btn_1174_big_shot.jpg` | Viking Sniper |
| `btn_1174_hide.jpg` | Viking Sniper |
| `btn_1180_blast.jpg` | Robot Hunter |
| `btn_1180_hiper.jpg` | Robot Hunter |
| `btn_1180_shield.jpg` | Robot Hunter |
| `btn_1180_wheel.jpg` | Robot Hunter |
| `btn_1220_special1.jpg` | Nebular Sniper |
| `btn_1220_special2.jpg` | Nebular Sniper |
| `btn_1236_laser.jpg` | 2-Gun Exobot |
| `btn_1236_whirlwind.jpg` | 2-Gun Exobot |
| `btn_1237_blades.jpg` | Cyber Samurai Mech, Cyber Samurai  Drone |
| `btn_1237_drone.jpg` | Cyber Samurai Mech, Cyber Samurai  Drone |
| `btn_1237_missiles.jpg` | Cyber Samurai Mech, Cyber Samurai  Drone |
| `btn_1237_scissors.jpg` | Cyber Samurai Mech, Cyber Samurai  Drone |
| `btn_bolas_dragon.jpg` | Red Draggy, Blue Draggy, Red Dragon, Blue Dragon |
| `btn_celestial_mega_mech.jpg` | Celestial Megamech |
| `btn_drone_1161.jpg` | Rune Golem, Rune Golem Drone |
| `btn_drone_dualcannon.jpg` | Massive Cannon Drone, Double Cannon Mech, Double Cannon Drone |
| `btn_garrote_orco.jpg` | Xplosive Ork, Xplosive Beast Boss, Xplosive Beast |
| `btn_laser_dragon.jpg` | Red Draggy, Blue Draggy, Red Dragon, Blue Dragon |
| `btn_laser_punisher.jpg` | Punisher Bot |
| `btn_liquid_mech_acid_balls.jpg` | Liquid Mech , Liquid Mech  Drone |
| `btn_liquid_mech_acid_rain.jpg` | Liquid Mech , Liquid Mech  Drone |
| `btn_liquid_mech_clone.jpg` | Liquid Mech , Liquid Mech  Drone |
| `btn_liquid_mech_drone.jpg` | Liquid Mech , Liquid Mech  Drone |
| `btn_megalaser_1161.jpg` | Rune Golem, Rune Golem Drone |
| `btn_misil_punisher.jpg` | Punisher Bot |
| `btn_misile_storm.jpg` | Big Handsaw Ork, Red Handsaw Ork |
| `btn_optimus.jpg` | Red Spinner |
| `btn_saw_attack.jpg` | Big Handsaw Ork, Red Handsaw Ork |
| `btn_smash_1161.jpg` | Rune Golem, Rune Golem Drone |
| `btn_special_ops_hide.jpg` | Special Ops. |
| `btn_special_ops_show.jpg` | Special Ops. |
| `btn_special_ops_slash_throat.jpg` | Special Ops. |
| `btn_special_rambo_grenade.jpg` | Ranbo |
| `btn_special_rambo_slash.jpg` | Ranbo |
| `btn_special_terminator_bazooka.jpg` | Erradicator |
| `btn_special_terminator_flamethrower.jpg` | Erradicator |
| `btn_ultrapunch_1161.jpg` | Rune Golem, Rune Golem Drone |

### 3.3 Item-icon mapping (sample)

| item id | name | `img_name` | thumbnail file |
|---|---|---|---|
| 1 | House I | `0001_house_1_m` | 0001_house_1_m.jpg |
| 2 | Wood Factory I | `0002_depot_wood_1_m` | 0002_depot_wood_1_m.jpg |
| 22 | Turret I | `0022_tower_1_m` | 0022_tower_1_m.jpg |
| 23 | Wall I | `0023_wall_1_m` | 0023_wall_1_m.jpg |
| 50 | Bunker I | `0050_bunker_1_m` | 0050_bunker_1_m.jpg |
| 80 | Fortress I | `0080_fortress_1_m` | 0080_fortress_1_m.jpg |
| 86 | Robotic Center | `0086_robotics_center` | 0086_robotics_center.jpg |
| 122 | Heliport | `0122_helipuerto_m` | 0122_helipuerto_m.jpg |
| 1001 | Worker I | `1001_worker_m,1001_worker_w` | 1001_worker_m.jpg;1001_worker_w.jpg |
| 1007 | Soldier | `1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_w` | 1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_w.jpg |
| 1008 | Bazooka | `1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_w` | 1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_w.jpg |
| 1014 | Machine Gun Jeep | `1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_w` | 1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_w.jpg |
| 1034 | UN Allied | `1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_w` | 1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_w.jpg |
| 1075 | Supreme Bot | `1075_supreme_m` | 1075_supreme_m.jpg |
| 1084 | Dreadnought | `1084_dreadnought_m` | 1084_dreadnought_m.jpg |
| 1123 | Orc Swordsman | `1123_orc_basic_knife_2` | 1123_orc_basic_knife_2.jpg |
| 1150 | Crusader Bot | `1150_crusader_bot` | 1150_crusader_bot.jpg |
| 1151 | Crusader Priest | `1151_crusader_priest` | 1151_crusader_priest.jpg |
| 1161 | Rune Golem | `1161_viking_rune_golem` | **MISSING** |
| 1180 | Robot Hunter | `1180_robot_hunter` | 1180_robot_hunter.jpg |
| 1220 | Nebular Sniper | `1220_nebular_sniper` | 1220_nebular_sniper.jpg |
| 1237 | Cyber Samurai Mech | `1237_cyber_samurai_mech` | 1237_cyber_samurai_mech.jpg |
| 1240 | Dark Ether Messiah Drone | `1240_dark_ether_messiah_drone` | 1240_dark_ether_messiah_drone.jpg |
| 10000 | Chained Bonus + Giant Walker | `10000_chained_bonus_giant_walker` | **MISSING** |
| 10034 | Chained Hercules Mech | `10034_chained_hercules_mech` | **MISSING** |
| 10048 | Play Dragon City | `10048_cross_dc` | **MISSING** |
| 127 | Enemy's harbour | `0127_enemy_harbour_m` | **MISSING** |
| 137 | Spy Academy | `0137_spy_academy_m` | **MISSING** |
| 925 | Expandable Land | `terreno` | **MISSING** |

### 3.4 How a re-implementation should use the thumbs

`utils/ThumbManager.as` is the reference implementation:

* it allocates a fixed **90 × 90 px** transparent `BitmapData` per key (`THUMB_WIDTH`/`THUMB_HEIGHT = 90`),
  requests `thumbs/<key>.jpg`, and **draws the loaded bitmap into the pre-allocated canvas**
  (`ThumbManager.as:58-60` and `:72-80`) — the thumbnails are therefore *not* necessarily 90×90 on disk, they are
  **scaled/cropped into** a 90×90 square by the runtime;
* it memoises by key, so a 90×90 `BitmapData` costs a fixed ~31.65 KB of accounted memory per entry
  (`THUMB_MEMORY_USED`);
* call sites that want a *live* animation instead of a static icon use the sprite instead:
  `InventoryCollection.as:67` → `new AnimatedUnit(imageBox, item.img_name[0], 50, item.type == Constants.TYPE_UNIT)`
  and `GUI/RecuadroInfo.as:943,968,1221` → `ThumbManager.instance.getThumb(item.img_name[0])`.

**Practical guidance for a web/GL client:**

1. Use `thumbs/<img_name>.jpg` verbatim as the inventory / store / army-cell icon. No conversion needed — JPEG is
   already a web-native format. 31 MB for 1 314 icons is acceptable, and they can be lazily fetched.
2. Use `thumbs/btn_<id>_<ability>.jpg` for the special-attack buttons. 67 files, tiny.
3. Where the original shows an *animated* unit (army cell, tooltip, inventory), the original uses the **sprite**,
   not the thumb — so a modern client needs both paths: static thumb for grids, animated sprite for detail views.
4. The 90 × 90 square is the de-facto icon contract; reproduce it (object-fit: cover / contain as appropriate).
5. Treat the 593 thumbs with no config `img_name` as **post-config content**: they are the icons for the 1307–1431
   unit wave and for special attacks of older units. They are usable immediately (the file names are stable),
   but they are not reachable through `config['items']`.

---

## 4. Per-item table — all 778 `config['items']`

Machine-readable version: `reports/items-assets.csv` (same content, 778 data rows).
A fenced copy of the CSV is appended at the very end of this report as **Appendix A**.

Columns: `id`, `name`, `type` (`b`=building, `u`=unit, `l`=land), `category_id`, `subcategory_id`,
`subcat_functional`, `img_name` (raw config value, comma-separated variants), `sprite_files`,
`thumb_files`, `sprite_ok`, `thumb_ok`.

### 4.1 Summary by type and category

| type | items | with sprite | with thumb |
|---|---|---|---|
| b | 469 | 460 | 444 |
| l | 1 | 1 | 0 |
| u | 308 | 307 | 305 |

### 4.2 The complete table

| id | name | type | cat | sub | func | `img_name` | sprite file | thumb file |
|---|---|---|---|---|---|---|---|---|
| 1 | House I | b | 1 | 11 | 111 | `0001_house_1_m` | 0001_house_1_m.swf | 0001_house_1_m.jpg |
| 2 | Wood Factory I | b | 1 | 12 | 129 | `0002_depot_wood_1_m` | 0002_depot_wood_1_m.swf | 0002_depot_wood_1_m.jpg |
| 3 | Oil Factory I | b | 1 | 12 | 129 | `0003_depot_oil_1_m` | 0003_depot_oil_1_m.swf | 0003_depot_oil_1_m.jpg |
| 4 | Steel Factory I | b | 1 | 12 | 129 | `0004_depot_steel_1_m` | 0004_depot_steel_1_m.swf | 0004_depot_steel_1_m.jpg |
| 5 | Gold Factory I | b | 1 | 12 | 129 | `0005_depot_gold_1_m` | 0005_depot_gold_1_m.swf | 0005_depot_gold_1_m.jpg |
| 6 | Wood Factory II | b | 1 | 12 | 129 | `0006_depot_wood_2_m` | 0006_depot_wood_2_m.swf | 0006_depot_wood_2_m.jpg |
| 7 | Oil Factory II | b | 1 | 12 | 129 | `0007_depot_oil_2_m` | 0007_depot_oil_2_m.swf | 0007_depot_oil_2_m.jpg |
| 8 | Steel Factory II | b | 1 | 12 | 129 | `0008_depot_steel_2_m` | 0008_depot_steel_2_m.swf | 0008_depot_steel_2_m.jpg |
| 9 | Gold Factory II | b | 1 | 12 | 129 | `0009_depot_gold_2_m` | 0009_depot_gold_2_m.swf | 0009_depot_gold_2_m.jpg |
| 10 | Wood Factory III | b | 1 | 12 | 129 | `0010_depot_wood_3_m` | 0010_depot_wood_3_m.swf | 0010_depot_wood_3_m.jpg |
| 11 | Oil Factory III | b | 1 | 12 | 129 | `0011_depot_oil_3_m` | 0011_depot_oil_3_m.swf | 0011_depot_oil_3_m.jpg |
| 12 | Steel Factory III | b | 1 | 12 | 129 | `0012_depot_steel_3_m` | 0012_depot_steel_3_m.swf | 0012_depot_steel_3_m.jpg |
| 13 | Gold Factory III | b | 1 | 12 | 129 | `0013_depot_gold_3_m` | 0013_depot_gold_3_m.swf | 0013_depot_gold_3_m.jpg |
| 14 | Wood Factory IV | b | 1 | 12 | 129 | `0014_depot_wood_4_m` | 0014_depot_wood_4_m.swf | 0014_depot_wood_4_m.jpg |
| 15 | Oil Factory IV | b | 1 | 12 | 129 | `0015_depot_oil_4_m` | 0015_depot_oil_4_m.swf | 0015_depot_oil_4_m.jpg |
| 16 | Steel Factory IV | b | 1 | 12 | 129 | `0016_depot_steel_4_m` | 0016_depot_steel_4_m.swf | 0016_depot_steel_4_m.jpg |
| 17 | Gold Factory IV | b | 1 | 12 | 129 | `0017_depot_gold_4_m` | 0017_depot_gold_4_m.swf | 0017_depot_gold_4_m.jpg |
| 18 | Market I | b | 1 | 17 | 132 | `0018_market_1_m` | 0018_market_1_m.swf | 0018_market_1_m.jpg |
| 19 | Prison | b | 8 | 81 | 812 | `0019_prision_m` | 0019_prision_m.swf | 0019_prision_m.jpg |
| 22 | Turret I | b | 2 | 21 | 211 | `0022_tower_1_m` | 0022_tower_1_m.swf | 0022_tower_1_m.jpg |
| 23 | Wall I | b | 2 | 22 | 221 | `0023_wall_1_m` | 0023_wall_1_m.swf | 0023_wall_1_m.jpg |
| 24 | Wall II | b | 2 | 22 | 221 | `0024_wall_2_m` | 0024_wall_2_m.swf | 0024_wall_2_m.jpg |
| 25 | Wall III | b | 2 | 22 | 221 | `0025_wall_3_m` | 0025_wall_3_m.swf | 0025_wall_3_m.jpg |
| 26 | Command Center | b | 1 | 17 | 135 | `0026_command_center_1_m` | 0026_command_center_1_m.swf | 0026_command_center_1_m.jpg |
| 28 | Hospital | b | 1 | 17 | 35 | `0028_hospital_1_m` | 0028_hospital_1_m.swf | 0028_hospital_1_m.jpg |
| 30 | Academy I | b | 3 | 31 | 111 | `0030_academy_1_m` | 0030_academy_1_m.swf | 0030_academy_1_m.jpg |
| 31 | Bazooka Academy I | b | 3 | 31 | 111 | `0031_bazooka_academy_1_m` | 0031_bazooka_academy_1_m.swf | 0031_bazooka_academy_1_m.jpg |
| 37 | Hangar I | b | 3 | 33 | 111 | `0037_hangar_1_m` | 0037_hangar_1_m.swf | 0037_hangar_1_m.jpg |
| 38 | Tank Academy I | b | 3 | 32 | 111 | `0038_cannon_academy_1_m` | 0038_cannon_academy_1_m.swf | 0038_cannon_academy_1_m.jpg |
| 39 | Turret IV | b | 2 | 21 | 211 | `0039_tower_2_m` | 0039_tower_2_m.swf | 0039_tower_2_m.jpg |
| 40 | Jeep garage I | b | 3 | 32 | 111 | `0040_workshop_1_m` | 0040_workshop_1_m.swf | 0040_workshop_1_m.jpg |
| 41 | Academy II | b | 3 | 31 | 111 | `0041_academy_2_m` | 0041_academy_2_m.swf | 0041_academy_2_m.jpg |
| 42 | Academy III | b | 3 | 31 | 111 | `0042_academy_3_m` | 0042_academy_3_m.swf | 0042_academy_3_m.jpg |
| 43 | Bazooka Academy II | b | 3 | 31 | 111 | `0043_bazooka_academy_2_m` | 0043_bazooka_academy_2_m.swf | 0043_bazooka_academy_2_m.jpg |
| 44 | Bazooka Academy III | b | 3 | 31 | 111 | `0044_bazooka_academy_3_m` | 0044_bazooka_academy_3_m.swf | 0044_bazooka_academy_3_m.jpg |
| 45 | Dual-Rocket Turret | b | 2 | 21 | 211 | `0045_tower_3_m` | 0045_tower_3_m.swf | 0045_tower_3_m.jpg |
| 46 | Cannon Turret | b | 2 | 21 | 211 | `0046_tower_4_m` | 0046_tower_4_m.swf | 0046_tower_4_m.jpg |
| 47 | House II | b | 1 | 11 | 111 | `0047_house_2_m` | 0047_house_2_m.swf | 0047_house_2_m.jpg |
| 48 | House III | b | 1 | 11 | 111 | `0048_house_3_m` | 0048_house_3_m.swf | 0048_house_3_m.jpg |
| 49 | Turret III | b | 2 | 21 | 211 | `0049_torreta_horacio_m` | 0049_torreta_horacio_m.swf | 0049_torreta_horacio_m.jpg |
| 50 | Bunker I | b | 2 | 24 | 211 | `0050_bunker_1_m` | 0050_bunker_1_m.swf | 0050_bunker_1_m.jpg |
| 51 | Bunker II | b | 2 | 24 | 211 | `0051_bunker_2_m` | 0051_bunker_2_m.swf | 0051_bunker_2_m.jpg |
| 52 | Bunker III | b | 2 | 24 | 211 | `0052_bunker_3_m` | 0052_bunker_3_m.swf | 0052_bunker_3_m.jpg |
| 53 | Mega Bunker | b | 2 | 24 | 211 | `0053_bunker_4_m` | 0053_bunker_4_m.swf | 0053_bunker_4_m.jpg |
| 54 | Helicopter Hangar I | b | 3 | 33 | 111 | `0054_copter_hangar_1_m` | 0054_copter_hangar_1_m.swf | 0054_copter_hangar_1_m.jpg |
| 55 | Helicopter Hangar II | b | 3 | 33 | 111 | `0055_copter_hangar_2_m` | 0055_copter_hangar_2_m.swf | 0055_copter_hangar_2_m.jpg |
| 56 | Helicopter Hangar III | b | 3 | 33 | 111 | `0056_copter_hangar_3_m` | 0056_copter_hangar_3_m.swf | 0056_copter_hangar_3_m.jpg |
| 57 | Turret II | b | 2 | 21 | 211 | `0057_torreta_ruben_m` | 0057_torreta_ruben_m.swf | 0057_torreta_ruben_m.jpg |
| 58 | Command Center II | b | 1 | 17 | 135 | `0058_command_center_2_m` | 0058_command_center_2_m.swf | 0058_command_center_2_m.jpg |
| 59 | Command Center III | b | 1 | 17 | 135 | `0059_command_center_3_m` | 0059_command_center_3_m.swf | 0059_command_center_3_m.jpg |
| 60 | Command Center IV | b | 1 | 17 | 135 | `0060_command_center_4_m` | 0060_command_center_4_m.swf | 0060_command_center_4_m.jpg |
| 61 | Allies Building | b | 1 | 17 | 111 | `0061_allies_building_m` | 0061_allies_building_m.swf | 0061_allies_building_m.jpg |
| 62 | Tank Academy II | b | 3 | 32 | 111 | `0062_cannon_academy_2_m` | 0062_cannon_academy_2_m.swf | 0062_cannon_academy_2_m.jpg |
| 63 | Tank Academy III | b | 3 | 32 | 111 | `0063_cannon_academy_3_m` | 0063_cannon_academy_3_m.swf | 0063_cannon_academy_3_m.jpg |
| 64 | Jeep garage II | b | 3 | 32 | 111 | `0064_workshop_2_m` | 0064_workshop_2_m.swf | 0064_workshop_2_m.jpg |
| 65 | Jeep garage III | b | 3 | 32 | 111 | `0065_workshop_3_m` | 0065_workshop_3_m.swf | 0065_workshop_3_m.jpg |
| 66 | Stoneage | b | 5 | 51 | 511 | `0066_stoneage_marvel_m` | 0066_stoneage_marvel_m.swf | 0066_stoneage_marvel_m.jpg |
| 67 | Machu Picchu | b | 5 | 51 | 511 | `0067_machupichu_m` | 0067_machupichu_m.swf | 0067_machupichu_m.jpg |
| 68 | Iguazu | b | 5 | 51 | 511 | `0068_iguazu_m` | 0068_iguazu_m.swf | 0068_iguazu_m.jpg |
| 69 | Sphynx | b | 5 | 51 | 511 | `0069_sfinx_m` | 0069_sfinx_m.swf | 0069_sfinx_m.jpg |
| 70 | Inca God | b | 5 | 51 | 511 | `0070_inca_god_m` | 0070_inca_god_m.swf | 0070_inca_god_m.jpg |
| 71 | Chichenitza | b | 5 | 51 | 511 | `0071_chichenitza_m` | 0071_chichenitza_m.swf | 0071_chichenitza_m.jpg |
| 72 | Babilonia | b | 5 | 51 | 511 | `0072_babilonia_m` | 0072_babilonia_m.swf | 0072_babilonia_m.jpg |
| 73 | Ankor | b | 5 | 51 | 511 | `0073_Ankor_m` | 0073_Ankor_m.swf | 0073_Ankor_m.jpg |
| 74 | Allies Market | b | 1 | 17 | 132 | `0074_Allies_market_m` | 0074_Allies_market_m.swf | 0074_Allies_market_m.jpg |
| 75 | Recon center | b | 1 | 17 | 132 | `0075_Spy_center_m` | 0075_Spy_center_m.swf | 0075_Spy_center_m.jpg |
| 76 | Hangar II | b | 3 | 33 | 111 | `0076_hangar_2_m` | 0076_hangar_2_m.swf | 0076_hangar_2_m.jpg |
| 77 | Hangar III | b | 3 | 33 | 111 | `0077_hangar_3_m` | 0077_hangar_3_m.swf | 0077_hangar_3_m.jpg |
| 78 | Wall IV | b | 2 | 22 | 221 | `0078_wall_4_m` | 0078_wall_4_m.swf | 0078_wall_4_m.jpg |
| 79 | Wall V | b | 2 | 22 | 221 | `0079_wall_5_m` | 0079_wall_5_m.swf | 0079_wall_5_m.jpg |
| 80 | Fortress I | b | 2 | 23 | 231 | `0080_fortress_1_m` | 0080_fortress_1_m.swf | 0080_fortress_1_m.jpg |
| 81 | Fortress II | b | 2 | 23 | 231 | `0081_fortress_2_m` | 0081_fortress_2_m.swf | 0081_fortress_2_m.jpg |
| 82 | Rocket Fortress | b | 2 | 23 | 231 | `0082_fortress_3_m` | 0082_fortress_3_m.swf | 0082_fortress_3_m.jpg |
| 83 | Fortress III | b | 2 | 23 | 231 | `0083_fortress_4_m` | 0083_fortress_4_m.swf | 0083_fortress_4_m.jpg |
| 84 | Special Fortress | b | 2 | 23 | 231 | `0084_fortress_5_m` | 0084_fortress_5_m.swf | 0084_fortress_5_m.jpg |
| 85 | Mega Fortress | b | 2 | 23 | 231 | `0085_fortress_6_m` | 0085_fortress_6_m.swf | 0085_fortress_6_m.jpg |
| 86 | Robotic Center | b | 1 | 17 | 111 | `0086_robotics_center` | 0086_robotics_center.swf | 0086_robotics_center.jpg |
| 87 | Turret VI | b | 2 | 21 | 211 | `0087_tower_7_m` | 0087_tower_7_m.swf | 0087_tower_7_m.jpg |
| 88 | Turret V | b | 2 | 21 | 211 | `0088_tower_8_m` | 0088_tower_8_m.swf | 0088_tower_8_m.jpg |
| 89 | Nuclear Plant | b | 1 | 11 | 111 | `0089_nuclear_plant_m` | 0089_nuclear_plant_m.swf | 0089_nuclear_plant_m.jpg |
| 90 | Market II | b | 1 | 17 | 132 | `0090_market_2_m` | 0090_market_2_m.swf | 0090_market_2_m.jpg |
| 91 | Market III | b | 1 | 17 | 132 | `0091_market_3_m` | 0091_market_3_m.swf | 0091_market_3_m.jpg |
| 92 | Apple tree | b | 4 | 41 | 411 | `0092_apple_tree_m` | 0092_apple_tree_m.swf | 0092_apple_tree_m.jpg |
| 93 | Pear tree | b | 4 | 41 | 411 | `0093_pear_tree_m` | 0093_pear_tree_m.swf | 0093_pear_tree_m.jpg |
| 94 | Sponge bush | b | 4 | 42 | 411 | `0094_sponge_bush_m` | 0094_sponge_bush_m.swf | 0094_sponge_bush_m.jpg |
| 95 | Little fountain | b | 4 | 45 | 411 | `0095_little_fountain_m` | 0095_little_fountain_m.swf | 0095_little_fountain_m.jpg |
| 96 | White Flowers | b | 4 | 42 | 411 | `0096_white_flowers_m` | 0096_white_flowers_m.swf | 0096_white_flowers_m.jpg |
| 97 | Red flowers | b | 4 | 42 | 411 | `0097_red_flowers_m` | 0097_red_flowers_m.swf | 0097_red_flowers_m.jpg |
| 98 | Blue flowers | b | 4 | 42 | 411 | `0098_blue_flowers_m` | 0098_blue_flowers_m.swf | 0098_blue_flowers_m.jpg |
| 100 | Red Leaf flowers | b | 4 | 42 | 411 | `0100_red_leaf_flowers_m` | 0100_red_leaf_flowers_m.swf | 0100_red_leaf_flowers_m.jpg |
| 101 | Pink Leaf flowers | b | 4 | 42 | 411 | `0101_pink_leaf_flowers_m` | 0101_pink_leaf_flowers_m.swf | 0101_pink_leaf_flowers_m.jpg |
| 102 | Blue Leaf flowers | b | 4 | 42 | 411 | `0102_blue_leaf_flowers_m` | 0102_blue_leaf_flowers_m.swf | 0102_blue_leaf_flowers_m.jpg |
| 103 | Bush | b | 4 | 42 | 411 | `0103_bush_m` | 0103_bush_m.swf | 0103_bush_m.jpg |
| 104 | Lamp | b | 4 | 45 | 411 | `0104_bancos_farolas_m` | 0104_bancos_farolas_m.swf | 0104_bancos_farolas_m.jpg |
| 105 | Victory Arch | b | 4 | 45 | 411 | `0105_victory_arch_m` | 0105_victory_arch_m.swf | 0105_victory_arch_m.jpg |
| 106 | Fountain | b | 4 | 45 | 411 | `0106_fountain_m` | 0106_fountain_m.swf | 0106_fountain_m.jpg |
| 107 | Sculpture | b | 4 | 44 | 411 | `0107_sculpture_m` | 0107_sculpture_m.swf | 0107_sculpture_m.jpg |
| 108 | Grape field | b | 1 | 13 | 129 | `0108_grape_field_m` | 0108_grape_field_m.swf | 0108_grape_field_m.jpg |
| 109 | Corn field | b | 1 | 13 | 129 | `0109_corn_field_m` | 0109_corn_field_m.swf | 0109_corn_field_m.jpg |
| 110 | Cow farm | b | 1 | 13 | 129 | `0110_cow_farm_m` | 0110_cow_farm_m.swf | 0110_cow_farm_m.jpg |
| 111 | Max Security Prison | b | 8 | 81 | 812 | `0111_prisoner_guile_m` | 0111_prisoner_guile_m.swf | 0111_prisoner_guile_m.jpg |
| 112 | Stolen Bazookas | b | 8 | 81 | 812 | `0112_stolen_bazookas_m` | 0112_stolen_bazookas_m.swf | 0112_stolen_bazookas_m.jpg |
| 113 | Disabled Jeeps | b | 8 | 81 | 812 | `0113_disabled_jeeps_m` | 0113_disabled_jeeps_m.swf | 0113_disabled_jeeps_m.jpg |
| 114 | Jeep wheels | b | 8 | 81 | 812 | `0114_jeep_weels_m` | 0114_jeep_weels_m.swf | 0114_jeep_weels_m.jpg |
| 115 | Supertank ammo | b | 8 | 81 | 812 | `0115_supertank_ammo_1_m` | 0115_supertank_ammo_1_m.swf | 0115_supertank_ammo_1_m.jpg |
| 116 | Supertank ammo | b | 8 | 81 | 812 | `0116_supertank_ammo_2_m` | 0116_supertank_ammo_2_m.swf | 0116_supertank_ammo_2_m.jpg |
| 117 | Disabled Supertank | b | 8 | 81 | 812 | `0117_disabled_supertank_m` | 0117_disabled_supertank_m.swf | 0117_disabled_supertank_m.jpg |
| 118 | Mind Control Laboratory | b | 2 | 23 | 231 | `0118_laboratory_m` | 0118_laboratory_m.swf | 0118_laboratory_m.jpg |
| 119 | Tank wheels | b | 8 | 81 | 812 | `0119_tank_wheels_m` | 0119_tank_wheels_m.swf | 0119_tank_wheels_m.jpg |
| 120 | Stolen missiles | b | 8 | 81 | 812 | `0120_stolen_missiles_m` | 0120_stolen_missiles_m.swf | 0120_stolen_missiles_m.jpg |
| 121 | Radio | b | 8 | 81 | 812 | `0121_radio_m` | 0121_radio_m.swf | 0121_radio_m.jpg |
| 122 | Heliport | b | 8 | 81 | 812 | `0122_helipuerto_m` | 0122_helipuerto_m.swf | 0122_helipuerto_m.jpg |
| 123 | Red Fortress | b | 8 | 81 | 812 | `0123_red_fortress_m` | 0123_red_fortress_m.swf | 0123_red_fortress_m.jpg |
| 124 | Disabled Tanks | b | 8 | 81 | 812 | `0124_disabled_tanks_m` | 0124_disabled_tanks_m.swf | 0124_disabled_tanks_m.jpg |
| 125 | Laboratory | b | 8 | 81 | 812 | `0125_laboratory_m` | 0125_laboratory_m.swf | 0125_laboratory_m.jpg |
| 126 | Enemy's airport | b | 8 | 81 | 812 | `0126_enemy_airport_m` | 0126_enemy_airport_m.swf | 0126_enemy_airport_m.jpg |
| 127 | Enemy's harbour | b | 8 | 81 | 812 | `0127_enemy_harbour_m` | 0127_enemy_harbour_m.swf | **— MISSING —** |
| 128 | Rocket launcher | b | 8 | 81 | 812 | `0128_rocket_launcher_m` | 0128_rocket_launcher_m.swf | 0128_rocket_launcher_m.jpg |
| 129 | Flamethrower Academy | b | 3 | 34 | 111 | `0129_fire_academy_m` | 0129_fire_academy_m.swf | 0129_fire_academy_m.jpg |
| 130 | Dominion Tank Academy | b | 3 | 34 | 111 | `0130_black_tank_academy_m` | 0130_black_tank_academy_m.swf | 0130_black_tank_academy_m.jpg |
| 131 | Stealth Fighter Hangar | b | 3 | 34 | 111 | `0131_black_aircraft_academy_m` | 0131_black_aircraft_academy_m.swf | 0131_black_aircraft_academy_m.jpg |
| 132 | Troubled Traveller | b | 4 | 45 | 411 | `0132_troubled_traveller_m` | 0132_troubled_traveller_m.swf | **— MISSING —** |
| 133 | Injured Soldier | b | 4 | 45 | 411 | `0133_injured_soldier_m` | 0133_injured_soldier_m.swf | **— MISSING —** |
| 134 | Field Hospital | b | 3 | 34 | 111 | `0134_field_hospital_m` | 0134_field_hospital_m.swf | 0134_field_hospital_m.jpg |
| 135 | Mechanical Garage | b | 3 | 34 | 111 | `0135_engineer_barrack_m` | 0135_engineer_barrack_m.swf | 0135_engineer_barrack_m.jpg |
| 136 | General Sculpture | b | 4 | 42 | 411 | `0136_general_sculpture_m` | 0136_general_sculpture_m.swf | 0136_general_sculpture_m.jpg |
| 137 | Spy Academy | b | 3 | 34 | 111 | `0137_spy_academy_m` | **— MISSING —** | **— MISSING —** |
| 138 | Mr T. Academy | b | 12 | 121 | 111 | `0138_mr_t_academy_m` | 0138_mr_t_academy_m.swf | 0138_mr_t_academy_m.jpg |
| 139 | Area 51 | b | 1 | 17 | 111 | `0139_area_51_m` | 0139_area_51_m.swf | 0139_area_51_m.jpg |
| 140 | Recruitment Prize | b | 1 | 17 | 111 | `0140_recruitment_m` | 0140_recruitment_m.swf | 0140_recruitment_m.jpg |
| 141 | Bazooka Academy IV | b | 3 | 31 | 111 | `0141_bazooka_academy_4_m` | 0141_bazooka_academy_4_m.swf | 0141_bazooka_academy_4_m.jpg |
| 142 | Bazooka Academy V | b | 3 | 31 | 111 | `0142_bazooka_academy_5_m` | 0142_bazooka_academy_5_m.swf | 0142_bazooka_academy_5_m.jpg |
| 143 | Academy IV | b | 3 | 31 | 111 | `0143_academy_4_m` | 0143_academy_4_m.swf | 0143_academy_4_m.jpg |
| 144 | Academy V | b | 3 | 31 | 111 | `0144_academy_5_m` | 0144_academy_5_m.swf | 0144_academy_5_m.jpg |
| 145 | Mortar Academy | b | 3 | 35 | 111 | `0145_mortar_academy_m` | 0145_mortar_academy_m.swf | 0145_mortar_academy_m.jpg |
| 146 | Helicopter Hangar IV | b | 3 | 33 | 111 | `0146_copter_hangar_4_m` | 0146_copter_hangar_4_m.swf | 0146_copter_hangar_4_m.jpg |
| 147 | Helicopter Hangar V | b | 3 | 33 | 111 | `0147_copter_hangar_5_m` | 0147_copter_hangar_5_m.swf | 0147_copter_hangar_5_m.jpg |
| 148 | Demolition Tank Academy | b | 3 | 35 | 111 | `0148_artillery_garage_m` | 0148_artillery_garage_m.swf | 0148_artillery_garage_m.jpg |
| 149 | Antiaircraft garage | b | 3 | 34 | 111 | `0149_antiaircraft_garage_m` | 0149_antiaircraft_garage_m.swf | 0149_antiaircraft_garage_m.jpg |
| 150 | Tank Academy IV | b | 3 | 32 | 111 | `0150_tank_academy_4_m` | 0150_tank_academy_4_m.swf | 0150_tank_academy_4_m.jpg |
| 151 | Tank Academy V | b | 3 | 32 | 111 | `0151_tank_academy_5_m` | 0151_tank_academy_5_m.swf | 0151_tank_academy_5_m.jpg |
| 152 | Robo flag | b | 12 | 121 | 411 | `0152_robo_flag_m` | 0152_robo_flag_m.swf | 0152_robo_flag_m.jpg |
| 153 | Robo statue | b | 12 | 121 | 411 | `0153_robo_statue_m` | 0153_robo_statue_m.swf | 0153_robo_statue_m.jpg |
| 154 | Crusader Soldier Academy | b | 12 | 121 | 111 | `0154_robo_soldier_academy_m` | 0154_robo_soldier_academy_m.swf | 0154_robo_soldier_academy_m.jpg |
| 155 | Crusader Swordsman Academy | b | 12 | 121 | 111 | `0155_robo_swordsman_academy_m` | 0155_robo_swordsman_academy_m.swf | 0155_robo_swordsman_academy_m.jpg |
| 156 | Crusader Bazooka Academy | b | 12 | 121 | 111 | `0156_robo_bazooka_academy_m` | 0156_robo_bazooka_academy_m.swf | 0156_robo_bazooka_academy_m.jpg |
| 157 | Jet Soldier Academy | b | 12 | 121 | 111 | `0157_jet_robosoldier_academy_m` | 0157_jet_robosoldier_academy_m.swf | 0157_jet_robosoldier_academy_m.jpg |
| 158 | Motorized Soldier Academy | b | 12 | 121 | 111 | `0158_motorized_robosoldier_academy_m` | 0158_motorized_robosoldier_academy_m.swf | 0158_motorized_robosoldier_academy_m.jpg |
| 159 | Retaliator Academy | b | 12 | 121 | 111 | `0159_retaliator_academy_m` | 0159_retaliator_academy_m.swf | 0159_retaliator_academy_m.jpg |
| 160 | Megalancer Academy | b | 12 | 121 | 111 | `0160_robo_lancer_academy_m` | 0160_robo_lancer_academy_m.swf | 0160_robo_lancer_academy_m.jpg |
| 161 | Crusader Tank Academy | b | 12 | 121 | 111 | `0161_demolisher_tank_academy_m` | 0161_demolisher_tank_academy_m.swf | 0161_demolisher_tank_academy_m.jpg |
| 162 | Dreadnought Academy | b | 12 | 121 | 111 | `0162_dreadnought_academy_m` | 0162_dreadnought_academy_m.swf | 0162_dreadnought_academy_m.jpg |
| 163 | House | b | 12 | 121 | 111 | `0163_robo_house_m` | 0163_robo_house_m.swf | 0163_robo_house_m.jpg |
| 164 | Laser Turret | b | 12 | 121 | 211 | `0164_robo_turret_1_m` | 0164_robo_turret_1_m.swf | 0164_robo_turret_1_m.jpg |
| 165 | Tesla Turret | b | 12 | 121 | 211 | `0165_robo_turret_2_m` | 0165_robo_turret_2_m.swf | 0165_robo_turret_2_m.jpg |
| 166 | Wall | b | 12 | 121 | 221 | `0166_robo_wall_m` | 0166_robo_wall_m.swf | 0166_robo_wall_m.jpg |
| 167 | Field | b | 12 | 121 | 129 | `0167_robo_farm_m` | 0167_robo_farm_m.swf | 0167_robo_farm_m.jpg |
| 168 | Crusader Skylander Hangar | b | 12 | 121 | 111 | `0168_skylander_hangar_m` | 0168_skylander_hangar_m.swf | 0168_skylander_hangar_m.jpg |
| 169 | Mega-Axe Academy | b | 12 | 121 | 111 | `0169_roboaxe_academy_m` | 0169_roboaxe_academy_m.swf | 0169_roboaxe_academy_m.jpg |
| 170 | Giant Walker Factory | b | 12 | 121 | 111 | `0170_giant_walker_factory_m` | 0170_giant_walker_factory_m.swf | 0170_giant_walker_factory_m.jpg |
| 171 | Missile Tank Academy | b | 12 | 121 | 111 | `0171_missile_tank_academy_m` | 0171_missile_tank_academy_m.swf | 0171_missile_tank_academy_m.jpg |
| 172 | Steel Claws Academy | b | 12 | 121 | 111 | `0172_steel_claws_academy_m` | 0172_steel_claws_academy_m.swf | 0172_steel_claws_academy_m.jpg |
| 173 | Development Wall | b | 12 | 121 | 111 | `0166_robo_wall_m` | 0166_robo_wall_m.swf | 0166_robo_wall_m.jpg |
| 174 | Fireman Academy | b | 3 | 34 | 111 | `0174_fireman_academy_m` | 0174_fireman_academy_m.swf | 0174_fireman_academy_m.jpg |
| 175 | Babilonian Temple | b | 5 | 51 | 511 | `0175_alejandria_m` | 0175_alejandria_m.swf | 0175_alejandria_m.jpg |
| 176 | Cash Wonder | b | 5 | 51 | 511 | `0176_maravilla_m` | 0176_maravilla_m.swf | 0176_maravilla_m.jpg |
| 177 | Axe Zoldier Academy | b | 12 | 121 | 111 | `0177_orc_soldier_academy_1_m` | 0177_orc_soldier_academy_1_m.swf | 0177_orc_soldier_academy_1_m.jpg |
| 178 | Gun Zoldier Academy | b | 12 | 121 | 111 | `0178_orc_soldier_academy_2_m` | 0178_orc_soldier_academy_2_m.swf | 0178_orc_soldier_academy_2_m.jpg |
| 179 | Xplosive Ork Academy | b | 12 | 121 | 111 | `0179_orc_boss_academy_m` | 0179_orc_boss_academy_m.swf | 0179_orc_boss_academy_m.jpg |
| 180 | Bear Ridda Academy | b | 12 | 121 | 111 | `0180_orc_rider_academy_m` | 0180_orc_rider_academy_m.swf | 0180_orc_rider_academy_m.jpg |
| 181 | Horned Badass Factory | b | 12 | 121 | 111 | `0181_orc_robot_factory_m` | 0181_orc_robot_factory_m.swf | 0181_orc_robot_factory_m.jpg |
| 182 | Flamethrowa Academy | b | 12 | 121 | 111 | `0182_orc_flamethrower_academy_m` | 0182_orc_flamethrower_academy_m.swf | 0182_orc_flamethrower_academy_m.jpg |
| 183 | Ork House | b | 12 | 121 | 111 | `0183_orc_house_m` | 0183_orc_house_m.swf | 0183_orc_house_m.jpg |
| 184 | Ork Farm | b | 12 | 121 | 129 | `0184_orc_farm_m` | 0184_orc_farm_m.swf | 0184_orc_farm_m.jpg |
| 185 | Ork Turret II | b | 12 | 121 | 211 | `0185_orc_turret_m` | 0185_orc_turret_m.swf | 0185_orc_turret_m.jpg |
| 186 | Ork Wall | b | 12 | 121 | 221 | `0186_orc_wall_m` | 0186_orc_wall_m.swf | 0186_orc_wall_m.jpg |
| 187 | Krazy Monsta Statue | b | 12 | 121 | 411 | `0187_orc_deco_1_m` | 0187_orc_deco_1_m.swf | 0187_orc_deco_1_m.jpg |
| 188 | Powa Banna | b | 12 | 121 | 411 | `0188_orc_deco_2_m` | 0188_orc_deco_2_m.swf | 0188_orc_deco_2_m.jpg |
| 189 | Ork Turret I | b | 12 | 121 | 211 | `0189_orc_turret_2_m` | 0189_orc_turret_2_m.swf | 0189_orc_turret_2_m.jpg |
| 190 | Molotov Kopta Hangar | b | 12 | 121 | 111 | `0190_helicopter_hangar2_m` | 0190_helicopter_hangar2_m.swf | 0190_helicopter_hangar2_m.jpg |
| 191 | Ork Tank Academy | b | 3 | 35 | 111 | `0191_camion_orco_academy_m` | 0191_camion_orco_academy_m.swf | 0191_camion_orco_academy_m.jpg |
| 192 | Knife Throwa Academy | b | 12 | 121 | 111 | `0192_orc_lanzamachetes_academy_m` | 0192_orc_lanzamachetes_academy_m.swf | 0192_orc_lanzamachetes_academy_m.jpg |
| 193 | Kamikaze Bros Academy | b | 12 | 121 | 111 | `0193_orc_mascota_kamikaze_academy_m` | 0193_orc_mascota_kamikaze_academy_m.swf | 0193_orc_mascota_kamikaze_academy_m.jpg |
| 194 | Big Handsaw Ork Factory | b | 12 | 121 | 111 | `0194_orc_robot_2_factory_m` | 0194_orc_robot_2_factory_m.swf | 0194_orc_robot_2_factory_m.jpg |
| 195 | Orc Headquarters | b | 1 | 17 | 135 | `0195_orc_headquarters` | 0195_orc_headquarters.swf | 0195_orc_headquarters.jpg |
| 196 | Orc Sponge Bush | b | 12 | 121 | 411 | `0196_orc_sponge_bush` | 0196_orc_sponge_bush.swf | 0196_orc_sponge_bush.jpg |
| 197 | Orc Lamp | b | 12 | 121 | 411 | `0197_orc_lamp` | 0197_orc_lamp.swf | 0197_orc_lamp.jpg |
| 198 | Orc Bush | b | 12 | 121 | 411 | `0198_orc_bush` | 0198_orc_bush.swf | 0198_orc_bush.jpg |
| 200 | Silo II | b | 1 | 14 | 0 | `0200_orc_silo` | 0200_orc_silo.swf | 0200_orc_silo.jpg |
| 201 | Orc Bunker  | b | 2 | 24 | 211 | `0201_orc_bunker` | 0201_orc_bunker.swf | 0201_orc_bunker.jpg |
| 202 | Orc Resource Building | b | 1 | 12 | 129 | `0202_orc_resource_building` | 0202_orc_resource_building.swf | 0202_orc_resource_building.jpg |
| 203 | Orc Harbour | b | 1 | 14 | 0 | `0203_orc_harbour` | 0203_orc_harbour.swf | 0203_orc_harbour.jpg |
| 204 | Disabled Orc Supertank | b | 8 | 81 | 812 | `0204_disabled_orc_supertank` | 0204_disabled_orc_supertank.swf | 0204_disabled_orc_supertank.jpg |
| 205 | Orc Fortress | b | 2 | 23 | 231 | `0205_orc_fortress` | 0205_orc_fortress.swf | 0205_orc_fortress.jpg |
| 206 | Enemy Ork Wall | b | 12 | 121 | 221 | `0186_orc_wall_m` | 0186_orc_wall_m.swf | 0186_orc_wall_m.jpg |
| 207 | Enemy Ork Turret I | b | 12 | 121 | 211 | `0189_orc_turret_2_m` | 0189_orc_turret_2_m.swf | 0189_orc_turret_2_m.jpg |
| 208 | Enemy Ork Turret II | b | 12 | 121 | 211 | `0185_orc_turret_m` | 0185_orc_turret_m.swf | 0185_orc_turret_m.jpg |
| 209 | Crusader Priest Academy | b | 12 | 121 | 111 | `209_crusader_priest_academy` | 209_crusader_priest_academy.swf | 209_crusader_priest_academy.jpg |
| 210 | Crusader Bot Factory | b | 12 | 121 | 111 | `210_crusader_bot_factory` | 210_crusader_bot_factory.swf | 210_crusader_bot_factory.jpg |
| 211 | Viking Axe Academy | b | 12 | 121 | 111 | `211_axeman_academy` | 211_axeman_academy.swf | 211_axeman_academy.jpg |
| 212 | Viking Soldier Academy | b | 12 | 121 | 111 | `212_dwarf_soldier_academy` | 212_dwarf_soldier_academy.swf | 212_dwarf_soldier_academy.jpg |
| 213 | Bear Knight Academy | b | 12 | 121 | 111 | `213_bear_knight_academy` | 213_bear_knight_academy.swf | 213_bear_knight_academy.jpg |
| 214 | Viking Tank Academy | b | 12 | 121 | 111 | `214_dwarf_tank_academy` | 214_dwarf_tank_academy.swf | 214_dwarf_tank_academy.jpg |
| 215 | Viking Airship Hangar | b | 12 | 121 | 111 | `215_viking_copter_II_hangar` | 215_viking_copter_II_hangar.swf | 215_viking_copter_II_hangar.jpg |
| 216 | Viking Hammerer Factory | b | 12 | 121 | 111 | `216_megahammer_dwarf_factory` | 216_megahammer_dwarf_factory.swf | 216_megahammer_dwarf_factory.jpg |
| 217 | Viking Core Factory | b | 12 | 121 | 111 | `217_dwarf_armored_core_factory` | 217_dwarf_armored_core_factory.swf | 217_dwarf_armored_core_factory.jpg |
| 218 | Viking House | b | 12 | 121 | 111 | `218_dwarf_house` | 218_dwarf_house.swf | 218_dwarf_house.jpg |
| 219 | Viking Field | b | 12 | 121 | 129 | `219_dwarf_farm` | 219_dwarf_farm.swf | 219_dwarf_farm.jpg |
| 220 | Viking Turret I | b | 12 | 121 | 211 | `220_dwarf_turret_1` | 220_dwarf_turret_1.swf | 220_dwarf_turret_1.jpg |
| 221 | Viking Turret II | b | 12 | 121 | 211 | `221_dwarf_turret_2` | 221_dwarf_turret_2.swf | 221_dwarf_turret_2.jpg |
| 222 | Viking Wall | b | 12 | 121 | 221 | `222_dwarf_wall` | 222_dwarf_wall.swf | 222_dwarf_wall.jpg |
| 223 | Hammerer Statue | b | 12 | 121 | 411 | `223_dwarf_deco_1` | 223_dwarf_deco_1.swf | 223_dwarf_deco_1.jpg |
| 224 | Viking Fountain | b | 12 | 121 | 411 | `224_dwarf_deco_2` | 224_dwarf_deco_2.swf | 224_dwarf_deco_2.jpg |
| 225 | Alien Wall | b | 12 | 121 | 221 | `225_alien_wall` | 225_alien_wall.swf | 225_alien_wall.jpg |
| 226 | Alien Turret I | b | 12 | 121 | 211 | `226_alien_turret_1` | 226_alien_turret_1.swf | 226_alien_turret_1.jpg |
| 227 | Alien Turret II | b | 12 | 121 | 211 | `227_alien_turret_2` | 227_alien_turret_2.swf | 227_alien_turret_2.jpg |
| 228 | Spider Wall | b | 12 | 121 | 221 | `228_spider_wall` | 228_spider_wall.swf | 228_spider_wall.jpg |
| 229 | Spider Turret I | b | 12 | 121 | 211 | `229_spider_turret_1` | 229_spider_turret_1.swf | 229_spider_turret_1.jpg |
| 230 | Spider Turret II | b | 12 | 121 | 211 | `230_spider_turret_2` | 230_spider_turret_2.swf | 230_spider_turret_2.jpg |
| 231 | War Tree | b | 12 | 121 | 411 | `231_dwarf_deco_3` | 231_dwarf_deco_3.swf | 231_dwarf_deco_3.jpg |
| 232 | Magic Lake | b | 12 | 121 | 411 | `232_dwarf_deco_4` | 232_dwarf_deco_4.swf | 232_dwarf_deco_4.jpg |
| 233 | Viking Bazooka Academy | b | 12 | 121 | 111 | `233_viking_bazooka_academy` | 233_viking_bazooka_academy.swf | 233_viking_bazooka_academy.jpg |
| 234 | Viking MotoSquad Academy | b | 12 | 121 | 111 | `234_viking_motosquad_academy` | 234_viking_motosquad_academy.swf | 234_viking_motosquad_academy.jpg |
| 235 | Rune Golem Academy | b | 12 | 121 | 111 | `235_viking_rune_golem_academy` | 235_viking_rune_golem_academy.swf | 235_viking_rune_golem_academy.jpg |
| 236 | Viking Sniper Academy | b | 12 | 121 | 111 | `236_viking_sniper_academy` | 236_viking_sniper_academy.swf | 236_viking_sniper_academy.jpg |
| 237 | Viking Butcher Academy | b | 12 | 121 | 111 | `237_viking_butcher_academy` | 237_viking_butcher_academy.swf | 237_viking_butcher_academy.jpg |
| 238 | Kamikaze Academy | b | 12 | 121 | 111 | `238_kamikaze_academy` | 238_kamikaze_academy.swf | 238_kamikaze_academy.jpg |
| 239 | Laser Viking Academy | b | 12 | 121 | 111 | `239_laser_viking_academy` | 239_laser_viking_academy.swf | 239_laser_viking_academy.jpg |
| 240 | Nebular Spearman Academy | b | 12 | 121 | 111 | `240_avatar_soldado_academy` | 240_avatar_soldado_academy.swf | 240_avatar_soldado_academy.jpg |
| 241 | Nebular Archer Academy | b | 12 | 121 | 111 | `241_avatar_arquero_academy` | 241_avatar_arquero_academy.swf | 241_avatar_arquero_academy.jpg |
| 242 | Greatsword Warrior Academy | b | 12 | 121 | 111 | `242_avatar_great_warrior_academy` | 242_avatar_great_warrior_academy.swf | 242_avatar_great_warrior_academy.jpg |
| 243 | Nebular Rider Academy | b | 12 | 121 | 111 | `243_avatar_jinete_academy` | 243_avatar_jinete_academy.swf | 243_avatar_jinete_academy.jpg |
| 244 | Nebular Wall | b | 12 | 121 | 221 | `244_avatar_wall` | 244_avatar_wall.swf | 244_avatar_wall.jpg |
| 245 | Nebular Turret | b | 12 | 121 | 211 | `245_avatar_turret` | 245_avatar_turret.swf | 245_avatar_turret.jpg |
| 246 | Nebular House | b | 12 | 121 | 111 | `246_avatar_house` | 246_avatar_house.swf | 246_avatar_house.jpg |
| 247 | Nebular Field | b | 12 | 121 | 129 | `247_avatar_farm` | 247_avatar_farm.swf | 247_avatar_farm.jpg |
| 248 | Ancient Nebular Tree | b | 12 | 121 | 411 | `248_avatar_deco` | 248_avatar_deco.swf | 248_avatar_deco.jpg |
| 249 | Nebular Knight Academy | b | 12 | 121 | 111 | `249_nebula_horse_rider_academy` | 249_nebula_horse_rider_academy.swf | 249_nebula_horse_rider_academy.jpg |
| 250 | Nebular Dragon Rider Academy | b | 12 | 121 | 111 | `250_nebula_dragon_nest` | 250_nebula_dragon_nest.swf | 250_nebula_dragon_nest.jpg |
| 251 | Nebular Assault Quad Academy | b | 12 | 121 | 111 | `251_nebula_motorized_academy` | 251_nebula_motorized_academy.swf | 251_nebula_motorized_academy.jpg |
| 252 | Skyscraper | b | 4 | 42 | 411 | `252_skyscraper` | 252_skyscraper.swf | 252_skyscraper.jpg |
| 253 | Parliament | b | 5 | 51 | 511 | `253_parliament` | 253_parliament.swf | 253_parliament.jpg |
| 254 | Nebular Priest Academy | b | 12 | 121 | 111 | `254_nebula_priest_academy` | 254_nebula_priest_academy.swf | 254_nebula_priest_academy.jpg |
| 255 | Nebular Bicopter Hangar | b | 12 | 121 | 111 | `255_nebula_blue_bicopter_hangar` | 255_nebula_blue_bicopter_hangar.swf | 255_nebula_blue_bicopter_hangar.jpg |
| 256 | Research Lab | b | 1 | 17 | 111 | `256_laboratory_tech` | 256_laboratory_tech.swf | 256_laboratory_tech.jpg |
| 257 | Blazing Beast Rider Academy | b | 12 | 121 | 111 | `257_nebula_monster_rider_academy` | 257_nebula_monster_rider_academy.swf | 257_nebula_monster_rider_academy.jpg |
| 258 | Nebular Maze Warrior Academy | b | 12 | 121 | 111 | `258_nebula_muze_warrior_academy` | 258_nebula_muze_warrior_academy.swf | 258_nebula_muze_warrior_academy.jpg |
| 259 | Nebular Sniper Academy | b | 12 | 121 | 111 | `259_nebula_sniper_academy` | 259_nebula_sniper_academy.swf | 259_nebula_sniper_academy.jpg |
| 260 | Nebular Dragon Knight Academy | b | 12 | 121 | 111 | `260_dragon_rider_2_academy` | 260_dragon_rider_2_academy.swf | 260_dragon_rider_2_academy.jpg |
| 261 | Auction House | b | 1 | 17 | 111 | `261_marketplace` | 261_marketplace.swf | 261_marketplace.jpg |
| 262 | Poison Spider Hive | b | 12 | 121 | 111 | `262_venom_spider_academy` | 262_venom_spider_academy.swf | 262_venom_spider_academy.jpg |
| 263 | Shredder Alien Nest | b | 12 | 121 | 111 | `266_tusk_alien_academy` | 266_tusk_alien_academy.swf | 266_tusk_alien_academy.jpg |
| 264 | Acid Alien Nest | b | 12 | 121 | 111 | `264_small_alien_academy` | 264_small_alien_academy.swf | 264_small_alien_academy.jpg |
| 265 | Huge Spider Hive | b | 12 | 121 | 111 | `265_big_spider_academy` | 265_big_spider_academy.swf | 265_big_spider_academy.jpg |
| 266 | Horned Alien Nest | b | 12 | 121 | 111 | `263_claw_alien_academy` | 263_claw_alien_academy.swf | 263_claw_alien_academy.jpg |
| 267 | Claw Spider Hive | b | 12 | 121 | 111 | `267_melee_spider_academy` | 267_melee_spider_academy.swf | 267_melee_spider_academy.jpg |
| 268 | Swamp Monster Academy | b | 12 | 121 | 111 | `268_nebula_monster_academy` | 268_nebula_monster_academy.swf | 268_nebula_monster_academy.jpg |
| 269 | S.W.A.T. Soldier Academy | b | 12 | 121 | 111 | `269_swat_soldier_academy` | 269_swat_soldier_academy.swf | 269_swat_soldier_academy.jpg |
| 270 | Hercules Mech Academy | b | 12 | 121 | 111 | `270_hercules_mech_academy` | 270_hercules_mech_academy.swf | 270_hercules_mech_academy.jpg |
| 271 | Space Elf Wall | b | 12 | 121 | 221 | `271_spatial_wall` | 271_spatial_wall.swf | 271_spatial_wall.jpg |
| 272 | Space Elf Turret | b | 12 | 121 | 211 | `272_spatial_turret` | 272_spatial_turret.swf | 272_spatial_turret.jpg |
| 273 | Space Elf House | b | 12 | 121 | 111 | `273_spatial_house` | 273_spatial_house.swf | 273_spatial_house.jpg |
| 274 | Space Elf Field | b | 12 | 121 | 129 | `274_spatial_farm` | 274_spatial_farm.swf | 274_spatial_farm.jpg |
| 275 | Elf Eagle Deco | b | 12 | 121 | 411 | `275_spatial_deco` | 275_spatial_deco.swf | 275_spatial_deco.jpg |
| 276 | Space Sword Elf Academy | b | 12 | 121 | 111 | `276_spatial_sward_academy` | 276_spatial_sward_academy.swf | 276_spatial_sward_academy.jpg |
| 277 | Space Archer Elf Academy | b | 12 | 121 | 111 | `277_spatial_archer_academy` | 277_spatial_archer_academy.swf | 277_spatial_archer_academy.jpg |
| 278 | Space Knight Elf Academy | b | 12 | 121 | 111 | `278_spatial_horseman_academy` | 278_spatial_horseman_academy.swf | 278_spatial_horseman_academy.jpg |
| 279 | Elf Airship Hangar | b | 12 | 121 | 111 | `279_spatial_airship_hangar` | 279_spatial_airship_hangar.swf | 279_spatial_airship_hangar.jpg |
| 280 | Paladin Elf Academy | b | 12 | 121 | 111 | `280_spatial_paladin_academy` | 280_spatial_paladin_academy.swf | 280_spatial_paladin_academy.jpg |
| 281 | Priest Elf Academy | b | 12 | 121 | 111 | `281_spatial_priest_academy` | 281_spatial_priest_academy.swf | 281_spatial_priest_academy.jpg |
| 282 | Elven Cruiser Hangar | b | 12 | 121 | 111 | `282_spatial_space_ship_hangar` | 282_spatial_space_ship_hangar.swf | 282_spatial_space_ship_hangar.jpg |
| 283 | Reptile Gun Academy | b | 12 | 121 | 111 | `283_reptile_gun_hangar` | 283_reptile_gun_hangar.swf | 283_reptile_gun_hangar.jpg |
| 284 | MegaBot Academy | b | 12 | 121 | 111 | `284_mega_bot_academy` | 284_mega_bot_academy.swf | 284_mega_bot_academy.jpg |
| 285 | Space Healer Elf Academy | b | 12 | 121 | 111 | `285_spatial_healer_academy` | 285_spatial_healer_academy.swf | 285_spatial_healer_academy.jpg |
| 286 | Space Elf Scouter Hangar | b | 12 | 121 | 111 | `286_spatial_exploration_module_hangar` | 286_spatial_exploration_module_hangar.swf | 286_spatial_exploration_module_hangar.jpg |
| 287 | GunBot Academy | b | 12 | 121 | 111 | `287_gun_bot_academy` | 287_gun_bot_academy.swf | 287_gun_bot_academy.jpg |
| 288 | Silver Gunner Elf Academy | b | 12 | 121 | 111 | `288_silver_elf_gunner_academy` | 288_silver_elf_gunner_academy.swf | 288_silver_elf_gunner_academy.jpg |
| 289 | Dino Rider Elf Academy | b | 12 | 121 | 111 | `289_elf_dino_rider_academy` | 289_elf_dino_rider_academy.swf | 289_elf_dino_rider_academy.jpg |
| 290 | Destruction Wizard Elf Academy | b | 12 | 121 | 111 | `290_destruction_wizard_academy` | 290_destruction_wizard_academy.swf | 290_destruction_wizard_academy.jpg |
| 291 | Elf Siege Striker Academy | b | 12 | 121 | 111 | `291_plasma_striker_academy` | 291_plasma_striker_academy.swf | 291_plasma_striker_academy.jpg |
| 292 | Winged Paladin Academy | b | 12 | 121 | 111 | `292_winged_paladin_academy` | 292_winged_paladin_academy.swf | 292_winged_paladin_academy.jpg |
| 293 | Andromeda Wall | b | 12 | 121 | 221 | `293_andromedaWall` | 293_andromedaWall.swf | 293_andromedaWall.jpg |
| 294 | Andromeda Turret | b | 12 | 121 | 211 | `294_andromedaTurret` | 294_andromedaTurret.swf | 294_andromedaTurret.jpg |
| 295 | Andromeda House | b | 12 | 121 | 111 | `295_andromedaHouse` | 295_andromedaHouse.swf | 295_andromedaHouse.jpg |
| 296 | Andromeda Farm | b | 12 | 121 | 129 | `296_andromedaFarm` | 296_andromedaFarm.swf | 296_andromedaFarm.jpg |
| 297 | Andromeda Statue | b | 12 | 121 | 411 | `297_andromedaDeco` | 297_andromedaDeco.swf | 297_andromedaDeco.jpg |
| 298 | Andromeda Private Academy | b | 12 | 121 | 111 | `298_andromedaPrivateAcademy` | 298_andromedaPrivateAcademy.swf | 298_andromedaPrivateAcademy.jpg |
| 299 | Andromeda Droid Factory | b | 12 | 121 | 111 | `299_andromedaDroidFactory` | 299_andromedaDroidFactory.swf | 299_andromedaDroidFactory.jpg |
| 300 | Andromeda Spaceship Hangar | b | 12 | 121 | 111 | `300_andromedaSpaceshipHangar` | 300_andromedaSpaceshipHangar.swf | 300_andromedaSpaceshipHangar.jpg |
| 301 | Punisher Bot Factory | b | 12 | 121 | 111 | `301_punisherBot_Factory` | 301_punisherBot_Factory.swf | 301_punisherBot_Factory.jpg |
| 901 | Oil | b | 1 | 12 | 123 | `10001_resource_oil_1` | 10001_resource_oil_1.swf | 10001_resource_oil_1.jpg |
| 902 | Oil | b | 1 | 12 | 123 | `10002_resource_oil_2` | 10002_resource_oil_2.swf | 10002_resource_oil_2.jpg |
| 903 | Oil | b | 1 | 12 | 123 | `10003_resource_oil_3` | 10003_resource_oil_3.swf | 10003_resource_oil_3.jpg |
| 904 | Oil | b | 1 | 12 | 123 | `10004_resource_oil_4` | 10004_resource_oil_4.swf | 10004_resource_oil_4.jpg |
| 905 | Tree | b | 1 | 12 | 125 | `10005_arbol1x1` | 10005_arbol1x1.swf | 10005_arbol1x1.jpg |
| 907 | Small Harbour | b | 1 | 14 | 0 | `10007_port_1` | 10007_port_1.swf | 10007_port_1.jpg |
| 908 | Harbour | b | 1 | 14 | 0 | `10008_harbour` | 10008_harbour.swf | 10008_harbour.jpg |
| 909 | Space Station | b | 1 | 14 | 0 | `0199_space_station` | 0199_space_station.swf | 0199_space_station.jpg |
| 910 | Steel | b | 1 | 12 | 126 | `10010_resource_steel_1` | 10010_resource_steel_1.swf | 10010_resource_steel_1.jpg |
| 911 | Steel | b | 1 | 12 | 126 | `10011_resource_steel_2` | 10011_resource_steel_2.swf | 10011_resource_steel_2.jpg |
| 912 | Steel | b | 1 | 12 | 126 | `10012_resource_steel_3` | 10012_resource_steel_3.swf | 10012_resource_steel_3.jpg |
| 913 | Steel | b | 1 | 12 | 126 | `10013_resource_steel_4` | 10013_resource_steel_4.swf | 10013_resource_steel_4.jpg |
| 914 | Gold | b | 1 | 12 | 127 | `10014_resource_gold_1` | 10014_resource_gold_1.swf | 10014_resource_gold_1.jpg |
| 915 | Gold | b | 1 | 12 | 127 | `10015_resource_gold_2` | 10015_resource_gold_2.swf | 10015_resource_gold_2.jpg |
| 916 | Gold | b | 1 | 12 | 127 | `10016_resource_gold_3` | 10016_resource_gold_3.swf | 10016_resource_gold_3.jpg |
| 917 | Gold | b | 1 | 12 | 127 | `10017_resource_gold_4` | 10017_resource_gold_4.swf | 10017_resource_gold_4.jpg |
| 918 | Regenerating oil.. | b | 1 | 12 | 128 | `10018_resource_oil_regen` | 10018_resource_oil_regen.swf | 10018_resource_oil_regen.jpg |
| 919 | Regenerating steel.. | b | 1 | 12 | 128 | `10019_resource_steel_regen` | 10019_resource_steel_regen.swf | 10019_resource_steel_regen.jpg |
| 920 | Regenerating gold.. | b | 1 | 12 | 128 | `10020_resource_gold_regen` | 10020_resource_gold_regen.swf | 10020_resource_gold_regen.jpg |
| 921 | Treasure Chest | b | 8 | 81 | 811 | `treasure` | **— MISSING —** | **— MISSING —** |
| 922 | Dummy 9-91 | b | 9 | 91 | 911 | `vacaPerdida` | **— MISSING —** | **— MISSING —** |
| 923 | Gorilla | u | 1 | 12 | 128 | `10023_gorilla` | 10023_gorilla.swf | 10023_gorilla.jpg |
| 924 | Dummy 12-121 | b | 12 | 121 | 111 | `casachina` | **— MISSING —** | **— MISSING —** |
| 925 | Expandable Land | l | 6 | 6 | 6 | `terreno` | terreno.swf | **— MISSING —** |
| 926 | Key | b | 8 | 81 | 812 | `10026_key` | 10026_key.swf | 10026_key.jpg |
| 927 | Prison | b | 8 | 81 | 812 | `10027_prision` | **— MISSING —** | **— MISSING —** |
| 928 | Broken Bridge | b | 12 | 121 | 0 | `10028_broken_bridge` | 10028_broken_bridge.swf | **— MISSING —** |
| 929 | Bridge | b | 12 | 121 | 1011 | `10029_bridge` | 10029_bridge.swf | **— MISSING —** |
| 930 | Trees | b | 1 | 12 | 125 | `10030_arbol2x2` | 10030_arbol2x2.swf | 10030_arbol2x2.jpg |
| 931 | Small forest | b | 1 | 12 | 125 | `10031_arbol3x3` | 10031_arbol3x3.swf | 10031_arbol3x3.jpg |
| 932 | Silo | b | 1 | 14 | 0 | `10032_silo_1` | 10032_silo_1.swf | 10032_silo_1.jpg |
| 933 | Wild Elephant | u | 1 | 12 | 128 | `10033_wild_elephant` | 10033_wild_elephant.swf | 10033_wild_elephant.jpg |
| 941 | Silo II | b | 1 | 14 | 0 | `10041_silo_2` | 10041_silo_2.swf | 10041_silo_2.jpg |
| 942 | Silo III | b | 1 | 14 | 0 | `10042_silo_3` | 10042_silo_3.swf | 10042_silo_3.jpg |
| 943 | Destroyed building 1 | b | 12 | 121 | 1011 | `10043_destroyed_building_1` | 10043_destroyed_building_1.swf | 10043_destroyed_building_1.jpg |
| 944 | Destroyed building 2 | b | 12 | 121 | 1011 | `10044_destroyed_building_2` | 10044_destroyed_building_2.swf | 10044_destroyed_building_2.jpg |
| 945 | Destroyed building 3 | b | 12 | 121 | 1011 | `10045_destroyed_building_3` | 10045_destroyed_building_3.swf | 10045_destroyed_building_3.jpg |
| 946 | Destroyed building 4 | b | 12 | 121 | 1011 | `10046_destroyed_building_4` | 10046_destroyed_building_4.swf | 10046_destroyed_building_4.jpg |
| 947 | Destroyed building 5 | b | 12 | 121 | 1011 | `10047_destroyed_building_5_b` | 10047_destroyed_building_5_b.swf | 10047_destroyed_building_5_b.jpg |
| 948 | Oil barrel | b | 12 | 121 | 0 | `10048_oil_barrel` | 10048_oil_barrel.swf | 10048_oil_barrel.jpg |
| 949 | Atrezzo Harbour | b | 1 | 14 | 0 | `10049_harbour` | 10049_harbour.swf | **— MISSING —** |
| 950 | Nice fountain | b | 4 | 45 | 411 | `10050_nice_fountain` | 10050_nice_fountain.swf | **— MISSING —** |
| 951 | Orange Tree | b | 4 | 45 | 411 | `10051_orange_tree` | 10051_orange_tree.swf | **— MISSING —** |
| 952 | Chickens | b | 4 | 45 | 411 | `10052_chickens` | 10052_chickens.swf | **— MISSING —** |
| 953 | Lost Rocket | b | 4 | 45 | 411 | `10053_lost_rocket` | 10053_lost_rocket.swf | **— MISSING —** |
| 954 | Astronaut Pack | b | 4 | 45 | 411 | `10054_astronaut_pack` | 10054_astronaut_pack.swf | **— MISSING —** |
| 955 | Destroyed Tank | b | 4 | 45 | 411 | `10055_destroyed_tank` | 10055_destroyed_tank.swf | **— MISSING —** |
| 956 | Lost Puppies | b | 4 | 45 | 411 | `10056_lost_puppies` | 10056_lost_puppies.swf | **— MISSING —** |
| 957 | Lost Oil Barrels | b | 4 | 45 | 411 | `1005_oil_barrels` | 1005_oil_barrels.swf | **— MISSING —** |
| 958 | Green T-Rex Cage | b | 1 | 14 | 0 | `10058_trex_cage` | 10058_trex_cage.swf | 10058_trex_cage.jpg |
| 959 | Red T-Rex Cage | b | 1 | 14 | 0 | `10059_trex_cage` | 10059_trex_cage.swf | 10059_trex_cage.jpg |
| 960 | Chest | b | 12 | 121 | 0 | `10060_chest` | 10060_chest.swf | **— MISSING —** |
| 961 | Chained Red Baron | b | 4 | 45 | 411 | `10061_chained_red_baron` | 10061_chained_red_baron.swf | 10061_chained_red_baron.jpg |
| 962 | Chained Metallic Dragon | b | 4 | 45 | 411 | `10062_chained_metallic_dragon` | 10062_chained_metallic_dragon.swf | 10062_chained_metallic_dragon.jpg |
| 963 | Chained Celestial Megamech | b | 4 | 45 | 411 | `10063_chained_celestial_megamech` | 10063_chained_celestial_megamech.swf | 10063_chained_celestial_megamech.jpg |
| 964 | Chained Metallic Dragon II | b | 4 | 45 | 411 | `10064_chained_metallic_dragon2` | 10064_chained_metallic_dragon2.swf | 10064_chained_metallic_dragon2.jpg |
| 965 | Chained Armored Core Alpha | b | 4 | 45 | 411 | `965_chained_armored_core_alpha` | 965_chained_armored_core_alpha.swf | 965_chained_armored_core_alpha.jpg |
| 966 | Chained Ultra-Mech | b | 4 | 45 | 411 | `966_chained_transformer_gigante` | 966_chained_transformer_gigante.swf | 966_chained_transformer_gigante.jpg |
| 967 | Chained Nemesis Core | b | 4 | 45 | 411 | `967_chained_ultra_robot` | 967_chained_ultra_robot.swf | 967_chained_ultra_robot.jpg |
| 968 | Chained F117 | b | 4 | 45 | 411 | `968_chained_f117` | 968_chained_f117.swf | 968_chained_f117.jpg |
| 969 | Chained Mega Tank | b | 4 | 45 | 411 | `969_chained_mega_tank` | 969_chained_mega_tank.swf | 969_chained_mega_tank.jpg |
| 970 | Chained Blue Steel Bahamut | b | 4 | 45 | 411 | `970_chained_bahamut_metalico` | 970_chained_bahamut_metalico.swf | 970_chained_bahamut_metalico.jpg |
| 971 | Chained Alien Instigator | b | 4 | 45 | 411 | `971_chained_alien_instigator` | 971_chained_alien_instigator.swf | 971_chained_alien_instigator.jpg |
| 972 | Chained Hyper Blazer  | b | 4 | 45 | 411 | `972_chained_mega_fire_bot` | 972_chained_mega_fire_bot.swf | 972_chained_mega_fire_bot.jpg |
| 973 | Chained Ether Messiah | b | 4 | 45 | 411 | `973_chained_ether_messiah` | 973_chained_ether_messiah.swf | 973_chained_ether_messiah.jpg |
| 974 | Chained Combo Dragons | b | 4 | 45 | 411 | `974_chained_combo_dragons` | 974_chained_combo_dragons.swf | 974_chained_combo_dragons.jpg |
| 975 | Chained Golem Boss | b | 4 | 45 | 411 | `975_chained_golem_boss` | 975_chained_golem_boss.swf | 975_chained_golem_boss.jpg |
| 976 | Chained Crusader Bot | b | 4 | 45 | 411 | `976_chained_crusader_bot` | 976_chained_crusader_bot.swf | 976_chained_crusader_bot.jpg |
| 977 | Chained Samurai Bot | b | 4 | 45 | 411 | `977_chained_samurai_bot` | 977_chained_samurai_bot.swf | 977_chained_samurai_bot.jpg |
| 978 | Chained Magic Chest | b | 4 | 45 | 411 | `978_chained_corfe_1` | 978_chained_corfe_1.swf | 978_chained_corfe_1.jpg |
| 979 | Chained Mega Chest | b | 4 | 45 | 411 | `979_chained_corfe_2` | 979_chained_corfe_2.swf | 979_chained_corfe_2.jpg |
| 980 | Chained Camu Dragon | b | 4 | 45 | 411 | `980_chained_camu_dragon` | 980_chained_camu_dragon.swf | 980_chained_camu_dragon.jpg |
| 981 | Chained Skater | b | 4 | 45 | 411 | `981_chained_skater` | 981_chained_skater.swf | 981_chained_skater.jpg |
| 982 | Chained Red Spinner | b | 4 | 45 | 411 | `982_chained_red_spinner` | **— MISSING —** | **— MISSING —** |
| 983 | Chained Golden Slayer | b | 4 | 45 | 411 | `983_chained_transformer_sword` | 983_chained_transformer_sword.swf | 983_chained_transformer_sword.jpg |
| 984 | Chained Gun Bot | b | 4 | 45 | 411 | `984_chained_gun_bot_2` | 984_chained_gun_bot_2.swf | 984_chained_gun_bot_2.jpg |
| 985 | Chained Robo Hunter | b | 4 | 45 | 411 | `985_chained_robo_hunter` | 985_chained_robo_hunter.swf | 985_chained_robo_hunter.jpg |
| 986 | Chained 50% Off | b | 4 | 45 | 411 | `986_chained_50_off` | 986_chained_50_off.swf | 986_chained_50_off.jpg |
| 987 | Chained Ufo | b | 4 | 45 | 411 | `987_chained_ufo` | 987_chained_ufo.swf | 987_chained_ufo.jpg |
| 988 | Chained MegaAxe&MegaLancer | b | 4 | 45 | 411 | `988_chained_axe_lancer` | 988_chained_axe_lancer.swf | 988_chained_axe_lancer.jpg |
| 989 | Chained Megafire T-Rex | b | 4 | 45 | 411 | `989_chained_trex` | 989_chained_trex.swf | 989_chained_trex.jpg |
| 990 | Chained Double Cash Offer | b | 4 | 45 | 411 | `990_chained_double` | 990_chained_double.swf | 990_chained_double.jpg |
| 991 | Chained Fire Karateka | b | 4 | 45 | 411 | `991_chained_karateka` | 991_chained_karateka.swf | 991_chained_karateka.jpg |
| 992 | Chained Gold Golem | b | 4 | 45 | 411 | `992_chained_gold_golem` | 992_chained_gold_golem.swf | 992_chained_gold_golem.jpg |
| 993 | Chained Double Cash Offer + F117 | b | 4 | 45 | 411 | `993_chained_double_f117` | 993_chained_double_f117.swf | 993_chained_double_f117.jpg |
| 994 | Chained Black Dragon | b | 4 | 45 | 411 | `994_chained_black_dragon` | 994_chained_black_dragon.swf | 994_chained_black_dragon.jpg |
| 995 | Chained Electric Dragon | b | 4 | 45 | 411 | `995_chained_electric_dragon` | 995_chained_electric_dragon.swf | 995_chained_electric_dragon.jpg |
| 996 | Chained Dragonborn Mech | b | 4 | 45 | 411 | `996_chained_dragon_mech` | 996_chained_dragon_mech.swf | 996_chained_dragon_mech.jpg |
| 997 | Chained Silver Hercules | b | 4 | 45 | 411 | `997_chained_herkules_matrix` | 997_chained_herkules_matrix.swf | 997_chained_herkules_matrix.jpg |
| 998 | Chained Rune Golem | b | 4 | 45 | 411 | `998_chained_rune_golem` | 998_chained_rune_golem.swf | 998_chained_rune_golem.jpg |
| 999 | Chained Supreme Chest | b | 4 | 45 | 411 | `999_chained_supreme_chest` | 999_chained_supreme_chest.swf | 999_chained_supreme_chest.jpg |
| 1001 | Worker I | u | 7 | 7 | 71 | `1001_worker_m,1001_worker_w` | 1001_worker_m.swf;1001_worker_w.swf | 1001_worker_m.jpg;1001_worker_w.jpg |
| 1002 | Red Tank | u | 7 | 7 | 80 | `1002_Red_Tank_m` | 1002_Red_Tank_m.swf | 1002_Red_Tank_m.jpg |
| 1003 | Tank II | u | 7 | 7 | 80 | `1003_cannon_2_m` | 1003_cannon_2_m.swf | 1003_cannon_2_m.jpg |
| 1004 | Tank III | u | 7 | 7 | 80 | `1004_cannon_3_m` | 1004_cannon_3_m.swf | 1004_cannon_3_m.jpg |
| 1005 | Special Spy | u | 7 | 7 | 80 | `1005_special_spy_m` | 1005_special_spy_m.swf | 1005_special_spy_m.jpg |
| 1006 | Killer Bazooka Jeep | u | 7 | 7 | 80 | `1006_red_bazooka_jeep_m` | 1006_red_bazooka_jeep_m.swf | 1006_red_bazooka_jeep_m.jpg |
| 1007 | Soldier | u | 7 | 7 | 80 | `1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_w` | 1007_soldier_1_m.swf;1007_soldier_1_m.swf;1007_soldier_1_m.swf;1007_soldier_1_m.swf;1007_soldier_1_w.swf | 1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_m.jpg;1007_soldier_1_w.jpg |
| 1008 | Bazooka | u | 7 | 7 | 80 | `1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_w` | 1008_bazooka_1_m.swf;1008_bazooka_1_m.swf;1008_bazooka_1_m.swf;1008_bazooka_1_m.swf;1008_bazooka_1_w.swf | 1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_m.jpg;1008_bazooka_1_w.jpg |
| 1009 | General Scarlett | u | 7 | 7 | 80 | `1009_good_girl_m` | 1009_good_girl_m.swf | 1009_good_girl_m.jpg |
| 1010 | APC | u | 7 | 7 | 80 | `1010_apc_m` | 1010_apc_m.swf | 1010_apc_m.jpg |
| 1011 | Ms. Evilia | u | 7 | 7 | 80 | `1011_bad_girl_m` | **— MISSING —** | **— MISSING —** |
| 1012 | Evil Hannibal | u | 7 | 7 | 80 | `1012_bad_boy` | 1012_bad_boy.swf | 1012_bad_boy.jpg |
| 1013 | Truck | u | 7 | 7 | 80 | `1013_truck_1_m` | 1013_truck_1_m.swf | 1013_truck_1_m.jpg |
| 1014 | Machine Gun Jeep | u | 7 | 7 | 80 | `1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_w` | 1014_machinegunjeep_1_m.swf;1014_machinegunjeep_1_m.swf;1014_machinegunjeep_1_m.swf;1014_machinegunjeep_1_m.swf;1014_machinegunjeep_1_w.swf | 1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_m.jpg;1014_machinegunjeep_1_w.jpg |
| 1015 | Aircraft | u | 7 | 7 | 83 | `1015_aircraft_1_m` | 1015_aircraft_1_m.swf | 1015_aircraft_1_m.jpg |
| 1016 | Tank | u | 7 | 7 | 80 | `1016_cannon_1_m` | 1016_cannon_1_m.swf | 1016_cannon_1_m.jpg |
| 1017 | General Mike | u | 7 | 7 | 80 | `1017_good_boy` | 1017_good_boy.swf | 1017_good_boy.jpg |
| 1018 | Zodiac | u | 7 | 7 | 80 | `1018_zodiac_m` | 1018_zodiac_m.swf | 1018_zodiac_m.jpg |
| 1019 | Ship | u | 7 | 7 | 80 | `1019_ship_m2` | 1019_ship_m2.swf | 1019_ship_m2.jpg |
| 1020 | Soldier II | u | 7 | 7 | 80 | `1020_soldier_2_m` | 1020_soldier_2_m.swf | 1020_soldier_2_m.jpg |
| 1021 | Soldier III | u | 7 | 7 | 80 | `1021_soldier_3_m` | 1021_soldier_3_m.swf | 1021_soldier_3_m.jpg |
| 1022 | Bazooka II | u | 7 | 7 | 80 | `1022_bazooka_2_m` | 1022_bazooka_2_m.swf | 1022_bazooka_2_m.jpg |
| 1023 | Bazooka III | u | 7 | 7 | 80 | `1023_bazooka_3_m` | 1023_bazooka_3_m.swf | 1023_bazooka_3_m.jpg |
| 1024 | Sergeant Megan | u | 7 | 7 | 80 | `1024_good_guillerma` | 1024_good_guillerma.swf | 1024_good_guillerma.jpg |
| 1025 | Aircraft II | u | 7 | 7 | 83 | `1025_aircraft_2_m` | 1025_aircraft_2_m.swf | 1025_aircraft_2_m.jpg |
| 1026 | Aircraft III | u | 7 | 7 | 83 | `1026_aircraft_3_m` | 1026_aircraft_3_m.swf | 1026_aircraft_3_m.jpg |
| 1027 | Helicopter | u | 7 | 7 | 83 | `1027_helicopter_1_m` | 1027_helicopter_1_m.swf | 1027_helicopter_1_m.jpg |
| 1028 | Helicopter II | u | 7 | 7 | 83 | `1028_helicopter_2_m` | 1028_helicopter_2_m.swf | 1028_helicopter_2_m.jpg |
| 1029 | Helicopter III | u | 7 | 7 | 83 | `1029_helicopter_3_m` | 1029_helicopter_3_m.swf | 1029_helicopter_3_m.jpg |
| 1030 | Machine Gun Jeep II | u | 7 | 7 | 80 | `1030_machinegunjeep_2_m` | 1030_machinegunjeep_2_m.swf | 1030_machinegunjeep_2_m.jpg |
| 1031 | Machine Gun Jeep III | u | 7 | 7 | 80 | `1031_machinegunjeep_3_m` | 1031_machinegunjeep_3_m.swf | 1031_machinegunjeep_3_m.jpg |
| 1032 | Truck 3 | u | 7 | 7 | 80 | `1032_truck_3_m` | 1032_truck_3_m.swf | 1032_truck_3_m.jpg |
| 1033 | Mr. Cigar | u | 7 | 7 | 80 | `1033_mr_cigar` | 1033_mr_cigar.swf | 1033_mr_cigar.jpg |
| 1034 | UN Allied | u | 7 | 7 | 80 | `1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_w` | 1034_un_allied_1_m.swf;1034_un_allied_1_m.swf;1034_un_allied_1_m.swf;1034_un_allied_1_m.swf;1034_un_allied_1_w.swf | 1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_m.jpg;1034_un_allied_1_w.jpg |
| 1035 | Truck II | u | 7 | 7 | 80 | `1035_truck_2_m` | 1035_truck_2_m.swf | 1035_truck_2_m.jpg |
| 1036 | Double Bazooka | u | 7 | 7 | 80 | `1036_double_bazooka_m` | 1036_double_bazooka_m.swf | 1036_double_bazooka_m.jpg |
| 1037 | MegaTank | u | 7 | 7 | 80 | `1037_megatank` | 1037_megatank.swf | 1037_megatank.jpg |
| 1038 | Red chopper | u | 7 | 7 | 83 | `1038_red_helicopter_m` | 1038_red_helicopter_m.swf | 1038_red_helicopter_m.jpg |
| 1039 | Worker II | u | 7 | 7 | 71 | `1001_worker_m` | 1001_worker_m.swf | 1001_worker_m.jpg |
| 1040 | Worker III | u | 7 | 7 | 71 | `1001_worker_m` | 1001_worker_m.swf | 1001_worker_m.jpg |
| 1041 | Worker IV | u | 7 | 7 | 71 | `1001_worker_m` | 1001_worker_m.swf | 1001_worker_m.jpg |
| 1042 | Sergeant Jack | u | 7 | 7 | 80 | `1042_good_guile` | 1042_good_guile.swf | 1042_good_guile.jpg |
| 1043 | Air Strike | u | 7 | 7 | 83 | `1043_air_strike_m` | 1043_air_strike_m.swf | 1043_air_strike_m.jpg |
| 1044 | Double Bazooka Jeep | u | 7 | 7 | 80 | `1044_double_bazooka_jeep_m` | 1044_double_bazooka_jeep_m.swf | 1044_double_bazooka_jeep_m.jpg |
| 1045 | Double Gun Soldier | u | 7 | 7 | 80 | `1045_double_gun_soldier_m` | 1045_double_gun_soldier_m.swf | 1045_double_gun_soldier_m.jpg |
| 1046 | Flamethrower | u | 7 | 7 | 80 | `1046_flamethrower_m` | 1046_flamethrower_m.swf | 1046_flamethrower_m.jpg |
| 1047 | Dominion Tank | u | 7 | 7 | 80 | `1047_black_tank_2_m` | 1047_black_tank_2_m.swf | 1047_black_tank_2_m.jpg |
| 1048 | Stealth Fighter | u | 7 | 7 | 83 | `1048_black_aircraft_2_m` | 1048_black_aircraft_2_m.swf | 1048_black_aircraft_2_m.jpg |
| 1049 | TankBoss | u | 7 | 7 | 80 | `1053_golem_boss_m` | 1053_golem_boss_m.swf | 1053_golem_boss_m.jpg |
| 1050 | Medic | u | 7 | 7 | 80 | `1050_medic_m` | 1050_medic_m.swf | 1050_medic_m.jpg |
| 1051 | Engineer | u | 7 | 7 | 80 | `1051_mechanic_m` | 1051_mechanic_m.swf | 1051_mechanic_m.jpg |
| 1052 | Special Ops. | u | 7 | 7 | 80 | `1052_special_ops_2_m` | 1052_special_ops_2_m.swf | 1052_special_ops_2_m.jpg |
| 1053 | GolemBoss | u | 7 | 7 | 80 | `1053_golem_boss_m` | 1053_golem_boss_m.swf | 1053_golem_boss_m.jpg |
| 1054 | Scarface girl | u | 7 | 7 | 80 | `1054_scarface_girl` | 1054_scarface_girl.swf | 1054_scarface_girl.jpg |
| 1055 | Mr. Treat | u | 7 | 7 | 80 | `1055_mr_t_m` | 1055_mr_t_m.swf | 1055_mr_t_m.jpg |
| 1056 | Elephant rider | u | 7 | 7 | 80 | `1056_elephant_rider_m` | 1056_elephant_rider_m.swf | 1056_elephant_rider_m.jpg |
| 1057 | T-Rex Green | u | 7 | 7 | 80 | `1057_t-rex_m` | 1057_t-rex_m.swf | 1057_t-rex_m.jpg |
| 1058 | Soldier IV | u | 7 | 7 | 80 | `1058_soldier_4_m` | 1058_soldier_4_m.swf | 1058_soldier_4_m.jpg |
| 1059 | Soldier V | u | 7 | 7 | 80 | `1059_soldier_5_m` | 1059_soldier_5_m.swf | 1059_soldier_5_m.jpg |
| 1060 | Mortar Thrower | u | 7 | 7 | 80 | `1060_mortar_m` | 1060_mortar_m.swf | 1060_mortar_m.jpg |
| 1061 | GunBot | u | 7 | 7 | 80 | `1061_baby_robot_m` | 1061_baby_robot_m.swf | 1061_baby_robot_m.jpg |
| 1062 | MegaBot | u | 7 | 7 | 80 | `1062_bumblebee_m` | 1062_bumblebee_m.swf | 1062_bumblebee_m.jpg |
| 1063 | Bazooka IV | u | 7 | 7 | 80 | `1063_bazooka_4_m` | 1063_bazooka_4_m.swf | 1063_bazooka_4_m.jpg |
| 1064 | Bazooka V | u | 7 | 7 | 80 | `1064_bazooka_5_m` | 1064_bazooka_5_m.swf | 1064_bazooka_5_m.jpg |
| 1065 | Antiaircraft battery | u | 7 | 7 | 80 | `1065_antiaircraft_battery_m` | 1065_antiaircraft_battery_m.swf | 1065_antiaircraft_battery_m.jpg |
| 1066 | Helicopter IV | u | 7 | 7 | 83 | `1066_helicopter_4_m` | 1066_helicopter_4_m.swf | 1066_helicopter_4_m.jpg |
| 1067 | Helicopter V | u | 7 | 7 | 83 | `1067_helicopter_5_m` | 1067_helicopter_5_m.swf | 1067_helicopter_5_m.jpg |
| 1068 | B52 | u | 7 | 7 | 83 | `1068_b52_m` | 1068_b52_m.swf | 1068_b52_m.jpg |
| 1069 | Demolition Tank | u | 7 | 7 | 80 | `1069_bigheaded_tank_m` | 1069_bigheaded_tank_m.swf | 1069_bigheaded_tank_m.jpg |
| 1070 | Tank IV | u | 7 | 7 | 80 | `1070_cannon_4_m` | 1070_cannon_4_m.swf | 1070_cannon_4_m.jpg |
| 1071 | Tank V | u | 7 | 7 | 80 | `1071_cannon_5_m` | 1071_cannon_5_m.swf | 1071_cannon_5_m.jpg |
| 1072 | Ranbo | u | 7 | 7 | 80 | `1072_rambo_m` | 1072_rambo_m.swf | 1072_rambo_m.jpg |
| 1073 | Erradicator | u | 7 | 7 | 80 | `1073_erradicator_m` | 1073_erradicator_m.swf | 1073_erradicator_m.jpg |
| 1074 | Punisher Bot | u | 7 | 7 | 80 | `1074_punisher_m` | 1074_punisher_m.swf | 1074_punisher_m.jpg |
| 1075 | Supreme Bot | u | 7 | 7 | 80 | `1075_supreme_m` | 1075_supreme_m.swf | 1075_supreme_m.jpg |
| 1076 | Crusader Soldier | u | 7 | 7 | 80 | `1076_robo_soldier_m` | 1076_robo_soldier_m.swf | 1076_robo_soldier_m.jpg |
| 1077 | Swordsman Soldier | u | 7 | 7 | 80 | `1077_robo_swordsman_m` | 1077_robo_swordsman_m.swf | 1077_robo_swordsman_m.jpg |
| 1078 | Bazooka Soldier | u | 7 | 7 | 80 | `1078_robo_bazooka_m` | 1078_robo_bazooka_m.swf | 1078_robo_bazooka_m.jpg |
| 1079 | Jet Soldier | u | 7 | 7 | 80 | `1079_robo_jumper_m` | 1079_robo_jumper_m.swf | 1079_robo_jumper_m.jpg |
| 1080 | Motorized Soldier | u | 7 | 7 | 80 | `1080_robo_biker_m` | 1080_robo_biker_m.swf | 1080_robo_biker_m.jpg |
| 1081 | Xtreme Retaliator | u | 7 | 7 | 80 | `1081_xtreme_retaliator_m` | 1081_xtreme_retaliator_m.swf | 1081_xtreme_retaliator_m.jpg |
| 1082 | Megalancer | u | 7 | 7 | 80 | `1082_robo_lancer_m` | 1082_robo_lancer_m.swf | 1082_robo_lancer_m.jpg |
| 1083 | Crusader Tank | u | 7 | 7 | 80 | `1083_demlisher_tank_m` | 1083_demlisher_tank_m.swf | 1083_demlisher_tank_m.jpg |
| 1084 | Dreadnought | u | 7 | 7 | 80 | `1084_dreadnought_m` | 1084_dreadnought_m.swf | 1084_dreadnought_m.jpg |
| 1085 | Metal Draggy | u | 7 | 7 | 83 | `1085_metal_draggy_m` | 1085_metal_draggy_m.swf | 1085_metal_draggy_m.jpg |
| 1086 | Mechanical Golem | u | 7 | 7 | 80 | `1053_golem_boss_m` | 1053_golem_boss_m.swf | 1053_golem_boss_m.jpg |
| 1087 | T-Rex | u | 7 | 7 | 80 | `1057_t-rex_m` | 1057_t-rex_m.swf | 1057_t-rex_m.jpg |
| 1088 | Skylander | u | 7 | 7 | 80 | `1088_skylander_m` | 1088_skylander_m.swf | 1088_skylander_m.jpg |
| 1089 | Mega-Axe | u | 7 | 7 | 80 | `1089_robo_axe_m` | 1089_robo_axe_m.swf | 1089_robo_axe_m.jpg |
| 1090 | Giant Walker | u | 7 | 7 | 80 | `1090_giant_walker_m` | 1090_giant_walker_m.swf | 1090_giant_walker_m.jpg |
| 1091 | Missile Tank | u | 7 | 7 | 80 | `1091_missile_tank_m` | 1091_missile_tank_m.swf | 1091_missile_tank_m.jpg |
| 1092 | Steel Claws | u | 7 | 7 | 80 | `1092_steel_claws_m` | 1092_steel_claws_m.swf | 1092_steel_claws_m.jpg |
| 1093 | Fire T-Rex | u | 7 | 7 | 80 | `1093_trex_m` | 1093_trex_m.swf | 1093_trex_m.jpg |
| 1094 | Aircraft IV | u | 7 | 7 | 83 | `1094_aircraft_4_m` | 1094_aircraft_4_m.swf | 1094_aircraft_4_m.jpg |
| 1095 | Aircraft V | u | 7 | 7 | 83 | `1095_aircraft_5_m` | 1095_aircraft_5_m.swf | 1095_aircraft_5_m.jpg |
| 1096 | F-117 | u | 7 | 7 | 83 | `1096_f117_m` | 1096_f117_m.swf | 1096_f117_m.jpg |
| 1097 | Red Draggy | u | 7 | 7 | 83 | `1097_red_draggy_m` | 1097_red_draggy_m.swf | 1097_red_draggy_m.jpg |
| 1098 | Blue Draggy | u | 7 | 7 | 83 | `1098_blue_draggy_m` | 1098_blue_draggy_m.swf | 1098_blue_draggy_m.jpg |
| 1099 | Red Dragon | u | 7 | 7 | 83 | `1099_red_dragon2_m` | 1099_red_dragon2_m.swf | 1099_red_dragon2_m.jpg |
| 1100 | Blue Dragon | u | 7 | 7 | 83 | `1100_blue_dragon2_m` | 1100_blue_dragon2_m.swf | 1100_blue_dragon2_m.jpg |
| 1101 | Celestial Megamech | u | 7 | 7 | 80 | `1101_celestial_megamech_m` | 1101_celestial_megamech_m.swf | 1101_celestial_megamech_m.jpg |
| 1102 | Red Baron | u | 7 | 7 | 83 | `1102_red_baron_m` | 1102_red_baron_m.swf | 1102_red_baron_m.jpg |
| 1103 | Zeppelin | u | 7 | 7 | 83 | `1103_zeppelin_m` | 1103_zeppelin_m.swf | 1103_zeppelin_m.jpg |
| 1104 | Fireman | u | 7 | 7 | 71 | `1104_fireman_1_m` | 1104_fireman_1_m.swf | 1104_fireman_1_m.jpg |
| 1105 | Metal Dragon | u | 7 | 7 | 83 | `1105_metalico_dragon3_m` | 1105_metalico_dragon3_m.swf | 1105_metalico_dragon3_m.jpg |
| 1106 | Axe Zoldier | u | 7 | 7 | 80 | `1106_hacha_m_2` | 1106_hacha_m_2.swf | 1106_hacha_m_2.jpg |
| 1107 | Gun Zoldier | u | 7 | 7 | 80 | `1107_metralleta_m_2` | 1107_metralleta_m_2.swf | 1107_metralleta_m_2.jpg |
| 1108 | Xplosive Ork | u | 7 | 7 | 80 | `1108_orc_boss_m_2` | 1108_orc_boss_m_2.swf | 1108_orc_boss_m_2.jpg |
| 1109 | Bear Ridda | u | 7 | 7 | 80 | `1109_orco_jinete_m_2` | 1109_orco_jinete_m_2.swf | 1109_orco_jinete_m_2.jpg |
| 1110 | Molotov Kopta | u | 7 | 7 | 80 | `1110_helicoptero_orco_m2` | 1110_helicoptero_orco_m2.swf | 1110_helicoptero_orco_m2.jpg |
| 1111 | Horned Badass | u | 7 | 7 | 80 | `1111_robot_orco_1_m` | 1111_robot_orco_1_m.swf | 1111_robot_orco_1_m.jpg |
| 1112 | Red Spinner | u | 7 | 7 | 80 | `1112_optimus_m` | 1112_optimus_m.swf | 1112_optimus_m.jpg |
| 1113 | Flamethrowa Ork | u | 7 | 7 | 80 | `1113_orc_flamethrower_m` | 1113_orc_flamethrower_m.swf | 1113_orc_flamethrower_m.jpg |
| 1114 | Knife Throwa | u | 7 | 7 | 80 | `1114_orc_knivethrower_m` | 1114_orc_knivethrower_m.swf | 1114_orc_knivethrower_m.jpg |
| 1115 | Big Handsaw Ork | u | 7 | 7 | 80 | `1115_orc_robot_22_m` | 1115_orc_robot_22_m.swf | 1115_orc_robot_22_m.jpg |
| 1116 | Orc Tank | u | 7 | 7 | 80 | `1116_orc_tank_m` | 1116_orc_tank_m.swf | 1116_orc_tank_m.jpg |
| 1117 | Kamikaze team | u | 7 | 7 | 80 | `1117_orc_kamikaze_team` | 1117_orc_kamikaze_team.swf | 1117_orc_kamikaze_team.jpg |
| 1118 | Kamikaze critter | u | 7 | 7 | 80 | `1118_squig_kamikaze` | 1118_squig_kamikaze.swf | 1118_squig_kamikaze.jpg |
| 1119 | Camu Metal Dragon | u | 7 | 7 | 83 | `1119_metal_dragon2_m` | 1119_metal_dragon2_m.swf | 1119_metal_dragon2_m.jpg |
| 1120 | Camu Draggy | u | 7 | 7 | 83 | `1120_metal_draggy_2_m` | 1120_metal_draggy_2_m.swf | 1120_metal_draggy_2_m.jpg |
| 1121 | War Buggy | u | 7 | 7 | 80 | `1121_buggy_2_m` | 1121_buggy_2_m.swf | 1121_buggy_2_m.jpg |
| 1122 | Orc Zoldier | u | 7 | 7 | 80 | `1122_orc_basic_gun_2` | 1122_orc_basic_gun_2.swf | 1122_orc_basic_gun_2.jpg |
| 1123 | Orc Swordsman | u | 7 | 7 | 80 | `1123_orc_basic_knife_2` | 1123_orc_basic_knife_2.swf | 1123_orc_basic_knife_2.jpg |
| 1124 | Basic Ork Tank | u | 7 | 7 | 80 | `1124_ork_tank_1` | 1124_ork_tank_1.swf | 1124_ork_tank_1.jpg |
| 1125 | Orc Worker | u | 7 | 7 | 71 | `1125_orc_worker` | 1125_orc_worker.swf | 1125_orc_worker.jpg |
| 1126 | Samurai Bot | u | 7 | 7 | 80 | `1126_samurai_bot_m` | 1126_samurai_bot_m.swf | 1126_samurai_bot_m.jpg |
| 1127 | Armored Core Alpha | u | 7 | 7 | 80 | `1127_huge_robot_m` | 1127_huge_robot_m.swf | 1127_huge_robot_m.jpg |
| 1128 | Alpha Drone | u | 7 | 7 | 83 | `1128_huge_draggy_m` | 1128_huge_draggy_m.swf | 1128_huge_draggy_m.jpg |
| 1129 | Samurai Minibot | u | 7 | 7 | 80 | `1129_samurai_minibot` | 1129_samurai_minibot.swf | **— MISSING —** |
| 1130 | Xplosive Beast Boss | u | 7 | 7 | 80 | `1130_xplosive_boss_2` | 1130_xplosive_boss_2.swf | 1130_xplosive_boss_2.jpg |
| 1131 | Xplosive Beast ATP | u | 7 | 7 | 80 | `1116_orc_tank_m_2` | 1116_orc_tank_m_2.swf | 1116_orc_tank_m_2.jpg |
| 1132 | Xplosive Beast | u | 7 | 7 | 80 | `1108_orc_boss_m_2` | 1108_orc_boss_m_2.swf | 1108_orc_boss_m_2.jpg |
| 1133 | Ork Bear Knight | u | 7 | 7 | 80 | `1109_orco_jinete_m_2` | 1109_orco_jinete_m_2.swf | 1109_orco_jinete_m_2.jpg |
| 1134 | Ork Kopta | u | 7 | 7 | 80 | `1110_helicoptero_orco_m2` | 1110_helicoptero_orco_m2.swf | 1110_helicoptero_orco_m2.jpg |
| 1135 | Horned Beast Ork | u | 7 | 7 | 80 | `1111_robot_orco_1_m` | 1111_robot_orco_1_m.swf | 1111_robot_orco_1_m.jpg |
| 1136 | Red Flamethrowa Ork | u | 7 | 7 | 80 | `1113_orc_flamethrower_m` | 1113_orc_flamethrower_m.swf | 1113_orc_flamethrower_m.jpg |
| 1137 | Orc Knifethrower | u | 7 | 7 | 80 | `1114_orc_knivethrower_m` | 1114_orc_knivethrower_m.swf | 1114_orc_knivethrower_m.jpg |
| 1138 | Red Handsaw Ork | u | 7 | 7 | 80 | `1115_orc_robot_22_m` | 1115_orc_robot_22_m.swf | 1115_orc_robot_22_m.jpg |
| 1139 | Kamikaze Bros | u | 7 | 7 | 80 | `1117_orc_kamikaze_team` | 1117_orc_kamikaze_team.swf | 1117_orc_kamikaze_team.jpg |
| 1140 | Kamikaze Pet | u | 7 | 7 | 80 | `1118_squig_kamikaze` | 1118_squig_kamikaze.swf | 1118_squig_kamikaze.jpg |
| 1141 | Samurai Bot | u | 7 | 7 | 80 | `1126_samurai_bot_m` | 1126_samurai_bot_m.swf | 1126_samurai_bot_m.jpg |
| 1142 | Samurai Minibot | u | 7 | 7 | 80 | `1129_samurai_minibot_m` | 1129_samurai_minibot_m.swf | 1129_samurai_minibot_m.jpg |
| 1143 | Melee Spider | u | 7 | 7 | 80 | `1143_melee_spider_s` | 1143_melee_spider_s.swf | 1143_melee_spider_s.jpg |
| 1144 | Venom Spider | u | 7 | 7 | 80 | `1144_ranged_spider_s` | 1144_ranged_spider_s.swf | 1144_ranged_spider_s.jpg |
| 1145 | Big Spider | u | 7 | 7 | 80 | `1145_spider_semi_boss_s_2` | 1145_spider_semi_boss_s_2.swf | 1145_spider_semi_boss_s_2.jpg |
| 1146 | Small Alien | u | 7 | 7 | 80 | `1146_basic_alien_s` | 1146_basic_alien_s.swf | 1146_basic_alien_s.jpg |
| 1147 | Tusk Alien | u | 7 | 7 | 80 | `1147_alien_bull_s` | 1147_alien_bull_s.swf | 1147_alien_bull_s.jpg |
| 1148 | Claw Alien | u | 7 | 7 | 80 | `1148_alien_claws_s` | 1148_alien_claws_s.swf | 1148_alien_claws_s.jpg |
| 1149 | Orc Big Tank | u | 7 | 7 | 80 | `1116_orc_tank_m` | 1116_orc_tank_m.swf | 1116_orc_tank_m.jpg |
| 1150 | Crusader Bot | u | 7 | 7 | 80 | `1150_crusader_bot` | 1150_crusader_bot.swf | 1150_crusader_bot.jpg |
| 1151 | Crusader Priest | u | 7 | 7 | 80 | `1151_crusader_priest` | 1151_crusader_priest.swf | 1151_crusader_priest.jpg |
| 1152 | Ultra-Mech | u | 7 | 7 | 80 | `1152_transformer_gigante` | 1152_transformer_gigante.swf | 1152_transformer_gigante.jpg |
| 1153 | Ultra-Mech Drone | u | 7 | 7 | 83 | `1153_transformer_gigante_drone` | 1153_transformer_gigante_drone.swf | 1153_transformer_gigante_drone.jpg |
| 1154 | Viking Axeman | u | 7 | 7 | 80 | `1154_axeman` | 1154_axeman.swf | 1154_axeman.jpg |
| 1155 | Viking Soldier | u | 7 | 7 | 80 | `1155_dwarf_soldier` | 1155_dwarf_soldier.swf | 1155_dwarf_soldier.jpg |
| 1156 | Viking Bear Knight | u | 7 | 7 | 80 | `1156_bear_knight` | 1156_bear_knight.swf | 1156_bear_knight.jpg |
| 1157 | Viking Tank | u | 7 | 7 | 80 | `1157_dwarf_tank` | 1157_dwarf_tank.swf | 1157_dwarf_tank.jpg |
| 1158 | Viking Airship | u | 7 | 7 | 80 | `1158_viking_copter_II` | 1158_viking_copter_II.swf | 1158_viking_copter_II.jpg |
| 1159 | Viking Hammerer | u | 7 | 7 | 80 | `1159_megahammer_dwarf` | 1159_megahammer_dwarf.swf | 1159_megahammer_dwarf.jpg |
| 1160 | Viking Core Bot | u | 7 | 7 | 80 | `1160_dwarf_armored_core` | 1160_dwarf_armored_core.swf | 1160_dwarf_armored_core.jpg |
| 1161 | Rune Golem | u | 7 | 7 | 80 | `1161_viking_rune_golem` | 1161_viking_rune_golem.swf | **— MISSING —** |
| 1162 | Nemesis Core | u | 7 | 7 | 80 | `1162_ultra_robot` | 1162_ultra_robot.swf | 1162_ultra_robot.jpg |
| 1163 | Nemesis Drone | u | 7 | 7 | 83 | `1163_ultra_robot_drone` | 1163_ultra_robot_drone.swf | 1163_ultra_robot_drone.jpg |
| 1164 | Viking Core Bot Drone | u | 7 | 7 | 83 | `1164_dwarf_armored_core_drone` | 1164_dwarf_armored_core_drone.swf | 1164_dwarf_armored_core_drone.jpg |
| 1165 | Viking Bazooka | u | 7 | 7 | 80 | `1165_bazooka_viking` | 1165_bazooka_viking.swf | 1165_bazooka_viking.jpg |
| 1166 | Viking MotoSquad | u | 7 | 7 | 80 | `1166_viking_motosquad` | 1166_viking_motosquad.swf | 1166_viking_motosquad.jpg |
| 1167 | Blue Steel Bahamut | u | 7 | 7 | 83 | `1167_bahamut_metalico` | 1167_bahamut_metalico.swf | 1167_bahamut_metalico.jpg |
| 1168 | Blue Steel Draggy | u | 7 | 7 | 83 | `1168_bahamut_metalico_draggy` | 1168_bahamut_metalico_draggy.swf | 1168_bahamut_metalico_draggy.jpg |
| 1169 | Roller Skater | u | 7 | 7 | 80 | `1169_transformer_skater` | 1169_transformer_skater.swf | 1169_transformer_skater.jpg |
| 1170 | Alien Instigator | u | 7 | 7 | 80 | `1170_alien_instigator` | 1170_alien_instigator.swf | 1170_alien_instigator.jpg |
| 1171 | Rune Golem Drone | u | 7 | 7 | 83 | `1171_viking_rune_golem_drone` | 1171_viking_rune_golem_drone.swf | 1171_viking_rune_golem_drone.jpg |
| 1172 | Hyper Blazer | u | 7 | 7 | 80 | `1172_mega_fire_bot` | 1172_mega_fire_bot.swf | 1172_mega_fire_bot.jpg |
| 1173 | Hyper Blazer Drone | u | 7 | 7 | 83 | `1173_mega_fire_bot_drone` | 1173_mega_fire_bot_drone.swf | 1173_mega_fire_bot_drone.jpg |
| 1174 | Viking Sniper | u | 7 | 7 | 80 | `1174_viking_sniper` | 1174_viking_sniper.swf | 1174_viking_sniper.jpg |
| 1175 | Chainsaw Butcher | u | 7 | 7 | 80 | `1175_viking_butcher` | 1175_viking_butcher.swf | 1175_viking_butcher.jpg |
| 1176 | Kamikaze | u | 7 | 7 | 80 | `1176_kamikaze` | 1176_kamikaze.swf | 1176_kamikaze.jpg |
| 1177 | UFO | u | 7 | 7 | 80 | `1177_ufo` | 1177_ufo.swf | 1177_ufo.jpg |
| 1178 | Ether Messiah | u | 7 | 7 | 80 | `1178_ether_messiah` | 1178_ether_messiah.swf | 1178_ether_messiah.jpg |
| 1179 | Ether Messiah Drone | u | 7 | 7 | 83 | `1179_ether_messiah_drone` | 1179_ether_messiah_drone.swf | 1179_ether_messiah_drone.jpg |
| 1180 | Robot Hunter | u | 7 | 7 | 80 | `1180_robot_hunter` | 1180_robot_hunter.swf | 1180_robot_hunter.jpg |
| 1181 | Golden Slayer | u | 7 | 7 | 80 | `1181_transformer_sword` | 1181_transformer_sword.swf | 1181_transformer_sword.jpg |
| 1182 | Golden Slayer Drone | u | 7 | 7 | 83 | `1182_transformer_sword_drone` | 1182_transformer_sword_drone.swf | 1182_transformer_sword_drone.jpg |
| 1183 | Big Laser Viking | u | 7 | 7 | 80 | `1183_laser_viking` | 1183_laser_viking.swf | 1183_laser_viking.jpg |
| 1184 | Fire Karateka | u | 7 | 7 | 80 | `1184_karateka` | 1184_karateka.swf | 1184_karateka.jpg |
| 1185 | MegaFire T-Rex | u | 7 | 7 | 80 | `1093_trex_m` | 1093_trex_m.swf | 1093_trex_m.jpg |
| 1186 | Nebular Spearman | u | 7 | 7 | 80 | `1186_avatar_soldado` | 1186_avatar_soldado.swf | 1186_avatar_soldado.jpg |
| 1187 | Nebular Archer | u | 7 | 7 | 80 | `1187_avatar_arquero` | 1187_avatar_arquero.swf | 1187_avatar_arquero.jpg |
| 1188 | Greatsword Warrior | u | 7 | 7 | 80 | `1188_avatar_great_warrior` | 1188_avatar_great_warrior.swf | 1188_avatar_great_warrior.jpg |
| 1189 | Nebular Rider | u | 7 | 7 | 80 | `1189_avatar_jinete` | 1189_avatar_jinete.swf | 1189_avatar_jinete.jpg |
| 1190 | Golden Golem | u | 7 | 7 | 80 | `1190_gold_golem` | 1190_gold_golem.swf | 1190_gold_golem.jpg |
| 1191 | Black Dragon | u | 7 | 7 | 83 | `1191_black_dragon` | 1191_black_dragon.swf | 1191_black_dragon.jpg |
| 1192 | Dragonborn Mech | u | 7 | 7 | 80 | `1192_dragon_mech` | 1192_dragon_mech.swf | 1192_dragon_mech.jpg |
| 1193 | Dragonborn Drone | u | 7 | 7 | 83 | `1193_dragon_mech_drone` | 1193_dragon_mech_drone.swf | 1193_dragon_mech_drone.jpg |
| 1194 | Electric Dragon | u | 7 | 7 | 80 | `1194_electric_dragon_2` | 1194_electric_dragon_2.swf | 1194_electric_dragon_2.jpg |
| 1195 | Electric Draggy | u | 7 | 7 | 83 | `1195_electric_draggy` | 1195_electric_draggy.swf | 1195_electric_draggy.jpg |
| 1196 | Black Draggy | u | 7 | 7 | 83 | `1196_black_draggy` | 1196_black_draggy.swf | 1196_black_draggy.jpg |
| 1197 | Silver Hercules | u | 7 | 7 | 80 | `1197_herkules_matrix` | 1197_herkules_matrix.swf | 1197_herkules_matrix.jpg |
| 1198 | Nebular Knight | u | 7 | 7 | 80 | `1198_nebular_horse_rider` | 1198_nebular_horse_rider.swf | 1198_nebular_horse_rider.jpg |
| 1199 | Nebular Dragon Rider | u | 7 | 7 | 83 | `1199_nebular_dragon_rider` | 1199_nebular_dragon_rider.swf | 1199_nebular_dragon_rider.jpg |
| 1200 | Nebular Assault Quad | u | 7 | 7 | 80 | `1200_nebular_motorized` | 1200_nebular_motorized.swf | 1200_nebular_motorized.jpg |
| 1201 | Steel Collector | u | 7 | 7 | 80 | `1201_junk_bot` | 1201_junk_bot.swf | 1201_junk_bot.jpg |
| 1202 | Nebular Dragon Rider Draggy | u | 7 | 7 | 83 | `1202_nebular_dragon_rider_draggy` | 1202_nebular_dragon_rider_draggy.swf | 1202_nebular_dragon_rider_draggy.jpg |
| 1203 | Viking Airship Outsider | u | 7 | 7 | 80 | `1158_viking_copter_II` | 1158_viking_copter_II.swf | 1158_viking_copter_II.jpg |
| 1204 | Viking Hammerer Outsider | u | 7 | 7 | 80 | `1159_megahammer_dwarf` | 1159_megahammer_dwarf.swf | 1159_megahammer_dwarf.jpg |
| 1205 | Dual Blade Automech | u | 7 | 7 | 80 | `1205_dual_blade_automech` | 1205_dual_blade_automech.swf | 1205_dual_blade_automech.jpg |
| 1206 | Dual Blade Automech Drone | u | 7 | 7 | 83 | `1206_dual_blade_automech_drone` | 1206_dual_blade_automech_drone.swf | 1206_dual_blade_automech_drone.jpg |
| 1207 | Black Belt Archer | u | 7 | 7 | 80 | `1207_transformer_archer` | 1207_transformer_archer.swf | 1207_transformer_archer.jpg |
| 1208 | Nebular Priest | u | 7 | 7 | 80 | `1208_nebula_priest` | 1208_nebula_priest.swf | 1208_nebula_priest.jpg |
| 1209 | Nebular Bicopter | u | 7 | 7 | 83 | `1209_nebular_blue_bicopter` | 1209_nebular_blue_bicopter.swf | 1209_nebular_blue_bicopter.jpg |
| 1210 | Great Shogun Mech | u | 7 | 7 | 80 | `1210_samurai_mech` | 1210_samurai_mech.swf | 1210_samurai_mech.jpg |
| 1211 | Great Shogun Mech Drone | u | 7 | 7 | 83 | `1211_samurai_mech_drone` | 1211_samurai_mech_drone.swf | 1211_samurai_mech_drone.jpg |
| 1212 | ATP Mech | u | 7 | 7 | 80 | `1212_tetrapod_mech` | 1212_tetrapod_mech.swf | 1212_tetrapod_mech.jpg |
| 1213 | Blazing Beast Rider | u | 7 | 7 | 80 | `1213_nebular_monster_rider` | 1213_nebular_monster_rider.swf | 1213_nebular_monster_rider.jpg |
| 1214 | Nebular Maze Warrior | u | 7 | 7 | 80 | `1214_nebular_maze_warrior` | 1214_nebular_maze_warrior.swf | 1214_nebular_maze_warrior.jpg |
| 1215 | Massive Cannon Mech | u | 7 | 7 | 80 | `1215_massive_cannon_mech` | 1215_massive_cannon_mech.swf | 1215_massive_cannon_mech.jpg |
| 1216 | Massive Cannon Drone | u | 7 | 7 | 83 | `1216_massive_cannon_drone` | 1216_massive_cannon_drone.swf | 1216_massive_cannon_drone.jpg |
| 1217 | Brutus Mech | u | 7 | 7 | 80 | `1217_brutus_mech` | 1217_brutus_mech.swf | 1217_brutus_mech.jpg |
| 1218 | S.W.A.T. Soldier | u | 7 | 7 | 80 | `1218_swat_soldier` | 1218_swat_soldier.swf | 1218_swat_soldier.jpg |
| 1219 | Nebular Dragon Knight | u | 7 | 7 | 80 | `1219_nebular_rider` | 1219_nebular_rider.swf | 1219_nebular_rider.jpg |
| 1220 | Nebular Sniper | u | 7 | 7 | 80 | `1220_nebular_sniper` | 1220_nebular_sniper.swf | 1220_nebular_sniper.jpg |
| 1221 | Nebular Dragon Knight Draggy | u | 7 | 7 | 83 | `1221_nebular_rider_draggy` | 1221_nebular_rider_draggy.swf | 1221_nebular_rider_draggy.jpg |
| 1222 | Liquid Mech  | u | 7 | 7 | 80 | `1222_liquid_mech` | 1222_liquid_mech.swf | 1222_liquid_mech.jpg |
| 1223 | Killer Driller | u | 7 | 7 | 80 | `1223_drill` | 1223_drill.swf | 1223_drill.jpg |
| 1224 | Liquid Mech  Drone | u | 7 | 7 | 83 | `1224_liquid_mech _drone` | 1224_liquid_mech _drone.swf | 1224_liquid_mech _drone.jpg |
| 1225 | Doctor Shock | u | 7 | 7 | 80 | `1225_doctor_shock` | 1225_doctor_shock.swf | 1225_doctor_shock.jpg |
| 1226 | Red Mercury Dragon | u | 7 | 7 | 80 | `1226_dragon_metalic` | 1226_dragon_metalic.swf | 1226_dragon_metalic.jpg |
| 1227 | Red Mercury Draggy | u | 7 | 7 | 83 | `1227_dragon_metalic_draggy` | 1227_dragon_metalic_draggy.swf | 1227_dragon_metalic_draggy.jpg |
| 1228 | Swamp Monster | u | 7 | 7 | 80 | `1228_nebula_monster` | 1228_nebula_monster.swf | 1228_nebula_monster.jpg |
| 1229 | Poison Spider | u | 7 | 7 | 80 | `1144_ranged_spider_s` | 1144_ranged_spider_s.swf | 1144_ranged_spider_s.jpg |
| 1230 | Shredder Alien | u | 7 | 7 | 80 | `1148_alien_claws_s` | 1148_alien_claws_s.swf | 1148_alien_claws_s.jpg |
| 1231 | Swamp Minion | u | 7 | 7 | 80 | `1231_nebula_monster_mini` | 1231_nebula_monster_mini.swf | 1231_nebula_monster_mini.jpg |
| 1232 | Claw Spider | u | 7 | 7 | 80 | `1143_melee_spider_s` | 1143_melee_spider_s.swf | 1143_melee_spider_s.jpg |
| 1233 | Huge Spider | u | 7 | 7 | 80 | `1145_spider_semi_boss_s_2` | 1145_spider_semi_boss_s_2.swf | 1145_spider_semi_boss_s_2.jpg |
| 1234 | Acid Alien | u | 7 | 7 | 80 | `1146_basic_alien_s` | 1146_basic_alien_s.swf | 1146_basic_alien_s.jpg |
| 1235 | Horned Alien | u | 7 | 7 | 80 | `1147_alien_bull_s` | 1147_alien_bull_s.swf | 1147_alien_bull_s.jpg |
| 1236 | 2-Gun Exobot | u | 7 | 7 | 80 | `1236_2gun_exobot` | 1236_2gun_exobot.swf | 1236_2gun_exobot.jpg |
| 1237 | Cyber Samurai Mech | u | 7 | 7 | 80 | `1237_cyber_samurai_mech` | 1237_cyber_samurai_mech.swf | 1237_cyber_samurai_mech.jpg |
| 1238 | Cyber Samurai  Drone | u | 7 | 7 | 83 | `1238_cyber_samurai_mech_drone` | 1238_cyber_samurai_mech_drone.swf | 1238_cyber_samurai_mech_drone.jpg |
| 1239 | Dark Ether Messiah | u | 7 | 7 | 80 | `1239_dark_ether_messiah` | 1239_dark_ether_messiah.swf | 1239_dark_ether_messiah.jpg |
| 1240 | Dark Ether Messiah Drone | u | 7 | 7 | 83 | `1240_dark_ether_messiah_drone` | 1240_dark_ether_messiah_drone.swf | 1240_dark_ether_messiah_drone.jpg |
| 1241 | Converter Wizard | u | 7 | 7 | 80 | `1241_enemy_converter_priest` | 1241_enemy_converter_priest.swf | 1241_enemy_converter_priest.jpg |
| 1242 | Hercules Mech | u | 7 | 7 | 80 | `1242_herkules_mech` | 1242_herkules_mech.swf | 1242_herkules_mech.jpg |
| 1243 | Forge Dragon | u | 7 | 7 | 80 | `1243_forge_dragon` | 1243_forge_dragon.swf | 1243_forge_dragon.jpg |
| 1244 | Forge Dragon Draggy | u | 7 | 7 | 83 | `1244_forge_draggy` | 1244_forge_draggy.swf | 1244_forge_draggy.jpg |
| 1245 | Reptile Gun | u | 7 | 7 | 80 | `1245_reptile_gun` | 1245_reptile_gun.swf | 1245_reptile_gun.jpg |
| 1246 | Double Cannon Mech | u | 7 | 7 | 80 | `1246_double_cannon_mech` | 1246_double_cannon_mech.swf | 1246_double_cannon_mech.jpg |
| 1247 | Double Cannon Drone | u | 7 | 7 | 83 | `1247_double_cannon_drone` | 1247_double_cannon_drone.swf | 1247_double_cannon_drone.jpg |
| 1248 | Laser Blade Automech | u | 7 | 7 | 80 | `1248_laser_blade_automech` | 1248_laser_blade_automech.swf | 1248_laser_blade_automech.jpg |
| 1249 | Laser Blade Automech Drone | u | 7 | 7 | 83 | `1249_laser_blade_automech_drone` | 1249_laser_blade_automech_drone.swf | 1249_laser_blade_automech_drone.jpg |
| 1250 | Burning Slayer | u | 7 | 7 | 80 | `1250_red_slayer` | 1250_red_slayer.swf | 1250_red_slayer.jpg |
| 1251 | Burning Slayer Drone | u | 7 | 7 | 83 | `1251_red_slayer_drone` | 1251_red_slayer_drone.swf | 1251_red_slayer_drone.jpg |
| 1252 | Karateka Gunner | u | 7 | 7 | 80 | `1252_karateka_gunner` | 1252_karateka_gunner.swf | 1252_karateka_gunner.jpg |
| 1253 | Swamp Monster | u | 7 | 7 | 80 | `1228_nebula_monster` | 1228_nebula_monster.swf | 1228_nebula_monster.jpg |
| 1254 | Prime Automech | u | 7 | 7 | 80 | `1254_optimus_prime` | 1254_optimus_prime.swf | 1254_optimus_prime.jpg |
| 1255 | Prime Automech Drone | u | 7 | 7 | 83 | `1255_optimus_prime_drone` | 1255_optimus_prime_drone.swf | 1255_optimus_prime_drone.jpg |
| 1256 | Big Razor Mech | u | 7 | 7 | 80 | `1256_big_razor_mech` | 1256_big_razor_mech.swf | 1256_big_razor_mech.jpg |
| 1257 | Big Razor Mech Drone | u | 7 | 7 | 83 | `1257_big_razor_mech_drone` | 1257_big_razor_mech_drone.swf | 1257_big_razor_mech_drone.jpg |
| 1258 | S.W.A.T. Soldier | u | 7 | 7 | 80 | `1218_swat_soldier` | 1218_swat_soldier.swf | 1218_swat_soldier.jpg |
| 1259 | Space Sword Elf | u | 7 | 7 | 80 | `1259_spatial_sward` | 1259_spatial_sward.swf | 1259_spatial_sward.jpg |
| 1260 | Space Archer Elf | u | 7 | 7 | 80 | `1260_spatial_archer` | 1260_spatial_archer.swf | 1260_spatial_archer.jpg |
| 1261 | Space Knight Elf | u | 7 | 7 | 80 | `1261_spatial_horseman` | 1261_spatial_horseman.swf | 1261_spatial_horseman.jpg |
| 1262 | Space Airship Elf | u | 7 | 7 | 83 | `1262_spatial_airship` | 1262_spatial_airship.swf | 1262_spatial_airship.jpg |
| 1263 | Spartan Warrior Mech | u | 7 | 7 | 80 | `1263_spartan_warrior_mech` | 1263_spartan_warrior_mech.swf | 1263_spartan_warrior_mech.jpg |
| 1264 | Spartan Warrior Drone | u | 7 | 7 | 83 | `1264_spartan_warrior_drone` | 1264_spartan_warrior_drone.swf | 1264_spartan_warrior_drone.jpg |
| 1265 | Space Priest Elf | u | 7 | 7 | 80 | `1265_spatial_priest` | 1265_spatial_priest.swf | 1265_spatial_priest.jpg |
| 1266 | Space Paladin Elf | u | 7 | 7 | 80 | `1266_spatial_paladin` | 1266_spatial_paladin.swf | 1266_spatial_paladin.jpg |
| 1267 | Space Elf Cruiser | u | 7 | 7 | 83 | `1267_spatial_space_ship` | 1267_spatial_space_ship.swf | 1267_spatial_space_ship.jpg |
| 1268 | Proto Winged Mech | u | 7 | 7 | 80 | `1268_winged_transformer` | 1268_winged_transformer.swf | 1268_winged_transformer.jpg |
| 1269 | Proto Winged Drone | u | 7 | 7 | 83 | `1269_winged_transformer_drone` | 1269_winged_transformer_drone.swf | 1269_winged_transformer_drone.jpg |
| 1270 | Spider Bot | u | 7 | 7 | 80 | `1270_spider_bot` | 1270_spider_bot.swf | 1270_spider_bot.jpg |
| 1271 | Pharaoh Warrior Mech | u | 7 | 7 | 80 | `1271_egyptian_warrior_mech` | 1271_egyptian_warrior_mech.swf | 1271_egyptian_warrior_mech.jpg |
| 1272 | Arachnid Mech | u | 7 | 7 | 80 | `1272_transformer_aracnid` | 1272_transformer_aracnid.swf | 1272_transformer_aracnid.jpg |
| 1273 | Arachnid Drone | u | 7 | 7 | 83 | `1273_transformer_aracnid_drone` | 1273_transformer_aracnid_drone.swf | 1273_transformer_aracnid_drone.jpg |
| 1274 | Multi Morpher | u | 7 | 7 | 80 | `1274_multi_morph` | 1274_multi_morph.swf | 1274_multi_morph.jpg |
| 1275 | Space Healer Elf | u | 7 | 7 | 80 | `1275_spatial_elf_healer` | 1275_spatial_elf_healer.swf | 1275_spatial_elf_healer.jpg |
| 1276 | Space Scouter Elf | u | 7 | 7 | 80 | `1276_spatial_exploration_module` | 1276_spatial_exploration_module.swf | 1276_spatial_exploration_module.jpg |
| 1277 | Pharaoh Mech Drone | u | 7 | 7 | 83 | `1277_egyptian_warrior_drone` | 1277_egyptian_warrior_drone.swf | 1277_egyptian_warrior_drone.jpg |
| 1278 | MegaBot | u | 7 | 7 | 80 | `1062_bumblebee_m` | 1062_bumblebee_m.swf | 1062_bumblebee_m.jpg |
| 1279 | Black Brutus Mech | u | 7 | 7 | 80 | `1279_black_brutus_mech` | 1279_black_brutus_mech.swf | 1279_black_brutus_mech.jpg |
| 1280 | 2-Head Frostfire Dragon | u | 7 | 7 | 80 | `1280_frost_fire_dragon` | 1280_frost_fire_dragon.swf | 1280_frost_fire_dragon.jpg |
| 1281 | Silver Gunner Elf | u | 7 | 7 | 80 | `1281_silver_elf_gunner` | 1281_silver_elf_gunner.swf | 1281_silver_elf_gunner.jpg |
| 1282 | Dino Rider Elf | u | 7 | 7 | 80 | `1282_elf_dino_rider` | 1282_elf_dino_rider.swf | 1282_elf_dino_rider.jpg |
| 1283 | 2-Head Frostfire Draggy | u | 7 | 7 | 83 | `1283_frost_fire_draggy` | 1283_frost_fire_draggy.swf | 1283_frost_fire_draggy.jpg |
| 1284 | Watcher Hero | u | 7 | 7 | 80 | `1284_cyclop_soldier` | 1284_cyclop_soldier.swf | 1284_cyclop_soldier.jpg |
| 1285 | Siege Striker | u | 7 | 7 | 83 | `1285_plasma_striker` | 1285_plasma_striker.swf | 1285_plasma_striker.jpg |
| 1286 | Avenger Mech Drone | u | 7 | 7 | 83 | `1286_avenger_mech_draggy` | 1286_avenger_mech_draggy.swf | 1286_avenger_mech_draggy.jpg |
| 1287 | Avenger Mech  | u | 7 | 7 | 80 | `1287_avenger_mech` | 1287_avenger_mech.swf | 1287_avenger_mech.jpg |
| 1288 | Destruction Wizard | u | 7 | 7 | 80 | `1288_destruction_wizard` | 1288_destruction_wizard.swf | 1288_destruction_wizard.jpg |
| 1289 | Executioner Mech Drone | u | 7 | 7 | 83 | `1289_executioner_mech_draggy` | 1289_executioner_mech_draggy.swf | 1289_executioner_mech_draggy.jpg |
| 1290 | Executioner Mech  | u | 7 | 7 | 80 | `1290_executioner_mech` | 1290_executioner_mech.swf | 1290_executioner_mech.jpg |
| 1291 | Winged Paladin | u | 7 | 7 | 80 | `1291_winged_paladin` | 1291_winged_paladin.swf | 1291_winged_paladin.jpg |
| 1292 | Andromeda Private | u | 7 | 7 | 80 | `1292_andromeda_private` | 1292_andromeda_private.swf | 1292_andromeda_private.jpg |
| 1293 | Godzilla Mech | u | 7 | 7 | 80 | `1293_godzilla_mech` | 1293_godzilla_mech.swf | 1293_godzilla_mech.jpg |
| 1294 | Godzilla Mech Drone | u | 7 | 7 | 83 | `1294_godzilla_mech_drone` | 1294_godzilla_mech_drone.swf | 1294_godzilla_mech_drone.jpg |
| 1295 | Andromeda Combat Droid | u | 7 | 7 | 80 | `1295_andromeda_combat_droid` | 1295_andromeda_combat_droid.swf | 1295_andromeda_combat_droid.jpg |
| 1296 | Andromeda Spaceship | u | 7 | 7 | 80 | `1296_andromeda_combat_spaceship` | 1296_andromeda_combat_spaceship.swf | 1296_andromeda_combat_spaceship.jpg |
| 1297 | King Kong Mech | u | 7 | 7 | 80 | `1297_kingKongMech` | 1297_kingKongMech.swf | 1297_kingKongMech.jpg |
| 1298 | King Kong Drone | u | 7 | 7 | 83 | `1298_kingKongDrone` | 1298_kingKongDrone.swf | 1298_kingKongDrone.jpg |
| 1299 | Gamera Mech | u | 7 | 7 | 80 | `1299_gameraMech` | 1299_gameraMech.swf | 1299_gameraMech.jpg |
| 1300 | Gamera Drone | u | 7 | 7 | 83 | `1300_gameraDrone` | 1300_gameraDrone.swf | 1300_gameraDrone.jpg |
| 1301 | Z Project Mech | u | 7 | 7 | 80 | `1301_zProjectMech` | 1301_zProjectMech.swf | 1301_zProjectMech.jpg |
| 1302 | Z Project Drone | u | 7 | 7 | 83 | `1302_zProjectDrone` | 1302_zProjectDrone.swf | 1302_zProjectDrone.jpg |
| 1303 | Massive Gunner Mech | u | 7 | 7 | 80 | `1303_massiveGunnerMech` | 1303_massiveGunnerMech.swf | 1303_massiveGunnerMech.jpg |
| 1304 | Massive Gunner Drone | u | 7 | 7 | 83 | `1304_massiveGunnerDrone` | 1304_massiveGunnerDrone.swf | 1304_massiveGunnerDrone.jpg |
| 1305 | Fire Godzilla Mech | u | 7 | 7 | 80 | `1305_blackGodzilla_mech` | 1305_blackGodzilla_mech.swf | 1305_blackGodzilla_mech.jpg |
| 1306 | Fire Godzilla Drone | u | 7 | 7 | 83 | `1306_blackGodzilla_drone` | 1306_blackGodzilla_drone.swf | 1306_blackGodzilla_drone.jpg |
| 10000 | Chained Bonus + Giant Walker | b | 4 | 45 | 411 | `10000_chained_bonus_giant_walker` | **— MISSING —** | **— MISSING —** |
| 10001 | Chained Bonus + Red Baron | b | 4 | 45 | 411 | `10001_chained_bonus_red_barron` | 10001_chained_bonus_red_barron.swf | 10001_chained_bonus_red_barron.jpg |
| 10002 | Chained Steel Collector | b | 4 | 45 | 411 | `10002_chained_junk_bot` | 10002_chained_junk_bot.swf | 10002_chained_junk_bot.jpg |
| 10003 | Chained Dual Blade Automech | b | 4 | 45 | 411 | `10003_chained_dual_blade_automech` | 10003_chained_dual_blade_automech.swf | 10003_chained_dual_blade_automech.jpg |
| 10004 | Chained Black Belt Archer | b | 4 | 45 | 411 | `10004_chained_transformer_archer` | 10004_chained_transformer_archer.swf | 10004_chained_transformer_archer.jpg |
| 10005 | Chained 30% Off | b | 4 | 45 | 411 | `10005_chained_30_off` | 10005_chained_30_off.swf | 10005_chained_30_off.jpg |
| 10006 | Chained Great Shogun Mech | b | 4 | 45 | 411 | `10006_chained_samurai_mech` | 10006_chained_samurai_mech.swf | 10006_chained_samurai_mech.jpg |
| 10007 | Chained ATP Mech | b | 4 | 45 | 411 | `10007_chained_tetrapod_mech` | 10007_chained_tetrapod_mech.swf | 10007_chained_tetrapod_mech.jpg |
| 10008 | Chained Bonus + Electric Draggy | b | 4 | 45 | 411 | `10008_chained_bonus_electric_draggy` | 10008_chained_bonus_electric_draggy.swf | 10008_chained_bonus_electric_draggy.jpg |
| 10009 | Chained Stealth Chest | b | 4 | 45 | 411 | `10009_chained_stealth_chest` | 10009_chained_stealth_chest.swf | 10009_chained_stealth_chest.jpg |
| 10010 | Chained 35% Off | b | 4 | 45 | 411 | `10010_chained_35_off` | 10010_chained_35_off.swf | 10010_chained_35_off.jpg |
| 10011 | Chained Cannon Mech | b | 4 | 45 | 411 | `10011_chained_cannon_mech` | 10011_chained_cannon_mech.swf | 10011_chained_cannon_mech.jpg |
| 10012 | Chained Brutus Mech | b | 4 | 45 | 411 | `10012_chained_brutus_mech` | 10012_chained_brutus_mech.swf | 10012_chained_brutus_mech.jpg |
| 10013 | Chained S.W.A.T. Soldier | b | 4 | 45 | 411 | `10013_chained_caballero_zodiac` | 10013_chained_caballero_zodiac.swf | 10013_chained_caballero_zodiac.jpg |
| 10014 | Chained Bonus +  Ether Messiah Drone | b | 4 | 45 | 411 | `10014_chained_bonus_ether_messiah_drone` | 10014_chained_bonus_ether_messiah_drone.swf | 10014_chained_bonus_ether_messiah_drone.jpg |
| 10015 | Chained Advanced Chest | b | 4 | 45 | 411 | `10015_chained_advance_chest` | 10015_chained_advance_chest.swf | 10015_chained_advance_chest.jpg |
| 10016 | Chained 60% Off | b | 4 | 45 | 411 | `10016_chained_60_off` | 10016_chained_60_off.swf | 10016_chained_60_off.jpg |
| 10017 | Chained Liquid Mech | b | 4 | 45 | 411 | `10017_chained_liquid_mech` | 10017_chained_liquid_mech.swf | 10017_chained_liquid_mech.jpg |
| 10018 | Chained Killer Driller | b | 4 | 45 | 411 | `10018_chained_drill` | 10018_chained_drill.swf | 10018_chained_drill.jpg |
| 10019 | Chained Doctor Shock | b | 4 | 45 | 411 | `10019_chained_doctor_shock` | 10019_chained_doctor_shock.swf | 10019_chained_doctor_shock.jpg |
| 10020 | Play Social Empires | b | 4 | 45 | 411 | `10020_cross_se` | 10020_cross_se.swf | 10020_cross_se.jpg |
| 10021 | Chained Professional Chest | b | 4 | 45 | 411 | `10021_chained_professional_pack` | 10021_chained_professional_pack.swf | 10021_chained_professional_pack.jpg |
| 10022 | Chained Red Mercury Dragon | b | 4 | 45 | 411 | `10022_chained_dragon_metalic_red` | 10022_chained_dragon_metalic_red.swf | 10022_chained_dragon_metalic_red.jpg |
| 10023 | Chained 90% Bonus | b | 4 | 45 | 411 | `10023_chained_90_bonus` | 10023_chained_90_bonus.swf | 10023_chained_90_bonus.jpg |
| 10024 | Chained Super Pack | b | 4 | 45 | 411 | `10024_chained_super_pack` | 10024_chained_super_pack.swf | 10024_chained_super_pack.jpg |
| 10025 | Chained Cyber Samurai Mech | b | 4 | 45 | 411 | `10025_chained_cyber_samurai_mech` | 10025_chained_cyber_samurai_mech.swf | 10025_chained_cyber_samurai_mech.jpg |
| 10026 | Chained 2-Gun Exobot | b | 4 | 45 | 411 | `10026_chained_2_gun_exobot` | 10026_chained_2_gun_exobot.swf | 10026_chained_2_gun_exobot.jpg |
| 10027 | Chained Dark Ether Messiah | b | 4 | 45 | 411 | `10027_chained_darck_ether_messiah` | 10027_chained_darck_ether_messiah.swf | 10027_chained_darck_ether_messiah.jpg |
| 10028 | Chained 95% Bonus | b | 4 | 45 | 411 | `10028_chained_95_bonus` | 10028_chained_95_bonus.swf | 10028_chained_95_bonus.jpg |
| 10029 | Chained Attack Pack | b | 4 | 45 | 411 | `10029_chained_attack_pack` | 10029_chained_attack_pack.swf | 10029_chained_attack_pack.jpg |
| 10030 | Chained Forge Dragon | b | 4 | 45 | 411 | `10030_chained_forge_dragon` | 10030_chained_forge_dragon.swf | 10030_chained_forge_dragon.jpg |
| 10031 | Chained Converter Wizard | b | 4 | 45 | 411 | `10031_chained_enemy_converter` | 10031_chained_enemy_converter.swf | 10031_chained_enemy_converter.jpg |
| 10032 | Chained Bonus + Red Mercury Draggy | b | 4 | 45 | 411 | `10032_chained_bonus_red_mercury_draggy` | 10032_chained_bonus_red_mercury_draggy.swf | 10032_chained_bonus_red_mercury_draggy.jpg |
| 10033 | Chained Swamp Monster | b | 4 | 45 | 411 | `10033_chained_nebula_monster` | 10033_chained_nebula_monster.swf | 10033_chained_nebula_monster.jpg |
| 10034 | Chained Hercules Mech | b | 4 | 45 | 411 | `10034_chained_hercules_mech` | **— MISSING —** | **— MISSING —** |
| 10035 | Chained Double Cannon Mech | b | 4 | 45 | 411 | `10035_chained_double_cannon_mech` | 10035_chained_double_cannon_mech.swf | 10035_chained_double_cannon_mech.jpg |
| 10036 | Chained Laser Blade Automech | b | 4 | 45 | 411 | `10036_chained_laser_blade_automech` | 10036_chained_laser_blade_automech.swf | 10036_chained_laser_blade_automech.jpg |
| 10037 | Chained Burning Slayer | b | 4 | 45 | 411 | `10037_chained_red_slayer` | 10037_chained_red_slayer.swf | 10037_chained_red_slayer.jpg |
| 10038 | Chained Karateka Gunner | b | 4 | 45 | 411 | `10038_chained_karateka_gunner` | 10038_chained_karateka_gunner.swf | 10038_chained_karateka_gunner.jpg |
| 10039 | Chained Demolition Pack | b | 4 | 45 | 411 | `10039_chained_demolition_pack` | 10039_chained_demolition_pack.swf | 10039_chained_demolition_pack.jpg |
| 10040 | Chained Half Price Party Weekend | b | 4 | 45 | 411 | `10040_chained_half_party_price_party_weekend` | 10040_chained_half_party_price_party_weekend.swf | **— MISSING —** |
| 10041 | Chained Prime Automech | b | 4 | 45 | 411 | `10041_chained_optimus_prime` | 10041_chained_optimus_prime.swf | 10041_chained_optimus_prime.jpg |
| 10042 | Chained Revolution Bonus 99 | b | 4 | 45 | 411 | `10042_chained_revolution_bonus_99` | 10042_chained_revolution_bonus_99.swf | 10042_chained_revolution_bonus_99.jpg |
| 10043 | Chained Retaliator Pack | b | 4 | 45 | 411 | `10043_chained_retaliator_pack` | 10043_chained_retaliator_pack.swf | 10043_chained_retaliator_pack.jpg |
| 10044 | Chained Big Razor Mech | b | 4 | 45 | 411 | `10044_chained_big_razor_mech` | 10044_chained_big_razor_mech.swf | 10044_chained_big_razor_mech.jpg |
| 10045 | Chained 150% Extra Cash | b | 4 | 45 | 411 | `10045_chained_150_extra_cash` | 10045_chained_150_extra_cash.swf | 10045_chained_150_extra_cash.jpg |
| 10046 | Chained 40% Off | b | 4 | 45 | 411 | `10046_chained_40_off` | 10046_chained_40_off.swf | 10046_chained_40_off.jpg |
| 10047 | Chained Destruction Pack | b | 4 | 45 | 411 | `10047_chained_destruction_pack` | 10047_chained_destruction_pack.swf | 10047_chained_destruction_pack.jpg |
| 10048 | Play Dragon City | b | 4 | 45 | 411 | `10048_cross_dc` | **— MISSING —** | **— MISSING —** |
| 10049 | Chained Dark Ether Messiah + Dual Blade Automech  | b | 4 | 45 | 411 | `10049_chained_dark_ether_messiah_dual_blade_automech` | 10049_chained_dark_ether_messiah_dual_blade_automech.swf | 10049_chained_dark_ether_messiah_dual_blade_automech.jpg |
| 10050 | Chained Spartan Warrior | b | 4 | 45 | 411 | `10050_chained_spartan_warrior` | 10050_chained_spartan_warrior.swf | 10050_chained_spartan_warrior.jpg |
| 10051 | Chained Assault Pack | b | 4 | 45 | 411 | `10051_chained_assault_pack` | 10051_chained_assault_pack.swf | 10051_chained_assault_pack.jpg |
| 10052 | Chained Proto Winged Mech | b | 4 | 45 | 411 | `10052_chained_widged_transformer` | 10052_chained_widged_transformer.swf | 10052_chained_widged_transformer.jpg |
| 10053 | Chained Spider Bot | b | 4 | 45 | 411 | `10053_chained_spider_bot` | 10053_chained_spider_bot.swf | 10053_chained_spider_bot.jpg |
| 10054 | Chained 100% Bonus + Draggy | b | 4 | 45 | 411 | `10054_100_bonus_draggy` | 10054_100_bonus_draggy.swf | 10054_100_bonus_draggy.jpg |
| 10055 | Chained Ambush Chest | b | 4 | 45 | 411 | `10055_chained_ambush_chest` | 10055_chained_ambush_chest.swf | 10055_chained_ambush_chest.jpg |
| 10056 | Chained Pharaoh Warrior Mech  | b | 4 | 45 | 411 | `10056_chained_egyptian_warrior_mech` | 10056_chained_egyptian_warrior_mech.swf | 10056_chained_egyptian_warrior_mech.jpg |
| 10057 | Chained Arachnid Mech | b | 4 | 45 | 411 | `10057_chained_transformer_aracnid` | 10057_chained_transformer_aracnid.swf | 10057_chained_transformer_aracnid.jpg |
| 10058 | Chained 95% Bonus Cash + Fire Karateka | b | 4 | 45 | 411 | `10058_chained_95bonus_fire_karateka` | 10058_chained_95bonus_fire_karateka.swf | 10058_chained_95bonus_fire_karateka.jpg |
| 10059 | Chained 35% Bonus Cash + Blue Steel Draggy | b | 4 | 45 | 411 | `10059_chained_35bonus_blue_steel_draggy` | 10059_chained_35bonus_blue_steel_draggy.swf | 10059_chained_35bonus_blue_steel_draggy.jpg |
| 10060 | Chained Storm Pack | b | 4 | 45 | 411 | `10060_chained_storm_pack` | 10060_chained_storm_pack.swf | 10060_chained_storm_pack.jpg |
| 10061 | Chained Black Brutus Mech | b | 4 | 45 | 411 | `10061_chained_black_brutus_mech` | 10061_chained_black_brutus_mech.swf | 10061_chained_black_brutus_mech.jpg |
| 10062 | Chained 2-Head Frostfire Dragon | b | 4 | 45 | 411 | `10062_chained_2head_frostfire_dragon` | 10062_chained_2head_frostfire_dragon.swf | 10062_chained_2head_frostfire_dragon.jpg |
| 10063 | Chained Multi Morpher | b | 4 | 45 | 411 | `10063_chained_multi_morph` | 10063_chained_multi_morph.swf | 10063_chained_multi_morph.jpg |
| 10064 | Chained Watcher Hero | b | 4 | 45 | 411 | `10064_chained_cyclop_soldier` | 10064_chained_cyclop_soldier.swf | 10064_chained_cyclop_soldier.jpg |
| 10065 | Chained Combat Chest | b | 4 | 45 | 411 | `10065_chained_combat_chest` | 10065_chained_combat_chest.swf | 10065_chained_combat_chest.jpg |
| 10066 | Chained Avenger Mech | b | 4 | 45 | 411 | `10066_chained_avenger_mech` | 10066_chained_avenger_mech.swf | 10066_chained_avenger_mech.jpg |
| 10067 | Chained 60% OFF + Electric Draggy | b | 4 | 45 | 411 | `10067_chained_60off_electric_draggy` | 10067_chained_60off_electric_draggy.swf | 10067_chained_60off_electric_draggy.jpg |
| 10068 | Chained 125% Bonus + Dark Ether Drone | b | 4 | 45 | 411 | `10068_chained_125off_dark_messiah_drone` | 10068_chained_125off_dark_messiah_drone.swf | 10068_chained_125off_dark_messiah_drone.jpg |
| 10069 | Chained Golden Slayer + M. Cannon Mech | b | 4 | 45 | 411 | `10069_chained_goldenslayer_cannonmech` | 10069_chained_goldenslayer_cannonmech.swf | 10069_chained_goldenslayer_cannonmech.jpg |
| 10070 | Chained 75% Bonus | b | 4 | 45 | 411 | `10070_chained_75bonus` | 10070_chained_75bonus.swf | 10070_chained_75bonus.jpg |
| 10071 | Chained Executioner Mech | b | 4 | 45 | 411 | `10071_chained_executioner_mech` | 10071_chained_executioner_mech.swf | 10071_chained_executioner_mech.jpg |
| 10072 | Chained Battle Chest | b | 4 | 45 | 411 | `10072_chained_battle_chest` | 10072_chained_battle_chest.swf | 10072_chained_battle_chest.jpg |
| 10073 | Chained 125% Extra Cash | b | 4 | 45 | 411 | `10073_chained_125_extra_cash` | 10073_chained_125_extra_cash.swf | 10073_chained_125_extra_cash.jpg |
| 10074 | Chained Killer Chest | b | 4 | 45 | 411 | `10074_chained_killer_chest` | 10074_chained_killer_chest.swf | 10074_chained_killer_chest.jpg |
| 10075 | Chained Godzilla Mech | b | 4 | 45 | 411 | `10075_chained_godzillaMech` | 10075_chained_godzillaMech.swf | 10075_chained_godzillaMech.jpg |
| 10076 | Chained 110% Bonus | b | 4 | 45 | 411 | `10076_chained_110Bonus` | 10076_chained_110Bonus.swf | 10076_chained_110Bonus.jpg |
| 10077 | Chained King Kong Mech | b | 4 | 45 | 411 | `10077_chained_kingKongMech` | 10077_chained_kingKongMech.swf | 10077_chained_kingKongMech.jpg |
| 10078 | Dragon City | b | 4 | 45 | 411 | `10078_dragonCity_cross` | 10078_dragonCity_cross.swf | 10078_dragonCity_cross.jpg |
| 10079 | Chained Power Bot Chest | b | 4 | 45 | 411 | `10079_chained_powerBotChest` | 10079_chained_powerBotChest.swf | 10079_chained_powerBotChest.jpg |
| 10080 | Chained Dark Ether M. + Laser B. Automech | b | 4 | 45 | 411 | `10080_chained_darkEtherM_LaserBAutomech` | 10080_chained_darkEtherM_LaserBAutomech.swf | 10080_chained_darkEtherM_LaserBAutomech.jpg |
| 10081 | Chained Gamera Mech | b | 4 | 45 | 411 | `10081_chained_gameraMech` | 10081_chained_gameraMech.swf | 10081_chained_gameraMech.jpg |
| 10082 | Chained Mecha Dragons Chest | b | 4 | 45 | 411 | `10082_chained_mechaDragonsChest` | 10082_chained_mechaDragonsChest.swf | 10082_chained_mechaDragonsChest.jpg |
| 10083 | Chained Double Cannon M. + Big Razor M. | b | 4 | 45 | 411 | `10083_chained_doubleCannonM_bigRazorM` | 10083_chained_doubleCannonM_bigRazorM.swf | 10083_chained_doubleCannonM_bigRazorM.jpg |
| 10084 | Chained 60% Bonus | b | 4 | 45 | 411 | `10084_chained_60bonus` | 10084_chained_60bonus.swf | 10084_chained_60bonus.jpg |
| 10085 | Chained Z Project Mech | b | 4 | 45 | 411 | `10085_chained_zProjectMech` | 10085_chained_zProjectMech.swf | 10085_chained_zProjectMech.jpg |
| 10086 | Chained Full Metal Chest | b | 4 | 45 | 411 | `10086_chained_fullMetalChest` | 10086_chained_fullMetalChest.swf | 10086_chained_fullMetalChest.jpg |
| 10087 | Chained Great Shogun Mech + Brutus Mech | b | 4 | 45 | 411 | `10087_chained_greatShogunMech_brutusMech` | 10087_chained_greatShogunMech_brutusMech.swf | 10087_chained_greatShogunMech_brutusMech.jpg |
| 10088 | Chained Massive Gunner Mech | b | 4 | 45 | 411 | `10088_chained_massiveGunnerMech` | 10088_chained_massiveGunnerMech.swf | 10088_chained_massiveGunnerMech.jpg |
| 10089 | Chained x2,5 Cash Offer | b | 4 | 45 | 411 | `10089_chained_x2_5CashOffer` | 10089_chained_x2_5CashOffer.swf | 10089_chained_x2_5CashOffer.jpg |
| 10090 | Chained Fire Godzilla Mech | b | 4 | 45 | 411 | `10090_chained_fireGodzillaMech` | 10090_chained_fireGodzillaMech.swf | 10090_chained_fireGodzillaMech.jpg |

---

## 5. FX catalogue — `assets/fx/` (205 files)

### 5.1 How FX are wired

* **Definition table:** `scripts/battle/projectiles/ProjectileDefinition.as` holds 219 constants; 205 of them
  name a file that exists in `assets/fx/` (see §5.4 for the 14 that do not).
* **Loading:** `managers/ProjectileManager.as:141` → `Base.Main.apfx + "fx/" + <id> + ".swf"`, with a
  `LoaderContext` on `ApplicationDomain.currentDomain` so the SWF’s exported symbol is visible to the client.
* **The symbol name equals the file base name** — verified with JPEXS FFDec: `sprites/0001_house_1_m.swf` exports
  `SymbolClass 4;"0001_house_1_m"`, and the client does `getDefinitionByName(img_name)`. The same convention
  holds for fx (`Class(loaderInfo.applicationDomain.getDefinition(<fx id>))`).
* **A projectile is a triple:** `projectileID` (the `p.` file that flies) + `blastID` (the `b.` file at impact)
  + optional `trailID`. The 16 reusable templates are:

| Template | projectile | blast | trail |
|---|---|---|---|
| `ProjectileDefinition.ALIEN_FLEGMA` | `p.alienFlegma` | `b.alienFlegma` | — |
| `ProjectileDefinition.CANNON` | `p.cannon` | `b.earth` | `b.smoke` |
| `ProjectileDefinition.CANNON_SMALL` | `p.cannonSmall` | `b.earth` | `b.smoke` |
| `ProjectileDefinition.EGG` | `p.egg` | `—` | — |
| `ProjectileDefinition.ENERGY_BOMB` | `p.forgelordball` | `b.earth` | — |
| `ProjectileDefinition.FIRE_BALL` | `p.fireBall` | `b.earth` | — |
| `ProjectileDefinition.GRENADE` | `p.grenade` | `b.earthBig` | — |
| `ProjectileDefinition.LASER_BURST` | `p.laserBlue` | `b.bullet2` | — |
| `ProjectileDefinition.MACHINEGUN` | `p.bullet` | `b.bullet2` | — |
| `ProjectileDefinition.MACHINEGUN_BIG` | `p.bulletBig` | `b.bullet2` | — |
| `ProjectileDefinition.MACHINEGUN_HEAVY` | `p.bulletBig` | `b.bullet2` | — |
| `ProjectileDefinition.MISSILE` | `p.missileM` | `b.missile` | `b.smokeSmall` |
| `ProjectileDefinition.MISSILE_BIG` | `p.bigmissile` | `b.earthBig` | `b.smokeSmall` |
| `ProjectileDefinition.MOLOTOV` | `p.molotov` | `b.bazooka` | — |
| `ProjectileDefinition.ORC_ROCKET` | `p.orcRocket` | `b.bazooka2` | `b.smokeSmall` |
| `ProjectileDefinition.ROCKET` | `p.rocketM` | `b.bazooka2` | `b.smoke` |

### 5.2 The 205 fx files grouped by role

**Projectile — bullet / tracer / shell (25)**

`p.bullet`, `p.bulletBig`, `p.bulletBigRed`, `p.bulletBigEnemy`, `p.bulletEnemy`, `p.bulletRifle`, `p.bulletAir`, `p.bulletAirBig`, `p.cannon`, `p.cannonSmall`, `p.arrow`, `p.avatarArrow`, `p.greenArrow`, `p.grenade`, `p.grenade2`, `p.fuseBomb`, `p.tnt`, `p.metallicBall`, `p.redMetalBall`, `p.yellowMetalBall`, `p.blueLaserBullet`, `p.yellowLaserBullet`, `p.yellowRedLaserBullet`, `p.avatarlance`, `p.espadazo`

**Projectile — laser / beam / ray (61)**

`p.laser`, `p.laserBeam`, `p.laserBeamBlue`, `p.laserBeamBlueFat`, `p.laserBlue`, `p.laserBlueBig`, `p.laserBlueSlim`, `p.laserBlueSmall`, `p.laserRed`, `p.laserRedViking`, `p.laserYellow`, `p.laserdrone`, `p.laserMassiveDrone`, `p.blueLaser`, `p.blueLaserBeamThin`, `p.blueLaserShot`, `p.bluePowerLaser`, `p.bluePlasmaBolt`, `p.bluePlasmaBoltLarge`, `p.blueRay`, `p.blueElectricRay`, `p.blueBeam`, `p.blueCycloneBall`, `p.beamBlue`, `p.beamBlueElectric`, `p.beamLab`, `p.beamSpatial`, `p.blackDragonBeam`, `p.chemicalLaser`, `p.chemicalLaserBig`, `p.curvesBeam`, `p.electricBeam`, `p.fireBeam`, `p.fireBeamLarge`, `p.forgelordbeam`, `p.greenBeam`, `p.healBeam`, `p.iceBeam`, `p.overseerBeam`, `p.readBeamLaserCone`, `p.readBeamLine`, `p.readUnformedBeam`, `p.redBallLaser`, `p.redBeam`, `p.redElectricBeam`, `p.spatialBigLaser`, `p.spectreRay`, `p.sunLaser`, `p.teslaRay`, `p.ufoLaser`, `p.ultraLaserBeam`, `p.urbanBeam`, `p.yellowBeam`, `p.yellowElectricBeam`, `p.yellowElectricLaserBeam`, `p.yellowLaserBall`, `p.yellowMetalBeam`, `p.yellowMetallicBeam`, `p.yellowPlasma`, `p.yellowUnformedBeam`, `p.orangeMetalBeam`

**Projectile — missile / rocket / bomb (13)**

`p.missileM`, `p.missileS`, `p.bigmissile`, `p.slimMissile`, `p.rocketM`, `p.blueRocket`, `p.redMissile`, `p.tankMissile`, `p.orcRocket`, `p.overseerMissiles`, `p.stalkerBomb`, `p.redElectricBomb`, `p.nuclear`

**Projectile — energy ball / plasma (16)**

`p.energyBall`, `p.energyBall2`, `p.energyBallBlue`, `p.energyBallBlueBig`, `p.megaEnergyBall`, `p.pureEnergyBall`, `p.forgelordball`, `p.blueBall`, `p.blueWaves`, `p.blackDragonBall`, `p.dragonFireBall`, `p.greenYellowBall`, `p.sunBall`, `p.yamatoBall`, `p.bigElectricBall`, `p.electricBall`

**Projectile — elemental (fire / ice / acid / chemical) (28)**

`p.fire`, `p.fireBall`, `p.fireBallSmall`, `p.fireBig`, `p.fireBlue`, `p.blueFlame`, `p.blueFlamingRock`, `p.acidBlue`, `p.alienFlegma`, `p.molotov`, `p.electric`, `p.water`, `p.lightningBlue`, `p.bladestormFireBall`, `p.redFireBall`, `p.yellowRedElectricBall`, `p.hadoken`, `p.hadoken_karateka`, `p.orcKnife`, `p.egg`, `p.nebularEgg`, `p.nebularSpear`, `p.spatialSpear`, `p.spatialSword`, `p.spiderNet`, `p.zProjectHand`, `p.zProjectHand2`, `p.blueAnvilShoot`

**Blast — explosion / impact (56)**

`b.bazooka`, `b.bazooka2`, `b.bazookaSmall`, `b.bullet2`, `b.earth`, `b.earthBig`, `b.missile`, `b.smoke`, `b.smokeSmall`, `b.ice`, `b.fireBomb`, `b.fireExplosion`, `b.largeFlames`, `b.chemicalBlast`, `b.chemicalBlastBig`, `b.acidBlue`, `b.alienFlegma`, `b.grenade2`, `b.grenade2_verde`, `b.blueExplosion`, `b.blueMetalBlast`, `b.orangeMetalBeamBlast`, `b.yellowMetalBeamBlast`, `b.redBeamBlast`, `b.yellowBeamBlast`, `b.blueBeam`, `b.readBeamLine`, `b.readBeamLaserCone`, `b.spatialBigBlast`, `b.blueSpatial`, `b.plasmaExplosion`, `b.pureEnergyBall`, `b.forgelordballblast`, `b.nuclear`, `b.nuclearMushrom`, `b.electrical`, `b.electricalExplosion`, `b.electricalYellow`, `b.electrical_verde`, `b.electrical_verde2`, `b.bigElectrical`, `b.electricMine`, `b.yellowLightning`, `b.laser`, `b.laserBlue`, `b.laserYellow`, `b.targetLethalBeam`, `b.stalkerBlast`, `b.overseerMissilesBlast`, `b.rift`, `b.tempest`, `b.servoWorm`, `b.skorpion`, `b.spiderNet`, `b.redFireBall`, `b.yellowLaser`

**Misc — persistent area / aura (6)**

`m.acidFloor`, `m.acidRain`, `m.blueShield`, `m.cristalRain`, `m.rayRain`, `m.satelliteLaser`

> The grouping above is an editorial classification by filename keyword. The **authoritative** classification is
> the `p.` / `b.` / `m.` prefix (143 / 56 / 6), which is what the client uses.

### 5.3 FX → units / attacks (from the AS3)

The mapping is derived from two authoritative places in the AS3:

* `scripts/core/isoengine/delegates/DelegatesManager.as` — 402 `registerDelegate(<Delegate>, {pDef: …}, Constants.ID_*)`
  calls bind a *weapon template* (and therefore its `p.`/`b.` fx) to specific item ids;
* the per-unit delegate implementation files in `scripts/core/isoengine/delegates/units/*.as` — these add the
  *special-attack* fx (e.g. `LiquidMechDelegate.as:195` spawns `MISC_ACID_RAIN`).

**202 of the 205 fx files resolve to at least one concrete item id.** The remaining 3:

| fx | explanation |
|---|---|
| `p.bulletEnemy` | the *enemy-coloured* machinegun bullet. `ProjectileManager.as:78` does `ProjectileDefinition.MACHINEGUN.setEnemyProjectileID(P_BULLET_ENEMY)` — i.e. it is the same machinegun template, recoloured, so it inherits every machinegun unit. |
| `p.bulletBigEnemy` | same, for `MACHINEGUN_BIG` (`ProjectileManager.as:79`). |
| `p.espadazo` | `BeamDefinition.BEAM_ESPADAZO` — bound to `TransformerSwordDelegate` (Transformer Sword) and `GreatWarriorDelegate` (Great Shogun Mech) at `DelegatesManager.as:1538,1560`. |

The full fx → delegate → item mapping (all 205):

| fx file | owning delegate class(es) | item(s) |
|---|---|---|
| `b.acidBlue.swf` | LiquidMechDelegate | Liquid Mech  |
| `b.alienFlegma.swf` | ProjectileDelegate, ProjectileTowerDelegate | Alien Turret I, Alien Turret II, Spider Turret I, Spider Turret II, Venom Spider, Small Alien, Poison Spider, Acid Alien |
| `b.bazooka.swf` | EvilSlaughtererDelegate, ProjectileDelegate, RobotHunterDelegate | Blue Steel Draggy, Robot Hunter, id1351, id1352 |
| `b.bazooka2.swf` | BlackDraggyDelegate, BushwackerDelegate, DoubleProjectileDelegate, DoubleRocketStealthDelegate, HammerheadDelegate, MetalDraggyDelegate, MultiShotDelegate, ProjectileDelegate, RedSpinnerDelegate, SpatialCruiserAirship | Aircraft, Aircraft II, Aircraft III, Stealth Fighter, Bazooka IV, Bazooka V, Antiaircraft battery, Metal Draggy, Aircraft IV, Aircraft V, F-117, Red Spinner, Camu Draggy, Black Draggy, Space Elf Cruiser, id1358, id1364 |
| `b.bazookaSmall.swf` | BushwackerDelegate, MultiShotDroneDelegate, ProjectileDelegate, RobotHunterDelegate, SwatSoldierDelegate, UrbanBusterDelegate | Red Draggy, Robot Hunter, S.W.A.T. Soldier, Red Mercury Draggy, S.W.A.T. Soldier, 2-Head Frostfire Draggy, Gamera Drone, id1358, id1408 |
| `b.bigElectrical.swf` | DoctorShockDelegate | Doctor Shock |
| `b.blueBeam.swf` | AgamemnonFortressDelegate, CycloneMechDelegate, HavocDelegate, MarauderBattleChasisDelegate, ProjectileDelegate, ReaperDelegate, SkorpionFortressDelegate, SuperfulcrumArmorDelegate, TempestMechDelegate, TyphoonServodragonDelegate | id1337, id1343, id1355, id1362, id1367, id1375, id1382, id1383, id1384, id1410 |
| `b.blueExplosion.swf` | MarauderBattleChasisDelegate | id1367 |
| `b.blueMetalBlast.swf` | ElectricDragonDroneDelegate, ProjectileDelegate, UltraBotDelegate | Ultra-Mech Drone, Nemesis Core, Nemesis Drone, Electric Draggy |
| `b.blueSpatial.swf` | ExecutionerMechDelegate, TransformerAracnidDelegate | Arachnid Mech, Arachnid Drone, Executioner Mech  |
| `b.bullet2.swf` | AgamemnonFortressDelegate, AndromedaCombatDroidDelegate, AndromedaCombatStarShipDelegate, AndromedaPrivateDelegate, AnvilPatternMechDelegate, AtomicBonecrushaDelegate, BismarkMechDelegate, BladeStormMechDelegate, BlueAnvilDelegate, BombardierDroneDelegate, BombardierMechDelegate, BonecrushaDelegate, BrawlerDelegate, BunkerDelegate, BushwackerDelegate, CannonMechBotDelegate, CentaurDelegate, CrimsonCenturionDelegate, CrusaderPriestDelegate, CycloneBattlesuitDelegate, DoubleCannonMechDelegate, DoubleMachinegunDelegate, DoubleMachinegunTowerDelegate, DoubleShotgunDelegate, DragonMechDelegate, DreadnoughtDelegate, DroneMaster2Delegate, DroneMasterDelegate, ElephantRiderDelegate, EnemyConverterPriestDelegate, ErradicatorDelegate, ExecutionerMechDelegate, FireGameraDelegate, GiantWalkerDelegate, GlaiveStormMechDelegate, GuardianDelegate, GunBotDelegate, HammerheadDelegate, HarvesterDelegate, HavocDelegate, HerculesMatrixDelegate, HerculesMechDelegate, IgnitionDelegate, IntruderDelegate, KaratekaDelegate, KaratekaGunnerDelegate, KnifeThrowerOrcDelegate, KnightExosuitDelegate, KnuckledraggerDelegate, MachinegunDelegate, MachinegunOrcDelegate, MachinegunTowerDelegate, MarauderBattleChasisDelegate, MassiveGunnerMechDelegate, MultiMorphDelegate, MultiShotDroneDelegate, NebularBlueBicopterDelegate, NebularSniperDelegate, OptimusPrimeBotDelegate, OrcRobot2Delegate, PauldronMechDelegate, ProjectileDelegate, PunisherDelegate, RamboDelegate, ReaperDelegate, RedBaronDelegate, ReptileGunDelegate, RobotHunterDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, SharkbiteDelegate, ShredderMechDelegate, SkorpionFortressDelegate, SkylanderDelegate, SpatialAirshipDelegate, SpatialArcherDelegate, SpatialCruiserAirship, SpatialElfDinoRiderDelegate, SpatialElfGunnerDelegate, SpatialElfHealerDelegate, SpatialExplorationModuleDelegate, SpatialPaladinDelegate, SpatialPriestDelegate, SpatialWingedElfPaladinDelegate, SpecialBunkerDelegate, SpectreMechDelegate, SpiderBotDelegate, SplinterMechDelegate, StalkerMechDelegate, StampedeMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, SuperfulcrumArmorDelegate, SwatSoldierDelegate, TarantulaDelegate, TransformerArcherDelegate, TwoGunExobotDelegate, UltraBotDelegate, UrbanBusterDelegate, VikingCopterDelegate, VikingLaserDelegate, VikingSniperDelegate, VortexDelegate, WarlordDelegate, WingedTransformerDelegate, XtremeRetaliatorDelegate, YamatoMechDelegate | Turret I, Turret III, Bunker I, Bunker II, Bunker III, Mega Bunker, Turret II, Turret VI, Ork Turret II, Enemy Ork Turret I, Viking Turret I, Viking Turret II, Nebular Turret, Soldier, General Scarlett, APC, Ms. Evilia, Evil Hannibal, Machine Gun Jeep, General Mike, Soldier II, Soldier III, Sergeant Megan, Helicopter, Helicopter II, Helicopter III, Machine Gun Jeep II, Machine Gun Jeep III, Mr. Cigar, UN Allied, Sergeant Jack, Double Gun Soldier, Scarface girl, Mr. Treat, Elephant rider, Soldier IV, Soldier V, GunBot, Helicopter IV, Helicopter V, Ranbo, Erradicator, Punisher Bot, Crusader Soldier, Jet Soldier, Motorized Soldier, Xtreme Retaliator, Dreadnought, Skylander, Giant Walker, Red Draggy, Blue Draggy, Red Baron, Gun Zoldier, Knife Throwa, Big Handsaw Ork, Orc Zoldier, Alpha Drone, Orc Knifethrower, Red Handsaw Ork, Crusader Priest, Viking Soldier, Viking Airship, Nemesis Core, Nemesis Drone, Viking Core Bot Drone, Rune Golem Drone, Viking Sniper, Ether Messiah Drone, Robot Hunter, Big Laser Viking, Fire Karateka, Dragonborn Mech, Dragonborn Drone, Silver Hercules, Viking Airship Outsider, Dual Blade Automech Drone, Black Belt Archer, Nebular Bicopter, Great Shogun Mech Drone, Massive Cannon Mech, S.W.A.T. Soldier, Nebular Sniper, Red Mercury Draggy, 2-Gun Exobot, Dark Ether Messiah Drone, Converter Wizard, Hercules Mech, Reptile Gun, Double Cannon Mech, Laser Blade Automech Drone, Karateka Gunner, Prime Automech, Big Razor Mech Drone, S.W.A.T. Soldier, Space Archer Elf, Space Airship Elf, Space Priest Elf, Space Paladin Elf, Space Elf Cruiser, Proto Winged Mech, Spider Bot, Multi Morpher, Space Healer Elf, Space Scouter Elf, Silver Gunner Elf, Dino Rider Elf, 2-Head Frostfire Draggy, Executioner Mech , Winged Paladin, Andromeda Private, Andromeda Combat Droid, Andromeda Spaceship, Gamera Drone, Massive Gunner Mech, id1307, id1309, id1313, id1315, id1317, id1319, id1321, id1327, id1329, id1330, id1333, id1334, id1339, id1341, id1347, id1349, id1353, id1354, id1355, id1356, id1358, id1360, id1362, id1364, id1367, id1368, id1370, id1372, id1375, id1379, id1381, id1382, id1385, id1388, id1390, id1392, id1393, id1394, id1398, id1399, id1400, id1408, id1410, id1412, id1413, id1414, id1416, id1417, id1418, id1419, id1421, id1422, id1424, id1428, id1430 |
| `b.chemicalBlast.swf` | ChemicalGunnerDelegate | id1396 |
| `b.chemicalBlastBig.swf` | ChemicalGunnerDelegate, CrimsonCenturionDelegate, PauldronMechDelegate, ProjectileDelegate | id1396, id1397, id1412, id1416 |
| `b.earth.swf` | AvatarArcherDelegate, AvatarSoldadoDelegate, BombardierMechDelegate, BuggyDelegate, BushwackerDelegate, CycloneMechDelegate, DoubleProjectileDelegate, ForgelordDelegate, GuardianDelegate, HellFireMechDelegate, MegaFireBotDelegate, MortarDelegate, MultiShotTowerDelegate, OrcoHelicopterDelegate, OrcoRobotDelegate, ProjectileDelegate, RavenMechDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, ShredderMechDelegate, SpatialHorsemanDelegate, SteelWandererMechDelegate, SuperfulcrumArmorDelegate, TempestMechDelegate, ThrowingTowerDelegate, VikingMotoSquadDelegate, YamatoMechDelegate | Cannon Turret, Turret V, Ork Turret I, Enemy Ork Turret II, Bazooka, Bazooka II, Bazooka III, Double Bazooka, Double Bazooka Jeep, Dominion Tank, Mortar Thrower, Bazooka Soldier, Molotov Kopta, Horned Badass, War Buggy, Ork Kopta, Horned Beast Ork, Viking Tank, Viking Bazooka, Viking MotoSquad, Hyper Blazer, Hyper Blazer Drone, Nebular Spearman, Nebular Archer, Nebular Dragon Rider Draggy, Nebular Dragon Knight Draggy, Forge Dragon Draggy, Space Knight Elf, id1311, id1329, id1331, id1333, id1335, id1337, id1339, id1341, id1343, id1347, id1348, id1355, id1358, id1385, id1388 |
| `b.earthBig.swf` | HellFireMechDelegate, HerculesMechDelegate, MetallicRedDragonDelegate, ProjectileDelegate, SpatialCruiserAirship, SpatialElfGunnerDelegate, SwatSoldierDelegate, ThrowingTowerDelegate, TransformerAracnidDelegate | Ork Turret I, Enemy Ork Turret II, Demolition Tank, S.W.A.T. Soldier, Red Mercury Dragon, Red Mercury Draggy, Hercules Mech, S.W.A.T. Soldier, Space Elf Cruiser, Arachnid Mech, Arachnid Drone, Silver Gunner Elf, id1311 |
| `b.electricMine.swf` | GuardianDelegate, ProximityMineDelegate | id1359, id1388 |
| `b.electrical.swf` | CrusherMonarchDelegate, ElectricTowerDelegate, RedDragonDelegate, UfoDelegate | Tesla Turret, Space Elf Turret, Blue Draggy, Blue Dragon, UFO, id1325 |
| `b.electricalExplosion.swf` | SpectreMechDelegate | id1319 |
| `b.electricalYellow.swf` | GoldenGolemDelegate, LaboratoryDelegate | Mind Control Laboratory, Golden Golem |
| `b.electrical_verde.swf` | MassiveGunnerMechDelegate | Massive Gunner Mech |
| `b.electrical_verde2.swf` | MassiveGunnerMechDelegate | Massive Gunner Mech |
| `b.fireBomb.swf` | AndromedaCombatStarShipDelegate, BlackHoleDelegate, CrusherMonarchDelegate, IntruderDelegate, MassiveGunnerMechDelegate, ReaperDelegate, ServowormDelegate, StalkerMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, TarantulaDelegate, TransformerAracnidDelegate, VortexDelegate, WingedTransformerDelegate, ZProjectMechDelegate | Proto Winged Mech, Arachnid Mech, Arachnid Drone, Andromeda Spaceship, Z Project Mech, Massive Gunner Mech, id1321, id1325, id1327, id1341, id1345, id1375, id1377, id1424, id1428, id1430 |
| `b.fireExplosion.swf` | FireGameraDelegate | id1392 |
| `b.forgelordballblast.swf` | ForgelordDelegate | id1331 |
| `b.grenade2.swf` | SwatSoldierDelegate | S.W.A.T. Soldier, S.W.A.T. Soldier |
| `b.grenade2_verde.swf` | MassiveGunnerMechDelegate | Massive Gunner Mech |
| `b.ice.swf` | DoubleProjectileDelegate | Forge Dragon Draggy |
| `b.largeFlames.swf` | HellFireMechDelegate | id1311 |
| `b.laser.swf` | BlackHoleDelegate, DoubleProjectileTowerDelegate, MultiShotDroneDelegate | Laser Turret, Andromeda Turret, id1318, id1377 |
| `b.laserBlue.swf` | AvatarArcherDelegate, AvatarSoldadoDelegate, CannonMechBotDelegate, DoubleCannonMechDelegate, DroneDelegate, ExecutionerMechDelegate, MultiShotDroneDelegate, OptimusPrimeBotDelegate, PhalanxDroneDelegate, ProjectileDelegate, SpatialHorsemanDelegate, TwoGunExobotDelegate, WingedTransformerDelegate | Nebular Spearman, Nebular Archer, Massive Cannon Mech, Massive Cannon Drone, Liquid Mech  Drone, 2-Gun Exobot, Cyber Samurai  Drone, Double Cannon Mech, Prime Automech, Prime Automech Drone, Space Knight Elf, Spartan Warrior Drone, Proto Winged Mech, Proto Winged Drone, Arachnid Drone, Pharaoh Mech Drone, Executioner Mech Drone, Executioner Mech , Godzilla Mech Drone, King Kong Drone, Z Project Drone, Massive Gunner Drone, Fire Godzilla Drone, id1308, id1310, id1312, id1314, id1316, id1320, id1322, id1324, id1326, id1328, id1332, id1336, id1338, id1340, id1342, id1344, id1346, id1350, id1357, id1374, id1376, id1378, id1386, id1387, id1389, id1391, id1395, id1401, id1404, id1411, id1415, id1423, id1425, id1429, id1431 |
| `b.laserYellow.swf` | GlaiveStormMechDelegate, MassiveGunnerMechDelegate, ProjectileDelegate, PunisherDelegate, RobotHunterDelegate | Punisher Bot, Robot Hunter, Massive Gunner Mech, id1307, id1361, id1369 |
| `b.missile.swf` | AndromedaCombatStarShipDelegate, BismarkMechDelegate, BlackHoleDelegate, BuggyDelegate, BushwackerDelegate, CentaurDelegate, CrusherMonarchDelegate, DoubleProjectileTowerDelegate, EvilSlaughtererDelegate, HammerheadDelegate, IntruderDelegate, LaboratoryDelegate, MassiveGunnerMechDelegate, MultiMorphDelegate, ProjectileDelegate, ReaperDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, ServowormDelegate, SpatialExplorationModuleDelegate, SpatialPlasmaStrikerDelegate, StalkerMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, SuperfulcrumArmorDelegate, TarantulaDelegate, TransformerAracnidDelegate, VortexDelegate, WingedTransformerDelegate, ZProjectMechDelegate | Turret IV, Dual-Rocket Turret, Mind Control Laboratory, Red Tank, Tank II, Tank III, Tank, Crusader Tank, Orc Tank, War Buggy, Basic Ork Tank, Xplosive Beast ATP, Orc Big Tank, Proto Winged Mech, Arachnid Mech, Arachnid Drone, Multi Morpher, Space Scouter Elf, Siege Striker, Andromeda Spaceship, Z Project Mech, Massive Gunner Mech, id1321, id1325, id1327, id1341, id1345, id1347, id1349, id1351, id1353, id1355, id1358, id1364, id1375, id1377, id1385, id1424, id1428, id1430 |
| `b.nuclear.swf` | BombardierMechDelegate, ShredderMechDelegate | id1329, id1333 |
| `b.nuclearMushrom.swf` | CentaurDelegate, ScarabDelegate | id1347, id1349 |
| `b.orangeMetalBeamBlast.swf` | BlackDragonDelegate, ElectricDragonDelegate, MetallicDragon2Delegate | Camu Metal Dragon, Camu Draggy, Black Dragon, Electric Dragon, Electric Draggy, Black Draggy |
| `b.overseerMissilesBlast.swf` | OverseerDelegate | id1406 |
| `b.plasmaExplosion.swf` | AgamemnonFortressDelegate | id1382 |
| `b.pureEnergyBall.swf` | ProjectileDelegate, ScarabDelegate | id1347, id1348 |
| `b.readBeamLaserCone.swf` | GameraMechDelegate | Gamera Mech |
| `b.readBeamLine.swf` | AndromedaPrivateDelegate, CyclopSoldierDelegate, GodzillaMechDelegate | Watcher Hero, Andromeda Private, Godzilla Mech |
| `b.redBeamBlast.swf` | AvengerMechDelegate, BahamutMetalDelegate, BlackDragonDelegate, JunkBotDelegate, MetallicDragonDelegate, ProjectileDelegate, RedDragonDelegate, SpatialDestructionWizardDelegate | Metal Draggy, Red Draggy, Red Dragon, Metal Dragon, Blue Steel Bahamut, Blue Steel Draggy, Black Dragon, Black Draggy, Steel Collector, Avenger Mech , Destruction Wizard, id1409 |
| `b.redFireBall.swf` | FireGodzillaMechDelegate | Fire Godzilla Mech |
| `b.rift.swf` | CrusaderBotDelegate, VikingRuneGolemDelegate | Crusader Bot, Rune Golem |
| `b.servoWorm.swf` | ServowormDelegate | id1345 |
| `b.skorpion.swf` | SkorpionFortressDelegate | id1410 |
| `b.smoke.swf` | BlackDraggyDelegate, BombardierMechDelegate, BuggyDelegate, DoubleProjectileDelegate, DoubleRocketStealthDelegate, MetalDraggyDelegate, MortarDelegate, MultiShotDelegate, MultiShotTowerDelegate, OrcoHelicopterDelegate, OrcoRobotDelegate, ProjectileDelegate, RavenMechDelegate, RedSpinnerDelegate, ShredderMechDelegate, SpatialCruiserAirship, SteelWandererMechDelegate, VikingMotoSquadDelegate | Cannon Turret, Turret V, Bazooka, Aircraft, Bazooka II, Bazooka III, Aircraft II, Aircraft III, Double Bazooka, Double Bazooka Jeep, Dominion Tank, Stealth Fighter, Mortar Thrower, Bazooka IV, Bazooka V, Antiaircraft battery, Bazooka Soldier, Metal Draggy, Aircraft IV, Aircraft V, F-117, Molotov Kopta, Horned Badass, Red Spinner, Camu Draggy, War Buggy, Ork Kopta, Horned Beast Ork, Viking Tank, Viking Bazooka, Viking MotoSquad, Black Draggy, Forge Dragon Draggy, Space Elf Cruiser, id1329, id1333, id1335, id1341 |
| `b.smokeSmall.swf` | AndromedaCombatStarShipDelegate, BismarkMechDelegate, BlackHoleDelegate, BuggyDelegate, BushwackerDelegate, CentaurDelegate, CrusherMonarchDelegate, DoubleProjectileTowerDelegate, EvilSlaughtererDelegate, HammerheadDelegate, IntruderDelegate, LaboratoryDelegate, MassiveGunnerMechDelegate, ProjectileDelegate, ReaperDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, ServowormDelegate, SpatialExplorationModuleDelegate, SpatialPlasmaStrikerDelegate, StalkerMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, SuperfulcrumArmorDelegate, TarantulaDelegate, ThrowingTowerDelegate, TransformerAracnidDelegate, VortexDelegate, WingedTransformerDelegate, ZProjectMechDelegate | Turret IV, Dual-Rocket Turret, Mind Control Laboratory, Ork Turret I, Enemy Ork Turret II, Red Tank, Tank II, Tank III, Tank, Demolition Tank, Crusader Tank, Orc Tank, War Buggy, Basic Ork Tank, Xplosive Beast ATP, Orc Big Tank, Proto Winged Mech, Arachnid Mech, Arachnid Drone, Space Scouter Elf, Siege Striker, Andromeda Spaceship, Z Project Mech, Massive Gunner Mech, id1321, id1325, id1327, id1341, id1345, id1347, id1349, id1351, id1353, id1355, id1358, id1364, id1375, id1377, id1385, id1424, id1428, id1430 |
| `b.spatialBigBlast.swf` | SpatialPriestDelegate, WingedTransformerDelegate | Space Priest Elf, Proto Winged Mech |
| `b.spiderNet.swf` | SpiderBotDelegate | Spider Bot |
| `b.stalkerBlast.swf` | CrimsonCenturionDelegate, PauldronMechDelegate, ProjectileDelegate, StalkerMechDelegate, UrbanBusterDelegate | id1321, id1408, id1412, id1416, id1417 |
| `b.targetLethalBeam.swf` | HavocDelegate | id1362 |
| `b.tempest.swf` | TempestMechDelegate | id1343 |
| `b.yellowBeamBlast.swf` | ElectricDragonDelegate, MetallicRedDragonDelegate | Electric Dragon, Electric Draggy, Red Mercury Dragon, Red Mercury Draggy |
| `b.yellowLaser.swf` | DoubleProjectileDelegate, ProjectileDelegate | Tank IV, Tank V |
| `b.yellowLightning.swf` | CrusaderBotDelegate | Crusader Bot |
| `b.yellowMetalBeamBlast.swf` | MetallicDragon2Delegate | Camu Metal Dragon, Camu Draggy |
| `m.acidFloor.swf` | LiquidMechDelegate | Liquid Mech  |
| `m.acidRain.swf` | LiquidMechDelegate | Liquid Mech  |
| `m.blueShield.swf` | CannonMechBotDelegate, DoubleCannonMechDelegate, KingKongMechDelegate, RobotHunterDelegate | Robot Hunter, Massive Cannon Mech, Double Cannon Mech, King Kong Mech |
| `m.cristalRain.swf` | SpatialDestructionWizardDelegate | Destruction Wizard |
| `m.rayRain.swf` | SpatialPriestDelegate | Space Priest Elf |
| `m.satelliteLaser.swf` | AnvilPatternMechDelegate | id1315 |
| `p.acidBlue.swf` | LiquidMechDelegate | Liquid Mech  |
| `p.alienFlegma.swf` | ProjectileDelegate, ProjectileTowerDelegate | Alien Turret I, Alien Turret II, Spider Turret I, Spider Turret II, Venom Spider, Small Alien, Poison Spider, Acid Alien |
| `p.arrow.swf` | SpatialArcherDelegate, TransformerArcherDelegate | Black Belt Archer, Space Archer Elf |
| `p.avatarArrow.swf` | AvatarArcherDelegate | Nebular Archer |
| `p.avatarlance.swf` | AvatarSoldadoDelegate | Nebular Spearman |
| `p.beamBlue.swf` | AgamemnonFortressDelegate, ProjectileDelegate, SkorpionFortressDelegate, TransformerAracnidDelegate, TyphoonServodragonDelegate | Arachnid Mech, Arachnid Drone, id1382, id1383, id1384, id1410 |
| `p.beamBlueElectric.swf` | CyberInquisitorDelegate, ExecutionerMechDelegate, HavocDelegate, MarauderBattleChasisDelegate, ReaperDelegate | Executioner Mech , id1362, id1367, id1375, id1420 |
| `p.beamLab.swf` | LaboratoryDelegate | Mind Control Laboratory |
| `p.beamSpatial.swf` | ProjectileDelegate | id1374 |
| `p.bigElectricBall.swf` | ScarabDelegate, SpatialElfGunnerDelegate | Silver Gunner Elf, id1347 |
| `p.bigmissile.swf` | ProjectileDelegate, SuperfulcrumArmorDelegate | Demolition Tank, id1355 |
| `p.blackDragonBall.swf` | BlackDragonDelegate | Black Dragon, Black Draggy |
| `p.blackDragonBeam.swf` | BlackDragonDelegate, BlackHoleDelegate, VortexDelegate | Black Dragon, Black Draggy, id1327, id1377 |
| `p.bladestormFireBall.swf` | BladeStormMechDelegate | id1317 |
| `p.blueAnvilShoot.swf` | BlueAnvilDelegate | id1398 |
| `p.blueBall.swf` | WingedTransformerDelegate | Proto Winged Mech |
| `p.blueBeam.swf` | CentaurDelegate, CycloneMechDelegate | id1337, id1349 |
| `p.blueCycloneBall.swf` | AgamemnonFortressDelegate, CycloneMechDelegate, GuardianDelegate, TempestMechDelegate | id1337, id1343, id1382, id1388 |
| `p.blueElectricRay.swf` | TempestMechDelegate | id1343 |
| `p.blueFlame.swf` | NebularMonsterRiderDelegate | Blazing Beast Rider |
| `p.blueFlamingRock.swf` | FireGameraDelegate | id1392 |
| `p.blueLaser.swf` | DragonMechDelegate, TwoGunExobotDelegate | Dragonborn Mech, 2-Gun Exobot |
| `p.blueLaserBeamThin.swf` | ZProjectMechDelegate | Z Project Mech |
| `p.blueLaserBullet.swf` | DragonMechDelegate, EnemyConverterPriestDelegate, ProjectileDelegate | Dragonborn Mech, Dragonborn Drone, Dual Blade Automech Drone, Great Shogun Mech Drone, Converter Wizard, Laser Blade Automech Drone, Big Razor Mech Drone |
| `p.blueLaserShot.swf` | SpatialWingedElfPaladinDelegate | Winged Paladin |
| `p.bluePlasmaBolt.swf` | SwatSoldierDelegate, UltraBotDelegate, WingedTransformerDelegate | Nemesis Core, Nemesis Drone, S.W.A.T. Soldier, S.W.A.T. Soldier, Proto Winged Mech |
| `p.bluePlasmaBoltLarge.swf` | UltraBotDelegate | Nemesis Core, Nemesis Drone |
| `p.bluePowerLaser.swf` | RedSpinnerDelegate | Red Spinner |
| `p.blueRay.swf` | CycloneBattlesuitDelegate | id1394 |
| `p.blueRocket.swf` | ProjectileDelegate | Crusader Tank |
| `p.blueWaves.swf` | ProjectileDelegate | Nemesis Drone, Viking Core Bot Drone |
| `p.bullet.swf` | BismarkMechDelegate, CrimsonCenturionDelegate, DoubleMachinegunDelegate, DoubleMachinegunTowerDelegate, DragonMechDelegate, EnemyConverterPriestDelegate, KnifeThrowerOrcDelegate, MachinegunDelegate, MachinegunTowerDelegate, OrcRobot2Delegate, PauldronMechDelegate, ProjectileDelegate, ReptileGunDelegate, RobotHunterDelegate, SuperfulcrumArmorDelegate, SwatSoldierDelegate, UrbanBusterDelegate | Turret I, Turret III, Soldier, APC, Ms. Evilia, Evil Hannibal, Machine Gun Jeep, Soldier II, Machine Gun Jeep II, Scarface girl, Soldier V, Knife Throwa, Big Handsaw Ork, Orc Zoldier, Orc Knifethrower, Red Handsaw Ork, Viking Soldier, Rune Golem Drone, Ether Messiah Drone, Robot Hunter, Dragonborn Mech, Dragonborn Drone, Dual Blade Automech Drone, Great Shogun Mech Drone, S.W.A.T. Soldier, Dark Ether Messiah Drone, Converter Wizard, Reptile Gun, Laser Blade Automech Drone, Big Razor Mech Drone, S.W.A.T. Soldier, id1353, id1355, id1399, id1408, id1412, id1416, id1417, id1419 |
| `p.bulletAir.swf` | ExecutionerMechDelegate, HerculesMatrixDelegate, MachinegunDelegate, SpatialWingedElfPaladinDelegate | Silver Hercules, Executioner Mech , Winged Paladin, id1372 |
| `p.bulletAirBig.swf` | BismarkMechDelegate, BushwackerDelegate, CrimsonCenturionDelegate, DroneMasterDelegate, HammerheadDelegate, HavocDelegate, HerculesMatrixDelegate, ProjectileDelegate, UrbanBusterDelegate | Silver Hercules, id1353, id1358, id1362, id1363, id1364, id1365, id1370, id1408, id1416 |
| `p.bulletBig.swf` | AgamemnonFortressDelegate, AndromedaCombatDroidDelegate, AndromedaCombatStarShipDelegate, AnvilPatternMechDelegate, AtomicBonecrushaDelegate, BladeStormMechDelegate, BlueAnvilDelegate, BombardierDroneDelegate, BombardierMechDelegate, BonecrushaDelegate, BrawlerDelegate, BunkerDelegate, BushwackerDelegate, CannonMechBotDelegate, CentaurDelegate, CrimsonCenturionDelegate, CycloneBattlesuitDelegate, DoubleCannonMechDelegate, DoubleMachinegunDelegate, DoubleMachinegunTowerDelegate, DoubleShotgunDelegate, DroneMaster2Delegate, DroneMasterDelegate, ElephantRiderDelegate, ErradicatorDelegate, ExecutionerMechDelegate, FireGameraDelegate, GiantWalkerDelegate, GlaiveStormMechDelegate, GuardianDelegate, HammerheadDelegate, HarvesterDelegate, HavocDelegate, HerculesMatrixDelegate, HerculesMechDelegate, IgnitionDelegate, IntruderDelegate, KaratekaDelegate, KaratekaGunnerDelegate, KnightExosuitDelegate, KnuckledraggerDelegate, MachinegunDelegate, MachinegunOrcDelegate, MachinegunTowerDelegate, MarauderBattleChasisDelegate, MassiveGunnerMechDelegate, MultiMorphDelegate, NebularBlueBicopterDelegate, NebularSniperDelegate, OptimusPrimeBotDelegate, PauldronMechDelegate, ProjectileDelegate, PunisherDelegate, RamboDelegate, ReaperDelegate, RedBaronDelegate, RobotHunterDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, SharkbiteDelegate, ShredderMechDelegate, SkorpionFortressDelegate, SpatialArcherDelegate, SpatialCruiserAirship, SpatialElfDinoRiderDelegate, SpatialElfGunnerDelegate, SpatialElfHealerDelegate, SpatialExplorationModuleDelegate, SpatialPaladinDelegate, SpatialPriestDelegate, SpatialWingedElfPaladinDelegate, SpecialBunkerDelegate, SpectreMechDelegate, SpiderBotDelegate, SplinterMechDelegate, StalkerMechDelegate, StampedeMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, SuperfulcrumArmorDelegate, TarantulaDelegate, TransformerArcherDelegate, TwoGunExobotDelegate, UrbanBusterDelegate, VikingSniperDelegate, VortexDelegate, WarlordDelegate, WingedTransformerDelegate, YamatoMechDelegate | Bunker I, Bunker II, Bunker III, Mega Bunker, Turret II, Turret VI, Ork Turret II, Enemy Ork Turret I, Viking Turret I, Viking Turret II, Nebular Turret, General Scarlett, General Mike, Soldier III, Sergeant Megan, Helicopter, Helicopter II, Helicopter III, Machine Gun Jeep III, Mr. Cigar, UN Allied, Sergeant Jack, Double Gun Soldier, Mr. Treat, Elephant rider, Soldier IV, Helicopter IV, Ranbo, Erradicator, Punisher Bot, Giant Walker, Red Baron, Gun Zoldier, Viking Sniper, Robot Hunter, Fire Karateka, Silver Hercules, Black Belt Archer, Nebular Bicopter, Massive Cannon Mech, Nebular Sniper, 2-Gun Exobot, Hercules Mech, Double Cannon Mech, Karateka Gunner, Prime Automech, Space Archer Elf, Space Priest Elf, Space Paladin Elf, Space Elf Cruiser, Proto Winged Mech, Spider Bot, Multi Morpher, Space Healer Elf, Space Scouter Elf, Silver Gunner Elf, Dino Rider Elf, Executioner Mech , Winged Paladin, Andromeda Combat Droid, Andromeda Spaceship, Massive Gunner Mech, id1307, id1309, id1313, id1315, id1317, id1319, id1321, id1327, id1329, id1330, id1333, id1334, id1339, id1341, id1347, id1349, id1355, id1356, id1358, id1360, id1362, id1364, id1367, id1368, id1370, id1372, id1375, id1379, id1381, id1382, id1385, id1388, id1390, id1392, id1393, id1394, id1398, id1400, id1408, id1410, id1412, id1413, id1414, id1416, id1418, id1421, id1422, id1424, id1428, id1430 |
| `p.bulletBigEnemy.swf` | — | — |
| `p.bulletBigRed.swf` | StampedeMechDelegate | id1309 |
| `p.bulletEnemy.swf` | — | — |
| `p.bulletRifle.swf` | BladeStormMechDelegate, DoubleShotgunDelegate, GlaiveStormMechDelegate, ProjectileDelegate, SplinterMechDelegate | Mr. Cigar, UN Allied, id1307, id1313, id1317 |
| `p.cannon.swf` | BombardierMechDelegate, BuggyDelegate, DoubleProjectileDelegate, MortarDelegate, MultiShotTowerDelegate, OrcoHelicopterDelegate, OrcoRobotDelegate, ProjectileDelegate, RavenMechDelegate, ShredderMechDelegate, SteelWandererMechDelegate, VikingMotoSquadDelegate | Cannon Turret, Bazooka, Bazooka II, Bazooka III, Double Bazooka, Double Bazooka Jeep, Dominion Tank, Mortar Thrower, Bazooka Soldier, Molotov Kopta, Horned Badass, War Buggy, Ork Kopta, Horned Beast Ork, Viking Tank, Viking Bazooka, Viking MotoSquad, Forge Dragon Draggy, id1329, id1333, id1335, id1341 |
| `p.cannonSmall.swf` | MultiShotTowerDelegate | Turret V |
| `p.chemicalLaser.swf` | ChemicalGunnerDelegate, ProjectileDelegate | id1396, id1397 |
| `p.chemicalLaserBig.swf` | ChemicalGunnerDelegate, PauldronMechDelegate | id1396, id1412 |
| `p.curvesBeam.swf` | AvengerMechDelegate | Avenger Mech  |
| `p.dragonFireBall.swf` | RobotHunterDelegate | Robot Hunter |
| `p.egg.swf` | NebularMonsterDelegate | Swamp Monster, Swamp Minion |
| `p.electric.swf` | ElectricTowerDelegate | Tesla Turret, Space Elf Turret |
| `p.electricBall.swf` | DoctorShockDelegate | Doctor Shock |
| `p.electricBeam.swf` | CrusherMonarchDelegate, DoctorShockDelegate, RedDragonDelegate | Blue Draggy, Blue Dragon, Doctor Shock, id1325 |
| `p.energyBall.swf` | MassiveGunnerMechDelegate, PunisherDelegate, RobotHunterDelegate | Punisher Bot, Robot Hunter, Massive Gunner Mech |
| `p.energyBall2.swf` | MarauderBattleChasisDelegate | id1367 |
| `p.energyBallBlue.swf` | CannonMechBotDelegate, DoubleCannonMechDelegate, GlaiveStormMechDelegate, HerculesMechDelegate, OptimusPrimeBotDelegate, SpatialCruiserAirship, SpatialElfGunnerDelegate, SpiderBotDelegate, TwoGunExobotDelegate | Massive Cannon Mech, 2-Gun Exobot, Hercules Mech, Double Cannon Mech, Prime Automech, Space Elf Cruiser, Spider Bot, Silver Gunner Elf, id1307 |
| `p.energyBallBlueBig.swf` | HerculesMechDelegate, SpatialCruiserAirship | Hercules Mech, Space Elf Cruiser |
| `p.espadazo.swf` | — | — |
| `p.fire.swf` | DoubleProjectileDelegate, FlamethrowerDelegate, ForgeDragonDelegate | Flamethrower, Flamethrowa Ork, Red Flamethrowa Ork, Forge Dragon, Forge Dragon Draggy |
| `p.fireBall.swf` | AvatarArcherDelegate, AvatarSoldadoDelegate, BlackDraggyDelegate, HellFireMechDelegate, MegaFireBotDelegate, MetalDraggyDelegate, ProjectileDelegate, SpatialHorsemanDelegate, YamatoMechDelegate | Metal Draggy, Red Draggy, Camu Draggy, Hyper Blazer, Hyper Blazer Drone, Nebular Spearman, Nebular Archer, Black Draggy, Nebular Dragon Rider Draggy, Nebular Dragon Knight Draggy, Red Mercury Draggy, Space Knight Elf, 2-Head Frostfire Draggy, id1311, id1339, id1393 |
| `p.fireBallSmall.swf` | ProjectileDelegate | Hyper Blazer Drone, Nebular Dragon Rider Draggy, Nebular Dragon Knight Draggy |
| `p.fireBeam.swf` | FrostFireDragonDelegate | 2-Head Frostfire Dragon, 2-Head Frostfire Draggy |
| `p.fireBeamLarge.swf` | FireGameraDelegate, HellFireMechDelegate | id1311, id1392 |
| `p.fireBig.swf` | MegaFireBotDelegate | Hyper Blazer |
| `p.fireBlue.swf` | NebularMonsterRiderDelegate | Blazing Beast Rider |
| `p.forgelordball.swf` | CycloneMechDelegate, ForgelordDelegate, ProjectileDelegate, ScarabDelegate, TempestMechDelegate | id1331, id1337, id1343, id1347, id1348 |
| `p.forgelordbeam.swf` | ForgelordDelegate | id1331 |
| `p.fuseBomb.swf` | ThrowingTowerDelegate | Ork Turret I, Enemy Ork Turret II |
| `p.greenArrow.swf` | TransformerArcherDelegate | Black Belt Archer |
| `p.greenBeam.swf` | DrillDelegate | Killer Driller |
| `p.greenYellowBall.swf` | MassiveGunnerMechDelegate | Massive Gunner Mech |
| `p.grenade.swf` | MetallicRedDragonDelegate, SwatSoldierDelegate, ThrowingTowerDelegate, TransformerAracnidDelegate, UrbanBusterDelegate | Ork Turret I, Enemy Ork Turret II, S.W.A.T. Soldier, Red Mercury Dragon, Red Mercury Draggy, S.W.A.T. Soldier, Arachnid Mech, Arachnid Drone, id1408 |
| `p.grenade2.swf` | MetallicRedDragonDelegate, SwatSoldierDelegate, TransformerAracnidDelegate | S.W.A.T. Soldier, Red Mercury Dragon, Red Mercury Draggy, S.W.A.T. Soldier, Arachnid Mech, Arachnid Drone |
| `p.hadoken.swf` | MessiahBotDelegate | Ether Messiah |
| `p.hadoken_karateka.swf` | KaratekaDelegate | Fire Karateka |
| `p.healBeam.swf` | HealerDelegate | id1373 |
| `p.iceBeam.swf` | FrostFireDragonDelegate | 2-Head Frostfire Dragon, 2-Head Frostfire Draggy |
| `p.laser.swf` | DoubleProjectileTowerDelegate, ProjectileDelegate | Laser Turret, Andromeda Turret, id1399, id1419 |
| `p.laserBeam.swf` | BumblebeeDelegate, TransformerSkaterDelegate | MegaBot, Roller Skater, MegaBot |
| `p.laserBeamBlue.swf` | ElectricDragonDroneDelegate, ProjectileDelegate | Ultra-Mech Drone, Electric Draggy |
| `p.laserBeamBlueFat.swf` | BushwackerDelegate, GuardianDelegate, RobotHunterDelegate, ScarletSuperfulcrumDelegate, SuperfulcrumArmorDelegate | Robot Hunter, id1355, id1358, id1385, id1388 |
| `p.laserBlue.swf` | AgamemnonFortressDelegate, AndromedaPrivateDelegate, AnvilPatternMechDelegate, BombardierMechDelegate, BonecrushaDelegate, CentaurDelegate, CrusaderPriestDelegate, CycloneBattlesuitDelegate, DoubleMachinegunDelegate, DreadnoughtDelegate, GunBotDelegate, IntruderDelegate, KaratekaGunnerDelegate, MachinegunDelegate, MarauderBattleChasisDelegate, MultiMorphDelegate, MultiShotDroneDelegate, ProjectileDelegate, ReaperDelegate, ScarletSuperfulcrumDelegate, SkylanderDelegate, SpatialAirshipDelegate, SpatialArcherDelegate, SpectreMechDelegate, StalkerMechDelegate, SuperfulcrumArmorDelegate, TarantulaDelegate, UltraBotDelegate, VikingCopterDelegate, VikingLaserDelegate, XtremeRetaliatorDelegate, YamatoMechDelegate | GunBot, Helicopter V, Crusader Soldier, Jet Soldier, Motorized Soldier, Xtreme Retaliator, Dreadnought, Skylander, Red Draggy, Blue Draggy, Alpha Drone, Crusader Priest, Viking Airship, Nemesis Core, Nemesis Drone, Viking Core Bot Drone, Big Laser Viking, Viking Airship Outsider, Red Mercury Draggy, Karateka Gunner, Space Archer Elf, Space Airship Elf, Multi Morpher, 2-Head Frostfire Draggy, Andromeda Private, Gamera Drone, id1315, id1319, id1321, id1329, id1339, id1349, id1355, id1356, id1367, id1375, id1382, id1385, id1394, id1428, id1430 |
| `p.laserBlueBig.swf` | DoubleMachinegunDelegate, DroneMaster2Delegate, MachinegunDelegate, SpatialElfDinoRiderDelegate | Soldier V, Helicopter V, Rune Golem Drone, Dino Rider Elf, id1400 |
| `p.laserBlueSlim.swf` | VikingCopterDelegate | Viking Airship, Viking Airship Outsider |
| `p.laserBlueSmall.swf` | CrusaderPriestDelegate, DoubleMachinegunDelegate, MachinegunDelegate, ProjectileDelegate, SpatialAirshipDelegate, VikingCopterDelegate, XtremeRetaliatorDelegate | Crusader Soldier, Jet Soldier, Motorized Soldier, Xtreme Retaliator, Crusader Priest, Viking Airship, Ether Messiah Drone, Viking Airship Outsider, Dark Ether Messiah Drone, Space Airship Elf |
| `p.laserMassiveDrone.swf` | DroneDelegate, ExecutionerMechDelegate, MultiShotDroneDelegate, PhalanxDroneDelegate, ProjectileDelegate, VortexDelegate | Massive Cannon Drone, Liquid Mech  Drone, Cyber Samurai  Drone, Prime Automech Drone, Spartan Warrior Drone, Proto Winged Drone, Arachnid Drone, Pharaoh Mech Drone, Executioner Mech Drone, Executioner Mech , Godzilla Mech Drone, King Kong Drone, Z Project Drone, Massive Gunner Drone, Fire Godzilla Drone, id1308, id1310, id1312, id1314, id1316, id1320, id1322, id1324, id1326, id1327, id1328, id1332, id1336, id1338, id1340, id1342, id1344, id1346, id1350, id1357, id1361, id1363, id1365, id1369, id1376, id1378, id1386, id1387, id1389, id1391, id1395, id1401, id1404, id1411, id1415, id1423, id1425, id1429, id1431 |
| `p.laserRed.swf` | BlackHoleDelegate, JunkBotDelegate, ProjectileDelegate | Steel Collector, id1377, id1409 |
| `p.laserRedViking.swf` | AndromedaPrivateDelegate, VikingLaserDelegate | Big Laser Viking, Andromeda Private |
| `p.laserYellow.swf` | DoubleProjectileDelegate, ProjectileDelegate | Tank IV, Tank V, Blue Steel Draggy |
| `p.laserdrone.swf` | MultiShotDroneDelegate, ProjectileDelegate | Golden Slayer Drone, Burning Slayer Drone, Avenger Mech Drone, id1318 |
| `p.lightningBlue.swf` | ProjectileDelegate | Blue Draggy |
| `p.megaEnergyBall.swf` | VikingRuneGolemDelegate | Rune Golem |
| `p.metallicBall.swf` | MetallicDragonDelegate | Metal Draggy, Metal Dragon |
| `p.missileM.swf` | AndromedaCombatStarShipDelegate, BismarkMechDelegate, BlackHoleDelegate, BuggyDelegate, BushwackerDelegate, CentaurDelegate, CrusherMonarchDelegate, DoubleProjectileTowerDelegate, EvilSlaughtererDelegate, GuardianDelegate, HammerheadDelegate, IntruderDelegate, LaboratoryDelegate, MassiveGunnerMechDelegate, MultiShotDelegate, ProjectileDelegate, ReaperDelegate, ScarabDelegate, ScarletSuperfulcrumDelegate, ServowormDelegate, SpatialExplorationModuleDelegate, SpatialPlasmaStrikerDelegate, StalkerMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, SuperfulcrumArmorDelegate, TarantulaDelegate, TransformerAracnidDelegate, VortexDelegate, WingedTransformerDelegate, ZProjectMechDelegate | Turret IV, Dual-Rocket Turret, Mind Control Laboratory, Red Tank, Tank II, Tank III, Tank, Antiaircraft battery, Crusader Tank, Orc Tank, War Buggy, Basic Ork Tank, Xplosive Beast ATP, Orc Big Tank, Proto Winged Mech, Arachnid Mech, Arachnid Drone, Space Scouter Elf, Siege Striker, Andromeda Spaceship, Z Project Mech, Massive Gunner Mech, id1321, id1325, id1327, id1341, id1345, id1347, id1349, id1351, id1353, id1355, id1358, id1364, id1375, id1377, id1385, id1388, id1424, id1428, id1430 |
| `p.missileS.swf` | DoubleProjectileTowerDelegate | Turret IV |
| `p.molotov.swf` | OrcoHelicopterDelegate | Molotov Kopta, Ork Kopta |
| `p.nebularEgg.swf` | NebularMonsterDelegate | Swamp Monster, Swamp Minion |
| `p.nebularSpear.swf` | ProjectileDelegate | Nebular Knight |
| `p.nuclear.swf` | BombardierMechDelegate, RavenMechDelegate, ShredderMechDelegate, SteelWandererMechDelegate | id1329, id1333, id1335, id1341 |
| `p.orangeMetalBeam.swf` | BlackDragonDelegate, ElectricDragonDelegate, MetallicDragon2Delegate | Camu Metal Dragon, Camu Draggy, Black Dragon, Electric Dragon, Electric Draggy, Black Draggy |
| `p.orcKnife.swf` | KnifeThrowerOrcDelegate, OrcRobot2Delegate | Knife Throwa, Big Handsaw Ork, Orc Knifethrower, Red Handsaw Ork |
| `p.orcRocket.swf` | OrcRobot2Delegate, OrcoRobotDelegate | Horned Badass, Big Handsaw Ork, Horned Beast Ork, Red Handsaw Ork |
| `p.overseerBeam.swf` | OverseerDelegate, ProjectileDelegate | id1406, id1407 |
| `p.overseerMissiles.swf` | OverseerDelegate | id1406 |
| `p.pureEnergyBall.swf` | ProjectileDelegate, ScarabDelegate | id1347, id1348 |
| `p.readBeamLaserCone.swf` | GameraMechDelegate | Gamera Mech |
| `p.readBeamLine.swf` | AndromedaPrivateDelegate, CrimsonCenturionDelegate, CyclopSoldierDelegate | Watcher Hero, Andromeda Private, id1416 |
| `p.readUnformedBeam.swf` | GodzillaMechDelegate | Godzilla Mech |
| `p.redBallLaser.swf` | GameraMechDelegate | Gamera Mech |
| `p.redBeam.swf` | RedDragonDelegate, SpatialDestructionWizardDelegate | Red Draggy, Red Dragon, Destruction Wizard |
| `p.redElectricBeam.swf` | BahamutMetalDelegate, MetallicDragonDelegate | Metal Draggy, Metal Dragon, Blue Steel Bahamut, Blue Steel Draggy |
| `p.redElectricBomb.swf` | MultiMorphDelegate, SpatialExplorationModuleDelegate, SpatialPlasmaStrikerDelegate | Multi Morpher, Space Scouter Elf, Siege Striker |
| `p.redFireBall.swf` | FireGodzillaMechDelegate | Fire Godzilla Mech |
| `p.redMetalBall.swf` | BahamutMetalDelegate, NebularPriestDelegate | Blue Steel Bahamut, Blue Steel Draggy, Nebular Priest |
| `p.redMissile.swf` | ProjectileDelegate, ReaperDelegate, TransformerAracnidDelegate | Arachnid Mech, Arachnid Drone, id1352, id1354, id1375 |
| `p.rocketM.swf` | BlackDraggyDelegate, BlackHoleDelegate, CrusherMonarchDelegate, DoubleProjectileDelegate, DoubleRocketStealthDelegate, IntruderDelegate, MassiveGunnerMechDelegate, MetalDraggyDelegate, MultiShotDelegate, ProjectileDelegate, RedSpinnerDelegate, ServowormDelegate, SpatialCruiserAirship, StalkerMechDelegate, SteelWandererMechDelegate, SteelgladiatorDelegate, TarantulaDelegate, VortexDelegate, WingedTransformerDelegate | Red Tank, Tank II, Tank III, Aircraft, Tank, Aircraft II, Aircraft III, Dominion Tank, Stealth Fighter, Bazooka IV, Bazooka V, Antiaircraft battery, Demolition Tank, Bazooka Soldier, Metal Draggy, Aircraft IV, Aircraft V, F-117, Red Spinner, Orc Tank, Camu Draggy, Basic Ork Tank, Xplosive Beast ATP, Orc Big Tank, Black Draggy, Space Elf Cruiser, Proto Winged Mech, Massive Gunner Mech, id1321, id1325, id1327, id1341, id1345, id1377, id1424, id1428, id1430 |
| `p.slimMissile.swf` | CrimsonCenturionDelegate, PauldronMechDelegate, ProjectileDelegate | id1412, id1416, id1417 |
| `p.spatialBigLaser.swf` | SpatialPriestDelegate | Space Priest Elf |
| `p.spatialSpear.swf` | SpatialHorsemanDelegate | Space Knight Elf |
| `p.spatialSword.swf` | SpatialPaladinDelegate | Space Paladin Elf |
| `p.spectreRay.swf` | SpectreMechDelegate, StalkerMechDelegate | id1319, id1321 |
| `p.spiderNet.swf` | SpiderBotDelegate | Spider Bot |
| `p.stalkerBomb.swf` | StalkerMechDelegate | id1321 |
| `p.sunBall.swf` | SpatialElfHealerDelegate | Space Healer Elf |
| `p.sunLaser.swf` | VikingCoreBotDelegate | Viking Core Bot |
| `p.tankMissile.swf` | MissileTankDelegate | Missile Tank |
| `p.teslaRay.swf` | ProjectileDelegate | id1402 |
| `p.tnt.swf` | XplosiveGuysDelegate | Xplosive Ork, Xplosive Beast Boss, Xplosive Beast |
| `p.ufoLaser.swf` | UfoDelegate | UFO |
| `p.ultraLaserBeam.swf` | UltraBotDelegate | Nemesis Core, Nemesis Drone |
| `p.urbanBeam.swf` | UrbanBusterDelegate | id1408 |
| `p.water.swf` | DoubleProjectileDelegate, FiremanDelegate | Fireman, Forge Dragon Draggy |
| `p.yamatoBall.swf` | YamatoMechDelegate | id1339 |
| `p.yellowBeam.swf` | ElectricDragonDelegate | Electric Dragon, Electric Draggy |
| `p.yellowElectricBeam.swf` | AndromedaCombatStarShipDelegate | Andromeda Spaceship |
| `p.yellowElectricLaserBeam.swf` | ZProjectMechDelegate | Z Project Mech |
| `p.yellowLaserBall.swf` | AndromedaCombatStarShipDelegate | Andromeda Spaceship |
| `p.yellowLaserBullet.swf` | AndromedaCombatDroidDelegate | Andromeda Combat Droid |
| `p.yellowMetalBall.swf` | MetallicDragon2Delegate | Camu Metal Dragon, Camu Draggy |
| `p.yellowMetalBeam.swf` | MetallicDragon2Delegate | Camu Metal Dragon, Camu Draggy |
| `p.yellowMetallicBeam.swf` | MetallicRedDragonDelegate | Red Mercury Dragon, Red Mercury Draggy |
| `p.yellowPlasma.swf` | CrusaderBotDelegate | Crusader Bot |
| `p.yellowRedElectricBall.swf` | MultiShotDroneDelegate, SteelgladiatorDelegate | Gamera Drone, id1424 |
| `p.yellowRedLaserBullet.swf` | AndromedaCombatStarShipDelegate, PauldronMechDelegate, ProjectileDelegate | Andromeda Spaceship, id1412, id1413, id1421 |
| `p.yellowUnformedBeam.swf` | FireGodzillaMechDelegate | Fire Godzilla Mech |
| `p.zProjectHand.swf` | ZProjectMechDelegate | Z Project Mech |
| `p.zProjectHand2.swf` | ZProjectMechDelegate | Z Project Mech |

### 5.4 FX constants that point at a **missing** file

14 `ProjectileDefinition` constants name an fx id that is **not** in `assets/fx/`:

| Constant | missing fx id | note |
|---|---|---|
| `BLAST_BULLET` | `b.bullet` | superseded by `b.bullet2` |
| `BLAST_GREY_BEAM` | `b.greyBeamBlast` | never shipped |
| `BLAST_PISTON` | `b.slaughtererPiston` | Slaughterer Mech special attack |
| `BLAST_TRANSFORM` | `b.transform` | Transformer special attack |
| `BLAST_YAMATO_BALL` | `b.yamatoBall` | Yamato Mech (post-config unit) |
| `P_BLUE_BEAM_ELECTRIC_2` | `p.beamBlueElectric2` | variant of `p.beamBlueElectric` |
| `P_BULLET_BLACK` | `p.bulletBlack` | never shipped |
| `P_CYBER_BEAM` | `p.cyberBeam` | Cyber Inquisitor (post-config) |
| `P_FIRE_BALL_BIG` | `p.fireBallBig` | — |
| `P_GREY_BEAM` | `p.greyBeam` | — |
| `P_LASER_BEAM_SLIM_WHITE` | `p.laserBeamSlimWhite` | — |
| `P_MISSILE_L` | `p.missileL` | long-range missile |
| `P_SACK` | `p.sack` | — |
| `P_TEMPEST` | `p.tempest` | Tempest Mech (post-config) |

`ProjectileManager.assetNotLoaded()` retries 3× then gives up, so these degrade to “no effect” rather than
breaking the battle. A re-implementation should simply not define them.

### 5.5 Special attacks → `btn_*` thumbnails

Full `btn_*` → unit table in §3.2. 67 of 68 referenced buttons exist; **`btn_1180_hiper` is missing**
(Robot Hunter, item 1180 — the other three of its buttons, `btn_1180_blast`, `btn_1180_shield`,
`btn_1180_wheel`, are present).

---

## 6. Audio catalogue — `assets/sounds/`

### 6.1 Totals

| Metric | Value |
|---|---|
| mp3 files in `assets/sounds/` | **140** (5 803 106 bytes, 5.53 MB) |
| `config['sounds']` entries | **139** |
| distinct `file` values | **138** (`explo1` is used by ids 1 and 4) |
| resolved | **139 / 139** |
| missing | **0** |
| files on disk not in the config | **2** (`BACKGROUND.mp3`, `battle_1.mp3` — the music beds) |

### 6.2 Semantics of the config fields

`core/SoundFile.as:34`:

```actionscript
public function SoundFile(param1:int, param2:String, param3:int, param4:int, param5:Boolean)
{   // param1 = id, param2 = file, param3 = max, param4 = loops, param5 = preload
    this.max = param3;  this.loops = param4;  this.preload = param5;
    this.sfxSimult = this.max;
    if(this.preload) { this.loadSound(); }
}
```

* `max` — max simultaneous instances of this sfx (every entry is `5` except the 80–139 “voice/robot” block,
  which uses `1`–`4`).
* `loops` — how many times the sample repeats when triggered (`1` for one-shots, `4` for the machinegun loop).
* `preload` — `1` = download at boot, `0` = lazy. Only 2 entries are `preload = 0` (ids 1 and 2).
* The URL is `sounds/<file>.mp3` (`SoundFile.as:55`).

### 6.3 The full `id → file → max/loops/preload` table

| id | file | max | loops | preload | description | asset |
|---|---|---|---|---|---|---|
| 1 | `explo1` | 5 | 1 | 0 | Test | **MISSING** |
| 2 | `metra` | 5 | 1 | 1 | Test | **MISSING** |
| 3 | `misil` | 5 | 1 | 1 | Missle sound fx (bazooka) | **MISSING** |
| 4 | `explo1` | 5 | 1 | 1 | Missle exploading sound | **MISSING** |
| 5 | `gunloop_1` | 5 | 4 | 1 | Machinegun sound | **MISSING** |
| 6 | `tank2` | 5 | 1 | 1 | Shooting tank | **MISSING** |
| 7 | `antitank` | 5 | 1 | 1 | Tank missle hitting | **MISSING** |
| 8 | `truckmov` | 5 | 1 | 1 | Truck driving | **MISSING** |
| 9 | `tankdef` | 5 | 1 | 1 | Tank moving | **MISSING** |
| 10 | `planemove` | 5 | 1 | 1 | Plane click | **MISSING** |
| 11 | `aldeano2` | 5 | 1 | 1 | Worker moving male | **MISSING** |
| 12 | `W-worker2` | 5 | 1 | 1 | Worker moving female 1 | **MISSING** |
| 13 | `M-common` | 5 | 1 | 1 | Male moving | **MISSING** |
| 14 | `M-gogo` | 5 | 1 | 1 | Male moving | **MISSING** |
| 15 | `M-letsgo3` | 5 | 1 | 1 | Male moving | **MISSING** |
| 16 | `M-Ohyeah3` | 5 | 1 | 1 | Male moving | **MISSING** |
| 17 | `M-okey` | 5 | 1 | 1 | Male moving | **MISSING** |
| 18 | `W-common2` | 5 | 1 | 1 | Female moving | **MISSING** |
| 19 | `W-gogo2` | 5 | 1 | 1 | Female moving | **MISSING** |
| 20 | `W-yeahlaugh` | 5 | 1 | 1 | Female moving | **MISSING** |
| 21 | `M-yessir2` | 5 | 1 | 1 | Male yessir | **MISSING** |
| 22 | `W-yessir` | 5 | 1 | 1 | Female yessir | **MISSING** |
| 23 | `aldeano1` | 5 | 1 | 1 | Worker click male | **MISSING** |
| 24 | `robott1` | 5 | 1 | 1 | Tank click | **MISSING** |
| 25 | `camionralenti` | 5 | 1 | 1 | Jeep click | **MISSING** |
| 26 | `die-M` | 5 | 1 | 1 | Male dead sound | **MISSING** |
| 27 | `die-W` | 5 | 1 | 1 | Female dead sound | **MISSING** |
| 28 | `tankbroke` | 5 | 1 | 1 | Tank dead sound | **MISSING** |
| 29 | `meidei` | 5 | 1 | 1 | Aircraft dead sound | **MISSING** |
| 30 | `metra2` | 5 | 1 | 1 | Rifle shot | **MISSING** |
| 31 | `click1` | 5 | 1 | 1 | Button over sound | **MISSING** |
| 32 | `clicck4` | 5 | 1 | 1 | Button click sound | **MISSING** |
| 33 | `colect2` | 5 | 1 | 1 | Collect xp sound | **MISSING** |
| 34 | `edifici1` | 5 | 1 | 1 | Building click | **MISSING** |
| 35 | `construcc` | 5 | 1 | 1 | Start builiding | **MISSING** |
| 36 | `obra` | 1 | 1 | 1 | Constructing sound | **MISSING** |
| 37 | `final.construc_1` | 1 | 1 | 1 | Constructing end | **MISSING** |
| 38 | `M-helicopter` | 5 | 1 | 1 | Male helicopter flying | **MISSING** |
| 39 | `gold` | 5 | 1 | 1 | Gold collecting sound | **MISSING** |
| 40 | `lumber` | 5 | 1 | 1 | Collecting wood sound | **MISSING** |
| 41 | `metal` | 5 | 1 | 1 | Collecting metal sound | **MISSING** |
| 42 | `petrol` | 5 | 1 | 1 | Collecting oil sound | **MISSING** |
| 43 | `W-worker3` | 5 | 1 | 1 | Worker moving female 2 | **MISSING** |
| 44 | `W-worker1` | 5 | 1 | 1 | Worker click female | **MISSING** |
| 45 | `planemoveOK` | 5 | 1 | 1 | Plane moving | **MISSING** |
| 46 | `levelUP_1` | 5 | 1 | 1 | Level up sound | **MISSING** |
| 47 | `metra1` | 5 | 1 | 1 | Machinegun sound - jeep | **MISSING** |
| 48 | `shotLoop1` | 5 | 5 | 1 | Machinegun loop 1 | **MISSING** |
| 49 | `shotLoop2` | 5 | 5 | 1 | Machinegun loop 2 (heavy) | **MISSING** |
| 50 | `shotLoop3` | 5 | 5 | 1 | Machinegun loop 3 | **MISSING** |
| 51 | `collect` | 5 | 1 | 1 | Collect resource sound | **MISSING** |
| 52 | `unitdone` | 5 | 1 | 1 | Unit spawn | **MISSING** |
| 53 | `W-1` | 5 | 1 | 1 | Worker women 1 | **MISSING** |
| 54 | `W-2` | 5 | 1 | 1 | Worker women 1 | **MISSING** |
| 55 | `W-3` | 5 | 1 | 1 | Worker women 1 | **MISSING** |
| 56 | `destroy_building` | 5 | 1 | 1 | Destroy builidng sound | **MISSING** |
| 57 | `lanzallamas` | 5 | 1 | 1 | Firethrower | **MISSING** |
| 58 | `mrTClick` | 5 | 1 | 1 | Mr. T Click | **MISSING** |
| 59 | `mrMove` | 5 | 1 | 1 | Mr. T Moving | **MISSING** |
| 60 | `knife` | 5 | 1 | 1 | Knife (special ops) | **MISSING** |
| 61 | `llamasClick` | 5 | 1 | 1 | Flamethrower click | **MISSING** |
| 62 | `llamasOkay` | 5 | 1 | 1 | Flamethrower moving | **MISSING** |
| 63 | `llamasFire` | 5 | 1 | 1 | Flamethrower moving 2 | **MISSING** |
| 64 | `mecOk` | 5 | 1 | 1 | Mecanic moving | **MISSING** |
| 65 | `mecYes` | 5 | 1 | 1 | Mecanic click | **MISSING** |
| 66 | `repair` | 5 | 1 | 1 | Mecanic repair | **MISSING** |
| 67 | `medicOk` | 5 | 1 | 1 | Medic moving | **MISSING** |
| 68 | `medicYES` | 5 | 1 | 1 | Medic Click | **MISSING** |
| 69 | `curar_2` | 5 | 1 | 1 | Medic heal | **MISSING** |
| 70 | `okMrT` | 5 | 1 | 1 | Mr.T moving 2 | **MISSING** |
| 71 | `yesMrT` | 5 | 1 | 1 | Mr.T click 2 | **MISSING** |
| 72 | `bush` | 5 | 1 | 1 | Special Ops moving | **MISSING** |
| 73 | `robotOkay` | 5 | 1 | 1 | GunBot Click | **MISSING** |
| 74 | `robotReady` | 5 | 1 | 1 | GunBot Moving | **MISSING** |
| 75 | `RobotShot1` | 5 | 1 | 1 | Laser Shot | **MISSING** |
| 76 | `laserRobot` | 5 | 1 | 1 | Laser Shot | **MISSING** |
| 77 | `robotCharge` | 5 | 1 | 1 | Bumblebee special laser | **MISSING** |
| 78 | `robotDestroy` | 5 | 1 | 1 | Bumblebee MOVING | **MISSING** |
| 79 | `robotAttack1` | 5 | 1 | 1 | Quest 12 boss special attack | **MISSING** |
| 80 | `80_fireBall` | 5 | 1 | 1 | Fire Ball SFX (metal draggy) | **MISSING** |
| 81 | `81_draggy_click` | 5 | 1 | 1 | Draggi selection | **MISSING** |
| 82 | `82_draggy_moving` | 5 | 1 | 1 | Draggy moving | **MISSING** |
| 83 | `83_draggy_die` | 5 | 1 | 1 | Draggy die | **MISSING** |
| 84 | `84_missileTank_click` | 5 | 1 | 1 | Missile Tank Click | **MISSING** |
| 85 | `85_missileTank_move` | 5 | 1 | 1 | Missile Tank Move | **MISSING** |
| 86 | `86_missileTank_die` | 5 | 1 | 1 | Missile Tank Die | **MISSING** |
| 87 | `87_imyourgun` | 5 | 1 | 1 | Terminator moving 1 | **MISSING** |
| 88 | `88_lavista` | 5 | 1 | 1 | Terminator moving 2 | **MISSING** |
| 89 | `89_yah` | 5 | 1 | 1 | Terminator Click | **MISSING** |
| 90 | `90_moto_click` | 5 | 1 | 1 | Robo biker click | **MISSING** |
| 91 | `91_moto_move` | 5 | 1 | 1 | Robo biker move | **MISSING** |
| 92 | `92_moto_die` | 5 | 1 | 1 | Robo biker die | **MISSING** |
| 93 | `93_robotDestroy` | 5 | 1 | 1 | Punisher bot moving 1 | **MISSING** |
| 94 | `94_space_move` | 5 | 1 | 1 | SkyLander / X-treme Retaliator move | **MISSING** |
| 95 | `95_space_click` | 5 | 1 | 1 | SkyLander click / X-treme Retaliato | **MISSING** |
| 96 | `96_lightning` | 5 | 1000 | 1 | Tesla tower | **MISSING** |
| 97 | `97_robot2_ready` | 5 | 1 | 1 | Dreadnought Click | **MISSING** |
| 98 | `98_robot2_oukei` | 5 | 1 | 1 | Dreadnought moving 1 | **MISSING** |
| 99 | `99_robot2_destroy` | 5 | 1 | 1 | Dreadnought miving 2 | **MISSING** |
| 100 | `100_enabled2` | 5 | 1 | 1 | Giant Walker Click | **MISSING** |
| 101 | `101_imready` | 5 | 1 | 1 | Giant Walker Moving 1 | **MISSING** |
| 102 | `102_recived` | 5 | 1 | 1 | Giant Walker Moving 2 | **MISSING** |
| 103 | `103_dragonclick` | 5 | 1 | 1 | Blue/Red dragon Click | **MISSING** |
| 104 | `104_dragonMove` | 5 | 1 | 1 | Blue/Red dragon Moving | **MISSING** |
| 105 | `105_dragondeath` | 5 | 1 | 1 | Blue/Red dragon Death | **MISSING** |
| 106 | `106_powerLaser` | 5 | 1 | 1 | Blue/Red dragon Special atack laser | **MISSING** |
| 107 | `107_laser4` | 5 | 1 | 1 | Red Dragon Normal atack | **MISSING** |
| 108 | `108_die-M` | 5 | 1 | 1 | Male Soldier Die | **MISSING** |
| 109 | `109_die-W` | 5 | 1 | 1 | Female Soldier Die | **MISSING** |
| 110 | `110_baronrojoClick` | 5 | 1 | 1 | Red Baron Click | **MISSING** |
| 111 | `111_baronrojoMove` | 5 | 1 | 1 | Red Baron move | **MISSING** |
| 112 | `112_oukei` | 5 | 1 | 1 | Rambo / double gun soldier move 1 | **MISSING** |
| 113 | `113_yesstalone` | 5 | 1 | 1 | Rambo / double gun soldier Click | **MISSING** |
| 114 | `114_yhal` | 5 | 1 | 1 | Rambo / double gun soldier move 2 | **MISSING** |
| 115 | `115_lancer` | 5 | 1 | 1 | Atack for SteelClaws / megalancer | **MISSING** |
| 116 | `116_newsold_2` | 5 | 1 | 1 | Steel Claws Move 1 | **MISSING** |
| 117 | `117_newsold_3` | 5 | 1 | 1 | Steel Claws Click | **MISSING** |
| 118 | `118_newsold_4` | 5 | 1 | 1 | Steel Claws Move 2 | **MISSING** |
| 119 | `119_jetmove` | 5 | 1 | 1 | Jet Soldier Move | **MISSING** |
| 120 | `120_newsold_13` | 5 | 1 | 1 | Jet Soldier Move 2 | **MISSING** |
| 121 | `121_newsold_14` | 5 | 1 | 1 | Jet Soldier Click 1 | **MISSING** |
| 122 | `122_newsold_15` | 5 | 1 | 1 | Jet Soldier Click 2 | **MISSING** |
| 123 | `123_newsold_8` | 5 | 1 | 1 | Swordman Move 1 | **MISSING** |
| 124 | `124_newsold_10` | 5 | 1 | 1 | Swordman Move 2 | **MISSING** |
| 125 | `125_newsold_11` | 5 | 1 | 1 | Swordman Click | **MISSING** |
| 126 | `126_sword2` | 5 | 1 | 1 | Sword sound 1 | **MISSING** |
| 127 | `127_swordOK` | 5 | 1 | 1 | Sword sound 2 | **MISSING** |
| 128 | `128_ataquegiratorio1` | 5 | 1 | 1 | Special Atack for megalancer | **MISSING** |
| 129 | `129_Robot_comm` | 5 | 1 | 1 | Robot Move | **MISSING** |
| 130 | `130_Robot_wait` | 5 | 1 | 1 | Robot Click | **MISSING** |
| 131 | `131_trollvoz3` | 5 | 1 | 1 | Troll Click1 | **MISSING** |
| 132 | `132_trollvoz4` | 5 | 1 | 1 | Troll Move 1 | **MISSING** |
| 133 | `133_trollvoz5` | 5 | 1 | 1 | Troll Clik2 | **MISSING** |
| 134 | `134_trollvoz7` | 5 | 1 | 1 | Troll Move 2 | **MISSING** |
| 135 | `135_saw` | 5 | 1 | 1 | Big Hadnshaw ork special atack | **MISSING** |
| 136 | `136_swoosh` | 5 | 1 | 1 | Horned Badass (when grab an enemy) | **MISSING** |
| 137 | `137_mecha` | 5 | 1 | 1 | Xplosive guyz launch | **MISSING** |
| 138 | `138_trolldie` | 5 | 1 | 1 | orks/trolls die | **MISSING** |
| 139 | `139_hit` | 5 | 1 | 1 | hammer sound | **MISSING** |

### 6.4 Music

`managers/SoundManager.as:37`:

```actionscript
private static const MUSIC:Array = ["sounds/BACKGROUND.mp3","sounds/battle_1.mp3",
                                        "sounds/BACKGROUND.mp3","sounds/battle_1.mp3","sounds/BACKGROUND.mp3"];
```

| const | value | file |
|---|---|---|
| `MUSIC_MAP` | 0 | `sounds/BACKGROUND.mp3` |
| `MUSIC_BATTLE` | 1 | `sounds/battle_1.mp3` |
| `MUSIC_SHIP` | 2 | `sounds/BACKGROUND.mp3` |
| `MUSIC_ASSAULT` | 3 | `sounds/battle_1.mp3` |
| `MUSIC_QUEST` | 4 | `sounds/BACKGROUND.mp3` |

`BACKGROUND.mp3` is 1 589 413 bytes (54 s) and `battle_1.mp3` is 1 340 517 bytes (46 s) — together 49 % of the
whole audio payload, so they are the only assets worth converting to a compressed/streamed format.

---

## 7. Fonts

### 7.1 The font files in the tree

`assets/fonts/` contains **2 files** — and they are **`.swf`, not TTF/OTF**:

| File | Size | Embedded font name (FFDec) | Exported class |
|---|---|---|---|
| `en_KomikaAxis.swf` | 51 451 B | `Komika Axis __Embedded__EN` | `fonts.en_KomikaAxis_fontClass` |
| `en_ArialRoundedBold.swf` | 37 543 B | `Arial Rounded MT Bold __Embedded__EN` | `fonts.en_ArialRoundedBold_fontClass` |

URL template (`utils/FontsLoader.as:60`): `fonts/<loadedLang>_<fontName>.swf`, with `fontName` from
`Base.as:1202-1203` → `addFont("ArialRoundedBold")`, `addFont("KomikaAxis")`.
`FontsLoader.availableLanguages = [en, tr, el]` (`Base.as:1199`) — only the `en` variants were shipped, so the
Turkish and Greek font files are **missing** (UNVERIFIED whether they ever existed).

### 7.2 Fonts embedded in the client SWF

`assets/flash/Basesec_1.5.4.swf` embeds **6 fonts** (all `DefineFont3`). Extracted with JPEXS FFDec 26.3.0:

| # | Font name | Exported TTF | Used by the AS3 |
|---|---|---|---|
| 1 | `Komika Axis` | 14_Komika Axis.ttf (98 332 B) | `core/Particle.as:108,136`, `GUI/GiftButtonLarge.as:121` (damage numbers) |
| 2 | `Arial Rounded MT Bold` | 19_Arial Rounded MT Bold.ttf (75 004 B) | `core/Base.as:1836` (debug tile readout) |
| 3 | `Eras Bold ITC` | 35_Eras Bold ITC.ttf (19 668 B) | not referenced by name in the AS3 — used as the **embedded** font of pre-laid-out movie-clip text fields |
| 4 | `Freestyle Script` | 640_Freestyle Script.ttf (30 992 B) | same — decorative/heading text baked into the timeline |
| 5 | `DS-Digital Bold Italic` | 1034_DS-Digital Bold Italic.ttf (4 532 B) | same — numeric/tech readouts baked into the timeline |
| 6 | `Arial` | *(FFDec did not write a TTF for it)* | system fallback — used for body copy when no other font is registered |

### 7.3 The font-equivalence mechanism (important for a re-implementation)

`core/TextFieldUtil.as` maintains two maps:

* `_originalToEmbedded[originalFontName] = embeddedFontName` — the runtime-loaded font replaces the original
  (e.g. `Komika Axis` → `Komika Axis __Embedded__EN`);
* `dicFontEquivalence` — a server-supplied map applied to *every* text field before rendering
  (`TextFieldUtil.setHTML` rewrites `_loc5_.font` twice through the map).

`Base.as:1415` populates it: `this.loadFontEquivalence(Base.Items.globals.FONT_EQUIVALENCE);`
**`FONT_EQUIVALENCE` is not present in `config/main.json`** (the `globals` object has 104 keys and none of them
is `FONT_EQUIVALENCE`), so `loadFontEquivalence(undefined)` throws inside the surrounding `try/catch` and the map
stays empty. The client therefore falls back to the embedded SWF fonts.

### 7.4 `BlockBertholdRegular`

**NOT PRESENT.** A binary search of the uncompressed `Basesec_1.5.4.swf` for `BlockBerthold` returns byte offset
`-1` (not found); the FFDec font export lists only the 6 fonts above; and no `.ttf`/`.otf` exists anywhere in the
repository (`Get-ChildItem -Recurse -Include *.ttf,*.otf,*.woff` → 0 hits). The font list in the task brief is
therefore **incorrect on this point** — mark it as *not present* rather than as a missing asset.

### 7.5 What a modern client must do with fonts

1. **The two `fonts/*.swf` files must be converted to real web fonts.** FFDec can export them directly:
   `-export font` on `en_KomikaAxis.swf` yields `Komika Axis __Embedded__EN.ttf` (138 276 B) and on
   `en_ArialRoundedBold.swf` yields `Arial Rounded MT Bold __Embedded__EN.ttf` (103 272 B) — but note the
   **extracted TTF is a subset** and the glyph coverage must be checked before shipping.
2. **The 6 embedded SWF fonts must be extracted too** (`ffdec -export font` on `Basesec_1.5.4.swf` produced
   exactly 5 TTF files — `Arial` is the 6th and FFDec wrote no TTF for it).
3. **Licensing:** `Komika Axis` is widely distributed as a **free display font** (UNVERIFIED from this repo —
   no licence file ships with it); `Arial Rounded MT Bold` and `Arial` are **proprietary Microsoft fonts** and
   `Eras Bold ITC`, `Freestyle Script` and `DS-Digital Bold Italic` are **proprietary Monotype fonts**.
   Redistribution of those four is a licensing problem for a modern client (see §9.5).

---

## 8. The `externalized/` directory

### 8.1 Contents

```
assets/externalized/
└── viral_buttons/
    └── crossDCi.swf        488 330 bytes
```

**That is the entire directory: 1 file, 488 330 bytes.**

**`weird.txt` is NOT present.** The client requests it at `core/Base.as:1112`:

```actionscript
urlLoader = new URLLoader(new URLRequest("externalized/weird.txt"));
urlLoader.addEventListener(Event.COMPLETE,function(param1:Event):void {
   var _loc2_:String = param1.target.data;
   _loc2_ = _loc2_.split("SEC")[0];
   Base.Commands.weirdSecurity = _loc2_;
});
```

It is a **relative** URL (no `apfx` prefix), so it resolves against the *page* URL, not the asset CDN. It is only
fetched when the page did **not** supply an `onuewg…`-shaped security parameter and no `dynamicUrl` was given
(`Base.as:1099-1123`). The `try/catch` swallows the failure, so its absence is harmless for the offline build —
but it means the **security-token fallback path is dead** in this tree. UNVERIFIED whether the file ever
existed upstream or was stripped deliberately (it holds a secret, so the latter is likely).

### 8.2 How the client consumes `externalized/`

Two mechanisms, both found by grepping the AS3 for `externalized`:

1. **`managers/AssetManager.as`**
   ```actionscript
   public static const TYPE_SPRITES:String = "sprites";
   public static const TYPE_FX:String = "fx";
   public static const EXTERNALIZED:String = "externalized";
   public static function getAsset(param1:String, param2:Function = null, param3:String = "sprites") : MovieClip
   ```
   and `managers/assets/SingleAssetLoader.as:31` builds `Base.Main.apfx + param3 + "/" + param1 + ".swf"`.
   So `getAsset("crossDCi", cb, "externalized/viral_buttons")` →
   `apfx + "externalized/viral_buttons/crossDCi.swf"`.
2. **`core/ImageLoader.as:18`** declares `public static const EXTERNALIZED:String = "externalized/";` — this is
   the *base folder* constant for `ImageLoader`'s 7th constructor argument, i.e. the same URL scheme but for
   raster art. It is not used for any file that exists in this tree.

The single consumer of `crossDCi.swf` is `GUI/CrossDCiViralIcon.as:20`, instantiated from
`GUI/GuiManager.as:803` as `new CrossDCiViralIcon("crossDCi")` — the **Dragon City** cross-promotion viral
button. (The Social Empires counterpart `crossSEi` is referenced in `globals.CROSS_ITEMS` but **no SWF exists**
for it in `externalized/`.)

### 8.3 What this means for a re-implementation

`externalized/` is a **hot-swap / cross-promo bucket**: content that Zynga could replace on the CDN without
shipping a new client. A modern client should keep the mechanism (a CDN-overridable folder) but the
Dragon-City button is dead marketing in 2026 and can simply be dropped.

---

## 9. Assessment for a modern (web / GL / canvas) client

### 9.1 What has to be converted

| Format | Files | Size | Action |
|---|---|---|---|
| **SWF sprites** (`assets/sprites/`) | 862 | 357.21 MB | **CONVERT** → SVG path data + frame timeline, or → sprite-sheet PNG/atlas |
| **SWF fx** (`assets/fx/`) | 205 | 9.03 MB | **CONVERT** → same pipeline as sprites (they are the same kind of vector timeline) |
| **SWF magic** (`assets/magic/`) | 10 | 1.36 MB | **CONVERT** |
| **SWF characters** (`assets/characters_2/`) | 26 | 2.09 MB | **CONVERT** (cutscene sprite sheets) |
| **SWF images** (6 in `images/en/intro/`, 3 research-centre popups in `images/en/`) | 9 | 5.70 MB | **CONVERT** (small, cutscene-like timelines) |
| **SWF fonts** (`assets/fonts/`) | 2 | 88 994 B | **CONVERT** → TTF/WOFF2 |
| **SWF client** (`assets/flash/`) | 60 | 244.19 MB | **DO NOT CONVERT** — this is the *old* client, keep as reference/archive only |
| **SWF runtime library** (`assets/swf/dynamic2.swf`) | 1 | 0.47 MB | archive only |
| **SWF externalized** (`externalized/viral_buttons/crossDCi.swf`) | 1 | 0.47 MB | archive only |
| **JPG** (thumbs + images) | 1 753 | 83.34 MB | **KEEP AS-IS** |
| **PNG** (images) | 130 | 7.27 MB | **KEEP AS-IS** |
| **MP3** (sounds) | 140 | 5.53 MB | **KEEP AS-IS** (optionally re-encode to Opus/AAC for web; 2 files dominate the size) |

**Total SWF to convert: 1 114 files / 393 729 718 bytes (375.49 MB)** (excluding the 60 client builds). The
dominant categories are the 862 unit/building sprites (357.21 MB) and the 205 fx (9.03 MB).

### 9.2 Tooling

The repo already ships what is needed — `C:\Users\Edison\AppData\Local\Temp\opencode\socialwarriors\tools\ffdec\`
contains **JPEXS Free Flash Decompiler 26.3.0** (`ffdec-cli.exe`, `ffdec.jar`, `ffdec_lib.jar`). Verified
working commands:

```
# vector shapes -> SVG (one SVG per DefineShape/DefineMorphShape, with bitmap fills inlined as base64 PNG)
ffdec-cli.exe -export shape,symbolClass <outdir> assets/sprites/0001_house_1_m.swf

# sprite frames -> PNG (one PNG per frame of the root timeline)
ffdec-cli.exe -export frame <outdir> assets/sprites/1001_worker_m.swf

# fonts -> TTF (both the runtime font SWFs and the fonts embedded in Basesec_1.5.4.swf)
ffdec-cli.exe -export font,symbolClass <outdir> assets/flash/Basesec_1.5.4.swf
```

**Recommended pipeline:**

1. `ffdec -export shape` per SWF → SVG files with a `SymbolClass` CSV giving the exported symbol name.
   ⚠ **The exported SVG is not “pure vector”.** The shapes are heavily **bitmap-filled** (the verified export of
   `0001_house_1_m` produced a 48 KB SVG whose fill is a 216×144 base64 PNG `<pattern>`). So a naive
   “SWF → SVG” gives you *raster art wrapped in SVG*, not paths. A better pipeline is:
   * `ffdec -export frame` → per-frame PNG (lossless, correct rasterisation), **or**
   * a headless Ruffle / `swfmill` / `swf2js`-style renderer that walks the timeline and emits a
     texture atlas + per-frame transform metadata.
2. Build a **texture atlas** per sprite: the frames of `sprites/<img_name>.swf` become one atlas page + a JSON
   frame table `{frame, x, y, w, h, anchorX, anchorY, duration}`. The client already knows the frame count via
   `items[].max_frame` and the `frame` field of a placed element.
3. Keep the **anchoring semantics** the Flash client relies on: `IsoElement`/`AnimatedUnit` place the sprite by
   its lower-centre anchor on an isometric grid (`Config.EI_TILE_WIDTH_PIXELS = 108`,
   `EI_TILE_HEIGHT_PIXELS = 54`). A modern renderer must reproduce that anchor or every unit will be misplaced.
4. For the 862 sprites, generate **atlas pages at the game resolution** (the tiles are 108×54 px, sprites are
   typically 1–4 tiles wide) and mip-map them; 357 MB of SWF collapses to something like 40–90 MB of PNG/WebP
   atlases (UNVERIFIED — depends on the chosen resolution and format).

### 9.3 What the asset tree does **NOT** cover

These are the gaps a clone must source or synthesise:

| Gap | Evidence | Impact |
|---|---|---|
| **Real fonts** (4 of 6 are proprietary) | `Eras Bold ITC`, `Freestyle Script`, `DS-Digital Bold Italic`, `Arial Rounded MT Bold`, `Arial` are embedded in `Basesec_1.5.4.swf`; only 2 have a redistributable runtime replacement in `assets/fonts/` | medium — substitute free display fonts, or re-draw the text baked into the sprites |
| **UI chrome / HUD layout** | the entire interface is vector shapes compiled into `Basesec_1.5.4.swf` (244 MB of client builds) and `templates/img`, `templates/css`, `templates/avatars` in the repo | high — the modern client must rebuild every panel, button, gauge and popup from scratch |
| **UI sounds** | `config['sounds']` covers only in-world SFX + unit voice lines; there is no “click”, “hover”, “error”, “reward” UI set in the tree (`clicck4.mp3` and `repair.mp3` are the closest) | low-medium |
| **The map / terrain tiles** | `Config.EI_MAP_WIDTH/HEIGHT = 100`, tiles 108×54; no terrain tile-set art exists in `assets/` — the map is drawn procedurally by `core/MapInitializer.as` using `assets/images/en/mapa1..5.jpg` (5 JPEG map backgrounds) | high — the 5 `mapa*.jpg` are the only map art |
| **Male/female avatar art for chapters** | `/chapters/chapter_N_m.jpg` and `_w.jpg` are referenced by the config but **34 chapter images are missing** (§2.4.1) | low — replace with the base `chapter_N.jpg` |
| **Turkish & Greek fonts** | `FontsLoader.availableLanguages = [en, tr, el]` but only `en_*` files ship | low — English-only build |
| **Spanish `intro - copia.swf`** | referenced by the config, missing from the tree | low |
| **Sound FX for the 1307–1431 unit wave** | the config has no items for them, so no `sounds[]` entries, and the AS3 uses `projectileSfxs` keyed by `projectileID` — several of those projectile ids have **no fx file** (§5.4) | medium |
| **`assets/bigbosses/bigboss1.jpg`** | `Base.as:1206` requests `apfx + "bigbosses/bigboss1.jpg"`; **the `bigbosses/` folder does not exist** | low — a single quest image |
| **Cross-promo `crossSEi`** | `globals.CROSS_ITEMS` references a Social Empires viral button; no SWF exists | low |
| **Offer-pack / promotion art** | `config['images']` points at `/packs/…` and `/res_packs/…`; those exist, but the *offer* content itself (Facebook offers) is server-side and dead | low |
| **`assets/thumbs` for 29 items** | see §2.2.2 | trivial |

### 9.4 Server-side data that a clone must re-implement

The asset tree is only the *presentation* half. The **game data** lives in `config/main.json` (778 items, 607
image paths, 139 sounds, 10 magics, 6 category trees, 90 inventory items, 100 levels, 91 goals, 44 offer packs, 26
social items, 104 globals, 30 dart items) plus the protocol layer described in reports 01–04. A modern client needs
the item table in the **exact shape** used here (`id`, `type`, `category_id`, `subcategory_id`,
`subcat_functional`, `img_name` as a **comma-separated variant list**, `max_frame`, `width`/`height` in tiles,
`elevation`, `group_type`, `properties` as a JSON string, `costs` as a JSON string, `trains_ids`, `upgrades_to`,
`best_against`, …). The per-item table in §4 is the authoritative extract of the fields that drive asset loading.

### 9.5 Licensing and attribution

| Asset class | Status | Notes |
|---|---|---|
| Repository code (server, tools) | **GPL v3** | `LICENSE` at the repo root (35 823 B), `README.md` §License: “Social Wars preservation project. Copyright (C) 2022 The Social Warriors team. See the GNU General Public License”. Any derivative of the *server* must be GPL v3. |
| Game **art and audio** (Zynga / Social Point) | **not GPL** — proprietary | The GPL covers the preservation project’s own code, not Zynga’s assets. A public re-implementation that ships Zynga’s sprites/audio inherits their rights. |
| Preservation / archival exemption | **explicitly invoked** | `README.md` §“On archives and accessibility to digital heritage” cites: the 2018 US Federal Register **“Exemption to PCCPSACT”** (DMCA §1201 circumvention exemption for libraries/archives/preservation), **EFGAMP** (European Federation of Video Game Archives, Museums and Preservation projects), the **UNESCO PERSIST** programme, the **Internet Archive**, **BlueMaxima’s Flashpoint**, and the **Adobe Flash Player Archive**. |
| Fonts | **mixed** | `Komika Axis` was released freeware; `Arial Rounded MT Bold` / `Arial` (Monotype), `Eras Bold ITC`, `Freestyle Script`, `DS-Digital Bold Italic` (Monotype) are proprietary and **must not be redistributed** as webfonts. |
| Music | **proprietary** | `BACKGROUND.mp3` / `battle_1.mp3` are Zynga's licensed tracks. |
| Cross-promo art (Dragon City / Social Empires) | **third-party trademarks** | `logo_DC.png`, `play_DC.jpg`, `logo_SE.png`, `play_SE.jpg`, `crossDCi.swf`, `globals.CROSS_ITEMS` — drop them in a modern build. |

**Recommendation for a modern client:**

* Keep the GPL v3 licence on the server and the *tools*; publish the asset-conversion tooling under GPL v3 too.
* Do **not** ship Zynga's art/audio/music in a public build. Either (a) keep the project strictly archival and
  non-commercial, relying on the preservation exemptions above, or (b) re-skin with original assets and keep the
  *data model* (which is the real IP being re-implemented).
* Substitute the 4 proprietary fonts with free alternatives (e.g. *Komika Axis* is already free and covers the
  Komika/Arial-Rounded roles; a SIL-licensed family can replace Eras/Freestyle/DS-Digital).
* Keep the `weird.txt` mechanism out of any public build, and drop the `crossDCi` / `crossSEi` cross-promo art
  (trademarked).

---

## 10. Reproducibility

Scripts used (all in `%TEMP%\opencode\socialwarriors\work\`):

| Script | Produces |
|---|---|
| `a01_inventory.py` | directory/extension inventory, item→sprite/thumb resolution, `a02_itemres.json` |
| `a03_resolve.py` | images / sounds / magics / fx resolution |
| `a04_fx.py`, `a05_fxmap.py`, `a06_fxmap2.py`, `a07_fxfiles.py`, `a15_fxtight.py`, `a16_fxfinal.py` | fx → constant → delegate → item mapping (`a16_fxfinal.json`) |
| `a08_final.py` | `btn_*` thumbnail → unit mapping (`a08_final.json`) |
| `a09_names.py`, `a11_fxgroup.py`, `a12_drift.py`, `a17_unref.py` | naming-convention statistics, version-drift analysis |
| `a10_itemtable.py` | the 778-row per-item table → `reports/items-assets.csv` |
| `gen_report_05.py` | this report |

FFDec used for the SWF introspection: `tools/ffdec/ffdec-cli.exe` v26.3.0.

---

## Appendix A — Machine-readable per-item table (CSV, 778 rows)

Same content as `reports/items-assets.csv`. Copy the block below verbatim.

```csv
id,name,type,category_id,subcategory_id,subcat_functional,img_name,sprite_files,thumb_files,sprite_ok,thumb_ok
1,House I,b,1,11,111,0001_house_1_m,assets/sprites/0001_house_1_m.swf,assets/thumbs/0001_house_1_m.jpg,Y,Y
2,Wood Factory I,b,1,12,129,0002_depot_wood_1_m,assets/sprites/0002_depot_wood_1_m.swf,assets/thumbs/0002_depot_wood_1_m.jpg,Y,Y
3,Oil Factory I,b,1,12,129,0003_depot_oil_1_m,assets/sprites/0003_depot_oil_1_m.swf,assets/thumbs/0003_depot_oil_1_m.jpg,Y,Y
4,Steel Factory I,b,1,12,129,0004_depot_steel_1_m,assets/sprites/0004_depot_steel_1_m.swf,assets/thumbs/0004_depot_steel_1_m.jpg,Y,Y
5,Gold Factory I,b,1,12,129,0005_depot_gold_1_m,assets/sprites/0005_depot_gold_1_m.swf,assets/thumbs/0005_depot_gold_1_m.jpg,Y,Y
6,Wood Factory II,b,1,12,129,0006_depot_wood_2_m,assets/sprites/0006_depot_wood_2_m.swf,assets/thumbs/0006_depot_wood_2_m.jpg,Y,Y
7,Oil Factory II,b,1,12,129,0007_depot_oil_2_m,assets/sprites/0007_depot_oil_2_m.swf,assets/thumbs/0007_depot_oil_2_m.jpg,Y,Y
8,Steel Factory II,b,1,12,129,0008_depot_steel_2_m,assets/sprites/0008_depot_steel_2_m.swf,assets/thumbs/0008_depot_steel_2_m.jpg,Y,Y
9,Gold Factory II,b,1,12,129,0009_depot_gold_2_m,assets/sprites/0009_depot_gold_2_m.swf,assets/thumbs/0009_depot_gold_2_m.jpg,Y,Y
10,Wood Factory III,b,1,12,129,0010_depot_wood_3_m,assets/sprites/0010_depot_wood_3_m.swf,assets/thumbs/0010_depot_wood_3_m.jpg,Y,Y
11,Oil Factory III,b,1,12,129,0011_depot_oil_3_m,assets/sprites/0011_depot_oil_3_m.swf,assets/thumbs/0011_depot_oil_3_m.jpg,Y,Y
12,Steel Factory III,b,1,12,129,0012_depot_steel_3_m,assets/sprites/0012_depot_steel_3_m.swf,assets/thumbs/0012_depot_steel_3_m.jpg,Y,Y
13,Gold Factory III,b,1,12,129,0013_depot_gold_3_m,assets/sprites/0013_depot_gold_3_m.swf,assets/thumbs/0013_depot_gold_3_m.jpg,Y,Y
14,Wood Factory IV,b,1,12,129,0014_depot_wood_4_m,assets/sprites/0014_depot_wood_4_m.swf,assets/thumbs/0014_depot_wood_4_m.jpg,Y,Y
15,Oil Factory IV,b,1,12,129,0015_depot_oil_4_m,assets/sprites/0015_depot_oil_4_m.swf,assets/thumbs/0015_depot_oil_4_m.jpg,Y,Y
16,Steel Factory IV,b,1,12,129,0016_depot_steel_4_m,assets/sprites/0016_depot_steel_4_m.swf,assets/thumbs/0016_depot_steel_4_m.jpg,Y,Y
17,Gold Factory IV,b,1,12,129,0017_depot_gold_4_m,assets/sprites/0017_depot_gold_4_m.swf,assets/thumbs/0017_depot_gold_4_m.jpg,Y,Y
18,Market I,b,1,17,132,0018_market_1_m,assets/sprites/0018_market_1_m.swf,assets/thumbs/0018_market_1_m.jpg,Y,Y
19,Prison,b,8,81,812,0019_prision_m,assets/sprites/0019_prision_m.swf,assets/thumbs/0019_prision_m.jpg,Y,Y
22,Turret I,b,2,21,211,0022_tower_1_m,assets/sprites/0022_tower_1_m.swf,assets/thumbs/0022_tower_1_m.jpg,Y,Y
23,Wall I,b,2,22,221,0023_wall_1_m,assets/sprites/0023_wall_1_m.swf,assets/thumbs/0023_wall_1_m.jpg,Y,Y
24,Wall II,b,2,22,221,0024_wall_2_m,assets/sprites/0024_wall_2_m.swf,assets/thumbs/0024_wall_2_m.jpg,Y,Y
25,Wall III,b,2,22,221,0025_wall_3_m,assets/sprites/0025_wall_3_m.swf,assets/thumbs/0025_wall_3_m.jpg,Y,Y
26,Command Center,b,1,17,135,0026_command_center_1_m,assets/sprites/0026_command_center_1_m.swf,assets/thumbs/0026_command_center_1_m.jpg,Y,Y
28,Hospital,b,1,17,35,0028_hospital_1_m,assets/sprites/0028_hospital_1_m.swf,assets/thumbs/0028_hospital_1_m.jpg,Y,Y
30,Academy I,b,3,31,111,0030_academy_1_m,assets/sprites/0030_academy_1_m.swf,assets/thumbs/0030_academy_1_m.jpg,Y,Y
31,Bazooka Academy I,b,3,31,111,0031_bazooka_academy_1_m,assets/sprites/0031_bazooka_academy_1_m.swf,assets/thumbs/0031_bazooka_academy_1_m.jpg,Y,Y
37,Hangar I,b,3,33,111,0037_hangar_1_m,assets/sprites/0037_hangar_1_m.swf,assets/thumbs/0037_hangar_1_m.jpg,Y,Y
38,Tank Academy I,b,3,32,111,0038_cannon_academy_1_m,assets/sprites/0038_cannon_academy_1_m.swf,assets/thumbs/0038_cannon_academy_1_m.jpg,Y,Y
39,Turret IV,b,2,21,211,0039_tower_2_m,assets/sprites/0039_tower_2_m.swf,assets/thumbs/0039_tower_2_m.jpg,Y,Y
40,Jeep garage I,b,3,32,111,0040_workshop_1_m,assets/sprites/0040_workshop_1_m.swf,assets/thumbs/0040_workshop_1_m.jpg,Y,Y
41,Academy II,b,3,31,111,0041_academy_2_m,assets/sprites/0041_academy_2_m.swf,assets/thumbs/0041_academy_2_m.jpg,Y,Y
42,Academy III,b,3,31,111,0042_academy_3_m,assets/sprites/0042_academy_3_m.swf,assets/thumbs/0042_academy_3_m.jpg,Y,Y
43,Bazooka Academy II,b,3,31,111,0043_bazooka_academy_2_m,assets/sprites/0043_bazooka_academy_2_m.swf,assets/thumbs/0043_bazooka_academy_2_m.jpg,Y,Y
44,Bazooka Academy III,b,3,31,111,0044_bazooka_academy_3_m,assets/sprites/0044_bazooka_academy_3_m.swf,assets/thumbs/0044_bazooka_academy_3_m.jpg,Y,Y
45,Dual-Rocket Turret,b,2,21,211,0045_tower_3_m,assets/sprites/0045_tower_3_m.swf,assets/thumbs/0045_tower_3_m.jpg,Y,Y
46,Cannon Turret,b,2,21,211,0046_tower_4_m,assets/sprites/0046_tower_4_m.swf,assets/thumbs/0046_tower_4_m.jpg,Y,Y
47,House II,b,1,11,111,0047_house_2_m,assets/sprites/0047_house_2_m.swf,assets/thumbs/0047_house_2_m.jpg,Y,Y
48,House III,b,1,11,111,0048_house_3_m,assets/sprites/0048_house_3_m.swf,assets/thumbs/0048_house_3_m.jpg,Y,Y
49,Turret III,b,2,21,211,0049_torreta_horacio_m,assets/sprites/0049_torreta_horacio_m.swf,assets/thumbs/0049_torreta_horacio_m.jpg,Y,Y
50,Bunker I,b,2,24,211,0050_bunker_1_m,assets/sprites/0050_bunker_1_m.swf,assets/thumbs/0050_bunker_1_m.jpg,Y,Y
51,Bunker II,b,2,24,211,0051_bunker_2_m,assets/sprites/0051_bunker_2_m.swf,assets/thumbs/0051_bunker_2_m.jpg,Y,Y
52,Bunker III,b,2,24,211,0052_bunker_3_m,assets/sprites/0052_bunker_3_m.swf,assets/thumbs/0052_bunker_3_m.jpg,Y,Y
53,Mega Bunker,b,2,24,211,0053_bunker_4_m,assets/sprites/0053_bunker_4_m.swf,assets/thumbs/0053_bunker_4_m.jpg,Y,Y
54,Helicopter Hangar I,b,3,33,111,0054_copter_hangar_1_m,assets/sprites/0054_copter_hangar_1_m.swf,assets/thumbs/0054_copter_hangar_1_m.jpg,Y,Y
55,Helicopter Hangar II,b,3,33,111,0055_copter_hangar_2_m,assets/sprites/0055_copter_hangar_2_m.swf,assets/thumbs/0055_copter_hangar_2_m.jpg,Y,Y
56,Helicopter Hangar III,b,3,33,111,0056_copter_hangar_3_m,assets/sprites/0056_copter_hangar_3_m.swf,assets/thumbs/0056_copter_hangar_3_m.jpg,Y,Y
57,Turret II,b,2,21,211,0057_torreta_ruben_m,assets/sprites/0057_torreta_ruben_m.swf,assets/thumbs/0057_torreta_ruben_m.jpg,Y,Y
58,Command Center II,b,1,17,135,0058_command_center_2_m,assets/sprites/0058_command_center_2_m.swf,assets/thumbs/0058_command_center_2_m.jpg,Y,Y
59,Command Center III,b,1,17,135,0059_command_center_3_m,assets/sprites/0059_command_center_3_m.swf,assets/thumbs/0059_command_center_3_m.jpg,Y,Y
60,Command Center IV,b,1,17,135,0060_command_center_4_m,assets/sprites/0060_command_center_4_m.swf,assets/thumbs/0060_command_center_4_m.jpg,Y,Y
61,Allies Building,b,1,17,111,0061_allies_building_m,assets/sprites/0061_allies_building_m.swf,assets/thumbs/0061_allies_building_m.jpg,Y,Y
62,Tank Academy II,b,3,32,111,0062_cannon_academy_2_m,assets/sprites/0062_cannon_academy_2_m.swf,assets/thumbs/0062_cannon_academy_2_m.jpg,Y,Y
63,Tank Academy III,b,3,32,111,0063_cannon_academy_3_m,assets/sprites/0063_cannon_academy_3_m.swf,assets/thumbs/0063_cannon_academy_3_m.jpg,Y,Y
64,Jeep garage II,b,3,32,111,0064_workshop_2_m,assets/sprites/0064_workshop_2_m.swf,assets/thumbs/0064_workshop_2_m.jpg,Y,Y
65,Jeep garage III,b,3,32,111,0065_workshop_3_m,assets/sprites/0065_workshop_3_m.swf,assets/thumbs/0065_workshop_3_m.jpg,Y,Y
66,Stoneage,b,5,51,511,0066_stoneage_marvel_m,assets/sprites/0066_stoneage_marvel_m.swf,assets/thumbs/0066_stoneage_marvel_m.jpg,Y,Y
67,Machu Picchu,b,5,51,511,0067_machupichu_m,assets/sprites/0067_machupichu_m.swf,assets/thumbs/0067_machupichu_m.jpg,Y,Y
68,Iguazu,b,5,51,511,0068_iguazu_m,assets/sprites/0068_iguazu_m.swf,assets/thumbs/0068_iguazu_m.jpg,Y,Y
69,Sphynx,b,5,51,511,0069_sfinx_m,assets/sprites/0069_sfinx_m.swf,assets/thumbs/0069_sfinx_m.jpg,Y,Y
70,Inca God,b,5,51,511,0070_inca_god_m,assets/sprites/0070_inca_god_m.swf,assets/thumbs/0070_inca_god_m.jpg,Y,Y
71,Chichenitza,b,5,51,511,0071_chichenitza_m,assets/sprites/0071_chichenitza_m.swf,assets/thumbs/0071_chichenitza_m.jpg,Y,Y
72,Babilonia,b,5,51,511,0072_babilonia_m,assets/sprites/0072_babilonia_m.swf,assets/thumbs/0072_babilonia_m.jpg,Y,Y
73,Ankor,b,5,51,511,0073_Ankor_m,assets/sprites/0073_Ankor_m.swf,assets/thumbs/0073_Ankor_m.jpg,Y,Y
74,Allies Market,b,1,17,132,0074_Allies_market_m,assets/sprites/0074_Allies_market_m.swf,assets/thumbs/0074_Allies_market_m.jpg,Y,Y
75,Recon center,b,1,17,132,0075_Spy_center_m,assets/sprites/0075_Spy_center_m.swf,assets/thumbs/0075_Spy_center_m.jpg,Y,Y
76,Hangar II,b,3,33,111,0076_hangar_2_m,assets/sprites/0076_hangar_2_m.swf,assets/thumbs/0076_hangar_2_m.jpg,Y,Y
77,Hangar III,b,3,33,111,0077_hangar_3_m,assets/sprites/0077_hangar_3_m.swf,assets/thumbs/0077_hangar_3_m.jpg,Y,Y
78,Wall IV,b,2,22,221,0078_wall_4_m,assets/sprites/0078_wall_4_m.swf,assets/thumbs/0078_wall_4_m.jpg,Y,Y
79,Wall V,b,2,22,221,0079_wall_5_m,assets/sprites/0079_wall_5_m.swf,assets/thumbs/0079_wall_5_m.jpg,Y,Y
80,Fortress I,b,2,23,231,0080_fortress_1_m,assets/sprites/0080_fortress_1_m.swf,assets/thumbs/0080_fortress_1_m.jpg,Y,Y
81,Fortress II,b,2,23,231,0081_fortress_2_m,assets/sprites/0081_fortress_2_m.swf,assets/thumbs/0081_fortress_2_m.jpg,Y,Y
82,Rocket Fortress,b,2,23,231,0082_fortress_3_m,assets/sprites/0082_fortress_3_m.swf,assets/thumbs/0082_fortress_3_m.jpg,Y,Y
83,Fortress III,b,2,23,231,0083_fortress_4_m,assets/sprites/0083_fortress_4_m.swf,assets/thumbs/0083_fortress_4_m.jpg,Y,Y
84,Special Fortress,b,2,23,231,0084_fortress_5_m,assets/sprites/0084_fortress_5_m.swf,assets/thumbs/0084_fortress_5_m.jpg,Y,Y
85,Mega Fortress,b,2,23,231,0085_fortress_6_m,assets/sprites/0085_fortress_6_m.swf,assets/thumbs/0085_fortress_6_m.jpg,Y,Y
86,Robotic Center,b,1,17,111,0086_robotics_center,assets/sprites/0086_robotics_center.swf,assets/thumbs/0086_robotics_center.jpg,Y,Y
87,Turret VI,b,2,21,211,0087_tower_7_m,assets/sprites/0087_tower_7_m.swf,assets/thumbs/0087_tower_7_m.jpg,Y,Y
88,Turret V,b,2,21,211,0088_tower_8_m,assets/sprites/0088_tower_8_m.swf,assets/thumbs/0088_tower_8_m.jpg,Y,Y
89,Nuclear Plant,b,1,11,111,0089_nuclear_plant_m,assets/sprites/0089_nuclear_plant_m.swf,assets/thumbs/0089_nuclear_plant_m.jpg,Y,Y
90,Market II,b,1,17,132,0090_market_2_m,assets/sprites/0090_market_2_m.swf,assets/thumbs/0090_market_2_m.jpg,Y,Y
91,Market III,b,1,17,132,0091_market_3_m,assets/sprites/0091_market_3_m.swf,assets/thumbs/0091_market_3_m.jpg,Y,Y
92,Apple tree,b,4,41,411,0092_apple_tree_m,assets/sprites/0092_apple_tree_m.swf,assets/thumbs/0092_apple_tree_m.jpg,Y,Y
93,Pear tree,b,4,41,411,0093_pear_tree_m,assets/sprites/0093_pear_tree_m.swf,assets/thumbs/0093_pear_tree_m.jpg,Y,Y
94,Sponge bush,b,4,42,411,0094_sponge_bush_m,assets/sprites/0094_sponge_bush_m.swf,assets/thumbs/0094_sponge_bush_m.jpg,Y,Y
95,Little fountain,b,4,45,411,0095_little_fountain_m,assets/sprites/0095_little_fountain_m.swf,assets/thumbs/0095_little_fountain_m.jpg,Y,Y
96,White Flowers,b,4,42,411,0096_white_flowers_m,assets/sprites/0096_white_flowers_m.swf,assets/thumbs/0096_white_flowers_m.jpg,Y,Y
97,Red flowers,b,4,42,411,0097_red_flowers_m,assets/sprites/0097_red_flowers_m.swf,assets/thumbs/0097_red_flowers_m.jpg,Y,Y
98,Blue flowers,b,4,42,411,0098_blue_flowers_m,assets/sprites/0098_blue_flowers_m.swf,assets/thumbs/0098_blue_flowers_m.jpg,Y,Y
100,Red Leaf flowers,b,4,42,411,0100_red_leaf_flowers_m,assets/sprites/0100_red_leaf_flowers_m.swf,assets/thumbs/0100_red_leaf_flowers_m.jpg,Y,Y
101,Pink Leaf flowers,b,4,42,411,0101_pink_leaf_flowers_m,assets/sprites/0101_pink_leaf_flowers_m.swf,assets/thumbs/0101_pink_leaf_flowers_m.jpg,Y,Y
102,Blue Leaf flowers,b,4,42,411,0102_blue_leaf_flowers_m,assets/sprites/0102_blue_leaf_flowers_m.swf,assets/thumbs/0102_blue_leaf_flowers_m.jpg,Y,Y
103,Bush,b,4,42,411,0103_bush_m,assets/sprites/0103_bush_m.swf,assets/thumbs/0103_bush_m.jpg,Y,Y
104,Lamp,b,4,45,411,0104_bancos_farolas_m,assets/sprites/0104_bancos_farolas_m.swf,assets/thumbs/0104_bancos_farolas_m.jpg,Y,Y
105,Victory Arch,b,4,45,411,0105_victory_arch_m,assets/sprites/0105_victory_arch_m.swf,assets/thumbs/0105_victory_arch_m.jpg,Y,Y
106,Fountain,b,4,45,411,0106_fountain_m,assets/sprites/0106_fountain_m.swf,assets/thumbs/0106_fountain_m.jpg,Y,Y
107,Sculpture,b,4,44,411,0107_sculpture_m,assets/sprites/0107_sculpture_m.swf,assets/thumbs/0107_sculpture_m.jpg,Y,Y
108,Grape field,b,1,13,129,0108_grape_field_m,assets/sprites/0108_grape_field_m.swf,assets/thumbs/0108_grape_field_m.jpg,Y,Y
109,Corn field,b,1,13,129,0109_corn_field_m,assets/sprites/0109_corn_field_m.swf,assets/thumbs/0109_corn_field_m.jpg,Y,Y
110,Cow farm,b,1,13,129,0110_cow_farm_m,assets/sprites/0110_cow_farm_m.swf,assets/thumbs/0110_cow_farm_m.jpg,Y,Y
111,Max Security Prison,b,8,81,812,0111_prisoner_guile_m,assets/sprites/0111_prisoner_guile_m.swf,assets/thumbs/0111_prisoner_guile_m.jpg,Y,Y
112,Stolen Bazookas,b,8,81,812,0112_stolen_bazookas_m,assets/sprites/0112_stolen_bazookas_m.swf,assets/thumbs/0112_stolen_bazookas_m.jpg,Y,Y
113,Disabled Jeeps,b,8,81,812,0113_disabled_jeeps_m,assets/sprites/0113_disabled_jeeps_m.swf,assets/thumbs/0113_disabled_jeeps_m.jpg,Y,Y
114,Jeep wheels,b,8,81,812,0114_jeep_weels_m,assets/sprites/0114_jeep_weels_m.swf,assets/thumbs/0114_jeep_weels_m.jpg,Y,Y
115,Supertank ammo,b,8,81,812,0115_supertank_ammo_1_m,assets/sprites/0115_supertank_ammo_1_m.swf,assets/thumbs/0115_supertank_ammo_1_m.jpg,Y,Y
116,Supertank ammo,b,8,81,812,0116_supertank_ammo_2_m,assets/sprites/0116_supertank_ammo_2_m.swf,assets/thumbs/0116_supertank_ammo_2_m.jpg,Y,Y
117,Disabled Supertank,b,8,81,812,0117_disabled_supertank_m,assets/sprites/0117_disabled_supertank_m.swf,assets/thumbs/0117_disabled_supertank_m.jpg,Y,Y
118,Mind Control Laboratory,b,2,23,231,0118_laboratory_m,assets/sprites/0118_laboratory_m.swf,assets/thumbs/0118_laboratory_m.jpg,Y,Y
119,Tank wheels,b,8,81,812,0119_tank_wheels_m,assets/sprites/0119_tank_wheels_m.swf,assets/thumbs/0119_tank_wheels_m.jpg,Y,Y
120,Stolen missiles,b,8,81,812,0120_stolen_missiles_m,assets/sprites/0120_stolen_missiles_m.swf,assets/thumbs/0120_stolen_missiles_m.jpg,Y,Y
121,Radio,b,8,81,812,0121_radio_m,assets/sprites/0121_radio_m.swf,assets/thumbs/0121_radio_m.jpg,Y,Y
122,Heliport,b,8,81,812,0122_helipuerto_m,assets/sprites/0122_helipuerto_m.swf,assets/thumbs/0122_helipuerto_m.jpg,Y,Y
123,Red Fortress,b,8,81,812,0123_red_fortress_m,assets/sprites/0123_red_fortress_m.swf,assets/thumbs/0123_red_fortress_m.jpg,Y,Y
124,Disabled Tanks,b,8,81,812,0124_disabled_tanks_m,assets/sprites/0124_disabled_tanks_m.swf,assets/thumbs/0124_disabled_tanks_m.jpg,Y,Y
125,Laboratory,b,8,81,812,0125_laboratory_m,assets/sprites/0125_laboratory_m.swf,assets/thumbs/0125_laboratory_m.jpg,Y,Y
126,Enemy's airport,b,8,81,812,0126_enemy_airport_m,assets/sprites/0126_enemy_airport_m.swf,assets/thumbs/0126_enemy_airport_m.jpg,Y,Y
127,Enemy's harbour,b,8,81,812,0127_enemy_harbour_m,assets/sprites/0127_enemy_harbour_m.swf,,Y,N
128,Rocket launcher,b,8,81,812,0128_rocket_launcher_m,assets/sprites/0128_rocket_launcher_m.swf,assets/thumbs/0128_rocket_launcher_m.jpg,Y,Y
129,Flamethrower Academy,b,3,34,111,0129_fire_academy_m,assets/sprites/0129_fire_academy_m.swf,assets/thumbs/0129_fire_academy_m.jpg,Y,Y
130,Dominion Tank Academy,b,3,34,111,0130_black_tank_academy_m,assets/sprites/0130_black_tank_academy_m.swf,assets/thumbs/0130_black_tank_academy_m.jpg,Y,Y
131,Stealth Fighter Hangar,b,3,34,111,0131_black_aircraft_academy_m,assets/sprites/0131_black_aircraft_academy_m.swf,assets/thumbs/0131_black_aircraft_academy_m.jpg,Y,Y
132,Troubled Traveller,b,4,45,411,0132_troubled_traveller_m,assets/sprites/0132_troubled_traveller_m.swf,,Y,N
133,Injured Soldier,b,4,45,411,0133_injured_soldier_m,assets/sprites/0133_injured_soldier_m.swf,,Y,N
134,Field Hospital,b,3,34,111,0134_field_hospital_m,assets/sprites/0134_field_hospital_m.swf,assets/thumbs/0134_field_hospital_m.jpg,Y,Y
135,Mechanical Garage,b,3,34,111,0135_engineer_barrack_m,assets/sprites/0135_engineer_barrack_m.swf,assets/thumbs/0135_engineer_barrack_m.jpg,Y,Y
136,General Sculpture,b,4,42,411,0136_general_sculpture_m,assets/sprites/0136_general_sculpture_m.swf,assets/thumbs/0136_general_sculpture_m.jpg,Y,Y
137,Spy Academy,b,3,34,111,0137_spy_academy_m,,,N,N
138,Mr T. Academy,b,12,121,111,0138_mr_t_academy_m,assets/sprites/0138_mr_t_academy_m.swf,assets/thumbs/0138_mr_t_academy_m.jpg,Y,Y
139,Area 51,b,1,17,111,0139_area_51_m,assets/sprites/0139_area_51_m.swf,assets/thumbs/0139_area_51_m.jpg,Y,Y
140,Recruitment Prize,b,1,17,111,0140_recruitment_m,assets/sprites/0140_recruitment_m.swf,assets/thumbs/0140_recruitment_m.jpg,Y,Y
141,Bazooka Academy IV,b,3,31,111,0141_bazooka_academy_4_m,assets/sprites/0141_bazooka_academy_4_m.swf,assets/thumbs/0141_bazooka_academy_4_m.jpg,Y,Y
142,Bazooka Academy V,b,3,31,111,0142_bazooka_academy_5_m,assets/sprites/0142_bazooka_academy_5_m.swf,assets/thumbs/0142_bazooka_academy_5_m.jpg,Y,Y
143,Academy IV,b,3,31,111,0143_academy_4_m,assets/sprites/0143_academy_4_m.swf,assets/thumbs/0143_academy_4_m.jpg,Y,Y
144,Academy V,b,3,31,111,0144_academy_5_m,assets/sprites/0144_academy_5_m.swf,assets/thumbs/0144_academy_5_m.jpg,Y,Y
145,Mortar Academy,b,3,35,111,0145_mortar_academy_m,assets/sprites/0145_mortar_academy_m.swf,assets/thumbs/0145_mortar_academy_m.jpg,Y,Y
146,Helicopter Hangar IV,b,3,33,111,0146_copter_hangar_4_m,assets/sprites/0146_copter_hangar_4_m.swf,assets/thumbs/0146_copter_hangar_4_m.jpg,Y,Y
147,Helicopter Hangar V,b,3,33,111,0147_copter_hangar_5_m,assets/sprites/0147_copter_hangar_5_m.swf,assets/thumbs/0147_copter_hangar_5_m.jpg,Y,Y
148,Demolition Tank Academy,b,3,35,111,0148_artillery_garage_m,assets/sprites/0148_artillery_garage_m.swf,assets/thumbs/0148_artillery_garage_m.jpg,Y,Y
149,Antiaircraft garage,b,3,34,111,0149_antiaircraft_garage_m,assets/sprites/0149_antiaircraft_garage_m.swf,assets/thumbs/0149_antiaircraft_garage_m.jpg,Y,Y
150,Tank Academy IV,b,3,32,111,0150_tank_academy_4_m,assets/sprites/0150_tank_academy_4_m.swf,assets/thumbs/0150_tank_academy_4_m.jpg,Y,Y
151,Tank Academy V,b,3,32,111,0151_tank_academy_5_m,assets/sprites/0151_tank_academy_5_m.swf,assets/thumbs/0151_tank_academy_5_m.jpg,Y,Y
152,Robo flag,b,12,121,411,0152_robo_flag_m,assets/sprites/0152_robo_flag_m.swf,assets/thumbs/0152_robo_flag_m.jpg,Y,Y
153,Robo statue,b,12,121,411,0153_robo_statue_m,assets/sprites/0153_robo_statue_m.swf,assets/thumbs/0153_robo_statue_m.jpg,Y,Y
154,Crusader Soldier Academy,b,12,121,111,0154_robo_soldier_academy_m,assets/sprites/0154_robo_soldier_academy_m.swf,assets/thumbs/0154_robo_soldier_academy_m.jpg,Y,Y
155,Crusader Swordsman Academy,b,12,121,111,0155_robo_swordsman_academy_m,assets/sprites/0155_robo_swordsman_academy_m.swf,assets/thumbs/0155_robo_swordsman_academy_m.jpg,Y,Y
156,Crusader Bazooka Academy,b,12,121,111,0156_robo_bazooka_academy_m,assets/sprites/0156_robo_bazooka_academy_m.swf,assets/thumbs/0156_robo_bazooka_academy_m.jpg,Y,Y
157,Jet Soldier Academy,b,12,121,111,0157_jet_robosoldier_academy_m,assets/sprites/0157_jet_robosoldier_academy_m.swf,assets/thumbs/0157_jet_robosoldier_academy_m.jpg,Y,Y
158,Motorized Soldier Academy,b,12,121,111,0158_motorized_robosoldier_academy_m,assets/sprites/0158_motorized_robosoldier_academy_m.swf,assets/thumbs/0158_motorized_robosoldier_academy_m.jpg,Y,Y
159,Retaliator Academy,b,12,121,111,0159_retaliator_academy_m,assets/sprites/0159_retaliator_academy_m.swf,assets/thumbs/0159_retaliator_academy_m.jpg,Y,Y
160,Megalancer Academy,b,12,121,111,0160_robo_lancer_academy_m,assets/sprites/0160_robo_lancer_academy_m.swf,assets/thumbs/0160_robo_lancer_academy_m.jpg,Y,Y
161,Crusader Tank Academy,b,12,121,111,0161_demolisher_tank_academy_m,assets/sprites/0161_demolisher_tank_academy_m.swf,assets/thumbs/0161_demolisher_tank_academy_m.jpg,Y,Y
162,Dreadnought Academy,b,12,121,111,0162_dreadnought_academy_m,assets/sprites/0162_dreadnought_academy_m.swf,assets/thumbs/0162_dreadnought_academy_m.jpg,Y,Y
163,House,b,12,121,111,0163_robo_house_m,assets/sprites/0163_robo_house_m.swf,assets/thumbs/0163_robo_house_m.jpg,Y,Y
164,Laser Turret,b,12,121,211,0164_robo_turret_1_m,assets/sprites/0164_robo_turret_1_m.swf,assets/thumbs/0164_robo_turret_1_m.jpg,Y,Y
165,Tesla Turret,b,12,121,211,0165_robo_turret_2_m,assets/sprites/0165_robo_turret_2_m.swf,assets/thumbs/0165_robo_turret_2_m.jpg,Y,Y
166,Wall,b,12,121,221,0166_robo_wall_m,assets/sprites/0166_robo_wall_m.swf,assets/thumbs/0166_robo_wall_m.jpg,Y,Y
167,Field,b,12,121,129,0167_robo_farm_m,assets/sprites/0167_robo_farm_m.swf,assets/thumbs/0167_robo_farm_m.jpg,Y,Y
168,Crusader Skylander Hangar,b,12,121,111,0168_skylander_hangar_m,assets/sprites/0168_skylander_hangar_m.swf,assets/thumbs/0168_skylander_hangar_m.jpg,Y,Y
169,Mega-Axe Academy,b,12,121,111,0169_roboaxe_academy_m,assets/sprites/0169_roboaxe_academy_m.swf,assets/thumbs/0169_roboaxe_academy_m.jpg,Y,Y
170,Giant Walker Factory,b,12,121,111,0170_giant_walker_factory_m,assets/sprites/0170_giant_walker_factory_m.swf,assets/thumbs/0170_giant_walker_factory_m.jpg,Y,Y
171,Missile Tank Academy,b,12,121,111,0171_missile_tank_academy_m,assets/sprites/0171_missile_tank_academy_m.swf,assets/thumbs/0171_missile_tank_academy_m.jpg,Y,Y
172,Steel Claws Academy,b,12,121,111,0172_steel_claws_academy_m,assets/sprites/0172_steel_claws_academy_m.swf,assets/thumbs/0172_steel_claws_academy_m.jpg,Y,Y
173,Development Wall,b,12,121,111,0166_robo_wall_m,assets/sprites/0166_robo_wall_m.swf,assets/thumbs/0166_robo_wall_m.jpg,Y,Y
174,Fireman Academy,b,3,34,111,0174_fireman_academy_m,assets/sprites/0174_fireman_academy_m.swf,assets/thumbs/0174_fireman_academy_m.jpg,Y,Y
175,Babilonian Temple,b,5,51,511,0175_alejandria_m,assets/sprites/0175_alejandria_m.swf,assets/thumbs/0175_alejandria_m.jpg,Y,Y
176,Cash Wonder,b,5,51,511,0176_maravilla_m,assets/sprites/0176_maravilla_m.swf,assets/thumbs/0176_maravilla_m.jpg,Y,Y
177,Axe Zoldier Academy,b,12,121,111,0177_orc_soldier_academy_1_m,assets/sprites/0177_orc_soldier_academy_1_m.swf,assets/thumbs/0177_orc_soldier_academy_1_m.jpg,Y,Y
178,Gun Zoldier Academy,b,12,121,111,0178_orc_soldier_academy_2_m,assets/sprites/0178_orc_soldier_academy_2_m.swf,assets/thumbs/0178_orc_soldier_academy_2_m.jpg,Y,Y
179,Xplosive Ork Academy,b,12,121,111,0179_orc_boss_academy_m,assets/sprites/0179_orc_boss_academy_m.swf,assets/thumbs/0179_orc_boss_academy_m.jpg,Y,Y
180,Bear Ridda Academy,b,12,121,111,0180_orc_rider_academy_m,assets/sprites/0180_orc_rider_academy_m.swf,assets/thumbs/0180_orc_rider_academy_m.jpg,Y,Y
181,Horned Badass Factory,b,12,121,111,0181_orc_robot_factory_m,assets/sprites/0181_orc_robot_factory_m.swf,assets/thumbs/0181_orc_robot_factory_m.jpg,Y,Y
182,Flamethrowa Academy,b,12,121,111,0182_orc_flamethrower_academy_m,assets/sprites/0182_orc_flamethrower_academy_m.swf,assets/thumbs/0182_orc_flamethrower_academy_m.jpg,Y,Y
183,Ork House,b,12,121,111,0183_orc_house_m,assets/sprites/0183_orc_house_m.swf,assets/thumbs/0183_orc_house_m.jpg,Y,Y
184,Ork Farm,b,12,121,129,0184_orc_farm_m,assets/sprites/0184_orc_farm_m.swf,assets/thumbs/0184_orc_farm_m.jpg,Y,Y
185,Ork Turret II,b,12,121,211,0185_orc_turret_m,assets/sprites/0185_orc_turret_m.swf,assets/thumbs/0185_orc_turret_m.jpg,Y,Y
186,Ork Wall,b,12,121,221,0186_orc_wall_m,assets/sprites/0186_orc_wall_m.swf,assets/thumbs/0186_orc_wall_m.jpg,Y,Y
187,Krazy Monsta Statue,b,12,121,411,0187_orc_deco_1_m,assets/sprites/0187_orc_deco_1_m.swf,assets/thumbs/0187_orc_deco_1_m.jpg,Y,Y
188,Powa Banna,b,12,121,411,0188_orc_deco_2_m,assets/sprites/0188_orc_deco_2_m.swf,assets/thumbs/0188_orc_deco_2_m.jpg,Y,Y
189,Ork Turret I,b,12,121,211,0189_orc_turret_2_m,assets/sprites/0189_orc_turret_2_m.swf,assets/thumbs/0189_orc_turret_2_m.jpg,Y,Y
190,Molotov Kopta Hangar,b,12,121,111,0190_helicopter_hangar2_m,assets/sprites/0190_helicopter_hangar2_m.swf,assets/thumbs/0190_helicopter_hangar2_m.jpg,Y,Y
191,Ork Tank Academy,b,3,35,111,0191_camion_orco_academy_m,assets/sprites/0191_camion_orco_academy_m.swf,assets/thumbs/0191_camion_orco_academy_m.jpg,Y,Y
192,Knife Throwa Academy,b,12,121,111,0192_orc_lanzamachetes_academy_m,assets/sprites/0192_orc_lanzamachetes_academy_m.swf,assets/thumbs/0192_orc_lanzamachetes_academy_m.jpg,Y,Y
193,Kamikaze Bros Academy,b,12,121,111,0193_orc_mascota_kamikaze_academy_m,assets/sprites/0193_orc_mascota_kamikaze_academy_m.swf,assets/thumbs/0193_orc_mascota_kamikaze_academy_m.jpg,Y,Y
194,Big Handsaw Ork Factory,b,12,121,111,0194_orc_robot_2_factory_m,assets/sprites/0194_orc_robot_2_factory_m.swf,assets/thumbs/0194_orc_robot_2_factory_m.jpg,Y,Y
195,Orc Headquarters,b,1,17,135,0195_orc_headquarters,assets/sprites/0195_orc_headquarters.swf,assets/thumbs/0195_orc_headquarters.jpg,Y,Y
196,Orc Sponge Bush,b,12,121,411,0196_orc_sponge_bush,assets/sprites/0196_orc_sponge_bush.swf,assets/thumbs/0196_orc_sponge_bush.jpg,Y,Y
197,Orc Lamp,b,12,121,411,0197_orc_lamp,assets/sprites/0197_orc_lamp.swf,assets/thumbs/0197_orc_lamp.jpg,Y,Y
198,Orc Bush,b,12,121,411,0198_orc_bush,assets/sprites/0198_orc_bush.swf,assets/thumbs/0198_orc_bush.jpg,Y,Y
200,Silo II,b,1,14,0,0200_orc_silo,assets/sprites/0200_orc_silo.swf,assets/thumbs/0200_orc_silo.jpg,Y,Y
201,Orc Bunker ,b,2,24,211,0201_orc_bunker,assets/sprites/0201_orc_bunker.swf,assets/thumbs/0201_orc_bunker.jpg,Y,Y
202,Orc Resource Building,b,1,12,129,0202_orc_resource_building,assets/sprites/0202_orc_resource_building.swf,assets/thumbs/0202_orc_resource_building.jpg,Y,Y
203,Orc Harbour,b,1,14,0,0203_orc_harbour,assets/sprites/0203_orc_harbour.swf,assets/thumbs/0203_orc_harbour.jpg,Y,Y
204,Disabled Orc Supertank,b,8,81,812,0204_disabled_orc_supertank,assets/sprites/0204_disabled_orc_supertank.swf,assets/thumbs/0204_disabled_orc_supertank.jpg,Y,Y
205,Orc Fortress,b,2,23,231,0205_orc_fortress,assets/sprites/0205_orc_fortress.swf,assets/thumbs/0205_orc_fortress.jpg,Y,Y
206,Enemy Ork Wall,b,12,121,221,0186_orc_wall_m,assets/sprites/0186_orc_wall_m.swf,assets/thumbs/0186_orc_wall_m.jpg,Y,Y
207,Enemy Ork Turret I,b,12,121,211,0189_orc_turret_2_m,assets/sprites/0189_orc_turret_2_m.swf,assets/thumbs/0189_orc_turret_2_m.jpg,Y,Y
208,Enemy Ork Turret II,b,12,121,211,0185_orc_turret_m,assets/sprites/0185_orc_turret_m.swf,assets/thumbs/0185_orc_turret_m.jpg,Y,Y
209,Crusader Priest Academy,b,12,121,111,209_crusader_priest_academy,assets/sprites/209_crusader_priest_academy.swf,assets/thumbs/209_crusader_priest_academy.jpg,Y,Y
210,Crusader Bot Factory,b,12,121,111,210_crusader_bot_factory,assets/sprites/210_crusader_bot_factory.swf,assets/thumbs/210_crusader_bot_factory.jpg,Y,Y
211,Viking Axe Academy,b,12,121,111,211_axeman_academy,assets/sprites/211_axeman_academy.swf,assets/thumbs/211_axeman_academy.jpg,Y,Y
212,Viking Soldier Academy,b,12,121,111,212_dwarf_soldier_academy,assets/sprites/212_dwarf_soldier_academy.swf,assets/thumbs/212_dwarf_soldier_academy.jpg,Y,Y
213,Bear Knight Academy,b,12,121,111,213_bear_knight_academy,assets/sprites/213_bear_knight_academy.swf,assets/thumbs/213_bear_knight_academy.jpg,Y,Y
214,Viking Tank Academy,b,12,121,111,214_dwarf_tank_academy,assets/sprites/214_dwarf_tank_academy.swf,assets/thumbs/214_dwarf_tank_academy.jpg,Y,Y
215,Viking Airship Hangar,b,12,121,111,215_viking_copter_II_hangar,assets/sprites/215_viking_copter_II_hangar.swf,assets/thumbs/215_viking_copter_II_hangar.jpg,Y,Y
216,Viking Hammerer Factory,b,12,121,111,216_megahammer_dwarf_factory,assets/sprites/216_megahammer_dwarf_factory.swf,assets/thumbs/216_megahammer_dwarf_factory.jpg,Y,Y
217,Viking Core Factory,b,12,121,111,217_dwarf_armored_core_factory,assets/sprites/217_dwarf_armored_core_factory.swf,assets/thumbs/217_dwarf_armored_core_factory.jpg,Y,Y
218,Viking House,b,12,121,111,218_dwarf_house,assets/sprites/218_dwarf_house.swf,assets/thumbs/218_dwarf_house.jpg,Y,Y
219,Viking Field,b,12,121,129,219_dwarf_farm,assets/sprites/219_dwarf_farm.swf,assets/thumbs/219_dwarf_farm.jpg,Y,Y
220,Viking Turret I,b,12,121,211,220_dwarf_turret_1,assets/sprites/220_dwarf_turret_1.swf,assets/thumbs/220_dwarf_turret_1.jpg,Y,Y
221,Viking Turret II,b,12,121,211,221_dwarf_turret_2,assets/sprites/221_dwarf_turret_2.swf,assets/thumbs/221_dwarf_turret_2.jpg,Y,Y
222,Viking Wall,b,12,121,221,222_dwarf_wall,assets/sprites/222_dwarf_wall.swf,assets/thumbs/222_dwarf_wall.jpg,Y,Y
223,Hammerer Statue,b,12,121,411,223_dwarf_deco_1,assets/sprites/223_dwarf_deco_1.swf,assets/thumbs/223_dwarf_deco_1.jpg,Y,Y
224,Viking Fountain,b,12,121,411,224_dwarf_deco_2,assets/sprites/224_dwarf_deco_2.swf,assets/thumbs/224_dwarf_deco_2.jpg,Y,Y
225,Alien Wall,b,12,121,221,225_alien_wall,assets/sprites/225_alien_wall.swf,assets/thumbs/225_alien_wall.jpg,Y,Y
226,Alien Turret I,b,12,121,211,226_alien_turret_1,assets/sprites/226_alien_turret_1.swf,assets/thumbs/226_alien_turret_1.jpg,Y,Y
227,Alien Turret II,b,12,121,211,227_alien_turret_2,assets/sprites/227_alien_turret_2.swf,assets/thumbs/227_alien_turret_2.jpg,Y,Y
228,Spider Wall,b,12,121,221,228_spider_wall,assets/sprites/228_spider_wall.swf,assets/thumbs/228_spider_wall.jpg,Y,Y
229,Spider Turret I,b,12,121,211,229_spider_turret_1,assets/sprites/229_spider_turret_1.swf,assets/thumbs/229_spider_turret_1.jpg,Y,Y
230,Spider Turret II,b,12,121,211,230_spider_turret_2,assets/sprites/230_spider_turret_2.swf,assets/thumbs/230_spider_turret_2.jpg,Y,Y
231,War Tree,b,12,121,411,231_dwarf_deco_3,assets/sprites/231_dwarf_deco_3.swf,assets/thumbs/231_dwarf_deco_3.jpg,Y,Y
232,Magic Lake,b,12,121,411,232_dwarf_deco_4,assets/sprites/232_dwarf_deco_4.swf,assets/thumbs/232_dwarf_deco_4.jpg,Y,Y
233,Viking Bazooka Academy,b,12,121,111,233_viking_bazooka_academy,assets/sprites/233_viking_bazooka_academy.swf,assets/thumbs/233_viking_bazooka_academy.jpg,Y,Y
234,Viking MotoSquad Academy,b,12,121,111,234_viking_motosquad_academy,assets/sprites/234_viking_motosquad_academy.swf,assets/thumbs/234_viking_motosquad_academy.jpg,Y,Y
235,Rune Golem Academy,b,12,121,111,235_viking_rune_golem_academy,assets/sprites/235_viking_rune_golem_academy.swf,assets/thumbs/235_viking_rune_golem_academy.jpg,Y,Y
236,Viking Sniper Academy,b,12,121,111,236_viking_sniper_academy,assets/sprites/236_viking_sniper_academy.swf,assets/thumbs/236_viking_sniper_academy.jpg,Y,Y
237,Viking Butcher Academy,b,12,121,111,237_viking_butcher_academy,assets/sprites/237_viking_butcher_academy.swf,assets/thumbs/237_viking_butcher_academy.jpg,Y,Y
238,Kamikaze Academy,b,12,121,111,238_kamikaze_academy,assets/sprites/238_kamikaze_academy.swf,assets/thumbs/238_kamikaze_academy.jpg,Y,Y
239,Laser Viking Academy,b,12,121,111,239_laser_viking_academy,assets/sprites/239_laser_viking_academy.swf,assets/thumbs/239_laser_viking_academy.jpg,Y,Y
240,Nebular Spearman Academy,b,12,121,111,240_avatar_soldado_academy,assets/sprites/240_avatar_soldado_academy.swf,assets/thumbs/240_avatar_soldado_academy.jpg,Y,Y
241,Nebular Archer Academy,b,12,121,111,241_avatar_arquero_academy,assets/sprites/241_avatar_arquero_academy.swf,assets/thumbs/241_avatar_arquero_academy.jpg,Y,Y
242,Greatsword Warrior Academy,b,12,121,111,242_avatar_great_warrior_academy,assets/sprites/242_avatar_great_warrior_academy.swf,assets/thumbs/242_avatar_great_warrior_academy.jpg,Y,Y
243,Nebular Rider Academy,b,12,121,111,243_avatar_jinete_academy,assets/sprites/243_avatar_jinete_academy.swf,assets/thumbs/243_avatar_jinete_academy.jpg,Y,Y
244,Nebular Wall,b,12,121,221,244_avatar_wall,assets/sprites/244_avatar_wall.swf,assets/thumbs/244_avatar_wall.jpg,Y,Y
245,Nebular Turret,b,12,121,211,245_avatar_turret,assets/sprites/245_avatar_turret.swf,assets/thumbs/245_avatar_turret.jpg,Y,Y
246,Nebular House,b,12,121,111,246_avatar_house,assets/sprites/246_avatar_house.swf,assets/thumbs/246_avatar_house.jpg,Y,Y
247,Nebular Field,b,12,121,129,247_avatar_farm,assets/sprites/247_avatar_farm.swf,assets/thumbs/247_avatar_farm.jpg,Y,Y
248,Ancient Nebular Tree,b,12,121,411,248_avatar_deco,assets/sprites/248_avatar_deco.swf,assets/thumbs/248_avatar_deco.jpg,Y,Y
249,Nebular Knight Academy,b,12,121,111,249_nebula_horse_rider_academy,assets/sprites/249_nebula_horse_rider_academy.swf,assets/thumbs/249_nebula_horse_rider_academy.jpg,Y,Y
250,Nebular Dragon Rider Academy,b,12,121,111,250_nebula_dragon_nest,assets/sprites/250_nebula_dragon_nest.swf,assets/thumbs/250_nebula_dragon_nest.jpg,Y,Y
251,Nebular Assault Quad Academy,b,12,121,111,251_nebula_motorized_academy,assets/sprites/251_nebula_motorized_academy.swf,assets/thumbs/251_nebula_motorized_academy.jpg,Y,Y
252,Skyscraper,b,4,42,411,252_skyscraper,assets/sprites/252_skyscraper.swf,assets/thumbs/252_skyscraper.jpg,Y,Y
253,Parliament,b,5,51,511,253_parliament,assets/sprites/253_parliament.swf,assets/thumbs/253_parliament.jpg,Y,Y
254,Nebular Priest Academy,b,12,121,111,254_nebula_priest_academy,assets/sprites/254_nebula_priest_academy.swf,assets/thumbs/254_nebula_priest_academy.jpg,Y,Y
255,Nebular Bicopter Hangar,b,12,121,111,255_nebula_blue_bicopter_hangar,assets/sprites/255_nebula_blue_bicopter_hangar.swf,assets/thumbs/255_nebula_blue_bicopter_hangar.jpg,Y,Y
256,Research Lab,b,1,17,111,256_laboratory_tech,assets/sprites/256_laboratory_tech.swf,assets/thumbs/256_laboratory_tech.jpg,Y,Y
257,Blazing Beast Rider Academy,b,12,121,111,257_nebula_monster_rider_academy,assets/sprites/257_nebula_monster_rider_academy.swf,assets/thumbs/257_nebula_monster_rider_academy.jpg,Y,Y
258,Nebular Maze Warrior Academy,b,12,121,111,258_nebula_muze_warrior_academy,assets/sprites/258_nebula_muze_warrior_academy.swf,assets/thumbs/258_nebula_muze_warrior_academy.jpg,Y,Y
259,Nebular Sniper Academy,b,12,121,111,259_nebula_sniper_academy,assets/sprites/259_nebula_sniper_academy.swf,assets/thumbs/259_nebula_sniper_academy.jpg,Y,Y
260,Nebular Dragon Knight Academy,b,12,121,111,260_dragon_rider_2_academy,assets/sprites/260_dragon_rider_2_academy.swf,assets/thumbs/260_dragon_rider_2_academy.jpg,Y,Y
261,Auction House,b,1,17,111,261_marketplace,assets/sprites/261_marketplace.swf,assets/thumbs/261_marketplace.jpg,Y,Y
262,Poison Spider Hive,b,12,121,111,262_venom_spider_academy,assets/sprites/262_venom_spider_academy.swf,assets/thumbs/262_venom_spider_academy.jpg,Y,Y
263,Shredder Alien Nest,b,12,121,111,266_tusk_alien_academy,assets/sprites/266_tusk_alien_academy.swf,assets/thumbs/266_tusk_alien_academy.jpg,Y,Y
264,Acid Alien Nest,b,12,121,111,264_small_alien_academy,assets/sprites/264_small_alien_academy.swf,assets/thumbs/264_small_alien_academy.jpg,Y,Y
265,Huge Spider Hive,b,12,121,111,265_big_spider_academy,assets/sprites/265_big_spider_academy.swf,assets/thumbs/265_big_spider_academy.jpg,Y,Y
266,Horned Alien Nest,b,12,121,111,263_claw_alien_academy,assets/sprites/263_claw_alien_academy.swf,assets/thumbs/263_claw_alien_academy.jpg,Y,Y
267,Claw Spider Hive,b,12,121,111,267_melee_spider_academy,assets/sprites/267_melee_spider_academy.swf,assets/thumbs/267_melee_spider_academy.jpg,Y,Y
268,Swamp Monster Academy,b,12,121,111,268_nebula_monster_academy,assets/sprites/268_nebula_monster_academy.swf,assets/thumbs/268_nebula_monster_academy.jpg,Y,Y
269,S.W.A.T. Soldier Academy,b,12,121,111,269_swat_soldier_academy,assets/sprites/269_swat_soldier_academy.swf,assets/thumbs/269_swat_soldier_academy.jpg,Y,Y
270,Hercules Mech Academy,b,12,121,111,270_hercules_mech_academy,assets/sprites/270_hercules_mech_academy.swf,assets/thumbs/270_hercules_mech_academy.jpg,Y,Y
271,Space Elf Wall,b,12,121,221,271_spatial_wall,assets/sprites/271_spatial_wall.swf,assets/thumbs/271_spatial_wall.jpg,Y,Y
272,Space Elf Turret,b,12,121,211,272_spatial_turret,assets/sprites/272_spatial_turret.swf,assets/thumbs/272_spatial_turret.jpg,Y,Y
273,Space Elf House,b,12,121,111,273_spatial_house,assets/sprites/273_spatial_house.swf,assets/thumbs/273_spatial_house.jpg,Y,Y
274,Space Elf Field,b,12,121,129,274_spatial_farm,assets/sprites/274_spatial_farm.swf,assets/thumbs/274_spatial_farm.jpg,Y,Y
275,Elf Eagle Deco,b,12,121,411,275_spatial_deco,assets/sprites/275_spatial_deco.swf,assets/thumbs/275_spatial_deco.jpg,Y,Y
276,Space Sword Elf Academy,b,12,121,111,276_spatial_sward_academy,assets/sprites/276_spatial_sward_academy.swf,assets/thumbs/276_spatial_sward_academy.jpg,Y,Y
277,Space Archer Elf Academy,b,12,121,111,277_spatial_archer_academy,assets/sprites/277_spatial_archer_academy.swf,assets/thumbs/277_spatial_archer_academy.jpg,Y,Y
278,Space Knight Elf Academy,b,12,121,111,278_spatial_horseman_academy,assets/sprites/278_spatial_horseman_academy.swf,assets/thumbs/278_spatial_horseman_academy.jpg,Y,Y
279,Elf Airship Hangar,b,12,121,111,279_spatial_airship_hangar,assets/sprites/279_spatial_airship_hangar.swf,assets/thumbs/279_spatial_airship_hangar.jpg,Y,Y
280,Paladin Elf Academy,b,12,121,111,280_spatial_paladin_academy,assets/sprites/280_spatial_paladin_academy.swf,assets/thumbs/280_spatial_paladin_academy.jpg,Y,Y
281,Priest Elf Academy,b,12,121,111,281_spatial_priest_academy,assets/sprites/281_spatial_priest_academy.swf,assets/thumbs/281_spatial_priest_academy.jpg,Y,Y
282,Elven Cruiser Hangar,b,12,121,111,282_spatial_space_ship_hangar,assets/sprites/282_spatial_space_ship_hangar.swf,assets/thumbs/282_spatial_space_ship_hangar.jpg,Y,Y
283,Reptile Gun Academy,b,12,121,111,283_reptile_gun_hangar,assets/sprites/283_reptile_gun_hangar.swf,assets/thumbs/283_reptile_gun_hangar.jpg,Y,Y
284,MegaBot Academy,b,12,121,111,284_mega_bot_academy,assets/sprites/284_mega_bot_academy.swf,assets/thumbs/284_mega_bot_academy.jpg,Y,Y
285,Space Healer Elf Academy,b,12,121,111,285_spatial_healer_academy,assets/sprites/285_spatial_healer_academy.swf,assets/thumbs/285_spatial_healer_academy.jpg,Y,Y
286,Space Elf Scouter Hangar,b,12,121,111,286_spatial_exploration_module_hangar,assets/sprites/286_spatial_exploration_module_hangar.swf,assets/thumbs/286_spatial_exploration_module_hangar.jpg,Y,Y
287,GunBot Academy,b,12,121,111,287_gun_bot_academy,assets/sprites/287_gun_bot_academy.swf,assets/thumbs/287_gun_bot_academy.jpg,Y,Y
288,Silver Gunner Elf Academy,b,12,121,111,288_silver_elf_gunner_academy,assets/sprites/288_silver_elf_gunner_academy.swf,assets/thumbs/288_silver_elf_gunner_academy.jpg,Y,Y
289,Dino Rider Elf Academy,b,12,121,111,289_elf_dino_rider_academy,assets/sprites/289_elf_dino_rider_academy.swf,assets/thumbs/289_elf_dino_rider_academy.jpg,Y,Y
290,Destruction Wizard Elf Academy,b,12,121,111,290_destruction_wizard_academy,assets/sprites/290_destruction_wizard_academy.swf,assets/thumbs/290_destruction_wizard_academy.jpg,Y,Y
291,Elf Siege Striker Academy,b,12,121,111,291_plasma_striker_academy,assets/sprites/291_plasma_striker_academy.swf,assets/thumbs/291_plasma_striker_academy.jpg,Y,Y
292,Winged Paladin Academy,b,12,121,111,292_winged_paladin_academy,assets/sprites/292_winged_paladin_academy.swf,assets/thumbs/292_winged_paladin_academy.jpg,Y,Y
293,Andromeda Wall,b,12,121,221,293_andromedaWall,assets/sprites/293_andromedaWall.swf,assets/thumbs/293_andromedaWall.jpg,Y,Y
294,Andromeda Turret,b,12,121,211,294_andromedaTurret,assets/sprites/294_andromedaTurret.swf,assets/thumbs/294_andromedaTurret.jpg,Y,Y
295,Andromeda House,b,12,121,111,295_andromedaHouse,assets/sprites/295_andromedaHouse.swf,assets/thumbs/295_andromedaHouse.jpg,Y,Y
296,Andromeda Farm,b,12,121,129,296_andromedaFarm,assets/sprites/296_andromedaFarm.swf,assets/thumbs/296_andromedaFarm.jpg,Y,Y
297,Andromeda Statue,b,12,121,411,297_andromedaDeco,assets/sprites/297_andromedaDeco.swf,assets/thumbs/297_andromedaDeco.jpg,Y,Y
298,Andromeda Private Academy,b,12,121,111,298_andromedaPrivateAcademy,assets/sprites/298_andromedaPrivateAcademy.swf,assets/thumbs/298_andromedaPrivateAcademy.jpg,Y,Y
299,Andromeda Droid Factory,b,12,121,111,299_andromedaDroidFactory,assets/sprites/299_andromedaDroidFactory.swf,assets/thumbs/299_andromedaDroidFactory.jpg,Y,Y
300,Andromeda Spaceship Hangar,b,12,121,111,300_andromedaSpaceshipHangar,assets/sprites/300_andromedaSpaceshipHangar.swf,assets/thumbs/300_andromedaSpaceshipHangar.jpg,Y,Y
301,Punisher Bot Factory,b,12,121,111,301_punisherBot_Factory,assets/sprites/301_punisherBot_Factory.swf,assets/thumbs/301_punisherBot_Factory.jpg,Y,Y
901,Oil,b,1,12,123,10001_resource_oil_1,assets/sprites/10001_resource_oil_1.swf,assets/thumbs/10001_resource_oil_1.jpg,Y,Y
902,Oil,b,1,12,123,10002_resource_oil_2,assets/sprites/10002_resource_oil_2.swf,assets/thumbs/10002_resource_oil_2.jpg,Y,Y
903,Oil,b,1,12,123,10003_resource_oil_3,assets/sprites/10003_resource_oil_3.swf,assets/thumbs/10003_resource_oil_3.jpg,Y,Y
904,Oil,b,1,12,123,10004_resource_oil_4,assets/sprites/10004_resource_oil_4.swf,assets/thumbs/10004_resource_oil_4.jpg,Y,Y
905,Tree,b,1,12,125,10005_arbol1x1,assets/sprites/10005_arbol1x1.swf,assets/thumbs/10005_arbol1x1.jpg,Y,Y
907,Small Harbour,b,1,14,0,10007_port_1,assets/sprites/10007_port_1.swf,assets/thumbs/10007_port_1.jpg,Y,Y
908,Harbour,b,1,14,0,10008_harbour,assets/sprites/10008_harbour.swf,assets/thumbs/10008_harbour.jpg,Y,Y
909,Space Station,b,1,14,0,0199_space_station,assets/sprites/0199_space_station.swf,assets/thumbs/0199_space_station.jpg,Y,Y
910,Steel,b,1,12,126,10010_resource_steel_1,assets/sprites/10010_resource_steel_1.swf,assets/thumbs/10010_resource_steel_1.jpg,Y,Y
911,Steel,b,1,12,126,10011_resource_steel_2,assets/sprites/10011_resource_steel_2.swf,assets/thumbs/10011_resource_steel_2.jpg,Y,Y
912,Steel,b,1,12,126,10012_resource_steel_3,assets/sprites/10012_resource_steel_3.swf,assets/thumbs/10012_resource_steel_3.jpg,Y,Y
913,Steel,b,1,12,126,10013_resource_steel_4,assets/sprites/10013_resource_steel_4.swf,assets/thumbs/10013_resource_steel_4.jpg,Y,Y
914,Gold,b,1,12,127,10014_resource_gold_1,assets/sprites/10014_resource_gold_1.swf,assets/thumbs/10014_resource_gold_1.jpg,Y,Y
915,Gold,b,1,12,127,10015_resource_gold_2,assets/sprites/10015_resource_gold_2.swf,assets/thumbs/10015_resource_gold_2.jpg,Y,Y
916,Gold,b,1,12,127,10016_resource_gold_3,assets/sprites/10016_resource_gold_3.swf,assets/thumbs/10016_resource_gold_3.jpg,Y,Y
917,Gold,b,1,12,127,10017_resource_gold_4,assets/sprites/10017_resource_gold_4.swf,assets/thumbs/10017_resource_gold_4.jpg,Y,Y
918,Regenerating oil..,b,1,12,128,10018_resource_oil_regen,assets/sprites/10018_resource_oil_regen.swf,assets/thumbs/10018_resource_oil_regen.jpg,Y,Y
919,Regenerating steel..,b,1,12,128,10019_resource_steel_regen,assets/sprites/10019_resource_steel_regen.swf,assets/thumbs/10019_resource_steel_regen.jpg,Y,Y
920,Regenerating gold..,b,1,12,128,10020_resource_gold_regen,assets/sprites/10020_resource_gold_regen.swf,assets/thumbs/10020_resource_gold_regen.jpg,Y,Y
921,Treasure Chest,b,8,81,811,treasure,,,N,N
922,Dummy 9-91,b,9,91,911,vacaPerdida,,,N,N
923,Gorilla,u,1,12,128,10023_gorilla,assets/sprites/10023_gorilla.swf,assets/thumbs/10023_gorilla.jpg,Y,Y
924,Dummy 12-121,b,12,121,111,casachina,,,N,N
925,Expandable Land,l,6,6,6,terreno,assets/sprites/terreno.swf,,Y,N
926,Key,b,8,81,812,10026_key,assets/sprites/10026_key.swf,assets/thumbs/10026_key.jpg,Y,Y
927,Prison,b,8,81,812,10027_prision,,,N,N
928,Broken Bridge,b,12,121,0,10028_broken_bridge,assets/sprites/10028_broken_bridge.swf,,Y,N
929,Bridge,b,12,121,1011,10029_bridge,assets/sprites/10029_bridge.swf,,Y,N
930,Trees,b,1,12,125,10030_arbol2x2,assets/sprites/10030_arbol2x2.swf,assets/thumbs/10030_arbol2x2.jpg,Y,Y
931,Small forest,b,1,12,125,10031_arbol3x3,assets/sprites/10031_arbol3x3.swf,assets/thumbs/10031_arbol3x3.jpg,Y,Y
932,Silo,b,1,14,0,10032_silo_1,assets/sprites/10032_silo_1.swf,assets/thumbs/10032_silo_1.jpg,Y,Y
933,Wild Elephant,u,1,12,128,10033_wild_elephant,assets/sprites/10033_wild_elephant.swf,assets/thumbs/10033_wild_elephant.jpg,Y,Y
941,Silo II,b,1,14,0,10041_silo_2,assets/sprites/10041_silo_2.swf,assets/thumbs/10041_silo_2.jpg,Y,Y
942,Silo III,b,1,14,0,10042_silo_3,assets/sprites/10042_silo_3.swf,assets/thumbs/10042_silo_3.jpg,Y,Y
943,Destroyed building 1,b,12,121,1011,10043_destroyed_building_1,assets/sprites/10043_destroyed_building_1.swf,assets/thumbs/10043_destroyed_building_1.jpg,Y,Y
944,Destroyed building 2,b,12,121,1011,10044_destroyed_building_2,assets/sprites/10044_destroyed_building_2.swf,assets/thumbs/10044_destroyed_building_2.jpg,Y,Y
945,Destroyed building 3,b,12,121,1011,10045_destroyed_building_3,assets/sprites/10045_destroyed_building_3.swf,assets/thumbs/10045_destroyed_building_3.jpg,Y,Y
946,Destroyed building 4,b,12,121,1011,10046_destroyed_building_4,assets/sprites/10046_destroyed_building_4.swf,assets/thumbs/10046_destroyed_building_4.jpg,Y,Y
947,Destroyed building 5,b,12,121,1011,10047_destroyed_building_5_b,assets/sprites/10047_destroyed_building_5_b.swf,assets/thumbs/10047_destroyed_building_5_b.jpg,Y,Y
948,Oil barrel,b,12,121,0,10048_oil_barrel,assets/sprites/10048_oil_barrel.swf,assets/thumbs/10048_oil_barrel.jpg,Y,Y
949,Atrezzo Harbour,b,1,14,0,10049_harbour,assets/sprites/10049_harbour.swf,,Y,N
950,Nice fountain,b,4,45,411,10050_nice_fountain,assets/sprites/10050_nice_fountain.swf,,Y,N
951,Orange Tree,b,4,45,411,10051_orange_tree,assets/sprites/10051_orange_tree.swf,,Y,N
952,Chickens,b,4,45,411,10052_chickens,assets/sprites/10052_chickens.swf,,Y,N
953,Lost Rocket,b,4,45,411,10053_lost_rocket,assets/sprites/10053_lost_rocket.swf,,Y,N
954,Astronaut Pack,b,4,45,411,10054_astronaut_pack,assets/sprites/10054_astronaut_pack.swf,,Y,N
955,Destroyed Tank,b,4,45,411,10055_destroyed_tank,assets/sprites/10055_destroyed_tank.swf,,Y,N
956,Lost Puppies,b,4,45,411,10056_lost_puppies,assets/sprites/10056_lost_puppies.swf,,Y,N
957,Lost Oil Barrels,b,4,45,411,1005_oil_barrels,assets/sprites/1005_oil_barrels.swf,,Y,N
958,Green T-Rex Cage,b,1,14,0,10058_trex_cage,assets/sprites/10058_trex_cage.swf,assets/thumbs/10058_trex_cage.jpg,Y,Y
959,Red T-Rex Cage,b,1,14,0,10059_trex_cage,assets/sprites/10059_trex_cage.swf,assets/thumbs/10059_trex_cage.jpg,Y,Y
960,Chest,b,12,121,0,10060_chest,assets/sprites/10060_chest.swf,,Y,N
961,Chained Red Baron,b,4,45,411,10061_chained_red_baron,assets/sprites/10061_chained_red_baron.swf,assets/thumbs/10061_chained_red_baron.jpg,Y,Y
962,Chained Metallic Dragon,b,4,45,411,10062_chained_metallic_dragon,assets/sprites/10062_chained_metallic_dragon.swf,assets/thumbs/10062_chained_metallic_dragon.jpg,Y,Y
963,Chained Celestial Megamech,b,4,45,411,10063_chained_celestial_megamech,assets/sprites/10063_chained_celestial_megamech.swf,assets/thumbs/10063_chained_celestial_megamech.jpg,Y,Y
964,Chained Metallic Dragon II,b,4,45,411,10064_chained_metallic_dragon2,assets/sprites/10064_chained_metallic_dragon2.swf,assets/thumbs/10064_chained_metallic_dragon2.jpg,Y,Y
965,Chained Armored Core Alpha,b,4,45,411,965_chained_armored_core_alpha,assets/sprites/965_chained_armored_core_alpha.swf,assets/thumbs/965_chained_armored_core_alpha.jpg,Y,Y
966,Chained Ultra-Mech,b,4,45,411,966_chained_transformer_gigante,assets/sprites/966_chained_transformer_gigante.swf,assets/thumbs/966_chained_transformer_gigante.jpg,Y,Y
967,Chained Nemesis Core,b,4,45,411,967_chained_ultra_robot,assets/sprites/967_chained_ultra_robot.swf,assets/thumbs/967_chained_ultra_robot.jpg,Y,Y
968,Chained F117,b,4,45,411,968_chained_f117,assets/sprites/968_chained_f117.swf,assets/thumbs/968_chained_f117.jpg,Y,Y
969,Chained Mega Tank,b,4,45,411,969_chained_mega_tank,assets/sprites/969_chained_mega_tank.swf,assets/thumbs/969_chained_mega_tank.jpg,Y,Y
970,Chained Blue Steel Bahamut,b,4,45,411,970_chained_bahamut_metalico,assets/sprites/970_chained_bahamut_metalico.swf,assets/thumbs/970_chained_bahamut_metalico.jpg,Y,Y
971,Chained Alien Instigator,b,4,45,411,971_chained_alien_instigator,assets/sprites/971_chained_alien_instigator.swf,assets/thumbs/971_chained_alien_instigator.jpg,Y,Y
972,Chained Hyper Blazer ,b,4,45,411,972_chained_mega_fire_bot,assets/sprites/972_chained_mega_fire_bot.swf,assets/thumbs/972_chained_mega_fire_bot.jpg,Y,Y
973,Chained Ether Messiah,b,4,45,411,973_chained_ether_messiah,assets/sprites/973_chained_ether_messiah.swf,assets/thumbs/973_chained_ether_messiah.jpg,Y,Y
974,Chained Combo Dragons,b,4,45,411,974_chained_combo_dragons,assets/sprites/974_chained_combo_dragons.swf,assets/thumbs/974_chained_combo_dragons.jpg,Y,Y
975,Chained Golem Boss,b,4,45,411,975_chained_golem_boss,assets/sprites/975_chained_golem_boss.swf,assets/thumbs/975_chained_golem_boss.jpg,Y,Y
976,Chained Crusader Bot,b,4,45,411,976_chained_crusader_bot,assets/sprites/976_chained_crusader_bot.swf,assets/thumbs/976_chained_crusader_bot.jpg,Y,Y
977,Chained Samurai Bot,b,4,45,411,977_chained_samurai_bot,assets/sprites/977_chained_samurai_bot.swf,assets/thumbs/977_chained_samurai_bot.jpg,Y,Y
978,Chained Magic Chest,b,4,45,411,978_chained_corfe_1,assets/sprites/978_chained_corfe_1.swf,assets/thumbs/978_chained_corfe_1.jpg,Y,Y
979,Chained Mega Chest,b,4,45,411,979_chained_corfe_2,assets/sprites/979_chained_corfe_2.swf,assets/thumbs/979_chained_corfe_2.jpg,Y,Y
980,Chained Camu Dragon,b,4,45,411,980_chained_camu_dragon,assets/sprites/980_chained_camu_dragon.swf,assets/thumbs/980_chained_camu_dragon.jpg,Y,Y
981,Chained Skater,b,4,45,411,981_chained_skater,assets/sprites/981_chained_skater.swf,assets/thumbs/981_chained_skater.jpg,Y,Y
982,Chained Red Spinner,b,4,45,411,982_chained_red_spinner,,,N,N
983,Chained Golden Slayer,b,4,45,411,983_chained_transformer_sword,assets/sprites/983_chained_transformer_sword.swf,assets/thumbs/983_chained_transformer_sword.jpg,Y,Y
984,Chained Gun Bot,b,4,45,411,984_chained_gun_bot_2,assets/sprites/984_chained_gun_bot_2.swf,assets/thumbs/984_chained_gun_bot_2.jpg,Y,Y
985,Chained Robo Hunter,b,4,45,411,985_chained_robo_hunter,assets/sprites/985_chained_robo_hunter.swf,assets/thumbs/985_chained_robo_hunter.jpg,Y,Y
986,Chained 50% Off,b,4,45,411,986_chained_50_off,assets/sprites/986_chained_50_off.swf,assets/thumbs/986_chained_50_off.jpg,Y,Y
987,Chained Ufo,b,4,45,411,987_chained_ufo,assets/sprites/987_chained_ufo.swf,assets/thumbs/987_chained_ufo.jpg,Y,Y
988,Chained MegaAxe&MegaLancer,b,4,45,411,988_chained_axe_lancer,assets/sprites/988_chained_axe_lancer.swf,assets/thumbs/988_chained_axe_lancer.jpg,Y,Y
989,Chained Megafire T-Rex,b,4,45,411,989_chained_trex,assets/sprites/989_chained_trex.swf,assets/thumbs/989_chained_trex.jpg,Y,Y
990,Chained Double Cash Offer,b,4,45,411,990_chained_double,assets/sprites/990_chained_double.swf,assets/thumbs/990_chained_double.jpg,Y,Y
991,Chained Fire Karateka,b,4,45,411,991_chained_karateka,assets/sprites/991_chained_karateka.swf,assets/thumbs/991_chained_karateka.jpg,Y,Y
992,Chained Gold Golem,b,4,45,411,992_chained_gold_golem,assets/sprites/992_chained_gold_golem.swf,assets/thumbs/992_chained_gold_golem.jpg,Y,Y
993,Chained Double Cash Offer + F117,b,4,45,411,993_chained_double_f117,assets/sprites/993_chained_double_f117.swf,assets/thumbs/993_chained_double_f117.jpg,Y,Y
994,Chained Black Dragon,b,4,45,411,994_chained_black_dragon,assets/sprites/994_chained_black_dragon.swf,assets/thumbs/994_chained_black_dragon.jpg,Y,Y
995,Chained Electric Dragon,b,4,45,411,995_chained_electric_dragon,assets/sprites/995_chained_electric_dragon.swf,assets/thumbs/995_chained_electric_dragon.jpg,Y,Y
996,Chained Dragonborn Mech,b,4,45,411,996_chained_dragon_mech,assets/sprites/996_chained_dragon_mech.swf,assets/thumbs/996_chained_dragon_mech.jpg,Y,Y
997,Chained Silver Hercules,b,4,45,411,997_chained_herkules_matrix,assets/sprites/997_chained_herkules_matrix.swf,assets/thumbs/997_chained_herkules_matrix.jpg,Y,Y
998,Chained Rune Golem,b,4,45,411,998_chained_rune_golem,assets/sprites/998_chained_rune_golem.swf,assets/thumbs/998_chained_rune_golem.jpg,Y,Y
999,Chained Supreme Chest,b,4,45,411,999_chained_supreme_chest,assets/sprites/999_chained_supreme_chest.swf,assets/thumbs/999_chained_supreme_chest.jpg,Y,Y
1001,Worker I,u,7,7,71,"1001_worker_m,1001_worker_w",assets/sprites/1001_worker_m.swf;assets/sprites/1001_worker_w.swf,assets/thumbs/1001_worker_m.jpg;assets/thumbs/1001_worker_w.jpg,Y,Y
1002,Red Tank,u,7,7,80,1002_Red_Tank_m,assets/sprites/1002_Red_Tank_m.swf,assets/thumbs/1002_Red_Tank_m.jpg,Y,Y
1003,Tank II,u,7,7,80,1003_cannon_2_m,assets/sprites/1003_cannon_2_m.swf,assets/thumbs/1003_cannon_2_m.jpg,Y,Y
1004,Tank III,u,7,7,80,1004_cannon_3_m,assets/sprites/1004_cannon_3_m.swf,assets/thumbs/1004_cannon_3_m.jpg,Y,Y
1005,Special Spy,u,7,7,80,1005_special_spy_m,assets/sprites/1005_special_spy_m.swf,assets/thumbs/1005_special_spy_m.jpg,Y,Y
1006,Killer Bazooka Jeep,u,7,7,80,1006_red_bazooka_jeep_m,assets/sprites/1006_red_bazooka_jeep_m.swf,assets/thumbs/1006_red_bazooka_jeep_m.jpg,Y,Y
1007,Soldier,u,7,7,80,"1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_m,1007_soldier_1_w",assets/sprites/1007_soldier_1_m.swf;assets/sprites/1007_soldier_1_m.swf;assets/sprites/1007_soldier_1_m.swf;assets/sprites/1007_soldier_1_m.swf;assets/sprites/1007_soldier_1_w.swf,assets/thumbs/1007_soldier_1_m.jpg;assets/thumbs/1007_soldier_1_m.jpg;assets/thumbs/1007_soldier_1_m.jpg;assets/thumbs/1007_soldier_1_m.jpg;assets/thumbs/1007_soldier_1_w.jpg,Y,Y
1008,Bazooka,u,7,7,80,"1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_m,1008_bazooka_1_w",assets/sprites/1008_bazooka_1_m.swf;assets/sprites/1008_bazooka_1_m.swf;assets/sprites/1008_bazooka_1_m.swf;assets/sprites/1008_bazooka_1_m.swf;assets/sprites/1008_bazooka_1_w.swf,assets/thumbs/1008_bazooka_1_m.jpg;assets/thumbs/1008_bazooka_1_m.jpg;assets/thumbs/1008_bazooka_1_m.jpg;assets/thumbs/1008_bazooka_1_m.jpg;assets/thumbs/1008_bazooka_1_w.jpg,Y,Y
1009,General Scarlett,u,7,7,80,1009_good_girl_m,assets/sprites/1009_good_girl_m.swf,assets/thumbs/1009_good_girl_m.jpg,Y,Y
1010,APC,u,7,7,80,1010_apc_m,assets/sprites/1010_apc_m.swf,assets/thumbs/1010_apc_m.jpg,Y,Y
1011,Ms. Evilia,u,7,7,80,1011_bad_girl_m,,,N,N
1012,Evil Hannibal,u,7,7,80,1012_bad_boy,assets/sprites/1012_bad_boy.swf,assets/thumbs/1012_bad_boy.jpg,Y,Y
1013,Truck,u,7,7,80,1013_truck_1_m,assets/sprites/1013_truck_1_m.swf,assets/thumbs/1013_truck_1_m.jpg,Y,Y
1014,Machine Gun Jeep,u,7,7,80,"1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_m,1014_machinegunjeep_1_w",assets/sprites/1014_machinegunjeep_1_m.swf;assets/sprites/1014_machinegunjeep_1_m.swf;assets/sprites/1014_machinegunjeep_1_m.swf;assets/sprites/1014_machinegunjeep_1_m.swf;assets/sprites/1014_machinegunjeep_1_w.swf,assets/thumbs/1014_machinegunjeep_1_m.jpg;assets/thumbs/1014_machinegunjeep_1_m.jpg;assets/thumbs/1014_machinegunjeep_1_m.jpg;assets/thumbs/1014_machinegunjeep_1_m.jpg;assets/thumbs/1014_machinegunjeep_1_w.jpg,Y,Y
1015,Aircraft,u,7,7,83,1015_aircraft_1_m,assets/sprites/1015_aircraft_1_m.swf,assets/thumbs/1015_aircraft_1_m.jpg,Y,Y
1016,Tank,u,7,7,80,1016_cannon_1_m,assets/sprites/1016_cannon_1_m.swf,assets/thumbs/1016_cannon_1_m.jpg,Y,Y
1017,General Mike,u,7,7,80,1017_good_boy,assets/sprites/1017_good_boy.swf,assets/thumbs/1017_good_boy.jpg,Y,Y
1018,Zodiac,u,7,7,80,1018_zodiac_m,assets/sprites/1018_zodiac_m.swf,assets/thumbs/1018_zodiac_m.jpg,Y,Y
1019,Ship,u,7,7,80,1019_ship_m2,assets/sprites/1019_ship_m2.swf,assets/thumbs/1019_ship_m2.jpg,Y,Y
1020,Soldier II,u,7,7,80,1020_soldier_2_m,assets/sprites/1020_soldier_2_m.swf,assets/thumbs/1020_soldier_2_m.jpg,Y,Y
1021,Soldier III,u,7,7,80,1021_soldier_3_m,assets/sprites/1021_soldier_3_m.swf,assets/thumbs/1021_soldier_3_m.jpg,Y,Y
1022,Bazooka II,u,7,7,80,1022_bazooka_2_m,assets/sprites/1022_bazooka_2_m.swf,assets/thumbs/1022_bazooka_2_m.jpg,Y,Y
1023,Bazooka III,u,7,7,80,1023_bazooka_3_m,assets/sprites/1023_bazooka_3_m.swf,assets/thumbs/1023_bazooka_3_m.jpg,Y,Y
1024,Sergeant Megan,u,7,7,80,1024_good_guillerma,assets/sprites/1024_good_guillerma.swf,assets/thumbs/1024_good_guillerma.jpg,Y,Y
1025,Aircraft II,u,7,7,83,1025_aircraft_2_m,assets/sprites/1025_aircraft_2_m.swf,assets/thumbs/1025_aircraft_2_m.jpg,Y,Y
1026,Aircraft III,u,7,7,83,1026_aircraft_3_m,assets/sprites/1026_aircraft_3_m.swf,assets/thumbs/1026_aircraft_3_m.jpg,Y,Y
1027,Helicopter,u,7,7,83,1027_helicopter_1_m,assets/sprites/1027_helicopter_1_m.swf,assets/thumbs/1027_helicopter_1_m.jpg,Y,Y
1028,Helicopter II,u,7,7,83,1028_helicopter_2_m,assets/sprites/1028_helicopter_2_m.swf,assets/thumbs/1028_helicopter_2_m.jpg,Y,Y
1029,Helicopter III,u,7,7,83,1029_helicopter_3_m,assets/sprites/1029_helicopter_3_m.swf,assets/thumbs/1029_helicopter_3_m.jpg,Y,Y
1030,Machine Gun Jeep II,u,7,7,80,1030_machinegunjeep_2_m,assets/sprites/1030_machinegunjeep_2_m.swf,assets/thumbs/1030_machinegunjeep_2_m.jpg,Y,Y
1031,Machine Gun Jeep III,u,7,7,80,1031_machinegunjeep_3_m,assets/sprites/1031_machinegunjeep_3_m.swf,assets/thumbs/1031_machinegunjeep_3_m.jpg,Y,Y
1032,Truck 3,u,7,7,80,1032_truck_3_m,assets/sprites/1032_truck_3_m.swf,assets/thumbs/1032_truck_3_m.jpg,Y,Y
1033,Mr. Cigar,u,7,7,80,1033_mr_cigar,assets/sprites/1033_mr_cigar.swf,assets/thumbs/1033_mr_cigar.jpg,Y,Y
1034,UN Allied,u,7,7,80,"1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_m,1034_un_allied_1_w",assets/sprites/1034_un_allied_1_m.swf;assets/sprites/1034_un_allied_1_m.swf;assets/sprites/1034_un_allied_1_m.swf;assets/sprites/1034_un_allied_1_m.swf;assets/sprites/1034_un_allied_1_w.swf,assets/thumbs/1034_un_allied_1_m.jpg;assets/thumbs/1034_un_allied_1_m.jpg;assets/thumbs/1034_un_allied_1_m.jpg;assets/thumbs/1034_un_allied_1_m.jpg;assets/thumbs/1034_un_allied_1_w.jpg,Y,Y
1035,Truck II,u,7,7,80,1035_truck_2_m,assets/sprites/1035_truck_2_m.swf,assets/thumbs/1035_truck_2_m.jpg,Y,Y
1036,Double Bazooka,u,7,7,80,1036_double_bazooka_m,assets/sprites/1036_double_bazooka_m.swf,assets/thumbs/1036_double_bazooka_m.jpg,Y,Y
1037,MegaTank,u,7,7,80,1037_megatank,assets/sprites/1037_megatank.swf,assets/thumbs/1037_megatank.jpg,Y,Y
1038,Red chopper,u,7,7,83,1038_red_helicopter_m,assets/sprites/1038_red_helicopter_m.swf,assets/thumbs/1038_red_helicopter_m.jpg,Y,Y
1039,Worker II,u,7,7,71,1001_worker_m,assets/sprites/1001_worker_m.swf,assets/thumbs/1001_worker_m.jpg,Y,Y
1040,Worker III,u,7,7,71,1001_worker_m,assets/sprites/1001_worker_m.swf,assets/thumbs/1001_worker_m.jpg,Y,Y
1041,Worker IV,u,7,7,71,1001_worker_m,assets/sprites/1001_worker_m.swf,assets/thumbs/1001_worker_m.jpg,Y,Y
1042,Sergeant Jack,u,7,7,80,1042_good_guile,assets/sprites/1042_good_guile.swf,assets/thumbs/1042_good_guile.jpg,Y,Y
1043,Air Strike,u,7,7,83,1043_air_strike_m,assets/sprites/1043_air_strike_m.swf,assets/thumbs/1043_air_strike_m.jpg,Y,Y
1044,Double Bazooka Jeep,u,7,7,80,1044_double_bazooka_jeep_m,assets/sprites/1044_double_bazooka_jeep_m.swf,assets/thumbs/1044_double_bazooka_jeep_m.jpg,Y,Y
1045,Double Gun Soldier,u,7,7,80,1045_double_gun_soldier_m,assets/sprites/1045_double_gun_soldier_m.swf,assets/thumbs/1045_double_gun_soldier_m.jpg,Y,Y
1046,Flamethrower,u,7,7,80,1046_flamethrower_m,assets/sprites/1046_flamethrower_m.swf,assets/thumbs/1046_flamethrower_m.jpg,Y,Y
1047,Dominion Tank,u,7,7,80,1047_black_tank_2_m,assets/sprites/1047_black_tank_2_m.swf,assets/thumbs/1047_black_tank_2_m.jpg,Y,Y
1048,Stealth Fighter,u,7,7,83,1048_black_aircraft_2_m,assets/sprites/1048_black_aircraft_2_m.swf,assets/thumbs/1048_black_aircraft_2_m.jpg,Y,Y
1049,TankBoss,u,7,7,80,1053_golem_boss_m,assets/sprites/1053_golem_boss_m.swf,assets/thumbs/1053_golem_boss_m.jpg,Y,Y
1050,Medic,u,7,7,80,1050_medic_m,assets/sprites/1050_medic_m.swf,assets/thumbs/1050_medic_m.jpg,Y,Y
1051,Engineer,u,7,7,80,1051_mechanic_m,assets/sprites/1051_mechanic_m.swf,assets/thumbs/1051_mechanic_m.jpg,Y,Y
1052,Special Ops.,u,7,7,80,1052_special_ops_2_m,assets/sprites/1052_special_ops_2_m.swf,assets/thumbs/1052_special_ops_2_m.jpg,Y,Y
1053,GolemBoss,u,7,7,80,1053_golem_boss_m,assets/sprites/1053_golem_boss_m.swf,assets/thumbs/1053_golem_boss_m.jpg,Y,Y
1054,Scarface girl,u,7,7,80,1054_scarface_girl,assets/sprites/1054_scarface_girl.swf,assets/thumbs/1054_scarface_girl.jpg,Y,Y
1055,Mr. Treat,u,7,7,80,1055_mr_t_m,assets/sprites/1055_mr_t_m.swf,assets/thumbs/1055_mr_t_m.jpg,Y,Y
1056,Elephant rider,u,7,7,80,1056_elephant_rider_m,assets/sprites/1056_elephant_rider_m.swf,assets/thumbs/1056_elephant_rider_m.jpg,Y,Y
1057,T-Rex Green,u,7,7,80,1057_t-rex_m,assets/sprites/1057_t-rex_m.swf,assets/thumbs/1057_t-rex_m.jpg,Y,Y
1058,Soldier IV,u,7,7,80,1058_soldier_4_m,assets/sprites/1058_soldier_4_m.swf,assets/thumbs/1058_soldier_4_m.jpg,Y,Y
1059,Soldier V,u,7,7,80,1059_soldier_5_m,assets/sprites/1059_soldier_5_m.swf,assets/thumbs/1059_soldier_5_m.jpg,Y,Y
1060,Mortar Thrower,u,7,7,80,1060_mortar_m,assets/sprites/1060_mortar_m.swf,assets/thumbs/1060_mortar_m.jpg,Y,Y
1061,GunBot,u,7,7,80,1061_baby_robot_m,assets/sprites/1061_baby_robot_m.swf,assets/thumbs/1061_baby_robot_m.jpg,Y,Y
1062,MegaBot,u,7,7,80,1062_bumblebee_m,assets/sprites/1062_bumblebee_m.swf,assets/thumbs/1062_bumblebee_m.jpg,Y,Y
1063,Bazooka IV,u,7,7,80,1063_bazooka_4_m,assets/sprites/1063_bazooka_4_m.swf,assets/thumbs/1063_bazooka_4_m.jpg,Y,Y
1064,Bazooka V,u,7,7,80,1064_bazooka_5_m,assets/sprites/1064_bazooka_5_m.swf,assets/thumbs/1064_bazooka_5_m.jpg,Y,Y
1065,Antiaircraft battery,u,7,7,80,1065_antiaircraft_battery_m,assets/sprites/1065_antiaircraft_battery_m.swf,assets/thumbs/1065_antiaircraft_battery_m.jpg,Y,Y
1066,Helicopter IV,u,7,7,83,1066_helicopter_4_m,assets/sprites/1066_helicopter_4_m.swf,assets/thumbs/1066_helicopter_4_m.jpg,Y,Y
1067,Helicopter V,u,7,7,83,1067_helicopter_5_m,assets/sprites/1067_helicopter_5_m.swf,assets/thumbs/1067_helicopter_5_m.jpg,Y,Y
1068,B52,u,7,7,83,1068_b52_m,assets/sprites/1068_b52_m.swf,assets/thumbs/1068_b52_m.jpg,Y,Y
1069,Demolition Tank,u,7,7,80,1069_bigheaded_tank_m,assets/sprites/1069_bigheaded_tank_m.swf,assets/thumbs/1069_bigheaded_tank_m.jpg,Y,Y
1070,Tank IV,u,7,7,80,1070_cannon_4_m,assets/sprites/1070_cannon_4_m.swf,assets/thumbs/1070_cannon_4_m.jpg,Y,Y
1071,Tank V,u,7,7,80,1071_cannon_5_m,assets/sprites/1071_cannon_5_m.swf,assets/thumbs/1071_cannon_5_m.jpg,Y,Y
1072,Ranbo,u,7,7,80,1072_rambo_m,assets/sprites/1072_rambo_m.swf,assets/thumbs/1072_rambo_m.jpg,Y,Y
1073,Erradicator,u,7,7,80,1073_erradicator_m,assets/sprites/1073_erradicator_m.swf,assets/thumbs/1073_erradicator_m.jpg,Y,Y
1074,Punisher Bot,u,7,7,80,1074_punisher_m,assets/sprites/1074_punisher_m.swf,assets/thumbs/1074_punisher_m.jpg,Y,Y
1075,Supreme Bot,u,7,7,80,1075_supreme_m,assets/sprites/1075_supreme_m.swf,assets/thumbs/1075_supreme_m.jpg,Y,Y
1076,Crusader Soldier,u,7,7,80,1076_robo_soldier_m,assets/sprites/1076_robo_soldier_m.swf,assets/thumbs/1076_robo_soldier_m.jpg,Y,Y
1077,Swordsman Soldier,u,7,7,80,1077_robo_swordsman_m,assets/sprites/1077_robo_swordsman_m.swf,assets/thumbs/1077_robo_swordsman_m.jpg,Y,Y
1078,Bazooka Soldier,u,7,7,80,1078_robo_bazooka_m,assets/sprites/1078_robo_bazooka_m.swf,assets/thumbs/1078_robo_bazooka_m.jpg,Y,Y
1079,Jet Soldier,u,7,7,80,1079_robo_jumper_m,assets/sprites/1079_robo_jumper_m.swf,assets/thumbs/1079_robo_jumper_m.jpg,Y,Y
1080,Motorized Soldier,u,7,7,80,1080_robo_biker_m,assets/sprites/1080_robo_biker_m.swf,assets/thumbs/1080_robo_biker_m.jpg,Y,Y
1081,Xtreme Retaliator,u,7,7,80,1081_xtreme_retaliator_m,assets/sprites/1081_xtreme_retaliator_m.swf,assets/thumbs/1081_xtreme_retaliator_m.jpg,Y,Y
1082,Megalancer,u,7,7,80,1082_robo_lancer_m,assets/sprites/1082_robo_lancer_m.swf,assets/thumbs/1082_robo_lancer_m.jpg,Y,Y
1083,Crusader Tank,u,7,7,80,1083_demlisher_tank_m,assets/sprites/1083_demlisher_tank_m.swf,assets/thumbs/1083_demlisher_tank_m.jpg,Y,Y
1084,Dreadnought,u,7,7,80,1084_dreadnought_m,assets/sprites/1084_dreadnought_m.swf,assets/thumbs/1084_dreadnought_m.jpg,Y,Y
1085,Metal Draggy,u,7,7,83,1085_metal_draggy_m,assets/sprites/1085_metal_draggy_m.swf,assets/thumbs/1085_metal_draggy_m.jpg,Y,Y
1086,Mechanical Golem,u,7,7,80,1053_golem_boss_m,assets/sprites/1053_golem_boss_m.swf,assets/thumbs/1053_golem_boss_m.jpg,Y,Y
1087,T-Rex,u,7,7,80,1057_t-rex_m,assets/sprites/1057_t-rex_m.swf,assets/thumbs/1057_t-rex_m.jpg,Y,Y
1088,Skylander,u,7,7,80,1088_skylander_m,assets/sprites/1088_skylander_m.swf,assets/thumbs/1088_skylander_m.jpg,Y,Y
1089,Mega-Axe,u,7,7,80,1089_robo_axe_m,assets/sprites/1089_robo_axe_m.swf,assets/thumbs/1089_robo_axe_m.jpg,Y,Y
1090,Giant Walker,u,7,7,80,1090_giant_walker_m,assets/sprites/1090_giant_walker_m.swf,assets/thumbs/1090_giant_walker_m.jpg,Y,Y
1091,Missile Tank,u,7,7,80,1091_missile_tank_m,assets/sprites/1091_missile_tank_m.swf,assets/thumbs/1091_missile_tank_m.jpg,Y,Y
1092,Steel Claws,u,7,7,80,1092_steel_claws_m,assets/sprites/1092_steel_claws_m.swf,assets/thumbs/1092_steel_claws_m.jpg,Y,Y
1093,Fire T-Rex,u,7,7,80,1093_trex_m,assets/sprites/1093_trex_m.swf,assets/thumbs/1093_trex_m.jpg,Y,Y
1094,Aircraft IV,u,7,7,83,1094_aircraft_4_m,assets/sprites/1094_aircraft_4_m.swf,assets/thumbs/1094_aircraft_4_m.jpg,Y,Y
1095,Aircraft V,u,7,7,83,1095_aircraft_5_m,assets/sprites/1095_aircraft_5_m.swf,assets/thumbs/1095_aircraft_5_m.jpg,Y,Y
1096,F-117,u,7,7,83,1096_f117_m,assets/sprites/1096_f117_m.swf,assets/thumbs/1096_f117_m.jpg,Y,Y
1097,Red Draggy,u,7,7,83,1097_red_draggy_m,assets/sprites/1097_red_draggy_m.swf,assets/thumbs/1097_red_draggy_m.jpg,Y,Y
1098,Blue Draggy,u,7,7,83,1098_blue_draggy_m,assets/sprites/1098_blue_draggy_m.swf,assets/thumbs/1098_blue_draggy_m.jpg,Y,Y
1099,Red Dragon,u,7,7,83,1099_red_dragon2_m,assets/sprites/1099_red_dragon2_m.swf,assets/thumbs/1099_red_dragon2_m.jpg,Y,Y
1100,Blue Dragon,u,7,7,83,1100_blue_dragon2_m,assets/sprites/1100_blue_dragon2_m.swf,assets/thumbs/1100_blue_dragon2_m.jpg,Y,Y
1101,Celestial Megamech,u,7,7,80,1101_celestial_megamech_m,assets/sprites/1101_celestial_megamech_m.swf,assets/thumbs/1101_celestial_megamech_m.jpg,Y,Y
1102,Red Baron,u,7,7,83,1102_red_baron_m,assets/sprites/1102_red_baron_m.swf,assets/thumbs/1102_red_baron_m.jpg,Y,Y
1103,Zeppelin,u,7,7,83,1103_zeppelin_m,assets/sprites/1103_zeppelin_m.swf,assets/thumbs/1103_zeppelin_m.jpg,Y,Y
1104,Fireman,u,7,7,71,1104_fireman_1_m,assets/sprites/1104_fireman_1_m.swf,assets/thumbs/1104_fireman_1_m.jpg,Y,Y
1105,Metal Dragon,u,7,7,83,1105_metalico_dragon3_m,assets/sprites/1105_metalico_dragon3_m.swf,assets/thumbs/1105_metalico_dragon3_m.jpg,Y,Y
1106,Axe Zoldier,u,7,7,80,1106_hacha_m_2,assets/sprites/1106_hacha_m_2.swf,assets/thumbs/1106_hacha_m_2.jpg,Y,Y
1107,Gun Zoldier,u,7,7,80,1107_metralleta_m_2,assets/sprites/1107_metralleta_m_2.swf,assets/thumbs/1107_metralleta_m_2.jpg,Y,Y
1108,Xplosive Ork,u,7,7,80,1108_orc_boss_m_2,assets/sprites/1108_orc_boss_m_2.swf,assets/thumbs/1108_orc_boss_m_2.jpg,Y,Y
1109,Bear Ridda,u,7,7,80,1109_orco_jinete_m_2,assets/sprites/1109_orco_jinete_m_2.swf,assets/thumbs/1109_orco_jinete_m_2.jpg,Y,Y
1110,Molotov Kopta,u,7,7,80,1110_helicoptero_orco_m2,assets/sprites/1110_helicoptero_orco_m2.swf,assets/thumbs/1110_helicoptero_orco_m2.jpg,Y,Y
1111,Horned Badass,u,7,7,80,1111_robot_orco_1_m,assets/sprites/1111_robot_orco_1_m.swf,assets/thumbs/1111_robot_orco_1_m.jpg,Y,Y
1112,Red Spinner,u,7,7,80,1112_optimus_m,assets/sprites/1112_optimus_m.swf,assets/thumbs/1112_optimus_m.jpg,Y,Y
1113,Flamethrowa Ork,u,7,7,80,1113_orc_flamethrower_m,assets/sprites/1113_orc_flamethrower_m.swf,assets/thumbs/1113_orc_flamethrower_m.jpg,Y,Y
1114,Knife Throwa,u,7,7,80,1114_orc_knivethrower_m,assets/sprites/1114_orc_knivethrower_m.swf,assets/thumbs/1114_orc_knivethrower_m.jpg,Y,Y
1115,Big Handsaw Ork,u,7,7,80,1115_orc_robot_22_m,assets/sprites/1115_orc_robot_22_m.swf,assets/thumbs/1115_orc_robot_22_m.jpg,Y,Y
1116,Orc Tank,u,7,7,80,1116_orc_tank_m,assets/sprites/1116_orc_tank_m.swf,assets/thumbs/1116_orc_tank_m.jpg,Y,Y
1117,Kamikaze team,u,7,7,80,1117_orc_kamikaze_team,assets/sprites/1117_orc_kamikaze_team.swf,assets/thumbs/1117_orc_kamikaze_team.jpg,Y,Y
1118,Kamikaze critter,u,7,7,80,1118_squig_kamikaze,assets/sprites/1118_squig_kamikaze.swf,assets/thumbs/1118_squig_kamikaze.jpg,Y,Y
1119,Camu Metal Dragon,u,7,7,83,1119_metal_dragon2_m,assets/sprites/1119_metal_dragon2_m.swf,assets/thumbs/1119_metal_dragon2_m.jpg,Y,Y
1120,Camu Draggy,u,7,7,83,1120_metal_draggy_2_m,assets/sprites/1120_metal_draggy_2_m.swf,assets/thumbs/1120_metal_draggy_2_m.jpg,Y,Y
1121,War Buggy,u,7,7,80,1121_buggy_2_m,assets/sprites/1121_buggy_2_m.swf,assets/thumbs/1121_buggy_2_m.jpg,Y,Y
1122,Orc Zoldier,u,7,7,80,1122_orc_basic_gun_2,assets/sprites/1122_orc_basic_gun_2.swf,assets/thumbs/1122_orc_basic_gun_2.jpg,Y,Y
1123,Orc Swordsman,u,7,7,80,1123_orc_basic_knife_2,assets/sprites/1123_orc_basic_knife_2.swf,assets/thumbs/1123_orc_basic_knife_2.jpg,Y,Y
1124,Basic Ork Tank,u,7,7,80,1124_ork_tank_1,assets/sprites/1124_ork_tank_1.swf,assets/thumbs/1124_ork_tank_1.jpg,Y,Y
1125,Orc Worker,u,7,7,71,1125_orc_worker,assets/sprites/1125_orc_worker.swf,assets/thumbs/1125_orc_worker.jpg,Y,Y
1126,Samurai Bot,u,7,7,80,1126_samurai_bot_m,assets/sprites/1126_samurai_bot_m.swf,assets/thumbs/1126_samurai_bot_m.jpg,Y,Y
1127,Armored Core Alpha,u,7,7,80,1127_huge_robot_m,assets/sprites/1127_huge_robot_m.swf,assets/thumbs/1127_huge_robot_m.jpg,Y,Y
1128,Alpha Drone,u,7,7,83,1128_huge_draggy_m,assets/sprites/1128_huge_draggy_m.swf,assets/thumbs/1128_huge_draggy_m.jpg,Y,Y
1129,Samurai Minibot,u,7,7,80,1129_samurai_minibot,assets/sprites/1129_samurai_minibot.swf,,Y,N
1130,Xplosive Beast Boss,u,7,7,80,1130_xplosive_boss_2,assets/sprites/1130_xplosive_boss_2.swf,assets/thumbs/1130_xplosive_boss_2.jpg,Y,Y
1131,Xplosive Beast ATP,u,7,7,80,1116_orc_tank_m_2,assets/sprites/1116_orc_tank_m_2.swf,assets/thumbs/1116_orc_tank_m_2.jpg,Y,Y
1132,Xplosive Beast,u,7,7,80,1108_orc_boss_m_2,assets/sprites/1108_orc_boss_m_2.swf,assets/thumbs/1108_orc_boss_m_2.jpg,Y,Y
1133,Ork Bear Knight,u,7,7,80,1109_orco_jinete_m_2,assets/sprites/1109_orco_jinete_m_2.swf,assets/thumbs/1109_orco_jinete_m_2.jpg,Y,Y
1134,Ork Kopta,u,7,7,80,1110_helicoptero_orco_m2,assets/sprites/1110_helicoptero_orco_m2.swf,assets/thumbs/1110_helicoptero_orco_m2.jpg,Y,Y
1135,Horned Beast Ork,u,7,7,80,1111_robot_orco_1_m,assets/sprites/1111_robot_orco_1_m.swf,assets/thumbs/1111_robot_orco_1_m.jpg,Y,Y
1136,Red Flamethrowa Ork,u,7,7,80,1113_orc_flamethrower_m,assets/sprites/1113_orc_flamethrower_m.swf,assets/thumbs/1113_orc_flamethrower_m.jpg,Y,Y
1137,Orc Knifethrower,u,7,7,80,1114_orc_knivethrower_m,assets/sprites/1114_orc_knivethrower_m.swf,assets/thumbs/1114_orc_knivethrower_m.jpg,Y,Y
1138,Red Handsaw Ork,u,7,7,80,1115_orc_robot_22_m,assets/sprites/1115_orc_robot_22_m.swf,assets/thumbs/1115_orc_robot_22_m.jpg,Y,Y
1139,Kamikaze Bros,u,7,7,80,1117_orc_kamikaze_team,assets/sprites/1117_orc_kamikaze_team.swf,assets/thumbs/1117_orc_kamikaze_team.jpg,Y,Y
1140,Kamikaze Pet,u,7,7,80,1118_squig_kamikaze,assets/sprites/1118_squig_kamikaze.swf,assets/thumbs/1118_squig_kamikaze.jpg,Y,Y
1141,Samurai Bot,u,7,7,80,1126_samurai_bot_m,assets/sprites/1126_samurai_bot_m.swf,assets/thumbs/1126_samurai_bot_m.jpg,Y,Y
1142,Samurai Minibot,u,7,7,80,1129_samurai_minibot_m,assets/sprites/1129_samurai_minibot_m.swf,assets/thumbs/1129_samurai_minibot_m.jpg,Y,Y
1143,Melee Spider,u,7,7,80,1143_melee_spider_s,assets/sprites/1143_melee_spider_s.swf,assets/thumbs/1143_melee_spider_s.jpg,Y,Y
1144,Venom Spider,u,7,7,80,1144_ranged_spider_s,assets/sprites/1144_ranged_spider_s.swf,assets/thumbs/1144_ranged_spider_s.jpg,Y,Y
1145,Big Spider,u,7,7,80,1145_spider_semi_boss_s_2,assets/sprites/1145_spider_semi_boss_s_2.swf,assets/thumbs/1145_spider_semi_boss_s_2.jpg,Y,Y
1146,Small Alien,u,7,7,80,1146_basic_alien_s,assets/sprites/1146_basic_alien_s.swf,assets/thumbs/1146_basic_alien_s.jpg,Y,Y
1147,Tusk Alien,u,7,7,80,1147_alien_bull_s,assets/sprites/1147_alien_bull_s.swf,assets/thumbs/1147_alien_bull_s.jpg,Y,Y
1148,Claw Alien,u,7,7,80,1148_alien_claws_s,assets/sprites/1148_alien_claws_s.swf,assets/thumbs/1148_alien_claws_s.jpg,Y,Y
1149,Orc Big Tank,u,7,7,80,1116_orc_tank_m,assets/sprites/1116_orc_tank_m.swf,assets/thumbs/1116_orc_tank_m.jpg,Y,Y
1150,Crusader Bot,u,7,7,80,1150_crusader_bot,assets/sprites/1150_crusader_bot.swf,assets/thumbs/1150_crusader_bot.jpg,Y,Y
1151,Crusader Priest,u,7,7,80,1151_crusader_priest,assets/sprites/1151_crusader_priest.swf,assets/thumbs/1151_crusader_priest.jpg,Y,Y
1152,Ultra-Mech,u,7,7,80,1152_transformer_gigante,assets/sprites/1152_transformer_gigante.swf,assets/thumbs/1152_transformer_gigante.jpg,Y,Y
1153,Ultra-Mech Drone,u,7,7,83,1153_transformer_gigante_drone,assets/sprites/1153_transformer_gigante_drone.swf,assets/thumbs/1153_transformer_gigante_drone.jpg,Y,Y
1154,Viking Axeman,u,7,7,80,1154_axeman,assets/sprites/1154_axeman.swf,assets/thumbs/1154_axeman.jpg,Y,Y
1155,Viking Soldier,u,7,7,80,1155_dwarf_soldier,assets/sprites/1155_dwarf_soldier.swf,assets/thumbs/1155_dwarf_soldier.jpg,Y,Y
1156,Viking Bear Knight,u,7,7,80,1156_bear_knight,assets/sprites/1156_bear_knight.swf,assets/thumbs/1156_bear_knight.jpg,Y,Y
1157,Viking Tank,u,7,7,80,1157_dwarf_tank,assets/sprites/1157_dwarf_tank.swf,assets/thumbs/1157_dwarf_tank.jpg,Y,Y
1158,Viking Airship,u,7,7,80,1158_viking_copter_II,assets/sprites/1158_viking_copter_II.swf,assets/thumbs/1158_viking_copter_II.jpg,Y,Y
1159,Viking Hammerer,u,7,7,80,1159_megahammer_dwarf,assets/sprites/1159_megahammer_dwarf.swf,assets/thumbs/1159_megahammer_dwarf.jpg,Y,Y
1160,Viking Core Bot,u,7,7,80,1160_dwarf_armored_core,assets/sprites/1160_dwarf_armored_core.swf,assets/thumbs/1160_dwarf_armored_core.jpg,Y,Y
1161,Rune Golem,u,7,7,80,1161_viking_rune_golem,assets/sprites/1161_viking_rune_golem.swf,,Y,N
1162,Nemesis Core,u,7,7,80,1162_ultra_robot,assets/sprites/1162_ultra_robot.swf,assets/thumbs/1162_ultra_robot.jpg,Y,Y
1163,Nemesis Drone,u,7,7,83,1163_ultra_robot_drone,assets/sprites/1163_ultra_robot_drone.swf,assets/thumbs/1163_ultra_robot_drone.jpg,Y,Y
1164,Viking Core Bot Drone,u,7,7,83,1164_dwarf_armored_core_drone,assets/sprites/1164_dwarf_armored_core_drone.swf,assets/thumbs/1164_dwarf_armored_core_drone.jpg,Y,Y
1165,Viking Bazooka,u,7,7,80,1165_bazooka_viking,assets/sprites/1165_bazooka_viking.swf,assets/thumbs/1165_bazooka_viking.jpg,Y,Y
1166,Viking MotoSquad,u,7,7,80,1166_viking_motosquad,assets/sprites/1166_viking_motosquad.swf,assets/thumbs/1166_viking_motosquad.jpg,Y,Y
1167,Blue Steel Bahamut,u,7,7,83,1167_bahamut_metalico,assets/sprites/1167_bahamut_metalico.swf,assets/thumbs/1167_bahamut_metalico.jpg,Y,Y
1168,Blue Steel Draggy,u,7,7,83,1168_bahamut_metalico_draggy,assets/sprites/1168_bahamut_metalico_draggy.swf,assets/thumbs/1168_bahamut_metalico_draggy.jpg,Y,Y
1169,Roller Skater,u,7,7,80,1169_transformer_skater,assets/sprites/1169_transformer_skater.swf,assets/thumbs/1169_transformer_skater.jpg,Y,Y
1170,Alien Instigator,u,7,7,80,1170_alien_instigator,assets/sprites/1170_alien_instigator.swf,assets/thumbs/1170_alien_instigator.jpg,Y,Y
1171,Rune Golem Drone,u,7,7,83,1171_viking_rune_golem_drone,assets/sprites/1171_viking_rune_golem_drone.swf,assets/thumbs/1171_viking_rune_golem_drone.jpg,Y,Y
1172,Hyper Blazer,u,7,7,80,1172_mega_fire_bot,assets/sprites/1172_mega_fire_bot.swf,assets/thumbs/1172_mega_fire_bot.jpg,Y,Y
1173,Hyper Blazer Drone,u,7,7,83,1173_mega_fire_bot_drone,assets/sprites/1173_mega_fire_bot_drone.swf,assets/thumbs/1173_mega_fire_bot_drone.jpg,Y,Y
1174,Viking Sniper,u,7,7,80,1174_viking_sniper,assets/sprites/1174_viking_sniper.swf,assets/thumbs/1174_viking_sniper.jpg,Y,Y
1175,Chainsaw Butcher,u,7,7,80,1175_viking_butcher,assets/sprites/1175_viking_butcher.swf,assets/thumbs/1175_viking_butcher.jpg,Y,Y
1176,Kamikaze,u,7,7,80,1176_kamikaze,assets/sprites/1176_kamikaze.swf,assets/thumbs/1176_kamikaze.jpg,Y,Y
1177,UFO,u,7,7,80,1177_ufo,assets/sprites/1177_ufo.swf,assets/thumbs/1177_ufo.jpg,Y,Y
1178,Ether Messiah,u,7,7,80,1178_ether_messiah,assets/sprites/1178_ether_messiah.swf,assets/thumbs/1178_ether_messiah.jpg,Y,Y
1179,Ether Messiah Drone,u,7,7,83,1179_ether_messiah_drone,assets/sprites/1179_ether_messiah_drone.swf,assets/thumbs/1179_ether_messiah_drone.jpg,Y,Y
1180,Robot Hunter,u,7,7,80,1180_robot_hunter,assets/sprites/1180_robot_hunter.swf,assets/thumbs/1180_robot_hunter.jpg,Y,Y
1181,Golden Slayer,u,7,7,80,1181_transformer_sword,assets/sprites/1181_transformer_sword.swf,assets/thumbs/1181_transformer_sword.jpg,Y,Y
1182,Golden Slayer Drone,u,7,7,83,1182_transformer_sword_drone,assets/sprites/1182_transformer_sword_drone.swf,assets/thumbs/1182_transformer_sword_drone.jpg,Y,Y
1183,Big Laser Viking,u,7,7,80,1183_laser_viking,assets/sprites/1183_laser_viking.swf,assets/thumbs/1183_laser_viking.jpg,Y,Y
1184,Fire Karateka,u,7,7,80,1184_karateka,assets/sprites/1184_karateka.swf,assets/thumbs/1184_karateka.jpg,Y,Y
1185,MegaFire T-Rex,u,7,7,80,1093_trex_m,assets/sprites/1093_trex_m.swf,assets/thumbs/1093_trex_m.jpg,Y,Y
1186,Nebular Spearman,u,7,7,80,1186_avatar_soldado,assets/sprites/1186_avatar_soldado.swf,assets/thumbs/1186_avatar_soldado.jpg,Y,Y
1187,Nebular Archer,u,7,7,80,1187_avatar_arquero,assets/sprites/1187_avatar_arquero.swf,assets/thumbs/1187_avatar_arquero.jpg,Y,Y
1188,Greatsword Warrior,u,7,7,80,1188_avatar_great_warrior,assets/sprites/1188_avatar_great_warrior.swf,assets/thumbs/1188_avatar_great_warrior.jpg,Y,Y
1189,Nebular Rider,u,7,7,80,1189_avatar_jinete,assets/sprites/1189_avatar_jinete.swf,assets/thumbs/1189_avatar_jinete.jpg,Y,Y
1190,Golden Golem,u,7,7,80,1190_gold_golem,assets/sprites/1190_gold_golem.swf,assets/thumbs/1190_gold_golem.jpg,Y,Y
1191,Black Dragon,u,7,7,83,1191_black_dragon,assets/sprites/1191_black_dragon.swf,assets/thumbs/1191_black_dragon.jpg,Y,Y
1192,Dragonborn Mech,u,7,7,80,1192_dragon_mech,assets/sprites/1192_dragon_mech.swf,assets/thumbs/1192_dragon_mech.jpg,Y,Y
1193,Dragonborn Drone,u,7,7,83,1193_dragon_mech_drone,assets/sprites/1193_dragon_mech_drone.swf,assets/thumbs/1193_dragon_mech_drone.jpg,Y,Y
1194,Electric Dragon,u,7,7,80,1194_electric_dragon_2,assets/sprites/1194_electric_dragon_2.swf,assets/thumbs/1194_electric_dragon_2.jpg,Y,Y
1195,Electric Draggy,u,7,7,83,1195_electric_draggy,assets/sprites/1195_electric_draggy.swf,assets/thumbs/1195_electric_draggy.jpg,Y,Y
1196,Black Draggy,u,7,7,83,1196_black_draggy,assets/sprites/1196_black_draggy.swf,assets/thumbs/1196_black_draggy.jpg,Y,Y
1197,Silver Hercules,u,7,7,80,1197_herkules_matrix,assets/sprites/1197_herkules_matrix.swf,assets/thumbs/1197_herkules_matrix.jpg,Y,Y
1198,Nebular Knight,u,7,7,80,1198_nebular_horse_rider,assets/sprites/1198_nebular_horse_rider.swf,assets/thumbs/1198_nebular_horse_rider.jpg,Y,Y
1199,Nebular Dragon Rider,u,7,7,83,1199_nebular_dragon_rider,assets/sprites/1199_nebular_dragon_rider.swf,assets/thumbs/1199_nebular_dragon_rider.jpg,Y,Y
1200,Nebular Assault Quad,u,7,7,80,1200_nebular_motorized,assets/sprites/1200_nebular_motorized.swf,assets/thumbs/1200_nebular_motorized.jpg,Y,Y
1201,Steel Collector,u,7,7,80,1201_junk_bot,assets/sprites/1201_junk_bot.swf,assets/thumbs/1201_junk_bot.jpg,Y,Y
1202,Nebular Dragon Rider Draggy,u,7,7,83,1202_nebular_dragon_rider_draggy,assets/sprites/1202_nebular_dragon_rider_draggy.swf,assets/thumbs/1202_nebular_dragon_rider_draggy.jpg,Y,Y
1203,Viking Airship Outsider,u,7,7,80,1158_viking_copter_II,assets/sprites/1158_viking_copter_II.swf,assets/thumbs/1158_viking_copter_II.jpg,Y,Y
1204,Viking Hammerer Outsider,u,7,7,80,1159_megahammer_dwarf,assets/sprites/1159_megahammer_dwarf.swf,assets/thumbs/1159_megahammer_dwarf.jpg,Y,Y
1205,Dual Blade Automech,u,7,7,80,1205_dual_blade_automech,assets/sprites/1205_dual_blade_automech.swf,assets/thumbs/1205_dual_blade_automech.jpg,Y,Y
1206,Dual Blade Automech Drone,u,7,7,83,1206_dual_blade_automech_drone,assets/sprites/1206_dual_blade_automech_drone.swf,assets/thumbs/1206_dual_blade_automech_drone.jpg,Y,Y
1207,Black Belt Archer,u,7,7,80,1207_transformer_archer,assets/sprites/1207_transformer_archer.swf,assets/thumbs/1207_transformer_archer.jpg,Y,Y
1208,Nebular Priest,u,7,7,80,1208_nebula_priest,assets/sprites/1208_nebula_priest.swf,assets/thumbs/1208_nebula_priest.jpg,Y,Y
1209,Nebular Bicopter,u,7,7,83,1209_nebular_blue_bicopter,assets/sprites/1209_nebular_blue_bicopter.swf,assets/thumbs/1209_nebular_blue_bicopter.jpg,Y,Y
1210,Great Shogun Mech,u,7,7,80,1210_samurai_mech,assets/sprites/1210_samurai_mech.swf,assets/thumbs/1210_samurai_mech.jpg,Y,Y
1211,Great Shogun Mech Drone,u,7,7,83,1211_samurai_mech_drone,assets/sprites/1211_samurai_mech_drone.swf,assets/thumbs/1211_samurai_mech_drone.jpg,Y,Y
1212,ATP Mech,u,7,7,80,1212_tetrapod_mech,assets/sprites/1212_tetrapod_mech.swf,assets/thumbs/1212_tetrapod_mech.jpg,Y,Y
1213,Blazing Beast Rider,u,7,7,80,1213_nebular_monster_rider,assets/sprites/1213_nebular_monster_rider.swf,assets/thumbs/1213_nebular_monster_rider.jpg,Y,Y
1214,Nebular Maze Warrior,u,7,7,80,1214_nebular_maze_warrior,assets/sprites/1214_nebular_maze_warrior.swf,assets/thumbs/1214_nebular_maze_warrior.jpg,Y,Y
1215,Massive Cannon Mech,u,7,7,80,1215_massive_cannon_mech,assets/sprites/1215_massive_cannon_mech.swf,assets/thumbs/1215_massive_cannon_mech.jpg,Y,Y
1216,Massive Cannon Drone,u,7,7,83,1216_massive_cannon_drone,assets/sprites/1216_massive_cannon_drone.swf,assets/thumbs/1216_massive_cannon_drone.jpg,Y,Y
1217,Brutus Mech,u,7,7,80,1217_brutus_mech,assets/sprites/1217_brutus_mech.swf,assets/thumbs/1217_brutus_mech.jpg,Y,Y
1218,S.W.A.T. Soldier,u,7,7,80,1218_swat_soldier,assets/sprites/1218_swat_soldier.swf,assets/thumbs/1218_swat_soldier.jpg,Y,Y
1219,Nebular Dragon Knight,u,7,7,80,1219_nebular_rider,assets/sprites/1219_nebular_rider.swf,assets/thumbs/1219_nebular_rider.jpg,Y,Y
1220,Nebular Sniper,u,7,7,80,1220_nebular_sniper,assets/sprites/1220_nebular_sniper.swf,assets/thumbs/1220_nebular_sniper.jpg,Y,Y
1221,Nebular Dragon Knight Draggy,u,7,7,83,1221_nebular_rider_draggy,assets/sprites/1221_nebular_rider_draggy.swf,assets/thumbs/1221_nebular_rider_draggy.jpg,Y,Y
1222,Liquid Mech ,u,7,7,80,1222_liquid_mech,assets/sprites/1222_liquid_mech.swf,assets/thumbs/1222_liquid_mech.jpg,Y,Y
1223,Killer Driller,u,7,7,80,1223_drill,assets/sprites/1223_drill.swf,assets/thumbs/1223_drill.jpg,Y,Y
1224,Liquid Mech  Drone,u,7,7,83,1224_liquid_mech _drone,assets/sprites/1224_liquid_mech _drone.swf,assets/thumbs/1224_liquid_mech _drone.jpg,Y,Y
1225,Doctor Shock,u,7,7,80,1225_doctor_shock,assets/sprites/1225_doctor_shock.swf,assets/thumbs/1225_doctor_shock.jpg,Y,Y
1226,Red Mercury Dragon,u,7,7,80,1226_dragon_metalic,assets/sprites/1226_dragon_metalic.swf,assets/thumbs/1226_dragon_metalic.jpg,Y,Y
1227,Red Mercury Draggy,u,7,7,83,1227_dragon_metalic_draggy,assets/sprites/1227_dragon_metalic_draggy.swf,assets/thumbs/1227_dragon_metalic_draggy.jpg,Y,Y
1228,Swamp Monster,u,7,7,80,1228_nebula_monster,assets/sprites/1228_nebula_monster.swf,assets/thumbs/1228_nebula_monster.jpg,Y,Y
1229,Poison Spider,u,7,7,80,1144_ranged_spider_s,assets/sprites/1144_ranged_spider_s.swf,assets/thumbs/1144_ranged_spider_s.jpg,Y,Y
1230,Shredder Alien,u,7,7,80,1148_alien_claws_s,assets/sprites/1148_alien_claws_s.swf,assets/thumbs/1148_alien_claws_s.jpg,Y,Y
1231,Swamp Minion,u,7,7,80,1231_nebula_monster_mini,assets/sprites/1231_nebula_monster_mini.swf,assets/thumbs/1231_nebula_monster_mini.jpg,Y,Y
1232,Claw Spider,u,7,7,80,1143_melee_spider_s,assets/sprites/1143_melee_spider_s.swf,assets/thumbs/1143_melee_spider_s.jpg,Y,Y
1233,Huge Spider,u,7,7,80,1145_spider_semi_boss_s_2,assets/sprites/1145_spider_semi_boss_s_2.swf,assets/thumbs/1145_spider_semi_boss_s_2.jpg,Y,Y
1234,Acid Alien,u,7,7,80,1146_basic_alien_s,assets/sprites/1146_basic_alien_s.swf,assets/thumbs/1146_basic_alien_s.jpg,Y,Y
1235,Horned Alien,u,7,7,80,1147_alien_bull_s,assets/sprites/1147_alien_bull_s.swf,assets/thumbs/1147_alien_bull_s.jpg,Y,Y
1236,2-Gun Exobot,u,7,7,80,1236_2gun_exobot,assets/sprites/1236_2gun_exobot.swf,assets/thumbs/1236_2gun_exobot.jpg,Y,Y
1237,Cyber Samurai Mech,u,7,7,80,1237_cyber_samurai_mech,assets/sprites/1237_cyber_samurai_mech.swf,assets/thumbs/1237_cyber_samurai_mech.jpg,Y,Y
1238,Cyber Samurai  Drone,u,7,7,83,1238_cyber_samurai_mech_drone,assets/sprites/1238_cyber_samurai_mech_drone.swf,assets/thumbs/1238_cyber_samurai_mech_drone.jpg,Y,Y
1239,Dark Ether Messiah,u,7,7,80,1239_dark_ether_messiah,assets/sprites/1239_dark_ether_messiah.swf,assets/thumbs/1239_dark_ether_messiah.jpg,Y,Y
1240,Dark Ether Messiah Drone,u,7,7,83,1240_dark_ether_messiah_drone,assets/sprites/1240_dark_ether_messiah_drone.swf,assets/thumbs/1240_dark_ether_messiah_drone.jpg,Y,Y
1241,Converter Wizard,u,7,7,80,1241_enemy_converter_priest,assets/sprites/1241_enemy_converter_priest.swf,assets/thumbs/1241_enemy_converter_priest.jpg,Y,Y
1242,Hercules Mech,u,7,7,80,1242_herkules_mech,assets/sprites/1242_herkules_mech.swf,assets/thumbs/1242_herkules_mech.jpg,Y,Y
1243,Forge Dragon,u,7,7,80,1243_forge_dragon,assets/sprites/1243_forge_dragon.swf,assets/thumbs/1243_forge_dragon.jpg,Y,Y
1244,Forge Dragon Draggy,u,7,7,83,1244_forge_draggy,assets/sprites/1244_forge_draggy.swf,assets/thumbs/1244_forge_draggy.jpg,Y,Y
1245,Reptile Gun,u,7,7,80,1245_reptile_gun,assets/sprites/1245_reptile_gun.swf,assets/thumbs/1245_reptile_gun.jpg,Y,Y
1246,Double Cannon Mech,u,7,7,80,1246_double_cannon_mech,assets/sprites/1246_double_cannon_mech.swf,assets/thumbs/1246_double_cannon_mech.jpg,Y,Y
1247,Double Cannon Drone,u,7,7,83,1247_double_cannon_drone,assets/sprites/1247_double_cannon_drone.swf,assets/thumbs/1247_double_cannon_drone.jpg,Y,Y
1248,Laser Blade Automech,u,7,7,80,1248_laser_blade_automech,assets/sprites/1248_laser_blade_automech.swf,assets/thumbs/1248_laser_blade_automech.jpg,Y,Y
1249,Laser Blade Automech Drone,u,7,7,83,1249_laser_blade_automech_drone,assets/sprites/1249_laser_blade_automech_drone.swf,assets/thumbs/1249_laser_blade_automech_drone.jpg,Y,Y
1250,Burning Slayer,u,7,7,80,1250_red_slayer,assets/sprites/1250_red_slayer.swf,assets/thumbs/1250_red_slayer.jpg,Y,Y
1251,Burning Slayer Drone,u,7,7,83,1251_red_slayer_drone,assets/sprites/1251_red_slayer_drone.swf,assets/thumbs/1251_red_slayer_drone.jpg,Y,Y
1252,Karateka Gunner,u,7,7,80,1252_karateka_gunner,assets/sprites/1252_karateka_gunner.swf,assets/thumbs/1252_karateka_gunner.jpg,Y,Y
1253,Swamp Monster,u,7,7,80,1228_nebula_monster,assets/sprites/1228_nebula_monster.swf,assets/thumbs/1228_nebula_monster.jpg,Y,Y
1254,Prime Automech,u,7,7,80,1254_optimus_prime,assets/sprites/1254_optimus_prime.swf,assets/thumbs/1254_optimus_prime.jpg,Y,Y
1255,Prime Automech Drone,u,7,7,83,1255_optimus_prime_drone,assets/sprites/1255_optimus_prime_drone.swf,assets/thumbs/1255_optimus_prime_drone.jpg,Y,Y
1256,Big Razor Mech,u,7,7,80,1256_big_razor_mech,assets/sprites/1256_big_razor_mech.swf,assets/thumbs/1256_big_razor_mech.jpg,Y,Y
1257,Big Razor Mech Drone,u,7,7,83,1257_big_razor_mech_drone,assets/sprites/1257_big_razor_mech_drone.swf,assets/thumbs/1257_big_razor_mech_drone.jpg,Y,Y
1258,S.W.A.T. Soldier,u,7,7,80,1218_swat_soldier,assets/sprites/1218_swat_soldier.swf,assets/thumbs/1218_swat_soldier.jpg,Y,Y
1259,Space Sword Elf,u,7,7,80,1259_spatial_sward,assets/sprites/1259_spatial_sward.swf,assets/thumbs/1259_spatial_sward.jpg,Y,Y
1260,Space Archer Elf,u,7,7,80,1260_spatial_archer,assets/sprites/1260_spatial_archer.swf,assets/thumbs/1260_spatial_archer.jpg,Y,Y
1261,Space Knight Elf,u,7,7,80,1261_spatial_horseman,assets/sprites/1261_spatial_horseman.swf,assets/thumbs/1261_spatial_horseman.jpg,Y,Y
1262,Space Airship Elf,u,7,7,83,1262_spatial_airship,assets/sprites/1262_spatial_airship.swf,assets/thumbs/1262_spatial_airship.jpg,Y,Y
1263,Spartan Warrior Mech,u,7,7,80,1263_spartan_warrior_mech,assets/sprites/1263_spartan_warrior_mech.swf,assets/thumbs/1263_spartan_warrior_mech.jpg,Y,Y
1264,Spartan Warrior Drone,u,7,7,83,1264_spartan_warrior_drone,assets/sprites/1264_spartan_warrior_drone.swf,assets/thumbs/1264_spartan_warrior_drone.jpg,Y,Y
1265,Space Priest Elf,u,7,7,80,1265_spatial_priest,assets/sprites/1265_spatial_priest.swf,assets/thumbs/1265_spatial_priest.jpg,Y,Y
1266,Space Paladin Elf,u,7,7,80,1266_spatial_paladin,assets/sprites/1266_spatial_paladin.swf,assets/thumbs/1266_spatial_paladin.jpg,Y,Y
1267,Space Elf Cruiser,u,7,7,83,1267_spatial_space_ship,assets/sprites/1267_spatial_space_ship.swf,assets/thumbs/1267_spatial_space_ship.jpg,Y,Y
1268,Proto Winged Mech,u,7,7,80,1268_winged_transformer,assets/sprites/1268_winged_transformer.swf,assets/thumbs/1268_winged_transformer.jpg,Y,Y
1269,Proto Winged Drone,u,7,7,83,1269_winged_transformer_drone,assets/sprites/1269_winged_transformer_drone.swf,assets/thumbs/1269_winged_transformer_drone.jpg,Y,Y
1270,Spider Bot,u,7,7,80,1270_spider_bot,assets/sprites/1270_spider_bot.swf,assets/thumbs/1270_spider_bot.jpg,Y,Y
1271,Pharaoh Warrior Mech,u,7,7,80,1271_egyptian_warrior_mech,assets/sprites/1271_egyptian_warrior_mech.swf,assets/thumbs/1271_egyptian_warrior_mech.jpg,Y,Y
1272,Arachnid Mech,u,7,7,80,1272_transformer_aracnid,assets/sprites/1272_transformer_aracnid.swf,assets/thumbs/1272_transformer_aracnid.jpg,Y,Y
1273,Arachnid Drone,u,7,7,83,1273_transformer_aracnid_drone,assets/sprites/1273_transformer_aracnid_drone.swf,assets/thumbs/1273_transformer_aracnid_drone.jpg,Y,Y
1274,Multi Morpher,u,7,7,80,1274_multi_morph,assets/sprites/1274_multi_morph.swf,assets/thumbs/1274_multi_morph.jpg,Y,Y
1275,Space Healer Elf,u,7,7,80,1275_spatial_elf_healer,assets/sprites/1275_spatial_elf_healer.swf,assets/thumbs/1275_spatial_elf_healer.jpg,Y,Y
1276,Space Scouter Elf,u,7,7,80,1276_spatial_exploration_module,assets/sprites/1276_spatial_exploration_module.swf,assets/thumbs/1276_spatial_exploration_module.jpg,Y,Y
1277,Pharaoh Mech Drone,u,7,7,83,1277_egyptian_warrior_drone,assets/sprites/1277_egyptian_warrior_drone.swf,assets/thumbs/1277_egyptian_warrior_drone.jpg,Y,Y
1278,MegaBot,u,7,7,80,1062_bumblebee_m,assets/sprites/1062_bumblebee_m.swf,assets/thumbs/1062_bumblebee_m.jpg,Y,Y
1279,Black Brutus Mech,u,7,7,80,1279_black_brutus_mech,assets/sprites/1279_black_brutus_mech.swf,assets/thumbs/1279_black_brutus_mech.jpg,Y,Y
1280,2-Head Frostfire Dragon,u,7,7,80,1280_frost_fire_dragon,assets/sprites/1280_frost_fire_dragon.swf,assets/thumbs/1280_frost_fire_dragon.jpg,Y,Y
1281,Silver Gunner Elf,u,7,7,80,1281_silver_elf_gunner,assets/sprites/1281_silver_elf_gunner.swf,assets/thumbs/1281_silver_elf_gunner.jpg,Y,Y
1282,Dino Rider Elf,u,7,7,80,1282_elf_dino_rider,assets/sprites/1282_elf_dino_rider.swf,assets/thumbs/1282_elf_dino_rider.jpg,Y,Y
1283,2-Head Frostfire Draggy,u,7,7,83,1283_frost_fire_draggy,assets/sprites/1283_frost_fire_draggy.swf,assets/thumbs/1283_frost_fire_draggy.jpg,Y,Y
1284,Watcher Hero,u,7,7,80,1284_cyclop_soldier,assets/sprites/1284_cyclop_soldier.swf,assets/thumbs/1284_cyclop_soldier.jpg,Y,Y
1285,Siege Striker,u,7,7,83,1285_plasma_striker,assets/sprites/1285_plasma_striker.swf,assets/thumbs/1285_plasma_striker.jpg,Y,Y
1286,Avenger Mech Drone,u,7,7,83,1286_avenger_mech_draggy,assets/sprites/1286_avenger_mech_draggy.swf,assets/thumbs/1286_avenger_mech_draggy.jpg,Y,Y
1287,Avenger Mech ,u,7,7,80,1287_avenger_mech,assets/sprites/1287_avenger_mech.swf,assets/thumbs/1287_avenger_mech.jpg,Y,Y
1288,Destruction Wizard,u,7,7,80,1288_destruction_wizard,assets/sprites/1288_destruction_wizard.swf,assets/thumbs/1288_destruction_wizard.jpg,Y,Y
1289,Executioner Mech Drone,u,7,7,83,1289_executioner_mech_draggy,assets/sprites/1289_executioner_mech_draggy.swf,assets/thumbs/1289_executioner_mech_draggy.jpg,Y,Y
1290,Executioner Mech ,u,7,7,80,1290_executioner_mech,assets/sprites/1290_executioner_mech.swf,assets/thumbs/1290_executioner_mech.jpg,Y,Y
1291,Winged Paladin,u,7,7,80,1291_winged_paladin,assets/sprites/1291_winged_paladin.swf,assets/thumbs/1291_winged_paladin.jpg,Y,Y
1292,Andromeda Private,u,7,7,80,1292_andromeda_private,assets/sprites/1292_andromeda_private.swf,assets/thumbs/1292_andromeda_private.jpg,Y,Y
1293,Godzilla Mech,u,7,7,80,1293_godzilla_mech,assets/sprites/1293_godzilla_mech.swf,assets/thumbs/1293_godzilla_mech.jpg,Y,Y
1294,Godzilla Mech Drone,u,7,7,83,1294_godzilla_mech_drone,assets/sprites/1294_godzilla_mech_drone.swf,assets/thumbs/1294_godzilla_mech_drone.jpg,Y,Y
1295,Andromeda Combat Droid,u,7,7,80,1295_andromeda_combat_droid,assets/sprites/1295_andromeda_combat_droid.swf,assets/thumbs/1295_andromeda_combat_droid.jpg,Y,Y
1296,Andromeda Spaceship,u,7,7,80,1296_andromeda_combat_spaceship,assets/sprites/1296_andromeda_combat_spaceship.swf,assets/thumbs/1296_andromeda_combat_spaceship.jpg,Y,Y
1297,King Kong Mech,u,7,7,80,1297_kingKongMech,assets/sprites/1297_kingKongMech.swf,assets/thumbs/1297_kingKongMech.jpg,Y,Y
1298,King Kong Drone,u,7,7,83,1298_kingKongDrone,assets/sprites/1298_kingKongDrone.swf,assets/thumbs/1298_kingKongDrone.jpg,Y,Y
1299,Gamera Mech,u,7,7,80,1299_gameraMech,assets/sprites/1299_gameraMech.swf,assets/thumbs/1299_gameraMech.jpg,Y,Y
1300,Gamera Drone,u,7,7,83,1300_gameraDrone,assets/sprites/1300_gameraDrone.swf,assets/thumbs/1300_gameraDrone.jpg,Y,Y
1301,Z Project Mech,u,7,7,80,1301_zProjectMech,assets/sprites/1301_zProjectMech.swf,assets/thumbs/1301_zProjectMech.jpg,Y,Y
1302,Z Project Drone,u,7,7,83,1302_zProjectDrone,assets/sprites/1302_zProjectDrone.swf,assets/thumbs/1302_zProjectDrone.jpg,Y,Y
1303,Massive Gunner Mech,u,7,7,80,1303_massiveGunnerMech,assets/sprites/1303_massiveGunnerMech.swf,assets/thumbs/1303_massiveGunnerMech.jpg,Y,Y
1304,Massive Gunner Drone,u,7,7,83,1304_massiveGunnerDrone,assets/sprites/1304_massiveGunnerDrone.swf,assets/thumbs/1304_massiveGunnerDrone.jpg,Y,Y
1305,Fire Godzilla Mech,u,7,7,80,1305_blackGodzilla_mech,assets/sprites/1305_blackGodzilla_mech.swf,assets/thumbs/1305_blackGodzilla_mech.jpg,Y,Y
1306,Fire Godzilla Drone,u,7,7,83,1306_blackGodzilla_drone,assets/sprites/1306_blackGodzilla_drone.swf,assets/thumbs/1306_blackGodzilla_drone.jpg,Y,Y
10000,Chained Bonus + Giant Walker,b,4,45,411,10000_chained_bonus_giant_walker,,,N,N
10001,Chained Bonus + Red Baron,b,4,45,411,10001_chained_bonus_red_barron,assets/sprites/10001_chained_bonus_red_barron.swf,assets/thumbs/10001_chained_bonus_red_barron.jpg,Y,Y
10002,Chained Steel Collector,b,4,45,411,10002_chained_junk_bot,assets/sprites/10002_chained_junk_bot.swf,assets/thumbs/10002_chained_junk_bot.jpg,Y,Y
10003,Chained Dual Blade Automech,b,4,45,411,10003_chained_dual_blade_automech,assets/sprites/10003_chained_dual_blade_automech.swf,assets/thumbs/10003_chained_dual_blade_automech.jpg,Y,Y
10004,Chained Black Belt Archer,b,4,45,411,10004_chained_transformer_archer,assets/sprites/10004_chained_transformer_archer.swf,assets/thumbs/10004_chained_transformer_archer.jpg,Y,Y
10005,Chained 30% Off,b,4,45,411,10005_chained_30_off,assets/sprites/10005_chained_30_off.swf,assets/thumbs/10005_chained_30_off.jpg,Y,Y
10006,Chained Great Shogun Mech,b,4,45,411,10006_chained_samurai_mech,assets/sprites/10006_chained_samurai_mech.swf,assets/thumbs/10006_chained_samurai_mech.jpg,Y,Y
10007,Chained ATP Mech,b,4,45,411,10007_chained_tetrapod_mech,assets/sprites/10007_chained_tetrapod_mech.swf,assets/thumbs/10007_chained_tetrapod_mech.jpg,Y,Y
10008,Chained Bonus + Electric Draggy,b,4,45,411,10008_chained_bonus_electric_draggy,assets/sprites/10008_chained_bonus_electric_draggy.swf,assets/thumbs/10008_chained_bonus_electric_draggy.jpg,Y,Y
10009,Chained Stealth Chest,b,4,45,411,10009_chained_stealth_chest,assets/sprites/10009_chained_stealth_chest.swf,assets/thumbs/10009_chained_stealth_chest.jpg,Y,Y
10010,Chained 35% Off,b,4,45,411,10010_chained_35_off,assets/sprites/10010_chained_35_off.swf,assets/thumbs/10010_chained_35_off.jpg,Y,Y
10011,Chained Cannon Mech,b,4,45,411,10011_chained_cannon_mech,assets/sprites/10011_chained_cannon_mech.swf,assets/thumbs/10011_chained_cannon_mech.jpg,Y,Y
10012,Chained Brutus Mech,b,4,45,411,10012_chained_brutus_mech,assets/sprites/10012_chained_brutus_mech.swf,assets/thumbs/10012_chained_brutus_mech.jpg,Y,Y
10013,Chained S.W.A.T. Soldier,b,4,45,411,10013_chained_caballero_zodiac,assets/sprites/10013_chained_caballero_zodiac.swf,assets/thumbs/10013_chained_caballero_zodiac.jpg,Y,Y
10014,Chained Bonus +  Ether Messiah Drone,b,4,45,411,10014_chained_bonus_ether_messiah_drone,assets/sprites/10014_chained_bonus_ether_messiah_drone.swf,assets/thumbs/10014_chained_bonus_ether_messiah_drone.jpg,Y,Y
10015,Chained Advanced Chest,b,4,45,411,10015_chained_advance_chest,assets/sprites/10015_chained_advance_chest.swf,assets/thumbs/10015_chained_advance_chest.jpg,Y,Y
10016,Chained 60% Off,b,4,45,411,10016_chained_60_off,assets/sprites/10016_chained_60_off.swf,assets/thumbs/10016_chained_60_off.jpg,Y,Y
10017,Chained Liquid Mech,b,4,45,411,10017_chained_liquid_mech,assets/sprites/10017_chained_liquid_mech.swf,assets/thumbs/10017_chained_liquid_mech.jpg,Y,Y
10018,Chained Killer Driller,b,4,45,411,10018_chained_drill,assets/sprites/10018_chained_drill.swf,assets/thumbs/10018_chained_drill.jpg,Y,Y
10019,Chained Doctor Shock,b,4,45,411,10019_chained_doctor_shock,assets/sprites/10019_chained_doctor_shock.swf,assets/thumbs/10019_chained_doctor_shock.jpg,Y,Y
10020,Play Social Empires,b,4,45,411,10020_cross_se,assets/sprites/10020_cross_se.swf,assets/thumbs/10020_cross_se.jpg,Y,Y
10021,Chained Professional Chest,b,4,45,411,10021_chained_professional_pack,assets/sprites/10021_chained_professional_pack.swf,assets/thumbs/10021_chained_professional_pack.jpg,Y,Y
10022,Chained Red Mercury Dragon,b,4,45,411,10022_chained_dragon_metalic_red,assets/sprites/10022_chained_dragon_metalic_red.swf,assets/thumbs/10022_chained_dragon_metalic_red.jpg,Y,Y
10023,Chained 90% Bonus,b,4,45,411,10023_chained_90_bonus,assets/sprites/10023_chained_90_bonus.swf,assets/thumbs/10023_chained_90_bonus.jpg,Y,Y
10024,Chained Super Pack,b,4,45,411,10024_chained_super_pack,assets/sprites/10024_chained_super_pack.swf,assets/thumbs/10024_chained_super_pack.jpg,Y,Y
10025,Chained Cyber Samurai Mech,b,4,45,411,10025_chained_cyber_samurai_mech,assets/sprites/10025_chained_cyber_samurai_mech.swf,assets/thumbs/10025_chained_cyber_samurai_mech.jpg,Y,Y
10026,Chained 2-Gun Exobot,b,4,45,411,10026_chained_2_gun_exobot,assets/sprites/10026_chained_2_gun_exobot.swf,assets/thumbs/10026_chained_2_gun_exobot.jpg,Y,Y
10027,Chained Dark Ether Messiah,b,4,45,411,10027_chained_darck_ether_messiah,assets/sprites/10027_chained_darck_ether_messiah.swf,assets/thumbs/10027_chained_darck_ether_messiah.jpg,Y,Y
10028,Chained 95% Bonus,b,4,45,411,10028_chained_95_bonus,assets/sprites/10028_chained_95_bonus.swf,assets/thumbs/10028_chained_95_bonus.jpg,Y,Y
10029,Chained Attack Pack,b,4,45,411,10029_chained_attack_pack,assets/sprites/10029_chained_attack_pack.swf,assets/thumbs/10029_chained_attack_pack.jpg,Y,Y
10030,Chained Forge Dragon,b,4,45,411,10030_chained_forge_dragon,assets/sprites/10030_chained_forge_dragon.swf,assets/thumbs/10030_chained_forge_dragon.jpg,Y,Y
10031,Chained Converter Wizard,b,4,45,411,10031_chained_enemy_converter,assets/sprites/10031_chained_enemy_converter.swf,assets/thumbs/10031_chained_enemy_converter.jpg,Y,Y
10032,Chained Bonus + Red Mercury Draggy,b,4,45,411,10032_chained_bonus_red_mercury_draggy,assets/sprites/10032_chained_bonus_red_mercury_draggy.swf,assets/thumbs/10032_chained_bonus_red_mercury_draggy.jpg,Y,Y
10033,Chained Swamp Monster,b,4,45,411,10033_chained_nebula_monster,assets/sprites/10033_chained_nebula_monster.swf,assets/thumbs/10033_chained_nebula_monster.jpg,Y,Y
10034,Chained Hercules Mech,b,4,45,411,10034_chained_hercules_mech,,,N,N
10035,Chained Double Cannon Mech,b,4,45,411,10035_chained_double_cannon_mech,assets/sprites/10035_chained_double_cannon_mech.swf,assets/thumbs/10035_chained_double_cannon_mech.jpg,Y,Y
10036,Chained Laser Blade Automech,b,4,45,411,10036_chained_laser_blade_automech,assets/sprites/10036_chained_laser_blade_automech.swf,assets/thumbs/10036_chained_laser_blade_automech.jpg,Y,Y
10037,Chained Burning Slayer,b,4,45,411,10037_chained_red_slayer,assets/sprites/10037_chained_red_slayer.swf,assets/thumbs/10037_chained_red_slayer.jpg,Y,Y
10038,Chained Karateka Gunner,b,4,45,411,10038_chained_karateka_gunner,assets/sprites/10038_chained_karateka_gunner.swf,assets/thumbs/10038_chained_karateka_gunner.jpg,Y,Y
10039,Chained Demolition Pack,b,4,45,411,10039_chained_demolition_pack,assets/sprites/10039_chained_demolition_pack.swf,assets/thumbs/10039_chained_demolition_pack.jpg,Y,Y
10040,Chained Half Price Party Weekend,b,4,45,411,10040_chained_half_party_price_party_weekend,assets/sprites/10040_chained_half_party_price_party_weekend.swf,,Y,N
10041,Chained Prime Automech,b,4,45,411,10041_chained_optimus_prime,assets/sprites/10041_chained_optimus_prime.swf,assets/thumbs/10041_chained_optimus_prime.jpg,Y,Y
10042,Chained Revolution Bonus 99,b,4,45,411,10042_chained_revolution_bonus_99,assets/sprites/10042_chained_revolution_bonus_99.swf,assets/thumbs/10042_chained_revolution_bonus_99.jpg,Y,Y
10043,Chained Retaliator Pack,b,4,45,411,10043_chained_retaliator_pack,assets/sprites/10043_chained_retaliator_pack.swf,assets/thumbs/10043_chained_retaliator_pack.jpg,Y,Y
10044,Chained Big Razor Mech,b,4,45,411,10044_chained_big_razor_mech,assets/sprites/10044_chained_big_razor_mech.swf,assets/thumbs/10044_chained_big_razor_mech.jpg,Y,Y
10045,Chained 150% Extra Cash,b,4,45,411,10045_chained_150_extra_cash,assets/sprites/10045_chained_150_extra_cash.swf,assets/thumbs/10045_chained_150_extra_cash.jpg,Y,Y
10046,Chained 40% Off,b,4,45,411,10046_chained_40_off,assets/sprites/10046_chained_40_off.swf,assets/thumbs/10046_chained_40_off.jpg,Y,Y
10047,Chained Destruction Pack,b,4,45,411,10047_chained_destruction_pack,assets/sprites/10047_chained_destruction_pack.swf,assets/thumbs/10047_chained_destruction_pack.jpg,Y,Y
10048,Play Dragon City,b,4,45,411,10048_cross_dc,,,N,N
10049,Chained Dark Ether Messiah + Dual Blade Automech ,b,4,45,411,10049_chained_dark_ether_messiah_dual_blade_automech,assets/sprites/10049_chained_dark_ether_messiah_dual_blade_automech.swf,assets/thumbs/10049_chained_dark_ether_messiah_dual_blade_automech.jpg,Y,Y
10050,Chained Spartan Warrior,b,4,45,411,10050_chained_spartan_warrior,assets/sprites/10050_chained_spartan_warrior.swf,assets/thumbs/10050_chained_spartan_warrior.jpg,Y,Y
10051,Chained Assault Pack,b,4,45,411,10051_chained_assault_pack,assets/sprites/10051_chained_assault_pack.swf,assets/thumbs/10051_chained_assault_pack.jpg,Y,Y
10052,Chained Proto Winged Mech,b,4,45,411,10052_chained_widged_transformer,assets/sprites/10052_chained_widged_transformer.swf,assets/thumbs/10052_chained_widged_transformer.jpg,Y,Y
10053,Chained Spider Bot,b,4,45,411,10053_chained_spider_bot,assets/sprites/10053_chained_spider_bot.swf,assets/thumbs/10053_chained_spider_bot.jpg,Y,Y
10054,Chained 100% Bonus + Draggy,b,4,45,411,10054_100_bonus_draggy,assets/sprites/10054_100_bonus_draggy.swf,assets/thumbs/10054_100_bonus_draggy.jpg,Y,Y
10055,Chained Ambush Chest,b,4,45,411,10055_chained_ambush_chest,assets/sprites/10055_chained_ambush_chest.swf,assets/thumbs/10055_chained_ambush_chest.jpg,Y,Y
10056,Chained Pharaoh Warrior Mech ,b,4,45,411,10056_chained_egyptian_warrior_mech,assets/sprites/10056_chained_egyptian_warrior_mech.swf,assets/thumbs/10056_chained_egyptian_warrior_mech.jpg,Y,Y
10057,Chained Arachnid Mech,b,4,45,411,10057_chained_transformer_aracnid,assets/sprites/10057_chained_transformer_aracnid.swf,assets/thumbs/10057_chained_transformer_aracnid.jpg,Y,Y
10058,Chained 95% Bonus Cash + Fire Karateka,b,4,45,411,10058_chained_95bonus_fire_karateka,assets/sprites/10058_chained_95bonus_fire_karateka.swf,assets/thumbs/10058_chained_95bonus_fire_karateka.jpg,Y,Y
10059,Chained 35% Bonus Cash + Blue Steel Draggy,b,4,45,411,10059_chained_35bonus_blue_steel_draggy,assets/sprites/10059_chained_35bonus_blue_steel_draggy.swf,assets/thumbs/10059_chained_35bonus_blue_steel_draggy.jpg,Y,Y
10060,Chained Storm Pack,b,4,45,411,10060_chained_storm_pack,assets/sprites/10060_chained_storm_pack.swf,assets/thumbs/10060_chained_storm_pack.jpg,Y,Y
10061,Chained Black Brutus Mech,b,4,45,411,10061_chained_black_brutus_mech,assets/sprites/10061_chained_black_brutus_mech.swf,assets/thumbs/10061_chained_black_brutus_mech.jpg,Y,Y
10062,Chained 2-Head Frostfire Dragon,b,4,45,411,10062_chained_2head_frostfire_dragon,assets/sprites/10062_chained_2head_frostfire_dragon.swf,assets/thumbs/10062_chained_2head_frostfire_dragon.jpg,Y,Y
10063,Chained Multi Morpher,b,4,45,411,10063_chained_multi_morph,assets/sprites/10063_chained_multi_morph.swf,assets/thumbs/10063_chained_multi_morph.jpg,Y,Y
10064,Chained Watcher Hero,b,4,45,411,10064_chained_cyclop_soldier,assets/sprites/10064_chained_cyclop_soldier.swf,assets/thumbs/10064_chained_cyclop_soldier.jpg,Y,Y
10065,Chained Combat Chest,b,4,45,411,10065_chained_combat_chest,assets/sprites/10065_chained_combat_chest.swf,assets/thumbs/10065_chained_combat_chest.jpg,Y,Y
10066,Chained Avenger Mech,b,4,45,411,10066_chained_avenger_mech,assets/sprites/10066_chained_avenger_mech.swf,assets/thumbs/10066_chained_avenger_mech.jpg,Y,Y
10067,Chained 60% OFF + Electric Draggy,b,4,45,411,10067_chained_60off_electric_draggy,assets/sprites/10067_chained_60off_electric_draggy.swf,assets/thumbs/10067_chained_60off_electric_draggy.jpg,Y,Y
10068,Chained 125% Bonus + Dark Ether Drone,b,4,45,411,10068_chained_125off_dark_messiah_drone,assets/sprites/10068_chained_125off_dark_messiah_drone.swf,assets/thumbs/10068_chained_125off_dark_messiah_drone.jpg,Y,Y
10069,Chained Golden Slayer + M. Cannon Mech,b,4,45,411,10069_chained_goldenslayer_cannonmech,assets/sprites/10069_chained_goldenslayer_cannonmech.swf,assets/thumbs/10069_chained_goldenslayer_cannonmech.jpg,Y,Y
10070,Chained 75% Bonus,b,4,45,411,10070_chained_75bonus,assets/sprites/10070_chained_75bonus.swf,assets/thumbs/10070_chained_75bonus.jpg,Y,Y
10071,Chained Executioner Mech,b,4,45,411,10071_chained_executioner_mech,assets/sprites/10071_chained_executioner_mech.swf,assets/thumbs/10071_chained_executioner_mech.jpg,Y,Y
10072,Chained Battle Chest,b,4,45,411,10072_chained_battle_chest,assets/sprites/10072_chained_battle_chest.swf,assets/thumbs/10072_chained_battle_chest.jpg,Y,Y
10073,Chained 125% Extra Cash,b,4,45,411,10073_chained_125_extra_cash,assets/sprites/10073_chained_125_extra_cash.swf,assets/thumbs/10073_chained_125_extra_cash.jpg,Y,Y
10074,Chained Killer Chest,b,4,45,411,10074_chained_killer_chest,assets/sprites/10074_chained_killer_chest.swf,assets/thumbs/10074_chained_killer_chest.jpg,Y,Y
10075,Chained Godzilla Mech,b,4,45,411,10075_chained_godzillaMech,assets/sprites/10075_chained_godzillaMech.swf,assets/thumbs/10075_chained_godzillaMech.jpg,Y,Y
10076,Chained 110% Bonus,b,4,45,411,10076_chained_110Bonus,assets/sprites/10076_chained_110Bonus.swf,assets/thumbs/10076_chained_110Bonus.jpg,Y,Y
10077,Chained King Kong Mech,b,4,45,411,10077_chained_kingKongMech,assets/sprites/10077_chained_kingKongMech.swf,assets/thumbs/10077_chained_kingKongMech.jpg,Y,Y
10078,Dragon City,b,4,45,411,10078_dragonCity_cross,assets/sprites/10078_dragonCity_cross.swf,assets/thumbs/10078_dragonCity_cross.jpg,Y,Y
10079,Chained Power Bot Chest,b,4,45,411,10079_chained_powerBotChest,assets/sprites/10079_chained_powerBotChest.swf,assets/thumbs/10079_chained_powerBotChest.jpg,Y,Y
10080,Chained Dark Ether M. + Laser B. Automech,b,4,45,411,10080_chained_darkEtherM_LaserBAutomech,assets/sprites/10080_chained_darkEtherM_LaserBAutomech.swf,assets/thumbs/10080_chained_darkEtherM_LaserBAutomech.jpg,Y,Y
10081,Chained Gamera Mech,b,4,45,411,10081_chained_gameraMech,assets/sprites/10081_chained_gameraMech.swf,assets/thumbs/10081_chained_gameraMech.jpg,Y,Y
10082,Chained Mecha Dragons Chest,b,4,45,411,10082_chained_mechaDragonsChest,assets/sprites/10082_chained_mechaDragonsChest.swf,assets/thumbs/10082_chained_mechaDragonsChest.jpg,Y,Y
10083,Chained Double Cannon M. + Big Razor M.,b,4,45,411,10083_chained_doubleCannonM_bigRazorM,assets/sprites/10083_chained_doubleCannonM_bigRazorM.swf,assets/thumbs/10083_chained_doubleCannonM_bigRazorM.jpg,Y,Y
10084,Chained 60% Bonus,b,4,45,411,10084_chained_60bonus,assets/sprites/10084_chained_60bonus.swf,assets/thumbs/10084_chained_60bonus.jpg,Y,Y
10085,Chained Z Project Mech,b,4,45,411,10085_chained_zProjectMech,assets/sprites/10085_chained_zProjectMech.swf,assets/thumbs/10085_chained_zProjectMech.jpg,Y,Y
10086,Chained Full Metal Chest,b,4,45,411,10086_chained_fullMetalChest,assets/sprites/10086_chained_fullMetalChest.swf,assets/thumbs/10086_chained_fullMetalChest.jpg,Y,Y
10087,Chained Great Shogun Mech + Brutus Mech,b,4,45,411,10087_chained_greatShogunMech_brutusMech,assets/sprites/10087_chained_greatShogunMech_brutusMech.swf,assets/thumbs/10087_chained_greatShogunMech_brutusMech.jpg,Y,Y
10088,Chained Massive Gunner Mech,b,4,45,411,10088_chained_massiveGunnerMech,assets/sprites/10088_chained_massiveGunnerMech.swf,assets/thumbs/10088_chained_massiveGunnerMech.jpg,Y,Y
10089,"Chained x2,5 Cash Offer",b,4,45,411,10089_chained_x2_5CashOffer,assets/sprites/10089_chained_x2_5CashOffer.swf,assets/thumbs/10089_chained_x2_5CashOffer.jpg,Y,Y
10090,Chained Fire Godzilla Mech,b,4,45,411,10090_chained_fireGodzillaMech,assets/sprites/10090_chained_fireGodzillaMech.swf,assets/thumbs/10090_chained_fireGodzillaMech.jpg,Y,Y
```
