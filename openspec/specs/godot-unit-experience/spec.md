# godot-unit-experience

## Purpose

Record the executed-legacy evidence for the legacy unit-experience branch `add_xp_unit`: the
committed fixture that proves what the branch accepts and stores, the fail-closed read-only
projection of a placed row's recorded experience, and the preserved refusal to award experience
from a client-supplied amount.

## Requirements

### Requirement: No experience is awarded from a client amount, and no derivation exists

The client SHALL NOT award, grant, compute, or display a unit-experience award, and SHALL NOT
expose a compatibility route, request, or client intent that could cause one. The capability
SHALL record **why** no award is reproduced: the amount reaches the field as a client argument
with **no validation of any kind**, including no integer coercion, and the field has **no
reader** anywhere in the legacy source — it is written twice and read zero times. The recorded
contract SHALL further state that the legacy service's own resource vector, applied before the
dispatch, moves the **player's** experience with a zero floor while the row accumulator has
**no floor and no bound**, and that one request can therefore move both quantities from
client-supplied amounts. This capability SHALL NOT introduce an experience schedule, a
threshold, a unit level, or a per-award amount.

#### Scenario: The amount is recorded as untrusted and unawarded

- **WHEN** a placed row's recorded experience is inspected
- **THEN** it is reported as content, no experience is awarded or computed from it, and the recorded contract names the client argument as the only source of the amount

#### Scenario: The absence of a reader is the recorded reason

- **WHEN** the recorded contracts are inspected
- **THEN** they state that the field is written only by the branch that takes a client amount and is read by no legacy branch, and that this — not the corpus — is why no award is reproduced

#### Scenario: No schedule, threshold, or unit level is introduced

- **WHEN** this capability's delivered surface and documentation are inspected
- **THEN** no experience schedule, threshold, unit level, or per-award amount exists, and no committed field is adopted as one

### Requirement: The committed per-unit experience field is refused as a derivation

The capability SHALL record that the committed item definitions carry an experience field on
every unit and that it is **not** an award source, because no legacy branch reads it and three
independent measurements contradict it: one definition carries many different accumulated values
within a single save, the accumulated totals are not integral multiples of the committed value,
and no accumulated total equals the owning save's stored player experience. Any sibling field
that could express a level, threshold, or award SHALL be recorded with its zero-consumer status,
and the fact that **no committed per-unit level schedule exists anywhere in the content package**
SHALL be recorded. A committed field with no consumer SHALL be recorded and never invented into
a rule.

#### Scenario: The committed field is reported as content only

- **WHEN** a unit definition's committed experience value is inspected
- **THEN** it may be reported as content, and no award, duration, or accumulator is derived from it

#### Scenario: The refuting measurements are recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state the definition-level value spread, the non-integral ratio to the committed value, and the zero overlap with stored player experience, and name the zero-consumer status

#### Scenario: The absence of a per-unit level schedule is recorded

- **WHEN** every level-shaped key in the content package is enumerated
- **THEN** the capability records that all of them are player-level, price-tier, or magic-gate keyed, and that no per-unit level schedule exists

### Requirement: The legacy branch's accepted and refused inputs are committed as a fixture

The capability SHALL commit a re-runnable executed-legacy fixture for the branch, captured by
executing the legacy server against a disposable corpus seeded from a committed village save, so
that **no player state is fabricated**. The fixture SHALL record, per transaction, the request,
the HTTP status, the response body, the before and after save states, the changed-leaf-path set,
and the stored resources before and after; and its manifest SHALL record the seed's digest, the
containment digest, the exit code, and the established-versus-derived split. The fixture SHALL
establish, and be replayable for, each of: the increment arm adding to an existing value, the
assign arm creating the key when absent, a missing row leaving the save unchanged while still
answering success, the absence of any floor on a negative amount, the absence of any bound, a
non-integer amount being persisted, the branch accepting a row of either committed type, and
the third argument leaving the post-state unchanged.

#### Scenario: The fixture is captured from an authentic committed save

- **WHEN** the capture runs
- **THEN** the disposable corpus is seeded from a committed village save whose identity comes from the document itself, every recorded before-state is a committed byte sequence, and the fixture is re-runnable to identical result

#### Scenario: The accepted and refused shapes are recorded

- **WHEN** the fixture manifest is read
- **THEN** each of the increment arm, the assign arm, the missing-row case, the unbounded and unfloored cases, the persisted non-integer, the type-agnostic row, and the ignored third argument is present with its measured outcome

#### Scenario: Only one leaf moves on a neutral request

- **WHEN** a transaction is executed with a neutral resource vector
- **THEN** exactly the addressed row's experience leaf changes, every other placed row, the storage, the private state, the player information, and every stored resource are byte-identical, and the recorded leaf path is asserted rather than described

#### Scenario: The failing type cases are recorded as failures

- **WHEN** a non-numeric amount is sent against a row that already carries the field
- **THEN** the legacy server fails with a server error and the save is unchanged, and the fixture records that outcome rather than normalising it

### Requirement: The asymmetry between the two arms is recorded, not reproduced

The capability SHALL record that the two arms of the write differ in type behaviour: the assign
arm persists whatever it is given, while the increment arm raises on a non-numeric amount. It
SHALL record the consequence — that the legacy server can be made to write a **non-numeric** value
into a committed save, after which every later increment against that row fails — and SHALL state
that this is a durability defect in the legacy server rather than a capability to reproduce. The
delivered projection SHALL therefore report the recorded value's **kind** as well as its value,
so a poisoned bag is distinguishable from an integer one instead of being read as a number.

#### Scenario: The recorded value's kind is reported

- **WHEN** a placed row's recorded experience is projected
- **THEN** the projection reports the value verbatim together with a classification of what it is, and an absent key is reported as absent rather than as a value

#### Scenario: A non-numeric recorded value is not silently coerced

- **WHEN** a recorded experience value is not an integer
- **THEN** the projection reports it as recorded and identifies its kind, and no numeric interpretation, conversion, or comparison is applied to it

#### Scenario: The defect is recorded, not reproduced

- **WHEN** this capability's documentation is read
- **THEN** it states the arm asymmetry and its save-poisoning consequence as a recorded legacy defect, and no delivered code path writes, coerces, or repairs the field

### Requirement: The third argument is recorded as display-only and safely ignorable

The capability SHALL record that the branch's optional third argument is read into a local, used
only inside a printed message, and written nowhere, and SHALL establish ignorability **by
measurement rather than by argument**: the two-argument and three-argument forms are recorded as
producing identical post-states and identical changed-leaf sets, while their printed output
differs. A delivered consumer of this contract SHALL accept and ignore such a client-supplied
value rather than refuse it, because refusing would reject a request the legacy server accepts
whose stored effect is nil. The value SHALL never be stored, never surfaced as a level the row
reached, and never used to derive a threshold.

#### Scenario: Ignorability is proven by the recorded post-states

- **WHEN** the two-argument and three-argument forms are compared in the fixture
- **THEN** their recorded post-states and changed-leaf sets are identical, while their printed output differs

#### Scenario: The value is accepted and ignored, not refused

- **WHEN** a consumer of this contract is given the optional third argument
- **THEN** the request is neither rejected nor altered by it, and no level, threshold, or stored field derives from it

#### Scenario: The falsy distinction is recorded

- **WHEN** the recorded contracts are inspected
- **THEN** they state that the legacy branch tests the argument's truthiness, so a zero or absent value takes a different printed line than any other value, and that an ignoring consumer is unaffected either way

### Requirement: Evidence, provenance, and claim limits

The change SHALL commit a deterministic `unit-experience-report-v1` report, written by the
suite itself from its live measurements so its tables cannot drift from the code they document,
recording the committed-evidence census, the accepted and refused input table, the changed-leaf
proof, the display-only comparison, the projection contract, and the established-versus-derived
split, byte-identical across reruns. The report SHALL distinguish what is **established** — the
field's two writes and zero readers, the unvalidated client amount, the executed input shapes,
and the corpus-wide census — from what is **derived-provisional**, which is the choice of
disposable seed save and the recommendation shape. The non-claims SHALL state: no Flash, Ruffle,
ActionScript, or browser executed; **no experience is awarded and no award is derivable**; **no
endpoint, route, or client intent is added**; **no unit level, threshold, or schedule exists or
is introduced**; the corpus's absence of the field remains **true of that corpus** and is a
**fact about the corpus, not evidence about the repository**; the committed per-unit experience
field is **not** adopted as an award; the third argument is display-only; **no level reward is
paid or invented**; parity covers the recorded transactions against **one** progressed village
save and **no** fresh-player corpus transaction; and **no windowed capture and no pixel-parity
oracle** is claimed, because nothing is rendered.

#### Scenario: Commit the deterministic report

- **WHEN** the evidence step runs
- **THEN** the report is committed under `apps/client-godot/evidence/unit-experience/` carrying every required field, the provenance split, and every required non-claim

#### Scenario: Deterministic report rerun

- **WHEN** the report step is rerun against the same inputs
- **THEN** it reproduces its committed bytes exactly

#### Scenario: The corpus figure stays labelled as a corpus fact

- **WHEN** the report's census is read
- **THEN** it states the fresh corpus's absence of the field **and** the repository-wide census over all committed save documents, and labels the corpus figure as a fact about that corpus rather than evidence that an award exists

#### Scenario: No award, endpoint, or schedule is claimed

- **WHEN** this capability's documentation and evidence are read
- **THEN** they state that no experience is awarded, no compatibility surface is added, and no unit level, threshold, or schedule exists or is introduced

### Requirement: The corrected reason replaces the corpus reason wherever it was recorded

Every delivered location that states the branch is out of scope **because the corpus cannot
exercise it** SHALL be corrected to state the real reason — that no trusted award exists because
the only writer takes a client-supplied amount — while retaining the corpus figure **labelled as
a corpus fact**. This includes client-facing note strings, code documentation, application
prose, and the two progression capabilities whose requirements carried the stale reason. A
correction SHALL NOT remove or weaken any refusal, and SHALL NOT alter any assertion value,
threshold, or intent: where a hermetic assertion is true but its **message** reads more broadly
than the assertion's scope, only the message wording is corrected.

#### Scenario: The reason is corrected everywhere it was recorded

- **WHEN** the delivered client, its tests, and its documentation are searched for the corpus-cannot-exercise reason
- **THEN** no location states it as the reason, and each states the untrusted-amount reason with the corpus figure retained as a labelled corpus fact

#### Scenario: A composite note has both halves checked

- **WHEN** a delivered note string carries an out-of-scope statement for more than one topic
- **THEN** each half states the reason that applies to it, so a corrected half never leaves a stale one beside it

#### Scenario: No refusal is weakened by the correction

- **WHEN** the corrected locations are compared with their previous text
- **THEN** every refusal, non-claim, and prohibition is still present, and the only textual changes are the reason and the added census

#### Scenario: Assertion scope is corrected, not assertion behaviour

- **WHEN** a hermetic assertion is true of its own scope but its message reads more broadly
- **THEN** only the message is reworded to name its scope, and the assertion's expected value is unchanged
