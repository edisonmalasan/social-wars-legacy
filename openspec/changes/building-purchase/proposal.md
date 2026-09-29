# Proposal

## Why

M7's first deliver line (placement) is delivered and archived: a store-listed
building is picked, previewed, and confirmed as one typed intent executed by the
unchanged legacy `command()` dispatcher inside Compatibility API v0, with an
executed-legacy `buy` fixture as the parity oracle. M7's next deliver line —
*purchase* — is still open: the client cannot acquire a store-listed item into
the player's storage, so the loop stops at "the building is on the map". The
legacy server already contains that behavior (`buy_stored_item_cash` writes
`boughtUnits` and `map["store"]` through unchanged engine helpers), and the
fresh-player corpus can exercise it exactly (cash 5, empty storage, item 105
"Victory Arch" priced `{"c": 5}` at `min_level` 1), so the smallest coherent
bounded objective is to record that legacy transaction, execute it through the
same v0 intent path, and surface the resulting storage and cash in the client.

## What Changes

- **Executed-legacy purchase fixture** — capture one real
  `command.php` `buy_stored_item_cash` transaction (item 105, derived cash
  price) from the real legacy Flask server inside a disposable copy under the
  pinned interpreter, committing request, complete before/after saves, response,
  manifest, and README under `tests/fixtures/godot-item-purchase/`, with the
  same containment as the placement capture.
- **Purchase envelope derivation** — a `purchase_envelope` module deriving the
  six-key legacy batch envelope for exactly one `buy_stored_item_cash` command
  (`args = [item_id]`, the cash price from the item's config `costs` mapped onto
  the legacy 8-slot resource vector), reusing the placement envelope's shared
  serialization helpers so one derivation backs both the capture and the
  endpoint.
- **Purchase execution endpoint** — `POST /v0/purchase` on Compatibility API v0
  accepting only the intent `{user_id, item_id}` (never client-supplied
  resource deltas), executing the unchanged legacy dispatcher in-process over
  the service corpus, and answering with the legacy `result` plus the
  authoritative storage mapping and current resources; structurally unresolvable
  input fails closed with a structured error and no mutation, and insufficient
  cash reproduces legacy clamping rather than rejection.
- **Typed purchase operation** — `GameApi.purchase_item()` on both
  implementations (`FakeApi` as the deterministic in-memory double,
  `LegacyV0Api` over loopback JSON), with a typed purchase result consumed
  identically by the flow.
- **Typed storage in town state** — parse `map["store"]` from the bootstrap
  payload the client already receives into a typed, fail-closed storage
  mapping, and show it in a storage readout.
- **Purchase flow** — a shop surface over the same fail-closed catalog parse
  (store-listed entries whose level allows and whose config price is cash),
  offering store-listed, cash-priced, level-eligible entries with their price
  against current cash, one `purchase_item` intent per confirm, an explicit
  refusal (no request) when the price exceeds current cash, and an
  authoritative apply of the response's storage and resources.
- **Evidence, tests, and documentation** — a windowed capture plus a
  deterministic `purchase-report-v1` structural report under
  `apps/client-godot/evidence/purchase/`, a hermetic `test_town_purchase` suite
  plus fake/live GameApi coverage, compat envelope/endpoint/parity tests, a
  `purchase-live` battery phase proving a disposable corpus save mutates, and
  `AGENTS.md` / README command, contract, and claim-limit documentation.

Non-goals for this change: `place_stored_item`, `store_item`, and
`sell_stored_item` (the later *store*, *move*, and *sell* deliver lines),
`store_add_items` (batch grant path), `buy_si_help` (construction-help,
deferred to the construction-timers line with no derivable config price), unit
training, collections, offers, and any monetization or premium flow. Legacy
sources, configs, saves, villages, committed fixtures, conversion packages,
registry manifests, and the committed M4/M6/placement evidence stay
byte-identical (existing SHA-256 guards plus the hash manifest). The legacy
`buy` command still fuses payment with placement, so both acquisition paths
coexist: placement onto the map, this change into storage. No Flash, Ruffle,
ActionScript, or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-purchase`: buying a store-listed, cash-priced item into the
  player's storage through the modern stack — an executed-legacy purchase
  fixture as the parity oracle, a loopback-only `/v0/purchase` intent endpoint
  executing the unchanged legacy `buy_stored_item_cash` path, a typed
  `GameApi.purchase_item()` operation, typed storage in the town state, a shop
  surface with a storage readout, and the evidence, containment, and claim
  limits that bound the purchase claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement now names both
  state-mutating gameplay capabilities (`godot-building-placement` and
  `godot-building-purchase`) as the only sanctioned execution paths, and the
  `GameApi` abstraction requirement gains the typed `purchase_item()` operation
  with a "Purchase through either implementation" scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/purchase_envelope.py`, a new
  `/v0/purchase` route in `apps/compat-api/compat_service.py`, a new
  `apps/compat-api/capture_purchase_fixture.py`, and new compat tests
  (envelope, endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `sessions.py`, `config/`,
  `villages/`, `tests/saves/`, and the existing committed fixtures are read
  only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`,
  `fake_api.gd`, `legacy_v0_api.gd`; `scripts/town/town_state.gd`, a new
  `scripts/town/shop_flow.gd`, and `scripts/town/town.gd`; a new
  `tests/test_town_purchase.gd`; new scope-test allow-list entries and the
  new evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic purchase suite and the
  `purchase-live` phase; the Compatibility API guard baseline, the hash
  manifest, and both batteries must stay green with no new packages and no
  non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
