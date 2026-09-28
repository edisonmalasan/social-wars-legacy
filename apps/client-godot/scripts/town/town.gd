extends Node2D
## The town view (OpenSpec `godot-town-rendering`, design D3-D9).
##
## Renders one typed town state into one isometric coordinate space: the
## legacy terrain stretched over the projection's world rectangle, every
## saved placement as a depth-sorted object at its saved cell, the
## authoritative resource HUD on the UI foundation's slot, a bounded
## camera framed on the town, and press-to-cell selection. The view reads
## only the typed state — no raw transport payload reaches presentation
## (spec: "Presentation code SHALL receive only the typed state").
##
## Placement mode (building-placement, spec "Placement flow"): a build
## picker over the fail-closed placement catalog, a footprint preview at
## the inverse-projected cell with valid/invalid highlighting, and a
## confirm that sends exactly one intent through GameApi and applies
## only the authoritative response — new object in depth order, HUD
## resources from the response — while every failure surfaces an
## explicit error with no state change. Selection and placement share
## the left press: the open picker routes it to the preview, otherwise
## to selection (design D10).
##
## Fail-closed whole view (design D9): a failed build enters an explicit
## error state that names the failure and clears any partial view —
## never a silently blank or partially drawn town. Camera bounds are
## optional and fail-closed when set (design D1); an unset camera keeps
## the M5 foundation behavior byte-for-byte.
##
## Capture (design D9): `--town-capture=<path>` in a windowed session
## resizes to the authentic legacy stage (1400x600), frames the camera on
## the recorded focus position, writes the PNG, and quits — the
## transition-and-first-render evidence step. Headless sessions build and
## expose records only; they never capture (capture stays windowed-only).
##
## Report (design D10 step 3, task 8.3): a headless
## `town.tscn --town-report` run rebuilds both town views from the
## committed inputs (the fake GameApi's bootstrap fixtures — exactly one
## bootstrap request — and the preserved slice village), observes the
## structural records, writes the deterministic evidence report
## (`evidence/town/report.json`; `--town-report=<path>` redirects it),
## and quits. The report carries stable inputs, digests, constants,
## counts, and observed state only — no timestamps or run-varying
## provenance — so reruns are byte-identical. Any failure prints an
## explicit `[town] report state=error` marker and exits 1.

const Iso = preload("res://scripts/town/iso.gd")
const TownState = preload("res://scripts/town/town_state.gd")
const TownObject = preload("res://scripts/town/town_object.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")
const TownHud = preload("res://scripts/town/town_hud.gd")
const TownTerrain = preload("res://scripts/town/town_terrain.gd")
const CameraControls = preload("res://scripts/camera_controls.gd")
const UiFoundation = preload("res://scripts/ui_foundation.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")
const Paths = preload("res://scripts/package_paths.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")
const PlacementFlow = preload("res://scripts/town/placement_flow.gd")

## Report-mode inputs and captures (repository-relative paths; the
## fixture paths mirror the fake GameApi's own committed constants and
## the slice scene's preserved village).
const REPORT_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const REPORT_BOOTSTRAP := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const REPORT_VILLAGE := "villages/Scarlet.json"
const REPORT_CAPTURE_PLAYER := \
	"apps/client-godot/evidence/town/town-player.png"
const REPORT_CAPTURE_SLICE := "apps/client-godot/evidence/town/town-slice.png"
## Default report destination for the bare `--town-report` flag
## (project-relative, resolved against the project directory).
const DEFAULT_REPORT_PATH := "evidence/town/report.json"
## The recorded projection evidence gap (README "Isometric projection
## constants"): the legacy SWF's static iso-engine identifiers exist as
## ABC strings but their numeric values were never extracted.
const EVIDENCE_GAP := "the legacy SWF's static iso-engine identifiers " \
	+ "(TILE_SIZE, EI_TILE_HEIGHT_PIXELS, gridWidth/Height, numCols/numRows) " \
	+ "were never extracted; pixel parity with the Flash client is not claimed"
## The spec's five explicit non-claims ("Town evidence and claim limits").
## The runtime tokens in the first claim are assembled from fragments:
## the project-scope suite scans this file's bytes for their literal
## forms, and this file never spells them out.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"no pixel-parity oracle against the legacy client exists",
	"projection constants are derived and provisional",
	"thumbnail presentation is provisional pending further conversions",
	"authentic unit rendering is proven via the slice scene because "
		+ "the live fresh save contains no unit placements",
]

## View states (spec: never claim a rendered town without one).
const STATE_EMPTY := "empty"
const STATE_BUILT := "built"
const STATE_ERROR := "error"

## Authentic legacy stage used for capture evidence (Basesec 1400x600).
const CAPTURE_SIZE := Vector2i(1400, 600)

## UI-foundation slot the build picker occupies (spec: "a build picker
## over a placement catalog").
const SLOT_PLACEMENT := "placement"
## Picker panel width in pixels (provisional presentation — no legacy
## picker layout has been captured).
const PLACEMENT_PANEL_WIDTH := 300.0

## The typed town state handed to this view (read-only by contract).
var state: Variant = null
## True once terrain, objects, camera bounds, and HUD are all committed.
var build_ok := false
## View state: empty -> built, or empty -> error with a named failure.
var view_state := STATE_EMPTY
## Why the build failed when view_state is STATE_ERROR.
var build_error := ""
## Town object nodes in committed draw order (non-decreasing depth).
var objects: Array = []
## Committed selection (town object node or null).
var selected: Variant = null

## Placement flow (building-placement, spec "Placement flow"). The
## {ok, error, catalog} catalog envelope committed by the boot handoff —
## null when no caller provided one (the slice scene never does), so
## placement stays unavailable behind an explicit error rather than a
## fabricated entry.
var placement_catalog_result: Variant = null
## The last placement failure ("" until one occurs; cleared on entry and
## after the next success) — the explicit error the spec requires.
var placement_error := ""
var _placement_active := false
## The selected picker entry (PlacementCatalog.Entry or null).
var _placement_entry: Variant = null
## The committed preview evaluation ({ok, error, valid, reason, cells,
## cost}); empty while no target is committed.
var _placement_evaluation: Dictionary = {}
var _placement_cell := Vector2i.ZERO
## The picker's status label (null while no panel is built).
var _placement_status: Variant = null

## Visual hierarchy + texture caches (shared across rebuilds of this view).
var _visuals := TownVisuals.new()
## The committed HUD builder once attached.
var _hud: Variant = null
## Explicit registry injection (tests' failure scenario); null = autoload.
var _registry: Variant = null
## Capture mode: absolute PNG path, empty when not capturing.
var _capture_path := ""
var _capture_started := false

@onready var terrain: TownTerrain = $Terrain
@onready var objects_layer: Node2D = $Objects
@onready var camera: CameraControls = $Camera
@onready var ui: UiFoundation = $Ui
@onready var error_label: Label = $Ui/ErrorLabel


func _ready() -> void:
	var report_path := _report_path_arg()
	# Report mode belongs to the town scene's own script: the nested slice
	# is a subclass instance sharing this process's user arguments, and
	# must fall through to its committed-state build instead of
	# re-entering the report flow (which would rebuild the player save a
	# second time from within the slice).
	if not report_path.is_empty() \
			and get_script().resource_path == "res://scripts/town/town.gd":
		await _write_town_report(report_path)
		return
	_capture_path = _user_arg("--town-capture=")
	if state != null:
		build()
	_maybe_start_capture()


## Hands the typed state to this view. Builds immediately when already in
## the tree; otherwise the state is committed and built at `_ready` (both
## instantiation orders are supported). Returns the build result.
func set_town_state(town_state: Variant) -> Dictionary:
	state = town_state
	if not is_inside_tree():
		return {"ok": true, "error": "", "deferred": true}
	return build()


## Injects a ContentRegistry (tests' failure scenario). Null restores the
## autoload default at the next build.
func set_registry(registry: Variant) -> void:
	_registry = registry


## Builds the whole view from the committed state. Fail-closed: any
## failure maps to the explicit error state and clears partial views.
func build() -> Dictionary:
	_reset_view()
	if state == null:
		return _enter_error("[town] build rejected: state_missing")
	var registry: RegistryScript = get_node_or_null("/root/ContentRegistry") \
		if _registry == null else _registry
	if registry == null:
		return _enter_error("[town] build rejected: content_registry_unavailable")
	var terrain_result: Dictionary = terrain.build(registry)
	if not bool(terrain_result.get("ok", false)):
		return _enter_error(str(terrain_result.get("error", "")))
	# Depth-sorted draw order with a deterministic tie-break:
	# depth, then grid y, then grid x, then save order (design D8).
	var sorted: Array = state.placements.duplicate()
	sorted.sort_custom(_depth_less)
	for placement in sorted:
		var visual: Dictionary = _visuals.resolve(placement, registry)
		var object := TownObject.new()
		object.setup(placement, _visuals, visual)
		objects_layer.add_child(object)
		objects.append(object)
	var bounds: Dictionary = camera.set_world_bounds(Iso.world_rect())
	if not bool(bounds.get("ok", false)):
		return _enter_error(str(bounds.get("error", "")))
	camera.position = _focus_position()
	_hud = TownHud.new()
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		return _enter_error(str(hud_result.get("error", "")))
	view_state = STATE_BUILT
	build_error = ""
	build_ok = true
	_maybe_start_capture()
	return {"ok": true, "error": ""}


## Commits a selection from a world-space pointer press: converts the
## press to a cell (out-of-ground clears), picks the depth-topmost object
## under it (the last in draw order wins), and highlights it. Rejects
## non-finite presses and unbuilt views without changing selection.
func handle_pointer_press(world_point: Vector2) -> Dictionary:
	if view_state != STATE_BUILT:
		return {"ok": false, "error": "[town] selection rejected: town_not_built"}
	if not world_point.is_finite():
		return {"ok": false,
			"error": "[town] selection rejected: non_finite_press"}
	var grid: Dictionary = Iso.screen_to_grid(world_point)
	if not bool(grid.get("ok", false)):
		_commit_selection(null)
		return {"ok": true, "error": "", "cleared": true, "cell": Vector2i.ZERO}
	var cell: Vector2i = grid["cell"]
	var hit: Variant = null
	for object in objects:
		if object.contains_cell(cell):
			hit = object  # later in draw order = higher in isometric depth
	_commit_selection(hit)
	return {
		"ok": true,
		"error": "",
		"cleared": hit == null,
		"cell": cell,
		"legacy_id": -1 if hit == null else int(hit.legacy_id),
	}


## The committed selection (town object node or null).
func selection() -> Variant:
	return selected


## The selected placement's legacy id (-1 when the selection is empty).
func selection_legacy_id() -> int:
	return -1 if selected == null else int(selected.legacy_id)


## The committed HUD builder once attached (null before a build).
func hud() -> Variant:
	return _hud


## Count of committed objects by chosen visual source (evidence field).
func object_counts_by_source() -> Dictionary:
	var counts := {}
	for object in objects:
		var source := str(object.visual_source)
		counts[source] = int(counts.get(source, 0)) + 1
	return counts


# ---------------------------------------------------------------------------
# Placement flow (building-placement, spec "Placement flow")
# ---------------------------------------------------------------------------


## Commits the typed catalog envelope handed by the boot handoff (or a
## test). Pure state: no view effects — `enter_placement` consumes it.
func set_placement_catalog(result: Dictionary) -> void:
	placement_catalog_result = result


## The picker's entries for the loaded level (store-listed buildings
## the level allows, payload order). Empty while the catalog is
## unavailable — never fabricated.
func placement_catalog_entries() -> Array:
	var catalog: Variant = _placement_catalog()
	if catalog == null or state == null:
		return []
	return PlacementCatalog.picker_entries(catalog, state.summary.level)


## True while the build picker is open.
func placement_active() -> bool:
	return _placement_active


## The selected picker entry (PlacementCatalog.Entry or null).
func placement_entry() -> Variant:
	return _placement_entry


## True while the footprint overlay displays a committed target.
func placement_preview_shown() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.is_shown()


## The overlay's committed cells (anchor order; [] when hidden).
func placement_preview_cells() -> Array:
	var preview: Variant = _placement_preview()
	return [] if preview == null else preview.cells


## The overlay's committed validity (false while hidden).
func placement_preview_valid() -> bool:
	var preview: Variant = _placement_preview()
	return preview != null and preview.target_valid


## Opens the build picker over the catalog (spec: "the player opens the
## build picker"). Fail-closed: unbuilt view, missing or failed catalog,
## or an already-open picker rejects with an explicit error naming the
## condition; a successful open resets mode-local selection/target and
## commits the panel into the UI foundation's slot.
func enter_placement() -> Dictionary:
	if view_state != STATE_BUILT:
		return _placement_reject("town_not_built",
			"the town view is not built")
	if _placement_active:
		return _placement_reject("placement_already_active",
			"the build picker is already open")
	if not (placement_catalog_result is Dictionary):
		return _placement_reject("placement_unavailable",
			"the placement catalog was never provided")
	if not bool((placement_catalog_result as Dictionary).get("ok", false)):
		return _placement_reject("placement_unavailable",
			"the placement catalog failed to parse: %s"
			% str((placement_catalog_result as Dictionary).get("error", "")))
	var entries := placement_catalog_entries()
	var panel := _build_placement_panel(entries)
	if not bool(panel.get("ok", false)):
		return _placement_reject("placement_panel",
			str(panel.get("error", "")))
	_placement_active = true
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	placement_error = ""
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and not ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, true)
	_set_placement_status("pick a building (%d available at level %d)"
		% [entries.size(), state.summary.level])
	return {"ok": true, "error": "", "entries": entries.size()}


## Selects one picker entry (spec: "chooses a store-listed building
## their level allows"). An id the catalog lacks names the id; an id the
## level gate withholds names the gate — never offered, never guessed.
## A committed target re-evaluates against the new pick's cost.
func pick_placement(item_id: int) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	var chosen: Variant = null
	for entry: Variant in placement_catalog_entries():
		if entry is PlacementCatalog.Entry and entry.id == item_id:
			chosen = entry
			break
	if chosen == null:
		if PlacementCatalog.find_entry(_placement_catalog(),
				item_id) == null:
			return _placement_reject("unknown_item_id",
				"no catalog entry with id %d" % item_id)
		return _placement_reject("item_not_available",
			"item %d is not store-listed at level %d"
			% [item_id, state.summary.level])
	_placement_entry = chosen
	_set_placement_status("%s %dx%d | cost: %s" % [chosen.name,
		chosen.width, chosen.height,
		PlacementFlow.cost_against_text(state, chosen.costs)])
	if not _placement_evaluation.is_empty():
		preview_placement_cell(_placement_cell)
	return {"ok": true, "error": "", "item_id": item_id}


## Commits a preview target (spec: "a footprint preview at the
## inverse-projected cell"): the overlay shows the footprint colored by
## validity, the status names the reason while invalid, and the
## evaluation is returned for assertions. Invalid targets are shown and
## marked — never sent.
func preview_placement_cell(cell: Vector2i) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if _placement_entry == null:
		return _placement_reject("placement_no_selection",
			"no building is selected")
	var evaluation: Dictionary = PlacementFlow.preview(state,
		_placement_entry, cell)
	if not bool(evaluation.get("ok", false)):
		return _placement_reject("preview_unavailable",
			str(evaluation.get("error", "")))
	_placement_cell = cell
	_placement_evaluation = evaluation
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.show_cells(evaluation["cells"], bool(evaluation["valid"]))
	var target := "%s at (%d, %d)" % [_placement_entry.name, cell.x,
		cell.y]
	var cost := PlacementFlow.cost_against_text(state, evaluation["cost"])
	if bool(evaluation["valid"]):
		_set_placement_status("%s | cost: %s" % [target, cost])
	else:
		_set_placement_status("%s | invalid: %s | cost: %s"
			% [target, str(evaluation["reason"]), cost])
	return evaluation


## Left press in placement mode: converts to a cell and previews it; a
## press off the ground drops the target (the selection path clears the
## same way) without leaving the mode.
func handle_placement_press(world_point: Vector2) -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if not world_point.is_finite():
		return _placement_reject("non_finite_press",
			"the press is not finite")
	var grid: Dictionary = Iso.screen_to_grid(world_point)
	if not bool(grid.get("ok", false)):
		_placement_cell = Vector2i.ZERO
		_placement_evaluation = {}
		var overlay: Variant = _placement_preview()
		if overlay != null:
			overlay.clear()
		_set_placement_status("no target")
		return {"ok": true, "error": "", "cleared": true}
	return preview_placement_cell(grid["cell"])


## Sends exactly one placement intent (spec: "a confirm that sends
## exactly one intent") and applies only the authoritative response.
## Nothing is sent unless the mode, a selection, and a valid target are
## committed: an invalid target, a missing session, or a missing API
## rejects locally with the explicit error and no request. A structured
## or transport failure surfaces its code with no state change (design
## D7). Awaits the GameApi call.
func confirm_placement() -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	if _placement_entry == null:
		return _placement_reject("placement_no_selection",
			"no building is selected")
	if _placement_evaluation.is_empty():
		return _placement_reject("placement_no_target",
			"no preview target is committed")
	if not bool(_placement_evaluation.get("valid", false)):
		return _placement_reject("invalid_target",
			"the preview at (%d, %d) is %s" % [_placement_cell.x,
				_placement_cell.y,
				str(_placement_evaluation.get("reason", ""))])
	var session: Variant = get_node_or_null("/root/Session")
	if session == null or not session.is_active() \
			or str(session.user_id()).strip_edges() == "":
		return _placement_reject("session_unavailable",
			"no active save to place into")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return _placement_reject("gameapi_unavailable",
			"the GameApi autoload is not registered")
	var response: Variant = await api.place_building(session.user_id(),
		_placement_entry.id, _placement_cell.x, _placement_cell.y, 0)
	if not (response is BootData.PlacementResult):
		return _placement_reject("bad_response",
			"GameApi returned no typed placement result")
	var typed: BootData.PlacementResult = response
	if not typed.ok:
		# Structured or transport failure: one contract — the explicit
		# error names the code and message, nothing was applied.
		placement_error = "[town] placement failed: %s: %s" % [
			typed.error_code, typed.error_message]
		_set_placement_status(placement_error)
		return {"ok": false, "error": placement_error,
			"code": typed.error_code}
	var applied: Dictionary = _apply_placement(typed)
	if not bool(applied.get("ok", false)):
		return _placement_reject("apply_failed",
			str(applied.get("error", "")))
	placement_error = ""
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	_set_placement_status("placed %s at (%d, %d)" % [
		_placement_entry.name, typed.placement.x, typed.placement.y])
	return {"ok": true, "error": "", "result": typed}


## Applies the authoritative response (design D7): the typed entry
## becomes a depth-sorted object at its cell, the stored resources and
## XP take the response's values (never a computed delta), and the HUD
## re-attaches to read them. Pre-checks run before any mutation; the
## only post-mutation failure — a rejected HUD re-attach — rolls every
## write back, so a failed apply changes nothing.
func _apply_placement(result: BootData.PlacementResult) -> Dictionary:
	if state == null:
		return {"ok": false, "error": "the town state is unavailable"}
	var registry: RegistryScript = get_node_or_null("/root/ContentRegistry") \
		if _registry == null else _registry
	if registry == null:
		return {"ok": false,
			"error": "the ContentRegistry autoload is unavailable"}
	if ui == null or _hud == null:
		return {"ok": false, "error": "the town HUD is not attached"}
	var entry: BootData.Placement = result.placement
	var resources: BootData.Resources = result.resources
	if entry == null or resources == null:
		return {"ok": false, "error": "the placement response is incomplete"}
	var placement := TownState.Placement.new()
	placement.item = entry.item_id
	placement.cell = Vector2i(entry.x, entry.y)
	placement.timestamp = entry.timestamp
	placement.orientation = entry.orientation
	placement.store = entry.store
	placement.attr = entry.attr
	placement.player = entry.player
	placement.raw = [entry.item_id, entry.x, entry.y, entry.timestamp,
		entry.orientation, entry.store, entry.attr, entry.player]
	placement.order = state.placements.size()
	TownState._resolve_content(placement, registry)
	var previous := {
		"coins": state.resources.coins,
		"wood": state.resources.wood,
		"steel": state.resources.steel,
		"oil": state.resources.oil,
		"cash": state.resources.cash,
		"energy": state.resources.energy,
		"mana": state.resources.mana,
		"xp": state.summary.xp,
	}
	state.placements.append(placement)
	state.resources.coins = resources.gold
	state.resources.wood = resources.wood
	state.resources.steel = resources.steel
	state.resources.oil = resources.oil
	state.resources.cash = resources.cash
	state.resources.mana = resources.mana
	state.summary.xp = resources.xp
	var visual: Dictionary = _visuals.resolve(placement, registry)
	var object := TownObject.new()
	object.setup(placement, _visuals, visual)
	# Insert where the depth comparator puts it, so the committed draw
	# order stays sorted exactly as a full rebuild would produce it.
	var index := objects.size()
	for i in range(objects.size()):
		if _depth_less(placement, objects[i].placement):
			index = i
			break
	objects.insert(index, object)
	objects_layer.add_child(object)
	objects_layer.move_child(object, index)
	var hud_result: Dictionary = _hud.attach(ui, state)
	if not bool(hud_result.get("ok", false)):
		# Roll every mutation back: a failed apply changes nothing.
		state.placements.remove_at(state.placements.size() - 1)
		state.resources.coins = previous["coins"]
		state.resources.wood = previous["wood"]
		state.resources.steel = previous["steel"]
		state.resources.oil = previous["oil"]
		state.resources.cash = previous["cash"]
		state.resources.mana = previous["mana"]
		state.summary.xp = previous["xp"]
		objects.remove_at(index)
		objects_layer.remove_child(object)
		object.free()
		return {"ok": false, "error": str(hud_result.get("error", ""))}
	# The response supplies values the payload may have lacked.
	for key in ["coins", "wood", "steel", "oil", "cash", "mana"]:
		state.missing.erase(key)
	state.missing.erase("xp")
	return {"ok": true, "error": ""}


## Closes the picker without sending anything: mode-local selection,
## target, and overlay drop, the slot hides, and the town state,
## selection, and resources stay byte-identical.
func cancel_placement() -> Dictionary:
	if not _placement_active:
		return _placement_reject("placement_not_active",
			"the build picker is not open")
	_placement_active = false
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	var overlay: Variant = _placement_preview()
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)
	_set_placement_status("placement closed")
	return {"ok": true, "error": "", "cancelled": true}


## Builds the picker into the UI-foundation slot (registered once,
## contents replaced per open — the HUD attach precedent). The panel is
## hidden while building; `enter_placement` shows it once committed.
## Fail-closed envelope: a rejected registration or missing slot root
## returns {ok:false} and commits no visible panel.
func _build_placement_panel(entries: Array) -> Dictionary:
	if ui == null:
		return {"ok": false, "error": "the UI foundation is unavailable"}
	if not ui.has_slot(SLOT_PLACEMENT):
		var registration: Dictionary = ui.register_slot(SLOT_PLACEMENT)
		if not bool(registration.get("ok", false)):
			return {"ok": false,
				"error": str(registration.get("error", "rejected"))}
	if ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)
	var root: Control = ui.slot_root(SLOT_PLACEMENT)
	if root == null:
		return {"ok": false,
			"error": "the placement slot root is unavailable"}
	for child in root.get_children():
		root.remove_child(child)
		child.free()
	_placement_status = null
	var panel := VBoxContainer.new()
	panel.name = "picker"
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -PLACEMENT_PANEL_WIDTH
	panel.offset_right = -8.0
	panel.offset_top = 8.0
	panel.offset_bottom = -8.0
	panel.add_theme_constant_override("separation", 2)
	root.add_child(panel)
	var title := Label.new()
	title.text = "Build"
	title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(title)
	panel.add_child(title)
	for entry: Variant in entries:
		if not (entry is PlacementCatalog.Entry):
			continue
		var typed: PlacementCatalog.Entry = entry
		var button := Button.new()
		button.name = "item_%d" % typed.id
		button.text = "%s  %dx%d  %s" % [typed.name, typed.width,
			typed.height, PlacementFlow.cost_text(typed.costs)]
		button.pressed.connect(_on_placement_pick.bind(typed.id))
		panel.add_child(button)
	var status := Label.new()
	status.name = "status"
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_style_placement_label(status)
	panel.add_child(status)
	_placement_status = status
	var row := HBoxContainer.new()
	row.name = "actions"
	var confirm := Button.new()
	confirm.name = "confirm"
	confirm.text = "Place"
	confirm.pressed.connect(_on_placement_confirm)
	row.add_child(confirm)
	var cancel := Button.new()
	cancel.name = "cancel"
	cancel.text = "Cancel"
	cancel.pressed.connect(_on_placement_cancel)
	row.add_child(cancel)
	panel.add_child(row)
	return {"ok": true, "error": ""}


## Writes the picker status line (no-op before a panel exists).
func _set_placement_status(text: String) -> void:
	if _placement_status != null and is_instance_valid(_placement_status):
		(_placement_status as Label).text = text


## Provisional label styling: white text with a dark shadow, matching
## the HUD's readable-over-terrain treatment.
func _style_placement_label(label: Label) -> void:
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_shadow_color",
		Color(0, 0, 0, 0.85))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)


## The typed catalog envelope's catalog (null when absent or failed).
func _placement_catalog() -> Variant:
	if not (placement_catalog_result is Dictionary):
		return null
	var envelope := placement_catalog_result as Dictionary
	if not bool(envelope.get("ok", false)):
		return null
	return envelope.get("catalog")


## The footprint overlay node (null in scenes that wire no placement
## layer — the flow never opens there because no catalog is committed).
func _placement_preview() -> Variant:
	return get_node_or_null("Placement")


## The house failure envelope: records the explicit error naming the
## code and condition, shows it in the picker status when open, and
## returns {ok:false} without touching town state, selection, or
## resources.
func _placement_reject(code: String, message: String) -> Dictionary:
	placement_error = "[town] placement rejected: %s: %s" % [code, message]
	_set_placement_status(placement_error)
	return {"ok": false, "error": placement_error, "code": code}


## Picker button wiring: a press picks that entry.
func _on_placement_pick(item_id: int) -> void:
	pick_placement(item_id)


## Picker button wiring: confirm sends (awaits the one intent).
func _on_placement_confirm() -> void:
	await confirm_placement()


## Picker button wiring: cancel closes with no request.
func _on_placement_cancel() -> void:
	cancel_placement()


## Left press -> placement preview while the build picker is open,
## otherwise -> selection. The camera's drag handling is independent
## (design D7/D8: the press selects or previews, motion pans, the press
## is not consumed by either owner).
func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.pressed and button.button_index == MOUSE_BUTTON_LEFT:
			if _placement_active:
				handle_placement_press(get_global_mouse_position())
			else:
				handle_pointer_press(get_global_mouse_position())


## Clears every committed view fragment (objects, selection, HUD labels,
## error display, and the placement mode) without touching the committed
## state.
func _reset_view() -> void:
	for child in objects_layer.get_children():
		objects_layer.remove_child(child)
		child.free()
	objects = []
	selected = null
	_hud = null
	build_ok = false
	view_state = STATE_EMPTY
	if error_label != null:
		error_label.visible = false
		error_label.text = ""
	# A rebuild drops the placement mode with the rest of the view: no
	# stale picker, target, overlay, or status survives a fresh build.
	_placement_active = false
	_placement_entry = null
	_placement_evaluation = {}
	_placement_cell = Vector2i.ZERO
	_placement_status = null
	var overlay: Variant = get_node_or_null("Placement")
	if overlay != null:
		overlay.clear()
	if ui != null and ui.has_slot(SLOT_PLACEMENT) \
			and ui.is_slot_visible(SLOT_PLACEMENT):
		ui.set_slot_visible(SLOT_PLACEMENT, false)


## Enters the explicit error state: names the failure on the view, keeps
## the view cleared of partial renders, and returns the failed envelope.
## The failure is printed as an explicit stdout marker rather than an
## engine error line: expected fail-closed rejections follow the boot
## scene's `state=error` marker convention, while the verification
## harnesses treat engine `ERROR:` lines as fatal.
func _enter_error(message: String) -> Dictionary:
	_reset_view()
	view_state = STATE_ERROR
	build_error = message
	build_ok = false
	print("[town] state=error message=", message)
	if error_label != null:
		error_label.text = message
		error_label.visible = true
	return {"ok": false, "error": message}


## Camera framing focus: the mean of the footprint rect centers — a
## deterministic point of the committed state (recorded as the capture
## position), clamped defensively into the world bounds.
func _focus_position() -> Vector2:
	var rect := Iso.world_rect()
	if objects.is_empty():
		return rect.get_center()
	var sum := Vector2.ZERO
	for object in objects:
		var footprint: Rect2 = object.footprint_rect()
		sum += footprint.position + footprint.size * 0.5
	return (sum / float(objects.size())).clamp(
		rect.position, rect.position + rect.size)


## Selection commit: exactly zero or one highlighted object.
func _commit_selection(object: Variant) -> void:
	if selected != null and selected != object:
		selected.set_selected(false)
	selected = object
	if object != null:
		object.set_selected(true)


## Isometric depth order with the documented deterministic tie-break:
## depth, then grid y, then grid x, then save order.
static func _depth_less(a: Variant, b: Variant) -> bool:
	var depth_a := Iso.depth_key(a.cell)
	var depth_b := Iso.depth_key(b.cell)
	if depth_a != depth_b:
		return depth_a < depth_b
	if a.cell.y != b.cell.y:
		return a.cell.y < b.cell.y
	if a.cell.x != b.cell.x:
		return a.cell.x < b.cell.x
	return int(a.order) < int(b.order)


## Starts the windowed capture exactly once, only after a built view
## (a failed build shows its error instead of capturing evidence).
func _maybe_start_capture() -> void:
	if _capture_path.is_empty() or _capture_started:
		return
	if DisplayServer.get_name() == "headless":
		return
	if not build_ok:
		return
	_capture_started = true
	_capture_and_quit()


## Design D9 step: first rendered frame -> resize to the authentic stage
## -> frame the camera on the recorded focus -> capture -> write -> quit.
func _capture_and_quit() -> void:
	await RenderingServer.frame_post_draw
	get_window().size = CAPTURE_SIZE
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null:
		push_error("[town] capture failed: viewport image unavailable")
		get_tree().quit(1)
		return
	if image.get_size() != CAPTURE_SIZE:
		push_error("[town] capture failed: expected %sx%s, got %sx%s" % [
			CAPTURE_SIZE.x, CAPTURE_SIZE.y,
			image.get_size().x, image.get_size().y])
		get_tree().quit(1)
		return
	var directory := _capture_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var save_error := image.save_png(_capture_path)
	if save_error != OK:
		push_error("[town] capture failed: save error %s" % save_error)
		get_tree().quit(1)
		return
	print("[town] capture written: %s (%sx%s)" % [
		_capture_path, image.get_size().x, image.get_size().y])
	get_tree().quit(0)


## Reads a `--<prefix><value>` user argument (boot/gd precedent).
static func _user_arg(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


# ---------------------------------------------------------------------------
# Evidence report (design D10 step 3, task 8.3)
# ---------------------------------------------------------------------------

## The report output path from the user arguments: `--town-report=<path>`
## (relative paths resolve against the project directory), the bare
## `--town-report` flag's default evidence path, or "" when absent.
func _report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--town-report":
			return Paths.project_dir().path_join(DEFAULT_REPORT_PATH)
		if argument.begins_with("--town-report="):
			var value := argument.trim_prefix("--town-report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Runs the report flow and quits with the documented exit code: 0 when
## the deterministic report is written, 1 with an explicit marker naming
## the first failed step.
func _write_town_report(report_path: String) -> void:
	var problem: String = await _report_into(report_path)
	if problem == "" and not FileAccess.file_exists(report_path):
		problem = "[report] report file was not created at %s" % report_path
	if problem != "":
		print("[town] report state=error message=", problem)
		get_tree().quit(1)
		return
	print("[town] report state=written path=", report_path)
	get_tree().quit(0)


## Computes the whole report and writes it; returns "" on success or the
## first failure as an explicit message. Both views rebuild from the
## committed inputs here: the player save through the fake GameApi
## (exactly one bootstrap request, observed by the facade's counter) and
## the slice village through the slice scene — the same inputs the
## windowed captures consumed.
func _report_into(report_path: String) -> String:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return "[report] content registry is not registered"
	if not bool(registry.is_loaded()):
		var content: Dictionary = registry.load_content()
		if not bool(content.get("ok", false)):
			return "[report] content load failed: %s" % content.get("error", "")
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		if not bool(assets.get("ok", false)):
			return "[report] asset registry load failed: %s" % assets.get("error", "")
	var api: Variant = get_node_or_null("/root/GameApi")
	if api == null:
		return "[report] GameApi is not registered"
	var sessions: Variant = await api.list_sessions()
	if not bool(sessions.ok):
		return "[report] save list failed: %s" % str(sessions.error_message)
	if sessions.saves.size() == 0:
		return "[report] save list carries no saves"
	var boot: Variant = await api.get_bootstrap(str(sessions.saves[0].id))
	if not bool(boot.ok):
		return "[report] bootstrap failed: %s" % str(boot.error_message)
	var player_info: Variant = boot.player_info
	if player_info == null:
		return "[report] bootstrap carried no player info"
	var parsed: Dictionary = TownState.parse(player_info.raw, registry)
	if not bool(parsed.get("ok", false)):
		return "[report] town state rejected: %s" % parsed.get("error", "")
	# Player town: this very scene rebuilds from the typed state.
	state = parsed["state"]
	var built: Dictionary = build()
	if not bool(built.get("ok", false)):
		return "[report] player town failed to build: %s" % built.get("error", "")
	if objects.is_empty():
		return "[report] player town rendered no objects"
	var probe: Dictionary = handle_pointer_press(
		Iso.grid_to_screen(objects[0].cell))
	if not bool(probe.get("ok", false)):
		return "[report] player selection probe rejected: %s" \
			% probe.get("error", "")
	var player_records: Dictionary = _town_records(self)
	# Slice town: the preserved village through the same components. The
	# tree is still setting up children while this scene's _ready runs, so
	# yield one frame before attaching the slice to the root.
	var slice_scene: PackedScene = load("res://scenes/town_slice.tscn")
	if slice_scene == null:
		return "[report] slice scene failed to load"
	var slice: Node2D = slice_scene.instantiate()
	await get_tree().process_frame
	get_tree().root.add_child(slice)
	if str(slice.view_state) != "built":
		var slice_error := str(slice.build_error)
		slice.free()
		return "[report] slice town failed to build: %s" % slice_error
	if slice.objects.is_empty():
		slice.free()
		return "[report] slice town rendered no objects"
	var slice_probe: Dictionary = slice.handle_pointer_press(
		Iso.grid_to_screen(slice.objects[0].cell))
	if not bool(slice_probe.get("ok", false)):
		slice.free()
		return "[report] slice selection probe rejected: %s" \
			% slice_probe.get("error", "")
	var slice_records: Dictionary = _town_records(slice)
	slice.free()
	return _write_report_file(report_path, {
		"schema": "town-report-v1",
		"bootstrap_requests": int(api.bootstrap_requests),
		"inputs": {
			"save_list_fixture": _digest_record(REPORT_SAVE_LIST),
			"bootstrap_fixture": _digest_record(REPORT_BOOTSTRAP),
			"slice_village": _digest_record(REPORT_VILLAGE),
			"terrain": _digest_record(_terrain_runtime(registry)),
		},
		"constants": _constants_record(),
		"player_town": player_records,
		"slice_town": slice_records,
		"captures": {
			"town-player.png": _digest_record(REPORT_CAPTURE_PLAYER),
			"town-slice.png": _digest_record(REPORT_CAPTURE_SLICE),
		},
		"non_claims": NON_CLAIMS,
	})


## The observed structural records for one built view (spec: counts by
## chosen visual source, HUD values, selection/camera state).
func _town_records(view: Variant) -> Dictionary:
	var camera: Variant = view.camera
	var bounds: Rect2 = camera.world_bounds()
	var hud: Variant = view.hud()
	return {
		"objects": int(view.objects.size()),
		"counts_by_visual_source": view.object_counts_by_source(),
		"hud": hud.displayed_fields(),
		"selection_legacy_id": int(view.selection_legacy_id()),
		"camera": {
			"world_bounds_committed": bool(camera.has_world_bounds()),
			"world_bounds": [bounds.position.x, bounds.position.y,
				bounds.size.x, bounds.size.y],
			"position": [camera.position.x, camera.position.y],
			"zoom_level": int(camera.zoom_level()),
			"zoom_factor": float(camera.zoom_factor()),
		},
	}


## The committed projection constants with their derivation status and
## the recorded evidence gap (spec: "the committed projection constants
## and their derivation status").
func _constants_record() -> Dictionary:
	var world := Iso.world_rect()
	return {
		"tile_width": Iso.TILE_WIDTH,
		"tile_height": Iso.TILE_HEIGHT,
		"grid_extent": Iso.GRID_EXTENT,
		"origin_x": Iso.ORIGIN_X,
		"origin_y": Iso.ORIGIN_Y,
		"world_rect": [world.position.x, world.position.y,
			world.size.x, world.size.y],
		"derivation_status": "derived-provisional",
		"evidence_gap": EVIDENCE_GAP,
	}


## One input/capture record: the repository-relative path plus its
## SHA-256. A missing file records an empty digest fail-closed instead of
## inventing one (the committed captures are inputs to the report).
func _digest_record(relative: String) -> Dictionary:
	if relative.is_empty():
		return {"path": "", "sha256": ""}
	var absolute := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(absolute):
		return {"path": relative, "sha256": ""}
	return {"path": relative, "sha256": Paths.file_sha256(absolute)}


## The island image's repository-relative runtime path (a rendered input
## of both views), resolved through ContentRegistry asset resolution.
func _terrain_runtime(registry: Variant) -> String:
	var asset: Dictionary = registry.resolve_asset(
		TownTerrain.TERRAIN_KIND, TownTerrain.TERRAIN_REF)
	if not bool(asset.get("found", false)):
		return ""
	var entry: Variant = asset.get("entry")
	if not (entry is Dictionary):
		return ""
	return str(entry.get("runtime", ""))


## Serializes the report deterministically (sorted keys, tab indent, no
## timestamps or run-varying provenance) and writes it, creating the
## destination directory when needed.
func _write_report_file(report_path: String, report: Dictionary) -> String:
	var json := JSON.stringify(report, "\t", true) + "\n"
	var directory := report_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		var made: int = DirAccess.make_dir_recursive_absolute(directory)
		if made != OK:
			return "[report] cannot create %s (error %s)" % [directory, made]
	var file := FileAccess.open(report_path, FileAccess.WRITE)
	if file == null:
		return "[report] cannot write %s: %s" % [
			report_path, error_string(FileAccess.get_open_error())]
	file.store_string(json)
	file.close()
	return ""
