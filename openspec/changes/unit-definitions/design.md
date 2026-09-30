# Design

## Context

See `proposal.md` — Why. This is M8's first deliver line and the first M8 change that is
**not** a legacy-behaviour derivation: everything it needs is committed content, already
verified by the registry.

### Established by committed artifacts

- **`packages/game-content/normalized/units.json`**: a bare list of **429 rows**. Every row
  carries `kind: "unit"` and `type: "u"`, a **distinct string `legacy_id`** spanning
  `923`..`1431`, `name`, `img_name`, `race`, `content_version`, `source_file`
  (`config/main.json`), and `source_layer` (`stored`). **53 fields**, of which 51 are
  present on every row and two — `breeding_order` and `sm_training_time` — on **300 of 429**
  each. Two fields are embedded-JSON **strings** requiring parsing (`costs`,
  `properties`), and three are nullable (`inventory_ids`, `premium_upgrade_costs`, plus
  `best_against` as a meaningful empty string).
- **`packages/game-content/schemas/unit.schema.json`** already defines the contract for
  one normalized unit, so the field set is committed, not inferred.
- **`ContentRegistry`** loads all 22 manifest outputs, names each domain by file basename,
  verifies **byte count and SHA-256 before parsing**, indexes each domain by
  `str(legacy_id)` with duplicate rejection, and exposes `has_domain`, `count`, `counts`,
  `domains_list`, `get_entry`, `content_fingerprint`, and the asset-ID resolution path
  (`resolve_asset`). **`units` is therefore already a loaded, verified domain today.**

### Established by the delivered predecessor

`apps/client-godot/scripts/town/placement_catalog.gd` is the precedent this line follows
for a building catalogue: it parses **only** the fields the flow needs, fails closed on
every malformed field, and **never guesses a price or fabricates an entry**. It also
documents the transport tolerance (the committed payload stores numbers as JSON strings,
so integers accept digit strings, ints, and integral floats — the pinned engine's
documented tolerance). Its header comment names why: a guessed price would contradict the
spec's "rather than guess a price or fabricate an entry".

### Established by the M8 entry position (not re-derived)

The committed fresh-player corpus has **no unit placements** and 0 of 40 placed rows
carry `attr["xp"]`; M4's converted Wild Elephant package proves **asset linkage and
renderability, not animation or gameplay semantics**; and the content package already
carries the 429 committed definitions.

## Decisions

**D1 — the model is a static `UnitDefinition`, read-only, resolved from the registry
(established).** One definition carries no player state, so it is immutable by
construction: the model exposes typed fields and never mutates. Resolution goes **only**
through `ContentRegistry.get_entry("units", legacy_id)`, so the manifest's byte-count and
digest verification and the registry's duplicate rejection remain the single gate — the
model cannot see unverified content. A `ContentRegistry` that has not loaded, or that does
not carry a `units` domain, is a **fail-closed** condition, never an empty catalogue.

**D2 — the static/instance boundary is a stated requirement, not an implicit convention
(established, and the point of the line).** `UnitDefinition` is content; a future
`UnitInstance` is player-owned save state with its own placement key, health, garrison,
and ownership. This change adds **no** `UnitInstance` type, **no** save shape, **no**
instance parsing, and **no** endpoint, and the spec says so explicitly so the
`unit instances` line inherits a named boundary instead of discovering one. The practical
consequence in code: the model has no field that could hold instance state — no key, no
coordinates, no owner, no current health — so a future instance cannot be smuggled in by
widening a definition.

**D3 — parsed fields are verbatim and carry no gameplay semantics (established; the
no-semantics half is the decision).** The model parses the committed fields in five named
groups so a reader can see what exists: identity/presentation (`legacy_id`, `name`,
`img_name`, `type`, `kind`, `race`, `display_order`), footprint and placement (`width`,
`height`, `elevation`, `population`, `volume`, `max_elem_vol`, `max_frame`),
statistics (`attack`, `defense`, `life`, `attack_interval`, `attack_range`, `velocity`,
`expiration`, `best_against`, `best_against_mult`), economy (`costs`, `cost`,
`cost_unit_cash`, `collect`, `collect_type`, `collect_xp`, `xp`, `unit_capacity`), and
training/upgrade (`training_time`, `sm_training_time`, `breeding_order`, `upgrades_to`,
`syringes`, `min_level`, `activation`, `clicks_to_build`, `build_time`). **Critically: the
statistics are exposed as committed numbers with no combat, damage, speed, or timing
semantics attached.** `attack: 10` is a number in a definition, not a damage rule; nothing
in this line computes with it. That is stated in the model's docstring, in the catalog's,
in the capability spec, and in the report's non-claims, because the alternative — a
`damage()` helper — would be exactly the "prematurely implement" failure this line exists
to avoid. Fields outside the five groups stay reachable through one documented raw-entry
accessor rather than being silently dropped.

**D4 — fail closed on every malformed field, with the two embedded-JSON fields parsed and
the three nullable ones accepted as absent (established precedent).** Mirroring
`placement_catalog.gd`: a malformed field returns `{ok: false, error}` naming the item and
field and produces **no** definition — nothing is guessed, defaulted, or coerced into a
meaningful value. `costs` and `properties` are embedded-JSON strings in the committed
package and are parsed with the **same letter vocabulary the delivered endpoints already
use** (`g`/`c`/`w`/`o`/`s` onto gold/cash/wood/oil/steel), because the delivered purchase,
shop, expand, and level lines already established that mapping and this line must not
re-derive or contradict it; an unknown cost key or a non-integer amount fails closed.
`inventory_ids`, `premium_upgrade_costs`, and `breeding_order`/`sm_training_time` when
absent are **absent**, never zero — a zero would be indistinguishable from a committed
zero.

**D5 — legacy IDs are preserved verbatim as strings, and uniqueness is asserted
(established).** The registry already rejects duplicate `str(legacy_id)` within a domain,
and this line preserves the **string** form — the normalized package records `legacy_id` as
the 0-based index elsewhere but here it is the **legacy item id** (`"923"`), and coercing it
to an integer would break lookups against the registry's index. The suite asserts all 429
ids are distinct strings and that a lookup by each of a sampled set returns its own
definition, and that a numeric lookup with the wrong form fails closed rather than
coercing.

**D6 — no endpoint, because a definition is not server state (established; the same
conclusion the resources line reached after its own premise proved wrong).** The compat
surface has nothing to add: a unit definition is committed read-only content that the
client's registry already serves, so there is no intent to send and nothing to authorise.
The compat suite must stay green **unchanged**, and this is stated as a claim so a later
line cannot assume a unit endpoint already exists.

**D7 — the only asset claim is the registry's own resolution (established, and narrow).**
A definition names `img_name`, and the registry can resolve an asset reference through the
committed asset-ID registry with a recorded status vocabulary. So the model may report
**whether** the committed sprite reference resolves and its recorded status — and
establishes nothing about rendering, animation, or visual fidelity, exactly as M4's
converted-package README states for its own output. The line asserts the **linkage** and no
more.

**D8 — evidence, claim limits, and containment.** A deterministic
`unit-definitions-report-v1` report recording the committed counts (429 definitions, the
legacy-ID range and distinctness, the manifest digest and fingerprint, the per-group
parsed-field inventory, the two absent-field groups with their 300/429 coverage, the
raw-entry escape hatch, the asset-linkage statuses, and the static/instance boundary) with
the non-claims, byte-identical across reruns. A windowed capture is **not** claimed for
this line: there is no visual change and no unit is rendered, so a capture would assert
nothing. Containment carries forward unchanged: no new packages, loopback only where a
network is used at all (none is needed), both batteries plus the guard baseline, the
3,258-entry hash manifest, and the content validator green in the final state, and the
orchestrator-run integration review as the fallback for the unavailable dedicated
verification workflow.

## Risks / Trade-offs

- **A statistics field invites misuse.** `attack`, `defense`, `life`, and `velocity` look
  like a combat model but are committed numbers with no committed consumer — nothing in the
  legacy server reads a unit's statistics. Mitigated by D3's explicit no-semantics rule and
  by the report's non-claims, so a later line derives behaviour from evidence rather than
  inheriting an invented rule from a parsed field.
- **Parsing 53 fields could couple the client to content shape.** Mitigated by D3's five
  named groups plus D4's single documented raw-entry accessor: a new committed field is
  reachable without touching the model, and a removed field is not silently tolerated.
- **The `costs` letter vocabulary is inherited, not re-derived.** Mitigated by D4's
  requirement that it match the mapping the delivered endpoints already implement, so the
  unit definition cannot disagree with what buying a unit would actually cost.
- **A definition model with no instance is easy to over-read as "units work".** Mitigated by
  D2's stated requirement and by the report's non-claims naming every behaviour line as
  undelivered.
- **No capture evidence.** Mitigated by D8: a capture would prove nothing for a line with
  no visual change, and saying so is more honest than manufacturing one.