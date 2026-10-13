# Spec Delta

## Purpose

Extends the Server v1 authority boundary from two worked slices to three, by applying
it to the `buy_magic` / `use_magic` pair — the target selected by measurement in
`docs/legacy-m13-line3-candidates.md`, whose §7.3 records that **no** remaining
candidate is as strong as line 2's was.

This delta specifies the part of that surface where authority is a **refusal made
specifiable** rather than a value derived. Two facts, both measured, drive it:

- Across **twelve** executed-legacy magic transactions in `tests/fixtures/godot-damage/`,
  **no** stored resource slot moved, including the one stored resource whose name
  matches a committed price column. The preserved server charges nothing.
- The committed magic table carries **four** numeric columns and **none of them is
  named a price**, so there is no rule by which one of them becomes a debit. Charging
  any of them is refused, and the refusal is proven rather than asserted: every
  stored resource must be byte-identical across a successful operation, which is
  exactly what a charge of any size would break.

Three further rules follow from the preserved branches and are specified here as
refusals of recorded defects: the identity is bound to the committed id space, the
counter is bounded and never reduced, and the committed `level` column is not a gate.

Every derivation in this delta is **established** except the identity validation and
the three refusal codes, which are **derived** and are labelled as such by the
boundary's own evidence requirement.

## ADDED Requirements

### Requirement: The request carries intent only: an identity and an operation, and no count, delta, or resulting value

A Server v1 magic request SHALL carry a save identity, a magic identity, and an
operation, and SHALL NOT carry a count, a delta, a resulting counter value, a price, a
mana cost, an effect magnitude, or any resource delta. The operation SHALL be one of
exactly two values — `buy` and `use` — and any other value SHALL be refused.

No v1 request schema SHALL accept a count or a resulting value. A request carrying one
SHALL be refused as a structural input error, and SHALL NOT be clamped, coerced, or
partially honoured. This is stricter than the preserved server, which applies a
client-supplied eight-slot resource vector at dispatch before the first branch
condition is tested, so a legacy client could pair any debit with either operation.

#### Scenario: A request carries an identity and an operation only

- **WHEN** a player sends a magic intent
- **THEN** the request carries a save identity, a magic identity, and one of the two declared operations
- **AND** no count, delta, resulting value, price, or effect field is accepted

#### Scenario: A client-supplied count or resulting value is refused

- **WHEN** a magic request carries a count, a delta, a resulting counter value, or a resource delta
- **THEN** the server refuses it as a structural input error with a named code
- **AND** the ledger and every stored resource are byte-identical to before
- **AND** no partial amount is applied

#### Scenario: An operation outside the closed two-value set is refused

- **WHEN** a magic request names an operation other than the two declared ones
- **THEN** the server refuses it as a structural input error
- **AND** no ledger entry is created

### Requirement: A magic identity must name a committed magic row, and every other identity is refused

A Server v1 magic operation SHALL require an integer magic identity that names a
committed magic row, and SHALL refuse an identity that names none with a typed
refusal that reports the identity requested. The validated identity SHALL be the
committed row's own id, not its position in the committed list.

Validation SHALL NOT coerce a non-canonical identity form into the committed key. An
identity whose JSON type is not an integer — a float, a string, or a boolean — SHALL
be refused as a malformed request rather than resolved.

This is stricter than the preserved server, which performs no validation at all,
accepts an arbitrary identity, creates a ledger entry for it, and keys the ledger on
the identity's **string** form, so a numeric identity sent as a float produces a
**distinct** ledger key. Both differences SHALL be recorded as **divergences** and
SHALL NOT be reported as parity.

#### Scenario: A committed magic identity is accepted

- **WHEN** a player sends a magic intent naming an identity that a committed magic row carries
- **THEN** the operation proceeds against that identity
- **AND** the response reports the committed row it resolved to

#### Scenario: An identity outside the committed table is refused

- **WHEN** a player sends a magic intent naming an identity no committed magic row carries
- **THEN** the server refuses with a typed refusal naming the identity requested
- **AND** no ledger entry is created and no stored resource moves

#### Scenario: A non-canonical identity form is refused, not coerced

- **WHEN** a magic request names an identity whose JSON type is not an integer while it denotes a committed row
- **THEN** the server refuses it as a malformed request
- **AND** no ledger entry is created under either spelling of that identity
- **AND** the difference from the preserved server's distinct-key behaviour is recorded as a divergence

### Requirement: The counter transition is bounded, never reduces, and a counter already above the bound is refused

A Server v1 magic operation SHALL derive the addressed counter's new value from the
server's own recorded state and the bound recorded in the preserved source, SHALL NOT
let the counter grow beyond that bound, and SHALL NOT reduce a counter that already
exceeds it.

A recorded counter **already greater** than the bound SHALL be refused with its own
typed refusal, the recorded state SHALL be reported rather than rewritten, and no
stored resource SHALL move.

This is stricter than the preserved server on both arms. One preserved branch **adds**
a bounded amount and is therefore unbounded, so repeated use climbs past the bound
indefinitely; the other **assigns** a bounded value and can therefore **reduce** an
existing counter. The obvious formula `min(bound, before + 1)` applied to a recorded
counter above the bound returns the bound, which is precisely the counter-destroying
decrease this requirement exists to refuse. Both differences SHALL be recorded as
**divergences**, separately from each other and from the difference between this
service and the preserved server, and none SHALL be reported as parity.

#### Scenario: The counter rises to the bound and stops

- **WHEN** a magic operation is applied repeatedly to one identity
- **THEN** the counter rises to the recorded bound and stops there
- **AND** repeated application does not push it beyond the bound

#### Scenario: A counter above the bound is refused, not clamped and not left alone

- **WHEN** a magic operation is applied to an identity whose recorded counter is already greater than the recorded bound
- **THEN** the server refuses with a typed refusal naming the recorded value and the bound
- **AND** the recorded counter is reported unchanged rather than rewritten
- **AND** no stored resource moves

#### Scenario: The two preserved branch asymmetries are recorded as divergences

- **WHEN** the preserved server's two magic branches are compared with this service
- **THEN** the unbounded growth of one, the reduction of the other, and the difference between this service and the preserved server are each recorded separately
- **AND** none of the three is reported as matching parity

### Requirement: No price is charged, and the committed cost columns are reported verbatim and never read to compute a debit

A Server v1 magic operation SHALL charge **no** resource. The committed magic table's
recorded cost, level, and target fields SHALL be reported **verbatim** exactly as
normalized, and SHALL NOT be read to produce a debit, a charge, a shortfall, or any
other value. No code path SHALL derive an amount from any committed numeric magic
column.

Where a committed entry's description promises an effect whose magnitude is **not**
committed, the absence SHALL be named explicitly and no magnitude SHALL be synthesized.
At least one committed entry's description promises to increase attack and life while
committing **no** multiplier, no factor, and no amount; the absence SHALL be reported
and no delivered code SHALL produce one.

The absence of a charge is a **specified** property, not an omission. It rests on
measured evidence: across twelve executed-legacy magic transactions, **no** stored
resource slot moved, and the table names none of its four numeric columns as a price.
Charging any column is therefore refused for want of a rule, and the committed corpus
cannot afford any committed magic on any column, so a charge would leave the operation
with no exercisable success against the committed corpus at all.

#### Scenario: A magic operation charges nothing

- **WHEN** a magic operation succeeds
- **THEN** every stored resource is byte-identical to its value before the request
- **AND** the response carries the committed row's recorded fields verbatim with no value computed from them

#### Scenario: No delivered code derives an amount from a committed magic column

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper capable of computing a price, a charge, a mana cost, a shortfall, a multiplier, a factor, or an effect amount from committed magic content
- **AND** this absence is enforced by a guard that fails when such a helper is introduced

#### Scenario: An absent effect magnitude is named, not synthesized

- **WHEN** the committed entry whose description promises an attack and life increase is projected
- **THEN** the absence of any committed magnitude is reported
- **AND** no delivered code computes a multiplier, factor, or amount for it

### Requirement: The committed level column is reported and is not a gate

A Server v1 magic operation SHALL NOT compare the player's recorded level against a
committed magic level, and SHALL NOT refuse an operation on that basis. The committed
level SHALL be reported verbatim beside the player's recorded level, so a client can
see both and disagree with them.

The column is a requirement by name, but no established rule supports enforcing it:
no legacy branch compares a player's level against any committed level, the field
carrying the established spelling has zero occurrences across the preserved modules,
and **no** committed save document at the lowest recorded level reaches any committed
magic. A gate would therefore leave the operation unexercisable against the committed
corpus while adding a rule nothing observed.

Deferring the gate is a recorded authority gap and not a denial: it becomes enforceable
if evidence ever establishes the committed table as a purchase-price table rather than
a reference table.

#### Scenario: A low-level player may operate a magic the table lists at a higher level

- **WHEN** a player whose recorded level is below a committed magic's recorded level sends a magic intent
- **THEN** the operation is not refused on the basis of that level
- **AND** the response reports both the committed level and the player's recorded level

#### Scenario: No delivered code compares a player level against a committed magic level

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper comparing a player's recorded level against a committed magic level
- **AND** this absence is enforced by a guard that fails when such a helper is introduced

### Requirement: Both operations apply one bounded transition, and the alias is stated rather than hidden

The two declared operations SHALL apply the **same** derived transition, and the
service SHALL state that they do. The service SHALL report, beside the value it wrote,
whether the preserved branch would have written the same value for the same recorded
state, and SHALL NOT report the two as agreeing when they do not.

The preserved branches differ in exactly one token, and the difference is two recorded
defects — unbounded growth in one, counter-destroying reduction in the other. Removing
both defects leaves one operation. The surface keeps two names because the compatibility
route has two request shapes and a migrating client must be able to send what it sent;
the sameness is documented rather than papered over with an invented distinction.

Both preserved branches also **increase** the counter: the operation named `use` adds a
charge rather than spending one, and no preserved branch anywhere decrements. The
counter SHALL therefore never be decremented, and SHALL NOT be read to answer whether
the player owns a spell.

#### Scenario: Both operations produce the same derived transition

- **WHEN** the same recorded state is addressed by either declared operation
- **THEN** the derived counter value is identical
- **AND** the response states that the two operations are the same transition

#### Scenario: The derived value and the preserved branch's value are reported separately

- **WHEN** a magic operation succeeds
- **THEN** the response reports the derived value beside the value the unchanged preserved branch would have written for the same recorded state
- **AND** states plainly whether they agree
- **AND** a disagreement is recorded as a divergence rather than presented as parity

### Requirement: Every refusal resolves before any ledger write, so a refused request leaves the recorded document byte-identical

The service SHALL complete every validation — structural, content, identity, and
recorded state — **before** any ledger entry is created or modified, so that a refused
request provably leaves the whole stored document byte-identical, including the ledger
and every other key.

The preserved server's ordering cannot be reproduced because it performs no validation
at all; the ordering requirement therefore exists to make this service's refusals safe
rather than to match a recorded ordering.

The refusal vocabulary SHALL be a closed table shared by every route, and this
operation SHALL NOT name a refusal reason that is absent from it.

#### Scenario: A refused request leaves the document byte-identical

- **WHEN** a magic request is refused for any reason
- **THEN** the whole stored document is byte-identical to its state before the request, including the ledger and every other key
- **AND** every stored resource is byte-identical

#### Scenario: Validation ordering is asserted structurally

- **WHEN** the delivered implementation is inspected
- **THEN** every validation precedes the ledger write, and the delivered module's whole function inventory is pinned so a reordering fails the suite

### Requirement: The post-execution proof is two-part, and only its second half is evidential

Every action SHALL carry a two-part post-execution proof: the addressed counter equals
the value derived from the server's own recorded prior value and the recorded bound,
every unaddressed counter is byte-identical and keeps its recorded position, exactly
one stored leaf path changed, **and** every stored resource the server knows about is
byte-identical.

The second half SHALL compare the **complete** stored resource set the service
exposes, and SHALL NOT compare a subset.

The second half is the falsifiable half, and it is falsifiable because the charge is
refused: every alternative this design rejected — charging the committed gold, the
committed cash, or the committed mana column — moves exactly one of the stored
resources and therefore fails it, while twelve executed-legacy transactions measured
no stored resource moving at all. The first half is a specification check rather than
an evidence claim, because this service is the only implementation writing the save on
this path and it diverges from the preserved branch by design; it SHALL NOT be
presented as parity.

#### Scenario: A successful operation changes exactly one leaf and no resource

- **WHEN** a magic operation succeeds
- **THEN** exactly one stored leaf path changed and every other key is byte-identical
- **AND** every stored resource is byte-identical to its value before the request

#### Scenario: The proof would fail a charge

- **WHEN** the delivered post-execution proof is exercised
- **THEN** an implementation that debited any stored resource by any amount fails the resource half of the proof
- **AND** this is asserted by a test rather than by comment
