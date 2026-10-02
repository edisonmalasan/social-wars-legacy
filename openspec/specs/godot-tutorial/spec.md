# godot-tutorial
## Purpose
Deliver the M9 tutorial line: the tutorial-state projection of the one committed flag, the one-branch gate recorded as data including its nine-value hole, the intent-only operation, the refused input shapes whose legacy behaviour is an unhandled error, the committed-content absences recorded as absences rather than filled, and the executed-legacy capture of the one reachable transition.
## Requirements
### Requirement: The tutorial state is projected verbatim and fails closed

The client SHALL expose a player's tutorial state as a typed, read-only projection
carrying the recorded completion flag exactly as stored, reporting it **verbatim**
with **no** value derived from another. It SHALL derive **no** step, **no** progress
ratio, **no** remaining time, and **no** completion, and it SHALL never present an
absent, wrongly-typed, or unresolvable state as a resolved one. Because the flag
lives in the save-level `playerInfo` record and not in any map record, the
projection SHALL read it from `playerInfo` and SHALL report **no** `playerInfo`
field as belonging to a map.

#### Scenario: The recorded flag is reported verbatim

- **WHEN** a player's tutorial state is projected
- **THEN** the completion flag is reported exactly as recorded and no step, progress
  ratio, remaining time, or completion is derived from it or from any other field

#### Scenario: The flag is read from the save-level record

- **WHEN** a player's tutorial state is projected
- **THEN** the flag is read from the save-level player record and no map record is
  consulted for it

#### Scenario: An unresolvable state is reported as unresolvable

- **WHEN** the player record is absent, is of the wrong type, or omits the flag
- **THEN** the projection reports the state as unresolvable with its recorded state
  intact and never presents a false or default completion as a resolved one

### Requirement: The tutorial gate is recorded as data, including its nine-value hole

The client SHALL record the legacy gate exactly as committed — that completion
follows a disjunction of "the step is at least twenty-five" **or** "the step is
exactly fifteen", applied to a client-supplied step. It SHALL record that the nine
values from sixteen through twenty-four inclusive **do not** complete the tutorial,
that there is **no** upper bound and **no** lower bound, that **no** type check is
applied, and that a value of a non-numeric type, a missing step, and a null step
are each answered by the legacy server with an unhandled error. These SHALL be
recorded as the committed rule and SHALL NOT be re-derived, widened, or narrowed.

#### Scenario: Both arms of the disjunction are recorded

- **WHEN** the gate is recorded
- **THEN** it records the "at least twenty-five" arm and the "exactly fifteen" arm
  as a disjunction over the client-supplied step

#### Scenario: The hole between the arms is recorded

- **WHEN** the gate is recorded
- **THEN** it records that every step from sixteen through twenty-four inclusive
  does not complete the tutorial

#### Scenario: The absent bounds and the absent type check are recorded

- **WHEN** the gate is recorded
- **THEN** it records the absence of any upper bound, any lower bound, and any type
  check, and records each of the three unhandled-error input shapes

### Requirement: A tutorial action is a server-derived intent, and no client outcome is trusted

The operation SHALL accept **only** a tutorial step. It SHALL derive completion
server-side by applying the committed gate to that step, and it SHALL **never**
accept, read, or honour a client-supplied completion outcome, a client-supplied
stored flag, or a client-supplied resource vector. A step that does not satisfy the
committed gate SHALL leave every recorded value unchanged.

#### Scenario: Completion is derived, never supplied

- **WHEN** a client reports a tutorial step
- **THEN** the operation derives completion by applying the committed gate and
  never reads a client-supplied outcome, stored flag, or resource vector

#### Scenario: A step outside the gate changes nothing

- **WHEN** a client reports a step that does not satisfy the committed gate
- **THEN** no recorded value changes and the operation reports that nothing changed

### Requirement: A non-numeric, missing, or null step is refused, and the divergence is recorded

The operation SHALL refuse a step that is not an integer, a missing step, and a null
step, each with its own named refusal code, an empty payload, and no state change.
The capability SHALL record that the legacy server instead answers all three with an
unhandled server error, and SHALL record the refusal as a **deliberate divergence
in failure handling only**: the legacy state transitions for every accepted step
are reproduced exactly, and no accepted step's outcome differs.

#### Scenario: Each invalid input shape has its own named refusal

- **WHEN** a step is not an integer, is absent, or is null
- **THEN** the operation refuses with the corresponding named code, an empty
  payload, and no state change

#### Scenario: The divergence from the legacy error is recorded

- **WHEN** the refusal set is inspected
- **THEN** it records that the legacy server answers all three shapes with an
  unhandled error and that only the failure handling differs, with no accepted
  step's outcome changed

### Requirement: No tutorial reward is paid and no stored resource moves

No tutorial action SHALL pay any reward, grant any item, or move any stored
resource. Every tutorial action's post-execution proof SHALL assert that **every**
stored resource is unchanged, and that proof SHALL be non-tautological because a
legacy transaction has been captured in which one client-sent request both
completed the tutorial and moved every stored resource.

#### Scenario: No reward is paid

- **WHEN** a tutorial action completes
- **THEN** no reward, item, currency, or experience is granted and the absence of
  any committed tutorial reward is recorded

#### Scenario: Every stored resource is proven unchanged

- **WHEN** any tutorial action is executed
- **THEN** the post-execution state shows every stored resource unchanged, and the
  check is anchored to a captured legacy transaction in which the same command moved
  every stored resource

### Requirement: No stored tutorial step exists, and no progress is derived from one

The capability SHALL record that the legacy server stores **no** tutorial step: the
step is a transient value used only for a comparison and a log line, and is never
persisted. It SHALL therefore record that a partially-progressed save is
unrepresentable in the legacy save shape, and it SHALL NOT introduce a stored step,
a resume position, a per-step progress record, or any derivation that would require
one.

#### Scenario: The absence of a stored step is recorded

- **WHEN** the tutorial's stored state is inspected
- **THEN** it records that no step is persisted, that a partially-progressed save is
  unrepresentable, and that no stored step, resume position, or per-step progress is
  introduced

### Requirement: The completion flag is one-way in the legacy server, and nothing is read from it

The capability SHALL record that the legacy server writes the completion flag at
exactly one site, always with the same value, and that **no** legacy module reads
it to decide anything, including the client-facing responses — the flag reaches the
client only because the whole player record is included wholesale. It SHALL record
that there is no reset, no clearing, and no migration of the flag, and it SHALL NOT
add an un-complete path.

#### Scenario: The flag's single writer and zero readers are recorded

- **WHEN** the flag's legacy usage is recorded
- **THEN** it records one write site with one value, zero reader modules, no reset,
  no clearing, and no migration, and that the flag reaches the client only through
  the wholesale inclusion of the player record

#### Scenario: No un-complete path is added

- **WHEN** a player is already complete
- **THEN** no operation clears or lowers the flag and the capability records that
  none exists

### Requirement: The executed-legacy fixture captures the one reachable transition

The repository SHALL capture an executed-legacy fixture for the tutorial, taken
against the real legacy server over a disposable corpus. The fixture SHALL record
the one transition the committed corpus can reach — the flag moving from its
initial value to complete — together with the request that caused it, the response,
the before and after save state, and the proof that exactly the one flag changed.
The fixture SHALL record that **no** absence of a fixture is claimed, because the
committed corpus's only incomplete save is the new-player template and the
transition is therefore genuinely exercisable.

#### Scenario: The transition is captured against the real server

- **WHEN** the fixture is captured
- **THEN** it records the request, the response, the before and after state, and the
  exact set of changed fields, taken from the real legacy server over a disposable
  corpus

#### Scenario: Exactly one field changed

- **WHEN** the captured transition is inspected
- **THEN** the changed field set is exactly the completion flag and every other
  recorded value is byte-identical

#### Scenario: No fixture absence is claimed

- **WHEN** the fixture is inspected
- **THEN** it records that no absence is claimed and names the committed corpus save
  whose initial value makes the transition reachable

### Requirement: The committed tutorial content absence is recorded and never filled

The capability SHALL record that the committed game configuration contains **no**
tutorial key at any depth and that the committed normalized content packages
contain **no** tutorial entry, and therefore that there is **no** committed step
list, step count, gate definition, tutorial text, or reward from which anything
could be derived. It SHALL NOT invent any of them, and it SHALL NOT name any
delivered identifier after a tutorial content field that does not exist.

#### Scenario: The content absence is recorded

- **WHEN** the committed content is inspected for tutorial data
- **THEN** the capability records that no tutorial key exists in the configuration at
  any depth and no tutorial entry exists in any normalized package

#### Scenario: Nothing is invented to fill the absence

- **WHEN** no committed tutorial content exists
- **THEN** no step list, schedule, gate table, tutorial text, or reward is invented
  and no delivered identifier is named after a nonexistent content field

### Requirement: Tutorial evidence and claim limits

The capability SHALL record its evidence and its limits. It SHALL claim parity only
for the one recorded transaction against the fresh-player corpus, SHALL record that
the gate thresholds are the legacy server's committed rule and are **never** claimed
to be what the Flash client counts as a step, SHALL record that nothing is claimed
about how the client renders tutorial progress, SHALL record that no pixel parity
and no windowed capture are claimed because nothing is rendered, and SHALL record
that the missing step bounds and the input-shape divergence are **deliberate** and
are not closed here.

#### Scenario: The parity claim is bounded

- **WHEN** the evidence is summarised
- **THEN** it claims parity for one recorded transaction against the fresh-player
  corpus and no more

#### Scenario: The client is not claimed

- **WHEN** the gate is described
- **THEN** it records that the thresholds are the legacy server's rule and makes no
  claim about what the Flash client counts as a step or how it renders progress

#### Scenario: The deliberate divergences are named

- **WHEN** the limits are inspected
- **THEN** they name the refusal of the three unhandled-error input shapes and the
  reproduced absence of step bounds, and record that neither is closed here
