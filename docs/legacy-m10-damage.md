# Legacy contract: M10 line 3 — damage

**Status:** committed investigation. No implementation is authorized by this
document. Every figure below was measured on `main` at `fdb1f7a` / `d6ca8f2`
with the pinned interpreter (CPython 3.9.13, Windows x64). Where a number came
from reading the source rather than executing it, it says so.

**Scope:** the damage surface of the preserved legacy server — whether it
resolves damage at all, and, finding that it does not, the one combat-effect
surface it does maintain.

---

## 1. The verdict, stated before the evidence

**The preserved server resolves no damage.** Not "no damage code was found" —
a stronger and more useful statement, established in two independent ways in
§2 and §3: no committed field describing damage is read by anything, and
**there is nowhere in a committed save row to store a hit point**.

That refusal is the line's primary finding and it is the same shape as the
M8 refusal lines. But this line is **not** a pure refusal line, because the
investigation surfaced a real, state-mutating, **capturable** combat-effect
surface that no delivered line owns: the **magics ledger counter**, written by
two adjacent dispatcher branches at `command.py:652-674` and read by nothing.

Both halves are recorded below. Neither is inflated to make the line look
larger than it is.

---

## 2. No committed damage field has a legacy consumer

Measured across all **11** legacy root modules (`command.py`, `engine.py`,
`sessions.py`, `server.py`, `constants.py`, `get_game_config.py`,
`get_player_info.py`, `version.py`, `auctions.py`, `bundle.py`,
`legacy_command_recorder.py`) under six independent counting rules, because
M8 line 8 learned that the wrong rule produces a confidently wrong number:

| rule | meaning |
| --- | --- |
| `whole` | whole-file occurrences (substring) |
| `dLine` | whole-file distinct lines |
| `code` | code-only occurrences (comments and string literals stripped) |
| `cLine` | code-only distinct lines |
| `token` | exact standalone identifier token |
| `quoted` | the quoted-access form `"field"` / `'field'` |

| field | whole | dLine | code | cLine | token | quoted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `damage` | 2 | 2 | 2 | 2 | **0** | **0** |
| `attack` | 42 | 38 | 30 | 30 | **0** | **0** |
| `defense` | 0 | 0 | 0 | 0 | 0 | 0 |
| `life` | 0 | 0 | 0 | 0 | 0 | 0 |
| `attack_interval` | 0 | 0 | 0 | 0 | 0 | 0 |
| `attack_range` | 0 | 0 | 0 | 0 | 0 | 0 |
| `best_against` | 0 | 0 | 0 | 0 | 0 | 0 |
| `best_against_mult` | 0 | 0 | 0 | 0 | 0 | 0 |
| `resurrectable` | 6 | 6 | 3 | 3 | 5 | 2 |

**The `code` column is not a consumer count, and this is the trap.** `damage`
shows `code=2` yet `token=0`. Both occurrences are the *substring* `damage`
inside longer identifiers:

```
constants.py:894   COST_DAMAGE_SELF  = "ds"
constants.py:895   COST_DAMAGE_ENEMY = "de"
```

`attack` is the same story at larger scale: all 42 whole-file occurrences sit
inside `end_attack`, `attacker`, `attacker_units`, `flash_reload_attack`,
`ANIMATION_ATTACKING*`, `tsAttacksReset`, and two standalone non-field uses
(`# TODO: Attack logs` at `command.py:824` and the display string
`"reload On End Attack"` at `server.py:297`). **The committed `attack` field is
never read.**

So the six committed damage-shaping fields — `attack`, `defense`, `life`,
`attack_interval`, `attack_range`, `best_against`, `best_against_mult` — have
**zero** legacy consumers. This **confirms and extends** the M8 line-8 finding
rather than contradicting it.

`resurrectable` is the control: it is the one field on this list that *does*
have code-bearing consumers (`command.py:159,162` plus `engine.py`), and its
non-zero `token`/`quoted` columns are exactly what a real consumer looks like.
It is already owned by the merged `godot-unit-behaviors` capability and is
**referenced, not reimplemented**, by this line.

### 2.1 The two `COST_DAMAGE_*` constants

`COST_DAMAGE_SELF = "ds"` and `COST_DAMAGE_ENEMY = "de"` are declared at
`constants.py:894-895` and have **zero occurrences anywhere in the 11 modules**
outside their own declaration. They are a resource-cost vocabulary with no
consumer — the same shape as `COST_ENERGY` / `TOKEN_ENERGY` / `CAT_ENERGY`,
which M7's resource line already recorded as declared-but-never-read.

They are **reported and never used**. A cost token for self-damage and one for
enemy damage is the closest surviving statement of a damage model the server
ever had, and it is a two-letter string with nothing behind it.

---

## 3. There is nowhere to store damage — the decisive measurement

§2 establishes that nothing *reads* damage. A stronger fact closes the line:
nothing could *write* it either, because the committed row shape has no slot
for it and the attribute bag has no key for it.

Measured over every placed row of every canonical committed save document
(**10 documents, 3,372 placed rows**):

| measurement | value |
| --- | --- |
| documents walked | 10 (8 under `villages/`, 2 under `tests/saves/`) |
| placed rows | **3,372** |
| distinct row lengths | **`{8: 3372}`** — every row is exactly 8 slots |
| slot 0 | `int` on all 3,372 |
| slot 1 | `int` on all 3,372 |
| slot 2 | `int` on all 3,372 |
| slot 3 | `int` on all 3,372 |
| slot 4 | `int` on all 3,372 |
| slot 5 | `list` on all 3,372 |
| slot 6 | `dict` on all 3,372 |
| slot 7 | `int` on all 3,372 |

The row shape is `[item, x, y, timestamp, orientation, garrison, attr, team]`.
Slot types are **fixed across every row in the repository** — there is no
per-row variation to repurpose.

The complete union of `attr[]` bag keys across all 3,372 rows:

| `attr` key | rows carrying it |
| --- | ---: |
| `cp` | 28 |
| `nu` | 1 |
| `si` | 53 |
| `ts` | 1 |
| `ui` | 1 |
| `xp` | 171 |

**No `hp`, `health`, `damage`, `dmg`, `armor`, `shield`, `life`, or `wound` key
exists in any row's attribute bag**, and **no `privateState` key in any of the
10 documents matches** `hp|health|damage|dmg|armor|shield|life|wound`.

This is why the refusal is a statement about the *shape of the data* rather than
a shrug about missing code. A damage system would need a field to hold a
remaining hit point. The committed format does not have one, the server never
added one, and the corpus never contains one. **Any damage value this client
displays would be a value the save does not store.**

---

## 4. The damage vocabulary that *does* exist

Three attack-named things survive, and all three are inert. They are recorded
because they are the only surviving statement of what a damage system was
supposed to do, and because a later line wanting to implement combat needs to
know they were checked.

### 4.1 `tsAttacksReset` — a new zero-consumer field

```
command.py:919   privateState["tsAttacksReset"] = max(0, privateState["tsAttacksReset"] - seconds)
```

**Exactly one occurrence in all 11 modules**, and it is a write inside
`fast_forward`. Its sibling on the next line, `tsSpyingsReset`, is identical and
also has exactly one occurrence. **Neither has a single reader.**

The name implies a daily attack allowance — the field a legacy attack-limit
check would have compared against. **No such check exists.** The instant is
therefore client-writable (any client can subtract from it via `fast_forward`)
and trusted by nothing.

### 4.2 `buy_mana_new` — a branch that does nothing, by its own comment

```
command.py:649   elif cmd == "buy_mana_new":
command.py:650       print("Bought mana") # Nothing needs to be done here :)
```

A named dispatcher branch whose entire body is a `print` and whose author's own
comment says the work was never done. It is **not** damage, but it is the third
member of the `{buy, use}_*` vocabulary family and is recorded with the other
two.

### 4.3 The `MISSION_*` combat types

M10 line 1 delivered all **64** `MISSION_*` declarations and recorded that they
have **zero** consumers. The damage-shaped members —
`MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND` (38),
`MISSION_ASSAULTS_WON` (46), `MISSION_KILLED_ENEMY` (67),
`MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT` (63) — are
**referenced, not reimplemented**, by this line, and the type-to-building mapping
remains owned and unused.

---

## 5. The one real combat-effect surface: the magics ledger

### 5.1 The two branches

```
command.py:652   elif cmd == "buy_magic":
command.py:653       magic_id = args[0]
command.py:656       magics = privateState["magics"]
command.py:657       if str(magic_id) in magics:
command.py:658           magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)
command.py:659       else:
command.py:660           magics[str(magic_id)] = 0
command.py:662       print("Bought magic spell")

command.py:664   elif cmd == "use_magic":
command.py:665       magic_id = args[0]
command.py:668       magics = privateState["magics"]
command.py:669       if str(magic_id) in magics:
command.py:670           magics[str(magic_id)] = min(50, magics[str(magic_id)] + 1)
command.py:671       else:
command.py:672           magics[str(magic_id)] = 0
command.py:674       print("Used magic spell")
```

These two branches are four lines apart and are **not interchangeable**:

- `buy_magic` uses **`+=`**: it *adds* `min(50, x + 1)`. The result is **not**
  bounded by 50. It grows without limit.
- `use_magic` uses **`=`**: it *assigns* `min(50, x + 1)`. That is an absolute
  clamp, so it can **decrease** a counter already above 50.

Reading the source strongly suggests this; only execution settles it.

### 5.2 Executed probe — the asymmetry is real

Run against the **real preserved Flask server** in a disposable copy seeded from
`villages/Neutral.json`, the only committed corpus whose `privateState.magics`
is non-empty. Both arms were driven against **the same counter key `1`** and
deliberately interleaved, so the divergence reads as one sequence:

| # | command | ledger key `1` before | after | verdict |
| ---: | --- | ---: | ---: | --- |
| — | (seed) | — | `2` | committed corpus value |
| 1 | `use_magic [1]` | 2 | **3** | `min(50, 2+1) = 3` |
| 2 | `buy_magic [1]` | 3 | **7** | `3 + min(50, 4) = 7` |
| 3 | `buy_magic [1]` | 7 | **15** | `7 + 8` |
| 4 | `buy_magic [1]` | 15 | **31** | `15 + 16` |
| 5 | `buy_magic [1]` | 31 | **63** | **crossed 50** |
| 6 | `buy_magic [1]` | 63 | **113** | **still climbing** |
| 7 | `use_magic [1]` | 113 | **50** | **the counter DECREASED** |
| 8 | `use_magic [1]` | 50 | **50** | unchanged (`min(50, 51) = 50`) |

Every request answered HTTP **200** with `{"result": "success"}`.

**Confirmed by execution:**

1. **`buy_magic` is unbounded.** It passed 50 and reached 113, and would keep
   adding 50 per request. The `50` is not a cap on this arm.
2. **`use_magic` can destroy spells.** Step 7 turned **113 owned spells into
   50**. "Used magic spell" *removed* 63 charges.
3. Neither branch charges anything (§5.4).

### 5.3 The id is unvalidated and untyped

Driven against the same disposable corpus:

| # | command | ledger before | ledger after | verdict |
| ---: | --- | --- | --- | --- |
| 9 | `use_magic [3]` | 5 keys | **6 keys** | absent id **created at `0`** |
| 10 | `buy_magic [99]` | 6 keys | **7 keys** | id outside the committed 10-entry table **accepted**, created at `0` |
| 11 | `use_magic ["1"]` | 7 keys | 7 keys | string id resolves to the same key |
| 12 | `use_magic [1.0]` | 7 keys | **8 keys** | a float id creates the **distinct key `"1.0"`**, separate from `"1"` |

Step 12 is the sharpest: `str(1.0)` is `'1.0'`, so a client sending `1.0`
instead of `1` silently gets a **second, unrelated ledger entry**. And step 10
shows the server never checks the id against the committed magic table at all —
`99` is not a spell.

### 5.4 No price is charged, and no effect is applied

The probe compared **8 resource slots** (`gold`, `wood`, `oil`, `steel`,
`cash`, `xp` from the map; `mana`, `energy` from `privateState`) before and
after all twelve requests.

> **resource slots compared: 8 — moved: NONE**

`mana` stayed at **15** through a `use_magic`. Using a spell costs nothing.
Neither branch debits gold, cash, or mana, and neither writes any other key —
`privateState` outside `magics` is byte-identical.

### 5.5 The ledger has zero readers, so the committed magics content is inert

```
command.py  6 sites  (lines 656, 657, 658, 660, 668, 669, 670, 672 — all writes)
version.py  4 sites  (lines 32-37)
```

`version.py:32-37` is a **migration, not a reader**: it coerces a missing or
non-dict `magics` to `{}`.

> ```
> version.py:32   if "magics" not in privateState:
> version.py:33       privateState["magics"] = None
> version.py:34   if type(privateState["magics"]) != dict:
> version.py:36       privateState["magics"] = {}
> version.py:37   print(" [!] Applied magics fix")
> ```

**Zero read-like sites exist.** Every ledger subscript in the codebase is an
assignment. This yields a stronger conclusion than any field count: because
**nothing ever reads the ledger**, **no committed magics field can be consumed
at all** — there is no code path from the content to any behaviour.

Confirmed directly against the committed content
(`packages/game-content/normalized/magics.json`, **10 entries**): the fields
`area`, `kind`, `img_name`, and `description` have **zero** code-only
occurrences across the 11 modules, and the non-zero counts for `target` (4),
`level` (8), `mana` (2), `gold` (4), and `cash` (5) are all **unrelated
contexts** — `target = destination / (name + ".json")` in the command recorder,
`map["level"]` in the XP branch, `mana = resource[7]` in `engine.py`, and so on.
**Not one of them touches magics.**

### 5.6 The committed magics carry no damage amount

The 10 committed magics are `AirStrike`, `Medic Case Rain`,
`Protection Shield`, `Nuclear Bomb`, `Shortcircuit Inductor`, `Magnetic Trap`,
`Mech Summoner`, `Stealth Sneak`, `Alien Abduction`, `Attack Boost`. Their
numeric fields are exactly `mana`, `level`, `gold`, `cash`, `target` — **there is
no damage, multiplier, magnitude, radius, or duration field**.

`Attack Boost` is the decisive one. Its description reads *"Your units will
increase their attack and life to wreak havoc on enemies!!"* and its committed
numbers are `mana: 10, level: 35, gold: 10000, cash: 30, target: 1`. **The
magnitude of the boost is not committed.** Nothing states how much attack or
life is added.

**This is the cleanest possible statement of the line's finding:** the game's
damage vocabulary exists as names, strings, and prices, and the single number
that would define a damage amount — the Attack Boost multiplier — **was never
committed and never read.**

### 5.7 The `50` is a bare literal, not derived from content

The cap appears only at `command.py:658` and `command.py:670`. The number `50`
**does** occur among the committed magics values — as `AirStrike.cash = 50` and
`Shortcircuit Inductor.level = 50` — but it appears in the source as a literal
in a `min()` call with no reference to content whatsoever.

**It is not derived from anything.** Recording it as content-derived would be
exactly the "silently inventing a derivation" failure this project treats as a
defect. It is recorded as a **hardcoded literal in the preserved source**.

---

## 6. Capturability

**`villages/Neutral.json` is the only committed corpus with a non-empty magics
ledger**, so this surface is genuinely capturable against committed data —
unlike the combat line's need for `AcidCaos`/`Neutral`, this needs only one
document.

| corpus | `privateState.magics` |
| --- | --- |
| **`Neutral.json`** | **`{'10': 0, '9': 1, '1': 2, '2': 0, '4': 2}`** |
| `AcidCaos.json` | `{}` |
| `General_Mike_30.json` | `{}` |
| `General_Mike_31.json` | `{}` |
| `Kiriakos.json` | `{}` |
| `Nerri.json` | `{}` |
| `Scarlet.json` | `{}` |
| `initial.json` | `{}` |
| `fresh-player.json` | `{}` |

Twelve transactions were executed against it in one disposable runtime with one
server, and are re-runnable.

---

## 7. Corrections to my own measurements

Four errors were made and caught during this investigation. All four are
recorded because each would have shipped a wrong figure into a spec.

**1. The first six-rule probe flagged `damage`, `armor` and `shield` as having
code-bearing consumers.** They do not. My probe's pass/fail flag treated a
code-only *substring* hit as a consumer, so `COST_DAMAGE_SELF` counted as a
`damage` consumer. The `token` column (`0`) was the correct signal all along.
Fixed by adopting `token or quoted` as the consumer test and by requiring a
code-bearing rule.

**2. My first row-shape walk reported "33 documents, 13,034 rows."** That was
wrong. The walk had recursed into `tests/fixtures/**` step documents *and* into
a Godot build cache at `apps/client-godot/.godot/verify/content/`. The canonical
figures are **10 documents, 3,372 rows**. The 3,332 the corrected 9-document walk
reported plus the 40 rows of the excluded `fresh-player-pre-migration.json`
reconcile exactly to 3,372, which is how the discrepancy was confirmed rather
than assumed away.

**3. I nearly recorded the `50` cap as content-derived**, because 50 does appear
among the committed magics values. Probing *which* field carried it showed it is
`AirStrike.cash` and `Shortcircuit.level` — a coincidence of the value
distribution. It is a bare literal (§5.7).

**4. My branch-count regex found 62 dispatcher branches; the project's own
`tools/command-catalog/verify_commands.py` reports `command_branches: 63`.** The
regex was the wrong instrument and its figure was discarded.

**A methodological note.** Three of the four errors came from an instrument
rather than from a reading. This project has a live precedent for that class of
defect (M9's `unit-experience` byte-count guard, which compared `st_size` and so
passed on an LF checkout), and the standing remedy applies here too: **a
counting script must be shown to count what it claims.** The 33/13,034 figure was
caught only because the corrected run disagreed with it.

### 7.1 Corrections found during implementation

Three further errors were found by the Apply stage and are recorded here rather
than by quiet edits above. All three were reported by the implementation
subagent, and all three were **independently re-measured** before being accepted.

**5. §5.5 contradicts itself on the ledger's site count.** It reads
`command.py 6 sites` and then lists **eight** lines (656, 657, 658, 660, 668,
669, 670, 672). The eight lines are correct and the "6" is wrong, but the
sentence as written is self-contradictory. The precise decomposition, which is
what the delivered module reports, is **four assignment statements, six
subscript occurrences** (the two assignment lines carry two each), **two
membership tests** (`if str(magic_id) in magics`), and **two local bindings** of
the ledger. Collapsing those four shapes into one number is what made the
sentence ambiguous in the first place.

**6. `config["magics"]` is a `list`, not a `dict`.** Measured: ten rows with
native `id` values `1..10`. Nothing in this investigation depends on the
difference — identity validation resolves a row by its native `id` — but the
delivered `is_committed_magic()` reads the loaded shape rather than assuming a
mapping, so the distinction is recorded here to keep the two in step.

**7. `get_game_config.py` has zero occurrences of `magic`, case-insensitively.**
This record asserted the committed magics content had no legacy consumer; that
holds, and this measurement is the direct confirmation from the module that
serves content. It was worth stating because it was previously an inference from
absence in the dispatcher rather than a count in the serving module.

**Correction 4 recurred, and that is the finding worth keeping.** The
implementation's own branch-count regex measured **62** where the catalog reports
**63**, for the *same* reason as before: the identifier character class was
`[A-Za-z_]+`, with **no digits**, and `push_queue_unit2` ends in `2`. I had
recorded the original error and then made it again a few days later while
writing the derivation, which is direct evidence that recording a correction is
not the same as preventing the class. `branch_count_agrees_with_catalog()` now
guards it mechanically in both the Python envelope and the GDScript projection,
and both suites re-derive the count on every run.

### 7.2 A measurement of mine that was false outright

While designing the post-execution proof I asserted that the legacy `use` arm and
the service's derived transition "agree only at a recorded counter of zero."
**That is false.** Measured over the whole legal domain, they are *literally the
same formula* `min(cap, x + 1)` and they agree at **every** counter from 0 to 50.
The entire divergence is about `buy` (which adds that quantity, so the legacy arm
is unbounded) and about the absent-key `else` arm (both write `0`, while the
derived transition gives `1`). The endpoint therefore reports `derived_after`,
`recorded_after` and `legacy_expected_after` side by side and states
`matches_derived` plainly, rather than asserting equality that would fail on five
of seven successful steps.

---

## 8. What the implementation line must and must not do

Recorded here as the contract this document exists to establish. **The proposal
owns the design; these are the boundaries the evidence sets.**

### Must not

- **Resolve, compute, apply, or store damage.** No such mechanism exists to
  reproduce, and no committed amount exists to derive one from (§3, §5.6).
- **Charge a price** for a spell. The probe measured all 8 resource slots
  unchanged (§5.4), so a price would be invented.
- **Reproduce the unbounded `buy_magic` growth.** The legacy arm grows past 50
  without limit (§5.2); reproducing that would ship a defect as parity.
- **Reproduce the `use_magic` decrease.** `113 → 50` destroys 63 owned charges
  on a command whose printed message claims the opposite (§5.2). This is a
  divergence to record, never parity — the same reasoning M10 line 2 applied to
  the legacy `max(0, sent - survived)` destruction count.
- **Accept arbitrary ids.** The legacy server accepts `99` and the float `1.0`
  (§5.3), creating keys outside the committed 10-entry table. Refusing them is
  the Server v1 / M13 authority this project wants, and the difference is a
  recorded divergence.

### Must

- Deliver the **server-derived counter transition**: the client sends only a
  magic id, the server derives the transition. Never a client-sent count.
- Validate the id against the **committed 10-entry magic table**, refusing an id
  outside it.
- Carry a **two-part post-execution proof**, in the form M10 line 2 established:
  the counter changed by **exactly** the derived delta, **and** every stored
  resource is unchanged. The second half is what makes the no-price claim
  non-tautological — §5.4 measured all 8 slots, so the proof must compare all 8.
- Re-derive the **12 client blob keys** and the 63-branch count from
  `command.py` **as bytes** on every run (design D4 from the combat line), so a
  legacy edit fails the suite instead of silently contradicting it.
- Report the **committed magics content verbatim** — 10 entries, their `mana`,
  `level`, `gold`, `cash`, `target` — and **derive nothing from it**. In
  particular, do not derive a cap from `AirStrike.cash`, and do not invent the
  Attack Boost multiplier the commit never made.
- Report, never use: `COST_DAMAGE_SELF`, `COST_DAMAGE_ENEMY`, `tsAttacksReset`,
  `tsSpyingsReset`, `buy_mana_new`, and the `MISSION_*` combat types.

### Cap semantics

The `50` must be delivered as the **recorded literal** it is, with the recorded
rejection of deriving it from content (§5.7). Whether the modern cap applies to
*both* actions — where the legacy server applies it to neither — is a design
decision for the proposal, and the divergence must be recorded either way.

---

## 9. Claim limits

- **No damage is resolved, and none is claimed.** The refusal is about the
  preserved server. It says nothing about what the Flash client displayed, and
  **no pixel-parity oracle exists**.
- **No magic effect is applied.** `use_magic` increments a number. Nothing
  happens to any unit.
- **Coverage is 1 of 10 committed magics** (id `1`, AirStrike, whose ledger
  entry the probe drove from `2` to `50`). The other nine ledger keys were
  observed in the corpus but not driven. The two branches are type-agnostic
  over ids, so the transition shape is shared, but **no per-magic behaviour is
  claimed** — and none exists to claim.
- **Parity covers 12 recorded transactions against one committed corpus**
  (`villages/Neutral.json`). No progressed-player save with a different ledger
  shape is exercised.
- **The recorded `buy_magic` / `use_magic` divergence is between two legacy
  arms**, not between legacy and modern. The proposal must not present the
  legacy-vs-modern differences in §8 as parity with either arm.
- **`tsAttacksReset` implies a daily attack allowance that no code enforces.**
  The inference about intent is **derived from the field's name only**, and no
  allowance limit, window, or reset rule is claimed.
- **No windowed capture**, because nothing is rendered by this line.
- No Flash, Ruffle, ActionScript, or browser executes in any command here, and
  every network call was loopback (`127.0.0.1:5055`).

---

## 10. Relationship to the already-delivered lines

| owned by | surface |
| --- | --- |
| `godot-combat-actions` (M10 line 2) | `end_attack`, `kill`, `sell`, `kill_iid`, `resurrect_hero`, `deadHeroes` |
| `godot-mission-vocabulary` (M10 line 1) | all 64 `MISSION_*` declarations |
| `godot-unit-behaviors` (M8 line 8) | `resurrectable`, `attr["nc"]`, `syringes` |
| `godot-unit-queues` (M8 line 3) | `attr["nu"]`, `attr["ts"]`, `attr["ui"]` |
| `godot-building-construction` (M7) | `attr["cp"]`, `clicks_to_build` |
| **`this line`** | **`buy_magic`, `use_magic`, the `magics` ledger, the damage refusal** |

`attr["si"]` (53 rows) and `attr["xp"]` (171 rows) are **already owned** by
`godot-unit-instances` and `godot-unit-experience` respectively. This line
touches none of them; they appear in §3 only as evidence that the bag has no
damage key.

**`tsAttacksReset` would be the eleventh zero-consumer committed field in this
project**, after `unit_capacity`, `max_frame`, `velocity`, `training_time`,
`harvester`/`collect`, the unread level-curve reward fields, `unlockedQuestIndex`,
and the tutorial flag's inert counterpart set.
