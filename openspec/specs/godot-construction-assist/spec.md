# godot-construction-assist Specification

## Purpose
Project the Socially-In-Construction assist state a placed row actually carries,
and record the measured finding that the surface is a **paid substitute for a
friend**: the list records who filled each assist slot, the only value any writer
ever appends is the integer `0`, and `engine.py:142` names that value verbatim as
*"0 is for buying instead of hiring friends"*. The **friend arm has no writer
anywhere**, which the committed corpus corroborates - 7 elements totalling exactly
one distinct value.

This capability is deliberately named for the **surface** rather than for the
deliver item it serves, because the surface is the inverse of that item's name.
The same recorded reason that withheld `godot-friends` applies here: naming a
capability after a delivered surface would claim what the measurement disproves.
What the measurement finds is that a `si` entry stands for a **paid** assist, and
never for a **reward** - the append branch makes no resource application and no
grant, and the delete branch removes one key and nothing else.

The token's expansion is **not inferred**. `engine.py:19` states it verbatim as
*"enable SI (Socially In Construction), because the game expects it"*, and the
trailing clause is reported rather than dropped: the author's own admission that
the game *expects* the field is the most informative sentence in the surface, and
it is the reason a client-display concession is not reported as gameplay.

Zero-consumer, no-writer, and grants-nothing are statements about the
**preserved server**. They say nothing about what the Flash client displayed,
which may have held a gifting interface entirely client-side.

## Requirements
### Requirement: The delivered surface is a typed read-only projection of the Socially-In-Construction assist state, and it implies no social reward

The capability SHALL deliver the `attr["si"]` assist state of a placed row as a
typed, **read-only** projection, and SHALL NOT imply that a social **reward**
exists, that a **friend** can be assisted, or that any assist has an observable
consequence. The token's expansion is **not inferred**: `engine.py:19` states it
verbatim as *"enable SI (Socially In Construction), because the game expects it"*,
and the trailing clause is reported as a recorded author admission that the
mechanism is a client-display concession rather than gameplay.

The capability's name is chosen over `godot-social-rewards` on the same recorded
reason that withheld `godot-friends`: naming a capability after a delivered
surface would claim what the measurement disproves. What the measurement finds is
a **paid substitute for a friend**, never a reward.

The projection SHALL report, per row, whether the attribute bag carries `si`, the
recorded **length** of its list, and each element's **recorded type and value
verbatim**. It SHALL derive **no** element from another, SHALL NOT decode a
non-`0` element, and SHALL NOT present the list as assistance in progress,
assistance received, or a progress ratio. A capability named
`godot-construction-assist` asserts nothing about what the Flash client displayed.

#### Scenario: Review the delivered scope
- **WHEN** a maintainer reviews the capability
- **THEN** the delivered surface is a projection of one recorded attribute-bag key
- **AND** no requirement in this capability describes a granted reward, a hired friend, or an assist that changes any balance

#### Scenario: Review the token's expansion
- **WHEN** a maintainer asks what `si` stands for
- **THEN** the expansion is quoted from the preserved source's own comment and is not reconstructed from the field's usage
- **AND** the "because the game expects it" clause is reported as recorded rather than dropped

### Requirement: A row's assist state fails closed, and the recorded slots travel untouched beside the refusal

The projection SHALL report an assist state as unresolvable — carrying the
recorded state intact and changing no value — when the row's attribute bag is
**absent**, is **not** an object, or carries `si` whose value is **not a list**.
It SHALL NOT coerce a non-list value into a list, SHALL NOT substitute an empty
list for a missing key, and SHALL NOT report a missing key as an empty list that
was resolved. **A missing key and an empty list are different recorded states**,
because the preserved server creates the key lazily and the two are produced by
different branches.

Each refusal SHALL carry a distinct code identifying which shape failed, and the
absence of each refusal SHALL be recorded: a value that is a list but whose
elements are of an unexpected type is **not** refused, because the element type
is reported verbatim and inventing a type rule would refuse recorded data.

#### Scenario: Refuse an unresolvable assist state
- **WHEN** a row's attribute bag is absent, is not an object, or carries `si` whose value is not a list
- **THEN** the assist state is reported unresolvable with its recorded state intact, and no list, length, or element is fabricated

#### Scenario: A missing key is not an empty list
- **WHEN** one row carries no `si` key and another carries `si` with an empty list
- **THEN** the two are reported as different recorded states rather than collapsed into one resolved-or-absent answer

#### Scenario: An unexpected element type is reported, not refused
- **WHEN** a recorded `si` list contains an element that is not an integer
- **THEN** the element's recorded type and value are reported verbatim and the state is not refused

### Requirement: The three recorded dispatchers and their effects are quoted from source, and none is reproduced

The capability SHALL record exactly **three** dispatcher branches that reach the
assist key, each with its source line and its effects quoted rather than
paraphrased:

- `buy_si_help` (`command.py:549`) - creates the key as `[0]` when absent and
  appends `0` when present;
- `finish_si` (`command.py:561`) - deletes the key when present;
- `set_resource_allies` (`command.py:637`) - **not named for the assist key** -
  calls `finish_si` at `:644` while also stamping the addressed row's instant at
  `:643` and writing a client-supplied market resource.

Every recorded effect SHALL carry `reproduced: false`, and the capability SHALL
NOT deliver a route that performs any of them. The capability SHALL record that
the delete path has **two** dispatchers rather than one, because a reader
consulting only the two assist-named branches would conclude the delete is
reachable only through `finish_si`.

The capability SHALL record that both dedicated branches require only that the
addressed map slot resolve to a row, and SHALL record the resulting absences: no
`friend_assistable` check, no type check, and no team check. **The absence of the
flag check SHALL NOT be reproduced as a client-side guard**, because doing so
would refuse a recorded corpus state - two committed rows carry the key without
the flag - and the divergence is recorded rather than closed.

The instant stamp performed by `set_resource_allies` SHALL be reported as owned
by `godot-social-state`, which already records that write, and this capability
SHALL NOT re-record it as its own or derive meaning from it.

#### Scenario: Review the dispatcher inventory
- **WHEN** a maintainer reviews which branches write or delete the assist key
- **THEN** three branches are named with their source lines
- **AND** the branch not named for the key is named, with its line
- **AND** the delete path's second dispatcher is named

#### Scenario: No recorded effect is reproduced
- **WHEN** a maintainer asks whether this capability can write the key
- **THEN** every recorded effect carries `reproduced: false` and no delivered route performs any of them

#### Scenario: The absent flag check is recorded, not enforced
- **WHEN** the capability reports the assist state's precondition
- **THEN** it records that only the addressed row must resolve, and that no flag, type, or team check exists
- **AND** the recorded corpus state of two flagged-less rows carrying the key is retained rather than refused away

### Requirement: The committed gate is referenced, not reimplemented, and the two owning capabilities are asserted to exist

The attribute bag's `si` key is **derived** at placement by
`godot-stored-item-placement`, whose committed `friend_assistable` reading this
capability **references**. This capability SHALL NOT reimplement that derivation,
SHALL NOT normalize, coerce, or re-derive the committed flag, and SHALL NOT read
the committed flag itself except to report the gate's recorded shape.

The ownership SHALL be **asserted rather than assumed** - the suite SHALL check
that the owning capability's spec exists and that the delivered derivation names
the same committed source field - so a rename on either side cannot orphan the
link or let the two capabilities describe the key's creation differently.

The gate's recorded measurements SHALL be reported: the committed flag is the
**string** `'1'` on **26 of 470** buildings and on **0 of 429** units. The
encoding SHALL be reported as recorded, because the normalized package stores
`properties` flags as strings and a consumer that compares the value against an
integer reads **every** carrier as false - a fault this project has recorded
before, in the `properties`-flag trap.

#### Scenario: Review the gate's provenance
- **WHEN** a maintainer asks where the `si` key comes from
- **THEN** the derivation is named as owned by `godot-stored-item-placement` and is referenced rather than reimplemented

#### Scenario: Review the flag's encoding
- **WHEN** a maintainer checks the committed `friend_assistable` value
- **THEN** it is reported as the string `'1'`, and a comparison against an integer is identified as a fault that would read every carrier as false

### Requirement: The only appended element is the integer 0, its meaning is quoted from a source comment, and the friend arm has no writer

The capability SHALL record that the **only** value any writer ever appends is the
integer `0`, and SHALL report that value's meaning as a **quoted source comment**
(`engine.py:142`, *"0 is for buying instead of hiring friends"*) rather than as an
inference from behaviour. The capability SHALL NOT decode the sentinel as a friend
identifier, a count, a price, a type tag, or a player id, and SHALL NOT invent a
non-`0` encoding.

The capability SHALL record, as a **measurement**, that the friend arm has **no
writer anywhere**: zero occurrences of a non-`0` write path across all eleven
legacy modules under six counting rules, corroborated by the committed corpus
holding **7** elements totalling **one** distinct element value, the integer `0`,
with no non-zero, float, string, `null`, or non-list value anywhere.

Because the list therefore records **who filled each assist slot** and the only
writer fills it with the **paid** arm, the capability SHALL record that the surface
is a record of a **paid substitute for a friend** - the inverse of the deliver
item's name - and SHALL NOT present the list as social assistance performed.

#### Scenario: Review the appended value
- **WHEN** a maintainer asks what the list's elements are
- **THEN** the only recorded element value is the integer `0`, and its meaning is quoted from the preserved source's own comment

#### Scenario: Review the absent friend arm
- **WHEN** a maintainer asks how a friend's participation is recorded
- **THEN** the answer is that no writer exists, with the zero-consumer measurement and the corpus corroboration both reported

#### Scenario: No element is decoded
- **WHEN** the capability reports a recorded `si` list
- **THEN** it reports elements verbatim and assigns no meaning to a non-`0` value

### Requirement: Three corpus facts are recorded as gaps, because `si` does not imply the flag in either direction

The capability SHALL record three measured facts about the committed corpus's
**canonical 10-document allow-list** and SHALL NOT reconcile them:

- **2 of 53** rows carrying `si` sit on items that do **not** carry
  `friend_assistable` (ids `61` and `75`), and both are non-empty at `[0, 0]`,
  with a `content_version` matching a genuine carrier's - so the flag was not
  added later;
- **2** flagged ids are placed with **no** `si` row (id `4`, one row; id `12`,
  three rows);
- **8 of 26** flagged ids are never placed in the corpus.

**Correction, recorded here rather than tidied away.** The superseded text of that
bullet continued *"and those are the corpus's **only** non-empty lists, at
`[0, 0]` each"*. That clause is **false**, and it was measured false rather than
asserted: the corpus holds **3** non-empty `si` lists totalling **7** elements,
not 2 totalling 4. The third is the **gated** item `9` at `[0, 0, 0]` - three
appends rather than two. The clause was wrong in the direction that mattered,
because it hid the one non-empty list sitting on a **flagged** id and so made the
corpus look uniformly unflagged-when-populated. The sibling requirement for
`godot-social-state` in **this same change** already carried the correct count
(*"3 of them non-empty at `[0, 0]` and `[0, 0, 0]`"*), so two specs of one change
disagreed and the corpus settled it.

The **conclusion is unchanged** - `si` presence still does not reliably indicate
the flag, because direction one is a fact about **two** rows and does not become
weaker by a third non-empty list existing elsewhere. What changes is that the
gated `[0, 0, 0]` is **not** covered by the first candidate explanation below,
which is stated in terms of two appends. The delivered suite now **asserts** the
count, so the clause cannot be reintroduced.

Candidate explanations - `buy_si_help`'s absent flag check producing exactly
`[0, 0]` after two appends, and `map_add_item_from_item` bypassing the gate
entirely - SHALL be recorded as **candidates, not measurements**, because nothing
in the preserved source performs either. The first candidate covers the two
ungated rows only: the gated item `9`'s `[0, 0, 0]` is three appends and is
therefore **outside** the shape that candidate describes, which is a reason the
candidate stays a candidate rather than an explanation.

The narrow claim SHALL be the one that holds: **`si` presence does not reliably
indicate `friend_assistable`**, and the corpus proves it in both directions. The
capability SHALL NOT assert a direction of implication in either form, and SHALL
NOT treat the presence of the key as evidence of assistability.

The corpus measurement SHALL be re-derived per run against the canonical
allow-list rather than pinned, and the allow-list SHALL be an explicit list, so a
naive walk cannot sweep fixture step documents or build caches into the count.

#### Scenario: Review the reconciliation
- **WHEN** a maintainer asks whether carrying `si` means a building is friend-assistable
- **THEN** the answer is that it does not, with both directions measured
- **AND** the two unflagged carriers and the two flagged-without-`si` ids are named

#### Scenario: Candidate explanations are labelled
- **WHEN** a maintainer reads the recorded anomalies
- **THEN** each candidate explanation is labelled a candidate rather than a measurement

### Requirement: No reward is granted, no resource is charged, and no committed reward table is decoded

The capability SHALL record that the assist surface grants **nothing** and charges
**nothing**: the append branch makes no resource application and no storage or
unit grant, and the delete branch removes one key and nothing else. It SHALL NOT
implement a charge, a credit, a refund, or a currency conversion.

The three committed social tables SHALL remain owned by
`social-tables-normalization`, and this capability SHALL NOT project their content
rows, SHALL NOT decode a `neighbor_assists` reward, SHALL NOT charge a
`findable_items` coin value, and SHALL NOT select a `social_items` worker or
worker cost. The ownership SHALL be asserted rather than assumed so a rename
cannot orphan it.

The uniformity of the committed reward schedule SHALL be reported as a **census,
not a projection**: `neighbor_assists.reward` is one distinct reward object
across all five entries and `findable_items.coins` is one distinct value across
all ten, so even a reader would have exactly one number to give. That census is
reported because it is the *reason* nothing here decodes a reward - a schedule
carrying a single value cannot distinguish a rule from a constant - and it states
no entry, no id, and no display string.

The `social_items` **internal** structure SHALL NOT be reported by this
capability. A measurement taken while writing this change found the 26 rows'
`legacy_id` values to be 13 low ids and 13 high ids differing by a fixed `+3000`,
i.e. **13 items each listed twice**, with `worker_cost` identical across the two
blocks. **That finding is deliberately not delivered here.** The owning capability
counts one definition per **stored entry**, and all 26 ids are **distinct**, so
its coverage, id-preservation, and id-uniqueness requirements are literally true
as written and no amendment is warranted. Reporting the recurrence would assert a
grouping the owning capability does not make, from inside a capability that is
forbidden to project those rows; and no legacy branch reads the table, so there is
no consumer whose two-block handling could be observed even if it did. The
measurement is recorded in `docs/legacy-m11-social-rewards.md` and travels to the
owning capability only if that capability ever needs it.

#### Scenario: Review the no-reward claim
- **WHEN** a maintainer asks what a successful assist gives the player
- **THEN** the answer is that it grants nothing and charges nothing, with the two recorded branches as the evidence

#### Scenario: The content tables stay owned elsewhere
- **WHEN** a maintainer asks which capability owns the three social tables
- **THEN** `social-tables-normalization` is named and asserted to exist
- **AND** no reward, coin, or worker cost is decoded here

#### Scenario: The duplicated schedule is reported, not interpreted
- **WHEN** a maintainer reviews the social-item schedule through this capability
- **THEN** the uniformity census covering the assist reward and findable coin values is reported as a census
- **AND** the social-item table's internal structure is left to `social-tables-normalization`, whose stored-entry coverage this capability does not restate or correct

### Requirement: Two further committed gift fields have zero legacy consumers, and no ordinal position is claimed for either

The capability SHALL record that `giftable` and `gift_level` each have **zero**
legacy consumers, measured as zero under all six counting rules across all eleven
legacy modules, and SHALL report each field's committed presence and
distribution: both are `int` on all **470** buildings, all **429** units and the
**1** special; `giftable` is `1` on **20** buildings and **10** units; and
`gift_level` spans `0..10` over buildings and `0..40` over units, so it is not a
constant.

The capability SHALL claim **no ordinal position** for either field. Earlier lines
in this project named successive zero-consumer discoveries "the sixth", "the
seventh", "the ninth" and "the tenth", but each count was taken over a **different
scope** and no single reconciled census of zero-consumer committed fields exists
in this repository. Assigning a number here would repeat the defect the
`godot-unit-behaviors` line was corrected for. What is claimed is the measured
fact, and the overlap with the other recorded instances is listed so a later line
does not double-count.

`godot-unit-behaviors` already records a units-only census row for `gift_level`,
and this capability SHALL **complete** that census rather than replace it: the
buildings-side measurement is added, and `giftable` - which is in **no** census in
this repository - becomes a recorded row instead of a gap. The completion SHALL
be asserted so the two capabilities cannot each claim to own the field.

The capability SHALL NOT derive a gifting threshold, comparison, rule, or
interface from either field, and SHALL record that no branch among the 63 is named
for a gift - so the existing `godot-social-state` guard reason *"no gift command
exists"* **remains true** while being incomplete, because the fields exist and are
read by nothing.

#### Scenario: Review the gift fields
- **WHEN** a maintainer reviews the two zero-consumer gift fields
- **THEN** both are reported as committed `int` fields with their distributions and their zero-consumer measurement
- **AND** neither is assigned an ordinal position among zero-consumer fields

#### Scenario: The census is completed, not duplicated
- **WHEN** a maintainer asks which capability records the `gift_level` census row
- **THEN** `godot-unit-behaviors` is named as the census owner and asserted to exist, with this capability adding the buildings-side measurement and the `giftable` row

#### Scenario: No gifting rule is derived
- **WHEN** a maintainer asks what `gift_level` controls
- **THEN** the answer is that no reader exists and no rule is derivable, and the "no gift command exists" finding is reported as still true and now incomplete

### Requirement: Every refusal is enforced by a guard proven by injection against a byte-identical copy

The capability's absences SHALL be enforced by **guards that fail when the
forbidden capability is introduced**, because a prose refusal cannot fail. Each
guard SHALL be proven by an **injection** against a **byte-identical copy** of the
delivered module, with the restored file's digest recorded in the evidence report
so the claim is checkable rather than remembered. A guard never shown failing is
not a guard.

The guard set SHALL include a **whole-function inventory pin** - the real gate -
and a **reserved-name** match applied **case-insensitively and by substring**, so
a suffixed or differently-cased helper wearing a reserved name is still caught. The
reserved-name guard SHALL be shown to be **necessary rather than redundant** by at
least one injection that borrows no reserved word, and the inventory pin SHALL be
compared as a sorted unique set with the declaration count pinned separately, so a
helper declared twice cannot make a positional comparison fail against the
delivered module itself.

No delivered code identifier SHALL be named after a refused behaviour, and the
suite SHALL assert that absence of the identifier so the naming cannot creep in
beside the behaviour.

#### Scenario: Guard the refusals
- **WHEN** a forbidden helper is introduced into the delivered module
- **THEN** the suite fails, and the injected file is then restored byte-identically with its digest recorded

#### Scenario: The reserved-name guard earns its place
- **WHEN** a suffixed or differently-cased helper wearing a reserved name is injected
- **THEN** the suite fails on the substring match, not only on the exact name

#### Scenario: No delivered identifier is named after a refusal
- **WHEN** a maintainer reviews the delivered module's identifiers
- **THEN** none is named after a refused assist, reward, friend, or gifting behaviour
