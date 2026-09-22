## 1. Normalized package

- [x] 1.1 Create `packages/game-content/normalized/darts_items.json` (27 definitions, one per patched entry) with `legacy_id`, source, patch lineage, content version, verbatim pools, verbatim `start_date` inputs, and resolved references in patched order; verify via the round-trip diff against the patched array

- [x] 1.2 Create `packages/game-content/schemas/darts_item.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [x] 1.3 Extend `packages/game-content/manifest.json` building with darts inputs, patch lineage, coercion ruleset reference, stored/patched counts, reference-edge counts, dynamic-boundary notes, and builder outcome; verify the manifest matches the produced output on every build while prior keys survive the merge untouched

## 2. Builder and validator

- [x] 2.1 Implement the stdlib-only darts builder/validator that verifies patch order, applies only the `targets` replace, keeps pools/dates verbatim, validates (id uniqueness, reference resolution, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [x] 2.2 Document the darts extension in the package README (inputs, layering, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [x] 3.1 Add focused tests covering layering (stored 30 recorded, patched 27 normalized, drift refusal), classification counts, coercion rules, validation failures (duplicate id, unresolvable reference, missing field), schema-validator traceability, exact round-trip, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where darts normalization checks belong; verify `openspec validate --strict` passes for the change
