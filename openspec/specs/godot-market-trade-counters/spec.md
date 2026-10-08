# godot-market-trade-counters Specification

## Purpose

Project the market / trade counter state read-only into the modern client, with the measured
legacy behaviour recorded as explicit refusals rather than reproduced, so that a surface with
committed content, one real consumer, and an **unenforced** cap cannot later be mistaken for a
priced, gated, or enforced market.

Three measured facts shape every requirement below, and each is re-derived on every suite run
rather than inherited:

- **8 of the 10** committed save documents record a zero last-trade instant, for which the legacy
  day-reset predicate is **unconditionally true** and the count is cleared on every load. The cap
  is therefore reachable in the committed corpus in **one** document.
- The trade cap is the legacy branch's own **literal**. A committed content value happens to carry
  the same number and has **zero** legacy consumers, so its agreement is recorded as a
  **coincidence** and nothing is derived from it.
- The branch stores the count **clamped** while printing the remaining-trades figure
  **unclamped**, so the two disagree above the cap. That disagreement is reproduced and reported,
  never corrected.

This capability is named for the **surface** (`market / trade counters`), not for the roadmap
deliver item it serves (`special mechanics`), and the promoted surface deliberately **displaced**
the investigation's own rank #1: that surface is already owned by `godot-unit-queues` under its
archived decision D6, and two owners of one surface is a boundary nobody enforces.

**Sync note.** No existing specification is amended by this capability. The single existing
mention, `godot-building-resources/spec.md`'s out-of-scope note, is a limitation this capability
**satisfies** rather than a requirement it revises.

## Requirements

### Requirement: The trade counter state is projected read-only

The client SHALL project the committed trade-counter state from the server's map and private
state, and SHALL report the committed count and the committed last-trade instant verbatim. It
SHALL NOT write either field, issue any request, or expose any affordance that begins,
completes, or reverses a trade.

#### Scenario: The counters project verbatim

- **WHEN** the projection runs over a state carrying a trade count and a last-trade instant
- **THEN** it reports the committed count and the committed instant unaltered
- **AND** it derives no price, cost, or resource movement from either

#### Scenario: The projection is read-only

- **WHEN** the projection is built
- **THEN** no game state is written
- **AND** no network request is issued
- **AND** the module exposes no callable action for trading, resetting the counter, or
  fast-forwarding the instant

#### Scenario: A malformed field is reported rather than coerced

- **WHEN** the count or the instant is absent, or is not an integer
- **THEN** the projection reports the field as unavailable
- **AND** it reports no derived value that would require the missing field
- **AND** the recorded field travels beside the refusal, untouched

---

### Requirement: The cap is the branch's literal and is reported as unenforced

The client SHALL derive the trade cap from the legacy branch's own hardcoded literal, and
SHALL report that the cap is **stored but never enforced**, because the committed count's only
reader is the increment that produces it.

#### Scenario: The cap resolves to the branch's literal

- **WHEN** the cap is inspected
- **THEN** it is the value the legacy branch stores when clamping the count
- **AND** it is read from that branch literal, not from any committed content value

#### Scenario: The coincidence with committed content is recorded, not used

- **WHEN** the committed trade-cap content value is inspected alongside the branch's literal
- **THEN** the two are reported as equal
- **AND** the equality is recorded as a coincidence
- **AND** no delivered value is derived from the committed content value, which has no legacy
  consumer

#### Scenario: No enforcement is claimed or offered

- **WHEN** this capability's client surface is inspected for a trade limit
- **THEN** no trade is refused, gated, or limited
- **AND** no affordance is offered that depends on the count
- **AND** the projection reports that the count is not read by any legacy branch to decide
  anything, because its only reader is its own increment

---

### Requirement: The branch's remaining-trades arithmetic is reproduced unclamped

The client SHALL reproduce the legacy branch's remaining-trades value **without clamping it**,
and SHALL report it separately from the stored count, because the branch prints the
unclamped local while storing the clamped one.

#### Scenario: The two values agree below the cap

- **WHEN** the stored count is below the cap
- **THEN** the reported remaining value is the cap minus the count
- **AND** it equals the count the branch would print

#### Scenario: The two values disagree above the cap and the defect is visible

- **WHEN** the count has reached the cap and a further trade is recorded
- **THEN** the stored count remains at the cap
- **AND** the reported remaining value is **negative**, reproducing the branch's print
- **AND** the projection performs no clamping of its own

#### Scenario: The defect cannot be silently corrected

- **WHEN** this capability's delivered modules are inspected
- **THEN** they contain no clamping of the reported remaining value
- **AND** no helper exists whose purpose is to bound, floor, or correct it

---

### Requirement: The day-bucket reset predicate is reported, never performed

The client SHALL report the day bucket of the recorded last-trade instant, the day bucket of
the server clock, and whether the legacy reset predicate holds between them. It SHALL NOT
perform the reset, and SHALL NOT reimplement the engine's reset helper.

#### Scenario: The predicate is reported from both buckets

- **WHEN** the projection evaluates the reset condition
- **THEN** it reports the recorded instant's day bucket and the current instant's day bucket
- **AND** it reports whether they differ, which is the legacy predicate verbatim

#### Scenario: No reset is performed and the engine helper is not reimplemented

- **WHEN** this capability's delivered modules are inspected
- **THEN** no module writes the trade count to zero
- **AND** no module duplicates the engine's reset logic
- **AND** the engine's helper is referenced as the owner of that behaviour

---

### Requirement: The committed trade schedule is projected verbatim with no derived economy

The client SHALL project every committed market-schedule value verbatim, SHALL report that
each has no legacy consumer, and SHALL derive no price, period, increment bound, cap, or
percentage from them.

#### Scenario: Every committed value projects verbatim

- **WHEN** the committed schedule is projected
- **THEN** each market-schedule value is reported exactly as committed, including its
  committed type
- **AND** the values are read through the existing normalized content registry rather than
  transcribed into a delivered module

#### Scenario: The zero-consumer status is re-measured, not asserted

- **WHEN** the suite runs
- **THEN** it re-measures, over every legacy module, how many of the projected values have a
  consumer
- **AND** it requires the measured count to equal the reported count
- **AND** a legacy edit that gives any of them a consumer fails the suite rather than
  silently contradicting it

#### Scenario: No economy is derived

- **WHEN** this capability's delivered modules are inspected
- **THEN** no price, cost, period, percentage, or increment bound is computed from any
  projected value
- **AND** no module contains a multiplication or division over a projected committed value

---

### Requirement: The client-dictated behaviours are recorded as divergences

The client SHALL record, and SHALL NOT reproduce, the two measured legacy behaviours by which
a client dictates a trade outcome: resource movement that would be applied before the command
dispatcher opens, and a last-trade instant made writable by a client-supplied offset.

#### Scenario: Resource movement is refused, not reproduced

- **WHEN** this capability's client surface is inspected for trade resource movement
- **THEN** no resource is moved and no resource vector is sent
- **AND** the divergence is recorded, because the legacy branch moves no resource itself and
  any movement would have arrived from the client

#### Scenario: The client-writable instant is refused, not reproduced

- **WHEN** this capability's client surface is inspected for a time-offset operation
- **THEN** no operation writes, decrements, or offsets the last-trade instant
- **AND** the recorded divergence states that the legacy branch subtracts a client-supplied
  number of seconds from it, which can move the instant across the day boundary

#### Scenario: Absence of a server rule is not a claim about the client

- **WHEN** this capability's non-claims are inspected
- **THEN** it states no claim about what the legacy client displayed, gated, or hid
- **AND** it states that the delivered client creates no market affordance at all

---

### Requirement: Ownership boundaries with the surrounding capabilities

This capability SHALL own the trade counter and last-trade instant only, and SHALL NOT own the
production queue, the bonus ladders, the darts instants, or the committed trade schedule
content.

#### Scenario: Foreign surfaces are not implemented here

- **WHEN** this capability's delivered modules are inspected
- **THEN** they contain no reference to the production queue's keys, the bonus-ladder fields,
  or the darts instants
- **AND** they compute no bonus, no collection, and no queue value

#### Scenario: Every declared owner exists

- **WHEN** the declared ownership boundaries are inspected
- **THEN** each owning capability's specification exists
- **AND** each owning capability projects the surface this line defers to, so a boundary
  cannot rot into an orphan

#### Scenario: The committed schedule stays with its normalizer

- **WHEN** the committed market-schedule values are inspected
- **THEN** they are read through the content registry that normalizes them
- **AND** this capability neither duplicates nor redefines that normalization
