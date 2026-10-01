## Purpose

Give the Godot client a typed, read-only projection of a production queue on a placed
row, carrying the three committed keys the legacy contract actually uses, with the
recorded absence of any server-side elapsed-time evaluation or completion stated as a
requirement, and with an executed-legacy fixture for the push/pop pair against a real
placed training producer.

## Requirements

### Requirement: A queue is a count, a start instant, and an optional queued unit id

The client SHALL project a production queue from a placed row's attribute bag as a typed,
read-only value carrying the three committed keys: the queue **count** (`nu`), the queue
**start instant** (`ts`), and the **optional queued unit id** (`ui`). It SHALL report
whether a queue is present, SHALL report each key's committed value verbatim, and SHALL
record the established **teardown rule** that a decrement to zero removes all three keys
together. An absent queue SHALL be reported as absent, never as a count of zero with an
instant of zero.

#### Scenario: The three keys are reported verbatim

- **WHEN** a row carrying `nu`, `ts`, and `ui` is projected
- **THEN** the projection reports the committed count, the committed start instant, and the committed queued unit id verbatim, with no scaling, rounding, or defaulting

#### Scenario: An absent queue is absent, not zero

- **WHEN** a row's attribute bag carries no queue keys
- **THEN** the projection reports no queue, and never a count of zero paired with a zero instant

#### Scenario: The teardown rule is recorded

- **WHEN** the projection reports a queue
- **THEN** it records that decrementing to zero removes the count, the start instant, and the queued unit id together

### Requirement: No elapsed-time evaluation and no completion

The client SHALL NOT compute whether a queue is complete, how much time remains, or any
progress ratio, and this capability SHALL introduce **no** completion of a queue and **no**
materialisation of a unit from one. This is a **recorded property of the legacy contract,
not a missing feature**: the legacy server never reads a queue's start instant to evaluate
elapsed time, and no legacy command completes a queue or creates a unit from it. The
`godot-unit-production` capability makes that absence **auditable** by recording every
legacy branch that can place a row on the map with the source of its item id named, and
by showing that **no** such branch derives an item id from a completed queue, from a
duration, or from committed production content — four of the five take the id straight
from the client and the fifth moves a row that already existed. A future
line MAY introduce completion only as its own deliverable, with its own evidence.

#### Scenario: No readiness is computed

- **WHEN** a queue is projected
- **THEN** the projection offers no completion test, no remaining time, and no progress ratio, because the legacy server has no such rule to reproduce

#### Scenario: The absence is stated, not implied

- **WHEN** this capability's specification is read
- **THEN** it states that the legacy server neither evaluates elapsed time nor completes a queue, and names that absence as a recorded contract rather than a gap to be filled here

#### Scenario: No unit is created

- **WHEN** this capability's diff is inspected for unit creation
- **THEN** no command, path, or projection creates, trains, spawns, or places a unit from a queue

#### Scenario: The absence is auditable, not only asserted
- **WHEN** the absence of any queue-derived unit creation is examined
- **THEN** the `godot-unit-production` inventory names every legacy branch that can place a row with its item id's source, and no inventoried branch derives an id from a completed queue, a duration, or committed production content, so the absence rests on the recorded entry paths rather than on a search that found no completion command

#### Scenario: The row instant is client-writable, which is why readiness stays refused

- **WHEN** this requirement's refusal of elapsed-time evaluation is read
- **THEN** it records that a legacy command shifts every row's recorded instant **and** its queue start instant backwards by a **client-supplied** number of seconds, so the instant is **client-writable**, and a readiness rule derived from it would trust a value the client can rewrite — the concrete reason this is a refusal rather than an omission

#### Scenario: The instant is reported as an opaque value

- **WHEN** a row's instant is projected
- **THEN** it is treated as an opaque recorded value with no elapsed, remaining, or readiness computation, and the `godot-unit-movement` capability records the same fact for the placement view
### Requirement: The three queue commands and their recorded lack of validation

The client SHALL record the three legacy queue commands' exact effects — a push that
increments the count and stamps the start instant, an atom-fusion push that additionally
records the queued unit id, and a pop that decrements or tears the queue down — together
with the established fact that each takes **only a map index** (plus the unit id for the
atom-fusion variant) and performs **no validation**: not that the item is a training
producer, not a training duration, not a minimum level, and not a bound on the count. The
recorded absence of validation SHALL be recorded as a property of the legacy contract and
SHALL NOT be treated as permission, and the client SHALL NOT add a bound on the count
because the legacy engine sets none.

#### Scenario: The command effects are recorded

- **WHEN** the recorded command contract is inspected
- **THEN** it names each command's arguments and effects, including the atom-fusion unit id and the three-key teardown, each traced to its committed source

#### Scenario: The absence of validation is recorded, not inherited

- **WHEN** the recorded contract is inspected
- **THEN** it states that no validation is performed and that the client therefore implements none, and it adds no producer, duration, level, or count rule

#### Scenario: No count bound is invented

- **WHEN** a queue is projected with any count
- **THEN** no maximum is applied, no entry is refused, and no documented absence is read as a rule

### Requirement: The atom-fusion speedup is recorded without a cost or a timer

The client SHALL record the legacy speedup command's contract: that it requires **both** a
start instant and a queued unit id on the item's attribute bag and therefore **fails** on a
row lacking either, that it reads the training duration from the **queued unit** rather than
from the building, that the duration field is present on only part of the committed unit
set and on no committed building, that the committed value is read as **seconds**, that the
recorded cost shape divides the remaining time by an hour, that the command **charges
nothing** and only reports a cost, and that it clears the start instant. It SHALL implement
**no** speedup cost, **no** timer semantics, and **no** speedup purchase, and it SHALL
refuse rather than fail where the legacy command would fail on a missing key.

#### Scenario: The speedup contract is recorded

- **WHEN** the recorded speedup contract is inspected
- **THEN** it names the two-key precondition, the duration's source, the seconds reading, the cost shape, the fact that nothing is charged, and the start-instant teardown, each traced to its committed source

#### Scenario: No cost is implemented

- **WHEN** this capability's client surface is inspected for a speedup cost
- **THEN** no cost is computed, no balance is changed, and no speedup is offered, because the legacy command charges nothing

#### Scenario: A missing key is refused, not crashed

- **WHEN** the speedup contract is applied to a row whose attribute bag lacks the start instant or the queued unit id
- **THEN** the client reports the unmet precondition and refuses, and does not fail the way the legacy command does

### Requirement: A queued unit id resolves through content, and an unresolvable one is reported

The client SHALL resolve a queue's recorded queued unit id through the content registry's
`units` domain, and SHALL report a queued id that does not resolve as **unresolvable with
its recorded value intact** — never dropped, never coerced to a name, and never replaced
by a guess. This is required because the id originates from a client-supplied argument and
no evidence establishes which ids a client actually sends.

#### Scenario: A queued id resolves

- **WHEN** a queue records a queued unit id that the content package carries
- **THEN** the projection resolves it and reports the committed unit name alongside the id

#### Scenario: An unresolvable queued id is reported, not dropped

- **WHEN** a queue records a queued unit id the content package does not carry
- **THEN** the projection reports it as unresolvable with the recorded value intact, and substitutes nothing

### Requirement: An executed-legacy fixture for the push and pop pair

The change SHALL capture an executed-legacy fixture for a queue **push** followed by a
queue **pop** against a real placed training producer in the committed corpus, in a
disposable copy of the legacy server, and SHALL record in the fixture's manifest that the
pair was captured, that **no** completion was captured, and that no completion command
exists. The fixture SHALL require no fabricated player state, and the committed corpus
SHALL remain byte-identical outside the disposable copy.

#### Scenario: The push and pop are captured

- **WHEN** the evidence step runs
- **THEN** a fixture is committed under `tests/fixtures/godot-unit-queues/` recording the push and the pop with their before and after states, against a real placed training producer, and the working-tree corpus and the ten delivered fixture directories are unchanged

#### Scenario: The manifest records the missing completion

- **WHEN** the fixture's manifest is read
- **THEN** it states that a push and a pop were captured, that no completion was captured, and that the legacy server has no completion command, so the gap is on the record rather than implied

#### Scenario: The proof is non-tautological

- **WHEN** the push and pop are replayed
- **THEN** each is proven to have changed the row's attribute bag in the recorded way, and every stored resource is proven **unchanged**, which is what makes the neutral-vector claim meaningful

### Requirement: Queue intents carry no cost, duration, or outcome

Queue mutations SHALL be sent as **guarded intents** carrying **only** a player identifier
and the target row's key. A client SHALL NOT send a cost, a duration, a training time, a
readiness value, a count, or any outcome, and the service SHALL ignore any such key. The
post-execution proof SHALL assert that **every stored resource is unchanged** by a push or a
pop, so a client-supplied resource vector cannot mint or burn a balance through this path.

#### Scenario: The intent is a key and nothing else

- **WHEN** a push or a pop is sent
- **THEN** the request carries only the player identifier and the target row's key, and no cost, duration, readiness, count, or outcome is sent

#### Scenario: A client-supplied outcome is ignored

- **WHEN** a push or pop request also carries a cost, duration, count, or readiness key
- **THEN** the service ignores those keys and derives any effect from committed content, changing nothing beyond the recorded attribute-bag effect

#### Scenario: No resource moves

- **WHEN** a push or a pop is executed and proven
- **THEN** every stored resource is identical before and after, and the row's attribute bag carries exactly the recorded count, instant, and optional queued unit id

### Requirement: Unit-queue evidence and claim limits

The change SHALL commit a deterministic `unit-queues-report-v1` report recording the three
commands' effects, the recorded absence of validation, the three-key teardown, the corpus
measurement, the fixture's before and after, the recorded speedup contract, the
established-versus-derived split, and the explicit non-claims, byte-identical across
reruns. The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed;
**no completion and no elapsed-time evaluation are implemented, because the legacy server
has neither**; **no cost and no timer are implemented**; **no count bound is implemented**;
**no unit is produced, trained, or placed**; **no acquisition is claimed**; no training
duration semantics are claimed; and the fixture covers a push and a pop only, so it
evidences nothing about a finished queue.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-queues/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture of a unit is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no unit is rendered, animated, or played, and that the fixture evidences a push and a pop rather than a produced unit
