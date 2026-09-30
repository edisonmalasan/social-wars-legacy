# Spec Delta

## Purpose

Let a player unlock a town expansion through the modern stack — a typed intent from
the Godot client executed by the unchanged legacy command path inside Compatibility
API v0, with an executed-legacy fixture as the parity oracle, a debit derived from
committed content, and no Flash, browser, or external network.

## ADDED Requirements

### Requirement: Executed-legacy expand fixture

The repository SHALL capture an expansion transaction by executing the real legacy
server's `command.php` `expand` command inside a disposable copy under the pinned
interpreter — recording the request, the complete player save before execution, the
response, and the complete save after execution — and SHALL commit that fixture
together with a manifest and a README documenting the capture command, its exit
codes, its containment, the derived debit and the schedule row the request carries,
which parts of the contract are established evidence versus derived, and the two
additional probes that justify the endpoint's guards; the capture SHALL leave every
working-tree legacy source, config, village, and save byte-identical and SHALL write
only the fixture output.

#### Scenario: Capture from the executed legacy server

- **WHEN** the expand fixture capture command runs
- **THEN** the transaction's request, before-state, response, and after-state are committed under `tests/fixtures/godot-building-expand/` together with its manifest and README, the legacy server is started and stopped within the run, and no working-tree save is touched

#### Scenario: The fixture records the expansion in place

- **WHEN** the recorded after-state is inspected
- **THEN** the owned-expansions list grew by exactly one entry equal to the expansion id that was sent, appended at the end, with the existing entries unchanged, in order, and not deduplicated; the item placements, the map level, the map sizes, the storage, the whole private state, the player info, and every resource the derived debit did not name are unchanged; and the derived debit landed in exactly the resources the request carried

#### Scenario: Replay parity offline

- **WHEN** the expand parity tests run with no server and no network
- **THEN** the endpoint's response and its corpus save after execution equal the captured legacy response and after-state for every stable field

#### Scenario: The two guard probes are recorded with the fixture

- **WHEN** the fixture's README and manifest are read
- **THEN** they record that the legacy server accepted an expansion id outside the committed schedule, an id the player already owned, and a negative id, all answering success — which is the evidence for the endpoint's range and duplicate guards — and that a non-integer id raised an unhandled server error; and they record the probe in which a client-sent gold debit larger than the balance landed on zero rather than a negative balance

### Requirement: Expansion price derivation

The service SHALL derive an expansion's resource vector entirely from committed
content and the player's own state, never from client input: the cost from the
expansion's committed row in the 98-entry committed expansion schedule, indexed by
the expansion id itself; the schedule's gold-named field into the server's gold
resource and its cash field into the server's cash resource; every other resource
left unchanged. The id-space indexing and the gold naming SHALL be marked exactly
as the change's design states — the indexing as derived, and the gold naming as
established by the committed client asset names — wherever the derivation is
recorded. An id outside the committed schedule SHALL be refused rather than priced,
an id the player already owns SHALL be refused rather than duplicated, and an
expansion whose committed neighbor or inventory requirement is greater than zero
SHALL be refused rather than paid under an invented requirement rule. A committed
row costing nothing SHALL derive the all-zero vector rather than being refused.

#### Scenario: An expansion pays the committed cost of its id

- **WHEN** an expand intent is executed for an id with a committed schedule row
- **THEN** the derived vector is a debit carrying that row's gold-named cost in the gold resource and its cash cost in the cash resource, and no client-supplied value influences either

#### Scenario: A free committed row derives the zero vector

- **WHEN** the addressed id's committed row costs nothing
- **THEN** the derived vector is all zeros, the execution still appends the id, and the post-state proof passes with every resource unchanged

#### Scenario: An unsupported id is refused, never priced

- **WHEN** the expansion id is outside the committed schedule, or the player already owns it
- **THEN** the service answers a structured JSON error, the legacy dispatcher never runs, and the corpus save is unchanged — the legacy server's acceptance of both is recorded as the reason the service does not accept them

#### Scenario: An unevaluable requirement is refused, never invented

- **WHEN** the addressed row records a positive neighbor requirement or a positive inventory requirement
- **THEN** the service answers a structured conflict error and the corpus save is unchanged, because nothing the delivered stack can read evaluates either requirement

#### Scenario: The derivation is marked where it is recorded

- **WHEN** the derivation is recorded in the envelope module, the fixture README, the application documentation, or the structural report
- **THEN** the id-space indexing is marked derived, the gold naming is recorded as established by the committed client asset names, the refusal rules are marked derived, and the consequence that no id the corpus owns could have been bought under the requirements rule is stated rather than omitted

### Requirement: Expansion execution endpoint

Compatibility API v0 SHALL expose a loopback-only expand endpoint that accepts an
intent — save id and an expansion id — and never client-supplied amounts, resources,
times, prices, or resource deltas. The endpoint SHALL read the player's existing
owned-expansions list before executing, refuse an id outside the committed schedule
and an id already owned, derive the debit from the committed row, execute the
unchanged legacy command dispatcher in-process so the legacy resource application,
the list append, and the batch save persistence run exactly as the legacy code
performs them, persist only into the service corpus, and answer with the legacy
result plus an authoritative superset carrying the owned list before and after
execution, the derived debit, the committed schedule row used, and the current
resources. Every structurally unresolvable input — a non-object body, a missing,
invalid, or unknown save id, or a missing, non-integer, out-of-range, or already-owned
expansion id — SHALL fail closed with a structured JSON error and no mutation. After
execution the endpoint SHALL require that the owned list grew by exactly one entry
equal to the sent id, appended at the end with every existing entry unchanged and in
order, and that every stored resource changed by exactly the derived debit; any other
outcome SHALL fail closed with a structured error rather than report the legacy
success.

#### Scenario: Expand successfully

- **WHEN** a valid expand intent names a known save, an id with a purchasable committed row, and a balance that covers the derived debit
- **THEN** the unchanged legacy command path executes, the corpus save persists with exactly one appended id, the derived debit is applied, and the response carries both lists, the derived debit, the committed row, and the current resources

#### Scenario: An unsupported id fails closed

- **WHEN** the expansion id is an integer outside the committed schedule, or an id the player's list already contains
- **THEN** the service answers a structured JSON error with a non-2xx status, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: An unevaluable requirement or an insufficient balance fails closed

- **WHEN** the addressed row records a positive neighbor or inventory requirement, or the balance does not cover the derived debit
- **THEN** the service answers a structured conflict error, the legacy dispatcher never runs, and the corpus save is unchanged — the debit is server-derived, so a partial charge is refused rather than absorbed by the per-resource clamp

#### Scenario: A post-state that diverges fails closed

- **WHEN** execution completes but the list did not grow by exactly the sent id, or a resource did not change by exactly the derived debit
- **THEN** the service answers a structured error instead of the legacy success, and the corpus save is left as the legacy batch left it, with the failure reported rather than hidden

#### Scenario: Fail closed on unresolvable input

- **WHEN** the body is not a JSON object, the save id is missing, invalid, or unknown, or the expansion id is missing or not an integer
- **THEN** the service answers a structured JSON error with a non-2xx status, the corpus save is unchanged, and no list is rewritten and no resource moves

#### Scenario: Persist into the corpus only

- **WHEN** an expansion executes and the save persists
- **THEN** only the service corpus save changes — the session and bootstrap endpoints stay byte-identical for every save, and no working-tree save file is ever written

#### Scenario: Bind to loopback only

- **WHEN** the service starts with expansion execution available
- **THEN** it listens only on `127.0.0.1` at the documented port and only documented clients are told to use it

### Requirement: Expansion flow

The client SHALL provide an expansion flow over the typed GameApi expansion
operation: an expansion readout for a selected map showing the committed schedule,
the player's owned expansion ids, and the next purchasable entry with its derived
cost and affordability; and an `Expand` action on the selection-driven surface,
mutually exclusive with the delivered move, sell, store, upgrade, build, and collect
modes, opening a confirm that names the derived debit; and a confirm that sends
exactly one intent. The readout and the confirm SHALL use the same committed content
the service derives from, and the confirm's amounts SHALL be presented as derived
rather than authoritative. Cancelling SHALL send nothing and leave the town
byte-identical, and an id that is out of range, already owned, blocked by an
unevaluable requirement, or unaffordable SHALL be refused with an explicit reason and
no request. On success the flow SHALL apply only the authoritative response — the
owned list, the balances, and the readout taken from the response values rather than
from the client's own arithmetic — and on any failure it SHALL surface an explicit
error naming the failure with the list unchanged and no balance moved. The flow SHALL
NOT alter terrain, the grid, buildable cells, or the placement bounds.

#### Scenario: Expand the town

- **WHEN** the player selects the map, chooses the expand action on a purchasable id, and confirms
- **THEN** exactly one expansion intent is sent, and on success the owned list carries the authoritative appended id and the HUD balances take the response values

#### Scenario: Balances move only by the server's numbers

- **WHEN** the client derived a debit that differs from the response's
- **THEN** the response wins: the applied list and balances are the response's values, and the client's own arithmetic is discarded rather than added to them

#### Scenario: Nothing to offer, nothing sent

- **WHEN** the selected expansion id is out of range, already owned, blocked by a requirement the client cannot evaluate, or unaffordable
- **THEN** no expansion action is offered for it and any attempt is refused with an explicit reason, with no request sent and the town unchanged

#### Scenario: A failed request moves nothing

- **WHEN** the expansion request fails at transport or returns a structured error, including an id the service refuses and a post-state the service rejects
- **THEN** an explicit error names the failure, the owned list keeps its previous contents, and the HUD keeps its pre-request balances

### Requirement: The expansion land effect is a recorded gap

This change SHALL NOT invent terrain growth, grid enlargement, new buildable cells,
or any change to the placement bounds, because no committed source maps an
expansion id to land geometry; and the requirement gap SHALL be recorded as a known
evidence gap wherever the slice is described, naming the committed evidence that
establishes the vocabulary — an expansion is a purchasable tile, bought through a
popup, priced in gold and cash — and the committed scope statement that explains
why the tile-to-cell geometry cannot be derived from the preserved inspection.
Non-claims in the delivered artifacts SHALL state that no claim is made about any
area of the town becoming buildable, and that the delivered evidence establishes the
unlock ledger only.

#### Scenario: No land behavior is invented

- **WHEN** the change's implementation and evidence are reviewed
- **THEN** no terrain, grid, buildable-cell, or placement-bound change is present, and the gap is stated explicitly rather than left for a reader to discover

#### Scenario: The gap is recorded with its boundary

- **WHEN** the change's documentation is read
- **THEN** it records what the committed evidence establishes (the tile vocabulary, the popup, the two price components), what it cannot establish (the tile-to-cell geometry, and the reason the committed inspection's scope excludes it), and that closing the gap requires new evidence rather than a derivation

### Requirement: Expansion evidence, provenance, and claim limits

The change SHALL commit a windowed capture of a completed expansion together with a
deterministic structural report recording its inputs and digests, the intent, both
owned lists, the derived debit, the committed schedule row used, the request counts,
and explicit non-claims, and every artifact SHALL distinguish the parts of the
contract that are **established** from committed legacy source, executed-legacy
evidence, and committed asset evidence — that the branch appends the id and changes
nothing else, that the price is client-sent and applied verbatim under the documented
clamp, that the clamp is reachable, that the server accepts an out-of-range, a
duplicate, and a negative id, and that the expansion price's gold component is
named `gold` by the client's own committed asset — from the parts that are
**derived** and never observed from the Flash client: the id-space indexing, the
requirements refusal, the affordability refusal, and the debit's sign and shape. The
non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; the
claim is that a debit is derived from the committed schedule row the id names, never
that it is the price a coherent player pays; the corpus's own owned ids are recorded
as incoherent under the chosen schedule and **none of them could have been bought**
under the requirements rule, so the delivered end-to-end transaction uses a
zero-cost committed row; parity covers one recorded transaction against the
fresh-player corpus; no pixel-parity oracle against the legacy client exists; and no
land, grid, or buildable-cell behavior is claimed. The report SHALL be byte-identical
across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the town with the expansion readout and the structural report are committed under `apps/client-godot/evidence/building-expand/`, and the report carries the established-versus-derived split and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation

All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the
existing locked dependencies and no new packages; legacy sources, configs, saves,
villages, committed fixtures, conversion packages, registry manifests, and the
committed M4, M6, and every delivered gameplay slice's evidence SHALL remain
byte-identical across the change (SHA-256 guards plus the hash manifest); expansion
execution SHALL never write a working-tree save; and both verification batteries
SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** fixture capture, parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the new hermetic expand suite and the live expand phase that proves a disposable corpus save mutates

### Requirement: Documented commands and assessment record

`AGENTS.md` and the application READMEs SHALL document the exact commands actually
executed — expand fixture capture, the expand tests, both batteries — with their
purposes, the loopback port, the evidence paths, the established-versus-derived
provenance of every pricing and refusal rule, the land-shape gap, and the limits of
the expansion claim; the committed investigation record SHALL be updated with the
four questions as resolved, the two new pieces of committed evidence, and the two
additional probe results; and the roadmap Project Status ledger SHALL record the M7
progress this change delivers with evidence pointers and remaining gaps, including
the ledger bookkeeping correction for the archived `building-collect` change.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record which parts of the expansion contract are established evidence and which are derived

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers, which M7 deliver lines remain, corrects the `building-collect` archive bookkeeping, and records the land-shape evidence gap as bounding visual land growth rather than blocking this slice