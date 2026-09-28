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

const Iso = preload("res://scripts/town/iso.gd")
const TownState = preload("res://scripts/town/town_state.gd")
const TownObject = preload("res://scripts/town/town_object.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")
const TownHud = preload("res://scripts/town/town_hud.gd")
const TownTerrain = preload("res://scripts/town/town_terrain.gd")
const CameraControls = preload("res://scripts/camera_controls.gd")
const UiFoundation = preload("res://scripts/ui_foundation.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")

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
