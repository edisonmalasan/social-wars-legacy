extends "res://tests/test_base.gd"
## Camera controls suite (OpenSpec `godot-camera` tasks 1.3 / 2.1, spec:
## "Camera controls scaffold" + "Pointer controls").
##
## Scaffold half: the component starts at the default view, walks the
## discrete zoom table one level at a time with both bound rejections
## failing closed and silent, pans by exactly the requested world delta,
## rejects the zero vector and non-finite components with state untouched,
## and notifies only on successful change with payload-equal signals.
##
## Pointer half: wheel notches consume and zoom (silent at a bound), a
## left drag pans the content under the cursor with the screen movement
## divided by the committed factor (exact at two zoom levels) and ends at
## the release, unrelated events pass through unconsumed, and the node's
## own `_unhandled_input` delegation is observed through behavior. The
## bounds half (M6 town slice): optional fail-closed world bounds —
## invalid rectangles rejected, inside commits silent, an outside
## position corrected exactly once, out-of-bounds pans rejected, and a
## clear restoring unbounded panning. A final source scan covers the
## scaffold's no-clock/no-persistence/no-loading/no-other-script
## clauses directly.
##
## Pure component: no API, no boot flow, no endpoint argument. Runs headless
## as part of `verify-boot.ps1`.

const CameraControls = preload("res://scripts/camera_controls.gd")
const CAMERA_SOURCE := "res://scripts/camera_controls.gd"
## Requirement clauses of "Camera controls scaffold" that no scenario
## covers on its own: the component must not read wall-clock or time
## services, must not perform persistence or content loading, and must not
## reference any other script or autoload (transport and legacy tokens are
## covered by the project-scope scan of every allow-listed file).
const CAMERA_SOURCE_FORBIDDEN := [
	"from_system",
	"Time.get_unix_time",
	"OS.get_time",
	"OS.get_date",
	"OS.get_datetime",
	"OS.get_unix_time",
	"FileAccess",
	"DirAccess",
	"ResourceSaver",
	"ConfigFile",
	"preload(",
	"load(",
	"GameApi",
	"ContentRegistry",
	"Session",
	"GameClock",
]

## Zoom payloads observed via the zoom signal, in emission order.
var _zoom_payloads: Array = []
## Pan payloads observed via the pan signal, in emission order.
var _pan_payloads: Array = []


func run_scenario() -> void:
	_check_default_view()
	_check_zoom_walk()
	_check_pan_and_rejections()
	_check_world_bounds()
	_check_wheel_input()
	_check_drag_input()
	_check_passthrough()
	_check_delegation()
	_check_source_contract()


## Spec: "Start at the default view".
func _check_default_view() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()
	check(camera is Camera2D, "the component is a Camera2D node")
	check_eq(camera.position, Vector2.ZERO,
		"the default view sits at the default world position")
	check_eq(camera.zoom_level(), 0, "the default zoom level is 0")
	check_eq(camera.zoom_factor(), 1.0, "the default factor is 1.0")
	check_eq(camera.zoom, Vector2(1, 1),
		"the node's own zoom equals the committed factor")
	check_eq(camera.zoom_level(), camera.ZOOM_LEVEL_MIN,
		"the committed level starts at the minimum constant")
	check_eq(camera.ZOOM_LEVEL_MAX, 2, "the table exposes three levels")
	check_eq(camera.ZOOM_FACTORS.size(), 3, "the factor table has three entries")
	check_eq(_zoom_payloads.size(), 0, "creation notifies nobody")
	check_eq(_pan_payloads.size(), 0, "creation never pans")
	check(not camera.has_world_bounds(),
		"the default view reports no world bounds")
	check_eq(camera.world_bounds(), Rect2(),
		"unset bounds expose an empty rectangle")
	camera.free()


## Spec: "Zoom one level at a time, fail closed at the bounds".
func _check_zoom_walk() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()
	var raised: Dictionary = camera.zoom_in()
	check(raised.get("ok") == true, "zooming in from level 0 succeeds")
	check_eq(camera.zoom_level(), 1, "the level advances by exactly one")
	check_eq(camera.zoom_factor(), 2.0, "the committed factor follows the table")
	check_eq(camera.zoom, Vector2(2, 2), "the node's zoom stays in agreement")
	check_eq(_zoom_payloads, [1], "the change notifies once with the new level")

	var raised_again: Dictionary = camera.zoom_in()
	check(raised_again.get("ok") == true, "zooming in to the maximum succeeds")
	check_eq(camera.zoom_level(), 2, "the level reaches the maximum")
	check_eq(camera.zoom_factor(), 4.0, "the maximum factor is committed")
	check_eq(camera.zoom, Vector2(4, 4), "the node's zoom reaches the maximum")
	check_eq(_zoom_payloads, [1, 2], "each level change notifies once")

	var at_max: Dictionary = camera.zoom_in()
	check(at_max.get("ok") == false, "zooming in at the maximum is rejected")
	check(String(at_max.get("error", "")).find("zoom_maximum_reached") != -1,
		"the error names the violated condition")
	_assert_zoom_unchanged(camera, 2, 4.0, Vector2(4, 4), Vector2.ZERO,
		"a rejected zoom leaves the view untouched")
	check_eq(_zoom_payloads, [1, 2], "a rejected zoom notifies nobody")

	var lowered: Dictionary = camera.zoom_out()
	check(lowered.get("ok") == true, "zooming out succeeds")
	check_eq(camera.zoom_level(), 1, "the level drops by exactly one")
	check_eq(camera.zoom_factor(), 2.0, "the factor follows the level down")
	var lowered_again: Dictionary = camera.zoom_out()
	check(lowered_again.get("ok") == true, "zooming out to the minimum succeeds")
	check_eq(camera.zoom_level(), 0, "the level reaches the minimum")
	check_eq(camera.zoom_factor(), 1.0, "the minimum factor is committed")
	check_eq(camera.zoom, Vector2(1, 1), "the node's zoom reaches the minimum")
	check_eq(_zoom_payloads, [1, 2, 1, 0], "every level change notifies once")

	var at_min: Dictionary = camera.zoom_out()
	check(at_min.get("ok") == false, "zooming out at the minimum is rejected")
	check(String(at_min.get("error", "")).find("zoom_minimum_reached") != -1,
		"the error names the violated condition")
	_assert_zoom_unchanged(camera, 0, 1.0, Vector2(1, 1), Vector2.ZERO,
		"a rejected zoom leaves the view untouched")
	check_eq(_zoom_payloads, [1, 2, 1, 0],
		"a rejected zoom at the minimum notifies nobody")
	camera.free()


## Spec: "Pan by a world delta" + "Reject an invalid pan".
func _check_pan_and_rejections() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()
	var first: Dictionary = camera.pan_by(Vector2(10, -5))
	check(first.get("ok") == true, "a finite nonzero pan succeeds")
	check_eq(camera.position, Vector2(10, -5),
		"the position moves by exactly the requested delta")
	check_eq(_pan_payloads, [Vector2(10, -5)],
		"the pan notifies once with the committed delta")

	var second: Dictionary = camera.pan_by(Vector2(-3, 7))
	check(second.get("ok") == true, "a second pan succeeds")
	check_eq(camera.position, Vector2(7, 2),
		"consecutive pans commit cumulatively")
	check_eq(_pan_payloads, [Vector2(10, -5), Vector2(-3, 7)],
		"each successful pan notifies exactly once")

	var zero: Dictionary = camera.pan_by(Vector2.ZERO)
	check(zero.get("ok") == false, "the zero vector is rejected")
	check(String(zero.get("error", "")).find("pan_zero_delta") != -1,
		"the zero-pan error names the violated condition")
	_assert_position_unchanged(camera, Vector2(7, 2),
		"a zero pan leaves the position untouched")

	var nan_delta: Dictionary = camera.pan_by(Vector2(NAN, 0))
	check(nan_delta.get("ok") == false, "a NaN component is rejected")
	check(String(nan_delta.get("error", "")).find("pan_invalid_delta") != -1,
		"the non-finite error names the violated condition")
	_assert_position_unchanged(camera, Vector2(7, 2),
		"a NaN pan leaves the position untouched")

	var inf_delta: Dictionary = camera.pan_by(Vector2(0, INF))
	check(inf_delta.get("ok") == false, "an infinite component is rejected")
	check(String(inf_delta.get("error", "")).find("pan_invalid_delta") != -1,
		"the infinite error names the violated condition")
	_assert_position_unchanged(camera, Vector2(7, 2),
		"an infinite pan leaves the position untouched")

	check_eq(_pan_payloads.size(), 2, "rejected pans never notify")
	camera.free()


## Spec deltas (M6): optional world bounds — invalid rectangles fail
## closed, committing bounds clamps an outside position exactly once, a
## pan leaving committed bounds fails closed, and clearing restores the
## unbounded contract byte-for-byte.
func _check_world_bounds() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()

	# Invalid rectangles fail closed: named error, bounds unset,
	# position and notifications untouched.
	var non_finite: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(NAN, 0), Vector2(10, 10)))
	check(non_finite.get("ok") == false, "a non-finite rectangle is rejected")
	check(String(non_finite.get("error", "")).find("bounds_non_finite") != -1,
		"the non-finite rejection names the violated condition")
	var infinite: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(0, 0), Vector2(INF, 10)))
	check(infinite.get("ok") == false, "an infinite extent is rejected")
	var empty: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(0, 0), Vector2(0, 10)))
	check(empty.get("ok") == false, "an empty rectangle is rejected")
	check(String(empty.get("error", "")).find("bounds_empty") != -1,
		"the empty rejection names the violated condition")
	check(not camera.has_world_bounds(),
		"failed bounds requests leave the bounds unset")
	check_eq(camera.position, Vector2.ZERO,
		"failed bounds requests leave the position unchanged")
	check_eq(_pan_payloads.size(), 0, "failed bounds requests never notify")

	# Committing bounds with the position already inside: no movement, no
	# notification; bounds never affect zoom level, factor, or node zoom.
	camera.zoom_in()
	var committed: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(-50, -50), Vector2(300, 200)))
	check(committed.get("ok") == true, "an inside position commits bounds")
	check(camera.has_world_bounds(), "the bounds getter reports committed state")
	check_eq(camera.world_bounds(),
		Rect2(Vector2(-50, -50), Vector2(300, 200)),
		"the committed rectangle round-trips")
	check_eq(camera.position, Vector2.ZERO,
		"committing bounds with an inside position does not move")
	check_eq(_pan_payloads.size(), 0,
		"committing bounds with an inside position does not notify")
	check_eq(camera.zoom_level(), 1, "bounds do not affect the zoom level")
	check_eq(camera.zoom_factor(), 2.0, "bounds do not affect the factor")
	check_eq(camera.zoom, Vector2(2, 2), "bounds do not affect the node zoom")

	# A pan that stays inside commits exactly; one that would leave fails
	# closed with no movement and no notification.
	var inside: Dictionary = camera.pan_by(Vector2(100, 50))
	check(inside.get("ok") == true, "a pan inside the bounds succeeds")
	check_eq(camera.position, Vector2(100, 50),
		"the in-bounds pan commits exactly the requested delta")
	check_eq(_pan_payloads, [Vector2(100, 50)],
		"the in-bounds pan notifies once")
	var outside: Dictionary = camera.pan_by(Vector2(0, 200))
	check(outside.get("ok") == false, "a pan leaving the bounds is rejected")
	check(String(outside.get("error", "")).find("outside_world_bounds") != -1,
		"the out-of-bounds rejection names the violated condition")
	check_eq(camera.position, Vector2(100, 50),
		"the rejected pan leaves the position unchanged")
	check_eq(_pan_payloads, [Vector2(100, 50)],
		"the rejected pan notifies nobody")

	# Committing bounds that exclude the current position corrects exactly
	# once, with exactly one notification carrying the correction delta.
	var clamped: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(1000, 1000), Vector2(100, 100)))
	check(clamped.get("ok") == true,
		"an outside position is corrected into the new bounds")
	check_eq(camera.position, Vector2(1000, 1000),
		"the position is clamped into the new rectangle")
	check_eq(_pan_payloads, [Vector2(100, 50), Vector2(900, 950)],
		"exactly one notification carries the correction delta")
	var second: Dictionary = camera.set_world_bounds(
		Rect2(Vector2(1000, 1000), Vector2(100, 100)))
	check(second.get("ok") == true, "re-applying the same bounds succeeds")
	check_eq(camera.position, Vector2(1000, 1000),
		"re-applying bounds does not move")
	check_eq(_pan_payloads.size(), 2, "re-applying bounds does not notify")

	# A pan blocked by the bounds, then a clear: the same delta commits
	# exactly, and the clear itself moves and notifies nothing.
	var blocked: Dictionary = camera.pan_by(Vector2(500, 500))
	check(blocked.get("ok") == false, "the pan beyond the bounds is rejected")
	check_eq(camera.position, Vector2(1000, 1000),
		"the blocked pan leaves the position unchanged")
	var cleared: Dictionary = camera.clear_world_bounds()
	check(cleared.get("ok") == true, "clearing bounds succeeds")
	check(not camera.has_world_bounds(), "the bounds getter reports unset")
	check_eq(camera.position, Vector2(1000, 1000),
		"clearing bounds does not move")
	check_eq(_pan_payloads.size(), 2, "clearing bounds does not notify")
	var unbounded: Dictionary = camera.pan_by(Vector2(500, 500))
	check(unbounded.get("ok") == true,
		"the previously rejected delta commits after the clear")
	check_eq(camera.position, Vector2(1500, 1500),
		"the unbounded pan commits exactly")
	check_eq(_pan_payloads.size(), 3, "the unbounded pan notifies once")
	camera.free()


## Spec: "Wheel zooms one level per notch" + "Wheel at a level bound is
## consumed and silent".
func _check_wheel_input() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()
	check(camera.handle_input(_wheel_event(MOUSE_BUTTON_WHEEL_UP, true)) == true,
		"a wheel-up notch is consumed")
	check_eq(camera.zoom_level(), 1, "wheel-up zooms in one level")
	check_eq(camera.zoom_factor(), 2.0, "the factor follows the notch")
	check_eq(camera.zoom, Vector2(2, 2), "the node's zoom follows the notch")
	check_eq(_zoom_payloads, [1], "the notch notifies once")

	check(camera.handle_input(_wheel_event(MOUSE_BUTTON_WHEEL_DOWN, true)) == true,
		"a wheel-down notch is consumed")
	check_eq(camera.zoom_level(), 0, "wheel-down zooms out one level")
	check_eq(_zoom_payloads, [1, 0], "each notch notifies once")
	check_eq(camera.zoom_factor(), 1.0, "the factor follows the notch down")
	check_eq(camera.zoom, Vector2(1, 1),
		"the node's zoom follows the notch down")

	camera.zoom_in()
	camera.zoom_in()
	check_eq(camera.zoom_level(), 2, "the view stands at the maximum")
	var payloads_before := _zoom_payloads.size()
	check(camera.handle_input(_wheel_event(MOUSE_BUTTON_WHEEL_UP, true)) == true,
		"wheel-up at the maximum is still consumed")
	_assert_zoom_unchanged(camera, 2, 4.0, Vector2(4, 4), Vector2.ZERO,
		"wheel-up at the maximum changes nothing")
	check_eq(_zoom_payloads.size(), payloads_before,
		"wheel-up at the maximum is silent")

	camera.zoom_out()
	camera.zoom_out()
	check_eq(camera.zoom_level(), 0, "the view stands at the minimum")
	var payloads_before_min := _zoom_payloads.size()
	check(camera.handle_input(_wheel_event(MOUSE_BUTTON_WHEEL_DOWN, true)) == true,
		"wheel-down at the minimum is still consumed")
	_assert_zoom_unchanged(camera, 0, 1.0, Vector2(1, 1), Vector2.ZERO,
		"wheel-down at the minimum changes nothing")
	check_eq(_zoom_payloads.size(), payloads_before_min,
		"wheel-down at the minimum is silent")
	camera.free()


## Spec: "A drag pans the content under the cursor".
func _check_drag_input() -> void:
	_reset_notifications()
	var camera: Variant = _new_camera()
	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_LEFT, true)) == true,
		"a left press begins a drag and is consumed")
	check(camera.handle_input(_motion(Vector2(100, 0))) == true,
		"motion while dragging is consumed")
	check_eq(camera.position, Vector2(-100, 0),
		"at level 0 a 100 px drag commits -100 world px")
	check_eq(_pan_payloads, [Vector2(-100, 0)],
		"the drag notifies with the committed world delta")

	var pan_count := _pan_payloads.size()
	check(camera.handle_input(_motion(Vector2.ZERO)) == true,
		"zero motion while dragging is still consumed")
	check_eq(camera.position, Vector2(-100, 0),
		"zero motion changes nothing")
	check_eq(_pan_payloads.size(), pan_count, "zero motion notifies nobody")

	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_LEFT, false)) == true,
		"a left release ends the drag and is consumed")
	check(camera.handle_input(_motion(Vector2(50, 0))) == false,
		"motion after the release is unconsumed")
	check_eq(camera.position, Vector2(-100, 0),
		"motion after the release does not pan")

	camera.zoom_in()
	check_eq(camera.zoom_factor(), 2.0, "the view is at level 1")
	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_LEFT, true)) == true,
		"a second press begins a new drag")
	check(camera.handle_input(_motion(Vector2(100, 0))) == true,
		"motion while dragging is consumed at level 1")
	check_eq(camera.position, Vector2(-150, 0),
		"at level 1 the same drag commits -50 world px")
	check_eq(_pan_payloads, [Vector2(-100, 0), Vector2(-50, 0)],
		"every committed drag notifies exactly once")
	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_LEFT, false)) == true,
		"the second release ends the drag")
	camera.free()


## Spec: "Unrelated events pass through".
func _check_passthrough() -> void:
	var camera: Variant = _new_camera()
	var zoom_count := _zoom_payloads.size()
	var pan_count := _pan_payloads.size()
	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_RIGHT, true)) == false,
		"a right-button press is unconsumed")
	check(camera.handle_input(_mouse_button(MOUSE_BUTTON_LEFT, false)) == false,
		"a left release without a drag is unconsumed")
	check(camera.handle_input(_motion(Vector2(25, 0))) == false,
		"idle motion is unconsumed")
	check(camera.handle_input(InputEventKey.new()) == false,
		"a key event is unconsumed")
	check(camera.handle_input(_wheel_event(MOUSE_BUTTON_WHEEL_UP, false)) == false,
		"a wheel release is unconsumed")
	check_eq(camera.position, Vector2.ZERO,
		"pass-through events never move the view")
	check_eq(camera.zoom_level(), 0, "pass-through events never zoom")
	check_eq(_zoom_payloads.size(), zoom_count,
		"pass-through events never notify a zoom")
	check_eq(_pan_payloads.size(), pan_count,
		"pass-through events never notify a pan")
	camera.free()


## Spec: "The node delegates input to the public handler".
func _check_delegation() -> void:
	var camera: Variant = _new_camera()
	var zoom_count := _zoom_payloads.size()
	root.add_child(camera)
	check(camera.get_parent() == root, "the component can be instanced in a tree")
	camera._unhandled_input(_wheel_event(MOUSE_BUTTON_WHEEL_UP, true))
	check_eq(camera.zoom_level(), 1,
		"the node's own input entry point advances the level")
	check_eq(_zoom_payloads.size(), zoom_count + 1,
		"the delegation emits exactly one zoom notification")
	root.remove_child(camera)
	camera.free()


## Requirement clauses with no scenario of their own: the scaffold source
## must contain no wall-clock/time-service read, no persistence or content
## loading, and no reference to any other script or autoload.
func _check_source_contract() -> void:
	var handle := FileAccess.open(CAMERA_SOURCE, FileAccess.READ)
	check(handle != null, "the component source is readable: " + CAMERA_SOURCE)
	if handle == null:
		return
	var body := handle.get_as_text()
	handle.close()
	check(body.length() > 0, "the component source is non-empty")
	for token in CAMERA_SOURCE_FORBIDDEN:
		check(body.find(token) == -1,
			"camera_controls.gd must not reference %s" % token)


## Each scenario asserts its own notifications from a clean slate (payload
## history across component instances is scenario-local, not global).
func _reset_notifications() -> void:
	_zoom_payloads.clear()
	_pan_payloads.clear()


## A fresh component with both signals observed into the payload arrays.
func _new_camera() -> Variant:
	var camera: Variant = CameraControls.new()
	camera.camera_panned.connect(_on_camera_panned)
	camera.camera_zoomed.connect(_on_camera_zoomed)
	return camera


func _on_camera_panned(world_delta: Vector2) -> void:
	_pan_payloads.append(world_delta)


func _on_camera_zoomed(level: int) -> void:
	_zoom_payloads.append(level)


func _assert_zoom_unchanged(camera: Variant, level: int, factor: float,
		node_zoom: Vector2, expected_position: Vector2, message: String) -> void:
	check_eq(camera.zoom_level(), level, message + " (level)")
	check_eq(camera.zoom_factor(), factor, message + " (factor)")
	check_eq(camera.zoom, node_zoom, message + " (node zoom)")
	check_eq(camera.position, expected_position, message + " (position)")


func _assert_position_unchanged(camera: Variant, expected: Vector2,
		message: String) -> void:
	check_eq(camera.position, expected, message)


func _mouse_button(button_index: MouseButton, pressed: bool) -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.button_index = button_index
	event.pressed = pressed
	return event


func _wheel_event(button_index: MouseButton, pressed: bool) -> InputEventMouseButton:
	return _mouse_button(button_index, pressed)


func _motion(relative: Vector2) -> InputEventMouseMotion:
	var event := InputEventMouseMotion.new()
	event.relative = relative
	return event
