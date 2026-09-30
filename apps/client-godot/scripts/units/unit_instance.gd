extends RefCounted
## Typed player-owned `UnitInstance` (OpenSpec `godot-unit-instances`
## "Unit instances are rows, not widened definitions" / "A garrisoned unit is
## a row nested in a row" / "Unit rows are classified by committed type",
## design D1-D3).
##
## ## A unit instance IS a legacy map row (established)
##
## The legacy save has **one** row shape, written by `engine.py:31` as
## `[item, x, y, timestamp, orientation, store, attr, player]`. A placed unit
## and a placed building are indistinguishable at the storage level; the only
## difference is the committed item `type` (`u` vs `b`). `push_unit`
## (`engine.py:54-57`) moves one row into another row's fifth slot, so a
## **garrisoned unit is a row nested inside another row** — a row within a row,
## which is why that slot is a list. `pop_unit` (`engine.py:58-68`) scans the
## same slot for a matching `item[0]` and pops it.
##
## ## The model wraps, it does not copy (design D1)
##
## An `Instance` **holds** its row and its resolved `UnitDefinition` and reads
## every value back out of them, so there is no second copy that could drift
## from the save. It exposes the row's own fields verbatim — cell coordinates,
## row instant, orientation, player team, and its `attr` bag — and reads its
## **identity from the definition**, never by restating it. Because the
## instance *has* a definition, nothing here can become definition state: the
## M8 line 1 static/instance boundary is structural, not conventional.
##
## Read-only by construction: there is **no** setter, **no** mutating method,
## and no writable public field on this class. The row and the definition are
## private and reachable only through readers; the `attr` bag is handed out as
## a deep copy so no reader can write back into the save the row came from.
##
## ## A non-unit row is rejected, never coerced (design D1/D3)
##
## The gate is the committed `type` on the **resolved definition**. A
## definition whose committed `type` is not `u` produces **no** instance, and
## the failure names the row's key and the committed type verbatim. The
## normalized `kind` field is a **normalization artifact** absent from the
## stored configuration (`config/main.json` items carry `type` and no `kind`),
## so it is never a gate here — it stays available on the definition as
## content.
##
## ## Nesting is bounded and fails closed (design D2)
##
## A save is untrusted input, and unbounded recursion over attacker-supplied
## nesting is a denial-of-service surface, so `MAX_GARRISON_DEPTH` is a named
## bound. Exceeding it is **refused** with an error naming the key, the slot
## path, and the depth — never silently truncated, because a truncated garrison
## is a wrong answer presented as a correct one. The legacy engine itself only
## ever nests one level (`push_unit` is called with a map row), so the committed
## corpus needs one; the bound leaves headroom for a legitimately nested
## garrison while keeping the recursion trivially bounded.
##
## ## An empty container is an empty garrison, not an absent one
##
## A fifth slot holding `[]` reads as a garrison with no members
## (`GARRISON_EMPTY`). A fifth slot that is **missing** or **malformed** is a
## different thing entirely: the row is refused, no instance is produced, and
## the failure names the key, the slot path, and what was found. There is no
## third state in which a bad container is read as an empty one.
##
## ## No gameplay semantics, and no queue or death rule (design D5-D7)
##
## Nothing on this class computes behaviour. There is deliberately **no**
## `damage()`, `can_defend()`, `speed()`, `lifetime()`, `attack_interval()`,
## `can_train()`, `has_resurrectable()`, `is_full()`, or `tick()` helper:
## `attack: 10` is a committed number in a definition, not a damage rule. The
## reserved production-queue `attr` keys and the dead-unit counter are
## **recorded** by `unit_instance_projection.gd` and are **not implemented**
## here — no increment, no decrement, no timestamp write, no queue projection,
## no corpse, and no resurrection predicate.

## The typed model whose resolved definition this instance wraps. Used as the
## parameter type, exactly as `unit_catalog.gd` types its registry dependency.
const UnitDefinition = preload("res://scripts/units/unit_definition.gd")

## The committed `type` that makes a row a unit. The legacy discriminator:
## the stored configuration carries `type` and no `kind` (design D3).
const TYPE_UNIT := "u"

## The number of slots a legacy map row has, and the only row length this
## model accepts. A row of any other length is refused, because a longer row
## would be an uncommitted shape and a shorter one has no fifth slot at all.
const ROW_SLOTS := 8

## The row's own slots, by index (established: `engine.py:31`).
const SLOT_ITEM := 0
const SLOT_CELL_X := 1
const SLOT_CELL_Y := 2
const SLOT_ROW_INSTANT := 3
const SLOT_ORIENTATION := 4
const SLOT_GARRISON := 5
const SLOT_ATTR := 6
const SLOT_PLAYER_TEAM := 7

## The two container states. There is deliberately no third: a missing or
## malformed container is a refusal, not a state.
const GARRISON_EMPTY := "empty"
const GARRISON_POPULATED := "populated"

## The named nesting bound (design D2). A placed row is depth 0, its garrison
## members are depth 1, and a member that would land deeper than this is
## refused rather than truncated.
const MAX_GARRISON_DEPTH := 4

## The established row contract, slot by slot, with the committed source lines
## that fix it. The evidence report reads this table rather than restating it,
## so a change here cannot leave the report describing a row shape the code no
## longer accepts.
const ROW_CONTRACT := [
	{"slot": SLOT_ITEM, "name": "item", "meaning":
		"the committed legacy item id, an integer",
		"source": "engine.py:31, map_add_item's row literal",
		"used_by": "the instance's identity is read from the resolved "
			+ "definition and cross-checked against this slot, never restated"},
	{"slot": SLOT_CELL_X, "name": "x", "meaning":
		"the row's cell x coordinate, an integer",
		"source": "engine.py:31",
		"used_by": "exposed verbatim as the instance's cell x"},
	{"slot": SLOT_CELL_Y, "name": "y", "meaning":
		"the row's cell y coordinate, an integer",
		"source": "engine.py:31",
		"used_by": "exposed verbatim as the instance's cell y"},
	{"slot": SLOT_ROW_INSTANT, "name": "timestamp", "meaning":
		"the row's own Unix-seconds instant, an integer",
		"source": "engine.py:31; re-stamped by push_unit at engine.py:56 "
			+ "when a row is moved into a garrison",
		"used_by": "exposed verbatim; no elapsed-time rule is computed "
			+ "from it, so no queue or garrison timer is implied"},
	{"slot": SLOT_ORIENTATION, "name": "orientation", "meaning":
		"the row's committed orientation code, an integer",
		"source": "engine.py:31",
		"used_by": "exposed verbatim; no rotation or facing rule is applied"},
	{"slot": SLOT_GARRISON, "name": "store", "meaning":
		"the garrison container: a LIST of nested ROWS, not a list of "
		+ "identifiers",
		"source": "engine.py:31 with the empty-list default at "
			+ "engine.py:11-12; push_unit appends a row at engine.py:55; "
			+ "pop_unit scans and pops a row at engine.py:61-67",
		"used_by": "each element is parsed as a UnitInstance in its own "
			+ "right, recursively, under MAX_GARRISON_DEPTH"},
	{"slot": SLOT_ATTR, "name": "attr", "meaning":
		"the row's attribute bag, an object",
		"source": "engine.py:31; the production-queue keys nu, ts, and ui "
			+ "live in this bag (engine.py:183-213)",
		"used_by": "read verbatim and handed out as a deep copy; the reserved "
			+ "queue keys are recorded by the projection, never written"},
	{"slot": SLOT_PLAYER_TEAM, "name": "player", "meaning":
		"the owning player id, an integer",
		"source": "engine.py:31; push_dead_unit requires item[7] == 1 at "
			+ "engine.py:151",
		"used_by": "exposed verbatim as the instance's player team; no "
			+ "ownership or death rule is evaluated from it"},
]

## One player-owned unit instance: a legacy map row plus the committed
## definition it resolves to.
##
## Read-only by construction — no setter, no mutating method, no writable
## public field. Every reader below returns the row's own committed value or a
## fresh copy, so reading an instance can change neither the save it was parsed
## from nor the definition it wraps.
class Instance extends RefCounted:
	## The row, **by reference** (design D1). Never copied, so an instance is a
	## view over the save rather than a restatement of it.
	var _row: Array = []
	## The resolved committed `UnitDefinition`, **by reference**. Held, never
	## copied and never widened.
	var _definition = null
	## The garrison members, in committed list order. Each is a nested
	## `Instance`, so a nested row is parsed as a unit instance in its own
	## right (design D2).
	var _garrison: Array = []
	## Which of the two container states this row's fifth slot is in.
	var _garrison_state := GARRISON_EMPTY
	## The map key this row is stored under, verbatim; "" for a row nested in a
	## garrison, which has no map key of its own.
	var _key := ""
	## The slot path this row was parsed from, e.g. `"5[0]"`; "" for a placed
	## row. It is what makes a refusal name the exact nested row.
	var _path := ""
	## Nesting depth: 0 for a placed row, 1 for its garrison members, and so
	## on, bounded by `MAX_GARRISON_DEPTH`.
	var _depth := 0

	## The instance's committed item id, read from the **definition** it wraps
	## and never restated from the row.
	func item_id() -> String:
		return str(_definition.legacy_id)

	## The row's own raw item-id slot, so a reader can compare it against
	## `item_id()`. The two were cross-checked when the instance was built.
	func row_item_id() -> int:
		return int(_row[SLOT_ITEM])

	## The committed definition this instance wraps.
	func definition() -> Variant:
		return _definition

	## The row's cell x coordinate, verbatim.
	func cell_x() -> int:
		return int(_row[SLOT_CELL_X])

	## The row's cell y coordinate, verbatim.
	func cell_y() -> int:
		return int(_row[SLOT_CELL_Y])

	## The row's own instant, verbatim. No elapsed-time rule is computed from
	## it, so reading it implies no queue or garrison timer.
	func row_instant() -> int:
		return int(_row[SLOT_ROW_INSTANT])

	## The row's committed orientation code, verbatim. No rotation or facing
	## rule is applied.
	func orientation() -> int:
		return int(_row[SLOT_ORIENTATION])

	## The row's owning player id, verbatim. No ownership or death rule is
	## evaluated from it.
	func player_team() -> int:
		return int(_row[SLOT_PLAYER_TEAM])

	## The row's attribute bag as a **deep copy**, so a reader can inspect the
	## committed keys and values — including the reserved production-queue
	## keys — without any possibility of writing back into the save.
	func attr_bag() -> Dictionary:
		return (_row[SLOT_ATTR] as Dictionary).duplicate(true)

	## The committed attribute-bag key names, sorted, so a reader gets a
	## deterministic list rather than the save's own insertion order.
	func attr_keys() -> Array:
		var out: Array = (_row[SLOT_ATTR] as Dictionary).keys()
		out.sort()
		return out

	## One committed attribute value, or `null` when the key is absent. An
	## absent key is **not** a committed zero: `null` is what tells the two
	## apart.
	func attr_value(key: Variant) -> Variant:
		var bag: Dictionary = _row[SLOT_ATTR]
		if not bag.has(key):
			return null
		var value: Variant = bag[key]
		return value.duplicate(true) if (value is Dictionary) else value

	## The committed definitions of this row's garrison, as a fresh list a
	## caller cannot append to. Each is a nested `Instance` in its own right.
	func garrison() -> Array:
		return _garrison.duplicate()

	## How many nested rows this row's fifth slot holds.
	func garrison_size() -> int:
		return _garrison.size()

	## `"empty"` or `"populated"`. A missing or malformed fifth slot is not a
	## state: that row was refused, and no instance exists to ask.
	func garrison_state() -> String:
		return _garrison_state

	## True when the fifth slot held an empty list. Distinct from a row whose
	## fifth slot was missing or malformed, which is refused outright.
	func garrison_is_empty() -> bool:
		return _garrison_state == GARRISON_EMPTY

	## Nesting depth: 0 for a placed row, 1 for a direct garrison member, and
	## so on.
	func depth() -> int:
		return _depth

	## The map key this row is stored under; "" for a nested row.
	func key() -> String:
		return _key

	## The slot path this row was parsed from; "" for a placed row.
	func path() -> String:
		return _path

	## The number of slots the wrapped row has. Always `ROW_SLOTS`: the build
	## refuses any other length, so a reader never sees a partial row.
	func row_size() -> int:
		return _row.size()

	## One committed slot of the wrapped row, verbatim. Read-only by
	## construction: the returned value is a scalar or a deep copy.
	func row_slot(index: int) -> Variant:
		if index < 0 or index >= _row.size():
			return null
		var value: Variant = _row[index]
		if (value is Dictionary) or (value is Array):
			return value.duplicate(true)
		return value

	## The instance's own committed state as one fresh record — the row's
	## fields verbatim plus the identity read from the definition and this
	## row's garrison summary. Everything here is derived from the row and the
	## definition; nothing is added to either.
	func fields() -> Dictionary:
		var members: Array = []
		for member: Variant in _garrison:
			members.append(str(member.item_id()))
		return {
			"key": _key,
			"path": _path,
			"depth": _depth,
			"item_id": item_id(),
			"row_item_id": row_item_id(),
			"cell_x": cell_x(),
			"cell_y": cell_y(),
			"row_instant": row_instant(),
			"orientation": orientation(),
			"player_team": player_team(),
			"attr": attr_bag(),
			"garrison_state": _garrison_state,
			"garrison_size": _garrison.size(),
			"garrison": members,
		}


## Builds one unit instance over one committed map row. Returns
##   `{ok: true, error: "", instance: <Instance>}`
## or
##   `{ok: false, error: "<message naming the key, the slot path, and the
##     committed type or slot>", instance: null}`
## — no partial instance, nothing guessed, defaulted, or coerced (design D1).
##
## `row` is one committed row of `maps[n].items`; `key` is the map key it is
## stored under and `path` is the slot path it was found at ("" for a placed
## row). `definition` is the row's already-resolved `UnitDefinition`; this
## module never resolves content itself, so the static/instance boundary stays
## one-way. `resolve_nested(item_id_text) -> Dictionary` is the caller's
## resolver for a garrisoned row's committed unit definition, returning
## `{ok, error, definition}` — the projection supplies it from the content
## registry. `depth` is 0 for a placed row and 1 or more for a row nested in a
## garrison.
static func build(key: Variant, path: String, row: Variant, definition: Variant,
		resolve_nested: Callable, depth: int) -> Dictionary:
	var row_key := str(key)
	if int(depth) > MAX_GARRISON_DEPTH:
		return _reject("garrison row of map key '%s' at slot path '%s' is "
			% [row_key, path] + "nested at depth %d, beyond the named maximum "
			% int(depth) + "of %d: refused rather than truncated"
			% MAX_GARRISON_DEPTH)
	var valid := validate_row(row, row_key, path)
	if not bool(valid.get("ok", false)):
		return _reject(str(valid.get("error", "")))
	var required := _require_unit_definition(definition)
	if not bool(required.get("ok", false)):
		return _reject("%s %s" % [_slot_label(row_key, path),
			str(required.get("error", ""))])
	if not resolve_nested.is_valid():
		return _reject("%s cannot be parsed: no usable garrison resolver was "
			% _slot_label(row_key, path) + "supplied for its nested rows")
	var typed: Variant = required["definition"]
	# Identity is cross-checked against the row, never restated from it: a
	# definition that is not the row's own item is refused.
	if str(typed.legacy_id) != str(int((row as Array)[SLOT_ITEM])):
		return _reject("%s carries item %d but its resolved definition is unit "
			% [_slot_label(row_key, path), int((row as Array)[SLOT_ITEM])]
			+ "%s: refused rather than coerced" % str(typed.legacy_id))
	var garrison := parse_garrison(row_key, _container_path(path),
		(row as Array)[SLOT_GARRISON], resolve_nested, int(depth) + 1)
	if not bool(garrison.get("ok", false)):
		return _reject(str(garrison.get("error", "")))
	var instance := Instance.new()
	instance._row = row
	instance._definition = typed
	instance._garrison = garrison["members"]
	instance._garrison_state = str(garrison["state"])
	instance._key = row_key
	instance._path = path
	instance._depth = int(depth)
	return {"ok": true, "error": "", "instance": instance}


## Parses a garrison container — a placed row's fifth slot — into nested unit
## instances. Returns
##   `{ok: true, error: "", members: Array, state: "empty"|"populated"}`
## or
##   `{ok: false, error: "<message naming the key, the slot path, and the
##     member>", members: [], state: ""}`
##
## Each element is a nested **row**, parsed as a `UnitInstance` in its own
## right (design D2), recursively. An empty list is `GARRISON_EMPTY`; a
## container that is not a list is refused, so a malformed container is never
## read as an empty garrison. `member_depth` is the depth the members occupy.
static func parse_garrison(key: Variant, path: String, container: Variant,
		resolve_nested: Callable, member_depth: int) -> Dictionary:
	var row_key := str(key)
	if not (container is Array):
		return _garrison_reject("garrison container of map key '%s' at slot "
			% row_key + "path '%s' is not a list of rows (found %s)"
			% [path, _type_name(container)])
	var members: Array = []
	var index := 0
	for element: Variant in container as Array:
		var child_path := "%s[%d]" % [path, index]
		index += 1
		if not (element is Array):
			return _garrison_reject("garrison member at slot path '%s' of map "
				% child_path + "key '%s' is not a row (found %s)"
				% [row_key, _type_name(element)])
		if (element as Array).size() != ROW_SLOTS:
			return _garrison_reject("garrison member at slot path '%s' of map "
				% child_path + "key '%s' has %d slots, not the committed %d"
				% [row_key, (element as Array).size(), ROW_SLOTS])
		var resolved: Variant = resolve_nested.call(
			str(int((element as Array)[SLOT_ITEM])))
		if not (resolved is Dictionary):
			return _garrison_reject("garrison member at slot path '%s' of map "
				% child_path + "key '%s' could not be resolved" % row_key)
		if not bool((resolved as Dictionary).get("ok", false)):
			return _garrison_reject("garrison member at slot path '%s' of map "
				% child_path + "key '%s' is refused: %s"
				% [row_key, str((resolved as Dictionary).get("error", ""))])
		var built := build(row_key, child_path, element,
			(resolved as Dictionary).get("definition"), resolve_nested,
			int(member_depth))
		if not bool(built.get("ok", false)):
			return _garrison_reject(str(built.get("error", "")))
		members.append(built["instance"])
	return {"ok": true, "error": "", "members": members,
		"state": GARRISON_EMPTY if members.is_empty() else GARRISON_POPULATED}


## Validates one committed map row's shape, independently of its content. This
## is the **row contract** gate, shared by the instance build and by the
## projection's building classification: returns
##   `{ok: true, error: ""}`
## or
##   `{ok: false, error: "<message naming the key, the slot path, and the
##     slot>"}`
##
## Every slot is checked, so no malformed slot is silently read as its declared
## default: the item id and the five other integer slots must be integers, the
## container must be a list, and the attribute bag must be an object. The
## pinned engine's JSON parser represents every committed number as a float, so
## an integer slot accepts an `int` or an integral `float` — the same documented
## transport tolerance the delivered building and unit catalogs apply to the
## same field class. A numeric **string** is refused: no committed source stores
## one.
static func validate_row(row: Variant, key: Variant, path: String) -> Dictionary:
	var row_key := str(key)
	if not (row is Array):
		return _slot_error(row_key, path, "is not a row (found %s)"
			% _type_name(row))
	if (row as Array).size() != ROW_SLOTS:
		return _slot_error(row_key, path, "has %d slots, not the committed %d"
			% [(row as Array).size(), ROW_SLOTS])
	for slot: int in [SLOT_ITEM, SLOT_CELL_X, SLOT_CELL_Y, SLOT_ROW_INSTANT,
			SLOT_ORIENTATION, SLOT_PLAYER_TEAM]:
		if _integer((row as Array)[slot]) == null:
			return _slot_error(row_key, path,
				"has a non-integer slot %d (found %s)"
				% [slot, _type_name((row as Array)[slot])])
	if not ((row as Array)[SLOT_GARRISON] is Array):
		return _slot_error(row_key, path,
			"has a garrison container of type %s, not a list of rows"
			% _type_name((row as Array)[SLOT_GARRISON]))
	if not ((row as Array)[SLOT_ATTR] is Dictionary):
		return _slot_error(row_key, path,
			"has an attribute bag of type %s, not an object"
			% _type_name((row as Array)[SLOT_ATTR]))
	return {"ok": true, "error": ""}


## The established row contract, slot by slot, with the committed source lines
## that fix it — as a fresh deep copy a caller may keep and mutate.
static func row_contract() -> Array:
	return (ROW_CONTRACT as Array).duplicate(true)


# ---------------------------------------------------------------------------
# Internals — every one fails closed and names the key and the slot
# ---------------------------------------------------------------------------


## A resolved definition this model will accept: a parsed `UnitDefinition`
## whose committed `type` is `u`. Anything else is refused **with the committed
## type named**, so a building row is never coerced into an instance
## (design D1/D3).
static func _require_unit_definition(definition: Variant) -> Dictionary:
	if definition == null:
		return {"ok": false, "error": "resolved no definition at all"}
	if not (definition is UnitDefinition.Definition):
		return {"ok": false, "error": "the resolved definition is not a parsed "
			+ "UnitDefinition (found %s)" % _type_name(definition)}
	if str(definition.type) != TYPE_UNIT:
		return {"ok": false, "error": "the resolved definition's committed type "
			+ "is '%s', not the unit type '%s'"
			% [str(definition.type), TYPE_UNIT]}
	return {"ok": true, "error": "", "definition": definition}


static func _reject(message: String) -> Dictionary:
	return {"ok": false, "error": "[unit-instance] parse rejected: " + message,
		"instance": null}


static func _slot_error(key: String, path: String, detail: String) -> Dictionary:
	return _reject("%s %s" % [_slot_label(key, path), detail])


static func _garrison_reject(message: String) -> Dictionary:
	return {"ok": false, "error": "[unit-instance] parse rejected: " + message,
		"members": [], "state": ""}


## A refusal's location: the map key, and the slot path within it ("" for a
## placed row).
static func _slot_label(key: String, path: String) -> String:
	return "map key '%s' at slot path '%s'" % [key,
		"placed row" if path.is_empty() else path]


## The slot path of a row's own fifth slot, so a nested row's container is
## addressed relative to where the nested row itself was found.
static func _container_path(path: String) -> String:
	if path.is_empty():
		return str(SLOT_GARRISON)
	return "%s/%d" % [path, SLOT_GARRISON]


## A committed integer: an `int` or an integral `float` inside the transported
## exact-integer range. A numeric string fails closed, because coercing `"10"`
## to ten would invent a value the committed row does not carry.
static func _integer(value: Variant) -> Variant:
	if value is int:
		return int(value)
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number) \
				and absf(number) <= 9007199254740992.0:
			return int(number)
	return null


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
		_:
			return "unsupported"
