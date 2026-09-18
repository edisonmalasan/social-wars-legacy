# Legacy content field-type survey verifier

Offline, read-only verification that the reviewed legacy content field-type
survey (`docs/game-content/field-types.json`) and its readable survey
(`docs/game-content/field-types.md`) still match the stored content source
`config/main.json` (20 top-level keys: 15 array-of-object keys with per-field
encoding profiles, 5 object keys with value-shape profiles). Python 3.9
standard library only; no new dependencies.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)),
from the pinned source runtime described in `docs/legacy-baseline.md`.
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B tools/field-survey/verify_fields.py
```

Exit 0 prints a JSON report with `"result": "agreement"`. The report goes to
stdout only; the tool never writes files.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Survey, readable, and stored source agree |
| 1 | Survey drift: whole-file counts, key coverage, entry count, per-field presence/type/string-encoded-number/embedded-JSON/empty-string/null counts, object value-shape distribution, or readable inconsistency detected; the report lists each problem |
| 2 | Invalid input or unsupported content shape: missing/unreadable files, invalid survey schema, unparseable content, a top level that is not a JSON object, a content key holding neither an array nor an object, an array entry that is not an object, or a survey source reference outside the repository, missing, or out of line range |

## What is verified

- Whole-file counts: the JSON-level string/number/boolean/null totals
  recomputed over all of `config/main.json` must equal the survey
  `whole_file` (43544 strings / 2997 numbers / 0 booleans / 780 nulls).
  Counts are exact recomputations, never samples.
- Key coverage: the 15 array keys and 5 object keys of `config/main.json`
  must exactly match the survey sections, with entry count matching per key.
- Per-field profiles: for every field of every array key, presence count,
  JSON-level type distribution, string-encoded-number count (full match
  against the numeric grammar
  `[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?`),
  embedded-JSON-string count (`json.loads` success), empty-string count,
  and null count must match. Counts are stored, pre-layering values:
  patches, duplicate cleaning, and dynamic derivation are layered separately
  and never folded into the profiles.
- Encoding classes: each array key is reviewed as `string_encoded` (every
  present value is a string; null marks absence), `native` (no strings
  occur), or `mixed` (string-encoded and native values coexist); the nine
  mixed-encoding keys (`levels`, `neighbor_assists`, `findable_items`,
  `goals`, `offer_packs`, `social_items`, `level_ranking_reward`,
  `darts_items`, `magics`) are labeled explicitly in the readable survey.
- Object value shapes: for `categories`, `inventory_items`, `globals`,
  `images`, and `units_collections_categories`, the value-type distribution
  must match (for example, `globals` holds 62 integers, 4 floats, 8 strings,
  8 objects, and 22 arrays).
- Survey schema: policy fields (including `key_count`/`array_key_count`/
  `object_key_count` cross-checked against the entries), the numeric grammar
  pinned verbatim, the embedded-JSON rule, per-field profile totals, and
  source references with file and line bounds. Every `source_references`
  entry must name a file under the repository root with
  `1 <= line <= end_line` within that file's actual line count.
- Readable consistency: every survey array key must appear in
  `field-types.md` as a ``| `name` | <encoding_class> |`` inventory row,
  every object key as a ``| `name` | object |`` row, with observed-encodings
  versus normalization labeling, mixed-encoding labeling, and the numeric
  grammar present verbatim.

## Evidence classification

This tool establishes structural, source-grounded consistency between the
survey, the readable document, and the current stored source. It is
evidence of reviewed documentation, not evidence of served-byte
equality, content validity, gameplay parity, or normalization.
No coercion rule, default, schema, or ID reassignment is specified or
applied; `make_dynamic` wall-clock rewriting of `darts_items` start dates
stays out of scope exactly as in the content census, and the verifier never
produces served bytes, which keeps repeated runs byte-identical.

## Containment

- Reads only `config/main.json`, `docs/game-content/field-types.json`, and
  `docs/game-content/field-types.md` (plus optional `--repo-root`
  relocation of the same reads). Every survey `source_references` entry
  points at `config/main.json`, so reference bound validation adds no
  further file to the read set.
- Never imports or executes any legacy application module (no
  `get_game_config`, `jsonpatch`, or Flask import), never applies
  patches, never reads runtime saves, never contacts a network, never
  starts a server, and never opens a browser or Flash content.
- Writes nothing: no report files, no bytecode (`-B` recommended), no
  caches, no temporary files in the repository. Repeated runs over
  unchanged inputs are byte-identical.
- The focused tests in `test_field_survey.py` run the same way:

```bash
python -B -m unittest discover -s tools/field-survey -p test_field_survey.py -v
```
