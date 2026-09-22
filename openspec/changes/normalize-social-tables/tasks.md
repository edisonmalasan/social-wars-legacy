## 1. Normalized package

- [ ] 1.1 Create `packages/game-content/normalized/neighbor_assists.json` (5 definitions), `findable_items.json` (10 definitions), and `social_items.json` (26 definitions) with one definition per stored entry, each preserving `legacy_id`, source, content version, verbatim native amounts, verbatim display strings, and uniformity notes, with entry order preserved; verify via the round-trip diff against stored content

- [ ] 1.2 Create `packages/game-content/schemas/neighbor_assist.schema.json`, `findable_item.schema.json`, and `social_item.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [ ] 1.3 Extend `packages/game-content/manifest.json` building with social inputs, coercion ruleset reference, definition counts, uniformity notes, and builder outcome; verify the manifest matches the produced output on every build while items/quests/tables/economy keys survive the merge untouched

## 2. Builder and validator

- [ ] 2.1 Implement the stdlib-only social builder/validator that loads stored tables, keeps all native amounts and display strings verbatim, validates (positional/id uniqueness, non-negative amounts, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [ ] 2.2 Document the social extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [ ] 3.1 Add focused tests covering classification counts (5/10/26), verbatim fidelity, validation failures (duplicate id, negative amount, missing field), schema-validator traceability, round-trip exact equality, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where social normalization checks belong; verify `openspec validate --strict` passes for the change
