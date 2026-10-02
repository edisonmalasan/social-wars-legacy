# Legacy contract — M9 line 3, `tutorial/progression`

**Status:** investigation record, committed before the proposal (the standing
investigation-first rule for this milestone).
**Scope:** the M9 deliver item `tutorial/progression`, and only the part of it
that the legacy server actually implements.
**Evidence status:** committed legacy source, the committed command catalog, and
**40 executed-legacy probe transactions** against the real Flask server in
disposable copies, across four probe rounds, of which **28 are conclusive**.
The remaining twelve measured monotonicity on an already-completed save, because
of three probe-ordering defects recorded in §4. Nothing here is inferred from a
converted asset package.

This is the **last** M9 deliver item with no delivered line at all. `building-xp`
(M7 line 11) delivered XP and levels; `unit-collection` (M8 line 5) delivered
collections; M9 lines 1 and 2 delivered `research` and `quests`.

---

## 1. Method, and the scope of every count below

Every occurrence count in this document is a **quoted** count: measured with the
`tokenize`/`ast` machinery so that comments, trailing comments on code lines, and
every docstring or bare string-expression statement are removed before counting.
This matters here — a naive per-line count inflated `playerInfo` from 26 to 27
because `sessions.py:174` and `sessions.py:213` carry trailing comments
containing the term, and it counted `sessions.py:19`, which sits inside a
module-level `'''…'''` block that is **not** a docstring (the imports come
first, so `ast.get_docstring` never sees it).

Module coverage was also wrong on the first sweep and is corrected here: there
are **eleven** root `.py` modules, not eight. The three initially missed are
`auctions.py`, `get_player_info.py`, and `legacy_command_recorder.py`. All three
were then measured and all three contribute **zero** occurrences of every term
below.

| Module | `tutorial` | `completed_tutorial` | `tutorial_step` |
| --- | --- | --- | --- |
| `command.py` | 6 (5 lines, L60–L65) | 1 (L65) | 4 (3 lines, L61–L63) |
| all other **ten** modules | 0 | 0 | 0 |

The full 11-module sweep, and the fact that `get_player_info.py` is the module
that serialises player state to the client, are both recorded here because the
missed modules were exactly the ones that could have refuted finding 2.

---

## 2. The findings

### 2.1 `complete_tutorial` is the entire legacy tutorial surface

Six quoted occurrences of `tutorial` on five lines, all inside one branch:

```
command.py:60      elif cmd == "complete_tutorial":
command.py:61          tutorial_step = args[0]
command.py:62          print("Tutorial step", tutorial_step, "reached.")
command.py:63          if tutorial_step >= 25 or tutorial_step == 15:
command.py:64              print("Tutorial COMPLETED!")
command.py:65              save["playerInfo"]["completed_tutorial"] = 1
command.py:66          return
```

There is no second tutorial command, no tutorial read, and no tutorial helper in
any module.

### 2.2 `completed_tutorial` is write-only — the tenth zero-consumer field

`completed_tutorial` has **exactly one** occurrence in the whole legacy server:
the write at `command.py:65`. **Zero readers, in any of the eleven modules.**

This is the same shape as the research counters on line 1 of this milestone, and
it makes `completed_tutorial` the **tenth** committed field in this project with
zero legacy consumers, after `unit_capacity`, the level curve's
`reward_type`/`reward_amount`, `max_frame`, the `velocity` family,
`training_time`, and `unlockedQuestIndex`.

**One correction to my own reasoning, recorded because it changes a conclusion.**
While first reading a `git grep` listing I concluded that the flag was never
sent to the client, since no module names it. That is wrong.
`get_player_info.py:15` builds its response as

```python
"playerInfo": session(USERID)["playerInfo"],
```

so the **entire** `playerInfo` dict is handed to the client verbatim and the flag
travels with it — by dict inclusion, not by any server-side naming of it. The
flag is therefore readable by the client, while still being read by **no** server
module.

### 2.3 `tutorial_step` is a local and is never persisted

Four quoted occurrences on three lines: bound from `args[0]` at L61, printed at
L62, compared twice at L63. It is **never written to `save`**.

So the legacy tutorial records a **terminal boolean and nothing else**. There is
no stored step, no per-step progress, and no way to recover a player's tutorial
position from the save. This single fact explains two other observations below:
the corpus contains no mid-tutorial save (§3), and "resume the tutorial" is not
merely undelivered but **unrepresentable** in the legacy save shape.

### 2.4 The gate is a disjunction on a client-sent value, with a nine-value hole

`tutorial_step >= 25 or tutorial_step == 15`, where `tutorial_step` is the
client's `args[0]`, used raw.

Measured by executed-legacy probe, **each value on its own freshly seeded server**
(see §4 for why that matters):

| Step sent | HTTP | `completed_tutorial` | Verdict |
| --- | --- | --- | --- |
| `0` | 200 | `0 → 0` | declines |
| `1` | 200 | `0 → 0` | declines |
| `-1` | 200 | `0 → 0` | declines |
| `14` | 200 | `0 → 0` | declines |
| `16` | 200 | `0 → 0` | **declines — inside the hole** |
| `24` | 200 | `0 → 0` | **declines — the hole's upper edge** |
| `15` | 200 | `0 → 1` | completes (exact arm) |
| `15.0` | 200 | `0 → 1` | completes — **a distinct wire value** |
| `true` | 200 | `0 → 0` | declines (`True >= 25` and `True == 15` both false) |
| `25` | 200 | `0 → 1` | completes (`>=` arm edge) |
| `1000000000` | 200 | `0 → 1` | completes — **no upper bound** |

**Steps 16 through 24 inclusive — nine values — do not complete the tutorial.**
The gate is not "reach the end"; it is "send exactly 15, or send at least 25".

Also measured:

- **No upper bound.** `10^9` completes.
- **No lower bound and no clamp.** `-1` simply declines.
- **No type check.** A float completes because `15.0 == 15`; a bool declines.
- **A non-numeric step is a server error.** `"15"` → **HTTP 500**, `[]` → **HTTP
  500**, `[null]` → **HTTP 500**.

### 2.5 The flag is monotone and one-way

The single write site always writes `1`. There is no reset, no clear, and no
migration: `version.py:6-51` does not touch the field. Executed: after a
completion, every later value leaves it at `1`, and the changed-leaf count for
every such transaction is **zero**.

### 2.6 The flag lives in `playerInfo`, a save-level record

`playerInfo` is the save-level object; `maps[0]` has **no** `completed_tutorial`
key at all. `complete_tutorial` is consequently the only write delivered on a
previous line that targets a save-level field rather than a map field — a
structural difference every earlier line's endpoint shape has to account for.

### 2.7 The tutorial command is a resource-minting vector — the strongest reason to derive

`apply_resources(save, map, resources_changed)` runs at `command.py:40`,
**before** dispatch, so a `complete_tutorial` command applies a client-sent
8-element vector exactly like any other.

Executed, in a single transaction: step `15` with the ladder
`[101, 3, 7, 11, 13, 17, 19, 23]` produced **eight** changed leaves —

```
/playerInfo/completed_tutorial  0 -> 1
/maps/0/xp                      4 -> 7
/maps/0/gold                 2000 -> 2007
/maps/0/wood                 2000 -> 2011
/maps/0/oil                  2000 -> 2013
/maps/0/steel                2000 -> 2017
/playerInfo/cash                5 -> 24
/privateState/mana               0 -> 23
```

Slot 0 (`unknown = 101`) is **absent** from the changed set, confirming
`engine.py:253` reads and discards it while the other seven are applied.

The same ladder on a **non-completing** step (`24`) still moved all seven
resources and left the flag at `0`. So the resource movement is a property of the
**client-sent vector on any tutorial command**, not of completion.

This captured transaction is what makes a "no stored resource moved" proof
**non-tautological** for this line — the same proof form the research and quests
lines arrived at independently, and the reason it is named here in the
investigation rather than discovered during Apply.

### 2.8 A raising step discards the already-applied vector — measured, not assumed

Because `apply_resources` has already run by the time `args[0]` is compared, the
obvious worry is that a bad step crashes the branch *after* minting resources, and
that the exception would still persist them. Executed with a **full non-neutral
ladder** attached:

| Probe | HTTP | Flag | Changed leaves | Resources moved |
| --- | --- | --- | --- | --- |
| step `"15"` + ladder | **500** | `0 → 0` | 0 | **no** |
| `[]` + ladder | **500** | `0 → 0` | 0 | **no** |
| step `null` + ladder | **500** | `0 → 0` | 0 | **no** |

So the legacy server's 500 on this path is **safe**: the exception propagates out
of `do_command`, out of the loop in `command()`, and past `save_session(USERID)`
at `command.py:32`, so the applied vector is discarded. This is a **correction to
my own probe**, which originally asked this question with a *neutral* vector and
therefore proved nothing.

### 2.9 The branch's `return` does not abort the rest of the batch

I first inferred the opposite and was wrong; reading the dispatcher refutes it
and an executed probe confirms it.

`command()` loops over `commands` at `command.py:19-30` and calls
`do_command(...)` **per command** at line 30, so the `return` at `command.py:66`
returns from `do_command` only and cannot escape the loop. `save_session(USERID)`
runs after the whole loop at line 32.

Executed, each case on its own fresh save:

| Case | Batch | Flag | Leaves |
| --- | --- | --- | --- |
| B | `flash_debug` alone | `0 → 0` | 6 (cash `5 → 7777`) |
| C | `complete_tutorial[15]`, then `flash_debug` | `0 → 1` | **7 — both ran** |
| D | `flash_debug`, then `complete_tutorial[15]` | `0 → 1` | 7 — identical total |
| E | `complete_tutorial[24]`, then `complete_tutorial[15]` | `0 → 1` | 1 |
| F | `complete_tutorial[15]`, then `complete_tutorial[24]` | `0 → 1` | 1 |
| G | `complete_tutorial[15]` + gold delta 5, then `complete_tutorial[15]` + gold delta 9 | `0 → 1` | 2, **gold `2000 → 2014`** |
| H | `complete_tutorial[24]` + gold delta 5 | `0 → 0` | 1, gold `2000 → 2005` |

Cases E and F show that one batch may both decline and complete, and that both
commands run. Case G shows `apply_resources` runs **per command** and the
client vectors **sum** (`+5 +9 = +14`). Case H separates the two effects.

### 2.10 Adjacent, measured, and deliberately out of scope

- **`set_variables` is a no-op.** `command.py:951-952` only prints. It is one of
  the four commands with committed replay evidence in `tools/protocol-replay`, and
  it mutates nothing. I initially misread the resource-writing branch at
  `command.py:302-318` as belonging to it, and drew a false inference from the
  result (§2.9).
- **`flash_debug` is the branch that writes `playerInfo["cash"]`** from client
  args (`command.py:302-320`). It **assigns** rather than clamps, and executed it
  drove `gold` from `2000` down to `111`. Recorded as a measurement, not as part
  of this line's scope; it belongs to a Server v1 / M13 authority question.

---

## 3. Committed content and corpus

### 3.1 There is no committed tutorial content at all

- `tutorial`: **zero** occurrences in `config/main.json` at **any** depth
  (measured across all 20 top-level keys by recursive walk).
- `tutorial`: **zero** occurrences across **all** committed normalized content
  packages under `packages/game-content/normalized/`.

So there is **no** committed step list, step count, gate definition, tutorial
dialogue, or reward. There is nothing to derive a schedule or a reward from. This
is a *cleaner* absence than the research line found, where `research` at least
appeared as asset names.

### 3.2 The corpus holds no mid-tutorial save — and could not

All **31** committed village saves carry the key. **30** record `1`; exactly
**one** — `villages/initial.json`, the template the server loads for a new player
— records `0`.

There is no partially-progressed save. That is **not** a corpus limitation to
work around but a direct consequence of §2.3: with no stored step, such a save is
unrepresentable. (`tests/saves/fresh-player.json`, the seed the compatibility
service uses, records `0`, so the `0 → 1` transition is fully exercisable.)

---

## 4. Corrections to my own probe design

Recorded as a corrections section rather than quiet edits, per this milestone's
standing practice. Every one of these changed what a probe actually proved.

1. **Probe order defeated the gate measurement.** The first probe sent the
   completing value (`15`) first. Because the flag is one-way (§2.5), every later
   probe started from `1` and therefore measured *monotonicity* — "the flag never
   returns to 0" — rather than *the gate*. Both are worth knowing; only the second
   is about the rule. Fixed by probing every non-completing value before the
   completing one.
2. **A neutral vector made a security question vacuous.** The first probe's 500
   case carried a **neutral** vector, so its "resources unchanged" was trivially
   true and said nothing about whether a crash persists the applied vector. Fixed
   in §2.8 by attaching a full ladder. This was the most important gap: the
   reassuring answer turned out to be true, but only after being measured.
3. **A shared server silently converts gate measurements into monotonicity
   measurements.** `sessions.py` holds saves in the in-memory `__saves` dict, so
   restoring the seed *file* does not reset server state. Every case in §2.4 and
   §2.9 therefore runs in its own disposable server. This trap fired three times.
4. **A false inference from a misattributed branch.** See §2.9 and §2.10: I read
   `flash_debug`'s body as `set_variables`'s, concluded the tutorial branch's
   `return` aborted the batch, and was refuted by reading the dispatcher.
5. **Module coverage was incomplete on the first sweep** (8 of 11), including the
   one module that serialises player state. Corrected in §1.
6. **A `git grep` listing was miscounted as 37 village files.** The measured glob
   is **31**, and 31 is the figure used above. The discrepancy was caught only
   because the grep line count and the glob count disagreed.
7. **One syntax error in a probe script** (`[` closed with `)` in a case tuple),
   caught by reading the traceback and fixed rather than re-run blind.

---

## 5. Evidence that already exists and must be referenced, not reimplemented

`tools/protocol-replay/test_protocol_replay.py:173-179`
(`test_tutorial_boundaries`) already pins the boundary arithmetic at steps
`14, 15, 24, 25, 26, -1`. It runs against a **stub oracle inside the replay
harness**, not the executed legacy server, so it is **not** an executed-legacy
oracle. The new line should reference this coverage and add the executed-legacy
fixture, rather than presenting the boundary table as new work.

`docs/legacy-protocol/commands.md` already catalogues `complete_tutorial` with
args `tutorial_step value; resources_changed deltas` and carries the standing
client-trust warning for the whole dispatcher.

---

## 6. What the contract implies for the deliver line

Stated as constraints the proposal must satisfy, not as a design:

- The tutorial state projection carries **only** `playerInfo.completed_tutorial`,
  reported **verbatim**, failing closed on an absent or wrongly-typed
  `playerInfo`. **No** step, **no** progress ratio, **no** remaining time, and
  **no** completion is derived from anything — the legacy save has nothing to
  derive from (§2.3).
- The branch's gate is recorded **as data**: the two arms, the nine-value hole
  between them, the missing upper and lower bounds, and the three 500-raising
  input shapes.
- The operation is **intent-only**: the client sends a step and **never** a
  completion outcome, a stored flag, or a resource vector. Completion is derived
  server-side from the committed disjunction.
- The endpoint must **refuse**, with a named code and no state change, the three
  input shapes the legacy server answers with an unhandled **500** — a
  non-numeric step, a missing step, and a null step — rather than reproducing a
  crash. This is a deliberate, recorded improvement in *failure handling only*:
  the legacy *state transitions* are reproduced exactly, and the divergence is
  stated, because a 500 is not a behaviour worth preserving.
- Every tutorial action must prove **every stored resource is unchanged**. That
  proof is anchored by the captured §2.7 transaction, so it is not tautological.
- **No tutorial reward exists and none is invented**; **no committed tutorial
  content is invented**, none existing (§3.1).

## 7. Claim limits on this record

- Everything here is one **fresh-player** corpus. No progressed-player save
  exists with `completed_tutorial` at any other value, because none can (§2.3).
- Parity would cover **one** transaction against that corpus, plus the probe set
  above. The probes establish the gate and the failure shapes; they are
  investigation evidence, not a committed fixture.
- **No claim is made about the Flash client.** The gate thresholds `15` and `25`
  are recorded verbatim as the legacy server's rule; nothing here establishes
  what the client counts as a step, whether it sends `15` or `25` first, or how it
  renders tutorial progress. The flag's journey to the client is established only
  as far as the wholesale `playerInfo` inclusion (§2.2).
- **No tutorial content, reward, schedule, dialogue, or step list is claimed to
  exist**, because none is committed (§3.1).
- **No pixel parity** and **no windowed capture** are in scope: nothing is
  rendered.
- `flash_debug`'s unclamped resource assignment (§2.10) is **measured but not
  owned** by this line; it is recorded here as an authority gap for Server v1 /
  M13.