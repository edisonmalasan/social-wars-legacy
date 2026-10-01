# Proposal

## Why

M8 has delivered three of its eight lines: `unit definitions`, `unit instances`, and
`queues`. Line 4 is `production`, and its investigation is committed as
`docs/legacy-unit-production.md` (PR #219). That investigation's finding is **stronger than
the queues line's recorded "no completion exists"**, and it is stated three independent ways:

- **The legacy server cannot produce a unit at all.** `command.py`'s only
  `map_add_item` / `map_add_item_from_item` call sites are five branches — `buy`,
  `place_stored_item`, `weekly_reward`, `pop_unit`, and `resurrect_hero` — and **four of the
  five take the item id straight from the client**. The fifth (`pop_unit`) moves a row that
  already existed. **Not one** derives an id from a completed queue, from a duration, or from
  any committed production rule.
- **`training_time` has zero legacy consumers.** The only three substring matches across
  `command.py`, `engine.py`, `sessions.py`, `server.py`, `constants.py`, and
  `get_game_config.py` are `sm_training_time` inside `soulmixer_speedup` — a **different
  field**, on the soul-mixer path (three occurrences, all inside that branch). So a
  building's committed `training_time` is read by **nothing**. *(Corrected coverage reading,
  measured after the Apply stage: the key is carried by **every** item — 470 of 470
  buildings and 429 of 429 units — taking only the values `0` and `5`; **130** buildings carry
  the positive value `5` and **0** units do. So "130 of 470 / 0 of 429" is the
  **positive-value** reading, not key presence.)* This is the **third**
  committed content field in this project with no legacy consumer, after `unit_capacity`
  (M8 line 2) and the level curve's `reward_type`/`reward_amount` (M7's XP line). The precedent
  is established twice: record the field, refuse to invent a rule from it.
- **The acquisition routes are unvalidated client-sent item lists.** `buy_offer_pack` reads
  `package_id` and then **never uses it**, `json.loads` a client-sent array, and stores every
  id in it with **no lookup into the committed `offer_packs` table**; `buy_stored_item_cash` is
  the same shape with one client-sent id. So the committed `offer_packs` and `darts_items`
  tables are read by **no** legacy **command branch** — they describe a content-derived
  acquisition system this server does not implement, which is later-milestone work.
  *(Two corrections applied after the Apply stage, both measured rather than asserted: the
  reference counts are **distinct** ids, not occurrences — 609 occurrences across `offer_packs`
  resolve to **109 distinct units and 42 distinct buildings**, and 213 across `darts_items` to
  44 distinct units and 24 buildings, so a units-only count silently drops buildings. And
  "read by no legacy module" would be **false**: `get_game_config.py`'s `make_dynamic` /
  `update_darts` do walk the darts table to rewrite each entry's `start_date`, so the precise
  claim is branch-level — no command branch reads either table, so no acquisition is derived
  from either. `offer_packs` genuinely is read by no legacy module.)*

And `add_xp_unit` **creates nothing**: it adds a **client-sent** `attr["xp"]` to a placed row,
with an optional client-sent level used only in a print. A production-shaped field therefore
exists in the corpus, with a plausible-looking committed `training_time`, and no recorded
reason to refuse — which is precisely the trap this line exists to close.

## What Changes

- **A production-readiness projection that cannot report readiness.** It projects that a queue
  exists and records its start instant, and states explicitly that **the legacy server cannot
  say whether that queue is ready** — so it delivers **no** readiness test, **no** completion,
  **no** remaining time, and **no** progress ratio, and it says so in its own documentation.
- **The row-entry inventory**: the five branches that can place a row on the map, each with the
  source of its `item_id` named — client-supplied, already-existing, or derived — so a later
  acquisition line knows which paths are **client-sent** and must be refused rather than
  trusted. This is the auditable record that makes the refusal checkable rather than asserted.
- **The `training_time` refusal as a stated requirement**: the committed duration has no legacy
  consumer, so no production duration is derived from it and no production time is computed.
- **The `add_xp_unit` refusal as a stated requirement**: a client-sent XP amount is never
  awarded, and the recorded `attr["xp"]` is read and reported as content only.
- **Tests and evidence** — a hermetic suite asserting the refusal surface: no readiness helper
  exists, the five row-entry paths and their input sources are recorded, no duration is derived
  from `training_time`, no XP is awarded, and the recorded absences are present as content; plus
  a deterministic `unit-production-report-v1` report.

### Explicitly not in this change

**No production mechanism, no unit creation, no completion, no readiness, no XP award, and no
executed-legacy fixture.** None of those can be delivered, because none exists to reproduce:
there is no completion command, no elapsed-time evaluation, no unread duration, and no
content-derived acquisition. A fixture is additionally impossible because the corpus has no unit
row, no storage, and no inventory.

**No endpoint and no Compatibility API change**: with no server-derived production to expose,
there is no intent to send and nothing to authorise, so the compat suite must stay green
**unchanged**. No **acquisition** mechanism — that is where the committed `offer_packs` and
`darts_items` content belongs, and enforcing it is later-milestone work. No **`training_time` or
`sm_training_time` duration semantics**. No **death or resurrection** behaviour (`sell`'s `KILL`
reason is unreachable because no reason is accepted from the client). No `collection`,
`movement`, `animations`, or `basic behaviors` — each its own later M8 line. No change to M8
lines 1–3 or the eleven M7 lines. No pixel parity. Legacy sources, configs, saves, villages,
the eleven delivered fixture directories, conversion packages, and registry manifests stay
byte-identical. No Flash, Ruffle, ActionScript, or browser executes, and no network is used.

## Capabilities

### New Capabilities

- `godot-unit-production`: the **explicit refusal** of a production mechanism, with its evidence
  — a readiness projection that reports a queue's presence and start instant while stating the
  server cannot say whether it is ready, the five row-entry branches with each `item_id` source
  named, and the `training_time` and `add_xp_unit` refusals — so a later line cannot compute a
  client-side readiness and call it production.

### Modified Capabilities

- `godot-unit-queues`: its "no completion and no elapsed-time evaluation" requirement gains the
  inventory that makes it auditable, so the absence names **where** a unit could have entered
  the map and proves that none of those paths derives from a queue.
- `godot-building-xp`: unchanged behaviour, but the unit-experience gap in its claim limits is
  superseded, because `add_xp_unit` — the only command that writes `attr["xp"]` — is now
  recorded as a client-sent award that no production path applies.

## Impact

- **Godot client** — a new `scripts/units/production_flow.gd` (the readiness projection and the
  recorded refusals) and a new `tests/test_unit_production.gd`, scope-test allow-list entries,
  and evidence under `apps/client-godot/evidence/unit-production/`.
- **Compatibility API v0** — **unmodified.** No endpoint, so the compat suite must stay green
  **unchanged** at its current count.
- **Legacy** — unchanged and read only, including `command.py` and `engine.py`.
- **Content package** — unchanged and read only; the report records the committed
  `training_time` distribution and the unread-field fact without altering anything.
- **Verification** — `verify-boot.ps1` gains the hermetic suite (31 hermetic); the guard
  baseline, hash manifest, content validator, and both batteries stay green.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status
  ledger, recording the executed commands, the refusal surface, and the claim limits.
