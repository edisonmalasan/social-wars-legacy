# Spec Delta

## Purpose

Let a player place a building into their town through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy placement fixture

The repository SHALL capture a placement transaction by executing the real legacy server's `command.php` `buy` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, and its containment, so placement parity has an executed-legacy oracle; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the placement fixture capture command runs
- **THEN** the `buy` transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-placement/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline

- **WHEN** the placement parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with every time-dependent field documented and normalized

### Requirement: Placement execution endpoint

Compatibility API v0 SHALL expose a loopback-only placement endpoint that accepts an intent — save id, building id, grid coordinates, orientation — and never client-supplied resource deltas; the endpoint SHALL derive the legacy command envelope internally (price vector from the item's config `costs`, next free map slot, player team), execute the unchanged legacy command dispatcher in-process so the legacy resource application, placement-entry rules, and batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the persisted eight-field placement entry and the current resources. Structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a building id absent from config, or coordinates that are not integers within the town grid — SHALL fail closed with a structured JSON error and no mutation, and insufficient resources SHALL reproduce legacy clamping rather than rejection.

#### Scenario: Place a building successfully

- **WHEN** a valid placement intent names a known save and a store-listed building at free in-grid cells
- **THEN** the unchanged legacy command path executes, the corpus save persists with a new eight-field placement entry (item, x, y, timestamp, orientation, store, attr, player) at the requested cell under the next free map slot and player team, and the response carries the persisted entry and the current resources

#### Scenario: Resource changes come only from the derived price vector

- **WHEN** a placement intent is executed
- **THEN** no client-supplied resource delta is accepted anywhere in the contract, and the applied resource change equals the negated config `costs` values mapped onto the legacy resource vector (gold, wood, oil, steel, cash)

#### Scenario: Insufficient resources clamp instead of rejecting

- **WHEN** the derived cost exceeds the player's current resources
- **THEN** the placement still executes and each affected resource is applied with the legacy clamp at zero — never a rejection — and the response reports the clamped values

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the building id is absent from config, or a coordinate is non-integer or outside the town grid
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no placement entry is written

#### Scenario: Persist into the corpus only

- **WHEN** a placement executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with placement execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Placement flow

The client SHALL provide a placement flow over the typed GameApi placement operation: a build picker over a placement catalog parsed fail-closed from the bootstrap payload the client already receives (store-listed buildings gated by their `min_level` against the loaded level, showing name, content footprint, and derived cost from that same payload), a footprint preview at the inverse-projected cell that marks a target invalid when it lies outside the grid or covers an existing footprint and shows the cost against current resources, and a confirm that sends exactly one intent. On success the flow SHALL apply only the authoritative response — the new object rendered at its cell with its content footprint in depth order and HUD resources updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with no object added and no resource changed. The catalog SHALL fail closed to an explicit error with placement unavailable rather than guess a price or fabricate an entry.

#### Scenario: Place a building through the flow

- **WHEN** the player opens the build picker, chooses a store-listed building their level allows, previews a free in-grid cell, and confirms
- **THEN** exactly one placement intent is sent, and on success the new building renders at that cell with its content footprint in depth order while the HUD resources change to the response values

#### Scenario: Invalid targets send nothing

- **WHEN** the previewed cell is outside the grid, covers an existing footprint, or the building's cost exceeds current resources
- **THEN** the preview is marked invalid, no request is sent, and the town state, selection, and resources are unchanged

#### Scenario: A failed request changes nothing

- **WHEN** the placement request fails at transport or returns a structured error
- **THEN** an explicit error names the failure, no object is added, and the HUD keeps its pre-request values

#### Scenario: Catalog fails closed

- **WHEN** the bootstrap payload lacks or malforms the fields the placement catalog needs
- **THEN** placement is unavailable behind an explicit error rather than a guessed price or a fabricated entry

### Requirement: Placement evidence and claim limits

The change SHALL commit a windowed capture of a placed building together with a deterministic structural report recording its inputs and digests, the placement intent, the resulting placement counts and resources, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the price vector, envelope placeholders, and slot choice are derived, never observed from the Flash client; parity covers one recorded transaction against the fresh-player corpus, not progressed players; insufficient resources reproduce legacy clamping, not rejection; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town containing the newly placed building and the structural report are committed under `apps/client-godot/evidence/placement/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4 and M6 evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); placement execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — placement fixture capture, placement parity tests, both batteries — with their purposes, the loopback port, the evidence paths, and the limits of the placement claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (placement), which M7 deliver lines remain, and points to the committed evidence
