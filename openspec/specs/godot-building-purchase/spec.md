## Purpose

Let a player buy a store-listed, cash-priced item into their storage through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle and no Flash, browser, or external network.

## Requirements

### Requirement: Executed-legacy purchase fixture

The repository SHALL capture a purchase transaction by executing the real legacy server's `command.php` `buy_stored_item_cash` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, and its containment, so purchase parity has an executed-legacy oracle; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the purchase fixture capture command runs
- **THEN** the `buy_stored_item_cash` transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-item-purchase/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: Replay parity offline

- **WHEN** the purchase parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with every time-dependent field documented and normalized

### Requirement: Purchase execution endpoint

Compatibility API v0 SHALL expose a loopback-only purchase endpoint that accepts an intent — save id and item id — and never client-supplied resource deltas, price, or quantity; the endpoint SHALL derive the legacy command envelope internally (the item's config `costs` cash component as the legacy 8-slot resource vector, one `buy_stored_item_cash` command whose single argument is the item id, and the documented placeholders), execute the unchanged legacy command dispatcher in-process so the legacy resource application, `boughtUnits` update, storage update, and batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the persisted storage mapping and the current resources. Structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, an item id absent from config, an item id that is not an integer, or an item whose config price is not a cash price — SHALL fail closed with a structured JSON error and no mutation, and insufficient cash SHALL reproduce legacy clamping rather than rejection.

#### Scenario: Purchase an item into storage successfully

- **WHEN** a valid purchase intent names a known save and a store-listed, cash-priced item
- **THEN** the unchanged legacy command path executes, the corpus save persists the item id in storage with an incremented quantity and records the item as bought, and the response carries the persisted storage mapping and the current resources

#### Scenario: Resource changes come only from the derived cash price

- **WHEN** a purchase intent is executed
- **THEN** no client-supplied resource delta is accepted anywhere in the contract, and the applied resource change equals the negated cash amount of the item's config `costs` placed in the cash slot of the legacy resource vector, with every other slot zero

#### Scenario: Insufficient cash clamps instead of rejecting

- **WHEN** the derived cash price exceeds the player's current cash
- **THEN** the purchase still executes and cash is applied with the legacy clamp at zero — never a rejection — and the response reports the clamped values

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item id is missing, non-integer, or absent from config, or the item's config price is not a cash price
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no storage entry is written

#### Scenario: Persist into the corpus only

- **WHEN** a purchase executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with purchase execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Purchase flow

The client SHALL provide a purchase flow over the typed GameApi purchase operation: a shop surface over a fail-closed catalog parsed from the bootstrap payload the client already receives (store-listed entries gated by their `min_level` against the loaded level and whose config price is a cash price, each showing its price against current cash), a purchase confirm that sends exactly one intent, and a storage readout that renders the stored items of the typed town state with a resolved content name when one exists and the raw item id otherwise. An entry whose price exceeds the player's current cash SHALL be refused locally with an explicit reason and no request, and the flow SHALL mark no entry purchasable when the catalog is missing or malformed rather than guess a price or fabricate an entry. On success the flow SHALL apply only the authoritative response — the stored items and the HUD resources take the response's values verbatim — and on any failure it SHALL surface an explicit error naming the failure with no storage or resource changed.

#### Scenario: Purchase an item through the flow

- **WHEN** the player opens the shop surface, chooses a store-listed cash-priced item their level allows and their cash covers, and confirms
- **THEN** exactly one purchase intent is sent, and on success the storage readout shows the item with the response's quantity while the HUD resources change to the response values

#### Scenario: Unaffordable entries send nothing

- **WHEN** the player selects a shop entry whose cash price exceeds current cash
- **THEN** the confirm is refused with the explicit reason, no request is sent, and the storage readout and resources are unchanged

#### Scenario: A failed request changes nothing

- **WHEN** the purchase request fails at transport or returns a structured error
- **THEN** an explicit error names the failure, no storage entry is added, and the HUD keeps its pre-request values

#### Scenario: Catalog fails closed

- **WHEN** the bootstrap payload lacks or malforms the fields the purchase catalog needs
- **THEN** the purchase surface is unavailable behind an explicit error rather than a guessed price or a fabricated entry

### Requirement: Storage in typed town state

The client SHALL parse the player's storage from the bootstrap payload's default map into a typed, fail-closed mapping of item ids to integer quantities, preserving quantities verbatim (including zero) and ids it cannot resolve; an absent storage field SHALL be recorded as missing and named by the storage readout instead of being defaulted, and a storage field that is present but not an object, or whose quantity or key is not the documented shape, SHALL reject the parse naming the offending key. The purchase response's storage mapping SHALL be parsed by the same parser.

#### Scenario: Storage loads from the bootstrap payload

- **WHEN** a town is loaded from a payload whose default map carries a storage mapping
- **THEN** the typed state holds each item id with its exact integer quantity, quantity zero included, and the storage readout renders one line per entry

#### Scenario: Absent storage is named, not defaulted

- **WHEN** the payload carries no storage field
- **THEN** the parse succeeds, the state records the field as missing, and the storage readout names the missing field rather than showing an empty inventory as fact

#### Scenario: Malformed storage fails closed

- **WHEN** the storage field is not an object, or an entry's quantity is not an integer, or an entry's key is not an item id
- **THEN** the parse is rejected with an error naming the offending key and no state is produced

### Requirement: Purchase evidence and claim limits

The change SHALL commit a windowed capture of a completed purchase together with a deterministic structural report recording its inputs and digests, the purchase intent, the storage and resource values before and after, the purchase and bootstrap request counts, and explicit non-claims — no Flash, Ruffle, ActionScript, or browser executed; the chosen legacy command and the cash-only price derivation are derived, never observed from the Flash client; parity covers one recorded transaction against the fresh-player corpus, not progressed players; insufficient cash reproduces legacy clamping, not rejection; storage is display-only here, with no placing from or selling out of storage; and no pixel-parity oracle against the legacy client exists — and the report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture showing the shop surface with the purchased item in the storage readout and the structural report are committed under `apps/client-godot/evidence/purchase/`, and the report carries every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, and placement evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); purchase execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6/placement evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic purchase suite and the live purchase phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — purchase fixture capture, the purchase tests, both batteries — with their purposes, the loopback port, the evidence paths, and the limits of the purchase claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (purchase), which M7 deliver lines remain, and points to the committed evidence
