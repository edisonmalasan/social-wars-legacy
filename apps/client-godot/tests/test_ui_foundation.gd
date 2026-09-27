extends "res://tests/test_base.gd"
## UI foundation suite (OpenSpec `godot-ui-foundation` tasks 1.3 / 2.1, spec:
## "UI foundation scaffold" + "Slot visibility control").
##
## Scaffold half: the component starts with an empty registry and its
## committed layer index, registers slots in order with full-rect visible
## pass-through containers and exactly one notification per registration,
## and rejects empty and duplicate registrations with named errors, the
## registry untouched, and silence.
##
## Visibility half: hide/show flips the committed visibility with exactly
## one change-only notification per change, while an unknown slot and an
## unchanged value are rejected with named errors, committed state
## untouched, and silence. A final source scan covers the scaffold's
## no-clock/no-persistence/no-loading/no-other-script clauses directly.
##
## Pure component: no API, no boot flow, no endpoint argument. Runs headless
## as part of `verify-boot.ps1`.

const UiFoundation = preload("res://scripts/ui_foundation.gd")
const UI_SOURCE := "res://scripts/ui_foundation.gd"
## Requirement clauses of "UI foundation scaffold" that no scenario
## covers on its own: the component must not read wall-clock or time
## services, must not perform persistence or content loading, and must not
## reference any other script or autoload (transport and legacy tokens are
## covered by the project-scope scan of every allow-listed file).
const UI_SOURCE_FORBIDDEN := [
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

## Registration payloads observed via the registration signal.
var _registered_payloads: Array = []
## Visibility payloads observed via the visibility signal, in emission order.
var _visibility_payloads: Array = []


func run_scenario() -> void:
	_check_empty_start()
	_check_register()
	_check_register_rejections()
	_check_visibility_control()
	_check_unknown_slot()
	_check_unchanged_value()
	_check_source_contract()


## Spec: "Start with an empty registry".
func _check_empty_start() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	check(ui is CanvasLayer, "the component is a CanvasLayer node")
	check_eq(ui.layer, ui.UI_LAYER_INDEX,
		"the node's layer agrees with the committed constant")
	check_eq(ui.UI_LAYER_INDEX, 1, "the committed layer index is 1")
	check_eq(ui.slot_names(), [], "the registry starts empty")
	check(ui.has_slot("hud") == false, "an unregistered slot is absent")
	check(ui.slot_root("hud") == null,
		"an unregistered slot has no container")
	check(ui.is_slot_visible("hud") == false,
		"an unregistered slot is not visible")
	check_eq(ui.get_child_count(), 0, "an empty registry owns no children")
	check_eq(_registered_payloads.size(), 0, "creation notifies nobody")
	check_eq(_visibility_payloads.size(), 0,
		"creation never changes visibility")
	ui.free()


## Spec: "Register a slot".
func _check_register() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	var first: Dictionary = ui.register_slot("hud")
	check(first.get("ok") == true, "registering a fresh name succeeds")
	check(ui.has_slot("hud"), "the slot is registered")
	check_eq(ui.slot_names(), ["hud"], "the registry lists the slot")
	var container: Control = ui.slot_root("hud")
	check(container != null, "the slot owns a container")
	check(container.get_parent() == ui, "the container is a child of the component")
	check_eq(container.anchor_left, 0.0, "the container spans the full rect (left)")
	check_eq(container.anchor_top, 0.0, "the container spans the full rect (top)")
	check_eq(container.anchor_right, 1.0, "the container spans the full rect (right)")
	check_eq(container.anchor_bottom, 1.0, "the container spans the full rect (bottom)")
	check_eq(container.visible, true, "a fresh slot starts visible")
	check(ui.is_slot_visible("hud"), "a fresh slot reports visible")
	check_eq(container.mouse_filter, Control.MOUSE_FILTER_IGNORE,
		"the container passes pointer input through")
	check_eq(_registered_payloads, ["hud"],
		"registration notifies once with the slot name")
	check_eq(_visibility_payloads.size(), 0,
		"registration does not notify visibility")

	var second: Dictionary = ui.register_slot("dialogs")
	check(second.get("ok") == true, "a second registration succeeds")
	check_eq(ui.slot_names(), ["hud", "dialogs"],
		"slots stay in registration order")
	check_eq(ui.get_child_count(), 2, "each slot owns one container")
	check_eq(ui.get_child(0), ui.slot_root("hud"),
		"the first registered container is the first child")
	check_eq(ui.get_child(1), ui.slot_root("dialogs"),
		"the later registered container follows it")
	check_eq(_registered_payloads, ["hud", "dialogs"],
		"each registration notifies exactly once")
	ui.free()


## Spec: "Reject an invalid registration".
func _check_register_rejections() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	ui.register_slot("hud")
	_reset_notifications()
	var container: Control = ui.slot_root("hud")

	var empty: Dictionary = ui.register_slot("")
	check(empty.get("ok") == false, "an empty name is rejected")
	check(String(empty.get("error", "")).find("slot_empty_name") != -1,
		"the error names the violated condition")
	check_eq(ui.slot_names(), ["hud"],
		"a rejected registration leaves the registry untouched")
	check_eq(ui.get_child_count(), 1,
		"a rejected registration adds no container")

	var duplicate: Dictionary = ui.register_slot("hud")
	check(duplicate.get("ok") == false, "a duplicate name is rejected")
	check(String(duplicate.get("error", "")).find("slot_already_registered") != -1,
		"the error names the violated condition")
	check_eq(ui.slot_names(), ["hud"],
		"the duplicate leaves the registry untouched")
	check_eq(ui.slot_root("hud"), container,
		"the duplicate never replaces the committed container")
	check_eq(ui.get_child_count(), 1, "the duplicate adds no container")
	check_eq(_registered_payloads.size(), 0,
		"rejected registrations never notify")
	ui.free()


## Spec: "Hide and show a registered slot".
func _check_visibility_control() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	ui.register_slot("hud")
	_reset_notifications()
	var container: Control = ui.slot_root("hud")

	var hidden: Dictionary = ui.set_slot_visible("hud", false)
	check(hidden.get("ok") == true, "hiding a visible slot succeeds")
	check_eq(ui.is_slot_visible("hud"), false,
		"the committed visibility flips to hidden")
	check_eq(container.visible, false, "the container leaves the view")
	check_eq(_visibility_payloads, [["hud", false]],
		"the change notifies once with the new value")

	var shown: Dictionary = ui.set_slot_visible("hud", true)
	check(shown.get("ok") == true, "showing a hidden slot succeeds")
	check_eq(ui.is_slot_visible("hud"), true,
		"the committed visibility flips back")
	check_eq(container.visible, true, "the container returns to view")
	check_eq(_visibility_payloads, [["hud", false], ["hud", true]],
		"each committed change notifies exactly once")
	check_eq(ui.slot_names(), ["hud"],
		"visibility changes never touch the registry")
	check_eq(ui.slot_root("hud"), container,
		"visibility changes never replace the container")
	check_eq(_registered_payloads.size(), 0,
		"visibility changes never notify registration")
	ui.free()


## Spec: "Reject an unknown slot".
func _check_unknown_slot() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	ui.register_slot("hud")
	_reset_notifications()
	var container: Control = ui.slot_root("hud")

	var unknown: Dictionary = ui.set_slot_visible("ghost", false)
	check(unknown.get("ok") == false, "an unknown slot is rejected")
	check(String(unknown.get("error", "")).find("slot_not_registered") != -1,
		"the error names the violated condition")
	check_eq(ui.slot_names(), ["hud"], "the registry is unchanged")
	check_eq(ui.is_slot_visible("hud"), true,
		"committed visibility is unchanged")
	check_eq(container.visible, true, "the container stays in view")
	check_eq(_visibility_payloads.size(), 0,
		"a rejected write notifies nobody")
	check_eq(_registered_payloads.size(), 0,
		"a rejected write never registers anything")
	ui.free()


## Spec: "Reject an unchanged value".
func _check_unchanged_value() -> void:
	_reset_notifications()
	var ui: Variant = _new_ui()
	ui.register_slot("hud")
	_reset_notifications()

	var unchanged: Dictionary = ui.set_slot_visible("hud", true)
	check(unchanged.get("ok") == false,
		"re-requesting the current visibility is rejected")
	check(String(unchanged.get("error", "")).find("slot_visibility_unchanged") != -1,
		"the error names the violated condition")
	check_eq(ui.is_slot_visible("hud"), true,
		"the committed visibility is unchanged")
	check_eq(_visibility_payloads.size(), 0,
		"an unchanged request notifies nobody")

	ui.set_slot_visible("hud", false)
	_reset_notifications()
	var still_hidden: Dictionary = ui.set_slot_visible("hud", false)
	check(still_hidden.get("ok") == false,
		"re-requesting the hidden value is rejected too")
	check(String(still_hidden.get("error", "")).find("slot_visibility_unchanged") != -1,
		"the error names the violated condition")
	check_eq(ui.is_slot_visible("hud"), false,
		"the committed visibility stays hidden")
	check_eq(_visibility_payloads.size(), 0,
		"the second unchanged request notifies nobody")
	ui.free()


## Requirement clauses with no scenario of their own: the scaffold source
## must contain no wall-clock/time-service read, no persistence or content
## loading, and no reference to any other script or autoload.
func _check_source_contract() -> void:
	var handle := FileAccess.open(UI_SOURCE, FileAccess.READ)
	check(handle != null, "the component source is readable: " + UI_SOURCE)
	if handle == null:
		return
	var body := handle.get_as_text()
	handle.close()
	check(body.length() > 0, "the component source is non-empty")
	for token in UI_SOURCE_FORBIDDEN:
		check(body.find(token) == -1,
			"ui_foundation.gd must not reference %s" % token)


## Each scenario asserts its own notifications from a clean slate (payload
## history across component instances is scenario-local, not global).
func _reset_notifications() -> void:
	_registered_payloads.clear()
	_visibility_payloads.clear()


## A fresh component with both signals observed into the payload arrays.
func _new_ui() -> Variant:
	var ui: Variant = UiFoundation.new()
	ui.slot_registered.connect(_on_slot_registered)
	ui.slot_visibility_changed.connect(_on_slot_visibility_changed)
	return ui


func _on_slot_registered(slot_name: String) -> void:
	_registered_payloads.append(slot_name)


func _on_slot_visibility_changed(slot_name: String, visible: bool) -> void:
	_visibility_payloads.append([slot_name, visible])
