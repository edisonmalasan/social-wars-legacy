## Purpose

Give the Godot client a cross-cutting Session scaffold: one autoload that holds which save is currently active and its typed summary, with an explicit fail-closed lifecycle that the boot flow populates and later foundation systems can observe without reaching into scene internals.

## Requirements

### Requirement: Session scaffold
The client SHALL provide a `Session` autoload that holds the active session as explicit state: no session SHALL exist at startup; activation SHALL require a non-empty user identifier together with a typed player summary that names the same user identifier, SHALL return an explicit `{ok, error}` result, and SHALL fail closed with an explicit error that leaves the previously committed state unchanged when validation fails; clearing SHALL return the scaffold to inactive; getters SHALL reflect only the committed state (inactive reports an empty user identifier and a null summary); and each successful activation SHALL notify observers once, while clearing SHALL notify only when an active session becomes inactive. The scaffold SHALL NOT perform transport, persistence, or content loading itself and SHALL NOT reference legacy protocol or Flash-related primitives.

#### Scenario: Start without an implicit session
- **WHEN** the project starts and no activation has occurred
- **THEN** the scaffold reports inactive with an empty user identifier and a null summary

#### Scenario: Activate a session explicitly
- **WHEN** activation is requested with a non-empty user identifier and a typed summary naming that same identifier
- **THEN** the request succeeds, the getters report the committed user identifier and summary, and observers receive one activation notification

#### Scenario: Reject an invalid activation
- **WHEN** activation is requested with an empty user identifier, a null summary, or a summary naming a different identifier
- **THEN** the request fails with an explicit error and the previously committed state (including an already-active session) is unchanged

#### Scenario: Clear back to inactive
- **WHEN** an active session is cleared
- **THEN** the scaffold reports inactive, observers receive one clearing notification, and a repeated clear is a no-op that notifies nobody

### Requirement: Boot integration
The boot scene SHALL clear any previously active session before it attempts a boot and SHALL activate the session only after a successful bootstrap, so the ready state carries exactly the bootstrapped save — its user identifier and a summary equal to the response — and any failed boot attempt (unreachable endpoint, structured API error, or malformed response) SHALL leave no session behind.

#### Scenario: Session active at ready
- **WHEN** the boot completes successfully against the fake implementation
- **THEN** the session is active, names the bootstrapped save, and its name, level, and xp equal the fixture save

#### Scenario: No session after a failed boot
- **WHEN** a boot attempt fails with an unreachable endpoint or a structured API error
- **THEN** the session is inactive — no stale or partial session exists

#### Scenario: Replace the previous session on a new attempt
- **WHEN** a successful boot is followed by a further boot attempt that fails
- **THEN** the previously active session is cleared by the new attempt and no session remains

### Requirement: Containment and scope
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render and boot evidence inputs, the conversion packages, the asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; and the updated project-scope test SHALL enforce exactly the three allow-listed autoloads with the two new files allow-listed while `GameClock`, camera, UI foundation, legacy-protocol, and non-loopback transport tokens remain forbidden.

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed, exactly the `GameApi`, `ContentRegistry`, and `Session` autoloads are registered, and no forbidden token appears in any project script or scene

#### Scenario: Keep prior verifications green
- **WHEN** the full verification battery runs in the final state
- **THEN** the render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the session-suite verification and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the Session scaffold delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers the Session autoload scaffold, which M5 items remain, and points to the committed evidence
