# Proposal

## Why

Roadmap M5 (Godot Foundation) delivers the Godot project, GameApi, LegacyV0Api, ContentRegistry, Session, GameClock, **camera**, and basic UI foundation; all of those except basic UI foundation are delivered and archived, and the roadmap ledger names basic UI foundation as the next eligible M5 objective (then Settings/AudioManager depth). `first-render-in-godot` requirement R1 still lists "UI foundation" as the one game system that SHALL remain absent until its own change adds it, so the project cannot host any UI code before this change. Later scheduled work needs the base layer: the M6 town vertical slice ends with HUD and selection (roadmap task 30 "Implement HUD resources — `feat: display authoritative player resource HUD`"), and both need a layer above the world to live in. An evidence search is recorded: `config/main.json` contains no UI layout or structure key (only button/popup image references and quest-hint strings), the save corpus and fixtures contain no UI state field, and the asset-registry SWF inspection exports UI-content symbol families (buttons, popups, tooltips, panels, menus, cursors — 18,589 name-pattern matches) but carries no timeline semantics or behavioral UI specification — so no legacy UI foundation behavior has been captured, and this change delivers the bounded, explicitly provisional M5 UI foundation rather than an unevidenced parity claim.

## What Changes

- New UI foundation component (`apps/client-godot/scripts/ui_foundation.gd`): a `CanvasLayer`-based component, deliberately **not** an autoload (AGENTS.md limits autoloads to cross-cutting services; the UI belongs to the scene that shows the game, and no world exists yet). Committed state = a fixed layer-index constant plus an ordered registry of named overlay slots; each registered slot owns a full-rect `Control` container that starts visible and never intercepts pointer input (pass-through by default, interactivity opt-in per widget); fail-closed `{ok, error}` envelopes for `register_slot(slot_name)` (empty name, duplicate) and `set_slot_visible(slot_name, visible)` (unknown slot, unchanged value); change-only `slot_registered(slot_name)` / `slot_visibility_changed(slot_name, visible)` signals; getters (`has_slot`, `slot_root`, `slot_names`, `is_slot_visible`) reflect only committed state. No wall-clock/time-service reads, no transport, no persistence, no content loading, no dependency on any other script or autoload.
- New headless suite `tests/test_ui_foundation.gd`, the eighth hermetic suite in `verify-boot.ps1` (pure component: no API, no boot flow, ignores the loop's endpoint argument).
- `project.godot` header comment records the component; the autoload set (four) and the scene set (two) stay unchanged — no `.tscn` is added, the component is script-only and will be instanced by the M6 town/HUD scene.
- Project scope grows: `test_project_scope.gd` allow-lists the two new files (41 → 43) and drops the `UiFoundation` forbidden token (14 → 13); legacy-protocol and non-loopback transport tokens remain forbidden.
- `first-render-in-godot` requirement R1 MODIFIED: the UI foundation joins the allow-listed foundation work; the named absent list disappears — after this change no game system remains outside the allow-list, and the clause becomes the general "every system outside the allow-list SHALL remain absent".
- Docs: `AGENTS.md` and the client README describe the actually executed eight-suite battery with observed counts; the roadmap Project Status ledger records the delivery at archive.

## Non-Goals

- No legacy-parity UI claim: authentic UI structure (slot taxonomy, z-order, HUD layout) binds later, where it will be captured with behavioral evidence first (M6 HUD task 30 onward).
- No HUD content or widgets: no resource display, labels, buttons, themes, fonts, colors, tooltips, dialogs, cursor, selection, or menu implementations — only the slot mechanism those will be built on.
- No boot integration — the boot scene keeps its own status labels; nothing instances the component in this change.
- No Settings or AudioManager work (the next M5 objectives); no Compatibility API, GameApi, Session, ContentRegistry, or GameClock behavior change.

## Capabilities

### New Capabilities

- `godot-ui-foundation`: the UI foundation component — the named overlay-slot registry over a `CanvasLayer`, fail-closed registration and visibility envelopes, change-only notifications, containment, and documented commands.

### Modified Capabilities

- `first-render-in-godot`: requirement R1 "Minimal render-verification Godot project" — the foundation allow-list grows to include the UI foundation with its script and tests (43 files, exactly four allow-listed autoloads, two scenes, 13 forbidden tokens), the UI foundation joins the allow-listed work, and the named absent list disappears because no game system remains outside the allow-list.

## Impact

- New files: `apps/client-godot/scripts/ui_foundation.gd`, `apps/client-godot/tests/test_ui_foundation.gd`.
- Edited files: `apps/client-godot/tests/test_project_scope.gd` (allow-list, forbidden token, count assertions), `apps/client-godot/verify-boot.ps1` (eighth hermetic suite, suite prose), `apps/client-godot/project.godot` (header comment only).
- Docs: `AGENTS.md`, `apps/client-godot/README.md`; the roadmap Project Status ledger at archive.
- Verification: `verify.ps1` and `verify-boot.ps1` both re-run to exit 0; `boot-report.json` grows by the new suite's assertions (regenerated, committed as `test:`); every guarded byte (guard baseline, first-render evidence, conversion packages, asset manifests, legacy sources, normalized content) stays byte-identical; no legacy or M4/M5 evidence file changes.
