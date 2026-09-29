# Proposal

## Why

M7's first two deliver lines are delivered and archived: placement (buy a
building and put it on the map) and purchase (buy a cash-priced item into
storage). The next deliver line in roadmap order — *move* — is still open: a
player cannot reposition a building they already own, so a town is frozen in the
layout the fresh save happens to ship with. The legacy server already contains
that behavior (`move` rewrites a placed item's `x`/`y` in place and nothing
else), the fresh-player corpus exercises it exactly (a Turret I at slot 11,
`(58, 48)`, with free cells around it), and the delivered placement flow
already provides the projection, the footprint preview, and the typed
client/service pattern to build on. The smallest coherent bounded objective is
therefore to record that legacy transaction, execute it through the same v0
intent path, and let the player drag an existing building to a free cell.

## What Changes

- **Executed-legacy move fixture** — capture one real `command.php` `move`
  command from the real legacy Flask server inside a disposable copy under the
  pinned interpreter, committing request, complete before/after saves,
  response, manifest, and README under `tests/fixtures/godot-building-move/`,
  with the same containment as the placement and purchase captures.
- **Move envelope derivation** — a `move_envelope` module deriving the six-key
  legacy batch envelope for exactly one `move` command (arguments
  `[item_index, x, y, frame, string]`, where `frame` and `string` are read and
  discarded by legacy), reusing the placement envelope's shared serialization
  helpers so one derivation backs both the capture and the endpoint.
- **Move execution endpoint** — `POST /v0/move` on Compatibility API v0
  accepting only the intent `{user_id, item_index, x, y}`, executing the
  unchanged legacy dispatcher in-process over the service corpus, and
  answering with the legacy `result` plus the authoritative persisted placement
  entry and current resources — the same superset shape the placement endpoint
  returns. Structurally unresolvable input fails closed with a structured error
  and no mutation.
- **Typed move operation** — `GameApi.move_building()` on both implementations
  (`FakeApi` as the deterministic in-memory double, `LegacyV0Api` over
  loopback JSON), reusing the existing typed placement result because the
  authoritative superset is identical.
- **Addressable placements in typed town state** — parse each placement's
  legacy map key so the client can name the item a move targets, keeping a key
  that is not a positive integer unaddressable behind an explicit refusal
  rather than coercing it.
- **Move flow** — a move surface over the existing footprint preview: the
  player selects a placed building, arms the move, previews a free in-grid
  cell (the moving building's own cells no longer count as occupied), and
  confirms exactly one intent; invalid targets and the building's current cell
  send nothing, and success applies only the authoritative response (the same
  object repositioned in depth order, HUD resources from the response).
- **Evidence, tests, and documentation** — a windowed capture plus a
  deterministic `move-report-v1` report under
  `apps/client-godot/evidence/building-move/`, a hermetic `test_town_move`
  suite plus fake/live GameApi coverage, a `move-live` battery phase proving a
  disposable corpus save mutates, and `AGENTS.md` / README command, contract,
  and claim-limit documentation.

Non-goals for this change: `orient` (flip, a separate backlog item), `sell`,
`store_item` / `place_stored_item` / `sell_stored_item`, `collect`, `upgrade`
paths, construction timers, town expansion, resources, and XP. Legacy sources,
configs, saves, villages, committed fixtures, conversion packages, registry
manifests, and the committed M4/M6/placement/purchase evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). No Flash,
Ruffle, ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-move`: repositioning a building the player already owns
  through the modern stack — an executed-legacy move fixture as the parity
  oracle, a loopback-only `/v0/move` intent endpoint executing the unchanged
  legacy `move` path, a typed `GameApi.move_building()` operation, a move
  surface with footprint preview over the shared iso projection, and the
  evidence, containment, and claim limits that bound the move claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all three
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, and `godot-building-move`) as the only sanctioned
  execution paths, and the `GameApi` abstraction requirement gains the typed
  `move_building()` operation with a "Move through either implementation"
  scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/move_envelope.py`, a
  `map_item()` accessor in `compat_legacy.py`, a new `/v0/move` route in
  `apps/compat-api/compat_service.py`, a new
  `apps/compat-api/capture_move_fixture.py`, and new compat tests (envelope,
  endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `sessions.py`, `config/`,
  `villages/`, `tests/saves/`, and every existing committed fixture are read
  only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd` (nothing structural beyond
  a documented reuse), `game_api.gd`, `fake_api.gd`, `legacy_v0_api.gd`;
  `scripts/town/town_state.gd` (placement keys), a new
  `scripts/town/move_flow.gd`, and `scripts/town/town.gd`; a new
  `tests/test_town_move.gd`; scope-test allow-list entries and the new evidence
  files.
- **Verification** — `verify-boot.ps1` gains the hermetic move suite and the
  `move-live` phase; the Compatibility API guard baseline, the hash manifest,
  and both batteries must stay green with no new packages and no non-loopback
  traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
