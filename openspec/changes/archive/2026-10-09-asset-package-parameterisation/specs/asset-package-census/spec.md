# Spec Delta

## Purpose

Measure which conversion targets are actually convertible, and record the refusals for the ones
that are not, so that a milestone claiming asset coverage rests on a re-runnable measurement
rather than on an assumption that a tool generalised because it ran without error once.

## ADDED Requirements

### Requirement: The convertible target set is measured over the whole candidate population

The census tool SHALL define a target as **convertible-candidate** when its sprite's bitmaps are
already recorded as extracted and its `img_name` resolves to exactly one row in the committed
normalized content, and SHALL evaluate **every** candidate rather than a sample. It SHALL record,
per target, the domain, the stem, the content `legacy_id`, the verdict, and — on refusal — the
refusal class and the distinct problem strings. The report SHALL be written to a deterministic,
committed path and SHALL be byte-identical across repeated runs against unchanged inputs.

#### Scenario: Evaluate every candidate

- **WHEN** the census runs over the candidate population
- **THEN** every candidate appears in the report exactly once with a verdict
- **AND** the counts of successes and refusals per domain sum to the candidate count

#### Scenario: Reproduce the report

- **WHEN** the census is run twice against unchanged inputs
- **THEN** the report bytes are identical, with no timestamp, host, or iteration-order field

#### Scenario: Derive the candidate set, never transcribe it

- **WHEN** the candidate set is built
- **THEN** it is derived from the committed asset-ID registry and the committed normalized content
- **AND** no stem, id, or count is transcribed into the tool

### Requirement: A refused target is data, not a failure of the census

The census tool SHALL complete the population when individual targets are refused by a converter,
reporting each refusal as a record, and SHALL exit non-zero only on a genuine tool failure — an
unreadable input, a malformed report, or a missing required output root. Each refused target SHALL
be attributed to exactly one refusal class, so that no target is double-counted and no class
boundary is invented to fit a target that fails for two reasons.

#### Scenario: One refusal does not end the run

- **WHEN** a target in the population is refused by its converter
- **THEN** the census records the refusal and continues with the remaining candidates
- **AND** the final report still accounts for every candidate

#### Scenario: Disjoint classes

- **WHEN** refusals are tallied by class
- **THEN** the per-class target counts sum to the total number of refused targets
- **AND** the class names are the converter's own problem strings, not invented categories

#### Scenario: A genuine tool failure still fails

- **WHEN** the census cannot read a required input or cannot write its report
- **THEN** it exits non-zero and writes no partial report

### Requirement: The census is contained and preserves every input

The census tool SHALL write only beneath an explicit output root and SHALL require one, never
defaulting to the repository root, and SHALL refuse an output root that is the repository root or
lies beneath it, deciding that before it creates anything. It SHALL NOT modify any sprite, extracted
bitmap, inspection or extraction manifest, normalized content file, save, config, or village, and
SHALL NOT write into `conversions.json`, `statuses.json`, or any converted package directory. It
SHALL NOT use Flash, a browser, the network, a server, or a subprocess.

#### Scenario: Every write is contained

- **WHEN** the census runs with an output root outside the repository
- **THEN** the repository gains no file and loses none
- **AND** the working tree is byte-identical before and after, apart from the committed report

#### Scenario: Refuse an output root inside the repository

- **WHEN** the census is given an output root that is the repository root or lies beneath it
- **THEN** it exits non-zero with a message naming the refusal
- **AND** it creates neither that output root nor any report

#### Scenario: Judge containment by resolved path, not by name

- **WHEN** the output root's path merely begins with the repository's path
- **AND** it is a sibling rather than a descendant
- **THEN** the census accepts it

#### Scenario: No converter output escapes the root

- **WHEN** a converter runs inside the census
- **THEN** its package directory, bitmap payloads, and manifest writes land beneath the output root
- **AND** no converted package directory or registry manifest in the repository is created or
  replaced