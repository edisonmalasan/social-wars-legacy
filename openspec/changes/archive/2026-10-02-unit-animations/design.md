# Design

## Context

The contract is established in `docs/legacy-unit-animations.md` (PR #237, merged `ff77e8f`).
Restated compactly, because every decision below rests on it:

- **No animation command.** 63 named dispatcher branches; the five containing animation vocabulary
  are substring artifacts (`move`, `orient`, `batch_remove`, `remove_inventory_item`, `end_attack`).
- **Six animation-adjacent committed fields, zero legacy reads each**: `max_frame` (429 units, 2
  distinct), `img_name` (401), `attack` (131), `attack_interval` (12), `attack_range` (14),
  `velocity` (11), plus the `animal` flag. `max_frame` is `5` on 427 units, `2` on ids 923 and 933,
  and `1`/`2` on all 470 buildings. Its committed encoding is a JSON **number**.
- **The asset carries the states.** `assets/converted/units/10033_wild_elephant/package.json`:
  sprite 63 has 29 frames and labels `QUIETO`@1, `ANDAR`@6, `ATAQUE`@11, `MUERTE`@16, `PICAR`@21;
  five sprites at 20 frames, one at 7; recorded `frame_rate` 30.0; root timeline one frame, no
  labels, single placement `move: False`.
- **The measured contradiction**: committed `max_frame` **2** vs parsed root `frame_count` **1** vs
  the labelled sprite's **29**, for the same unit (`img_name == legacy_id`).
- **One** converted unit package and **one** building package are committed.
- M4's recorded limit: no tessellation, **no playback semantics**, labels **names-only**.

## Decisions

**D1 — the deliverable is a linkage projection plus explicit refusals, and it is a real deliverable
(the scoping decision).** No legacy branch selects an animation state, so a "unit animation
feature" would have to be invented. What is deliverable is the **linkage projection** — the labels,
their frame positions, the per-sprite frame counts, and the recorded rate — plus the **inventory**
and **refusals** that make the absence auditable. This is not a stub: without it, the five labels are
exactly what a later line would reach for to build a state machine, with no committed transition rule
to anchor it. The record closes that door with the evidence attached, matching the delivered
`godot-unit-production`, `godot-unit-movement`, and `building-xp` refusal shapes.

**D2 — `max_frame` is reported as content, and its non-equivalence to the asset frame count is a
first-class recorded fact rather than a footnote (the correctness decision).** The projection
exposes `max_frame` **verbatim** because it is a committed field, and separately records the
measured disagreement: **2** against **1** and **29**. This is the decision the whole investigation
turned up, and it is the reason the line must state the non-equivalence as a requirement: a later
line reading only the *name* `max_frame` would reasonably but wrongly adopt it as a frame count. The
recorded fact is one data point, labelled as such, and the requirement is written as a **refusal to
adopt**, never as a claim about what `max_frame` means.

**D3 — the refusal set covers every playback rule, each with a reason, and the suite asserts the
absence of the helpers (the anti-invention guard).** No frame duration, loop count, state machine,
transition, priority, interrupt, playback order, per-state timing, animation trigger, or
event-to-state mapping. The suite compares the module's whole function inventory against a pinned
list, so a `duration_of`, `next_state`, `should_loop`, or `play` helper fails the run wherever it is
added. The guard must then be **tested by injection**, as the `movement` and `production` lines did.

**D4 — no endpoint, because there is no server-selected state to expose (established, and the same
conclusion M8 lines 1, 2, 4, and 6 reached).** Animation is chosen by nothing: no branch writes a
state, and the client-side instant a readiness check would trust is client-writable by
`fast_forward`. So the compat suite must stay green **unchanged**, and stating it as a requirement
stops a later line assuming an animation endpoint exists.

**D5 — the projection covers exactly the one committed package, and the report says so (the
generality decision).** Only one converted unit package exists, so the projection is exercised over
**that** package and the refusal generalises to all units as a statement about the legacy source
rather than about the assets. The report records the coverage explicitly, so a later line that
converts more packages extends the coverage visibly instead of assuming it was always there.

**D6 — `godot-unit-definitions` delegates the animation reading rather than duplicating it (the
non-duplication decision).** That capability already reports sprite **resolution** status through
the asset-ID registry. This line adds the **timeline** reading. Separating "does the reference
resolve" from "what does the timeline contain" keeps each capability's claim narrow and its
evidence specific, and the delta states the boundary so the two cannot drift.

**D7 — evidence, claim limits, and containment.** A deterministic `unit-animations-report-v1` report
recording the labels and frame positions verbatim, the per-sprite frame counts, the recorded rate,
the six-field inventory with zero-consumer statements, the `max_frame` distribution and its
non-equivalence, the one-package coverage, the established-versus-derived split, and every
non-claim — byte-identical across reruns. **No windowed capture is claimed**: nothing is animated,
nothing new is rendered, and a capture would assert nothing. Containment: no new packages, **no
network at all**, both batteries plus the guard baseline, the 3,258-entry hash manifest, and the
content validator green in the final state.

## Risks / Trade-offs

- **A refusal line can feel like nothing was delivered.** Mitigated by D1's framing and by D2: the
  line closes a specific, named trap — the `max_frame` misreading — and its requirements are
  positive statements about what the projection *does* report.
- **The `max_frame` contradiction rests on one data point.** Accepted and stated three times over
  (investigation, design, report). The requirement is deliberately phrased as a refusal to adopt
  rather than as a claim about meaning, which is exactly what one data point supports.
- **Reporting five labels could invite a state machine.** Mitigated by D3's requirement barring
  transitions and by the report recording that no legacy branch selects a state.
- **Only one converted package exists**, so the projection's coverage is thin. Mitigated by D5: the
  coverage is recorded, and extending it later is a visible addition.
- **Inventory staleness** as later lines add fields. Accepted: it is scoped to the committed legacy
  source's closed command set and the committed package, and a later line extends it explicitly.
- **No fixture could read as missing evidence.** Mitigated by the report's non-claims: there is
  **no animation behaviour for the legacy server to have**, which is stronger than a corpus
  limitation — the same shape as the delivered `movement` and `production` records.
