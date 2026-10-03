# The stored-item placement round trip — `place_stored_item`, `sell_stored_item`, `store_add_items`

**Status:** committed investigation record. **This document implements nothing.**
It establishes the contract for the nearest undelivered step on a fully
content-derived path: taking an item **out of storage and onto the map**.

**Date:** 2026-10-03
**Branch:** `docs/stored-unit-placement`
**Predecessors:** `docs/legacy-m9-assessment.md` (PR #270) §4, which named this
as the nearest follow-up and measured it as exercisable
**Named by:** `capture_collection_fixture.py`'s manifest key
`"stored_item_placement_chained": False`
**Close-out target:** the `unit-collection` line's own carried follow-up,
*"this line only evidences the grant into storage and not a unit placed on the
map"*

---

## 0. Summary

**24 executed-legacy probe transactions** in two contained runs against the real
Flask server settle every open question. The headline findings:

1. **This is not a refusal line.** Three legacy branches exist, they are
   reachable, and two of the three mutate real state. `place_stored_item` is
   **type-agnostic** — it places a *unit* and a *building* identically.
2. **No price exists and none moves.** Every one of the 24 transactions left all
   six stored resources byte-identical, under a **neutral** 8-slot vector. The
   branch never reads the client's vector for anything.
3. **The placed row is almost entirely server-derived.** Of its eight slots the
   client supplies three (`item_id`, `x`, `y`); the server writes `timestamp`,
   `store`, `attr`, and `player`. `orientation` is passed through **verbatim**.
4. **`attr` is content-derived, not client-supplied.** Placing the Command
   Center (`clicks_to_build` 1) produced `{"nc": 0}`; placing Metal Draggy
   (`clicks_to_build` 0) produced `{}`.
5. **The client-sent player team is read and discarded.** `args[4] playerID = 3`
   produced a row whose slot 7 is **`1`**.
6. **Four unguarded behaviours, all confirmed by execution.** Three are vectors a
   modern endpoint must **refuse** rather than reproduce — placing an item
   **not in storage** (silent duplication), placing onto an **occupied index**
   (silent destruction of an existing row, invisible to any count-based check),
   and placing an **item id with no committed definition**. The fourth,
   placing at an **out-of-grid cell**, is the **already-recorded** M6
   geometry gap and is *recorded, not refused* — see §3.11 and §7.
7. **The collection prize is not always a unit.** **4 of the 10** committed
   collection prizes are **buildings** (164 Laser Turret, 45 Dual-Rocket Turret,
   136 General Sculpture, 106 Fountain), 6 are units. The type-agnostic branch is
   what lets one placement line serve all ten.
8. **The capture corpus can be built entirely from content-derived commands.**
   The committed fresh corpus has an **empty** store, so a fixture must seed
   one. `complete_collection` is that seed: the client's only input is a
   collection id and the **prize is derived from committed content**, exactly as
   the delivered collection line established.

**Recommendation:** deliver the storage round trip as **one bounded line** —
`place_stored_item` and `sell_stored_item` together, since they sit three lines
apart, share `remove_store_item`, and are exact inverses. **`store_add_items` is
out of scope**: it is an unvalidated client-sent grant, which `unit-production`
already recorded as an acquisition anti-pattern. Nothing here authorises
implementing any of it.

---

## 1. Method, and one defect in my own probes

Both probe runs reused the project's own containment harness
(`apps/compat-api/capture_legacy_fixtures.py`): `build_disposable` copies the
root `*.py` plus `config`, `mods`, `villages`, `templates` into a
`tempfile.mkdtemp(prefix="socialwars-capture-")` and seeds **one** save from
`tests/saves/fresh-player.json`; `start_server` runs `[sys.executable, "-B",
"server.py"]` with `cwd=disposable` on `127.0.0.1:5055`; `wait_ready` is a bare
TCP connect loop with a 45 s deadline; `stop_server` `taskkill`s the tree and
re-checks the port; the disposable is `rmtree`d in a `finally`.
`containment_snapshot()` digests the root Python, `config`, `mods`, `villages`,
`templates`, `tests/saves`, and `saves` before and after.

**Both runs reported containment byte-identical**, and the port free afterwards:

```
run 1  18e5e55ba85473bb6a7aca8ff6a27b05ba7848794649af9391896e6d49b4a724
run 2  18e5e55ba85473bb...   (identical: True)
```

State deltas were measured with a JSON-pointer leaf diff, the project's
machine-checkable form, and every probe's full changed-leaf set is reproduced in
§3.

### 1.1 Defect — probe 1 asked the wrong question about type

Probe 1 labelled id `1037` a *building* and so never tested whether the branch
is unit-only. The committed content says `1037` is **`MegaTank`, a unit**
(`units.json`, `type` `u`). Probe 1's "I" transaction therefore proved nothing
about buildings.

**Corrected in probe 2** with genuinely mixed ids — the Command Center `26` and
the Wall `23` from `buildings.json`, both `type` `b`, `clicks_to_build` 1 —
which is where the `{"nc": 0}` seeding and the type-agnosticism finding come
from. Recorded because a probe that silently tests the wrong thing is worse than
no probe: its output looked like an answer.

---

## 2. The three storage branches

All three sit within 33 lines of each other in `command.py:233-266`.

### 2.1 `place_stored_item` — `command.py:233-248`

Eight client arguments, three effects, one print:

```python
elif cmd == "place_stored_item":
    item_index = args[0]
    item_id = args[1]
    x = args[2]
    y = args[3]
    playerID = args[4]
    orientation = args[5]
    unknown_autoactivable_bool = args[6]
    unknown_imgIndex = args[7] # one of these might be timestamp
    name = str(get_name_from_item_id(item_id))

    remove_store_item(map, item_id)
    map_add_item(map, item_index, item_id, x, y, orientation=orientation)
    bought_unit_add(save, item_id)

    print(f"Placed stored {name}.")
```

`args[4]` `playerID`, `args[6]`, and `args[7]` are **read and never used** —
`playerID` is not passed to `map_add_item`. The branch reads the resource vector
nowhere. Measured by identifier occurrence inside the 16-line branch, comment
stripped:

| identifier | lines it appears on | verdict |
| --- | --- | --- |
| `item_index` | 234, 245 | used |
| `item_id` | 235, 242, 244, 245, 246 | used |
| `orientation` | 239, 245 | used, **passthrough** |
| `name` | 242, 248 | used, **display only** |
| `playerID` | **238 only** | **read, never used** |
| `unknown_autoactivable_bool` | **240 only** | **read, never used** |
| `unknown_imgIndex` | **241 only** | **read, never used** |

The branch's three effect lines, verbatim and complete:

```python
    remove_store_item(map, item_id)
    map_add_item(map, item_index, item_id, x, y, orientation=orientation)
    bought_unit_add(save, item_id)
```

### 2.2 `sell_stored_item` — `command.py:250-256`

One argument, one effect, **no refund**:

```python
elif cmd == "sell_stored_item":
    item_id = args[0]
    name = str(get_name_from_item_id(item_id))

    remove_store_item(map, item_id)

    print(f"Sell stored {name}.")
```

No `map["gold"]`, no `apply_resources`, no return value. Confirmed by execution
in §3.4: the stored item left and **every** resource was unchanged.

### 2.3 `store_add_items` — `command.py:258-266`

```python
elif cmd == "store_add_items":
    item_id_list = args[0]

    # Add to store
    for item_id in item_id_list:
        add_store_item(map, item_id)
        bought_unit_add(save, item_id)
```

An unvalidated client-sent id list that grants into storage. **Out of scope for
this line**, and used in the probes only as a seeding device.

### 2.4 The two engine helpers both branches share

```python
def remove_store_item(map: dict, item: int, quantity: int = 1):   # engine.py:77-84
    itemstr = str(item)
    if itemstr in map["store"]:        # <-- ABSENT IS A SILENT NO-OP
        new_quantity = map["store"][itemstr] - quantity
        if new_quantity <= 0:
            del map["store"][itemstr]
        else:
            map["store"][itemstr] = new_quantity

def bought_unit_add(save: dict, item: int):                      # engine.py:86-89
    boughtUnits = save["privateState"]["boughtUnits"]
    if item not in boughtUnits:
        boughtUnits.append(item)
```

Two consequences, both confirmed by execution: the default `quantity=1` means
one placement consumes one unit of stock (§3.5), and `bought_unit_add`'s
append-if-absent means repeated placements never duplicate the ledger (§3.6).

`map_add_item` (`engine.py:8-31`) is the fourth participant. It **assigns**
`map["items"][str(index)] = [...]` — there is no occupancy test — and its
`player == 1` default seeds `attr` from committed content:

```python
if player == 1:
    properties = get_attribute_from_item_id(item, "properties")
    if properties:
        properties = json.loads(properties)
        if "friend_assistable" in properties:
            if int(properties["friend_assistable"]) > 0:
                attr["si"] = []
    click_to_build = get_attribute_from_item_id(item, "clicks_to_build")
    if click_to_build:
        if int(click_to_build) > 0:
            attr["nc"] = 0
```

---

## 3. Executed-legacy evidence

Two runs, 24 transactions, all answering `{"result":"success"}` with status
**200**. Changed-leaf sets are complete.

### 3.1 The target transaction (probe 1, #2)

```
store_add_items  [[1085]]                 -> store {"1085": 1}, boughtUnits [1085], rows 40
place_stored_item [41, 1085, 58, 47, 1, 0, 0, 0]
  rows           40 -> 41
  store          {"1085": 1} -> {}
  boughtUnits    1 -> 1     (unchanged: 1085 already present)
  resources      NONE moved
  privateState   NONE moved
  changed leaves (2):
     /maps/0/items/41     None -> [1085, 58, 47, 1791012599, 0, [], {}, 1]
     /maps/0/store/1085   1 -> None
```

**Exactly two leaves.** No other row, no resource, no other `privateState` key.
`1085` is Metal Draggy — the **committed prize of collection 1** — so this is the
exact round trip the collection line refused to close.

### 3.2 The row is server-derived in five of eight slots

| slot | field | source | evidence |
| --- | --- | --- | --- |
| 0 | `item_id` | client `args[1]` | 1085, echoed verbatim |
| 1 | `x` | client `args[2]` | 58 |
| 2 | `y` | client `args[3]` | 47 |
| 3 | `timestamp` | **server clock** | 1791012599, `int(time.time())` at `engine.py:5-6` via `engine.py:13-14` |
| 4 | `orientation` | client `args[5]`, **passthrough** | 0, and `map_add_item` defaults it to 0 |
| 5 | `store` | **server**, always `[]` | `engine.py:11-12` |
| 6 | `attr` | **committed content** | `{}` for 1085, `{"nc": 0}` for 26 — §3.7 |
| 7 | `player` | **server**, always `1` | `engine.py:8` default; §3.8 |

> Slot 3 is a **wall-clock reading**, so a fixture's `after.json` is *not*
> byte-stable across reruns. This is the same condition the placement fixture
> already records (`tests/fixtures/godot-building-placement/README.md`): its
> volatile allowlist gains this one entry, and with it the
> `save_after_sha256` that entry feeds — four volatile items in total.

### 3.3 Vector one — placing an item that is not in storage (probe 1, #5)

```
place_stored_item [42, 1071, 60, 47, 1, 0, 0, 0]     # 1071 was NEVER stored
  status 200, body {"result":"success"}
  rows        41 -> 42
  store       {"1055": 1} -> {"1055": 1}              # UNCHANGED
  boughtUnits 3 -> 4                                  # GREW
  changed leaves (2):
     /maps/0/items/42          None -> [1071, 60, 47, 1791012599, 0, [], {}, 1]
     /privateState/boughtUnits/length  3 -> 4
```

A unit the player never acquired appears on the map, is recorded as bought, and
the server answers success. **`remove_store_item`'s conditional is the whole
cause.** Probe 2 repeated the shape at #9 with the store empty and got the same
result: one changed leaf, the new row, nothing else.

### 3.4 Vector two — placing onto an occupied index (probe 1, #6)

```
index 1 currently held [26, 51, 41, 0, 0, [], {}, 1]     # the Command Center
place_stored_item [1, 1055, 61, 47, 1, 0, 0, 0]
  rows        42 -> 42                                   # COUNT UNCHANGED
  store       {"1055": 1} -> {}
  changed leaves (5):
     /maps/0/items/1/0    26 -> 1055
     /maps/0/items/1/1    51 -> 61
     /maps/0/items/1/2    41 -> 47
     /maps/0/items/1/3    0 -> 1791012599
     /maps/0/store/1055   1 -> None
  index 1 is now: [1055, 61, 47, 1791012599, 0, [], {}, 1]
```

**A placed building is destroyed with no error and no resource movement**, and
because the row count does not change it is invisible to any count-based check.
`map["items"][str(index)] = [...]` is an assignment with no occupancy test
(`engine.py:31`). This is the most serious of the four vectors and the one a
two-part post-state proof must be built to catch.

### 3.5 Quantity semantics — one placement consumes one (probe 1, #7–8)

```
store_add_items [[1121, 1121]]            -> store {"1121": 2}, boughtUnits 4 -> 5
place_stored_item [43, 1121, 62, 47, ...] -> store {"1121": 2} -> {"1121": 1}
```

`remove_store_item`'s default `quantity=1` decrements by one; the branch exposes
no way to place a quantity. **`boughtUnits` grew by one, not two**, because
`bought_unit_add` is append-if-absent and `1121` was not yet present — the ledger
counts *distinct ids*, never units held.

### 3.6 Repeated placement never duplicates the ledger (probe 1, #9–11)

```
store_add_items [[1063, 1063]]            -> store {"1063": 2}, boughtUnits 5 -> 6
place_stored_item [44, 1063, 63, 47, ...] -> store {"1063": 2} -> {"1063": 1}, boughtUnits 6 -> 6
place_stored_item [45, 1063, 64, 47, ...] -> store {"1063": 1} -> {},         boughtUnits 6 -> 6
```

Two rows, two stock decrements, **one** ledger entry. Probe 2 #5 repeated this
across runs: re-storing an id already in `boughtUnits` (`26`) left the ledger
length unchanged.

### 3.7 The `attr` bag is content-derived (probe 2, #2)

```
store_add_items [[26, 23]]                        -> store {"23":1,"26":1}, boughtUnits 0 -> 2
place_stored_item [41, 26, 58, 47, 1, 0, 0, 0]
  rows 40 -> 41
  changed leaves (2):
     /maps/0/items/41    None -> [26, 58, 47, 1791012742, 0, [], {"nc": 0}, 1]
     /maps/0/store/26    1 -> None
```

The **Command Center**, `type` `b`, `clicks_to_build` 1 → `{"nc": 0}`. Compare
§3.1's **Metal Draggy**, `clicks_to_build` 0 → `{}`. The `attr` bag is therefore
**not** a client input and **not** a free-form dict: it is a pure function of the
committed item's `clicks_to_build` and `properties.friend_assistable`, and the
client cannot influence it.

Measured over the whole committed content:

| table | rows | `friend_assistable` > 0 | `clicks_to_build` > 0 |
| --- | --- | --- | --- |
| `units.json` | 429 | **0** | **0** |
| `buildings.json` | 470 | **26** | **298** |

So `attr` is **always `{}` for a unit** and is content-shaped only for buildings —
which is precisely why the four building prizes in §6.1 all seed `{"nc": 0}` and
the six unit prizes all seed `{}`. `attr["si"]` is unreachable for every unit and
reachable for 26 committed buildings, none of which is a collection prize.

> **An encoding asymmetry to get right.** `properties` is an **object** in both
> normalized tables (`units.json` 429/429, `buildings.json` 470/470) — but it is
> a JSON-encoded **string** in the raw `config/main.json`, which is what
> `engine.py:21` parses. A derivation must read the *normalized* shape and must
> not re-implement the raw parse.

### 3.8 The client-sent player team is discarded (probe 2, #4)

```
place_stored_item [42, 1085, 59, 47, 3, 0, 0, 0]     # args[4] = 3
  rows 41 -> 42
  >> placed row: [1085, 59, 47, 1791012742, 0, [], {}, 1]
  >> slot 7 (player) = 1
```

`command.py:238` reads `playerID = args[4]`; `command.py:245` does not pass it.
The row is **always** player `1`, whatever the client sends. So `args[4]` is a
read-but-unused argument, exactly like M7's `move` `frame`/`string` and M8's
`used_syringe`.

### 3.9 The branch is type-agnostic (probe 2, #2 and #6)

Both a building (`26`) and a unit (`1085`) place identically, and
`sell_stored_item` also accepted a building (`26`, probe 2 #6). There is **no**
type check anywhere on this path. That is not a defect to guard against for its
own sake — it is what makes one placement line serve all ten collection prizes,
four of which are buildings (§6.2).

### 3.10 Vector three — an item with no committed definition (probe 1, #14)

```
place_stored_item [47, 999999, 66, 47, 1, 0, 0, 0]
  status 200, body {"result":"success"}
  rows 46 -> 47
  changed leaves (2):
     /maps/0/items/47               None -> [999999, 66, 47, 1791012599, 0, [], {}, 1]
     /privateState/boughtUnits/length  7 -> 8
```

`999999` is in no normalized table and in no `config` section. The row is placed
with an **empty** `attr` — `get_attribute_from_item_id` returns nothing — and
`999999` is appended to `boughtUnits` as a purchased unit. A modern endpoint must
resolve the id against committed content and refuse otherwise.

### 3.11 Vector four — no bounds, no index validation (probe 2, #8 and #10)

```
place_stored_item [43, 1085, 250, -3, 1, 0, 0, 0]
  rows 42 -> 43
  /maps/0/items/43   None -> [1085, 250, -3, 1791012743, 0, [], {}, 1]

place_stored_item [999999, 1085, 58, 49, 1, 0, 0, 0]
  /maps/0/items/999999  None -> [1085, 58, 49, 1791012743, 0, [], {}, 1]
  >> key 999999 present: True
```

`(250, -3)` is stored verbatim, outside the derived `0..99` grid on both axes,
and `item_index` `999999` becomes a map key. This is the **already-recorded** M6
gap — tile-to-cell geometry and bounds are client-side rules with no
server-authoritative validation — and it is **not** a new finding. It is recorded
here so the line's refusal list is complete, and it should be handled as a
client-side rule plus a recorded Server v1 / M13 gap, exactly as `building-move`
did, rather than as a refusal this line invents.

---

## 4. `sell_stored_item`, executed (probe 1 #4, probe 2 #6)

```
sell_stored_item [1033]                  # a unit
  rows 41 -> 41 ; boughtUnits 3 -> 3
  changed leaves (1):
     /maps/0/store/1033   1 -> None

sell_stored_item [26]                    # a building
  rows 42 -> 42
  changed leaves (1):
     /maps/0/store/26   1 -> None
  >> store now {"23": 1}
```

**Exactly one changed leaf, and it is the store key.** No row is added, no
`boughtUnits` entry is written or removed, and no resource is credited. A "sale"
is a pure storage decrement with **no refund**, which retroactively explains why
the delivered `building-store` line recorded "no refund is claimed" for building
sales and why it never implemented this branch.

Its only unguarded property is the same `remove_store_item` conditional: selling
an item that is not in storage is a **silent no-op**, not an error. That is
benign where it is a no-op, but it means "sell" cannot be distinguished from
"sell of nothing" by the response, so a modern endpoint must fail closed on an
absent id rather than report success.

---

## 5. Committed evidence for a capture corpus

### 5.1 The fresh corpus cannot seed itself

```
tests/saves/fresh-player.json   rows 40   store {}   privateState.boughtUnits []
```

Both the store and the ledger are **empty**, so a placement fixture has nothing
to place. The capture harness seeds exactly one save from this file
(`capture_legacy_fixtures.py:237-255`), so the seed route must be chosen
deliberately.

**Three routes, and only one is content-derived:**

| route | client input | content-derived? | verdict |
| --- | --- | --- | --- |
| `store_add_items` | an **arbitrary id list** | no | out of scope; an unvalidated grant |
| hand-edited seed save | none | n/a | **forbidden** — a fabricated corpus |
| **`complete_collection`** | a collection **id** | **yes — the prize is derived from the committed table** | **recommended** |

`complete_collection` is precisely the branch the delivered `unit-collection`
line established: the client names a collection and the server derives the prize
from `config/main.json`. Using it as the seed gives a capture in which **every
transaction is content-derived and no client-sent item id list appears
anywhere**:

```
login_post
command_complete_collection   [1]                       -> store {"1085": 1}, ledger [1]
command_place_stored_item     [41, 1085, 58, 47, 1, 0, 0, 0]   -> row 41, store {}, ledger [1]
```

This also makes the new fixture the **first executed-legacy evidence for the
collection→placement round trip**, closing the `unit-collection` line's own
recorded gap rather than merely adding a new one.

### 5.2 The derived cell is already an established rule

`building-move` derived the free cell `(58, 47)` when moving the Turret I off
`(58, 48)`. The committed corpus agrees that this is free and adjacent:

```
        x=54 55 56 57 58 59 60 61 62
 y=47    .  .  .  .  .  .  .  .  .      (. = no row anchored here)
 y=48    .  .  .  .  . 22 23  .  .  .
 y=49   23 23 23 23 23 23  .  .  .
```

Key 11 is item 22 at `(58,48)`; `(58,47)` is the cell the move line derived and
used. Reusing it keeps the two lines consistent and means the "free cell" claim
is checkable against a rule that already ships.

Metal Draggy is **1×1**, so its footprint is a single cell and no edge case
arises. The general-sculpture prize (136) is 2×2 and the fountain (106) is 3×3,
so a footprint-aware cell derivation is *not* trivially extendable to all ten
prizes — see §7.

---

## 6. What the collection→placement loop actually looks like

### 6.1 All ten prizes resolve

| collection | prize | kind | w×h | `clicks_to_build` | `attr` on placement |
| --- | --- | --- | --- | --- | --- |
| 1 | 1085 Metal Draggy | unit | 1×1 | 0 | `{}` |
| 2 | 1062 MegaBot | unit | 1×1 | 0 | `{}` |
| 3 | 1096 F-117 | unit | 1×1 | 0 | `{}` |
| 4 | **164 Laser Turret** | **building** | 1×1 | **1** | `{"nc": 0}` |
| 5 | 1073 Erradicator | unit | 1×1 | 0 | `{}` |
| 6 | 1010 APC | unit | 1×1 | 0 | `{}` |
| 7 | **45 Dual-Rocket Turret** | **building** | 1×1 | **1** | `{"nc": 0}` |
| 8 | **136 General Sculpture** | **building** | **2×2** | **1** | `{"nc": 0}` |
| 9 | **106 Fountain** | **building** | **3×3** | **1** | `{"nc": 0}` |
| 10 | 1056 Elephant rider | unit | 1×1 | 0 | `{}` |

### 6.2 This corrects a framing in the assessment

`docs/legacy-m9-assessment.md` §5 said collections' one missing step is placing
**"the granted unit"**. That is true for **6 of 10** collections. The other
**four grant buildings**, three of which need a build-click
(`clicks_to_build` 1, hence the `nc` counter the construction line owns) and two
of which occupy more than one cell.

> The correct framing is **not** "a collection's unit cannot be placed" but
> **"a collection's prize cannot be placed"**. The line's scope must be written
> against the prize, not the word "unit" — and because the branch is
> type-agnostic (§3.9), one line still serves all ten.

---

## 7. What a bounded line would deliver, and what it must refuse

Proposed shape. **Not authorised here** — this is the investigation's
recommendation, for the proposal stage to accept, narrow, or reject.

**Deliver**

1. `POST /v0/place_stored` — intent `{user_id, item_id, x, y}` (+ optional
   `orientation`), deriving `item_index` server-side as the smallest positive
   absent slot, exactly as `placement_envelope.next_free_slot` already does.
2. A committed envelope module imported by **both** the capture and the
   endpoint, so parity is checked against one derivation.
3. A two-part post-execution proof: the stored count decremented by exactly one
   **and** `boughtUnits` gained the id **only if newly present** — plus the
   `{"nc": 0}`-or-`{}` `attr` assertion, which is the content-derived half.
4. An executed-legacy fixture chained `complete_collection` → `place_stored_item`,
   with the four behaviours of §3.3/§3.4/§3.10/§3.11 recorded as **probes** in the
   manifest, not as recorded steps — the `capture_collection_fixture.py`
   convention.
5. `POST /v0/sell_stored` in the same line: one argument, one leaf, **no refund**
   claimed, absent id refused.
6. A Godot client flow that places from the storage view, reusing the delivered
   `building-store` projection and `unit-instances` typing.

**Refuse, each with a named code**

| refusal | why | legacy behaviour |
| --- | --- | --- |
| `not_in_storage` | §3.3 duplication vector | places anyway, success |
| `slot_occupied` | §3.4 silent destruction | overwrites, success |
| `unknown_item_id` | §3.10 | places anyway, success |
| `item_not_placeable` | `get_attribute_from_item_id` yields nothing | n/a |

**Record, do not refuse**

* grid bounds and cell occupancy — the **M6 geometry gap**, already recorded, no
  server-authoritative validation in legacy and none to be invented here;
* `store_add_items` — out of scope, an unvalidated client-sent grant;
* footprint-aware cell derivation — necessary for prizes 136 (2×2) and 106 (3×3),
  but **the tile-to-cell geometry is a known evidence gap** that needs new
  evidence, not a derivation. A 1×1 prize needs none, so the line can ship on
  Metal Draggy and record the rest.

**Divergences to declare**

* The four refusals above are all **deliberate divergences** from the legacy
  server, which answers `success` in every case.
* No price is charged and no stored resource moves — reproduced, not invented:
  all 24 transactions show it.
* The neutral 8-slot vector is **derived-provisional**; the branch never reads
  it, so no behaviour is claimed from it.

---

## 8. Corrections this record makes

| record | claim | correction |
| --- | --- | --- |
| `docs/legacy-m9-assessment.md` §5 | collections' missing step is placing "the granted **unit**" | true for **6 of 10**; four prizes are **buildings**, three needing a build click, two multi-cell |
| `docs/legacy-m9-assessment.md` §4 | "the store is map-level, `Nerri` carries six stored unit ids" | still true, but the *capture* harness seeds only `fresh-player.json`, whose store is **empty** — so the village evidence motivates the line while `complete_collection` must seed the fixture |
| `building-store` | storage is display-only, "no placing from or selling out of storage" | accurate about the delivered client; the legacy branch is type-agnostic, charges nothing, and its **sell half pays no refund** — now executed |

Nothing here requires un-delivering any delivered behaviour. The `attr`
seeding, the discarded `playerID`, and the four unguarded vectors are all new
measurements against previously unexercised branches.

---

## 9. Re-measurement

Every figure above came from executed probes or committed-file reads and was
re-measured before being written down. The two probe scripts are throwaway and
live outside the repository. Nothing in `command.py`, `engine.py`, `config/`,
`villages/`, `tests/saves/`, `packages/`, or any committed fixture was modified:
both runs reported a byte-identical working-tree containment digest and a free
port afterwards.

**No Flash, Ruffle, ActionScript, or browser executed.** The legacy server ran
in a disposable temp copy on `127.0.0.1:5055`; every request was loopback.