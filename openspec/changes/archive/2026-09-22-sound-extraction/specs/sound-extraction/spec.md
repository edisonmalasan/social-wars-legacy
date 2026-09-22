## Purpose

Provide verbatim MP3 payload extraction with characteristics validation so embedded game audio exists as standalone files without decoding, playback, or Flash involvement.

## ADDED Requirements

### Requirement: Verbatim MP3 frame extraction
The tool SHALL re-walk DefineSound tags in the inspected source file, validate format nibble 2 with sane rate/size/type characteristics, slice each payload from its first `FF Ex` frame sync to payload end, and SHALL write one `.mp3` per character ID under `assets/converted/sounds/`. Sync offsets SHALL be uniform at 9 or fail as drift.

#### Scenario: Extract the measured sounds
- **WHEN** the extractor runs on the current corpus
- **THEN** 27 MP3 files are written with per-sound digests, and reruns are byte-identical

#### Scenario: Reject a shifted sync
- **WHEN** a sound payload's first frame sync is anywhere but offset 9
- **THEN** validation fails identifying the sound without writing outputs

### Requirement: Extraction manifest and status overlay
The tool SHALL write `extraction.json` with per-sound source tag, characteristics, sync offset, output digest, and byte counts, plus `statuses.json` mapping the 27 registry paths to `extracted`. Registry, coverage, and inspection outputs SHALL remain untouched.

#### Scenario: Review extraction provenance
- **WHEN** a maintainer reads the extraction manifest
- **THEN** every output byte is traced to its source tag offset with a matching digest

#### Scenario: Preserve registry bytes
- **WHEN** extraction succeeds
- **THEN** the registry, coverage, and inspection files are byte-identical to before the run

### Requirement: Validation and round-trip evidence
The tool SHALL validate format nibbles, sync uniformity, characteristics, schema fields, and determinism. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing outputs only on success.

#### Scenario: Reject a non-MP3 sound
- **WHEN** a DefineSound tag carries any format nibble other than 2
- **THEN** validation fails explicitly identifying the sound and format

#### Scenario: Prove outputs match inputs
- **WHEN** extraction outputs are re-derived in memory
- **THEN** payload slices, digests, and counts are recomputed equal before any write

### Requirement: Preservation-safe extraction tooling
The tool SHALL NOT decode audio to samples, play back, transcode, convert, relocate, or modify any source asset; SHALL NOT use Flash, browser, network, server, or subprocess execution; and SHALL write only converted MP3s plus the two manifest files on success. Converted outputs SHALL live separately under `assets/converted/`.

#### Scenario: Extract without source side effects
- **WHEN** the extractor succeeds or fails
- **THEN** every source asset remains byte-identical and only converted outputs plus manifests are created or replaced
