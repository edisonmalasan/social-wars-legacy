## Purpose

Provide normalized, schema-validated inventory, shop-taxonomy, and unit-collection definitions for the legacy object-keyed classification content while preserving every legacy key without changing legacy behavior.

## ADDED Requirements

### Requirement: Classified normalized taxonomy definitions
The package SHALL contain one normalized definition per stored entry of `inventory_items`, `categories`, and `units_collections_categories`. Each definition SHALL preserve `legacy_id` as the stored object key verbatim, record its content source and version, and carry coerced numerics, verbatim display strings, and validated unit references. Entry order SHALL follow stored key order.

#### Scenario: Review domain coverage
- **WHEN** the stored taxonomy objects are compared with the normalized package
- **THEN** all 90 inventory items, 6 categories, and 20 unit-collection groups are represented with preserved legacy keys and order

#### Scenario: Distinguish validated references from opaque codes
- **WHEN** a maintainer reviews a collection units array or an item category code
- **THEN** the units integers are identified as validated item references while category codes are identified as opaque classification codes with a documented gap note

### Requirement: Documented object-key coercions
String-encoded inventory numerics (`id`, `cashPrice`, `droppable`, `dropRate`, `dropsFrom`) SHALL coerce to integers citing the field-type survey; category ids and localized names SHALL be kept verbatim with `sub` arrays carried as observed; collection native integers SHALL be kept verbatim with `units` arrays validated and the single null `costs` preserved as null. The uniformly-empty collection `category_name_el` (20 of 20) SHALL be preserved verbatim with a manifest note. Stored item `category_id`/`subcategory_id` codes without category entries SHALL be recorded as opaque codes with a manifest note, never treated as references. No value SHALL be rebalanced, renamed for gameplay, or assigned a new gameplay meaning.

#### Scenario: Review a coerced inventory price
- **WHEN** a maintainer reviews a normalized inventory item
- **THEN** the integer price and the coercion rule from the string-encoded source are identified

#### Scenario: Review evidence limitations
- **WHEN** a maintainer reviews a normalization rule
- **THEN** the rule cites survey evidence and states that normalization is a representation change, not gameplay parity

### Requirement: Validation and round-trip evidence
The builder SHALL validate key uniqueness, non-negative amounts, unresolvable collection `units` references, unresolvable stored `inventory_ids` keys, required schema fields, and schema-validator traceability. It SHALL re-emit legacy-shaped keyed objects and diff them against stored content modulo documented coercions, failing on unexplained differences. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing normalized output only on success.

#### Scenario: Detect an unresolvable collection reference
- **WHEN** a collection units integer does not resolve against the normalized items legacy-ID set
- **THEN** validation fails with a non-zero exit identifying the offending definition

#### Scenario: Prove round-trip fidelity
- **WHEN** normalized taxonomy definitions are re-emitted to legacy shape
- **THEN** the result matches stored content except for documented coercions

### Requirement: Preservation-safe normalization tooling
Normalization SHALL NOT import or execute legacy application modules, read runtime saves, contact a network, start a server, open a browser, or execute Flash. It SHALL NOT modify any file under `config/`, `mods/`, saves, or other legacy sources; normalized output SHALL live separately under `packages/game-content/`. The mods pipeline SHALL stay inactive; any active mod fails the build. The builder SHALL refuse patch drift targeting any of the three keys.

#### Scenario: Build without legacy side effects
- **WHEN** the builder succeeds or fails
- **THEN** legacy sources, saves, and repository inputs remain unchanged and no legacy runtime activity occurs
