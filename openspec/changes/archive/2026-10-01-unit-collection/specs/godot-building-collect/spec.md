# Spec Delta

## MODIFIED Requirements

### Requirement: Collection payout derivation
The service SHALL derive a collection's resource vector entirely from committed content and the addressed row's own state, never from client input: the amount from the item's committed collection amount, the resource from its committed collection type, the experience from its committed collection experience, each scaled by the committed ladder rung the row has actually reached, with the elapsed time measured from the row's recorded collection instant and clamped at the top rung. Every rung and every rule behind that derivation SHALL be marked derived-provisional wherever the derivation is recorded, because no legacy branch reads the content that describes it. A collection whose item records a non-zero collection cap SHALL be refused rather than paid under an invented cap semantics, a collection whose item records a resource type outside the committed set SHALL be refused rather than paid into an assumed resource, and the vector's unread slot and its experience-free resource slot SHALL be left zero.

#### Scenario: A collection pays the committed amount at the reached rung

- **WHEN** a collect intent is executed for a row that has reached a committed ladder rung
- **THEN** the applied vector carries the item's committed amount in the slot its committed resource type names and its committed experience, each scaled by that rung's committed multiplier, and no client-supplied value influences either

#### Scenario: The elapsed time is clamped at the top rung

- **WHEN** a row's elapsed time exceeds the last committed rung
- **THEN** the top rung's committed multiplier is used and no larger amount is derived or extrapolated

#### Scenario: A capped or unmappable item is refused, not paid

- **WHEN** the item records a non-zero collection cap, or a resource type outside the committed set
- **THEN** the service answers a structured JSON error, the legacy dispatcher never runs, and the corpus save is unchanged

#### Scenario: The ladder is marked derived wherever it is recorded

- **WHEN** the derivation is recorded in the envelope module, the fixture README, the application documentation, or the structural report
- **THEN** the amount formula, the experience scaling, the sub-first-rung behavior, the cap semantics, the shared-field rule, and the cash/experience semantics are each marked derived-provisional rather than observed

#### Scenario: The derived payout applies to buildings only
- **WHEN** a committed item's collect-related fields are inspected for income
- **THEN** the derived payout is computed only for an item carrying a positive committed collect amount, **no committed unit carries one**, and no collect field is read by the legacy service, so no unit income is derived — the `godot-unit-collection` capability supplies the sharper position that this is a property of the content and the server, not of the corpus
