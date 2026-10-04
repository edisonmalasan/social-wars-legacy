# Spec Delta

## Purpose

Expose the legacy mission vocabulary as a typed, read-only surface — the 64
committed `MISSION_*` declarations and the three committed mission-adjacent
globals — reported verbatim, with the zero-consumer finding recorded structurally
and with mission *state* left to the capability that already owns it.

## ADDED Requirements

### Requirement: The mission-type vocabulary is projected verbatim and fails closed

The client SHALL expose the committed mission-type vocabulary as a typed,
read-only projection carrying each declaration's name and value exactly as
committed, reporting them **verbatim** with **no** value derived from another. It
SHALL derive **no** category, **no** grouping, **no** ordering beyond the committed
value, and **no** behaviour, trigger, or dispatch keyed on any mission type. It
SHALL never present an absent, malformed, or unresolvable vocabulary as a resolved
one.

#### Scenario: Every declaration is reported verbatim

- **WHEN** the mission vocabulary is projected
- **THEN** every committed declaration is reported with its exact committed name
  and integer value, in committed value order, and no category, grouping, or
  behaviour is derived from any of them

#### Scenario: A malformed or unresolvable vocabulary is reported as unresolvable

- **WHEN** the vocabulary table is absent, is not an array, omits a name or a value,
  or carries a non-integer value
- **THEN** the projection reports the vocabulary as unresolvable with the offending
  entry's recorded state intact, and never substitutes a default or nominal type

### Requirement: The committed vocabulary table is byte-faithful to the legacy declaration

Because the legacy declarations live in a source file rather than in the normalized
content package, the projection SHALL be guarded against transcription drift. The
client's tests SHALL assert, per entry, that the committed table's name and value
are byte-equal to the declaration the legacy source carries, and SHALL assert that
the entry count and the numbering-gap set match an independent extraction of that
source. A hand edit that transcribes any name or value wrongly SHALL fail the
suite rather than ship.

#### Scenario: A faithful table passes

- **WHEN** the committed vocabulary table is compared against the legacy
  declarations
- **THEN** every name and value is byte-equal, the entry counts match, and the
  numbering-gap set matches the extraction

#### Scenario: A mistranscribed value fails

- **WHEN** a committed table entry carries a name or value that differs from the
  legacy declaration
- **THEN** the suite fails naming the differing entry, and the projection is not
  accepted as a faithful representation of the committed vocabulary

#### Scenario: An omitted or added entry fails

- **WHEN** the committed table's entry count or numbering-gap set differs from the
  extraction of the legacy source
- **THEN** the suite fails rather than accepting a partial or padded vocabulary

### Requirement: The zero-consumer finding is recorded structurally, not merely asserted

The client SHALL record that the committed mission vocabulary has no consumer in the
preserved legacy server as a **structural** property rather than a prose claim. It
SHALL pin the delivered module's whole static-function inventory so that adding a
dispatch, trigger, or resolution helper fails the suite, and it SHALL fail if any
delivered code identifier is named after a mission type or mission constant. Both
guards SHALL be proven by injection and restore during implementation, not
trusted.

#### Scenario: An invented dispatch helper fails

- **WHEN** a helper that resolves, dispatches, or triggers on a mission type is
  added to the delivered module
- **THEN** the suite fails on the static-function inventory pin and the suite exits
  non-zero

#### Scenario: A helper named after a mission type fails

- **WHEN** a delivered code identifier is named after a mission type or a
  `MISSION_`-prefixed constant
- **THEN** the suite fails, even if the identifier introduces no behaviour

#### Scenario: The guards are proven rather than trusted

- **WHEN** the line is delivered
- **THEN** each guard has been shown to fail under injection and the file restored
  byte-identically, with the restored file returning the suite to its passing state

### Requirement: The committed mission-adjacent globals are reported verbatim and unenforced

The client SHALL report the three committed mission-adjacent globals — the active
mission count, the permission pack unit list, and the permission cost table —
**exactly as committed**, read through the existing normalized content registry
rather than re-transcribed. It SHALL derive **no** cap, **no** limit, **no** price,
and **no** rule from any of them, and SHALL report no enforcement for any of them,
because the preserved server reads none.

#### Scenario: Each global is reported exactly as committed

- **WHEN** the mission globals are projected
- **THEN** the active-mission count, the pack unit list, and the cost table are
  reported with their committed values and no cap, limit, or price is derived from
  any of them

#### Scenario: No enforcement is reported

- **WHEN** the mission globals are projected
- **THEN** no enforcement of the active-mission count or of the permission entries
  is reported, and the projection records that the preserved server reads none

#### Scenario: The globals are not duplicated

- **WHEN** the projection obtains the mission globals
- **THEN** it reads them from the existing normalized content registry and holds no
  second transcribed copy of them

### Requirement: Mission state is owned by the quest capability and is not re-projected here

The mission identifier, the last-chapter instant, and the current quest-variable
map are already projected verbatim by the quest capability, which also records the
identifier's stringification divergence and the last-chapter instant's
client-writability. This capability SHALL NOT re-project, re-derive, or reconcile
those fields, and SHALL record the boundary structurally: the delivered module
SHALL declare no mission **state**, and the suite SHALL pin that. The two
capabilities SHALL NOT become two sources of truth for the same field.

#### Scenario: The mission state fields are not re-projected

- **WHEN** the mission vocabulary is projected
- **THEN** the mission identifier, the last-chapter instant, and the current
  quest-variable map are not projected by this capability, and no value of theirs
  is derived, reconciled, or reported as belonging to it

#### Scenario: The boundary is pinned

- **WHEN** the delivered module is inspected
- **THEN** it declares no mission state, and adding mission-state access to it
  fails the suite

#### Scenario: The dual-source risk is refused

- **WHEN** the quest capability and this capability are both consulted
- **THEN** the quest capability remains the single owner of the mission state
  fields, and no reconciliation between two readings is introduced

### Requirement: Numbering gaps and near-duplicate declarations are reported as content

The committed vocabulary's numbering is not contiguous and contains near-duplicate
declarations, and no committed rule reconciles either. The projection SHALL report
the numbering gaps and the near-duplicate declarations **as recorded content**. It
SHALL NOT renumber, close gaps, deduplicate, or select a preferred member of a
near-duplicate group.

#### Scenario: The gaps are reported

- **WHEN** the mission vocabulary is projected
- **THEN** the absent numbers in the committed numbering are reported as gaps, and
  no gap is closed by a synthesised value

#### Scenario: Near-duplicates are neither resolved nor removed

- **WHEN** two or more declarations share a stem and overlap in meaning
- **THEN** every member is reported with its own committed value, and none is
  dropped, merged, or declared preferred
