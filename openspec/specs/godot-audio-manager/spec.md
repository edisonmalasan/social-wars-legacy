## Purpose

Give the Godot client a bounded AudioManager service: an `AudioManager` autoload that owns the `Music` and `SFX` runtime audio buses as explicit committed output state, applies the Settings preferences as bus mute through a one-directional read-only binding, and fails closed on invalid requests — while explicitly disclaiming any playback or legacy-parity audio behavior (no sound content is played here; that binding belongs to later work).

## Requirements

### Requirement: AudioManager bus structure and output state
The client SHALL provide an `AudioManager` autoload (`scripts/audio_manager.gd`) that at startup ensures idempotently that `Music` and `SFX` exist as audio buses under `Master`, and owns exactly two committed boolean outputs — `music_enabled` and `sfx_enabled`, both `true` at startup — through typed accessors: `set_music_enabled(enabled)` and `set_sfx_enabled(enabled)` SHALL return an explicit `{ok, error}` result and SHALL fail closed with `music_setting_unchanged` / `sfx_setting_unchanged` (leaving committed state untouched and notifying nobody) when the request equals the committed value, and with `music_bus_missing` / `sfx_bus_missing` when the corresponding bus no longer exists; a successful request SHALL commit exactly the requested value, apply it to the bus's mute state — the bus is muted if and only if the committed value is `false`, and volume SHALL never be written (it stays at 0 dB) — and emit exactly one `music_enabled_changed(enabled)` / `sfx_enabled_changed(enabled)` notification carrying the new value; the getters SHALL reflect only committed state; creation SHALL notify nobody; and the service SHALL NOT read wall-clock or time services, load content, perform persistence or transport, reference legacy protocol or Flash-related primitives, or depend on any script other than its read-only Settings binding.

#### Scenario: Start with both buses ready
- **WHEN** the autoload starts
- **THEN** `Music` and `SFX` both exist under `Master`, both getters report `true`, both buses are unmuted with volume untouched at 0 dB, and creation notifies nobody

#### Scenario: Apply a music toggle
- **WHEN** `set_music_enabled` receives the opposite boolean
- **THEN** the request succeeds, the getter reflects the committed value, the `Music` bus is muted if and only if the committed value is `false`, and exactly one notification is emitted with the new value

#### Scenario: Reject an unchanged toggle
- **WHEN** a setter receives the value already committed
- **THEN** the request fails with the category-specific error naming the violated condition, committed state is unchanged, no bus state changes, and no notification is emitted

#### Scenario: Reject when the bus is missing
- **WHEN** a setter is called after its bus has been removed
- **THEN** the request fails with the category-specific bus-missing error, committed state is unchanged, and no notification is emitted

### Requirement: Settings binding
At `_ready` the AudioManager SHALL bind to the Settings autoload through a `/root/Settings` lookup: when present it SHALL connect to `setting_changed` and apply the current preferences (initial application included, change-only — an already-matching bus emits nothing), and SHALL follow every later `setting_changed` emission by applying the carried value; when absent it SHALL remain operational for direct control without error; the binding SHALL be one-directional — the Settings service SHALL NOT reference AudioManager or any audio API.

#### Scenario: Follow a Settings change
- **WHEN** the Settings autoload commits `music_enabled` to `false`
- **THEN** the AudioManager receives it, its own committed `music_enabled` becomes `false`, the `Music` bus is muted, and exactly one `music_enabled_changed` notification is emitted with `false`

#### Scenario: Bind to current preferences
- **WHEN** a Settings preference is already `false` and a manager instance starts
- **THEN** the instance binds, its committed state matches the preference, the corresponding bus matches, and exactly one notification is emitted for the applied value

#### Scenario: Start without Settings
- **WHEN** a manager instance starts while the Settings autoload is absent from `/root`
- **THEN** startup succeeds without error, both buses are ensured, and direct setter control still commits, applies, and notifies exactly as specified

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce the 47-file allow-list with exactly the six allow-listed autoloads and two scenes, while the 13 forbidden legacy-protocol and non-loopback transport tokens remain unchanged. The audio suite SHALL scan `audio_manager.gd` with the established clock, persistence, content-loading, transport, legacy, and other-autoload token list (the `Settings` binding being its sole allowed cross-service reference).

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed (47 files), exactly the `GameApi`, `ContentRegistry`, `Session`, `GameClock`, `Settings`, and `AudioManager` autoloads are registered, exactly the two allow-listed scenes exist, and no forbidden token (13) appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the audio-manager verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the audio-manager delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the AudioManager autoload, which M5 items remain, and points to the committed evidence
