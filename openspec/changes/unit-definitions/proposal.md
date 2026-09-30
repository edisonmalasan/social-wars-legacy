# Proposal

## Why

M7 is complete with its exit assessed MET, and the cursor has advanced to **M8 — Units**.
Its deliver list is `unit definitions`, `unit instances`, `queues`, `production`,
`collection`, `movement`, `animations`, `basic behaviors`, and this change delivers the
**first and smallest** of them: **unit definitions**.

This is a **content-delivery line over committed artifacts**, not a legacy-behaviour
derivation — and the repository already holds everything it needs:

- **`packages/game-content/normalized/units.json` is a committed, manifest-verified
  output** of the M3 content normalization: a bare list of **429 rows**, each with
  `kind: "unit"`, `type: "u"`, a **distinct string `legacy_id`** spanning `923`..`1431`,
  53 normalized fields (51 present on every row plus `breeding_order` and
  `sm_training_time` on 300 each), each row carrying its own `content_version`,
  `source_file`, and `source_layer`.
- **`packages/game-content/schemas/unit.schema.json` already defines the contract** for
  one normalized unit, so the field set is a committed contract rather than a reading.
- **`ContentRegistry` already loads all 22 manifest outputs**, naming each domain by its
  file basename, verifying every output's byte count and SHA-256 **before** parsing,
  and indexing each domain by `str(legacy_id)` with duplicate rejection.

So `ContentRegistry.get_entry("units", "923")` works today. What does **not** exist is a
**typed Godot-facing unit model**: the client has `placement_catalog.gd` for buildings —
eight parsed fields, fail-closed, no guessed price or fabricated entry — and nothing
equivalent for units.

That gap is worth closing now, for three reasons that all point forward:

1. **Every later M8 unit line needs it.** `unit instances`, `queues`, `production`, and
   `collection` all read a unit's committed definition (its cost, its training time, its
   capacity, its sprite). Without a typed model each would re-parse raw dictionaries.
2. **The separation the architecture requires can only be drawn once.** A
   `UnitDefinition` is **static content**; a `UnitInstance` is **player-owned state** in
   the save. Drawing that line now, with the static side typed and the instance side
   explicitly absent, is exactly what `AGENTS.md` asks for ("Separate static definitions
   from player state, e.g. `BuildingDefinition` vs `BuildingInstance`") — and it is far
   cheaper to draw now than to untangle after the first instance ships.
3. **The corpus cannot exercise any of it.** The committed fresh-player save has **no
   unit placements at all** and 0 of its 40 placed rows carry `attr["xp"]`, so nothing
   behaviour-bearing about units is testable against it. A definition model is therefore
   the *right* first line: it needs no player state, so it is fully deliverable now, while
   the behaviour lines wait for the corpus question to be answered honestly rather than
   fabricated.

## What Changes

- **A typed static `UnitDefinition` model** in the client, resolved from the registry's
  `units` domain and preserving each definition's legacy ID verbatim. It parses the
  fields a definition *is* — identity and presentation (`legacy_id`, `name`,
  `img_name`, `type`, `kind`, `race`), footprint and placement (`width`, `height`,
  `elevation`, `population`, `volume`), combat and lifecycle statistics (`attack`,
  `defense`, `life`, `attack_interval`, `attack_range`, `velocity`, `expiration`),
  economy (`costs`, `cost`, `cost_unit_cash`, `collect`, `collect_type`, `collect_xp`,
  `xp`), training and upgrade (`training_time`, `sm_training_time`,
  `breeding_order`, `upgrades_to`, `syringes`, `unit_capacity`, `min_level`), and the
  embedded-JSON `properties` bag — and it **fails closed** on any malformed field rather
  than guessing, exactly as the delivered building catalog does.
- **A registry-backed catalog** exposing definition lookup by legacy ID, a count, a
  named-lookup where the committed name is unique enough to be useful, and the raw entry
  for callers that need a field this model deliberately does not parse. It reads only
  through `ContentRegistry`, so manifest verification and duplicate rejection remain the
  single gate.
- **The static/instance boundary drawn explicitly.** `UnitDefinition` is read-only
  content; the model carries **no** player state and the change adds **no**
  `UnitInstance`, **no** save shape, and **no** endpoint. The capability spec states this
  separation as a requirement so the `unit instances` line has a named boundary to grow
  into rather than an implicit one.
- **Tests and evidence** — a hermetic suite over the fake registry covering every parsed
  field group, the fail-closed paths, legacy-ID preservation and uniqueness, the
  asset-resolution link through the registry's asset ID registry (the **only** asset claim
  this line makes), and the absence of any instance or endpoint surface; plus a
  deterministic `unit-definitions-report-v1` report recording the committed counts, the
  parsed field inventory, the boundary, and the non-claims.

### Explicitly not in this change

**Unit instances, queues, production, collection, movement, animation semantics, and basic
behaviors** — each its own later M8 deliver line. No `UnitInstance` type, no save shape,
no `UnitInstance` parsing, no garrison or production-queue state. No endpoint and no
Compatibility API change: a definition is committed read-only content, so the client's
`ContentRegistry` is the only reader and the compat surface is untouched — the same shape
the delivered resources line discovered after its own design premise proved wrong. Also out
of scope: building definitions (already modelled by `placement_catalog.gd`; not duplicated),
asset **rendering** (M4's converted unit package establishes asset linkage, not animation
correctness or rendering), any gameplay meaning for the statistical fields
(`attack`, `defense`, `life`, `velocity`, `attack_interval` are parsed and exposed
**verbatim** with no combat, damage, speed, or timing semantics attached), XP or level
interaction, server-authoritative validation (Server v1 / M13), and any change to the
eleven delivered M7 lines. Legacy sources, configs, saves, villages, committed fixtures,
conversion packages, registry manifests, and every delivered slice's evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). No Flash, Ruffle,
ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-unit-definitions`: the committed unit definitions as a typed, fail-closed,
  read-only Godot-facing model — a static `UnitDefinition` resolved from the
  manifest-verified `units` domain through `ContentRegistry`, preserving every legacy ID,
  exposing only the committed fields verbatim with no gameplay semantics attached, and
  **drawing the static-definition/player-instance boundary explicitly** so the later
  `unit instances` line has a named boundary rather than an implicit one.

### Modified Capabilities

- `godot-compatibility-boot`: the `GameApi` abstraction requirement records that unit
  **definitions** are read from the committed content package through `ContentRegistry` and
  are therefore **not** a GameApi operation — no server round trip, no compat surface, and
  no client-supplied or server-supplied unit content.

## Impact

- **Godot client** — a new `scripts/units/unit_definition.gd` (the typed model, fail-closed
  parsing) and a new `scripts/units/unit_catalog.gd` (registry-backed lookup), a new
  `tests/test_unit_definitions.gd`, scope-test allow-list entries, and the new evidence
  under `apps/client-godot/evidence/unit-definitions/`.
- **Compatibility API v0** — **unmodified.** A unit definition is committed read-only
  content served by the registry the client already loads; the compat suite must stay
  green unchanged.
- **Legacy** — unchanged and read only: `command.py`, `engine.py`, `constants.py`,
  `sessions.py`, `config/`, `villages/`, `tests/saves/`, and every committed fixture.
- **Content package** — unchanged and read only: `packages/game-content/**` including
  `normalized/units.json`, `schemas/unit.schema.json`, and `manifest.json`; the manifest
  digests remain the verification gate.
- **Verification** — `verify-boot.ps1` gains the hermetic unit-definitions suite; the
  guard baseline, the hash manifest, the content validator, and both batteries must stay
  green with no new packages and no non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project
  Status ledger, recording the commands actually executed, the parsed field inventory, the
  static/instance boundary, and the claim limits.