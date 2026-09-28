# Spec Delta

## Purpose

Render a real legacy town in Godot without Flash: parse the town state from the client's existing bootstrap data, project legacy grid coordinates into one isometric coordinate space, render the legacy terrain and every saved town object with an authoritative HUD, selection, and bounded camera — and prove the M6 vertical-slice gate with committed evidence and explicit claim limits.

## ADDED Requirements

### Requirement: Typed town state loading

The client SHALL parse the bootstrap payload into a typed town state before any town view renders: every placement SHALL be preserved verbatim as its eight legacy positional fields (item, x, y, timestamp, orientation, store, attr, player) with integer grid coordinates, the resource and summary fields SHALL come from the same payload, and each placed legacy id SHALL be resolved against ContentRegistry (name, kind, footprint `width`/`height`, `img_name`, asset status). Parsing SHALL fail closed with an explicit `{ok, error}` result naming the missing or invalid field — never a partial town state, never fabricated or defaulted values — and content-resolution failures SHALL be recorded per placement (rendered later as a placeholder) rather than failing the whole save, since a legacy save may legitimately contain ids the content package does not. Presentation code SHALL receive only the typed state, never the raw transport payload.

#### Scenario: Parse the fresh-save bootstrap payload

- **WHEN** the town state is parsed from the committed fresh-save bootstrap fixture
- **THEN** all 40 placements are present verbatim with their integer coordinates, the 11 distinct placed ids resolve against ContentRegistry with their content footprints, and the resource and summary fields equal the fixture save's values

#### Scenario: Fail closed on malformed input

- **WHEN** the payload lacks the default map, or contains a non-integer coordinate or a placement that is not an eight-field array
- **THEN** parsing returns an explicit error naming the offending field and produces no town state

#### Scenario: Record unresolvable content without failing the save

- **WHEN** a placement names a legacy id absent from the content package
- **THEN** the placement is kept verbatim with an unresolved marker and recorded id, and the remaining placements still parse

### Requirement: Isometric projection

The client SHALL provide a bidirectional isometric projection between legacy grid cells and world screen pixels: grid→screen SHALL map a cell deterministically and SHALL derive a multi-cell footprint's screen bounds from its corner cells alone; screen→grid SHALL be the exact inverse inside the grid and SHALL report an explicit out-of-grid result (never a wrapped or silently clamped cell) for coordinates outside the world or with negative components; the two directions SHALL round-trip exactly for every cell of the 0..99 legacy extent, including footprint corners. The projection constants (tile width, tile height, world origin) SHALL be committed with a documented derivation procedure and evidence basis (legacy save coordinate extents, content footprints, converted sprite and thumbnail scales, the legacy client's static iso-engine identifiers), and SHALL be recorded as derived and provisional — the numeric constants embedded in the legacy SWF bytecode were not extracted, and pixel parity with the legacy client is not claimed.

#### Scenario: Round-trip every cell and footprint corner

- **WHEN** grid→screen→grid is applied across the full 0..99 extent, including each converted building's multi-cell footprint corners
- **THEN** every cell returns exactly itself

#### Scenario: Report out-of-grid explicitly

- **WHEN** screen→grid receives a point outside the projected world or a negative component
- **THEN** it returns an explicit out-of-grid result and never a valid but wrong cell

#### Scenario: Stable, documented constants

- **WHEN** the projection is used by terrain, objects, selection, and camera bounds
- **THEN** all four consume the same committed constants, and the repository documents how those constants were derived and that they are provisional

### Requirement: Terrain rendering

The town view SHALL render the legacy town terrain image as the ground layer beneath all objects, resolved through ContentRegistry asset resolution over the legacy image corpus; the terrain layer SHALL be placed by the projection's world rectangle so ground, objects, selection, and camera share one coordinate space; and an unresolvable terrain asset SHALL surface an explicit town error state naming it — never a silent blank ground beneath a claimed render.

#### Scenario: Terrain beneath the town

- **WHEN** a town view builds from valid town state with the legacy terrain asset available
- **THEN** a ground layer carrying the legacy island image exists beneath the object layer at the projection's world rectangle

#### Scenario: Fail visibly without terrain

- **WHEN** the terrain asset cannot be resolved
- **THEN** the view enters an explicit error state naming the terrain failure and does not claim a rendered town

### Requirement: Town object rendering

Every placement SHALL render as a town object at its projected position with its footprint taken from content `width`/`height` — never from texture or sprite dimensions — and with its visual chosen by a fixed hierarchy: an authentic converted package sprite when the item's asset status is `converted`, otherwise the preserved legacy thumbnail for its `img_name` scaled to its footprint with its white background keyed to transparency, otherwise an explicit footprint marker. A placement whose legacy id is absent from content SHALL render a labeled placeholder and be recorded — never skipped silently, never a crash. Each rendered object SHALL carry committed metadata (legacy id, name, grid position, footprint, chosen visual source) reachable for tests, HUD, and selection.

#### Scenario: Render the player's real save

- **WHEN** a town view builds from the fresh-save town state
- **THEN** 40 objects exist at their saved cells with content footprints, thumbnails render for the items that have preserved thumbnails, and the thumbnail-less items render footprint markers

#### Scenario: Render authentic converted assets in town

- **WHEN** a town view builds from the slice village state (`villages/Scarlet.json`), whose map contains House I and Wild Elephant placements
- **THEN** those placements render as authentic converted package sprites while the remaining objects render by the thumbnail/marker hierarchy

#### Scenario: Placeholder for an unknown legacy id

- **WHEN** a placement names a legacy id the content package does not contain
- **THEN** a labeled placeholder renders at its saved cell with the id recorded, the rest of the town is intact, and no error aborts the view

### Requirement: Isometric depth sorting

Town objects SHALL be drawn in non-decreasing isometric depth order derived from their grid position, so an object nearer the camera occludes objects farther away; objects sharing a depth key SHALL have a deterministic documented tie-break whose relative order is identical across runs and platforms.

#### Scenario: Near objects draw after far objects

- **WHEN** two objects are placed so their projected sprites overlap
- **THEN** the object whose cells are nearer the camera is drawn later (on top)

#### Scenario: Deterministic ties

- **WHEN** several objects share one depth key
- **THEN** their relative draw order is identical across repeated builds

### Requirement: Authoritative resource HUD

The town HUD SHALL display the resource values (coins, wood, steel, oil, cash, energy, mana) and summary fields (name, level, xp) verbatim from the loaded town state, built on the UI foundation slot registry; it SHALL NOT compute deltas, rates, timers, or any value absent from the state; a missing or invalid value SHALL render an explicit indicator naming that field — never a guessed, zeroed, or stale number — and the displayed strings SHALL equal the state values exactly as headless assertions observe them.

#### Scenario: Display exactly what the state carries

- **WHEN** the HUD builds from the fresh-save town state
- **THEN** every displayed value string equals the corresponding town-state value, and nothing is derived

#### Scenario: Name a missing value instead of guessing

- **WHEN** the state lacks one of the displayed fields
- **THEN** the HUD shows an explicit indicator naming the field and no fabricated number appears

### Requirement: Object selection

The town view SHALL support selection from pointer input: a left press SHALL be converted through the inverse projection to a cell and SHALL commit the topmost object whose footprint covers that cell (depth order breaking overlaps), a press on empty or out-of-grid space SHALL clear the selection, and a non-finite or otherwise invalid press SHALL change nothing; the committed selection SHALL be visible as a highlight over the selected footprint, exposed through a public getter for tests, and selection SHALL NOT mutate town state — placement, movement, and disposal remain out of scope until the building-system phase.

#### Scenario: Select by clicking a footprint

- **WHEN** a left press lands on a cell covered by a town object
- **THEN** that object becomes the committed selection, the highlight covers its footprint, and the public getter reports it

#### Scenario: Topmost wins and empty space clears

- **WHEN** footprints overlap at the pressed cell, and then a press lands on empty ground
- **THEN** the depth-topmost object is selected, and the subsequent press clears the selection with no other state change

#### Scenario: Selection never mutates the save

- **WHEN** selections are made and cleared repeatedly
- **THEN** the underlying town state (placements, resources) is byte-for-byte unchanged

### Requirement: Camera bounds integration

The town view SHALL instance the camera-controls component and set its world bounds from the projection's world rectangle, so every committed pan position stays inside the town while the existing zoom levels and pointer controls operate unchanged; the bounds SHALL derive from the same committed projection constants as terrain, objects, and selection — one coordinate space, no second geometry.

#### Scenario: Panning stops at the town edge

- **WHEN** a drag or `pan_by` request would carry the camera position outside the town bounds
- **THEN** the request fails closed per the camera's bounds contract, the committed position stays within the bounds, and pan/zoom remain usable inside them

#### Scenario: One geometry for everything

- **WHEN** terrain, object footprints, selection hits, and camera bounds are computed
- **THEN** all four derive from the same committed projection constants

### Requirement: Boot to town launch flow

The project SHALL provide the town scene as the launch target: in a windowed run it SHALL receive the already-validated typed state from the ready boot scene and render terrain, objects, HUD, selection, and camera as one view, using the state handed off — no second bootstrap request, and no raw payload reaching presentation code; a handoff or town-build failure SHALL surface an explicit error naming the failure, never a blank window or a partially rendered town; headless runs SHALL be unaffected and SHALL NOT enter the town scene.

#### Scenario: A player launches into the town

- **WHEN** a windowed run completes bootstrap successfully
- **THEN** the boot view is replaced by the town view rendering that save's terrain, objects, and HUD, exactly one bootstrap request was made, and the committed evidence capture records the view

#### Scenario: Headless boot behavior is unchanged

- **WHEN** the headless boot verification runs (success and unreachable-endpoint cases)
- **THEN** its markers, displayed summary, error states, and exit codes are exactly as before — the town scene is never instantiated

#### Scenario: Explicit failure instead of a blank window

- **WHEN** the handed state cannot build a valid town state at transition time
- **THEN** an explicit error naming the failure replaces the view and no partial town is shown

### Requirement: Town slice verification scene

The project SHALL provide a town-slice verification scene that renders the committed legacy village `villages/Scarlet.json` — an existing preserved legacy save whose map contains House I and Wild Elephant placements — through the same town components, headlessly and windowed without any server, GameApi mutation, or Flash runtime; it SHALL exist to prove the slice properties the player's fresh save cannot (authentic converted building and unit sprites in town, thumbnail and marker rendering, depth order, that save's HUD values, selection, and bounds), and it SHALL record its input file and digest in the evidence report while leaving every legacy file byte-identical.

#### Scenario: Prove the converted building and unit in town

- **WHEN** the slice scene builds from the legacy village save
- **THEN** the House I and Wild Elephant placements render as authentic converted package sprites at their legacy-saved cells, the remaining objects render by the visual hierarchy, and headless assertions observe object counts, depth order, HUD values from that save, selection, and bounds

#### Scenario: Preserve the input

- **WHEN** the slice scene has rendered (headless or windowed)
- **THEN** `villages/Scarlet.json` and every other legacy input are byte-identical (guard hashes match)

### Requirement: Town evidence and claim limits

The change SHALL commit windowed captures of both town views (the player's fresh save and the slice village) together with a structural report recording: the inputs and their digests, the committed projection constants and their derivation status, object counts by chosen visual source, the observed HUD values, and selection/camera state; the report SHALL state explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; no pixel-parity oracle against the legacy client exists; projection constants are derived and provisional; thumbnail presentation is provisional pending further conversions; authentic unit rendering is proven via the slice scene because the live fresh save contains no unit placements — and prior committed evidence (first-render, boot) SHALL remain byte-identical.

#### Scenario: Evidence is committed and self-describing

- **WHEN** verification completes
- **THEN** the town captures and report exist, the report names its inputs, constants, counts, and every non-claim above, and the pre-existing evidence bytes are unchanged

#### Scenario: No legacy or fixture bytes change

- **WHEN** the full verification battery has run
- **THEN** guard hashes over legacy sources, saves, fixtures, conversion packages, registry manifests, the content package, and the legacy baseline entries for the consumed assets are identical before and after

### Requirement: Containment and scope

The change SHALL keep every prior verification green (`verify.ps1`, `verify-boot.ps1`, Compatibility API guards, first-render comparator and self-test) and every guarded byte identical; the updated project-scope test SHALL enforce an allow-list of exactly 66 project files — the pre-existing 47 plus the town scene, slice scene, eight town scripts, six town suites, and three evidence files — with exactly the unchanged six autoloads (GameApi, ContentRegistry, Session, GameClock, Settings, AudioManager) and exactly four allow-listed scenes (boot, first_render, town, town_slice), while legacy-protocol, Flash, and non-loopback transport tokens remain forbidden; no new Python package, no network beyond loopback, and no server, Compatibility API, fixture, or content-package change is in scope.

#### Scenario: Scope enforces the new boundary

- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed (66 files), exactly the six allow-listed autoloads are registered, exactly the four allow-listed scenes exist, and no forbidden token appears in any project script or scene

#### Scenario: Keep prior verifications green

- **WHEN** the full verification battery runs in the final state
- **THEN** both verification commands exit 0, Compatibility API guard digests match before and after, and the committed first-render and boot evidence remain byte-identical

### Requirement: Documented commands and assessment record

`AGENTS.md` and the client README SHALL document the exact commands actually executed for the town verification and both verification batteries, with their purposes and scope limitations (including the slice-scene input provenance and the claim limits above), and the roadmap Project Status ledger SHALL record the M6 delivery with pointers to the committed town evidence and the gaps that remain (projection provenance, authentic HUD/selection visuals, unit presence in the live save, and the systems deferred to later phases).

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone

- **WHEN** this change concludes
- **THEN** the ledger states that M6's vertical-slice gate is delivered, points to the committed town evidence, and names the remaining gaps
