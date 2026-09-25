## Context

The building converter assembles static packages from top-level shapes; units need per-sprite animation inventory because their art lives in nested labeled timelines. Direct reads show the elephant file is the smallest such library: a 550×400 @ 30 fps one-frame movie whose root places exactly one character (`DefineSprite` 63, exported as `10033_wild_elephant`), with 7 `DefineSprite` definitions, 28 shapes, and 28 bitmaps. All five Spanish labels (QUIETO/ANDAR/ATAQUE/MUERTE/PICAR) are `FrameLabel` tags inside sprite 63 at frames 1/6/11/16/21; declared sprite frame counts (20/20/20/20/20/7/29) each equal the observed `ShowFrame` count. This design scopes the sixth M4 slice: one unit, inventoried per sprite, playback deferred. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Converted package `assets/converted/units/10033_wild_elephant/` with `package.json` (identity, unit definition ref, provenance, frame data, symbols, per-sprite animation states, bitmap outputs with digests) plus bitmap copies.
- Stdlib-only per-sprite inventory reusing the building shape parser by local sibling import (no code duplication), with the same no-tessellation boundary.
- A shared `conversions.json` package entry plus `converted` statuses merge; bitmap-fill resolution (referenced fills only) and content-ref uniqueness enforced.
- Byte-align the shared style parser after the `FillStyleArray` so the elephant's shapes parse, with the existing house package re-verified byte-identical.
- A neutral `conversion-v1` manifest envelope with per-package policies so both converters can share the manifest deterministically.
- Focused tests on synthetic sprite timelines and the real file, plus determinism, order-independence, and containment.

**Non-Goals:**
- No animation playback, blending, or state-machine interpretation; labels are names only.
- No edge tessellation, rasterization, matrix/script interpretation; placement optional payloads (matrix, ratio, name, clip data) are skipped, not decoded.
- No remaining units (separate future slices driven by M6 needs).
- No registry/coverage/inspection/extraction-manifest mutation.
- No Godot code or rendering verification of any kind.
- No claim of M4 exit; render verification belongs to M5/M6.

## Decisions

- **Reuse by import, not duplication.** `convert_unit.py` inserts its own directory on `sys.path` and imports the building converter's bit-reader, style parser, record counter, schema validator, digest helpers, and tag walkers. Rationale: one parsing implementation; alternative duplication rejected as divergence risk.

- **Sprites are animation states.** Each `DefineSprite` becomes one animation entry (sprite id, declared frame count, its own labels with frame indices, placements with frame/depth/referenced character, removals, and the shape/bitmap references derived from its directly placed shapes); the root timeline is recorded the same way as a `main` entry; root-level shape definitions (if any) attach to `main`. Label-to-sprite attribution comes from parsing `FrameLabel` tags inside each sprite body (all five land in sprite 63), never from filenames or inspection's merged label lists. The `symbols` field records `{id, name}` pairs parsed from `SymbolClass` so consumers can link the exported name to the inventoried sprite id (deliberate divergence from the building package's committed names-only list, which stays unchanged). Placement decode is depth-first: `flags UI8`, `depth UI16`, then `character UI16` when `0x02` — order confirmed independently by Ruffle's `read_place_object_2_or_3` (depth read first) and Haxe's `format/swf/Reader.hx`, and empirically by corpus scoring (depth-first places 100% of character ids displayable and covers every `RemoveObject2` depth; character-first reaches 0–51% and zero remove coverage). `RemoveObject2` payload is the depth only; a label's frame index is the number of preceding `ShowFrame` tags plus one. Unsupported timeline control tags, undefined character references, and declared-versus-observed frame-count mismatches fail closed.

- **Byte-aligned style arrays.** The shared `parse_style_arrays` currently reads the line-style count immediately after the fill styles, so any file whose fill array ends mid-byte raises `shape byte misaligned`; the elephant fails on 19 of 28 shapes under the byte-strict read while aligning after the `FillStyleArray` parses 28 of 28. Decision: align to a byte boundary after the fill array (before the line count). Aligning after each individual fill is observationally identical on every measured shape (non-final fills already end byte-aligned), so the array-level align is the smallest change that stays fail-closed elsewhere. The house's single fill already ends aligned, so the fix is a no-op for it; the house package is regenerated and its `package_sha256` compared byte-for-byte to prove no behavior drift.

- **Placeholder fills are recorded, referenced fills must resolve.** 25 of the 28 elephant shapes carry a first fill with `bitmap_id 65535` that no shape record references; every shape's referenced fill (the last style, reached through the record state's fill index) is a real bitmap id, and the 28 referenced ids are exactly the 28 extracted JPEG3 outputs (a bijection). Decision: the converter collects fill indices activated by `StateChange` records and validates referenced fills only — each referenced fill must be in range and resolve to an extraction output with a `bitmap_id` other than 65535. Unreferenced 65535 fills are recorded verbatim in `package.json` as source-faithful data and excluded from resolution; a referenced 65535 fill, an out-of-range index, or an unresolvable referenced id fails validation without writes.

- **Small domain module.** New logic lives in `convert_unit.py`, not `command.py`-style dispatch.

- **Package by directory, manifest globally (neutral envelope).** The committed `conversions.json` hardcodes policy `building-conversion-v1` at the envelope and `convert_building.py` rewrites the file with only its own entry, so a second tool cannot share it as-is, and any last-writer-wins policy makes the file's bytes depend on rerun order (violating determinism). Decision: migrate the envelope to `policy: "conversion-v1"` with per-package entries that each carry `policy` (`building-conversion-v1` / `unit-conversion-v1`) and their own `output_bytes`; `counts` becomes `{packages, output_bytes}` recomputed as entry count and byte sum so either tool reproduces identical bytes regardless of which ran last; `inputs` keys are merged per domain and preserved; `packages` entries are sorted by `directory`. Both converters read the existing manifest, preserve foreign entries and input keys verbatim, replace their own entry (keyed by `directory`), stamp the envelope policy, and validate before writing. The building converter performs the one-time migration: a legacy `building-conversion-v1` envelope is accepted only while its sole entry matches the building's own `legacy_id` (regenerated fresh), and any foreign legacy entry fails closed. The unit converter requires a `conversion-v1` envelope and fails closed with a clear message otherwise. Rejected alternatives: keeping the building constant (the manifest would mislabel itself once a unit entry exists), last-writer policy (order-dependent bytes), per-kind manifests (fragmented Godot-import readiness tracking), and dropping `output_bytes` (counts could not be recomputed from preserved entries).

- **Extraction outputs are a documented prerequisite, not a converter dependency change.** Like the building converter, `convert_unit.py` reads the extracted bitmap files (gitignored under `assets/converted/images/`) and verifies them against the committed `image_extraction.json`. The elephant's directory does not exist in a fresh working tree, so verification runs the already-verified `extract_images.py` first; that run writes only ignored bitmap outputs, but it also rewrites the tracked `statuses.json` (downgrading already-`converted` entries to `extracted`) and regenerates `image_extraction.json` with identical values in LF form, so the restore step below covers it too. Ordering matters for byte-identical reruns: `content_version` hashes the raw worktree bytes of the content file plus `inspection.json` and `image_extraction.json`, and the committed digests reproduce only with the generated forms in place — `buildings.json`/`units.json` LF (as `build_items.py` writes them) and both registry manifests in their `core.autocrlf=true` checkout form (CRLF), the combination that uniquely matched the committed `buildings_content_version`. `inspect_swf.py` and `extract_images.py` rewrite their manifests with LF endings (changing the fingerprint), and `build_items.py` resets `packages/game-content/manifest.json`'s other sections, so the documented sequence is extract → restore forms (delete the file first when only the line-ending form differs, then `git checkout --`; restore `manifest.json` after `build_items.py` and `statuses.json` after an extraction run) → convert. This note is recorded in `tools/asset-registry/README.md` for operators.

## Risks / Unknowns

- **[Shared shape parser]** The alignment fix touches building-slice code; mitigated by regenerating the house package and comparing its digest plus running both focused suites.
- **[Sibling import]** `convert_unit.py` depends on `convert_building.py` internals; acceptable because both live in the same tool directory and the building tests guard the shared surface.
- **[Label attribution]** Frame labels live inside sprite bodies while inspection exposes only file-level merged label lists; attribution is decided by parsing sprite bodies, with the spec's per-sprite scenarios as the check.
- **[Manifest policy migration]** The neutral envelope retroactively touches `conversion.schema.json`, `convert_building.py`, and the committed `conversions.json`; mitigated by the fail-closed legacy rules above and an order-independence test that runs both converters in both orders.
- **[Schema drift]** The new unit package schema must track the building package schema's conventions; decided by mirroring field names and digest format rather than inventing new encodings.

## Migration Plan

1. Implement `convert_unit.py` plus `unit_package.schema.json` against measured elephant values.
2. Apply the shared-parser alignment fix in `convert_building.py`; regenerate the house package and verify its `package_sha256` is unchanged.
3. Migrate the envelope (`conversion.schema.json` const and per-entry fields, merge/preserve semantics in `convert_building.py`); regenerate `conversions.json` so the committed manifest is already `conversion-v1`.
4. Merge the unit package entry and statuses layer; re-run both focused suites plus determinism, order-independence, and containment checks.
5. Retire nothing: the building converter stays in place, gaining only alignment and merge behavior.

## Out of Scope

Rendering in Godot, playback state machines, remaining unit conversions, tessellation, registry regeneration, networked or server-backed conversion, and any change to the legacy corpus or normalized content.
