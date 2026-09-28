# Proposal

## Why

Roadmap M3 (Content Normalization) delivers five items — normalized game configuration, schemas, content validator, dependency validation, and content manifest — and the §14 backlog item "Build content validator" (`tooling: validate normalized game content`) is the last open M3 line, but nothing in the repository currently validates the *committed* normalized package as a whole. The ten builders validate their own outputs at build time (round-trip gates, schema-required fields, their own reference edges), and the runtime `ContentRegistry` verifies manifest bytes/SHA-256 per output at load time, yet between those two points no offline tool answers the M3 exit question — "can Godot load validated game definitions?" — independently of a rebuild: the 21 schema files are only ever applied by the builder that owns each domain, the manifest's recorded counts and section records are never cross-checked against the files they describe, and cross-domain reference edges are checked only by whichever builder happens to own them. This change delivers a standalone, read-only content validator over the committed package, and in doing so completes the M3 "dependency validation" line as the validator's reference-integrity family.

## What Changes

- New `packages/game-content/tools/validate_content.py`: a standalone offline validator, Python 3.9 standard library only, self-contained (it implements the documented schema subset independently and never imports the ten builders or any legacy module). It reads exactly the committed package — `packages/game-content/manifest.json`, the normalized outputs the manifest records, and the 21 schema files — and writes nothing. Exit 0 prints a JSON success report (per-file entry counts, files verified, references checked); exit 1 prints a `validation-failed` report listing each problem with stable identifiers (check family, file, entry `legacy_id`, field) and writes nothing; exit 2 reports invalid input or unsupported shape (missing/unreadable/unparseable file, invalid schema file, bad usage) on stderr.
- Four check families:
  1. **Package structure and hygiene** — the `normalized/` directory set equals the manifest-recorded output set exactly (22 files: no missing output, no unrecorded file); the root record and all nine extension sections are present with `schema_version`, `result: success`, and `policy` recorded; every required schema file exists, parses, and is structurally valid (object schema, `required` ⊆ `properties`, `kind` const naming its file).
  2. **Manifest integrity** — every recorded output's byte count and SHA-256 match the file on disk; the count keys that name output entries match the actual entry counts under a documented mapping (provenance-only counts such as `stored_items` are recorded verbatim, not file-verifiable).
  3. **Schema conformance** — every entry of the 21 schema-backed files passes the same schema subset the builders enforce: `required`, type unions where a bool is never an integer, `const` (including `kind`), `enum`, `minimum`, `minItems`/`minProperties`, `propertyNames`, `additionalProperties: false`, and nested object gates. `specials.json` (the one file without a schema) gets its documented gates instead: exactly one entry, `legacy_id` `925`, and the exact `special_note`.
  4. **Dependency validation** (completes the M3 line) — per-file `legacy_id` uniqueness and distinctness of the 900-entry items union; `upgrades_to`/`trains_ids` resolution with the `-1`/`0` sentinels; `inventory_ids` object keys resolving against the inventory domain; collections `item_refs`/`prize_refs` derived from `item_ids`/`prize` and resolving against the items union; `level_ranking_reward` `unit_refs` derived from `units`; `unit_collection_categories` `unit_refs` derived from stored `units`; darts `item_refs`/`extra_ref` derived from the pooled `items`/`extra_item`; offers `item_refs` derived from the stored item shapes (flat leaves, pair firsts, group integer leaves; pair seconds opaque) including the two pinned anomalies, and resolving against the items union; categories `sub` parent references resolving against the categories domain.
- New suite `packages/game-content/tests/test_validate_content.py` using the package's in-process import convention: the committed package validates (exit 0 and report counts matching reality); a mutation matrix where each check family is broken in a disposable copy and must be caught with a named problem while the committed package stays untouched; traceability-by-mutation over every schema-required field of every schema; CLI exit codes 0/1/2; determinism (identical report bytes across runs); and containment (no writes anywhere — package file set and bytes identical before and after every run).
- Docs: a `content validator` extension section in `packages/game-content/README.md` (executable, invocation, exit codes, evidence classification, containment) and the validator commands in `AGENTS.md`'s verified-commands section, recorded only after they have actually been executed.

## Non-Goals

- No re-derivation and no builder changes: the ten builders, all normalized outputs, `manifest.json`, and all schema files stay byte-identical; the validator never rewrites anything.
- No source-fidelity re-check: input freshness (config/patch/mods round-trip, `content_fingerprint` recomputation) remains the builders' build-time job — the validator reads no legacy sources (`config/`, `mods/`, saves) at all.
- No new dependency: standard library only; no `jsonschema` or any other package.
- No runtime integration: no Godot, `ContentRegistry`, Compatibility API, server, or gameplay change; no wiring into any existing verification battery beyond documentation.
- No served-byte, asset-existence, or gameplay-parity claims; no M6 work.

## Capabilities

### New Capabilities

- `content-validation`: the standalone offline validator — package structure/hygiene, manifest integrity, schema conformance over the documented subset (plus the special's gates), dependency/reference integrity over every cross-domain edge, exit-code and report contract, containment, and documented commands.

### Modified Capabilities

- (none — no existing spec's requirements change: `godot-content-registry` keeps client-side digest verification, the normalization specs keep describing their builders, and no spec mentions a validator or dependency validation today.)

## Impact

- New files: `packages/game-content/tools/validate_content.py`, `packages/game-content/tests/test_validate_content.py`.
- Edited files: `packages/game-content/README.md` (validator extension section), `AGENTS.md` (verified commands entry), `docs/DEVELOPMENT_ROADMAP.md` (Project Status ledger at archive, recording both M3 open lines delivered).
- Verification: the new suite plus full discovery over `packages/game-content/tests` (all 11 suites, proving the ten builders still pass); the validator itself against the committed package; `openspec validate --all --strict`; the Compatibility API guard baseline and both prior batteries (`verify.ps1`, `verify-boot.ps1`) re-run to exit 0 as regression evidence.
- Guards: `packages/game-content` is not a `guard_baseline.py` group; `verify.ps1`'s content-package digest is pre-vs-post within each run; hash-manifest evidence covers immutable baseline Git blobs — adding tooling files and the README section changes no guarded byte, and no normalized output, manifest, schema, legacy source, save, or M4/M5 evidence file changes.
