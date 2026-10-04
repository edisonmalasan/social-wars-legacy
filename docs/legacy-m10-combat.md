# Legacy contract: M10 line 2 — combat actions

**Status:** committed investigation. No implementation is authorized by this
document. Every figure below was measured on `main` at `d437ede` / `9f24739`
with the pinned interpreter (CPython 3.9.13, Windows x64) and the installed Godot
4.7.2.stable. Where a number came from reading rather than execution it says so.

**Scope:** the combat-action surface of the preserved legacy server, and the
correction this surface forces on a merged spec.

---

## 1. The measurement that decides this line's shape

M8's `godot-unit-behaviors` recorded, as the reason no executed-legacy fixture
could be captured:

> `resurrectable` is **unit-only**, the committed corpus places **only
> buildings** and **no unit row**, and its ledger is present and `{}`.

**That is false of the repository.** It is true of
`tests/saves/fresh-player.json` alone, which has 0 committed-unit ids in 40
rows — and this is the *same* delivered-claim defect M9's `unit-experience` line
already corrected once, for `attr["xp"]`.

Measured across every committed save document (11 documents, 3,372 placed rows):

| document | rows | unit rows | team-1 unit rows | team-1 **resurrectable** unit rows | `deadHeroes` before |
| --- | ---: | ---: | ---: | ---: | --- |
| `fresh-player.json` | 40 | 0 | 0 | 0 | `{}` |
| `fresh-player-pre-migration.json` | 40 | 0 | 0 | 0 | `{}` |
| `initial.json` | 40 | 0 | 0 | 0 | `{}` |
| `AcidCaos.json` | 319 | 48 | 48 | 48 | `{}` |
| `General_Mike_30.json` | 436 | 31 | 31 | 31 | `{}` |
| `General_Mike_31.json` | 436 | 31 | 31 | 31 | `{}` |
| `Kiriakos.json` | 569 | 109 | 109 | 109 | **9 keys** |
| `Nerri.json` | 367 | 70 | 70 | 70 | **9 keys** |
| `Neutral.json` | 549 | 87 | 87 | 87 | **29 keys** |
| `Scarlet.json` | 576 | 65 | 65 | 53 | **2 keys** |
| **TOTAL** | **3,372** | **441** | **441** | **429** | |

Four facts follow, and together they invert the line's shape:

1. **441 committed unit rows** are placed, across **7 of 11** save documents.
2. **All 441 are on team 1**, which is the value `push_dead_unit` requires
   (`item[7] != 1` returns `False`).
3. **426 of 429** committed units carry `resurrectable` **inside their
   committed `properties` object** (the key is *absent*, not zero, on 923, 933,
   1176 — which is what §2's third gate tests for), and **0 of 470** buildings
   carry it, so **429** rows satisfy the fourth gate outright.
4. **Five village saves carry a non-empty `deadHeroes` ledger.** `Neutral.json`
   holds 29 keys, `Kiriakos.json` 9, `Nerri.json` 9, `Scarlet.json` 2.

**So M10 line 2 is not a refusal line.** A fixture is capturable against
`AcidCaos.json` (48 ledger-satisfiable rows, empty ledger) and against
`Neutral.json` (87 rows, 28-key ledger) without manufacturing anything.

### 1.1 Where the false claim survives, and where it does not

Every occurrence was read in context before being classified. Three are
correctly scoped and must not be "corrected":

- `AGENTS.md:706` and `README.md:2117` — the M7 XP record says the
  fresh-player facts "are facts about *that* corpus and not about the branch",
  and immediately supplies the repository-wide figures beside them.
- `AGENTS.md:1742` — this **is** the M9 correction, which already established
  that the fresh-player reading is false of the repository.

Four prose locations and one **merged spec** carry the false claim unscoped:

| location | claim | status |
| --- | --- | --- |
| `AGENTS.md:827` | "the committed corpus has no unit row (40 rows, 11 distinct ids, all committed `type` `b` …)" | **false** |
| `README.md:2673` | "the committed corpus holds no unit row (40 placements, 11 distinct ids, every committed `type` `b`)" | **false** |
| `AGENTS.md:1113` | "no unit is placed or moved and the corpus holds no unit row" | **false** (the line's *other* recorded reason still stands) |
| `AGENTS.md:1278` | "the committed corpus places **only buildings** and **no unit row**, and its ledger is present and `{}`" | **false twice** — rows *and* ledger |
| `openspec/specs/godot-unit-behaviors/spec.md:171,173,179` | requirement "No executed-legacy behaviour fixture is claimed": "the committed corpus places **only buildings** and **no unit row**, and its ledger is present and empty, so no resurrectable row exists to exercise" | **false, and contractual** |

The last row is the reason this correction **cannot be deferred**. The false
premise is encoded in a merged requirement's SHALL text *and* in its scenario.
Any sibling capability that captures a combat fixture against a village corpus
would leave two merged specs asserting incompatible things about the same
repository. This is the M8-line-5 precedent — completing the `production` line's
acquisition finding — recurring because the Apply stage disproved the premise.

---

## 2. The combat surface: 4 named branches, 3 engine helpers, 2 real doors

Four of the 63 `command.py` dispatcher branches carry combat names — `kill`
(169), `kill_iid` (183), `resurrect_hero` (625), `end_attack` (808) — but combat
reaches further than its names. Counting occurrences per line over a
quote-stripped view of all eleven root modules (the substring trap already caught
once in this project, so raw-text counts are reported beside code counts):

| helper | definition | call sites |
| --- | --- | --- |
| `map_lose_item` | `engine.py:215` | `command.py:796` (`end_quest`), `command.py:872` (`end_attack`) |
| `push_dead_unit` | `engine.py:149` | `command.py:160` (`sell`, reason guard), `engine.py:223` (inside `map_lose_item`) |
| `resurrect_hero` | `engine.py:172` | `command.py:632` |
| `pop_unit` | `engine.py:58` | `command.py:397` |

So the dead-hero ledger has **four doors**, reached from three branches —
which is what the M9 research line recorded when it corrected the M8 count of
three.

**Two content fields govern the ledger and both are consumed;
`syringes` is not consumed at all.** `resurrectable` has 3 code occurrences
(`command.py:158,160,164`); `syringes` has **zero** occurrences in the eleven
modules. `used_syringe` is read at `command.py:630` and discarded, so **no
syringe cost is ever charged** — the M8-line-8 finding, re-measured here.

**`KILL` is never compared by the dispatcher.** It appears at five
`constants.py` lines only (`962, 995, 996, 1046, 1047`); `command.py:159`
compares the **string literal** `"KILL"`. The constant is unread.

---

## 3. `end_attack` — the combat-resolution branch, and the most dangerous one

`command.py:808-884`. The request carries a **client-supplied JSON blob** at
`args[0]`; `args[1]` is read into `unknown` and never used. On a parse failure
the branch's bare `except:` prints and returns (probe **P3c**: save untouched).

Eleven keys are read from the client blob (`command.py:839-862`). **Seven reach
nothing at all:**

| key | fate |
| --- | --- |
| `victim_units` | read, **discarded** |
| `resources_victim` | read, **discarded** |
| `attacker` | read, **discarded** |
| `resources` | read, **discarded** |
| `honor` | read, **discarded** |
| `duration` | read, **discarded** |
| `townhall_gold` | read, **discarded** |
| `different_island` | read, **discarded** |
| `win` | reaches a `print` only |
| `victim` | `victim["name"]` reaches a `print` only |
| `attacker_units` | **the sole mutation path** |

The branch carries three of its own TODOs: *"Parse more data in the future"*,
*"Affect victim player save"*, *"Attack logs"*.

The whole write is `command.py:866-872`:

```python
for unit in attacker_units:
    # item_id (not on map), sent_to_battle, A, B
    lost = max(0, unit[2] - unit[3])   # number of loses is A - B
    if lost > 0:
        item = unit[0]
        print(f"Lost {lost} {get_name_from_item_id(unit[0])}(s)")
        map_lose_item(map, privateState, unit[0], lost)
```

`unit[0]` (which item), `unit[2]` and `unit[3]` (how many) are **all
client-supplied**, and the destruction count is computed **on the client** with
the server subtracting two numbers it never validates. This is the identical
anti-pattern the M9 `quests` line found in `end_quest` and refused — and the M9
line's recorded divergence is that the legacy server destroyed a placed row
(`40 → 39`) where the modern endpoint derives `units: []`.

`map_lose_item` then loops `qty` times, each pass taking the **first** row whose
`row[0] == item` and whose `row[7]` is **truthy**, popping it, and calling
`push_dead_unit`. It `return`s as soon as one pass finds no match.

### 3.1 The team asymmetry, and why it is *not* exercisable

`map_lose_item` accepts **any truthy** `row[7]`; `push_dead_unit` records only
`row[7] == 1`. So a team-3 *unit* row would be destroyed yet never enter the
ledger. **All 441 committed unit rows are team 1**, so that case **cannot be
reached from the committed corpus**. It is recorded as a real code asymmetry and
a recorded gap — not as a captured behaviour, and not as something to
manufacture a row for.

### 3.2 The emergent clamp

The bound on destruction is **not** a check. It is the exhaustion of matches:
`lost = 9999` against an item with 2 placed rows destroyed **exactly 2**
(probe **P4**, identical to P1). A player holding 400 of one unit id could be
made to lose all 400 by a single client-sent tuple.

---

## 4. Executed-legacy probes

Eight probes plus three variants, run against the **executed legacy
`do_command`** in a disposable directory: a temp tree whose `saves/` holds a
single copied village, with junctions to the repository's read-only data
directories, the repository root on `sys.path`, and `cwd` set to the disposable
tree so `bundle.SAVES_DIR` (`./saves`) resolves inside it. The tree is removed
after every probe. Each probe reports a full leaf-level diff of the save.

One harness lesson, recorded because it produced a wrong reading once: the
first harness printed its result marker on **stdout**, and the legacy loader's
own unterminated `print(..., end='')` interleaved with it, so probe **P2**
reported `NO RESULT` and its real outcome was unknown. The result marker now
goes to a **file**, which cannot be interleaved, and stderr is captured whole.
The lesson generalizes: a result channel shared with the code under test is not
a result channel.

| probe | request | exception | save mutated | rows | `deadHeroes` |
| --- | --- | --- | --- | ---: | --- |
| **P1** | `end_attack`, `attacker_units=[[1007,1,3,1]]` | none | **yes** | **319 → 317** | `{}` → `{'1007': 2}` |
| **P2** | `end_attack`, `attacker_units` **omitted** | `TypeError: 'NoneType' object is not iterable` | **no** | 319 | `{}` |
| **P3** | `end_attack`, `victim` **omitted** | `TypeError: argument of type 'NoneType' is not iterable` | **yes** | **319 → 317** | `{}` → `{'1007': 2}` |
| **P3b** | `end_attack`, `attacker_units: []` | none | **no** | 319 | `{}` |
| **P3c** | `end_attack`, `args[0]` unparseable | none (bare `except` swallows it) | **no** | 319 | `{}` |
| **P4** | `end_attack`, `lost = 9999` | none | **yes** | **319 → 317** | `{}` → `{'1007': 2}` |
| **P5** | `kill [772, 'COMBAT']` | none | **yes** | 319 → 318 | **`{}` — untouched** |
| **P6** | `sell [772, 'KILL']` | none | **yes** | 319 → 318 | `{}` → `{'1007': 1}` |
| **P7** | `kill_iid [1007, 'COMBAT']` | none | **no** | 319 | `{}` |
| **P8** | `resurrect_hero [900, 1001, 41, 42, 1]` vs `Neutral.json` | none | **yes** | 549 → **550** | `1001: 28 → 27`, other 27 keys untouched |

P1 removed **14** leaves across **two** distinct map keys (772 and 1408) — both
rows of item `1007`, since `map_lose_item` takes the first match per pass. The
ledger increment of 2 records both.

### 4.1 The ordering finding, which is the sharpest one

**P2 raises before mutating; P3 raises after mutating.** Both are the same
unguarded `None` dereference, but they sit on opposite sides of the write loop:

- `command.py:866` `for unit in attacker_units` — reached **before** any
  destruction, so P2 leaves the save byte-identical.
- `command.py:874` `if "name" in victim` — reached **after** the loop, so P3
  leaves the save **already destroyed** (2 rows gone, ledger incremented) and
  *then* raises.

Any endpoint must therefore validate `victim`'s presence **before** the
destruction step, not after, or it reproduces a partially-applied save on a
refusal path. This is the same ordering discipline the M9 `quests` line applied
to `end_quest`.

### 4.2 P8 is the direct disproof of the delivered claim

`resurrect_hero` against `Neutral.json`'s committed ledger: one ledger key
decremented `28 → 27`, one new row added at the **client-supplied** key 900 with
the **client-supplied** cells `(41, 42)`, and the other **27** ledger keys
byte-identical. Six leaves added, one changed, none removed. The surviving
non-refusal claim is narrow and holds: `used_syringe` is read and discarded, so
**no resource moves and no syringe cost is charged**.

---

## 5. What M8 line 8 already owns, and the boundary this line must respect

`godot-unit-behaviors` delivered the ledger projection, its four gates, the
three-door command inventory, and the `resurrect_hero` revival intent. The
merged spec mentions `map_lose_item` and **not** `end_attack` or `kill_iid`;
no other delivered spec mentions any of the three.

So:

- **Re-delivered already, must be referenced not reimplemented:** the ledger
  projection, the four gates, the `resurrect_hero` decrement and re-placement,
  the absent syringe cost.
- **New to this line:** `end_attack`'s destruction path, `kill`, `kill_iid`,
  and the `sell`-with-`"KILL"` door *as the request shapes they actually take*.
- **Corrected by this line:** the false corpus claim, in four prose locations
  and one merged spec.

`godot-mission-vocabulary` remains the owner of the 64 `MISSION_*` declarations,
of which this surface names `MISSION_ATTACK_PLAYER` (37),
`MISSION_ASSAULTS_WON` (46), `MISSION_KILLED_ENEMY` (67),
`MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT` (63) and others.
**None is dispatched, and this line dispatches none of them** — the vocabulary is
the statement of what combat must resolve, and resolving it is a later line.

---

## 6. Measured content fields, and a second discrepancy with a merged record

`resurrectable` is the **only** combat-adjacent committed field with a legacy
consumer, and its consumer is a mutation of private state rather than a read.
It is **nested inside the committed `properties` object**, not a top-level key —
the top-level count is **0**, and this is the same trap the M9 `quests` line
recorded for `harvester`.

Measured across all eleven root modules under two counting rules — *raw* (every
match in the file text, strings and comments included) and *code* (matches on a
quote-stripped, comment-trimmed view) — with occurrence counts, distinct-line
counts, and committed presence reported separately:

| field | raw occ. | code occ. | lines | units (top level) | units (in `properties`) | buildings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `resurrectable` | 5 | **3** | 3 | 0 | **426 / 429** | **0 / 470** |
| `syringes` | 0 | **0** | 0 | **429 / 429** | 0 | **470 / 470** |
| `attack` | 12 | 5 | 5 | 429 | 0 | 470 |
| `defense` | 0 | **0** | 0 | 429 | 0 | 470 |
| `life` | 0 | **0** | 0 | 429 | 0 | 470 |
| `min_level` | 0 | **0** | 0 | 429 | 0 | 470 |
| `attack_interval` | 0 | **0** | 0 | 429 | 0 | 470 |
| `attack_range` | 0 | **0** | 0 | 429 | 0 | 470 |
| `best_against` | 0 | **0** | 0 | 429 | 0 | 470 |
| `best_against_mult` | 0 | **0** | 0 | 429 | 0 | 470 |
| `max_frame` | 0 | **0** | 0 | 429 | 0 | 470 |
| `velocity` | 0 | **0** | 0 | 429 | 0 | 470 |

**`syringes` is the sharpest line in this table**: it is carried on **every one
of the 429 units and every one of the 470 buildings** and read by **nothing**.
`resurrectable`'s absence is an **absent key**, not a zero, on ids 923, 933,
1176 — which is exactly what `push_dead_unit`'s third gate tests for — and on
**all 470** buildings.

### 6.1 Five figures in the M8 record that this measurement cannot reproduce

M8 line 8 recorded: "`attack` 131 distinct, `defense` 1, `life` 150,
`min_level` 21, `syringes` 6". Each was re-measured under every counting rule
that could plausibly produce it:

| field | M8 recorded | raw | code | lines | units top | units in `properties` | reproduces as |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `resurrectable` | 426 | 5 | 3 | 3 | 0 | **426** | **units-in-`properties`** |
| `attack` | 131 | 12 | 5 | 5 | 429 | 0 | **nothing measured** |
| `defense` | 1 | 0 | 0 | 0 | 429 | 0 | **nothing measured** |
| `life` | 150 | 0 | 0 | 0 | 429 | 0 | **nothing measured** |
| `min_level` | 21 | 0 | 0 | 0 | 429 | 0 | **nothing measured** |
| `syringes` | 6 | 0 | 0 | 0 | 429 | 0 | **nothing measured** |

**This does not weaken M8's conclusion — it strengthens it.** M8 recorded these
fields as having zero or near-zero legacy consumption; this measurement finds
**exactly zero** for four of them, and for `syringes` finds zero against a
committed presence of 429 units and 470 buildings. The **direction** of the
delivered claim holds.

What does not hold is the **figures**. Four of the five reproduce under no
counting rule applied here. The most likely explanation — offered as a
**hypothesis, not a finding** — is that M8 counted matches over a wider corpus
than the eleven root legacy modules, such as the committed content package or
the delivered documentation, which would inflate every figure. That was not
measured, because measuring it is not this line's business and guessing at it
would be exactly the error being recorded.

**Recorded as a discrepancy, not corrected here.** The delivered M8 record is
not edited by this investigation; a later line that owns those fields should
either reproduce the figures under a stated rule or amend them. Carrying an
unreproducible number forward because "it was already written down" is the same
failure this project has now caught three times — the `units[].xp` award source,
the `harvester` field shape, and the corpus claim in §1.


---

## 7. Claim limits this investigation itself carries

- **Probes ran against the executed legacy `do_command`, not the HTTP
  endpoint.** No endpoint response shape is established here; that is the Apply
  stage's work.
- **The corpus coverage is 2 of 7 usable village documents** for the mutation
  probes (`AcidCaos`, `Neutral`), and **7 of 11** for the inventory. No
  progressed-player HTTP capture exists, and none is claimed.
- **`P2`'s first harness result was lost to stdout interleaving** and the
  reported value in that run was not a behaviour. The table above reports only
  the file-marker re-run.
- **`P3c` sent `args[0] = null`**, so the bare `except:` caught a `TypeError`
  from `json.loads`, not a malformed *string*. A malformed string takes the same
  branch; that equivalence is **read from the source**, not executed.
- **The team-3 asymmetry is a recorded gap, not a captured behaviour** — no
  committed unit row is on a team other than 1.
- **No probe establishes what the Flash client actually sent.** Every request
  shape here is **derived**, never observed, exactly as `proposal`-stage
  derivations are recorded elsewhere in this project.
- **`kill_iid`'s emptiness is established for this corpus and this request
  shape only.** The branch has no write statement at all, which is stronger, but
  the branch's *intent* is unknown.
- **No damage, no health, no combat arithmetic is delivered, measured, or
  claimed.** `lost` is a count of *rows removed from the map*, not a damage
  number, and the field it arrives in (`unit[2] - unit[3]`) is a client
  subtraction with no meaning established anywhere in the preserved source.

### 7.1 Containment, including one failure

The repository was **not** written to. Verified after the probe run: no
working-tree `saves/` directory exists, and `git status` showed exactly one
entry — this document. Every probe ran in a temp tree with junctions to the
repository's read-only data directories and its `saves/` holding a single copied
village; the tree was removed after each probe with `rmdir /S /Q`, which removes
the junction rather than following it.

**One probe directory leaked and was removed.** The *first* harness run aborted
on `OSError: [WinError 1314]` — Windows symlinks require elevation the session
does not hold — and it aborted inside `setup()`, *before* the cleanup path existed,
leaving `m10-combat-probe-5ljup605` in the system temp directory. It was
detected by the post-run sweep and removed. Two things are recorded rather than
smoothed over: the leak happened because cleanup was added *after* the first
failure rather than before it, and the retry switched to `mklink /J` junctions,
which need no elevation. A containment guarantee that is established by the
happy path is not a containment guarantee.


---

## 8. What the next stage must decide

A proposal for this line must settle, explicitly and in writing:

1. **Whether a client-dictated `lost` is reproduced or refused.** The M9 `quests`
   line refused `end_quest`'s equivalent and recorded the difference from the
   legacy server as a **divergence**, not parity. Reproducing `end_attack`'s
   would be the `AGENTS.md` "Bad" pattern verbatim.
2. **The ordering**, per §4.1: validation strictly before any destruction.
3. **Which of the eleven discarded keys are reported as read-and-unused**, so the
   non-claims are structural rather than prose.
4. **Whether `kill_iid` is delivered as a proven no-op** or refused outright.
5. **How the `godot-unit-behaviors` spec correction is carried** — as a
   `MODIFIED` requirement on a merged spec, which the workflow treats as a
   semantic merge rather than a new capability.
6. **Whether `kill` and `sell`-with-`"KILL"` are re-delivered** given
   `godot-unit-behaviors` already recorded the three-door inventory, or
   referenced as that capability's territory.

Nothing above is decided here. This document is the contract the proposal is
written against, and it is deliberately explicit about what it does *not* know.
