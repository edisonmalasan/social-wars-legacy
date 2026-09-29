# Proposal

## Why

M7's first seven deliver lines are delivered and archived: placement, purchase,
move, sell, store, upgrade, and construction. A player can therefore build,
upgrade, and watch a building finish constructing — and then the town produces
nothing, because the delivered lines derive a **neutral** resource vector on
purpose (the committed configuration records no price for building, buying,
moving, selling, storing, upgrading, or starting a build). The production half
of the loop is entirely missing: no income readout, no collection action, and the
`collect` command no delivered surface reaches.

This is also the **first line with a committed content source for its income**.
Every earlier line had to derive a neutral vector because nothing in the
repository prices its action; here the content is explicit - `collect` (amount),
`collect_type` (which resource), `collect_xp` (experience), `max_collects` (a cap
where non-zero), and the ladder globals `COLLECT_MINUTES = [5, 60, 240, 480]` and
`COLLECT_MULTIPLIER = [0.25, 1, 2, 3]` - so the derived vector can be a real
payout instead of a refusal to invent one.

The contract was established by investigation and is committed as
`docs/legacy-collect-income.md` (PR #183): the `collect` branch writes **only**
`item[3] = time_now` (`command.py:136-147`), and the income is the client-sent
8-slot vector applied verbatim per resource as `max(current + delta, 0)`
(`engine.py:251-271`). An executed probe confirmed both, and a second probe
settled the one question that needed new evidence (see the design).

## What Changes

- **Executed-legacy collect fixture** — capture one real `command.php` `collect`
  command from the real legacy Flask server inside a disposable copy under the
  pinned interpreter, committing request, complete before/after saves, response,
  manifest, and README under `tests/fixtures/godot-building-collect/`, with the
  same containment as the seven delivered captures.
- **Collection payout derivation** — a `collect_envelope` module deriving the
  six-key legacy batch envelope for exactly one `collect` command whose 8-slot
  resource vector is **derived from committed content** (the amount and resource
  from the item's `collect` and `collect_type`, the experience from
  `collect_xp`, each scaled by the ladder rung the row has actually reached), with
  every rung and every unobserved rule marked derived-provisional in the module
  docstring.
- **Collection execution endpoint** — `POST /v0/collect` on Compatibility API v0
  accepting only the intent `{user_id, item_index}`, resolving the index before
  executing, and answering with the legacy `result` plus an authoritative superset:
  the row as read before and after execution, the derived payout and the ladder
  rung it came from, and the current resources. Structurally unresolvable input
  fails closed with a structured error and no mutation, and the endpoint proves
  the post-state in **two** ways: the row's collection instant moved forward **and**
  every stored resource increased by exactly the derived payout.
- **The `item[3]` overlap, closed** — collect is refused, never executed, on a row
  carrying construction state, in **both** layers: the client offers no `Collect`
  action and sends nothing, and the endpoint fails closed before the dispatcher
  runs. This is required, not defensive: a second executed probe showed that
  `collect` on a row that `activate` had just stamped **overwrites the build's
  start instant while the countdown attribute survives**, silently restarting an
  active build's timer, and legacy answers `{"result":"success"}`.
- **Typed collection operation** — `GameApi.collect_income()` on both
  implementations (`FakeApi` as the deterministic in-memory double,
  `LegacyV0Api` over loopback JSON), with a typed result carrying both rows, the
  derived payout and rung, and the resources.
- **Collection flow** — a collection readout on the delivered selection-driven
  surface (what the next collection would yield, in which resource, and how long
  until the next ladder rung) plus a `Collect` action - the sixth mutually
  exclusive mode - that sends exactly one intent and applies **only** the
  authoritative response, so the player's balances move by the server's numbers
  and never by the client's own arithmetic; a full rollback on any failure.
- **Evidence, tests, and documentation** — a windowed capture plus a deterministic
  `collect-report-v1` report under `apps/client-godot/evidence/building-collect/`,
  a hermetic `test_town_collect` suite plus fake/live GameApi coverage, a
  `collect-live` battery phase proving a disposable corpus save mutates, and
  `AGENTS.md` / README command, provenance, and claim-limit documentation.

Non-goals for this change: the cap semantics of a non-zero `max_collects` (the
endpoint refuses rather than invents them), friend assistance, construction
speedups, the storage round trip, the premium upgrade path, `orient`, town
expansion, XP basics, and any server-authoritative validation (Server v1 / M13).
Legacy sources, configs, saves, villages, committed fixtures, conversion
packages, registry manifests, and every delivered slice's evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). No Flash,
Ruffle, ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-collect`: collecting the income a building produces through the
  modern stack — an executed-legacy collect fixture as the parity oracle, a
  loopback-only `/v0/collect` intent endpoint whose payout is **derived from
  committed content** for the first time in this family and whose post-state is
  proved twice, a typed `GameApi.collect_income()` operation, a collection
  readout and `Collect` action on the selection-driven surface, the closed
  `item[3]` overlap with the delivered construction timers, and the evidence,
  containment, provenance, and claim limits that bound the collection claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all eight
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, `godot-building-sell`,
  `godot-building-store`, `godot-building-upgrade`, `godot-building-construction`,
  and `godot-building-collect`) as the only sanctioned execution paths, and the
  `GameApi` abstraction requirement gains the typed `collect_income()` operation
  with a "Collect through either implementation" scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/collect_envelope.py`, content
  accessors for a collection payout in `compat_legacy.py` (mirroring the delivered
  `item_upgrade_to` / `item_build_time` patterns), a `POST /v0/collect` route in
  `apps/compat-api/compat_service.py` (reusing the delivered `has_map_item` /
  `map_item` accessors), a new `apps/compat-api/capture_collect_fixture.py`, and
  new compat tests (envelope, endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `constants.py`, `sessions.py`,
  `config/`, `villages/`, `tests/saves/`, and every existing committed fixture are
  read only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`, `fake_api.gd`,
  `legacy_v0_api.gd`; `scripts/town/town_state.gd` (a typed collection clock on a
  placement), a new `scripts/town/collection_flow.gd` for the pure payout, ladder,
  and countdown helpers, `scripts/town/town.gd` (a collect mode and the readout); a
  new `tests/test_town_collect.gd`; scope-test allow-list entries and the new
  evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic collect suite and the
  `collect-live` phase; the Compatibility API guard baseline, the hash manifest,
  and both batteries must stay green with no new packages and no non-loopback
  traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, `docs/legacy-collect-income.md` (the six decisions
  resolved), the new fixture README, and the roadmap Project Status ledger.
