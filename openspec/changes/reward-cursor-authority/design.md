# Design

## Context

`/v0/reward` already exists and already refuses. It advances no cursor, grants nothing, and
reports the cursor's recorded bounds and addressability gap. It was delivered by M10 line 1 as
a **cursor** capability, not an authority capability, and its refusal of the grant is total:
seven grant-shaped classes are refused by name.

What it leaves in place is the branch's actual defect. `command.py:446` computes
`next_id = args[1] + 1` and `command.py:451` clamps it to `1` above the literal `5`. The
arithmetic is the server's own; the input is the client's. The recorded fixture executes the
consequence rather than arguing it — an oversized client-sent next id moves a stored cursor
**backwards**, `4 -> 1`.

The stamped instant compounds this. `timestampLastBonus` is written at `command.py:454` and
subtracted at `command.py:914` inside `fast_forward`, where the subtracted number is
**client-supplied**. It has **zero readers** across all eleven legacy modules. So the field is
client-writable and nothing consumes it: there is no daily window, no cooldown, and no
already-claimed check anywhere in the preserved server to reproduce.

`apps/server-v1/` is the first slice that refuses rather than applies client input. Its
structure is fixed by lines 1-4: a closed `RefusalCode` table in `server_v1_refusals.py` that
no route may extend, a domain module per surface, and a typed result module on the client.

## Goals / Non-Goals

**Goals:**

- Derive the successor cursor from the recorded document, keeping the preserved arithmetic and
  replacing the client input.
- Refuse every grant-shaped input by name, resolving each before the cursor moves.
- Make the *absence* of a payout and of an eligibility rule **proven properties** with proofs
  that would fail if either were implemented.
- Report the bound, the rejected derivation, and the addressability gap without enforcing
  anything the oracle does not enforce.

**Non-Goals:**

- Paying anything. `DAILY_GOLD_REWARDS` and `MONDAY_BONUS_REWARDS` stay unread.
- Deriving eligibility, cooldown, or a claim window. There is no oracle rule to derive.
- Decoding the schedule's type letters. The delivered line reports them undecoded and a later
  line wanting those readings must re-derive them.
- Modifying `apps/compat-api/**` at all, including `/v0/reward`.
- Reproducing the backwards move.

## Decisions

### D1 - One route, two branches, `operation` field

`POST /v1/reward` with a closed two-value `operation` vocabulary, following `/v1/magic`,
which already covers `buy_magic` and `use_magic` behind one route.

*Alternative rejected:* two routes. It would double the transport and the refusal plumbing for
a second branch that differs only in its cursor field and its bound.

### D2 - The successor is derived from the **stored** cursor

`next = stored + 1`, then the preserved clamp. The request carries **no** cursor contribution
of any kind, and a request carrying one is refused as a structural input error.

*Alternative rejected:* accept a next id and validate it against the bound. That is a range rule
the oracle does not have, and the whole point of the line is that the oracle's cursor is
client-directed.

*Alternative rejected:* reproduce the backwards move and clamp to the floor, matching the
oracle. That is a divergence this project records, not reproduces — and reproducing a cursor
regression would defeat the line.

### D3 - The bound is the preserved literal `5`, with the rejected derivation retained

The daily bound is the branch literal at `command.py:451`, **not** `len(DAILY_GOLD_REWARDS)`.
The two agree today — the schedule holds exactly five entries — and the agreement is recorded
as a **coincidence**. A constant whose derivation was guessed would be one legacy edit away
from silently becoming a different rule.

*Alternative rejected:* derive the bound from the schedule. It would be a derivation the
oracle never performed, and the delivered M10 line already reached this conclusion and retained
the rejection.

### D4 - No payout, proven rather than assumed

The post-execution proof asserts that **every** stored resource, storage, and the bought-unit
list are byte-identical across a successful transaction. Because the transaction succeeds and
still moves nothing, the proof is not tautological — it is the same instrument shape as
`collect`'s, with the comparison inverted.

### D5 - No eligibility rule, and the zero-reader finding is re-derived

The instant is written and reported and never consulted. A test re-derives that
`timestampLastBonus` has zero readers across all eleven legacy modules, counting occurrences and
distinct lines separately, and fails if a reader ever appears — rather than asserting the
absence from a transcribed table.

### D6 - New refusal codes on the existing closed table

The grammar in `server_v1_refusals.py` is a fresh vocabulary, not a subset of v0's 104 codes,
and no route may grow its own answer. This line adds codes there and nowhere else, taking the
table from 20 to its new size. The inventory and its `< N` pin move together with the test that
asserts the literal spelling of the count, as line 4 found when the same two pins had to move
in lockstep.

### D7 - The two client-side count pins move together

`test_auction_schedule.gd` and `test_market_trade.gd` hold the battery's hermetic-suite and
live-phase counts. Adding a suite and a live phase moves both pins in both files. They are
amended **in place**, which is the established pattern for a count this change legitimately
moves, and is distinct from amending an already-archived line's behavioural assertion.

### D8 - `apps/compat-api/**` is not modified

The v0 route and its 7-transaction executed-legacy fixture are the oracle this line is measured
against. A live phase would drive v1 against the committed fixture read as bytes, never
re-captured.

## Risks / Trade-offs

- **The derivation has no committed content behind it** — the only two M13 transactions with
  committed prices are `collect` and `complete_collection`, and this line has neither. Mitigation:
  the absence of a payout is itself a specified, proven property, and the spec says so plainly
  rather than dressing the transition as derived-from-content.
- **A v1 client can advance a cursor once per request with no gate**, which is what the oracle
  allows. This is a deliberate refusal to invent a cooldown. Mitigation: recorded as a
  Server v1 / M13 gap in the line's claim limits, with the zero-reader measurement attached.
- **The backwards move is now unreachable**, so any client relying on it breaks. Mitigation:
  recorded as an explicit divergence, and no committed fixture asserts it as required behaviour.
- **Route placement is fragile.** Adding a fifth v1 route can break suites that slice a
  handler's source between route markers. Mitigation: declare the route's position and assert
  it, as `test_tutorial_endpoint.RoutePlacementTests` does, rather than relying on accident.