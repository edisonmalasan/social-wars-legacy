# Asset registry foundation (M4 slice 1: observe and record)

Validated on-disk asset registry joined against normalized content
references, built offline with Python 3.9 standard library only; no new
dependencies, no SWF parsing, no conversion, no asset mutation, no Flash
execution.

## Inputs

- Worktree asset files with extensions `.swf`, `.jpg`, `.jpeg`,
  `.png`, `.mp3`, `.wav`, `.gif`, minus exclusions `.git/`, `saves/`,
  `temp/`, `new_assets/`, `assets/converted/` (generated outputs are
  not source corpus), `build/bundle`, `build/dist`, `build/work`.
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
