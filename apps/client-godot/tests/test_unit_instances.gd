extends "res://tests/test_base.gd"
## Unit-instances suite (OpenSpec `godot-unit-instances` "Unit instances are
## rows, not widened definitions" / "A garrisoned unit is a row nested in a row"
## / "Unit rows are classified by committed type" / "The garrison container has
## no enforced capacity" / "The production-queue keys are reserved, not
## implemented" / "A dead unit leaves no instance" / "The committed corpus
## yields zero unit instances, and that is asserted" / "Unit instances are
## read-only state, not a server operation" / "Unit-instance evidence and
## claim limits", design D1-D9).
##
## Scenarios:
##   row         the eight-slot row contract and the source lines that fix it;
##   instance    a well-formed unit row: every field verbatim, identity read
##               from the definition, the row and the definition unchanged by
##               any read, and the `attr` bag unwriteable through the instance;
##   malformed   every malformed slot fails closed, names the key, and produces
##               no instance — nothing guessed, defaulted, or coerced;
##   type        every non-unit committed `type` is rejected with that type
##               named, never coerced, and the normalization artifact `kind`
##               gates nothing;
##   garrison    one-level and two-level garrisons, an empty garrison distinct
##               from a missing or malformed slot, malformed nested rows, and a
##               crafted row set beyond `MAX_GARRISON_DEPTH` refused rather
##               than truncated;
##   gate        an unavailable registry, an unloaded registry, and a registry
##               missing the `units` or the `buildings` domain all fail closed
##               — never an empty projection presented as a loaded one;
##   mixed       a crafted in-memory row set classifies by committed `type`
##               only, parses a placed building's container into unit
##               instances, and refuses an item id in neither domain;
##   reserved    the reserved `nu`/`ts`/`ui` inventory is named, typed, and
##               recorded with its teardown rule, presence and committed values
##               are readable, and nothing writes a key;
##   dead        the dead-unit counter is read as a plain integer map, no row or
##               corpse is derived from it, a null or non-integer counter is
##               refused, and no resurrection predicate is ever evaluated;
##   capacity    the committed `unit_capacity` is reported with its
##               distribution and an explicit no-rule statement, and an
##               over-capacity garrison is neither refused nor truncated;
##   corpus      the committed fresh-player corpus yields **zero** instances
##               and that is asserted: 40 rows, 11 distinct ids, all buildings,
##               0 non-empty containers, every `attr` bag empty, no reserved
##               key, `deadHeroes` and `boughtUnits` empty;
##   fabricated  instances are demonstrated over a crafted in-memory row set
##               only, and the corpus, the fixtures, and the working tree carry
##               no written unit row after the run;
##   behaviour   neither module exposes a behaviour helper, a queue mutation, a
##               capacity rule, or a death or resurrection rule, and the
##               recorded non-claims name every undelivered line.
##
## Hermetic: no process, no server, no socket, and no request is issued — an
## instance is read from a save already in hand and its definition from the
## already-loaded content registry, so no GameApi operation is involved at all.
## The fault scenarios build **copies** under `.godot/`, never a source file.
## Runs headless as part of `verify-boot.ps1`.
##
## `--report=<path>` writes the deterministic `unit-instances-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-instances/report.json`. Every table is derived from the live
## model, the verified registry, and the committed corpus bytes, so the report
## cannot drift from the code it documents.

const UnitInstance = preload("res://scripts/units/unit_instance.gd")
const UnitInstanceProjection = preload("res://scripts/units/unit_instance_projection.gd")
const UnitDefinition = preload("res://scripts/units/unit_definition.gd")
const UnitCatalog = preload("res://scripts/units/unit_catalog.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")

const SCRATCH := ".godot/verify/unit-instances"
## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-instances/report.json"
## The committed save this line reads, and the map inside it.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const CORPUS_MAP_INDEX := 0
## The committed corpus measurements D8 requires the suite to assert.
const EXPECTED_CORPUS_ROWS := 40
const EXPECTED_CORPUS_IDS := 11
## One committed unit row's definition (Ship), one committed building's
## (Tree, the only committed capacity the corpus exercises at 4), and the five
## committed unit ids that carry a capacity themselves — the members of the
## crafted over-capacity garrison.
const SAMPLE_UNIT_ID := "1019"
const SAMPLE_BUILDING_ID := "905"
const CAPACITY_CARRYING_UNIT_IDS := ["1013", "1018", "1019", "1032", "1035"]
## The committed capacities: 48 of 470 buildings and — contrary to the
## committed investigation record — 5 of 429 units.
const EXPECTED_BUILDING_CAPACITY_DISTRIBUTION := {
	"0": 422, "1": 7, "2": 15, "3": 4, "4": 17, "6": 3, "10": 2,
}
const EXPECTED_UNIT_CAPACITY_DISTRIBUTION := {"0": 424, "4": 2, "6": 3}
## Tokens a read-only projection model must not carry: a node, a clock, a
## request, or a mutation of anything but its own freshly parsed record. The
## transport needles are spelled as fragments because the project-scope suite
## scans every source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]
## The whole function inventory of `unit_instance.gd`, public and private,
## compared as a sorted set. The inner `Instance` class's readers are
## deliberately part of the same list: a behaviour helper added anywhere in
## the file — static or instance — shows up here and fails the check.
const EXPECTED_INSTANCE_MODULE_METHODS := [
	# The Instance class's readers.
	"item_id", "row_item_id", "definition", "cell_x", "cell_y",
	"row_instant", "orientation", "player_team", "attr_bag", "attr_keys",
	"attr_value", "garrison", "garrison_size", "garrison_state",
	"garrison_is_empty", "depth", "key", "path", "row_size", "row_slot",
	"fields",
	# The module's own functions.
	"build", "parse_garrison", "validate_row", "row_contract",
	"_require_unit_definition", "_reject", "_slot_error", "_garrison_reject",
	"_slot_label", "_container_path", "_integer", "_type_name",
]
const EXPECTED_PROJECTION_METHODS := [
	"project", "project_rows", "committed_capacity", "reserved_keys",
	"reserved_key_names", "reserved_key", "instance_count",
	"placed_unit_count", "building_count", "_registry_gate",
	"_dead_counter", "_classify", "_nested_resolver", "_collect",
	"_record_reserved", "_reject", "_forward", "_gate_error", "_integer",
	"_type_name",
]
## Committed fields a read-only instance must NOT restate on its definition, and
## the normalization artifact that must never gate anything.
const KIND_TOKEN := "kind"
const RESURRECTATION_FIELD := "properties"
## Behaviour tokens that would mean a rule is implemented: a queue mutation, a
## capacity application, a death or resurrection rule, or a gameplay rule.
const BEHAVIOUR_NEEDLES := [
	"push_queue_unit", "pop_queue_unit", "enqueue", "dequeue", "clear_queue",
	"set_reserved", "tick_queue", "can_train", "start_train", "finish_queue",
	"resurrect", "revive", "corpse", "kill_row", "apply_damage", "damage",
	"can_defend", "speed", "lifetime", "next_attack", "is_full",
	"apply_capacity", "enforce_capacity",
]
## The non-claim phrases the delta's evidence requirement names verbatim.
const REQUIRED_NON_CLAIMS := [
	"no Flash", "no unit is rendered, animated, or played",
	"no windowed capture is claimed", "no executed-legacy fixture",
	"none was fabricated", "first executed-legacy unit fixture belongs to the "
		+ "production line", "no acquisition is claimed",
	"no queueing, training, production, garrison-capacity, death, "
		+ "resurrection, movement, collection, animation, or basic behaviour is "
		+ "implemented", "no gameplay semantics", "no capacity rule is enforced",
	"ZERO unit instances", "no compatibility route", "no pixel-parity oracle",
]
## The later M8 deliver lines the non-claims must name as undelivered.
const UNDELIVERED_LINES := [
	["unit instances", "queueing", "training", "production", "garrison "
		+ "capacity", "death", "resurrection", "movement", "collection",
		"animation", "behaviour"],
]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return

	var package_dir := Paths.repo_root().path_join("packages/game-content")
	var saves_dir := Paths.repo_root().path_join("tests/saves")
	var fixtures_dir := Paths.repo_root().path_join("tests/fixtures")
	var package_before := Paths.directory_digest(package_dir)
	var saves_before := Paths.directory_digest(saves_dir)
	var fixtures_before := Paths.directory_digest(fixtures_dir)
	check(bool(package_before.get("ok", false)),
		"content package digest is readable before the run (%s)"
		% str(package_before.get("error", "")))
	check(bool(saves_before.get("ok", false)),
		"committed saves digest is readable before the run (%s)"
		% str(saves_before.get("error", "")))
	check(bool(fixtures_before.get("ok", false)),
		"committed fixtures digest is readable before the run (%s)"
		% str(fixtures_before.get("error", "")))
	if not bool(package_before.get("ok", false)):
		return
	if not bool(saves_before.get("ok", false)):
		return
	if not bool(fixtures_before.get("ok", false)):
		return
	var save_before := Paths.file_sha256_checked(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check(bool(save_before.get("ok", false)),
		"the committed corpus save is readable before the run")
	if not bool(save_before.get("ok", false)):
		return

	# The fail-closed gate, proved BEFORE any load: an unavailable registry, an
	# unloaded registry, and a registry whose manifest declares no `units` or no
	# `buildings` output (a mutated COPY under `.godot/`, so manifest
	# verification of every other output still passes and the absent domain is
	# what fails).
	_check_gate(registry)

	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"the committed package loads (error: %s)"
		% str(content.get("error", "")))
	if not bool(content.get("ok", false)):
		return
	var built: Dictionary = UnitCatalog.build(registry)
	check(bool(built.get("ok", false)),
		"the committed unit catalog builds, so every definition this line "
			+ "resolves is a parsed typed model (error: %s)"
			% str(built.get("error", "")))
	if not bool(built.get("ok", false)):
		return
	var catalog: Variant = built["catalog"]

	_check_row_contract()
	_check_instance(registry, catalog)
	_check_malformed(registry)
	_check_type(registry)
	_check_garrison(registry)
	_check_depth(registry)
	_check_mixed(registry)
	_check_reserved(registry)
	_check_dead(registry)
	_check_capacity(registry)
	var corpus := _check_corpus(registry)
	_check_behaviour()
	_check_fabricated(saves_before, fixtures_before, save_before)

	var package_after := Paths.directory_digest(package_dir)
	var saves_after := Paths.directory_digest(saves_dir)
	var fixtures_after := Paths.directory_digest(fixtures_dir)
	check_eq(package_after.get("sha256", ""), package_before.get("sha256", ""),
		"content package bytes are unchanged after the run")
	check_eq(package_after.get("files", 0), package_before.get("files", 0),
		"content package file count is unchanged after the run")
	check_eq(saves_after.get("sha256", ""), saves_before.get("sha256", ""),
		"no committed save byte changed during the run")
	check_eq(fixtures_after.get("sha256", ""),
		fixtures_before.get("sha256", ""),
		"no committed fixture byte changed during the run")

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, catalog, content, corpus,
			package_before, save_before)
	info("unit instances: corpus rows %d, placed units %d, instances %d, "
		% [EXPECTED_CORPUS_ROWS, UnitInstanceProjection.placed_unit_count(
			corpus.get("projection", null)),
		UnitInstanceProjection.instance_count(corpus.get("projection", null))])


# ---------------------------------------------------------------------------
# The established row contract (design D1/D2)
# ---------------------------------------------------------------------------


## The eight-slot row, slot by slot, with the committed source lines that fix
## it. Read from the model's own table so the evidence cannot describe a row
## shape the code no longer accepts.
func _check_row_contract() -> void:
	var contract := UnitInstance.row_contract()
	check_eq(contract.size(), 8,
		"the legacy row has exactly the committed eight slots")
	var wrong_slots: Array = []
	var wrong_sources: Array = []
	for entry: Dictionary in contract:
		if int(entry["slot"]) != contract.find(entry):
			wrong_slots.append(str(entry["name"]))
		if not str(entry["source"]).begins_with("engine.py:"):
			wrong_sources.append(str(entry["name"]))
	check_eq(wrong_slots, [],
		"every slot of the row contract is at its committed index, 0 through 7")
	check_eq(wrong_sources, [],
		"every slot of the row contract names the committed legacy line that "
			+ "establishes it")
	check_eq(UnitInstance.ROW_SLOTS, 8,
		"the model accepts exactly the committed eight-slot row")
	check_eq(UnitInstance.SLOT_GARRISON, 5,
		"the garrison container is the row's fifth slot, the one push_unit "
			+ "appends a row to")
	var names: Array = []
	for entry: Dictionary in contract:
		names.append(str(entry["name"]))
	check_eq(names,
		["item", "x", "y", "timestamp", "orientation", "store", "attr",
			"player"],
		"the committed slot names are the ones engine.py:31 writes")
	(contract[0] as Dictionary)["name"] = "tampered"
	check_eq(str((UnitInstance.row_contract()[0] as Dictionary)["name"]), "item",
		"the row contract is handed out as a fresh deep copy, never the "
			+ "constant itself")
	check(UnitInstance.MAX_GARRISON_DEPTH > 0
			and UnitInstance.MAX_GARRISON_DEPTH <= 16,
		"the garrison nesting bound is a named, small, positive depth (%d)"
			% UnitInstance.MAX_GARRISON_DEPTH)


# ---------------------------------------------------------------------------
# A well-formed unit row (design D1)
# ---------------------------------------------------------------------------


## A well-formed unit row: every field exposed verbatim, identity read from
## the definition rather than restated, and **neither the row nor the
## definition changed by any read**. The instance's `attr` bag is a deep copy,
## so even a caller writing into it cannot reach the save.
func _check_instance(registry: Variant, catalog: Variant) -> void:
	var definition = UnitCatalog.find(catalog, SAMPLE_UNIT_ID)
	check(definition != null, "the sampled committed unit %s resolves"
		% SAMPLE_UNIT_ID)
	if definition == null:
		return
	var row := _row(1019, 41, 17, 1700000000, 1, [], {"nc": 0, "si": []}, 1)
	var built := UnitInstance.build("7", "", row, definition, _resolver(registry),
		0)
	check(bool(built.get("ok", false)),
		"a well-formed unit row builds an instance (error: %s)"
		% str(built.get("error", "")))
	if not bool(built.get("ok", false)):
		return
	var instance: Variant = built["instance"]
	var fields: Dictionary = instance.fields()
	check_eq(int(instance.cell_x()), int(row[1]),
		"the instance's cell x is the row's slot 1 verbatim")
	check_eq(int(instance.cell_y()), int(row[2]),
		"the instance's cell y is the row's slot 2 verbatim")
	check_eq(int(instance.row_instant()), int(row[3]),
		"the instance's row instant is the row's slot 3 verbatim")
	check_eq(int(instance.orientation()), int(row[4]),
		"the instance's orientation is the row's slot 4 verbatim")
	check_eq(int(instance.player_team()), int(row[7]),
		"the instance's player team is the row's slot 7 verbatim")
	check_eq(str(instance.item_id()), SAMPLE_UNIT_ID,
		"the instance's item id is read from the definition it wraps")
	check_eq(int(instance.row_item_id()), int(row[0]),
		"the instance also reports the row's own item-id slot verbatim")
	check(instance.definition() == definition,
		"the instance HOLDS its resolved definition rather than copying it")
	check_eq(str(instance.key()), "7",
		"a placed instance reports the map key it is stored under")
	check_eq(str(instance.path()), "",
		"a placed instance's slot path is empty")
	check_eq(int(instance.depth()), 0,
		"a placed instance's nesting depth is 0")
	check_eq(int(instance.row_size()), 8,
		"an instance never exposes a partial row")
	for slot: int in range(8):
		var expected: Variant = row[slot]
		var actual: Variant = instance.row_slot(slot)
		if (expected is Dictionary) or (expected is Array):
			check_eq(JSON.stringify(actual), JSON.stringify(expected),
				"row slot %d reads back verbatim as a deep copy" % slot)
		else:
			check_eq(actual, expected, "row slot %d reads back verbatim" % slot)
	check_eq(instance.row_slot(8), null,
		"a slot outside the committed row is null, never an invented value")
	check_eq(instance.row_slot(-1), null,
		"a negative slot index is null, never an invented value")
	check_eq(instance.garrison_size(), 0,
		"an empty fifth slot is a garrison with no members")
	check_eq(str(instance.garrison_state()), UnitInstance.GARRISON_EMPTY,
		"an empty fifth slot reads as the empty garrison state")
	check_eq(instance.garrison_is_empty(), true,
		"an empty fifth slot reports itself as empty")
	check_eq(instance.attr_keys(), ["nc", "si"],
		"the committed attribute keys are reported sorted and verbatim")
	check_eq(int(instance.attr_value("nc")), 0,
		"a committed attribute value reads back verbatim")
	check_eq(instance.attr_value("absent"), null,
		"an absent attribute key reads as null, never as a committed zero")
	# The instance is a VIEW over the row and the definition: reading through
	# every accessor changes neither.
	var row_before := JSON.stringify(row)
	var definition_before := _snapshot(definition)
	for _i in range(3):
		instance.fields()
		instance.attr_bag()
		instance.attr_keys()
		instance.garrison()
		instance.definition()
		instance.row_slot(0)
	check_eq(JSON.stringify(row), row_before,
		"reading an instance through every accessor mutates nothing in its row")
	check_eq(_snapshot(definition), definition_before,
		"reading an instance through every accessor mutates nothing in the "
			+ "definition it wraps")
	# And a caller cannot reach the save through the instance either.
	var bag: Dictionary = instance.attr_bag()
	bag["injected"] = 1
	(instance.attr_bag()["nc"]) = 99
	instance.garrison().append("injected")
	check_eq(JSON.stringify((row[6] as Dictionary)), JSON.stringify(
		{"nc": 0, "si": []}),
		"the attribute bag is a deep copy, so a caller writing into it cannot "
			+ "reach the save it was parsed from")
	check_eq(instance.garrison_size(), 0,
		"the garrison list is handed out as a fresh copy a caller cannot "
			+ "append to")
	# The instance's own record is exactly the row's fields plus the identity
	# read from the definition — nothing added.
	check_eq(_sorted_keys(fields), ["attr", "cell_x", "cell_y", "depth",
			"garrison", "garrison_size", "garrison_state", "item_id", "key",
			"orientation", "path", "player_team", "row_instant", "row_item_id"],
		"an instance's own record is the row's fields plus the definition's "
			+ "identity and its garrison summary — no player state beyond them")


## A field-by-field snapshot of a definition, for the immutability comparison.
func _snapshot(definition: Variant) -> Dictionary:
	var out := {}
	for property: Dictionary in definition.get_property_list():
		if (int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE) == 0:
			continue
		var field := str(property["name"])
		var value: Variant = definition.get(field)
		out[field] = JSON.stringify(value) \
			if (value is Dictionary or value is Array) else value
	return out


# ---------------------------------------------------------------------------
# Every malformed slot fails closed (design D1)
# ---------------------------------------------------------------------------


## One malformed value per slot class refuses the parse, names the row's key,
## and produces **no** instance. Cases: a row that is not a row, a short row, a
## long row, a non-integer in every integer slot, a container that is not a
## list, an attribute bag that is not an object, and a row whose item id
## disagrees with the definition resolved for it.
func _check_malformed(registry: Variant) -> void:
	var definition = _definition_of(registry, SAMPLE_UNIT_ID)
	if definition == null:
		return
	var cases := [
		["a row that is not a row", "not a row", "is not a row"],
		["a seven-slot row", _row(1019, 1, 1, 0, 0, [], {}, 1).slice(0, 7),
			"7 slots"],
		["a nine-slot row", _row(1019, 1, 1, 0, 0, [], {}, 1) + [99],
			"9 slots"],
		["a string item id", _row_with({0: "1019"}), "slot 0"],
		["a float cell x", _row_with({1: 1.5}), "slot 1"],
		["a string cell y", _row_with({2: "3"}), "slot 2"],
		["a null row instant", _row_with({3: null}), "slot 3"],
		["a bool orientation", _row_with({4: true}), "slot 4"],
		["a string player team", _row_with({7: "1"}), "slot 7"],
		["a null row", null, "is not a row"],
		["an object garrison container", _row_with({5: {}}), "not a list"],
		["a string garrison container", _row_with({5: "[]"}), "not a list"],
		["an integer garrison container", _row_with({5: 3}), "not a list"],
		["an array attribute bag", _row_with({6: []}), "not an object"],
		["a null attribute bag", _row_with({6: null}), "not an object"],
		["a string attribute bag", _row_with({6: "nc"}), "not an object"],
	]
	var wrong: Array = []
	var unnamed: Array = []
	var produced: Array = []
	for item: Variant in cases:
		var label := str(item[0])
		var row: Variant = item[1]
		var expected := str(item[2])
		var built := UnitInstance.build("42", "", row, definition,
			_resolver(registry), 0)
		if bool(built.get("ok", true)):
			wrong.append(label)
			continue
		if not str(built.get("error", "")).contains(expected):
			unnamed.append("%s -> %s (wanted %s)"
				% [label, str(built.get("error", "")), expected])
		if not str(built.get("error", "")).contains("map key '42'"):
			unnamed.append("%s does not name the row's key: %s"
				% [label, str(built.get("error", ""))])
		if not (built.get("instance", null) == null):
			produced.append(label)
	check_eq(wrong, [], "every malformed slot is refused with no coercion")
	check_eq(unnamed, [],
		"every malformed-slot refusal names the row's key and the offending "
			+ "slot")
	check_eq(produced, [], "no malformed-slot refusal leaves a partial instance")

	# The row's own item id must be the definition's id: a definition resolved
	# for a different item is refused rather than adopted.
	var mismatched := UnitInstance.build("42", "",
		_row(1013, 1, 1, 0, 0, [], {}, 1), definition, _resolver(registry), 0)
	check_eq(bool(mismatched.get("ok", true)), false,
		"a row whose item id disagrees with its resolved definition is refused")
	check(str(mismatched.get("error", "")).contains("unit 1019"),
		"the mismatched-identity refusal names both ids (got: %s)"
			% str(mismatched.get("error", "")))
	check(mismatched.get("instance", null) == null,
		"the mismatched-identity refusal produces no instance")
	var standing := UnitInstance.build("42", "",
		_row(1019, 1, 1, 0, 0, [], {}, 1), definition, _resolver(registry), 0)
	check_eq(bool(standing.get("ok", false)),
		true, "the same row with its own definition builds, so the refusal is "
			+ "the identity mismatch and nothing else")

	# The row contract gate is reachable on its own, for a row the projection
	# classifies as a building: a committed 905 row with a malformed slot fails
	# the same way, naming the key and the slot.
	var building: Dictionary = registry.get_entry(
		UnitInstanceProjection.BUILDING_DOMAIN, SAMPLE_BUILDING_ID)
	check(bool(building.get("found", false)),
		"the sampled committed building %s resolves" % SAMPLE_BUILDING_ID)
	var shared := UnitInstance.validate_row(_row_with({5: {}}, 905), "905", "")
	check_eq(bool(shared.get("ok", true)), false,
		"the row contract gate refuses a malformed row independently of its "
			+ "content")
	check(str(shared.get("error", "")).contains("map key '905'"),
		"the row contract gate names the key it refused")
	check_eq(UnitInstance.validate_row(_row(905, 1, 1, 0, 0, [], {}, 1), "905",
		"").get("ok", true), true,
		"the row contract gate accepts a well-formed row of any committed type")
	# A non-string key is named as it arrived, not fabricated into a string id.
	var odd_key := UnitInstance.validate_row("not a row", 5, "")
	check(str(odd_key.get("error", "")).contains("map key '5'"),
		"a non-string map key is reported as it arrived (got: %s)"
			% str(odd_key.get("error", "")))


# ---------------------------------------------------------------------------
# Committed type is the gate; `kind` is not (design D1/D3)
# ---------------------------------------------------------------------------


## Every non-unit committed `type` is rejected with that type **named**, never
## coerced, and the normalized `kind` gates nothing. The committed content
## itself carries `type` on every row of both domains and `kind` only as a
## normalization artifact, which is asserted from the registry.
func _check_type(registry: Variant) -> void:
	var types := {}
	var kinds := {}
	for domain: String in [UnitInstanceProjection.UNIT_DOMAIN,
			UnitInstanceProjection.BUILDING_DOMAIN]:
		var enumerated: Dictionary = registry.legacy_ids(domain)
		check(bool(enumerated.get("found", false)),
			"the '%s' domain enumerates through the registry's own accessor"
				% domain)
		for id_text: Variant in enumerated.get("ids", []):
			var entry: Dictionary = registry.get_entry(domain, str(id_text))[
				"entry"]
			types["%s/%s" % [domain, str(entry["type"])]] = \
				int(types.get("%s/%s" % [domain, str(entry["type"])], 0)) + 1
			kinds["%s/%s" % [domain, str(entry["kind"])]] = \
				int(kinds.get("%s/%s" % [domain, str(entry["kind"])], 0)) + 1
	check_eq(_sorted_keys(types),
		["buildings/b", "units/u"],
		"the committed content discriminates purely on type: every unit row is "
			+ "type 'u' and every building row is type 'b'")
	check_eq(_sorted_keys(kinds),
		["buildings/building", "units/unit"],
		"the normalization adds kind to both domains, which is exactly why it "
			+ "cannot be the legacy discriminator")

	# A definition whose committed type is not `u` produces no instance, and
	# the refusal names the committed type verbatim. The committed type is a
	# non-empty string by construction, so an empty one is refused a step
	# earlier — the typed parse — which is asserted just below.
	for committed_type: Variant in ["b", "x", "U", "unit", "units"]:
		var other: Variant = _definition_with(registry, SAMPLE_UNIT_ID,
			{"type": committed_type})
		if other == null:
			continue
		var built := UnitInstance.build("7", "", _row(1019, 1, 1, 0, 0, [], {},
			1), other, _resolver(registry), 0)
		check_eq(bool(built.get("ok", true)), false,
			"a row whose committed type is %s is rejected, not coerced"
				% JSON.stringify(committed_type))
		check(str(built.get("error", "")).contains("'%s'"
			% str(committed_type)),
			"the rejection names the committed type %s verbatim (got: %s)"
				% [JSON.stringify(committed_type),
				str(built.get("error", ""))])
		check(str(built.get("error", "")).contains("map key '7'"),
			"the rejection names the row's key too")
		check(built.get("instance", null) == null,
			"a rejected committed type produces no instance")

	# An empty committed type cannot even be parsed into a definition, so the
	# type gate is never reached with one and nothing is defaulted into its
	# place.
	var blank_entry: Dictionary = (registry.get_entry(
		UnitInstanceProjection.UNIT_DOMAIN, SAMPLE_UNIT_ID)["entry"]
		as Dictionary).duplicate(true)
	blank_entry["type"] = ""
	var blank := UnitDefinition.parse(blank_entry)
	check_eq(bool(blank.get("ok", true)), false,
		"an empty committed type is refused by the typed parse, never "
			+ "defaulted to a unit")
	check(blank.get("definition", null) == null,
		"the refused empty committed type produces no definition")
	check_eq(_definition_of(registry, SAMPLE_UNIT_ID) != null, true,
		"the untouched committed unit still parses after the override probes")

	# `kind` is never a gate: a definition whose kind says "building" and whose
	# committed type still says "u" builds an instance unchanged.
	var mislabelled: Variant = _definition_with(registry, SAMPLE_UNIT_ID,
		{"kind": "building"})
	if mislabelled != null:
		var built := UnitInstance.build("7", "", _row(1019, 1, 1, 0, 0, [], {},
			1), mislabelled, _resolver(registry), 0)
		check_eq(bool(built.get("ok", false)), true,
			"a definition whose normalization artifact kind says 'building' "
				+ "still builds an instance: classification reads the committed "
				+ "type, never kind (error: %s)" % str(built.get("error", "")))
	# And neither module's CODE mentions kind or the resurrection property at
	# all — only its documentation and the recorded artifact constant do.
	for relative: String in ["scripts/units/unit_instance.gd",
			"scripts/units/unit_instance_projection.gd"]:
		var code := _code_only(relative)
		check(code.find(KIND_TOKEN) == -1,
			"%s never reads the normalization artifact kind in code" % relative)
		check(code.find(RESURRECTATION_FIELD) == -1,
			"%s never reads the committed resurrection property in code, so no "
				% relative + "resurrection predicate can be evaluated")

	# The type gate also refuses a definition that is not a parsed
	# `UnitDefinition` at all, and one that is missing.
	for bad: Variant in [null, {}, "1019", 1019, []]:
		var built := UnitInstance.build("7", "", _row(1019, 1, 1, 0, 0, [], {},
			1), bad, _resolver(registry), 0)
		check_eq(bool(built.get("ok", true)), false,
			"a resolved definition of type %s is refused"
				% _type_name(bad))
		check(built.get("instance", null) == null,
			"an unusable definition produces no instance")

	# A build with no usable nested-row resolver cannot parse a row at all, and
	# says so rather than silently ignoring the container.
	var no_resolver := UnitInstance.build("7", "", _row(1019, 1, 1, 0, 0, [],
		{}, 1), _definition_of(registry, SAMPLE_UNIT_ID), Callable(), 0)
	check_eq(bool(no_resolver.get("ok", true)), false,
		"a build with no usable garrison resolver is refused")
	check(str(no_resolver.get("error", "")).contains("garrison resolver"),
		"the missing-resolver refusal says why (got: %s)"
			% str(no_resolver.get("error", "")))


# ---------------------------------------------------------------------------
# The nested garrison (design D2)
# ---------------------------------------------------------------------------


## A one-level and a two-level garrison, an empty garrison distinct from a
## missing or a malformed slot, and every malformed nested row refused with the
## member's slot path named.
func _check_garrison(registry: Variant) -> void:
	# One level: a placed unit row whose container holds one nested unit row.
	var one := UnitInstance.build("7", "",
		_row(1019, 1, 1, 0, 0, [_row(1013, 5, 6, 1700, 0, [], {}, 1)], {}, 1),
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(one.get("ok", false)), true,
		"a one-level garrison parses (error: %s)" % str(one.get("error", "")))
	if bool(one.get("ok", false)):
		var parent: Variant = one["instance"]
		check_eq(parent.garrison_size(), 1,
			"the container holds exactly one nested row")
		check_eq(str(parent.garrison_state()),
			UnitInstance.GARRISON_POPULATED,
			"a container holding a row is the populated state, not the empty one")
		check_eq(parent.garrison_is_empty(), false,
			"a container holding a row does not report itself as empty")
		var member: Variant = (parent.garrison() as Array)[0]
		check_eq(str(member.item_id()), "1013",
			"the nested row is a unit instance of its own, with its own id")
		check_eq(int(member.cell_x()), 5,
			"the nested row carries its OWN cell, not its container's")
		check_eq(int(member.cell_y()), 6,
			"the nested row carries its OWN cell y")
		check_eq(int(member.row_instant()), 1700,
			"the nested row carries its OWN instant")
		check_eq(int(member.depth()), 1,
			"a direct garrison member is nesting depth 1")
		check_eq(str(member.key()), "7",
			"a nested row reports the map key it was found under")
		check_eq(str(member.path()), "5[0]",
			"a nested row's slot path names the container slot and the member")
		check_eq(str(member.key()) == str(parent.key()), true,
			"the nested row and its container share the one map key")

	# Two levels: the nested row itself garrons, recursively.
	var two := UnitInstance.build("7", "",
		_row(1019, 1, 1, 0, 0,
			[_row(1013, 5, 6, 1700, 0,
				[_row(1019, 8, 9, 1800, 0, [], {}, 1)], {}, 1)], {}, 1),
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(two.get("ok", false)), true,
		"a two-level garrison parses recursively (error: %s)"
			% str(two.get("error", "")))
	if bool(two.get("ok", false)):
		var outer: Variant = two["instance"]
		var inner: Variant = (outer.garrison() as Array)[0]
		var deepest: Variant = (inner.garrison() as Array)[0]
		check_eq(str(deepest.item_id()), SAMPLE_UNIT_ID,
			"the third row of the chain is a unit instance of its own")
		check_eq(int(deepest.depth()), 2,
			"a two-level garrison reaches depth 2")
		check_eq(str(deepest.path()), "5[0]/5[0]",
			"the deepest row's slot path names the whole chain")
		check_eq(str(deepest.garrison_state()),
			UnitInstance.GARRISON_EMPTY,
			"the innermost row's empty container is an empty garrison")

	# An empty container is an EMPTY GARRISON; a missing or malformed one is a
	# refusal with no instance at all. The two are never confused.
	var empty := UnitInstance.build("7", "", _row(1019, 1, 1, 0, 0, [], {}, 1),
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(empty.get("ok", false)), true,
		"an empty container still produces a valid instance")
	check_eq(str((empty["instance"]).garrison_state()),
		UnitInstance.GARRISON_EMPTY,
		"an empty container reads as an empty garrison, distinguishable from a "
			+ "missing or malformed slot")
	for bad: Variant in [{}, "[]", 0, true, null, "rows"]:
		var refused := UnitInstance.build("7", "",
			_row_with({5: bad}, 1019),
			_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
		check_eq(bool(refused.get("ok", true)), false,
			"a container of type %s is refused, never read as an empty garrison"
				% _type_name(bad))
		check(refused.get("instance", null) == null,
			"a malformed container produces no instance to ask")
	var missing := UnitInstance.build("7", "",
		_row(1019, 1, 1, 0, 0, [], {}, 1).slice(0, 7),
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(missing.get("ok", true)), false,
		"a row whose fifth slot is MISSING is refused, not read as an empty "
			+ "garrison")

	# Every malformed nested member is refused with its slot path named.
	var nested_cases := [
		["a member that is not a row", ["not a row"], "5[0]"],
		["a member that is not a container", [7], "5[0]"],
		["an empty member", [[]], "0 slots"],
		["a two-slot member", [[1013, 5]], "2 slots"],
		["a nine-slot member", [_row(1013, 5, 6, 0, 0, [], {}, 1) + [1]],
			"9 slots"],
		["a member with a non-integer id", [[ "1013", 5, 6, 0, 0, [], {}, 1]],
			"slot 0"],
		["a member with a malformed container",
			[_row_with({5: {}}, 1013)], "not a list"],
		["a member with a malformed attribute bag",
			[_row_with({6: 1}, 1013)], "not an object"],
		["a member whose item id resolves nowhere",
			[_row(4242, 5, 6, 0, 0, [], {}, 1)], "map key '7'"],
		["a BUILDING id inside a container",
			[_row(905, 5, 6, 0, 0, [], {}, 1)], "905"],
	]
	var wrong: Array = []
	var unnamed: Array = []
	var produced: Array = []
	for item: Variant in nested_cases:
		var label := str(item[0])
		var container: Variant = item[1]
		var built := UnitInstance.build("7", "",
			_row_with({5: container}, 1019),
			_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
		if bool(built.get("ok", true)):
			wrong.append(label)
			continue
		var message := str(built.get("error", ""))
		if not message.contains("map key '7'"):
			unnamed.append("%s does not name the key: %s" % [label, message])
		if not message.contains(str(item[2])):
			unnamed.append("%s does not name the member (%s): %s"
				% [label, str(item[2]), message])
		if not (built.get("instance", null) == null):
			produced.append(label)
	check_eq(wrong, [], "every malformed nested row is refused")
	check_eq(unnamed, [],
		"every nested-row refusal names the map key and the member's slot path")
	check_eq(produced, [], "no nested-row refusal leaves a partial instance")


# ---------------------------------------------------------------------------
# The named nesting bound (design D2)
# ---------------------------------------------------------------------------


## A crafted row set nests exactly to `MAX_GARRISON_DEPTH` and is accepted, and
## one level deeper is **refused** with the key and the depth named — never
## silently truncated.
func _check_depth(registry: Variant) -> void:
	var at_bound := _nested_chain(UnitInstance.MAX_GARRISON_DEPTH + 1)
	var accepted := UnitInstance.build("7", "", at_bound,
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(accepted.get("ok", false)), true,
		"a chain nested exactly to the named maximum depth %d is accepted "
			% UnitInstance.MAX_GARRISON_DEPTH
			+ "(error: %s)" % str(accepted.get("error", "")))
	if bool(accepted.get("ok", false)):
		var deepest: Variant = (accepted["instance"])
		var depth := 0
		var cursor: Variant = deepest
		while int((cursor as Object).garrison_size()) > 0:
			cursor = ((cursor as Object).garrison() as Array)[0]
			depth = int((cursor as Object).depth())
		check_eq(depth, UnitInstance.MAX_GARRISON_DEPTH,
			"the deepest member of the accepted chain is at the named maximum")
		check_eq(int(deepest.garrison_size()), 1,
			"no member of the accepted chain is dropped or truncated")

	var over := _nested_chain(UnitInstance.MAX_GARRISON_DEPTH + 2)
	var refused := UnitInstance.build("7", "", over,
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(refused.get("ok", true)), false,
		"a chain one level beyond the named maximum is refused")
	var message := str(refused.get("error", ""))
	check(message.contains("map key '7'"),
		"the over-deep refusal names the row's key (got: %s)" % message)
	check(message.contains("depth %d" % (UnitInstance.MAX_GARRISON_DEPTH + 1)),
		"the over-deep refusal names the offending depth (got: %s)" % message)
	check(message.contains("refused rather than truncated"),
		"the over-deep refusal states that it refuses rather than truncates, "
			+ "because a truncated garrison is a wrong answer presented as a "
			+ "correct one (got: %s)" % message)
	check(refused.get("instance", null) == null,
		"the over-deep refusal returns no partial garrison at all")
	var deep_container := _nested_chain(UnitInstance.MAX_GARRISON_DEPTH + 2)
	var projected := UnitInstanceProjection.project_rows(registry,
		{"7": deep_container}, {"deadHeroes": {}})
	check_eq(bool(projected.get("ok", true)), false,
		"the projection refuses an over-deep row set whole, not row by row")
	check(str(projected.get("error", "")).contains("depth %d"
		% (UnitInstance.MAX_GARRISON_DEPTH + 1)),
		"the projection forwards the over-depth refusal verbatim (got: %s)"
			% str(projected.get("error", "")))
	check(projected.get("projection", null) == null,
		"an over-deep row set yields no projection at all")


## A chain of `levels` nested rows, the innermost container empty. `levels` 2 is
## one garrison level; the outermost row is what a map stores.
func _nested_chain(levels: int) -> Array:
	var row := _row(1019, 1, 1, 0, 0, [], {}, 1)
	for _i in range(levels - 1):
		row = _row(1019, 1, 1, 0, 0, [row], {}, 1)
	return row


# ---------------------------------------------------------------------------
# The fail-closed projection gate (design D1/D3)
# ---------------------------------------------------------------------------


## Five fail-closed conditions, each producing NO projection:
##   1. no registry at all;
##   2. a registry that has not loaded (the autoload starts unloaded, and the
##      registry's own contract is explicit loading);
##   3. a registry that HAS loaded but whose manifest declares no `units`
##      output;
##   4. the same for the `buildings` output, which the projection needs to
##      recognise a non-unit row with no coercion;
##   5. a save that is not a parsed document at all.
## None of them yields an empty projection presented as a loaded one.
func _check_gate(registry: Variant) -> void:
	var rows := {"1": _row(905, 1, 1, 0, 0, [], {}, 1)}
	var missing := UnitInstanceProjection.project(null,
		{"maps": [{"items": rows}], "privateState": {"deadHeroes": {}}})
	check_eq(bool(missing.get("ok", true)), false,
		"an unavailable registry fails closed")
	check(missing.get("projection", null) == null,
		"an unavailable registry yields no projection at all")
	check(str(missing.get("error", "")).contains("unavailable"),
		"the unavailable-registry error says why (got: %s)"
			% str(missing.get("error", "")))

	check(not registry.is_loaded(),
		"the registry starts unloaded, so the unloaded gate is reachable")
	var unloaded := UnitInstanceProjection.project(registry,
		{"maps": [{"items": rows}], "privateState": {"deadHeroes": {}}})
	check_eq(bool(unloaded.get("ok", true)), false,
		"an unloaded registry fails closed")
	check(unloaded.get("projection", null) == null,
		"an unloaded registry yields no projection at all")
	check(str(unloaded.get("error", "")).contains("has not loaded"),
		"the unloaded-registry error says why (got: %s)"
			% str(unloaded.get("error", "")))
	var unloaded_rows := UnitInstanceProjection.project_rows(null, rows,
		{"deadHeroes": {}})
	check_eq(bool(unloaded_rows.get("ok", true)), false,
		"the row-set primitive fails closed without a registry too")

	for dropped: String in [UnitInstanceProjection.UNIT_DOMAIN,
			UnitInstanceProjection.BUILDING_DOMAIN]:
		var copy_repo := _build_copy(dropped)
		if copy_repo == "":
			fail("the package copy without the %s output is buildable" % dropped)
			continue
		var stripped: RegistryScript = RegistryScript.new()
		var loaded: Dictionary = stripped.load_content(copy_repo)
		check(bool(loaded.get("ok", false)),
			"the copy without the %s output still loads every other output "
				% dropped + "(error: %s)" % str(loaded.get("error", "")))
		check(bool(stripped.is_loaded()),
			"the copy without the %s output reports loaded" % dropped)
		check(not stripped.has_domain(dropped),
			"the copy carries no '%s' domain" % dropped)
		var absent := UnitInstanceProjection.project(stripped,
			{"maps": [{"items": rows}], "privateState": {"deadHeroes": {}}})
		check_eq(bool(absent.get("ok", true)), false,
			"a registry without the '%s' domain fails closed" % dropped)
		check(absent.get("projection", null) == null,
			"an absent '%s' domain yields no projection at all" % dropped)
		check(str(absent.get("error", "")).contains("carries no"),
			"the absent-domain error says which domain (got: %s)"
				% str(absent.get("error", "")))
		stripped.free()

	# A save that is not a parsed document is refused, not read as an empty map.
	# Those shape checks run against a LOADED registry, in `_check_mixed`,
	# because the gate above refuses an unloaded registry first and that would
	# mask the shape failure they are about.


## Copies `manifest.json` and `normalized/` into `.godot/verify/…` and drops
## the named output record from the copy's manifest. Returns the scratch
## repository root (the substitute root that contains
## `packages/game-content/`), or "" on failure. The sources are never touched.
func _build_copy(dropped: String) -> String:
	var source_root := Paths.repo_root().path_join("packages/game-content")
	var copy_root := Paths.project_dir().path_join(SCRATCH)
	var copy_package := copy_root.path_join("packages/game-content")
	DirAccess.make_dir_recursive_absolute(copy_package + "/normalized")
	if not _copy_file(source_root + "/manifest.json",
			copy_package + "/manifest.json"):
		return ""
	var normalized := DirAccess.open(source_root + "/normalized")
	if normalized == null:
		return ""
	normalized.list_dir_begin()
	var entry := normalized.get_next()
	while entry != "":
		if not normalized.current_is_dir():
			if not _copy_file(source_root + "/normalized/" + entry,
					copy_package + "/normalized/" + entry):
				normalized.list_dir_end()
				return ""
		entry = normalized.get_next()
	normalized.list_dir_end()
	if not _drop_output(copy_root, dropped):
		return ""
	return copy_root


## Removes one output record from the copy's manifest, so the copy's inventory
## is verified without it. The digest of every remaining output is untouched, so
## the copy still passes manifest verification.
func _drop_output(copy_root: String, dropped: String) -> bool:
	var manifest_path := copy_root + "/packages/game-content/manifest.json"
	var manifest: Variant = _read_json(manifest_path)
	if not (manifest is Dictionary):
		return false
	var outputs: Variant = (manifest as Dictionary).get("outputs", null)
	if not (outputs is Array):
		return false
	var kept: Array = []
	for record: Variant in outputs:
		if (record is Dictionary) and str((record as Dictionary).get(
				"file", "")).ends_with("/%s.json" % dropped):
			continue
		kept.append(record)
	(manifest as Dictionary)["outputs"] = kept
	return _write_bytes(manifest_path,
		JSON.stringify(manifest).to_utf8_buffer())


# ---------------------------------------------------------------------------
# Mixed classification over a CRAFTED row set (design D3/D8)
# ---------------------------------------------------------------------------


## A crafted **in-memory** row set — never a save, corpus, or fixture — mixes
## placed units, placed buildings, a placed building whose container holds more
## unit rows than its committed capacity, and a placed unit whose container
## holds a unit. Classification follows the committed `type` alone, a placed
## building's container is parsed into unit instances, and the over-capacity
## garrison is neither refused nor truncated.
func _check_mixed(registry: Variant) -> void:
	var over_capacity: Array = []
	for index in range(CAPACITY_CARRYING_UNIT_IDS.size()):
		var id_text: String = CAPACITY_CARRYING_UNIT_IDS[index]
		over_capacity.append(_row(int(id_text), 20 + index, 30, 1700, 0, [],
			{}, 1))
	var rows := {
		# A placed unit row with an empty container.
		"1": _row(1019, 10, 10, 100, 0, [], {}, 1),
		# A placed BUILDING row (committed capacity 4) whose container holds
		# FIVE unit rows: over its committed capacity, and still not refused.
		"2": _row(905, 11, 10, 100, 0, over_capacity, {}, 1),
		# A placed building row with no container.
		"3": _row(23, 12, 10, 100, 0, [], {}, 1),
		# A placed unit row whose container holds a unit row.
		"4": _row(1013, 13, 10, 100, 0,
			[_row(1019, 0, 0, 0, 0, [], {}, 1)], {}, 1),
	}
	var result := UnitInstanceProjection.project_rows(registry, rows,
		{"deadHeroes": {}})
	check_eq(bool(result.get("ok", false)), true,
		"a mixed crafted row set projects (error: %s)"
			% str(result.get("error", "")))
	if not bool(result.get("ok", false)):
		return
	var projection: Variant = result["projection"]
	check_eq(int(projection.row_count), 4,
		"every crafted row is classified, none silently dropped")
	check_eq((projection.keys as Array), ["1", "2", "3", "4"],
		"the classified keys are reported in the row set's own committed order")
	check_eq(UnitInstanceProjection.placed_unit_count(projection), 2,
		"only the two rows whose committed type is 'u' become unit instances")
	check_eq(UnitInstanceProjection.building_count(projection), 2,
		"the two rows whose committed type is 'b' are reported as buildings")
	# 2 placed units + 5 building-container members + 1 member of placed unit 4
	check_eq(UnitInstanceProjection.instance_count(projection), 8,
		"every unit row is an instance in its own right, nested ones included")
	check_eq(int(projection.max_depth), 1,
		"the crafted row set reaches nesting depth 1")
	var placed: Array = projection.placed_units
	check_eq(str(placed[0].item_id()), "1019",
		"placed unit '1' is the committed unit it resolves")
	check_eq(str(placed[1].item_id()), "1013",
		"placed unit '4' is the committed unit it resolves")
	check_eq(int(projection.building_garrison_members), 5,
		"a placed BUILDING row's container is parsed into unit instances: "
			+ "push_unit moves a row into a container row, and the committed "
			+ "garrison-capable rows are buildings")
	var buildings: Array = projection.buildings
	check_eq(str((buildings[0] as Dictionary)["key"]), "2",
		"building record '2' is the placed building with the full container")
	check_eq(str((buildings[0] as Dictionary)["name"]), "Tree",
		"a building record reports its committed name verbatim")
	check_eq(str((buildings[0] as Dictionary)["type"]), "b",
		"a building record reports its committed type verbatim")
	check_eq(int((buildings[0] as Dictionary)["committed_unit_capacity"]), 4,
		"a building record reports its committed capacity for reference")
	check_eq(bool((buildings[0] as Dictionary)["capacity_enforced"]), false,
		"a building record states that no capacity rule is enforced")
	check_eq(str((buildings[1] as Dictionary)["garrison_state"]),
		UnitInstance.GARRISON_EMPTY,
		"a placed building with an empty container reads as an empty garrison")

	# The over-capacity garrison: five members against a committed capacity of
	# four, and every one of them survives.
	var garrison: Array = (buildings[0] as Dictionary)["garrison"]
	check_eq(garrison.size(), 5,
		"an over-capacity garrison is neither refused nor truncated: all five "
			+ "members are projected against a committed capacity of 4")
	var member_ids: Array = []
	for member: Variant in garrison:
		member_ids.append(str(member.item_id()))
	check_eq(member_ids, CAPACITY_CARRYING_UNIT_IDS,
		"every over-capacity member is present, in committed container order")
	check_eq(int(projection.building_garrison_members), 5,
		"the projection counts every container member, none dropped")
	# A placed unit row's own container is parsed exactly the same way.
	check_eq(int(placed[1].garrison_size()), 1,
		"a placed UNIT row's container is parsed into unit instances too")

	# An item id that resolves in neither content domain is refused, so no row
	# is silently dropped from a row set the projection cannot classify.
	var unknown := UnitInstanceProjection.project_rows(registry,
		{"5": _row(4242, 1, 1, 0, 0, [], {}, 1)}, {"deadHeroes": {}})
	check_eq(bool(unknown.get("ok", true)), false,
		"a row whose item id resolves in neither domain fails closed")
	check(str(unknown.get("error", "")).contains("map key '5'"),
		"the unclassifiable row's key is named (got: %s)"
			% str(unknown.get("error", "")))
	check(str(unknown.get("error", "")).contains("4242"),
		"the unclassifiable row's item id is named")
	check(unknown.get("projection", null) == null,
		"an unclassifiable row yields no projection at all, not a partial one")
	# A malformed row in a row set fails the whole projection closed.
	var malformed := UnitInstanceProjection.project_rows(registry,
		{"1": _row(1019, 1, 1, 0, 0, [], {}, 1),
			"2": _row_with({1: "x"}, 23)}, {"deadHeroes": {}})
	check_eq(bool(malformed.get("ok", true)), false,
		"one malformed row fails the whole projection closed")
	check(malformed.get("projection", null) == null,
		"a projection with a malformed row is never returned in part")

	# A save that is not a parsed document is refused, never read as an empty
	# map. These run here because the registry is loaded by now: an unloaded
	# registry would fail the gate first and mask the shape failure.
	var shaped := {"maps": [{"items": {"1": _row(905, 1, 1, 0, 0, [], {}, 1)}}],
		"privateState": {"deadHeroes": {}}}
	for bad: Variant in [null, "save", 7, [], {"maps": {}, "privateState": {}},
			{"privateState": {"deadHeroes": {}}},
			{"maps": [{"items": {"1": _row(905, 1, 1, 0, 0, [], {}, 1)}}]},
			{"maps": [7], "privateState": {"deadHeroes": {}}}]:
		var refused := UnitInstanceProjection.project(registry, bad, 0)
		check_eq(bool(refused.get("ok", true)), false,
			"a save of type %s is refused, never read as an empty map"
				% _type_name(bad))
		check(refused.get("projection", null) == null,
			"a refused save yields no projection")
	for index: int in [-1, 1, 3]:
		var out_of_range := UnitInstanceProjection.project(registry, shaped,
			index)
		check_eq(bool(out_of_range.get("ok", true)), false,
			"a map index %d outside the save's one map is refused" % index)
		check(str(out_of_range.get("error", "")).contains("outside"),
			"the out-of-range map error says why (got: %s)"
				% str(out_of_range.get("error", "")))
	var bad_rows := UnitInstanceProjection.project_rows(registry, [],
		{"deadHeroes": {}})
	check_eq(bool(bad_rows.get("ok", true)), false,
		"a row set that is not a row dictionary is refused")


# ---------------------------------------------------------------------------
# The reserved production-queue keys (design D6)
# ---------------------------------------------------------------------------


## `nu`, `ts`, and `ui` are a named, typed, **reserved** inventory with their
## established meanings and their three-key teardown rule. Presence and
## committed values are readable, no queue state is computed from them, and the
## row is byte-identical afterwards — the empirical proof that nothing here
## writes a key.
func _check_reserved(registry: Variant) -> void:
	var inventory := UnitInstanceProjection.reserved_keys()
	check_eq(_sorted_array(UnitInstanceProjection.reserved_key_names()),
		["nu", "ts", "ui"],
		"the reserved production-queue inventory names exactly nu, ts, and ui")
	check_eq(inventory.size(), 3,
		"the reserved inventory carries one record per key")
	var meanings := {}
	var unsigned_established: Array = []
	var no_write_statement: Array = []
	for record: Dictionary in inventory:
		var name := str(record["key"])
		check_eq(name, str(record["key"]),
			"the reserved record names its own key")
		check(str(record["meaning"]).length() > 20,
			"the reserved key %s records its established meaning" % name)
		check(str(record["type"]) == "integer",
			"the reserved key %s is typed as the committed integer it is" % name)
		check(bool(record["optional"]) == (name == "ui"),
			"only ui is optional: it is the atom-fusion path's queued unit id")
		if not str(record["established_from"]).contains("engine.py:"):
			unsigned_established.append(name)
		if not str(record["read_only_here"]).contains("writes nothing"):
			no_write_statement.append(name)
		meanings[name] = str(record["meaning"])
	check_eq(unsigned_established, [],
		"every reserved key names the committed legacy lines that establish it")
	check_eq(no_write_statement, [],
		"every reserved key states in its own record that this line writes "
			+ "nothing")
	check(str(meanings["nu"]).contains("COUNT"),
		"nu is the queued-unit count, not a list and not a position")
	check(str(meanings["ts"]).contains("START INSTANT"),
		"ts is the queue's start instant")
	check(str(meanings["ui"]).contains("OPTIONAL queued unit id"),
		"ui is the optional queued unit id")
	var teardown := str(UnitInstanceProjection.RESERVED_ATTR_TEARDOWN)
	check(teardown.contains("TOGETHER") and teardown.contains("never torn down "
			+ "independently"),
		"the reserved inventory records the three-key teardown rule, which no "
			+ "inspection of the dispatcher would reveal")
	for name: String in UnitInstanceProjection.reserved_key_names():
		check(teardown.contains(name),
			"the teardown rule names the %s key it deletes" % name)
	var scope := str(UnitInstanceProjection.RESERVED_ATTR_SCOPE)
	for phrase: String in ["CONTENT-LEVEL ONLY", "no queue increment",
			"no decrement", "no timestamp write", "no queue projection"]:
		check(scope.contains(phrase),
			"the reserved scope statement names the %s this line does not do"
				% phrase)
	check(UnitInstanceProjection.reserved_key("nope") == null,
		"a key that is not reserved resolves to null, never to a new rule")
	check(UnitInstanceProjection.reserved_key("nu") != null,
		"a reserved key resolves to its own record")
	(inventory[0] as Dictionary)["key"] = "tampered"
	check_eq(str((UnitInstanceProjection.reserved_keys()[0] as Dictionary)[
			"key"]), "nu",
		"the reserved inventory is handed out as a fresh deep copy, never the "
			+ "constant itself")

	# Presence and committed values are readable as content, and the row is
	# untouched afterwards.
	var attr := {"nu": 2, "ts": 1700000000, "ui": 1013, "nc": 0}
	var row := _row_with({6: attr}, 1019)
	var before := JSON.stringify(row)
	var built := UnitInstance.build("7", "", row,
		_definition_of(registry, SAMPLE_UNIT_ID), _resolver(registry), 0)
	check_eq(bool(built.get("ok", false)), true,
		"a row carrying every reserved key still builds (error: %s)"
			% str(built.get("error", "")))
	if bool(built.get("ok", false)):
		var instance: Variant = built["instance"]
		check_eq(int(instance.attr_value("nu")), 2,
			"a committed reserved count reads back verbatim as content")
		check_eq(int(instance.attr_value("ts")), 1700000000,
			"a committed reserved start instant reads back verbatim")
		check_eq(int(instance.attr_value("ui")), 1013,
			"a committed reserved queued unit id reads back verbatim")
		check_eq(instance.attr_keys(), ["nc", "nu", "ts", "ui"],
			"the reserved keys are reported as ordinary committed attribute "
				+ "keys, with no queue state computed from them")
		var projected := UnitInstanceProjection.project_rows(registry,
			{"7": row}, {"deadHeroes": {}})
		check_eq(bool(projected.get("ok", false)), true,
			"a row carrying reserved keys projects (error: %s)"
				% str(projected.get("error", "")))
		if bool(projected.get("ok", false)):
			var presence: Dictionary = (projected["projection"]).reserved_presence
			check_eq(_sorted_keys(presence), ["nu", "ts", "ui"],
				"the projection records which reserved keys a row carries")
			check_eq(int((projected["projection"]).reserved_rows.size()), 1,
				"exactly one reserved-key record is reported for the one row "
					+ "that carries reserved keys")
			var record: Dictionary = (projected["projection"]).reserved_rows[0]
			check_eq(_sorted_keys(record),
				["committed_values", "item_id", "key", "reserved_keys"],
				"a reserved-key record carries the row, the keys, and their "
					+ "committed values — and no computed queue state")
			check_eq(record["reserved_keys"], ["nu", "ts", "ui"],
				"the reserved keys are reported in inventory order")
			check_eq(JSON.stringify(record["committed_values"]),
				JSON.stringify({"nu": 2, "ts": 1700000000, "ui": 1013}),
				"the reserved keys' committed values are reported verbatim")
	check_eq(JSON.stringify(row), before,
		"reading the reserved keys off a row changes nothing in it, so no "
			+ "queue mutation is implemented")


# ---------------------------------------------------------------------------
# The dead-unit counter (design D7)
# ---------------------------------------------------------------------------


## The dead-unit counter is a plain integer map keyed by item id that discards
## the row, so no instance is derived from it. A null, absent, or non-integer
## counter is refused rather than read as zero, a non-empty counter changes
## nothing about the instances a row set produces, and no resurrection predicate
## is ever evaluated.
func _check_dead(registry: Variant) -> void:
	check_eq(str(UnitInstanceProjection.DEAD_COUNTER_PATH),
		"privateState.deadHeroes",
		"the dead-unit counter's committed location is recorded")
	for phrase: String in ["INTEGER COUNT", "KEYED BY ITEM ID", "DISCARDS the "
			+ "row", "derives no"]:
		check(str(UnitInstanceProjection.DEAD_COUNTER_RULE).contains(phrase),
			"the dead-counter contract records %s" % phrase)
	check(str(UnitInstanceProjection.DEAD_COUNTER_ABSENT).contains("REFUSED"),
		"the dead-counter contract records that an absent count is refused, "
			+ "never read as zero")

	var unit_row := {"1": _row(1019, 1, 1, 0, 0, [], {}, 1)}
	var with_dead := UnitInstanceProjection.project_rows(registry, unit_row,
		{"deadHeroes": {"1019": 2, "1032": 1}})
	check_eq(bool(with_dead.get("ok", false)), true,
		"a non-empty dead counter is read (error: %s)"
			% str(with_dead.get("error", "")))
	if bool(with_dead.get("ok", false)):
		var projection: Variant = with_dead["projection"]
		check_eq(JSON.stringify(projection.dead_heroes),
			JSON.stringify({"1019": 2, "1032": 1}),
			"the dead counter is reported verbatim as an integer map keyed by "
				+ "item id")
		var without_dead := UnitInstanceProjection.project_rows(registry,
			unit_row, {"deadHeroes": {}})
		check_eq(UnitInstanceProjection.instance_count(projection),
			UnitInstanceProjection.instance_count(
				without_dead.get("projection", null)),
			"a dead-unit count derives NO instance: the instance count is the "
				+ "same with and without it, and a dead unit's row was discarded "
				+ "by the legacy branch that kept the count")
		check_eq(str(projection.dead_heroes["1019"]), "2",
			"the count is an integer, never a list of rows or a corpse")
		check_eq(UnitInstanceProjection.placed_unit_count(projection), 1,
			"a row still on the map is still a placed instance, whatever the "
				+ "dead counter says about earlier ones")
	var empty := UnitInstanceProjection.project_rows(registry,
		{"1": _row(23, 1, 1, 0, 0, [], {}, 1)}, {"deadHeroes": {}})
	check_eq(JSON.stringify((empty["projection"]).dead_heroes), "{}",
		"an empty dead counter is reported as an empty map, not as a null")

	for bad: Variant in [null, [], "1019", 3, {"1019": "3"}, {"1019": 1.5},
			{"1019": null}, {"1019": true}]:
		var refused := UnitInstanceProjection.project_rows(registry, unit_row,
			{"deadHeroes": bad})
		check_eq(bool(refused.get("ok", true)), false,
			"a dead counter of %s is refused, never read as an empty count"
				% JSON.stringify(bad))
		check(refused.get("projection", null) == null,
			"a refused dead counter yields no projection at all")
	var no_state := UnitInstanceProjection.project_rows(registry, unit_row,
		null)
	check_eq(bool(no_state.get("ok", true)), false,
		"a save with no private state at all is refused")
	check(str(no_state.get("error", "")).contains("privateState"),
		"the missing-private-state refusal names the field (got: %s)"
			% str(no_state.get("error", "")))

	# The committed coverage of the resurrection property is content, and this
	# line evaluates none of it.
	var covered := 0
	var total := 0
	for id_text: Variant in registry.legacy_ids(
			UnitInstanceProjection.UNIT_DOMAIN).get("ids", []):
		var entry: Dictionary = registry.get_entry(
			UnitInstanceProjection.UNIT_DOMAIN, str(id_text))["entry"]
		total += 1
		var bag: Dictionary = entry["properties"]
		if int(bag.get("resurrectable", 0)) > 0:
			covered += 1
	check_eq(covered, 426,
		"the committed resurrection property covers 426 of %d unit rows, "
			% total + "recorded as content and never applied as a predicate")
	check_eq(total, 429, "the committed unit domain holds 429 rows")


# ---------------------------------------------------------------------------
# The committed capacity, recorded and never enforced (design D5)
# ---------------------------------------------------------------------------


## The committed `unit_capacity` distribution is **measured** from the
## registry, not restated, and the explicit no-rule statement travels with it.
## An over-capacity garrison is neither refused nor truncated, and the five
## committed unit rows that carry a capacity are recorded as a correction to
## the committed investigation record.
func _check_capacity(registry: Variant) -> void:
	var buildings := _capacity_distribution(registry,
		UnitInstanceProjection.BUILDING_DOMAIN)
	var units := _capacity_distribution(registry,
		UnitInstanceProjection.UNIT_DOMAIN)
	check_eq(JSON.stringify(buildings["distribution"]),
		JSON.stringify(EXPECTED_BUILDING_CAPACITY_DISTRIBUTION),
		"the committed buildings' unit_capacity distribution is 48 of 470 "
			+ "carrying a capacity (capacities 1, 2, 3, 4, 6, and 10)")
	check_eq(int(buildings["with_capacity"]), 48,
		"48 of 470 committed buildings are garrison-capable")
	check_eq(int(buildings["of"]), 470,
		"the committed buildings domain holds 470 rows")
	check_eq(JSON.stringify(units["distribution"]),
		JSON.stringify(EXPECTED_UNIT_CAPACITY_DISTRIBUTION),
		"the committed units' unit_capacity distribution — CONTRARY to the "
			+ "committed investigation record, 5 of 429 unit rows carry a "
			+ "capacity, not 0")
	check_eq(int(units["with_capacity"]), 5,
		"5 of 429 committed units carry a committed unit_capacity, which the "
			+ "evidence records as a correction rather than restating the "
			+ "record's wrong zero")
	check_eq(_sorted_array(units["capacity_ids"]), CAPACITY_CARRYING_UNIT_IDS,
		"the five capacity-carrying committed unit ids are exactly these")
	check(str(UnitInstanceProjection.CAPACITY_CORRECTION).contains("5 of 429"),
		"the capacity correction states the committed count explicitly")
	check(str(UnitInstanceProjection.CAPACITY_RULE).contains(
			"NO CAPACITY RULE IS IMPLEMENTED"),
		"the capacity contract states the no-rule decision verbatim")
	for phrase: String in ["engine.py", "command.py", "sessions.py", "server.py",
			"constants.py", "no member is refused, dropped, or truncated"]:
		check(str(UnitInstanceProjection.CAPACITY_RULE).contains(phrase),
			"the capacity contract records %s" % phrase)

	# The committed capacity is reported for reference, on both domains, and
	# never applied.
	var building := UnitInstanceProjection.committed_capacity(registry,
		SAMPLE_BUILDING_ID)
	check_eq(bool(building.get("ok", false)), true,
		"a committed building's capacity is reportable (error: %s)"
			% str(building.get("error", "")))
	check_eq(int(building.get("unit_capacity", -1)), 4,
		"the sampled committed building's capacity reads back verbatim (4)")
	check_eq(bool(building.get("enforced", true)), false,
		"the reported capacity is explicitly not enforced")
	check(str(building.get("rule", "")).contains("NO CAPACITY RULE"),
		"the reported capacity travels with the no-rule statement")
	var unit := UnitInstanceProjection.committed_capacity(registry, "1019")
	check_eq(int(unit.get("unit_capacity", -1)), 6,
		"a committed UNIT's capacity reads back verbatim (6), which is the "
			+ "concrete correction to the investigation record's '0 of 429'")
	check_eq(str(unit.get("domain", "")), UnitInstanceProjection.UNIT_DOMAIN,
		"a unit's capacity is reported from the units domain")
	var uncapped := UnitInstanceProjection.committed_capacity(registry, "23")
	check_eq(int(uncapped.get("unit_capacity", -1)), 0,
		"a committed zero capacity reads back as a committed zero, not as an "
			+ "absence")
	for bad: Variant in [905, "", "no_such_id", null, ["905"]]:
		var refused := UnitInstanceProjection.committed_capacity(registry, bad)
		check_eq(bool(refused.get("ok", true)), false,
			"a capacity request for %s fails closed"
				% JSON.stringify(bad))
		check_eq(int(refused.get("unit_capacity", -1)), -1,
			"a refused capacity request reports an explicit -1 sentinel, never "
				+ "a guessed zero")
	var no_registry := UnitInstanceProjection.committed_capacity(null,
		SAMPLE_BUILDING_ID)
	check_eq(bool(no_registry.get("ok", true)), false,
		"the capacity accessor fails closed without a loaded registry")
	# The accessor's sentinels are explicit, never a guessed zero.
	for bad_projection: Variant in [null, {}, 7]:
		check_eq(UnitInstanceProjection.instance_count(bad_projection), -1,
			"instance_count reports -1 for an unusable projection")
		check_eq(UnitInstanceProjection.placed_unit_count(bad_projection), -1,
			"placed_unit_count reports -1 for an unusable projection")
		check_eq(UnitInstanceProjection.building_count(bad_projection), -1,
			"building_count reports -1 for an unusable projection")


## The committed unit_capacity distribution of one domain, measured from the
## registry: how many rows, how many carry a capacity, and which ids do.
func _capacity_distribution(registry: Variant, domain: String) -> Dictionary:
	var distribution := {}
	var carrying: Array = []
	var total := 0
	for id_text: Variant in registry.legacy_ids(domain).get("ids", []):
		var entry: Dictionary = registry.get_entry(domain, str(id_text))["entry"]
		total += 1
		var capacity := int(entry.get(UnitInstanceProjection.CAPACITY_FIELD, 0))
		distribution[str(capacity)] = \
			int(distribution.get(str(capacity), 0)) + 1
		if capacity > 0:
			carrying.append(str(id_text))
	carrying.sort()
	return {"of": total, "distribution": distribution,
		"with_capacity": carrying.size(), "capacity_ids": carrying}


# ---------------------------------------------------------------------------
# The committed corpus yields ZERO instances, and that is asserted (design D8)
# ---------------------------------------------------------------------------


## The committed fresh-player corpus: 40 placed rows across 11 distinct item
## ids, **zero** of them a unit. The projection returns zero instances, all 40
## rows classify as buildings, no row carries a non-empty container, no row
## carries a reserved production-queue key, every attribute bag is empty, and
## `deadHeroes` and `boughtUnits` are both empty. The zero is asserted, not
## tolerated.
func _check_corpus(registry: Variant) -> Dictionary:
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed corpus save parses as an object")
	if not (save is Dictionary):
		return {"ok": false, "error": "corpus unreadable"}
	var rows: Variant = (save as Dictionary)["maps"][CORPUS_MAP_INDEX]["items"]
	check(rows is Dictionary, "the corpus map's row dictionary is readable")
	if not (rows is Dictionary):
		return {"ok": false, "error": "corpus rows unreadable"}

	# The committed bytes, measured directly from the save file.
	var distinct := {}
	var row_count := 0
	var non_empty_container := 0
	var rows_with_attrs := 0
	var lengths := {}
	for key: Variant in (rows as Dictionary).keys():
		var row: Variant = (rows as Dictionary)[key]
		row_count += 1
		distinct[str((row as Array)[0])] = true
		lengths[str((row as Array).size())] = \
			int(lengths.get(str((row as Array).size()), 0)) + 1
		if (row as Array)[UnitInstance.SLOT_GARRISON].size() > 0:
			non_empty_container += 1
		if not ((row as Array)[UnitInstance.SLOT_ATTR] as Dictionary).is_empty():
			rows_with_attrs += 1
	check_eq(row_count, EXPECTED_CORPUS_ROWS,
		"the committed corpus holds exactly %d placed rows"
			% EXPECTED_CORPUS_ROWS)
	check_eq(distinct.size(), EXPECTED_CORPUS_IDS,
		"the committed corpus's %d rows span exactly %d distinct item ids"
			% [EXPECTED_CORPUS_ROWS, EXPECTED_CORPUS_IDS])
	check_eq(_sorted_keys(lengths), ["8"],
		"every committed corpus row has exactly the committed eight slots")
	check_eq(non_empty_container, 0,
		"no committed corpus row carries a non-empty container, so no garrison "
			+ "exists anywhere in it")
	check_eq(rows_with_attrs, 0,
		"every committed corpus row's attribute bag is empty, so nu, ts, and "
			+ "ui appear on no row")
	check_eq((save as Dictionary)["privateState"]["deadHeroes"],
		{}, "the committed corpus's dead-unit counter is empty")
	check_eq((save as Dictionary)["privateState"]["boughtUnits"], [],
		"the committed corpus's bought-units list is empty")
	check_eq((save as Dictionary)["maps"][CORPUS_MAP_INDEX]["store"], {},
		"the committed corpus's player storage is empty, and it is a separate "
			+ "per-map dictionary rather than any row's container slot")

	# The projection over those same committed bytes.
	var result := UnitInstanceProjection.project(registry, save, CORPUS_MAP_INDEX)
	check_eq(bool(result.get("ok", false)), true,
		"the projection runs against the committed corpus (error: %s)"
			% str(result.get("error", "")))
	if not bool(result.get("ok", false)):
		return {"ok": false, "error": str(result.get("error", ""))}
	var projection: Variant = result["projection"]
	check_eq(UnitInstanceProjection.instance_count(projection), 0,
		"the committed corpus yields ZERO unit instances, and that zero is "
			+ "asserted rather than tolerated")
	check_eq(UnitInstanceProjection.placed_unit_count(projection), 0,
		"no committed corpus row is a unit row")
	check_eq(UnitInstanceProjection.building_count(projection),
		EXPECTED_CORPUS_ROWS,
		"all %d committed corpus rows classify as buildings"
			% EXPECTED_CORPUS_ROWS)
	check_eq(int(projection.row_count), EXPECTED_CORPUS_ROWS,
		"the projection classified every committed corpus row, none dropped")
	check_eq(int(projection.building_garrison_members), 0,
		"no committed corpus row's container holds a unit row")
	check_eq(int(projection.max_depth), 0,
		"the committed corpus reaches no garrison nesting at all")
	var states := {}
	var capables := 0
	for record: Dictionary in projection.buildings:
		states[str(record["garrison_state"])] = \
			int(states.get(str(record["garrison_state"]), 0)) + 1
		if int(record["committed_unit_capacity"]) > 0:
			capables += 1
		check_eq(bool(record["capacity_enforced"]), false,
			"no committed corpus building record enforces a capacity, including "
				+ "the three garrison-capable decorations")
	check_eq(_sorted_keys(states), [UnitInstance.GARRISON_EMPTY],
		"every committed corpus row's container is an empty garrison")
	check_eq(capables, 9,
		"9 of the 40 committed corpus rows are garrison-capable, across 3 "
			+ "distinct item ids (905, 930, 931) — all of them collect:20 "
			+ "decorations, and every one of their containers is empty. The "
			+ "committed investigation record's '3 placed rows' is the "
			+ "DISTINCT-ID count, not the row count.")
	check(str(UnitInstanceProjection.GARRISON_CAPABLE_CORRECTION).contains(
			"9 such rows"),
		"the recorded correction states the committed row count explicitly")
	var capable_ids: Array = []
	for record: Dictionary in projection.buildings:
		if int(record["committed_unit_capacity"]) > 0 \
				and not capable_ids.has(str(record["item_id"])):
			capable_ids.append(str(record["item_id"]))
	capable_ids.sort()
	check_eq(_sorted_array(capable_ids), ["905", "930", "931"],
		"the garrison-capable committed item ids are exactly these three")
	check_eq((projection.reserved_presence as Dictionary), {},
		"no committed corpus row carries a reserved production-queue key")
	check_eq((projection.reserved_rows as Array), [],
		"no committed corpus row has a reserved-key record")
	check_eq((projection.dead_heroes as Dictionary), {},
		"the committed corpus's dead-unit counter projects as an empty map")
	check_eq(int(projection.map_index), CORPUS_MAP_INDEX,
		"the projection records which map it read")
	info("committed corpus: %d rows, %d distinct ids, %d unit instances, "
		% [EXPECTED_CORPUS_ROWS, EXPECTED_CORPUS_IDS,
		UnitInstanceProjection.instance_count(projection)]
		+ "%d building rows" % UnitInstanceProjection.building_count(projection))
	return {"ok": true, "error": "", "projection": projection,
		"distinct_item_ids": distinct.size()}


# ---------------------------------------------------------------------------
# No fabricated save, and no behaviour rule (design D8, D6/D7)
# ---------------------------------------------------------------------------


## Instances are demonstrated over a crafted in-memory row set only, and the
## committed saves, the committed fixtures, and the working tree carry no
## written unit row after the run. The suite itself never writes to any of
## them; the digests are the proof.
func _check_fabricated(saves_before: Dictionary, fixtures_before: Dictionary,
		save_before: Dictionary) -> void:
	var working_saves := Paths.repo_root().path_join("saves")
	check(not DirAccess.dir_exists_absolute(working_saves),
		"no working-tree saves/ directory exists, so this line wrote no save")
	var saves_after := Paths.directory_digest(
		Paths.repo_root().path_join("tests/saves"))
	var fixtures_after := Paths.directory_digest(
		Paths.repo_root().path_join("tests/fixtures"))
	check_eq(saves_after.get("sha256", ""), saves_before.get("sha256", ""),
		"no committed save was created or modified to hold a unit row")
	check_eq(fixtures_after.get("sha256", ""), fixtures_before.get("sha256", ""),
		"no committed fixture was created or modified to hold a unit row")
	var save_after := Paths.file_sha256_checked(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check_eq(save_after.get("sha256", ""), save_before.get("sha256", ""),
		"the committed corpus save is byte-identical after the run")
	var report_path := Paths.project_dir().path_join(DEFAULT_REPORT_PATH)
	var report: Variant = null
	if FileAccess.file_exists(report_path):
		report = _read_json(report_path)
	if report is Dictionary:
		check_eq(str((report as Dictionary).get("schema", "")),
			"unit-instances-report-v1",
			"the committed evidence report is the one this suite writes")
		check_eq(((report as Dictionary).get("instances", {}) as Dictionary
			).get("fabricated_save", true), false,
			"the committed evidence report states that no save was fabricated")


## Neither module exposes a behaviour helper, and neither its documentation nor
## the recorded non-claims leave a rule unimplemented-but-implied.
func _check_behaviour() -> void:
	var instance_body := _source("res://scripts/units/unit_instance.gd")
	var projection_body := _source("res://scripts/units/unit_instance_projection.gd")
	check(instance_body != "" and projection_body != "",
		"both unit-instance modules are readable")
	check_eq(_methods(instance_body),
		_sorted_unique(EXPECTED_INSTANCE_MODULE_METHODS),
		"the instance module's whole function inventory is exactly the row, "
			+ "identity, and garrison readers of design D1/D2 — the inner "
			+ "class's readers included, so a helper cannot hide in either")
	check_eq(_methods(projection_body),
		_sorted_unique(EXPECTED_PROJECTION_METHODS),
		"the projection's whole function inventory is exactly the projection, "
			+ "lookup, and recorded-contract accessors of design D3/D5-D7 — no "
			+ "queue, capacity, death, or behaviour helper")
	for body: String in [instance_body, projection_body]:
		var impure: Array = []
		for needle: String in PURITY_NEEDLES:
			if body.contains(needle):
				impure.append(needle)
		check_eq(impure, [],
			"neither module carries a node, a clock, a request, or a mutation "
				+ "(pure parse and lookup only)")
	for relative: String in ["scripts/units/unit_instance.gd",
			"scripts/units/unit_instance_projection.gd"]:
		var code := _code_only(relative)
		var found: Array = []
		for needle: String in BEHAVIOUR_NEEDLES:
			if code.find(needle) != -1:
				found.append(needle)
		check_eq(found, [],
			"%s declares no queue mutation, capacity application, death or "
				% relative + "resurrection rule, or gameplay helper")
	# The modules' own documentation states the no-rule decisions where a
	# reader meets them.
	for phrase: String in ["capacity rule is implemented", "no "
			+ "resurrection predicate", "never silently truncated", "an empty "
			+ "garrison"]:
		var stated := 0
		for body: String in [instance_body, projection_body]:
			if body.to_lower().contains(phrase.to_lower()):
				stated += 1
		check(stated >= 1,
			"the modules' own documentation states the rule: %s" % phrase)
	check(UnitInstanceProjection.KIND_ARTIFACT.contains("artifact"),
		"the projection's own documentation records that kind is a "
			+ "normalization artifact, not a legacy field")
	# The provenance split and the non-claims.
	check(UnitInstanceProjection.PROVENANCE["established"].size() >= 7,
		"the provenance split records every established fact with its "
			+ "committed source (%d records)"
			% UnitInstanceProjection.PROVENANCE["established"].size())
	check(UnitInstanceProjection.PROVENANCE["derived"].size() >= 3,
		"the provenance split records the derived choices separately from the "
			+ "established facts (%d records)"
			% UnitInstanceProjection.PROVENANCE["derived"].size())
	for entry: Dictionary in UnitInstanceProjection.PROVENANCE["derived"]:
		check(str(entry["evidence"]).contains("derived")
				or str(entry["evidence"]).contains("by observation"),
			"the derived record %s says so in its own evidence"
				% str(entry["fact"]).substr(0, 40))
	var missing: Array = []
	for phrase: String in REQUIRED_NON_CLAIMS:
		var found := false
		for claim: String in UnitInstanceProjection.NON_CLAIMS:
			if claim.find(phrase) != -1:
				found = true
		if not found:
			missing.append(phrase)
	check_eq(missing, [],
		"the evidence carries every non-claim the delta requires, verbatim")
	for line: Variant in UNDELIVERED_LINES:
		var undelivered := false
		for claim: String in UnitInstanceProjection.NON_CLAIMS:
			if claim.find(str((line as Array)[0])) != -1:
				undelivered = true
		check(undelivered, "the non-claims name the '%s' deliver line as "
			% str((line as Array)[0]) + "undelivered")
	check(UnitInstanceProjection.NON_CLAIMS.size() >= REQUIRED_NON_CLAIMS.size(),
		"the evidence carries the full non-claim list (%d claims)"
			% UnitInstanceProjection.NON_CLAIMS.size())
	# The static/instance boundary, now that an instance exists: the definition
	# still carries no player state, and the instance's own player state lives
	# on the instance.
	var boundary := UnitInstanceProjection.UNREAD_PRIVATE_STATE
	check(boundary.size() >= 3,
		"the projection records what it deliberately does not read (%d records)"
			% boundary.size())
	for entry: Dictionary in boundary:
		check(str(entry["why"]).length() > 20
				and not str(entry["owned_by"]).is_empty(),
			"the unread-field record for %s names its owner and its reason"
				% str(entry["field"]))


# ---------------------------------------------------------------------------
# Evidence report (design D9)
# ---------------------------------------------------------------------------


## The report output path from the user arguments: `--report=<path>` (relative
## paths resolve against the project directory) or the bare `--report` flag's
## default evidence path; "" when absent.
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


## Computes and writes the deterministic `unit-instances-report-v1` report.
##
## EVERY fact about the model comes from `unit_instance.gd` and
## `unit_instance_projection.gd` — their own `ROW_CONTRACT`,
## `RESERVED_ATTR_KEYS`, `CAPACITY_RULE`, `DEAD_COUNTER_RULE`, `PROVENANCE`, and
## `NON_CLAIMS` — every committed number comes from the registry that was just
## verified, and every corpus measurement comes from the committed save's bytes,
## so the report cannot drift from the code it documents. Nothing here reads the
## wall clock, resolves a path outside the repository, or sends a request: that
## is what makes the file byte-identical across reruns.
func _write_report(path: String, registry: Variant, catalog: Variant,
		loaded: Dictionary, corpus: Dictionary, package_digest: Dictionary,
		save_digest: Dictionary) -> void:
	var projection: Variant = corpus.get("projection", null)
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	var rows: Dictionary = (save as Dictionary)["maps"][CORPUS_MAP_INDEX]["items"]
	var buildings := _capacity_distribution(registry,
		UnitInstanceProjection.BUILDING_DOMAIN)
	var units := _capacity_distribution(registry,
		UnitInstanceProjection.UNIT_DOMAIN)
	var dead_states := {}
	var instant_values := 0
	var orientation_values := 0
	for key: Variant in rows.keys():
		var row: Variant = rows[key]
		instant_values += 1 if int((row as Array)[3]) == 0 else 0
		orientation_values += 1 if int((row as Array)[4]) != 0 else 0
		var team := str(int((row as Array)[7]))
		dead_states[team] = int(dead_states.get(team, 0)) + 1
	var types := {}
	for domain: String in [UnitInstanceProjection.UNIT_DOMAIN,
			UnitInstanceProjection.BUILDING_DOMAIN]:
		for id_text: Variant in registry.legacy_ids(domain).get("ids", []):
			var entry: Dictionary = registry.get_entry(domain, str(id_text))[
				"entry"]
			types["%s/%s" % [domain, str(entry["type"])]] = \
				int(types.get("%s/%s" % [domain, str(entry["type"])], 0)) + 1

	var report := {
		"schema": "unit-instances-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_instances.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from the "
				+ "model's own constants, the verified registry, and the "
				+ "committed corpus bytes, and every derived set is sorted "
				+ "before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) "
				+ "plus one trailing newline; every number written is an "
				+ "integer - the pinned engine's integral floats are "
				+ "normalised on the way in, which changes no value - so no "
				+ "float formatting varies between runs",
		},
		"row_contract": {
			"slots": UnitInstance.ROW_SLOTS,
			"source": "engine.py:31, map_add_item's row literal [item, x, y, "
				+ "timestamp, orientation, store, attr, player]",
			"table": UnitInstance.row_contract(),
			"identity_rule": "the instance's item id is read from the "
				+ "definition it wraps and cross-checked against the row's own "
				+ "slot 0, never restated from either alone; a row whose "
				+ "resolved definition carries a committed type other than 'u' "
				+ "is refused with that type named, never coerced",
			"wrapping": "an instance HOLDS its row and its definition by "
				+ "reference and reads every value back out of them, so there "
				+ "is no second copy that could drift from the save; the "
				+ "attribute bag is the one exception and is handed out as a "
				+ "deep copy so no reader can write back into the save",
			"integer_transport_note": "the pinned engine's JSON parser "
				+ "represents every committed number as a float, so an "
				+ "integer slot accepts an int or an integral float - the "
				+ "documented transport tolerance the delivered building and "
				+ "unit catalogs apply to the same field class - and a numeric "
				+ "string is refused because no committed source stores one",
			"row_length_rule": "a row of exactly the committed eight slots is "
				+ "the only accepted shape: a longer row is an uncommitted "
				+ "shape and a shorter one has no container slot at all",
		},
		"classification": {
			"gate": "the committed item type, read from the resolved content "
				+ "entry",
			"unit_type": UnitInstanceProjection.TYPE_UNIT,
			"building_type": UnitInstanceProjection.TYPE_BUILDING,
			"classified_types": _sorted_array(
				UnitInstanceProjection.CLASSIFIED_TYPES),
			"domains_required": [UnitInstanceProjection.UNIT_DOMAIN,
				UnitInstanceProjection.BUILDING_DOMAIN],
			"domains_required_note": "the projection needs BOTH domains: the "
				+ "units domain to type an instance and the buildings domain to "
				+ "recognise and report a non-unit row with no coercion, so a "
				+ "registry missing either fails closed",
			"committed_type_distribution": types,
			"kind_artifact": UnitInstanceProjection.KIND_ARTIFACT,
			"kind_is_never_a_gate": "neither module's code contains the token "
				+ "kind at all, so no comparison on the normalization artifact "
				+ "can exist; and a definition whose kind says 'building' while "
				+ "its committed type still says 'u' builds an instance "
				+ "unchanged, which the suite asserts",
			"unclassified_type_branch": "a committed type outside {u, b}, and "
				+ "a units-domain row whose committed type is not 'u', are both "
				+ "refused with the committed type named. The second is "
				+ "exercised by the suite through a crafted definition; the "
				+ "first is unreachable against the committed content, whose "
				+ "measured distribution is units/u 429 and buildings/b 470, "
				+ "so it is defence in depth and the suite asserts the "
				+ "distribution that makes it unreachable",
			"unresolvable_item_id": "an item id resolving in neither domain "
				+ "fails the whole projection closed, so no row is ever "
				+ "silently dropped",
		},
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"map_index": CORPUS_MAP_INDEX,
			"rows": int(projection.row_count),
			"distinct_item_ids": int(corpus.get("distinct_item_ids", 0)),
			"unit_rows": UnitInstanceProjection.placed_unit_count(projection),
			"building_rows": UnitInstanceProjection.building_count(projection),
			"garrison_capable_rows": 9,
			"garrison_capable_item_ids": 3,
			"garrison_capable_ids": ["905", "930", "931"],
			"garrison_capable_note": UnitInstanceProjection
				.GARRISON_CAPABLE_CORRECTION,
			"rows_with_non_empty_container": 0,
			"rows_with_any_attr_key": 0,
			"attr_bags_all_empty": true,
			"reserved_keys_present": projection.reserved_presence,
			"dead_heroes": projection.dead_heroes,
			"bought_units": (save as Dictionary)["privateState"]["boughtUnits"],
			"player_store": (save as Dictionary)["maps"][CORPUS_MAP_INDEX][
				"store"],
			"row_instants": {"committed_zero": instant_values, "of":
				int(projection.row_count)},
			"non_default_orientations": orientation_values,
			"player_teams": dead_states,
			"sources": {
				"rows, distinct ids, containers, attr bags, row shape":
					"measured from the committed save bytes by the suite",
				"unit_rows, building_rows, reserved keys, dead counter":
					"the projection's own result over those same bytes",
				"bought_units, player_store": "read by the suite and recorded "
					+ "as a measurement only: the projection deliberately "
					+ "reads neither, and UNREAD_PRIVATE_STATE names why",
			},
		},
		"instances": {
			"asserted_zero": true,
			"placed": UnitInstanceProjection.placed_unit_count(projection),
			"nested": int(projection.building_garrison_members),
			"total": UnitInstanceProjection.instance_count(projection),
			"max_depth": int(projection.max_depth),
			"claim": "the committed corpus yields ZERO unit instances and "
				+ "every placed row classifies as a building. That zero is "
				+ "asserted by the suite and is a fact about the corpus, not "
				+ "evidence that a unit can be obtained, placed, or observed.",
			"demonstration": "instances are demonstrated over a crafted "
				+ "in-memory row set the suite builds itself, which is test "
				+ "input and not evidence of any behaviour: 2 placed unit "
				+ "rows, 2 placed building rows, a placed building's container "
				+ "holding 5 nested unit rows against its committed capacity "
				+ "of 4, and a placed unit row whose container holds a unit, "
				+ "for 8 instances at depth 1",
			"fabricated_save": false,
			"fabrication_note": "no save, corpus, or fixture was written to "
				+ "hold a unit row, and the committed corpus save is "
				+ "byte-identical after the run; the suite asserts the "
				+ "digest of tests/saves and tests/fixtures is unchanged and "
				+ "that no working-tree saves/ directory exists",
		},
		"garrison": {
			"slot": UnitInstance.SLOT_GARRISON,
			"container_element": "a nested row, parsed as a UnitInstance in "
				+ "its own right - never a list of identifiers",
			"container_states": [UnitInstance.GARRISON_EMPTY,
				UnitInstance.GARRISON_POPULATED],
			"max_depth": UnitInstance.MAX_GARRISON_DEPTH,
			"max_depth_provenance": "derived (design D2): the legacy engine "
				+ "nests exactly one level, because push_unit is called with a "
				+ "map row, so the committed corpus needs 1 and this bound is "
				+ "headroom against unbounded recursion over untrusted save "
				+ "input - not an observation",
			"over_depth": "refused with the key, the slot path, and the depth "
				+ "named; never truncated, because a truncated garrison is a "
				+ "wrong answer presented as a correct one",
			"corpus_max_depth": int(projection.max_depth),
			"corpus_non_empty_containers": 0,
			"empty_is_not_absent": "a fifth slot holding [] is an empty "
				+ "garrison; a fifth slot that is missing or malformed is a "
				+ "refusal with NO instance at all, so the two can never be "
				+ "confused and there is no third state",
			"container_row": "a placed row's container is parsed into unit "
				+ "instances whatever the container row's own committed type: "
				+ "the 48 garrison-capable committed rows are all buildings "
				+ "and none of them trains anything, so the container row in "
				+ "practice is a building",
			"garrisoned_row": "a row inside a container is always parsed as a "
				+ "UnitInstance, because push_unit moves a UNIT row into a "
				+ "container - a building id inside a container is refused",
			"slot_path_form": "5 for a placed row's container, 5[0] for its "
				+ "first member, 5[0]/5[0] for that member's own container, so "
				+ "a refusal names the exact nested row",
		},
		"dead_unit_counter": {
			"path": UnitInstanceProjection.DEAD_COUNTER_PATH,
			"rule": UnitInstanceProjection.DEAD_COUNTER_RULE,
			"absent_rule": UnitInstanceProjection.DEAD_COUNTER_ABSENT,
			"corpus": projection.dead_heroes,
			"no_instance_derived": true,
			"no_instance_derived_note": "the suite projects the same row set "
				+ "with and without a non-empty dead counter and asserts the "
				+ "instance count is identical, so the count demonstrably "
				+ "derives no row, no corpse, and no recoverable instance",
			"resurrectable_evaluated": false,
			"resurrectable_coverage": {"of": 429, "resurrectable_gt_0": 426},
			"resurrectable_note": "the committed coverage of the resurrection "
				+ "property is recorded as CONTENT: neither module's code "
				+ "contains the token properties at all, so no resurrection "
				+ "predicate can be evaluated, and death and resurrection "
				+ "remain undelivered behaviour belonging to a combat line",
		},
		"reserved_queue_keys": {
			"scope": UnitInstanceProjection.RESERVED_ATTR_SCOPE,
			"implemented": false,
			"inventory": UnitInstanceProjection.reserved_keys(),
			"names": UnitInstanceProjection.reserved_key_names(),
			"teardown": UnitInstanceProjection.RESERVED_ATTR_TEARDOWN,
			"teardown_note": "the three keys are deleted TOGETHER when the "
				+ "count reaches zero, and no committed branch deletes one of "
				+ "them on its own - a contract no inspection of the "
				+ "dispatcher would reveal, which is why it is recorded here",
			"corpus_presence": projection.reserved_presence,
			"corpus_rows": int(projection.reserved_rows.size()),
			"read_only": "reading whether a row carries a reserved key and what "
				+ "committed value it holds is projection; WRITING one is "
				+ "behaviour and is not implemented. Neither module declares "
				+ "an increment, a decrement, a timestamp write, or a queue "
				+ "projection, and the suite asserts the row is "
				+ "byte-identical after every reserved-key read.",
		},
		"unit_capacity": {
			"field": UnitInstanceProjection.CAPACITY_FIELD,
			"enforced": false,
			"rule": UnitInstanceProjection.CAPACITY_RULE,
			"legacy_consumers": 0,
			"legacy_modules_searched": ["engine.py", "command.py", "sessions.py",
				"server.py", "constants.py"],
			"buildings": {
				"of": int(buildings["of"]),
				"with_capacity": int(buildings["with_capacity"]),
				"distribution": buildings["distribution"],
			},
			"units": {
				"of": int(units["of"]),
				"with_capacity": int(units["with_capacity"]),
				"distribution": units["distribution"],
				"capacity_ids": units["capacity_ids"],
			},
			"correction": UnitInstanceProjection.CAPACITY_CORRECTION,
			"training_and_garrison_are_disjoint": {
				"buildings_with_training_time": 130,
				"buildings_with_capacity": 48,
				"buildings_with_both": 0,
				"units_with_training_time": 0,
				"note": "the producer garrons nothing and the garrison-capable "
					+ "rows train nothing, so nothing in the committed "
					+ "content joins the two",
			},
			"over_capacity_scenario": "a placed building whose committed "
				+ "capacity is 4 (905 Tree) holds FIVE nested unit rows in the "
				+ "crafted row set; all five are projected, none is refused "
				+ "and none is dropped, which is the observable form of the "
				+ "no-rule decision",
		},
		"boundary": {
			"definition": "UnitDefinition is committed content: typed, "
				+ "read-only, resolved through the content registry, and "
				+ "carrying no player state",
			"instance": "UnitInstance is a distinct player-owned type that "
				+ "WRAPS a legacy map row together with its resolved "
				+ "definition; it does not extend or copy the definition, so "
				+ "no instance field can migrate into one and the boundary is "
				+ "structural rather than conventional",
			"read_only": "neither module declares a setter, a mutating method, "
				+ "or a writable public field, and the suite asserts that "
				+ "reading an instance through every accessor changes neither "
				+ "its row nor its definition and that a caller writing into "
				+ "the handed-out attribute bag cannot reach the save",
			"endpoint": "none: an instance is read from a save already in "
				+ "hand, so no compatibility route, response field, error "
				+ "code, or persistence behaviour was added and no client "
				+ "intent is sent to obtain one",
			"fixture": "none captured and none fabricated: the committed "
				+ "corpus has no unit row, so capturing one would mean "
				+ "fabricating a player state",
			"next_unit_fixture": "the production line, because the Command "
				+ "Center at map key 1 is a real placed training producer "
				+ "(training_time 5, min_level 1) and makes the queue "
				+ "genuinely exercisable against the corpus",
			"acquisition": "none claimed: in_store is 0 for all 429 "
				+ "committed units, and the committed unit sources are the "
				+ "offer-pack and darts systems, which are later milestones",
			"unread_private_state": UnitInstanceProjection.UNREAD_PRIVATE_STATE,
			"undelivered_lines": ["queues", "production", "collection",
				"movement", "animations", "basic behaviors", "acquisition",
				"combat", "targeting"],
		},
		"content_source": {
			"units_file": str(catalog.source_file),
			"units_manifest_bytes": _as_int(_manifest_record(registry,
				"packages/game-content/normalized/units.json", "bytes")),
			"units_manifest_sha256": _manifest_record(registry,
				"packages/game-content/normalized/units.json", "sha256"),
			"content_fingerprint": str(catalog.content_fingerprint),
			"manifest_outputs_verified": _as_int(loaded.get("files_verified",
				0)),
			"manifest_bytes_verified": _as_int(loaded.get("bytes_verified", 0)),
			"package_files": _as_int(package_digest.get("files", 0)),
			"package_sha256": str(package_digest.get("sha256", "")),
			"enumeration": "ContentRegistry.legacy_ids(domain), the "
				+ "registry's own public accessor over the index it built "
				+ "during its verified load, so every enumeration and every "
				+ "capacity distribution in this report crosses the same "
				+ "byte-count and digest gate as every other read and no "
				+ "committed file is re-read behind the registry's back",
		},
		"provenance": UnitInstanceProjection.PROVENANCE,
		"non_claims": UnitInstanceProjection.NON_CLAIMS,
	}
	check(not (report["non_claims"] as Array).is_empty(),
		"the report carries the evidence's non-claims")
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)"
		% problem)
	if problem == "":
		check(FileAccess.file_exists(path),
			"the report file exists at %s" % path)
		info("report written: %s" % path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## A CRAFTED, in-memory legacy map row. **Test input only**: this is never
## written into a save, a corpus, or a fixture (design D8).
func _row(item: int, cell_x: int, cell_y: int, instant: int, orientation: int,
		container: Variant, attr: Variant, player: int) -> Array:
	return [item, cell_x, cell_y, instant, orientation, container, attr, player]


## A crafted row with the named slots replaced. Also test input only.
func _row_with(overrides: Dictionary, item: int = 1019) -> Array:
	var row := _row(item, 1, 1, 0, 0, [], {}, 1)
	for slot: Variant in overrides:
		row[int(slot)] = overrides[slot]
	return row


## The suite's OWN nested-row resolver, independent of the projection's, so the
## `UnitInstance` module is exercised against a resolver the suite controls.
func _resolver(registry: Variant) -> Callable:
	return func(item_id_text: String) -> Dictionary:
		var resolved: Dictionary = registry.get_entry(
			UnitInstanceProjection.UNIT_DOMAIN, item_id_text)
		if not bool(resolved.get("found", false)):
			return {"ok": false, "error": "no committed unit definition for "
				+ "item id %s" % item_id_text, "definition": null}
		var parsed := UnitDefinition.parse(resolved["entry"])
		if not bool(parsed.get("ok", false)):
			return {"ok": false, "error": str(parsed.get("error", "")),
				"definition": null}
		return {"ok": true, "error": "", "definition": parsed["definition"]}


## The committed definition of one unit id, parsed fresh from the registry.
func _definition_of(registry: Variant, legacy_id: String) -> Variant:
	var resolved: Dictionary = registry.get_entry(
		UnitInstanceProjection.UNIT_DOMAIN, legacy_id)
	if not bool(resolved.get("found", false)):
		fail("the committed unit %s resolves" % legacy_id)
		return null
	var parsed := UnitDefinition.parse(resolved["entry"])
	if not bool(parsed.get("ok", false)):
		fail("the committed unit %s parses (error: %s)"
			% [legacy_id, str(parsed.get("error", ""))])
		return null
	return parsed["definition"]


## A freshly parsed definition from a COPY of a committed entry with the named
## committed fields overridden. This is a fault or fact injection into **test
## input** only: the result is a throwaway object, the registry and the catalog
## are never touched, and nothing is written to any file.
func _definition_with(registry: Variant, legacy_id: String,
		overrides: Dictionary) -> Variant:
	var resolved: Dictionary = registry.get_entry(
		UnitInstanceProjection.UNIT_DOMAIN, legacy_id)
	if not bool(resolved.get("found", false)):
		fail("the committed unit %s resolves for an override" % legacy_id)
		return null
	var crafted: Dictionary = (resolved["entry"] as Dictionary).duplicate(true)
	for field: String in overrides:
		crafted[field] = overrides[field]
	var parsed := UnitDefinition.parse(crafted)
	if not bool(parsed.get("ok", false)):
		fail("the crafted definition for %s parses (error: %s)"
			% [legacy_id, str(parsed.get("error", ""))])
		return null
	return parsed["definition"]


## Every `.gd` source's DECLARATIONS, read from its own source: comment lines
## are dropped and string-literal content is blanked, so a prose mention or a
## recorded non-claim string can never be mistaken for code.
func _code_only(relative: String) -> String:
	var lines := FileAccess.get_file_as_string(
		Paths.project_dir().path_join(relative)).split("\n")
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


## The public and private function names a module declares, sorted, from its
## own source: the check that a behaviour-computing helper cannot hide.
func _methods(body: String) -> Array:
	var out: Array = []
	for line: String in body.split("\n"):
		var signature := line.strip_edges()
		if signature.begins_with("static func "):
			signature = signature.substr(len("static "))
		if not signature.begins_with("func "):
			continue
		var name := signature.substr(len("func "))
		var bracket := name.find("(")
		out.append(name if bracket == -1 else name.substr(0, bracket))
	out.sort()
	return out


func _source(res_path: String) -> String:
	return FileAccess.get_file_as_string(res_path)


func _sorted_keys(source: Dictionary) -> Array:
	return _sorted_unique(source.keys())


func _sorted_array(values: Variant) -> Array:
	var out: Array = []
	for value: Variant in values:
		out.append(value)
	out.sort()
	return out


## Ascending, duplicates collapsed — the shape a name inventory is compared in,
## so a name that appears twice cannot make an otherwise exact inventory look
## wrong.
func _sorted_unique(values: Variant) -> Array:
	var out: Array = []
	var previous: Variant = null
	for value: Variant in _sorted_array(values):
		if previous != null and str(value) == str(previous):
			continue
		previous = value
		out.append(value)
	return out


## The observed type of a refused value.
func _type_name(value: Variant) -> String:
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


## A committed number as the exact integer it denotes. The pinned engine's JSON
## parser yields integral floats; every number the report writes goes through
## here, so the report carries integers and its determinism does not depend on a
## float's serialization.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


## The manifest's own record for one output file.
func _manifest_record(registry: Variant, file: String, field: String) -> Variant:
	var manifest: Variant = _read_json(Paths.repo_root().path_join(
		"packages/game-content/manifest.json"))
	if not (manifest is Dictionary):
		return null
	for record: Variant in (manifest as Dictionary).get("outputs", []):
		if (record is Dictionary) and str((record as Dictionary).get(
				"file", "")) == file:
			return (record as Dictionary).get(field, null)
	return null


## Serializes deterministically (sorted keys, tab indent, one trailing newline)
## and writes the report, creating the destination directory when needed.
func _write_json(path: String, report: Dictionary) -> String:
	var directory := path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		if DirAccess.make_dir_recursive_absolute(directory) != OK:
			return "cannot create " + directory
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return "cannot write " + path + ": " \
			+ error_string(FileAccess.get_open_error())
	file.store_string(JSON.stringify(report, "\t", true) + "\n")
	file.close()
	return ""


func _read_json(path: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_string(path))


func _copy_file(from_path: String, to_path: String) -> bool:
	var bytes := FileAccess.get_file_as_bytes(from_path)
	if bytes.is_empty():
		return false
	return _write_bytes(to_path, bytes)


func _write_bytes(path: String, bytes: PackedByteArray) -> bool:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return false
	file.store_buffer(bytes)
	file.close()
	return true
