# godot-friends Specification

## Purpose

Project the roster `neighbors(USERID)` serves — every loaded village other than a
hardcoded two-pid exclusion — as a typed, read-only, **unordered** projection, and
refuse the relationship vocabulary the deliver item's name would otherwise imply.

## Requirements

### Requirement: The roster is delivered as a typed read-only projection reported as an unordered set
The capability SHALL project each roster entry as the twelve `playerInfo` keys the
preserved server carries plus the six fields it derives from `maps[0]`, and SHALL
report membership as an **unordered set**. It SHALL NOT assert a roster order,
because the preserved order follows `os.listdir()` and is already recorded as
environment-dependent in the committed field-stability record. The projection
SHALL be read-only: it SHALL NOT mutate the payload it reads.

#### Scenario: Project the committed roster
- **WHEN** the bootstrap payload's roster is projected
- **THEN** every entry carries exactly eighteen keys
- **AND** the twelve carried keys and the six derived keys are distinguishable in the projection
- **AND** membership is reported without an asserted order

#### Scenario: Reject an asserted order
- **WHEN** the roster is reversed relative to the served order
- **THEN** the projected membership is unchanged
- **AND** no delivered assertion compares one roster position against another

### Requirement: Membership is derived from the literal pid exclusion pair, and the exclusion is not derived from content
Membership SHALL be every loaded static village, minus the two-pid literal
exclusion the preserved server hardcodes, minus the requesting player in the
saves loop only. The capability SHALL ship the **literal** pid pair and SHALL
record that nothing in committed content or configuration names it, so deriving
the exclusion from content would be an invention. The capability SHALL record that
the exclusion applies to the static-village loop only and that the self-exclusion
applies to the saves loop only.

#### Scenario: Exclude the literal pair
- **WHEN** a loaded static village carries one of the two excluded pids
- **THEN** that village is absent from the projected roster

#### Scenario: Record that the exclusion is literal
- **WHEN** a maintainer asks why the pair is a literal rather than a lookup
- **THEN** the recorded reason is that no committed schedule, configuration, or normalized package names it
- **AND** the rejected content-derived alternative is recorded

### Requirement: A malformed roster fails closed rather than projecting a partial roster
The capability SHALL refuse a roster that is absent, is not a list, or contains an
entry that is not an object, and SHALL NOT substitute an empty roster, a default
entry, or a coerced value for the refusal. A refusal SHALL carry a distinct code
identifying which shape failed.

#### Scenario: Refuse a non-list roster
- **WHEN** the roster field is not a list
- **THEN** the projection fails closed
- **AND** the refusal names the malformed shape

#### Scenario: Refuse a non-object entry
- **WHEN** one roster entry is not an object
- **THEN** the projection fails closed rather than skipping that entry

### Requirement: No roster entry exposes a privateState key, and the projection reports that absence as measured
The capability SHALL report that no roster entry carries any key of the recording
player's `privateState`, and SHALL enforce that absence structurally rather than
by assertion alone. The projection SHALL NOT be widened to carry private progress,
and the roster's exposure of six economy fields SHALL be reported as the preserved
server's behaviour rather than as a permission to expose more.

#### Scenario: Report the absence
- **WHEN** each entry's keys are compared against the recording player's `privateState` keys
- **THEN** the intersection is empty for every entry
- **AND** the empty intersection is reported rather than assumed

### Requirement: Both roster channels are reported, and neither is silently chosen
The preserved server serves a roster **twice**: the bootstrap roster with eighteen
fields per entry, and the Flash-variable roster with two fields per entry, by two
functions that are near-duplicates and were not derived from one another. The
capability SHALL report both channels, their differing per-entry field sets, and
the fact that only the bootstrap channel is a modern-runtime surface. It SHALL NOT
present one channel's shape as the roster's shape, and SHALL NOT deduplicate the
two channels into a single projection.

#### Scenario: Report the channel disagreement
- **WHEN** a maintainer reviews the roster
- **THEN** both channels are named with their per-entry field counts
- **AND** the flash-variable channel is recorded as client-only and not delivered

### Requirement: The relationship vocabulary is refused, and the refusal is enforced structurally
The capability SHALL NOT present a roster entry as a friend, ally, or neighbour in
the social sense, and SHALL NOT derive direction, consent, membership lifecycle, or
any selection rule. It SHALL record that membership is total and unconditional,
and that every relationship-shaped token has zero consumers across all eleven
legacy modules while the corresponding corpus fields are uniformly empty. The
absence of a friendship selection, add, remove, accept, or decline capability SHALL
be **enforced by guards that fail when such a capability is introduced**, because a
prose refusal cannot fail.

#### Scenario: Refuse the relationship claim
- **WHEN** a maintainer reviews the delivered surface
- **THEN** no capability name, identifier, or delivered field presents an entry as a friend
- **AND** no membership is ever selected, added, removed, or accepted

#### Scenario: Guard the refusal
- **WHEN** a friendship-selection, assist, consent, or lifecycle capability is introduced into the delivered module
- **THEN** the suite fails
- **AND** the failure is shown by injection rather than trusted

### Requirement: The visit surface is recorded as a divergence and is not delivered
The preserved server has a visit route whose general-Mike branch tests membership
in the two-pid pair and then passes the **first** pid for both, so requesting the
second returns the first's data. The capability SHALL record that behaviour as a
**divergence not reproduced**, SHALL record that the visit payload exposes the
visited player's entire `privateState` and returns an empty string with HTTP 200
on failure, and SHALL NOT reproduce the discarded pid, SHALL NOT deliver a visit
payload, and SHALL NOT derive a visit, world, or leaderboard concept.

#### Scenario: Record the discarded-pid divergence
- **WHEN** a maintainer reviews the visit surface
- **THEN** the discarded-pid behaviour is recorded as a divergence rather than reproduced as parity
- **AND** the absence of any committed fixture exercising a visit is recorded

#### Scenario: Absent delivery
- **WHEN** the delivered surface is reviewed
- **THEN** no visit payload, visit map, or visit session capability is delivered
- **AND** the absence of a committed visit fixture is recorded as the reason

### Requirement: Both roster arms are backed by already-committed executed evidence, and no new capture is fabricated
The capability SHALL record that both roster channels are backed by committed
executed-legacy captures that this line re-verifies rather than re-derives, and
SHALL NOT fabricate a new fixture. It SHALL record that the saves-loop half of
either channel has **no** executed evidence, because the committed captures ran
with no saves directory, and SHALL NOT claim coverage it does not have.

#### Scenario: Reuse the committed captures
- **WHEN** the projection is verified against executed evidence
- **THEN** the bootstrap roster is compared leaf-by-leaf against the committed capture
- **AND** the flash-variable roster is compared against the committed capture
- **AND** no new fixture is created

#### Scenario: Record the uncovered half
- **WHEN** a maintainer asks about the saves loop
- **THEN** the recorded answer is that no committed capture exercised it
- **AND** the coverage claim is limited to the static-village roster
