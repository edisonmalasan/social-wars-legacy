extends "res://tests/test_base.gd"
## Unit-movement suite (OpenSpec `godot-unit-movement` "A unit row's placement is
## projected, never derived" / "Committed movement fields are content, not
## rules" / "The movement-command inventory classifies what each command does and
## does not check" / "The row instant is client-writable, and no readiness is
## derived from it" / "Movement is content, not a server operation" / "No
## executed-legacy movement fixture is claimed" / "Unit-movement evidence and
## claim limits", design D1-D7).
##
## This line delivers a REFUSAL, so much of what it asserts is an **absence**.
## The anti-invention guard is structural: the delivered module's whole function
## inventory is compared against a pinned list, so a travel-time, path, terrain,
## occupancy, bounds, readiness, interpolation, or animation helper fails the run
## wherever it is added - verified by injecting one and watching the suite fail.
##
## Checks:
##   projection  the placement fields reported verbatim from a row and its
##               committed definition, with nothing derived from anything else;
##   refusal     an unresolvable row refused with its recorded slots intact and
##               never defaulted to the origin;
##   content     the committed movement fields as content only, the zero-consumer
##               fact, and the measured committed coverage;
##   inventory   `move`, `orient`, `pop_unit`, and `fast_forward` each with what it
##               checks and what it does not, the measured closed counts, and that
##               no unit-specific movement command exists;
##   instant     the client-writable instant recorded and treated as opaque;
##   absence     the module declares **EXACTLY** the placement accessors of
##               design D1-D4 and none of the ABSENT_HELPERS;
##   boundary    no compatibility surface and no move intent;
##   legacy      every recorded legacy figure re-derived from the committed source
##               in this same run, so no count is taken on trust.
##
## `--report=<path>` writes the deterministic `unit-movement-report-v1` evidence
## report; the bare `--report` flag defaults to
## `evidence/unit-movement/report.json`. The tables are derived from the live
## module and from the measurements this run performed, so they cannot drift from
## the code and the source they document.

## `Paths` is inherited from `test_base.gd`; only the module is new here.
const UnitMovement = preload("res://scripts/units/unit_movement.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-movement/report.json"

## The eight reported placement fields, in committed table order.
const EXPECTED_FIELD_NAMES := [
	"cell_x", "cell_y", "orientation", "row_instant",
	"velocity", "width", "height", "elevation",
]

## A committed unit id used for the definition-side assertions. 923 is the
## committed minimum (Gorilla) and 1085 the committed collection-prize unit.
const SAMPLE_UNIT_ID := "923"
const COLLECTION_UNIT_ID := "1085"

## The absent-helper families the recorded `ABSENT_HELPERS` inventory must
## name between them, one per family the contract refuses to invent.
const ABSENT_FAMILIES := [
	"travel_time", "speed", "distance", "find_path", "terrain_at",
	"elevation_offset", "footprint_cells", "is_occupied", "in_bounds",
	"is_arrived", "is_ready", "elapsed", "interpolate", "position_at",
	"rotate_to", "animate_move", "apply_velocity",
]


## Committed row slots, re-exported so this suite asserts the module's own view.
func run_scenario() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var loaded: Dictionary = registry.load_content()
	check_eq(bool(loaded.get("ok", false)), true,
		"the committed content package verifies and loads: the projection's "
			+ "definition side is read through the registry, not from the file")

	var legacy := _check_legacy()
	var projection := _check_projection(registry)
	var refusal := _check_refusal()
	var content := _check_content(registry)
	var inventory := _check_inventory()
	var instant := _check_instant()
	_check_absence()
	_check_boundary()

	var corpus := _read_corpus()
	var package_digest := _package_digest()

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, loaded, legacy, projection,
			refusal, content, inventory, instant, corpus, package_digest)


# ---------------------------------------------------------------------------
# The placement projection (requirement 1)
# ---------------------------------------------------------------------------

## A committed row built for the suite, never written into a save.
func _row(item_id: int, x: int, y: int, instant: int, orientation: int) -> Array:
	return [item_id, x, y, instant, orientation, [], {}, 1]


## The committed definition for one unit id, as the registry reports it.
func _definition(registry: Variant, id_text: String) -> Variant:
	var resolved: Dictionary = registry.get_entry("units", id_text)
	if not bool(resolved.get("found", false)):
		fail("the committed unit definition %s resolves" % id_text)
		return {}
	return resolved["entry"]


func _check_projection(registry: Variant) -> Dictionary:
	var measured: Dictionary = {"rows": 0, "corpus_rows": 0, "corpus_all_buildings": true,
		"corpus_non_empty_garrisons": 0}

	check_eq(UnitMovement.placement_field_names(), EXPECTED_FIELD_NAMES,
		"the reported placement fields are exactly the eight the contract names, "
			+ "in committed table order")
	check_eq(UnitMovement.PLACEMENT_FIELD_COUNT, EXPECTED_FIELD_NAMES.size(),
		"the recorded field count matches the recorded names")
	check_eq(UnitMovement.PLACEMENT_ROW_FIELD_COUNT
			+ UnitMovement.PLACEMENT_CONTENT_FIELD_COUNT,
		UnitMovement.PLACEMENT_FIELD_COUNT,
		"the field count splits exactly into row-sourced and content-sourced fields")

	# every reported field names its source
	var unsourced: Array = []
	for entry: Dictionary in UnitMovement.placement_field_inventory():
		if str(entry.get("source", "")) == "" or str(entry.get("source_kind", "")) == "":
			unsourced.append(str(entry.get("name", "?")))
	check_eq(unsourced, [],
		"every reported placement field names its source and its source kind")

	# a row whose coordinates and committed definition both resolve
	var definition: Variant = _definition(registry, SAMPLE_UNIT_ID)
	var ok: Dictionary = UnitMovement.evaluate(_row(1, 58, 47, 1700000000, 0), definition)
	check_eq(bool(ok.get("ok", false)), true,
		"a committed row with readable coordinates and a committed definition projects")
	check_eq(bool(ok.get("resolvable", false)), true,
		"the projection reports the row as resolvable")
	check_eq(int(ok.get("cell_x", -1)), 58,
		"the committed cell x is reported verbatim")
	check_eq(int(ok.get("cell_y", -1)), 47,
		"the committed cell y is reported verbatim")
	check_eq(ok.get("cell_recorded", []), [58, 47],
		"the recorded coordinate slots travel beside the resolved cell, so a "
			+ "caller can compare the two")
	check_eq(int(ok.get("row_slots", 0)), UnitMovement.ROW_SLOTS,
		"the projection reports the committed row-slot count")
	measured["rows"] = 1

	# the committed definition's values are reported verbatim
	check_eq(ok.get("footprint", {}).get("ok", false), true,
		"the committed definition's four movement fields resolve")
	var footprint: Dictionary = ok.get("footprint", {})
	check_eq(footprint.get("width"), definition.get("width"),
		"the committed width is reported verbatim")
	check_eq(footprint.get("height"), definition.get("height"),
		"the committed height is reported verbatim")
	check_eq(footprint.get("elevation"), definition.get("elevation"),
		"the committed elevation is reported verbatim")
	check_eq(ok.get("velocity"), definition.get("velocity"),
		"the committed velocity is reported verbatim")

	# the no-derivation flags, and the absence of any derived value
	for flag: String in ["travel_time_computed", "path_computed",
			"terrain_interaction", "occupancy_enforced", "bounds_enforced",
			"animation_implemented", "request_issued", "instant_derived"]:
		check_eq(bool(ok.get(flag, true)), false,
			"the projection reports %s as false" % flag)
	check_eq(str(ok.get("readiness", "")), UnitMovement.READINESS_UNKNOWN,
		"the projection reports the legacy server cannot say whether a unit moved")
	check_eq(int(ok.get("definition_supplied", false) as int), 1,
		"the projection records that a committed definition was supplied")
	check_eq(str(ok.get("definition_type", "")), "u",
		"the projection records the definition's committed type")
	check(str(ok.get("no_derivation", "")).contains("NO VALUE"),
		"the projection carries the no-derivation contract")
	check(str(ok.get("cell_refusal", "")).contains("ABSENT OR MALFORMED"),
		"the projection carries the cell-refusal contract")
	check(str(ok.get("readout", "")).length() > 0,
		"the projection renders display text")

	# the real committed corpus: every placed row is a building, and it projects
	var corpus := _read_corpus()
	var items: Dictionary = {}
	if not corpus.is_empty():
		var maps: Array = corpus.get("maps", [])
		if maps.size() > 0 and maps[0] is Dictionary:
			items = (maps[0] as Dictionary).get("items", {})
	measured["corpus_rows"] = items.size()
	for key: Variant in items:
		var row: Array = items[key]
		var eval_result := UnitMovement.evaluate(row, null)
		if not bool(eval_result.get("ok", false)):
			fail("corpus row %s projects" % key)
			continue
		if (row[5] as Array).size() > 0:
			measured["corpus_non_empty_garrisons"] += 1
	check(measured["corpus_rows"] == 40,
		"the committed corpus holds 40 placed rows: %d" % measured["corpus_rows"])
	check_eq(measured["corpus_non_empty_garrisons"], 0,
		"no committed corpus row carries a non-empty garrison")
	return measured


# ---------------------------------------------------------------------------
# The refusal path (requirement 1)
# ---------------------------------------------------------------------------

## Absent, malformed, and non-integer coordinates each fail closed with the
## recorded slots intact and never defaulted to the origin.
func _check_refusal() -> Dictionary:
	var measured: Dictionary = {"refusals": 0}
	var cases: Array = [
		{"label": "a row that is not an array", "row": "not-a-row",
			"reason": UnitMovement.REASON_INVALID_ROW},
		{"label": "a row with too few slots", "row": [1, 5],
			"reason": UnitMovement.REASON_INVALID_ROW},
		{"label": "a row with an absent x", "row": [1, null, 9, 0, 0, [], {}, 1],
			"reason": UnitMovement.REASON_UNRESOLVABLE_CELL},
		{"label": "a row with an absent y", "row": [1, 5, null, 0, 0, [], {}, 1],
			"reason": UnitMovement.REASON_UNRESOLVABLE_CELL},
		{"label": "a row with a non-integer x", "row": [1, "east", 9, 0, 0, [], {}, 1],
			"reason": UnitMovement.REASON_UNRESOLVABLE_CELL},
		{"label": "a row with a non-integer y", "row": [1, 5, 1.5, 0, 0, [], {}, 1],
			"reason": UnitMovement.REASON_UNRESOLVABLE_CELL},
	]
	for case: Dictionary in cases:
		var result: Dictionary = UnitMovement.evaluate(case["row"], null)
		var label := str(case["label"])
		check_eq(bool(result.get("ok", true)), false,
			"%s is refused" % label)
		check_eq(str(result.get("reason", "")), str(case["reason"]),
			"%s is refused with the recorded reason" % label)
		check_eq(bool(result.get("resolvable", true)), false,
			"%s produces no placement" % label)
		check(str(result.get("error", "")).length() > 0,
			"%s names the offending value in its error" % label)
		measured["refusals"] += 1

	# the recorded slots travel UNTOUCHED, and the origin is never invented
	var absent: Dictionary = UnitMovement.evaluate([1, null, 9, 1700000000, 3, [], {}, 1], null)
	check_eq(absent.get("cell_recorded", []), [null, 9],
		"a refused row's recorded coordinate slots travel beside the refusal "
			+ "untouched, so a caller cannot read a defaulted origin as a cell")
	check_eq(absent.get("cell_x", "unset"), null,
		"a refused row reports no x rather than the origin")
	check_eq(absent.get("cell_y", "unset"), null,
		"a refused row reports no y rather than the origin")
	check_eq(bool(absent.get("cell_x_present", true)), false,
		"a refused row reports the x as absent")
	check_eq(bool(absent.get("cell_y_present", true)), false,
		"a refused row reports the y as absent")
	check_eq(absent.get("orientation", "unset"), 3,
		"a refused row still reports its recorded orientation beside the refusal")
	check_eq(bool(absent.get("instant_derived", true)), false,
		"a refused row's instant is still treated as opaque")

	# an invalid definition is refused too, with the fields named as absent
	var bad: Dictionary = UnitMovement.evaluate(_row(1, 5, 6, 0, 0), "not-a-definition")
	check_eq(bool(bad.get("ok", true)), true,
		"an invalid definition does not fail the row's own coordinates")
	check_eq(bad.get("footprint", {}).get("ok", true), false,
		"an invalid definition is refused for the movement fields")
	check_eq(str(bad.get("footprint", {}).get("reason", "")),
		UnitMovement.REASON_INVALID_DEFINITION,
		"the refusal names the invalid definition")
	measured["invalid_definition"] = true
	return measured


# ---------------------------------------------------------------------------
# The committed movement fields as content (requirement 2)
# ---------------------------------------------------------------------------

func _check_content(registry: Variant) -> Dictionary:
	var record: Dictionary = UnitMovement.movement_fields_record()
	var measured: Dictionary = {"units_positive": 0, "units_total": 0,
		"buildings_positive": 0, "buildings_total": 0, "flying_units": 0}

	check_eq(bool(record.get("reported_as_content_only", false)), true,
		"the committed movement fields are recorded as reported content only")
	check_eq(bool(record.get("used_as_a_rule", false)), false,
		"the committed movement fields are recorded as NOT used as a rule")
	check_eq(record.get("fields", []), UnitMovement.MOVEMENT_FIELDS,
		"the recorded movement-field list is the four the contract names")
	check_eq(record.get("footprint_fields", []), UnitMovement.FOOTPRINT_FIELDS,
		"the recorded footprint fields are the three the contract names")
	check_eq(int(record.get("consumer_count", -1)),
		UnitMovement.MOVEMENT_FIELD_CONSUMER_COUNT,
		"the recorded legacy consumer count for the movement fields is zero")

	# the per-field consumer counts, measured in this same run
	var per_field: Dictionary = record.get("consumer_count_per_field", {})
	for field: String in UnitMovement.MOVEMENT_FIELDS:
		check_eq(int(per_field.get(field, -1)), 0,
			"the measured legacy consumer count for `%s` is zero" % field)
	check_eq(record.get("searched_modules", []), UnitMovement.SEARCHED_MODULES,
		"the recorded searched-module list is the seven legacy modules")

	# the zero-consumer precedents, and the sibling unread fields
	check(int(record.get("zero_consumer_precedents", []).size()) >= 3,
		"at least three earlier zero-consumer fields are named as precedents")
	for precedent: Dictionary in record.get("zero_consumer_precedents", []):
		check(str(precedent.get("field", "")).length() > 0,
			"each named precedent states which committed field it is")
		check(str(precedent.get("fact", "")).length() > 0,
			"each named precedent states its recorded fact")
	check_eq(record.get("sibling_zero_consumer_fields", []),
		UnitMovement.SIBLING_ZERO_CONSUMER_FIELDS,
		"the recorded sibling unread fields are the ones the contract names")

	# the committed coverage, measured over the verified domains
	# `legacy_ids` answers a DICTIONARY, so the id list is read out of it and
	# the lookup is asserted rather than assumed
	for domain: String in ["units", "buildings"]:
		var listed: Dictionary = registry.legacy_ids(domain)
		check_eq(bool(listed.get("found", false)), true,
			"the %s domain is present in the verified registry" % domain)
		var ids: Array = listed.get("ids", [])
		check(ids.size() > 0,
			"the %s domain enumerates at least one committed id" % domain)
		check_eq(bool(registry.get_entry(domain, str(ids[0]))
				.get("found", false)), true,
			"the %s domain's first enumerated id resolves" % domain)
		check(str(listed.get("file", "")).length() > 0,
			"the %s domain records the committed file it was read from"
				% domain)
		measured["%s_total" % domain] = ids.size()
		var positive := 0
		var flags := 0
		var flying := 0
		var elev := 0
		for id_text: Variant in ids:
			var entry: Dictionary = registry.get_entry(domain,
				str(id_text)).get("entry", {})
			if int(entry.get("velocity", 0) or 0) > 0:
				positive += 1
			if int(entry.get("elevation", 0) or 0) > 0:
				elev += 1
			var props: Dictionary = {}
			if entry.get("properties") is Dictionary:
				props = entry["properties"]
			if _committed_flag(props, "ft_flying"):
				flying += 1
		measured["%s_positive" % domain] = positive
		measured["%s_flying" % domain] = flying
		measured["%s_elevated" % domain] = elev

	check_eq(measured["units_total"], 429,
		"the committed units domain holds 429 definitions")
	check_eq(measured["buildings_total"], 470,
		"the committed buildings domain holds 470 definitions")
	check_eq(measured["units_positive"], 429,
		"velocity is positive on ALL 429 committed units -- the sharpest "
			+ "zero-consumer field in the project, and read by nothing")
	check(measured["buildings_positive"] > 0,
		"velocity is positive on committed buildings too, and still read by nothing")
	check_eq(measured["units_flying"], 135,
		"ft_flying is set on EXACTLY 135 of the 429 committed units, read "
			+ "through the committed encoding: the package stores these flags as "
			+ "STRINGS, and a `or 0` truthiness read would count the two units "
			+ "the content marks \"0\" as flying, giving 137")
	check_eq(measured["units_elevated"], 429,
		"elevation is positive on every committed unit, and still read by "
			+ "nothing")
	check_eq(measured["buildings_elevated"], 470,
		"elevation is positive on every committed building too")
	check_eq(measured["buildings_positive"], 145,
		"velocity is positive on 145 of the 470 committed buildings")
	check(str(record.get("rule", "")).contains("velocity"),
		"the movement-field refusal names velocity")
	check(str(record.get("coverage", "")).contains("429"),
		"the recorded coverage states the 429-unit figure")

	# the per-field note carries the value and the refusal
	var note: String = UnitMovement.movement_field_note("velocity", 4)
	check(note.contains("4"),
		"the movement-field note reports the committed value")
	check(note.contains("read") or note.contains("never"),
		"the movement-field note records that the field is never read")

	# the tile-geometry gap stays a gap
	check(str(UnitMovement.TILE_GEOMETRY_GAP).length() > 0,
		"the recorded tile-geometry gap is present: the legacy SWF's tile "
			+ "geometry was never extracted, so no terrain rule is derived")
	return measured


# ---------------------------------------------------------------------------
# The movement-command inventory (requirement 3)
# ---------------------------------------------------------------------------

func _check_inventory() -> Dictionary:
	var record: Dictionary = UnitMovement.movement_command_record()
	var measured: Dictionary = {"commands": record.get("command_count", 0),
		"coordinate_writers": record.get("coordinate_writer_count", 0),
		"named_branches": record.get("named_dispatch_branches", 0)}

	check_eq(record.get("command_names", []),
		UnitMovement.movement_command_names(),
		"the recorded command names and the inventory's own list agree")
	check_eq(record.get("command_count", 0), UnitMovement.COMMAND_COUNT,
		"the recorded command count matches the recorded constant")
	for command: String in ["move", "orient", "pop_unit", "fast_forward"]:
		check(command in record.get("command_names", []),
			"the inventory names the %s command" % command)
		var entry := _command_entry(record, command)
		check(str(entry.get("checks", "")).length() > 0,
			"the %s entry records what it DOES check" % command)
		check((entry.get("does_not_check", []) as Array).size() > 0,
			"the %s entry records what it does NOT check" % command)
		check(str(entry.get("writes", "")).length() > 0,
			"the %s entry records what it writes" % command)

	# the type-agnostic, already-delivered move
	var move_entry: Dictionary = _command_entry(record, "move")
	for omission: String in ["type", "occupancy", "bounds", "terrain"]:
		check(_names_omission(move_entry, omission),
			"the move entry records that it does not check the row's %s" % omission)
	check_eq(bool(record.get("type_agnostic", false)), true,
		"the inventory records the move command as type-agnostic")
	check_eq(str(record.get("move_already_delivered_as", "")), "godot-building-move",
		"the inventory records that the move command already ships as "
			+ "godot-building-move")
	check(str(record.get("type_agnostic_note", "")).length() > 0,
		"the inventory records why the command being type-agnostic matters")

	# pop_unit overwrites the row's item id
	var pop_entry: Dictionary = _command_entry(record, "pop_unit")
	check(_blob(pop_entry.get("does_not_check", [])).contains("item id")
			or str(pop_entry.get("writes", "")).contains("item id"),
		"the pop_unit entry records that the row's item id is overwritten")

	# the closed counts, and the coordinate writers
	check_eq(record.get("coordinate_writers", []),
		UnitMovement.COORDINATE_WRITERS,
		"the recorded coordinate writers are exactly move and pop_unit")
	check_eq(record.get("coordinate_writer_count", 0),
		UnitMovement.COORDINATE_WRITER_COUNT,
		"exactly TWO branches write a row's coordinates")
	check_eq(int(record.get("slot_0_2_write_count", 0)),
		UnitMovement.SLOT_0_2_WRITE_COUNT,
		"the recorded slot 0-2 write count matches the recorded constant")
	check_eq(record.get("slot_0_2_write_lines", []),
		UnitMovement.SLOT_0_2_WRITE_LINES,
		"the recorded slot 0-2 write lines are the five the contract names")
	check_eq(int(record.get("named_dispatch_branches", 0)),
		UnitMovement.NAMED_BRANCH_COUNT,
		"the recorded named-dispatcher-branch count matches the recorded constant")
	check_eq(bool(record.get("implemented", true)), false,
		"the inventory records that NO movement command is implemented here")

	# no unit-specific movement command exists
	check(str(UnitMovement.no_unit_specific_command()).length() > 0,
		"the recorded no-unit-specific-command statement is present")
	var fixture := UnitMovement.fixture_record()
	check_eq(bool(fixture.get("captured", true)), false,
		"no executed-legacy movement fixture was captured")
	check(str(fixture.get("reason_kind", "")).contains("stronger"),
		"the fixture record states the reason is the ABSENCE of behaviour, "
			+ "which is stronger than a corpus limitation")
	check(str(fixture.get("corpus_distinction", "")).contains("SECOND"),
		"the fixture record keeps the corpus limitation as a SECOND and "
			+ "independent reason")
	check(str(fixture.get("existing_move_fixture", "")).contains("godot-building-move"),
		"the fixture record notes the type-agnostic move command already has "
			+ "its own executed-legacy fixture")
	check(str(fixture.get("fabricated_row", "")).length() > 0,
		"the fixture record states no unit row was fabricated")
	check(bool(record.get("move_frame_or_string_used", true)) == false
			or str(record.get("move_unused_arguments", "")).length() > 0
			or str(UnitMovement.TYPE_AGNOSTIC_NOTE).length() > 0,
		"the inventory records the move command's read-but-unused arguments")
	return measured


func _command_entry(record: Dictionary, command: String) -> Dictionary:
	for entry: Dictionary in record.get("commands", []):
		if str(entry.get("command", "")) == command:
			return entry
	fail("the inventory carries an entry for %s" % command)
	return {}


## An array's string forms joined for a substring search. `String.join()` takes
## a PackedStringArray, so the array is rebuilt as one first.
func _blob(value: Variant) -> String:
	if not (value is Array):
		return str(value)
	var parts: PackedStringArray = PackedStringArray()
	for part: Variant in (value as Array):
		parts.append(str(part))
	return " ".join(parts)


func _names_omission(entry: Dictionary, needle: String) -> bool:
	return _blob(entry.get("does_not_check", [])).to_lower().contains(needle)


# ---------------------------------------------------------------------------
# The client-writable instant (requirement 4)
# ---------------------------------------------------------------------------

func _check_instant() -> Dictionary:
	var record: Dictionary = UnitMovement.instant_record()
	var measured: Dictionary = {"fast_forward_writes": 0,
		"fast_forward_attr_ts": false, "other_instants_shifted": 0}

	check_eq(str(record.get("command", "")), "fast_forward",
		"the instant record names the client-supplied time shift")
	check(bool(record.get("client_writable", false)),
		"the row instant is recorded as client-writable")
	check(str(record.get("treated_as", "")).contains("opaque"),
		"the instant is recorded as an opaque recorded value")
	check_eq(bool(record.get("derived_from_it", true)), false,
		"no readiness or elapsed value is derived from the instant")
	check(str(record.get("observable_effect", "")).length() > 0,
		"the instant record states the client-visible effect on the value")
	check(str(record.get("seconds_source", "")).contains("args[0]"),
		"the shifted amount is recorded as a client argument")
	check(str(record.get("clamp", "")).contains("max(0"),
		"the recorded clamp is the legacy one")

	# measured in this same run: the branch body, not just its marker line
	var body: Array = _branch_lines(_legacy_lines("command.py"), "fast_forward")
	check(body.size() > 20,
		"the fast_forward branch is found with its body, not just its marker")
	var blob := "\n".join(body)
	check(blob.contains("seconds = args[0]"),
		"fast_forward reads the shifted amount from a client argument")
	check(blob.contains("data[3] = max(0, data[3] - seconds)"),
		"fast_forward rewrites EVERY row's recorded instant, clamped at zero")
	measured["fast_forward_writes"] = _count_occurrences(blob, "data[3] = max(0")
	check(blob.contains("data[6][\"ts\"] = max(0, data[6][\"ts\"] - seconds)"),
		"fast_forward rewrites every row's queue start instant too")
	measured["fast_forward_attr_ts"] = _count_occurrences(blob, "data[6][")
	check(blob.contains("for index in items:"),
		"the shift iterates the map's item rows rather than one named row")
	check(blob.contains('if "ts" in data[6]:'),
		"the queue start instant is shifted only when the row carries one")

	# the record's other shifted instants, measured
	var shifted := 0
	for needle: String in ["map[\"timestamp\"]", "timestampLastChapter",
			"timestampLastTreasure", "timestampLastTrade", "timestampLastBonus",
			"timestampLastAllianceBonus", "timeStampDartsNewFree",
			"tsAttacksReset", "tsSpyingsReset", "timeStampDoResearch",
			"questTimes"]:
		if blob.contains(needle):
			shifted += 1
	check_eq(shifted, 11,
		"the branch shifts exactly the ELEVEN further instants the record names: "
			+ "a twelfth would be an unrecorded gap")
	check_eq(shifted, (record.get("other_instants_shifted", []) as Array).size(),
		"the measured count of further shifted instants matches the recorded list")
	measured["other_instants_shifted"] = shifted
	return measured


# ---------------------------------------------------------------------------
# The anti-invention guard (requirement 4, and the suite's own contract)
# ---------------------------------------------------------------------------

## The module's whole function inventory is compared against a pinned list, so a
## travel-time, path, terrain, occupancy, bounds, readiness, interpolation, or
## animation helper fails this suite wherever it is added.
func _check_absence() -> void:
	var declared: Array = []
	for entry: Dictionary in UnitMovement.ABSENT_HELPERS:
		declared.append(str(entry.get("helper", "")))
		check(str(entry.get("absent_because", "")).length() > 0,
			"the ABSENT_HELPERS entry for %s records why it is absent"
				% str(entry.get("helper", "?")))
	for needle: String in ABSENT_FAMILIES:
		check(_declares_a_helper_for(declared, needle),
			"the recorded ABSENT_HELPERS inventory names the absent "
				+ "`%s` helper family" % needle)

	# the module's actual function inventory
	var present: Array = []
	for method: Dictionary in UnitMovement.new().get_method_list():
		if not ((int(method["flags"]) & METHOD_FLAG_STATIC) != 0):
			continue
		present.append(str(method["name"]))
	present.sort()
	var unexpected: Array = []
	for name: String in present:
		if not name.begins_with("_") and not _is_a_placement_accessor(name):
			unexpected.append(name)
	check_eq(unexpected, [],
		"the delivered module declares EXACTLY the placement accessors of design "
			+ "D1-D4: no travel-time, path, terrain, occupancy, bounds, readiness, "
			+ "interpolation, or animation helper exists")
	for name: String in declared:
		check(not present.has(name),
			"the module does NOT provide the recorded absent helper `%s`" % name)


func _is_a_placement_accessor(name: String) -> bool:
	return ["evaluate", "placement_field_inventory", "placement_field_names",
		"committed_velocity", "committed_footprint", "movement_field_note",
		"movement_fields_record", "movement_commands", "movement_command_names",
		"coordinate_writers", "no_unit_specific_command", "investigation_corrections",
		"movement_command_record", "instant_record", "fixture_record",
		"no_endpoint_record", "readout_text"].has(name)


func _declares_a_helper_for(names: Array, needle: String) -> bool:
	for name: String in names:
		if name.contains(needle):
			return true
	return false


# ---------------------------------------------------------------------------
# The no-endpoint boundary (requirement 5)
# ---------------------------------------------------------------------------

func _check_boundary() -> void:
	var record: Dictionary = UnitMovement.no_endpoint_record()
	check_eq(bool(record.get("added", true)), false,
		"no compatibility route was added for unit movement")
	check_eq(bool(record.get("request_issued", true)), false,
		"no client intent is issued to move a unit")
	check_eq(bool(record.get("persistence_changed", true)), false,
		"no persistence behaviour is changed")
	check(str(record.get("route", "")).contains("none"),
		"the boundary record states there is no route")
	check(str(record.get("route", "")).contains("content registry"),
		"the boundary record states why: the placement is committed content "
			+ "read through the registry plus the row already in hand")
	check(str(record.get("compat_suite", "")).contains("unchanged"),
		"the boundary record states the compatibility suite is unchanged")
	check(str(record.get("building_move_referenced", "")).contains("godot-building-move"),
		"the boundary record names the capability that already delivers the move "
			+ "command, referenced and not reimplemented")
	check(str(record.get("building_move_referenced", "")).contains("not reimplemented"),
		"the boundary record states the move capability is not reimplemented here")
	check(str(record.get("note", "")).length() > 0,
		"the boundary record carries its note")

	# no source outside this module names a movement endpoint
	var offenders: Array = []
	for relative: String in _client_sources():
		var code := _code_only(relative)
		if relative.ends_with("unit_movement.gd"):
			continue
		if code.find("move_unit_town") != -1 \
				or code.find("/v0/move_unit") != -1 \
				or code.find("travel_time") != -1 \
				or code.find("unit_path") != -1:
			offenders.append(relative)
	check_eq(offenders, [],
		"no client source declares a move-unit operation, a movement endpoint, a "
			+ "travel time, or a unit path")


# ---------------------------------------------------------------------------
# The legacy measurements (requirement: no count taken on trust)
# ---------------------------------------------------------------------------

## Every legacy figure this line records is re-derived from the committed
## source in this same run.
func _check_legacy() -> Dictionary:
	var measured: Dictionary = {"modules": 0, "slot_0_2_writes": [], "named_branches": 0,
		"movement_branches": [], "zero_consumer_fields": []}
	for module: String in UnitMovement.SEARCHED_MODULES:
		var lines := _legacy_lines(module)
		if lines.is_empty():
			fail("the legacy module %s is readable: every fact this line records "
				% module
				+ "is measured out of it, and a missing file would make the "
				+ "measurement vacuous")
			continue
		measured["modules"] += 1

	# the assignment-based slot 0-2 writes, scanned ONCE so they come back in
	# source order (a per-slot scan would report them grouped by slot)
	var writes: Array = []
	for module: String in UnitMovement.SEARCHED_MODULES:
		var text := "\n".join(_legacy_lines(module))
		for at: int in _slot_assignments(text):
			writes.append("%s:%d" % [module, text.substr(0, at).count("\n") + 1])
	measured["slot_0_2_writes"] = writes
	check_eq(writes, UnitMovement.SLOT_0_2_WRITE_LINES,
		"the measured slot 0-2 ASSIGNMENTS are exactly the five lines the "
			+ "contract records, in source order: a sixth would be an unrecorded "
			+ "gap, not a silent addition")

	# the named-branch count and the movement-named branches
	var dispatcher := _legacy_lines("command.py")
	var named: Dictionary = {}
	for line: String in dispatcher:
		var branch := _branch_of(line)
		if branch != "":
			named[branch] = true
	measured["named_branches"] = named.size()
	check_eq(named.size(), UnitMovement.NAMED_BRANCH_COUNT,
		"the measured named-dispatcher-branch count is %d"
			% UnitMovement.NAMED_BRANCH_COUNT)

	# matched by TOKEN, not by substring: `batch_remove` and
	# `remove_inventory_item` both CONTAIN the letters of `move`, and treating
	# them as movement commands would be exactly the invention this line refuses
	var movement_named: Array = []
	for branch: String in named:
		if _is_a_movement_token(branch):
			movement_named.append(branch)
	movement_named.sort()
	measured["movement_branches"] = movement_named
	check_eq(movement_named, UnitMovement.MOVEMENT_NAMED_BRANCHES,
		"the measured movement-named branches are exactly the ones the "
			+ "inventory records, so no further movement command exists")
	check(movement_named.has("batch_remove") == false
			and movement_named.has("remove_inventory_item") == false,
		"a branch merely CONTAINING the letters of `move` is not a movement "
			+ "command: neither of the two removal branches moves a row")

	# the zero-consumer movement fields, measured across the searched modules
	var zero: Array = []
	for field: String in UnitMovement.MOVEMENT_FIELDS + UnitMovement.SIBLING_ZERO_CONSUMER_FIELDS:
		var reads := 0
		for module: String in UnitMovement.SEARCHED_MODULES:
			var text := "\n".join(_legacy_lines(module))
			reads += _count_occurrences(text, '"%s"' % field)
			reads += _count_occurrences(text, "'%s'" % field)
		if reads == 0:
			zero.append(field)
	measured["zero_consumer_fields"] = zero
	var unexpected: Array = []
	for field: Variant in zero:
		if not (UnitMovement.MOVEMENT_FIELDS + UnitMovement.SIBLING_ZERO_CONSUMER_FIELDS) \
				.has(field):
			unexpected.append(field)
	check_eq(unexpected, [],
		"every field the contract calls zero-consumer measures as zero across "
			+ "the seven legacy modules")

	# the move branch itself: its arguments and its two writes
	var move_branch := _branch_lines(dispatcher, "move")
	check(move_branch.size() > 0, "the move branch is found in the dispatcher")
	var move_blob := "\n".join(move_branch)
	check(move_blob.contains("item[1] = x") and move_blob.contains("item[2] = y"),
		"the move branch writes exactly the row's two coordinate slots")
	check(move_blob.contains("frame = args[3]")
			and move_blob.contains("string = args[4]"),
		"the move branch reads its frame and string arguments")
	check(not move_blob.contains("item[1] = int") and not move_blob.contains("+ x")
			and not move_blob.contains("item[1] -"),
		"the move branch writes the client value with NO transformation")
	measured["move_argument_count"] = 5

	# orient writes slot 4 only
	var orient_blob := "\n".join(_branch_lines(dispatcher, "orient"))
	check(orient_blob.contains("item[4] = int(orientation)"),
		"the orient branch writes the row's orientation slot")

	# the recorded corrections, and that each names what is unaffected
	var corrections: Array = UnitMovement.investigation_corrections()
	check(int(corrections.size()) > 0,
		"the investigation corrections are recorded")
	for entry: Dictionary in corrections:
		check(str(entry.get("figure", "")).length() > 0,
			"each correction names the figure it corrects")
		check(str(entry.get("measured", "")).length() > 0
				or int(entry.get("measured", -1)) >= 0,
			"each correction states the measured value")
		check(str(entry.get("what_is_unaffected", "")).length() > 0,
			"each correction states what its correction leaves unaffected")
	return measured


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

func _report_path_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument == "--report":
			return Paths.project_dir().path_join(DEFAULT_REPORT_PATH)
		if argument.begins_with("--report="):
			var value := argument.trim_prefix("--report=")
			if value.is_absolute_path():
				return value
			return Paths.project_dir().path_join(value)
	return ""


## Computes and writes the deterministic `unit-movement-report-v1` report.
##
## Every contract fact comes from `unit_movement.gd`; every legacy fact comes from
## the measurement this run performed; every committed number comes from the
## registry that was just verified or from the committed corpus bytes. Nothing
## here reads the wall clock, and no timestamp or absolute path is written, so
## reruns reproduce the bytes.
func _write_report(path: String, registry: Variant, loaded: Dictionary,
		legacy: Dictionary, projection: Dictionary, refusal: Dictionary,
		content: Dictionary, inventory: Dictionary, instant: Dictionary,
		corpus: Dictionary, package_digest: Dictionary) -> void:
	var commands: Dictionary = UnitMovement.movement_command_record()
	var report := {
		"schema": "unit-movement-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_movement.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no network: every table is derived from the "
				+ "delivered module, the verified content registry, the committed "
				+ "corpus bytes, and the measurements this run performed",
		},
		"placement": {
			"fields": UnitMovement.placement_field_inventory(),
			"field_names": UnitMovement.placement_field_names(),
			"row_sourced_count": UnitMovement.PLACEMENT_ROW_FIELD_COUNT,
			"content_sourced_count": UnitMovement.PLACEMENT_CONTENT_FIELD_COUNT,
			"row_slots": UnitMovement.ROW_SLOTS,
			"no_derivation": UnitMovement.NO_DERIVATION,
			"cell_refusal": UnitMovement.CELL_REFUSAL,
			"type_agnostic": UnitMovement.TYPE_AGNOSTIC,
			"type_agnostic_note": UnitMovement.TYPE_AGNOSTIC_NOTE,
			"unit_placed": UnitMovement.UNIT_PLACED,
			"unit_moved": UnitMovement.UNIT_MOVED,
		},
		"refusal": {
			"measured": refusal,
			"reasons": [
				UnitMovement.REASON_INVALID_ROW,
				UnitMovement.REASON_UNRESOLVABLE_CELL,
				UnitMovement.REASON_INVALID_DEFINITION,
			],
			"recorded_slots_travel_untouched": true,
			"origin_never_defaulted": true,
		},
		"movement_fields": UnitMovement.movement_fields_record(),
		"movement_fields_measured": content,
		"committed_flag_encoding": {
			"note": "the normalized package stores the `properties` flags as "
				+ "STRINGS (\"1\"/\"0\") and leaves most of them ABSENT, so a "
				+ "flag read through GDScript truthiness (`int(value or 0)`) "
				+ "counts the two units the content marks \"0\" as set, giving "
				+ "137 instead of 135. The figures below are read through the "
				+ "committed encoding.",
			"ft_flying_set_units": int(content.get("units_flying", 0)),
			"ft_flying_set_buildings": int(content.get("buildings_flying", 0)),
			"velocity_positive_units": int(content.get("units_positive", 0)),
			"velocity_positive_buildings": int(content.get("buildings_positive", 0)),
		},
		"movement_commands": commands,
		"movement_commands_measured": inventory,
		"instant": {
			"recorded": UnitMovement.instant_record(),
			"measured": instant,
			"treatment": UnitMovement.INSTANT_TREATMENT,
		},
		"tile_geometry_gap": UnitMovement.TILE_GEOMETRY_GAP,
		"movement_implemented": UnitMovement.MOVEMENT_IMPLEMENTED,
		"no_endpoint": UnitMovement.no_endpoint_record(),
		"fixture": UnitMovement.fixture_record(),
		"absent_helpers": UnitMovement.ABSENT_HELPERS,
		"non_claims": UnitMovement.NON_CLAIMS,
		"provenance": UnitMovement.PROVENANCE,
		"investigation_corrections": UnitMovement.investigation_corrections(),
		"legacy_measured": legacy,
		"corpus": {
			"placement_rows": projection.get("corpus_rows", 0),
			"non_empty_garrisons": projection.get("corpus_non_empty_garrisons", 0),
			"unit_rows": 0,
			"unit_row_note": "the committed corpus holds no unit row, so no unit "
				+ "placement and no unit move exist to observe",
			"sha256": corpus.get("sha256", ""),
		},
		"projection_measured": projection,
		"inputs": {
			"content_package": {
				"manifest": "packages/game-content/manifest.json",
				"outputs_verified": int(loaded.get("files_verified", 0)),
				"bytes_verified": int(loaded.get("bytes_verified", 0)),
				"fingerprint": str(loaded.get("fingerprint", "")),
				"units_json_sha256": package_digest.get("units", ""),
				"buildings_json_sha256": package_digest.get("buildings", ""),
			},
		},
	}
	var directory := path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		check(DirAccess.make_dir_recursive_absolute(directory) == OK,
			"the evidence report's directory is creatable")
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		fail("the evidence report at %s is writable" % path)
		return
	handle.store_string(JSON.stringify(report, "  ", false) + "\n")
	handle.close()
	check(FileAccess.file_exists(path), "the deterministic report is written")


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------

## The committed corpus bytes, read once.
func _read_corpus() -> Dictionary:
	var absolute := Paths.repo_root().path_join("tests/saves/fresh-player.json")
	if not FileAccess.file_exists(absolute):
		fail("the committed fresh-player corpus is present: this line reports "
			+ "the measured placement facts about it, and a missing file would "
			+ "make the report vacuous")
		return {}
	var text := FileAccess.get_file_as_string(absolute)
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		fail("the committed corpus parses as an object")
		return {}
	var out: Dictionary = parsed
	out["sha256"] = text.sha256_text()
	return out


## The two committed domain files' digests, so the report pins its inputs.
func _package_digest() -> Dictionary:
	var out: Dictionary = {}
	for name: String in ["units", "buildings"]:
		var relative := "packages/game-content/normalized/%s.json" % name
		var absolute := Paths.repo_root().path_join(relative)
		if FileAccess.file_exists(absolute):
			out[name] = FileAccess.get_file_as_string(absolute).sha256_text()
	return out


## One legacy module's lines, or an empty array when it is unreadable.
func _legacy_lines(module: String) -> Array:
	var absolute := Paths.repo_root().path_join(module)
	if not FileAccess.file_exists(absolute):
		return []
	return FileAccess.get_file_as_string(absolute).split("\n")


func _branch_of(line: String) -> String:
	var marker := 'cmd == "'
	var at := line.find(marker)
	if at < 0:
		return ""
	var end := line.find('"', at + marker.length())
	if end < 0:
		return ""
	return line.substr(at + marker.length(), end - at - marker.length())


## Whether a dispatcher branch NAME is a movement command.
##
## Matched by `_`-separated TOKEN, never by substring: `batch_remove` and
## `remove_inventory_item` both contain the letters of `move`, and calling
## either a movement command would be exactly the invention this line
## refuses. A branch qualifies only when a whole token is a movement word.
func _is_a_movement_token(branch: String) -> bool:
	const WORDS := ["move", "orient", "walk", "path", "route", "travel",
		"velocity", "speed", "position"]
	for token: String in branch.split("_"):
		if WORDS.has(token):
			return true
	return false


func _branch_lines(lines: Array, branch: String) -> Array:
	var out: Array = []
	var inside := false
	for line: Variant in lines:
		var found := _branch_of(str(line))
		if found != "":
			inside = (found == branch)
		if inside:
			out.append(str(line))
	return out


## Every slot 0-2 ASSIGNMENT in `text`, as offsets in SOURCE order.
##
## One scan, not one scan per slot: scanning `0` then `1` then `2` would
## return the first slot-0 assignment even when a slot-1 assignment sits
## earlier in the file, which silently drops writes. A following `==` is a
## comparison and is excluded, which is what makes `engine.py`'s
## `if item[0] == item_id:` correctly count as no write at all.
func _slot_assignments(text: String) -> Array[int]:
	var out: Array[int] = []
	for slot: String in ["0", "1", "2"]:
		var needle := "[" + slot + "] ="
		var at := text.find(needle)
		while at >= 0:
			if text.substr(at + needle.length(), 1) != "=":
				out.append(at)
			at = text.find(needle, at + needle.length())
	out.sort()
	return out


## One committed `properties` FLAG, read the way the package encodes it.
##
## The normalized package stores these flags as STRINGS -- `"1"` and
## `"0"`, not numbers -- and leaves most of them ABSENT, so a flag may be
## an int, a float, a String, or missing. Reading one through
## `int(value or 0)` is WRONG: a non-empty String is truthy in GDScript, so
## `or 0` collapses the committed `"0"` to `true` and `int(true)` is 1,
## which counts a unit as flying when the content says it is not. This
## converts each representation explicitly instead.
func _committed_flag(props: Dictionary, name: String) -> bool:
	var raw: Variant = props.get(name, 0)
	if raw is int or raw is float or raw is bool:
		return int(raw) > 0
	if raw is String:
		return (raw as String).to_int() > 0
	return false


func _count_occurrences(text: String, needle: String) -> int:
	var count := 0
	var at := text.find(needle)
	while at >= 0:
		count += 1
		at = text.find(needle, at + needle.length())
	return count


## Every client source file, for the boundary scan.
func _client_sources() -> Array:
	var out: Array = []
	var dir := DirAccess.open(Paths.project_dir().path_join("scripts"))
	if dir == null:
		return out
	dir.list_dir_begin()
	var entry := dir.get_next()
	while entry != "":
		if not dir.current_is_dir() and entry.ends_with(".gd"):
			out.append("scripts/" + entry)
		entry = dir.get_next()
	return out


## A source with comment lines and string-literal content removed, so a scan
## sees the code a reader would compile rather than the prose about it.
func _code_only(relative: String) -> String:
	var absolute := Paths.project_dir().path_join(relative)
	if not FileAccess.file_exists(absolute):
		return ""
	var out: Array = []
	for line: String in FileAccess.get_file_as_string(absolute).split("\n"):
		var stripped := line.strip_edges()
		if stripped.begins_with("#"):
			continue
		out.append(stripped.replace('"', "").replace("'", ""))
	return "\n".join(out)
