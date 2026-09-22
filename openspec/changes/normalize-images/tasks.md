## 1. Normalized package

- [x] 1.1 Create `packages/game-content/normalized/images.json` (607 definitions, one per stored path) with `legacy_id`, source, content version, verbatim path, and locale in stored document order; verify via the round-trip diff against the stored object

- [x] 1.2 Create `packages/game-content/schemas/image_asset.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [x] 1.3 Extend `packages/game-content/manifest.json` building with images inputs, coercion ruleset reference, definition counts, extension distribution, and builder outcome; verify the manifest matches the produced output on every build while prior keys survive the merge untouched

## 2. Builder and validator

- [x] 2.1 Implement the stdlib-only images builder/validator that loads the stored object, keeps paths verbatim, enforces locale `en`, validates (key uniqueness/non-emptiness, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [x] 2.2 Document the images extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [x] 3.1 Add focused tests covering classification counts (607, all-`en`, extension split), verbatim fidelity, validation failures (non-`en` locale, duplicate key, missing field), schema-validator traceability, exact round-trip, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where images normalization checks belong; verify `openspec validate --strict` passes for the change
