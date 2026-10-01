# Spec Delta

## MODIFIED Requirements

### Requirement: Committed asset linkage only

A definition names its committed sprite reference, and the model MAY report **whether** that
reference resolves through the committed asset-ID registry together with its recorded
**The animation reading of that asset is delegated to the `godot-unit-animations`
capability** — this capability owns whether the committed sprite reference
*resolves*, and that capability owns what the asset's recorded timeline contains — so
sprite resolution and animation linkage each have one owner and cannot drift apart. This
capability SHALL establish no rendering
no visual fidelity, and no gameplay semantics for any unit, and SHALL NOT claim that a unit
can be drawn, animated, or played.

#### Scenario: Sprite linkage is reported, not rendered

- **WHEN** a definition is inspected for its sprite reference
- **THEN** the model may report whether the committed reference resolves and its recorded status, and claims nothing about rendering, animation, or visual fidelity

#### Scenario: No visual or behavioural claim is made

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no unit is rendered, animated, or played by this change, and name the animation, movement, and behaviour deliver lines as undelivered

#### Scenario: The animation reading has one owner

- **WHEN** a definition's committed sprite reference is inspected
- **THEN** this capability reports whether it resolves and through which recorded status, while the labels, frame positions, per-sprite frame counts, and recorded rate come from the `godot-unit-animations` projection rather than a second implementation here, so the two cannot drift apart

#### Scenario: Neither owner claims playback
- **WHEN** either capability's claim limits are read
- **THEN** both state that no animation is played, animated, or rendered, and that the converted unit package establishes asset and timeline **linkage** only, never playback correctness or gameplay behaviour
