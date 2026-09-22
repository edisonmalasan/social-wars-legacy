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
