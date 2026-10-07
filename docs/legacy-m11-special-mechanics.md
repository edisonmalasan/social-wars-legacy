# Legacy investigation — M11 `special mechanics`

**Status:** investigation record, committed before any proposal.
**Binding scope:** the final M11 deliver item, `special mechanics`.
**Oracle:** the preserved legacy server, read as source. Nothing in this record was observed from the Flash client.

This record exists because the deliver item's name is not the surface, and because the
measurement census that scoped this milestone produced a **ranked candidate list whose
rank #1 turned out to be already owned by a delivered capability**. Recording the census's
displacement is as important as recording its findings: an unowned-surface audit built on
names or substrings would have proposed to re-open a settled decision.

---

## 0. Method, and the instrument this record is careful about

### 0.1 The corpus

**Eleven** legacy root modules, and no others:

```
auctions.py  bundle.py  command.py  constants.py  engine.py  get_game_config.py
get_player_info.py  legacy_command_recorder.py  server.py  sessions.py  version.py
```

All eleven, always. A consumer count over a subset is not a consumer count.

### 0.2 Two lexers, because one cannot do this job

The measurement census established a rule that this record re-confirmed by hitting its
own version of the error:

> This codebase touches state almost entirely through **quoted dict keys**. A code-only
> view that blanks string *contents* therefore removes exactly the tokens under
> inspection. **R3 and R5 are 0 for most state fields by construction; R6 — the
> quoted-access form — is the rule that reveals the access.**

So:

| view | built by | used for |
|---|---|---|
| **RAW** | file text, unmodified | R1 whole-file occurrences, R5 whole-word, **R6 quoted access**, and branch enumeration |
| **CODE-ONLY** | length-preserving two-state lexer: comment bodies and string *contents* blanked, newlines and byte offsets retained | R2 distinct lines, R3 code-only occurrences, R4 code-only distinct lines |

The lexer is **length-preserving on purpose**: every original line number survives, so any
line a rule reports can be checked against the raw file in a second pass without re-running
the lexer. It handles triple-quoted strings, which a naive lexer closes on the first inner
quote — a defect this project has already hit twice.

**Branch enumeration must run on RAW.** Branch names live inside string literals
(`elif cmd == "trade_resource":`), so the code-only view returns **zero** branches. This is
the one place the raw/code split cannot be applied to the token itself.

### 0.3 The six rules

| rule | definition |
|---|---|
| **R1** | whole-file occurrences of the token |
| **R2** | whole-file distinct lines containing it |
| **R3** | code-only occurrences |
| **R4** | code-only distinct lines |
| **R5** | exact identifier token, word-bounded |
| **R6** | quoted-access form: `"field"` or `'field'` |

**A consumer claim resting on R1 alone is wrong in this codebase.** The census
demonstrated that three times, and this record adds a fourth (§2.3). R1 counts substrings
of longer identifiers.

### 0.4 Defects in my own instruments, recorded rather than quietly fixed

Six, all found by measurement during this investigation. Each is recorded with its cause
because each would otherwise have produced a false claim.

| # | defect | cause | consequence if shipped |
|---|---|---|---|
| **D1** | `count_rules` computed R4 over the whole file blob instead of per distinct line, giving R4 = 956 for nearly every token | one pass, two meanings | the entire first census run's R4 column was vacuous; caught before any number was trusted and the census was re-run |
| **D2** | asserted `command.py:915`–`:918` were **all** commented out | over-broad assertion folded two live lines into a four-line claim | 3 false failures; the census was right and specific |
| **D3** | counted quoted keys through the code-only lexer, which blanks string contents | used one instrument for two incompatible rules | reported **0** occurrences of `timeStampMondayBonus` and `timeStampDartsReset` — vacuously, because the lexer had eaten the tokens |
| **D4** | asserted `timeStampDartsReset` had zero live sites *anywhere* | asserted the wrong **scope**: the census claimed the *`fast_forward` write* was commented, not that the *field* was dead | would have made the census look as if it had found a dead field; the field has 5 live sites |
| **D5** | ownership audit tested branch names and name stems | a substring cannot distinguish "this spec claims the mechanic" from "this spec contains the word" | `complete_tutorial` reported **OWNED by 43 specs** (stem `complete`); `soulmixer_speedup` reported **UNOWNED** although `godot-unit-queues` owns it |
| **D6** | the write/read classifier used `["']field["']\s*=[^=]`, missing the `]` between the closing quote and `=` | pattern omitted the subscript close | every site classified **READ**; `command.py:470` and `engine.py:240` are writes |
| **D7** | the §1 branch-group table **duplicated one branch and omitted six** (`collect`, `darts_reset`, `darts_new_free`, `darts_shoot_balloon`, `buy_premium_account`, `fast_forward`) | hand-written from two sources, then trusted | the table did **not** partition the 63 branches, so any reader counting rows got a wrong total while **every individual row was correct** — the same shape as D1 |
| **D8** | the verifier that *caught* D7 then reported a **false mismatch** (54 ≠ 63) | its count-cell pattern used a bare `\d+`, so the two **emphasised** cells were skipped | a checker that reports a false failure is as damaging as one that misses a real one: it trains the reader to dismiss its output. The table was arithmetically correct throughout |

**D3 and D5 are the same class as two recorded incidents**: a substring is evidence about
text, never about meaning. `betWin` is a substring of `betWinner` (`auctions.py:176`), and
`ALLIES_MARKET` / `ALLIES_BUILDING` are substrings of `ID_BUILDING_ALLIES_MARKET = 74` and
`ID_BUILDING_ALLIES_BUILDING = 61` (`constants.py:234-235`).

---

## 1. The surface: 63 named dispatcher branches

Re-derived from raw text by the orchestrator, independently of the census:

* **63** named branches, **0** duplicates
* span `command.py:42` – `command.py:951`
* plus the unhandled fallthrough at `command.py:954`

The census classified all 63 into twelve special-mechanics candidates and seven owned
groups. Its totals sum to 63 (12 + 18 + 18 + 5 + 4 + 3 + 1 + 2). **The census's grouping
is superseded below by a complete partition**, because D7 found the census's own
classification had missed a branch (§6) and this record must not inherit that.

**The grouping is a judgement. The partition is measured.** The table below is checked
token-for-token against a raw re-derivation of `command.py`: every one of the 63 branches
appears exactly once, no token in it is not a branch, and the declared counts sum to 63.

| group | n | branches |
|---|---|---|
| economy / placement | 12 | `buy` `move` `orient` `sell` `expand` `store_item` `place_stored_item` `sell_stored_item` `store_add_items` `buy_stored_item_cash` `batch_remove` `collect` |
| construction | 3 | `add_click` `activate` `activate_item_click` |
| combat | 4 | `kill` `kill_iid` `end_attack` `resurrect_hero` |
| social rewards / assist | 3 | `buy_si_help` `finish_si` `set_resource_allies` |
| progression | 19 | `level_up` `add_xp_unit` `complete_tutorial` `set_goals` `complete_goal` `set_quest_var` `end_quest` `collect_mission` `unit_collections_completed` `next_research_step` `research_buy_step_cash` `next_research_item` `reset_research_item` `add_inventory_item` `remove_inventory_item` `complete_collection` `push_unit` `pop_unit` `buy_offer_pack` |
| queue | 3 | `push_queue_unit` `push_queue_unit2` `pop_queue_unit` |
| magic | 2 | `buy_magic` `use_magic` |
| darts / premium | 4 | `darts_reset` `darts_new_free` `darts_shoot_balloon` `buy_premium_account` |
| **special mechanics (the 9 candidates)** | **9** | `buy_powerups` `soulmixer_speedup` `trade_resource` `win_daily_bonus` `weekly_reward` `rt_open_graph_unit` `first_time_marketplace` `buy_mana_new` `admin_set_quest_rank` |
| infrastructure | 4 | `fast_forward` `flash_debug` `ping` `set_variables` |
| **total** | **63** | |

Of the nine candidates, **three are already owned** (`soulmixer_speedup`, `win_daily_bonus`,
`weekly_reward`, plus `admin_set_quest_rank`), leaving the six audited in §2.2.

---

## 2. The ownership audit — the central finding

A deliver line must be a surface **no delivered spec already claims**. That measurement,
not interest, decides the next change.

Baseline: **71** delivered specs, **435** requirements.

### 2.1 Both name-based tests fail, in opposite directions

**Too loose (D5).** `complete_tutorial` was reported OWNED by **43** of 71 specs, because
the stem `complete` matches almost any English sentence.

**Too tight (D5).** `soulmixer_speedup` was reported **UNOWNED** — because no delivered
spec ever writes the command's name. `godot-unit-queues/spec.md:105-129` carries a whole
requirement titled

> `### Requirement: The atom-fusion speedup is recorded without a cost or a timer`

with three scenarios, the two-key precondition, and the three-key teardown. The archived
change records the decision explicitly:

> `2026-10-01-unit-queues/design.md` — **D6 — `soulmixer_speedup` is recorded verbatim and
> implemented not at all**

So the surface is **owned in substance and unnamed in form**. An audit built on names would
have proposed to re-open a decision that was deliberately settled and archived.

### 2.2 The substance audit

Ownership is therefore re-tested against **requirement titles** — a title is a claim, a
passing mention is not — using the vocabulary a reader would actually search for.

| branch | verdict | evidence |
|---|---|---|
| `soulmixer_speedup` | **OWNED** | `godot-unit-queues` requirement title claims it; archived D6 |
| `win_daily_bonus` | **OWNED** | `godot-rewards`: *"The daily bound is the recorded hardcoded literal, and the rejected content derivation…"* |
| `weekly_reward` | **OWNED** | `godot-rewards`, `darts-schedule-normalization` |
| `buy_mana_new` | **OWNED, spuriously** | see §2.3 — the only "claim" is a substring artifact |
| `buy_powerups` | **UNOWNED** (purchase half only) | `globals-tuning-normalization` mentions `powerup` / `SOUL_MIXER`, **mention only**, no requirement title claims it |
| `trade_resource` | **UNOWNED** | three specs mention `trade`/`market`, **all mention only** |
| `rt_open_graph_unit` | **UNOWNED** | `godot-social-state` mentions `crossPromotions`, **mention only** |
| `first_time_marketplace` | **UNOWNED** | **no spec mentions it at all** |

### 2.3 A fourth recorded substring artifact, and it is a joke

`buy_mana_new` was first reported as claimed by `godot-audio-manager`, under the
requirement title

> `### Requirement: AudioManager bus structure and output state`

because the stem `mana` is a substring of `Audio`+`Manager`. A resource-count probe token
matched an autoload's name. This is the fourth instance of the class, after `betWin` /
`betWinner` and the two `ALLIES_*` / `ID_BUILDING_ALLIES_*` pairs.

### 2.4 What the audit displaces

The census's **rank #1 was the Atom Fusion / Soul Mixer queue**, on the strength of the
single strongest corpus artifact in the milestone: `villages/AcidCaos.json`
`maps[0].items["363"] = [302, 49, 33, 1705771607, 0, [], {"nu": 1, "ts": 0, "ui": 1390}, 1]`,
whose `ts` is exactly `0`.

That artifact is **real, unique, and correctly interpreted** (§3.1) — and the surface it
points at is **already owned**. Rank #1 is displaced for a reason only obtainable by reading
the delivered specs rather than the source. The new rank #1 is §4.

---

## 3. Corrections to committed records

### 3.1 The atom-fusion corpus artifact — confirmed, and the attribution is airtight

Independently re-verified:

```
documents containing the nu+ts+ui triple : 1   (villages/AcidCaos.json, key "363")
building 302 -> 'Atom Fusion'  domain=buildings  type='b'
unit    1390 -> 'Knight Exosuit' domain=units  sm_training_time=480000
```

Across the **9** save documents walked (2 fixtures + 7 villages; `initial.json` is a
village and is walked):

* the triple occurs in **exactly one** document, at **exactly one** key
* the recorded `ts` is **exactly `0`**
* `push_queue_unit` (`engine.py:183-189`) writes `attr["ts"] = timestamp_now()`
* `push_queue_unit2` (`engine.py:206-213`) writes `attr["ts"] = timestamp_now()` **and**
  `attr["ui"] = unit_id`
* `soulmixer_speedup` (`command.py:727-743`) writes `atom_fusion[6]["ts"] = 0` at
  **`command.py:741`**, under the comment `# Set start timestamp to 0 so that if refreshed,
  the timer will be gone`
* `pop_queue_unit` deletes `nu`, `ts` and `ui` **together**

**`command.py:741` is the only site in the eleven modules that ever stores a literal `0`
into a queue `ts`.** The only other writers store `timestamp_now()`, a Unix second. So a
surviving `ts: 0` with `nu` and `ui` both present is **not reachable** by any other path:
not by a push (which stamps the clock), not by a pop (which deletes all three). The
attribution is a proof over the writer set, not an inference from one row.

Also measured, and consistent with the archived record: `sm_training_time` has **exactly
one** consumer in the eleven modules (`command.py:735`), and is **absent from 129 of 429**
units and from all **470** buildings.

### 3.2 **`fast_forward` is NOT inert** — a correction to a committed record

`docs/legacy-unit-movement.md` records `fast_forward` as having no observable effect
"precisely because nothing evaluates elapsed time". **That is false.**

`engine.reset_stuff` (`engine.py:230-249`), called from `get_player_info.py` on a
player-info load, **does** evaluate elapsed time:

```python
now = timestamp_now()
for map in save["maps"]:
    last_trade = map["timestampLastTrade"]
    if now // 86400 != last_trade // 86400:     # :239  DAY bucket
        map["numTradesDone"] = 0                # :240
```

and a week bucket for darts at `:246-249`. `fast_forward` (`command.py:905-947`) writes
`timestampLastTrade` at `:913` by **subtracting a client-supplied number of seconds**
(`seconds = args[0]`, `command.py:906`). So moving that instant **backward across a
`// 86400` boundary clears the trade counter** — a real, reachable state change.

**This correction is independently corroborated by committed corpus data.**
`villages/Neutral.json` records

```
timestampLastTrade = 1683054101   (2023-05-02T19:01:41Z)
numTradesDone      = 0
```

A non-zero trade instant with a cleared count is exactly what the day-bucket reset
produces, and the count has no other writer that zeroes it. The census's correction and
the corpus agree.

### 3.3 `fast_forward` touches **one** darts instant, not two — scoped to the branch

Two lines inside the branch are commented out:

```
 913| LIVE      timestampLastTrade          map["timestampLastTrade"] = max(0, ...)
 914| LIVE      timestampLastBonus          privateState["timestampLastBonus"] = max(0, ...)
 915| COMMENTED timeStampMondayBonus        # privateState["timeStampMondayBonus"] = max(0, ...)
 916| LIVE      timestampLastAllianceBonus  privateState["timestampLastAllianceBonus"] = ...
 917| COMMENTED timeStampDartsReset         # privateState["timeStampDartsReset"] = max(0, ...)
 918| LIVE      timeStampDartsNewFree       privateState["timeStampDartsNewFree"] = max(0, ...)
 919| LIVE      tsAttacksReset              privateState["tsAttacksReset"] = max(0, ...)
```

`command.py:917` (`timeStampDartsReset`) and `command.py:915` (`timeStampMondayBonus`) are
commented; `command.py:918` (`timeStampDartsNewFree`) is live. `:915` carries the author's
reason: `# don't process weekly things`.

**This claim is scoped to the branch, and D4 is why that scope must be stated.** The two
*fields* are emphatically **not** dead:

| field | live quoted-access sites |
|---|---|
| `timeStampDartsReset` | **5** elsewhere — `command.py:581`, `engine.py:243`, `:246`, `:249`, `sessions.py:121` |
| `timeStampDartsNewFree` | **5** elsewhere — `command.py:582`, `:589`, `:603` |

So the finding is that `fast_forward` **skips one specific write**, not that a field is
dead. It also matters for ownership: `godot-darts` already owns the darts instants, so
`timeStampDartsReset` is **not** an unowned surface.

### 3.4 A real coverage gap next to a delivered capability

`godot-mission-vocabulary` owns `MISSION_*` — **64** declarations — and the census
re-measured their absence of consumers **every run**. Two adjacent families sit outside
that ownership:

| family | declarations | line range | legacy consumers | spec coverage |
|---|---|---|---|---|
| `MISSION_*` | 64 | `constants.py:984-1047` | 0 outside `constants.py` | **owned** (`godot-mission-vocabulary`) |
| `TECH_*` | 10 | `constants.py:1075-1084` | 0 | **none — unowned** |
| `SPELL_*` | 14 | `constants.py:1085-1098` | 0 | **none — unowned** |

**24 declarations, zero consumers, zero occurrences of the strings `SPELL_` or `TECH_` in
any file under `openspec/`.** Note the `SPELL_*` family is eight of the twelve colours
(`BLUE`, `RED`, `GREEN`, `BROWN`, `CYAN`, `YELLOW`, `GREY`, `MAGENTA`) plus four verbs
(`ENLARGE`, `SUMMON_DRAGON`, `FULL_LIMIT`, `SPEED_INCREASER`, `RANGE_INCREASER`,
`BLACK_HOLE`).

---

## 4. Rank #1 — the market / trade counters

**This is the strongest unowned surface in the milestone**, and it is the one the
ownership audit promoted. Its evidence is stronger than the census's rank #1 because it
has **committed content, a real consumer, and executed-legacy corpus evidence** at once.

### 4.1 The branch

```python
465|     elif cmd == "trade_resource":
466|         resource_type = args[0]
467|         sold = args[1] # 1 if sold, 2 if bought
468|
469|         num_trades = map["numTradesDone"] + 1
470|         map["numTradesDone"] = min(20, num_trades)
471|         map["timestampLastTrade"] = time_now
472|
473|         print(f"Remaining trades: {20-num_trades}")
```

Both arguments are **dead**: `resource_type` is read once at `:466` and never used;
`sold` is read once at `:467` and never used. **No resource moves.** Resource movement
would have to arrive client-sent through `engine.apply_resources` (`engine.py:251-271`),
applied at `command.py:40` — **before** the dispatcher chain opens at `command.py:42`.

`time_now` is the server clock: `time_now = timestamp_now()` at `command.py:36`.

### 4.2 An eight-key committed economy with **zero** consumers

`MARKET_*` in `packages/game-content/normalized/globals.json`, counted raw and quoted over
all eleven modules:

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

**All eight: zero consumers.** There is no `MARKET_*` or `TRADE_*` declaration in
`constants.py` at all.

**`MARKET_MAX_NUM_TRADES = 20` equals the hardcoded `min(20, …)` at `command.py:470`. This
is a coincidence and is recorded as one.** The constant has zero consumers, so the
coincidence cannot license deriving the cap from it. This is the same treatment this
project already gives the magic cap `50`.

### 4.3 The two counters behave differently, and the difference is the deliverable

Correcting D6 — every site below is classified by hand against the raw line:

| field | reads | writes | consumer? |
|---|---|---|---|
| `numTradesDone` | **1** — `command.py:469`, and that read *is* its own increment | `command.py:470` (clamp), `engine.py:240` (day-bucket reset) | **NO.** The clamp's result is never read to gate anything |
| `timestampLastTrade` | **1** — `engine.py:238`, the day-bucket comparison | `command.py:471` (`= time_now`), `command.py:913` (`fast_forward`, client-supplied decrement) | **YES.** `reset_stuff` reads it |

So the line splits cleanly, and both halves are wanted:

* a **working arm** — `timestampLastTrade` has a genuine consumer, and moving it backward
  across a `// 86400` boundary clears `numTradesDone`. That is testable behaviour with a
  real state change.
* a **refusal arm** — the trade cap is **stored and never enforced**. `numTradesDone`'s
  only reader is its own increment. A client could trade past the cap and the server would
  keep storing `20`.

### 4.4 Corpus evidence — the cap is reached, and the reset is observed

9 documents walked:

| document | `numTradesDone` | `timestampLastTrade` |
|---|---|---|
| `fresh-player.json` | 0 | 0 |
| `AcidCaos.json` | 0 | 0 |
| `General_Mike_30.json` | 0 | 0 |
| `General_Mike_31.json` | 0 | 0 |
| `Kiriakos.json` | 0 | 0 |
| **`Nerri.json`** | **20** | 1705776695 |
| **`Neutral.json`** | **0** | **1683054101** |
| `Scarlet.json` | 0 | 0 |
| `initial.json` | 0 | 0 |

* `Nerri.json` sits **at the cap of 20** — the clamp is exercised by a real player.
* `Neutral.json` separates a non-zero instant from a zero count — the day-bucket reset
  fired (§3.2).

**Neither `Nerri` nor `Neutral` carries `numTradesDone == 20` *and* a later instant**, so
the corpus does not show a clamp-then-reset sequence in one document. Recorded as a limit.

### 4.5 A legacy defect to reproduce, not correct

`command.py:473` prints `20 - num_trades` — the **unclamped** local — while `:470` stores
`min(20, num_trades)`. From the 21st trade onward the two disagree, and the printed
remaining count goes negative:

| incoming | stored | printed "remaining" |
|---|---|---|
| 19 | 19 | 1 |
| 20 | 20 | 0 |
| 21 | 20 | **-1** |
| 25 | 20 | **-5** |

Reproduced verbatim. Correcting it would be a behaviour change this contract does not make.

---

## 5. Rank #2 — the atom-fusion **powerup purchase** (not the speedup)

The census conflated two distinct surfaces under one name. The ownership audit separates
them, and only one is unowned.

### 5.1 Owned, and settled: the speedup

`soulmixer_speedup` (`command.py:727-743`) — see §2.1 and §3.1. Owned by
`godot-unit-queues`, archived decision **D6**.

Its recorded facts, for the avoidance of doubt:

```python
732|         # Quite useless cost calculation for understanding it
733|         start = atom_fusion[6]["ts"]
735|         sm_training_time = int(get_attribute_from_item_id(atom_fusion[6]["ui"], "sm_training_time"))
737|         remaining_time = sm_training_time - (now - start)
738|         cash_cost = ceil(remaining_time / 3600)
741|         atom_fusion[6]["ts"] = 0
```

The duration is read from the **queued unit** (`ui`), not the building; it is read in
**seconds**; `ceil(remaining/3600)` is the shape; **nothing is charged**; and the author's
own verdict is retained verbatim rather than tidied away.

### 5.2 Unowned: the purchase

```python
720|     elif cmd == "buy_powerups":
721|         powerup_index = args[0]
722|
723|         # TODO
724|
725|         print("Buy Atom Fusion PowerUP")
```

**3 executable lines.** It reads `args[0]` and discards it. The branch body is the
author's own placeholder.

The price ladder it would need is committed:

```json
// config/patch/atom_fusion_powerup.json — a single `add` op
[{"op": "add", "path": "/globals/SOUL_MIXER_POWERUPS_LEVELS",
  "value": [{"cash_cost": 1,  "order_increment": 1},
            {"cash_cost": 2,  "order_increment": 2},
            {"cash_cost": 4,  "order_increment": 4},
            {"cash_cost": 8,  "order_increment": 8},
            {"cash_cost": 15, "order_increment": 15},
            {"cash_cost": 20, "order_increment": 20}]}]
```

**Six rows.** Normalized as `globals-tuning-normalization` (a `value_type: array` row,
`source_layer` the atom-fusion patch), which **explicitly refuses a gameplay meaning** for
it. Legacy consumers across the eleven modules: **raw 0, quoted 0.**

In all six rows `order_increment == cash_cost`. Recorded as an observation about the
committed rows. **No index bound, no ladder length, and no requirement that
`order_increment` reach anything are derived** — inventing them would be exactly the
invention this milestone's precedents forbid.

**Why this is rank #2 and not rank #1:** it is adjacent to an owned surface, and its branch
is empty. The committed ladder plus a `# TODO` is a strong *content* story and a weak
*behaviour* story, whereas §4 has a branch with two real state writes, a live consumer,
and two corpus rows.

---

## 6. Rank #3 — `first_time_marketplace`, recovered from a classification gap

**This branch was missed by the census's classification and by my own first group table.**
Recorded because a gap in a census is a fact about the census.

```python
899|     elif cmd == "first_time_marketplace":
900|         privateState = save["privateState"]
901|         privateState["marketPlaceFirstTime"] = True
902|
903|         print("Seen Auction House")
```

* **2 statements.** Writes one boolean.
* **No spec mentions it at all** — the only mention anywhere is
  `docs/legacy-m11-social.md`.
* Corpus: present in **9 of 9** documents, values `None` and `True`.

Note the naming trap already recorded in the census: the **live** writer is
`marketPlaceFirstTime` (lower-case `m` in `market`), which is a **different string** from
`mapPlaceFirstTime` (capital `P`) — and `mapPlaceFirstTime` is present in **0 of 9**
documents.

It is adjacent to `godot-auction-schedule`, delivered in the immediately preceding line.
Too small to carry a milestone on its own; recorded as a candidate and as a census gap.

---

## 7. Rank #4 — `rt_open_graph_unit` and the cross-promotion fields

`rt_open_graph_unit` is unowned (`godot-social-state` mentions `crossPromotions` only in
passing). Its two persisted fields are present in **9 of 9** documents:

| field | distinct values across the corpus |
|---|---|
| `crossPromotionsFinished` | `[]` — **every** document |
| `unlockedSkins` | `None` — **every** document |

Zero legacy readers were found for either outside their own branches. So the surface is
content-persisted and behaviour-absent, with **no corpus evidence of a non-default
value** in either direction — the same evidentiary position the `collection` line recorded
before its fixture existed.

---

## 8. Rank #5 — the dead `SPELL_*` / `TECH_*` vocabulary

24 declarations, zero consumers, zero spec coverage (§3.4). Small, mechanical, and the
same shape `godot-mission-vocabulary` already established — which is precisely why it is
rank #5 and not rank #1: **the precedent exists**, so it adds vocabulary and no new method.
Recorded as the coverage gap that should be closed, and as the obvious hand-off candidate
to `godot-mission-vocabulary` rather than a new capability.

---

## 9. Dead ends, recorded so they are not re-walked

| surface | measured state |
|---|---|
| `buy_powerups` | `# TODO`, 3 executable lines, args discarded (§5.2) |
| `buy_mana_new` (`command.py:649-650`) | **no-op** — reads and discards |
| `/alliance/` (`server.py:326-334`) | empty stub |
| `specials` domain | 1 row ("Expandable Land"); 49 of 57 fields zero-consumer; all 8 consumers shared with the item domain |
| `version.py` | confirmed **MIGRATION**, not gameplay |
| `admin_set_quest_rank` (`command.py:745-750`) | owned by `godot-quests` and `godot-social-state` |
| `TOKEN_MANA = 9` vs `engine.py:260` mana at `resource[7]` | **unresolved** — same slot, different resources, or a stale constant. Not established. |

---

## 10. Claim limits for this record

* **Nothing here was observed from the Flash client.** Every finding is source- and
  corpus-derived. Absence of a server-side behaviour says nothing about what the client
  displayed, which in this codebase may have been entirely client-side — the recorded
  lesson of `godot-friends`, where the "relationship" was a directory listing.
* **No ordinal is claimed** for any zero-consumer field count. Four conflicting ordinals
  already exist in the delivered records, each counting over a different scope.
* **The grouping of 63 branches in §1 is a judgement**, reproduced as a table so it can be
  disputed. The **count** is measured.
* **The `MARKET_*` keys are committed content with zero consumers.** That is a statement
  about the preserved server. It does not license deriving a price, a cap, a period, or a
  percentage from them, and none is derived here.
* **`MARKET_MAX_NUM_TRADES == 20` matching the branch's literal is recorded as a
  coincidence.** The cap must come from the branch or not at all.
* **`numTradesDone` has no consumer**, so "the cap is 20" is a claim about a stored value,
  never about an enforced limit.
* **`timestampLastTrade` is client-writable** through `fast_forward`
  (`seconds = args[0]`, `command.py:906`). Reproducing that faithfully is **not** the same
  as endorsing it; the anti-pattern `AGENTS.md` names as "Bad" is a client dictating an
  authoritative outcome, and any delivered endpoint must decide this explicitly rather than
  inherit it silently.
* **`villages/Neutral.json` is evidence the day-bucket reset fired.** It is one row in one
  document and is consistent with the branch; it is not an executed fixture, and no fixture
  is captured by this record.
* **`villages/Nerri.json` at the cap** shows the clamp's result reached the corpus. It does
  not show that the clamp ever *rejected* anything, because nothing reads it to do so.
* **The `print` defect at `command.py:473` is reproduced, not corrected.**
* **`server.py` routes beyond the audited list, `legacy_command_recorder.py` and
  `bundle.py` are recorded as UNEXAMINED, not empty.** This record does not claim to have
  read them for this item.
* **`auctions/` is never touched with the repository root as the working directory**; the
  containment assertion (`auctions/` absent, `git status` clean) was checked after every
  measurement run in this investigation.
* **Six defects in my own instruments are recorded in §0.4.** Two of them (D3, D5) would
  each have produced a false headline claim.
* No Flash, Ruffle, ActionScript, or browser executed in any measurement behind this
  record, and no network was used at all.
