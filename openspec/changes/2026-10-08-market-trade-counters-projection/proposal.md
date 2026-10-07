# Proposal

## Why

M11's final deliver item is `special mechanics`. The measurement committed in
`docs/legacy-m11-special-mechanics.md` re-derived all **63** named dispatcher branches
and classified them, then ran an ownership audit against the **71** delivered specs to find
which special-mechanics surfaces are genuinely unowned.

That audit **displaced the census's own rank #1**. The Atom Fusion / Soul Mixer queue — the
surface carrying the single strongest corpus artifact in the milestone — is **already
owned** by `godot-unit-queues`, which claims it in a requirement titled *"The atom-fusion
speedup is recorded without a cost or a timer"* and whose archived change records
**D6 — "`soulmixer_speedup` is recorded verbatim and implemented not at all"**. Proposing it
would re-open a deliberately settled decision.

The audit promoted the **market / trade counters**, on evidence no other candidate matches:

- **Eight** committed `MARKET_*` globals, **every one with zero legacy consumers** — raw and
  quoted, across all eleven modules.
- Two branches of **opposite shape**. `timestampLastTrade` has a **live reader**
  (`engine.py:238`, the day-bucket comparison). `numTradesDone` has **one** reader and it
  **is its own increment** (`command.py:469`) — so the cap at `:470` is a *stored value*,
  never an enforced limit.
- **Two corpus rows.** `villages/Nerri.json` sits **at the cap of 20**. `villages/Neutral.json`
  records a non-zero instant with a cleared count, and because `trade_resource` is the
  **only** site in the eleven modules that can raise the instant from 0 (`fast_forward` only
  subtracts and floors at 0), that row **proves** the day-bucket reset fired after a trade.

Neither fact is recorded anywhere. `godot-building-resources/spec.md:119` names "the market
and trade counters" only to place them **out of scope**, and `field_stability.py:99-104`
already notes the reset is boundary-dependent while observing that it is *invariant* for the
fixture corpus — which is exactly the detail that decides what can and cannot be evidenced.

The name of the deliver item is not the surface, once more: `friends` was a directory
listing, `social rewards` a paid substitute with no friend writer, `legacy event systems` a
module that cannot construct itself, and here the census's top candidate was already
delivered.

## What Changes

- Add a **read-only projection** of the trade-counter state: the committed count, the
  committed instant, the day bucket each side of the reset predicate, the predicate itself
  evaluated against the server clock, and the branch's own remaining-trades arithmetic.
- **Derive exactly one value** — the cap of **20** — from the **branch literal** at
  `command.py:470`, through a single named constant, and record that it coincides with the
  committed `MARKET_MAX_NUM_TRADES` without deriving it from there.
- **Reproduce the legacy print defect as a reported field**, not correct it:
  `command.py:473` prints `20 - num_trades` from the *unclamped* local, so the reported
  remaining count goes **negative** from the 21st trade onward while the stored count stays
  clamped.
- **Report the reset predicate, never perform it.** `engine.reset_stuff` is the engine's and
  is referenced, not reimplemented.
- Project the **eight committed `MARKET_*` values verbatim** with their measured
  zero-consumer status, and derive **no** price, cap, period, or percentage from them.
- Record and refuse to reproduce the two measured behaviours that constitute the "Bad"
  client-dictates-the-outcome pattern: resource movement that would arrive through
  `engine.apply_resources` **before** the dispatcher chain opens, and an instant that
  `fast_forward` makes client-writable by subtracting a client-supplied number of seconds.
- **No route, no `apps/compat-api/**` change, no live phase, and no executed-legacy
  fixture.** Each is a decision with a measured reason, recorded in the design — the fixture
  refusal in particular is *not* a missing corpus row but a property of the corpus itself.

## Non-goals

- **No enforcement.** Nothing in the preserved server reads the count to decide anything, so
  nothing here may present the cap as a limit, refuse a trade, or gate an affordance.
- **No price, no cost, no period, no percentage.** The committed schedule has no consumer, and
  a market economy derived from unread content would be an invention.
- **No route.** A client affordance for a transaction that grants nothing is precisely the
  surface the `social-rewards-assist-projection` line refused.
- **No claim that the Flash client displayed, gated, or hid anything.** Every finding here is
  source- and corpus-derived.
- **No ownership of the bonus ladders** (`godot-rewards`), the queue (`godot-unit-queues`), or
  the darts instants (`godot-darts`).

## Impact

- **Affected capability:** `godot-market-trade-counters` (new).
- **Affected code:** two new read-only client modules and one new hermetic suite, registered
  in `verify-boot.ps1`. No endpoint, no service change, no compat-API edit.
- **Affected specs:** one new capability; **no existing spec is amended**, because the single
  existing mention (`godot-building-resources:119`) is an out-of-scope note that this line
  satisfies rather than contradicts.
- **Preservation:** no legacy, config, save, village, content-package, conversion-package, or
  registry-manifest byte changes.
- **Claim limits are load-bearing and travel with the change.** In particular the fixture
  corpus **cannot** witness accumulation: **8 of 10** committed documents record
  `timestampLastTrade == 0`, for which the reset predicate is unconditionally true, so the
  count is cleared on every load. `Nerri.json` is the only document that reached the cap, and
  that is **one** data point.
