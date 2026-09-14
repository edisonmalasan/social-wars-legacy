# Controlled legacy save fixtures

These are controlled canonical test inputs derived from repository behavior,
not historical player observations. Fresh-player creation and the complete
pre/post migration boundary are verified. Authentic early-game, mid-game,
late-game, and stress-town player saves are **unavailable and unverified**.
Files under [`villages/`](../../villages/) other than the initial template are
static neighbor or quest content, not player progression substitutes.

## Commands and environment

Run from the repository root with the verified Windows x64 CPython 3.9.13
environment and its existing pinned runtime dependencies, plus local Git:

```text
python -B tools/save-fixtures/save_fixtures.py generate
python -B tools/save-fixtures/save_fixtures.py verify
python -B -m unittest discover -s tools/save-fixtures -p test_save_fixtures.py -v
```

The executable used for the 2026-09-14 checks is
`C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe`.
Its interpreter/dependency provenance is recorded in the
[legacy baseline](../../docs/legacy-baseline.md#interpreter-provenance-and-host).
This transient environment is not a repository dependency.

Generation replaces only these three named outputs after capture succeeds:

- [`fresh-player-pre-migration.json`](../../tests/saves/fresh-player-pre-migration.json)
- [`fresh-player.json`](../../tests/saves/fresh-player.json)
- [`manifest.json`](../../tests/saves/manifest.json)

Verification regenerates into temporary storage and compares all three outputs
without refreshing evidence. A missing or changed source, fixture, or manifest
produces a non-zero result naming the affected path. No server, network, browser,
Flash, SWF, or protocol recorder is executed.

## Capture and provenance

The command verifies baseline commit
`e8c98a03c902eba70323538dc5d4eaba2f2927a1` and the raw blob identity, SHA-256,
and size of the required legacy sources. It checks the real import closure,
including `engine.py`, `constants.py`, `get_game_config.py`, and preserved
`config/` and `mods/` inputs, in addition to `sessions.py`, `version.py`,
`bundle.py`, and `villages/initial.json`. Source comparison permits only CRLF/LF
checkout conversion; the manifest hashes identify raw Git blobs. Local Git
reads disable replacement objects, lazy fetching, network protocols, prompts,
and optional locks. No Git configuration or history is changed.

An isolated `-I -B` child runs from the repository root, imports the actual
legacy modules, redirects the already imported `sessions.SAVES_DIR` to a
temporary directory, and clears only that child's in-memory village tables.
UUID is fixed to `00000000-0000-4000-8000-000000000001`; timestamp is fixed to
`1700000000`. The migration wrapper records a deep copy of the actual state
passed by `sessions.new_village()`, rather than duplicating its construction.
The original migration runs, the original persistence runs, and the tool
validates the persisted state using `sessions.is_valid_village()`.

The complete independently migrated pre-state must equal both the complete
persisted JSON object and the in-memory session. Unknown fields are retained;
a focused test injects unknown nested fields only in a disposable test template.
This test does not expand the canonical evidence into synthetic player history.

The post fixture contains the exact persisted bytes. Both state fixtures use
the verified Windows representation: ASCII JSON with escaped non-ASCII text,
four-space indentation, insertion order, CRLF line endings, and no final
newline. The manifest is deterministic UTF-8 JSON with sorted keys and LF.
An unexpected persisted representation fails explicitly; other platforms have
not been verified. The runtime `saves/` path is snapshotted before and after
capture, and provenance is rechecked after capture.

## Limits and review

This establishes controlled fresh-state and migration-boundary evidence only.
It does not establish gameplay parity, historical progression, protocol parity,
canonical modern save design, or client behavior. It does not load or rewrite
authentic runtime player saves. Raw templates, static content, runtime modules,
and archival assets remain unchanged.

The existing repository ignore pattern `saves/` also matches `tests/saves/`, so
the three evidence files require an explicit initial Git addition. Repository
attributes preserve the two state fixtures as exact binary evidence and enforce
LF for the deterministic manifest; subsequent changes to the tracked files are
reviewed normally.

## Executed evidence (2026-09-14)

The final focused unittest discovery run exited 0: **11 tests passed** in
156.052 seconds. Coverage includes actual-path capture, complete migration,
unknown-field retention, repeated generation, fixture/manifest tampering,
source rejection, actionable non-zero CLI results, missing evidence, and
write containment. Earlier added CLI checks exposed test-harness root routing
and Windows path-separator assertion mistakes; both were repaired before the
final complete passing run.

Generation and read-only verification each exited 0 and reported two controlled
fixtures plus manifest, totaling 41,057 bytes. Two successive generations in
the focused tests produced identical bytes and retained an unrelated output
marker. Verification tests compared complete disposable-source snapshots,
including an existing opaque runtime save, before and after successful and
failed verification.

Independent `hashlib.sha256` and byte-length checks against the generated files
matched every fixture manifest entry:

| Canonical file | Bytes | SHA-256 |
| --- | ---: | --- |
| `fresh-player-pre-migration.json` | 15,625 | `0b92be3ead3f01374dca383781095903ba7ca8171a6ad6b9576750c873a1498e` |
| `fresh-player.json` | 15,628 | `25df5b5a665b5eb07a88af1ea8179f0416fa0078cfaac8dd4b8749a3762643f5` |
| `manifest.json` | 9,804 | `ce6d52202d24969eac8dbc2e2aab665ad9f56e8766249cabd5d859325e37e106` |

The same interpreter executed `python -m pip --isolated check` successfully
(`No broken requirements found.`). `python -m compileall -q .` exited 0 in
a temporary copy of all 17 repository Python source files, containing every
generated bytecode file outside the working tree. This is syntax evidence,
separate from behavioral tests.

`openspec validate capture-fresh-legacy-save-fixtures --strict --no-interactive`
exited 0. Local documentation file links in this guide and the legacy baseline
resolved, and `git diff --check` passed. The working tree had no runtime
`saves/` directory; its pre-existing coordinator-owned roadmap edit was retained.
No legacy module, raw village, configuration, dependency, or archival asset was
modified by this worker.

The installed OpenSpec implementation verification workflow was not executed
by this worker: the exposed skill catalog has no verification skill and the
installed CLI has no implementation verification command. Strict artifact
validation does not substitute for the coordinator's independent implementation
verification and final acceptance.
