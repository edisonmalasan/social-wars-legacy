# godot-darts Specification

## Purpose

Deliver M11's darts and premium-account line: the darts state machine over six
recorded fields, and the one surface in M11 where the preserved server derives a
value from committed content and computes it authoritatively — the premium
account duration — beside a committed price that nothing anywhere reads.

## Requirements

### Requirement: The delivered surface is a typed read-only projection of recorded darts and premium state, and it implies no darts feature

The capability SHALL deliver a typed read-only projection of the six recorded
darts fields and the premium-account instant, and SHALL NOT imply that darts is a
playable game feature, that a balloon may be shot, or that a premium account may
be displayed to a player. A capability named for darts asserts nothing about
whether the Flash client presented a darts or premium-purchase interface.

#### Scenario: Review what the capability claims
- **WHEN** the delivered surface is reviewed
- **THEN** it is a projection of recorded state plus server-derived transitions
- **AND** no delivered response field, identifier, or capability name presents a shot, a target, a win, or a premium entitlement as obtainable or active

### Requirement: The six recorded darts fields are delivered with their storage location and recorded corpus values

The projection SHALL cover exactly the six darts state fields measured by the
committed investigation — the balloon list, the got-extra flag, the has-free flag,
the random seed, and the two instants — each reported with the document it is
stored in, and SHALL NOT add a field the investigation did not measure. Recorded
corpus values SHALL be reported with their document counts, and no populated
example SHALL be synthesized where a recorded value is uniform.

#### Scenario: Review darts field coverage
- **WHEN** the projection is compared with the investigation's measured darts field list
- **THEN** all six fields are present with their recorded storage location
- **AND** no unmeasured field is present
- **AND** each field's recorded value is reported with the number of committed documents carrying it

### Requirement: The darts state transitions are delivered as recorded, with their client-sent inputs named as such

The three recorded darts command transitions SHALL be delivered with each
transition's server-written fields derived from recorded state, and each
client-supplied input SHALL be named as client-sent with its source. A client
value SHALL NOT be re-derived, validated, defaulted, or given a meaning the
preserved server does not give it.

#### Scenario: Review a darts transition
- **WHEN** a reset, free-grant, or shot transition is delivered
- **THEN** the fields the server writes are derived from recorded state
- **AND** the client-sent inputs are reported as client-sent rather than as authoritative
- **AND** no semantic is derived from the random seed, which no preserved branch reads

### Requirement: The premium duration is derived server-side from the committed schedule, including its recorded index clamp

The premium duration SHALL be derived from the committed premium-account schedule
on the server, never from a client-supplied duration. An oversized schedule index
SHALL resolve to the last schedule entry, reproducing the recorded clamp, and a
schedule entry carrying no duration SHALL yield zero days rather than an error.

#### Scenario: Derive a premium duration
- **WHEN** a purchase names a schedule index within the committed schedule
- **THEN** the duration is the committed entry's recorded duration, and no client value influences it
- **AND** the committed price beside that duration is not read, derived, or reported as charged

#### Scenario: Resolve an oversized schedule index
- **WHEN** a purchase names a schedule index at or beyond the committed schedule's last entry
- **THEN** the duration is the last committed entry's recorded duration

### Requirement: The premium purchase selects its arm by a server-side comparison, and each arm's corpus reachability is reported

The purchase SHALL select between setting the premium instant and extending it by
comparing the server's own clock against the recorded instant, and the selection
SHALL be reported with which arm was taken. Because every committed document
carrying a non-zero premium instant records one that has passed, the extend arm
SHALL be reported as **not** exercised by the committed corpus rather than as
corpus-evidenced.

#### Scenario: Purchase against an elapsed premium instant
- **WHEN** a purchase is delivered for a document whose recorded premium instant is in the past
- **THEN** the instant is set to the server clock plus the derived duration
- **AND** the selected arm is reported as the set arm

#### Scenario: Report the extend arm's reachability
- **WHEN** the corpus is measured
- **THEN** the extend arm is reported as unreachable in every committed document
- **AND** any coverage of that arm is reported as crafted input rather than as corpus evidence

### Requirement: Nothing is charged, and the complete stored resource set must be unchanged

Every delivered action SHALL charge no stored resource, and every successful
action's post-execution proof SHALL compare the **complete** set of stored
resources and require it byte-identical, so the no-charge claim cannot be
satisfied vacuously by checking a subset. A committed price that the preserved
server never reads SHALL be reported with its zero-consumer measurement and SHALL
NOT be turned into a charge.

#### Scenario: Complete a purchase without charging
- **WHEN** a premium purchase succeeds
- **THEN** the premium instant moved by the derived duration
- **AND** every stored resource is byte-identical to its value before the request

#### Scenario: Report the committed price
- **WHEN** the committed schedule is reviewed
- **THEN** the price recorded beside every duration is reported as having zero consumers across the declared legacy modules
- **AND** no amount is debited, and no capability name, identifier, or response field implies a payment was made

### Requirement: The client-sent shot outcome is refused and recorded as a divergence

The recorded shoot transition reads a client truthiness that sets the got-extra
flag when the client claims a win. The preserved server verifies no win, so the
outcome SHALL be refused: no delivered route SHALL set the got-extra flag from a
client value, and the difference from the preserved server SHALL be recorded as a
**divergence** rather than reproduced as parity. The shot index, being an intent
rather than an asserted outcome, SHALL remain deliverable.

#### Scenario: A client claims a won shot
- **WHEN** a shoot request carries a client value claiming the shot won
- **THEN** the got-extra flag is not set by that value
- **AND** the refusal and its divergence from the preserved branch are reported

### Requirement: The unbounded shot list and the absent schedule membership test are refused and reported

The preserved server appends a client shot index to the balloon list whenever the
index is absent, with **no** bound on the list's length and **no** membership
test against the committed darts schedule. Neither rule SHALL be invented. The
delivered surface SHALL refuse to grow the list without a recorded bound, SHALL
report that no schedule membership test exists, and SHALL report the corpus fact
that a committed document records a shot index absent from the committed schedule
while the preserved server accepted it.

#### Scenario: Report the list's missing bound
- **WHEN** the recorded shoot transition is reviewed
- **THEN** it is reported as appending without any length bound
- **AND** no maximum shot count is delivered

#### Scenario: Report the out-of-schedule corpus shot
- **WHEN** the committed corpus is measured
- **THEN** a recorded shot index absent from the committed darts schedule is reported
- **AND** the absence of any preserved membership test is reported, and no membership rule is invented

### Requirement: The week-boundary reset is delivered as a derived predicate with its recorded constants

The one server-side, time-derived darts mutation SHALL be delivered as a predicate
over the recorded instant, the server clock, and the recorded constants, together
with its recorded existence guard and its recorded zero write. Its intent comment
SHALL be reported as a comment, and no reset of any other field SHALL be delivered
because it shares the same function.

#### Scenario: Evaluate the week-boundary predicate
- **WHEN** the reset predicate is evaluated for a recorded instant
- **THEN** the result is derived from the recorded offset applied to both sides, the recorded week length, and a floor-division week comparison
- **AND** the field the recorded branch writes is written as zero, never as the server clock

#### Scenario: A record lacking the instant
- **WHEN** the reset predicate is evaluated for a document that does not carry the instant
- **THEN** no reset is applied, reproducing the recorded existence guard

### Requirement: The darts and premium content tables remain owned by their normalization capabilities

The committed darts schedule SHALL remain owned by its schedule-normalization
capability and the committed premium-account schedule by its tuning-constants
normalization capability. This capability SHALL read both, SHALL NOT normalize,
re-order, extend, or re-derive either, and the ownership SHALL be asserted rather
than assumed so a rename cannot orphan it.

#### Scenario: Verify the content boundary
- **WHEN** the delivered surface is reviewed
- **THEN** the darts schedule is reported as owned elsewhere and is read, not transformed
- **AND** the premium schedule is reported as owned elsewhere and is read, not transformed

### Requirement: Absence is guarded structurally, and every guard is proven by injection

Each refusal in this capability SHALL be enforced by a guard that fails when the
forbidden behavior is introduced, because a prose refusal cannot fail and a guard
can. Every guard SHALL be proven by an injection against a byte-identical copy of
the delivered module, and the recorded injection results — including the restored
file's digest — SHALL appear in the evidence report so the claim is checkable
rather than remembered. No delivered code identifier SHALL be named after the
refused behaviors, and the guards SHALL be shown to be necessary rather than
redundant by at least one injection that borrows no reserved word.

#### Scenario: Introduce a forbidden helper
- **WHEN** a helper capable of charging the committed price, of bounding the shot list, of testing schedule membership, of verifying a win, or of deriving a client duration is introduced into the delivered module
- **THEN** the suite fails with at least one independent failure

#### Scenario: Review the guard evidence
- **WHEN** the evidence report is read
- **THEN** every recorded injection names the guards that caught it, a non-zero exit, and the restored module's digest
- **AND** the suite asserts that at least one injection was caught by a guard other than a name-based one

### Requirement: The corpus that can exercise this surface is named, and the fresh-player document's inability to do so is recorded

The capability SHALL name the committed corpus a fixture or live phase exercises,
and SHALL record that the canonical fresh-player document carries every darts
field at its initial value and a zero premium instant, so it cannot exercise the
shoot arm, the free arm, or the premium purchase arm. Any coverage of those arms
over the fresh-player document SHALL be reported as crafted input.

#### Scenario: Review corpus coverage
- **WHEN** the corpus is measured
- **THEN** the documents carrying a played darts state and a live premium instant are counted and named
- **AND** the fresh-player document is reported as unable to exercise those arms
