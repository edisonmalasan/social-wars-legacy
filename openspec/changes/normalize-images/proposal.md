## Why

Nine M3 slices normalized 19 of the 20 census content keys. The last key is the `images` asset-path index (607 entries, every value the locale string `en`). Normalizing it as a validated path registry closes the census loop to 20/20, gives the future M4 asset pipeline and Godot ContentRegistry a single validated path source, and turns any added/removed path or locale drift into an explicit build failure. It is the smallest possible final content slice: one key, one shape, no references, no layering.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/images.json` (607, one per stored path), a JSON schema (`image-asset`), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, and legacy IDs.
- Coerce per the field-type survey with documented rules: the asset path is preserved verbatim as `legacy_id` (459 leading-slash, 148 relative, never rewritten); the locale must be exactly `en` (fail on any other value as drift); extension distribution (470 jpg, 127 png, 10 swf) recorded with a manifest note — the 10 swf paths are recorded archival references only and never executed here (asset truth and conversion belong to M4).
- Normalize from stored content directly (no patch targets `images`; the builder refuses patch drift and active mods explicitly).
- Validate: key uniqueness and non-emptiness, locale exactly `en`, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped object diffed against the stored object exactly.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity or asset existence.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `images` entries | 607; every value is the locale string `en` (zero exceptions); keys are asset paths (470 jpg, 127 png, 10 swf; 459 leading-slash) |
| Patch interaction | None: no active patch targets `images`; mods pipeline must stay inactive |
| Cross-references | None: keys are file paths and values are locale tags, not content IDs |
| Asset existence | Explicitly unverified: paths are recorded, never checked against disk (M4 owns asset truth); swf paths never execute |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `images-normalization`: Normalized image-asset path registry with schema, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (one normalized file, one schema, builder/validator, manifest `images` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. This completes M3 stored-content coverage at 20/20 census keys; domain model and Godot loading remain future work and this change does not claim them.
