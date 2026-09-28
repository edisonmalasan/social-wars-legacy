# Proposal

## Why

M5 delivered the Godot foundation — boot against Compatibility API v0, the typed GameApi boundary, ContentRegistry, camera controls, and the UI foundation — but no scene yet renders a town: there is no save → town-state path, no isometric projection, no terrain, no town objects, no HUD, and no selection. The camera and UI specs explicitly deferred their authentic bindings ("that binding belongs to the town slice, where evidence will be captured first"). M6 is the roadmap's first major success target: **a player can launch and view a real legacy town without Flash**, delivered as the smallest coherent slice in roadmap order — save loading → terrain → town objects → one building and one unit → camera/zoom → selection → HUD.

## What Changes

- **Town state loading**: a typed `TownState` parsed fail-closed from the bootstrap payload the client already receives (`playerInfo`, default `map`, `privateState`), preserving every placement array verbatim (all eight positional fields) and never fabricating missing values.
- **Isometric projection**: pure grid→screen and screen→grid conversion over explicitly derived constants, with the derivation procedure and its evidence basis documented (legacy save coordinate range, content footprints, sprite/thumbnail scales, the client's own static iso-engine identifiers) and its provisional status recorded — the numeric values inside the legacy SWF bytecode are not extracted.
- **Terrain**: the town ground renders from the legacy `mapa1.jpg` island asset (registered in `config/main.json` and referenced by the client's string pool), resolved through ContentRegistry asset resolution, fail-closed when unavailable.
- **Town objects**: every placement in the loaded save renders at its projected footprint, depth-sorted — an authentic converted package sprite when the item's asset status is `converted` (House I, Wild Elephant), otherwise the preserved legacy per-item thumbnail scaled to its content footprint with the white background keyed out, otherwise an explicit footprint marker; footprints always come from content `width`/`height`, never from texture dimensions; unknown legacy ids fail closed to a labeled placeholder.
- **HUD**: authoritative resource values (coins, wood, steel, oil, cash, energy, mana, plus the session summary fields) displayed from the parsed state via the UI foundation's slot registry — display only, no computation or deltas — with an explicit error state for missing values.
- **Selection**: pointer hit → inverse projection → topmost footprint hit → committed selection with a highlight; empty space clears; invalid input changes nothing; a public testable API.
- **Camera bounds**: `camera_controls.gd` gains fail-closed optional world bounds; unset bounds preserve today's exact pan contract, and the town sets bounds from the projected world rectangle.
- **Launch flow**: in a windowed run, the ready boot scene hands its typed bootstrap state to the town scene and transitions; headless boot behavior (marker + quit, error states) is unchanged.
- **One building, one unit (§32/§34)**: the fresh player save contains neither converted asset, so a town-slice verification scene renders the committed legacy village `villages/Scarlet.json` — an existing legacy save whose map contains House I and the Wild Elephant placements — through the same town components, proving authentic converted sprites in town without synthesizing state, re-seeding the corpus, or re-capturing executed-legacy fixtures.
- **Verification**: new headless suites (projection, town state, town scene, HUD, selection, camera bounds, boot→town handoff, §36 gate aggregation), suite registration in the boot verification, updated project-scope allow-list, and committed windowed evidence captures (player town from the fresh save + slice town from the legacy village) with a structural report and explicit claim limits.

No legacy source, config, save, fixture, conversion package, registry manifest, or Compatibility API change is needed — the bootstrap already carries the full town state.

## Capabilities

### New Capabilities

- `godot-town-rendering`: the town vertical slice — typed town-state loading from bootstrap data, isometric projection, legacy terrain rendering, depth-sorted town-object rendering with the converted-sprite/thumbnail/footprint visual hierarchy, authoritative HUD display, object selection, camera-bounds integration, the boot→town handoff target scene, the slice verification scene over a committed legacy village, committed evidence with claim limits, and containment.

### Modified Capabilities

- `godot-camera`: the pan contract gains fail-closed optional world-bounds behavior (bounds unset = today's behavior byte-for-byte; a pan that would commit a position outside the bounds fails closed with a named error; setting bounds clamps an out-of-bounds position with one correction notification).
- `godot-compatibility-boot`: add the windowed-only transition from the ready boot scene to the town scene with explicit failure states; the headless boot contract, fixtures, and parity requirements are unchanged.

## Impact

- **Code (new)**: `apps/client-godot/scenes/town.tscn`, `scenes/town_slice.tscn`, `scripts/town/*` (town state, iso projection, terrain, object layer, HUD, selection, town scene, slice scene), `tests/test_town_*.gd` suites, `evidence/town/*` committed captures and report.
- **Code (edited)**: `scripts/camera_controls.gd` (bounds), `scripts/boot.gd` (windowed handoff), `tests/test_project_scope.gd` (allow-list), `verify-boot.ps1` (suite registration), `apps/client-godot/README.md`, `AGENTS.md` (commands actually executed).
- **Read-only legacy inputs consumed**: `assets/images/en/mapa1.jpg`, `assets/thumbs/*.jpg` (in the legacy baseline manifest), `villages/Scarlet.json`, committed Compatibility API fixtures — all byte-identical before and after (existing SHA-256 guards plus the hash manifest).
- **Unchanged**: Compatibility API v0, GameApi surface, session/content/game-clock/settings/audio autoloads, `tests/saves/*`, fixture capture, conversion/asset-registry tooling, first-render and boot evidence bytes, server and legacy protocol.
- **Dependencies**: none added; Godot 4.7.2 and pinned CPython 3.9.13 only.
- **Claim limits carried forward**: projection constants are derived and provisional (legacy bytecode values unextracted); thumbnail presentation is provisional pending further conversions; the live fresh save contains no unit placements, so authentic unit rendering is proven via the slice scene; no pixel-parity oracle against the legacy client exists, so evidence is structural plus committed captures.
