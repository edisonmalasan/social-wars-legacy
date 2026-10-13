# Spec Delta

## Purpose

Amends the boundary capability that lines 1, 2 and 3 delivered, because this line's
measurement changes one of its claims in a specific respect and moves one arithmetic
figure.

**The claim that changes.** `server-v1-authority-boundary` requires that "every
resource movement is derived by the server from committed content" and demonstrates
that on three worked transactions: `collect` and `complete_collection`, both of which
move resources, and the magic counter transition, which moves none. This line adds a
fourth worked transaction of a category none of the three covers: one that **moves no
stored resource and destroys no row**, whose post-execution proof is **whole-document
byte-identity**, including the dead-hero ledger. The amendment adds that case rather
than replacing any existing one.

**The figure that changes.** The Purpose records "**4** branches have authoritative v1
routes, leaving **59** without one". This line makes `end_attack` authoritative, so the
arithmetic becomes **5** and **58**. The routed/unrouted split of **39** and **24** is
**unchanged** and is restated here only because it is adjacent to the figure that moves;
`POST /v1/combat` is a **v1** route and adds no v0 route, so it cannot move that split.

The change is a widening, not a correction. Every requirement lines 1, 2 and 3
specified stays true; only the count of worked examples, the coverage of the
destruction case, and one arithmetic figure are restated.

The other requirements — server-derived movement, typed refusal, refusal moves nothing,
coexistence with v0, the facade, unknown-field survival, and labelled evidence — are
**not** modified by this change and are left untouched.

## MODIFIED Requirements

### Requirement: `collect` demonstrates the boundary end to end

The collection transaction SHALL be implemented on the v1 boundary as the first vertical
slice, deriving its payout server-side and refusing its documented invalid cases through
the typed channel. Its post-execution proof SHALL check both that the collection instant
moved forward **and** that every stored resource changed by exactly the derived amount,
so that a derivation which moved nothing could not pass as success.

`collect` is chosen because the Compatibility API's own collection is already proven
against a captured executed-legacy fixture, so v1's first slice is measured against an
existing oracle rather than a new one.

The boundary SHALL be demonstrated end to end by **at least four** transactions, and the
second, third, and fourth SHALL each exercise at least one rule the first does not.

`collect` remains the worked example of a **derived payout**: the server derives what a
`collect` *yields* from committed income content, and the client selects only which row
to collect.

`complete_collection` is the worked example of a **derived grant behind derived
preconditions**: the server derives what the collection *yields* from the committed
prize, whether the caller *may* claim it from the committed requirement list, what it
*costs* from the committed price, and whether it *has already* been claimed from the
recorded ledger. Each of those four is a rule `collect` does not exercise.

The magic counter transition is the worked example of a **derived state transition
that moves no stored resource**: the server derives the identity's new counter value
from its own recorded state and from a bound recorded in the preserved source, the
client selects only which committed magic the identity names, and no committed
price, mana cost, or effect magnitude is read to produce it. It demonstrates the
boundary's refusal half on a transaction whose preserved-server counterpart charged
nothing, because the only mechanism by which a legacy client could have paid was a
resource vector applied before the dispatcher opened.

The combat resolution is the worked example of a **refused destruction behind a reported
gate**: the server derives **no** destruction quantity, because the preserved branch's
only quantity is a subtraction of two client numbers and the committed content carries
no value naming this branch's outcome; instead it resolves and reports the two committed
conditions under which the preserved server would credit a destroyed row — the recorded
player team and a committed `resurrectable` flag — without enforcing either and without
writing the ledger, and refuses the client's destruction figure outright. It demonstrates
the boundary's refusal half on a transaction whose preserved-server counterpart removed
a placed row and incremented a ledger, and whose post-execution proof is **whole-document
byte-identity** including the dead-hero ledger, the strongest such instrument on this
boundary.

All four SHALL derive every resource movement they make from committed content, SHALL
refuse a client-supplied resource delta outright, and a refusal in any of them SHALL
move nothing. The combat transaction, which makes no resource movement at all, SHALL
additionally destroy no row and leave the dead-hero ledger byte-identical.

#### Scenario: A collected row advances its instant and pays exactly the derived amount

- **WHEN** a collection succeeds on an addressable row that has reached a committed rung
- **THEN** the row's recorded collection instant advances
- **AND** each stored resource changed by exactly the derived amount for the reached rung
- **AND** the response reports the rung the payout came from

#### Scenario: A collection below the first committed rung is refused

- **WHEN** a collection is requested on a row that has not reached a committed rung
- **THEN** the domain refuses it with a named reason
- **AND** the stored save document is byte-identical to its pre-request bytes

#### Scenario: A collection on a row under construction is refused in the service

- **WHEN** a collection is requested on a row carrying construction state
- **THEN** the domain refuses it with a named reason
- **AND** the row's construction instants are unchanged

#### Scenario: The boundary has two worked transactions, not one

- **WHEN** the boundary is exercised
- **THEN** both `collect` and `complete_collection` are specified end to end
- **AND** each derives every resource movement from committed content
- **AND** each refuses a client-supplied delta outright rather than clamping it

#### Scenario: The boundary has a third worked transaction that moves no resource at all

- **WHEN** the boundary is exercised
- **THEN** `collect`, `complete_collection`, and the magic counter transition are all specified end to end
- **AND** each derives every resource movement it makes from committed content
- **AND** the magic counter transition derives no cost, and the absence of that cost is itself proven rather than assumed
- **AND** each refuses a client-supplied delta outright rather than clamping it

#### Scenario: The boundary has a fourth worked transaction that destroys nothing

- **WHEN** the boundary is exercised
- **THEN** `collect`, `complete_collection`, the magic counter transition, and the combat resolution are all specified end to end
- **AND** the combat resolution derives no destruction and destroys no row
- **AND** the combat resolution reports, without enforcing, the two committed conditions the preserved server would have applied to credit the ledger
- **AND** each refuses a client-supplied delta outright rather than clamping it

#### Scenario: A refused collection completion moves nothing

- **WHEN** a collection completion is refused for any reason
- **THEN** storage, the collection ledger, and every stored resource are byte-identical to before
- **AND** no partial grant survives the refusal

#### Scenario: A transaction that derives no cost is still on the boundary

- **WHEN** a worked transaction charges nothing because the preserved server charged nothing and no committed content establishes a price
- **THEN** the absence of the charge is a specified property with a proof that asserts every stored resource is byte-identical
- **AND** a charge of any size on any stored resource fails that proof

#### Scenario: A transaction that destroys nothing is still on the boundary

- **WHEN** a worked transaction destroys no row because the preserved server's destruction quantity is not derivable from committed content
- **THEN** the absence of the destruction is a specified property with a proof that asserts the whole persisted document, including the dead-hero ledger, is byte-identical
- **AND** a destruction of any size at any identity fails that proof
