# Design

## Context

`buy_magic` (`command.py:652-663`) and `use_magic` (`command.py:664-675`) are the
top-ranked target of `docs/legacy-m13-line3-candidates.md` §7.1 and the only
remaining D6-pool branch whose committed content is **corroborated by the corpus**
rather than by a name. This design re-derives every ranking-relevant figure, and
**contradicts the selection record's economic claim** (§ Instrument faults and
§ Contradictions below).

### The two branches, read as executed

```python
elif cmd == "buy_magic":            elif cmd == "use_magic":
    magic_id = args[0]                  magic_id = args[0]
    magics = save["privateState"]        magics = save["privateState"]
      ["magics"]                          ["magics"]
    if str(magic_id) in magics:          if str(magic_id) in magics:
        magics[str(magic_id)] +=             magics[str(magic_id)] =
            min(50, magics[...]+1)              min(50, magics[...]+1)
    else:                                else:
        magics[str(magic_id)] = 0             magics[str(magic_id)] = 0
```

Four measured properties, each of which carries a decision below:

1. **Both arms increase the counter.** `use_magic` writes `min(50, x + 1)`. There
   is no `x - 1` anywhere in either arm, and no other branch in the preserved
   server writes `privateState["magics"]` at all. Nothing ever **spends** a charge.
2. **`min(50, …)` bounds the increment, not the total.** `buy_magic` is therefore
   **unbounded**: repeated purchases climb past 50 and keep climbing.
   `use_magic` is bounded at 50 and **destroys** an existing counter above it — the
   executed fixture recorded `113 → 50`.
3. **The identity is unvalidated.** `str(magic_id)` becomes a ledger key. The
   fixture's `txn_use_float_id_creates_a_distinct_key` records a float identity
   producing a key distinct from the integer's.
4. **The absent-key arm writes `0`, not `1`.** Both branches take the `else` arm for
   an identity with no recorded entry and write that entry at **zero**, so the
   preserved server's "acquire a spell you hold none of" path increments nothing.
   This is the third legacy asymmetry after the two above, and it is the one the
   fresh corpus reaches **first** (its ledger is `{}`).

### The committed table, measured

`packages/game-content/normalized/magics.json`, all ten rows, all fifteen fields
present on every row:

| id | `legacy_id` | name | gold | cash | mana | level | `target` | `area` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `"1"` | AirStrike | 30000 | 50 | 8 | 38 | 2 | [5,7,9] |
| 2 | `"2"` | Medic Case Rain | 40000 | 60 | 8 | 40 | 1 | [5,7,9] |
| 3 | `"3"` | Protection Shield | 60000 | 80 | 8 | 45 | 1 | [5,7,9] |
| 4 | `"4"` | Nuclear Bomb | 90000 | 110 | 20 | 52 | 2 | [5,7,9] |
| 5 | `"5"` | Shortcircuit Inductor | 80000 | 100 | 10 | 50 | 2 | [5,7,9] |
| 6 | `"6"` | Magnetic Trap | 50000 | 70 | 12 | 42 | 2 | [25,30,35] |
| 7 | `"7"` | Mech Summoner | 70000 | 90 | 16 | 48 | 0 | [5,7,9] |
| 8 | `"8"` | Stealth Sneak | 100000 | 120 | 8 | 55 | 1 | [5,7,9] |
| 9 | `"9"` | Alien Abduction | 20000 | 40 | 15 | 35 | 2 | [5,7,9] |
| 10 | `"10"` | Attack Boost | 10000 | 30 | 10 | 35 | 1 | [5,10,15] |

Five measured properties carry the design:

- **`id == position + 1` on every row, with no gaps.** The raw `config/main.json`
  `magics` is a positional list of ten whose `id` equals its one-based position.
- **`legacy_id` is the string form of `id`** on every row, as for every
  `legacy_id` in the normalized packages.
- **No field is named a price.** `gold` 10 distinct, `cash` 10 distinct, `mana` 6
  distinct, `level` 9 distinct. Contrast `collections.json`, whose `cashPrice` is
  *named* a price and sits beside `prize`.
- **`area` is a JSON string in the raw config**, coerced to a list by normalization.
  Reported verbatim as normalized; the coercion is recorded, not interpreted.
- **`kind` is `"magic"` on all ten rows**, so the table is unambiguous about what
  it is.

### Corpus feasibility, measured over 33 real save documents

34 committed JSON candidates were walked; `tests/saves/manifest.json` has no
`privateState` and is excluded, leaving **33 real save documents**.

| Fact | Value |
|---|---|
| `privateState.magics` shape | `{}` in **32**, `{"1":2,"2":0,"4":2,"9":1,"10":0}` in **1** (`villages/Neutral.json`) |
| All five populated keys resolve against committed ids | **yes** — 1, 2, 4, 9, 10 all within 1..10 |
| `privateState.mana` spread | `0`×11, `15`, `50`, `200`, `1600`×19 |
| `privateState.energy` | `50` on all **33** |
| `maps[0].level` spread | 1..67; level 1 in **3** documents |
| Documents whose level reaches *any* magic's `level` | **9–11 of 33** per magic; **0** at level 1 |
| Documents affordable the cheapest `gold` (10000) | **6 of 33** |
| Documents affordable the cheapest `cash` (30) | **8 of 33** |
| Documents affordable the cheapest `mana` (8) | **22 of 33** |
| `tests/saves/fresh-player.json` affordability | **none** — gold 2000, cash 5, mana 0 |

Three corpus facts decide D2, D5 and D8 respectively:

- The **fresh corpus cannot afford any committed magic on any column.** A charge
  would make `/v1/magic` answer a refusal on every request in the live phase.
- **No document at level 1 reaches any magic.** A level gate would do the same.
- **Every one of the 33 documents already carries a dict `magics`.** So the
  `version.py:32-37` coercion path, and any ledger-shape refusal, are unreachable
  through the committed corpus and must be exercised over an in-memory row — the
  same pattern line 1 used for `no_build_time`.

### Fixture strength

`tests/fixtures/godot-damage/` holds **13 steps**: `login_post` plus **12 dedicated**
magic transactions, 6 per arm — the best in the D6 pool after `add_xp_unit` and
`end_attack`. Ids sent: `1`, `3`, `99`, `1.0`, `"1"`. Every request carries the
neutral vector `[0,0,0,0,0,0,0,0]`. **No resource slot moved in any of the twelve**
— this is the strongest single input to D2 and the selection record does not mention
it. The capture manifest claims parity for only **3** steps, records **9**
divergences and **7** `not_claimed` items, among them "a per-magic price, mana cost,
or effect for any of the ten committed magics".

### Ownership, measured

- `openspec/specs/godot-damage/spec.md` names `buy_magic` and `use_magic` (once
  each) and already specifies "No price is charged", the identity refusals, the
  recorded literal cap, and the refused asymmetries.
- `openspec/specs/server-v1-authority-boundary/spec.md` names both branches and
  `/v0/magic`.
- **No spec names any `/v1/` route path.** A `grep` for `/v1/` across
  `openspec/specs/**` returns zero hits.

## Goals / Non-Goals

**Goals**

- Put the magic identity under committed-content authority.
- Put the counter transition under authority, bounded and never reduced.
- Make the **absence** of a price a specified, proven property rather than an
  omission, and refuse the only mechanism by which a legacy client could have paid.
- Demonstrate on the boundary a third worked transaction of a category the first two
  do not cover: **one that moves no stored resource at all**.

**Non-Goals**

- No change to `apps/compat-api/**`; it stays the oracle.
- No re-specification of `godot-damage`'s delivered v0 client surface.
- No SQL / PostgreSQL / Alembic (line 1's D4 defers them).
- No conversion of any other route; no adoption of v1 in gameplay.
- No claim about Flash client behaviour.
- No derived effect magnitude, no damage, no combat resolution.

## Established vs Derived

The boundary capability requires every v1 claim to be labelled. This line's split:

**ESTABLISHED** — observed in committed legacy source or in executed-legacy
evidence:

- Both branches' arithmetic verbatim, and that both arms **increase**.
- The cap literal `50` at `command.py:658` and `:670`, and that it bounds the
  **increment**.
- The identity being unvalidated and keyed by `str(magic_id)`, and a float identity
  producing a distinct key.
- The absent-key arm writing `0`.
- The committed id space `1..10`, `legacy_id` being its string form, and all five
  corpus keys resolving against it.
- **No resource moves**, across twelve executed transactions including a `use` with
  mana steady at 15.
- The ledger having **zero readers** and the committed table having **zero**
  consumers: `get_game_config.py` contains **0** occurrences of `magics`.
- Mana's only legacy writer being `engine.py:268`, inside the client-sent eight-slot
  vector applied at `command.py:40`.

**DERIVED** — chosen by this design, never observed from the Flash client. Each
carries its rejected alternative below.

- D1 the operation vocabulary in the request body.
- D2 **the refusal to derive a price** (the *refusal* is derived; the absence of any
  charge is established).
- D3 the committed `id` column as the validating key.
- D4 the counter as "read, derived-written, never interpreted".
- D5 `level` as content rather than a gate.
- D6 the bound, and the refusal of a counter already above it.
- D7 the two operations being one transition.
- D8 the refusal vocabulary.
- D9 the proof shape.

**One thing this line establishes that no earlier line did:** that the *absence* of
a price is itself the authority decision here. D2 turns "no price is charged" from
an observation about v0's implementation into a **specified boundary property with a
proof half that a charge would fail.**

## Decisions

### D1 — One route, `POST /v1/magic`, with a closed two-operation vocabulary in the body

The request is `{player_id, magic_id, operation}`, `operation` a **required string**
whose only legal values are `buy` and `use` — the two literals v0's own
`magic_envelope.ACTIONS` uses. Any other value is a structural input error.

The vocabulary is v0's, **not** `command.py`'s, and that is deliberate: line 2
recorded that naming a route after a legacy command would make v1's vocabulary a
subset of `command.py`'s 63 branch names, which is the inheritance the boundary
exists to stop.

**Rejected alternative:** two routes, `POST /v1/magic/buy` and
`POST /v1/magic/use`, with the operation taken from the path. Rejected because the
line's central finding is that the two arms **are one operation** (D7), and two
independent resources would hide that pairing behind two files, two `ROUTES` rows,
two `KNOWN_ROUTE_PATHS` entries and two client result types — for zero authority
gain, since the transition is the same object under a different operator.

**Rejected alternative:** a single operation with no `operation` field. Rejected
because the v0 surface has two request shapes and a migrating client must be able to
send what it sent; converting a migration into a translation is a cost this line
does not need to pay. The alias is documented instead of hidden (D7).

### D2 — No price is charged, and the committed numeric columns are reported verbatim and never read to compute a debit

This is the decision the selection record most expected to go the other way, and the
measurement is why it goes this way. Six inputs:

1. **No field is named a price.** Four numeric columns, no disambiguator. Compare
   `collections.json`, whose `cashPrice` is named a price and sits beside `prize` —
   that is why line 2 could derive a price and this line cannot.
2. **Twelve executed transactions moved zero of eight resource slots**, mana steady
   at 15 across a `use_magic`. A charge is not a thing the preserved server did.
3. **The ledger has zero readers and the table has zero consumers**, so nothing
   anywhere ties `gold`, `cash` or `mana` to this operation. The linkage is
   *name-only*, which `docs/legacy-m13-unrouted-branches.md`'s own §7.2 reasoning
   already rejected as a basis for a derivation on `win_daily_bonus`.
4. **The fresh corpus can afford nothing** on any column (gold 2000 < 10000,
   cash 5 < 30, mana 0 < 8), so any charge would leave `/v1/magic` with **no
   exercisable success path** on the committed live corpus.
5. **Mana has exactly one legacy writer and it is the client** (`engine.py:268`
   inside the vector applied at `command.py:40`). Charging mana would make v1 the
   first thing in the repository to move it, from a column whose meaning is
   unestablished.
6. **`use_magic` never reads mana** and `buy_mana_new` (`command.py:649-651`) is a
   bare `print`, so there is no committed statement anywhere of what mana buys.

The columns are still **reported verbatim** in the success payload, because content
that cannot be consumed should be visible rather than silently dropped — the same
posture `godot-damage` took.

**Rejected alternative:** charge the committed `gold`. Rejected: it is the most
expensive column (cheapest 10000), so it refuses the fresh corpus 10 of 10; it
would make the route's success unreachable in the committed live phase; and nothing
distinguishes it from `cash` or `mana`.

**Rejected alternative:** charge the committed `mana`. Rejected: it is the column
whose *name* matches a stored resource and whose meaning is least established; the
only measured writer is the client; and the fixture recorded mana **not** moving
across a `use_magic`, which is the single most direct contradiction available.

**Rejected alternative:** charge `cash`. Rejected: `cashPrice` in line 2 was named a
price and sat beside the granted object; here `cash` sits beside `gold` and `mana`
with nothing to disambiguate.

**Rejected alternative:** charge all three as a composite. Rejected: a composite
nobody observed is three inventions stacked, and it would refuse the fresh corpus on
the gold column anyway.

### D3 — The validated key is the committed `id`, and the "index base" question is dissolved rather than answered

The preserved branches **never index the committed table** — they use the client's
value as a dictionary key and never consult `magics.json`. So there is no legacy
index base to reproduce, and the honest framing is that the question is not "which
position does this id name" but "**which committed row is this id**". The answer is
the `id` column, and `legacy_id` is its string form, so the ledger's `str(magic_id)`
key space and the committed id space coincide.

Both candidate readings were checked against the corpus rather than argued:

- **Zero-based (position) is falsified.** `villages/Neutral.json` records ledger key
  `"10"`, which is out of range for a ten-row zero-based table, and **4 of that
  document's 5 keys would retarget to different spells** under that reading.
- **One-based (`id`) is supported** by `id == position + 1` on all ten rows with no
  gaps, and by all five corpus keys resolving.

**Rejected alternative:** adopt the one-based positional index explicitly, as the
archived `levels` curve line did. Rejected because it would encode an index base
into the design for a table the legacy server never indexes, inviting the next
reader to ask why the position mattered. Naming the `id` column instead states what
is actually true and is not re-litigable by the next corpus that lands.

### D4 — `privateState["magics"]` is read as an id-keyed counter map, written only under a derived value, and never interpreted

Read: to obtain the addressed key's recorded prior value. Written: only with a value
v1 derived itself. Never used for anything else — not to gate an operation, not to
decide eligibility, not to answer "does the player own this spell".

The last one matters. "Charges" is a **derived reading**, and this line's own
measurement is what makes it visibly so: both arms **increase**, nothing ever
decreases, and no branch reads the map. v1 therefore calls it a **counter** in
every identifier, field name and refusal message, and never a charge, a spell count,
or an ownership flag.

**Rejected alternative:** refuse any operation on an identity the player has no
counter for, i.e. treat "owns none" as "may not buy". Rejected: it is a rule the
preserved server has no statement of, and it would leave the fresh corpus — whose
ledger is `{}` — with **no** exercisable success on either operation, which is the
outcome D2's fourth input already rules out for a charge. An absent counter reads
as zero and the derived transition applies.

**Rejected alternative:** decrement on `use`. Rejected outright: the preserved
`use_magic` **increases**, and inventing a decrement would be inventing the game's
economy.

### D5 — The committed `level` column is content, never a gate

`level` is a required level, by name and by distribution (9 distinct values spanning
35..55 against a corpus whose levels run 1..67). It is nevertheless **not enforced**:

- **0 of 33 documents at level 1 reach any magic**, so a gate makes the route
  unexercisable on the committed live corpus — the same "no success path" outcome
  D2 rejects for a charge.
- **`min_level` has zero occurrences** across all eleven legacy modules, so no
  established gate spelling exists to reproduce.
- **No legacy comparison of a player's level against any content `level` exists.**
  `level` appears in legacy source only as a client write (`command.py:84`), inside
  `add_xp_unit` (`command.py:325-341`), in display (`sessions.py:146-215`), in
  `get_xp_from_level` (`get_game_config.py:100-101`), and in `auctions.py`.

`level` is reported verbatim in the payload beside the player's recorded level, so a
client can see both and disagree with them, which is the disagreement-reporting
posture `godot-building-xp` established for the level curve.

**Rejected alternative:** enforce `player level >= committed level`. Rejected for
the reach above, and recorded here as a **deferred authority gap** with its
condition: the gate becomes enforceable the moment evidence identifies the magic
table as a purchase-price table rather than a reference table, which is the same
unknown that D2 turns on.

### D6 — The cap is the recorded literal `50`, applied as a bound, and a counter already above it is refused

The cap is the literal in the preserved source at `command.py:658` and `:670`, with
no reference to any content beside it. v1 applies it as the **upper bound on the
counter**, carrying forward `godot-damage`'s decision to use the literal and retain
the rejected content derivation explicitly.

Both preserved asymmetries are refused: the counter does not grow without bound, and
an operation never reduces an existing counter. A recorded counter **already above**
the cap is **refused** with `counter_above_cap` rather than clamped — clamping with
`min(cap, before + 1)` returns the cap, which *is* the charge-destroying decrease
wearing v1's own clothes, and leaving it alone would answer success for an operation
that changed nothing.

**Rejected alternative:** derive the cap from committed content. Rejected: the
preserved source applies the literal with no content reference, and the coincidence
that the same value occurs among the committed `level`/`mana` columns is a property
of the value distribution, not a provenance.

**Rejected alternative:** reproduce `buy_magic`'s unbounded climb for parity.
Rejected: it is unbounded, and an unbounded purchase counter is an authority hole,
not a compatibility detail.

**Rejected alternative:** reproduce `use_magic`'s assignment so a counter above the
cap becomes the cap. Rejected: it destroys owned state on a command whose own
recorded message claims the opposite.

### D7 — Both operations are the same bounded increment, and the alias is stated

The two preserved arms differ in exactly one token, and the difference is **two
defects**: unbounded growth (`+=`) versus cap-crossing reduction (`=`). Remove both
defects and the arms are identical. v1 therefore implements **one** bounded
transition and accepts both operation names for it.

The response reports the operation requested, the derived before and after values,
and a statement of whether the preserved branch would have written the same number —
which for `buy` it never does (it is unbounded) and for an absent counter it does not
either (it writes `0`). Those are **divergences**, recorded once, never presented as
parity.

**Rejected alternative:** invent a distinction, e.g. `buy` bounded and `use`
decrementing. Rejected: a decrement is invented (D4), and any other distinction would
be a rule the preserved source does not have.

### D8 — Three refusals resolve before any write; the vocabulary is extended by exactly **two** codes, and a third was rejected by a measured guard

New codes, in `server_v1_refusals.py` only:

| Code | Status | Meaning |
| --- | --- | --- |
| `unknown_magic_id` | 409 | the integer names no committed magic row |
| `counter_above_cap` | 409 | the addressed counter is already greater than the recorded cap |

Reused codes: `malformed_request` (400) for a non-integer `magic_id`, a missing
field, or an `operation` outside the closed two-value set; `client_supplied_delta`
(400); `unknown_request_field` (400); `unknown_player` (404); `unreadable_state`
(500) for a ledger that is absent or is not an object.

**Why the identity code is not a third new code.** A non-canonical identity — the
float `1.0` or the string `"1"` that the fixture recorded — is a **JSON type error
on the request's addressing field**, and `server_v1_intent.parse_intent` already
refuses a wrongly-typed addressing value with `malformed_request` (its
`NON_NEGATIVE_ADDRESSING` / `isinstance` checks). A third code would duplicate that
check inside the domain, and the intent module's own docstring records that reaching
into the refusal vocabulary from a route is exactly what design D2 forbids.

**The measured consequence.** `apps/server-v1/tests/test_boundary_invariant.py:392`
asserts `self.assertLess(len(list(RefusalCode)), 20)`, and the table holds **17**.
Three new codes make it exactly 20 and **fail**. Two make it 19 and pass
**unchanged**. The guard therefore stays as line 1 wrote it, and this line records —
rather than amends — that it is now **one code from a trip**, with the amendment
path named.

**Every refusal resolves before any write**, so a refused request leaves the whole
document byte-identical, including the ledger. The preserved server's ordering cannot
be reproduced because it performs no validation at all.

### D9 — The post-execution proof is two-part, and only its second half is evidential

1. **The addressed ledger key equals the derived transition**, every unaddressed key
   is byte-identical and keeps its recorded position, and **exactly one** document
   leaf path changed.
2. **Every one of the seven stored resources v1 knows about is byte-identical**
   across the request.

**Why this is not tautological, stated precisely.** Half 1 is a *specification*
check, not an evidence claim: v1 is the only implementation writing the save on this
path, so comparing v1's written value to v1's derived value could not fail for any
interesting reason, and half 1 is presented as such rather than dressed as parity
with the preserved branch — which is not executed here and which v1 diverges from by
design on every `buy` and every absent key.

Half 2 is the falsifiable half, and it is falsifiable **because of D2**: the
alternative designs this line rejected — charge `gold`, charge `cash`, charge
`mana` — each move exactly one of the seven slots, and the fixture measured that the
preserved server moved none of eight across twelve executed transactions. A charge
of any size fails half 2. That is the proof doing work.

A **refused** operation leaves the ledger, every other key, and all seven stored
resources byte-identical.

### D10 — `buy_mana_new` is unreachable, and the branch-coverage figures move by exactly two

`/v1/magic`'s `operation` set is closed to `{buy, use}`, so the parked
`buy_mana_new` (`command.py:649-651`, whose entire body is one `print`) has **no**
representable request. That is where the `39`/`24` routed/unrouted split of
`docs/legacy-m13-unrouted-branches.md` stands today; this proposal does **not** edit
that document, which is owned elsewhere, and does not move the split.

It does move the other figure: `buy_magic` and `use_magic` become authoritative, so
**branches without an authoritative v1 route goes 61 → 59**, and the boundary
capability's Purpose restates it. The `61` in `AGENTS.md` and the roadmap is left
alone, for the reason the candidates record itself gives about `AGENTS.md`'s
superseded arithmetic.

### D11 — `apps/compat-api/**` is untouched, and the recorded baseline is re-run rather than assumed

The oracle is not the thing being replaced. This change adds no v0 route and edits
no v0 file, so the Compatibility API suite stays at its recorded **3077** as a
**verified** figure — re-run and reported, exactly as `godot-friends` and
`godot-construction-assist` did, and as this repository has twice had to learn the
hard way.

## Instrument faults in my own measurements

Recorded because a figure that is wrong because of the instrument is worse than no
figure. These are mine, in this session, on top of the selection record's own ten.

1. **My branch-span regex was `[A-Za-z_]+` and measured 62 branches.** The missing
   name was `push_queue_unit2`, whose trailing digit the class could not match. A
   digits-capable class measures **63**, which reproduces `tools/command-catalog`
   and `AGENTS.md`. A census that silently drops a branch whose name ends in a digit
   is not a census. I reproduced the fault deliberately to confirm the count before
   relying on it.
2. **I nearly inherited the selection record's "exact token 10" figure for
   `magics`.** That figure is the selection record's own **fault 6**: its code-only
   lexer deletes string literals, and a Python dict key *is* a string literal, so
   `privateState["magics"]` reads as a bare `privateState` under that rule. The two
   adjacent rows in its table are identical (10 and 10) precisely because one
   inherits the other's instrument. Measured over the raw file the exact-token count
   is **17**. Full census: whole-file **17**, distinct lines **13**, code-only
   **10**, code-distinct lines **8**, quoted `"magics"` **6**, exact token **17** —
   `command.py` 12/8/10/8/2/12 and `version.py` 5/5/0/0/4/5.
3. **`get_game_config.py` contains 0 occurrences of `magics`** — checked directly
   rather than inferred from the total, because the "zero consumers of the committed
   table" claim is load-bearing for D2 and the inference from a total would have been
   the weaker instrument.
4. **I first wrote "the price is derived" in my own summary before measuring
   affordability**, because the selection record says so three times. The affordability
   measurement falsified it. Recorded because the error was inherited from a binding
   document, which is the hardest kind to catch.

## Contradictions with `docs/legacy-m13-line3-candidates.md`

The selection record is the binding document for **which** target, and this
proposal accepts its target without re-ranking. Its **economic** framing does not
survive measurement. Reported rather than quietly adopted:

| # | Record says | Measured | Which is right |
|---|---|---|---|
| 1 | §6.2 row 1: `buy_magic` is "`+=` then clamped `min(50,…)`" | the `min` bounds the **increment**; `buy_magic` is **unbounded** | the measurement |
| 2 | §7.3: the arms "differ by exactly 2 lines — `+=` vs `=`" | the line count is right; the arms are **not near-duplicates in effect** — one is unbounded, one reduces a counter above the cap, and **both increase** | the measurement, on the effect |
| 3 | §5.3 census, "exact token" row: **10** | **17** over the raw file; 10 is the code-only figure | the measurement |
| 4 | §7.1 R1: "`magics.json` carries a complete price vector … this is the same discovery line 2 made with `collections.json`" | `collections.json` has `prize` (one reading) and `cashPrice` (**named** a price, beside `prize`); `magics.json` has **four** unnamed numeric columns and no disambiguator, and 12 executed transactions moved **zero** of eight slots | the measurement; the analogy does not hold, and D2 refuses the price |
| 5 | §7.1 R3 / the shape paragraph: "derive the charge/price from committed `magics.json`" | not derivable by any justifiable rule; the fresh corpus can afford **none** of the ten on **any** column | the measurement; D2 |
| 6 | §7.1 R2: corpus corroboration — the five keys resolve against the committed id space | **confirmed**: `1, 2, 4, 9, 10` all within `1..10` | the record |
| 7 | §9.5: whether the four columns are prices or reference values — **Unknown** | still unknown, and now measured from both sides: nothing names them a price, and the fixture shows no slot moving | unchanged; it is *why* D2 refuses |

**None of these moves the ranking.** `§7.3` already states that no candidate is as
strong as `complete_collection` was, and the target is still the strongest
available. What changes is that the line's **shape** is "a refusal made
specifiable" rather than "a derivation", and the proposal says so rather than
claiming a derivation it cannot justify.

## Risks / Trade-offs

- **D2 is a refusal, so this line delivers less capability than lines 1 and 2.**
  That is stated here rather than in a footnote. Its value is that it is the first
  boundary worked transaction that **moves no stored resource at all**, which is a
  category the boundary's own Requirements never covered.
- **D7's alias could read as a bug.** Two operation names over one transition is
  unusual, so the response states it explicitly and the hermetic suite asserts both
  names produce the same transition.
- **The `level` gate is a real authority gap left open** (D5). It is deferred, not
  denied, and its condition for revisiting is named.
- **`test_boundary_invariant.py:392` is one code from tripping.** Not amended here;
  recorded, with the amendment path named, because the honest fix is a decision
  about the ceiling rather than a bump for one line.
- **Two cross-line guards will go red and must be amended as ownership hand-offs,
  not loosened**: `test_stored_item_placement.gd`'s whole-tree absence check, and
  `test_auction_schedule.gd` / `test_market_trade.gd`'s count pins, currently
  **52 hermetic / 25 live** after line 2. The pins move to **53 / 26**.
- **v1's stored resource set is seven; `godot-damage` compared eight.** v1's seven
  are `maps[0].xp/gold/wood/oil/steel`, `playerInfo.cash`, `privateState.mana`;
  `privateState.energy` is absent because the eight-slot vector's eighth target is
  read into `unknown` and never written. Recorded as a measured difference between
  two layers, not papered over.

## Migration Plan

1. Extend `server_v1_refusals.py` with the two new codes, their statuses, purposes
   and v0 equivalents (D8). The `< 20` guard must pass unchanged.
2. Extend `server_v1_intent.py`: one schema row for `magic`, one addressing-field
   row, and the closed `operation` value set. No new machinery beyond the
   declaration style already used.
3. Implement `server_v1_magic.py`: identity lookup against the committed table
   through the existing content registry (**do not transcribe** any committed
   value), ledger read, bounded derivation, all three refusals before any write.
4. Register `POST /v1/magic` in `server_v1_app.py` with no arithmetic, no refusal
   vocabulary and no domain value construction.
5. Client: `ServerV1Api` facade forwarder plus a typed result module, in the exact
   shape lines 1 and 2 established.
6. Hermetic suite over the client facade, re-deriving every committed-table figure
   from the committed package on each run.
7. Live phase `magic-live-v1`: two operations against a disposable corpus on
   loopback, **no seeding** — the fresh corpus's `{}` ledger is already exercisable,
   and seeding money would weaken nothing but would make the only mutation less
   legible. Assert the save mutated on each operation, and that all seven stored
   resources are unchanged across both.

## Corrections (recorded during Apply, 2026-10-13)

Three items, corrected **here** rather than in place, as task 10.4 directs. The first
two were reported by the implementation subagent and **independently re-verified**
against `packages/game-content/normalized/magics.json` before being recorded here -
the table is 10 rows and 15 columns, of which **six** are numeric. The third is a
boundary the task set left unfixed and the implementation had to settle on evidence.

### C1 - The committed table carries **six** numeric columns, not four

**Wrong.** D2's evidence item 1 ("Four numeric columns, no disambiguator") and the
row-7 contradiction-table entry ("`magics.json` has **four** unnamed numeric
columns").

**Measured.** The six numeric columns are `id`, `mana`, `level`, `gold`, `cash` and
`target`. `id` and `target` are numbers too, so "four" undercounts the surface the
refusal has to hold against.

**The decision is unchanged, and in fact slightly stronger.** The four columns a
price could plausibly be read from are the four naming a *resource or a level* -
`gold`, `cash`, `mana`, `level` - and **no** column at all, numeric or otherwise, is
named a price. That is the claim D2 makes, and it holds over six columns as well as
four. The delivered suite carries the two lists separately (`NUMERIC_COLUMNS` = 6,
`PRICE_CANDIDATE_COLUMNS` = 4) precisely so the counts cannot be confused again.

### C2 - D6's cap rejection cited one column that does not contain the value

**Wrong.** D6's "Rejected alternative: derive the cap from committed content", which
cites "the same value occurs among the committed `level`/`mana` columns".

**Measured.** `50` occurs in exactly two committed cells - magic `id` 5
(`Shortcircuit Inductor`) `level` = 50, and magic `id` 1 (`AirStrike`) `cash` = 50. It
does **not** occur in `mana` at all, whose six distinct values span 8..20. So `level`
is right and `mana` is wrong.

**The rejection stands and its reasoning is unaffected.** The preserved source applies
the literal `50` with no content reference, so a matching value elsewhere in the table
is a property of the value distribution rather than a provenance. Naming `mana` was an
error in the illustration, not in the argument.

### C3 - D6's cap boundary was left unfixed by the task set, and is settled here

**Gap.** D6 fixes the cap value (`50`) and the refusal for a counter already above it,
but never fixes what happens **at** exactly the cap.

**Settled as accept-at-cap (option B), on evidence rather than preference.** `before
== 50` succeeds as a recorded no-op; `before == 51` is refused `counter_above_cap`.
The measured basis is that the preserved `use_magic` arm is *itself* a no-op at exactly
50, because `min(50, 51) == 50`. The third option - refuse at the cap - would have
refused a transaction the preserved branch performs.

**Recorded here because this is a design boundary, not a task detail.** The task
record carries the same decision at `tasks.md` 3.3 and 10.5; the two agree.

### Checked and found sound

The line attribution task 10.4 also asks for is **correct** as recorded above:
`buy_magic` is `command.py:652`-`:662` and `use_magic` `command.py:664`-`:674`.

## Open Questions

- **Q1.** Is a counter a charge at all? Both arms increase and nothing consumes, so
  "charges" is a derived reading and v1 names it a counter. **Unknown**, and
  deliberately not resolved by naming.
- **Q2.** What is `mana` spent on? `use_magic` never reads it; `buy_mana_new` is a
  `print`. **Unknown**, and unanswerable from this table.
- **Q3.** What does `50` mean — lifetime charges, or a display cap? **Unknown**;
  v1 applies it as a recorded bound, which is true under either reading.
- **Q4.** Should the `level` gate be enforced? Deferred with its condition (D5).
- **Q5.** Are `gold`, `cash` and `mana` three prices, one price in three currencies,
  or reference values? **Unknown**, and the reason D2 refuses rather than guesses.
- **Q6.** Is `area`'s string-to-list coercion semantically meaningful? **Unknown**;
  reported verbatim as normalized and never read.
- **Q7.** What did the Flash client display, and did it show a price? **Unknown,
  and permanently so** — this line reads the server and the committed content only.
