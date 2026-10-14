# server-v1-reward-authority

## Purpose

Lets a Server v1 client advance a daily or weekly reward cursor from what the server has
recorded, with every grant-shaped input refused by name and no payout ever derived.

## Requirements

### Requirement: The reward cursor is derived from recorded state, never from a client-sent next id

The reward transaction SHALL derive a branch's successor cursor from the cursor the
recorded save document already carries. It SHALL NOT accept a next id, an offset, or any
other cursor contribution from the client, and a request carrying one SHALL be refused as a
structural input error rather than clamped, coerced, or partially honoured.

The preserved branch computes `args[1] + 1` and clamps the result, so the arithmetic is
the server's own while its input is not. The transaction SHALL replace the input, not the
arithmetic, and SHALL report the stored cursor before, the derived cursor after, and the
change between them.

The preserved branch's **backwards** transition - an oversized client-sent next id moving a
recorded cursor from 4 to 1 - SHALL be recorded as a divergence from the oracle. It SHALL
NOT be reproduced, because reproducing a client-directed cursor regression would defeat the
purpose of making the cursor authoritative.

#### Scenario: A daily cursor advances from the stored value

- **WHEN** a daily reward transaction succeeds on a recorded document
- **THEN** the recorded cursor advances to its derived successor
- **AND** the response reports the stored value before, the derived value after, and the change
- **AND** no client-sent value contributed to either

#### Scenario: A client-sent next id is refused rather than used

- **WHEN** a reward request carries a next id, offset, or successor
- **THEN** the domain refuses it with a named reason and an empty payload
- **AND** the stored cursor is byte-identical to its pre-request value

#### Scenario: The backwards transition is a divergence, not a behaviour

- **WHEN** the preserved branch would have moved a recorded cursor backwards
- **THEN** the transaction records that outcome as a divergence from the oracle
- **AND** no request can produce a backwards move in the stored document

### Requirement: No reward is paid and no stored resource moves

The reward transaction SHALL move **no** stored resource, SHALL grant **no** item, and SHALL
apply **no** committed reward ladder. The preserved branches credit nothing: the daily arm's
grant is a client-sent item id written into storage and a deduplicating unit list, and its
non-granting arm only prints.

This SHALL be a specified property with a proof, not an assumption: the post-execution proof
SHALL assert that **every** stored resource is byte-identical across a successful
transaction, so a grant of any size fails that proof.

The committed schedules `DAILY_GOLD_REWARDS` and `MONDAY_BONUS_REWARDS` SHALL be reported
and left unread. Applying either would diverge from the oracle, which pays nothing.

#### Scenario: A successful reward transaction moves no stored resource

- **WHEN** a reward transaction succeeds
- **THEN** every stored resource is byte-identical to its pre-request value
- **AND** storage and the bought-unit list are byte-identical to their pre-request values
- **AND** a grant of any size at any resource fails that proof

#### Scenario: A client-sent grant is refused by name

- **WHEN** a reward request carries an item id, a cell, a player identity, or a map index
- **THEN** each is refused with its own named reason and an empty payload
- **AND** the refusal is resolved before the cursor advances

### Requirement: The cursor bound is the preserved literal, and the rejected derivation is retained

The daily cursor bound SHALL be the literal `5` recorded in the preserved source, not a
length derived from a committed schedule. The two happen to agree, because
`DAILY_GOLD_REWARDS` holds exactly five entries, and the transaction SHALL record that
agreement as a **coincidence** with the rejected derivation retained beside it.

The weekly bound SHALL be the count reported by the preserved source's own accessor. Where
the recorded corpus carries a cursor the bound cannot address, the transaction SHALL report
the addressability gap rather than silently clamping into it.

#### Scenario: The daily bound is the literal, with the rejected derivation recorded

- **WHEN** the daily bound is reported
- **THEN** it is the preserved literal
- **AND** the rejected schedule-length derivation is retained in the recorded material beside it
- **AND** the agreement between them is labelled a coincidence, not a derivation

#### Scenario: An unaddressable stored cursor is reported, not silently clamped

- **WHEN** a stored cursor names a position the bound does not address
- **THEN** the response reports the addressability gap
- **AND** no rule is derived that would resolve it

### Requirement: No eligibility rule is derived, and its absence is reported

The reward transaction SHALL NOT derive an eligibility, cooldown, daily-window, weekly-period,
or already-claimed rule. The preserved server has none to reproduce: the instant each branch
stamps has **no reader anywhere** in the eleven legacy modules, so nothing consumes it.

The stamped instant SHALL be written and reported, and SHALL NOT be consulted to decide
whether a transaction may proceed. The zero-reader finding SHALL be a specified property,
and a test asserting it SHALL re-derive the absence rather than restate it.

#### Scenario: The stored instant is reported without gating the transaction

- **WHEN** a reward transaction succeeds
- **THEN** the response reports the instant before and after
- **AND** no rule consulted the instant to decide whether the transaction was permitted

#### Scenario: The stamped instant has no legacy reader

- **WHEN** the absence of an eligibility rule is asserted
- **THEN** the assertion re-derives that the stamped instant is written and never read across every legacy module
- **AND** the assertion fails if a reader ever appears
