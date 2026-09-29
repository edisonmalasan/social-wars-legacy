## Purpose

Let a player put a building they own into their storage through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle and no Flash, browser, or external network.

## Requirements

### Requirement: Executed-legacy store fixture

The repository SHALL capture a store transaction by executing the real legacy server's `command.php` `store_item` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, and its containment, so store parity has an executed-legacy oracle; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the store fixture capture command runs
- **THEN** the `store_item` transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-store/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline

- **WHEN** the store parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with every time-dependent field documented and normalized

### Requirement: Store execution endpoint

Compatibility API v0 SHALL expose a loopback-only store endpoint that accepts an intent — save id and the legacy map index of an existing placement — and never client-supplied resource deltas, price, or quantity; the endpoint SHALL resolve the index against the save's own placements before executing, derive the legacy command envelope internally (one `store_item` command whose single argument is the item index, with a neutral derived resource vector), execute the unchanged legacy command dispatcher in-process so the legacy resource application, row pop, storage increment, and batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the eight-field row as read before execution, the full post-execution storage mapping, and the current resources. The endpoint SHALL fail closed if the popped key survives execution or the storage entry did not land. Structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a missing or non-integer item index, or an item index that names no placement in the save — SHALL fail closed with a structured JSON error and no mutation.

#### Scenario: Store a placed building successfully

- **WHEN** a valid store intent names a known save and an existing placement index
- **THEN** the unchanged legacy command path executes, the corpus save persists without that row and with the item's id present in storage, every other row unchanged, and the bought-units list unchanged (the legacy branch does not write it), and the response carries the pre-execution row, the full storage mapping, and the current resources

#### Scenario: Resource changes come only from the derived vector

- **WHEN** a store intent is executed
- **THEN** no client-supplied resource delta or price is accepted anywhere in the contract, and the applied resource change equals the derived vector, which is neutral because the committed configuration records no price for storing — so this change claims no storing cost rather than inventing one

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or the request carries any other shape the contract does not define
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and neither the map nor the storage is modified

#### Scenario: Persist into the corpus only

- **WHEN** a store executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with store execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Store flow

The client SHALL provide a store flow over the typed GameApi store operation: a `Store` action on the selection-driven surface, offered only for a selected placed building the move and sell flows also require, opening a confirm that names the building and reports where it will land; a confirm that sends exactly one intent. Cancelling SHALL send nothing and leave the town byte-identical, and a placement with no addressable legacy key SHALL be refused with the same explicit reason the move and sell flows already use. On success the flow SHALL apply only the authoritative response — that building's object removed, its typed placement removed while the remaining buildings keep the committed depth order, the typed storage replaced through the same fail-closed parser the payload parse uses, the storage readout re-rendered from it, and HUD resources and XP updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with the building still on the map, the storage unchanged, and no resource changed. Storing SHALL NOT change the bought-units list, SHALL NOT place anything, and SHALL NOT sell or grant anything.

#### Scenario: Store a building through the flow

- **WHEN** the player selects a placed building, chooses the store action, and confirms
- **THEN** exactly one store intent is sent, and on success that building is gone from the town, the storage readout shows its item id with the response's quantity, and the HUD resources take the response values

#### Scenario: Cancelling sends nothing

- **WHEN** the player opens the store confirm and cancels it
- **THEN** no request is sent and the town state, storage readout, selection, and resources are unchanged

#### Scenario: A failed request stores nothing

- **WHEN** the store request fails at transport or returns a structured error, including an index the service does not know
- **THEN** an explicit error names the failure, the building is still on the map, the storage readout is unchanged, and the HUD keeps its pre-request values

#### Scenario: Modes are mutually exclusive

- **WHEN** a store confirm is armed and the player tries to arm the move or sell action (or the selection changes)
- **THEN** the conflicting action is refused with an explicit reason, no request is sent, and the armed store confirm is unchanged

### Requirement: Store evidence and claim limits

The change SHALL commit a windowed capture of a completed store together with a deterministic structural report recording its inputs and digests, the store intent, the stored building's row and cell, the storage mapping and the placement count before and after, the resources before and after, the request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the command's argument value and the neutral price vector are derived, never observed from the Flash client; **no storing cost and no capacity rule are claimed**, because the committed configuration records neither and the legacy server has no capacity check; the bought-units list is deliberately not written by the legacy branch; this line only moves a building *into* storage, so stored items are not yet playable and `place_stored_item` remains open; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town without the stored building and its storage readout, together with the structural report, are committed under `apps/client-godot/evidence/building-store/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, placement, purchase, move, and sell evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); store execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6/placement/purchase/move/sell evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic store suite and the live store phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — store fixture capture, the store tests, both batteries — with their purposes, the loopback port, the evidence paths, and the limits of the store claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (store), which M7 deliver lines remain, and points to the committed evidence
