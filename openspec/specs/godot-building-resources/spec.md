# godot-building-resources

## Purpose

Let a player read every one of their resources correctly: a canonical projection in which each resource is named as the server names it, the primary currency is visible for the first time, the real eighth resource is exposed, and no state-mutating surface changes.

## Requirements

### Requirement: Canonical resource projection
The client SHALL derive every displayed resource from a single canonical projection
that names each resource exactly as the legacy server names it, mapping each name to
exactly one save location: `xp` to the map's experience counter, `gold` to the map's
primary currency, `wood`, `oil`, and `steel` to their map locations, `cash` to the
player info's cash, and `mana` to the private state's mana. The projection SHALL NOT
name a resource with a field the server never produces, SHALL NOT display the same
resource under two names, and SHALL NOT invent a resource the save does not contain.
The experience counter SHALL be grouped with the player's summary rather than with the
spendable resources, because nothing spends it.

#### Scenario: Every row resolves to one save location

- **WHEN** the canonical projection is inspected
- **THEN** each resource row names a field the server produces, maps to exactly one save location, and appears exactly once, with the experience counter in the summary group

#### Scenario: The primary currency is named as the server names it

- **WHEN** the projection names the primary currency
- **THEN** it names `gold`, the field the legacy resource application writes and the field the corpus stores, and no row is keyed by any other name for it

#### Scenario: An unproduced field is never displayed under an invented name

- **WHEN** a display row would require a field the server does not produce
- **THEN** the row is not created under that name, and the projection records no such row

### Requirement: Resource readout completeness
Every row the resource readout renders SHALL display the resource's real stored value.
The readout SHALL NOT render an absent-field indicator for a resource the server does
produce, and every resource the legacy resource application writes SHALL be readable
by value. A resource that is genuinely absent from a payload SHALL still render the
explicit absent-field indicator rather than a guess or a zero.

#### Scenario: Every server-written resource is readable by value

- **WHEN** a player views their resource readout against a payload carrying the resources the service produces
- **THEN** each of the seven resources the legacy resource application writes renders its real stored value and no row renders an absent-field indicator

#### Scenario: A genuinely absent resource still fails closed

- **WHEN** a payload omits a resource the projection expects
- **THEN** that row renders the explicit absent-field indicator, no value is guessed or defaulted to zero, and every other row is unaffected

#### Scenario: A missing row cannot be reintroduced by a test payload

- **WHEN** the readout's tests build a payload
- **THEN** the payload uses the field names the service actually produces, and no test supplies a resource field under a name the service does not produce

### Requirement: The eighth resource is displayed with its gap recorded
The client SHALL display the stored energy value the player payload carries, under the
name the save uses for it, and SHALL source it from that location. The service SHALL NOT
be changed to provide it: the stored value already reaches the client through the
delivered payload path, so no accessor, no field, and no route is added, and the shared
resource accessor the state-mutating endpoints' post-execution proofs compare SHALL NOT
be widened. The legacy resource mutation vector SHALL NOT gain a slot for it, because no
delivered path mutates it and the vector is the legacy wire format. Because no committed
source records how the stored energy value changes over time, neither the service nor the
client SHALL invent such a rule, and the absence SHALL be recorded as an explicit gap
wherever the resource is described.

#### Scenario: The stored energy value is displayed by value

- **WHEN** a player views their resource readout against the delivered payload
- **THEN** the stored energy value renders by value under the save's own name for it, sourced from that save location, and not as an absent-field indicator

#### Scenario: No service change was needed and none was made

- **WHEN** this change's diff is inspected against the Compatibility API
- **THEN** no accessor, no response field, no route, and no error-table row was added or changed, and the shared resource accessor still returns exactly the seven keys the nine delivered post-execution proofs compare

#### Scenario: No delivered path can change it, and nothing pretends otherwise

- **WHEN** any state-mutating action executes
- **THEN** the stored energy value is unchanged, and no proof, response, or vector claims it is part of the mutated resource set

#### Scenario: The regeneration rule is a recorded gap

- **WHEN** the change's documentation or structural report is read
- **THEN** it records that the legacy resource application never writes the stored energy value, that no legacy branch touches it, that no committed source records a regeneration interval, and that no rule is claimed for how it changes

### Requirement: No state-mutating surface changes
This change SHALL NOT add, remove, or rename a field in any state-mutating response,
SHALL NOT add an endpoint, and SHALL NOT change any balance. None of the delivered
gameplay endpoints' contracts, error tables, or post-execution proofs SHALL change,
and their committed executed-legacy parity fixtures SHALL remain valid.

#### Scenario: The delivered endpoints are untouched

- **WHEN** this change is reviewed against the delivered surfaces
- **THEN** no state-mutating route, response shape, error code, or proof is modified, and the executed-legacy parity fixtures for all of them still pass unchanged

#### Scenario: The diff is confined to the projection

- **WHEN** the change's diff is inspected
- **THEN** it touches the client's readout and projection, one additive read-only accessor and its exposure path, tests, evidence, and documentation, and no legacy source, config, village, save, or committed fixture

### Requirement: Resource evidence, provenance, and claim limits
The change SHALL commit a windowed capture of the resource readout with every row
sourced together with a deterministic structural report recording the canonical
projection table — each row's canonical name, its save location, and its group — the
observed stored values, the input digests, the request counts, and explicit
non-claims. The report's provenance section SHALL record as **established** that the
legacy resource application writes exactly the seven named slots at the recorded
locations, that the primary currency's field is `gold`, that the stored energy value
exists in the save and in the committed constants, and that the legacy resource
application never writes it; and it SHALL record that **no rule for how the energy
value changes is claimed**, since none is committed. The non-claims SHALL state: no
Flash, Ruffle, ActionScript, or browser executed; the readout claims to display what
the save stores, never a value the legacy client would have displayed; no pixel-parity
oracle against the legacy client exists; the readout's labels and layout are the
delivered provisional convention; the market and trade counters and item cost mapping
are out of scope; and the committed capture runs the fake GameApi. The report SHALL be
byte-identical across reruns.

#### Scenario: Commit the capture and report

- **WHEN** the evidence step runs in an interactive session
- **THEN** a windowed capture of the resource readout and the structural report are committed under `apps/client-godot/evidence/building-resources/`, and the report carries the projection table, the observed values, the provenance split, and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

### Requirement: Containment and preservation
All execution SHALL stay on loopback under the pinned CPython 3.9.13 with the
existing locked dependencies and no new packages; legacy sources, configs, saves,
villages, committed fixtures, conversion packages, registry manifests, and the
committed M4, M6, and every delivered gameplay slice's evidence — other than the
regenerated per-run battery report — SHALL remain byte-identical across the change
(SHA-256 guards plus the hash manifest); the bootstrap endpoint SHALL never write a
working-tree save; and both verification batteries SHALL exit 0 in the final state.

#### Scenario: Verify without side effects

- **WHEN** the parity tests, both batteries, and the preservation guards have all run
- **THEN** guard hashes over legacy sources, saves, both conversion packages, the three registry manifests, and the committed M4/M6 and delivered-slice evidence are identical before and after, the hash manifest verifies, and only disposable corpora were mutated

#### Scenario: Both batteries green

- **WHEN** the first-render verification and the compatibility-boot verification run in the final state
- **THEN** both exit 0 with their documented markers, including the expanded resource-projection coverage

### Requirement: Documented commands and assessment record
`AGENTS.md` and the application READMEs SHALL document the exact commands actually
executed — the resource tests and both batteries — with their purposes, the evidence
paths, the established provenance of the projection, the energy gap, and the limits of
the readout claim; the committed investigation record SHALL be updated with the
resolutions; and the roadmap Project Status ledger SHALL record the M7 progress this
change delivers with evidence pointers and remaining gaps.

#### Scenario: Record the executed commands

- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands with their purposes and constraints, matching what was actually run, and record that the projection names resources as the server names them and that the energy regeneration rule is a recorded gap

#### Scenario: Record the milestone progress

- **WHEN** this change concludes
- **THEN** the ledger states which M7 deliver line this change delivers, which M7 deliver lines remain, and points to the committed evidence
