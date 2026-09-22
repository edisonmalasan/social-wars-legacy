## Why

Eight M3 slices proved the normalization pattern, including two with pinned stored anomalies (taxonomy opaque codes, darts dynamic boundary). The next smallest coherent slice is the last gameplay-content array domain: `offer_packs` (44 purchasable-pack definitions). Its heterogeneous item shapes were fully characterized at proposal time — five flat bundles, one null entry, 38 nested group pools, and exactly two pinned leaf anomalies — so a bounded fail-closed design with a pinned exception list is possible. Only the 607-entry `images` asset index remains after it.

## What Changes

- Add normalized definitions under `packages/game-content/`: `normalized/offer_packs.json` (44), a JSON schema (`offer-pack`), a stdlib-only builder/validator tool extension, and manifest entries recording sources, content version, shape classes, and legacy IDs.
- Coerce per the field-type survey with documented rules: native scalar amounts and display strings kept verbatim (including the 18 empty `type` values and the single null `items`); `items` shapes preserved verbatim with a recorded shape class per entry (null, flat, pairs, groups); flat leaves, pair firsts, and group leaves validated against the normalized items legacy-ID set with references carried in stored order; pair seconds recorded as opaque numbers; the two pinned anomalies — pair second `35` in offer 4 and float `1072.1224` in offer 35 — preserved verbatim with manifest notes under an exact-match allowlist. Every definition preserves `legacy_id` as the decimal id.
- Normalize from stored content directly (no patch targets `offer_packs`; the builder refuses patch drift and active mods explicitly).
- Validate: id uniqueness, reference resolution outside the pinned allowlist, pair/group structural conformity, required schema fields, and schema-validator traceability. Round-trip evidence: re-emitted legacy-shaped entries diffed against stored content exactly.
- Leave all legacy content, patches, and behavior unchanged; touch no other content key and claim no gameplay parity.

## Source-grounded scope

References below are proposal-time measurements from direct reads; the implementation must verify them against source rather than trusting this list.

| Fact | Value |
| --- | --- |
| `offer_packs` entries | 44; uniform scalar keys (`id`, `cost_cash`, `gold`, `wood`, `steel`, `oil`, `xp`, `enabled`, `position`, `mana` native ints; `name`, `type` strings with `type` empty in 18); `items` null in 1 entry (id 18, Premium Account), flat int arrays in 5 (all leaves resolving, repetition as quantity), nested groups in 38 |
| Nested shapes | 1 entry of len-2 pairs (id 4: firsts resolve, seconds opaque), 9 of len-3 triples, 3 of len-5, 24 of mixed len-3/6, 1 of mixed len-3/5/6; every group leaf resolves except the single float |
| Pinned anomalies | Exactly two: `(offer 4, 35)` unresolving pair second and `(offer 35, 1072.1224)` float where sibling offers carry `1072, 1224`; the builder allowlists exactly these and fails on any other unresolving leaf |
| Patch interaction | None: no active patch targets `offer_packs`; mods pipeline must stay inactive |
| Cross-references | One edge: flat/pair-first/group leaves → normalized items `legacy_id` set (quest-precedent pattern); pair seconds and anomalies are opaque, not refs |
| Served bytes | Out of scope |

## Capabilities

### New Capabilities

- `offers-normalization`: Normalized offer-pack definitions with shape classes, schema, builder/validator, round-trip evidence, and manifest entries.

### Modified Capabilities

None.

## Impact

Extends `packages/game-content/` (one normalized file, one schema, builder/validator, manifest `offers` section) plus focused tests and documentation links. Uses Python 3.9 standard-library tooling with no dependency upgrade, server import, network, browser, Flash, save mutation, or gameplay change. The `images` asset index, domain model, and Godot loading remain future work; this change does not claim them.
