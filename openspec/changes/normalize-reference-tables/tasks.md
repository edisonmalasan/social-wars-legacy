## 1. Normalized package

- [ ] 1.1 Create `packages/game-content/normalized/magics.json` (10 definitions), `levels.json` (100 definitions), and `sounds.json` (139 definitions) with one definition per stored entry, each preserving `legacy_id`, source, content version, coerced fields, and recorded asset refs, with XP curve order preserved; verify via the round-trip diff against stored content

- [ ] 1.2 Create `packages/game-content/schemas/magic.schema.json`, `level.schema.json`, and `sound.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [ ] 1.3 Extend `packages/game-content/manifest.json` building with tables inputs, coercion ruleset reference, definition counts, and builder outcome; verify the manifest matches the produced output on every build

## 2. Builder and validator

- [ ] 2.1 Implement the stdlib-only tables builder/validator that loads stored `magics`/`levels`/`sounds`, coerces per documented rules, validates (duplicates, non-negative amounts, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [ ] 2.2 Document the tables extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [ ] 3.1 Add focused tests covering classification counts (10/100/139), coercion rules, validation failures (duplicate ID, bad amount, missing field), schema-validator traceability, round-trip fidelity modulo documented coercions, manifest consistency, and containment; verify the suite exits 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where tables normalization checks belong; verify `openspec validate --strict` passes for the change
