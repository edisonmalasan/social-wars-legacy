# Spec Delta

## Purpose

Expose a unit's animation asset as a typed, read-only **linkage** projection — the labels, their
recorded frame positions, the per-sprite frame counts, and the recorded frame rate, reported
**strictly as linkage** — together with the animation-field inventory, the recorded non-equivalence
of the committed `max_frame` to the asset's parsed frame count, and the explicit refusals of every
playback rule.

## ADDED Requirements

### Requirement: An animation asset is projected as linkage, never as behaviour

The client SHALL expose a unit's animation asset as a typed, read-only projection carrying the
recorded animation labels, each label's recorded frame position, the per-sprite recorded frame
counts, and the recorded frame rate, each reported **verbatim**. The projection SHALL compute **no**
value from another: no duration from a frame count and a rate, no loop count, no transition, no
playback order, and no intermediate or elapsed frame. An asset that is absent, unreadable, or
carrying no labels SHALL be reported as unresolvable with its recorded state intact, never defaulted
to an empty or nominal animation.

#### Scenario: Labels and frame positions are reported verbatim

- **WHEN** a unit's animation asset is projected
- **THEN** each recorded label and its recorded frame position are reported exactly as recorded, in committed order, with no duration, loop, or transition computed from them

#### Scenario: The recorded rate is reported, never applied

- **WHEN** the projection reports the recorded frame rate
- **THEN** the value is reported as recorded and is never multiplied by a frame count to produce a duration or a frame time

#### Scenario: An unresolvable asset is reported, not defaulted

- **WHEN** a unit's animation asset is absent, unreadable, or carries no labels
- **THEN** the projection reports it as unresolvable with its recorded state intact, and never defaults it to an empty, nominal, or single-frame animation

### Requirement: Committed animation fields are content with no legacy consumer

The client SHALL report the committed `max_frame`, `img_name`, `attack`, `attack_interval`,
`attack_range`, and `velocity` as **content only**, together with the `animal` `properties` flag, and
SHALL record that **no legacy branch reads any of them**. The recorded facts SHALL report the
committed distributions, and SHALL name the earlier committed fields in this project that share the
same zero-consumer property, identifying `max_frame` as the most recent of them.

#### Scenario: The fields are reported, never used

- **WHEN** a unit definition's animation-adjacent fields are inspected
- **THEN** their values may be reported as content, and no duration, loop, transition, priority, trigger, or state selection is computed from any of them

#### Scenario: The zero-consumer fact is recorded with its distributions

- **WHEN** the recorded contracts are inspected
- **THEN** they state that no committed branch reads these fields, report the committed distributions including the near-constant `max_frame`, and name the earlier zero-consumer fields in this project

### Requirement: The committed max_frame is not the asset's frame count

The client SHALL record, as a stated requirement, that the committed `max_frame` is **not** the
parsed frame count of the animation asset its own committed sprite reference names, because for the
one committed converted package the two disagree. The client SHALL record the measured disagreement
itself, SHALL adopt `max_frame` **nowhere** as a frame count, a duration, or a loop bound, and SHALL
**not** claim what `max_frame` means, since the measurement is a single data point.

#### Scenario: The non-equivalence is stated

- **WHEN** the recorded contracts are inspected
- **THEN** they state that the committed `max_frame` and the asset's parsed frame count disagree for the one committed converted package, and report both measured values

#### Scenario: max_frame is adopted nowhere

- **WHEN** this change's diff and the recorded contracts are inspected for a use of `max_frame`
- **THEN** it is reported as content only and is never used as a frame count, a duration, a loop bound, or a state count

#### Scenario: No claim is made about what max_frame means

- **WHEN** the recorded contracts are read
- **THEN** they state that the measurement is one data point, that only one converted unit package is committed, and that what `max_frame` means is not claimed

### Requirement: No legacy branch selects an animation, and no state machine is derived

The client SHALL record that **no** legacy command branch starts, stops, advances, loops, or selects
an animation, and SHALL record the measured command inventory together with the reason each
vocabulary match is a substring artifact rather than an animation command. The client SHALL derive
**no** state machine, transition rule, priority, interrupt, playback order, per-state timing,
animation trigger, or mapping from any legacy command to any recorded state.

#### Scenario: The command inventory is recorded and classified

- **WHEN** the recorded contracts are inspected
- **THEN** the named-branch count and each vocabulary match's reason are recorded, and the count of animation commands is stated as zero

#### Scenario: No state machine is derived from the labels

- **WHEN** the recorded labels are inspected
- **THEN** no transition, next-state, priority, interrupt, or playback-order relation is derived from them, and no legacy command is mapped to any state

### Requirement: Animation is content, not a server operation

Unit animation SHALL be read from the committed content package and the committed converted asset
already on disk, and SHALL NOT require or expose a server operation: no compatibility API route
SHALL be added, no client intent SHALL be sent to animate a unit, and no persistence behaviour SHALL
change. The compatibility test suite SHALL remain green **unchanged**.

#### Scenario: No compatibility surface is added

- **WHEN** this change's diff is inspected against the compatibility service
- **THEN** no route, response field, error code, or persistence behaviour was added, and the compatibility test suite remains green unchanged

#### Scenario: No animate intent is sent

- **WHEN** the client has no state to select
- **THEN** it issues no request, and no intent exists to authorise

### Requirement: No executed-legacy animation fixture is claimed

The change SHALL capture **no** executed-legacy animation fixture, and the non-claims SHALL state
that this is because there is **no animation behaviour for the legacy server to have**, which is a
stronger statement than any corpus limitation. The committed corpus and the delivered fixture
directories SHALL remain byte-identical, and no asset SHALL be re-converted or re-parsed to
manufacture coverage for another unit.

#### Scenario: No fixture is captured, and the reason is stated

- **WHEN** this capability's evidence and claim limits are read
- **THEN** they state that no animation fixture was captured because no animation behaviour exists in the legacy server to capture

#### Scenario: No coverage is manufactured

- **WHEN** this change's verification runs
- **THEN** no conversion or extraction output is regenerated to cover another unit, the committed conversion package and registry manifests stay byte-identical, and the projection's one-package coverage is recorded as such

### Requirement: Unit-animation evidence and claim limits

The change SHALL commit a deterministic `unit-animations-report-v1` report recording the labels and
frame positions verbatim, the per-sprite frame counts, the recorded frame rate, the six-field
inventory with its zero-consumer statements, the `max_frame` distribution and its measured
non-equivalence, the one-package coverage, the established-versus-derived split, and the explicit
non-claims, byte-identical across reruns. The non-claims SHALL state: no Flash, Ruffle, ActionScript,
or browser executed; **no frame duration, loop count, state machine, transition, priority, interrupt,
playback order, per-state timing, animation trigger, or event-to-state mapping is implemented**;
**the committed animation fields are read by no legacy branch** and are reported as content only;
**`max_frame` is not adopted as a frame count** and what it means is not claimed; **no legacy branch
selects an animation**; **no animation is played, animated, or rendered**, and the converted unit
package establishes asset and timeline **linkage** only, never playback correctness; **no claim is
made for any unit other than the one committed converted package**, which is the only coverage
measured; **no executed-legacy fixture was captured**; **no pixel parity is claimed**; and **no
windowed capture is claimed**.

#### Scenario: Commit the report

- **WHEN** the evidence step runs
- **THEN** the deterministic report is committed under `apps/client-godot/evidence/unit-animations/` carrying every required field and non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: Playback and parity are not claimed

- **WHEN** this capability's documentation is read
- **THEN** it states that no animation is played or rendered, that the converted unit package establishes linkage only, and that no pixel parity or windowed capture is claimed
