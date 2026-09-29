# Design

## Context

See `proposal.md` — Why. Placement and purchase are delivered and archived, so
the client can put a new building on the map and buy one into storage; it cannot
reposition a building the player already owns. This change reuses the delivered
structure end to end and adds one new piece of state the client does not yet
hold: each placement's legacy map key, which is what a legacy `move` command
addresses.

Observed legacy facts (recorded in `docs/legacy-protocol/commands.md` row for
`move` and `command.py:119-134`, `engine.py:36-40`):

- `move` takes exactly five positional args — `item_index`, `x`, `y`, `frame`,
  `string`. It resolves the row with `map_get_item(map, item_index)`, i.e.
  `map["items"][str(item_index)]`, then writes `item[1] = x` and `item[2] = y`
  and nothing else. `frame` and `string` are read and discarded; a missing item
  logs an error and returns early, so an unknown index is a silent no-op that
  still persists the save.
- Like every branch, `apply_resources` runs before it (command.py:40,
  engine.py:251-271) with the client-sent vector, clamped per resource at
  `max(…, 0)`.
- Legacy performs no ownership, bounds, collision, or price check: the catalog
  records "Client repositions any indexed item; no ownership, collision, or
  bounds check."
- The committed config carries no move price. Every item's `cost` is `"0"` and
  every `cost_type` is `null` over all 778 items (dead fields), `costs` prices
  the *purchase* only (`{"g":…}`, `{"w":…}`, `{"s":…}`, `{"c":…}`), and none of
  the 104 globals records a move cost (the money-adjacent ones are
  `MARKET_SELL_PERCENTAGE`, `MARKET_BASE_COSTS`, `PERMISSION_COSTS`,
  `COST_HURRY_UP`, `COST_MANA_CASH`, `COST_MANA_GOLD`, `ENERGY_COSTS`,
  `ENERGY_CONSTRUCTION_COST`, `DART_COST_CASH`, `NEWS_STORE`).
- The fresh-player corpus makes the command exercisable: 40 placements keyed
  `1..40`, among them Turret I (item 22, 1x1) at slot 11 anchored at
  `(58, 48)`. Its free one-step neighbours are `(57, 48)` and `(58, 47)`;
  `(59, 48)` and `(58, 49)` hold Wall I rows. With the placement fixture's
  documented rule (Manhattan-nearest free cell, ties broken row-major by
  smallest `y` then smallest `x`) the derived target is `(58, 47)`.
- Static SWF inventory (no execution) shows the move surface exists — the
  MultiTool "MOVE" cursor instructions, `btMove`-class names such as
  `moveItem` / `moveToPosition`, and an item description reading "Item might be
  moved to storage later on." — and shows no move-cost string. Which arguments
  or deltas the Flash client sends for a move is never observed, so the
  envelope below is derived-provisional exactly as the placement and purchase
  envelopes were.

## Goals / Non-Goals

**Goals:**

- One executed-legacy `move` transaction captured from the real legacy server,
  committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives the legacy envelope, executes the
  unchanged dispatcher in-process over the service corpus, and answers with the
  authoritative superset (persisted placement entry + resources).
- One typed `GameApi.move_building()` operation with the fake/live
  implementations interchangeable behind it.
- Placements that carry their legacy map key, so the client can name the target
  and can refuse an unaddressable key explicitly.
- A move surface whose confirm sends exactly one intent, whose refusals send
  nothing, and whose success applies only the response.
- Evidence, claim limits, documentation, and battery integration matching the
  placement and purchase bars.

**Non-Goals:**

- No behavior of the later M7 deliver lines (`sell`, the storage commands,
  `upgrade` paths, construction timers, `collect`, expansion, resources, XP) and
  no `orient` (flip), which the second-implementation backlog lists separately.
- No client-side occupancy, bounds, or ownership *enforcement* beyond the
  documented display rules: the client marks invalid targets and sends nothing,
  and the endpoint keeps structural fail-closed validation only.
- No server-authoritative anti-cheat validation (Server v1 / M13) and no change
  to legacy behavior.
- No multi-item move, no rotation during a move, and no move of a stored item
  (storage placement is the later *store* line).

## Decisions

**D1 — Move command: `move`.** It is the only legacy branch that repositions a
placed item, it takes the item's map index plus a target cell, and it writes
nothing else. Alternative: `orient` (only rewrites `item[4]`, and it is a
separate backlog item) — rejected as a different deliver line; `place_stored_item`
plus `store_item` (storage round trip) — rejected as the later *store* line,
already rejected once as the placement alternative.

**D2 — Neutral price vector.** The derived `resources_changed` is the all-zero
vector. Rationale: the committed config records no move price at all (dead
`cost`/`cost_type`, purchase-only `costs`, no global), so no price is derivable;
inventing one from the item's purchase price would be fabricating behavior, and
accepting a client-sent price would break the intent-only contract the two
delivered lines established. A zero vector is also the only choice that cannot
corrupt a resource balance, and legacy's own per-resource `max(…, 0)` clamp
means an observed Flash price, if one exists, would be recorded in the deltas we
never observe. This is a derivation boundary, stated as a claim limit: the
service claims neither that moving is free in the legacy client nor that it
costs anything — it claims that the price this change derives is neutral and
that the Flash-sent vector is unobserved.

**D3 — Intent-only contract `{user_id, item_index, x, y}`.** No client-supplied
resource delta, no price, no `frame`/`string` (the client never chooses values
legacy discards). `item_index` is the legacy map key as an integer; the endpoint
requires it to resolve to a row in the corpus's `map["items"]` before executing.
Every error path returns before the dispatcher runs, so the corpus is untouched
on failure (carry-forward).

**D4 — Reuse the placement superset shape.** Success answers with the legacy
`result` plus the persisted eight-field `placement` entry (the same row the
placement endpoint returns, re-read from the save after execution) and the same
`resources` object. Rationale: the authoritative superset for "this row now
sits at this cell" is identical to the delivered placement response, so the
client reuses one typed result class and one parse function instead of growing
a parallel shape; the endpoint path and the request contract are what differ.

**D5 — Validation split carried forward.** The client owns the gameplay rules
the legacy server never enforced — the anchor-in-grid display bound, footprint
occupancy *ignoring the moving building's own cells*, and refusing a no-op move
to the cell the building already occupies. The endpoint keeps structural
fail-closed validation only (resolvable save, integer item index present in the
corpus, integer in-grid coordinates), so an out-of-bounds or overlapping target
is a client-side refusal, never a server rejection, and anti-cheat validation
remains Server v1 (M13) work.

**D6 — One shared envelope derivation.** `move_envelope.py` imports the shared
helpers from `placement_envelope` (`is_strict_int`, `ENVELOPE_KEYS`,
`payload_json`, `data_field`, `parse_data_field`, `EnvelopeError`, `GRID_EXTENT`,
`in_grid`) and adds only what a move needs: `build_envelope(item_index, x, y,
frame=0, string="", ts=None)` producing one
`[0, "move", [item_index, x, y, frame, string], zero_vector]` command. The
placement and purchase modules are not refactored, so their suites and fixtures
keep passing unchanged.

**D7 — Placements carry their legacy key.** `TownState.Placement` gains the map
key the row was parsed from. A key that is not a positive integer is stored as
no addressable slot (never coerced to 0, which would address a real row), and
the move flow refuses such a placement with an explicit reason — a save shape
legacy itself could not address, since `map_get_item` looks up `str(index)`.

**D8 — A move surface beside the placement picker and the shop.** The move
panel is its own UI-foundation slot, armed from the delivered selection path
(selecting a placed building offers a `Move` action; pressing it enters move
mode), reusing the existing footprint preview overlay with the moving building's
own cells excluded from occupancy. Rationale: the placement picker's flow is
preview-driven from a catalog of *not yet owned* items and its state is
placement-local, while a move starts from an *owned* row and must address it by
legacy index; keeping them apart leaves both delivered surfaces untouched. The
selection wiring is included because without it the line is not reachable by a
player; it adds no state and no request.

**D9 — Evidence and claim limits.** A windowed fake-API capture driving the
same flow a player uses (select, arm, preview, confirm) plus a headless
deterministic `move-report-v1` report (inputs and digests, the intent, the
placement count and cell before/after, resources, request counts, the
projection-constants pointer, and explicit non-claims), byte-identical across
reruns. The claim-limit list carries the delivered lines' non-claims and adds:
the command's argument values, the discarded `frame`/`string`, and the neutral
price vector are derived, never observed from the Flash client; occupancy and
bounds rules are client-side only; parity covers one recorded transaction
against the fresh-player corpus.

**D10 — Execution and containment carried forward.** The unchanged legacy
`command()` runs in-process over a disposable corpus and persists only through
legacy `save_session` into that corpus; loopback only; no new packages; both
batteries, the Compatibility API guard baseline, and the 3,258-entry hash
manifest green in the final state. No dedicated OpenSpec verification workflow
is installed, so the fallback is orchestrator-run strict validation,
independent verification where possible, both batteries, and final diff review.

## Risks / Trade-offs

- **The neutral price may differ from the legacy client** → the price is a
  derivation boundary with no config source; the fixture and both READMEs state
  that no claim is made about the Flash-sent vector, and no client-sent price is
  ever accepted, so the risk is bounded to a claim limit rather than a behavior
  divergence inside the service.
- **A move is the first intent that addresses an *existing* row**, so an unknown
  or stale index is a real failure mode → the endpoint resolves the index against
  the corpus before executing (404 `unknown_item_index`), legacy's silent
  early-return is never used as a success signal, and the client's stale-state
  case is a structured failure with no state change.
- **Repositioning a rendered object risks depth-order and HUD regressions** →
  the apply reuses the delivered placement rollback structure, re-sorts the
  object with the existing depth comparator, and the whole placement, purchase,
  selection, and town-scene suites stay in the battery.
- **Key parsing could coerce or drop a legacy key** → D7 stores the key as
  parsed and records an unaddressable key rather than coercing; the parse is
  covered in the town-state suite alongside the storage cases.
- **Larger client surface in one deliver line** → bounded to a single intent, a
  single command, a single fixture transaction, and one committed evidence
  pair, with the two delivered surfaces left untouched so a regression there is
  visible in the existing suites.
