extends "res://tests/test_base.gd"
## Placement suite (building-placement, spec "Placement flow").
##
## Scenarios:
##   catalog    the typed catalog parses fail-closed from the bootstrap
##              config payload already in hand: all 900 items in payload
##              order with the eight typed fields, legacy cost keys
##              mapped to resource names, and the derived content
##              footprint;
##   gating     store-listed buildings gate by `min_level` against the
##              loaded level and only those are offered;
##   malformed  a missing or invalid field fails closed with an error
##              naming the offending item and field and yields no
##              catalog — never a guessed price or a fabricated entry —
##              while a null/empty cost parses as the documented free
##              item and the JSON transport's integral floats parse as
##              ints;
##   no-request the whole run issues no bootstrap request (the catalog
##              derives from the payload in hand, design D10).
##
## Later tasks extend this file with the town placement-flow scenarios
## (pick -> preview -> confirm -> apply, invalid-target no-request,
## failure rollback, cancelled-mode immutability).
##
## Uses the committed bootstrap fixtures directly. No API calls, no
## server. Runs headless as part of `verify-boot.ps1`.

const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

const CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var payload: Variant = _fixture(CONFIG_FIXTURE)
	check(payload is Dictionary, "config fixture parses as JSON")
	if not (payload is Dictionary):
		return
	_check_catalog_derivation(payload)
	_check_level_gating(payload)
	_check_malformed(payload)
	_check_no_second_bootstrap_request()


## Fixture facts from the committed payload (probe-recorded): House I
## costs 30 wood on a 2x2 footprint, Wood Factory III costs 6000 gold,
## Stoneage costs 20 cash, and Command Center is not store-listed.
func _check_catalog_derivation(payload: Dictionary) -> void:
	var result: Dictionary = PlacementCatalog.parse(payload)
	check(bool(result.get("ok", false)),
		"the committed config parses: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var catalog: Variant = result["catalog"]
	check(catalog is PlacementCatalog.Catalog, "the catalog is typed")
	if not (catalog is PlacementCatalog.Catalog):
		return
	check_eq(catalog.items, 900, "all 900 items parse")
	check_eq(catalog.entries.size(), 900, "every parsed entry is kept")
	var rows: Array = payload["items"]
	check(not rows.is_empty(), "the payload carries items")
	if rows.is_empty():
		return
	check_eq(catalog.entries[0].id, int(str((rows[0] as Dictionary)["id"])),
		"payload order is preserved (the first row leads)")

	var house: Variant = PlacementCatalog.find_entry(catalog, 1)
	check(house is PlacementCatalog.Entry, "House I (item 1) parses")
	if house is PlacementCatalog.Entry:
		check_eq(house.name, "House I", "the name is verbatim")
		check_eq(house.costs, {"wood": 30},
			"the w cost maps to the wood resource")
		check_eq(house.min_level, 1, "min_level parses as an integer")
		check(house.in_store, "the store flag parses as true")
		check_eq(house.width, 2, "width parses as an integer")
		check_eq(house.height, 2, "height parses as an integer")
		check_eq(house.footprint, Vector2i(2, 2),
			"the content footprint derives from width/height")
		check_eq(house.type, "b", "the type is verbatim")
	var factory: Variant = PlacementCatalog.find_entry(catalog, 10)
	check(factory is PlacementCatalog.Entry,
		"Wood Factory III (item 10) parses")
	if factory is PlacementCatalog.Entry:
		check_eq(factory.costs, {"gold": 6000},
			"the g cost maps to the gold resource")
	var wonder: Variant = PlacementCatalog.find_entry(catalog, 66)
	check(wonder is PlacementCatalog.Entry, "Stoneage (item 66) parses")
	if wonder is PlacementCatalog.Entry:
		check_eq(wonder.costs, {"cash": 20},
			"the c cost maps to the cash resource")
	check(PlacementCatalog.find_entry(catalog, 999999) == null,
		"an absent id yields no entry (never fabricated)")
	check_eq(PlacementCatalog.COST_RESOURCES.size(), 5,
		"all five legacy cost keys map to resource names")


## Gating runs against the loaded level (the picker feeds the town
## state's summary level; here the documented fixture levels directly).
func _check_level_gating(payload: Dictionary) -> void:
	var parsed: Dictionary = PlacementCatalog.parse(payload)
	if not bool(parsed.get("ok", false)):
		fail("the catalog must parse for the gating scenario")
		return
	var catalog: Variant = parsed["catalog"]
	if not (catalog is PlacementCatalog.Catalog):
		fail("the parsed catalog must be typed for the gating scenario")
		return

	var level_one: Array = PlacementCatalog.picker_entries(catalog, 1)
	check_eq(level_one.size(), 14,
		"level 1 offers exactly the 14 store-listed buildings it allows")
	var ids := {}
	for entry: Variant in level_one:
		check(entry is PlacementCatalog.Entry,
			"every offered entry is typed")
		if not (entry is PlacementCatalog.Entry):
			continue
		ids[entry.id] = true
		check(entry.in_store, "offered entries are store-listed")
		check_eq(entry.type, "b", "offered entries are buildings")
		check(entry.min_level <= 1, "offered entries gate min_level <= 1")
	check(bool(ids.get(1, false)), "House I is offered at level 1")
	check(not ids.has(5),
		"Gold Factory I (min_level 2) is withheld at level 1")
	check(not ids.has(10),
		"Wood Factory III (min_level 21) is withheld at level 1")
	check(not ids.has(26),
		"Command Center (not store-listed) is never offered")

	var level_two: Array = PlacementCatalog.picker_entries(catalog, 2)
	check(level_two.size() > level_one.size(),
		"a higher level never withholds what a lower level had")
	var ids_two := {}
	for entry: Variant in level_two:
		if entry is PlacementCatalog.Entry:
			ids_two[entry.id] = true
	check(bool(ids_two.get(1, false)), "House I stays offered at level 2")
	check(bool(ids_two.get(5, false)), "Gold Factory I unlocks at level 2")
	check(not ids_two.has(10),
		"Wood Factory III stays withheld at level 2")

	var level_twenty_one: Array = PlacementCatalog.picker_entries(catalog, 21)
	var ids_21 := {}
	for entry: Variant in level_twenty_one:
		if entry is PlacementCatalog.Entry:
			ids_21[entry.id] = true
	check(bool(ids_21.get(10, false)),
		"Wood Factory III unlocks at level 21")
	check(level_one.size() <= level_twenty_one.size(),
		"the level-21 offering is a superset of the level-1 offering")

	check_eq(PlacementCatalog.picker_entries(null, 1).size(), 0,
		"an absent catalog offers no entries (never fabricated)")


## Every malformed field fails closed: {ok:false, error naming the
## offender, catalog null}.
func _check_malformed(payload: Dictionary) -> void:
	var base: Dictionary = _row_with_id(payload, "1")
	check(not base.is_empty(), "a committed row is available for crafting")
	if base.is_empty():
		return

	_expect_reject(PlacementCatalog.parse(null), "payload is not an object")
	_expect_reject(PlacementCatalog.parse({}), "field 'items'")
	_expect_reject(PlacementCatalog.parse({"items": {}}), "field 'items'")
	_expect_reject(PlacementCatalog.parse({"items": ["x"]}),
		"item 0 is not an object")
	_expect_reject(_parse_with(base, "id", "abc"), "field 'id'")
	_expect_reject(_parse_with(base, "id", -7), "field 'id'")
	_expect_reject(_parse_without(base, "name"), "field 'name'")
	_expect_reject(_parse_with(base, "costs", '{"x":5}'),
		"unknown cost key 'x'")
	_expect_reject(_parse_with(base, "costs", '{"w":'), "not valid JSON")
	_expect_reject(_parse_with(base, "costs", '{"w":"30"}'),
		"amount of cost key 'w'")
	_expect_reject(_parse_with(base, "min_level", "abc"), "field 'min_level'")
	_expect_reject(_parse_with(base, "in_store", "2"), "field 'in_store'")
	_expect_reject(_parse_with(base, "width", "0"),
		"field 'width'/'height'")
	_expect_reject(_parse_with(base, "height", ""),
		"field 'width'/'height'")
	_expect_reject(_parse_with(base, "type", ""), "field 'type'")

	# A failure in a later row names that row and still yields no catalog.
	var late_bad := _row_with_id(payload, "1")
	late_bad["min_level"] = "oops"
	var late := PlacementCatalog.parse(
		{"items": [_row_with_id(payload, "2"), late_bad]})
	_expect_reject(late, "item 1")

	# A null or empty cost parses as the documented free item (the
	# endpoint applies no cost for it) instead of failing or guessing.
	var free := _parse_with(base, "costs", null)
	check(bool(free.get("ok", false)), "a null cost parses as a free item")
	if bool(free.get("ok", false)):
		var free_entry: Variant = (free["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(free_entry.costs, {}, "the free item costs nothing")
	var blank := _parse_with(base, "costs", "")
	check(bool(blank.get("ok", false)), "an empty cost parses as free")
	if bool(blank.get("ok", false)):
		var blank_entry: Variant = (blank["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(blank_entry.costs, {}, "the blank item costs nothing")

	# The pinned JSON transport widens numbers to floats; an integral
	# float still parses as the same integer field.
	var widened := _parse_with(base, "min_level", 2.0)
	check(bool(widened.get("ok", false)),
		"an integral transported float parses: %s" % widened.get("error"))
	if bool(widened.get("ok", false)):
		var widened_entry: Variant = \
			(widened["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(widened_entry.min_level, 2,
			"the widened min_level keeps its integer value")


## The catalog derives from the payload in hand: this whole run must not
## issue a bootstrap request (spec: "parsed fail-closed from the
## bootstrap payload the client already receives", design D10).
func _check_no_second_bootstrap_request() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	check_eq(int(api.bootstrap_requests), 0,
		"no bootstrap request was issued (the payload in hand suffices)")


## A rejected parse: {ok:false} with a non-empty error containing the
## named offender and a null catalog — never a partial parse.
func _expect_reject(result: Dictionary, needle: String) -> void:
	check(not bool(result.get("ok", false)),
		"'%s' fails closed" % needle)
	check(str(result.get("error", "")).find(needle) != -1,
		"the error names '%s' (got: %s)" % [needle,
			str(result.get("error", ""))])
	check(result.get("catalog") == null,
		"'%s' yields no catalog" % needle)


## The committed row with the given id, deep-copied for crafting.
func _row_with_id(payload: Dictionary, id_text: String) -> Dictionary:
	for row: Variant in payload["items"]:
		if row is Dictionary and str((row as Dictionary).get("id")) == id_text:
			return (row as Dictionary).duplicate(true)
	return {}


## parse() over one crafted payload carrying a single mutated row.
func _parse_with(row: Dictionary, field: String, value: Variant) -> Dictionary:
	var crafted := row.duplicate(true)
	crafted[field] = value
	return PlacementCatalog.parse({"items": [crafted]})


## parse() over one crafted payload carrying a row missing a field.
func _parse_without(row: Dictionary, field: String) -> Dictionary:
	var crafted := row.duplicate(true)
	crafted.erase(field)
	return PlacementCatalog.parse({"items": [crafted]})


## Loads a repository-relative JSON fixture as parsed text (read-only).
func _fixture(relative: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_bytes(
		Paths.repo_root().path_join(relative)).get_string_from_utf8())
