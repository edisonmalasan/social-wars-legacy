## Purpose

Define deterministic, privacy-conscious structural comparison of supplied legacy village states so recorded mutations can be reviewed without replaying commands or changing preserved inputs.

## ADDED Requirements

### Requirement: Explicit offline comparison inputs
The state-diff command SHALL accept either two explicitly named UTF-8 JSON files containing object-root before and after states, or one explicitly named schema-version-1 legacy command record containing object-root `before` and `after` boundaries. The modes SHALL be mutually exclusive. A null record boundary SHALL mean unavailable evidence and SHALL NOT be treated as an empty state. Unknown state fields and unknown record metadata SHALL remain valid inputs, and the command SHALL NOT discover saves, import application modules, migrate state, replay commands, contact a server or network, or execute Flash.

#### Scenario: Compare two supplied state files
- **WHEN** an operator supplies valid object-root before and after JSON files
- **THEN** the command compares exactly those two complete structures without reading a runtime save or modifying either input

#### Scenario: Compare one recorder record
- **WHEN** an operator supplies a supported recorder record with available object-root boundaries
- **THEN** the command compares only its complete `before` and `after` structures and ignores transaction metadata for state equality

#### Scenario: Reject unavailable record evidence
- **WHEN** either boundary in a supplied recorder record is null or missing
- **THEN** the command reports comparison unavailable and emits no comparison report

### Requirement: Type-strict structural differences
Comparison SHALL preserve case-sensitive object keys, unknown fields, numeric-looking string keys, exact legacy identifiers, empty containers, and positional array semantics. Object member order, JSON whitespace, escape spelling, and line endings SHALL not create differences. Booleans, integers, floating-point numbers, strings, null, objects, arrays, and missing members SHALL be distinct comparison types. A changed scalar or type mismatch SHALL produce one changed entry; an added or removed subtree SHALL produce one entry at its root; and common array positions followed by tail additions or removals SHALL be compared in ascending index order.

#### Scenario: Compare canonical migration-boundary fixtures
- **WHEN** the controlled pre-migration and post-migration fresh-player fixtures are compared
- **THEN** the report contains exactly one changed entry at `/version` from null to string

#### Scenario: Preserve legacy array position
- **WHEN** item tuple elements or map-list entries change position or value
- **THEN** the report identifies changes at their exact numeric array paths without set conversion or identifier-based rematching

#### Scenario: Ignore representational JSON differences
- **WHEN** two inputs express the same complete JSON value with different object order, whitespace, escape spelling, or line endings
- **THEN** the command reports the states as equal

### Requirement: Deterministic value-free report
Successful comparison SHALL emit exactly one JSON report to standard output with schema version `1`, policy `structural-json-types-v1`, comparison `equal` or `different`, a change count, and an ordered changes array. Each change SHALL contain only operation `added`, `removed`, or `changed`, an RFC 6901-escaped path, and before and after type labels where missing is distinct from null. The report SHALL contain no state values, payloads, filenames, player correlation, source hashes, timestamps, durations, UUIDs, or machine metadata. Object paths SHALL be ordered by exact key, array paths by numeric index, and serialization SHALL be ASCII-escaped UTF-8 JSON with sorted keys, two-space indentation, LF line endings, and one final newline.

#### Scenario: Repeat a comparison
- **WHEN** the same semantic inputs are compared repeatedly
- **THEN** the command emits byte-identical reports and the same exit status

#### Scenario: Report equality and difference
- **WHEN** a comparison is equal or different
- **THEN** it exits `0` for equal or `1` for different and emits a complete schema-version-1 report matching that outcome

### Requirement: Sensitive path protection
Before emitting a report, the command SHALL collect values associated with the command recorder's known sensitive-key policy from both supplied states and, in record mode, the complete supplied record. It SHALL replace occurrences of those sensitive values in reported path components before RFC 6901 escaping. If protection would collapse distinct changed paths into one reported path, the command SHALL fail explicitly rather than omit, merge, or misidentify a change. Reports SHALL remain classified as private evidence because unknown key names can still identify player data.

#### Scenario: Changed secret remains value-free
- **WHEN** a changed value or path component contains an authentication-bearing value discoverable under a known sensitive key
- **THEN** the comparison still detects the change but the original sensitive value appears nowhere in standard output or standard error

#### Scenario: Protected paths collide
- **WHEN** sensitive-value replacement makes two distinct changed paths indistinguishable
- **THEN** the command emits no comparison report and returns a bounded path-ambiguity error

### Requirement: Strict bounded failure and containment
The command SHALL reject invalid UTF-8, malformed JSON, duplicate object keys, non-finite numbers, unsupported record schema versions, invalid boundary types, files larger than 16 MiB, structures deeper than 128 containers, more than 1,000,000 visited nodes, or more than 100,000 changes. Invalid, unavailable, read, resource-limit, serialization, and output failures SHALL exit `2`, emit no partial or apparently successful JSON report, and write only a fixed bounded diagnostic category and input role to standard error without local paths, JSON fragments, key names, values, exception text, or tracebacks. The command SHALL create no file or directory and SHALL leave canonical fixtures, runtime saves, recorder evidence, legacy sources, and all other repository content unchanged.

#### Scenario: Reject ambiguous or excessive input
- **WHEN** an input contains duplicate keys, non-finite values, excessive size, depth, nodes, or changes
- **THEN** the command exits `2` with a bounded diagnostic and no comparison report

#### Scenario: Preserve all supplied evidence
- **WHEN** comparison succeeds or fails
- **THEN** every supplied input and repository file retains its original bytes and no runtime save, cache, temporary report, or bytecode file is created by the documented invocation

