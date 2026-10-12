# Server v1 collect: established behaviour vs derived authority

Milestone M13's first slice delivers `POST /v1/collect`. This record states, per
rule, which parts of that slice are **established** from committed legacy source
and executed-legacy evidence, and which are **derived** by this design and were
never observed. For every derived rule the rejected alternative is named.

The normative source for all of this is the code, not this document:
`apps/server-v1/server_v1_economy.py` carries the same classification in its
module docstring, `apps/server-v1/server_v1_refusals.py` the closed vocabulary,
and `apps/server-v1/tests/` the assertions. Where this document and the code
disagree, the code is right and this document is a defect.

## The oracle

One executed-legacy transaction, captured once and committed:

- fixture: `tests/fixtures/godot-building-collect/`
- command: `collect` against the committed Tree, item `905`, at map key `2`
- recorded request vector: `[0, 3, 0, 60, 0, 0, 0, 0]`, capture instant `ts`
  `1790705901`
- recorded row before: `[905, 53, 39, 0, 0, [], {}, 1]`
- recorded row after: `[905, 53, 39, 1790705901, 0, [], {}, 1]`
- recorded balance change: `xp 4 -> 7`, `wood 2000 -> 2060`, all five other
  stored resources byte-identical
- recorded response body: `{"result":"success"}`

`apps/server-v1/tests/test_parity_v0_collect.py` compares against those
**captured bytes**. It does not re-capture from the legacy server, so the
comparison cannot be invalidated by a legacy server that has since changed.

## ESTABLISHED

Each of these is present in committed legacy source or in the captured fixture.

1. **The income fields exist and are string-encoded.** `collect "20"`,
   `collect_type "w"`, `collect_xp "1"`, `max_collects "0"` for item `905`. The
   derivation reads them through the content loader's coercion, never as raw
   text.
2. **The ladder globals are committed and parallel.** `COLLECT_MINUTES
   [5, 60, 240, 480]` and `COLLECT_MULTIPLIER [0.25, 1, 2, 3]`, four entries
   each.
3. **`COLLECT_MINUTES` is in minutes; both recorded instants are in Unix
   seconds.** The conversion is the single constant
   `SECONDS_PER_COMMITTED_MINUTE`, and `tests/test_economy.py` asserts every
   rung boundary from both sides (299/300, 3599/3600, 14399/14400,
   28799/28800).
4. **Slot 3 of a map row is the collection instant.** It moved from `0` to the
   capture instant and nothing else in the row changed.
5. **A recorded instant of `0` means "never collected"**, which is why the
   captured row had unbounded elapsed time and therefore landed on the top rung
   deterministically.
6. **The seven stored resource paths**, already established by
   `engine.apply_resources` (`engine.py:251-271`) and re-read here through the
   repository seam.
7. **v0's collect route answers `{"result":"success"}`** and nothing else. The
   captured `response.body` is `b'{"result":"success"}\r\n'`. v1 does **not**
   reproduce that body; it reports its derivation. That difference is a
   deliberate divergence, not parity.
8. **The legacy server answers success unconditionally and applies a
   client-sent resource vector before dispatch** (`command.py:40`, unconditional
   `apply_resources`; `server.py:318-322`). This is the fact the whole slice
   exists to refuse, and it is why a client-supplied delta in v1 is a `400`
   rather than an applied value.

## DERIVED

Each is a rule this design introduced. None was observed. The rejected
alternative is named because a rule without its rejected alternative is not
reproducible by a later reader, only re-guessed.

| # | Derived rule | Rejected alternative |
| --- | --- | --- |
| D1 | The rung is the **highest committed threshold** the elapsed time has reached, clamped at the top rung | Interpolating past the last rung, which would make the top multiplier unbounded |
| D2 | The multiplier **scales** the income amount | A flat payout, which would leave `COLLECT_MULTIPLIER` as dead content — the two arrays are parallel and four long, so a rule ignoring the second would have no effect at all |
| D3 | The **same** rung scales `collect_xp` | A flat `collect_xp`, which would leave the payout's two halves inconsistent |
| D4 | Below the first committed rung, **nothing** is derived (`below_first_rung`) | Paying a fraction of the first rung's `0.25`, which would invent an amount no committed threshold authorises |
| D5 | `collect_type` is a **closed** vocabulary mapping to v1's stored resource names | Inventing a mana mapping for a content value no item records; the census is measured over the 900 loaded items as `g` 853, `w` 23, `o` 11, `s` 11, `c` 2 — five distinct values and no sixth, so the five-entry map is exactly the committed set |
| D6 | A non-zero `max_collects` is **refused**, not interpreted (`capped_collection`) | Reading it as a per-collection limit, or ignoring it; measured over the same 900 items the values are `"0"` on 889, `"25"` on 9 and `"100"` on 2, and nothing in the repository says which of three plausible readings is meant |
| D7 | A recorded instant in the **future** is refused, not clamped (`unreadable_state`) | Clamping to zero, which would pay a full-payout-equivalent derivation for a row that has not elapsed |
| D8 | The minutes/seconds conversion happens through **one named constant** | Converting inline at each comparison, which is how the two units get mixed |
| D9 | Structural input errors are `400`, gameplay refusals `409`, an unknown player `404` | One status for every outcome, which is how v0 grew 24 routes to answer one question; v1's transport names no refusal code and reads every status out of the closed table |
| D10 | The refusal vocabulary is a **fresh small set**, not a subset of v0's 104 constants | Reusing v0's constants, which would import v0's vocabulary into the authority boundary; v0's mapping table exists in `apps/compat-api/` as documentation and is never imported |

D1 deserves its own note: **no legacy branch reads either ladder global**, so
nothing about a ladder was ever observed in execution. The committed fixture
shows exactly one transaction, at the top rung, from an unbounded elapsed time.
A rule that fitted that single data point equally well and was rejected anyway
is D4 (paying `0.25` of the base below the first rung).

## Claim limits

- The claim is that a payout **grows in four committed rungs** derived from an
  item's committed income fields. It is **never** a claim about any specific
  amount the legacy client paid — the legacy client paid whatever it sent, and
  the server applied it.
- **No price, cost, or fee is charged** and **no stored resource moves** outside
  the derived payout.
- **`mana` can never be paid by this derivation** — the save has the slot and no
  committed item records a mana collect type.
- **No cap semantics are implemented.** A non-zero cap is refused (D6), so the
  committed `"25"` and `"100"` values are unreachable rather than honoured.
- **No collection eligibility is checked against anything but the row's own
  recorded state.** There is no level gate, no quest tie-in, and no
  permission check, because the legacy server has none to reproduce.
- **A collection on a row under construction is refused in both layers** (the
  client offers no action and the service fails closed). The legacy client's own
  behaviour there is unobserved.
- **Parity covers one recorded transaction** against the fresh-player corpus
  only. No progressed-player save exists, and no other collectable row in the
  corpus has been compared.
- **The save shape is not migrated.** v1 reads and writes the committed save
  document through a repository seam; SQLAlchemy and Alembic are deferred to
  M14 by design D4.
- **This slice says nothing about the other 39 uncited legacy command branches.**
  `tools/route-coverage/` reports 24 of 63 branches covered by a v0 route and
  39 uncovered; this line covers exactly one of the 24.

## A correction recorded against this document's own first draft

Two figures in the **ESTABLISHED/DERIVED** tables above were inherited from
`server_v1_economy.py`'s module docstring rather than measured, and both were
**wrong**. They are corrected here and in the code:

| Figure | Inherited | Measured | Cause |
| --- | --- | --- | --- |
| `collect_type` census | `g` 731 over "778 stored items" | `g` **853** over **900** loaded items | The four minority counts were right and the majority was not, so the figure had been carried over from a differently-scoped count rather than counted |
| `max_collects` census | `"0"` for 767 of 778 | `"0"` on **889** of 900, `"25"` on 9, `"100"` on 2 | Same cause |

Neither correction changes a conclusion. The five-entry `collect_type` map is
still exactly the committed set, and a non-zero `max_collects` is still refused
rather than interpreted.

**One measurement strengthens D5 and D6 and is worth stating separately:**
`COLLECT_MINUTES`, `COLLECT_MULTIPLIER`, `collect_type` and `max_collects`
together have **zero** occurrences across all seven legacy root modules
(`command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`,
`get_game_config.py`, `version.py`). So all four committed fields this slice
derives from have no legacy consumer at all: the legacy server never read a
ladder, never read a collect type, and never read a cap. That is why D1 through
D6 are derived rather than established, and it is measured rather than
inherited.
