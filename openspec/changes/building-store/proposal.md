# Proposal

## Why

M7's first four deliver lines are delivered and archived: placement, purchase,
move, and sell. The client's storage view now shows what a player bought, and
the town can be rearranged and pruned — but the delivered purchase line
explicitly stops at "the item is in your storage": nothing can be *put* there
from the map, so the storage the player sees is write-only from the shop and
the map is still the only place a building can stand. The legacy server already
contains that behavior (`store_item` pops a placed row and adds its item to
`map["store"]`), the fresh-player corpus exercises it exactly (the Tree
decoration at map slot 2, with an empty storage to fill), and the delivered
selection-driven surface, addressable keys, and storage readout are exactly
what this needs. The smallest coherent bounded objective is therefore to record
that legacy transaction, execute it through the same v0 intent path, and let the
player put a selected building into storage.

## What Changes

- **Executed-legacy store fixture** — capture one real `command.php`
  `store_item` command from the real legacy Flask server inside a disposable
  copy under the pinned interpreter, committing request, complete before/after
  saves, response, manifest, and README under
  `tests/fixtures/godot-building-store/`, with the same containment as the four
  delivered captures.
- **Store envelope derivation** — a `store_envelope` module deriving the
  six-key legacy batch envelope for exactly one `store_item` command (its single
  argument is the item index, and a neutral derived resource vector), reusing
  the placement envelope's shared serialization helpers so one derivation backs
  both the capture and the endpoint.
- **Store execution endpoint** — `POST /v0/store` on Compatibility API v0
  accepting only the intent `{user_id, item_index}`, resolving the index against
  the save before executing, and answering with the legacy `result` plus an
  authoritative superset: the eight-field row as read **before** execution, the
  full post-execution storage mapping, and the current resources — plus proof
  that the row is gone and the storage entry landed. Structurally unresolvable
  input fails closed with a structured error and no mutation.
- **Typed store operation** — `GameApi.store_building()` on both implementations
  (`FakeApi` as the deterministic in-memory double, `LegacyV0Api` over loopback
  JSON), with a typed result carrying the removed row, the storage mapping, and
  the resources.
- **Store flow** — a `Store` action on the delivered selection-driven surface
  (beside `Move` and `Sell`) opening a confirm that names the building and
  reports where it will land; exactly one intent per confirm, cancellation with
  no state change, and success applying only the authoritative response — the
  rendered object freed, the typed placement removed, the typed storage and its
  readout replaced from the response's mapping, and the HUD updated — with a
  full rollback on any failure. A placement without an addressable legacy key is
  refused with the same explicit reason the move and sell flows already use.
- **Evidence, tests, and documentation** — a windowed capture plus a
  deterministic `store-report-v1` report under
  `apps/client-godot/evidence/building-store/`, a hermetic `test_town_store`
  suite plus fake/live GameApi coverage, a `store-live` battery phase proving a
  disposable corpus save mutates, and `AGENTS.md` / README command, contract,
  and claim-limit documentation.

Non-goals for this change: taking a stored item back out
(`place_stored_item`), selling a stored item (`sell_stored_item`), granting
stored items (`store_add_items`), building storage capacity, `orient`,
`collect`, upgrade paths, construction timers, town expansion, resources, and
XP. Legacy sources, configs, saves, villages, committed fixtures, conversion
packages, registry manifests, and the committed M4/M6 evidence and every
delivered slice's evidence stay byte-identical (existing SHA-256 guards plus the
hash manifest). No Flash, Ruffle, ActionScript, or browser executes, and no
external network is used.

## Capabilities

### New Capabilities

- `godot-building-store`: putting a building the player owns into their storage
  through the modern stack — an executed-legacy store fixture as the parity
  oracle, a loopback-only `/v0/store` intent endpoint executing the unchanged
  legacy `store_item` path, a typed `GameApi.store_building()` operation, a
  `Store` action on the selection-driven surface that updates the typed storage
  and its readout, and the evidence, containment, and claim limits that bound
  the store claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all five
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, `godot-building-sell`, and
  `godot-building-store`) as the only sanctioned execution paths, and the
  `GameApi` abstraction requirement gains the typed `store_building()`
  operation with a "Store through either implementation" scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/store_envelope.py`, a
  `POST /v0/store` route in `apps/compat-api/compat_service.py` (reusing the
  delivered `has_map_item` / `map_item` / `map_store` accessors), a new
  `apps/compat-api/capture_store_fixture.py`, and new compat tests (envelope,
  endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `sessions.py`, `config/`,
  `villages/`, `tests/saves/`, and every existing committed fixture are read
  only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`,
  `fake_api.gd`, `legacy_v0_api.gd`; `scripts/town/town.gd` (a store mode on the
  selection-driven surface plus the storage readout refresh); a new
  `tests/test_town_store.gd`; scope-test allow-list entries and the new evidence
  files.
- **Verification** — `verify-boot.ps1` gains the hermetic store suite and the
  `store-live` phase; the Compatibility API guard baseline, the hash manifest,
  and both batteries must stay green with no new packages and no non-loopback
  traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
