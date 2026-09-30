# Legacy investigation: XP basics

Status: **investigation complete; the server-side contract is ESTABLISHED and the
client-owned part is bounded, with one off-by-one that the committed corpus decides.**
This record exists so the final bounded M7 change — *XP basics* — is proposed against
verified evidence, and so the index-base question is answered by evidence rather than
by a guess that would silently shift every level.

## What "XP basics" can and cannot mean here

The roadmap's M7 deliver list ends with **XP basics**, and its exit criterion is
"core town-building gameplay loop works". Investigating first was worth it: the legacy
server is almost entirely absent from this area, and the content that does exist is
complete and unused.

**Nothing in the legacy server reads the committed `levels` schedule.** A search across
`command.py`, `engine.py`, `sessions.py`, `server.py`, and `constants.py` finds
**zero** references to it. The level curve is therefore content the **client** owns
entirely — the server neither derives a level from experience nor validates one against
the curve.

## Established: the two XP-related commands

Both are in the catalog's "Tutorial, level, and unit XP" section and both are
one-or-two-line branches:

**`level_up(new_level)`** (`command.py:81-85`):

```python
elif cmd == "level_up":
    new_level = args[0]
    map["level"] = new_level
    print("Level up! New level:", new_level)
```

**One line of state change, with no range check and no XP validation** — the catalog
already records this. A client can set any level at all, including 99, and the server
answers `{"result":"success"}`. This is the same client-trusted shape the collect and
expand lines already refused, and it is the one place where this line can add a real
guard.

**`add_xp_unit(item_index, xp_gain, level?)`** (`command.py:322-338`): creates
`attr["xp"] = xp_gain` on an item row, or increments it if present; a missing item logs
an error and returns early; the optional third argument **only changes the log line**.
This is **unit** experience, on a unit's attribute bag — not the player's.

**Corpus fact that bounds it:** of the 40 placed rows, **0** carry an `xp` key in their
attribute bag, and the fresh save contains **no unit placements** at all. So the unit
XP path cannot be exercised against the committed corpus, and the player has nothing to
grant experience to.

## Established: the player's experience and level in the save

- `maps[0].xp` — the player's cumulative experience. It is the 8-slot resource vector's
  **slot 1**, written by `engine.apply_resources` like any other resource, and it is the
  **only** experience the server maintains. `privateState` carries no XP-bearing key.
- `maps[0].level` — the player's level, written **only** by `level_up`.
- Corpus values: `xp 4`, `level 1`. The resource readout already displays both (`xp` in
  the summary group because nothing spends it; `level` beside the player's name), so
  the *values* are visible today — what is missing is the **curve**: how much experience
  the next level needs, how far along the player is, and whether the stored level
  matches the stored experience.

## Established: the committed level curve

`config/main.json`'s `levels` has **100 entries**, already normalized as
"positional XP-curve order preserved with `legacy_id` as the 0-based index"
(`packages/game-content/README.md`, tables extension), fully native numbers
(`docs/game-content/field-types.md`). Each entry:

```json
{"name": "Slave", "exp_required": 0, "reward_type": "s", "reward_amount": 50}
```

- `exp_required` is **strictly increasing** across all 100 entries, with **no
  duplicates and no non-positive gap**: `0, 40, 60, 100, 200, 350, 550, 800, …`,
  reaching `2016089205` at the last entry.
- `reward_type` is one of `s`, `w`, `g`, `c` — **the same letter vocabulary as
  `items[].costs`** that the expand and resources investigations recorded, not the
  server's resource names.
- `reward_amount` takes exactly three values (`1`, `50`, `250`).
- `name` is **not** distinct: 44 distinct names across 100 entries, so the name is a
  label, not an identifier. Every entry from **one-based level 45** onward is
  `"Conqueror"`.

  **Correction (made during Apply):** this record originally wrote "from level 49
  onward", which was a **zero-based position** while the curve's index base is
  one-based (see below) — the first `"Conqueror"` row is at curve index 44, i.e.
  one-based level **45**. The delivered client module derives the one-based value
  and records the discrepancy rather than carrying the slip forward.

**And nothing consumes `reward_type`/`reward_amount`.** No legacy branch reads them, so
a level's reward is content with no server behaviour behind it — the same situation as
the expansion `neighbors`/`inventory_qte` requirements, and it must be refused rather
than invented.

## The one off-by-one, and why the corpus decides it

Two readings of the curve's index are possible, and they disagree by one level:

- **0-based** — `map["level"]` is the index into `levels`, so stored level 1 is
  `"Servant"` with `exp_required` 40.
- **1-based** — stored level *n* is `levels[n - 1]`, so stored level 1 is `"Slave"`
  with `exp_required` 0.

The committed corpus discriminates between them, and **0-based is contradicted**:

```
corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0
```

Under 0-based, a player with 4 experience is recorded as level 1 while the curve says
level 1 begins at 40 experience. Under **1-based**, the stored level 1 is `levels[0]`
— `"Slave"`, `exp_required` 0 — and `4 >= 0` holds, so **the corpus is self-consistent
under 1-based**.

This is the single most consequential decision in the line: guessing 0-based would
shift **every** level in the game by one, and the error would be invisible until a
player noticed the wrong level name. The evidence available is one data point in a
hand-built corpus, so the resolution is **derived** — but it is derived from the only
evidence there is, and the rejected alternative is **actively contradicted** rather
merely unsupported. The change must therefore:

- read the curve as **1-based**, with the index conversion in **one named place**;
- treat the stored `level` as **unverified against the curve** rather than authoritative,
  and surface any disagreement instead of hiding it;
- and cover the conversion's boundaries explicitly, including `xp` below the first
  threshold, exactly on a threshold, and the corpus's own `xp 4 / level 1` case as a
  regression fixture.

## The reachable scope

Supported by the evidence above, and the smallest complete version of "XP basics":

- a **level readout** from the committed curve — the player's current level, its name,
  the experience the next level requires, and how much is left, with any disagreement
  between the stored level and the curve **shown rather than smoothed over**;
- a **progress-to-next-level** figure derived from the same curve, so the player can see
  the loop close;
- and a **guarded level-up intent** that accepts only the level the committed curve
  implies for the player's experience, refusing anything else — the one place where a
  real server-side guard is possible, because the curve is committed content and the
  corpus proves the index base. A refused request must leave the corpus byte-identical.

Explicitly **out of scope**, each for a stated reason:

- **unit XP** (`add_xp_unit`) — needs unit placements, and the committed corpus has
  **none** and no row carrying `attr["xp"]`;
- **level rewards** (`reward_type`/`reward_amount`) — **no legacy branch reads them**,
  so paying them would be inventing an economy, exactly as the expansion requirements
  were refused;
- **the tutorial** (`complete_tutorial`) — a separate progression system with its own
  semantics and no bearing on the town-building loop;
- **XP curve rebalancing** — the committed `exp_required` values are preserved verbatim;
  no tuning is proposed or performed;
- and server-authoritative validation beyond this one guard (Server v1 / M13).

## What the next change should deliver

A committed-curve level model with the 1-based conversion in one named place; a level
and progress readout that surfaces any stored-versus-derived disagreement; a
`POST /v0/level_up` endpoint accepting only the level the curve implies, deriving it
server-side rather than trusting the client's number, and proving its post-state the way
the collect and expand endpoints do — the stored level changed to exactly the derived
value and every stored resource changed by exactly the derived delta; a typed
`GameApi.level_up_town()`; an eighth mutually exclusive client mode; and evidence with
the established-versus-derived split naming the index base as derived.

After this line, all eleven M7 deliver lines are delivered and the M7 exit criterion can
be assessed.

## Resolution, after the `building-xp` proposal and Apply (2026-09-30)

### D1 confirmed empirically, not just by the corpus contradiction

The one-based interpretation was resolved in the design from the corpus's contradiction
(the 0-based reading is impossible for `xp 4 / level 1`), and the compat slice then
**confirmed it directly**: its derivation returns **level 1** for the corpus's `xp 4`,
matching the recorded level. So the committed corpus is self-consistent under one-based,
exactly as the investigation predicted, and the conversion lives in exactly one named
function per layer — `level_envelope.entry_index_for_level` on the service side and
`LevelFlow.entry_index_for_level` on the client side, each with a named inverse and a
round-trip assertion across all 100 entries.

### An honest consequence: the delivered corpus is already at its derived level

Because the corpus is consistent, `POST /v0/level_up` **refuses** it with
`level_already_current`, before the dispatcher runs. Two things follow, both recorded:

- the committed fixture's own `level_up` transaction therefore moves **nothing** —
  `level` 1 → 1 and **all seven resources byte-identical** — recorded as
  `level_moved: false` with a `level_moved_note`, and the level *movement* itself is
  established by a recorded probe in the same run (`level_up([2])` with a client-sent
  experience vector moved `level 1 → 2` and `xp 4 → 504`, with the changed map keys
  exactly `['level', 'xp']`). That probe is what makes the endpoint's "no resource
  moved" proof non-tautological: it demonstrates the vector *would* have moved a
  resource had one been sent.
- the `level-up-live` battery phase therefore **cannot** assert a corpus save mutation
  and deliberately does not pass the mutation flag; it asserts the refusal, its code, its
  empty payload, and the corpus's byte-identity, and `verify-boot.ps1` carries a marker
  recording the deliberate absence. The success path rests on the fake double and the
  hermetic flow over an in-memory experience, and this is a recorded claim limit rather
  than an unexercised assertion.

### What was closed, and what stayed open

Closed: the committed-curve level model with the one named conversion; the level and
progress readout; **explicit stored-versus-derived disagreement reporting** with no
silent preference or reconciliation; a guarded level-up intent whose target the service
derives and whose client-supplied level is ignored exactly as a client-supplied amount
or price is ignored elsewhere; and the two-part post-state proof.

Stayed open, as designed: **no level reward is paid** — `reward_type` and
`reward_amount` are committed on every entry and consumed by no legacy branch, so paying
them would invent an economy; **unit XP and tutorial progression remain out of scope**
because the corpus cannot exercise them (0 of 40 placed rows carry `attr["xp"]`, and there
are no unit placements); and the **committed thresholds are preserved verbatim** with no
rebalancing.
