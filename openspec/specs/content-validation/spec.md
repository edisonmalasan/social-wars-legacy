# Content Validation Specification

## Purpose

Validate the committed normalized content package offline — manifest integrity, schema conformance, and cross-domain reference integrity — so a consumer such as Godot can load game definitions that have been checked as a whole, independently of any rebuild.

## Requirements

### Requirement: Standalone read-only validator with a three-exit contract
The repository SHALL provide an offline content validator over the committed package (`packages/game-content/manifest.json`, every normalized output the manifest records, and the schema files), implemented with the Python 3.9 standard library only. It SHALL read exactly that package and nothing else — no legacy sources, saves, clock, network, or Flash — SHALL never import the builders or any legacy module, and SHALL write nothing in any outcome. The validator SHALL exit 0 with a JSON success report containing per-file entry counts, files verified, and references checked; exit 1 with a `validation-failed` report listing each problem with stable identifiers (check family, file, entry `legacy_id`, field) while writing nothing; and exit 2 on stderr for invalid input or unsupported shape (missing, unreadable, or unparseable file, invalid schema file, or bad usage) without claiming validity.

#### Scenario: Validate the committed package
- **WHEN** the validator runs against the committed package
- **THEN** it exits 0 with a JSON success report whose per-file counts match the actual entries, and no file is written or changed

#### Scenario: Report problems without writing
- **WHEN** any check family fails on a disposable copy of the package
- **THEN** it exits 1 with a `validation-failed` report naming each problem by check family, file, entry, and field, and the package remains byte-identical

#### Scenario: Reject invalid input distinctly
- **WHEN** a manifest-recorded output is missing or unparseable, or a schema file is invalid
- **THEN** it exits 2 on stderr, distinguishes the unusable input, and never prints a validity report

### Requirement: Package structure and manifest integrity
The validator SHALL require that the `normalized/` directory set equals the manifest-recorded output set exactly (22 files — no missing output and no unrecorded file), that the root record and all nine extension sections are present with `schema_version`, a `success` result, and `policy` recorded, that every recorded output's byte count and SHA-256 match the file on disk, and that every documented count key that names output entries matches the actual entry count (provenance-only counts are recorded verbatim and are not file-verifiable).

#### Scenario: Detect an unrecorded output
- **WHEN** `normalized/` contains a file the manifest does not record as an output
- **THEN** validation fails with exit 1 naming the unrecorded file

#### Scenario: Detect altered output bytes
- **WHEN** an output's bytes no longer match its recorded byte count or SHA-256
- **THEN** validation fails with exit 1 naming that output and the digest mismatch

#### Scenario: Detect count drift
- **WHEN** a count key that names an output's entries disagrees with the actual entry count in that file
- **THEN** validation fails with exit 1 naming the section, count key, and both values

### Requirement: Schema conformance over the documented subset
Every entry of every schema-backed file (21 files against their 21 schemas) SHALL pass the same schema subset the builders document and enforce: required fields, type unions in which a boolean is never an integer, `const` (including `kind`), `enum`, `minimum`, `minItems`/`minProperties`, `propertyNames`, `additionalProperties: false`, and nested object gates. The schema-less special file SHALL instead carry its documented gates: exactly one entry, `legacy_id` `925`, and the exact recorded `special_note`.

#### Scenario: Enforce every schema-required field
- **WHEN** any schema-required field is removed from any entry of any schema-backed file
- **THEN** validation fails with exit 1 naming the file, entry, and missing field

#### Scenario: Enforce type and value gates
- **WHEN** an entry carries a wrong type, a `const`/`enum`/`minimum` violation, an unknown property, or a property name outside its allowed set
- **THEN** validation fails with exit 1 naming the file, entry, and offending field

#### Scenario: Gate the schema-less special
- **WHEN** `specials.json` contains a second entry, or its entry's `legacy_id` or `special_note` differs from the documented values
- **THEN** validation fails with exit 1 naming the deviation

### Requirement: Dependency and reference integrity
The validator SHALL enforce per-file `legacy_id` uniqueness and distinctness across the 900-entry items union, SHALL resolve every cross-domain reference edge against its target domain — items `upgrades_to`/`trains_ids` (excluding the `-1`/`0` sentinels), `inventory_ids` object keys against the inventory domain, collections `item_refs`/`prize_refs`, `level_ranking_reward` and `unit_collection_categories` `unit_refs`, darts `item_refs`/`extra_ref`, offers `item_refs`, and categories `sub` parents — and SHALL require each derived reference field to match what its stored source field derives, not merely to resolve. The two pinned offer anomalies SHALL stay exactly as recorded, and no additional unresolving offer leaf SHALL appear.

#### Scenario: Keep identifiers unique
- **WHEN** two entries in one file share a `legacy_id`, or the items union repeats an id across files
- **THEN** validation fails with exit 1 naming the file (or union) and the duplicated id

#### Scenario: Resolve every reference
- **WHEN** any reference points outside its target domain beyond the documented sentinels
- **THEN** validation fails with exit 1 naming the entry, field, and unresolved value

#### Scenario: Detect derived-reference drift
- **WHEN** a stored reference field no longer matches what its source field derives, even when the stored value would still resolve
- **THEN** validation fails with exit 1 naming the entry, field, derived value, and stored value

#### Scenario: Preserve the pinned offer anomalies
- **WHEN** either pinned offer anomaly value changes, or any other offer leaf fails to resolve
- **THEN** validation fails with exit 1 naming the offer and leaf

### Requirement: Containment and documented evidence
The validator SHALL not read or write legacy sources, saves, `config/`, `mods/`, or any M4/M5 evidence, SHALL not contact a network or start a server, and SHALL leave the committed package byte-identical and file-set-identical in every outcome. The package README and `AGENTS.md` SHALL document the validator's exact commands, exit codes, and evidence classification only after those commands have actually been executed, and SHALL state the limits: schema, manifest, and reference conformance of the committed package — not served-byte equality, content validity, asset existence, gameplay parity, or progressed-player coverage.

#### Scenario: Run without side effects
- **WHEN** the validator and its test suite run, succeed or fail
- **THEN** the package's file set and every file's bytes are identical before and after, and no file is created outside temporary test directories

#### Scenario: Document executed commands
- **WHEN** a maintainer reads the package README and `AGENTS.md`
- **THEN** they find the validator command, its test-suite command, exit codes, and the evidence limits above
