## Context

Seven M3 slices are complete and archived, including two with patch layering (items appends, darts replace). Direct reads show stored `globals` (104 heterogeneous constants) gains exactly one entry from the `atom_fusion_powerup` add, and the 8 string constants are opaque quoted payloads that must never be parsed as references. This design scopes the planning artifacts for the eighth M3 normalization slice. Scope is the normalized tuning table plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `globals.json` (105) with `legacy_id` as the constant name, source, per-entry layer (`stored` vs `patched(atom_fusion_powerup)`), content version, verbatim values, and recorded value types.
- JSON schema for global-entry definitions with a value-type union; stdlib-only builder/validator extension that applies only the powerup add, guards patch drift and active mods, and enforces the schema.
- Round-trip evidence (loaded-shaped re-emission diffed exactly against the loaded object) and manifest `globals` section merged without touching prior keys.
- Focused regression tests for layering, classification, verbatim fidelity, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No parsing of string constants: version lists, URL, date, depot-limits string, and friend-reward CSV strings stay opaque display/config data.
- No semantic grouping or renaming of constants; tuning meaning belongs to future authoritative-server work.
- No offer packs, images, or other content domains.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Loaded content is the input; layering mirrors the legacy loader for this key only.** The builder verifies the ordered patch list and applies exactly the one powerup add; any other globals-targeting op, a missing powerup patch, or a divergent add shape fails explicitly (exit 2). `source_layer` records per-entry provenance and the manifest records stored (104) versus loaded (105) counts.
- **Values are verbatim JSON with recorded types.** Each definition carries `value` (deep-copied verbatim: int stays int, float stays float, bool would stay bool, strings/objects/arrays as observed) plus `value_type` (integer/number/string/array/object/boolean/null, booleans distinguished from integers). No numeric parsing, no embedded-JSON decoding, no CSV splitting.
- **Schema uses a value-type union.** The schema types `value` as the full JSON scalar/structure union; the hand-rolled validator enforces it plus required/type/const/minimum/additionalProperties gates, with traceability tests as in prior slices.
- **Round-trip targets the loaded object.** Re-emitted keyed object must equal the loaded object exactly by key, type, and value.
- **Small domain module.** Add a globals builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Heterogeneity] → The union schema cannot express per-constant shapes; fidelity rests on exact round-trip plus type-distribution counts rather than per-key contracts.
- [Opaque strings] → Friend-reward strings that resemble item lists are deliberately not validated; if a future change specifies their format, a new rule (not a silent reinterpretation) is required.
- [Future patch drift] → Any new globals-targeting patch fails the build until re-censused.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
