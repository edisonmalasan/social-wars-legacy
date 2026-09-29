extends "res://tests/test_base.gd"
## Typed town-state suite (OpenSpec `godot-town-rendering` "Typed town
## state loading", change task 2.1; extended by `building-purchase` task
## 4.1 with the typed storage mapping and by `building-move` task 4.1 with
## the addressable legacy map key).
##
## Scenarios:
##   fresh       the committed fresh-save bootstrap fixture parses into
##               40 verbatim placements with 11 resolved ids, content
##               footprints/asset statuses, and resource/summary values
##               equal to the fixture;
##   malformed   a payload without the default map, a non-integer
##               coordinate, a placement that is not an eight-field array,
##               and a present-but-invalid field each fail closed with an
##               error naming the offender and produce no state;
##   unresolved  an unknown legacy id keeps its placement verbatim and is
##               recorded while the rest of the save parses;
##   absent      a resource field absent from the payload is recorded in
##               `missing` instead of being fabricated or defaulted;
##   storage     the typed storage mapping: the fresh save's present-but-
##               empty `map.store` parses as an empty (not missing)
##               inventory, the preserved village's `{"302": 1}` parses
##               verbatim, quantity `0` and an unresolvable id are kept,
##               an absent field is recorded in `missing` under
##               `storage` rather than defaulted, and a non-object field,
##               a non-item-id key, or a non-integer quantity each fail
##               closed naming the offender;
##   keys        the addressable legacy map key (building-move design D7):
##               every fresh row carries its key verbatim as the
##               addressable index a move intent names, a key that is not a
##               positive integer is recorded unaddressable and NEVER
##               coerced (it is kept, rendered, and reported by its
##               verbatim key instead), and the pure key rule covers digit
##               strings, int keys, `0`, negatives, non-numeric, empty, and
##               non-scalar keys;
##   construction the typed construction state (building-construction task
##               4.1, design D5): a row with no construction state records
##               none of the three facts, a counter-only row records the
##               counter, a countdown-with-counter row records both plus the
##               row's start instant, a countdown-only row records the
##               countdown and the start instant, a zero timestamp yields no
##               start instant (nothing stamped the row), a non-object bag
##               records NO state and is marked unreadable without rejecting
##               the delivered save, and a present-but-invalid counter or
##               countdown each fail closed naming the row;
##   village     the preserved `villages/Scarlet.json` (`maps[0]` shape)
##               parses: 576 placements, the six content-unknown ids
##               recorded, House I and Wild Elephant resolved.
##
## Uses the ContentRegistry autoload (content + asset registry loaded
## explicitly, per its contract). No API, no server. Runs headless as part
## of `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")

const FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const SCARLET := "villages/Scarlet.json"
const SCARLET_UNKNOWN := [5005, 5008, 5000, 5007, 5004, 5001]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"content package loads: %s" % content.get("error"))
	var assets: Dictionary = registry.load_asset_registry()
	check(bool(assets.get("ok", false)),
		"asset registry loads: %s" % assets.get("error"))
	if not bool(content.get("ok", false)) or not bool(assets.get("ok", false)):
		return

	var payload: Variant = JSON.parse_string(
		FileAccess.get_file_as_bytes(
			Paths.repo_root().path_join(FIXTURE)).get_string_from_utf8())
	check(payload is Dictionary, "fresh fixture parses as JSON")
	if not (payload is Dictionary):
		return

	_check_fresh_parse(payload, registry)
	_check_malformed(payload, registry)
	_check_unresolved_id(payload, registry)
	_check_absent_field(payload, registry)
	_check_storage(payload, registry)
	_check_addressable_keys(payload, registry)
	_check_construction_state(payload, registry)
	_check_registry_precondition()
	_check_village_parse(registry)


func _check_fresh_parse(payload: Variant, registry: Variant) -> void:
	var result: Dictionary = TownState.parse(payload, registry)
	check(bool(result.get("ok", false)),
		"fresh fixture parses: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	check_eq(state.placements.size(), 40, "all 40 placements are present")
	# Verbatim: every row equals the fixture's parsed row, and the integer
	# coordinates match exactly.
	var fixture_rows: Dictionary = payload["map"]["items"]
	var mismatched := 0
	var order_keys := fixture_rows.keys()
	for index in range(state.placements.size()):
		var placement = state.placements[index]
		var expected: Variant = fixture_rows[order_keys[index]]
		if placement.raw != expected:
			mismatched += 1
		if placement.cell != Vector2i(int(expected[1]), int(expected[2])):
			mismatched += 1
	check_eq(mismatched, 0,
		"every placement row and coordinate is verbatim (mismatches: %d)"
		% mismatched)
	var distinct: Dictionary = {}
	for placement in state.placements:
		distinct[placement.item] = true
	check_eq(distinct.size(), 11, "11 distinct placed ids are present")
	check(state.unresolved_ids.is_empty(),
		"every fresh id resolves (unresolved: %s)" % str(state.unresolved_ids))
	check_eq(state.missing, [],
		"no displayed field is missing from the fresh payload")
	# Content resolution spot checks across the footprint range.
	var by_item := {}
	for placement in state.placements:
		if not by_item.has(placement.item):
			by_item[placement.item] = placement
	check(_content_ok(by_item, 930, Vector2i(2, 2), "Trees", "building",
		"extracted"), "Trees resolve 2x2 extracted")
	check(_content_ok(by_item, 26, Vector2i(4, 4), "Command Center",
		"building", "extracted"), "Command Center resolves 4x4")
	check(_content_ok(by_item, 909, Vector2i(12, 6), "Space Station",
		"building", "extracted"), "Space Station resolves 12x6")
	check(_content_ok(by_item, 929, Vector2i(5, 5), "Bridge", "building",
		"extracted"), "Bridge resolves 5x5")
	# Resource and summary values equal the fixture save exactly.
	var res = state.resources
	check_eq([res.coins, res.wood, res.steel, res.oil, res.cash, res.energy,
		res.mana], [2000, 2000, 2000, 2000, 5, 50, 0],
		"resource values equal the fixture save")
	var sum = state.summary
	check_eq([sum.name, sum.level, sum.xp], ["Warrior", 1, 4],
		"summary values equal the fixture save")


func _content_ok(by_item: Dictionary, item: int, footprint: Vector2i,
		name: String, kind: String, status: String) -> bool:
	if not by_item.has(item):
		return false
	var placement = by_item[item]
	return (placement.content_ok and placement.footprint == footprint
		and placement.name == name and placement.kind == kind
		and placement.asset_status == status
		and placement.img_name != "")


func _check_malformed(payload: Variant, registry: Variant) -> void:
	var no_map: Dictionary = (payload as Dictionary).duplicate(true)
	no_map.erase("map")
	no_map.erase("maps")
	var result: Dictionary = TownState.parse(no_map, registry)
	check(not bool(result.get("ok", true)),
		"a payload without the default map fails closed")
	check(result.get("state") == null, "no state is produced for no map")
	check(str(result.get("error", "")).find("map") >= 0,
		"the error names the missing map (got: %s)" % result.get("error"))

	var bad_coord: Dictionary = (payload as Dictionary).duplicate(true)
	(bad_coord["map"] as Dictionary)["items"]["bad"] = [1, 2.5, 3, 0, 0, [], {}, 1]
	result = TownState.parse(bad_coord, registry)
	check(not bool(result.get("ok", true)),
		"a non-integer coordinate fails closed")
	check(result.get("state") == null, "no state is produced for bad coords")
	check(str(result.get("error", "")).find("coordinate") >= 0,
		"the error names the coordinate (got: %s)" % result.get("error"))
	check(str(result.get("error", "")).find("bad") >= 0,
		"the error names the offending placement (got: %s)" % result.get("error"))

	var short_row: Dictionary = (payload as Dictionary).duplicate(true)
	(short_row["map"] as Dictionary)["items"]["short"] = [1, 5, 5]
	result = TownState.parse(short_row, registry)
	check(not bool(result.get("ok", true)),
		"a placement that is not an eight-field array fails closed")
	check(result.get("state") == null, "no state is produced for a short row")
	check(str(result.get("error", "")).find("eight-field") >= 0,
		"the error names the eight-field violation (got: %s)"
		% result.get("error"))
	check(str(result.get("error", "")).find("short") >= 0,
		"the error names the offending placement (got: %s)" % result.get("error"))

	var bad_gold: Dictionary = (payload as Dictionary).duplicate(true)
	(bad_gold["map"] as Dictionary)["gold"] = "lots"
	result = TownState.parse(bad_gold, registry)
	check(not bool(result.get("ok", true)),
		"a present-but-invalid resource field fails closed")
	check(result.get("state") == null, "no state is produced for bad gold")
	check(str(result.get("error", "")).find("map.gold") >= 0,
		"the error names map.gold (got: %s)" % result.get("error"))

	var not_object: Dictionary = TownState.parse([1, 2, 3], registry)
	check(not bool(not_object.get("ok", true)),
		"a non-object payload fails closed")
	check(str(not_object.get("error", "")).find("not an object") >= 0,
		"the error names the payload shape (got: %s)"
		% not_object.get("error"))


func _check_unresolved_id(payload: Variant, registry: Variant) -> void:
	var with_unknown: Dictionary = (payload as Dictionary).duplicate(true)
	(with_unknown["map"] as Dictionary)["items"]["mystery"] = \
		[999999, 10, 10, 0, 0, [], {}, 1]
	var result: Dictionary = TownState.parse(with_unknown, registry)
	check(bool(result.get("ok", false)),
		"an unknown legacy id does not fail the save: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	check_eq(state.placements.size(), 41,
		"the unknown placement is kept, not skipped")
	check_eq(state.unresolved_ids, [999999],
		"the unknown id is recorded")
	var last = state.placements.back()
	check(not last.content_ok and last.content_error != "",
		"the unknown placement carries its resolution failure")
	check(last.raw == [999999, 10, 10, 0, 0, [], {}, 1],
		"the unknown placement stays verbatim")
	check_eq(state.missing, [],
		"the remaining save still parses fully")


func _check_absent_field(payload: Variant, registry: Variant) -> void:
	var without_energy: Dictionary = (payload as Dictionary).duplicate(true)
	(without_energy["privateState"] as Dictionary).erase("energy")
	var result: Dictionary = TownState.parse(without_energy, registry)
	check(bool(result.get("ok", false)),
		"an absent resource field does not fail the save: %s"
		% result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	check("energy" in state.missing,
		"the absent field is recorded for the HUD (missing: %s)"
		% str(state.missing))
	check_eq(state.resources.mana, 0, "the other privateState values remain")
	check_eq(state.placements.size(), 40,
		"an absent field never drops placements")


## The typed storage mapping (building-purchase task 4.1, design D7):
## present-but-empty parses as an empty inventory (NOT missing), the
## village's real entry parses verbatim, quantity `0` and an id the
## content package cannot resolve are kept, an absent field is recorded in
## `missing` under `storage` instead of being defaulted, and every
## present-but-invalid shape fails closed naming the offending key.
func _check_storage(payload: Variant, registry: Variant) -> void:
	# The fresh save carries `map.store = {}`: an empty inventory is a
	# real, observed state and must not be reported as a missing field.
	var fresh: Dictionary = TownState.parse(payload, registry)
	check(bool(fresh.get("ok", false)),
		"the fresh storage parses: %s" % fresh.get("error"))
	if bool(fresh.get("ok", false)):
		var state = fresh["state"]
		check_eq(state.storage, {},
			"the fresh save's present-but-empty storage parses as {}")
		check(not state.missing.has(TownState.STORAGE_MISSING_KEY),
			"a present storage field is never recorded missing")

	# Entries are kept verbatim, including a quantity of 0 and an id the
	# content package cannot resolve.
	var stocked: Dictionary = (payload as Dictionary).duplicate(true)
	(stocked["map"] as Dictionary)["store"] = {
		"302": 2, "999999": 0}
	var result: Dictionary = TownState.parse(stocked, registry)
	check(bool(result.get("ok", false)),
		"a populated storage parses: %s" % result.get("error"))
	if bool(result.get("ok", false)):
		var state = result["state"]
		check_eq(state.storage, {"302": 2, "999999": 0},
			"quantities are verbatim, quantity 0 included, unresolved ids "
			+ "included")
		check_eq(state.placements.size(), 40,
			"a populated storage never drops placements")

	# An int key is canonicalized to the documented string form.
	var int_keys: Dictionary = (payload as Dictionary).duplicate(true)
	(int_keys["map"] as Dictionary)["store"] = {302: 2}
	result = TownState.parse(int_keys, registry)
	check(bool(result.get("ok", false)),
		"an int storage key parses: %s" % result.get("error"))
	if bool(result.get("ok", false)):
		check_eq((result["state"] as Variant).storage, {"302": 2},
			"an int key canonicalizes to the stringified item id")

	# Absent -> recorded in `missing`, never defaulted to an empty one.
	var without_store: Dictionary = (payload as Dictionary).duplicate(true)
	(without_store["map"] as Dictionary).erase("store")
	result = TownState.parse(without_store, registry)
	check(bool(result.get("ok", false)),
		"an absent storage field does not fail the save: %s"
		% result.get("error"))
	if bool(result.get("ok", false)):
		var state = result["state"]
		check(state.missing.has(TownState.STORAGE_MISSING_KEY),
			"the absent storage field is recorded for the readout "
			+ "(missing: %s)" % str(state.missing))
		check_eq(state.storage, {},
			"an absent field yields no fabricated inventory")
		check("energy" not in state.missing,
			"the storage record never displaces the HUD's own fields")

	# Present-but-invalid: each shape fails closed naming the offender.
	_expect_storage_reject(_with_store(payload, "nope"), "not an object")
	_expect_storage_reject(_with_store(payload, []), "not an object")
	_expect_storage_reject(_with_store(payload, {"mystery": 1}),
		"storage entry key 'mystery' is not an item id")
	_expect_storage_reject(_with_store(payload, {"105": "one"}),
		"storage entry '105' quantity")
	_expect_storage_reject(_with_store(payload, {"105": 1.5}),
		"storage entry '105' quantity")
	_expect_storage_reject(_with_store(payload, {"-1": 1}),
		"storage entry key '-1' is not an item id")
	_expect_storage_reject(_with_store(payload, {"105": -3}),
		"storage entry '105' quantity")

	# The shared parser the purchase apply reuses is the same function:
	# the response's `store` mapping goes through exactly these rules.
	var response: Dictionary = TownState.storage_of({"105": 1.0})
	check(bool(response.get("ok", false)),
		"the shared storage parser accepts a response mapping")
	check(bool(response.get("present", false)),
		"a response mapping is always present")
	check_eq(response.get("storage", {}), {"105": 1},
		"the shared parser canonicalizes the transport's integral float")
	var response_bad: Dictionary = TownState.storage_of({"105": null})
	check(not bool(response_bad.get("ok", true)),
		"the shared parser rejects a null quantity fail-closed")
	var response_absent: Dictionary = TownState.storage_of(null)
	check(bool(response_absent.get("present", true)) == false,
		"the shared parser reports an absent mapping as not present")
	check_eq(response_absent.get("storage", {}), {},
		"an absent mapping yields no fabricated inventory")


## The addressable legacy map key (building-move task 4.1, design D7): the
## positive integer a row was stored under is the verbatim index a move
## intent names; a key that is not one is recorded unaddressable and never
## coerced, because coercing it to `0` would address a real, different row.
func _check_addressable_keys(payload: Variant, registry: Variant) -> void:
	var result: Dictionary = TownState.parse(payload, registry)
	check(bool(result.get("ok", false)),
		"the fresh save parses for the key check: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	# Every fresh row is keyed 1..40, so each is addressable and its recorded
	# key text equals its index.
	var by_slot := {}
	for placement in state.placements:
		by_slot[placement.slot] = true
		check(int(placement.slot) > 0,
			"fresh placement '%s' carries an addressable index"
				% str(placement.slot_key))
		check_eq(str(placement.slot_key), str(placement.slot),
			"the recorded key text equals the addressable index")
	check_eq(by_slot.size(), 40, "all 40 fresh keys are distinct and addressable")
	# The row the executed move fixture targets: key "11", Turret I.
	var turret = null
	for placement in state.placements:
		if placement.slot == 11:
			turret = placement
	check(turret != null, "the fixture's key 11 resolves to a placement")
	if turret != null:
		check_eq(turret.item, 22, "key 11 names Turret I")
		check_eq(turret.cell, Vector2i(58, 48),
			"key 11 is anchored at (58,48) in the fresh save")

	# The pure key rule, over every shape a save could carry. A digit
	# string is the documented legacy shape; an int key canonicalizes to
	# the same index; everything else is unaddressable, never coerced.
	check_eq(TownState.slot_of("11"), 11, "a digit string is the index")
	check_eq(TownState.slot_of(11), 11, "an int key is the same index")
	check_eq(TownState.slot_of("1"), 1, "index 1 is addressable")
	check_eq(TownState.slot_of("0"), null, "index 0 is not addressable")
	check_eq(TownState.slot_of(0), null, "int key 0 is not addressable either")
	check_eq(TownState.slot_of("-1"), null, "a negative key is not addressable")
	check_eq(TownState.slot_of("-1"), null,
		"a negative digit-prefixed key is not addressable")
	check_eq(TownState.slot_of("mystery"), null,
		"a non-numeric key is not addressable")
	check_eq(TownState.slot_of("1.5"), null,
		"a non-integer numeric key is not addressable")
	check_eq(TownState.slot_of(""), null, "an empty key is not addressable")
	check_eq(TownState.slot_of(null), null, "a null key is not addressable")
	check_eq(TownState.slot_of([11]), null,
		"a non-scalar key is not addressable")
	check_eq(TownState.slot_of({"11": true}), null,
		"an object key is not addressable")
	check_eq(TownState.NO_SLOT, -1,
		"the unaddressable sentinel is never a usable index")
	check(not TownState.is_addressable(null),
		"an absent placement is never addressable")
	check(not TownState.is_addressable({"slot": 11}),
		"an untyped bag is never addressable (no guessing)")

	# A crafted payload whose rows carry unusable keys: the save still parses
	# and every row is kept, rendered, and reported by its verbatim key — the
	# move flow refuses such a row explicitly instead of moving another one.
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	var items: Dictionary = (crafted["map"] as Dictionary)["items"]
	items["mystery"] = [1, 20, 20, 0, 0, [], {}, 1]
	items["0"] = [1, 21, 20, 0, 0, [], {}, 1]
	items[""] = [1, 22, 20, 0, 0, [], {}, 1]
	items["-3"] = [1, 23, 20, 0, 0, [], {}, 1]
	items[7] = [1, 24, 20, 0, 0, [], {}, 1]
	var crafted_result: Dictionary = TownState.parse(crafted, registry)
	check(bool(crafted_result.get("ok", false)),
		"unusable keys do not fail the save: %s"
		% crafted_result.get("error"))
	if not bool(crafted_result.get("ok", false)):
		return
	var crafted_state = crafted_result["state"]
	check_eq(crafted_state.placements.size(), 45,
		"every crafted row is kept, not dropped")
	var unaddressable := 0
	for placement in crafted_state.placements:
		if not TownState.is_addressable(placement):
			unaddressable += 1
			check_eq(int(placement.slot), TownState.NO_SLOT,
				"an unaddressable row carries the sentinel, not a guess")
			check(str(placement.slot_key) in ["mystery", "0", "", "-3"],
				"an unaddressable row records its own key verbatim ('%s')"
					% str(placement.slot_key))
	check_eq(unaddressable, 4,
		"the four unusable keys are recorded unaddressable")
	# An int key "7" already names a real row, so the parser now finds two
	# rows under the same index: both carry it verbatim (the key is never
	# rewritten), and the duplicate is the save's own shape to report, not
	# something the parser invents.
	var seven = 0
	for placement in crafted_state.placements:
		if int(placement.slot) == 7:
			seven += 1
	check_eq(seven, 2, "both rows stored under index 7 carry it verbatim")
	# The usable rows are untouched by the unusable ones.
	var turret_after = null
	for placement in crafted_state.placements:
		if placement.slot == 11 and placement.item == 22:
			turret_after = placement
	check(turret_after != null,
		"an addressable row stays addressable beside unusable keys")


## The typed construction state (building-construction task 4.1, design D5):
## the click counter, the recorded countdown, and the start instant are each
## ABSENT when the row records none, they are read from the row's own attribute
## bag in the one shared placement parser, and every present-but-invalid value
## fails closed naming the row. The pure accessor the flow helpers read is the
## same rule set, so a row can never be read two ways.
func _check_construction_state(payload: Variant, registry: Variant) -> void:
	# The committed corpus itself: every fresh row was placed before the
	# corpus was recorded, so every bag is empty and no row is building.
	var result: Dictionary = TownState.parse(payload, registry)
	check(bool(result.get("ok", false)),
		"the fresh save parses for the construction check: %s"
		% result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	var without_state := 0
	for placement in state.placements:
		var construction: Dictionary = TownState.construction_of(placement)
		if not bool(construction.get("ok", false)):
			continue
		if placement.clicks == null and placement.countdown == null \
				and placement.started_at == null:
			without_state += 1
	check_eq(without_state, state.placements.size(),
		"no row of the fresh corpus records construction state (attr is {})")
	var turret = _placement_by_slot(state, 11)
	check(turret != null, "the fixture's key 11 resolves for the build check")
	if turret != null:
		var empty: Dictionary = TownState.construction_of(turret)
		check(bool(empty.get("ok", false)),
			"an empty attribute bag is a readable construction state")
		check_eq(empty.get("clicks", 1), null,
			"an empty bag records no click counter")
		check_eq(empty.get("countdown", 1), null,
			"an empty bag records no countdown")
		check_eq(empty.get("started_at", 1), null,
			"an empty bag records no start instant")

	# The four documented states, each parsed through the SAME parser and read
	# through the SAME accessor the pure flow helpers use.
	_check_construction_row(payload, registry, "bare", 0, {}, null, null, null)
	_check_construction_row(payload, registry, "counter", 0, {"nc": 0}, 0,
		null, null)
	_check_construction_row(payload, registry, "counter-raised", 0, {"nc": 1},
		1, null, null)
	_check_construction_row(payload, registry, "countdown-and-counter",
		1790690555, {"cp": 5, "nc": 1}, 1, 5, 1790690555)
	_check_construction_row(payload, registry, "countdown-only", 1790690555,
		{"cp": 5}, null, 5, 1790690555)
	# A countdown with no usable start instant: the row's own timestamp is 0,
	# so nothing stamped it and no remaining time can be derived from it.
	_check_construction_row(payload, registry, "countdown-unstamped", 0,
		{"cp": 5}, null, 5, null)
	# Other bag entries are carried verbatim and never interpreted: the
	# friend-assist cluster's `si` bag is out of scope for this line.
	var friendly: Dictionary = _with_attr(payload, {"si": [], "nc": 2, "cp": 60})
	var friendly_result: Dictionary = TownState.parse(friendly, registry)
	check(bool(friendly_result.get("ok", false)),
		"a row carrying the friend-assist bag still parses: %s"
		% friendly_result.get("error"))
	if bool(friendly_result.get("ok", false)):
		var friendly_state = friendly_result["state"]
		var friendly_placement: Variant = _placement_by_slot(friendly_state, 11)
		check(friendly_placement != null
			and friendly_placement.clicks == 2
			and friendly_placement.countdown == 60
			and friendly_placement.attr.has("si"),
			"only nc and cp are interpreted; si is carried verbatim")

	# Present-but-invalid: a counter and a countdown each fail closed naming
	# the offending row, exactly as a malformed coordinate does.
	_expect_construction_reject(_with_attr(payload, {"nc": -1}), "counter")
	_expect_construction_reject(_with_attr(payload, {"nc": 1.5}), "counter")
	_expect_construction_reject(_with_attr(payload, {"nc": "one"}), "counter")
	_expect_construction_reject(_with_attr(payload, {"cp": 0}), "countdown")
	_expect_construction_reject(_with_attr(payload, {"cp": -5}), "countdown")
	_expect_construction_reject(_with_attr(payload, {"cp": "soon"}), "countdown")

	# A bag that is not an object at all records NO construction state and is
	# marked unreadable, WITHOUT rejecting the save: the delivered parser has
	# always kept such a row verbatim (the selection suite's crafted overlap
	# rows carry `0` there), so rejecting it would change delivered behavior,
	# while reading a counter out of it would be fabrication.
	var opaque: Dictionary = (payload as Dictionary).duplicate(true)
	((opaque["map"] as Dictionary)["items"] as Dictionary)["opaque"] = [
		26, 0, 0, 0, 0, 0, 0, 0]
	var opaque_result: Dictionary = TownState.parse(opaque, registry)
	check(bool(opaque_result.get("ok", false)),
		"a row whose bag is not an object still parses: %s"
		% opaque_result.get("error"))
	if bool(opaque_result.get("ok", false)):
		var opaque_state = opaque_result["state"]
		check_eq(opaque_state.placements.size(), 41,
			"the row is kept, not dropped")
		var opaque_placement: Variant = _placement_by_slot(opaque_state, "opaque")
		check(opaque_placement != null, "the opaque row is addressable by key")
		if opaque_placement != null:
			check(not opaque_placement.construction_readable,
				"the opaque row is marked unreadable, not half-parsed")
			check_eq(opaque_placement.clicks, null,
				"the opaque row records no click counter")
			var unreadable: Dictionary = TownState.construction_of(
				opaque_placement)
			check(not bool(unreadable.get("ok", true)),
				"the shared accessor refuses to read the opaque row")

	# The accessor itself never guesses: an absent placement and an untyped bag
	# are both refused, and the sentinel-free nulls are reported as nulls.
	check(not bool(TownState.construction_of(null).get("ok", true)),
		"an absent placement has no readable construction state")
	check(not bool(TownState.construction_of({"clicks": 1}).get("ok", true)),
		"an untyped bag is never read as a placement (no guessing)")


## One crafted row's construction state: the row, the expected three facts,
## and the fact the parser kept the row verbatim.
func _check_construction_row(payload: Variant, registry: Variant, key: String,
		stamp: int, attr: Dictionary, clicks: Variant, countdown: Variant,
		started: Variant) -> void:
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[key] = [
		22, 12, 12, stamp, 0, [], attr, 1]
	var result: Dictionary = TownState.parse(crafted, registry)
	check(bool(result.get("ok", false)),
		"the '%s' row parses: %s" % [key, result.get("error")])
	if not bool(result.get("ok", false)):
		return
	var placement: Variant = _placement_by_slot(result["state"], key)
	check(placement != null, "the '%s' row is kept and addressable" % key)
	if placement == null:
		return
	check(placement.construction_readable,
		"the '%s' row's construction state is readable" % key)
	check_eq(placement.clicks, clicks,
		"the '%s' row's click counter is the recorded one" % key)
	check_eq(placement.countdown, countdown,
		"the '%s' row's countdown is the recorded one" % key)
	check_eq(placement.started_at, started,
		"the '%s' row's start instant is the recorded one" % key)
	check_eq(placement.attr, attr,
		"the '%s' row's attribute bag is carried verbatim" % key)
	var shared: Dictionary = TownState.construction_of(placement)
	check(bool(shared.get("ok", false)),
		"the shared accessor reads the '%s' row" % key)
	check_eq(shared.get("clicks", 0), clicks,
		"the shared accessor reports the '%s' row's counter" % key)
	check_eq(shared.get("countdown", 0), countdown,
		"the shared accessor reports the '%s' row's countdown" % key)
	check_eq(shared.get("started_at", 0), started,
		"the shared accessor reports the '%s' row's start instant" % key)


## A rejected construction parse: `{ok: false}` with an error naming the
## offending row and no state produced.
func _expect_construction_reject(payload: Dictionary, needle: String) -> void:
	var result: Dictionary = TownState.parse(payload, registry_of(payload))
	check(not bool(result.get("ok", true)),
		"an invalid %s fails closed" % needle)
	check(result.get("state") == null, "an invalid %s yields no state" % needle)
	check(str(result.get("error", "")).find(needle) != -1
		and str(result.get("error", "")).find("11") != -1,
		"the error names the invalid %s and the offending row (got: %s)"
		% [needle, str(result.get("error", ""))])


## The committed placement carrying an addressable index (null when absent).
func _placement_by_slot(state: Variant, slot: Variant) -> Variant:
	if state == null:
		return null
	for placement: Variant in state.placements:
		if placement == null:
			continue
		if int(placement.slot) == int(slot) or str(placement.slot_key) \
				== str(slot):
			return placement
	return null


## A rejected storage parse: `{ok: false}` with an error naming the
## offender and no state produced.
func _expect_storage_reject(payload: Dictionary, needle: String) -> void:
	var result: Dictionary = TownState.parse(payload, registry_of(payload))
	check(not bool(result.get("ok", true)),
		"'%s' fails closed" % needle)
	check(result.get("state") == null, "'%s' yields no state" % needle)
	check(str(result.get("error", "")).find(needle) != -1,
		"the error names '%s' (got: %s)" % [needle,
		str(result.get("error", ""))])


## The ContentRegistry autoload (the payload scenarios all share it).
func registry_of(_payload: Dictionary) -> Variant:
	return root.get_node_or_null("ContentRegistry")


## The payload with one crafted attribute bag on the recorded key 11.
func _with_attr(payload: Dictionary, value: Variant) -> Dictionary:
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["11"][6] = value
	return crafted


## The payload with one crafted `map.store` value.
func _with_store(payload: Dictionary, value: Variant) -> Dictionary:
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	(crafted["map"] as Dictionary)["store"] = value
	return crafted


func _check_registry_precondition() -> void:
	var cold = load("res://scripts/content_registry.gd").new()
	root.add_child(cold)
	var result: Dictionary = TownState.parse({"map": {"items": []}}, cold)
	check(not bool(result.get("ok", true)),
		"an unloaded content registry fails closed")
	check(str(result.get("error", "")).find("content is not loaded") >= 0,
		"the precondition error is explicit (got: %s)" % result.get("error"))
	root.remove_child(cold)
	cold.free()


func _check_village_parse(registry: Variant) -> void:
	var payload: Variant = JSON.parse_string(
		FileAccess.get_file_as_bytes(
			Paths.repo_root().path_join(SCARLET)).get_string_from_utf8())
	check(payload is Dictionary, "village file parses as JSON")
	if not (payload is Dictionary):
		return
	var result: Dictionary = TownState.parse(payload, registry)
	check(bool(result.get("ok", false)),
		"village (maps[0] shape) parses: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var state = result["state"]
	check_eq(state.placements.size(), 576, "all 576 village placements parse")
	check_eq(state.unresolved_ids, SCARLET_UNKNOWN,
		"the six content-unknown village ids are recorded in save order")
	check(state.missing.is_empty(),
		"no displayed field is missing from the village payload (missing: %s)"
		% str(state.missing))
	check_eq(state.storage, {"302": 1},
		"the village's real storage entry parses verbatim")
	var elephant = null
	var house = null
	for placement in state.placements:
		if placement.item == 933 and elephant == null:
			elephant = placement
		if placement.item == 1 and house == null:
			house = placement
	check(house != null and house.content_ok and house.kind == "building"
		and house.footprint == Vector2i(2, 2)
		and house.asset_status == "converted",
		"House I resolves as a converted 2x2 building in the village")
	check(elephant != null and elephant.content_ok and elephant.kind == "unit"
		and elephant.footprint == Vector2i(1, 1)
		and elephant.asset_status == "converted",
		"Wild Elephant resolves as a converted 1x1 unit in the village")
	check_eq(state.summary.name, "Scarlet",
		"the village summary name equals its save")
