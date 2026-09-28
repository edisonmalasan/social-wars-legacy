# Spec Delta

## Purpose

Give the Godot client a bounded Settings service: a `Settings` autoload that owns the client's user preferences as explicit committed boolean state with fail-closed setters, change-only notifications, and explicit `ConfigFile` persistence — while explicitly disclaiming any legacy-parity settings behavior (no legacy user-settings behavior exists to capture; that binding belongs to later work, where evidence will be captured first).

## ADDED Requirements

### Requirement: Settings preference state
The client SHALL provide a `Settings` autoload (`scripts/settings.gd`) that owns exactly two committed boolean preferences — `music_enabled` and `sfx_enabled`, both `true` at startup — through typed accessors: `set_music_enabled(enabled)` and `set_sfx_enabled(enabled)` SHALL return an explicit `{ok, error}` result and SHALL fail closed with `setting_unchanged` (leaving committed state untouched and notifying nobody) when the request equals the committed value, and SHALL otherwise commit exactly the requested value and emit exactly one `setting_changed(key, value)` notification carrying the preference key and its new value; the getters SHALL reflect only committed state; creation SHALL notify nobody; and the service SHALL NOT read wall-clock or time services, load content, perform transport, reference legacy protocol or Flash-related primitives, or depend on any other script or autoload.

#### Scenario: Start with default preferences
- **WHEN** the autoload starts and nothing has been set or loaded
- **THEN** both getters report `true` and creation notifies nobody

#### Scenario: Commit a preference change
- **WHEN** a setter receives the opposite boolean
- **THEN** the request succeeds, the getter reflects the committed value, and exactly one notification is emitted with that key and the new value

#### Scenario: Reject an unchanged preference
- **WHEN** a setter receives the value already committed
- **THEN** the request fails with an explicit error naming the violated condition, committed state is unchanged, and no notification is emitted

### Requirement: Explicit fail-closed persistence
`load(path)` and `save(path)` (defaulting to `user://settings.cfg`) SHALL return explicit `{ok, error}` results and SHALL never run automatically — no startup load, no signal-triggered write, no boot wiring. A failed load SHALL leave committed state and notifications untouched, distinguishing an absent file (`storage_file_missing`), any other read failure such as corrupt contents (`storage_read_failed`, with the engine error code in the message detail), and a parsed file that violates the strict two-key schema — a missing known key, a non-`boolean` value, or an unknown key (`storage_invalid_contents`) — so that no field is ever dropped or half-applied; a successful load SHALL commit both keys and emit `setting_changed` only per key that actually changed; `save` SHALL fail closed with `storage_write_failed` when the file cannot be written and SHALL otherwise write the committed state and change nothing.

#### Scenario: Round trip through storage
- **WHEN** both preferences are set to `false`, saved to an explicit path, and loaded back after being reset to `true`
- **THEN** the save and both loads succeed and both getters report the saved `false` values

#### Scenario: Reject an absent file
- **WHEN** `load` targets a path that does not exist
- **THEN** the request fails with the file-missing error, committed state is unchanged, and no notification is emitted

#### Scenario: Reject unreadable contents
- **WHEN** the file exists but cannot be parsed
- **THEN** the request fails with the read-failed error, committed state is unchanged, and no notification is emitted

#### Scenario: Reject invalid contents
- **WHEN** the file parses but omits a known key, stores a non-`boolean` value, or carries an unknown key
- **THEN** each request fails with the invalid-contents error, committed state is unchanged, and no notification is emitted

#### Scenario: Apply a load change-only
- **WHEN** a successful load returns values differing from committed state in exactly one key
- **THEN** exactly one notification is emitted for the changed key and none for the unchanged key

#### Scenario: Report a storage write failure
- **WHEN** `save` targets a path whose directory does not exist
- **THEN** the request fails with the write-failed error and committed state is unchanged

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce the 47-file allow-list with exactly the six allow-listed autoloads and two scenes, while the 13 forbidden legacy-protocol and non-loopback transport tokens remain unchanged. The settings suite SHALL scan `settings.gd` for the clock, raw-persistence, content-loading, and other-dependency tokens (the sanctioned `ConfigFile` mechanism excluded from its scan and `ResourceLoader`, `AudioManager`, and `AudioServer` added).

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed (47 files), exactly the `GameApi`, `ContentRegistry`, `Session`, `GameClock`, `Settings`, and `AudioManager` autoloads are registered, exactly the two allow-listed scenes exist, and no forbidden token (13) appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the settings verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the settings delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the Settings autoload, which M5 items remain, and points to the committed evidence
