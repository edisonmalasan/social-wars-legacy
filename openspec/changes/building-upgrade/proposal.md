# Proposal

## Why

M7's first five deliver lines are delivered and archived: placement, purchase,
move, sell, and store. A player can build, buy, rearrange, sell, and stow — but
every building stays at the tier it was bought in, so a town can never grow past
tier I, which is the heart of the milestone's "core town-building gameplay
loop". Unlike the previous five lines, this one needed an investigation first,
and that investigation succeeded: the legacy upgrade contract is now
**established with executed-legacy evidence**, not inferred.

What the repository already proved before any code was written:

- the dispatcher has **no upgrade command** (63 named `command.py` branches, none
  named `upgrade`), so an upgrade cannot be one command;
- `sell` is the only branch that consumes a reason, and committed legacy source
  defines the upgrade reason: `constants.py:970`
  `SELL_REASON_UPGRADE = "UPGR"`;
- `buy` takes a **client-supplied map key** and cell
  (`command.py:42-58`, `map_add_item(map, item_index, item_id, x, y, ...)`), so a
  sale followed by a purchase can reuse the exact key and cell;
- a two-command batch `[[0,"sell",[12,"UPGR"],[0×8]],[0,"buy",[12,24,45,49,1,0,0,""],[0×8]]]`
  **executes on the real legacy server** and upgrades the row in place (Wall I →
  Wall II at the same key and cell, `boughtUnits` gaining the new tier, 40 → 40
  placements, every other row and every resource byte-identical);
- the **order is forced**: the reverse batch also answers `{"result":"success"}`
  and leaves the key *absent* (40 → 39) — legacy reports success either way, so
  success alone is not proof and the endpoint must prove the post-state.

The smallest coherent bounded objective is therefore to record that legacy
transaction as a fixture, execute it through the same v0 intent path, and let
the player upgrade a selected building to its next tier.

## What Changes

- **Executed-legacy upgrade fixture** — capture one real `command.php` request
  carrying the two-command batch from the real legacy Flask server inside a
  disposable copy under the pinned interpreter, committing request, complete
  before/after saves, response, manifest, and README under
  `tests/fixtures/godot-building-upgrade/`, with the same containment as the five
  delivered captures.
- **Upgrade envelope derivation** — an `upgrade_envelope` module deriving the
  six-key legacy batch envelope for the two commands (a `sell` with the committed
  `UPGR` reason and a `buy` of the target tier reusing the row's key, cell,
  orientation, and player, each with a neutral derived resource vector),
  reusing the placement envelope's shared serialization helpers.
- **Upgrade execution endpoint** — `POST /v0/upgrade` on Compatibility API v0
  accepting only the intent `{user_id, item_index}`, resolving the target tier
  from the committed configuration, reading the row before execution, and
  answering with the legacy `result` plus an authoritative superset: the row as
  read **before** execution, the row re-read **after** it, and the current
  resources. Structurally unresolvable input — including a placement with no
  upgrade path — fails closed with a structured error and no mutation, and a
  post-execution state that is not the derived upgrade fails closed too.
- **Typed upgrade operation** — `GameApi.upgrade_building()` on both
  implementations (`FakeApi` as the deterministic in-memory double, `LegacyV0Api`
  over loopback JSON), with a typed result carrying the replaced row, the new row,
  and the resources.
- **Upgrade flow** — an `Upgrade` action on the delivered selection-driven
  surface (beside `Move`, `Sell`, and `Store`) opening a confirm that names the
  current and target tier; exactly one intent per confirm, cancellation with no
  state change, and success applying only the authoritative response — the same
  object replaced by the new tier at the same cell and key, in depth order, with
  the HUD updated — with a full rollback on any failure.
- **Evidence, tests, and documentation** — a windowed capture plus a deterministic
  `upgrade-report-v1` report under `apps/client-godot/evidence/building-upgrade/`,
  a hermetic `test_town_upgrade` suite plus fake/live GameApi coverage, an
  `upgrade-live` battery phase proving a disposable corpus save mutates, and
  `AGENTS.md` / README command, contract, provenance, and claim-limit
  documentation.

Non-goals for this change: the construction timer the upgraded building is
seeded with (`attr = {"nc": 0}`) and the `activate` / click-to-build family,
which belong to the next M7 line; the premium (`premium_upgrade_costs`) upgrade
path; the client's level gate and daily-upgrade limit (see the design's
deliberately-unimplemented rules and the claim limits); `place_stored_item` /
`sell_stored_item`; `orient`; `collect`; town expansion; resources; XP. Legacy
sources, configs, saves, villages, committed fixtures, conversion packages,
registry manifests, and every delivered slice's evidence stay byte-identical
(existing SHA-256 guards plus the hash manifest). No Flash, Ruffle, ActionScript,
or browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-upgrade`: upgrading a building the player owns to its next
  tier through the modern stack — an executed-legacy two-command upgrade fixture
  as the parity oracle, a loopback-only `/v0/upgrade` intent endpoint deriving
  both legacy commands and proving the post-state, a typed
  `GameApi.upgrade_building()` operation, an `Upgrade` action on the
  selection-driven surface, and the evidence, containment, provenance, and claim
  limits that bound the upgrade claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all six
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, `godot-building-sell`,
  `godot-building-store`, and `godot-building-upgrade`) as the only sanctioned
  execution paths, and the `GameApi` abstraction requirement gains the typed
  `upgrade_building()` operation with an "Upgrade through either implementation"
  scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/upgrade_envelope.py`, an
  `item_upgrade_to()` accessor in `compat_legacy.py`, a `POST /v0/upgrade` route
  in `apps/compat-api/compat_service.py` (reusing the delivered `has_map_item` /
  `map_item` accessors), a new `apps/compat-api/capture_upgrade_fixture.py`, and
  new compat tests (envelope, endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `constants.py`, `sessions.py`,
  `config/`, `villages/`, `tests/saves/`, and every existing committed fixture are
  read only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`,
  `fake_api.gd`, `legacy_v0_api.gd`; `scripts/town/town.gd` (an upgrade mode on the
  selection-driven surface); a new `tests/test_town_upgrade.gd`; scope-test
  allow-list entries and the new evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic upgrade suite and the
  `upgrade-live` phase; the Compatibility API guard baseline, the hash manifest,
  and both batteries must stay green with no new packages and no non-loopback
  traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
