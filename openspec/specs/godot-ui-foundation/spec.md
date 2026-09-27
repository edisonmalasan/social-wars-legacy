## Purpose

Give the Godot client a basic UI foundation: a reusable `CanvasLayer`-based component that owns named overlay slots with fail-closed management envelopes and change-only notifications — the layer the M6 HUD and dialogs will instance — while explicitly disclaiming any legacy-parity UI behavior (that binding belongs to later work, where evidence will be captured first).

## Requirements

### Requirement: UI foundation scaffold
The client SHALL provide a `CanvasLayer`-based UI foundation component (`scripts/ui_foundation.gd`) with explicit committed state: a fixed layer-index constant that the node's own layer index stays in agreement with, and at creation an empty slot registry; `register_slot(slot_name)` SHALL return an explicit `{ok, error}` result and SHALL fail closed with a named error that leaves the registry unchanged when the name is empty or already registered; a successful registration SHALL append the slot in registration order and own a full-rect `Control` container that starts visible and never intercepts pointer input (pass-through by default, so world and camera input stay unaffected); the getters SHALL reflect only committed state; and the component SHALL NOT read wall-clock or time services, perform transport or persistence, load content, reference legacy protocol or Flash-related primitives, or depend on any other script or autoload.

#### Scenario: Start with an empty registry
- **WHEN** the component is created and no slot has been registered
- **THEN** it reports an empty slot list, its layer index equals the committed layer-index constant, and creation notifies nobody

#### Scenario: Register a slot
- **WHEN** `register_slot` receives a fresh nonempty name
- **THEN** the request succeeds, the slot appears last in registration order with a full-rect visible container that passes pointer input through, and exactly one registration notification is emitted with that slot name

#### Scenario: Reject an invalid registration
- **WHEN** `register_slot` receives an empty name or a name that is already registered
- **THEN** each request fails with an explicit error naming the violated condition, the slot list is unchanged, and no notification is emitted

### Requirement: Slot visibility control
`set_slot_visible(slot_name, visible)` SHALL return an explicit `{ok, error}` result: it SHALL fail closed with a named error that leaves committed visibility unchanged when the slot is not registered and when the requested value equals the committed visibility, and SHALL otherwise commit exactly the requested visibility; a hidden slot SHALL remain registered with its container intact and out of view; and notifications SHALL be change-only — each committed change emits exactly one notification carrying the slot name and the new visibility, while every rejection emits nothing.

#### Scenario: Hide and show a registered slot
- **WHEN** a visible registered slot is hidden and later shown again
- **THEN** each request succeeds, the committed visibility flips exactly as requested each time, and each change emits exactly one notification with the new value

#### Scenario: Reject an unknown slot
- **WHEN** `set_slot_visible` receives a name that was never registered
- **THEN** the request fails with an explicit error naming the violated condition, the registry and every committed visibility are unchanged, and no notification is emitted

#### Scenario: Reject an unchanged value
- **WHEN** `set_slot_visible` requests the visibility a slot already has
- **THEN** the request fails with an explicit error naming the violated condition, the committed visibility is unchanged, and no notification is emitted

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce the 43-file allow-list with exactly the unchanged four autoloads and two scenes, while the `UiFoundation` token retires from the forbidden list and legacy-protocol and non-loopback transport tokens remain forbidden.

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed (43 files), exactly the `GameApi`, `ContentRegistry`, `Session`, and `GameClock` autoloads are registered, exactly the two allow-listed scenes exist, and no forbidden token (13) appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the UI-foundation verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the UI-foundation delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the UI foundation component, which M5 items remain, and points to the committed evidence
