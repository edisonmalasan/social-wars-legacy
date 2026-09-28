# Tasks

## 1. Isometric projection

- [x] 1.1 Implement `scripts/town/iso.gd` (pure grid↔screen, footprint rect, depth key over committed constants) with `tests/test_town_iso.gd` covering round-trip across the 0..99 extent, footprint-corner round-trip, explicit out-of-grid for negative/outside points, deterministic depth keys, and shared-constant agreement — verify: the suite passes headless.
- [x] 1.2 Execute the D2 derivation (scale anchor from the converted package frames against content footprints, viewable-town criterion at the 1400×600 stage — 29 of 40 fresh placements inside a 35×30-cell window — and land-fit validation classifying `mapa1.jpg` land/water with the residual recorded), commit `TW=40`, `TH=20`, and the origin as provisional in `iso.gd`, and document the derivation, evidence basis (legacy save extents, footprints, sprite/thumb scales, stage size, static ABC identifiers), and the evidence gap in `apps/client-godot/README.md` — verify: the README documentation matches the committed constants and records the land-fit residual.

## 2. Town state

- [x] 2.1 Implement `scripts/town/town_state.gd` (`parse` fail-closed envelope: verbatim eight-field placements, ContentRegistry resolution per id, per-placement unresolved records, resources/summary from the payload) with `tests/test_town_state.gd` covering the fresh-save bootstrap fixture (40 placements verbatim, 11 ids resolved, resources/summary equal the fixture), malformed inputs naming the offending field, and an unknown id recorded without failing the save — verify: the suite passes headless.

## 3. Terrain, object layer, and town scene

- [x] 3.1 Implement `scripts/town/town_terrain.gd` (ContentRegistry terrain resolution, ground layer at the projection world rectangle, explicit error state when unresolvable) and `scripts/town/town_visuals.gd` (visual hierarchy: converted package sprite → keyed legacy thumbnail scaled to content footprint → labeled footprint marker) — verify: unit assertions in `tests/test_town_scene.gd` cover all three visual sources plus the unresolvable-terrain error state.
- [x] 3.2 Implement `scripts/town/town_object.gd` (per-placement node: metadata, footprint highlight drawing) and `scripts/town/town.gd` + `scenes/town.tscn` (build terrain, depth-sorted objects, HUD slot, selection, camera bounds from one `TownState`) — verify: `tests/test_town_scene.gd` observes 40 objects at saved cells with content footprints, deterministic depth order, bridges as markers, and an unknown-id placeholder that leaves the town intact.

## 4. HUD

- [x] 4.1 Implement `scripts/town/town_hud.gd` (UI-foundation slot, verbatim state values, error indicator naming a missing field) with `tests/test_town_hud.gd` covering value-string equality with the fresh-save state and the missing-field indicator — verify: the suite passes headless.

## 5. Selection

- [x] 5.1 Implement selection in `scripts/town/town.gd` (inverse-projection hit test, depth-topmost footprint hit, empty clears, invalid unchanged, highlight on `town_object.gd`) with `tests/test_town_selection.gd` covering select/topmost/clear/invalid and byte-identical town state after repeated selections — verify: the suite passes headless.

## 6. Camera world bounds

- [x] 6.1 Add fail-closed optional bounds to `scripts/camera_controls.gd` (`set_world_bounds`/`clear_world_bounds`: invalid rect rejected, out-of-bounds pan rejected, single correction on set, unbounded after clear) and extend `tests/test_camera_controls.gd` with every bounds scenario from the `godot-camera` delta — verify: the suite passes headless and the pre-existing camera scenarios still pass unchanged.

## 7. Launch flow and slice scene

- [x] 7.1 Implement the windowed boot→town handoff in `scripts/boot.gd` (reuse the already-validated bootstrap state, exactly one bootstrap request, explicit error instead of a blank window, headless path untouched) and extend `tests/test_boot_scene.gd` for headless-unchanged plus handoff failure routing — verify: the suite passes headless and `verify-boot.ps1`'s boot scenarios still report the same markers.
- [x] 7.2 Implement `scripts/town/town_slice.gd` + `scenes/town_slice.tscn` rendering `villages/Scarlet.json` through the same components (windowed capture + headless assertions via scene args) and extend `tests/test_town_scene.gd` with slice assertions: House I and Wild Elephant as authentic converted sprites at their legacy cells, unknown ids as placeholders, that save's HUD values, and input digest recorded — verify: the suite passes headless with the village file byte-identical (guard hashes).

## 8. Scope, batteries, and evidence

- [x] 8.1 Update the allow-list in `tests/test_project_scope.gd` to exactly 66 files (47 + 2 scenes, 8 town scripts, 6 town suites, 3 evidence files), six autoloads, four scenes — verify: the scope suite passes with no forbidden token and `verify.ps1` exits 0.
- [x] 8.2 Register the six town suites (`test_town_iso`, `test_town_state`, `test_town_scene`, `test_town_hud`, `test_town_selection`, `test_town_gate`) in `verify-boot.ps1` and add `tests/test_town_gate.gd` aggregating the §36 gate (save loading, terrain, objects, HUD, camera bounds, selection, no-Flash scope, slice sprite coverage, terrain land-fit assertion) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end.
- [x] 8.3 Capture the two town views into `apps/client-godot/evidence/town/` via the D10 three-step flow: a windowed fake-API launch of the boot scene with `--town-capture=` (proves the transition and commits `town-player.png`), a windowed `town_slice.tscn --town-capture=` (commits `town-slice.png`), and a headless `town.tscn --town-report` run writing the deterministic `report.json` (inputs + digests, projection constants + derivation status, object counts by visual source, HUD/selection/camera state, bootstrap-request count, capture digests, and every non-claim from the spec) — verify: both captures succeed in an interactive session at 1400×600, the report lists all required fields, and a rerun of the report step reproduces its bytes; headless assertions remain the functional proof if no display is available.
- [x] 8.4 Run both batteries plus preservation guards and confirm preservation holds — verify: `verify.ps1` and `verify-boot.ps1` exit 0, guard baseline digest `6978b959…` unchanged before/after, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, first-render evidence bytes are unchanged, and `git diff` shows no legacy/fixture/manifest byte changes (the boot report regenerates with its own provenance fields and is committed as that battery's record).

## 9. Documentation and integration review

- [x] 9.1 Document the town slice in `apps/client-godot/README.md` (architecture, visual hierarchy, slice-scene provenance, capture commands, claim limits) and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one that was run successfully in this change.
- [x] 9.2 Perform the integration review: re-read the final diff against proposal/specs/design, run `openspec validate town-vertical-slice --strict` and both batteries once more, and record any residual gaps (projection provenance, provisional visuals, no live unit in the fresh save) — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.
