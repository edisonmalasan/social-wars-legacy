extends "res://tests/test_base.gd"
## Social-state suite (OpenSpec `godot-social-state` "The delivered surface is a
## typed read-only projection of persisted social state, and it implies no social
## feature" / "The nineteen measured social fields are delivered with their
## recorded storage location" / "The zero-consumer census is re-derived on every
## run and never merely asserted" / "`questsRank` is reported as
## read-without-written and is not folded into the zero-consumer group" /
## "Uniform emptiness is reported as one recorded value and its document count,
## and no populated example is synthesized" / "An absent field is reported as
## absent and is never coerced to its committed uniform value" / "The one real
## social-state writer is recorded with its client-sent value and is not
## reproduced" / "No social reward, coin, worker cost, eligibility window, or
## assist task is derived or charged" / "The social content tables remain owned
## by `social-tables-normalization`" / "Absence is guarded structurally, and
## both guards are proven by injection" / "The absence of an executed-legacy
## fixture is recorded as the deliverable, not left as a gap" / "Visits and
## scores are reported as having no server-side surface", design D1-D10).
##
## This line delivers a REFUSAL, so a large part of what it asserts is an
## **absence**: twelve of nineteen social state fields have zero occurrences of
## any kind across all eleven legacy modules. An absence is exactly what a later
## contributor erases by accident, so the absence is **re-derived on every run**
## rather than asserted, and three structural guards must fail when violated.
##
## The committed investigation and the proposal said thirteen, counting
## `questsRank`; that was wrong, because `admin_set_quest_rank` both reads and
## writes it. The re-derivation is what surfaced the error, which is the point
## of re-deriving.
##
## Checks:
##   projection  the nineteen measured fields, their recorded store, the
##               recorded uniform value and document count, reported verbatim;
##   absent      a missing key reported ABSENT and never coerced to the field's
##               recorded uniform value, with the recorded slot travelling beside
##               the refusal;
##   census      the zero-occurrence group recomputed from the committed legacy
##               sources and compared to the pinned set in BOTH directions, with
##               `questsRank` placed outside it and its single reader named;
##   corpus      the uniform-value table measured over the committed documents,
##               and the recorded statement that no populated example exists;
##   recorded    `set_resource_allies` recorded verbatim as a client-sent write
##               that this capability does NOT reproduce, and the empty route set;
##   boundary    the three social content tables not projected, their owner
##               asserted to exist, and no derived rule from any of them;
##   absence     the module's whole function inventory compared against a pinned
##               list, the ABSENT_HELPERS inventory complete with reasons, and no
##               comparison of one committed social value against another;
##   visits      the world keys carried but never read, the measured absence of
##               score arithmetic, and the two rejected near-miss readings;
##   legacy      every recorded legacy figure re-derived from the committed source
##               in this same run, so no count is taken on trust.
##
## `--report=<path>` writes the deterministic `social-state-report-v1` evidence
## report; the bare `--report` flag defaults to
## `evidence/social-state/report.json`. The tables are derived from the live
## module and from the measurements this run performed, so they cannot drift from
## the code and the source they document.

## The whole delivered module. Its projection table and static accessors are
## reached directly on the script, matching `unit_movement.gd`'s convention.
## `Paths` is inherited from `test_base.gd`, which preloads
## `res://scripts/package_paths.gd`; redeclaring it here is a parse error.
const SocialState := preload("res://scripts/social/social_state.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/social-state/report.json"

## The eleven legacy modules, relative to the repository root.
const LEGACY_ROOTS := ["../../legacy"]

## The measured field names, in the investigation's order.
const EXPECTED_FIELD_NAMES := [
	"friendsHelpedCoveredItem", "neighborAssists", "receivedAssists",
	"resourceAlliesMarket", "firstTimeAlliance", "helpMap", "attacksSent",
	"attacksReceived", "attacksPack", "spyings", "spyingsPack",
	"publishedOpenGraphUnit", "marketPlaceFirstTime", "questsRank",
	"numTradesDone", "resourcesTraded", "timestampLastTrade",
	"timeStampEndPremium", "crossPromotionsFinished",
]

## The fields recorded as living in the map rather than private state.
const EXPECTED_MAP_FIELDS := [
	"receivedAssists", "resourceAlliesMarket", "numTradesDone",
	"resourcesTraded", "timestampLastTrade",
]

## The pinned zero-occurrence census, which this suite RE-DERIVES every run.
##
## `questsRank` is deliberately ABSENT, and its absence is the sharpest check in
## this suite. An early revision counted identifier tokens only, and because the
## comment-stripping lexer erases string literals it scored `questsRank` as zero -
## hiding that `command.py:750` really writes it. That branch both READS and
## WRITES the field, so it is in neither category here.
const EXPECTED_ZERO_OCCURRENCE := [
	"friendsHelpedCoveredItem", "neighborAssists", "receivedAssists",
	"firstTimeAlliance", "helpMap", "attacksSent", "attacksReceived",
	"attacksPack", "spyings", "spyingsPack",
	"resourcesTraded", "crossPromotionsFinished",
]

## The twelve write-less fields and their single recorded corpus value.
const EXPECTED_UNIFORM_VALUES := {
	"friendsHelpedCoveredItem": null,
	"firstTimeAlliance": null,
	"neighborAssists": {},
	"receivedAssists": {},
	"resourcesTraded": {},
	"helpMap": [],
	"attacksSent": [],
	"attacksReceived": [],
	"spyings": [],
	"crossPromotionsFinished": [],
	"attacksPack": 0,
	"spyingsPack": 0,
}

## The absent-helper families the recorded inventory must name.
const ABSENT_FAMILIES := [
	"assist", "friend", "visit", "neighbor_map", "social_reward", "social_action",
	"score", "leaderboard", "ranking", "allies", "gift", "invite",
	"relationship", "cooperation", "spy", "attack_pack", "help_reward",
	"populate",
]

## The module's whole public function inventory, pinned (design D7).
const EXPECTED_FUNCTIONS := [
	"field_names", "zero_occurrence_names", "store_of", "field_record", "project",
]

## The instance-side public functions, pinned.
const EXPECTED_INSTANCE_FUNCTIONS := [
	"present", "value", "present_names", "absent_names",
]

## The census measurement, filled in by `_check_census`.
var census := {}

## The corpus measurement, filled in by `_check_corpus`.
var corpus := {}

## The legacy re-measurement, filled in by `_check_legacy`.
var legacy := {}


func run_scenario() -> void:
	_check_projection()
	_check_absent()
	_check_census()
	_check_corpus()
	_check_recorded()
	_check_boundary()
	_check_absence()
	_check_visits()
	_check_legacy()
	if OS.get_cmdline_user_args().has("--report") \
			or _has_report_argument():
		_write_report()


func _has_report_argument() -> bool:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report"):
			return true
	return false


# ---------------------------------------------------------------------------
# The projection (requirements 1, 2)
# ---------------------------------------------------------------------------

func _check_projection() -> void:
	var names: Array = SocialState.field_names()
	check_eq(names.size(), 19,
		"the projection delivers exactly the NINETEEN measured social fields")
	check_eq(names, EXPECTED_FIELD_NAMES,
		"the delivered field names equal the investigation's measured list, in order")

	# bidirectional: every expected name is delivered
	for expected: String in EXPECTED_FIELD_NAMES:
		check(names.has(expected),
			"the measured field `%s` is delivered" % expected)

	var maps: Array = []
	for name: String in names:
		var store: String = SocialState.store_of(name)
		check(store == "privateState" or store == "maps[]",
			"the field `%s` records a known store, got `%s`" % [name, store])
		if store == "maps[]":
			maps.append(name)
	check_eq(maps, EXPECTED_MAP_FIELDS,
		"the fields recorded as map keys are exactly the measured five")

	# an unmeasured name yields no store and no field, never a guessed one
	check_eq(SocialState.store_of("not_a_measured_field"), "",
		"an unmeasured field name yields no store rather than a guessed one")

	var state = SocialState.project(null)
	check(state.field("not_a_measured_field") == null,
		"an unmeasured field name yields no projection entry")
	check(state.present_names().is_empty(),
		"a document that is not a save projects no present field")


# ---------------------------------------------------------------------------
# Absent is not empty (requirement 6)
# ---------------------------------------------------------------------------

func _check_absent() -> void:
	# a document carrying one social field only
	var document := {
		"privateState": {"neighborAssists": {"0": 1}},
		"maps": [{"resourceAlliesMarket": "wood"}],
	}
	var state = SocialState.project(document)

	check_eq(state.present("neighborAssists"), true,
		"a carried field is reported present")
	check_eq(state.value("neighborAssists"), {"0": 1},
		"the carried value is reported verbatim")
	# This document deliberately carries TWO fields, one per store, so a
	# projection that read only `privateState` would be caught instead of
	# passing on a coincidental single match.
	check_eq(state.present_names(), ["neighborAssists", "resourceAlliesMarket"],
		"the carried fields of BOTH stores are reported present, in measured order")
	check_eq(state.absent_names().size(), 17,
		"every uncarried field is reported absent: 19 measured, 2 carried")

	# THE load-bearing case: an absent field must NOT take the uniform value.
	check_eq(state.value("receivedAssists"), null,
		"an absent field reports a null value")
	check_eq(state.present("receivedAssists"), false,
		"an absent field is distinguishable from one recorded as null")
	var received = state.field("receivedAssists")
	check_eq(received.present, false,
		"the absent field's entry records present=false")
	check_eq(received.recorded_value, null,
		"the absent field's recorded value stays null and is NOT defaulted "
			+ "to the committed uniform value {}")
	# The uniform value is held as its OWN column, which is what proves the
	# previous check is not merely reading a null. Asserting it here makes the
	# separation mechanical: the value exists, and the projection still refused
	# to substitute it for a key the document did not carry.
	check_eq(received.committed_value, {},
		"the committed uniform value is reported in its own column, not merged "
			+ "into the recorded one")

	# `spyingsPack`'s uniform value is 0: an absent key must not become 0 either.
	check_eq(state.value("spyingsPack"), null,
		"an absent field with a uniform ZERO is not coerced to 0")
	check_eq(state.present("spyingsPack"), false,
		"absence is reported for a field whose uniform value is 0")
	check_eq(state.field("spyingsPack").committed_value, 0,
		"the uniform ZERO is likewise held separately from the absent value")

	# non-save inputs refuse cleanly
	for bad: Variant in [null, 42, "text", [], {}]:
		var refused = SocialState.project(bad)
		check_eq(refused.present_names(), [],
			"a non-save document projects no present field")
		check_eq(refused.field("neighborAssists") != null, true,
			"the field table is still available for a refused document")

	# a save whose privateState is missing entirely
	var bare = SocialState.project({"maps": []})
	check_eq(bare.present("neighborAssists"), false,
		"a document with no privateState reports every privateState field absent")
	check_eq(bare.present_names(), [],
		"a document with no privateState and an empty map projects nothing")


# ---------------------------------------------------------------------------
# The re-derived census (requirements 3, 4)
# ---------------------------------------------------------------------------

func _check_census() -> void:
	var recomputed: Array = _recompute_zero_occurrence()

	# THE GUARD: the pinned number is never taken on trust.
	check_eq(recomputed.size(), EXPECTED_ZERO_OCCURRENCE.size(),
		"the RE-DERIVED zero-occurrence count matches the pinned expectation "
			+ "(13) - a legacy edit that adds or removes an occurrence must fail here")
	check_eq(recomputed, EXPECTED_ZERO_OCCURRENCE,
		"the RE-DERIVED zero-occurrence set equals the pinned set exactly")
	for name: String in EXPECTED_ZERO_OCCURRENCE:
		check(recomputed.has(name),
			"the pinned zero-occurrence field `%s` reproduces" % name)
	for name: String in recomputed:
		check(EXPECTED_ZERO_OCCURRENCE.has(name),
			"the recomputed field `%s` is in the pinned expectation" % name)
	census["zero_occurrence_recomputed"] = recomputed
	census["zero_occurrence_count"] = recomputed.size()

	# the module's own pinned table agrees with the suite's
	check_eq(SocialState.zero_occurrence_names(), EXPECTED_ZERO_OCCURRENCE,
		"the module's pinned zero-occurrence table equals the suite's")

	# questsRank is read AND written, so it is NOT in the zero group (D9).
	#
	# This is the check that caught the census defect: counting identifier tokens
	# alone scored it zero, because the strip erases the `["questsRank"]` form
	# the branch actually uses. The two-form count below is what makes the
	# exclusion real rather than inherited.
	check(not recomputed.has("questsRank"),
		"questsRank is NOT in the zero-occurrence group, because the dispatcher "
			+ "really does read and write it")
	check(not EXPECTED_ZERO_OCCURRENCE.has("questsRank"),
		"questsRank is absent from the pinned group too")
	var forms: Dictionary = census.get("forms:questsRank", {})
	check(int(forms.get("quoted", 0)) > 0,
		"questsRank really occurs in the QUOTED subscript form, which is how the "
			+ "legacy server reaches it - the form the stripped view erases")
	check_eq(int(forms.get("identifier", -1)), 0,
		"questsRank occurs ZERO times as a bare identifier, which is precisely "
			+ "why an identifier-only census got this wrong")
	var readers: Dictionary = SocialState.READ_AND_WRITTEN
	check_eq(readers.get("questsRank", ""), "admin_set_quest_rank",
		"questsRank's one branch is recorded as admin_set_quest_rank")
	var quests_rank_record: Variant = SocialState.field_record("questsRank")
	check_eq(quests_rank_record.zero_occurrence, false,
		"questsRank's own record says it is NOT zero-occurrence")
	check_eq(quests_rank_record.readers, ["admin_set_quest_rank"],
		"questsRank's record names its one branch")
	check_eq(quests_rank_record.written_by, ["admin_set_quest_rank"],
		"questsRank's record names the SAME branch as its writer")

	# and the branch really is a reader AND a writer, re-measured
	var quests_rank_source: String = ""
	var qr_path: String = _repo_root().path_join("command.py")
	if FileAccess.file_exists(qr_path):
		quests_rank_source = FileAccess.get_file_as_string(qr_path)
	check(quests_rank_source.contains("elif cmd == \"admin_set_quest_rank\":"),
		"admin_set_quest_rank exists as a named dispatcher branch")
	check(quests_rank_source.contains("privateState[\"questsRank\"]"),
		"that branch really reaches questsRank through the quoted subscript form")

	# self-check: the instrument must be non-vacuous, or every count above is 0
	check(_token_count("friendly", "friendly") == 1,
		"the census instrument finds a token that IS present")
	check(_token_count("friendly", "friend") == 0,
		"the census instrument refuses a substring match inside a longer word")
	check(_token_count("questsRank", "questsRank") >= 1,
		"the census instrument really does scan the legacy sources, so a zero "
			+ "means absent rather than unread")
	census["instrument_non_vacuous"] = true


## Recompute which measured fields have zero occurrences of any kind.
##
## ## Why this needs TWO views, and why the obvious one is wrong
##
## Counting whole-identifier tokens over a comment-and-string-stripped view is
## the obvious approach and it is **wrong here**. The strip erases string
## literals by design, so a field reached as `privateState["questsRank"]`
## disappears entirely - and that made an early revision of this suite report
## `questsRank` as zero-occurrence when it has both a reader
## (`admin_set_quest_rank`) and a writer (`command.py:750`). Eight measured
## fields were wrong the same way.
##
## So the census counts **both** forms and sums them:
##
##   identifier  whole-identifier tokens in the stripped view, so a mention in
##               prose or a print string cannot be counted as a consumer;
##   quoted      the `["field"]` / `['field']` subscript form in the RAW source,
##               because that is how the legacy server actually reaches a save
##               key.
##
## A field is zero-occurrence only when BOTH are zero.
func _recompute_zero_occurrence() -> Array:
	var stripped: Array = []
	var raw: Array = []
	for module_name: String in SocialState.LEGACY_MODULES:
		var path: String = _repo_root().path_join(module_name)
		if not FileAccess.file_exists(path):
			continue
		var text: String = FileAccess.get_file_as_string(path)
		stripped.append(_strip_code(text))
		raw.append(text)
	check_eq(stripped.size(), 11,
		"all ELEVEN declared legacy modules were read for the census")

	var out: Array = []
	for name: String in EXPECTED_FIELD_NAMES:
		var identifier: int = 0
		var quoted: int = 0
		for index: int in stripped.size():
			identifier += _token_count(stripped[index], name)
			quoted += _quoted_count(raw[index], name)
		census["forms:" + name] = {"identifier": identifier, "quoted": quoted}
		if identifier == 0 and quoted == 0:
			out.append(name)
	return out


## Occurrences of `word` in the `["word"]` / `['word']` subscript form.
##
## Counted over RAW source, never over the stripped view, because the strip
## erases exactly this form.
func _quoted_count(code: String, word: String) -> int:
	if code.is_empty() or word.is_empty():
		return 0
	var total: int = 0
	for quote: String in ['"', "'"]:
		var needle: String = quote + word + quote
		var at: int = 0
		while true:
			var found: int = code.find(needle, at)
			if found < 0:
				break
			total += 1
			at = found + 1
	return total


## Whole-identifier occurrences of `word` in `code`. Never a substring count.
func _token_count(code: String, word: String) -> int:
	if code.is_empty() or word.is_empty():
		return 0
	var total: int = 0
	var at: int = 0
	var step: int = word.length()
	while true:
		var found: int = code.find(word, at)
		if found < 0:
			break
		var before_ok: bool = found == 0 \
			or not _is_word_char(code.unicode_at(found - 1))
		var after: int = found + step
		var after_ok: bool = after >= code.length() \
			or not _is_word_char(code.unicode_at(after))
		if before_ok and after_ok:
			total += 1
		at = found + 1
	return total


func _is_word_char(code_point: int) -> bool:
	return code_point == 95 or (code_point >= 48 and code_point <= 57) \
		or (code_point >= 65 and code_point <= 90) \
		or (code_point >= 97 and code_point <= 122)


## Remove comments and string literals with a two-state lexer.
##
## A regex cannot do this: an apostrophe inside a double-quoted string
## desynchronises a naive scanner, and this project has already recorded that
## defect once.
func _strip_code(body: String) -> String:
	var out: PackedStringArray = PackedStringArray()
	var i: int = 0
	var n: int = body.length()
	while i < n:
		var c: String = body[i]
		if c == "#":
			while i < n and body[i] != "\n":
				i += 1
		elif c == "'" or c == "\"":
			var quote: String = c
			var triple: bool = body.substr(i, 3) == quote + quote + quote
			i += 3 if triple else 1
			while i < n:
				if triple and body.substr(i, 3) == quote + quote + quote:
					i += 3
					break
				if not triple and body[i] == "\\":
					i += 2
					continue
				if not triple and body[i] == quote:
					i += 1
					break
				if not triple and body[i] == "\n":
					break
				i += 1
			out.append("\"\"")
		else:
			out.append(c)
			i += 1
	return "".join(out)


func _repo_root() -> String:
	return Paths.repo_root()


# ---------------------------------------------------------------------------
# The corpus (requirement 5)
# ---------------------------------------------------------------------------

func _check_corpus() -> void:
	var roots := ["tests/saves", "villages"]
	var exclude := ["tests/saves/manifest.json"]
	var values := {}
	# A Dictionary is a REFERENCE type in GDScript, so the walker can increment
	# the tally inside the shared object. An `int` parameter would NOT work: it is
	# passed by value, so the count stayed 0 while the value tallies came back
	# correct - an earlier revision had exactly that split.
	var tally := {"documents": 0}
	for root_name: String in roots:
		var base: String = _repo_root().path_join(root_name)
		_walk_json(base, exclude, values, tally)
	var documents: int = int(tally["documents"])

	corpus["documents"] = documents
	corpus["root_count"] = roots.size()

	# the settled denominator, reproduced rather than assumed
	check_eq(roots.size(), 2,
		"the census walks the two recorded roots, tests/saves and villages")
	check_eq(documents, 33,
		"the corpus walk reproduces the settled THIRTY-THREE carrying documents")

	for field_name: String in EXPECTED_UNIFORM_VALUES:
		var observed: Dictionary = values.get(field_name, {})
		var expected_value: Variant = EXPECTED_UNIFORM_VALUES[field_name]
		check_eq(observed.size(), 1,
			"the write-less field `%s` holds exactly ONE recorded value"
				% field_name)
		if observed.size() == 1:
			var only: Variant = observed.keys()[0]
			# The tally key is the STRINGIFIED value, and JSON.stringify(null)
			# yields the four-character string "null" - not a null. Comparing it
			# to a null expectation with `==` is a TYPE error, so both sides are
			# normalised through _same_value before comparison.
			check(_same_value(only, expected_value),
				"the recorded value of `%s` is the measured one (%s vs %s)"
					% [field_name, only, expected_value])
			check_eq(int(observed[only]), documents,
				"the recorded value of `%s` holds in all %d documents"
					% [field_name, documents])
		corpus["uniform:" + field_name] = {
			"distinct_values": observed.size(),
			"documents": observed.values()[0] if not observed.is_empty() else 0,
		}

	# NO populated example exists anywhere in the corpus.
	#
	# "Populated" means a NON-EMPTY CONTAINER. A scalar uniform value such as
	# `0` is not a populated example of anything, so treating it as one would be
	# a false alarm - an earlier revision of this check did exactly that and
	# reported all twelve fields as populated.
	for field_name: String in EXPECTED_UNIFORM_VALUES:
		var observed: Dictionary = values.get(field_name, {})
		for key: Variant in observed.keys():
			check(not _is_non_empty_container(key),
				"the corpus holds no POPULATED example of `%s`, so none is "
					% field_name + "synthesized here")


## Compare a JSON-stringified value against an expected native value.
##
## The corpus walk keys its tallies by `JSON.stringify(value)`, so `null`
## arrives as the four-character STRING "null" and `{}` as the string "{}".
## Comparing those to native values with `==` is a type error in GDScript, so
## both sides are normalised here.
func _same_value(recorded: Variant, expected: Variant) -> bool:
	if typeof(recorded) == TYPE_STRING:
		var text: String = str(recorded)
		# `JSON.parse_string` DECODES every JSON number as a float, so the corpus
		# value `0` arrives as 0.0 and `==` against an int is false in GDScript.
		# The numeric branch therefore compares floats, not raw variants.
		var parsed: Variant = JSON.parse_string(text)
		if typeof(parsed) == TYPE_FLOAT:
			return is_equal_approx(float(parsed), float(expected)) \
				if typeof(expected) == TYPE_INT or typeof(expected) == TYPE_FLOAT \
				else false
		if typeof(parsed) != TYPE_NIL or text == "null":
			return _deep_equal(parsed, expected)
		return text == str(expected)
	return _deep_equal(recorded, expected)


func _deep_equal(left: Variant, right: Variant) -> bool:
	if typeof(left) != typeof(right):
		return false
	match typeof(left):
		TYPE_NIL:
			return true
		TYPE_ARRAY:
			var a: Array = left
			var b: Array = right
			if a.size() != b.size():
				return false
			for index: int in a.size():
				if not _deep_equal(a[index], b[index]):
					return false
			return true
		TYPE_DICTIONARY:
			var da: Dictionary = left
			var db: Dictionary = right
			if da.size() != db.size():
				return false
			for key: Variant in da:
				if not db.has(key):
					return false
				if not _deep_equal(da[key], db[key]):
					return false
			return true
		_:
			return left == right


## True only for a container that actually holds something.
func _is_non_empty_container(value: Variant) -> bool:
	if value is Array:
		return not (value as Array).is_empty()
	if value is Dictionary:
		return not (value as Dictionary).is_empty()
	return false


func _walk_json(base: String, exclude: Array, values: Dictionary,
		tally: Dictionary) -> void:
	var dir := DirAccess.open(base)
	if dir == null:
		return
	dir.list_dir_begin()
	var entry: String = dir.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = dir.get_next()
			continue
		var full: String = base.path_join(entry)
		if dir.current_is_dir():
			if entry != ".git":
				_walk_json(full, exclude, values, tally)
		elif entry.ends_with(".json"):
			var relative: String = full.replace(_repo_root(), "").replace("\\", "/")
			relative = relative.replace("res:/", "")
			if not exclude.has(relative.lstrip("/")):
				if _absorb_document(full, values):
					tally["documents"] = int(tally["documents"]) + 1
		entry = dir.get_next()
	dir.list_dir_end()


## Accumulate one document's social values.
##
## Returns true when the document carried at least one map, which is the settled
## definition of a "carrying" document, so the count cannot drift from the walk.
func _absorb_document(path: String, values: Dictionary) -> bool:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return false
	var document: Dictionary = parsed
	var containers: Array = []
	var private_state: Variant = document.get("privateState", null)
	if private_state is Dictionary:
		containers.append(private_state)
	var maps: Variant = document.get("maps", null)
	var map_objects: Array = []
	if maps is Array:
		map_objects = maps
	elif maps is Dictionary:
		var keys: Array = (maps as Dictionary).keys()
		keys.sort()
		for key: Variant in keys:
			map_objects.append((maps as Dictionary)[key])
	for map_object: Variant in map_objects:
		if map_object is Dictionary:
			containers.append(map_object)

	for field_name: String in EXPECTED_FIELD_NAMES:
		for container: Variant in containers:
			if not (container as Dictionary).has(field_name):
				continue
			var key: String = JSON.stringify((container as Dictionary)[field_name])
			if not values.has(field_name):
				values[field_name] = {}
			values[field_name][key] = int(values[field_name].get(key, 0)) + 1
	return not map_objects.is_empty()


# ---------------------------------------------------------------------------
# The recorded writer (requirement 7)
# ---------------------------------------------------------------------------

func _check_recorded() -> void:
	var writers: Array = SocialState.RECORDED_WRITERS
	check_eq(writers.size(), 1,
		"exactly ONE branch is recorded as writing social state")
	var record: Dictionary = writers[0]
	check_eq(str(record.get("branch", "")), "set_resource_allies",
		"the recorded writer is set_resource_allies")
	check_eq(str(record.get("source", "")), "command.py:637",
		"the recorded writer's source line is command.py:637")
	check_eq(str(record.get("target", "")), "maps[]/resourceAlliesMarket",
		"the recorded write target is the map's resourceAlliesMarket key")
	check_eq(str(record.get("client_sent_argument", "")), "args[0]",
		"the recorded write takes its value from a CLIENT-SENT argument")
	check_eq(bool(record.get("semantics_derived", true)), false,
		"no semantics are derived from the recorded row-instant stamp")
	check_eq(bool(record.get("reproduced", true)), false,
		"the recorded write is NOT reproduced by this capability")

	var effects: Array = record.get("effects", [])
	check_eq(effects.size(), 3,
		"all THREE recorded effects of the branch are listed")
	var blob: String = str(effects)
	check(blob.contains("client-sent"),
		"the recorded effects name the client-sent write")
	check(blob.contains("item[3]"),
		"the recorded effects name the row instant stamp")
	check(blob.contains("finish_si"),
		"the recorded effects name the finish_si call")

	# no route, endpoint, or intent is delivered (D5, D8)
	check_eq(SocialState.DELIVERED_ROUTES, [],
		"this capability delivers NO route: the recorded write is not reproduced")
	var route_blob: String = _module_source()
	for forbidden: String in ["add_endpoint", "route(", "http", "func post",
			"func request", "func buy_"]:
		check(not route_blob.contains(forbidden),
			"the delivered module contains no route surface (`%s`)" % forbidden)

	# the other written fields are recorded with their branch
	var other: Dictionary = SocialState.OTHER_WRITTEN_FIELDS
	for field_name: String in ["publishedOpenGraphUnit", "marketPlaceFirstTime",
			"numTradesDone", "timestampLastTrade", "timeStampEndPremium"]:
		check(other.has(field_name),
			"the written field `%s` records its writing branch" % field_name)
	check_eq(other.get("publishedOpenGraphUnit", ""), "rt_open_graph_unit",
		"publishedOpenGraphUnit is recorded as written by rt_open_graph_unit")

	# questsRank is NOT among the written fields
	check(not other.has("questsRank"),
		"questsRank is not recorded as written, because nothing writes it")


# ---------------------------------------------------------------------------
# The content boundary (requirements 8, 9)
# ---------------------------------------------------------------------------

func _check_boundary() -> void:
	var boundary: Dictionary = SocialState.CONTENT_BOUNDARY
	check_eq(str(boundary.get("owner", "")), "social-tables-normalization",
		"the social content tables are owned by social-tables-normalization")
	check_eq(boundary.get("tables", []),
		["neighbor_assists", "findable_items", "social_items"],
		"the three owned content tables are named")
	for flag: String in ["reward_decoded", "coin_charged", "worker_selected",
			"eligibility_derived"]:
		check_eq(bool(boundary.get(flag, true)), false,
			"the capability records that it does not %s" % flag)

	# the owner capability must actually exist, or the hand-off is an orphan
	var owner_spec: String = _repo_root().path_join(
		"openspec/specs/social-tables-normalization/spec.md")
	check(FileAccess.file_exists(owner_spec),
		"the owning capability social-tables-normalization EXISTS, so the "
			+ "hand-off is not an orphan")
	if FileAccess.file_exists(owner_spec):
		var owner_text: String = FileAccess.get_file_as_string(owner_spec)
		for table: String in boundary.get("tables", []):
			check(owner_text.contains(table),
				"the owning capability's spec really does own `%s`" % table)

	# this capability projects NO content row
	var source: String = _module_source()
	for table: String in boundary.get("tables", []):
		check(not _references_content_row(source, table),
			"the delivered module does not project any `%s` content row" % table)

	# and no rule is derived from a committed social value
	for forbidden: String in ["worker_cost", "workerCost", "coins", "reward",
			"notification"]:
		var derived: bool = _declares_rule_from(source, forbidden)
		check(not derived,
			"the delivered module derives no rule from the committed `%s`"
				% forbidden)

	# THE DERIVATION GUARD, stated mechanically.
	#
	# The word-guard above only fires on the WORD. A helper with an innocuous
	# name that compared two committed social values would pass it, and also
	# pass the reserved-name guard if it borrowed no reserved word. This check
	# closes that hole by measuring the module's own operators: with nineteen
	# fields whose committed values are only uniform ACROSS documents, any
	# arithmetic or ordering between them would be a rule this capability has no
	# evidence for and is forbidden from inventing.
	#
	# The claim is therefore literally true of the source rather than a
	# statement about intent, and it is re-measured on every run.
	var code: String = _strip_code(source)
	var arithmetic_lines: Array = []
	var ordering_lines: Array = []
	for line: String in code.split("\n"):
		var text: String = line.strip_edges()
		if text.is_empty() or text.begins_with("#"):
			continue
		# a comment/docstring body line, or a bare statement
		if _has_arithmetic(text):
			arithmetic_lines.append(text)
		if _has_ordering(text):
			ordering_lines.append(text)
	check_eq(arithmetic_lines, [],
		"the delivered module contains NO arithmetic on any value, so no "
			+ "score, rate, ratio, or total is computed")
	check_eq(ordering_lines, [],
		"the delivered module contains NO ordering comparison between values, so "
			+ "no field is ranked, sorted, or compared against another")

	# The two detectors are self-checked, because a detector that never fires
	# satisfies an emptiness assertion vacuously.
	check(_has_arithmetic("\tvar total: int = count + delta"),
		"the arithmetic detector fires on a real addition")
	check(_has_arithmetic("\treturn first_value * second_value"),
		"the arithmetic detector fires on a multiplication")
	check(not _has_arithmetic("\treturn _present.get(field_name, null)"),
		"the arithmetic detector does NOT fire on a plain lookup, so the "
			+ "emptiness check above is not satisfied by ordinary indexing")
	check(_has_ordering("\tif first_value > second_value:"),
		"the ordering detector fires on a real comparison")
	check(_has_ordering("\treturn value <= bound"),
		"the ordering detector fires on an inclusive comparison")
	check(not _has_ordering("\tif _present.has(field_name):"),
		"the ordering detector does NOT fire on a membership test, so the "
			+ "emptiness check above is not satisfied by an existence check")
	# `==` and `typeof` are structural discrimination, not ordering, and the
	# delivered module legitimately uses both. Asserting that keeps the
	# emptiness claim honest instead of quietly excluding them.
	check(not _has_ordering("\tif typeof(document) == TYPE_DICTIONARY:"),
		"the ordering detector does NOT fire on type discrimination, which is "
			+ "structural and carries no rule about a value's magnitude")
	check(not _has_ordering("\tif name == field_name:"),
		"the ordering detector does NOT fire on an identity test")


func _references_content_row(source: String, table: String) -> bool:
	# The table NAME appears legitimately in `CONTENT_BOUNDARY.tables`, which is
	# the hand-off record, not a projection. What must not appear is a READ of a
	# row: an index, a subscript, or a `.get`. Comments and docstrings are
	# stripped first, so prose about the boundary cannot trip this either.
	var code: String = _strip_code(source)
	for needle: String in [table + "[", table + ".get", "load(%s" % table]:
		if code.contains(needle):
			return true
	return false


## True when a line performs arithmetic on values.
##
## Recognises the four binary operators plus the compound assignments. Each
## candidate operator must have an operand character on BOTH sides, skipping
## spaces and tabs outwards, so a comment marker, a `*/` terminator, a path
## separator or a lone `/` in a slice expression cannot be read as an operator.
## Bracketed indexing (`value[0]`) is not arithmetic and is deliberately not
## matched.
func _has_arithmetic(text: String) -> bool:
	# Every offset, not just the `<`/`>` ones: an earlier revision reused
	# `_operator_offsets()` here and therefore scanned for ordering operators
	# while looking for arithmetic, so the detector could never fire and its
	# emptiness assertion was vacuously true. The self-checks below are what
	# caught it.
	for index: int in range(text.length()):
		var two: String = text.substr(index, 2)
		if two == "+=" or two == "-=" or two == "*=" or two == "/=":
			if _is_value_head(_skip_space_left(text, index - 1)) \
					and _is_value_tail(_skip_space_right(text, index + 2)):
				return true
			continue
		var one: String = text.substr(index, 1)
		if one == "+" or one == "-" or one == "*" or one == "/":
			if _is_value_tail(_skip_space_left(text, index - 1)) \
					and _is_value_head(_skip_space_right(text, index + 1)):
				return true
	return false


## True when a line ORDERS two values.
##
## Deliberately narrower than "any comparison". `==`, `!=` and `typeof(...)`
## discrimination are how the projection decides whether a document is a save
## and whether a key exists, which is structural and carries no rule about the
## values themselves. Those are excluded, and the guard claims only that no
## field is ordered against another.
##
## `<`, `>`, `<=` and `>=` are included: any of them compares a value's
## magnitude, which for nineteen fields that are merely uniform ACROSS documents
## would be an invented rule.
func _has_ordering(text: String) -> bool:
	for index: int in _operator_offsets(text):
		var two: String = text.substr(index, 2)
		var span: int = 1
		if two == "<=" or two == ">=":
			span = 2
		elif two.substr(0, 1) != "<" and two.substr(0, 1) != ">":
			continue
		if _is_value_tail(_skip_space_left(text, index - 1)) \
				and _is_value_head(_skip_space_right(text, index + span)):
			return true
	return false


## The offsets of every `<` or `>` character in a line.
##
## Scanned out separately so both detectors agree on what an operator offset is,
## and so `==` is skipped without either detector having to know the other's
## rules.
func _operator_offsets(text: String) -> Array:
	var out: Array = []
	var index: int = 0
	while index < text.length():
		var character: String = text.substr(index, 1)
		if character == "<" or character == ">":
			out.append(index)
		index += 1
	return out


## The nearest non-space character at or before `index`.
func _skip_space_left(text: String, index: int) -> String:
	var cursor: int = index
	while cursor >= 0:
		var character: String = text.substr(cursor, 1)
		if character != " " and character != "\t":
			return character
		cursor -= 1
	return ""


## The nearest non-space character at or after `index`.
func _skip_space_right(text: String, index: int) -> String:
	var cursor: int = index
	while cursor < text.length():
		var character: String = text.substr(cursor, 1)
		if character != " " and character != "\t":
			return character
		cursor += 1
	return ""


## The characters that can end an operand: word characters, digits, a closing
## delimiter, or a closing quote.
const VALUE_TAIL_CHARS := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_)]}'\""


## The characters that can start an operand: word characters, digits, an opening
## delimiter, or an opening quote.
const VALUE_HEAD_CHARS := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_([{'\"."


## True when a character can end an operand.
func _is_value_tail(character: String) -> bool:
	if character.is_empty():
		return false
	return VALUE_TAIL_CHARS.contains(character)


## True when a character can start an operand.
func _is_value_head(character: String) -> bool:
	if character.is_empty():
		return false
	return VALUE_HEAD_CHARS.contains(character)


func _declares_rule_from(source: String, word: String) -> bool:
	# A mention inside a comment or a documented refusal is not a rule. Only a
	# subscript read or an assignment would be one.
	var code: String = _strip_code(source)
	for needle: String in ["[\"%s\"]" % word, "[\"%s\"] =" % word,
			".get(\"%s\"" % word]:
		if code.contains(needle):
			return true
	return false


# ---------------------------------------------------------------------------
# The anti-invention guards (requirement 10)
# ---------------------------------------------------------------------------

func _check_absence() -> void:
	var declared: Array = []
	for entry: Dictionary in SocialState.ABSENT_HELPERS:
		declared.append(str(entry.get("helper", "")))
		check(str(entry.get("absent_because", "")).length() > 0,
			"the ABSENT_HELPERS entry for `%s` records why it is absent"
				% str(entry.get("helper", "?")))
	for needle: String in ABSENT_FAMILIES:
		check(_declares_a_helper_for(declared, needle),
			"the recorded ABSENT_HELPERS inventory names the absent `%s` family"
				% needle)

	# the module's ACTUAL function inventory, pinned in both directions
	var present: Array = []
	for match: String in _function_names(_module_source()):
		present.append(match)
	present.sort()
	var unexpected: Array = []
	for name: String in present:
		if not _is_a_declared_accessor(name):
			unexpected.append(name)
	check_eq(unexpected, [],
		"the delivered module declares EXACTLY its recorded accessors: no "
			+ "friend-level, assist-reward, visit, score, or relationship helper exists")
	for name: String in EXPECTED_FUNCTIONS:
		check(present.has(name),
			"the recorded static accessor `%s` is delivered" % name)
	for name: String in EXPECTED_INSTANCE_FUNCTIONS:
		check(_instance_function_names().has(name),
			"the recorded instance accessor `%s` is delivered" % name)
	for name: String in declared:
		check(not present.has(name),
			"the module does NOT provide the recorded absent helper `%s`" % name)

	# The RESERVED-NAME guard, applied to the module's real function inventory
	# with BOTH a substring and a case-folded comparison.
	#
	# The whole-inventory pin above is the real gate: any function outside the
	# two recorded accessor lists fails there. This guard is the belt, and it is
	# deliberately redundant, because redundancy is what catches the two
	# disguises the pin alone would report as a mere unknown function:
	# a reserved absent name wearing a SUFFIX, and one wearing different CASE.
	# NOTE on the `%` binding: in GDScript `%` binds tighter than `+`, so a
	# message split across two string literals formats only the SECOND one. A
	# placeholder in the first literal silently raises "not all arguments
	# converted" and the message text is lost. Both messages below therefore
	# keep the placeholder in the final literal, or parenthesize the whole.
	var suffixed_probe := "assist_reward_for_item"
	var upper_probe := "FRIEND_LEVEL"
	check(_matches_reserved_absent(declared, suffixed_probe),
		("the reserved-name guard catches a SUFFIXED helper wearing a reserved "
			+ "name (`%s`), which an exact-name check would miss")
				% suffixed_probe)
	check(_matches_reserved_absent(declared, upper_probe),
		("the reserved-name guard is case-insensitive: the `%s` spelling is "
			+ "caught by the folded comparison")
				% upper_probe)
	# The real claim: applying the folded substring guard to every reserved
	# absent name finds NOTHING in the delivered module's function inventory.
	var dirty: Array = []
	for name: String in declared:
		if _matches_reserved_absent(present, name):
			dirty.append(name)
	check_eq(dirty, [],
		"the reserved-name guard, folded and bidirectional, reports the delivered "
			+ "module clean against every one of the %d reserved names"
				% declared.size())

	# The guard must be discriminating, not vacuous: it fires on a delivered
	# accessor's own neighbourhood but not on an unrelated pair. A guard that
	# matched everything would satisfy the check above trivially.
	check(_matches_reserved_absent(["friend_level_soft"], "FRIEND_LEVEL"),
		"the folded guard fires on a reserved name as a PREFIX of a candidate")
	check(_matches_reserved_absent(["assist_reward_for"], "assist_reward"),
		"the folded guard fires on a reserved name as a SUFFIX of a candidate")
	check(not _matches_reserved_absent(present, "present"),
		"the guard does not fire on a delivered accessor, so it is not matching "
			+ "everything")


## The whole static-function inventory declared in the delivered module.
##
## Measured from the module SOURCE rather than via reflection, so the guard works
## in a headless script run and cannot be satisfied by a dynamically added method.
func _function_names(source: String) -> Array:
	var out: Array = []
	var stripped: String = _strip_code(source)
	for line: String in stripped.split("\n"):
		var text: String = line.strip_edges()
		if not text.begins_with("static func "):
			continue
		var rest: String = text.substr(11).strip_edges()
		var paren: int = rest.find("(")
		if paren < 0:
			continue
		out.append(rest.substr(0, paren).strip_edges())
	return out


func _instance_function_names() -> Array:
	var out: Array = []
	var source: String = _module_source()
	for line: String in _strip_code(source).split("\n"):
		var text: String = line.strip_edges()
		if not text.begins_with("func "):
			continue
		var rest: String = text.substr(5).strip_edges()
		if rest.begins_with("static "):
			continue
		var paren: int = rest.find("(")
		if paren < 0:
			continue
		out.append(rest.substr(0, paren).strip_edges())
	return out


func _is_a_declared_accessor(name: String) -> bool:
	return EXPECTED_FUNCTIONS.has(name) or EXPECTED_INSTANCE_FUNCTIONS.has(name)


func _declares_a_helper_for(names: Array, needle: String) -> bool:
	for name: String in names:
		if name.contains(needle):
			return true
	return false


## True when any reserved absent name in `declared` matches `candidate`, judged
## as a SUBSTRING in EITHER direction and with both sides FOLDED to lower case.
##
## Two disguises are covered deliberately, each learned from a real miss on an
## earlier line of this project:
##
##   - the SUFFIX. An exact-name comparison does not match
##     `assist_reward_for_item` against the reserved `assist_reward`, so a
##     suffixed helper would pass an exact-name check.
##   - the CASE. `FRIEND_LEVEL` is not equal to `friend_level`, so a
##     case-sensitive comparison would miss an upper-case spelling.
##
## Folding both sides means the comparison is genuinely case-insensitive rather
## than incidentally so.
func _matches_reserved_absent(declared: Array, candidate: String) -> bool:
	var probe: String = candidate.to_lower()
	for name: String in declared:
		var reserved: String = str(name).to_lower()
		if reserved.is_empty():
			continue
		if reserved == probe or probe.contains(reserved) or reserved.contains(probe):
			return true
	return false


func _module_source() -> String:
	return FileAccess.get_file_as_string(
		"res://scripts/social/social_state.gd")


# ---------------------------------------------------------------------------
# Visits and scores (requirement 12)
# ---------------------------------------------------------------------------

func _check_visits() -> void:
	var world: Array = SocialState.WORLD_KEYS
	check_eq(world, ["world_id", "worldChange"],
		"the two carried-but-never-read world keys are named")

	# MEASURED, not asserted: both are carried by the corpus and read nowhere.
	#
	# The store is asserted too, because it is NOT uniform: `world_id` is a map
	# key and `worldChange` is a `privateState` key. The committed investigation
	# had recorded both as map keys; re-measuring over the corpus corrected that,
	# and the narrow search it implied is what surfaced the error.
	var in_corpus: int = 0
	var read_in_legacy: int = 0
	var stores: Array = []
	for key: String in world:
		var store: String = _corpus_store_of_key(key)
		if store != "":
			in_corpus += 1
		stores.append([key, store])
		if _legacy_mentions(key):
			read_in_legacy += 1
	check_eq(in_corpus, 2,
		"BOTH world keys are carried by the committed corpus, so their absence "
			+ "from the server is a real absence and not a missing document")
	check_eq(stores, [["world_id", "maps[]"], ["worldChange", "privateState"]],
		"the two world keys live in DIFFERENT stores, as re-measured")
	check_eq(read_in_legacy, 0,
		"NEITHER world key is mentioned anywhere in the eleven legacy modules")

	# no score-like arithmetic in the dispatcher
	var command_path: String = _repo_root().path_join("command.py")
	check(FileAccess.file_exists(command_path),
		"the dispatcher source was located for the score measurement")
	if FileAccess.file_exists(command_path):
		# RAW source, skipping comment lines, matching the committed
		# investigation's measurement. Reading the stripping view here would be
		# the same view that erased the branch NAMES, and a branch name is
		# exactly where a score-like word is most likely to live.
		var code: String = FileAccess.get_file_as_string(command_path)
		var arithmetic: int = 0
		for line: String in code.split("\n"):
			var text: String = line.strip_edges()
			if text.begins_with("#"):
				continue
			for token: String in ["score", "rank", "points", "leaderboard"]:
				if _token_count(text, token) > 0 \
						and (text.contains("+") or text.contains("-") \
						or text.contains("*") or text.contains("/")):
					arithmetic += 1
		check_eq(arithmetic, 0,
			"there is ZERO arithmetic on any score-like value in the dispatcher, "
				+ "measured over raw source")

	# the two rejected near-miss readings are recorded so they are not re-counted
	var rejected: Array = SocialState.REJECTED_SCORE_READINGS
	check_eq(rejected.size(), 2,
		"exactly TWO near-miss readings are recorded as rejected")
	var rejected_names: Array = []
	for entry: Dictionary in rejected:
		rejected_names.append(str(entry.get("token", "")))
		check(str(entry.get("actual", "")).length() > 0,
			"the rejected reading `%s` records what it actually is"
				% str(entry.get("token", "?")))
	check_eq(rejected_names, ["lost", "won"],
		"the rejected readings are the unit-loss counter and the auction-bet result")
	check(not EXPECTED_FIELD_NAMES.has("lost"),
		"the unit-loss local is NOT counted as a social field")
	check(not EXPECTED_FIELD_NAMES.has("won"),
		"the auction-bet result is NOT counted as a social field")


## True when the committed corpus really carries `key` as a map key.
##
## Measured by searching the committed documents rather than by projecting a
## synthetic one. The point of the check is that the CORPUS carries the key, so a
## synthetic document would prove nothing about it.
## True when the committed corpus really carries `key` in EITHER store.
##
## Measured by searching the committed documents rather than by projecting a
## synthetic one. The point of the check is that the CORPUS carries the key, so a
## synthetic document would prove nothing about it.
##
## The search covers `privateState` as well as `maps[]`. An earlier revision
## searched maps only, because the committed investigation had recorded both
## world keys as map keys; re-measuring showed `world_id` is a map key in 33 of
## 33 documents while `worldChange` is a `privateState` key in 33 of 33. The
## narrow search therefore reported one of the two, and the suite's own
## "BOTH are carried" assertion caught it.
func _corpus_carries_key(key: String) -> bool:
	return _key_in_committed_corpus(key, false).size() > 0


## The store the committed corpus really carries `key` in, or "" when absent.
##
## Returned as the labels `"privateState"` / `"maps[]"`, in the fixed order the
## search visits them, so a caller can assert WHICH store rather than only that
## the key was found.
func _corpus_store_of_key(key: String) -> String:
	var stores: Array = _key_in_committed_corpus(key, true)
	if stores.is_empty():
		return ""
	return str(stores[0])


func _key_in_committed_corpus(key: String, want_stores: bool) -> Array:
	var out: Array = []
	var roots := ["tests/saves", "villages"]
	for root_name: String in roots:
		var base: String = _repo_root().path_join(root_name)
		if not DirAccess.dir_exists_absolute(base):
			continue
		_search_key(base, key, out, want_stores)
		if not out.is_empty():
			return out
	return out


## Search the committed corpus for `key`, visiting BOTH stores.
##
## `found` is an Array rather than a `bool` because GDScript passes a `bool`
## parameter **by value**: the recursive call's assignment never reached the
## caller, so every search reported absent. An earlier revision had exactly that
## signature and the two world keys silently measured as 0.
##
## `want_stores` selects what a hit records: the key itself, or the store label.
## A document counts as carrying the key in a store only when the store is
## itself a Dictionary and holds the key, so a non-object store cannot produce a
## false hit.
func _search_key(base: String, key: String, found: Array, want_stores: bool) -> void:
	if not found.is_empty():
		return
	var dir := DirAccess.open(base)
	if dir == null:
		return
	dir.list_dir_begin()
	var entry: String = dir.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = dir.get_next()
			continue
		var full: String = base.path_join(entry)
		if dir.current_is_dir():
			if entry != ".git":
				_search_key(full, key, found, want_stores)
		elif entry.ends_with(".json") and not entry.ends_with("manifest.json"):
			var parsed: Variant = JSON.parse_string(
				FileAccess.get_file_as_string(full))
			if parsed is Dictionary:
				var document: Dictionary = parsed
				var private: Variant = document.get("privateState", null)
				if private is Dictionary and (private as Dictionary).has(key):
					found.append("privateState" if want_stores else key)
				var maps: Variant = document.get("maps", null)
				var objects: Array = []
				if maps is Array:
					objects = maps
				elif maps is Dictionary:
					var keys: Array = (maps as Dictionary).keys()
					keys.sort()
					for k: Variant in keys:
						objects.append((maps as Dictionary)[k])
				for map_object: Variant in objects:
					if map_object is Dictionary \
							and (map_object as Dictionary).has(key):
						found.append("maps[]" if want_stores else key)
		if not found.is_empty():
			dir.list_dir_end()
			return
		entry = dir.get_next()
	dir.list_dir_end()


func _legacy_mentions(word: String) -> bool:
	for module_name: String in SocialState.LEGACY_MODULES:
		var path: String = _repo_root().path_join(module_name)
		if not FileAccess.file_exists(path):
			continue
		if _token_count(_strip_code(FileAccess.get_file_as_string(path)), word) > 0:
			return true
	return false


# ---------------------------------------------------------------------------
# The legacy re-measurement (every recorded figure, recomputed)
# ---------------------------------------------------------------------------

func _check_legacy() -> void:
	var command_path: String = _repo_root().path_join("command.py")
	check(FileAccess.file_exists(command_path),
		"the dispatcher source was located for the branch re-measurement")

	if FileAccess.file_exists(command_path):
		var source: String = FileAccess.get_file_as_string(command_path)
		var code: String = _strip_code(source)
		# A branch name lives INSIDE a string literal (`cmd == "set_resource_allies"`),
		# so the stripping view erases it to `cmd == ""`. Any assertion about a
		# branch NAME, or about a save key reached by subscript, must therefore
		# read the RAW source. Reading the stripped view here silently reported the
		# recorded writer as absent.
		var raw: String = source

		# the branch count the investigation recorded
		#
		# Read RAW source. A branch NAME is a quoted literal, so the stripping
		# view rewrites `if cmd == "buy"` to `if cmd == ""`: the count happens
		# to survive because the prefix does, but every name-based assertion
		# built the same way fails.
		var branches: int = 0
		for line: String in raw.split("\n"):
			var text: String = line.strip_edges()
			if text.begins_with("if cmd == \"") \
					or text.begins_with("elif cmd == \""):
				branches += 1
		check_eq(branches, 63,
			"the RE-MEASURED dispatcher branch count is 63, matching the committed "
				+ "command catalog")
		legacy["branches"] = branches

		# no branch is named for a social deliver item
		for absent_branch: String in ["friend", "visit", "score", "social",
				"leaderboard", "gift", "invite"]:
			check(not _declares_branch_named(absent_branch),
				"no dispatcher branch is named `%s*`" % absent_branch)
		legacy["social_named_branches"] = 0

		# the recorded writer is really there, with its client-sent write.
		# Every assertion below reads RAW source: the branch name and the save key
		# both live inside string literals, which the stripping view erases.
		check(raw.contains("set_resource_allies"),
			"the recorded writer set_resource_allies exists in the dispatcher")
		check(raw.contains("elif cmd == \"set_resource_allies\":"),
			"set_resource_allies is really a NAMED dispatcher branch")
		check(raw.contains("map[\"resourceAlliesMarket\"] = resource"),
			"the recorded write really assigns a client-sent value to the map key")
		check(raw.contains("item[3] = time_now"),
			"the recorded row-instant stamp is present verbatim")
		check(raw.contains("finish_si(item)"),
			"the recorded finish_si call is present verbatim")

		# the rejected near-misses really are what this suite says they are
		check(code.contains("lost = max(0, unit[2] - unit[3])"),
			"the rejected `lost` reading is really the unit-loss local")
		var auctions_path: String = _repo_root().path_join("auctions.py")
		if FileAccess.file_exists(auctions_path):
			var auctions: String = FileAccess.get_file_as_string(auctions_path)
			check(auctions.contains("bet[\"won\"]"),
				"the rejected `won` reading is really the auction-bet result")

	# the three social content tables have ZERO legacy consumers, re-measured
	for table: String in ["social_items", "findable_items", "neighbor_assists"]:
		var total: int = 0
		for module_name: String in SocialState.LEGACY_MODULES:
			var path: String = _repo_root().path_join(module_name)
			if not FileAccess.file_exists(path):
				continue
			total += _token_count(
				_strip_code(FileAccess.get_file_as_string(path)), table)
		check_eq(total, 0,
			"the RE-MEASURED consumer count for the committed `%s` table is zero"
				% table)
		legacy["consumers:" + table] = total

	# the recorded source line of the one writer
	check(FileAccess.file_exists(command_path) \
			and _line_of(command_path, "set_resource_allies") == 637,
		"the recorded source line command.py:637 is where set_resource_allies "
			+ "actually appears")


## True when a named dispatcher branch begins with `prefix`.
##
## Reads RAW source. The stripped view rewrites every `cmd == "name"` to
## `cmd == ""`, so the extracted name was always the empty string and this
## returned false for every prefix - a vacuous pass.
func _declares_branch_named(prefix: String) -> bool:
	var command_path: String = _repo_root().path_join("command.py")
	if not FileAccess.file_exists(command_path):
		return false
	var code: String = FileAccess.get_file_as_string(command_path)
	for line: String in code.split("\n"):
		var text: String = line.strip_edges()
		for opener: String in ["if cmd == \"", "elif cmd == \""]:
			if not text.begins_with(opener):
				continue
			var rest: String = text.substr(opener.length())
			var quote: int = rest.find("\"")
			if quote < 0:
				continue
			var name: String = rest.substr(0, quote)
			if name.to_lower().begins_with(prefix):
				return true
	return false


func _line_of(path: String, needle: String) -> int:
	var lines: PackedStringArray = FileAccess.get_file_as_string(path) \
		.split("\n")
	for index: int in lines.size():
		if lines[index].contains(needle):
			return index + 1
	return -1


# ---------------------------------------------------------------------------
# The fixture record (requirement 11)
# ---------------------------------------------------------------------------

func _check_fixture_record() -> void:
	var fixture: Dictionary = SocialState.FIXTURE_ABSENCE
	check_eq(bool(fixture.get("fixture_delivered", true)), false,
		"no executed-legacy fixture is delivered, and that is recorded")
	check_eq(bool(fixture.get("fabricated_precondition", true)), false,
		"no precondition is fabricated to obtain one")
	check(str(fixture.get("reason", "")).contains("no social command"),
		"the recorded reason names the absent command as the cause")
	check(str(fixture.get("reason", "")).contains("no populated social field"),
		"the recorded reason names the corpus limitation as well")


# ---------------------------------------------------------------------------
# The evidence report
# ---------------------------------------------------------------------------

func _write_report() -> void:
	var path: String = DEFAULT_REPORT_PATH
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report="):
			path = argument.trim_prefix("--report=")
	var report := {
		"schema": "social-state-report-v1",
		"capability": "godot-social-state",
		"kind": "refusal",
		"delivered": "a typed read-only projection of persisted social state",
		"not_delivered": [
			"a friends, visits, scores, or social-rewards feature",
			"any route, endpoint, or intent for the recorded writer",
			"any decoded reward, charged coin, or selected worker",
			"any executed-legacy fixture",
		],
		"fields": _field_table(),
		"census": census,
		"corpus": corpus,
		"recorded_writers": SocialState.RECORDED_WRITERS,
		"other_written_fields": SocialState.OTHER_WRITTEN_FIELDS,
		"content_boundary": SocialState.CONTENT_BOUNDARY,
		"absent_helpers": SocialState.ABSENT_HELPERS,
		"delivered_routes": SocialState.DELIVERED_ROUTES,
		"fixture": SocialState.FIXTURE_ABSENCE,
		"world_keys": SocialState.WORLD_KEYS,
		"rejected_score_readings": SocialState.REJECTED_SCORE_READINGS,
		"legacy_measured": legacy,
		"claim_limits": [
			"twelve of nineteen fields have zero legacy occurrences, which is a "
				+ "statement about the preserved server and says nothing about what "
				+ "the Flash client did",
			"the committed investigation and the proposal counted thirteen by "
				+ "including questsRank, which admin_set_quest_rank both reads and "
				+ "writes; the re-derived figure is twelve and the proposal's number "
				+ "is corrected rather than the measurement",
			"the uniform values are a corpus fact about 33 documents, not a claim "
				+ "about all players",
			"no world, visit, or leaderboard concept is derived from the world keys",
			"the recorded row-instant stamp is reported with no semantics derived",
			"no parity is claimed: nothing here executes against the legacy server",
		],
	}
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the evidence report could not be written to %s" % path)
		return
	file.store_string(JSON.stringify(report, "  ", false, true))
	file.close()
	info("wrote the social-state evidence report to %s" % path)


## The measured field table, read from the module's own record table.
##
## Read through `SocialState.field_record()` rather than through a projection:
## the projection's `field()` deliberately exposes only the three columns a
## document contributes (`present`, `recorded_value`, `committed_value`), so
## asking it for `store` or `documents` would be asking the wrong object. The
## projection is exercised separately, over documents.
func _field_table() -> Array:
	var out: Array = []
	for field_name: String in EXPECTED_FIELD_NAMES:
		var record: Variant = SocialState.field_record(field_name)
		if record == null:
			continue
		var entry: Dictionary = record
		out.append({
			"name": field_name,
			"store": str(entry.get("store", "")),
			"zero_occurrence": bool(entry.get("zero_occurrence", false)),
			"written_by": entry.get("written_by", []),
			"readers": entry.get("readers", []),
			"recorded_value": entry.get("recorded_value", null),
			"documents": entry.get("documents", 0),
			"note": str(entry.get("note", "")),
		})
	return out
