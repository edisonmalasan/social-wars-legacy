# Spec Delta

## Purpose

Let a player collect the income a building produces through the modern stack — a typed intent from the Godot client executed by the unchanged legacy command path inside Compatibility API v0, with an executed-legacy fixture as the parity oracle, a payout derived from committed content, and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy collect fixture

The repository SHALL capture a collect transaction by executing the real legacy server's `command.php` `collect` command inside a disposable copy under the pinned interpreter — recording the request, the complete player save before execution, the response, and the complete save after execution — and SHALL commit that fixture together with a manifest and a README documenting the capture command, its exit codes, its containment, the derived payout and rung the request carries, and which parts of the contract are established evidence versus derived; the capture SHALL leave every working-tree legacy source, config, village, and save byte-identical and SHALL write only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the collect fixture capture command runs
- **THEN** the transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-collect/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: The fixture records the collection in place

- **WHEN** the recorded after-state is inspected
- **THEN** the row keeps its item id, cell, key, orientation, player, and attribute bag and carries a re-stamped collection instant, the placement count is unchanged, the derived payout landed in exactly the resource and experience the request carried, and every other row, the whole private state, the storage, the player info, and every other resource are unchanged

#### Scenario: Replay parity offline

- **WHEN** the collect parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field, with the row's re-stamped collection instant documented and normalized

### Requirement: Collection payout derivation

The service SHALL derive a collection's resource vector entirely from committed content and the addressed row's own state, never from client input: the amount from the item's committed collection amount, the resource from its committed collection type, the experience from its committed collection experience, each scaled by the committed ladder rung the row has actually reached, with the elapsed time measured from the row's recorded collection instant and clamped at the top rung. Every rung and every rule behind that derivation SHALL be marked derived-provisional wherever the derivation is recorded, because no legacy branch reads the content that describes it. A collection whose item records a non-zero collection cap SHALL be refused rather than paid under an invented cap semantics, a collection whose item records a resource type outside the committed set SHALL be refused rather than paid into an assumed resource, and the vector's unread slot and its experience-free resource slot SHALL be left zero.

#### Scenario: A collection pays the committed amount at the reached rung

- **WHEN** a collect intent is executed for a row that has reached a committed ladder rung
- **THEN** the applied vector carries the item's committed amount in the slot its committed resource type names and its committed experience, each scaled by that rung's committed multiplier, and no client-supplied value influences either

#### Scenario: The elapsed time is clamped at the top rung

- **WHEN** a row's elapsed time exceeds the last committed rung
- **THEN** the top rung's committed multiplier is used and no larger amount is derived or extrapolated

#### Scenario: A capped or unmappable item is refused, not paid

- **WHEN** the item records a non-zero collection cap, or a resource type outside the committed set
- **THEN** the service answers a structured JSON error, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: The ladder is marked derived wherever it is recorded

- **WHEN** the derivation is recorded in the envelope module, the fixture README, the application documentation, or the structural report
- **THEN** the amount formula, the experience scaling, the sub-first-rung behavior, the cap semantics, the shared-field rule, and the cash/experience semantics are each marked derived-provisional rather than observed

### Requirement: Collection execution endpoint

Compatibility API v0 SHALL expose a loopback-only collect endpoint that accepts an intent — save id and the legacy map index of an existing placement — and never client-supplied amounts, resources, tiers, times, prices, or resource deltas. The endpoint SHALL resolve the index against the save's own placements before executing, derive the legacy command envelope internally, execute the unchanged legacy command dispatcher in-process so the legacy resource application, the row's collection-instant write, and the batch save persistence run exactly as the legacy code performs them, persist only into the service corpus, and answer with the legacy result plus an authoritative superset carrying the row as read before execution, the row re-read after execution, the derived payout with the rung it came from, the reference instant the rung was computed against, and the current resources. Every structurally unresolvable input — a non-object body, a missing, invalid, or unknown save id, a missing or non-integer item index, or an item index that names no placement in the save — SHALL fail closed with a structured JSON error and no mutation. After execution the endpoint SHALL require that the row still exists, that its recorded collection instant moved forward, and that every stored resource changed by exactly the derived delta; any other outcome SHALL fail closed with a structured error rather than report the legacy success, so a reduced or diverging payout is reported instead of trusted.

#### Scenario: Collect successfully

- **WHEN** a valid collect intent names a known save and an existing placement
- **THEN** the unchanged legacy command path executes, the corpus save persists the row with a re-stamped collection instant and the derived payout applied to exactly the named resource and the experience, and the response carries both rows, the derived payout with its rung, the reference instant, and the current resources

#### Scenario: An unknown placement index fails closed

- **WHEN** the intent's item index is an integer that names no placement in the corpus save
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: A payout that did not land in full fails closed

- **WHEN** execution completes but a resource did not change by exactly the derived delta, or the collection instant did not move forward
- **THEN** the service answers a structured error instead of the legacy success, and the corpus save is left as the legacy batch left it, with the failure reported rather than hidden

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, the item index is missing or non-integer, or the request carries any other shape the contract does not define
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no row is rewritten and no resource moves

#### Scenario: Persist into the corpus only

- **WHEN** a collection executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with collection execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Collection is refused on a row under construction

A collection SHALL NOT be executed on a row carrying construction state, and the refusal SHALL hold in both layers: the client SHALL offer no collection action for such a row and send nothing, and the service SHALL fail closed with a structured conflict error **before** the legacy dispatcher runs, so that a client which ignores the client-side rule still cannot corrupt the row's recorded collection instant, which the delivered construction behavior uses as a build's start instant. This requirement exists because executing a collection on a row whose construction was just started overwrites that start instant while the recorded countdown survives, silently restarting an active build's timer, and the legacy server reports the transaction as a success.

#### Scenario: The client refuses a building under construction

- **WHEN** the player selects a placed building that carries a recorded countdown or a recorded build-click counter
- **THEN** no collection action is offered and any attempt to collect it is refused with an explicit reason, with no request sent

#### Scenario: The service refuses even when the client asks

- **WHEN** a collect intent names a placement that carries construction state
- **THEN** the service answers a structured conflict error, the legacy dispatcher never runs, and the corpus save is byte-identical — the build's start instant and recorded countdown are untouched

#### Scenario: Both refusals are recorded with the evidence

- **WHEN** the change's documentation is read
- **THEN** it records the executed probe that a collection on a just-started construction overwrites the start instant while the countdown survives and that the legacy server answers success, and states the rule as the safest behavior supported by that evidence while marking the legacy client's own behavior as unobserved

### Requirement: Collection flow

The client SHALL provide a collection flow over the typed GameApi collection operation: a collection readout for a selected placed building showing what the next collection would yield, which resource it would be paid in, the committed ladder rungs, and how long until the next rung; and a `Collect` action on the selection-driven surface, mutually exclusive with the delivered move, sell, store, upgrade, and construction modes, opening a confirm that names the derived payout; and a confirm that sends exactly one intent. The readout and the confirm SHALL use the same committed content the service derives from, and the confirm's amount SHALL be presented as derived rather than authoritative. Cancelling SHALL send nothing and leave the town byte-identical, and a building with no addressable legacy key, no committed income, or no reached rung SHALL be refused with an explicit reason and no request. On success the flow SHALL apply only the authoritative response — the typed row replaced by the response's post-execution row, the same object retained in depth order, and the HUD balances, experience, and readout taken from the response values rather than from the client's own arithmetic — and on any failure it SHALL surface an explicit error naming the failure with the row unchanged and no balance moved. The flow SHALL NOT collect from a building under construction, SHALL NOT offer a collection below the first committed rung, and SHALL NOT alter the construction timers.

#### Scenario: Collect a building's income

- **WHEN** the player selects an income-bearing building that has reached a committed rung, chooses the collect action, and confirms
- **THEN** exactly one collection intent is sent, and on success the building's recorded collection instant is re-stamped, the HUD balances and experience take the response values, and the readout reflects the new clock

#### Scenario: Balances move only by the server's numbers

- **WHEN** the client derived a payout that differs from the response's
- **THEN** the response wins: the applied balances and experience are the response's values, and the client's own arithmetic is discarded rather than added to them

#### Scenario: Nothing to offer, nothing sent

- **WHEN** the selected building has no committed income, has not reached the first committed rung, is under construction, or is not addressable
- **THEN** no collection action is offered and any attempt is refused with an explicit reason, with no request sent and the town unchanged

#### Scenario: A failed request moves nothing

- **WHEN** the collection request fails at transport or returns a structured error, including an index the service does not know, a capped item, a refused construction state, and a post-state the service rejects
- **THEN** an explicit error names the failure, the row keeps its previous collection instant, and the HUD keeps its pre-request balances

### Requirement: Collection evidence, provenance, and claim limits

The change SHALL commit a windowed capture of a completed collection together with a deterministic structural report recording its inputs and digests, the intent, both rows, the derived payout and the rung it came from, the committed ladder, the next-rung countdown, the resource movement before and after, the request counts, and explicit non-claims, and every artifact SHALL distinguish the parts of the contract that are **established** from committed legacy source and executed-legacy evidence — that the branch writes only the collection instant, that the income is the client-sent vector applied verbatim per resource under the documented clamp, and that a collection on a row under construction overwrites the build's start instant while the countdown survives — from the parts that are **derived** and never observed from the Flash client: the amount formula, the experience scaling, the sub-first-rung behavior, the cap semantics, the shared-field refusal, and the cash and experience semantics. The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; the claim is that a payout grows in four committed rungs derived from the item's committed income fields, never any specific amount the legacy client pays; the clamp is not exercised by the fixture because the derived payout never drives a balance below zero; parity covers one recorded transaction against the fresh-player corpus, whose only income-bearing rows are decorations because the real factories are not placed; and no pixel-parity oracle against the legacy client exists. The report SHALL be byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town showing the collection readout and the structural report are committed under `apps/client-godot/evidence/building-collect/`, and the report carries the established-versus-derived split and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the existing locked dependencies and no new packages; legacy sources, configs, saves, villages, committed fixtures, conversion packages, registry manifests, and the committed M4, M6, and every delivered gameplay slice's evidence SHALL remain byte-identical across the change (SHA-256 guards plus the hash manifest); collection execution SHALL never write a working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic collect suite and the live collect phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually executed — collect fixture capture, the collect tests, both batteries — with their purposes, the loopback port, the evidence paths, the established-versus-derived provenance of every payout rule, and the limits of the collection claim, and the committed investigation record SHALL be updated with the six decisions as resolved and with the executed probe that closed the shared-field question, and the roadmap Project Status ledger SHALL record the M7 progress this change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record which parts of the collection contract are established evidence and which are derived

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers (collect income), which M7 deliver lines remain, and points to the committed evidence
