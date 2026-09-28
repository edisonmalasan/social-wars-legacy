extends Camera2D
## Camera controls (M5 foundation, OpenSpec `godot-camera` design D1-D7).
##
## Reusable view component for the town scene that will instance it (design
## D1: deliberately not an autoload — a camera belongs to the scene that
## renders the world, and no world exists yet). Committed view state is the
## world position plus a discrete zoom level 0..2 over the fixed factor
## table (design D4), with the node's own zoom kept equal to the committed
## factor. Provisional foundation (design D2): no legacy camera behavior
## has been captured, so authentic bounds, ranges, and input feel are
## still provisional — the town slice commits optional fail-closed world
## bounds (design D1) over the projection's world rectangle, and unset
## bounds keep the original unbounded contract byte-for-byte.
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
## Committed world bounds (empty while unbounded).
var _world_bounds := Rect2()
## True while world bounds are committed (town slice design D1).
var _has_world_bounds := false


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
## and the committed position is untouched; with world bounds committed, a
## delta whose result would leave them is rejected the same way (named
## error, no movement, no notification); otherwise the position moves by
## exactly the requested delta and one pan notification is emitted. With
## bounds unset the unbounded foundation contract applies byte-for-byte.
func pan_by(world_delta: Vector2) -> Dictionary:
	if world_delta == Vector2.ZERO:
		return {"ok": false,
			"error": "[camera] pan_by rejected: pan_zero_delta"}
	if not world_delta.is_finite():
		return {"ok": false,
			"error": "[camera] pan_by rejected: pan_invalid_delta"}
	var target := position + world_delta
	if _has_world_bounds and not _contains(target):
		return {"ok": false,
			"error": "[camera] pan_by rejected: outside_world_bounds"}
	position = target
	camera_panned.emit(world_delta)
	return {"ok": true, "error": ""}


## True while world bounds are committed.
func has_world_bounds() -> bool:
	return _has_world_bounds


## The committed world bounds (Rect2() while unbounded). Reflects only
## committed state.
func world_bounds() -> Rect2:
	return _world_bounds


## Commits world bounds. Fail-closed: a non-finite component or empty
## extent is rejected with a named error, bounds and position unchanged.
## A committed position outside the new bounds is corrected exactly once
## (one movement, one pan notification carrying the correction delta); a
## position already inside commits the bounds with no movement and no
## notification. Bounds never affect zoom level, factor, or node zoom.
func set_world_bounds(rect: Rect2) -> Dictionary:
	if not rect.position.is_finite() or not rect.size.is_finite():
		return {"ok": false,
			"error": "[camera] set_world_bounds rejected: bounds_non_finite"}
	if rect.size.x <= 0.0 or rect.size.y <= 0.0:
		return {"ok": false,
			"error": "[camera] set_world_bounds rejected: bounds_empty"}
	_world_bounds = rect
	_has_world_bounds = true
	if not _contains(position):
		var corrected := position.clamp(rect.position, rect.position + rect.size)
		var correction := corrected - position
		position = corrected
		if correction != Vector2.ZERO:
			camera_panned.emit(correction)
	return {"ok": true, "error": ""}


## Clears world bounds, restoring the unbounded pan contract: no movement
## and no notification.
func clear_world_bounds() -> Dictionary:
	_world_bounds = Rect2()
	_has_world_bounds = false
	return {"ok": true, "error": ""}


## Inclusive containment of a point in the committed bounds (edges are
## inside, matching Vector2.clamp's correction target).
func _contains(point: Vector2) -> bool:
	return (point.x >= _world_bounds.position.x
		and point.x <= _world_bounds.position.x + _world_bounds.size.x
		and point.y >= _world_bounds.position.y
		and point.y <= _world_bounds.position.y + _world_bounds.size.y)


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
