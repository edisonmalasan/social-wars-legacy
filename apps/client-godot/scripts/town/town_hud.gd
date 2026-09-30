extends RefCounted
## Authoritative resource HUD (OpenSpec `godot-town-rendering` "Authoritative
## resource HUD", design D6; `godot-building-resources` "Canonical resource
## projection" / "Resource readout completeness", design D1-D5).
##
## Display-only snapshot over the UI foundation's slot registry: one row per
## entry of the canonical projection in `resource_projection.gd` — the seven
## resources the readout shows (gold, wood, steel, oil, cash, energy, mana)
## plus the summary fields (name, level, xp) — every string exactly
## `str(state.value)`. **Every resource is named exactly as the legacy server
## names it: the primary currency is `gold`, never `coins`,** because
## `engine.apply_resources` writes `maps[0].gold` and the save carries no
## `coins` field at all (design D1). Nothing is computed — no deltas, no
## rates, no timers, no polling. A field the payload did not carry renders an
## explicit indicator naming that field (`[missing: <field>]`) — never a
## guessed, zeroed, or stale number (spec: "Name a missing value instead
## of guessing").
##
## The ten rows, their order, and their labels are the DELIVERED set: this
## change corrected one key (`coins` -> `gold`) and added no row, removed no
## row, and reordered nothing. The projection, not this module, owns which
## fields exist.
##
## Presentation is provisional (design Non-Goals): no authentic legacy
## HUD layout has been captured, so this binds slot, order, and typography
## as a documented placeholder until evidence exists.

const UiFoundation = preload("res://scripts/ui_foundation.gd")
const ResourceProjection = preload("res://scripts/town/resource_projection.gd")

## The UI-foundation slot the HUD owns.
const SLOT_NAME := "hud"
## Indicator rendered in place of a value the state does not carry.
const MISSING_FORMAT := ResourceProjection.MISSING_FORMAT

## Committed display: canonical field key -> the exact string on screen.
var field_texts := {}


## The display rows this HUD renders: the canonical projection's entries, in
## display order, as fresh copies. Exposed so a suite reads the SAME table
## the readout renders instead of restating it (design D5).
static func fields() -> Array:
	return ResourceProjection.rows()


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
	for entry in fields():
		var key := str(entry["name"])
		var label := str(entry["label"])
		var text := ResourceProjection.text_for(state, entry)
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


## The exact string displayed for a canonical field key ("" before attach /
## for a name the projection does not carry). Never keyed by the typed
## state's own field names, so a key the server does not produce can never
## resolve to a row.
func displayed(field_key: String) -> String:
	return str(field_texts.get(field_key, ""))


## The exact committed display map (canonical field key -> string).
func displayed_fields() -> Dictionary:
	return field_texts.duplicate()


## The house rejection envelope: names the violated condition, leaves the
## slot untouched (the caller maps this to the explicit town error state).
func _reject(operation: String, error: String) -> Dictionary:
	return {"ok": false,
		"error": "[town] hud %s rejected: %s" % [operation, error]}
