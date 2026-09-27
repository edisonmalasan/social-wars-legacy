# Spec Delta

## Purpose

Give the Godot client a cross-cutting GameClock: one autoload whose game time is the boot response's server epoch committed once at boot and then advanced locally from processed frames, with an explicit fail-closed anchor/clear lifecycle, deterministic pause and manual-advance controls, and transition signals that later foundation and economy systems can observe without reaching into scene internals.

## ADDED Requirements

### Requirement: Clock scaffold
The client SHALL provide a `GameClock` autoload that owns game time as explicit state: no anchor SHALL exist at startup (getters then report an unanchored, running clock with a zero epoch); anchoring SHALL require a positive server timestamp, SHALL return an explicit `{ok, error}` result, SHALL fail closed with an explicit error that leaves the committed anchor and elapsed time unchanged when validation fails, and SHALL reject a second anchor until the clock is cleared; clearing SHALL return the scaffold to unanchored with zero elapsed time; the running state SHALL be independently controllable — pausing SHALL freeze reported time and resuming SHALL continue it; manual advancement SHALL return an explicit `{ok, error}` result, SHALL be permitted only while the clock is paused, SHALL advance exactly the requested positive millisecond count, and SHALL fail closed otherwise; getters SHALL reflect only committed state (unanchored reports a zero epoch); and the scaffold SHALL NOT read wall-clock or calendar time, SHALL NOT perform transport, persistence, or content loading itself, and SHALL NOT reference legacy protocol or Flash-related primitives.

#### Scenario: Start without an implicit anchor
- **WHEN** the project starts and no anchor has been committed
- **THEN** the clock reports unanchored and running with a zero epoch

#### Scenario: Anchor once to the response epoch
- **WHEN** a positive server timestamp is anchored to an unanchored clock
- **THEN** the request succeeds, the getters report the anchored clock with that exact timestamp, and observers receive one anchoring notification

#### Scenario: Reject an invalid anchor
- **WHEN** anchoring is requested with a zero or negative timestamp, or while the clock is already anchored
- **THEN** each request fails with an explicit error and the committed anchor and elapsed time are unchanged

#### Scenario: Pause freezes time and resume continues it
- **WHEN** a running clock is paused, frames are processed, and the clock is then resumed
- **THEN** the reported epoch and elapsed time stay unchanged while paused, observers receive exactly one pause-state notification per transition, and time advances again after resuming

#### Scenario: Advance exactly while paused, fail closed otherwise
- **WHEN** a paused clock is advanced by a positive millisecond count, or any clock is advanced by a zero or negative count or while running
- **THEN** the valid request succeeds with exactly the requested advance and one time-change notification, and every invalid request fails with an explicit error leaving the state unchanged

#### Scenario: Clear back to unanchored
- **WHEN** an anchored clock is cleared
- **THEN** the clock reports unanchored with a zero epoch and zero elapsed time, observers receive one clearing notification, and a repeated clear is a no-op that notifies nobody

### Requirement: Boot integration
The boot scene SHALL clear any previous anchor before it attempts a boot and SHALL anchor the clock to the successful bootstrap's session-list server timestamp immediately before activating the session, so the ready state implies an anchored clock whose epoch is that response timestamp advanced only by processed local frames; any failed boot attempt (unreachable endpoint, structured API error, or malformed response) SHALL leave the clock unanchored; and an anchor request that fails validation SHALL surface as an explicit boot error instead of reaching the ready state.

#### Scenario: Anchored clock at ready
- **WHEN** the boot completes successfully against the fake implementation
- **THEN** the clock is anchored to the fixture response's server timestamp, and the reported epoch is at or ahead of that timestamp and within a bounded post-anchor interval

#### Scenario: No anchor after a failed boot
- **WHEN** a boot attempt fails with an unreachable endpoint or a structured API error
- **THEN** the clock reports unanchored with a zero epoch — no stale or partial anchor exists

#### Scenario: Replace the previous anchor on a new attempt
- **WHEN** a successful boot is followed by a further boot attempt that fails
- **THEN** the new attempt clears the previously anchored clock on entry, observers receive one clearing notification, and no anchor remains after the failure

### Requirement: Change notifications
The clock SHALL notify observers whenever game time actually advances — once per processed frame that crosses a new whole millisecond and once per successful manual advance, each payload equal to the committed elapsed time and strictly increasing within the current base — and SHALL notify anchor, clear, and pause-state changes only on the corresponding transition, so anchoring or clearing (which rebase the elapsed time) are announced by their own transition notifications rather than time-change notifications, and every repeated no-op request is silent.

#### Scenario: Notify every advance
- **WHEN** time advances through processed frames or through a successful manual advance
- **THEN** observers receive one time-change notification per advance whose payload equals the reported elapsed time, and payloads never repeat or regress within the current base

#### Scenario: Notify transitions once
- **WHEN** the clock is anchored, cleared, paused, or resumed, including repeated no-op requests
- **THEN** each real transition notifies exactly once with the corresponding signal and every repeated no-op request notifies nobody

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce exactly the four allow-listed autoloads with the two new files allow-listed while camera, UI foundation, legacy-protocol, and non-loopback transport tokens remain forbidden.

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed, exactly the `GameApi`, `ContentRegistry`, `Session`, and `GameClock` autoloads are registered, and no forbidden token appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the game-clock-suite verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the GameClock delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the GameClock autoload scaffold, which M5 items remain, and points to the committed evidence
