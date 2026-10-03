extends "res://tests/test_base.gd"
## Stored-item placement suite (OpenSpec `godot-stored-item-placement`
## "Storage contents are projected verbatim and fail closed" /
## "Placing a stored item is a server-derived intent and the row is server-owned" /
## "Selling a stored item credits nothing" /
## "Storage placement is consumable, and one operation consumes exactly one" /
## "Four refusals replace four unguarded legacy behaviours" /
## "Grid bounds and cell occupancy are recorded, not invented" /
## "Both GameApi implementations answer the same intents identically" /
## "An executed-legacy fixture for the storage round trip" /
## "Stored-item placement evidence and claim limits", design D1-D7).
##
## This line delivers a **working round trip**, not a refusal: the legacy server
## can place a stored item, and 24 executed probe transactions in
## `docs/legacy-stored-unit-placement.md` established its shape. So most of what
## is asserted here is positive -- the storage projection, the attribute mirror
## checked against **all 900** committed items, the four refusals, the recorded
## geometry gap, and both implementations driving the captured fixture.
##
## The anti-invention guard is structural **and was tested rather than trusted**:
## `stored_item_flow.gd`'s whole function inventory is compared against a
## pinned list, its `ABSENT_HELPERS` are named, a pinned set of forbidden helper
## names is asserted absent, and the delivered declarations are parsed to prove
## none of them accepts an `attr`, `player`, `item_index`, `timestamp`,
## `quantity`, `price`, or `refund` parameter -- which is what makes "the client
## cannot dictate the row's bag, its team, or any price" mechanical rather than
## a promise.
##
## Checks:
##   projection  the store and ledger read verbatim, the four fail-closed codes,
##               an absent store and an absent ledger treated as real readings
##               rather than errors, and a malformed shape never inventing an
##               entry;
##   attr        the attribute mirror over **all 900** committed items against an
##               independent computation, the measured 601/273/26 bag
##               distribution, 0 items unplaceable, the named inverse's round
##               trip, and both fail-closed codes;
##   intents     the two intent key sets, the dismissed keys, and the forbidden
##               parameters absent from every delivered declaration;
##   refusals    the four refusals, each recorded as a **divergence** from an
##               oracle that answers success in all four cases;
##   geometry    the recorded gap, `bounds_refused` false, and no bounds,
##               occupancy, or footprint helper anywhere;
##   evaluate    `evaluate_place`/`evaluate_sell` over crafted envelopes, a
##               refusal envelope reported unresolvable, and `credited` **read**
##               rather than assumed;
##   fake        the FakeApi double driven end to end over the committed capture:
##               placement and sale, the refusals, and both orderings;
##   api         both implementations declare the same two operations, and the
##               facade declares both forwarders and both counters;
##   absence     the delivered module's whole function inventory against a pinned
##               list, its `ABSENT_HELPERS` named with reasons, the forbidden
##               helper names absent **by name**, and the module pure;
##   legacy      the committed legacy source re-read for every fact this line
##               records: both branch line ranges, the four arguments each read
##               on exactly one line, `apply_resources` running before dispatch,
##               the store conditional, and the append-if-absent ledger;
##   fixture     the committed executed-legacy capture: 40 -> 41 placements, the
##               storage entry removed, one ledger id appended, **no** stored
##               resource moved, and a sale changing exactly one leaf;
##   boundary    the storage command token is declared in code only by the owned
##               files, which is the positive replacement for the collection
##               suite's now-superseded whole-tree absence claim.
const StoredItemFlow = preload("res://scripts/units/stored_item_flow.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")

const DELIVERED_FLOW_SCRIPT := "res://scripts/units/stored_item_flow.gd"
const DELIVERED_SUITE := "res://tests/test_stored_item_placement.gd"
const FIXTURE_DIR := "tests/fixtures/godot-stored-item-placement/steps"
const PLACE_BEFORE := FIXTURE_DIR + "/command_place_stored_item/before.json"
const PLACE_AFTER := FIXTURE_DIR + "/command_place_stored_item/after.json"
const SELL_BEFORE := FIXTURE_DIR + "/command_sell_stored_item/before.json"
const SELL_AFTER := FIXTURE_DIR + "/command_sell_stored_item/after.json"

## The committed stored item the capture grants and places: collection 1's prize,
## unit `1085` ("Metal Draggy"), a 1x1 item so the delivered line needs no
## footprint derivation.
const CAPTURED_ITEM := 1085
const CAPTURED_ITEM_NAME := "Metal Draggy"
const CAPTURED_CELL := [58, 47]
const CAPTURED_SLOT := 41
## The capture's recorded first derived slot, over 40 placements at keys 1..40.
const COMMITTED_PLACEMENTS := 40
const COMMITTED_SLOT_KEYS_LOW := 1
const COMMITTED_SLOT_KEYS_HIGH := 40

## The whole function inventory of `stored_item_flow.gd`. This is the
## anti-invention guard: a bounds, capacity, expiry, value, price, refund,
## occupancy, or slot-derivation helper appears here and fails the suite.
## Every entry is a projection reader, a mirror, an evaluator, a readout, a
## recorded-contract accessor, or a private reader.
const EXPECTED_FLOW_METHODS := [
	"_committed_int", "_decode_properties", "_ledger_gained", "attr_derived_from",
	"bag_is_derivable", "derive_attr", "evaluate_place", "evaluate_sell",
	"project_storage", "readout_sell", "readout_text", "stored_count",
]

## Helpers a capacity, expiry, value, price, refund, bounds, or occupancy rule
## would take. The inventory above is the real gate; this list is what the suite
## also asserts is absent **by name**, so a rename cannot smuggle one past the
## inventory and a leftover fails visibly.
const FORBIDDEN_HELPERS := [
	"bounds", "in_bounds", "cell_is_free", "footprint", "price", "cost",
	"refund", "capacity", "expiry", "value", "is_placeable", "next_free_slot",
]

## Parameters no delivered declaration may accept (stored-item-placement design
## D3). A parameter here would be a channel for exactly what the design refuses.
const FORBIDDEN_PARAMETERS := ["attr", "player", "item_index", "timestamp",
	"quantity", "price", "refund"]

## The seven STORED resources `engine.apply_resources` writes, which is exactly
## what `compat_legacy.resources()` returns and therefore exactly what the
## no-resource-moved proof compares. Deliberately not the M7 readout's set,
## which additionally surfaces the never-written `privateState.energy`.
const RESOURCE_KEYS := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

## The committed normalized content files the mirror is checked against. 900
## items in total: 470 buildings + 429 units + 1 special.
const CONTENT_FILES := ["buildings", "units", "specials"]

## The measured bag distribution over those 900 items, computed independently
## below and pinned here so a content drift fails the run.
const EXPECTED_ITEM_COUNT := 900
const EXPECTED_BUILDING_COUNT := 470
const EXPECTED_UNIT_COUNT := 429
const EXPECTED_SPECIAL_COUNT := 1
const EXPECTED_BAG_EMPTY := 601
const EXPECTED_BAG_CLICKS := 273
const EXPECTED_BAG_BOTH := 26
const EXPECTED_NOT_PLACEABLE := 0
const EXPECTED_UNITS_WITH_CLICKS := 0
const EXPECTED_UNITS_WITH_ASSIST := 0
const EXPECTED_BUILDINGS_WITH_CLICKS := 298
const EXPECTED_BUILDINGS_WITH_ASSIST := 26

## The legacy source facts this line records, pinned so a legacy drift fails the
## run instead of publishing a different fixture.
const LEGACY_PLACE_BRANCH_START := 233
const LEGACY_PLACE_BRANCH_END := 248
const LEGACY_SELL_BRANCH_START := 250
const LEGACY_SELL_BRANCH_END := 256
const LEGACY_APPLY_RESOURCES_LINE := 40
const LEGACY_STORE_CONDITIONAL_LINE := 78
const LEGACY_MAP_ADD_ITEM_LINE := 31
const LEGACY_Bought_UNIT_ADD_END := 89

## The files allowed to name the storage command token in CODE. A prose mention
## or a recorded non-claim string cannot be mistaken for code because
## `_code_only()` blanks comment lines and string-literal content.
const STORAGE_OWNERS := [
	"res://scripts/units/stored_item_flow.gd",
	"res://scripts/gameapi/boot_data.gd",
	"res://scripts/gameapi/game_api.gd",
	"res://scripts/gameapi/legacy_v0_api.gd",
	"res://scripts/gameapi/fake_api.gd",
	"res://tests/test_stored_item_placement.gd",
]

## The two operations both implementations must declare (design D8).
const REQUIRED_OPERATIONS := ["place_stored_item_town", "sell_stored_item_town"]

## The committed collection that seeds storage in the capture, and the two
## committed prizes this line reasons about.
const SEED_COLLECTION := 1
const PRIZE_UNIT := "1085"
const PRIZE_BUILDING := "1062"
const EXPECTED_COLLECTION_COUNT := 10

## Report evidence version, written by `--report=<path>`.
const REPORT_VERSION := "stored-placement-report-v1"
const DEFAULT_REPORT := "apps/client-godot/evidence/stored-placement/report.json"

## Collected while the checks run so the report is generated from the LIVE model
## and the LIVE content rather than restated from a constant.
var _report := {}
var _content_error := ""
var _items: Array = []
var _report_path := ""


func run_scenario() -> void:
	if _scenario_arg() == "live-stored-placement":
		await _check_live_stored_placement()
		return
	_report_path = _report_argument()
	_load_committed_items()
	_report = {
		"version": REPORT_VERSION,
		"flow_module": DELIVERED_FLOW_SCRIPT,
		"content_files": CONTENT_FILES,
		"content_error": _content_error,
		"row_slots": _row_slot_table(),
		"attr_mirror": {},
		"storage_projection": {},
		"intents": {
			"place_keys": StoredItemFlow.PLACE_INTENT_KEYS.duplicate(),
			"sell_keys": StoredItemFlow.SELL_INTENT_KEYS.duplicate(),
			"dismissed_keys": StoredItemFlow.DISMISSED_KEYS.duplicate(),
			"forbidden_parameters": FORBIDDEN_PARAMETERS.duplicate(),
		},
		"refusals": StoredItemFlow.REFUSALS.duplicate(true),
		"geometry": {
			"note": StoredItemFlow.GEOMETRY_GAP,
			"occupancy_note": StoredItemFlow.CELL_OCCUPANCY_GAP,
			"bounds_refused": false,
			"cell_occupancy_refused": false,
		},
		"rules": {
			"slot": StoredItemFlow.SLOT_RULE,
			"row": StoredItemFlow.ROW_DERIVATION,
			"attr": StoredItemFlow.ATTR_RULE,
			"timestamp": StoredItemFlow.TIMESTAMP_NOTE,
			"quantity": StoredItemFlow.QUANTITY_RULE,
			"ledger": StoredItemFlow.LEDGER_RULE,
			"no_price": StoredItemFlow.NO_PRICE,
			"no_refund": StoredItemFlow.NO_REFUND,
			"no_storage_rule": StoredItemFlow.NO_STORAGE_RULE,
			"store_not_purchase": StoredItemFlow.STORE_NOT_PURCHASE,
		},
		"resources": StoredItemFlow.RESOURCE_NAMES.duplicate(),
		"committed_content": {
			"items": _items.size(),
			"note": StoredItemFlow.COMMITTED_CONTENT_NOTE,
		},
		"absent_helpers": (StoredItemFlow.ABSENT_HELPERS as Array).duplicate(true),
		"fixture": {},
	}
	_check_projection()
	_check_attr_mirror()
	_check_intents()
	_check_refusals()
	_check_geometry()
	_check_evaluate()
	_check_fake_double()
	_check_api_shape()
	_check_absence()
	_check_legacy()
	_check_fixture()
	_check_boundary()
	if _report_path != "":
		_write_report()


# --- projection ------------------------------------------------------------

func _check_projection() -> void:
	# The captured before-state: one stored unit, an empty ledger.
	var projection := StoredItemFlow.project_storage({PRIZE_UNIT: 1}, [])
	check(bool(projection["ok"]), "the captured storage reads cleanly")
	check_eq(projection["code"], "", "a readable store carries no failure code")
	check_eq(projection["distinct_ids"], 1, "the captured store holds one id")
	check_eq(projection["total_units"], 1, "the captured store holds one unit")
	check_eq(projection["entries"], {PRIZE_UNIT: 1},
		"the stored count is read verbatim, under its committed string key")
	check_eq(projection["ledger"], [], "the captured ledger is empty")
	check_eq(bool(projection["ledger_present"]), true,
		"a present empty ledger is a real reading, not an absent field")

	# An ABSENT store and an ABSENT ledger: the committed fresh corpus records
	# both, so neither may be invented as an error.
	var absent_store := StoredItemFlow.project_storage(null, null)
	check(not bool(absent_store["ok"]),
		"an absent store cannot be read, so the projection fails closed")
	check_eq(absent_store["code"], "store_absent", "an absent store is named")
	check_eq(bool(absent_store["ledger_present"]), false,
		"an absent ledger is reported as absent, not as empty-and-present")
	check_eq(absent_store["ledger"], [], "an absent ledger reads as no ids")
	check_eq(absent_store["total_units"], 0,
		"an unreadable store reports no units rather than inventing a count")

	var absent_ledger := StoredItemFlow.project_storage({}, null)
	check(bool(absent_ledger["ok"]),
		"an absent ledger alone does not make the store unreadable")
	check_eq(absent_ledger["total_units"], 0, "an empty store holds no units")

	# Every fail-closed code, with the recorded entry preserved.
	var not_object := StoredItemFlow.project_storage([], [])
	check(not bool(not_object["ok"]), "a non-mapping store fails closed")
	check_eq(not_object["code"], "store_not_object",
		"a non-mapping store is named store_not_object")

	var bad_count := StoredItemFlow.project_storage({"7": "many"}, [])
	check(not bool(bad_count["ok"]), "a non-integer stored count fails closed")
	check_eq(bad_count["code"], "count_not_integer",
		"a non-integer stored count is named count_not_integer")
	check_eq(bad_count["entries"], {},
		"no entry is invented for an unreadable count")

	var fractional := StoredItemFlow.project_storage({"7": 1.5}, [])
	check(not bool(fractional["ok"]),
		"a non-integral stored count fails closed rather than truncating")
	check_eq(fractional["code"], "count_not_integer",
		"a fractional stored count is named, not rounded")

	var bad_ledger := StoredItemFlow.project_storage({}, {})
	check(not bool(bad_ledger["ok"]), "a non-list ledger fails closed")
	check_eq(bad_ledger["code"], "ledger_not_list",
		"a non-list ledger is named ledger_not_list")

	# A JSON float that IS integral is an integer: the transport widens the
	# legacy save's ints to floats, and the M7 resource line recorded why.
	var widened := StoredItemFlow.project_storage({"7": 3.0}, [])
	check(bool(widened["ok"]), "an integral float count reads as an integer")
	check_eq(widened["entries"], {"7": 3}, "an integral float keeps its value")

	# Booleans are not integers legacy would accept.
	var boolean_count := StoredItemFlow.project_storage({"7": true}, [])
	check(not bool(boolean_count["ok"]),
		"a boolean stored count fails closed rather than coercing")

	# Several ids: the ledger counts DISTINCT ids and never units held.
	var many := StoredItemFlow.project_storage({PRIZE_UNIT: 2, PRIZE_BUILDING: 1},
		[1, 2])
	check_eq(many["distinct_ids"], 2, "two stored ids are two distinct ids")
	check_eq(many["total_units"], 3, "three units across two ids are three units")
	check_eq(many["ledger"], [1, 2], "the ledger is read verbatim and in order")

	# The stored-count accessor: string keys first, then the JSON spelling.
	check_eq(StoredItemFlow.stored_count({PRIZE_UNIT: 3}, CAPTURED_ITEM), 3,
		"the stored count reads the committed string key")
	check_eq(StoredItemFlow.stored_count({}, CAPTURED_ITEM), 0,
		"an absent id holds nothing")
	check_eq(StoredItemFlow.stored_count(null, CAPTURED_ITEM), 0,
		"an unreadable store holds nothing rather than raising")
	check_eq(StoredItemFlow.stored_count({PRIZE_UNIT: 0}, CAPTURED_ITEM), 0,
		"an entry whose count reached zero holds nothing")

	_report["storage_projection"] = {
		"captured": {
			"ok": bool(projection["ok"]),
			"code": str(projection["code"]),
			"distinct_ids": int(projection["distinct_ids"]),
			"total_units": int(projection["total_units"]),
			"entries": (projection["entries"] as Dictionary).duplicate(true),
		},
		"absent_store_code": str(absent_store["code"]),
		"absent_ledger_is_absent": not bool(absent_ledger["ledger_present"]),
		"codes": _codes_of(StoredItemFlow.PROJECTION_ERRORS),
	}


# --- the attribute mirror over all 900 committed items ---------------------

func _check_attr_mirror() -> void:
	check_eq(_content_error, "", "the committed normalized items are readable")
	if not _items.is_empty():
		_check_attr_across_content()
	# The three bag shapes, over crafted input, so the mirror is exercised even
	# if the content file were ever unreadable.
	var unit_bag := StoredItemFlow.derive_attr(0, {"ft_building": "1"})
	check(bool(unit_bag["ok"]), "a unit's committed fields derive cleanly")
	check_eq(unit_bag["attr"], {},
		"a unit with neither field yields an empty bag, as 0 of 429 committed units do")
	check_eq(unit_bag["fields"], [],
		"an empty bag has no derived field to report")

	var clicks_bag := StoredItemFlow.derive_attr(3, {"bulldozable": "1"})
	check_eq(clicks_bag["attr"], {StoredItemFlow.ATTR_CLICKS_KEY: 0},
		"a positive click count seeds nc at zero")
	check_eq(clicks_bag["fields"], ["clicks_to_build"],
		"nc is reported as derived from clicks_to_build")

	var assist_bag := StoredItemFlow.derive_attr(0,
		{"friend_assistable": "1"})
	check_eq(assist_bag["attr"], {StoredItemFlow.ATTR_ASSIST_KEY: []},
		"a friend-assistable item seeds an empty assist list")
	check_eq(assist_bag["fields"], ["properties.friend_assistable"],
		"si is reported as derived from the committed flag")

	var both_bag := StoredItemFlow.derive_attr(2, {"friend_assistable": "2"})
	check_eq(both_bag["fields"], ["properties.friend_assistable", "clicks_to_build"],
		"both keys are reported in the legacy write order, si before nc")

	# The committed normalized package stores the flags as STRINGS, so the
	# committed "0" must stay 0 -- a non-empty String is truthy in GDScript, and
	# `unit_movement.gd` records the same correction.
	var string_zero := StoredItemFlow.derive_attr(0, {"friend_assistable": "0"})
	check_eq(string_zero["attr"], {},
		"the committed string \"0\" reads as zero, not as a truthy String")
	var int_zero := StoredItemFlow.derive_attr(0, {"friend_assistable": 0})
	check_eq(int_zero["attr"], {}, "an integer zero reads as zero too")

	# The raw configuration stores the blob as a JSON-encoded STRING; the
	# normalized package stores an object. Both must agree.
	var raw := StoredItemFlow.derive_attr(0, "{\"friend_assistable\": \"1\"}")
	check_eq(raw["attr"], {StoredItemFlow.ATTR_ASSIST_KEY: []},
		"the raw JSON-encoded blob derives the same bag as the object form")

	# Fail-closed: a committed field legacy's int() could not read.
	var bad_flag := StoredItemFlow.derive_attr(0, {"friend_assistable": "many"})
	check(not bool(bad_flag["ok"]),
		"a non-numeric committed flag fails closed instead of half-deriving")
	check_eq(bad_flag["code"], "item_field_invalid",
		"a non-numeric committed flag is named item_field_invalid")
	check_eq(bad_flag["attr"], {}, "a failed derivation yields no bag at all")

	var bad_clicks := StoredItemFlow.derive_attr("many", {})
	check(not bool(bad_clicks["ok"]),
		"a non-numeric committed click count fails closed")
	check_eq(bad_clicks["code"], "item_field_invalid",
		"a non-numeric click count is named item_field_invalid")

	var boolean_clicks := StoredItemFlow.derive_attr(true, {})
	check(not bool(boolean_clicks["ok"]),
		"a boolean committed click count fails closed rather than coercing")

	var fractional_clicks := StoredItemFlow.derive_attr(1.5, {})
	check(not bool(fractional_clicks["ok"]),
		"a non-integral committed click count fails closed rather than truncating")

	var bad_properties := StoredItemFlow.derive_attr(0, 7)
	check(not bool(bad_properties["ok"]),
		"an unreadable committed properties field fails closed")
	check_eq(bad_properties["code"], "item_properties_invalid",
		"an unreadable properties field is named item_properties_invalid")

	# The empty blob: legacy tests truthiness FIRST, so an empty blob yields no
	# `si` and must NOT be reported as unreadable.
	var empty_object := StoredItemFlow.derive_attr(0, {})
	check(bool(empty_object["ok"]),
		"an empty properties object is truthiness-empty, not unreadable")
	check_eq(empty_object["attr"], {}, "an empty properties object yields no si")
	var empty_string := StoredItemFlow.derive_attr(0, "")
	check(bool(empty_string["ok"]), "an empty properties string is not unreadable")
	check_eq(empty_string["attr"], {}, "an empty properties string yields no si")

	# The named inverse: a key outside the derived vocabulary is reported, not
	# silently accepted, so a bag the service did not derive stays visible.
	check_eq(StoredItemFlow.attr_derived_from({"xp": 5}),
		["unknown:xp"],
		"an underived key is reported as unknown rather than accepted")
	check_eq(StoredItemFlow.attr_derived_from("not a bag"), [],
		"a non-object bag reports no derived field")
	check_eq(StoredItemFlow.attr_derived_from({}), [],
		"an empty bag reports no derived field")
	check(bool(StoredItemFlow.bag_is_derivable({})),
		"an empty bag is fully derivable")
	check(bool(StoredItemFlow.bag_is_derivable(
		{StoredItemFlow.ATTR_CLICKS_KEY: 0})), "an nc-only bag is derivable")
	check(not bool(StoredItemFlow.bag_is_derivable({"xp": 5})),
		"a bag carrying a key this mirror cannot derive is not derivable")
	check(not bool(StoredItemFlow.bag_is_derivable("not a bag")),
		"a non-object bag is not derivable")


## The mirror over EVERY committed item, against an independent computation done
## here from the same committed fields. A mirror that disagreed with the service
## would be a bug, and this is what makes that mechanical rather than asserted.
func _check_attr_across_content() -> void:
	var empty := 0
	var clicks := 0
	var both := 0
	var not_placeable := 0
	var units_with_clicks := 0
	var units_with_assist := 0
	var buildings_with_clicks := 0
	var buildings_with_assist := 0
	var inverse_failures: Array = []
	var mirror_failures: Array = []
	for entry: Dictionary in _items:
		var domain := str(entry["__domain"])
		var row: Dictionary = entry["row"]
		var clicks_to_build: Variant = row.get("clicks_to_build", null)
		var properties: Variant = row.get("properties", null)
		# The independent expectation, computed from the same committed fields
		# without touching the module under test.
		var expect: Array = []
		var flag: int = _flag(properties, StoredItemFlow.ATTR_FLAG_KEY)
		if flag > 0:
			expect.append(StoredItemFlow.ATTR_ASSIST_KEY)
		if _whole(clicks_to_build) > 0:
			expect.append(StoredItemFlow.ATTR_CLICKS_KEY)
		var derived := StoredItemFlow.derive_attr(clicks_to_build, properties)
		if not bool(derived["ok"]):
			mirror_failures.append(str(row.get("legacy_id", "?")))
			continue
		var got: Array = (derived["attr"] as Dictionary).keys()
		got.sort()
		var wanted := expect.duplicate()
		wanted.sort()
		if got != wanted:
			mirror_failures.append("%s (%s vs %s)" % [
				str(row.get("legacy_id", "?")), str(got), str(wanted)])
		# The inverse must name exactly the fields the forward derivation
		# consumed, for every committed item.
		var fields: Array = derived["fields"]
		var expected_fields: Array = []
		for key: String in expect:
			expected_fields.append(StoredItemFlow.ATTR_SOURCE[key])
		if fields != expected_fields:
			inverse_failures.append(str(row.get("legacy_id", "?")))
		match _bag_shape(wanted):
			"empty":
				empty += 1
			"clicks":
				clicks += 1
			_:
				both += 1
		# `is_placeable`: neither properties nor clicks_to_build, which the
		# SERVICE refuses as `item_not_placeable`. 0 of 900 committed items fail
		# it, which is why that refusal is unreachable through the corpus.
		if _placeable(properties, clicks_to_build) == false:
			not_placeable += 1
		if domain == "units":
			if _whole(clicks_to_build) > 0:
				units_with_clicks += 1
			if flag > 0:
				units_with_assist += 1
		elif domain == "buildings":
			if _whole(clicks_to_build) > 0:
				buildings_with_clicks += 1
			if flag > 0:
				buildings_with_assist += 1
	check_eq(mirror_failures.size(), 0,
		"the attribute mirror agrees with an independent derivation over all %d "
		% _items.size() + "committed items: " + str(mirror_failures.slice(0, 3)))
	check_eq(inverse_failures.size(), 0,
		"the named inverse round-trips over every committed item: "
		+ str(inverse_failures.slice(0, 3)))
	check_eq(_items.size(), EXPECTED_ITEM_COUNT,
		"the committed package holds exactly 900 normalized items")
	check_eq(empty, EXPECTED_BAG_EMPTY,
		"exactly 601 committed items derive an empty bag")
	check_eq(clicks, EXPECTED_BAG_CLICKS,
		"exactly 273 committed items seed nc alone")
	check_eq(both, EXPECTED_BAG_BOTH,
		"exactly 26 committed items seed both keys")
	check_eq(empty + clicks + both, EXPECTED_ITEM_COUNT,
		"every committed item falls into exactly one of the three bag shapes")
	check_eq(not_placeable, EXPECTED_NOT_PLACEABLE,
		"0 of 900 committed items are unplaceable, so the item_not_placeable "
		+ "refusal is unreachable through the corpus")
	check_eq(units_with_clicks, EXPECTED_UNITS_WITH_CLICKS,
		"0 of 429 committed units record a positive clicks_to_build")
	check_eq(units_with_assist, EXPECTED_UNITS_WITH_ASSIST,
		"0 of 429 committed units carry a friend_assistable flag at all")
	check_eq(buildings_with_clicks, EXPECTED_BUILDINGS_WITH_CLICKS,
		"298 of 470 committed buildings record a positive clicks_to_build")
	check_eq(buildings_with_assist, EXPECTED_BUILDINGS_WITH_ASSIST,
		"26 of 470 committed buildings carry a friend_assistable flag")
	_report["attr_mirror"] = {
		"items": _items.size(),
		"bag_empty": empty,
		"bag_clicks": clicks,
		"bag_both": both,
		"not_placeable": not_placeable,
		"units_with_clicks": units_with_clicks,
		"units_with_assist": units_with_assist,
		"buildings_with_clicks": buildings_with_clicks,
		"buildings_with_assist": buildings_with_assist,
		"attrs": {
			"si": StoredItemFlow.ATTR_ASSIST_KEY,
			"nc": StoredItemFlow.ATTR_CLICKS_KEY,
			"source": StoredItemFlow.ATTR_SOURCE.duplicate(true),
			"rule": StoredItemFlow.ATTR_RULE,
		},
	}


# --- the two intents -------------------------------------------------------

func _check_intents() -> void:
	check_eq(StoredItemFlow.PLACE_INTENT_KEYS,
		["user_id", "item_id", "x", "y", "orientation"],
		"the placement intent carries the save identity, the stored id, the cell, "
		+ "and the orientation passthrough -- nothing else")
	check_eq(StoredItemFlow.SELL_INTENT_KEYS, ["user_id", "item_id"],
		"the sale intent carries the save identity and the stored id -- nothing else")
	check_eq(StoredItemFlow.INTENT_KEYS,
		["user_id", "item_id", "x", "y"],
		"the shared intent vocabulary is the intersection of the two")
	# Every outcome-bearing key the refusals exist for must be named as dismissed.
	for key: String in ["item_index", "map_key", "attr", "player", "quantity",
			"price", "refund", "resources"]:
		check(StoredItemFlow.DISMISSED_KEYS.has(key),
			"the dismissed key list names '%s'" % key)
	# The parsed declarations: no forbidden parameter anywhere.
	var declarations := _declarations(DELIVERED_FLOW_SCRIPT)
	check(declarations.size() >= EXPECTED_FLOW_METHODS.size(),
		"the delivered module declares every method the pinned inventory names")
	for entry: Dictionary in declarations:
		var name := str(entry["name"])
		for parameter: String in FORBIDDEN_PARAMETERS:
			check(not (entry["parameters"] as Array).has(parameter),
				"delivered declaration '%s' accepts no '%s' parameter: the row's "
				% [name, parameter]
				+ "bag, team, slot, instant, quantity, price and refund are the "
				+ "service's, not the client's")
	check(StoredItemFlow.FORBIDDEN_PARAMETERS.size() >= FORBIDDEN_PARAMETERS.size(),
		"the recorded FORBIDDEN_PARAMETERS list covers every parameter the suite "
		+ "rejects")
	for entry: Dictionary in StoredItemFlow.FORBIDDEN_PARAMETERS:
		check(FORBIDDEN_PARAMETERS.has(str(entry["parameter"])),
			"the recorded forbidden parameter '%s' is one the suite rejects"
				% str(entry["parameter"]))
		check(str(entry["why"]).strip_edges() != "",
			"the recorded forbidden parameter '%s' states why it is forbidden"
				% str(entry["parameter"]))
	# The slot ownership claim is mechanical: four row slots are the client's
	# intent and four are derived, together all eight.
	check_eq(StoredItemFlow.CLIENT_INTENT_SLOTS.size()
		+ StoredItemFlow.SERVER_OWNED_SLOTS.size(), StoredItemFlow.ROW_SLOT_COUNT,
		"the four client-intent slots and the four server-derived slots partition "
		+ "the row's eight slots")
	var every_slot: Array = StoredItemFlow.CLIENT_INTENT_SLOTS.duplicate()
	every_slot.append_array(StoredItemFlow.SERVER_OWNED_SLOTS)
	every_slot.sort()
	var numbered: Array = StoredItemFlow.ROW_SLOTS.duplicate()
	numbered.sort()
	check_eq(every_slot, numbered,
		"the two slot groups cover every committed slot exactly once")
	check_eq(StoredItemFlow.ROW_SLOT_NAMES.size(), StoredItemFlow.ROW_SLOT_COUNT,
		"every committed slot has a recorded name")


# --- the four refusals -----------------------------------------------------

func _check_refusals() -> void:
	var refusals: Array = StoredItemFlow.REFUSALS
	check_eq(refusals.size(), 4, "exactly four refusals are recorded")
	var named: Array = []
	for entry: Dictionary in refusals:
		var code := str(entry["refusal"])
		named.append(code)
		check(StoredItemFlow.REFUSAL_CODES.has(code),
			"the refusal vocabulary names '%s'" % code)
		check_eq(bool(entry["divergence"]), true,
			"refusal '%s' is recorded as a DIVERGENCE from the oracle" % code)
		check_eq(int(entry["status"]), 409, "refusal '%s' answers 409" % code)
		check(str(entry["legacy"]).strip_edges() != "",
			"refusal '%s' records what the legacy server actually does" % code)
		check(str(entry["why"]).strip_edges() != "",
			"refusal '%s' records why it diverges" % code)
	named.sort()
	var sorted_codes: Array = StoredItemFlow.REFUSAL_CODES.duplicate()
	sorted_codes.sort()
	check_eq(named, sorted_codes,
		"the recorded refusals and the refusal vocabulary are the same set")
	check_eq(bool(StoredItemFlow.ALL_REFUSALS_ARE_DIVERGENCES), true,
		"the module states that every recorded refusal is a divergence, so a "
		+ "future line cannot quietly promote one to a parity claim")
	# The quantity and ledger rules are stated once and are consumable facts.
	check_eq(StoredItemFlow.QUANTITY, 1,
		"one operation consumes exactly one unit of stock")
	check_eq(StoredItemFlow.QUANTITY_RULE.find("quantity=1") >= 0, true,
		"the recorded quantity rule cites remove_store_item's default")
	check(StoredItemFlow.LEDGER_RULE.find("DISTINCT ITEM IDS") >= 0,
		"the recorded ledger rule states that the ledger counts distinct ids")
	check_eq(StoredItemFlow.DERIVED_GARRISON, [],
		"the derived garrison is always an empty list")
	check_eq(StoredItemFlow.DERIVED_PLAYER, 1,
		"the derived player team is always 1, because the legacy branch never "
		+ "passes the client-sent playerID on")
	check(StoredItemFlow.NO_PRICE.find("NO PRICE EXISTS") >= 0,
		"the no-price rule is recorded")
	check(StoredItemFlow.NO_REFUND.find("CREDITS NOTHING") >= 0,
		"the no-refund rule is recorded")
	check(StoredItemFlow.NO_STORAGE_RULE.find("NO CAPACITY") >= 0,
		"the no-storage-rule is recorded")
	check(StoredItemFlow.STORE_NOT_PURCHASE.find("NOT a purchase inventory") >= 0,
		"the store is explicitly not a purchase inventory")
	# The seven resources the proofs compare are the STORED seven, which is a
	# different set from the M7 readout's (that one also surfaces energy).
	check_eq(StoredItemFlow.RESOURCE_NAMES, RESOURCE_KEYS,
		"the proof resource set is exactly the seven apply_resources writes, "
		+ "which excludes the never-written privateState.energy")
	check_eq(StoredItemFlow.RESOURCE_NAMES.size(), 7, "seven stored resources")


# --- the recorded geometry gap --------------------------------------------

func _check_geometry() -> void:
	check(StoredItemFlow.GEOMETRY_GAP.find("RECORDED, NOT REFUSED") >= 0,
		"the geometry gap is recorded rather than closed")
	check(StoredItemFlow.GEOMETRY_GAP.find("(250, -3)") >= 0,
		"the recorded gap cites the executed probe that stored an out-of-range cell")
	check(StoredItemFlow.GEOMETRY_GAP.find("EVIDENCE") >= 0,
		"the recorded gap says closing it needs new evidence, not a derivation")
	check(StoredItemFlow.CELL_OCCUPANCY_GAP.find("NEIGHBOURING ROW") >= 0,
		"the occupancy gap names the absence of any neighbour read")
	check(StoredItemFlow.CELL_OCCUPANCY_GAP.find("1x1") >= 0,
		"the occupancy gap records that the delivered prize is a 1x1 item")
	# slot_occupied is NOT a contradiction of the recorded gap: it destroys an
	# existing row, which the out-of-range cell demonstrably does not.
	var occupied := {}
	for entry: Dictionary in StoredItemFlow.REFUSALS:
		if str(entry["refusal"]) == "slot_occupied":
			occupied = entry
	check(not occupied.is_empty(), "slot_occupied is recorded")
	check(str(occupied["legacy"]).find("REPLACES") >= 0,
		"slot_occupied records that the legacy branch replaces an existing row")
	check(str(occupied["why"]).find("COUNT") >= 0
		or str(occupied["why"]).find("count") >= 0,
		"slot_occupied records that the destruction leaves the row count unchanged")
	check(not StoredItemFlow.GEOMETRY_GAP.find("slot_occupied") == 0
		or StoredItemFlow.GEOMETRY_GAP.find("`slot_occupied` is not a contradiction") >= 0,
		"the geometry gap explicitly reconciles itself with slot_occupied")
	# The delivered line names no geometry helper, so the gap is mechanical.
	for helper: String in ["bounds", "in_bounds", "cell_is_free", "footprint"]:
		check(FORBIDDEN_HELPERS.has(helper),
			"the forbidden helper list names '%s'" % helper)


# --- evaluating the service's own responses --------------------------------

func _check_evaluate() -> void:
	var placed := {
		"ok": true,
		"placement": {"item_id": CAPTURED_ITEM, "x": CAPTURED_CELL[0],
			"y": CAPTURED_CELL[1], "orientation": 0, "map_key": CAPTURED_SLOT,
			"slot_rule": StoredItemFlow.SLOT_RULE},
		"row": {"slots": [CAPTURED_ITEM, CAPTURED_CELL[0], CAPTURED_CELL[1],
			1791020315, 0, [], {}, 1], "attr": {}, "store": [], "player": 1},
		"quantity": {"consumed": 1, "count_before": 1, "count_after": 0},
		"ledger_before": [],
		"ledger_after": [CAPTURED_ITEM],
		"geometry": {"bounds_refused": false, "cell_occupancy_refused": false},
	}
	var evaluation := StoredItemFlow.evaluate_place(placed)
	check(bool(evaluation["resolvable"]), "a complete placement envelope resolves")
	check_eq(evaluation["map_key"], CAPTURED_SLOT,
		"the derived map key is taken from the response, never recomputed")
	check_eq(evaluation["item_id"], CAPTURED_ITEM, "the stored id is reported")
	check_eq(evaluation["cell"], CAPTURED_CELL, "the cell is reported")
	check_eq(evaluation["player"], 1, "the derived team is reported")
	check_eq(evaluation["garrison"], [], "the always-empty garrison is reported")
	check_eq(evaluation["count_before"], 1, "the stock before is reported")
	check_eq(evaluation["count_after"], 0, "the stock after is reported")
	check_eq(evaluation["quantity"], 1, "one unit was consumed")
	check_eq(bool(evaluation["ledger_gained"]), true,
		"the ledger gained the id, so the placement is recorded as acquiring it")
	check_eq(bool(evaluation["credited"]), false,
		"a placement credits nothing")
	check_eq(bool(evaluation["bounds_refused"]), false,
		"the evaluated placement reports that bounds were NOT refused")
	check(bool(evaluation["attr_derivable"]),
		"the empty bag this service would derive is fully derivable")

	var readout := StoredItemFlow.readout_text(evaluation)
	check(readout.find("Placed stored item %d" % CAPTURED_ITEM) >= 0,
		"the readout names the placed item")
	check(readout.find("derived by the server") >= 0,
		"the readout says the row was server-derived")
	check(readout.find("No resource moved") >= 0,
		"the readout says no resource moved")
	check(readout.find("one operation consumes 1") >= 0,
		"the readout states the quantity rule")

	# A bag the service did NOT derive must stay visible.
	var odd_bag := placed.duplicate(true)
	odd_bag["row"]["attr"] = {"xp": 5}
	var odd := StoredItemFlow.evaluate_place(odd_bag)
	check_eq(bool(odd["attr_derivable"]), false,
		"a bag carrying an underived key is not reported as derivable")
	check(odd["attr_fields"].has("unknown:xp"),
		"the evaluation reports the underived key instead of hiding it")

	# A missing block is a bad response, never a guess.
	check_eq(str(StoredItemFlow.evaluate_place({"ok": true})["reason"]),
		"bad_response", "a placement envelope with no row is a bad_response")
	check_eq(str(StoredItemFlow.evaluate_place("nonsense")["reason"]),
		"bad_response", "a non-object placement envelope is a bad_response")
	check_eq(str(StoredItemFlow.readout_text({"resolvable": false})),
		"Stored item not placed: ", "an unresolvable evaluation reads out as refused")

	# The sale. `credited` is READ, never assumed: a response claiming a credit
	# must surface it, or the readout would lie about the oracle.
	var sold := {
		"ok": true,
		"sale": {"item_id": CAPTURED_ITEM, "credited": false, "refund": null,
			"quantity_rule": StoredItemFlow.QUANTITY_RULE},
		"quantity": {"consumed": 1, "count_before": 1, "count_after": 0},
		"ledger_before": [CAPTURED_ITEM],
		"ledger_after": [CAPTURED_ITEM],
	}
	var sale := StoredItemFlow.evaluate_sell(sold)
	check(bool(sale["resolvable"]), "a complete sale envelope resolves")
	check_eq(bool(sale["credited"]), false, "a sale credits nothing")
	check_eq(int(sale["refund"]), 0, "a null refund reads as zero, not as a guess")
	check_eq(int(sale["count_before"]), 1, "the stock before a sale is reported")
	check_eq(int(sale["count_after"]), 0, "the stock after a sale is reported")
	check_eq(bool(sale["ledger_untouched"]), true,
		"a sale leaves the purchase ledger alone")
	var dishonest := sold.duplicate(true)
	dishonest["sale"]["credited"] = true
	dishonest["sale"]["refund"] = 500
	check_eq(bool(StoredItemFlow.evaluate_sell(dishonest)["credited"]), true,
		"the evaluator READS a claimed credit rather than forcing false, so a "
		+ "service regression would be visible instead of hidden")
	check_eq(int(StoredItemFlow.evaluate_sell(dishonest)["refund"]), 500,
		"a claimed refund is surfaced verbatim")
	var sell_readout := StoredItemFlow.readout_sell(sale)
	check(sell_readout.find("credited nothing") >= 0,
		"the sale readout says out loud that it credited nothing")
	check(sell_readout.find("purchase ledger was left alone") >= 0,
		"the sale readout reports the untouched ledger")
	check_eq(str(StoredItemFlow.evaluate_sell({"ok": true})["reason"]),
		"bad_response", "a sale envelope with no sale block is a bad_response")


# --- the FakeApi double, driven over the committed capture -----------------

func _check_fake_double() -> void:
	# Placement first.
	# Each double is added to the tree so the SceneTree owns it, exactly as
	# `test_tutorial.gd` does: an unparented `Node.new()` is still live at exit
	# and emits the ObjectDB-leak line that `verify-boot.ps1`'s `^ERROR:` guard
	# would read as a script error.
	var placer := FakeApi.new()
	root.add_child(placer)
	var placed: BootData.StoredPlacementResult = placer.place_stored_item_town(
		_fixture_pid(), CAPTURED_ITEM, CAPTURED_CELL[0], CAPTURED_CELL[1])
	check(bool(placed.ok), "the double places the captured stored item")
	check_eq(placed.result, "success", "the placement reports the legacy success")
	check_eq(placed.item_id, CAPTURED_ITEM, "the placed id is reported")
	check_eq(placed.map_key, CAPTURED_SLOT,
		"the derived map key is 41, over the corpus's 40 placements at keys 1..40")
	check_eq([placed.x, placed.y], CAPTURED_CELL, "the cell is echoed")
	check_eq(placed.row.size(), StoredItemFlow.ROW_SLOT_COUNT,
		"the placed row carries all eight slots")
	check_eq(int(placed.row[StoredItemFlow.ROW_SLOT_ITEM]), CAPTURED_ITEM,
		"row slot 0 is the placed item id")
	check_eq(int(placed.row[StoredItemFlow.ROW_SLOT_X]), CAPTURED_CELL[0],
		"row slot 1 is the cell's x")
	check_eq(int(placed.row[StoredItemFlow.ROW_SLOT_Y]), CAPTURED_CELL[1],
		"row slot 2 is the cell's y")
	check(int(placed.row[StoredItemFlow.ROW_SLOT_TIMESTAMP]) > 0,
		"the row instant is a wall-clock reading, so it is asserted positively")
	check(int(placed.server_time) > 0, "the envelope carries a positive server_time")
	# The double never reads the wall clock: its row instant is EXACTLY the
	# capture's recorded one, which is asserted against the fixture rather than
	# against `server_time` (which is a DIFFERENT recorded instant -- the base
	# capture's `playerInfo.timestamp` -- so equating the two would be a false
	# claim about two unrelated recordings).
	check_eq(int(placed.row[StoredItemFlow.ROW_SLOT_TIMESTAMP]),
		_captured_row_instant(),
		"the double's row instant is the capture's recorded instant, byte for "
		+ "byte, so it never reads its own clock")
	check_eq(placed.garrison, [],
		"the placed row's garrison is always empty")
	check_eq(placed.attr, {},
		"a unit's placed row carries an empty bag, as 0 of 429 committed units "
		+ "seed either derived key")
	check_eq(placed.player, 1, "the placed row's team is always 1")
	check_eq(placed.attr_derived_from, [],
		"an empty bag has no derived field to report")
	check_eq(placed.count_before, 1, "the stock before the placement is 1")
	check_eq(placed.count_after, 0, "the stock after the placement is 0")
	check_eq(placed.consumed, 1, "one unit was consumed")
	check_eq(placed.ledger_before, [], "the captured ledger starts empty")
	check_eq(placed.ledger_after, [CAPTURED_ITEM],
		"the placement appended exactly the one placed id to the ledger")
	check_eq(bool(placed.ledger_gained), true, "the ledger gained the id")
	check_eq(bool(placed.credited), false, "the placement credited nothing")
	check_eq(bool(placed.bounds_refused), false,
		"bounds were recorded, not refused")
	check_eq(bool(placed.cell_occupancy_refused), false,
		"cell occupancy was recorded, not refused")
	check(placed.geometry_note.find("RECORDED, NOT REFUSED") >= 0,
		"the typed result carries the recorded geometry note")
	check(placed.slot_rule.find("DERIVED SERVER-SIDE") >= 0,
		"the typed result carries the slot rule")
	check(placed.resources != null, "the placement carries a complete resource set")
	for name: String in RESOURCE_KEYS:
		check(int(placed.resources.get(name)) >= 0,
			"the placement reports a non-negative %s" % name)
	# Placing consumes the stock, so a second placement of the same id is refused.
	var second: BootData.StoredPlacementResult = placer.place_stored_item_town(
		_fixture_pid(), CAPTURED_ITEM, 10, 10)
	check(not bool(second.ok), "a placement with no stock left is refused")
	check_eq(second.error_code, "not_in_storage",
		"placing an item no longer in storage is refused not_in_storage")
	# ...and a sale of it too.
	var sold_gone: BootData.StoredSaleResult = placer.sell_stored_item_town(
		_fixture_pid(), CAPTURED_ITEM)
	check(not bool(sold_gone.ok),
		"selling an item whose stock is exhausted is refused")
	check_eq(sold_gone.error_code, "not_in_storage",
		"selling an item no longer in storage is refused not_in_storage")

	# Sale first, then placement: the mirror ordering of the same round trip.
	var seller := FakeApi.new()
	root.add_child(seller)
	var sold_first: BootData.StoredSaleResult = seller.sell_stored_item_town(
		_fixture_pid(), CAPTURED_ITEM)
	check(bool(sold_first.ok), "the double sells the captured stored item")
	check_eq(bool(sold_first.credited), false, "a sale credits nothing")
	check_eq(sold_first.refund, 0, "a sale refunds nothing")
	check_eq(sold_first.count_before, 1, "the stock before the sale is 1")
	check_eq(sold_first.count_after, 0, "the stock after the sale is 0")
	check_eq(bool(sold_first.ledger_untouched), true,
		"a sale leaves the purchase ledger alone")
	check_eq(sold_first.storage_before, {PRIZE_UNIT: 1},
		"the sale reports the storage it read")
	check_eq(sold_first.storage_after, {},
		"the sale removed exactly the one storage entry")
	check(sold_first.quantity_rule.find("EXACTLY ONE") >= 0,
		"the sale reports the quantity rule")
	check(sold_first.resources != null, "the sale carries a complete resource set")
	for name: String in RESOURCE_KEYS:
		check(int(sold_first.resources.get(name)) >= 0,
			"the sale reports a non-negative %s" % name)
	var after_sale: BootData.StoredPlacementResult = seller.place_stored_item_town(
		_fixture_pid(), CAPTURED_ITEM, 10, 10)
	check(not bool(after_sale.ok),
		"placing an item already sold is refused")
	check_eq(after_sale.error_code, "not_in_storage",
		"placing a sold item is refused not_in_storage")

	# The three refusals the double can reach through its own inputs.
	var unknown := FakeApi.new()
	root.add_child(unknown)
	var unknown_id := unknown.place_stored_item_town(
		_fixture_pid(), 999999, 5, 5)
	check(not bool(unknown_id.ok),
		"placing an id no committed content defines is refused")
	check_eq(unknown_id.error_code, "unknown_item_id",
		"an unknown item id is refused unknown_item_id")
	var missing_user := unknown.place_stored_item_town(
		"", CAPTURED_ITEM, 5, 5)
	check(not bool(missing_user.ok), "an empty save identity is refused")
	check_eq(missing_user.error_code, "missing_user_id",
		"an empty save identity is refused missing_user_id")
	var wrong_user := unknown.place_stored_item_town(
		"not-the-captured-save", CAPTURED_ITEM, 5, 5)
	check_eq(wrong_user.error_code, "unknown_user_id",
		"an unknown save identity is refused unknown_user_id")
	var sale_unknown := unknown.sell_stored_item_town("", CAPTURED_ITEM)
	check_eq(sale_unknown.error_code, "missing_user_id",
		"the sale refuses an empty save identity too")
	var sale_no_stock := unknown.sell_stored_item_town(_fixture_pid(), 999999)
	check_eq(sale_no_stock.error_code, "not_in_storage",
		"selling an id no stock holds is refused not_in_storage")

	# `slot_occupied` is unreachable through an honest corpus, which is precisely
	# why it is a second line of defence; the double still names it.
	var occupied_helper := _code_only(FileAccess.get_file_as_string(
		"res://scripts/gameapi/fake_api.gd"))
	check(occupied_helper.contains("_stored_slot_occupied"),
		"the double keeps the slot rule's named inverse reachable")

	_report["fixture"] = {
		"pid": _fixture_pid(),
		"captured_item": CAPTURED_ITEM,
		"captured_item_name": CAPTURED_ITEM_NAME,
		"captured_cell": CAPTURED_CELL.duplicate(),
		"captured_slot": CAPTURED_SLOT,
		"committed_placements": COMMITTED_PLACEMENTS,
		"seed_collection": SEED_COLLECTION,
		"placement_row": (placed.row as Array).duplicate(),
		"placement_server_time_is_positive": placed.server_time > 0,
		"placement_count": [placed.count_before, placed.count_after],
		"placement_ledger": [placed.ledger_before.duplicate(),
			placed.ledger_after.duplicate()],
		"sale_count": [sold_first.count_before, sold_first.count_after],
		"sale_storage": [sold_first.storage_before.duplicate(),
			sold_first.storage_after.duplicate()],
		"sale_credited": bool(sold_first.credited),
		"sale_refund": sold_first.refund,
	}


# --- the operations both implementations declare ---------------------------

func _check_api_shape() -> void:
	for source: String in ["res://scripts/gameapi/legacy_v0_api.gd",
			"res://scripts/gameapi/fake_api.gd"]:
		var code := _code_only(FileAccess.get_file_as_string(source))
		for operation: String in REQUIRED_OPERATIONS:
			check(code.contains("func %s(" % operation),
				"%s declares '%s'" % [source, operation])
	var facade := _code_only(FileAccess.get_file_as_string(
		"res://scripts/gameapi/game_api.gd"))
	for operation: String in REQUIRED_OPERATIONS:
		check(facade.contains("func %s(" % operation),
			"the GameApi facade forwarder '%s' is declared" % operation)
		check(facade.contains("await _impl.%s(" % operation),
			"the facade forwarder '%s' delegates to the selected implementation"
				% operation)
	check(facade.contains("var stored_placement_requests := 0"),
		"the facade counts placement intents, like every other delivered intent")
	check(facade.contains("var stored_sale_requests := 0"),
		"the facade counts sale intents")
	# The live implementation must send ONLY the intent keys. Read the RAW text
	# here (not `_code_only`, which blanks string content): the question is which
	# KEYS the request bodies name, and a string literal IS that key.
	var live := FileAccess.get_file_as_string(
		"res://scripts/gameapi/legacy_v0_api.gd")
	for key: String in StoredItemFlow.PLACE_INTENT_KEYS:
		check(live.contains("\"%s\":" % key),
			"the live placement request carries '%s'" % key)
	check(live.contains("const STORED_PLACE_PATH := \"/v0/place_stored\""),
		"the live placement posts to the documented path")
	check(live.contains("const STORED_SELL_PATH := \"/v0/sell_stored\""),
		"the live sale posts to the documented path")
	# No outcome key may be sent by the two STORED-item request bodies. Scoped to
	# those two function bodies, because this same transport legitimately sends
	# `item_index` on the move, sell, store, upgrade, and construction routes --
	# a whole-file scan would report those and say nothing about this line.
	var stored_bodies := _function_body(live, "place_stored_item_town") \
			+ _function_body(live, "sell_stored_item_town")
	check(not stored_bodies.is_empty(),
		"the two live stored-item request bodies are locatable in the transport")
	for key: String in ["map_key", "item_index", "attr", "player", "quantity",
			"price", "resources", "timestamp", "store", "refund", "cost"]:
		check(not _request_body_keys(stored_bodies, key),
			"the live stored-item request bodies send no '%s' key: it is derived "
			% key + "or refused")
	# The fake must synthesize the SAME envelope the service sends, so the shared
	# parser yields one typed shape by construction (design D8).
	var fake := FileAccess.get_file_as_string(
		"res://scripts/gameapi/fake_api.gd")
	for key: String in ["placement", "row", "quantity", "storage_before",
			"storage_after", "ledger_before", "ledger_after", "geometry",
			"sale", "resources"]:
		check(fake.contains("\"%s\":" % key),
			"the double synthesizes the '%s' block the service sends" % key)
	check(fake.contains("BootData.parse_stored_placement("),
		"the double's placement goes through the SHARED parser")
	check(fake.contains("BootData.parse_stored_sell("),
		"the double's sale goes through the SHARED parser")
	check(live.contains("BootData.parse_stored_placement("),
		"the live placement goes through the SHARED parser")
	check(live.contains("BootData.parse_stored_sell("),
		"the live sale goes through the SHARED parser")


# --- the anti-invention guard ----------------------------------------------

func _check_absence() -> void:
	var declarations := _declarations(DELIVERED_FLOW_SCRIPT)
	var found: Array = []
	for entry: Dictionary in declarations:
		found.append(str(entry["name"]))
	found.sort()
	var expected: Array = EXPECTED_FLOW_METHODS.duplicate()
	expected.sort()
	check_eq(found, expected,
		"the delivered module declares EXACTLY its projection, mirror, "
		+ "evaluation, and readout accessors -- a bounds, capacity, expiry, value, "
		+ "price, refund, occupancy, or slot-derivation helper would appear here "
		+ "and fail the run")
	for helper: String in FORBIDDEN_HELPERS:
		check(not found.has(helper),
			"no '%s' helper is declared: the legacy server has no such rule" % helper)
		check(not _code_only(FileAccess.get_file_as_string(DELIVERED_FLOW_SCRIPT))
			.contains("static func %s(" % helper),
			"the module declares no '%s' function in any form" % helper)
		# A SUFFIXED name is the same helper wearing a disguise: `refund_for`
		# invents exactly the refund rule `refund` names, and an exact-match-only
		# guard would miss it -- which it did, until this check was added after
		# an injection of `refund_for` tripped the inventory pin and NOTHING
		# else. Recorded rather than quietly fixed: the by-name guard is weaker
		# than it looks, and the whole-inventory pin above is the real gate.
		var disguised: Array = []
		for name: String in found:
			if name != helper and name.contains(helper):
				disguised.append(name)
		check(disguised.is_empty(),
			"no declared helper hides '%s' under a suffixed name: %s"
				% [helper, str(disguised)])
	# The recorded absences name each one with its reason.
	var absent: Array = StoredItemFlow.ABSENT_HELPERS
	check_eq(absent.size(), FORBIDDEN_HELPERS.size(),
		"the recorded ABSENT_HELPERS list names exactly as many helpers as the "
		+ "suite forbids")
	for entry: Dictionary in absent:
		var helper := str(entry["helper"])
		check(FORBIDDEN_HELPERS.has(helper),
			"the recorded absent helper '%s' is one the suite forbids" % helper)
		check(str(entry["absent_because"]).strip_edges() != "",
			"the recorded absent helper '%s' states why its absence is mandatory"
				% helper)
	# The delivered module is PURE: no node, clock, request, or transport.
	var body := _code_only(FileAccess.get_file_as_string(DELIVERED_FLOW_SCRIPT))
	for needle: String in ["HTTP" + "Request", "HTTP" + "Client", "OS.",
			"Time.", "Engine", "get_tree", "request(", "await "]:
		check(not body.contains(needle),
			"the delivered module names no %s: it is pure" % needle)
	check(not body.contains("preload("),
		"the delivered module preloads nothing: it reads no registry and no "
		+ "service, so it cannot disagree with one")
	# The no-Flash gate in the client's own terms.
	check(not body.contains("swf") and not body.contains("flash"),
		"the delivered module names no Flash runtime or SWF")
	_report["methods"] = found


# --- the committed legacy source ------------------------------------------

func _check_legacy() -> void:
	var command_lines := _legacy_lines("command.py")
	var engine_lines := _legacy_lines("engine.py")
	check(command_lines.size() > LEGACY_PLACE_BRANCH_END,
		"the committed command.py is longer than the recorded branch")
	check(engine_lines.size() > LEGACY_Bought_UNIT_ADD_END,
		"the committed engine.py is longer than the recorded helper")
	# Both branches, at the recorded lines.
	var place_branch := _slice(command_lines, LEGACY_PLACE_BRANCH_START,
		LEGACY_PLACE_BRANCH_END)
	var sell_branch := _slice(command_lines, LEGACY_SELL_BRANCH_START,
		LEGACY_SELL_BRANCH_END)
	check(place_branch.find("place_stored_item") >= 0,
		"the placement branch starts at command.py:%d, as recorded"
			% LEGACY_PLACE_BRANCH_START)
	check(place_branch.find("map_add_item") >= 0,
		"the placement branch is the one that calls map_add_item")
	check(place_branch.find("remove_store_item") >= 0,
		"the placement branch is the one that calls remove_store_item")
	check(place_branch.find("bought_unit_add") >= 0,
		"the placement branch is the one that calls bought_unit_add")
	check(sell_branch.find("sell_stored_item") >= 0,
		"the sale branch starts at command.py:%d, as recorded"
			% LEGACY_SELL_BRANCH_START)
	check(sell_branch.find("remove_store_item") >= 0,
		"the sale branch is the one that calls remove_store_item")
	check(sell_branch.find("map_add_item") < 0,
		"the sale branch adds no placement, which is why its entire effect is one "
		+ "storage key disappearing")
	check(sell_branch.find("bought_unit_add") < 0,
		"the sale branch touches no ledger")
	check(sell_branch.find("resources") < 0,
		"the sale branch reads no price, so a sale credits nothing")
	# The four trailing arguments. Each appears on exactly ONE line **inside the
	# branch**, which is the scope in which the claim was measured: `args[4]` and
	# `args[5]` are also read by six other branches, so a whole-file count would
	# be false, while the two `unknown_*` names are globally unique.
	for argument: String in ["playerID", "orientation", "autoactivable", "imgIndex"]:
		var index := _arg_index(argument)
		var sites: Array = _sites(command_lines, "args[%d]" % index)
		var inside := 0
		for line_number: int in sites:
			if line_number >= LEGACY_PLACE_BRANCH_START \
					and line_number <= LEGACY_PLACE_BRANCH_END:
				inside += 1
		check_eq(inside, 1,
			"the recorded argument 'args[%d] %s' is read on exactly one line inside "
			% [index, argument]
			+ "the branch (command.py:%d), its own assignment" % _arg_line(argument))
	check_eq(_sites(command_lines, "unknown_autoactivable_bool").size(), 1,
		"the discarded argument name `unknown_autoactivable_bool` is globally "
		+ "unique: it exists only on its own assignment line")
	check_eq(_sites(command_lines, "unknown_imgIndex").size(), 1,
		"the discarded argument name `unknown_imgIndex` is globally unique")
	check(_sites(command_lines, "args[4]").size() > 1,
		"args[4] is read by other branches too, which is why the single-line "
		+ "claim is branch-scoped and not whole-file")
	# `playerID` is read and never passed on; `orientation` is read and passed
	# once. That difference is exactly why the team is derived and the
	# orientation is the client's.
	var pass_on := _slice(command_lines, LEGACY_PLACE_BRANCH_END - 4,
		LEGACY_PLACE_BRANCH_END)
	check(pass_on.find("map_add_item") >= 0,
		"the branch's last call is map_add_item, at command.py:%d"
			% LEGACY_PLACE_BRANCH_END)
	check(pass_on.find("orientation=orientation") >= 0,
		"only orientation is passed on, so a client-sent playerID is discarded "
		+ "and the team is always 1")
	check(pass_on.find("playerID") < 0,
		"playerID is never passed to map_add_item, which is why the derived team "
		+ "is 1 whatever the client sends")
	# apply_resources runs BEFORE the dispatcher, so a client-sent delta on this
	# branch could mint resources -- which is why the derived vector is neutral.
	var apply_line := _line_with(command_lines, "apply_resources(")
	check(apply_line > 0, "command.py calls apply_resources")
	check_eq(apply_line, LEGACY_APPLY_RESOURCES_LINE,
		"the apply_resources call is at command.py:%d, as recorded"
			% LEGACY_APPLY_RESOURCES_LINE)
	var branch_line := _line_with(command_lines, "\"place_stored_item\"")
	check(branch_line == LEGACY_PLACE_BRANCH_START,
		"the placement branch is the one at command.py:%d, as recorded"
			% LEGACY_PLACE_BRANCH_START)
	check(apply_line < branch_line,
		"apply_resources is applied BEFORE the stored-placement dispatch, which is "
		+ "why a client-sent vector on this branch could mint resources")
	# The store conditional: an absent item is a silent no-op, which is why
	# not_in_storage is a refusal rather than a parity claim.
	check(engine_lines.size() > LEGACY_STORE_CONDITIONAL_LINE,
		"the committed engine.py is longer than the recorded conditional")
	var conditional := _slice(engine_lines, LEGACY_STORE_CONDITIONAL_LINE - 2,
		LEGACY_STORE_CONDITIONAL_LINE + 2)
	check(conditional.find("itemstr in map[\"store\"]") >= 0
		or conditional.find("itemstr in map['store']") >= 0
		or conditional.find("store") >= 0,
		"remove_store_item's `if itemstr in map[\"store\"]` conditional is at "
		+ "engine.py:%d, as recorded" % LEGACY_STORE_CONDITIONAL_LINE)
	# The row writer is a bare assignment, with no occupancy test.
	check(engine_lines.size() > LEGACY_MAP_ADD_ITEM_LINE,
		"the committed engine.py is longer than the recorded assignment")
	var assignment := _slice(engine_lines, LEGACY_MAP_ADD_ITEM_LINE,
		LEGACY_MAP_ADD_ITEM_LINE + 1)
	check(assignment.find("items") >= 0 and assignment.find("=") >= 0,
		"map_add_item's row assignment is at engine.py:%d, as recorded"
			% LEGACY_MAP_ADD_ITEM_LINE)
	# The ledger appends only when the id is absent.
	var ledger := _slice(engine_lines, LEGACY_Bought_UNIT_ADD_END - 6,
		LEGACY_Bought_UNIT_ADD_END)
	check(ledger.find("bought_unit_add") >= 0 or ledger.find("not in") >= 0
		or ledger.find("append") >= 0,
		"bought_unit_add's append-if-absent rule ends at engine.py:%d, as recorded"
			% LEGACY_Bought_UNIT_ADD_END)
	# The three recorded command names exist in the dispatcher and nowhere else
	# as a branch.
	check_eq(_branch_count(command_lines, "place_stored_item"), 1,
		"the committed dispatcher has exactly one place_stored_item branch")
	check_eq(_branch_count(command_lines, "sell_stored_item"), 1,
		"the committed dispatcher has exactly one sell_stored_item branch")


# --- the committed executed-legacy capture --------------------------------

func _check_fixture() -> void:
	var place_before := _fixture_document(PLACE_BEFORE)
	var place_after := _fixture_document(PLACE_AFTER)
	var sell_before := _fixture_document(SELL_BEFORE)
	var sell_after := _fixture_document(SELL_AFTER)
	if place_before.is_empty() or place_after.is_empty() \
			or sell_before.is_empty() or sell_after.is_empty():
		fail("the committed storage-round-trip capture is readable in full")
		return
	var before_map := _map_of(place_before)
	var after_map := _map_of(place_after)
	var sell_before_map := _map_of(sell_before)
	var sell_after_map := _map_of(sell_after)
	check(before_map.has("items") and after_map.has("items"),
		"the capture's placement states carry an items map")
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), COMMITTED_PLACEMENTS,
		"the capture's before-state holds exactly 40 placements")
	check_eq(after_items.size(), COMMITTED_PLACEMENTS + 1,
		"the capture's placement grew the placement count by exactly one")
	var added: Array = []
	for key: Variant in after_items:
		if not before_items.has(str(key)):
			added.append(str(key))
	check_eq(added.size(), 1, "the capture added exactly one row")
	check_eq(added[0], str(CAPTURED_SLOT),
		"the capture's derived first free slot is 41, over keys 1..40")
	var row: Array = after_items[str(CAPTURED_SLOT)]
	check_eq(row.size(), StoredItemFlow.ROW_SLOT_COUNT,
		"the captured row carries all eight slots")
	check_eq(int(row[StoredItemFlow.ROW_SLOT_ITEM]), CAPTURED_ITEM,
		"the captured row's item is the collection 1 prize")
	check_eq([int(row[StoredItemFlow.ROW_SLOT_X]), int(row[StoredItemFlow.ROW_SLOT_Y])],
		CAPTURED_CELL, "the captured row's cell is the requested one")
	check(int(row[StoredItemFlow.ROW_SLOT_TIMESTAMP]) > 0,
		"the captured row's instant is a positive wall-clock reading, which is "
		+ "why the capture's after.json is not byte-stable across reruns")
	check_eq(int(row[StoredItemFlow.ROW_SLOT_ORIENTATION]), 0,
		"the captured row's orientation is the derived 0")
	check_eq((row[StoredItemFlow.ROW_SLOT_STORE] as Array).size(), 0,
		"the captured row's garrison is empty")
	check_eq((row[StoredItemFlow.ROW_SLOT_ATTR] as Dictionary).size(), 0,
		"the captured row's bag is empty, as 0 of 429 committed units seed one")
	check_eq(int(row[StoredItemFlow.ROW_SLOT_PLAYER]), 1,
		"the captured row's team is 1, never the client-sent playerID")
	# The storage, the ledger, and the seven balances.
	check_eq(before_map["store"], {PRIZE_UNIT: 1},
		"the capture's before-state holds the committed prize in storage")
	check_eq(after_map["store"], {},
		"the placement removed exactly the one storage entry")
	check_eq(_bought_units(place_before), [],
		"the capture's ledger starts empty")
	check_eq(_bought_units(place_after), [CAPTURED_ITEM],
		"the placement appended exactly one ledger id")
	check_eq(_resources_of(place_before), _resources_of(place_after),
		"placing a stored item moved NO stored resource, which is what makes the "
		+ "endpoint's no-resource-moved proof non-tautological")
	# The sale: exactly one storage leaf changed, nothing else.
	var changed := _changed_leaf_paths(sell_before, sell_after)
	check_eq(changed.size(), 1,
		"the captured sale changed exactly one leaf: " + str(changed))
	check_eq(str(changed[0]), "maps[0].store.%s" % PRIZE_BUILDING,
		"the only leaf the captured sale changed is the storage entry it removed")
	check_eq(sell_before_map["store"], {PRIZE_BUILDING: 1},
		"the capture's sale starts from the second committed prize in storage")
	check_eq(sell_after_map["store"], {},
		"the sale removed exactly the one storage entry")
	check_eq(sell_before_map["items"], sell_after_map["items"],
		"the sale added and removed no placement")
	check_eq(_resources_of(sell_before), _resources_of(sell_after),
		"selling a stored item credited NOTHING, which is what makes the "
		+ "endpoint's no-resource-moved proof non-tautological")
	# The capture CHAINED the only content-derived seeding route.
	var manifest := _fixture_document(
		"tests/fixtures/godot-stored-item-placement/capture-manifest.json")
	check(not manifest.is_empty(), "the capture manifest is committed")
	if not manifest.is_empty():
		var text := JSON.stringify(manifest)
		check(text.find("complete_collection") >= 0,
			"the capture manifest records the chained collection seeding")
		check(text.find("store_add_items") >= 0,
			"the capture manifest names store_add_items, and records it as PROBE-ONLY "
			+ "rather than as a seeding route: it is an unvalidated client-sent grant")
		check_eq(int(manifest.get("exit_code", 1)), 0,
			"the capture exited 0 and is re-runnable")
	_check_collection_prizes()


## The two committed prizes this line reasons about. Both are units, which is
## why both place with an empty bag; four of the ten committed prizes are
## BUILDINGS, which is why the building-prize path seeds `{"nc": 0}`.
func _check_collection_prizes() -> void:
	var path := Paths.repo_root().path_join(
		"packages/game-content/normalized/collections.json")
	if not FileAccess.file_exists(path):
		fail("the committed normalized collections table is readable")
		return
	var parsed: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(path))
	if not (parsed is Array):
		fail("the committed collections table is a list")
		return
	var rows: Array = parsed
	var found := {}
	var building_prizes := 0
	var unit_prizes := 0
	var classified := 0
	for entry: Variant in rows:
		if not (entry is Dictionary):
			continue
		var row: Dictionary = entry
		var prize: Variant = row.get("prize")
		if not (prize is Dictionary) or (prize as Dictionary).is_empty():
			continue
		classified += 1
		for id: Variant in (prize as Dictionary).keys():
			found[str(id)] = true
			if _domain_of(str(id)) == "buildings":
				building_prizes += 1
			else:
				unit_prizes += 1
	check_eq(rows.size(), EXPECTED_COLLECTION_COUNT,
		"the committed package holds exactly 10 collections")
	check_eq(classified, EXPECTED_COLLECTION_COUNT,
		"every committed collection carries a non-empty prize bag")
	check(found.has(PRIZE_UNIT),
		"collection 1's committed prize is the placed unit %s" % PRIZE_UNIT)
	check(found.has(PRIZE_BUILDING),
		"collection 2's committed prize is the sold unit %s" % PRIZE_BUILDING)
	check_eq(building_prizes, 4,
		"exactly four of the ten committed collection prizes are BUILDINGS, so "
		+ "the delivered line ships on a 1x1 unit prize and the 2x2/3x3 building "
		+ "prizes remain blocked on the recorded geometry gap")
	check_eq(unit_prizes, EXPECTED_COLLECTION_COUNT - 4,
		"the remaining six committed collection prizes are UNITS, which is why "
		+ "both captured transactions place and sell an item with an empty bag")
	# Every prize id resolves against the committed items, and a UNIT prize can
	# never seed a derived key -- so the delivered line's empty-bag reading is
	# a property of the content, not an accident of the capture.
	for id: Variant in (found as Dictionary).keys():
		var resolved := _by_legacy_id(str(id))
		check(not resolved.is_empty(),
			"committed prize %s resolves against the 900 committed items" % str(id))
		if _domain_of(str(id)) == "units":
			check_eq(StoredItemFlow.derive_attr(resolved.get("clicks_to_build"),
				resolved.get("properties"))["attr"], {},
				"a unit prize %s derives an empty bag, so its placement is "
				% str(id) + "content-shaped")


# --- boundary: who may name the stored-placement command -------------------

func _check_boundary() -> void:
	var sources := _client_sources()
	check(sources.size() > 0, "the client source tree is walkable")
	var offenders: Array = []
	for source: String in sources:
		var code := _code_only(FileAccess.get_file_as_string(source))
		var names_place := code.contains(StoredItemFlow.PLACE_COMMAND)
		var names_sell := code.contains(StoredItemFlow.SELL_COMMAND)
		if not (names_place or names_sell):
			continue
		if not STORAGE_OWNERS.has(source):
			offenders.append(source)
	check_eq(offenders.size(), 0,
		"only the owned files declare the storage command tokens in code: "
		+ str(offenders))
	for owner: String in STORAGE_OWNERS:
		check(sources.has(owner), "the ownership list names a real source: %s" % owner)
	# The delivered module assembles the names from fragments, so the
	# collection suite's needle cannot be tripped by this line's own constants.
	var flow_code := _code_only(FileAccess.get_file_as_string(DELIVERED_FLOW_SCRIPT))
	check(not flow_code.contains(StoredItemFlow.PLACE_COMMAND),
		"the delivered module assembles the placement token from fragments")
	check(not flow_code.contains(StoredItemFlow.SELL_COMMAND),
		"the delivered module assembles the sale token from fragments")


# --- content loading -------------------------------------------------------

func _load_committed_items() -> void:
	for name: String in CONTENT_FILES:
		var path := Paths.repo_root().path_join(
			"packages/game-content/normalized/%s.json" % name)
		if not FileAccess.file_exists(path):
			_content_error = "missing committed content file: %s" % name
			return
		var parsed: Variant = JSON.parse_string(
			FileAccess.get_file_as_string(path))
		if not (parsed is Array):
			_content_error = "committed content file %s is not a list" % name
			return
		for entry: Variant in (parsed as Array):
			if not (entry is Dictionary):
				_content_error = "committed content row in %s is not an object" % name
				return
			_items.append({"__domain": name, "row": entry})


func _by_legacy_id(legacy_id: String) -> Dictionary:
	for entry: Dictionary in _items:
		var row: Dictionary = entry["row"]
		if str(row.get("legacy_id", "")) == legacy_id:
			return row
	return {}


## Which committed domain one legacy id belongs to: `buildings`, `units`, or
## `specials`. Empty when the id resolves to nothing.
func _domain_of(legacy_id: String) -> String:
	for entry: Dictionary in _items:
		var row: Dictionary = entry["row"]
		if str(row.get("legacy_id", "")) == legacy_id:
			return str(entry["__domain"])
	return ""


## The recorded slot-3 instant of the capture's placed row, read straight off
## the committed after-state.
func _captured_row_instant() -> int:
	var document := _fixture_document(PLACE_AFTER)
	var items: Variant = _map_of(document).get("items", {})
	if not (items is Dictionary):
		return -1
	var entry: Variant = (items as Dictionary).get(str(CAPTURED_SLOT))
	if not (entry is Array) or (entry as Array).size() != 8:
		return -1
	return int((entry as Array)[StoredItemFlow.ROW_SLOT_TIMESTAMP])


# --- small pure readers ----------------------------------------------------

## One committed flag read as an integer, INDEPENDENTLY of the module under
## test: the normalized package stores these as strings, so the committed "0"
## must stay 0 rather than being treated as a truthy String.
func _flag(properties: Variant, key: String) -> int:
	if not (properties is Dictionary):
		return 0
	var value: Variant = (properties as Dictionary).get(key, null)
	if value == null or value is bool:
		return 0
	if value is int:
		return int(value)
	if value is String:
		var text := str(value).strip_edges()
		if text.is_valid_int():
			return int(text)
		return 1
	return 0


## One committed count read as a whole number, failing closed to 0.
func _whole(value: Variant) -> int:
	if value == null or value is bool:
		return 0
	if value is int:
		return int(value)
	if value is float:
		return int(value) if float(value) == floor(float(value)) else 0
	if value is String:
		var text := str(value).strip_edges()
		return int(text) if text.is_valid_int() else 0
	return 0


## The SERVICE's placeability predicate, recomputed independently: a row
## carrying neither properties nor clicks_to_build.
func _placeable(properties: Variant, clicks_to_build: Variant) -> bool:
	if properties is Dictionary and not (properties as Dictionary).is_empty():
		return true
	if properties is String and str(properties).strip_edges() != "":
		return true
	return _whole(clicks_to_build) > 0


## Which of the three measured bag shapes a sorted key list denotes.
func _bag_shape(keys: Array) -> String:
	if keys.is_empty():
		return "empty"
	if keys.size() == 1 and keys[0] == StoredItemFlow.ATTR_CLICKS_KEY:
		return "clicks"
	return "both"


func _codes_of(entries: Array) -> Array:
	var out: Array = []
	for entry: Dictionary in entries:
		out.append(str(entry["code"]))
	out.sort()
	return out


func _row_slot_table() -> Array:
	var out: Array = []
	for index: int in StoredItemFlow.ROW_SLOTS:
		out.append({
			"slot": index,
			"name": StoredItemFlow.ROW_SLOT_NAMES[index],
			"server_owned": StoredItemFlow.SERVER_OWNED_SLOTS.has(index),
		})
	return out


# --- declarations ----------------------------------------------------------

## Every `func` declaration in a source, with its parameter names, parsed from
## the CODE-ONLY text so a parameter named inside a string cannot be counted.
func _declarations(source: String) -> Array:
	var out: Array = []
	var code := _code_only(FileAccess.get_file_as_string(source))
	var lines := code.split("\n")
	for index in range(lines.size()):
		var line := str(lines[index])
		var at := line.find("func ")
		if at < 0:
			continue
		var header := line.substr(at + 5)
		var paren := header.find("(")
		if paren < 0:
			continue
		var name := header.substr(0, paren).strip_edges()
		var depth := 0
		var parameters: Array = []
		var current := ""
		var started := false
		var cursor := paren
		while cursor < header.length():
			var character := header[cursor]
			if character == "(":
				depth += 1
				if depth == 1:
					started = true
					cursor += 1
					continue
			elif character == ")":
				depth -= 1
				if depth == 0:
					if current.strip_edges() != "":
						parameters.append(current.strip_edges())
					break
			if started:
				if character == ",":
					if current.strip_edges() != "":
						parameters.append(current.strip_edges())
					current = ""
					cursor += 1
					continue
				current += character
			cursor += 1
		out.append({"name": name, "parameters": parameters,
			"line": index + 1})
	return out


# --- legacy source ---------------------------------------------------------

func _legacy_lines(module: String) -> Array:
	var path := Paths.repo_root().path_join(module)
	if not FileAccess.file_exists(path):
		return []
	return (FileAccess.get_file_as_string(path) as String).split("\n")


func _slice(lines: Array, first: int, last: int) -> String:
	var out: Array = []
	for number in range(maxi(1, first), mini(lines.size(), last) + 1):
		out.append(str(lines[number - 1]))
	return "\n".join(PackedStringArray(out))


func _line_with(lines: Array, needle: String) -> int:
	for index in range(lines.size()):
		if str(lines[index]).find(needle) >= 0:
			return index + 1
	return -1


## The recorded argument index of each name, and the line its single branch-
## scoped read is on.
func _arg_index(name: String) -> int:
	match name:
		"playerID":
			return 4
		"orientation":
			return 5
		"autoactivable":
			return 6
		_:
			return 7


func _arg_line(name: String) -> int:
	match name:
		"playerID":
			return 238
		"orientation":
			return 239
		"autoactivable":
			return 240
		_:
			return 241


## Every line number naming `needle` in the committed legacy source.
func _sites(lines: Array, needle: String) -> Array:
	var out: Array = []
	for index in range(lines.size()):
		if str(lines[index]).find(needle) >= 0:
			out.append(index + 1)
	return out


## How many `elif name == ...` dispatcher branches name this command.
func _branch_count(lines: Array, name: String) -> int:
	var count := 0
	for index in range(lines.size()):
		var line := str(lines[index])
		if line.find("== \"%s\"" % name) >= 0 or line.find("=='%s'" % name) >= 0:
			count += 1
	return count


## The dispatcher line that routes the placement branch, for the
## before-dispatch ordering check.
func _placement_dispatch_line(lines: Array) -> int:
	var line := _line_with(lines, "place_stored_item")
	return line if line > 0 else maxi(lines.size(), 1)


## The text after the first mention of `needle`.
func _after_read(text: String, needle: String) -> String:
	var at := text.find(needle)
	if at < 0:
		return ""
	return text.substr(at + needle.length())


# --- the committed capture -------------------------------------------------

func _fixture_document(relative: String) -> Dictionary:
	var path := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return {}
	return _as_ints(parsed)


func _map_of(document: Dictionary) -> Dictionary:
	var maps: Variant = document.get("maps", [])
	if not (maps is Array) or (maps as Array).is_empty():
		return {}
	var first: Variant = (maps as Array)[0]
	return first as Dictionary if first is Dictionary else {}


func _bought_units(document: Dictionary) -> Array:
	var private: Variant = document.get("privateState", {})
	if not (private is Dictionary):
		return []
	var ledger: Variant = (private as Dictionary).get("boughtUnits", [])
	return ledger as Array if ledger is Array else []


## The seven STORED resources, exactly as `compat_legacy.resources()` reads them.
func _resources_of(document: Dictionary) -> Dictionary:
	var map := _map_of(document)
	var out := {}
	for key: String in ["xp", "gold", "wood", "oil", "steel"]:
		out[key] = int(map.get(key, 0))
	var private: Variant = document.get("privateState", {})
	var info: Variant = document.get("playerInfo", {})
	out["mana"] = int((private as Dictionary).get("mana", 0)) \
		if private is Dictionary else 0
	out["cash"] = int((info as Dictionary).get("cash", 0)) \
		if info is Dictionary else 0
	return out


## Every leaf whose value differs between two documents, as dotted paths. Used to
## prove the sale changed exactly one leaf rather than asserting a count alone.
##
## A **removed** key is a change, and it is the only kind a storage sale makes,
## so both key sets are walked: iterating only the after-state's keys would make
## every removal invisible, which is exactly the defect an earlier draft of this
## suite shipped. Indices render as `name[0]` so a path names the array it is in.
func _changed_leaf_paths(before: Variant, after: Variant,
		prefix: String = "") -> Array:
	var out: Array = []
	if before is Dictionary and after is Dictionary:
		var before_keys: Array = (before as Dictionary).keys()
		var after_keys: Array = (after as Dictionary).keys()
		var every: Array = before_keys.duplicate()
		for key: Variant in after_keys:
			if not every.has(key):
				every.append(key)
		every.sort()
		for key: Variant in every:
			var path := _join(prefix, str(key))
			if not before_keys.has(key):
				out.append(path)
				continue
			if not after_keys.has(key):
				out.append(path)
				continue
			out.append_array(_changed_leaf_paths(
				(before as Dictionary)[key], (after as Dictionary)[key], path))
		return out
	if before is Array and after is Array:
		if (before as Array).size() != (after as Array).size():
			out.append("%s[]" % prefix)
			return out
		for index in range((before as Array).size()):
			out.append_array(_changed_leaf_paths(
				(before as Array)[index], (after as Array)[index],
				"%s[%d]" % [prefix, index]))
		return out
	if JSON.stringify(before) != JSON.stringify(after):
		out.append(prefix)
	return out


## One dotted path segment, so a root key does not begin with a separator.
func _join(prefix: String, key: String) -> String:
	return key if prefix == "" else "%s.%s" % [prefix, key]


## Every integral float in a parsed JSON document narrowed to an int.
##
## The pinned engine's JSON transport decodes EVERY number as a float (probed on
## Godot 4.7.2 and recorded by `boot_data._parse_int`), so a committed capture
## read straight off disk arrives as `{"1085": 1.0}` and would never equal the
## committed `{"1085": 1}`. Narrowing here -- and only for integral values --
## keeps every byte-level claim in this suite about the RECORDED state rather
## than about the transport's widening, and leaves a genuine fractional value
## alone so a malformed capture cannot be rounded into agreement.
func _as_ints(value: Variant) -> Variant:
	if value is Dictionary:
		var out := {}
		for key: Variant in (value as Dictionary):
			out[key] = _as_ints((value as Dictionary)[key])
		return out
	if value is Array:
		var listed: Array = []
		for entry: Variant in (value as Array):
			listed.append(_as_ints(entry))
		return listed
	if value is float:
		var typed := float(value)
		return int(typed) if typed == floor(typed) else typed
	return value


func _fixture_pid() -> String:
	var document := _fixture_document(PLACE_BEFORE)
	var info: Variant = document.get("playerInfo", {})
	if info is Dictionary:
		return str((info as Dictionary).get("pid", ""))
	return ""


# --- the client source walk ------------------------------------------------

func _client_sources() -> Array:
	var out: Array = []
	for directory: String in ["res://scripts", "res://tests"]:
		_collect_gd(directory, out)
	out.sort()
	return out


func _collect_gd(directory: String, out: Array) -> void:
	var handle := DirAccess.open(directory)
	if handle == null:
		return
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if entry != "." and entry != "..":
			var full := directory.path_join(entry)
			if handle.current_is_dir():
				_collect_gd(full, out)
			elif str(entry).ends_with(".gd"):
				out.append(full)
		entry = handle.get_next()
	handle.list_dir_end()


## A source's DECLARATIONS: comment lines are dropped and string-literal content
## is blanked, so a prose mention or a recorded non-claim string can never be
## mistaken for code.
func _code_only(body: String) -> String:
	var lines := body.split("\n")
	var out: Array = []
	for line: String in lines:
		var stripped := line.strip_edges()
		if stripped.begins_with("#"):
			continue
		var without_strings := ""
		var inside := false
		for index in range(line.length()):
			var character := line[index]
			if character == "\"":
				inside = not inside
				continue
			without_strings += " " if inside else character
		out.append(without_strings)
	return "\n".join(PackedStringArray(out))


## The whole body of one `func` declaration, from its header to the next
## top-level declaration. Used to scope a claim to ONE function, because a
## whole-file scan on a shared transport says nothing about one route.
func _function_body(source: String, name: String) -> String:
	var lines := source.split("\n")
	var start := -1
	for index in range(lines.size()):
		if str(lines[index]).find("func %s(" % name) >= 0:
			start = index
			break
	if start < 0:
		return ""
	var out: Array = []
	for index in range(start, lines.size()):
		if index > start and str(lines[index]).begins_with("func "):
			break
		out.append(str(lines[index]))
	return "\n".join(PackedStringArray(out))


## Whether a set of request bodies names `key` as a JSON member. Scoped to the
## `JSON.stringify({...})` regions so a `key` named in a doc comment or in the
## refusal vocabulary cannot be mistaken for a sent field.
func _request_body_keys(bodies: String, key: String) -> bool:
	var marker := "\"%s\":" % key
	var at := bodies.find("JSON.stringify({")
	while at >= 0:
		var close := bodies.find("}))", at)
		if close < 0:
			return false
		if bodies.substr(at, close - at).find(marker) >= 0:
			return true
		at = bodies.find("JSON.stringify({", close)
	return false


# --- the report ------------------------------------------------------------

func _report_argument() -> String:
	for argument in OS.get_cmdline_user_args():
		var text := str(argument)
		if text.begins_with("--report="):
			return text.trim_prefix("--report=")
		if text == "--report":
			return DEFAULT_REPORT
	return ""


func _write_report() -> void:
	var path := _report_path
	if path.begins_with("res://") or path.find("://") >= 0:
		path = ProjectSettings.globalize_path(path)
	elif not path.is_absolute_path():
		path = Paths.repo_root().path_join(path)
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		fail("the report path is writable: " + path)
		return
	handle.store_string(JSON.stringify(_report, "  ", false) + "\n")
	handle = null
	info("report written %s" % path)


# The live-stored-placement phase (verify-boot's `stored-placement-live`)
# ---------------------------------------------------------------------------
#
# This line is the FIRST M9/M8 line whose live phase exercises a **working
# round trip** rather than a refusal, so the phase is written as a four-step
# sequence over the disposable corpus:
#
#   A  seed storage      complete_collection(1) -> the COMMITTED prize {1085: 1}
#   B  place it          place_stored_item(1085)  -> a NEW derived map slot
#   C  seed it again     complete_collection(1)   -> the ledger is NOT idempotent
#   D  sell it           sell_stored_item(1085)   -> the storage empties, no refund
#
# Step C exists because step B *consumes* the stored unit, so without it there is
# nothing left to sell and the sale half of the line would go unproven. Re-running
# the committed completion is the only content-derived way to put that unit back:
# `complete_collection` reads a committed prize and never checks the ledger, which
# `collection-live` already established, so the second grant is a real second
# write rather than a fabricated one.
#
# Every step asserts its typed response AND its post-state, and every step asserts
# that **all seven stored resources are unchanged** -- which is what makes this
# line's "placing is free and a sale refunds nothing" claim non-tautological. The
# phase harness separately asserts the corpus save file mutated.


## The committed collection whose prize seeds this phase's storage, and the
## committed prize it grants.
const LIVE_SEED_COLLECTION := 1
const LIVE_PRIZE_ID := "1085"
const LIVE_PRIZE_QUANTITY := 1
## The cell the committed capture places into. Reused here so the live phase and
## the fixture agree on one recorded cell; the endpoint derives no geometry, so
## the value is a recorded input, never a derived bound.
const LIVE_CELL_X := 58
const LIVE_CELL_Y := 47
## The seven stored balances the value-level proof compares.
const LIVE_RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana"]


func _check_live_stored_placement() -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the live phase")
	if endpoint == "":
		return
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("legacy_v0", endpoint)
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult, "the corpus save list resolves")
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)

	# --- the corpus's own state before anything ------------------------------
	# Read from the SERVICE, never from the fake: an empty storage is what makes
	# the grant in step A an observable write at all.
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(), "the corpus pre-placement payload resolves")
	if before_payload.is_empty():
		return
	var map_before: Dictionary = before_payload.get("map", {}) as Dictionary
	var items_before: Dictionary = map_before.get("items", {}) as Dictionary
	check_eq(_as_ints(map_before.get("store", {})), {},
		"the live corpus's storage is EMPTY before this phase, so the committed "
		+ "grant is an observable write")
	check(items_before.size() > 0, "the live corpus carries placements")
	var resources_before := _live_resources(before_payload)

	# --- A: seed the storage with the committed prize -----------------------
	var seeded: Variant = await api.complete_collection_town(pid,
		LIVE_SEED_COLLECTION)
	check(seeded is BootData.CollectionResult and bool(seeded.ok),
		"the content-derived seed is accepted by the real endpoint: %s"
			% str((seeded as BootData.CollectionResult).error_message
				if seeded is BootData.CollectionResult else ""))
	if not (seeded is BootData.CollectionResult and bool(seeded.ok)):
		return
	var seeded_store: Variant = _as_ints(
		(seeded as BootData.CollectionResult).store_after)
	check_eq(seeded_store, {LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
		"the seed granted EXACTLY the committed prize bag")
	var seeded_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check_eq(_as_ints(_live_map(seeded_payload).get("store", {})),
		{LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
		"the corpus's storage now holds exactly the committed prize")

	# --- B: place the stored unit ------------------------------------------
	var placed: Variant = await api.place_stored_item_town(pid,
		int(LIVE_PRIZE_ID), LIVE_CELL_X, LIVE_CELL_Y)
	check(placed is BootData.StoredPlacementResult and bool(placed.ok),
		"a placement is accepted by the real endpoint: %s"
			% str((placed as BootData.StoredPlacementResult).error_message
				if placed is BootData.StoredPlacementResult else ""))
	if not (placed is BootData.StoredPlacementResult and bool(placed.ok)):
		return
	var typed: BootData.StoredPlacementResult = placed
	_check_typed_placement_live(typed)
	check_eq(typed.item_id, int(LIVE_PRIZE_ID),
		"the service echoed the item id exactly as sent")
	# The DERIVED slot: the smallest positive integer absent from the map. The
	# corpus holds keys 1..40, so the derived key is 41 -- and the client never
	# sent one, so the only way this can hold is if the service derived it.
	var derived_key := items_before.size() + 1
	check_eq(typed.map_key, derived_key,
		"the map slot was DERIVED server-side from the corpus's own placements")
	check_eq(typed.x, LIVE_CELL_X, "the requested cell x is echoed")
	check_eq(typed.y, LIVE_CELL_Y, "the requested cell y is echoed")
	check_eq(typed.row.size(), 8, "the placed row carries all eight legacy slots")
	check_eq(int(typed.row[StoredItemFlow.ROW_SLOT_ITEM]), int(LIVE_PRIZE_ID),
		"row slot 0 carries the item id")
	check_eq(int(typed.row[StoredItemFlow.ROW_SLOT_X]), LIVE_CELL_X,
		"row slot 1 carries the requested cell x")
	check_eq(int(typed.row[StoredItemFlow.ROW_SLOT_Y]), LIVE_CELL_Y,
		"row slot 2 carries the requested cell y")
	check(int(typed.row[StoredItemFlow.ROW_SLOT_TIMESTAMP]) > 0,
		"row slot 3 is a wall-clock reading, asserted positively")
	check_eq(int(typed.row[StoredItemFlow.ROW_SLOT_ORIENTATION]),
		StoredItemFlow.DERIVED_ORIENTATION,
		"row slot 4 records the DERIVED orientation, not a client value")
	# The attribute bag, DERIVED from committed content. The prize is a UNIT and
	# no committed unit carries `clicks_to_build` or a `properties` flag, so the
	# bag is empty -- which is what `derive_attr` returns, not what the client
	# asked for.
	check_eq(_as_ints(typed.attr), {},
		"the derived attribute bag is EMPTY for a committed unit prize")
	check_eq((typed.attr_derived_from as Array).size(), 0,
		"an empty bag derives from no committed field")
	# The two-part post-execution proof the SERVICE reports, read rather than
	# assumed.
	check_eq(typed.consumed, 1, "the service reports consuming exactly one unit")
	check_eq(typed.count_before, LIVE_PRIZE_QUANTITY,
		"the service saw one unit in storage before the placement")
	check_eq(typed.count_after, 0,
		"the service saw the unit GONE from storage after the placement")
	check_eq(typed.count_before - typed.count_after, 1,
		"the storage fell by exactly the consumed quantity")
	check_eq(bool(typed.credited), false,
		"placing a stored item is FREE: the service credits nothing")
	check_eq(bool(typed.bounds_refused), false,
		"the service records the bounds gap rather than refusing it")
	check_eq(bool(typed.cell_occupancy_refused), false,
		"the service records the occupancy gap rather than refusing it")
	check_eq((_as_ints(typed.ledger_after) as Array).has(int(LIVE_PRIZE_ID)), true,
		"the placed unit is recorded in the bought-units ledger")
	# The value-level half of the free-placement claim.
	for name: String in LIVE_RESOURCE_NAMES:
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the placement" % name)

	var placed_payload: Dictionary = await _live_payload(api, endpoint, pid)
	var placed_map: Dictionary = placed_payload.get("map", {}) as Dictionary
	var placed_items: Dictionary = placed_map.get("items", {}) as Dictionary
	check_eq(placed_items.size(), items_before.size() + 1,
		"the placement count grew by EXACTLY one")
	check_eq(_as_ints(placed_map.get("store", {})), {},
		"the storage is EMPTY after the placement: the unit left storage")
	check(str(placed_items.get(str(derived_key), "")) != "",
		"the row is filed under the DERIVED key the response reported")

	# --- C: seed the same prize a second time -------------------------------
	# The ledger is NOT idempotent, so the second completion is a second real
	# grant. This is the only content-derived route back to a sellable unit.
	var reseeded: Variant = await api.complete_collection_town(pid,
		LIVE_SEED_COLLECTION)
	check(reseeded is BootData.CollectionResult and bool(reseeded.ok),
		"the same committed completion is accepted a second time")
	if reseeded is BootData.CollectionResult and bool(reseeded.ok):
		check_eq(_as_ints((reseeded as BootData.CollectionResult).store_after),
			{LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
			"the second grant is exactly one more unit of the same id")
		check_eq(bool((reseeded as BootData.CollectionResult).ledger_appended),
			false,
			"the ledger did NOT grow: the append is IF-ABSENT, so a repeat "
			+ "completion grants the prize AGAIN while the ledger stands still -- "
			+ "which is precisely why step D has something to sell")
		check_eq((_as_ints((reseeded as BootData.CollectionResult).ledger_after
				as Array)).size(),
			(_as_ints((seeded as BootData.CollectionResult).ledger_after
				as Array)).size(),
			"the ledger is byte-identical across the two completions")

	# --- D: sell the stored unit -------------------------------------------
	var sold: Variant = await api.sell_stored_item_town(pid,
		int(LIVE_PRIZE_ID))
	check(sold is BootData.StoredSaleResult and bool(sold.ok),
		"a sale is accepted by the real endpoint: %s"
			% str((sold as BootData.StoredSaleResult).error_message
				if sold is BootData.StoredSaleResult else ""))
	if not (sold is BootData.StoredSaleResult and bool(sold.ok)):
		return
	var sale: BootData.StoredSaleResult = sold
	_check_typed_sale_live(sale)
	check_eq(sale.item_id, int(LIVE_PRIZE_ID),
		"the service echoed the item id exactly as sent")
	check_eq(_as_ints(sale.storage_before), {LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
		"the response's before storage is the corpus's one-unit storage")
	check_eq(_as_ints(sale.storage_after), {},
		"the response's after storage is EMPTY: the sale removed the entry")
	# NO REFUND, and this is the line's sharpest claim: a sale removes the item
	# and moves no balance at all.
	check_eq(bool(sale.credited), false,
		"a sale CREDITS nothing: the legacy refund travels in client-sent deltas "
		+ "this contract refuses")
	check_eq(int(sale.refund), 0, "the reported refund is exactly zero")
	check_eq(bool(sale.ledger_untouched), true,
		"a sale leaves the bought-units ledger untouched")
	check_eq(int(sale.count_before), LIVE_PRIZE_QUANTITY,
		"the service saw one unit before the sale")
	check_eq(int(sale.count_after), 0, "the service saw none after the sale")
	for name: String in LIVE_RESOURCE_NAMES:
		check_eq(int((sale.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the sale: no refund is paid" % name)

	# --- the corpus after all four steps ------------------------------------
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	var after_map: Dictionary = after_payload.get("map", {}) as Dictionary
	check_eq(_as_ints(after_map.get("store", {})), {},
		"the live storage ends EMPTY: both transactions moved the whole unit")
	check_eq((after_map.get("items", {}) as Dictionary).size(),
		items_before.size() + 1,
		"the placement count stayed at 41: a sale is STORAGE-ONLY and never "
			+ "unplaces, so the row this phase placed is still on the map")
	check_eq(_live_resources(after_payload), resources_before,
		"every live corpus balance is byte-identical after all four steps")

	# --- the same intents through the fake, offline -------------------------
	# Both implementations must produce the same typed shapes and the same
	# derived row, with no process, server, or socket.
	api.configure("fake")
	var offline_place: Variant = await api.place_stored_item_town(pid,
		int(LIVE_PRIZE_ID), LIVE_CELL_X, LIVE_CELL_Y)
	check(offline_place is BootData.StoredPlacementResult
			and bool(offline_place.ok),
		"the fake accepts the same placement offline")
	if offline_place is BootData.StoredPlacementResult:
		check_eq(int((offline_place as BootData.StoredPlacementResult).map_key),
			typed.map_key,
			"both implementations DERIVE the same map slot from the same corpus")
		check_eq(_row_without_instant(
				(offline_place as BootData.StoredPlacementResult).row),
			_row_without_instant(typed.row),
			"both implementations place the SAME seven client-and-content slots, "
			+ "with slot 3 excluded because each is its own wall-clock reading")
		check(int((offline_place as BootData.StoredPlacementResult).row[
				StoredItemFlow.ROW_SLOT_TIMESTAMP]) > 0,
			"the double's instant is a positive wall-clock reading too")
		check_eq(_as_ints(
				(offline_place as BootData.StoredPlacementResult).attr),
			_as_ints(typed.attr),
			"both implementations derive the SAME attribute bag from content")

	# --- the refusals the live corpus can actually reach --------------------
	# Placing an id the content does not define, and placing an id with nothing
	# in storage, are BOTH reachable here and carry the service's own codes.
	api.configure("legacy_v0", endpoint)
	var unknown: Variant = await api.place_stored_item_town(pid, 999999,
		LIVE_CELL_X, LIVE_CELL_Y)
	check(unknown is BootData.StoredPlacementResult and not bool(unknown.ok),
		"placing an id no committed content defines is refused live")
	if unknown is BootData.StoredPlacementResult:
		check_eq(unknown.error_code, "unknown_item_id",
			"the live refusal is the service's own code: %s"
				% str(unknown.error_message))
		check_eq(int(unknown.map_key), -1,
			"the refused placement derives NO map slot")
		check((unknown.row as Array).is_empty(),
			"the refused placement carries NO partial row")
	var empty_store: Variant = await api.sell_stored_item_town(pid,
		int(LIVE_PRIZE_ID))
	check(empty_store is BootData.StoredSaleResult
			and not bool(empty_store.ok),
		"selling from an empty storage is refused live")
	if empty_store is BootData.StoredSaleResult:
		check_eq(empty_store.error_code, "not_in_storage",
			"the live sale refusal is the service's own code: %s"
				% str(empty_store.error_message))
		check_eq(bool(empty_store.credited), false,
			"the refused sale credits nothing")

	print("[test] live-stored-placement seeded=%d placed_key=%d cell=%d,%d "
		% [LIVE_SEED_COLLECTION, typed.map_key, typed.x, typed.y]
		+ "sold=%d refund=0 resources_unchanged=true refused=unknown_item_id,"
			% sale.item_id + "not_in_storage")


## The live placement's own typed shape, with no price, refund, cost, quantity,
## capacity, or bounds field anywhere on it.
func _check_typed_placement_live(result: BootData.StoredPlacementResult) -> void:
	check_eq(result.protocol, BootData.PROTOCOL,
		"the typed placement reports the v0 protocol")
	check_eq(result.result, "success",
		"the typed placement carries the legacy success result")
	check(result.server_time > 0, "the typed placement's server_time is positive")
	check_eq(result.slot_rule, StoredItemFlow.SLOT_RULE,
		"the service's echoed slot rule is the one the flow records")
	check(result.geometry_note.strip_edges() != "",
		"the service's echoed geometry note is present, not blank")
	_check_shared_gap_note(result.geometry_note, StoredItemFlow.GEOMETRY_GAP,
		"placement", GEOMETRY_CLAUSES)
	check_eq(result.refusal, "", "an accepted placement carries no refusal code")
	check_eq(result.error_code, "", "an accepted placement carries no error code")
	check(result.resources != null,
		"the typed placement carries the seven stored resources")
	for name: String in LIVE_RESOURCE_NAMES:
		check((result.resources as BootData.Resources).get(name) is int,
			"the %s slot is an integer on the typed placement" % name)


## The live sale's own typed shape, with no refund ever assumed.
func _check_typed_sale_live(result: BootData.StoredSaleResult) -> void:
	check_eq(result.protocol, BootData.PROTOCOL,
		"the typed sale reports the v0 protocol")
	check_eq(result.result, "success",
		"the typed sale carries the legacy success result")
	check(result.server_time > 0, "the typed sale's server_time is positive")
	check(result.quantity_rule.strip_edges() != "",
		"the service echoed a quantity rule, not blank")
	_check_shared_gap_note(result.quantity_rule, StoredItemFlow.QUANTITY_RULE,
		"quantity", QUANTITY_CLAUSES)
	check_eq(result.refusal, "", "an accepted sale carries no refusal code")
	check_eq(result.error_code, "", "an accepted sale carries no error code")
	check(result.resources != null,
		"the typed sale carries the seven stored resources")
	for name: String in LIVE_RESOURCE_NAMES:
		check((result.resources as BootData.Resources).get(name) is int,
			"the %s slot is an integer on the typed sale" % name)


## The live payload's `map` object, or {}.
##
## The bootstrap payload is keyed `map` (singular) because it is the legacy
## `get_player_info()` body verbatim, while the recorded FIXTURE documents are
## keyed `maps[0]`. Reading one with the other's accessor returns `{}` silently,
## which is exactly the bug the first live run of this phase exposed: a storage
## check passed for the wrong reason and then failed on the seeded state. Both
## accessors are named so the distinction is deliberate rather than remembered.
func _live_map(payload: Dictionary) -> Dictionary:
	var value: Variant = payload.get("map", {})
	return value as Dictionary if value is Dictionary else {}


## That the service's echoed rule note and the client's own copy are the SAME
## recorded rule, asserted on the clauses that identify it rather than on
## byte-equality.
##
## The two texts are deliberately NOT identical: the service's copies cite their
## source lines and probe numbers, while the client's copies are readout strings.
## Earlier drafts of this phase asserted byte-equality for both and failed on
## exactly that difference -- correctly, because the claim they made ("verbatim")
## was stronger than anything true. What IS checkable, and what the client
## actually depends on, is that both copies name the same rule: the caller
## supplies the identifying clauses and this asserts both texts carry all of
## them.
func _check_shared_gap_note(echoed: String, own: String, label: String,
		clauses: Array) -> void:
	check(not echoed.strip_edges().is_empty(),
		"the service echoed a %s note" % label)
	check(not own.strip_edges().is_empty(),
		"the client records its own %s note" % label)
	for clause: String in clauses:
		check(echoed.contains(clause),
			"the service's echoed %s note carries the identifying clause '%s'"
				% [label, clause])
		check(own.contains(clause),
			"the client's own %s note carries the same clause '%s'"
				% [label, clause])


## The clauses that name the recorded geometry gap in BOTH copies.
const GEOMETRY_CLAUSES := [
	"GRID BOUNDS AND CELL OCCUPANCY ARE RECORDED, NOT REFUSED",
	"ALREADY-RECORDED M6",
	"tile-to-cell geometry gap",
]
## The clauses that name the recorded quantity rule in BOTH copies.
const QUANTITY_CLAUSES := [
	"ONE OPERATION CONSUMES EXACTLY ONE UNIT OF STOCK",
	"quantity",
]


## A placed row with slot 3 (the server clock) replaced by a sentinel, so two
## rows recorded by two different clocks can be compared on the seven slots that
## are NOT the clock. Narrowing is limited to integral floats, exactly as
## `_as_ints` does, so a genuinely fractional value still fails the comparison.
func _row_without_instant(row: Array) -> Array:
	var narrowed: Variant = _as_ints(row)
	if not (narrowed is Array):
		return []
	var listed: Array = (narrowed as Array).duplicate()
	if listed.size() != StoredItemFlow.ROW_SLOT_COUNT:
		return listed
	listed[StoredItemFlow.ROW_SLOT_TIMESTAMP] = "<SERVER CLOCK>"
	return listed


## The `--scenario=` value this run was launched with, or "".
func _scenario_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if str(argument).begins_with("--scenario="):
			return str(argument).trim_prefix("--scenario=")
	return ""


## The loopback endpoint the live phase must dial.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if str(argument).begins_with("--gameapi-endpoint="):
			return str(argument).trim_prefix("--gameapi-endpoint=")
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The corpus's own bootstrap payload, or {} when it cannot be read. Read from
## the SERVICE and never from the fake's fixture, because every pre- and
## post-state claim in this phase is about the service's real state.
func _live_payload(api: Variant, endpoint: String,
		user_id: String) -> Dictionary:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return {}
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return {}
	return _as_ints((info as BootData.PlayerInfoPayload).raw) as Dictionary


## The live payload's seven stored balances, as integers -- the reference the
## live value-level proofs compare against. The set is the SERVICE's own
## `resources()` set, which is NOT the M7 readout's set: that readout also
## surfaces `privateState.energy`, which `apply_resources` never writes.
func _live_resources(payload: Dictionary) -> Dictionary:
	var map: Dictionary = payload.get("map", {}) as Dictionary
	var player: Dictionary = payload.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = payload.get("privateState", {}) as Dictionary
	return {
		"xp": int(map.get("xp", 0)),
		"gold": int(map.get("gold", 0)),
		"wood": int(map.get("wood", 0)),
		"oil": int(map.get("oil", 0)),
		"steel": int(map.get("steel", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(priv.get("mana", 0)),
	}