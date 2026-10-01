## Purpose


Expose the placement of a unit row as a typed, read-only projection — cell, orientation, footprint,
elevation, and `velocity` reported **strictly as committed content** — together with the
movement-command inventory (including that `move` is type-agnostic and already delivered, and that
`fast_forward` makes the row instant client-writable) and the explicit refusals of travel time,
paths, terrain, occupancy, bounds, readiness, and interpolation.

## Requirements

### Requirement: A unit row's placement is projected, never derived

The client SHALL expose a unit row's placement as a typed, read-only projection carrying its
**committed** cell coordinates, its orientation, its committed footprint (`width` and `height`),
its committed `elevation`, and its committed `velocity`, each reported **verbatim**. The projection
SHALL compute **no** value from another: no coordinate from a velocity, no offset from a footprint,
no elevation-adjusted position, and no interpolation between two instants. A row whose committed
coordinates are absent or malformed SHALL be reported as unresolvable with its recorded state
intact, never defaulted to the origin.

#### Scenario: Placement is reported verbatim

- **WHEN** a unit row's placement is projected
- **THEN** its committed cell, orientation, footprint, elevation, and velocity are each reported exactly as committed, with no scaling, rounding, or defaulting

#### Scenario: No value is derived from another

- **WHEN** the projection is inspected
- **THEN** no coordinate is computed from a velocity, no offset from a footprint, no position from an elevation, and no intermediate position between two instants

#### Scenario: An unresolvable row is reported, not defaulted

- **WHEN** a row's committed coordinates are absent or malformed
- **THEN** the placement is reported as unresolvable with its recorded state intact, and is never defaulted to the origin

### Requirement: Committed movement fields are content, not rules

The client SHALL report the committed `velocity`, `width`, `height`, and `elevation` as **content
only**, and SHALL derive **no** velocity-based travel time, path, terrain or elevation interaction,
occupancy rule, bounds rule, readiness, or interpolation from them. The recorded fact SHALL state
that **no legacy branch reads any of these fields**, report the committed distributions for
reference, and name the fields in this project that share the same zero-consumer property.

#### Scenario: The committed fields are reported, never used

- **WHEN** a unit definition's velocity and footprint fields are inspected
- **THEN** their values may be reported as content, and no travel time, path, terrain interaction, occupancy, bounds, readiness, or interpolation is computed from any of them

#### Scenario: The zero-consumer fact is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that no committed branch reads these fields, report the committed distributions, and name the earlier fields in this project with the same zero-consumer property

#### Scenario: The tile-geometry gap stays a gap

- **WHEN** terrain or elevation interaction is considered
- **THEN** none is implemented, and the recorded absence of the legacy tile geometry is stated rather than filled with an assumed geometry

### Requirement: The movement-command inventory classifies what each command does and does not check

The client SHALL record the inventory of the legacy commands that write a row's placement, naming
`move`, `orient`, and `pop_unit`, and the adjacent time command `fast_forward`, and for each SHALL
record what it checks and what it does **not**. The recorded facts SHALL include that **`move` is
type-agnostic and checks neither type, occupancy, bounds, terrain, nor speed**, that its frame and
string arguments are read but unused, that `move` is **already delivered** by an earlier
capability, that `orient` is a plain orientation write, and that `pop_unit` is the only other
command writing coordinates and overwrites the row's item id. The inventory SHALL record that **no
unit-specific movement command exists**, and this capability SHALL implement **none**.

#### Scenario: Each command is classified

- **WHEN** the inventory is inspected
- **THEN** each recorded command carries an explicit statement of what it checks and what it does not, and the count of coordinate-writing commands matches the committed source

#### Scenario: The type-agnostic move is recorded as already delivered

- **WHEN** the inventory describes the move command
- **THEN** it records that the command is type-agnostic and already delivered, so this capability adds no new server behaviour and does not reimplement it

#### Scenario: No unit-specific movement command is invented

- **WHEN** this change's diff is inspected for movement commands
- **THEN** no new command, route, or request is introduced, and the inventory records that none exists in the legacy source

### Requirement: The row instant is client-writable, and no readiness is derived from it

The client SHALL record that a legacy command shifts every row's recorded instant **and** its
queue start instant **backwards by a client-supplied number of seconds**, and SHALL therefore
record that the row instant is **client-writable**. The client SHALL derive **no** readiness,
elapsed time, or completion from that instant, consistent with the earlier capability that refuses
any elapsed-time evaluation, and SHALL treat the recorded instant as an opaque recorded value.

#### Scenario: The client-writable instant is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that a client-supplied time shift rewrites every row's instant and queue start instant, and that no readiness, elapsed time, or completion is derived from the result

#### Scenario: The instant is opaque, not a clock

- **WHEN** a row's instant is projected
- **THEN** it is reported as an opaque recorded value with no elapsed, remaining, or readiness computation

### Requirement: Movement is content, not a server operation

Unit movement SHALL be read from the committed content package and the committed row already in
hand, and SHALL NOT require or expose a server operation: no compatibility API route SHALL be
added, no client intent SHALL be sent to move a unit, and no persistence behaviour SHALL change. The
compatibility test suite SHALL remain green **unchanged**.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No move intent is sent

- **WHEN** the client has nothing to move
- **THEN** it issues no request, and no intent exists to authorise

### Requirement: No executed-legacy movement fixture is claimed

The change SHALL capture **no** executed-legacy movement fixture, and the non-claims SHALL state
that this is because there is **no unit-specific movement behaviour to capture** rather than only
because the committed corpus lacks a unit row, and that the move command which does exist is
already delivered with its own executed-legacy fixture. The committed corpus SHALL remain
byte-identical, and no unit row SHALL be written to any save, corpus, or fixture to manufacture one.

#### Scenario: No fixture is captured, and the reason is stated

- **WHEN** this capability's evidence and claim limits are read
- **THEN** they state that no movement fixture was captured because there is no unit-specific movement behaviour to capture, distinguish that from the corpus's missing unit row, and note that the existing move command is already delivered with its own fixture

#### Scenario: No unit row is fabricated

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a unit row, and the committed corpus and the delivered fixture directories stay byte-identical

### Requirement: Unit-movement evidence and claim limits

The change SHALL commit a deterministic `unit-movement-report-v1` report recording the placement
fields verbatim, the committed velocity and footprint distributions with their zero-consumer
statements, the movement-command inventory with each command's checks and non-checks, the
client-writable instant recording, the corpus measurement, the tile-geometry gap, the
established-versus-derived split, and the explicit non-claims, byte-identical across reruns. The
non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no velocity-based
travel time, path, terrain or elevation interaction, occupancy, bounds, readiness, or
interpolation is implemented**; **the committed movement fields are read by no legacy branch** and
are reported as content only; **no unit-specific movement command exists and none was invented**;
**no unit is placed or moved**, and the corpus holds no unit row; **no executed-legacy fixture was
**no animation is implemented, and that refusal belongs to the `godot-unit-animations`
capability**, which records the five committed asset labels and refuses every playback rule (this line's own `animate_move` entry in its absent-helper list is one of them);
timeline linkage only, never playback correctness; **no pixel parity is claimed** and the tile
geometry remains a recorded gap; and **no windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-movement/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: Animation and parity are not claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no animation or playback is implemented, that the converted unit package establishes linkage only, and that no pixel parity or windowed capture is claimed

#### Scenario: The animation refusal has one owner
- **WHEN** this requirement's non-claim that no animation is implemented is read
- **THEN** it names `godot-unit-animations` as the single owner of the animation refusals, so the movement capability records that no animation exists here without re-deriving why, and the two capabilities cannot disagree about whether a unit moves with an animation
