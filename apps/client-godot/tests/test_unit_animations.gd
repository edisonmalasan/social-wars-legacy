extends "res://tests/test_base.gd"
## Unit-animations suite (OpenSpec `godot-unit-animations` "An animation asset
## is projected as linkage, never as behaviour" / "Committed animation fields are
## content with no legacy consumer" / "The committed max_frame is not the asset's
## frame count" / "No legacy branch selects an animation, and no state machine is
## derived" / "Animation is content, not a server operation" / "No
## executed-legacy animation fixture is claimed" / "Unit-animation evidence and
## claim limits", design D1-D7).
##
## This line delivers a LINKAGE PROJECTION plus a set of refusals, so a large part
## of what it asserts is an **absence**. The anti-invention guard is structural:
## the delivered module's whole function inventory is compared against a pinned
## list, so a duration, loop, state-machine, transition, priority, interrupt,
## timing, trigger, or playback helper fails the run wherever it is added -
## verified by injecting one and watching the suite fail.
##
## Checks:
##   projection  the recorded labels, their recorded frame positions, the
##               per-sprite recorded frame counts, and the recorded rate, each
##               reported verbatim out of the committed converted package;
##   refusal     an absent, unreadable, label-less, malformed-label, unreferenced,
##               and comma-joined-reference asset each refused with its recorded
##               state intact and never defaulted;
##   content     the six committed animation fields plus the `animal` flag as
##               content only, the zero-consumer fact, and the measured committed
##               distributions over both item domains;
##   max_frame   the three measured numbers, the refusal to adopt the committed
##               field as a frame count, and the one-data-point statement;
##   inventory   the 63-branch inventory, the five vocabulary matches each with
##               its classification and reason, and the zero animation commands;
##   refusals    every refusal family present with a non-empty reason, and the
##               module declares EXACTLY the linkage accessors of D1-D5 and none
##               of the ABSENT_HELPERS;
##   boundary    no compatibility surface and no animate intent;
##   coverage    the one-package coverage measured, and the ambiguous-reference
##               refusal over the committed set;
##   legacy      every recorded legacy figure re-derived from the committed source
##               in this same run, so no count is taken on trust.
##
## `--report=<path>` writes the deterministic `unit-animations-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-animations/report.json`. The tables are derived from the live
## module and from the measurements this run performed, so they cannot drift from
## the code and the source they document.

## `Paths` is inherited from `test_base.gd`; only the module is new here.
const UnitAnimations = preload("res://scripts/units/unit_animations.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-animations/report.json"

## The five reported linkage fields, in committed table order.
const EXPECTED_FIELD_NAMES := [
	"labels", "label_frame_positions", "sprite_frame_counts",
	"root_frame_count", "frame_rate",
]

## The one committed converted unit package, repository-relative.
const PACKAGE_RELATIVE := "assets/converted/units/10033_wild_elephant/package.json"

## The committed unit whose own `img_name` names that package.
const COVERED_UNIT_ID := "933"

## A committed unit whose `img_name` is a comma-joined list rather than one
## sprite reference, so the ambiguous-reference refusal is exercised over the
## committed content rather than over invented input.
const AMBIGUOUS_UNIT_ID := "1001"

## A committed unit whose `img_name` names no committed converted package, so the
## absent-asset refusal is exercised through the real resolution path.
const UNCONVERTED_UNIT_ID := "923"

## The five labels the one committed converted package records, verbatim and in
## committed order, each with its recorded frame position. This table is the
## suite's own transcription of the committed bytes, so a projection that altered
## a name, a position, the order, or the anchor fails the run.
const EXPECTED_LABELS := [
	{"name": "QUIETO", "frame": 1, "anchor": false},
	{"name": "ANDAR", "frame": 6, "anchor": false},
	{"name": "ATAQUE", "frame": 11, "anchor": false},
	{"name": "MUERTE", "frame": 16, "anchor": false},
	{"name": "PICAR", "frame": 21, "anchor": false},
]

## The seven recorded sprites, verbatim: five at 20 frames with no labels, one at
## 7 with no labels, and the labelled one at 29. NOTE the placement and remove
## counts of the labelled sprite: ELEVEN placements and SEVEN removes, not five
## placements - the five direct shape placements are only part of its timeline.
const EXPECTED_SPRITES := [
	{"sprite_id": 19, "frame_count": 20, "label_count": 0,
		"placement_count": 5, "remove_count": 0},
	{"sprite_id": 28, "frame_count": 20, "label_count": 0,
		"placement_count": 5, "remove_count": 0},
	{"sprite_id": 37, "frame_count": 20, "label_count": 0,
		"placement_count": 5, "remove_count": 0},
	{"sprite_id": 46, "frame_count": 20, "label_count": 0,
		"placement_count": 5, "remove_count": 0},
	{"sprite_id": 55, "frame_count": 20, "label_count": 0,
		"placement_count": 5, "remove_count": 0},
	{"sprite_id": 62, "frame_count": 7, "label_count": 0,
		"placement_count": 3, "remove_count": 0},
	{"sprite_id": 63, "frame_count": 29, "label_count": 5,
		"placement_count": 11, "remove_count": 7},
]

## The seven recorded sprite ids, in committed order.
const EXPECTED_SPRITE_IDS := [19, 28, 37, 46, 55, 62, 63]

## Every refusal family the delta's refusal requirement names, and that the
## recorded `REFUSALS` inventory must cover by exact name.
const EXPECTED_REFUSAL_FAMILIES := [
	"frame_duration", "frame_time", "loop_count", "state_machine",
	"transition", "priority", "interrupt", "playback_order",
	"per_state_timing", "animation_trigger", "event_state_mapping",
	"playback",
]

## The absent-helper families the recorded `ABSENT_HELPERS` inventory must name
## between them, one per family the contract refuses to invent.
const ABSENT_FAMILIES := [
	"frame_duration", "frame_time", "loop_count", "state_machine",
	"next_state", "state_priority", "interrupt", "playback_order",
	"per_state_timing", "animation_trigger", "event_state_mapping",
	"play", "animate", "current_frame", "advance_frame",
]

## Every absence flag a projection carries, and which must be false whether the
## projection resolved or was refused.
const ABSENCE_FLAGS := [
	"rate_applied", "duration_computed", "frame_time_computed",
	"loop_count_computed", "state_machine_derived", "transition_derived",
	"priority_computed", "interrupt_computed", "playback_order_derived",
	"per_state_timing_computed", "animation_trigger_derived",
	"event_state_mapping_derived", "intermediate_frame_computed",
	"elapsed_frame_computed", "max_frame_adopted_anywhere",
	"max_frame_adopted_as_frame_count", "max_frame_adopted_as_duration",
	"max_frame_adopted_as_loop_bound", "max_frame_adopted_as_state_count",
]

## The tokens a client source must not carry for this line to have added no
## animate operation anywhere.
const ANIMATE_TOKENS := ["animate_unit", "/v0/animate", "/v0/animation",
	"play_animation", "select_state", "animation_trigger(", "frame_duration(",
	"state_machine("]


func run_scenario() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var loaded: Dictionary = registry.load_content()
	check_eq(bool(loaded.get("ok", false)), true,
		"the committed content package verifies and loads: the projection's "
			+ "definition side is read through the registry, not from the file")

	var package := _read_package()
	var legacy := _check_legacy()
	var projection := _check_projection(registry, package)
	var refusal := _check_refusal(registry, package)
	var content := _check_content(registry)
	var max_frame := _check_max_frame(registry, package)
	var inventory := _check_command_inventory()
	var refusals := _check_refusals()
	_check_absence()
	_check_boundary()
	var coverage := _check_coverage(registry)

	var digests := _input_digests()

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, loaded, package, legacy, projection,
			refusal, content, max_frame, inventory, refusals, coverage, digests)


# ---------------------------------------------------------------------------
# The linkage projection (requirement 1)
# ---------------------------------------------------------------------------

## Every label the committed package records, in committed order, read straight
## out of its own bytes with no interpretation: the root timeline's own labels
## first, then each sprite's own labels in recorded sprite order.
func _committed_labels(package: Dictionary) -> Array:
	var out: Array = []
	var main_timeline: Variant = package.get("main", null)
	if main_timeline is Dictionary:
		for entry: Variant in (main_timeline as Dictionary).get(
				"labels", []) as Array:
			if entry is Dictionary:
				out.append(entry)
	var sprites: Variant = package.get("sprites", null)
	if not (sprites is Array):
		return out
	for sprite: Variant in (sprites as Array):
		if not (sprite is Dictionary):
			continue
		for entry: Variant in (sprite as Dictionary).get("labels", []) as Array:
			if entry is Dictionary:
				out.append(entry)
	return out


## The committed definition for one unit id, as the registry reports it.
func _definition(registry: Variant, id_text: String) -> Variant:
	var resolved: Dictionary = registry.get_entry("units", id_text)
	if not bool(resolved.get("found", false)):
		fail("the committed unit definition %s resolves" % id_text)
		return {}
	return resolved["entry"]


## Every reported value is compared against the committed bytes this suite read
## itself, so "verbatim" is a measurement rather than a claim.
func _check_projection(registry: Variant, package: Dictionary) -> Dictionary:
	var measured: Dictionary = {
		"labels": 0, "sprites": 0, "resolved": 0,
		"package_legacy_id": "", "asset_named_by_content": false,
		"frame_rate": 0.0, "root_frame_count": 0,
	}

	check_eq(UnitAnimations.linkage_field_names(), EXPECTED_FIELD_NAMES,
		"the reported linkage fields are exactly the five the contract names, "
			+ "in committed table order")
	check_eq(UnitAnimations.LINKAGE_FIELD_COUNT, EXPECTED_FIELD_NAMES.size(),
		"the recorded field count matches the recorded names")

	# every reported field names its own recorded source, and no two share one
	var unsourced: Array = []
	var sources: Array = []
	for entry: Dictionary in UnitAnimations.linkage_field_inventory():
		var source := str(entry.get("source", ""))
		if source == "" or str(entry.get("source_kind", "")) == "":
			unsourced.append(str(entry.get("name", "?")))
			continue
		if sources.has(source):
			unsourced.append(str(entry.get("name", "?")) + " shares a source")
		sources.append(source)
		check_eq(bool(entry.get("verbatim", false)), true,
			"the reported field %s is recorded as verbatim"
				% str(entry.get("name", "?")))
	check_eq(unsourced, [],
		"every reported linkage field names its own recorded source, and no two "
			+ "fields share one: a derived field would have to name its source's "
			+ "field as well as its own")

	var definition: Variant = _definition(registry, COVERED_UNIT_ID)
	var result: Dictionary = UnitAnimations.resolve_asset(definition)

	check_eq(bool(result.get("ok", false)), true,
		"the one committed converted unit package resolves for the committed "
			+ "definition that names it")
	check_eq(bool(result.get("resolvable", false)), true,
		"the projection reports the asset as resolvable")
	check_eq(str(result.get("package_relative_path", "")),
		UnitAnimations.CONVERTED_UNITS_DIR + "/" + str(
			definition.get("img_name", "")) + "/" + UnitAnimations.PACKAGE_FILE,
		"the committed package path is derived only from the committed "
			+ "sprite reference the definition names")
	check_eq(str(result.get("package_legacy_id", "")),
		UnitAnimations.COVERED_UNIT_SPRITE_REFERENCE,
		"the resolved package is the one committed converted unit package")
	check_eq(str(result.get("package_kind", "")), "converted_unit",
		"the resolved package is recorded as a converted unit package")
	check_eq(bool(result.get("asset_named_by_content", false)), true,
		"the committed definition's sprite reference EQUALS the resolved "
			+ "package's own legacy id, so both describe the SAME unit: that "
			+ "identity is what makes the max_frame comparison a comparison of "
			+ "one unit with itself")
	measured["package_legacy_id"] = str(result.get("package_legacy_id", ""))
	measured["asset_named_by_content"] = bool(
		result.get("asset_named_by_content", false))
	measured["resolved"] = 1

	# -- the recorded labels, verbatim and in recorded order -----------------
	check_eq(str(result.get("asset_state", "")), UnitAnimations.ASSET_RESOLVED,
		"the projection records how the asset was resolved")
	check_eq(int(result.get("label_count", -1)), EXPECTED_LABELS.size(),
		"the projection reports exactly the FIVE recorded labels")
	measured["labels"] = int(result.get("label_count", 0))
	var reported: Array = result.get("labels", []) as Array
	check_eq(reported.size(), EXPECTED_LABELS.size(),
		"the reported label list has one entry per recorded label")
	var committed_labels := _committed_labels(package)
	check_eq(reported.size(), committed_labels.size(),
		"the reported label count equals the count this suite read out of the "
			+ "committed package itself")
	for index: int in range(mini(reported.size(), EXPECTED_LABELS.size())):
		var got: Dictionary = reported[index] as Dictionary
		var want: Dictionary = EXPECTED_LABELS[index]
		check_eq(str(got.get("name", "")), str(want["name"]),
			"label %d is reported verbatim by name" % index)
		check_eq(int(got.get("frame", -1)), int(want["frame"]),
			"label %s is reported at its recorded frame position %d"
				% [str(want["name"]), int(want["frame"])])
		check_eq(bool(got.get("anchor", true)), bool(want["anchor"]),
			"label %s reports its recorded anchor verbatim" % str(want["name"]))
		check_eq(got.get("recorded_keys", []), UnitAnimations.LABEL_KEYS,
			"label %s reports the committed key set %s, so a label carrying "
				% [str(want["name"]), str(UnitAnimations.LABEL_KEYS)]
				+ "more than names, positions, and an anchor would be visible")
		if index < committed_labels.size():
			var raw: Dictionary = committed_labels[index] as Dictionary
			check_eq(got.get("name"), raw.get("name"),
				"label %d's name matches the committed bytes exactly, with no "
					% index
					+ "re-encoding")
			check_eq(got.get("frame"), raw.get("frame"),
				"label %d's frame position matches the committed bytes exactly, "
					% index
					+ "with no rounding or conversion")
			check_eq(got.get("anchor"), raw.get("anchor"),
				"label %d's anchor matches the committed bytes exactly" % index)
	check_eq(result.get("label_order", []),
		[UnitAnimations.LABEL_SOURCE_SPRITE_PREFIX + "63",
			UnitAnimations.LABEL_SOURCE_SPRITE_PREFIX + "63",
			UnitAnimations.LABEL_SOURCE_SPRITE_PREFIX + "63",
			UnitAnimations.LABEL_SOURCE_SPRITE_PREFIX + "63",
			UnitAnimations.LABEL_SOURCE_SPRITE_PREFIX + "63"],
		"all five recorded labels are reported as recorded on sprite 63, and "
			+ "the root timeline's own empty label list is not invented into")
	check_eq(int(result.get("labelled_sprite_id", -1)), 63,
		"the projection names the one sprite that carries the recorded labels")
	check_eq(int(result.get("labelled_sprite_frame_count", -1)), 29,
		"the labelled sprite's own recorded frame count is reported verbatim")
	check_eq(int(result.get("recorded_label_count", -1)),
		EXPECTED_LABELS.size(),
		"the recorded label count equals the reported label count for a "
			+ "resolvable asset")

	# -- the recorded frame counts and rate, verbatim ------------------------
	check_eq(int(result.get("root_frame_count", -1)),
		int(package.get("frame_count", -2)),
		"the asset root's own recorded frame count is reported verbatim out of "
			+ "the committed package")
	check_eq(int(result.get("main_timeline_frame_count", -1)),
		int((package.get("main", {}) as Dictionary).get("frame_count", -2)),
		"the root main timeline's own recorded frame count is reported verbatim")
	check_eq(str(result.get("frame_rate", "")),
		str(package.get("frame_rate", "")),
		"the recorded frame rate is reported exactly as recorded")
	measured["frame_rate"] = float(str(result.get("frame_rate", "0")))
	measured["root_frame_count"] = int(result.get("root_frame_count", 0))
	check_eq(bool(result.get("rate_applied", true)), false,
		"the recorded rate is reported but never applied")
	check_eq(str(result.get("rate_applied_to", "unset")), "",
		"the recorded rate is applied to nothing at all")

	var rows: Array = result.get("sprite_frame_counts", []) as Array
	check_eq(rows.size(), EXPECTED_SPRITES.size(),
		"the projection reports every recorded sprite's own frame count")
	measured["sprites"] = rows.size()
	check_eq(int(result.get("sprite_count", 0)), EXPECTED_SPRITES.size(),
		"the recorded sprite count is reported verbatim")
	var ids: Array = []
	var placement_total := 0
	var remove_total := 0
	for index: int in range(mini(rows.size(), EXPECTED_SPRITES.size())):
		var got: Dictionary = rows[index] as Dictionary
		var want: Dictionary = EXPECTED_SPRITES[index]
		ids.append(int(got.get("sprite_id", -1)))
		check_eq(int(got.get("sprite_id", -1)), int(want["sprite_id"]),
			"sprite %d is reported verbatim by id" % index)
		check_eq(int(got.get("frame_count", -1)), int(want["frame_count"]),
			"sprite %s reports its own recorded frame count verbatim"
				% str(want["sprite_id"]))
		check_eq(int(got.get("label_count", -1)), int(want["label_count"]),
			"sprite %s reports its own recorded label count verbatim"
				% str(want["sprite_id"]))
		check_eq(int(got.get("placement_count", -1)),
			int(want["placement_count"]),
			"sprite %s reports its own recorded placement count verbatim"
				% str(want["sprite_id"]))
		check_eq(int(got.get("remove_count", -1)), int(want["remove_count"]),
			"sprite %s reports its own recorded remove count verbatim"
				% str(want["sprite_id"]))
		placement_total += int(want["placement_count"])
		remove_total += int(want["remove_count"])
	check_eq(ids, EXPECTED_SPRITE_IDS,
		"the recorded sprites are reported in committed order")
	check_eq(placement_total, 39,
		"the seven recorded sprites carry 39 placements between them, which is "
			+ "why the labelled sprite's ELEVEN placements (not five) matter")
	check_eq(remove_total, 7,
		"the only recorded removes belong to the labelled sprite, which records "
			+ "seven of them")
	check_eq(int(result.get("root_placement_count", -1)),
		((package.get("main", {}) as Dictionary).get("placements", []) as Array).size(),
		"the root timeline's own recorded placement count is reported verbatim")
	check_eq(int(result.get("root_remove_count", -1)),
		((package.get("main", {}) as Dictionary).get("removes", []) as Array).size(),
		"the root timeline's own recorded remove count is reported verbatim")

	# -- no derivation, structurally and behaviourally ------------------------
	for flag: String in ABSENCE_FLAGS:
		check_eq(bool(result.get(flag, true)), false,
			"the projection reports %s as false" % flag)
	check(str(result.get("no_derivation", "")).contains("NO VALUE"),
		"the projection carries the no-derivation contract")
	check(str(result.get("asset_refusal", "")).contains("NEVER DEFAULTED"),
		"the projection carries the asset-refusal contract")
	check(str(result.get("readout", "")).contains("REPORTED, NEVER APPLIED"),
		"the readout states that the recorded rate is reported, never applied")
	check(str(result.get("readout", "")).contains("QUIETO"),
		"the readout renders the recorded label names verbatim")

	# the same package projected twice differs in nothing
	var again: Dictionary = UnitAnimations.resolve_asset(definition)
	check_eq(again, result,
		"the same committed package projected twice is identical: nothing is "
			+ "derived, sampled, or time-dependent")

	# an absurd set of committed animation fields leaves every linkage field
	# untouched: this is the behavioural proof that the recorded fields are read
	# as content and never as a rule
	var absurd: Dictionary = (definition as Dictionary).duplicate(true)
	absurd["max_frame"] = 999999
	absurd["attack"] = 999999
	absurd["attack_interval"] = 999999
	absurd["attack_range"] = 999999
	absurd["velocity"] = 999999
	var poisoned: Dictionary = UnitAnimations.resolve_asset(absurd)
	for linkage: String in ["labels", "label_count", "label_order",
			"labelled_sprite_id", "labelled_sprite_frame_count",
			"root_frame_count", "main_timeline_frame_count", "frame_rate",
			"sprite_frame_counts", "sprite_count", "sprite_placement_counts",
			"sprite_remove_counts", "root_placement_count", "root_remove_count"]:
		check_eq(poisoned.get(linkage), result.get(linkage),
			"absurd committed animation fields leave the reported %s untouched: "
				% linkage
				+ "no linkage value is computed from a committed animation field")
	check_eq(int(poisoned.get("content_fields", {}).get("max_frame", 0)),
		999999,
		"the absurd committed max_frame is reported back verbatim as content")
	return measured


# ---------------------------------------------------------------------------
# The fail-closed path (requirement 1, second half)
# ---------------------------------------------------------------------------

## Absent, unreadable, label-less, malformed, unreferenced, and ambiguous assets
## each fail closed with their recorded state intact and never default.
func _check_refusal(registry: Variant, package: Dictionary) -> Dictionary:
	var measured: Dictionary = {"refusals": 0, "ambiguous": 0}
	var definition: Variant = _definition(registry, COVERED_UNIT_ID)

	var cases: Array = [
		{"label": "an absent asset", "package": null,
			"state": UnitAnimations.ASSET_ABSENT,
			"reason": UnitAnimations.REASON_ASSET_ABSENT},
		{"label": "an unreadable asset", "package": "not-a-package",
			"state": UnitAnimations.ASSET_UNREADABLE,
			"reason": UnitAnimations.REASON_ASSET_UNREADABLE},
		{"label": "an asset claimed resolved but carrying nothing",
			"package": null, "state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_ASSET_UNREADABLE},
		{"label": "a label-less asset", "package": _label_less_package(),
			"state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_NO_LABELS},
		{"label": "an asset whose sprite list is unreadable",
			"package": {"frame_count": 4, "frame_rate": 12.0, "sprites": 7},
			"state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_ASSET_UNREADABLE},
		{"label": "a label entry that is not an object",
			"package": _package_with_labels(["not-a-label"]),
			"state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_MALFORMED_LABEL},
		{"label": "a label entry missing its recorded frame",
			"package": _package_with_labels([{"name": "X", "anchor": false}]),
			"state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_MALFORMED_LABEL},
		{"label": "a label entry missing its recorded name",
			"package": _package_with_labels([{"frame": 3, "anchor": false}]),
			"state": UnitAnimations.ASSET_RESOLVED,
			"reason": UnitAnimations.REASON_MALFORMED_LABEL},
	]
	for case: Dictionary in cases:
		var result: Dictionary = UnitAnimations.project_asset(definition,
			case["package"], str(case["state"]))
		var label := str(case["label"])
		check_eq(bool(result.get("ok", true)), false, "%s is refused" % label)
		check_eq(str(result.get("reason", "")), str(case["reason"]),
			"%s is refused with its recorded reason" % label)
		check_eq(bool(result.get("resolvable", true)), false,
			"%s produces no resolved linkage" % label)
		check_eq(int(result.get("label_count", -1)), 0,
			"%s reports no label, never a defaulted one" % label)
		check_eq(result.get("labels", ["defaulted"]), [],
			"%s reports an empty label list rather than a nominal animation"
				% label)
		check(str(result.get("error", "")).length() > 0,
			"%s names the offending state in its error" % label)
		check(result.get("root_frame_count", 1) != 1
				or bool(case["package"]) == false,
			"%s never reports a nominal single frame where none was recorded"
				% label)
		for flag: String in ABSENCE_FLAGS:
			check_eq(bool(result.get(flag, true)), false,
				"%s still reports %s as false: a refusal is not a default"
					% [label, flag])
		measured["refusals"] += 1

	# the label-less asset keeps its OWN recorded state beside the refusal
	var label_less: Dictionary = UnitAnimations.project_asset(definition,
		_label_less_package(), UnitAnimations.ASSET_RESOLVED)
	check_eq(int(label_less.get("root_frame_count", -1)), 7,
		"a label-less asset still reports its own recorded root frame count "
			+ "beside the refusal")
	check_eq(str(label_less.get("frame_rate", "")),
		str(_label_less_package().get("frame_rate", "")),
		"a label-less asset still reports its own recorded rate")
	check_eq((label_less.get("sprite_frame_counts", []) as Array).size(), 2,
		"a label-less asset still reports its own recorded per-sprite frame "
			+ "counts")

	# a malformed label reports the recorded label COUNT even though it reports
	# no label, so nothing is silently shortened
	var malformed: Dictionary = UnitAnimations.project_asset(definition,
		_package_with_labels([{"name": "X", "anchor": false}]),
		UnitAnimations.ASSET_RESOLVED)
	check_eq(int(malformed.get("recorded_label_count", -1)), 1,
		"a malformed label entry still reports the recorded label count beside "
			+ "the refusal")

	# a definition that names no committed sprite reference at all
	var unreferenced: Dictionary = UnitAnimations.resolve_asset({})
	check_eq(bool(unreferenced.get("ok", true)), false,
		"a committed definition carrying no sprite reference is refused")
	check_eq(str(unreferenced.get("reason", "")),
		UnitAnimations.REASON_NO_SPRITE_REFERENCE,
		"the refusal names the missing sprite reference")

	# a committed definition whose committed sprite reference is COMMA-JOINED
	var ambiguous_definition: Variant = _definition(registry, AMBIGUOUS_UNIT_ID)
	var ambiguous: Dictionary = UnitAnimations.resolve_asset(ambiguous_definition)
	check_eq(bool(ambiguous.get("ok", true)), false,
		"a committed definition whose sprite reference is a comma-joined list "
			+ "is refused: it names no single asset")
	check_eq(str(ambiguous.get("reason", "")),
		UnitAnimations.REASON_AMBIGUOUS_SPRITE_REFERENCE,
		"the refusal names the ambiguous sprite reference")
	check(ambiguous.get("error", "").to_lower().contains("comma"),
		"the refusal states that the reference is comma-joined and is not split")
	measured["ambiguous"] = 1

	# a committed definition whose sprite reference names NO committed package
	var unconverted: Dictionary = UnitAnimations.resolve_asset(
		_definition(registry, UNCONVERTED_UNIT_ID))
	check_eq(bool(unconverted.get("ok", true)), false,
		"a committed definition naming no committed converted package is "
			+ "refused through the real resolution path")
	check_eq(str(unconverted.get("reason", "")),
		UnitAnimations.REASON_ASSET_ABSENT,
		"the missing-package refusal is the absent-asset reason")
	check(str(unconverted.get("package_relative_path", "")).length() > 0,
		"the refused resolution still reports the path it looked for")
	check_eq(unconverted.get("root_frame_count", 1), null,
		"an absent asset reports a null root frame count, never a nominal 1")
	check_eq(int(unconverted.get("label_count", -1)), 0,
		"an absent asset reports no label, never a single-frame animation")

	# an invalid definition is a NAMED ABSENCE of the committed fields, never a
	# reason to refuse the linkage itself
	var bad_definition: Dictionary = UnitAnimations.project_asset(
		"not-a-definition", package, UnitAnimations.ASSET_RESOLVED)
	check_eq(bool(bad_definition.get("ok", false)), true,
		"an invalid committed definition does not refuse the asset linkage")
	check_eq(bad_definition.get("content_absent", []),
		UnitAnimations.ANIMATION_FIELDS,
		"an invalid committed definition reports all six animation fields "
			+ "ABSENT, never as committed zeros")
	check_eq(bad_definition.get("content_fields", {"any": true}), {},
		"an invalid committed definition substitutes no animation field value")
	check_eq(int(bad_definition.get("label_count", 0)),
		EXPECTED_LABELS.size(),
		"the linkage itself still projects every recorded label")
	measured["invalid_definition"] = true
	return measured


## A crafted package that records sprites and a rate but **no** label anywhere.
func _label_less_package() -> Dictionary:
	return {
		"kind": "converted_unit",
		"legacy_id": "crafted_label_less",
		"frame_count": 7,
		"frame_rate": 12.0,
		"main": {"frame_count": 7, "labels": [], "placements": [], "removes": []},
		"sprites": [
			{"sprite_id": 1, "frame_count": 7, "labels": [],
				"placements": [], "removes": []},
			{"sprite_id": 2, "frame_count": 3, "labels": [],
				"placements": [], "removes": []},
		],
	}


## A crafted package carrying the given label entries on one sprite, so a
## malformed entry is exercised over a well-formed asset around it.
func _package_with_labels(entries: Array) -> Dictionary:
	return {
		"kind": "converted_unit",
		"legacy_id": "crafted_malformed",
		"frame_count": 5,
		"frame_rate": 24.0,
		"main": {"frame_count": 5, "labels": [], "placements": [], "removes": []},
		"sprites": [
			{"sprite_id": 4, "frame_count": 5, "labels": [],
				"placements": [], "removes": []},
			{"sprite_id": 9, "frame_count": 11, "labels": entries,
				"placements": [], "removes": []},
		],
	}


# ---------------------------------------------------------------------------
# The committed animation fields as content (requirement 2)
# ---------------------------------------------------------------------------

func _check_content(registry: Variant) -> Dictionary:
	var record: Dictionary = UnitAnimations.animation_fields_record()
	var measured: Dictionary = {"units_total": 0, "buildings_total": 0,
		"units_flag": 0, "buildings_flag": 0, "units_max_frame": {},
		"buildings_max_frame": {}, "distinct": {}, "distribution": {}}

	check_eq(bool(record.get("reported_as_content_only", false)), true,
		"the committed animation fields are recorded as reported content only")
	check_eq(bool(record.get("used_as_a_rule", false)), false,
		"the committed animation fields are recorded as NOT used as a rule")
	check_eq(record.get("fields", []), UnitAnimations.ANIMATION_FIELDS,
		"the recorded animation-field list is the six the contract names")
	check_eq(str(record.get("flag", "")), UnitAnimations.ANIMATION_FLAG,
		"the recorded properties flag is the one the contract names")
	check_eq(int(record.get("consumer_count", -1)),
		UnitAnimations.ANIMATION_FIELD_CONSUMER_COUNT,
		"the recorded legacy consumer count for the animation fields is zero")
	check_eq(record.get("searched_modules", []), UnitAnimations.SEARCHED_MODULES,
		"the recorded searched-module list is the seven legacy modules")

	var per_field: Dictionary = record.get("consumer_count_per_field", {})
	for field: String in UnitAnimations.ANIMATION_FIELDS:
		check_eq(int(per_field.get(field, -1)), 0,
			"the recorded legacy consumer count for `%s` is zero" % field)
	check_eq(int(per_field.get(UnitAnimations.ANIMATION_FLAG, -1)), 0,
		"the recorded legacy consumer count for the `%s` flag is zero"
			% UnitAnimations.ANIMATION_FLAG)

	# the zero-consumer precedents, and the ordinal
	check(int(record.get("zero_consumer_precedents", []).size()) == 6,
		"the six earlier zero-consumer committed fields are named as precedents")
	for precedent: Dictionary in record.get("zero_consumer_precedents", []):
		check(str(precedent.get("field", "")).length() > 0,
			"each named precedent states which committed field it is")
		check(str(precedent.get("fact", "")).length() > 0,
			"each named precedent states its recorded fact")
	check_eq(int(record.get("zero_consumer_ordinal", 0)),
		UnitAnimations.MAX_FRAME_ORDINAL,
		"max_frame is recorded as the seventh zero-consumer committed field")
	check_eq(int(record.get("zero_consumer_ordinal", 0)),
		int(record.get("zero_consumer_precedents", []).size()) + 1,
		"the recorded ordinal is exactly one more than the named precedents, "
			+ "so it cannot drift from them")

	# the committed coverage, measured over both verified domains in this run
	for domain: String in ["units", "buildings"]:
		var listed: Dictionary = registry.legacy_ids(domain)
		check_eq(bool(listed.get("found", false)), true,
			"the %s domain is present in the verified registry" % domain)
		var ids: Array = listed.get("ids", [])
		check(ids.size() > 0,
			"the %s domain enumerates at least one committed id" % domain)
		check(str(listed.get("file", "")).length() > 0,
			"the %s domain records the committed file it was read from" % domain)
		measured["%s_total" % domain] = ids.size()
		var distribution := {}
		var flags := 0
		var present := 0
		var typed := 0
		var exceptions: Array = []
		var counts := {}
		for field: String in UnitAnimations.ANIMATION_FIELDS:
			counts[field] = {}
		for id_text: Variant in ids:
			var entry: Dictionary = registry.get_entry(domain,
				str(id_text)).get("entry", {}) as Dictionary
			var value: Variant = entry.get("max_frame", null)
			var key := _numeric_key(value)
			distribution[key] = int(distribution.get(key, 0)) + 1
			if not (value is String):
				typed += 1
			if key != "5" and domain == "units":
				exceptions.append(str(id_text))
			for field: String in UnitAnimations.ANIMATION_FIELDS:
				if entry.has(field):
					present += 1
				var raw: Variant = entry.get(field, null)
				var value_key := "%s:%s" % [type_string(typeof(raw)),
					str(raw)]
				var per_field_counts: Dictionary = counts[field]
				per_field_counts[value_key] = int(per_field_counts.get(
					value_key, 0)) + 1
			var properties: Dictionary = {}
			if entry.get("properties") is Dictionary:
				properties = entry["properties"] as Dictionary
			if _committed_flag(properties, UnitAnimations.ANIMATION_FLAG):
				flags += 1
		measured["%s_max_frame" % domain] = distribution
		measured["%s_flag" % domain] = flags
		measured["distribution"][domain] = {
			"max_frame": distribution,
			"animation_fields_present": present,
			"definitions": ids.size(),
			"flag_set": flags,
		}
		if domain == "units":
			measured["units_max_frame_typed"] = typed
			measured["units_fields_present"] = present
			measured["units_exceptions"] = exceptions
			for field: String in UnitAnimations.ANIMATION_FIELDS:
				measured["distinct"][field] = (
					counts[field] as Dictionary).size()
	measured["distribution"]["distinct_unit_values"] = (
		measured["distinct"] as Dictionary).duplicate()
	measured["distribution"]["max_frame_encoding"] = (
		"NUMBER on all %d committed units and a STRING on none of them, unlike "
			% UnitAnimations.UNIT_COUNT
		+ "the string-encoded properties flags")

	check_eq(measured["units_total"], UnitAnimations.UNIT_COUNT,
		"the committed units domain holds 429 definitions")
	check_eq(measured["buildings_total"], UnitAnimations.BUILDING_COUNT,
		"the committed buildings domain holds 470 definitions")
	check_eq(measured["units_max_frame"],
		UnitAnimations.MAX_FRAME_UNIT_DISTRIBUTION,
		"the measured committed max_frame over the 429 units is 5 on 427 of "
			+ "them and 2 on exactly two")
	check_eq(measured["buildings_max_frame"],
		UnitAnimations.MAX_FRAME_BUILDING_DISTRIBUTION,
		"the measured committed max_frame over the 470 buildings takes only 1 "
			+ "(on 24 of them) and 2 (on 446)")
	check_eq(measured["units_exceptions"], UnitAnimations.MAX_FRAME_UNIT_EXCEPTIONS,
		"the two units whose committed max_frame is not 5 are exactly legacy "
			+ "ids 923 and 933")
	check_eq(int(measured["units_max_frame"].get("5", 0)),
		UnitAnimations.MAX_FRAME_UNIT_MODAL_COUNT,
		"the near-constant is 5 on exactly 427 committed units")
	check_eq(int(measured["units_max_frame"].get("5", 0)),
		UnitAnimations.UNIT_COUNT - 2,
		"the near-constant covers every committed unit but the two recorded "
			+ "exceptions")
	check_eq(int(measured["units_max_frame_typed"]), UnitAnimations.UNIT_COUNT,
		"the committed max_frame is a NUMBER on every one of the 429 units and "
			+ "a string on none of them, unlike the committed properties flags")

	# every field present on every unit, with its measured distinct-value count
	for field: String in UnitAnimations.ANIMATION_FIELDS:
		check_eq(record.get("distinct_unit_values", {}).get(field, -1),
			(measured["distinct"] as Dictionary).get(field, -2),
			"the recorded distinct-value count for `%s` is the measured one"
				% field)
		check_eq(int(record.get("distinct_unit_values", {}).get(field, 0)),
			int((measured["distinct"] as Dictionary).get(field, 0)),
			"the recorded and measured distinct-value counts for `%s` agree "
				% field
				+ "numerically")
	check_eq(int(measured["units_fields_present"]),
		UnitAnimations.UNIT_COUNT * UnitAnimations.ANIMATION_FIELDS.size(),
		"all six committed animation fields are present on all 429 committed "
			+ "units")
	check_eq(int(record.get("unit_count", 0)), int(measured["units_total"]),
		"the recorded unit count is the measured one")

	check_eq(int(measured["units_flag"]), 2,
		"the committed `animal` flag is set on exactly 2 of the 429 committed "
			+ "units, read through the committed STRING encoding: a "
			+ "truthiness read would miscount the committed \"0\" values")
	check_eq(int(measured["buildings_flag"]), 0,
		"the committed `animal` flag is carried by none of the 470 committed "
			+ "buildings")

	# the recorded coverage sentence, and the per-field note
	check(str(record.get("rule", "")).contains("ZERO legacy consumers"),
		"the recorded animation-field refusal states the zero-consumer fact")
	check(str(record.get("coverage", "")).contains("427"),
		"the recorded coverage states the near-constant 427-of-429 figure")
	check(str(record.get("coverage", "")).contains("923"),
		"the recorded coverage names the two recorded exception ids")
	check(str(record.get("encoding", "")).contains("NUMBER"),
		"the recorded encoding states that max_frame is committed as a JSON "
			+ "number, unlike the string-encoded properties flags")

	var note: String = UnitAnimations.animation_field_note("max_frame", 2)
	check(note.contains("2"),
		"the animation-field note reports the committed value")
	check(note.contains("CONTENT ONLY"),
		"the animation-field note records that the value is content only")
	check_eq(UnitAnimations.animation_field_note("defense", 1), "",
		"a field outside the recorded animation inventory renders no note, so "
			+ "the note table cannot be widened silently")

	var absent: Dictionary = UnitAnimations.animation_field_values(
		{"max_frame": 5})
	check_eq(absent.get("present", []), ["max_frame"],
		"a definition missing five of the six fields reports exactly the one it "
			+ "carries")
	check_eq(absent.get("absent", []).size(),
		UnitAnimations.ANIMATION_FIELDS.size() - 1,
		"a definition missing five of the six fields names the other five as "
			+ "ABSENT, never as committed zeros")
	return measured


# ---------------------------------------------------------------------------
# The measured max_frame non-equivalence (requirement 3)
# ---------------------------------------------------------------------------

## All three numbers measured in this same run, and the refusal to adopt the
## committed field as a frame count.
func _check_max_frame(registry: Variant, package: Dictionary) -> Dictionary:
	var record: Dictionary = UnitAnimations.non_equivalence_record()
	var measured: Dictionary = {}

	var definition: Variant = _definition(registry, COVERED_UNIT_ID)
	var projection: Dictionary = UnitAnimations.resolve_asset(definition)
	var content_ref: Dictionary = package.get("content_ref", {}) as Dictionary

	var committed_value: Variant = (definition as Dictionary).get("max_frame", null)
	var root_count: Variant = package.get("frame_count", null)
	var labelled_count: Variant = projection.get(
		"labelled_sprite_frame_count", null)

	measured["committed_max_frame"] = committed_value
	measured["parsed_root_frame_count"] = root_count
	measured["labelled_sprite_frame_count"] = labelled_count
	measured["package_content_ref_max_frame"] = content_ref.get("max_frame", null)
	measured["content_img_name"] = str((definition as Dictionary).get("img_name",
		""))
	measured["package_legacy_id"] = str(package.get("legacy_id", ""))

	check_eq(int(record.get("committed_max_frame", -1)),
		int(committed_value),
		"the recorded committed max_frame is the measured one for the covered "
			+ "unit")
	check_eq(int(record.get("parsed_root_frame_count", -1)), int(root_count),
		"the recorded parsed root frame count is the measured one")
	check_eq(int(record.get("labelled_sprite_frame_count", -1)),
		int(labelled_count),
		"the recorded labelled sprite's frame count is the measured one")
	check_eq(int(record.get("labelled_sprite_id", -1)),
		int(projection.get("labelled_sprite_id", -1)),
		"the recorded labelled sprite id is the measured one")
	check_eq(int(measured["package_content_ref_max_frame"]),
		int(committed_value),
		"the converted package's own committed copy of the definition carries "
			+ "the SAME committed max_frame, so the comparison is against one "
			+ "unit and not two")

	check(int(committed_value) != int(root_count),
		"the committed max_frame and the parsed root frame count DISAGREE: "
			+ "%s against %s" % [str(committed_value), str(root_count)])
	check(int(root_count) != int(labelled_count),
		"the parsed root frame count and the labelled sprite's own frame count "
			+ "DISAGREE: %s against %s" % [str(root_count), str(labelled_count)])
	check(int(committed_value) != int(labelled_count),
		"the committed max_frame and the labelled sprite's own frame count "
			+ "DISAGREE: %s against %s"
			% [str(committed_value), str(labelled_count)])
	check_eq(str(record.get("agreement", "")), "NONE: 2 against 1 against 29",
		"the recorded agreement string names all three measured numbers")

	check_eq(bool(record.get("max_frame_is_the_asset_frame_count", true)), false,
		"the record states that the committed max_frame is NOT the asset's "
			+ "parsed frame count")
	for role: String in ["adopted_as_frame_count", "adopted_as_duration",
			"adopted_as_loop_bound", "adopted_as_state_count", "adopted_anywhere"]:
		check_eq(bool(record.get(role, true)), false,
			"the record states that max_frame is adopted nowhere as %s"
				% role)
	check_eq(str(record.get("max_frame_role", "")),
		str(projection.get("max_frame_role", "")),
		"the projection and the record agree that the field's only role is "
			+ "content")

	check_eq(bool(record.get("same_unit", false)), true,
		"the record states that the committed reference and the package's own "
			+ "legacy id name the SAME unit")
	check_eq(str(measured["content_img_name"]), str(measured["package_legacy_id"]),
		"measured here: the committed sprite reference equals the package's own "
			+ "legacy id, which is what makes the three numbers comparable")

	# the one-data-point statements
	check_eq(int(record.get("data_points", 0)), 1,
		"the record states that the measurement is ONE data point")
	check_eq(int(record.get("converted_unit_packages", 0)), 1,
		"the record states that exactly one converted unit package is committed")
	check(str(record.get("what_max_frame_means", "")).contains("NOT CLAIMED"),
		"the record states that what max_frame means is NOT claimed")
	check(str(record.get("what_max_frame_means", "")).contains("ONE"),
		"the record ties its refusal to the single committed package")
	check_eq(bool(record.get("generalises", true)), false,
		"the record states that the one data point does NOT generalise")
	check(str(record.get("rule", "")).contains("ADOPTED NOWHERE"),
		"the recorded rule states that max_frame is adopted nowhere")

	# the structural proof: the committed field reaches a caller only as a
	# reported value. Every occurrence of the field's name in the module's CODE -
	# comments and string literals removed - must be part of a MAX_FRAME constant
	# name, so no identifier, local, or parameter is named after it and nothing
	# in the module can compute from it by name.
	var code := _code_only("scripts/units/unit_animations.gd")
	var lowered := code.to_lower()
	var offenders: Array = []
	var at := lowered.find("max_frame")
	while at >= 0:
		if code.substr(at, 9) != "MAX_FRAME":
			offenders.append(code.substr(maxi(at - 24, 0), 48))
		at = lowered.find("max_frame", at + 9)
	check_eq(offenders, [],
		"no identifier, local, or parameter in the delivered module is named "
			+ "after the committed field: every occurrence of the name in the "
			+ "module's code is part of a MAX_FRAME constant, so nothing can "
			+ "compute from it by name")
	return measured


# ---------------------------------------------------------------------------
# The animation-command inventory (requirement 4)
# ---------------------------------------------------------------------------

func _check_command_inventory() -> Dictionary:
	var record: Dictionary = UnitAnimations.animation_command_record()
	var measured: Dictionary = {}

	check_eq(int(record.get("named_branch_count", 0)),
		UnitAnimations.NAMED_BRANCH_COUNT,
		"the recorded named-dispatcher-branch count matches the recorded "
			+ "constant")
	check_eq(int(record.get("animation_command_count", -1)),
		UnitAnimations.ANIMATION_COMMAND_COUNT,
		"the recorded count of animation commands is ZERO")
	check_eq(bool(record.get("implemented", true)), false,
		"the inventory records that NO animation is implemented here")
	check_eq(bool(record.get("selected_by_server", true)), false,
		"the inventory records that no server selects an animation")
	check_eq(record.get("vocabulary", []), UnitAnimations.ANIMATION_VOCABULARY,
		"the recorded animation vocabulary is the four stems the suite scans "
			+ "for")
	check_eq(record.get("vocabulary_with_no_match", []),
		UnitAnimations.ANIMATION_VOCABULARY_NO_MATCH,
		"the recorded vocabulary stems that match no branch are the ones the "
			+ "suite measures")
	check_eq(int(record.get("match_count", 0)), 5,
		"exactly FIVE of the 63 named branches carry any animation vocabulary")
	check_eq(int(record.get("animation_command_count_measured", -1)), 0,
		"none of the five recorded matches is classified as an animation command")
	check(str(record.get("no_animation_command", "")).contains("ZERO"),
		"the recorded no-animation-command statement is present")

	var matches: Array = record.get("matches", []) as Array
	check_eq(matches.size(), 5,
		"every one of the five vocabulary matches is recorded")
	var names: Array = []
	for entry: Dictionary in matches:
		var command := str(entry.get("command", ""))
		names.append(command)
		check_eq(bool(entry.get("is_animation_command", true)), false,
			"the recorded match for `%s` states it is NOT an animation command"
				% command)
		check(str(entry.get("why_not", "")).length() > 0,
			"the recorded match for `%s` states why it is not" % command)
		check(str(entry.get("matched_vocabulary", "")).length() > 0,
			"the recorded match for `%s` names the vocabulary stem it matched"
				% command)
	names.sort()
	var expected_names := ["batch_remove", "end_attack", "move", "orient",
		"remove_inventory_item"]
	expected_names.sort()
	check_eq(names, expected_names,
		"the five recorded matches are exactly the five the committed "
			+ "dispatcher contains")

	var whole: Array = record.get("whole_token_matches", []) as Array
	whole.sort()
	var whole_expected: Array = UnitAnimations.WHOLE_TOKEN_MATCHES.duplicate()
	whole_expected.sort()
	check_eq(whole, whole_expected,
		"three of the five are whole-token matches - move, orient, end_attack - "
			+ "so the other two are pure substring artifacts")
	var inside: Array = record.get("substring_artifacts", []) as Array
	inside.sort()
	var inside_expected: Array = UnitAnimations.SUBSTRING_ARTIFACTS.duplicate()
	inside_expected.sort()
	check_eq(inside, inside_expected,
		"exactly two matches are substring artifacts: batch_remove and "
			+ "remove_inventory_item both contain the letters of `move` inside "
			+ "re-MOVE")
	check(not record.get("whole_token_matches", [] as Array)
			.has("batch_remove")
			and not record.get("whole_token_matches", [] as Array)
			.has("remove_inventory_item"),
		"a branch merely CONTAINING the letters of `move` is not a movement or "
			+ "animation command: neither of the two removal branches moves a "
			+ "row")

	# the refusal families this capability owns
	check(UnitAnimations.ANIMATION_SELECTED_BY_SERVER == false
			and str(UnitAnimations.ANIMATION_OWNERSHIP).contains("OWNED HERE"),
		"animation refusals are owned by this capability and nowhere else, so "
			+ "the delivered movement capability's recorded `animate_move` "
			+ "deferral is discharged here")
	check(str(UnitAnimations.M4_LIMIT_RECORDED).contains("NAMES-ONLY"),
		"M4's recorded limit is restated: labels are recorded names-only, with "
			+ "no playback semantics and no tessellation")
	return measured


# ---------------------------------------------------------------------------
# The refusal set and the anti-invention guard (requirements 4 and 5)
# ---------------------------------------------------------------------------

## Every refusal family is present with a non-empty reason, and the module
## declares EXACTLY the linkage accessors of design D1-D5.
func _check_refusals() -> Dictionary:
	var refusals: Array = UnitAnimations.refusal_record()
	check_eq(refusals.size(), EXPECTED_REFUSAL_FAMILIES.size(),
		"the recorded refusal set covers exactly the families the contract "
			+ "names")
	var present: Array = []
	for entry: Dictionary in refusals:
		var family := str(entry.get("family", ""))
		present.append(family)
		check_eq(bool(entry.get("refused", false)), true,
			"the refusal family `%s` is recorded as refused" % family)
		check(str(entry.get("reason", "")).length() > 0,
			"the refusal family `%s` records why it is refused" % family)
	for family: String in EXPECTED_REFUSAL_FAMILIES:
		check(present.has(family),
			"the recorded refusal set names the `%s` family" % family)
	check(str(UnitAnimations.REFUSAL_STATEMENT).contains("NOTHING PLAYABLE"),
		"the refusal statement is present beside the projection")
	for family: String in ["frame duration", "loop count", "state machine",
			"transition rule", "priority", "interrupt", "playback order",
			"per-state timing", "animation trigger", "event-to-state mapping"]:
		check(str(UnitAnimations.REFUSAL_STATEMENT).contains(family),
			"the refusal statement names the `%s` it refuses" % family)

	# the declared absent helpers, each with its reason and none of them present
	var declared: Array = []
	for entry: Dictionary in UnitAnimations.absent_helpers():
		declared.append(str(entry.get("helper", "")))
		check(str(entry.get("absent_because", "")).length() > 0,
			"the ABSENT_HELPERS entry for %s records why it is absent"
				% str(entry.get("helper", "?")))
	for family: String in ABSENT_FAMILIES:
		check(declared.has(family),
			"the recorded ABSENT_HELPERS inventory declares the `%s` helper"
				% family)

	var inventory := _static_functions()
	for name: String in declared:
		check(not inventory.has(name),
			"the module does NOT provide the recorded absent helper `%s`" % name)
	return {"refusals": refusals.size(), "absent": declared.size()}


## The module's actual static-function inventory: a duration, loop,
## state-machine, transition, priority, interrupt, timing, trigger, or playback
## helper fails this suite wherever it is added.
func _check_absence() -> void:
	var inventory := _static_functions()
	var unexpected: Array = []
	for name: String in inventory:
		if name.begins_with("_") or _is_a_linkage_accessor(name):
			continue
		unexpected.append(name)
	check_eq(unexpected, [],
		"the delivered module declares EXACTLY the linkage accessors of design "
			+ "D1-D5: no duration, loop, state-machine, transition, priority, "
			+ "interrupt, timing, trigger, or playback helper exists")


func _is_a_linkage_accessor(name: String) -> bool:
	return ["project_asset", "resolve_asset", "package_relative_path",
		"linkage_field_inventory", "linkage_field_names",
		"animation_field_values", "animation_field_note",
		"animation_fields_record", "non_equivalence_record",
		"animation_command_record", "command_names", "vocabulary_matches",
		"refusal_record", "absent_helpers", "non_claims", "coverage_record",
		"fixture_record", "no_endpoint_record", "readout_text"].has(name)


## Every static function the delivered module declares, sorted.
func _static_functions() -> Array:
	var present: Array = []
	for method: Dictionary in UnitAnimations.new().get_method_list():
		if not ((int(method["flags"]) & METHOD_FLAG_STATIC) != 0):
			continue
		present.append(str(method["name"]))
	present.sort()
	return present


# ---------------------------------------------------------------------------
# The no-endpoint boundary (requirement 5)
# ---------------------------------------------------------------------------

func _check_boundary() -> void:
	var record: Dictionary = UnitAnimations.no_endpoint_record()
	check_eq(bool(record.get("added", true)), false,
		"no compatibility route was added for unit animation")
	check_eq(bool(record.get("request_issued", true)), false,
		"no client intent is issued to animate a unit")
	check_eq(bool(record.get("selected_by_server", true)), false,
		"no server selects an animation, so there is no intent to authorise")
	check_eq(bool(record.get("persistence_changed", true)), false,
		"no persistence behaviour is changed")
	check_eq(bool(record.get("network_used", true)), false,
		"no network is used at all by this line")
	check(str(record.get("route", "")).contains("none"),
		"the boundary record states there is no route")
	check(str(record.get("route", "")).contains("converted asset"),
		"the boundary record states why: the linkage is committed content read "
			+ "through the content registry plus the committed converted asset on "
			+ "disk")
	check(str(record.get("compat_suite", "")).contains("unchanged"),
		"the boundary record states the compatibility suite is unchanged")
	check(str(record.get("note", "")).length() > 0,
		"the boundary record carries its note")

	var fixture := UnitAnimations.fixture_record()
	check_eq(bool(fixture.get("captured", true)), false,
		"no executed-legacy animation fixture was captured")
	check(str(fixture.get("reason_kind", "")).contains("stronger"),
		"the fixture record states the reason is the ABSENCE of behaviour, "
			+ "which is stronger than a corpus limitation")
	check(str(fixture.get("corpus_distinction", "")).contains("SECOND"),
		"the fixture record keeps the corpus limitation as a SECOND and "
			+ "independent reason")
	check_eq(int(fixture.get("animation_commands_available", -1)), 0,
		"the fixture record states that zero animation commands were available "
			+ "to capture")
	check_eq(bool(fixture.get("fabricated_state", true)), false,
		"the fixture record states no state was fabricated")

	# no source outside this module names an animate operation
	var offenders: Array = []
	for relative: String in _client_sources():
		if relative.ends_with("unit_animations.gd"):
			continue
		var code := _code_only(relative)
		for token: String in ANIMATE_TOKENS:
			if code.find(token) != -1:
				offenders.append("%s: %s" % [relative, token])
	check_eq(offenders, [],
		"no client source outside this module declares an animate operation, an "
			+ "animation endpoint, a state selection, or a duration helper")


# ---------------------------------------------------------------------------
# The coverage record (design D5)
# ---------------------------------------------------------------------------

## The one-package coverage, measured rather than assumed, and the ambiguous
## -reference refusal over the committed set.
func _check_coverage(registry: Variant) -> Dictionary:
	var record: Dictionary = UnitAnimations.coverage_record()
	var measured: Dictionary = {"unit_packages": 0, "building_packages": 0,
		"covered_units": [], "ambiguous_units": []}

	var names: Array = record.get("unit_packages", []) as Array
	measured["unit_packages"] = names.size()
	check_eq(names, UnitAnimations.CONVERTED_UNIT_PACKAGES,
		"exactly ONE converted unit package is committed, and it is the one "
			+ "this projection reads")
	check_eq(int(record.get("unit_package_count", 0)), 1,
		"the recorded converted-unit-package count is one")
	check_eq(int(record.get("unit_package_count_recorded", 0)),
		int(record.get("unit_package_count", -1)),
		"the recorded count and the measured count agree, so a later "
			+ "conversion would have to change both")
	measured["building_packages"] = int(record.get("building_package_count", 0))
	check_eq(int(record.get("building_package_count", 0)), 1,
		"exactly ONE converted building package is committed, so no "
			+ "distribution over the corpus is measurable from the assets")
	check_eq(str(record.get("covered_unit_legacy_id", "")),
		UnitAnimations.COVERED_UNIT_LEGACY_ID,
		"the recorded covered unit is legacy id 933, the Wild Elephant")
	check_eq(bool(record.get("reconverted", true)), false,
		"no conversion or extraction output is regenerated to cover another "
			+ "unit")
	check(str(record.get("statement", "")).contains("EXACTLY ONE UNIT"),
		"the coverage statement says the coverage is exactly one unit")

	# measured over the committed set: exactly one unit's committed sprite
	# reference names a committed converted package
	var covered: Array = []
	var ambiguous: Array = []
	var listed: Array = registry.legacy_ids("units").get("ids", []) as Array
	for id_text: Variant in listed:
		var entry: Dictionary = registry.get_entry("units",
			str(id_text)).get("entry", {}) as Dictionary
		var reference := str(entry.get("img_name", ""))
		if names.has(reference):
			covered.append(str(id_text))
		if reference.contains(","):
			ambiguous.append(str(id_text))
	measured["covered_units"] = covered
	measured["ambiguous_units"] = ambiguous
	check_eq(covered, [UnitAnimations.COVERED_UNIT_LEGACY_ID],
		"exactly ONE committed unit names a committed converted package, so the "
			+ "projection's measured coverage is one unit")
	check_eq(ambiguous, UnitAnimations.AMBIGUOUS_REFERENCE_UNITS,
		"exactly 5 committed units carry a COMMA-JOINED sprite reference, and "
			+ "each of them is refused rather than split")
	check_eq(ambiguous.size(), int(record.get("ambiguous_reference_count", 0)),
		"the recorded ambiguous-reference count is the measured one")
	return measured


# ---------------------------------------------------------------------------
# The legacy measurements (requirement: no count taken on trust)
# ---------------------------------------------------------------------------

## Every legacy figure this line records is re-derived from the committed source
## in this same run.
func _check_legacy() -> Dictionary:
	var measured: Dictionary = {"modules": 0, "zero_consumer_names": [],
		"named_branches": [], "vocabulary_matches": [], "whole_token": [],
		"substring": [], "no_match": []}

	for module: String in UnitAnimations.SEARCHED_MODULES:
		var lines := _legacy_lines(module)
		if lines.is_empty():
			fail("the legacy module %s is readable: every fact this line "
				% module
				+ "records is measured out of it, and a missing file would "
				+ "make the measurement vacuous")
			continue
		measured["modules"] += 1
	check_eq(int(measured["modules"]), 7,
		"all seven legacy root modules are readable")

	# the seven zero-consumer names, measured across the searched modules
	var zero: Array = []
	for field: String in UnitAnimations.ANIMATION_FIELDS + [
			UnitAnimations.ANIMATION_FLAG]:
		var reads := 0
		for module: String in UnitAnimations.SEARCHED_MODULES:
			var text := "\n".join(_legacy_lines(module))
			reads += _count_occurrences(text, "\"%s\"" % field)
			reads += _count_occurrences(text, "'%s'" % field)
		if reads == 0:
			zero.append(field)
	measured["zero_consumer_names"] = zero
	check_eq(zero.size(), UnitAnimations.ANIMATION_FIELDS.size() + 1,
		"the six animation fields AND the animal flag measure as zero across "
			+ "the seven legacy modules: the recorded zero-consumer fact is a "
			+ "measurement, not a claim")
	for field: String in UnitAnimations.ANIMATION_FIELDS:
		check(zero.has(field),
			"the committed field `%s` measures as zero-consumer" % field)
	check(zero.has(UnitAnimations.ANIMATION_FLAG),
		"the committed `animal` flag measures as zero-consumer")

	# the dispatcher's named branches, re-derived and compared by SET
	var dispatcher := _legacy_lines("command.py")
	var named: Array = []
	for line: Variant in dispatcher:
		var branch := _branch_of(str(line))
		if branch != "" and not named.has(branch):
			named.append(branch)
	measured["named_branches"] = named
	var recorded: Array = UnitAnimations.command_names()
	check_eq(named.size(), recorded.size(),
		"the measured named-dispatcher-branch count is the recorded one")
	check_eq(named, recorded,
		"the measured named branches are EXACTLY the recorded list, in committed "
			+ "source order: a new branch would be an unrecorded gap, not a "
			+ "silent addition")

	# the vocabulary matches, and their two disjoint classes
	var matches: Array = []
	for stem: String in UnitAnimations.ANIMATION_VOCABULARY:
		for branch: String in named:
			if branch.contains(stem) and not matches.has(branch):
				matches.append(branch)
	measured["vocabulary_matches"] = matches
	check_eq(matches.size(), 5,
		"exactly FIVE of the measured named branches carry any animation "
			+ "vocabulary")
	var whole: Array = []
	var inside: Array = []
	for branch: String in matches:
		if _has_whole_token(branch, UnitAnimations.ANIMATION_VOCABULARY):
			whole.append(branch)
		else:
			inside.append(branch)
	measured["whole_token"] = whole
	measured["substring"] = inside
	whole.sort()
	inside.sort()
	var whole_expected: Array = UnitAnimations.WHOLE_TOKEN_MATCHES.duplicate()
	whole_expected.sort()
	var inside_expected: Array = UnitAnimations.SUBSTRING_ARTIFACTS.duplicate()
	inside_expected.sort()
	check_eq(whole, whole_expected,
		"the measured whole-token matches are move, orient, and end_attack")
	check_eq(inside, inside_expected,
		"the measured substring artifacts are batch_remove and "
			+ "remove_inventory_item, and NEITHER moves or animates anything")

	# the negative measurement: the stems that match nothing at all
	var silent: Array = []
	for stem: String in UnitAnimations.ANIMATION_VOCABULARY_NO_MATCH:
		var found := false
		for branch: String in named:
			if branch.contains(stem):
				found = true
		if not found:
			silent.append(stem)
	measured["no_match"] = silent
	check_eq(silent, UnitAnimations.ANIMATION_VOCABULARY_NO_MATCH,
		"the stems frame, play, loop, state, clip, sprite, idle, walk, and "
			+ "death match NO branch at all, which is what makes the five "
			+ "positive matches the whole vocabulary surface")
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


## Computes and writes the deterministic `unit-animations-report-v1` report.
##
## Every contract fact comes from `unit_animations.gd`; every legacy fact comes
## from the measurement this run performed; every committed number comes from
## the registry that was just verified, from the committed package bytes, or from
## the committed corpus. Nothing here reads the wall clock, and no timestamp or
## absolute path is written, so reruns reproduce the bytes.
func _write_report(path: String, loaded: Dictionary, package: Dictionary,
		legacy: Dictionary, projection: Dictionary, refusal: Dictionary,
		content: Dictionary, max_frame: Dictionary, inventory: Dictionary,
		refusals: Dictionary, coverage: Dictionary, digests: Dictionary) -> void:
	var linkage: Dictionary = UnitAnimations.resolve_asset(
		_definition(root.get_node_or_null("ContentRegistry"), COVERED_UNIT_ID))
	var fields: Dictionary = UnitAnimations.animation_fields_record()
	var measured_fields: Dictionary = content.get("distribution", {}) as Dictionary
	fields["distribution_measured"] = measured_fields.duplicate(true)
	var report := {
		"schema": "unit-animations-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_animations.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no network: every table is derived from the "
				+ "delivered module, the verified content registry, the "
				+ "committed converted package bytes, and the measurements "
				+ "this run performed",
		},
		"linkage": {
			"fields": UnitAnimations.linkage_field_inventory(),
			"field_names": UnitAnimations.linkage_field_names(),
			"field_count": UnitAnimations.LINKAGE_FIELD_COUNT,
			"label_keys": (UnitAnimations.LABEL_KEYS as Array).duplicate(),
			"no_derivation": UnitAnimations.NO_DERIVATION,
			"asset_refusal": UnitAnimations.ASSET_REFUSAL,
			"rate_reported_not_applied": {
				"recorded_rate": linkage.get("frame_rate", null),
				"applied": bool(linkage.get("rate_applied", true)),
				"applied_to": str(linkage.get("rate_applied_to", "")),
				"rule": "the recorded rate is reported exactly as recorded and "
					+ "is never multiplied by a frame count to produce a "
					+ "duration or a frame time",
			},
			"labels": linkage.get("labels", []),
			"label_count": int(linkage.get("label_count", 0)),
			"label_order": linkage.get("label_order", []),
			"labelled_sprite_id": linkage.get("labelled_sprite_id", null),
			"labelled_sprite_ids": linkage.get("labelled_sprite_ids", []),
			"labelled_sprite_frame_count":
				linkage.get("labelled_sprite_frame_count", null),
			"root_frame_count": linkage.get("root_frame_count", null),
			"main_timeline_frame_count":
				linkage.get("main_timeline_frame_count", null),
			"frame_rate": linkage.get("frame_rate", null),
			"sprite_frame_counts": linkage.get("sprite_frame_counts", []),
			"sprite_count": int(linkage.get("sprite_count", 0)),
			"sprite_placement_counts":
				linkage.get("sprite_placement_counts", []),
			"sprite_remove_counts": linkage.get("sprite_remove_counts", []),
			"root_placement_count": linkage.get("root_placement_count", null),
			"root_remove_count": linkage.get("root_remove_count", null),
			"package_legacy_id": linkage.get("package_legacy_id", ""),
			"package_kind": linkage.get("package_kind", ""),
			"package_source_file": linkage.get("package_source_file", ""),
			"package_relative_path": linkage.get("package_relative_path", ""),
			"asset_named_by_content": bool(
				linkage.get("asset_named_by_content", false)),
			"content_sprite_reference":
				linkage.get("content_sprite_reference", null),
			"readout": linkage.get("readout", ""),
		},
		"refusal": {
			"measured": refusal,
			"reasons": [
				UnitAnimations.REASON_ASSET_ABSENT,
				UnitAnimations.REASON_ASSET_UNREADABLE,
				UnitAnimations.REASON_NO_LABELS,
				UnitAnimations.REASON_MALFORMED_LABEL,
				UnitAnimations.REASON_NO_SPRITE_REFERENCE,
				UnitAnimations.REASON_AMBIGUOUS_SPRITE_REFERENCE,
				UnitAnimations.REASON_INVALID_DEFINITION,
			],
			"recorded_state_intact": true,
			"nominal_animation_never_defaulted": true,
			"single_frame_never_defaulted": true,
		},
		"animation_fields": fields,
		"animation_fields_measured": content,
		"max_frame": UnitAnimations.non_equivalence_record(),
		"max_frame_measured": max_frame,
		"commands": UnitAnimations.animation_command_record(),
		"commands_measured": inventory,
		"refusals": UnitAnimations.refusal_record(),
		"refusal_statement": UnitAnimations.REFUSAL_STATEMENT,
		"absent_helpers": UnitAnimations.absent_helpers(),
		"m4_limit": UnitAnimations.M4_LIMIT_RECORDED,
		"ownership": UnitAnimations.ANIMATION_OWNERSHIP,
		"animation_implemented": UnitAnimations.ANIMATION_IMPLEMENTED,
		"no_endpoint": UnitAnimations.no_endpoint_record(),
		"fixture": UnitAnimations.fixture_record(),
		"coverage": UnitAnimations.coverage_record(),
		"coverage_measured": coverage,
		"refusal_measured": refusals,
		"non_claims": UnitAnimations.non_claims(),
		"provenance": UnitAnimations.PROVENANCE,
		"projection_measured": projection,
		"legacy_measured": legacy,
		"committed_package": {
			"relative_path": PACKAGE_RELATIVE,
			"sha256": digests.get("package", ""),
			"source_file": str(package.get("source_file", "")),
			"content_ref_legacy_id": str(
				(package.get("content_ref", {}) as Dictionary).get(
					"legacy_id", "")),
			"content_ref_max_frame":
				(package.get("content_ref", {}) as Dictionary).get(
					"max_frame", null),
			"top_level_keys": _sorted_keys(package),
		},
		"inputs": {
			"content_package": {
				"manifest": "packages/game-content/manifest.json",
				"outputs_verified": int(loaded.get("files_verified", 0)),
				"bytes_verified": int(loaded.get("bytes_verified", 0)),
				"fingerprint": str(loaded.get("fingerprint", "")),
				"units_json_sha256": digests.get("units", ""),
				"buildings_json_sha256": digests.get("buildings", ""),
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


## A parsed object's keys, sorted, so the report records the committed asset's
## own shape without depending on its key order.
func _sorted_keys(value: Dictionary) -> Array:
	var out: Array = []
	for key: Variant in value:
		var text := str(key)
		if text == "sha256":
			# injected by this suite, not part of the committed package
			continue
		out.append(text)
	out.sort()
	return out


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------

## The committed converted package's bytes, read once and parsed by this suite
## itself, so every "verbatim" claim is compared against an independent read.
func _read_package() -> Dictionary:
	var absolute := Paths.repo_root().path_join(PACKAGE_RELATIVE)
	if not FileAccess.file_exists(absolute):
		fail("the one committed converted unit package is present at %s: this "
			% PACKAGE_RELATIVE
			+ "line's whole linkage evidence is read out of it, and a missing "
			+ "file would make the report vacuous")
		return {}
	var text := FileAccess.get_file_as_string(absolute)
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		fail("the committed converted package parses as an object")
		return {}
	var out: Dictionary = parsed
	out["sha256"] = text.sha256_text()
	return out


## The digests of the committed inputs this report reads, so the report pins its
## own inputs.
func _input_digests() -> Dictionary:
	var out: Dictionary = {}
	for name: String in ["units", "buildings"]:
		var relative := "packages/game-content/normalized/%s.json" % name
		var absolute := Paths.repo_root().path_join(relative)
		if FileAccess.file_exists(absolute):
			out[name] = FileAccess.get_file_as_string(absolute).sha256_text()
	var package_absolute := Paths.repo_root().path_join(PACKAGE_RELATIVE)
	if FileAccess.file_exists(package_absolute):
		out["package"] = FileAccess.get_file_as_string(
			package_absolute).sha256_text()
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


## Whether a branch name contains any vocabulary stem as a WHOLE `_`-separated
## token. Never a substring: `batch_remove` and `remove_inventory_item` both
## contain the letters of `move` inside "re**move**", and calling either a
## movement or animation command would be exactly the invention this line
## refuses.
func _has_whole_token(branch: String, stems: Array) -> bool:
	for token: String in branch.split("_"):
		if stems.has(token):
			return true
	return false


## A committed NUMBER's own text, with the JSON transport's `2.0` normalised to
## `2`.
##
## The pinned engine's JSON parser represents every committed JSON number as a
## float, so `str(2.0)` is "2.0" and a distribution keyed on `str()` would read
## as a field of entirely different keys. This normalises an INTEGRAL float to
## its integer text and leaves everything else — a fractional number, a string,
## a boolean — exactly as it is, so a committed encoding change stays visible.
func _numeric_key(value: Variant) -> String:
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number):
			return str(int(number))
		return str(value)
	return str(value)


## One committed `properties` FLAG, read the way the package encodes it.
##
## The normalized package stores these flags as STRINGS -- "1" and "0", not
## numbers -- and leaves most of them ABSENT, so a flag may be an int, a float, a
## String, or missing. Reading one through `int(value or 0)` is WRONG: a
## non-empty String is truthy in GDScript, so `or 0` collapses the committed
## "0" to `true` and `int(true)` is 1. This converts each representation
## explicitly instead.
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


## A source's CODE: comments and string-literal contents removed, so a scan sees
## the identifiers a reader would compile rather than the prose and the recorded
## strings about them. The `max_frame` proof depends on this: the committed
## field's name survives only where it is an identifier, never where it is a
## reported key.
func _code_only(relative: String) -> String:
	var absolute := Paths.project_dir().path_join(relative)
	if not FileAccess.file_exists(absolute):
		return ""
	var out: Array = []
	for line: String in FileAccess.get_file_as_string(absolute).split("\n"):
		out.append(_strip_code(line))
	return "\n".join(out)


## One line with its string-literal contents and any trailing comment removed.
func _strip_code(line: String) -> String:
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
		if character == "#":
			break
		out += character
		index += 1
	return out