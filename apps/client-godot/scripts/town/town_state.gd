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
## malformed placement rows, non-integer coordinates, a malformed storage
## mapping, present-but-invalid field types) return `{ok: false, error}`
## naming the offending field and produce no state; nothing is fabricated,
## defaulted, or dropped. Content
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
##
## Addressable keys (building-move design D7): every placement also carries
## the legacy map key it was stored under, so a move intent can name the row
## it targets. A key that is not a positive integer is recorded verbatim as
## unaddressable (`NO_SLOT`) instead of being coerced — a coerced index
## would address a *different* row, which is exactly the failure this
## records instead.
##
## Construction state (building-construction task 4.1, design D5): every
## placement also carries the three legacy attribute-bag facts a build
## records — the click counter (`attr["nc"]`), the recorded countdown
## (`attr["cp"]`), and the start instant they are measured from (the row's
## own timestamp, meaningful only while a countdown is recorded). Each is
## ABSENT when the row carries none, and each is parsed fail-closed in the
## one shared placement parser, so the readout and the step logic read a
## single rule set: an attribute bag that is not an object, a counter that is
## not a non-negative integer, and a countdown that is not a positive integer
## (legacy can never record one — a non-positive duration CLEARS the whole
## bag instead) each reject the save naming the offending field. The click
## requirement and the derived duration are NOT here: both come from
## committed content, and the service derives them the same way.

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
## The storage field of the default map and the key it is recorded under in
## `State.missing` when the payload carries no storage at all (design D7:
## absent is named, never defaulted to an empty inventory).
const STORAGE_FIELD := "map.store"
const STORAGE_MISSING_KEY := "storage"


## The addressable-index sentinel: a placement whose legacy map key is not
## a positive integer carries no index a move intent could name
## (building-move design D7). Never `0` — coercing an unusable key to 0
## would address a real row.
const NO_SLOT := -1

## One placement exactly as the legacy save carries it: the eight
## positional fields kept verbatim (`raw` preserves the parsed values
## byte-for-byte), the legacy map key the row was stored under
## (building-move design D7), plus resolved content metadata for
## rendering.
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
	## The legacy map key this row was parsed from, as text, verbatim —
	## the diagnostic the move flow names when the key is unusable.
	var slot_key := ""
	## The addressable index a legacy `move` names this row by (design
	## D7): the positive integer the key carried, or `NO_SLOT` (-1) when
	## the key is not one. Never coerced to a guessable value.
	var slot := -1
	## The build's click counter (`attr["nc"]`) as a non-negative integer, or
	## null when the row records none. Seeded by the purchase half for an
	## item whose committed `clicks_to_build > 0`, raised by a build click,
	## and deleted by a completion.
	var clicks: Variant = null
	## The build's recorded countdown in seconds (`attr["cp"]`) as a positive
	## integer, or null when the row records none.
	var countdown: Variant = null
	## The instant the countdown started — the row's own timestamp, and only
	## present while a countdown is recorded AND the row carries a positive
	## one. The remaining time is a pure client derivation from this and
	## `countdown`; no legacy branch ever computes it.
	var started_at: Variant = null
	## False only when the row's attribute bag is not an object at all, so no
	## construction fact can be read from it. Such a row still parses and
	## renders (the delivered parser keeps every row verbatim), and the build
	## flow refuses it by name rather than reading a number out of a value that
	## is not a bag.
	var construction_readable := true
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
	## The player's storage: string item id -> integer quantity, preserved
	## verbatim (quantity `0` included, unresolved ids included). Empty ONLY
	## when the payload carried a storage object with no entries; an absent
	## field is recorded in `missing` under `STORAGE_MISSING_KEY` instead of
	## being defaulted here (design D7).
	var storage: Dictionary = {}
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
	# Storage (design D7): absent is named in `missing`, never defaulted to
	# an empty inventory; a present-but-invalid mapping rejects the parse
	# naming the offending key, through the one shared parser the purchase
	# apply reuses for the response's `store`.
	var storage: Dictionary = _storage_of(map)
	if not bool(storage.get("ok", false)):
		return reject.call(str(storage.get("error", "")))

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
		# The legacy map key the row was stored under (design D7): the
		# addressable index a move intent names, or the recorded
		# unaddressable key. Recorded either way — never dropped, never
		# coerced into an index that could name a different row.
		placement.slot_key = str(key)
		placement.slot = _slot_index(key)
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
		# Construction state (building-construction design D5): parsed from the
		# row's own attribute bag in the SAME fail-closed pass, so the readout
		# and the step logic read one rule set. A row whose bag is not an object
		# is NOT a rejected save — the delivered parser has always kept such a
		# row verbatim — but it records NO construction state and is marked
		# unreadable, so the build flow refuses it by name instead of reading
		# numbers out of something that is not a bag.
		var construction: Dictionary = _construction_of(row, str(key))
		if construction.get("fatal", false):
			return reject.call(str(construction.get("error", "")))
		placement.construction_readable = bool(construction.get("ok", false))
		placement.clicks = construction["clicks"]
		placement.countdown = construction["countdown"]
		placement.started_at = construction["started_at"]
		_resolve_content(placement, registry)
		if not placement.content_ok \
				and not (placement.item in state.unresolved_ids):
			state.unresolved_ids.append(placement.item)
		state.placements.append(placement)

	state.storage = storage["storage"]
	if not bool(storage["present"]):
		state.missing.append(STORAGE_MISSING_KEY)
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


## The player's storage from a default map: `{ok, present, storage, error}`
## (design D7). One parser serves BOTH entry points — this bootstrap/village
## parse and the purchase apply, which feeds it the response's `store`
## mapping — so a response can never be read with different rules than the
## payload it replaces.
##
## Rules (fail-closed, nothing guessed):
##   * the field absent -> `present: false` with an EMPTY mapping: the state
##     records the key in `missing` and the readout names it, rather than
##     presenting an empty inventory as fact;
##   * present but not an object, a key that is not an item id, or a
##     quantity that is not a non-negative integer -> `{ok: false}` with an
##     error naming the offending key, exactly as the placement rows do;
##   * quantity `0` is preserved verbatim (observed in real saves) and an id
##     the content package cannot resolve is carried through untouched —
##     the parser never drops what it does not understand.
static func storage_of(value: Variant) -> Dictionary:
	if value == null:
		return {"ok": true, "present": false, "storage": {}, "error": ""}
	if not (value is Dictionary):
		return _storage_reject("field '%s' is not an object" % STORAGE_FIELD)
	var storage := {}
	for key: Variant in (value as Dictionary):
		var id: Variant = _item_id(key)
		if id == null:
			return _storage_reject("storage entry key '%s' is not an item id"
				% str(key))
		var quantity: Variant = _integer((value as Dictionary)[key])
		if quantity == null or int(quantity) < 0:
			return _storage_reject(
				"storage entry '%s' quantity is not a non-negative integer"
				% str(int(id)))
		storage[str(int(id))] = int(quantity)
	return {"ok": true, "present": true, "storage": storage, "error": ""}


## The default map's storage field through `storage_of()` (the payload's
## own entry point; the purchase apply calls `storage_of()` directly).
static func _storage_of(map: Variant) -> Dictionary:
	if not (map is Dictionary):
		return _storage_reject("field '%s' has no default map" % STORAGE_FIELD)
	return storage_of((map as Dictionary).get("store"))


## The resolved content name for one legacy item id, or "" when the content
## package does not know it (design D7: the storage readout renders the raw
## item id in that case — a name is never guessed). Searches the same
## domains, in the same order, as the placement resolution.
static func content_name(item_id: int, registry: RegistryScript) -> String:
	if registry == null or not registry.is_loaded():
		return ""
	var id_text := str(item_id)
	for domain in CONTENT_DOMAINS:
		if not registry.has_domain(domain):
			continue
		var result: Dictionary = registry.get_entry(domain, id_text)
		if not bool(result.get("found", false)):
			continue
		var entry: Variant = result.get("entry")
		if not (entry is Dictionary):
			continue
		return str((entry as Dictionary).get("name", ""))
	return ""


## One storage key -> its non-negative integer id, or null when the key is
## not an item id. The legacy save keys storage by the stringified item id
## (`engine.add_store_item` writes `map["store"][str(item_id)]`), so a digit
## string is the documented shape; an int key is accepted and canonicalized
## to its string form. Nothing else is ever coerced.
static func _item_id(key: Variant) -> Variant:
	if key is int:
		return int(key) if int(key) >= 0 else null
	if key is String:
		var text := str(key)
		if text.is_empty() or text.length() > 16:
			return null
		for character in text:
			if character < "0" or character > "9":
				return null
		return text.to_int()
	return null


## One placement map key -> its addressable index, or `NO_SLOT` when the key
## is not a positive integer (building-move design D7). Legacy resolves a
## row with `engine.map_get_item(map, index)`, i.e.
## `map["items"][str(index)]`, so a digit string is the documented shape and
## an int key canonicalizes to the same index. Everything else is recorded
## as unaddressable instead of coerced: a key legacy could not address
## (`"0"`, `"-1"`, `"mystery"`, an empty string, a float) yields
## `NO_SLOT`, never a guess that would name a different row.
static func _slot_index(key: Variant) -> int:
	if key is int:
		return int(key) if int(key) > 0 else NO_SLOT
	if key is String:
		var text := str(key)
		if text.is_empty() or text.length() > 16:
			return NO_SLOT
		for character in text:
			if character < "0" or character > "9":
				return NO_SLOT
		var value := text.to_int()
		return value if value > 0 else NO_SLOT
	return NO_SLOT


## One placement key -> its addressable index, or null when the key is not
## a positive integer (the public form of `_slot_index`, for callers that
## want the "no index" case without the sentinel).
static func slot_of(key: Variant) -> Variant:
	var index := _slot_index(key)
	return null if index == NO_SLOT else index


## True when the placement carries an addressable index a move intent can
## name (design D7). Reads the sentinel, never a guess.
static func is_addressable(placement: Variant) -> bool:
	if placement == null or not (placement is Placement):
		return false
	return int((placement as Placement).slot) > 0


## The construction state of one placement as the pure flow helpers read it:
## `{ok, error, clicks, countdown, started_at}`, where each of the three facts
## is null when the row records none (building-construction design D5). The
## public form of `_construction_of`, so the readout, the step machine, and the
## shared placement parser all consume ONE rule set and can never disagree
## about what a row carries.
static func construction_of(placement: Variant) -> Dictionary:
	if placement == null or not (placement is Placement):
		return {"ok": false, "error": "[town] no typed placement to read",
			"clicks": null, "countdown": null, "started_at": null}
	var typed: Placement = placement
	if not typed.construction_readable:
		return {"ok": false,
			"error": "the row's attribute bag is not an object, so no "
				+ "construction state can be read from it",
			"clicks": null, "countdown": null, "started_at": null}
	return {"ok": true, "error": "",
		"clicks": typed.clicks, "countdown": typed.countdown,
		"started_at": typed.started_at}


## One eight-field row -> its construction state, fail-closed.
##
## Rules (nothing guessed, nothing defaulted):
##   * `attr["nc"]`, when the bag is an object and carries it, must be a
##     non-negative integer: a click counter is a count, and a negative or
##     fractional one is not a shape legacy writes — a present-but-invalid
##     counter REJECTS the save naming the row;
##   * `attr["cp"]`, likewise, must be a POSITIVE integer: it is a duration in
##     seconds, and legacy can never record a non-positive one because a
##     non-positive `activate` duration clears the whole bag instead (design
##     D6) — a present-but-invalid countdown REJECTS the save naming the row;
##   * the start instant is the row's own timestamp, present only while a
##     countdown is recorded and only when that timestamp is a positive
##     integer — a zero timestamp means nothing stamped this row, so no
##     remaining time can be derived from it;
##   * a row whose bag is not an object at all records NO construction state
##     and is marked unreadable (`ok: false`, `fatal: false`): the delivered
##     parser has always kept such a row verbatim, so rejecting the save here
##     would change delivered behavior, while reading a counter out of a value
##     that is not a bag would be fabrication. The build flow refuses such a
##     row by name instead.
## Every other `attr` entry (`si` for friend assistance, and anything a
## future branch writes) is carried verbatim in `Placement.attr` and never
## interpreted here.
static func _construction_of(row: Array, key: String) -> Dictionary:
	var empty := {"ok": true, "error": "", "fatal": false, "clicks": null,
		"countdown": null, "started_at": null}
	if not (row[6] is Dictionary):
		return {"ok": false, "fatal": false,
			"error": "field 'attr' of placement '%s' is not an object" % key,
			"clicks": null, "countdown": null, "started_at": null}
	var attr: Dictionary = row[6]
	var clicks: Variant = null
	if attr.has("nc"):
		var counter: Variant = _integer(attr["nc"])
		if counter == null or int(counter) < 0:
			return {"ok": false, "fatal": true,
				"error": "click counter of placement '%s' is not a "
					% key + "non-negative integer",
				"clicks": null, "countdown": null, "started_at": null}
		clicks = counter
	var countdown: Variant = null
	if attr.has("cp"):
		var duration: Variant = _integer(attr["cp"])
		if duration == null or int(duration) <= 0:
			return {"ok": false, "fatal": true,
				"error": "countdown of placement '%s' is not a positive "
					% key + "integer",
				"clicks": null, "countdown": null, "started_at": null}
		countdown = duration
	var started: Variant = null
	if countdown != null:
		var stamp: Variant = _integer(row[3])
		if stamp != null and int(stamp) > 0:
			started = stamp
	return {"ok": true, "error": "", "fatal": false, "clicks": clicks,
		"countdown": countdown, "started_at": started}


## The house storage rejection envelope: names the offending field or key.
static func _storage_reject(message: String) -> Dictionary:
	return {"ok": false, "present": true, "storage": {},
		"error": "[town] parse rejected: " + message}


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
