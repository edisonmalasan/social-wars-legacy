# Asset registry foundation (M4 slice 1: observe and record)

Validated on-disk asset registry joined against normalized content
references, built offline with Python 3.9 standard library only; no new
dependencies, no SWF parsing, no conversion, no asset mutation, no Flash
execution.

## Inputs

- Worktree asset files with extensions `.swf`, `.jpg`, `.jpeg`,
  `.png`, `.mp3`, `.wav`, `.gif`, minus exclusions `.git/`, `saves/`,
  `temp/`, `new_assets/`, `assets/converted/` (generated outputs are
  not source corpus), `build/bundle`, `build/dist`, `build/work`, and
  `apps/` (modern Godot client output — project files and committed
  render evidence are not legacy source corpus).
- Committed normalized outputs: `buildings.json`, `units.json`,
  `specials.json` (`img_name`), `magics.json` (`img_name`),
  `sounds.json` (`file`), `images.json` (`path`).
- `tools/asset-registry/schemas/` (registry, entry, and coverage
  contracts enforced by the builder).

## Join rules

- Item `img_name` comma-parts resolve as `assets/sprites/<stem>.swf`
  (case-sensitive); magic `img_name` as `assets/magic/<stem>.swf`;
  sound `file` as `assets/sounds/<stem>.mp3`.
- Images paths resolve by basename with single/collision/missing
  tiers; the web-root-relative form is preserved, never rewritten.
- Unmatched names are reported (missing lists), never errors; the
  report exists to prioritize conversion work.

## Outputs

- `tools/asset-registry/registry.json`: ordered entries with path,
  size, sha256 (worktree bytes), extension, directory class, and
  default status `registered`.
- `tools/asset-registry/coverage.json`: per-domain resolved/missing
  counts with missing-name lists, basename tiers, unreferenced-file
  counts per directory class, and corpus totals.

## Validation gates (failures exit 1, outputs unwritten)

Unsorted or duplicate paths, negative sizes, malformed digests,
excluded-path leakage, and schema violations. Exit 2 reports invalid
input (missing/unreadable files, unparseable content). Reruns on
unchanged trees are byte-identical.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13). Any working Python 3.9+ standard-library interpreter
should behave identically.

From the repository root:

```bash
python -B tools/asset-registry/build_registry.py
```

## Evidence classification

This tool establishes source-grounded registry consistency for the
worktree asset corpus: enumeration coverage, digest fidelity, join
match rates, and determinism. Hashes identify worktree bytes and are
distinct from the baseline Git-blob hashes owned by
`legacy-manifest.json`. It is evidence of observation, not of parsing,
conversion, asset validity, gameplay parity, or Godot rendering.

## Containment

- Reads only worktree asset files, the six normalized reference
  files, and the three schema files (plus optional
  `--repo-root`/`--out-root` relocation; `--out-root` redirects the
  two written files for testing).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash, never modifies any asset.
- Writes only `registry.json` plus `coverage.json`, and only on
  success. No bytecode (`-B` recommended), no caches, no temporary
  files in the repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_build_registry.py -v
```

---

# SWF static inspection (M4 slice 2: parse and record)

Static inventory of SWF headers, tags, symbols, and embedded assets,
built offline with Python 3.9 standard library (`struct` + `zlib`)
only; no new dependencies, no execution, no conversion, no asset
mutation, no Flash runtime in any form.

## Inputs

- `tools/asset-registry/registry.json` (committed registry; every
  `.swf` entry is inspected).
- `tools/asset-registry/schemas/inspection.schema.json` and
  `inspection_entry.schema.json` (contracts enforced by the inspector).

## Parsing rules

- Headers: `CWS` (zlib) and `FWS` (uncompressed) accepted; `ZWS` and
  any other signature fail closed as drift. Versions must be 1..40.
  Declared header lengths are recorded, never trusted: walks are
  bounded by actual bytes.
- FrameSize RECT bit-decoding yields stage dimensions; frame rate
  (8.8 fixed) and frame count recorded verbatim.
- Tag walks terminate at the End tag or fail identifying the file;
  overruns and truncations fail explicitly. Unknown tag codes are
  recorded by number, never rejected.
- DefineSprite payloads are walked recursively with merged
  inventories; nesting beyond 64 levels fails closed.
- SymbolClass/ExportAssets names, DefineBits/JPEG and DefineSound
  IDs, DoABC/DoAction presence and counts, frame labels, and scene
  counts are recorded verbatim; nothing is interpreted behaviorally.
- Scene data uses variable-length LEB128 integers per the SWF format;
  fixed-width decoding is a known pitfall and is covered by a
  dedicated synthetic test.

## Outputs

- `tools/asset-registry/inspection.json`: per-path entries plus corpus
  statistics (file count, version distribution, scripted-file counts,
  embedded-asset totals, sprite totals and depth).

## Validation gates (failures exit 1, outputs unwritten)

Unreadable or unparseable corpus files, walk termination failures,
signature/version violations, missing registry or wrong registry
policy (exit 2), schema violations, and any determinism difference.
Reruns on unchanged inputs are byte-identical.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13). Any working Python 3.9+ standard-library interpreter
should behave identically.

From the repository root (after the registry build):

```bash
python -B tools/asset-registry/inspect_swf.py
```

## Evidence classification

This tool establishes source-grounded parse consistency for the SWF
corpus: header fidelity, tag inventories, symbol listings, and
script-presence flags across all 1176 files (1,175 with ABC, 0 with
legacy actions). It is evidence of static observation, not of
conversion, timeline semantics, script behavior, asset validity,
gameplay parity, or Godot rendering.

## Containment

- Reads only the committed registry, the two inspection schemas, and
  the registry-listed `.swf` files (plus optional
  `--repo-root`/`--out-root` relocation).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash, never modifies any asset.
- Writes only `inspection.json`, and only on success. No bytecode
  (`-B` recommended), no caches, no temporary files in the repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_inspect_swf.py -v
```

---

# Sound extraction (M4 slice 3: verbatim MP3 extraction)

Verbatim payload extraction for the 27 embedded MP3 sounds (all in
`assets/swf/dynamic2.swf`), built offline with Python 3.9 standard
library only; no new dependencies, no decoding, no playback, no
transcoding, no Flash runtime in any form.

## Inputs

- `tools/asset-registry/inspection.json` (committed inspection; every
  file with `sound_ids` is extracted).
- `tools/asset-registry/schemas/extraction.schema.json` and
  `extraction_sound.schema.json` (contracts enforced by the extractor).

## Slicing rule

DefineSound tags are re-walked; format nibble 2 (MP3) with sane
rate/size/type characteristics is required and anything else fails
closed. Each payload is sliced from its first `FF Ex` frame sync to
payload end; the sync offset must equal 9 for every sound (the measured
uniform invariant) or the build fails as drift. One `.mp3` per
character ID lands under `assets/converted/sounds/`.

## Outputs

- `assets/converted/sounds/<id>.mp3`: 27 verbatim MP3 frames.
- `tools/asset-registry/extraction.json`: per-sound source tag,
  characteristics, sync offset, output digest, and byte counts.
- `tools/asset-registry/statuses.json`: registry-path to `extracted`
  overlay; registry, coverage, and inspection files stay untouched.

## Validation gates (failures exit 1, outputs unwritten)

Non-MP3 formats, shifted or missing syncs, truncated walks, digest
mismatches on re-derivation, duplicate IDs, and schema violations.
Exit 2 reports invalid input (missing inspection, unreadable files,
unparseable content). Reruns on unchanged inputs are byte-identical.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13). Any working Python 3.9+ standard-library interpreter
should behave identically.

From the repository root (after the inspection build):

```bash
python -B tools/asset-registry/extract_sounds.py
```

## Evidence classification

This tool establishes source-grounded extraction consistency for all
27 embedded sounds: payload provenance, characteristics, sync
uniformity, and digest fidelity. It is evidence of verbatim slicing,
not of decoding, playback quality, transcoding, timeline semantics,
gameplay parity, or Godot rendering. MP3 stays MP3 — Godot plays it
natively, so no transcoding is specified.

## Containment

- Reads only the committed inspection, the two extraction schemas,
  and the inspection-listed sounded SWF (plus optional
  `--repo-root`/`--out-root` relocation).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash/audio-decoding libraries,
  never modifies any source asset.
- Writes only converted MP3s plus the two manifest files, and only on
  success. No bytecode (`-B` recommended), no caches, no temporary
  files in the repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_extract_sounds.py -v
```

---

# Bitmap extraction (M4 slice 4: format-faithful image extraction)

Format-faithful extraction for all bitmap payloads (46,425 JPEG3 +
14,364 lossless + 913 plain-JPEG tags), built offline with Python 3.9
standard library only; no new dependencies, no rendering, no JPEG
decoding to pixels, no Flash runtime in any form.

## Inputs

- `tools/asset-registry/inspection.json` (committed inspection; every
  file is re-walked for bitmap tags).
- `tools/asset-registry/schemas/bitmap_extraction.schema.json` and
  `extracted_bitmap.schema.json` (contracts enforced by the extractor).

## Per-family rules

- Plain JPEG (tags 6/21): payload bytes verbatim; JPEGTables spliced
  only when SOI is absent (never observed on real corpus; synthetic
  tests prove the path, manifest records splice counts).
- JPEG3 (tag 35): verbatim `.jpg` plus zlib-decoded alpha as
  grayscale `_alpha.png`; decoded length must equal width×height,
  where dimensions come from a minimal JPEG SOF scan (structure only).
- Lossless ARGB (format 5): zlib pixels mapped ARGB→RGBA as stored
  (no un-premultiplying; documented) into `.png` via the hand-rolled
  writer (signature, IHDR, filter-0 IDAT, IEND with CRCs).
- Lossless colormap (format 3): U8 count prefix outside zlib, palette
  plus stride-padded index rows inside; expanded to RGBA `.png`.
- Any other bitmap format fails closed as drift.

## Outputs

- `assets/converted/images/<swf-stem>/`: bulk `.jpg`/`.png` outputs in
  the ignored build-artifact directory (61k files, ~566 MB — committing
  them is rejected; they regenerate byte-identically from the manifest).
- `tools/asset-registry/image_extraction.json`: per-bitmap source tag,
  family, format, dimensions, output digests, and byte counts.
- `tools/asset-registry/statuses.json`: merged overlay advancing
  extracted files (neutral `asset-statuses-v1` envelope shared across
  extraction slices).

## Validation gates (failures exit 1, outputs unwritten)

Payload structure, zlib integrity, alpha dimension match, PNG re-parse
(signature plus IHDR), JPEG SOI presence, unknown-format refusal,
schema fields, and determinism. Exit 2 reports invalid input (missing
inspection, unreadable files, unparseable content).

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13). Any working Python 3.9+ standard-library interpreter
should behave identically.

From the repository root (after the inspection build):

```bash
python -B tools/asset-registry/extract_images.py
```

## Evidence classification

This tool establishes source-grounded extraction consistency for all
61,702 bitmap payloads: family coverage, dimensional fidelity
(re-parse checked), digest fidelity, and determinism. It is evidence
of byte transport, not of rendering correctness, color judgment,
timeline assembly, gameplay parity, or Godot rendering.

## Containment

- Reads only the committed inspection, the two bitmap schemas, and
  the inspection-listed SWF files (plus optional
  `--repo-root`/`--out-root` relocation).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash, never modifies any source
  asset.
- Writes bulk outputs under ignored `assets/converted/images/` plus
  the committed manifest and statuses merge, and only on success. No
  bytecode (`-B` recommended), no caches, no temporary files in the
  repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_extract_images.py -v
```

---

# First-building conversion (M4 slice 5: package assembly)

Assembled converted package for `0001_house_1_m` (House I) from
inspection data, extraction outputs, the normalized buildings package,
and parsed shape-style records, built offline with Python 3.9 standard
library only; no new dependencies, no tessellation, no rasterization,
no matrix/script interpretation, no Flash runtime in any form.

## Inputs

- `tools/asset-registry/inspection.json` (frame data, symbols).
- `tools/asset-registry/image_extraction.json` plus extracted bitmap
  files (bitmap linkage with digest equality).
- `packages/game-content/normalized/buildings.json` (exactly one
  `img_name` match; placement tiles recorded verbatim).
- `tools/asset-registry/schemas/building_package.schema.json` and
  `conversion.schema.json` (contracts enforced by the converter).

## Parsing boundary

SHAPEWITHSTYLE bounds, fill/line style arrays (solid, gradient stubs,
bitmap fills with IDs plus raw matrices), and edge-record type counts
are parsed; mid-stream NewStyles blocks are parsed into the same
arrays. Matrices stay raw bytes. Edge geometry is counted, never
tessellated. Shape tags outside {2, 22, 32} fail closed.

## Outputs

- `assets/converted/buildings/0001_house_1_m/`: `package.json` plus
  byte-identical bitmap copies (digests must match extraction outputs).
- `tools/asset-registry/conversions.json`: package entries with digests
  under the neutral `conversion-v1` envelope (per-entry `policy` and
  `output_bytes`; foreign entries and input keys preserved so either
  converter yields identical bytes in either order). A legacy
  `building-conversion-v1` envelope migrates only while it holds solely
  the building entry; foreign legacy entries fail closed.
- `tools/asset-registry/statuses.json`: merged overlay marking the
  source path `converted` (neutral `asset-statuses-v1` envelope).

## Validation gates (failures exit 1, outputs unwritten)

Bounds presence, bitmap-fill resolution, content-ref uniqueness, digest
equality, schema fields, envelope policy, and determinism. Exit 2
reports invalid input (missing inspection/extraction/buildings,
unreadable files, unparseable content).

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Programs\Python\Python39\python.exe`
(CPython 3.9.13). Any working Python 3.9+ standard-library interpreter
should behave identically.

From the repository root (after the extraction builds):

```bash
python -B tools/asset-registry/convert_building.py
```

Byte-identical reruns also depend on the worktree line-ending forms of
the fingerprint inputs; see the worktree-form note in the
*First-unit conversion* section below.

## Evidence classification

This tool establishes source-grounded assembly consistency for one
converted building: shape-style fidelity, bitmap linkage, content
linkage, and determinism. It is evidence of package assembly, not of
rendering correctness, visual fidelity, tessellation, gameplay
footprint semantics, or Godot loading. No Godot project is created or
required here.

## Containment

- Reads only the committed inspection, extraction manifest plus bitmap
  files, normalized buildings, the two converter schemas, and the
  source SWF (plus optional `--repo-root`/`--out-root` relocation).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash, never modifies any source
  asset or prior manifest (verified byte-identical after runs).
- Writes only the package directory plus the conversions manifest and
  statuses merge, and only on success. No bytecode (`-B` recommended),
  no caches, no temporary files in the repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_building.py -v
```

---

# First-unit conversion (unit slice: package assembly)

Assembled converted package for `10033_wild_elephant` (normalized unit
`legacy_id` 933, Wild Elephant) from inspection data, extraction
outputs, the normalized units package, and parsed sprite-timeline
records, built offline with Python 3.9 standard library only; no new
dependencies, no tessellation, no rasterization, no matrix/script
interpretation, no Flash runtime in any form.

## Inputs

- `tools/asset-registry/inspection.json` (frame labels and sprite
  count for the source, cross-checked against the parsed timeline).
- `tools/asset-registry/image_extraction.json` plus extracted bitmap
  files (bitmap linkage with digest equality).
- `packages/game-content/normalized/units.json` (exactly one `legacy_id`
  `933` match, `img_name` `10033_wild_elephant`, recorded verbatim and
  no other definition touched).
- `tools/asset-registry/schemas/unit_package.schema.json` and
  `conversion.schema.json` (contracts enforced by the converter).

## Parsing boundary

`DefineSprite` bodies and their timeline tags: `PlaceObject2` decoded
depth-first (`flags UI8`, `depth UI16`, `character UI16` when the
character bit is set), `RemoveObject2` as the depth only, `FrameLabel`
frame indices (preceding `ShowFrame` count plus one), `ShowFrame`
counting, and `End`. Frame labels are recorded as names with their
frame indices only — an inventory for playback, never playback or
state-machine semantics of their own. `SymbolClass` id-name pairs and
the root timeline are recorded as `symbols` and `main`. Shape records
come from the shared shape-style parser (bounds, fill/line arrays,
edge counts — no tessellation); that parser aligns to the next byte
boundary after the fill-style array because bitmap fills in sprite
libraries end mid-byte.
Fill indices activated by state-change records are collected and each
referenced fill must be in range and resolve to a non-placeholder
extraction output, while unreferenced `65535` placeholder fills are
recorded verbatim. Unsupported timeline tags, undefined character
references, declared-versus-observed frame-count mismatches, and label
or sprite-count disagreement with inspection fail closed.

## Outputs

- `assets/converted/units/10033_wild_elephant/`: `package.json` plus
  byte-identical bitmap copies (digests must match extraction outputs).
- `tools/asset-registry/conversions.json`: merged package entry under
  the shared neutral `conversion-v1` envelope (identical bytes
  regardless of converter run order).
- `tools/asset-registry/statuses.json`: merged overlay marking the
  source path `converted` (neutral `asset-statuses-v1` envelope).

## Validation gates (failures exit 1, outputs unwritten)

Content-ref uniqueness, sprite and label coverage, declared-versus-
observed frame counts, character references, referenced bitmap-fill
resolution, inspection agreement, digest equality, schema fields
(including nested), envelope policy (a legacy envelope fails closed
under the unit converter), and determinism. Exit 2 reports invalid
input (missing inspection/extraction/units, unreadable files,
unparseable content).

## Executable and invocation

Verified executable used for this section's runs:
`C:\Users\Edison\AppData\Local\Temp\opencode\cpython39\pkg\tools\python.exe`
(CPython 3.9.13 Windows x64). Any working Python 3.9+ standard-library
interpreter should behave identically.

From the repository root, after the extraction builds. The elephant's
bitmap outputs are ignored under `assets/converted/images/` and may be
absent in a fresh tree, so run the already-verified extraction first —
it also rewrites the tracked `statuses.json` (downgrading
already-`converted` entries to `extracted`) and regenerates
`image_extraction.json` with identical values in LF form, so restore
every tracked file it touched (worktree-form note below) before
converting:

```bash
python -B tools/asset-registry/extract_images.py
python -B tools/asset-registry/convert_unit.py
```

Worktree-form note: `content_version` fingerprints the raw worktree
bytes of the content file plus `inspection.json` and
`image_extraction.json` (`buildings_content_version` over
`buildings.json`, `units_content_version` over `units.json`), and the
committed package digests reproduce only with the generated forms in
place: `buildings.json`/`units.json` LF as `build_items.py` writes
them, both registry manifests in their `core.autocrlf=true` checkout
form (CRLF). `inspect_swf.py`/`extract_images.py` rewrite their
manifests with LF endings (changing the fingerprint), and
`build_items.py` resets `packages/game-content/manifest.json`'s other
sections; after any of those runs restore what changed (delete the
file first when only the line-ending form differs, then
`git checkout --`; restore `manifest.json` after `build_items.py`, and
`statuses.json` after an extraction run) before re-running a
converter. Order: extract → restore forms → convert.

## Evidence classification

This tool establishes source-grounded assembly consistency for one
converted unit: sprite-timeline fidelity (labels, placements, removals,
frame counts), shape-style and bitmap linkage, content linkage, and
determinism. It is evidence of package assembly, not of animation
correctness, rendering, visual fidelity, gameplay semantics, or Godot
loading. No Godot project is created or required here.

## Containment

- Reads only the committed inspection, extraction manifest plus bitmap
  files, normalized units, the two converter schemas, and the source
  SWF (plus optional `--repo-root`/`--out-root` relocation).
- Never imports or executes any legacy application module, never uses
  subprocess/network/server/browser/Flash, never modifies any source
  asset or prior manifest (verified byte-identical after runs).
- Writes only the package directory plus the conversions manifest and
  statuses merge, and only on success. No bytecode (`-B` recommended),
  no caches, no temporary files in the repository.
- The focused tests run the same way:

```bash
python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_unit.py -v
```
