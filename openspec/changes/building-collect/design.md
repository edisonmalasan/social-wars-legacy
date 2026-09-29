# Design

## Context

See `proposal.md` — Why, and the committed investigation record
`docs/legacy-collect-income.md`. The legacy mechanics are **established**; what
remained were six *client/gameplay derivation decisions* that no amount of legacy
evidence can settle, because no branch reads the content that describes them.
This design answers all six explicitly, marks each as derived-provisional, and
records the one additional executed probe that closed the only question where
"safest behavior supported by evidence" was not already clear.

### Established (unchanged from the investigation record)

- `collect(item_index)` writes **only** `item[3] = time_now` (`command.py:136-147`).
- The income is the client-sent 8-slot vector `[unknown, xp, gold, wood, oil, steel, cash, mana]`
  applied verbatim per resource as `max(current + delta, 0)` (`engine.py:251-271`),
  run before the branch (`command.py:40`).
- Per-item income content: `collect` (amount; `0` for 727 of 778 stored items),
  `collect_type` (`g` 731, `w` 23, `o` 11, `s` 11, `c` 2), `collect_xp` (`0` for 419),
  `max_collects` (`0` for 767; `25` and `100` for 11).
- Ladder globals: `COLLECT_MINUTES = [5, 60, 240, 480]`,
  `COLLECT_MULTIPLIER = [0.25, 1, 2, 3]`, `COLLECT_HELP_SECONDS = 3600`.
- Corpus: the only income-bearing placed rows are the decorations - the **Tree**
  (`905`) at map slot 2 and the **Trees** / **Small forest** (`930` / `931`) at
  slots 21-28, each `collect 20`, `collect_type "w"`, `collect_xp 1`. Every one of
  the 40 rows has `item[3] == 0`, so nothing has ever been collected and the
  elapsed time for any of them is unbounded - the **top rung is deterministic**.
- Probe 1: `collect(2)` with `[0, 7, -5, 60, 0, 0, 0, 0]` moved only the row's
  timestamp and applied the vector verbatim (`xp 4→11`, `wood 2000→2060`,
  `gold 2000→1995`); the clamp was **not** exercised, because −5 on 2000 stays
  positive.

### The additional probe, and what it decided

The delivered construction line reads `attr["cp"]` together with `item[3]` as a
build's start instant and countdown, and `collect` writes the same field. Whether
collecting during a build is merely ambiguous or actually destructive was not
answerable from source reading, so one more batch was executed on the real
server: `activate(11, 3600)` then `collect(11)` with `[0, 1, 0, 20, 0, 0, 0, 0]`.

```
row 11 before: [22, 58, 48, 0,       0, [], {},             1]
row 11 after : [22, 58, 48, 1790703572, 0, [], {"cp": 3600}, 1]
xp 4 → 5; wood 2000 → 2020; every other row, privateState, playerInfo byte-identical
response {"result":"success"}
```

`item[3]` moved to the **collect** instant while `attr["cp"] = 3600` **survived**.
The row therefore still advertises a full hour of construction, but its start
instant is now the collection time: the delivered client's remaining-time
derivation `cp - (now - item[3])` measures the countdown from the wrong epoch and
silently restarts an active build's timer, and legacy reports success. So the
overlap is not ambiguous - it is corruption, and the safe rule (D5) is forced.

## The six decisions, answered

**D1 — The multiplier is applied to the amount, rung chosen by elapsed time
(derived).** `amount = collect × COLLECT_MULTIPLIER[r]`, where `r` is the highest
index whose `COLLECT_MINUTES[r]` threshold the elapsed time `now - item[3]` has
reached; the elapsed time is clamped at the top rung rather than extrapolated.
Evidence that supports the pairing: the two globals are parallel four-element
arrays and the collection amount is otherwise a constant, so a ladder that did
not scale the amount would have no effect at all. No branch reads them, so the
formula itself is **derived-provisional**, and the claim is limited to "a payout
that grows in four committed rungs", not to any specific amount the legacy client
would send. For the corpus the answer is deterministic: every row's `item[3]` is
`0`, so the top rung applies - the Tree pays `20 × 3 = 60` wood and
`1 × 3 = 3` xp.

**D2 — `collect_xp` scales with the same rung (derived).** The experience is part
of the same collection payout, and applying the committed ladder to only part of
it would leave the vector internally inconsistent. The alternative - a flat
`collect_xp` - is equally unobservable and is recorded here as the rejected
option, so a later change can revisit it with evidence rather than rediscover it.

**D3 — Below the first rung, no collection is offered and none is executed
(derived).** `COLLECT_MINUTES[0] = 5` with a multiplier of `0.25` reads as "five
minutes in, a quarter of the full amount", which leaves the sub-five-minute case
unspecified: a quarter, nothing, or a refusal. The safe reading is the one that
invents no amount: the client offers no `Collect` action and sends nothing, and
the endpoint independently fails closed with `too_early` when no rung is reached,
so a speculative payout can never be derived. Both rules are **derived**, and the
refusal is exercisable only against a row whose instant is recent (no corpus row
is), so it is covered by a stubbed instant rather than by a fixture.

**D4 — A non-zero `max_collects` fails closed; only `0` is implemented (derived).**
`0` on 767 of 778 items reads as "no cap", and the corpus's income rows all record
`0`. What a non-zero value caps - one collection, a daily total, or a building's
lifetime output - is unobserved, and the three readings imply different payouts.
The endpoint therefore answers `capped_collection` (409) for such an item instead
of picking one. Exercisable only by stubbing, exactly as the construction line's
`no_build_time` was.

**D5 — Collect is refused on a row carrying construction state, in both layers
(established risk, derived rule).** The probe above shows that executing a
collection on a row with `attr["cp"]` (or `attr["nc"]`) overwrites the build's
start instant while the countdown survives, silently restarting an active build's
timer, and that legacy answers success. So: the client offers no `Collect` action
for such a row and refuses with an explicit reason, **and** the endpoint fails
closed with `construction_in_progress` (409) *before* the dispatcher runs, so a
client that ignores the client-side rule still cannot corrupt the timers the
delivered construction line depends on. The two-layer choice is deliberate: the
compat layer exists precisely so that client-supplied intent cannot destroy
server state, and a single client-side check would be a client-trust assumption.
The rule is still **derived** in the sense that the legacy client is never observed
and may well avoid this state by other means; what is established is that legacy
does not prevent it and reports success when it happens.

**D6 — Only the five committed resource types are produced, and mana never is
(derived).** `collect_type` values are `g`, `w`, `o`, `s`, `c`, mapping onto the
vector's gold, wood, oil, steel, and cash slots; the vector's `mana` slot is left
zero because no item records a mana collect type, and the unread `unknown` slot 0
is left zero as every other delivered line does. A `collect_type` outside the five
fails closed with `unknown_collect_type` rather than being coerced, so a content
change can never silently pay the wrong resource.

## The remaining decisions of the change

**D7 — Intent-only contract `{user_id, item_index}` with a content-derived
payout.** No amount, resource, tier, or time from the client: the endpoint reads
the row, resolves the item's `collect` / `collect_type` / `collect_xp` /
`max_collects` from the loaded configuration, computes the elapsed time against
its own clock, derives the vector, and executes. This is the first delivered line
whose vector is deliberately **not** neutral, and therefore the first whose
artifacts must document each rung of the ladder it implements and each decision it
answers by derivation.

**D8 — The post-state is proved twice, including the money.** After execution the
endpoint requires: the row still exists and is a row; its recorded collection
instant moved **forward**; and **every** stored resource changed by exactly the
derived delta (so a clamp that reduced a payout, or any other divergence, is a
fail-closed `internal_error` rather than a reported success). This is the
family's strongest proof and the first that checks a *value* the client would
otherwise trust.

**D9 — Validation split, and the client's readout.** The client owns what the
server cannot see: the countdown to the next rung, the refusal below the first
rung, and the construction-state refusal; the endpoint owns structural input
validity, the content refusals (`capped_collection`, `unknown_collect_type`,
`no_build_time`-style gaps), the `too_early` and `construction_in_progress`
guards, and the post-state proof. Authoritative validation remains Server v1
(M13) work.

**D10 — Evidence, claim limits, and containment.** A windowed fake-API capture
driving the flow a player uses plus a headless deterministic `collect-report-v1`
report (inputs and digests, the intent, both rows, the derived payout and the rung
it came from, the rung ladder, the next-rung countdown, the resource movement, the
projection-constants pointer, the established-versus-derived split, and explicit
non-claims), byte-identical across reruns. Execution and containment carry forward
unchanged: unchanged legacy `command()` in-process over a disposable corpus,
loopback only, no new packages, both batteries plus the guard baseline and the
3,258-entry hash manifest green in the final state, and the orchestrator-run
integration review as the fallback for the unavailable dedicated verification
workflow.

## Risks / Trade-offs

- **Every number in the payout is derived, not observed** → the boundary is drawn
  once, in D1-D6, and carried verbatim into the envelope docstring, the fixture
  README, both application READMEs, and the report's own provenance section; the
  claim is "a payout that grows in four committed rungs, derived from the item's
  committed income fields", never "the amount the legacy client pays".
- **The endpoint now has a wall clock in its contract** → the tier it derives
  depends on `now`, so the response carries the reference instant it used and the
  deterministic report pins the same instant, exactly as the construction line
  pinned its displayed countdown; the fixture's corpus rows (`item[3] == 0`) make
  the tier deterministic in every run.
- **A client that ignores the client-side construction refusal still cannot
  corrupt a timer** → D5's second layer; the compat test drives the refused
  request against a row that carries construction state and asserts the corpus is
  byte-identical.
- **The payout is server-applied, so a wrong derivation would mint resources**
  → mitigated by D8's value-level proof and by the neutral, client-refused
  alternatives in D3 and D4: where the evidence was thin, the change refuses
  instead of guessing.
- **A sixth mode on one surface** → modes stay mutually exclusive, each keeps its
  own state, and the seven delivered suites must stay green, so a regression shows
  up in an existing suite rather than hiding behind the new one.
- **The ladder's lower rungs are untested against a real clock** → they are unit
  covered at the pure-helper level with explicit instants, and the endpoint's
  rung selection is covered against the deterministic top rung plus a stubbed
  instant, never against a live wall clock.
