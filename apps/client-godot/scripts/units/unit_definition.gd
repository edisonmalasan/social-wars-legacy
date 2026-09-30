extends RefCounted
## Typed static `UnitDefinition` (OpenSpec `godot-unit-definitions`
## "Static unit definitions" / "Typed definition fields with no gameplay
## semantics" / "Fail-closed parsing", design D1-D5).
##
## One definition is committed, read-only CONTENT. It carries **no player
## state**: no placement key, no coordinates, no owner, no current health, no
## garrison, no queue position — so a future `UnitInstance` cannot be smuggled
## in by widening a definition (design D2). Resolution goes only through
## `ContentRegistry.get_entry("units", legacy_id)`, whose manifest byte-count and
## SHA-256 verification and duplicate-legacy-ID rejection stay the single gate
## (design D1).
##
## ## Fields are parsed verbatim and carry NO gameplay semantics (design D3)
##
## The five named groups below hold the committed values **exactly**: no
## scaling, no rounding, no defaulting, no coercion. The statistics —
## `attack`, `defense`, `life`, `attack_interval`, `attack_range`, `velocity`,
## `expiration`, `best_against`, `best_against_mult` — are **numbers in a
## definition, not rules**. `attack: 10` is the committed value of one field of
## one committed row; it is **not** a damage rule, **not** an attack rate,
## **not** a hit count, and **nothing here computes damage, a defence outcome,
## a speed, a lifetime, or an attack timing from it**. There is deliberately
## **no** `damage()`, `can_defend()`, `speed()`, `lifetime()`, or
## `next_attack()` helper on this class or on `UnitCatalog`: a later line must
## derive behaviour from evidence instead of inheriting an invented rule from a
## parsed number.
##
## ## Absent is never zero (design D4)
##
## `breeding_order` and `sm_training_time` are committed on 300 of the 429
## committed rows, and the two nullable bags are committed as `null`. Each of
## the four is recorded with an explicit `has_*` flag, and its value is never
## substituted with zero — a zero would be indistinguishable from a committed
## zero.
##
## ## The cost vocabulary is inherited, not re-derived (design D4)
##
## `COST_RESOURCES` is not written out here: it is **aliased** from the
## delivered `placement_catalog.gd`, which mirrors the compatibility
## endpoints' own `g/c/w/o/s` mapping. Aliasing the constant means this model
## cannot disagree with what buying the unit would actually cost. An unknown
## cost key or a non-integer amount fails closed; nothing is guessed.
##
## ## Fields outside the five groups are not dropped
##
## Whatever the groups do not parse — `in_store`, `max_collects`,
## `trains_ids`, `group_type`, the `category_id` family, the building-limit
## pair, `source_file`, `source_layer`, `content_version` — stays reachable
## through `UnitCatalog.raw_entry`, the one documented escape hatch
## (design D3). The five groups are the *typed* view, not a filter.
##
## ## Failure is closed and named (design D4)
##
## Every malformed field returns `{ok: false, error}` naming the offending
## definition and field and produces **no** definition, mirroring the delivered
## building catalog. The `legacy_id` is read first so every later message can
## name the item.
##
## ## The committed numbers arrive as integral floats
##
## The pinned engine's JSON parser represents every committed JSON number as a
## **float**, including the integers the content package's rule R1 coerces.
## An integer field therefore accepts an `int` or an integral `float` and
## stores the exact integer — the documented transport tolerance the delivered
## `placement_catalog.gd` applies to the same field class. This is a
## representation change with no value change: `10` and `10.0` are the same
## committed number, and nothing is scaled, rounded, or defaulted. A numeric
## **string** is refused, because no committed source stores one.

## The delivered building catalog, reused only for its cost-key table.
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

## Legacy cost keys onto resource names — **aliased, not restated** (design
## D4). Identical to the delivered purchase, shop, expansion and level
## surfaces' mapping by construction, because it *is* their mapping.
const COST_RESOURCES := PlacementCatalog.COST_RESOURCES

## Largest magnitude accepted for a transported integer (2^53, the exact
## integer range of an IEEE-754 double on the pinned JSON transport).
const MAX_INTEGER := 9007199254740992.0

## The five named field groups (design D3). This table is the single source of
## truth for the parsed-field inventory: the suite and the evidence report read
## it rather than restating it, so a field added or removed here cannot leave
## the documentation describing a model that no longer exists.
const GROUP_IDENTITY := "identity_presentation"
const GROUP_FOOTPRINT := "footprint_placement"
const GROUP_STATISTICS := "statistics"
const GROUP_ECONOMY := "economy"
const GROUP_TRAINING := "training_upgrade"

## Group name -> its committed field names, in schema order.
const FIELD_GROUPS := {
	GROUP_IDENTITY: ["legacy_id", "name", "img_name", "type", "kind", "race",
		"display_order"],
	GROUP_FOOTPRINT: ["width", "height", "elevation", "population", "volume",
		"max_elem_vol", "max_frame"],
	GROUP_STATISTICS: ["attack", "defense", "life", "attack_interval",
		"attack_range", "velocity", "expiration", "best_against",
		"best_against_mult"],
	GROUP_ECONOMY: ["costs", "cost", "cost_unit_cash", "collect",
		"collect_type", "collect_xp", "xp", "unit_capacity"],
	GROUP_TRAINING: ["training_time", "sm_training_time", "breeding_order",
		"upgrades_to", "syringes", "min_level", "activation",
		"clicks_to_build", "build_time"],
}

## The groups, in their canonical order.
const GROUP_ORDER := [GROUP_IDENTITY, GROUP_FOOTPRINT, GROUP_STATISTICS,
	GROUP_ECONOMY, GROUP_TRAINING]

## The embedded-JSON `properties` bag. It is committed content this model
## parses verbatim, and it is deliberately **outside** the five groups: it is a
## free-form committed flag map, not one of D3's five categories, so grouping it
## would invent a category the design does not name.
const PROPERTY_BAG_FIELD := "properties"

## Fields committed on only part of the set; each carries a `has_*` flag.
const CONDITIONALLY_PRESENT_FIELDS := ["breeding_order", "sm_training_time"]

## Nullable committed bags; each carries a `has_*` flag and is absent — never
## zero, never an empty bag substituted for a committed `null` — when the row
## records `null`.
const NULLABLE_BAG_FIELDS := ["inventory_ids", "premium_upgrade_costs"]


## One committed unit definition: static content, verbatim, no player state.
##
## Read-only by construction: the class declares no setter, no mutating method,
## and no lifecycle. It exists so a reader can see exactly what a committed unit
## row carries, and nothing that belongs to a player's save.
class Definition extends RefCounted:
	## Group: identity and presentation.
	## Legacy item id, preserved **verbatim as a string** (design D5): the
	## normalized package records it as the legacy item id, and coercing it to
	## an integer would break lookups against the registry's own index.
	var legacy_id := ""
	var name := ""
	## The committed sprite asset reference, verbatim. A comma-joined list on
	## part of the committed set; this field is never split or interpreted here.
	var img_name := ""
	var type := ""
	var kind := ""
	var race := ""
	var display_order := 0

	## Group: footprint and placement (committed content, no cell semantics).
	var width := 0
	var height := 0
	var elevation := 0
	var population := 0
	var volume := 0
	var max_elem_vol := 0
	var max_frame := 0

	## Group: statistics — committed numbers with **no** gameplay semantics.
	## See the module docstring: `attack: 10` is a number in a definition, not
	## a damage rule.
	var attack := 0
	var defense := 0
	var life := 0
	var attack_interval := 0
	var attack_range := 0
	var velocity := 0
	var expiration := 0
	## The committed opaque combat flag: an integer code or a string flag,
	## preserved verbatim and never coerced to one or the other. No committed
	## row carries an integer, and the empty string is a committed value here,
	## not an absence.
	var best_against: Variant = ""
	var best_against_mult := 0

	## Group: economy.
	## The committed cost bag, parsed with the delivered endpoints' own letter
	## vocabulary: resource name -> integer amount. An empty committed object
	## stays empty; it is never filled in from `cost`.
	var costs := {}
	var cost := 0
	var cost_unit_cash := 0
	var collect := 0
	var collect_type := ""
	var collect_xp := 0
	var xp := 0
	var unit_capacity := 0

	## Group: training and upgrade.
	var training_time := 0
	## `sm_training_time` is committed on 300 of the 429 rows. When it is
	## absent the flag is `false` and the field keeps its declared default —
	## and the flag, not the value, is the distinguisher: the committed set
	## records no committed zero for either conditionally-present field, so
	## only the flag can tell "absent" from "zero".
	var has_sm_training_time := false
	var sm_training_time := 0
	## `breeding_order` is committed on 300 of 429 rows, under the same rule.
	var has_breeding_order := false
	var breeding_order := 0
	## The committed upgrade-chain reference. It is a **signed** integer
	## because the committed rows record `-1`; the schema documents -1 and 0
	## as "none" and this model applies **no** interpretation of that note — no
	## `has_upgrade()`, no resolution to another definition.
	var upgrades_to := 0
	var syringes := 0
	var min_level := 0
	var activation := 0
	var clicks_to_build := 0
	var build_time := 0

	## The committed embedded-JSON property bag, verbatim: committed flag key
	## -> committed flag value. Never interpreted — `ft_ground: "1"` is not
	## read as a movement rule, and no key grants a capability.
	var properties := {}

	## The two nullable committed bags. A committed `null` is recorded as
	## **absent** with a `false` flag and a null value: never an empty object
	## substituted for a null, and never zero.
	var has_inventory_ids := false
	var inventory_ids = null
	var has_premium_upgrade_costs := false
	var premium_upgrade_costs = null


## Parses one committed registry entry. Returns
##   `{ok: true, error: "", definition: <Definition>}`
## or
##   `{ok: false, error: "<message naming the definition and the field>",
##     definition: null}`
## — no partial definition, nothing guessed, defaulted, or coerced (design D4).
##
## `entry` is one stored entry of the registry's `units` domain. The
## `legacy_id` is validated first so every later failure can name the item.
static func parse(entry: Variant) -> Dictionary:
	if not (entry is Dictionary):
		return _reject("entry is not an object")
	var row: Dictionary = entry
	var legacy_id: Variant = _text(row.get("legacy_id"), false)
	if legacy_id == null:
		return _reject("field 'legacy_id' is invalid")
	var label := "unit %s" % str(legacy_id)
	var typed := Definition.new()
	typed.legacy_id = str(legacy_id)

	# -- Group: identity and presentation ------------------------------------
	var text_field: Dictionary = _text_field(row, "name", label, false)
	if not bool(text_field.get("ok", false)):
		return _reject(str(text_field.get("error", "")))
	typed.name = str(text_field["value"])
	# The committed sprite reference may be the meaningful empty string, so it
	# is the one identity field that is not required to be non-empty.
	text_field = _text_field(row, "img_name", label, true)
	if not bool(text_field.get("ok", false)):
		return _reject(str(text_field.get("error", "")))
	typed.img_name = str(text_field["value"])
	for identity_field: String in ["type", "kind", "race"]:
		text_field = _text_field(row, identity_field, label, false)
		if not bool(text_field.get("ok", false)):
			return _reject(str(text_field.get("error", "")))
		typed.set(identity_field, str(text_field["value"]))
	var display_order := _count_field(row, "display_order", label)
	if not bool(display_order.get("ok", false)):
		return _reject(str(display_order.get("error", "")))
	typed.display_order = int(display_order["value"])

	# -- Group: footprint and placement --------------------------------------
	for footprint_field: String in ["width", "height", "elevation",
			"population", "volume", "max_elem_vol", "max_frame"]:
		var footprint := _count_field(row, footprint_field, label)
		if not bool(footprint.get("ok", false)):
			return _reject(str(footprint.get("error", "")))
		typed.set(footprint_field, int(footprint["value"]))

	# -- Group: statistics (verbatim numbers, no semantics) ------------------
	for statistic: String in ["attack", "defense", "life", "attack_interval",
			"attack_range", "velocity", "expiration",
			"best_against_mult"]:
		var value := _count_field(row, statistic, label)
		if not bool(value.get("ok", false)):
			return _reject(str(value.get("error", "")))
		typed.set(statistic, int(value["value"]))
	var best_against := _best_against_field(row, label)
	if not bool(best_against.get("ok", false)):
		return _reject(str(best_against.get("error", "")))
	typed.best_against = best_against["value"]

	# -- Group: economy ------------------------------------------------------
	var costs := _parse_costs(row.get("costs"), label)
	if not bool(costs.get("ok", false)):
		return _reject(str(costs.get("error", "")))
	typed.costs = costs["costs"]
	for economy_field: String in ["cost", "cost_unit_cash", "collect",
			"collect_xp", "xp", "unit_capacity"]:
		var value := _count_field(row, economy_field, label)
		if not bool(value.get("ok", false)):
			return _reject(str(value.get("error", "")))
		typed.set(economy_field, int(value["value"]))
	text_field = _text_field(row, "collect_type", label, false)
	if not bool(text_field.get("ok", false)):
		return _reject(str(text_field.get("error", "")))
	typed.collect_type = str(text_field["value"])

	# -- Group: training and upgrade ----------------------------------------
	for training_field: String in ["training_time", "syringes", "min_level",
			"activation", "clicks_to_build", "build_time"]:
		var value := _count_field(row, training_field, label)
		if not bool(value.get("ok", false)):
			return _reject(str(value.get("error", "")))
		typed.set(training_field, int(value["value"]))
	# The upgrade-chain reference is the one signed field: the committed rows
	# record -1, so a non-negative parser would refuse every committed row.
	var upgrades := _signed_field(row, "upgrades_to", label)
	if not bool(upgrades.get("ok", false)):
		return _reject(str(upgrades.get("error", "")))
	typed.upgrades_to = int(upgrades["value"])
	# The two conditionally-present fields: absent stays absent (design D4).
	for optional: String in ["sm_training_time", "breeding_order"]:
		if not row.has(optional):
			continue
		var value := _count_field(row, optional, label)
		if not bool(value.get("ok", false)):
			return _reject(str(value.get("error", "")))
		typed.set("has_" + optional, true)
		typed.set(optional, int(value["value"]))

	# -- The committed embedded-JSON property bag ----------------------------
	var properties := _parse_properties(row.get(PROPERTY_BAG_FIELD), label)
	if not bool(properties.get("ok", false)):
		return _reject(str(properties.get("error", "")))
	typed.properties = properties["properties"]

	# -- The two nullable committed bags: a committed null is ABSENT ---------
	for bag: String in NULLABLE_BAG_FIELDS:
		if not row.has(bag) or row[bag] == null:
			continue
		if not (row[bag] is Dictionary):
			return _reject("field '%s' of %s is invalid" % [bag, label])
		typed.set("has_" + bag, true)
		typed.set(bag, (row[bag] as Dictionary).duplicate(true))

	return {"ok": true, "error": "", "definition": typed}


## The parsed-field inventory: group name -> field names, as fresh copies a
## caller may mutate. Never the constant itself.
static func field_inventory() -> Dictionary:
	var out := {}
	for group: String in GROUP_ORDER:
		out[group] = (FIELD_GROUPS[group] as Array).duplicate()
	return out


## Every parsed committed field name, groups in canonical order, group fields
## in schema order, then the property bag and the two nullable bags — the whole
## committed surface the model types, **without** the four `has_*` flags, which
## are the model's own presence record rather than committed fields and are
## listed by `presence_flags()`. The two conditionally-present integers are
## already members of their group and are not appended twice.
static func parsed_fields() -> Array:
	var out: Array = []
	for group: String in GROUP_ORDER:
		out.append_array(FIELD_GROUPS[group] as Array)
	out.append(PROPERTY_BAG_FIELD)
	out.append_array(NULLABLE_BAG_FIELDS)
	return out


## The `has_*` flag names, one per presence-flagged field: the two
## conditionally-present integers and the two nullable bags.
static func presence_flags() -> Array:
	var out: Array = []
	for field: String in CONDITIONALLY_PRESENT_FIELDS:
		out.append("has_" + field)
	for field: String in NULLABLE_BAG_FIELDS:
		out.append("has_" + field)
	return out


# ---------------------------------------------------------------------------
# Field readers — every one fails closed and names its field
# ---------------------------------------------------------------------------


## A required string field. `allow_empty` is set only for `img_name`, whose
## meaningful empty string is a committed value.
static func _text_field(row: Dictionary, field: String, label: String,
		allow_empty: bool) -> Dictionary:
	var value: Variant = _text(row.get(field), allow_empty)
	if value == null:
		return _invalid(field, label)
	return {"ok": true, "value": value}


## A non-negative committed integer field.
static func _count_field(row: Dictionary, field: String,
		label: String) -> Dictionary:
	var value: Variant = _count(row.get(field))
	if value == null:
		return _invalid(field, label)
	return {"ok": true, "value": value}


## A signed committed integer field (`upgrades_to` records -1).
static func _signed_field(row: Dictionary, field: String,
		label: String) -> Dictionary:
	var value: Variant = _integer(row.get(field))
	if value == null:
		return _invalid(field, label)
	return {"ok": true, "value": value}


## The committed opaque combat flag: an integer code or a string flag,
## preserved verbatim. The empty string is committed content here, not an
## absence, so it is accepted; any other type fails closed.
static func _best_against_field(row: Dictionary, label: String) -> Dictionary:
	var raw: Variant = row.get("best_against")
	if raw is String:
		return {"ok": true, "value": raw}
	if typeof(raw) == TYPE_INT:
		return {"ok": true, "value": int(raw)}
	return _invalid("best_against", label)


## The committed cost bag parsed onto the delivered endpoints' resource names.
##
## The committed normalized rows carry `costs` as a **JSON object** — the
## content package's rule R2 already coerced the legacy embedded-JSON string —
## so the object is the form this reader must accept. A JSON string is also
## accepted and parsed, because that is the transport tolerance the delivered
## building catalog documents for the same field class; both paths then fail
## closed identically. The field is **required** by `unit.schema.json` and
## committed on every row, so an absent or null one is refused rather than
## defaulted to an empty bag. An unknown cost key or a non-integer amount is
## refused, and nothing is fabricated: a committed empty object stays empty.
static func _parse_costs(value: Variant, label: String) -> Dictionary:
	var source: Variant = value
	if source == null:
		return {"ok": false, "costs": {},
			"error": "field 'costs' of %s is invalid: missing" % label}
	if source is String:
		var text := str(source)
		if text.strip_edges().is_empty():
			return {"ok": false, "costs": {},
				"error": "field 'costs' of %s is invalid: empty" % label}
		var json := JSON.new()
		if json.parse(text) != OK:
			return {"ok": false, "costs": {},
				"error": "field 'costs' of %s is invalid: not valid JSON (%s)"
					% [label, json.get_error_message()]}
		source = json.get_data()
	if not (source is Dictionary):
		return {"ok": false, "costs": {},
			"error": "field 'costs' of %s is invalid: not a cost object"
				% label}
	var costs := {}
	for key: Variant in source:
		var resource: Variant = COST_RESOURCES.get(str(key))
		if resource == null:
			return {"ok": false, "costs": {},
				"error": "field 'costs' of %s is invalid: unknown cost key '%s'"
					% [label, str(key)]}
		var amount: Variant = _amount((source as Dictionary)[key])
		if amount == null:
			return {"ok": false, "costs": {},
				"error": "field 'costs' of %s is invalid: amount of cost key "
					% label + "'%s' is not an integer" % str(key)}
		costs[str(resource)] = int(amount)
	return {"ok": true, "costs": costs, "error": ""}


## The committed property bag, parsed verbatim: a committed flag key -> a
## committed flag value. The committed rows carry every value as a **string**
## (`{"ft_ground": "1"}`), so a non-string value fails closed rather than being
## coerced into a readable flag. The field is **required** by
## `unit.schema.json` and committed on every row, so an absent one is refused
## rather than defaulted to an empty bag. No key is interpreted: no property
## grants a capability, a movement mode, or a behaviour.
static func _parse_properties(value: Variant, label: String) -> Dictionary:
	if value == null:
		return {"ok": false, "properties": {},
			"error": "field '%s' of %s is invalid: missing"
				% [PROPERTY_BAG_FIELD, label]}
	if not (value is Dictionary):
		return {"ok": false, "properties": {},
			"error": "field '%s' of %s is invalid: not an object"
				% [PROPERTY_BAG_FIELD, label]}
	var properties := {}
	for key: Variant in value:
		if not (key is String) or str(key).is_empty():
			return {"ok": false, "properties": {},
				"error": "field '%s' of %s is invalid: property key is not a "
					% [PROPERTY_BAG_FIELD, label] + "non-empty string"}
		var entry: Variant = (value as Dictionary)[key]
		if not (entry is String):
			return {"ok": false, "properties": {},
				"error": "field '%s' of %s is invalid: property '%s' is not a "
					% [PROPERTY_BAG_FIELD, label, str(key)] + "string"}
		properties[str(key)] = str(entry)
	return {"ok": true, "properties": properties, "error": ""}


## The house rejection envelope: names the offending definition and field and
## never produces a partial definition.
static func _reject(message: String) -> Dictionary:
	return {"ok": false,
		"error": "[unit] parse rejected: " + message,
		"definition": null}


static func _invalid(field: String, label: String) -> Dictionary:
	return {"ok": false, "error": "field '%s' of %s is invalid" % [field, label]}


## A committed string. `allow_empty` admits the meaningful empty string; null
## for anything else, never a coerced or trimmed value.
static func _text(value: Variant, allow_empty: bool) -> Variant:
	if not (value is String):
		return null
	var text := str(value)
	if text.is_empty() and not allow_empty:
		return null
	return text


## A non-negative committed integer: an `int` or an integral `float` — the
## pinned engine's JSON parser represents every committed number as a float —
## inside the transported exact-integer range. A numeric **string** fails closed
## on purpose: the committed normalized package stores these fields as JSON
## numbers, so accepting digit strings would invent a tolerance no committed
## source requires.
static func _count(value: Variant) -> Variant:
	var number: Variant = _integer(value)
	if number == null or int(number) < 0:
		return null
	return number


## A committed integer: an `int` or an integral `float` inside the transported
## exact-integer range. Signed, because `upgrades_to` records -1.
static func _integer(value: Variant) -> Variant:
	if value is int:
		var typed := int(value)
		return typed if absf(float(typed)) <= MAX_INTEGER else null
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and is_finite(typed) and absf(typed) <= MAX_INTEGER:
			return int(typed)
	return null


## A cost amount exactly as the delivered endpoints accept one: an integer or
## an integral float in the transported integer range; a numeric string fails
## closed, because coercing `"10"` to ten would invent a value the committed
## object does not carry.
static func _amount(value: Variant) -> Variant:
	return _integer(value)