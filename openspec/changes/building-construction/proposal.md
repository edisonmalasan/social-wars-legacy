# Proposal

## Why

M7's first six deliver lines are delivered and archived: placement, purchase,
move, sell, store, and upgrade. The upgrade line proved that a purchased or
upgraded building arrives **unfinished** — `engine.map_add_item` seeds
`attr = {"nc": 0}` for any player-owned item whose config has
`clicks_to_build > 0`, and the upgrade delta explicitly recorded that the counter
is "reported but deliberately not consumed" by the next M7 deliver line. So the
current client renders a building that legacy considers under construction and
then ignores the fact forever: nothing starts a build, nothing records a build
click, nothing completes one, and no countdown is ever shown. The construction
loop is the last mechanical piece between "build a thing" and "watch it finish".

Unlike move, sell, and store, this contract was **established by investigation
before this proposal** and is recorded in `docs/legacy-construction-timing.md`,
including four executed-legacy probes. What is established: the three commands'
argument shapes and effects, that they write only the row's timestamp and
attribute bag, that the counter is seeded by the *purchase* half rather than by
these commands, and — decisively — that **no server-side completion rule
exists**, so the client owns the threshold. What is derived and never observed:
that these are the commands a real construction sends, and the duration value a
client sends to start one.

## What Changes

- **Executed-legacy construction fixture** — capture one real `command.php`
  request carrying the derived two-command batch (`activate` starting a countdown
  whose duration is derived from the item's committed build time, then
  `add_click`) from the real legacy Flask server inside a disposable copy under
  the pinned interpreter, committing request, complete before/after saves,
  response, manifest, and README under
  `tests/fixtures/godot-building-construction/`, with the same containment as the
  six delivered captures.
- **Construction envelope derivation** — a `construction_envelope` module
  deriving the six-key legacy batch envelope for exactly one of the three
  commands, with the start duration derived from committed content and the
  resource vector neutral, reusing the placement envelope's shared serialization
  helpers.
- **Construction execution endpoint** — `POST /v0/construction` on Compatibility
  API v0 accepting only the intent `{user_id, item_index, action}` where the
  action is one of three documented values, never a duration, never resource
  deltas; executing the unchanged dispatcher in-process; and answering with the
  legacy `result` plus the row as read before and after execution and the current
  resources. A per-action post-execution proof must hold before success is
  reported, structurally unresolvable input (including an unknown action) fails
  closed, and a construction action that destroyed its row would fail closed
  rather than be reported.
- **Typed construction operation** — `GameApi.build_construction()` on both
  implementations (`FakeApi` as the deterministic in-memory double,
  `LegacyV0Api` over loopback JSON), with a typed result carrying both rows, the
  resources, and the resolved action.
- **Construction flow** — a `Build` action on the delivered selection-driven
  surface whose single primary step follows the row's own state — start a build
  with the derived duration, record a build click, or finish the build — plus a
  construction readout showing the click progress and the remaining countdown
  derived from the row's state; exactly one intent per confirm, cancellation
  with no state change, and success applying only the authoritative response with
  a full rollback on any failure.
- **Evidence, tests, and documentation** — a windowed capture plus a
  deterministic `construction-report-v1` report under
  `apps/client-godot/evidence/building-construction/`, a hermetic
  `test_town_construction` suite plus fake/live GameApi coverage, a
  `construction-live` battery phase proving a disposable corpus save mutates, and
  `AGENTS.md` / README command, provenance, and claim-limit documentation.

Non-goals for this change: the friend-assist cluster (`buy_si_help` /
`finish_si` and the `attr["si"]` bag, a separable social feature), construction
**speedups** and the `UPGRADE_SPEEDUP_PRICING` global, the premium upgrade path,
`orient`, `collect`, town expansion, resources, and XP. Legacy sources, configs,
saves, villages, committed fixtures, conversion packages, registry manifests, and
every delivered slice's evidence stay byte-identical (existing SHA-256 guards
plus the hash manifest). No Flash, Ruffle, ActionScript, or browser executes, and
no external network is used.

## Capabilities

### New Capabilities

- `godot-building-construction`: starting, counting, and completing the
  construction of a building the player owns through the modern stack — an
  executed-legacy construction fixture as the parity oracle, a loopback-only
  `/v0/construction` intent endpoint deriving one of three legacy commands with a
  per-action post-execution proof, a typed `GameApi.build_construction()`
  operation, a state-driven build step and construction readout on the
  selection-driven surface, and the evidence, containment, provenance, and claim
  limits that bound the construction claim.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all seven
  state-mutating gameplay capabilities (`godot-building-placement`,
  `godot-building-purchase`, `godot-building-move`, `godot-building-sell`,
  `godot-building-store`, `godot-building-upgrade`, and
  `godot-building-construction`) as the only sanctioned execution paths, and the
  `GameApi` abstraction requirement gains the typed `build_construction()`
  operation with a "Construct through either implementation" scenario.

## Impact

- **Compatibility API v0** — new `apps/compat-api/construction_envelope.py`, a
  `LegacyBoot` content accessor for the committed build time (reusing the
  delivered `item_upgrade_to` pattern), a `POST /v0/construction` route in
  `apps/compat-api/compat_service.py` (reusing the delivered `has_map_item` /
  `map_item` accessors), a new `apps/compat-api/capture_construction_fixture.py`,
  and new compat tests (envelope, endpoint, executed-legacy replay).
- **Legacy** — unchanged: `command.py`, `engine.py`, `constants.py`,
  `sessions.py`, `config/`, `villages/`, `tests/saves/`, and every existing
  committed fixture are read only and SHA-256 guarded.
- **Godot client** — `scripts/gameapi/boot_data.gd`, `game_api.gd`,
  `fake_api.gd`, `legacy_v0_api.gd`; `scripts/town/town_state.gd` (typed
  construction state on a placement), `scripts/town/town.gd` (a build mode and a
  construction readout on the selection-driven surface); a new
  `scripts/town/construction_flow.gd` for the pure state-machine helpers; a new
  `tests/test_town_construction.gd`; scope-test allow-list entries and the new
  evidence files.
- **Verification** — `verify-boot.ps1` gains the hermetic construction suite and
  the `construction-live` phase; the Compatibility API guard baseline, the hash
  manifest, and both batteries must stay green with no new packages and no
  non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the new fixture README, and the roadmap Project
  Status ledger.
