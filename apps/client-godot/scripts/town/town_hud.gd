extends RefCounted
## Authoritative resource HUD (OpenSpec `godot-town-rendering` "Authoritative
## resource HUD", design D6).
##
## Display-only snapshot over the UI foundation's slot registry: labels
## for the seven resources (coins, wood, steel, oil, cash, energy, mana)
## plus the summary fields (name, level, xp), every string exactly
## `str(state.value)`. Nothing is computed — no deltas, no rates, no
## timers, no polling. A field the payload did not carry renders an
## explicit indicator naming that field (`[missing: <field>]`) — never a
## guessed, zeroed, or stale number (spec: "Name a missing value instead
## of guessing").
##
## Presentation is provisional (design Non-Goals): no authentic legacy
## HUD layout has been captured, so this binds slot, order, and typography
## as a documented placeholder until evidence exists.

const UiFoundation = preload("res://scripts/ui_foundation.gd")

## The UI-foundation slot the HUD owns.
const SLOT_NAME := "hud"
## Indicator rendered in place of a value the state does not carry.
const MISSING_FORMAT := "[missing: %s]"

## Display order: [field key, group, human label]. `group` names where the
## value lives on the typed town state (`resources` or `summary`).
const FIELDS := [
	["coins", "resources", "Coins"],
	["wood", "resources", "Wood"],
	["steel", "resources", "Steel"],
	["oil", "resources", "Oil"],
	["cash", "resources", "Cash"],
	["energy", "resources", "Energy"],
	["mana", "resources", "Mana"],
	["name", "summary", "Name"],
	["level", "summary", "Level"],
	["xp", "summary", "XP"],
]

## Committed display: field key -> the exact string on screen.
var field_texts := {}


## Builds the HUD into the UI foundation's slot from the typed town state.
## Fail-closed: a missing state, a rejected registration, or a missing
## slot root returns `{ok, false}` naming the condition. Rebuilds reuse
## the registered slot (the foundation rejects duplicate registrations)
## and replace its contents.
func attach(ui: UiFoundation, state: Variant) -> Dictionary:
	field_texts = {}
	if state == null:
		return _reject("attach", "state_missing")
	if ui == null:
		return _reject("attach", "ui_foundation_unavailable")
	var registration: Dictionary
	if ui.has_slot(SLOT_NAME):
		registration = {"ok": true, "error": ""}
	else:
		registration = ui.register_slot(SLOT_NAME)
	if not bool(registration.get("ok", false)):
		return {"ok": false,
			"error": "[town] hud rejected: %s" % str(registration.get("error"))}
	var root: Control = ui.slot_root(SLOT_NAME)
	if root == null:
		return _reject("attach", "slot_root_unavailable")
	for child in root.get_children():
		root.remove_child(child)
		child.free()

	var column := VBoxContainer.new()
	column.name = "values"
	column.position = Vector2(8.0, 8.0)
	column.add_theme_constant_override("separation", 2)
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(column)
	for field in FIELDS:
		var key := str(field[0])
		var group := str(field[1])
		var label := str(field[2])
		var text := _text_for(state, group, key)
		field_texts[key] = text
		var row := Label.new()
		row.text = "%s: %s" % [label, text]
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		# Readable over the terrain: white text with a dark shadow
		# (provisional presentation).
		row.add_theme_color_override("font_color", Color.WHITE)
		row.add_theme_color_override("font_shadow_color",
			Color(0.0, 0.0, 0.0, 0.85))
		row.add_theme_constant_override("shadow_offset_x", 1)
		row.add_theme_constant_override("shadow_offset_y", 1)
		column.add_child(row)
	return {"ok": true, "error": ""}


## The exact string displayed for a field ("" before attach / unknown).
func displayed(field_key: String) -> String:
	return str(field_texts.get(field_key, ""))


## The exact committed display map (field key -> string).
func displayed_fields() -> Dictionary:
	return field_texts.duplicate()


## Value string for one field: the explicit missing-field indicator when
## the state does not carry it, otherwise `str(state.value)` verbatim.
func _text_for(state: Variant, group: String, key: String) -> String:
	for missing in state.missing:
		if str(missing) == key:
			return MISSING_FORMAT % key
	var bag: Variant = state.resources if group == "resources" else state.summary
	if bag == null or not (key in _field_names(bag)):
		return MISSING_FORMAT % key
	return str(bag.get(key))


## The property names of a state bag (Resources / Summary instances).
func _field_names(bag: Variant) -> Array:
	var names: Array = []
	for property in bag.get_property_list():
		if int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			names.append(str(property["name"]))
	return names


## The house rejection envelope: names the violated condition, leaves the
## slot untouched (the caller maps this to the explicit town error state).
func _reject(operation: String, error: String) -> Dictionary:
	return {"ok": false,
		"error": "[town] hud %s rejected: %s" % [operation, error]}
