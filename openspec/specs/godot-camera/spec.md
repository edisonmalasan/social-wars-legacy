## Purpose

Give the Godot client camera controls: a reusable `Camera2D`-based component with explicit committed view state (world position plus discrete zoom levels over a fixed factor table), fail-closed pan/zoom control envelopes, change-only signals, and a public pointer-input handler — the piece the M6 town scene will instance — while explicitly disclaiming any legacy-parity camera behavior (that binding belongs to the town slice, where evidence will be captured first).

## Requirements

### Requirement: Camera controls scaffold
The client SHALL provide a `Camera2D`-based camera-controls component (`scripts/camera_controls.gd`) with explicit committed view state: at creation the view SHALL sit at the default world position with zoom level 0 and factor 1.0; zoom SHALL be discrete levels 0 through 2 over the fixed factor table `1.0`, `2.0`, `4.0`, with the component's committed factor and the node's own zoom always in agreement; `zoom_in()` and `zoom_out()` SHALL return explicit `{ok, error}` results and SHALL fail closed with a named error that leaves position, level, factor, and node zoom unchanged when already at the maximum or minimum level; `pan_by(world_delta)` SHALL return an explicit `{ok, error}` result, SHALL reject the zero vector and any non-finite component with a named error that leaves the position unchanged, and SHALL otherwise commit exactly the requested world delta; getters SHALL reflect only committed state; and the component SHALL NOT read wall-clock or time services, perform transport or persistence, load content, reference legacy protocol or Flash-related primitives, or depend on any other script or autoload.

#### Scenario: Start at the default view
- **WHEN** the component is created and no control has been applied
- **THEN** the view reports the default world position with zoom level 0, factor 1.0, and the node's zoom exactly `(1, 1)`

#### Scenario: Zoom one level at a time, fail closed at the bounds
- **WHEN** zoom-in is requested until the maximum level and zoom-out is then requested past both extremes
- **THEN** each valid request advances exactly one level with the table factor reflected in both the committed factor and the node's zoom, and each out-of-bounds request fails with an explicit error leaving level, factor, node zoom, and position unchanged

#### Scenario: Pan by a world delta
- **WHEN** `pan_by` receives a finite nonzero world delta
- **THEN** the request succeeds and the committed position moves by exactly the requested delta, verified cumulatively across consecutive pans

#### Scenario: Reject an invalid pan
- **WHEN** `pan_by` receives the zero vector, a NaN component, or an infinite component
- **THEN** each request fails with an explicit error and the committed position is unchanged

#### Scenario: Notify only on successful change
- **WHEN** a zoom or pan request succeeds, or a request is rejected or motion carries no movement
- **THEN** each success emits exactly one corresponding notification whose payload is the committed change (the new zoom level, or the requested world delta), and every rejection or no-op emits nothing

### Requirement: Pointer controls
The component SHALL map pointer input through a public `handle_input(event) -> bool`: a wheel-up press SHALL zoom in one level and a wheel-down press SHALL zoom out one level, each event consumed regardless of outcome and silent when fail-closed at a level bound; a left-button press SHALL begin a drag and be consumed; motion while dragging SHALL be consumed and SHALL pan so the content under the cursor follows the cursor, converting the screen-space movement by the inverse of the committed zoom factor; a left-button release SHALL end the drag and be consumed; and every other event SHALL be unconsumed with no state change; the node's own unhandled-input entry point SHALL delegate to that public handler so an instanced component responds to input from the scene tree.

#### Scenario: Wheel zooms one level per notch
- **WHEN** a wheel-up event and then a wheel-down event are handled at the default view
- **THEN** each event is consumed, the level moves 0 → 1 → 0 with factor and node zoom kept in sync, and each change emits one zoom notification

#### Scenario: Wheel at a level bound is consumed and silent
- **WHEN** the view is at the maximum level and a wheel-up event is handled, and at the minimum level with a wheel-down event
- **THEN** each event is consumed, level, factor, node zoom, and position are unchanged, and no notification is emitted

#### Scenario: A drag pans the content under the cursor
- **WHEN** a left press, a motion carrying a rightward drag delta, and a left release are handled
- **THEN** each is consumed; at zoom level 0 a 100 px drag commits a −100 world-px pan and at level 1 the same drag commits −50 world px; the drag ends at the release; and subsequent motion is unconsumed and does not pan

#### Scenario: Unrelated events pass through
- **WHEN** a right-button press, motion while no drag is active, or a key event is handled
- **THEN** each returns `false` and the view state is unchanged

#### Scenario: The node delegates input to the public handler
- **WHEN** the component's own unhandled-input entry point receives a wheel-up event while instanced in the scene tree
- **THEN** the zoom level advances, observed through behavior, proving the delegation rather than a test-only call path

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce the 41-file allow-list with exactly the unchanged four autoloads and two scenes, while the camera tokens retire from the forbidden list and UI foundation, legacy-protocol, and non-loopback transport tokens remain forbidden.

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed (41 files), exactly the `GameApi`, `ContentRegistry`, `Session`, and `GameClock` autoloads are registered, exactly the two allow-listed scenes exist, and no forbidden token (14) appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the camera-controls verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the camera-controls delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the camera controls component, which M5 items remain, and points to the committed evidence
