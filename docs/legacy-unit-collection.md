# Legacy unit collection and acquisition — investigation record

**Status:** investigation only. No behaviour is implemented and no fixture is captured.

**Date:** 2026-10-01 · **Milestone:** M8 — Units, line 5 of 8 · **Predecessors:** lines 1–4
delivered and archived. The delivered `building-collect` capability covers a **building's**
income; this record establishes what collection means for a **unit**, and in doing so finds the
**first content-derived, server-authoritative unit acquisition path in this project.**

**Facts not re-derived here:** the `collect` command's effect is recorded below; the queue keys
`nu`/`ts`/`ui`; the five row-entry branches all take the item id from the client; `training_time`
has zero legacy consumers; and the delivered `godot-unit-production` capability already refuses
to derive any production duration or award any experience.

---

## 1. The headline finding: a collection prize can be a unit, and it is content-derived

`complete_collection` is the **only** server-side grant in the unit area that derives its
contents from committed content:

```python
elif cmd == "complete_collection":
    collection_id = args[0]
    bought = args[1]
    privateState = save["privateState"]
    prize = get_collection_prize(collection_id)
    for key in prize:
        add_store_item(map, int(key), prize[key])
    ...
```

and `get_collection_prize` reads the committed table positionally:

```python
def get_collection_prize(collection: int):
    index = max(0, collection - 1)
    collections = __game_config["collections"]
    if index < len(collections):
        return json.loads(collections[index]["prize"])
    return None
```

So the client sends a **collection id**, and the server looks up **what that collection grants**
in committed content. The client chooses *which* collection, never *what it receives*.

**Six of the ten committed collections grant a unit:**

| index | `collection_id` | Name | Committed prize |
| --- | --- | --- | --- |
| 0 | 1 | Draggy Collection | **unit 1085 Metal Draggy** |
| 1 | 2 | Transformer Collection | **unit 1062 MegaBot** |
| 2 | 3 | Plane Collection | **unit 1096 F-117** |
| 3 | 4 | Defense Collection | building 164 |
| 4 | 5 | Gun Collection | **unit 1073 Erradicator** |
| 5 | 6 | Tank Collection | **unit 1010 APC** |
| 6 | 7 | Launcher Collection | building 45 |
| 7 | 8 | Soldier Awards Collection | building 136 |
| 8 | 9 | Relaxing Time Collection | building 106 |
| 9 | 10 | Animal Collection | **unit 1056 Elephant rider** |

**6 distinct unit ids** (1010, 1056, 1062, 1073, 1085, 1096) and **4 building ids** (45, 106,
136, 164): the ten committed prize bags hold **ten** item ids in total, each collection granting
exactly one.

This **corrects and extends** the acquisition picture recorded by the `production` line. That
record established that `buy_offer_pack` and `buy_stored_item_cash` are **unvalidated
client-sent item lists** and therefore that no committed unit is obtainable through them. That
remains true — but it is not the whole picture, and this is the path the production line did not
find: **`complete_collection` derives its grant from committed content.**

### Why this is capturable against the corpus

The committed fresh-player save has `maps[0]["store"] == {}` and
`privateState["collections"] == []`. A completion would therefore **write** the committed prize
into the store — a real, observable, content-derived mutation. Combined with `place_stored_item`
(which places a stored id onto the map), this is a **two-step, fully committed, server-derived
path by which a unit enters a town**, and the corpus can exercise it **without fabricating a
player state**.

## 2. Two authority gaps the record must state, not smooth over

**Which collection is a client choice, and nothing checks it was earned.** `get_collection_prize`
clamps with `max(0, collection - 1)` and bounds-checks `index < len(collections)` — but **no
branch verifies that the collection's items were actually collected**, and `complete_collection`
does not test `privateState["collections"]` before granting. So a client may name any of the
ten. The **grant contents** remain content-derived; **the eligibility** is not server-checked.
That is a server-authority gap for M13, not something to fix here.

**The 1-based index is a derived-provisional interpretation.** `collection - 1` plus
`max(0, ...)` implies a **1-based** collection id. The committed table's own `id` column runs
`1`..`10` against `legacy_id` `0`..`9`, which agrees — so the reading is corroborated by the data
rather than merely plausible. Recorded as derived-provisional with the rejected zero-based
alternative, and with the one ambiguity named: `collection = 0` clamps to index 0, so **id 0 and
id 1 resolve to the same prize**.

## 3. The `collect` command is field-agnostic — it reads no collect field

The whole command:

```python
elif cmd == "collect":
    item_index = args[0]
    item = map_get_item(map, item_index)
    if not item:
        print("Error: item not found.")
        return
    # Update collect timers
    item[3] = time_now
    print("Collect", str(get_name_from_item_id(item[0])))
```

It **re-stamps the row's slot-3 timestamp and does nothing else.** It does not read the item's
`collect`, `collect_type`, `collect_xp`, `max_collects`, `max_elem_vol`, or `harvester`. A
measurement across `command.py`, `engine.py`, `constants.py`, and `get_game_config.py`:

| Field | Legacy reads |
| --- | --- |
| `collect` | **0** — the single `"collect"` string in `command.py` is the *branch name*, not a field read |
| `collect_type` | **0** |
| `collect_xp` | **0** |
| `max_collects` | **0** |
| `max_elem_vol` | **0** |
| `harvester` | **0** — and note this is **not** a top-level committed field: it is a
|   | `properties` flag key, present on **5** units (Worker I, Worker II, Worker III,
|   | Worker IV, Orc Worker), **every one of them with `collect` 0** |

So **every one of those committed collect fields has zero legacy consumers** — the same shape
as `unit_capacity`, `training_time`, and the level curve's reward fields. (`harvester` is the
one imprecise entry in that list: it is a `properties` flag key rather than a top-level field,
which does not change the zero-consumer finding but is recorded here so the list is not read
as six top-level fields.) That is why the delivered
`building-collect` capability **derived** its payout from committed content and recorded it as
derived-provisional: the server has none to reproduce, and the client's `resources_changed`
vector is the untrusted path.

## 4. No unit carries a positive collect amount

| Domain | `collect > 0` | `harvester > 0` | **Both** |
| --- | --- | --- | --- |
| units (429) | **0** | 5 | **0** |
| buildings (470) | 51 | 0 | **0** |

So **no committed unit grants income at all**, and the five "harvester" units are on a set
**disjoint** from any positive `collect` value. The four other collect-bearing building groups
are the income the delivered line already covered.

`max_collects` is **0 on all 429 units** — so the cap semantics the delivered `building-collect`
line deliberately refused (a non-zero committed cap) have **no unit analogue**: there is no
committed unit cap to interpret.

`collect_xp` is non-zero on many units (211 carry 3, 159 carry 2), but it is **never read**, and
the only command that writes `attr["xp"]` takes a **client-sent** amount — already refused by the
delivered `godot-unit-production` capability. **So a collection must not reintroduce an XP award.**

## 5. Two different "collection" concepts must not be conflated

| Concept | Command | Effect |
| --- | --- | --- |
| **Collection completion** (the `collections` table) | `complete_collection` | grants the **committed prize** into `map["store"]`, then appends the id to `privateState["collections"]` |
| **Unit collection tracking** | `unit_collections_completed` | calls `unit_collection_complete`, which only **appends an id** to `privateState["unitCollectionsCompleted"]` — **no grant** |
| Mission chapters | `collect_mission` | writes `idCurrentMission` and a timestamp; unrelated to items |

`unit_collections_completed` grants **nothing**, so it is not an acquisition route. The
committed `unit_collection_categories` table (20 entries) groups units into categories with
Greek names and empty costs; **no legacy branch reads it**.

## 6. What the corpus can and cannot exercise

| Operation | Exercisable? | Why |
| --- | --- | --- |
| `complete_collection` granting a **unit** prize | **Yes** | the store is empty and no collection is recorded, so the committed grant is an observable write |
| `complete_collection` granting a **building** prize | **Yes** | same, for collections 4, 7, 8, 9 |
| `place_stored_item` placing the granted unit | **Yes, after the grant** | the id would be in `map["store"]` |
| `collect` on a **unit** row | **No** | the corpus has no unit row — and a unit has no committed income to derive |
| `collect` on a **building** row | **Yes** | already delivered as `building-collect` |
| `unit_collections_completed` | **Yes, but inert** | it appends an id and grants nothing |
| any collection eligibility check | **No** | no such check exists |

## 7. The consequence for M8 line 5

`collection` is deliverable, and its shape is **materially different from `production`** — this is
the first M8 line with a **server-derived, content-backed grant** and therefore the first with a
genuinely capturable unit transaction:

- a typed, read-only **collection-prize projection**: the committed one-based index resolution,
  the committed prize bag, the unit/building classification of each prize, and the recorded
  authority gaps (eligibility unchecked; id 0 and id 1 alias);
- an **acquisition-path inventory** distinguishing the one **content-derived** route
  (`complete_collection` → `map["store"]` → `place_stored_item`) from the **unvalidated
  client-sent** routes already recorded, so the difference is auditable rather than implied;
- the **`collect` field-agnosticism refusal** — no unit income derived, because no unit carries a
  positive `collect` and no collect field is ever read;
- the **`max_collects` and `collect_xp` refusals** — no cap semantics for units (uniformly 0) and
  no experience awarded (never read, and the writer is client-sent);
- **an executed-legacy fixture** for `complete_collection` granting a committed unit prize into
  the empty store — **the project's first content-derived, server-authoritative unit
  acquisition**, captured without fabricating a player state.

**What must not be claimed:** that a collection is *earned* (nothing checks), that the client
cannot name any collection, that a unit collects income (none does), that a unit's
`max_collects` or `collect_xp` has meaning, that XP is awarded on collection, or that a client
displayed any of this.

## 8. Established versus derived

**Established from committed source and content:** the `complete_collection` branch and
`get_collection_prize`'s positional lookup; the ten committed collections and that **six grant a
unit** and four a building; the absence of any eligibility check; the `collect` command's single
effect of re-stamping slot 3; the **zero** legacy reads of `collect`, `collect_type`,
`collect_xp`, `max_collects`, `max_elem_vol`, and `harvester`; **0 of 429** units with a
positive `collect`; the five harvester units being on a disjoint set; `max_collects` being 0 on
all units; `unit_collections_completed` granting nothing; the corpus's empty store and empty
`collections` list; and `unit_collection_categories` being read by no branch.

**Derived** (provisional, reversible): the **1-based** collection index, corroborated by the
committed `id` column running `1`..`10` against `legacy_id` `0`..`9`, with the rejected zero-based
alternative retained and the id-0/id-1 alias named; that the collection completion route is the
project's only content-derived unit acquisition; and that the fixture belongs to this line rather
than to a later acquisition milestone.

**Not established, and not claimed:** what the Flash client displayed on collection; whether a
player in normal play ever completed one of these ten collections; how a collection's
`item_ids` requirement is checked in the real client; and the semantics of the 20
`unit_collection_categories` rows.
