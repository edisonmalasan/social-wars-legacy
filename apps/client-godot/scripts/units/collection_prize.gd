extends RefCounted
## Read-only projection of the committed collection prize (OpenSpec
## `godot-unit-collection` "A collection prize is derived from committed
## content" / "The index is one-based, and the id-0/id-1 alias is reported",
## design D1, D3).
##
## ## What this module is
##
## One function, `resolve()`, plus the recorded contracts around it.  It answers
## a single question: **what does the legacy server grant when a collection id is
## completed?**  The answer is the committed `collections` table's own row, read
## through the **one-based** index the legacy lookup uses, with every granted id
## classified as a **unit** or a **building** by resolving it against the
## content registry.  It is **read-only**: nothing here writes, mutates, or
## persists, and the module holds no node, no clock, no request, and no
## transport.
##
## ## The registry is a PARAMETER, never reached behind the caller's back
##
## Every committed number arrives as an argument, exactly as `queue_flow.gd` and
## `production_flow.gd` take a save bag.  A caller passes a `resolve` callable
## `(domain, legacy_id) -> {found, error, entry}`; this module never preloads
## `ContentRegistry` itself, so the hermetic suite, the town view, and the
## deterministic report all consume the SAME functions over the SAME registry.
##
## ## The index is one-based, and the alias is reported, not hidden (D3)
##
## The legacy lookup is `index = max(0, collection - 1)` followed by
## `collections[index]`.  So:
##
## * the id is **one-based** — `collection - 1` is the array position — which is
##   recorded as **derived-provisional** with the rejected **zero-based**
##   alternative retained in :data:`REJECTED_ALTERNATIVE`;
## * the clamp is an **alias**: every id **below** 1 (id `0` and every negative
##   id) resolves to index `0` and therefore to the **same committed prize as id
##   1**.  :func:`resolve` reports `clamped` and `aliased` plus `alias_of`, and
##   it **never** presents an aliased id as a distinct collection.  Collection id
##   `1` itself is the boundary: `1 - 1 == 0` is already its own index, so it is
##   **not** clamped.
##
## The one-based reading is corroborated by the stored content rather than merely
## plausible: the committed `collections` table carries its own native `id`
## column running `"1".."10"` over ten **array positions** `0..9`, so
## `collection - 1` maps that native id onto exactly its own position.  The
## zero-based alternative would leave the last committed collection (id `"10"`,
## Animal Collection, the only one granting a mounted unit) unreachable from any
## id a client can name.
##
## ## An out-of-table id is REPORTED, never substituted (D1)
##
## `resolve()` returns `resolved: false` with the **recorded id intact** and an
## empty prize.  There is deliberately no default prize, no clamping to the last
## row, and no dropped id: substituting one would present a grant the committed
## table does not describe.
##
## ## Values are reported verbatim
##
## The committed row's own `name`, its own native `id` column, and its `prize`
## bag with its **committed string keys** are reported exactly as stored — no
## scaling, rounding, defaulting, or reordering.  The bag's keys are strings
## because that is the form `map["store"]` is keyed by, and a caller comparing a
## grant must compare those keys.
##
## ## Classification is content resolution, not a guess (D1)
##
## Each granted id is resolved against the registry's `units` domain first and
## its `buildings` domain second, and the committed `type` field decides the
## label.  An id that resolves to **neither** domain is reported as
## `unclassified` with its value intact — never defaulted to a building because
## most things are.  The two domains are disjoint by construction in the
## committed package, so a buildable-by-accident situation cannot arise; the
## order is still fixed and documented so the answer cannot depend on iteration.

## The content domain the committed collection rows live in, named by the
## normalized output's file basename because that is how `ContentRegistry` names
## a domain.
const DOMAIN := "collections"

## The two domains a granted id is resolved against, in the **fixed** order they
## are tried.  Every committed prize id resolves in exactly one of them.
const UNIT_DOMAIN := "units"
const BUILDING_DOMAIN := "buildings"

## The committed type letter each domain records.  A unit row is identified by
## its committed `type`, never by an id range — the same rule the unit-instances
## and unit-production lines apply.
const TYPE_UNIT := "u"
const TYPE_BUILDING := "b"

## The three ways a granted id can be reported.
const CLASS_UNIT := "unit"
const CLASS_BUILDING := "building"
const CLASS_UNCLASSIFIED := "unclassified"
const CLASSIFICATIONS := [CLASS_UNIT, CLASS_BUILDING, CLASS_UNCLASSIFIED]

## The closed count of committed collections, measured from the verified
## registry rather than asserted from prose.
const COMMITTED_COLLECTION_COUNT := 10

## The measured unit-granting / building-granting split of the committed table.
const COMMITTED_UNIT_COLLECTIONS := 6
const COMMITTED_BUILDING_COLLECTIONS := 4
## The distinct item ids the ten committed prize bags hold between them (each
## collection grants exactly one item, so ten bags hold ten ids).
const COMMITTED_DISTINCT_PRIZE_IDS := 10

## The first collection id the one-based reading names, and the last one the
## committed table resolves.
const FIRST_COLLECTION_ID := 1
const LAST_COLLECTION_ID := COMMITTED_COLLECTION_COUNT

## The index is 1-based, derived-provisional, with the zero-based alternative
## retained.
const INDEX_BASE := "one-based"
const DERIVATION_STATUS := "derived-provisional"
const REJECTED_ALTERNATIVE := "zero-based"

## The recorded index rule, in the wording the report and the endpoint share.
const INDEX_RULE := ("THE COLLECTION ID SPACE IS 1-BASED AND THE LOOKUP IS "
	+ "POSITIONAL. The legacy lookup computes `index = max(0, collection - 1)` "
	+ "against the loaded configuration's `collections` LIST and returns "
	+ "`json.loads(collections[index]['prize'])`, so the id a client names is one "
	+ "greater than the array position it selects. The 1-based reading is "
	+ "DERIVED-PROVISIONAL and is corroborated by the stored content rather than "
	+ "merely plausible: the committed table carries its own native `id` column "
	+ "running \"1\"..\"10\" over the ten ARRAY POSITIONS 0..9, so `collection - "
	+ "1` maps that native id onto exactly its own position. Nothing here is "
	+ "observed from the Flash client")

const REJECTED_ALTERNATIVE_NOTE := ("REJECTED: a 0-BASED id space, in which the "
	+ "id would BE the array position. It is rejected because it leaves the "
	+ "committed table unreachable: under 0-based indexing the largest namable id "
	+ "would select the second-to-last row and the last committed collection "
	+ "(id '10' / Animal Collection, the only one granting a mounted unit) would "
	+ "need id 10 to reach. The retained alternative is kept visible so a later "
	+ "reader can re-derive the choice rather than inherit it")

## The clamp, reported as what it is rather than absorbed.
const ALIAS_RULE := ("THE CLAMP IS AN ALIAS, REPORTED NOT HIDDEN. "
	+ "`max(0, collection - 1)` clamps BELOW the requested index, so EVERY "
	+ "collection id below 1 - id 0 and every negative id - resolves to index 0 "
	+ "and therefore to the SAME committed prize as id 1. In particular COLLECTION "
	+ "ID 0 AND COLLECTION ID 1 RESOLVE TO THE SAME PRIZE, and this projection "
	+ "never presents id 0 as a distinct collection. Collection id 1 is the "
	+ "boundary and is NOT clamped, because 1 - 1 is already the index its own "
	+ "committed row sits at. The alias is a recorded legacy-contract fact, NOT "
	+ "permission to widen the route: the grant contents stay content-derived, "
	+ "because an aliased id selects a genuine committed row rather than "
	+ "manufacturing one")

## The reason strings this projection can produce.  There is exactly one, and it
## is a **report**, not an error: an id outside the committed table is a fact the
## caller must be told about, not a fault.
const REASON_UNKNOWN_COLLECTION_ID := "unknown_collection_id"
const REASON_INVALID_COLLECTION_ID := "invalid_collection_id"

## The name an unresolvable collection reads as in the readout — a **named
## absence**, never a substituted collection.
const UNRESOLVABLE_TEXT := "[no committed collection]"

## The name an unclassifiable granted item reads as — also a named absence, never
## a guessed unit or building.
const UNCLASSIFIED_TEXT := "[unclassified item]"


# ---------------------------------------------------------------------------
# The one projection
# ---------------------------------------------------------------------------


## The **whole** prize projection for one collection id, and the ONLY entry point
## a surface uses. Returns
## `{ok, reason, error, resolved, collection_id, requested_index, index,
##   clamped, aliased, alias_of, name, id_column, prize, entries, item_count,
##   quantity_total, unit_count, building_count, unclassified_count, index_base,
##   derivation_status, rejected_alternative}`.
##
## `registry_row` is a callable `(domain: String, legacy_id: String) -> Dictionary`
## returning `{found: bool, error: String, entry: Dictionary}`, exactly the shape
## `ContentRegistry.get_entry` produces.  `registry_ids` is a callable
## `(domain: String) -> Dictionary` returning
## `{found: bool, error: String, ids: Array, file: String}`, exactly the shape
## `ContentRegistry.legacy_ids` produces.  Both are **parameters**, never
## preloads, so the same function serves the town view, the hermetic suite, and
## the deterministic report.
##
## Every committed value is reported **verbatim**: the row's own `name`, its own
## native `id` column, and its `prize` bag with its committed string keys.  An
## id outside the committed table comes back `resolved: false` with the recorded
## value **intact** and nothing substituted (D1).
static func resolve(collection_id: Variant,
		registry_row: Variant, registry_ids: Variant) -> Dictionary:
	if typeof(collection_id) != TYPE_INT or typeof(collection_id) == TYPE_BOOL:
		return _reject(collection_id, REASON_INVALID_COLLECTION_ID,
			"collection_id must be an integer, got %s"
				% _type_name(collection_id))
	var id_value := int(collection_id)
	# The committed table is enumerated positionally, because the lookup itself is
	# positional: an id does not select a row by key, it selects one by position.
	var table := _committed_table(registry_row, registry_ids)
	if table.is_empty():
		return _reject(id_value, REASON_UNKNOWN_COLLECTION_ID,
			"the content registry carries no '%s' domain, or it enumerates no "
				% DOMAIN + "committed collection")
	var requested := id_value - 1
	var index := maxi(0, requested)
	var clamped := index != requested
	var row: Variant = table[index] if index < table.size() else null
	if not (row is Dictionary):
		return {
			"ok": false,
			"reason": REASON_UNKNOWN_COLLECTION_ID,
			"error": "collection_id %d resolves to index %d, outside the %d-entry "
				% [id_value, index, table.size()]
				+ "committed collections table",
			"resolved": false,
			"collection_id": id_value,
			"requested_index": requested,
			"index": index,
			"clamped": clamped,
			"aliased": clamped,
			"alias_of": FIRST_COLLECTION_ID if clamped else -1,
			"name": "",
			"id_column": "",
			"prize": {},
			"entries": [],
			"item_count": 0,
			"quantity_total": 0,
			"unit_count": 0,
			"building_count": 0,
			"unclassified_count": 0,
			"index_base": INDEX_BASE,
			"derivation_status": DERIVATION_STATUS,
			"rejected_alternative": REJECTED_ALTERNATIVE,
		}
	var body: Dictionary = row
	var bag := _prize_bag(body.get("prize"))
	if bag.is_empty():
		return _reject(id_value, REASON_UNKNOWN_COLLECTION_ID,
			"the committed collection %d carries no readable prize bag" % id_value)
	var entries_out: Array = []
	var units := 0
	var buildings := 0
	var unclassified := 0
	var bag_out := {}
	for key: Variant in _sorted_keys(bag):
		var item_id := str(key)
		var quantity: Variant = bag[key]
		var resolution := _classify(item_id, registry_row)
		match str(resolution["classification"]):
			CLASS_UNIT:
				units += 1
			CLASS_BUILDING:
				buildings += 1
			_:
				unclassified += 1
		entries_out.append({
			"item_id": item_id,
			"quantity": quantity,
			"classification": str(resolution["classification"]),
			"name": str(resolution["name"]),
			"type": str(resolution["type"]),
			"domain": str(resolution["domain"]),
		})
		bag_out[item_id] = quantity
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"resolved": true,
		"collection_id": id_value,
		"requested_index": requested,
		"index": index,
		"clamped": clamped,
		"aliased": clamped,
		"alias_of": FIRST_COLLECTION_ID if clamped else -1,
		"name": str(body.get("name", "")),
		"id_column": _column_text(body.get("id", "")),
		"prize": bag_out,
		"entries": entries_out,
		"item_count": entries_out.size(),
		"quantity_total": _sum(bag_out),
		"unit_count": units,
		"building_count": buildings,
		"unclassified_count": unclassified,
		"index_base": INDEX_BASE,
		"derivation_status": DERIVATION_STATUS,
		"rejected_alternative": REJECTED_ALTERNATIVE,
	}


## Whether the legacy clamp actually moves this id's index: true exactly when
## `collection - 1` is **not** a non-negative index, i.e. for every id below 1.
## Collection id 1 is the boundary and is **not** clamped. This is the
## machine-readable form of :data:`ALIAS_RULE`.
static func is_aliased(collection_id: Variant) -> bool:
	if typeof(collection_id) != TYPE_INT or typeof(collection_id) == TYPE_BOOL:
		return false
	return int(collection_id) < FIRST_COLLECTION_ID


## The id a clamped id resolves to, or ``-1`` when the id is not clamped.  Every
## id below the clamp floor resolves to index 0, which is the row named by
## collection id 1.
static func alias_of(collection_id: Variant) -> int:
	return FIRST_COLLECTION_ID if is_aliased(collection_id) else -1


## The index one collection id selects, or ``-1`` for a non-integer id.  The
## arithmetic is the legacy expression itself, so a reader can check it against
## `get_collection_prize` line by line.
static func index_for(collection_id: Variant) -> int:
	if typeof(collection_id) != TYPE_INT or typeof(collection_id) == TYPE_BOOL:
		return -1
	return maxi(0, int(collection_id) - 1)


## Every committed collection, as a fresh deep copy in the registry's own
## committed order — so a report reads the table rather than restating it.
static func committed_table(registry_row: Variant,
		registry_ids: Variant) -> Array:
	return _committed_table(registry_row, registry_ids)


## The closed classification vocabulary, as a fresh array.
static func classification_vocabulary() -> Array:
	return (CLASSIFICATIONS as Array).duplicate()


## The six committed collections that grant a **unit**, as the registry's own
## entry order reports them: `[{collection_id, name, item_id, item_name}, ...]`.
## The count is a **measurement** of the committed table, so a content change
## that moved a prize between domains would show up here rather than being
## papered over by a pinned number.
static func unit_collections(registry_row: Variant,
		registry_ids: Variant) -> Array:
	return _collections_with_class(registry_row, registry_ids, CLASS_UNIT)


## The four committed collections that grant a **building**, in the same shape.
static func building_collections(registry_row: Variant,
		registry_ids: Variant) -> Array:
	return _collections_with_class(registry_row, registry_ids, CLASS_BUILDING)


## The index resolution as the evidence report records it: the one-based rule,
## the retained alternative, the alias, and the two boundary ids — read from this
## module's own constants so the report cannot describe a contract the code does
## not hold.
static func index_record() -> Dictionary:
	return {
		"base": INDEX_BASE,
		"derivation_status": DERIVATION_STATUS,
		"rejected_alternative": REJECTED_ALTERNATIVE,
		"rejected_alternative_note": REJECTED_ALTERNATIVE_NOTE,
		"rule": INDEX_RULE,
		"alias_rule": ALIAS_RULE,
		"alias_boundary": FIRST_COLLECTION_ID,
		"first_collection_id": FIRST_COLLECTION_ID,
		"last_collection_id": LAST_COLLECTION_ID,
		"clamp_expression": "max(0, collection - 1)",
		"zero_and_one_alias": true,
		"negative_ids_alias_too": true,
	}


## How the readout renders the index resolution for one projection, so a reader
## is never left to infer whether the id they named was clamped.
static func index_note(projection: Dictionary) -> String:
	if not bool(projection.get("resolved", false)):
		return "index: unresolved (%s)" % str(projection.get("reason", ""))
	if bool(projection.get("aliased", false)):
		return ("index: %d resolved through the one-based index to %d — CLAMPED, "
				% [int(projection.get("collection_id", 0)),
					int(projection.get("index", 0))]
				+ "so this id grants exactly what collection id %d grants"
					% int(projection.get("alias_of", 1)))
	return ("index: %d resolved through the one-based index to %d"
		% [int(projection.get("collection_id", 0)),
			int(projection.get("index", 0))])


## How the readout renders one committed prize entry: the id, the committed
## quantity, the classification, and the committed name when there is one.
static func entry_note(entry: Dictionary) -> String:
	var label := str(entry.get("classification", CLASS_UNCLASSIFIED))
	var text := "grants %s x%s (%s" % [str(entry.get("item_id", "")),
		str(entry.get("quantity", 0)), label]
	var name := str(entry.get("name", ""))
	if name == "":
		return text + " " + UNCLASSIFIED_TEXT + ")"
	return text + ", " + name + ")"


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural or unresolvable rejection with **every** field present, so a
## caller can never read a half-built verdict.
static func _reject(collection_id: Variant, reason: String,
		message: String) -> Dictionary:
	return {
		"ok": false,
		"reason": reason,
		"error": "[collection] %s: %s" % [reason, message],
		"resolved": false,
		"collection_id": collection_id,
		"requested_index": -1,
		"index": -1,
		"clamped": false,
		"aliased": false,
		"alias_of": -1,
		"name": "",
		"id_column": "",
		"prize": {},
		"entries": [],
		"item_count": 0,
		"quantity_total": 0,
		"unit_count": 0,
		"building_count": 0,
		"unclassified_count": 0,
		"index_base": INDEX_BASE,
		"derivation_status": DERIVATION_STATUS,
		"rejected_alternative": REJECTED_ALTERNATIVE,
	}


## The committed `collections` rows, in the registry's own committed order.
## Enumeration goes through the registry's PUBLIC `legacy_ids(domain)` accessor,
## so every row crosses the same byte-count and digest gate as every other read.
## An unreadable enumeration, or one that resolves nothing, is an **empty** list:
## `resolve()` then reports every id as unresolvable, which is a fact rather than
## a crash.
static func _committed_table(registry_row: Variant,
		registry_ids: Variant) -> Array:
	if typeof(registry_row) != TYPE_CALLABLE:
		return []
	if typeof(registry_ids) != TYPE_CALLABLE:
		return []
	var enumerated: Variant = registry_ids.call(DOMAIN)
	if not (enumerated is Dictionary) or not bool(enumerated.get("found", false)):
		return []
	var ids: Variant = enumerated.get("ids", [])
	if not (ids is Array):
		return []
	var table: Array = []
	for legacy_id: Variant in ids as Array:
		var resolved: Variant = registry_row.call(DOMAIN, str(legacy_id))
		if resolved is Dictionary and bool((resolved as Dictionary).get(
				"found", false)):
			var entry: Variant = (resolved as Dictionary).get("entry", null)
			if entry is Dictionary:
				table.append(entry)
	return table


## The committed `prize` bag as `{item id text: quantity}`.  The committed rows
## in this package carry an already-parsed object; a JSON-encoded string is
## accepted too, so the projection is usable against either representation.
## Quantities must be **integers**: a float or a string would make "the granted
## quantity equals the committed quantity" a comparison against a coerced number.
static func _prize_bag(raw: Variant) -> Dictionary:
	var parsed: Variant = raw
	if parsed is String:
		var json := JSON.new()
		if json.parse(str(parsed)) != OK or not (json.data is Dictionary):
			return {}
		parsed = json.data
	if not (parsed is Dictionary):
		return {}
	var bag := {}
	for key: Variant in (parsed as Dictionary).keys():
		var quantity: Variant = _whole_number((parsed as Dictionary)[key])
		if quantity == null:
			# A non-integral or non-numeric quantity is dropped rather than
			# coerced: "the granted quantity equals the committed quantity" would
			# otherwise be a comparison against a rounded number.
			continue
		bag[str(key)] = int(quantity)
	return bag


## The exact integer a committed number denotes, or ``null`` when it is not a
## whole number. The pinned engine's JSON parser widens every committed number to
## a float, so an integral float is the *same* committed value and is accepted;
## a bool, a string, or a fractional number is not a quantity at all.
static func _whole_number(value: Variant) -> Variant:
	if typeof(value) == TYPE_INT:
		return value
	if typeof(value) == TYPE_FLOAT:
		var number := float(value)
		return int(number) if number == floor(number) else null
	return null


## One committed row's native id column as its decimal form.  The pinned
## engine's JSON parser widens every committed number to a float, so the
## unmodified value would report the committed "1" as "1.0".  A whole
## number is rendered as its integer and anything else verbatim, never
## guessed into a shape the committed row does not have.
static func _column_text(value: Variant) -> String:
	var whole: Variant = _whole_number(value)
	if whole != null:
		return str(int(whole))
	return str(value)


## One granted id's classification, by resolving it against the content package.
## The **committed `type`** decides, never an id range: the two domains are
## disjoint, and a range test would break the moment a building id fell inside a
## unit id's numeric span.
static func _classify(item_id: String, registry_row: Variant) -> Dictionary:
	for domain: String in [UNIT_DOMAIN, BUILDING_DOMAIN]:
		var resolved: Variant = registry_row.call(domain, item_id)
		if not (resolved is Dictionary):
			continue
		if not bool((resolved as Dictionary).get("found", false)):
			continue
		var entry: Variant = (resolved as Dictionary).get("entry", null)
		if not (entry is Dictionary):
			continue
		var body: Dictionary = entry
		var committed_type := str(body.get("type", ""))
		var label := CLASS_UNCLASSIFIED
		if committed_type == TYPE_UNIT:
			label = CLASS_UNIT
		elif committed_type == TYPE_BUILDING:
			label = CLASS_BUILDING
		return {
			"classification": label,
			"domain": domain,
			"type": committed_type,
			"name": str(body.get("name", "")),
		}
	# Neither domain carries it: a named absence, never a guess.
	return {
		"classification": CLASS_UNCLASSIFIED,
		"domain": "",
		"type": "",
		"name": "",
	}


## The committed bag's keys in a deterministic order: **numerically** where every
## key is a digit string, so "45" sorts before "1062" the way the numbers do
## rather than the way the strings do.  Mixed or non-numeric keys sort after,
## lexicographically, so the order is total either way.
static func _sorted_keys(bag: Dictionary) -> Array:
	var keys: Array = bag.keys()
	var numeric := true
	for key: Variant in keys:
		if not str(key).is_valid_int():
			numeric = false
			break
	if numeric:
		keys.sort_custom(func(a: Variant, b: Variant) -> bool:
			return int(a) < int(b))
	else:
		keys.sort()
	return keys


## The bag's total quantity, or 0 for an empty bag.
static func _sum(bag: Dictionary) -> int:
	var total := 0
	for key: Variant in bag.keys():
		total += int(bag[key])
	return total


## The committed collections whose committed prize classifies as `wanted`, in
## the registry's own committed order.
static func _collections_with_class(registry_row: Variant,
		registry_ids: Variant, wanted: String) -> Array:
	var out: Array = []
	var table := _committed_table(registry_row, registry_ids)
	for position in table.size():
		var row: Dictionary = table[position]
		var bag := _prize_bag(row.get("prize"))
		for key: Variant in _sorted_keys(bag):
			var resolution := _classify(str(key), registry_row)
			if str(resolution["classification"]) != wanted:
				continue
			out.append({
				"collection_id": position + 1,
				"name": str(row.get("name", "")),
				"item_id": str(key),
				"quantity": int(bag[key]),
				"item_name": str(resolution["name"]),
			})
	return out


## The observed type of a refused value, so a failure names what it found
## instead of saying only "invalid".
static func _type_name(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "bool"
		TYPE_INT:
			return "int"
		TYPE_FLOAT:
			return "float"
		TYPE_STRING:
			return "string"
		TYPE_ARRAY:
			return "array"
		TYPE_DICTIONARY:
			return "object"
		TYPE_CALLABLE:
			return "callable"
		_:
			return "unsupported"