# Spec Delta

## MODIFIED Requirements

### Requirement: Deterministic asset ID registry
The repository SHALL provide an offline builder that joins every distinct content asset reference from the four reference domains — image paths, item sprites, magic sprites, and sound files — with the committed corpus registry and the M4 conversion and extraction evidence, and writes `tools/asset-registry/asset_ids.json` recording for each reference exactly one runtime status from the closed vocabulary `converted`, `extracted`, `passthrough`, `pending`, `ambiguous`, `missing_source`, together with a runtime path only where one truthfully exists. Image references SHALL be joined by the reference's own path under the committed web root before any basename match, so that a reference whose directory already identifies its file is never reported as a collision; the closed vocabulary is unchanged and `ambiguous` remains available for a reference that neither its path nor a single basename match identifies. The output SHALL reconcile with the committed coverage counts and the conversion and extraction manifests, SHALL be byte-identical on rerun without tree changes, SHALL run under the pinned CPython 3.9.13 interpreter with no new dependencies, and SHALL write only its own output file.

#### Scenario: Map every reference
- **WHEN** the builder runs on the current worktree
- **THEN** each distinct reference of the four domains has exactly one entry with one vocabulary status — the two converted packages recorded as `converted`, sprite and image names absent from the corpus recorded as `missing_source`, corpus-resolved MP3 sounds recorded as `passthrough`, and corpus-resolved sprite SWFs recorded as `extracted` or `pending` per the bitmap-extraction evidence, while the 607 image references record 566 `passthrough` (564 whose file was identified by the reference's own path and 2 by the recorded basename fallback), 9 `extracted`, and 32 `missing_source`, with no image entry left `ambiguous`

#### Scenario: Rerun determinism
- **WHEN** the builder runs twice without tree changes
- **THEN** both outputs are byte-identical

#### Scenario: Reconcile with committed evidence
- **WHEN** the output is validated against the committed manifests
- **THEN** per-domain resolved and missing counts equal the committed coverage report, `converted` entries equal the conversion manifest's packages, `extracted` entries name only directories the bitmap-extraction manifest records, and each `missing_source` list equals the coverage missing list for its domain

#### Scenario: Build without side effects
- **WHEN** the builder succeeds or fails
- **THEN** every content, corpus, conversion, and legacy source byte is unchanged and only `asset_ids.json` is created or replaced