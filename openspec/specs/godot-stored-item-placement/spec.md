# godot-stored-item-placement

## Purpose

Deliver the stored-item round trip — placing a stored item onto the map and selling one
back out of storage — as two intent-only, server-derived operations whose server-owned
row slots are computed by the service from committed content, with a verbatim and
fail-closed storage projection, three deliberate refusals the legacy server omits, one
recorded geometry gap left unrefused, and an executed-legacy fixture seeded through
committed content rather than a client-sent item list.

## Requirements

### Requirement: Storage contents are projected verbatim and fail closed

The client SHALL read a player's storage as the map-level record `maps[0]["store"]`
together with the ledger `privateState.boughtUnits`, reporting each stored item's
committed count and the ledger's contents **verbatim**, and SHALL fail closed —
reporting the storage as unresolvable and changing no value — when the store is
absent or is not a mapping, when a count is not an integer, or when the ledger is
present but not a list. The projection SHALL derive no capacity, no stacking
limit, no expiry, no value, and no price: the committed save records none, so no
such rule exists to reproduce. It SHALL NOT label the store a purchase inventory
or attach a refund to any entry.

#### Scenario: Stored counts and the ledger are reported verbatim

- **WHEN** a player's storage is projected
- **THEN** every stored item id appears with exactly its committed count, the ledger appears exactly as recorded including its order and any duplicates the save contains, and no count is recomputed, normalised, or omitted

#### Scenario: An unresolvable store is reported as unresolvable

- **WHEN** the store is absent, is not a mapping, holds a non-integer count, or the ledger is present but not a list
- **THEN** the projection reports the storage as unresolvable with the recorded values it could read, and no entry is invented, defaulted, or dropped

#### Scenario: No storage rule is derived from content

- **WHEN** the storage projection is inspected
- **THEN** it exposes no capacity, expiry, value, or price helper, and the recorded absence of such rules in the committed save is itself reported

### Requirement: Placing a stored item is a server-derived intent and the row is server-owned

Placing a stored item SHALL be an intent-only operation carrying the player, the
stored item id, and the target cell — and **never** a map slot, a row, an
attribute bag, a player team, a stored count, or a price. The service SHALL derive
the map slot itself as the smallest positive integer absent from the map's
placements, SHALL write the row's instant from its own clock, SHALL always write
an empty garrison list and player team `1`, and SHALL derive the row's attribute
bag as a pure function of the committed item's build-click count and friend-
assistable flag — the legacy branch reads a client-supplied player team and never
passes it on, so the team is always `1` and a client-supplied team is ignored
exactly as a client-supplied amount or price is ignored elsewhere. The branch
charges nothing: **no stored resource may move**, and this is proved by an
explicit post-execution check rather than assumed.

The operation SHALL be refused, with a named code and no state change, when the
item is **not in storage**, when the derived slot is **occupied**, when the item id
resolves to **no committed definition**, and when the item is **not placeable**.
Each of these is a deliberate divergence: the legacy server answers success in
every case, and each is recorded as executed probe evidence in the fixture
manifest.

It SHALL NOT refuse an out-of-range or negative cell. That absence is the
already-recorded tile-to-cell geometry gap, it requires new evidence rather than
a derivation, and inventing a bound would fabricate a rule the legacy server does
not have. The refusal of an occupied slot is not a contradiction of that: an
occupied slot silently destroys an existing row and is invisible to any
count-based check, which is a different and more serious failure than an
out-of-range coordinate.

#### Scenario: The row's server-owned slots are derived, never supplied

- **WHEN** a stored item is placed
- **THEN** the service supplies the map slot, the row instant, the empty garrison list, the player team `1`, and the attribute bag derived from the committed item's fields, and no value the client sent for any of them is honoured

#### Scenario: The attribute bag is a pure function of committed content

- **WHEN** a stored item whose committed build-click count is positive is placed, and when a stored item whose committed build-click count is zero is placed
- **THEN** the first yields a build-click counter seeded at zero and the second yields an empty bag, and no client input can add, remove, or alter either key

#### Scenario: No stored resource moves

- **WHEN** a placement succeeds
- **THEN** every stored resource is unchanged, and the post-execution proof asserts each one explicitly so the claim cannot be satisfied vacuously

#### Scenario: An unstored, occupied, unknown, or unplaceable item is refused

- **WHEN** a placement is attempted for an item that is not in storage, a derived slot that is occupied, an item id with no committed definition, or an item that is not placeable
- **THEN** the operation is refused with the corresponding named code and no stored count, placement, or ledger entry changes

#### Scenario: An out-of-range cell is recorded, not refused

- **WHEN** a placement is attempted with a coordinate outside the derived grid, including a negative one
- **THEN** the placement is not refused on that ground and no bounds helper exists to refuse it, and the absence is reported as the recorded geometry gap rather than as an oversight

### Requirement: Selling a stored item credits nothing

Selling a stored item SHALL be an intent-only operation carrying the player and the
stored item id — and **never** a price, a refund, or a quantity. It SHALL remove
exactly one unit of stock, SHALL NOT add or remove a placement, SHALL NOT change
the ledger, and SHALL credit **no** stored resource, because the legacy branch
credits none: its entire effect is one store key disappearing. Selling an item that
is not in storage SHALL be refused with a named code and no state change rather
than silently succeeding as a no-op, since the response is otherwise
indistinguishable from a real sale.

#### Scenario: A sale moves stock and nothing else

- **WHEN** a stored item is sold
- **THEN** its stored count decreases by exactly one, no placement is added or removed, the ledger is unchanged, and every stored resource is unchanged with the post-execution proof asserting each one explicitly

#### Scenario: A sale of nothing is refused

- **WHEN** a sale is attempted for an item that is not in storage
- **THEN** the operation is refused with a named code and the storage, the placements, the ledger, and every stored resource are unchanged

### Requirement: Storage placement is consumable, and one operation consumes exactly one

The client SHALL offer placement from the storage view and SHALL NOT offer a sale
whose result it cannot describe honestly as crediting nothing. The purchase ledger
SHALL be reported as a set of **distinct item ids** and never as a count of units
held: one id added twice leaves one entry. The client SHALL derive no sale value,
no restocking rule, and no relationship between the ledger and the store, because
the committed save records none.

#### Scenario: Place from storage through either implementation

- **WHEN** headless tests run the storage placement flow with the fake implementation selected, and a live run places against a running Compatibility API v0
- **THEN** both implementations yield the same typed result shapes consumed identically by the flow, the flow applies the service's derived slot, instant, team, and attribute bag rather than its own arithmetic, and the scope test still finds no forbidden legacy transport token outside the legacy-v0 implementation

#### Scenario: One placement consumes one unit of stock

- **WHEN** an item is stored at a count above one and is placed
- **THEN** its stored count decreases by exactly one, no quantity argument exists to place more, and the ledger gains the id only if it was not already present

#### Scenario: The ledger counts distinct ids

- **WHEN** the same item id is recorded in the ledger more than once
- **THEN** the projection reports the ledger exactly as recorded and no flow presents it as a unit count, and appending an id already present changes nothing

### Requirement: The stored-item round trip is proved by an executed legacy fixture and a content-derived seed

The stored-item round trip SHALL be captured by executing the real legacy server
inside a disposable copy, and the capture's precondition — an item in storage —
SHALL be established by a **content-derived** command whose only client input is an
identifier and whose granted item is derived from committed content. The capture
SHALL NOT seed its precondition through an unvalidated client-sent item list and
SHALL NOT use a hand-edited save. The four unguarded behaviours SHALL be recorded
in the fixture manifest as executed probes, distinguished from the recorded
transactions.

#### Scenario: Seed the storage from committed content

- **WHEN** the capture runs
- **THEN** the recorded transaction chain is a completion whose granted item is derived from the committed collection table followed by the placement, and no client-sent item id list appears in any recorded request

#### Scenario: The unguarded behaviours are recorded as probes

- **WHEN** the capture records a placement of an item that was not in storage, a placement onto an occupied index, a placement of an id with no committed definition, and a placement at an out-of-range cell
- **THEN** each appears in the manifest as a probe with its observed response and changed-state facts, each is marked as a divergence rather than as parity, and none of them is presented as a recorded transaction

#### Scenario: The time-dependent row instant is documented

- **WHEN** the fixture is written
- **THEN** the row's wall-clock instant is named in the documented time-dependent field list and excluded from byte-stability claims, and the manifest states that rerunning the capture reproduces the after-state except for that field

#### Scenario: Stay contained

- **WHEN** the capture runs
- **THEN** the legacy server runs only in a disposable copy on the loopback port, the working tree's saves and preserved sources are digest-identical before and after, the port is released, and the disposable copy is removed