# Proposal

## Why

M7's first three deliver lines are delivered and archived: placement, purchase,
and move. A player can therefore build, buy, and rearrange — but a building they
no longer want is stuck on the map forever, so the town still cannot be pruned
and the loop has no way out. The legacy server already contains that behavior
(`sell` deletes a placed row and records the reason, nothing else), the
fresh-player corpus exercises it exactly (Turret I at map slot 20), and the
delivered selection surface plus the addressable-key rule from the move line
give the client everything it needs to address the row. The smallest coherent
bounded objective is therefore to record that legacy transaction, execute it
through the same v0 intent path, and let the player sell a building they
selected.

## What Changes

- **Executed-legacy sell fixture** — capture one real `command.php` `sell`
  command from the real legacy Flask server inside a disposable copy under the
  pinned interpreter, committing request, complete before/after saves,
  response, manifest, and README under `tests/fixtures/godot-building-sell/`,
  with the same containment as the three delivered captures.
- **Sell envelope derivation** — a `sell_envelope` module deriving the six-key
  legacy batch envelope for exactly one `sell` command (arguments
  `[item_index, reason]`, where the reason is derived rather than chosen, and a
  neutral derived resource vector), reusing the placement envelope's shared
  serialization helpers so one derivation backs both the capture and the
  endpoint.
- **Sell execution endpoint** — `POST /v0/sell` on Compatibility API v0
  accepting only the intent `{user_id, item_index}`, resolving the index against
  the save before executing (legacy's missing-item path is a silent early return
  that must not be reported as success), and answering with the legacy `result`
  plus an authoritative superset: the eight-field row as it was read **before**
  execution, current resources, and proof that the row is gone from the
  persisted save. Structurally unresolvable input fails closed with a structured
  error and no mutation.
- **Typed sell operation** — `GameApi.sell_building()` on both implementations
  (`FakeApi` as the deterministic in-memory double, `LegacyV0Api` over loopback
  JSON), with a typed result carrying the removed row and the resources.
- **Sell flow** — a `Sell` action on the delivered selection-driven surface
  (beside the move action) that opens a confirm with the building's name and no
  target: exactly one intent per confirm, cancellation with no state change, and
  success applying only the authoritative response — the same rendered object
  removed, the typed placement removed with the town re-sorted, and HUD
  resources updated from the response — with a full rollback on any failure. A
  placement without an addressable legacy key is refused with the same explicit
  reason the move flow already uses.
- **Evidence, tests, and documentation** — a windowed capture plus a
  deterministic `sell-report-v1` report under
  `apps/client-godot/evidence/building-sell/`, a hermetic `test_town_sell`
  suite plus fake/live GameApi coverage, a `sell-live` battery phase proving a
  disposable corpus save mutates, and `AGENTS.md` / README command, contract,
  and claim-limit documentation.

Non-goals for this change: the refund policy (no config source, see the design
and the claim limits), the combat `KILL` reason and its resurrectable-hero path,
`sell_stored_item` and the other storage commands, `orient`, `collect`, upgrade
paths, construction timers, town expansion, resources, and XP. Legacy sources,
configs, saves, villages, committed fixtures, conversion packages, registry
manifests, and the committed M4/M6/placement/purchase/move evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). No Flash,
Ruffle, ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-sell`: selling a building the player owns through the modern
  stack — an executed-legacy sell fixture as the parity oracle, a loopback-only
  `/v0/sell` intent endpoint executing the unchanged legacy `sell` path, a typed
  `GameApi.sell_building()` operation, a sell confirm on the selection-driven
  surface, and the evidence, containment, and claim limits that bound the sell
  claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all four
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, and `godot-building-sell`)
  as the only sanctioned execution paths, and the `GameApi` abstraction
  requirement gains the typed `sell_building()` operation with a "Sell through
  either implementation" scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/sell_envelope.py`, a
  `POST /v0/sell` route in `apps/compat-api/compat_service.py` (reusing the
  delivered `has_map_item` / `map_item` accessors), a new
  `apps/compat-api/capture_sell_fixture.py`, and new compat tests (envelope,
  endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `sessions.py`, `config/`,
  `villages/`, `tests/saves/`, and every existing committed fixture are read
  only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`,
  `fake_api.gd`, `legacy_v0_api.gd`; `scripts/town/town.gd` (a sell mode on the
  selection-driven surface); a new `tests/test_town_sell.gd`; scope-test
  allow-list entries and the new evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic sell suite and the
  `sell-live` phase; the Compatibility API guard baseline, the hash manifest,
  and both batteries must stay green with no new packages and no non-loopback
  traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
