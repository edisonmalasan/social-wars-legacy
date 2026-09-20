## 1. Normalized package

- [ ] 1.1 Create `packages/game-content/normalized/expansion_prices.json` (98 definitions), `town_prices.json` (4 definitions), `map_prices.json` (4 definitions), and `level_ranking_reward.json` (50 definitions) with one definition per stored entry, each preserving `legacy_id`, source, content version, verbatim native fields, and resolved ranking unit references, with schedule order preserved; verify via the round-trip diff against stored content

- [ ] 1.2 Create `packages/game-content/schemas/expansion_price.schema.json`, `town_price.schema.json`, `map_price.schema.json`, and `level_ranking_reward.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [ ] 1.3 Extend `packages/game-content/manifest.json` building with economy inputs, coercion ruleset reference, definition counts, ranking reference-edge counts, and builder outcome; verify the manifest matches the produced output on every build while items/quests/tables keys survive the merge untouched

## 2. Builder and validator

- [ ] 2.1 Implement the stdlib-only economy builder/validator that loads stored schedules, keeps all native fields verbatim, validates (positional uniqueness, non-negative amounts, ranking 50..1 coverage, unresolvable ranking unit references against the committed normalized items outputs, required fields), writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [ ] 2.2 Document the economy extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [ ] 3.1 Add focused tests covering classification counts (98/4/4/50), verbatim fidelity, validation failures (duplicate position, negative amount, ranking gap, unresolvable reference, missing field), schema-validator traceability, round-trip exact equality, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [ ] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where economy normalization checks belong; verify `openspec validate --strict` passes for the change
