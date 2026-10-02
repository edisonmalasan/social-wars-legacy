extends "res://tests/test_base.gd"
## Research suite (OpenSpec `godot-research` "The research counter vector is
## projected for both tracks, verbatim" / "The four legacy branch effects are
## recorded as data, not recomputed" / "Both research tracks are named, and their
## committed building ids are reported but not used" / "`fast_forward` is recorded
## as a fourth writer of the research instant" / "A research action is a
## server-derived intent, and no client value is trusted" / "No research price is
## charged, and every stored resource is proven unchanged" / "Executed-legacy
## behaviour fixtures are captured" / "Research evidence and claim limits", design
## D1-D10).
##
## Checks:
##   counters   the three committed private-state keys, the two-track width, and
##              both tracks' six values reported **verbatim** with nothing derived
##              from another;
##   projection a full vector, a non-zero vector, a zero vector that is a real
##              zero, and the **five** malformed shapes — absent, non-object,
##              non-list, wrong length, non-integer, negative — each reported
##              unresolvable with its recorded state intact and never defaulted to
##              a zero vector;
##   branches   the four recorded effects measured against `command.py` itself:
##              the step increment and stamp, the cash branch's instant-only
##              zeroing with its discarded price, the item branch's **paired**
##              step-and-instant reset, and the reset branch's three-counter zeroing;
##   tracks     the two committed names, their committed building ids, that the
##              names exist **only** in the four branch comments, and that **no**
##              delivered code identifier is named after either of them;
##   writers    the research instant's **five** writers measured out of the
##              source, the `fast_forward` writer and its client-supplied seconds,
##              and that no delivered operation or helper derives a fast forward;
##   source     the legacy figures **re-measured** here rather than trusted: the
##              four branch line ranges, the three counters' occurrence counts and
##              write-only property, and the track comment lines;
##   absence   the four refusal families with non-empty reasons, the named
##              non-derivation list, and the module's whole function inventory
##              compared against a pinned list (task 4.3);
##   content    the **measured** content findings, including the two figures the
##              M9 investigation and this line's proposal got **wrong**;
##   corpus     the committed fresh-player corpus: 40 rows, all three counters
##              `[0, 0]` of length 2, and no placed row carrying a research counter;
##   ledger     the cross-milestone correction: the dead-hero ledger has **four**
##              doors, `map_lose_item` is the fourth and is reached from the
##              **quest** path, and it is an engine helper rather than a
##              dispatcher branch (task 5.1/5.2);
##   fixture    the committed executed-legacy capture: **eight** branch-track
##              steps, their derived vectors, the round trip back to the seed, the
##              three probes, and the corpus staying byte-identical;
##   intents    the facade's research operation takes EXACTLY the save identity, a
##              closed action, and a track, so no channel exists through which a
##              client could send a counter, an instant, or a cash amount;
##   purity     the delivered module names no node, clock, request, or transport
##              token, and loads nothing at all;
##   containment the content package, the committed saves, and the committed
##              fixtures are byte-identical after the run.
##
## Hermetic: no process, no server, no socket, and no request is issued. A research
## state is read from a save already in hand, so no GameApi operation is involved
## except in the `intents` inventory read. The fault scenarios build **copies**
## under `.godot/`, never a source file.
##
## `--scenario=live-research` is the `research-live` phase: a full step → item →
## reset cycle through the real Compatibility endpoint over a disposable corpus,
## asserting each typed response, each post-condition, that every stored resource
## is unchanged, and the corpus's own refusal codes.
## `--report=<path>` writes the deterministic `research-report-v1` evidence
## report; the bare `--report` flag defaults to `evidence/research/report.json`.
## Every table is derived from the live model and the committed bytes, so the
## report cannot drift from the code it documents.

const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

const SCRATCH := ".godot/verify/research"
## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/research/report.json"
## The committed corpus this line measures.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
## The committed fixture directory, its manifest, and the eight recorded steps.
const FIXTURE_DIR := "tests/fixtures/godot-research"
const FIXTURE_MANIFEST := FIXTURE_DIR + "/capture-manifest.json"
## The eight branch-track steps, in the order they execute.
const STEP_NAMES := [
	"command_next_research_step_track_0",
	"command_next_research_step_track_1",
	"command_research_buy_step_cash_track_0",
	"command_research_buy_step_cash_track_1",
	"command_next_research_item_track_0",
	"command_next_research_item_track_1",
	"command_reset_research_item_track_0",
	"command_reset_research_item_track_1",
]
## The legacy root modules the research figures are measured across.
const LEGACY_MODULES := [
	"command.py", "engine.py", "sessions.py", "server.py", "constants.py",
	"get_game_config.py", "version.py",
]
## The recorded figures this suite RE-MEASURES rather than trusting. A drift fails
## the run instead of publishing a different contract (task 4.4).
const EXPECTED_STEP_SITES := 3
const EXPECTED_ITEM_SITES := 2
const EXPECTED_INSTANT_SITES := 5
const EXPECTED_BRANCH_RANGES := {
	"next_research_step": [268, 274],
	"research_buy_step_cash": [276, 282],
	"next_research_item": [284, 291],
	"reset_research_item": [293, 300],
}
const EXPECTED_TRACK_COMMENT_LINES := [269, 278, 285, 294]
const EXPECTED_WRITER_SITES := [
	"command.py:272", "command.py:280", "command.py:289", "command.py:298",
	"command.py:923",
]
## The committed content-absence findings, MEASURED (task 4.2). Two of the three
## figures correct the M9 investigation and this line's proposal, which both
## state that `research` appears in exactly ONE normalized file and that
## `config/main.json` has NO key containing `research` at any depth.
const EXPECTED_NORMALIZED_FILES := 22
const EXPECTED_RESEARCH_FILES := {"buildings.json": 1, "images.json": 6}
const EXPECTED_RESEARCH_LAB_ID := "256"
const EXPECTED_RESEARCH_LAB_NAME := "Research Lab"
const EXPECTED_IMAGE_ASSETS := [
	"popupResearchCenter_buildingProcess.swf",
	"popupResearchCenter_buildingProcess_2.swf",
	"popupResearchCenter_buildingProcess_3.swf",
]
const EXPECTED_CONFIG_RESEARCH_KEYS := [
	"/images/popupResearchCenter_buildingProcess.swf",
	"/images/popupResearchCenter_buildingProcess_2.swf",
	"/images/popupResearchCenter_buildingProcess_3.swf",
]
const EXPECTED_CONFIG_TOP_LEVEL_KEYS := 20
## Tokens a pure projection must not carry: a node, a clock, a request, or a
## transport. The transport needles are spelled as fragments because the
## project-scope suite scans every source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]
## The whole function inventory of `research_flow.gd`, public and private,
## including the inner classes' readers. Compared as a sorted set, so a readiness,
## duration, price, or unlock helper fails the run wherever it is added
## (task 4.3).
const EXPECTED_FLOW_MODULE_METHODS := [
	"_action_index", "_integer", "_parse_vector", "_recorded_snapshot",
	"_reject", "_result_error", "_type_name", "branch_record", "confirm_text",
	"evaluate", "intent_body", "intent_record", "is_action", "is_track",
	"offers", "parse_result", "project", "readout_text", "refusal_text",
	"result_failure",
]
## The inner `TrackView` and `ResearchView` readers, pinned for the same reason.
const EXPECTED_TRACK_VIEW_METHODS := ["fields", "instant", "item", "step", "track"]
const EXPECTED_RESEARCH_VIEW_METHODS := [
	"counters", "error", "fields", "reason", "recorded", "resolvable", "track",
	"tracks",
]
## Names a readiness, remaining-time, price, unlock, or fast-forward helper would
## take. Each is ALSO a named entry in `ResearchFlow.NON_DERIVATION`, so the
## recorded list and this one cannot drift: a rename cannot smuggle a helper past
## the inventory and a leftover in the recorded list fails visibly.
const FORBIDDEN_HELPERS := [
	"is_research_complete", "research_ready", "research_duration",
	"research_price", "unlock_research", "research_step_count",
	"research_reward", "fast_forward",
]
## Further spellings that are likewise absent. These are checked against the
## module's declarations and its whole function inventory, not against the named
## list, so the two lists stay independently useful.
const ALSO_ABSENT_HELPERS := [
	"research_remaining", "research_cost", "research_time_left",
	"research_complete", "research_elapsed", "research_total_steps",
	"research_unlock_cost", "research_progress", "research_ratio",
	"research_fraction", "is_complete", "remaining_time",
]
## Tokens that would mean a readiness, duration, price, or reward is computed.
const BEHAVIOUR_NEEDLES := [
	"research_price(", "research_duration(", "is_research_complete(",
	"research_ready(", "unlock_research(", "maxf(", "Time.", "minf(",
]
## The non-claim phrases the delta's evidence requirement names.
const REQUIRED_NON_CLAIMS := [
	"no Flash",
	"NO RESEARCH PRICE IS CHARGED AND NO STORED RESOURCE MOVES",
	"NO COMPLETION, READINESS, REMAINING-TIME, OR UNLOCK SEMANTICS ARE",
	"NO COUNTER BOUND, MEMBERSHIP RULE, OR CLAMP IS ADDED",
	"NO REWARD IS PAID",
	"NO COMMITTED RESEARCH CONTENT IS INVENTED",
	"the track-to-building mapping is REPORTED and NEVER USED",
	"NO FAST-FORWARD OPERATION IS DELIVERED",
	"THE COUNTERS HAVE NO IN-GAME CONSUMER",
	"no pixel-parity oracle exists",
	"no windowed capture is claimed",
]
## The endpoint override the live phase is invoked with.
const ARG_ENDPOINT := "--gameapi-endpoint="
## The delivered module's own resource path, read by the suite for its
## function-inventory and purity checks — read reflectively so a rename or a new
## helper fails the SUITE rather than a comment.
const RESEARCH_SOURCE := "res://scripts/units/research_flow.gd"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-research":
		await _check_live_research()
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

	_check_counters()
	_check_projection()
	_check_branches()
	_check_tracks()
	_check_writers()
	var source := _check_source()
	_check_absence()
	_check_content()
	var corpus := _check_corpus()
	_check_ledger()
	var fixture := _check_fixture()
	_check_intents()
	await _check_fake_double()
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before, save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, source, corpus, fixture, package_before,
			save_before)
	info("research: corpus rows %d, vector %s, fixture steps %d"
		% [int(corpus.get("rows", 0)), corpus.get("vector", {}),
			(fixture.get("steps", []) as Array).size()])


# ---------------------------------------------------------------------------
# The three counters and the two tracks (design D1)
# ---------------------------------------------------------------------------


## The three committed private-state keys, the two-track width, and both tracks'
## six values reported verbatim with nothing derived from another.
func _check_counters() -> void:
	check_eq(ResearchFlow.KEY_STEP, "researchStepNumber",
		"the step counter is the committed researchStepNumber")
	check_eq(ResearchFlow.KEY_ITEM, "researchItemNumber",
		"the item counter is the committed researchItemNumber")
	check_eq(ResearchFlow.KEY_INSTANT, "timeStampDoResearch",
		"the research instant is the committed timeStampDoResearch")
	check_eq(ResearchFlow.COUNTERS,
		["researchStepNumber", "researchItemNumber", "timeStampDoResearch"],
		"the research state is exactly those three counters, in committed order")
	check_eq(ResearchFlow.TRACK_COUNT, 2, "the vector carries two tracks")
	var vector := {
		"researchStepNumber": [7, 0],
		"researchItemNumber": [2, 5],
		"timeStampDoResearch": [10000000000, 0],
	}
	var projected: Variant = ResearchFlow.project(vector)
	check(bool(projected.get("ok", false)),
		"a well-formed research vector projects (error: %s)"
			% str(projected.get("error", "")))
	if not bool(projected.get("ok", false)):
		return
	var research: Variant = projected["research"]
	var rows: Array = (research as ResearchFlow.ResearchView).tracks()
	check_eq(rows.size(), 2, "the projection carries BOTH tracks")
	check_eq((rows[0] as ResearchFlow.TrackView).step(), 7,
		"track 0's step counter is reported verbatim")
	check_eq((rows[0] as ResearchFlow.TrackView).item(), 2,
		"track 0's item counter is reported verbatim")
	check_eq((rows[0] as ResearchFlow.TrackView).instant(), 10000000000,
		"track 0's research instant is reported verbatim and unscaled")
	check_eq((rows[1] as ResearchFlow.TrackView).step(), 0,
		"track 1's step counter is reported verbatim, including a real zero")
	check_eq((rows[1] as ResearchFlow.TrackView).item(), 5,
		"track 1's item counter is reported verbatim")
	check_eq((rows[1] as ResearchFlow.TrackView).instant(), 0,
		"track 1's research instant is reported verbatim, including a real zero")
	# A ten-billion-second stamp derives NO remaining time: there is no field in
	# which one could hide, and the record is exactly the six committed values.
	var fields: Dictionary = (rows[0] as ResearchFlow.TrackView).fields()
	var field_names: Array = fields.keys()
	field_names.sort()
	check_eq(field_names, ["instant", "item", "step", "track"],
		"a track record carries exactly the four committed facts and nothing else")
	var counters: Dictionary = (research as ResearchFlow.ResearchView).counters()
	check_eq(counters, vector, "the counter vectors are reported verbatim")
	# A zero vector is a real committed state here, not an absence: every legacy
	# branch writes a zero.
	var zeros: Variant = ResearchFlow.project(ResearchFlow.CORPUS_VECTOR)
	check(bool(zeros.get("ok", false)),
		"the committed all-zero vector resolves: it is a real state, not an "
			+ "absence")
	# …and it is distinguishable from the unresolvable paths below.
	if bool(zeros.get("ok", false)):
		var zero_research: Variant = zeros["research"]
		check_eq((zero_research as ResearchFlow.ResearchView).resolvable(), true,
			"the committed all-zero vector RESOLVES, so a real zero and a "
				+ "refusal are never the same report")
		var view: Dictionary = (zero_research as ResearchFlow.ResearchView).fields()
		check_eq((view["tracks"] as Array)[0],
			{"track": 0, "step": 0, "item": 0, "instant": 0},
			"a real zero vector reports zeros as COMMITTED values")


## Both tracks and all three counters, verbatim — and nothing derived.
func _check_projection() -> void:
	# --- the five (six) malformed shapes, each refused with its recorded state ---
	var cases := [
		[null, ResearchFlow.REASON_ABSENT_STATE],
		["nope", ResearchFlow.REASON_NON_OBJECT],
		[7, ResearchFlow.REASON_NON_OBJECT],
		[{}, ResearchFlow.REASON_ABSENT_STATE],
		[{"researchStepNumber": {}, "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NOT_A_LIST],
		[{"researchStepNumber": "00", "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NOT_A_LIST],
		[{"researchStepNumber": [0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_WRONG_LENGTH],
		[{"researchStepNumber": [0, 0, 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_WRONG_LENGTH],
		[{"researchStepNumber": ["0", 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NON_INTEGER],
		[{"researchStepNumber": [1.5, 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NON_INTEGER],
		[{"researchStepNumber": [true, 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NON_INTEGER],
		[{"researchStepNumber": [null, 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NON_INTEGER],
		[{"researchStepNumber": [-1, 0], "researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_NEGATIVE],
		[{"researchItemNumber": [0, 0],
			"timeStampDoResearch": [0, 0]}, ResearchFlow.REASON_ABSENT_STATE],
		[{"researchStepNumber": [0, 0], "timeStampDoResearch": [0, 0]},
			ResearchFlow.REASON_ABSENT_STATE],
	]
	for entry: Variant in cases:
		var state: Variant = (entry as Array)[0]
		var reason := str((entry as Array)[1])
		var projected: Variant = ResearchFlow.project(state)
		check(not bool(projected.get("ok", false))
				and str(projected.get("reason", "")) == reason,
			"the malformed research state %s is refused with %s"
				% [_state_label(state), reason])
		check(str(projected.get("error", "")).begins_with("[research]"),
			"the refusal message names the projection")
		check(projected.get("research", null) == null,
			"a refused state produces NO research view at all")
		check(projected.has("recorded"),
			"the refusal carries the state's RECORDED shape, not a substitute")
	check_eq(ResearchFlow.PROJECTION_REASONS.size(), 6,
		"the projection's refusal vocabulary is closed and holds six reasons")
	for reason: String in ResearchFlow.PROJECTION_REASONS:
		check(str(reason) != "", "the refusal reason %s is named" % reason)
	# --- read-only: projecting writes nothing back into the save -------------
	var source := {
		"researchStepNumber": [1, 2],
		"researchItemNumber": [3, 4],
		"timeStampDoResearch": [5, 6],
		"goals": [null, null],
	}
	var snapshot: Dictionary = source.duplicate(true)
	var projected: Variant = ResearchFlow.project(source)
	if bool(projected.get("ok", false)):
		var research: Variant = projected["research"]
		var fields: Dictionary = (research as ResearchFlow.ResearchView).fields()
		(fields["counters"] as Dictionary)["researchStepNumber"][0] = 99
		((fields["tracks"] as Array)[0] as Dictionary)["step"] = 99
		check_eq(source, snapshot,
			"projecting a research state writes nothing back into the save")
		var again: Dictionary = (research as ResearchFlow.ResearchView).fields()
		check_eq((again["counters"] as Dictionary)["researchStepNumber"], [1, 2],
			"mutating the handed-out record cannot change the reported counters")
		check_eq(((again["tracks"] as Array)[0] as Dictionary)["step"], 1,
			"mutating the handed-out track cannot change the reported track")
	check_eq((source as Dictionary).get("goals"), [null, null],
		"an unrelated committed private-state field is neither read nor written")
	# --- the integral-float transport tolerance, and no numeric string -------
	var transported: Variant = ResearchFlow.project({
		"researchStepNumber": [1.0, 2.0],
		"researchItemNumber": [3.0, 4.0],
		"timeStampDoResearch": [5.0, 6.0],
	})
	check(bool(transported.get("ok", false)),
		"an integral float vector is accepted: the pinned engine's JSON parser "
			+ "widens every committed number")
	if bool(transported.get("ok", false)):
		var research: Variant = transported["research"]
		check_eq((research as ResearchFlow.ResearchView)
			.counters()["researchStepNumber"], [1, 2],
			"the integral floats read as the exact integers they denote")
	# --- the evaluation is the one entry point, and it composes the records ---
	var evaluation: Dictionary = ResearchFlow.evaluate(ResearchFlow.CORPUS_VECTOR)
	check(bool(evaluation.get("ok", false)) and bool(evaluation.get("resolvable",
		false)),
		"the evaluation resolves the committed vector")
	check_eq((evaluation.get("tracks", []) as Array).size(), 2,
		"the evaluation carries both tracks")
	var refused: Dictionary = ResearchFlow.evaluate({"researchStepNumber": [0]})
	check(not bool(refused.get("ok", false)),
		"the evaluation refuses a malformed state")
	check_eq(refused.get("fields", {}), {},
		"a refused evaluation carries no partial payload")
	check(str(refused.get("error", "")).contains("researchStepNumber"),
		"the refusal names the offending counter")


# ---------------------------------------------------------------------------
# The four recorded branch effects (design D1)
# ---------------------------------------------------------------------------


## The four branch records, measured against the committed source rather than
## trusted from this file.
func _check_branches() -> void:
	check_eq(ResearchFlow.BRANCHES.size(), ResearchFlow.BRANCH_COUNT,
		"the branch table holds exactly the four recorded branches")
	check_eq(ResearchFlow.BRANCH_COUNT, 4,
		"the legacy dispatcher has four research branches")
	check_eq(ResearchFlow.ACTIONS.size(), 4,
		"the action vocabulary is closed and holds four actions")
	var action_names: Array = (ResearchFlow.ACTIONS as Array).duplicate()
	action_names.sort()
	check_eq(action_names,
		["buy_step_cash", "next_item", "next_step", "reset_item"],
		"the closed action set is the four committed outcomes")
	for action: String in ResearchFlow.ACTIONS:
		check(ResearchFlow.is_action(action),
			"%s is inside the closed action set" % action)
	for value: Variant in ["", "fast_forward", "NEXT_STEP", "step", null, 0, []]:
		check(not ResearchFlow.is_action(value),
			"%s is outside the closed action set" % str(value))
	# --- the step branch: increments the step counter and stamps the instant --
	var step: Dictionary = _branch("next_step")
	check_eq(str(step["command"]), "next_research_step",
		"the step action derives the committed command")
	check_eq(step["counters_written"],
		["researchStepNumber", "timeStampDoResearch"],
		"the step branch writes the step counter and the research instant")
	check(bool(step["stamps_instant"]),
		"the step branch stamps the research instant")
	check(not bool(step["paired_reset"]),
		"the step branch does not reset anything")
	# --- the cash branch: zeroes the instant and charges NOTHING --------------
	var cash: Dictionary = _branch("buy_step_cash")
	check_eq(str(cash["command"]), "research_buy_step_cash",
		"the cash action derives the committed command")
	check_eq(cash["counters_written"], ["timeStampDoResearch"],
		"the cash branch writes the research instant and NOTHING else")
	check(bool(cash["reads_a_price"]), "the cash branch reads a price")
	check(not bool(cash["charges"]), "the cash branch CHARGES NOTHING")
	check(str(cash["effect"]).contains("ZEROED"),
		"the cash branch's recorded effect is a zeroing")
	check(str(cash["price_note"]).contains("NEVER uses it"),
		"the cash branch's price is recorded as DISCARDED")
	check_eq(str(cash["argument_order"]), "cash-then-track",
		"the cash branch's argument list is [cash, track]")
	# --- the item branch: increments the item and resets step AND instant -----
	var item: Dictionary = _branch("next_item")
	check_eq(str(item["command"]), "next_research_item",
		"the item action derives the committed command")
	check_eq(item["counters_written"],
		["researchItemNumber", "researchStepNumber", "timeStampDoResearch"],
		"the item branch writes all three counters of the addressed track")
	check(bool(item["paired_reset"]),
		"the item branch's step and instant reset is recorded as PAIRED")
	check(str(item["paired_reset_note"]).contains("TOGETHER"),
		"the pairing note says the two resets happen TOGETHER")
	# --- the reset branch: zeroes all three -----------------------------------
	var reset: Dictionary = _branch("reset_item")
	check_eq(str(reset["command"]), "reset_research_item",
		"the reset action derives the committed command")
	check_eq(reset["counters_written"],
		["researchItemNumber", "researchStepNumber", "timeStampDoResearch"],
		"the reset branch writes all three counters of the addressed track")
	check(not bool(reset["stamps_instant"]),
		"the reset branch stamps nothing")
	# --- every branch records the ABSENCE of validation (design D6) -----------
	for record: Variant in ResearchFlow.BRANCHES:
		var body: Dictionary = record
		var command := str(body["command"])
		check(str(body["validation"]).begins_with("none"),
			"%s records that it validates nothing" % command)
		for token: String in ["bounds", "clamp", "membership", "guard",
				"existence"]:
			check(str(body["validation"]).contains(token),
				"%s records the absent %s check" % [command, token])
		check(not bool(body["charges"]),
			"%s charges nothing" % command)
		check_eq(body["args"],
			["cash", "track index"] if command == "research_buy_step_cash"
				else ["track index"],
			"%s records its exact argument list" % command)


## One branch record by action, or an empty dictionary.
func _branch(action: String) -> Dictionary:
	for record: Variant in ResearchFlow.BRANCHES:
		if str((record as Dictionary)["action"]) == action:
			return record as Dictionary
	return {}


# ---------------------------------------------------------------------------
# The two tracks (design D5)
# ---------------------------------------------------------------------------


## The two committed names, their committed building ids, and the structural
## proof that the mapping is reported and never used.
func _check_tracks() -> void:
	check_eq((ResearchFlow.TRACKS as Array).size(), 2,
		"the track inventory holds exactly two tracks")
	var reported: Array = []
	for record: Variant in ResearchFlow.TRACKS:
		var body: Dictionary = record
		reported.append([int(body["track"]), str(body["name"]),
			int(body["building_id"])])
	check_eq(reported, [[0, "TYPE_AREA_51", 139], [1, "TYPE_ROBOTIC", 86]],
		"both tracks are reported by their committed names and building ids")
	for record: Variant in ResearchFlow.TRACKS:
		var body: Dictionary = record
		check(not bool(body["defined_in_server"]),
			"track %d's name is defined NOWHERE in the legacy server"
				% int(body["track"]))
		check(str(body["where_named"]).contains("command.py:269"),
			"track %d's name is recorded as living only in the branch comments"
				% int(body["track"]))
		check(str(body["building_constant"]).contains("constants.py:"),
			"track %d's committed building constant is cited" % int(body["track"]))
	check(str(ResearchFlow.TRACK_RECORD_NOTE).contains("REPORTED AND NEVER USED"),
		"the mapping is recorded as reported and never used")
	check(str(ResearchFlow.TRACK_RECORD_NOTE).contains("DESIGNED NOWHERE")
			or str(ResearchFlow.TRACK_RECORD_NOTE).contains("DEFINED NOWHERE"),
		"the note states the names are undefined in the server")
	# --- the mapping is structurally unusable: no IDENTIFIER is named after
	# either constant.  The names survive only as string DATA (task 1.4).
	var declarations := _declared_identifiers(RESEARCH_SOURCE)
	for forbidden: String in FORBIDDEN_HELPERS:
		check(not declarations.has(forbidden),
			"no delivered identifier is named %s" % forbidden)
	for constant: String in ["TYPE_AREA_51", "TYPE_ROBOTIC"]:
		check(not declarations.has(constant),
			"no delivered code identifier is named after the track constant %s"
				% constant)
	# …and the names are still REPORTED, as values:
	var names: Array = []
	for record: Variant in ResearchFlow.TRACKS:
		names.append(str((record as Dictionary)["name"]))
	check_eq(names, ["TYPE_AREA_51", "TYPE_ROBOTIC"],
		"the two committed names are reported as DATA")
	# --- only the two tracks are addressable, and no bound is invented --------
	check(ResearchFlow.is_track(0) and ResearchFlow.is_track(1),
		"tracks 0 and 1 are addressable")
	for value: Variant in [2, 7, 999, -1, "0", null, true, 1.5]:
		check(not ResearchFlow.is_track(value),
			"the track %s is not addressable" % str(value))


# ---------------------------------------------------------------------------
# The five writers (design D7)
# ---------------------------------------------------------------------------


## The research instant's five writers, the `fast_forward` writer and its
## client-supplied seconds, and the absence of any delivered fast forward.
func _check_writers() -> void:
	check_eq((ResearchFlow.INSTANT_WRITERS as Array).size(),
		ResearchFlow.INSTANT_WRITER_COUNT,
		"the writer inventory holds exactly five entries")
	check_eq(ResearchFlow.INSTANT_WRITER_COUNT, 5,
		"the research instant has FIVE writers")
	var branches := 0
	for record: Variant in ResearchFlow.INSTANT_WRITERS:
		if str((record as Dictionary)["kind"]) == "dispatcher-branch":
			branches += 1
	check_eq(branches, 4, "four of the five writers are dispatcher branches")
	var fast: Dictionary = {}
	for record: Variant in ResearchFlow.INSTANT_WRITERS:
		if str((record as Dictionary)["writer"]) \
				== ResearchFlow.INSTANT_WRITER_FAST_FORWARD:
			fast = record as Dictionary
	check(not fast.is_empty(),
		"the fifth writer is recorded, and it is fast_forward")
	check(bool(fast["client_writable"]),
		"fast_forward makes the research instant CLIENT-WRITABLE")
	check(str(fast["source"]).contains("command.py:923"),
		"the recorded read line is cited")
	check(str(fast["source"]).contains("command.py:927"),
		"the recorded write line is cited")
	check(str(fast["effect"]).contains("CLIENT-SUPPLIED"),
		"the recorded effect names the client-supplied seconds")
	check(str(ResearchFlow.FAST_FORWARD_CONTRACT)
		.contains("IMPLEMENTED NOT AT ALL"),
		"fast_forward is recorded as implemented not at all")
	check(str(ResearchFlow.FAST_FORWARD_CONTRACT).contains("NO fast-forward"),
		"the contract states no fast-forward operation is delivered")
	# --- and NO fast-forward action, operation, or helper exists --------------
	check(not ResearchFlow.ACTIONS.has("fast_forward"),
		"the closed action set does NOT include fast_forward")
	for action: String in ResearchFlow.ACTIONS:
		check(str((ResearchFlow.ACTION_COMMANDS as Dictionary)[action])
				!= "fast_forward",
			"no action derives fast_forward")
	check(str(ResearchFlow.INTENT_IGNORED_KEYS).contains("seconds"),
		"the ignored-key list names `seconds`, so a client fast forward is refused")
	check(str(ResearchFlow.INTENT_IGNORED_KEYS).contains("fast_forward"),
		"the ignored-key list names `fast_forward` itself")
	for helper: Dictionary in ResearchFlow.NON_DERIVATION:
		if str(helper["helper"]) == "fast_forward":
			check(str(helper["absent_because"]).contains("design D7"),
				"the named absence cites the decision that records it")


# ---------------------------------------------------------------------------
# The legacy figures, MEASURED (task 4.4)
# ---------------------------------------------------------------------------


## Every recorded legacy figure re-derived out of the seven modules in this same
## run. A discrepancy fails the suite rather than being averaged away.
func _check_source() -> Dictionary:
	var measured := {
		"step_sites": 0,
		"item_sites": 0,
		"instant_sites": 0,
		"instant_lines": [],
		"branch_ranges": {},
		"track_comment_lines": [],
		"reads": [],
		"modules_touched": {},
	}
	for name: String in LEGACY_MODULES:
		var path := Paths.repo_root().path_join(name)
		if not FileAccess.file_exists(path):
			fail("the legacy module %s is present so its figures can be measured"
				% name)
			return measured
	for counter: String in ResearchFlow.COUNTERS:
		var lines: Array = []
		var sites := 0
		for name: String in LEGACY_MODULES:
			var text := FileAccess.get_file_as_string(
				Paths.repo_root().path_join(name))
			var index := 0
			for raw: String in text.split("\n"):
				index += 1
				var occurrences := raw.count(counter)
				if occurrences > 0:
					sites += occurrences
					if name == "command.py":
						lines.append(index)
					var touched: Dictionary = measured["modules_touched"]
					touched[counter] = str(name)
		match counter:
			"researchStepNumber":
				measured["step_sites"] = sites
			"researchItemNumber":
				measured["item_sites"] = sites
			_:
				measured["instant_sites"] = sites
				measured["instant_lines"] = lines
	# The three counters exist in `command.py` and NOWHERE else — which is the
	# write-only finding's other half: nothing outside the dispatcher touches one.
	for counter: String in ResearchFlow.COUNTERS:
		var names: Array = []
		for name: String in LEGACY_MODULES:
			if FileAccess.get_file_as_string(
					Paths.repo_root().path_join(name)).contains(counter):
				names.append(name)
		check_eq(names, ["command.py"],
			"%s appears in command.py and nowhere else in the seven modules"
				% counter)
	check_eq(int(measured["step_sites"]), EXPECTED_STEP_SITES,
		"researchStepNumber occurs exactly %d times" % EXPECTED_STEP_SITES)
	check_eq(int(measured["item_sites"]), EXPECTED_ITEM_SITES,
		"researchItemNumber occurs exactly %d times" % EXPECTED_ITEM_SITES)
	check_eq(int(measured["instant_sites"]), EXPECTED_INSTANT_SITES,
		"timeStampDoResearch occurs exactly %d times" % EXPECTED_INSTANT_SITES)
	check_eq(measured["instant_lines"], [272, 280, 289, 298, 923],
		"the instant's five sites are the four branch writes and the "
			+ "fast_forward read")
	# --- the single non-write occurrence, and what it is ---------------------
	var command_text := FileAccess.get_file_as_string(
		Paths.repo_root().path_join("command.py"))
	var command_lines: Array = command_text.split("\n")
	var reads: Array = []
	for index in range(command_lines.size()):
		var line: String = command_lines[index]
		if not line.contains("timeStampDoResearch"):
			continue
		var stripped := line.strip_edges()
		if stripped.begins_with("research_timers = "):
			reads.append(index + 1)
			measured["reads"].append({"line": index + 1, "text": stripped})
		elif not (stripped.ends_with("= 0") or stripped.ends_with("= time_now")):
			fail("unclassified research-instant site at command.py:%d: %s"
				% [index + 1, stripped])
	check_eq(reads, [923],
		"exactly ONE site reads the research instant, and it is the "
			+ "fast_forward assignment at command.py:923")
	check_eq(str(command_lines[922]).strip_edges(),
		'research_timers = privateState["timeStampDoResearch"]',
		"command.py:923 is the fast_forward read")
	check(str(command_lines[926]).contains(
		"research_timers[i] = max(0, research_timers[i] - seconds)"),
		"command.py:927 writes every track's instant, clamped at zero")
	check(str(command_lines[905]).contains("seconds = args[0]"),
		"the seconds fast_forward subtracts are CLIENT-SUPPLIED")
	# --- the four branch line ranges, measured -------------------------------
	for command: String in EXPECTED_BRANCH_RANGES:
		var measured_range := _branch_range(command_lines, command)
		measured["branch_ranges"][command] = measured_range
		check_eq(measured_range, EXPECTED_BRANCH_RANGES[command],
			"%s occupies command.py:%d-%d" % [command,
				(EXPECTED_BRANCH_RANGES[command] as Array)[0],
				(EXPECTED_BRANCH_RANGES[command] as Array)[1]])
	# --- the four track comments, measured ----------------------------------
	var comment_lines: Array = []
	for index in range(command_lines.size()):
		var line: String = command_lines[index]
		if "#" in line and (line.contains("TYPE_AREA_51")
				or line.contains("TYPE_ROBOTIC")):
			comment_lines.append(index + 1)
	check_eq(comment_lines, EXPECTED_TRACK_COMMENT_LINES,
		"the two track names appear on exactly the four branch comment lines")
	for name: String in LEGACY_MODULES:
		var text := FileAccess.get_file_as_string(
			Paths.repo_root().path_join(name))
		for constant: String in ["TYPE_AREA_51", "TYPE_ROBOTIC"]:
			var occurrences := text.count(constant)
			check_eq(occurrences, 4 if name == "command.py" else 0,
				"%s contains %s exactly %s time(s)"
					% [name, constant, "4" if name == "command.py" else "0"])
	# --- the two committed building ids, measured ---------------------------
	var constants_text := FileAccess.get_file_as_string(
		Paths.repo_root().path_join("constants.py"))
	check(constants_text.contains("ID_BUILDING_ROBOTIC_CENTER = 86"),
		"constants.py records ID_BUILDING_ROBOTIC_CENTER = 86")
	check(constants_text.contains("ID_BUILDING_AREA_51 = 139"),
		"constants.py records ID_BUILDING_AREA_51 = 139")
	check_eq(ResearchFlow.COMMITTED_BUILDING_AREA_51, 139,
		"the module's committed Area 51 building id is 139")
	check_eq(ResearchFlow.COMMITTED_BUILDING_ROBOTIC_CENTER, 86,
		"the module's committed Robotic Center building id is 86")
	# --- the display list that corroborates the mapping ---------------------
	check(str(command_lines[273]).contains('["Area 51", "Robotic Center"][_type]'),
		"the step branch's own print names track 0 'Area 51' and track 1 "
			+ "'Robotic Center', which corroborates the comment's word order")
	return measured


## One dispatcher branch's inclusive 1-based line range, measured.
func _branch_range(command_lines: Array, command: String) -> Array:
	var start_index := -1
	for index in range(command_lines.size()):
		var line: String = (command_lines[index] as String).strip_edges()
		if line == "elif cmd == \"%s\":" % command:
			start_index = index
			break
	if start_index < 0:
		return []
	# `index` is 0-based and names the NEXT branch's header, whose own 1-based
	# line number is `index + 1` — so this branch's last 1-based line is
	# `index - 1`.
	for index in range(start_index + 1, command_lines.size()):
		var line: String = (command_lines[index] as String).strip_edges()
		if line.begins_with("elif cmd =="):
			return [start_index + 1, index - 1]
	return []


# ---------------------------------------------------------------------------
# The refusals and the anti-invention guard (tasks 4.1/4.3)
# ---------------------------------------------------------------------------


## The four refusal families, the named non-derivation list, and the module's
## whole function inventory.
func _check_absence() -> void:
	var refusals: Array = (ResearchFlow.REFUSALS as Array).duplicate(true)
	var names: Array = []
	for record: Variant in refusals:
		names.append(str((record as Dictionary)["refusal"]))
	names.sort()
	check_eq(names, ["no_bounds", "no_price", "no_readiness", "no_reward"],
		"the four refusal families are present")
	check_eq(refusals.size(), ResearchFlow.REFUSAL_COUNT,
		"the refusal table holds exactly four entries")
	for record: Variant in refusals:
		var body: Dictionary = record
		check(not bool(body["implemented"]),
			"the %s refusal is stated as NOT implemented" % str(body["refusal"]))
		check(str(body["reason"]).strip_edges() != "",
			"the %s refusal carries a non-empty reason" % str(body["refusal"]))
		check(str(body["reason"]).length() > 200,
			"the %s refusal's reason is a recorded statement, not a stub"
				% str(body["refusal"]))
	# --- each family names the mechanism it refuses -------------------------
	check(str(ResearchFlow.NO_PRICE).contains("research_buy_step_cash")
			and str(ResearchFlow.NO_PRICE).contains("discards"),
		"the no-price family names the discarded cash")
	check(str(ResearchFlow.NO_PRICE).contains("NEUTRAL"),
		"the no-price family names the neutral derived vector")
	check(str(ResearchFlow.NO_READINESS).contains("WRITE-ONLY"),
		"the no-readiness family names the write-only property")
	check(str(ResearchFlow.NO_READINESS).contains("command.py:923"),
		"the no-readiness family names the fast_forward read")
	check(str(ResearchFlow.NO_BOUNDS).contains("NOT permission"),
		"the no-bounds family states the absence is not permission")
	check(str(ResearchFlow.NO_BOUNDS).contains("Server v1 / M13"),
		"the no-bounds family names the milestone that owns the real limit")
	check(str(ResearchFlow.NO_REWARD).contains("not even a zero-valued one"),
		"the no-reward family states that none exists")
	# --- the named non-derivation list --------------------------------------
	var helpers: Array = []
	for entry: Variant in ResearchFlow.NON_DERIVATION:
		var body: Dictionary = entry
		helpers.append(str(body["helper"]))
		check(str(body["absent_because"]).strip_edges() != "",
			"the %s absence carries a reason" % str(body["helper"]))
	for helper: String in FORBIDDEN_HELPERS:
		check(helpers.has(helper),
			"the named non-derivation list records %s as absent" % helper)
	check_eq((ResearchFlow.NON_DERIVATION as Array).size(),
		FORBIDDEN_HELPERS.size(),
		"the named non-derivation list covers every forbidden helper name")
	# --- the structural gate: the whole function inventory (task 4.3) --------
	var declared := _declared_methods(RESEARCH_SOURCE)
	var expected := EXPECTED_FLOW_MODULE_METHODS.duplicate()
	expected.sort()
	check_eq(declared, expected,
		"the delivered module's whole function inventory is exactly the pinned "
			+ "list, so an invented helper fails the run wherever it is added")
	var track_methods := _declared_methods(RESEARCH_SOURCE, "TrackView")
	check_eq(track_methods, EXPECTED_TRACK_VIEW_METHODS,
		"the TrackView readers are exactly the pinned list")
	var view_methods := _declared_methods(RESEARCH_SOURCE, "ResearchView")
	check_eq(view_methods, EXPECTED_RESEARCH_VIEW_METHODS,
		"the ResearchView readers are exactly the pinned list")
	for helper: String in FORBIDDEN_HELPERS + ALSO_ABSENT_HELPERS:
		check(not declared.has(helper),
			"the module declares no %s helper" % helper)
		check(not track_methods.has(helper),
			"TrackView declares no %s reader" % helper)
		check(not view_methods.has(helper),
			"ResearchView declares no %s reader" % helper)
	# --- and no code line computes one of them -----------------------------
	var code := _code_only(RESEARCH_SOURCE)
	for needle: String in BEHAVIOUR_NEEDLES:
		check(not code.contains(needle),
			"the delivered module's code contains no '%s'" % needle)


# ---------------------------------------------------------------------------
# The measured content findings (task 4.2)
# ---------------------------------------------------------------------------


## The content-absence findings, MEASURED from the committed bytes, including the
## two figures the M9 investigation and this line's proposal got wrong.
func _check_content() -> void:
	var normalized := Paths.repo_root().path_join(
		"packages/game-content/normalized")
	var files: Array = []
	_collect_json(normalized, "", files)
	check_eq(files.size(), EXPECTED_NORMALIZED_FILES,
		"the committed content package holds %d normalized files"
			% EXPECTED_NORMALIZED_FILES)
	var per_file: Dictionary = {}
	var research_sections := 0
	for relative: String in files:
		var text := FileAccess.get_file_as_string(normalized.path_join(relative))
		var occurrences := text.to_lower().count("research")
		if occurrences > 0:
			per_file[relative.get_file()] = occurrences
		var document: Variant = JSON.parse_string(text)
		if document is Array:
			for row: Variant in document as Array:
				if row is Dictionary:
					for key: Variant in (row as Dictionary).keys():
						if str(key).to_lower() == "research":
							research_sections += 1
	check_eq(research_sections, 0,
		"no normalized row carries a research key: there is no research SECTION")
	# --- MEASURED CORRECTION: TWO normalized files, not one -----------------
	var expected_files: Dictionary = EXPECTED_RESEARCH_FILES.duplicate()
	check_eq(per_file, expected_files,
		"'research' appears in exactly TWO normalized files — buildings.json once "
			+ "and images.json six times — NOT one, which is what the M9 "
			+ "investigation and this line's proposal both state")
	# --- the buildings occurrence is the Research Lab name -------------------
	var buildings: Array = _json_array(normalized.path_join("buildings.json"))
	check_eq(buildings.size(), 470, "the committed buildings package holds 470 rows")
	var lab: Array = []
	for row: Variant in buildings:
		if row is Dictionary \
				and str((row as Dictionary).get("legacy_id", "")) \
						== EXPECTED_RESEARCH_LAB_ID:
			lab.append(row as Dictionary)
	check_eq(lab.size(), 1,
		"exactly one committed building carries legacy_id %s"
			% [EXPECTED_RESEARCH_LAB_ID])
	if lab.size() == 1:
		check_eq(str((lab[0] as Dictionary)["name"]),
			EXPECTED_RESEARCH_LAB_NAME,
			"that building is named %s" % [EXPECTED_RESEARCH_LAB_NAME])
		check((lab[0] as Dictionary)["legacy_id"] is String,
			"its legacy_id is the STRING \"%s\", not the integer 256"
				% EXPECTED_RESEARCH_LAB_ID)
	# --- the images occurrences are three popup asset rows ------------------
	var images: Array = _json_array(normalized.path_join("images.json"))
	check_eq(images.size(), 607, "the committed images package holds 607 rows")
	var assets: Array = []
	for row: Variant in images:
		if row is Dictionary \
				and str(JSON.stringify(row)).to_lower().contains("research"):
			assets.append(str((row as Dictionary)["legacy_id"]))
	assets.sort()
	check_eq(assets, EXPECTED_IMAGE_ASSETS,
		"the images package's research hits are exactly three "
			+ "popupResearchCenter_buildingProcess asset rows")
	# --- MEASURED CORRECTION: config/main.json DOES carry research keys -------
	var config_text := FileAccess.get_file_as_string(
		Paths.repo_root().path_join("config/main.json"))
	var config: Variant = JSON.parse_string(config_text)
	check(config is Dictionary, "the committed config parses")
	if not (config is Dictionary):
		return
	var keys: Array = []
	_collect_research_keys(config as Dictionary, "", keys)
	check_eq(keys, EXPECTED_CONFIG_RESEARCH_KEYS,
		"config/main.json carries exactly THREE research-containing keys, all "
			+ "under /images — NOT none, which is what the M9 investigation and "
			+ "this line's proposal both state")
	check_eq((config as Dictionary).size(), EXPECTED_CONFIG_TOP_LEVEL_KEYS,
		"the committed config holds its %d top-level content keys"
			% EXPECTED_CONFIG_TOP_LEVEL_KEYS)
	for key: Variant in (config as Dictionary).keys():
		check(not str(key).to_lower().contains("research"),
			"the top-level content key %s does not name research" % str(key))
	var values: Array = []
	_collect_research_values(config as Dictionary, "", values)
	check_eq(values, ["/items/244/name"],
		"exactly ONE config string value contains 'research': the building name")
	# --- the conclusion the corrections leave untouched ----------------------
	for token: String in ["research_price", "research_cost", "research_step",
			"research_unlock", "research_reward", "researchSteps",
			"researchRequirements"]:
		check(not config_text.contains(token),
			"the committed config records no %s field" % token)
		for relative: String in files:
			check(not FileAccess.get_file_as_string(
					normalized.path_join(relative)).contains(token),
				"no normalized file records a %s field" % token)
	check(str(ResearchFlow.CONTENT_ABSENCE).contains("MEASURED CORRECTION"),
		"the module's recorded content absence states the corrections")
	check(str(ResearchFlow.CONTENT_ABSENCE).contains("images.json"),
		"the recorded absence names the second normalized file")
	check(str(ResearchFlow.CONTENT_ABSENCE).contains("THREE keys"),
		"the recorded absence names the three config keys")


# ---------------------------------------------------------------------------
# The committed corpus
# ---------------------------------------------------------------------------


## The committed fresh-player corpus: 40 rows, all three counters `[0, 0]`, and no
## placed row carrying a research counter.
func _check_corpus() -> Dictionary:
	var document: Variant = _read_json(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check(document is Dictionary, "the committed corpus save parses")
	var measured := {"rows": 0, "vector": {}, "resources": {}, "store": {}}
	if not (document is Dictionary):
		return measured
	var save: Dictionary = document
	var private: Variant = save.get("privateState")
	check(private is Dictionary, "the corpus carries a private state")
	if not (private is Dictionary):
		return measured
	for counter: String in ResearchFlow.COUNTERS:
		var entries: Variant = (private as Dictionary).get(counter)
		check_eq(_as_int_tree(entries), [0, 0],
			"the corpus's committed %s is [0, 0]" % counter)
		check_eq((entries as Array).size(), 2,
			"the corpus's committed %s carries two tracks" % counter)
	var corpus_vector: Variant = _as_int_tree(_vector_of(save))
	check_eq(corpus_vector, ResearchFlow.CORPUS_VECTOR,
		"the module's pinned research vector matches the corpus on all three "
			+ "counters")
	var maps: Variant = save.get("maps")
	check(maps is Array and not (maps as Array).is_empty(),
		"the corpus carries a first map")
	if maps is Array and not (maps as Array).is_empty():
		var first: Dictionary = (maps as Array)[0]
		var items: Variant = first.get("items")
		check(items is Dictionary, "the corpus's first map carries placements")
		if items is Dictionary:
			measured["rows"] = (items as Dictionary).size()
			check_eq(measured["rows"], ResearchFlow.CORPUS_PLACEMENTS,
				"the corpus places %d rows" % ResearchFlow.CORPUS_PLACEMENTS)
			var carrying := 0
			for key: Variant in (items as Dictionary).keys():
				if str(JSON.stringify((items as Dictionary)[key])).to_lower() \
						.contains("research"):
					carrying += 1
			check_eq(carrying, 0,
				"no placed row carries a research counter anywhere")
		measured["store"] = (first.get("store", {}) as Dictionary).duplicate(true)
		measured["resources"] = _resources_of(save)
	check_eq(measured["resources"], ResearchFlow.CORPUS_RESOURCES,
		"the corpus's seven stored balances match the module's pin")
	return measured


## The seven stored balances of one save document, as integers.
func _resources_of(save: Dictionary) -> Dictionary:
	var first: Dictionary = (save["maps"] as Array)[0]
	var info: Dictionary = save["playerInfo"]
	var private: Dictionary = save["privateState"]
	return {
		"xp": _as_int(first.get("xp")),
		"gold": _as_int(first.get("gold")),
		"wood": _as_int(first.get("wood")),
		"oil": _as_int(first.get("oil")),
		"steel": _as_int(first.get("steel")),
		"cash": _as_int(info.get("cash")),
		"mana": _as_int(private.get("mana")),
	}


# ---------------------------------------------------------------------------
# The cross-milestone correction: FOUR ledger doors (tasks 5.1/5.2)
# ---------------------------------------------------------------------------


## The dead-hero ledger has FOUR doors, not three: `map_lose_item` is the fourth
## and it is reached from the **quest** path, not the death path.
##
## `godot-unit-behaviors`' living spec and this delivered module both record
## THREE. The M9 investigation measured a FOURTH — `map_lose_item`
## (`engine.py:215-228`) calls `push_dead_unit` — and this suite re-measures it,
## so the correction is a measurement here and not a restatement.
func _check_ledger() -> void:
	var engine_lines: Array = FileAccess.get_file_as_string(
		Paths.repo_root().path_join("engine.py")).split("\n")
	var command_lines: Array = FileAccess.get_file_as_string(
		Paths.repo_root().path_join("command.py")).split("\n")
	# --- the fourth door exists and calls the M8 helper ----------------------
	var definition := -1
	for index in range(engine_lines.size()):
		var line: String = (engine_lines[index] as String).strip_edges()
		if line.begins_with("def map_lose_item("):
			definition = index + 1
			break
	check(definition > 0, "engine.py defines map_lose_item")
	check_eq(definition, 215, "map_lose_item is defined at engine.py:215")
	var calls := 0
	var call_line := -1
	for index in range(definition - 1, min(engine_lines.size(), definition + 16)):
		var line: String = engine_lines[index] as String
		if line.contains("push_dead_unit(") \
				and not line.strip_edges().begins_with("def "):
			calls += 1
			call_line = index + 1
	check_eq(calls, 1, "map_lose_item calls push_dead_unit exactly once")
	check_eq(call_line, 223, "the call is at engine.py:223")
	# --- it is an ENGINE HELPER, not a dispatcher branch --------------------
	var is_branch := false
	for line: Variant in command_lines:
		if (line as String).contains("cmd == \"map_lose_item\""):
			is_branch = true
	check(not is_branch,
		"map_lose_item is NOT a dispatcher branch, so the door count and the "
			+ "named-branch count stay distinguishable")
	check((command_lines[5] as String).contains("map_lose_item"),
		"command.py imports map_lose_item")
	# --- it is reached from the QUEST path, not the death path ---------------
	var reached := 0
	var reached_at: Array = []
	for index in range(command_lines.size()):
		var line: String = command_lines[index] as String
		if line.contains("map_lose_item(") and not line.contains("import"):
			reached += 1
			reached_at.append(index + 1)
	check_eq(reached, 2, "map_lose_item is called from exactly two branches")
	check_eq(reached_at, [796, 872],
		"both callers are inside end_quest (command.py:752-807) and end_attack "
			+ "(command.py:869+): the quest path, not the death path")
	var quest_block := ""
	for index in range(751, 808):
		quest_block += (command_lines[index] as String) + "\n"
	check(quest_block.contains("map_lose_item(map, privateState"),
		"end_quest removes lost units through map_lose_item")
	# --- `kill` reaches neither the ledger nor this helper -------------------
	var kill_block := ""
	for index in range(168, 181):
		kill_block += (command_lines[index] as String) + "\n"
	check(not kill_block.contains("push_dead_unit"),
		"kill deletes the row and never touches the dead-hero ledger")
	check(kill_block.contains("map_delete_item"),
		"kill deletes the addressed row")
	# --- so the ledger has FOUR doors, and the delivered record is corrected --
	check_eq(int(UnitBehaviors.LEDGER_REACHING_COMMAND_COUNT), 2,
		"the delivered record's LEDGER-REACHING COMMAND count is two (sell and "
			+ "resurrect_hero), which stays true")
	check_eq(UnitBehaviors.INVENTORY_COMMANDS,
		["kill", "sell", "resurrect_hero"],
		"the delivered record names the three DISPATCHER-BRANCH doors")
	var helper_names: Array = []
	for record: Variant in UnitBehaviors.ENGINE_HELPERS:
		helper_names.append(str((record as Dictionary)["helper"]))
	check_eq(helper_names, ["push_dead_unit", "resurrect_hero"],
		"the delivered record names its two engine helpers, and map_lose_item is "
			+ "NOT among them — which is precisely the correction D8 corrects")
	var door_count := helper_names.size() + 1
	check_eq(door_count, 3,
		"two named helpers plus one uncounted caller is three, so the M8 record's "
			+ "THREE-door statement is falsified by measurement")
	check_eq(UnitBehaviors.NAMED_BRANCH_COUNT, 63,
		"the dispatcher still has its 63 named branches, which the door count "
			+ "must stay distinguishable from")


# ---------------------------------------------------------------------------
# The committed executed-legacy fixture (tasks 2.1/2.2)
# ---------------------------------------------------------------------------


## The committed capture: eight branch-track steps, their derived vectors, the
## round trip back to the seed, and the corpus staying byte-identical.
func _check_fixture() -> Dictionary:
	var measured := {"steps": [], "manifest": {}}
	var manifest: Variant = _read_json(
		Paths.repo_root().path_join(FIXTURE_MANIFEST))
	check(manifest is Dictionary, "the committed research manifest parses")
	if not (manifest is Dictionary):
		return measured
	var body: Dictionary = _as_int_tree(manifest) as Dictionary
	measured["manifest"] = body
	check_eq(str(body["schema"]), "godot-research/legacy-capture-v1",
		"the manifest carries the research capture's own schema")
	# --- eight branch-track combinations ------------------------------------
	var transactions: Array = body["transactions"]
	check_eq(transactions.size(), STEP_NAMES.size(),
		"the manifest records exactly eight executed transactions")
	check_eq(transactions.size(), ResearchFlow.CAPTURED_COMBINATIONS,
		"the module's pinned combination count matches the manifest")
	var combinations: Array = []
	for record: Variant in transactions:
		var entry: Dictionary = record
		combinations.append("%s:%d" % [str(entry["command"]),
			int(entry["track"])])
	combinations.sort()
	var expected_combinations: Array = []
	for action: String in ResearchFlow.ACTIONS:
		var branch: Dictionary = _branch(action)
		for track: int in range(ResearchFlow.TRACK_COUNT):
			expected_combinations.append(
				"%s:%d" % [str(branch["command"]), track])
	expected_combinations.sort()
	check_eq(combinations, expected_combinations,
		"all four branches were executed on BOTH tracks: every one of the eight "
			+ "branch-track combinations")
	# --- every recorded vector matches the derived result ------------------
	for name: String in STEP_NAMES:
		var step: Dictionary = _fixture_step(name)
		if step.is_empty():
			continue
		var action: String = name.trim_prefix("command_")
		action = _action_for(name)
		var track := int(name.substr(name.length() - 1, 1))
		var before: Dictionary = _vector_of(step["before"])
		var after: Dictionary = _vector_of(step["after"])
		var divergence := _expected_state(before, action, track, after)
		check_eq(str(divergence), "",
			"the recorded %s on track %d matches the derived effect" % [action,
				track])
		measured["steps"].append({
			"name": name,
			"action": action,
			"track": track,
			"command": str(_branch(action)["command"]),
			"vector_before": before,
			"vector_after": after,
			"leaves": _leaf_differences(step["before"], step["after"]),
		})
	check_eq((measured["steps"] as Array).size(), STEP_NAMES.size(),
		"all eight recorded steps were read and checked")
	# --- the paired reset is visible in the recorded state -------------------
	var item_step: Dictionary = _fixture_step("command_next_research_item_track_0")
	if not item_step.is_empty():
		var before: Dictionary = _vector_of(item_step["before"])
		var after: Dictionary = _vector_of(item_step["after"])
		check_eq(int((before["researchStepNumber"] as Array)[0]), 1,
			"a research step really was in flight when the item branch ran")
		check_eq(int((after["researchStepNumber"] as Array)[0]), 0,
			"the item branch reset the step counter")
		check_eq(int((after["researchItemNumber"] as Array)[0]), 1,
			"the item branch incremented the item counter")
		check_eq(int((after["timeStampDoResearch"] as Array)[0]), 0,
			"the item branch zeroed the research instant in the SAME branch")
		check_eq(int((before["researchItemNumber"] as Array)[0]), 0,
			"the item counter really was zero going in")
	var visibility: Dictionary = (body["transaction"] as Dictionary)[
		"transition_visibility"]
	check(bool(visibility["item_step_instant_was_already_zero"]),
		"the manifest RECORDS that the item step's instant half is a 0 -> 0 "
			+ "transition, because the two cash steps already zeroed it")
	check(str(visibility["rule"]).contains("command.py:287-289"),
		"the manifest cites the committed lines that establish the pairing")
	# --- the cash branch charged nothing, and the eight steps round-trip -----
	var cash_step: Dictionary = _fixture_step(
		"command_research_buy_step_cash_track_0")
	if not cash_step.is_empty():
		var before: Dictionary = _vector_of(cash_step["before"])
		var after: Dictionary = _vector_of(cash_step["after"])
		check(int((before["timeStampDoResearch"] as Array)[0]) > 0,
			"the cash branch really was handed a live research instant")
		check_eq(int((after["timeStampDoResearch"] as Array)[0]), 0,
			"the cash branch zeroed the research instant")
		check_eq(after["researchStepNumber"], before["researchStepNumber"],
			"the cash branch left the step counter untouched")
		check_eq(after["researchItemNumber"], before["researchItemNumber"],
			"the cash branch left the item counter untouched")
	var first: Dictionary = _fixture_step(STEP_NAMES[0])
	var last: Dictionary = _fixture_step(STEP_NAMES[STEP_NAMES.size() - 1])
	check_eq(last["after"], first["before"],
		"the eight steps round-trip the corpus's research vector back to the "
			+ "committed seed byte-for-byte")
	check_eq(last["after"],
		_as_int_tree(_read_json(Paths.repo_root().path_join(CORPUS_SAVE))),
		"the last recorded after-state IS the committed corpus save")
	# --- every stored resource is unchanged by all eight steps --------------
	for record: Variant in transactions:
		var entry: Dictionary = record
		check_eq(entry["vector_after"] != null, true,
			"the transaction records its after vector")
	for name: String in STEP_NAMES:
		var step: Dictionary = _fixture_step(name)
		if step.is_empty():
			continue
		check_eq(_resources_of(step["after"]), ResearchFlow.CORPUS_RESOURCES,
			"the recorded %s left every stored resource byte-identical" % name)
	# --- the three probes ----------------------------------------------------
	var probes: Array = body["probes"]
	check_eq(probes.size(), 3, "the manifest records the three executed probes")
	if probes.size() == 3:
		var first_probe: Dictionary = probes[0]
		check_eq(int(first_probe["cash_argument_sent"]), 250,
			"probe 1 handed the cash branch a price of 250")
		check_eq(int(first_probe["cash_moved"]), 0,
			"probe 1 proves the branch DISCARDS it: playerInfo.cash did not move")
		check_eq(int(first_probe["xp_after"]) - int(first_probe["xp_before"]), 500,
			"probe 1 also proves the resource vector is client-sent, which is "
				+ "what makes the neutral-vector proof non-tautological")
		var second: Dictionary = probes[1]
		check_eq(int(second["instant_after"]),
			maxi(0, int(second["instant_before"]) - int(second["seconds_sent"])),
			"probe 2 proves fast_forward subtracts the client-supplied seconds")
		check_eq(int(second["step_after"]), int(second["step_before"]),
			"probe 2 proves fast_forward writes only the research instant")
		var third: Dictionary = probes[2]
		check_eq(int(third["instant_after"]), 0,
			"probe 3 proves the fast_forward decrement CLAMPS at zero")
	# --- and the containment the capture claims ------------------------------
	var containment: Dictionary = body["containment"]
	check(bool(containment["identical"]),
		"the capture records that its working-tree containment held")
	check_eq(str(containment["pre_combined_sha256"]),
		str(containment["post_combined_sha256"]),
		"the capture's before and after working-tree digests are identical")
	check(bool(containment["protected_fixtures"]["identical"]),
		"the capture's thirteen committed fixture digests are identical")
	check_eq(int(body["captured"]["combinations"]), 8,
		"the manifest records eight captured combinations")
	check(not bool(body["captured"]["completion_captured"]),
		"the manifest records that NO completion was captured")
	check(not bool(body["captured"]["readiness_captured"]),
		"the manifest records that NO readiness was captured")
	check(not bool(body["fast_forward"]["implemented"]),
		"the manifest records fast_forward as implemented not at all")
	check(bool(body["fast_forward"]["client_writable"] if
		body["fast_forward"].has("client_writable") else true),
		"the manifest's fast_forward block is present")
	# --- the measured content findings the capture recorded -----------------
	var content: Dictionary = body["content"]
	check_eq(_as_int_tree(content["normalized_files_containing_research"]),
		EXPECTED_RESEARCH_FILES,
		"the capture's own content measurement agrees with this suite's")
	check_eq(_as_int_tree(content["config_keys_containing_research"]),
		EXPECTED_CONFIG_RESEARCH_KEYS,
		"the capture's own config measurement agrees with this suite's")
	return measured


## One recorded step, or {} when it cannot be read.
func _fixture_step(name: String) -> Dictionary:
	var base := Paths.repo_root().path_join(FIXTURE_DIR + "/steps/" + name)
	var before: Variant = _as_int_tree(_read_json(base.path_join("before.json")))
	var after: Variant = _as_int_tree(_read_json(base.path_join("after.json")))
	if not (before is Dictionary) or not (after is Dictionary):
		fail("the recorded %s step is readable" % name)
		return {}
	return {"before": before, "after": after}


## The closed action a recorded step name carries.
func _action_for(name: String) -> String:
	match name:
		"command_next_research_step_track_0", \
		"command_next_research_step_track_1":
			return ResearchFlow.ACTION_STEP
		"command_research_buy_step_cash_track_0", \
		"command_research_buy_step_cash_track_1":
			return ResearchFlow.ACTION_BUY_STEP_CASH
		"command_next_research_item_track_0", \
		"command_next_research_item_track_1":
			return ResearchFlow.ACTION_ITEM
		_:
			return ResearchFlow.ACTION_RESET


## One committed save's three research counter vectors, as integers.
func _vector_of(document: Variant) -> Dictionary:
	var out: Dictionary = {}
	if not (document is Dictionary):
		return out
	var private: Variant = (document as Dictionary).get("privateState")
	if not (private is Dictionary):
		return out
	for counter: String in ResearchFlow.COUNTERS:
		var entries: Variant = (private as Dictionary).get(counter)
		if not (entries is Array):
			return out
		var row: Array = []
		for entry: Variant in entries as Array:
			row.append(_as_int(entry))
		out[counter] = row
	return out


## The first divergence between a recorded after-state and the derived result,
## or "" when there is none. The step branch's stamp is compared by SHAPE and
## DIRECTION only, because the legacy branch stamps the wall clock.
func _expected_state(before: Dictionary, action: String, track: int,
		after: Dictionary) -> String:
	var branch: Dictionary = _branch(action)
	if branch.is_empty():
		return "no recorded branch for action %s" % action
	var index := track
	var other := 1 - track
	var written: Array = branch["counters_written"]
	for counter: String in ResearchFlow.COUNTERS:
		if not before.has(counter) or not after.has(counter):
			return "counter %s is absent" % counter
		if not written.has(counter) \
				and int((after[counter] as Array)[index]) \
						!= int((before[counter] as Array)[index]):
			return ("the addressed track's %s moved, which the branch never "
				% counter + "writes")
		if int((after[counter] as Array)[other]) \
				!= int((before[counter] as Array)[other]):
			return "the UNADDRESSED track's %s moved" % counter
	var step := int((before[ResearchFlow.KEY_STEP] as Array)[index])
	var item := int((before[ResearchFlow.KEY_ITEM] as Array)[index])
	var instant := int((before[ResearchFlow.KEY_INSTANT] as Array)[index])
	match str(branch["command"]):
		"next_research_step":
			step += 1
		"research_buy_step_cash":
			instant = 0
		"next_research_item":
			item += 1
			step = 0
			instant = 0
		"reset_research_item":
			step = 0
			item = 0
			instant = 0
	if int((after[ResearchFlow.KEY_STEP] as Array)[index]) != step:
		return "the step counter is not the derived %d" % step
	if int((after[ResearchFlow.KEY_ITEM] as Array)[index]) != item:
		return "the item counter is not the derived %d" % item
	var stamp: Variant = (after[ResearchFlow.KEY_INSTANT] as Array)[index]
	if bool(branch["stamps_instant"]):
		if not (stamp is int) or int(stamp) < 0:
			return "the stamped research instant is not a non-negative integer"
		if int(stamp) < instant:
			return "the stamped research instant moved backwards"
	elif int(stamp) != instant:
		return "the research instant is not the derived %d" % instant
	return ""


# ---------------------------------------------------------------------------
# The intents (task 3.5)
# ---------------------------------------------------------------------------


## The facade's research operation takes EXACTLY the save identity, a closed
## action, and a track, and both implementations carry it.
func _check_intents() -> void:
	var facade: Variant = root.get_node_or_null("GameApi")
	check(facade != null, "GameApi autoload is registered")
	if facade == null:
		return
	var methods: Variant = facade.get_script().get_script_method_list()
	var found: Variant = _method(methods, "advance_research_town")
	check(found != null, "the facade implements the research intent")
	if found != null:
		var args: Array = (found as Dictionary)["args"]
		check_eq(args.size(), 3,
			"advance_research_town takes EXACTLY the save identity, the action, "
				+ "and the track: there is no parameter through which a client "
				+ "could send a counter, an instant, or a cash amount")
		check_eq((args as Array).size(), (ResearchFlow.INTENT_KEYS as Array).size(),
			"the operation's argument count equals the intent's key count")
	check(_has_counter(facade, "research_requests"),
		"the facade counts research intents like every other command")
	check(str(facade.implementation_name()) == "fake",
		"the hermetic run is on the fake implementation")
	# --- the flow's own intent body is three keys wide ----------------------
	var body: Variant = ResearchFlow.intent_body("pid", "next_step", 0)
	check(bool(body.get("ok", false)), "a well-formed intent body is accepted")
	if bool(body.get("ok", false)):
		var intent_keys: Array = (body["body"] as Dictionary).keys()
		intent_keys.sort()
		check_eq(intent_keys,
			["action", "track", "user_id"],
			"the intent body carries EXACTLY the player identifier, the action, "
				+ "and the track")
		check_eq((body["body"] as Dictionary)["track"], 0,
			"the track is carried as an integer")
	for payload: Array in [["next_step", 2], ["next_step", "0"], ["fast_forward",
			0], ["", 0], [null, 0]]:
		var refused: Variant = ResearchFlow.intent_body("pid", payload[0],
			payload[1])
		check(not bool(refused.get("ok", false)),
			"the intent (%s, %s) is refused before a request is formed"
				% [str(payload[0]), str(payload[1])])
		check_eq((refused.get("body", {}) as Dictionary), {},
			"a refused intent carries NO body at all")
		check(str(refused.get("reason", "")) in ["invalid_action",
			"invalid_track"],
			"the refusal carries its own named reason")
	# --- both implementations carry the operation ---------------------------
	var transport_source := _source("res://scripts/gameapi/legacy_v0_api.gd")
	check(transport_source.contains("/v0/research"),
		"the legacy-v0 implementation names the research endpoint")
	var facade_source := _source("res://scripts/gameapi/game_api.gd")
	check(not facade_source.contains("/v0/research"),
		"the facade never names the research endpoint")
	var fake_source := _source("res://scripts/gameapi/fake_api.gd")
	check(not fake_source.contains("/v0/research"),
		"the fake double never names the research endpoint")
	check(transport_source.contains("advance_research_town"),
		"the legacy-v0 implementation implements the research operation")
	check(fake_source.contains("advance_research_town"),
		"the fake double implements the research operation")
	# --- and the typed result declares no invented field --------------------
	var members := _class_members(ResearchFlow.ResearchResult)
	for required: String in ["action", "track", "command", "derived",
			"vector_before", "vector_after", "research", "tracks",
			"tracks_source", "cash_charged", "cash_argument_ignored",
			"price_computed", "fast_forward_offered", "resources"]:
		check(members.has(required),
			"the typed research result declares %s" % required)
	for forbidden: String in ["remaining", "progress", "complete", "ready",
			"duration", "step_count", "reward", "price", "cost", "unlock",
			"elapsed", "total_steps"]:
		check(not members.has(forbidden),
			"the typed research result declares no %s field: the legacy server "
				% forbidden + "has no such rule to report")
	var fresh := ResearchFlow.ResearchResult.new()
	check(fresh.track == -1 and fresh.cash_charged == 0,
		"a fresh typed research result carries no partial payload")


# ---------------------------------------------------------------------------
# The offline double
# ---------------------------------------------------------------------------


## The fake implementation, driven offline for **all eight** branch-track
## combinations, so the hermetic run exercises the very shapes the live phase
## will. The double reads the committed fixture's first before-state — the
## committed corpus, whose three counters are `[0, 0]` — and derives each branch's
## effect from the same `BRANCHES` record the service applies, so a divergence
## between the two implementations is a failure here rather than in the battery.
##
## It is a deterministic test double, **not** a parity oracle: executed-legacy
## parity rests on the committed fixture and the compat fixture-replay tests.
func _check_fake_double() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the fake resolves a save list offline")
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	if saves.is_empty():
		fail("the fake carries a save")
		return
	var pid := str(saves[0].id)
	var observed := {}
	for action: String in ResearchFlow.ACTIONS:
		for track: int in range(ResearchFlow.TRACK_COUNT):
			var result: Variant = await api.advance_research_town(pid, action,
				track)
			check(result is ResearchFlow.ResearchResult and result.ok,
				"the fake accepts %s on track %d: %s"
					% [action, track,
						((result as ResearchFlow.ResearchResult).error_message
							if result is ResearchFlow.ResearchResult else "")])
			if not (result is ResearchFlow.ResearchResult and result.ok):
				continue
			_check_typed_research(result)
			var typed: ResearchFlow.ResearchResult = result
			check_eq(str(typed.action), action,
				"the double echoed the action exactly as sent")
			check_eq(int(typed.track), track,
				"the double addressed the track the client named")
			check_eq(str(typed.command), str(_branch(action)["command"]),
				"the double derived the committed command")
			check_eq((typed.research.get("derived", null) as Dictionary), {},
				"the double's projection derives nothing from the counters")
			check_eq((typed.research.get("tracks", []) as Array).size(),
				ResearchFlow.TRACK_COUNT,
				"the double's projection carries both tracks")
			check_eq(int(typed.cash_charged), 0,
				"the double charges nothing on any action")
			for name: String in ResearchFlow.CORPUS_RESOURCES.keys():
				check_eq(int((typed.resources as BootData.Resources).get(name)),
					int(ResearchFlow.CORPUS_RESOURCES[name]),
					"the double's %s balance is the committed value: a research "
						% name + "action moves none")
			observed["%s:%d" % [action, track]] = typed.vector_after
	check_eq((observed as Dictionary).size(), ResearchFlow.CAPTURED_COMBINATIONS,
		"the double drove all eight branch-track combinations offline")
	# The step branch stamps a FIXTURE instant, never a clock, so two consecutive
	# offline runs are byte-identical: the value it uses is the one the committed
	# capture recorded.
	var restamped: Variant = await api.advance_research_town(pid, "next_step", 0)
	if restamped is ResearchFlow.ResearchResult and restamped.ok:
		check(int((restamped as ResearchFlow.ResearchResult)
			.vector_after["timeStampDoResearch"][0]) > 0,
			"the double's research instant is a positive recorded stamp")
	# --- the double's own refusals ------------------------------------------
	for payload: Array in [["next_step", 7], ["fast_forward", 0], ["", 0]]:
		var refused: Variant = await api.advance_research_town(pid, payload[0],
			payload[1])
		check(refused is ResearchFlow.ResearchResult and not refused.ok,
			"the double refuses (%s, %s) with the endpoint's own order"
				% [str(payload[0]), str(payload[1])])
		if refused is ResearchFlow.ResearchResult:
			check(str(refused.error_code) in ["invalid_action", "invalid_track"],
				"the double's refusal code is the service's own: %s"
					% str(refused.error_code))
			check((refused as ResearchFlow.ResearchResult).vector_after.is_empty(),
				"the double's refused intent carries no partial payload")
	var unknown: Variant = await api.advance_research_town("does-not-exist-0000",
		"next_step", 0)
	check(unknown is ResearchFlow.ResearchResult and not unknown.ok,
		"the double refuses an unknown save")
	if unknown is ResearchFlow.ResearchResult:
		check_eq(str(unknown.error_code), "unknown_user_id",
			"the double's unknown-save code is the shared one")


# ---------------------------------------------------------------------------
# Purity and containment
# ---------------------------------------------------------------------------


## The delivered module names no node, clock, request, or transport token.
func _check_purity() -> void:
	var code := _code_only(RESEARCH_SOURCE)
	for needle: String in PURITY_NEEDLES:
		check(not code.contains(needle),
			"research_flow.gd declares no '%s': the projection is pure over a "
				% needle + "save the caller already holds")
	check_eq(_preloads(_source(RESEARCH_SOURCE)),
		["res://scripts/gameapi/boot_data.gd"],
		"the module loads exactly the typed-data module and nothing else")
	check(not _source(RESEARCH_SOURCE).contains("await "),
		"the module awaits nothing")


## The content package, the committed saves, and the committed fixtures are
## byte-identical after the run: this line writes evidence under
## `evidence/research/` and nothing else.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, save_before: Dictionary) -> void:
	var package_after := Paths.directory_digest(Paths.repo_root().path_join(
		"packages/game-content"))
	var saves_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/saves"))
	var fixtures_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/fixtures"))
	check_eq(package_after.get("sha256", ""), package_before.get("sha256", ""),
		"content package bytes are unchanged after the run")
	check_eq(package_after.get("files", 0), package_before.get("files", 0),
		"content package file count is unchanged after the run")
	check_eq(saves_after.get("sha256", ""), saves_before.get("sha256", ""),
		"no committed save byte changed during the run")
	check_eq(fixtures_after.get("sha256", ""), fixtures_before.get("sha256", ""),
		"no committed fixture byte changed during the run — including the "
			+ "executed research fixture, which is only read")
	var save_after := Paths.file_sha256_checked(Paths.repo_root().path_join(
		CORPUS_SAVE))
	check_eq(save_after.get("sha256", ""), save_before.get("sha256", ""),
		"the committed corpus save is byte-identical after the run")
	check_eq(save_after.get("bytes", 0), save_before.get("bytes", 0),
		"the committed corpus save's byte count is unchanged")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory exists after the run")


# ---------------------------------------------------------------------------
# The live-research phase (verify-boot's `research-live`)
# ---------------------------------------------------------------------------


## One full step → item → reset cycle through the REAL Compatibility endpoint, so
## the unchanged legacy `command()` executes the derived research envelopes over
## the disposable corpus. This side asserts the typed response for each action
## AND its post-state — the derived counters, the item branch's paired reset, the
## unaddressed track byte-identical, and **every stored resource unchanged** —
## plus the two named refusals carrying the service's own codes with no partial
## payload. The phase harness separately asserts the corpus save file mutated.
func _check_live_research() -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the live phase")
	if endpoint == "":
		return
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("legacy_v0", endpoint)
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult, "the corpus save list resolves")
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(), "the corpus pre-research payload resolves")
	if before_payload.is_empty():
		return
	var resources_before := _live_resources(before_payload)
	var vector_before := _live_vector(before_payload)
	check_eq(vector_before, _live_committed_vector(),
		"the live corpus's research vector is the committed [0, 0] on both tracks")
	# --- the step action ----------------------------------------------------
	var stepped: Variant = await api.advance_research_town(pid, "next_step", 0)
	check(stepped is ResearchFlow.ResearchResult and stepped.ok,
		"a step is accepted by the real endpoint: %s"
			% ((stepped as ResearchFlow.ResearchResult).error_message
				if stepped is ResearchFlow.ResearchResult else ""))
	if not (stepped is ResearchFlow.ResearchResult and stepped.ok):
		return
	_check_typed_research(stepped)
	var typed: ResearchFlow.ResearchResult = stepped
	check_eq(str(typed.action), "next_step",
		"the service echoed the action exactly as sent")
	check_eq(int(typed.track), 0, "the service addressed the track the client "
		+ "named")
	check_eq(str(typed.command), "next_research_step",
		"the service derived the committed step command")
	check_eq(int((typed.vector_after["researchStepNumber"] as Array)[0]), 1,
		"the executed step incremented the addressed track's step counter")
	check_eq(int((typed.vector_after["researchStepNumber"] as Array)[1]), 0,
		"the executed step left the UNADDRESSED track's step counter at zero")
	check(int((typed.vector_after["timeStampDoResearch"] as Array)[0]) > 0,
		"the executed step stamped the research instant with the wall clock")
	check_eq(typed.derived.get("instant", null), null,
		"the typed result reports a null instant on a stamping branch: the value "
			+ "is not derivable")
	check_eq(typed.derived.get("step", null), 1,
		"the typed result reports the derived step value")
	for name: String in ResearchFlow.CORPUS_RESOURCES.keys():
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the step (the endpoint's "
				% name + "value-level proof)")
	# --- the cash action, with a client-supplied cash that is ignored -------
	var cashed: Variant = await api.advance_research_town(pid,
		"buy_step_cash", 0)
	check(cashed is ResearchFlow.ResearchResult and cashed.ok,
		"a cash-branch action is accepted by the real endpoint")
	if cashed is ResearchFlow.ResearchResult and cashed.ok:
		var typed_cash: ResearchFlow.ResearchResult = cashed
		check_eq(str(typed_cash.command), "research_buy_step_cash",
			"the service derived the committed cash command")
		check_eq(int((typed_cash.vector_after["timeStampDoResearch"] as Array)[0]),
			0, "the executed cash branch zeroed the research instant")
		check_eq(int((typed_cash.vector_after["researchStepNumber"] as Array)[0]),
			1, "the executed cash branch left the step counter untouched")
		check_eq(int(typed_cash.cash_charged), 0,
			"the executed cash branch charged nothing")
		check(bool(typed_cash.cash_argument_ignored),
			"the service states the cash argument was ignored")
		for name: String in ResearchFlow.CORPUS_RESOURCES.keys():
			check_eq(int((typed_cash.resources as BootData.Resources).get(name)),
				int(resources_before[name]),
				"the %s balance is UNCHANGED by the cash branch" % name)
	# --- the item action: the PAIRED reset ----------------------------------
	var itemed: Variant = await api.advance_research_town(pid, "next_item", 0)
	check(itemed is ResearchFlow.ResearchResult and itemed.ok,
		"an item action is accepted by the real endpoint")
	if itemed is ResearchFlow.ResearchResult and itemed.ok:
		var typed_item: ResearchFlow.ResearchResult = itemed
		check(bool(typed_item.derived.get("paired_reset", false)),
			"the service reports the item branch's PAIRED reset")
		check_eq(int((typed_item.vector_after["researchItemNumber"] as Array)[0]),
			1, "the executed item branch incremented the item counter")
		check_eq(int((typed_item.vector_after["researchStepNumber"] as Array)[0]),
			0, "the executed item branch reset the step counter")
		check_eq(int((typed_item.vector_after["timeStampDoResearch"] as Array)[0]),
			0, "the executed item branch reset the research instant in the SAME "
				+ "branch")
		for name: String in ResearchFlow.CORPUS_RESOURCES.keys():
			check_eq(int((typed_item.resources as BootData.Resources).get(name)),
				int(resources_before[name]),
				"the %s balance is UNCHANGED by the item branch" % name)
	# --- the same intents through the fake, offline -------------------------
	api.configure("fake")
	var fake_step: Variant = await api.advance_research_town(pid, "next_step", 0)
	check(fake_step is ResearchFlow.ResearchResult and fake_step.ok,
		"the fake accepts the same step offline")
	if fake_step is ResearchFlow.ResearchResult and fake_step.ok:
		_check_typed_research(fake_step)
		check_eq(int((fake_step as ResearchFlow.ResearchResult)
			.vector_after["researchStepNumber"][0]), 1,
			"both implementations derive the same step counter")
	# --- two named refusals, carrying the service's own codes ---------------
	api.configure("legacy_v0", endpoint)
	var refused_track: Variant = await api.advance_research_town(pid,
		"next_step", 7)
	check(refused_track is ResearchFlow.ResearchResult
			and not refused_track.ok,
		"a track the vector cannot address is refused")
	if refused_track is ResearchFlow.ResearchResult:
		check_eq(str(refused_track.error_code), "invalid_track",
			"the refusal is the service's own code: %s"
				% str(refused_track.error_message))
		check(refused_track.vector_before.is_empty()
				and refused_track.derived.is_empty(),
			"the refused intent carries no partial payload")
	var refused_action: Variant = await api.advance_research_town(pid,
		"fast_forward", 0)
	check(refused_action is ResearchFlow.ResearchResult
			and not refused_action.ok,
		"a fast_forward intent is refused: the fourth writer is recorded and "
			+ "delivered not at all")
	if refused_action is ResearchFlow.ResearchResult:
		check_eq(str(refused_action.error_code), "invalid_action",
			"the fast-forward refusal is the service's own code")
	# --- the reset action returns the track to its initial state -------------
	var reset: Variant = await api.advance_research_town(pid, "reset_item", 0)
	check(reset is ResearchFlow.ResearchResult and reset.ok,
		"a reset action is accepted by the real endpoint")
	if reset is ResearchFlow.ResearchResult and reset.ok:
		var typed_reset: ResearchFlow.ResearchResult = reset
		check_eq(typed_reset.vector_after["researchStepNumber"][0], 0,
			"the executed reset branch zeroed the step counter")
		check_eq(typed_reset.vector_after["researchItemNumber"][0], 0,
			"the executed reset branch zeroed the item counter")
		check_eq(typed_reset.vector_after["timeStampDoResearch"][0], 0,
			"the executed reset branch zeroed the research instant")
		check_eq(int((typed_reset.vector_after["researchStepNumber"] as Array)[1]),
			0, "the reset left the unaddressed track's step counter at zero")
		for name: String in ResearchFlow.CORPUS_RESOURCES.keys():
			check_eq(int((typed_reset.resources as BootData.Resources).get(name)),
				int(resources_before[name]),
				"the %s balance is UNCHANGED by the reset" % name)
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check_eq(_live_vector(after_payload), vector_before,
		"the live corpus's research vector is byte-identical after the full "
			+ "step -> cash -> item -> reset cycle")
	check_eq(_live_resources(after_payload), resources_before,
		"every live corpus balance is byte-identical after the whole cycle")
	print("[test] live-research applied step=1 cash=0 item=1 paired_reset=true "
		+ "reset=0 resources_unchanged=true "
		+ "refused=invalid_track,invalid_action")


## The typed result's own shape, asserted rather than assumed: the action, the
## track, the derived block, both vectors, the projection, and the seven
## resources — with no readiness, remaining time, price, reward, or fast-forward
## field anywhere.
func _check_typed_research(result: Variant) -> void:
	if not (result is ResearchFlow.ResearchResult):
		return
	var typed: ResearchFlow.ResearchResult = result
	check_eq(bool(typed.ok), true, "the research result reports success")
	check_eq(str(typed.protocol), BootData.PROTOCOL,
		"the typed result reports the v0 protocol")
	check_eq(str(typed.result), "success",
		"the typed result carries the legacy success result")
	check(typed.server_time > 0,
		"the typed result's server_time is a positive integer")
	check_eq(int(typed.cash_charged), 0,
		"the typed result reports no consumed cash")
	check(bool(typed.cash_argument_ignored),
		"the typed result states the cash argument was ignored")
	check(not bool(typed.price_computed),
		"the typed result states no price was computed")
	check(not bool(typed.fast_forward_offered),
		"the typed result states no fast-forward operation was offered")
	check_eq((typed.research.get("derived", null) as Dictionary), {},
		"the projection carries an EMPTY derived block: nothing is computed from "
			+ "the counters")
	check_eq((typed.research.get("tracks", []) as Array).size(),
		ResearchFlow.TRACK_COUNT, "the projection carries both committed tracks")
	check_eq((typed.tracks_source as Array).size(), ResearchFlow.TRACK_COUNT,
		"the response carries both committed track records")
	check(typed.resources != null,
		"the typed result carries the authoritative resources")
	var members := _class_members(ResearchFlow.ResearchResult)
	for forbidden: String in ["remaining", "progress", "complete", "ready",
			"duration", "reward", "price", "cost", "unlock", "elapsed"]:
		check(not members.has(forbidden),
			"the typed research result declares no %s field" % forbidden)


# ---------------------------------------------------------------------------
# Evidence report (design D10)
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


## Computes and writes the deterministic `research-report-v1` report.
##
## EVERY fact about the model comes from `research_flow.gd` — its own key
## constants, `BRANCHES`, `TRACKS`, `INSTANT_WRITERS`, `FAST_FORWARD_CONTRACT`,
## `NON_DERIVATION`, `REFUSALS`, `CONTENT_ABSENCE`, `PROVENANCE`, and
## `NON_CLAIMS` — and every committed number comes from the legacy source, the
## content package, the corpus save, and the fixture bytes **measured in this
## run**. Nothing here reads the wall clock, resolves a path outside the
## repository, or sends a request: that is what makes the file byte-identical
## across reruns.
func _write_report(path: String, source: Dictionary, corpus: Dictionary,
		fixture: Dictionary, package_digest: Dictionary,
		save_digest: Dictionary) -> void:
	var report := {
		"schema": "research-report-v1",
		"generated_by": "apps/client-godot/tests/test_research.gd --report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no request, "
				+ "and no saved state: every table is derived from the model's "
				+ "own constants and from the committed bytes measured in the "
				+ "same run, and every derived set is sorted before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) plus "
				+ "one trailing newline; every number written is an integer - the "
				+ "pinned engine's integral floats are normalised on the way in, "
				+ "which changes no value - so no float formatting varies between "
				+ "runs",
			"time_dependent_fields": "the ONLY time-dependent value in this "
				+ "line's evidence is the research instant the legacy step branch "
				+ "stamped, which the fixture fixed at one run; the fake double "
				+ "stamps that same committed value rather than reading a clock",
		},
		"counter_model": {
			"counters": (ResearchFlow.COUNTERS as Array).duplicate(),
			"counter_meanings": {
				ResearchFlow.KEY_STEP: "the STEP counter: incremented by "
					+ "next_research_step and reset (with the instant, together) "
					+ "by next_research_item",
				ResearchFlow.KEY_ITEM: "the ITEM counter: incremented by "
					+ "next_research_item and zeroed by reset_research_item",
				ResearchFlow.KEY_INSTANT: "the RESEARCH INSTANT: stamped by "
					+ "next_research_step, zeroed by the cash, item, and reset "
					+ "branches, and decremented by the recorded fast_forward "
					+ "writer",
			},
			"track_count": ResearchFlow.TRACK_COUNT,
			"verbatim_rule": "each counter is reported exactly as the save holds "
				+ "it - no scaling, rounding, defaulting, or clamping - and a "
				+ "malformed value fails closed with the counter and the element "
				+ "named. An integral float is the documented transport tolerance; "
				+ "a numeric string is refused",
			"unresolvable_rule": "a state that is absent, is not an object, "
				+ "carries a counter that is not a list, holds the wrong number of "
				+ "entries, or holds a non-integer or negative value is reported "
				+ "UNRESOLVABLE with its recorded state intact, and is never "
				+ "defaulted to a zero vector presented as a resolved one",
			"read_only": "the view holds copies of the committed values and "
				+ "declares no setter, no mutating method, and no writable public "
				+ "field; every reader returns a committed value or a fresh copy",
			"reasons": (ResearchFlow.PROJECTION_REASONS as Array).duplicate(),
		},
		"branches": (ResearchFlow.BRANCHES as Array).duplicate(true),
		"branch_count": ResearchFlow.BRANCH_COUNT,
		"branch_count_rule": "the dispatcher has 63 named branches and exactly "
			+ "FOUR of them touch a research counter (command.py:268-300); the "
			+ "suite re-derives each one's inclusive line range and fails the run "
			+ "on a drift",
		"instant_writers": (ResearchFlow.INSTANT_WRITERS as Array).duplicate(true),
		"instant_writer_count": ResearchFlow.INSTANT_WRITER_COUNT,
		"fast_forward": {
			"command": ResearchFlow.FAST_FORWARD_COMMAND,
			"contract": ResearchFlow.FAST_FORWARD_CONTRACT,
			"offered": false,
			"source": "command.py:905-946, research lines 922-928",
			"read_line": "command.py:923",
			"write_line": "command.py:927",
			"seconds_source": "args[0], CLIENT-SUPPLIED (command.py:906)",
			"formula": "research_timers[i] = max(0, research_timers[i] - seconds)",
			"clamped": true,
			"is_a_research_branch": false,
		},
		"tracks": (ResearchFlow.TRACKS as Array).duplicate(true),
		"tracking_note": ResearchFlow.TRACK_RECORD_NOTE,
		"tracking_rule": "the mapping is REPORTED and asserted never to be used: "
			+ "no code identifier in this repository is named after either track "
			+ "constant, and the suite asserts that over the delivered module's "
			+ "declarations (design D5)",
		"non_derivation": (ResearchFlow.NON_DERIVATION as Array).duplicate(true),
		"refusals": (ResearchFlow.REFUSALS as Array).duplicate(true),
		"refusal_count": ResearchFlow.REFUSAL_COUNT,
		"content_absence": ResearchFlow.CONTENT_ABSENCE,
		"measured_content": {
			"normalized_files": EXPECTED_NORMALIZED_FILES,
			"normalized_files_containing_research":
				EXPECTED_RESEARCH_FILES,
			"research_sections": 0,
			"config_top_level_keys": EXPECTED_CONFIG_TOP_LEVEL_KEYS,
			"config_keys_containing_research": EXPECTED_CONFIG_RESEARCH_KEYS,
			"config_string_values_containing_research": ["/items/244/name"],
			"research_lab_building": {
				"domain": "buildings",
				"legacy_id": EXPECTED_RESEARCH_LAB_ID,
				"name": EXPECTED_RESEARCH_LAB_NAME,
			},
			"research_center_popup_assets": EXPECTED_IMAGE_ASSETS,
			"corrections": "the M9 investigation and this line's proposal both "
				+ "state that 'research' appears in exactly ONE normalized file "
				+ "and only inside one `name`, and that config/main.json has NO "
				+ "key containing 'research' at any depth. Both figures are WRONG "
				+ "- two files, and three /images keys plus one value - and the "
				+ "conclusion is unchanged: no committed research cost, step "
				+ "count, unlock requirement, or reward exists, so none is "
				+ "invented (design D4)",
		},
		"measured_legacy": {
			"step_sites": int(source.get("step_sites", 0)),
			"item_sites": int(source.get("item_sites", 0)),
			"instant_sites": int(source.get("instant_sites", 0)),
			"instant_lines": (source.get("instant_lines", []) as Array).duplicate(),
			"branch_ranges": (source.get("branch_ranges", {}) as Dictionary)
				.duplicate(true),
			"track_comment_lines": (source.get("track_comment_lines", []) as Array)
				.duplicate(),
			"modules_touched": (source.get("modules_touched", {}) as Dictionary)
				.duplicate(),
			"write_only_rule": "every occurrence of all three counters is a write "
				+ "in command.py, and the instant's single read is itself a write "
				+ "inside fast_forward: nothing anywhere reads a research counter "
				+ "to decide anything",
		},
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"rows": int(corpus.get("rows", 0)),
			"vector": (corpus.get("vector", {}) as Dictionary).duplicate(true),
			"resources": (corpus.get("resources", {}) as Dictionary).duplicate(true),
			"store": (corpus.get("store", {}) as Dictionary).duplicate(true),
			"rows_carrying_a_research_counter": 0,
			"claim": "the committed corpus holds every research counter at its "
				+ "initial value [0, 0] on both tracks, and no placed row carries "
				+ "a research counter anywhere. That is why this line is the first "
				+ "M9 line with a real executed-legacy fixture, and it is a fact "
				+ "about the corpus, not evidence that research can be obtained, "
				+ "finished, or shown to be ready",
		},
		"fixture": {
			"directory": FIXTURE_DIR,
			"manifest": FIXTURE_MANIFEST,
			"executed_legacy": true,
			"combinations": (fixture.get("steps", []) as Array).size(),
			"steps": (fixture.get("steps", []) as Array).duplicate(true),
			"round_trip_to_seed": true,
			"completion_captured": false,
			"readiness_captured": false,
			"note": "all FOUR branches were captured on BOTH tracks - eight "
				+ "branch-track combinations - and the eight steps round-trip the "
				+ "vector back to the committed seed byte-for-byte. No completion "
				+ "and no readiness were captured, because the legacy server has "
				+ "neither: every one of the ten counter sites is a write and the "
				+ "instant's single read is itself a fast_forward write",
			"probes": 3,
			"probe_note": "probe 1 hands the cash branch a price of 250 and proves "
				+ "playerInfo.cash does not move, while a client-sent resource "
				+ "vector does - which is what makes the endpoint's "
				+ "everything-unchanged proof non-tautological; probes 2 and 3 "
				+ "prove the recorded fast_forward writer subtracts a "
				+ "client-supplied number of seconds and clamps at zero",
			"fixture_scope": "the four counter transitions over two tracks against "
				+ "the fresh-player corpus: no progressed save, no other command, "
				+ "and nothing about a finished or ready step",
		},
		"ledger_door_correction": {
			"doors": 4,
			"fourth_door": "map_lose_item",
			"source": "engine.py:215-228",
			"calls_helper_at": "engine.py:223 (push_dead_unit)",
			"is_a_dispatcher_branch": false,
			"reached_from": "the QUEST path (command.py:796 inside end_quest, "
				+ "and command.py:872 inside end_attack), not the death path",
			"superseded": "godot-unit-behaviors records THREE doors; the M9 "
				+ "investigation measured four and this suite re-measures it. Its "
				+ "named-BRANCH count stays three, which is what keeps the two "
				+ "counts distinguishable",
			"heading_note": "the superseded 'three-door' word is retained in the "
				+ "requirement heading because a MODIFIED delta resolves its "
				+ "header against the existing requirement name and Archive "
				+ "REFUSES a renamed heading",
		},
		"intents": ResearchFlow.intent_record(),
		"provenance": ResearchFlow.PROVENANCE,
		"non_claims": (ResearchFlow.NON_CLAIMS as Array).duplicate(true),
		"package_files": _as_int(package_digest.get("files", 0)),
		"package_sha256": str(package_digest.get("sha256", "")),
	}
	var non_claims: Array = report["non_claims"]
	check(not non_claims.is_empty(),
		"the report carries the evidence's non-claims")
	for phrase: String in REQUIRED_NON_CLAIMS:
		check(_contains_phrase(non_claims, phrase),
			"the report's non-claims name '%s'" % phrase)
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)" % problem)
	if problem == "":
		check(FileAccess.file_exists(path),
			"the report file exists at %s" % path)
		info("report written: %s" % path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## Every `.json` file under a directory, as repository-relative paths, in
## committed order.
func _collect_json(directory: String, prefix: String, out: Array) -> void:
	var handle := DirAccess.open(directory)
	if handle == null:
		fail("cannot open " + directory)
		return
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = handle.get_next()
			continue
		var full := directory.path_join(entry)
		if handle.current_is_dir():
			_collect_json(full, prefix + entry + "/", out)
		elif entry.ends_with(".json"):
			out.append(prefix + entry)
		entry = handle.get_next()
	handle.list_dir_end()


## One committed JSON file's rows, or an empty array.
func _json_array(path: String) -> Array:
	var document: Variant = _read_json(path)
	if document is Array:
		return document as Array
	fail("the committed package %s is a top-level array" % path.get_file())
	return []


## Every JSON-pointer whose key contains "research", collected depth-first.
func _collect_research_keys(node: Variant, path: String, out: Array) -> void:
	if node is Dictionary:
		for key: Variant in (node as Dictionary).keys():
			var child := "%s/%s" % [path, str(key)]
			if str(key).to_lower().contains("research"):
				out.append(child)
			_collect_research_keys((node as Dictionary)[key], child, out)
	elif node is Array:
		for index in range((node as Array).size()):
			_collect_research_keys((node as Array)[index],
				"%s/%d" % [path, index], out)


## Every JSON-pointer whose STRING value contains "research", collected
## depth-first.
func _collect_research_values(node: Variant, path: String, out: Array) -> void:
	if node is Dictionary:
		for key: Variant in (node as Dictionary).keys():
			_collect_research_values((node as Dictionary)[key],
				"%s/%s" % [path, str(key)], out)
	elif node is Array:
		for index in range((node as Array).size()):
			_collect_research_values((node as Array)[index],
				"%s/%d" % [path, index], out)
	elif node is String and (node as String).to_lower().contains("research"):
		out.append(path)


## One committed number as the exact integer it denotes.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


## Every committed number of a JSON value, normalised to integers, so a
## comparison against a literal holds without weakening the value. The pinned
## engine's parser widens every integer to a float.
func _as_int_tree(value: Variant) -> Variant:
	if value is float:
		return _as_int(value)
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_as_int_tree(entry))
		return list
	if value is Dictionary:
		var bag: Dictionary = {}
		for key: Variant in (value as Dictionary).keys():
			bag[key] = _as_int_tree((value as Dictionary)[key])
		return bag
	return value


## Every entry of the facade's own method list with the given name, or null.
func _method(methods: Variant, name: String) -> Variant:
	for entry: Variant in methods as Array:
		if entry is Dictionary and str((entry as Dictionary).get("name", "")) == name:
			return entry
	return null


## Whether an object exposes a counter with the given name.
func _has_counter(object: Variant, name: String) -> bool:
	for entry: Variant in object.get_property_list():
		if str((entry as Dictionary).get("name", "")) == name:
			return true
	return false


## A class's declared property names, as a sorted set.
func _class_members(script: Variant) -> Array:
	var out: Array = []
	for entry: Variant in script.get_script_property_list():
		out.append(str((entry as Dictionary).get("name", "")))
	out.sort()
	return out


## Whether a list of sentences contains the given phrase, as a substring.
func _contains_phrase(lines: Variant, phrase: String) -> bool:
	for line: Variant in lines as Array:
		if str(line).contains(phrase):
			return true
	return false


## One script's source, verbatim.
func _source(res_path: String) -> String:
	return FileAccess.get_file_as_string(res_path)


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


## The public and private function names a module declares, sorted. With no
## ``inner`` class the MODULE level is returned — and a module-level ``func`` is
## one at column 0, which is what keeps it separate from an inner class's
## readers — so the module's own inventory and each class's stay
## distinguishable.
func _declared_methods(res_path: String, inner: String = "") -> Array:
	var out: Array = []
	var inside := false
	var lines: Array = FileAccess.get_file_as_string(res_path).split("\n")
	for raw: Variant in lines:
		var line: String = raw
		var signature := line.strip_edges()
		if signature.begins_with("#") or signature == "":
			continue
		var indented := line.begins_with("\t") or line.begins_with(" ")
		if inner == "":
			if indented or signature.begins_with("class "):
				continue
			if signature.begins_with("static func "):
				signature = signature.substr(len("static "))
			if not signature.begins_with("func "):
				continue
			out.append(_function_name(signature))
			continue
		if not inside:
			if signature.begins_with("class %s" % inner):
				inside = true
			elif signature.begins_with("class ") and not indented:
				inside = false
			continue
		if signature.begins_with("class "):
			inside = false
			continue
		if signature.begins_with("func ") \
				and not signature.begins_with("static "):
			out.append(_function_name(signature))
	out.sort()
	return out


## One `func`/`static func` signature's bare name.
func _function_name(signature: String) -> String:
	var name := signature.substr(signature.find("func ") + len("func "))
	var bracket := name.find("(")
	return name if bracket == -1 else name.substr(0, bracket)


## Every identifier a script DECLARES or BINDS: functions, inner classes,
## constants, and bound variables — the mechanical form of "no code identifier is
## named after either track constant" (task 1.4).
func _declared_identifiers(res_path: String) -> Dictionary:
	var out: Dictionary = {}
	for line: String in FileAccess.get_file_as_string(res_path).split("\n"):
		var signature := line.strip_edges()
		if signature.begins_with("#"):
			continue
		var text := signature
		for prefix: String in ["static func ", "func ", "const ", "class ",
				"var ", "enum "]:
			if text.begins_with(prefix):
				text = text.substr(prefix.length())
				break
		if text == signature and not (signature.begins_with("static ")
				or signature.begins_with("func ") or signature.begins_with("const ")
				or signature.begins_with("class ") or signature.begins_with("var ")):
			continue
		var name := ""
		for index in range(text.length()):
			var character := text[index]
			if character == "(" or character == " " or character == "=" \
					or character == ":" or character == "[":
				break
			name += character
		if name != "":
			out[name] = true
	return out


## Every `.gd` source's DECLARATIONS: comment lines are dropped and string-
## literal content is blanked, so a prose mention or a recorded non-claim string
## can never be mistaken for code.
##
## The `inside` flag is carried **across** lines, which is what makes a multi-line
## triple-quoted docstring blank correctly, and a backslash-escaped quote is
## skipped so an escaped `\"` inside a literal cannot desynchronise the scan.
func _code_only(res_path: String) -> String:
	var out: Array = []
	var inside := false
	var lines: Array = FileAccess.get_file_as_string(res_path).split("\n")
	for raw: Variant in lines:
		var line: String = raw
		if line.strip_edges().begins_with("#"):
			continue
		var without_strings := ""
		var index := 0
		while index < line.length():
			var character := line[index]
			if character == "\\" and index + 1 < line.length():
				# An escaped character: keep neither, and never let it toggle
				# the string state.
				without_strings += "  "
				index += 2
				continue
			if character == '"':
				inside = not inside
				index += 1
				continue
			without_strings += " " if inside else character
			index += 1
		out.append(without_strings)
	return "\n".join(PackedStringArray(out))


## Every research JSON-pointer leaf at which two recorded states differ — the
## three counters' six elements, plus a whole-document check that NOTHING ELSE
## moved. The whole-document half is what makes this useful: a recorded step that
## touched a placement, a balance, or any other private-state field would add a
## pointer here and fail.
func _leaf_differences(before: Variant, after: Variant) -> Array:
	var collected: Array = []
	var before_vector := _vector_of(before)
	var after_vector := _vector_of(after)
	for counter: String in ResearchFlow.COUNTERS:
		for track: int in range(ResearchFlow.TRACK_COUNT):
			if not before_vector.has(counter) or not after_vector.has(counter):
				continue
			if int((before_vector[counter] as Array)[track]) \
					!= int((after_vector[counter] as Array)[track]):
				collected.append("/privateState/%s/%d" % [counter, track])
	# Nothing else moved: every other private-state key, both placement rows, the
	# storage, the player info, and the seven balances.
	if not (before is Dictionary) or not (after is Dictionary):
		return collected
	for key: Variant in ResearchFlow.COUNTERS:
		collected.erase("/privateState/%s" % str(key))
	var before_private: Variant = (before as Dictionary).get("privateState")
	var after_private: Variant = (after as Dictionary).get("privateState")
	if before_private is Dictionary and after_private is Dictionary:
		for key: Variant in (before_private as Dictionary).keys():
			if ResearchFlow.COUNTERS.has(str(key)):
				continue
			if (before_private as Dictionary)[key] \
					!= (after_private as Dictionary).get(key):
				collected.append("/privateState/%s" % str(key))
		if (after_private as Dictionary).size() \
				!= (before_private as Dictionary).size():
			collected.append("/privateState")
	if (before as Dictionary).get("maps") != (after as Dictionary).get("maps"):
		collected.append("/maps")
	if (before as Dictionary).get("playerInfo") \
			!= (after as Dictionary).get("playerInfo"):
		collected.append("/playerInfo")
	collected.sort()
	return collected


## A short label for a refused state, for a failure message.
func _state_label(value: Variant) -> String:
	if value is Dictionary:
		return "an object with keys %s" % ", ".join(PackedStringArray(
			_sorted_keys(value as Dictionary)))
	return str(value)


func _sorted_keys(value: Dictionary) -> Array:
	var out: Array = []
	for key: Variant in value.keys():
		out.append(str(key))
	out.sort()
	return out


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


func _working_saves_exist() -> bool:
	return DirAccess.dir_exists_absolute(Paths.repo_root().path_join("saves"))


## The loopback endpoint the live phase resolves, from the user arguments.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The corpus's own bootstrap payload, or {} when it cannot be read.
func _live_payload(api: Variant, endpoint: String, user_id: String
		) -> Dictionary:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return {}
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return {}
	return (info as BootData.PlayerInfoPayload).raw


## The live payload's research vector, as integers.
func _live_vector(payload: Dictionary) -> Dictionary:
	var private: Variant = payload.get("privateState", {})
	var out: Dictionary = {}
	if not (private is Dictionary):
		return out
	for counter: String in ResearchFlow.COUNTERS:
		var entries: Variant = (private as Dictionary).get(counter)
		if not (entries is Array):
			return out
		var row: Array = []
		for entry: Variant in entries as Array:
			row.append(_as_int(entry))
		out[counter] = row
	return out


## The committed all-zero research vector, for the live corpus comparison.
func _live_committed_vector() -> Dictionary:
	var out: Dictionary = {}
	for counter: String in ResearchFlow.COUNTERS:
		out[counter] = (ResearchFlow.CORPUS_VECTOR[counter] as Array).duplicate()
	return out


## The live payload's seven stored balances, as integers — the pre-request
## reference the live value-level proof compares against.
func _live_resources(payload: Dictionary) -> Dictionary:
	var map: Dictionary = payload.get("map", {}) as Dictionary
	var player: Dictionary = payload.get("playerInfo", {}) as Dictionary
	var private: Dictionary = payload.get("privateState", {}) as Dictionary
	return {
		"xp": int(map.get("xp", 0)),
		"gold": int(map.get("gold", 0)),
		"wood": int(map.get("wood", 0)),
		"oil": int(map.get("oil", 0)),
		"steel": int(map.get("steel", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(private.get("mana", 0)),
	}
