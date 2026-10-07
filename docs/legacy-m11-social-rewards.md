# M11 line 4 - `social rewards`: legacy measurement contract

Committed before any proposal, on its own branch `docs/legacy-m11-social-rewards`,
so that the change which follows is bounded by measurement rather than by the
deliver item's name.

**Deliver item under investigation:** `social rewards`, the fourth of M11's six
items (`friends`, `visits`, `scores`, `social rewards`, `legacy event systems`,
`special mechanics`).

**The standing classification is falsified.** `docs/legacy-m11-social.md` §3
and §7, and the roadmap's `Next eligible objective` bullet, all classify this
item as *content committed, behaviour absent* on the strength of three tables
with zero consumers. That measurement is **reproduced** (§4 below), and it is
**true of the tables**. It is **false of the deliver item**, because the
preserved server contains a social-assistance state machine that is persisted,
written, dispatched from three branches, and recorded in the committed corpus -
and none of it is in those three tables.

---

## 0. Instrument faults committed by this investigation

Recorded before the findings, because every one of them produced a wrong
number first. This is the standing convention in this project.

1. **A string-vs-int comparison produced a false negative.** The normalized
   package stores `properties` flag values as **strings**, so
   `friend_assistable` is the string `'1'`. An early probe tested
   `isinstance(v, (int, float)) and v > 0`, which is **false for every carrier**,
   and reported `0` overlaps between `attr["si"]` and `friend_assistable`. The
   corrected figure is **51 of 53** (§6). This is the identical trap
   `godot-unit-movement` recorded, where `int(value or 0)` collapses the
   committed `"0"` to `true`; the coercer must be `int()`, and `int("0")` is
   verified `0` by probe.
2. **A `repr`-keyed counter cannot distinguish `1` from `'1'`.** `repr(1)` is the
   *string* `'1'`, so an earlier distribution count reported every committed
   value as a string. Re-measured against the parsed JSON objects: `giftable`
   and `gift_level` are **`int`** on all 470 buildings, all 429 units and the
   1 special, while `friend_assistable` is **`str`**. Both facts are load-bearing
   and both are recorded in §7.
3. **The first corpus scan walked a glob, not the canonical allow-list.** It read
   `tests/saves/*.json` plus `villages/*.json` - **11** paths, including
   `tests/saves/manifest.json`, which is a manifest of saves and not a save. The
   authoritative definition is an explicit **allow-list of 10 documents** in
   `apps/client-godot/scripts/units/magic_flow.gd:554-566`, with its exclusions
   recorded at `:570-580` and the reason they exist: *"a naive walk reported 33
   documents and 13,034 rows because it recursed into the fixture step documents
   and into a Godot build cache"*. Every figure in this document is re-measured
   over that allow-list. The placed-row total came out at **3,372**, identical
   to `magic_flow.gd:588`'s `PLACED_ROWS_RECORDED`, so the earlier walk's
   **row** figure was unaffected - only its **document** denominator was wrong.
4. **A table's row count was read as its item count.** The first pass reported
   `social_items` as **26** entries and computed `worker_cost`'s distribution
   over those 26 rows. Re-measuring per id showed **13 distinct ids, each
   appearing twice at a fixed `+3000` offset**, with `worker_cost` identical in
   both blocks - so the distribution was one 13-item table counted twice, and
   `{1: 2, 2: 20, 3: 4}` is not a 26-item distribution (§8). The fault survived
   a first draft of §8 that was about to be committed. **The general hazard:**
   a normalized package preserves one row per *stored config entry*, and two
   stored entries may be the same logical item; only a per-id distinct count
   distinguishes them. The same pass also found `neighbor_assists` has **no `id`
   key at all**, so a check asserting an `id` field raised `KeyError` and the
   identity field is `legacy_id`.

---

## 1. Denominators (settled, reproduced)

| Denominator | Value | Source |
|---|---|---|
| Top-level legacy modules walked | **11** | `auctions.py`, `bundle.py`, `command.py`, `constants.py`, `engine.py`, `get_game_config.py`, `get_player_info.py`, `legacy_command_recorder.py`, `server.py`, `sessions.py`, `version.py` |
| Counting rules applied | **6** | whole-file occurrences; whole-file distinct lines; code-only occurrences (comments and string literals stripped by a two-state lexer); code-only distinct lines; exact word-boundary identifier token; quoted-access form |
| Named `command.py` dispatcher branches | **63** | re-measured from `if cmd == "..."` / `elif cmd == "..."` |
| Committed save documents | **10** | explicit allow-list, `magic_flow.gd:554-566` |
| Placed rows in that corpus | **3,372** | `magic_flow.gd:588`, reproduced |
| Committed item definitions | **470 buildings + 429 units + 1 special** | `packages/game-content/normalized/` |
| Committed social content entries | **41 rows** = `social_items` **26 rows / 13 items**, `findable_items` **10**, `neighbor_assists` **5** | `packages/game-content/normalized/` |
| Compatibility routes | **24**, all in `compat_service.py` | none assist-shaped |
| Delivered client `.gd` sources scanned | **119** | `apps/client-godot/scripts` + `apps/client-godot/tests` |

---

## 2. Finding A - the deliver item's name is the *inverse* of what the server has

Six of the 63 branch names touch a reward-, assist-, coin-, worker-, social-,
trade-, help-, ally- or neighbour-shaped term. Measured:

| Line | Branch | Terms matched |
|---|---|---|
| `command.py:345` | `weekly_reward` | reward |
| `command.py:444` | `win_daily_bonus` | bonus, daily |
| `command.py:465` | `trade_resource` | trade |
| `command.py:549` | `buy_si_help` | help |
| `command.py:586` | `darts_new_free` | free |
| `command.py:637` | `set_resource_allies` | allie |

Of these, **four are already owned elsewhere** and are not this line's business:
`weekly_reward` by `godot-rewards` (M10 line 4, which delivers the
`MONDAY_BONUS_REWARDS` cursors); `trade_resource` and `set_resource_allies` by
`godot-social-state` (M11 line 1, which records `set_resource_allies` verbatim
in `social_state.gd:270-283` and both written trade fields in `:290-296`);
`darts_new_free` by `godot-darts` (M11 line 2).

`win_daily_bonus` (`command.py:444-463`) is **not social** and is **not owned**.
It advances a 5-id cursor from **client-sent** `args[1]`, and when
`args[0] > 0` it grants a **client-sent** item id into storage
(`bought_unit_add` + `add_store_item`). It is the daily-bonus shape of
`godot-rewards`, not a social reward, and it is recorded here so that a later
line does not mistake it for one. **No claim is made about it in this document
beyond those four lines.**

That leaves **`buy_si_help`**, and it is the whole of the unowned social-reward
surface.

---

## 3. Finding B - `si` means "Socially In Construction", and the author's own comment says so

The token `si` is unmeasurable as a raw substring: it measures **150** whole-file
occurrences over **126** distinct lines across **8** of the 11 modules, because
it sits inside `using`, `version`, `revision`, `signature`, `sessionid` and
`buy_si_help` itself. Every figure below therefore uses the word-boundary
token rule, and the raw figure is reported only to show why the rule is required.

**Word-boundary `si`: 6 occurrences, 6 distinct lines, all in `engine.py`** -
`:24`, `:139`, `:140`, `:142`, `:146`, `:147` - across three functions.

```python
# engine.py:18-24, inside map_add_item, guarded by `if player == 1:` at :15
properties = get_attribute_from_item_id(item, "properties")
# enable SI (Socially In Construction), because the game expects it
if properties:
    properties = json.loads(properties)
    if "friend_assistable" in properties:
        if int(properties["friend_assistable"]) > 0:
            attr["si"] = []
```

**The expansion is not inferred.** `engine.py:19` states it verbatim, and the
comment continues *"because the game expects it"* - an admission that this is a
client-display concession, not gameplay.

```python
# engine.py:137-147
def buy_si_help(item: dict):
    attr = item[6]
    if "si" not in attr:
        attr["si"] = [ 0 ]
        return
    attr["si"].append(0) # 0 is for buying instead of hiring friends

def finish_si(item: dict):
    attr = item[6]
    if "si" in attr:
        del attr["si"]
```

**The second comment is the finding.** `engine.py:142` says the appended `0`
means *"buying instead of hiring friends"*. So the list on a row records, per
assist slot, **who filled it** - and the only writer ever fills it with the
**paid** arm. The list is a **record of a paid substitute for a friend**, which
is the opposite of a social reward and the reason this deliver item is not what
its name suggests.

---

## 4. Finding C - the three tables really do have zero consumers (reproduced, not inherited)

| Table | Entries | Whole-file occurrences | Whole-file distinct lines | Code-only occurrences | Code-only distinct lines | Word token | Quoted form |
|---|---|---|---|---|---|---|---|
| `neighbor_assists` | 5 | **0** | **0** | **0** | **0** | **0** | **0** |
| `findable_items` | 10 | **0** | **0** | **0** | **0** | **0** | **0** |
| `social_items` | 26 | **0** | **0** | **0** | **0** | **0** | **0** |

Also **0** across all six rules: `workers`, `worker_cost`.

The raw `config/main.json` key positions are re-confirmed at **`neighbor_assists`
`:44946`**, **`findable_items` `:45047`**, **`social_items` `:47262`**, matching
the citation in `docs/legacy-m11-social.md` §3. So that record is accurate and
is **not** corrected here.

**This reproduces, and does not alter, the standing record.** The falsification
in the header is narrower than it looks: the tables have zero consumers, *and*
there is a separate, larger, unowned surface they do not describe.

---

## 5. Finding D - three branches reach the helpers, and one of them is not named for them

```python
# command.py:549-559
elif cmd == "buy_si_help":
    index = args[0]
    item = map_get_item(map, index)
    if not item:
        print("Error: item not found.")
        return
    buy_si_help(item)
    print("Bought SI help for", str(get_name_from_item_id(item[0])))

# command.py:561-571
elif cmd == "finish_si":
    index = args[0]
    item = map_get_item(map, index)
    if not item:
        print("Error: item not found.")
        return
    finish_si(item)
    print("Finished SI for", str(get_name_from_item_id(item[0])))
```

**Third call site, reached by a differently-named branch:**

```python
# command.py:637-647
elif cmd == "set_resource_allies":
    resource = args[0]
    index = args[1]
    item = map_get_item(map, index)
    if item:
        item[3] = time_now
        finish_si(item)
    map["resourceAlliesMarket"] = resource
```

So `del attr["si"]` has **two** dispatchers, not one. `godot-social-state`
already records the `finish_si` call as one of the three effects of
`set_resource_allies` (`social_state.gd:275-279`) and states `reproduced: false`.
**The effect is owned; the mechanism is not.**

**Refusal shape, identical in both dedicated branches:** the only precondition is
that `map_get_item` returns non-`None`. There is **no `friend_assistable`
check**, **no type check**, and **no team check**. A client can therefore open an
assist list on **any** row, flagged or not - which is the most plausible
explanation for the corpus anomaly in §6, and is recorded as a candidate rather
than a conclusion because nothing in the preserved source performs it.

**Nothing is charged and nothing is granted.** `buy_si_help` performs no
`apply_resources` call and no `bought_unit_add`. `finish_si` only deletes a key.
The `print` lines are narration, exactly as `complete_goal`'s is (§10).

---

## 6. Finding E - the corpus: 53 rows, 7 elements, every one of them the integer `0`

Over the canonical 10-document allow-list:

| Document | Placed rows | Rows carrying `si` | Non-empty | Elements |
|---|---|---|---|---|
| `villages/AcidCaos.json` | 319 | **9** | 2 | **5** |
| `villages/General_Mike_30.json` | 436 | 0 | 0 | 0 |
| `villages/General_Mike_31.json` | 436 | 0 | 0 | 0 |
| `villages/Kiriakos.json` | 569 | **18** | 0 | 0 |
| `villages/Nerri.json` | 367 | **7** | 0 | 0 |
| `villages/Neutral.json` | 549 | **8** | 1 | **2** |
| `villages/Scarlet.json` | 576 | **11** | 0 | 0 |
| `villages/initial.json` | 40 | 0 | 0 | 0 |
| `tests/saves/fresh-player.json` | 40 | 0 | 0 | 0 |
| `tests/saves/fresh-player-pre-migration.json` | 40 | 0 | 0 | 0 |
| **Total** | **3,372** | **53** | **3** | **7** |

**Element census: `int:0` x 7. One distinct element value in the entire corpus.**
There is no non-zero element, no float, no string, no `null`, and no non-list
value. The whole attribute-bag key union is `["cp", "nu", "si", "ts", "ui",
"xp"]` - already declared as `magic_flow.gd:545`'s `ATTR_BAG_UNION`.

Every one of the 53 rows is on **player team 1**, which is consistent with the
`if player == 1:` guard at `engine.py:15`.

**The two non-empty rows are the only non-empty rows in the corpus:**

| Document | Slot | Item | Item name | `si` |
|---|---|---|---|---|
| `villages/AcidCaos.json` | 9275 | 75 | Recon center | `[0, 0]` |
| `villages/Neutral.json` | 40114 | 61 | Allies Building | `[0, 0]` |

(the third non-empty row, `villages/AcidCaos.json` slot 6888 item 9, carries
`[0, 0, 0]`.)

### Reconciliation against `friend_assistable`

`friend_assistable` is committed as the **string `'1'`** on **26 of 470
buildings** and **0 of 429 units**; the key is absent from the 1 special.
Its ids are `2-17`, `108`, `109`, `110`, `167`, `184`, `202`, `219`, `247`, `274`,
`296`. It has **2** whole-file, **2** code-only, **2** word-token and **2**
quoted occurrences across the 11 modules - all four in `engine.py:22-23` - so it
has exactly **one** consumer site, `engine.py:22-24`. It is **not** a
zero-consumer field.

| Reconciliation | Count |
|---|---|
| `si` rows whose item is `friend_assistable`-positive | **51 of 53** |
| `si` rows whose item is **not** `friend_assistable`-positive | **2** (items 61 and 75, both **non-empty** `[0, 0]`) |
| `friend_assistable`-positive ids never placed in the corpus | **8 of 26** (`5`, `167`, `184`, `202`, `219`, `247`, `274`, `296`) |
| `friend_assistable`-positive ids placed but carrying **no** `si` row | **2** (id 4 "Steel Factory I", 1 row; id 12 "Steel Factory III", 3 rows) |

**Three facts here are not resolved, and are recorded as gaps rather than
explained:**

1. Both non-flagged carriers carry the *same* `content_version` as a genuine
   carrier, so the flag was not added later. `buy_si_help`'s absent flag check
   (§5) would produce exactly `[0, 0]` on such a row after two appends, which is
   a candidate explanation and **not** a measurement.
2. Two flagged ids are placed with no `si` at all.
3. Several flagged ids carry fewer `si` rows than placed rows, which the current
   gate could not produce. `engine.map_add_item_from_item`
   (`engine.py:33-34`) bypasses the gate entirely and is a second candidate.

The honest claim is the narrow one: **`attr["si"]`'s presence does not reliably
indicate `friend_assistable`**, and the corpus proves it in both directions.

---

## 7. Finding F - two more committed fields with zero legacy consumers

| Field | Committed on | Distribution | Legacy consumers (6 rules x 11 modules) |
|---|---|---|---|
| `giftable` | **470 buildings + 429 units + 1 special**, `int` | `1` on **20 buildings** and **10 units**; `0` on the remaining **879** | **0 / 0 / 0 / 0 / 0 / 0** |
| `gift_level` | **470 buildings + 429 units + 1 special**, `int` | buildings: `0`x43, `1`x398, `2`x2, `3`x8, `4`x2, `5`x2, `6`x1, `7`x1, `8`x6, `9`x6, `10`x1 &nbsp;&nbsp; units: `0`x2, `1`x138, `4`x282, `10`x1, `18`x3, `20`x1, `30`x1, `40`x1 | **0 / 0 / 0 / 0 / 0 / 0** |

**No ordinal position is claimed for these two.** Earlier lines named
successive discoveries "the sixth", "the seventh", "the ninth", "the tenth" and
so on, but those counts were taken over **different scopes** - some over the
whole unit field set, some over behavioural fields only, some over map rows -
and no single reconciled census of zero-consumer committed fields exists in this
repository. Assigning a number here would repeat the defect M8 line 8 was
corrected for, where prose said "twenty of twenty-two" while naming twenty-one.
What is measured is the fact itself: **two more committed fields have zero
legacy consumers.** The other recorded instances, listed only so a later line can
see the overlap and avoid double-counting, are `unit_capacity`,
`training_time`, `velocity`, `max_frame`, `unlockedQuestIndex`,
`reward_type`/`reward_amount`, `completed_tutorial`, and the combat and
behavioural `properties` flags.

**`gift_level` is already recorded, for units only.** `unit_behaviors.gd:355`
carries `{"field": "gift_level", "legacy_reads": 0, "unit_distinct": 8}` in that
capability's zero-consumer census, and `test_unit_definitions.gd:822` lists both
field names in the unit field inventory. **`giftable` is in no census at all** -
`godot-unit-behaviors` recorded `gift_level` and did not record `giftable`, and
no other delivered module mentions either. That omission is a real gap in a
delivered artifact, not a fact about the legacy server.

**`gift_level` is a gifting threshold with real structure** - buildings span
`0..10` and units span `0..40`, and the committed names include "Recruitment
Prize" (140, level 1), "Gift Level" decorations, "Victory Arch" (105, level 7),
"Robo flag" (152, level 8), "Robo statue" (153, level 9) - so it is not a
constant. **No reader exists, no rule is derivable, and none is invented here.**
`godot-social-state`'s `ABSENT_HELPERS` entry `gift_to` states *"no gift command
exists"*, which **remains true**: no branch among the 63 is named for a gift.
That reason text is now incomplete rather than wrong - the fields exist and are
read by nothing - and completing it belongs to a line that owns the field.

---

## 8. Finding G - the committed reward schedule is uniform, so it carries no variation

| Table | Field | Committed values | Distinct |
|---|---|---|---|
| `neighbor_assists` (5 rows) | `reward` | `{"cash": 0, "coins": 50, "xp": 15}` on **all 5** - all three keys `int` | **1 object of 5** |
| `findable_items` (10 rows) | `coins` | `100` on **all 10**, `int` | **1 value of 10** |
| `social_items` (**13 items**, 26 rows) | `worker_cost` | `int`, values `{1, 2, 3}` - `1` x1, `2` x10, `3` x2 | 3 of 13 |
| `social_items` (**13 items**, 26 rows) | `workers` | `str` on every row (display names, e.g. `"Oil QA Supervisor, Chemical"`) | **14 strings over 26 rows** |

**This is the load-bearing correction to the deliver item's framing.** The three
tables *do* carry reward amounts, and `neighbor_assists.reward` is the **only**
committed reward schedule in the social domain. But it is **uniform**: one
distinct reward object across all five entries. So even a reader would have
exactly one number to give, and the table's five distinct rows differ only in
their `task`, `action` and `notification` display strings - **5** distinct
values each - with `rnd` `0` on all five.

**`social_items` holds 13 items, not 26.** Every id appears **twice**, at a
**fixed `+3000` offset** with no exceptions:

- low block: `3, 9, 12, 16, 28, 37, 44, 54, 61, 64, 74, 75, 140`
- high block: `3003, 3009, 3012, 3016, 3028, 3037, 3044, 3054, 3061, 3064, 3074, 3075, 3140`

The offset set is exactly `{3000}` across all **13** pairs. `worker_cost` is
**identical** in both blocks, so every distinct-cost figure above is a figure
over **13** items - the earlier `{1: 2, 2: 20, 3: 4}` over 26 rows is the same
table counted twice and is **not** a 26-item distribution. **`workers` differs on
2 of the 13 pairs**, which is the only place the duplication carries information:

| id | low-block `workers` | high-block `workers` |
|---|---|---|
| 64 | `Mechanic,Mechanic` | `Mechanic, Mechanic Assistant` |
| 74 | `Friend,Friend,Friend,Friend,Friend,Friend,Friend,Friend` | `Ally I, Ally II, Ally III, Ally IV, Ally V, Ally VI, Ally VII, Ally VIII, Ally IX` |

`description` is `""` on all **26** rows. **What the `+3000` block means is not
established** - no legacy branch reads the table at all, so there is no consumer
whose two-block handling could be observed. The duplication is recorded as a
committed-content fact and **not** interpreted as a second schedule.

**The three tables carry two different id spaces, and only one of them is an
item id.** `social_items.legacy_id` is an **item id** for the **13** low ids -
`legacy_id` 3 is `Oil QA Supervisor, Chemical` while item 3 is `Oil Factory I` -
and the **13** high ids resolve to **no** committed building or unit. By
contrast `findable_items` ids are `1..10` and `neighbor_assists` carries no `id`
key at all: its identity is a `position` of `0..4`, and **`position` equals
`legacy_id` on all five rows**, so that id space is table-local and sequential.
`findable_items` is the only one of the three whose `id` and `legacy_id` are
both present and equal. **Intersecting `findable_items` or
`neighbor_assists` ids with building ids would be a category error** and is
explicitly not done, even though **10 of 10** and **4 of 5** of those ids do
happen to resolve to committed items - coincidence, not a reference.

The `si`-carrying ids are
`{2, 3, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 61, 75, 108, 109, 110}`; **16**
of them are `friend_assistable`-positive and **10** are among `social_items`' 13
low ids, which includes **61** and **75** - the two `si` carriers that lack
`friend_assistable` (§6). **No relationship is claimed from either figure** -
both id spaces overlap by construction, and reading a rule into the overlap
would be exactly the invention this project refuses.

---

## 9. What is already delivered, and the exact ownership boundary

Measured site by site across the 119 delivered `.gd` sources. Every row is a
site, not a file, because several files mention a token only in a guard.

| Owned by | Site | What it owns |
|---|---|---|
| `godot-stored-item-placement` | `stored_item_flow.gd:117` `ATTR_ASSIST_KEY := "si"`; `:121` `ATTR_SOURCE`; `:127` `ATTR_FLAG_KEY`; `:567-577` | **The `attr` derivation itself**: `si` seeded `[]` from `properties.friend_assistable > 0`, `nc` from `clicks_to_build`. Its suite reports *"26 of 470 committed buildings carry a friend_assistable flag"* and *"0 of 429 committed units carry a friend_assistable flag at all"* (`test_stored_item_placement.gd:538,542`) - **both reproduced here**. |
| `godot-damage` | `magic_flow.gd:545` `ATTR_BAG_UNION`; `:554-566` `CANONICAL_CORPUS`; `:588` `PLACED_ROWS_RECORDED` | **The corpus definition** and the attribute-bag key union, including `si`. |
| `godot-town-rendering` | `town_state.gd:617-618` | `attr["si"]` **carried verbatim** in `Placement.attr`, *"never coerced, never dropped"*, with `nc` and `cp` validated. |
| `godot-social-state` | `social_state.gd:270-283` | The `set_resource_allies` effects **verbatim**, `reproduced: false`. `:405-465` `ABSENT_HELPERS` names `assist_reward`, `assist_task`, `assist_window`, `receive_assist`, `send_assist`, `social_reward`, `help_reward`, `gift_to` with measured reasons. `:83` records the three tables as owned by `social-tables-normalization`. |
| `godot-building-construction` | `town.gd:192-196` | Records *"the friend-assist cluster (`buy_si_help` / `finish_si`, the `attr["si"]` bag) are deliberately out of scope"*. |
| `godot-unit-animations` / `godot-unit-behaviors` | `unit_animations.gd:450`, `unit_behaviors.gd:279` | Both list `buy_si_help` and `finish_si` in `ABSENT_HELPERS` - they name them as helpers those modules must **never** provide. |
| `social-tables-normalization` | main spec | The three tables as committed content. |

**Measured absences.** `social_state.gd` contains **0** occurrences of
`friend_assistable` and **0** of `giftable` / `gift_level`. No compat module
holds an assist-shaped consumer: the 24 routes are none of them assist-shaped,
and the `si` / `finish_si` / `neighborAssists` hits in `apps/compat-api/**`
are all in `capture_*` fixture-capture helpers and `*_envelope.py` modules -
**never on the request path**. So no delivered capability projects the assist
**lifecycle**, the sentinel's meaning, the second delete path, or the absent
friend arm.

---

## 10. What this investigation does NOT establish

1. **No reward is granted, anywhere.** No branch pays `neighbor_assists.reward`,
   `findable_items.coins` or `social_items.worker_cost`. **No coin is charged**
   by `buy_si_help`.
2. **The friend arm's semantics are unknown.** That `0` means "bought" is the
   author's comment at `engine.py:142`; what a *friend* entry would contain is
   **not established**, because no writer exists. Any non-`0` decoding would be
   invention.
3. **The two corpus anomalies (§6) are unresolved.** Candidate explanations are
   recorded; neither is measured.
4. **`item[3]`'s role in `set_resource_allies` is not claimed.**
   `godot-social-state` records the stamp with no reader asserted, and this
   document adds none.
5. **No `si` row exists in the driven parity corpus.** `fresh-player.json`,
   `fresh-player-pre-migration.json` and `initial.json` carry **0** of 40 rows
   with `si`. An executed-legacy fixture is nonetheless **reachable**, because
   `buy_si_help` creates the key when absent - so unlike the refusal lines this
   is not a corpus limitation. Whether to spend a fixture capture on a command
   that grants nothing is a decision for the proposal, not for this document.
6. **`giftable` / `gift_level` semantics are unknown.** The names and the
   distributions are recorded; no threshold, no comparison, no rule.
7. **`win_daily_bonus` is not investigated here** beyond the four lines quoted in
   §2.
8. **Nothing here says what the Flash client displayed.** Every claim is about
   the preserved server and the committed corpus.

---

## 11. Recommended next step

Propose **M11 line 4** as a bounded line whose delivered surface is:

- a typed read-only projection of the **`attr["si"]` assist state** on a placed
  row - presence, list length, and each element's recorded type and value
  **verbatim** - failing closed on a non-object bag and on a non-list value, with
  the recorded slots travelling untouched beside the refusal;
- the **recorded transition table** for the three dispatchers, each effect
  quoted from source with its line, and `reproduced: false`;
- the **committed `friend_assistable` gate referenced, not reimplemented**, since
  `godot-stored-item-placement` owns the derivation;
- the **absence record**: no writer for any non-`0` element, no charge, no
  grant, no reward decoded, no eligibility window, and `giftable`/`gift_level`
  measured as zero-consumer with `giftable` newly recorded as a census gap in
  `godot-unit-behaviors`.

**Design D1 (recommended): no new route, no `apps/compat-api/**` change.**
`attr["si"]` is already carried on `/v0/bootstrap` - the town projection reads it
at `town_state.gd:333` straight off row slot 6 - so a read-only line needs no
endpoint, and the compat suite should stay at its **3077** baseline as a
*verified* figure, exactly as `godot-friends` did.

**Rejected alternative: a `/v0/assist` route exposing `buy_si_help` /
`finish_si`.** Recorded so the choice is not silent. Both branches mutate a
placed row, so a route would need a post-execution proof; but the transaction
**grants nothing and charges nothing**, the only appended value is a fixed `0`,
and `finish_si` is reachable through a second branch that also writes a
client-sent market resource. Building a mutation surface for a sentinel that
carries no observable consequence is a worse trade than recording the absence.
If a later line wants the route, `set_resource_allies` must be settled first,
because it is the branch with the real write.

---

## 12. Corrections to earlier records

1. **This document's own four instrument faults**, §0. Recorded here rather than
   fixed in place because the fault is the evidence that the guard is needed.
2. **`docs/legacy-m11-social.md` §3's `config/main.json` line citations are
   confirmed**, not corrected: `neighbor_assists` `:44946`, `findable_items`
   `:45047`, `social_items` `:47262`.
3. **`docs/legacy-m11-social.md` §3 and §7, and the roadmap's `Next eligible
   objective` bullet, classify `social rewards` as *content committed, behaviour
   absent*.** That classification is **falsified** and this branch records the
   correction in the roadmap's Project Status ledger rather than editing the
   superseded entries, per the standing rule that a progress ledger is never
   rewritten in place.
4. **`godot-unit-behaviors`'s zero-consumer census omits `giftable`** while
   recording `gift_level` (`unit_behaviors.gd:355`). Recorded as a gap in a
   delivered artifact, not as a fact about the legacy server.
5. **`godot-social-state`'s `ABSENT_HELPERS` reason for `gift_to`** reads *"no
   gift command exists"*, which is true, but no longer says that two committed
   gift fields exist and are read by nothing.
