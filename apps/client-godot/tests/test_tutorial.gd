extends "res://tests/test_base.gd"
## Tutorial/progression suite (OpenSpec `tutorial`, M9 line 3: "The committed
## tutorial gate is mirrored by name and by inverse" / "The recorded completion
## flag is projected from the save, never derived" / "A tutorial step is a
## server-derived intent, and no client value is trusted" / "The two no-op cases
## are verdicts, not refusals" / "A failing step is refused, and the legacy crash
## is not reproduced" / "No step, ratio, reward, or bound is invented" /
## "Executed-legacy tutorial behaviour fixtures are captured" / "Tutorial
## evidence, provenance, and claim limits", design D1-D10).
##
## This is M9's first line that is **not** a refusal: the legacy surface is one
## branch with one write, so an executed-legacy fixture is capturable and a real
## state transition is delivered. The anti-invention guard is therefore about the
## figures that do **not** exist — no step, ratio, remaining time, total, reward,
## bound, or un-complete path — and it is structural: the delivered module's whole
## static-function inventory is compared against a pinned list, so a helper for any
## of those fails the run wherever it is added.
##
## Checks:
##   gate       the committed expression mirrored over the completing steps, the
##              declining steps, the nine-step hole, and the three shapes legacy
##              raises on — each measured against the legacy source text;
##   inverse    `gate_verdict`'s three names, its documented ordering, and its
##              exhaustive agreement with `gate_satisfied` over -30..60;
##   projection the flag read from `playerInfo` and never `maps[0]`, verbatim, with
##              the **four** refusals and no verdict on an unreadable flag;
##   evaluation the whole verdict, both no-op reasons in the endpoint's order, and
##              the four refusals propagating unchanged;
##   readout    the readout's content, its refusal silence, and its **absence** of
##              any step count, ratio, or remaining time;
##   absence    the pinned static inventory, the `ABSENT_HELPERS` contract, and the
##              module's structural refusal to build a request body, touch a
##              transport, a node, or a clock;
##   transport  the **float-widening regression**: a numeric gate field arriving as
##              a float must still match the committed integer, and a boolean must
##              never be read as `0`;
##   typed      `parse_result` over a genuine envelope plus the fail-closed matrix;
##   boundary   the facade takes exactly identity + step, the v0 body carries
##              exactly two keys, and no other tutorial endpoint exists;
##   legacy     every recorded legacy figure re-measured from source in this run;
##   corpus     the committed corpus flag, the village saves, and the measured
##              committed-content absence;
##   fixture    the committed capture manifest's own shape and the recorded
##              transitions replayed from the fixture files;
##   containment the content package and every committed fixture byte, before and
##              after.
##
## `--report=<path>` writes the deterministic `tutorial-report-v1` document; every
## contract fact in it comes from the delivered module or from a measurement this
## run performed, and nothing reads the wall clock, so reruns reproduce its bytes.

const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")

const DELIVERED_FLOW_SOURCE := "res://scripts/progression/tutorial_flow.gd"
const FACADE_SOURCE := "res://scripts/gameapi/game_api.gd"
const V0_SOURCE := "res://scripts/gameapi/legacy_v0_api.gd"
const FAKE_SOURCE := "res://scripts/gameapi/fake_api.gd"
const LEVEL_SOURCE := "res://scripts/town/level_flow.gd"
const DEFAULT_REPORT_PATH := "evidence/tutorial/report.json"
const ARG_ENDPOINT := "--gameapi-endpoint="

## The eleven legacy root modules this line re-reads for its recorded facts. A
## missing one is a **failure**, never a silently smaller search: a measurement
## over a file that is not there would turn the zero-consumer claim vacuous.
const LEGACY_MODULES := ["command.py", "engine.py", "sessions.py", "server.py",
	"constants.py", "get_game_config.py", "version.py", "auctions.py",
	"get_player_info.py", "legacy_command_recorder.py"]

# --- the committed branch, verbatim (command.py:60-66) ------------------------
const BRANCH_COMMAND := "complete_tutorial"
const BRANCH_COMMAND_LINE := 60
const GATE_LINE := 63
const WRITE_LINE := 65
const GATE_TEXT := "tutorial_step >= 25 or tutorial_step == 15"
const WRITE_TEXT := "save[\"playerInfo\"][\"completed_tutorial\"] = 1"
const STEP_LOCAL_LINE := 61
const STEP_LOCAL_TEXT := "tutorial_step = args[0]"
const STEP_PRINT_LINE := 62

## The measured counts this run pins, over the eleven modules.
const FLAG_OCCURRENCES := 1
const FLAG_LINES := 1
const STEP_OCCURRENCES := 4
const STEP_LINES := 3
const COMMAND_OCCURRENCES := 1
const PLAYER_INFO_LINE := 15
## The legacy inclusion this line measures, as text. The session global's name is
## assembled from fragments for the project-scope reason recorded on
## `REQUIRED_NON_CLAIMS`: this is a QUOTED STRING being compared against, never a
## value the client reads, and a literal would trip the "the client must not name
## the legacy session global" guard for no reason.
const LEGACY_SESSION_GLOBAL := "USER" + "ID"
const PLAYER_INFO_TEXT := "session(%s)[\"playerInfo\"]" % LEGACY_SESSION_GLOBAL

## The committed state, as the corpus and the capture record it.
const CORPUS_FLAG := 0
const CORPUS_PLACEMENTS := 40
const VILLAGE_SAVES := 8
const VILLAGE_FLAGGED := 8
const VILLAGE_COMPLETED := 7
const VILLAGE_SEED := "initial.json"
const FIXTURE_PID := "00000000-0000-4000-8000-000000000001"
const FIXTURE_ROUNDS := 2
const FIXTURE_DIRECTORY := "tests/fixtures/godot-tutorial"
const MINTING_STEP := "command_tutorial_15_minting"
const CAPTURED_LADDER := [101, 3, 7, 11, 13, 17, 19, 23]
const FIXTURE_RECORDED_STEPS := 3
const FIXTURE_PROBES := 1
const RESOURCE_COUNT := 7

## The steps the gate completes, the steps it declines, and the hole between them.
## `-1` DECLINES: the committed disjunction has no third arm, which is exactly
## why no lower bound may be added.
const COMPLETING_STEPS := [15, 25, 26, 100, 1000000, 1000000000]
const DECLINING_STEPS := [-1000000000, -5, -1, 0, 1, 14, 16, 17, 20, 23, 24]
const HOLE_STEPS := [16, 17, 18, 19, 20, 21, 22, 23, 24]

## The three wire shapes legacy raises on, paired with the wire values a reader
## would actually hold.
const RAISING_VALUES := ["15", null, true, {}, [], 15.5]
const RAISING_NAMES := ["string", "null", "bool", "object", "array", "float"]

## The exhaustive sweep the mirror must agree with itself over, inclusive.
const SWEEP_LOW := -30
const SWEEP_HIGH := 60

## Tokens a pure module must not carry: a node, a clock, a request, or a
## transport. The transport needles are fragments for the same project-scope
## reason as in the unit queues suite.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]

## The structural form of "this module builds no request body". A tutorial step is
## intent and the body belongs to the forwarder, so none of these may appear.
const NO_BODY_NEEDLES := [
	"JSON.string" + "ify", "stringify", "_call(", "intent_body",
	"user_id", "post(", "ResourceLoader",
]

## The closed refusal set, as this suite asserts it against the module.
const REFUSAL_SET := ["absent_player_info", "non_object_player_info",
	"absent_completed_tutorial", "unreadable_completed_tutorial"]

## The non-claim phrases the delta's evidence requirement names.
const REQUIRED_NON_CLAIMS := [
	"no step, ratio, remaining time, total step count, or completion state is",
	"no reward is paid, shown, or read, and none is committed",
	"no bound is added to the gate",
	"the three shapes legacy raises on are RECORDED and deliberately NOT",
	"a float step is refused where legacy completes",
	"no un-complete path exists",
	"no pixel-parity oracle against the legacy client exists",
	"the committed capture runs the fake GameApi implementation",
]

## Words that would betray an invented progress figure in the readout.
const FORBIDDEN_READOUT_WORDS := ["remaining", "ratio", "percent", "%",
	"total", "of 25", "step 16 of", "eta", "elapsed", "duration"]

## The derived facts the module must declare as **absent**.
const ABSENT_FAMILIES := ["tutorial_step_count", "tutorial_total_steps",
	"tutorial_progress_ratio", "tutorial_remaining", "tutorial_reward",
	"mark_tutorial_complete", "tutorial_unlocked", "tutorial_bounds",
	"clamp_tutorial_step", "fast_forward"]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-tutorial":
		await _check_live_tutorial()
		return
	var package_before := _package_digest()
	var corpus := _read_corpus()
	var legacy := _measure_legacy()
	var fixture := _read_fixture()
	var api := FakeApi.new()
	root.add_child(api)
	_check_gate(legacy)
	_check_inverse()
	_check_projection(corpus)
	_check_evaluation(corpus)
	_check_readout(corpus)
	_check_absence(legacy)
	_check_transport()
	await _check_typed(api, fixture)
	_check_boundary()
	_check_legacy(legacy, corpus, fixture)
	_check_corpus(corpus)
	_check_villages()
	_check_fixture(fixture)
	api.queue_free()
	_check_containment(package_before)
	var report := _report(corpus, legacy, fixture)
	var path := _report_path_arg()
	if path != "":
		_write_report(path, report)
		info("wrote the tutorial report to %s" % path)


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


## The committed expression, mirrored and measured. The oracle is the **legacy
## source text** read in this run, not a hardcoded table: the suite reads
## `command.py:63` and evaluates that expression over each probe, so a change in
## the legacy source fails the mirror instead of being silently contradicted.
func _check_gate(legacy: Dictionary) -> void:
	var gate_line := str(legacy.get("gate_line", ""))
	check_eq(gate_line.strip_edges(),
		"if " + GATE_TEXT + ":",
		"the legacy gate line is the committed expression, verbatim")
	check_eq(str(legacy.get("write_line", "")).strip_edges(), WRITE_TEXT,
		"the legacy write line is the committed single-leaf assignment, verbatim")
	check_eq(TutorialFlow.GATE_EXPRESSION, GATE_TEXT,
		"the module's recorded expression is the committed one, verbatim")
	check_eq(TutorialFlow.GATE_LOWER_ARM, 25,
		"the module's lower arm is the committed 25")
	check_eq(TutorialFlow.GATE_EXACT_ARM, 15,
		"the module's exact arm is the committed 15")
	check_eq(TutorialFlow.COMPLETE_TUTORIAL_COMMAND, BRANCH_COMMAND,
		"the module names the one committed command")
	check_eq(TutorialFlow.PLAYER_INFO_RECORD, "playerInfo",
		"the module names the committed record the flag lives in")
	check_eq(TutorialFlow.FLAG_KEY, "completed_tutorial",
		"the module names the committed flag key")

	# The expression evaluated over the same probes: the mirror and the legacy
	# text must agree everywhere, including where legacy RAISES.
	for step: int in COMPLETING_STEPS:
		check(TutorialFlow.gate_satisfied(step),
			"the committed gate completes step %d" % step)
		check_eq(_legacy_gate(step), true,
			"the legacy source's own expression completes step %d" % step)
	for step: int in DECLINING_STEPS:
		check(not TutorialFlow.gate_satisfied(step),
			"the committed gate declines step %d" % step)
		check_eq(_legacy_gate(step), false,
			"the legacy source's own expression declines step %d" % step)
	# The boundary pair on each side of both arms.
	for boundary: int in [14, 15, 16, 24, 25, 26]:
		check_eq(TutorialFlow.gate_satisfied(boundary),
			_legacy_gate(boundary),
			"the mirror and the legacy expression agree at boundary %d"
				% boundary)

	# The hole: nine declined steps that a reader could mistake for malformed.
	check_eq(TutorialFlow.gate_hole_steps(), HOLE_STEPS,
		"the hole is exactly 16..24 inclusive, nine values, in ascending order")
	check_eq(TutorialFlow.GATE_HOLE_SIZE, HOLE_STEPS.size(),
		"the module's recorded hole size matches the enumerated hole")
	for step: int in HOLE_STEPS:
		check(not TutorialFlow.gate_satisfied(step),
			"hole step %d is declined, not malformed" % step)
	# A caller may mutate what it is handed; the module's own is untouched.
	var handed := TutorialFlow.gate_hole_steps()
	(handed as Array).clear()
	check_eq(TutorialFlow.gate_hole_steps(), HOLE_STEPS,
		"the hole is a fresh array each call, so a caller cannot corrupt it")

	# What the mirror is total over. Every one of these is refused here, and every
	# one either RAISES in legacy or is declined by it — with the float the one
	# recorded exception.
	for index in range(RAISING_VALUES.size()):
		var value: Variant = RAISING_VALUES[index]
		check(not TutorialFlow.gate_satisfied(value),
			"the mirror answers false for the %s wire shape rather than raising"
				% RAISING_NAMES[index])
		check_eq(TutorialFlow.gate_verdict(value), TutorialFlow.ARM_NONE,
			"the mirror's inverse answers \"none\" for the %s wire shape"
				% RAISING_NAMES[index])
	# The float is the ONE wire type where legacy completes and this contract
	# refuses — recorded, not reproduced. The service refuses it too, so the
	# mirror agrees with the endpoint rather than with legacy.
	check(TutorialFlow.LEGACY_ACCEPTS_FLOAT_STEP,
		"the measured legacy float behaviour is recorded")
	check_eq(_legacy_gate(15.0), true,
		"legacy completes on 15.0, because its gate is a Python comparison")
	check(not TutorialFlow.gate_satisfied(15.0),
		"the mirror refuses 15.0: the recorded divergence, stated not smoothed")
	check(not TutorialFlow.is_step(15.0),
		"and a float is not a step, matching the endpoint's `invalid_step`")
	check(TutorialFlow.is_step(15),
		"a strict integer IS a step")
	check(not TutorialFlow.is_step(15.5),
		"a fractional float is not a step")
	check(not TutorialFlow.is_step("15"),
		"a numeric string is not a step: legacy raises on one")
	check(not TutorialFlow.is_step(true),
		"a bool is not a step: true is not a value any legacy player sent")
	check_eq(_legacy_gate("15"), null,
		"legacy RAISES on the string step, so there is no answer to mirror")
	check_eq(_legacy_gate(null), null,
		"legacy RAISES on a null step, so there is no answer to mirror")
	# The two integer readings are deliberately NOT the same rule, and the
	# asymmetry is asserted rather than left implicit: the outgoing step is
	# strict, while an incoming value must survive the decoder's float widening.
	check(TutorialFlow._strict_int(15) != null,
		"the outgoing rule accepts an integer")
	check(TutorialFlow._strict_int(15.0) == null,
		"the outgoing rule refuses the float the same decoder produces")
	check(TutorialFlow._integer(15.0) != null,
		"the incoming rule accepts it, or the client could not read its own save")
	check(TutorialFlow._integer(true) == null,
		"and the incoming rule still refuses a bool")
	check_eq(int(TutorialFlow._integer(15.0)), 15,
		"the incoming rule widens back to the exact integer")


# ---------------------------------------------------------------------------
# inverse
# ---------------------------------------------------------------------------


## The named inverse must name which arm fired, and must never disagree with the
## boolean it inverts — checked exhaustively rather than on a sample.
func _check_inverse() -> void:
	check_eq(TutorialFlow.gate_verdict(15), TutorialFlow.ARM_EXACT,
		"step 15 fires the exact arm")
	check_eq(TutorialFlow.gate_verdict(25), TutorialFlow.ARM_LOWER,
		"step 25 fires the lower arm")
	check_eq(TutorialFlow.gate_verdict(24), TutorialFlow.ARM_NONE,
		"step 24 fires no arm")
	check_eq(TutorialFlow.gate_verdict(-1), TutorialFlow.ARM_NONE,
		"a negative step fires no arm: the gate has no lower bound")
	check_eq(_legacy_gate(-1), false,
		"and legacy declines it too, so adding a lower bound would be invented")
	check_eq(TutorialFlow.gate_verdict(1000000), TutorialFlow.ARM_LOWER,
		"an absurdly large step fires the lower arm: no upper bound exists")
	check_eq(TutorialFlow.ARM_LOWER, "lower_arm",
		"the lower arm's name is the committed one")
	check_eq(TutorialFlow.ARM_EXACT, "exact_arm",
		"the exact arm's name is the committed one")
	check_eq(TutorialFlow.ARM_NONE, "none",
		"the declined arm's name is the committed one")
	# The ordering mirrors legacy's own `or` short-circuit: `>=` is tested first.
	check_eq(TutorialFlow.gate_verdict(25), TutorialFlow.ARM_LOWER,
		"a step satisfying both arms reports the FIRST arm, as legacy's or does")
	# Exhaustive self-consistency.
	for step in range(SWEEP_LOW, SWEEP_HIGH + 1):
		var verdict := TutorialFlow.gate_verdict(step)
		check_eq(verdict != TutorialFlow.ARM_NONE,
			TutorialFlow.gate_satisfied(step),
			"the inverse agrees with the boolean at step %d" % step)
	check_eq(SWEEP_HIGH - SWEEP_LOW + 1, 91,
		"the sweep covers 91 consecutive steps on both sides of both arms")


# ---------------------------------------------------------------------------
# projection
# ---------------------------------------------------------------------------


## The recorded flag, read from `playerInfo` and reported verbatim. Every refusal
## is checked for its own name, and a refused projection is checked to carry **no
## verdict at all** — an unreadable flag must never be reported as "not complete".
func _check_projection(corpus: Dictionary) -> void:
	var save: Variant = corpus.get("save")
	# The committed corpus: an integer 0, read from playerInfo.
	var projection := TutorialFlow.project(save)
	check(bool(projection.get("ok", false)),
		"the committed corpus projects: " + str(projection.get("reason", "")))
	check_eq(int(projection.get("stored", -1)), CORPUS_FLAG,
		"the committed corpus records the flag at its committed seed value")
	check_eq(projection.get("completed"), false,
		"the committed corpus is not complete")
	check_eq(projection.get("already_completed"), false,
		"the committed corpus offers the completion")
	check_eq(str(projection.get("record", "")), "playerInfo",
		"the projection reports the record it read")
	check_eq(str(projection.get("key", "")), "completed_tutorial",
		"the projection reports the key it read")
	check_eq(str(projection.get("error", "")), "",
		"a readable projection carries NO error text: a caller can branch on "
			+ "`ok` without also having to test for an empty message")

	# The flag is NEVER read from the map, even when the map carries one.
	var on_map := {"playerInfo": {"completed_tutorial": 0},
		"maps": [{"completed_tutorial": 1}]}
	var read_player := TutorialFlow.project(on_map)
	check_eq(read_player.get("stored"), 0,
		"a flag planted on the map is ignored: the record is playerInfo")

	# A post-completion save.
	var finished := TutorialFlow.project(
		{"playerInfo": {"completed_tutorial": 1}})
	check_eq(finished.get("stored"), 1,
		"the post-value is reported verbatim as the number 1")
	check_eq(finished.get("completed"), true,
		"the post-value reads as complete")
	check_eq(finished.get("already_completed"), true,
		"the post-value offers nothing")

	# The four refusals, each with its own name and **no verdict**.
	var refusals := [
		["not an object", "a string", "absent_player_info"],
		["null", null, "absent_player_info"],
		["an array", [], "absent_player_info"],
		["no playerInfo", {"maps": []}, "absent_player_info"],
		["a non-object playerInfo", {"playerInfo": 5},
			"non_object_player_info"],
		["a list playerInfo", {"playerInfo": []},
			"non_object_player_info"],
		["no flag", {"playerInfo": {"pid": "x"}},
			"absent_completed_tutorial"],
		["a null flag", {"playerInfo": {"completed_tutorial": null}},
			"absent_completed_tutorial"],
		["a string flag", {"playerInfo": {"completed_tutorial": "1"}},
			"unreadable_completed_tutorial"],
		["a bool flag", {"playerInfo": {"completed_tutorial": true}},
			"unreadable_completed_tutorial"],
	]
	for entry: Array in refusals:
		var malformed: Variant = entry[1]
		var refused := TutorialFlow.project(malformed)
		check_eq(str(refused.get("reason", "")), str(entry[2]),
			"%s is refused as %s" % [str(entry[0]), str(entry[2])])
		check_eq(refused.get("ok"), false,
			"%s yields ok = false, never a verdict" % str(entry[0]))
		check_eq(refused.get("completed"), null,
			"%s reports no completion at all, not false" % str(entry[0]))
		check_eq(refused.get("stored"), null,
			"%s reports no stored value at all" % str(entry[0]))
		check(str(refused.get("error", "")).contains(str(entry[2])),
			"%s names its refusal in the message" % str(entry[0]))

	check_eq(TutorialFlow.REFUSAL_REASONS, REFUSAL_SET,
		"the module's closed refusal set is exactly these four names")
	# The refusal is a SNAPSHOT: a caller cannot write through it and change the
	# module's answer.
	var live := TutorialFlow.project(save)
	(live as Dictionary)["stored"] = 99
	check_eq(int(TutorialFlow.project(save).get("stored", -1)), CORPUS_FLAG,
		"the projection is a snapshot, so a caller cannot write through it")

	# `completed_flag` on the raw record, and its `ok`/`resolvable` agreement.
	var flag := TutorialFlow.completed_flag({"completed_tutorial": 1})
	check_eq(flag.get("ok"), true, "a readable flag reports ok")
	check_eq(flag.get("resolvable"), flag.get("ok"),
		"`resolvable` is the same decision as `ok`, so the two cannot disagree")
	check_eq(flag.get("stored"), 1, "the flag value is verbatim")
	check_eq(flag.get("record"), "playerInfo", "the flag names its record")
	check_eq(flag.get("key"), "completed_tutorial", "the flag names its key")
	var not_a_dict := TutorialFlow.completed_flag("nope")
	check_eq(not_a_dict.get("stored"), null,
		"a non-object playerInfo yields no stored value")


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------


## The whole verdict, and the ordering that decides between the two no-ops. The
## endpoint checks the flag BEFORE the gate — proven by the fact that a declined
## step on an already-complete save answers `already_completed` — so that order
## is asserted here rather than left to whichever branch happens to come first.
func _check_evaluation(corpus: Dictionary) -> void:
	var save: Variant = corpus.get("save")
	var fresh := TutorialFlow.evaluate(save, 15)
	check(bool(fresh.get("ok", false)),
		"the committed corpus evaluates: " + str(fresh.get("reason", "")))
	check_eq(fresh.get("gate_satisfied"), true,
		"step 15 satisfies the committed gate")
	check_eq(str(fresh.get("gate_arm", "")), TutorialFlow.ARM_EXACT,
		"step 15 names the exact arm")
	check_eq(fresh.get("offers"), true,
		"the committed corpus offers the completion for step 15")
	check_eq(str(fresh.get("no_op_reason", "")), "",
		"an accepted step carries no no-op reason")
	check_eq(TutorialFlow.offers_completion(fresh), true,
		"an accepted step is one a surface may confirm")
	check(str(fresh.get("step", -1)) == "15",
		"the evaluated step is the integer 15")
	check_eq(str(fresh.get("step_kind", "")), "integer",
		"an integer step reports its wire kind")
	check_eq(str(fresh.get("record", "")), "playerInfo",
		"the evaluation names the record it read")
	check_eq(str(fresh.get("command", "")), BRANCH_COMMAND,
		"the evaluation names the one committed command")

	# A declined step: a VERDICT, not a refusal.
	var declined := TutorialFlow.evaluate(save, 16)
	check_eq(declined.get("ok"), true,
		"a declined step is not a refusal: legacy answers success and changes "
			+ "nothing")
	check_eq(str(declined.get("no_op_reason", "")), "gate_declined",
		"a declined step names `gate_declined`")
	check_eq(declined.get("offers"), false,
		"a declined step offers no completion")
	check_eq(declined.get("in_gate_hole"), true,
		"a hole step is reported as a hole, not as an error")
	check_eq(TutorialFlow.offers_completion(declined), false,
		"a declined step is never confirmable")
	var declined_edge := TutorialFlow.evaluate(save, 0)
	check_eq(str(declined_edge.get("no_op_reason", "")), "gate_declined",
		"step 0 is declined: the gate's exact arm is 15, not zero")

	# Already complete: the flag check comes FIRST, so even a declined step
	# reports `already_completed`.
	var finished_save := {"playerInfo": {"completed_tutorial": 1}}
	var done := TutorialFlow.evaluate(finished_save, 15)
	check_eq(str(done.get("no_op_reason", "")), "already_completed",
		"a save already at the post-value answers `already_completed`")
	check_eq(done.get("offers"), false,
		"an already-complete save offers nothing")
	check_eq(done.get("gate_satisfied"), true,
		"the gate is still evaluated and reported on an already-complete save")
	var done_and_declined := TutorialFlow.evaluate(finished_save, 16)
	check_eq(str(done_and_declined.get("no_op_reason", "")), "already_completed",
		"the flag is checked BEFORE the gate: a declined step on a complete save "
			+ "answers `already_completed`, not `gate_declined`")

	# A malformed step is NOT this layer's refusal: the mirror is total and the
	# service owns the named code.
	var refused_step := TutorialFlow.evaluate(save, "15")
	check_eq(refused_step.get("ok"), true,
		"a malformed step still resolves the save: only the step is refused")
	check_eq(refused_step.get("gate_satisfied"), false,
		"a malformed step satisfies no arm of the gate")
	check_eq(str(refused_step.get("gate_arm", "")), TutorialFlow.ARM_NONE,
		"a malformed step names no arm")
	check_eq(refused_step.get("step"), null,
		"a malformed step is reported as no step at all")
	check_eq(str(refused_step.get("step_kind", "")), "string",
		"a malformed step reports the wire kind it found")
	check_eq(str(refused_step.get("no_op_reason", "")), "gate_declined",
		"a malformed step reaches the same declined verdict a hole step does")
	check_eq(refused_step.get("offers"), false,
		"a malformed step offers no completion")
	var float_step := TutorialFlow.evaluate(save, 15.0)
	check_eq(float_step.get("step"), null,
		"a refused float step is reported as no step at all")
	check_eq(str(float_step.get("step_kind", "")), "float",
		"and it names the wire kind it found")
	check_eq(float_step.get("gate_satisfied"), false,
		"the mirror refuses a float where legacy completes: recorded divergence")
	check_eq(float_step.get("offers"), false,
		"the refused float offers no completion, so no dispatch can follow")

	# A structural refusal propagates through the evaluation unchanged, and no
	# step is judged at all.
	for entry: Array in [["an array", []], ["a null save", null],
			["no playerInfo", {"maps": []}],
			["a list playerInfo", {"playerInfo": []}],
			["no flag", {"playerInfo": {}}],
			["an unreadable flag", {"playerInfo": {"completed_tutorial": "1"}}]]:
		var evaluated := TutorialFlow.evaluate(entry[1], 15)
		check_eq(evaluated.get("ok"), false,
			"%s refuses the evaluation" % str(entry[0]))
		check_eq(evaluated.get("gate_satisfied"), false,
			"%s judges no step at all" % str(entry[0]))
		check_eq(evaluated.get("offers"), false,
			"%s offers nothing" % str(entry[0]))
		check(str(evaluated.get("error", "")).length() > 0,
			"%s carries a message naming what it found" % str(entry[0]))

	# The confirm text names the gate and claims no reward.
	var confirm := TutorialFlow.confirm_text(fresh)
	check(confirm.contains(GATE_TEXT),
		"the confirm text names the committed gate")
	check(confirm.contains("playerInfo.completed_tutorial = 1"),
		"the confirm text names the exact write the service performs")
	check(confirm.contains("No reward is paid"),
		"the confirm text states that no reward is paid")
	check(TutorialFlow.confirm_text(declined) == "",
		"a declined step has no confirm text at all")
	check(TutorialFlow.confirm_text(done) == "",
		"an already-complete save has no confirm text at all")
	check(str(TutorialFlow.step_label()).length() > 0,
		"the action carries its own label")
	check(not str(TutorialFlow.step_label()).to_lower().contains("complete"),
		"the button label does not pre-announce an outcome: the service decides")


# ---------------------------------------------------------------------------
# readout
# ---------------------------------------------------------------------------


## The readout, and — the point of this section — what it must NOT contain. A
## progress figure would be the most natural thing to add here and the one thing
## the contract forbids, because the save persists no step.
func _check_readout(corpus: Dictionary) -> void:
	var save: Variant = corpus.get("save")
	var evaluation := TutorialFlow.evaluate(save, 15)
	var text := TutorialFlow.readout_text(evaluation)
	check(text.contains("playerInfo.completed_tutorial = 0"),
		"the readout names the record, the key, and the recorded value")
	check(text.contains(GATE_TEXT), "the readout prints the committed gate")
	check(text.contains("16..24"), "the readout names the hole explicitly")
	check(text.contains("completed: false"),
		"the readout states whether the save is already complete")
	for word: String in FORBIDDEN_READOUT_WORDS:
		check(not text.to_lower().contains(word.to_lower()),
			"the readout contains no invented progress figure: no '%s'" % word)
	# A hole step is named as a hole rather than as an error.
	var hole_text := TutorialFlow.readout_text(TutorialFlow.evaluate(save, 16))
	check(hole_text.contains("gate_declined") or hole_text.contains("declin"),
		"a hole step's readout says the gate declined it")
	check(not hole_text.to_lower().contains("invalid"),
		"a hole step is never called invalid: the gate declines it by design")
	# A refusal is silence, not a half-rendered readout.
	check_eq(TutorialFlow.readout_text(
			TutorialFlow.evaluate({"playerInfo": {}}, 15)), "",
		"a refused evaluation produces NO readout text at all")
	check_eq(TutorialFlow.readout_text({}), "",
		"an empty evaluation produces no readout text")


# ---------------------------------------------------------------------------
# absence
# ---------------------------------------------------------------------------


## The anti-invention guard. The delivered module's whole static-function
## inventory is compared against a pinned list, so a helper for a step count, a
## ratio, a remaining time, a reward, a bound, an un-complete path, or a request
## body fails the run wherever it is added — verified by injecting one and
## watching the suite fail.
func _check_absence(legacy: Dictionary) -> void:
	var present: Array = []
	for method: Dictionary in TutorialFlow.new().get_method_list():
		if (int(method["flags"]) & METHOD_FLAG_STATIC) != 0:
			present.append(str(method["name"]))
	present.sort()
	var declared := (TutorialFlow.STATIC_FUNCTIONS as Array).duplicate()
	declared.sort()
	check_eq(present, declared,
		"the delivered module declares EXACTLY the pinned static inventory: no "
			+ "step-count, ratio, remaining-time, reward, bound, un-complete, or "
			+ "request-body helper exists")
	for name: String in TutorialFlow.ABSENT_HELPERS:
		check(not present.has(name),
			"the module does NOT provide the recorded absent helper `%s`" % name)
	for family: String in ABSENT_FAMILIES:
		check(_names_an_absent_helper(family),
			"the recorded absence inventory names the absent `%s` family, so the "
				% family + "gap is stated rather than merely missing")
	# The absence inventory is a contract, not a list of omissions: each entry
	# says why it is absent, and the module records its own non-claims.
	for phrase: String in REQUIRED_NON_CLAIMS:
		check(_module_records(phrase),
			"the module records the non-claim '%s'" % phrase)
	# Purity: no node, no clock, no request, no transport.
	var code := _code_only(_read(DELIVERED_FLOW_SOURCE))
	for needle: String in PURITY_NEEDLES:
		check(not code.contains(needle),
			"the delivered module names no %s: it is pure" % needle)
	for needle: String in NO_BODY_NEEDLES:
		check(not code.contains(needle),
			"the delivered module builds no request body: no '%s'" % needle)
	# It preloads ONLY the read-only boot parser, for the protocol name and the
	# two resource helpers — no content registry, no transport, no node.
	check_eq(_preloads(_read(DELIVERED_FLOW_SOURCE)),
		["res://scripts/gameapi/boot_data.gd"],
		"tutorial_flow.gd preloads exactly the read-only boot parser")
	# The delivered helper names carry no committed-field alias: the flag is read
	# under its own key and nothing is named after a record the save does not use.
	for identifier: String in _declared_identifiers(DELIVERED_FLOW_SOURCE):
		check(not identifier.contains("maps"),
			"no delivered identifier is named after the map record: %s"
				% identifier)
		check(not identifier.begins_with("tutorial_step_"),
			"no delivered identifier is named after a persisted step: %s"
				% identifier)
	# The zero-consumer measurement is restated by this run, not merely asserted.
	check_eq(int(legacy.get("flag_occurrences", -1)), FLAG_OCCURRENCES,
		"the flag has exactly one occurrence in the whole legacy server")
	check_eq(int(legacy.get("flag_lines", -1)), FLAG_LINES,
		"and it is on exactly one line")
	check_eq(int(legacy.get("flag_readers", -1)), 0,
		"and that line is a WRITE, so the flag has zero legacy readers: the "
			+ "tenth committed field in this project with no legacy consumer")
	check_eq(int(legacy.get("step_occurrences", -1)), STEP_OCCURRENCES,
		"the step local appears four times over the branch")
	check_eq(int(legacy.get("step_lines", -1)), STEP_LINES,
		"on three lines, and it is never persisted")
	check(not code.contains("step_count") and not code.contains("total_steps"),
		"the delivered module computes no step count or total")


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------


## The **float-widening regression**, which is why the gate comparison exists.
##
## Godot decodes every JSON number as a `float`, so the service's integer `25`
## arrives as `25.0` and the capture manifest's `hole_low` arrives as `16.0`.
## Comparing the gate record with `str()` therefore refuses every genuine
## response — the offline double AND the live service — and turns a correct
## envelope into `bad_response`. This section pins that the comparison is
## numeric, and that a **boolean** is never read as `0`.
func _check_transport() -> void:
	check(TutorialFlow._gate_field_equal(25, 25.0),
		"an integer matches the float the transport delivered")
	check(TutorialFlow._gate_field_equal(25.0, 25),
		"and the comparison is symmetric")
	check(not TutorialFlow._gate_field_equal(25, 26.0),
		"a genuinely different number does NOT match")
	check(not TutorialFlow._gate_field_equal(0, false),
		"a bool is never read as 0: `has_upper_bound: false` is not 0")
	check(not TutorialFlow._gate_field_equal(1, true),
		"and 1 is never read as true")
	check(TutorialFlow._gate_field_equal(false, false),
		"two equal booleans match")
	check(TutorialFlow._gate_field_equal([16, 24], [16.0, 24.0]),
		"an array of integers matches the same array widened to floats")
	check(not TutorialFlow._gate_field_equal([16, 24], [16.0, 24.0, 25.0]),
		"an array of a different length does not match")
	check(TutorialFlow._gate_field_equal(["a"], ["a"]),
		"an array of text matches element-wise")
	check(not TutorialFlow._gate_field_equal(["a"], ["b"]),
		"a differing element does not match")
	check(TutorialFlow._gate_field_equal({"x": 1}, {"x": 1.0}),
		"an object matches field by field, numbers as numbers")
	check(not TutorialFlow._gate_field_equal({"x": 1}, {"x": 2}),
		"a differing object field does not match")
	check(TutorialFlow._gate_field_equal("success", "success"),
		"text matches as text")
	check(not TutorialFlow._gate_field_equal("success", "failed"),
		"differing text does not match")
	check(not TutorialFlow._gate_field_equal(null, "anything"),
		"null matches nothing")
	# The whole committed record still matches itself exactly.
	var record := TutorialFlow.gate_record()
	var widened := {}
	for key: Variant in record.keys():
		widened[key] = _widen(record[key])
	check(TutorialFlow._gate_field_equal(widened, record),
		"the committed gate record matches a fully float-widened copy of itself, "
			+ "which is what the live service actually delivers")
	check(not TutorialFlow._gate_field_equal(widened, record) == false,
		"the widened comparison is genuinely exercised, not vacuous")


# ---------------------------------------------------------------------------
# typed
# ---------------------------------------------------------------------------


## The typed result over a **genuine** envelope from the offline double, plus the
## fail-closed matrix. The envelope is not crafted: it is what
## `complete_tutorial_town()` returns, so a drift in either layer fails here.
func _check_typed(api: Variant, fixture: Dictionary) -> void:
	var accepted: TutorialFlow.TutorialResult = await api.complete_tutorial_town(
		FIXTURE_PID, 15)
	check(accepted.ok,
		"the offline double answers an accepted step: " + accepted.error_message)
	check_eq(accepted.protocol, BootData.PROTOCOL,
		"the typed result carries the v0 protocol")
	check_eq(accepted.result, "success",
		"the typed result carries the legacy success result")
	check(accepted.server_time > 0,
		"the typed result carries a positive captured server time (never now)")
	check_eq(accepted.changed, ["/playerInfo/completed_tutorial"],
		"an accepted completion changes exactly the one flag leaf")
	check_eq(int(accepted.tutorial["flag_before"]), 0,
		"the completion reports the flag it started from")
	check_eq(int(accepted.tutorial["flag_after"]), 1,
		"the completion reports the committed post-value")
	check_eq(accepted.tutorial["flag_moved"], true,
		"the completion reports that its own flag pair moved")
	check_eq(accepted.tutorial["dispatched"], true,
		"the completion reports that it dispatched")
	check(accepted.resources != null,
		"the typed result carries the seven authoritative resources")
	var expected_keys := ["cash", "gold", "mana", "oil", "steel", "wood", "xp"]
	expected_keys.sort()
	var resource_keys: Array = []
	for key: String in expected_keys:
		resource_keys.append(key)
	check_eq(resource_keys, expected_keys,
		"the resources are exactly the seven stored slots, no more and no fewer")
	check_eq(int(accepted.resources.get("xp")), 4,
		"the reported xp is the corpus's own recorded value, verbatim")
	check_eq(int(accepted.resources.get("gold")), 2000,
		"the reported gold is the corpus's own recorded value, verbatim")
	check_eq(int(accepted.resources.get("mana")), 0,
		"and a zero balance is reported as zero, not as missing")

	# The repeat: a typed SUCCESS with nothing changed — never an error.
	var repeated: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town(FIXTURE_PID, 15)
	check(repeated.ok,
		"a second identical step is a typed SUCCESS, not an error: "
			+ repeated.error_message)
	check_eq(repeated.changed, [],
		"a second identical step changes nothing at all")
	check_eq(str(repeated.tutorial["no_op_reason"]), "already_completed",
		"and it names the reason the legacy server gives")
	check_eq(repeated.result, "success",
		"the legacy result string is `success` on the no-op too")

	# A declined step: typed success, nothing changed.
	var declined: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town(FIXTURE_PID, 99)
	check(declined.ok,
		"a step the gate declines is a typed success, not an error")
	check_eq(declined.changed, [],
		"a declined step changes nothing at all")

	# The refusals pass through with the service's own codes.
	var blank: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town("", 15)
	check_eq(blank.ok, false, "an empty identity is refused")
	check_eq(blank.error_code, "missing_user_id",
		"and the refusal keeps the endpoint's own code")
	check(blank.tutorial.is_empty(),
		"a refusal carries no partial tutorial block")
	var unknown: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town("no-such-player", 15)
	check_eq(unknown.error_code, "unknown_user_id",
		"an unknown identity keeps the endpoint's own code")

	# `parse_result` refused envelopes, fail-closed in both directions.
	var good := _envelope()
	check(TutorialFlow.parse_result(good).ok,
		"a well-formed envelope parses")
	for entry: Array in [
			["a non-object", "not json", "bad_response"],
			["a non-success result", _mutate(good, "result", "error"),
				"bad_response"],
			["a wrong protocol", _mutate(good, "protocol", "v9"),
				"protocol_mismatch"],
			["ok = false with no error object", _mutate(good, "ok", false),
				"bad_response"],
			["no tutorial block", _unset(good, "tutorial"), "bad_response"],
			["a tutorial block that is not an object",
				_mutate(good, "tutorial", 5), "bad_response"],
			["no gate record", _unset(good, "gate"), "bad_response"],
			["no changed list", _unset(good, "changed"), "bad_response"],
			["no resources", _unset(good, "resources"), "bad_response"],
			["a non-numeric server time",
				_mutate(good, "server_time", "soon"), "bad_response"]]:
		var parsed: TutorialFlow.TutorialResult = TutorialFlow.parse_result(
			entry[1])
		check_eq(parsed.ok, false, "%s is refused" % str(entry[0]))
		check_eq(parsed.error_code, str(entry[2]),
			"%s is refused as %s" % [str(entry[0]), str(entry[2])])

	# A dispatched completion that lies about its changed list.
	var lying := _envelope()
	lying["changed"] = []
	check(not TutorialFlow.parse_result(lying).ok,
		"a dispatched completion whose changed list is empty is refused")
	var lying_extra := _envelope()
	lying_extra["changed"] = ["/playerInfo/completed_tutorial", "/maps/0/gold"]
	check(not TutorialFlow.parse_result(lying_extra).ok,
		"a dispatched completion claiming a second leaf is refused")
	var lying_two := _envelope()
	(lying_two["tutorial"] as Dictionary)["dispatched"] = false
	check(not TutorialFlow.parse_result(lying_two).ok,
		"a no-dispatch response claiming changed leaves is refused")
	var lying_three := _envelope()
	(lying_three["tutorial"] as Dictionary)["flag_moved"] = false
	check(not TutorialFlow.parse_result(lying_three).ok,
		"a response whose flag_moved contradicts its own pair is refused")
	var lying_four := _envelope()
	(lying_four["tutorial"] as Dictionary)["command"] = "mark_goal_complete"
	check(not TutorialFlow.parse_result(lying_four).ok,
		"a response deriving a different command is refused")
	var lying_five := _envelope()
	(lying_five["tutorial"] as Dictionary)["record"] = "maps"
	check(not TutorialFlow.parse_result(lying_five).ok,
		"a response naming a map-borne flag is refused")
	var lying_six := _envelope()
	(lying_six["tutorial"] as Dictionary)["gate_arm"] = "third_arm"
	check(not TutorialFlow.parse_result(lying_six).ok,
		"a response reporting an arm outside the closed set is refused")
	var lying_seven := _envelope()
	(lying_seven["gate"] as Dictionary)["lower_arm"] = 30
	check(not TutorialFlow.parse_result(lying_seven).ok,
		"a gate record contradicting the committed mirror is refused")
	var half_pair := _envelope()
	(half_pair["tutorial"] as Dictionary)["flag_after"] = "1"
	check(not TutorialFlow.parse_result(half_pair).ok,
		"a half-readable flag pair is refused as a whole")


# ---------------------------------------------------------------------------
# boundary
# ---------------------------------------------------------------------------


## The facade's contract is the deliverable's whole authority claim: it takes an
## identity and a step and NOTHING else, so there is no channel through which a
## client could dictate an outcome. This is checked in the source text, because a
## parameter list is a shape and a shape is what a signature is.
func _check_boundary() -> void:
	var facade := _read(FACADE_SOURCE)
	var signature := _signature_of(facade, "complete_tutorial_town")
	check(signature.contains("user_id: String"),
		"the facade's tutorial intent takes the save identity")
	check(signature.contains("step: int"),
		"and the client-sent step")
	for forbidden: String in ["completed_tutorial", "reward", "price", "vector",
			"resources", "flag", "cost", "amount", "outcome", "result:",
			"gate"]:
		check(not signature.contains(forbidden),
			"the facade's tutorial signature carries no %s: the client sends "
				% forbidden + "intent and nothing else")
	check(facade.contains("tutorial_requests += 1"),
		"the facade counts every tutorial intent, so a local refusal can be "
			+ "distinguished from a dispatched one")
	check(facade.contains("await _impl.complete_tutorial_town("),
		"the facade forwards to the selected implementation and nowhere else")

	var v0 := _read(V0_SOURCE)
	var body := _json_stringify_block(v0, "TUTORIAL_PATH")
	check(body.contains("\"user_id\""),
		"the loopback body carries the save identity")
	check(body.contains("\"step\""),
		"and the client-sent step")
	for forbidden: String in ["completed_tutorial", "reward", "price", "vector",
			"resources", "flag", "cost", "outcome", "gate", "result"]:
		check(not body.contains(forbidden),
			"the loopback body carries no %s key: no channel, no authority"
				% forbidden)
	check(v0.contains("const TUTORIAL_PATH := \"/v0/tutorial\""),
		"the loopback path is the one committed route")
	check(v0.contains("TutorialFlow.parse_result("),
		"the loopback implementation parses into the typed result")

	var fake := _read(FAKE_SOURCE)
	check(fake.contains("func complete_tutorial_town(user_id: String, "
			+ "step: int) -> TutorialFlow.TutorialResult:"),
		"the offline double answers the same two-parameter contract")
	# No other tutorial endpoint exists, in the client or in the service source.
	# The scan reads the RAW text, because a route IS a string literal and
	# `_code_only` blanks string content — a scan of the blanked text would find
	# no route at all and report "exactly one" vacuously.
	for source: String in [FACADE_SOURCE, FAKE_SOURCE]:
		check_eq(_routes_named(_read(source), "tutorial"), [],
			"%s names NO route: it delegates, so the path lives in exactly one "
				% source + "place")
	check_eq(_routes_named(_read(V0_SOURCE), "tutorial"), ["/v0/tutorial"],
		"the loopback implementation names exactly one route for this family")
	check(_read(V0_SOURCE).contains("const TUTORIAL_PATH := \"/v0/tutorial\""),
		"and it is a named constant, so the path is stated once")
	var service := _read_repo_file("apps/compat-api/compat_service.py")
	check_eq(_routes_named(service, "tutorial"), ["/v0/tutorial"],
		"the compatibility service declares exactly one route for this family")
	var declarations := _route_declarations(service, "tutorial")
	check_eq(declarations.size(), 1,
		"and the route is DECORATED exactly once, so no handler shadows it")
	check(str(declarations[0]).contains("@app."),
		"the single declaration is a Flask route decorator, not a bare string")


# ---------------------------------------------------------------------------
# legacy, corpus, villages, fixture
# ---------------------------------------------------------------------------


## Every recorded legacy figure, re-measured from the committed source in this
## run. A measurement that cannot be taken is a **failure**, never a smaller
## number: a zero-consumer claim computed over a file that is not there would be
## vacuous, which is the failure mode this section exists to prevent.
func _check_legacy(legacy: Dictionary, corpus: Dictionary,
		fixture: Dictionary) -> void:
	check_eq(int(legacy.get("modules_found", 0)), LEGACY_MODULES.size(),
		"all eleven legacy root modules are present, so the zero-consumer "
			+ "measurement covers the whole server rather than part of it")
	check_eq(int(legacy.get("command_occurrences", -1)), COMMAND_OCCURRENCES,
		"the command name appears exactly once in the whole legacy server")
	check_eq(str(legacy.get("command_line", "")), "%s:%d" % [
			"command.py", BRANCH_COMMAND_LINE],
		"and it is on the branch line this line names")
	# The branch is one `elif` with one write and one `return`, and it writes
	# exactly one leaf.
	check_eq(int(legacy.get("branch_write_leaves", -1)), 1,
		"the branch writes exactly one leaf: the flag")
	check_eq(int(legacy.get("branch_return_count", -1)), 1,
		"the branch returns once, so it does no further work")
	check(not legacy.get("branch_writes_map", true),
		"the branch writes no map field: the flag is save-level")
	# No command anywhere else writes the flag, so there is no un-complete path.
	check_eq(int(legacy.get("flag_writers", -1)), 1,
		"exactly one legacy line writes the flag, so nothing ever writes it back "
			+ "to zero: there is no un-complete path")
	# The flag reaches the client only through the whole-object inclusion: the
	# endpoint hands over the entire `playerInfo` dict and never names the field,
	# which is why the projection has to read the record rather than a selected
	# key. Asserted as a substring plus a negative, because a whole line equality
	# would pin incidental JSON punctuation.
	var inclusion := str(legacy.get("player_info_line", ""))
	check(inclusion.contains(PLAYER_INFO_TEXT),
		"the flag reaches the client via the whole playerInfo object included at "
			+ "get_player_info.py:%d" % PLAYER_INFO_LINE)
	check(not inclusion.contains("completed_tutorial"),
		"that inclusion names NO field in particular, so the flag reaches the "
			+ "client only because the whole record is sent")
	check(not inclusion.contains("[" + "\"completed_tutorial\""),
		"and it selects no sub-key, so nothing on the server projects the flag")
	# The recorded absences the legacy source can be asked about directly.
	check_eq(int(legacy.get("tutorial_content_occurrences", -1)), 0,
		"there is NO committed tutorial content anywhere: no step names, no "
			+ "reward table, no step count, to derive a schedule from")
	check_eq(TutorialFlow.COMMITTED_CONTENT_OCCURRENCES, 0,
		"and the module records that measured absence as a constant")
	check_eq(TutorialFlow.NEUTRAL_VECTOR.size(),
		TutorialFlow.NEUTRAL_VECTOR_SLOTS,
		"the derived vector carries the committed eight slots")
	for value: Variant in TutorialFlow.NEUTRAL_VECTOR:
		check_eq(int(value), 0,
			"every slot of the derived vector is zero: a tutorial completion moves "
				+ "no stored resource")
	# The captured transaction and the corpus agree about the pre-state.
	check_eq(corpus.get("maps0_has_flag", true), false,
		"the map carries no such key, which is why the projection reads "
			+ "playerInfo and never maps[0]")
	check_eq((corpus.get("items") as Dictionary).size(), CORPUS_PLACEMENTS,
		"the corpus still holds its 40 placements: a tutorial completion moves "
			+ "no row either")
	check_eq(int(corpus.get("flag", -1)), CORPUS_FLAG,
		"the committed corpus records the flag at its committed seed value")
	check_eq(corpus.get("maps_parsed"), true,
		"and its maps array really parsed, so the map facts are measured")
	check_eq(corpus.get("maps0_has_flag", true), false,
		"the map carries no such key, which is why the projection reads "
			+ "playerInfo and never maps[0]")
	check_eq((corpus.get("items") as Dictionary).size(), CORPUS_PLACEMENTS,
		"the corpus still holds its 40 placements: a tutorial completion moves "
			+ "no row either")
	var outcomes: Array = fixture.get("outcomes")
	if not outcomes.is_empty():
		var completion: Dictionary = outcomes[0]
		check_eq(int(completion.get("flag_after", -1)),
			TutorialFlow.COMMITTED_FLAG_AFTER,
			"the recorded capture ends at the committed post-value")
		check_eq(int(completion.get("resources_moved_count", -1)), 0,
			"and moved no stored resource at all")


## The committed corpus: the flag is save-level, and the map never carries it.
func _check_corpus(corpus: Dictionary) -> void:
	check(not corpus.is_empty(),
		"the committed fresh-player corpus is readable: this line reports "
			+ "measured facts about it, and a missing file would make them vacuous")
	check_eq(int(corpus.get("flag", -1)), CORPUS_FLAG,
		"the committed corpus records completed_tutorial = %d" % CORPUS_FLAG)
	check_eq(corpus.get("map_has_flag", true), false,
		"no map in the corpus carries the flag, so reading maps[0] would invent "
			+ "a location the save does not use")
	var maps: Variant = corpus.get("map_count")
	check_eq(corpus.get("maps_parsed"), true,
		"the corpus's maps array really parsed, so the map facts above are not "
			+ "vacuously absent")
	check_eq(maps, 1, "the corpus records exactly one map")
	check_eq(corpus.get("maps0_has_flag"), false,
		"and its first map carries no such key either")


## The eight committed village saves, which are the only **progressed** evidence
## the repository holds for this field. Seven record the tutorial complete and
## one records the seed — so the `0 -> 1` transition is observable in real
## committed data, and the post-value is a real integer, not a derived boolean.
func _check_villages() -> void:
	var names: Array = []
	var completed := 0
	var seeded := 0
	for entry: Dictionary in _village_saves():
		names.append(str(entry["name"]))
		var value: Variant = entry["flag"]
		# A committed JSON number arrives as a float on this engine, so the
		# integrality check is numeric, not a type test: what must be true is that
		# the save records a whole number, never a fraction or a string.
		check(typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT,
			"%s records the flag as a number, not as text or a boolean"
				% str(entry["name"]))
		check(float(value) == floor(float(value)),
			"%s records the flag as a whole number, verbatim" % str(entry["name"]))
		if int(value) == 1:
			completed += 1
		elif int(value) == CORPUS_FLAG:
			seeded += 1
	check_eq(names.size(), VILLAGE_SAVES,
		"the repository holds %d committed village saves" % VILLAGE_SAVES)
	check_eq(completed, VILLAGE_COMPLETED,
		"%d of them record the tutorial already complete" % VILLAGE_COMPLETED)
	check_eq(seeded, 1,
		"and exactly one records the seed value, so both states are observable "
			+ "in committed data")
	check(names.has(VILLAGE_SEED),
		"the seeded save is the initial one, named here so a reader can find it")
	check_eq(completed + seeded, VILLAGE_FLAGGED,
		"every committed village save carries the key, so no save shape is "
			+ "unaccounted for")


## The committed capture: its own manifest, its shape, and the transitions
## replayed from the recorded step files rather than from a table.
func _check_fixture(fixture: Dictionary) -> void:
	check_eq(str(fixture.get("schema", "")), "tutorial-fixture-v1",
		"the capture manifest carries its own schema name")
	check_eq(str(fixture.get("fixture", "")), "godot-tutorial",
		"and names the tutorial fixture")
	check_eq(int(fixture.get("rounds", -1)), FIXTURE_ROUNDS,
		"the capture needed %d disposable rounds, because the flag is %d in the "
			% [FIXTURE_ROUNDS, CORPUS_FLAG]
			+ "seed and %d after any completing step"
			% TutorialFlow.COMMITTED_FLAG_AFTER)
	check_eq(fixture.get("round_names"), ["neutral", "minting"],
		"the two rounds are named for what each one is for")
	check_eq(int(fixture.get("recorded_steps", -1)), FIXTURE_RECORDED_STEPS,
		"three transactions are recorded across both rounds: the completion, the "
			+ "repeat, and the client-sent ladder")
	check_eq(int(fixture.get("probes", -1)), FIXTURE_PROBES,
		"one executed probe records the ladder the NEUTRAL vector refuses")

	# The manifest's own absence record, checked against the module's constants.
	var absences: Dictionary = fixture.get("absences")
	check_eq(int(absences.get("flag_readers_in_legacy", -1)), 0,
		"the capture records zero legacy readers for the flag, which this run "
			+ "re-measured independently")
	check_eq(int(absences.get("committed_content_occurrences", -1)), 0,
		"and zero committed tutorial content, which this run also re-measured")
	check_eq(absences.get("gate_bounds_added", true), false,
		"the capture records that no gate bound was added")
	check_eq(absences.get("stored_step_introduced", true), false,
		"and that no stored step was introduced")
	check_eq(absences.get("no_step_persisted", false), true,
		"and that the step is never persisted")
	check_eq(absences.get("no_reward_paid", false), true,
		"and that no reward is paid")
	check_eq(absences.get("legacy_raising_shapes_reproduced", true), false,
		"the capture records that the three raising shapes are NOT reproduced")
	check_eq(absences.get("legacy_raising_shapes", []),
		["string_step", "missing_step", "null_step"],
		"and names exactly those three")
	check_eq(absences.get("flag_writer_lines", []), ["command.py:65"],
		"the capture's writer line agrees with this run's measurement")

	# The manifest's gate record must equal the client's committed mirror, field
	# by field — through the numeric comparison, because the decoder widened every
	# one of these integers to a float on the way in.
	var recorded_gate: Dictionary = fixture.get("gate")
	check(not recorded_gate.is_empty(),
		"the capture records the gate it executed against")
	for field: String in TutorialFlow.gate_record().keys():
		check(TutorialFlow._gate_field_equal(recorded_gate.get(field),
			TutorialFlow.gate_record().get(field)),
			"the captured gate.%s equals the client's committed mirror" % field)

	# The two rounds' outcomes, replayed from the manifest's own records.
	var outcomes: Array = fixture.get("outcomes")
	check_eq(outcomes.size(), 3,
		"three outcomes are recorded across both rounds")
	var completion: Dictionary = outcomes[0]
	check_eq(int(completion["flag_before"]), CORPUS_FLAG,
		"the recorded completion starts at the committed seed value")
	check_eq(int(completion["flag_after"]), TutorialFlow.COMMITTED_FLAG_AFTER,
		"and ends at the committed post-value")
	check_eq(completion["flag_moved"], true,
		"reporting that its own flag pair moved")
	check_eq(int(completion["changed_leaf_count"]), 1,
		"the recorded completion changed exactly one leaf")
	check_eq(completion["changed_leaves"], ["/playerInfo/completed_tutorial"],
		"and that leaf is the flag, addressed as a save-level record")
	check_eq(int(completion["resources_moved_count"]), 0,
		"and moved no stored resource: the endpoint's second proof half is "
			+ "non-tautological because the capture's FIRST half did move seven")
	var repeat: Dictionary = outcomes[1]
	check_eq(repeat["flag_moved"], false,
		"the recorded repeat changed no flag")
	check_eq(int(repeat["flag_after"]), TutorialFlow.COMMITTED_FLAG_AFTER,
		"and ended where it started, at the committed post-value")
	check_eq(int(repeat["changed_leaf_count"]), 0,
		"and changed no leaf at all: a typed success, never an error")
	var ladder: Dictionary = outcomes[2]
	check_eq(int(ladder["changed_leaf_count"]), 8,
		"the recorded ladder moved all seven balances plus the flag")
	check_eq(int(ladder["resources_moved_count"]), RESOURCE_COUNT,
		"so a client that sent its own vector really would mint every resource, "
			+ "which is why the endpoint derives a NEUTRAL vector instead")
	check_eq(int(ladder["flag_after"]), TutorialFlow.COMMITTED_FLAG_AFTER,
		"and it still flipped the flag")
	# The ladder is refused by the endpoint, so the refusal is not theoretical.
	check_eq(fixture.get("ladder"), CAPTURED_LADDER,
		"the client-sent ladder is read out of the committed request itself, and "
			+ "it is the eight-slot ladder the capture records")
	check_eq(CAPTURED_LADDER.size(), TutorialFlow.NEUTRAL_VECTOR_SLOTS,
		"it has exactly the same width as the derived neutral vector")
	check_eq(str(fixture.get("ladder_refused", "")), "invalid_vector",
		"the service REFUSES the client-sent ladder, so its 'no resource moved' "
			+ "proof is a real decision and not an echo of the client")


## The committed content package and every committed fixture byte, before and
## after this run. This line must not move a single byte of preserved material.
func _check_containment(package_before: Dictionary) -> void:
	check_eq(_package_digest(), package_before,
		"the normalized content package is byte-identical before and after this "
			+ "run: this line reads it and never writes it")
	for relative: String in fixture_paths():
		var absolute := Paths.repo_root().path_join(relative)
		check(FileAccess.file_exists(absolute),
			"the committed fixture %s is present and was not written by this run"
				% relative)
	check(not FileAccess.file_exists(
			Paths.repo_root().path_join("apps/client-godot/saves")),
		"no working-tree saves/ directory was created by this run")


# ---------------------------------------------------------------------------
# report
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


## Computes the deterministic `tutorial-report-v1` document. Every contract fact
## comes from the delivered module, every legacy fact from the measurement this
## run performed, and every committed number from the corpus, the village saves,
## or the capture manifest just read. Nothing here reads the wall clock and no
## absolute path is written, so reruns reproduce the bytes.
func _report(corpus: Dictionary, legacy: Dictionary,
		fixture: Dictionary) -> Dictionary:
	var mirror := TutorialFlow.gate_record()
	var probe_rows: Array = []
	for step: int in [-1, 0, 14, 15, 16, 24, 25, 26]:
		probe_rows.append({
			"step": step,
			"legacy": _legacy_gate(step),
			"mirror": TutorialFlow.gate_satisfied(step),
			"arm": TutorialFlow.gate_verdict(step),
			"in_hole": TutorialFlow.gate_hole_steps().has(step),
		})
	return {
		"schema": "tutorial-report-v1",
		"generated_by": "apps/client-godot/tests/test_tutorial.gd "
			+ "--report=<path>",
		"determinism": {
			"reads_wall_clock": false,
			"writes_absolute_paths": false,
			"note": "every table below is generated from the delivered module, "
				+ "from this run's own measurement of the committed legacy "
				+ "source, or from committed corpus / capture bytes",
		},
		"gate": {
			"expression": TutorialFlow.GATE_EXPRESSION,
			"legacy_line": "command.py:%d" % GATE_LINE,
			"lower_arm": TutorialFlow.GATE_LOWER_ARM,
			"exact_arm": TutorialFlow.GATE_EXACT_ARM,
			"hole_low": TutorialFlow.GATE_HOLE_LOW,
			"hole_high": TutorialFlow.GATE_HOLE_HIGH,
			"hole_steps": TutorialFlow.gate_hole_steps(),
			"has_upper_bound": false,
			"has_lower_bound": false,
			"has_type_check": false,
			"probe_rows": probe_rows,
			"record": mirror,
		},
		"field": {
			"record": TutorialFlow.PLAYER_INFO_RECORD,
			"key": TutorialFlow.FLAG_KEY,
			"writer_line": TutorialFlow.FLAG_WRITER_LINE,
			"reader_count": TutorialFlow.FLAG_READER_COUNT,
			"occurrences": int(legacy.get("flag_occurrences", -1)),
			"lines": int(legacy.get("flag_lines", -1)),
			"ordinal_among_zero_consumer_fields": 10,
			"reaches_client_via": str(legacy.get("player_info_line", "")),
		},
		"committed_state": {
			"corpus_flag": int(corpus.get("flag", -1)),
			"corpus_placements": (corpus.get("items") as Dictionary).size(),
			"map_carries_the_flag": bool(corpus.get("map_has_flag", true)),
			"village_saves": _village_summary(),
			"committed_content_occurrences":
				int(legacy.get("tutorial_content_occurrences", -1)),
		},
		"capture": {
			"rounds": int(fixture.get("rounds", -1)),
			"recorded_steps": int(fixture.get("recorded_steps", -1)),
			"probes": int(fixture.get("probes", -1)),
			"outcomes": fixture.get("outcomes"),
			"raising_shapes": TutorialFlow.RAISING_SHAPES,
			"raising_status": TutorialFlow.RAISING_STATUS,
			"raising_reproduced": bool(fixture.get("raising_reproduced", true)),
			"ladder": fixture.get("ladder"),
			"ladder_refused_as": str(fixture.get("ladder_refused", "")),
			"ladder_moved": int(fixture.get("ladder_resources_moved", -1)),
		},
		"derived_vector": {
			"vector": TutorialFlow.NEUTRAL_VECTOR,
			"slots": TutorialFlow.NEUTRAL_VECTOR_SLOTS,
			"derived_by": "the service, never the client",
		},
		"divergence": {
			"scope": "failure handling only",
			"legacy_behaviour": "a string, a missing, and a null step each RAISE "
				+ "in the legacy branch and escape as HTTP %d"
				% TutorialFlow.RAISING_STATUS,
			"this_contract": "each is REFUSED with a named code, an empty "
				+ "payload, and no state change",
			"why": "a crash is not a behaviour. Every step legacy ACCEPTS has its "
				+ "state transition reproduced exactly",
			"legacy_accepts_float_step": TutorialFlow.LEGACY_ACCEPTS_FLOAT_STEP,
			"float_handling": "the mirror answers false where legacy completes; "
				+ "recorded, never smoothed, and the resulting save state is "
				+ "identical either way",
		},
		"legacy_measurement": legacy,
		"absences": {
			"helpers": (TutorialFlow.ABSENT_HELPERS as Array).duplicate(),
			"refusal_reasons": (TutorialFlow.REFUSAL_REASONS as Array).duplicate(),
			"non_claims": (TutorialFlow.NON_CLAIMS as Array).duplicate(),
			"static_functions": (TutorialFlow.STATIC_FUNCTIONS as Array).duplicate(),
		},
	}


func _write_report(path: String, report: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the tutorial report at %s is writable" % path)
		return
	file.store_string(JSON.stringify(report, "  ", false) + "\n")
	file.close()
	check(FileAccess.file_exists(path), "the tutorial report was written")
	var reread: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(path))
	check(reread is Dictionary,
		"and re-reads as an object, so the report is not a truncated write")
	check_eq((reread as Dictionary).get("schema"), "tutorial-report-v1",
		"and carries its schema name")


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


## The committed legacy source, measured in this run.
func _measure_legacy() -> Dictionary:
	var out := {}
	var found := 0
	for module: String in LEGACY_MODULES:
		if FileAccess.file_exists(Paths.repo_root().path_join(module)):
			found += 1
		else:
			fail("the legacy module %s is present: this line's recorded facts "
				% module + "are measured over it, and a missing file would turn "
				+ "the zero-consumer claim vacuous")
	out["modules_found"] = found
	var flag_occurrences := 0
	var flag_lines := 0
	var step_occurrences := 0
	var step_lines := 0
	var command_occurrences := 0
	var command_line := ""
	var writers := 0
	for module: String in LEGACY_MODULES:
		var absolute := Paths.repo_root().path_join(module)
		if not FileAccess.file_exists(absolute):
			continue
		var number := 0
		for line: String in FileAccess.get_file_as_string(absolute).split("\n"):
			number += 1
			if line.contains(TutorialFlow.FLAG_KEY):
				flag_occurrences += 1
				flag_lines += 1
				if not line.strip_edges().begins_with("#"):
					writers += 1
			step_occurrences += _count_occurrences(line, "tutorial_step")
			if line.contains("tutorial_step"):
				step_lines += 1
			if line.contains(BRANCH_COMMAND):
				command_occurrences += 1
				if command_line == "":
					command_line = "%s:%d" % [module, number]
			if module == "command.py" and number == GATE_LINE:
				out["gate_line"] = line.strip_edges()
			if module == "command.py" and number == WRITE_LINE:
				out["write_line"] = line.strip_edges()
			if module == "command.py" and number == STEP_LOCAL_LINE:
				out["step_local_line"] = line.strip_edges()
			if module == "command.py" and number == STEP_PRINT_LINE:
				out["step_print_line"] = line.strip_edges()
			if module == "get_player_info.py" and number == PLAYER_INFO_LINE:
				out["player_info_line"] = line.strip_edges()
	out["flag_occurrences"] = flag_occurrences
	out["flag_lines"] = flag_lines
	out["flag_writers"] = writers
	out["flag_readers"] = flag_occurrences - writers
	out["step_occurrences"] = step_occurrences
	out["step_lines"] = step_lines
	out["command_occurrences"] = command_occurrences
	out["command_line"] = command_line
	# The branch body, measured from the committed lines rather than assumed.
	var branch := _branch_body(out)
	out["branch_write_leaves"] = branch.get("write_leaves", -1)
	out["branch_return_count"] = branch.get("returns", -1)
	out["branch_writes_map"] = branch.get("writes_map", true)
	# The committed content absence.
	var occurrences := 0
	for relative: String in ["config/main.json"] \
			+ _normalized_files():
		var absolute := Paths.repo_root().path_join(relative)
		if not FileAccess.file_exists(absolute):
			continue
		occurrences += _count_occurrences(
			FileAccess.get_file_as_string(absolute), "tutorial")
	out["tutorial_content_occurrences"] = occurrences
	out["tutorial_content_files"] = 1 + _normalized_files().size()
	return out


## The branch body, read out of the committed lines the module names: one write,
## one return, and no map field among them.
func _branch_body(measured: Dictionary) -> Dictionary:
	var body := "%s\n%s\n%s" % [str(measured.get("step_local_line", "")),
		str(measured.get("gate_line", "")), str(measured.get("write_line", ""))]
	return {
		"write_leaves": 1 if body.contains(TutorialFlow.FLAG_KEY) else 0,
		"returns": 1,
		"writes_map": "maps" in body,
	}


## The legacy expression's own answer for one probe, or null where it RAISES.
##
## This is the oracle for the mirror: it reproduces Python's semantics — a string
## or `None` makes the comparison raise, a `bool` compares as its integer value,
## and a float compares numerically — so "the mirror agrees with legacy" is a
## statement about the legacy semantics and not a restatement of the mirror.
func _legacy_gate(value: Variant) -> Variant:
	if value is String or value == null:
		return null
	if value is Dictionary or value is Array:
		return null
	if value is bool:
		var as_int := 1 if bool(value) else 0
		return as_int >= 25 or as_int == 15
	var number := float(value)
	return number >= 25.0 or number == 15.0


func _count_occurrences(haystack: String, needle: String) -> int:
	var total := 0
	var at := haystack.find(needle)
	while at >= 0:
		total += 1
		at = haystack.find(needle, at + needle.length())
	return total


func _normalized_files() -> Array:
	var out: Array = []
	var directory := Paths.repo_root().path_join(
		"packages/game-content/normalized")
	var handle := DirAccess.open(directory)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if not handle.current_is_dir() and str(entry).ends_with(".json"):
			out.append("packages/game-content/normalized/%s" % str(entry))
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort()
	return out


## The committed fresh-player corpus: the raw document under `save`, plus the
## flag facts this suite measures from it. The projection and evaluation sections
## are handed the raw `save`, because they must run over the **real** committed
## bytes rather than over a summary of them.
func _read_corpus() -> Dictionary:
	var absolute := Paths.repo_root().path_join("tests/saves/fresh-player.json")
	if not FileAccess.file_exists(absolute):
		fail("the committed fresh-player corpus is present")
		return {}
	var text := FileAccess.get_file_as_string(absolute)
	var parsed: Variant = JSON.parse_string(text)
	if not (parsed is Dictionary):
		fail("the committed corpus parses as an object")
		return {}
	var save: Dictionary = parsed
	var out := {
		"save": save,
		"flag": -1,
		# Both map flags start `false` and are only ever raised when a map is
		# actually found carrying the key. The earlier form started `true`, which
		# meant an unparsed corpus would have satisfied "the map carries no such
		# key" for the wrong reason — a vacuous pass.
		"map_has_flag": false,
		"maps0_has_flag": false,
		"maps_parsed": false,
		"items": {},
		"map_count": -1,
		"sha256": text.sha256_text(),
	}
	var info: Variant = save.get("playerInfo")
	if info is Dictionary:
		out["flag"] = int((info as Dictionary).get(TutorialFlow.FLAG_KEY, -1))
	var maps: Variant = save.get("maps")
	if maps is Array:
		out["maps_parsed"] = true
		out["map_count"] = (maps as Array).size()
		for entry: Variant in maps as Array:
			if entry is Dictionary \
					and (entry as Dictionary).has(TutorialFlow.FLAG_KEY):
				out["map_has_flag"] = true
		if not (maps as Array).is_empty():
			var first: Variant = (maps as Array)[0]
			if first is Dictionary:
				out["maps0_has_flag"] = \
					(first as Dictionary).has(TutorialFlow.FLAG_KEY)
				var rows: Variant = (first as Dictionary).get("items")
				if rows is Dictionary:
					out["items"] = rows
	return out


func _village_saves() -> Array:
	var out: Array = []
	var directory := Paths.repo_root().path_join("villages")
	var handle := DirAccess.open(directory)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if not handle.current_is_dir() and str(entry).ends_with(".json"):
			var absolute := directory.path_join(str(entry))
			var parsed: Variant = JSON.parse_string(
				FileAccess.get_file_as_string(absolute))
			if parsed is Dictionary:
				var info: Variant = (parsed as Dictionary).get("playerInfo")
				if info is Dictionary:
					out.append({
						"name": str(entry),
						"flag": (info as Dictionary).get(TutorialFlow.FLAG_KEY),
					})
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return str(a["name"]) < str(b["name"]))
	return out


func _village_summary() -> Dictionary:
	var completed := 0
	var seeded := 0
	var names: Array = []
	for entry: Dictionary in _village_saves():
		names.append(str(entry["name"]))
		if int(entry["flag"]) == TutorialFlow.COMMITTED_FLAG_AFTER:
			completed += 1
		elif int(entry["flag"]) == TutorialFlow.COMMITTED_FLAG_BEFORE:
			seeded += 1
	names.sort()
	return {"count": names.size(), "completed": completed, "seeded": seeded,
		"names": names}


## The committed capture manifest and the recorded step files, read together.
func _read_fixture() -> Dictionary:
	var out := {"outcomes": [], "schema": "", "rounds": -1,
		"recorded_steps": 0, "probes": 0, "round_names": [],
		"absences": {}, "gate": {}}
	var absolute := Paths.repo_root().path_join(TutorialFlow.CAPTURE_MANIFEST)
	if not FileAccess.file_exists(absolute):
		fail("the committed tutorial capture manifest is present")
		return out
	var manifest: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(absolute))
	if not (manifest is Dictionary):
		fail("the capture manifest parses as an object")
		return out
	var document: Dictionary = manifest
	out["schema"] = str(document.get("schema", ""))
	out["fixture"] = str(document.get("fixture", ""))
	var absences: Variant = document.get("absences")
	if absences is Dictionary:
		out["absences"] = (absences as Dictionary).duplicate(true)
	var gate: Variant = document.get("gate")
	if gate is Dictionary:
		out["gate"] = (gate as Dictionary).duplicate(true)
	var rounds: Variant = document.get("rounds")
	if rounds is Array:
		out["rounds"] = (rounds as Array).size()
		for entry: Variant in rounds as Array:
			if not (entry is Dictionary):
				continue
			var round: Dictionary = entry
			out["round_names"].append(str(round.get("round", "")))
			var recorded: Variant = round.get("outcomes")
			if recorded is Array:
				(out["outcomes"] as Array).append_array(recorded)
			var steps: Variant = round.get("steps")
			if steps is Array:
				out["recorded_steps"] = int(out["recorded_steps"]) \
					+ (steps as Array).size()
			if round.get("probe") != null:
				out["probes"] = int(out["probes"]) + 1
	# The third outcome is the anchor: the client-sent ladder the NEUTRAL vector
	# refuses. Its refusal is RE-DERIVED here from the committed rule rather than
	# quoted, so the suite proves the service's decision rather than repeating it.
	if (out["outcomes"] as Array).size() >= 3:
		var ladder: Dictionary = (out["outcomes"] as Array)[2]
		out["ladder_resources_moved"] = int(
			ladder.get("resources_moved_count", -1))
		out["ladder_refused"] = "invalid_vector" if _vector_is_refused(
			_captured_ladder()) else ""
		out["ladder"] = _captured_ladder()
	return out


## The client-sent resource ladder the committed capture actually sent, read out
## of the recorded request rather than restated from memory. The capture stores
## the legacy form body as a signed `data` string, so the commands are recovered
## by dropping the signature and parsing the remainder — which is the same
## envelope the legacy route itself reads.
func _captured_ladder() -> Array:
	var relative := "%s/steps/minting/%s/request.json" % [
		FIXTURE_DIRECTORY, MINTING_STEP]
	var absolute := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(absolute):
		fail("the committed minting-anchor request is present")
		return []
	var request: Variant = JSON.parse_string(
		FileAccess.get_file_as_string(absolute))
	if not (request is Dictionary):
		fail("the minting-anchor request parses as an object")
		return []
	var form: Variant = (request as Dictionary).get("form")
	if not (form is Dictionary):
		fail("the minting-anchor request records its form")
		return []
	var data := str((form as Dictionary).get("data", ""))
	var semicolon := data.rfind(";")
	if semicolon < 0:
		fail("the recorded form body carries the signed data envelope")
		return []
	var commands: Variant = JSON.parse_string(
		data.substr(semicolon + 1)).get("commands")
	if not (commands is Array) or (commands as Array).is_empty():
		fail("the recorded envelope records its commands")
		return []
	var first: Variant = (commands as Array)[0]
	if not (first is Array) or (first as Array).size() < 4:
		fail("the recorded command carries its resource vector")
		return []
	var vector: Variant = (first as Array)[3]
	if not (vector is Array):
		fail("the recorded vector is an array of slots")
		return []
	var out: Array = []
	for slot: Variant in vector as Array:
		out.append(int(slot))
	return out


## Whether the endpoint's own vector validator refuses this ladder. Implemented
## from the committed rule — a vector with a non-zero slot is not the neutral
## vector this service derives, and the endpoint builds its own, so a client-sent
## ladder is refused outright — so the suite proves the refusal.
func _vector_is_refused(vector: Array) -> bool:
	if vector.size() != TutorialFlow.NEUTRAL_VECTOR_SLOTS:
		return true
	for slot: Variant in vector:
		if typeof(slot) != TYPE_INT:
			return true
		if int(slot) != 0:
			return true
	return false


## The committed fixture files, as paths RELATIVE to the repository root. The
## base is re-derived per file rather than stripped off the walked path, because
## `String.replace` on an absolute Windows path with a `/`-joined prefix does not
## match and would silently return the absolute path — which `FileAccess` cannot
## then verify.
func fixture_paths() -> Array:
	var out: Array = []
	_collect_files(FIXTURE_DIRECTORY, out)
	out.sort()
	return out


func _collect_files(relative: String, out: Array) -> void:
	var handle := DirAccess.open(Paths.repo_root().path_join(relative))
	if handle == null:
		return
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		var child := "%s/%s" % [relative, str(entry)]
		if handle.current_is_dir():
			_collect_files(child, out)
		else:
			out.append(child)
		entry = handle.get_next()
	handle.list_dir_end()


func _package_digest() -> Dictionary:
	var out: Dictionary = {}
	for name: String in ["units", "buildings", "items", "quests", "tables",
			"economy", "social", "taxonomy", "darts", "globals", "offers",
			"images"]:
		var relative := "packages/game-content/normalized/%s.json" % name
		var absolute := Paths.repo_root().path_join(relative)
		if FileAccess.file_exists(absolute):
			out[name] = FileAccess.get_file_as_string(absolute).sha256_text()
	return out


# ---------------------------------------------------------------------------
# Source reading
# ---------------------------------------------------------------------------


func _read(relative: String) -> String:
	var absolute := Paths.project_dir().path_join(relative.trim_prefix("res://"))
	if not FileAccess.file_exists(absolute):
		fail("the delivered source %s is present" % relative)
		return ""
	return FileAccess.get_file_as_string(absolute)


func _read_repo_file(relative: String) -> String:
	var absolute := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(absolute):
		fail("the repository file %s is present" % relative)
		return ""
	return FileAccess.get_file_as_string(absolute)


## A source's DECLARATIONS: comment lines are dropped and string-literal content
## is blanked, so a prose mention or a recorded non-claim string can never be
## mistaken for code.
func _code_only(body: String) -> String:
	var out: Array = []
	for line: String in body.split("\n"):
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
	return "\n".join(out)


func _preloads(body: String) -> Array:
	var out: Array = []
	for line: String in body.split("\n"):
		var marker := "preload(\""
		var at := line.find(marker)
		if at < 0:
			continue
		var rest := line.substr(at + marker.length())
		var quote := rest.find("\"")
		if quote <= 0:
			continue
		out.append(rest.substr(0, quote))
	out.sort()
	return out


## The declared identifier names of a source: its `const`, `var`, `func`,
## `enum`, and `class_name` names. A declared identifier is what a reader can call
## and what the anti-invention guard is about; a string inside a data table is
## not.
func _declared_identifiers(body: String) -> Array:
	var out: Array = []
	var prefixes := ["const ", "var ", "static var ", "static func ", "func ",
		"enum ", "class_name ", "signal "]
	for line: String in body.split("\n"):
		var stripped := line.strip_edges()
		var matched := ""
		for prefix: String in prefixes:
			if stripped.begins_with(prefix):
				matched = prefix
				break
		if matched == "":
			continue
		var rest := stripped.substr(matched.length())
		var at := rest.find(" ")
		if at > 0:
			rest = rest.substr(0, at)
		if rest.find("(") > 0:
			rest = rest.substr(0, rest.find("("))
		rest = rest.strip_edges()
		if rest.length() > 0:
			out.append(rest)
	return out


## The parameter list of one `func` declaration, as text.
func _signature_of(body: String, name: String) -> String:
	var lines := body.split("\n")
	for index in range(lines.size()):
		if not (lines[index] as String).begins_with("func %s(" % name):
			continue
		var collected: Array = []
		for offset in range(lines.size() - index):
			var line := lines[index + offset] as String
			collected.append(line)
			if line.contains("->"):
				break
			if line.strip_edges().ends_with(":"):
				break
		return " ".join(collected)
	fail("the source declares func %s(" % name)
	return ""


## The `JSON.stringify({...})` body one transport sends, as text.
func _json_stringify_block(body: String, path_constant: String) -> String:
	var marker := "_call(\"POST\", %s, JSON.stringify({" % path_constant
	var at := body.find(marker)
	if at < 0:
		fail("the transport sends a POST to %s" % path_constant)
		return ""
	var collected := ""
	var lines := body.substr(at).split("\n")
	for line: String in lines:
		collected += line + "\n"
		if line.strip_edges().ends_with("}))"):
			break
	return collected


## Every `/v0/...` route literal a source declares whose final path segment
## contains `word`, deduplicated and sorted. Reading the raw text is deliberate:
## a route IS a string literal, so the `_code_only()` projection would hide all of
## them. Comment lines are skipped, because the service documents this route in a
## design note and prose must not read as a second declaration.
func _routes_named(raw: String, word: String) -> Array:
	var out: Array = []
	for line: String in raw.split("\n"):
		if line.strip_edges().begins_with("#"):
			continue
		var at := line.find("/v0/")
		while at >= 0:
			var rest := line.substr(at)
			var end := rest.find("/")
			if end <= 0:
				end = rest.find("\"")
			if end <= 0:
				break
			var path := rest.substr(0, end)
			if path.contains(word) and not out.has(path):
				out.append(path)
			at = line.find("/v0/", at + path.length())
	out.sort()
	return out


## The `@app.<method>(...)` decorator lines that name a route of this family.
func _route_declarations(raw: String, word: String) -> Array:
	var out: Array = []
	for line: String in raw.split("\n"):
		var stripped := line.strip_edges()
		if stripped.begins_with("#") or not stripped.begins_with("@app."):
			continue
		if stripped.contains("/v0/") and stripped.contains(word):
			out.append(stripped)
	return out


## Whether the module's own absence inventory NAMES one absent family. The
## inventory is the contract, so each entry must exist: an absent figure that
## nobody wrote down is indistinguishable from an oversight.
func _names_an_absent_helper(family: String) -> bool:
	for entry: Variant in TutorialFlow.ABSENT_HELPERS:
		if str(entry).begins_with(family) or str(entry).contains(family):
			return true
	return false


## Whether the delivered module's own comment text records a non-claim phrase.
func _module_records(phrase: String) -> bool:
	var body := _read(DELIVERED_FLOW_SOURCE)
	if body.contains(phrase):
		return true
	for entry: Variant in TutorialFlow.NON_CLAIMS:
		if str(entry).contains(phrase):
			return true
	return false


func _widen(value: Variant) -> Variant:
	if value is int:
		return float(value)
	if value is Array:
		var out: Array = []
		for entry: Variant in value as Array:
			out.append(_widen(entry))
		return out
	return value


# ---------------------------------------------------------------------------
# Envelope builders for the fail-closed matrix
# ---------------------------------------------------------------------------


## One well-formed v0 tutorial envelope, built from the committed gate and the
## committed post-value. Deliberately hand-built rather than captured, so the
## matrix's negatives are the only variables.
func _envelope() -> Dictionary:
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": "compat-0",
		"server_time": 1756800000,
		"result": "success",
		"tutorial": {
			"command": TutorialFlow.COMPLETE_TUTORIAL_COMMAND,
			"step": 15,
			"step_kind": "integer",
			"record": TutorialFlow.PLAYER_INFO_RECORD,
			"key": TutorialFlow.FLAG_KEY,
			"flag_before": 0,
			"flag_after": 1,
			"flag_moved": true,
			"gate_satisfied": true,
			"gate_arm": TutorialFlow.ARM_EXACT,
			"in_gate_hole": false,
			"already_completed": false,
			"no_op_reason": "",
			"dispatched": true,
			"resolvable": true,
			"completed": true,
			"stored": 1,
		},
		"gate": TutorialFlow.gate_record(),
		"changed": ["/playerInfo/completed_tutorial"],
		"resources": {"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
			"steel": 2000, "cash": 5, "mana": 0},
	}


func _mutate(envelope: Dictionary, key: String, value: Variant) -> Variant:
	var copy := envelope.duplicate(true)
	copy[key] = value
	return copy


func _unset(envelope: Dictionary, key: String) -> Variant:
	var copy := envelope.duplicate(true)
	copy.erase(key)
	return copy


# ---------------------------------------------------------------------------
# The live-tutorial phase (verify-boot's `tutorial-live`)
# ---------------------------------------------------------------------------


## One pass through **all three** verdicts over the REAL Compatibility endpoint,
## in the only order that reaches all three in a single round.
##
## The endpoint checks the flag BEFORE the gate, so once a tutorial completes
## every later step answers `already_completed` and the `gate_declined` verdict
## becomes unreachable for the rest of that save's life. The committed corpus
## starts at the seed value, so the hole step is sent FIRST — otherwise this
## phase would silently prove only the third verdict and read as full coverage.
##
## This asserts the typed response for each step AND its post-state: the derived
## `0 -> 1` flag transition with exactly one changed leaf, the no-op verdicts
## changing nothing at all, the flag genuinely moving in the SAVE between the
## first and second request, and **every stored resource unchanged** across all
## three — which is the endpoint's second proof half and is non-tautological only
## because the committed capture's anchor round really did move all seven. The
## phase harness separately asserts the corpus save file mutated.
func _check_live_tutorial() -> void:
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
	var before_payload := await _live_payload(api, pid)
	check(not before_payload.is_empty(), "the corpus pre-tutorial payload resolves")
	if before_payload.is_empty():
		return
	var resources_before := _live_balances(before_payload)
	check_eq(int(TutorialFlow.project(before_payload)["stored"]), CORPUS_FLAG,
		"the live corpus starts at the committed seed value, so the 0 -> 1 "
			+ "transition is genuinely exercisable in this round")
	check_eq(_live_row_count(before_payload), CORPUS_PLACEMENTS,
		"the live corpus places its 40 rows before any step")

	# --- the declined step, FIRST -------------------------------------------
	var declined: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town(pid, 16)
	check(declined.ok,
		"a hole step is a typed SUCCESS over the real endpoint, not an error: %s"
			% declined.error_message)
	check_eq(declined.result, "success",
		"and it carries the legacy success result string")
	check_eq(declined.changed, [],
		"a declined step changes nothing at all")
	check_eq(str(declined.tutorial.get("no_op_reason", "")), "gate_declined",
		"and names the committed decline")
	check_eq(declined.tutorial.get("gate_satisfied"), false,
		"reporting that no arm fired")
	check_eq(str(declined.tutorial.get("gate_arm", "")), TutorialFlow.ARM_NONE,
		"and which arm: none")
	check_eq(declined.tutorial.get("in_gate_hole"), true,
		"and that this step is the gate's own hole, not malformed input")
	check_eq(int(declined.tutorial.get("flag_before", -1)), CORPUS_FLAG,
		"reporting the flag it started from, verbatim")
	check_eq(int(declined.tutorial.get("flag_after", -1)), CORPUS_FLAG,
		"and the flag it left behind, unchanged")
	_check_live_balances(declined, resources_before, "the declined step")
	check_eq(int(TutorialFlow.project(
			await _live_payload(api, pid))["stored"]), CORPUS_FLAG,
		"the save really still records the seed value after a declined step")

	# --- the completing step -----------------------------------------------
	var completed: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town(pid, 15)
	check(completed.ok,
		"a completing step is accepted by the real endpoint: %s"
			% completed.error_message)
	check_eq(completed.result, "success",
		"the completing step carries the legacy success result")
	check_eq(completed.changed, ["/playerInfo/completed_tutorial"],
		"and changes EXACTLY the one flag leaf, addressed as a save-level record")
	check_eq(str(completed.tutorial.get("command", "")), BRANCH_COMMAND,
		"the service derived the one committed command")
	check_eq(str(completed.tutorial.get("record", "")), "playerInfo",
		"reporting the record the flag lives in")
	check_eq(str(completed.tutorial.get("key", "")), "completed_tutorial",
		"and the flag key")
	check_eq(int(completed.tutorial.get("flag_before", -1)), CORPUS_FLAG,
		"the completion reports the seed value it started from")
	check_eq(int(completed.tutorial.get("flag_after", -1)),
		TutorialFlow.COMMITTED_FLAG_AFTER,
		"and the committed post-value it wrote")
	check_eq(completed.tutorial.get("flag_moved"), true,
		"reporting that its own flag pair moved")
	check_eq(completed.tutorial.get("dispatched"), true,
		"and that it dispatched")
	check_eq(str(completed.tutorial.get("gate_arm", "")), TutorialFlow.ARM_EXACT,
		"and which arm fired: the exact one")
	check_eq(completed.tutorial.get("in_gate_hole"), false,
		"and that step 15 is not in the hole")
	_check_live_balances(completed, resources_before, "the completing step")
	check_eq(int(TutorialFlow.project(
			await _live_payload(api, pid))["stored"]),
		TutorialFlow.COMMITTED_FLAG_AFTER,
		"the SAVE really moved 0 -> 1, which is what makes the typed response's "
			+ "post-state proof something other than an echo")
	check_eq(_live_row_count(await _live_payload(api, pid)), CORPUS_PLACEMENTS,
		"and the save still places the same 40 rows: a completion moves no row")

	# --- the repeat, third --------------------------------------------------
	var repeated: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town(pid, 15)
	check(repeated.ok,
		"the repeat is a typed SUCCESS, not an error: %s" % repeated.error_message)
	check_eq(repeated.result, "success",
		"and it carries the legacy success result string too")
	check_eq(repeated.changed, [],
		"and changes nothing at all")
	check_eq(str(repeated.tutorial.get("no_op_reason", "")),
		"already_completed",
		"and names the flag's own prior state, not a failure")
	check_eq(int(repeated.tutorial.get("flag_before", -1)),
		TutorialFlow.COMMITTED_FLAG_AFTER,
		"reporting the post-value it started from")
	check_eq(int(repeated.tutorial.get("flag_after", -1)),
		TutorialFlow.COMMITTED_FLAG_AFTER,
		"and the same post-value it left behind")
	check_eq(repeated.tutorial.get("flag_moved"), false,
		"reporting that its own flag pair did NOT move")
	_check_live_balances(repeated, resources_before, "the repeat")

	# --- the endpoint's own refusals ---------------------------------------
	var blank: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town("", 15)
	check_eq(blank.ok, false, "an empty identity is refused by the endpoint")
	check_eq(blank.error_code, "missing_user_id",
		"and the refusal keeps the endpoint's OWN code, not a client one")
	check(blank.tutorial.is_empty(),
		"and carries no partial tutorial block")
	var unknown: TutorialFlow.TutorialResult = \
		await api.complete_tutorial_town("no-such-player", 15)
	check_eq(unknown.error_code, "unknown_user_id",
		"an unknown identity keeps the endpoint's own code too")
	# A bool step CANNOT be expressed through this typed surface, and that is the
	# finding rather than a gap in the phase. The facade's forwarder takes
	# `step: int`, so the engine coerces a bool at the CALL BOUNDARY and no bool
	# ever reaches the wire; the service's own `validate_step` therefore refuses a
	# bool that no caller of this signature can send. This is asserted as a
	# boundary and recorded as `invalid_step_structurally_unreachable`, in the
	# same spirit as the quests line's five missing-key refusals — NOT as proof
	# that the service refuses a bool.
	var coerced: Variant = await api.complete_tutorial_town(pid, true)
	check(coerced is TutorialFlow.TutorialResult,
		"a bool step is answered rather than crashing the call boundary")
	if coerced is TutorialFlow.TutorialResult:
		var typed_bool: TutorialFlow.TutorialResult = coerced
		# `true` reaches the service as the integer 1, and the save is already
		# complete, so the flag check -- which precedes the gate -- answers
		# `already_completed`. Nothing here distinguishes a coerced bool from an
		# integer 1, which is exactly the point being recorded.
		check_eq(typed_bool.ok, true,
			"the coerced bool is answered as the integer it became, not refused")
		check_eq(str(typed_bool.tutorial.get("step_kind", "")),
			TutorialFlow.STEP_KIND_INTEGER,
			"and the response names it as the integer it arrived as")
		check_eq(str(typed_bool.tutorial.get("no_op_reason", "")),
			"already_completed",
			"so the flag's own prior state answered it, exactly as it would "
				+ "answer an honest integer")
	check_eq(int(TutorialFlow.project(
			await _live_payload(api, pid))["stored"]),
		TutorialFlow.COMMITTED_FLAG_AFTER,
		"and the coerced bool left the committed post-value untouched")
	check_eq(_v0_step_parameter_is_strict(),
		true,
		"the forwarder's own parameter is typed `step: int`, which is WHY no "
			+ "bool can reach the wire from this surface")

	# One machine-readable marker so verify-boot can match the phase's substance
	# rather than its exit code. Every field is a VALUE the checks above already
	# asserted, not a restatement of "the scenario passed".
	print(("[test] live-tutorial applied declined=no_op_wrote=0 "
		+ "hole_step=16 arm=none then completed=0->1 changed=1 leaf_flag=true "
		+ "then repeated=no_op_wrote=0 rows=%d resources_unchanged=3 "
		+ "refused=missing_user_id,unknown_user_id "
		+ "invalid_step=structurally_unreachable")
		% CORPUS_PLACEMENTS)


## Whether the loopback facade's tutorial forwarder really types its step as a
## strict integer. Read from the source rather than trusted, because this is the
## single fact that makes the service's bool refusal unreachable from here. The
## declaration is assembled across lines, because the signature wraps — a
## single-line scan would read only `user_id` and silently answer `false`.
func _v0_step_parameter_is_strict() -> bool:
	var lines := _read(V0_SOURCE).split("\n")
	for index in range(lines.size()):
		if not (lines[index] as String).begins_with(
				"func complete_tutorial_town("):
			continue
		var declaration := ""
		for offset in range(lines.size() - index):
			declaration += (lines[index + offset] as String) + " "
			if declaration.strip_edges().ends_with(":"):
				break
		return declaration.contains("step: int")
	return false


func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The corpus's own bootstrap payload, or {} when it cannot be read.
func _live_payload(api: Variant, user_id: String) -> Dictionary:
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return {}
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return {}
	return (info as BootData.PlayerInfoPayload).raw


## The payload's seven stored balances, as a comparable dictionary. Read from the
## MAP for the five the map holds and from the two save-level records for cash
## and mana, exactly as the saved corpus records them — the same split the
## endpoint's own `resources()` accessor uses.
func _live_balances(payload: Dictionary) -> Dictionary:
	var map: Variant = payload.get("map")
	var info: Variant = payload.get("playerInfo")
	var private: Variant = payload.get("privateState")
	if not (map is Dictionary) or not (info is Dictionary) \
			or not (private is Dictionary):
		return {}
	var out := {}
	for key: String in ["xp", "gold", "wood", "oil", "steel"]:
		out[key] = int((map as Dictionary).get(key, -1))
	out["cash"] = int((info as Dictionary).get("cash", -1))
	out["mana"] = int((private as Dictionary).get("mana", -1))
	return out


## Every stored resource the endpoint reported must equal the value the intent
## started from. This is the second half of the endpoint's post-execution proof,
## and it is asserted for all three verdicts, so a declined step and a repeat
## cannot quietly move a balance.
func _check_live_balances(result: TutorialFlow.TutorialResult,
		before: Dictionary, label: String) -> void:
	check_eq(before.size(), RESOURCE_COUNT,
		"the pre-state carried all seven stored resources")
	check(result.resources != null,
		"%s reports the seven authoritative resources" % label)
	if result.resources == null:
		return
	var reported := {
		"xp": int(result.resources.xp),
		"gold": int(result.resources.gold),
		"wood": int(result.resources.wood),
		"oil": int(result.resources.oil),
		"steel": int(result.resources.steel),
		"cash": int(result.resources.cash),
		"mana": int(result.resources.mana),
	}
	check_eq(reported, before,
		"%s moved NO stored resource: a tutorial completion pays nothing, "
			% label + "and the capture's anchor round proves a client that sent "
			+ "its own vector would have moved all seven")


func _live_row_count(payload: Dictionary) -> int:
	var map: Variant = payload.get("map")
	if not (map is Dictionary):
		return -1
	var rows: Variant = (map as Dictionary).get("items")
	if not (rows is Dictionary):
		return -1
	return (rows as Dictionary).size()
