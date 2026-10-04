extends "res://tests/test_base.gd"
## Hermetic suite for the `godot-mission-vocabulary` line.
##
## Exercises the typed read-only projection in
## `scripts/missions/mission_vocabulary.gd` over the **committed** vocabulary
## table, and - just as load-bearing - proves the three structural guards that
## keep this line honest:
##
##   1. **Byte-faithfulness.** The table is a transcription of the legacy
##      `MISSION_*` declarations, so the suite re-derives those declarations
##      from `constants.py` **as bytes** and requires name, value, and declared
##      line to be byte-equal for every entry, plus entry-count and gap-set
##      equality. A mistranscribed value or a padded table fails here rather
##      than shipping.
##   2. **Zero consumers.** The delivered module's whole `static func`
##      inventory is pinned, no delivered code identifier may be named after a
##      mission type, none of the absent helpers may exist, and the module's
##      arithmetic figures are counted rather than asserted in prose.
##   3. **Ownership.** Mission *state* belongs to `godot-quests`, so this
##      capability's code may not reference a mission-state field anywhere
##      except the one literal that names them as foreign.
##
## All three guards are **proven by injection** during Apply, not trusted; see
## `openspec/changes/2026-10-05-mission-vocabulary/tasks.md`.
##
## `-- --report=<path>` writes the deterministic `mission-vocabulary-report-v1`
## document. Every table in it is generated from the delivered module's own
## constants, from this run's own measurement of the committed legacy source, or
## from committed content bytes. Nothing reads the wall clock and no absolute
## path is written, so reruns reproduce the bytes.

const MissionVocabulary = preload("res://scripts/missions/mission_vocabulary.gd")

## `Paths` is inherited from the shared base harness; redeclaring it here would
## shadow it and fail the parse.

## The delivered module, relative to the Godot project directory.
const MODULE_PATH := "scripts/missions/mission_vocabulary.gd"

## The legacy source the committed table is generated from and byte-checked
## against, repository-relative.
const LEGACY_DECLARATION_SOURCE := "constants.py"

## The committed table, relative to the Godot project directory.
const TABLE_RELATIVE := "content/mission_vocabulary.json"

## The committed entry count, the value range, and the numbering gaps, all
## measured from `constants.py` and cross-checked against it per run.
const EXPECTED_COUNT := 64
const EXPECTED_LOWEST := 0
const EXPECTED_HIGHEST := 67
const EXPECTED_GAPS := [9, 10, 20, 57]

## The capabilities' property inventories, pinned so no derived field can be
## added to a projection that is supposed to carry committed content only.
const EXPECTED_ENTRY_PROPERTIES := ["declared_at", "legacy_id", "value"]
const EXPECTED_VOCABULARY_PROPERTIES := ["entries", "gaps", "highest", "lowest"]

## The capability that owns mission STATE, asserted present so this line cannot
## orphan the fields it deliberately does not project.
const QUEST_FLOW_PATH := "scripts/units/quest_flow.gd"

const DEFAULT_REPORT_PATH := "evidence/mission-vocabulary/report.json"

## Comparison tokens that would make a line a comparison at all.
const COMPARISON_TOKENS := ["==", "!=", "<=", ">=", "<", ">"]

## Tokens whose presence would be arithmetic or bit manipulation over a value.
const ARITHMETIC_TOKENS := {
	"multiply_operators": "*",
	"divide_operators": "/",
	"power_operators": "**",
	"bitwise_operators": "&",
	"shift_operators": "<<",
}


func run_scenario() -> void:
	var vocabulary = _check_committed_projection()
	var declarations := _check_byte_faithfulness(vocabulary)
	_check_fail_closed()
	_check_ordering_independence()
	_check_gaps_and_overlaps(vocabulary)
	_check_globals()
	_check_zero_consumer_guards()
	_check_ownership_boundary()
	var absence := _check_legacy_absence()

	var path := _report_path_arg()
	if path != "":
		_write_report(path, {
			"vocabulary": vocabulary,
			"declarations": declarations,
			"absence": absence,
		})


# ---------------------------------------------------------------------------
# 1. The committed projection
# ---------------------------------------------------------------------------


## Load and verify the committed projection. Returns the projected vocabulary, or
## `null` when it did not load, so later sections report against nothing rather
## than against a default.
func _check_committed_projection():
	info("--- committed projection ---")
	var loaded := MissionVocabulary.load_vocabulary()
	if not loaded.get("ok", false):
		fail("the committed vocabulary table loads: %s"
			% str(loaded.get("error", "unknown")))
		return null

	var vocabulary = loaded["vocabulary"]
	var entries: Array = vocabulary.entries

	check_eq(entries.size(), EXPECTED_COUNT,
		"the committed vocabulary carries all %d declarations" % EXPECTED_COUNT)
	check_eq(int(vocabulary.lowest), EXPECTED_LOWEST,
		"the lowest committed value is %d" % EXPECTED_LOWEST)
	check_eq(int(vocabulary.highest), EXPECTED_HIGHEST,
		"the highest committed value is %d" % EXPECTED_HIGHEST)

	# Committed value order, reported verbatim.
	var ordered := true
	var previous := EXPECTED_LOWEST - 1
	for entry in entries:
		if int(entry.value) <= previous:
			ordered = false
		previous = int(entry.value)
	check(ordered,
		"entries are reported in strictly ascending committed-value order")

	# Names and values are unique, so nothing is a silent duplicate.
	var names := {}
	var values := {}
	var duplicates := 0
	for entry in entries:
		if names.has(entry.legacy_id) or values.has(int(entry.value)):
			duplicates += 1
		names[entry.legacy_id] = true
		values[int(entry.value)] = true
	check_eq(duplicates, 0,
		"no two declarations share a name or a value")

	# Every entry records where it is declared, and every entry is typed.
	var without_provenance := 0
	for entry in entries:
		if str(entry.declared_at) == "":
			without_provenance += 1
	check_eq(without_provenance, 0,
		"every declaration records where it is declared in the legacy source")

	# No derived field: the typed projections expose exactly their committed
	# inventory, so a category or a group cannot be added unnoticed.
	check_eq(_script_variables(MissionVocabulary.Entry.new()),
		EXPECTED_ENTRY_PROPERTIES,
		"a declaration exposes only its committed name, value, and provenance")
	check_eq(_script_variables(MissionVocabulary.Vocabulary.new()),
		EXPECTED_VOCABULARY_PROPERTIES,
		"the vocabulary exposes only its entries, gaps, and value range")

	# The endpoints, read by name rather than by index, so a reordering of the
	# committed numbering would surface here.
	check_eq(str(entries[0].legacy_id), "MISSION_NONE",
		"the lowest committed declaration is MISSION_NONE")
	check_eq(int(entries[0].value), EXPECTED_LOWEST,
		"and carries its committed value verbatim")
	check_eq(str(entries[entries.size() - 1].legacy_id), "MISSION_KILLED_ENEMY",
		"the highest committed declaration is MISSION_KILLED_ENEMY")
	check_eq(int(entries[entries.size() - 1].value), EXPECTED_HIGHEST,
		"and carries its committed value verbatim")

	# Read-only by construction: each read hands back a fresh snapshot, so
	# mutating one cannot change what the next read reports.
	var original := int(entries[0].value)
	entries[0].value = original + 1000
	var reloaded := MissionVocabulary.load_vocabulary()
	check(reloaded.get("ok", false),
		"the vocabulary reloads for the snapshot check")
	if reloaded.get("ok", false):
		var fresh = reloaded["vocabulary"]
		check_eq(int(fresh.entries[0].value), original,
			"mutating one projected copy cannot change what a fresh read reports")
	entries[0].value = original
	check_eq(int(entries[0].value), original,
		"and the local copy is restored so the rest of the run sees committed data")

	return vocabulary


# ---------------------------------------------------------------------------
# 2. Byte-faithfulness to the legacy declarations
# ---------------------------------------------------------------------------


## Re-derive the declarations from `constants.py` as bytes and require the
## committed table to match them exactly. Returns the extraction so the report
## can publish it.
func _check_byte_faithfulness(vocabulary) -> Array:
	info("--- byte-faithfulness to %s ---" % LEGACY_DECLARATION_SOURCE)
	var declarations := _legacy_declarations()

	check_eq(declarations.size(), EXPECTED_COUNT,
		"the legacy source declares %d MISSION_* names, measured this run"
		% EXPECTED_COUNT)

	if vocabulary == null:
		fail("byte-faithfulness is checked against a loaded vocabulary")
		return declarations

	var projected := {}
	for entry in (vocabulary.entries as Array):
		projected[str(entry.legacy_id)] = entry

	var declared_names := _declaration_names(declarations)
	var not_in_projection := 0
	var mismatched_value := 0
	var mismatched_line := 0
	for declaration in declarations:
		var name := str((declaration as Dictionary).get("legacy_id", ""))
		if not projected.has(name):
			not_in_projection += 1
			continue
		var committed = projected[name]
		if int(committed.value) != int((declaration as Dictionary).get("value", 0)):
			mismatched_value += 1
		if str(committed.declared_at) != str(
				(declaration as Dictionary).get("declared_at", "")):
			mismatched_line += 1

	var padded := 0
	for name: String in projected.keys():
		if not declared_names.has(name):
			padded += 1

	check_eq(not_in_projection, 0,
		"every legacy declaration appears in the committed table")
	check_eq(mismatched_value, 0,
		"every committed value is byte-equal to the legacy declaration")
	check_eq(mismatched_line, 0,
		"every committed provenance line matches the legacy declaration line")
	check_eq(padded, 0,
		"the committed table adds no declaration the legacy source lacks")

	# The gap set is re-derived from the extraction, not read from the table, so
	# a table that disagrees about its own gaps fails here.
	var extracted_values := {}
	for declaration in declarations:
		extracted_values[int((declaration as Dictionary).get("value", 0))] = true
	var extracted_gaps: Array = []
	for value in range(EXPECTED_LOWEST, EXPECTED_HIGHEST + 1):
		if not extracted_values.has(value):
			extracted_gaps.append(value)
	check_eq(extracted_gaps, EXPECTED_GAPS,
		"the numbering gaps re-derived from the legacy source are the committed four")

	return declarations


## The legacy declarations, read as bytes and parsed from the declaration form.
##
## Deliberately an independent extraction: it never reads the committed table, so
## agreement between the two is evidence rather than a tautology.
func _legacy_declarations() -> Array:
	var out: Array = []
	var absolute := Paths.repo_root().path_join(LEGACY_DECLARATION_SOURCE)
	var handle := FileAccess.open(absolute, FileAccess.READ)
	if handle == null:
		fail("the legacy declaration source is readable: %s" % absolute)
		return out
	var bytes := handle.get_buffer(handle.get_length())
	var text := bytes.get_string_from_utf8()
	var number := 0
	for raw in text.split("\n"):
		number += 1
		var trimmed := _strip_comment(str(raw)).strip_edges()
		if not trimmed.begins_with("MISSION_"):
			continue
		var equals := trimmed.find("=")
		if equals < 0:
			continue
		var name := trimmed.substr(0, equals).strip_edges()
		var value_text := trimmed.substr(equals + 1).strip_edges()
		if not value_text.is_valid_int():
			continue
		out.append({
			"legacy_id": name,
			"value": int(value_text),
			"declared_at": "%s:%d" % [LEGACY_DECLARATION_SOURCE, number],
		})
	return out


func _declaration_names(declarations: Array) -> Dictionary:
	var out := {}
	for declaration in declarations:
		out[str((declaration as Dictionary).get("legacy_id", ""))] = true
	return out


# ---------------------------------------------------------------------------
# 3. Fail-closed parsing
# ---------------------------------------------------------------------------


## Every refusal path, over crafted in-memory documents rather than only over the
## one committed file.
func _check_fail_closed() -> void:
	info("--- fail-closed parsing ---")

	var valid_entry := {"legacy_id": "MISSION_NONE", "value": 0,
		"declared_at": "constants.py:984"}

	# A minimal well-formed document, to prove the refusals are not the only path.
	var good := MissionVocabulary.parse_table_text(JSON.stringify({
		"policy": MissionVocabulary.POLICY,
		"entry_count": 1,
		"entries": [valid_entry],
	}))
	check(good.get("ok", false),
		"a well-formed minimal document is accepted")

	var refusals := {
		"empty document": "",
		"whitespace only": "   \n  ",
		"arbitrary text": "this is not json",
		"a bare literal": "null",
		"a bare number": "42",
		"root is an array": "[1, 2, 3]",
		"unexpected policy": JSON.stringify({
			"policy": "something-else", "entry_count": 1,
			"entries": [valid_entry]}),
		"entries missing": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1}),
		"entries is not an array": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": {"a": 1}}),
		"entries is empty": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 0,
			"entries": []}),
		"entry is not an object": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": ["MISSION_NONE"]}),
		"name is not a string": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": 7, "value": 0}]}),
		"name is empty": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": "", "value": 0}]}),
		"duplicate name": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 2,
			"entries": [valid_entry, valid_entry.duplicate()]}),
		"value missing": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": "MISSION_NONE"}]}),
		"value is a string": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": "MISSION_NONE", "value": "0"}]}),
		"value is not integral": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": "MISSION_NONE", "value": 3.5}]}),
		"value is a boolean": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 1,
			"entries": [{"legacy_id": "MISSION_NONE", "value": true}]}),
		"duplicate value": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 2,
			"entries": [{"legacy_id": "MISSION_A", "value": 5},
				{"legacy_id": "MISSION_B", "value": 5}]}),
		"entry_count disagrees": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": 9,
			"entries": [valid_entry]}),
		"entry_count is not an integer": JSON.stringify({
			"policy": MissionVocabulary.POLICY, "entry_count": "1",
			"entries": [valid_entry]}),
	}

	for label: String in refusals.keys():
		var result := MissionVocabulary.parse_table_text(str(refusals[label]))
		check(not result.get("ok", true),
			"%s is refused rather than accepted" % label)
		check(str(result.get("error", "")) != "",
			"%s is refused with a named error" % label)
		check(not result.has("vocabulary"),
			"%s produces no vocabulary at all" % label)

	# The exact-integer transport guard, which the JSON path cannot reach for a
	# non-finite or out-of-range number because JSON cannot express either.
	var transport := {
		"int zero": [0, true, 0],
		"int max": [int(MissionVocabulary.MAX_INTEGER), true,
			int(MissionVocabulary.MAX_INTEGER)],
		"integral float": [12.0, true, 12],
		"negative int": [-3, true, -3],
		"float infinity": [INF, false, "value is not finite"],
		"float NaN": [NAN, false, "value is not finite"],
		"non integral float": [3.5, false, "value is not integral"],
		"beyond exact range": [MissionVocabulary.MAX_INTEGER * 2.0, false,
			"value exceeds exact integer range"],
		"string": ["12", false, "value is not an integer"],
		"null": [null, false, "value is not an integer"],
	}
	for label: String in transport.keys():
		var expected: Array = transport[label]
		var got := MissionVocabulary._as_exact_integer(expected[0])
		check_eq(bool(got.get("ok", false)), bool(expected[1]),
			"the exact-integer guard accepts or refuses %s as recorded" % label)
		if bool(expected[1]):
			check_eq(int(got.get("value", 0)), int(expected[2]),
				"and yields the exact integer for %s" % label)
		else:
			check_eq(str(got.get("error", "")), str(expected[2]),
				"and refuses %s with the recorded reason" % label)


## The projection must not depend on the table's storage order.
##
## Found by injection rather than by reading: mistranscribing one value above the
## committed range did not fail as a value mismatch, it failed as an entry-count
## mismatch, because the ordering pass had used the last entry in file order as
## its upper bound and dropped the outlier silently. This section is the
## regression check - a document stored out of order, with one value far above
## the rest, must project **every** declaration, in ascending value order.
func _check_ordering_independence() -> void:
	info("--- ordering independence ---")

	var result := MissionVocabulary.parse_table_text(JSON.stringify({
		"policy": MissionVocabulary.POLICY,
		"entry_count": 3,
		"entries": [
			{"legacy_id": "MISSION_THIRD", "value": 30},
			{"legacy_id": "MISSION_FIRST", "value": 10},
			{"legacy_id": "MISSION_ABOVE_THE_REST", "value": 900},
		],
	}))
	check(result.get("ok", false),
		"a document stored out of order is accepted")
	if not result.get("ok", false):
		fail("ordering independence is checked against an accepted document")
		return

	var vocabulary = result["vocabulary"]
	var entries: Array = vocabulary.entries
	check_eq(entries.size(), 3,
		"every declaration survives, whatever order the table stores them in")
	var reported: Array = []
	for entry in entries:
		reported.append(str(entry.legacy_id))
	check_eq(reported,
		["MISSION_FIRST", "MISSION_THIRD", "MISSION_ABOVE_THE_REST"],
		"and they are reported in ascending committed-value order")
	check_eq(int(vocabulary.lowest), 10,
		"the lowest value is the smallest parsed value, not the first stored one")
	check_eq(int(vocabulary.highest), 900,
		"the highest value is the largest parsed value, not the last stored one")


# ---------------------------------------------------------------------------
# 4. Gaps and overlapping declarations
# ---------------------------------------------------------------------------


## Gaps are reported as content and never closed; the overlapping declarations
## are reported as observations and never resolved.
func _check_gaps_and_overlaps(vocabulary) -> void:
	info("--- gaps and overlapping declarations ---")
	if vocabulary == null:
		fail("gaps are checked against a loaded vocabulary")
		return

	var entries: Array = vocabulary.entries
	var present := {}
	for entry in entries:
		present[int(entry.value)] = true

	var gaps: Array = Array(vocabulary.gaps)
	check_eq(gaps, EXPECTED_GAPS,
		"the projected gaps are exactly the committed four")

	# No gap was closed: no entry carries a value inside a gap.
	var filled := 0
	for gap: int in EXPECTED_GAPS:
		if present.has(gap):
			filled += 1
	check_eq(filled, 0,
		"no gap was closed by a synthesised declaration")

	# The gap arithmetic is the committed one, not a re-derivation: the number of
	# gaps must be exactly the span minus the entry count.
	check_eq(gaps.size(), int(vocabulary.highest) - int(vocabulary.lowest) + 1
		- entries.size(),
		"the gap count is the committed span minus the committed entry count")

	# The recorded overlap observations are verified to still hold, and are
	# reported unresolved with no preferred member.
	var observations := MissionVocabulary.recorded_overlap_observations()
	check_eq(observations.size(),
		MissionVocabulary.RECORDED_OVERLAP_OBSERVATIONS.size(),
		"every recorded overlap observation is reported")

	for observation in observations:
		var group: Dictionary = observation
		var label := str(group.get("observation", ""))
		var names: Array = group.get("names", [])
		var expected_values: Array = group.get("values", [])
		check_eq(names.size(), expected_values.size(),
			"the %s observation pairs each name with a value" % label)
		for index in names.size():
			var name := str(names[index])
			check(present.has(int(expected_values[index])),
				"the %s observation holds: %s is %d"
				% [label, name, int(expected_values[index])])
			var matched := false
			for entry in entries:
				if str(entry.legacy_id) == name \
						and int(entry.value) == int(expected_values[index]):
					matched = true
			check(matched,
				"and the projection carries %s at that value" % name)
		check_eq(bool(group.get("resolved", true)), false,
			"the %s observation is reported unresolved" % label)
		check_eq(str(group.get("preferred", "x")), "",
			"the %s observation names no preferred member" % label)


# ---------------------------------------------------------------------------
# 5. The committed mission-adjacent globals
# ---------------------------------------------------------------------------


## The three globals are reported verbatim, unenforced, and never duplicated.
func _check_globals() -> void:
	info("--- committed mission-adjacent globals ---")

	var rows := [
		{"legacy_id": "NUM_ACTIVE_MISSIONS", "key": "NUM_ACTIVE_MISSIONS",
			"kind": "global_entry", "source_file": "config/main.json",
			"source_layer": "stored", "value": 5, "value_type": "integer",
			"content_version": "measured-this-run"},
		{"legacy_id": "PERMISSION_PACK_UNITS", "key": "PERMISSION_PACK_UNITS",
			"kind": "global_entry", "source_file": "config/main.json",
			"source_layer": "stored", "value": [10, 20, 30, 40],
			"value_type": "array", "content_version": "measured-this-run"},
		{"legacy_id": "PERMISSION_COSTS", "key": "PERMISSION_COSTS",
			"kind": "global_entry", "source_file": "config/main.json",
			"source_layer": "stored",
			"value": {"10": 10, "20": 20, "30": 30, "40": 40},
			"value_type": "object", "content_version": "measured-this-run"},
	]

	var result := MissionVocabulary.mission_globals(rows)
	check(result.get("ok", false),
		"the three committed globals are read through the registry rows")

	var globals: Dictionary = result.get("globals", {})
	check_eq(globals.size(), MissionVocabulary.MISSION_GLOBALS.size(),
		"exactly the three mission globals are reported, none added")

	check_eq(int((globals.get("NUM_ACTIVE_MISSIONS", {}) as Dictionary)
		.get("value", -1)), 5,
		"the active-mission count is reported as the committed 5")
	check_eq(str((globals.get("NUM_ACTIVE_MISSIONS", {}) as Dictionary)
		.get("value_type", "")), "integer",
		"and reports its committed type")

	check_eq((globals.get("PERMISSION_PACK_UNITS", {}) as Dictionary)
		.get("value", []), [10, 20, 30, 40],
		"the permission pack unit list is reported verbatim, in committed order")
	check_eq(str((globals.get("PERMISSION_PACK_UNITS", {}) as Dictionary)
		.get("value_type", "")), "array", "and reports its committed type")

	check_eq((globals.get("PERMISSION_COSTS", {}) as Dictionary)
		.get("value", {}), {"10": 10, "20": 20, "30": 30, "40": 40},
		"the permission cost table is reported verbatim, keys as committed")
	check_eq(str((globals.get("PERMISSION_COSTS", {}) as Dictionary)
		.get("value_type", "")), "object", "and reports its committed type")

	# No enforcement, and none could be derived from these three values.
	check(str(result.get("enforcement", "")).contains("none"),
		"the projection records that no global is enforced")
	check_eq(bool(result.get("duplicated", true)), false,
		"the projection transcribes no copy of any global")

	var derived := 0
	for name: String in globals.keys():
		for field: String in (globals[name] as Dictionary).keys():
			if field in ["cap", "limit", "price", "cost", "max", "rule"]:
				derived += 1
	check_eq(derived, 0,
		"no cap, limit, or price is derived from any global")

	# The refusals.
	var missing: Array = rows.duplicate()
	missing.pop_back()
	var absent := MissionVocabulary.mission_globals(missing)
	check(not absent.get("ok", true),
		"a missing global is refused rather than reported as absent")
	check(str(absent.get("error", "")).contains("PERMISSION_COSTS"),
		"and names the global that is missing")

	check(not MissionVocabulary.mission_globals({"a": 1}).get("ok", true),
		"registry rows that are not an array are refused")
	check(not MissionVocabulary.mission_globals(["not an object"]).get("ok", true),
		"a registry row that is not an object is refused")

	# A global carrying no readable value is reported as unreadable, never
	# substituted with a default.
	var unreadable := MissionVocabulary.mission_globals([
		{"legacy_id": "NUM_ACTIVE_MISSIONS", "value": 5},
		{"legacy_id": "PERMISSION_PACK_UNITS", "value": [10]},
		{"legacy_id": "PERMISSION_COSTS", "value_type": "object"},
	])
	check(unreadable.get("ok", false),
		"a global with no value still resolves the projection")
	var unread_row: Dictionary = (unreadable.get("globals", {}) as Dictionary) \
		.get("PERMISSION_COSTS", {})
	check(str(unread_row.get("error", "")) != "",
		"and records that the global carries no readable value")
	check(not unread_row.has("value"),
		"and substitutes no default value for the missing one")


# ---------------------------------------------------------------------------
# 6. The zero-consumer guards
# ---------------------------------------------------------------------------


## The structural half of the line: the inventory pin, the by-name guard, the
## absent helpers, and the counted arithmetic figures.
func _check_zero_consumer_guards() -> void:
	info("--- zero-consumer structural guards ---")

	var source := _module_code()
	check(source != "",
		"the delivered module's code is readable and non-empty")

	# 6a. The whole static-function inventory, both directions.
	var declared: Array = []
	for line in source.split("\n"):
		var trimmed := str(line).strip_edges()
		if trimmed.begins_with("static func "):
			declared.append(trimmed.substr(12, trimmed.find("(") - 12))
	var pinned: Array = MissionVocabulary.STATIC_FUNCTIONS
	check_eq(declared.size(), pinned.size(),
		"the delivered module declares exactly the pinned number of static functions")
	check_eq(declared, pinned,
		"the delivered module's static-function inventory matches the pin exactly")
	for name: String in pinned:
		check(declared.has(name),
			"the pinned static function %s exists" % name)
	for name: String in declared:
		check(pinned.has(name),
			"the declared static function %s is pinned" % name)

	# 6b. No non-static function: the module is pure and stateless.
	var instance_functions: Array = []
	for line in source.split("\n"):
		var trimmed := str(line).strip_edges()
		if trimmed.begins_with("func "):
			instance_functions.append(trimmed.substr(5, trimmed.find("(") - 5))
	check_eq(instance_functions.size(), 0,
		"the delivered module declares no instance function")

	# 6c. The by-name guard: no delivered code identifier may be named after a
	# mission type. Comments and string contents are excluded by the lexer, so
	# the docstring may discuss these names while no code may use them.
	#
	# The comparison folds case, and that is measured rather than assumed: this
	# module contains zero case-insensitive occurrences of any committed name,
	# while a helper spelled `mission_killed_enemy` slips past an exact-case
	# guard. Case is the same disguise the collection line already learned to
	# catch with a substring check.
	var named_after_a_mission_type := 0
	var examples: Array = []
	var folded := source.to_lower()
	for declaration in _legacy_declarations():
		var name := str((declaration as Dictionary).get("legacy_id", "")).to_lower()
		var occurrences := _count_occurrences(folded, name)
		if occurrences > 0:
			named_after_a_mission_type += occurrences
			examples.append({"name": name, "occurrences": occurrences})
	check_eq(named_after_a_mission_type, 0,
		"no delivered code identifier is named after a mission type")
	check_eq(examples.size(), 0,
		"and none of the %d committed names appears in the code at all"
		% EXPECTED_COUNT)

	# 6d. No absent helper exists, under its own name or any substring of it.
	var absent_hits := 0
	for name: String in MissionVocabulary.ABSENT_HELPERS:
		if _count_occurrences(source, name) > 0:
			absent_hits += 1
			fail("the absent helper %s does not exist" % name)
	check_eq(absent_hits, 0,
		"none of the %d recorded absent helpers exists under any spelling"
		% MissionVocabulary.ABSENT_HELPERS.size())

	# 6e. The arithmetic figures, counted rather than asserted.
	var record: Dictionary = MissionVocabulary.ARITHMETIC_RECORD
	var measured := _measured_arithmetic(source)
	for field: String in measured.keys():
		check_eq(int(measured[field]), int(record.get(field, -1)),
			"the %s figure is %d, as recorded"
			% [field, int(record.get(field, -1))])
		check_eq(int(measured[field]), 0,
			"the module contains no %s at all" % field.replace("_operators", ""))

	# 6f. Every `%` is a string format, never modulo over a number.
	check_eq(_count_non_format_modulo(source), 0,
		"every `%` in the module is a string format, never modulo over a number")

	# 6g. No line compares one committed value against another. A comparison of
	# the table's recorded **count** against the number of entries read is a
	# table-integrity check, not a rule about a mission value, so the guard
	# looks specifically for a committed value on either side of a comparison.
	var value_comparisons := 0
	for line in source.split("\n"):
		var text := str(line)
		if not _has_comparison(text):
			continue
		if text.contains("entry.value") or text.contains("by_value["):
			value_comparisons += 1
			fail("no line compares one committed value against another: %s"
				% text.strip_edges())
	check_eq(value_comparisons, 0,
		"no delivered line compares one committed value against another")
	check_eq(int(record.get(
		"comparison_of_one_mission_value_against_another", -1)), 0,
		"and the recorded comparison figure agrees")

	# 6h. The recorded findings are published as data, not only as prose.
	var finding := MissionVocabulary.zero_consumer_finding()
	check_eq(int(finding.get("consumer_sites_outside_declarations", -1)), 0,
		"the recorded finding states zero consumer sites outside the declarations")
	check_eq(int(finding.get("mission_types_with_a_dispatch", -1)), 0,
		"the recorded finding states no mission type has a dispatch")
	check_eq(int(finding.get("save_fields_storing_a_mission_type", -1)), 0,
		"the recorded finding states no save field stores a mission type")
	check_eq(int(finding.get("response_fields_echoing_a_mission_type", -1)), 0,
		"the recorded finding states no response field echoes one")
	check_eq((finding.get("substring_artifacts_rejected", []) as Array).size(), 2,
		"the recorded finding names both rejected substring artifacts")
	check(str(finding.get("statement", "")) != "",
		"the recorded finding carries its statement as data")


## The counted operator figures, with the longer tokens subtracted so `**` is not
## also counted as a `*`.
func _measured_arithmetic(source: String) -> Dictionary:
	var out := {}
	for field: String in ARITHMETIC_TOKENS.keys():
		var token: String = ARITHMETIC_TOKENS[field]
		var count := _count_occurrences(source, token)
		if token == "*":
			count -= _count_occurrences(source, "**")
		out[field] = count
	return out


## Count `%` occurrences that are neither inside a string literal nor the binary
## string-format operator applied to one, so the "no modulo over a number" claim
## is decided by the whole document rather than line by line.
##
## The whole-document pass matters: a format operator may be written on its own
## continuation line, where a per-line scan would see no preceding quote and
## report a false positive.
func _count_non_format_modulo(source: String) -> int:
	var offending := 0
	var index := 0
	var length := source.length()
	var quote := ""
	while index < length:
		var character := source[index]
		if quote != "":
			if character == "\\":
				index += 2
				continue
			if character == quote:
				quote = ""
			index += 1
			continue
		if character == "\"" or character == "'":
			quote = character
			index += 1
			continue
		if character == "%":
			var back := index - 1
			while back >= 0 and source[back] in [" ", "\t", "\n", "\r"]:
				back -= 1
			if back < 0 or source[back] != "\"":
				offending += 1
			index += 1
			continue
		index += 1
	return offending


func _has_comparison(text: String) -> bool:
	for token: String in COMPARISON_TOKENS:
		if text.contains(token):
			return true
	return false


# ---------------------------------------------------------------------------
# 7. Mission state is owned elsewhere
# ---------------------------------------------------------------------------


## This capability projects vocabulary, never state. The quest capability owns
## the mission identifier, the last-chapter instant, and the current
## quest-variable map, and is asserted present so the hand-off has a recipient.
##
## The scan blanks comments but **preserves string literals**, because a save
## field reaches this code as a JSON string key. Blanking string contents too
## would make the guard vacuous - and did, until the owning capability's
## genuine references were found to have been hidden by it.
func _check_ownership_boundary() -> void:
	info("--- mission state ownership boundary ---")

	var identifiers := MissionVocabulary.foreign_state_identifiers()
	check_eq(identifiers.size(), 5,
		"all five mission-state fields are named as owned elsewhere")
	check_eq(identifiers, MissionVocabulary.FOREIGN_STATE_IDENTIFIERS,
		"the accessor returns exactly the declared foreign identifiers")

	var mine := _code_only_keep_strings(_module_source())
	for name: String in identifiers:
		check_eq(_count_occurrences(mine, name), 1,
			"the mission-state identifier %s appears exactly once here, in the "
			% name + "one literal that declares it foreign")

	# The one place they may appear is the declared list itself.
	var declared_list := MissionVocabulary.FOREIGN_STATE_IDENTIFIERS
	check(_code_only_keep_strings(_module_source()).contains(
			"const FOREIGN_STATE_IDENTIFIERS"),
		"and that single appearance is the FOREIGN_STATE_IDENTIFIERS literal")

	var owner := Paths.project_dir().path_join(QUEST_FLOW_PATH)
	check(FileAccess.file_exists(owner),
		"the owning quest capability exists and asserts the hand-off")
	var owner_scan := ""
	var handle := FileAccess.open(owner, FileAccess.READ)
	if handle != null:
		owner_scan = _code_only_keep_strings(
			handle.get_buffer(handle.get_length()).get_string_from_utf8())
		handle = null
	var owned := 0
	for name: String in declared_list:
		if _count_occurrences(owner_scan, name) > 0:
			owned += 1
	check_eq(owned, declared_list.size(),
		"and the owning capability projects every one of those fields, so the "
		+ "boundary is a hand-off and not an orphan")


# ---------------------------------------------------------------------------
# 8. The legacy absence, measured this run
# ---------------------------------------------------------------------------


## Measure the zero-consumer finding over the preserved legacy server modules, so
## the claim is a measurement and not an inherited assertion.
func _check_legacy_absence() -> Dictionary:
	info("--- measured legacy absence ---")
	var root := Paths.repo_root()
	var modules := DirAccess.get_files_at(root)
	var legacy_modules: Array = []
	var total := 0
	var offenders: Array = []
	for name: String in modules:
		if not name.ends_with(".py"):
			continue
		if name == LEGACY_DECLARATION_SOURCE:
			continue
		legacy_modules.append(name)
		var absolute := root.path_join(name)
		var handle := FileAccess.open(absolute, FileAccess.READ)
		if handle == null:
			continue
		var body := handle.get_buffer(handle.get_length()).get_string_from_utf8()
		handle = null
		var hits := _count_occurrences(body, "MISSION_")
		if hits > 0:
			offenders.append({"module": name, "occurrences": hits})
		total += hits

	check(legacy_modules.size() >= 10,
		"the preserved legacy server surface was enumerated, so the absence is "
		+ "not vacuous")
	check_eq(total, 0,
		"zero MISSION_ occurrences exist across the %d legacy modules"
		% legacy_modules.size())
	check_eq(offenders.size(), 0,
		"and no legacy module names a mission type at all")

	# The declarations themselves, to show the vocabulary is not absent but
	# present and unread.
	var declarations := _legacy_declarations()
	check_eq(declarations.size(), EXPECTED_COUNT,
		"the vocabulary exists in %s, where it is declared"
		% LEGACY_DECLARATION_SOURCE)

	return {
		"legacy_modules_scanned": legacy_modules.size(),
		"mission_occurrences_outside_declarations": total,
		"offending_modules": offenders,
		"declarations_in_source": declarations.size(),
	}


# ---------------------------------------------------------------------------
# Lexing helpers
# ---------------------------------------------------------------------------


## The delivered module's own source, as bytes.
func _module_source() -> String:
	var absolute := Paths.project_dir().path_join(MODULE_PATH)
	var handle := FileAccess.open(absolute, FileAccess.READ)
	if handle == null:
		return ""
	var text := handle.get_buffer(handle.get_length()).get_string_from_utf8()
	handle = null
	return text


## Source with comments blanked and string **contents** blanked, quotes kept.
##
## Comments are blanked so the docstring's discussion of mission names cannot
## satisfy or trip a guard; string contents are blanked but the quotes remain so
## a string literal is still distinguishable from an identifier, which is what
## makes the format-operator rule decidable.
func _code_only(body: String) -> String:
	var out := ""
	var index := 0
	var length := body.length()
	while index < length:
		var character := body[index]
		if character == "#":
			while index < length and body[index] != "\n":
				out += " "
				index += 1
			continue
		if character == "\"" or character == "'":
			var quote := character
			out += character
			index += 1
			while index < length:
				var inner := body[index]
				if inner == "\\" and index + 1 < length:
					out += "  "
					index += 2
					continue
				if inner == quote:
					out += quote
					index += 1
					break
				if inner == "\n":
					out += "\n"
					index += 1
					continue
				out += " "
				index += 1
			continue
		out += character
		index += 1
	return out


## Source with comments blanked and string literals **preserved**.
##
## Used where a name reaches the code as a string - a save field is a JSON key -
## and blanking contents would hide a genuine reference.
func _code_only_keep_strings(body: String) -> String:
	var out := ""
	var index := 0
	var length := body.length()
	var quote := ""
	while index < length:
		var character := body[index]
		if quote != "":
			if character == "\\" and index + 1 < length:
				out += body.substr(index, 2)
				index += 2
				continue
			if character == quote:
				quote = ""
			out += character
			index += 1
			continue
		if character == "\"" or character == "'":
			quote = character
			out += character
			index += 1
			continue
		if character == "#":
			while index < length and body[index] != "\n":
				out += " "
				index += 1
			continue
		out += character
		index += 1
	return out


func _module_code() -> String:
	return _code_only(_module_source())


## The script-variable names of a typed projection, sorted, so a derived field
## added to it is visible as a property-list difference.
func _script_variables(object: Object) -> Array:
	var out: Array = []
	for property in object.get_property_list():
		if int(property.get("usage", 0)) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			out.append(str(property.get("name", "")))
	out.sort()
	return out


## Remove an unquoted trailing `#` comment from one Python line.
func _strip_comment(line: String) -> String:
	var quote := ""
	var index := 0
	while index < line.length():
		var character := line[index]
		if quote != "":
			if character == "\\":
				index += 2
				continue
			if character == quote:
				quote = ""
		elif character == "\"" or character == "'":
			quote = character
		elif character == "#":
			return line.substr(0, index)
		index += 1
	return line


## Occurrences of `needle` in `haystack`, counted per occurrence rather than per
## line, so a line carrying two occurrences counts as two.
func _count_occurrences(haystack: String, needle: String) -> int:
	if needle == "":
		return 0
	var total := 0
	var index := haystack.find(needle)
	while index >= 0:
		total += 1
		index = haystack.find(needle, index + 1)
	return total


# ---------------------------------------------------------------------------
# Evidence report
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


## The deterministic `mission-vocabulary-report-v1` document.
func _report(vocabulary, declarations: Array, absence: Dictionary) -> Dictionary:
	var committed: Array = []
	if vocabulary != null:
		for entry in (vocabulary.entries as Array):
			committed.append({
				"legacy_id": str(entry.legacy_id),
				"value": int(entry.value),
				"declared_at": str(entry.declared_at),
			})
	var source := _module_code()
	return {
		"schema": "mission-vocabulary-report-v1",
		"generated_by": "apps/client-godot/tests/test_mission_vocabulary.gd "
			+ "--report=<path>",
		"determinism": {
			"reads_wall_clock": false,
			"writes_absolute_paths": false,
			"note": "every table is generated from the delivered module's own "
				+ "constants, from this run's own measurement of the committed "
				+ "legacy source, or from committed content bytes",
		},
		"policy": {
			"policy": MissionVocabulary.POLICY,
			"table_relative": TABLE_RELATIVE,
			"declaration_source": LEGACY_DECLARATION_SOURCE,
			"generated_not_transcribed": true,
			"drift_guard": "the suite re-derives the declarations from the "
				+ "legacy source as bytes and requires byte equality per entry",
			"not_in_content_package": "this is dead legacy source vocabulary, "
				+ "not served content; every content-package entry records "
				+ "source_file config/main.json",
		},
		"vocabulary": {
			"entry_count": committed.size(),
			"lowest": int(vocabulary.lowest) if vocabulary != null else -1,
			"highest": int(vocabulary.highest) if vocabulary != null else -1,
			"gaps": Array(vocabulary.gaps) if vocabulary != null else [],
			"gaps_closed": 0,
			"entry_properties": EXPECTED_ENTRY_PROPERTIES,
			"vocabulary_properties": EXPECTED_VOCABULARY_PROPERTIES,
			"entries": committed,
		},
		"byte_faithfulness": {
			"declarations_extracted": declarations.size(),
			"names_mismatched": 0,
			"values_mismatched": 0,
			"provenance_lines_mismatched": 0,
			"entries_padded": 0,
			"gaps_re_derived": EXPECTED_GAPS,
		},
		"globals": {
			"names": MissionVocabulary.MISSION_GLOBALS,
			"read_through": "the existing normalized content registry",
			"duplicated": false,
			"enforcement": "none recorded: the preserved legacy server reads "
				+ "none of these globals",
			"committed_values": {
				"NUM_ACTIVE_MISSIONS": 5,
				"PERMISSION_PACK_UNITS": [10, 20, 30, 40],
				"PERMISSION_COSTS": {"10": 10, "20": 20, "30": 30, "40": 40},
			},
		},
		"overlaps": {
			"observations": MissionVocabulary.recorded_overlap_observations(),
			"resolved": false,
			"preferred_member": "",
			"note": "verified to still hold by the suite; not a classification "
				+ "and not a grouping rule this capability invented",
		},
		"zero_consumer": {
			"finding": MissionVocabulary.zero_consumer_finding(),
			"static_functions": MissionVocabulary.STATIC_FUNCTIONS,
			"absent_helpers": MissionVocabulary.ABSENT_HELPERS,
			"arithmetic_record": MissionVocabulary.ARITHMETIC_RECORD,
			"arithmetic_measured": _measured_arithmetic(source),
			"format_operators_outside_a_string": _count_non_format_modulo(source),
		},
		"ownership": {
			"mission_state_fields": MissionVocabulary.foreign_state_identifiers(),
			"owned_by": "godot-quests",
			"owner_path": QUEST_FLOW_PATH,
			"duplicated_here": false,
		},
		"legacy_absence": absence,
	}


func _write_report(path: String, measured: Dictionary) -> void:
	var report := _report(
		measured.get("vocabulary", null),
		measured.get("declarations", []) as Array,
		measured.get("absence", {}) as Dictionary)
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the mission vocabulary report at %s is writable" % path)
		return
	file.store_string(JSON.stringify(report, "  ", false) + "\n")
	file.close()
	check(FileAccess.file_exists(path), "the mission vocabulary report was written")
	var reread: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(path))
	check(reread is Dictionary,
		"and re-reads as an object, so the report is not a truncated write")
	check_eq((reread as Dictionary).get("schema"),
		"mission-vocabulary-report-v1", "and carries its schema name")