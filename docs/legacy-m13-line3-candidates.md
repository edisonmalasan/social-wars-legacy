# M13 line 3 — ranked target selection from the surviving D6 pool

**Date:** 2026-10-13
**Commit measured:** `22eee08` ("Merge pull request #392 from edisonmalasan/chore/archive-collection-grant-authority")
**Interpreter:** `%TEMP%\opencode\cpython39\pkg\tools\python.exe` (CPython 3.9.13), always with `-B`. The
PATH `python` was never invoked.
**Status of this file:** investigation record. Nothing was implemented, no OpenSpec change was created, no
OpenSpec artifact was edited, no git write command was run, no task box was ticked, and no file outside this
one was created or modified. Working tree was clean before and after.

---

## 0. What this file is, and what it is not

This is a **target-selection** investigation for M13 line 3. It answers one question: **of the branches left in
the D6 pool after lines 1 and 2, which one should line 3 make authoritative first?**

It is not a proposal, not a design, and not a spec. Every rule, price, index base, and derivation it mentions
would have to be re-argued in a proposal. The reasoning below is deliberately one level short of a design so
that nothing here can be mistaken for approval to implement.

### The question, restated operationally

M13's purpose is stated in `AGENTS.md` and in the roadmap: replace the legacy server's habit of applying a
**client-sent** resource vector (`command.py:40`, before the dispatcher opens at :42) with **server-authoritative**
outcomes. A line is valuable in proportion to how much of a transaction currently travels from the client as
*dictionary* rather than as *intent*.

### The five measurements applied to every candidate

| # | Question | How it was measured |
|---|---|---|
| **C1** | Is the stored outcome **already** server-derived, or could it be? | Read of the branch body: every `args[]` index, every `save`/`map` write, every `get_*`/`map_*`/`add_*`/`pop_*` call, with absolute `command.py` line numbers. |
| **C2** | Is any part of the outcome **client-dictated**? | Same read; each dictating argument named with its slot and the line where it lands in stored state. |
| **C3** | Is there a **request path** at all? | Every `*_envelope.build_envelope` under `apps/compat-api/` **executed** with a synthetic intent, and the branch read out of the batch it returns. Cross-checked by quoted-token scan of all 21 envelope modules. |
| **C4** | Is it **fixture-proven**? | Every `tests/fixtures/**/steps/**/request.json` parsed; three strengths reported separately: distinct steps, **dedicated** steps (a step that carries this branch and no other), and occurrences. |
| **C5** | Which **committed content** could a derivation read, and by what function? | Field-level walk of `packages/game-content/normalized/*.json` (presence, distinct-value counts) plus a four-rule occurrence census of each candidate field across the eight root legacy modules. |

Counting rules used throughout, because they changed answers:

- **Occurrences and distinct lines are reported separately.** Counting lines understates a field read three
  times on one line.
- **Raw substring hits are reported as such** under four rules — whole-file, code-only (comments and string
  literals stripped by a two-state lexer), exact identifier token, and the quoted form `"field"` / `'field'`.
  Python dict keys *are* string literals, so the quoted form is counted over the **raw** file while the
  code-only form is not; a field consumed only as a dict key looks zero-consumer under a rule that strips
  string literals.
- **Zero-consumer** therefore means zero under the rule named, over the eight modules named — never
  "never used" unqualified.

---

## 1. Method and containment

- Every measurement script was written to `%TEMP%\opencode\m13l3\`, **not** into the repository, so that
  "edit nothing outside this deliverable" is satisfied by construction rather than by care.
- `get_weekly_reward_length()` was **executed** against the committed `config/main.json` (import-time patches
  apply and print; the return value is recorded below) rather than read and inferred.
- Every envelope builder was executed in-process against `apps/compat-api` modules. Zero loud failures in the
  final run; the first run's 14 loud failures are disclosed in §9.
- Save-document walks covered **34 committed JSON documents** under `villages/` (incl. `villages/quest/`),
  `tests/saves/` and `saves/`; one of them (`tests/saves/manifest.json`) has no `privateState` and is excluded
  from every field census, leaving **33 real save documents**.
- No server was started, no network call was made, no Flash/Ruffle/ActionScript/browser executed.

---

## 2. The D6 pool, re-derived from source

### 2.1 The 63 branches

Measured by regex over `command.py` for `\bcmd\s*==\s*['"]([A-Za-z_0-9]+)['"]`: **63 comparison sites,
63 distinct names, 0 duplicates.** The dispatcher is one chain whose first arm is `if cmd == "buy":`
(`command.py:42`) and whose remaining 62 arms are `elif`. This reproduces the 63 in
`tools/command-catalog` and the 63 in `AGENTS.md`.

> **Instrument fault.** The regex I first wrote was `el?if`, which requires a leading `e` and therefore
> cannot match a bare `if`. It reported **62**. The missing name was `buy` — the first branch. A census that
> silently drops the first arm of a chain is not a census.

### 2.2 Routed vs unrouted

Two independent measures were run, and they disagree. Both are reported.

**Measure A — executed builders (39).** Each `*_envelope.build_envelope` was executed and the branch read out
of the `commands` batch it returns. Result: **21 routes, 39 distinct dispatched branches, 0 loud failures.**

**Measure B — quoted-token scan of all 21 envelope modules (44).** A branch counts if its name appears as a
quoted literal in any `*_envelope.py`. Result: **44 of 63.**

The difference is exactly five branches, and each was then located by hand:

| Branch | Where its name appears | Dispatched? |
|---|---|---|
| `buy_mana_new` | `magic_envelope.py:152` `NO_OP_COMMAND = "buy_mana_new"` | **no** |
| `store_add_items` | `stored_placement_envelope.py:588` — a refusal-catalog string | **no** |
| `buy_offer_pack` | `collection_envelope.py:425` — inside a contract record | **no** |
| `fast_forward` | `quest_envelope.py:201`, `research_envelope.py:302` — contract constants | **no** |
| `push_queue_unit2` | `magic_envelope.py:924` catalog label; `queue_envelope.py:169` `ATOM_FUSION_COMMAND` | **no** |

**Verdict: routed = 39, unrouted = 24.** A branch is routed only if a request path *builds and sends* it;
naming it as a parked constant or a refusal label is the opposite of routing. `tools/route-coverage`
independently lists `buy_mana_new` under `branches_without_cited_route`.

### 2.3 Fixture-proven

| Figure | Value |
|---|---|
| fixture directories under `tests/fixtures/` | **21** |
| `request.json` files | **104** |
| … carrying a `form` object | **78** |
| … with **no** `form` key | **26** |
| distinct branches in a parsed batch | **34** |

**Two rules were used, and they agree exactly.**

- **R1 (raw):** un-escape `\u007b`/`\u007d` in the raw `form.data` text, split on the first `;`, parse the
  JSON tail, read `commands[].1`.
- **R2 (parsed):** `json.loads(request.json)` → `["form"]["data"]` → same.

`R1_only == R2_only == []`. R2 is the stronger rule — R1 can be satisfied by prose that happens to quote a
branch name in a manifest field — and because both produce the same 34, the fixture corpus is not
self-deferring on this point.

### 2.4 The pool arithmetic, and the reproduction verdict

```
63  named dispatcher branches
39  dispatched by a v0 route          (24 have no route at all)
34  fixture-proven in tests/fixtures
33  routed ∩ fixture-proven           <- the D6 pool
32  minus `collect`                   <- reproduces the recorded 32 EXACTLY
31  minus `complete_collection`       <- today's candidate set, at HEAD
```

**Verdict: the recorded 32 reproduces exactly.** The pool is not copied from the binding documents; it is
re-derived and lands on the same number by a different route.

The 33 members are:

```
activate  add_click  admin_set_quest_rank  buy  buy_magic  buy_stored_item_cash
collect  collect_mission  complete_collection  complete_goal  complete_tutorial
end_attack  end_quest  expand  kill  kill_iid  level_up  move  next_research_item
next_research_step  place_stored_item  pop_queue_unit  push_queue_unit
research_buy_step_cash  reset_research_item  sell  sell_stored_item  set_goals
set_quest_var  store_item  use_magic  weekly_reward  win_daily_bonus
```

Boundary figures, measured: **6** routed branches are **not** fixture-proven (`activate_item_click`,
`buy_premium_account`, `darts_new_free`, `darts_reset`, `darts_shoot_balloon`, `resurrect_hero`) and are
outside the pool by D6's own definition; **1** fixture-proven branch is **not** routed (`add_xp_unit`) and is
therefore outside it too, despite being the single strongest fixture in the repository — see §7.

> **Note on the routed set's stability.** The 33-member pool is identical whether the routed set is the
> executed 39 or the named 44, because none of the five metadata-only names is fixture-proven. The
> `buy_mana_new` contradiction in §3 therefore does **not** disturb the pool — it disturbs the routed/unrouted
> headline figure that the pool is quoted against.

---

## 3. A measured contradiction with a binding document

`docs/legacy-m13-unrouted-branches.md` states the split **four times**:

- line 23: `40` branches dispatched by a v0 route
- line 24: `23` branches with no route at all
- line 167 and line 172: the same two numbers again

and `AGENTS.md`'s M13 section, in its FIGURE CORRECTION dated 2026-10-13, adopts them ("**40** of 63
branches are dispatched by a v0 route and **23** by none").

**Both documents are wrong by one, in the same direction. The measured numbers are 39 routed and 24 unrouted.**

The single disputed branch is `buy_mana_new` (`command.py:649-651`), whose entire body is one `print`. It is
named in `magic_envelope.py:152` as `NO_OP_COMMAND`, whose own note at :155 records that the branch's body is
"a print whose own trailing comment reads …", and `magic_envelope.ACTIONS` at :165 of that module is
`(ACTION_BUY, ACTION_USE)` — `buy` and `use` only. Measured occurrences of `buy_mana_new` in
`compat_service.py`: **0**.

**Which number is right, and why:** 39/24. The document's own stated method — "measured by executing each
committed envelope builder and reading the branch out of the batch it returns" — produces 39. The 40 arises
from reading `buy_mana_new`'s **name** out of the magic module and counting a parked no-op constant as a
dispatch. `tools/route-coverage` agrees with 39: it lists `buy_mana_new` in `branches_without_cited_route`,
because it measures whether a handler *cites* a resolving `command.py` line span, and no handler does.

**What this does and does not change.** It does **not** change the pool, the 33, the 32, or the 31 — see
§2.4.

**It does NOT change the "non-authoritative branches" figure, and this section previously claimed it
did. That claim was wrong and is withdrawn.** It read `docs/DEVELOPMENT_ROADMAP.md` line 37's "61" as
stale and proposed **62** (63 − 1 authoritative branch). At the time the roadmap figure was written,
63 − 1 **was** correct, because `collect` was the only authoritative branch. It is not stale: line 2
delivered `complete_collection` as `POST /v1/collection`, so the arithmetic is now 63 − **2** = **61**,
which is exactly what the roadmap says. The proposal to raise it to 62 would have introduced the error
it claimed to remove. The root cause of the mistake is a **stale `AGENTS.md` figure**, not a stale
roadmap: `AGENTS.md`'s 2026-10-13 correction states "the correct non-authoritative total is **63 - 1 =
62**", which was true when written and was superseded by line 2 without `AGENTS.md` being updated.

The two figures move in **opposite** directions and only one of them was actually wrong:

| Figure | Recorded | Correct | Changed? |
|---|---|---|---|
| routed / unrouted | 40 / 23 | **39 / 24** | **yes — corrected** |
| branches without an authoritative route | 61 | **61** | **no — the proposal was rejected** |

**Resolution.** The routed/unrouted split was corrected in the `server-v1-authority-boundary` **Purpose**,
which had carried 40/23 since line 2's Sync (PR #393, merge `6be6012`). `docs/legacy-m13-unrouted-branches.md`
was **not** edited by that correction and still carries 40/23 at lines 23, 24, 167 and 172; it remains
owned by whatever change corrects it. `AGENTS.md`'s superseded "63 − 1 = 62" is **not** edited here — `AGENTS.md`
is outside this investigation's write scope, and the stale figure is recorded as a follow-up rather than
silently fixed.

**Neither figure was changed by this investigation.** `docs/legacy-m13-unrouted-branches.md` and
`docs/DEVELOPMENT_ROADMAP.md` were untouched by the investigation itself; the contradiction is recorded
here for the change that owns those documents. The **spec** copy of the 40/23 figure was corrected
afterwards by the orchestrator (PR #393), and the "non-authoritative" proposal above was rejected there —
see the table under §3.

---

## 4. The corpus census this ranking depends on

Measured over all **33** real save documents. Values that occur in only one or two documents are shown with
their document count.

| Field | Distinct values across 33 docs | Notes |
|---|---|---|
| `privateState.magics` | `{}` in **32**; `{'10':0,'9':1,'1':2,'2':0,'4':2}` in **1** (`villages/Neutral.json`) | all **5** populated keys resolve against `magics.json` ids `1..10` |
| `privateState.weeklyRewardIndex` | `0` (28), `1` (5), `2` (1), `3` (1) | **3 and 4 never observed**; the branch's cycle is mod **5** |
| `privateState.timeStampMondayBonus` | `0` (26), else **5** distinct non-zero instants across 7 documents | |
| `privateState.bonusNextId` | `0` (7), `2` (22), `3` (2) | **`0` is unreachable** by the branch's own 1..5 clamp |
| `privateState.questsRank` | `{}` in **31**; keys `0..18` in 1, `0..22` in 1, every value the **string** `'1'` | |
| `privateState.goals` length | **151** in 31 documents, **153** in 2 | populated indices reach **92,93,94,95,96,97,99,110,152** |

Two of those rows are decisive and are used as evidence below:

- **`magics`: the one populated document's five keys all resolve against the committed id space.** This is
  corroboration by corpus, not by name.
- **`weeklyRewardIndex` reaches 3 while the committed schedule has 3 rows and the cycle modulus is 5.**
  Indices 3 and 4 are reachable by the branch and have no committed row. One of them is **observed in the
  corpus** (`weeklyRewardIndex = 3` in `villages/Neutral.json`; `= 2` in `villages/Nerri.json`).
- **`bonusNextId` records 0, which the branch cannot produce.** Its clamp is `next_id > 5 → 1`, so the
  reachable set is `1..5`. A stored `0` therefore has no branch-explanation, and any derivation must either
  treat `0` as "never granted" or as a 0-based ladder index — an unresolvable index-base collision of the same
  class as the already-archived `levels` one-based dispute.

---

## 5. Content availability, measured

### 5.1 The globals census

`packages/game-content/normalized/globals.json` carries **105** rows. Counting occurrences of each `key`
across the eight root legacy modules (`command.py`, `engine.py`, `server.py`, `sessions.py`, `constants.py`,
`get_game_config.py`, `auctions.py`, `version.py`):

| | Count |
|---|---|
| keys with **zero** occurrences in all 8 modules | **101** |
| keys with any occurrence | **4** — `ALLIES_BUILDING`, `ALLIES_MARKET`, `MONDAY_BONUS_REWARDS`, `PREMIUM_ACCOUNTS` |

Two of those four are already delivered (`PREMIUM_ACCOUNTS` by `godot-darts`/`godot-premium`). That leaves
**`MONDAY_BONUS_REWARDS` as the only committed schedule in the entire globals package with a live legacy read.**

### 5.2 The three reward ladders, side by side

| Ladder | Rows | Legacy reads | Content shape |
|---|---|---|---|
| `MONDAY_BONUS_REWARDS` | 3 — `{type:"g",value:2500}`, `{type:"u",value:[1055,1033,1046,1063,1198]}`, `{type:"c",value:5}` | **yes** (`get_game_config.py:195-208`) | mixed scalar / list; all 5 unit ids resolve to real `units.json` rows |
| `DAILY_GOLD_REWARDS` | 5 — `[100,250,500,1000,0]` | **0** | flat scalars |
| `ALLIANCE_DAILY_BONUS_REWARDS` | 4 — all `{type:"g"|"c", members:N}` | **0** | member thresholds |

`get_weekly_reward_length()` was **executed**, not read:

```
value: 5
MONDAY_BONUS_REWARDS rows: 3
```

So the cycle modulus is **5** and the table has **3** rows. This is measured, and it is a genuine hole.

### 5.3 `magics.json` — the strongest zero-consumer price vector found

**10 rows**, ids `1..10` contiguous, 15 fields, all 10 rows populated:

| id | gold | cash | mana | level | area | target | name |
|---|---|---|---|---|---|---|---|
| 1 | 30000 | 50 | 8 | 38 | [5,7,9] | 2 | AirStrike |
| 2 | 40000 | 60 | 8 | 40 | [5,7,9] | 1 | Medic Case Rain |
| 3 | 60000 | 80 | 8 | 45 | [5,7,9] | 1 | Protection Shield |
| 4 | 90000 | 110 | 20 | 52 | [5,7,9] | 2 | Nuclear Bomb |
| 5 | 80000 | 100 | 10 | 50 | [5,7,9] | 2 | Shortcircuit Inductor |
| 6 | 50000 | 70 | 12 | 42 | [25,30,35] | 2 | Magnetic Trap |
| 7 | 70000 | 90 | 16 | 48 | [5,7,9] | 0 | Mech Summoner |
| 8 | 100000 | 120 | 8 | 55 | [5,7,9] | 1 | Stealth Sneak |
| 9 | 20000 | 40 | 15 | 35 | [5,7,9] | 2 | Alien Abduction |
| 10 | 10000 | 30 | 10 | 35 | [5,10,15] | 1 | Attack Boost |

`gold` 10 distinct, `cash` 10 distinct, `mana` 6 distinct, `level` 9 distinct, `area`/`target` 3 distinct.

**Legacy consumers of this table: zero.** Occurrence census for the token `magics`:

| Rule | Occ | Lines | Where |
|---|---|---|---|
| whole-file | 17 | 13 | `command.py` 12, `version.py` 5 |
| code-only | 10 | 8 | `command.py` 10 |
| exact token | 10 | 8 | `command.py` 10 |
| quoted `"magics"` | 6 | 6 | `command.py` 2, `version.py` 4 |

**Every one of them is `privateState["magics"]`.** Measured occurrences of `magics` inside
`get_game_config.py`: **0**. So the legacy server reads *the player's charge counters* under the key `magics`
and *never reads the committed `magics` table* that describes what those charges buy.

That is the exact shape line 2 found and delivered: committed content carrying an outcome, with zero legacy
consumers.

---

## 6. Ranking

### 6.1 The ordering rule, stated before the table

Ordered by these criteria **in this priority order**, so the order is falsifiable rather than a matter of
taste:

1. **Content-anchored derivation exists** — a committed value that names this branch's outcome and that a v1
   route could read instead of a client-supplied one. (This is what made `complete_collection` the right
   line-2 target.)
2. **The stored outcome is already server-computed**, so authority tightens an existing rule rather than
   inventing one.
3. **Fixture depth**, measured as dedicated steps.
4. **A live v0 route already exists** to replace.
5. **A measured unbounded/unvalidated client input** that a refusal would close.

Criteria 1 and 5 pull in opposite directions often — the branches with the worst client input frequently have
no committed content to derive from — so the table reports both rather than collapsing them into a score.

### 6.2 The table

C4 is `steps / dedicated / occ`. C3 gives route and the envelope module that owns it. C1 values: **S** =
outcome already server-computed; **P** = partial; **N** = no.

| # | Branch (span) | C1 outcome server-derived? | C2 client-dictated outcome (arg → state, line) | C3 request path | C4 fixture | C5 content a derivation would read |
|---|---|---|---|---|---|---|
| **1** | `buy_magic` (652-663) | **S** — `+=` then clamped `min(50,…)`, :658 | `args[0]` → stored key `str(magic_id)`, :653/:657/:660 | `/v0/magic` (`magic_envelope`) | **6 / 6 / 6** | **`magics.json`** — `gold`/`cash`/`mana`/`level`; **zero** legacy reads |
| **1** | `use_magic` (664-675) | **S** — `=` then clamped `min(50,…)`, :670 — **2 lines differ from `buy_magic`** | `args[0]` → same key, :665/:669/:672 | `/v0/magic` | **6 / 6 / 6** | same `magics.json`; `mana` column, 6 distinct, zero reads |
| 2 | `win_daily_bonus` (444-464) | **P** — cursor clamped `>5 → 1`, :451-452 | `args[0]` → item into storage, :445/:460; `args[1]` → `next_id=args[1]+1`, :446 | `/v0/reward` (`rewards_envelope`) | 4 / 4 / 4 | `globals.json` `DAILY_GOLD_REWARDS` (5 rows, **0** legacy reads) — link is **name-only**; index base unresolved |
| 3 | `weekly_reward` (345-364) | **P** — `weeklyRewardIndex` computed mod `get_weekly_reward_length()`, :363 | `args[0..4]` → item index/id/x/y/team → `map_add_item`, :347-353 | `/v0/reward` | 3 / 3 / 3 | `globals.json` `MONDAY_BONUS_REWARDS` — **executed**, returns **5** over a **3-row** table |
| 4 | `end_attack` (808-885) | **P** | `args[0]` = JSON blob parsed :813; destruction count computed **inside the blob** → `map_lose_item`, :872 | `/v0/combat` (`combat_envelope`, 3 actions) | **10 / 9 / 11** | none — `attack`/`defense`/`life`/`attack_interval`/`attack_range` measured **zero** consumers |
| 5 | `set_goals` (68-75) | **N** | `args[0]` = goal index, :69 — probe grew the list **151 → 501**, no upper bound; `args[1]` = JSON progress, :70 | `/v0/quests` (`quest_envelope`; `is_goal_index` accepts any non-negative int, `_pad_goals`) | 1 / 1 / 1 | `quests.json` 91 rows, ids 1..91 contiguous — **measured not to bound the corpus** (indices to 152 observed) |
| 6 | `next_research_step` (268-275) | **S** | `args[0]` = track, :269 — no membership test | `/v0/research` | 2 / 2 / 2 | **none** — no committed research cost/step/unlock exists |
| 6 | `next_research_item` (284-292) | **S** | `args[0]` = track, :285 | `/v0/research` | 2 / 2 / 2 | none |
| 6 | `reset_research_item` (293-301) | **S** | `args[0]` = track, :294 | `/v0/research` | 2 / 2 / 2 | none |
| 6 | `research_buy_step_cash` (276-283) | **N** | `args[0]` = cash, :277 — **read and discarded**; `args[1]` = track, :278 | `/v0/research` | 2 / 2 / 2 | none — and the *name* says cash, which is exactly the argument the branch throws away |
| 8 | `expand` (211-217) | **N** | `args[0]` → `int()` appended, :214 | `/v0/expand` | 1 / 1 / 1 | `expansion_prices.json` 98 rows — **already derived** by `godot-building-expand` |
| 8 | `level_up` (81-86) | **N** | `args[0]` → `map["level"]`, :84 | `/v0/level_up` | 1 / 1 / 1 | `levels.json` 100 rows — **already derived** by `godot-building-xp` |
| 8 | `place_stored_item` (233-249) | **P** — instant/orientation/garrison/team derived; cell from args | `args[0..3]`, `args[6]`, `args[7]`, :234-241 | `/v0/place_stored` | 1 / 1 / 1 | none; M6 geometry gap, **recorded not refused** |
| 8 | `complete_collection` (504-524) | **S** | — | `/v0/collection` | 3 / 3 / 3 | `collections.json` — **delivered by line 2** |
| 8 | `collect` (136-148) | **S** | — | `/v0/collect` | 1 / 1 / 1 | `COLLECT_MINUTES` — **delivered by line 1** |
| 12 | `buy` (42-59) | **N** | **all 8** args, :43-50, into `map_add_item`, :55 | `/v0/place`, `/v0/upgrade` | 2 / 1 / 2 | none — `costs` measured **0** occurrences |
| 12 | `move` (119-135) | **N** | `args[1]`,`args[2]` rewrite both coordinate slots, :121-122; `frame`/`string` read and unused, :123-124 | `/v0/move` | 1 / 1 / 1 | none — `velocity` measured zero-consumer on all 429 units |
| 12 | `activate` (412-429) | **P** | `args[1]` → `item[6]["cp"]`, :423 — the build duration | `/v0/construction` | 1 / **0** / 1 | none — `build_time`/`buildTime` measured 0 occurrences |
| 12 | `sell` (149-168) | **S** | `args[1]` = reason, :151, gates the `push_dead_unit` path, :160 | `/v0/sell`, `/v0/upgrade` | 2 / 1 / 2 | none; **no refund claimed** |
| 12 | `kill` (169-182) | **S** | `args[1]` = reason, :171, read and discarded | `/v0/combat` | 2 / 2 / 2 | none |
| 12 | `store_item` (218-232) | **S** | `args[0]` = row key only | `/v0/store` | 1 / 1 / 1 | none — no storing cost, no capacity rule |
| 12 | `sell_stored_item` (250-257) | **S** | `args[0]` = item id, :251 | `/v0/sell_stored` | 1 / 1 / 1 | none — no refund |
| 12 | `buy_stored_item_cash` (475-481) | **N** | `args[0]` = item id, :476 | `/v0/purchase` | 1 / 1 / 1 | none measured; M7's cash price is **derived-provisional** |
| 12 | `push_queue_unit` (676-686) | **S** | `args[0]` = row key only | `/v0/queue` | 1 / 1 / 1 | `training_time` measured **zero** consumers |
| 12 | `pop_queue_unit` (699-709) | **S** | `args[0]` = row key only | `/v0/queue` | 1 / 1 / 1 | `sm_training_time` absent from 129 units and all 470 buildings |
| 12 | `add_click` (525-536) | **S** | `args[0]` = row key only | `/v0/construction` | 1 / **0** / 1 | `clicks_to_build` read once at `engine.py:26` — the **seed**, not the threshold |
| 20 | `end_quest` (752-807) | **P** | `args[0]` = JSON blob, :756; count computed in the blob → `map_lose_item`, :796 | `/v0/quests` | 1 / 1 / 1 | none; the equivalent count refusal is **already delivered** for this branch by `godot-quests` |
| 20 | `collect_mission` (430-443) | **P** — wraps at 99, stored as `str` | `args[0]` → `str(next_mission)`, :438 | `/v0/quests` | 1 / 1 / 1 | none |
| 20 | `set_quest_var` (87-118) | **P** | `args[0]` key / `args[1]` value, :88-89 → `idCurrentMission`, :111 | `/v0/quests` | 1 / 1 / 1 | none |
| 20 | `admin_set_quest_rank` (745-751) | **N** | `args[0]` → dict **key**, `args[1]` → value, :750 — unbounded key space | `/v0/quests` | 1 / 1 / 1 | none — `questsRank` has no committed source |
| 20 | `complete_goal` (76-80) | **N** — **mutates nothing at all** | `args[0]` read only for a `print`, :77 | `/v0/quests` | 1 / 1 / 1 | `quests.json` `reward`, uniform `10`, read by nothing — **no reward to derive** |
| 20 | `kill_iid` (183-188) | **N** — **mutates nothing at all** | `args[0]`, `args[1]`, :184-185 | `/v0/combat` | 1 / 1 / 1 | none |
| 20 | `complete_tutorial` (60-67) | **N** | `args[0]` = step, :61; gate `>=25 or ==15`, :63 → write, :65 | `/v0/tutorial` | 3 / 3 / 3 | none — no committed step count exists |
| 20 | `buy_stored_item_cash` — see row 12 | | | | | |

---

## 7. Recommendation

### 7.1 The target: the `buy_magic` / `use_magic` pair at `/v0/magic`

**Nothing in the pool ranks above it.** The reasoning against each candidate that could plausibly have been
chosen instead follows in §7.2; the reasoning for it is five measured facts.

**R1 — it is the only pool branch whose economic content is committed *and* uncorroborated-by-nothing.**
`magics.json` carries a complete price vector over a contiguous id space `1..10`, and the legacy server reads
the player's charge counters under the key `magics` while reading the committed table **zero** times. This is
the same discovery line 2 made with `collections.json`, applied to a table with more independent fields
(`gold`, `cash`, `mana`, `level`).

**R2 — the link is corroborated by the corpus, not only by the name.** `villages/Neutral.json` is the only
document with a populated `privateState["magics"]`, and its five keys `1, 2, 4, 9, 10` **all resolve** against
`magics.json` ids `1..10`. For `DAILY_GOLD_REWARDS` and `MONDAY_BONUS_REWARDS` there is no such corroboration —
see §7.2. This is the single most important reason the magic pair outranks both reward branches, and it is a
corroboration a name cannot fake.

**R3 — the stored outcome is already server-computed, and already bounded.** The branch computes
`min(50, magics[str(id)] + 1)` itself. No amount arrives from the client. The only client input is the
identifier, and it becomes the stored key unvalidated — so a v1 line's job is to *bound the identifier against
a committed id set* and *derive the price*, with no invention of any state shape.

**R4 — the fixture strength is the best in the pool after `add_xp_unit` and `end_attack`.** **6 dedicated
steps** per arm, 12 combined, from `godot-damage`. Only `add_xp_unit` (12, and not routed) and `end_attack`
(9) exceed it.

**R5 — the route exists and is live.** `/v0/magic` is `compat_service.py:3036` with
`magic_envelope.ACTIONS = (ACTION_BUY, ACTION_USE)`. It is also, measured, the route whose module parks the
`buy_mana_new` no-op — the one branch the §3 contradiction turns on — so a line here closes a known,
documented inconsistency in the same file.

**The shape of a v1 line, stated only as far as it constrains ranking:** derive the charge/price from
committed `magics.json`, refuse an id outside `1..10` (the legacy branch accepts a float and creates a
distinct key — one fixture step, `txn_use_float_id_creates_a_distinct_key`, already records that), and report
what the client sent without echoing it. **No rule above is approved by this file.**

### 7.2 Every rival, and why it lost

**`win_daily_bonus` (rank 2) — lost on linkage, not on size.** Its content case looks better than it is:
`DAILY_GOLD_REWARDS` has 5 rows and **zero** legacy reads, and the branch's own clamp `next_id > 5 → 1`
(:451-452) is a server-side 1..5 cycle. Three measured problems:
(a) the correspondence between the branch and the ladder is **name-only** — nothing in the eight legacy modules
reads either, so "daily bonus reward" in the config could name any of the several daily systems;
(b) the index base is **unresolved** — the branch cycles `1..5` while the ladder is naturally indexed `0..4`,
and the corpus records `bonusNextId = 0` in 7 documents, a value the branch **cannot produce**; resolving it
needs one more corpus datum that does not exist;
(c) the committed vector is **gold only**, with no item column, so the branch's actual grant — an item id sent
in `args[0]` and dropped into storage at :460 — has **nothing to derive from at all**. A v1 line here would
have to refuse an item grant with no replacement, which is a smaller win than it looks.

**`weekly_reward` (rank 3) — lost on a measured hole, despite being the best-linked ladder.**
`MONDAY_BONUS_REWARDS` is one of only **4 of 105** `globals.json` keys with any legacy read, and
`get_weekly_reward_length()` was **executed** to confirm it. But what that execution establishes is the
**cycle length (5)**, not any payout: the branch's long arm grants a client-sent item and its short arm grants
**nothing at all** (:358). So there is no committed row to pay. Worse, the modulus is 5 over a 3-row table, and
`weeklyRewardIndex = 3` is **observed in the corpus** (`villages/Neutral.json`) — a state the content cannot
describe. A v1 line would have to either refuse a reachable, corpus-real state or invent a fifth row.

**`end_attack` (rank 4) — lost on content, and it is already half-delivered.** It has the strongest single
fixture in the pool (**10 steps / 9 dedicated**) and the most obviously illegitimate input in the pool: the
destruction count is computed **inside a client-supplied JSON blob** and handed to `map_lose_item` at :872. But
`godot-quests` has already delivered exactly this refusal for the twin branch `end_quest` (probe 4 of the
recorded investigation: the legacy server destroyed a row, 40 → 39, while the modern endpoint destroys none).
Repeating it for `end_attack` is a second instance of a shape the project has already shipped, and there is no
committed content to derive from instead: `attack`, `defense`, `life`, `attack_interval`, `attack_range` are
all measured zero-consumer. It is a good *later* line — a cheap one — but it buys no derivation.

**`set_goals` (rank 5) — lost because the committed set does not bound the corpus.** This is the pool's worst
client input: one probe grew `privateState.goals` from **151 to 501** entries with no upper bound, and the
v0 route **reproduces** that growth rather than closing it. That would make it an obvious target — if there
were content to refuse against. There is not: `quests.json` has 91 rows with ids `1..91` contiguous and zero
gaps, which looks like a perfect bound, and the corpus **refutes** it — populated indices **92, 93, 94, 95,
96, 97, 99, 110, 152** appear in `villages/Nerri.json` and `92, 93, 94, 110, 152` in `villages/Neutral.json`. A
membership test built from the committed ids would refuse states the committed corpus contains. Worse, the
branch has **two index spaces in one body**: `get_attribute_from_goal_id` maps id → position through
`goals_id_to_goals_index`, while `engine.set_goals` writes `goals[goal_id]` **by id**.

**The four research branches (rank 6, tied) — lost because there is no committed research content at all.**
`research` appears in the content package **only** as asset names and one building's display name; there is no
committed cost, step count, unlock requirement, or reward. `godot-research` already recorded the three
counters as **write-only** and `research_buy_step_cash` as reading a client-sent cash value and discarding it.
A v1 line here could refuse the discarded price and could refuse an unbounded track, and would have nothing to
derive. Four branches, one refusal, no derivation.

**Everything at rank 8 or below — lost because it is already delivered or has nothing to derive.**
`expand`, `level_up`, `place_stored_item`, `collect`, `complete_collection` are already delivered lines;
`buy`, `move`, `activate`, `kill`, `store_item`, `sell`, `sell_stored_item`, `buy_stored_item_cash`,
`push_queue_unit`, `pop_queue_unit`, `add_click` have **zero** committed consumers for their decisive input
(`costs`, `velocity`, `build_time`/`buildTime`, `training_time`, `sm_training_time` — all measured 0), which is
the established precedent in this project: record the field and refuse to invent a rule.

**`end_quest`, `collect_mission`, `set_quest_var`, `admin_set_quest_rank`, `complete_goal`, `kill_iid`,
`complete_tutorial` (rank 20, tied) — lost because they are inert or already covered.** `complete_goal` and
`kill_iid` mutate **nothing at all** (measured: zero writes), so there is no state to be authoritative about.
`complete_tutorial` has no committed step count, so a `total_steps()` would be invented. `end_quest`'s
client-dictated count refusal is already delivered. The rest have no committed content and no fixture depth.

### 7.3 The honest comparison with line 2

**No remaining pool branch is as strong as `complete_collection` was.**

`complete_collection` was an unusually good target: a **single** branch, **3 dedicated** fixture steps, a
route with **no prior surface**, and a prize bag that was **literally committed, complete, and had one
unambiguous interpretation** (`{"1085": 1}` matching a committed `prize` exactly, so the grant required no
rule at all — the proof was a set equality).

`buy_magic` is good, but it is good in a weaker way: its content is a **price vector whose correct index base
and correct semantics were never observed**, its two arms are near-duplicates (differing by exactly **2
lines** — `+=` vs `=`, and the print text), and 12 of its 13 pool rivals are inert. It is the strongest
available, not a strong target.

---

## 8. Rejected alternatives

| Rejected | Reason |
|---|---|
| **`add_xp_unit`** — the single strongest fixture in the repository (**12 dedicated steps**) | **Not routed.** It fails D6's own "has a request path" condition and therefore sits outside the 33. Unrouting it would be a different line. |
| **An unrouted branch** (19 remain, e.g. `add_inventory_item`, `batch_remove`, `orient`, `pop_unit`, `push_unit`, `buy_powerups`, `buy_si_help`, `finish_si`, `trade_resource`, `soulmixer_speedup`, `flash_debug`, `ping`, `rt_open_graph_unit`, `first_time_marketplace`, `set_variables`, `set_resource_allies`, `unit_collections_completed`, `remove_inventory_item`, `add_xp_unit`) | None is fixture-proven, so there is no parity evidence for any of them. Line 3 would have no oracle. |
| **The `end_attack` + `end_quest` pair** | Already half-delivered by `godot-quests` for `end_quest`, and both have zero committed combat content. Cheapest, least new. |
| **`/v0/research`** as a route-level target | One route, four branches, **zero** committed content. A route-level line would deliver four refusals and no derivation. |
| **Widening `DAILY_GOLD_REWARDS` / `ALLIANCE_DAILY_BONUS_REWARDS` into the picture** | Both are zero-consumer, but their link to any branch is name-only (§7.2). Naming them in a proposal would present an inference as a finding. |
| **Normalising `magics` into the client's registry** (the D1 question M10 asked for mission vocabulary) | Out of scope for target selection, and the corpus corroboration in §7.1 is available without it. Recorded, not decided. |
| **Choosing by "most client-dictated"** | The branches with the worst client input are exactly the ones with no committed content, so that criterion selects refusal-only lines. |

---

## 9. Unknowns — figures this investigation did **not** establish

Every item below is **unknown**. None of them was estimated, and none may be cited from this file as a
finding.

1. Whether `DAILY_GOLD_REWARDS` is the ladder for `win_daily_bonus`. Name-only. **Unknown.**
2. Whether `ALLIANCE_DAILY_BONUS_REWARDS` is consumed by anything at all, and by what. **Unknown.**
3. The correct index base for `bonusNextId`. **Unknown** and, on this corpus, unresolvable without new evidence.
4. Which `MONDAY_BONUS_REWARDS` row a given `weeklyRewardIndex` selects, given the modulus is 5 over 3 rows.
   **Unknown.**
5. Whether `magics.json`'s `gold`/`cash`/`mana`/`level` columns are the price a coherent player pays, or four
   independent reference values. **Unknown.**
6. What `mana` is spent on. `buy_mana_new` is a `print`, `use_magic` never reads it. **Unknown.**
7. What the `min(50, …)` cap means — lifetime charges, or a display cap. **Unknown.**
8. Whether `/v0/combat` or `/v0/resurrect` is the correct route attribution for `resurrect_hero`. My first
   route map said `/v0/combat`; the executed `combat_envelope.ACTIONS` has **3** actions (`end_attack`, `kill`,
   `kill_iid`) and **not** `resurrect_hero`, and `behavior_envelope` names it instead. I did not re-execute
   the map. **Unknown**, and it does not affect the pool (`resurrect_hero` is not fixture-proven).
9. Whether the `10` of `13` "owned by a delivered capability" census should be cited — the census measured
   that only **14 of 31** candidates are named as whole tokens in some `openspec/specs/*/spec.md`, the other
   **17** only through their route or surface vocabulary, and **no** spec names any route path (`/v0/research`
   and friends appear **0** times across all 77 specs). Exactly one explicit `M13` mention exists in any main
   spec (`godot-quests/spec.md:204`). Whether that constitutes ownership is a judgement, not a measurement.
   **Unknown.**
10. The `offers` and `social` normalized sections were **not measured** — see §10. **Unknown.**
11. What the Flash client displayed for any of these surfaces. This investigation reads the server only.
    **Unknown, and permanently so.**

---

## 10. Instrument faults in my own measurements

Recorded because a figure that is wrong because of the instrument is worse than no figure.

1. **`el?if` regex dropped the first branch.** Reported 62 instead of 63; the missing name was `buy`. The
   chain's first arm is `if`, not `elif`. (§2.1)
2. **First routed run had 14 loud failures** from guessed `build_envelope` signatures. Fixed by reading each
   envelope's real signature; final run 0 failures over 21 routes. (§2.2)
3. **`fpstrength.py` walked one `steps/` level only** and therefore missed `godot-tutorial`'s nested
   `steps/<variant>/<name>/` layout, reporting **33** fixture-proven branches instead of **34**. (§2.3)
4. **`fpstrength.py` assumed `form` always exists**, which is false for 26 of 104 requests. (§2.3)
5. **`node.end_lineno` gave every branch span `:NNN-956`.** The dispatcher is one nested `if`/`elif` chain;
   `ast.walk` over the module found **0** branches because the `elif`s live in `orelse`. Spans were taken
   from the next branch's first line instead. All spans in this file come from that second method.
6. **The code-only lexer destroyed dict-key string literals**, and therefore reported **0** consumers for
   fields that are in fact consumed (e.g. `exp_required`: 0 code-only, but 2 quoted reads at
   `get_game_config.py`). Every "zero-consumer" claim in this file is therefore stated **with its rule
   named**, and the quoted form is counted over the raw file.
7. **The "save writes" detector only matched two-level assignments** and missed
   `privateState["questsRank"][str(quest_index)] = difficulty` (`command.py:750`), reporting
   `admin_set_quest_rank` as writing nothing. It does write. Corrected by reading the body.
8. **`content.py` crashed on `offers.json`** (`FileNotFoundError`) — the file does not exist under that name
   in `packages/game-content/normalized/` — leaving the `offers` and `social` sections unmeasured and the run
   incomplete. (§9.10)
9. **`magic_envelope.build_envelope` takes positional scalars**, not a kwargs dict; my first caller guessed
   wrong and contributed to fault 2.
10. **`config/main.json`'s `items` is a 778-entry positional list** where index 105 is legacy id `"116"`.
    Indexing `items` by legacy id returns the wrong item. Any future derivation that reads item ids from the
    raw config must go through `get_game_config.py`, not the list position.

---

## 11. Claim limits

- **This file recommends a target. It approves nothing.** No rule, price, index base, refusal, or route
  described here is approved, and every one would have to be re-argued in a proposal with its own
  design and spec deltas.
- **Every ranking figure is a property of the preserved server and the committed content at `22eee08`.** It
  says nothing about what the Flash client displayed, did, or sent.
- **The 39/24 split contradicts a binding document** (§3). Neither document was edited. The 33-member pool,
  the 32, and the 31 are unaffected by the contradiction; the roadmap's "61 non-authoritative branches" is.
- **`magics.json` linkage is corroborated but not established.** The corpus corroborates the *id space*; it
  does not establish that `gold`/`cash`/`mana`/`level` are prices rather than reference values.
- **Fixture strength counts steps, not correctness.** 6 dedicated steps means the branch was executed 6
  times against a legacy oracle; it does not mean the corpus exercised every reachable state.
- **Zero-consumer claims are rule-scoped.** They are counted over eight root legacy modules under named rules.
  A consumer in a mod, a served script, or the Flash client would not be counted.
- **No server was started, no network call was made, no Flash, Ruffle, ActionScript, or browser executed.**
  The only executed legacy code was `get_weekly_reward_length()` and the 21 Compatibility API envelope
  builders.
- **No repository file other than this one was created or modified**, verified by `git status --short`
  returning empty before and after.
