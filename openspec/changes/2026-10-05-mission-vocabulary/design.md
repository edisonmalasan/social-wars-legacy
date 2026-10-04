# Design

## Context

`docs/legacy-m10-missions.md` (PR #283, merged `e4fc5e2`) measured M10's first
objective. Its findings, in one paragraph: mission *state* is already delivered by
the M9 `godot-quests` line; mission *loading* has no oracle because no committed
save has more than one map; both mission save fields are write-only; and the
undelivered surface is a **64-constant mission-type vocabulary with zero
consumers**, plus three committed mission-adjacent globals the normalized package
already carries and nothing reads.

That vocabulary lives in **legacy `constants.py`**, not in the content package.
This is the fact that shapes the whole design, and it is the difference between
this line and M8's `unit-definitions` line, which read an already-normalized table.

## Goals / Non-Goals

**Goals**

- Project the 64 `MISSION_*` constants read-only, with names, values, ordering and
  numbering gaps verbatim and nothing derived.
- Report the three committed mission-adjacent globals verbatim, with no rule
  derived from any of them.
- Record the zero-consumer finding **structurally**, so it cannot be quietly
  falsified by a later line.
- Make transcription from `constants.py` impossible to get wrong.
- Establish the mission-type numbering that M10's later combat lines can cite.

**Non-goals** — everything in the proposal's Non-goals list, restated: no loading
mechanism, no completion, no reward, no unlock, no enforcement of
`NUM_ACTIVE_MISSIONS`, no map-index refusal, no second `collect_mission` capture,
and **no behaviour keyed on a mission type**.

## Decisions

### 1. The vocabulary is not normalized into the content package

The normalized package is built from `config/main.json`, and every entry in it
records `source_file: "config/main.json"`. Extending it to carry 64 declarations
out of legacy `constants.py` would introduce a **second content source** for
vocabulary that is not content the server ever serves — it is dead legacy code.

Doing that is defensible, but it is a **larger architectural change than this
bounded line should carry**: it would touch the package manifest, add an
eleventh builder, alter the validator's source-of-truth accounting, and change
the content validator's output count. This line is scoped to projection, and the
content-package extension is recorded as a **deferred alternative** rather than
smuggled in.

The cost of this choice is one committed table that duplicates 64 declarations.
Decision 2 makes that duplication safe.

### 2. The committed table is byte-faithful to `constants.py`, and a test proves it

Because decision 1 leaves a duplicated table, drift is the real risk. So the
hermetic suite asserts, per entry, that the table's name and value are byte-equal
to the declaration `constants.py` actually carries, and additionally that the
table's **entry count and gap set** match the extraction. A hand edit that
transcribes a value wrongly fails the suite rather than silently shipping.

The suite reads `constants.py` **as bytes** — the project's standing lesson from
two closed CRLF guard defects — and extracts declarations by pattern, so the
assertion is against source truth and not against a copy of the copy.

This makes the guard **stronger than a normalization pass** for the failure mode
that matters (a wrong number reaching the client), and it is the reason decision 1
is acceptable.

### 3. The three globals are read from the existing normalized package, not re-transcribed

`NUM_ACTIVE_MISSIONS`, `PERMISSION_PACK_UNITS` and `PERMISSION_COSTS` are already
normalized in `packages/game-content/normalized/globals.json`. This line reads
them through the existing content registry and reports them verbatim. It
**duplicates nothing** for them. This asymmetry — globals from the package,
constants from a drift-guarded table — is deliberate and is recorded in the
report so a reader is not left guessing why two sourcing paths coexist.

### 4. The zero-consumer finding is recorded structurally, with two guards

The claim "nothing consumes the mission vocabulary" is the line's load-bearing
finding, and a prose assertion is worthless because a later line can falsify it
without noticing. Two independent guards are added, following the M8
`unit-behaviors` precedent:

- a **whole static-function inventory pin** on the delivered module, so adding a
  dispatch or trigger helper fails the suite outright;
- a **by-name guard** that fails if any delivered code identifier is named after a
  mission type or mission constant, so a "just this one is special" helper wearing
  the vocabulary as a name is caught.

Both guards are **to be proven by injection and restore during Apply**, not
trusted, which is the standing practice in this project.

### 5. Mission state fields stay owned by `godot-quests`; this line asserts the boundary

`godot-quests` already projects `idCurrentMission`, `timestampLastChapter` and
`currentQuestVars` verbatim (its spec lines 8–9) and already records the
stringification divergence and the `fast_forward` client-writability. This line
**does not re-project, re-derive, or reconcile** them.

Instead it asserts the ownership boundary: the mission **vocabulary** module
declares no mission **state**, and the suite pins that. This mirrors the boundary
assertion M8's `unit-definitions` line had to add when `unit-instances` landed,
and it prevents two capabilities from drifting into two sources of truth for the
same field.

### 6. Gaps and near-duplicates are reported, never normalised

The numbering has **four gaps** (`9`, `10`, `20`, `57`) and two near-duplicate
pairs (`15`/`16`/`17` `MISSION_DESTROYED*`, and `31` `MISSION_COMPLETE_QUEST_IN_MAP`
versus `47` `MISSION_COMPLETE_QUEST`). The projection reports gaps and
near-duplicates **as content**. It does **not** renumber, close gaps, deduplicate,
or pick a winner — no committed rule reconciles the `31`/`47` pair, so choosing one
would invent the reconciliation.

### 7. No endpoint, no fixture, no live phase

There is no behaviour to exercise. This is the same finding that removed the
fixture from M8's movement and animations lines, and it is stronger here than a
corpus limitation: there is no mission *command* to exercise beyond the one
`godot-quests` already captured. Adding a fixture or live phase would manufacture
verification of something that does not exist.

## Risks / Trade-offs

- **A duplicated table can rot.** Accepted, and mitigated by decision 2's
  byte-faithfulness guard, which fails the suite rather than shipping a wrong
  value.
- **A later line might treat a mission type as behaviour.** Mitigated by decision
  4's structural guards, and by decision 5's ownership boundary.
- **The line delivers no visible gameplay.** Accepted and inherent: the oracle has
  no mission behaviour to reproduce, so any visible behaviour would be invented.
- **Deferred work is real.** The content-package extension (decision 1) and the
  client-side projection of the three globals' *meaning* remain open, and are
  recorded as follow-ups rather than treated as done.

## Migration Plan

Single slice, no ordering constraint against other lines, no persistence change,
no network. The projection is added beside the existing unit and quest projections
and touches none of them.

## Open Questions

- Should the legacy `constants.py` vocabulary eventually be normalized into the
  content package as a second source (decision 1)? Recorded as a deferred
  alternative; deliberately not decided here.
- Should the four numbering gaps and the `31`/`47` near-duplicate pair be recorded
  as a content anomaly in the census tooling? Out of scope here; a census-level
  question rather than a client one.
