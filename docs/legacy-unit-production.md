# Legacy unit production — investigation record

**Status:** investigation only. No mechanism is implemented and no fixture is captured,
because — as established below — **the legacy server has no production mechanism to
reproduce.**

**Date:** 2026-10-01 · **Milestone:** M8 — Units, line 4 of 8 · **Predecessors:** lines 1–3,
delivered and archived; the `queues` capability already recorded that no completion command
exists and no elapsed time is evaluated

**Facts not re-derived here:** the queue's `attr` keys are `nu`/`ts`/`ui` with a three-key
teardown; `push`/`pop` were captured against the Command Center at map key 1 with every
resource byte-identical; `unit_capacity` has no legacy consumer; no committed unit is
store-listed; and a unit instance is a map row whose garrison is a nested row.

---

## 1. The headline finding: the legacy server cannot produce a unit

This is stronger than "no completion was captured". There is **no production mechanism at
all**, established from three independent directions:

### 1a. Exactly five branches can put a row on the map, and none is a completion

| Branch | Where the `item_id` comes from | What it actually does |
| --- | --- | --- |
| `buy` | **client `args[1]`** | places any id at any cell; no store check, no producer check |
| `place_stored_item` | **client `args[1]`** | removes the id from `map["store"]`, then places it |
| `weekly_reward` | **client `args[1]`** | a reward — an item *or* resources |
| `pop_unit` | client `args[2]`, but the **row already exists** | moves a garrison row back onto the map |
| `resurrect_hero` | **client `args[1]`** | decrements the dead-unit count, then places |

`command.py`'s only `map_add_item` / `map_add_item_from_item` call sites are these five.
**Four of the five take the item id straight from the client**, and the fifth moves a row that
was already there. **Not one** derives an id from a completed queue, from `training_time`, or
from any committed production rule.

### 1b. No completion command exists, and nothing evaluates elapsed time

Already recorded by the `queues` line and re-confirmed here: the dispatcher's `complete_*`
family is exactly `complete_collection`, `complete_goal`, `complete_tutorial`, and **every**
`attr["ts"]` use in the legacy source is a write or a deletion. So there is neither a
completion command nor a readiness rule to reproduce.

### 1c. The duration field is never read

**`training_time` has no legacy consumer.** The only three substring matches across
`command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`, and `get_game_config.py`
are `sm_training_time` inside `soulmixer_speedup` — a **different field**, on the soul-mixer
path. So a building's committed `training_time` — on **130 of 470** buildings, including the
Command Center's `5` — is read by **nothing**.

**This is the third committed content field in this project with no legacy consumer**, after
`unit_capacity` (M8 line 2) and the level curve's `reward_type`/`reward_amount` (M7's XP
line). The precedent is established twice: record the field, refuse to invent a rule from it.

## 2. The acquisition routes are unvalidated client-sent item lists

Six branches can fill `map["store"]`, and two of them are the plausible unit sources:

| Branch | What it adds to the store | Input source |
| --- | --- | --- |
| `store_item` | the id of a row popped off the map | an existing row |
| `store_add_items` | a set of ids | client |
| `win_daily_bonus` | a reward | committed schedule |
| `buy_stored_item_cash` | one id | **client `args[0]`** |
| `complete_collection` | a collection reward | committed content |
| `buy_offer_pack` | every id in a JSON list | **client `args[1]`** |

Both plausible unit sources are unvalidated. `buy_offer_pack` reads `package_id` — and then
**never uses it**:

```python
elif cmd == "buy_offer_pack":
    package_id = args[0]
    item_list = args[1]
    items = json.loads(item_list)
    for item in items:
        add_store_item(map, item)
```

There is **no lookup into the committed `offer_packs` table** — the client sends an arbitrary
JSON array of ids and the server stores every one. `buy_stored_item_cash` is the same shape:
one client-sent `item_id`, stored with no check. This is exactly the pattern the delivered
`building-purchase` line already recorded as *derived-provisional* — "the choice of
`buy_stored_item_cash` and the cash-only price derivation are derived-provisional, never
observed from the Flash client" — and it is why that line refused to claim anything about
resource-priced storage purchases.

**Consequence: the committed `offer_packs` content (44 packs, 109 unit references) and the
committed `darts_items` content (27 entries, 44 unit references) are never read by any legacy
branch.** They describe a content-derived acquisition system the legacy server does not
implement. The offer and darts systems are later milestones, and enforcing their content is
their work, not this line's.

## 3. What `add_xp_unit` actually does — and why it is not production

`add_xp_unit` reads a **placed** row's `attr` and adds to `attr["xp"]`:

```python
elif cmd == "add_xp_unit":
    item_index = args[0]
    xp_gain = args[1]
    level = None
    if len(args) > 2:
        level = args[2]
    item = map_get_item(map, item_index)
    ...
    if "xp" not in attr:
        attr["xp"] = xp_gain
    else:
        attr["xp"] += xp_gain
```

It **creates nothing**. The XP amount is **client-sent**, and the optional level is a
client-sent value used only in a print. So it is a client-driven XP award, not a production
step — and it is the third untrusted client-delta pattern in this area, alongside the queue
vector and `trade_resource`. **No XP may be awarded from a client amount**, and none is
implemented here.

## 4. `sell` with a kill reason is a death path, and it is unreachable

`sell` calls `push_dead_unit(save["privateState"], item)` when `reason == "KILL"` and prints
`Remove {name} (Resurrectable)` when it returns `True`. The delivered `building-sell` line
already established that the combat `KILL` reason is **never reached**, because no reason is
accepted from the client. So no unit death, and no resurrection, is exercisable.

## 5. What the corpus can exercise

The committed corpus has **no unit row**, **no storage** (`maps[0]["store"]` is `{}`), an
**empty `inventoryItems`**, and **40 rows, 11 distinct item ids, all committed `type` `b`**.

| Operation | Exercisable? | Why |
| --- | --- | --- |
| `push_queue_unit` / `pop_queue_unit` | **Yes** — already captured | the Command Center at key 1 is a real placed producer |
| a queue **completion** | **No** | no command exists |
| a **readiness** evaluation | **No** | nothing reads `ts` |
| `place_stored_item` placing a unit | **No** | the store is empty, and only `buy_offer_pack`/`buy_stored_item_cash` could fill it with a unit, both client-sent |
| `add_xp_unit` | **Yes, but inert** | it needs a placed row; it would add a client-sent `attr["xp"]` to a building |
| `buy` placing a unit | **Yes, but meaningless** | it would accept the id with no check — which is the problem, not a capability |
| `sell` with `KILL` | **No** | no reason is accepted from the client |

So no fixture can be captured for production, because **there is no production behaviour to
capture** — not merely because the corpus lacks the state.

## 6. The consequence for M8 line 4

The honest deliverable for `production` is **a refusal made explicit, plus the inventory that
makes it auditable**:

- a **production-readiness projection that cannot report readiness**: it projects that a queue
  exists and records its start instant, and states that **the legacy server cannot say whether
  it is ready** — so the line delivers no readiness test, no completion, and no unit creation;
- **the row-entry inventory**: the five branches that can place a row, each with the source of
  its `item_id` named, so a later acquisition line knows which paths are **client-sent** and
  must be refused rather than trusted;
- the **`training_time` refusal**, stated as a spec requirement: the field has **zero** legacy
  consumers, so no training duration is derived from it and no production time is computed;
- the **`add_xp_unit` refusal**: a client-sent XP amount is never awarded;
- **no endpoint, no fixture, and no mechanism** — because none exists to reproduce.

**This is a real deliverable, not a stub.** Without it, a later line would face a
production-shaped field with a plausible-looking committed `training_time` and no recorded
reason to refuse, and would compute a client-side readiness and call it production. The
delivered `building-xp` and `godot-unit-queues` lines already refused that once each; this
line makes the refusal a capability with its evidence attached, so it cannot be quietly
undone.

**What must not be claimed:** that a queue completes, that a unit is produced or trained, that
`training_time` is a production duration, that XP is awarded on production, that a player
obtains a unit through the offer or darts systems, or that any client-visible rule gates
production.

## 7. Established versus derived

**Established from committed source:** the five row-entry branches and the source of each
`item_id`; that `buy_offer_pack` reads `package_id` and never uses it and `json.loads` a
client-sent list with no lookup into the committed table; that `buy_stored_item_cash` takes one
client-sent id; the six `add_store_item` call sites; that `training_time` has three substring
matches, all of them the distinct `sm_training_time`; `add_xp_unit`'s client-sent XP and its
client-sent level; `sell`'s `KILL` reachability; the corpus's empty store and empty inventory;
and that the committed `offer_packs` and `darts_items` tables are read by no legacy branch.

**Derived** (provisional, reversible): that the line's deliverable should be a refusal plus an
inventory rather than a mechanism; that the row-entry inventory belongs to this line rather than
to a later acquisition line; and that no endpoint is warranted while no server-derived
production exists.

**Not established, and not claimed:** what the Flash client displayed when a queue finished;
where a player actually obtained a unit in normal play; whether the offer and darts systems had
server-side validation in a client that this legacy server never received; and any production
duration, reward, or scheduling rule.
