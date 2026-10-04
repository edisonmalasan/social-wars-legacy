extends "res://tests/test_base.gd"
## Unit-experience suite (OpenSpec `godot-unit-experience` "No experience is
## awarded from a client amount, and no derivation exists" / "The committed
## per-unit experience field is refused as a derivation" / "The legacy branch's
## accepted and refused inputs are committed as a fixture" / "The asymmetry
## between the two arms is recorded, not reproduced" / "The third argument is
## recorded as display-only and safely ignorable" / "Evidence, provenance, and
## claim limits" / "The corrected reason replaces the corpus reason wherever it
## was recorded", design D1-D7).
##
## This line delivers a **refusal plus a fail-closed classification**, so most
## of what it asserts is an absence. `production_flow.gd::experience()` already
## reported a recorded `attr["xp"]` verbatim and never awarded it; this suite
## pins that surface, adds the one thing the executed evidence made necessary —
## **the recorded value's KIND** — and proves the module gained neither an
## arithmetic operator on that value nor an award helper.
##
## Checks:
##   projection  the closed six-member `recorded_kind` vocabulary, every member
##               reachable, the value reported verbatim beside its kind, the
##               non-dictionary bag refused, and the seven pre-existing fields
##               unchanged in name and meaning;
##   kinds       every vocabulary member with its witness value, `bool` proved
##               SEPARATE from `int`, a stored `null` proved `other` rather than
##               `absent`, and no coercion, conversion, or comparison applied to
##               any non-integer;
##   no-arith    the experience surface's function bodies, extracted BY NAME,
##               carry zero numeric operators and zero numeric conversions, and
##               every module line that names the experience key carries none
##               either — each proved non-vacuous by a self-test before it is
##               trusted;
##   absence     the module's WHOLE `static`-function inventory against a pinned
##               list, the recorded `ABSENT_HELPERS` still naming
##               `award_experience`, and no award/level/threshold helper by
##               name — the anti-invention guard (D5);
##   census      the repository-wide measurement over **all 31** committed save
##               documents (rows, rows carrying the field, documents carrying
##               it) beside the fresh corpus's own 40-row figure, each labelled
##               for what it is;
##   legacy      the committed legacy source re-read for the field's two writes
##               and its zero readers, the two branches' asymmetry, and
##               `apply_resources`' player-XP clamp against the accumulator's
##               absence of one;
##   reason      the tree scan: **zero** client sources state the
##               corpus-cannot-exercise reason for unit experience, pinned to
##               zero so a change in EITHER direction fails;
##   fixture     the committed executed-legacy fixture's own manifest when it is
##               present, and an explicit absent marker when it is not — never a
##               fabricated table;
##   boundary    no client source computes an award, a unit level, a threshold,
##               or a schedule from the field, and the delivered surface exposes
##               no route and no intent;
##   purity      the delivered module names no node, a clock, a request, or a
##               transport token, and preloads exactly the two read-only models;
##   containment the content package, the committed saves, the committed
##               fixtures, the committed villages, and the legacy root modules
##               are byte-identical after the run.
##
## Hermetic: no process, no server, no socket, and **no request is issued** —
## this line has nothing to send, which is the point of it. It runs headless as
## part of `verify-boot.ps1` and adds **no live phase**, because there is no
## endpoint and nothing mutates.
##
## `--report=<path>` writes the deterministic `unit-experience-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-experience/report.json`. Every table is derived from the live
## projection module's own constants, this same run's measurements over the
## committed bytes, and the fixture's own recorded manifest — so the report
## cannot drift from the code it documents.

const ProductionFlow = preload("res://scripts/units/production_flow.gd")
const UnitQueue = preload("res://scripts/units/unit_queue.gd")

## Preloaded only so the boundary check can read the transport's own closed
## action vocabulary. This suite sends nothing: the action is read, never used
## to address a command, which is exactly the boundary the check asserts.
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-experience/report.json"

## The delivered module this suite guards, and the two read-only models it
## preloads.
const DELIVERED_SCRIPT := "res://scripts/units/production_flow.gd"
const EXPECTED_PRELOADS := ["res://scripts/units/queue_flow.gd",
	"res://scripts/units/unit_queue.gd"]

## ## The whole function inventory of `production_flow.gd` (D5)
##
## The anti-invention guard is STRUCTURAL and whole-inventory, following the
## precedent `test_unit_production.gd` already establishes: a readiness,
## duration, award, level, threshold, or schedule helper appears here and the
## suite fails. It is the real gate; the by-name list below is the belt, added
## because a rename must not smuggle one past the inventory.
const EXPECTED_MODULE_METHODS := [
	"_client_routes", "_count_text", "_evaluation_reject",
	"_experience_reject", "_number_text", "_type_name",
	"acquisition_note", "acquisition_record", "acquisition_routes",
	"classification_counts", "classification_vocabulary",
	"committed_training_time", "death_record", "derived_row_entries",
	"evaluate", "experience", "experience_note", "experience_record",
	"no_derivation_finding", "readout_text", "recorded_experience_kind",
	"recorded_kind_vocabulary", "row_entry_branch_names",
	"row_entry_inventory", "training_time_note", "training_time_record",
]

## Helpers an award, a unit level, a threshold, or a schedule would take. The
## inventory above is the real gate.
const FORBIDDEN_HELPERS := [
	"award_experience", "grant_experience", "add_experience", "add_xp",
	"award_xp", "experience_award", "experience_for", "xp_award",
	"total_experience", "new_experience", "level_up_experience",
	"experience_threshold", "experience_to_level", "level_from_experience",
	"xp_schedule", "experience_schedule", "per_unit_level", "unit_level",
	"award_level", "threshold_for_level",
]

## The experience surface whose bodies are scanned for arithmetic and for
## numeric conversion. Extracted BY NAME, and the extraction is proved
## non-vacuous before anything is asserted about the bodies.
const EXPERIENCE_SURFACE := ["experience", "recorded_experience_kind",
	"experience_note", "experience_record", "_experience_reject"]

## Numeric binary operators, each SPACE-PADDED so a continuation-line string
## concatenation (`+` in column one) and a return-type arrow (`->`) are not
## mistaken for arithmetic. `%` is deliberately absent: in this module it is
## GDScript's string-format operator, never a modulo, and that decision is
## recorded in the report rather than left implicit.
const NUMERIC_OPERATORS := [" + ", " - ", " * ", " / ", " ** ", " += ", " -= ",
	" *= ", " /= "]

## Numeric conversions and numeric built-ins. Each is matched with a
## non-identifier character before it, so `int(` never matches `print(`.
const NUMERIC_CONVERSIONS := ["int(", "float(", "round(", "abs(", "min(",
	"max(", "clamp(", "ceil(", "floor(", "sign(", "snappedf(", "snappedi(",
	"pow(", "lerp(", "fmod(", "nearest_po2(", "is_equal_approx("]

## ## The corrected-reason tree scan (D6, task 5.4)
##
## The needles are the REASON CONSTRUCTION, not the corpus figure, because the
## corrected text legitimately keeps the figure and labels it. They are spelled
## as fragments for the same project-scope reason as every other suite in this
## project: the scanner's own source must not contain the phrase it hunts for.
const REASON_CONSTRUCTIONS := [
	"cannot " + "exercise",
	"can not " + "exercise",
	"could not " + "exercise",
	"cannot be " + "exercised",
	"can not be " + "exercised",
	"could not be " + "exercised",
]

## A hit counts only when a unit-experience token sits within this many
## characters of the construction, which is what scopes the scan to unit
## experience: the repository holds several NEGATED occurrences about
## production, animation, movement, and resurrection, and none of them is this
## capability's reason.
const REASON_WINDOW := 160

## The tokens that scope a construction occurrence to unit experience.
const UNIT_EXPERIENCE_TOKENS := ["add_xp_unit", "attr['xp']", 'attr["xp"]',
	"unit experience", "unit-experience", "recorded experience",
	"experience_awarded", "recorded_experience_kind"]

## The scan's expected hit count, PINNED. A change in either direction fails:
## a new stale sentence is a failure, and so is a silently broadened or
## narrowed scan.
const EXPECTED_REASON_HITS := 0

## The client source trees the scan walks.
const CLIENT_SCAN_ROOTS := ["res://scripts", "res://tests"]

## This suite's own path, excluded from the reason scan.
##
## The scan deliberately carries a crafted copy of the stale sentence as its
## negative control, to prove the scanner is live rather than vacuously empty.
## Without this exclusion the control trips the very guard it exists to test, so
## the scan reported this file as an offender of its own rule. That is the same
## shape as the stored-placement hand-off, where the owner list lives in one
## suite and the other asserts the recipient exists: the exclusion is exact and
## named, never a blanket skip of the `res://tests` tree.
const REASON_SCAN_SELF := "res://tests/test_unit_experience.gd"

## Tokens a pure module must not carry: a node, a clock, a request, or a
## transport. The transport needles are fragments for the same project-scope
## reason as the reason constructions above.
const PURITY_NEEDLES := ["extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client"]

## The committed-evidence census, measured by this suite over the committed
## bytes and never copied from prose. `docs/legacy-unit-xp.md` §4e records the
## same figures; the suite measures them so the two cannot drift apart silently.
const EXPECTED_CENSUS_DOCUMENTS := 31
const EXPECTED_CENSUS_ROWS := 12954
const EXPECTED_CENSUS_ROWS_WITH_XP := 171
const EXPECTED_CENSUS_DOCUMENTS_WITH_XP := 5
const VILLAGES_DIR := "villages"
const VILLAGES_QUEST_SUBDIR := "quest"

## The fresh corpus's own figure, labelled as a corpus fact and never as
## evidence that an award exists.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const CORPUS_MAP_INDEX := 0
const EXPECTED_CORPUS_ROWS := 40
const EXPECTED_CORPUS_ROWS_WITH_XP := 0

## The committed executed-legacy fixture. Its ABSENCE is a recorded state with
## a named cause, never a fabricated table: this suite reads a manifest if one
## is committed and writes an explicit absent marker if it is not.
const FIXTURE_DIR := "tests/fixtures/godot-unit-experience"
const FIXTURE_MANIFEST := "capture-manifest.json"

## The fields a recorded transaction may carry. Copied only when present, and
## the keys each transaction actually carries are recorded alongside, so a
## schema the suite did not anticipate is visible instead of silent.
const TRANSACTION_FIELDS := ["command", "args", "attr_before", "attr_after",
	"changed_leaves", "status", "response", "response_body", "established",
	"note", "why_it_matters", "probe", "question"]

## The legacy modules this suite re-reads. A missing one is a FAILURE, never a
## silently smaller search: a measurement over a file that is not there would
## turn the zero-reader claim vacuous.
const LEGACY_MODULES := ["command.py", "engine.py", "sessions.py", "server.py",
	"constants.py", "get_game_config.py", "version.py", "auctions.py",
	"get_player_info.py", "legacy_command_recorder.py"]

## The two writes of the row's experience and the membership test that chooses
## between them, in committed line order.
const XP_WRITE_LINES := [336, 338]
const XP_ARM_LINES := [322, 343]

## `apply_resources`, which moves the PLAYER's experience with a floor, and the
## command.py line at which it runs before the dispatch.
const APPLY_RESOURCES_COMMAND := "engine.py:251-271"
const APPLY_RESOURCES_SITE := "command.py:40"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var package_dir := Paths.repo_root().path_join("packages/game-content")
	var saves_dir := Paths.repo_root().path_join("tests/saves")
	var fixtures_dir := Paths.repo_root().path_join("tests/fixtures")
	var villages_dir := Paths.repo_root().path_join(VILLAGES_DIR)
	var package_before := Paths.directory_digest(package_dir)
	var saves_before := Paths.directory_digest(saves_dir)
	var fixtures_before := Paths.directory_digest(fixtures_dir)
	var villages_before := Paths.directory_digest(villages_dir)
	var groups: Array = [["content package", package_before],
		["committed saves", saves_before],
		["committed fixtures", fixtures_before],
		["committed villages", villages_before]]
	for entry: Array in groups:
		var group := str(entry[0])
		var digest: Dictionary = entry[1]
		check(bool(digest.get("ok", false)),
			"%s digest is readable before the run (%s)"
				% [group, str(digest.get("error", ""))])
		if not bool(digest.get("ok", false)):
			return
	var legacy_before := _legacy_digest()
	check(bool(legacy_before.get("ok", false)),
		"legacy root modules digest is readable before the run (%s)"
			% str(legacy_before.get("error", "")))
	if not bool(legacy_before.get("ok", false)):
		return

	var kinds := _check_projection()
	_check_kinds(kinds)
	_check_no_arithmetic()
	_check_absence()
	var census := _check_census()
	var corpus := _check_corpus()
	var legacy := _check_legacy()
	_check_reason()
	var fixture := _check_fixture()
	_check_boundary()
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before,
		villages_before, legacy_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, kinds, census, corpus, legacy, fixture)
	info("unit experience: kinds %s, census %d/%d rows in %d/%d documents, "
		% [",".join(PackedStringArray(ProductionFlow.RECORDED_KINDS)),
			int(census.get("rows_with_xp", 0)), int(census.get("rows", 0)),
			int(census.get("documents_with_xp", 0)),
			int(census.get("documents", 0))]
		+ "reason hits %d, fixture present %s"
			% [_reason_scan().size(), str(bool(fixture.get("present", false)))])


# ---------------------------------------------------------------------------
# The projection: the recorded value and its kind (design D1/D2)
# ---------------------------------------------------------------------------


## The whole projected record for one bag, so the suite measures the SAME
## surface a caller reads. Returns the measured rows so the report is generated
## from them rather than restated.
func _check_projection() -> Dictionary:
	var measured := {"rows": [], "kinds": [], "field_sets": {}}

	# The closed vocabulary, read from the module's own inventory.
	check_eq(ProductionFlow.recorded_kind_vocabulary(),
		["absent", "int", "float", "string", "bool", "other"],
		"the recorded-kind vocabulary is the closed six-member set design D2 "
			+ "names, in order")
	check_eq(ProductionFlow.RECORDED_KINDS.size(), 6,
		"the vocabulary has exactly six members and no seventh can be added "
			+ "silently")
	for kind: String in ProductionFlow.RECORDED_KINDS:
		check(not kind.is_empty(),
			"the vocabulary member '%s' is named" % kind)
		check(kind == kind.strip_edges(),
			"the vocabulary member '%s' is a bare token" % kind)

	# Every field the delivered projection already carried, with its meaning
	# unchanged, and the ONE field this line adds beside it.
	var original_fields := ["ok", "reason", "error", "recorded",
		"recorded_is_absent", "awarded", "award_source", "award_implemented",
		"contract", "corpus_note"]
	var read := ProductionFlow.experience({"xp": 250})
	var keys: Array = read.keys()
	keys.sort()
	var expected_keys: Array = (original_fields + ["recorded_kind"]).duplicate()
	expected_keys.sort()
	check_eq(keys, expected_keys,
		"experience() returns the ten fields it always returned PLUS exactly "
			+ "one new field, `recorded_kind`, and drops nothing")
	var refused := ProductionFlow.experience(null)
	var refused_keys: Array = refused.keys()
	refused_keys.sort()
	check_eq(refused_keys, keys,
		"the structural refusal carries the SAME field set as a successful "
			+ "report, so no caller can read a half-built record")
	for field: String in original_fields:
		check(refused.has(field),
			"the refusal still carries the pre-existing '%s' field" % field)

	# Each original field's meaning, unchanged.
	check_eq(bool(read.get("ok", false)), true,
		"a bag carrying the field is read")
	check_eq(str(read.get("reason", "x")), "",
		"a successful read carries an empty reason")
	check_eq(str(read.get("error", "x")), "",
		"a successful read carries an empty error")
	check_eq(int(read.get("recorded", -1)), 250,
		"`recorded` is still the value verbatim")
	check_eq(bool(read.get("recorded_is_absent", true)), false,
		"`recorded_is_absent` still means the key is present")
	check_eq(bool(read.get("awarded", true)), false,
		"`awarded` is still a constant false")
	check(str(read.get("award_source", "")).contains("client argument"),
		"`award_source` still names the client argument as the only source")
	check_eq(bool(read.get("award_implemented", true)), false,
		"`award_implemented` is still false")
	check(str(read.get("contract", "")).contains("NO EXPERIENCE IS AWARDED"),
		"`contract` still carries the refusal")
	check(str(read.get("corpus_note", "")).contains("0 of its 40"),
		"`corpus_note` still carries the labelled corpus figure")

	# The record accessor carries the kind contract beside the old fields.
	var record := ProductionFlow.experience_record()
	for field: String in ["command", "site", "attr_key", "attr_slot",
			"amount_source", "level_source", "award_implemented",
			"creates_anything", "rule", "corpus_note", "corpus_finding",
			"kind_helper", "recorded_kinds", "kind_rule", "arm_asymmetry",
			"level_display_only", "coerced", "converted", "compared",
			"field_repaired"]:
		check(record.has(field),
			"the recorded contract carries '%s'" % field)
	check_eq(str(record["kind_helper"]), "recorded_experience_kind",
		"the contract names the single classification helper")
	check_eq(str(record["attr_key"]), "xp",
		"the recorded field name is the committed attr['xp']")
	check_eq(int(record["attr_slot"]), UnitQueue.ATTR_SLOT,
		"the field lives in the placed row's attr bag, the queue keys' slot")
	check_eq(bool(record["award_implemented"]), false,
		"the award is still declared NOT implemented")
	check_eq(bool(record["creates_anything"]), false,
		"add_xp_unit still CREATES NOTHING")
	for field: String in ["coerced", "converted", "compared", "field_repaired"]:
		check_eq(bool(record.get(field, true)), false,
			"the contract states the recorded value is never %s" % field)
	# The two recorded defects and the third-argument rule, verbatim.
	check(str(record["arm_asymmetry"]).contains("RECORDED, NEVER REPRODUCED"),
		"the arm asymmetry is recorded as a defect that is never reproduced")
	check(str(record["arm_asymmetry"]).contains("336")
			and str(record["arm_asymmetry"]).contains("338"),
		"the arm asymmetry names BOTH writes, so the two arms can be compared")
	check(str(record["arm_asymmetry"]).contains("500"),
		"the arm asymmetry records the increment arm's server error")
	check(str(record["level_display_only"]).contains("DISPLAY-ONLY"),
		"the third argument is recorded as display-only")
	check(str(record["level_display_only"]).contains("ACCEPT AND IGNORE"),
		"the third argument's rule is accept-and-ignore, never refuse")
	check(str(record["level_display_only"]).contains("TRUTHINESS"),
		"the third argument's falsy distinction is recorded")
	check(str(record["kind_rule"]).contains("CLOSED vocabulary"),
		"the kind rule states the vocabulary is closed")

	# The readout still renders a value and the refusal, and never a number a
	# player could read as an award. Its text is unchanged in meaning.
	var note := ProductionFlow.experience_note(read)
	check(note.contains("250") and note.contains("never awarded"),
		"the experience readout shows the recorded value and the refusal")
	check(ProductionFlow.experience_note(
			ProductionFlow.experience({})).contains("absent"),
		"the readout names an absent recorded experience as absent")
	check(ProductionFlow.experience_note({}).is_empty(),
		"a refused experience renders no readout")

	measured["record"] = record
	measured["note_int"] = note
	measured["note_absent"] = ProductionFlow.experience_note(
		ProductionFlow.experience({}))
	return measured


# ---------------------------------------------------------------------------
# Every vocabulary member, and no coercion of a non-integer (design D2)
# ---------------------------------------------------------------------------


## Every member of the closed vocabulary, each with the witness value that
## produces it, and — for every non-integer — the proof that no coercion,
## conversion, or comparison was applied on the way out.
func _check_kinds(measured: Dictionary) -> void:
	# (bag, expected kind, witness label, is it an integer?)
	var cases := [
		[{}, "absent", "a bag with no attr['xp'] at all", false],
		[{"xp": 0}, "int", "the integer zero", true],
		[{"xp": 23}, "int", "the executed increment arm's recorded 23", true],
		[{"xp": -977}, "int", "the executed UNCLAMPED negative", true],
		[{"xp": 25.5}, "float", "the executed PERSISTED FRACTION", false],
		[{"xp": "5"}, "string", "the executed POISONED STRING on the assign arm",
			false],
		[{"xp": true}, "bool", "a STORED True, reachable on the assign arm "
			+ "which writes the gain verbatim - DERIVED from the branch, not "
			+ "executed: the executed boolean took the increment arm and moved "
			+ "a row from 23 to 24, an int, so no True is persisted there",
			false],
		[{"xp": null}, "other", "a stored null, which is NOT an absent key",
			false],
		[{"xp": [1]}, "other", "a stored array", false],
		[{"xp": {"a": 1}}, "other", "a stored object", false],
	]
	var vocabulary: Array = ProductionFlow.recorded_kind_vocabulary()
	for entry: Variant in cases:
		var bag: Dictionary = entry[0]
		var expected := str(entry[1])
		var label := str(entry[2])
		var is_integer: bool = bool(entry[3])
		var read := ProductionFlow.experience(bag)
		check(bool(read.get("ok", false)),
			"the bag holding %s is read" % label)
		check_eq(str(read.get("recorded_kind", "")), expected,
			"a bag holding %s is classified as '%s'" % [label, expected])
		check(vocabulary.has(str(read.get("recorded_kind", ""))),
			"the reported kind for %s comes from the CLOSED vocabulary" % label)
		check_eq(bool(read.get("awarded", true)), false,
			"a bag holding %s is still never awarded" % label)
		if str(expected) == "absent":
			check_eq(bool(read.get("recorded_is_absent", false)), true,
				"an absent key is reported as ABSENT rather than as a value")
			check_eq(read.get("recorded", "unset"), null,
				"an absent key reports null, which a zero cannot say")
			continue
		check_eq(bool(read.get("recorded_is_absent", true)), false,
			"%s is reported as RECORDED, not absent" % label)
		# The value comes back byte-for-byte what went in.
		check_eq(_normalized(read.get("recorded", null)),
			_normalized(bag[ProductionFlow.XP_ATTR_KEY]),
			"the recorded value for %s is reported verbatim" % label)
		if is_integer:
			continue
		# No coercion, no conversion, no comparison, on a NON-INTEGER.
		check_eq(typeof(read.get("recorded", null)), typeof(bag["xp"]),
			"the reported kind for %s changes no runtime TYPE" % label)
		check_eq(str(read.get("recorded", null)), str(bag["xp"]),
			"the reported value for %s keeps its exact string form" % label)
		check_eq(_derived_numeric_keys(read), [],
			"no numeric interpretation of %s is exposed anywhere on the record: "
				% label
				+ "no field on it holds a number derived from the recorded "
				+ "value, so nothing derived is readable as a quantity. The "
				+ "`recorded` field is excluded from that scan because it is "
				+ "the value verbatim, which is the contract and not an "
				+ "interpretation")
		(measured["rows"] as Array).append({
			"witness": label,
			"bag": bag.duplicate(true),
			"kind": expected,
			"reported_value": read.get("recorded", null),
			"reported_value_type": _type_name(read.get("recorded", null)),
			"awarded": bool(read.get("awarded", true)),
		})
		(measured["kinds"] as Array).append(expected)

	# `bool` is proved SEPARATE from `int`, by reason and not by accident.
	check_eq(ProductionFlow.experience({"xp": true}).get("recorded_kind"), "bool",
		"a boolean is classified `bool`, NOT `int`, even though the legacy "
			+ "server's own arithmetic treats True as 1")
	check_eq(ProductionFlow.experience({"xp": 1}).get("recorded_kind"), "int",
		"the integer 1 is classified `int`, so the two really are distinct")
	check(not ProductionFlow.recorded_kind_vocabulary().has("number"),
		"the vocabulary has no numeric umbrella member that would collapse "
			+ "int, float, and bool together")
	check(str(ProductionFlow.XP_KIND_RULE).contains("True + 5"),
		"the recorded kind rule states WHY bool is separate, by reference to "
			+ "the legacy server's own arithmetic")

	# The rule must keep the EXECUTED boolean fact and the DERIVED one apart.
	#
	# A first draft of this line's prose claimed the executed evidence shows the
	# legacy server "stores True for a client-sent true". The committed fixture
	# contradicts it: the boolean transaction incremented a row recorded at 23 to
	# 24, an int, because the increment arm does arithmetic on the gain. A stored
	# True is reachable only on the assign arm, which writes the gain verbatim --
	# derived from the branch, not executed here. Asserting the distinction keeps
	# a true-sounding claim from being upgraded into executed evidence again.
	var kind_rule := str(ProductionFlow.XP_KIND_RULE)
	check(kind_rule.contains("EXECUTED"),
		"the recorded kind rule labels its boolean evidence as EXECUTED")
	check(kind_rule.contains("DERIVED"),
		"the recorded kind rule labels the stored-True half as DERIVED")
	check(not kind_rule.contains("evidence shows the server stores True"),
		"the recorded kind rule no longer claims executed evidence of a stored "
			+ "True, which the committed fixture contradicts")

	# Every member of the closed vocabulary is actually REACHED by a witness.
	var reached := {}
	for entry: Variant in cases:
		reached[str(entry[1])] = true
	var unreached: Array = []
	for kind: String in ProductionFlow.RECORDED_KINDS:
		if not reached.has(kind):
			unreached.append(kind)
	check_eq(unreached, [],
		"every member of the closed vocabulary is reached by a witness value "
			+ "in this suite, so no member is decorative")

	# The structural rejection: a bag that is not a bag is refused, and the
	# refusal reports the named absence rather than a value.
	for value: Variant in [null, [], "bag", 7, 25.5]:
		var refused := ProductionFlow.experience(value)
		check(not bool(refused.get("ok", false)),
			"the attribute bag %s is refused: a missing bag and a non-bag mean "
				% [value] + "different things")
		check_eq(str(refused.get("reason", "")),
			ProductionFlow.REASON_INVALID_ATTR,
			"the experience refusal carries its own named reason")
		check_eq(str(refused.get("recorded_kind", "")), "absent",
			"a refused read reports the kind `absent`: nothing was read, so "
				+ "nothing may be classified")
		check_eq(refused.get("recorded", "unset"), null,
			"a refused read reports no value at all")
		check_eq(bool(refused.get("awarded", true)), false,
			"a refused read awards nothing")
	# The non-dictionary rejection is DELIBERATE, and is reported: a structural
	# rejection keeps every other field at its recorded neutral value.
	check(str(ProductionFlow.experience([1, 2]).get("error", "")).contains(
			"not an object"),
		"a non-object attribute bag is named in the refusal message")

	# No field on the record turns the value into a number.
	var integer_read := ProductionFlow.experience({"xp": 250})
	for field: String in ["granted", "level_up", "xp_awarded",
			"experience_award", "new_xp", "total_xp", "level", "threshold"]:
		check(not integer_read.has(field),
			"the record carries NO %s field: there is no award, no level, and "
				% field + "no threshold to report")
	check(not _numeric_keys(integer_read).has("level"),
		"the record carries no level derived from the recorded value")


# ---------------------------------------------------------------------------
# The structural anti-invention guard (design D5)
# ---------------------------------------------------------------------------


## The experience surface gained **no arithmetic and no numeric conversion**,
## and the whole module carries no award helper. Every scan here is proved
## non-vacuous by a self-test BEFORE it is trusted, because a scan that is
## handed a path instead of a body becomes vacuously true — a defect this
## project has already hit twice.
func _check_no_arithmetic() -> void:
	var source := _source(DELIVERED_SCRIPT)
	check(not source.is_empty(),
		"the delivered module's source is readable, so the guards scan a body "
			+ "and never a path")
	if source.is_empty():
		return
	var code := _code_only(source)

	# The scanners are PROVED live first: each must find the violation planted
	# in a crafted body and miss nothing in a clean one.
	var planted_arithmetic := ("static func experience(a) -> int:\n\treturn "
		+ "int(a[\"xp\"]) + 1\n")
	check(_numeric_occurrences(_code_only(planted_arithmetic),
			NUMERIC_OPERATORS, NUMERIC_CONVERSIONS).size() >= 2,
		"the arithmetic scanner is PROVED LIVE: it finds both a numeric "
			+ "operator and a numeric conversion planted in a crafted body, so "
			+ "its zero result below is a measurement and not a broken scan")
	check_eq(_numeric_occurrences(_code_only(
			"static func experience(a) -> Dictionary:\n\treturn a\n"),
			NUMERIC_OPERATORS, NUMERIC_CONVERSIONS), [],
		"the arithmetic scanner reports nothing on a clean body")
	check(_numeric_occurrences(_code_only(
			"static func experience(a):\n\tprint(a[\"xp\"])\n"),
			NUMERIC_OPERATORS, NUMERIC_CONVERSIONS) == [],
		"the arithmetic scanner does NOT false-positive on `print(`, because "
			+ "each conversion token is matched behind a non-identifier "
			+ "character")

	for name: String in EXPERIENCE_SURFACE:
		var body := _function_body(code, name)
		check(not body.is_empty(),
			"the experience surface's '%s' body is extracted BY NAME, so the "
				% name + "arithmetic guard scans a body and not a path")
		if body.is_empty():
			continue
		check(body.contains("return"),
			"the extracted '%s' body is a real body (it returns something), so "
				% name + "the extraction found the function and not its "
				+ "signature alone")
		var found := _numeric_occurrences(body, NUMERIC_OPERATORS,
			NUMERIC_CONVERSIONS)
		check_eq(found, [],
			"the '%s' body carries NO arithmetic and NO numeric conversion: a "
				% name + "recorded experience is never added to, rounded, "
				+ "narrowed, or compared")
		check(not body.contains("XP_AMOUNT_SOURCE")
				or name == "experience_note"
				or name == "experience_record",
			"the '%s' body names no client amount to apply — it only ever "
				% name + "quotes the recorded SOURCE text")

	# Whole-module: every code line naming the experience key carries no
	# numeric token either, and the number of such lines is pinned so a new
	# read of the field is noticed.
	var key_lines: Array = []
	for index in range(code.split("\n").size()):
		var line: String = code.split("\n")[index]
		if _names_identifier(line, "XP_ATTR_KEY"):
			key_lines.append(line.strip_edges())
	check(key_lines.size() > 0,
		"at least one module line names the experience key, so the whole-module "
			+ "guard below is a measurement and not an empty set")
	check_eq(key_lines.size(), 6,
		"exactly six module lines name the experience key: its definition, the "
			+ "membership test and verbatim read in `experience()`, the same pair "
			+ "in `recorded_experience_kind()`, and the record's `attr_key` echo. "
			+ "A seventh would be a NEW read of the field and is reported rather "
			+ "than ignored")
	for line: String in key_lines:
		check_eq(_numeric_occurrences(line, NUMERIC_OPERATORS,
			NUMERIC_CONVERSIONS), [],
			"no module line that names the experience key performs arithmetic: "
				+ "'%s'" % line)


## The whole `static`-function inventory, the recorded absences, and the
## by-name belt.
func _check_absence() -> void:
	var declared := _declared_methods(_source(DELIVERED_SCRIPT))
	check_eq(declared, EXPECTED_MODULE_METHODS,
		"production_flow.gd declares EXACTLY its pinned whole inventory: the "
			+ "two kind accessors design D1 permits, and no award, level, "
			+ "threshold, or schedule helper")
	check_eq(_methods_live(),
		["award_experience", "int_", "round_"],
		"the method extractor is PROVED LIVE: it finds planted declarations and "
			+ "reports their names, through BOTH the `static func` and the plain "
			+ "`func` spellings, including one the module must NOT have")
	for helper: String in FORBIDDEN_HELPERS:
		check(not declared.has(helper),
			"the module declares no '%s' helper: no award is computed, no unit "
				% helper + "level exists, and no threshold or schedule is "
				+ "derived")
	# The by-name belt scans identifiers in the CODE, so a recorded contract
	# string may still name an absent helper.
	var code := _code_only(_source(DELIVERED_SCRIPT))
	for helper: String in FORBIDDEN_HELPERS:
		check(not _declares_identifier(code, helper),
			"no identifier in the delivered module is named '%s': not a "
				% helper + "function, not a local, and not a constant")
	# The recorded absences survive: twelve of them, and `award_experience` is
	# still one of them with its reason.
	var absent: Array = ProductionFlow.ABSENT_HELPERS
	check_eq(absent.size(), 12,
		"the recorded ABSENT_HELPERS list still names all twelve absences")
	var named: Array = []
	for entry: Dictionary in absent:
		named.append(str(entry["helper"]))
		check(not str(entry["absent_because"]).is_empty(),
			"the recorded absence of '%s' still states why"
				% str(entry["helper"]))
	check(named.has("award_experience"),
		"`award_experience` is still a RECORDED absence, not a renamed helper")
	for entry: Dictionary in absent:
		if str(entry["helper"]) == "award_experience":
			check(str(entry["absent_because"]).contains("client argument"),
				"the recorded absence of an experience award still grounds "
					+ "itself in the client amount")


# ---------------------------------------------------------------------------
# The committed-evidence census (design: corpus figure stays labelled)
# ---------------------------------------------------------------------------


## The repository-wide measurement over **all** committed save documents, and
## the fresh corpus's own figure beside it. The corpus figure is labelled a
## fact about that corpus and never as evidence about the repository.
func _check_census() -> Dictionary:
	var root := Paths.repo_root()
	var documents: Array = []
	documents.append_array(_json_files(root.path_join(VILLAGES_DIR)))
	documents.append_array(_json_files(root.path_join(VILLAGES_DIR).path_join(
		VILLAGES_QUEST_SUBDIR)))
	documents.sort()
	check_eq(documents.size(), EXPECTED_CENSUS_DOCUMENTS,
		"the census reads every committed save document: the 8 in villages/ "
			+ "plus the 23 quest snapshots in villages/quest/")
	var rows := 0
	var rows_with_xp := 0
	var per_document: Array = []
	var documents_with_xp: Array = []
	var kinds := {}
	var ids := {}
	for relative: String in documents:
		var document: Variant = _read_json(Paths.repo_root().path_join(
			relative))
		if not (document is Dictionary):
			check(false, "the committed save document %s is readable JSON"
				% relative)
			continue
		var map: Dictionary = (document as Dictionary)["maps"][0]
		var items: Dictionary = map["items"]
		var here := 0
		for key: Variant in items.keys():
			var row: Variant = items[key]
			var bag: Variant = (row as Array)[UnitQueue.ATTR_SLOT]
			if not (bag is Dictionary):
				continue
			if not (bag as Dictionary).has(ProductionFlow.XP_ATTR_KEY):
				continue
			here += 1
			var value: Variant = (bag as Dictionary)[ProductionFlow.XP_ATTR_KEY]
			# JSON decodes every number as a float, so the kind is classified
			# from the NORMALIZED value: an integral float is an integer on
			# disk, and only a genuine fraction is a float. Without this every
			# committed row would be reported as a float.
			kinds[_type_name(_normalized(value))] = true
			ids[str((row as Array)[0])] = true
		rows += items.size()
		rows_with_xp += here
		per_document.append({"document": relative.get_file(),
			"rows": items.size(), "rows_with_xp": here})
		if here > 0:
			documents_with_xp.append(relative.get_file())
	check_eq(rows, EXPECTED_CENSUS_ROWS,
		"the census places %d rows across every committed save document"
			% EXPECTED_CENSUS_ROWS)
	check_eq(rows_with_xp, EXPECTED_CENSUS_ROWS_WITH_XP,
		"exactly %d placed rows across the whole repository carry attr['xp']"
			% EXPECTED_CENSUS_ROWS_WITH_XP)
	check_eq(documents_with_xp.size(), EXPECTED_CENSUS_DOCUMENTS_WITH_XP,
		"the field appears in exactly %d of the %d committed save documents"
			% [EXPECTED_CENSUS_DOCUMENTS_WITH_XP, EXPECTED_CENSUS_DOCUMENTS])
	check_eq(kinds, {"int": true},
		"every one of the %d committed recorded values is an INTEGER, so each "
			% EXPECTED_CENSUS_ROWS_WITH_XP
			+ "non-integer kind this line classifies is reachable only through "
			+ "the executed legacy evidence or crafted input, never through the "
			+ "repository census")
	check(ids.size() > EXPECTED_CENSUS_DOCUMENTS,
		"the recorded rows resolve to more distinct item ids than there are "
			+ "documents, so the field is not one unit's own value")
	per_document.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return str(a["document"]) < str(b["document"]))
	return {
		"documents": documents.size(),
		"rows": rows,
		"rows_with_xp": rows_with_xp,
		"documents_with_xp": documents_with_xp.size(),
		"documents_with_xp_names": documents_with_xp,
		"per_document": per_document,
		"recorded_value_kinds": _sorted_keys(kinds),
		"distinct_item_ids": ids.size(),
		"measured_by": "this run, over every committed save document in "
			+ "villages/ and villages/quest/",
	}


## The fresh corpus's own 40-row figure, read from the committed bytes and
## labelled for exactly what it is.
func _check_corpus() -> Dictionary:
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed fresh-player corpus is readable")
	var document: Dictionary = save as Dictionary
	var map: Dictionary = document["maps"][CORPUS_MAP_INDEX]
	var rows: Dictionary = map["items"]
	check_eq(rows.size(), EXPECTED_CORPUS_ROWS,
		"the committed fresh-player corpus places %d rows"
			% EXPECTED_CORPUS_ROWS)
	var experience_rows: Array = []
	for key: Variant in rows.keys():
		var bag: Variant = (rows[key] as Array)[UnitQueue.ATTR_SLOT]
		if (bag is Dictionary) and (bag as Dictionary).has("xp"):
			experience_rows.append(str(key))
	check_eq(experience_rows, [], EXPECTED_STRIPPED_CORPUS_MESSAGE)
	check_eq(experience_rows.size(), EXPECTED_CORPUS_ROWS_WITH_XP,
		"the fresh-player corpus carries the recorded experience on %d of its "
			% EXPECTED_CORPUS_ROWS_WITH_XP + "%d rows" % EXPECTED_CORPUS_ROWS)
	check_eq(map.get("store", null), {},
		"the fresh-player corpus's storage is empty")
	return {
		"save": CORPUS_SAVE,
		"rows": rows.size(),
		"rows_with_xp": experience_rows.size(),
		"experience_rows": experience_rows,
		"store_empty": (map.get("store", {}) as Dictionary).is_empty(),
		"figure_label": "A FACT ABOUT THIS ONE DOCUMENT, and never evidence "
			+ "about the repository and never evidence that an award exists: "
			+ "the same field is present on %d placed rows across %d committed "
			% [EXPECTED_CENSUS_ROWS_WITH_XP, EXPECTED_CENSUS_DOCUMENTS_WITH_XP]
			+ "save documents",
	}


const EXPECTED_STRIPPED_CORPUS_MESSAGE := ("NOT ONE of the %d rows in THIS "
	+ "committed fresh-player corpus carries attr['xp']: the field is absent "
	+ "from all of them, which is a corpus measurement over that one document "
	+ "and never an award (this is a scope claim about the fresh-player "
	+ "corpus, NOT a repository-wide one: the `godot-unit-experience` "
	+ "capability measures %d of %d placed rows across %d of the %d committed "
	+ "save documents as carrying it)")
# Filled in at run time by _check_corpus; declared so the constant above stays
# a single literal the report and the message share.


# ---------------------------------------------------------------------------
# The committed legacy source (design: established, never derived)
# ---------------------------------------------------------------------------


## The field's two writes, its zero readers, the two arms' asymmetry, and the
## player-XP clamp against the accumulator's absence of one.
func _check_legacy() -> Dictionary:
	for module: String in LEGACY_MODULES:
		check(FileAccess.file_exists(
				Paths.repo_root().path_join(module)),
			"the legacy module %s exists: a measurement over a missing file "
				% module + "would turn the zero-reader claim vacuous")

	var command := _legacy_lines("command.py")
	var attr_sites: Array = []
	var xp_gain_sites: Array = []
	var player_sites: Array = []
	var level_sites: Array = []
	for index in range(command.size()):
		var line: String = str(command[index])
		var number := index + 1
		if line.contains("attr[\"xp\"]"):
			attr_sites.append(number)
		if line.contains("xp_gain"):
			xp_gain_sites.append(number)
		if line.contains("map[\"xp\"]") or line.contains('map["xp"]'):
			player_sites.append(number)
		if line.contains("if level:"):
			level_sites.append(number)
	check_eq(attr_sites, XP_WRITE_LINES,
		"the row's recorded experience is written at exactly two lines, and "
			+ "both are inside this one branch")
	check_eq(xp_gain_sites.size(), 5,
		"the client-sent amount appears five times in the branch: read once, "
			+ "written twice, interpolated twice")
	check_eq(attr_sites.size(), 2,
		"the field has exactly TWO occurrences of attr['xp'] in the whole "
			+ "committed dispatcher")
	# Zero READERS of the row's field, repository-wide, counted as quoted
	# subscripts over every legacy module.
	var read_sites: Array = []
	var write_sites: Array = []
	for module: String in LEGACY_MODULES:
		for index in range(_legacy_lines(module).size()):
			var line: String = str(_legacy_lines(module)[index])
			if not line.contains("attr[\"xp\"]"):
				continue
			# `+=` READS as well as writes, so the increment is recorded on BOTH
			# lists and the zero-reader claim below is measured rather than
			# obtained by classifying an increment as a pure write.
			if line.contains("+="):
				read_sites.append("%s:%d (the increment reads and writes)"
					% [module, index + 1])
			elif not line.contains("="):
				read_sites.append("%s:%d (a bare subscript)" % [module, index + 1])
			write_sites.append("%s:%d" % [module, index + 1])
	check_eq(write_sites.size(), 2,
		"the field is written at exactly two lines, both inside one branch")
	check_eq(read_sites, ["command.py:338 (the increment reads and writes)"],
		"the field has NO reader other than the increment's own read-modify-"
			+ "write: every attr['xp'] occurrence in the legacy source is a "
			+ "write, so no branch, engine helper, session function, or migration "
			+ "ever consults a unit's recorded total")
	# The branch is type-agnostic and the two arms differ.
	check(str(command[XP_ARM_LINES[0] - 1]).contains("add_xp_unit"),
		"the recorded branch is named add_xp_unit at command.py:322")
	var assign: String = str(command[XP_WRITE_LINES[0] - 1])
	var increment: String = str(command[XP_WRITE_LINES[1] - 1])
	check(assign.contains("=") and not assign.contains("+="),
		"the ASSIGN arm stores the client amount verbatim")
	check(increment.contains("+="),
		"the INCREMENT arm adds the client amount to what is there, which is "
			+ "why it raises on a non-numeric stored value")
	var falsy_test_line := -1
	if level_sites.size() == 1:
		falsy_test_line = int(level_sites[0])
	check(level_sites.size() == 1
			and falsy_test_line >= XP_ARM_LINES[0]
			and falsy_test_line <= XP_ARM_LINES[1],
		"the branch FALSY-TESTS its third argument inside the branch, which is "
			+ "the recorded display-only distinction")
	# `apply_resources` moves a DIFFERENT experience, with a floor.
	var engine := _legacy_lines("engine.py")
	var clamp_sites: Array = []
	for index in range(engine.size()):
		if str(engine[index]).contains("max(map[\"xp\"]"):
			clamp_sites.append(index + 1)
		elif str(engine[index]).contains("max(map['xp']"):
			clamp_sites.append(index + 1)
	check_eq(clamp_sites.size(), 1,
		"the PLAYER's experience is clamped at zero by apply_resources "
			+ "(engine.py:251-271), on exactly one line")
	check(player_sites.size() >= 1,
		"the player's own maps[0][\"xp\"] is read and written by the legacy "
			+ "source, so it is a distinct quantity from the row accumulator")
	check(str(command[39]).contains("apply_resources"),
		"apply_resources runs at command.py:40, BEFORE the dispatch, so one "
			+ "request can move the player's experience and a row's "
			+ "accumulator together from client-sent amounts")
	return {
		"branch": ProductionFlow.XP_COMMAND,
		"branch_span": ProductionFlow.XP_SITE,
		"attr_occurrences": attr_sites.size(),
		"attr_sites": attr_sites,
		"readers": read_sites.size(),
		"reader_sites": read_sites,
		"xp_gain_occurrences": xp_gain_sites.size(),
		"player_xp_sites_in_command": player_sites,
		"level_falsy_sites": level_sites,
		"player_clamp_site": clamp_sites,
		"apply_resources": APPLY_RESOURCES_COMMAND + ", applied at "
			+ APPLY_RESOURCES_SITE + " before the dispatch",
		"accumulator_clamped": false,
		"accumulator_bounded": false,
		"amount_validated": false,
		"note": "the field is written twice and read zero times; the amount is "
			+ "client args[1] with no validation of any kind, not even an "
			+ "int(); the optional third argument is client args[2], used "
			+ "ONLY inside a printed line and written nowhere. Only the "
			+ "PLAYER's experience is clamped, and only by apply_resources",
	}


# ---------------------------------------------------------------------------
# The corrected-reason tree scan (design D6)
# ---------------------------------------------------------------------------


## **Zero** client sources state the corpus-cannot-exercise reason for unit
## experience. The expected count is PINNED, so a change in either direction
## fails: a newly stale sentence is a failure, and so is a scan quietly
## narrowed until it finds nothing.
func _check_reason() -> void:
	var sources := _client_sources()
	check(sources.size() > 0,
		"the reason scan walks at least one client source")
	var hits := _reason_scan()
	check_eq(hits.size(), EXPECTED_REASON_HITS,
		"NO client source states the corpus-cannot-exercise reason for unit "
			+ "experience: the real reason is that no trusted award exists, "
			+ "because the field's only writer takes a client-supplied amount "
			+ "and the field has zero legacy readers. Offenders: "
				+ str(_hit_names(hits)))
	for hit: Dictionary in hits:
		check(false,
			"the stale reason is stated in %s: %s"
				% [str(hit["file"]), str(hit["context"])])

	# The scanner is PROVED LIVE, both ways: a crafted sentence naming unit
	# experience IS found, and a negated sentence about a DIFFERENT topic is
	# NOT.
	# Built from FRAGMENTS so this suite's own source does not contain the
	# hunted phrase, which would otherwise make the scan above find its own
	# self-test and report a failure it did not mean.
	var stale := ("unit experience is out of scope because the committed corpus "
		+ "cannot " + "exercise it")
	check(_reason_hits_in(stale.to_lower()).size() == 1,
		"the reason scanner is PROVED LIVE: a crafted stale sentence naming "
			+ "unit experience is found, so the zero result above is a "
			+ "measurement and not a broken scan")
	var other := ("no animation behaviour for the legacy server to have, not "
		+ "merely a corpus that could not " + "exercise it")
	check_eq(_reason_hits_in(other.to_lower()), [],
		"the reason scanner is SCOPED: a negated sentence about a DIFFERENT "
			+ "topic is not a hit, so the zero result is about unit experience "
			+ "and not about the phrase")
	var corrected := ("the corpus figure is a CORPUS FACT, not the reason: 0 of "
		+ "the 40 placed rows in the committed fresh-player corpus carry "
		+ "attr[\"xp\"]")
	check_eq(_reason_hits_in(corrected.to_lower()), [],
		"the corrected text, which LEGITIMATELY keeps the corpus figure, is "
			+ "not a hit: the scan targets the reason construction and not the "
			+ "figure")

	# The normalizer is PROVED EQUIVALENT to the loop it replaced, so the
	# speedup cannot have changed what the scan matches.
	for sample: String in ["", "  ", "\n\n\t", "one two", "  leading and "
			+ "trailing  ", "MiXeD\r\nCaSe", "a  b   c    d",
			"unit experience is out of scope because the corpus cannot exercise it"]:
		check_eq(_normalized_text(sample), _normalized_text_loop(sample),
			"the RegEx normalizer and the per-character loop agree on %s, so the "
				% JSON.stringify(sample)
				+ "speedup cannot have changed what the scan matches")

	# The corrected text is actually present, with BOTH halves of the
	# composite note stating the truth.
	var level_source := _source("res://scripts/town/level_flow.gd")
	var check_note := _note_text(level_source)
	check(check_note.contains("NO TRUSTED AWARD EXISTS"),
		"the user-facing note states the REAL reason: no trusted award exists")
	check(check_note.contains("client-supplied amount"),
		"the user-facing note names the client-supplied amount as the cause")
	check(check_note.contains("zero legacy readers"),
		"the user-facing note names the field's zero legacy readers")
	check(check_note.contains("CORPUS FACT"),
		"the user-facing note labels the corpus figure a corpus fact")
	check(check_note.contains("171 of 12,954"),
		"the user-facing note carries the repository-wide census beside the "
			+ "corpus figure, so the figure is no longer the only one a reader "
			+ "sees")
	check(check_note.contains("Tutorial progression is NOT out of scope"),
		"the composite note's TUTORIAL half still states the truth: tutorial "
			+ "progression is delivered")
	check(check_note.contains("tutorial`") and check_note.contains("line delivers it"),
		"the composite note's tutorial half still names the delivered line, "
			+ "asserted as its two halves so the check survives the note's own "
			+ "literal concatenation")
	# The doc comments were corrected the same way.
	var block := _comment_text(level_source)
	check(block.contains("a fact\n") or block.contains("a fact "),
		"the module's documented bullet labels the 0-of-40 figure a fact "
			+ "about that one document")
	check(block.contains("171 of 12,954"),
		"the module's documented bullet carries the repository-wide census")
	check(block.contains("zero legacy readers"),
		"the module's documented bullets state the real reason")
	var town_source := _source("res://scripts/town/town.gd")
	var town_block := _comment_text(town_source)
	check(town_block.contains("171 of 12,954"),
		"the view's own level-flow documentation was corrected too: it was a "
			+ "SIXTH location stating the stale reason, which the committed "
			+ "investigation's count of five missed")
	check(town_block.contains("Tutorial progression IS delivered"),
		"the view's documentation states that tutorial progression is "
			+ "DELIVERED, not out of scope")


## The scan itself: every client source, every reason construction, every hit
## where a unit-experience token sits within the window.
func _reason_scan() -> Array:
	var hits: Array = []
	for relative: String in _client_sources():
		if relative == REASON_SCAN_SELF:
			continue
		# `relative` is already a `res://` path; globalizing it through
		# `project_dir()` would join an absolute path onto a scheme-prefixed
		# one, which reads nothing and would make the scan vacuously empty.
		var normalized := _normalized_text(
			FileAccess.get_file_as_string(relative))
		for construction: String in REASON_CONSTRUCTIONS:
			var at := normalized.find(construction)
			while at >= 0:
				var from := maxi(at - REASON_WINDOW, 0)
				var window := normalized.substr(from,
					mini(REASON_WINDOW * 2,
						normalized.length() - from))
				if _names_unit_experience(window):
					hits.append({"file": relative, "construction": construction,
						"offset": at, "context": window})
				at = normalized.find(construction, at + 1)
	hits.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var left := "%s:%d" % [str(a["file"]), int(a["offset"])]
		var right := "%s:%d" % [str(b["file"]), int(b["offset"])]
		return left < right)
	return hits


## The hit list for one already-normalised, already-lowercased text.
func _reason_hits_in(normalized: String) -> Array:
	var hits: Array = []
	for construction: String in REASON_CONSTRUCTIONS:
		var at := normalized.find(construction)
		while at >= 0:
			var from := maxi(at - REASON_WINDOW, 0)
			var window := normalized.substr(from,
				mini(REASON_WINDOW * 2, normalized.length() - from))
			if _names_unit_experience(window):
				hits.append({"construction": construction, "context": window})
			at = normalized.find(construction, at + 1)
	return hits


func _names_unit_experience(window: String) -> bool:
	for token: String in UNIT_EXPERIENCE_TOKENS:
		if window.contains(token.to_lower()):
			return true
	return false


func _hit_names(hits: Array) -> Array:
	var names: Array = []
	for hit: Dictionary in hits:
		names.append("%s@%d" % [str(hit["file"]), int(hit["offset"])])
	return names


# ---------------------------------------------------------------------------
# The committed executed-legacy fixture
# ---------------------------------------------------------------------------


## The committed fixture's own manifest when it is present, and an explicit
## absent marker when it is not. **No transaction table is ever invented**: a
## missing fixture yields an empty table and a named cause, so a reader can
## tell the difference between "recorded" and "not yet recorded".
func _check_fixture() -> Dictionary:
	var directory := Paths.repo_root().path_join(FIXTURE_DIR)
	var manifest_path := directory.path_join(FIXTURE_MANIFEST)
	if not DirAccess.dir_exists_absolute(directory):
		return {
			"present": false,
			"directory": FIXTURE_DIR,
			"cause": "the committed executed-legacy fixture directory is not "
				+ "in the working tree at all, so this suite read NO "
				+ "transaction data and wrote NO table from any source",
			"transactions": [],
			"table_is_empty_because": "the fixture is absent, NOT because the "
				+ "branch has no executed evidence: docs/legacy-unit-xp.md §4 "
				+ "records 22 executed transactions against a disposable corpus "
				+ "seeded from the committed village save villages/AcidCaos.json",
			"not_invented": true,
		}
	check(true, "the committed executed-legacy fixture directory is present")
	if not FileAccess.file_exists(manifest_path):
		return {
			"present": false,
			"directory": FIXTURE_DIR,
			"cause": "the fixture directory exists but carries no "
				+ FIXTURE_MANIFEST + ", so this suite read NO transaction data",
			"transactions": [],
			"not_invented": true,
		}
	check(true, "the fixture's own manifest is present")
	var manifest_text := FileAccess.get_file_as_string(manifest_path)
	var manifest: Variant = JSON.parse_string(manifest_text)
	check(manifest is Dictionary,
		"the fixture's manifest parses as JSON")
	if not (manifest is Dictionary):
		return {"present": false, "directory": FIXTURE_DIR,
			"cause": "the manifest did not parse", "transactions": [],
			"not_invented": true}
	var document: Dictionary = manifest as Dictionary

	var manifest_sha := Paths.file_sha256(manifest_path)
	var top_keys: Array = document.keys()
	top_keys.sort()

	# The transactions the manifest actually records, copied field by field
	# and never restated.
	var transactions: Array = []
	for entry: Variant in (document.get("transactions", []) as Array):
		if not (entry is Dictionary):
			continue
		var row: Dictionary = entry as Dictionary
		var copied := {}
		for field: String in TRANSACTION_FIELDS:
			if row.has(field):
				copied[field] = _normalized(row[field])
		var carried: Array = row.keys()
		carried.sort()
		copied["fields_present"] = carried
		copied["fields_missing"] = _missing_fields(carried)
		transactions.append(copied)
	var step_names := _directory_names(directory.path_join("steps"))

	# The recorded manifest facts, read rather than asserted.
	var recorded: Dictionary = {
		"schema": str(document.get("schema", "")),
		"exit_code": _as_int(document.get("exit_code", null)),
		"container_shipped": str(document.get("invocation", "")),
		"seed": _seed_record(document),
		"containment_identical": bool((document.get("containment", {}) as Dictionary)
		.get("identical", false)),
		"containment_pre": str((document.get("containment", {}) as Dictionary)
			.get("pre_combined_sha256", "")),
		"containment_post": str((document.get("containment", {}) as Dictionary)
			.get("post_combined_sha256", "")),
	}
	check_eq(str(recorded["containment_pre"]), str(recorded["containment_post"]),
		"the fixture's own manifest records an IDENTICAL containment digest "
			+ "before and after its executed pass")
	check_eq(int(recorded["exit_code"]), 0,
		"the fixture's own manifest records a zero exit code")

	# The changed-leaf proof, read out of the transactions themselves.
	var leaf_counts: Array = []
	var neutral_leaf_counts: Array = []
	for row: Dictionary in transactions:
		if not row.has("changed_leaves"):
			continue
		var leaves: Array = row["changed_leaves"] as Array
		leaf_counts.append(leaves.size())
		var all_xp_leaves := true
		for leaf: Variant in leaves:
			if not str(leaf).ends_with("/xp"):
				all_xp_leaves = false
		if all_xp_leaves:
			neutral_leaf_counts.append(leaves.size())
	check(leaf_counts.size() > 0,
		"the fixture's transactions record a changed-leaf set each, so the "
			+ "one-leaf proof is READ rather than asserted")
	var one_leaf := 0
	for count: Variant in leaf_counts:
		if int(count) == 1:
			one_leaf += 1
	check(one_leaf > 0,
		"at least one recorded transaction moved EXACTLY ONE leaf, which is "
			+ "the branch's own stored effect")
	check(neutral_leaf_counts.size() > 0,
		"at least one recorded transaction moved only /xp leaves, so the "
			+ "one-addressed-row proof holds for it")

	# The display-only comparison, read out of the recorded transactions.
	var display_only := _display_only_pair(transactions)
	check(bool(display_only.get("found", false)),
		"the fixture records BOTH the two-argument and the three-argument form "
			+ "of the branch, so the third argument's ignorability is "
			+ "established by recorded post-states rather than by argument")
	if bool(display_only.get("found", false)):
		check_eq(display_only["post_states_identical"], true,
			"the recorded two-argument and three-argument post-states are "
				+ "IDENTICAL, which is the measurement that makes the third "
				+ "argument ignorable")
		check_eq(display_only["leaf_sets_identical"], true,
			"the recorded two-argument and three-argument changed-leaf sets "
				+ "are IDENTICAL, so the argument's absence from the "
				+ "post-state is not a missing write")

	return {
		"present": true,
		"directory": FIXTURE_DIR,
		"manifest": FIXTURE_MANIFEST,
		"manifest_sha256": manifest_sha,
		"manifest_top_level_keys": top_keys,
		"manifest_bytes": manifest_text.length(),
		"recorded": recorded,
		"step_names": step_names,
		"transactions": transactions,
		"transaction_count": transactions.size(),
		"changed_leaf_counts": leaf_counts,
		"one_leaf_transactions": one_leaf,
		"display_only": display_only,
		"not_invented": true,
		"read_from": "the committed fixture's own manifest; every field above "
			+ "is COPIED from it and every missing field is listed per "
			+ "transaction in fields_missing",
	}


## The two-argument and three-argument forms, paired by their recorded
## command and arguments, compared on post-state and leaf set.
func _display_only_pair(transactions: Array) -> Dictionary:
	var two: Array = []
	var three: Array = []
	for row: Dictionary in transactions:
		var args: Variant = row.get("args", null)
		if not (args is Array):
			continue
		var list: Array = args as Array
		if list.size() == 2:
			two.append(row)
		elif list.size() == 3:
			three.append(row)
	if two.is_empty() or three.is_empty():
		return {"found": false, "two_argument_count": two.size(),
			"three_argument_count": three.size(),
			"note": "the manifest records no pair of the two-argument and "
				+ "three-argument forms, so the display-only claim is NOT "
				+ "established by this suite's own read of it. The recorded "
				+ "contract in production_flow.gd still states the rule and "
				+ "the investigation records the measurement"}
	var left: Dictionary = two[0]
	var right: Dictionary = three[0]
	var same_args: bool = str((left["args"] as Array)[0]) \
		== str((right["args"] as Array)[0]) \
		and str((left["args"] as Array)[1]) == str((right["args"] as Array)[1])
	return {
		"found": true,
		"two_argument_count": two.size(),
		"three_argument_count": three.size(),
		"same_row_and_amount": same_args,
		"two_argument_after": left.get("attr_after", null),
		"three_argument_after": right.get("attr_after", null),
		"post_states_identical": _normalized(left.get("attr_after", null)) \
			== _normalized(right.get("attr_after", null)),
		"two_argument_leaves": left.get("changed_leaves", null),
		"three_argument_leaves": right.get("changed_leaves", null),
		"leaf_sets_identical": _normalized(left.get("changed_leaves", null)) \
			== _normalized(right.get("changed_leaves", null)),
		"printed_output_differs": "the recorded contract in production_flow.gd "
			+ "states the printed lines differ (+5xp against +5xp BOUGHT LEVEL "
			+ "UP -> 9); printed output is NOT a recorded state leaf, so this "
			+ "suite reads the difference from the contract rather than "
			+ "inventing a transcript",
	}


func _seed_record(document: Dictionary) -> Dictionary:
	var corpus: Dictionary = document.get("corpus", {}) as Dictionary
	var seed: Dictionary = corpus.get("seed", {}) as Dictionary
	return {
		"path": str(seed.get("path", "")),
		"file_sha256": str(seed.get("file_sha256", "")),
		"pid": str(corpus.get("pid", "")),
		"seeded_as": str(corpus.get("seeded_as", "")),
	}


func _missing_fields(carried: Array) -> Array:
	var out: Array = []
	for field: String in TRANSACTION_FIELDS:
		if not carried.has(field):
			out.append(field)
	return out


# ---------------------------------------------------------------------------
# The boundary and purity guards
# ---------------------------------------------------------------------------


## No client source computes an award, a unit level, a threshold, or a
## schedule from this field; the delivered surface exposes no route and no
## intent; and the module is pure.
func _check_boundary() -> void:
	var sources := _client_sources()
	check(sources.size() > 0, "the boundary scan walks the client source tree")
	for relative: String in sources:
		var code := _code_only(_source(relative))
		for helper: String in FORBIDDEN_HELPERS:
			check(not _declares_identifier(code, helper),
				"no client source declares an '%s' helper: %s"
					% [helper, relative])
	# No route, no intent, no facade operation: the delivered client has nothing
	# to send for this field.
	for route: String in ["/v0/unit_xp", "/v0/add_xp_unit", "/v0/experience",
			"/v0/award_xp", "/v0/unit_experience"]:
		check(not _source("res://scripts/gameapi/legacy_v0_api.gd").contains(
				route),
			"the legacy-v0 implementation names no %s route: this line adds "
				% route + "NO endpoint")
	var facade: Variant = root.get_node_or_null("GameApi")
	check(facade != null, "GameApi autoload is registered")
	if facade != null:
		var methods: Variant = facade.get_script().get_script_method_list()
		for name: String in ["add_xp_unit_town", "unit_xp_town",
				"award_experience_town", "experience_town"]:
			check(_method(methods, name) == null,
				"the facade exposes NO %s operation: there is no award intent "
					% name + "to send and nothing to authorise")
	check_eq(BootData.QUEUE_ACTIONS, ["push", "pop"],
		"the v0 endpoint's closed action vocabulary is unchanged: this line "
			+ "adds no action")


## The delivered module is pure: no node, no clock, no request, no transport,
## and exactly the two read-only models preloaded.
func _check_purity() -> void:
	var source := _source(DELIVERED_SCRIPT)
	for needle: String in PURITY_NEEDLES:
		check(not _code_only(source).contains(needle),
			"the delivered module carries no '%s' token: it is pure" % needle)
	check_eq(_preloads(source), EXPECTED_PRELOADS,
		"the delivered module preloads EXACTLY the two read-only models, so "
			+ "it reaches neither content nor transport behind its contract")
	check(not _working_saves_exist(),
		"this line creates no working-tree saves/")


## The read working-tree groups are byte-identical after the run: this line
## measures committed bytes and writes nothing outside its report.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, villages_before: Dictionary,
		legacy_before: Dictionary) -> void:
	for entry: Variant in [["content package", "packages/game-content",
			package_before],
			["committed saves", "tests/saves", saves_before],
			["committed villages", "villages", villages_before],
			["legacy root modules", "(11 root *.py files)", legacy_before]]:
		var label := str(entry[0])
		var relative := str(entry[1])
		var before: Dictionary = entry[2]
		var after: Dictionary = Paths.directory_digest(
			Paths.repo_root().path_join(relative))
		if relative.begins_with("("):
			after = _legacy_digest()
		check_eq(str(after.get("sha256", "")), str(before.get("sha256", "")),
			"the %s is byte-identical after the run" % label)
	# The committed FIXTURES group is compared apart from this suite's own
	# report, which is written under apps/client-godot/evidence/ and not under
	# tests/fixtures/.
	var fixtures_after := Paths.directory_digest(
		Paths.repo_root().path_join("tests/fixtures"))
	check_eq(str(fixtures_after.get("sha256", "")),
		str(fixtures_before.get("sha256", "")),
		"the committed fixtures are byte-identical after the run: this suite "
			+ "reads them and writes nothing there")


# ---------------------------------------------------------------------------
# The deterministic report
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


## The deterministic `unit-experience-report-v1` report.
##
## Every contract fact comes from `production_flow.gd`'s own constants; every
## census, legacy, and boundary figure comes from the measurement this same run
## performed; every executed fact comes from the committed fixture's own
## manifest, **or is explicitly marked absent**. Nothing here reads the wall
## clock, resolves a path outside the repository, or sends a request, so the
## file is byte-identical across reruns — with ONE recorded exception: the
## fixture block changes if the fixture is added later, which is a change of
## input and not of nondeterminism.
func _write_report(path: String, kinds: Dictionary, census: Dictionary,
		corpus: Dictionary, legacy: Dictionary, fixture: Dictionary) -> void:
	var report := {
		"schema": "unit-experience-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_experience.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from "
				+ "production_flow.gd's own constants, this same run's "
				+ "measurements over the committed bytes, and the fixture's "
				+ "own recorded manifest, and every derived list is sorted "
				+ "before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) plus "
				+ "one trailing newline; every number written is an integer "
				+ "where the value is integral - the pinned engine's integral "
				+ "floats are normalised on the way in, which changes no "
				+ "value",
			"time_dependent_fields": "NONE in this line's hermetic evidence: "
				+ "the projection reads a bag, the census reads committed save "
				+ "documents, and the legacy figures are measured out of the "
				+ "committed source",
			"recorded_input_change": "the `fixture` block is the ONE place "
				+ "whose content depends on whether "
				+ "tests/fixtures/godot-unit-experience is committed. It is "
				+ "written from that manifest and marked absent otherwise, so "
				+ "a change there is a change of INPUT and is recorded rather "
				+ "than hidden",
		},
		"projection": {
			"contract": (kinds.get("record", {}) as Dictionary).duplicate(
				true),
			"field_set": ["ok", "reason", "error", "recorded",
				"recorded_is_absent", "recorded_kind", "awarded",
				"award_source", "award_implemented", "contract",
				"corpus_note"],
			"fields_added_by_this_line": ["recorded_kind"],
			"fields_removed_by_this_line": [],
			"fields_whose_meaning_changed": [],
			"vocabulary": ProductionFlow.recorded_kind_vocabulary(),
			"vocabulary_size": ProductionFlow.RECORDED_KINDS.size(),
			"note_int": str(kinds.get("note_int", "")),
			"note_absent": str(kinds.get("note_absent", "")),
		},
		"kind_cases": (kinds.get("rows", []) as Array).duplicate(true),
		"kind_cases_count": (kinds.get("rows", []) as Array).size(),
		"census": {
			"repository_wide": census,
			"fresh_corpus": corpus,
			"split": {
				"established": "the field is on %d of %d placed rows across "
					% [EXPECTED_CENSUS_ROWS_WITH_XP, EXPECTED_CENSUS_ROWS]
					+ "%d committed save documents, every recorded value is "
					% EXPECTED_CENSUS_DOCUMENTS
					+ "an integer, and the field is written twice and read "
					+ "zero times",
				"derived": "nothing about the AWARD is derived: the amount "
					+ "reaches the field as a client argument, so no award, "
					+ "threshold, unit level, or schedule is reproduced "
					+ "anywhere in this repository",
				"labelling": "the fresh corpus's 0-of-40 figure is a FACT "
					+ "ABOUT THAT ONE DOCUMENT and is never evidence about "
					+ "the repository nor evidence that an award exists",
			},
		},
		"legacy": legacy,
		"fixture": fixture,
		"reason_scan": {
			"constructions": REASON_CONSTRUCTIONS.duplicate(),
			"unit_experience_tokens": UNIT_EXPERIENCE_TOKENS.duplicate(),
			"window_characters": REASON_WINDOW,
			"client_sources_scanned": _client_sources().size(),
			"roots": CLIENT_SCAN_ROOTS.duplicate(),
		"excluded": REASON_SCAN_SELF,
		"excluded_because": "this suite carries the stale sentence as its "
			+ "negative control, so scanning itself would report the control "
			+ "as an offender of the rule the control exists to test",
			"expected_hits": EXPECTED_REASON_HITS,
			"hits": _reason_scan(),
			"hit_count": _reason_scan().size(),
			"targets_the_construction_not_the_figure": "the corrected text "
				+ "LEGITIMATELY keeps the corpus figure and labels it, so the "
				+ "scan hunts the reason construction and the figure is never "
				+ "the needle",
			"scope_limit": "the scan is scoped to unit experience by a "
				+ "proximity window. The repository also holds NEGATED "
				+ "occurrences of the same constructions about production, "
				+ "animation, movement, and resurrection; none of them is this "
				+ "capability's reason, and the suite proves that scoping by "
				+ "asserting a negated sentence about another topic is not a "
				+ "hit",
			"corrected_locations": [
				"apps/client-godot/scripts/town/level_flow.gd (FOUR: the "
					+ "module's own FIRST doc line at :1, the two documented "
					+ "blocks, and the user-facing note string)",
				"apps/client-godot/scripts/town/town.gd (one documented "
					+ "block at :329-330) - the SIXTH, which the committed "
					+ "investigation's count of five did not record",
				"the SEVENTH was level_flow.gd:1, and it is the only one of "
					+ "the seven that the delivered TREE SCAN found rather "
					+ "than a reader: the investigation enumerated five, a "
					+ "second reader found a sixth, and the guard found the "
					+ "seventh in the most prominent line in the file. That "
					+ "is the whole argument for a scan over an enumeration",
				"apps/client-godot/scripts/units/production_flow.gd (the "
					+ "module header, which recorded the supersession by "
					+ "quoting the superseded construction and now records it "
					+ "by reference; NOT one of the seven stale locations - the "
					+ "sharp reason was already there)",
				"apps/client-godot/tests/test_unit_production.gd (one "
					+ "assertion MESSAGE, widened to name its own 40-row "
					+ "scope; no expected value, threshold, or intent "
					+ "changed)",
				"AGENTS.md and apps/client-godot/README.md (two prose "
					+ "locations) - NOT this suite's: see task 5.2",
			],
		},
		"guards": {
			"anti_invention": {
				"whole_static_function_inventory": _declared_methods(
					_source(DELIVERED_SCRIPT)),
				"pinned_inventory_size": EXPECTED_MODULE_METHODS.size(),
				"forbidden_helpers": FORBIDDEN_HELPERS.duplicate(),
				"absent_helpers_recorded": ProductionFlow.ABSENT_HELPERS
					.size(),
				"injection_note": "the guard counts as PROVEN only because it "
					+ "was made to FAIL by injection and the file restored "
					+ "from a byte-identical copy; see the change's report",
			},
			"no_arithmetic": {
				"experience_surface": EXPERIENCE_SURFACE.duplicate(),
				"numeric_operators": NUMERIC_OPERATORS.duplicate(),
				"numeric_conversions": NUMERIC_CONVERSIONS.duplicate(),
				"percent_operator_excluded_because": "% is GDScript's "
					+ "string-format operator in this module and is never a "
					+ "modulo, so it is recorded as excluded rather than "
					+ "silently dropped",
				"extraction": "each surface function's body is extracted BY "
					+ "NAME from the module's own source and is asserted to be "
					+ "a real body before anything is asserted about it",
			},
		},
		"provenance": {
			"established": [
				"the field has exactly two occurrences of attr['xp'] in the "
				+ "committed dispatcher, both inside add_xp_unit "
				+ "(command.py:336 and command.py:338), and both are WRITES",
				"the field has ZERO readers across all ten legacy root "
				+ "modules: no branch, engine helper, session function, or "
				+ "migration consults a unit's recorded total",
				"the amount is client args[1] with no validation of any kind, "
				+ "not even an int() call",
				"the optional third argument is client args[2], falsy-tested "
				+ "and used ONLY inside a printed line, written nowhere",
				"only the PLAYER's experience is clamped, by apply_resources "
				+ "(engine.py:251-271) at command.py:40, before the dispatch; "
				+ "the row accumulator has no floor and no bound",
				"the repository-wide census: %d of %d placed rows across %d "
				% [EXPECTED_CENSUS_ROWS_WITH_XP, EXPECTED_CENSUS_ROWS,
					EXPECTED_CENSUS_DOCUMENTS]
				+ "committed save documents carry the field, every recorded "
				+ "value an integer",
				"the fresh corpus's own figure: 0 of %d placed rows"
				% EXPECTED_CORPUS_ROWS,
			],
			"derived_provisional": [
				"the disposable seed's CHOICE (the fixture's manifest records "
				+ "which committed save it used and why)",
				"the recommendation that a future consumer ACCEPTS AND IGNORES "
				+ "the display-only third argument rather than refusing it",
				"the recommendation shape for a client consumer of this "
				+ "contract, which this line implements no part of",
			],
			"not_established": [
				"what amount the Flash client actually sent in args[1]",
				"whether the committed per-unit experience field was the "
				+ "intended per-award value in a client this legacy server "
				+ "never received",
				"whether a unit level exists anywhere in the original game",
			],
		},
		"non_claims": [
			"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
				+ ", or browser executed",
			"NO EXPERIENCE IS AWARDED AND NO AWARD IS DERIVABLE: the field's "
			+ "only writer takes a client-supplied amount and the field has "
			+ "zero legacy readers, so there is no trusted award to reproduce",
			"NO ENDPOINT, ROUTE, ENVELOPE, OR CLIENT INTENT IS ADDED: with no "
			+ "route there is no request to authorise",
			"NO UNIT LEVEL, THRESHOLD, OR SCHEDULE EXISTS OR IS INTRODUCED: "
			+ "every level-shaped key in the content package is player-level, "
			+ "price-tier, or magic-gate keyed",
			"THE COMMITTED PER-UNIT EXPERIENCE FIELD IS NOT ADOPTED AS AN "
			+ "AWARD: it has zero legacy consumers and three measurements "
			+ "contradict it",
			"THE THIRD ARGUMENT IS DISPLAY-ONLY: it is recorded and never "
			+ "stored, never surfaced as a level the row reached, and never "
			+ "used to derive a threshold",
			"THE CORPUS'S ABSENCE OF THE FIELD REMAINS TRUE OF THAT CORPUS and "
			+ "is a FACT ABOUT THE CORPUS, not evidence about the repository",
			"NO LEVEL REWARD IS PAID OR INVENTED: reward_type, reward_amount, "
			+ "and level_ranking_reward all have zero legacy consumers",
			"PARITY COVERS THE FIXTURE'S RECORDED TRANSACTIONS AGAINST ONE "
			+ "PROGRESSED VILLAGE SAVE AND NO FRESH-PLAYER CORPUS TRANSACTION",
			"NO WINDOWED CAPTURE AND NO PIXEL-PARITY ORACLE IS CLAIMED, because "
			+ "nothing is rendered",
			"THIS LINE'S HERMETIC SUITE CANNOT DETECT ENVELOPE OR WIRE DRIFT, "
			+ "because it builds no request: there is no endpoint",
		],
	}
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)"
		% problem)
	if problem == "":
		check(FileAccess.file_exists(path), "the report file exists at %s" % path)
		info("report written: %s" % path)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A source's CODE: comment lines dropped and string-literal contents blanked,
## so a prose mention or a recorded contract string can never be mistaken for
## code.
func _code_only(body: String) -> String:
	var out: Array = []
	for line: String in body.split("\n"):
		if line.strip_edges().begins_with("#"):
			out.append("")
			continue
		out.append(_blank_literals(line))
	return "\n".join(PackedStringArray(out))


## One line with its string-literal contents blanked, two-state so an escaped
## quote cannot desynchronise the scan.
func _blank_literals(line: String) -> String:
	var out := ""
	var in_string := false
	var index := 0
	while index < line.length():
		var character := line[index]
		if in_string:
			if character == "\\":
				index += 2
				continue
			if character == "\"":
				in_string = false
			index += 1
			continue
		if character == "\"":
			in_string = true
			index += 1
			continue
		out += character
		index += 1
	return out


## The public and private function names a module declares, sorted. Used for
## the whole-inventory guard.
func _declared_methods(body: String) -> Array:
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


## The method extractor proved live against a planted body, so a broken
## extractor cannot make the inventory guard vacuously true.
func _methods_live() -> Array:
	var planted := ("static func award_experience(a) -> int:\n\treturn a\n"
		+ "func int_(b):\n\treturn b\n"
		+ "static func round_(c) -> int:\n\treturn c\n")
	var found: Array = []
	for line: String in planted.split("\n"):
		var signature := line.strip_edges()
		if signature.begins_with("static func "):
			signature = signature.substr(len("static "))
		if not signature.begins_with("func "):
			continue
		var name := signature.substr(len("func "))
		var bracket := name.find("(")
		found.append(name if bracket == -1 else name.substr(0, bracket))
	found.sort()
	return found


## Every script a module loads, in committed order.
func _preloads(body: String) -> Array:
	var out: Array = []
	for line: String in body.split("\n"):
		var signature := line.strip_edges()
		if not signature.begins_with("const "):
			continue
		var open := signature.find("preload(\"")
		if open == -1:
			continue
		var start := open + len("preload(\"")
		out.append(signature.substr(start,
			signature.find("\"", start) - start))
	return out


## ONE function's body, extracted by name from the code-only source: from its
## declaration to the next unindented, non-empty line. An empty result means
## the function was NOT found, which every caller treats as a failure.
func _function_body(code: String, name: String) -> String:
	var lines := code.split("\n")
	var start := -1
	for index in range(lines.size()):
		var line: String = str(lines[index])
		var signature := line.strip_edges()
		if signature.begins_with("static func "):
			signature = signature.substr(len("static "))
		if not signature.begins_with("func "):
			continue
		var declared := signature.substr(len("func "))
		var bracket := declared.find("(")
		if (declared if bracket == -1 else declared.substr(0, bracket)) != name:
			continue
		start = index + 1
		break
	if start == -1:
		return ""
	var body: Array = []
	for index in range(start, lines.size()):
		var line: String = str(lines[index])
		if not line.is_empty() and not line.begins_with(" ") \
				and not line.begins_with("\t"):
			break
		body.append(line)
	return "\n".join(PackedStringArray(body))


## Every numeric operator and numeric conversion in a body, as readable
## findings. A conversion token is matched behind a non-identifier character so
## `int(` never matches `print(`.
func _numeric_occurrences(body: String, operators: Array,
		conversions: Array) -> Array:
	var found: Array = []
	for token: Variant in operators:
		var needle := str(token)
		var at := body.find(needle)
		while at >= 0:
			found.append({"token": needle, "offset": at,
				"context": body.substr(maxi(at - 20, 0), 40)})
			at = body.find(needle, at + 1)
	for token: Variant in conversions:
		var needle := str(token)
		var at := body.find(needle)
		while at >= 0:
			if at == 0 or not _is_identifier_char(body[at - 1]):
				found.append({"token": needle, "offset": at,
					"context": body.substr(maxi(at - 20, 0), 40)})
			at = body.find(needle, at + 1)
	found.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var left := "%s:%d" % [str(a["token"]), int(a["offset"])]
		var right := "%s:%d" % [str(b["token"]), int(b["offset"])]
		return left < right)
	return found


func _is_identifier_char(character: String) -> bool:
	return character == "_" or character.to_lower() != character.to_upper()


## Every field on a record that exposes a NUMBER derived from its value. The
## empty result is the claim: a recorded experience is not readable as a
## quantity anywhere on the record.
func _numeric_keys(record: Dictionary) -> Array:
	var out: Array = []
	for key: Variant in record.keys():
		var value: Variant = record[key]
		if value is int or value is float:
			out.append(str(key))
	out.sort()
	return out


## Every field on a record that holds a NUMBER derived from the recorded value,
## EXCLUDING `recorded` itself. `recorded` is the value verbatim by contract,
## so a caller reading it sees the stored type and not a derived quantity;
## every OTHER field is scanned, and the empty result is the claim that nothing
## on the record turns the value into a readable number.
func _derived_numeric_keys(record: Dictionary) -> Array:
	var out: Array = []
	for key: Variant in record.keys():
		if str(key) == "recorded":
			continue
		var value: Variant = record[key]
		if value is int or value is float:
			out.append(str(key))
	out.sort()
	return out


## Every numeric reading of a value a record exposes. The empty result is the
## no-coercion proof.
func _numeric_readings(value: Variant) -> Array:
	var out: Array = []
	if value is String:
		var text := str(value)
		if text.is_valid_int():
			out.append("int_form")
		if text.is_valid_float():
			out.append("float_form")
	if value is Array or value is Dictionary:
		out.append("structural_form")
	return out


## Every `.gd` file under the scan roots, as full `res://` paths, sorted.
func _client_sources() -> Array:
	var out: Array = []
	for directory: String in CLIENT_SCAN_ROOTS:
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
		if entry != "." and entry != ".." and not entry.begins_with("."):
			var path := directory.path_join(entry)
			if handle.current_is_dir():
				_collect_gd(path, out)
			elif entry.ends_with(".gd"):
				out.append(path)
		entry = handle.get_next()
	handle.list_dir_end()


## Every `.json` file directly in a directory, as repo-relative paths, sorted.
func _json_files(directory: String) -> Array:
	var out: Array = []
	var handle := DirAccess.open(directory)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if not handle.current_is_dir() and entry.ends_with(".json"):
			out.append(directory.replace(Paths.repo_root() + "/", "") + "/"
				+ entry)
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort()
	return out


## The sub-directory names of a directory, sorted — a fixture's recorded step
## names, never their contents.
func _directory_names(directory: String) -> Array:
	var out: Array = []
	var handle := DirAccess.open(directory)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if handle.current_is_dir():
			out.append(entry)
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort()
	return out


## A text with every whitespace run collapsed to one space, lowercased — the
## form the reason scan matches, so a construction split across two source
## lines is still found.
##
## Implemented with `RegEx` rather than a per-character loop. The loop spelled
## the same rule but appended to a `String` once per character, which is
## quadratic over the 4.8 MB client source tree: **measured at 171 seconds for
## one scan, against well under a second here**. `RegEx` is a standard GDScript
## type, so this introduces no dependency, and the equivalence is asserted
## against the loop's own output below rather than assumed.
static var _whitespace_run: RegEx = null


func _whitespace_run_regex() -> RegEx:
	if _whitespace_run == null:
		_whitespace_run = RegEx.new()
		# `\\s+` covers exactly the four characters the loop tested, plus the
		# vertical tab and form feed, which no GDScript source uses and which
		# collapsing to a space cannot change any match.
		_whitespace_run.compile("\\s+")
	return _whitespace_run


func _normalized_text(text: String) -> String:
	return _whitespace_run_regex().sub(text, " ", true).strip_edges().to_lower()


## The loop this replaced, kept as the equivalence oracle.
func _normalized_text_loop(text: String) -> String:
	var out := ""
	var pending := false
	for index in range(text.length()):
		var character := text[index]
		if character == " " or character == "\t" or character == "\n" \
				or character == "\r":
			pending = true
			continue
		if pending and out != "":
			out += " "
		pending = false
		out += character.to_lower()
	return out


## The module's OWN comment text, so a documented block can be read back.
func _comment_text(source: String) -> String:
	var out: Array = []
	for line: String in source.split("\n"):
		var stripped := line.strip_edges()
		if stripped.begins_with("#"):
			out.append(stripped.substr(1).strip_edges())
	return "\n".join(PackedStringArray(out))


## The user-facing note string `NON_CLAIMS` carries, assembled from its
## concatenated literals, so the composite note is read WHOLE rather than as
## separate source lines.
func _note_text(source: String) -> String:
	var at := source.find("const NON_CLAIMS")
	if at == -1:
		return ""
	var from := at
	var to := source.find("\n\n", from)
	if to == -1:
		to = source.length()
	var block := source.substr(from, to - from)
	var out: Array = []
	for line: String in block.split("\n"):
		var pieces := line.split("\"")
		var index := 1
		while index < pieces.size() - 1:
			out.append(pieces[index])
			index += 2
	return " ".join(PackedStringArray(out))


## Whether a body declares an identifier by name, matched behind a
## non-identifier character so `add_xp` never matches `add_xp_unit`.
## Whether one line names an identifier, matched behind a non-identifier
## character on BOTH sides. The plain-substring spelling is deliberately NOT
## used: the key is `xp`, which occurs inside ordinary words such as `exp`,
## so a substring test measures the wrong thing.
func _names_identifier(line: String, identifier: String) -> bool:
	var at := line.find(identifier)
	while at >= 0:
		var before_ok := at == 0 or not _is_identifier_char(line[at - 1])
		var after := at + identifier.length()
		var after_ok := after >= line.length() \
				or not _is_identifier_char(line[after])
		if before_ok and after_ok:
			return true
		at = line.find(identifier, at + 1)
	return false


func _declares_identifier(code: String, identifier: String) -> bool:
	var at := code.find(identifier)
	while at >= 0:
		var before_ok := at == 0 or not _is_identifier_char(code[at - 1])
		var after := at + identifier.length()
		var after_ok := after >= code.length() \
			or not _is_identifier_char(code[after])
		if before_ok and after_ok:
			return true
		at = code.find(identifier, at + 1)
	return false


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


## A value normalised for comparison: integral floats become integers, because
## the pinned engine's JSON parser yields them and the report's determinism
## must not depend on a float's serialization.
func _normalized(value: Variant) -> Variant:
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_normalized(entry))
		return list
	if value is Dictionary:
		var bag := {}
		for key: Variant in (value as Dictionary).keys():
			bag[str(key)] = _normalized((value as Dictionary)[key])
		return bag
	return value


func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


func _sorted_keys(values: Dictionary) -> Array:
	var out: Array = values.keys()
	out.sort()
	return out


func _legacy_lines(module: String) -> Array:
	return FileAccess.get_file_as_string(
		Paths.repo_root().path_join(module)).split("\n")


## A SHA-256 over the eleven root legacy modules, so containment is compared
## against a recorded digest rather than a file count.
func _legacy_digest() -> Dictionary:
	var combined := ""
	var modules: Array = []
	var handle := DirAccess.open(Paths.repo_root())
	if handle != null:
		handle.list_dir_begin()
		var entry := handle.get_next()
		while entry != "":
			if not handle.current_is_dir() and entry.ends_with(".py"):
				modules.append(entry)
			entry = handle.get_next()
		handle.list_dir_end()
	modules.sort()
	if modules.size() != 11:
		return {"ok": false, "error": "expected 11 root *.py files, found %d"
			% modules.size(), "sha256": "", "modules": modules.size()}
	for module: String in modules:
		combined += "%s:%s\n" % [module, Paths.file_sha256(
			Paths.repo_root().path_join(module))]
	return {"ok": true, "error": "", "sha256": Paths.sha256_hex(
		combined.to_utf8_buffer()), "modules": modules.size()}


func _method(methods: Variant, name: String) -> Variant:
	if not (methods is Array):
		return null
	for entry: Variant in methods as Array:
		if str((entry as Dictionary).get("name", "")) == name:
			return entry
	return null


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	return JSON.parse_string(FileAccess.get_file_as_string(path))


func _source(res_path: String) -> String:
	return FileAccess.get_file_as_string(res_path)


func _working_saves_exist() -> bool:
	return DirAccess.dir_exists_absolute(
		Paths.repo_root().path_join("saves"))


## Serializes deterministically (sorted keys, tab indent, one trailing
## newline) and writes the report, creating the destination directory when
## needed.
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
