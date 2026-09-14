## Purpose

Define contained replay of a bounded subset of recorded legacy command transactions so the preserved dispatcher can be checked against complete observed state boundaries without touching runtime saves.

## ADDED Requirements

### Requirement: Explicit eligible recorder evidence
The replay command SHALL accept exactly one explicitly named regular UTF-8 JSON file through `replay --record <file>`. It SHALL require an exact integer recorder schema version `1`, POST to the recorded command route, object-root available `before` and `after` states, coherent player correlation, an object command envelope, and at most 256 positional commands. Each command SHALL have an in-range non-boolean integer map index, a command name, a list of arguments, and exactly eight finite non-boolean numeric resource deltas. Only `complete_tutorial`, `level_up`, `ping`, and `set_variables` SHALL be eligible; their argument shapes SHALL be validated, except that an empty `level_up` argument list SHALL remain eligible only as a recorded command-phase `IndexError` case. Execution-relevant redaction placeholders, unsupported commands, unavailable boundaries, parse-phase records, snapshot or response failures, and incoherent outcome/error/response metadata SHALL be rejected before legacy execution. Unknown state fields and unknown non-execution metadata SHALL remain valid.

#### Scenario: Accept a supported successful record
- **WHEN** an operator supplies a coherent recorder-v1 success record containing only supported commands and complete boundaries
- **THEN** the command replays exactly that ordered batch from the supplied before-state

#### Scenario: Accept the supported partial-failure boundary
- **WHEN** a coherent command-phase failure record contains `level_up` with one level followed by `level_up` with no argument and records `IndexError`
- **THEN** the batch remains eligible so replay can test its partial in-memory mutation and absent persistence

#### Scenario: Reject unavailable or unsupported evidence
- **WHEN** a record lacks an available complete boundary, describes another failure phase, contains an unsupported command, exceeds 256 commands, or contains redacted execution data
- **THEN** replay exits as unavailable or unsupported without invoking legacy code or emitting a replay report

### Requirement: Pinned isolated legacy execution
Replay SHALL verify the required legacy source and content closure against immutable Git blobs from preservation baseline `e8c98a03c902eba70323538dc5d4eaba2f2927a1`, permitting only CRLF/LF checkout conversion for textual files, before copying only that reviewed closure into external disposable storage. It SHALL execute the original dispatcher in a separate Windows x64 CPython 3.9.13 child using isolated mode with bytecode disabled, a minimal environment, a fixed child-only sentinel clock, a safe internal player alias, an explicitly seeded in-memory before-state, and save persistence redirected to disposable storage. It SHALL NOT import `server.py`, load ambient saves, migrate state, reconstruct HTTP authentication or signatures, start a listener, contact a network, open a browser, or execute Flash. Changing the sentinel clock SHALL NOT change an eligible replay result.

#### Scenario: Replay without ambient state
- **WHEN** an eligible record is replayed while repository runtime saves or unrelated environment settings exist
- **THEN** the child uses only the supplied before-state and reviewed pinned oracle closure and leaves ambient state unread and unchanged

#### Scenario: Reject oracle drift
- **WHEN** a required oracle source or content file is missing, linked, unpinned, or differs from its recorded Git blob beyond line-ending conversion
- **THEN** replay exits before child execution with a bounded provenance diagnostic

#### Scenario: Prove clock independence
- **WHEN** the same eligible record is replayed with either of two controlled sentinel values in focused verification
- **THEN** the resulting complete state and normalized outcome are identical

### Requirement: Complete boundary and persistence comparison
Replay SHALL execute commands in recorded order using the original dispatcher and compare the complete resulting in-memory state with the supplied recorded after-state using `structural-json-types-v1` semantics. It SHALL separately compare normalized outcome, response contract, and persistence behavior. A successful batch SHALL complete with the fixed legacy route response and SHALL persist a disposable save whose complete state equals replay memory. The supported `IndexError` batch SHALL retain mutations performed before the exception, SHALL stop before trailing commands, and SHALL produce no disposable persisted save. These observations SHALL describe isolated replay behavior only and SHALL NOT claim that a recorded failure was historically persisted.

#### Scenario: Match a successful boundary
- **WHEN** the supported batch reproduces the complete after-state, success outcome, response contract, and successful disposable persistence
- **THEN** replay reports a match and exits `0`

#### Scenario: Match a partial command failure
- **WHEN** replay reproduces the recorded command-phase `IndexError`, complete partial after-state, stopped ordering, null failure body, status `500`, and absent persistence
- **THEN** replay reports a match and exits `0` without rolling back the partial in-memory mutation

#### Scenario: Report a boundary mismatch
- **WHEN** replay completes but any complete state, outcome, response, or persistence comparison differs
- **THEN** replay reports a difference and exits `1`

### Requirement: Deterministic value-free private report
A completed replay SHALL emit exactly one JSON report with schema version `1`, policy `legacy-command-replay-v1`, replay result `match` or `different`, a nested state comparison following the durable structural state-diff schema, and value-free `equal` or `different` outcome, response, and persistence comparisons. The report SHALL contain no record values, command arguments, resource deltas, response or error text, filenames, player IDs, hashes, timestamps, durations, random IDs, source paths, legacy prints, or machine metadata. Serialization SHALL be ASCII-escaped UTF-8 JSON with sorted keys, two-space indentation, LF line endings, and one final newline. Sensitive values collected from the complete input record and actual replay state SHALL protect reported path components; protected-path collisions SHALL fail rather than merge changes. Reports SHALL remain classified as private evidence.

#### Scenario: Repeat a replay
- **WHEN** identical eligible evidence is replayed repeatedly against the unchanged pinned oracle
- **THEN** it emits byte-identical reports and the same exit status

#### Scenario: Protect replay-created sensitive paths
- **WHEN** a replayed result creates a changed path containing a known sensitive value
- **THEN** the path remains detectable while the original sensitive value appears nowhere in standard output or standard error

### Requirement: Bounded failure and repository containment
Each input SHALL be limited to 16 MiB, JSON structures to 128 container levels and 1,000,000 visited nodes, state changes to 100,000 entries, command batches to 256 entries, child result data to 32 MiB, and child wall time to 30 seconds. Invalid input, unavailable or unsupported evidence, provenance drift, ambiguous protected paths, resource limits, child crash or timeout, unexpected legacy exception, dependency failure, persistence inconsistency, cleanup failure, serialization failure, and output failure SHALL exit `2`, emit no apparently successful replay report, and write only a fixed bounded category to standard error without paths, values, legacy output, exception text, or traceback. Handled success and failure SHALL leave supplied evidence, repository sources, canonical fixtures, runtime saves, recorder output, and all other repository content byte-identical; it SHALL create no repository cache, bytecode, report, or temporary file and SHALL clean its external disposable storage.

#### Scenario: Contain successful and failed replay
- **WHEN** replay matches, differs, rejects input, reproduces the supported exception, or encounters a child failure
- **THEN** every repository and supplied-evidence byte remains unchanged and no repository artifact or runtime process remains

#### Scenario: Bound a stalled child
- **WHEN** isolated legacy execution exceeds 30 seconds or its result exceeds 32 MiB
- **THEN** replay terminates that child, cleans handled disposable state, emits a bounded category, and exits `2`

### Requirement: Honest evidence classification
Replay documentation SHALL distinguish controlled recorder-test transactions from historical player observations, identify the exact four-command eligibility set, state that sanitized records cannot reconstruct original secrets, and state that the pinned oracle proves the executed source rather than the historical source of an unproven record. It SHALL identify clock-dependent and unsupported commands, authentic progressed-player coverage, raw HTTP parity, general persistence parity, and gameplay parity as unavailable or unverified.

#### Scenario: Review replay scope
- **WHEN** a maintainer reviews replay output or documentation
- **THEN** supported controlled evidence, unsupported command families, source provenance, sanitization limits, and unverified parity claims are explicitly distinguishable
