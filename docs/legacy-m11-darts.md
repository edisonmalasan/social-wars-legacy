# M11 line 2 — Darts and premium: legacy measurement contract

Companion to `docs/legacy-m11-social.md` (PR #309, merged `0cccdde`). That document
classified M11's six deliver items; this one measures the **one item it classified
as "Partial" with a real undelivered surface**, and records **two corrections to
that document** which this investigation found while doing so.

**This is a measurement document. It creates no OpenSpec change and no
implementation.**

---

## 0. Corrections to `docs/legacy-m11-social.md` §6

Both corrections were found by measurement, and both were caused by the same
instrument fault, which is the standing lesson re-earned a third time in this
milestone: **a counting rule that does not distinguish a comment from code
produces a confident wrong number.**

### C1 — `fast_forward` is **not** a writer of `timeStampDartsReset`

`docs/legacy-m11-social.md` §6 credits `timeStampDartsReset` with writers
`darts_reset, fast_forward` and lists `fast_forward` as touching "two of its
instants".

`command.py:917` is **commented out**:

```python
917:  # privateState["timeStampDartsReset"] = max(0, privateState["timeStampDartsReset"] - seconds) # don't process weekly things
```

A whole-file occurrence count credits that line as a write. Counting only
uncommented occurrences, `timeStampDartsReset` has **5** code sites and `917`
is not among them. `fast_forward` touches exactly **one** darts instant,
`timeStampDartsNewFree` at `:918`.

### C2 — `timeStampDartsReset` has **two** writers the committed table omits

The same table attributes the field only to `darts_reset` and `fast_forward`.
Two further **uncommented** sites exist, in modules §6 does not attribute:

| Site | What it does |
|------|--------------|
| `engine.py:249` | inside `reset_stuff`, sets the field to **`0`** at a week boundary |
| `sessions.py:121` | seeds the field to **`0`** on new-player creation |

`reset_stuff` is the **only time-derived server mutation in this entire
surface**, and §6's shape — three command branches over six fields — omits it
because it is not a command.

**Neither correction changes §7's classification.** `darts` remains "Partial:
real multi-branch state", and the field remains write-ful. What changed is that
the surface is **larger and more interesting** than recorded: one branch is
server-derived, one is a weekly server-side reset, and one field is seeded at
player creation.

### Instrument fault committed by this investigation

The first version of the counting probe here **blanked string literals as well
as comments**, and reported **zero** code-only occurrences of
`dartsBalloonsShot` — a field plainly assigned at `command.py:578`. The cause
is structural: **every persistence field in this codebase is reached through a
dict subscript**, so the field name is *inside* a string. A "code-only" rule
that erases strings is therefore unsound for exactly the class of field this
project counts, and any zero-consumer figure derived from it is worthless.

The corrected probe blanks **comments only** and preserves string contents. A
second version of the probe still got it wrong by preserving the string
*delimiters* while blanking their *contents*, and produced the same false
zero. It is recorded because the failure looks like a finding rather than a
bug: a probe that reports zero everywhere is more alarming, not less.

### The draft's claim about `godot-social-state` was wrong, and reading it refuted it

The first draft of this section asserted a **standing risk** to the delivered
`godot-social-state` census: that its code-only lexer blanks string literals
and therefore cannot see a subscript-keyed field. **That claim is false, and
the suite already handles this hazard explicitly.**

`test_social_state.gd:387` calls `_quoted_count(raw[index], name)` over **RAW**
source, not over the stripped view, and the function's own comment at `:396-397`
says why: *"Counted over RAW source, never over the stripped view, because the
strip erases exactly this form."* `_token_count` at `:386` covers the identifier
form over the stripped view, and `:389` requires **both** to be zero. The two
forms are summed exactly as the earlier `questsRank` correction required.

That refutation raised the **inverse** question, which is worth answering
because raw-source counting can only push fields *out* of the zero group, never
in — and `command.py:917` is precisely such a comment-only occurrence. Measured
over all 11 modules for all 19 delivered social fields:

| Field | raw-quoted | code-only | comment-only |
|---|---|---|---|
| `resourceAlliesMarket` | 1 | 1 | **0** |
| `publishedOpenGraphUnit` | 6 | 6 | **0** |
| `marketPlaceFirstTime` | 1 | 1 | **0** |
| the other 16 | 0 | 0 | **0** |

**No social field has a comment-only occurrence**, so the delivered
zero-occurrence figure of **12** is not inflated by raw-source counting, and the
census is sound in **both** directions. The delivered number stands.

---

## 1. Denominators (settled, reproduced)

| Quantity | Value | How measured |
|---|---|---|
| legacy modules searched | **11** | `command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`, `version.py`, `auctions.py`, `bundle.py`, `get_game_config.py`, `get_player_info.py`, `legacy_command_recorder.py` — **all 11 present** |
| named `command.py` dispatcher branches | **63** | `cmd == "…"` in raw source |
| save-shaped JSON documents in the repository | **231** | every `.json` with a dict `privateState` |
| committed `PREMIUM_ACCOUNTS` entries | **6** | `config/main.json` → `globals`, and `normalized/globals.json` verbatim |
| committed normalized `darts_items` entries | **27** | `packages/game-content/normalized/darts_items.json`, ids `1..27` |

The first probe in this investigation searched only the **7** modules that
`social_state.gd`'s older module list implied, and its §0 figures were
**re-measured over all 11** before being recorded. Every darts and premium site
is inside the original 7; the four extra modules add no darts site and add only
`reset_stuff`'s **import** and **call** in `get_player_info.py`. **The figure
did not change, but the denominator had been wrong and is recorded as
corrected.**

---

## 2. Finding A — darts is the only special system with real, varied, played state

Four fields across three command branches plus one engine function. All are
**client-argument-driven** except the week-boundary reset in §4.

| Branch | Site | `args` read | Effect |
|--------|------|-------------|--------|
| `darts_reset` | `command.py:573` | `[0]` | seed from client; **6 fields** written, `dartsBalloonsShot` reset to `[]`, both instants to `time_now` |
| `darts_new_free` | `command.py:586` | **none** | `dartsHasFree = True`, `timeStampDartsNewFree = time_now` |
| `darts_shoot_balloon` | `command.py:593` | `[0]`, `[1]` | **appends** client `index` to `dartsBalloonsShot`; `dartsHasFree = False`; stamps `timeStampDartsNewFree`; if client `won_extra` then `dartsGotExtra = True` |

**Every value that makes the system work is client-sent.** The seed, the shot
index, and whether the shot won are all `args`. This is the same authority
shape as `set_resource_allies` and as the `research_buy_step_cash` line: a
recorded transition whose *inputs* are untrusted.

**Three authority gaps, measured, not assumed:**

1. **No bound on the shot list.** `darts_shoot_balloon` appends whenever
   `index not in targets` and never checks a length. A client may grow
   `dartsBalloonsShot` without limit. This is the same unbounded-client-list
   shape recorded for `set_goals` in `godot-quests`.
2. **No membership test against the committed schedule.** The only test is
   `if index not in targets`. Nothing compares `index` to the 27 committed
   `darts_items` ids — and **the corpus contains a shot index of `0`, which is
   not among them** (ids run `1..27`). The legacy server accepted an
   out-of-schedule shot.
3. **`won_extra` is an unvalidated truthiness.** `if won_extra:` accepts any
   non-empty client value. No `int()`, no comparison.

---

## 3. Finding B — `buy_premium_account` is the **first server-derived** value in M11

This inverts the pattern every other M11 surface follows. The duration is
**read from committed content on the server**:

```python
612: elif cmd == "buy_premium_account":
613:     package_index = args[0]
614:     days = get_premium_days(package_index)
616:     privateState = save["privateState"]
617:     ts_premium = privateState["timeStampEndPremium"]
618:     if time_now >= ts_premium:
619:         privateState["timeStampEndPremium"] = time_now + days * 86400
620:         print(f"Bought Premium Account for {days} day(s)")
621:     else:
622:         privateState["timeStampEndPremium"] += days * 86400
623:         print(f"Extended Premium Account for {days} day(s)")
```

`get_premium_days` (`get_game_config.py:181-189`) reads
`globals.PREMIUM_ACCOUNTS`, **clamps** an oversized index to the last entry,
and returns `package["time"]` or `0` when `time` is absent.

Committed schedule — `time` in days, `price` in the game's primary currency:

| index | `time` (days) | `price` |
|---|---|---|
| 0 | 360 | 800 |
| 1 | 180 | 450 |
| 2 | 30 | 80 |
| 3 | 7 | 40 |
| 4 | 3 | 20 |
| 5 | 1 | 8 |

### B1 — **THE committed `price` has zero consumers. Premium is bought for free.**

`get_premium_days` returns `package["time"]` and **never touches `price`**.
A whole-module scan for `premium`/`Premium`/`PREMIUM_ACCOUNTS` over **all 11**
legacy modules returns only the 4 sites above plus the import, the single
`get_game_config.py:182` table read, and the two `print` lines. **Nothing
anywhere reads a premium price.** Measured code-only sites for the constant
literals, so the arithmetic in §3 is reported rather than reconstructed:

| Literal | Code-only sites |
|---|---|
| `86400` | `command.py:619`, `command.py:622`, `engine.py:239`, and six in `get_game_config.py` |
| `604800` | `engine.py:248`, `get_game_config.py:243` |
| `259200` | `engine.py:246`, `engine.py:247` |

The `259200` pair is `reset_stuff`'s week offset (§4) and appears **nowhere
else** in the eleven modules.

This is the sharpest content-with-no-consumer finding in M11 so far, and it
differs from the three social tables in kind: those are cosmetic rows, this is
**a committed price for a paid purchase**. The server derives the *duration*
authoritatively and charges *nothing* for it.

> This inverts the shape of the recorded `research_buy_step_cash` refusal.
> There, the server **discards a client-sent price**. Here, the server
> **ignores a committed price**. Both are recorded refusals to charge, but they
> are different mechanisms and a proposal must not describe them as one.

### B2 — two arms, selected by a server-side comparison

`time_now >= ts_premium` selects **set** (`now + days*86400`) over
**extend** (`+= days*86400`). Both arms are reachable in the corpus:

- **47 of 231** documents carry `timeStampEndPremium = 1682945878`
  (= **2023-05-01 12:57:58 UTC**).
- That instant is **in the past** relative to today, so a replay of any command
  against those documents takes the **set** arm. The **extend** arm is reachable
  only for a document with a future instant, and **no such document exists** —
  so the extend arm is exercisable only over crafted input, and must be
  recorded as such rather than as corpus-evidenced.

### B3 — there is **no premium flag**

`premiumAccount` carries in **0 of 231** documents. Premium is *only* a
timestamp; there is no boolean, no tier, and no separate expiry field.

---

## 4. Finding C — `reset_stuff` is the only time-derived server mutation here

`engine.py:230-249`, reached from `get_player_info.py:9` on **every player-info
fetch** — not a command, not client-triggered:

```python
243:     if "timeStampDartsReset" in privateState:
246:         last_darts_reset = privateState["timeStampDartsReset"] + 259200
247:         temp = now + 259200
248:         if temp // 604800 != last_darts_reset // 604800:
249:             privateState["timeStampDartsReset"] = 0
```

Measured properties, none of them derived:

- The guard is `in privateState` — an **existence check**, the only one in this
  surface, and the reason the field cannot be assumed present.
- The offset is `259200` seconds (3 days), applied to **both** sides, with the
  source comment stating the intent: *"since timestamp 0 is thursday, we want
  reset to happen on monday"*.
- The week is `604800` seconds; the comparison is **floor-division week index
  inequality**.
- The write is to **`0`**, never to `time_now` — the field is a flag for the
  client to call `darts_reset`, exactly as `sessions.py:121`'s comment says.

> `reset_stuff` also resets `map["numTradesDone"]` on a **day** boundary at
> `:239-240`. `numTradesDone` has three code-only sites — `command.py:469`,
> `command.py:470` and this one — so unlike the darts field it is *also*
> command-reachable. **No claim is made about it in this document**, and it is
> named here only so a later line does not rediscover the function and assume
> it touches darts alone.

---

## 5. What the corpus shows: darts and premium are **played**, not inert

Over the 231 save-shaped documents:

| Field | Distinct recorded values | Distribution |
|---|---|---|
| `dartsRandomSeed` | 15 | `0` ×107, then 23340 ×51, 9709 ×47, … |
| `timeStampDartsReset` | 15 | `0` ×107, then 1705671822 ×51, … |
| `timeStampDartsNewFree` | 21 | `0`, 1671867066, 1671967335, … |
| `dartsHasFree` | 2 | `false` ×159, `true` ×72 |
| `dartsBalloonsShot` | 4 | `[]` ×178, `[18, 17]` ×51, `[0]` ×1, `[18]` ×1 |
| `dartsGotExtra` | 1 | `false` |
| `timeStampEndPremium` | 2 | `0` ×184, `1682945878` ×47 |

**53** documents carry a fully played darts state (seeded, reset-stamped, and
with shots). **47** additionally carry a live premium instant. Ids `17` and `18`
resolve against the committed `darts_items`; **`0` does not**.

**The canonical corpus document `tests/saves/fresh-player.json` has none of
this** — every darts field is at its initial value and `timeStampEndPremium` is
`0`. So:

> **An executed-legacy fixture for this line is possible only against a village
> corpus document, not against `fresh-player.json`.** The fresh-player document
> cannot exercise the shoot arm, the free arm, or the premium buy arm. Any
> proposal must name the corpus it means, and must not claim fresh-player
> coverage.

---

## 6. Classification of the two surfaces

| Surface | Classification | Basis |
|---|---|---|
| **Darts state** | **Real, played, and client-argument-driven.** Four client-sent inputs, three unbounded/membership-free rules, one server-side week reset | §2, §4, §5 |
| **Premium purchase** | **Server-derived duration, zero charged price.** The first M11 surface with an authoritative server-computed value, and the first with a **committed price nothing reads** | §3 |

**Both are inside M11's `special mechanics` / `legacy event systems` items.**
Neither is social. `social_state.gd` already owns `timeStampEndPremium` and
`crossPromotionsFinished` as **inert social-candidate fields**, and both are
**wrongly filed there** — `timeStampEndPremium` has three real writers and a
server-derived value, and `crossPromotionsFinished` is inert but is a
cross-promotion field, not a social one. A proposal must resolve that
ownership, not silently re-report them.

---

## 7. What this investigation does NOT establish

- **No parity claim.** Nothing here was executed against the legacy server.
  Every figure is a static source or corpus measurement.
- **No fixture was captured.** §5 establishes that one *could* be, against a
  village document, and that `fresh-player.json` cannot. Capturing it is a
  later decision, not a finding.
- **The corpus's live darts/premium state is a corpus fact, not a claim about
  all players.** 231 documents is every save-shaped JSON in the repository, not
  the game's population.
- **`darts_random_seed`'s meaning is not established.** It is written from a
  client value and read by nothing. No claim is made that it seeds a PRNG, and
  the word "seed" is used only because the source prints `SEED`.
- **`dartsBalloonsShot` entries' meaning is not established.** `17`/`18` resolve
  against committed `darts_items` ids, but **nothing in the preserved server
  performs that resolution**, so it is recorded as a coincidence of two
  independent id spaces, not as a lookup.
- **The `[0]` shot is reported, not explained.** It is outside the committed
  schedule and the legacy server accepted it; whether the Flash client could
  produce it is unverifiable from the oracle.
- **Absence of a token remains not absence of a feature.** Nothing here says the
  Flash client lacked a darts UI or a premium purchase flow.
- **The extend arm is unproven against the corpus** (§3 B2) and would need
  crafted input.

## 8. Recommended next step

The natural line is the one this document most supports: a **`godot-darts`**
capability projecting the six darts fields and the premium instant **verbatim**,
delivering the **server-derived** premium duration and the two-arm selection as
**server-authoritative transitions**, reproducing the week-boundary reset as a
**derived predicate**, and **refusing** to trust the seed, the shot index,
`won_extra`, the unbounded list, and the committed price.

That is the shape of `godot-rewards` and `godot-unit-collection` — the two
precedents that derived a value from committed content and proved no balance
moved — rather than the shape of the pure refusal lines, because the premium
duration genuinely **is** derived.

**This is a recommendation, not a proposal.** No OpenSpec change is created by
this document.
