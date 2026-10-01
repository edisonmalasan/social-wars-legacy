# Spec Delta

## MODIFIED Requirements

### Requirement: Unit-movement evidence and claim limits

The change SHALL commit a deterministic `unit-movement-report-v1` report recording the placement
fields verbatim, the committed velocity and footprint distributions with their zero-consumer
statements, the movement-command inventory with each command's checks and non-checks, the
client-writable instant recording, the corpus measurement, the tile-geometry gap, the
established-versus-derived split, and the explicit non-claims, byte-identical across reruns. The
non-claims SHALL state: no Flash, Ruffle, ActionScript, or browser executed; **no velocity-based
travel time, path, terrain or elevation interaction, occupancy, bounds, readiness, or
interpolation is implemented**; **the committed movement fields are read by no legacy branch** and
are reported as content only; **no unit-specific movement command exists and none was invented**;
**no unit is placed or moved**, and the corpus holds no unit row; **no executed-legacy fixture was
**no animation is implemented, and that refusal belongs to the `godot-unit-animations`
capability**, which records the five committed asset labels and refuses every playback rule (this line's own `animate_move` entry in its absent-helper list is one of them);
timeline linkage only, never playback correctness; **no pixel parity is claimed** and the tile
geometry remains a recorded gap; and **no windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-movement/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: Animation and parity are not claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no animation or playback is implemented, that the converted unit package establishes linkage only, and that no pixel parity or windowed capture is claimed

#### Scenario: The animation refusal has one owner
- **WHEN** this requirement's non-claim that no animation is implemented is read
- **THEN** it names `godot-unit-animations` as the single owner of the animation refusals, so the movement capability records that no animation exists here without re-deriving why, and the two capabilities cannot disagree about whether a unit moves with an animation
