# Legacy village structural state diff

This standalone Python 3.9 standard-library tool compares supplied evidence
without importing the game or recorder. It describes structural differences,
not gameplay meaning, save validity, or persistence. Reports are private local
evidence even though they contain no state values.

## Commands and environment

Run from the repository root; `python` means a selected working interpreter,
not the Windows Store alias. Use `-B` to prevent bytecode creation.

```text
python -B tools/state-diff/state_diff.py compare --before tests/saves/fresh-player-pre-migration.json --after tests/saves/fresh-player.json
python -B tools/state-diff/state_diff.py compare --before tests/saves/fresh-player.json --after tests/saves/fresh-player.json
python -B -m unittest discover -s tools/state-diff -p test_state_diff.py -v
```

These commands were executed with Windows x64 CPython 3.9.13 on 2026-09-14,
using this explicit PowerShell executable prefix in place of `python`:

```text
& C:/Users/Edison/AppData/Local/Temp/socialwars-runtime-740419ee065f46eab323c20a2d601e6b/cpython/tools/python.exe
```

That transient interpreter is not a repository dependency. See the
[baseline provenance](../../docs/legacy-baseline.md#interpreter-provenance-and-host).
The tool needs no installed application packages or Git executable.

The alternative explicit mode is `compare --record <file>` for one
[schema-version-1 recorder record](../../docs/legacy-command-recording.md).
Focused CLI tests executed this mode against controlled disposable records.
Replace `<file>` with an existing record; the tool does not locate records,
discover saves, or produce sample evidence. Pair mode requires both `--before`
and `--after`; neither may be combined with `--record`. A state with fields named
`before` or `after` remains a state in pair mode.

Each input must be a regular UTF-8 JSON file. Pair roots must be objects.
Record roots must be objects with an exact integer `schema_version` of `1`
(boolean `true` and number `1.0` are rejected) and object `before`/`after`
boundaries. Missing or null boundaries mean unavailable evidence, not empty
states. Unknown record metadata is accepted and does not affect equality,
but is validated, bounded, and inspected for known secrets.

## Report and comparison semantics

The canonical controlled
[pre-migration fixture](../../tests/saves/fresh-player-pre-migration.json) and
[post-migration fixture](../../tests/saves/fresh-player.json) produce exactly:

```json
{
  "change_count": 1,
  "changes": [
    {
      "after_type": "string",
      "before_type": "null",
      "operation": "changed",
      "path": "/version"
    }
  ],
  "comparison": "different",
  "policy": "structural-json-types-v1",
  "schema_version": 1
}
```

Successful output is exactly one JSON document on stdout, serialized with
sorted member names, two-space indentation, ASCII escaping, UTF-8 bytes,
LF line endings, and one final newline. Equality has `comparison: "equal"`,
`change_count: 0`, and an empty `changes` array. No payload, old/new value,
filename, source hash, player correlation, time, UUID, or machine metadata
is included. Each entry contains only the four fields shown above.

Objects are walked by exact Python string key order, preserving case, unknown
fields, numeric-looking keys, and legacy identifiers. Arrays are compared by
position in ascending numeric index order: common positions first, then tail
additions/removals. Insertions and reordering can therefore cause many changes.
Object order, whitespace, equivalent escape spellings, and line endings do not
change equality. No domain normalization or ignore rules are applied.

Type labels are `null`, `boolean`, `integer`, `number` (floating point),
`string`, `object`, `array`, and `missing`. `true`, `1`, and `1.0` differ.
Numbers otherwise use exact Python scalar equality, with no tolerance;
finite floating-point values follow Python's JSON decoding precision.
Missing differs from null; empty objects and empty arrays remain distinct.
Scalar changes and type changes create one `changed` entry. Added and removed
subtrees create one `added` or `removed` entry at the subtree root, not entries
for every descendant. Paths use RFC 6901: `~` becomes `~0`, `/` becomes `~1`,
and an empty object key is represented by a trailing `/`.

## Fixed limits and failures

| Bound | Maximum |
| --- | ---: |
| Bytes per input file | 16 MiB (16,777,216 bytes) |
| Nested containers, counting the root | 128 |
| Visited JSON value nodes across supplied inputs | 1,000,000 |
| Change entries | 100,000 |

Pair mode counts both entire trees; record mode counts the complete record
once, including its boundaries and metadata. Object keys are validated but
do not count as value nodes. Validation includes unchanged and added/removed
subtrees, so subtree summaries cannot bypass limits. The complete record root
counts toward container depth. Limits are inclusive; exceeding any one fails
without a truncated report. File bytes are bounded before JSON decoding;
decoder recursion or memory exhaustion also produces a limit failure.

Invalid UTF-8, malformed JSON, duplicate keys at any depth, `NaN`, infinities
(including numeric overflow such as `1e9999`), and unpaired Unicode surrogates
are rejected. No boundary coercion, migration, or schema projection occurs.

| Exit | Meaning | Stdout |
| --- | --- | --- |
| `0` | Equal | Complete report |
| `1` | Different | Complete report |
| `2` | Invalid/unavailable evidence or processing/output failure | No report before output begins |

Errors emit one fixed bounded category on stderr, such as `arguments invalid`,
`before input invalid`, `after input read failed`, `record schema invalid`,
`record boundary invalid`, `record evidence unavailable`,
`record input limit exceeded`, `comparison limit exceeded`,
`comparison path ambiguity`, `report serialization failed`, or `output failed`.
They contain no paths, filenames, keys, values, decoder fragments, underlying
exception messages, or tracebacks. The report is fully built and serialized
before the first stdout write. A failing pipe or consumer can still receive a
prefix before an output failure; stdout is not transactional. Exit `2` remains
authoritative where output failure is observable. If stderr also fails, the
category cannot be delivered. Shell redirection can create/truncate files and
lies outside tool containment.

## Sensitive paths and evidence meaning

Known sensitive-key matching is case-insensitive and removes punctuation,
matching the recorder's `user_key`, `accessToken`, `authorization`,
`proxyAuthorization`, `cookie`, `cookies`, `setCookie`, `signature`,
`data_hash`, `password`, `secret`, `token`, `session_id`, and `api_key` policy.
The tool collects all nonempty string values below these keys from both
states, or from the complete supplied record. It does not import the recorder
and does not infer extra secrets from headers or form encoding.

Comparison uses original structures. Only reported path components replace
occurrences of collected secrets with `[REDACTED]`, before RFC 6901 escaping.
Longer secrets are protected first, with exact string order breaking ties;
inserted placeholders are not rewritten by subsequent replacements. If two
distinct changed paths become the same protected path, the entire comparison
fails with path ambiguity rather than losing a change. Ordering remains the
original key/index traversal order. State values never enter the report.

This policy does not recognize arbitrary personal data, secrets under unknown
keys, or encoded secrets. Unknown key names may identify players. Review
reports before sharing; there is no automatic evidence promotion or commit.

Recorder boundaries surround in-memory `command()` execution, not necessarily
persisted saves. A failed command can have partial unsaved mutations; a parse
failure can have equal boundaries. The diff does not interpret outcome metadata
or assert that the after-state was saved. Canonical inputs establish only the
controlled fresh-player migration boundary, as explained in the
[fixture guide](../save-fixtures/README.md); progressed-player and gameplay
parity remain unverified.

## Containment and verification

The comparison command only opens explicitly supplied files for reading and
writes stdout/stderr. It creates no directory, cache, bytecode, temporary report,
save, or evidence file under the documented `-B` invocation. It imports no
legacy/runtime module and starts no process, network, server, browser, or Flash
activity. Existing sources, archives, canonical fixtures, runtime saves, and
recorder evidence remain unchanged. The focused test suite itself creates and
cleans controlled test inputs in external temporary storage.

The focused suite covers both modes, strict failure categories, representational
equality, type distinctions, positional arrays, exact limit boundaries,
canonical `/version`, all known sensitive-key spellings, repeated/overlapping
secrets, path collisions, serialization/memory/output failures, and byte-stable
reports. Every CLI test snapshots its complete disposable input directory,
including directories, before and after. A complete disposable checkout test
includes runtime saves, canonical fixtures, source and archive markers, and
surrounding files. Repository root Python sources, canonical fixture bytes,
and the real runtime save tree are also checked across the suite. Audit hooks
check explicit reads and prohibit writes, runtime imports, network calls,
process starts, and filesystem mutations during success and failure.

Replay, patch application, domain summaries/normalization, ignore rules,
progressed-player synthesis, runtime integration, dependency changes, modern
API/client work, gameplay changes, and Flash execution are excluded. These
focused checks do not substitute for the coordinator's final preservation
checks, strict OpenSpec validation, or independent artifact verification.

## Executed evidence (2026-09-14)

The final focused discovery run exited `0`: **29 tests passed** in 30.239
seconds on the explicit CPython 3.9.13 Windows AMD64 interpreter above.
The canonical pair command exited `1`, with exactly one `/version` change
from null to string; the self-comparison command exited `0`, with no changes.
Both emitted the specified value-free report and no diagnostic.

All five local file links in this guide and the new README/AGENTS references
resolved. A contained `python -m compileall -q .` run over disposable copies
of the two new Python files exited `0`; generated bytecode stayed outside the
worktree. `git diff --check` passed. This syntax check is separate from the
29 behavioral tests and is not the full-repository final verification.

Earlier focused runs exposed Windows stderr newline translation and audit
harness assumptions about pathlib's two-stage read events, plus a test that
expected Unicode validation to precede invalid record schema validation.
Diagnostics now use explicit LF bytes, and the corrected audit and record
input tests passed in the final run. No runtime source, recorder, canonical
fixture, dependency, roadmap, or OpenSpec artifact was edited by this worker.
