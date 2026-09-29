# Design

## Context

See `proposal.md` — Why. The placement change (archived as
`2026-09-29-building-placement`) delivered M7's first deliver line: a build
picker over a fail-closed catalog parse, a footprint preview, and one
`GameApi.place_building()` intent executed by the unchanged legacy `buy` path
through `POST /v0/place`, with an executed-legacy fixture and a live battery
phase as parity evidence. This change reuses that exact structure for the
*purchase* deliver line and adds one new piece of state the client does not yet
hold: the player's storage (`map["store"]`).

Observed legacy facts (all already recorded in `docs/legacy-protocol/commands.md`
row 49 and `command.py:475-480`, `engine.py:70-89`):

- `buy_stored_item_cash` takes exactly one positional arg (the item id), calls
  `bought_unit_add(save, item_id)` and `add_store_item(map, item_id)`
  (quantity defaults to 1), and performs no validation of its own.
- Like every dispatcher branch, it runs after the pre-dispatch
  `apply_resources(save, map, resources_changed)` (command.py:40,
  engine.py:251-271), which clamps every resource at `max(…, 0)`; the price
  travels only in those client-sent deltas.
- `add_store_item` increments `map["store"][str(item_id)]`; `bought_unit_add`
  appends the item id to `privateState.boughtUnits` when absent.
- The fresh-player corpus makes the command exercisable: `cash` 5, `store` `{}`,
  `boughtUnits` `[]`, `map.level` 1, and item 105 "Victory Arch" is store-listed
  (`in_store` 1), `min_level` 1, and priced `costs = {"c": 5}`.
- Storage in real saves holds both buildings and units and may hold quantity
  `0` (`villages/Nerri.json`), so a storage readout must render ids it cannot
  resolve rather than drop them.
- The legacy log line for this branch reads "Bought … from unit collection"
  while the archived placement design grouped `buy_stored_item_cash` among the
  deferred "stored/cash purchase" flows; which command the Flash client sends
  for a shop purchase is never observed (Flash is never executed), so the
  choice below is recorded as derived-provisional, exactly as the placement
  envelope placeholders were.

## Goals / Non-Goals

**Goals:**

- One executed-legacy `buy_stored_item_cash` transaction captured from the real
  legacy server, committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives the legacy envelope, executes the
  unchanged dispatcher in-process over the service corpus, and answers with an
  authoritative superset (storage mapping + resources).
- One typed `GameApi.purchase_item()` operation with the fake/live
  implementations interchangeable behind it.
- A shop surface whose confirm sends exactly one intent, whose refusals send
  nothing, and whose success applies only the response's authoritative values.
- Typed storage parsed fail-closed from the payload the client already receives,
  visible in a storage readout.
- Evidence, claim limits, documentation, and battery integration matching the
  placement change's bar.

**Non-Goals:**

- No behavior of the later M7 deliver lines: `place_stored_item`,
  `store_item`, `sell_stored_item` (storage→map, map→storage, selling), `move`,
  `upgrade`, construction timers, income, expansion, resources, XP.
- No `store_add_items` (batch grant), `buy_si_help` (construction help),
  `complete_collection`, `win_daily_bonus`, offers, training, or monetization
  commands.
- No server-authoritative affordability, ownership, or anti-cheat validation
  (Server v1 / M13), and no change to legacy behavior.
- No quantity parameter (legacy `add_store_item` adds exactly one), no
  multi-item purchase, no placement of the purchased item.

## Decisions

**D1 — Purchase command: `buy_stored_item_cash`.** It is the only legacy branch
that both names a purchase and writes purchase state (`bought_unit_add` +
`add_store_item`) for a single item, which matches a one-item intent contract.
Alternatives considered: `store_add_items` (a batch of client-chosen item ids
with no price semantics of its own — reads as the reward/grant path used by
"your reward has been placed at the store" flows, and is a list contract);
`buy_si_help` (construction help; needs an `si` attribute and has no derivable
config price, so the price could not be derived rather than invented);
`place_stored_item` (already rejected as the placement deliver line; it is the
later *store* line). Consequence: the Flash client's actual shop command
remains unobserved and is recorded as a claim limit.

**D2 — Cash-only price derivation.** The endpoint derives exactly the `c`
component of the item's raw config `costs` (a JSON-encoded string) into slot 6
of the legacy 8-slot vector `[unknown, xp, gold, wood, oil, steel, cash, mana]`
and zeroes the rest; the envelope carries one command
`[0, "buy_stored_item_cash", [item_id], vector]`. An item whose parsed `costs`
is not exactly `{"c": N}` (absent, empty, another resource, or mixed) fails
closed with a structured `costs_not_cash` error before the dispatcher runs.
Rationale: the command's name, `docs/legacy-protocol/commands.json` ("Cash
price travels through client-sent deltas"), and the SWF's "Buy with Cash"
surface all scope this path to cash. Alternative: reuse the full placement
`cost_vector` and let any resource price ride a cash-named command — rejected
because a resource-priced storage purchase is not derivable to this command and
any-price storage acquisition is the deferred `store_add_items` path; the
restriction is a derivation boundary, not a gameplay rule. Unresolvable config
(`costs_invalid`) stays a 500 exactly as in placement; `costs_not_cash` is a
400 because the client should not have offered the item.

**D3 — Intent-only contract `{user_id, item_id}`.** No client-supplied resource
deltas, no price, no quantity, no slot or coordinates (carry-forward of the
placement contract). Every error path returns before the legacy dispatcher runs,
so the corpus is untouched on failure (carry-forward).

**D4 — Authoritative superset response.** Success answers with the legacy
`result` plus the full post-execution `store` mapping (a `{str(item_id): int}`
copy of `map["store"]`) and the same `resources` object the placement endpoint
returns (`xp`, `gold`, `wood`, `oil`, `steel`, `cash`, `mana`). The client
replaces its storage view and its resource values from the response; it never
computes a delta, and a failed apply rolls every write back. Returning the
whole storage mapping (not just the purchased entry) keeps the client free of
arithmetic for pre-existing contents, mirroring how placement returned the
persisted entry it could not otherwise reconstruct.

**D5 — Validation split carried forward.** The client owns the gameplay rules
the legacy server never enforced — the level gate (catalog `min_level`) and cash
affordability; the endpoint keeps structural fail-closed validation only.
Insufficient cash therefore reproduces legacy clamping (`max(…, 0)`), never a
rejection, exactly as placement does; authoritative validation belongs to
Server v1 (M13). The client refuses locally and sends nothing when the price
exceeds current cash, so the clamp path is proven at the endpoint by a test
rather than relied on by the player flow.

**D6 — One shared envelope derivation.** `purchase_envelope.py` imports the
placement envelope's shared, already-public helpers (`is_strict_int`,
`ENVELOPE_KEYS`, `payload_json`, `data_field`, `parse_data_field`,
`EnvelopeError`, `COST_SLOTS`) and adds only what purchase needs: the
cash-only price vector and `build_envelope(item_id, costs, ts=None)`. The
placement module is not refactored (no rename, no moved symbols), so the
placement suite and fixture keep passing unchanged and the placement
derivation remains exactly as documented.

**D7 — Typed storage parsed fail-closed.** `TownState.State` gains
`storage: Dictionary` (string item id → integer quantity) parsed from
`map["store"]` by one static parser reused by the bootstrap parse and the
purchase apply. Rules: absent → recorded in `missing` (the readout names it);
present but not an object, or a quantity that is not an integer, or a key that
is not an item id → reject naming the key, as the placement rows do. Quantity
`0` is preserved verbatim (observed in real saves) and never dropped. Names
come from `ContentRegistry` when resolvable; unresolved ids render as the raw
id, never a guessed name.

**D8 — Shop surface beside, not inside, the placement picker.** A "Shop" panel
in its own UI-foundation slot, built from the same fail-closed catalog parse and
filtered to store-listed, level-eligible, cash-priced entries (11 of the 14
level-1 store-listed entries of the fresh save), with each entry's price shown
against current cash, a purchase confirm, a cancel, a status line, and the
storage readout. Rationale: the placement picker's flow is preview-driven and
its selection/preview state is placement-local; adding a second action there
would couple purchase to a mode it does not need and risk perturbing a
verified deliver line. Presentation remains provisional (no captured legacy
shop layout), like the HUD and picker.

**D9 — Evidence and claim limits.** A windowed fake-API capture driving the same
flow a player uses (enter shop, pick entry, confirm) plus a headless
deterministic `purchase-report-v1` report (inputs and digests, the intent,
storage and resource before/after, request counts, the projection-constants
pointer, and explicit non-claims), byte-identical across reruns. The claim-limit
list carries placement's non-claims and adds: the command choice and the
cash-only derivation are derived, never observed from the Flash client; storage
is display-only here (no placing from or selling out of storage); the committed
capture runs the fake double, not the live service.

**D10 — Execution and containment carried forward.** The unchanged legacy
`command()` runs in-process over a disposable corpus, persists only through
legacy `save_session` into that corpus, listens on loopback only, adds no
packages, and keeps both batteries, the Compatibility API guard baseline, and
the 3,258-entry hash manifest green in the final state. No dedicated OpenSpec
verification workflow is installed, so the fallback is orchestrator-run strict
validation, independent verification, both batteries, and final diff review.

## Risks / Trade-offs

- **Wrong legacy command for a real shop purchase** (Flash unobservable) → the
  choice is recorded as derived-provisional in the proposal, design, README,
  and report non-claims; the executed-legacy fixture proves the behavior of the
  chosen path, not Flash's button wiring.
- **Cash-only restriction may exclude a real resource-priced storage purchase**
  → the restriction is a fail-closed derivation boundary with a structured
  error; `store_add_items` remains the candidate for any-price storage
  acquisition in a later change, and the spec does not claim gold-priced
  storage purchases exist or do not exist.
- **A purchased item is not yet usable** (no `place_stored_item` until the
  later *store* line) → the storage readout makes ownership and the cash
  payment visible, and the roadmap's deliver order is preserved rather than
  reordered.
- **Fake double could diverge from legacy** → parity rests on the compat
  fixture-replay tests and the `purchase-live` battery phase asserting a
  disposable corpus save mutated; the fake is documented as a test double and
  never a parity oracle.
- **Storage holds items the catalog cannot resolve** (units in real saves) →
  the readout renders the raw id with no guessed name; the parser never drops
  unknown ids (carry-forward of the placement unresolved-id precedent).
- **Larger client surface in one deliver line** (shop panel + readout + apply +
  evidence) → the flow is bounded to a single intent, a single command, a
  single fixture transaction, and one committed evidence pair, and the
  placement deliver line's code path is left untouched so a regression there is
  visible in the existing suites.
