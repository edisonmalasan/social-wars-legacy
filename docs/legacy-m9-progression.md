# M9 — Progression: legacy contract established by measurement

**Recorded 2026-10-02 by the root orchestrator, before any M9 proposal.**

M9's deliver list is `XP`, `levels`, `quests`, `research`, `collections`, `tutorial/progression`, and its
exit criterion is "Primary long-term progression systems work." Two of those six are already partly
delivered — `building-xp` (M7's eleventh line) delivered **XP and levels**, and `unit-collection` (M8
line 5) delivered **collections** as the project's first content-derived, server-authoritative unit
grant — so this record's first job was to establish what is genuinely undelivered.

**The headline finding is that M9 is not a refusal milestone. It is, by a wide margin, the richest in
the project, and in most places the only milestone whose mechanisms are all exercisable by the
committed corpus.** M8 established a pattern of three consecutive refusal-shaped lines, and this
record was written under the same caution that produced M8's line 8 — *measure, do not assume* — and
the pattern **does not hold**.

Every figure below is measured from the committed source by the scripts named in the last section,
not asserted.

---

## 1. The surface: 18 of 63 branches name a progression concept

The committed `command.py` dispatcher has **63** named branches. **Eighteen** of them name a
progression concept; **45** do not.

| Family | Branches | Delivered? |
| --- | --- | --- |
| Goals | `set_goals`, `complete_goal` | **no** |
| Quest state | `set_quest_var`, `end_quest`, `admin_set_quest_rank` | **no** |
| Chapters | `collect_mission` | **no** |
| Research | `next_research_step`, `research_buy_step_cash`, `next_research_item`, `reset_research_item` | **no** |
| XP | `level_up`, `add_xp_unit`, (`expand` matches on the substring `xp`) | `level_up` delivered by `building-xp`; `add_xp_unit` **no** |
| Collections | `complete_collection`, `unit_collections_completed`, (`collect`, `collect_mission`) | `complete_collection` delivered by `unit-collection`; `unit_collections_completed` **no** |
| Tutorial | `complete_tutorial` | **no** |
| Rewards | `weekly_reward` | **no** |

**Seven of M9's six deliver items have at least one entirely undelivered branch**, and `quests`,
`research`, and `tutorial/progression` have **none** delivered at all.

---

## 2. Research: four branches, no cost, no bounds, no gate, no completion

The clearest contract in M9, and the sharpest contrast with M8's refusals. Two parallel tracks, named
in the source as `0: TYPE_AREA_51` and `1: TYPE_ROBOTIC` (Area 51, Robotic Center):

| Branch | `command.py` | Effect |
| --- | --- | --- |
| `next_research_step(_type)` | 268–274 | `researchStepNumber[_type] += 1`; `timeStampDoResearch[_type] = time_now` |
| `research_buy_step_cash(cash, _type)` | 276–282 | `timeStampDoResearch[_type] = 0`; **`cash` read and never used** |
| `next_research_item(_type)` | 284–291 | `researchItemNumber[_type] += 1`; `researchStepNumber[_type] = 0`; `timeStampDoResearch[_type] = 0` |
| `reset_research_item(_type)` | 293–300 | all three set to `0` |

**A guard audit of all four branches finds no bounds check, no numeric clamp, no membership test, no
exception guard, and no existence check.** `research_buy_step_cash` matches a cost-token search only
because of its own parameter name; it performs **no cost validation and charges nothing**.

**`research_buy_step_cash` reads a client-supplied cash amount and discards it**, which is structurally
identical to M8 line 8's `used_syringe`: a legacy author took the price, printed "Buy research step
for …", and moved no balance. **No research price is committed and none is charged.**

There is also **no completion rule** — no branch reads `researchStepNumber` to decide whether an item
finished, and none reads `timeStampDoResearch` to decide whether a step is ready. The counter pair is
advanced **entirely on the client's word**.

---

## 3. Quests and chapters: real state, almost entirely client-sent

### `set_goals(goal_id, progress)` → `set_goals()` helper, `engine.py:96-100`

```python
def set_goals(privateState: dict, goal: int, progress: list):
    goals = privateState["goals"]
    while goal >= len(goals):
        goals.append(None)
    goals[goal] = progress
```

`progress` is `json.loads(args[1])`, documented in the source as **`[visited, currentStep]`** — a
**client-sent** progress vector. The helper **grows the list on demand**, which explains the corpus:
`privateState["goals"]` has **151 entries and every one is `None`**. A client walked goal ids up to 150
and the server padded the list to accommodate, writing no value for any of them.

### `complete_goal(goal_id)` — mutates nothing

The branch reads a goal id, prints the goal's committed title via `get_attribute_from_goal_id`, and
**writes no state at all**. There is no completion flag, no ledger, no reward. A goal "completes" by
being narrated in a print statement.

### `set_quest_var(key, value)` — `command.py:87-117`

Writes `map["currentQuestVars"][key] = value` with **both the key and the value from the client**, with
no membership test against the eight keys the source's own comment enumerates (`id`, `spawned`, `ended`,
`visited`, `activators`, `boss`, `treasure`, `killed`) — so **any key the client invents is accepted and
persisted**. Two special cases: the key
`idSimpleChapter` is **explicitly ignored** (the source's comment explains the game resets chapters past
9, so the key is dropped to let players reach chapter 99), and the key `id` **also** writes
`map["idCurrentMission"]`.

**The corpus trap:** `maps[0]["currentQuestVars"]` is **`None`**, not `{}`. The branch self-heals it
(`if not map["currentQuestVars"]: map["currentQuestVars"] = {}`), so the first write succeeds — but any
modern reader that assumes a dictionary will fault, and the corpus proves the field is genuinely
nullable.

### `collect_mission(next_mission)` — `command.py:430-442`

Writes `map["idCurrentMission"] = str(next_mission)` (**stringified, while the corpus records the
integer `0`**), sets `map["timestampLastChapter"] = time_now`, and **clears**
`map["currentQuestVars"] = {}`. `next_mission` is client-sent and the only guard is `if next_mission > 99:
next_mission = 1` — a **wrap**, not a rejection.

### `end_quest(json_blob)` — `command.py:752-807`, the most client-sent branch in the project

Takes **one argument that is a client-authored JSON blob**, parses it, and reads `win`, `duration`,
`units`, `map`, `difficulty`, `voluntary_end`, and `quest_id` from it. `difficulty` is the **only**
clamped value in the branch (`max(1, min(3, …))`). The branch then destroys player state:

```python
for unit in units:
    lost = max(0, unit[2] - unit[3])   # number of loses is A - B
    if lost > 0:
        map_lose_item(map, privateState, unit[0], lost)
```

**The number of units destroyed is computed by the client** from a client-sent tuple, and the item id
is client-sent. This is the single most authoritative-looking command in the legacy dispatcher with the
least server authority behind it.

### `admin_set_quest_rank(quest_index, difficulty)` — `command.py:745-750`

`privateState["questsRank"][str(quest_index)] = difficulty`, **both values client-sent**, no bounds,
creating the key on first write. The corpus's `questsRank` is `{}`.

### **The finding that connects M9 to M8: `map_lose_item` calls `push_dead_unit`**

`engine.py:215-228`:

```python
def map_lose_item(map: dict, privateState: dict, item: int, quantity: int):
    while qty > 0:
        for index in map_items:
            if map_items[index][0] == item and map_items[index][7]:
                _item = map_pop_item(map, index)
                push_dead_unit(privateState, _item)      # <-- M8 line 8's helper
```

**A unit lost in a quest is pushed onto the dead-hero ledger through the same helper M8 line 8
delivered.** This is the **fourth** door into `deadHeroes`, and the investigation of M8 line 8
recorded only three (`kill`, `sell`, `resurrect_hero`). That earlier record was correct **about the
dispatcher branches** — `map_lose_item` is an **engine helper**, not a branch — but the M9 measurement
shows the ledger has **four** entry points counting helpers, not three, and one of them is reached
from the quest path rather than the death path. M8 line 8's spec named three doors; this record
corrects that number and must be reflected in M9's deltas.

---

## 4. Tutorial: one branch, one flag, a client-sent threshold

`complete_tutorial(tutorial_step)` — `command.py:60-66` — sets `save["playerInfo"]["completed_tutorial"] = 1`
**iff** `tutorial_step >= 25 or tutorial_step == 15`. The step is client-sent; there is no other guard,
and the two conditions are a disjunction rather than a range. The corpus's
`playerInfo["completed_tutorial"]` is **`0`**, so this branch is genuinely exercisable.

---

## 5. Weekly reward: client-sent prize, server-advanced index

`weekly_reward(...)` — `command.py:345-364` — is guarded only by `len(args) > 4`. When five arguments
are present it places a **client-sent** `item_id` at **client-sent** `x`/`y` with a **client-sent**
player team via `map_add_item`, and appends to `bought_units`. It then sets
`timeStampMondayBonus = time_now` and advances `weeklyRewardIndex` by one. With fewer than five
arguments it prints "Won resources" and **pays nothing** — the resource prize is client-sent through
`apply_resources` before dispatch, like every other transaction in this project. The corpus's
`weeklyRewardIndex` is `0` and `timeStampMondayBonus` is `0`.

---

## 6. XP: what `building-xp` did not deliver

`add_xp_unit(item_index, xp_gain, level=None)` — `command.py:322-344` — resolves the row, then
`attr["xp"] += xp_gain` where **`xp_gain` is client-sent**, and prints a **client-sent** level that is
never used. The branch's own `level_up` note ("BOUGHT LEVEL UP") records that the level was bought, not
earned. This is the unit-XP surface M7's `building-xp` explicitly put out of scope, and it is
**exercisable in principle** but not in the committed corpus, where **0 of 40** placed rows carry
`attr["xp"]`.

---

## 7. Unit collections: a second, distinct branch

`unit_collections_completed(collection_id)` calls `unit_collection_complete()` (`engine.py:91-94`),
which appends the id to `privateState["unitCollectionsCompleted"]` **if not already present** — a
**membership test**, the one deduplicating guard in the whole M9 surface. This is a **different
helper and a different ledger** from the `complete_collection` branch M8 line 5 delivered. The corpus's
`unitCollectionsCompleted` is `[]`.

---

## 8. What is genuinely undelivered, stated plainly

| M9 item | Delivered | Still missing |
| --- | --- | --- |
| XP | `level_up` via `building-xp` (map-level, server-derived level, no reward paid, no unit XP) | `add_xp_unit`; unit XP entirely; the bought-level path |
| levels | the committed 100-entry curve, read-only | the curve's `reward_type`/`reward_amount` are read by **no** legacy branch; the legacy level gate and daily limit are not implemented |
| quests | **nothing** | `set_goals`, `complete_goal`, `set_quest_var`, `end_quest`, `admin_set_quest_rank`, `collect_mission`; all six |
| research | **nothing** | all four branches; the two-track counters |
| collections | `complete_collection` (the content-derived grant) | `unit_collections_completed`; the stored-item round trip (`place_stored_item`); collection eligibility |
| tutorial/progression | **nothing** | `complete_tutorial`; the chapter/mission chain |

---

## 9. The corpus can exercise most of this

This is what separates M9 from M8. Measured against `tests/saves/fresh-player.json`:

| State | Value | Consequence |
| --- | --- | --- |
| `privateState.researchItemNumber` | `[0, 0]` | **all four research branches exercisable** |
| `privateState.researchStepNumber` | `[0, 0]` | as above |
| `privateState.timeStampDoResearch` | `[0, 0]` | as above |
| `privateState.goals` | **151** entries, **all `None`** | `set_goals` exercisable; the list is already long enough that no padding occurs |
| `privateState.questsRank` | `{}` | `admin_set_quest_rank` exercisable |
| `privateState.unlockedQuestIndex` | `0` | present |
| `privateState.unitCollectionsCompleted` | `[]` | `unit_collections_completed` exercisable |
| `privateState.weeklyRewardIndex` | `0` | `weekly_reward` exercisable |
| `playerInfo.completed_tutorial` | `0` | `complete_tutorial` exercisable |
| `maps[0].idCurrentMission` | `0` (int) | `collect_mission` exercisable — and note the branch writes a **string** |
| `maps[0].questTimes` | `{}` | `end_quest` exercisable |
| `maps[0].currentQuestVars` | **`None`** | `set_quest_var` must handle a null field |
| `maps[0].level` / `xp` | `1` / `4` | already delivered by `building-xp` |

**Unlike M8 line 8 — where `resurrectable` is unit-only and the corpus holds no unit row — M9's state is
all present and all at its initial value.** Executed-legacy fixtures are therefore expected to be
capturable for most M9 lines, and this record deliberately does **not** pre-decide which.

The committed content is available too: `packages/game-content/normalized/quests.json` holds **91**
entries, every one carrying the same ten-field shape (`legacy_id`, `kind`, `source_file`, `source_layer`,
`content_version`, `id`, `title`, `hint`, `description`, `reward`), with the first entry
`{"legacy_id": "2", "kind": "quest", "id": 2, "title": "Train another Villager", "reward": 10}`.

---

## 10. The authority pattern M9 must confront

Every branch measured here writes state from client input. Not one validates. The established project
rule — clients send intent, the server derives outcomes — therefore applies to **M9 more sharply than
to any delivered milestone**, and the deliverable question for each line is the same one:

- where the legacy server **derives** something, reproduce the derivation (as `building-xp` and
  `unit-collection` did);
- where it **discards** a client amount (`research_buy_step_cash`'s `cash`, `used_syringe`'s precedent),
  ignore the amount and prove the no-charge claim with a post-execution proof that every stored
  resource is unchanged;
- where it **accepts a client-computed outcome** (`end_quest`'s `lost = unit[2] - unit[3]`), **refuse
  the outcome** rather than reproduce it, and record the divergence — reproducing a client-dictated
  destruction count would be exactly the anti-pattern `AGENTS.md` names as "Bad".

**No research price, no quest reward, and no tutorial reward is committed-consumable**, so no line may
pay one. The `reward` field exists on all 91 committed quest entries and is **read by no legacy
branch** — the same shape as the level curve's unread `reward_type`/`reward_amount`.

---

## How these figures were measured

Scripts under `%TEMP%\opencode\` (`m9_recon.py`, `m9_recon2.py`, `m9_recon3.py`, `m9_recon4.py`),
run with pinned CPython 3.9.13 and `-B`, all **read-only** over `command.py`, `engine.py`,
`sessions.py`, `server.py`, `constants.py`, `get_game_config.py`, `version.py`,
`packages/game-content/normalized/quests.json`, and `tests/saves/fresh-player.json`. No save, config,
content package, fixture, or legacy source was modified; the Git working tree carried no byte of
preserved material.

**Nothing in this record is inferred from a converted asset package**, the caution that made M8 line 7
scoped correctly — no rendering, animation, or combat semantics are claimed anywhere above.

---

## 11. Research, measured in full: the counters are write-only

This section was added after a follow-up probe, because the finding is sharper
than section 2 states and it decides the line's whole shape.

**Every occurrence of the three counters across the seven modules:**

| Counter | Sites | All writes? |
| --- | --- | --- |
| `researchStepNumber` | 3 | **yes** — `command.py:271` `+= 1`, `288` `= 0`, `297` `= 0` |
| `researchItemNumber` | 2 | **yes** — `command.py:287` `+= 1`, `296` `= 0` |
| `timeStampDoResearch` | 5 | 4 writes in the branches, plus **one read** at `command.py:923` |

**The single read is itself a write.** `command.py:922-928` is inside `fast_forward`:

```python
# research timers
research_timers = privateState["timeStampDoResearch"]
num_research_timers = len(research_timers)
i = 0
while i < num_research_timers:
    research_timers[i] = max(0, research_timers[i] - seconds)
    i += 1
```

`fast_forward` subtracts a **client-supplied** `seconds` from every research stamp, clamped at zero.

**Therefore: the research state surface is four branches plus one `fast_forward` decrement, and not one
of them reads a counter to decide anything.** There is no completion test, no readiness test, no
remaining-time computation, no unlock gate, and no cost check. The counters are pure bookkeeping with no
consumer — the same shape as `velocity`, which M8 line 6 found is positive on all 429 units and read by
nothing, and the same shape as `training_time`, which M8 line 4 refused to derive from.

**This decides M9 line 1's shape:** the deliverable is the counter mechanics themselves, and *every*
derivation must be refused, because there is nothing to derive from — not a refusal line like M8's, because
the counters genuinely mutate and the corpus genuinely exercises all four branches, but a line whose
entire content surface is "four commands, three integers, two tracks."

### `fast_forward` makes the research stamp client-writable

M8 line 6 recorded that `fast_forward` makes a row's instant client-writable and named it "the instant a
client-side readiness check would trust." **The research stamp is the same case, and it is worse in one
specific way: there is no readiness check anywhere, so the trusted-by-nothing instant is the *only*
elapsed-time input the research system has.** It has no observable effect for the same reason
`fast_forward` has none elsewhere — nothing evaluates it — and recording that is part of the line.

## 12. Research has almost no committed content, and the two tracks are resolvable

Measured across every normalized package and `config/main.json`:

- **No normalized package contains a research section.** `research` appears in exactly **one** normalized
  file, `buildings.json`, and there only inside a single `name` value: **`legacy_id` 256, `name`
  "Research Lab"**. It is a building, and it is not what the counters track.
- **`config/main.json` has no key whose name contains `research`** — zero of the 20 top-level content
  keys, and no nested key either.
- **There is therefore no committed cost, no committed step count, no committed unlock requirement, and no
  committed reward for research.** Nothing exists to derive a schedule from, which independently confirms
  section 2's refusal and strengthens it: a research price is not merely unsourced, it is **absent from
  the content entirely**.
- **The two tracks are named by committed content, though** — as building ids in
  `constants.py:299-300`: `ID_BUILDING_ROBOTIC_CENTER = 86` and `ID_BUILDING_AREA_51 = 139`. The branch
  comments read `0: TYPE_AREA_51 , 1: TYPE_ROBOTIC`, so track 0 is Area 51 (building 139) and track 1 is
  Robotic Center (building 86). The names `TYPE_AREA_51` and `TYPE_ROBOTIC` appear **only inside those four
  comments** and are defined nowhere, so the track-to-building link rests on the comment's own word order
  plus the two committed id constants — **established enough to report the mapping, not to derive any
  behaviour from it.**

## 13. What this means for the M9 line order

Research is the correct first M9 line, and the measurement sharpens the reasons rather than changing them.
It is a **closed four-branch set** over a **three-integer, two-track** state vector; it is **fully
exercisable** by the committed corpus, which holds all three counters at `[0, 0]`; it has the clearest
authority story in M9, since the counters advance on the client's word and the one price-taking branch
**charges nothing**; and it needs **no content package**, because none exists.

Quests remains the largest surface and the natural second line, with its content side already normalized at
**91** entries of a uniform ten-field shape.
