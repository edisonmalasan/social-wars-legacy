# Spec Delta

## Purpose

Let a player sell a building they own through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy sell fixture

The repository SHALL capture a sell transaction by executing the real legacy server's `command.php` `sell` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, and its containment, so sell parity has an executed-legacy oracle; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the sell fixture capture command runs
- **THEN** the `sell` transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-sell/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline

- **WHEN** the sell parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with every time-dependent field documented and normalized

### Requirement: Sell execution endpoint

Compatibility API v0 SHALL expose a loopback-only sell endpoint that accepts an intent — save id and the legacy map index of an existing placement — and never client-supplied resource deltas, refund, or sell reason; the endpoint SHALL resolve the index against the save's own placements before executing, derive the legacy command envelope internally (one `sell` command whose arguments are the item index and a derived reason the legacy branch treats as a log label, with a neutral derived resource vector), execute the unchanged legacy command dispatcher in-process so the legacy resource application, row deletion, and batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the eight-field row as read before execution, the current resources, and the fact that the row is absent from the persisted save. Structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a missing or non-integer item index, or an item index that names no placement in the save — SHALL fail closed with a structured JSON error and no mutation, and the combat reason that would route a row through the resurrectable-unit path SHALL be unreachable because no reason is accepted from the client.

#### Scenario: Sell a placed building successfully

- **WHEN** a valid sell intent names a known save and an existing placement index
- **THEN** the unchanged legacy command path executes, the corpus save persists without that row and with every other row and every resource unchanged, and the response carries the row as it was read before execution, the current resources, and the removal fact

#### Scenario: Resource changes come only from the derived vector

- **WHEN** a sell intent is executed
- **THEN** no client-supplied resource delta, refund, or price is accepted anywhere in the contract, and the applied resource change equals the derived vector, which is neutral because the committed configuration records no building-sale refund rule — so this change claims no refund at all rather than inventing one

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or the request carries any other shape the contract does not define
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no row is removed

#### Scenario: Persist into the corpus only

- **WHEN** a sell executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with sell execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Sell flow

The client SHALL provide a sell flow over the typed GameApi sell operation: a `Sell` action on the selection-driven surface that is offered only for a selected, addressable placed building and opens a confirm naming that building with no target, and a confirm that sends exactly one intent. Cancelling the confirm SHALL send nothing and leave the town byte-identical, and a placement with no addressable legacy key SHALL be refused with the same explicit reason the move flow already uses. On success the flow SHALL apply only the authoritative response — that building's object removed, its typed placement removed while the remaining buildings keep the committed depth order, and HUD resources and XP updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with the building still on the map and no resource changed. Selling SHALL NOT place anything, SHALL NOT touch storage, and SHALL NOT reach the legacy combat reason.

#### Scenario: Sell a building through the flow

- **WHEN** the player selects a placed building, chooses the sell action, and confirms
- **THEN** exactly one sell intent is sent, and on success that building is gone from the town, the remaining buildings keep their depth order, and the HUD resources take the response values

#### Scenario: Cancelling sends nothing

- **WHEN** the player opens the sell confirm and cancels it
- **THEN** no request is sent and the town state, selection, and resources are unchanged

#### Scenario: An unaddressable building cannot be sold

- **WHEN** the selected building's legacy map key is not a positive integer
- **THEN** the sell action is not offered and any attempt to sell it is refused with an explicit reason, with no request sent

#### Scenario: A failed request removes nothing

- **WHEN** the sell request fails at transport or returns a structured error, including an index the service does not know
- **THEN** an explicit error names the failure, the building is still on the map, and the HUD keeps its pre-request values

### Requirement: Sell evidence and claim limits

The change SHALL commit a windowed capture of a completed sale together with a deterministic structural report recording its inputs and digests, the sell intent, the removed building's row and cell, the placement and object counts and resources before and after, the request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the derived sell reason and the neutral price vector are derived, never observed from the Flash client; **no refund is claimed**, because the committed configuration records no building-sale refund rule and the legacy refund travels in client-sent deltas this contract refuses; the legacy combat reason is never reached; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town without the sold building and the structural report are committed under `apps/client-godot/evidence/building-sell/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, placement, purchase, and move evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); sell execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6/placement/purchase/move evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic sell suite and the live sell phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — sell fixture capture, the sell tests, both batteries — with their purposes, the loopback port, the evidence paths, and the limits of the sell claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (sell), which M7 deliver lines remain, and points to the committed evidence
