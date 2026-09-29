extends RefCounted
## Typed placement catalog (building-placement, spec "Placement flow").
##
## Parses only the fields the flow needs — `id`, `name`, `costs`,
## `min_level`, `in_store`, `width`, `height`, `type` — fail-closed from
## the bootstrap config payload the client already holds (design D10: one
## request per launch, never a second one, never a re-fetch). The parser
## mirrors `TownState.parse`: every malformed field returns
## `{ok: false, error}` naming the offending item and field and produces
## no catalog — nothing is guessed, defaulted, or dropped, because a
## guessed price would contradict the spec's "rather than guess a price or
## fabricate an entry".
##
## Cost semantics match the v0 endpoint and the fake double exactly: the
## legacy cost keys `g/w/o/s/c` map onto resource names
## `gold/wood/oil/steel/cash`, `null`/"" means a free item, and an unknown
## key or a non-integer amount fails closed (the endpoint answers 500 for
## the same committed config; the catalog never invents a price). The
## committed payload stores every number as a JSON string, so `id`,
## `min_level`, `in_store`, `width`, and `height` accept digit strings,
## ints, and integral floats — the documented transport tolerance of the
## pinned engine.


## One placeable entry: the eight parsed fields plus the derived content
## footprint.
class Entry:
	extends RefCounted
	## Legacy item id as an integer.
	var id := 0
	## Display name verbatim from the payload.
	var name := ""
	## Derived cost: resource name -> integer amount ({} for a free item).
	var costs := {}
	## Store gating recorded verbatim; the picker filters on both this
	## and `min_level` against the loaded level.
	var min_level := 0
	var in_store := false
	## Content footprint in cells (width/height, each >= 1).
	var width := 1
	var height := 1
	## Item type verbatim (`b` building, `u` unit, `l` landscape); the
	## picker offers buildings only — units are a later deliver line.
	var type := ""
	## Derived once: width x height as the footprint vector.
	var footprint := Vector2i.ONE


## The whole parsed catalog, payload order preserved.
class Catalog:
	extends RefCounted
	## Every parsed item in payload order (900 in the committed payload).
	var entries: Array = []
	## Item count actually parsed.
	var items := 0


## Legacy cost keys onto resource names — identical to the endpoint's
## cost-vector mapping (design D4).
const COST_RESOURCES := {
	"g": "gold",
	"w": "wood",
	"o": "oil",
	"s": "steel",
	"c": "cash",
}
## The picker offers store-listed buildings only; units and landscapes
## belong to later deliver lines.
const STORE_TYPE := "b"
## Largest magnitude accepted for a transported integer (2^53, the exact
## integer range of an IEEE-754 double on the pinned JSON transport).
const MAX_INTEGER := 9007199254740992.0


## Parse a bootstrap config payload into a typed catalog. Returns
## `{ok, error, catalog}`; on failure `catalog` is null and `error` names
## the missing or invalid field. No I/O and no requests: the caller
## passes the payload already in hand (design D10).
static func parse(payload: Variant) -> Dictionary:
	if not (payload is Dictionary):
		return _reject("payload is not an object")
	var items: Variant = (payload as Dictionary).get("items")
	if not (items is Array):
		return _reject("field 'items' is missing or invalid")
	var catalog := Catalog.new()
	for index in range((items as Array).size()):
		var row: Variant = (items as Array)[index]
		if not (row is Dictionary):
			return _reject("item %d is not an object" % index)
		var entry_result := _parse_entry(row as Dictionary, index)
		if not bool(entry_result.get("ok", false)):
			return _reject(str(entry_result.get("error", "")))
		catalog.entries.append(entry_result["entry"])
	catalog.items = catalog.entries.size()
	return {"ok": true, "error": "", "catalog": catalog}


## The picker's entries for a loaded level: store-listed buildings whose
## `min_level` the level allows, payload order preserved (spec: "store-
## listed buildings gated by their `min_level` against the loaded level").
## An absent catalog yields no entries — never a fabricated one.
static func picker_entries(catalog: Variant, level: int) -> Array:
	var entries: Array = []
	if not (catalog is Catalog):
		return entries
	for entry: Variant in (catalog as Catalog).entries:
		if not (entry is Entry):
			continue
		var typed: Entry = entry
		if typed.in_store and typed.type == STORE_TYPE \
				and typed.min_level <= level:
			entries.append(typed)
	return entries


## Look up one parsed entry by id (null when absent — never guessed).
static func find_entry(catalog: Variant, item_id: int) -> Variant:
	if not (catalog is Catalog):
		return null
	for entry: Variant in (catalog as Catalog).entries:
		if entry is Entry and (entry as Entry).id == item_id:
			return entry
	return null


## One item row -> a typed entry, or a failure naming the offending
## field. The id parses first so every later message can name the item.
static func _parse_entry(row: Dictionary, index: int) -> Dictionary:
	var id: Variant = _strict_int(row.get("id"))
	if id == null:
		return {"ok": false,
			"error": "field 'id' of item %d is invalid" % index}
	var label := "item %d (id %d)" % [index, int(id)]
	var name: Variant = row.get("name")
	if not (name is String) or str(name).is_empty():
		return {"ok": false, "error": "field 'name' of %s is invalid" % label}
	var costs := _parse_costs(row.get("costs"))
	if not bool(costs.get("ok", false)):
		return {"ok": false, "error": "field 'costs' of %s: %s"
			% [label, str(costs.get("error", ""))]}
	var min_level: Variant = _strict_int(row.get("min_level"))
	if min_level == null:
		return {"ok": false,
			"error": "field 'min_level' of %s is invalid" % label}
	var in_store: Variant = _strict_bool(row.get("in_store"))
	if in_store == null:
		return {"ok": false,
			"error": "field 'in_store' of %s is invalid" % label}
	var width: Variant = _strict_int(row.get("width"))
	var height: Variant = _strict_int(row.get("height"))
	if width == null or int(width) < 1 \
			or height == null or int(height) < 1:
		return {"ok": false,
			"error": "field 'width'/'height' of %s is invalid" % label}
	var type: Variant = row.get("type")
	if not (type is String) or str(type).is_empty():
		return {"ok": false, "error": "field 'type' of %s is invalid" % label}
	var entry := Entry.new()
	entry.id = int(id)
	entry.name = str(name)
	entry.costs = costs["costs"]
	entry.min_level = int(min_level)
	entry.in_store = bool(in_store)
	entry.width = int(width)
	entry.height = int(height)
	entry.type = str(type)
	entry.footprint = Vector2i(entry.width, entry.height)
	return {"ok": true, "error": "", "entry": entry}


## Cost map -> `{ok, costs, error}` with resource names, mirroring the
## fake double's `_derive_costs` (and through it the endpoint): `null` or
## "" is a free item, a JSON string parses to an object, unknown keys and
## non-integer amounts fail closed.
static func _parse_costs(value: Variant) -> Dictionary:
	var source: Variant = value
	if source == null:
		return {"ok": true, "costs": {}, "error": ""}
	if source is String:
		if str(source).strip_edges().is_empty():
			return {"ok": true, "costs": {}, "error": ""}
		# The instance parse returns the error instead of printing an
		# engine error line on malformed text (the verify wrappers treat
		# any engine ERROR line as fatal); both paths fail closed alike.
		var json := JSON.new()
		if json.parse(str(source)) != OK:
			return {"ok": false, "costs": {},
				"error": "not valid JSON (%s)" % json.get_error_message()}
		source = json.get_data()
	if not (source is Dictionary):
		return {"ok": false, "costs": {}, "error": "not a cost object"}
	var costs := {}
	for key: Variant in source:
		var resource: Variant = COST_RESOURCES.get(str(key))
		if resource == null:
			return {"ok": false, "costs": {},
				"error": "unknown cost key '%s'" % str(key)}
		var amount: Variant = _strict_amount(source[key])
		if amount == null:
			return {"ok": false, "costs": {},
				"error": "amount of cost key '%s' is invalid" % str(key)}
		costs[str(resource)] = int(amount)
	return {"ok": true, "costs": costs, "error": ""}


## A cost amount exactly as the fake double and the endpoint accept one:
## an int or an integral float in the transported integer range (signed —
## the legacy cost vector applies negatives without rejecting them);
## anything else, including a numeric string, fails closed.
static func _strict_amount(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and absf(typed) <= MAX_INTEGER:
			return int(typed)
	return null


## A non-negative integer from an int, an integral float, or a digit-only
## string (the committed config stores ids and dimensions as strings);
## null for anything else — never a lossy or signed conversion.
static func _strict_int(value: Variant) -> Variant:
	if value is int:
		return value if int(value) >= 0 else null
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and typed >= 0.0 and typed <= MAX_INTEGER:
			return int(typed)
		return null
	if value is String:
		var text := str(value)
		if text.is_empty() or text.length() > 16:
			return null
		for character in text:
			if character < "0" or character > "9":
				return null
		return text.to_int()
	return null


## A store flag from "0"/"1" (the payload's string encoding) or 0/1;
## null for anything else — never a truthy guess.
static func _strict_bool(value: Variant) -> Variant:
	if value is String:
		if str(value) == "0":
			return false
		if str(value) == "1":
			return true
		return null
	if value is int:
		if int(value) == 0:
			return false
		if int(value) == 1:
			return true
		return null
	return null


## The house rejection envelope: names the invalid field, never produces
## a partial catalog.
static func _reject(message: String) -> Dictionary:
	return {"ok": false,
		"error": "[catalog] parse rejected: " + message,
		"catalog": null}
