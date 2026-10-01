## Purpose

Expose the committed collection prize as a typed, read-only, content-derived projection —
including the six collections that grant a unit — with the acquisition-path inventory separating
the one content-derived route from the unvalidated client-sent ones, the two recorded authority
gaps, and the refusals of unit income, cap semantics, and any experience award.

## Requirements

### Requirement: A collection prize is derived from committed content

The client SHALL resolve a collection id to its **committed** prize bag, and SHALL classify each
granted id by resolving it against the content package, reporting a **unit** prize distinctly from
a **building** prize. The projection SHALL be read-only and SHALL report the committed prize
values verbatim. A collection id outside the committed table SHALL be reported as unresolvable with
its recorded value intact, never dropped and never substituted.

#### Scenario: A unit-granting collection resolves

- **WHEN** a collection id naming a unit-granting collection is resolved
- **THEN** the projection reports the committed prize bag verbatim and classifies the granted id as a unit, with its committed name

#### Scenario: A building prize is classified as a building

- **WHEN** a collection id naming a building-granting collection is resolved
- **THEN** the granted id is classified as a building and reported distinctly from a unit prize

#### Scenario: An unresolvable collection is reported, not substituted

- **WHEN** a collection id outside the committed table is resolved
- **THEN** the projection reports it as unresolvable with its recorded value intact, and substitutes nothing

#### Scenario: Every committed collection is covered

- **WHEN** the committed table is inspected
- **THEN** every entry is resolvable and classified, and the unit-granting count is reported exactly

### Requirement: The index is one-based, and the id-0/id-1 alias is reported

The client SHALL resolve a collection id through a **one-based** index with the legacy clamp, and
SHALL report that clamp's effect explicitly: **collection id 0 and collection id 1 resolve to the
same prize**. The one-based interpretation SHALL be recorded as derived-provisional with the
rejected zero-based alternative retained, and the client SHALL NOT report id 0 as a distinct
collection from id 1.

#### Scenario: The one-based index is applied

- **WHEN** a collection id is resolved
- **THEN** the committed row is selected through the one-based index with the legacy clamp, and the interpretation is recorded as derived-provisional

#### Scenario: The alias is reported rather than hidden

- **WHEN** ids 0 and 1 are both resolved
- **THEN** they yield the same committed prize, and the projection reports that alias rather than presenting them as distinct

### Requirement: One route is content-derived and the rest are client-supplied

The client SHALL record an inventory of the acquisition and row-entry routes, classifying each one
as **content-derived** or **client-supplied**, and SHALL record that the committed collection
completion route is the **only** content-derived one. The recorded classification SHALL be
consistent with the already-recorded finding that the offer-pack and stored-item-cash routes accept
client-supplied item lists, and this capability SHALL implement **no** client-supplied route.

#### Scenario: Each route is classified

- **WHEN** the inventory is inspected
- **THEN** each recorded route carries an explicit content-derived or client-supplied classification, and the collection completion route is the sole content-derived entry

#### Scenario: No client-supplied route is implemented

- **WHEN** this change's diff is inspected for acquisition
- **THEN** no client-supplied item id, package id, or item list is accepted, enforced, or trusted, and no request is issued for any recorded client-supplied route

#### Scenario: The earlier finding is completed, not contradicted

- **WHEN** the recorded classification is read alongside the previously recorded acquisition finding
- **THEN** they are consistent: the client-supplied routes remain unusable, and the content-derived route is named as the one that grants from committed content

### Requirement: Collection eligibility is not checked, and that gap is recorded

The client SHALL record, and SHALL NOT paper over, that the legacy service verifies **nothing**
about whether a collection was earned — so a caller may name any committed collection — and SHALL
implement **no** eligibility check, because none exists to reproduce. The projection SHALL report
the recorded gap rather than presenting the grant as conditional on anything.

#### Scenario: No eligibility is invented

- **WHEN** a collection id is resolved
- **THEN** no check is performed on the caller's collection state, and the recorded gap that the legacy server checks nothing is stated

#### Scenario: The gap is named, not fixed

- **WHEN** this capability's documentation is read
- **THEN** it states that a caller may name any committed collection, and that no eligibility rule is implemented because the legacy service has none

### Requirement: No unit income, no cap semantics, and no experience award

The client SHALL NOT derive unit income from a collection, SHALL NOT interpret a unit collection
cap, and SHALL NOT award experience. No committed unit carries a positive collect amount and no
collect field is read by the legacy service, so there is nothing to derive; a unit collection cap
is uniformly absent, so no threshold exists to interpret; and the experience field is never read
with its only writer taking a client-sent amount, which an earlier capability already refuses. The
client MAY report a committed collect-related value as **content only** and SHALL state that no
payout, cap, or experience is derived from it.

#### Scenario: No unit income is derived

- **WHEN** a unit's committed collect fields are inspected
- **THEN** no income, payout, or collection reward is computed from them, and the recorded fact that no unit carries a positive collect amount is stated

#### Scenario: No cap is invented

- **WHEN** a unit's committed cap value is inspected
- **THEN** no maximum, limit, or threshold is interpreted from it, and the recorded absence is stated as an absence rather than read as permission to set one

#### Scenario: No experience is awarded

- **WHEN** a collection resolves or a unit's experience field is inspected
- **THEN** no experience is awarded, granted, or computed, and the earlier capability's refusal of a client-sent experience amount still stands

### Requirement: The completion intent carries only an identifier

A collection completion SHALL be sent as a **guarded intent** carrying **only** a player identifier
and a collection id. A client SHALL NOT send a prize, an item id, or a quantity, and the service
SHALL ignore any such key and derive the grant entirely from committed content. The post-execution
proof SHALL assert that the granted id and quantity match the **committed** prize bag exactly and
that the recorded collection ledger grew by exactly one appended id.

#### Scenario: The intent is an identifier and nothing else

- **WHEN** a completion is sent
- **THEN** the request carries only the player identifier and the collection id, and no prize, item id, or quantity is sent

#### Scenario: A client-supplied prize is ignored

- **WHEN** a completion request also carries a prize, item id, or quantity
- **THEN** the service ignores those keys and grants exactly what the committed collection grants, and the proof compares against the committed bag rather than the request

#### Scenario: The proof is content-derived

- **WHEN** a completion is executed and proven
- **THEN** the granted id and quantity equal the committed prize bag exactly, and the collection ledger grew by exactly one appended id

### Requirement: An executed-legacy fixture for the committed grant

The change SHALL capture an executed-legacy fixture for a collection completion that grants a
committed **unit** prize into the corpus's empty store, in a disposable copy of the legacy server,
and SHALL record in the fixture's manifest that the grant is **content-derived** and that the
committed corpus remains byte-identical outside the disposable copy. The fixture SHALL require no
fabricated player state, and SHALL **not** chain the stored-item placement step, which is a
separate follow-up.

#### Scenario: The grant is captured

- **WHEN** the evidence step runs
- **THEN** a fixture is committed under `tests/fixtures/godot-unit-collection/` recording the completion with its before and after states, against a collection whose committed prize is a unit, and the working-tree corpus and the twelve delivered fixture directories are unchanged

#### Scenario: The manifest records the derivation and the stopped scope

- **WHEN** the fixture's manifest is read
- **THEN** it states that the granted id and quantity were derived from the committed collection table, and that the stored-item placement step was not chained because it is a separate follow-up

#### Scenario: No fabricated state is written

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a unit row, and the committed corpus stays byte-identical

### Requirement: Unit-collection evidence and claim limits

The change SHALL commit a deterministic `unit-collection-report-v1` report recording the ten
committed collections with their prize classification, the index resolution and its alias, the
acquisition inventory with each route's classification, the two authority gaps, the collect-field
zero-consumer findings, the corpus measurement, the established-versus-derived split, and the
explicit non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash, Ruffle,
ActionScript, or browser executed; **no unit income, collection payout, cap semantics, or experience
award is implemented**; **no collection eligibility is checked**, and a caller may name any
committed collection; **ids 0 and 1 alias**; **no client-supplied acquisition route is implemented**;
**the stored-item placement step is not delivered**, so the fixture evidences the grant into storage
and not a unit placed on the map; **no unit is placed or garrisoned**; and no windowed capture is
claimed.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-collection/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture of a placed unit is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that the fixture evidences a committed grant into storage and not a unit placed on the map
