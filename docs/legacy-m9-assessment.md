# The M9 progression assessment — `XP`, `levels`, and `collections`

**Status:** committed investigation record. **This document implements nothing.**
It answers one question per deliver item: *what is delivered, what is
deliberately not, and does M9's exit criterion require the omissions?*

**Date:** 2026-10-03
**Branch:** `docs/m9-progression-assessment`
**Predecessors:** `docs/legacy-m9-progression.md` (PR #250, extended by #252),
`docs/legacy-m9-quests.md` (#258), `docs/legacy-m9-tutorial.md` (#264)
**Lines assessed:** `building-xp` (M7 line 11, archived `building-xp`),
`unit-collection` (M8 line 5, archived `2026-10-01-unit-collection`)
**Exit criterion under assessment:** *"Primary long-term progression systems
work."*

---

## 0. Summary

All three M9 items that had no delivered line are now delivered, archived, and
closed (`research`, `quests`, `tutorial/progression`). That leaves three items
which **were** delivered by earlier milestones and **deliberately narrowed**
there. This assessment establishes that:

1. **The level curve's index base is no longer derived-provisional.** The
   delivered `building-xp` line rested its one-based reading on **one** corpus
   data point. The committed **village** saves provide **eight**, and the
   one-based reading is **TIGHT on 7 of 8** while the zero-based reading is
   **TIGHT on 0 of 8**. The zero-based alternative is now excluded by
   measurement rather than retained as a caveat.
2. **Unit XP is not unreachable.** The delivered claim *"no unit XP; the corpus
   cannot exercise it"* is true of `tests/saves/fresh-player.json` and **false
   as a statement about the repository's committed evidence**: `attr["xp"]`
   appears on **171 rows across 5 of the 8 committed village saves**, with
   per-village totals up to **930,837**.
3. **Committed level rewards exist and are not uniform.** `building-xp` recorded
   that `reward_type` and `reward_amount` "carry no information" and paid
   nothing. Measurement contradicts the first half: the curve carries **five**
   distinct `(reward_type, reward_amount)` pairs, `c`/1 on 96 entries and four
   exceptions. A **second** committed reward table, `level_ranking_reward`,
   holds **50** entries naming a cash amount and a unit grant per level. Both
   have **zero** legacy consumers, so the refusal stands — but it now rests on a
   *content* argument rather than an *absence* argument.
4. **The stored-item placement round trip is exercisable from committed
   evidence.** `Nerri.json` carries six stored unit ids and free map slots;
   `place_stored_item` is `command.py:233-248`.
5. **One legacy duplication vector is recorded, not reproduced.**
   `remove_store_item` (`engine.py:77-84`) is conditional, so `place_stored_item`
   places a row even when the item is **not** in the store.

**Recommendation:** M9's exit criterion **cannot** be assessed as MET on
delivered evidence alone, for the reason in §5: no delivered M9 surface has a
progression *consumer*. **Each of the three assessed items has a real, bounded,
evidence-backed gap** — `XP` (the accumulation branch is undelivered), `levels`
(a reward exists in committed content but has no committed vocabulary), and
`collections` (the granted unit is never placed) — and §5 proposes them as
separate bounded lines. **Nothing here authorises implementing any of them.**

---

## 1. Method, and two defects in my own probes

Counting is by **quoted occurrence** over **comment-stripped** code across the
twelve legacy root modules (`command.py`, `engine.py`, `sessions.py`,
`server.py`, `constants.py`, `get_game_config.py`, `get_player_info.py`,
`auctions.py`, `version.py`, `bundle.py`, `build/path_bundle.py`,
`legacy_command_recorder.py`). Occurrence counts and distinct-line counts are
reported **separately**, after the `unit-production` line found a worker that
counted lines and called them occurrences.

### 1.1 Defect one — my first probe blanked the field names

The first version of the counter stripped **string literals**, which is exactly
where every save field name lives — `map["xp"]`, `save["privateState"]`. The
defect is reproduced and measured rather than recollected:

| field | defective probe (literals stripped) | corrected probe (comments only) |
| --- | --- | --- |
| `privateState` | **0 occ / 0 lines** | **138 occ / 113 lines** |
| `collections` | **0 occ / 0 lines** | **10 occ / 8 lines** |

Zero is not a subtle undercount — it is the whole field name gone, and it would
have supported a confident claim that `command.py` never touches
`privateState["collections"]`, when `command.py:517-518` reads it. Discarded; the
corrected probe removes comments only and keeps literals.

### 1.2 Defect two — my second probe computed one function twice

The first index-base probe printed columns headed `one-b` and `zero-b`, and both
columns showed the **same number on every row** — because both called the same
function. The second column was meaningless and would have supported a
confident claim about a reading it never tested. Discarded and re-measured with
a direct test in §2.2.

Recorded because both are the standing failure mode this repository keeps
learning: *assert before writing, and read the artifact, not the code.*

---

## 2. `XP` and `levels` — assessed against `building-xp`

### 2.1 What the legacy server actually does with the curve

| accessor | defined | imported | **called** |
| --- | --- | --- | --- |
| `get_xp_from_level(level)` | `get_game_config.py:100` | `command.py:4` | **0 call sites** |
| `get_level_from_xp(xp)` | `get_game_config.py:103` | — | **0 callers** |

`exp_required` — the field every threshold in the game comes from — has exactly
**2** occurrences across all twelve modules, `get_game_config.py:101` and
`:106`, and **both are inside these two dead accessors**. The `levels` key
itself has the same 2 occurrences, at `:101` and `:105`, in the same two
functions.

> **So the entire committed level curve is unreachable from every legacy command
> branch.** It is imported once and never called.

### 2.2 The index base is settled — eight data points, not one

The delivered line recorded its one-based reading as *derived-provisional* from a
single corpus data point (`xp 4`, stored level `1`) and explicitly retained the
rejected zero-based alternative. That caution was right, and the committed
villages now decide it directly.

**The test.** Stored level *n* names entry *n − 1* under the one-based reading
and entry *n* under the zero-based reading. A reading is **consistent** with a
save when the entry it names has `exp_required ≤ xp`, and **TIGHT** when the next
entry's `exp_required > xp`.

| committed save | level | xp | one-based (→ entry *level*−1) | zero-based (→ entry *level*) |
| --- | --- | --- | --- | --- |
| `AcidCaos.json` | 41 | 117,012 | **TIGHT** | INCONSISTENT (needs 120,275) |
| `General_Mike_30.json` | 40 | 107,502 | **TIGHT** | INCONSISTENT (needs 112,746) |
| `General_Mike_31.json` | 40 | 107,502 | **TIGHT** | INCONSISTENT (needs 112,746) |
| `Kiriakos.json` | 46 | 155,520 | **TIGHT** | INCONSISTENT (needs 163,955) |
| `Nerri.json` | 42 | 122,956 | **TIGHT** | INCONSISTENT (needs 128,180) |
| `Neutral.json` | 44 | 136,878 | **TIGHT** | INCONSISTENT (needs 145,195) |
| `Scarlet.json` | 33 | 107,694 | consistent, **not tight** (xp also reaches entry 33) | consistent, not tight (reaches entry 34) |
| `initial.json` | 1 | 4 | **TIGHT** | INCONSISTENT (needs 40) |

**One-based: TIGHT on 7 of 8. Zero-based: TIGHT on 0 of 8** — under zero-based,
every save's recorded level names an entry whose threshold that save's own
experience does not reach. The lowest case is the decisive one and matches the
original corpus observation exactly: `xp 4`, `level 1`; one-based names entry 0
(`exp_required` 0) and holds, zero-based names entry 1 (`exp_required` 40) and
fails.

> **The one-based reading is now established, not derived-provisional, and the
> zero-based alternative is excluded by measurement.** The eight-point
> corroboration is stronger than the one-point derivation it replaces, and the
> single named conversion (`level_envelope.entry_index_for_level`) needs no
> change.

`Scarlet.json` is the one genuine disagreement and is worth keeping: its stored
level **33** sits exactly **one level below** the curve's tight level of 34 for
its experience. That is the fingerprint of `level_up` having written a client
integer with no validation (§2.4), and it is the first committed evidence that
the stored level and the curve genuinely diverge in practice rather than in
theory. It also confirms the delivered decision to **report** the disagreement
rather than reconcile it.

### 2.3 Unit XP exists in the committed evidence — a correction

The delivered line recorded: *"unit XP and tutorial progression are out of scope
because the corpus cannot exercise them (0 of 40 placed rows carry
`attr["xp"]`; no unit placements exist)."*

That is **true of the corpus** and **false of the repository's committed
evidence.** Measured across all eight village saves:

| save | rows with `attr["xp"]` | sum | min | max |
| --- | --- | --- | --- | --- |
| `AcidCaos.json` | **36** | 12,438 | 19 | 4,892 |
| `Kiriakos.json` | **16** | 930,837 | 16 | 380,001 |
| `Nerri.json` | **46** | 784,852 | 80 | 611,650 |
| `Neutral.json` | **65** | 526,001 | 10 | 384,125 |
| `Scarlet.json` | **8** | 71,343 | 31 | 70,286 |
| `General_Mike_30/31.json`, `initial.json` | 0 | — | — | — |

**171 rows across 5 saves**, values from 10 to 611,650. The corpus's 0-of-40 is
a property of a *fresh player*, not of the evidence.

The mechanism is `add_xp_unit` (`command.py:322-343`): it looks the row up by
`args[0]`, then `attr["xp"] = xp_gain` when absent and `attr["xp"] += xp_gain`
otherwise. Its optional third argument is assigned to a local `level` and used
**only in a `print`** (`:340-341`) — it is never written anywhere. So the branch
has **one** stored effect and **one** display-only argument.

> **Correction to the delivered record:** unit XP is exercisable, and
> `add_xp_unit` is a real accumulation branch with an executed-legacy-fixture
> opportunity the delivered line did not claim. The *reason* the line gave for
> excluding it was wrong even though its *conclusion* (not delivered) was right.

### 2.4 `level_up` remains entirely client-dictated

`command.py:81-85` — one branch, one write, verbatim:

```python
elif cmd == "level_up":
    new_level = args[0]

    map["level"] = new_level
    print("Level up! New level:", new_level)
```

No range check, no XP validation, no curve consultation. `Scarlet.json`'s
one-level disagreement in §2.2 is committed evidence that a stored level can
indeed sit below the curve. The delivered endpoint already ignores a
client-supplied level and derives its target from stored experience against the
committed schedule — correct, and unchanged by this assessment.

### 2.5 `level` has one other home, and it is dead code

Beyond the report-only projections in `sessions.py` (`save_info` at `:145-147`
and the neighbour projection at `:201-202` and `:214-215`, all of which merely
*copy* `xp`/`level` into a response), the only other `level` occurrences are
five in `auctions.py` — the auction **bid**'s own `level` field, a different
field entirely.

The gate that would have used it, `Auctions.get_auctions(user_id, level)`, is
defined at `auctions.py:203` and has exactly **one** call site in the whole
repository:

```
server.py:200:  #     bets = auction_house.get_auctions(user_id, level)
```

**It is commented out.** So the auction level gate is unreachable code.

### 2.6 Committed level rewards exist, are non-uniform, and are unread

`building-xp` recorded that `reward_type` and `reward_amount` "are committed on
every entry and consumed by no legacy branch, so paying one would invent an
economy". The **zero-consumer** half is correct and re-measured: **0**
occurrences of either field across all twelve modules. The "carries no
information" half is **wrong**. Measured:

| `reward_type` | `reward_amount` | entries |
| --- | --- | --- |
| `c` | 1 | **96** |
| `s` | 50 | 1 |
| `w` | 250 | 1 |
| `s` | 250 | 1 |
| `g` | 250 | 1 |

All `reward_amount` values are **integers**, not the coerced strings the
quests/research lines saw elsewhere. Entry 0 is `Slave` (`exp_required` 0,
`s`/50), entry 1 is `Servant` (`exp_required` 40, `w`/250), entry 50 is
`Conqueror` (`exp_required` 207,439, `c`/1).

> A uniform "cash 1" reading would be **wrong for 4 of the 100 levels**, and the
> letters `c`/`g`/`s`/`w` have **no committed mapping** to any resource name.
> Paying one would therefore invent both a *schedule* and a *vocabulary*.

There is also a **second** committed reward table the delivered line did not
mention: **`level_ranking_reward`**, **50** entries, each shaped
`{level, cash, units}` —

```
{"level": 50, "cash": 1, "units": {"1016": 1}}
{"level": 24, "cash": 1, "units": {"1003": 1}}
{"level":  1, "cash": 1, "units": {"1037": 1}}
```

whose unit ids resolve against the 900 normalized items. It also has **zero**
legacy consumers. Three measured properties matter if it is ever delivered:

* the table **covers levels 1…50 completely** — 50 entries, 50 distinct levels,
  nothing missing, nothing outside the range, **no duplicates**;
* `cash` is **uniformly `1` on all 50 entries**, so the cash field carries **no
  variation** — all the information is in `units`;
* the order is **descending but not strictly so**: there is exactly **one**
  positional inversion, at index 30→31, where level **19** is followed by level
  **24**. Level 24's entry (`{"1003": 1}`) belongs between levels 25 and 23.

> So a **positional**-index consumer of this table would be correct for 49 of 50
> levels and wrong for level 24, while a **field-keyed** consumer would be
> correct for all 50. Which one the legacy client did is unobservable, since
> nothing reads the table.

### 2.7 Assessment for `XP` / `levels`

| | |
| --- | --- |
| **Delivered** | verbatim projection of `maps[0].xp` and `maps[0].level`; a server-derived level from stored experience against the committed curve; an intent-only `level_up` that ignores a client-supplied level; an executed-legacy fixture; a two-part post-state proof including "every stored resource unchanged" |
| **Deliberately not** | no level reward paid; no unit XP; no successful live level-up; stored-versus-derived disagreement reported, not reconciled |
| **Reassessed** | the index base is now **established**, not derived-provisional; unit XP **is** exercisable; level rewards **do** carry information |
| **Still true** | the curve is unreachable from every command branch; `reward_type`/`reward_amount`/`level_ranking_reward` have zero consumers; no reward vocabulary is committed |

**Does the exit criterion require the omissions?** Partly. `XP` and `levels`
are the *only* M9 items a player sees as progression, and as delivered they
advance nothing: a player can neither gain experience through a delivered
surface nor receive a reward for levelling. But the **legacy server cannot
express either** — the accumulation branch exists (`add_xp_unit`) yet the curve
that would price it is dead code, and the reward tables are unread. So this is a
**legacy capability gap**, not a modernization shortfall, and it must be recorded
as such rather than closed by inventing a schedule.

---

## 3. `collections` — assessed against `unit-collection`

### 3.1 Delivered state, unchanged

`/v0/collection` grants a collection's committed prize into storage, derives the
prize from the committed table (never from the client), appends the id to the
ledger, and proves both halves post-execution. Its captured fixture
(`Draggy Collection`, id `1`) moved the corpus's empty store to exactly
`{"1085": 1}` and the ledger to `[1]`.

### 3.2 Two collection systems exist, and they are distinct

The committed save carries **two** ledger fields, and the delivered line's
`collections` is only one of them:

| field | written by | committed evidence |
| --- | --- | --- |
| `privateState.collections` | `command.py:517-518` (`complete_collection`) | `Nerri` 8 ids, `Neutral` **all 10** |
| `privateState.unitCollectionsCompleted` | `engine.unit_collection_complete` (`engine.py:91-94`), called by the `unit_collections_completed` branch at `command.py:482-486` | `Nerri` `[1]` only |

The **unit** collection system has exactly **one** committed record anywhere in
the repository, against **ten** for the item collection system — so it is
effectively unevidenced.

### 3.3 The committed table, and the id mapping

`config/main.json` `collections` holds **10** entries with **string** ids
`"1"`..`"10"`, and all ten share one key set: `cashPrice`, `description`, `id`,
`item_ids`, `name`, `prize`. Entry `1`, verbatim:

```
{"id": "1", "name": "Draggy Collection", "item_ids": "[66,67,68,69,70]", "prize": "{\"1085\":1}", "description": "collection description 1", "cashPrice": "35"}
```

Entry `2` for contrast, verbatim:

```
{"id": "2", "name": "Transformer Collection", "item_ids": "[46,47,48,49,50]", "prize": "{\"1062\":1}", "description": "collection description 2", "cashPrice": "60"}
```

Both accessors index it the same way (`get_game_config.py:163-175`):

```python
index = max(0, collection - 1)
```

> The delivered line recorded "ids 0 and 1 alias". That is right but
> under-specified: it is a **`max(0, id − 1)` clamp**, so id `0` does not alias
> id `1` — it clamps to the *first* entry, which id `1` also names. The exact
> behaviour is that every id `< 1` names entry 0.

**Zero** legacy consumers for `item_ids`, `cashPrice`, and `description`. So the
requirement list is unchecked and there is no collection price — consistent with
the delivered line, and re-measured rather than inherited.

### 3.4 A client-supplied argument decides only the print

`complete_collection` (`command.py:504-523`) takes `args[1]` as `bought` and
uses it **only** to choose between `print(f"Bought {name}")` and
`print(f"Completed {name}")`. The prize is added and the ledger appended
unconditionally. The delivered endpoint already refuses a client-supplied
outcome, so this is consistent.

### 3.5 Assessment for `collections`

| | |
| --- | --- |
| **Delivered** | content-derived prize into storage; ledger append; executed-legacy fixture; two-part post-state proof; an id `0`-and-`1` refusal recorded |
| **Deliberately not** | the **placement** step; no eligibility check; no income/payout/cap semantics; no experience award |
| **Reassessed** | the id mapping is a `max(0, id − 1)` **clamp**, not a two-way alias; a **second, distinct** collection system (`unitCollectionsCompleted`) exists with one committed record |

**Does the exit criterion require the omissions?** **Yes, and uniquely.** A
collection is only meaningful once its unit is on the map, and `place_stored_item`
exists. The delivered line's own note — *"this line only evidences the grant into
storage and not a unit placed on the map"* — is the gap M9's exit criterion turns
on, and §4 shows it is now closable with committed evidence rather than blocked.

---

## 4. `place_stored_item` — the nearest follow-up, measured as exercisable

`command.py:233-248`, eight client-supplied arguments (`item_index`, `item_id`,
`x`, `y`, `playerID`, `orientation`, `unknown_autoactivable_bool`,
`unknown_imgIndex`), three effects:

```python
remove_store_item(map, item_id)
map_add_item(map, item_index, item_id, x, y, orientation=orientation)
bought_unit_add(save, item_id)
```

**The store is map-level** (`maps[0]["store"]`), not save-level. Committed
evidence with a populated store:

| save | placed rows | map key range | stored **unit** ids | stored **building** ids | first free slot |
| --- | --- | --- | --- | --- | --- |
| `Nerri.json` | 367 | 1 – 31,994 | **6** (1207 ×2, 1071, 1055, 1033, 1121, 1063) | 8 (one at quantity 0) | 31,995 |
| `Kiriakos.json` | 569 | 29 – 63,712 | **1** (1033) | 1 | 63,713 |
| `Scarlet.json` | 576 | 29 – 8,957 | 0 | 1 | 8,958 |

`boughtUnits` is well populated in the same five villages that carry
`attr["xp"]` — 50 (`Kiriakos`), 75 (`AcidCaos`), 76 (`Nerri`), 85 (`Scarlet`),
135 (`Neutral`) — and **0** in the corpus and in `initial.json` and both
`General_Mike` saves.

> **The round trip is fully exercisable from committed evidence**: a stored unit,
> a free map slot, a populated `boughtUnits`, and a real branch. The recorded
> blocker ("no acquired unit is ever placed on the map") is still true of the
> *delivered client*; it is not true of the *evidence*.

### 4.1 A legacy duplication vector, recorded and not to be reproduced

`remove_store_item` (`engine.py:77-84`) is **conditional**:

```python
def remove_store_item(map, item: int, quantity: int = 1):
    itemstr = str(item)
    if itemstr in map["store"]:      # <- absent is a silent no-op
        ...
```

So `place_stored_item` on an item that is **not** in the store still places the
row and still appends to `boughtUnits`. The legacy server therefore permits
placing an item the player never acquired. **A modern endpoint must verify store
membership** — reproducing the legacy absence here would be exactly the
client-dictated-outcome pattern `AGENTS.md` names as the anti-pattern.

### 4.2 The sell half exists too, and pays nothing

`sell_stored_item` (`command.py:250-256`) is a real branch two lines after the
placement one, and it is two statements long:

```python
elif cmd == "sell_stored_item":
    item_id = args[0]
    name = str(get_name_from_item_id(item_id))

    remove_store_item(map, item_id)

    print(f"Sell stored {name}.")
```

**It credits no resource.** No `map["gold"]`, no `apply_resources`, no return
value — the item leaves the store and nothing enters the balance. So the
delivered `building-store` line's claim that storage is display-only, with "no
placing from or selling out of storage", is accurate as a statement about the
*delivered client*, and the legacy branch it did not implement would itself have
paid **no refund**.

> A storage round trip therefore has **three** legacy branches, not one:
> `store_item`, `place_stored_item`, and `sell_stored_item` — of which the first
> is delivered and the other two are not, and **none of the three pays a price**.
> `store_add_items` (`command.py:258-266`) is a fourth, an unvalidated
> client-sent id list that grants into the store and appends to `boughtUnits`
> together — the same acquisition-from-client pattern `unit-production` recorded.

### 4.3 Everything else on the path is already delivered

`remove_store_item` and `map_add_item` are established; `building-move` already
delivers the coordinates; `unit-definitions` and `unit-instances` already deliver
the typed read-only unit view; `building-store` already delivers the store
projection. The only genuinely missing step is the command itself.

---

## 5. What M9's exit criterion requires, and the bounded next lines

M9's criterion is *"Primary long-term progression systems work."* Assessed
against the delivered evidence:

| item | delivered surface | can it *progress*? | verdict |
| --- | --- | --- | --- |
| `research` | counters, transitions | counters have **no in-game consumer** | transitions delivered; nothing consumes them |
| `quests` | state, no rewards | `complete_goal` **mutates nothing** | narrated, not completed |
| `tutorial/progression` | flag, gate | one-way flag, **zero readers** | delivered, inert |
| `XP` / `levels` | projection + derived level | no reward; accumulation branch undelivered | inert |
| `collections` | grant into storage | **the unit is never placed** | one step from working |

> **The exit criterion is not MET, and the reason is uniform across all five
> items: the legacy server has no progression *consumer*.** Every delivered M9
> surface projects, records, or narrates; nothing in the committed legacy server
> reads any of it back to change what a player may do. That is a finding about
> the oracle, and it is the honest answer to "do the primary long-term
> progression systems work".

Two gaps are nonetheless real, bounded, and evidence-backed. Proposed as
**separate bounded lines**, each with its own investigation and proposal, and
**neither authorised here**:

1. **`place_stored_item`** — the stored-unit placement round trip. Legacy branch
   known (`command.py:233-248`), committed corpus for it now measured and
   named (`Nerri`), store-membership verification required and recorded as a
   deliberate divergence from the legacy absence. This is the nearest undelivered
   step on a fully content-derived path and the only one that turns a delivered
   M9 surface into a working one. Its sibling `sell_stored_item` is the same
   round trip with **no refund** and is a natural companion scope, since the
   two branches sit three lines apart and neither pays a price.
2. **`add_xp_unit`** — the unit-experience accumulation branch. Legacy branch
   known (`command.py:322-343`), committed `attr["xp"]` evidence now measured
   (171 rows, 5 saves), optional `level` argument already known to be
   display-only. The level-curve reward tables are **not** in scope: they have
   zero consumers and no committed resource vocabulary, so paying one is
   refused, and that refusal should be re-recorded against §2.6's corrected
   measurement rather than the delivered line's weaker claim.

The remaining items (`reward_type`/`reward_amount`, `level_ranking_reward`,
`unitCollectionsCompleted`, collection `item_ids` eligibility, collection
`cashPrice`) are **refused**, each for a measured reason, and each reason is now
stated against a corrected measurement rather than an assumed one.

---

## 6. Corrections this assessment makes to delivered records

| delivered claim | where | correction |
| --- | --- | --- |
| the one-based curve index is *derived-provisional* from one data point | `building-xp` | **established**: TIGHT on 7 of 8 committed saves, zero-based TIGHT on 0 of 8 |
| `reward_type`/`reward_amount` "carry no information" | `building-xp` | they carry **five** distinct pairs; `c`/1 on 96 of 100, four exceptions |
| unit XP is out of scope because "the corpus cannot exercise it" | `building-xp` | true of the corpus, **false of the evidence**: 171 rows across 5 village saves |
| collection ids `0` and `1` "alias" | `unit-collection` | it is a **`max(0, id − 1)` clamp**; every id `< 1` names entry 0 |
| collections have one ledger | `unit-collection` | there are **two**, `collections` and `unitCollectionsCompleted`, and only the first is delivered |

Three of these change a *reason* while leaving a *conclusion* intact, which is
the outcome this repository should prefer: **nothing here requires un-delivering
any delivered behaviour**, and every claim limit that was sound is still sound.
The two that narrow a *claim* rather than a reason — the index base becoming
established, and the collection id mapping becoming precisely specified — both
make a delivered behaviour *more* precisely specified than the record it came
from, and neither changes a single byte of delivered behaviour.