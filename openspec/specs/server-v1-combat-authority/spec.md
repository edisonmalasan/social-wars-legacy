# Spec Delta

## Purpose

Extends the Server v1 authority boundary from three worked slices to four, by applying
it to `end_attack` — the target selected by measurement in
`docs/legacy-m13-line4-candidates.md`, whose §4 records the finding that decides this
delta's whole shape: **0 of the 29** branches still in the M13 pool have a committed
value that names their outcome, and every content-anchored M13 line is already
delivered.

This delta specifies the part of that surface where authority is a **refusal made
specifiable** and where the refusal is total. Three facts, each measured, drive it:

- The branch's entire stored effect is **one call**, and both the item id and **the
  number of rows destroyed** arrive from the client. The count is
  `max(0, unit[2] - unit[3])` — a subtraction of two client numbers the preserved
  source labels only `A` and `B` in its own comment.
- **No committed value names that outcome.** Across the nine other committed combat
  fields, every occurrence count is `0` under six counting rules over the preserved
  modules; the one field that appears at all, `attack`, has a **whole-word** count of
  `0` and all twelve of its whole-file occurrences sit inside longer identifiers.
- `map_lose_item` pushes every destroyed row onto `privateState["deadHeroes"]`, so a
  single client request writes **two** pieces of authoritative state — a placed row and
  a ledger count.

So this line **derives nothing at all**, which is stated here rather than discovered by
the reader. It closes the client's ability to name a destruction, it resolves and
**reports** the two committed gates the preserved server would have applied without
acting on either, and it proves the refusal with the strongest instrument in this
project: **the entire persisted document, including the dead-hero ledger, is
byte-identical after a successful request.**

Every derivation in this delta is **established** except the route shape, the identity
validation, the gate reporting posture, and the refusal code, which are **derived** and
are labelled as such by the boundary's own evidence requirement.

## Requirements

### Requirement: The request carries a combat identity and no destruction, casualty, damage, or resource figure

A Server v1 combat request SHALL carry a save identity and a combat identity — a
committed unit identity — and SHALL NOT carry a destruction count, a casualty figure, a
lost-unit list, a damage amount, an honour value, a resource payout, or any resource
delta. There SHALL be exactly one action on the route; no operation or action field
SHALL be accepted, and any other field SHALL be refused as an unknown request field.

No v1 combat request schema SHALL accept a destruction, casualty, damage, or resource
figure. A request carrying one SHALL be refused as a structural input error, and SHALL
NOT be clamped, coerced, or partially honoured. This is stricter than the preserved
server, whose `end_attack` reads an entire JSON blob from `args[0]` and computes
`max(0, unit[2] - unit[3])` on two client numbers — the only quantity the branch
derives — before writing.

#### Scenario: A combat intent carries an identity only

- **WHEN** a player sends a combat intent
- **THEN** the request carries a save identity and a committed combat identity and nothing else
- **AND** no destruction, casualty, damage, honour, payout, or resource field is accepted

#### Scenario: A client-supplied destruction or casualty figure is refused

- **WHEN** a combat request carries a destruction count, a casualty list, a damage amount, or a lost-unit figure
- **THEN** the server refuses it as a structural input error with a named code
- **AND** the whole stored document and every stored resource are byte-identical to before

#### Scenario: A client-supplied resource delta is refused

- **WHEN** a combat request additionally carries a resource delta
- **THEN** the server refuses it as a structural input error and applies no partial amount

### Requirement: A combat identity must name a committed unit row, and every other identity is refused

A Server v1 combat operation SHALL require an integer combat identity that names a
committed **unit** row, and SHALL refuse an identity that names none with a typed
refusal that reports the identity requested. The validated identity SHALL be the
committed row's own committed `legacy_id`, not its position in the committed list.

Validation SHALL NOT coerce a non-canonical identity form into the committed key. An
identity whose JSON type is not an integer — a float, a string, or a boolean — SHALL be
refused as a malformed request rather than resolved. Zero and every negative identity
resolve to no committed unit row and are refused by the same out-of-table refusal, and
that is asserted rather than left to a separate non-negative rule.

This is stricter than the preserved server, which performs no validation at all, keys
the dead-hero ledger on the identity's **string** form, and would create a ledger entry
for any value. The difference SHALL be recorded as a **divergence** and SHALL NOT be
reported as parity.

#### Scenario: A committed unit identity is accepted

- **WHEN** a player sends a combat intent naming an identity that a committed unit row carries
- **THEN** the operation proceeds against that identity
- **AND** the response reports the committed row it resolved to

#### Scenario: An identity outside the committed unit table is refused

- **WHEN** a player sends a combat intent naming an identity no committed unit row carries
- **THEN** the server refuses with a typed refusal naming the identity requested
- **AND** no ledger entry is created and no stored resource moves

#### Scenario: A non-canonical identity form is refused, not coerced

- **WHEN** a combat request names an identity whose JSON type is not an integer while it denotes a committed row
- **THEN** the server refuses it as a malformed request
- **AND** no ledger entry is created under either spelling of that identity

### Requirement: No destruction is performed and no destruction count is derived; the client-dictated count is reported and refused

A Server v1 combat operation SHALL destroy **no** placed row and SHALL NOT increment,
create, or decrement the dead-hero ledger. It SHALL NOT derive a destruction count, a
casualty count, a damage amount, or any resource payout from committed content or from
the request. A request that attempts to name a destruction SHALL be refused with its own
typed refusal code.

Where the request or the preserved branch carries a client-dictated destruction figure,
the response SHALL **report** that figure together with the named code that refused it,
so a client can see what it sent and why it was not applied. No delivered code SHALL
compute a destruction, damage, casualty, honour, or payout quantity from any committed
column or any request field.

The absence of a derivation is a **specified** property, not an omission. It rests on
measured evidence: the preserved branch's only quantity is a subtraction of two client
numbers labelled only `A` and `B`, and the committed content carries no value that
names this branch's outcome. This is stricter than the preserved server and than the
Compatibility API's own `resolve` action, both of which destroy a row; that difference
SHALL be recorded as a **divergence**, never as parity.

#### Scenario: A combat operation destroys nothing

- **WHEN** a combat operation succeeds
- **THEN** no placed row is removed and the dead-hero ledger is byte-identical to its value before the request
- **AND** every stored resource is byte-identical

#### Scenario: The client-dictated destruction is reported and refused

- **WHEN** a combat request carries a destruction, casualty, or damage figure
- **THEN** the server refuses it with the destruction refusal code
- **AND** the response reports the figure that was refused
- **AND** the whole stored document is byte-identical

#### Scenario: No delivered code derives a destruction or damage quantity

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper capable of computing a destruction, damage, casualty, honour, or payout quantity from committed content or a request field
- **AND** the combat domain module contains no arithmetic operator at all
- **AND** these absences are enforced by guards that fail when such a helper is introduced

### Requirement: The two committed ledger gates are resolved and reported verbatim, and neither is acted on

A Server v1 combat operation SHALL resolve, from committed content and from recorded
state, the two conditions under which the preserved server credits a destroyed row to
the dead-hero ledger: that the row's recorded player team is the player's own team, and
that the committed unit row carries a `resurrectable` flag greater than zero. It SHALL
**report** both verbatim and SHALL NOT enforce either as a precondition, SHALL NOT
refuse an operation on the basis of either gate, and SHALL NOT write the ledger.

A committed `resurrectable` value that is **absent** SHALL be reported as **absent**,
never as zero, matching the preserved helper's refusal on an absent flag. A row that is
not present on the recorded map SHALL be reported as **absent**, with no team value,
rather than refused. The asymmetry between the preserved helpers — that one accepts any
truthy team while the other requires the player's own team exactly — SHALL be reported
in the response rather than reconciled.

The committed unit row and the recorded team are read through the existing content
registry and repository seams; no committed value SHALL be transcribed into code.

#### Scenario: The committed resurrectable gate is reported verbatim

- **WHEN** a combat operation succeeds on an identity whose committed row carries a `resurrectable` flag
- **THEN** the response reports that committed flag verbatim and whether it is greater than zero
- **AND** the ledger is byte-identical

#### Scenario: An absent committed flag is reported as absent, never as zero

- **WHEN** a combat operation succeeds on an identity whose committed row does not carry a `resurrectable` key
- **THEN** the response reports the flag as absent
- **AND** does not read the absence as zero

#### Scenario: A row absent from the recorded map is reported as absent

- **WHEN** a combat operation succeeds on an identity with no row on the recorded map
- **THEN** the response reports the row as absent and carries no team value
- **AND** the operation is not refused

#### Scenario: Neither gate is enforced as a precondition

- **WHEN** a combat operation is applied to an identity that would fail either reported gate
- **THEN** the operation still proceeds and destroys nothing
- **AND** the response reports the gate outcome without refusing on it

### Requirement: Every refusal resolves before any write, so a refused request leaves the whole persisted document byte-identical

The service SHALL complete every validation — structural, content, identity, and
recorded state — **before** any row, ledger, or resource is written, so that a refused
request provably leaves the whole stored document byte-identical, including the
dead-hero ledger, the placed rows, storage, and every other key.

The preserved server's ordering cannot be reproduced because it performs no validation
at all; the ordering requirement therefore exists to make this service's refusals safe
rather than to match a recorded ordering. The preserved server's two unguarded absent
value dereferences are recorded as unreachable in v1, because v1 carries no list and
no victim object for a request to omit.

The refusal vocabulary SHALL be a closed table shared by every route, and this
operation SHALL NOT name a refusal reason that is absent from it.

#### Scenario: A refused request leaves the whole document byte-identical

- **WHEN** a combat request is refused for any reason
- **THEN** the whole stored document is byte-identical to its state before the request, including the dead-hero ledger and every placed row
- **AND** every stored resource is byte-identical

#### Scenario: The destruction refusal is its own closed code

- **WHEN** a request attempts to name a destruction, casualty, or damage figure
- **THEN** the server refuses it with the single named destruction refusal code declared in the shared table
- **AND** no other reason is invented for the same request shape

### Requirement: The post-execution proof is two-part, and only its second half is evidential

Every action SHALL carry a two-part post-execution proof: the addressed identity
resolved to the committed unit row the response reports, the two reported gates match
committed content and recorded state, the whole persisted document including the
dead-hero ledger and every placed row is **byte-identical**, and every stored resource
the server knows about is byte-identical.

The second half SHALL compare the **complete** stored resource set the service exposes,
and SHALL NOT compare a subset. It SHALL also compare the complete stored document, not
only the addressed subtree.

The second half is the falsifiable half, and it is falsifiable **because** the
destruction is refused: every alternative this design rejected — destroying one row,
destroying every eligible row, destroying the client-computed `A - B` — removes a
placed row or increments the ledger, and therefore fails the whole-document comparison.
The first half is a specification check rather than an evidence claim, because this
service is the only implementation writing the save on this path and it diverges from
the preserved branch by design; it SHALL NOT be presented as parity.

#### Scenario: A successful combat changes no leaf and no resource

- **WHEN** a combat operation succeeds
- **THEN** the whole stored document is byte-identical to its value before the request, including the dead-hero ledger
- **AND** every stored resource is byte-identical to its value before the request

#### Scenario: The proof would fail any destruction

- **WHEN** the delivered post-execution proof is exercised
- **THEN** an implementation that removes any placed row or increments the ledger by any amount fails the whole-document half of the proof
- **AND** this is asserted by a test rather than by comment
