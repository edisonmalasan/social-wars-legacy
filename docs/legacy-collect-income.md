# Legacy collect income (investigation record)

Status: **investigation complete, and the six decisions resolved by the
`building-collect` change** (design D1–D6, delivered and archived
`2026-09-30-building-collect`). The investigation below is preserved as the
evidence base; the resolutions are recorded in "The six decisions, as
resolved" at the end, and one further probe was executed to settle the
shared-field question. It follows the method the `building-upgrade` and
`building-construction` changes used: committed legacy source first, then
executed-legacy probes, with the *established* / *derived* boundary drawn
explicitly.

No Flash, Ruffle, ActionScript, or browser executed. The probe ran the real legacy
server on `127.0.0.1:5055` inside a disposable copy under the system temp root,
wrote nothing into the repository, and removed its copy on exit.

## The command

| Command | Args | Effect | Source |
| --- | --- | --- | --- |
| `collect` | `[item_index]` | `item[3] = time_now()` and **nothing else** | `command.py:136-147` |

A missing row logs an error and returns early (still persisting the batch), so -
exactly as the move, sell, store, and upgrade lines established - the endpoint
must resolve the index before executing rather than reporting legacy's success.

**The income is not computed by the server.** `apply_resources` runs before the
branch (`command.py:40`, `engine.py:251-271`) and applies the client-sent 8-slot
vector verbatim, per resource, as `max(current + delta, 0)`. The `collect` row of
the command catalog states it outright: "Income itself travels through
client-sent deltas; the branch only stamps the timer." Legacy's own comment on
`engine.py:252` records the intent - "So these will be negative if the user used
resources and positive if the user gained resources, we can detect cheats by
checking if any are less than 0 after applying" - which the `max(…, 0)` clamp on
the very next lines makes impossible. That is a legacy bug candidate, not a rule
to reproduce or "fix" here.

## Where the income amount actually comes from: committed content

Unlike every earlier deliver line, a **content source exists**, so this is the
first line whose derived resource vector need not be neutral:

| Field | Meaning | Corpus facts |
| --- | --- | --- |
| `collect` | the amount produced per collection | `0` for 727 of 778 stored items; `10`, `100`, `150`, `250`, `350`, `500`, `1800` for the rest |
| `collect_type` | which resource it produces: `g`, `w`, `o`, `s`, `c` | 731 `g`, 23 `w`, 11 `o`, 11 `s`, 2 `c` |
| `collect_xp` | xp produced per collection | `0` for 419 items; `1`–`40` otherwise |
| `max_collects` | a cap, where non-zero | `0` for 767 items; `25` (9 items) and `100` (2 items) |
| `COLLECT_MINUTES` | the collection ladder's waiting times | `[5, 60, 240, 480]` |
| `COLLECT_MULTIPLIER` | the matching multipliers | `[0.25, 1, 2, 3]` |
| `COLLECT_HELP_SECONDS` | a friend-help duration | `3600` |

So a collection has a **tiered** amount: a building collected early yields less,
and the ladder tops out at 480 minutes. The elapsed time is measured from the row's
own `item[3]`, which is the field the `collect` command stamps - the same field the
construction line already reads as a build's start instant. Note the overlap and
the ambiguity it creates, which the next change must decide explicitly rather than
guess: **`item[3]` serves as both a construction start instant and a
last-collection instant**, and the construction line writes it through `activate`
while `collect` overwrites it.

**The committed corpus has no income-bearing buildings except decorations.** All
40 placed rows: the Command Center (`26`), walls, turrets, bridges, the Space
Station, and the harbours all record `collect 0`; the only rows with income are
the decorations - the **Tree** (`905`) at map slot 2 and the eight **Trees** /
**Small forest** rows (`930` / `931`) at slots 21-28, each with `collect 20`,
`collect_type "w"` (20 wood), `collect_xp 1`, and `activation 6`. The real income
buildings (factories, depots) are not placed, so a corpus fixture must use a
decoration.

All 40 rows also carry `item[3] == 0`, so nothing has ever been collected and the
elapsed time for any of them is unbounded - which makes the **top ladder tier
(3x) deterministic** for a fixture.

## Executed-legacy probe

One command, `collect(2)` on the Tree, carrying a deliberately recognisable
vector `[0, 7, -5, 60, 0, 0, 0, 0]` (xp +7, gold -5, wood +60):

```
row 2 before: [905, 53, 39, 0,       0, [], {}, 1]
row 2 after : [905, 53, 39, 1790696251, 0, [], {}, 1]
placements 40 -> 40; every other row byte-identical
privateState identical (boughtUnits [], deadHeroes {}); store {}; playerInfo identical
xp 4 -> 11; wood 2000 -> 2060; gold 2000 -> 1995; oil/steel/cash/mana unchanged
response {"result":"success"} (HTTP 200)
```

Established by this probe: the branch stamps **only** the row's timestamp; the
client-sent vector is applied **verbatim**, per resource, including a negative
delta; nothing else in the save moves.

**The clamp was deliberately not exercised** - a `-5` gold delta on a `2000`
balance stays positive, so no clamping occurred. The clamp itself remains what
`engine.py:262-268` says: `max(current + delta, 0)` per resource, i.e. it only
bites when a delta would drive a resource below zero. A future fixture that needs
to observe the clamp must send a delta larger than the balance.

## Established versus derived

**Established** (committed source, plus the probe): the command's argument shape
and its single effect (`item[3] = time_now`); that the income is the client-sent
vector applied verbatim per resource with the `max(…, 0)` clamp; the content
fields that describe a building's income (`collect`, `collect_type`,
`collect_xp`, `max_collects`) and the ladder globals; the corpus facts above.

**Derived and never observed from the Flash client** - and these are the open
questions the next change must resolve *explicitly* rather than by guessing:

1. **Whether the ladder multiplies the amount at all.** `COLLECT_MINUTES` and
   `COLLECT_MULTIPLIER` sit side by side and obviously pair, but no branch reads
   them, so the real client's formula is unobserved. A defensible derivation is
   `amount = collect x multiplier_of_the_reached_tier` (Tree: 20 x 3 = 60 wood).
2. **Whether `collect_xp` is multiplied by the same tier** or added flat.
3. **How the tier is chosen below 5 minutes** - whether a collection below the
   first rung yields `0.25x`, nothing, or is refused.
4. **Whether `max_collects` caps a single collection, a daily total, or a
   building's lifetime output** - `0` presumably means unlimited, but that is an
   inference from the distribution, not a recorded rule.
5. **What "collect" means for the ladder's clock when a building is still under
   construction** - the shared `item[3]` field is stamped by both commands, so
   constructing a building also resets its collection clock, and which stamp a
   real client sends first is unobserved.
6. Whether a resource-type collection ever yields `cash` (`collect_type "c"`,
   2 items) and whether `mana` is ever produced (no item sets a mana collect type,
   so the ladder's top of the vector is almost certainly always zero).

## Shape of the next bounded change

- One intent-only endpoint (`POST /v0/collect`) taking only the row's index, with
  the vector **derived from committed content** - the first delivered line whose
  derived vector is deliberately not neutral, and therefore the first that must
  document each rung of the ladder it implements and each question it answers by
  derivation rather than observation.
- A pre-execution row read plus a post-execution proof in the family's style: the
  row still exists, and its recorded collection instant moved forward.
- A client collection readout: the amount and resource a collection would yield
  for the reached tier, the next rung's time, and a `Collect` action - the sixth
  mutually exclusive mode on the selection-driven surface - that sends exactly one
  intent and applies only the authoritative response (the new resource values come
  from the response, never from the client's own arithmetic).
- **Decide and document the `item[3]` overlap**: either the collection clock
  ignores rows carrying construction state, or a construction stamp is understood
  to reset the collection clock. Either choice is a derivation and must be a named
  claim limit.
- The same claim limits as the delivered lines: the ladder formula, the xp rule,
  the sub-first-rung rule, and the cap semantics are derived; parity covers one
  recorded transaction against the fresh-player corpus; and the server enforces
  only structural input validity, with authoritative validation belonging to
  Server v1 (M13).

## One further probe, and the six decisions as resolved

The `item[3]` question above could not be settled by reading, because both
commands write the field silently. One more batch was executed on the real legacy
server: `activate(11, 3600)` then `collect(11)` with `[0, 1, 0, 20, 0, 0, 0, 0]`.

```
row 11 before: [22, 58, 48, 0,       0, [], {},             1]
row 11 after : [22, 58, 48, 1790703572, 0, [], {"cp": 3600}, 1]
xp 4 -> 5; wood 2000 -> 2020; every other row, privateState, playerInfo byte-identical
response {"result":"success"}
```

`item[3]` moved to the **collect** instant while `attr["cp"] = 3600` **survived**,
so the row still advertises a full hour of construction measured from the wrong
epoch — an active build's timer is silently restarted, and the legacy server
reports success. So the overlap is not ambiguous, it is corruption.

| # | Question | Resolution (all derived) |
| --- | --- | --- |
| D1 | multiplier formula | `amount = collect × COLLECT_MULTIPLIER[r]`, `r` the highest committed rung the elapsed time has reached, **clamped at the top**. **The committed ladder is in minutes and both instants are Unix seconds**, so the comparison converts through one named constant (300 / 3 600 / 14 400 / 28 800 s), each boundary asserted from both sides. Found during implementation: comparing the units directly would have paid the top rung within five seconds |
| D2 | `collect_xp` scaling | scaled by the **same** rung, rounded half-up (so the 0.25 rung of `collect_xp 1` pays `0`). The flat alternative is the recorded rejected option |
| D3 | below the first rung | **refused in both layers** — the client offers no action and the service fails closed `too_early` (409) — so a sub-rung amount is never derived |
| D4 | `max_collects` semantics | `0` implemented as "no cap"; a non-zero cap fails closed `capped_collection` (409) rather than choosing between per-collection, daily, and lifetime readings |
| D5 | the `item[3]` overlap | **refused in both layers**: the client offers no `Collect` action for a row carrying construction state, and the service fails closed `construction_in_progress` (409) *before* the dispatcher runs, so a client that ignores the client-side rule still cannot corrupt the delivered construction timers |
| D6 | cash / experience semantics | `g`/`w`/`o`/`s`/`c` map to the vector's gold/wood/oil/steel/cash slots; the unread slot 0 and the **mana** slot 7 are always zero (no item records a mana collect type); an unmapped type fails closed `unknown_collect_type` (409) |

The delivered endpoint additionally proves its post-state **twice**: the row's
collection instant moved forward **and** every stored resource changed by exactly
the derived delta, so a clamp that reduced a payout is reported rather than
trusted. On the committed corpus that lands the Tree at slot 2 (never collected,
so the elapsed time is unbounded and the top rung is deterministic) at
`xp 4 → 7` and `wood 2000 → 2060` from the derived vector
`[0, 3, 0, 60, 0, 0, 0, 0]`, with only `item[3]` changing on the row.
