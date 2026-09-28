# Design

## Context

M5 left a working foundation: `boot.gd` reaches `state=ready` against either GameApi implementation and consumes a typed `PlayerSummary`, but the underlying bootstrap payload already carries the full legacy town state (`playerInfo`, default `map` with `items`, `privateState`) and nothing reads it. `camera_controls.gd` and `ui_foundation.gd` were both specified with their authentic bindings deliberately deferred ("that binding belongs to the town slice"). ContentRegistry can resolve content entries (`get_entry`) and asset references (`resolve_asset`), the package loader can render the two M4-converted packages, and the terrain image (`assets/images/en/mapa1.jpg`), per-item thumbnails (`assets/thumbs/`, 1,314 files in the legacy baseline manifest), and the legacy village `villages/Scarlet.json` are all preserved inputs.

Evidence that constrains this design (recorded during reconciliation):

- Legacy grid: placements across 20+ saves use integer `x,y ∈ [0..99]`; placement format is `[item, x, y, timestamp, orientation, store, attr, player]`.
- The client's ABC string pool contains `mapa1.jpg`, `core.isoengine.isoUtils`, `TILE_SIZE`, `EI_TILE_HEIGHT_PIXELS`, `gridWidth`, `gridHeight`, `numCols`, `numRows`, `selectorSquare` — identifiers only; numeric values are inside ABC bytecode and were **not** extracted (evidence gap, recorded not guessed).
- `mapa1.jpg` is 701×514 and is the only island/terrain image; the main SWF (`Basesec_1.4.30.swf`) has stage 1400×600 at 30 fps.
- The fresh player save has 40 placements (11 distinct building ids), **no units**, and neither converted asset; `villages/Scarlet.json` contains both House I (item 1) and Wild Elephant (unit 933) among 576 items.
- Converted assets: `0001_house_1_m` (content 1, footprint 2×2, sprite 216×144) and `10033_wild_elephant` (content 933, footprint 1×1, sprite 171×191), both `status: "converted"` in `asset_ids.json` with runtime package paths.
- Thumbnails exist for 866/899 buildings+units (9/11 fresh-town types; missing only the two bridges), are 90×90 JPEGs on a white background, and are tracked in `legacy-manifest.json` (preservation material, read-only).

## Goals / Non-Goals

**Goals:**

- One coordinate space shared by terrain, objects, selection, and camera bounds.
- Typed, fail-closed town state that never fabricates or drops legacy data.
- A windowed launch flow that reaches a rendered town in one run, plus a headless-runnable slice scene that proves the converted building and unit in town.
- Verification that is honest about what it does and does not prove (claim limits recorded in the evidence report).

**Non-Goals:**

- Authentic pixel parity with the Flash client (no oracle exists; projection constants are derived, not extracted).
- Placement, movement, selling, animations, missions, neighbors, or any state mutation — selection is read-only until the building-system phase.
- Additional asset conversions, corpus re-seeding, fixture re-capture, Compatibility API or server changes.
- An authentic legacy HUD/selection visual layout (provisional presentation; authentic binding needs evidence captured later).

## Decisions

### D1 — Town state is parsed from the bootstrap payload, not fetched separately

`scripts/town/town_state.gd` exposes `parse(payload) -> {ok, error, state}` and reuses the existing fail-closed envelope style of `boot_data.gd`. It keeps every placement verbatim (all eight fields stored alongside resolved metadata), resolves each legacy id through `ContentRegistry.get_entry`, and records resolution failures per placement instead of aborting — a legacy save may legitimately contain ids the content package lacks (Scarlet has six). Resources/summary come from the same payload the boot scene already validated.

*Alternatives:* re-fetching town state from the Compatibility API (rejected: the bootstrap already carries it; a second `get_player_info` call would double-apply the legacy `last_logged_in` mutation); parsing inside `boot.gd` (rejected: presentation owns display, not parsing, and the slice scene needs the same parser without a boot flow).

### D2 — Projection parameters are derived constants with a documented, reproducible derivation

`scripts/town/iso.gd` is a pure module: `grid_to_screen(cell)`, `screen_to_grid(point)`, `footprint_rect(cell, w, h)`, `depth_key(cell)`, all from three committed constants (tile width `TW`, tile height `TH`, world origin). The ABC numeric constants are unreachable without bytecode interpretation, so the derivation is an implementation-time procedure recorded in the README and evidence report.

The derivation is a recorded selection over three criteria, executed with the committed data (no Flash, no bytecode interpretation):

1. **Scale anchor from converted art.** The only size evidence that ties pixels to cells is the converted package frames against content footprints: the House I frame (216×144) on a 2×2 footprint and the Wild Elephant frame (171×191) on a 1×1 footprint. This yields a bounded candidate family of 2:1 diamond tiles; the 90×90 thumbnails are fixed-size UI art and are excluded from scale selection.
2. **Viewable-town criterion at the authentic stage size.** The Basesec stage is 1400×600. A candidate is preferred when a window at that size, centered on the densest fresh-town region, contains a substantial share of the save's placements: `TW=40, TH=20` shows 35×30 cells, which contains 29 of the 40 fresh placements (the best such window), while rendering thumbnails near their natural size against 2×2 footprints (80 px) and leaving converted sprites at authentic native bounds (overhang over the footprint is accepted and recorded as provisional presentation, never scaled).
3. **Land-fit validation of alignment and orientation.** `mapa1.jpg` is classified into land/water by channel thresholds; the projection maps the fresh save's (and, secondarily, Scarlet's) placement anchors through the committed constants and the land mask, and the residual (anchors on water or off-terrain) is recorded. Because the terrain texture is stretched to the derived world rectangle (spec R3), this check is scale-invariant — it validates alignment/orientation, not scale, and its residual is committed as an assertion input, not a selector.

The world rectangle equals the terrain rectangle (the diamond bounding box), so ground, objects, selection, and camera bounds share one rect; the recorded stretch factors (5.7× horizontal, 3.9× vertical at `TW=40`) and the `x→lower-right` orientation are provisional presentation facts. The chosen constants — `TW=40`, `TH=20`, origin such that cell `(0,0)`'s center sits at the top vertex offset `TH/2` — are committed in `iso.gd` with the full derivation, the land-fit residual, and the evidence gap (ABC identifiers `TILE_SIZE` / `EI_TILE_HEIGHT_PIXELS` exist but their values were never extracted) documented in the README and the evidence report.

Round-trip exactness is a hard spec requirement independent of the derivation; authentic-client parity is not claimed, and the constants are labeled derived/provisional everywhere they are reported.

*Alternatives:* hardcoding a guess from sprite bounds alone (rejected: no land-fit check, silently wrong if the island shape disagrees); interpreting ABC bytecode to recover `TILE_SIZE` (rejected as out-of-scope risk — a dedicated static-analysis tool with its own evidence; recorded as follow-up for parity refinement).

### D3 — Terrain resolves through ContentRegistry, placed by the projection's world rectangle

The town scene resolves the terrain image via `ContentRegistry.resolve_asset` over the images kind (fail-closed to an explicit error state per spec). The ground is a `TextureRect` spanning the projection's derived world rectangle (the full 100×100 diamond bbox), so any later constant correction moves ground, objects, selection, and bounds together.

### D4 — One visual-hierarchy module owns object appearance

`scripts/town/town_visuals.gd` maps a resolved placement to a visual: (1) `resolve_asset("item_sprites", img_name).status == "converted"` → package sprite loaded through `PackageLoader` (authentic art, exact sprite bounds); (2) else `assets/thumbs/<img_name>.jpg` exists → thumbnail texture with the near-white background keyed to transparency at load (corner-sampled color key with tolerance, applied once, fail-closed to marker if the thumb is unreadable), scaled to the content footprint; (3) else → labeled footprint marker. `scripts/town/town_object.gd` is the per-placement node carrying metadata (legacy id, name, cell, footprint, visual source, depth key) and the selection highlight. Footprint dimensions come from content `width`/`height` only — never texture dimensions (AGENTS rule).

*Why thumbnails at all:* footprint markers alone would satisfy "objects render" literally but fail the milestone's intent — a player must *view a real legacy town*. Thumbnails are preserved legacy art in the baseline manifest, recognizable per item, and honest when labeled provisional. The white-background keying is a presentation technique, documented and tested.

### D5 — "One building, one unit" is proven by a slice scene over an existing legacy village, not by mutating the pipeline

`scenes/town_slice.tscn` + `scripts/town/town_slice.gd` load `villages/Scarlet.json` (byte-identical preserved input) through the same `TownState.parse` + town components, exactly as `first_render.tscn` bypasses GameApi to verify packages. Scarlet's map contains House I and the Wild Elephant, so §32/§34 (authentic converted sprites in town), unit rendering, large footprints (12×6 space station), unknown ids, and that save's HUD values are all exercised from 100 % legacy-authored state — zero synthesis.

*Alternatives rejected:* re-seeding the compat/capture corpus (churns M5 executed-legacy evidence and the fixtures README provenance); booting Scarlet as the canonical player save (churns every boot expectation — name/level/xp, boot-report, parity tests — and changes what "the player's town" means); a derived fresh+Scarlet fixture (synthetic combination; strictly weaker provenance than the untouched village); converting fresh-town buildings now (M4 scope, registry/guard churn, contradicts the milestone's "one building, one unit" cap).

The player-facing boot flow still renders the real fresh save (40 objects); the unit claim is explicitly scoped to the slice scene in the evidence report.

### D6 — HUD is display-only state over the UI foundation

`scripts/town/town_hud.gd` registers a slot on `ui_foundation.gd` and renders labels for coins, wood, steel, oil, cash, energy, mana, plus name/level/xp (level/xp live on the default `map` object, not `playerInfo` — parse reads them there). Every string is `str(state.value)`; missing fields render an error indicator naming the field. No rates, deltas, timers, or polling — the state is a snapshot.

### D7 — Camera bounds live in `camera_controls.gd`, fail-closed, unset by default

Bounds are added to the camera component itself (its spec explicitly anticipated this binding): `set_world_bounds(rect)` / `clear_world_bounds()` return `{ok, error}`; non-finite/empty rectangles fail closed; setting bounds clamps an out-of-bounds position once (single correction + one pan notification); a pan that would leave committed bounds fails closed with a named error (consistent with the existing rejection envelope — the position is never softly corrected mid-drag). Unset bounds keep today's behavior byte-for-byte. The town derives the rectangle as exactly the projection world rect and calls `set_world_bounds` at build time.

*Alternative:* clamping in the town scene around the camera signal (rejected: splits ownership of committed view state and would make camera getters lie).

### D8 — Selection is inverse-projection hit testing on committed metadata

A left press converts to a cell via `screen_to_grid`; objects are tested by footprint containment (integer cell ranges — cheap, exact) and the depth-topmost hit is committed; empty/out-of-grid clears; non-finite input is rejected without change. Highlight = a drawn footprint outline on the selected object node. No save mutation — `town_state` is treated as read-only by the scene.

### D9 — Boot transition reuses the already-validated typed state

`boot.gd` keeps the bootstrap result it already holds; on `state == ready` in a **windowed** run it builds `TownState`, instantiates `scenes/town.tscn`, passes the state via an explicit setter, and switches scenes; any failure routes to the existing explicit error surface. Headless keeps its marker + quit path untouched (existing suites assert it). Exactly one bootstrap request per launch is enforced by construction (no second `GameApi` bootstrap call) and made observable by a `bootstrap_requests` counter on the `GameApi` facade, which the handoff asserts before transitioning and the evidence report records. A `--town-capture=<path>` user argument puts the town scene into capture mode: after the first rendered frame it resizes the window to the authentic 1400×600 stage, frames the camera on the recorded capture position, captures the viewport, and quits — the argument is verification-only and its absence leaves the windowed town as a plain entry point.

### D10 — Verification is structured as headless suites + two windowed captures + one gate check

New suites: `test_town_iso`, `test_town_state`, `test_town_scene`, `test_town_hud`, `test_town_selection`, `test_town_gate` (aggregates the §36 gate: save loading, terrain, objects, HUD, camera, selection, no-Flash scope, plus slice-scene sprite assertions and the land-fit residual). Camera bounds scenarios extend `test_camera_controls.gd`; handoff behavior extends `test_boot_scene.gd`. The project-scope allow-list grows to exactly 66 files (47 + 2 scenes, 8 scripts, 6 suites, 3 evidence files) with six autoloads and four scenes. Town suites register in `verify-boot.ps1` (the gate battery); `verify.ps1` keeps first-render scope but its scope test picks up the new allow-list.

Evidence generation for `evidence/town/` is a three-step deterministic flow: (1) a windowed fake-API launch of the boot scene with `--town-capture=` proves the transition end to end and commits `town-player.png`; (2) a windowed run of `town_slice.tscn --town-capture=` commits `town-slice.png`; (3) a headless run of `town.tscn --town-report` rebuilds both views from the same committed inputs (bootstrap fixture + `villages/Scarlet.json`), computes the structural records (inputs + digests, constants + derivation status, counts by visual source, HUD values, selection/camera state, bootstrap-request count, capture digests) and writes `report.json` with no timestamps or run-varying provenance, so a rerun reproduces its bytes exactly.

## Risks / Trade-offs

- [Derived projection may not match the authentic client's constants] → Round-trip and land-fit checks make it self-consistent and visually verified; constants are labeled provisional; bytecode extraction is recorded as a parity follow-up, not silently assumed.
- [Thumbnail color-keying may fringe on JPEG edges or clip dark backgrounds] → Corner-sampled key with tolerance, tested on fresh-save items; failures fall back to the footprint marker; presentation is documented as provisional.
- [66-file pin may drift if implementation reveals a needed helper module] → The change's own artifacts (proposal/spec/tasks) are amended before the PR merges — no silent divergence; the scope test is the enforcement point.
- [Scarlet contains content-unknown ids and 576 objects] → Per-placement resolution records + labeled placeholders are spec'd; the slice suite asserts the town still builds (fail-closed per object, not per scene).
- [Windowed capture needs an interactive session, like first-render] → Same pattern as `verify.ps1`: capture gated on display availability, headless assertions carry the functional claims, capture records are committed either way.
- [Two batteries must stay green with unchanged prior evidence] → Guards, comparator, boot report, and guard-baseline checks are rerun as-is; the headless boot path is intentionally untouched.

## Migration Plan

Single Apply branch; no deployment or rollback concern (client-only, additive). Order: projection + tests → town state + tests → visuals/object layer + scene → terrain/HUD/selection → camera bounds → boot handoff → slice scene → suites/allow-list/verification registration → windowed evidence → docs/commands. Each stage commits independently; full battery runs before the PR.

## Open Questions

- None blocking. The parity value of extracting `TILE_SIZE`/`EI_TILE_HEIGHT_PIXELS` from ABC bytecode is a recorded follow-up for the camera/parity refinement backlog, not required for this slice.
