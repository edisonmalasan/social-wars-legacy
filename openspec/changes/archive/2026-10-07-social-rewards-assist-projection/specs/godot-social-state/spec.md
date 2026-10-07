# Spec Delta

## MODIFIED Requirements

### Requirement: The delivered surface is a typed read-only projection of persisted social state, and it implies no social feature

The capability SHALL project the social state a committed save carries, and SHALL
report it verbatim. It SHALL NOT imply that a **visits** or **scores** feature
exists, and it SHALL NOT itself deliver a **social reward**.

**This requirement is amended a second time, and the second amendment is measured
rather than assumed.** Its first amendment recorded an ownership hand-off after
the premise behind the name was measured false. That amendment left standing a
sentence reading *"It SHALL NOT imply that a **visits**, **scores**, or **social
rewards** feature exists."* That sentence is now **partly false**, and the change
is confined to the clause it falsifies:

- **What remains true and standing.** No committed social content entry has any
  legacy consumer. This capability's eighth requirement - that no
  `neighbor_assists` reward is decoded, no `findable_items` coin charged, no
  `social_items` worker or worker cost selected, and no assist task, eligibility
  window or relationship rule derived - is **unchanged and still measured true**.
- **What was false.** A social-assistance state machine exists: `attr["si"]` is
  *"Socially In Construction"* by the preserved source's own comment at
  `engine.py:19`, it is gated by the committed `properties.friend_assistable`
  flag, it is written by three functions in `engine.py`, and it is dispatched from
  **three** branches. It is persisted on **53 of 3,372** placed rows across the
  canonical 10-document corpus.
- **What it still is not.** The surface grants nothing, charges nothing, and its
  only appended value is the integer `0`, which `engine.py:142` names as
  *"buying instead of hiring friends"* - so it records a **paid substitute for a
  friend**, not a reward. The **friend arm has no writer anywhere**.

The hand-off therefore **extends to a third capability** rather than being
replaced:

- `godot-social-state` owns the persisted social **state fields** - the nineteen
  measured fields, their recorded storage document, their writers and readers, and
  the zero-consumer census re-derived per run.
- `godot-friends` owns the **roster projection** over loaded villages, which is a
  projection of *other players' saves*, not of this capability's measured state
  fields.
- **`godot-construction-assist`** owns the **`attr["si"]` assist lifecycle**: the
  typed projection, the three recorded dispatchers, the `0` sentinel and its
  quoted meaning, the absent friend arm, the corpus's three reconciliation gaps,
  and the two zero-consumer gift fields.
- **Zero measured state fields move.** `attr["si"]` is a **map-row attribute-bag
  key**, not a `privateState` field, and is **not** one of the nineteen. The
  roster's eighteen-key entry is likewise not one of the nineteen. This
  capability's field set is unchanged by the hand-off.
- The original reasoning **survives in amended form for a second time**: no
  capability names a delivered surface after a social *relationship* or a social
  *reward*, because neither exists in the preserved server. `godot-friends` refuses
  the relationship vocabulary, `godot-construction-assist` refuses the reward
  vocabulary, and this capability refuses both - the reservation was conditional
  on the roster's absence, which has been disproved, and on the reward's absence,
  which has **not**.

#### Scenario: Review the delivered scope
- **WHEN** a maintainer reviews the capability
- **THEN** the delivered surface is a projection of stored social state
- **AND** no requirement in this capability describes a visits or scores behaviour
- **AND** this capability delivers no social reward, while a separate capability delivers the assist lifecycle whose absence this clause previously overstated

#### Scenario: Review the hand-off
- **WHEN** a maintainer asks which capability owns the roster
- **THEN** the roster projection is owned by `godot-friends`
- **AND** which capability owns the assist lifecycle is owned by `godot-construction-assist`
- **AND** no measured social state field is owned by either
- **AND** the recorded reason the name was originally withheld is stated together with the measurement that falsified it

#### Scenario: The reward refusal survives, narrowed
- **WHEN** a maintainer asks whether this capability still refuses a social reward
- **THEN** it refuses decoding any committed reward value and charging any coin or worker cost
- **AND** the refusal no longer rests on the claim that no social-assistance surface exists, because one does

### Requirement: The one real social-state writer is recorded with its client-sent value and is not reproduced

`set_resource_allies` SHALL be reported as the only branch writing social state,
writing `resourceAlliesMarket` from a client-supplied argument, and as stamping the
addressed row's recorded instant.

**This requirement's record is amended to name an effect it omitted.**
`set_resource_allies` performs a **third** recorded effect: at `command.py:644` it
calls `engine.finish_si`, which deletes the row's `attr["si"]` key. The previous
text of this requirement listed two effects and the scenarios restated two, so a
reader consulting this capability alone would conclude the row instant was the
branch's only row-level effect. The `finish_si` call is now named here, and its
**mechanism** is owned by `godot-construction-assist` - the hand-off is that the
**effect** is recorded in this capability while the **lifecycle** is delivered
there, so the two cannot describe the same call differently.

The capability SHALL NOT deliver an endpoint that performs either write, and
SHALL NOT derive meaning from the recorded instant stamp, and SHALL NOT
re-deliver the `finish_si` call that belongs to the assist capability.

The premium-account branch SHALL NOT be reported as a client-sent social writer:
it is owned by `godot-darts`, and it writes its recorded instant **twice** in one
branch with a value derived server-side from the committed schedule, so this
capability's record of it SHALL carry neither a client-sent value nor a
single-write description.

#### Scenario: Review the recorded writer
- **WHEN** a maintainer reviews the only branch that writes social state
- **THEN** it is identified as writing the market resource from a client-supplied value
- **AND** the row instant stamp is reported with no semantics derived from it
- **AND** no delivered route performs either write

#### Scenario: Review the third effect the record omitted
- **WHEN** a maintainer reviews what the branch does to the addressed row
- **THEN** the `finish_si` call at `command.py:644` is named as a third recorded effect
- **AND** its mechanism is identified as owned by `godot-construction-assist` rather than re-delivered here

#### Scenario: Review the premium record's corrected description
- **WHEN** a maintainer reviews how the premium-account branch is recorded here
- **THEN** it is identified as owned by another capability rather than as a client-sent social writer
- **AND** this capability asserts neither that its value is client-sent nor that the branch performs a single write

### Requirement: The absence of an executed-legacy fixture is recorded as the deliverable, not left as a gap

The capability SHALL record that no executed-legacy fixture is delivered, and SHALL
NOT fabricate a precondition to obtain one.

**The recorded reason is corrected, because it was falsified on two counts.** The
previous text gave two causes - *"no social command exists"* and *"the corpus
contains no populated social field"* - and neither survives measurement:

- **Three social commands exist**: `buy_si_help` (`command.py:549`), `finish_si`
  (`:561`), and `set_resource_allies` (`:637`), which this capability already
  records. "No social command exists" was wrong and is not repaired by renaming;
  it was simply untrue.
- **The corpus does carry a populated social-adjacent field.** Across the
  canonical 10-document allow-list, **53** of **3,372** placed rows carry
  `attr["si"]`, **3** of them non-empty at `[0, 0]` and `[0, 0, 0]`. That is a map
  attribute-bag key rather than a `privateState` field, so the narrower original
  claim about *this capability's* nineteen fields survives and is restated
  explicitly: **no `privateState` social field is populated in any committed
  document**, which is what the reason actually needed.

The **cause** of this capability's fixture absence is therefore restated as a
**decision, not a limitation**: this capability delivers no route that performs the
recorded writes, so there is no delivered transaction for a fixture to exercise.
That is the same cause `godot-darts` recorded for shipping a state-mutating
endpoint with no live phase. The capability SHALL record that an
executed-legacy fixture **was reachable** for the assist surface - `buy_si_help`
creates the key when it is absent - and that it is owned by
`godot-construction-assist`'s scope decision rather than by any corpus limitation.

#### Scenario: Review fixture absence
- **WHEN** a maintainer asks why no executed-legacy fixture accompanies this capability
- **THEN** the recorded reason is that the capability delivers no transaction, so there is none to exercise
- **AND** the superseded reason is recorded as measured false, with both of its counts corrected
- **AND** no fixture is fabricated to fill the gap

#### Scenario: The narrower original claim survives
- **WHEN** a maintainer asks whether any committed document populates a social **state** field
- **THEN** the answer is that no `privateState` social field is populated in any committed document, stated independently of the assist key's corpus presence
