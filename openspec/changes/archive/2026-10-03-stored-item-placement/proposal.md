# Proposal

## Why

The delivered `unit-collection` line recorded its own carried follow-up in its
claim limits: *"the stored-item placement step is not delivered, so the fixture
evidences the grant into storage and **not** a unit placed on the map, leaving
that round trip a carried follow-up."* `docs/legacy-m9-assessment.md` (PR #270)
then named it the nearest undelivered step on a fully content-derived path, and
`capture_collection_fixture.py`'s manifest has carried the key
`"stored_item_placement_chained": False` ever since.

The committed investigation (`docs/legacy-stored-unit-placement.md`, PR #271)
settled the contract with **24 executed-legacy probe transactions** in two
contained runs and found this is **not** a refusal line:

* `place_stored_item` (`command.py:233-248`) is reachable, mutates real state,
  and is **type-agnostic** — it places a unit and a building identically;
* **no price exists and none moves** — every one of the 24 transactions left
  every stored resource byte-identical;
* the placed row is **server-derived in five of its eight slots**, so a client
  cannot dictate the result even by sending the shape;
* `sell_stored_item` (`command.py:250-256`) is the same round trip in reverse
  and **pays no refund at all**;
* and four behaviours the legacy server does not guard were each **confirmed by
  execution**, three of which a modern endpoint must refuse.

It also **corrects** the assessment: **four of the ten committed collection
prizes are buildings**, not units, three of them needing a build click and two
occupying more than one cell. The line's scope must therefore be written against
the **prize**, not the word "unit".

## What Changes

- **New capability `godot-stored-item-placement`**, delivering the storage
  round trip:
  - A typed, read-only **storage projection** over `maps[0]["store"]` and
    `privateState.boughtUnits`, reporting the committed count and ledger
    verbatim, failing closed on a non-mapping store or a non-integer count.
  - Two **intent-only** operations. `POST /v0/place_stored` takes
    `{user_id, item_id, x, y}` (+ optional `orientation`) and derives
    `item_index` server-side as the smallest positive absent slot; the client
    never sends an index, a row, an `attr` bag, a player team, or a price.
    `POST /v0/sell_stored` takes `{user_id, item_id}` and credits **nothing**,
    because the legacy branch credits nothing.
  - A **content-derived row derivation** shared by both layers: `timestamp` from
    the server clock, `store` always `[]`, `player` always `1`, and `attr` a
    pure function of the committed item's `clicks_to_build` and
    `properties.friend_assistable` — the same function `engine.map_add_item`
    applies, never a client input.
  - **Four named refusals** with codes: `not_in_storage`, `slot_occupied`,
    `unknown_item_id`, `item_not_placeable`. Each is a **deliberate divergence**
    — the legacy server answers `{"result":"success"}` in all four cases — and
    each is justified by an executed probe recorded in the fixture manifest.
  - A **two-part post-execution proof**: the stored count decremented by exactly
    one **and** the row present at the derived index with the derived `attr`,
    plus the ledger assertion that it gained the id *only if newly present*.
    `boughtUnits` counts **distinct ids**, never units held.
  - An **executed-legacy fixture** chained `complete_collection(1)` →
    `place_stored_item`, in which every transaction is content-derived and **no
    client-sent item id list appears anywhere** — the seed route the
    investigation chose over `store_add_items` and over a hand-edited save.
  - A Godot **placement-from-storage flow** reusing the delivered
    `building-store` projection and the `unit-instances` row typing.

- **Modification to `godot-compatibility-boot`**: the two new endpoints, their
  refusals, and the fixture's post-execution proof.

## Non-goals

- **`store_add_items` is out of scope.** It is an unvalidated client-sent id
  list that grants into storage; `unit-production` already recorded it as an
  acquisition anti-pattern.
- **Grid bounds and cell occupancy are recorded, not refused.** This is the
  **already-recorded** M6 tile-to-cell geometry gap. The legacy server validates
  neither, the gap needs new evidence rather than a derivation, and inventing a
  bound here would fabricate a rule. `slot_occupied` is refused because placing
  onto an occupied index is *silent destruction of an existing row*, which is a
  different and far more serious failure than an out-of-range coordinate.
- **No footprint-aware cell derivation.** Necessary for the 2×2 General Sculpture
  and the 3×3 Fountain prizes, blocked on the same M6 geometry gap. A 1×1 prize
  needs none, so the line ships on Metal Draggy and records the rest.
- **No price, no resource movement, and no refund** — reproduced, not invented.
- **No acceptance tests.** The legacy server has none and authoring some would
  invent a rule.
- **No `GameApi` behaviour beyond two additive forwarders**, matching the 15
  existing ones.

## Impact

- **Affected specs:** `godot-stored-item-placement` (new),
  `godot-compatibility-boot` (modified).
- **Affected code:** `apps/compat-api/` — a new `stored_placement_envelope.py`,
  a new `capture_stored_placement_fixture.py`, two endpoints and a `GameApi`
  facade pair in `compat_service.py`, a new parity test module.
- **Affected client:** `apps/client-godot/scripts/` — a storage projection, a
  placement flow, and a hermetic suite.
- **Preservation:** nothing in `command.py`, `engine.py`, `config/`, `villages/`,
  `tests/saves/`, `packages/`, or any committed fixture is modified. The capture
  runs the legacy server in a disposable temp copy on `127.0.0.1:5055` and
  digest-pins the working tree before and after, as every capture in this project
  does.
- **Claim limits carried from the investigation:** the row's `timestamp` is a
  wall-clock reading, so the fixture's `after.json` is not byte-stable across
  reruns and the volatile allowlist gains that entry; the neutral 8-slot vector
  is derived-provisional and the branch never reads it; parity covers **one**
  recorded placement transaction and one recorded sale against the fresh-player
  corpus; the derived cell `(58,47)` is the one `building-move` already shipped;
  and the four refusals are divergences, not parity.