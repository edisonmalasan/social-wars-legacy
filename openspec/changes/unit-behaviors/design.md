# Design

## Context

The contract is established in `docs/legacy-unit-behaviors.md` (PR #244, merged `2e98d55`).
Restated compactly, because every decision below rests on it:

- **Twenty** behavioural committed fields measure **zero** legacy consumers across the seven
  modules; **two** do not.
- **`resurrectable`**: **426 of 429 units**, **0 of 470 buildings**, exactly **two** reads at
  `engine.py:159,162`, inside `push_dead_unit`.
- **`clicks_to_build`**: one read at `engine.py:26` inside `map_add_item`, seeding `attr["nc"] = 0`.
- `privateState["deadHeroes"]` is a **string-keyed count per item id**.
- **`kill`** (`command.py:169-181`) deletes the row and **never** touches the ledger.
- **`sell`** (`command.py:149-167`) calls `push_dead_unit` **only** when `reason == "KILL"`.
- **`resurrect_hero`** (`command.py:625-635`) calls `resurrect_hero` (`engine.py:172-182`), which
  decrements and **deletes the key at zero**, then `map_add_item`s the row at **client-supplied**
  `index`/`x`/`y`; `used_syringe` is read from `args[4]` and **discarded**.
- Both legacy reads go through `get_attribute_from_item_id(...)` then `json.loads(properties)`, so
  the server reads the **raw config string** while the normalized package stores an **object** — the
  R2 coercion boundary M8 line 1 recorded.
- The corpus: `deadHeroes` present and **`{}`**; **0 of 40** placed rows resurrectable; **no unit
  row**.
- 63 named dispatcher branches; `kill` and `resurrect_hero` are branches, `push_dead_unit` is an
  engine helper.

## Decisions

**D1 — this line delivers a mechanism, not a refusal, and the proposal's scope follows the
measurement (the scoping decision).** The last three M8 lines each delivered a projection plus
refusals because no mechanism existed. Here one does: a two-sided, server-authoritative counter with
two named gates and a delete-at-zero rule. Delivering a refusal here would be the *more*
conservative-looking choice and the *wrong* one, because it would leave a real server mutation
unimplemented while the committed `resurrectable` flag sits on **426 of 429** unit definitions
looking like dead content. The line therefore adds a real endpoint, the first M8 line since
`collection` whose transaction is both server-derived and state-mutating.

**D2 — the endpoint derives the revived item id and the map key server-side, and ignores
`used_syringe` (the authority decision).** The legacy branch takes `index`, `item_id`, `x`, and `y`
all from the client, which is the untrusted pattern `godot-building-move` and `godot-building-collect`
already record. This contract keeps the legacy *behaviour* and rejects the legacy *trust*: the client
sends **only** a player identifier and a cell, the service resolves the ledger entry for that cell
itself, and the client-supplied `used_syringe` is discarded rather than charged. That is the same
rule the `collection` line applied to a client-sent prize, and the reason the compat suite's
post-execution proof can compare against server-derived values.

**D3 — no syringe cost, and the refusal is a requirement rather than a footnote (the non-invention
decision).** `syringes` is committed on all 429 units with **6 distinct values** and **zero** legacy
consumers, so the legacy server charges nothing. Charging one would invent an economy, and a player
watching revival consume a resource the server never checked would be a behaviour no legacy branch
implements. The endpoint's post-execution proof therefore includes the **seven stored resources are
unchanged** half, which is what makes the no-cost claim non-tautological — the same proof form the
`level_up` line established for exactly this reason.

**D4 — the corpus's inability to exercise this is recorded, not engineered around (the fixture
decision).** `resurrectable` is **unit-only**, the corpus places **only buildings**, and its
`deadHeroes` is `{}`. A one-shot executed-legacy fixture would require manufacturing a unit row
first, which `godot-unit-instances` already refused and recorded as the right call. So this line has
**no** executed-legacy fixture — and unlike the refusal lines, the reason is *not* the absence of
behaviour. It is the absence of a **resurrectable row in the corpus**, and the distinction is stated
explicitly so the distinction is never lost.

**D5 — the placement validation refusals are stated requirements (the boundary decision).** The
legacy `resurrect_hero` branch re-places the row with no occupancy, bounds, type, or terrain check.
This line reproduces that — it does not invent validation it cannot derive — and records the gap as
a Server v1 / M13 requirement, exactly as `building-move`, `building-place`, and `building-upgrade`
already do. Inventing an occupancy check here would make the modern client *stricter* than the
legacy server, which is a parity break in the opposite direction from the usual risk.

**D6 — `clicks_to_build` is referenced, never reimplemented (the non-duplication decision).** Its
single consumer seeds the `{"nc": 0}` counter that `godot-building-construction` already delivers,
reports, and deliberately does not consume. This line names that relationship in the inventory and
touches nothing.

**D7 — the anti-invention guard is structural and then tested by injection.** The suite compares the
module's whole static-function inventory against a pinned list, so a `syringe_cost`, `resolve_damage`,
`apply_attack`, `is_occupied`, or `charge_revive` helper fails the run wherever it is added. The
guard must then be exercised by injection, as the `production`, `movement`, and `animations` lines
each did — a guard that is only asserted is not evidence.

**D8 — evidence, claim limits, and containment.** A deterministic `unit-behaviors-report-v1` report
recording the ledger projection, the three-door inventory, both gates, the delete-at-zero rule, the
`used_syringe` discard, the twenty zero-consumer fields with their distributions, the corpus
measurement, the established-versus-derived split, and every non-claim — byte-identical across
reruns. **No windowed capture is claimed**: a revived unit needs a unit row, and the corpus has
none, so nothing would be rendered that is not already rendered. Containment: no new packages,
**loopback network only**, both batteries plus the guard baseline, the 3,258-entry hash manifest, and
the content validator green in the final state.

## Risks / Trade-offs

- **Adding a state-mutating endpoint grows the compat suite and adds a live phase.** Accepted: the
  mechanism is real, and the `collection` line set the precedent for exactly this trade.
- **The endpoint is stricter than the legacy branch** (it derives the key instead of accepting it).
  This is the established project rule — the legacy client is the reference for *behaviour*, not for
  *trust* — and D2 records it explicitly so the divergence is visible rather than accidental.
- **No executed-legacy fixture could look like weaker evidence than the refusal lines delivered.**
  Mitigated by D4: the reason is a corpus limitation with a named cause, not an absence of behaviour,
  and the deliverable is a mechanism rather than an absence.
- **The death/resurrection pairing is derived.** Mitigated by recording it as derived in the
  investigation and never asserting it as a server guarantee — the two functions are complementary and
  share the ledger, but no comment or dispatch path asserts the pairing.
- **Coverage is thin**: no committed unit row exists, so every path is exercised over crafted
  in-memory rows with the committed `resurrectable` distribution asserted rather than assumed.
- **`deadHeroes` is initialised to `None` then coerced to `{}` in `version.py`**, which is a migration
  path rather than gameplay. Recorded, not treated as behaviour.
