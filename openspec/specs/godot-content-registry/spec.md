## Purpose

Give the Godot client a canonical, manifest-verified read-only registry of the normalized content package and an asset ID registry that maps every content asset reference to the modern runtime asset it resolves to, or an explicit status when none truthfully exists.

## Requirements

### Requirement: Canonical content registry loading
The client SHALL provide a `ContentRegistry` autoload that loads the committed normalized content package read-only from the repository root, driven entirely by `packages/game-content/manifest.json`: every file the manifest records as an output (22 files across the root section and the nine extension sections) SHALL be read, and its byte count and SHA-256 SHALL be verified against the manifest entry before the file is used. A missing, altered, or unparseable output SHALL fail the load with an explicit error naming that file, and no partial content SHALL be served from a damaged package. The registry SHALL NOT write into the content package and SHALL NOT reference legacy protocol, network, or Flash-related primitives.

#### Scenario: Load the canonical package
- **WHEN** the registry loads the committed content package
- **THEN** all 22 manifest outputs verify against their recorded byte counts and SHA-256 digests, every domain parses to its recorded entry counts (470 buildings, 429 units, 91 quests, 607 images, 139 sounds, 105 globals), and the package bytes are unchanged afterward

#### Scenario: Fail closed on altered content
- **WHEN** loading is attempted against a deliberately altered or missing copy of a manifest output
- **THEN** the load fails with an error naming that file and no domain is served from the damaged package

#### Scenario: Read-only containment
- **WHEN** a verification run loads the registry end to end
- **THEN** the SHA-256 directory digest of `packages/game-content/` is identical before and after, and no registry script contains a legacy protocol, network, or Flash-related token

### Requirement: Domain indexing and lookup
The registry SHALL index each domain's entries by `legacy_id`, SHALL reject a duplicate `legacy_id` within a domain at load time with an error naming that domain, and SHALL expose lookups — the domain list, existence check, entry retrieval, entry count, domain id enumeration, and the package content fingerprint — that return an explicit not-found result for an unknown domain or reference rather than a null or guessed value. Domain id enumeration SHALL report the committed index order rather than a collation of the identifier strings, because the identifiers are digit strings and a lexicographic sort would interleave them.

#### Scenario: Look up known definitions
- **WHEN** lookups ask for known `legacy_id` values in several domains (a building, a quest, a sound)
- **THEN** each returns the exact stored entry and the reported count for its domain matches the manifest-verified entry total

#### Scenario: Report unknown references explicitly
- **WHEN** a lookup names an unknown domain or an unknown `legacy_id`
- **THEN** the result explicitly reports not-found, and the registry state is unchanged

#### Scenario: Reject duplicate identifiers
- **WHEN** an altered copy of a domain contains a repeated `legacy_id`
- **THEN** the load fails with an error naming that domain and no partial index is exposed

#### Scenario: Enumerate a domain's identifiers
- **WHEN** a caller asks a loaded registry for the legacy ids of a domain it did not
  hard-code
- **THEN** the registry returns those ids in the committed order they were indexed in,
  their count equals the domain's reported entry count, and the result comes from the
  index built during the manifest-verified load, so a consumer enumerates verified content
  instead of re-reading the committed file behind the registry's back

#### Scenario: Report an unknown domain when enumerating
- **WHEN** an enumeration names a domain that is not loaded
- **THEN** the result explicitly reports not-found with an empty list and a message naming
  the domain, never a guessed empty enumeration presented as a loaded one

### Requirement: Deterministic asset ID registry
The repository SHALL provide an offline builder that joins every distinct content asset reference from the four reference domains — image paths, item sprites, magic sprites, and sound files — with the committed corpus registry and the M4 conversion and extraction evidence, and writes `tools/asset-registry/asset_ids.json` recording for each reference exactly one runtime status from the closed vocabulary `converted`, `extracted`, `passthrough`, `pending`, `ambiguous`, `missing_source`, together with a runtime path only where one truthfully exists. The output SHALL reconcile with the committed coverage counts and the conversion and extraction manifests, SHALL be byte-identical on rerun without tree changes, SHALL run under the pinned CPython 3.9.13 interpreter with no new dependencies, and SHALL write only its own output file.

#### Scenario: Map every reference
- **WHEN** the builder runs on the current worktree
- **THEN** each distinct reference of the four domains has exactly one entry with one vocabulary status — the two converted packages recorded as `converted`, sprite and image names absent from the corpus recorded as `missing_source`, corpus-resolved MP3 sounds recorded as `passthrough`, and corpus-resolved sprite SWFs recorded as `extracted` or `pending` per the bitmap-extraction evidence

#### Scenario: Rerun determinism
- **WHEN** the builder runs twice without tree changes
- **THEN** both outputs are byte-identical

#### Scenario: Reconcile with committed evidence
- **WHEN** the output is validated against the committed manifests
- **THEN** per-domain resolved and missing counts equal the committed coverage report, `converted` entries equal the conversion manifest's packages, `extracted` entries name only directories the bitmap-extraction manifest records, and each `missing_source` list equals the coverage missing list for its domain

#### Scenario: Build without side effects
- **WHEN** the builder succeeds or fails
- **THEN** every content, corpus, conversion, and legacy source byte is unchanged and only `asset_ids.json` is created or replaced

### Requirement: Client asset resolution
The registry SHALL load the asset ID registry and resolve an asset reference to its status, returning a runtime path only for statuses that carry one (`converted`, `extracted`, `passthrough`); `pending`, `ambiguous`, and `missing_source` references SHALL be reported with their status and no runtime-path claim; and an unknown reference kind or a reference absent from the registry SHALL fail closed with an explicit error.

#### Scenario: Resolve a converted sprite
- **WHEN** resolution asks for item sprite `0001_house_1_m`
- **THEN** it reports `converted` with the converted building package path, and that path exists on disk

#### Scenario: Resolve a passthrough sound
- **WHEN** resolution asks for a sound reference whose corpus MP3 exists
- **THEN** it reports `passthrough` with the source file path and its recorded SHA-256

#### Scenario: Distinguish unavailable from unknown
- **WHEN** resolution asks for a known-but-unavailable reference (a `missing_source` sprite) and then for an unknown kind or an absent reference
- **THEN** the known reference reports its status with no runtime path, while the unknown kind or absent reference produces an explicit error

### Requirement: Containment and verification
The change SHALL keep every prior verification green and every guarded byte identical: the Compatibility API guard baseline, the committed first-render evidence, both conversion packages, the three asset-registry manifests, the legacy sources, and the normalized content package SHALL be byte-identical before and after the full verification battery; the updated project-scope test SHALL enforce the grown allow-list and exactly the two allow-listed autoloads while `GameClock`, `Session`, camera, UI-foundation, legacy-protocol, and non-loopback transport tokens remain forbidden; and the builder and its tests SHALL run under the pinned interpreter with the standard library only.

#### Scenario: Scope enforces the new boundary
- **WHEN** the project-scope test runs in the final state
- **THEN** every project file is allow-listed, exactly the `GameApi` and `ContentRegistry` autoloads are registered, and no forbidden token appears in any project script or scene

#### Scenario: Keep M4 and M5 green
- **WHEN** the full verification battery runs in the final state
- **THEN** the first-render verification and the boot verification both exit 0, the Compatibility API guard digests are equal before and after, and the committed first-render report and PNG remain byte-identical

#### Scenario: No guarded bytes move
- **WHEN** fixture, builder, and verification runs have all completed
- **THEN** guard hashes over legacy sources, conversion packages, the registry manifests, and the content package are identical to their pre-change values

### Requirement: Documented commands and assessment record
`AGENTS.md` and the client README SHALL document the exact commands actually executed for the asset ID registry build, its tests, the content-registry verification, and both verification commands, with their purposes and scope limitations, and the roadmap Project Status ledger SHALL record the §19 and §20 delivery with pointers to the committed evidence and the M5 items that remain.

#### Scenario: Record the executed commands
- **WHEN** verification has passed
- **THEN** `AGENTS.md` and the READMEs list those commands as actually run, with their purposes and constraints

#### Scenario: Record the milestone progress
- **WHEN** this change concludes
- **THEN** the ledger states that this change delivers §19 ContentRegistry and §20 asset ID registry, which M5 items remain, and points to the committed evidence
