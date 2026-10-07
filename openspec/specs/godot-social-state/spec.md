# godot-social-state Specification

## Purpose
Project the social state a committed save actually carries, and record the
measured absence that is the finding: 12 of 19 social state fields have zero
occurrences of any kind across all eleven legacy modules, and all 41 committed
social content entries have zero consumers.

This capability is deliberately named for **state** rather than for a feature.
It asserts nothing about whether visits, scores, or social rewards exist.
Zero-consumer is a statement about the **preserved
server** and says nothing about the Flash client, which may have held social
features entirely client-side.

**Corrected premise, recorded rather than edited away.** This Purpose once read,
as the reason the name `godot-friends` was withheld, "a capability named
`godot-friends` would claim exactly what this one measures to be absent." That
premise has since been **measured false**: a real server-side roster surface
exists at `player_info.neighbors` and is delivered by `godot-friends`. What the
measurement disproved is the roster's **absence**, not the absence of a social
*relationship* — so the name is still withheld for the narrower reason, and the
narrower reason is the one that now stands.

## Requirements

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

### Requirement: The nineteen measured social fields are delivered with their recorded storage location
The projection SHALL cover exactly the nineteen fields measured by the committed
investigation, each reported with the document or map it is stored in, and SHALL
NOT add a field that the investigation did not measure. Of those nineteen,
**seventeen** are social state; the remaining two — `timeStampEndPremium` and
`crossPromotionsFinished` — SHALL be reported as **foreign** to this capability and
named as owned by `godot-darts`, because the first records a paid purchase with a
server-derived value rather than a social fact, and the second records a
cross-promotion flag. The projection SHALL NOT present either as social state, and
SHALL NOT describe the field set as nineteen social fields.

#### Scenario: Review field coverage
- **WHEN** the projection is compared with the investigation's measured field list
- **THEN** all nineteen measured fields are present with their recorded storage location
- **AND** no unmeasured field is present

#### Scenario: Review the two foreign fields
- **WHEN** a maintainer reviews the field set
- **THEN** `timeStampEndPremium` and `crossPromotionsFinished` are reported as owned by another capability rather than as social state
- **AND** the delivered field set is described as seventeen social fields plus two foreign ones
- **AND** the named owning capability is verified to exist, so the hand-off is not an orphan

### Requirement: The zero-consumer census is re-derived on every run and never merely asserted
The suite SHALL re-derive, on every run, which social fields have zero occurrences of
any kind across the declared legacy module list, and SHALL require the recomputed set
to equal the pinned expectation in both directions. The census SHALL count
whole-identifier tokens and quoted subscripts as two separate forms and sum them, so a
field reached through a string literal is not scored as absent. A legacy edit that adds
or removes an occurrence SHALL fail the suite rather than silently contradicting the
delivered claim.

#### Scenario: Review the census provenance
- **WHEN** a maintainer asks how the twelve-field zero-consumer group was established
- **THEN** the suite reports that it recomputes the group from the legacy sources on every run
- **AND** it compares that recomputation against the pinned expectation in both directions

### Requirement: `questsRank` is reported as read-and-written and is not folded into the zero-consumer group
`questsRank` SHALL be reported as having one reader and one writer, both
`admin_set_quest_rank`, which assigns the key and deletes it when the assignment
is refused, and SHALL NOT be counted among the fields with zero occurrences of
any kind, notwithstanding that its name resembles the zero group.

#### Scenario: Review the one read-and-written field
- **WHEN** the census is recomputed
- **THEN** `questsRank` is excluded from the zero-occurrence group
- **AND** both its reader and its writer are reported

#### Scenario: Review how a writer through an aliased local was found
- **WHEN** a maintainer asks why the recorded count fell from thirteen to twelve
- **THEN** the census is recorded as counting identifier tokens and quoted subscripts as two separate forms
- **AND** the change is recorded as a lexer correction rather than a reclassification

### Requirement: Uniform emptiness is reported as one recorded value and its document count, and no populated example is synthesized
For each of the twelve write-less fields, the projection SHALL report the single value
the corpus records and the number of documents recording it, and SHALL NOT invent a
non-empty value, infer population from absence, or treat an empty container as
evidence that no relationship exists.

#### Scenario: Review a uniformly empty field
- **WHEN** a maintainer reviews `neighborAssists`
- **THEN** the projection reports the recorded value and the document count
- **AND** it does not report that the player has no assists, because that is a reading of an empty container

### Requirement: An absent field is reported as absent and is never coerced to its committed uniform value
A social field missing from a document SHALL be reported as absent, and SHALL NOT be
defaulted to that field's recorded uniform value. An absent key means a document
shape this capability has not observed, and coercing it would conceal exactly that.

#### Scenario: Review a document missing a social field
- **WHEN** a document omits a social key the corpus otherwise carries
- **THEN** the projection reports the key as absent
- **AND** it does not substitute the recorded uniform value for it

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

### Requirement: No social reward, coin, worker cost, eligibility window, or assist task is derived or charged
The capability SHALL NOT decode a `neighbor_assists` reward, SHALL NOT charge a
`findable_items` coin value, SHALL NOT select a `social_items` worker or worker cost,
and SHALL NOT derive an assist task, eligibility window, or relationship rule from any
committed value.

#### Scenario: Review the committed social content
- **WHEN** a maintainer reviews the three social content tables
- **THEN** their rewards, coins, worker costs, and tasks are reported as committed content owned by `social-tables-normalization`
- **AND** no delivered rule is derived from any of them

### Requirement: The social content tables remain owned by `social-tables-normalization`
The capability SHALL NOT project the `neighbor_assists`, `findable_items`, or
`social_items` content rows, and the suite SHALL assert that the owning capability
exists and retains that ownership.

#### Scenario: Review the capability boundary
- **WHEN** a maintainer looks for the owner of the social content tables
- **THEN** this capability identifies `social-tables-normalization` as the owner
- **AND** the suite fails if that capability is absent

### Requirement: Absence is guarded structurally, and all three guards are proven by injection
The suite SHALL pin an inventory of social helpers that must not exist and SHALL match
it case-insensitively and by substring, so a suffixed or differently-cased helper
carrying a reserved name is still detected. It SHALL also assert the delivered module
performs no arithmetic on, and no ordering comparison between, committed social
values. Each guard SHALL be demonstrated to fail when a violation is injected and the
file is then restored byte-identically; a guard never shown failing is not a guard.

#### Scenario: Review the anti-invention guards
- **WHEN** a maintainer asks how the absence claim is protected
- **THEN** the suite names the pinned absent-helper inventory and the substring and case-insensitive matching
- **AND** injection of a reserved helper, including a suffixed one, fails the suite
- **AND** the restore returns the file to a byte-identical state and the suite to passing

#### Scenario: Review a derivation that borrows no reserved word
- **WHEN** a helper comparing two committed social values is injected under a name that borrows no reserved word
- **THEN** the arithmetic and ordering guards fail the suite, not only the name-based guards
- **AND** those guards are self-checked so their emptiness assertions cannot be satisfied vacuously

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

### Requirement: Visits and scores are reported as having no server-side surface
`world_id` and `worldChange` SHALL be reported as save keys that appear zero times in
the legacy source, and the capability SHALL record that no score-like arithmetic exists
in the command dispatcher. It SHALL NOT derive a world, visit, or leaderboard concept,
and SHALL NOT treat the locally-named unit-loss and auction-bet values as scores.

#### Scenario: Review visits and scores
- **WHEN** a maintainer reviews the visits and scores classification
- **THEN** the two world-related keys are reported as carried but never read
- **AND** the absence of score arithmetic is reported as measured
- **AND** the rejected unit-loss and auction-bet readings are named so they are not re-counted as scores