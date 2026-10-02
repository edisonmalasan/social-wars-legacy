# Design

## Context

Restated compactly from `docs/legacy-m9-progression.md` §11–§13, because every decision below rests on it:

- **Four** dispatcher branches, `command.py:268-274`, `276-282`, `284-291`, `293-300`.
- **Two** tracks, `0: TYPE_AREA_51`, `1: TYPE_ROBOTIC` — named **only** in those four comments and
  defined nowhere.
- **Three** counters, each a 2-element list: `researchStepNumber`, `researchItemNumber`,
  `timeStampDoResearch`.
- Effects: `next_research_step` → step `+= 1`, stamp `= time_now`. `research_buy_step_cash(cash, _type)`
  → stamp `= 0`, **`cash` read and discarded**. `next_research_item` → item `+= 1`, step `= 0`,
  stamp `= 0`. `reset_research_item` → all three `= 0`.
- **Every one of those sites is a write.** The single read of `timeStampDoResearch` outside the branches
  is `command.py:923`, inside `fast_forward`, and it writes: it subtracts a **client-supplied** `seconds`
  from each element, clamped at `0`.
- A guard audit of all four branches finds **no** bounds check, numeric clamp, membership test, exception
  guard, or existence check.
- **No committed research content.** No normalized package has a research section. `research` appears in
  exactly one normalized file, `buildings.json`, only inside one `name` — `legacy_id` 256,
  `"Research Lab"`. `config/main.json` has **no** key containing `research` at any depth.
- Committed track ids: `constants.py:299-300`, `ID_BUILDING_ROBOTIC_CENTER = 86`,
  `ID_BUILDING_AREA_51 = 139`.
- Corpus: all three counters `[0, 0]`.

## Decisions

**D1 — the deliverable is the counter mechanics, and every derivation is refused (the scoping
decision).** This line is *not* a refusal line and must not be written as one: the counters genuinely
mutate, the corpus genuinely exercises all four branches, and an executed-legacy fixture is capturable.
But the counters are **read by nothing**, so there is no rule to reproduce — only state to move. The line
therefore delivers the projection plus the four branch effects as data, and states as requirements that
no readiness, completion, remaining-time, or unlock semantics exist. Delivering a refusal here would be
wrong twice over: it would deny a real mutation, and it would invent the absence of something the
source never looked for.

**D2 — intent-only surface: the client sends a player identifier and a track, nothing else (the
authority decision).** Every legacy branch takes `_type` from the client and mutates the counters
directly. Reproducing that would mean accepting client counter values, which `AGENTS.md` names as the
"Bad" pattern. So each endpoint accepts **only** `{user_id, track}` and the service advances the vector
itself. This is the same rule `unit-collection` applied to a client-sent prize: keep the legacy
*behaviour*, reject the legacy *trust*. `research_buy_step_cash`'s `cash` is the clearest case — the
client may still send one, and it is **discarded rather than charged**, exactly as `used_syringe` was.

**D3 — the discarded cash is proved non-charging, not merely refused (the proof decision).** A refusal
stated in prose is a claim; a post-execution check over the full resource set is evidence. Every research
action's post-execution proof therefore includes that **every stored resource is byte-identical**
before and after — the same form `level_up` and `resurrect` use, and the reason M8 line 8 could say its
no-cost claim was non-tautological. The check compares all seven stored resources, not a selected subset,
so a future change cannot smuggle a delta through an uncompared slot.

**D4 — no content is invented, and the absence is stated as a finding (the non-invention
decision).** There is no research cost, step count, unlock requirement, or reward in the committed
content — not merely unrecorded but **absent**, since no normalized section and no config key exists. A
line that derived a step count from the building footprint or a price from a coin table would be
fabricating an economy. The line instead ships the two facts that *are* committed: the `Research Lab`
building name, and the two building ids the track names resolve to — **reported, and asserted never to be
used** in any computation.

**D5 — the track-to-building mapping is reported but structurally unusable (the decision that makes D4
mechanical).** `TYPE_AREA_51` and `TYPE_ROBOTIC` exist only in branch comments. The suite asserts that
**no code identifier in the delivered module is named after either**, so a later reader cannot mistake the
reported mapping for a used one. This is the same discipline M8 line 7 applied to `max_frame`, which
forced the accessor to be named `non_equivalence_record()`.

**D6 — no bounds, membership, or clamp is added (the parity decision).** A client could send track `7`
and Python would raise `IndexError` on a 2-element list; a client could send `999` and the counter would
grow without limit. Both are legacy behaviours. Reproducing them means **not** inventing validation, and
recording both as Server v1 / M13 gaps. The endpoint enforces only *structural* input validity — that the
track is an integer and the state vector is well-formed — because a service that cannot address its own
state is not delivering behaviour.

**D7 — `fast_forward` is recorded as a fourth writer, and its client-writable nature is named (the
cross-branch decision).** The M9 investigation found that `fast_forward` subtracts a client-supplied
number of seconds from every research stamp. That makes the research instant **client-writable** in
exactly the way M8 line 6 found a row's instant client-writable, and it is named here because it is the
only elapsed-time input the research system has — an instant trusted by nothing, in a system where
nothing reads it. The line **implements no fast-forward route**; it records the writer.

**D8 — the `godot-unit-behaviors` door count is corrected here (the honesty decision).** That capability's
living spec says the ledger has three helper doors. Measurement makes it four, because
`map_lose_item` (`engine.py:215-228`) calls `push_dead_unit`. Its record was correct *about the
dispatcher branches* — `map_lose_item` is an engine helper, not a branch — but the door count as stated
is falsified. Correcting a delivered claim is in scope for the line that disproved it; leaving a spec
asserting a false count while shipping a projection of the same subsystem would be worse.

**D9 — fixtures are captured, because the corpus can exercise this (the evidence decision).** This is the
contrast with M8 line 8, where `resurrectable` is unit-only and the corpus holds no unit row, so no
fixture existed and the absence was the finding. Here all three counters sit at `[0, 0]` in the committed
corpus, so a one-shot executed-legacy capture of the counter transitions is genuinely capturable. The
fixture records the real server's before/after for each branch, and the endpoint's parity tests replay it.

**D10 — evidence, claim limits, containment.** A deterministic `research-report-v1` report recording the
counter vector, the four branch effects, both tracks with their committed ids, the `fast_forward`
writer, the absent-content findings, and every non-claim, byte-identical across reruns. **No windowed
capture is claimed** — nothing is rendered, and the two research buildings are not placed in the corpus.
Containment: **loopback network only**, both batteries plus the guard baseline, the 3,258-entry hash
manifest, and the content validator green in the final state.

## Risks / Trade-offs

- **Adding state-mutating endpoints grows the compat suite and adds a live phase.** Accepted: four real
  branches, four real mutations.
- **The endpoint is stricter than the legacy branches** (it derives the counters instead of accepting
  them). D2 records this so the divergence is deliberate and visible.
- **The counters have no consumer, so the delivered feature is unobservable in-game.** That is the
  finding, not a gap in the line. Any future claim that research "works" must mean these specific counter
  transitions and nothing more.
- **No committed content means no derived schedule.** Accepted as D4: inventing one would be worse than
  shipping none.
- **`fast_forward` can rewrite the stamp arbitrarily.** Recorded, not implemented, and named as a M13 gap.
- **Coverage of the four branches is by executed fixture plus hermetic input**; the two tracks are
  exercised for both, giving eight branch-track combinations.