## Purpose

Provide a validated on-disk asset registry joined against normalized content references so conversion work can be prioritized and missing assets are known before any parsing or conversion.

## Requirements

### Requirement: Deterministic asset corpus registry
The tool SHALL enumerate worktree files with asset extensions under all top-level directories except the documented exclusions, and SHALL write an ordered registry with per-file path, size, sha256, extension, directory class, and default status `registered`. Reruns on unchanged trees SHALL be byte-identical.

#### Scenario: Enumerate the measured corpus
- **WHEN** the builder runs on the current worktree
- **THEN** all 1176 SWF files and the jpg/png/mp3 sets are registered with POSIX paths in sorted order, and excluded dirs contribute zero entries

#### Scenario: Rerun determinism
- **WHEN** the builder runs twice without tree changes
- **THEN** both registry outputs are byte-identical

### Requirement: Content cross-reference coverage
The tool SHALL extract asset references from the committed normalized package (item `img_name` parts, magic `img_name`, sound `file`, images paths), join them with the documented per-domain rules, and SHALL write coverage with per-domain resolved/missing counts, missing-name lists, unreferenced-file counts, and corpus totals. The image domain's join SHALL resolve each reference by its own path under the committed web root before falling back to a basename match, and SHALL record the image tiers as path-resolved, fallback-resolved, and missing counts together with the rule text describing that order, replacing the previous basename-only single/collision tiering.

#### Scenario: Review measured joins
- **WHEN** the coverage report is compared with direct reads
- **THEN** sprites resolve 862/872 with the 10 missing names listed, magic 10/10, sounds 138/138 file ids, and the 607 image references resolve 573 by their own path, 2 by the recorded basename fallback, and 32 remain listed as missing

#### Scenario: Surface gaps for prioritization
- **WHEN** a maintainer reads the coverage report
- **THEN** referenced-but-missing names and present-but-unreferenced counts are identified per domain without any asset being modified

#### Scenario: Record the fallback rather than hide it
- **WHEN** the image tiers are written
- **THEN** the fallback-resolved count is recorded separately from the path-resolved count and names
  its members, so a reference whose directory disagrees with the corpus is distinguishable from one
  whose path identified its file directly

### Requirement: Validation and round-trip evidence
The builder SHALL validate corpus determinism, registry/coverage schema fields, join-rule conformity, and exclusion integrity. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing outputs only on success.

#### Scenario: Detect excluded-dir leakage
- **WHEN** an asset file exists under an excluded directory
- **THEN** it never appears in the registry and a dedicated test proves the exclusion

#### Scenario: Prove outputs match inputs
- **WHEN** registry and coverage outputs are re-derived in memory
- **THEN** digests, sizes, joins, and counts are recomputed equal before any write

### Requirement: Preservation-safe asset tooling
The tool SHALL NOT execute, decode, convert, relocate, or modify any asset; SHALL NOT use Flash, SWF, browser, network, server, or subprocess execution; SHALL NOT modify any file under `assets/`, `config/`, `mods/`, saves, or other legacy sources; and SHALL write only the two registry files on success. Outputs SHALL live separately under `tools/asset-registry/`.

#### Scenario: Build without asset side effects
- **WHEN** the builder succeeds or fails
- **THEN** every source asset remains byte-identical and only the two registry outputs are created or replaced
