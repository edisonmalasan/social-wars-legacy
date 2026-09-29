# Spec Delta

## Purpose

Let a player reposition a building they already own through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy move fixture

The repository SHALL capture a move transaction by executing the real legacy server's `command.php` `move` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, and its containment, so move parity has an executed-legacy oracle; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the move fixture capture command runs
- **THEN** the `move` transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-move/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline

- **WHEN** the move parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with every time-dependent field documented and normalized

### Requirement: Move execution endpoint

Compatibility API v0 SHALL expose a loopback-only move endpoint that accepts an intent — save id, the legacy map index of an existing placement, and grid coordinates — and never client-supplied resource deltas or price; the endpoint SHALL derive the legacy command envelope internally (one `move` command whose arguments are the item index, the target coordinates, and the documented placeholders the legacy branch discards, with a neutral derived resource vector), execute the unchanged legacy command dispatcher in-process so the legacy resource application, in-place coordinate writes, and batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the persisted eight-field placement entry and the current resources. Structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a non-integer item index, an item index that names no placement in the corpus, or coordinates that are not integers within the town grid — SHALL fail closed with a structured JSON error and no mutation.

#### Scenario: Move a placed building successfully

- **WHEN** a valid move intent names a known save, an existing placement index, and in-grid coordinates
- **THEN** the unchanged legacy command path executes, the corpus save persists that row with the requested coordinates and every other field unchanged, and the response carries the persisted entry and the current resources

#### Scenario: Resource changes come only from the derived vector

- **WHEN** a move intent is executed
- **THEN** no client-supplied resource delta or price is accepted anywhere in the contract, and the applied resource change equals the derived vector, which is neutral because the committed configuration records no move price — so the player's stored resources are unchanged by the move

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or a coordinate is non-integer or outside the town grid
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no placement row is written or moved

#### Scenario: Persist into the corpus only

- **WHEN** a move executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with move execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Addressable placements in typed town state

The client SHALL parse each placement together with the legacy map key it was stored under, so a placement can be named as the target of a move intent; a key that is not a positive integer SHALL be recorded as having no addressable index and never coerced to an index that could name a different placement.

#### Scenario: Placements carry their legacy key

- **WHEN** a town is loaded from a payload whose map stores placements under legacy keys
- **THEN** each parsed placement carries that key as its addressable index, verbatim, alongside its item id, cell, and raw row

#### Scenario: An unaddressable key is never coerced

- **WHEN** a placement row is stored under a key that is not a positive integer
- **THEN** the placement is parsed and rendered as before but carries no addressable index, and any attempt to move it is refused with an explicit reason instead of targeting a coerced index

### Requirement: Move flow

The client SHALL provide a move flow over the typed GameApi move operation: the player selects a placed building, arms the move, previews a target cell through the existing isometric projection with a footprint preview, and confirms exactly one intent. A target SHALL be marked invalid when its anchor lies outside the town grid or when its footprint covers a placement other than the one being moved, and a target equal to the building's current cell SHALL be refused, in each case with no request sent and no state change. On success the flow SHALL apply only the authoritative response — the same building repositioned at the target cell in depth order, its typed row replaced by the response's persisted entry, and HUD resources updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with nothing moved and no resource changed. Moving SHALL NOT require or perform a purchase: the building already exists in the save.

#### Scenario: Move a building through the flow

- **WHEN** the player selects a placed building, arms the move, previews a free in-grid cell, and confirms
- **THEN** exactly one move intent is sent, and on success that building renders at the target cell in depth order while the HUD resources take the response values

#### Scenario: Invalid targets send nothing

- **WHEN** the previewed cell is outside the grid, its footprint covers another placement, or it is the building's current cell
- **THEN** the preview is marked invalid with its reason, no request is sent, and the town state, selection, and resources are unchanged

#### Scenario: The building's own cells do not block it

- **WHEN** the previewed footprint overlaps only the cells the moving building already occupies
- **THEN** the target is valid and the move is not refused as occupied

#### Scenario: A failed request moves nothing

- **WHEN** the move request fails at transport or returns a structured error, including an index the service does not know
- **THEN** an explicit error names the failure, the building stays at its cell, and the HUD keeps its pre-request values

### Requirement: Move evidence and claim limits

The change SHALL commit a windowed capture of a completed move together with a deterministic structural report recording its inputs and digests, the move intent, the moved building's cell before and after, the placement count and resources, the request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the command's argument values, the arguments the legacy branch discards, and the neutral price vector are derived, never observed from the Flash client, so no claim is made about what moving costs in the legacy client; parity covers one recorded transaction against the fresh-player corpus, not progressed players; occupancy and grid-bounds rules are client-side only, with no server-authoritative validation; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing the building at its new cell and the structural report are committed under `apps/client-godot/evidence/building-move/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, placement, and purchase evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); move execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6/placement/purchase evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic move suite and the live move phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — move fixture capture, the move tests, both batteries — with their purposes, the loopback port, the evidence paths, and the limits of the move claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (move), which M7 deliver lines remain, and points to the committed evidence
