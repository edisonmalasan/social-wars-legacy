# Design

## Context

See `proposal.md` — Why. Placement, purchase, and move are delivered and
archived; this is the disposal counterpart to the move line, and it reuses the
same delivered machinery: the legacy-index-addressed intent contract, the
pre-execution index resolution, the selection-driven surface, the addressable
placement keys, and the response-apply-with-rollback pattern.

Observed legacy facts (recorded in `docs/legacy-protocol/commands.md` row for
`sell` and `command.py:149-168`, `engine.py:36-52`):

- `sell` takes exactly two positional args — `item_index` and `reason`. It
  resolves the row with `map_get_item(map, item_index)`, deletes it with
  `map_delete_item`, and writes nothing else. `reason == "KILL"` additionally
  routes the row through `push_dead_unit`, which may mark a unit resurrectable
  in `privateState.deadHeroes`; every other reason is only a log label. A
  missing item logs an error and returns early, still persisting the batch.
- Like every branch, `apply_resources` runs before it (command.py:40,
  engine.py:251-271) with the client-sent vector, clamped per resource at
  `max(…, 0)`; the catalog records that the **refund travels entirely through
  those deltas** — the server computes no price.
- Legacy performs no ownership, price, or state check: "Client chooses the
  victim item and the reason; resurrectability is a server-side lookup, not a
  client flag."
- **No building-sale refund rule exists in the committed configuration.** Item
  `cost` is `"0"` and `cost_type` is `null` across all 778 items (dead fields),
  `costs` prices the purchase only, and the money-adjacent globals are market
  constants — `MARKET_SELL_PERCENTAGE` (0.75) sits next to `MARKET_BASE_COSTS`
  and `MARKET_AMOUNT_TRADE` and governs the *resource* market ("SELL 100 WOOD
  ON MARKET"), not building sales. The client's own `DIVISOR_SELL` constant
  appears in the SWF string pool without a value, and the `Sell for #0#` UI
  template means the Flash client computes a refund the repository never records.
- Static SWF inventory (no execution) shows the sell surface and its reason
  vocabulary: `btSell` / `btnSell` / `buttonSell`, `CmdSell`, and
  `SELL_REASON_KILL`, `SELL_REASON_BULLDOZE`, `SELL_REASON_UPGRADE`,
  `SELL_REASON_TREASURE`, `SELL_REASON_ACTIVATOR` and others — no reason
  specific to a player-initiated sale, so the reason the Flash client sends for
  "sell this building" is unobserved.
- The fresh-player corpus makes the command exercisable: 40 placements keyed
  `1..40`, including **Turret I (item 22, 1x1) at slot 20 anchored at
  `(41, 48)`** — the second Turret I in map-slot order, chosen so this
  fixture's target differs from the move fixture's slot 11 and the two fixtures
  stay independently readable.

## Goals / Non-Goals

**Goals:**

- One executed-legacy `sell` transaction captured from the real legacy server,
  committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives the legacy envelope, executes the
  unchanged dispatcher in-process over the service corpus, and answers with an
  authoritative superset naming exactly what was removed.
- One typed `GameApi.sell_building()` operation with the fake/live
  implementations interchangeable behind it.
- A sell confirm on the delivered selection-driven surface, with exactly one
  intent, cancellation with no state change, and an authoritative apply that
  rolls back completely on any failure.
- Evidence, claim limits, documentation, and battery integration matching the
  delivered lines.

**Non-Goals:**

- **The refund policy.** Nothing in the repository states what a legacy sale
  refunds, so the derived vector is neutral and the service claims no refund
  (see D2). Refund economics, like the rest of the economy, belong to Server v1
  (M13) and to the later *resources* deliver line.
- The combat `KILL` reason and the resurrectable-hero path (M9+), the storage
  commands, `orient`, `collect`, upgrades, construction timers, expansion,
  resources, and XP.
- Server-authoritative anti-cheat validation and any change to legacy behavior.

## Decisions

**D1 — Sell command: `sell`.** It is the only legacy branch that removes a
placed row on a player-initiated basis. Alternative: `sell_stored_item` (removes
from *storage*, not the map — the later *store* line, and already out of scope
for the map), or `batch_remove` (a combat/batch path) — rejected.

**D2 — Neutral price vector, and no refund claim.** The derived
`resources_changed` is the all-zero vector, the same boundary the move line took
and for the same reason: the server computes no price, the committed config
records no building-sale refund rule, and accepting a client-sent refund would
break the intent-only contract and let any client mint resources. The player
therefore sees a sale that removes the building and changes no balance, and
every artifact states plainly that this is a **derivation boundary, not a claim
that selling is free** — the legacy client's refund is computed in the Flash
client and is unobserved.

**D3 — The reason is derived, never chosen.** The envelope carries
`args = [item_index, ""]`. The endpoint accepts no reason from the client, so no
client can claim `"KILL"` and reach `push_dead_unit`; that path belongs to combat
and is out of scope here. The empty string is a documented placeholder: legacy
compares it against `"KILL"` and otherwise uses it as a log label, so the empty
reason is behaviorally inert — but the value the Flash client actually sends is
unobserved, and this change therefore claims nothing about it.

**D4 — Intent-only contract `{user_id, item_index}`.** No price, no refund, no
reason, no resource delta. The endpoint resolves the index against the save's
own `map["items"]` before executing (the move line's precedent): legacy's
missing-item path is a silent early return that still persists, so accepting it
would claim a removal that never happened. After execution the endpoint verifies
the key is gone and fails closed if it is not.

**D5 — An authoritative superset that names the removal.** Success answers with
the legacy `result`, the eight-field row **as read before execution** (so the
client can match exactly what disappeared, including its cell and legacy key),
and the current `resources`. The row is deliberately the *pre-execution* one: the
persisted save no longer holds it, and reconstructing it after the fact would be
fabrication. The endpoint additionally proves removal by re-reading the map
after execution and failing closed if the key survives.

**D6 — Validation split carried forward.** The client owns the gameplay rules
legacy never enforced — a building is sellable only while it is selected and
addressable, and the confirm is the only way to reach the intent — while the
endpoint keeps structural fail-closed validation only (resolvable save, integer
index present in the save). Authoritative validation remains Server v1 (M13)
work, and anti-cheat is unaffected by this change's scope.

**D7 — One shared envelope derivation.** `sell_envelope.py` imports the shared
helpers from `placement_envelope` (`is_strict_int`, `ENVELOPE_KEYS`,
`payload_json`, `data_field`, `parse_data_field`, `EnvelopeError`) and adds only
what a sell needs: `build_envelope(item_index, reason="", ts=None)` producing one
`[0, "sell", [item_index, reason], zero_vector]` command. The three delivered
envelope modules are not refactored, so their suites and fixtures keep passing
unchanged.

**D8 — A sell mode on the delivered selection-driven surface.** The move line's
surface is already the selection-driven one (it enables `Move` for an
addressable selection), so `Sell` joins it there and opens a confirm showing the
building's name; the move mode, its preview, and its confirm are untouched and
its suite stays green. A third panel would duplicate the selection affordance
for no behavioral gain, and a sell has no grid target, so it reuses the same
panel's status line and its confirm/cancel row in a second mode. The delivered
placement picker and shop surfaces are not involved.

**D9 — The apply removes and can rebuild.** Success applies only the response:
the selected placement is removed from the typed state and its rendered object is
freed, the remaining objects keep the committed depth order, and the HUD
resources and XP take the response values. The apply captures everything it
touches first, so a failure at any step restores the placement at its original
index, re-attaches the object, and re-renders the HUD — the same
pre-check/rollback contract the placement, purchase, and move applies already
implement.

**D10 — Evidence, claim limits, and containment.** A windowed fake-API capture
driving the same flow a player uses (select, sell, confirm) plus a headless
deterministic `sell-report-v1` report (inputs and digests, the intent, the
removed row and cell, placement and object counts before/after, resources,
request counts, the projection-constants pointer, and explicit non-claims),
byte-identical across reruns. The claim-limit list carries the delivered lines'
non-claims and adds: the command's reason value and the neutral vector are
derived, never observed; **no refund is claimed**; the combat `KILL` path is
never reached; parity covers one recorded transaction against the fresh-player
corpus. Execution and containment carry forward unchanged: unchanged legacy
`command()` in-process over a disposable corpus, loopback only, no new packages,
both batteries plus the guard baseline and the 3,258-entry hash manifest green
in the final state, and the orchestrator-run integration review as the fallback
for the unavailable dedicated verification workflow.

## Risks / Trade-offs

- **A player sells for nothing in this stage** → the behavior is legacy's own
  (the server applies only client-sent deltas and we refuse those), the limit is
  stated in the proposal, design, both READMEs, and the report's non-claims, and
  the economics are explicitly deferred to Server v1 (M13) and the *resources*
  deliver line rather than being invented here.
- **Losing a rendered object is the first destructive apply in the client** →
  the apply snapshots the placement, its index, the object, and every resource
  before mutating, and rolls all of them back on failure; the whole battery
  (including the placement, purchase, move, selection, and town-scene suites)
  runs in the final state.
- **A client could claim the `KILL` reason to resurrect units** → the endpoint
  never accepts a reason (D3), so the only derived value is the empty string and
  `push_dead_unit` is unreachable through this surface.
- **The removed row is captured pre-execution** → it is documented in D5 as the
  authoritative record of what the client asked to remove, and the endpoint
  separately proves the row is absent from the persisted save, so the two facts
  cannot drift.
- **Perturbing the delivered move surface** → the sell action is additive, the
  move mode's preview/confirm state machine is unchanged, and `test_town_move`
  plus the rest of the battery must stay green; any regression is visible in the
  existing suite rather than hidden behind the new one.
