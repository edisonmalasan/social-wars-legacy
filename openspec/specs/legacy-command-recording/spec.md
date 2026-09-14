# Legacy Command Recording Specification

## Purpose

Define safe, reproducible observation of legacy command transactions so request, response, and complete state boundaries can become preservation evidence without changing game behavior.

## Requirements

### Requirement: Explicit opt-in recording
Legacy command recording SHALL be disabled when no recording destination is configured. Enabling recording SHALL require an explicit destination that is outside the repository tree, and invalid destinations SHALL be rejected without writing into legacy saves, canonical fixtures, source assets, or tracked project paths.

#### Scenario: Run with recording disabled
- **WHEN** a legacy command request runs without a configured recording destination
- **THEN** the request follows the existing command and persistence path without creating recorder output

#### Scenario: Reject an unsafe destination
- **WHEN** recording is configured to write inside the repository tree
- **THEN** the recorder reports the unsafe configuration and creates no evidence file there

### Requirement: Complete command transaction evidence
For each observed `command.php` request, the recorder SHALL capture the HTTP method and path, safe player correlation, sanitized parsed command batch, complete player state immediately before legacy command execution, complete player state immediately after execution or failure, response status and body when produced, outcome classification, execution duration, schema version, and a unique record identifier. A session identifier SHALL be recorded only when the command path actually uses one and it can be represented without retaining an authentication secret.

#### Scenario: Record a successful command transaction
- **WHEN** recording is enabled and a valid command request completes
- **THEN** one record contains the parsed commands, exact complete before and after states, returned response status and body, success outcome, duration, and correlation metadata

#### Scenario: Record a failed command transaction
- **WHEN** recording is enabled and request parsing or command execution raises an error
- **THEN** one record contains the available request and state boundaries, a failure classification, and non-secret error metadata while the original error behavior remains unchanged

### Requirement: Behavior-preserving observation
Recorder enablement, snapshotting, sanitization, and evidence persistence SHALL NOT change command ordering, resource application, in-memory state mutation, save persistence, HTTP response semantics, or exception propagation. Recorder-internal failures SHALL be reported explicitly but SHALL NOT replace or suppress the legacy command result or error.

#### Scenario: Compare disabled and enabled behavior
- **WHEN** the same controlled command transaction is executed once with recording disabled and once with recording enabled
- **THEN** its returned result and resulting player-save bytes are identical apart from recorder output

#### Scenario: Evidence persistence fails
- **WHEN** the recorder cannot serialize or atomically persist an evidence record
- **THEN** it emits an actionable diagnostic and preserves the legacy response, exception, and state outcome

### Requirement: Sensitive-value exclusion
Recorder output SHALL omit or replace authentication-bearing request values, including the legacy user key, access token, command data signature, cookies, and authorization headers. Sanitization SHALL occur before any evidence record is serialized or written.

#### Scenario: Record a request containing credentials
- **WHEN** a command request includes authentication-bearing form fields, headers, cookies, or parsed payload values
- **THEN** none of their original values appear anywhere in the persisted record

### Requirement: Durable contained records
Each transaction SHALL be persisted as one deterministic-schema JSON record using an atomic same-directory replacement so readers never observe a partial record. Recorder writes SHALL be confined to the configured destination, and record filenames SHALL remain collision-safe across multiple requests.

#### Scenario: Persist a complete record atomically
- **WHEN** evidence persistence succeeds
- **THEN** the configured destination contains one complete schema-valid JSON record and no leftover temporary file

#### Scenario: Record multiple requests
- **WHEN** multiple command requests are observed
- **THEN** each request has a distinct record and no earlier evidence is overwritten
