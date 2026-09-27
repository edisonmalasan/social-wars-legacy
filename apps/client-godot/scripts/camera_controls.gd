extends Camera2D
## Camera controls (M5 foundation, OpenSpec `godot-camera` design D1-D7).
##
## Reusable view component for the town scene that will instance it (design
## D1: deliberately not an autoload — a camera belongs to the scene that
## renders the world, and no world exists yet). Committed view state is the
## world position plus a discrete zoom level 0..2 over the fixed factor
## table (design D4), with the node's own zoom kept equal to the committed
## factor. Provisional foundation (design D2): no legacy camera behavior
## has been captured, so authentic bounds, ranges, and input feel bind
## later, with evidence, at the town slice.
##
## The controls follow the fail-closed `{ok, error}` envelope of the other
## foundation scaffolds: a rejected request names the violated condition,
## leaves committed state untouched, and notifies nobody (spec: "Zoom one
## level at a time, fail closed at the bounds" / "Reject an invalid pan").
## Pointer gestures map through the public `handle_input()` so the contract
## is testable without the OS input system (design D7); the node's
## `_unhandled_input` delegates to it.

## Emitted once per successful pan with the committed world delta.
signal camera_panned(world_delta: Vector2)
## Emitted once per committed zoom-level change with the new level.
signal camera_zoomed(zoom_level: int)

## Lowest zoom level (factor 1.0, the Camera2D default at creation).
const ZOOM_LEVEL_MIN := 0
## Highest zoom level the foundation exposes.
const ZOOM_LEVEL_MAX := 2
## Fixed factor per zoom level. Integer factors keep raster town art
## texel-aligned; the values are provisional foundation, explicitly not a
## legacy parity claim (design D2).
const ZOOM_FACTORS := [1.0, 2.0, 4.0]

## Committed zoom level (0 at creation).
var _zoom_level := ZOOM_LEVEL_MIN
## True between a consumed left press and its release.
var _dragging := false


## Delegates the node's input entry point to the public handler, so an
## instanced component responds to pointer input from the scene tree.
func _unhandled_input(event: InputEvent) -> void:
	handle_input(event)


## The committed zoom level (ZOOM_LEVEL_MIN..ZOOM_LEVEL_MAX).
func zoom_level() -> int:
	return _zoom_level


## The committed zoom factor for the current level (1.0 at creation);
## always equal to the node's own zoom.
func zoom_factor() -> float:
	return float(ZOOM_FACTORS[_zoom_level])


## Raises the zoom by exactly one level. Fail-closed: at the maximum level
## the error names the condition, state is untouched, nobody is notified.
func zoom_in() -> Dictionary:
	if _zoom_level >= ZOOM_LEVEL_MAX:
		return {"ok": false,
			"error": "[camera] zoom_in rejected: zoom_maximum_reached"}
	_commit_zoom_level(_zoom_level + 1)
	return {"ok": true, "error": ""}


## Lowers the zoom by exactly one level. Fail-closed: at the minimum level
## the error names the condition, state is untouched, nobody is notified.
func zoom_out() -> Dictionary:
	if _zoom_level <= ZOOM_LEVEL_MIN:
		return {"ok": false,
			"error": "[camera] zoom_out rejected: zoom_minimum_reached"}
	_commit_zoom_level(_zoom_level - 1)
	return {"ok": true, "error": ""}


## Pans the view by a world-space delta. Fail-closed: the zero vector and
## any non-finite component are rejected with an error naming the condition
## and the committed position is untouched; otherwise the position moves by
## exactly the requested delta and one pan notification is emitted. No
## bounds are enforced — town bounds belong to the town slice (design D5).
func pan_by(world_delta: Vector2) -> Dictionary:
	if world_delta == Vector2.ZERO:
		return {"ok": false,
			"error": "[camera] pan_by rejected: pan_zero_delta"}
	if not world_delta.is_finite():
		return {"ok": false,
			"error": "[camera] pan_by rejected: pan_invalid_delta"}
	position += world_delta
	camera_panned.emit(world_delta)
	return {"ok": true, "error": ""}


## Maps a pointer event; returns true when the event was consumed.
## Consumption rules (design D7): a pressed wheel notch is always a camera
## gesture — consumed even when fail-closed at a level bound, and then
## silent; a left press begins a drag, motion while dragging pans so the
## grabbed content follows the cursor (screen movement divided by the
## committed factor), a left release ends the drag; every other event is
## left unconsumed so future selection/UI keeps its input.
func handle_input(event: InputEvent) -> bool:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.pressed and button.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom_in()
			return true
		if button.pressed and button.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom_out()
			return true
		if button.button_index == MOUSE_BUTTON_LEFT:
			if button.pressed:
				_dragging = true
				return true
			if _dragging:
				_dragging = false
				return true
		return false
	if event is InputEventMouseMotion:
		if not _dragging:
			return false
		var motion := event as InputEventMouseMotion
		if motion.relative != Vector2.ZERO:
			pan_by(-motion.relative / zoom_factor())
		return true
	return false


## Commits a new zoom level: the factor getter follows the table, the
## node's own zoom stays in agreement, and one notification carries the new
## level (design D6: change-only emission).
func _commit_zoom_level(new_level: int) -> void:
	_zoom_level = new_level
	var factor := float(ZOOM_FACTORS[_zoom_level])
	zoom = Vector2(factor, factor)
	camera_zoomed.emit(_zoom_level)
