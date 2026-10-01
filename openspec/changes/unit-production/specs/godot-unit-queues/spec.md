# Spec Delta

## MODIFIED Requirements

### Requirement: No elapsed-time evaluation and no completion

The client SHALL NOT compute whether a queue is complete, how much time remains, or any
progress ratio, and this capability SHALL introduce **no** completion of a queue and **no**
materialisation of a unit from one. This is a **recorded property of the legacy contract,
not a missing feature**: the legacy server never reads a queue's start instant to evaluate
elapsed time, and no legacy command completes a queue or creates a unit from it. The
`godot-unit-production` capability makes that absence **auditable** by recording every
legacy branch that can place a row on the map with the source of its item id named, and
by showing that **no** such branch derives an item id from a completed queue, from a
duration, or from committed production content — four of the five take the id straight
from the client and the fifth moves a row that already existed. A future
line MAY introduce completion only as its own deliverable, with its own evidence.

#### Scenario: No readiness is computed

- **WHEN** a queue is projected
- **THEN** the projection offers no completion test, no remaining time, and no progress ratio, because the legacy server has no such rule to reproduce

#### Scenario: The absence is stated, not implied

- **WHEN** this capability's specification is read
- **THEN** it states that the legacy server neither evaluates elapsed time nor completes a queue, and names that absence as a recorded contract rather than a gap to be filled here

#### Scenario: No unit is created

- **WHEN** this capability's diff is inspected for unit creation
- **THEN** no command, path, or projection creates, trains, spawns, or places a unit from a queue

#### Scenario: The absence is auditable, not only asserted
- **WHEN** the absence of any queue-derived unit creation is examined
- **THEN** the `godot-unit-production` inventory names every legacy branch that can place a row with its item id's source, and no inventoried branch derives an id from a completed queue, a duration, or committed production content, so the absence rests on the recorded entry paths rather than on a search that found no completion command
