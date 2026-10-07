# auction-schedule-normalization Specification

## Purpose

Provide normalized, schema-validated auction schedule definitions for the
committed `config/auctionhouse.json` table, preserving every legacy value
verbatim while making the three committed auctions — and the fact that they name
real committed units — visible to the modern client for the first time.

## Requirements

### Requirement: Layered normalized auction definitions

The package SHALL contain one normalized definition per committed entry of
`config/auctionhouse.json`, preserving committed order. Each definition SHALL
preserve `legacy_id` as the committed `uuid` **string** verbatim, and SHALL
carry the committed `unit`, `level`, `interval`, `price`, `priceIncrement` and
`betPrice` values without alteration. Because the source table is a standalone
file rather than a key of `config/main.json`, each definition SHALL record that
file as its content source.

The `uuid` SHALL remain a string. Coercing it to an integer would be an
unjustified transformation: the module keys its state document by that value
(`auctions.py:106`) and the committed table declares it quoted, so an integer
would claim a type the source does not carry.

#### Scenario: Every committed auction is present, in committed order

- **WHEN** the normalized package is read
- **THEN** it contains exactly three definitions
- **AND** their `legacy_id` values are `"1"`, `"2"`, `"3"`, in that order
- **AND** no entry is added, removed, merged or deduplicated

#### Scenario: The uuid stays a string

- **WHEN** a definition's `legacy_id` is examined
- **THEN** it is the JSON string `"1"`, not the number `1`
- **AND** the committed `unit` value is carried as the integer the source commits

### Requirement: The referenced unit is resolved against the committed items

Each definition SHALL resolve its committed `unit` against the normalized items
package, which is the cross-domain reference edge for this builder, and SHALL
carry the resolved unit's display name. A unit id that does not resolve SHALL be
recorded as unresolved rather than dropped, silently replaced, or invented.

This edge is the reason the schedule is worth normalizing at all: all three
committed auctions name committed endgame units, which makes the table live
content rather than filler.

#### Scenario: All three committed units resolve

- **WHEN** resolution runs against `normalized/units.json`
- **THEN** unit `1167` resolves to `Blue Steel Bahamut`
- **AND** unit `1168` resolves to `Blue Steel Draggy`
- **AND** unit `1226` resolves to `Red Mercury Dragon`
- **AND** zero definitions are recorded as unresolved

#### Scenario: An unresolvable unit is recorded, not dropped

- **WHEN** a committed `unit` id is absent from the normalized items
- **THEN** its definition is still emitted, in committed order
- **AND** it is recorded as unresolved with no display name
- **AND** the failure is reported rather than swallowed

### Requirement: The committed interval is preserved as committed, and the
conversion is named rather than performed

The committed `interval` SHALL be preserved verbatim as committed — in
**minutes** — and the builder SHALL NOT convert it. The conversion to seconds
(`interval * 60`) belongs to the consuming client, where it must live in exactly
one named function, because that is the shape established for `COLLECT_MINUTES`
in `godot-building-collect`.

Preserving the unit in the package keeps the package honest about what the
source says; converting inside the builder would hide the only non-obvious
arithmetic in the surface inside a data file where it is least visible.

#### Scenario: The interval is stored in the committed unit

- **WHEN** a definition is read
- **THEN** its `interval` is the integer the source commits — `120`, `60`, `120`
- **AND** no `seconds` or `duration` field is present on the definition
- **AND** the conversion factor `60` is not recorded as data

### Requirement: The committed price fields are carried and marked unread

Each definition SHALL carry `price`, `priceIncrement` and `betPrice` verbatim.
The package SHALL additionally record that `betPrice` has **zero** consumers in
the preserved server, alongside the measurement that establishes it: the module
contains no occurrence of `gold`, `coins`, `cash`, `wood`, `steel`, `oil`, `xp`,
`mana`, `energy`, `cost` or `apply_resources`, and never calls
`apply_resources`.

Carrying a price that nothing charges is not a defect to fix here. It is the
finding, and marking it in the package is what stops a later line from reading
`betPrice` as a price to honour.

#### Scenario: betPrice is carried and flagged as unconsumed

- **WHEN** any definition is read
- **THEN** its `betPrice` is the integer the source commits — `2` on all three
- **AND** the package records `bet_price_consumed: false`
- **AND** that record cites the zero-consumer measurement rather than asserting
  the price is meaningless

### Requirement: Validation and round-trip evidence

The builder SHALL validate the package with a schema, and SHALL emit exact
round-trip evidence showing that the normalized definitions reproduce the
committed source document field for field. Coercions SHALL be listed explicitly
in the schema; a coercion that cannot be listed is not permitted.

#### Scenario: Round-trip reproduces the committed source

- **WHEN** the normalized package is compared back to `config/auctionhouse.json`
- **THEN** every field of every entry is byte-equal after the documented
  coercions
- **AND** the comparison covers all 7 committed keys across all 3 entries
- **AND** no value is dropped, padded or defaulted

#### Scenario: The builder is repeatable

- **WHEN** the builder runs twice with no change to its inputs
- **THEN** the normalized output and the manifest section are byte-identical
- **AND** no prior manifest section is modified

### Requirement: Preservation-safe normalization tooling

The builder SHALL write only to the normalized package and the package
manifest. It SHALL NOT modify `config/auctionhouse.json`, any legacy module, any
save, or any fixture, and it SHALL NOT import or execute `auctions.py`.

Not importing the module is a deliberate constraint, not an oversight. The
module cannot construct itself (measured: `FileNotFoundError` at
`auctions.py:33`), and importing it would create an `auctions/` state directory
as a side effect of reading committed content.

#### Scenario: No legacy byte changes

- **WHEN** the builder completes
- **THEN** `config/auctionhouse.json` and every legacy root module are unchanged
- **AND** no `auctions/` directory is created in the repository
- **AND** the preservation manifest still verifies

#### Scenario: The module is never imported

- **WHEN** the builder's import graph is inspected
- **THEN** `auctions` is absent from it
- **AND** no module-level side effect of the auction house is reachable