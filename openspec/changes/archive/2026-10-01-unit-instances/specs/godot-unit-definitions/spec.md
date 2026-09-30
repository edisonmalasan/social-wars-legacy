# Spec Delta

## MODIFIED Requirements

### Requirement: Static definitions are content, not a server operation

Unit definitions SHALL be read from the committed content package through the content
registry and SHALL NOT require or expose a server operation: no compatibility API route
SHALL be added for them, no client intent SHALL be sent to obtain one, and no
server-supplied or client-supplied unit content SHALL be introduced. This capability SHALL
introduce no player-owned unit instance type, no save shape, no instance parsing, and no
garrison or production-queue state: the player-owned instance is specified separately by the
`godot-unit-instances` capability, which wraps a legacy map row and this definition rather than
extending it, so a `UnitInstance` is a distinct type and a definition remains immutable and free of
player state.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No player-owned unit state is introduced

- **WHEN** this change's diff is inspected for player state
- **THEN** no unit instance type, save shape, instance parsing, garrison state, or production-queue state was added

#### Scenario: Enumeration crosses the same verification gate

- **WHEN** the catalog enumerates the domain's legacy IDs
- **THEN** it does so through the content registry's public enumeration accessor over the
  index built during the verified load, cross-checks the enumerated count against the
  registry's reported count, and fails closed on disagreement, and no committed content file
  is read behind the registry's back

#### Scenario: Definitions are read, never fetched

- **WHEN** the client needs a unit definition
- **THEN** it is read from the already-loaded content registry and no request is issued

#### Scenario: The instance is a distinct type, not a widened definition
- **WHEN** a unit instance is constructed from a legacy map row and this definition
- **THEN** it holds the definition rather than extending or copying it, the definition
  remains unchanged and still free of player state, and the instance's own player state
  lives on the instance, so no instance field can migrate into a definition
