# Spec Delta

## MODIFIED Requirements

### Requirement: The delivered surface is a typed read-only projection of persisted social state, and it implies no social feature
The capability SHALL project the social state a committed save carries, and SHALL
report it verbatim. It SHALL NOT imply that a **visits**, **scores**, or **social
rewards** feature exists.

The name `godot-social-state` was chosen over `godot-friends` on an explicitly
recorded premise: that a capability named `godot-friends` "would claim exactly what
this one measures to be absent." **That premise has been measured false** — a real
server-side roster surface exists and is delivered by `godot-friends`. This
requirement therefore records an **ownership hand-off** rather than a standing
refusal:

- `godot-social-state` owns the persisted social **state fields** — the measured
  fields, their recorded storage document, their writers and readers, and the
  zero-consumer census re-derived per run.
- `godot-friends` owns the **roster projection** over loaded villages, which is a
  projection of *other players' saves*, not of this capability's measured state
  fields.
- The original reasoning **survives in amended form**: neither capability names a
  delivered surface after a social *relationship*, because none exists in the
  preserved server. `godot-friends` refuses the relationship vocabulary for the
  same reason this capability does — the reservation was conditional on the roster
  being absent, and the roster's *absence* is what has been disproved, not the
  absence of a relationship.
- No measured state field moves to `godot-friends`. The roster's eighteen-key entry
  is **not** a `privateState` field and is not one of the nineteen.

#### Scenario: Review the delivered scope
- **WHEN** a maintainer reviews the capability
- **THEN** the delivered surface is a projection of stored social state
- **AND** no requirement in this capability describes a visits, scores, or social-rewards behaviour

#### Scenario: Review the hand-off
- **WHEN** a maintainer asks which capability owns the roster
- **THEN** the roster projection is owned by `godot-friends`
- **AND** no measured social state field is owned by that capability
- **AND** the recorded reason the name was originally withheld is stated together with the measurement that falsified it
