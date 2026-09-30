extends "res://tests/test_base.gd"
## Unit-definitions suite (OpenSpec `godot-unit-definitions` "Static unit
## definitions" / "Typed definition fields with no gameplay semantics" /
## "Fail-closed parsing" / "Static definitions are content, not a server
## operation" / "Committed asset linkage only" / "Unit-definition evidence and
## claim limits", design D1-D8).
##
## Scenarios:
##   fields     every parsed field of every group equals its committed value
##              verbatim, and both embedded-JSON bags are parsed;
##   malformed  one malformed value per parsed field class refuses the parse,
##              names the definition and the field, and produces no
##              definition — nothing is guessed, defaulted, or coerced;
##   absent     the two conditionally-present fields and the two nullable bags
##              are recorded ABSENT with an explicit flag, never as zero;
##   legacy_id  all 429 legacy IDs are distinct strings across the committed
##              range, each lookup returns its own definition, a wrong-form ID
##              fails closed without coercion, and the IDs are the committed
##              strings rather than numbers; the named lookup returns every
##              match for a name the committed set shares between two rows;
##   gate       an unavailable registry, an unloaded registry, and a registry
##              whose manifest declares no `units` output all fail closed —
##              never an empty catalog presented as a loaded one;
##   raw        the raw-entry escape hatch returns a committed field no typed
##              group parses, and the whole unparsed remainder is reachable;
##   boundary   no definition field can carry player state, reading a
##              definition through every accessor mutates nothing, and the
##              client carries no unit-instance, garrison, or production-queue
##              surface at all;
##   semantics  neither the model nor the catalog exposes a helper that
##              computes behaviour from a parsed statistic, and their own
##              documentation states the no-semantics rule;
##   linkage    a committed `img_name` reference resolves through the registry's
##              asset-ID registry with a recorded status, reported as linkage
##              only.
##
## Hermetic: no process, no server, no socket, and no request is issued — a
## definition is read from the already-loaded content registry, so no GameApi
## operation is involved at all. The fault scenarios mutate COPIES under
## `.godot/`, never a source file. Uses the `ContentRegistry` autoload (content
## + asset registry loaded explicitly). Runs headless as part of
## `verify-boot.ps1`.
##
## `--report=<path>` writes the deterministic `unit-definitions-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-definitions/report.json`. The tables are derived from the live
## model and registry, so they cannot drift from the code they document.

const UnitDefinition = preload("res://scripts/units/unit_definition.gd")
const UnitCatalog = preload("res://scripts/units/unit_catalog.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")

const SCRATCH := ".godot/verify/unit-definitions"
## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-definitions/report.json"
## The committed domain and its committed row count.
const DOMAIN := "units"
const EXPECTED_DEFINITIONS := 429
## The committed legacy-ID range, recorded as strings (design D5).
const EXPECTED_MIN_ID := "923"
const EXPECTED_MAX_ID := "1431"
## The one definition every check about a committed row uses: the first
## committed row of the committed file, read independently of the registry so
## the assertions are against the FILE, not against the registry's own copy.
const SAMPLE_ID := "923"

## Field names that could hold player state. A `UnitDefinition` carries none of
## them (design D2), which is what makes the static/instance boundary
## structural rather than a convention: a future instance cannot be smuggled in
## by widening a definition.
const PLAYER_STATE_NAMES := [
	"key", "index", "item_index", "x", "y", "cell", "pos", "position",
	"owner", "user_id", "player_id", "health", "current_health", "hp",
	"garrison", "queue", "queue_position", "state", "alive", "target",
	"level_state", "slot", "instance_id", "map_key",
]

## Tokens a static definition model must not carry: a node, a clock, a request,
## or a mutation of anything but its own freshly parsed row. The transport
## needles are spelled as fragments because the project-scope suite scans every
## source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]

## Every function the two modules expose, public and private. Compared as a
## sorted set: a helper that computed damage, defence, speed, lifetime, or
## attack timing from a parsed statistic would appear here and fail the check.
const EXPECTED_MODEL_METHODS := [
	"parse", "field_inventory", "parsed_fields", "presence_flags",
	"_text_field", "_count_field", "_signed_field", "_best_against_field",
	"_parse_costs", "_parse_properties", "_reject", "_invalid", "_text",
	"_count", "_integer", "_amount",
]
const EXPECTED_CATALOG_METHODS := [
	"build", "lookup", "find", "find_by_name", "has", "count", "legacy_ids",
	"raw_entry", "sprite_linkage", "_link_for", "_verified_index", "_reject",
	"_not_found", "_linkage_error",
]

## The non-claim every evidence consumer must be able to find.
const NO_RENDER_CLAIM := "no unit is rendered, animated, or played"


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
	var before := Paths.directory_digest(package_dir)
	check(bool(before.get("ok", false)),
		"content package digest is readable before the run (%s)"
		% str(before.get("error", "")))
	if not bool(before.get("ok", false)):
		return

	# The fail-closed gate, proved BEFORE any load: an unavailable registry, an
	# unloaded registry, and a registry whose manifest declares no `units`
	# output (a mutated COPY under `.godot/`, so manifest verification of every
	# other output still passes and the absent domain is what fails).
	_check_gate(registry)

	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"the committed package loads (error: %s)"
		% str(content.get("error", "")))
	if not bool(content.get("ok", false)):
		return
	if not bool(registry.assets_loaded()):
		var assets: Dictionary = registry.load_asset_registry()
		check(bool(assets.get("ok", false)),
			"the committed asset registry loads (error: %s)"
			% str(assets.get("error", "")))
	if not bool(registry.assets_loaded()):
		return

	var built: Dictionary = UnitCatalog.build(registry)
	check(bool(built.get("ok", false)),
		"the catalog builds from the verified units domain (error: %s)"
		% str(built.get("error", "")))
	if not bool(built.get("ok", false)):
		return
	var catalog: Variant = built["catalog"]

	var rows := _committed_rows()
	check(rows.size() == EXPECTED_DEFINITIONS,
		"the committed file holds %d unit rows (got %d)"
		% [EXPECTED_DEFINITIONS, rows.size()])
	check_eq(UnitCatalog.count(catalog), EXPECTED_DEFINITIONS,
		"the catalog carries every committed definition")

	_check_fields(catalog, rows, registry)
	_check_malformed(registry)
	_check_absent(catalog, rows)
	_check_legacy_id(catalog, rows)
	_check_raw(registry, catalog, rows)
	_check_boundary(catalog)
	_check_semantics()
	_check_linkage(catalog)

	var after := Paths.directory_digest(package_dir)
	check_eq(after.get("sha256", ""), before.get("sha256", ""),
		"content package bytes are unchanged after the run")
	check_eq(after.get("files", 0), before.get("files", 0),
		"content package file count is unchanged after the run")

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, catalog, content)
	info("unit definitions parsed: %d, content fingerprint %s"
		% [UnitCatalog.count(catalog), str(catalog.content_fingerprint)])


# ---------------------------------------------------------------------------
# Fail-closed resolution gate (design D1)
# ---------------------------------------------------------------------------


## Three fail-closed conditions, each producing NO catalog:
##   1. no registry at all;
##   2. a registry that has not loaded (the autoload starts unloaded, and the
##      registry's own contract is explicit loading);
##   3. a registry that HAS loaded but whose manifest declares no `units`
##      output — a mutated copy under `.godot/`, so every other output still
##      verifies its byte count and digest and the absent domain is the only
##      thing that can fail.
## None of them yields an empty catalog presented as a loaded one.
func _check_gate(registry: Variant) -> void:
	var missing := UnitCatalog.build(null)
	check_eq(bool(missing.get("ok", true)), false,
		"an unavailable registry fails closed")
	check(not missing.has("catalog") or missing["catalog"] == null,
		"an unavailable registry yields no catalog at all")
	check(str(missing.get("error", "")).contains("unavailable"),
		"the unavailable-registry error says why (got: %s)"
		% str(missing.get("error", "")))

	check(not registry.is_loaded(),
		"the registry starts unloaded, so the unloaded gate is reachable")
	var unloaded := UnitCatalog.build(registry)
	check_eq(bool(unloaded.get("ok", true)), false,
		"an unloaded registry fails closed")
	check(unloaded["catalog"] == null,
		"an unloaded registry yields no catalog at all")
	check(str(unloaded.get("error", "")).contains("has not loaded"),
		"the unloaded-registry error says why (got: %s)"
		% str(unloaded.get("error", "")))

	var copy_repo := _build_copy()
	if copy_repo == "":
		fail("the mutated package copy under " + SCRATCH + " is buildable")
		return
	var stripped: RegistryScript = RegistryScript.new()
	var loaded: Dictionary = stripped.load_content(copy_repo)
	check(bool(loaded.get("ok", false)),
		"the copy without the units output still loads every other output "
		+ "(error: %s)" % str(loaded.get("error", "")))
	check(bool(stripped.is_loaded()), "the stripped copy reports loaded")
	check(not stripped.has_domain(DOMAIN),
		"the stripped copy carries no '%s' domain" % DOMAIN)
	var absent := UnitCatalog.build(stripped)
	check_eq(bool(absent.get("ok", true)), false,
		"a registry without a '%s' domain fails closed" % DOMAIN)
	check(absent["catalog"] == null,
		"an absent '%s' domain yields no catalog at all" % DOMAIN)
	check(str(absent.get("error", "")).contains("carries no"),
		"the absent-domain error says why (got: %s)"
		% str(absent.get("error", "")))
	stripped.free()


## Copies `manifest.json` and `normalized/` into `.godot/verify/…` and drops
## the `units` output record from the copy's manifest root outputs. Returns the
## scratch repository root (the substitute root that contains
## `packages/game-content/`), or "" on failure. The sources are never touched.
func _build_copy() -> String:
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
	if not _drop_units_output(copy_root):
		return ""
	return copy_root


## Removes the `units` output record from the copy's manifest, so the copy's
## inventory is verified without it. The digest of every remaining output is
## untouched, so the copy still passes manifest verification.
func _drop_units_output(copy_root: String) -> bool:
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
				"file", "")).ends_with("/units.json"):
			continue
		kept.append(record)
	(manifest as Dictionary)["outputs"] = kept
	return _write_bytes(manifest_path,
		JSON.stringify(manifest).to_utf8_buffer())


# ---------------------------------------------------------------------------
# Parsed fields, verbatim (design D3)
# ---------------------------------------------------------------------------


## Every parsed field of every group equals the committed row's value exactly,
## with no scaling, rounding, or defaulting — asserted for all 429 definitions,
## not a sample, because 429 rows is cheap and a per-row divergence would
## otherwise hide behind a representative one. Both embedded-JSON bags are
## included: the cost bag parsed onto the delivered endpoints' resource names,
## and the property bag verbatim.
func _check_fields(catalog: Variant, rows: Array,
		registry: Variant) -> void:
	var inventory := UnitDefinition.field_inventory()
	check_eq(inventory.size(), 5,
		"the model declares the design's five named field groups")
	check_eq(_sorted_keys(inventory), _sorted_array(UnitDefinition
		.GROUP_ORDER), "the groups are exactly D3's five, in canonical order")
	var parsed_count := 0
	for group: String in inventory:
		parsed_count += (inventory[group] as Array).size()
	check_eq(UnitDefinition.parsed_fields().size(), parsed_count + 3,
		"the model's committed surface is the five groups plus the property bag "
			+ "and the two nullable bags")
	check_eq(_sorted_unique(UnitDefinition.parsed_fields()).size(),
		UnitDefinition.parsed_fields().size(),
		"no committed field name is claimed by two groups, so the inventory "
			+ "cannot double-count one")

	var mismatches: Array = []
	var group_totals := {}
	for group: String in inventory:
		group_totals[group] = (inventory[group] as Array).size()
	var cost_keys := {}
	var property_keys := {}
	var signed_seen := 0
	var best_against_kinds := {}
	var kinds := {}
	var types := {}
	var races := {}
	var upgrades := {}
	for row: Dictionary in rows:
		var id_text := str(row["legacy_id"])
		var found: Dictionary = UnitCatalog.lookup(catalog, id_text)
		if not bool(found.get("found", false)):
			mismatches.append("%s: not found" % id_text)
			continue
		var definition = found["definition"]
		kinds[str(definition.kind)] = int(kinds.get(str(definition.kind), 0)) + 1
		types[str(definition.type)] = int(types.get(str(definition.type), 0)) + 1
		races[str(definition.race)] = int(races.get(str(definition.race), 0)) + 1
		upgrades[str(int(definition.upgrades_to))] = \
			int(upgrades.get(str(int(definition.upgrades_to)), 0)) + 1
		if int(definition.upgrades_to) < 0:
			signed_seen += 1
		var flag_kind := "int"
		if typeof(definition.best_against) == TYPE_STRING:
			flag_kind = "string"
		best_against_kinds[flag_kind] = 1
		for group: String in inventory:
			for field: String in inventory[group]:
				if not _verbatim(definition, field, row):
					mismatches.append("%s.%s" % [id_text, field])
		# The committed cost bag parsed onto the delivered resource names.
		var expected_costs := {}
		for key: Variant in row["costs"]:
			expected_costs[UnitDefinition.COST_RESOURCES[str(key)]] = \
				int((row["costs"] as Dictionary)[key])
		if JSON.stringify(definition.costs) != JSON.stringify(expected_costs):
			mismatches.append("%s.costs" % id_text)
		for key: Variant in definition.costs:
			cost_keys[str(key)] = int(cost_keys.get(str(key), 0)) + 1
		# The committed property bag verbatim, flag values untouched.
		if JSON.stringify(definition.properties) \
				!= JSON.stringify(row["properties"]):
			mismatches.append("%s.properties" % id_text)
		for key: Variant in definition.properties:
			property_keys[str(key)] = true
		# The cost vocabulary is the delivered endpoints' mapping, by identity.
		if UnitDefinition.COST_RESOURCES != PlacementCatalog.COST_RESOURCES:
			mismatches.append("%s.cost-vocabulary" % id_text)
	check_eq(mismatches, [],
		"every parsed field of all %d definitions equals its committed value "
			% EXPECTED_DEFINITIONS + "verbatim, with no scaling, rounding, "
			+ "defaulting, or coercion")
	check_eq(_sorted_keys(cost_keys), ["cash", "gold", "oil", "steel", "wood"],
		"the committed cost bags name exactly the five resources the delivered "
			+ "endpoints' vocabulary maps onto, never an invented one")
	check_eq(_sorted_keys(kinds), ["unit"],
		"every committed row is classified kind 'unit'")
	check_eq(_sorted_keys(types), ["u"],
		"every committed row carries the stored type 'u'")
	check(races.size() >= 1 and int(races.get("a", 0)) > 0,
		"the committed race field is parsed verbatim (%s)" % JSON.stringify(races))
	check(signed_seen == EXPECTED_DEFINITIONS,
		"the signed upgrade-chain field accepts the committed -1 on every "
			+ "definition (a non-negative parser would refuse them all)")
	check_eq(_sorted_keys(upgrades), ["-1"],
		"the committed upgrade-chain reference is -1 on every definition, "
			+ "reproduced verbatim and never resolved or interpreted")
	check(_manifest_numbers_are_integral(),
		"the pinned engine's JSON parser represents the committed integers as "
			+ "integral floats, so the model's integers are the documented "
			+ "transport tolerance and not a change of value")
	check(property_keys.size() >= 1,
		"the committed property bag carries its committed flag keys verbatim "
			+ "(%d distinct)" % property_keys.size())
	check_eq(_sorted_keys(best_against_kinds), ["string"],
		"the committed combat flag is a string on every definition, preserved "
			+ "verbatim (the schema also permits an integer code)")
	check_eq(UnitDefinition.COST_RESOURCES,
		PlacementCatalog.COST_RESOURCES,
		"the cost vocabulary IS the delivered endpoints' table, aliased and "
			+ "not restated")


## One parsed field equals the committed row's value.
##
## The pinned engine's JSON parser represents every committed number as a
## **float**, so a committed `10` arrives as `10.0` and the model stores the
## exact integer 10 — the documented transport tolerance the delivered building
## catalog applies to the same field class. The comparison is therefore by
## VALUE, and a non-integral or out-of-range number can never match. The
## `has_*` flags are the model's own presence record and are asserted by the
## absent-field scenario, so they are not compared here.
func _verbatim(definition: Variant, field: String, row: Dictionary) -> bool:
	if UnitDefinition.presence_flags().has(field):
		return true
	# `costs` is compared against the committed bag translated through the
	# delivered cost vocabulary, immediately below, not key for key.
	if field == "costs":
		return true
	if not row.has(field):
		# A conditionally-present field the row omits is compared through its
		# flag, which the absent-field scenario asserts.
		return UnitDefinition.CONDITIONALLY_PRESENT_FIELDS.has(field) \
			and not bool(definition.get("has_" + field))
	var committed: Variant = row[field]
	var parsed: Variant = definition.get(field)
	if (committed is String) or (parsed is String) \
			or (committed is Dictionary) or (parsed is Dictionary):
		return JSON.stringify(parsed) == JSON.stringify(committed)
	if _is_number(committed) and _is_number(parsed):
		var number := float(parsed)
		return number == floor(number) and number == float(committed)
	return false


## True for an `int` or a `float` — the two shapes a committed number arrives
## in through the pinned engine's JSON parser.
func _is_number(value: Variant) -> bool:
	return value is int or value is float


## True when every committed row reaches the client as an integral `float` —
## the pinned engine's JSON number representation, recorded here so the
## evidence states the transport fact it rests on instead of assuming it.
func _manifest_numbers_are_integral() -> bool:
	var parsed: Variant = _read_json(Paths.repo_root().path_join(
		"packages/game-content/normalized/units.json"))
	if not (parsed is Array):
		return false
	for row: Variant in parsed:
		if not (row is Dictionary):
			return false
		var number: Variant = (row as Dictionary).get("attack", null)
		if not (number is float) or float(number) != floor(float(number)):
			return false
	return true


# ---------------------------------------------------------------------------
# Fail-closed parsing (design D4)
# ---------------------------------------------------------------------------


## One malformed value per parsed field class refuses the parse, and the
## refusal names BOTH the offending definition and the field while producing no
## definition. A crafted copy of the committed row is fed to the parser
## directly, so this never touches the registry, the content package, or any
## save.
##
## Classes covered: a required non-empty string, an integer field, the signed
## integer field, the verbatim combat flag, the embedded-JSON cost bag (as an
## object, as a malformed JSON string, with an unknown key, and with a
## non-integer amount), the embedded-JSON property bag, a conditionally-present
## field, a nullable bag, and the non-object entry itself.
func _check_malformed(registry: Variant) -> void:
	var entry: Dictionary = registry.get_entry(DOMAIN, SAMPLE_ID)["entry"]
	var template: Dictionary = (entry as Dictionary).duplicate(true)
	var cases := [
		["name", 12345, "name"],
		["name", "", "name"],
		["img_name", 42, "img_name"],
		["race", null, "race"],
		["display_order", "99", "display_order"],
		["display_order", 99.5, "display_order"],
		["width", -1, "width"],
		["volume", true, "volume"],
		["attack", "10", "attack"],
		["attack_range", 1.25, "attack_range"],
		["expiration", -3, "expiration"],
		["upgrades_to", "-1", "upgrades_to"],
		["best_against", {"flag": "ft_ground"}, "best_against"],
		["costs", "not json", "costs"],
		["costs", {"zz": 1}, "costs"],
		["costs", {"g": "10"}, "costs"],
		["costs", {"g": 1.5}, "costs"],
		["costs", [1, 2], "costs"],
		["properties", "ft_ground", "properties"],
		["properties", {"ft_ground": 1}, "properties"],
		["properties", {"": "1"}, "properties"],
		["collect_type", 7, "collect_type"],
		["unit_capacity", {}, "unit_capacity"],
		["inventory_ids", 5, "inventory_ids"],
		["premium_upgrade_costs", "g", "premium_upgrade_costs"],
		["sm_training_time", "4000", "sm_training_time"],
		["breeding_order", [2], "breeding_order"],
		["legacy_id", 923, "legacy_id"],
		["legacy_id", "", "legacy_id"],
	]
	var wrong: Array = []
	var unnamed: Array = []
	var produced: Array = []
	for item: Variant in cases:
		var field := str(item[0])
		var value: Variant = item[1]
		var crafted: Dictionary = template.duplicate(true)
		crafted[field] = value
		var parsed := UnitDefinition.parse(crafted)
		if bool(parsed.get("ok", true)):
			wrong.append("%s=%s" % [field, JSON.stringify(value)])
			continue
		var message := str(parsed.get("error", ""))
		if not message.contains("'%s'" % field):
			unnamed.append("%s=%s -> %s" % [field,
				JSON.stringify(value), message])
		# A malformed `legacy_id` is the one field a refusal cannot name the
		# definition by: the id is what is broken. It must then say so instead
		# of fabricating one.
		if field == "legacy_id":
			if message.contains("unit "):
				unnamed.append("a malformed legacy_id named a definition: %s"
					% message)
			continue
		if not message.contains("unit %s" % SAMPLE_ID):
			unnamed.append("%s does not name the definition: %s"
				% [field, message])
		if not (parsed["definition"] == null):
			produced.append(field)
	# The entry itself must not be an object.
	var not_object := UnitDefinition.parse(["unit"])
	check_eq(bool(not_object.get("ok", true)), false,
		"an entry that is not an object fails closed")
	check(not_object["definition"] == null,
		"a non-object entry produces no definition")
	check(not str(not_object.get("error", "")).contains("unit %s" % SAMPLE_ID),
		"a non-object entry cannot name a definition and says so instead")
	check_eq(wrong, [],
		"every malformed value in every parsed field class is refused")
	check_eq(unnamed, [],
		"every refusal names BOTH the offending definition and the field")
	check_eq(produced, [],
		"no refusal leaves a partial definition behind")

	# A field the schema never permits is refused as an absent required field,
	# never defaulted: dropping `attack` is a malformed definition.
	for dropped: String in ["attack", "name", "img_name", "costs",
			"properties", "collect_type"]:
		var crafted: Dictionary = template.duplicate(true)
		crafted.erase(dropped)
		var parsed := UnitDefinition.parse(crafted)
		check_eq(bool(parsed.get("ok", true)), false,
			"a definition missing its required '%s' field fails closed" % dropped)
		check(str(parsed.get("error", "")).contains("'%s'" % dropped),
			"the missing-field refusal names '%s' (got: %s)"
			% [dropped, str(parsed.get("error", ""))])


# ---------------------------------------------------------------------------
# Absent is never zero (design D4)
# ---------------------------------------------------------------------------


## The four presence-flagged fields, over every committed definition: the two
## conditionally-present integers are present on 300 rows and absent on 129,
## and the two nullable bags are committed as `null` on all 429. Each absence
## is recorded with `has_* == false` and a value that is **not** a substituted
## zero, and each presence with `has_* == true` and the committed number.
func _check_absent(catalog: Variant, rows: Array) -> void:
	var committed_present := {"breeding_order": 0, "sm_training_time": 0}
	for row: Dictionary in rows:
		for field: String in UnitDefinition.CONDITIONALLY_PRESENT_FIELDS:
			if row.has(field):
				committed_present[field] = \
					int(committed_present.get(field, 0)) + 1
	check_eq(committed_present.get("breeding_order", 0), 300,
		"the committed rows carry breeding_order on exactly 300 of %d"
			% EXPECTED_DEFINITIONS)
	check_eq(committed_present.get("sm_training_time", 0), 300,
		"the committed rows carry sm_training_time on exactly 300 of %d"
			% EXPECTED_DEFINITIONS)

	var wrong_flag: Array = []
	var zero_substituted: Array = []
	var wrong_value: Array = []
	var nullable_present := {"inventory_ids": 0, "premium_upgrade_costs": 0}
	var absent_ones := {}
	for row: Dictionary in rows:
		var id_text := str(row["legacy_id"])
		var definition = UnitCatalog.find(catalog, id_text)
		if definition == null:
			wrong_flag.append("%s: absent" % id_text)
			continue
		for field: String in UnitDefinition.CONDITIONALLY_PRESENT_FIELDS:
			var flag := bool(definition.get("has_" + field))
			var committed: Variant = row.get(field, null)
			var value: Variant = definition.get(field)
			if flag != _is_number(committed):
				wrong_flag.append("%s.%s" % [id_text, field])
				continue
			if flag and int(value) != int(committed):
				wrong_value.append("%s.%s" % [id_text, field])
			if not flag and int(value) != 0:
				# The declared default is zero, and a reader could mistake it
				# for a committed zero; the flag is what distinguishes them.
				zero_substituted.append("%s.%s=%s" % [id_text, field,
					str(value)])
			if not flag:
				absent_ones[field] = int(absent_ones.get(field, 0)) + 1
		for field: String in UnitDefinition.NULLABLE_BAG_FIELDS:
			var flag := bool(definition.get("has_" + field))
			var committed: Variant = row.get(field, null)
			if flag != (committed is Dictionary):
				wrong_flag.append("%s.%s" % [id_text, field])
				continue
			if flag:
				nullable_present[field] = \
					int(nullable_present.get(field, 0)) + 1
			elif definition.get(field) != null:
				wrong_flag.append("%s.%s is not null" % [id_text, field])
	check_eq(wrong_flag, [],
		"every presence flag matches the committed row on all %d definitions"
			% EXPECTED_DEFINITIONS)
	check_eq(wrong_value, [],
		"every present value equals the committed number verbatim")
	check_eq(zero_substituted, [],
		"no absent field carries a value other than its declared zero default")
	check_eq(_sorted_keys(absent_ones),
		["breeding_order", "sm_training_time"],
		"both conditionally-present fields are recorded absent on 129 rows")
	check_eq(absent_ones.get("breeding_order", 0), 129,
		"breeding_order is recorded absent on exactly 129 of %d"
			% EXPECTED_DEFINITIONS)
	check_eq(absent_ones.get("sm_training_time", 0), 129,
		"sm_training_time is recorded absent on exactly 129 of %d"
			% EXPECTED_DEFINITIONS)
	for field: String in UnitDefinition.NULLABLE_BAG_FIELDS:
		check_eq(nullable_present.get(field, -1), 0,
			"the nullable bag '%s' is committed as an object on no row, so it "
				% field + "is recorded absent on all %d" % EXPECTED_DEFINITIONS)
	check_eq(UnitDefinition.presence_flags().size(), 4,
		"the four presence-flagged fields carry exactly four has_* flags")
	# The distinction a reader depends on: an absent field and a committed zero
	# are told apart by the flag, never by the value.
	var with_zero: Array = []
	for row: Dictionary in rows:
		for field: String in UnitDefinition.CONDITIONALLY_PRESENT_FIELDS:
			if row.has(field) and int(row[field]) == 0:
				with_zero.append(str(row["legacy_id"]) + "." + field)
	check(with_zero.is_empty(),
		"no committed row records a committed zero for a conditionally-present "
			+ "field, so the flag is the only distinguisher this corpus needs "
			+ "(found %d)" % with_zero.size())
	check(committed_present.size() == 2,
		"both conditionally-present fields are accounted for")


# ---------------------------------------------------------------------------
# Legacy IDs (design D5)
# ---------------------------------------------------------------------------


## All 429 legacy IDs are distinct strings spanning the committed range; each
## lookup returns its own definition and not another; a wrong-form ID fails
## closed with no coercion.
func _check_legacy_id(catalog: Variant, rows: Array) -> void:
	var ids := UnitCatalog.legacy_ids(catalog)
	check_eq(ids.size(), EXPECTED_DEFINITIONS,
		"the catalog enumerates every committed legacy id")
	var non_strings := 0
	var distinct := {}
	var mismatched: Array = []
	var mixed_up: Array = []
	for id_text: Variant in ids:
		if not (id_text is String):
			non_strings += 1
			continue
		if distinct.has(str(id_text)):
			mixed_up.append(str(id_text))
		distinct[str(id_text)] = true
		var found: Dictionary = UnitCatalog.lookup(catalog, id_text)
		if not bool(found.get("found", false)) \
				or str((found["definition"]).legacy_id) != str(id_text):
			mismatched.append(str(id_text))
	check_eq(non_strings, 0, "every legacy id is a String, preserved verbatim")
	check_eq(mixed_up, [], "every committed legacy id is distinct")
	check_eq(mismatched, [],
		"every lookup by a committed legacy id returns its OWN definition")
	check_eq(ids[0], EXPECTED_MIN_ID,
		"the committed row order starts at the committed file's first row, %s"
			% EXPECTED_MIN_ID)
	check_eq(ids[ids.size() - 1], EXPECTED_MAX_ID,
		"the committed row order ends at the committed file's last row, %s"
			% EXPECTED_MAX_ID)
	var bounds := _id_bounds(ids)
	check_eq(bounds[0], EXPECTED_MIN_ID,
		"the committed legacy-id range starts at %s" % EXPECTED_MIN_ID)
	check_eq(bounds[1], EXPECTED_MAX_ID,
		"the committed legacy-id range ends at %s" % EXPECTED_MAX_ID)
	check(not _ids_ascend(ids),
		"the committed row order is not a numeric sort, so the range is "
			+ "computed over the values and not read off the order")
	check_eq(distinct.size(), EXPECTED_DEFINITIONS,
		"the registry's duplicate rejection plus the catalog's own index hold "
			+ "%d distinct string legacy ids" % EXPECTED_DEFINITIONS)

	# Every committed row is found by ITS OWN id, and the definition it yields
	# is that row — checked through the model and not through the index alone.
	var wrong_row: Array = []
	for row: Dictionary in rows:
		var id_text := str(row["legacy_id"])
		var definition = UnitCatalog.find(catalog, id_text)
		if definition == null or str(definition.name) != str(row["name"]) \
				or str(definition.img_name) != str(row["img_name"]) \
				or int(definition.attack) != int(row["attack"]):
			wrong_row.append(id_text)
	check_eq(wrong_row, [],
		"every one of the %d committed rows is reachable by its own legacy id "
			% EXPECTED_DEFINITIONS + "and yields that row")

	# The wrong form fails closed: an integer never becomes the string.
	for wrong_form: Variant in [923, 923.0, true, ["923"], {"id": "923"},
			null, " 923", "0923", "922", "1432", "", "Gorilla"]:
		var result: Dictionary = UnitCatalog.lookup(catalog, wrong_form)
		check_eq(bool(result.get("found", true)), false,
			"a legacy id in the wrong form %s fails closed"
				% JSON.stringify(wrong_form))
		check(result["definition"] == null,
			"the wrong-form lookup for %s produces no definition"
				% JSON.stringify(wrong_form))
		check(str(result.get("error", "")) != "",
			"the wrong-form lookup for %s says why"
				% JSON.stringify(wrong_form))
	check_eq(UnitCatalog.has(catalog, 923), false,
		"has() refuses the integer form rather than coercing it")
	check_eq(UnitCatalog.find(catalog, 923), null,
		"find() returns null for the integer form")
	check(UnitCatalog.find(catalog, SAMPLE_ID) != null,
		"the committed string form resolves")

	# The named lookup, where the committed names are NOT unique: six of them
	# are shared by two rows each, so the accessor returns every match and
	# never picks one.
	var by_name := {}
	for row: Dictionary in rows:
		var unit_name := str(row["name"])
		by_name[unit_name] = int(by_name.get(unit_name, 0)) + 1
	var duplicated := []
	for unit_name: String in by_name:
		if int(by_name[unit_name]) > 1:
			duplicated.append(unit_name)
	duplicated.sort()
	check_eq(duplicated.size(), 6,
		"the committed names are not unique: six are shared by two rows each")
	var shared: Dictionary = UnitCatalog.find_by_name(catalog,
		str(duplicated[0]))
	check_eq(int(shared.get("count", 0)), 2,
		"a duplicated committed name returns BOTH definitions (name: %s)"
			% str(duplicated[0]))
	check_eq(bool(shared.get("found", false)), true,
		"the duplicated-name lookup reports what it found rather than "
			+ "silently picking one")
	var unique_names := []
	for unit_name: String in by_name:
		if int(by_name[unit_name]) == 1:
			unique_names.append(unit_name)
			break
	var lone: Dictionary = UnitCatalog.find_by_name(catalog,
		str(unique_names[0]))
	check_eq(int(lone.get("count", 0)), 1,
		"a unique committed name resolves to exactly one definition")
	check_eq(str(lone.get("error", "sentinel")), "",
		"a found name carries no error")
	var absent_name: Dictionary = UnitCatalog.find_by_name(catalog,
		"No Such Committed Unit")
	check_eq(bool(absent_name.get("found", true)), false,
		"an unknown name reports not-found")
	check(str(absent_name.get("error", "")).contains("no unit definition"),
		"the unknown-name error says why")
	for bad_name: Variant in [923, "", null, ["Gorilla"]]:
		var refused: Dictionary = UnitCatalog.find_by_name(catalog, bad_name)
		check_eq(int(refused.get("count", -1)), 0,
			"a name in the wrong form %s fails closed"
				% JSON.stringify(bad_name))


# ---------------------------------------------------------------------------
# The raw-entry escape hatch (design D3)
# ---------------------------------------------------------------------------


## Every committed field no typed group parses stays reachable through the one
## documented accessor, so nothing is silently dropped and a new content field
## needs no model change. The whole unparsed remainder is enumerated from the
## committed rows themselves rather than restated, and one of its fields is
## read back by name to prove the accessor works.
func _check_raw(registry: Variant, catalog: Variant, rows: Array) -> void:
	var parsed := UnitDefinition.parsed_fields()
	var committed_fields := {}
	for row: Dictionary in rows:
		for field: Variant in row:
			committed_fields[str(field)] = true
	var unparsed: Array = []
	for field: String in committed_fields:
		if not parsed.has(field):
			unparsed.append(field)
	unparsed.sort()
	check_eq(unparsed, ["building_limit_same_id", "building_limit_same_scf",
			"category_id", "content_version", "gift_level", "giftable",
			"group_type", "in_store", "max_collects", "new_item",
			"source_file", "source_layer", "subcat_functional",
			"subcategory_id", "trains_ids"],
		"the committed fields outside the typed model are exactly these "
			+ "fifteen, and every one stays reachable")
	check_eq(committed_fields.size(), 58,
		"the committed rows carry 58 fields between them (56 on every row "
			+ "plus the two patch-added fields on 300)")
	for field: String in unparsed:
		var entry: Dictionary = UnitCatalog.raw_entry(registry, catalog,
			SAMPLE_ID)
		check(bool(entry.get("found", false)),
			"the raw entry resolves for %s (error: %s)"
				% [SAMPLE_ID, str(entry.get("error", ""))])
		if not bool(entry.get("found", false)):
			break
		check(entry["entry"].has(field),
			"the committed row exposes its unparsed field '%s'" % field)
	check_eq(UnitCatalog.raw_entry(registry, catalog, SAMPLE_ID)["entry"]
		.get("in_store", null), 0,
		"a field no typed group parses reads back from the committed row "
			+ "verbatim")
	check_eq(UnitCatalog.raw_entry(registry, catalog, SAMPLE_ID)["entry"]
		.get("source_file", ""), "config/main.json",
		"a second unparsed field reads back from the committed row verbatim")
	check(str(UnitCatalog.raw_entry(registry, catalog, "no_such_id")
		.get("error", "")).contains("no unit definition"),
		"the raw accessor fails closed for an unknown legacy id")
	var no_registry := UnitCatalog.raw_entry(null, catalog, SAMPLE_ID)
	check_eq(bool(no_registry.get("found", true)), false,
		"the raw accessor fails closed without a loaded registry")
	check((no_registry.get("entry", {}) as Dictionary).is_empty(),
		"the raw accessor's failure carries no entry")


# ---------------------------------------------------------------------------
# The static/instance boundary (design D2, D6)
# ---------------------------------------------------------------------------


## A definition carries no field that could hold player state, reading it
## through every accessor mutates nothing, and the client itself carries no
## unit-instance, garrison, or production-queue surface: the boundary is
## structural, so the later `unit instances` line inherits a named edge instead
## of finding one.
func _check_boundary(catalog: Variant) -> void:
	var stateful: Array = []
	var inventory: Array = []
	for id_text: Variant in UnitCatalog.legacy_ids(catalog):
		var definition = UnitCatalog.find(catalog, id_text)
		for property: Dictionary in definition.get_property_list():
			if (int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE) == 0:
				continue
			var field := str(property["name"])
			inventory.append(field)
			if PLAYER_STATE_NAMES.has(field):
				stateful.append(str(id_text) + "." + field)
	check_eq(stateful, [],
		"no definition field could carry a placement key, coordinates, an "
			+ "owner, current health, a garrison, or a queue position")
	inventory.sort()
	var distinct_inventory := []
	var previous := ""
	for field: String in inventory:
		if field == previous:
			continue
		previous = field
		distinct_inventory.append(field)
	var expected_fields := _sorted_unique(
		UnitDefinition.parsed_fields()
			+ UnitDefinition.presence_flags())
	check_eq(distinct_inventory, expected_fields,
		"a definition's whole field inventory is exactly the committed parsed "
			+ "fields and their presence flags — nothing else, so no field "
			+ "could be widened into an instance")
	check_eq(inventory.size(), distinct_inventory.size()
			* UnitCatalog.count(catalog),
		"every one of the %d definitions declares each of its %d fields exactly "
			% [UnitCatalog.count(catalog), distinct_inventory.size()]
			+ "once, with no alias and no extra field")

	# Immutability, observed rather than asserted: every accessor is exercised
	# over a real definition and the definition is then compared field by field.
	var definition = UnitCatalog.find(catalog, SAMPLE_ID)
	var before := _snapshot(definition)
	UnitCatalog.lookup(catalog, SAMPLE_ID)
	UnitCatalog.find(catalog, SAMPLE_ID)
	UnitCatalog.has(catalog, SAMPLE_ID)
	UnitCatalog.count(catalog)
	UnitCatalog.legacy_ids(catalog)
	UnitCatalog.find_by_name(catalog, str(definition.name))
	UnitDefinition.parse(_committed_rows()[0])
	check_eq(_snapshot(definition), before,
		"reading a definition through every accessor mutates nothing in it")
	var ids_before := UnitCatalog.legacy_ids(catalog)
	UnitCatalog.legacy_ids(catalog).append("tampered")
	check_eq(UnitCatalog.legacy_ids(catalog), ids_before,
		"the id list is a fresh copy, so a caller cannot mutate the catalog "
			+ "through it")
	var inventory_copy := UnitDefinition.field_inventory()
	(inventory_copy[UnitDefinition.GROUP_IDENTITY] as Array).append("tampered")
	check_eq((UnitDefinition.field_inventory()[
		UnitDefinition.GROUP_IDENTITY] as Array).size(), 7,
		"the field inventory is a fresh copy, never the constant itself")

	# The static/instance BOUNDARY, not a repository-wide absence. An earlier
	# version of this block asserted that NO client source anywhere declared a
	# unit instance or a garrison, which was a stronger claim than the
	# requirement makes and which the very next deliver line
	# (`godot-unit-instances`) is chartered to falsify — the assertion had to be
	# weakened or the delivered suite would have rotted the moment the boundary
	# it drew was crossed. What is permanent is narrower and stronger: the two
	# modules THIS capability delivers declare no instance or queue state, and
	# where an instance type does exist it is a DISTINCT type that holds this
	# definition rather than extending it. Both this suite's own token lists and
	# the recorded non-claims in `unit_catalog.gd` necessarily name what they
	# forbid, so the scan drops comment lines AND string-literal content before
	# searching — what remains is the code a reader would compile.
	for relative: String in ["scripts/units/unit_definition.gd",
			"scripts/units/unit_catalog.gd"]:
		var code := _code_only(relative)
		check_eq(code.find("UnitInstance"), -1,
			"%s declares no unit-instance type: the instance is a distinct "
				% relative + "type owned by a later capability")
		check_eq(code.find("garrison"), -1,
			"%s declares no garrison state" % relative)
		check_eq(code.find("production_queue"), -1,
			"%s declares no production-queue state" % relative)
		check_eq(code.find("train_queue"), -1,
			"%s declares no train-queue state" % relative)

	# Where an instance type exists, the boundary still holds: it is a separate
	# script, it is not this definition, and the definition it holds carries the
	# same fields as every other definition with no player state among them. This
	# is what makes the instance line an extension of this contract rather than a
	# contradiction of it, and it holds whether or not that line has landed yet.
	var instance_path := Paths.project_dir().path_join(
		"scripts/units/unit_instance.gd")
	if FileAccess.file_exists(instance_path):
		var instance_script: Variant = load(instance_path)
		check(instance_script != null, "the unit-instance type is its own script")
		check(instance_script != UnitDefinition,
			"a unit instance is a DISTINCT type from UnitDefinition, not a "
				+ "widening of it")
		# Every definition in the catalog must still expose the same script
		# variables and none of them may be player state, which is exactly the
		# inventory asserted above — re-asserted here so a future instance type
		# cannot satisfy the distinctness check while quietly widening the
		# definition it holds.
		var held_stateful: Array = []
		var held_inventory := 0
		for held_id: Variant in UnitCatalog.legacy_ids(catalog):
			var held_definition = UnitCatalog.find(catalog, held_id)
			for property: Dictionary in held_definition.get_property_list():
				if (int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE) == 0:
					continue
				held_inventory += 1
				if PLAYER_STATE_NAMES.has(str(property["name"])):
					held_stateful.append(str(held_id) + "." + str(property["name"]))
		check_eq(held_stateful, [],
			"the definition an instance holds still carries no field that "
				+ "could hold player state")
		check(held_inventory == inventory.size(),
			"every definition still exposes the same field inventory: no "
				+ "player state migrated into the definition")
	else:
		check(true,
			"no unit-instance type exists yet: the boundary holds trivially "
				+ "until the instance capability lands")

	check_eq(_saved_shape_names(catalog), [],
		"no player-owned unit state is stored by this line: nothing here "
			+ "writes, and no save shape is introduced")


# ---------------------------------------------------------------------------
# No gameplay semantics (design D3)
# ---------------------------------------------------------------------------


## Neither module exposes a helper that computes behaviour from a parsed
## statistic, and both state the no-semantics rule in their own documentation
## where a reader will meet it.
func _check_semantics() -> void:
	var model_body := _source("res://scripts/units/unit_definition.gd")
	var catalog_body := _source("res://scripts/units/unit_catalog.gd")
	check(model_body != "" and catalog_body != "",
		"both unit modules are readable")
	check_eq(_methods(model_body), _sorted_unique(EXPECTED_MODEL_METHODS),
		"the model exposes exactly the parse and inventory helpers of design "
			+ "D3/D4 — no damage, defence, speed, lifetime, or timing helper")
	check_eq(_methods(catalog_body), _sorted_unique(EXPECTED_CATALOG_METHODS),
		"the catalog exposes exactly the lookup, count, raw-entry, and linkage "
			+ "helpers of design D1/D3/D7 — no behaviour helper")
	for body: String in [model_body, catalog_body]:
		var impure: Array = []
		for needle: String in PURITY_NEEDLES:
			if body.contains(needle):
				impure.append(needle)
		check_eq(impure, [],
			"neither unit module carries a node, a clock, a request, or a "
				+ "mutation (pure parse and lookup only)")
	var instance_functions: Array = []
	for line: String in model_body.split("\n"):
		if line.begins_with("\tfunc ") or line.begins_with("func "):
			if not line.contains(" static func "):
				instance_functions.append(line.strip_edges())
	check_eq(instance_functions, [],
		"every model helper is static, so the model holds no state that could "
			+ "drift between reads")
	check(model_body.contains("`attack: 10` is the committed value")
			and model_body.contains("**not** a damage rule"),
		"the model's own documentation states that a statistical field is a "
			+ "committed number and not a damage rule")
	check(catalog_body.contains("not a rule"),
		"the catalog's own documentation repeats the no-semantics rule")
	var no_render := 0
	var no_semantics := 0
	for claim: String in UnitCatalog.NON_CLAIMS:
		if claim.contains(NO_RENDER_CLAIM):
			no_render += 1
		if claim.find("no gameplay semantics") != -1:
			no_semantics += 1
	check(no_render >= 1,
		"the non-claims state verbatim that no unit is rendered, animated, or "
			+ "played")
	check(no_semantics >= 1,
		"the non-claims state that no gameplay semantics are attached to any "
			+ "parsed statistic")
	var undelivered := 0
	for line: Variant in [["unit instances", "unit instance"],
			["queues", "queue"], ["production", "production"],
			["collection", "collect"], ["movement", "movement"],
			["animations", "animation"], ["basic behaviors", "behaviour"]]:
		var named := false
		for claim: String in UnitCatalog.NON_CLAIMS:
			for form: String in line as Array:
				if claim.find(form) != -1:
					named = true
		check(named, "the non-claims name the '%s' deliver line as "
			% str((line as Array)[0]) + "undelivered")
		undelivered += 1
	check_eq(undelivered, 7,
		"every later M8 unit deliver line is named as undelivered")
	check(UnitCatalog.NON_CLAIMS.size() >= 10,
		"the evidence carries the full non-claim list (%d claims)"
			% UnitCatalog.NON_CLAIMS.size())


# ---------------------------------------------------------------------------
# Committed asset linkage only (design D7)
# ---------------------------------------------------------------------------


## A committed sprite reference resolves through the registry's asset-ID
## registry with a recorded status, and the report distinguishes the whole
## reference from its comma-separated parts — the committed set names a
## comma-joined list on part of the rows, and reporting only the whole string
## would misrepresent those as unresolvable. Linkage is reported and nothing
## more: no rendering, animation, or visual-fidelity claim.
func _check_linkage(catalog: Variant) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	var resolved := 0
	var unreportable: Array = []
	var unresolved_whole: Array = []
	var multi_part := 0
	var statuses := {}
	var part_total := 0
	var part_resolved := 0
	var claiming := 0
	var samples: Array = []
	for id_text: Variant in UnitCatalog.legacy_ids(catalog):
		var result: Dictionary = UnitCatalog.sprite_linkage(registry, catalog,
			id_text)
		if not bool(result.get("ok", false)):
			unreportable.append(str(id_text))
			continue
		var linkage: Dictionary = result["linkage"]
		if str(linkage.get("kind", "")) != UnitCatalog.SPRITE_KIND:
			unreportable.append("%s: wrong kind" % str(id_text))
			continue
		if int(linkage.get("part_count", 0)) > 1:
			multi_part += 1
		part_total += int(linkage.get("part_count", 0))
		part_resolved += int(linkage.get("parts_resolved", 0))
		if bool(linkage.get("resolved", false)):
			resolved += 1
			statuses[str(linkage.get("status", ""))] = \
				int(statuses.get(str(linkage.get("status", "")), 0)) + 1
			if samples.size() < 3:
				samples.append("%s -> %s (%s)" % [str(linkage.get("legacy_id",
					"")), str(linkage.get("reference", "")),
					str(linkage.get("status", ""))])
		else:
			unresolved_whole.append(str(id_text))
		if str(linkage.get("claim", "")).contains("linkage only"):
			claiming += 1
	check_eq(unreportable, [],
		"every definition's committed sprite linkage is reportable: no "
			+ "reference and no recorded status is silently dropped")
	var sample_note := "at least one committed sprite reference resolves (" \
		+ str(resolved) + " of " + str(EXPECTED_DEFINITIONS) \
		+ " whole references, statuses " + JSON.stringify(statuses) + ")"
	check(resolved > 0, sample_note)
	check_eq(unresolved_whole.size(), multi_part,
		"the only whole references that do not resolve are the committed "
			+ "comma-joined ones (" + str(multi_part) + "), and each is "
			+ "reported as such rather than dropped")
	var parts_note := "every comma-separated part of every committed sprite "
	parts_note += "reference resolves (" + str(part_resolved) + " of "
	parts_note += str(part_total) + " parts), so no row is left looking "
	parts_note += "unresolvable when its parts are not"
	check(part_resolved == part_total, parts_note)
	check_eq(claiming, EXPECTED_DEFINITIONS,
		"every linkage record states the linkage-only claim, so no reader can "
			+ "mistake a status for a rendering result")
	check(samples.size() >= 1, "resolved linkage samples: %s"
		% ", ".join(PackedStringArray(samples)))
	var missing := UnitCatalog.sprite_linkage(null, catalog, SAMPLE_ID)
	check_eq(bool(missing.get("ok", true)), false,
		"the linkage path fails closed without a loaded asset registry")
	var unknown := UnitCatalog.sprite_linkage(registry, catalog, "no_such_id")
	check_eq(bool(unknown.get("ok", true)), false,
		"the linkage path fails closed for an unknown legacy id")
	check(UnitCatalog.PROVENANCE["established"].size() >= 5
			and UnitCatalog.PROVENANCE["derived"].size() >= 2,
		"the provenance split records the established facts and the derived "
			+ "choices separately")


# ---------------------------------------------------------------------------
# Evidence report (design D8)
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


## Computes and writes the deterministic `unit-definitions-report-v1` report.
##
## EVERY fact about the model comes from `unit_definition.gd` and
## `unit_catalog.gd` — their own `FIELD_GROUPS`, `COST_RESOURCES`,
## `PROVENANCE`, and `NON_CLAIMS` — and every committed number comes from the
## registry entry that was just parsed, so the report cannot drift from the code
## it documents. Nothing here reads the wall clock, resolves a path outside the
## repository, or sends a request: that is what makes the file byte-identical
## across reruns.
func _write_report(path: String, registry: Variant, catalog: Variant,
		loaded: Dictionary) -> void:
	var rows := _committed_rows()
	var ids := UnitCatalog.legacy_ids(catalog)

	# -- Committed counts and the manifest's own record of the domain file --
	var committed_fields := {}
	var cost_resources := {}
	var property_keys := {}
	for row: Dictionary in rows:
		for field: Variant in row:
			committed_fields[str(field)] = true
	for id_text: Variant in ids:
		var definition = UnitCatalog.find(catalog, id_text)
		for resource: String in definition.costs:
			cost_resources[resource] = \
				int(cost_resources.get(resource, 0)) + 1
		for key: String in definition.properties:
			property_keys[key] = true

	# -- Coverage of every field that is absent on part of the set -----------
	var presence := {}
	for field: String in UnitDefinition.presence_flags():
		var base := field.trim_prefix("has_")
		var present := 0
		var absent := 0
		var zeros := 0
		for row: Dictionary in rows:
			var definition = UnitCatalog.find(catalog, str(row["legacy_id"]))
			if bool(definition.get(field)):
				present += 1
				if int(definition.get(base)) == 0:
					zeros += 1
			else:
				absent += 1
		presence[field] = {
			"field": base,
			"kind": "nullable bag" if UnitDefinition.NULLABLE_BAG_FIELDS.has(
				base) else "conditionally present integer",
			"present": present,
			"absent": absent,
			"committed_zero_present": zeros,
			"of": rows.size(),
			"flag": field,
			"absent_is_not_zero": "an absent field is never given a value in "
				+ "place of the committed one: a conditionally-present "
				+ "integer keeps its declared default and the nullable bag "
				+ "keeps null, and the flag is what tells absent from "
				+ "committed",
		}

	# -- Asset linkage -------------------------------------------------------
	var linkage := {
		"kind": UnitCatalog.SPRITE_KIND,
		"claim": "linkage only: whether the committed reference resolves "
			+ "through the asset-ID registry and with which recorded status. "
			+ "No rendering correctness, no animation correctness, no visual "
			+ "fidelity, and no claim that a unit can be drawn, animated, or "
			+ "played.",
		"whole_reference": {"resolved": 0, "unresolved": 0, "statuses": {}},
		"parts": {"total": 0, "resolved": 0, "unresolved": 0, "statuses": {}},
		"multi_part_definitions": 0,
	}
	var whole_statuses := {}
	var part_statuses := {}
	for id_text: Variant in ids:
		var result: Dictionary = UnitCatalog.sprite_linkage(registry, catalog,
			id_text)
		var link: Dictionary = result["linkage"]
		if int(link.get("part_count", 0)) > 1:
			linkage["multi_part_definitions"] = \
				int(linkage["multi_part_definitions"]) + 1
		if bool(link.get("resolved", false)):
			linkage["whole_reference"]["resolved"] = \
				int(linkage["whole_reference"]["resolved"]) + 1
			var status := str(link.get("status", ""))
			whole_statuses[status] = int(whole_statuses.get(status, 0)) + 1
		else:
			linkage["whole_reference"]["unresolved"] = \
				int(linkage["whole_reference"]["unresolved"]) + 1
		for part: Dictionary in link.get("parts", []):
			linkage["parts"]["total"] = int(linkage["parts"]["total"]) + 1
			if bool(part.get("resolved", false)):
				linkage["parts"]["resolved"] = \
					int(linkage["parts"]["resolved"]) + 1
				var status := str(part.get("status", ""))
				part_statuses[status] = int(part_statuses.get(status, 0)) + 1
			else:
				linkage["parts"]["unresolved"] = \
					int(linkage["parts"]["unresolved"]) + 1
	linkage["whole_reference"]["statuses"] = whole_statuses
	linkage["parts"]["statuses"] = part_statuses
	linkage["reference_form_note"] = "the committed img_name is a single " \
		+ "reference on most rows and a comma-joined list on the rest; both " \
		+ "the whole reference and each part are reported, because reporting " \
		+ "only the whole string would misrepresent a comma-joined row as " \
		+ "unresolvable when every one of its parts resolves"

	# -- The raw-entry escape hatch ------------------------------------------
	var parsed_fields := UnitDefinition.parsed_fields()
	var unparsed: Array = []
	for field: String in committed_fields:
		if not parsed_fields.has(field):
			unparsed.append(field)
	unparsed.sort()
	var sample_entry: Dictionary = UnitCatalog.raw_entry(registry, catalog,
		SAMPLE_ID)["entry"]

	# -- The static/instance boundary ----------------------------------------
	var group_counts := {}
	for group: String in UnitDefinition.GROUP_ORDER:
		group_counts[group] = (UnitDefinition.field_inventory()[
			group] as Array).size()
	var bounds := _id_bounds(ids)
	var report := {
		"schema": "unit-definitions-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_definitions.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and every table is derived from the parsed model "
				+ "and the verified registry; the catalog preserves the "
				+ "committed row order and every derived set is sorted before "
				+ "it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) "
				+ "plus one trailing newline; every number written is an "
				+ "integer — the pinned engine's integral floats are "
				+ "normalised on the way in, which changes no value — so no "
				+ "float formatting varies between runs",
		},
		"verbatim": {
			"claim": "each parsed field equals its committed value exactly: no "
				+ "scaling, rounding, defaulting, or coercion",
			"transport_note": "the pinned engine's JSON parser represents "
				+ "every committed number as a float, including the integers "
				+ "the content package's rule R1 coerces, so an integer field "
				+ "stores the exact integer an integral float denotes. This is "
				+ "the documented transport tolerance the delivered "
				+ "placement_catalog.gd applies to the same field class, and "
				+ "it changes no value: a non-integral or out-of-range number "
				+ "can never match.",
		},
		"content_source": {
			"domain": UnitCatalog.DOMAIN,
			"file": str(catalog.source_file),
			"schema": "packages/game-content/schemas/unit.schema.json",
			"manifest": "packages/game-content/manifest.json",
			"manifest_bytes": _as_int(_manifest_record(registry, "bytes")),
			"manifest_sha256": _manifest_record(registry, "sha256"),
			"file_bytes": _file_bytes(str(catalog.source_file)),
			"file_sha256": _digest_record(str(catalog.source_file)),
			"manifest_and_file_agree": _manifest_record(registry, "sha256") \
				== _digest_record(str(catalog.source_file)),
			"content_fingerprint": str(catalog.content_fingerprint),
			"manifest_outputs_verified": int(loaded.get("files_verified", 0)),
			"manifest_bytes_verified": int(loaded.get("bytes_verified", 0)),
			"enumeration": UnitCatalog.ENUMERATION,
			"enumeration_note": "the catalog enumerates through "
				+ "ContentRegistry.legacy_ids(domain), a public accessor this "
				+ "change added, which returns the ids of the index the "
				+ "registry built during its verified load; the catalog "
				+ "cross-checks the enumerated count against the registry's own "
				+ "count() and fails closed on disagreement, and no file is "
				+ "re-read behind the registry's back, so the manifest's "
				+ "byte-count and digest verification stays the single gate",
		},
		"counts": {
			"definitions": ids.size(),
			"committed_fields_union": committed_fields.size(),
			"committed_fields_on_every_row": _minimum_field_count(rows),
			"typed_committed_fields": parsed_fields.size(),
			"typed_presence_flags": UnitDefinition.presence_flags().size(),
			"typed_fields_including_presence_flags":
				parsed_fields.size() + UnitDefinition.presence_flags().size(),
			"group_field_counts": group_counts,
			"unparsed_committed_fields": unparsed.size(),
			"note": "typed_committed_fields counts the committed field names "
				+ "the model parses; the presence flags are the model's own "
				+ "record of which of those fields the committed row carries, "
				+ "not committed fields themselves",
		},
		"legacy_ids": {
			"form": "string, preserved verbatim (design D5)",
			"count": ids.size(),
			"distinct": _distinct(ids),
			"min": str(bounds[0]),
			"max": str(bounds[1]),
			"committed_order_first": str(ids[0]),
			"committed_order_last": str(ids[ids.size() - 1]),
			"order": "the committed row order of units.json, which is not a "
				+ "numeric sort: the ids are digit strings, so a collation "
				+ "would interleave them and misrepresent the committed order",
			"wrong_form_fails_closed": ["int", "float", "bool", "array",
				"object", "null", "padded string", "zero-padded string",
				"unknown id", "empty string", "name"],
			"range_note": "the ids are the legacy item ids the normalized "
				+ "package records, not its positional indices; coercing one "
				+ "to an integer would break the registry's own index, and the "
				+ "range is computed over the values rather than read off the "
				+ "order",
		},
		"field_groups": _group_record(),
		"embedded_json_bags": {
			"committed_form": "the content package's rule R2 already coerced "
				+ "the legacy embedded-JSON strings, so the committed rows "
				+ "carry objects; the parser accepts the committed object and "
				+ "the delivered catalog's JSON-string transport tolerance, and "
				+ "both fail closed alike",
			"costs": {
				"group": UnitDefinition.GROUP_ECONOMY,
				"vocabulary": UnitDefinition.COST_RESOURCES,
				"vocabulary_source": "aliased from placement_catalog.gd's own "
					+ "COST_RESOURCES, so this model cannot disagree with the "
					+ "delivered purchase, shop, expansion and level surfaces",
				"resources_used": cost_resources,
				"unknown_keys": 0,
				"non_integer_amounts": 0,
				"note": "resource name -> integer amount; an empty committed "
					+ "object stays empty and is never filled in from `cost`",
			},
			"properties": {
				"group": "outside the five groups: a free-form committed flag "
					+ "map, not one of design D3's five categories",
				"distinct_keys": _sorted_array(property_keys.keys()),
				"committed_value_type": "string",
				"note": "reproduced verbatim; no key is interpreted, so no "
					+ "property grants a capability, a movement mode, or a "
					+ "behaviour",
			},
		},
		"conditionally_present": presence,
		"raw_entry_escape_hatch": {
			"accessor": "UnitCatalog.raw_entry(registry, catalog, legacy_id)",
			"unparsed_committed_fields": unparsed,
			"count": unparsed.size(),
			"example": {"legacy_id": SAMPLE_ID, "field": "in_store",
				"value": _as_int(sample_entry.get("in_store", null))},
			"note": "the typed groups are the typed VIEW of the committed row, "
				+ "not a filter over it: every field outside them stays "
				+ "reachable from the committed row, so a new content field "
				+ "needs no model change and nothing is silently dropped",
		},
		"asset_linkage": linkage,
		"boundary": {
			"static": "UnitDefinition is committed content: typed, read-only, "
				+ "resolved through the content registry, carrying no player "
				+ "state",
			"player_state_fields": [],
			"player_state_field_names_checked": PLAYER_STATE_NAMES,
			"instance": "none: this change adds no UnitInstance type, no save "
				+ "shape, no instance parsing, no garrison state, and no "
				+ "production-queue state",
			"endpoint": "none: a definition is read from the already-loaded "
				+ "registry, so no compatibility route was added, no client "
				+ "intent is sent, and no server- or client-supplied unit "
				+ "content is introduced",
			"undelivered_lines": ["unit instances", "queues", "production",
				"collection", "movement", "animations", "basic behaviors"],
			"note": "the boundary is structural, not conventional: a "
				+ "definition has no field that could be widened into an "
				+ "instance, so the later unit-instances line grows into a "
				+ "named edge",
		},
		"provenance": UnitCatalog.PROVENANCE,
		"non_claims": UnitCatalog.NON_CLAIMS,
	}
	check(not report["non_claims"].is_empty(),
		"the report carries the evidence's non-claims")
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)"
		% problem)
	if problem == "":
		check(FileAccess.file_exists(path),
			"the report file exists at %s" % path)
		info("report written: %s" % path)


## The five groups with their committed field names and counts, read from the
## model's own table so the report cannot describe a model that no longer
## exists.
func _group_record() -> Array:
	var out: Array = []
	var inventory := UnitDefinition.field_inventory()
	for group: String in UnitDefinition.GROUP_ORDER:
		out.append({
			"group": group,
			"fields": inventory[group],
			"count": (inventory[group] as Array).size(),
		})
	return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## The committed rows, read from the committed file itself. Used only to
## assert the model AGAINST the committed bytes; every definition the catalog
## serves is resolved through the registry.
func _committed_rows() -> Array:
	var parsed: Variant = _read_json(Paths.repo_root().path_join(
		"packages/game-content/normalized/units.json"))
	if not (parsed is Array):
		fail("the committed units.json parses as a JSON array")
		return []
	return parsed


## Every definition's own field values, for the immutability comparison.
func _snapshot(definition: Variant) -> Dictionary:
	var out := {}
	for property: Dictionary in definition.get_property_list():
		if (int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE) == 0:
			continue
		var field := str(property["name"])
		var value: Variant = definition.get(field)
		out[field] = JSON.stringify(value) if (value is Dictionary) else value
	return out


## The legacy IDs that a definition would have to record as player-owned state,
## asserted empty. Nothing is written anywhere by this line, so the honest form
## of the check is that no model field, no module source, and no client file
## declares such a state.
func _saved_shape_names(catalog: Variant) -> Array:
	var out: Array = []
	for id_text: Variant in UnitCatalog.legacy_ids(catalog):
		var definition = UnitCatalog.find(catalog, id_text)
		for field: String in PLAYER_STATE_NAMES:
			if definition.get(field) != null:
				out.append("%s.%s" % [str(id_text), field])
	return out


## Every `.gd` source in the client project, project-relative.
func _project_sources() -> Array:
	var out: Array = []
	var collected: Array = []
	_collect_sources(Paths.project_dir(), "", collected)
	for relative: Variant in collected:
		out.append(str(relative))
	out.sort()
	return out


## A source file's DECLARATIONS: comment lines are dropped and string-literal
## content is blanked, so a prose mention or a recorded non-claim string can
## never be mistaken for a declared surface. Only what remains — the code a
## reader would compile — is searched for an instance or garrison type.
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


func _collect_sources(directory: String, prefix: String, out: Array) -> void:
	var handle := DirAccess.open(directory)
	if handle == null:
		return
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = handle.get_next()
			continue
		var full := directory.path_join(entry)
		if handle.current_is_dir():
			if entry != ".godot":
				_collect_sources(full, prefix + entry + "/", out)
		elif str(entry).ends_with(".gd"):
			out.append(prefix + entry)
		entry = handle.get_next()
	handle.list_dir_end()


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


## Ascending, duplicates collapsed — the shape a field-name inventory is
## compared in, so a name that appears in two declared groups cannot make an
## otherwise exact inventory look wrong.
func _sorted_unique(values: Variant) -> Array:
	var out: Array = []
	var previous: Variant = null
	for value: Variant in _sorted_array(values):
		if previous != null and str(value) == str(previous):
			continue
		previous = value
		out.append(value)
	return out


func _distinct(values: Array) -> int:
	var seen := {}
	for value: Variant in values:
		seen[str(value)] = true
	return seen.size()


## The numeric low and high of a list of digit-string legacy ids, as strings.
## Computed over the VALUES, because the ids are strings and the committed row
## order is not a numeric sort.
func _id_bounds(ids: Array) -> Array:
	var low := 9223372036854775807
	var high := -9223372036854775807
	for id_text: Variant in ids:
		var value := int(str(id_text))
		low = value if value < low else low
		high = value if value > high else high
	return [str(low), str(high)]


## True when the digit-string ids ascend numerically, which the committed row
## order does not — the record that the range must be computed, not read off.
func _ids_ascend(ids: Array) -> bool:
	for index in range(1, ids.size()):
		if int(str(ids[index])) < int(str(ids[index - 1])):
			return false
	return true


## A committed number as the exact integer it denotes. The pinned engine's
## JSON parser yields integral floats; every number the report writes goes
## through here, so the report carries integers and its determinism does not
## depend on a float's serialization.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


## The smallest number of committed fields any row carries — the count every
## row has, against the union across the whole committed set.
func _minimum_field_count(rows: Array) -> int:
	var smallest := -1
	for row: Dictionary in rows:
		var count := (row as Dictionary).size()
		if smallest == -1 or count < smallest:
			smallest = count
	return smallest


## The manifest's own record for one output record of the `units` domain.
func _manifest_record(registry: Variant, field: String) -> Variant:
	var manifest: Variant = _read_json(Paths.repo_root().path_join(
		"packages/game-content/manifest.json"))
	if not (manifest is Dictionary):
		return null
	var wanted := "packages/game-content/normalized/units.json"
	for record: Variant in (manifest as Dictionary).get("outputs", []):
		if (record is Dictionary) and str((record as Dictionary).get(
				"file", "")) == wanted:
			return (record as Dictionary).get(field, null)
	return null


func _file_bytes(relative: String) -> Variant:
	if relative.is_empty():
		return null
	var check_result := Paths.file_sha256_checked(
		Paths.repo_root().path_join(relative))
	return int(check_result.get("bytes", -1)) if bool(
		check_result.get("ok", false)) else null


func _digest_record(relative: String) -> String:
	if relative.is_empty():
		return ""
	return Paths.file_sha256(Paths.repo_root().path_join(relative))


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


func _read_bytes(path: String) -> PackedByteArray:
	return FileAccess.get_file_as_bytes(path)


func _copy_file(from_path: String, to_path: String) -> bool:
	var bytes := _read_bytes(from_path)
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