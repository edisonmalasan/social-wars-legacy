# Design

## Context

The contract is established in `docs/legacy-unit-movement.md` (PR #229, merged `5cd47a1`).
Restated compactly, because every decision below rests on it:

- **`move`** rewrites `item[1] = x`, `item[2] = y` from client args. No type, occupancy, bounds,
  terrain, or speed check. `frame = args[3]` and `string = args[4]` are read and **unused**. It is
  **type-agnostic**, and it **already ships** as M7's `godot-building-move`.
- **Six** writes to a row's slots 0–2 exist across the seven legacy modules; only **`move`** and
  **`pop_unit`** write coordinates (the latter releasing a garrison row at client-supplied
  coordinates with the item id overwritten). **`orient`** writes slot 4 from a client value.
- **`fast_forward`** subtracts a **client-supplied** `seconds` from every row's slot 3 and every
  row's `attr["ts"]`.
- **Zero** legacy reads of `velocity` (positive on **429 of 429** units and 145 of 470 buildings),
  `max_elem_vol`, `width`, `height`, `elevation`, `attack_range`, `ft_flying`, `ft_ground`.
- The legacy SWF's tile geometry was never extracted — the recorded M6 evidence gap.
- The corpus has **no unit row** (40 rows, 11 distinct ids, all committed `type` `b`).

## Decisions

**D1 — the deliverable is a projection plus an explicit refusal, and it is a real deliverable
(the scoping decision).** There is no movement rule to reproduce and no unit-specific command to
deliver, so a "movement feature" would have to be invented. What is deliverable is a **placement
projection** reporting what the row and its committed content actually say, plus the **inventory**
and **refusals** that make the absence auditable. This is not a stub: without it, `velocity` —
non-zero on **every** unit definition — is exactly the field a later line would reach for to build
a travel-time model, with `fast_forward`'s client-writable instant as its clock. The record closes
that door with the evidence attached, which is the same shape as the delivered
`godot-unit-production` refusal and the `building-xp` no-reward refusal.

**D2 — `velocity` and the footprint are reported as content only, with the zero-consumer fact
stated (the reporting decision).** The projection exposes the committed `velocity`, `width`,
`height`, and `elevation` **verbatim**, and states in its own documentation that **no legacy branch
reads any of them**. Reporting the value is useful — a reader can see what the content says —
while the recorded fact prevents it being mistaken for a rule. This mirrors how M8 line 1 reports
`costs` and `properties` as committed content.

**D3 — the movement-command inventory names `move`, `orient`, `pop_unit`, and `fast_forward`, with
what each does and does not check (the auditability decision).** The useful content is not the
list of names but the **classification**: `move` is **type-agnostic and already delivered**; `orient`
is a plain slot write; `pop_unit` is the only other coordinate writer and overwrites the item id;
`fast_forward` is the client-writable instant. A reader who sees only "`move` exists" might assume
a movement rule exists; a reader who sees "`move` is type-agnostic, ships as `building-move`, and
checks nothing" does not.

**D4 — the refusals are stated requirements and the suite asserts the absence of the helpers (the
anti-invention guard).** No travel time, path, terrain or elevation interaction, occupancy, bounds,
readiness, or interpolation. The suite asserts that **no** helper computing any of those exists on
the projection, so a later line that adds one **fails the delivered suite** rather than quietly
reintroducing an invented rule. This is the same technique the delivered `unit-production` line
used, and its guard was verified by injection.

**D5 — no endpoint, because there is no server-derived movement to expose (established, and the
same conclusion M8 lines 1, 2, and 4 reached).** With no mechanism, there is no intent to send and
nothing to authorise, so the compat suite must stay green **unchanged**. Stating it as a spec
requirement prevents a later line assuming a movement endpoint exists.

**D6 — `godot-building-move` is referenced, never reimplemented (the non-duplication
decision).** The command is already delivered. This line adds the **unit** placement *view* and the
recorded facts about the command; it does not touch the endpoint, the flow, or the evidence of that
line. Reimplementing it would duplicate a delivered capability and blur which line owns the move.

**D7 — evidence, claim limits, and containment.** A deterministic `unit-movement-report-v1` report
recording the row's placement fields verbatim, the committed `velocity` and footprint
distributions with their zero-consumer statements, the movement-command inventory with each
command's checks and non-checks, the `fast_forward` recording, the corpus measurement, the
M6 tile-geometry gap, the established-versus-derived split, and every non-claim — byte-identical
across reruns. **No windowed capture is claimed**: nothing is rendered and no unit exists to
render, and a capture would assert nothing. Containment: no new packages, **no network at all**,
both batteries plus the guard baseline, the 3,258-entry hash manifest, and the content validator
green in the final state.

## Risks / Trade-offs

- **A refusal line can feel like nothing was delivered.** Mitigated by D1's framing: it closes a
  specific, named trap, and the spec's requirements are positive statements about what the
  projection *does* report, with the absence stated as contract rather than omission.
- **Reporting `velocity` could invite its use.** Mitigated by D2's explicit zero-consumer statement
  and by D4's requirement barring its use as a travel time.
- **The projection duplicating placement fields could conflict with `godot-unit-instances`.**
  Mitigated by D6 and by the `godot-unit-instances` delta, which assigns the placement *view* to
  this capability while the instance capability keeps ownership of the row — so the two cannot
  drift.
- **Inventory staleness** as later lines add commands. Accepted: it is scoped to the committed
  legacy source's command set, which is closed for that source, and a later line would extend it
  explicitly.
- **No fixture could read as missing evidence.** Mitigated by the report's non-claims: there is
  **no unit-specific movement behaviour to capture**, which is stronger than a corpus limitation.
