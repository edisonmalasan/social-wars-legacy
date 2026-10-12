# M13 line 2 — the unrouted-branch surface, measured

**Status:** investigation only. No OpenSpec change is proposed by this document
and no implementation follows from it. It exists to answer the question the
`server-v1-authority-boundary` line left open: *which* of the branches with no
route behind either server should Server v1 port first, and on what evidence.

**Scope:** the 63 named `command.py` dispatcher branches, the 24 `/v0`
Compatibility API routes, and Server v1's single delivered route. Every figure
below was measured in this working tree on 2026-10-13; the commands used are
recorded with their results so the numbers can be re-derived rather than
trusted.

---

## 1. Headline

| Figure | Value | Instrument |
| --- | --- | --- |
| Named dispatcher branches | **63** | `tools/command-catalog/verify_commands.py` (`result: agreement`, exit 0) |
| `/v0` routes | **24** | `tools/route-coverage/verify_route_coverage.py` (`routes: 24`) |
| Routes that dispatch a branch | **22** | measured, §3 |
| Branches a route dispatches | **40** | measured, §3 |
| **Branches no route dispatches** | **23** | measured, §3 |
| Branches with an authoritative v1 route | **1** (`collect`) | `apps/server-v1/` |

**The recorded figure of 39 unrouted branches is an overstatement and is
corrected to 23** (§2).

The 23 partition cleanly into six groups. **Only one branch is a port
candidate**, and the group counts below sum to 23 by measurement, not by
construction:

| Class | Count | Branches | What v1's answer is |
| --- | --- | --- | --- |
| A — catalog-classified must-not-migrate | 2 | `flash_debug`, `fast_forward` | refusal, never a route |
| B — the branch writes nothing | 3 | `ping`, `set_variables`, `buy_powerups` | nothing to make authoritative |
| C — unbounded client-dictated grant or destruction | 6 | `store_add_items`, `batch_remove`, `pop_unit`, `push_unit`, `add_inventory_item`, `remove_inventory_item` | refusal, never a route |
| D — client-sent value, no committed rule | 7 | `orient`, `trade_resource`, `first_time_marketplace`, `rt_open_graph_unit`, `unit_collections_completed`, `add_xp_unit`, `soulmixer_speedup` | refusal, never a route |
| E — already owned by a delivered capability's refusal | 4 | `buy_si_help`, `finish_si`, `set_resource_allies`, `push_queue_unit2` | already decided; a second surface would drift |
| **F — committed content supplies both the selector and the answer** | **1** | **`buy_offer_pack`** | **port candidate** |
| | **23** | | |

---

## 2. Correction: 39 → 23

`docs/legacy-m13-collect-v1.md:115-117` records:

> This slice says nothing about the other 39 uncited legacy command branches.
> `tools/route-coverage/` reports 24 of 63 branches covered by a v0 route and
> 39 uncovered; this line covers exactly one of the 24.

The first sentence is correct and is what this document is about. The second
sentence misreads the instrument, and **the "39 of 63 branches covered" figure
it repeats is a citation count, not a coverage count**.

`tools/route-coverage/verify_route_coverage.py` states its own rule in its
output (`evidence_policy`):

> A branch is COVERED only when the route handler's own source cites it with a
> command.py:NNN line span resolving inside the branch span. A backticked
> branch name in a docstring is NOT coverage: it shows the handler CITES the
> branch, not that it implements it, and handlers routinely name a branch to
> contrast themselves with it.

That is a defensible, deliberately conservative rule — and it is the wrong rule
for the question "does a route dispatch this branch". The tool measures
*documentation*, and the sentence inherited from it silently promoted that into
*implementation*.

The gap is exactly measurable in both directions, and both directions were
measured:

- **The tool's uncovered set is a strict superset of the truly undispatched
  set.** All **23** branches no route dispatches appear in the tool's 39
  `branches_without_cited_route`. **Zero** disputes in that direction.
- **16** branches the tool files as uncovered *are* dispatched, their handlers
  simply do not cite them with a `command.py:NNN` span: `activate_item_click`,
  `add_click`, `admin_set_quest_rank`, `buy`, `buy_mana_new`,
  `buy_premium_account`, `buy_stored_item_cash`, `collect_mission`,
  `complete_goal`, `darts_new_free`, `darts_reset`, `next_research_item`,
  `pop_queue_unit`, `research_buy_step_cash`, `reset_research_item`,
  `use_magic`.

The tool is not wrong and is **not** to be changed: it answers the question it
was built to answer, and its own output already carries the permissive reading
(`branches_covered_permissive_reading: 37`,
`branches_without_cited_route_permissive_reading: 26`) alongside the
conservative headline. What was wrong was one sentence that read the headline as
a coverage claim. `26` is the tool's own closest answer to the real figure and
it is still **3 high**, because a name-only mention is weaker evidence than an
executed envelope builder.

**Nothing else in that sentence changes.** "this line covers exactly one of the
24" is correct and unaffected, and the route count of 24 is correct.

---

## 3. How the dispatch map was measured

Three instruments were built and **two of them were discarded**. They are
recorded here because a measurement whose instrument is defective must never be
reported as a finding.

**Discarded — quoted-token scan.** Matching each branch name as a quoted literal
inside `compat_service.py` reported **3 covered / 60 uncovered**. That is
impossible against 22 mutating routes, and the cause is mechanical: no route
handler names a legacy command as a quoted literal. Each route delegates to a
per-line envelope module that holds the name in a `*_COMMAND` constant. The
instrument measured the wrong file.

**Discarded — module-constant scan.** Scanning every `*_envelope.py` for
`*_COMMAND` constants and attributing each module's names to whichever route
used it reported **44 covered / 19 uncovered**. This over-counts because a
module's constant table names branches the route *refuses* or names only to
contrast itself with — `magic_envelope` carries `buy`, `store_envelope`'s
handler mentions `buy_stored_item_cash` in prose, and `stored_placement_envelope`
carries `store_add_items` while the route declines it.

**Accepted — executed builders plus declared action tables.** For each route,
the branch actually placed into the legacy batch was read out of the value the
envelope builder *returns*, and for the multi-action envelopes from the
module's own declared `ACTIONS` tuple / `command_for_action` mapping. This is
stronger than any text scan because it observes the constructed batch rather
than reading a name.

| Route | Branch(es) dispatched |
| --- | --- |
| `/v0/tutorial` | `complete_tutorial` |
| `/v0/place` | `buy` |
| `/v0/upgrade` | `sell`, `buy` |
| `/v0/sell` | `sell` |
| `/v0/move` | `move` |
| `/v0/store` | `store_item` |
| `/v0/construction` | `activate`, `add_click`, `activate_item_click` |
| `/v0/collect` | `collect` |
| `/v0/expand` | `expand` |
| `/v0/purchase` | `buy_stored_item_cash` |
| `/v0/place_stored` | `place_stored_item` |
| `/v0/sell_stored` | `sell_stored_item` |
| `/v0/queue` | `push_queue_unit`, `pop_queue_unit` |
| `/v0/collection` | `complete_collection` |
| `/v0/resurrect` | `resurrect_hero` |
| `/v0/quests` | `set_goals`, `complete_goal`, `set_quest_var`, `collect_mission`, `admin_set_quest_rank`, `end_quest` |
| `/v0/research` | `next_research_step`, `research_buy_step_cash`, `next_research_item`, `reset_research_item` |
| `/v0/level_up` | `level_up` |
| `/v0/reward` | `weekly_reward`, `win_daily_bonus` |
| `/v0/magic` | `buy_magic`, `use_magic`, `buy_mana_new` |
| `/v0/darts` | `darts_reset`, `darts_new_free`, `darts_shoot_balloon`, `buy_premium_account` |
| `/v0/combat` | `end_attack`, `kill`, `kill_iid` |
| `/v0/session`, `/v0/bootstrap` | *(read-only; dispatch no branch)* |

`63 − 40 = 23`. Two cautions on this table, both load-bearing:

- The 22-route figure counts **routes**, and 24 routes exist. `/v0/session` is a
  `GET` and `/v0/bootstrap` is a read that builds no batch, so 22 is the number
  of routes that can dispatch anything.
- **`push_queue_unit2` is excluded from `/v0/queue` and is genuinely unrouted.**
  Its constant is declared in `queue_envelope` but the route's action set is
  closed at `push`/`pop`, and the handler states the exclusion explicitly. This
  is a real absence, not a scan artefact — which is why the executed-builder
  instrument was necessary.

---

## 4. The 23 unrouted branches

Every claim in this section is against `command.py` source read directly, not
against the command catalog's prose.

### Class A — catalog-classified must-not-migrate; refusal only, never a route (2)

| Branch | Source | What it does |
| --- | --- | --- |
| `flash_debug` | `command.py:302-320` | Assigns `playerInfo["cash"]` and `map["xp"/"gold"/"oil"/"steel"/"wood"]` **outright** from seven client args. No clamp, no validation, no delta accounting. |
| `fast_forward` | `command.py:905-947` | Subtracts a client-supplied `seconds` from **9** stored instants, floored at zero: 4 on `maps[0]` (`timestamp`, `timestampLastChapter`, `timestampLastTreasure`, `timestampLastTrade`) and 5 on `privateState` (`timestampLastBonus`, `timestampLastAllianceBonus`, `timeStampDartsNewFree`, `tsAttacksReset`, `tsSpyingsReset`). A further **2** such assignments exist but are **commented out** (`timeStampMondayBonus`, `timeStampDartsReset`), along with 4 more commented sections (research timers, map items, building timers, quest times). |

`flash_debug` is the single largest authority hole in the legacy dispatcher and
the catalog already classifies it `must-not-migrate`. Porting it would *add* a
hole, not close one.

### Class B — the branch writes nothing at all (3)

| Branch | Source | What it does |
| --- | --- | --- |
| `ping` | `command.py:948-949` | `print("Pong")`. |
| `set_variables` | `command.py:951-952` | `print("Set player resources")`. |
| `buy_powerups` | `command.py:720-725` | `print("Buy Atom Fusion PowerUP")` under a bare `# TODO`. |

`set_variables` is the sharp one, and it is grouped here rather than by the
catalog's classification because the reason matters more than the label: its
body writes **nothing whatsoever**, and its entire effect is the pre-dispatch
`apply_resources` at `command.py:40`. It is not a branch with behaviour — it is
the client-delta surface wearing a branch name. Server v1's design decision D3
already refuses that vector at the request layer for every route v1 owns, so
there is nothing left here to port.

A branch that writes nothing cannot be made authoritative, because there is no
state for authority to attach to.

### Class C — unbounded client-dictated grant or destruction (6)

| Branch | Source | What it does |
| --- | --- | --- |
| `store_add_items` | `command.py:258-267` | Iterates a client-sent id list, calling `add_store_item` and `bought_unit_add` on each. No selector, so no committed table can be indexed. |
| `batch_remove` | `command.py:189-196` | `map_delete_item` for every index in a `json.loads`'d client list. |
| `pop_unit` | `command.py:383-411` | Releases a garrison after **overwriting** the row's item id, cell, and team from client args (`unit[0] = item_id`, `unit[1] = x`, `unit[2] = y`, `unit[7] = playerID`). |
| `push_unit` | `command.py:365-382` | Pops a row off the map into a client-named building at client-named indexes. |
| `add_inventory_item` | `command.py:488-495` | `inventory_add` on a client item id and quantity. |
| `remove_inventory_item` | `command.py:496-503` | `inventory_remove` on a client item id and quantity. |

All six are refusal-only under any honest reading: with no committed rule saying
*what* may be destroyed or granted, a server that implements them faithfully is
a pass-through.

### Class D — client-sent value, no committed rule (7)

| Branch | Source | What it does |
| --- | --- | --- |
| `orient` | `command.py:198-209` | `item[4] = int(orientation)` — a client integer into a row slot. |
| `trade_resource` | `command.py:465-473` | `resource_type` and `sold` are read and **never used**; only `numTradesDone` and `timestampLastTrade` are written. |
| `rt_open_graph_unit` | `command.py:886-897` | Appends `str(item)` to `privateState["publishedOpenGraphUnit"]`. |
| `first_time_marketplace` | `command.py:899-903` | `privateState["marketPlaceFirstTime"] = True`. |
| `unit_collections_completed` | `command.py:482-486` | `unit_collection_complete(save, collection_id)`. |
| `add_xp_unit` | `command.py:322-344` | Assigns or increments `item attr xp` by an unvalidated client amount. |
| `soulmixer_speedup` | `command.py:727-744` | Zeros `atom_fusion[6]["ts"]`. |

None can be implemented without inventing a rule. `orient` is the clearest case:
the branch stores a client integer into a row slot and no committed content says
which orientations are legal or how one is chosen.

`soulmixer_speedup` is the sharpest instance of a computed-but-unapplied value:
it computes `cash_cost = ceil(remaining_time / 3600)` at `:738` and that local
has exactly **two** occurrences in the branch — the assignment and the f-string
at `:743` — so the cost is printed and **never charged**.

Three of these are single-field stamps whose fields have **no reader anywhere**
in the seven legacy root modules, measured code-only with comments and string
literals stripped: `publishedOpenGraphUnit` (written 6× in `rt_open_graph_unit`,
**0** read sites), `marketPlaceFirstTime` (written 1× in
`first_time_marketplace`, **0** read sites), and `unitCollectionsCompleted`
(written by `engine.py`'s `unit_collection_complete`, whose sole read-shaped hit
is its own idempotence guard at `engine.py:93`). A stamp nothing reads cannot be
made authoritative, because there is nothing downstream for authority to affect.

### Class E — already owned by a delivered capability's refusal (4)

These four must not be re-opened by a second surface, because a port that
duplicates an existing refusal decision is worse than no port: it creates two
surfaces that can drift apart.

| Branch | Owning capability | The decision already recorded |
| --- | --- | --- |
| `buy_si_help` | `godot-construction-assist` | The socially-in-construction surface; the only value any writer appends to `attr["si"]` is the integer `0`. |
| `finish_si` | `godot-construction-assist` | Same surface, reached through a second dispatcher (`set_resource_allies`). |
| `set_resource_allies` | `godot-construction-assist` | Same surface; no assist cost is ever charged. |
| `push_queue_unit2` | `godot-unit-queues` (design D6) | Atom fusion is recorded there as a deliberate absence, so promoting it here would create two owners of one surface. |

`trade_resource`, `soulmixer_speedup`, and `add_xp_unit` are also already owned
— by `godot-market-trade`, `godot-unit-queues`, and `godot-unit-experience`
respectively — but they sit in Class D because their *shape* independently
rules them out, and the overlap is recorded rather than hidden.

### Class F — committed content supplies both the selector and the answer (1)

**`buy_offer_pack`** is the only branch in the repository where a server can
derive the whole effect from committed content rather than inventing a rule, and
it is therefore the entire port-candidate set. §5 is about it.

> An earlier draft of this document put `buy_offer_pack` in a class of its own
> called "Class D" and gave that class a size of **6**. That 6 was a pack count
> that had drifted into a branch count, and the four classes as then written did
> not partition the 23 — `set_variables` and the three socially-in-construction
> branches sat outside every class and the arithmetic summed to 23 by accident.
> The six classes above partition all 23 with no branch in two classes and none
> omitted, and the class letters were relettered so the old "Class D" could not
> be mistaken for the new "Class D".

---

## 5. `buy_offer_pack` — the one branch where committed content can close the hole

### 5.1 The legacy branch

```python
elif cmd == "buy_offer_pack":
    package_id = args[0]
    item_list = args[1]
    items = json.loads(item_list)
    for item in items:
        add_store_item(map, item)
    print("Bought Offer Pack")
```

`command.py:710-718`. Two facts make this the strongest authority candidate in
the repository:

1. **The client sends a selector the server throws away.** `package_id` is
   assigned and never read — not passed to `add_store_item`, not compared
   against anything. This is the same shape as `research_buy_step_cash` reading
   a client cash value and discarding it, but with a committed table sitting
   right there that the value indexes into.
2. **The client sends the answer, and the server grants it verbatim.**
   `add_store_item` (`engine.py:70-75`) increments `map["store"][str(item)]`
   with no bound, no membership test, and no price check.

A client can therefore mint arbitrary items into storage for free, because the
price "travels through client-sent deltas" and the branch itself never looks at
a balance.

### 5.2 The committed content

`packages/game-content/normalized/offer_packs.json`, **44** entries, measured:

| Property | Measured |
| --- | --- |
| Entries | **44**, `legacy_id` `"1"`..`"44"`, all distinct |
| `str(id) == legacy_id` | **44 of 44** (no mismatch) |
| `items_shape` | `groups` **37**, `flat` **5**, `pairs` **1**, `null` **1** |
| `type` | `super` **25**, `""` **18**, `premium_account` **1** |
| `enabled` | `1` on **6**, `0` on **38** |
| `cost_cash` | `{0, 20, 25, 30, 40, 45, 60}` |
| `position` | `{0, 1, 2, 3, 4, 5, 6}` |
| Packs granting any resource | **1** — pack `1` "starter pack", `cost_cash 25`, **5000 each of gold, wood, steel, oil** |
| Zero-cost packs | **1** — pack `18` "Premium Account", `type premium_account`, `items_shape null`, `items null` |

The committed table supplies **everything** the branch throws away: the item
list keyed by the selector it ignores, a price it never checks, and resource
grants it never applies. Pack 1 is the sharp case — it grants 20,000 resources
across four slots, and under the legacy path those resources can only arrive as
client-sent deltas.

### 5.3 Zero legacy consumers — the field family, measured

Over the seven legacy root modules (`command.py`, `engine.py`, `sessions.py`,
`server.py`, `constants.py`, `get_game_config.py`, `version.py`), counting
whole-file occurrences, whole-file distinct lines, code-only occurrences with
comments and string literals stripped by a two-state lexer, and code-only
distinct lines:

| Field | whole | lines | code | code lines |
| --- | --- | --- | --- | --- |
| `offer_packs` | 0 | 0 | 0 | 0 |
| `cost_cash` | 0 | 0 | 0 | 0 |
| `items_shape` | 0 | 0 | 0 | 0 |
| `item_refs` | 0 | 0 | 0 | 0 |

**Zero consumers under all four counting rules.** This continues an established
sequence in this project — `unit_capacity`, the `levels` reward fields,
`max_frame`, `training_time`, `velocity`, `unlockedQuestIndex`,
`completed_tutorial` — and it is the first instance where **the absence of a
consumer is itself the authority defect**: the branch that should read this
table takes its values from the client instead.

`premium_account` measured **1** whole-file occurrence and **0** code-only, and
that single occurrence is the `buy_premium_account` **branch name** at
`command.py:612` — a substring artifact, exactly as `godot-mission-vocabulary`
recorded for `MISSION_DESTROYED_SUBCATFUNC`. The real premium schedule is
`PREMIUM_ACCOUNTS` in `globals`, read at `get_game_config.py:182`, which is a
different table and is already owned by `godot-darts`.

### 5.4 Corpus feasibility

All **10** committed save documents carrying `maps[0]` also carry a `store`
dict, so `add_store_item` cannot raise a missing-key; **3** have a non-empty
store. `tests/saves/fresh-player.json` has `store {}`, `playerInfo.cash 5`,
`gold`/`wood`/`steel`/`oil` `2000`, `xp 4`, and **40** placed rows.

The cheapest pack costs **20** cash. The fresh-player corpus therefore has
**5** against a floor of **20** — it cannot afford anything, which yields a
genuine `insufficient_resources` refusal with no fixture fabrication, while
`villages/AcidCaos.json` (cash **500**) can afford the full ladder. **Both arms
are exercisable against committed corpora**, which is the condition M13 line 1
required before capturing a fixture and which most of the 23 cannot meet.

---

## 6. Why the other 21 are not port candidates

| Candidate | Why not |
| --- | --- |
| `flash_debug`, `fast_forward` | Catalog-classified `must-not-migrate`; a route would add an authority hole. |
| `ping`, `set_variables` | Write nothing. No authority surface to make authoritative. |
| `buy_powerups` | Body is a `# TODO` and a `print`; writes nothing. |
| `store_add_items` | Client-sent id list with **no selector at all**, so no committed table can be indexed. Refusal is the only honest answer. |
| `batch_remove` | A client-supplied destruction list. There is no committed content describing what may be removed in bulk. |
| `add_inventory_item` / `remove_inventory_item` | `inventory_items` content exists (90 entries), but the **quantity** is a legitimate client choice and there is no committed rule bounding it. |
| `orient` | No committed orientation vocabulary. |
| `trade_resource` | Amounts are client-sent with no committed price; an authoritative route would grant a **free** trade, which is worse than the hole. Already owned by `godot-market-trade`. |
| `rt_open_graph_unit`, `first_time_marketplace`, `unit_collections_completed` | Client-sent ids with no committed selection rule; all three fields are single-field stamps with **no reader** (§4 Class D). |
| `pop_unit`, `push_unit` | Client-dictated coordinates, team, and item id. Already recorded by `godot-unit-movement` and `godot-unit-instances` as the exact untrusted shape v1 must refuse. |
| `add_xp_unit`, `soulmixer_speedup` | Already owned by `godot-unit-experience` and `godot-unit-queues` as deliberate refusals; `soulmixer_speedup` also computes a cost it never charges. |
| `buy_si_help`, `finish_si`, `set_resource_allies` | Already owned by `godot-construction-assist`; the only writer appends the integer `0` and no cost is ever charged. |

The pattern is worth stating plainly: **the largest holes and the best port
candidates are disjoint.** `flash_debug` can set six balances to arbitrary
values and cannot be ported under any reading. `buy_offer_pack` can mint
arbitrary items and is the one branch where committed content says exactly what
the grant should be.

---

## 7. Recommendation

Port **`buy_offer_pack`** as M13 line 2, and deliver it the way M13 line 1
delivered `collect`:

- the request carries **only** a pack selector;
- the item list, the resource grants, and the price are derived **server-side**
  from committed `offer_packs` content;
- a client-supplied item list is **refused**, never sanitised;
- an unaffordable pack is **refused** before any mutation;
- the post-execution proof checks the store grew by **exactly** the derived
  quantities and the charged cash moved by **exactly** `cost_cash`;
- the two unresolved leaves (§8) are **refused**, not coerced.

This is the only Class-F candidate, and it is the only branch in the repository
where the legacy dispatcher receives a client-supplied answer to a question
committed content can answer.

---

## 8. What is still unresolved, and must be before a proposal

These are open questions, deliberately not settled here.

1. **The two committed leaf anomalies reproduce and are not yet characterised.**
   Over all 579 leaves across the 44 packs, leaf types are **578 `int` + 1
   `float`**, and exactly **2** leaves do not resolve against the 900 normalized
   item `legacy_id`s: pack **4** leaf `35`, and pack **35** leaf `1072.1224`.
   This reproduces the two pinned anomalies `packages/game-content/README.md`
   records for the offers builder, so the builder's claim holds — but *why*
   those two leaves exist, and whether a pack containing one is purchasable at
   all, is not established. Both must be **refused**, not coerced.
2. **The `groups` and `pairs` shapes have no established semantics.** 37 packs
   are `groups` and exactly **1** is `pairs`. The legacy branch does
   `json.loads` and passes each element straight to `add_store_item`, so the
   legacy server treats a nested list as an item id and would store it under
   `str([1038, 1071, 1085])`. Whether the Flash client flattened these before
   sending is **unobserved**. Deriving a flattening rule would be an invention;
   refusing the shapes whose meaning is unknown is the honest alternative, and
   that decision belongs to the proposal, not to this document.
3. **`enabled` is `0` on 38 of 44 packs.** Whether a disabled pack is
   purchasable, and what `enabled` means to the client, is not established. Note
   pack 1 (the only resource-granting pack) is `enabled: 1`, which is weak
   corroboration and nothing more.
4. **The `premium_account` pack (18) has `items_shape: null` and `cost_cash: 0`.**
   Whether it is the same transaction as `buy_premium_account` — which reads the
   unrelated `PREMIUM_ACCOUNTS` schedule and charges nothing — or a distinct
   zero-cash no-op is not established.
5. **No executed-legacy fixture exists for `buy_offer_pack`.** One is capturable
   (§5.4) but has not been captured, so every parity statement here is a
   prediction, not evidence.
6. **The 23 figure is measured over the routes as they stand.** Any future v0
   route changes it, and the `route-coverage` tool's 24/39 will keep disagreeing
   with it by design. The reconciliation in §2 is a property of the current
   tree and would need re-measuring, not re-deriving.

---

## 9. Commands run, with results

| Command | Result |
| --- | --- |
| `python -B tools/command-catalog/verify_commands.py` | exit 0, `catalog_commands: 63`, `command_branches: 63`, `result: agreement` |
| `python -B tools/route-coverage/verify_route_coverage.py` | exit 0, `routes: 24`, `legacy_branches: 63`, `branches_covered: 24`, `branches_without_cited_route: 39`, permissive `37`/`26`, `ambiguous_citations: 3`, `unresolved_citations: 11`, `routes_without_cited_branch: 2` |

All enumeration was additionally performed by executing the committed envelope
modules against a throwaway interpreter with `apps/compat-api` on `sys.path`. No
service was started, no port was bound, and no save was written.

**Two repository files are modified by this stage:** this document, and the
correction note added to `docs/legacy-m13-collect-v1.md` (§2) so that the
falsified figure is withdrawn at its source rather than only contradicted
elsewhere. Every legacy source line quoted in §4 was checked against the working
tree at the range stated, by locating the `cmd == "<branch>"` header and
confirming it sits at the claimed first line — **19 of 19 verified, zero
mismatches**.

## 10. Claim limits

- **This document proposes nothing.** It recommends `buy_offer_pack` and stops.
  The OpenSpec change, its design decisions, and its ten derived rules are a
  later stage and none of them are settled here.
- **No claim about what the Flash client did.** Every statement is about the
  preserved Python server and the committed content. Absence of a server-side
  rule says nothing about client-side behaviour, which may have been entirely
  client-driven.
- **The 23 is a count of *dispatch*, not of *correctness*.** A route dispatching
  a branch does not make it authoritative; 40 dispatched branches include many
  that reproduce a client-sent vector, and those are recorded as such by the
  lines that own them.
- **Zero-consumer figures are about the seven legacy root modules only.** They
  say nothing about the 21 compatibility envelope modules, which are modern code
  and are expected to reference committed content.
- **The two unresolved leaves are a measurement, not a diagnosis.** §8.1 is
  explicit that the cause is unestablished.
- **No parity is claimed for any arm.** No fixture was captured and no legacy
  server was executed.
