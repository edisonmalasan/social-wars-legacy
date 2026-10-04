# Spec Delta

## ADDED Requirements

### Requirement: A combat resolution derives the destroyed set server-side and refuses a client-dictated destruction count

The compatibility service SHALL expose a combat-resolution operation whose
request carries **intent only** and never a destruction count. The service SHALL
derive the affected unit identity, the eligible rows, and the number of rows
destroyed **from its own state**, and SHALL NOT accept a client-supplied
destruction count, a client-computed `lost` value, or the two operands that
subtract to one. The legacy branch derives its destruction count as
`max(0, sent - survived)` on values the client supplies, and the service SHALL
record that the difference is **refused, not reproduced** — the divergence this
creates against the legacy server SHALL be recorded as a **divergence**, never as
parity. A successful resolution SHALL return a typed response carrying the
server-derived identity and the resulting counts, and SHALL NOT echo any
client-supplied value it ignored.

#### Scenario: The client sends intent only

- **WHEN** a combat resolution is requested
- **THEN** the request carries no destruction count and no subtraction operands, and the service derives the unit identity and the number of destroyed rows from its own recorded state

#### Scenario: A client-dictated destruction count is refused

- **WHEN** a combat-resolution request carries a destruction count or a pair of values intended to subtract to one
- **THEN** the operation is refused with a named code, an empty payload, and no change to the recorded state

#### Scenario: The difference from the legacy server is a divergence, not parity

- **WHEN** the recorded results are compared against the executed legacy behaviour
- **THEN** the comparison is recorded as a divergence in which the legacy server destroyed rows from a client-dictated count and the modern operation destroyed none, and it is not reported as matching parity

### Requirement: Every refusal resolves before any destruction, so a refused request leaves the state byte-identical

The operation SHALL complete **all** validation before any row is removed and
before the dead-hero ledger is written, so that a refused request provably leaves
the recorded state byte-identical. The legacy branch's two unguarded absent-value
dereferences sit on **opposite sides** of its write loop: omitting the loss list
raises **before** the state is touched, while omitting the victim record raises
**after** rows are already removed and the ledger already incremented. The
service SHALL place its own checks strictly before the write step, and the
post-execution proof for a refusal SHALL compare the **whole** recorded document
rather than a selected subset of it.

#### Scenario: A refused request changes nothing

- **WHEN** a combat-resolution request is refused for any reason
- **THEN** no placed row is removed, no ledger entry is written, and the recorded state is byte-identical to its pre-request form

#### Scenario: The ordering is a property of the delivered flow, not of prose

- **WHEN** the delivered combat flow is inspected
- **THEN** every validation precedes the destruction step in the delivered code, and the ordering is asserted by a guard rather than stated only in a claim

#### Scenario: An empty loss list is a no-op rather than a refusal

- **WHEN** a combat resolution carries an empty loss list
- **THEN** the operation succeeds, removes nothing, and records no ledger change, matching the executed legacy behaviour for that shape

### Requirement: The request's read-and-discarded fields are recorded, and no combat outcome is derived from any of them

The capability SHALL record the combat request's full field inventory, which is
**eleven** keys read from the client payload, and SHALL record that **seven** of
them reach nothing at all — the victim's unit list, the victim's resources, the
attacker record, the attacker's won resources, honour, duration, and the town-hall
gold — while the win flag and the victim's name reach only printed output. The
recorded inventory SHALL be **re-derived on every verification run** from the
preserved source, so a legacy edit fails the guard instead of silently
contradicting it, and the count of discarded keys and the identity of each
discarded key SHALL both be asserted. The client SHALL derive **no** combat
outcome from any field: no damage, no attack result, no defence application, no
hit chance, and no life or interval arithmetic, because the committed fields that
would express those rules have **zero** legacy consumers.

#### Scenario: The discarded fields are recorded and re-derived

- **WHEN** the combat request's field inventory is produced
- **THEN** all eleven keys are listed, the seven that reach nothing are named individually, and the inventory is re-measured from the preserved source on every run rather than transcribed

#### Scenario: No combat outcome is derived from a recorded field

- **WHEN** the committed combat fields are inspected
- **THEN** their values may be reported as content with their zero-consumer status, and no damage, outcome, defence, hit, or life computation is derived from any of them

#### Scenario: No syringe cost is charged

- **WHEN** a combat-adjacent revival is recorded
- **THEN** no stored resource moves and no cost is charged, because the committed syringe field is carried by every unit and every building and is read by no legacy code

### Requirement: A kill removes one addressed row and never touches the dead-hero ledger

The operation SHALL expose a row-removal intent that deletes **only** the
addressed row and SHALL record that this command **never** touches the dead-hero
ledger, which is stronger than observing one unchanged ledger. It SHALL refuse an
address that resolves to no placed row, and SHALL record that the legacy command
returns without any change in that case. It SHALL **not** record a ledger
increment for this path, because the executed legacy branch has none. The
separate selling path that *does* reach the ledger behind a combat-reason guard
belongs to another capability and SHALL be referenced rather than re-delivered.

#### Scenario: A kill removes the row and only the row

- **WHEN** a row-removal intent addresses a placed row
- **THEN** that row is removed, every other placed row is unchanged, and no dead-hero ledger entry is created or incremented

#### Scenario: The ledger's non-participation is asserted, not observed once

- **WHEN** the row-removal path is verified
- **THEN** the dead-hero ledger is asserted to be untouched by this path as a property of the delivered behaviour, rather than inferred from one request that happened not to change it

#### Scenario: An unaddressable row is refused

- **WHEN** a row-removal intent addresses a key that resolves to no placed row
- **THEN** the operation is refused with a named code, an empty payload, and no change to the recorded state

### Requirement: The item-keyed kill is delivered as a proven no-op

The capability SHALL deliver the item-keyed kill as a command whose recorded
contract is that it **mutates nothing**: no placed row, no ledger, and no stored
resource changes, because the preserved branch contains **no write statement at
all**. This SHALL be delivered rather than refused, because an empty branch is a
behaviour the preserved server has and a client can be verified against. It SHALL
be reported as an **empty command** with its recorded no-write status, and no
replacement meaning SHALL be invented for it.

#### Scenario: Nothing is written

- **WHEN** the item-keyed kill is invoked
- **THEN** no placed row, no ledger entry, and no stored resource changes, and the whole recorded document is byte-identical to its pre-request form

#### Scenario: Its emptiness is recorded as a property of the branch

- **WHEN** the item-keyed kill's contract is inspected
- **THEN** it states that the preserved branch contains no write statement, which is stronger than any single observed request, and that the command's intent is therefore unknown rather than assumed

### Requirement: An executed-legacy fixture is captured against a committed village document, and its coverage is measured

The change SHALL capture an executed-legacy behaviour fixture for the combat
resolution path against a **committed village document** that places committed
unit rows and carries a dead-hero ledger, and SHALL NOT manufacture any row,
save, or corpus to make one capturable. The capture SHALL record the exact
destruction count the legacy server applied, the ledger value it wrote, and the
count of committed unit rows the corpus holds. The recorded coverage SHALL state
which committed documents were used and SHALL record that **five** committed
village documents carry a non-empty ledger and **441** committed unit rows exist
across the repository, superseding any earlier statement that the corpus places
no unit row. Where the legacy server's outcome differs from this capability's
operation, the fixture SHALL record the difference as a **divergence** and SHALL
NOT record parity.

#### Scenario: The fixture is captured against a real committed row

- **WHEN** the capture runs
- **THEN** the request is executed against a committed village document holding committed unit rows, and the recorded result carries the legacy server's exact row count change and ledger write

#### Scenario: The coverage is measured, not asserted

- **WHEN** the recorded coverage is read
- **THEN** it states the number of committed unit rows and the number of committed documents carrying a non-empty ledger, measured across every committed save document rather than against one

#### Scenario: No corpus is manufactured

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a row the committed corpus lacks, and the committed corpus and the delivered fixture directories stay byte-identical

### Requirement: Combat-action evidence and claim limits

The change SHALL commit a deterministic `combat-actions-report-v1` report
recording the request's field inventory with each key's fate, the validation
ordering, the server-derived destruction set, the row-removal and item-keyed
kill contracts, the captured legacy result, the recorded divergence, the
corpus measurement, the established-versus-derived split, and the explicit
non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash,
Ruffle, ActionScript, or browser executed; **no client-dictated destruction count
is reproduced in either direction**; **no damage, health, defence, hit chance, or
life arithmetic is delivered or claimed**; **no mission is dispatched, resolved,
or completed**, and the mission vocabulary remains owned elsewhere; **no honour or
reward is paid and no stored resource moves**; **no syringe cost is charged**;
**no occupancy, bounds, type, or terrain validation is added**, that being a
server-authority gap; **the team asymmetry between the row-removal helper and the
ledger helper is recorded as a code fact and not exercised**, since no committed
unit row is on a team other than one; and **no windowed capture and no pixel-parity
oracle are claimed**, because nothing is rendered.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/combat-actions/` carrying every required field and non-claim

#### Scenario: The non-claims are structural where they can be

- **WHEN** the delivered code is inspected for the recorded non-claims
- **THEN** helpers that would implement a damage, duration, honour, reward, or mission-completion rule are absent, and the absence is asserted by a guard proven to fail when such a helper is injected