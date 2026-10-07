# Design — market / trade counters

Binding investigation: `docs/legacy-m11-special-mechanics.md` (PR #337, merged `1c8786b`).

Every line number, count, and value below was measured against the repository at
`1c8786b`. Where a figure was inherited from a prior record it is marked, and where a prior
record was wrong it is corrected here rather than quietly adopted.

---

## D1 — No route, and no `apps/compat-api/**` change

**Decision.** The projection is pure and read-only. No endpoint is added; the compatibility
API is not touched at all.

**Why.** The two counters have **opposite** shapes, and only one of them has a consumer:

| field | live writers | live readers | consumer? |
|---|---|---|---|
| `numTradesDone` | `command.py:470`, `engine.py:240` | `command.py:469` — **its own increment** | **no** |
| `timestampLastTrade` | `command.py:471`, `command.py:913` | `engine.py:238` | **yes** |

So there is no server-side rule to expose and nothing for a client to act on. The one real
consumer — the day-bucket reset — **already runs** on every player-info load inside
`engine.reset_stuff`, called from `get_player_info.py`. Adding a route would be a client
affordance for a transaction that grants nothing, which is the surface the
`social-rewards-assist-projection` line refused by the same reasoning (its design D1).

**Rejected alternative.** A `/v0/trade` route that increments server-side. Rejected because
the increment is the *only* thing the branch does and there is nothing to authorise it
against; a route would imply a limit that no legacy code enforces.

---

## D2 — The cap comes from the branch literal, never from `MARKET_MAX_NUM_TRADES`

**Decision.** One named constant, `TRADE_CAP_FROM_BRANCH := 20`, documented as read from
`command.py:470`.

**Why.** `MARKET_MAX_NUM_TRADES` is committed with the value **20** and has **zero**
consumers — raw 0 and quoted 0 across all eleven modules. The equality is a **coincidence**
and is recorded as one. This is the same treatment the project already gives the magic cap
`50`: a number appearing in both an unread committed constant and a branch literal is two
facts, not a derivation.

**Rejected alternative.** Deriving the cap from the normalized `globals.json` row, on the
reasoning that content is the better source. Rejected: it would make an unread constant
load-bearing, which is precisely the invention the milestone's precedents forbid. The claim
this line can make is *"this is the value the branch stores"*, never *"this is the limit a
player faced"*.

---

## D3 — The unclamped print is reproduced as a reported field

**Decision.** The projection reports **two** numbers and labels them: the stored count
(`min(20, …)`) and the branch's remaining-trades value computed from the **unclamped**
increment, exactly as `command.py:473` prints it.

**Why.** The two disagree from the 21st trade onward:

| incoming | stored | branch's printed "remaining" |
|---|---|---|
| 19 | 19 | 1 |
| 20 | 20 | 0 |
| 21 | 20 | **−1** |
| 25 | 20 | **−5** |

Correcting this would be a behaviour change this contract does not make. Reproducing it as a
*named, labelled* field is strictly better than reproducing it silently: a future
implementer sees the defect as a property of the oracle instead of rediscovering it.

**Note.** The suite must assert the module contains **no clamping** of the reported remaining
value, so the defect cannot be "helpfully" fixed.

---

## D4 — The reset predicate is reported; `reset_stuff` is referenced, not reimplemented

**Decision.** The projection evaluates `now // 86400 != last_trade // 86400` and reports the
result together with both buckets. It performs no reset and calls no engine helper.

**Why.** `engine.py:230-249` belongs to the engine and already runs on the load path.
Duplicating it would create two sources of truth for a day boundary. This mirrors how
`godot-unit-behaviors` **references** `clicks_to_build`'s consumer rather than
reimplementing it.

**The correction this rests on.** `docs/legacy-unit-movement.md` records `fast_forward` as
having no observable effect "precisely because nothing evaluates elapsed time". **That is
false** — `reset_stuff` does, and this is why the correction matters to a deliver line
rather than only to a record. See design D7.

---

## D5 — The committed schedule is reported, and nothing is derived from it

**Decision.** All eight `MARKET_*` values are projected verbatim with their measured
zero-consumer status. No price, cap, period, increment bound, or percentage is computed.

| key | value | raw | quoted |
|---|---|---|---|
| `MARKET_AMOUNT_TRADE` | `[100, 200, 300]` | 0 | 0 |
| `MARKET_BASE_COSTS` | `{"o": 100, "s": 150, "w": 100}` | 0 | 0 |
| `MARKET_INCREMENT` | `0.02` | 0 | 0 |
| `MARKET_MAX_DECREMENTS` | `25` | 0 | 0 |
| `MARKET_MAX_INCREMENTS` | `200` | 0 | 0 |
| `MARKET_MAX_NUM_TRADES` | `20` | 0 | 0 |
| `MARKET_PERIOD_HOURS` | `20` | 0 | 0 |
| `MARKET_SELL_PERCENTAGE` | `0.75` | 0 | 0 |

They are read through the **existing normalized registry**, never transcribed. The suite
re-measures the zero-consumer count **every run** over all eleven modules using the raw
quoted-access pass, so the claim cannot rot if a legacy file is edited.

---

## D6 — Two divergences recorded, neither reproduced as parity

### D6.1 — Resource movement is client-sent, and `trade_resource` moves nothing

Both arguments of `trade_resource` are dead: `resource_type` is read once at
`command.py:466` and never used; `sold` is read once at `:467` and never used. **No resource
moves.** Any movement would arrive through `engine.apply_resources` (`engine.py:251-271`),
applied at `command.py:40` — **before** the dispatcher chain opens at `command.py:42`.

This is the `AGENTS.md` "Bad" pattern verbatim: the client dictates the outcome. The delivered
client therefore **moves no resource and sends no resource vector**, and the divergence is
recorded rather than reproduced.

### D6.2 — The instant is client-writable

`fast_forward` (`command.py:905-947`) sets

```
 913|     map["timestampLastTrade"] = max(0, map["timestampLastTrade"] - seconds)
```

with `seconds = args[0]` — a **client-supplied** integer. A client can therefore walk the
instant backward across a `// 86400` boundary and clear the trade count. This is a real,
reachable state change and it is a **divergence**, not parity. No fast-forward operation is
delivered.

---

## D7 — What the corpus can and cannot witness

This is the decision that shapes every claim limit, and it is **not** a missing-corpus-row
limitation — it is a property of the corpus.

**Measured:** **8 of 10** committed save documents record `timestampLastTrade == 0`. For each
of those, `0 // 86400 == 0` while any real `now` is in a far later bucket, so the predicate at
`engine.py:239` is **unconditionally true** and `numTradesDone` is cleared on **every load**.

| document | `numTradesDone` | `timestampLastTrade` | bucket |
|---|---|---|---|
| `fresh-player.json` | 0 | 0 | 0 |
| `fresh-player-pre-migration.json` | 0 | 0 | 0 |
| `AcidCaos.json` | 0 | 0 | 0 |
| `General_Mike_30.json` | 0 | 0 | 0 |
| `General_Mike_31.json` | 0 | 0 | 0 |
| `Kiriakos.json` | 0 | 0 | 0 |
| `Scarlet.json` | 0 | 0 | 0 |
| `initial.json` | 0 | 0 | 0 |
| **`Nerri.json`** | **20** | 1705776695 | 19742 |
| **`Neutral.json`** | 0 | 1683054101 | 19479 |

**Consequences, each of which is a refusal rather than an omission:**

1. An executed-legacy fixture on the fixture corpus could show the increment (`0 → 1`) but
   **cannot** show the cap binding or the reset changing a non-zero count.
2. **No fixture is captured.** Two options were considered and both are worse than none: a
   fixture that shows `0 → 1` followed by a reset to `0` on the next load would license a
   round trip this change explicitly refuses to deliver (D1), which is the same reasoning that
   removed the `construction-assist` fixture.
3. **Demonstrating accumulation requires `Nerri.json`**, the only document that reached the
   cap — and that is **one** data point, not a parity claim.

### The `Neutral.json` proof, and why it is a proof

`Neutral.json` records a non-zero instant with a cleared count. That is only evidence the
reset fired **if** the instant proves a trade occurred — so the exclusivity of the raising
writer was established rather than assumed:

* live writers of `timestampLastTrade`: `command.py:471` (`= time_now`) and `command.py:913`
  (`max(0, … - seconds)`).
* `:913` **subtracts a client-supplied** quantity and **floors at 0**, so from the
  fresh-player's `0` it can only ever produce `0`. It cannot manufacture a non-zero instant.
* therefore `command.py:471` is the **only** site that can raise it, so a non-zero instant
  implies a trade ran, the count reached ≥ 1, and the only writer that can then set it to `0`
  is `engine.py:240`.

The same proof shape as the atom-fusion `ts: 0` attribution: derived from the writer set, not
read off one row.

---

## D8 — Ownership boundaries

| surface | owner | this line's stance |
|---|---|---|
| `soulmixer_speedup`, the `nu`/`ts`/`ui` queue | `godot-unit-queues` | **referenced, not reimplemented.** The rank-#1 displacement in the investigation is the reason. |
| `numTradesDone`, `timestampLastTrade` | **this line** | new |
| `MARKET_*` committed rows | `globals-tuning-normalization` (as content) | read **through** the registry; not transcribed |
| `weekly_reward`, `win_daily_bonus`, `bonusNextId`, `timestampLastBonus` | `godot-rewards` | **not touched** |
| `timeStampDartsReset`, `timeStampDartsNewFree` | `godot-darts` | **not touched.** The commented `fast_forward` write at `command.py:917` is recorded in the investigation as a *branch* fact only; both fields have **5** live sites elsewhere |
| `first_time_marketplace`, `marketPlaceFirstTime` | **unowned**, 2-statement branch | **not delivered here.** Recorded as census candidate #3; too small to carry a milestone, and adjacent to `godot-auction-schedule` |
| `rt_open_graph_unit`, `crossPromotionsFinished`, `unlockedSkins` | **unowned** | **not delivered here.** Recorded as candidate #4; `[]` and `None` in 9 of 9 documents, so no corpus evidence either way |
| `SPELL_*`, `TECH_*` | **unowned**, 24 declarations | **not delivered here.** Recorded as candidate #5 and as a coverage gap beside `godot-mission-vocabulary` |

The suite asserts these owners **exist**, so a boundary cannot rot into an orphan, and asserts
this line's own modules name **none** of the foreign fields.

---

## D9 — Anti-invention guards, proven by injection

Following the established pattern, these are structural and will be **proven by injection
with byte-identical restores**, not trusted:

| guard | rejects |
|---|---|
| whole static-function inventory pin | any new helper, whatever its name |
| reserved-name substring scan (case-folded, **both** directions, over **declared** function names) | a suffixed helper wearing a reserved name as a prefix — the exact miss recorded on the friends line |
| absent-helper set | an invented `trade_cost`, `cap_for`, `enforce_trade_limit`, `is_trade_allowed`, `remaining_trades_clamped` |
| no-clamping assertion (D3) | "fixing" the negative remaining-trades value |
| zero-consumer re-measurement (D5) | a silent legacy edit that gives a `MARKET_*` key a consumer |
| absent-ordinal guard | claiming an ordinal for the zero-consumer count — four conflicting ordinals already exist in the records |
| ownership assertions (D8) | an orphaned boundary or a foreign field leaking into this line |

Each probe's **failure count** is measured, not merely its non-zero exit, and every restore is
verified by sha256 with zero NUL bytes and a final-newline state matching the baseline — the
harness discipline recorded after the CRLF rewrite defect.

---

## D10 — Reserved tokens

The 13 tokens in `test_project_scope.gd`'s `FORBIDDEN` table and the `RUNTIME_NEEDLES` in
`test_town_gate.gd` were checked against this line's vocabulary. **No collision**: the
forbidden set is entirely Flash and transport tokens (`command.php`, `FlashVars`, `AMF`,
`USERID`, `Ruffle`, `ActionScript`, `https://`, …), and the market/trade vocabulary is
`trade`, `market`, `numTradesDone`, `timestampLastTrade`, `MARKET_*`. **No guard is relaxed
and no deliverable is reworded**, because none is needed.

---

## D11 — Deliverable shape

Two read-only modules and one hermetic suite, matching the `social-rewards-assist-projection`
line's shape:

* a counter projection module (typed, read-only, fail-closed on a malformed field, reporting
  both the stored count and the branch's unclamped remaining value);
* a committed-schedule projection module (eight `MARKET_*` rows verbatim, zero-consumer status
  re-measured each run);
* a hermetic suite that also writes the deterministic `market-trade-report-v1` evidence
  report, whose tables are generated from the live modules so they cannot drift from the code
  they document.

Baseline impact on the batteries: **+1 hermetic suite**, **+0 live phases**, and the
`verify-boot.ps1` guard digest must be **identical before and after** — the compat suite stays
at its 3,077-test baseline because `apps/compat-api/**` is not touched.
