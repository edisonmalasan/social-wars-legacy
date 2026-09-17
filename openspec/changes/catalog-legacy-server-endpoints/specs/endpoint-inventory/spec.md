## Purpose

Provide a source-grounded inventory of preserved legacy server endpoints that distinguishes registered routes from disabled declarations without executing the application.

## ADDED Requirements

### Requirement: Complete classified endpoint inventory
The inventory SHALL cover every explicit active route in the legacy server, the framework-provided static registration, and the three commented-out auction routes. Each entry SHALL identify its route, handler or framework origin, declared and effective methods, source reference, and registration classification. Disabled declarations SHALL NOT be presented as registered endpoints, and the active alliance placeholder SHALL NOT be described as implemented alliance gameplay.

#### Scenario: Review current route coverage
- **WHEN** the current legacy server is compared with the inventory
- **THEN** all 15 explicit active routes, one implicit static registration, and three disabled auction declarations are represented separately

#### Scenario: Distinguish framework methods
- **WHEN** a route omits explicit methods or declares GET
- **THEN** the inventory distinguishes the default GET and automatic HEAD and OPTIONS behavior from methods explicitly declared by the handler

### Requirement: Source-grounded behavior and evidence
Each inventory entry SHALL describe required and optional input names, route parameters, response branches, state and persistence effects, and supporting source references. Documentation SHALL distinguish source inspection from executed behavioral evidence, label unavailable evidence explicitly, and contain no credential values or private player records. Source review SHALL NOT be presented as gameplay parity or complete command discovery.

#### Scenario: Review a state-changing page
- **WHEN** a maintainer reviews the new-village endpoint
- **THEN** the inventory identifies its village creation and session changes despite its default GET method

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews the player or command endpoint
- **THEN** source-derived effects and available focused evidence are identified without claiming general gameplay or progressed-player parity

### Requirement: Offline inventory verification
A read-only verification command SHALL check catalog structure, unique entries, route and method coverage, source references, and consistency with the readable inventory. It SHALL report agreement with exit 0, catalog drift with exit 1, and invalid inputs or unsupported source syntax with exit 2. Repeated verification of unchanged inputs SHALL produce identical results. Unsupported registration expressions SHALL fail explicitly rather than silently omit routes.

#### Scenario: Detect route drift
- **WHEN** an active route or its declared methods differ from the reviewed inventory
- **THEN** verification exits 1 and identifies the catalog inconsistency

#### Scenario: Reject unsupported registration syntax
- **WHEN** a registration cannot be resolved by the supported static analysis
- **THEN** verification exits 2 without claiming complete coverage

### Requirement: Preservation-safe catalog tooling
Catalog verification SHALL NOT import or execute legacy application modules, invoke route handlers, read runtime saves, contact a network, start a server, open a browser, or execute Flash. The documented invocation SHALL leave repository and supplied input bytes unchanged and create no cache, bytecode, report, or temporary file in the repository. The catalog change SHALL preserve existing handlers and legacy behavior.

#### Scenario: Verify without runtime side effects
- **WHEN** verification succeeds, detects drift, or rejects invalid source
- **THEN** supplied inputs and repository files remain unchanged and no legacy runtime activity occurs
