# Design

## Context

`docs/legacy-m11-event-systems.md` is the binding contract. The findings that
constrain this design:

1. The auction house is the **only** interval- or expiry-driven system in the
   eleven legacy root modules (`interval`: 1 hit, `auctions.py:76` only;
   `expire`: 3 hits, `auctions.py` only).
2. `AuctionHouse()` **cannot construct itself** — `auctions.py:32` guards on
   `FILE_AH_CONFIG` while `:33` reads `FILE_AH_STATE`.
3. Three routes (`server.py:186`, `:217`, `:248`) and the module import
   (`server.py:28-29`) are all commented out.
4. `apply_resources` is absent from the module; `betPrice` is committed and read
   nowhere.
5. `currentPrice = bet_amount + priceIncrement` with **zero** comparison
   operators; a bid of `1` moved the price `5000 → 1001`.
6. `round` is always `1`; `count_expired` is computed at `:127` and discarded.
7. 16 of 21 state keys have no server-side reader; **all** are serialised to the
   wire, so "no reader" is a server-side claim only.
8. Over the 10 genuine save documents, zero carry any auction term.

## Goals / Non-Goals

**Goals**

- Make the three committed auctions legible to the client for the first time,
  through the architecture that already exists.
- Derive exactly one non-committed value, through one named conversion.
- Record every measured refusal with its evidence, labelled as a divergence.
- Keep the bootstrap defect visible as a property of the oracle.

**Non-Goals**

- Any route, any `apps/compat-api/**` change, any live phase, any fixture.
- Any settlement, round, winner, price, fee, countdown or scheduler.
- Any claim about what the Flash client displayed.
- Repairing the bootstrap defect.

## Decisions

### D1 — Normalize the schedule, because the client can read nothing else

`docs/legacy-m11-event-systems.md` §12 listed normalization as out of scope,
with the caveat "unless a proposal says otherwise". This is that case.

The Godot client reads committed content **only** through the normalized
registry (`godot-content-registry`); `premium_purchase.gd` is the precedent for
reading a committed schedule through it. A projection without a normalized table
would have to read `config/auctionhouse.json` directly, introducing a second
parallel path into committed content and contradicting the structure established
since M4.

**Rejected alternative:** read the raw config from the client. Rejected because it
creates a content path that no other line uses, and because the raw file has no
schema, no coercion record, and no round-trip evidence.

**Consequence:** the change is two capabilities, not one. That is a dependency,
not scope creep, and it is recorded in the proposal rather than drifted past.

### D2 — Preserve `uuid` as a string; do not convert `interval`

Two encodings are load-bearing and both are preserved verbatim.

`uuid` stays the JSON string `"1"`. `auctions.py:106` keys the state document by
it and the committed table declares it quoted; an integer would claim a type the
source does not carry.

`interval` stays in **minutes** and the builder performs no conversion. The
`× 60` lives in exactly one named client function with a named inverse, matching
`COLLECT_MINUTES` in `godot-building-collect`, where the ladder is committed in
minutes and both row instants are Unix seconds.

**Rejected alternative:** normalize `interval` into seconds in the builder.
Rejected because it would hide the only non-obvious arithmetic in the surface
inside a data file, where a reader cannot see that a conversion happened, and
because it makes the package disagree with its own source about units.

### D3 — Normalization is read-only and never imports the module

The builder SHALL NOT import or execute `auctions.py`. Importing it would
execute `__init__`, which calls `os.makedirs` on `AUCTIONS_DIR` — a path relative
to the process cwd — creating an `auctions/` directory as a side effect of
reading committed content. The module also raises on construction, so an import
would have to be caught and swallowed to proceed.

**Rejected alternative:** import the module to resolve unit names through
`get_name_from_item_id`. Rejected on both counts above; unit names come from the
normalized items package instead, which is the cross-domain reference edge every
other builder already uses.

### D4 — Exactly one derivation, in exactly one function

The single derived value is the duration, `interval * 60`. The conversion lives in
one named function with a named inverse and a round-trip assertion over every
committed entry.

Nothing else is derived. No price, no fee, no total, no remaining time, no round
number, no winner, no ranking. Each of those would require a rule the oracle does
not have: the price path is client-dictated (finding 5), there is no round
counter (finding 6), and no winner is ever computed from amounts.

The suite asserts this absence mechanically, as `godot-mission-vocabulary`
asserted that the module contains no multiplication or division lines at all.

### D5 — No route, no compat change, no live phase

Three reasons, each independent:

- There is no request path to route. All three routes are commented out
  (finding 3).
- There is no corpus instance and none can be manufactured: zero of the 10
  genuine saves carry an auction term, and the state lives in a document the
  module cannot create (finding 8, finding 2).
- A live phase would require a client transport and a `GameApi` forwarder for a
  surface with nothing to call.

`godot-darts` set the precedent of a content-derived line with a
state-mutating endpoint and no live phase; here there is not even an endpoint.

### D6 — No executed-legacy fixture, and the reason is specific

This is the decision most likely to be mistaken for a limitation, so the reason
is stated exactly.

**It is not** a missing corpus row — unlike `godot-unit-instances` and
`godot-unit-behaviors`, the blocker is not that the corpus lacks an instance.
The blocker is that the behaviour has **no request path**. A fixture would have
to be produced by instantiating `AuctionHouse` directly against a hand-seeded
state document, which is not a transaction any client ever made. Committing it
would misrepresent a dead surface as a served one and would license a round trip
the client does not have.

Enabling the commented-out routes to obtain a genuine fixture would modify legacy
behaviour to make a modern test easier, which `AGENTS.md` forbids
("Do not modify legacy behavior merely to make modern implementation easier").

The investigation's Part-2 figures all came from such a constructed precondition
and are labelled as constructed at every step. They are evidence about the
module's logic; they are not a fixture and are not carried forward as one.

### D7 — Report the zero-consumer findings; claim no ordinal

`betPrice` is carried and marked `bet_price_consumed: false`. No ordinal is
claimed for it. Four earlier lines each numbered zero-consumer fields over a
different scope, and no reconciled census of zero-consumer committed fields
exists in the repository — the same reasoning `godot-construction-assist`
recorded when it declined to number `giftable` and `gift_level`.

### D8 — Record the bootstrap defect; forbid the repair

The bootstrap failure is a requirement of this capability, not commentary. The
risk it guards against is specific and quiet: a later implementer reads
"auction house is commented out", helpfully makes it construct, and the client
now claims parity with a system that could never run.

So the delivered modules SHALL contain no state-document creation, default or
repair path, and the suite asserts that absence.

### D9 — "No server-side reader" is scoped precisely

16 of 21 state keys have no **server-side** read. Every key is serialised to the
wire by the disabled routes, so the Flash client may have read all of them.

The delivered wording is therefore "no server-side reader", never "dead field",
never "unused". This is the same limitation already recorded for `social_items`
and the `MISSION_*` vocabulary, and it is repeated here rather than inherited
silently.

### D10 — One suite, one evidence report, self-measuring figures

A single hermetic suite, registered in `verify-boot.ps1`, carrying its own
authored evidence report whose tables are derived from the live projection and
registry so they cannot drift from the code they document.

Every zero-consumer and absent-helper figure is **re-derived from the committed
sources on every run**, so a legacy edit fails the suite rather than silently
contradicting it. This is the `godot-mission-vocabulary` discipline: the
declaration count and gap set were recomputed each run rather than pinned.

The anti-invention guards are structural: a pinned declared-function inventory
is the real gate, and reserved-name checks are the belt. Both directions are
proven by injection with byte-identical restores, and probes are measured for
failure count rather than merely checked for a non-zero exit.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Normalizing a table the server never reads is dead weight | Accepted deliberately: the table names real endgame units and is the only committed content for this surface. The alternative is leaving committed content invisible. |
| A future line reads `betPrice` as a charge | `bet_price_consumed: false` in the package, cited to the zero-consumer measurement |
| A future implementer "fixes" the bootstrap and claims parity | D8 makes the defect a delivered requirement with an asserted absence |
| Deriving a price or winner to "complete" the surface | D4 plus an inventory-pinned absence assertion; inventing either is an injection the suite catches |
| The refusal is misread as "nothing was delivered" | The schedule, the resolved units and the derived duration **are** delivered; the refusals are scoped to specific measured behaviours |

## Migration Plan

Purely additive. A new builder, a new normalized file and manifest section, two
new client modules, one new suite and one new evidence report. No existing
normalized file, no legacy module, no save, no fixture and no
`apps/compat-api/**` file changes.

Rollback is deletion of the added paths plus removal of the manifest section;
nothing else depends on them.

## Open Questions

None blocking. Two are recorded as deferred rather than open:

- **Round history.** `betUsersPrev`, `prevRoundBidders` and `userRounds` are the
  residue of an unimplemented round system. Projecting them would be projecting
  fields with no reader and no writer, so they are recorded and not projected.
- **Asset truth.** No committed image matches `auction|bet|bid`, so there is no
  visual surface to verify and no windowed capture is claimed. This is
  consistent with the other refusal lines.