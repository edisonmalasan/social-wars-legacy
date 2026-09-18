# Legacy game-content census verifier

Offline, read-only verification that the reviewed legacy game-content
census (`docs/game-content/census.json`) and its readable inventory
(`docs/game-content/census.md`) still match the stored content sources:
`config/main.json` (20 top-level keys), the ordered patch list
`config/patch/patches.txt` with its five patch files, and the mods
pipeline status in `mods/mods.txt`. Python 3.9 standard library only;
no new dependencies.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)),
from the pinned source runtime described in `docs/legacy-baseline.md`.
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B tools/content-census/verify_content.py
```

Exit 0 prints a JSON report with `"result": "agreement"`. The report goes to
stdout only; the tool never writes files.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Census, inventory, and stored sources agree |
| 1 | Census drift: key coverage, container shape, entry count, patch order/position/op-count/op-mix/target, mods status, or inventory inconsistency detected; the report lists each problem |
| 2 | Invalid input or unsupported content shape: missing/unreadable files, invalid census schema, unparseable content, a top level that is not a JSON object, a content key holding neither an array nor an object, a patch file that is not a list of RFC 6902-style ops with string `op`/`path`, a patch operation outside the supported subset (`add`, `remove`, `replace`, `move`, `copy`, `test`), or a census source reference outside the repository, missing, or out of line range |

## What is verified

- Key coverage: the 20 top-level keys of `config/main.json` must exactly
  match the census `content_keys`, with container shape (`array`/`object`)
  and entry count matching per key. Counts are stored, pre-layering
  values: patches, duplicate cleaning, and dynamic derivation are
  layered separately and never folded into the counts.
- Patch coverage: the active patch order parsed from
  `config/patch/patches.txt` (comment and blank lines skipped, matching
  the legacy loader) must equal the census order
  (`atom_fusion_item`, `unit_patch`, `atom_fusion_items_data`,
  `atom_fusion_powerup`, `targets`); every patch file must parse as a
  JSON op list, and per-file position, op count, op mix, and normalized
  target paths (numeric index segments folded to `{index}`) must match.
  Patches are parsed only, never applied.
- Mods status: the active/inactive mod lists parsed from
  `mods/mods.txt` must match the census. Current truth is inactive:
  no active mods, with `no_hiring_needed` commented out.
- Census schema: policy fields (including `key_count`/`patch_count`
  cross-checked against the entries), per-key fields (container shape,
  entry count, ID scheme, asset-reference fields, layering), per-patch
  fields (position, op count, op mix totalling the op count, target
  paths), mods status, duplicate-cleaning and dynamic-derivation
  descriptions, and source references with file and line bounds. Every
  `source_references` entry must name a file under the repository root
  with `1 <= line <= end_line` within that file's actual line count.
- Inventory consistency: every census content key and patch name must
  appear verbatim in `census.md`, with the inactive mods pipeline
  labeled as inactive, stored sources distinguished from served bytes,
  and the `make_dynamic` derivation boundary plus
  `remove_duplicate_items` cleaning named.

## Evidence classification

This tool establishes structural, source-grounded consistency between the
census, the readable inventory, and the current stored sources. It is
evidence of reviewed documentation, not evidence of served-byte
equality, content validity, gameplay parity, or normalization.
`make_dynamic` rewrites `darts_items` start dates from the wall clock
at import (`get_game_config.py:319`) and per request
(`get_game_config.py:89-91`), so served configuration is
nondeterministic by design; served-byte equality is explicitly
unverified and the verifier never produces served bytes, which keeps
repeated runs byte-identical.

## Containment

- Reads only `config/main.json`, `config/patch/patches.txt`, the five
  patch files under `config/patch/`, `mods/mods.txt`,
  `docs/game-content/census.json`, and `docs/game-content/census.md`
  (plus optional `--repo-root` relocation of the same reads), plus the
  additional repository files named by the census's `source_references`
  (`get_game_config.py`, `mods/no_hiring_needed.json`), which are read
  to validate reference line bounds.
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never applies
  patches, never reads runtime saves, never contacts a network, never
  starts a server, and never opens a browser or Flash content.
- Writes nothing: no report files, no bytecode (`-B` recommended), no
  caches, no temporary files in the repository. Repeated runs over
  unchanged inputs are byte-identical.
- The focused tests in `test_content_census.py` run the same way:

```bash
python -B -m unittest discover -s tools/content-census -p test_content_census.py -v
```
