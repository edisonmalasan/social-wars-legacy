## Purpose

Give the Godot client a typed, read-only projection of a player-owned **unit instance** —
a legacy map row plus its resolved definition, including rows nested inside a garrison
container — with no acquisition, training, movement, or gameplay semantics, and with the
committed corpus's lack of unit rows recorded as a limitation rather than fabricated
around.

## Requirements

### Requirement: Unit instances are rows, not widened definitions

The client SHALL expose a player-owned **unit instance** as a typed, read-only
`UnitInstance` that **wraps** one legacy map row together with its resolved
`UnitDefinition`, and SHALL be a **distinct type** from the static definition rather than
an extension of it. An instance SHALL carry the row's own fields verbatim — item id, cell
coordinates, row instant, orientation, and player team — and its `attr` bag, and SHALL
read its identity from its resolved definition rather than restating the definition's
fields. A row whose committed item `type` is not a unit SHALL be **rejected**, never
coerced into an instance, and the instance surface SHALL NOT mutate its row or its
definition.

#### Scenario: An instance wraps a row and its definition

- **WHEN** a unit instance is built from a committed map row and its resolved definition
- **THEN** it carries the row's item id, cell, instant, orientation, and player team verbatim, holds the definition rather than copying it, and the definition remains unchanged

#### Scenario: A non-unit row is rejected, not coerced

- **WHEN** a row is offered whose committed item `type` is not a unit
- **THEN** no instance is produced, the failure names the row's key and its committed type, and nothing is coerced

#### Scenario: A definition is never mutated into an instance

- **WHEN** an instance is inspected for a field that could hold player state
- **THEN** the definition it holds still has none, and the instance's own player state lives on the instance, never on the definition

### Requirement: A garrisoned unit is a row nested in a row

The client SHALL treat a placed row's fifth slot as a **list of nested rows**, not a list
of identifiers, and SHALL parse each nested element as a unit instance in its own right.
Nesting SHALL be bounded by a named maximum depth, and a row set exceeding that bound
SHALL **fail closed** with an error naming the key and the depth — never silently
truncated, because a truncated garrison is a wrong answer presented as a correct one.
An empty fifth slot SHALL be an empty garrison, not an absent one.

#### Scenario: A nested row is parsed as an instance

- **WHEN** a placed row's fifth slot contains a row
- **THEN** that row is parsed as a unit instance of its own, with its own item id, cell, and definition

#### Scenario: An empty garrison is empty, not absent

- **WHEN** a placed row's fifth slot is an empty list
- **THEN** it reads as a garrison with no members, distinguishable from a row whose fifth slot is missing or malformed

#### Scenario: Excessive nesting fails closed

- **WHEN** a row set nests rows beyond the named maximum depth
- **THEN** parsing fails closed with an error naming the key and the depth, and no partial garrison is returned

### Requirement: Unit rows are classified by committed type

The client SHALL classify a map row as a unit by its committed item **`type`** field, and
SHALL NOT use the normalized `kind` field as the classification gate, because the
committed stored configuration carries no `kind` field. A normalized `kind` value MAY
remain available on the resolved definition as a normalization artifact and SHALL NOT gate
classification.

#### Scenario: Classification uses the committed field

- **WHEN** rows are classified and some carry committed `type` `u` while others carry `b`
- **THEN** only the `u` rows become unit instances, and the `b` rows are reported as buildings with no coercion

#### Scenario: The normalization artifact is not a gate

- **WHEN** a definition exposes a normalized `kind`
- **THEN** classification is unchanged by it, and the artifact is documented as absent from the stored configuration

### Requirement: The garrison container has no enforced capacity

The client SHALL impose **no** garrison capacity limit, because the committed
`unit_capacity` field has **no** legacy consumer: it is not read by any legacy branch.
The client MAY report the committed capacity of a garrison-capable definition for
reference — 48 of 470 committed buildings and **5 of 429 committed units** carry a
non-zero value — and SHALL state that no capacity rule is implemented and that
authoritative validation belongs to a later server-authoritative milestone.

#### Scenario: No capacity is refused or truncated

- **WHEN** a garrison is projected and its size is compared against the definition's committed capacity
- **THEN** no limit is applied, no member is refused, and no member is dropped

#### Scenario: The committed capacity is reported as content only

- **WHEN** a garrison-capable definition is inspected
- **THEN** its committed capacity may be reported, and the report states that no legacy branch reads the field and that no rule is implemented

### Requirement: The production-queue keys are reserved, not implemented

The client SHALL declare the production-queue attribute keys `nu`, `ts`, and `ui` as a
named reserved inventory with their established meanings and their established teardown
rule — the count, the start instant, the optional queued unit id, and the deletion of all
three together when the count reaches zero. Reading whether a row carries these keys is
permitted projection; this capability SHALL add **no** queue increment, no decrement, no
timestamp write, and no queue projection, and SHALL implement no training, production, or
queueing behaviour.

#### Scenario: The reserved inventory is named and typed

- **WHEN** the reserved attribute-key inventory is inspected
- **THEN** it names `nu`, `ts`, and `ui` with their established meanings and the teardown rule, and the meanings are recorded as established from committed source

#### Scenario: No queue behaviour is implemented

- **WHEN** this capability's client surface is inspected for queue mutation
- **THEN** it offers no increment, no decrement, no timestamp write, and no queue projection, and training, production, and queueing remain undelivered later deliver lines

#### Scenario: Presence is readable without behaviour

- **WHEN** a row is projected that carries the reserved keys
- **THEN** their presence and committed values may be reported as content, and no queue state is computed from them

### Requirement: A dead unit leaves no instance

The client SHALL record that the legacy dead-unit pool is an **integer count keyed by
item id** that **discards the unit's row**, and SHALL therefore model **no** instance for a
dead unit. The client MAY read and report that count as a plain integer map. It SHALL NOT
evaluate a resurrection predicate, SHALL NOT create a corpse or recoverable instance, and
SHALL implement no death or resurrection behaviour; the committed coverage of any
resurrection property is content, not an applied rule.

#### Scenario: The count is reported as a count

- **WHEN** the legacy dead-unit count is read
- **THEN** it is reported as an integer keyed by item id, and no row, corpse, or recoverable instance is derived from it

#### Scenario: No resurrection rule is applied

- **WHEN** a unit definition carries a resurrection property
- **THEN** no predicate is evaluated from it, and death and resurrection remain undelivered behaviour

### Requirement: The committed corpus yields zero unit instances, and that is asserted

The projection SHALL return **zero** unit instances for the committed fresh-player
corpus, and the client SHALL assert that zero explicitly rather than tolerate it. The
client SHALL demonstrate that the projection returns instances for a row set that
contains unit rows, and SHALL demonstrate it with **crafted in-memory test input only** —
never by writing a unit row into a save, a corpus, or a fixture. Against the committed
corpus the client SHALL record that every placed row classifies as a building and that no
row carries a non-empty garrison or any production-queue attribute.

#### Scenario: The corpus result is zero and is asserted

- **WHEN** the projection runs against the committed fresh-player corpus
- **THEN** it returns zero unit instances, every placed row is reported as a building, no row carries a non-empty garrison, and no row carries a production-queue attribute

#### Scenario: Instances are demonstrated without fabricating a save

- **WHEN** the projection is exercised over a crafted in-memory row set containing a unit row
- **THEN** a unit instance is returned, and the input is labelled as test input rather than as evidence of any behaviour

#### Scenario: No fabricated save is written

- **WHEN** this change's verification runs
- **THEN** no save, corpus, or fixture is created or modified to hold a unit row, and the committed corpus stays byte-identical

### Requirement: Unit instances are read-only state, not a server operation

Unit instances SHALL be read from a save already in hand and SHALL NOT require or expose a
server operation: no compatibility API route SHALL be added, no client intent SHALL be sent
to obtain one, and no persistence behaviour SHALL change. This capability SHALL add no
executed-legacy fixture, SHALL claim **no** means by which a player obtains or places a
unit, and SHALL claim no queueing, training, collection, movement, animation, or behaviour.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No acquisition is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no committed unit is store-listed, that the committed unit sources are later-milestone systems, and that no means of obtaining or placing a unit is claimed

#### Scenario: No behaviour line is claimed

- **WHEN** this capability's claim limits are read
- **THEN** they name queues, production, collection, movement, animations, and basic behaviors as undelivered later deliver lines, and state that the first executed-legacy unit fixture belongs to the production line

### Requirement: Unit-instance evidence and claim limits

The change SHALL commit a deterministic `unit-instances-report-v1` report recording the row
contract and the source lines that establish it, the corpus measurements, the
zero-instance result, the garrison container contract, the dead-counter contract, the
reserved-key inventory, the committed capacity distribution with its no-rule statement,
the established-versus-derived split, and the explicit non-claims, byte-identical across
reruns. The non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed;
**no unit is rendered, animated, or played**; **no executed-legacy fixture was captured**
because the committed corpus contains no unit row, and none was fabricated; **no
acquisition, queueing, training, garrison-capacity, death, resurrection, movement, or
behaviour is implemented**; **no gameplay semantics are attached to any unit statistic**;
**no capacity rule is enforced**; and the first executed-legacy unit fixture belongs to
the production line. The change SHALL NOT claim a windowed capture, because no unit exists
to render and the projection changes nothing visual.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-instances/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: No capture is claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no windowed capture is claimed, because no unit exists to render
