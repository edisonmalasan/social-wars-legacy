# Spec Delta

## Purpose

Give the Godot client a typed, fail-closed, read-only model of the committed unit
definitions — preserving every legacy ID and drawing the static-definition /
player-instance boundary explicitly — with no endpoint, no save shape, and no gameplay
semantics.

## ADDED Requirements

### Requirement: Static unit definitions

The client SHALL expose each committed unit definition as a typed, read-only
`UnitDefinition` resolved through `ContentRegistry` from the manifest-verified `units`
domain, enumerating that domain's legacy IDs through the registry's own public enumeration
accessor rather than re-reading the committed file, and SHALL preserve the definition's
legacy ID **verbatim as a string**. A
definition SHALL carry no player state: it SHALL have no field that could hold a placement
key, coordinates, an owner, current health, a garrison, or any other per-player value, and
the model SHALL be immutable. Resolution SHALL go only through the content registry, so
the manifest's byte-count and digest verification and the registry's duplicate-legacy-ID
rejection remain the single gate; a registry that has not loaded, or that does not carry a
`units` domain, SHALL fail closed rather than yield an empty catalog.

#### Scenario: A definition resolves by its legacy ID

- **WHEN** a caller requests a unit definition by legacy ID
- **THEN** the definition is returned from the registry's `units` domain, carries that legacy ID verbatim as a string, and is the committed row

#### Scenario: The legacy ID is preserved verbatim and is unique

- **WHEN** every committed unit definition is inspected
- **THEN** each carries a distinct string legacy ID spanning the committed range, and a lookup by any of them returns its own definition rather than another

#### Scenario: A lookup with the wrong form fails closed

- **WHEN** a lookup supplies a legacy ID in a form other than the committed string
- **THEN** the lookup fails closed and returns no definition, and no coercion to a number is attempted

#### Scenario: An unloaded or absent registry fails closed

- **WHEN** the content registry has not loaded, or carries no `units` domain
- **THEN** the catalog reports the failure and returns no definitions, and never an empty catalog presented as a loaded one

#### Scenario: A definition cannot be mutated into an instance

- **WHEN** a definition is inspected for fields that could carry player state
- **THEN** it has none, and the static-definition surface is read-only

### Requirement: Typed definition fields with no gameplay semantics

The `UnitDefinition` SHALL expose the committed fields in named groups — identity and
presentation, footprint and placement, statistics, economy, and training and upgrade —
parsing each **verbatim**. The statistical fields SHALL carry **no gameplay semantics**:
nothing in this capability SHALL compute damage, defence outcomes, speed, lifetimes, or
attack timing from them, and no helper on the model or the catalog SHALL derive behaviour
from a parsed statistic. Any committed field outside those groups SHALL remain reachable
through one documented raw-entry accessor rather than being silently dropped.

#### Scenario: Every parsed field is the committed value

- **WHEN** a definition is compared against its committed row
- **THEN** each parsed field equals the committed value exactly, with no scaling, rounding, or defaulting

#### Scenario: Statistics carry no behaviour

- **WHEN** the model or catalog exposes a statistical field
- **THEN** the value is the committed number and no helper computes damage, defence, speed, lifetime, or timing from it, and the capability's own documentation states that none is implied

#### Scenario: Fields outside the parsed groups remain reachable

- **WHEN** a caller needs a committed field the typed model does not parse
- **THEN** the documented raw-entry accessor returns it from the committed row, so nothing is silently dropped and a new content field needs no model change

### Requirement: Fail-closed parsing

Parsing a definition SHALL fail closed on any malformed field, returning a failure that
names the offending definition and field and producing **no** definition; nothing SHALL be
guessed, defaulted, or coerced into a meaningful value. The two committed object bags SHALL be
parsed from the committed object form the content package's own coercion rule produces, and
the cost vocabulary SHALL match the mapping the delivered endpoints already implement; an
unknown cost key or a non-integer amount SHALL fail closed. A field absent from the
committed row SHALL be recorded as **absent**, never as zero, so an absent field is
distinguishable from a committed zero.

#### Scenario: A malformed field produces no definition

- **WHEN** a committed field of a definition is malformed
- **THEN** parsing fails closed, the failure names the definition and the field, and no definition is produced

#### Scenario: The cost vocabulary matches the delivered endpoints

- **WHEN** a definition's committed cost bag is parsed
- **THEN** its keys map onto the same resource names the delivered purchase, shop, expansion, and level surfaces already implement, so the definition cannot disagree with what the unit would actually cost

#### Scenario: An absent field is absent, not zero

- **WHEN** a definition lacks a field the schema permits to be absent
- **THEN** the model records that field as absent, and never substitutes zero for it

### Requirement: Static definitions are content, not a server operation

Unit definitions SHALL be read from the committed content package through the content
registry and SHALL NOT require or expose a server operation: no compatibility API route
SHALL be added for them, no client intent SHALL be sent to obtain one, and no
server-supplied or client-supplied unit content SHALL be introduced. This capability SHALL
introduce no player-owned unit instance type, no save shape, no instance parsing, and no
garrison or production-queue state.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No player-owned unit state is introduced

- **WHEN** this change's diff is inspected for player state
- **THEN** no unit instance type, save shape, instance parsing, garrison state, or production-queue state was added

#### Scenario: Enumeration crosses the same verification gate

- **WHEN** the catalog enumerates the domain's legacy IDs
- **THEN** it does so through the content registry's public enumeration accessor over the
  index built during the verified load, cross-checks the enumerated count against the
  registry's reported count, and fails closed on disagreement, and no committed content file
  is read behind the registry's back

#### Scenario: Definitions are read, never fetched

- **WHEN** the client needs a unit definition
- **THEN** it is read from the already-loaded content registry and no request is issued

### Requirement: Committed asset linkage only

A definition names its committed sprite reference, and the model MAY report **whether** that
reference resolves through the committed asset-ID registry together with its recorded
status. This capability SHALL establish no rendering correctness, no animation correctness,
no visual fidelity, and no gameplay semantics for any unit, and SHALL NOT claim that a unit
can be drawn, animated, or played.

#### Scenario: Sprite linkage is reported, not rendered

- **WHEN** a definition is inspected for its sprite reference
- **THEN** the model may report whether the committed reference resolves and its recorded status, and claims nothing about rendering, animation, or visual fidelity

#### Scenario: No visual or behavioural claim is made

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no unit is rendered, animated, or played by this change, and name the animation, movement, and behaviour deliver lines as undelivered

### Requirement: Unit-definition evidence and claim limits

The change SHALL commit a deterministic `unit-definitions-report-v1` report recording the
committed counts, the legacy-ID range and distinctness, the content fingerprint and manifest
digest, the per-group parsed-field inventory, the coverage of every field that is absent on
part of the set, the raw-entry escape hatch, the asset-linkage statuses, and the
static/instance boundary, together with explicit non-claims, byte-identical across reruns.
The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no unit is
rendered, animated, or played**; **no unit instance, queue, production, collection,
movement, animation, or behaviour is implemented** — each is a separate later deliver line;
no gameplay semantics are attached to any parsed statistic; the definitions are the
committed normalized rows with no tuning, balancing, or interpolation; asset linkage is
reported and nothing more; and the committed corpus's lack of unit placements means no
instance behaviour is evidenced here. The change SHALL NOT claim a windowed capture, because
it changes nothing visual and a capture would assert nothing.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-definitions/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture is claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no windowed capture is claimed because the change alters nothing visual

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing
locked dependencies and no new packages; the content package — including
`normalized/units.json`, `schemas/unit.schema.json`, and `manifest.json` — SHALL remain
byte-identical, as SHALL legacy sources, configs, saves, villages, committed fixtures,
conversion packages, registry manifests, and every delivered slice's evidence; and both
verification batteries and the content validator SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** the suite, both batteries, the guard baseline, the hash manifest, and the content validator have all run
- **THEN** the manifest digests still verify, the guard hashes are identical before and after, and the diff touches no content package or legacy byte