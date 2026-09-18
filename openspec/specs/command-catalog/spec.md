# Command Catalog Specification

## Purpose

Provide a source-grounded inventory of preserved legacy dispatcher commands that distinguishes handled commands from the unhandled fallthrough and records client trust without executing the application.

## Requirements

### Requirement: Complete classified command inventory
The inventory SHALL cover the `command.php` envelope contract, every named dispatcher branch in the legacy command module, and the unhandled-command fallthrough. Each entry SHALL identify its command name, domain, positional argument shape, and dispatch classification. Unhandled names SHALL NOT be presented as implemented behavior, and debug or time-manipulation commands SHALL be labeled as never valid on a production client path. (The proposal estimated 64 named branches; source truth is 63 — `push_dead_unit` is an engine helper, not a dispatcher branch.)

#### Scenario: Review current dispatch coverage
- **WHEN** the current legacy dispatcher is compared with the inventory
- **THEN** all 63 named commands and the unhandled fallthrough are represented separately

#### Scenario: Distinguish the envelope from commands
- **WHEN** a maintainer reviews a batched request
- **THEN** the envelope fields, per-command tuple shape, and pre-dispatch resource application are identified apart from any single command

### Requirement: Source-grounded behavior and evidence
Each inventory entry SHALL describe argument names and shapes, client-sent resource effects, state reads, state writes, persistence effects, client-trusted fields with security concerns, supporting source references, observed fixtures where they exist, and migration status. Documentation SHALL distinguish source inspection from executed behavioral evidence, label unavailable evidence explicitly, and contain no credential values or private player records. Source review SHALL NOT be presented as gameplay parity or complete command discovery.

#### Scenario: Review a client-trusted path
- **WHEN** a maintainer reviews a command with client-sent effects
- **THEN** the inventory identifies which inputs the legacy server trusts, including pre-dispatch resource deltas, cash effects, and timestamp manipulation

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a command without focused evidence
- **THEN** the entry states that only source inspection supports it and names the four commands with replay evidence as the exception

### Requirement: Offline inventory verification
A read-only verification command SHALL check catalog structure, unique entries, command and envelope coverage, source references, and consistency with the readable inventory. It SHALL report agreement with exit 0, catalog drift with exit 1, and invalid inputs or unsupported source syntax with exit 2. Repeated verification of unchanged inputs SHALL produce identical results. Unsupported dispatch expressions SHALL fail explicitly rather than silently omit commands.

#### Scenario: Detect command drift
- **WHEN** a dispatcher branch or its argument handling differs from the reviewed inventory
- **THEN** verification exits 1 and identifies the catalog inconsistency

#### Scenario: Reject unsupported dispatch syntax
- **WHEN** a branch cannot be resolved by the supported static analysis
- **THEN** verification exits 2 without claiming complete coverage

### Requirement: Preservation-safe catalog tooling
Catalog verification SHALL NOT import or execute legacy application modules, invoke command handlers, read runtime saves, contact a network, start a server, open a browser, or execute Flash. The documented invocation SHALL leave repository and supplied input bytes unchanged and create no cache, bytecode, report, or temporary file in the repository. The catalog change SHALL preserve existing handlers and legacy behavior.

#### Scenario: Verify without runtime side effects
- **WHEN** verification succeeds, detects drift, or rejects invalid source
- **THEN** supplied inputs and repository files remain unchanged and no legacy runtime activity occurs
