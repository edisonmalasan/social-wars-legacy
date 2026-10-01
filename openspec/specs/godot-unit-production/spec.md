## Purpose

State the **explicit refusal** of a unit-production mechanism, with the evidence that makes it
auditable: a readiness projection that reports a queue's presence and start instant while
recording that the legacy server cannot say whether it is ready, the five legacy branches that
can place a row on the map with each item id's source named, and the `training_time` and
`add_xp_unit` refusals — so no later line can compute a client-side readiness and call it
production.

## Requirements

### Requirement: Production is refused, with the evidence recorded

The client SHALL NOT implement a unit-production mechanism. It SHALL create **no** unit, run **no**
completion, offer **no** readiness test, and provide **no** production endpoint. This is a
**recorded property of the legacy contract, not a missing feature**: the legacy server has no
completion command, never evaluates a queue's elapsed time, and cannot derive a unit from any
committed production rule. The capability SHALL record that absence as a requirement so a later
line inherits a named refusal instead of meeting a production-shaped field with no recorded
reason to decline it.

#### Scenario: No production mechanism exists

- **WHEN** this capability's client surface is inspected for production
- **THEN** it creates no unit, runs no completion, and exposes no readiness test, and its documentation states that the legacy server has no mechanism to reproduce

#### Scenario: The absence is stated, not implied

- **WHEN** this capability's specification is read
- **THEN** it states that no completion command exists, that no elapsed time is evaluated, and that no committed production rule derives a unit, naming each absence rather than leaving it to inference

#### Scenario: A later line inherits the refusal

- **WHEN** a later line considers adding a completion or readiness rule
- **THEN** it finds this capability's requirement already stating that the legacy contract has neither, and must bring its own evidence rather than inferring one from the committed duration field

### Requirement: The row-entry inventory names every item id's source

The client SHALL record the legacy branches that can place a row on the map, and SHALL record
for each one **where its item id comes from**, classifying it as **client-supplied**,
**already-existing**, or **derived from committed content**. The inventory SHALL cover every
branch in the committed legacy source that places a row, and it SHALL record that **no** such
branch derives an item id from a completed queue, from a duration, or from committed production
content. The recorded set SHALL be closed over the committed legacy source, and any branch that
places a row outside it SHALL be reported as an unrecorded gap rather than ignored.

#### Scenario: Every row-entry branch is inventoried

- **WHEN** the inventory is inspected
- **THEN** each legacy branch that places a row is named with its item id's source classified, and the count matches the committed source

#### Scenario: Client-supplied ids are named as such

- **WHEN** a branch's item id comes from a client argument
- **THEN** the inventory records it as client-supplied, so it is never treated as a trusted derivation

#### Scenario: No path derives a unit from a queue

- **WHEN** the inventory is compared against the queue contract
- **THEN** no inventoried path derives an item id from a completed queue, from a duration, or from committed production content, and the comparison is recorded

### Requirement: No duration is derived from the committed training time

The client SHALL report the committed training-time field as **content only** and SHALL NOT
derive a production duration, a remaining time, or a progress ratio from it. The recorded fact
SHALL state that the field has **no legacy consumer** — no committed branch reads it — while
reporting its committed distribution as reference. A committed field with no committed consumer
SHALL be recorded and never invented into a rule, and the client SHALL add no duration semantics
for any related field either.

#### Scenario: The committed duration is reported, never used

- **WHEN** a definition's committed training time is inspected
- **THEN** its value may be reported as content, and no production time, remaining time, or progress ratio is computed from it

#### Scenario: The zero-consumer fact is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that no committed branch reads the field, report its committed distribution, and name the earlier fields in this project that share the same zero-consumer property

#### Scenario: No related duration semantics are added

- **WHEN** any sibling duration field is inspected
- **THEN** no production or timing semantics are derived from it either, and the unrelated field's own recorded path is not treated as a general duration

### Requirement: No experience is awarded from a client amount

The client SHALL NOT award unit experience. It MAY read and report a placed row's recorded
experience value as **content**, and SHALL record that the only legacy command writing it takes
the amount from the client, with an optional client-supplied level used only in a printed
message. The client SHALL NOT compute, grant, or display an experience award arising from
production, and SHALL record the committed corpus's absence of the field on its placed rows.

#### Scenario: A recorded experience value is read, not awarded

- **WHEN** a placed row carries a recorded experience value
- **THEN** the value is reported as content, and no experience is awarded, granted, or computed from it

#### Scenario: The client-supplied amount is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that the only legacy command writing the field takes its amount from a client argument and uses an optional client-supplied level only in a print

#### Scenario: No production experience is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no experience is awarded on production, and record that the committed corpus carries the field on none of its placed rows

### Requirement: No server operation is exposed for production

The client SHALL NOT expose or require a compatibility API operation for production: no route,
no request, and no client intent to create, complete, or award a unit. The compatibility test
suite SHALL remain green **unchanged**. Any client-supplied acquisition key — an item id, a
package id, or an item list — SHALL be recorded as client-supplied and SHALL NOT be treated as
authorising, and the content it might otherwise be validated against is named as belonging to a
later capability. **This finding is completed, not amended**, by the `godot-unit-collection`
capability: the committed collection completion route derives its grant from the committed
collection table and is the **only** content-derived acquisition path, so no committed unit is
obtainable through the client-supplied routes named here — but a unit **is** obtainable
through that one content-derived route, and it is the sole exception.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No client intent is sent

- **WHEN** the client has nothing to produce
- **THEN** it issues no request, and no intent exists to authorise

#### Scenario: Client-supplied acquisition keys are not treated as authority

- **WHEN** an item id, package id, or item list originates from a client argument
- **THEN** it is recorded as client-supplied, and the committed table it might otherwise be validated against is named as a later capability's work rather than enforced or trusted here

#### Scenario: The acquisition finding names the one content-derived route
- **WHEN** this requirement's acquisition finding is read
- **THEN** it names the client-supplied routes as unusable **and** points to the
  `godot-unit-collection` capability for the single content-derived route, so the finding is not
  read as "no committed unit is obtainable anywhere"

### Requirement: Unit-production evidence and claim limits

The change SHALL commit a deterministic `unit-production-report-v1` report recording the
row-entry inventory with each item id's source and classification, the committed training-time
distribution with its zero-consumer statement, the recorded experience-award contract, the
acquisition-route findings, the corpus measurement, the established-versus-derived split, and
the explicit non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash,
Ruffle, ActionScript, or browser executed; **no production mechanism, completion, or readiness
is implemented**; **no unit is created, trained, or placed**; **no duration is derived from the
committed training time**; **no experience is awarded**; **no acquisition is implemented or
claimed**, and the committed acquisition tables are read by no legacy **command branch**, so no
acquisition is derived from either; **no executed-legacy
fixture was captured, because no production behaviour exists to capture** rather than because
the corpus lacked state; death and resurrection are unreachable and unimplemented; and no
windowed capture is claimed.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-production/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture is claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that neither a windowed capture nor an executed-legacy fixture is claimed, and distinguishes "no mechanism exists" from "the corpus could not exercise it"
