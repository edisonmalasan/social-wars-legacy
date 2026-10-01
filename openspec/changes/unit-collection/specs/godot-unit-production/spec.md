# Spec Delta

## MODIFIED Requirements

### Requirement: No server operation is exposed for production

The client SHALL NOT expose or require a compatibility API operation for production: no route,
no request, and no client intent to create, complete, or award a unit. The compatibility test
suite SHALL remain green **unchanged**. Any client-supplied acquisition key — an item id, a
package id, or an item list — SHALL be recorded as client-supplied and SHALL NOT be treated as
authorising, and the content it might otherwise be validated against is named as belonging to a
later capability. **This finding is completed, not amended**, by the `godot-unit-collection`
capability: the committed collection completion route derives its grant from the committed
collection table and is the **only** content-derived acquisition path, so no committed unit is
obtainable through the client-supplied routes named here — but a unit **is** obtainable
through that one content-derived route, and it is the sole exception.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No client intent is sent

- **WHEN** the client has nothing to produce
- **THEN** it issues no request, and no intent exists to authorise

#### Scenario: Client-supplied acquisition keys are not treated as authority

- **WHEN** an item id, package id, or item list originates from a client argument
- **THEN** it is recorded as client-supplied, and the committed table it might otherwise be validated against is named as a later capability's work rather than enforced or trusted here

#### Scenario: The acquisition finding names the one content-derived route
- **WHEN** this requirement's acquisition finding is read
- **THEN** it names the client-supplied routes as unusable **and** points to the
  `godot-unit-collection` capability for the single content-derived route, so the finding is not
  read as "no committed unit is obtainable anywhere"
