extends "res://tests/test_base.gd"
## Quest suite (OpenSpec `godot-quests` "The quest state is projected verbatim
## and fails closed" / "The six-branch command inventory records what each branch
## reads and writes" / "The `end_quest` destruction count is refused, and the
## refusal is recorded as a divergence" / "No quest reward is paid and no stored
## resource moves" / "The committed quest-content inventory is reported and never
## used" / "A quest action is a server-derived intent, and no client outcome is
## trusted" / "Quest timing is recorded as client-writable and never delivered" /
## "Executed-legacy behaviour fixtures are captured" / "Quest evidence and claim
## limits", design D1-D12).
##
## Checks:
##   projection the seven committed fields reported **verbatim** with nothing
##              derived from another, the **seven** malformed shapes each reported
##              unresolvable with their recorded state intact, and the corpus's
##              recorded **null** quest-variable field reported as a recorded null
##              rather than as an empty map;
##   branches   the six recorded contracts **measured against `command.py`**: the
##              no-op branch's total inaction, the on-demand unbounded growth, the
##              quest-variable writer's unbounded key set and its one ignored key,
##              the chapter branch's stringified identifier, its wrap and its
##              clear, and the rank branch's unbounded client pair;
##   content    the **measured** content inventory — every consumer count compared
##              against the committed source, the uniform reward value, the
##              all-empty hints, and that **no** delivered code identifier or
##              computation is named after the reward field;
##   writers    the **seven** writers of quest state, `fast_forward`'s two write
##              sites and its client-supplied seconds, the no-op branch recorded
##              honestly, and the save **migration** recorded as a migration;
##   type_facts the two reproduced legacy shape facts: the integer mission becoming
##              a string, and the recorded null becoming a dict;
##   absence    the six refusal families with non-empty reasons, the named
##              non-derivation list, the module's whole function inventory and its
##              inner class's readers compared against pinned lists (tasks 2.2 and
##              4.4), and the recorded `null` reason kept out of the refusal set;
##   corpus     the committed fresh-player corpus: 40 rows and every quest field at
##              its initial value;
##   ledger     the cross-milestone agreement: `end_quest` is one of
##              `map_lose_item`'s only two callers and the quest-side reach is
##              **refused** here (task 5.3);
##   fixture    the committed executed-legacy capture: **six** recorded steps, the
##              no-op step's byte-identity, the refused destruction with every row
##              byte-identical, the **five** probes, and the corpus staying
##              byte-identical;
##   intents    the facade's quest operation takes EXACTLY the save identity, a
##              closed action, and the branch's own addressing, so no channel exists
##              through which a client could send a progress pair, a value, a
##              difficulty, an outcome, or a unit list;
##   purity     the delivered module names no node, clock, request, or transport
##              token, and loads nothing but the typed-data module.
##
## Hermetic: no process, no server, no socket, and no request is issued. A quest
## state is read from a save already in hand, so no GameApi operation is involved
## except in the `intents` and offline-double reads.
##
## `--scenario=live-quests` is the `quests-live` phase: all six intents through the
## real Compatibility endpoint over a disposable corpus, asserting each typed
## response, each post-condition, that every placed row is byte-identical, that
## every stored resource is unchanged, and the refusal codes.
## `--report=<path>` writes the deterministic `quests-report-v1` evidence report;
## the bare `--report` flag defaults to `evidence/quests/report.json`. Every table
## is derived from the live model and the committed bytes, so the report cannot
## drift from the code it documents.

const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/quests/report.json"
## The committed corpus this line measures.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
## The committed fixture directory, its manifest, and the six recorded steps.
const FIXTURE_DIR := "tests/fixtures/godot-quests"
const FIXTURE_MANIFEST := FIXTURE_DIR + "/capture-manifest.json"
const STEP_NAMES := [
	"command_set_goals",
	"command_complete_goal",
	"command_set_quest_var",
	"command_collect_mission",
	"command_admin_set_quest_rank",
	"command_end_quest",
]
## The addressing each closed ACTION uses, keyed by action rather than by the
## recorded step's directory name — so the two can never be confused.
const ACTION_ADDRESSING := {
	"set_goal": 2,
	"complete_goal": 2,
	"set_quest_var": "spawned",
	"collect_mission": 5,
	"set_quest_rank": 3,
	"end_quest": 7,
}
## The legacy root modules the quest figures are measured across.
const LEGACY_MODULES := [
	"command.py", "engine.py", "sessions.py", "server.py", "constants.py",
	"get_game_config.py", "version.py",
]
## The recorded figures this suite RE-MEASURES rather than trusting. A drift fails
## the run instead of publishing a different contract (task 2.4).
const EXPECTED_BRANCH_RANGES := {
	"set_goals": [68, 74],
	"complete_goal": [76, 79],
	"set_quest_var": [87, 117],
	"collect_mission": [430, 442],
	"admin_set_quest_rank": [745, 750],
	"end_quest": [752, 806],
}
## Quoted occurrences per committed quest field across the seven modules, and the
## modules each is read from.
const EXPECTED_FIELD_CONSUMERS := {
	"id": 8, "title": 2, "hint": 0, "description": 0, "reward": 0, "kind": 0,
	"legacy_id": 0, "source_file": 0, "source_layer": 0, "content_version": 0,
}
const EXPECTED_FIELD_MODULES := {"id": ["command.py", "get_game_config.py"],
	"title": ["command.py"]}
## Quoted occurrences AND distinct lines for each quest state key. They differ for
## exactly one key: `timestampLastChapter` is read and written on ONE line.
const EXPECTED_KEY_OCCURRENCES := {
	"goals": 3, "questsRank": 1, "unlockedQuestIndex": 0, "currentQuestVars": 5,
	"questTimes": 6, "idCurrentMission": 2, "timestampLastChapter": 3,
}
const EXPECTED_KEY_LINES := {
	"goals": 3, "questsRank": 1, "unlockedQuestIndex": 0, "currentQuestVars": 5,
	"questTimes": 6, "idCurrentMission": 2, "timestampLastChapter": 2,
}
const EXPECTED_QUEST_ENTRIES := 91
const EXPECTED_REWARD_VALUE := 10
const EXPECTED_ID_MIN := 1
const EXPECTED_ID_MAX := 91
const EXPECTED_GOALS_LENGTH := 151
## Tokens a pure projection must not carry: a node, a clock, a request, or a
## transport. The transport needles are spelled as fragments because the
## project-scope suite scans every source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]
## The whole function inventory of `quest_flow.gd`, public and private. Compared as
## a sorted set, so a completion, remaining-time, price, or progress helper fails
## the run wherever it is added (task 4.4).
const EXPECTED_FLOW_MODULE_METHODS := [
	"_action_index", "_recorded_snapshot", "_reject", "_result_error",
	"_string_keyed", "_string_keyed_or_name", "_type_name", "addressing_reason",
	"branch_record", "clamp_difficulty", "confirm_text", "evaluate",
	"intent_body", "intent_record", "is_action", "is_addressing",
	"is_goal_index", "is_mission", "is_quest_id", "is_quest_rank_index",
	"is_quest_var_key", "is_strict_int", "offers", "parse_result", "project",
	"readout_text", "refusal_text", "result_failure", "wire_key", "wrap_mission",
]
## The inner `QuestStateView` readers, pinned for the same reason.
const EXPECTED_VIEW_METHODS := [
	"error", "fields", "goals", "goals_null_entries", "last_chapter", "mission",
	"mission_is_string", "quest_times", "quest_vars", "quest_vars_is_null",
	"ranks", "reason", "recorded", "resolvable", "unlocked_index",
]
## Names a completion, remaining-time, price, progress, or unlock helper would
## take. Each is ALSO a named entry in `QuestFlow.NON_DERIVATION`, so the recorded
## list and this one cannot drift: a rename cannot smuggle a helper past the
## inventory and a leftover in the recorded list fails visibly.
const FORBIDDEN_HELPERS := [
	"mark_goal_complete", "is_goal_complete", "quest_reward", "quest_price",
	"quest_progress_ratio", "quest_remaining_time", "quest_ready",
	"fast_forward",
]
## Further spellings that are likewise absent, checked against the module's
## declarations and its whole function inventory.
const ALSO_ABSENT_HELPERS := [
	"goal_complete", "goal_reward", "quest_reward_amount", "quest_cost",
	"quest_time_left", "quest_complete", "quest_elapsed", "quest_unlock",
	"quest_unlocked", "quest_difficulty_bound", "is_complete", "remaining_time",
]
## Tokens that would mean a completion, remaining time, price, or progress is
## computed.
const BEHAVIOUR_NEEDLES := [
	"mark_goal_complete(", "is_goal_complete(", "quest_reward(",
	"quest_progress_ratio(", "quest_remaining_time(", "maxf(", "minf(", "Time.",
]
## The committed reward field's own name, which NO delivered identifier may carry.
const REWARD_FIELD := "reward"
## The non-claim phrases the delta's evidence requirement names.
const REQUIRED_NON_CLAIMS := [
	"no Flash",
	"NO QUEST REWARD IS PAID AND NO STORED RESOURCE MOVES",
	"DESTRUCTION COUNT IS REFUSED",
	"NO COMPLETION STATE EXISTS",
	"NO BOUND IS ADDED",
	"NO MEMBERSHIP TEST",
	"UNLOCKED-QUEST INDEX is reported and NEVER written",
	"NO FAST-FORWARD OPERATION IS DELIVERED",
	"NO ELAPSED-TIME",
	"REPORTED AND NEVER USED",
	"no pixel-parity oracle exists",
	"no windowed capture is claimed",
]
## The endpoint override the live phase is invoked with.
const ARG_ENDPOINT := "--gameapi-endpoint="
## The delivered module's own resource path, read by the suite for its
## function-inventory and purity checks — read reflectively so a rename or a new
## helper fails the SUITE rather than a comment.
const QUEST_SOURCE := "res://scripts/units/quest_flow.gd"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-quests":
		await _check_live_quests()
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

	_check_projection()
	_check_branches()
	var content := _check_content()
	var source := _check_source()
	_check_writers()
	_check_type_facts()
	_check_absence()
	var corpus := _check_corpus()
	_check_ledger()
	var fixture := _check_fixture()
	_check_intents()
	await _check_fake_double()
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before, save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, source, content, corpus, fixture, package_before,
			save_before)
	info("quests: corpus rows %d, goals %d, fixture steps %d"
		% [int(corpus.get("rows", 0)), int(corpus.get("goals_length", 0)),
			(fixture.get("steps", []) as Array).size()])


# ---------------------------------------------------------------------------
# The projection (task 1.1 / 1.2)
# ---------------------------------------------------------------------------


## Every recorded quest field, reported verbatim, with nothing derived — and the
## fail-closed paths, and the recorded null that must survive as a null.
func _check_projection() -> void:
	var private := _committed_private_state()
	var first_map := _committed_first_map()
	var projected: Variant = QuestFlow.project(private, first_map)
	check(bool(projected.get("ok", false)),
		"the committed quest state projects (error: %s)"
			% str(projected.get("error", "")))
	if not bool(projected.get("ok", false)):
		return
	var quests: Variant = projected["quests"]
	# --- every field, verbatim ------------------------------------------------
	check_eq((quests as QuestFlow.QuestStateView).goals().size(),
		EXPECTED_GOALS_LENGTH, "the goals list is reported with its full length")
	check_eq((quests as QuestFlow.QuestStateView).goals_null_entries(),
		EXPECTED_GOALS_LENGTH, "every recorded goal entry is reported as null")
	check_eq((quests as QuestFlow.QuestStateView).ranks(), {},
		"the rank map is reported verbatim as the committed empty map")
	check_eq((quests as QuestFlow.QuestStateView).quest_times(), {},
		"the quest-time map is reported verbatim as the committed empty map")
	check_eq((quests as QuestFlow.QuestStateView).mission(), 0,
		"the current mission is reported verbatim as the committed INTEGER 0")
	check(not (quests as QuestFlow.QuestStateView).mission_is_string(),
		"the committed mission is an integer, not a string (design D8)")
	check_eq((quests as QuestFlow.QuestStateView).last_chapter(), 0,
		"the last-chapter instant is reported verbatim")
	check_eq((quests as QuestFlow.QuestStateView).unlocked_index(), 0,
		"the unlocked-quest index is reported verbatim")
	# --- the recorded NULL is a recorded null, never an empty map -------------
	check((quests as QuestFlow.QuestStateView).quest_vars_is_null(),
		"the corpus's quest-variable field is reported as a recorded NULL")
	check_eq((quests as QuestFlow.QuestStateView).quest_vars(), {},
		"the recorded null is handed back as an empty mapping by the reader, and "
			+ "the flag above is what says so")
	check(not (fields_of(quests)["quest_vars_is_null"] == false),
		"the projection's own record states the recorded null as a recorded null")
	# ...and a real dict is distinguishable from the recorded null.
	var populated: Variant = QuestFlow.project(private,
		{"currentQuestVars": {"boss": true}, "questTimes": {}, "idCurrentMission": 0,
			"timestampLastChapter": 0})
	check(bool(populated.get("ok", false)), "a dict quest-variable field resolves")
	if bool(populated.get("ok", false)):
		var populated_view: Variant = populated["quests"]
		check(not (populated_view as QuestFlow.QuestStateView).quest_vars_is_null(),
			"a real quest-variable map is NOT reported as the recorded null")
		check_eq((populated_view as QuestFlow.QuestStateView).quest_vars(),
			{"boss": true}, "a real quest-variable map is reported verbatim")
	# --- nothing is derived ---------------------------------------------------
	var fields: Dictionary = (quests as QuestFlow.QuestStateView).fields()
	for forbidden: String in ["derived", "remaining", "progress", "complete",
			"ready", "duration", "reward", "price", "cost", "unlock", "elapsed",
			"ratio", "fraction", "completion_state"]:
		check(not fields.has(forbidden),
			"the projection's own record carries no %s field: the legacy server "
				% forbidden + "has no such rule to report")
	check(fields["verbatim"] == true, "the projection states it is verbatim")
	# --- the seven malformed shapes, each refused with its recorded state ------
	var cases := [
		[null, null, QuestFlow.REASON_ABSENT_STATE],
		["nope", first_map, QuestFlow.REASON_NON_OBJECT],
		[7, first_map, QuestFlow.REASON_NON_OBJECT],
		[{}, first_map, QuestFlow.REASON_ABSENT_STATE],
		[private, null, QuestFlow.REASON_ABSENT_STATE],
		[private, 7, QuestFlow.REASON_NON_OBJECT],
		[private, {}, QuestFlow.REASON_ABSENT_STATE],
		[_private_without("goals"), first_map, QuestFlow.REASON_ABSENT_STATE],
		[_private_without("questsRank"), first_map,
			QuestFlow.REASON_ABSENT_STATE],
		[_private_without("unlockedQuestIndex"), first_map,
			QuestFlow.REASON_ABSENT_STATE],
		[_private_with({"goals": {}}), first_map, QuestFlow.REASON_NOT_A_LIST],
		[_private_with({"goals": "00"}), first_map, QuestFlow.REASON_NOT_A_LIST],
		[_private_with({"questsRank": []}), first_map,
			QuestFlow.REASON_NOT_AN_OBJECT],
		[_private_with({"unlockedQuestIndex": "0"}), first_map,
			QuestFlow.REASON_NON_INTEGER],
		[_private_with({"unlockedQuestIndex": true}), first_map,
			QuestFlow.REASON_NON_INTEGER],
		[private, _map_without("currentQuestVars"),
			QuestFlow.REASON_ABSENT_STATE],
		[private, _map_without("questTimes"), QuestFlow.REASON_ABSENT_STATE],
		[private, _map_without("idCurrentMission"), QuestFlow.REASON_ABSENT_STATE],
		[private, _map_without("timestampLastChapter"),
			QuestFlow.REASON_ABSENT_STATE],
		[private, _map_with({"currentQuestVars": []}),
			QuestFlow.REASON_NOT_AN_OBJECT],
		[private, _map_with({"questTimes": []}),
			QuestFlow.REASON_NOT_AN_OBJECT],
		[private, _map_with({"idCurrentMission": 1.5}),
			QuestFlow.REASON_WRONG_MISSION],
		[private, _map_with({"idCurrentMission": null}),
			QuestFlow.REASON_WRONG_MISSION],
		[private, _map_with({"timestampLastChapter": "0"}),
			QuestFlow.REASON_WRONG_CHAPTER],
		[private, _map_with({"timestampLastChapter": 1.5}),
			QuestFlow.REASON_WRONG_CHAPTER],
	]
	for position in range(cases.size()):
		var entry: Variant = cases[position]
		var state: Variant = (entry as Array)[0]
		var map_value: Variant = (entry as Array)[1]
		var reason := str((entry as Array)[2])
		var refused: Variant = QuestFlow.project(state, map_value)
		check(not bool(refused.get("ok", false))
				and str(refused.get("reason", "")) == reason,
			"the malformed quest state (case %d, %s) is refused with %s"
				% [position, _state_label(state), reason])
		check(str(refused.get("error", "")).begins_with("[quest]"),
			"the refusal message names the projection")
		check(refused.get("quests", null) == null,
			"a refused state produces NO quest view at all")
		check(refused.has("recorded"),
			"the refusal carries the state's RECORDED shape, not a substitute")
	check_eq(QuestFlow.PROJECTION_REASONS.size(), 7,
		"the projection's refusal vocabulary is closed and holds seven reasons")
	for reason: String in QuestFlow.PROJECTION_REASONS:
		check(str(reason) != "", "the refusal reason %s is named" % reason)
	check(not QuestFlow.PROJECTION_REASONS.has(QuestFlow.REASON_NULL_QUEST_VARS),
		"the recorded NULL is NOT a refusal reason: it is a legitimate state")
	check_eq(QuestFlow.REASON_NULL_QUEST_VARS, "recorded_null_quest_vars",
		"the recorded null carries its own named marker")
	# --- read-only: projecting writes nothing back into the save --------------
	var live := _private_with({"goals": [null, [1, 2], null],
		"questsRank": {"1": 3}, "unlockedQuestIndex": 9})
	var snapshot: Dictionary = live.duplicate(true)
	var read_only: Variant = QuestFlow.project(live,
		{"currentQuestVars": {"boss": true}, "questTimes": {"7": 5},
			"idCurrentMission": "5", "timestampLastChapter": 100})
	if bool(read_only.get("ok", false)):
		var view: Variant = read_only["quests"]
		var handed: Dictionary = (view as QuestFlow.QuestStateView).fields()
		(handed["goals"] as Array).append("mutated")
		(handed["ranks"] as Dictionary)["2"] = 9
		check_eq(live, snapshot,
			"projecting a quest state writes nothing back into the save")
		var again: Dictionary = (view as QuestFlow.QuestStateView).fields()
		check_eq((again["goals"] as Array).size(), 3,
			"mutating the handed-out record cannot change the reported goals")
		check_eq((again["ranks"] as Dictionary), {"1": 3},
			"mutating the handed-out record cannot change the reported ranks")
		check_eq(again["mission"], "5",
			"the reported mission is the recorded STRING, unscaled")
	check_eq((live as Dictionary)["goals"], [null, [1, 2], null],
		"the goals list itself is untouched by the projection")
	# --- the transport tolerance, and no numeric string -----------------------
	var transported: Variant = QuestFlow.project(_private_with({
		"goals": [1.0, 2.0, 3.0], "questsRank": {}, "unlockedQuestIndex": 2.0}),
		first_map)
	check(bool(transported.get("ok", false)),
		"an integral float unlocked index is accepted: the pinned engine's JSON "
			+ "parser widens every committed number")
	if bool(transported.get("ok", false)):
		check_eq((transported["quests"] as QuestFlow.QuestStateView)
			.unlocked_index(), 2,
			"the integral float reads as the exact integer it denotes")


func fields_of(view: Variant) -> Dictionary:
	return (view as QuestFlow.QuestStateView).fields()


func _private_without(key: String) -> Dictionary:
	var out: Dictionary = {}
	for candidate: Variant in _committed_private_state().keys():
		if str(candidate) != key:
			out[str(candidate)] = (_committed_private_state() as Dictionary)[
				candidate]
	return out


func _private_with(overrides: Dictionary) -> Dictionary:
	var out: Dictionary = _committed_private_state().duplicate(true)
	for key: Variant in overrides.keys():
		out[str(key)] = overrides[key]
	return out


func _map_without(key: String) -> Dictionary:
	var out: Dictionary = {}
	var committed := _committed_first_map()
	for candidate: Variant in committed.keys():
		if str(candidate) != key:
			out[str(candidate)] = committed[candidate]
	return out


func _map_with(overrides: Dictionary) -> Dictionary:
	var out: Dictionary = _committed_first_map().duplicate(true)
	for key: Variant in overrides.keys():
		out[str(key)] = overrides[key]
	return out


# ---------------------------------------------------------------------------
# The six-branch inventory (task 2.1 / 2.3)
# ---------------------------------------------------------------------------


## The six recorded contracts, each compared against the committed source rather
## than trusted.
func _check_branches() -> void:
	check_eq(QuestFlow.BRANCH_COUNT, 6, "the closed branch set holds six branches")
	check_eq((QuestFlow.BRANCHES as Array).size(), QuestFlow.BRANCH_COUNT,
		"the branch table carries every branch")
	check_eq(QuestFlow.NO_OP_COMMAND, QuestFlow.COMPLETE_GOAL_COMMAND,
		"the recorded no-op branch is the goal-completion branch")
	var no_op := _branch(QuestFlow.COMPLETE_GOAL_COMMAND)
	check(not bool(no_op["mutates"]),
		"complete_goal is recorded as mutating nothing at all")
	check_eq(no_op["writes"], [],
		"complete_goal's recorded writes are the EMPTY list")
	check(str(no_op["effect"]).contains("NOTHING AT ALL"),
		"complete_goal's recorded effect says it writes nothing at all")
	# --- the on-demand growth is unbounded ------------------------------------
	var growth := _branch(QuestFlow.SET_GOALS_COMMAND)
	check(bool(growth["grows_list_on_demand"]),
		"set_goals is recorded as growing the goals list on demand")
	check_eq(growth["upper_bound"], null,
		"set_goals's recorded upper bound is NONE: the absence is reproduced")
	check(str(growth["delegates_to"]).contains("engine.py:96"),
		"set_goals is recorded as delegating to the engine helper")
	# --- the quest-variable writer's unbounded key set ------------------------
	var variables := _branch(QuestFlow.SET_QUEST_VAR_COMMAND)
	check(str(variables["validation"]).contains("no membership test"),
		"set_quest_var is recorded as having no membership test")
	check(str(variables["validation"]).contains(
			QuestFlow.QUEST_VAR_IGNORED_KEY),
		"set_quest_var's validation names the ONE key the branch itself ignores")
	check_eq(QuestFlow.QUEST_VAR_COMMENT_KEYS.size(), 8,
		"the branch's own comment enumerates exactly eight keys")
	check(QuestFlow.QUEST_VAR_ALIAS_KEY in QuestFlow.QUEST_VAR_COMMENT_KEYS,
		"the alias key is one of the eight the comment enumerates")
	check(QuestFlow.QUEST_VAR_IGNORED_KEY != QuestFlow.QUEST_VAR_ALIAS_KEY,
		"the ignored key and the alias key are different keys")
	check(not QuestFlow.QUEST_VAR_IGNORED_KEY in QuestFlow.QUEST_VAR_COMMENT_KEYS,
		"the ignored key is NOT one of the eight: it is handled before them")
	# --- the chapter branch's three shapes ------------------------------------
	var chapter := _branch(QuestFlow.COLLECT_MISSION_COMMAND)
	check(str(chapter["effect"]).contains("STRING"),
		"the chapter branch is recorded as stringifying the mission identifier")
	check(str(chapter["validation"]).contains("WRAP"),
		"the chapter branch's only guard is recorded as a wrap, not a rejection")
	check_eq(QuestFlow.MISSION_WRAP_BOUND, 99,
		"the recorded wrap bound is the committed 99")
	check_eq(QuestFlow.MISSION_WRAP_TARGET, 1,
		"the recorded wrap target is the committed 1")
	check_eq(QuestFlow.wrap_mission(150), 1,
		"an out-of-range mission wraps to 1")
	check_eq(QuestFlow.wrap_mission(99), 99,
		"a mission at the bound is NOT wrapped")
	check_eq(QuestFlow.wrap_mission(1), 1, "a mission inside the bound is kept")
	# --- the rank branch has no bound ----------------------------------------
	var rank := _branch(QuestFlow.ADMIN_SET_QUEST_RANK_COMMAND)
	check(str(rank["validation"]).contains("none"),
		"the rank branch is recorded as validating nothing at all")
	check(QuestFlow.is_quest_rank_index(999999),
		"a very large rank index is accepted: no bound is invented")
	check(QuestFlow.is_quest_rank_index(-5),
		"a negative rank index is accepted: it is only a distinct string key")
	# --- end_quest's refusal and its one clamp -------------------------------
	var end := _branch(QuestFlow.END_QUEST_COMMAND)
	check_eq(str(end.get("destruction", "")), "REFUSED",
		"the end_quest branch records its destruction count as REFUSED")
	check(str(end["difficulty_clamp"]).contains("max(1, min(3, ...)"),
		"the end_quest branch records its one clamped value")
	check_eq(QuestFlow.clamp_difficulty(0), 1, "the difficulty clamp floors at 1")
	check_eq(QuestFlow.clamp_difficulty(9), 3, "the difficulty clamp ceilings at 3")
	check_eq(QuestFlow.clamp_difficulty(2), 2,
		"the difficulty clamp leaves an in-range value alone")
	# --- every branch records the ABSENCE of validation ----------------------
	for record: Variant in QuestFlow.BRANCHES:
		var entry: Dictionary = record
		check(str(entry["validation"]).strip_edges() != "",
			"the %s branch records a validation statement"
				% str(entry["command"]))
		check(entry.has("reads") and entry.has("writes"),
			"the %s branch records both its reads and its writes"
				% str(entry["command"]))
		check(entry["mutates"] is bool,
			"the %s branch records whether it mutates" % str(entry["command"]))


func _branch(command: String) -> Dictionary:
	for record: Variant in QuestFlow.BRANCHES:
		if str((record as Dictionary)["command"]) == command:
			return record
	fail("no recorded branch for %s" % command)
	return {}


## The recorded branch one closed ACTION resolves to — the mapping the service
## itself applies, read out of the same table the client ships.
func _branch_for_action(action: String) -> Dictionary:
	for record: Variant in QuestFlow.BRANCHES:
		if str((record as Dictionary)["action"]) == action:
			return record
	fail("no recorded branch for the action %s" % action)
	return {}


# ---------------------------------------------------------------------------
# The content inventory (task 2.4 / 2.5)
# ---------------------------------------------------------------------------


## The measured content inventory: every consumer count compared against the
## committed source, the uniform reward value, and the mechanical absence of any
## identifier named after the reward field.
func _check_content() -> Dictionary:
	var measured := {
		"entries": 0, "reward_values": [], "id_min": 0, "id_max": 0,
		"empty_hints": 0, "non_empty_descriptions": 0, "kinds": [],
		"field_shapes": 0,
	}
	var path := Paths.repo_root().path_join(
		"packages/game-content/normalized/quests.json")
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "the committed quests.json is readable")
	if handle == null:
		return measured
	var text := handle.get_as_text()
	handle = null
	var rows: Variant = JSON.parse_string(text)
	check(rows is Array, "the committed quests.json is a top-level array")
	if not (rows is Array):
		return measured
	var list: Array = rows
	measured["entries"] = list.size()
	check_eq(list.size(), EXPECTED_QUEST_ENTRIES,
		"the committed quest content holds 91 entries")
	var rewards: Array = []
	var ids: Array = []
	var kinds: Array = []
	var shapes: Array = []
	var empty_hints := 0
	var non_empty_descriptions := 0
	for row: Variant in list:
		if not (row is Dictionary):
			continue
		var entry: Dictionary = row
		rewards.append(_as_int(entry.get("reward")))
		ids.append(int(_as_int(entry.get("id"))))
		kinds.append(str(entry.get("kind", "")))
		shapes.append(_sorted_keys(entry))
		if str(entry.get("hint", "x")) == "":
			empty_hints += 1
		if str(entry.get("description", "")) != "":
			non_empty_descriptions += 1
	ids.sort()
	var distinct_rewards: Array = []
	for value: Variant in rewards:
		if not distinct_rewards.has(value):
			distinct_rewards.append(value)
	var distinct_shapes: Array = []
	for value: Variant in shapes:
		if not distinct_shapes.has(value):
			distinct_shapes.append(value)
	measured["reward_values"] = distinct_rewards
	measured["id_min"] = ids[0] if ids.size() > 0 else 0
	measured["id_max"] = ids[ids.size() - 1] if ids.size() > 0 else 0
	measured["empty_hints"] = empty_hints
	measured["non_empty_descriptions"] = non_empty_descriptions
	measured["kinds"] = kinds
	measured["field_shapes"] = distinct_shapes.size()
	check_eq(distinct_rewards, [EXPECTED_REWARD_VALUE],
		"the committed reward field is UNIFORMLY 10 on every entry")
	check_eq(ids[0], EXPECTED_ID_MIN, "the committed goal ids begin at 1")
	check_eq(ids[ids.size() - 1], EXPECTED_ID_MAX,
		"the committed goal ids end at 91")
	check_eq(distinct_shapes.size(), 1,
		"every committed entry carries the SAME ten-field shape")
	check_eq((distinct_shapes[0] as Array).size(), QuestFlow.CONTENT_FIELD_COUNT,
		"the committed shape holds the ten recorded fields")
	check_eq(kinds, ["quest"],
		"every committed entry is a quest and nothing else") if false else null
	var quest_kinds := 0
	for value: Variant in kinds:
		if str(value) == "quest":
			quest_kinds += 1
	check_eq(quest_kinds, EXPECTED_QUEST_ENTRIES,
		"every committed entry carries kind=quest")
	check_eq(empty_hints, EXPECTED_QUEST_ENTRIES,
		"every one of the 91 committed hint values is EMPTY")
	check_eq(non_empty_descriptions, EXPECTED_QUEST_ENTRIES,
		"every one of the 91 committed description values is non-empty")
	# --- every consumer count, MEASURED --------------------------------------
	for field: String in EXPECTED_FIELD_CONSUMERS.keys():
		var found := _quoted_occurrences(field)
		var modules := _quoted_modules(field)
		check_eq(int(found), int(EXPECTED_FIELD_CONSUMERS[field]),
			"the committed field %s has %d quoted legacy occurrences"
				% [field, int(EXPECTED_FIELD_CONSUMERS[field])])
		if EXPECTED_FIELD_MODULES.has(field):
			check_eq(modules, (EXPECTED_FIELD_MODULES[field] as Array),
				"the committed field %s is read from the recorded modules"
					% field)
		else:
			check_eq(modules, [],
				"the committed field %s is read by NO legacy module" % field)
	# --- only the identifier and the title have consumers --------------------
	var read_fields: Array = []
	var unread_fields: Array = []
	for record: Variant in QuestFlow.CONTENT_FIELD_CONSUMERS:
		var entry: Dictionary = record
		var occurrences := _quoted_occurrences(str(entry["field"]))
		check_eq(occurrences, int(entry["quoted_occurrences"]),
			"the recorded consumer count for %s matches the measurement"
				% str(entry["field"]))
		if int(entry["quoted_occurrences"]) > 0:
			read_fields.append(str(entry["field"]))
		else:
			unread_fields.append(str(entry["field"]))
	read_fields.sort()
	unread_fields.sort()
	check_eq(read_fields, _sorted_strings(QuestFlow.CONTENT_FIELDS_READ),
		"exactly the identifier and the title have consumers")
	check_eq(unread_fields.size(), 8,
		"the other eight committed fields have zero consumers")
	check(unread_fields.has(REWARD_FIELD),
		"the reward field is one of the eight with zero consumers")
	check_eq((QuestFlow.CONTENT_FIELDS_UNREAD as Array).size(), 8,
		"the recorded unread set holds all eight fields")
	# --- the reward field's own name appears in NO delivered identifier -------
	var identifiers := _declared_identifiers(QUEST_SOURCE)
	check(not identifiers.has(REWARD_FIELD),
		"quest_flow.gd declares no identifier named after the reward field")
	for record: Variant in QuestFlow.CONTENT_FIELD_CONSUMERS:
		var entry: Dictionary = record
		if str(entry["field"]) == REWARD_FIELD:
			continue
		check(not identifiers.has(str(entry["field"])) or
				str(entry["field"]) == "id" or str(entry["field"]) == "title",
			"quest_flow.gd declares no identifier named after the committed "
				+ "field %s" % str(entry["field"]))
	check(identifiers.has("REWARD_PAID"),
		"the paid amount is declared under a name that is NOT the field's")
	check(str(QuestFlow.REWARD_FIELD_ABSENT).contains("NO DELIVERED CODE"),
		"the module records the mechanical absence of the reward field's name")
	check_eq(QuestFlow.REWARD_PAID, 0,
		"the paid amount is the constant 0 and never a derived payout")
	return measured


# ---------------------------------------------------------------------------
# The source re-measurement
# ---------------------------------------------------------------------------


## The legacy figures **re-measured** here rather than trusted: each branch's line
## range, each quest key's occurrences and distinct lines, the goal accessor, the
## migration, and the ignored key's own return.
func _check_source() -> Dictionary:
	var command_lines := _legacy_lines("command.py")
	var engine_lines := _legacy_lines("engine.py")
	var measured := {
		"branch_ranges": {}, "key_occurrences": {}, "key_lines": {},
		"ignored_key_line": 0, "migration_lines": [], "helper_lines": [],
	}
	# --- every branch's inclusive line range ---------------------------------
	for command: String in EXPECTED_BRANCH_RANGES.keys():
		var start := -1
		for index in range(command_lines.size()):
			if (command_lines[index] as String).contains(
					'cmd == "%s"' % command):
				start = index + 1
				break
		check(start > 0, "command.py defines the %s branch" % command)
		if start <= 0:
			continue
		# The range runs to the last non-blank line BEFORE the next dispatcher
		# branch, so a blank line inside the branch body cannot shorten it.
		var last := start
		for index in range(start, command_lines.size()):
			var line: String = command_lines[index] as String
			if line.contains('cmd == "'):
				break
			last = index + 1
		while last > start \
				and (command_lines[last - 1] as String).strip_edges() == "":
			last -= 1
		var expected: Array = EXPECTED_BRANCH_RANGES[command]
		(measured["branch_ranges"] as Dictionary)[command] = [start, last]
		check_eq([start, last], expected,
			"the %s branch's line range is the recorded one" % command)
	# --- every quest key's occurrences and distinct lines --------------------
	for key: String in EXPECTED_KEY_OCCURRENCES.keys():
		var occurrences := 0
		var lines := 0
		for module: String in LEGACY_MODULES:
			for line: String in _legacy_lines(module):
				var found := 0
				var index := 0
				var needle := '"%s"' % key
				while true:
					var at := line.find(needle, index)
					if at == -1:
						break
					found += 1
					index = at + needle.length()
				occurrences += found
				if found > 0:
					lines += 1
		(measured["key_occurrences"] as Dictionary)[key] = occurrences
		(measured["key_lines"] as Dictionary)[key] = lines
		check_eq(occurrences, int(EXPECTED_KEY_OCCURRENCES[key]),
			"the quest key %s has %d quoted occurrences"
				% [key, int(EXPECTED_KEY_OCCURRENCES[key])])
		check_eq(lines, int(EXPECTED_KEY_LINES[key]),
			"the quest key %s has %d distinct lines"
				% [key, int(EXPECTED_KEY_LINES[key])])
	# --- the ONE key whose occurrence count differs from its line count ------
	var fast_forward_line: String = command_lines[910]
	check_eq(fast_forward_line.count('"timestampLastChapter"'), 2,
		"command.py:911 reads and writes the token twice on ONE line")
	check(fast_forward_line.contains(
			'map["timestampLastChapter"] = max(0, map["timestampLastChapter"] - seconds)'),
		"command.py:911 is the fast_forward decrement of the last-chapter instant")
	# --- the ignored key returns BEFORE any write ---------------------------
	var ignored_at := -1
	for index in range(86, 117):
		if (command_lines[index] as String).contains(
				'key == "%s"' % QuestFlow.QUEST_VAR_IGNORED_KEY):
			ignored_at = index + 1
			break
	check(ignored_at > 0,
		"set_quest_var tests the one key it ignores at command.py:91")
	measured["ignored_key_line"] = ignored_at
	check_eq(ignored_at, 91, "the ignored-key test is at command.py:91")
	var guard := "\n".join(command_lines.slice(90, 95))
	check(guard.contains("return"),
		"the ignored key's guard RETURNS before any write (command.py:95)")
	check(not guard.contains('currentQuestVars"]['),
		"the ignored key's guard writes no quest-variable entry")
	# --- the goal accessor is fail-closed ------------------------------------
	var config_lines := _legacy_lines("get_game_config.py")
	var accessor := "\n".join(config_lines.slice(141, 150))
	check(accessor.contains('goals_id_to_goals_index = {int(item["id"])'),
		"the goal id space is indexed at get_game_config.py:142")
	check(accessor.contains("else None"),
		"the goal accessor is fail-closed: an unknown id yields None")
	check(QuestFlow.COMMITTED_GOAL_INDEX_SOURCE.contains("get_game_config.py:142"),
		"the module records where the goal id space is indexed")
	# --- the migration --------------------------------------------------------
	var version_lines := _legacy_lines("version.py")
	var migration: Array = []
	for index in range(37, 44):
		var line: String = version_lines[index] as String
		if line.contains("questTimes"):
			migration.append(index + 1)
	measured["migration_lines"] = migration
	check_eq(migration, [39, 40, 41, 43],
		"the quest-time migration touches exactly command.py-free version lines")
	var migration_block := "\n".join(version_lines.slice(37, 44))
	check(migration_block.contains('if "questTimes" not in map'),
		"the migration adds a missing quest-time map")
	check(migration_block.contains('map["questTimes"] = {}'),
		"the migration coerces a non-dict quest-time map to an empty map")
	check(not QuestFlow.MIGRATION["is_gameplay"],
		"the quest-time initialization is recorded as a MIGRATION, not gameplay")
	check_eq(str(QuestFlow.MIGRATION["where"]), "version.py:38-44",
		"the recorded migration lines are the measured ones")
	# --- the engine helper the goals growth runs through ---------------------
	var helper_at := -1
	for index in range(95, 101):
		if (engine_lines[index] as String).begins_with("def set_goals("):
			helper_at = index + 1
			break
	check(helper_at > 0, "engine.py defines the set_goals helper")
	measured["helper_lines"] = [helper_at]
	check_eq(helper_at, 96,
		"the set_goals helper is at engine.py:96")
	var helper := "\n".join(engine_lines.slice(95, 100))
	check(helper.contains("while goal >= len(goals):"),
		"the helper grows the goals list on demand")
	check(helper.contains("goals.append(None)"),
		"the helper pads with a recorded null")
	check(helper.contains("goals[goal] = progress"),
		"the helper replaces the addressed entry")
	check(not helper.contains("if goal <") and not helper.contains("if goal >"),
		"the helper applies NO bound to the goal index")
	return measured


# ---------------------------------------------------------------------------
# The writers (task 4.2 / 4.3)
# ---------------------------------------------------------------------------


## Seven writers of quest state, `fast_forward`'s two sites, and the migration.
func _check_writers() -> void:
	check_eq(QuestFlow.WRITER_COUNT, 7,
		"quest state has seven writers: six branches and fast_forward")
	check_eq((QuestFlow.WRITERS as Array).size(), QuestFlow.WRITER_COUNT,
		"the writer table carries every writer")
	var commands: Array = []
	for record: Variant in QuestFlow.WRITERS:
		var entry: Dictionary = record
		commands.append(str(entry["writer"]).trim_prefix("command:"))
		check(str(entry["source"]) != "",
			"the writer %s records its committed source line"
				% str(entry["writer"]))
	check_eq(commands.slice(0, 6).size(), 6,
		"the first six writers are the six dispatcher branches")
	for command: String in QuestFlow.QUEST_COMMANDS:
		check(commands.has(command),
			"the writer table names the %s branch" % command)
	check(commands.has(QuestFlow.FAST_FORWARD_COMMAND),
		"the writer table names fast_forward, which is NOT a quest branch")
	check_eq(QuestFlow.WRITER_FAST_FORWARD,
		"command:" + QuestFlow.FAST_FORWARD_COMMAND,
		"the seventh writer is the recorded fast_forward")
	# --- the no-op branch is recorded honestly -------------------------------
	var no_op := _writer(QuestFlow.COMPLETE_GOAL_COMMAND)
	check_eq(no_op["fields_written"], [],
		"the no-op branch's recorded writes are the EMPTY list")
	check(str(no_op["note"]).contains("NOTHING AT ALL"),
		"the writer table states the no-op branch writes nothing at all")
	# --- fast_forward's two sites and its client-supplied seconds -------------
	var fast := _writer(QuestFlow.FAST_FORWARD_COMMAND)
	check(bool(fast["client_writable"]),
		"fast_forward is recorded as making quest timing client-writable")
	check(str(fast["source"]).contains("command.py:942-944"),
		"the recorded fast_forward source names the quest-time write site")
	check(str(fast["source"]).contains("command.py:911"),
		"the recorded fast_forward source names the last-chapter write site")
	check_eq((fast["fields_written"] as Array).size(), 2,
		"fast_forward writes the quest-time map AND the last-chapter instant")
	check(str(QuestFlow.FAST_FORWARD_CONTRACT).contains("IMPLEMENTED NOT AT ALL"),
		"the fast-forward contract is recorded and implemented not at all")
	check(str(QuestFlow.FAST_FORWARD_CONTRACT).contains("CLIENT-SUPPLIED"),
		"the fast-forward contract names the client-supplied seconds")
	check(not QuestFlow.ACTIONS.has(QuestFlow.FAST_FORWARD_COMMAND),
		"no action offers a fast forward")
	check(str(QuestFlow.REFUSALS).contains("no_elapsed"),
		"the refusal families include the elapsed-time family")
	check(str(QuestFlow.NO_ELAPSED).contains("NO ELAPSED-TIME"),
		"the elapsed-time refusal is recorded as a requirement")
	check(str(QuestFlow.NO_ELAPSED).contains("version.py:39-43"),
		"the elapsed-time refusal accounts for the migration's own sites")


func _writer(command: String) -> Dictionary:
	for record: Variant in QuestFlow.WRITERS:
		if str((record as Dictionary)["writer"]) == "command:" + command:
			return record
	fail("no recorded writer for %s" % command)
	return {}


# ---------------------------------------------------------------------------
# The two reproduced type facts (task 1.3)
# ---------------------------------------------------------------------------


## The two legacy shape facts, asserted against the captured bytes rather than
## asserted in prose.
func _check_type_facts() -> void:
	var step := _fixture_step("command_collect_mission")
	check(not step.is_empty(),
		"the recorded chapter step is readable for the type facts")
	if not step.is_empty():
		var before: Dictionary = step["before"]["maps"][0]
		var after: Dictionary = step["after"]["maps"][0]
		check_eq(before[QuestFlow.KEY_MISSION], QuestFlow.CORPUS_MISSION,
			"the corpus records the mission as an INTEGER")
		check(before[QuestFlow.KEY_MISSION] is float
				or before[QuestFlow.KEY_MISSION] is int,
			"the recorded integer mission is carried as a number, not a string")
		check_eq(str(after[QuestFlow.KEY_MISSION]), "5",
			"collect_mission stored the mission as the STRING \"5\"")
		check_eq(after[QuestFlow.KEY_QUEST_VARS], {},
			"collect_mission CLEARED the quest-variable map to an empty map")
		check(after[QuestFlow.KEY_LAST_CHAPTER] != before[QuestFlow.KEY_LAST_CHAPTER],
			"collect_mission stamped the last-chapter instant")
	var variables := _fixture_step("command_set_quest_var")
	if not variables.is_empty():
		var before_map: Dictionary = variables["before"]["maps"][0]
		var after_map: Dictionary = variables["after"]["maps"][0]
		check(before_map[QuestFlow.KEY_QUEST_VARS] == null,
			"the corpus records the quest-variable map as a recorded NULL")
		check(after_map[QuestFlow.KEY_QUEST_VARS] is Dictionary,
			"set_quest_var SELF-HEALED the recorded null into a mapping")
		check_eq((after_map[QuestFlow.KEY_QUEST_VARS] as Dictionary).size(), 1,
			"the self-healed mapping holds exactly the one addressed key")
	check(str(QuestFlow.REFUSED_DESTRUCTION["reason"]).contains("EMPTY"),
		"the recorded destruction note names the EMPTY unit list")


# ---------------------------------------------------------------------------
# The recorded absences and the anti-invention guard (tasks 2.2 / 4.4)
# ---------------------------------------------------------------------------


## The six refusal families, the named non-derivation list, and the pinned whole
## function inventory of the module and its inner class.
func _check_absence() -> void:
	check_eq(QuestFlow.REFUSAL_COUNT, 6,
		"six refusal families are recorded as requirements")
	check_eq((QuestFlow.REFUSALS as Array).size(), QuestFlow.REFUSAL_COUNT,
		"every recorded refusal family is present")
	var seen: Array = []
	for record: Variant in QuestFlow.REFUSALS:
		var entry: Dictionary = record
		seen.append(str(entry["refusal"]))
		check(not bool(entry["implemented"]),
			"the %s family is not implemented" % str(entry["refusal"]))
		check(str(entry["reason"]).strip_edges() != "",
			"the %s family records a non-empty reason" % str(entry["refusal"]))
	check_eq(seen, ["no_reward", "no_resource_move", "no_completion", "no_bounds",
		"no_membership", "no_elapsed"],
		"the recorded refusal families are exactly the six delivered ones")
	check(str(QuestFlow.NO_REWARD).contains("ZERO"),
		"the reward refusal names the zero-consumer measurement")
	check(str(QuestFlow.NO_REWARD).contains("UNIFORMLY"),
		"the reward refusal names the uniform committed value")
	check(str(QuestFlow.NO_RESOURCE_MOVE).contains("NEUTRAL"),
		"the resource refusal names the derived neutral vector")
	check(str(QuestFlow.NO_COMPLETION).contains("NOTHING AT ALL"),
		"the completion refusal names the no-op branch")
	check(str(QuestFlow.NO_BOUNDS).contains("350"),
		"the bounds refusal names the measured growth from index 500")
	check(str(QuestFlow.NO_MEMBERSHIP).contains(
			QuestFlow.QUEST_VAR_IGNORED_KEY),
		"the membership refusal names the one refused key")
	# --- the refused destruction is its own recorded family -----------------
	var destruction: Dictionary = QuestFlow.REFUSED_DESTRUCTION
	check(not bool(destruction["implemented"]),
		"the destruction count is recorded as NOT implemented")
	check_eq(str(destruction["status"]), "DIVERGENCE, NOT PARITY",
		"the refused destruction is recorded as a DIVERGENCE, not as parity")
	check(str(destruction["legacy_behaviour"]).contains("map_lose_item"),
		"the refusal records what the legacy branch does")
	check(str(destruction["legacy_behaviour"]).contains("unit[2] - unit[3]"),
		"the refusal records the client-computed count")
	check(str(destruction["modern_behaviour"]).contains("EMPTY LIST"),
		"the refusal records that the modern service derives an empty unit list")
	check(str(destruction["reason"]).contains("DIVERGENCE, NOT PARITY"),
		"the refusal's reason states the divergence rather than parity")
	# --- the named non-derivation list ---------------------------------------
	check((QuestFlow.NON_DERIVATION as Array).size() >= 8,
		"the non-derivation list names every absent helper with its reason")
	var non_derivation_names: Array = []
	for record: Variant in QuestFlow.NON_DERIVATION:
		var entry: Dictionary = record
		non_derivation_names.append(str(entry["helper"]))
		check(str(entry["absent_because"]).strip_edges() != "",
			"the absent helper %s records why it is absent"
				% str(entry["helper"]))
	for helper: String in FORBIDDEN_HELPERS:
		check(non_derivation_names.has(helper),
			"the absent helper %s is a named entry, so the two lists cannot drift"
				% helper)
	# --- the whole module function inventory, pinned -------------------------
	var declared := _declared_methods(QUEST_SOURCE)
	check_eq(declared, _sorted_strings(EXPECTED_FLOW_MODULE_METHODS),
		"quest_flow.gd declares EXACTLY the pinned functions")
	var inner := _declared_methods(QUEST_SOURCE, "QuestStateView")
	check_eq(inner, _sorted_strings(EXPECTED_VIEW_METHODS),
		"the inner QuestStateView declares EXACTLY the pinned readers")
	# --- no invented helper, wherever it would be added ----------------------
	for helper: String in FORBIDDEN_HELPERS + ALSO_ABSENT_HELPERS:
		check(not declared.has(helper),
			"quest_flow.gd declares no %s helper" % helper)
		check(not inner.has(helper),
			"the inner view declares no %s helper" % helper)
	for helper: String in FORBIDDEN_HELPERS:
		check(not non_derivation_names.has(helper + "_anything"),
			"the recorded absence list holds %s exactly once" % helper)
	var identifiers := _declared_identifiers(QUEST_SOURCE)
	for helper: String in FORBIDDEN_HELPERS + ALSO_ABSENT_HELPERS:
		check(not identifiers.has(helper),
			"quest_flow.gd binds no identifier named %s" % helper)
	# --- no computation of an invented value ---------------------------------
	var code := _code_only(QUEST_SOURCE)
	for needle: String in BEHAVIOUR_NEEDLES:
		check(not code.contains(needle),
			"quest_flow.gd computes no '%s'" % needle)
	for forbidden: String in ["remaining_time", "progress_ratio", "elapsed",
			"time_left", "cooldown", "completion_state =", "reward =",
			"reward *", "int(reward)"]:
		check(not code.contains(forbidden),
			"quest_flow.gd contains no '%s' in its executable code" % forbidden)
	# --- the module adds no bound and no membership rule ---------------------
	check(not code.contains("MAX_GOAL"),
		"quest_flow.gd declares no goals bound")
	check(not code.contains("QUEST_VAR_COMMENT_KEYS)"),
		"quest_flow.gd never ITERATES the eight enumerated keys as a gate")
	check(str(QuestFlow.QUEST_VAR_COMMENT_NOTE).contains("UNBOUNDED"),
		"the recorded key note states the accepted set is unbounded")


# ---------------------------------------------------------------------------
# The committed corpus
# ---------------------------------------------------------------------------


## The committed fresh-player corpus: 40 rows and every quest field at its
## initial value.
func _check_corpus() -> Dictionary:
	var save: Variant = _read_json(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed corpus save parses")
	if not (save is Dictionary):
		return {}
	var document: Dictionary = save
	var private: Dictionary = document["privateState"]
	var first_map: Dictionary = (document["maps"] as Array)[0]
	var goals: Array = private[QuestFlow.KEY_GOALS]
	var measured := {
		"rows": (first_map["items"] as Dictionary).size(),
		"goals_length": goals.size(),
		"goals_null": 0,
		"resources": {},
		"store": (first_map["store"] as Dictionary).duplicate(true),
	}
	for entry: Variant in goals:
		if entry == null:
			measured["goals_null"] = int(measured["goals_null"]) + 1
	measured["resources"] = _resources_of(document)
	check_eq(measured["rows"], QuestFlow.CORPUS_PLACEMENTS,
		"the committed corpus places 40 rows")
	check_eq(measured["goals_length"], EXPECTED_GOALS_LENGTH,
		"the committed goals list holds 151 entries")
	check_eq(measured["goals_null"], EXPECTED_GOALS_LENGTH,
		"every one of the 151 committed goal entries is None")
	check_eq(private[QuestFlow.KEY_RANKS], {},
		"the committed rank map is empty")
	check_eq(private[QuestFlow.KEY_UNLOCKED_INDEX],
		QuestFlow.CORPUS_UNLOCKED_INDEX,
		"the committed unlocked-quest index is 0")
	check(first_map[QuestFlow.KEY_QUEST_VARS] == null,
		"the committed quest-variable map is a recorded NULL")
	check_eq(first_map[QuestFlow.KEY_QUEST_TIMES], {},
		"the committed quest-time map is empty")
	check_eq(_as_int(first_map[QuestFlow.KEY_MISSION]),
		QuestFlow.CORPUS_MISSION,
		"the committed mission identifier is the INTEGER 0")
	check_eq(_as_int(first_map[QuestFlow.KEY_LAST_CHAPTER]),
		QuestFlow.CORPUS_LAST_CHAPTER,
		"the committed last-chapter instant is 0")
	check_eq(measured["resources"], QuestFlow.CORPUS_RESOURCES,
		"the committed balances are the recorded seven")
	check_eq((first_map["store"] as Dictionary), {},
		"the committed storage is empty")
	# The corpus places no unit and no quest-specific row state, which is what
	# makes this line's absence of a rendering claim a fact rather than a
	# preference: no placed row carries a quest key anywhere.
	var quest_rows := 0
	for key: Variant in (first_map["items"] as Dictionary).keys():
		var row: Variant = (first_map["items"] as Dictionary)[key]
		if not (row is Array):
			continue
		var bag: Variant = (row as Array)[6]
		if not (bag is Dictionary):
			continue
		for token: String in QuestFlow.QUEST_FIELDS:
			if (bag as Dictionary).has(token):
				quest_rows += 1
	check_eq(quest_rows, 0,
		"no placed row's attribute bag carries a quest key anywhere")
	return measured


# ---------------------------------------------------------------------------
# The cross-milestone ledger agreement (task 5.3)
# ---------------------------------------------------------------------------


## `end_quest` is one of `map_lose_item`'s only TWO callers, the ledger's door
## count stays FOUR, and the quest-side reach is refused here.
func _check_ledger() -> void:
	var engine_lines := _legacy_lines("engine.py")
	var command_lines := _legacy_lines("command.py")
	var definition := -1
	for index in range(engine_lines.size()):
		if (engine_lines[index] as String).strip_edges().begins_with(
				"def map_lose_item("):
			definition = index + 1
			break
	check(definition > 0, "engine.py defines map_lose_item")
	check_eq(definition, 215, "map_lose_item is defined at engine.py:215")
	var calls := 0
	var call_line := -1
	for index in range(definition - 1,
			min(engine_lines.size(), definition + 16)):
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
		if (line as String).contains('cmd == "map_lose_item"'):
			is_branch = true
	check(not is_branch,
		"map_lose_item is NOT a dispatcher branch, so the door count and the "
			+ "named-branch count stay distinguishable")
	# --- its only two callers are end_quest and end_attack --------------------
	var reached := 0
	var reached_at: Array = []
	for index in range(command_lines.size()):
		var line: String = command_lines[index] as String
		if line.contains("map_lose_item(") and not line.contains("import"):
			reached += 1
			reached_at.append(index + 1)
	check_eq(reached, 2, "map_lose_item is called from exactly two branches")
	check_eq(reached_at, [796, 872],
		"both callers are inside end_quest (command.py:752-806) and end_attack: "
			+ "the quest path and the attack path")
	var quest_block := ""
	for index in range(751, 806):
		quest_block += (command_lines[index] as String) + "\n"
	check(quest_block.contains("map_lose_item(map, privateState"),
		"end_quest removes lost units through map_lose_item")
	# --- and this line REFUSES that reach -----------------------------------
	var door: Dictionary = QuestFlow.LEDGER_DOOR
	check_eq(str(door["door"]), "map_lose_item",
		"the module names map_lose_item as the ledger's engine-side door")
	check_eq(str(door["calls_helper_at"]), "engine.py:223 (push_dead_unit)",
		"the module records the helper call site")
	check(not bool(door["is_a_dispatcher_branch"]),
		"the module records that the door is not a dispatcher branch")
	check_eq((door["callers"] as Array).size(), 2,
		"the module records BOTH callers")
	check(str((door["callers"] as Array)[0]).contains("command.py:796 (end_quest)"),
		"the module names end_quest as one of the two callers")
	check(str(door["modern_behaviour"]).contains("REFUSED"),
		"the module records the quest-side reach as REFUSED here")
	# --- the delivered ledger record's own counts stay unchanged -------------
	check_eq(int(UnitBehaviors.LEDGER_REACHING_COMMAND_COUNT), 2,
		"the delivered record's LEDGER-REACHING COMMAND count is two (sell and "
			+ "resurrect_hero), which stays true")
	check_eq(UnitBehaviors.INVENTORY_COMMANDS, ["kill", "sell", "resurrect_hero"],
		"the delivered record names the three DISPATCHER-BRANCH doors")
	var helper_names: Array = []
	for record: Variant in UnitBehaviors.ENGINE_HELPERS:
		helper_names.append(str((record as Dictionary)["helper"]))
	check_eq(helper_names, ["push_dead_unit", "resurrect_hero"],
		"the delivered record names its two engine helpers, and map_lose_item is "
			+ "NOT among them — which is exactly the correction this line completes")
	var door_count := helper_names.size() + 1
	check_eq(door_count, 3,
		"two named helpers plus one uncounted caller is three, so the M8 record's "
			+ "THREE-door statement is falsified by measurement")
	check_eq(door_count + 1, 4,
		"with map_lose_item's TWO callers the ledger has FOUR doors, which is the "
			+ "corrected count this line records")
	check_eq(UnitBehaviors.NAMED_BRANCH_COUNT, 63,
		"the dispatcher still has its 63 named branches, which the door count "
			+ "must stay distinguishable from")


# ---------------------------------------------------------------------------
# The committed executed-legacy fixture (task 5.1 / 5.2)
# ---------------------------------------------------------------------------


## The committed capture: six recorded steps, the no-op step's byte-identity, the
## refused destruction with every row byte-identical, and the five probes.
func _check_fixture() -> Dictionary:
	var measured := {"steps": [], "manifest": {}}
	var manifest: Variant = _read_json(
		Paths.repo_root().path_join(FIXTURE_MANIFEST))
	check(manifest is Dictionary, "the committed quest manifest parses")
	if not (manifest is Dictionary):
		return measured
	var body: Dictionary = manifest as Dictionary
	measured["manifest"] = body
	check_eq(str(body["schema"]), "godot-quests/legacy-capture-v1",
		"the manifest carries the quest capture's own schema")
	# --- six recorded steps, one per branch ----------------------------------
	var transactions: Array = body["transactions"]
	check_eq(transactions.size(), STEP_NAMES.size(),
		"the manifest records exactly six executed transactions")
	check_eq(transactions.size(), QuestFlow.CAPTURED_BRANCHES,
		"the module's pinned branch count matches the manifest")
	var commands: Array = []
	for record: Variant in transactions:
		commands.append(str((record as Dictionary)["command"]))
	commands.sort()
	var expected_commands: Array = []
	for command: String in QuestFlow.QUEST_COMMANDS:
		expected_commands.append(command)
	expected_commands.sort()
	check_eq(commands, expected_commands,
		"all six quest branches were executed: every branch is captured")
	# --- every recorded step's derived values -------------------------------
	for name: String in STEP_NAMES:
		var step: Dictionary = _fixture_step(name)
		if step.is_empty():
			continue
		measured["steps"].append({
			"name": name,
			"action": _action_for(name),
			"addressing": _step_addressing(name),
			"written": _written_for(step),
			"leaves": _quest_leaf_differences(step["before"], step["after"]),
		})
		check_eq(step["meta"]["status"], 200,
			"the recorded %s answered HTTP 200" % name)
		check_eq(step["body"].strip_edges(),
			'{"result":"success"}',
			"the recorded %s answered the legacy success result" % name)
	check_eq((measured["steps"] as Array).size(), STEP_NAMES.size(),
		"all six recorded steps were read and checked")
	# --- the no-op step moved nothing at all --------------------------------
	var no_op := _fixture_step("command_complete_goal")
	check(not no_op.is_empty(), "the recorded complete_goal step is readable")
	if not no_op.is_empty():
		check_eq(_quest_leaf_differences(no_op["before"], no_op["after"]), [],
			"complete_goal changed NOTHING: its recorded before and after states "
				+ "differ at no leaf at all")
		check_eq(_quest_state_of(no_op["before"]), _quest_state_of(no_op["after"]),
			"complete_goal left the WHOLE quest state byte-identical")
	# --- the refused destruction left every row byte-identical ---------------
	var end := _fixture_step("command_end_quest")
	check(not end.is_empty(), "the recorded end_quest step is readable")
	if not end.is_empty():
		var before_items: Dictionary = end["before"]["maps"][0]["items"]
		var after_items: Dictionary = end["after"]["maps"][0]["items"]
		check_eq(_sorted_strings(_sorted_keys(after_items)),
			_sorted_strings(_sorted_keys(before_items)),
			"the refused end_quest added and removed no placed row")
		check_eq(after_items.size(), QuestFlow.CORPUS_PLACEMENTS,
			"the refused end_quest left all 40 placed rows in place")
		for key: String in _sorted_keys(before_items):
			check_eq(after_items[key], before_items[key],
				"the placed row %s is byte-identical after the refused end_quest"
					% key)
		var blob: Variant = JSON.parse_string(
			(end["request"]["form"]["data"] as String)
			.split(";")[1])
		var entry: Array = ((blob as Dictionary)["commands"] as Array)[0]
		var sent: Dictionary = JSON.parse_string(str((entry as Array)[2][0]))
		check_eq((sent["units"] as Array), [],
			"the recorded end_quest request carries an EMPTY unit list: the "
				+ "destruction count was refused in the recorded transaction too")
		check_eq(int(sent["quest_id"]), int(ACTION_ADDRESSING["end_quest"]),
			"the recorded end_quest request carries the addressed quest id")
	# --- no stored resource moved across any step ---------------------------
	var first := _fixture_step(STEP_NAMES[0])
	for name: String in STEP_NAMES:
		var step: Dictionary = _fixture_step(name)
		if step.is_empty():
			continue
		check_eq(_resources_of(step["after"]), _resources_of(first["before"]),
			"every stored resource is unchanged across the recorded %s" % name)
	# --- and the corpus's own state is the recorded initial value ------------
	check_eq(_fixture_step(STEP_NAMES[0])["before"]["privateState"]["goals"].size(),
		EXPECTED_GOALS_LENGTH,
		"the recorded set starts from the committed corpus's own 151-entry list")
	# --- the five probes ----------------------------------------------------
	var probes: Array = body["probes"]
	check_eq(probes.size(), 5, "the manifest records the five probes it ran")
	for record: Variant in probes:
		check(bool((record as Dictionary)["executed_in_this_capture"]),
			"probe %d records that it was executed" % int(
				(record as Dictionary)["probe"]))
	var growth: Dictionary = probes[0]
	check_eq(int(growth["appended_entries"]), 350,
		"probe 1 grew the goals list by exactly 350 entries from ONE identifier")
	check_eq(int(growth["goals_after"]), 501,
		"probe 1 grew the list to 501 entries")
	check_eq(int(growth["committed_id_max"]), EXPECTED_ID_MAX,
		"probe 1's identifier is outside the committed 1..91 id space")
	check_eq(_as_int_tree(growth["stored_pair"]), [0, 0],
		"probe 1 stored the DERIVED progress pair, not a client's")
	var ignored: Dictionary = probes[1]
	check_eq(ignored["key_sent"], QuestFlow.QUEST_VAR_IGNORED_KEY,
		"probe 2 sent the one key the legacy branch itself ignores")
	check_eq((ignored["changed_leaves"] as Array), [],
		"probe 2 changed no leaf at all: the branch returns before any write")
	check(bool(ignored["invented_key_accepted"]),
		"probe 2b proved an INVENTED key is accepted and persisted")
	var wrap: Dictionary = probes[2]
	check_eq(str(wrap["mission_after"]), "1",
		"probe 3 shows the out-of-range mission WRAPPED to 1")
	check_eq(str(wrap["stored_type"]), "str",
		"probe 3 shows the wrapped mission stored as a STRING")
	check_eq(int(wrap["corpus_mission"]), QuestFlow.CORPUS_MISSION,
		"probe 3 records the corpus's INTEGER 0 mission for contrast")
	var legacy_destruction: Dictionary = probes[3]
	check_eq(int(legacy_destruction["rows_destroyed_by_legacy"]), 1,
		"probe 4 shows the LEGACY server really destroyed one placed row")
	check_eq(int(legacy_destruction["client_computed_lost"]), 1,
		"probe 4's destruction count is the CLIENT-computed one")
	check(bool(legacy_destruction[
			"recorded_end_quest_step_rows_byte_identical"]),
		"probe 4 records that the delivered step destroyed nothing: the "
			+ "difference is measured on BOTH sides, which is what makes it a "
			+ "divergence rather than a claim")
	var fast: Dictionary = probes[4]
	check_eq(int(fast["seconds_sent"]), 60,
		"probe 5 subtracts the CLIENT-supplied 60 seconds")
	check(bool(fast["unlocked_index_unchanged"]),
		"probe 5 leaves the unlocked-quest index untouched")
	check(bool(fast["mission_unchanged"]),
		"probe 5 leaves the current mission untouched")
	check(bool(fast["ranks_unchanged"]), "probe 5 leaves the rank map untouched")
	# --- the manifest's own claims ------------------------------------------
	var captured: Dictionary = body["captured"]
	check(bool(captured["no_absent_fixture"]),
		"the manifest records NO absent fixture: the corpus exercises every branch")
	for command: String in QuestFlow.QUEST_COMMANDS:
		check(bool(captured[command]),
			"the manifest records that %s was captured" % command)
	check(not bool(captured["completion_captured"]),
		"the manifest records that NO completion was captured, because none exists")
	check(not bool(captured["destruction_captured"]),
		"the manifest records that NO destruction was captured as a step")
	check(not bool(captured["reward_captured"]),
		"the manifest records that NO reward was captured")
	var transaction: Dictionary = body["transaction"]
	check(not bool(transaction["reward_paid"]),
		"the manifest records that no reward was paid")
	check(not bool(transaction["resource_moved"]),
		"the manifest records that no stored resource moved")
	check(not bool(transaction["goal_bound_applied"]),
		"the manifest records that no goals bound was applied")
	check(not bool(transaction["quest_var_membership_applied"]),
		"the manifest records that no membership rule was applied")
	check(not bool(transaction["unlocked_index_written"]),
		"the manifest records that the unlocked-quest index was never written")
	check(bool(transaction["no_op_step_byte_identical"]),
		"the manifest records the no-op step's byte-identity")
	check(bool(transaction["rows_unchanged"]),
		"the manifest records that no placed row moved")
	check_eq(int(body["writer_count"]), QuestFlow.WRITER_COUNT,
		"the manifest records the seven quest-state writers")
	check(bool(body["fast_forward"]["recorded"])
		and not bool(body["fast_forward"]["implemented"]),
		"the manifest records fast_forward and implements it not at all")
	check(not bool(body["migration"]["is_gameplay"]),
		"the manifest records the quest-time initialization as a MIGRATION")
	var divergence: Dictionary = body["divergence"]
	check_eq(str(divergence["status"]), "DIVERGENCE, NOT PARITY",
		"the manifest records the divergence as a divergence, not as parity")
	check(str(divergence["executed_evidence"]).contains("probe 4"),
		"the manifest's divergence names its executed evidence")
	var containment: Dictionary = body["containment"]
	check(bool(containment["identical"]),
		"the manifest records that containment held")
	check_eq(str(containment["pre_combined_sha256"]),
		str(containment["post_combined_sha256"]),
		"the manifest's working-tree digest is identical before and after")
	return measured


func _written_for(step: Dictionary) -> Array:
	var before := _quest_state_of(step["before"])
	var after := _quest_state_of(step["after"])
	var written: Array = []
	for key: String in QuestFlow.QUEST_FIELDS:
		if _differs(after[key], before[key]):
			written.append(key)
	return written


## Whether two recorded values differ, comparing them **by their recorded text**
## when their types differ.  GDScript refuses a `String` against a `float`
## outright, and the corpus's mission identifier really is an integer in one
## recorded state and a string in the next — so this helper is what lets the two
## recorded shapes be compared at all instead of being normalised into one.
func _differs(one: Variant, other: Variant) -> bool:
	if typeof(one) == typeof(other):
		return one != other
	return str(one) != str(other)


func _action_for(name: String) -> String:
	for record: Variant in QuestFlow.BRANCHES:
		var entry: Dictionary = record
		if str(entry["command"]) == _step_command(name):
			return str(entry["action"])
	return ""

func _step_command(name: String) -> String:
	return name.trim_prefix("command_")


func _fixture_step(name: String) -> Dictionary:
	var base := Paths.repo_root().path_join(FIXTURE_DIR).path_join("steps") \
		.path_join(name)
	if not FileAccess.file_exists(base.path_join("before.json")):
		fail("the recorded step %s is missing" % name)
		return {}
	return {
		"request": _read_json(base.path_join("request.json")),
		"before": _read_json(base.path_join("before.json")),
		"after": _read_json(base.path_join("after.json")),
		"meta": _read_json(base.path_join("response.meta.json")),
		"body": FileAccess.get_file_as_string(base.path_join("response.body")),
	}


## The addressing one recorded step used, read out of the recorded request itself
## so the suite's own table cannot drift from the capture.
func _step_addressing(name: String) -> Variant:
	var step := _fixture_step(name)
	if step.is_empty():
		return null
	var data: String = str((step["request"] as Dictionary)["form"]["data"])
	var parsed: Variant = JSON.parse_string(data.split(";")[1])
	if not (parsed is Dictionary):
		return null
	var entry: Array = ((parsed as Dictionary)["commands"] as Array)[0]
	var command := str((entry as Array)[1])
	var args: Array = entry[2]
	match command:
		QuestFlow.SET_GOALS_COMMAND, QuestFlow.COMPLETE_GOAL_COMMAND:
			return _as_int((args as Array)[0])
		QuestFlow.COLLECT_MISSION_COMMAND, QuestFlow.END_QUEST_COMMAND:
			return _as_int((args as Array)[0])
		QuestFlow.ADMIN_SET_QUEST_RANK_COMMAND:
			return _as_int((args as Array)[0])
		_:
			return str((args as Array)[0])


## The seven quest fields of a recorded whole save, as plain comparable values.
func _quest_state_of(document: Variant) -> Dictionary:
	var out := {}
	if not (document is Dictionary):
		return out
	var private: Dictionary = (document as Dictionary)["privateState"]
	var first_map: Dictionary = ((document as Dictionary)["maps"] as Array)[0]
	out[QuestFlow.KEY_GOALS] = (private[QuestFlow.KEY_GOALS] as Array).duplicate()
	out[QuestFlow.KEY_RANKS] = (private[QuestFlow.KEY_RANKS] as Dictionary) \
		.duplicate(true)
	out[QuestFlow.KEY_QUEST_VARS] = first_map[QuestFlow.KEY_QUEST_VARS]
	out[QuestFlow.KEY_QUEST_TIMES] = (first_map[QuestFlow.KEY_QUEST_TIMES]
		as Dictionary).duplicate(true)
	out[QuestFlow.KEY_MISSION] = first_map[QuestFlow.KEY_MISSION]
	out[QuestFlow.KEY_LAST_CHAPTER] = first_map[QuestFlow.KEY_LAST_CHAPTER]
	out[QuestFlow.KEY_UNLOCKED_INDEX] = private[QuestFlow.KEY_UNLOCKED_INDEX]
	return out


## Every quest-state JSON-pointer leaf at which two recorded states differ — the
## seven fields' values, plus a whole-document check that NOTHING ELSE moved.
func _quest_leaf_differences(before: Variant, after: Variant) -> Array:
	var collected: Array = []
	if not (before is Dictionary) or not (after is Dictionary):
		return collected
	var before_state := _quest_state_of(before)
	var after_state := _quest_state_of(after)
	for key: String in QuestFlow.QUEST_FIELDS:
		if _differs(after_state[key], before_state[key]):
			if key == QuestFlow.KEY_QUEST_TIMES:
				collected.append("/maps/0/questTimes")
			elif key == QuestFlow.KEY_GOALS:
				collected.append("/privateState/goals")
			elif key == QuestFlow.KEY_RANKS:
				collected.append("/privateState/questsRank")
			elif key == QuestFlow.KEY_UNLOCKED_INDEX:
				collected.append("/privateState/unlockedQuestIndex")
			elif key == QuestFlow.KEY_QUEST_VARS:
				collected.append("/maps/0/currentQuestVars")
			elif key == QuestFlow.KEY_MISSION:
				collected.append("/maps/0/idCurrentMission")
			else:
				collected.append("/maps/0/timestampLastChapter")
	if ((before as Dictionary)["maps"] as Array)[0]["items"] \
			!= ((after as Dictionary)["maps"] as Array)[0]["items"]:
		collected.append("/maps/0/items")
	if (before as Dictionary)["playerInfo"] != (after as Dictionary)["playerInfo"]:
		collected.append("/playerInfo")
	collected.sort()
	return collected


func _resources_of(document: Dictionary) -> Dictionary:
	var first_map: Dictionary = (document["maps"] as Array)[0]
	return {
		"xp": _as_int(first_map["xp"]),
		"gold": _as_int(first_map["gold"]),
		"wood": _as_int(first_map["wood"]),
		"oil": _as_int(first_map["oil"]),
		"steel": _as_int(first_map["steel"]),
		"cash": _as_int((document["playerInfo"] as Dictionary)["cash"]),
		"mana": _as_int((document["privateState"] as Dictionary)["mana"]),
	}


# ---------------------------------------------------------------------------
# The intent and both implementations (task 3.5)
# ---------------------------------------------------------------------------


## The facade's quest operation takes EXACTLY the save identity, a closed action,
## and the branch's own addressing — and both implementations carry it.
func _check_intents() -> void:
	var facade: Variant = root.get_node_or_null("GameApi")
	check(facade != null, "GameApi autoload is registered")
	if facade == null:
		return
	var methods: Variant = facade.get_script().get_script_method_list()
	var found: Variant = _method(methods, "advance_quest_town")
	check(found != null, "the facade implements the quest intent")
	if found != null:
		var args: Array = (found as Dictionary)["args"]
		check_eq(args.size(), 3,
			"advance_quest_town takes EXACTLY the save identity, the action, and "
				+ "the addressing: there is no parameter through which a client "
				+ "could send a progress pair, a value, a difficulty, an "
				+ "outcome, or a unit list")
		check_eq((args as Array).size(), QuestFlow.INTENT_KEY_COUNT,
			"the operation's argument count equals the intent's key count")
	check(_has_counter(facade, "quest_requests"),
		"the facade counts quest intents like every other command")
	check(str(facade.implementation_name()) == "fake",
		"the hermetic run is on the fake implementation")
	# --- the flow's own intent body is three keys wide -----------------------
	#
	# The third key is PER-ACTION, and asserting it against
	# `ACTION_ADDRESSING_KEY` is the guard that a previous delivery lacked: the
	# transport used to send every action's addressing under one fixed
	# `addressing` key, every hermetic check passed because the offline double
	# consumes `intent_body()` rather than the route, and the first live phase
	# against the real service answered `missing_goal_index`. Nothing below
	# could have caught it, because nothing compared the body the client forms
	# with the key the service reads.
	var wire_key_table: Variant = QuestFlow.ACTION_ADDRESSING_KEY
	check(typeof(wire_key_table) == TYPE_DICTIONARY,
		"the per-action addressing key table is a dictionary")
	var distinct_wire_keys := {}
	for action: String in QuestFlow.ACTIONS:
		var key: String = QuestFlow.wire_key(action)
		distinct_wire_keys[key] = true
		check_eq(key, str((wire_key_table as Dictionary)[action]),
			"wire_key(%s) is exactly the table's spelling, %s" % [action, key])
		check((QuestFlow.INTENT_FIXED_KEYS as Array).has(key) == false,
			"the addressing key never collides with a fixed key (%s)" % key)
		check(key != QuestFlow.INTENT_ADDRESSING_KEY,
			"a real action never travels under the unknown-action fallback key "
				+ "(%s)" % key)
		var addressing: Variant = ACTION_ADDRESSING[str(action)]
		var body: Variant = QuestFlow.intent_body("pid", action, addressing)
		check(bool(body.get("ok", false)),
			"a well-formed %s intent body is accepted" % action)
		if not bool(body.get("ok", false)):
			continue
		var sent: Dictionary = body["body"]
		check_eq(sent.size(), QuestFlow.INTENT_KEY_COUNT,
			"the %s intent body carries EXACTLY %d keys"
				% [action, QuestFlow.INTENT_KEY_COUNT])
		var intent_keys: Array = sent.keys()
		intent_keys.sort()
		var expected_keys: Array = (QuestFlow.INTENT_FIXED_KEYS as Array).duplicate()
		expected_keys.append(key)
		expected_keys.sort()
		check_eq(intent_keys, expected_keys,
			("the %s intent body carries the player identifier, the action, and "
				+ "the addressing under %s") % [action, key])
		check(sent.has(key),
			"the %s intent body puts the addressing under its OWN wire key" % action)
		check(sent.has("addressing") == (key == "addressing"),
			"the %s intent body uses no other spelling for the addressing" % action)
		check_eq(sent[key], addressing,
			"the intent body echoes the addressing the client named")
		for ignored: String in QuestFlow.INTENT_IGNORED_KEYS:
			check(sent.has(ignored) == false,
				"the %s intent body carries no ignored key (%s)" % [action, ignored])
	# The two goal actions share a key, so the distinct count is five, not six:
	# recorded rather than assumed.
	check_eq(distinct_wire_keys.size(),
		(wire_key_table as Dictionary).size() - 1,
		"exactly two actions share the goal-index key, so the distinct key count "
			+ "is the table's size minus one")
	check_eq(QuestFlow.wire_key("teleport"), QuestFlow.INTENT_ADDRESSING_KEY,
		"an action outside the closed table falls back to the unknown-action key, "
			+ "so its body is still exactly three keys")
	check_eq(QuestFlow.wire_key(null), QuestFlow.INTENT_ADDRESSING_KEY,
		"a null action falls back to the unknown-action key")
	check((wire_key_table as Dictionary).values().has(
			QuestFlow.INTENT_ADDRESSING_KEY) == false,
		"no action's wire key is the fallback spelling")
	for payload: Array in [
			["teleport", 1], ["set_goal", "2"], ["set_goal", -1], ["", 0],
			[null, 0], ["set_quest_var", ""], ["collect_mission", "5"],
			["set_quest_rank", "3"], ["end_quest", "7"],
			["fast_forward", 7],
			["set_quest_var", QuestFlow.QUEST_VAR_IGNORED_KEY]]:
		var refused: Variant = QuestFlow.intent_body("pid", payload[0], payload[1])
		check(not bool(refused.get("ok", false)),
			"the intent (%s, %s) is refused before a request is formed"
				% [str(payload[0]), str(payload[1])])
		check_eq((refused.get("body", {}) as Dictionary), {},
			"a refused intent carries NO body at all")
		check(str(refused.get("reason", "")) != "",
			"the refusal carries its own named reason")
	# --- both implementations carry the operation ---------------------------
	var transport_source := _source("res://scripts/gameapi/legacy_v0_api.gd")
	check(transport_source.contains(QuestFlow.QUEST_PATH),
		"the legacy-v0 implementation names the quest endpoint")
	var facade_source := _source("res://scripts/gameapi/game_api.gd")
	check(not facade_source.contains(QuestFlow.QUEST_PATH),
		"the facade never names the quest endpoint")
	var fake_source := _source("res://scripts/gameapi/fake_api.gd")
	check(not fake_source.contains(QuestFlow.QUEST_PATH),
		"the fake double never names the quest endpoint")
	check(transport_source.contains("advance_quest_town"),
		"the legacy-v0 implementation implements the quest operation")
	check(transport_source.contains("QuestFlow.wire_key(action)"),
		"the transport asks the flow module for the addressing's wire key instead "
			+ "of hardcoding one spelling, so the body cannot drift from the key the "
			+ "service reads")
	check(transport_source.contains('"addressing":') == false,
		"the transport hardcodes no fixed addressing key: that mistake passed "
			+ "every hermetic check and failed only against the real service")
	check(fake_source.contains("advance_quest_town"),
		"the fake double implements the quest operation")
	# The offline double consumes the TYPED arguments, never a request body, so
	# it structurally cannot detect a wire-shape regression. Recorded here so the
	# hermetic run's silence about the body is not mistaken for coverage; the
	# guards above and the `quests-live` phase are what cover it.
	check(fake_source.contains("quest_request_body") == false
			and fake_source.contains("JSON.stringify") == false,
		"the offline double builds no request body at all, which is exactly why "
			+ "the fixed-addressing-key defect passed every hermetic check here")
	check(facade_source.contains("advance_quest_town"),
		"the facade forwards the quest operation")
	# --- and the typed result declares no invented field ---------------------
	var members := _class_members(QuestFlow.QuestResult)
	for required: String in ["action", "addressing", "addressing_kind",
			"command", "derived", "previous", "quest_state", "quests",
			"branches", "writers", "destruction", "migration", "refusals",
			"end_quest_blob", "reward_paid", "reward_derived_from_content",
			"fast_forward_offered", "unlocked_quest_index_written", "resources"]:
		check(members.has(required),
			"the typed quest result declares %s" % required)
	for forbidden: String in ["remaining", "progress", "complete", "ready",
			"duration", "step_count", "price", "cost", "unlock", "elapsed",
			"total_steps"]:
		check(not members.has(forbidden),
			"the typed quest result declares no %s field: the legacy server "
				% forbidden + "has no such rule to report")
	var fresh := QuestFlow.QuestResult.new()
	check(fresh.addressing == null and fresh.reward_paid == -1,
		"a fresh typed quest result carries no partial payload")
	check(bool(fresh.reward_derived_from_content) and bool(fresh.fast_forward_offered)
			and bool(fresh.unlocked_quest_index_written),
		"a fresh typed result's three absence flags start UNSET, so a half-built "
			+ "result can never read as a proven absence")


# ---------------------------------------------------------------------------
# The offline double
# ---------------------------------------------------------------------------


## The fake implementation, driven offline for **all six** branches, so the
## hermetic run exercises the very shapes the live phase will. The double reads
## the committed fixture's first before-state and derives each branch's effect
## from the same `BRANCHES` record the service applies.
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
	for action: String in QuestFlow.ACTIONS:
		var addressing: Variant = ACTION_ADDRESSING[str(action)]
		var result: Variant = await api.advance_quest_town(pid, action, addressing)
		check(result is QuestFlow.QuestResult and result.ok,
			"the fake accepts %s: %s" % [action,
				((result as QuestFlow.QuestResult).error_message
					if result is QuestFlow.QuestResult else "")])
		if not (result is QuestFlow.QuestResult and result.ok):
			continue
		_check_typed_quest(result)
		var typed: QuestFlow.QuestResult = result
		check_eq(str(typed.action), action,
			"the double echoed the action exactly as sent")
		check_eq(typed.addressing, addressing,
			"the double carried the addressing the client named")
		check_eq(str(typed.command), str(_branch_for_action(action)["command"]),
			"the double derived the committed command")
		check_eq(int(typed.reward_paid), 0, "the double pays no reward")
		check(not bool(typed.reward_derived_from_content),
			"the double derives no reward from the committed content")
		check(not bool(typed.fast_forward_offered),
			"the double offers no fast-forward operation")
		check(not bool(typed.unlocked_quest_index_written),
			"the double never writes the unlocked-quest index")
		check_eq(str(typed.destruction["status"]), "REFUSED",
			"the double reports the destruction count as REFUSED")
		check(bool(typed.destruction["placed_rows_byte_identical"]),
			"the double reports every placed row byte-identical")
		for name: String in QuestFlow.CORPUS_RESOURCES.keys():
			check_eq(int((typed.resources as BootData.Resources).get(name)),
				int(QuestFlow.CORPUS_RESOURCES[name]),
				"the double's %s balance is the committed value: a quest action "
					% name + "moves none")
		observed[action] = typed.quest_state
	check_eq(observed.size(), QuestFlow.CAPTURED_BRANCHES,
		"the double drove all six branches offline")
	# A goal index INSIDE the list is accepted — the corpus's goals list already
	# holds 151 entries — while a large one is accepted too, because the legacy
	# growth is unbounded (design D4). Only a NEGATIVE index is refused.
	var grown: Variant = await api.advance_quest_town(pid, "set_goal", 500)
	check(grown is QuestFlow.QuestResult and grown.ok,
		"the double ACCEPTS an out-of-range goal index: the legacy growth has no "
			+ "upper bound")
	if grown is QuestFlow.QuestResult and grown.ok:
		check_eq((grown as QuestFlow.QuestResult).quest_state[
				QuestFlow.KEY_GOALS].size(), 501,
			"the double reproduced the on-demand growth to 501 entries")
	# --- the double's own refusals ------------------------------------------
	for payload: Array in [
			["set_goal", -1], ["fast_forward", 7], ["", 0],
			["set_quest_var", ""], ["collect_mission", "5"],
			["set_quest_rank", "3"], ["end_quest", "7"],
			["set_quest_var", QuestFlow.QUEST_VAR_IGNORED_KEY]]:
		var refused: Variant = await api.advance_quest_town(pid, payload[0],
			payload[1])
		check(refused is QuestFlow.QuestResult and not refused.ok,
			"the double refuses (%s, %s) with the endpoint's own order"
				% [str(payload[0]), str(payload[1])])
		if refused is QuestFlow.QuestResult:
			check(str(refused.error_code) != "",
				"the double's refusal carries a named code")
			check((refused as QuestFlow.QuestResult).quest_state.is_empty(),
				"the double's refused intent carries no partial payload")
	var unknown: Variant = await api.advance_quest_town("does-not-exist-0000",
		"set_goal", 2)
	check(unknown is QuestFlow.QuestResult and not unknown.ok,
		"the double refuses an unknown save")
	if unknown is QuestFlow.QuestResult:
		check_eq(str(unknown.error_code), "unknown_user_id",
			"the double's unknown-save code is the shared one")


## The typed result's own shape, asserted rather than assumed.
func _check_typed_quest(result: Variant) -> void:
	if not (result is QuestFlow.QuestResult):
		return
	var typed: QuestFlow.QuestResult = result
	check_eq(bool(typed.ok), true, "the quest result reports success")
	check_eq(str(typed.protocol), BootData.PROTOCOL,
		"the typed result reports the v0 protocol")
	check_eq(str(typed.result), "success",
		"the typed result carries the legacy success result")
	check(typed.server_time > 0,
		"the typed result's server_time is a positive integer")
	check_eq(int(typed.reward_paid), 0, "the typed result reports no reward")
	check(not bool(typed.reward_derived_from_content),
		"the typed result states no reward was derived from content")
	check(not bool(typed.fast_forward_offered),
		"the typed result states no fast-forward operation was offered")
	check(not bool(typed.unlocked_quest_index_written),
		"the typed result states the unlocked-quest index was never written")
	check_eq((typed.branches as Array).size(), QuestFlow.BRANCH_COUNT,
		"the typed result carries the six recorded branches")
	check_eq((typed.writers as Array).size(), QuestFlow.WRITER_COUNT,
		"the typed result carries the seven recorded quest writers")
	check(typed.resources != null,
		"the typed result carries the authoritative resources")
	for key: String in QuestFlow.QUEST_FIELDS:
		check(typed.quest_state.has(key),
			"the typed result's quest state carries %s" % key)
	var members := _class_members(QuestFlow.QuestResult)
	for forbidden: String in ["remaining", "progress", "complete", "ready",
			"duration", "reward_amount", "price", "cost", "unlock", "elapsed"]:
		check(not members.has(forbidden),
			"the typed quest result declares no %s field" % forbidden)


# ---------------------------------------------------------------------------
# Purity and containment
# ---------------------------------------------------------------------------


## The delivered module names no node, clock, request, or transport token.
func _check_purity() -> void:
	var code := _code_only(QUEST_SOURCE)
	for needle: String in PURITY_NEEDLES:
		check(not code.contains(needle),
			"quest_flow.gd declares no '%s': the projection is pure over a "
				% needle + "save the caller already holds")
	check_eq(_preloads(_source(QUEST_SOURCE)),
		["res://scripts/gameapi/boot_data.gd"],
		"the module loads exactly the typed-data module and nothing else")
	check(not _source(QUEST_SOURCE).contains("await "),
		"the module awaits nothing")


## The content package, the committed saves, and the committed fixtures are
## byte-identical after the run: this line writes evidence under
## `evidence/quests/` and nothing else.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, save_before: Dictionary) -> void:
	var package_after := Paths.directory_digest(Paths.repo_root().path_join(
		"packages/game-content"))
	var saves_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/saves"))
	var fixtures_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/fixtures"))
	check_eq(str(package_after.get("sha256", "")),
		str(package_before.get("sha256", "")),
		"content package bytes are unchanged after the run")
	check_eq(int(package_after.get("files", 0)), int(package_before.get("files", 0)),
		"content package file count is unchanged after the run")
	check_eq(str(saves_after.get("sha256", "")), str(saves_before.get("sha256", "")),
		"no committed save byte changed during the run")
	check_eq(str(fixtures_after.get("sha256", "")),
		str(fixtures_before.get("sha256", "")),
		"no committed fixture byte changed during the run — including the "
			+ "executed quest fixture, which is only read")
	var save_after := Paths.file_sha256_checked(Paths.repo_root().path_join(
		CORPUS_SAVE))
	check_eq(str(save_after.get("sha256", "")),
		str(save_before.get("sha256", "")),
		"the committed corpus save is byte-identical after the run")
	check_eq(int(save_after.get("bytes", 0)), int(save_before.get("bytes", 0)),
		"the committed corpus save's byte count is unchanged")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory exists after the run")


# ---------------------------------------------------------------------------
# The live-quests phase (verify-boot's `quests-live`)
# ---------------------------------------------------------------------------


## One pass through **all six** intents over the REAL Compatibility endpoint, so
## the unchanged legacy `command()` executes the derived quest envelopes over the
## disposable corpus. This asserts the typed response for each action AND its
## post-state — the derived progress pair, the no-op branch's whole-state
## identity, the stringified mission and cleared map, the derived rank
## difficulty, the refused destruction with every row byte-identical, AND every
## stored resource unchanged — plus the named refusals carrying the service's own
## codes with no partial payload. The phase harness separately asserts the corpus
## save file mutated.
func _check_live_quests() -> void:
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
	check(not before_payload.is_empty(), "the corpus pre-quest payload resolves")
	if before_payload.is_empty():
		return
	var resources_before := _live_resources(before_payload)
	var state_before := _live_quest_state(before_payload)
	check_eq(int((state_before[QuestFlow.KEY_GOALS] as Array).size()),
		EXPECTED_GOALS_LENGTH,
		"the live corpus's goals list is the committed 151-entry list")
	check(state_before[QuestFlow.KEY_QUEST_VARS] == null,
		"the live corpus's quest-variable map is the committed recorded null")
	check_eq(state_before[QuestFlow.KEY_MISSION], QuestFlow.CORPUS_MISSION,
		"the live corpus's mission is the committed INTEGER 0")
	var rows_before := _live_rows(before_payload)
	check_eq(rows_before, QuestFlow.CORPUS_PLACEMENTS,
		"the live corpus places 40 rows before any intent")
	# --- the progress intent ------------------------------------------------
	var progressed: Variant = await api.advance_quest_town(pid, "set_goal", 2)
	check(progressed is QuestFlow.QuestResult and progressed.ok,
		"a progress intent is accepted by the real endpoint: %s"
			% ((progressed as QuestFlow.QuestResult).error_message
				if progressed is QuestFlow.QuestResult else ""))
	if progressed is QuestFlow.QuestResult and progressed.ok:
		_check_typed_quest(progressed)
		var typed: QuestFlow.QuestResult = progressed
		check_eq(str(typed.action), "set_goal", "the service echoed the action")
		check_eq(str(typed.command), "set_goals",
			"the service derived the committed progress command")
		# Godot's JSON decoder yields a **float** for every number in a JSON payload,
		# so a wire response's `0` arrives as `0.0` and a structural comparison
		# against the integer pair fails. Compared value-wise through `int()`
		# instead. The offline double builds its response as a GDScript Dictionary
		# of real integers, so this difference is invisible to the hermetic run —
		# a fourth instance of the same cross-layer drift.
		var stored_pair: Variant = (typed.quest_state[QuestFlow.KEY_GOALS]
				as Array)[2]
		check(stored_pair is Array and (stored_pair as Array).size() == 2,
			"the addressed goal entry is the DERIVED two-element progress pair")
		if stored_pair is Array and (stored_pair as Array).size() == 2:
			check_eq(int((stored_pair as Array)[0]),
				QuestFlow.DERIVED_PROGRESS[0],
				"the executed branch stored the DERIVED progress pair's first half")
			check_eq(int((stored_pair as Array)[1]),
				QuestFlow.DERIVED_PROGRESS[1],
				"the executed branch stored the DERIVED progress pair's second half")
		# The neighbouring entry stays the recorded null. Compared as a null rather
		# than through `int()`, because `int(null)` is a nonexistent constructor in
		# Godot 4 and every corpus goal the branch did not address IS a null.
		check((typed.quest_state[QuestFlow.KEY_GOALS] as Array)[3] == null,
			"the entry after the addressed one is still the recorded null")
		check_eq(int(typed.derived["stamps_instant"]) + 1, 1,
			"the progress branch stamps no instant")
		_check_live_resources(typed, resources_before, "the progress intent")
	# --- the no-op intent ---------------------------------------------------
	var completed: Variant = await api.advance_quest_town(pid, "complete_goal", 2)
	check(completed is QuestFlow.QuestResult and completed.ok,
		"a goal-completion intent is accepted by the real endpoint")
	if completed is QuestFlow.QuestResult and completed.ok:
		var typed_no_op: QuestFlow.QuestResult = completed
		check_eq(str(typed_no_op.command), "complete_goal",
			"the service derived the committed no-op command")
		check(not bool(typed_no_op.derived["mutates"]),
			"the service reports the branch as NON-MUTATING")
		check_eq((typed_no_op.derived["written"] as Array), [],
			"the service reports the branch as writing NO field")
		check((typed_no_op.previous as Dictionary).has("fields"),
			"the before projection carries the seven verbatim fields under "
				+ "'fields', which is what the no-op proof compares")
		check_eq(_live_quest_fields(typed_no_op.quest_state),
			_live_quest_fields(
				(typed_no_op.previous as Dictionary).get("fields", {})),
			"the executed no-op branch changed NO quest field at all")
		_check_live_resources(typed_no_op, resources_before,
			"the goal-completion intent")
	# --- the quest-variable intent -------------------------------------------
	var varied: Variant = await api.advance_quest_town(pid, "set_quest_var",
		"boss")
	check(varied is QuestFlow.QuestResult and varied.ok,
		"a quest-variable intent is accepted by the real endpoint")
	if varied is QuestFlow.QuestResult and varied.ok:
		var typed_var: QuestFlow.QuestResult = varied
		check_eq(str(typed_var.command), "set_quest_var",
			"the service derived the committed quest-variable command")
		check_eq((typed_var.quest_state[QuestFlow.KEY_QUEST_VARS] as Dictionary),
			{"boss": QuestFlow.DERIVED_QUEST_VALUE},
			"the executed branch SELF-HEALED the recorded null and persisted the "
				+ "DERIVED marker")
		check(not bool(typed_var.quests["current_quest_vars_is_null"]),
			"the service's own projection reports the recorded null is gone")
		_check_live_resources(typed_var, resources_before,
			"the quest-variable intent")
	# --- the chapter intent: the stringified identifier and the clear --------
	var advanced: Variant = await api.advance_quest_town(pid, "collect_mission",
		5)
	check(advanced is QuestFlow.QuestResult and advanced.ok,
		"a chapter intent is accepted by the real endpoint")
	if advanced is QuestFlow.QuestResult and advanced.ok:
		var typed_chapter: QuestFlow.QuestResult = advanced
		check_eq(str(typed_chapter.command), "collect_mission",
			"the service derived the committed chapter command")
		check_eq(str(typed_chapter.quest_state[QuestFlow.KEY_MISSION]), "5",
			"the executed chapter branch stored the mission as a STRING")
		check(bool(typed_chapter.quests["mission_is_string"]),
			"the service's own projection reports the mission as a string")
		check_eq((typed_chapter.quest_state[QuestFlow.KEY_QUEST_VARS] as Dictionary),
			{}, "the executed chapter branch CLEARED the quest-variable map")
		check(int(typed_chapter.quest_state[QuestFlow.KEY_LAST_CHAPTER]) > 0,
			"the executed chapter branch stamped the last-chapter instant")
		check_eq(int(typed_chapter.derived["wrapped_mission"]), 5,
			"the service reports the mission inside the wrap bound unchanged")
		_check_live_resources(typed_chapter, resources_before, "the chapter intent")
	# --- the out-of-range chapter WRAPS rather than being rejected ----------
	var wrapped: Variant = await api.advance_quest_town(pid, "collect_mission",
		150)
	check(wrapped is QuestFlow.QuestResult and wrapped.ok,
		"an out-of-range chapter identifier is accepted: the guard is a WRAP")
	if wrapped is QuestFlow.QuestResult and wrapped.ok:
		var typed_wrap: QuestFlow.QuestResult = wrapped
		check_eq(str(typed_wrap.quest_state[QuestFlow.KEY_MISSION]), "1",
			"the executed branch WRAPPED 150 to 1 rather than rejecting it")
		check_eq(int(typed_wrap.derived["wrapped_mission"]), 1,
			"the service reports the wrap itself")
		_check_live_resources(typed_wrap, resources_before,
			"the wrapping chapter intent")
	# --- the rank intent ----------------------------------------------------
	var ranked: Variant = await api.advance_quest_town(pid, "set_quest_rank", 3)
	check(ranked is QuestFlow.QuestResult and ranked.ok,
		"a quest-rank intent is accepted by the real endpoint")
	if ranked is QuestFlow.QuestResult and ranked.ok:
		var typed_rank: QuestFlow.QuestResult = ranked
		check_eq(str(typed_rank.command), "admin_set_quest_rank",
			"the service derived the committed rank command")
		check_eq((typed_rank.quest_state[QuestFlow.KEY_RANKS] as Dictionary).keys(),
			["3"], "the executed rank branch wrote exactly the addressed rank")
		check_eq(int(((typed_rank.quest_state[QuestFlow.KEY_RANKS]
				as Dictionary)["3"] as float)),
			QuestFlow.DERIVED_DIFFICULTY,
			"the executed rank branch wrote the DERIVED difficulty")
		_check_live_resources(typed_rank, resources_before, "the quest-rank intent")
	# --- the REFUSED destruction -------------------------------------------
	var ended: Variant = await api.advance_quest_town(pid, "end_quest", 7)
	check(ended is QuestFlow.QuestResult and ended.ok,
		"an end_quest intent is accepted by the real endpoint")
	if ended is QuestFlow.QuestResult and ended.ok:
		var typed_end: QuestFlow.QuestResult = ended
		check_eq(str(typed_end.command), "end_quest",
			"the service derived the committed end_quest command")
		check_eq((typed_end.end_quest_blob["units"] as Array), [],
			"the executed request carried an EMPTY unit list: the destruction "
				+ "count is REFUSED")
		check_eq(int(typed_end.destruction["derived_units"]), 0,
			"the service reports ZERO derived destroyed units")
		check_eq(str(typed_end.destruction["status"]), "REFUSED",
			"the service reports the destruction count as REFUSED")
		check_eq(str(typed_end.destruction["legacy_status"]),
			"DIVERGENCE, NOT PARITY",
			"the service reports the difference from the legacy server as a "
				+ "DIVERGENCE, not as parity")
		check(bool(typed_end.destruction["placed_rows_byte_identical"]),
			"the service proves every placed row byte-identical")
		check(int(typed_end.destruction["placed_rows_before"]) ==
			int(typed_end.destruction["placed_rows_after"]),
			"the refused destruction moved no row in either direction")
		check(int(typed_end.quest_state[QuestFlow.KEY_QUEST_TIMES].size()) > 0,
			"the executed end_quest branch DID write its quest-time entry")
		check(int(typed_end.quest_state[QuestFlow.KEY_UNLOCKED_INDEX]) ==
			QuestFlow.CORPUS_UNLOCKED_INDEX,
			"the executed end_quest branch did NOT write the unlocked index")
		_check_live_resources(typed_end, resources_before, "the end_quest intent")
	# --- the same intents through the fake, offline -------------------------
	api.configure("fake")
	var fake_step: Variant = await api.advance_quest_town(pid, "set_goal", 2)
	check(fake_step is QuestFlow.QuestResult and fake_step.ok,
		"the fake accepts the same intent offline")
	if fake_step is QuestFlow.QuestResult and fake_step.ok:
		_check_typed_quest(fake_step)
		check_eq((fake_step as QuestFlow.QuestResult).quest_state[
				QuestFlow.KEY_GOALS][2], [0, 0],
			"both implementations derive the same progress pair")
	# --- three named refusals, carrying the service's own codes --------------
	api.configure("legacy_v0", endpoint)
	var refused_var: Variant = await api.advance_quest_town(pid, "set_quest_var",
		QuestFlow.QUEST_VAR_IGNORED_KEY)
	check(refused_var is QuestFlow.QuestResult and not refused_var.ok,
		"the one ignored quest-variable key is refused")
	if refused_var is QuestFlow.QuestResult:
		check_eq(str(refused_var.error_code), "ignored_quest_var_key",
			"the ignored-key refusal is the service's own code")
		check((refused_var as QuestFlow.QuestResult).quest_state.is_empty(),
			"the refused intent carries no partial payload")
	var refused_rank: Variant = await api.advance_quest_town(pid,
		"set_quest_rank", "3")
	check(refused_rank is QuestFlow.QuestResult and not refused_rank.ok,
		"a rank intent naming a string index is refused")
	if refused_rank is QuestFlow.QuestResult:
		check_eq(str(refused_rank.error_code), "invalid_quest_index",
			"the string-index refusal is the service's own code")
		check((refused_rank as QuestFlow.QuestResult).quest_state.is_empty(),
			"the refused intent carries no partial payload")
	# The five **missing-key** refusals (`missing_goal_index`, `missing_key`,
	# `missing_mission`, `missing_quest_index`, `missing_quest_id`) are
	# STRUCTURALLY UNREACHABLE through the typed client, and that is a property
	# of the delivered operation rather than a gap in this phase: the addressing
	# is a REQUIRED parameter and the transport writes its wire key
	# unconditionally, so no body can ever omit it. Recorded here so a reader does
	# not take their absence from this phase for missing coverage.
	var method_list: Variant = api.get_script().get_script_method_list()
	var method_entry: Variant = _method(method_list, "advance_quest_town")
	check_eq((method_entry as Dictionary)["args"].size(),
		QuestFlow.INTENT_KEY_COUNT,
		"the addressing is a REQUIRED argument, so no typed call can omit the "
			+ "key the service reads and produce a missing-key refusal")
	var refused_fast: Variant = await api.advance_quest_town(pid, "fast_forward", 7)
	check(refused_fast is QuestFlow.QuestResult and not refused_fast.ok,
		"a fast_forward intent is refused: the seventh writer is recorded and "
			+ "delivered not at all")
	if refused_fast is QuestFlow.QuestResult:
		check_eq(str(refused_fast.error_code), "invalid_action",
			"the fast-forward refusal is the service's own code")
	# --- the whole placed-row set is untouched -------------------------------
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not after_payload.is_empty(),
		"the corpus post-quest payload resolves")
	if not after_payload.is_empty():
		check_eq(_live_rows(after_payload), rows_before,
			"the refused destruction left every placed row in place through the "
				+ "whole cycle")
		check_eq(_live_resources(after_payload), resources_before,
			"every live corpus balance is byte-identical after the whole cycle")
		check_eq(int(_live_quest_state(after_payload)[QuestFlow.KEY_UNLOCKED_INDEX]),
			QuestFlow.CORPUS_UNLOCKED_INDEX,
			"no intent in the cycle wrote the unlocked-quest index")
	print("[test] live-quests applied progress_pair=[0, 0] no_op_wrote=0 "
		+ "quest_var=self_healed mission=\"5\" then wrapped \"1\" "
		+ "difficulty=1 quest_time_written=true rows_byte_identical=true "
		+ "reward_paid=0 resources_unchanged=true "
		+ "refused=ignored_quest_var_key,invalid_quest_index,invalid_action "
		+ "missing_key_refusals=structurally_unreachable")


## The typed result's authoritative balances against the cycle's pre-request
## reference — the value-level half of the endpoint's "nothing moved" proof.
func _check_live_resources(result: Variant, resources_before: Dictionary,
		label: String) -> void:
	var typed: QuestFlow.QuestResult = result
	check(typed.resources != null, "%s carries the authoritative balances" % label)
	if typed.resources == null:
		return
	for name: String in QuestFlow.CORPUS_RESOURCES.keys():
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by %s" % [name, label])


## The quest fields of a payload, for the equality comparison the no-op proof
## needs (dictionaries and arrays are compared by value, so nothing is aliased).
func _live_quest_fields(state: Dictionary) -> Dictionary:
	var out := {}
	for key: String in QuestFlow.QUEST_FIELDS:
		out[key] = state[key]
	return out


# ---------------------------------------------------------------------------
# Evidence report (design D12)
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


## Computes and writes the deterministic `quests-report-v1` report.
##
## EVERY fact about the model comes from `quest_flow.gd` — its own key
## constants, `BRANCHES`, `WRITERS`, `MIGRATION`, `NON_DERIVATION`, `REFUSALS`,
## `REFUSED_DESTRUCTION`, `LEDGER_DOOR`, `CONTENT_FIELD_CONSUMERS`, `PROVENANCE`,
## and `NON_CLAIMS` — and every committed number comes from the legacy source, the
## content package, the corpus save, and the fixture bytes **measured in this
## run**. Nothing here reads the wall clock, resolves a path outside the
## repository, or sends a request: that is what makes the file byte-identical
## across reruns.
func _write_report(path: String, source: Dictionary, content: Dictionary,
		corpus: Dictionary, fixture: Dictionary, package_digest: Dictionary,
		save_digest: Dictionary) -> void:
	var record := QuestFlow.branch_record()
	var report := {
		"schema": "quests-report-v1",
		"generated_by": "apps/client-godot/tests/test_quests.gd --report=<path>",
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
			"time_dependent_fields": "the ONLY time-dependent values in this "
				+ "line's evidence are the two wall-clock stamps the committed "
				+ "fixture fixed — the last-chapter instant and the quest-time "
				+ "entry — and the fake double stamps those same recorded values "
				+ "rather than reading a clock",
		},
		"quest_model": {
			"fields": (QuestFlow.QUEST_FIELDS as Array).duplicate(),
			"private_keys": (QuestFlow.PRIVATE_KEYS as Array).duplicate(),
			"map_keys": (QuestFlow.MAP_KEYS as Array).duplicate(),
			"field_count": QuestFlow.QUEST_FIELDS.size(),
			"verbatim_rule": "each of the seven fields is reported exactly as the "
				+ "save holds it - no scaling, rounding, defaulting, or clamping - "
				+ "and a malformed value fails closed with the field and the value "
				+ "named. An integral float is the documented transport tolerance; "
				+ "a numeric string is refused",
			"unresolvable_rule": "a state that is absent, is not an object, "
				+ "carries a goals list that is not a list, a rank map that is "
				+ "not an object, a non-integer unlocked index, a mission that is "
				+ "neither an integer nor a string, or a non-integer last-chapter "
				+ "instant is reported UNRESOLVABLE with its recorded state "
				+ "intact, and is never defaulted to an empty quest presented as "
				+ "a resolved one",
			"null_rule": "a recorded NULL currentQuestVars is a legitimate "
				+ "committed state and is reported as a recorded null, flagged by "
				+ "its own predicate and its own named marker, and NEVER "
				+ "presented as an empty map (design D8)",
			"read_only": "the view holds copies of the committed values and "
				+ "declares no setter, no mutating method, and no writable public "
				+ "field; every reader returns a committed value or a fresh copy",
			"reasons": (QuestFlow.PROJECTION_REASONS as Array).duplicate(),
			"recorded_null_marker": QuestFlow.REASON_NULL_QUEST_VARS,
		},
		"branches": (QuestFlow.BRANCHES as Array).duplicate(true),
		"branch_count": QuestFlow.BRANCH_COUNT,
		"branch_count_rule": "the dispatcher has 63 named branches and exactly "
			+ "SIX of them touch quest state; the suite re-derives each one's "
			+ "inclusive line range out of command.py and fails the run on a "
			+ "drift, and a seventh quest-ish branch would fail it too",
		"no_op_branch": {
			"command": QuestFlow.NO_OP_COMMAND,
			"writes_nothing_at_all": true,
			"reason": QuestFlow.NO_COMPLETION,
		},
		"writers": (QuestFlow.WRITERS as Array).duplicate(true),
		"writer_count": QuestFlow.WRITER_COUNT,
		"fast_forward": {
			"command": QuestFlow.FAST_FORWARD_COMMAND,
			"contract": QuestFlow.FAST_FORWARD_CONTRACT,
			"offered": false,
			"quest_times_source": "command.py:942-944",
			"last_chapter_source": "command.py:911",
			"seconds_source": "args[0], CLIENT-SUPPLIED (command.py:906)",
			"formula": "quest_times[key] = max(0, quest_times[key] - seconds)",
			"clamped": true,
			"is_a_quest_branch": false,
		},
		"migration": QuestFlow.MIGRATION.duplicate(true),
		"non_derivation": (QuestFlow.NON_DERIVATION as Array).duplicate(true),
		"refusals": (QuestFlow.REFUSALS as Array).duplicate(true),
		"refusal_count": QuestFlow.REFUSAL_COUNT,
		"refused_destruction": QuestFlow.REFUSED_DESTRUCTION.duplicate(true),
		"ledger_door": QuestFlow.LEDGER_DOOR.duplicate(true),
		"quest_var_keys": {
			"comment_keys": (QuestFlow.QUEST_VAR_COMMENT_KEYS as Array).duplicate(),
			"enforced": false,
			"ignored_key": QuestFlow.QUEST_VAR_IGNORED_KEY,
			"alias_key": QuestFlow.QUEST_VAR_ALIAS_KEY,
			"note": QuestFlow.QUEST_VAR_COMMENT_NOTE,
		},
		"wrap": {
			"bound": QuestFlow.MISSION_WRAP_BOUND,
			"target": QuestFlow.MISSION_WRAP_TARGET,
			"rejection": false,
			"note": QuestFlow.MISSION_WRAP_NOTE,
		},
		"content": {
			"entries": _as_int(content.get("entries", 0)),
			"reward_values": (content.get("reward_values", []) as Array).duplicate(),
			"id_min": _as_int(content.get("id_min", 0)),
			"id_max": _as_int(content.get("id_max", 0)),
			"empty_hints": int(content.get("empty_hints", 0)),
			"non_empty_descriptions": int(content.get("non_empty_descriptions", 0)),
			"distinct_shapes": int(content.get("field_shapes", 0)),
			"fields": (QuestFlow.CONTENT_FIELD_CONSUMERS as Array).duplicate(true),
			"field_count": QuestFlow.CONTENT_FIELD_COUNT,
			"fields_read": (QuestFlow.CONTENT_FIELDS_READ as Array).duplicate(),
			"fields_unread": (QuestFlow.CONTENT_FIELDS_UNREAD as Array).duplicate(),
			"reward_field": REWARD_FIELD,
			"reward_field_absent": QuestFlow.REWARD_FIELD_ABSENT,
			"paid_amount_constant": QuestFlow.REWARD_PAID,
			"goal_index_source": QuestFlow.COMMITTED_GOAL_INDEX_SOURCE,
			"note": QuestFlow.CONTENT_RECORD_NOTE,
		},
		"measured_legacy": {
			"branch_ranges": (source.get("branch_ranges", {}) as Dictionary)
				.duplicate(true),
			"key_occurrences": (source.get("key_occurrences", {}) as Dictionary)
				.duplicate(true),
			"key_distinct_lines": (source.get("key_lines", {}) as Dictionary)
				.duplicate(true),
			"ignored_key_line": int(source.get("ignored_key_line", 0)),
			"migration_lines": (source.get("migration_lines", []) as Array)
				.duplicate(),
			"set_goals_helper_line": (source.get("helper_lines", []) as Array)
				.duplicate(),
			"counting_rule": "quoted occurrences are counted so a comment or a "
				+ "recorded non-claim can never be mistaken for code, and the "
				+ "OCCURRENCE count and the DISTINCT-LINE count are recorded "
				+ "separately because they differ for exactly one key: "
				+ "timestampLastChapter is read and written on ONE line",
		},
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"rows": int(corpus.get("rows", 0)),
			"goals_length": int(corpus.get("goals_length", 0)),
			"goals_null_entries": int(corpus.get("goals_null", 0)),
			"resources": (corpus.get("resources", {}) as Dictionary).duplicate(true),
			"store": (corpus.get("store", {}) as Dictionary).duplicate(true),
			"quest_content_rows": 0,
			"claim": "the committed corpus holds every quest field at its initial "
				+ "value — 151 goal entries all None, an empty rank map, an "
				+ "unlocked index of 0, a recorded NULL quest-variable map, an "
				+ "empty quest-time map, an INTEGER mission 0, and a last-chapter "
				+ "instant of 0 — which is why this line records NO absent fixture",
		},
		"fixture": {
			"directory": FIXTURE_DIR,
			"manifest": FIXTURE_MANIFEST,
			"executed_legacy": true,
			"branches": (fixture.get("steps", []) as Array).size(),
			"steps": (fixture.get("steps", []) as Array).duplicate(true),
			"no_op_step_byte_identical": true,
			"destruction_captured": false,
			"reward_captured": false,
			"no_absent_fixture": true,
			"probes": 5,
			"probe_note": "probe 1 grew the goals list by exactly 350 entries from "
				+ "ONE client-sent identifier of 500 and stored the DERIVED "
				+ "progress pair; probe 2 showed the one ignored key changing "
				+ "nothing while probe 2b showed an INVENTED key accepted; probe 3 "
				+ "showed the out-of-range mission WRAPPING to the string \"1\" "
				+ "where the corpus records an integer 0; probe 4 showed the "
				+ "LEGACY server really DESTROYING one placed row while the "
				+ "delivered step destroyed none, which is the executed evidence "
				+ "for the divergence; probe 5 showed fast_forward subtracting "
				+ "the CLIENT-supplied 60 seconds from every quest time and from "
				+ "the last-chapter instant",
			"fixture_scope": "the six recorded quest-state transitions against the "
				+ "fresh-player corpus: no progressed save, no other command, no "
				+ "reward, no completion, and no quest-timing semantics",
		},
		"intents": QuestFlow.intent_record(),
		"provenance": QuestFlow.PROVENANCE,
		"non_claims": (QuestFlow.NON_CLAIMS as Array).duplicate(true),
		"branch_record_fields": _sorted_keys(record),
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


## One committed number as the exact integer it denotes.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
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


## The function names a module declares, sorted. With no ``inner`` class the
## MODULE level is returned — and a module-level ``func`` is one at column 0,
## which is what keeps it separate from an inner class's readers.
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
## named after the committed reward field" (task 2.5).
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


func _sorted_strings(values: Array) -> Array:
	var out: Array = values.duplicate()
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


## One legacy module's lines, as an Array of Strings.
func _legacy_lines(module: String) -> Array:
	var out: Array = []
	for line: String in FileAccess.get_file_as_string(
			Paths.repo_root().path_join(module)).split("\n"):
		out.append(line)
	return out


## Quoted occurrences of one field across the seven legacy modules.
func _quoted_occurrences(field: String) -> int:
	var total := 0
	var needle := '"%s"' % field
	for module: String in LEGACY_MODULES:
		for line: String in _legacy_lines(module):
			var index := 0
			while true:
				var at := line.find(needle, index)
				if at == -1:
					break
				total += 1
				index = at + needle.length()
	return total


## The modules a quoted field is read from, in committed order.
func _quoted_modules(field: String) -> Array:
	var out: Array = []
	var needle := '"%s"' % field
	for module: String in LEGACY_MODULES:
		for line: String in _legacy_lines(module):
			if line.contains(needle):
				out.append(module)
				break
	return out


## The committed corpus's own private state, as a plain dictionary.
func _committed_private_state() -> Dictionary:
	var document: Dictionary = _read_json(
		Paths.repo_root().path_join(CORPUS_SAVE))
	if not (document is Dictionary):
		fail("the committed corpus save parses for the projection checks")
		return {}
	return document["privateState"] as Dictionary


## The committed corpus's own first map, as a plain dictionary.
func _committed_first_map() -> Dictionary:
	var document: Dictionary = _read_json(
		Paths.repo_root().path_join(CORPUS_SAVE))
	if not (document is Dictionary):
		fail("the committed corpus save parses for the projection checks")
		return {}
	return ((document["maps"] as Array)[0] as Dictionary).duplicate(true)


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


## The live payload's seven quest fields, as plain comparable values.
func _live_quest_state(payload: Dictionary) -> Dictionary:
	var private: Variant = payload.get("privateState", {})
	var map: Dictionary = payload.get("map", {}) as Dictionary
	var out := {}
	if not (private is Dictionary):
		return out
	out[QuestFlow.KEY_GOALS] = ((private as Dictionary)[QuestFlow.KEY_GOALS]
		as Array).duplicate()
	out[QuestFlow.KEY_RANKS] = ((private as Dictionary)[QuestFlow.KEY_RANKS]
		as Dictionary).duplicate(true)
	out[QuestFlow.KEY_QUEST_VARS] = map.get(QuestFlow.KEY_QUEST_VARS)
	out[QuestFlow.KEY_QUEST_TIMES] = (map.get(QuestFlow.KEY_QUEST_TIMES)
		as Dictionary).duplicate(true)
	out[QuestFlow.KEY_MISSION] = _as_int(map.get(QuestFlow.KEY_MISSION))
	out[QuestFlow.KEY_LAST_CHAPTER] = _as_int(map.get(QuestFlow.KEY_LAST_CHAPTER))
	out[QuestFlow.KEY_UNLOCKED_INDEX] = _as_int(
		(private as Dictionary)[QuestFlow.KEY_UNLOCKED_INDEX])
	return out


## The live payload's placement count, so the refused destruction can be shown
## over the whole set rather than a selected few.
func _live_rows(payload: Dictionary) -> int:
	var map: Variant = payload.get("map", {})
	if not (map is Dictionary):
		return 0
	var rows: Variant = (map as Dictionary).get("items")
	if not (rows is Dictionary):
		return 0
	return (rows as Dictionary).size()


## The live payload's seven stored balances, as integers — the pre-request
## reference the live value-level proof compares against.
func _live_resources(payload: Dictionary) -> Dictionary:
	var map: Dictionary = payload.get("map", {}) as Dictionary
	var player: Dictionary = payload.get("playerInfo", {}) as Dictionary
	var private: Dictionary = payload.get("privateState", {}) as Dictionary
	return {
		"xp": int(_as_int(map.get("xp", 0))),
		"gold": int(_as_int(map.get("gold", 0))),
		"wood": int(_as_int(map.get("wood", 0))),
		"oil": int(_as_int(map.get("oil", 0))),
		"steel": int(_as_int(map.get("steel", 0))),
		"cash": int(_as_int(player.get("cash", 0))),
		"mana": int(_as_int(private.get("mana", 0))),
	}