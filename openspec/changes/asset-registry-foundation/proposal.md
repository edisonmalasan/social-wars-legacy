## Why

M3 normalized all 20 content keys, and every normalized definition that names art or audio carries only a recorded string (item `img_name`, magic `img_name`, sound `file`, images paths) — asset existence was explicitly M4. M4 must therefore start with observation: a complete, validated registry of the on-disk asset corpus joined against those recorded references, so conversion work can be prioritized (roadmap §14) and missing assets are known before any SWF is parsed or converted. Without it, extraction and conversion slices would work blind.

## What Changes

- Add `tools/asset-registry/` with a stdlib-only offline builder/validator that enumerates the worktree asset corpus (by extension, minus excluded dirs), records per-file registry entries (path, size, sha256, extension, directory class, default status `registered`), extracts content asset references from the committed normalized package, joins them with documented per-domain rules, and writes `registry.json` plus `coverage.json` plus a console/JSON report. Round-trip evidence: re-enumeration diffed for byte-identical outputs; coverage rejoin asserted in tests.
- Join rules (proposal-time measurements, implementation must verify): item `img_name` comma-parts resolve as `<stem>.swf` under `assets/sprites/` (862/872 resolve; 10 named missing); magic `img_name` resolves under `assets/magic/` (10/10); sound `file` resolves as `<stem>.mp3` under `assets/sounds/` (138/138 file ids); images paths resolve by basename (575/607, remainder recorded missing with match-tier notes, never rewritten or checked beyond presence).
- Validate: corpus determinism (sorted order, byte-identical reruns), registry schema fields, join-rule conformity, required coverage fields, and failure on excluded-dir leakage. Report referenced-but-missing per domain, present-but-unreferenced counts, and the SWF/jpg/png/mp3 corpus totals.
- Leave all legacy assets, patches, content, and behavior unchanged; write only the two registry files on success; claim no conversion, no dimension/frame knowledge, no Godot rendering.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| On-disk SWF corpus | 1176 files: sprites 862, fx 205, flash 60, characters_2 26, magic 10, images 9, fonts 2, swf 1, externalized 1 |
| Other asset files | jpg 1756, png 143, mp3 140 (worktree-wide; thumbs 1314 jpg derived set included in enumeration with directory class recorded) |
| Item img refs | 872 distinct comma-parts; 862 resolve to `assets/sprites/<stem>.swf`; missing 10 (`0137_spy_academy_m`, `10000_chained_bonus_giant_walker`, `10027_prision`, `10034_chained_hercules_mech`, `10048_cross_dc`, `1011_bad_girl_m`, `982_chained_red_spinner`, `casachina`, `treasure`, `vacaPerdida`) |
| Magic/sound refs | 10/10 magic stems under `assets/magic/`; 138/138 sound file ids as `.mp3` under `assets/sounds/` |
| Images paths | 607 keys; `assets/`+key join 0/607 (web-root-relative form preserved, never rewritten); basename join 575/607 |
| Excluded from corpus | `.git/`, `saves/`, `temp/`, `build/bundle|dist|work`, `new_assets/` (all gitignored); no network, no Flash execution |

## Capabilities

### New Capabilities

- `asset-registry`: Validated on-disk asset registry with content cross-reference coverage, builder/validator, and manifest-grade outputs.

### Modified Capabilities

None.

## Impact

Adds `tools/asset-registry/` (builder/validator, focused tests, README) plus generated `registry.json`/`coverage.json` and `docs/assets/registry.md` links. Uses Python 3.9 standard-library tooling with no dependency upgrade, no server import, no network, no browser, no Flash/SWF execution, no asset mutation, and no Godot code. SWF parsing, symbol/dimension extraction, conversion tooling, and converted buildings/units remain future M4 slices; Godot rendering verification belongs to M5/M6 and is not claimed here.
