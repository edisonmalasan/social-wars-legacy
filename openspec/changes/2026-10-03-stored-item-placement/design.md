# Design

## Context

The legacy storage round trip is three branches within 33 lines of each other in
`command.py:233-266`, plus two engine helpers and one row-writing helper they
share.

```python
elif cmd == "place_stored_item":          # command.py:233-248
    ...
    remove_store_item(map, item_id)
    map_add_item(map, item_index, item_id, x, y, orientation=orientation)
    bought_unit_add(save, item_id)
```

Five constraints shape every decision below. All are measurements from
`docs/legacy-stored-unit-placement.md` (PR #271), which ran 24 executed-legacy
probe transactions against the real Flask server.

1. **The row is mostly server-derived.** Of its eight slots the client supplies
   three — `item_id`, `x`, `y`. The server writes `timestamp` (wall clock),
   `store` (always `[]`), `player` (always `1`), and `attr` (from committed
   content). `orientation` is a verbatim passthrough. The remaining three
   arguments — `playerID`, `unknown_autoactivable_bool`, `unknown_imgIndex` —
   each appear on exactly one line, their own assignment.
2. **`attr` is a pure function of committed content.** `engine.map_add_item`
   seeds `attr["nc"] = 0` when the item's `clicks_to_build` is positive and
   `attr["si"] = []` when `properties.friend_assistable` is. Measured: **0 of
   429** units carry either, against **298 of 470** and **26 of 470** buildings.
   So `attr` is always `{}` for a unit.
3. **No price exists.** All 24 transactions left every stored resource
   byte-identical, and the branch never reads the client's vector. The sale half
   credits nothing at all — exactly one changed leaf, the store key.
4. **`map_add_item` is an assignment with no occupancy test**
   (`engine.py:31`: `map["items"][str(index)] = [...]`), and
   `remove_store_item` is conditional (`engine.py:78`: `if itemstr in
   map["store"]`). Those two conditionals are the entire cause of the four
   unguarded behaviours.
5. **The committed fresh corpus cannot seed a placement.** `tests/saves/
   fresh-player.json` has an **empty** store and an **empty** `boughtUnits`, and
   the capture harness seeds exactly one save from it.

## Goals / Non-goals

**Goals**

- Reproduce the placement and sale transactions exactly as executed.
- Derive every server-owned slot server-side, in one named function per layer.
- Fail closed on the three unguarded behaviours that destroy or duplicate state.
- Close the `unit-collection` line's recorded round-trip gap with executed
  evidence.

**Non-goals** — the proposal's non-goals list applies unchanged; the two that
constrain *design* are the M6 geometry gap (bounds and occupancy recorded, not
refused) and footprint-aware cell derivation (blocked on the same gap).

## Decisions

### D1 — The seed route is `complete_collection`, and it is the only acceptable one

Three routes can put an item in storage for a capture:

| route | client input | content-derived? | decision |
| --- | --- | --- | --- |
| `store_add_items` | an arbitrary id list | no | rejected — unvalidated grant |
| hand-edited seed save | none | n/a | rejected — a fabricated corpus |
| `complete_collection` | a collection **id** | yes | **chosen** |

The chain is `login_post` → `complete_collection(1)` → `place_stored_item`.
Collection 1's committed prize is exactly `{"1085": 1}`, Metal Draggy — a 1×1
unit — so the whole transaction set is content-derived and **no client-sent item
id list appears anywhere**. This also makes the new fixture the first
executed-legacy evidence for the collection→placement round trip, which is what
closes the carried follow-up rather than merely adding a new one.

*Why not `store_add_items`:* it reads `args[0]` as an id list and grants each
entry. Seeding a fixture through it would mean the fixture's own precondition was
established by the exact anti-pattern this project refuses. It is used in the
**probes** for that reason and is out of scope for delivery.

### D2 — `item_index` is derived server-side

The client sends `{user_id, item_id, x, y}`. The endpoint derives the map slot as
the smallest positive integer absent from `map["items"]`, which is precisely what
`placement_envelope.next_free_slot` already does and what the placement line
already ships. The corpus seeds to `41`, so the first placement is slot `41`.

This makes `slot_occupied` a *second* refusal rather than the first line of
defence, and it is the reason the refused case must be **tested** rather than
assumed unreachable: with a derived index the client cannot reach it at all, so
an occupied-index guard can only be exercised by a corpus that already has a gap
or by a deliberately injected conflict. Both are recorded in the suite.

### D3 — `attr` is derived by one shared function, and the suite asserts the client cannot reach it

The derivation is a port of `engine.map_add_item`'s `player == 1` block:

```python
attr = {}
if clicks_to_build > 0: attr["nc"] = 0
if properties.friend_assistable > 0: attr["si"] = []
```

with `player` fixed at `1` because that is the only value `map_add_item` can be
called with from this branch. `place_stored_item` never passes `playerID`, so
the client-sent team is **discarded** — executed probe evidence, recorded in the
report.

The hermetic suite asserts **no** delivered helper accepts an `attr` or a
`player` parameter, which makes "the client cannot dictate the row's bag or
team" a mechanical claim rather than a promise.

### D4 — Four refusals, and the split between refused and recorded is argued

| refusal | executed evidence | why fail closed |
| --- | --- | --- |
| `not_in_storage` | 1071 placed, never stored: rows 41→42, store unchanged, `boughtUnits` grew, `success` | duplicates an unacquired unit |
| `slot_occupied` | index 1's Command Center `[26,51,41,0,0,[],{},1]` **silently replaced**; 5 leaves rewritten, **row count unchanged** | destroys a placed building invisibly |
| `unknown_item_id` | `999999` in no normalized table placed with an empty `attr` and appended to `boughtUnits` | a row nothing can render or price |
| `item_not_placeable` | — | `get_attribute_from_item_id` yields nothing |

**Bounds are deliberately *not* refused.** `place_stored_item [43, 1085, 250,
-3, …]` stored `(250, -3)` verbatim and `item_index` `999999` became a key. That
is the already-recorded M6 geometry gap, it needs new evidence rather than a
derivation, and inventing a `0..99` bound here would fabricate a rule the oracle
does not have. The suite therefore asserts the *absence* of any bounds helper,
making the recorded gap mechanical rather than an oversight.

The distinction is not arbitrary: `slot_occupied` destroys an **existing** row
and is invisible to any count-based check, while an out-of-range coordinate
damages nothing. `building-move`, `building-sell`, and `building-store` all made
the same call for the same reason.

### D5 — The post-execution proof is two-part, and the sale's is one-part

For placement: the stored count decremented **by exactly one** **and** the row
present at the derived index carrying the derived `attr` and `player` **and** the
ledger assertion. The count half is non-tautological because the sale proves a
decrement can occur, and the row half is non-tautological because the four
probes show the row can differ from what a client asks for.

For sale: **every stored resource unchanged**, which is the whole claim, plus the
store key absent afterwards. `boughtUnits` is *not* touched by a sale, and the
suite asserts it is not.

### D6 — The fixture's volatile allowlist gains the row timestamp

`engine.py:13-14` stamps `int(time.time())` into slot 3. The placement fixture
already records this condition and its volatile allowlist; this line adds the
one entry for the storage placement, and with it the `save_after_sha256` feeds
one more volatile item. The manifest states this explicitly rather than letting
a rerun produce a digest mismatch.

### D7 — The line delivers both halves, and says why

`place_stored_item` and `sell_stored_item` sit three lines apart, share
`remove_store_item`, and are exact inverses. Shipping one without the other would
leave the round trip half-delivered and the client unable to *return* an item it
placed — and the sale is the branch with **no refund**, which is a fact a client
must be able to display honestly. Shipping them together also means the
quantity semantics (one operation consumes exactly one) is proved once and used
twice.

## Risks / Trade-offs

| risk | mitigation |
| --- | --- |
| The capture seeds its precondition through a *completion* command, so the fixture is two transactions deep | this is the `research` and `quests` chained-transaction pattern, and the seed's derivation is recorded in the fixture README |
| `slot_occupied` is unreachable through the typed client because the index is derived | the suite injects a derived index conflict and asserts the refusal; the offline suite builds its own response envelope so it **can** exercise it, and `verify-boot.ps1` inspects the envelope for the same reason the `quests` line added its guards |
| A `timestamp`-bearing row makes the fixture non-reproducible | recorded in the manifest and the README, with the exact volatile path |
| `attr` derivation ports legacy content logic into the modern layer | it is a pure function of two committed fields, ported once per layer with a round-trip assertion against all 900 normalized items, and the suite asserts no client-facing parameter exists |
| The claim "the client cannot dictate the row" is easy to state and easy to violate later | the suite asserts the absence of any `attr` or `player` parameter on any delivered helper — a guard tested by injection before it is trusted |

## Migration Plan

Single bounded line. No schema migration: the storage map and `boughtUnits` are
existing save fields the legacy server already writes. Rollback is deleting the
new endpoint pair, the envelope module, the projection, and the flow; no
persisted shape changes.

## Open Questions

None. Every decision above is forced by a measurement in the committed
investigation record. Two recorded gaps are explicitly *not* answered here and
are named in the proposal's non-goals: the M6 tile-to-cell geometry, and
footprint-aware cell derivation for the 2×2 and 3×3 collection prizes.