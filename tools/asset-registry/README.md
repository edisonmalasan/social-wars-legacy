# Asset registry foundation (M4 slice 1: observe and record)

Validated on-disk asset registry joined against normalized content
references, built offline with Python 3.9 standard library only; no new
dependencies, no SWF parsing, no conversion, no asset mutation, no Flash
execution.

## Inputs

- Worktree asset files with extensions `.swf`, `.jpg`, `.jpeg`,
  `.png`, `.mp3`, `.wav`, `.gif`, minus exclusions `.git/`, `saves/`,
  `temp/`, `new_assets/`, `build/bundle`, `build/dist`, `build/work`.
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
