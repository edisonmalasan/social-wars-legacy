# Spec Delta

## Purpose

Project the committed auction schedule read-only into the modern client, with the
measured behaviour of the legacy auction house recorded as explicit refusals
rather than reproduced, so that a dead surface stays legible without becoming a
false claim of parity.

## ADDED Requirements

### Requirement: Read-only projection of the committed schedule

The client SHALL project the committed auction schedule through the existing
normalized content registry, and SHALL NOT read `config/auctionhouse.json`
directly. Each projected entry SHALL carry its committed `legacy_id`, `level`,
`interval`, `price`, `priceIncrement` and `betPrice`, plus the resolved unit id
and display name. The projection SHALL be read-only: it SHALL mutate no state,
issue no request, and expose no affordance that begins, extends, or bids on an
auction.

#### Scenario: Entries project verbatim

- **WHEN** the projection runs
- **THEN** it yields three entries in committed order, `legacy_id` `"1"`, `"2"`,
  `"3"`
- **AND** each carries the committed level, interval, price, priceIncrement and
  betPrice unaltered
- **AND** each carries its resolved unit id and display name

#### Scenario: The projection is read-only

- **WHEN** the projection is built
- **THEN** no game state is written
- **AND** no network request is issued
- **AND** the module exposes no callable action for placing, bidding on,
  starting, extending or cancelling an auction

#### Scenario: Content is read only through the registry

- **WHEN** the projection's source of committed content is inspected
- **THEN** it reads the normalized package through the content registry
- **AND** it does not read the raw committed config file
- **AND** no delivered module references a raw config path for this schedule

### Requirement: Exactly one derived value, through one named conversion

The projection SHALL derive exactly one value that is not committed: the auction
duration in seconds. The committed `interval` is in **minutes**; the conversion
factor is `60`, and it SHALL live in exactly one named function with a named
inverse, so that the unit of the committed field is stated in one place.

No other arithmetic SHALL be performed. In particular the projection SHALL NOT
derive a price, a fee, a total, a remaining time, a round number, a winner, or a
ranking.

#### Scenario: The duration derives from the committed interval

- **WHEN** a committed `interval` of `120` is projected
- **THEN** the duration is `7200` seconds
- **AND** a committed `interval` of `60` yields `3600` seconds
- **AND** the conversion is the single named conversion, not an inline literal

#### Scenario: The conversion round-trips

- **WHEN** the named inverse is applied to a derived duration
- **THEN** it returns the committed interval exactly, for every committed entry

#### Scenario: Nothing else is derived

- **WHEN** the projection is inspected for arithmetic
- **THEN** it contains no derivation of a price, fee, total, remaining time,
  round, winner or ranking
- **AND** that absence is asserted by the suite rather than merely intended

### Requirement: The expiry semantics are recorded as recorded, not implemented

The projection SHALL record the legacy expiry boundary exactly as measured, and
SHALL NOT implement any countdown, scheduler, timer or clock read. The recorded
facts are: an auction with no bidder is replaced at `endDate + 1`; an auction
with at least one bidder survives until `endDate + 60`; and the round is reset to
the literal `1`.

These are properties of the oracle reported for reference. The delivered client
SHALL NOT offer a player any way to observe, wait for, or act on them, because
the surface has no request path through which a player ever could.

#### Scenario: The boundary is reported verbatim

- **WHEN** the recorded expiry semantics are read
- **THEN** the no-bidder boundary is `endDate + 1`
- **AND** the one-bidder boundary is `endDate + 60`
- **AND** the round reset is the literal `1`

#### Scenario: No timer is implemented

- **WHEN** the delivered modules are inspected
- **THEN** no countdown, scheduler, timer or clock read is present
- **AND** no module exposes a remaining-time or ready-state helper

### Requirement: The bootstrap defect is recorded as a property of the oracle

The client SHALL record that the legacy auction house cannot construct itself,
and SHALL NOT implement a bootstrap that succeeds.

The measured fact is that `auctions.py:32` guards on `FILE_AH_CONFIG` while
`:33` reads `FILE_AH_STATE`, so construction raises `FileNotFoundError` on a
machine holding the committed config and no leftover state. A modern
implementation that bootstrapped successfully would be implementing something the
original never did, and must not present that as parity.

#### Scenario: The defect is recorded, not repaired

- **WHEN** the recorded oracle properties are read
- **THEN** the bootstrap failure is stated with its cause and both line numbers
- **AND** the delivered client contains no state-document creation, default or
  repair path for this surface

#### Scenario: The recorded reason is the measured one

- **WHEN** the bootstrap record is inspected
- **THEN** it attributes the failure to the guard reading a different file than
  the one it tests
- **AND** it does NOT attribute the surface's inertness solely to the
  commented-out import, which is a second and independent reason

### Requirement: Client-dictated outcomes are refused, not reproduced

The projection SHALL NOT reproduce the measured client-dictated behaviour as
parity, and SHALL state each refusal with its measurement. The recorded
behaviours are:

- the bid amount is client-supplied and stored unvalidated, with **zero**
  comparison operators against `bet_amount`, `currentPrice`, `beginPrice` or
  `betPrice`; a bid of `1` moved `currentPrice` from `5000` to `1001`, and
  `-5000` produced `-4000`;
- `checkFinish` is client-sent and is the only thing that can make `betWinner`
  appear;
- no winner is derived from bid amounts, and `won` is unconditionally `1`.

Each of these is a **divergence** from the preserved branch, not parity.

#### Scenario: The refusals are stated with their evidence

- **WHEN** a client-dictated outcome is recorded
- **THEN** the record names the measured behaviour, including the value the
  preserved branch produced
- **AND** it is labelled a divergence rather than parity
- **AND** no delivered module implements the client-dictated price path

#### Scenario: No price is charged

- **WHEN** the projection is inspected
- **THEN** no resource is debited and no resource field is computed
- **AND** the committed `betPrice` is reported as an unconsumed committed price
  rather than as a charge

### Requirement: No route, no compatibility change, no live phase, no fixture

This capability SHALL add no route, SHALL touch no `apps/compat-api/**` file,
SHALL add no live phase, and SHALL capture no executed-legacy fixture.

The fixture is refused for a specific measured reason, and the reason is **not**
a missing corpus row: the auction behaviour has **no request path**, because all
three routes and the module import are commented out. A fixture would have to be
produced by instantiating `AuctionHouse` directly, which is not a transaction any
client made and would misrepresent a dead surface as a served one. Enabling the
routes to obtain one would modify legacy behaviour to make a modern test easier,
which `AGENTS.md` forbids.

#### Scenario: No server surface is added

- **WHEN** the change is applied
- **THEN** no route is declared
- **AND** no `apps/compat-api/**` file is modified
- **AND** the registered live-phase count is unchanged

#### Scenario: No fixture is fabricated

- **WHEN** the delivered evidence is inspected
- **THEN** it contains no executed-legacy auction fixture
- **AND** it states that the blocker is the absent request path, not an absent
  corpus instance
- **AND** the committed config is left untouched

### Requirement: Anti-invention guards are structural and proven by injection

The suite SHALL assert the absence of any mechanism this capability does not
deliver, and those guards SHALL be proven by injection rather than trusted. Each
probe SHALL be restored byte-identically, and the suite SHALL assert the
delivered modules' declared-function inventory so that a new helper is caught by
the inventory itself and not only by a name check.

#### Scenario: An invented helper fails the suite

- **WHEN** an invented helper is injected into a delivered module
- **THEN** the suite fails on more than one independent check
- **AND** restoring the byte-identical file returns the suite to its passing
  state

#### Scenario: The inventory is the real gate

- **WHEN** an injected helper borrows no reserved word
- **THEN** the declared-function inventory still fails the suite

#### Scenario: Absences are measured, not inherited

- **WHEN** the suite reports a zero-consumer or absent-helper figure
- **THEN** it is re-derived from the committed sources on every run
- **AND** a legacy edit fails the suite rather than silently contradicting it