# Design

## Context

The contract is established in `docs/legacy-unit-instances.md` (PR #208). Its facts,
restated compactly because every decision below rests on them:

- The legacy row is `[item, x, y, timestamp, orientation, store, attr, player]`
  (`engine.py:31`). **A unit instance is a row.** `push_unit` appends a popped row into
  `building[5]` and stamps `building[3]`; `pop_unit` scans slot 5 for a matching
  `item[0]` and pops it. A garrisoned unit is a **row nested inside a row**.
- `nu` (count), `ts` (start instant), and `ui` (queued unit id, atom-fusion only) live
  in the **building's `attr` bag** and are deleted together at zero
  (`engine.py:183-213`).
- `unit_capacity` has **zero** occurrences in five legacy modules.
- `training_time` is on 130 of 470 buildings, `unit_capacity` on 48 of 470, and the two
  sets are **disjoint**. 0 of 429 units carry either.
- `in_store` is 0 for all 429 units; `offer_packs` (109 refs) and `darts_items` (44) are
  the only committed unit sources.
- `push_dead_unit` stores a **count** in `privateState["deadHeroes"][item_id]` and
  **discards the row**; it needs player team, a `properties` bag, and
  `resurrectable > 0` (426 of 429 units have it).
- The corpus: 40 rows, 11 distinct item ids, all `type` `b`; **0 units**, 0 non-empty
  slot 5, **every `attr` bag `{}`**; one placed training producer at key 1 (id 26
  Command Center, `training_time` 5, `min_level` 1).
- The stored `config/main.json` items carry `type` but **no `kind`** — `kind` is a
  normalization artifact, so the legacy discriminator is `type` alone.

## Decisions

**D1 — `UnitInstance` wraps a row plus its resolved definition; it is not a copy and
not a widened definition (established shape, derived composition).** The evidence says
a unit instance *is* a row, so the honest model is a typed view **over** a row, holding
the row and its `UnitDefinition` rather than duplicating the definition's fields. That
also makes the M8 line 1 boundary structural: a `UnitInstance` **has** a definition, so
nothing in the definition can be instance state, and the definition stays immutable.
Deriving the row's item identity from the definition (not the other way round) means a
row whose committed `type` is not `u` is **rejected**, never coerced.

**D2 — the garrison is a nested row, parsed recursively, and slot 5 is a row list
(established).** `building[5]` holds rows, so each element is parsed as a `UnitInstance`
in its own right. Nesting is bounded by a named maximum depth: a save is untrusted
input, and unbounded recursion over attacker-supplied nesting is a denial-of-service
surface. Exceeding the bound **fails closed** with an error naming the key and the
depth — never truncates silently, because a truncated garrison is a wrong answer
presented as a right one.

**D3 — the projection resolves rows by committed `type`, never by `kind` (established;
the `kind` half is the decision).** M8 line 1's `UnitDefinition` exposes `kind: "unit"`
because the normalization adds it; the stored config has no such field. The projection
therefore discriminates on the committed `type` (`u` for a unit, `b` for a building), so
a row is classified by a field the legacy save actually carries. `kind` remains
available on the definition as a normalization artifact and is not used as a gate.

**D4 — no endpoint, no compat change, and no fixture (established by the reachability
table).** An instance is read from a save, not fetched from a server, so there is no
intent to send and nothing to authorise — the same conclusion M8 line 1 reached for
definitions. And no fixture can be captured without fabricating a player state, because
the corpus has no unit row. Both are recorded in the spec as explicit non-claims rather
than worked around, and the compat suite must stay green **unchanged**.

**D5 — `unit_capacity` is recorded, never enforced (established; the refusal is the
decision).** The engine appends to slot 5 unconditionally and no legacy module reads
the field. A garrison therefore has **no capacity limit in this model**, and the report
records the committed capacities alongside the explicit statement that no rule is
implemented. This is the `building-xp` precedent applied to a second unread content
field. A server-side limit belongs to M13.

**D6 — the production-queue keys are reserved and named, not implemented (established
shape; the scope is the decision).** `nu`, `ts`, and `ui` are declared as a typed
`RESERVED_ATTR_KEYS` inventory with their established meaning and the three-key teardown
rule recorded, so the `queues` and `production` lines inherit a named contract. This
change adds **no** increment, decrement, timestamp write, or queue projection. Reading
the reserved keys off a row and reporting whether a queue is present is projection, not
behaviour; writing them is behaviour and is out of scope.

**D7 — the dead-unit counter is recorded, never modelled as an instance (established).**
`push_dead_unit` discards the row and keeps a count, so a dead unit has **no** instance
to project. The count is read and reported as a plain integer map; no corpse, no
resurrection state, and no `resurrectable` evaluation — that last one is a *death* rule
belonging to a combat line, and the 426-of-429 coverage is recorded as content, not
applied as a predicate.

**D8 — the zero-instance result is an assertion, not a shrug (the honest-reporting
decision).** The committed corpus yields **zero** unit instances. The suite asserts that
zero explicitly, asserts that all 40 rows classify as buildings, and asserts that the
projection would return instances for a corpus that had them — via a crafted in-memory
row set, never a fabricated save file. A projection that cannot be shown to work on
*any* input would be untested, and the alternative — writing a unit row into a
disposable corpus to manufacture a fixture — is precisely the fabrication this change
refuses. The crafted rows are clearly labelled as test input, not as evidence of
behaviour.

**D9 — evidence, claim limits, and containment.** A deterministic
`unit-instances-report-v1` report recording the row contract and its source lines, the
corpus measurements (40 rows, 11 distinct ids, 0 units, 0 non-empty slot 5, all-empty
`attr` bags), the zero-instance result, the garrison container contract, the dead-counter
contract, the reserved-key inventory, the committed `unit_capacity` distribution with
the no-rule statement, the established-versus-derived split, and the non-claims —
byte-identical across reruns. **No windowed capture is claimed**: nothing is rendered and
no unit exists to render, so a capture would assert nothing. Containment carries forward:
no new packages, no network at all, both batteries plus the guard baseline, the
3,258-entry hash manifest, and the content validator green in the final state.

## Risks / Trade-offs

- **A model with no fixture is easy to over-read as "units work".** Mitigated by D4's and
  D8's explicit spec non-claims and the report's non-claim list naming every behaviour
  line as undelivered.
- **Recursive nesting introduces a stack-depth surface.** Mitigated by D2's named bound
  and fail-closed refusal; a crafted over-deep row set is asserted in the suite.
- **Classifying on `type` while the definition exposes `kind` could confuse a reader.**
  Mitigated by D3's explicit rationale and by recording in the report that `kind` is a
  normalization artifact absent from the stored config.
- **Reserving queue keys without implementing them could invite a later line to treat
  the reservation as the behaviour.** Mitigated by D6's explicit "no increment,
  decrement, timestamp write, or projection" and by the spec requirement stating the
  reservation is content-level only.
- **Refusing capacity could look like a missing feature.** Mitigated by D5's recorded
  distribution and the explicit no-rule statement: the alternative would invent a rule
  the legacy server does not have, which is the failure mode this project has refused
  three times already.
