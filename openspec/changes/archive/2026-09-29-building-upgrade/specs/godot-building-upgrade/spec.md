# Spec Delta

## Purpose

Let a player upgrade a building they own to its next tier through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy two-command fixture as the parity oracle and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy upgrade fixture

The repository SHALL capture an upgrade transaction by executing the real legacy server's `command.php` request carrying the derived two-command batch — a `sell` with the committed upgrade reason followed by a `buy` of the target tier reusing the row's own map key and cell — inside a disposable copy under the pinned interpreter, recording the request, the complete player save before execution, the response, and the complete save after execution, and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, its containment, and which parts of the transaction are established evidence versus derived; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the upgrade fixture capture command runs
- **THEN** the two-command transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-upgrade/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: The fixture records the replacement in place

- **WHEN** the recorded after-state is inspected
- **THEN** the upgraded key holds the target tier's id at the pre-execution cell, the placement count is unchanged because the key is reused, the bought-units list gains the target tier because the purchase half records it, and every other row and every resource is unchanged

#### Scenario: Replay parity offline

- **WHEN** the upgrade parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with the newly written row's wall-clock timestamp documented and normalized

### Requirement: Upgrade execution endpoint

Compatibility API v0 SHALL expose a loopback-only upgrade endpoint that accepts an intent — save id and the legacy map index of an existing placement — and never client-supplied target tier, reason, coordinates, orientation, player, quantity, price, or resource deltas. The endpoint SHALL derive the target tier from the committed configuration's upgrade reference, the reason from the committed legacy constant, the cell, orientation, and player from the row being replaced, and a neutral derived resource vector for both commands; it SHALL execute the unchanged legacy command dispatcher in-process so the legacy resource application, the reason-carrying row deletion, the fresh row write, the bought-units record, and the batch save persistence run exactly as the legacy code performs them; it SHALL persist only into the service corpus; and it SHALL answer with the legacy result plus an authoritative superset carrying the row as read before execution, the row re-read after execution, and the current resources. A placement with no resolvable upgrade path, and every structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a missing or non-integer item index, or an item index that names no placement in the save — SHALL fail closed with a structured JSON error and no mutation. After execution the endpoint SHALL require that the key still exists, that its item id equals the derived target tier, and that its cell equals the pre-execution cell; any other outcome SHALL fail closed with a structured error rather than report legacy's success.

#### Scenario: Upgrade a placed building successfully

- **WHEN** a valid upgrade intent names a known save and an existing placement that has a resolvable next tier
- **THEN** the unchanged legacy command path executes both derived commands, the corpus save persists the target tier at that key and cell with the counted purchase half's bought-units record, and the response carries both rows and the current resources

#### Scenario: Resource changes come only from the derived vector

- **WHEN** an upgrade intent is executed
- **THEN** no client-supplied resource delta or price is accepted anywhere in the contract, both commands carry the derived neutral vector, and the player's stored resources are unchanged — the change therefore claims no upgrade cost of any kind

#### Scenario: A placement with no upgrade path fails closed

- **WHEN** the intent's placement has no resolvable next tier in the committed configuration
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged — a building that cannot be upgraded is never reduced to a bare sale

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: A post-state that is not the derived upgrade fails closed

- **WHEN** execution completes but the key is absent, holds a different item id than the derived target tier, or sits at a different cell
- **THEN** the service answers a structured error instead of legacy's success — the outcome the reverse command order produces, which the legacy server itself reports as a success — and the corpus save is left as the legacy batch left it, with the failure reported rather than hidden

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or the request carries any other shape the contract does not define
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no row is removed or rewritten

#### Scenario: Persist into the corpus only

- **WHEN** an upgrade executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with upgrade execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Upgrade flow

The client SHALL provide an upgrade flow over the typed GameApi upgrade operation: an `Upgrade` action on the selection-driven surface, offered only for a selected addressable placed building that has a resolvable next tier, opening a confirm that names the current tier and the target tier; and a confirm that sends exactly one intent. The action SHALL be mutually exclusive with the delivered move, sell, and store modes, a placement with no addressable legacy key or no resolvable next tier SHALL be refused with an explicit reason and no request, and cancelling SHALL send nothing and leave the town byte-identical. On success the flow SHALL apply only the authoritative response — the same building's object replaced by the target tier at the same cell and key, the typed row replaced by the response's post-execution row, the remaining buildings keeping the committed depth order, and HUD resources and XP updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with the building unchanged and no resource changed. The flow SHALL NOT construct, complete, or time the upgrade: the new row's construction counter is reported as it arrives and is left for the construction-timer behavior.

#### Scenario: Upgrade a building through the flow

- **WHEN** the player selects a placed building, chooses the upgrade action, and confirms
- **THEN** exactly one upgrade intent is sent, and on success that key holds the target tier at the same cell in depth order while the HUD resources take the response values

#### Scenario: A building with no upgrade path cannot be upgraded

- **WHEN** the selected building's item has no resolvable next tier
- **THEN** the upgrade action is not offered and any attempt is refused with an explicit reason, with no request sent

#### Scenario: Cancelling sends nothing

- **WHEN** the player opens the upgrade confirm and cancels it
- **THEN** no request is sent and the town state, selection, and resources are unchanged

#### Scenario: A failed request upgrades nothing

- **WHEN** the upgrade request fails at transport or returns a structured error, including an index the service does not know and a post-state the service rejects
- **THEN** an explicit error names the failure, the building keeps its current tier, and the HUD keeps its pre-request values

### Requirement: Upgrade evidence, provenance, and claim limits

The change SHALL commit a windowed capture of a completed upgrade together with a deterministic structural report recording its inputs and digests, the upgrade intent, both rows and both tiers, the bought-units change, the placement and object counts and resources before and after, the request counts, and explicit non-claims, and every artifact SHALL distinguish the parts of the contract that are **established** from committed legacy source and executed-legacy evidence (the absence of an upgrade command, the committed upgrade reason, the purchase's client-supplied key and cell, the fresh row semantics, the bought-units record, the forced command order, and the resulting state) from the parts that are **derived** and never observed from the Flash client (that the client sends exactly this pair, the purchase's orientation, player, and discarded arguments, and the price vector). The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no upgrade cost is claimed**; the construction counter the purchase half seeds is reported but not consumed; the premium upgrade price field is not used; the legacy client's level gate, daily-upgrade limit, and space check are known to exist and are deliberately not implemented here, with the corpus reason the level gate cannot be enforced; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists. The report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing the target tier at the same cell and the structural report are committed under `apps/client-godot/evidence/building-upgrade/`, and the report carries the established-versus-derived split and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, and every delivered gameplay slice's evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); upgrade execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic upgrade suite and the live upgrade phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — upgrade fixture capture, the upgrade tests, both batteries — with their purposes, the loopback port, the evidence paths, the established-versus-derived provenance of the contract, and the limits of the upgrade claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record which parts of the upgrade contract are established evidence and which are derived

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (upgrade), which M7 deliver lines remain, and points to the committed evidence
