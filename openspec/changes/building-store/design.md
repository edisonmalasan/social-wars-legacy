# Design

## Context

See `proposal.md` — Why. Placement, purchase, move, and sell are delivered and
archived. This is the fifth change in the same family, and it reuses everything
they established: the legacy-index-addressed intent contract, the
pre-execution index resolution and row read, the post-execution proof, the
selection-driven surface, the addressable placement keys, the typed storage and
its readout, and the response-apply-with-rollback pattern.

Observed legacy facts (recorded in `docs/legacy-protocol/commands.md` row for
`store_item` and `command.py:218-232`, `engine.py:42-47`, `engine.py:70-76`):

- `store_item` takes exactly **one** positional arg — the item index. It pops the
  row with `map_pop_item`, and if the row is missing it logs an error and
  returns early (still persisting the batch). Otherwise it reads the item id
  from the popped row (`item[0]`) and calls `add_store_item(map, item_id)`,
  which increments `map["store"][str(item_id)]` with quantity 1. It writes
  nothing else — and, unlike `buy` / `place_stored_item` /
  `buy_stored_item_cash`, it does **not** call `bought_unit_add`, so a stored
  building is not appended to `boughtUnits`.
- Like every branch, `apply_resources` runs before it (command.py:40,
  engine.py:251-271) with the client-sent vector, clamped at `max(…, 0)`; the
  catalog records that the client "moves any indexed item into storage; no
  capacity check", so there is no server-side price and no capacity rule.
- The committed configuration records no price for storing anything (the same
  evidence the move and sell lines recorded: item `cost` is `"0"` and
  `cost_type` is `null` across all 778 items, `costs` prices the purchase only).
- Static SWF inventory (no execution) shows the player-facing affordance this
  change reproduces: `btPutInStorage` sits in the same building information
  panel as `btSell` and `upgradeinfo`, and an item description reads "Item might
  be moved to storage later on." Which arguments or deltas the Flash client
  sends is never observed.
- The fresh-player corpus makes the command exercisable: 40 placements keyed
  `1..40` and an **empty** `store`, so the storage mapping is directly
  observable before and after. The fixture stores the **Tree** decoration
  (item 905, 1x1) at map slot **2**, anchored at `(53, 39)`, whose row is
  `[905, 53, 39, 0, 0, [], {}, 1]` — a map decoration rather than a shop item
  (`in_store` 0), which is what the "put in storage" affordance is for, and a
  slot distinct from the move fixture's 11 and the sell fixture's 20 so the
  three fixtures stay independently readable.

## Goals / Non-Goals

**Goals:**

- One executed-legacy `store_item` transaction captured from the real legacy
  server, committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives the legacy envelope, executes the
  unchanged dispatcher in-process over the service corpus, and answers with an
  authoritative superset naming both sides of the move: what left the map and
  what landed in storage.
- One typed `GameApi.store_building()` operation with the fake/live
  implementations interchangeable behind it.
- A store confirm on the delivered selection-driven surface with exactly one
  intent, cancellation with no state change, and an authoritative apply that
  updates the town, the typed storage, and the readout and rolls back completely
  on any failure.
- Evidence, claim limits, documentation, and battery integration matching the
  delivered lines.

**Non-Goals:**

- Taking a stored item back onto the map (`place_stored_item`), selling or
  gifting a stored item (`sell_stored_item`, `CmdSellStoredItem` in the SWF), or
  granting stored items (`store_add_items`): each is a separate legacy command
  with its own argument shape, and the round trip is not needed to deliver this
  line.
- Storage capacity, expiry, or any other storage rule — legacy has none, and
  inventing one would be fabricating behavior.
- `boughtUnits` bookkeeping: `store_item` deliberately does not write it, and
  this change reproduces that exactly (asserted in the fixture and the compat
  tests) rather than "fixing" it.
- `orient`, `collect`, upgrade paths, construction timers, expansion, resources,
  XP, and any server-authoritative validation (Server v1 / M13).

## Decisions

**D1 — Store command: `store_item`.** It is the only legacy branch that moves a
placed row into storage, and its single-argument shape is the cleanest intent
contract in the family. Alternatives: `place_stored_item` (the reverse
direction — storage to map — and the later part of this deliver line, already
rejected twice as the placement and move alternatives), `sell_stored_item`
(storage to proceeds, a sale of a stored item — a different intent with a
refund question the sale line already answers), `store_add_items` (a
client-chosen item-id list with no relation to the map — the grant path, already
deferred by the purchase line).

**D2 — Neutral price vector.** The derived `resources_changed` is the all-zero
vector, the same derivation boundary the move and sell lines took: the server
computes no price, the committed configuration records no storing price, and
accepting a client-sent delta would break the intent-only contract and let a
client mint resources. Storing is therefore free in this stage, stated as a
derivation boundary rather than a claim about the legacy client.

**D3 — Intent-only contract `{user_id, item_index}`.** No price, no refund, no
reason (the branch takes no reason), no resource delta, no quantity (legacy's
`add_store_item` defaults to exactly 1). The endpoint resolves the index against
the save's own `map["items"]` before executing, because legacy's missing-item
path is a silent early return that would otherwise be reported as success.

**D4 — A superset that names both sides of the move.** Success answers with the
legacy `result`, the eight-field row **as read before execution** (the same
pre-execution record the sell line established), the **full post-execution
storage mapping**, and the current `resources`. The storage mapping is the
authoritative fact the client needs for the readout the purchase line already
renders, and returning it whole means the client performs no arithmetic for
pre-existing contents. The endpoint additionally proves both halves: the popped
key is absent from the map and the storage entry is present after execution,
failing closed otherwise.

**D5 — Validation split carried forward.** The client owns the gameplay rules
legacy never enforced — a building is storable only while it is selected,
addressable, and not already being moved or sold — while the endpoint keeps
structural fail-closed validation only (resolvable save, integer index present
in the save). Authoritative validation remains Server v1 (M13) work.

**D6 — One shared envelope derivation.** `store_envelope.py` imports the shared
helpers from `placement_envelope` and adds only what a store needs:
`build_envelope(item_index, ts=None)` producing one
`[0, "store_item", [item_index], zero_vector]` command. The four delivered
envelope modules are not refactored, so their suites and fixtures keep passing
unchanged.

**D7 — One more mode on the selection-driven surface.** The delivered surface
already offers `Move` and `Sell` for a selected addressable placement, and the
legacy UI puts "put in storage" beside "sell" in the same panel, so `Store`
joins them there and opens a targetless confirm naming the building. The move
and sell modes keep their state machines unchanged, and their suites stay
green; a fourth panel would duplicate the selection affordance for no
behavioral gain.

**D8 — The apply updates the town and the storage together.** Success applies
only the response: the rendered object is freed, the typed placement is removed
while the remaining buildings keep the committed depth order, the typed storage
is replaced through the **same fail-closed parser** the payload parse and the
purchase apply use, the storage readout re-renders from it, and the HUD
resources and XP take the response values. The apply snapshots every field it
touches first, so any failure restores the building, the previous storage view,
the readout, and the HUD — the same pre-check/rollback contract the delivered
applies implement.

**D9 — Evidence, claim limits, and containment.** A windowed fake-API capture
driving the same flow a player uses (select, store, confirm) plus a headless
deterministic `store-report-v1` report (inputs and digests, the intent, the
stored building and its cell, the storage mapping before and after, counts and
resources before/after, request counts, the projection-constants pointer, and
explicit non-claims), byte-identical across reruns. The claim-limit list
carries the delivered lines' non-claims and adds: the command's argument value
and the neutral vector are derived, never observed; storing is free in this
stage and no claim is made about the legacy client; **no capacity rule exists**;
this line only moves a building *into* storage, so the storage the player sees
is still not playable; parity covers one recorded transaction against the
fresh-player corpus. Execution and containment carry forward unchanged.

## Risks / Trade-offs

- **Storing is a one-way trip in this change** → stated in the proposal, design,
  both READMEs, the surface's status line, and the report's non-claims, and
  `place_stored_item` remains the obvious next slice rather than an omission.
  The player can always move the building back with the delivered move line or
  sell it with the delivered sell line.
- **Two writes must land atomically from the client's point of view** → the
  endpoint proves both halves and the apply is one snapshot-and-rollback step
  (D8), so a partially applied store is impossible: either the response is
  applied whole or nothing changes.
- **The storage mapping now arrives from two different endpoints** (bootstrap,
  purchase, and now store) → all three are parsed by the same `TownState`
  storage parser, so one rule set governs every entry point; the compat tests
  and the client suite both assert the shape.
- **Adding a third mode to one surface grows it** → the modes are mutually
  exclusive (arming one refuses the others), each keeps its own state, and the
  delivered suites prove the earlier modes are unchanged; a regression there
  fails in an existing suite rather than hiding behind the new one.
- **A second free client action on every building** (move and store both cost
  nothing in this stage) → the claim limits say so explicitly, so the player
  economy is not mistaken for a delivered rule; the real economy stays with
  Server v1 (M13) and the later *resources* line.
