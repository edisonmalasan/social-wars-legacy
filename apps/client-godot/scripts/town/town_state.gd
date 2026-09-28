extends RefCounted
## Typed town state parsed from the bootstrap payload (OpenSpec
## `godot-town-rendering` "Typed town state loading", design D1).
##
## One parser serves both entry points: the windowed boot handoff (the
## Compatibility API's `get_player_info` payload, root `map`) and the
## slice scene (a preserved legacy village file, `maps[0]`). Presentation
## code receives only the typed `State` — never the raw payload.
##
## Fail-closed contract (spec): structural violations (no default map,
## malformed placement rows, non-integer coordinates, present-but-invalid
## field types) return `{ok: false, error}` naming the offending field and
## produce no state; nothing is fabricated, defaulted, or dropped. Content
## resolution failures are different by design: a legacy save may
## legitimately contain ids the content package lacks, so those placements
## are kept verbatim with the failure recorded (`content_error`,
## `unresolved_ids`) and render later as placeholders. A resource or
## summary field that is simply absent is recorded in `missing` (HUD names
## it per "Authoritative resource HUD") instead of failing the save.
##
## Requires an explicitly loaded `ContentRegistry` (content + asset
## registry) — the registry's own contract is explicit loading, and this
## parser never loads implicitly on the caller's behalf.

## Content domains searched, in order, for a placed legacy id (the
## normalized package splits items into buildings/units/specials; ids do
## not overlap between domains).
const CONTENT_DOMAINS := ["buildings", "units", "specials"]
## The registry script, used as the parameter type: callers pass the
## ContentRegistry autoload (or an equally loaded instance).
const RegistryScript = preload("res://scripts/content_registry.gd")
## Resource fields of the town HUD and where each lives in the payload.
const RESOURCE_FIELDS := {
	"coins": "map.gold",
	"wood": "map.wood",
	"steel": "map.steel",
	"oil": "map.oil",
	"cash": "playerInfo.cash",
	"energy": "privateState.energy",
	"mana": "privateState.mana",
}
## Summary fields of the town HUD and where each lives in the payload.
const SUMMARY_FIELDS := {
	"name": "playerInfo.name",
	"level": "map.level",
	"xp": "map.xp",
}


## One placement exactly as the legacy save carries it: the eight
## positional fields kept verbatim (`raw` preserves the parsed values
## byte-for-byte) plus resolved content metadata for rendering.
class Placement:
	extends RefCounted
	## Item (legacy id) as an integer.
	var item := 0
	## Integer grid coordinates.
	var cell := Vector2i.ZERO
	## The remaining legacy fields, verbatim (timestamp, orientation,
	## store, attr, player) — never coerced, never dropped.
	var timestamp: Variant = null
	var orientation: Variant = null
	var store: Variant = null
	var attr: Variant = null
	var player: Variant = null
	## The full eight-field row as parsed from the save.
	var raw: Array = []
	## Save order — the deterministic last tie-break of the depth sort.
	var order := 0
	## True when ContentRegistry resolved the placed legacy id.
	var content_ok := false
	## Why resolution failed when content_ok is false ("" when resolved).
	var content_error := ""
	## Resolved content metadata (valid when content_ok): display name,
	## kind (building/unit/special), footprint in cells, img_name, and the
	## item-sprite asset status from the asset ID registry. An unresolved
	## id keeps a single-cell footprint until rendering (placeholder).
	var name := ""
	var kind := ""
	var footprint := Vector2i.ONE
	var img_name := ""
	var asset_status := ""


## The HUD's resource values, parsed from the payload and never computed.
class Resources:
	extends RefCounted
	var coins := 0
	var wood := 0
	var steel := 0
	var oil := 0
	var cash := 0
	var energy := 0
	var mana := 0


## The HUD's summary values, parsed from the payload and never computed.
class Summary:
	extends RefCounted
	var name := ""
	var level := 0
	var xp := 0


## The typed town state handed to presentation code.
class State:
	extends RefCounted
	## Placement objects in save order.
	var placements: Array = []
	## Parsed resource and summary values.
	var resources := Resources.new()
	var summary := Summary.new()
	## Displayed field keys the payload did not carry (HUD names them).
	var missing: Array = []
	## Distinct placed legacy ids ContentRegistry could not resolve.
	var unresolved_ids: Array = []


## Parse a bootstrap/village payload into a typed town state. Returns
## `{ok, error, state}`; on failure `state` is null and `error` names the
## missing or invalid field.
static func parse(payload: Variant, registry: RegistryScript) -> Dictionary:
	var reject := func(message: String) -> Dictionary:
		return {"ok": false, "error": "[town] parse rejected: " + message,
			"state": null}
	if not (payload is Dictionary):
		return reject.call("payload is not an object")
	if registry == null:
		return reject.call("content registry is unavailable")
	if not registry.is_loaded():
		return reject.call("content is not loaded")
	if not registry.assets_loaded():
		return reject.call("asset registry is not loaded")
	var map: Variant = _default_map(payload)
	if map == null:
		return reject.call("field 'map' (default map) is missing or invalid")
	var rows: Variant = _placement_rows(map)
	if rows == null:
		return reject.call("field 'items' is missing or invalid")

	var state := State.new()
	# Resource/summary lookup roots: the extracted default map (root `map`
	# or `maps[0]`) plus the payload's root-level player objects.
	var values := {
		"map": map,
		"playerInfo": (payload as Dictionary).get("playerInfo"),
		"privateState": (payload as Dictionary).get("privateState"),
	}
	var order := 0
	for key in (rows as Dictionary).keys():
		var row: Variant = (rows as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			return reject.call(
				"placement '%s' is not an eight-field array" % str(key))
		var placement := Placement.new()
		placement.raw = (row as Array).duplicate()
		placement.order = order
		order += 1
		var item: Variant = _integer(row[0])
		if item == null:
			return reject.call(
				"field 'item' of placement '%s' is not an integer" % str(key))
		var x: Variant = _integer(row[1])
		var y: Variant = _integer(row[2])
		if x == null or y == null:
			return reject.call(
				"coordinate of placement '%s' is not an integer" % str(key))
		placement.item = item as int
		placement.cell = Vector2i(x as int, y as int)
		placement.timestamp = row[3]
		placement.orientation = row[4]
		placement.store = row[5]
		placement.attr = row[6]
		placement.player = row[7]
		_resolve_content(placement, registry)
		if not placement.content_ok \
				and not (placement.item in state.unresolved_ids):
			state.unresolved_ids.append(placement.item)
		state.placements.append(placement)

	for hud_key in RESOURCE_FIELDS:
		var source: String = RESOURCE_FIELDS[hud_key]
		var cell_value: Variant = _payload_value(values, source)
		if cell_value == null:
			state.missing.append(hud_key)
			continue
		var number: Variant = _integer(cell_value)
		if number == null:
			return reject.call("field '%s' is not an integer" % source)
		(state.resources as Resources).set(hud_key, number as int)
	for hud_key in SUMMARY_FIELDS:
		var source: String = SUMMARY_FIELDS[hud_key]
		var cell_value: Variant = _payload_value(values, source)
		if cell_value == null:
			state.missing.append(hud_key)
			continue
		if hud_key == "name":
			if not (cell_value is String):
				return reject.call("field '%s' is not a string" % source)
			(state.summary as Summary).name = cell_value
		else:
			var number: Variant = _integer(cell_value)
			if number == null:
				return reject.call("field '%s' is not an integer" % source)
			(state.summary as Summary).set(hud_key, number as int)
	return {"ok": true, "error": "", "state": state}


## The payload's default map: root `map` (get_player_info response) or
## `maps[0]` (preserved legacy village file). Null when neither exists.
static func _default_map(payload: Dictionary) -> Variant:
	if payload.get("map") is Dictionary \
			and not (payload["map"] as Dictionary).is_empty():
		return payload["map"]
	if payload.get("maps") is Array \
			and not (payload["maps"] as Array).is_empty() \
			and payload["maps"][0] is Dictionary:
		return payload["maps"][0]
	return null


## The placement container of a map as `{save_key: row}`: legacy saves
## store items as an object keyed by placement id or as an array. Null
## when absent or wrongly typed (an empty container is a valid town).
static func _placement_rows(map: Dictionary) -> Variant:
	var items: Variant = map.get("items")
	if items is Dictionary:
		return items
	if items is Array:
		var keyed: Dictionary = {}
		for index in range((items as Array).size()):
			keyed[index] = items[index]
		return keyed
	return null


## Resolve one placement against ContentRegistry: content entry (name,
## kind, footprint, img_name) plus the item-sprite asset status. Failures
## are recorded on the placement, never thrown.
static func _resolve_content(placement: Placement,
		registry: RegistryScript) -> void:
	var id_text := str(placement.item)
	var found := false
	for domain in CONTENT_DOMAINS:
		if not registry.has_domain(domain):
			continue
		var result: Dictionary = registry.get_entry(domain, id_text)
		if not bool(result.get("found", false)):
			continue
		var entry: Variant = result.get("entry")
		if not (entry is Dictionary):
			continue
		found = true
		placement.name = str(entry.get("name", ""))
		placement.kind = str(entry.get("kind", ""))
		placement.footprint = Vector2i(
			int(entry.get("width", 1)), int(entry.get("height", 1)))
		placement.img_name = str(entry.get("img_name", ""))
		break
	if not found:
		placement.content_ok = false
		placement.content_error = \
			"[town] content id not found in package: %s" % id_text
		return
	placement.content_ok = true
	placement.content_error = ""
	var asset: Dictionary = registry.resolve_asset(
		"item_sprites", placement.img_name)
	placement.asset_status = str(
		(asset.get("entry") as Dictionary).get("status", "") \
		if asset.get("entry") is Dictionary else "")
	if not bool(asset.get("found", false)):
		placement.asset_status = "unregistered"


## Integer conversion for legacy JSON numbers (parsed as floats) and
## ints; null for anything non-integral or non-numeric.
static func _integer(value: Variant) -> Variant:
	if typeof(value) == TYPE_INT:
		return value
	if typeof(value) == TYPE_FLOAT and not is_nan(value) and not is_inf(value) \
			and value == floorf(value):
		return int(value)
	return null


## Read `a.b.c` from the payload; null when any level is absent. Present
## but wrongly-typed leaves are rejected by the caller.
static func _payload_value(payload: Dictionary, path: String) -> Variant:
	var cursor: Variant = payload
	for part in path.split("."):
		if not (cursor is Dictionary) or not (cursor as Dictionary).has(part):
			return null
		cursor = (cursor as Dictionary)[part]
	return cursor
