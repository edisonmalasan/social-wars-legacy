## Context

M2 behavioral tooling is complete and archived. The content census records stored sources and layering; the field-type survey records exact encoding profiles (items fully string-encoded, costs always JSON-object strings with keys `o/s/g/w/c`, `cost_type` always null). This design scopes the planning artifacts for the first M3 normalization slice: the items domain only. Scope is the normalized package plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code.

## Goals / Non-Goals

**Goals:**
- Normalized `buildings.json` (469) and `units.json` (308) with `legacy_id`, source, content version, and asset references, plus a documented special for id `925`.
- JSON schemas for building and unit definitions; a stdlib-only builder/validator that loads stored content, mirrors legacy layering without importing it, coerces per documented rules, validates, and writes output only on success.
- Round-trip evidence (legacy-shaped re-emission diffed modulo coercions) and a manifest entry.
- Focused regression tests for classification, coercion, validation failures, round-trip, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No quests, research, collections, missions, or other content keys.
- No asset-existence validation (M4 asset pipeline owns asset truth).
- No Godot loading code, Compatibility API, or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Normalize loaded content, not stored bytes.** The game serves patched, deduped content, so definitions must reflect post-layering values (including the 122 patch-appended items and added fields). The builder reimplements the three load steps (ordered RFC 6902 application limited to observed ops, keep-later dedup) in stdlib without importing `get_game_config` or `jsonpatch`. Alternative (normalizing raw stored values) was rejected because definitions would then describe content the game never serves.
- **Coercion rules cite the survey.** Numeric strings become numbers, embedded-JSON strings become structures, `""` survives only where the survey shows it carries meaning, `cost_type` is dropped with a note. No rule invents gameplay semantics; anything the survey does not cover fails validation explicitly.
- **Schemas are contracts; the validator is hand-rolled with traceability.** Python 3.9 stdlib has no JSON-Schema validator, so the builder enforces the normative requirements directly and a traceability test asserts every schema-required field has a validator check. Alternative (adding a `jsonschema` dependency) was rejected per the no-new-dependencies rule.
- **Round-trip diff is the fidelity gate.** Re-emitted legacy-shaped items must equal loaded legacy items except for documented coercions; this is stronger than spot checks and directly evidences "representation change, not gameplay change".
- **Small domain module.** One builder/validator tool plus tests under the new package area; no giant dispatcher, no new dependencies.

## Risks / Trade-offs

- [Patch-opSubset drift] → If a patch file ever uses an op outside the observed set, the builder fails explicitly (exit 2-style invalid input) instead of mis-applying content.
- [Classification edge cases] → Any `type` value outside `b`/`u`/`l` fails validation; the `l` special is documented, not generalized.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.
- [Cost-key drift] → Costs outside `o/s/g/w/c` or negative amounts fail validation rather than entering definitions.
- [Round-trip strictness] → Key ordering and float formatting are normalized before comparison so only semantic differences fail the gate.
