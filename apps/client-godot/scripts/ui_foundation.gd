extends CanvasLayer
## UI foundation (M5 foundation, OpenSpec `godot-ui-foundation` design D1-D6).
##
## Reusable overlay component for the town/HUD scene that will instance it
## (design D1: deliberately not an autoload — UI is presentation owned by the
## scene that shows the game, and no game world exists yet). Committed state
## is the node's layer index plus an ordered registry of named slots, each
## owning a full-rect container that starts visible and passes pointer input
## through (design D4: interactivity is opt-in per widget a consumer adds
## inside its slot). Provisional foundation (design D2): no legacy UI
## behavior has been captured, so authentic slot taxonomy, stacking order,
## and HUD layout bind later, with evidence.
##
## The component follows the fail-closed `{ok, error}` envelope of the other
## foundation scaffolds: a rejected request names the violated condition,
## leaves committed state untouched, and notifies nobody (spec: "Reject an
## invalid registration", "Reject an unknown slot", "Reject an unchanged
## value"). Notifications are change-only (design D6).

## Emitted once per successful registration with the slot name.
signal slot_registered(slot_name: String)
## Emitted once per committed visibility change with the new visibility.
signal slot_visibility_changed(slot_name: String, visible: bool)

## Committed layer index for the foundation canvas: above default world
## canvas content, set from this constant at creation. The value is a
## provisional foundation choice — no legacy layering evidence exists
## (design D5).
const UI_LAYER_INDEX := 1

## Registration-ordered slot names.
var _slot_names: Array = []
## Slot name -> its full-rect container.
var _slot_roots: Dictionary = {}
## Slot name -> committed visibility (true at registration).
var _slot_visible: Dictionary = {}


func _init() -> void:
	layer = UI_LAYER_INDEX


## Registers a named slot with a fresh full-rect pass-through container.
## Fail-closed: an empty name or an already-registered name is rejected
## with an error naming the condition, the registry is untouched, and
## nobody is notified (spec: "Reject an invalid registration").
func register_slot(slot_name: String) -> Dictionary:
	if slot_name.is_empty():
		return _reject("register_slot", "slot_empty_name")
	if _slot_roots.has(slot_name):
		return _reject("register_slot", "slot_already_registered")
	var container := Control.new()
	container.name = slot_name
	container.set_anchors_preset(Control.PRESET_FULL_RECT)
	container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	container.visible = true
	add_child(container)
	_slot_names.append(slot_name)
	_slot_roots[slot_name] = container
	_slot_visible[slot_name] = true
	slot_registered.emit(slot_name)
	return {"ok": true, "error": ""}


## Commits the visibility of a registered slot. Fail-closed: an unknown
## slot and a request that equals the committed value are rejected with an
## error naming the condition, committed state is untouched, and nobody is
## notified (spec: "Slot visibility control").
func set_slot_visible(slot_name: String, visible: bool) -> Dictionary:
	if not _slot_roots.has(slot_name):
		return _reject("set_slot_visible", "slot_not_registered")
	if bool(_slot_visible[slot_name]) == visible:
		return _reject("set_slot_visible", "slot_visibility_unchanged")
	_slot_visible[slot_name] = visible
	var container: Control = _slot_roots[slot_name]
	container.visible = visible
	slot_visibility_changed.emit(slot_name, visible)
	return {"ok": true, "error": ""}


## True when the slot is registered.
func has_slot(slot_name: String) -> bool:
	return _slot_roots.has(slot_name)


## The slot's full-rect container, or null when the slot is unregistered.
func slot_root(slot_name: String) -> Control:
	if not _slot_roots.has(slot_name):
		return null
	return _slot_roots[slot_name] as Control


## The registered slot names in registration order (a copy; the committed
## registry cannot be mutated from outside).
func slot_names() -> Array:
	return _slot_names.duplicate()


## The committed visibility of a slot (false when unregistered).
func is_slot_visible(slot_name: String) -> bool:
	return bool(_slot_visible.get(slot_name, false))


## The house rejection envelope: names the violated condition, leaves
## committed state untouched, notifies nobody.
func _reject(operation: String, error: String) -> Dictionary:
	return {"ok": false,
		"error": "[ui] %s rejected: %s" % [operation, error]}
