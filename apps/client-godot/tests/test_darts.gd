extends "res://tests/test_base.gd"
## Darts and premium suite (OpenSpec `godot-darts`, spec:
## "darts-and-premium").
##
## ## Hermetic by construction
##
## No service, no network, no GameApi. Every value either comes from the committed
## corpus on disk, from the committed normalized content package through the
## existing `ContentRegistry` autoload, or from a **crafted** input that is
## labelled as such. Nothing is executed against the legacy server, so **no
## parity is claimed anywhere in this suite** and no executed-legacy fixture
## exists (requirement 12).
##
## ## Everything measured is re-derived, not inherited
##
## The corpus denominator and every per-value multiplicity are recomputed from
## `tests/saves` + `villages` on **every run** and compared against the pinned
## figures in `darts_state.gd`. A pinned expectation the suite never re-measures
## is a comment; a pinned expectation that is re-measured is a guard.
##
## ## The denominator is 33, and that is a CORRECTION
##
## `docs/legacy-m11-darts.md` §5 originally reported 231 corpus documents. Two
## hundred of those were generated `tests/fixtures/**` `before.json`/`after.json`
## files -- derived copies of canonical saves, each recording both sides of one
## transaction -- so the denominator was inflated roughly sevenfold. The canonical
## corpus is 33 documents. See that document's §0b C3. `_check_corpus` re-derives
## 33 and would fail against the old figure.
##
## ## Two guards that are proven rather than trusted
##
## `_check_absence` pins the whole static-function inventory of all three modules
## and applies a case-folded SUBSTRING test against `DartsState.ABSENT_HELPERS`.
## The pin is the gate and the name test is the belt, because an exact-name check
## was measured in this project to miss a suffixed helper wearing a reserved name.
##
## Every injection result recorded in the evidence report was produced by applying
## the probe to a byte-identical copy of the real module, running this suite, and
## restoring. The suite cannot rewrite the module it is judging, so the
## orchestrator performs the injections and the results are recorded here as
## `_injection_record()`.

## `Paths` is inherited from `test_base.gd`, which preloads
## `res://scripts/package_paths.gd`; re-declaring it here is a parse error.

const DartsState := preload("res://scripts/darts/darts_state.gd")
const PremiumPurchase := preload("res://scripts/darts/premium_purchase.gd")
const WeekReset := preload("res://scripts/darts/week_reset.gd")
const DartsTransitions := preload("res://scripts/darts/darts_transitions.gd")

const DEFAULT_REPORT_PATH := "evidence/darts/report.json"

## The canonical corpus roots, matching `DartsState.EXPECTED_CORPUS`.
const CORPUS_ROOTS := ["tests/saves", "villages"]

## The seven fields that carry the six darts fields plus the two handed ones.
## `timeStampEndPremium` appears once and `crossPromotionsFinished` once.
const ALL_FIELD_NAMES := [
	"dartsRandomSeed", "dartsBalloonsShot", "dartsGotExtra", "dartsHasFree",
	"timeStampDartsReset", "timeStampDartsNewFree",
	"timeStampEndPremium", "crossPromotionsFinished",
]

const DARTS_ONLY_NAMES := [
	"dartsRandomSeed", "dartsBalloonsShot", "dartsGotExtra", "dartsHasFree",
	"timeStampDartsReset", "timeStampDartsNewFree",
]

## The committed darts schedule's id range, from the normalized package.
const SCHEDULE_ID_MIN := 1
const SCHEDULE_ID_MAX := 27

## The corpus census, filled in by `_check_corpus`.
var corpus := {}

## The projection measurement, filled in by `_check_projection`.
var projection := {}

## The premium measurement, filled in by `_check_premium`.
var premium := {}

## The transitions measurement, filled in by `_check_transitions`.
var transitions := {}


func run_scenario() -> void:
	_check_projection()
	_check_corpus()
	_check_premium()
	_check_transitions()
	_check_week_reset()
	_check_boundary()
	_check_absence()
	if _has_report_argument():
		_write_report()


func _has_report_argument() -> bool:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report"):
			return true
	return false


# ---------------------------------------------------------------------------
# Requirement 1 & 2 -- the typed read-only projection
# ---------------------------------------------------------------------------

func _check_projection() -> void:
	var names: Array = DartsState.field_names()
	check_eq(names, ALL_FIELD_NAMES,
		"the projection delivers the six darts fields plus the two handed ones, "
			+ "in the investigation's order")
	check_eq(names.size(), 8,
		"the projection delivers exactly EIGHT fields")
	check_eq(DartsState.darts_field_names(), DARTS_ONLY_NAMES,
		"the darts-field accessor delivers exactly the SIX darts state fields")
	check_eq(DartsState.darts_field_names().size(), 6,
		"SIX darts fields are delivered, and the two handed fields are not "
			+ "among them")
	check_eq(DartsState.field_names().size(),
		DartsState.darts_field_names().size() + 2,
		"the handed fields are exactly the difference between the full set and "
			+ "the darts set")

	# The handed fields must be found and distinguishable from unmeasured names.
	check(DartsState.field_record("timeStampEndPremium") != null,
		"the handed premium field is projected")
	check(DartsState.field_record("crossPromotionsFinished") != null,
		"the handed cross-promotion field is projected")
	check(DartsState.field_record("notARealField") == null,
		"an unmeasured field name yields null rather than a synthesized record")
	check_eq(DartsState.distinct_values_of("notARealField"), -1,
		"an unmeasured field reports -1 distinct values rather than a guess")
	check_eq(DartsState.recorded_values_of("notARealField"), {},
		"an unmeasured field yields an empty distribution rather than a guess")

	# Client-sent classification, which the whole refusal case rests on.
	for name: String in ["dartsRandomSeed", "dartsBalloonsShot", "dartsGotExtra"]:
		check(DartsState.is_client_sent(name),
			("the field `%s` is recorded as client-sent, which is the recorded "
				+ "branch's behaviour") % name)
	for name: String in ["dartsHasFree", "timeStampDartsReset",
			"timeStampDartsNewFree", "timeStampEndPremium"]:
		check(not DartsState.is_client_sent(name),
			("the field `%s` is recorded as NOT client-sent") % name)
	check(not DartsState.is_client_sent("notARealField"),
		"an unmeasured field is not classified as client-sent")

	# Every record carries a note and cites provenance, so the projection cannot
	# be a bare name list.
	for name: String in names:
		var record: Variant = DartsState.field_record(name)
		check(record is Dictionary,
			("the field `%s` has a Dictionary record") % name)
		if not (record is Dictionary):
			continue
		var entry: Dictionary = record
		check(str(entry.get("store", "")) == "privateState",
			("the field `%s` records its measured storage location") % name)
		check(str(entry.get("note", "")).length() > 0,
			("the field `%s` records WHY its classification is what it is")
				% name)
		var distribution: Dictionary = entry.get("recorded_values", {})
		var total: int = 0
		for value: Variant in distribution.values():
			total += int(value)
		check_eq(total, DartsState.EXPECTED_CORPUS["documents"],
			("the pinned distribution of `%s` sums to the corpus denominator, so "
				+ "no document is unaccounted for") % name)
		check_eq(distribution.size(), int(entry.get("distinct", -1)),
			("the pinned distribution of `%s` has exactly the recorded number of "
				+ "distinct values") % name)

	# The projection over a real document, and absent-field handling.
	projection["absent_document"] = DartsState.project({}).absent_names()
	projection["empty_document"] = DartsState.project({}).present_names()
	_check_absent_semantics()
	_check_out_of_schedule_corpus_facts()


## Absence must be reported as absence, never defaulted to a recorded value.
##
## All 33 canonical documents carry all eight fields, so a missing key means a
## document shape never observed. Folding "absent" into the recorded uniform
## value would hide exactly that case, so `present()` is the discriminator.
func _check_absent_semantics() -> void:
	var empty := DartsState.project({})
	check_eq(empty.present_names(), [],
		"an empty document projects no present fields")
	check_eq(empty.absent_names().size(), 8,
		"an empty document reports all EIGHT fields absent")
	for name: String in ALL_FIELD_NAMES:
		check(not empty.present(name),
			("an empty document reports `%s` absent") % name)
		check(empty.value(name) == null,
			("an empty document reports a null value for `%s` rather than a "
				+ "default") % name)
	check(not empty.has_recorded_shots(),
		"an empty document reports no recorded shots")

	# A present-but-uniform document must be distinguishable from an absent one:
	# `dartsGotExtra: false` present, versus the field missing entirely.
	var uniform := DartsState.project({"privateState": {
		"dartsGotExtra": false, "dartsBalloonsShot": [],
	}})
	check(uniform.present("dartsGotExtra"),
		"a recorded `false` is PRESENT, and is therefore distinct from absent")
	check(uniform.value("dartsGotExtra") == false,
		"a recorded `false` reads back as false, not as null")
	check(not uniform.present("timeStampEndPremium"),
		"a field the document omits stays absent even beside present fields")

	# Non-dictionary documents fail closed.
	for bogus: Variant in [null, 5, "text", [1, 2]]:
		var projection_v: Variant = DartsState.project(bogus)
		check_eq(projection_v.present_names(), [],
			("a non-dictionary document (%s) projects nothing rather than "
				+ "crashing or guessing") % str(bogus))


## The corpus facts that justify refusing a schedule-membership test.
##
## `villages/Nerri.json` records shot `[0]`, and `0` is NOT among the committed
## ids 1..27. That single document is the evidence the missing membership test is
## not merely unimplemented but demonstrably NOT enforced -- so adding one would
## contradict the corpus rather than reproduce it.
func _check_out_of_schedule_corpus_facts() -> void:
	var entries: Array = DartsState.OUT_OF_SCHEDULE_SHOTS
	check_eq(entries.size(), 3,
		"exactly THREE canonical documents carry a non-empty shot list")
	var outside_total: int = 0
	var named: Array = []
	for entry: Dictionary in entries:
		var document: String = str(entry.get("document", ""))
		named.append(document)
		var shots: Variant = entry.get("shots", null)
		check(shots is Array and not (shots as Array).is_empty(),
			("the out-of-schedule entry `%s` records a non-empty shot list")
				% document)
		for shot: Variant in entry.get("outside_schedule", []):
			var index: int = int(shot)
			check(index < SCHEDULE_ID_MIN or index > SCHEDULE_ID_MAX,
				("the recorded shot %d in `%s` is genuinely outside the committed "
					+ "schedule range %d..%d")
					% [index, document, SCHEDULE_ID_MIN, SCHEDULE_ID_MAX])
			outside_total += 1
	check_eq(outside_total, 1,
		"exactly ONE recorded shot lies outside the committed schedule range")
	check(named.has("villages/Nerri.json"),
		"the out-of-schedule shot is attributed to villages/Nerri.json by name")

	# Every document that DOES lie inside the range, so the range itself is real.
	var inside: int = 0
	for entry: Dictionary in entries:
		for shot: Variant in (entry.get("shots", []) as Array):
			var index: int = int(shot)
			if index >= SCHEDULE_ID_MIN and index <= SCHEDULE_ID_MAX:
				inside += 1
	check_eq(inside, 3,
		"THREE recorded shots DO lie inside the committed schedule range, so the "
			+ "range is a real constraint the corpus partly respects")

	check_eq(DartsState.SCHEDULE_RANGE["first"], SCHEDULE_ID_MIN,
		"the module's recorded schedule range starts at the committed first id")
	check_eq(DartsState.SCHEDULE_RANGE["last"], SCHEDULE_ID_MAX,
		"the module's recorded schedule range ends at the committed last id")
	check_eq(str(DartsState.SCHEDULE_RANGE["owner"]),
		"darts-schedule-normalization",
		"the committed darts schedule is owned by its normalization capability, "
			+ "so this capability reads it and never re-owns it")


# ---------------------------------------------------------------------------
# Requirement 12 -- the named corpus, re-derived every run
# ---------------------------------------------------------------------------

func _check_corpus() -> void:
	var repo: String = Paths.repo_root()
	var values := {}
	var tally := {"documents": 0}
	for root_name: String in CORPUS_ROOTS:
		_walk_json(repo.path_join(root_name), [], values, tally)
	var documents: int = int(tally["documents"])

	corpus["documents"] = documents
	corpus["roots"] = CORPUS_ROOTS.size()
	corpus["definition"] = DartsState.EXPECTED_CORPUS["carrying_rule"]

	check_eq(CORPUS_ROOTS.size(), 2,
		"the census walks the two recorded roots, tests/saves and villages")
	check_eq(documents, 33,
		"the corpus walk RE-DERIVES the corrected THIRTY-THREE carrying "
			+ "documents (the investigation's 231 counted generated fixtures too)")
	check_eq(documents, int(DartsState.EXPECTED_CORPUS["documents"]),
		"the re-derived denominator equals the module's pinned denominator")

	# Every document must actually carry a map, which is the carrying rule.
	var maps_total: int = 0
	var village_total: int = 0
	for root_name: String in CORPUS_ROOTS:
		var base: String = repo.path_join(root_name)
		var sub := {"documents": 0, "maps": 0, "village": 0}
		_walk_json(base, [], {}, sub)
		maps_total += int(sub["maps"])
		village_total += int(sub["village"])
	corpus["maps_observed"] = maps_total
	corpus["village_documents"] = village_total
	check_eq(maps_total, documents,
		"every counted document carries at least one map, so the carrying rule "
			+ "is what selected them")

	# Every pinned distribution is re-derived and compared, in BOTH directions.
	var mismatches: Array = []
	for field_name: String in ALL_FIELD_NAMES:
		var observed: Dictionary = values.get(field_name, {})
		var pinned: Dictionary = DartsState.recorded_values_of(field_name)
		if not _distributions_agree(observed, pinned):
			mismatches.append(field_name)
			continue
		check_eq(observed.size(), DartsState.distinct_values_of(field_name),
			("the re-derived distinct-value count for `%s` matches the pinned "
				+ "count") % field_name)
		var pinned_total: int = 0
		for value: Variant in pinned.values():
			pinned_total += int(value)
		var observed_total: int = 0
		for value: Variant in observed.values():
			observed_total += int(value)
		check_eq(observed_total, pinned_total,
			("the re-derived multiplicity total for `%s` equals the pinned "
				+ "total") % field_name)
	check_eq(mismatches, [],
		"every re-derived field distribution EQUALS the pinned distribution, so "
			+ "no multiplicity is inherited on trust")

	# The two headline corpus findings.
	var extra: Dictionary = values.get("dartsGotExtra", {})
	check_eq(extra.size(), 1,
		"`dartsGotExtra` holds exactly ONE distinct value in the whole corpus")
	check_eq(extra.keys()[0], "false",
		"`dartsGotExtra` is `false` in EVERY canonical document: the corpus "
			+ "records no won shot at all, so the client-dictated outcome refusal "
			+ "has NO corpus evidence in either direction")
	check_eq(extra.values()[0], documents,
		"`dartsGotExtra` is false in ALL 33 documents, not merely most")

	# There is no premium flag anywhere.
	var flag_documents: int = 0
	for root_name: String in CORPUS_ROOTS:
		var sub := {"premium_flag": 0}
		_walk_json(repo.path_join(root_name), [], {}, sub)
		flag_documents += int(sub["premium_flag"])
	corpus["premium_flag_documents"] = flag_documents
	check_eq(flag_documents, 0,
		"the key `premiumAccount` appears in ZERO canonical documents: there is "
			+ "no premium flag, only an instant")
	check_eq(int(DartsState.PREMIUM_FLAG_ABSENT["documents_carrying"]), 0,
		"the module records the absent premium flag as carried by no document")
	check(not bool(DartsState.PREMIUM_FLAG_ABSENT["boolean_derived"]),
		"no premium boolean is derived from the instant, because deriving one "
			+ "would invent a state the save does not carry")

	# The one live premium instant, named rather than only counted.
	var premium_values: Dictionary = values.get("timeStampEndPremium", {})
	check_eq(premium_values.size(), 2,
		"`timeStampEndPremium` holds exactly TWO distinct values in the corpus")
	check_eq(int(premium_values.get("1682945878", 0)), 1,
		"exactly ONE canonical document records a live premium instant "
			+ "(the investigation's corrected figure of 47 counted fixtures)")
	var live: Dictionary = DartsState.LIVE_PREMIUM_DOCUMENT
	check_eq(str(live.get("document", "")), "villages/Neutral.json",
		"the single live-premium document is NAMED")
	check_eq(int(live.get("instant", 0)), 1682945878,
		"the named live premium instant is the recorded one")
	check(bool(live.get("elapsed", false)),
		"the named instant has PASSED, so it is not a live entitlement")
	check(not bool(live.get("extend_arm_reachable", true)),
		"the extend arm is therefore UNREACHABLE in the corpus, so any coverage "
			+ "of it is crafted input and never corpus evidence")

	# The fresh-player document's inability, recorded as a reason (requirement 12).
	_check_fresh_player_limit(repo)


## The canonical document the legacy oracle would drive, and why it cannot
## exercise this surface.
##
## This is the concrete reason **no executed-legacy fixture is claimed**: every
## darts field sits at its initial value and `timeStampEndPremium` is 0, so the
## shoot arm, the free arm and BOTH premium arms are unreachable over it. This is
## stronger than the sibling refusal lines' "no corpus document at all" -- a real
## document exists, it simply cannot drive this surface.
func _check_fresh_player_limit(repo: String) -> void:
	var limit: Dictionary = DartsState.FRESH_PLAYER_LIMIT
	var path: String = repo.path_join(str(limit["document"]))
	check(FileAccess.file_exists(path),
		"the recorded fresh-player document exists at its recorded path")
	if not FileAccess.file_exists(path):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	check(parsed is Dictionary,
		"the fresh-player document parses as a JSON object")
	if not (parsed is Dictionary):
		return
	var projection_v: Variant = DartsState.project(parsed)
	for field_name: String in ALL_FIELD_NAMES:
		var recorded: Variant = limit.get(field_name, "ABSENT")
		check(projection_v.present(field_name),
			("the fresh-player document carries `%s`, so the refusal to claim a "
				+ "fixture is not explained by an absent key") % field_name)
		check(_same_value(projection_v.value(field_name), recorded),
			("the fresh-player document records `%s` at its recorded initial "
				+ "value (%s)") % [field_name, str(recorded)])

	# The three consequences, each a named reachability flag.
	check(not bool(limit["shoot_arm_reachable"]),
		"the shoot arm is UNREACHABLE over the fresh-player corpus")
	check(not bool(limit["free_arm_reachable"]),
		"the free arm is UNREACHABLE over the fresh-player corpus")
	check(not bool(limit["premium_arm_reachable"]),
		"both premium arms are UNREACHABLE over the fresh-player corpus")
	check_eq(str(limit["coverage_kind"]), "crafted input only",
		"coverage of those arms over this document is labelled CRAFTED INPUT, "
			+ "never corpus evidence")

	# The initial values must be the inert ones, or the reason would be hollow.
	var shots: Variant = projection_v.value("dartsBalloonsShot")
	check(shots is Array and (shots as Array).is_empty(),
		"the fresh-player shot list is EMPTY, so no shot has ever been taken")
	check_eq(int(projection_v.value("dartsRandomSeed")), 0,
		"the fresh-player seed is 0, so darts was never reset there")
	check_eq(int(projection_v.value("timeStampDartsReset")), 0,
		"the fresh-player reset instant is 0, so darts was never reset there")


## Walk `*.json` under `base`, tallying per-field value distributions.
##
## `premium_flag` counts documents carrying the absent `premiumAccount` key.
## `village` counts documents whose path starts with `villages/`. `maps` counts
## documents carrying at least one map. Every document must begin with `{`: a
## document that does not is refused BEFORE the parser is invoked, because
## `JSON.parse_string` emits an engine `ERROR:` line for malformed input and
## `verify-boot.ps1` treats any `^ERROR:` as a script error.
func _walk_json(base: String, exclude: Array, values: Dictionary,
		tally: Dictionary) -> void:
	var directory := DirAccess.open(base)
	if directory == null:
		return
	directory.list_dir_begin()
	var name: String = directory.get_next()
	while name != "":
		if directory.current_is_dir():
			if name != "." and name != "..":
				var child: String = base.path_join(name)
				if not exclude.has(child):
					_walk_json(child, exclude, values, tally)
		elif name.ends_with(".json"):
			var full: String = base.path_join(name)
			if not exclude.has(full):
				_absorb_document(full, values, tally)
		name = directory.get_next()
	directory.list_dir_end()


func _absorb_document(path: String, values: Dictionary, tally: Dictionary) -> void:
	var text: String = FileAccess.get_file_as_string(path)
	if not text.begins_with("{"):
		# Refused before the parser, for the engine-error reason named above.
		return
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		return
	var document: Dictionary = parsed

	var containers: Array = []
	var private_state: Variant = document.get("privateState", null)
	if typeof(private_state) == TYPE_DICTIONARY:
		containers.append(private_state)
	var maps: Variant = document.get("maps", null)
	var map_count: int = 0
	if typeof(maps) == TYPE_ARRAY:
		for map_object: Variant in maps:
			if typeof(map_object) == TYPE_DICTIONARY:
				containers.append(map_object)
				map_count += 1
	elif typeof(maps) == TYPE_DICTIONARY:
		var keys: Array = (maps as Dictionary).keys()
		keys.sort()
		for key: Variant in keys:
			var map_object: Variant = (maps as Dictionary)[key]
			if typeof(map_object) == TYPE_DICTIONARY:
				containers.append(map_object)
				map_count += 1
	# THE CARRYING RULE: a document counts only when it carries at least one map.
	if map_count == 0:
		return

	tally["documents"] = int(tally.get("documents", 0)) + 1
	tally["maps"] = int(tally.get("maps", 0)) + map_count
	if path.contains("villages"):
		tally["village"] = int(tally.get("village", 0)) + 1

	var containers_probe: Dictionary = {}
	for container: Variant in containers:
		var source: Dictionary = container
		if source.has("premiumAccount"):
			tally["premium_flag"] = int(tally.get("premium_flag", 0)) + 1

	for field_name: String in ALL_FIELD_NAMES:
		for container: Variant in containers:
			var source: Dictionary = container
			if source.has(field_name):
				var bucket: Dictionary = values.get(field_name, {})
				var key: String = _distribution_key(source[field_name])
				bucket[key] = int(bucket.get(key, 0)) + 1
				values[field_name] = bucket
				break


## The canonical distribution key for a recorded value.
##
## `JSON.parse_string` decodes EVERY JSON number as a FLOAT, so a corpus seed of
## `2366` arrives as `2366.0` and `JSON.stringify` then yields the key `"2366.0"`,
## which would never match the pinned key `"2366"`. An integral float is therefore
## normalized to its INT spelling, so the pinned table is written in the same form
## the save would use in Python.
##
## An array key is its stringified form WITHOUT spaces (`[18,17]`, not `[18, 17]`),
## because that is what `JSON.stringify` produces and therefore what the pinned
## table must contain. An earlier revision of this suite compared against
## `"[18, 17]"` and failed on a spacing difference, not a data difference.
func _distribution_key(value: Variant) -> String:
	if typeof(value) == TYPE_FLOAT:
		return _normalize_number(float(value))
	if typeof(value) == TYPE_ARRAY:
		var parts: PackedStringArray = PackedStringArray()
		for element: Variant in (value as Array):
			parts.append(_distribution_key(element))
		return "[" + ",".join(parts) + "]"
	return JSON.stringify(value)


## The canonical spelling of a recorded number.
##
## Applied at EVERY depth, not only at the top: an earlier revision normalized
## only a bare number, so a recorded shot list `[18, 17]` keyed as `[18.0,17.0]`
## and the pinned distribution could never match. Element-wise normalization is
## what makes the array key comparable.
func _normalize_number(as_float: float) -> String:
	if is_equal_approx(as_float, floor(as_float)) and absf(as_float) < 9.0e15:
		return str(int(as_float))
	return JSON.stringify(as_float)


## An order-independent, float-normalized key for a nested structure.
##
## Used to compare a committed content value against its recorded expectation.
## Two mismatches it absorbs, both recorded rather than hidden: every JSON number
## arrives as a FLOAT (so `800` is `800.0`), and dictionary key order is not
## guaranteed by the source that produced the expectation. Sorting the keys is
## what makes the comparison about VALUES rather than about spelling.
func _structure_key(value: Variant) -> String:
	if typeof(value) == TYPE_FLOAT:
		return _normalize_number(float(value))
	if typeof(value) == TYPE_INT:
		return str(value)
	if typeof(value) == TYPE_ARRAY:
		var array_parts: PackedStringArray = PackedStringArray()
		for element: Variant in (value as Array):
			array_parts.append(_structure_key(element))
		return "[" + ",".join(array_parts) + "]"
	if typeof(value) == TYPE_DICTIONARY:
		var source: Dictionary = value
		var names: Array = source.keys()
		names.sort()
		var dict_parts: PackedStringArray = PackedStringArray()
		for key: Variant in names:
			dict_parts.append("%s:%s"
				% [_structure_key(key), _structure_key(source[key])])
		return "{" + ",".join(dict_parts) + "}"
	return JSON.stringify(value)


## Compare two value distributions for equality as SETS of keys with counts.
##
## Both directions are required: an extra observed key fails just as a missing one
## does, which is what stops the pinned table from quietly omitting a value the
## corpus actually holds.
func _distributions_agree(observed: Dictionary, pinned: Dictionary) -> bool:
	if observed.size() != pinned.size():
		return false
	for key: Variant in observed.keys():
		if not pinned.has(key):
			return false
		if int(observed[key]) != int(pinned[key]):
			return false
	return true


## Value equality that tolerates the two documented JSON/GDScript mismatches.
##
## `JSON.parse_string` decodes every JSON number as a FLOAT, so a corpus `0`
## arrives as `0.0` and `0.0 == 0` is false in GDScript. And `JSON.stringify(null)`
## yields the four-character STRING `"null"`, not a null, so comparing a stringified
## key to a null expectation with `==` is a type error.
func _same_value(recorded: Variant, expected: Variant) -> bool:
	if typeof(recorded) == typeof(expected):
		if typeof(recorded) == TYPE_DICTIONARY or typeof(recorded) == TYPE_ARRAY:
			return JSON.stringify(recorded) == JSON.stringify(expected)
		return recorded == expected
	if typeof(recorded) in [TYPE_INT, TYPE_FLOAT] \
			and typeof(expected) in [TYPE_INT, TYPE_FLOAT]:
		return is_equal_approx(float(recorded), float(expected))
	if recorded == null and str(expected) == "null":
		return true
	if expected == null and str(recorded) == "null":
		return true
	return false


# ---------------------------------------------------------------------------
# Requirement 4 & 5 -- the premium duration and the arm selection
# ---------------------------------------------------------------------------

func _check_premium() -> void:
	# Read the committed schedule through the EXISTING normalized registry. This
	# is the one server-derived value in M11, so the read is part of the claim.
	var registry: Variant = _registry_instance()
	check(registry != null,
		"the ContentRegistry autoload instance is available to read committed "
			+ "content through")
	if registry == null:
		return
	# The autoload registers but performs NO implicit load at startup, so this
	# suite must load the committed package explicitly before reading it --
	# `get_entry` on an unloaded registry answers `unknown domain: globals`,
	# which is a real refusal rather than a missing schedule.
	check(not registry.is_loaded(),
		"the ContentRegistry autoload performs no implicit load at startup, so "
			+ "the suite must load the committed package itself")
	var loaded: Dictionary = registry.load_content()
	check(bool(loaded.get("ok", false)),
		("the committed normalized content package loads through the registry "
			+ "(%s)") % str(loaded.get("error", "")))
	var committed: Dictionary = PremiumPurchase.committed_schedule(registry)
	check(bool(committed.get("ok", false)),
		("the committed PREMIUM_ACCOUNTS schedule is read through "
			+ "ContentRegistry.get_entry (%s)") % str(committed.get("error", "")))
	if not bool(committed.get("ok", false)):
		return
	var schedule: Array = committed.get("schedule", [])
	check_eq(schedule.size(), 6,
		"the committed schedule holds exactly SIX entries")

	# The committed entries verbatim, as the content package carries them.
	var expected := [
		{"time": 360, "price": 800}, {"time": 180, "price": 450},
		{"time": 30, "price": 80}, {"time": 7, "price": 40},
		{"time": 3, "price": 20}, {"time": 1, "price": 8},
	]
	check_eq(_structure_key(schedule), _structure_key(expected),
		"the committed schedule is the recorded six entries VERBATIM: durations "
			+ "360/180/30/7/3/1 days beside prices 800/450/80/40/20/8")
	for entry_index: int in range(expected.size()):
		var committed_entry: Variant = schedule[entry_index]
		var expected_entry: Variant = expected[entry_index]
		check_eq(_structure_key(committed_entry), _structure_key(expected_entry),
			("committed schedule entry %d is exactly the recorded object, so a "
				+ "mistranscribed duration or price fails even though both sides "
				+ "hold six entries") % entry_index)
		var committed_fields: Array = (committed_entry as Dictionary).keys()
		var expected_fields: Array = (expected_entry as Dictionary).keys()
		committed_fields.sort()
		expected_fields.sort()
		check_eq(committed_fields, expected_fields,
			("committed schedule entry %d carries exactly the two recorded "
				+ "fields, `time` and `price`") % entry_index)
	premium["schedule"] = schedule
	premium["entries"] = schedule.size()

	# Every duration is derived, and the index is the ONLY input.
	for index: int in range(schedule.size()):
		var expected_days: int = int((schedule[index] as Dictionary)["time"])
		check_eq(PremiumPurchase.premium_days(schedule, index), expected_days,
			("the duration for package %d is derived from the committed schedule "
				+ "as %d days") % [index, expected_days])
		check_eq(PremiumPurchase.premium_days_refusal(schedule, index), "",
			("a valid package index (%d) is not refused") % index)

	# The recorded oversized-index CLAMP, from get_game_config.py:184-185.
	var last_days: int = int((schedule[schedule.size() - 1] as Dictionary)["time"])
	for index: int in [6, 7, 99, 1000000]:
		check_eq(PremiumPurchase.premium_days(schedule, index), last_days,
			("an oversized package index (%d) CLAMPS to the last entry, "
				+ "reproducing get_game_config.py:184-185") % index)
		check(PremiumPurchase._is_clamped(schedule, index),
			("package index %d is reported as clamped, so the clamp is visible "
				+ "rather than silent") % index)
	check(not PremiumPurchase._is_clamped(schedule, 0),
		"an in-range package index is NOT reported as clamped")

	# The missing-duration fallback, from get_game_config.py:187-189.
	check_eq(PremiumPurchase.premium_days([{"price": 5}], 0), 0,
		"a committed entry carrying no `time` yields the recorded 0 fallback")
	check_eq(PremiumPurchase.premium_days([{}], 0), 0,
		"an empty committed entry yields the recorded 0 fallback")
	check_eq(PremiumPurchase.premium_days_refusal([{"price": 5}], 0), "",
		"an entry with no duration is not refused; the legacy branch returns 0")

	# Fail-closed refusals, each named.
	# Each case is `[schedule, package_index, expected_reason]`. The schedule is
	# a VALID one wherever the case is about the index, and the index is a VALID
	# one wherever the case is about the schedule, so each case fails for exactly
	# the reason it names and cannot pass for an unrelated one.
	var refusal_cases := [
		["not_an_array", 0, "schedule_not_array"],
		[[], 0, "schedule_empty"],
		[schedule, "0", "package_index_not_integer"],
		[schedule, -1, "package_index_negative"],
		[[5], 0, "schedule_entry_not_object"],
		[[{"time": "x"}], 0, "schedule_duration_not_integer"],
	]
	for triple: Variant in refusal_cases:
		var probe: Array = triple
		var bad_schedule: Variant = probe[0]
		var bad_index: Variant = probe[1]
		var expected_reason: String = str(probe[2])
		check_eq(PremiumPurchase.premium_days_refusal(bad_schedule, bad_index),
			expected_reason,
			("the malformed input (%s, %s) is refused with its named reason")
				% [str(bad_schedule), str(bad_index)])
		check_eq(PremiumPurchase.premium_days(bad_schedule, bad_index),
			PremiumPurchase.MALFORMED,
			("a refused duration for package index %s returns the MALFORMED "
				+ "sentinel, not a guessed value") % str(bad_index))
		check(str(PremiumPurchase.premium_days_refusal(bad_schedule, bad_index))
				.length() > 0,
			("a refusal for (%s, %s) names a reason rather than returning an "
				+ "empty string") % [str(bad_schedule), str(bad_index)])

	# The two arms, and the comparison that selects them (command.py:618).
	check_eq(PremiumPurchase.select_arm(1000, 500), PremiumPurchase.ARM_SET,
		"when now >= instant the SET arm is selected")
	check_eq(PremiumPurchase.select_arm(1000, 1000), PremiumPurchase.ARM_SET,
		"at the EXACT boundary now == instant the SET arm is selected, "
			+ "reproducing command.py:618's `>=`")
	check_eq(PremiumPurchase.select_arm(999, 1000), PremiumPurchase.ARM_EXTEND,
		"when now < instant the EXTEND arm is selected")
	check_eq(PremiumPurchase.select_arm(1000, 1001), PremiumPurchase.ARM_EXTEND,
		"one second before expiry selects the EXTEND arm")

	# The two arms must genuinely differ. An earlier probe of this change chose
	# values where both arms coincidentally returned 87400, which would have made
	# a broken single-arm implementation indistinguishable from a correct one.
	var days_one: int = 1
	var set_result: Dictionary = PremiumPurchase.purchase(1000, 500, schedule, 5)
	var extend_result: Dictionary = PremiumPurchase.purchase(100, 5000, schedule, 5)
	check_eq(str(set_result.get("arm", "")), PremiumPurchase.ARM_SET,
		"the SET arm is taken when now >= instant")
	check_eq(str(extend_result.get("arm", "")), PremiumPurchase.ARM_EXTEND,
		"the EXTEND arm is taken when now < instant")
	check_eq(int(set_result.get("instant_before", 0)), 500,
		"the SET arm records the instant it read")
	check_eq(int(set_result.get("instant_after", 0)),
		1000 + days_one * PremiumPurchase.SECONDS_PER_DAY,
		"the SET arm computes now + days*86400 (command.py:619)")
	check_eq(int(extend_result.get("instant_after", 0)),
		5000 + days_one * PremiumPurchase.SECONDS_PER_DAY,
		"the EXTEND arm computes instant + days*86400 (command.py:622)")
	check(int(set_result.get("instant_after", 0)) != int(extend_result.get("instant_after", 0)),
		"the two arms produce DIFFERENT instants for the same duration, so the "
			+ "arms are not one implementation wearing two names")
	check_eq(int(set_result.get("days", 0)), days_one,
		"the duration reaches the purchase result as DAYS")
	check_eq(int(set_result.get("seconds", 0)),
		days_one * PremiumPurchase.SECONDS_PER_DAY,
		"the duration is converted to seconds by the named constant 86400")
	premium["set_arm"] = set_result
	premium["extend_arm"] = extend_result

	# Arm reachability, reported per arm as the spec requires.
	for arm_key: String in ["set_arm", "extend_arm"]:
		var result: Dictionary = premium.get(arm_key, {})
		var arm_record: Dictionary = result.get("arm_record", {})
		check(str(arm_record.get("site", "")).length() > 0,
			("the %s cites its recorded command.py write site") % arm_key)
		check(bool(arm_record.has("corpus_reachable")),
			("the %s reports its corpus reachability explicitly") % arm_key)
	check(bool(premium["set_arm"]["arm_record"]["corpus_reachable"]),
	"the SET arm IS corpus-reachable: every committed instant has already "
		+ "passed, so all 33 documents select it")
	check(not bool(premium["extend_arm"]["arm_record"]["corpus_reachable"]),
		"the EXTEND arm is NOT corpus-reachable, so its coverage here is "
			+ "CRAFTED INPUT and never corpus evidence")

	# The purchase refusals.
	check_eq(PremiumPurchase.purchase(1000, null, schedule, 0).get("ok", true),
		false, "a purchase with no recorded premium instant is refused")
	check_eq(PremiumPurchase.purchase(1000, "x", schedule, 0).get("ok", true),
		false, "a purchase whose instant is not an integer is refused")
	check_eq(PremiumPurchase.purchase(-1, 0, schedule, 0).get("ok", true),
		false, "a purchase with a negative server clock is refused")

	# THE COST REFUSAL -- requirement 6.
	#
	# The committed price beside every committed duration has ZERO consumers
	# across all eleven legacy modules, so nothing is charged. Note this is a
	# DIFFERENT mechanism from `research_buy_step_cash`, where the server reads a
	# client-sent price and discards it; here the server IGNORES A COMMITTED one.
	for arm_key: String in ["set_arm", "extend_arm"]:
		var result: Dictionary = premium[arm_key]
		check(not bool(result.get("charged", true)),
			("the %s charges NOTHING, because the committed price has zero "
				+ "consumers") % arm_key)
		check_eq(int(result.get("resources_moved", -1)), 0,
			("the %s reports zero stored resources moved") % arm_key)
		check(not bool(result.get("duration_client_sent", true)),
			("the %s's duration is NOT client-sent") % arm_key)
	var cost: Dictionary = PremiumPurchase.COST_RECORD
	check(not bool(cost.get("charged", true)),
		"the cost record states that nothing is charged")
	check_eq(int(cost.get("resources_moved", -1)), 0,
		"the cost record states that zero stored resources move")
	check_eq(int(cost.get("amount_field_consumers_measured", -1)), 0,
		"the cost record states the committed amount beside every duration has "
			+ "ZERO legacy consumers")
	check(str(cost.get("source", "")).length() > 0,
		"the cost record cites the source that reads the duration and not the "
			+ "amount")
	check(str(cost.get("why", "")).contains("never reads"),
		"the cost record explains WHY the amount is refused: the legacy helper "
			+ "reads the committed duration and never the committed amount")


## The ContentRegistry autoload, or null when the scene did not register it.
##
## `get_entry` is an INSTANCE method, so the script class cannot stand in for it;
## `premium_purchase.gd` refuses a class with `registry_has_no_get_entry`, which
## is correct fail-closed behaviour rather than a defect.
func _registry_instance() -> Variant:
	# `test_base.gd` extends `SceneTree`, so this test script IS the tree and
	# `root` is reached directly -- there is no `get_tree()` to call, which is a
	# parse error rather than a runtime null.
	return root.get_node_or_null("ContentRegistry")


# ---------------------------------------------------------------------------
# Requirement 3, 7 & 8 -- the transitions and their refusals
# ---------------------------------------------------------------------------

func _check_transitions() -> void:
	# darts_reset -- six writes, one client-sent seed.
	var reset: Dictionary = DartsTransitions.reset(7, 1000)
	check(bool(reset.get("ok", false)), "the reset transition succeeds")
	var reset_written: Dictionary = reset.get("written", {})
	check_eq(reset_written.size(), DartsTransitions.RESET_WRITE_COUNT,
		"the reset transition writes exactly SIX fields (command.py:577-582)")
	check_eq(int(reset.get("field_count", 0)), DartsTransitions.RESET_WRITE_COUNT,
		"the reset transition reports its own write count as six")
	for field_name: Variant in ["dartsRandomSeed", "dartsBalloonsShot",
			"dartsHasFree", "dartsGotExtra", "timeStampDartsReset",
			"timeStampDartsNewFree"]:
		check(reset_written.has(field_name),
			("the reset transition writes `%s`") % str(field_name))
	check_eq(int(reset_written.get("dartsRandomSeed", 0)), 7,
		"the reset transition stores the client-sent seed VERBATIM")
	check_eq(JSON.stringify(reset_written.get("dartsBalloonsShot", null)), "[]",
		"the reset transition REPLACES the shot list with an empty one")
	check_eq(bool(reset_written.get("dartsHasFree", false)), true,
		"the reset transition sets the free flag")
	check_eq(bool(reset_written.get("dartsGotExtra", true)), false,
		"the reset transition CLEARS the got-extra flag")
	check_eq(int(reset_written.get("timeStampDartsReset", 0)), 1000,
		"the reset transition stamps both instants with the server clock")
	check_eq(int(reset_written.get("timeStampDartsNewFree", 0)), 1000,
		"the reset transition stamps the new-free instant with the server clock")
	var seed_input: Dictionary = reset.get("client_sent", {}).get(
		"dartsRandomSeed", {})
	check_eq(str(seed_input.get("argument", "")), "args[0]",
		"the seed is NAMED as the client-sent argument args[0]")
	check(not bool(seed_input.get("semantics_derived", true)),
		"NOTHING is derived from the seed: it is stored and read by no branch, so "
			+ "no ordering or meaning is invented")
	check(bool(seed_input.get("stored_verbatim", false)),
		"the seed is recorded as stored verbatim")

	# darts_new_free -- two writes, no client argument at all.
	var free: Dictionary = DartsTransitions.new_free(2000)
	check(bool(free.get("ok", false)), "the free transition succeeds")
	check_eq(int(free.get("field_count", 0)), DartsTransitions.FREE_WRITE_COUNT,
		"the free transition writes exactly TWO fields (command.py:588-589)")
	check_eq(int(free.get("client_argument_count", -1)), 0,
		"the free transition reads NO client argument, as the legacy branch does")
	check_eq(bool(free.get("written", {}).get("dartsHasFree", false)), true,
		"the free transition sets the free flag")
	check_eq(int(free.get("written", {}).get("timeStampDartsNewFree", 0)), 2000,
		"the free transition stamps the new-free instant")

	# darts_shoot_balloon -- three writes, an unbounded list, a refused outcome.
	var state := {"dartsBalloonsShot": [18], "dartsGotExtra": false}
	var win_claim: Dictionary = DartsTransitions.shoot(state, 17, true, 1000)
	check(bool(win_claim.get("ok", false)), "the shoot transition succeeds")
	var shoot_written: Dictionary = win_claim.get("written", {})
	check_eq(int(win_claim.get("field_count", 0)), DartsTransitions.SHOOT_WRITE_COUNT,
		"the shoot transition reports THREE writes: two unconditional plus the "
			+ "conditional got-extra write the legacy branch guards")
	check_eq(JSON.stringify(shoot_written.get("dartsBalloonsShot", null)),
		"[18,17]",
		"the shoot transition APPENDS the client-sent index to the recorded list")
	check_eq(bool(shoot_written.get("dartsHasFree", true)), false,
		"the shoot transition clears the free flag")
	check_eq(int(shoot_written.get("timeStampDartsNewFree", 0)), 1000,
		"the shoot transition stamps the new-free instant")

	# REQUIREMENT 7 -- the client-dictated outcome is REFUSED.
	check(not bool(win_claim.get("extra_flag_from_client_claim", true)),
		"the shoot transition NEVER writes the got-extra flag from the client's "
			+ "claim, even when the client asserts a win")
	check(not shoot_written.has("dartsGotExtra"),
		"the refused outcome leaves the got-extra flag UNWRITTEN, so the "
			+ "delivered write set differs from the legacy branch's")
	var outcome: Dictionary = win_claim.get("client_sent", {}).get(
		"dartsGotExtra", {})
	check_eq(str(outcome.get("argument", "")), "args[1]",
		"the refused outcome is NAMED as the client-sent argument args[1]")
	check(bool(outcome.get("claimed", false)),
		"the transition records that the client DID claim a win")
	check(not bool(outcome.get("delivered", true)),
		"the transition records that the claim was NOT delivered")
	check(win_claim.get("refusals", []).has("args[1]"),
		"the refusal is reported in the result's refusal list")
	var divergences: Array = win_claim.get("divergences", [])
	check_eq(divergences.size(), 1,
		"exactly ONE divergence is recorded, for the refused outcome")
	var divergence: Dictionary = divergences[0]
	check(not bool(divergence.get("is_parity", true)),
		"the recorded divergence is explicitly NOT parity")
	check_eq(str(divergence.get("site", "")), "command.py:604-605",
		"the divergence cites the recorded write site it refuses to reproduce")
	check(str(divergence.get("corpus_evidence", "")).length() > 0,
		"the divergence records its corpus evidence, which is NONE in either "
			+ "direction because dartsGotExtra is false in all 33 documents")

	# A client asserting a LOSS takes the same path: nothing is written either way.
	var loss_claim: Dictionary = DartsTransitions.shoot(
		{"dartsBalloonsShot": [], "dartsGotExtra": false}, 0, false, 5)
	check_eq(loss_claim.get("refusals", []).size(), 0,
		"a client asserting a loss needs no refusal: the flag would not be set "
			+ "either way")
	check(not loss_claim.get("written", {}).has("dartsGotExtra"),
		"the loss path also leaves the got-extra flag unwritten")

	# REQUIREMENT 8 -- the list is unbounded and untested against the schedule.
	check(not bool(win_claim.get("length_bound", true)),
		"the shot list is delivered with NO length bound")
	check(not bool(win_claim.get("membership_tested", true)),
		"the shot index is NOT tested against the committed schedule")
	var shot_input: Dictionary = win_claim.get("client_sent", {}).get(
		"dartsBalloonsShot", {})
	check_eq(str(shot_input.get("role", "")), "intent",
		"the shot index is accepted as client-sent INTENT (design D10)")
	check(not bool(shot_input.get("derived_from_it", true)),
		"NOTHING is derived from the shot index")
	check(not bool(shot_input.get("bounded_with_it", true)),
		"NOTHING is bounded with the shot index")

	# An out-of-schedule shot is still accepted, which is the corpus's own fact.
	var outside: Dictionary = DartsTransitions.shoot(
		{"dartsBalloonsShot": [], "dartsGotExtra": false}, 0, false, 5)
	check_eq(JSON.stringify(outside.get("written", {}).get(
		"dartsBalloonsShot", null)), "[0]",
		"an out-of-schedule shot index 0 is ACCEPTED, reproducing villages/Nerri.json "
			+ "and refusing a membership test the corpus contradicts")
	check(not bool(outside.get("membership_tested", true)),
		"accepting the out-of-schedule shot is a REFUSAL to invent a membership "
			+ "rule, not a validation")

	# Re-shooting a recorded index is a no-op append, as `index not in targets` is.
	var repeat: Dictionary = DartsTransitions.shoot(
		{"dartsBalloonsShot": [18], "dartsGotExtra": false}, 18, false, 5)
	check_eq(JSON.stringify(repeat.get("written", {}).get(
		"dartsBalloonsShot", null)), "[18]",
		"re-shooting an already recorded index does NOT append it twice")

	# Fail-closed refusals on the shoot input shape.
	var refusal_cases := [
		["not_an_object", 1, "recorded_state_not_object"],
		[{}, 1, "shot_list_absent"],
		[{"dartsBalloonsShot": "x"}, 1, "shot_list_not_array"],
		[{"dartsBalloonsShot": []}, "1", "shot_index_not_integer"],
	]
	for pair: Variant in refusal_cases:
		var probe: Array = pair
		var result: Dictionary = DartsTransitions.shoot(probe[0], probe[1],
			false, 5)
		check(not bool(result.get("ok", true)),
			("a malformed shoot input is refused rather than attempted"))
		check_eq(str(result.get("error", "")), str(probe[2]),
			("the malformed shoot input %s/%s is refused with its named reason")
				% [str(probe[0]), str(probe[1])])
	var seed_refusal: Dictionary = DartsTransitions.reset("not_an_int", 1000)
	check(not bool(seed_refusal.get("ok", true)),
		"a non-integer seed is refused rather than stored")

	transitions["reset"] = reset
	transitions["new_free"] = free
	transitions["shoot_win_claim"] = win_claim
	transitions["shoot_out_of_schedule"] = outside
	transitions["write_counts"] = {
		"darts_reset": DartsTransitions.RESET_WRITE_COUNT,
		"darts_new_free": DartsTransitions.FREE_WRITE_COUNT,
		"darts_shoot_balloon": DartsTransitions.SHOOT_WRITE_COUNT,
	}


# ---------------------------------------------------------------------------
# Requirement 9 -- the week-boundary predicate
# ---------------------------------------------------------------------------

func _check_week_reset() -> void:
	check_eq(WeekReset.OFFSET_SECONDS, 259200,
		"the recorded offset is 259200 seconds (3 days), from engine.py:246-247")
	check_eq(WeekReset.WEEK_SECONDS, 604800,
		"the recorded week length is 604800 seconds, from engine.py:248")
	check_eq(WeekReset.RESET_VALUE, 0,
		"the recorded reset value is 0, NOT the server clock")

	# The arithmetic, reproduced from engine.py:243-249 exactly.
	var boundary: Dictionary = WeekReset.evaluate(true, 1672677498, 1000000000)
	check(bool(boundary.get("ok", false)), "the week evaluation succeeds")
	check_eq(str(boundary.get("reason", "")), WeekReset.REASON_WEEK_BOUNDARY,
		"an instant in an earlier week reports the week boundary")
	check(bool(boundary.get("reset_due", false)),
		"an instant in an earlier week reports the reset as due")
	check_eq(int(boundary.get("shifted_instant", 0)), 1672677498 + 259200,
		"the recorded instant is shifted by the 3-day offset (engine.py:246)")
	check_eq(int(boundary.get("shifted_clock", 0)), 1000000000 + 259200,
		"the server clock is shifted by the same offset (engine.py:247)")
	check_eq(int(boundary.get("instant_week", 0)),
		(1672677498 + 259200) / 604800,
		"the shifted instant's week index is a FLOOR division by 604800")
	check_eq(int(boundary.get("clock_week", 0)),
		(1000000000 + 259200) / 604800,
		"the shifted clock's week index is a floor division by 604800")

	# The same week is not a boundary.
	var same_week: Dictionary = WeekReset.evaluate(true,
		1000000000 - 1000, 1000000000)
	check_eq(str(same_week.get("reason", "")), WeekReset.REASON_SAME_WEEK,
		"an instant inside the current week reports no boundary")
	check(not bool(same_week.get("reset_due", true)),
		"an instant inside the current week reports NO reset due")

	# The existence guard from engine.py:243.
	var absent: Dictionary = WeekReset.evaluate(false, null, 1000000000)
	check_eq(str(absent.get("reason", "")), WeekReset.REASON_ABSENT,
		"an ABSENT instant reports absence rather than a computed week, "
			+ "reproducing the `in privateState` guard at engine.py:243")
	check(not bool(absent.get("reset_due", true)),
		"an absent instant never reports a reset due")

	# Fail-closed refusals.
	check_eq(str(WeekReset.evaluate(true, "x", 1000000000).get("reason", "")),
		WeekReset.REASON_INSTANT_TYPE,
		"a non-integer instant is refused with a named reason")
	check_eq(str(WeekReset.evaluate(true, -1, 1000000000).get("reason", "")),
		WeekReset.REASON_NEGATIVE,
		"a negative instant is refused with a named reason")
	check_eq(str(WeekReset.evaluate(true, 0, -1).get("reason", "")),
		WeekReset.REASON_CLOCK_NEGATIVE,
		"a negative server clock is refused with a named reason")

	# NO MUTATION and NO ROUTE are delivered.
	check(not bool(WeekReset.MUTATION_DELIVERED),
		"the week reset delivers NO mutation: the reset-to-zero write belongs to "
			+ "the preserved engine, not to this capability")
	check_eq(WeekReset.DELIVERED_ROUTES.size(), 0,
		"the week reset delivers NO route at all")
	check_eq(int(boundary.get("shifted_clock", -1)) > 0, true,
		"the clock shift is reported for the reader")
	check(not bool(boundary.get("written", true)),
		"the evaluation reports that it wrote NOTHING")
	check(int(boundary.get("reset_value", -1)) == 0
			and not bool(boundary.get("reset_value_is_clock", true)),
		"the evaluation records the reset value as 0 and explicitly NOT the clock")

	# The Thursday/Monday intent is a COMMENT, never a weekday rule.
	var comment: Dictionary = WeekReset.INTENT_COMMENT
	check_eq(str(comment.get("source", "")), "engine.py:244",
		"the recorded intent comment cites its exact source line")
	check_eq(str(comment.get("delivered_as", "")), "a comment",
		"the Thursday/Monday intent is recorded as delivered AS A COMMENT")
	check(not bool(comment.get("weekday_computed", true)),
		"the record states that NO weekday is computed from the intent")
	check(str(comment.get("quoted", "")).contains("hursday"),
		"the recorded text carries the legacy author's own Thursday rationale "
			+ "verbatim, so a reader can audit the claim against engine.py:244")
	check(str(comment.get("why", "")).length() > 0,
		"the record explains why no weekday rule was derived")
	_check_no_weekday_identifier()


## No delivered IDENTIFIER computes a weekday.
##
## Checked over declared function, `const` and `var` names rather than over the
## raw source: the module legitimately names the string key `weekday_computed`
## inside `INTENT_COMMENT`, so a raw substring test fails on the very record that
## documents the refusal. What must not exist is a declared identifier that
## computes one.
func _check_no_weekday_identifier() -> void:
	var module_source: String = source_of("res://scripts/darts/week_reset.gd")
	var needles: Array = ["weekday", "monday", "thursday", "dayofweek",
		"day_of_week", "dayname"]
	var declared: Array = _function_names(module_source)
	for line: String in _strip_code(module_source).split("\n"):
		var text: String = line.strip_edges()
		for keyword: String in ["const ", "var "]:
			if not text.begins_with(keyword):
				continue
			# Take the FIRST whitespace-separated token after the keyword. A
			# `:=` typed declaration leaves the token as `NAME :`, which is not
			# an identifier, so an earlier revision that split on `=` alone
			# scanned only 3 identifiers and its non-vacuity assertion is what
			# caught it.
			var rest: String = text.substr(keyword.length()).strip_edges()
			var space: int = rest.find(" ")
			if space > 0:
				rest = rest.substr(0, space)
			rest = rest.trim_suffix(":")
			if rest.is_valid_identifier():
				declared.append(rest)
	for name: String in declared:
		var lowered: String = name.to_lower()
		for needle: String in needles:
			check(not lowered.contains(str(needle)),
				("the declared identifier `%s` does not compute a weekday, so the "
					+ "recorded Thursday/Monday comment was not turned into a rule")
					% name)
	check(declared.size() >= 6,
		"the weekday scan inspected a non-trivial set of declared identifiers "
			+ "(%d), so its emptiness is meaningful rather than vacuous"
			% declared.size())


# ---------------------------------------------------------------------------
# Requirement 10 -- content ownership
# ---------------------------------------------------------------------------

func _check_boundary() -> void:
	# The darts schedule and the globals entry stay owned by normalization.
	check_eq(str(DartsState.SCHEDULE_RANGE["owner"]),
		"darts-schedule-normalization",
		"the committed darts_items schedule stays owned by its normalization "
			+ "capability")
	check_eq(str(PremiumPurchase.SCHEDULE_OWNER), "globals-tuning-normalization",
		"the committed PREMIUM_ACCOUNTS entry stays owned by its normalization "
			+ "capability")
	check_eq(PremiumPurchase.CONTENT_DOMAIN, "globals",
		"the premium schedule is read from the `globals` domain")
	check_eq(PremiumPurchase.SCHEDULE_KEY, "PREMIUM_ACCOUNTS",
		"the premium schedule is read by its committed key")
	check_eq(PremiumPurchase.DURATION_FIELD, "time",
		"the duration is read from the committed `time` field, as "
			+ "get_premium_days does")
	check_eq(PremiumPurchase.DURATION_UNIT, "days",
		"the committed duration's unit is recorded as days")
	check_eq(PremiumPurchase.SECONDS_PER_DAY, 86400,
		"the days-to-seconds conversion is the recorded 86400")

	# No committed price is read anywhere in the three delivered modules.
	for module_path: String in [
			"res://scripts/darts/darts_state.gd",
			"res://scripts/darts/premium_purchase.gd",
			"res://scripts/darts/week_reset.gd",
			"res://scripts/darts/darts_transitions.gd",
		]:
		var text: String = source_of(module_path)
		var code: String = _strip_code(text)
		check(_does_not_read_price(code),
			("the module `%s` reads NO committed price field in CODE (a mention in "
				+ "a comment is fine; a subscript is not)")
				% module_path.get_file())

	# The projection is read-only: it declares no setter, no setter-by-name, and
	# no assignment-shaped public method.
	for module_path: String in [
			"res://scripts/darts/darts_state.gd",
			"res://scripts/darts/premium_purchase.gd",
			"res://scripts/darts/week_reset.gd",
			"res://scripts/darts/darts_transitions.gd",
		]:
		var names: Array = _function_names(source_of(module_path))
		for method_name: String in names:
			check(not _looks_like_a_setter(method_name),
				("the module `%s` declares no setter-shaped function `%s`; the "
					+ "projection is read-only")
					% [module_path.get_file(), method_name])

	# The fresh-player limitation is recorded as a reason, not an absence.
	check(str(DartsState.FRESH_PLAYER_LIMIT.get("document", "")).length() > 0,
		"the fresh-player limitation NAMES the document it applies to")


func _looks_like_a_setter(name: String) -> bool:
	var lowered: String = name.to_lower()
	return lowered.begins_with("set_") or lowered.begins_with("write_") \
		or lowered.ends_with("_set") or lowered.ends_with("_write") \
		or lowered == "set" or lowered == "write" \
		or lowered == "apply" or lowered.begins_with("apply_")


## True when `code` contains no read of a committed price field.
##
## Checked in CODE only, with comments stripped, because every delivered module
## names the refused price field in its documentation -- a raw-source substring
## test would fail on the very comments that record the refusal.
func _does_not_read_price(code: String) -> bool:
	for field_name: String in ["\"price\"", "'price'"]:
		if code.contains(field_name):
			# A dictionary LITERAL in a recorded table is not a read. The
			# dangerous form is a subscript, so require no `[` before it.
			var index: int = code.find(field_name)
			while index != -1:
				var before: String = code.substr(max(0, index - 1), 1)
				var after: String = code.substr(index + field_name.length(), 1)
				var is_literal: bool = (index > 0 and before == ":") \
						or (index > 0 and before == "{") \
						or (index > 0 and before == ",") \
						or after == ":"
				if not is_literal:
					return false
				index = code.find(field_name, index + 1)
	return true


# ---------------------------------------------------------------------------
# Requirement 11 -- structural absence guards, proven by injection
# ---------------------------------------------------------------------------

## The whole static-function inventory of the three delivered modules, pinned.
##
## This is the REAL gate. Any function outside this list fails here, whatever it
## is called. The reserved-name test below is the belt: it exists to report WHY a
## helper is forbidden, and because an exact-name check was measured in this
## project to miss a suffixed helper wearing a reserved name.
const EXPECTED_FUNCTIONS := {
	"res://scripts/darts/darts_state.gd": [
		"field_names", "darts_field_names", "field_record", "distinct_values_of",
		"recorded_values_of", "is_client_sent", "project",
		# The `DartsProjection` inner class. Pinned in the same inventory rather
		# than exempted, because an exemption would be an unguarded hole exactly
		# where an invented helper is easiest to hide.
		"_init", "_projected_names", "present", "value", "has_recorded_shots",
		"premium_instant_is_future", "present_names", "absent_names",
	],
	"res://scripts/darts/premium_purchase.gd": [
		"committed_schedule", "premium_days", "premium_days_refusal",
		"select_arm", "instant_after", "purchase", "_is_clamped", "_is_integral",
	],
	"res://scripts/darts/week_reset.gd": [
		"week_index", "evaluate", "_is_integral",
	],
	"res://scripts/darts/darts_transitions.gd": [
		"reset", "new_free", "shoot", "_base", "_refuse", "_is_integral",
	],
}


func _check_absence() -> void:
	# Every recorded absent helper is justified.
	for entry: Dictionary in DartsState.ABSENT_HELPERS:
		check(str(entry.get("absent_because", "")).length() > 0,
			("the absent helper `%s` records WHY it is absent")
				% str(entry.get("helper", "?")))
		check(str(entry.get("helper", "")).length() > 0,
			"every absent-helper entry names a helper")

	# The whole-inventory pin, in BOTH directions, per module.
	for module_path: String in EXPECTED_FUNCTIONS.keys():
		var present: Array = _function_names(source_of(module_path))
		var expected: Array = EXPECTED_FUNCTIONS[module_path]
		var unexpected: Array = []
		for name: String in present:
			if not expected.has(name):
				unexpected.append(name)
		check_eq(unexpected, [],
			("the module `%s` declares EXACTLY its recorded accessors: no "
				+ "price-charging, shot-bounding, membership-testing, "
				+ "win-verifying, client-duration, or eligibility helper exists")
				% module_path.get_file())
		var missing: Array = []
		for name: String in expected:
			if not present.has(name):
				missing.append(name)
		check_eq(missing, [],
			("the module `%s` delivers EXACTLY the recorded accessors, so the "
				+ "inventory cannot be padded with a name nobody declared")
				% module_path.get_file())

	# The reserved-name belt: case-folded SUBSTRING, bidirectional.
	#
	# An exact-name check was measured in this project to miss a suffixed helper
	# wearing a reserved name, and a case-sensitive check to miss a renamed one.
	var reserved: Array = []
	for entry: Dictionary in DartsState.ABSENT_HELPERS:
		reserved.append(str(entry.get("helper", "")))
	for module_path: String in EXPECTED_FUNCTIONS.keys():
		for name: String in _function_names(source_of(module_path)):
			for needle: String in reserved:
				if _matches_reserved(name, needle):
					check(false,
						("the module `%s` declares `%s`, which collides with the "
							+ "recorded absent helper `%s`")
							% [module_path.get_file(), name, needle])


## Bidirectional, case-folded substring match.
##
## `a` matches `b` if either contains the other, so a PREFIXED or SUFFIXED helper
## is caught, not only an exact spelling.
func _matches_reserved(name: String, needle: String) -> bool:
	if needle.length() == 0:
		return false
	var a: String = name.to_lower()
	var b: String = needle.to_lower()
	return a.contains(b) or b.contains(a)


## The declared function names of a module, comments stripped.
##
## Split by LINE rather than matched with a multiline `^`-anchored regex: GDScript's
## `RegEx` has no multiline flag, so `^[ \t]*func` matched ZERO declarations in
## every delivered module and this inventory -- the real anti-invention gate --
## was silently vacuous. An earlier revision used `search_all` and reported every
## accessor as "not delivered". Line splitting is what the sibling census does.
func _function_names(source: String) -> Array:
	var out: Array = []
	for line: String in _strip_code(source).split("\n"):
		var text: String = line.strip_edges()
		if text.begins_with("static func "):
			text = text.substr(12)
		elif text.begins_with("func "):
			text = text.substr(5)
		else:
			continue
		var paren: int = text.find("(")
		if paren < 0:
			continue
		var name: String = text.substr(0, paren).strip_edges()
		# A signature broken across lines yields an empty name; skip rather than
		# record a phantom entry that could never be declared.
		if name.length() > 0 and name.is_valid_identifier():
			out.append(name)
	return out


## Strip comments from GDScript source, preserving STRING CONTENTS.
##
## String contents are preserved on purpose: every persistence field is reached
## through a dict subscript like `privateState["timeStampEndPremium"]`, so
## blanking strings would erase the very tokens the guards must see. An earlier
## revision of the sibling census passed a PATH where a BODY was expected, making
## three scans vacuously true.
func _strip_code(source: String) -> String:
	var out: String = ""
	var index: int = 0
	var length: int = source.length()
	while index < length:
		var character: String = source[index]
		if character == "#":
			while index < length and source[index] != "\n":
				index += 1
		elif character == "\"":
			out += character
			index += 1
			while index < length:
				var inner: String = source[index]
				out += inner
				index += 1
				if inner == "\\":
					if index < length:
						out += source[index]
						index += 1
					continue
				if inner == "\"":
					break
		elif character == "'":
			out += character
			index += 1
			while index < length:
				var inner2: String = source[index]
				out += inner2
				index += 1
				if inner2 == "\\":
					if index < length:
						out += source[index]
						index += 1
					continue
				if inner2 == "'":
					break
		else:
			out += character
			index += 1
	return out


func _declares_any(source: String, needles: Array) -> bool:
	var code: String = _strip_code(source).to_lower()
	for needle: Variant in needles:
		if code.contains(str(needle).to_lower()):
			return true
	return false


func source_of(path: String) -> String:
	return FileAccess.get_file_as_string(path)


# ---------------------------------------------------------------------------
# The evidence report
# ---------------------------------------------------------------------------

## The injection results, produced by the orchestrator.
##
## Each probe was applied to a byte-identical copy of the real module, this suite
## was run, the copy was restored, and the restored digest compared. The suite
## cannot rewrite the module it is judging, so the probes are applied outside it
## and their measured results are recorded here. The `whole_inventory_pin` row is
## the important one: it borrows NO reserved word, so it is caught only by the
## inventory pin -- which is what makes the pin the gate and the name test the
## belt rather than the other way round.
func _injection_record() -> Dictionary:
	return {
		"method": "each probe was applied to a byte-identical copy of the real "
			+ "delivered module, this suite was run against it, the copy was "
			+ "restored, and the restored SHA-256 compared to the original; the "
			+ "suite cannot rewrite the module it is judging, so the orchestrator "
			+ "applies the probes and the MEASURED results are recorded here",
		"probes_detected": 10,
		"probes_missed": 0,
		"all_restores_byte_identical": true,
		"probes": [
			{
				"probe": "static func premium_charge(schedule, index)",
				"module": "premium_purchase.gd",
				"disguise": "the natural invented name for charging a premium "
					+ "account, but NOT itself a recorded absent name",
				"guards_that_fired": ["whole_inventory_pin"],
				"failures": 1,
				"exit_code": 1,
			},
			{
				"probe": "static func cost_for(item_id)",
				"module": "premium_purchase.gd",
				"disguise": "a generic invented cost helper, and NOT a recorded "
					+ "absent name",
				"guards_that_fired": ["whole_inventory_pin"],
				"failures": 1,
				"exit_code": 1,
			},
			{
				"probe": "static func in_schedule(shot_index)",
				"module": "darts_transitions.gd",
				"disguise": "the exact membership refusal this line exists to "
					+ "prevent, spelled exactly",
				"guards_that_fired": ["whole_inventory_pin",
					"reserved_name_folded_substring"],
				"failures": 2,
				"exit_code": 1,
			},
			{
				"probe": "static func shot_limit()",
				"module": "darts_transitions.gd",
				"disguise": "an invented shot-list bound, spelled exactly",
				"guards_that_fired": ["whole_inventory_pin",
					"reserved_name_folded_substring"],
				"failures": 2,
				"exit_code": 1,
			},
			{
				"probe": "static func verify_win(shot_index)",
				"module": "darts_transitions.gd",
				"disguise": "an invented win verification, spelled exactly",
				"guards_that_fired": ["whole_inventory_pin",
					"reserved_name_folded_substring"],
				"failures": 2,
				"exit_code": 1,
			},
			{
				"probe": "static func normalize(first, second)",
				"module": "week_reset.gd",
				"disguise": "NO reserved word borrowed at all, so it can only be "
					+ "caught by the pin; this is why the pin is the gate",
				"guards_that_fired": ["whole_inventory_pin"],
				"failures": 1,
				"exit_code": 1,
			},
			{
				"probe": "static func CLIENT_DURATION(package_index)",
				"module": "premium_purchase.gd",
				"disguise": "a recorded absent name in UPPER CASE, which a "
					+ "case-sensitive comparison does not match",
				"guards_that_fired": ["whole_inventory_pin",
					"reserved_name_folded_substring"],
				"failures": 2,
				"exit_code": 1,
			},
			{
				"probe": "a committed price read by SUBSCRIPT, "
					+ "(entry as Dictionary)[\"price\"]",
				"module": "premium_purchase.gd",
				"disguise": "not a reserved name at all: a silent reach into the "
					+ "refused field, which the inventory pin cannot see by design",
				"guards_that_fired": ["whole_inventory_pin",
					"no_committed_price_read"],
				"failures": 2,
				"exit_code": 1,
			},
			{
				"probe": "a committed price read by .get(), "
					+ "(entry as Dictionary).get(\"price\", 0)",
				"module": "premium_purchase.gd",
				"disguise": "the second access FORM of the same silent read, so "
					+ "both spellings are proven rather than one",
				"guards_that_fired": ["whole_inventory_pin",
					"no_committed_price_read", "reserved_name_folded_substring"],
				"failures": 3,
				"exit_code": 1,
			},
			{
				"probe": "static func darts_charge_for(schedule)",
				"module": "premium_purchase.gd",
				"disguise": "a recorded absent name WEARING A SUFFIX, "
					+ "`darts_charge_for` contains `darts_charge`",
				"guards_that_fired": ["whole_inventory_pin",
					"reserved_name_folded_substring"],
				"failures": 2,
				"exit_code": 1,
			},
		],
		"measured_belt_limitation": "probes 1 and 2 fired ONE guard, not two. "
			+ "`premium_charge` and `cost_for` contain no recorded absent name and "
			+ "are not contained by one, so the case-folded substring belt stayed "
			+ "silent and only the whole-inventory pin caught them. The belt is "
			+ "therefore NOT a complete second line of defence: it fires only for "
			+ "names that overlap a recorded absent name, which is why the pin is "
			+ "the gate and this limitation is recorded rather than smoothed over",
		"measured_parse_error_lesson": "two earlier probe attempts reported "
			+ "`failures=0 exit=1`, which is a PARSE ERROR rather than a clean "
			+ "detection: the injected body reached GDScript as `(entry as "
			+ "Dictionary)[\"\"price\"\"]` because a doubled quote inside a "
			+ "PowerShell double-quoted here-string is not collapsed. Those two "
			+ "runs proved nothing and were discarded rather than recorded as "
			+ "passing; both probes were rewritten and re-measured",
	}


func _write_report() -> void:
	var path: String = DEFAULT_REPORT_PATH
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report="):
			path = argument.trim_prefix("--report=")
	var report := {
		"schema": "darts-report-v1",
		"capability": "godot-darts",
		"kind": "server-derived value plus refusals",
		"delivered": [
			"a typed read-only projection of six darts state fields plus the two "
				+ "fields handed from godot-social-state",
			"the three recorded darts transitions with their client-sent inputs "
				+ "named as client-sent",
			"the premium duration derived from the committed PREMIUM_ACCOUNTS "
				+ "schedule, with its recorded index clamp",
			"the premium arm selection by the recorded server-side comparison, "
				+ "with each arm's corpus reachability reported",
			"the week-boundary reset as a pure predicate with no mutation and no "
				+ "route",
		],
		"not_delivered": [
			"any charge: the committed price has zero legacy consumers",
			"the client-dictated shot outcome (refused, and recorded as a "
				+ "divergence rather than reproduced as parity)",
			"any shot-list length bound",
			"any schedule-membership test, which the corpus contradicts",
			"any weekday rule, from the legacy author's own comment",
			"any executed-legacy fixture",
			"any rendering, darts table, or premium-buy screen",
		],
		"fields": _field_table(),
		"corpus": corpus,
		"projection": projection,
		"premium": premium,
		"transitions": transitions,
		"week_reset": {
			"offset_seconds": WeekReset.OFFSET_SECONDS,
			"week_seconds": WeekReset.WEEK_SECONDS,
			"reset_value": WeekReset.RESET_VALUE,
			"reset_value_is_clock": false,
			"mutation_delivered": WeekReset.MUTATION_DELIVERED,
			"delivered_routes": WeekReset.DELIVERED_ROUTES,
			"intent_comment": WeekReset.INTENT_COMMENT,
			"out_of_scope_reset": WeekReset.OUT_OF_SCOPE_RESET,
		},
		"absent_helpers": DartsState.ABSENT_HELPERS,
		"content_ownership": {
			"darts_schedule": DartsState.SCHEDULE_RANGE,
			"premium_schedule": {
				"owner": PremiumPurchase.SCHEDULE_OWNER,
				"domain": PremiumPurchase.CONTENT_DOMAIN,
				"key": PremiumPurchase.SCHEDULE_KEY,
				"duration_field": PremiumPurchase.DURATION_FIELD,
				"duration_unit": PremiumPurchase.DURATION_UNIT,
			},
		},
		"cost_record": PremiumPurchase.COST_RECORD,
		"premium_flag_absence": DartsState.PREMIUM_FLAG_ABSENT,
		"live_premium_document": DartsState.LIVE_PREMIUM_DOCUMENT,
		"out_of_schedule_shots": DartsState.OUT_OF_SCHEDULE_SHOTS,
		"handed_fields": DartsState.HANDED_FIELDS,
		"fresh_player_limit": DartsState.FRESH_PLAYER_LIMIT,
		"guard_injections": _injection_record(),
		"expected_function_inventory": EXPECTED_FUNCTIONS,
		"claim_limits": [
			"the corpus denominator is 33 canonical documents, not the 231 the "
				+ "investigation reported: 200 of those were generated fixture "
				+ "files, each recording both sides of one transaction",
			"dartsGotExtra is false in 33 of 33 documents, so the corpus records "
				+ "no won shot and the client-dictated outcome refusal has NO "
				+ "corpus evidence in either direction",
			"nothing is charged, and that is a REFUSAL rather than parity: "
				+ "engine.apply_resources applies a client-sent eight-slot vector "
				+ "before dispatch, so a legacy client could pair a debit with "
				+ "the purchase",
			"the committed price has zero consumers, which is a DIFFERENT "
				+ "mechanism from research_buy_step_cash, where the server "
				+ "discards a client-sent price; here it ignores a committed one",
			"the extend arm is unreachable in the corpus because every committed "
				+ "instant has already passed, so its coverage here is crafted "
				+ "input and never corpus evidence",
			"the shot index is accepted as client-sent intent per design D10; "
				+ "nothing is derived from it and nothing is bounded with it",
			"no weekday rule is implemented: the legacy comment's Thursday/Monday "
				+ "rationale is recorded as a comment only",
			"no parity is claimed anywhere: nothing here executes against the "
				+ "legacy server, and no executed-legacy fixture exists because "
				+ "the fresh-player document cannot drive this surface",
			"absence of a token is not absence of a feature: whether the Flash "
				+ "client showed a darts table or a premium-buy screen is "
				+ "unverifiable from the preserved oracle",
			"the premium instant is reported as recorded; no entitlement, flag, "
				+ "or expiry rule is derived from it",
		],
	}
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the evidence report could not be written to %s" % path)
		return
	file.store_string(JSON.stringify(report, "  ", false, true))
	file.close()
	info("wrote the darts evidence report to %s" % path)


## The field table, read through the module's own accessor rather than
## transcribed, so the report cannot drift from the code it documents.
func _field_table() -> Array:
	var out: Array = []
	for name: String in DartsState.field_names():
		var record: Variant = DartsState.field_record(name)
		if not (record is Dictionary):
			continue
		var entry: Dictionary = record
		out.append({
			"name": name,
			"store": entry.get("store", ""),
			"distinct": entry.get("distinct", -1),
			"documents": entry.get("documents", 0),
			"written_by": entry.get("written_by", []),
			"readers": entry.get("readers", []),
			"client_sent": entry.get("client_sent", false),
			"recorded_values": entry.get("recorded_values", {}),
			"note": entry.get("note", ""),
			"owned_by_this_capability": DartsState.darts_field_names().has(name),
		})
	return out
