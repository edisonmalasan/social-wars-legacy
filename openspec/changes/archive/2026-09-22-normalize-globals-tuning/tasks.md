## 1. Normalized package

- [x] 1.1 Create `packages/game-content/normalized/globals.json` (105 definitions, one per loaded entry) with `legacy_id`, source, per-entry layer, content version, verbatim values, and recorded value types in loaded key order; verify via the round-trip diff against the loaded object

- [x] 1.2 Create `packages/game-content/schemas/global_entry.schema.json` specifying required fields, types, and the value-type union; verify every schema-required field has a validator check via the traceability test

- [x] 1.3 Extend `packages/game-content/manifest.json` building with globals inputs, patch lineage, coercion ruleset reference, stored/loaded counts, type-distribution counts, and builder outcome; verify the manifest matches the produced output on every build while prior keys survive the merge untouched

## 2. Builder and validator

- [x] 2.1 Implement the stdlib-only globals builder/validator that verifies patch order, applies only the powerup add, keeps values verbatim with recorded types, validates (key uniqueness, patch-shape conformity, required fields including the union), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [x] 2.2 Document the globals extension in the package README (inputs, layering, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [x] 3.1 Add focused tests covering layering (stored 104 recorded, loaded 105 normalized, drift refusal), classification counts and type distribution, verbatim fidelity, validation failures (divergent patch, missing field), schema-validator traceability including the union, exact round-trip, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where globals normalization checks belong; verify `openspec validate --strict` passes for the change
