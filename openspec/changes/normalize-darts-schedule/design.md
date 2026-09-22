## Context

Six M3 slices are complete and archived (items with patch layering; quests, tables, economy, social, taxonomy without). Direct reads show stored `darts_items` (30 entries) is wholly replaced by the `targets` patch (27 entries, ids 1..27, uniform shape, clean item references), and the serve-time `make_dynamic` rewrite of `start_date` is an explicitly censused out-of-scope boundary. This design scopes the planning artifacts for the seventh M3 normalization slice. Scope is the normalized darts schedule plus builder/validator tooling and tests; no legacy change, no other content key, no Godot code. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Normalized `darts_items.json` (27) with `legacy_id`, source, patch lineage, content version, verbatim native pools, verbatim `start_date` derivation inputs, and resolved item references.
- JSON schema for darts-item definitions; stdlib-only builder/validator extension that applies only the `targets` replace, guards patch drift and active mods, and validates the items reference edge.
- Round-trip evidence (patched-shaped re-emission diffed exactly against the patched array) and manifest `darts` section merged without touching prior keys.
- Focused regression tests for layering, classification, coercion, validation failures, round-trip, manifest merge, and containment.

**Non-Goals:**
- No modification of any legacy content file, patch, or behavior.
- No stored-array normalization alongside the patched array: the stored 30 entries are derivation inputs to the replace, recorded as counts only.
- No `start_date` interpretation, re-derivation, or served-byte comparison: `make_dynamic` never runs here.
- No offer packs, globals, images, or other content domains.
- No Godot loading code or gameplay code.
- No claim of M3 exit, gameplay parity, or progressed-player coverage.

## Decisions

- **Patched content is the input; layering mirrors the legacy loader.** Like the items builder, this builder verifies the ordered patch list and applies the observed replace subset restricted to `/darts_items` (exactly one replace op); any additional darts-targeting op, a missing `targets` patch, or a divergent replace value shape fails explicitly (exit 2 drift refusal). `source_layer` records `patched(targets)` and the manifest records stored-vs-patched counts.
- **`start_date` is data, not a clock.** The patched datetime strings are preserved verbatim as derivation inputs with a manifest note citing the census dynamic-derivation boundary; no wall-clock read, no Monday-anchor recomputation, no served comparison.
- **References reuse the quest edge.** Pooled `items` integers and `extra_item` must resolve against the committed normalized items legacy-ID set or validation fails; `item_refs` preserves pool order and `extra_ref` carries the single extra id.
- **`legacy_id` is the decimal id; order preserved.** Ids must be unique native integers; entry order follows the patched array.
- **Round-trip targets the patched array.** Re-emitted entries must equal the patched entries exactly (all fields native or verbatim strings).
- **Small domain module.** Add a darts builder module plus tests alongside the existing package tooling; no new dependencies.

## Risks / Trade-offs

- [Stored vs patched confusion] → The manifest records both counts and the replace lineage explicitly; tests assert the stored 30 are never normalized directly.
- [Dynamic drift] → Any future change to the `targets` payload shape or a new darts-targeting patch fails the build until re-censused; serve-time dates remain unverified by design.
- [Schema/validator drift] → The traceability test fails the suite if a schema-required field lacks a validator check.

## Migration Plan

Not applicable: additive normalized outputs plus manifest merge; no legacy migration, no rollout, no rollback beyond reverting the new files.
