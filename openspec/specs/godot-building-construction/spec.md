## Purpose

Let a player start, count, and complete the construction of a building they own through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy construction fixture as the parity oracle and no Flash, browser, or external network.

## Requirements

### Requirement: Executed-legacy construction fixture

The repository SHALL capture a construction transaction by executing the real legacy server's `command.php` request carrying the derived batch — a construction start whose duration is derived from committed content, followed by a build click — inside a disposable copy under the pinned interpreter, recording the request, the complete player save before execution, the response, and the complete save after execution, and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, its containment, and which parts of the contract are established evidence versus derived; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the construction fixture capture command runs
- **THEN** the transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-construction/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: The fixture records the construction state in place

- **WHEN** the recorded after-state is inspected
- **THEN** the row keeps its item id, cell, key, orientation, player, storage, and placement count, and carries a recorded countdown equal to the item's committed build time together with a click counter, while the whole private state, the storage, the player info, and every resource are unchanged

#### Scenario: Replay parity offline

- **WHEN** the construction parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with the row's re-stamped wall-clock start time documented and normalized

### Requirement: Construction execution endpoint

Compatibility API v0 SHALL expose a loopback-only construction endpoint that accepts an intent — save id, the legacy map index of an existing placement, and one of three documented actions naming an outcome (start a build, record a build click, complete a build) — and never client-supplied countdowns, prices, or resource deltas. The endpoint SHALL resolve the index against the save's own placements before executing, derive the legacy command and every one of its arguments from committed content and the row's own state — the start countdown from the item's committed build time, never from the client — execute the unchanged legacy command dispatcher in-process so the legacy resource application, the timestamp write, the attribute-bag writes, and the batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the row as read before execution, the row re-read after execution, the resolved action, and the current resources. A missing, non-integer, or non-positive committed build time, a placement with no resolvable construction state, and every structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a missing or non-integer item index, an item index that names no placement in the save, or an action outside the documented set — SHALL fail closed with a structured JSON error and no mutation. After execution the endpoint SHALL require that the row still exists and that the action's own post-condition holds; any other outcome SHALL fail closed with a structured error rather than report the legacy success.

#### Scenario: Start, click, and complete a build

- **WHEN** valid construction intents name a known save, an existing placement, and each documented action in turn
- **THEN** the unchanged legacy command path executes the matching derived command, the corpus save persists the row's timestamp and attribute-bag changes with every other field unchanged, and each response carries both rows, the resolved action, and the current resources

#### Scenario: The countdown is derived from committed content

- **WHEN** a start action is executed
- **THEN** the derived command's duration equals the item's committed build time and no client-supplied value can influence it, and a missing, non-integer, or non-positive committed build time fails closed instead of being coerced

#### Scenario: Resource changes come only from the derived vector

- **WHEN** a construction intent is executed
- **THEN** no client-supplied resource delta or price is accepted anywhere in the contract, the applied resource change equals the derived vector, which is neutral because the committed configuration records no price for building — so this change claims no building cost rather than inventing one

#### Scenario: An unknown action fails closed

- **WHEN** the action is missing, not a string, or outside the documented set
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: A post-state that is not the promised construction fails closed

- **WHEN** execution completes but the row is gone, is not a row, or the action's own post-condition does not hold — a start without the derived countdown, a click without a click counter, or a completion that still carries one
- **THEN** the service answers a structured error instead of the legacy success, and the corpus save is left as the legacy batch left it, with the failure reported rather than hidden

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or the request carries any other shape the contract does not define
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no row is removed or rewritten

#### Scenario: Persist into the corpus only

- **WHEN** a construction intent executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with construction execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Construction flow

The client SHALL provide a construction flow over the typed GameApi construction operation: a `Build` action on the selection-driven surface, offered only for a selected addressable placed building and mutually exclusive with the delivered move, sell, store, and upgrade modes, opening a confirm whose single primary step follows the row's own construction state — starting a build with the derived duration when no construction state is present, recording a build click while the click counter is below the item's committed click requirement, and completing the build once the counter has reached it, with no step offered when a countdown is running and the counter is already consumed. A placement with no addressable legacy key SHALL be refused with the same explicit reason the delivered flows use, cancelling SHALL send nothing and leave the town byte-identical, and the confirm SHALL NOT offer a cancellation that clears the building's construction state, because the legacy command that clears the attribute bag also destroys the click counter and any friend-assistance state. The client SHALL show the building's construction progress (the click counter against the item's committed click requirement) and, when a countdown is recorded, its remaining time derived from that countdown and the row's recorded start time. On success the flow SHALL apply only the authoritative response — the typed row replaced by the response's post-execution row, the same rendered object retained in depth order, and HUD resources and XP updated from the response values — and on any failure it SHALL surface an explicit error naming the failure with the row unchanged and no resource changed. The flow SHALL NOT hire or finish friend assistance, apply a speedup, or remove the building.

#### Scenario: Walk a building through its construction

- **WHEN** the player selects a placed building, chooses the build action, and confirms each offered step in turn
- **THEN** exactly one construction intent is sent per step, the offered step follows the row's state — start, then click, then complete, then nothing to do — and on each success the readout and HUD take the response values

#### Scenario: Only the promised step is offered

- **WHEN** the selected row already carries a countdown with the click counter consumed, or its click counter has already reached the requirement
- **THEN** no step is offered and any attempt is refused with an explicit reason, with no request sent

#### Scenario: Cancelling sends nothing and never clears construction state

- **WHEN** the player opens the build confirm and cancels it
- **THEN** no request is sent, the town state, selection, and resources are unchanged, and no action that would clear the building's construction state is reachable

#### Scenario: A failed request changes nothing

- **WHEN** the construction request fails at transport or returns a structured error, including an index the service does not know, an unknown action, and a post-state the service rejects
- **THEN** an explicit error names the failure, the row keeps its previous construction state, and the HUD keeps its pre-request values

### Requirement: Construction evidence, provenance, and claim limits

The change SHALL commit a windowed capture of a completed construction sequence together with a deterministic structural report recording its inputs and digests, the intent and its resolved action, the derived duration together with the committed field it came from, both rows, the click counter, the countdown, the request counts, and explicit non-claims, and every artifact SHALL distinguish the parts of the contract that are **established** from committed legacy source and executed-legacy evidence (the three commands' argument shapes and effects, that they write only the row's timestamp and attribute bag, that the click counter is seeded by the purchase half, the start countdown's recorded shape, and that no server-side completion rule exists) from the parts that are **derived** and never observed from the Flash client (that a real construction sends these commands, that the duration is the item's committed build time rather than its activation field or a speedup-adjusted figure, and the automatic timing of the legacy client's loop). The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no building cost is claimed**; the click threshold and the remaining time are client-side derivations with no server enforcement; construction speedups and their recorded price are out of scope; the friend-assist mechanism is out of scope, so no friend can be hired or finished here; the legacy command that clears the attribute bag is never used as a cancel; parity covers one recorded transaction against the fresh-player corpus, not progressed players; and no pixel-parity oracle against the legacy client exists. The report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing a building under construction and the structural report are committed under `apps/client-godot/evidence/building-construction/`, and the report carries the established-versus-derived split and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, and every delivered gameplay slice's evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); construction execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic construction suite and the live construction phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — construction fixture capture, the construction tests, both batteries — with their purposes, the loopback port, the evidence paths, the established-versus-derived provenance of the contract, and the limits of the construction claim, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record which parts of the construction contract are established evidence and which are derived

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (construction timers), which M7 deliver lines remain, and points to the committed evidence
