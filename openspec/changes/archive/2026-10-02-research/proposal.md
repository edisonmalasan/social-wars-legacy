# Proposal

## Why

**M9 — Progression is IN PROGRESS**, and this is its **first line**, `research`. The milestone-wide
investigation is committed as `docs/legacy-m9-progression.md` (PR #250, merged `f74647c`), extended by
the research measurements in PR #252 (merged `3d44159`).

That measurement overturned the pattern M8 ended on, and it is worth stating why before the contract,
because it decides this line's shape. Of the **63** named `command.py` branches, **18** name a
progression concept and **45** do not. `quests`, `research`, and `tutorial/progression` had **no**
delivered line at all. M9 is not a refusal milestone; it is the richest in the project.

Research is the right first line for five measured reasons:

1. It is **entirely undelivered** — four branches, none implemented, no endpoint.
2. It is a **closed four-branch set** over a **three-counter, two-track** state vector, so one line covers
   it without an open-ended surface.
3. It is **fully exercisable by the committed corpus**, which holds all three counters at `[0, 0]`.
4. It has the **clearest authority story** in M9: two counters advance on the client's word, and the one
   price-taking branch **charges nothing**.
5. It needs **no content package**, because none exists.

## The contract, measured

Four dispatcher branches over two tracks, named in the source's own comments as
`0: TYPE_AREA_51 , 1: TYPE_ROBOTIC`:

| Branch | `command.py` | `researchStepNumber` | `researchItemNumber` | `timeStampDoResearch` |
| --- | --- | --- | --- | --- |
| `next_research_step(_type)` | 268–274 | `+= 1` | — | `= time_now` |
| `research_buy_step_cash(cash, _type)` | 276–282 | — | — | `= 0` |
| `next_research_item(_type)` | 284–291 | `= 0` | `+= 1` | `= 0` |
| `reset_research_item(_type)` | 293–300 | `= 0` | `= 0` | `= 0` |

**`research_buy_step_cash` reads a client-supplied cash value and discards it.** It prints "Buy research
step for …" and moves no balance. This is structurally identical to M8 line 8's `used_syringe`: a legacy
author took the price and charged nothing.

**The counters are write-only.** `researchStepNumber` has 3 sites and `researchItemNumber` 2, every one
a write. `timeStampDoResearch` has 5 sites — the 4 branch writes plus a single read at
`command.py:923`, and **that read is itself a write**, because it sits inside `fast_forward`:

```python
research_timers = privateState["timeStampDoResearch"]
while i < num_research_timers:
    research_timers[i] = max(0, research_timers[i] - seconds)   # seconds is CLIENT-SUPPLIED
```

**Nothing anywhere reads a research counter to decide anything.** No completion test, no readiness test,
no remaining-time computation, no unlock gate, no cost check. A guard audit of all four branches finds
**no** bounds check, numeric clamp, membership test, exception guard, or existence check.

## What Changes

- **A typed, read-only research-state projection**: both tracks, all three counters, each reported
  **verbatim**, with the four branch effects recorded as data rather than code — the `next_research_item`
  reset of step **and** stamp recorded as happening **together**, and `fast_forward`'s client-writable
  decrement named as a **fourth writer**. Failing **closed** on an absent, non-list, wrong-length,
  non-integer, or negative counter vector rather than defaulting it.
- **The track inventory**, recording the two committed track names, the committed building ids they
  resolve to (`ID_BUILDING_AREA_51 = 139`, `ID_BUILDING_ROBOTIC_CENTER = 86`), and that `TYPE_AREA_51`
  and `TYPE_ROBOTIC` appear **only** in branch comments and are defined nowhere — so the mapping is
  reported, never used to derive behaviour.
- **An intent-only compatibility surface** with one endpoint per action, accepting **only** a player
  identifier and a track. The client sends **no** counter value, **no** timestamp, and **no** cash
  amount; the service advances the counters itself.
- **`research_buy_step_cash`'s cash discarded**, with a post-execution proof that **every stored resource
  is unchanged** — the same proof form that made M8 line 8's no-syringe-cost claim non-tautological.
- **Executed-legacy fixtures**, because the corpus can exercise these counters from their initial state.
  Unlike M8 line 8, this line should have real oracle evidence.
- **Tests and evidence**: a hermetic suite plus a `research-live` battery phase and a deterministic
  `research-report-v1` report.

### Explicitly not in this change

**No research price is charged and no stored resource moves** — none is committed, and the legacy branch
charges nothing. **No completion or readiness semantics**: the counters are read by nothing, so deriving
either would invent a rule. **No counter bounds, membership rules, or clamps** are added — the legacy
branches have none, and authoritative validation belongs to Server v1 / M13. **No rewards**: there is no
committed reward for research anywhere, not even a zero-valued one. **No committed research content is
invented** — no normalized section exists and `config/main.json` has no `research` key, so the line ships
the committed `Research Lab` building name and the two committed building ids as *content reported*, and
nothing else. **No client-trusted resource deltas.** Legacy sources, configs, saves, the sixteen
delivered fixture directories, conversion packages, and registry manifests stay byte-identical. No Flash,
Ruffle, ActionScript, or browser executes, and every network call is loopback.

## Capabilities

### New Capabilities

- `godot-research`: the two-track research counter vector as a typed, server-authoritative projection —
  both tracks, all three counters verbatim, the four branch effects recorded as data, the
  `fast_forward` writer named, the committed track-to-building mapping reported without being used, and
  the explicit absence of any price, bound, readiness rule, or reward.

### Modified Capabilities

- **`godot-unit-behaviors`**: its living spec claims the dead-hero ledger has **three** helper doors
  (`kill`, `sell`, `resurrect_hero`). The M9 investigation disproved that count: **`map_lose_item`
  (`engine.py:215-228`) calls `push_dead_unit`**, so a unit lost in a quest is pushed onto the ledger
  through the same helper. The count is **four**. This is a **correction of a delivered claim that
  measurement has falsified**, and it is corrected here rather than left standing.
- **`godot-compatibility-boot`**: the new typed research operations join its operation list, with the
  counter values named as server-derived.

## Impact

- **Compatibility API v0** — a new `research_envelope.py`, four action routes, an
  `apply_research_action` dispatcher, and post-execution proofs. The compat suite will **grow**.
- **Godot client** — a new `scripts/units/research_flow.gd` (or progression path), a new hermetic
  `tests/test_research.gd`, typed research operations on both GameApi implementations, scope-test
  allow-list entries, and evidence under `apps/client-godot/evidence/research/`.
- **Fixture capture** — a new `capture_research_fixture.py`, run against the committed corpus in a
  disposable copy, recording the counter mutations the real legacy server performs.
- **Verification** — `verify-boot.ps1` gains the hermetic suite and a `research-live` phase.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status ledger.