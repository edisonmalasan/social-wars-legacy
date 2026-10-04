# The M9 closure — implementation-complete to the oracle, exit NOT MET

**Date:** 2026-10-05
**Milestone:** M9 — Progression
**Exit criterion:** *"Primary long-term progression systems work."*
**Verdict:** **implementation-complete to the extent the committed legacy oracle
supports; exit criterion NOT MET.**
**Classification:** a **legacy-reference capability gap**, not an unfinished
modern implementation.

This document closes M9. It is not an assessment of new behaviour and it
proposes no implementation. Its whole job is to state, precisely and
auditably, what M9 now contains, why its criterion cannot be met from the
preserved oracle, and why the correct next move is M10 rather than another M9
line.

---

## 1. What was reconciled

Four sources were checked against each other rather than against memory:

| source | state found |
| --- | --- |
| `docs/legacy-m9-assessment.md` (PR #270, `7ab93c7`) | intact; its two proposed bounded gaps are both now delivered; its refusal list is unchanged |
| the delivered M9 specifications in `openspec/specs/` | **seven** capabilities present, all six deliver items covered |
| `apps/client-godot/verify-boot.ps1` | all five M9 hermetic suites registered and passing |
| `AGENTS.md` | **two delivered lines were undocumented** — see §5 |

Two things did **not** reconcile cleanly, and both are corrected here rather
than smoothed over: `AGENTS.md` was missing the command sections for two
delivered lines (§5), and the blanket phrase this closure rests on is
**imprecise as written** (§3). Neither required un-delivering anything.

---

## 2. Per-item completeness

M9's deliver list is `XP`, `levels`, `quests`, `research`, `collections`, and
`tutorial/progression`. Every item has a delivered capability:

| deliver item | delivered capability | state |
| --- | --- | --- |
| `research` | `godot-research` | counters, transitions, fast-forward writer named |
| `quests` | `godot-quests` | state, six branches, no rewards |
| `tutorial/progression` | `godot-tutorial` | flag and gate |
| `XP` (player) | `godot-building-xp` | verbatim projection, derived level, intent-only `level_up` |
| `XP` (unit) | `godot-unit-experience` | twelve executed-legacy transactions, fail-closed projection |
| `levels` | `godot-building-xp` | curve established one-based, disagreement reported not reconciled |
| `collections` | `godot-unit-collection`, `godot-stored-item-placement` | content-derived grant into storage, **plus the placement round trip** |

The two bounded gaps the assessment named are both closed, each through its own
full lifecycle:

1. **`place_stored_item`** → `godot-stored-item-placement`
   (`2026-10-03-stored-item-placement`, PRs #271–#274).
2. **`add_xp_unit`** → `godot-unit-experience`
   (`2026-10-04-unit-experience-evidence`, PRs #276–#281).

`openspec list` reports **no active changes**. There is no partial M9 line.

**Measured on the merged state (2026-10-05), all five M9 hermetic suites:**

| suite | checks | exit |
| --- | --- | --- |
| `test_tutorial.gd` | 639 | 0 |
| `test_unit_experience.gd` | 2430 | 0 |
| `test_research.gd` | 1024 | 0 |
| `test_quests.gd` | 1223 | 0 |
| `test_stored_item_placement.gd` | 544 | 0 |

Zero `ERROR:`, `SCRIPT ERROR`, or `[test] FAIL` markers across all five.

---

## 3. Why the exit criterion is NOT MET — re-measured, and a correction

The reason the criterion cannot be met is that the preserved oracle contains no
progression **consumer**: nothing in the committed legacy server reads
progression state back in order to change what a player may do.

**That claim was re-measured independently rather than carried forward, and it
is right in substance but imprecise as usually stated.** A naive
read/write classifier over the eleven legacy root modules (3,833 lines, **47**
occurrences of a stored progression key) finds **nine read occurrences across
eight distinct lines**. Judged individually, every one is a non-consumer — and the
three that most looked like consumers are the interesting ones:

| read site | what it actually does |
| --- | --- |
| `sessions.py:147` (**two** occurrences, one for `"xp"` and one for `"level"`) | echoes stored `xp` and `level` into the **player-info response dict** — read back to the client, gating nothing |
| `auctions.py:91` | `"level": auction["level"]` — an auction field echoed into a response |
| `command.py:335` | `if "xp" not in attr:` — a **membership test choosing between two writes** (assign vs increment) |
| `command.py:517` | `if collection_id not in privateState["collections"]:` — a **membership test guarding the append on the next line** |
| `command.py:518` | the append itself — a **write**, misclassified as a read because it is a method call rather than an assignment |
| **`command.py:113`** | `if not map["currentQuestVars"]:` — the closest thing to a consumer in the repository, and still not one: it decides whether to **self-heal an empty container** before writing into it. It changes the *shape* of a subsequent write, never what a player may do. Already recorded by the `quests` line. |
| **`version.py:39`**, **`:41`** | `if "questTimes" not in map:` and `if type(map["questTimes"]) != dict:` — inside the **`0.02a` save migration**, guarded by `if save["version"] == "0.01a"`. A **migration**, not gameplay. Already recorded by the `quests` line. |

Grouped: **three echoes**, **two membership tests** that choose or guard a
write, **one write** the classifier misread, **one self-heal**, and **two
migration reads**. Separately, `command.py:940` → `:1844`
(`research_timers = privateState["timeStampDoResearch"]`) is an **alias feeding a
write** and the classifier counted it as such, not as a read.

So the precise statement is: **nine read occurrences across eight lines, and zero
reads that gate a player's options.**

Searching for a consumer and finding only these is a **stronger** result than
asserting it: the three sites that most resemble one were each examined, each is
benign, and two were independently documented by an earlier line.

This is **not** a contradiction of any delivered record. The delivered specs'
"zero consumers" claims are scoped to the **level curve and reward tables**
(`exp_required`, `reward_type`, `reward_amount`, `level_ranking_reward`), and
those genuinely have **zero** occurrences of any kind. The correction here is to
the *shorthand*, which said "no reads" where it should have said "no
*consumers*."

**Why this is a legacy-reference capability gap.** A capability gap in the
reference implementation cannot be closed by the successor: the behaviour being
asked for does not exist in the oracle to be reproduced. Implementing one would
mean **inventing** it, and an invented progression system is not a migration —
it is a different game wearing the same save format. The honest classification
is therefore:

> M9 is **implementation-complete to the extent the committed legacy oracle
> supports**. Its exit criterion is **NOT MET** because the preserved
> implementation being migrated **has no progression consumer**, and closing the
> gap would require authoring behaviour that has no oracle.

---

## 4. Refusals preserved

Each refusal below stands. None is revisited by this closure, and none may be
"fixed" without new committed evidence of a consumer.

| refusal | measured reason |
| --- | --- |
| **no unit-XP award schedule** | the amount is `args[1]`, **entirely client-supplied**, with **no validation whatsoever — not even `int()`**. The branch assigns or increments and prints. Any schedule would be invented, and the committed `units[].xp` was **refuted** as the award by three recomputed measurements. |
| **no level reward** | `reward_type`/`reward_amount` are committed on all 100 curve entries and carry **five** distinct pairs, but have **zero** legacy consumers and **no committed vocabulary** for the reward-type letter. `level_ranking_reward` (50 entries, cash plus a unit grant) has the same problem. Paying either invents a schedule *and* a vocabulary. |
| **no progression gate or consumer** | measured in §3: zero reads gate a player. |
| **no collection eligibility check** | the committed collections' `item_ids` requirements are unchecked by the server; a Server v1 / M13 gap, deliberately not filled. |
| **`unitCollectionsCompleted`** | a **second, distinct** collection ledger with one committed record; only `collections` is delivered, and this one has no reader to justify delivering it. |
| **collection `cashPrice`** | no consumer. |

These refusals are the *substance* of this closure. A milestone is not closed by
removing its refusals.

---

## 5. `AGENTS.md` reconciliation

`AGENTS.md` carries a `Verified … commands` section per delivered line, and
required that section be updated with commands "actually executed successfully."
It had **35** such sections and was missing **two** for delivered M9 lines:

- **`unit-tutorial`** (M9 line 3) — no section
- **`unit-experience-evidence`** (M9's second post-assessment line) — no section

Both lines' commands had been executed and recorded, so the sections were
written from those executions and the suite counts in §2 were re-measured on
the merged state rather than quoted from memory. The `unit-experience` section
also corrects the `building-xp` claim limit that pointed at it.

---

## 6. Transition to M10

M9's criterion is unreachable, so holding the project on it would stall the
roadmap on an oracle limitation rather than on real work. The cursor moves to
**M10 — Missions and Combat**, whose deliver list is `mission loading`,
`mission state`, `combat actions`, `damage`, `death`, `mission completion`,
`rewards`, and whose criterion is *"Primary combat loop works."*

M10 is a **better** target than M9 turned out to be, for a measured reason: M8
established that combat fields (`attack`, `defense`, `life`, `attack_interval`,
`attack_range`, `best_against`, `best_against_mult`) all measure **zero**
legacy consumers, but M8 also established a **real placed training producer**
and genuine combat branches (`end_attack`, `map_lose_item`, `kill`,
`resurrect_hero`). Whether M10's criterion is reachable must be established by
its own investigation, exactly as M9's was — **nothing is pre-authorised here.**

The first M10 objective in roadmap and dependency order is **mission loading /
mission state**, and it begins with its own committed investigation contract.

---

## 7. Claim limits

- This closure asserts **no new behaviour** and delivers **no code**. It is a
  ledger and a classification.
- "Implementation-complete" is scoped to **the six named deliver items** and to
  the committed oracle's evidence. It is **not** a claim that M9 is complete in
  general.
- The §3 read/write split was produced by a **deliberately naive whole-line
  heuristic** — comments included — and each of the 47 occurrences was classified
  mechanically, then the nine reads **judged by hand** against the source line
  quoted. The eight-line classification is a reading of those eight lines, not a
  parser result. A first pass that reported **seven** sites was **wrong**: it
  missed `command.py:113` and the two `version.py` migration reads, which are the
  strongest candidates for a genuine consumer. The corrected figure is above.
- The five suite counts in §2 were re-measured on the merged state. They are
  **not** a fixed property: `test_unit_experience.gd` walks the client source
  tree, so any line adding a client source raises its count.
- Nothing in §4 is reopened by this document, and no refusal may be converted
  into an implementation without new committed evidence of a legacy consumer.
- No Flash, Ruffle, ActionScript, or browser executed in any command behind this
  document, and no network was used.
