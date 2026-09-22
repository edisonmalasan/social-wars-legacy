## 1. Normalized package

- [x] 1.1 Create `packages/game-content/normalized/inventory_items.json` (90 definitions), `categories.json` (6 definitions), and `unit_collection_categories.json` (20 definitions) with one definition per stored object entry, each preserving `legacy_id` as the stored key, source, content version, coerced numerics, verbatim strings, validated unit references, and gap/uniformity notes, in stored key order; verify via the round-trip diff against stored content

- [x] 1.2 Create `packages/game-content/schemas/inventory_item.schema.json`, `category.schema.json`, and `unit_collection_category.schema.json` specifying required fields, types, and shapes; verify every schema-required field has a validator check via the traceability test

- [x] 1.3 Extend `packages/game-content/manifest.json` building with taxonomy inputs, coercion ruleset reference, definition counts, reference-edge counts, opaque-code gap notes, and builder outcome; verify the manifest matches the produced output on every build while items/quests/tables/economy/social keys survive the merge untouched

## 2. Builder and validator

- [x] 2.1 Implement the stdlib-only taxonomy builder/validator that loads stored objects, coerces per documented rules, validates (key uniqueness, non-negative amounts, unresolvable collection units references, unresolvable stored inventory_ids keys, required fields), records category codes as opaque with a note, writes output only on success, and exits 0/non-zero; verify with a clean build plus failure-case runs

- [x] 2.2 Document the taxonomy extension in the package README (inputs, rules, validation gates, exit codes, evidence, containment); verify the documented invocation leaves legacy sources and saves unchanged

## 3. Regression tests

- [x] 3.1 Add focused tests covering classification counts (90/6/20), coercion rules, validation failures (duplicate key, negative amount, unresolvable reference, missing field), schema-validator traceability, round-trip fidelity modulo documented coercions, manifest consistency and merge preservation, and containment; verify the suite exits 0

## 4. Documentation and validation

- [x] 4.1 Update documentation links and the executed-check references in AGENTS.md/README where taxonomy normalization checks belong; verify `openspec validate --strict` passes for the change
