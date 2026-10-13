# M13 line 4 — ranked target selection, and a withdrawal

**Date:** 2026-10-13
**Commit measured:** `f9865f5` ("Merge pull request #398 from edisonmalasan/chore/archive-magic-price-authority")
**Interpreter:** `%TEMP%\opencode\cpython39\pkg\tools\python.exe` (CPython 3.9.13), always with `-B`. The
PATH `python` was never invoked.
**Status of this file:** investigation record. Nothing was implemented, no OpenSpec change was created, no
OpenSpec artifact was edited, no git write command was run, no task box was ticked, and no file outside this
one was created or modified. Working tree was clean before and after; `git status --short` is empty.
`openspec validate --all --strict` reports **78 passed, 0 failed (78 items)** — unchanged.

---

## 0. What this file is, and what it is not

This is a **target-selection** investigation for M13 line 4. It answers one question: **of the branches still
available after lines 1, 2 and 3, which one should line 4 make authoritative?**

It is not a proposal, not a design, and not a spec. Every rule, refusal and derivation it mentions would have to
be re-argued in a proposal.

It also **withdraws the premise it was commissioned under.** The assignment was that `add_xp_unit` leads. That
premise is **false on measurement**, and the reason is not a close call — it is that the branch has **no request
path**, and the committed content that would anchor a derivation is **contradicted by the committed corpus in 171
of 171 comparable rows**. The reasoning is in §3. Nothing is quietly edited; §10 records what changed.

### The question, restated operationally

M13's purpose is to replace the legacy server's habit of applying a **client-sent** resource vector
(`command.py:40`, before the dispatcher opens at `:42`) with **server-authoritative** outcomes. A line is
valuable in proportion to how much of a transaction currently travels from the client as *dictionary* rather
than as *intent*.

### The five measurements applied to every candidate

| # | Question | How it was measured |
|---|---|---|
| **C1** | Is the stored outcome **already** server-derived, or could it be? | Read of the branch body: every `args[]` index, every `save`/`map` write, every `get_*`/`map_*`/`add_*`/`pop_*` call, with absolute `command.py` line numbers. |
| **C2** | Is any part of the outcome **client-dictated**? | Same read; each dictating argument named with its slot and the line where it lands in stored state. |
| **C3** | Is there a **request path** at all? | Every `*_envelope.build_envelope` under `apps/compat-api/` **executed** with a synthetic intent, and the branch read out of the batch it returns. Cross-checked by quoted-token scan of all 21 envelope modules. |
| **C4** | Is it **fixture-proven**? | Every `tests/fixtures/**/request.json` parsed; three strengths reported separately: distinct steps, **dedicated** steps, and occurrences. |
| **C5** | Which **committed content** could a derivation read, and by what function? | Field-level walk of `packages/game-content/normalized/*.json` (presence, distinct-value counts) plus a four-rule occurrence census of each candidate field across the eleven legacy root modules. |

Counting rules used throughout, because they changed answers:

- **Occurrences and distinct lines are reported separately.** Counting lines understates a field read three
  times on one line.
- **Raw substring hits are reported as such** under four rules — whole-file, code-only (comments and string
  literals stripped by a two-state lexer), exact identifier token, and the quoted form `"field"` / `'field'`.
  Python dict keys *are* string literals, so the quoted form is counted over the **raw** file while the
  code-only form is not; a field consumed only as a dict key looks zero-consumer under a rule that strips
  string literals.
- **Zero-consumer** therefore means zero under the rule named, over the modules named — never "never used"
  unqualified.

---

## 1. Method and containment

- Every measurement script was written to `%TEMP%\opencode\m13l4\`, **not** into the repository.
- Every envelope builder was executed in-process against `apps/compat-api` modules. **Zero loud failures** in
  the final run across 40 executed calls; the first two runs' 27 then 8 loud failures are disclosed in §9.
- Save-document walks covered **34 committed JSON documents** under `villages/` (incl. `villages/quest/`),
  `tests/saves/` and `saves/`; one of them (`tests/saves/manifest.json`) has no `maps[0].items` and is excluded
  from every field census, leaving **33 real save documents**.
- Item identities were resolved through `legacy_id` in `units.json` / `buildings.json`, **never** by list
  position. This mattered: `args[0]` in `add_xp_unit` is a **map row key**, not an item id, so the first pass of
  the anchor analysis was wrong and is disclosed in §9.
- No server was started, no network call was made, no Flash/Ruffle/ActionScript/browser executed.

---

## 2. The pool, re-derived from source

### 2.1 The 63 branches

Measured by regex over `command.py` for `\bcmd\s*==\s*['"]([A-Za-z_0-9]+)['"]`: **63 comparison sites,
63 distinct names, 0 duplicates.** The dispatcher is one chain whose first arm is `if cmd == "buy":`
(`command.py:42`) and whose remaining 62 arms are `elif`; **0** comparison sites sit outside that chain head.
This reproduces the 63 in `tools/command-catalog` and the 63 in `AGENTS.md`.

Spans follow the convention `docs/legacy-m13-line3-candidates.md` §2 fixed: **branch site .. next site − 1**.

### 2.2 Routed vs unrouted

Two independent measures were run. They disagree, so both are reported, and only the executed one is used as
the claim.

**Measure A — executed builders: 39 dispatched.** 40 builder calls, **0 loud failures**, covering 24 v0
routes. A branch counts as dispatched only if its name appears at index `1` of a `[uid, name, args, vector]`
tuple in the **`commands` batch a real builder call returns**. Builder signatures were read from
`inspect.signature`, not guessed.

**Measure B — quoted-token scan of all 21 envelope modules: 44 of 63.** A branch counts if its name appears as
a quoted literal in any `*_envelope.py`. This is a **citation** census, not a coverage claim.

The difference is exactly five branches, and each was located by hand:

| Branch | Where its name appears | Dispatched? |
|---|---|---|
| `buy_mana_new` | `magic_envelope.py` — `NO_OP_COMMAND` | **no** |
| `store_add_items` | `stored_placement_envelope.py` — a refusal-catalog string | **no** |
| `buy_offer_pack` | `collection_envelope.py` — inside a contract record | **no** |
| `fast_forward` | `quest_envelope.py`, `research_envelope.py` — contract constants | **no** |
| `push_queue_unit2` | `magic_envelope.py` catalog label; `queue_envelope.py` `ATOM_FUSION_COMMAND` | **no** |

**Disputes in either direction: zero.** Every name Measure A dispatches is also named by Measure B, and every
name Measure B names but Measure A does not dispatch was located by hand as metadata. A request path *builds
and sends* a branch; naming it as a parked constant or a refusal label is the opposite of routing.

**Verdict: routed = 39, unrouted = 24.**

`add_xp_unit` appears as a quoted literal in **zero** envelope modules. Its only three whole-word occurrences in
`apps/compat-api` are prose inside rationale strings (`collection_envelope.py:287`, `level_envelope.py:94`,
`compat_service.py:431`), backtick-quoted rather than quote-delimited, plus the capture tool
`capture_unit_xp_fixture.py` and test files. **It has no request path.**

### 2.3 Fixture-proven

| Figure | Value |
|---|---|
| fixture directories under `tests/fixtures/` | **21** |
| `request.json` files | **104** |
| … yielding a parsed batch under R2 | **78** |
| distinct branches in a parsed batch | **34** |

Two rules were used and, **once R1 is corrected**, they agree exactly.

- **R2 (parsed):** `json.loads(request.json)` → `["form"]["data"]` → split on the first `;` → parse the JSON
  tail → read `commands[].1`. Yields a batch for **78** of 104.
- **R1 (corrected):** extract the `data` **string literal** from the raw file text and decode it **as a JSON
  string**, then as R2. Yields a batch for **78** of 104, with **0** branch-set disagreements, `R1_only == []`
  and `R2_only == []`.

> **The R1 rule as described in the line-3 record fires 0 of 104 times.** See §10. The agreement is real, but it
> requires the corrected R1; under the rule as literally written the "two rules agree" claim is vacuous.

**A rule ambiguity worth naming, because it changes a figure.** *Dedicated* can mean a step carrying this branch
and no other **branch** (10 for `end_attack`) or no other **occurrence** (9 — one combat step carries
`end_attack` twice). `end_attack` is the only branch where the two rules disagree. **`add_xp_unit` is 12 under
both rules**, because no step carries it more than once, so its headline figure is robust to the ambiguity.

### 2.4 The pool arithmetic at HEAD

```
63  named dispatcher branches
39  dispatched by a v0 route          (24 have no route at all)
34  fixture-proven in tests/fixtures
33  routed INTERSECT fixture-proven   <- the D6 pool
29  minus the 4 delivered branches    <- today's candidate set at f9865f5
 1  fixture-proven but NOT routed     -> add_xp_unit, outside the pool by D6's own definition
 6  routed but NOT fixture-proven     (activate_item_click, buy_premium_account,
                                       darts_new_free, darts_reset,
                                       darts_shoot_balloon, resurrect_hero)
```

The 29 remaining pool branches, ranked by **dedicated** fixture steps:

```
ded  steps  occ   branch (span)
 10     10   11   end_attack            command.py:808-885
  4      4    4   win_daily_bonus       command.py:444-464
  3      3    3   weekly_reward         command.py:345-364
  3      3    3   complete_tutorial     command.py:60-67
  2      2    2   reset_research_item   command.py:293-301
  2      2    2   research_buy_step_cash command.py:276-283
  2      2    2   next_research_step    command.py:268-275
  2      2    2   next_research_item    command.py:284-292
  2      2    2   kill                  command.py:169-182
  1      2    2   sell                  command.py:149-168
  1      2    2   buy                   command.py:42-59
  1      1    1   store_item            command.py:218-232
  1      1    1   set_quest_var         command.py:87-118
  1      1    1   set_goals             command.py:68-75
  1      1    1   sell_stored_item      command.py:250-257
  1      1    1   push_queue_unit       command.py:676-686
  1      1    1   pop_queue_unit        command.py:699-709
  1      1    1   place_stored_item     command.py:233-249
  1      1    1   move                  command.py:119-135
  1      1    1   level_up              command.py:81-86
  1      1    1   kill_iid              command.py:183-188
  1      1    1   expand                command.py:211-217
  1      1    1   end_quest             command.py:752-807
  1      1    1   complete_goal         command.py:76-80
  1      1    1   collect_mission       command.py:430-443
  1      1    1   collect               command.py:136-148
  1      1    1   buy_stored_item_cash  command.py:475-481
  1      1    1   admin_set_quest_rank  command.py:745-751
  0      1    1   add_click             command.py:525-536
  0      1    1   activate              command.py:412-429
```

---

## 3. The assigned candidate, measured: `add_xp_unit`

### 3.1 The span, and a figure conflict across four committed sources

Four committed sources, and they split two-and-two:

| Source | Span |
|---|---|
| `docs/legacy-m13-unrouted-branches.md:246` | `command.py:322-344` |
| `docs/legacy-protocol/commands.json` → `source_references` | `command.py:322-344` (`line: 322`, `end_line: 344`) |
| `apps/compat-api/capture_unit_xp_fixture.py:143` | `command.py:322-343` |
| `apps/compat-api/collection_envelope.py:287` | `command.py:322-343` |
| The assignment brief | `command.py:322-343` |

Measured: the branch header is at **322**, the last **code** line is **343**, **344 is blank**, and the next
`elif` — `weekly_reward` — is at **345**. Under the convention the line-3 record fixed — branch site .. next site
− 1 — the correct figure is **`command.py:322-344`**, and the `322-343` form is "last code line", a different and
less useful quantity. The span is independently corroborated: `weekly_reward` is measured here at
`command.py:345-364`, which is consistent with `345` being the next chain site. **This record uses 322-344.**
No source was edited; the conflict is recorded here and in §10.

### 3.2 The branch body

Read directly (`command.py:322-344`):

```
322      elif cmd == "add_xp_unit":
323          item_index = args[0]
324          xp_gain = args[1]                     # <-- NO CAST. Not even int().
325          level = None
326          if len(args) > 2:
327              level = args[2]
328          
329          item = map_get_item(map, item_index)
330          if not item:
331              print("Error: item not found.")
332              return
333  
334          attr = item[6]
335          if "xp" not in attr:
336              attr["xp"] = xp_gain
337          else:
338              attr["xp"] += xp_gain
339  
340          if level:
341              print(f"{get_name_from_item_id(item[0])} +{xp_gain}xp BOUGHT LEVEL UP -> {level}")
342          else:
343              print(f"{get_name_from_item_id(item[0])} +{xp_gain}xp")
344  
345      elif cmd == "weekly_reward":
```

The award amount reaches the save at exactly one of two lines — **`:336` (assign)** or **`:338`
(increment)** — and the two arms disagree. The branch writes **nothing** but `attr["xp"]`; there is no
`response` local, no unused-argument line, and no second mutation. `args[0]` is resolved through `map_get_item`
at `:329`, confirming it is a **map row key**, not an item id.

Two arms that **disagree with each other**, which is the branch's most distinctive property:

- The **assign arm** (`:336`) persists whatever was sent. The recorded fixture step
  `txn_string_amount_assign_persisted` sends the **string** `"5"` and the save carries `"5"`.
- The **increment arm** (`:338`) uses `+=`, which raises on the same string. The recorded step
  `txn_string_amount_increment_fails` is exactly that: the request raises, **zero leaves change**.

Measured: of the **171** rows in the committed corpus that carry `attr["xp"]`, **171** store a JSON integer
and **0** store a string, float, or bool. So the assign arm's persisted `"5"` is a type the field holds
**nowhere else** in the corpus.

So one branch accepts and persists a type-poisoned value on one code path and 500s on the other. There is no
amount validation, no range check, no type check, and no bound. The third argument is **display-only**: the
`godot-unit-xp` investigation recorded that `[772,5]` and `[772,5,9]` produce an identical `attr_after`, leaf
set and whole-state digest, differing only in the printed line — and this record does not re-measure that, so
it is carried as a *recorded* result, not an independent one. (The committed fixture's own
`txn_level_argument_ignored` step carries the third argument as `9`, which is the recorded basis for that
claim.)

### 3.3 Committed content **does** exist — and the corpus contradicts it

This is the finding that changes the answer, and it runs against the framing the line-3 record used.

**Content exists.** Field-level walk of `packages/game-content/normalized/`:

| File | Field | Carried | Distinct values |
|---|---|---|---|
| `units.json` | `xp` | **429 / 429** units | **24** |
| `units.json` | `collect_xp` | **429 / 429** units | **6** |
| `buildings.json` | `xp`, `collect_xp` | 470 / 470 | — |

So the honest answer to "is there any committed XP content?" is **yes — two candidate fields, on every unit**,
and it is **wrong** to say there is none.

**Nothing reads them.** Raw-substring census over the eleven legacy root `command.py`, `engine.py`, `server.py`,
`sessions.py`, `constants.py`, `get_game_config.py`, `auctions.py`, `version.py`, `get_player_info.py`,
`bundle.py`, `legacy_command_recorder.py`:

| Token | whole-file | code-only | whole-word | quoted |
|---|---|---|---|---|
| `collect_xp` | **0** | **0** | **0** | **0** |
| `max_collects` | **0** | **0** | **0** | **0** |
| `collect_type` | **0** | **0** | **0** | **0** |
| `add_xp_unit` | 1 | 1 | 1 | 1 (`command.py` only) |

**The corpus contradicts both fields.** Of the 33 real save documents, **5** carry at least one row with
`attr["xp"]`; those 5 documents hold **13,034** placed rows of which **171** carry `attr["xp"]` — **all 171 are
committed unit rows**, **0** are buildings, **0** are outside content — spanning **155 distinct stored values**.
Then:

| Comparison | Result |
|---|---|
| stored `attr["xp"]` **equals** committed `units.json` `xp` | **0 of 171** |
| stored `attr["xp"]` **equals** committed `units.json` `collect_xp` | **0 of 171** |

**A derivation keyed on either field is contradicted, not merely unsupported.** This is a stronger negative than
"zero consumers", and it is the reason `add_xp_unit` cannot be a content-anchored authority line even if a
route existed.

**The recorded oracle never sent a committed value either.** Resolving each addressed row through `legacy_id`:

| Step | row key | item id | committed item | `xp` / `collect_xp` | amount sent (verbatim) | 3rd arg |
|---|---|---|---|---|---|---|
| `txn_increment_existing` | 772 | 1007 | Soldier (`type u`) | 3 / 1 | `5` | — |
| `txn_zero_amount` | 772 | 1007 | Soldier | 3 / 1 | `0` | — |
| `txn_negative_no_clamp` | 772 | 1007 | Soldier | 3 / 1 | `-1000` | — |
| `txn_float_amount_persisted` | 772 | 1007 | Soldier | 3 / 1 | `2.5` | — |
| `txn_bool_amount_increments_as_one` | 772 | 1007 | Soldier | 3 / 1 | `True` | — |
| `txn_string_amount_increment_fails` | 772 | 1007 | Soldier | 3 / 1 | `'5'` | — |
| `txn_unbounded_amount` | 772 | 1007 | Soldier | 3 / 1 | `1000000000000` | — |
| `txn_level_argument_ignored` | 772 | 1007 | Soldier | 3 / 1 | `5` | `9` |
| `txn_assign_absent_key` | 1783 | 1050 | Medic (`type u`) | 10 / 1 | `7` | — |
| `txn_string_amount_assign_persisted` | 1783 | 1050 | Medic | 10 / 1 | `'5'` | — |
| `txn_building_row_type_agnostic` | 3 | 23 | Wall I (`type b`) | 1 / 0 | `11` | — |
| `txn_missing_row` | 999999 | *(no row)* | — | — | `5` | — |

The corpus's committed XP for a Soldier is **3**. The twelve recorded amounts are
`7, True, 11, 2.5, 5, 5, 5, -1000, '5', '5', 1000000000000, 0` — **nine distinct values**, and **not one of
them equals `3`**. Same for Medic (committed `10` → sent `7` and `'5'`) and for Wall I (committed `1` → sent
`11`). The fixture is a deliberate adversarial set, which is exactly what makes it good evidence about
validation and useless as evidence about an amount.

`txn_level_argument_ignored` carries the third argument as `9`, which is the recorded basis for the
display-only claim in §3.2.

### 3.4 The derivation path **exists** — and was not taken for XP

This is the sharpest form of the finding, and it is stronger than either "no content" or "zero consumers".

`get_game_config.py:123` defines a generic committed-attribute accessor:

```python
def get_attribute_from_item_id(id: int, attribute_name: str) -> str:
    item = get_item_from_id(id)
    ...
```

The legacy server **does** use it, and the set of committed attributes it has ever read this way is exactly
**four**:

| Attribute | Read at |
|---|---|
| `clicks_to_build` | `engine.py:26` |
| `properties` | `engine.py:18`, `engine.py:154` |
| `name` | `get_game_config.py:128` (inside `get_name_from_item_id`) |
| `sm_training_time` | `command.py:735` |

**`xp` is not among them. `collect_xp` is not among them.** So the machinery to read a committed per-unit
attribute is proven, was used three times for three different attributes, and was **not** used for XP. That
distinguishes two very different situations — a field nobody could have read, versus a readable field the
server never read — and it is the situation `add_xp_unit` is in.

It also means the §3.3 conclusion is *robust to the accession question*: even granting that a derivation path
exists, the corpus still contradicts the field it would read.

### 3.5 Verdict on the assigned candidate

`add_xp_unit` fails on three independent, separately sufficient grounds:

1. **No request path.** It is the only fixture-proven branch in the repository that no route dispatches. It is
   outside the D6 pool by the pool's own definition, and an M13 line that serves it must **invent a client
   surface** for a transaction no client can currently make.

   This is not merely an absence — it is **enforced by a delivered guard**. `apps/compat-api/tests/
   test_unit_xp_fixture.py:129` declares:

   ```python
   # Route paths that would mean this line grew the endpoint it explicitly excludes.
   UNIT_XP_ROUTE_FORBIDDEN_SUBSTRINGS = ("unit_xp", "unit-experience", "add_xp_unit")
   ```

   The `godot-unit-experience` line did not merely decline to route this branch; it **wrote a test that fails
   if any route path mentions it**. A line 4 that routed `add_xp_unit` would therefore have to amend an
   archived line's guard before it could start — which is the same situation this project records avoiding when
   a later line touches `collect` or a count pin. The cost is small and the decision is the orchestrator's; the fact is what makes this ground real rather
   than rhetorical.

2. **No content-anchored derivation.** Its two candidate committed fields are contradicted by the corpus in
   **171 of 171** comparable rows and read by **zero** legacy sites, while a proven accessor exists that would
   have read them.
3. **A refusal with nothing to replace.** A v1 line here could refuse the unvalidated amount and would have no
   committed value to pay instead. That is a real authority improvement — the amount is genuinely unvalidated
   and the assign arm genuinely poisons a save — but it is a refusal line on a new surface, not a tightening of
   an existing one.

Its **fixture depth is the strongest in the repository** — 12 dedicated steps, robust under both dedicated
rules, and the top row of §2.4's rival table. That is a real asset and it is why the branch stays on the
record. It is not sufficient.

---

## 4. Content availability for the whole remaining pool

The decisive observation for line 4 is a **negative across the board**.

The line-3 ordering rule put **criterion 1 first: a content-anchored derivation exists.** Applying it to all 29
remaining pool branches, **none passes**:

| Branch | Committed content a derivation would read | Legacy reads of it | Corpus verdict |
|---|---|---|---|
| `end_attack` | none | `defense`, `life`, `attack_interval`, `attack_range`, `best_against` all **0** whole-word; `attack` **12** whole-file / **5** code-only / **0** whole-word | — |
| `win_daily_bonus` | `globals.json` `DAILY_GOLD_REWARDS` (5 rows) | **0** under all four rules | ladder is gold-only; the branch's actual grant is a client-sent item |
| `weekly_reward` | `globals.json` `MONDAY_BONUS_REWARDS` (3 rows) | **1** whole-word — the only reward ladder with a real read | what the read yields is a cycle length, not a payout |
| `set_goals` | `quests.json` 91 rows, ids `1..91` contiguous | `reward` carried on 91/91 and uniform `10` | line 3 measured populated indices beyond 91 in the corpus; a membership test would refuse corpus-real states |
| `next_research_step`, `next_research_item`, `reset_research_item`, `research_buy_step_cash` | **none** — **0** research-bearing keys in the whole normalized package | — | — |
| `buy` | `costs` — **0** occurrences | 0 | — |
| `move` | `velocity` — **0** occurrences | 0 | — |
| `activate` | `build_time` / `buildTime` — **0** occurrences | 0 | — |
| `push_queue_unit` | `training_time` — **3** occurrences, all in `command.py`, and inside `sm_training_time` | substring artifact | — |
| `pop_queue_unit` | `sm_training_time` — **3** whole-word, `command.py` only, read by the *soul mixer*, not by this branch | 3 | — |
| `add_click` | `clicks_to_build` — read **once** at `engine.py:26`, as the **seed** `attr["nc"] = 0`, not as a threshold | 1 | two distinct values, both `0` |
| `store_item`, `sell`, `sell_stored_item`, `buy_stored_item_cash`, `place_stored_item` | none | 0 | — |
| `kill`, `kill_iid`, `end_quest`, `collect_mission`, `set_quest_var`, `admin_set_quest_rank`, `complete_goal`, `complete_tutorial` | none | 0 | `complete_goal` and `kill_iid` mutate nothing at all |
| `expand`, `level_up` | committed, but **already derived** by delivered capabilities | — | not re-offered |
| `collect` | committed, but **delivered** (line 1) | — | not re-offered |

**Therefore line 4 must be a refusal line.** That is the finding, and it is a program-level one: the M13 D6 pool
now holds 29 branches and **not one of them has a committed value that names its outcome**. Every content-
anchored line (lines 1–3: `collect`, `complete_collection`, `buy_magic`/`use_magic`) is already delivered.

Two counting traps worth recording, both of which would have produced a wrong answer:

- **`attack` is not a consumer.** Its 12 whole-file occurrences sit inside longer identifiers — `end_attack`,
  `attacker`, `attacker_units`, `flash_reload_attack` — and its whole-word count is **0**. Reported as 5
  code-only, and as 12 whole-file, it looks like a read.
- **`training_time` is not a distinct field at the site that reads it.** The 3 occurrences are inside
  `sm_training_time`.

---

## 5. Ranking

The line-3 ordering rule is reused unchanged, so the two records are comparable:

1. **Content-anchored derivation exists.** — **dead for all 29** (§4).
2. **The stored outcome is already server-computed**, so authority tightens an existing rule.
3. **Fixture depth**, measured as dedicated steps.
4. **A live v0 route already exists** to replace.
5. **A measured unbounded or unvalidated client input** that a refusal would close.

With criterion 1 exhausted, the order is decided by 2–5, and criteria 3 and 4 point the same way:

| # | Branch (span) | C1 | C2 client-dictated outcome | C3 route | C4 fixture (steps/ded/occ) | C5 content |
|---|---|---|---|---|---|---|
| **1** | **`end_attack`** (808-885) | **N** — the branch's only mutation is a client-computed count | `args[0]` is a **JSON blob** (`:813`) carrying `attacker_units`; per tuple, `lost = max(0, unit[2] - unit[3])` at **`:868`** → `map_lose_item(map, privateState, unit[0], lost)` at **`:872`**: the item id **and** the count both arrive from the client | `/v0/combat` (`combat_envelope`, 3 actions) | **10 / 10 / 11** | **none** |
| 2 | `win_daily_bonus` (444-464) | P — cursor clamped `>5 → 1`, `:451-452` | `args[0]` → item into storage, `:445`/`:460`; `args[1]` → next id, `:446` | `/v0/reward` | 4 / 4 / 4 | `DAILY_GOLD_REWARDS`, **0** reads, linkage **name-only**, index base unresolved |
| 3 | `weekly_reward` (345-364) | P | `args[0..4]` → item index/id/x/y/team → `map_add_item`, `:347-353` | `/v0/reward` | 3 / 3 / 3 | `MONDAY_BONUS_REWARDS` — read, but only for a cycle length |
| 4 | the four research branches (268-301) | S / N | track unbounded in all four; `research_buy_step_cash` reads a cash value and **discards** it, `:277` | `/v0/research` | 2 / 2 / 2 each | **none** |
| 5 | `set_goals` (68-75) | N | `args[0]` index and `args[1]` JSON progress; no upper bound | `/v0/quests` | 1 / 1 / 1 | `quests.json` refuted by the corpus |
| 6 | `complete_tutorial` (60-67) | N | `args[0]` step; gate `>=25 or ==15`, `:63` | `/v0/tutorial` | 3 / 3 / 3 | no committed step count |
| 7 | `expand`, `level_up` | N | — | routed | 1 / 1 / 1 | already derived by delivered capabilities |
| 8 | `buy`, `move`, `activate`, `add_click`, `store_item`, `sell`, `kill`, `place_stored_item`, `sell_stored_item`, `buy_stored_item_cash`, `push_queue_unit`, `pop_queue_unit` | mixed | see §4 | routed | ≤ 2 | zero-consumer decisive fields |
| 9 | `end_quest`, `collect_mission`, `set_quest_var`, `admin_set_quest_rank`, `complete_goal`, `kill_iid` | N / inert | — | routed | 1 / 1 / 1 | none; `complete_goal` and `kill_iid` write nothing |

---

## 6. Recommendation

### 6.1 The target: `end_attack` at `/v0/combat`

It wins on three of the four surviving criteria and loses on none. Read fresh, not inherited:

**R1 — fixture depth, the best in the pool.** **10 steps, 10 dedicated, 11 occurrences** — the second-strongest
fixture in the repository behind `add_xp_unit` alone, and it is **in** the pool. It is the only branch that is
both top-two on fixtures and routed.

**R2 — a live route exists to replace.** `/v0/combat` with `combat_envelope.ACTIONS = (resolve, kill,
kill_iid)`. This is criterion 4, and it is the criterion `add_xp_unit` fails outright.

**R3 — the worst client input in the pool, and it is a destruction.** The branch's entire stored effect is
one call. Everything else is a local:

| Verified | |
|---|---|
| `args[0]` JSON-parsed | `:813`, with `args[1]` read into `unknown` and never used, `:810` |
| distinct fields copied out of the client blob | **12** (`:839-862`) |
| `lost = max(0, unit[2] - unit[3])` computed **inside the blob** | `:868` |
| `map_lose_item(map, privateState, unit[0], lost)` | `:872` — the branch's only state mutation |
| other `map_*`/`add_*`/`pop_*`/`set_*` calls in the body | **0** |
| `map_lose_item` call sites in the whole legacy source | **2**: `command.py:796` (`end_quest`) and `command.py:872` |

Both the **item id** and the **number of rows destroyed** are client-dictated, and the destruction is not
bounded by anything in the save. `map_lose_item` (`engine.py:215-228`) additionally pushes every destroyed row
onto the dead-hero ledger via `push_dead_unit` (`:223`), so one client request writes **two** pieces of
authoritative state. Line 3 already recorded the recorded probe for the twin branch: `end_quest` with
`units = [[26, 0, 1, 0]]` made the **legacy** server destroy a placed row, 40 → 39, while the modern endpoint
derives `units: []` and destroys none. That divergence is a delivered precedent, not a new invention.

**Two further unguarded paths, verified in the body** — recorded because they bear on the refusal surface, and
because they are facts about the branch rather than about a proposal:

- `attacker_units` is initialised to `None` at `:837` and dereferenced at `:866` with `for unit in
  attacker_units:`. The assignment at `:857-860` is conditional on the key being present, so an **absent** key
  yields `for unit in None` — a `TypeError`, with no guard. The `None` initialiser is what makes this reachable.
- `victim` is initialised to `None` at `:827` and dereferenced at `:874` with `if "name" in victim:` — same
  shape.

**R4 — the refusal shape is already shipped once.** `godot-quests` delivered the identical client-dictated
destruction refusal for `end_quest`, whose only mutation is `map_lose_item` at `command.py:796` — measured here
as the *only other* call site. The design is proven; line 4 repeats it once more on the branch where the count
is computed even further from the server.

**The shape of a v1 line, stated only as far as it constrains ranking:** derive the destruction set server-side
(or refuse it), refuse a blob that does not carry the fields the branch requires, and report what the client
sent without acting on it. **No rule above is approved by this file.**

**And the honest limit, stated up front:** this line would deliver **no derivation at all**. §4 is the reason.
`end_attack` is the strongest available, not a strong target, and line 3 said the same thing about
`buy_magic` before it was chosen.

### 6.2 Every rival, and why it lost

**`win_daily_bonus` (rank 2) — lost on linkage, not on size.** Its content case is weaker than it looks:
`DAILY_GOLD_REWARDS` has 5 rows and **zero** legacy reads under all four counting rules, so the correspondence
between the branch and the ladder is **name-only**. The branch's own clamp `next_id > 5 → 1` (`:451-452`) is a
1..5 cycle while the ladder is naturally indexed 0..4, and line 3 measured the corpus recording a value the
branch cannot produce. Decisively, the committed vector is **gold only** with no item column, so the branch's
actual grant — a client-sent item id dropped into storage at `:460` — has **nothing to derive from**. A refusal
with no replacement, against 4 dedicated steps instead of 10.

**`weekly_reward` (rank 3) — lost on a measured hole, despite being the best-linked ladder.**
`MONDAY_BONUS_REWARDS` is one of only **2 of 105** `globals.json` keys with any legacy read (§10 corrects line
3's 4). But what the read yields is a **cycle length**, not a payout: the long arm grants a client-sent item and
the short arm grants nothing at all. The modulus is 5 over a 3-row table, and `weeklyRewardIndex = 3` is
recorded in the corpus — a state the content cannot describe. A v1 line must either refuse a reachable,
corpus-real state or invent a fifth row.

**The four research branches (rank 4) — lost because there is no committed research content at all.** Measured
in this record: **0** research-bearing keys in the entire 23-file normalized package. Four branches would yield
four refusals and no derivation, at 2 dedicated steps each.

**`set_goals` (rank 5) — lost because the committed set does not bound the corpus.** `quests.json` has 91 rows
with contiguous ids, which looks like a perfect bound, and line 3 measured the corpus **refuting** it. The
branch also has **two index spaces in one body** — `get_attribute_from_goal_id` maps id → position while
`engine.set_goals` writes by id.

**`complete_tutorial` (rank 6) — lost because a step count would be invented.** 3 dedicated steps is respectable
and the branch's write is real, but no committed total exists, and a `total_steps()` helper is precisely the
invention this project records as having been proven to fail a guard.

**Everything at rank 7 and below — lost because it is already delivered, inert, or has nothing to derive.**
`expand` and `level_up` are already derived by delivered capabilities. `complete_goal` and `kill_iid` mutate
**nothing at all** — there is no state to be authoritative about. `buy`, `move`, `activate`, `add_click`,
`store_item`, `sell`, `kill`, `place_stored_item`, `sell_stored_item`, `buy_stored_item_cash`,
`push_queue_unit`, `pop_queue_unit` all have zero-consumer decisive fields, measured in §4.

**`add_xp_unit` — the strongest fixture in the repository, and still the wrong line.** §3.3: its content is
contradicted by **171 of 171** corpus rows. §3.4: the accessor that could read it exists and was used three
times for other attributes. §2.2: it has **no request path** at all, so it is outside the D6 pool by the pool's
own definition. Line 3 rejected it on routing alone and said unrouting it "would be a different line"; this
record agrees, and adds that unrouting would not have rescued it.

---

## 7. Rejected alternatives

| Rejected | Reason |
|---|---|
| **`add_xp_unit` — the single strongest fixture in the repository (12 dedicated steps, robust under both dedicated rules)** | **No request path** (measured: dispatched by no executed builder; zero quoted literals in 21 envelope modules), so it is outside the D6 pool. And its committed fields are **contradicted by the corpus in 171 of 171** comparable rows, so there is no derivation to make authoritative. Serving it means inventing a client surface for a transaction no client can currently make. |
| **Any other unrouted branch** (23 remain: `flash_debug`, `fast_forward`, `ping`, `set_variables`, `buy_powerups`, `orient`, `pop_unit`, `push_unit`, `batch_remove`, `store_add_items`, `add_inventory_item`, `remove_inventory_item`, `buy_offer_pack`, `buy_si_help`, `finish_si`, `set_resource_allies`, `trade_resource`, `soulmixer_speedup`, `rt_open_graph_unit`, `first_time_marketplace`, `unit_collections_completed`, `buy_mana_new`, `push_queue_unit2`) | **None is fixture-proven** except `add_xp_unit` — so there is no parity evidence for any of the other 23, and M13's own claim limits forbid claiming parity without an oracle. |
| **The `/v0/research` route as a route-level target** | One route, four branches, **zero** committed content. A route-level line delivers four refusals and no derivation — and three of the four have **0** dedicated steps beyond the shared scaffold. |
| **The `end_attack` + `end_quest` pair as one line** | `end_quest`'s equivalent refusal is **already delivered** by `godot-quests`, including a recorded divergence against the legacy oracle. Re-delivering it would be a second surface for one decision. `end_attack` alone is the un-delivered half. |
| **Widening `DAILY_GOLD_REWARDS` / `ALLIANCE_DAILY_BONUS_REWARDS` into the picture** | Both zero-consumer; their link to any branch is name-only. Naming them in a proposal would present an inference as a finding. |
| **Choosing by "most client-dictated"** | Measured: the branches with the worst client input are exactly the ones with no committed content. That criterion selects refusal-only lines — which §4 shows is now **every** option, so it cannot break the tie. |
| **Normalising `units.json` `xp` / `collect_xp` into a client-readable schedule** | The corpus contradicts both fields in **171 of 171** rows. Publishing them as a schedule would surface a committed number that the recorded oracle demonstrably never used, and invite a client to award against it. Out of scope for target selection regardless; recorded, not decided. |
| **A line that pays unit XP at all** | No committed rule exists to pay from, and the corpus contradicts the two candidate fields. An XP award would be invented from end to end. |

---

## 8. Unknowns — figures this investigation did **not** establish

- **Whether the client-sent `attacker_units` blob was ever shaped differently.** Nothing in the preserved
  server constrains it; the 12 field names are the branch's own defaults, not a contract.
- **Whether `end_attack`'s two unguarded `None` dereferences (`:866`, `:874`) are reachable in practice.** The
  code path is reachable by construction; whether a real client omitted either key is **unknown**, and this
  record did not execute a probe against it.
- **The correct index base of `DAILY_GOLD_REWARDS`.** Line 3 recorded it as unresolved and this record did not
  re-measure it; the branch cycles `1..5` against a naturally `0..4` ladder.
- **The provenance of the 155 distinct stored `attr["xp"]` values.** They were written by some path — no legacy
  branch other than `add_xp_unit` writes them, and it accepts client amounts — but **which** client wrote what,
  and when, is not recoverable from the committed corpus.
- **Whether any committed save document outside the 33 walked here exists.** Only `villages/`,
  `tests/saves/` and `saves/` were walked.
- **What the Flash client actually did.** Every zero-consumer and zero-occurrence figure in this record is a
  statement about the **preserved server**, and says nothing about what the Flash client sent, displayed, or
  expected. `add_xp_unit`'s 12-step fixture is the closest thing to client evidence in this repository, and it
  is deliberately adversarial rather than representative.
- **Whether `attr["xp"]` has any consumer outside the 11 root modules.** A web client, a tool, or a mod could
  read it; the census covers the server.

---

## 9. Instrument faults in my own measurements

A defective instrument is discarded, not reported as a result. Four of these changed an answer.

1. **The first execution harness was a flat addressing dict.** Guessing one calling convention for every
   envelope module produced **27 loud failures** and an undercount of **21** dispatched branches. Not an
   undercount of the pool — a broken instrument. Discarded. Signatures were then read from
   `inspect.signature` and **8** loud failures remained, fixed by using legacy **vector tokens** (`c`, `w`) in
   `costs` and by recognising that `combat` and `quest` addressing is a **scalar**, not a dict. Final run: **40
   calls, 0 loud failures.** The 21 was never reported.

2. **The fixture occurrence counter double-counted.** `for b in pool_hits: occ[b] += batch.count(b)` iterated
   the batch, so a step carrying a branch **twice** was counted four times. `end_attack` read **13** instead of
   **11**. Fixed by iterating `set(pool_hits)` and counting once per step. **This record's occurrence figures
   are post-fix**; the 13 was discarded.

3. **The raw parse rule R1, as described in the line-3 record, fires 0 of 104 times.** My first implementation
   substituted `\u007b`/`\u007d` in the raw `form.data` text — but these fixtures escape their braces as
   `\"`, not `\u`, so the extracted tail began with a backslash and `json.loads` always raised. Corrected by
   decoding the extracted literal **as a JSON string** (`json.loads('"' + captured + '"')`), which yields 78 of
   104 and agrees with R2 on every branch set. **The rule as written is discarded**; the corrected rule is what
   §2.3 reports.

4. **The anchor analysis resolved `args[0]` as an item id.** It is a **map row key**. The first pass reported
   ids `772` and `1783` as "NOT FOUND in units/buildings/specials" and nearly produced the false conclusion that
   the addressed items were outside content. Re-read of the branch body (`map_get_item(map, item_index)`) and of
   the fixture's own before/after rows showed key `772` holds item **1007** (Soldier) and key `1783` holds item
   **1050** (Medic). **The corrected resolution is what §3.3 reports**, and the "not in content" reading is
   discarded — it was an artefact of the wrong join key, not a corpus fact.

5. **The attribute-name extraction ran over code-stripped text.** `get_attribute_from_item_id(…, "xp")` was
   searched in the lexer-stripped body, where string literals are blanked, so the extraction returned **0**
   attributes and briefly looked like "the accessor was never used". Re-run over raw text it returns the four
   real attributes. **The zero was discarded.**

6. **`uses after assignment` over-counted.** The per-field "is the blob field used" tally counted the
   pre-initialiser lines (`:826-837`), reporting 2 uses for fields that are in fact never read after
   assignment. The structural facts §6.1 relies on were instead read directly off the branch body line by line,
   and §6.1 states them from that read.

7. **A verbatim code block was reconstructed from a summary instead of from the source — and was wrong.**
   The first draft of the §3.2 block carried three lines the branch does not contain (a `response = None`
   local, an `unknown = args[2]` line, and a different not-found message), had **every line number after `:325`
   shifted by one**, and put `attr["xp"] += xp_gain` at `:337` instead of `:338`. Caught by re-reading
   `command.py:320-346` and discarded. The corrected block is transcribed from the source. The **span**
   conclusion was unaffected and was independently confirmed by the same read: header at `322`, last code line
   `343`, blank `344`, and the next `elif` — `weekly_reward` — at **`345`**, which also matches the span
   independently recorded for `weekly_reward` at `command.py:345-364`.

8. **The fixture-amount table was transcribed from a truncated console read and mis-stated three amounts.**
   The first pass reported `txn_increment_existing` as `11` (actually `5`),
   `txn_building_row_type_agnostic` as `7` (actually `11`), and `txn_missing_row` as carrying no amount
   (actually `5`). Re-run over the committed requests with `repr()` per amount and the full 12-row table
   rebuilt. **The conclusion is unchanged** — no recorded amount equals the addressed unit's committed `xp`,
   which is the only thing the table is cited for — but three figures were wrong and are corrected here
   rather than left standing. A table built from truncated console output is the same defect as one built from
   prose.

9. **A committed column that looks like a fixture census and is not.** `docs/legacy-protocol/commands.json`
   carries `observed_fixtures` per branch, and `add_xp_unit`'s row reads **`[]`** with
   `evidence: "Source inspection only; no focused behavioral evidence."` — while
   `tests/fixtures/godot-unit-experience/` holds **12 dedicated steps** for exactly this branch. The obvious
   reading is "the catalog is stale", and §10 originally recorded that as a correction before the column's
   meaning was checked. It is **not** stale under its own definition: `observed_fixtures` is non-empty for only
   **4 of 64** rows (`complete_tutorial`, `level_up`, `ping`, `set_variables`), and every populated value is the
   *same prose string* about `tools/protocol-replay` recorder-v1 eligibility. The column records **replay
   eligibility, not the existence of a captured fixture**. The `[0]` is correct, and the "stale catalog"
   correction is **withdrawn** — it would have been a false claim about a committed document, produced by
   reading a field's name instead of its contents. This is the third time in this file's own history that a
   promising-looking count turned out to measure something else.

---

## 10. Corrections to inherited figures

A falsified claim is withdrawn, not quietly edited. No file outside this one was modified.

1. **The "two rules agree exactly" claim in `docs/legacy-m13-line3-candidates.md` §2.3 is withdrawn as stated.**
   The R1 rule as described there — un-escape `\u007b`/`\u007d` — **fires 0 of 104** times against the committed
   fixtures, whose braces are `\"`-escaped. A rule that never fires cannot corroborate another rule, so the
   agreement was vacuous as recorded. The underlying figure of **34** is **not** affected: it reproduces exactly
   under R2, and under a corrected R1 that agrees with R2 on every branch set. What is withdrawn is the claim
   of corroboration, not the number.

2. **`docs/legacy-m13-line3-candidates.md` §5.1 "4 of 105 `globals.json` keys with any legacy read" is
   withdrawn; the measured figure is 2.** `ALLIES_BUILDING` and `ALLIES_MARKET` are **substring artifacts**:
   their sole occurrences are inside the *different* identifiers `ID_BUILDING_ALLIES_MARKET`
   (`constants.py:234`) and `ID_BUILDING_ALLIES_BUILDING` (`constants.py:235`), where
   `\bALLIES_BUILDING\b` does not match. Under the whole-word rule, only `MONDAY_BONUS_REWARDS` and
   `PREMIUM_ACCOUNTS` have a legacy read — **2 of 105**. This is the same substring trap the M8 combat record
   measured for `attack`, in a different file.

3. **The `end_attack` dedicated-step figure is rule-dependent, and the rule was unstated.** Measured **10**
   under "carries this branch and no other **branch**" and **9** under "carries this branch and no other
   **occurrence**", because `txn_resolve_batch_discarded_on_raise` carries `end_attack` **twice**. The line-3
   record quotes **10 / 9 / 11**; the order it presents is steps/dedicated/occurrences, so the 9 and the 10 are
   both correct under their own rule and the ambiguity was never resolved in prose. **This record uses 10**
   (branch-set difference) and states the rule. `add_xp_unit` is 12 under **both** rules, so the figure that
   mattered for §3 is unaffected.

4. **The `add_xp_unit` span is contested across four committed sources and this record resolves it to
   `command.py:322-344`.** `docs/legacy-m13-unrouted-branches.md:246` and
   `docs/legacy-protocol/commands.json` (`source_references: line 322, end_line 344`) both say 322-344;
   `capture_unit_xp_fixture.py:143` and `collection_envelope.py:287` both say 322-343. Measured: header 322,
   last code line 343, 344 blank, next `elif` 345. Under the line-3 span convention the answer is **322-344**,
   which is also the majority answer among committed sources. **The 322-343 sources are not corrected here** —
   they belong to `godot-unit-experience`, and reworking an archived line's recorded span from a selection
   record is exactly the kind of unearned fix this project records avoiding.

5. **`docs/legacy-m13-line3-candidates.md` §8's "An unrouted branch (**19** remain …)" understates the
   unrouted total.** Measured unrouted is **24**. All 19 names it lists are genuinely unrouted — **0** of them
   are wrong — but the list omits the **5** named-but-not-dispatched branches (`buy_mana_new`,
   `buy_offer_pack`, `fast_forward`, `push_queue_unit2`, `store_add_items`) that §2.2 of the same record had
   already identified. "19" is a subset, not the total.

6. **A corpus-denominator difference, recorded rather than resolved.** The `AGENTS.md` record for
   `godot-unit-experience` states **171 of 12,954 placed rows across 5 of the 31 committed save documents**.
   This record measures **171 of 13,034 rows across 5 of 33 documents**. The **numerator (171)** and the
   **document count (5)** reproduce exactly; the two denominators do not. The likely cause is the two documents
   outside `villages/` and a corpus that has grown since. The discrepancy is recorded, not explained — this
   investigation did not measure what changed.

---

## 11. Claim limits

- **This file selects a target. It delivers no authority, no route, no refusal, and no spec.**
- **The recommended line would deliver no derivation.** §4 is the measurement behind that: **0 of 29** remaining
  pool branches have a committed value naming their outcome. `end_attack` is the strongest available, and
  "strongest available" is not the same as "good".
- **No parity is claimed against a live legacy server.** Everything measured here is source, committed content,
  committed fixtures, and in-process execution of the Compatibility API's own envelope builders. The legacy
  server was **not** started.
- **The executed builders are the Compatibility API's, not a network surface.** Measure A establishes which
  branches a request path *would* send; it does not establish that a real client sent them.
- **Fixture figures are over the committed corpus only.** 12 dedicated steps for `add_xp_unit` is evidence
  about the recorded oracle, not about any player's experience, and that fixture set is deliberately adversarial
  (string, float, bool, negative, 10¹² amounts) so it says nothing about a real award.
- **Every zero is rule-scoped.** "Zero consumers" means zero under the named rule over the named eleven root
  modules. It does not mean the Flash client, a mod, a tool, or a web client never read the field. In
  particular, `add_xp_unit`'s **12** field names and `collect_xp`'s zero reads are statements about the
  preserved server only.
- **The committed `xp` and `collect_xp` fields are reported, never adopted.** Their contradiction by the corpus
  is measured over **171** comparable rows in **5** documents. That is a strong negative for *deriving an award
  from them*; it is **not** a claim that the fields are meaningless, and no other consumer of them is ruled
  out.
- **The two unguarded `None` dereferences in `end_attack` are recorded as code facts.** Whether a real client
  triggered either is **unknown** (§8).
- **No ordinal is claimed** for any zero-consumer count. Four earlier records in this project each numbered
  that class over a different scope, and a fifth number would not be comparable.
- **Line 3's rejections of `weekly_reward`, `win_daily_bonus` and `end_attack` were re-measured only where this
  record's own selection depended on them** (§4, §6.2). Where a figure is carried from line 3 rather than
  re-measured — the `DAILY_GOLD_REWARDS` index base, the `set_goals` populated indices, the `end_quest` probe —
  it is marked as a recorded result, not an independent one.
- **Nothing here is approved.** Every refusal, every derivation, and every route named above would have to be
  re-argued in a proposal.
- The recorded flaky surfaces remain open; this file claims **no ordinal** for them. And one more applies here:
  this record's own `git status --short` was clean **before and after**, which is the only evidence about file
  containment that this investigation can offer.
