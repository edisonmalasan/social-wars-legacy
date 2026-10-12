# Spec Delta

## Purpose

Extends the Server v1 authority boundary from one worked slice to two, by applying it
to the only branch in the routed, fixture-proven half of the command surface whose
**grant** is already server-derived from committed content. Where `collect` derived a
payout from committed income fields, `complete_collection` has an **unbounded,
unconditional, free grant**: no eligibility check, no price, and a grant that repeats.

This delta specifies the three rules that close it - a once-only grant, an
`item_ids`-derived eligibility check, and a `cashPrice`-derived debit - each of which is
a **derived** authority rather than an observed one, and each of which therefore
produces a recorded **divergence** from the preserved branch rather than parity.

## ADDED Requirements

### Requirement: A collection is granted at most once

A Server v1 collection completion SHALL grant a committed collection's prize to a
player **at most once**. The player's recorded collection ledger is the authority for
what has already been claimed, and a completion naming a collection already present in
that ledger SHALL be refused with a typed refusal that names the ledger as its reason.

A refusal to repeat SHALL move nothing: the player's storage, their ledger, and every
stored resource SHALL be byte-identical before and after.

This is stricter than the preserved branch, whose ledger append at
`command.py:517-518` is conditional on absence while the grant itself is not, so a
repeated completion grants the prize again. That divergence is deliberate and is
recorded as such.

#### Scenario: A first completion grants the committed prize exactly

- **WHEN** a player sends a collection intent naming a collection absent from their ledger
- **THEN** the server derives the prize from committed content
- **AND** the granted item id and quantity equal the committed prize exactly
- **AND** no other stored storage key changed
- **AND** the ledger gained exactly one appended id

#### Scenario: A repeated completion is refused and moves nothing

- **WHEN** a player sends a collection intent naming a collection already in their ledger
- **THEN** the server refuses with a typed refusal naming the ledger as its reason
- **AND** storage, the ledger, and every stored resource are byte-identical to before

### Requirement: Collection eligibility is decided by the server from committed requirements

A Server v1 collection completion SHALL verify eligibility before granting. A
collection is eligible only when the player holds **every** item id in that
collection's committed `item_ids` list, and the server SHALL derive that requirement
from committed content rather than accept it from the client.

A completion naming a collection whose requirements are not met SHALL be refused with a
typed refusal reporting which committed item ids are missing. Storage SHALL be
byte-identical after such a refusal.

No v1 request schema SHALL carry a requirement list, a held-item list, or any
eligibility assertion; those are the server's to read, never the client's to state.

#### Scenario: An eligible collection is granted

- **WHEN** a player sends a collection intent and holds every committed requirement id
- **THEN** the server grants the committed prize
- **AND** the response reports the requirement set it evaluated

#### Scenario: A collection whose requirements are unmet is refused

- **WHEN** a player sends a collection intent for a collection whose committed `item_ids` are not all held
- **THEN** the server refuses with a typed refusal naming the missing committed item ids
- **AND** storage, the ledger, and every stored resource are byte-identical to before

#### Scenario: A client-supplied requirement list is refused

- **WHEN** a collection intent carries a held-item or requirement list
- **THEN** the server refuses it as a structural input error
- **AND** the refusal is not a clamped or partially honoured request

### Requirement: The collection price is derived from committed content, never sent

A Server v1 collection completion SHALL derive the completion's cost from the
collection's committed `cashPrice` and SHALL debit the player's stored cash by exactly
that amount through the economy authority. The price SHALL NOT be accepted from the
client in any form.

This is stricter than the preserved branch, which charges nothing at all and leaves any
"cost" to arrive as a client-sent resource vector applied at dispatch before the branch
is selected. That divergence is deliberate and is recorded as such.

A completion the player cannot afford SHALL be refused with a typed refusal, and every
stored resource SHALL be byte-identical after such a refusal.

#### Scenario: A completion debits exactly the committed price

- **WHEN** a player completes an affordable, eligible, unclaimed collection
- **THEN** stored cash decreases by exactly the committed `cashPrice`
- **AND** every other stored resource is unchanged
- **AND** the response reports the derived price rather than echoing a client figure

#### Scenario: An unaffordable completion is refused

- **WHEN** a player completes a collection they cannot afford
- **THEN** the server refuses with a typed refusal naming the derived price and the shortfall
- **AND** every stored resource and the storage and ledger state are byte-identical to before

### Requirement: A collection id that does not name a distinct committed collection is refused

A Server v1 collection completion SHALL require an id that resolves to exactly one
committed collection. Because the committed table is indexed positionally from one,
ids that clamp to the first row - the integer zero and every negative id - resolve to
the same collection as id one, and SHALL be refused rather than served the clamped
prize.

A refusal SHALL report the id requested, the id it would have resolved to, and that the
request was aliased, so no caller can present an aliased id as a distinct collection.

#### Scenario: An aliased id is refused and names its collision

- **WHEN** a player sends a collection intent whose id clamps to the first committed collection
- **THEN** the server refuses with a typed refusal naming the alias and the id it collides with
- **AND** storage, the ledger, and every stored resource are byte-identical to before

#### Scenario: An unresolvable id is refused

- **WHEN** a player sends a collection intent naming an id no committed collection resolves to
- **THEN** the server refuses with a typed refusal
- **AND** storage, the ledger, and every stored resource are byte-identical to before