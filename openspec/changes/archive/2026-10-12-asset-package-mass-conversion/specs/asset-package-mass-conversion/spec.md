# asset-package-mass-conversion — delta

## ADDED Requirements

### Requirement: The converted set is the measured convertible set, derived and never transcribed

A mass-conversion tool SHALL convert exactly those targets the committed census records with a
`converted` verdict, and SHALL derive that set at run time by reading the census. It SHALL NOT
transcribe any target stem, id, or count into source code, configuration, or a committed list, so
that a content change moves the set without a hand edit.

The tool SHALL report, per target, the domain, stem, verdict, and whether the verdict agreed with the
census, and SHALL summarise the totals. **A disagreement SHALL be reported as a distinct outcome**,
not silently overwritten by the run's own verdict.

#### Scenario: Convert the measured convertible set

- **WHEN** the tool runs against the committed census
- **THEN** it converts every census-convertible target exactly once and no other target
- **AND** the number of converted targets equals the census's own convertible count

#### Scenario: A target whose verdict disagrees with the census

- **WHEN** a target converts during the run but the census records it as refused, or the reverse
- **THEN** the disagreement is counted and listed in the summary
- **AND** it is not silently accepted in either direction

#### Scenario: The set is derived, not transcribed

- **WHEN** the target set is built
- **THEN** it is read from the committed census at run time
- **AND** no target stem appears as a literal in the tool's source

#### Scenario: Refused targets stay refused

- **WHEN** the tool runs
- **THEN** every census-refused target is left unconverted and no refusal class is lifted

### Requirement: Conversion output is deterministic across repeated runs

The tool's committed output SHALL be byte-identical across **three** consecutive runs against
unchanged inputs, and SHALL contain no timestamp, host name, iteration-order, or absolute-path field
that varies between runs or between checkout forms.

#### Scenario: Reproduce the output

- **WHEN** the tool is run three consecutive times against unchanged inputs
- **THEN** all three runs produce byte-identical package manifests and registry updates

#### Scenario: No run-varying field

- **WHEN** the output is inspected for volatile fields
- **THEN** it records none, and a change in any recorded digest fails the run

### Requirement: Conversion preserves every input and the preservation manifest

The tool SHALL treat all repository sources as read-only input: sprites, extracted bitmaps,
inspection and extraction manifests, normalized content, saves, config, and villages SHALL be
byte-identical before and after a run.

**The tool SHALL NOT regenerate, modify, or re-pin the preservation manifest.** That manifest is
built from the Git tree of one pinned commit, so later additions cannot enter it; rewriting it would
assert a change that cannot occur.

#### Scenario: Prove inputs are untouched

- **WHEN** a run completes
- **THEN** the digests of every protected input source are equal before and after
- **AND** no source file is created, modified, or deleted

#### Scenario: The preservation manifest does not move

- **WHEN** converted packages are added to the repository
- **THEN** the preservation manifest still verifies at its original entry count and byte total

#### Scenario: Conversion is contained and offline

- **WHEN** the tool runs
- **THEN** it uses no Flash, Ruffle, ActionScript, browser, server, subprocess, or network access

### Requirement: Committed package manifests reference shared bitmaps and copy none

A committed converted package SHALL contain exactly one file, `package.json`, and SHALL reference
every bitmap it records by a path into the shared extracted image tree together with that bitmap's
byte count and SHA-256. It SHALL contain no copied bitmap bytes.

Every referenced path SHALL resolve and its bytes SHALL hash to the recorded SHA-256 at conversion
time, so a reference is verified at build time rather than trusted.

#### Scenario: A package holds no copied bytes

- **WHEN** a converted package directory is inspected
- **THEN** its only file is `package.json`
- **AND** no bitmap file is present in it

#### Scenario: Every reference is verified

- **WHEN** conversion completes successfully
- **THEN** every recorded bitmap path resolved and hashed to its recorded SHA-256 during the run

#### Scenario: An unverifiable reference fails the run

- **WHEN** a referenced extracted bitmap is missing or its digest differs
- **THEN** conversion fails, identifies the bitmap, and writes no outputs

### Requirement: Carried-forward parse anomalies are recorded once, never encoded as data

Where a captured field's meaning is not established, the tool SHALL preserve the captured bytes
**verbatim** and SHALL NOT add a per-record field asserting an interpretation of them. Such an
anomaly SHALL be recorded once at the level of the change's own artifacts, with its measurement
quoted, as carried-forward and unresolved.

#### Scenario: Captured bytes are preserved

- **WHEN** a package records a field whose decoding is unestablished
- **THEN** the recorded value is the captured bytes verbatim

#### Scenario: No interpretation is invented as data

- **WHEN** packages are inspected for anomaly fields
- **THEN** none carries a field asserting an interpretation of the unestablished bytes