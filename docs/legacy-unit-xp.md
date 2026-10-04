# Legacy unit experience (`add_xp_unit`) — investigation record

**Status:** investigation only. **No endpoint, no award, and no capability is proposed
by this record.** It establishes the branch's full contract from committed source plus
**22 executed-legacy transactions**, answers the seven authority questions, corrects the
delivered evidence base, and states what the smallest honest bounded change would be —
which is **not** a server-derived unit-XP award, because no trusted derivation exists.

**Date:** 2026-10-04 · **Milestone:** M9 — Progression, second post-assessment line ·
**Predecessors:** `research`, `quests`, `tutorial/progression` delivered and archived;
`godot-unit-production` already delivers a **read-only, never-awarded** projection of
this very field

**Facts not re-derived here** (already established by committed records): that
`add_xp_unit` creates nothing, that its XP amount is client-sent, that its optional level
is client-sent and used only in a `print` (`docs/legacy-unit-production.md` §3); that the
`levels` schedule has 100 strictly increasing `exp_required` entries and is read by no
legacy branch; that `reward_type` / `reward_amount` are committed on every level entry and
read by no legacy branch, so no level reward is paid; that `collect_xp` is never read;
that `unit_capacity`, `training_time`, `velocity`, `max_frame` and the behavioural
`properties` flags have zero legacy consumers; and that `place_stored_item` is
type-agnostic with five of eight row slots server-derived.

---

## 1. The headline: there is no trusted award, and this is the first executed evidence for the branch

Two findings, one negative and one corrective, and **the negative is the one that decides
the line.**

**The negative.** `attr["xp"]` — a placed row's accumulated unit experience — has
**exactly two occurrences in the entire legacy source**, and both are inside
`add_xp_unit` itself: one assignment and one increment. **It has zero readers.** No branch,
no engine helper, no session function, no migration ever reads it. And the amount that
reaches it is `args[1]`, taken from the client with **no validation of any kind** — not
even an `int()` call. So a unit's recorded experience is a running total of client-asserted
numbers that nothing on the server ever consults.

**The corrective.** The delivered record said unit experience was unreachable *"because
the corpus cannot exercise it (0 of 40 placed rows carry `attr["xp"]`)"*. That is **true
of the fresh-player corpus and false of the repository's committed evidence.** Measured
across **all 31 committed save documents** — the 8 in `villages/` plus the 23 quest
snapshots in `villages/quest/` — the field appears on **171 of 12,954 placed rows**, in
exactly **5 of 31** documents. Every one of the 23 quest snapshots, holding 9,662 rows
between them, carries **zero**. So the field is not absent from the evidence; it is
**rare**, and a progressed village is required to see it.

The M9 assessment already recorded the 171-row correction. This record goes further in
three ways: it extends the count to the 23 quest snapshots nobody had walked, it
establishes the branch's behaviour **by execution rather than by reading**, and it proves
the negative — that no derivation exists — with arithmetic rather than with an absence of
search results.

---

## 2. The branch, and the total absence of a reader

```python
# command.py:322-343
elif cmd == "add_xp_unit":
    item_index = args[0]
    xp_gain = args[1]
    level = None
    if len(args) > 2:
        level = args[2]

    item = map_get_item(map, item_index)
    if not item:
        print("Error: item not found.")
        return

    attr = item[6]
    if "xp" not in attr:
        attr["xp"] = xp_gain
    else:
        attr["xp"] += xp_gain

    if level:
        print(f"{get_name_from_item_id(item[0])} +{xp_gain}xp BOUGHT LEVEL UP -> {level}")
    else:
        print(f"{get_name_from_item_id(item[0])} +{xp_gain}xp")
```

### 2a. Occurrence counts over the whole legacy root (11 `.py` files)

Counted as **occurrences**, not distinct lines, so a line matching twice counts twice.

| Needle | Occurrences | Where |
| --- | --- | --- |
| `add_xp_unit` | **1** | the dispatch test at `command.py:322` — no engine helper, no other caller, no second branch |
| `attr["xp"]` | **2** | `command.py:336` (`=`), `command.py:338` (`+=`) — **both writes, both inside this branch** |
| `xp_gain` | 5 | `command.py:324, 336, 338, 341, 343` — one read from the client, two writes, two print interpolations |
| `get_xp_from_level` | 2 | the import at `command.py:4` and the definition at `get_game_config.py:100` — **zero call sites** |
| `get_level_from_xp` | 1 | the definition at `get_game_config.py:103` — **zero call sites, and not even imported** |
| `"xp"` **subscript** `["xp"]` | **10** over **7 lines** | the **player's** XP: `command.py:314` ×1, `engine.py:262` ×2, `sessions.py:145` ×1, `sessions.py:201` ×2, `sessions.py:214` ×2. The **row's** `attr["xp"]`: `command.py:336` ×1, `command.py:338` ×1. Separately, `command.py:335` tests the bare key literal `"xp" not in attr` — a membership test, not a subscript. |
| `min_level` | **0** | — |
| `gift_level` | **0** | — |
| `collect_xp` | **0** | — |
| `reward_type` / `reward_amount` | **0** | — |
| `level_ranking_reward` | **0** | — |
| `COST_XP` / `TOKEN_XP` | 2 | definitions only (`constants.py:893, 1050`) — **zero consumers** |
| `attr` in `version.py` | **0 lines** | no save migration touches any attribute bag |

**No other command writes the `xp` key of any attribute bag.** `fast_forward` stamps row
and map *instants*, never `xp`; `add_click` and `activate_item_click` write `nc`; `sell`
and `kill` delete rows. The only `["xp"]` writes in the root are `command.py:336` and
`:338`. And the only *reads* of any `"xp"` key outside `add_xp_unit` are reads of the
**player's** `maps[0]["xp"]`.

**So the accumulated unit total is write-only** — the same shape as M9's three
`research` counters, which were delivered as a refusal for precisely this reason, and the
same as the established precedent for `unit_capacity`, `training_time`, `velocity`,
`max_frame`, the behavioural `properties` flags, `collect_xp` and `unlockedQuestIndex`:
**record the field, refuse to invent a rule from it.**

### 2b. The two XP helpers are both dead, and both are *player*-level

`get_xp_from_level(level)` reads `levels[level]["exp_required"]` and
`get_level_from_xp(xp)` walks the same curve. **Neither is ever called** — the first is
imported into `command.py` and unused; the second is not even imported. Both name the
**player** level curve, which the M7 `building-xp` line already delivers as the player's
level, derived under its own derived-provisional one-based index.

That matters for the framing: the committed curve is *not* an unread field here, and it is
*not* a unit-XP award schedule. `add_xp_unit` does not consult it, and its optional third
argument is a **client-sent** integer that is never checked against it.

### 2c. `apply_resources` moves a *different* XP, and it is the one that is clamped

`apply_resources(save, map, resources_changed)` runs at `command.py:40`, **before** the
dispatch. Its eight slots are `unknown, xp, gold, wood, oil, steel, cash, mana`
(`engine.py:251-271`), so slot 1 is the **player's** `maps[0]["xp"]`, written as
`max(map["xp"] + xp, 0)`.

Two consequences, both confirmed by execution in §4:

- The player XP and the unit accumulator are **two distinct quantities** that a single
  request can move **together**, both from client-supplied amounts.
- **Only the player one is clamped at zero.** The unit accumulator has no clamp, and a
  negative `xp_gain` drives it negative.

---

## 3. Question 1 — is there any committed rule that derives a legitimate `xp_gain`?

**No. Established, and established by arithmetic rather than by a failed search.**

### 3a. The committed per-unit `xp` field exists, and is never read

`units[].xp` is present on **429 of 429** units with **24 distinct values** — the largest
groups being `30` ×133, `80` ×121, `15` ×38, `25` ×22, `20` ×22, `5` ×16. It is a
**static per-definition value in the range 5–80**, not an accumulator.

It has **zero legacy consumers.** Every `get_attribute_from_item_id` call site in the root
asks for one of exactly three names — `sm_training_time` (`command.py:735`),
`properties` (`engine.py:18, 154`), `clicks_to_build` (`engine.py:26`) — and **none asks
for `xp`**. There is no other per-item attribute-read path.

### 3b. Three independent arguments rule it out as the award

1. **The same unit id carries different accumulated values.** Grouping all 171 rows by
   item id gives **55 distinct unit ids, of which 27 take more than one value.** Unit
   `1034` (UN Allied, committed `xp` = 7) alone carries **24 distinct totals inside the
   single save `Neutral.json`** — `10, 13, 15, 54, 55, 61, 112, 115, 118, 130, 132, 153,
   188, 255, 458, 1024, 1286, 1383, 1417, 1618, 1660, 1869, 1871, 1942`, spread over 24
   separate placed rows. A quantity that varies across 24 rows of one definition cannot be
   a function of that definition.
2. **The totals are not multiples of the committed value.** The ratio
   `attr["xp"] / units[].xp` takes **167 distinct rounded values** from `0.4` to
   `38,412.5`, and only **9** of them are integral. So the total is not a count of
   fixed-size awards.
3. **The totals are not the player's experience either.** **0** of 171 rows equal their
   save's `maps[0]["xp"]`; 167 are below it and **4 are above it** — up to 611,650 against
   a stored 122,956.

The largest values also look like assertions rather than accumulations. The ten largest
distinct values are `611,650`, `384,125`, `380,001`, `200,001`, `90,001`, `80,001`,
`70,286`, `29,815`, `28,351`, `20,183` — and **exactly four of the 155 distinct values end
in `001`** (`80,001`, `90,001`, `200,001`, `380,001`), all four in `Kiriakos.json`. None of
the four is among the top three, so the pattern is a handful of manual values rather than a
scale. Whatever produced them, it was not a committed per-unit award.

The full set of 155 distinct values runs from `10` to `611,650`, summing to `2,325,471`.
Whatever produced them, it was not a committed per-unit award.

### 3c. Every other candidate field has zero legacy consumers

| Field | Committed on | Legacy consumers | Verdict |
| --- | --- | --- | --- |
| `units[].xp` | 429/429 units, 24 values | **0** | unread; and refuted as the award by §3b |
| `units[].collect_xp` | 429/429, 6 values (`3`×211, `2`×159, `1`×37, `5`×12, `4`×8, `0`×2) | **0** | already recorded unread; M8's `collection` line refuses to award it |
| `units[].min_level` | 429/429, 21 values (`6`×190, `8`×155, …) | **0** | an acquisition **gate**, not an award |
| `units[].gift_level` | 429/429, 8 values (`4`×282, `1`×138, …) | **0** | a gifting gate, not an award |
| `levels[].exp_required` | 100/100 entries | **0** (`get_xp_from_level` and `get_level_from_xp` are both dead) | the **player** curve; already delivered by M7 `building-xp` |
| `levels[].reward_type` / `reward_amount` | 100/100 entries, and near-uniform: `reward_type` is `'c'` on 96 of 100 (then `'s'` ×2, `'w'`, `'g'`) and `reward_amount` is `1` on 96 of 100 (then `250` ×3, `50`) | **0** | preserved refusal; **not** to be paid — and the 96-fold uniformity means they carry almost no information even if they were read |
| `level_ranking_reward[]` | 50 entries, levels 50…1, each with `cash` and a `units` grant | **0** | a **player-level** ranking reward, not a unit-XP award |

The `level_ranking_reward` shape is worth quoting so it is not later mistaken for a
per-unit award: entry `legacy_id` `"50"` is
`{"level": 50, "cash": 1, "unit_refs": ["1016"], "units": {"1016": 1}}` — a cash amount
and a unit grant, keyed by **player level**.

### 3d. There is no committed per-unit level schedule anywhere

Enumerating every `level`-shaped key across all 22 normalized content files finds exactly
five places, none of them per-unit:

| File | Key | Count | What it is |
| --- | --- | --- | --- |
| `levels.json` | `level_index` | 100 | the **player** XP curve |
| `level_ranking_reward.json` | `level` | 50 | **player-level** ranking rewards |
| `magics.json` | `level` | 10 | a magic's player-level requirement |
| `map_prices.json` | `level` | 4 | a map tier price schedule |
| `town_prices.json` | `level` | 4 | a town tier price schedule |

There is no unit level, no unit XP curve, no per-unit threshold and no per-unit award
table in the committed package. **The `level` argument of `add_xp_unit` has no committed
schedule behind it at all** — it is a client-sent integer that is printed and discarded.

> **Recorded explicitly, as instructed:** there is **no trusted source for `xp_gain`.** The
> legacy server accepts a client-supplied amount, and that acceptance is not authority. A
> client-supplied XP amount must not become an authoritative modern intent merely because
> the legacy server stores it.

---

## 4. Question 2 — what the branch actually accepts: 22 executed transactions

### 4a. Method, and three harness defects found and fixed

The disposable corpus seeds `saves/AcidCaos.save.json` from the committed
`villages/AcidCaos.json` (SHA-256 `870a3c20…e9cd`). Of the five committed saves that carry
`attr["xp"]`, this one was chosen because it is the **smallest by placed-row count** (319,
against 569 / 367 / 549 / 576 for the other four), so it is the cheapest disposable, while
still carrying **36** rows with the field — ample for a fixture — **and** 283 without it,
including **12 unit rows** with an empty bag (`1783`, `1792`, `1793`, `1795`, `1909`, …)
and **271 building rows**. So **both** arms of `if "xp" not in attr` and **both** kinds of
row are exercisable from **one authentic committed save**, with no fabricated player state.

Targets used: key `772` = unit `1007` (Soldier) with `{"xp": 23}`; key `1783` = unit
`1050` with `{}`; key `3` = building `23` (Wall I) with `{}`.

Three defects in my own harness, all found by measurement and all recorded rather than
quietly repaired:

1. **The legacy server caches the corpus in memory.** `sessions.load_saves()`
   (`sessions.py:34-66`) reads `saves/` once at import into a module-global `__saves`.
   Restoring the save file between probes therefore does **not** reset server state: the
   first version of this harness restored the file and every probe after the first
   silently **accumulated** onto its predecessor while reporting the restored on-disk
   value as "before". **Fixed** by starting and stopping one server per probe. **12
   transactions from the first pass are discarded** and none of their numbers are used.
2. **Request-time `print` output was lost.** Python block-buffers stdout when it is
   redirected to a file, and `terminate()` killed the server before the buffer flushed, so
   every log ended at `[+] Running server...`. **Fixed** with `PYTHONUNBUFFERED=1` in the
   child environment; five argument tuples were then **re-executed** to capture their
   printed lines.
3. **Two containment digests from two different recipes.** The discarded first script and
   the per-probe script each implemented their own containment digest over slightly
   different traversal orders. The `4e966fda…` value belongs to the discarded script and is
   **not** comparable with the per-probe script's. The single valid figure is below, taken
   before and after the executed pass with one function, and re-measured afterwards with
   that same function.

**Containment:** `11e3b807afb4759467e3dd07137390e43892b031666314a1c759766c1ca37f18`,
identical before and after the executed pass and identical when re-measured later — over
the 11 root `*.py` files and `config/`, `mods/`, `villages/`, `templates/`,
`tests/saves/`, `saves/`. `git status --porcelain` is empty and **no working-tree
`saves/` exists**. All network traffic was `127.0.0.1:5055`. **39 server starts** in
total: 12 discarded, 22 distinct transactions, 5 re-executions.

### 4b. The accepted-and-mutating cases

All rows below are from `villages/AcidCaos.json`, each in a fresh disposable with a fresh
server. "Leaves" is the changed-leaf-path set of the whole save document.

| # | `args` | HTTP | body | `attr` before → after | Leaves |
| --- | --- | --- | --- | --- | --- |
| P01 | `[772, 5]` | 200 | `{"result":"success"}` | `{"xp": 23}` → `{"xp": 28}` | **1** |
| P02 | `[1783, 7]` | 200 | `{"result":"success"}` | `{}` → `{"xp": 7}` | **1** |
| P03 | `[772, -1000]` | 200 | `{"result":"success"}` | `{"xp": 23}` → **`{"xp": -977}`** | **1** |
| P04 | `[772, 0]` | 200 | `{"result":"success"}` | `{"xp": 23}` → `{"xp": 23}` | 0 |
| P05 | `[999999, 5]` | 200 | `{"result":"success"}` | *(no such row)* → *(no such row)* | 0 |
| P07 | `[772, 2.5]` | 200 | `{"result":"success"}` | `{"xp": 23}` → **`{"xp": 25.5}`** | **1** |
| P08 | `[772, 5, 9]` | 200 | `{"result":"success"}` | `{"xp": 23}` → `{"xp": 28}` | **1** |
| P09 | `[3, 11]` | 200 | `{"result":"success"}` | `{}` → `{"xp": 11}` | **1** |
| P11 | `[772, 5]` **+ vector `[0,999,0,0,0,0,0,0]`** | 200 | `{"result":"success"}` | `{"xp": 23}` → `{"xp": 28}` | **2** |
| P12 | `[772, 10**12]` | 200 | `{"result":"success"}` | `{"xp": 23}` → **`{"xp": 1000000000023}`** | **1** |
| P14 | `[772, 5]` (repeat of P01, fresh disposable) | 200 | `{"result":"success"}` | `{"xp": 23}` → `{"xp": 28}` | **1** |

Eight findings fall out of this table, and each one is a rule a modern endpoint must not
invent:

- **P02 — the assign arm is real and is the only way the field ever appears.** On a bag
  with no `xp`, the branch writes `args[1]` verbatim.
- **P03 — there is no clamp.** `23 - 1000 = -977` is stored. This is the sharp contrast
  with `apply_resources`, whose player XP is `max(current + delta, 0)`. A row's experience
  can therefore go **negative** in a committed save, and nothing rejects it.
- **P04 — zero is a no-op by coincidence, not by rule.** The branch writes `0` into the
  key; the value happens to be unchanged.
- **P05 — a missing row is a silent success.** The branch prints an error and returns
  early, but `command()` still calls `save_session(USERID)` (`command.py:32`), so the
  request answers `{"result":"success"}` with **zero** leaves changed. A client cannot
  distinguish "awarded" from "no such row" from the response body.
- **P07 — a float is persisted.** `25.5` is written into the save as a JSON number with a
  fractional part. There is no `int()` anywhere in the branch.
- **P09 — the branch is type-agnostic.** A **building** row accepted the write. The
  committed evidence only ever records the field on units (§4e), but the server does not
  check, so the *capability* is not unit-scoped and must not be described as if it were.
- **P11 — one request moves two XPs.** With a client-sent vector of slot 1 = 999, the
  player's `maps[0]["xp"]` went `117012 → 118011` **in the same transaction** as the unit's
  accumulator, and the leaf set is `["/maps/0/items/772/6/xp", "/maps/0/xp"]`. This is the
  untrusted-vector pattern M7 `expand` and M9 `research` already refuse.
- **P12 — no bound.** A one-trillion gain is accepted and stored.

### 4c. The failing cases, and the asymmetric poisoning

| `args` | HTTP | `attr` before → after | Exception |
| --- | --- | --- | --- |
| `[772, "5"]` | **500** | `{"xp": 23}` → `{"xp": 23}` | `TypeError: unsupported operand type(s) for +=: 'int' and 'str'` at **`command.py:338`** |
| `[1783, "5"]` | **200** | `{}` → **`{"xp": "5"}`** | *none* — a **string is persisted** |
| `[772, "abc"]` | **500** | `{"xp": 23}` → `{"xp": 23}` | `TypeError` at `command.py:338` |
| `[772]` | **500** | `{"xp": 23}` → `{"xp": 23}` | `IndexError: list index out of range` at **`command.py:324`** |
| `[]` | **500** | — | `IndexError: list index out of range` at **`command.py:323`** |
| `[772, null]` | **500** | `{"xp": 23}` → `{"xp": 23}` | `TypeError: … 'int' and 'NoneType'` at `command.py:338` |
| `[772, true]` | **200** | `{"xp": 23}` → **`{"xp": 24}`** | *none* — Python `bool` is an `int`, so `True` is **+1 XP** |
| `[-5, 5]` | **200** | *(no such row)* → *(no such row)* | *none* — a negative index is a silent no-op |
| `["772", 5]` | **200** | `{"xp": 23}` → `{"xp": 28}` | *none* — `map_get_item` does `str(index)` (`engine.py:36-40`), so a string index resolves |

**The two arms are asymmetric and the difference is a save-poisoning path.** A string gain
**fails** on a row that already has `xp` (the `+=` at `:338` raises), but **succeeds** on a
row that does not (the `=` at `:336` stores whatever it is given). The server can therefore
be made to write `{"xp": "5"}` into a committed save — and every subsequent increment
against that row is a guaranteed 500. That is a durability defect in the legacy server, not
a capability to reproduce.

Every 500 comes through `server.py:318` in `command_response` (`server.py:303`).

### 4d. The printed lines, verbatim

Re-executed with `PYTHONUNBUFFERED=1`. The `[+] COMMAND: … ->` prefix is added by
`server.py`; everything after the arrow is this branch's own output.

```
[+] COMMAND: add_xp_unit([772, 5])     -> Soldier +5xp
[+] COMMAND: add_xp_unit([772, 5, 9])  -> Soldier +5xp BOUGHT LEVEL UP -> 9
[+] COMMAND: add_xp_unit([999999, 5])  -> Error: item not found.
[+] COMMAND: add_xp_unit([3, 11])      -> Wall I +11xp
[+] COMMAND: add_xp_unit([772, -1000]) -> Soldier +-1000xp
```

Two of these are load-bearing. `Wall I +11xp` is the printed proof of type-agnosticism —
the name is resolved from the **item definition**, so the log calls a building a unit.
`Soldier +-1000xp` is the printed proof that there is no clamp: the double sign is the
server's own formatting of a negative gain, not a transcription.

### 4e. What the committed evidence actually contains

Measured over **all 31 committed save documents**:

| Document group | Documents | Placed rows | Rows carrying `attr["xp"]` |
| --- | --- | --- | --- |
| `villages/*.json` | 8 | 3,292 | **171** |
| `villages/quest/*.json` | 23 | 9,662 | **0** |
| **total** | **31** | **12,954** | **171** (in 5 documents) |

| Save | Rows | With `attr["xp"]` | Sum | Min | Max | Player `maps[0]["xp"]` | Level |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AcidCaos.json` | 319 | **36** | 12,438 | 19 | 4,892 | 117,012 | 41 |
| `Kiriakos.json` | 569 | **16** | 930,837 | 16 | 380,001 | 155,520 | 46 |
| `Nerri.json` | 367 | **46** | 784,852 | 80 | 611,650 | 122,956 | 42 |
| `Neutral.json` | 549 | **65** | 526,001 | 10 | 384,125 | 136,878 | 44 |
| `Scarlet.json` | 576 | **8** | 71,343 | 31 | 70,286 | 107,694 | 33 |
| `General_Mike_30.json` | 436 | 0 | — | — | — | 107,502 | 40 |
| `General_Mike_31.json` | 436 | 0 | — | — | — | 107,502 | 40 |
| `initial.json` | 40 | 0 | — | — | — | 4 | 1 |

Five structural facts about the recorded values, all measured:

- **All 171 are `int`.** No string and no float appears in committed evidence, even though
  the branch accepts both (§4c).
- **All 171 resolve to a committed unit**; **zero** to a building. The unit-only shape of
  the *evidence* is in sharp contrast to the branch's type-agnostic *behaviour*.
- **Every one of the 171 bags contains exactly one key**, `xp`. The field never appears
  beside `nc`, `si`, `nu`, `ts` or anything else — it arrives in isolation.
- **55 distinct unit ids** carry it, and **27 of them carry more than one value** (§3b).
- `General_Mike_30.json` and `_31.json` are **not** byte-identical and **not**
  parse-identical, despite equal row counts and equal stored XP. They are two distinct
  saves at the same level, not a duplicated pair.

---

## 5. Question 4 — can a fixture be captured without fabricating player state?

**Yes, and this would be the repository's first capture seeded from a village save rather
than from `tests/saves/fresh-player.json`.**

Every capture harness in `apps/compat-api/` seeds its disposable corpus from
`FRESH_PLAYER_SAVE`, a module constant (`capture_legacy_fixtures.py:98, 237-255`), and
derives the `pid` from `seed["playerInfo"]["pid"]`. A village save satisfies that contract,
though **not uniformly**: `playerInfo.pid` equals the filename stem for only **5 of the 8**
— `AcidCaos`, `Kiriakos`, `Nerri`, `Neutral` and `Scarlet` — while `General_Mike_30.json`
carries pid `100000030`, `General_Mike_31.json` carries `100000031`, and `initial.json`
carries **no pid at all**. A capture must therefore read the pid from the document rather
than construct it from the filename. Every save is structurally identical to the fresh
corpus — the same four top-level keys `{maps, playerInfo, privateState, version}`, the same
**32** `maps[0]` keys and the same **47** `privateState` keys. Because
`sessions.load_saves()` keys every file in `saves/` by `playerInfo.pid`, seeding
`saves/AcidCaos.save.json` and posting as `USERID=AcidCaos` works, which is what §4 did.

**No fabrication would be needed.** `AcidCaos.json` already contains, in one authentic
committed save:

- a unit row **with** `attr["xp"]` (key `772`) — the increment arm;
- a unit row **without** it (key `1783`) — the assign arm;
- a building row (key `3`) — the type-agnostic arm;
- and no key `999999` — the missing-row arm.

**Two things this changes and one it does not.**

*Changed:* the claim that "no executed-legacy fixture exists for this branch" is no longer
merely true-of-the-corpus. It was true when written, and it is now **superseded**: 22
transactions have been executed. `docs/legacy-unit-production.md` §5 already listed
`add_xp_unit` as *"Yes, but inert — it needs a placed row; it would add a client-sent
`attr["xp"]` to a building"*, which P09 turned from a prediction into an execution
(`Wall I +11xp`).

*Unchanged:* the branch's behaviour is still entirely a function of a **client-supplied
amount**. A fixture can prove the branch's *mechanics*; it cannot make the amount
authoritative. Recording the former never implies the latter.

*Not attempted here:* this record captures nothing into the repository. Per-transaction
fixture directories, manifests, and a `capture_*_fixture.py` script are Apply-stage work
and belong to a proposal, not to an investigation.

---

## 6. Question 5 — exactly what leaves change on success

From the fourteen isolated pass-one transactions, and from P11 in particular:

**On a successful increment (P01):** exactly **one** leaf changes,
`/maps/0/items/<key>/6/xp`. Nothing else in the document moves.

**On a successful first-time assignment (P02):** exactly **one** leaf changes,
`/maps/0/items/<key>/6/xp`, and it is an **addition** — the key did not exist in the bag
before, so the bag goes from `{}` to `{"xp": …}` and its key count changes.

**Byte-identical across every successful case:** the row's other seven slots (item id, `x`,
`y`, the timestamp, orientation, the garrison list, the player team), the number of placed
rows, every other row in the document, `maps[0]["store"]`, the whole `privateState`, the
whole `playerInfo`, and — checked separately for each transaction — **all five of the
stored resource slots the save carries** (`gold`, `wood`, `steel`, `oil`, `xp`) plus every
other `maps[0]` key.

**The one exception, and it is not the branch's doing:** P11 moved a second leaf,
`/maps/0/xp`, because `apply_resources` had already applied the client-sent vector at
`command.py:40`. A neutral vector changes nothing, which is what every other row above
records.

So the branch's own stored effect is **precisely one leaf**, and it is always
`items/<key>/6/xp`. That is a clean post-execution proof shape for any future endpoint: one
addressed row, one bag key, every other resource unchanged.

---

## 7. Question 6 — is the optional `level` argument safely ignorable?

**Yes — and it is proven ignorable rather than argued to be.**

`level` is assigned to a local at `command.py:325-327` and used **only** in the
interpolated `print` at `:340-341`. It is written nowhere. Three measurements agree:

1. **Source:** the name occurs five times in the branch and four of them are the amount or
   the two prints; the fifth is the assignment. There is no second write.
2. **Execution, P01 vs P08:** `[772, 5]` produced `{"xp": 23}` → `{"xp": 28}` with **one**
   changed leaf, and `[772, 5, 9]` produced `{"xp": 23}` → `{"xp": 28}` with **one**
   changed leaf. **The two post-states are identical**, and so are both leaf sets.
3. **The printed line differs** — `Soldier +5xp` versus
   `Soldier +5xp BOUGHT LEVEL UP -> 9` — which is precisely why the argument is
   *display-only* and why its absence from the post-state is not evidence of a missing
   write.

**Recommendation, and its precedent:** a modern endpoint should **accept and ignore** the
argument, not refuse it. Refusing would reject a request the legacy server accepts and
whose stored effect is nil, and the established pattern in this repository for a
client-supplied value with no stored effect is to ignore it and prove the two- and
three-argument forms reach the same post-state — exactly what M7's `sell` reason and M9's
`research` client level already do. Note also that the argument is **falsy-checked**
(`if level:`), so `0` and `null` take the no-level print while any other value takes the
level-up print; a faithful reproduction would have to model that, and an ignoring endpoint
simply does not care.

**What must not happen:** the argument must never be stored, never displayed as a level the
unit reached, and never used to derive a threshold. §3d established there is no committed
per-unit level schedule for it to be checked against.

---

## 8. Question 7 — which delivered claims are false, and which are already right

**Twelve** delivered locations mention this field — counted by re-reading each one, not
inferred. **Five are false as written and must be corrected** (§8a); **seven are already
correct and must not be touched** (§8b), one of those seven carrying only a
wording-precision item.

> **Correction, recorded during Apply.** §8a enumerated **five** stale locations. The
> delivery found **two more**, so the true count is **seven** — and the two extras are the
> argument for the guard D6 required:
>
> 1. the **sixth**: `apps/client-godot/scripts/town/town.gd:329-330`, which carried the
>    identical false sentence verbatim and which §8a does not list anywhere;
> 2. the **seventh**: `apps/client-godot/scripts/town/level_flow.gd:1`, the module's own
>    first doc line, read *"Unit experience is out of scope because the committed corpus
>    cannot exercise it."* — the same falsehood in the most prominent position in the file,
>    which §8a's search missed because it evidently began below the module header.
>
> The seventh is the one that matters methodologically. Three different readers produced
> five, six, and six: an enumeration does not converge, and the last reader to run found a
> defect in the *first line of the file*. That is why the delivered guard is a **scan** over
> every client source with a pinned expected hit count of **zero**, and not a checklist.
> See §11.

### 8a. False as written — must be corrected

| Location | What it says | Why it is wrong |
| --- | --- | --- |
| `apps/client-godot/scripts/town/level_flow.gd:1` (module doc line) | *"Unit experience is out of scope because the committed corpus cannot exercise it."* | **Found by the delivered scan, not by this investigation — see the correction above.** False for the same reason as the two rows below, and in the most prominent position in the file. |
| `apps/client-godot/scripts/town/level_flow.gd:56-58` (doc comment) | *"`0 of the 40` placed corpus rows carry `attr["xp"]`, and the fresh save carries no unit placements, **so the unit-experience path cannot be exercised**"* | the first two clauses are true; the conclusion is **false**. The path has now been exercised 22 times against an authentic committed village save. |
| `apps/client-godot/scripts/town/level_flow.gd:82-84` (doc comment) | *"**Unit experience** … **is out of scope**: the committed corpus carries no unit placements and no row carrying `attr["xp"]`, so the path cannot be exercised (design D7)"* | false on both counts: the repository's committed evidence has 171 such rows in 5 of 31 saves, and the path has been executed. |
| `apps/client-godot/scripts/town/level_flow.gd:846-848` (the note string returned to the view) | *"unit experience (add_xp_unit) is out of scope **because the committed corpus cannot exercise it**: 0 of the 40 placed rows carry `attr[\"xp\"]` and the fresh save has no unit placements"* | false as written, and it is a **user-facing string**, so the falsehood is on the surface. Note it is **composite**: its continuation at `:848-850` already says tutorial progression is *not* out of scope. So this one string holds a **corrected** tutorial half and a **stale** unit-XP half side by side — the clearest single artefact of the unpropagated supersession. |

Two further prose locations carry the same stale sentence and were **never** updated even
though `production_flow.gd:67-74` says in a comment that it *supersedes* them:

- `AGENTS.md:704-705` — *"**unit XP and tutorial progression are out of scope** because the
  corpus cannot exercise them (0 of 40 placed rows carry `attr["xp"]`; no unit placements
  exist)"*. This is **doubly** stale: tutorial progression was delivered and archived as
  `2026-10-03-tutorial`, which `level_flow.gd:86-92` already says in prose while leaving
  this sentence intact.
- `apps/client-godot/README.md:2115-2116` — the identical sentence.

**So the correction is not one edit. It is three in-code locations, two prose locations,
and the reason the supersession was recorded only in a comment and never propagated.**

### 8b. Already correct — must **not** be changed

| Location | Why it stands |
| --- | --- |
| `apps/client-godot/scripts/units/production_flow.gd:67-74` | already states the sharp version: *"the sharper truth is that **nothing on the server awards it from a trusted value**."* |
| `production_flow.gd:319-323` `CORPUS_XP_NOTE` | already labels the figure correctly: *"asserted by the suite as a measurement and is **a fact about the corpus, not evidence that an award exists**."* |
| `production_flow.gd:865-885` `experience()` | already delivers the read-only, verbatim, **never-awarded** projection — `recorded`, `recorded_is_absent`, `awarded: false`, `award_source`. |
| `test_unit_production.gd:1185-1189` | asserts the corpus measurement **and** qualifies it in the same assertion: *"which is a corpus measurement and never an award."* The assertion is over the fresh corpus's **40** rows (`EXPECTED_ROWS := 40` at `:85`, asserted at `:1142`), so it is **true** — but its message reads *"NOT ONE **committed** row"*, which is broader than its scope and is exactly the phrasing a reader takes for a repository-wide claim. **A wording precision item, not a false claim.** |
| `AGENTS.md:969` / `README.md:2453` (*"no experience is awarded from the recorded `attr["xp`]"*) | true of the delivered client, and unaffected. |
| `collection_flow.gd:252-260` | the refusal's **reason** is the client amount, with the corpus figure as a trailing parenthetical — `collect_xp` unread → `add_xp_unit` takes a client argument → *"already refused by the delivered godot-unit-production requirement"* → `(design D5)`. Correctly ordered; nothing to fix. |

**The conclusion is therefore not "the refusal was wrong."** `godot-unit-production`
anticipated this correction in a code comment and got the reasoning right. What went wrong
is that the supersession **stopped at the comment**, and two prose files still assert a
reason that is false.

---

## 9. The smallest honest bounded change

The evidence supports proceeding, but **not** with a server-derived award. There is no
derivation (§3), and there is no per-unit level schedule (§3d). A modern endpoint that
accepts a client XP amount would be precisely the anti-pattern `AGENTS.md` names:

```python
# Bad: the client dictates an authoritative resource delta.
award_unit_xp(item_index, xp_gain=client_amount)
```

So the honest options are exactly these, and the first is the one the evidence selects:

**Option A — a correction and evidence line (recommended).** Deliver
1. the **evidence correction**: replace all seven stale "out of scope because the corpus
   cannot exercise it" statements — five enumerated in §8a plus two this investigation
   missed, per the correction above — with the measured repository-wide figure and the correct
   reason — *no trusted award exists*, keeping the corpus figure labelled as a corpus fact;
2. the **executed-legacy fixture** for the branch, captured against a committed village
   save, re-runnable, with containment unchanged — which converts "no fixture exists" from
   a corpus limitation into an executed record;
3. a **hardening of the existing `production_flow.gd` projection**: it already reports a
   recorded value verbatim and refuses to award one, and it should now record that the
   field **can be absent, a negative integer, a float, or a string** (all four reachable by
   execution), so a downstream reader fails closed on a poisoned bag rather than assuming
   an integer;
4. **no endpoint, no award, no threshold, no level**, and the existing level-reward refusal
   preserved untouched.

**Option B — a mutating endpoint that refuses the amount.** Implement `/v0/unit_xp` that
accepts an intent and **always** answers `409`, existing only to give the refusal a
network surface. This is *worse* than Option A: it adds a route, a save-shape
expectation and a live phase to express something the client can already be told
locally, and M9 `research` established the precedent that a write-only counter whose only
writer is client-sent does **not** warrant an endpoint.

**Option C — a derived award from `units[].xp`.** **Refused by §3.** Twenty-seven of
fifty-five unit ids carry more than one accumulated value, only 9 of 167 ratios are
integral, and the field has zero legacy consumers. Adopting it would invent an economy and
contradict the committed evidence.

**Option D — defer.** **Weaker than Option A**: the stale claims are *already* wrong in the
repository and will mislead the next reader, and the executed evidence exists whether or
not it is committed.

Recommendation: **Option A**, scoped as one bounded change, with the level-reward refusal
(`reward_type`, `reward_amount`, `level_ranking_reward` — all zero-consumer) explicitly
carried as an untouched, named refusal, and with no award, endpoint, threshold or unit
level introduced.

---

## 10. Established versus derived

**Established from committed source** (occurrence counts over the 11 root modules):
`add_xp_unit` has one occurrence; `attr["xp"]` has two, both writes inside it, and **zero
readers**; `xp_gain` is `args[1]` with no validation; the optional `level` is client-sent
and used only in a `print`; `apply_resources` runs before the dispatch and clamps the
**player's** `xp` at zero; `get_xp_from_level` and `get_level_from_xp` are both dead;
`min_level`, `gift_level`, `collect_xp`, `reward_type`, `reward_amount` and
`level_ranking_reward` have zero legacy occurrences; `units[].xp` is committed on 429/429
units with 24 values and zero consumers; no per-unit level schedule exists in the package;
`version.py` has zero lines mentioning `attr`.

**Established by execution** (22 transactions, 39 server starts, containment unchanged,
loopback only): the increment and assign arms; the missing-row early return that still
answers success; the absence of any clamp, bound, or type check; a float persisted; a
building row accepted; a string persisted on the assign arm and a `TypeError` on the
increment arm; `True` worth +1 XP; `IndexError` for missing arguments; `str(index)`
resolution; the silent no-op for an absent or negative index; the two-leaf move under a
client-sent vector; and the verbatim printed lines including `Wall I +11xp` and
`Soldier +-1000xp`.

**Established by measurement** (31 committed save documents): 171 of 12,954 placed rows
carry `attr["xp"]`, in 5 of 31 documents; all 171 are integers on committed unit ids; all
171 bags contain exactly that one key; 55 distinct unit ids carry it and 27 take more than
one value, the widest being unit `1034` with 24 distinct values inside one save; 167
distinct ratios against `units[].xp` of which 9 are integral; 0 rows equal their save's
player XP; exactly 4 of the 155 distinct values end in `001`.

**Derived** (provisional, reversible): that the deliverable should be a correction plus a
committed fixture plus a hardening of the existing projection, rather than an endpoint;
that the third optional argument should be accepted and ignored rather than refused; that
a village save is an acceptable capture corpus for this line.

**Not established, and not claimed:** what amount the Flash client actually sent in
`args[1]`; whether `units[].xp` was the intended per-award value in a client this legacy
server never received, or something unrelated; why exactly four of the 155 distinct values
end in `001`; whether a unit level exists anywhere in the original game; whether
`collect_xp` should ever pay; and any per-unit XP schedule, threshold or award.
