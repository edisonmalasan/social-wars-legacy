# Proposal

## Why

`POST /v1/collect` (M13 line 1) and `POST /v1/collection` (line 2) both landed on a
surface where the legacy server already reached an answer from committed content.
Line 3's target is the one the binding selection record
(`docs/legacy-m13-line3-candidates.md`, PR #394) ranked first: the `buy_magic` /
`use_magic` pair at `POST /v0/magic`. It is the strongest available candidate, and
`§7.3` of that record says plainly that **no remaining pool branch is as strong as
`complete_collection` was**.

This proposal takes that target and, in the course of measuring it, **contradicts
the selection record's central economic claim**. The record ranked the pair first on
`R1` — "`magics.json` carries a complete price vector over a contiguous id space
`1..10`" — and instructed a v1 line to "derive the charge/price from committed
`magics.json`". Measurement says the price is **not derivable from this table by
any rule this repository can justify**, and the proposed design therefore **refuses
it rather than deriving it**.

### What the branches do

`command.py:652-663` (`buy_magic`) and `command.py:664-675` (`use_magic`):

```python
elif cmd == "buy_magic":
    magic_id = args[0]
    magics = save["privateState"]["magics"]
    if str(magic_id) in magics:
        magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)
    else:
        magics[str(magic_id)] = 0
```

`use_magic` is the same twelve lines with `+=` replaced by `=`. Four facts, each
measured rather than read off the selection record:

- **Both arms _increase_ the counter.** `use_magic` writes
  `min(50, x + 1)`, not `x - 1`. Nothing in the preserved server ever *spends* a
  charge. The name `use` is the only place consumption is asserted anywhere.
- **The selection record's `buy_magic` description is wrong.** Its §6.2 row 1 reads
  "`+=` then clamped `min(50,…)`". The `min` bounds the **increment**, not the
  total, so `buy_magic` is **unbounded** and climbs past 50 indefinitely, while
  `use_magic` is bounded at 50 and **destroys** an existing counter above it
  (113 → 50). The recorded fixture measured exactly this, and
  `openspec/specs/godot-damage/spec.md` already specifies both refusals at v0.
- **The ledger has zero readers.** `privateState["magics"]` has 17 occurrences
  across all eleven legacy modules — 12 in `command.py`, 5 in `version.py` — and
  every one is a **write**, a membership test, or the `version.py:32-37`
  container coercion. `get_game_config.py` contains **0** occurrences of `magics`.
  The legacy server reads the player's counters and **never reads the committed
  table that describes what those counters buy**.
- **Nothing is charged, and this was executed.** `tests/fixtures/godot-damage/`
  holds **12 dedicated magic transactions** (6 per arm) plus a `login_post`. Every
  request carries a **neutral** eight-slot vector `[0,0,0,0,0,0,0,0]`, **no**
  resource slot moved in any of the twelve, and `privateState.mana` held at **15**
  across a `use_magic` — so the one stored resource that shares a name with a
  committed price column was measured *not* moving.

### The price question, answered by measurement

`packages/game-content/normalized/magics.json` carries **10** rows, ids `1..10`
contiguous, with four numeric columns: `gold` (10 distinct), `cash` (10 distinct),
`mana` (6 distinct), `level` (9 distinct). **None of the four is named a price.**
`level` is not a currency at all. The comparison with line 2's table is decisive and
runs the wrong way:

| | line 2 (`collections.json`) | line 3 (`magics.json`) |
|---|---|---|
| field naming the outcome | `prize` — one object, one reading | none; four numeric columns |
| field naming a cost | `cashPrice` — **named a price**, sitting beside `prize` | none |
| ambiguity in the "cost" | none | `gold`? `cash`? `mana`? all three? |
| committed rows reachable in the corpus | 10 | 10 ids, **0 affordable** |

Two further measurements close the question:

- **The fresh corpus can afford nothing.** `tests/saves/fresh-player.json` records
  gold `2000`, `playerInfo.cash` `5`, `privateState.mana` `0`. The cheapest gold in
  the table is `10000`, the cheapest cash is `30`, the cheapest mana is `8`. **No
  committed magic is affordable on any column** by the corpus the live phase drives.
  A v1 line that charged any column would answer `insufficient_resources` on every
  request, and the route's success path would be unreachable in the committed
  corpus.
- **Mana has exactly one legacy writer, and it is the client.**
  `engine.py:268` is inside `apply_resources`'s eight-slot vector (`resource[7]`),
  applied at `command.py:40` **before the dispatcher's first branch condition at
  `command.py:42`**. So a legacy client could pair any mana debit with a
  `buy_magic`, and v1 has no way to know what it meant.

**Therefore: v1 charges nothing, and the committed numeric columns are reported
verbatim and never read to compute a debit.** The authority hole is not the price —
it is the client-sent vector, which is the *only* mechanism by which a legacy
client could have paid at all. v1 closes it by **refusing** `client_supplied_delta`,
and proves the refusal by asserting that **every stored resource is byte-identical
across a successful magic operation**. That assertion is falsifiable: it is exactly
what a charge would break.

### What is established, and what stays unknown

| Claim | Status |
|---|---|
| Both arms' arithmetic, verbatim, including that both **increase** | **established** (branch body, executed fixture) |
| `min(50, …)` is the only bound, and it bounds the increment | **established** |
| The counter is keyed by `str(magic_id)` with no validation | **established** |
| The committed id space is `1..10` and the corpus keys resolve against it | **established** (table + corpus, not by name) |
| The committed `gold`/`cash`/`mana` columns are a price vector | **refuted as derivable** — see above |
| What a counter *means* | **unknown**; v1 calls it a counter, never charges |
| What `mana` is spent on | **unknown** and unanswerable here: `use_magic` never reads it |
| What `50` means | **unknown**; v1 applies it as a recorded bound, not as a rule |
| What the Flash client displayed | **unknown, permanently** |

## What Changes

- **`POST /v1/magic`** added to `apps/server-v1/`: one route, one request
  `{player_id, magic_id, operation}` with `operation` a **closed two-value set**
  `{buy, use}` mirroring v0's own `magic_envelope.ACTIONS`. The action vocabulary is
  v0's, not `command.py`'s, for the reason line 2 recorded: v1's vocabulary must not
  become a subset of the 63 branch names.
- **The magic identity is bound to the committed id space.** An id that names no
  committed magic row is refused. The preserved server accepts any identity,
  including a float that becomes a *distinct* ledger key — recorded by the fixture
  step `txn_use_float_id_creates_a_distinct_key` — so this is a **divergence**.
- **The counter is bounded and never reduced.** `buy_magic`'s unbounded climb and
  `use_magic`'s charge-destroying assignment are both **refused**, carrying forward
  the two rules `godot-damage` already specified at v0, and a recorded counter
  already above the cap is refused with its own code rather than clamped.
- **Both operations are the same bounded increment, and that alias is documented
  rather than papered over.** The two preserved arms differ only in a defect, so v1
  has no rule to distinguish them by; the surface is kept at two operations because
  the v0 surface has two and the recorded divergence is stated once.
- **No price, and the absence is a proof half rather than an omission.** Every
  success carries a two-part post-execution proof whose second half is that **all
  seven v1 stored resources are byte-identical**.
- **The committed `level` column is reported and never enforced** as a gate, because
  **0 of 33** committed save documents at level 1 reach any magic — enforcing it
  would make the route unexercisable on the committed corpus — and because no
  legacy comparison of a player's level against any content `level` exists.
- **Three codes extend the closed refusal table, two of them new.** A third
  candidate code was rejected by a measured guard: `test_boundary_invariant.py:392`
  asserts `len(RefusalCode) < 20`, the table holds **17**, and a third new code
  would make it exactly 20 and fail. See `design.md` D8.
- **`buy_mana_new` becomes explicitly unreachable** at v1 as well as at v0, which
  is where the `39`/`24` routed/unrouted split of
  `docs/legacy-m13-unrouted-branches.md` stands today. The two disputed branches
  become authoritative, so the "branches without an authoritative route" figure
  moves **61 → 59**. The routed/unrouted split does **not** move, and this proposal
  does not edit the document that carries it.

## Non-goals

- **No change to `apps/compat-api/**`.** It is the parity oracle, not the thing
  being replaced. Line 1's D1 (coexistence) holds unchanged.
- **No SQL, PostgreSQL, or Alembic migration.** Line 1's D4 defers them.
- **No change to `godot-damage`'s delivered v0 surface.** That spec already owns
  the counter transition, the identity refusals, the cap, and "no price is charged";
  this line re-decides the same questions with authority over them and does not
  re-specify the v0 client surface.
- **No claim about what the Flash client displayed, sent, or charged.** Every rule
  below is derived from committed content or the preserved branch, never observed
  from the client.
- **No windowed capture and no pixel-parity claim**, because nothing is rendered.
- **No ordinal claimed for any zero-consumer field.** Four conflicting ordinals
  already exist over four different scopes.

## Impact

- Affected specs: `server-v1-magic-authority` (new),
  `server-v1-authority-boundary` (extended — the boundary gains a third worked
  transaction, of a category the first two do not cover).
- Affected code: `apps/server-v1/` only, plus the client-side `ServerV1Api` facade
  the boundary already registered, plus the v1 live-phase registration.
- The Compatibility API suite stays at its recorded baseline as a **verified**
  figure, because this change adds no v0 route and touches no `apps/compat-api/**`
  file.
