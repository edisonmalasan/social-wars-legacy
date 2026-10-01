# Spec Delta

## MODIFIED Requirements

### Requirement: Unit instances are rows, not widened definitions

The client SHALL expose a player-owned **unit instance** as a typed, read-only
`UnitInstance` that **wraps** one legacy map row together with its resolved
`UnitDefinition`, and SHALL be a **distinct type** from the static definition rather than
An instance SHALL read the row's own identity and state verbatim — item id, row instant,
player team, and its `attr` bag — and SHALL **delegate the placement view** (cell
coordinates, orientation, and committed footprint and `velocity`) to the
`godot-unit-movement` capability, so the instance owns the row while the movement capability
owns the placement reading of it. An instance
coordinates, row instant, orientation, and player team — and its `attr` bag, and SHALL
read its identity from its resolved definition rather than restating the definition's
fields. A row whose committed item `type` is not a unit SHALL be **rejected**, never
coerced into an instance, and the instance surface SHALL NOT mutate its row or its
definition.

#### Scenario: An instance wraps a row and its definition

- **WHEN** a unit instance is built from a committed map row and its resolved definition
- **THEN** it carries the row's item id, cell, instant, orientation, and player team verbatim, holds the definition rather than copying it, and the definition remains unchanged

#### Scenario: A non-unit row is rejected, not coerced

- **WHEN** a row is offered whose committed item `type` is not a unit
- **THEN** no instance is produced, the failure names the row's key and its committed type, and nothing is coerced

#### Scenario: A definition is never mutated into an instance

- **WHEN** an instance is inspected for a field that could hold player state
- **THEN** the definition it holds still has none, and the instance's own player state lives on the instance, never on the definition

#### Scenario: The placement view has one owner

- **WHEN** a unit instance's placement is read
- **THEN** the cell, orientation, and committed footprint come from the `godot-unit-movement` capability's projection rather than a second implementation here, so the row's owner and the placement's owner cannot drift apart

#### Scenario: The instance still owns the row

- **WHEN** a unit instance is inspected
- **THEN** its item id, row instant, player team, garrison, and `attr` bag remain read here, so delegating the placement view did not move ownership of the row
