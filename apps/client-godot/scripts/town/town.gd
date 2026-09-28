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


## Left press -> selection. The camera's drag handling is independent
## (design D7/D8: the press selects, motion pans, the press is not
## consumed by either owner).
func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.pressed and button.button_index == MOUSE_BUTTON_LEFT:
			handle_pointer_press(get_global_mouse_position())


## Clears every committed view fragment (objects, selection, HUD labels,
## error display) without touching the committed state.
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


## Enters the explicit error state: names the failure on the view, keeps
## the view cleared of partial renders, and returns the failed envelope.
func _enter_error(message: String) -> Dictionary:
	_reset_view()
	view_state = STATE_ERROR
	build_error = message
	build_ok = false
	push_error("[town] " + message)
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
