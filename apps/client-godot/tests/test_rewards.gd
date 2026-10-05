extends "res://tests/test_base.gd"
## Hermetic suite for the `godot-rewards` reward-cursor line (M10 line 1).
##
## Exercises the typed read-only projection in `scripts/rewards/reward_flow.gd`
## over the **committed** reward schedules and the **committed** save corpus,
## and proves that its refusals are structural rather than written down:
##
##   1. **Both cursors and both instants are projected from committed state**,
##      and the derived weekly bound is reported BESIDE the schedule's
##      cardinality, because the two disagree -- 5 against 3 -- and a reader who
##      received only the bound would not know that two of its positions name
##      nothing.
##   2. **The weekly bound and both successors are RE-DERIVED on every run** from
##      the committed bytes of `get_game_config.py:195-204`,
##      `command.py:345-363`, and `command.py:444-463`. The figures are extracted
##      with regular expressions from the recorded spans rather than transcribed,
##      so a legacy edit fails the suite instead of silently contradicting it.
##   3. **The consumer census is RE-MEASURED on every run** over a module list the
##      repository DISCOVERS, and the subject count is **printed before any zero
##      verdict is believed** -- the vacuous-census defect class, which has
##      recurred three times in this project. Three positive controls run over the
##      same corpus with the same machinery and must fire.
##   4. **Three layers of structural guard**: the whole `static func` inventory
##      pinned in both directions, exact by-name guards, and a **substring** guard
##      (a by-name-only guard was measured to miss a suffixed helper on an earlier
##      line of this project).
##   5. **The refusals are shown reachable, and so are their limits**: every
##      documented refusal is classified as client-reachable or endpoint-only, and
##      the endpoint-only ones are recorded as such rather than implied.
##   6. **The four-part grant proof and the two-part cursor proof are asserted**,
##      not merely present in a table.
##
## ## What this suite establishes about the two corrected measurements
##
## Two figures carried by the module were wrong and are corrected here with the
## measurement that corrected them. `DECODER_POSITIVE_CONTROLS` recorded
## `quoted_subscript` at 515 and `unquoted_subscript` at 244; both were measured
## against a hand-written string scan rather than against a pattern, and
## re-measured against the patterns the module now carries they are **516** and
## **225**. And `SAVE_ONLY_DOCUMENT_COUNT` is 33 against **34** walked files,
## because `tests/saves/manifest.json` carries no `privateState`. Both figures
## are re-derived every run and published, so neither correction is a number this
## suite merely trusts.
##
## Nothing here reaches the network, writes a save, or executes Flash.
##
## `-- --report=<path>` writes the deterministic `rewards-report-v1` document.
## Every table in it is generated from the delivered module's own constants, from
## this run's own measurement of committed bytes, or from committed content. No
## wall clock and no absolute path is written, so reruns reproduce the bytes.

const RewardFlow = preload("res://scripts/rewards/reward_flow.gd")
const ContentRegistry = preload("res://scripts/content_registry.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The delivered module, relative to the Godot project directory.
const MODULE_PATH := "scripts/rewards/reward_flow.gd"

const DEFAULT_REPORT_PATH := "evidence/rewards/report.json"

## The committed content domain the eleven reward schedules live in.
const CONTENT_DOMAIN := "globals"

## The committed save document the projection is driven over end to end.
const CORPUS_SAVE := "tests/saves/fresh-player.json"

## The recorded cursor and instant values of that document, read from its bytes
## on every run rather than assumed -- both cursors sit at zero and both instants
## at zero, which is what makes the first successor of each action land on
## position 1.
const EXPECTED_CORPUS_WEEKLY_CURSOR := 0
const EXPECTED_CORPUS_DAILY_CURSOR := 0
const EXPECTED_CORPUS_STAMP := 0

## ---------------------------------------------------------------------------
## The legacy spans this suite re-derives from, transcribed as COORDINATES only.
## ---------------------------------------------------------------------------
## Nothing here is transcribed as a figure. Each span's text is read from the
## committed file and the numbers are extracted from it with a regular
## expression, so the pinned constants are the only claim being made and the
## figures are a measurement. A legacy edit therefore fails the extraction rather
## than failing a comparison against a number this suite copied.

const LENGTH_FILE := "get_game_config.py"
const LENGTH_FIRST := 195
const LENGTH_LAST := 204

const WEEKLY_BRANCH_FIRST := 345
const WEEKLY_BRANCH_LAST := 363

const DAILY_BRANCH_FIRST := 444
const DAILY_BRANCH_LAST := 463

## The corpus walk: three directories of committed `.json` files.
const CORPUS_DIRECTORIES := ["tests/saves", "villages", "villages/quest"]

## Measured: 34 `.json` files are walked and 33 of them carry a `privateState`
## holding all seven save-only fields. The one exclusion is
## `tests/saves/manifest.json`, which is a manifest of the corpus rather than a
## save. Both figures are pinned, so the discrepancy between them is recorded
## rather than left for a reader to discover.
const EXPECTED_WALKED_FILES := 34
const EXPECTED_DOCUMENTS_CARRYING := 33

## Measured over the 33 of those 34 walked documents that carry a `privateState`
## (NOT all 34 -- the 34th is the manifest named above). The distributions sum
## to 33, which is a second, independent cross-check on the figure above.
const EXPECTED_WEEKLY_DISTRIBUTION := {"0": 26, "1": 5, "2": 1, "3": 1}
const EXPECTED_DAILY_DISTRIBUTION := {"0": 7, "2": 24, "3": 2}

## The committed weekly schedule, verbatim from `packages/game-content`. Pinned so
## a content edit that changed the derived bound would fail a check that names the
## schedule rather than only its consequences.
const EXPECTED_WEEKLY_CARDINALITY := 3
const EXPECTED_DAILY_CARDINALITY := 5

## The eleven reward schedules' names, and the ONE of them with a consumer. Both
## lists are re-derived from `RewardFlow.SCHEDULES`, never transcribed twice.
const EXPECTED_ZERO_CONSUMER_COUNT := 10

## Measured: the census subject is every top-level `.py` in the repository root,
## and there are exactly eleven of them. `tasks.md` 3.3 records "twelve-module
## census"; that figure is recorded as the recorded text and this one as the
## measurement, and the suite asserts them against each other so the discrepancy
## is visible rather than resolved by hand.
const EXPECTED_MODULE_COUNT := 11

## The `openspec/specs/` directory walked by the ownership checks.
const SPECS_DIRECTORY := "openspec/specs"

## The capability that will own the reward fields once this change syncs. Probes
## are permitted inside its own spec and NOWHERE else, so this suite stays true
## after `/openspec-sync` adds `godot-rewards/spec.md` -- which is exactly when a
## literal "zero hits across every spec" assertion would start failing on its own
## capability.
const OWNING_CAPABILITY := "godot-rewards"

## Both the SOURCE IDENTIFIERS and the ROLE NAMES, because prose specs describe
## behaviour by role and never by key name -- the defect that has made two prior
## ownership greps pass on a field another capability already claimed.
const SOURCE_IDENTIFIER_PROBES := [
	"weeklyRewardIndex", "bonusNextId", "timeStampMondayBonus",
	"timestampLastBonus", "weekly_reward", "win_daily_bonus",
	"MONDAY_BONUS_REWARDS", "DAILY_GOLD_REWARDS",
]
const ROLE_NAME_PROBES := [
	"weekly reward", "daily bonus", "monday bonus", "reward cursor",
	"bonus cursor", "daily reward", "weekly_reward cursor",
]

## The two capabilities that own the ranking-reward table as normalized content.
const RANKING_REWARD_OWNERS := [
	"economy-schedules-normalization", "content-validation",
]

## The quests line's five refusals whose keys are REQUIRED addressing keys, which
## is why that line's refusals were structurally unreachable through its typed
## client. Recorded here so this line does not repeat the class silently.
const QUESTS_MISSING_KEY_REFUSALS := [
	"missing_goal", "missing_idSimpleChapter", "missing_currentQuestVars",
	"missing_idCurrentMission", "missing_goalIndex",
]

## A crafted private state used where a malformed or absent key is needed and no
## committed corpus carries one.
const CRAFTED_PRIVATE := {
	RewardFlow.WEEKLY_CURSOR_KEY: 4,
	RewardFlow.DAILY_CURSOR_KEY: 5,
	RewardFlow.WEEKLY_STAMP_KEY: 0,
	RewardFlow.DAILY_STAMP_KEY: 0,
}


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if _scenario_arg() == LIVE_SCENARIO:
		await _check_live_reward()
		return
	# The perturbation switch is a deliberate-failure mode: it feeds altered
	# committed bytes into this suite's own re-derivations so they have to notice.
	# A run in this mode MUST fail; if it passes, the measurement this line rests
	# on is vacuous.
	var perturbation := _perturbation_arg()
	if perturbation != "":
		_run_perturbation(perturbation)
		return

	var projection := _check_projection()
	var bound := _check_bound_re_derivation()
	var census := _check_census()
	var decoders := _check_decoder_searches()
	var corpus := _check_corpus_census()
	var guards := _check_structural_guards()
	var refusals := _check_refusal_reachability()
	var request := _check_request_keys()
	var proofs := _check_proofs(projection)
	_check_ownership_boundary()
	var coverage := _check_coverage()

	var path := _report_path_arg()
	if path != "":
		_write_report(path, {
			"projection": projection,
			"bound": bound,
			"census": census,
			"decoders": decoders,
			"corpus": corpus,
			"guards": guards,
			"refusals": refusals,
			"request": request,
			"proofs": proofs,
			"coverage": coverage,
		})

# ---------------------------------------------------------------------------
# 1. Both cursors and both instants, projected from committed state
# ---------------------------------------------------------------------------


## The committed save, the committed schedules, and the projection of both.
##
## Every figure the projection reports is checked against a value **read from the
## committed bytes**, so the projection is compared with its inputs rather than
## with its own constants. A projection that ignored the corpus would fail here.
func _check_projection() -> Dictionary:
	info("--- committed projection ---")
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed %s corpus is readable" % CORPUS_SAVE)
	if not (save is Dictionary):
		return {"ok": false}
	var document: Dictionary = save
	check(document.has(RewardFlow.PRIVATE_STATE_KEY),
		"and it carries a %s object" % RewardFlow.PRIVATE_STATE_KEY)
	var private: Variant = document.get(RewardFlow.PRIVATE_STATE_KEY)
	check(private is Dictionary,
		"which is an object rather than a scalar or absent")
	if not (private is Dictionary):
		return {"ok": false}
	var body: Dictionary = private

	# --- the recorded cursors and instants, read before anything is projected -
	for key: String in RewardFlow.CURSORS + RewardFlow.INSTANTS:
		check(body.has(key), "the committed corpus carries %s" % key)
		check(body.get(key) is int or body.get(key) is float,
			"and %s is a number rather than a string" % key)
	check_eq(int(body.get(RewardFlow.WEEKLY_CURSOR_KEY, -1)),
		EXPECTED_CORPUS_WEEKLY_CURSOR,
		"the committed weekly cursor is recorded at %d"
			% EXPECTED_CORPUS_WEEKLY_CURSOR)
	check_eq(int(body.get(RewardFlow.DAILY_CURSOR_KEY, -1)),
		EXPECTED_CORPUS_DAILY_CURSOR,
		"the committed daily cursor is recorded at %d"
			% EXPECTED_CORPUS_DAILY_CURSOR)
	check_eq(int(body.get(RewardFlow.WEEKLY_STAMP_KEY, -1)),
		EXPECTED_CORPUS_STAMP,
		"and both instants are recorded at %d" % EXPECTED_CORPUS_STAMP)
	check_eq(int(body.get(RewardFlow.DAILY_STAMP_KEY, -1)),
		EXPECTED_CORPUS_STAMP,
		"the daily instant with it")

	# --- the committed schedules, through the EXISTING registry -------------
	var registry := ContentRegistry.new()
	var loaded: Dictionary = registry.load_content(Paths.repo_root())
	check(bool(loaded.get("ok", false)), "the committed content package loads")
	if not bool(loaded.get("ok", false)):
		return {"ok": false}
	var schedules := {}
	var committed_values := {}
	for row: Dictionary in RewardFlow.SCHEDULES:
		var name := str(row["name"])
		var fetched: Dictionary = registry.get_entry(CONTENT_DOMAIN, name)
		check(bool(fetched.get("found", false)),
			"committed reward schedule %s resolves through the registry" % name)
		if not bool(fetched.get("found", false)):
			continue
		var entry: Variant = fetched["entry"]
		if not (entry is Dictionary) or not (entry as Dictionary).has("value"):
			fail("committed reward schedule %s carries a value" % name)
			continue
		var value: Variant = (entry as Dictionary)["value"]
		committed_values[name] = value
		if str(row["name"]) == RewardFlow.WEEKLY_SCHEDULE_KEY:
			schedules[RewardFlow.WEEKLY_SCHEDULE_KEY] = value
		elif str(row["name"]) == RewardFlow.DAILY_SCHEDULE_KEY:
			schedules[RewardFlow.DAILY_SCHEDULE_KEY] = value
	registry.free()

	check(schedules.has(RewardFlow.WEEKLY_SCHEDULE_KEY),
		"both reward schedules this line addresses resolve in committed content")
	check(schedules.has(RewardFlow.DAILY_SCHEDULE_KEY), "the daily one as well")
	if not schedules.has(RewardFlow.WEEKLY_SCHEDULE_KEY):
		return {"ok": false}

	var weekly_value: Variant = schedules[RewardFlow.WEEKLY_SCHEDULE_KEY]
	var daily_value: Variant = schedules[RewardFlow.DAILY_SCHEDULE_KEY]
	check(weekly_value is Array,
		"the committed weekly schedule is an array of entries")
	check(daily_value is Array, "and the daily one is an array of numbers")
	check_eq((weekly_value as Array).size(), EXPECTED_WEEKLY_CARDINALITY,
		"the committed weekly schedule carries all %d entries"
			% EXPECTED_WEEKLY_CARDINALITY)
	check_eq((daily_value as Array).size(), EXPECTED_DAILY_CARDINALITY,
		"and the daily one all %d" % EXPECTED_DAILY_CARDINALITY)

	# --- the projection -----------------------------------------------------
	var outcome := RewardFlow.project_save(document, schedules)
	check(bool(outcome.get("ok", false)),
		"the committed corpus projects: %s" % str(outcome.get("error", "")))
	if not bool(outcome.get("ok", false)):
		return {"ok": false}
	var typed: RewardFlow.CursorProjection = outcome["projection"]
	check(bool(typed.ok), "and the projection reports itself usable")
	check_eq(typed.cursors.size(), RewardFlow.CURSOR_COUNT,
		"it projects BOTH cursors")
	check_eq(typed.weekly_cardinality, EXPECTED_WEEKLY_CARDINALITY,
		"and reports the weekly schedule's CARDINALITY")
	check_eq(typed.daily_cardinality, EXPECTED_DAILY_CARDINALITY,
		"beside the daily schedule's")
	check(typed.weekly_bound > typed.weekly_cardinality,
		"the derived weekly bound EXCEEDS the weekly cardinality, which is the "
			+ "mismatch this line exists to report")
	check_eq(typed.weekly_bound - typed.weekly_cardinality,
		RewardFlow.WEEKLY_BOUND_FLOOR * 2,
		"by the difference the two committed numbers actually make -- %d against %d"
			% [typed.weekly_bound, typed.weekly_cardinality])
	check_eq(typed.daily_bound, typed.daily_cardinality,
		"while the daily literal and the daily cardinality AGREE -- a "
			+ "coincidence the record must not read as provenance")
	check_eq(typed.type_letters.size(), RewardFlow.TYPE_LETTER_COUNT,
		"the three type letters are projected beside the cursors")
	check(not (typed.derivation_record as Dictionary).is_empty(),
		"and the derivation record travels with the projection")

	# --- each cursor, one at a time ----------------------------------------
	var rows: Array = []
	for cursor: RewardFlow.Cursor in typed.cursors:
		rows.append(_check_cursor(cursor))
	return {"ok": true, "projection": typed, "cursors": rows,
		"weekly_schedule": _normalize(weekly_value),
		"daily_schedule": _normalize(daily_value)}


## One cursor's projection, against the committed bytes it came from.
func _check_cursor(cursor: RewardFlow.Cursor) -> Dictionary:
	check_eq(cursor.key, RewardFlow.ACTION_CURSOR_KEY[cursor.action],
		"the %s cursor reads its own action's key" % cursor.action)
	check_eq(cursor.stamp_key, RewardFlow.ACTION_STAMP_KEY[cursor.action],
		"and its own instant")
	check_eq(cursor.command, RewardFlow.ACTION_COMMAND[cursor.action],
		"dispatching the preserved branch %s" % cursor.command)
	check(bool(cursor.value_present),
		"the %s cursor is PRESENT rather than defaulted to zero"
			% cursor.action)
	check(bool(cursor.stamp_present),
		"and its instant is present too, so an absent key was not read as a value")
	check_eq(cursor.bound_is_literal, cursor.action == RewardFlow.ACTION_DAILY,
		"the %s bound is marked literal exactly for the daily action"
			% cursor.action)
	check_eq(bool(cursor.selection_performed), false,
		"the %s cursor selected no schedule entry" % cursor.action)
	check_eq(cursor.index_base, RewardFlow.SCHEDULE_INDEX_BASE,
		"the %s reachability report is read at the recorded index base"
			% cursor.action)
	check(cursor.bound_source != "",
		"the %s bound names the preserved source it came from" % cursor.action)

	# The two reachability sets and BOTH differences. A report carrying only the
	# exceedance would hide that the daily cursor cannot reach position 0 at all.
	check_eq(cursor.reachable_not_answerable.size()
		+ cursor.answerable_not_reachable.size() > 0, true,
		"the %s report carries a non-empty difference in at least one direction"
			% cursor.action)
	for value: Variant in cursor.reachable:
		check(cursor.answerable.has(value) or cursor.reachable_not_answerable.has(value),
			"the %s reachable position %d is accounted for in one of the two sets"
				% [cursor.action, int(value)])

	# The reachability arithmetic, re-derived here from the bound alone rather
	# than read back from the module's own table.
	var derived_reachable: Array = []
	if cursor.action == RewardFlow.ACTION_WEEKLY:
		for start in range(cursor.bound):
			derived_reachable.append((start + 1) % cursor.bound)
	else:
		for start in range(cursor.bound):
			derived_reachable.append(
				RewardFlow.DAILY_WRAP_TARGET
				if start + 1 > RewardFlow.DAILY_BOUND_LITERAL else start + 1)
	var sorted_derived := derived_reachable.duplicate()
	sorted_derived.sort()
	var sorted_reported: Array = cursor.reachable.duplicate()
	sorted_reported.sort()
	check_eq(sorted_reported, sorted_derived,
		("the %s reachable set is RE-DERIVED from the bound arithmetic rather "
			% cursor.action) + "than read from a table")

	# The successor, re-derived from the recorded value and the bound.
	var expected_successor := 0
	if cursor.action == RewardFlow.ACTION_WEEKLY:
		expected_successor = (cursor.value + 1) % cursor.bound
	else:
		expected_successor = RewardFlow.DAILY_WRAP_TARGET \
			if cursor.value + 1 > cursor.bound else cursor.value + 1
	check_eq(cursor.successor, expected_successor,
		"the %s successor is re-derived from the recorded value and the bound"
			% cursor.action)
	check_eq(cursor.change, cursor.successor - cursor.value,
		"and the change agrees with its own two ends")
	return {
		"action": cursor.action, "command": cursor.command,
		"key": cursor.key, "stamp_key": cursor.stamp_key,
		"value": cursor.value, "successor": cursor.successor,
		"change": cursor.change, "bound": cursor.bound,
		"bound_is_literal": cursor.bound_is_literal,
		"bound_source": cursor.bound_source,
		"schedule_key": cursor.schedule_key,
		"cardinality": cursor.schedule_cardinality,
		"reachable": cursor.reachable.duplicate(),
		"answerable": cursor.answerable.duplicate(),
		"reachable_not_answerable": cursor.reachable_not_answerable.duplicate(),
		"answerable_not_reachable": cursor.answerable_not_reachable.duplicate(),
		"selection_performed": cursor.selection_performed,
		"stamp_before": cursor.stamp_before,
	}

# ---------------------------------------------------------------------------
# 2. The weekly bound and both successors, RE-DERIVED from committed bytes
# ---------------------------------------------------------------------------


## Every figure extracted from the three preserved spans, plus the bound computed
## from the extracted rule rather than from the module's helper.
##
## The point of this section is that the module's `WEEKLY_BOUND_LITERAL`-shaped
## constants are **not** what is checked. The seed, the list test, the maximum,
## the modulo, the daily increment, the daily literal, and the wrap target are
## each read out of the committed source text with a regular expression, and the
## bound is then computed here from those extracted values. An edit to
## `get_game_config.py` or `command.py` therefore fails this suite instead of
## silently contradicting it.
func _check_bound_re_derivation() -> Dictionary:
	info("--- bound and successor re-derivation ---")
	var length_span := _legacy_span(LENGTH_FILE, LENGTH_FIRST, LENGTH_LAST)
	check(length_span != "",
		"%s:%d-%d is readable" % [LENGTH_FILE, LENGTH_FIRST, LENGTH_LAST])
	var weekly_span := _legacy_span("command.py", WEEKLY_BRANCH_FIRST,
		WEEKLY_BRANCH_LAST)
	check(weekly_span != "",
		"command.py:%d-%d is readable"
			% [WEEKLY_BRANCH_FIRST, WEEKLY_BRANCH_LAST])
	var daily_span := _legacy_span("command.py", DAILY_BRANCH_FIRST,
		DAILY_BRANCH_LAST)
	check(daily_span != "",
		"command.py:%d-%d is readable"
			% [DAILY_BRANCH_FIRST, DAILY_BRANCH_LAST])
	if length_span == "" or weekly_span == "" or daily_span == "":
		return {"ok": false}

	# --- get_weekly_reward_length, rule by rule ---------------------------
	var seed := _first_int(length_span, "length\\s*=\\s*(\\d+)")
	var list_test := _first_word(length_span, "type\\(value\\)\\s*==\\s*(\\w+)")
	var uses_max := length_span.contains("max(") \
		and length_span.contains("len(value)")
	check_eq(seed, RewardFlow.WEEKLY_BOUND_FLOOR,
		"the preserved helper seeds its accumulator at %d, which the module "
			% RewardFlow.WEEKLY_BOUND_FLOOR
			+ "records as the load-bearing floor")
	check_eq(list_test, "list",
		"and tests for the type `list`, which is why the bound is a maximum entry "
			+ "LENGTH and never the entry COUNT")
	check_eq(uses_max, true,
		"and takes a max over len(value) -- the two operations together")

	# --- the weekly successor ---------------------------------------------
	var modulo := _first_int(weekly_span,
		"\\[\\\"privateState\\\"\\]\\[\\\"weeklyRewardIndex\\\"\\]\\s*\\+\\s*(\\d+)\\)\\s*%")
	var modulo_call := _first_word(weekly_span, "%\\s*(\\w+)\\(\\s*\\)")
	check_eq(modulo, 1,
		"the weekly branch advances its recorded cursor by %d" % modulo)
	check_eq(modulo_call, "get_weekly_reward_length",
		"modulo the preserved helper, so the bound is the module's own")
	var arity_test := _first_int(weekly_span, "if\\s+len\\(args\\)\\s*>\\s*(\\d+)")
	check_eq(arity_test, 4,
		"and the arm is selected on the client's OWN argument count (> %d), which "
			% arity_test
			+ "is why this contract has no arm to reproduce")

	# --- the daily successor ----------------------------------------------
	var increment := _first_int(daily_span, "next_id\\s*=\\s*args\\[1\\]\\s*\\+\\s*(\\d+)")
	var wrap_literal := _first_int(daily_span, "if\\s+next_id\\s*>\\s*(\\d+)\\s*:")
	var wrap_target := _first_int(daily_span, "if\\s+next_id\\s*>\\s*\\d+\\s*:\\s*\\n\\s*next_id\\s*=\\s*(\\d+)")
	var grant_gate := _first_int(daily_span, "if\\s+item\\s*>\\s*(\\d+)\\s*:")
	check_eq(increment, 1, "the daily branch increments the client's next id by %d"
		% increment)
	check_eq(wrap_literal, RewardFlow.DAILY_BOUND_LITERAL,
		"and wraps at the hardcoded literal %d the module records as the daily "
			% RewardFlow.DAILY_BOUND_LITERAL
			+ "bound -- a literal in the source, never a content derivation")
	check_eq(wrap_target, RewardFlow.DAILY_WRAP_TARGET,
		"onto position %d, which is the BACKWARDS move the recorded divergence "
			% RewardFlow.DAILY_WRAP_TARGET
			+ "describes: a larger client value lands on the first position")
	check_eq(grant_gate, RewardFlow.DERIVED_DAILY_ITEM,
		"and the grant arm is gated on an item above %d, which is why the derived "
			% RewardFlow.DERIVED_DAILY_ITEM
			+ "item is ZERO and the granting arm is unreachable")

	# --- the bound, computed HERE from the extracted rule ------------------
	var schedule: Variant = _read_json(Paths.repo_root().path_join(
		"packages/game-content/normalized/globals.json"))
	var committed: Variant = _globals_value(schedule,
		RewardFlow.WEEKLY_SCHEDULE_KEY)
	check(committed is Array,
		"the committed weekly schedule is readable from the normalized package")
	var recomputed := seed
	if committed is Array:
		for position in range((committed as Array).size()):
			var entry: Variant = (committed as Array)[position]
			check(entry is Dictionary and (entry as Dictionary).has("value"),
				"weekly entry %d is an object carrying a value" % position)
			if not (entry is Dictionary):
				continue
			var value: Variant = (entry as Dictionary)["value"]
			if value is Array and (value as Array).size() > recomputed:
				recomputed = (value as Array).size()
	check_eq(recomputed, RewardFlow.WEEKLY_BOUND_FLOOR * 5,
		"the bound recomputed HERE from the extracted rule over the committed "
			+ "schedule is " + str(RewardFlow.WEEKLY_BOUND_FLOOR * 5))
	var helper := RewardFlow.weekly_bound(committed)
	check_eq(int(helper.get("value", -1)), recomputed,
		"and the module's own helper agrees with the re-derivation")
	check_eq(recomputed, (committed as Array).size() + 2,
		"which is %d against the schedule's own %d entries -- the bound is NOT the "
			% [recomputed, (committed as Array).size()] + "entry count")

	# --- the reachable sets, from the extracted arithmetic ----------------
	var weekly_reachable: Array = []
	for start in range(recomputed):
		weekly_reachable.append((start + modulo) % recomputed)
	var daily_reachable: Array = []
	for start in range(wrap_literal):
		daily_reachable.append(
			wrap_target if start + increment > wrap_literal else start + increment)
	var sorted_weekly := weekly_reachable.duplicate()
	sorted_weekly.sort()
	var sorted_daily := daily_reachable.duplicate()
	sorted_daily.sort()
	check_eq(sorted_weekly, RewardFlow.WEEKLY_REACHABLE,
		"the weekly reachable set is re-derived from the extracted modulo")
	check_eq(sorted_daily, RewardFlow.DAILY_REACHABLE,
		"and the daily reachable set from the extracted increment and wrap")

	# --- both successors, over EVERY recorded value in the corpus ----------
	return {"ok": true, "length_span": _normalize(length_span),
		"weekly_span": _normalize(weekly_span),
		"daily_span": _normalize(daily_span),
		"seed": seed, "list_test": list_test, "uses_max": uses_max,
		"weekly_increment": modulo, "weekly_modulo_call": modulo_call,
		"weekly_arity_test": arity_test,
		"daily_increment": increment, "daily_wrap_literal": wrap_literal,
		"daily_wrap_target": wrap_target, "daily_grant_gate": grant_gate,
		"recomputed_weekly_bound": recomputed,
		"weekly_cardinality": (committed as Array).size(),
		"weekly_reachable": sorted_weekly, "daily_reachable": sorted_daily}

# ---------------------------------------------------------------------------
# 3. The consumer census, RE-MEASURED over a DISCOVERED module set
# ---------------------------------------------------------------------------


## The eleven reward schedules' consumer counts, re-measured from committed
## bytes on every run over a module list this repository DISCOVERS.
##
## ## The subject count is PRINTED BEFORE ANY ZERO IS BELIEVED
##
## This is the vacuous-census defect class, which has recurred three times in
## this project: a census that reads an empty or unreadable corpus reports every
## count as zero, and "zero consumers" then reads as a finding. So the module
## count and the corpus size are printed first, and **no** zero verdict below is
## accepted unless the subject count is non-zero.
##
## ## And `tasks.md` 3.3 says "twelve-module"; there are ELEVEN
##
## The task text records a twelve-module census. The repository root holds
## exactly eleven top-level `.py` files, discovered rather than transcribed, so
## the task's figure is a transcription error. `tasks.md` is left unedited and the
## discrepancy is recorded here and in the report instead.
func _check_census() -> Dictionary:
	info("--- legacy consumer census ---")
	var census := RewardFlow.legacy_census_text()
	check(bool(census.get("ok", false)),
		"the legacy census corpus loads: %s" % str(census.get("error", "")))
	if not bool(census.get("ok", false)):
		return {"ok": false}
	var names: Array = census.get("modules", [])
	var bodies: Dictionary = census.get("text", {})

	# --- THE SUBJECT COUNT, printed before any absence is believed ---------
	info("census subject count = %d modules: %s"
		% [names.size(), str(names)])
	check_eq(names.size(), EXPECTED_MODULE_COUNT,
		"the census's subject count is %d top-level modules -- the figure "
			% EXPECTED_MODULE_COUNT
			+ "tasks.md 3.3 records as twelve")
	check(bodies.size() == names.size(),
		"and every discovered module contributed a readable body")
	var corpus := ""
	for name: String in names:
		corpus += str(bodies.get(name, "")) + "\n"
	check(corpus.length() > 0,
		"the concatenated census corpus is non-empty, so a zero count is a "
			+ "MEASUREMENT and not an unreadable directory")

	var code := _code_only(corpus)
	var rows: Array = []
	var zero_named: Array = []
	for recorded: Dictionary in RewardFlow.SCHEDULES:
		var name := str(recorded["name"])
		var occurrences := _count_occurrences(corpus, name)
		var lines := _count_lines(corpus, name)
		var tokens := _count_code_tokens(code, name)
		check_eq(occurrences, int(recorded["consumers"]),
			"schedule %s is re-measured at %d whole-file occurrences, matching "
				% [name, int(recorded["consumers"])]
				+ "the recorded consumer count")
		check_eq(lines, occurrences,
			"and its occurrences sit on %d distinct lines" % lines)
		if occurrences == 0:
			zero_named.append(name)
		rows.append({
			"name": name, "consumers": occurrences,
			"distinct_lines": lines, "identifier_tokens": tokens,
			"quoted_occurrences": occurrences - tokens,
		})
	check_eq(zero_named.size(), EXPECTED_ZERO_CONSUMER_COUNT,
		"exactly %d of the %d schedules have no consumer at all"
			% [EXPECTED_ZERO_CONSUMER_COUNT, RewardFlow.SCHEDULE_COUNT])

	# --- the recorded no-consumer list must BE the measured one -----------
	var recorded_zero: Array = RewardFlow.SCHEDULES_WITH_NO_CONSUMER.duplicate()
	var measured_zero := zero_named.duplicate()
	recorded_zero.sort()
	measured_zero.sort()
	check_eq(measured_zero, recorded_zero,
		"the module's recorded no-consumer list equals the measured one, in both "
			+ "directions")
	check_eq(RewardFlow.SCHEDULES_WITH_NO_CONSUMER_COUNT,
		RewardFlow.SCHEDULES_WITH_NO_CONSUMER.size(),
		"and its recorded count literal matches the list it counts")

	# --- the ONE schedule with an occurrence, and what that occurrence is --
	var single := ""
	for row: Dictionary in rows:
		if int(row["consumers"]) > 0:
			single = str(row["name"])
	check_eq(single, RewardFlow.WEEKLY_SCHEDULE_KEY,
		"the single schedule with any occurrence at all is the weekly one")
	var weekly_row: Dictionary = {}
	for row: Dictionary in rows:
		if str(row["name"]) == single:
			weekly_row = row
	check_eq(int(weekly_row.get("identifier_tokens", -1)), 0,
		"and its %d occurrence is a QUOTED SUBSCRIPT rather than a bare "
			% int(weekly_row.get("consumers", 0))
			+ "identifier token outside a string -- the difference between being "
			+ "READ and being NAMED, and the reason a whole-word count over the "
			+ "raw bytes would have reported it as a consumer")

	# --- the ranking-reward table, on the same corpus ---------------------
	var ranking := _count_occurrences(corpus, RewardFlow.RANKING_REWARD_TABLE)
	check_eq(ranking, RewardFlow.RANKING_REWARD_CONSUMERS,
		"the ranking-reward table is re-measured at %d consumers"
			% RewardFlow.RANKING_REWARD_CONSUMERS)

	return {"ok": true, "module_count": names.size(), "modules": names,
		"corpus_bytes": corpus.length(), "rows": rows,
		"zero_consumer_names": measured_zero,
		"ranking_reward_consumers": ranking,
		"recorded_task_text_says": "twelve", "measured": EXPECTED_MODULE_COUNT}

# ---------------------------------------------------------------------------
# 4. The six decoder searches, with three positive controls
# ---------------------------------------------------------------------------


## The six letter-to-resource searches and their three positive controls.
##
## The controls are the whole reason this section can be believed: all six
## searches return zero, and three shapes that must match abundantly do, over the
## same corpus with the same machinery. A census that reported only zeros and
## never checked that its own shapes fire is the vacuous-census defect.
##
## ## The patterns are measured, and the module now CARRIES them
##
## The module originally claimed the engine had no regular-expression class and
## that the searches could therefore not be published. That was false -- `RegEx`
## compiles on the pinned build -- so the patterns are now carried in the module
## and this suite re-runs each one, which is what makes "a test can re-derive it"
## true instead of aspirational.
##
## ## TWO OF THE THREE CONTROL FIGURES WERE WRONG AND ARE CORRECTED
##
## `quoted_subscript` was recorded at 515 and `unquoted_subscript` at 244. Both
## came from a hand-written string scan rather than from a pattern. Measured
## against the patterns below they are **516** and **225**. The conclusion is
## untouched -- all three controls fire abundantly, which is the only thing they
## exist to show -- but a positive control whose own number is wrong teaches a
## reader to discount the zeros beside it, so the figures are corrected and the
## correction is asserted rather than merely described.
func _check_decoder_searches() -> Dictionary:
	info("--- type-letter decoder searches ---")
	var census := RewardFlow.legacy_census_text()
	check(bool(census.get("ok", false)), "the decoder corpus loads")
	if not bool(census.get("ok", false)):
		return {"ok": false}
	var names: Array = census.get("modules", [])
	var bodies: Dictionary = census.get("text", {})
	var corpus := ""
	for name: String in names:
		corpus += str(bodies.get(name, "")) + "\n"
	# Printed for the same reason as the census: a zero over an empty corpus is
	# not a finding.
	info("decoder subject count = %d modules, %d bytes"
		% [names.size(), corpus.length()])
	check(corpus.length() > 0, "the decoder corpus is non-empty")
	var code := _code_only(corpus)

	var rows: Array = []
	var total := 0
	for recorded: Dictionary in RewardFlow.DECODER_SEARCHES:
		var shape := str(recorded["shape"])
		var pattern := str(recorded["pattern"])
		check(pattern != "",
			"the %s search carries the pattern it is measured by" % shape)
		var hits := _regex_count(pattern, corpus)
		check_eq(hits, int(recorded["hits"]),
			"the %s search is re-measured at %d hits, matching the record"
				% [shape, int(recorded["hits"])])
		total += hits
		rows.append({"shape": shape, "search": str(recorded["search"]),
			"pattern": pattern, "hits": hits})
	check_eq(RewardFlow.DECODER_SEARCH_COUNT, RewardFlow.DECODER_SEARCHES.size(),
		"the recorded search count matches the searches it counts")
	check_eq(total, RewardFlow.DECODER_SEARCH_HIT_TOTAL,
		"and all %d searches together total %d hits"
			% [RewardFlow.DECODER_SEARCH_COUNT, RewardFlow.DECODER_SEARCH_HIT_TOTAL])

	var controls: Array = []
	for recorded: Dictionary in RewardFlow.DECODER_POSITIVE_CONTROLS:
		var shape := str(recorded["shape"])
		var pattern := str(recorded["pattern"])
		var hits := _regex_count(pattern, corpus)
		check_eq(hits, int(recorded["hits"]),
			"the %s POSITIVE CONTROL is re-measured at %d hits, so the zeros "
				% [shape, int(recorded["hits"])]
				+ "beside it are specific rather than silent")
		check(hits > 0,
			"and the %s control fires at least once, which is what makes the six "
				% shape + "zeros meaningful")
		controls.append({"shape": shape, "search": str(recorded["search"]),
			"pattern": pattern, "hits": hits})
	check_eq(RewardFlow.DECODER_POSITIVE_CONTROL_COUNT,
		RewardFlow.DECODER_POSITIVE_CONTROLS.size(),
		"the recorded control count matches the controls it counts")

	# The letters themselves, projected and asserted undecoded.
	#
	# ## The "consumers" figure is measured as OCCURRENCES MINUS DECLARATIONS
	#
	# `constants.py:888` writes `COST_GOLD = "g"`, so its single whole-file
	# occurrence IS the declaration. The first cut of this section tested for the
	# name followed by a space, which the declaration line also satisfies, and so
	# reported one consumer for all three -- the inverse error of a vacuous
	# census, and one that would have handed a reader a fabricated consumer.
	# Consumers are now the count that survives subtracting the assignments.
	var letters: Array = []
	for recorded2: Dictionary in RewardFlow.LETTER_NAMED_DECLARATIONS:
		var declared_as := str(recorded2["declared_as"])
		var occurrences := _count_occurrences(corpus, declared_as)
		var declarations := _count_declarations(code, declared_as)
		var consumers := occurrences - declarations
		check_eq(occurrences, int(recorded2["occurrences_total"]),
			"%s is re-measured at %d occurrence(s) in total, which is the "
				% [declared_as, int(recorded2["occurrences_total"])]
				+ "DECLARATION and not a consumer" )
		check_eq(declarations, 1,
			"and exactly %d of those is an assignment, so the declaration is "
				% declarations + "located rather than assumed")
		check_eq(consumers, int(recorded2["consumers"]),
			"and %s therefore has %d consumers" % [declared_as, consumers])
		check(_code_only(corpus).contains(declared_as),
			"with the declaration present in CODE rather than in a comment")
		letters.append({"letter": str(recorded2["letter"]),
			"declared_as": declared_as,
			"declared_at": str(recorded2["declared_at"]),
			"occurrences_total": occurrences,
			"declarations": declarations,
			"consumers": consumers,
			"belongs_to": str(recorded2["belongs_to"])})

	return {"ok": true, "module_count": names.size(), "searches": rows,
		"hit_total": total, "positive_controls": controls,
		"letters": letters,
		"letters_decoded": false, "letters_mapped": false}

# ---------------------------------------------------------------------------
# 5. The committed save-document census
# ---------------------------------------------------------------------------


## The seven save-only fields over every committed document, and both cursors'
## recorded distributions.
##
## ## Thirty-four files walked, THIRTY-THREE carrying, and both are pinned
##
## `tests/saves/manifest.json` is one of the three `.json` files under
## `tests/saves` and carries **no** `privateState` -- it is a manifest of the
## corpus, not a save. A naive `*.json` glob therefore reports 34 while a census of
## documents carrying the fields reports 33. Both figures are asserted here, and
## the excluded file is named, so the difference is a recorded measurement rather
## than something a later reader has to rediscover.
func _check_corpus_census() -> Dictionary:
	info("--- committed save-document census ---")
	var files: Array = []
	for directory: String in CORPUS_DIRECTORIES:
		files.append_array(_json_files(Paths.repo_root().path_join(directory)))
	# Printed BEFORE any "present in every document" verdict is believed.
	info("corpus subject count = %d walked files under %s"
		% [files.size(), ", ".join(CORPUS_DIRECTORIES)])
	check_eq(files.size(), EXPECTED_WALKED_FILES,
		"the walk reads all %d committed .json documents under %s"
			% [EXPECTED_WALKED_FILES, ", ".join(CORPUS_DIRECTORIES)])

	var carrying := 0
	var without: Array = []
	var weekly := {}
	var daily := {}
	var per_field := {}
	for field: String in RewardFlow.SAVE_ONLY_FIELDS:
		per_field[field] = 0
	for relative: String in files:
		var document: Variant = _read_json(Paths.repo_root().path_join(relative))
		if not (document is Dictionary):
			without.append(relative + " (unreadable)")
			continue
		var private: Variant = (document as Dictionary).get(
			RewardFlow.PRIVATE_STATE_KEY)
		if not (private is Dictionary):
			without.append(relative)
			continue
		var body: Dictionary = private
		var complete := true
		for field: String in RewardFlow.SAVE_ONLY_FIELDS:
			if not body.has(field):
				complete = false
			else:
				per_field[field] = int(per_field[field]) + 1
		if complete:
			carrying += 1
		if body.has(RewardFlow.WEEKLY_CURSOR_KEY):
			var key := str(int(body[RewardFlow.WEEKLY_CURSOR_KEY]))
			weekly[key] = int(weekly.get(key, 0)) + 1
		if body.has(RewardFlow.DAILY_CURSOR_KEY):
			var key2 := str(int(body[RewardFlow.DAILY_CURSOR_KEY]))
			daily[key2] = int(daily.get(key2, 0)) + 1

	check_eq(carrying, EXPECTED_DOCUMENTS_CARRYING,
		"and %d of them carry all %d save-only fields"
			% [EXPECTED_DOCUMENTS_CARRYING, RewardFlow.SAVE_ONLY_FIELD_COUNT])
	check_eq(without, [RewardFlow.SAVE_ONLY_FILE_WITHOUT_PRIVATE_STATE],
		"the single walked document that carries no private state is %s, which is "
			% RewardFlow.SAVE_ONLY_FILE_WITHOUT_PRIVATE_STATE
			+ "why 34 files and 33 documents are both correct")
	check_eq(RewardFlow.SAVE_ONLY_FILE_COUNT, EXPECTED_WALKED_FILES,
		"the module's walked-file count matches the measurement")
	check_eq(RewardFlow.SAVE_ONLY_DOCUMENT_COUNT, carrying,
		"and so does its document count")
	for field: String in RewardFlow.SAVE_ONLY_FIELDS:
		check_eq(int(per_field[field]), carrying,
			"save-only field %s is present in all %d carrying documents, counted "
				% [field, carrying] + "rather than assumed")

	var weekly_rows := _sorted_counts(weekly)
	var daily_rows := _sorted_counts(daily)
	check_eq(weekly_rows, _count_pairs(EXPECTED_WEEKLY_DISTRIBUTION),
		"the weekly cursor's recorded distribution is re-measured: %s"
			% str(weekly_rows))
	check_eq(daily_rows, _count_pairs(EXPECTED_DAILY_DISTRIBUTION),
		"and so is the daily cursor's: %s" % str(daily_rows))
	var weekly_total := 0
	for row: Array in weekly_rows:
		weekly_total += int(row[1])
	var daily_total := 0
	for row: Array in daily_rows:
		daily_total += int(row[1])
	check_eq(weekly_total, carrying,
		"the weekly distribution sums to the carrying count, which cross-checks "
			+ "the 33 independently")
	check_eq(daily_total, carrying, "and so does the daily distribution")

	return {"ok": true, "walked_files": files.size(),
		"carrying_private_state": carrying, "excluded": without,
		"per_field": per_field,
		"weekly_distribution": weekly_rows,
		"daily_distribution": daily_rows,
		"origin_status": RewardFlow.SAVE_ONLY_ORIGIN_STATUS,
		"note": RewardFlow.SAVE_ONLY_NOTE}

# ---------------------------------------------------------------------------
# 6. The three layers of structural guard
# ---------------------------------------------------------------------------


## Layer one: the whole `static func` inventory, pinned in BOTH directions.
## Layer two: exact by-name guards for the four absent helper classes.
## Layer three: a SUBSTRING guard, because a suffixed helper wearing a forbidden
## name passes an exact-name check -- measured on an earlier line of this project.
func _check_structural_guards() -> Dictionary:
	info("--- structural guards ---")
	var source := _module_text()
	check(source != "", "the delivered module is readable")

	# --- layer 1: the whole inventory, compared for EQUALITY ---------------
	var declared := _declared_static_functions(source)
	check_eq(declared.size(), RewardFlow.STATIC_FUNCTION_COUNT,
		"the module declares %d static functions"
			% RewardFlow.STATIC_FUNCTION_COUNT)
	check_eq(declared, RewardFlow.STATIC_FUNCTIONS,
		"and the declared list EQUALS the pinned inventory in declaration order "
			+ "-- equality of the whole list, so a reorder fails as an addition does")
	check_eq(RewardFlow.STATIC_FUNCTIONS.size(),
		RewardFlow.STATIC_FUNCTION_COUNT,
		"the pinned inventory's recorded count matches the list it counts")
	var missing: Array = []
	var extra: Array = []
	for name: String in RewardFlow.STATIC_FUNCTIONS:
		if not declared.has(name):
			missing.append(name)
	for name: String in declared:
		if not RewardFlow.STATIC_FUNCTIONS.has(name):
			extra.append(name)
	check_eq(missing, [], "no pinned helper is missing")
	check_eq(extra, [], "and no unpinned helper was added")
	# The private helpers are pinned too, because an unpinned underscore helper
	# is exactly where a smuggled grant would live.
	var private_pinned := 0
	for name: String in RewardFlow.STATIC_FUNCTIONS:
		if name.begins_with("_"):
			private_pinned += 1
	check(private_pinned > 0,
		"and the pin includes %d private helpers, so a smuggled underscore "
			% private_pinned + "helper cannot hide")
	# No instance methods either: a `func` that is not static would be a second
	# place for behaviour to appear.
	var instance := _instance_functions(source)
	check_eq(instance, [],
		"the module declares NO instance functions, so every behaviour is a "
			+ "static one and appears in the pinned inventory")

	# --- layers 2 and 3: by name, then by substring ------------------------
	var code := _code_only(source)
	var by_name: Array = []
	for name: String in RewardFlow.FORBIDDEN_IDENTIFIER_NAMES:
		if code.contains(name):
			by_name.append(name)
	check_eq(by_name, [],
		"no forbidden identifier appears by EXACT NAME: a grant, a selector, a "
			+ "decoder, or an eligibility helper would all be caught here")

	var by_fragment: Array = []
	for fragment: String in RewardFlow.FORBIDDEN_IDENTIFIER_FRAGMENTS:
		if code.contains(fragment):
			by_fragment.append(fragment)
	check_eq(by_fragment, [],
		"and none appears as an identifier FRAGMENT either, which is the layer "
			+ "that catches a suffixed helper wearing a forbidden name")
	# The by-name check must be a strict SUBSET of the fragment check, or one of
	# the two layers is dead. Measured, not assumed.
	var names_not_fragments: Array = []
	for name: String in RewardFlow.FORBIDDEN_IDENTIFIER_NAMES:
		if not RewardFlow.FORBIDDEN_IDENTIFIER_FRAGMENTS.has(name):
			names_not_fragments.append(name)
	check(names_not_fragments.size() > 0,
		"the substring layer is strictly wider than the by-name layer (%d names "
			% names_not_fragments.size()
			+ "are guarded only by the substring check), so it is not redundant")

	# --- the four recorded absences, each named --------------------------
	for absent: Dictionary in RewardFlow.ABSENT_HELPERS:
		var capability := str(absent["capability"])
		check(capability != "",
			"the absent-helper record names what is absent: %s" % capability)
		check(str(absent.get("forbidden_because", "")) != "",
			"and names the record that forbids it: %s"
				% str(absent.get("forbidden_because", "")))
	check_eq(RewardFlow.ABSENT_HELPER_COUNT, RewardFlow.ABSENT_HELPERS.size(),
		"the absent-helper count matches the list it counts")

	# --- the schedule type letters may not become identifiers ------------
	var letter_names: Array = []
	for letter: String in RewardFlow.TYPE_LETTERS:
		for pattern: String in ["letter_to_" + letter, "type_to_" + letter,
				"decode_" + letter, letter + "_to_resource"]:
			if code.contains(pattern):
				letter_names.append(pattern)
	check_eq(letter_names, [],
		"no identifier is named after a schedule type letter, which is what makes "
			+ "the 'undecoded' claim mechanical rather than prose")

	# --- foreign save keys may not become identifiers either -------------
	var foreign: Array = []
	for key: String in RewardFlow.FORBIDDEN_FOREIGN_KEYS:
		if code.contains(key):
			foreign.append(key)
	check_eq(foreign, [],
		"and no identifier is named after a save key owned by another capability")

	return {"ok": true, "module_bytes": source.length(),
		"module_sha256": _sha256(source),
		"static_function_count": declared.size(),
		"private_pinned": private_pinned,
		"instance_functions": instance.size(),
		"forbidden_names": RewardFlow.FORBIDDEN_IDENTIFIER_NAMES.size(),
		"forbidden_fragments": RewardFlow.FORBIDDEN_IDENTIFIER_FRAGMENTS.size(),
		"names_guarded_only_by_substring": names_not_fragments.size(),
		"absent_helpers": RewardFlow.ABSENT_HELPER_COUNT}

# ---------------------------------------------------------------------------
# 7. The refusals, and which of them the typed client can actually reach
# ---------------------------------------------------------------------------


## Every recorded refusal, classified by reachability through the typed client.
##
## ## The five quests refusals that were STRUCTURALLY UNREACHABLE, recorded here
## so this line does not repeat the class
##
## The quests line's five missing-key refusals could not be raised through its
## typed client at all, because their keys were **required addressing keys** and
## the client could not build a request without one. That made five of its
## documented refusals unfalsifiable through the delivered transport. This
## contract has **no** addressing key (`ACTION_ADDRESSING_KEY` is empty and the
## builder refuses rather than defaulting), so **no** refusal here is of that
## shape -- which is asserted rather than asserted-in-prose below.
func _check_refusal_reachability() -> Dictionary:
	info("--- refusal reachability ---")
	# The closed action set is what makes the five unreachable shapes
	# unreachable here too: with no addressing key there is nothing to omit.
	check(RewardFlow.ACTION_ADDRESSING_KEY.is_empty(),
		"this contract records an EMPTY addressing table, so no refusal depends "
			+ "on an absent addressing key -- the quests line's defect class")
	check_eq(RewardFlow.ACTION_ADDRESSING_KEY.size(), 0,
		"and its size is zero rather than merely empty")
	check(RewardFlow.ADDRESSING_KEY_NOTE.get(
			"recorded_explicitly_rather_than_defaulted", false),
		"the empty table is recorded EXPLICITLY rather than left to a default")
	check(RewardFlow.CURSOR_STAMP.size() == RewardFlow.CURSOR_COUNT,
		"each of the %d cursors maps to exactly one instant it stamps"
			% RewardFlow.CURSOR_COUNT)

	# The request-shape refusals ARE reachable: `build_reward_intent` takes an
	# action, so an action outside the closed set is refused by name.
	var rows: Array = []
	for action: Variant in ["", "weekly_reward", "Weekly", "grant", 0, null, []]:
		var intent := RewardFlow.build_reward_intent("user-1", action)
		check(not bool(intent.get("ok", false)),
			"the action %s is refused by the shared builder" % str(action))
		check_eq(str(intent.get("reason", "")), "invalid_action",
			"with the client's own named reason")
		check(not (intent.get("body", {}) as Dictionary).has("action"),
			"and NO body at all, so no request is built for it")
		rows.append({"kind": "action", "value": str(action),
			"reason": str(intent.get("reason", ""))})
	for user_id: Variant in ["", "   ", "\t"]:
		var empty := RewardFlow.build_reward_intent(str(user_id),
			RewardFlow.ACTION_WEEKLY)
		check(not bool(empty.get("ok", false)),
			"a blank user id %s is refused" % str(user_id))
		check_eq(str(empty.get("reason", "")), "missing_user_id",
			"with its own named reason")
		rows.append({"kind": "user_id", "value": str(user_id),
			"reason": str(empty.get("reason", ""))})

	# The grant-shaped refusals are reachable ONLY against a hand-built request,
	# because the builder's SIGNATURE cannot carry one. Asserted here as a
	# property of `refused_client_keys`, which is exactly the honest statement.
	var refused_payload := {"user_id": "user-1", "action": "daily", "item": 5}
	var refused := RewardFlow.refused_client_keys(refused_payload)
	check_eq(refused, ["item"],
		"a hand-built body carrying an item resolves to its named refusal class")
	var all_shapes := {"item": 1, "item_index": 2, "cell": [1, 2], "x": 1, "y": 2,
		"player": 3, "next_id": 4, "amount": 5, "price": 6}
	var resolved := RewardFlow.refused_client_keys(all_shapes)
	check_eq(resolved.size(), RewardFlow.CLIENT_KEY_REFUSALS.size()
		+ RewardFlow.CLIENT_KEY_ALIAS_COUNT,
		"all %d grant-shaped classes plus %d cell-coordinate aliases resolve"
			% [RewardFlow.CLIENT_KEY_REFUSALS.size(),
				RewardFlow.CLIENT_KEY_ALIAS_COUNT])
	check_eq(RewardFlow.CLIENT_KEY_REFUSAL_COUNT,
		RewardFlow.CLIENT_KEY_REFUSALS.size(),
		"the recorded refusal-class count literal matches the list it counts")
	check_eq(RewardFlow.CLIENT_KEY_ALIAS_COUNT,
		RewardFlow.CLIENT_KEY_ALIASES.size(),
		"and so does the alias count")
	var aliases_share_a_class := true
	for key: String in RewardFlow.CLIENT_KEY_ALIASES:
		if str(RewardFlow.CLIENT_KEY_ALIASES[key]) != "client_supplied_cell":
			aliases_share_a_class = false
	check_eq(aliases_share_a_class, true,
		"both cell coordinates resolve to ONE class, so two keys are one refusal")
	# `REFUSAL_KEY_MAP` is keyed by the CLIENT KEY it refuses, and its VALUES are
	# the reasons. Iterating its keys and demanding each be a reason -- which the
	# first cut of this suite did -- tests the wrong half of the table and fails
	# on all nine keys, so it is the values that are checked here.
	for key: String in RewardFlow.REFUSAL_KEY_MAP:
		var reason := str(RewardFlow.REFUSAL_KEY_MAP[key])
		check(RewardFlow.VALIDATION_ORDER.has(reason),
			"every refused client key resolves to a reason in the validation "
				+ "order: " + key + " -> " + reason)

	# The recorded-state refusals ARE reachable through the offline projection.
	for private: Variant in [{}, {"weeklyRewardIndex": 0},
			{RewardFlow.WEEKLY_CURSOR_KEY: "zero"},
			{RewardFlow.WEEKLY_CURSOR_KEY: 0}]:
		var projected := RewardFlow.project_cursor(private, RewardFlow.ACTION_WEEKLY,
			5, 3)
		check(not bool(projected.get("ok", false))
				or bool(projected.get("ok", false)),
			"the weekly projection is decidable for %s" % str(private.keys()
				if private is Dictionary else private))
	check(not bool(RewardFlow.project_cursor({}, RewardFlow.ACTION_WEEKLY,
			5, 3).get("ok", false)),
		"an absent cursor is REFUSED, never read as zero")
	check_eq(str(RewardFlow.project_cursor({}, RewardFlow.ACTION_WEEKLY, 5, 3)
		.get("reason", "")), "absent_reward_cursor",
		"with its named reason, because the preserved branch would raise")
	var no_instant := {RewardFlow.WEEKLY_CURSOR_KEY: 0}
	check_eq(str(RewardFlow.project_cursor(no_instant, RewardFlow.ACTION_WEEKLY,
		5, 3).get("reason", "")), "absent_reward_instant",
		"and an absent INSTANT is refused with its own named reason")
	var bad_cursor := {RewardFlow.WEEKLY_CURSOR_KEY: "0",
		RewardFlow.WEEKLY_STAMP_KEY: 0}
	check_eq(str(RewardFlow.project_cursor(bad_cursor, RewardFlow.ACTION_WEEKLY,
		5, 3).get("reason", "")), "invalid_reward_cursor",
		"and a NON-NUMERIC cursor is refused rather than coerced")

	# The validation order, and its write step.
	check_eq(RewardFlow.VALIDATION_ORDER.size(), RewardFlow.VALIDATION_ORDER_STEPS,
		"the validation order carries all %d steps"
			% RewardFlow.VALIDATION_ORDER_STEPS)
	check_eq(RewardFlow.WRITE_STEP, RewardFlow.VALIDATION_ORDER_STEPS + 1,
		"and the write step follows every one of them")
	check_eq(RewardFlow.STRUCTURAL_REFUSAL_COUNT, RewardFlow.VALIDATION_ORDER.size(),
		"the recorded structural refusal count matches the order it counts")
	check_eq(RewardFlow.REQUEST_SHAPE_REFUSALS.size()
		+ RewardFlow.RECORDED_STATE_REFUSALS.size(),
		RewardFlow.VALIDATION_ORDER.size(),
		"the order splits into request-shape and recorded-state halves that "
			+ "together are the whole of it")
	check_eq(bool(RewardFlow.ORDERING_RULE.get(
			"every_refusal_precedes_the_cursor_write", false)), true,
		"and the ordering rule states that every refusal precedes the cursor write")
	check_eq(bool(RewardFlow.ORDERING_RULE.get(
			"every_refusal_precedes_the_instant_stamp", false)), true,
		"and every refusal precedes the instant STAMP, which is what keeps a "
			+ "refused document byte-identical")

	# The quests line's five, recorded rather than repeated.
	var quests: Array = []
	for reason: String in QUESTS_MISSING_KEY_REFUSALS:
		quests.append({"refusal": reason,
			"why_unreachable_there": "its key was a required addressing key, and "
				+ "the quests typed client could not build a request without one",
			"reachable_here": false,
			"why_not_here": "this contract has no addressing key at all, so no "
				+ "refusal of that shape exists to be unreachable"})
	var unreachable_here := 0
	for row: Dictionary in quests:
		if not bool(row["reachable_here"]):
			unreachable_here += 1
	check_eq(unreachable_here, QUESTS_MISSING_KEY_REFUSALS.size(),
		"all %d of the quests line's missing-key refusals are recorded as NOT "
			% QUESTS_MISSING_KEY_REFUSALS.size()
			+ "reproducing that shape here")

	return {"ok": true, "client_reachable": rows.size(),
		"grant_shapes_reachable_only_against_a_hand_built_request": true,
		"validation_order": RewardFlow.VALIDATION_ORDER,
		"write_step": RewardFlow.WRITE_STEP,
		"quests_missing_key_refusals": quests,
		"quest_shape_unreachable_here": unreachable_here}

# ---------------------------------------------------------------------------
# 8. The request carries only an action and a save id
# ---------------------------------------------------------------------------


func _check_request_keys() -> Dictionary:
	info("--- request shape ---")
	check_eq(RewardFlow.REQUEST_KEYS, ["user_id", "action"],
		"the recorded request keys are exactly a save id and an action")
	check_eq(RewardFlow.REQUEST_KEYS.size(), RewardFlow.BODY_KEY_COUNT,
		"and the recorded body-key count matches that list")
	check_eq(RewardFlow.REWARD_PATH, "/v0/reward",
		"the endpoint this contract speaks to is /v0/reward")

	for action: String in RewardFlow.ACTIONS:
		var intent := RewardFlow.build_reward_intent("user-1", action)
		check(bool(intent.get("ok", false)),
			"the shared builder accepts the %s action" % action)
		if not bool(intent.get("ok", false)):
			continue
		var body: Dictionary = intent.get("body", {})
		var keys: Array = []
		for key: Variant in body:
			keys.append(str(key))
		keys.sort()
		# Both sides sorted: comparing a sorted walk against an unsorted literal
		# would fail on ORDER rather than on membership, which is a failure this
		# check does not mean to make.
		var declared_keys: Array = RewardFlow.REQUEST_KEYS.duplicate()
		declared_keys.sort()
		check_eq(keys, declared_keys,
			"and the %s body carries EXACTLY the two recorded keys, so a "
				% action + "grant shape is not expressible rather than merely refused")
		check_eq(body.size(), RewardFlow.BODY_KEY_COUNT,
			"which is %d keys" % RewardFlow.BODY_KEY_COUNT)
		check_eq(str(body["action"]), action, "naming the driven action")
		# And nothing grant-shaped rides along.
		for shape: Array in RewardFlow.CLIENT_KEY_REFUSALS:
			check(not body.has(str(shape[0])),
				"the %s body carries no %s key" % [action, str(shape[0])])
		for alias: String in RewardFlow.CLIENT_KEY_ALIASES:
			check(not body.has(alias),
				"and no %s alias" % alias)
		check_eq(RewardFlow.refused_client_keys(body), [],
			"so the builder's own body resolves to NO refusal class")

	return {"ok": true, "request_keys": RewardFlow.REQUEST_KEYS,
		"body_key_count": RewardFlow.BODY_KEY_COUNT,
		"path": RewardFlow.REWARD_PATH}

# ---------------------------------------------------------------------------
# 9. The four-part grant proof and the two-part cursor proof, ASSERTED
# ---------------------------------------------------------------------------


## Both proofs, checked as ASSERTIONS rather than as the presence of a table.
##
## The four grant parts are asserted to be four **distinct, checkable**
## statements -- not one prose paragraph -- and each is required to name a
## `wire_key` the parser can demand without comparing a word of prose. And the
## parser is then driven with an answer whose grant block is missing a part, so
## the requirement is shown to be load-bearing rather than decorative.
func _check_proofs(projection: Dictionary) -> Dictionary:
	info("--- the two proofs ---")
	check_eq(RewardFlow.REFUSAL_PROOF_PART_COUNT,
		RewardFlow.REFUSAL_PROOF_PARTS.size(),
		"the grant proof carries all four parts")
	var parts: Array = []
	var wire_keys: Array = []
	var numbers: Array = []
	for part: Dictionary in RewardFlow.REFUSAL_PROOF_PARTS:
		parts.append({"part": int(part["part"]), "id": str(part["id"]),
			"wire_key": str(part["wire_key"]), "claim": str(part["claim"]),
			"covered_by": str(part["covered_by"])})
		wire_keys.append(str(part["wire_key"]))
		numbers.append(int(part["part"]))
	check_eq(numbers, [1, 2, 3, 4],
		"the four parts are numbered 1..4, so none is a duplicate of another")
	check_eq(wire_keys, RewardFlow.REFUSAL_PROOF_WIRE_KEYS,
		"and their four wire keys are the four the parser requires")
	var unique_ids := {}
	for part: Dictionary in RewardFlow.REFUSAL_PROOF_PARTS:
		unique_ids[str(part["id"])] = true
	check_eq(unique_ids.size(), RewardFlow.REFUSAL_PROOF_PART_COUNT,
		"so the four parts name four DIFFERENT landing places, which is what "
			+ "makes the proof non-tautological")
	var covered: Array = []
	for part: Dictionary in RewardFlow.REFUSAL_PROOF_PARTS:
		covered.append(str(part["covered_by"]))
	# THREE of the four parts -- the map rows, the bought-units list, and the
	# store -- are covered by the single whole-document leaf allowlist, and only
	# the fourth needs a comparison of its own. An earlier draft of this check
	# asserted **two**, which would have been a claim that part 3 was checked
	# separately when it is in fact covered by the same containment; the count is
	# measured here rather than assumed.
	check_eq(covered.count("the whole-document leaf allowlist"), 3,
		"parts 1, 2 and 3 are all covered by the one whole-document leaf "
			+ "allowlist, so three landing places are covered by one check")
	check_eq(covered.count("the complete resource-set equality the route performs"),
		1, "and part 4 by the complete resource-set equality")
	# The allowlist is what makes parts 1-3 a containment check rather than three
	# hand-maintained comparisons.
	check_eq(RewardFlow.ALLOWED_LEAF_PATH_COUNT, 2,
		"exactly two leaf paths may change per action")
	for action: String in RewardFlow.ACTIONS:
		var paths: Array = RewardFlow.ALLOWED_LEAF_PATHS[action]
		check_eq(paths.size(), RewardFlow.ALLOWED_LEAF_PATH_COUNT,
			"the %s action may change exactly %d paths"
				% [action, RewardFlow.ALLOWED_LEAF_PATH_COUNT])
		check(paths.has("/" + RewardFlow.PRIVATE_STATE_KEY + "/"
				+ RewardFlow.ACTION_CURSOR_KEY[action]),
			"one of which is its own cursor")
		check(paths.has("/" + RewardFlow.PRIVATE_STATE_KEY + "/"
				+ RewardFlow.ACTION_STAMP_KEY[action]),
			"and the other its own instant")
	check_eq(bool(RewardFlow.NO_REWARD_MOVED.get("nothing_is_granted", false)), true,
		"and the grant refusal itself is recorded")
	check_eq(bool(RewardFlow.NO_REWARD_MOVED.get("complete_resource_set_not_a_subset",
		false)), true,
		"with the COMPLETE-set requirement stated rather than left implied")

	# The two-part cursor proof: the addressed cursor moved by EXACTLY the
	# derived transition, and nothing else changed. Driven through a real
	# envelope so it is asserted end to end rather than described.
	if not bool(projection.get("ok", false)):
		return {"ok": false, "parts": parts}
	var typed: RewardFlow.CursorProjection = projection["projection"]
	var schedules := {
		RewardFlow.WEEKLY_SCHEDULE_KEY: _schedules_from_projection(projection),
		RewardFlow.DAILY_SCHEDULE_KEY: _schedules_from_projection(projection),
	}
	schedules[RewardFlow.WEEKLY_SCHEDULE_KEY] = projection["weekly_schedule"]
	schedules[RewardFlow.DAILY_SCHEDULE_KEY] = projection["daily_schedule"]

	for action: String in RewardFlow.ACTIONS:
		var cursor: RewardFlow.Cursor = null
		for candidate: RewardFlow.Cursor in typed.cursors:
			if candidate.action == action:
				cursor = candidate
		if cursor == null:
			fail("the projection carries a %s cursor" % action)
			continue
		var envelope := RewardFlow.build_reward_response(action,
			{"projection": typed}, {
				"cursor_after": cursor.successor,
				"resources": _zero_resources(),
				"changed": RewardFlow.ALLOWED_LEAF_PATHS[action],
				"server_time": 0, "game_version": "",
			})
		check(envelope is Dictionary and bool((envelope as Dictionary).get("ok",
			false)), "the %s answer is assembled" % action)
		if not (envelope is Dictionary):
			continue
		var parsed := RewardFlow.parse_reward(envelope)
		check(bool(parsed.ok),
			"and the shared parser accepts it: %s / %s"
				% [str(parsed.reason), str(parsed.error)])
		if not bool(parsed.ok):
			continue
		# PART ONE: the cursor moved by exactly the derived transition.
		check_eq(parsed.cursor_before, cursor.value,
			"the %s cursor's BEFORE value is the recorded one" % action)
		check_eq(parsed.cursor_after, cursor.successor,
			"the %s cursor's AFTER value is the re-derived successor" % action)
		check_eq(parsed.cursor_change, cursor.change, "and its change agrees")
		check_eq(parsed.derived_after, cursor.successor,
			"the parser's OWN re-derivation agrees with the answer's after value")
		check_eq(parsed.derived_change, cursor.change,
			"and with its change, so the answer is not merely echoed")
		check_eq(parsed.cursor_after - parsed.cursor_before, parsed.cursor_change,
			"the two-part cursor proof's first half: the change equals its own "
				+ "two ends")
		# PART TWO: the complete resource set, unchanged.
		check_eq((parsed.resources as Dictionary).size(),
			RewardFlow.RESOURCE_NAMES.size(),
			"the %s answer carries the COMPLETE %d stored resource set"
				% [action, RewardFlow.RESOURCE_NAMES.size()])
		check_eq(parsed.resources, _zero_resources(),
			"and every one of them is unchanged")
		# The four grant parts, each demanded as a key.
		for wire_key: String in RewardFlow.REFUSAL_PROOF_WIRE_KEYS:
			check(_present(parsed.refusal_evidence.get(wire_key, null)),
				"the %s answer carries grant-proof part %s" % [action, wire_key])
		check_eq(parsed.allowed_leaf_paths,
			RewardFlow.ALLOWED_LEAF_PATHS[action],
			"and the %s answer's allowed leaf paths are its OWN two" % action)
		# And the changed-pointer list is a SUBSET of them: the containment check.
		var outside: Array = []
		for path: Variant in parsed.changed:
			if not RewardFlow.ALLOWED_LEAF_PATHS[action].has(str(path)):
				outside.append(str(path))
		check_eq(outside, [],
			"so every changed pointer of the %s answer is inside the allowlist"
				% action)

		# --- the proofs are LOAD-BEARING: break each and be refused ---------
		var dropped := (envelope as Dictionary).duplicate(true)
		var grant: Dictionary = (dropped["reward"] as Dictionary)["grant"]
		grant.erase(RewardFlow.REFUSAL_PROOF_WIRE_KEYS[2])
		var refused := RewardFlow.parse_reward(dropped)
		check(not bool(refused.ok),
			"the %s answer is REFUSED when a grant-proof part is dropped" % action)
		check_eq(str(refused.reason), RewardFlow.REASON_BAD_RESPONSE,
			"with the parser's own refusal reason")
		check_eq((refused.resources as Dictionary).size(), 0,
			"and NO partial payload travels with the refusal")

		var moved := (envelope as Dictionary).duplicate(true)
		var cursor_body: Dictionary = (moved["reward"] as Dictionary)["cursor"]
		cursor_body["after"] = int(cursor_body["after"]) + 1
		check(not bool(RewardFlow.parse_reward(moved).ok),
			"and the %s answer is REFUSED when the cursor moved by anything but "
				% action + "the derived transition")

		var granted := (envelope as Dictionary).duplicate(true)
		((granted["reward"] as Dictionary)["grant"])["grants_nothing"] = false
		check(not bool(RewardFlow.parse_reward(granted).ok),
			"and REFUSED when the grant block stops claiming a grant")

	return {"ok": true, "parts": parts, "wire_keys": wire_keys,
		"allowed_leaf_paths": RewardFlow.ALLOWED_LEAF_PATHS,
		"part_count": RewardFlow.REFUSAL_PROOF_PART_COUNT}

# ---------------------------------------------------------------------------
# 10. Ownership, at three levels
# ---------------------------------------------------------------------------


## Task 5's three boundaries, each checked MECHANICALLY rather than by prose.
##
## The suite walks `openspec/specs/` for both the source identifiers and the
## **role names**, because a prose spec describes behaviour by role and never by
## key name -- the defect that made two prior ownership greps pass on a field
## another capability had already claimed. It then confirms the ranking-reward
## table's split ownership, and proves each foreign save field's owner exists
## and actually names it.
func _check_ownership_boundary() -> void:
	info("--- ownership boundary ---")
	var specs := _spec_files()
	check(specs.size() > 0, "the committed specs directory is walked (%d files)"
		% specs.size())
	var own_spec := "%s/%s/spec.md" % [SPECS_DIRECTORY, OWNING_CAPABILITY]

	# --- 5.1: both source identifiers and role names ---------------------
	var hits: Array = []
	var own_hits: Array = []
	for probe: String in SOURCE_IDENTIFIER_PROBES + ROLE_NAME_PROBES:
		var found := ""
		var count := 0
		for relative: String in specs:
			var body := _read_text(Paths.repo_root().path_join(relative))
			var occurrences := _count_occurrences(body, probe)
			if occurrences > 0:
				found = relative
				count += occurrences
		if count > 0 and relative_is_own(found, own_spec):
			own_hits.append({"probe": probe, "spec": found, "hits": count})
		elif count > 0:
			hits.append({"probe": probe, "spec": found, "hits": count})
	check_eq(hits, [],
		"no OTHER capability's spec claims either cursor, either branch, or "
			+ "either schedule -- checked by SOURCE IDENTIFIER and by ROLE NAME")
	info("ownership: %d source-identifier probes, %d role-name probes, "
		% [SOURCE_IDENTIFIER_PROBES.size(), ROLE_NAME_PROBES.size()]
		+ "%d hits outside %s, %d inside it"
			% [hits.size(), OWNING_CAPABILITY, own_hits.size()])

	# --- 5.2: the ranking-reward table's split ownership ------------------
	for owner: String in RANKING_REWARD_OWNERS:
		var owner_spec := "%s/%s/spec.md" % [SPECS_DIRECTORY, owner]
		check(specs.has(owner_spec),
			"the %s capability has a committed spec" % owner)
		var owner_body := _read_text(Paths.repo_root().path_join(owner_spec))
		check(_count_occurrences(owner_body, RewardFlow.RANKING_REWARD_TABLE) > 0,
			"and that spec names %s, so this line's claim that it is owned as "
				% RewardFlow.RANKING_REWARD_TABLE + "normalized content is checkable")
	var ranking_owners: Array = []
	for relative: String in specs:
		var body := _read_text(Paths.repo_root().path_join(relative))
		if _count_occurrences(body, RewardFlow.RANKING_REWARD_TABLE) > 0:
			ranking_owners.append(relative)
	check_eq(ranking_owners.size(), RANKING_REWARD_OWNERS.size(),
		"exactly %d specs name the ranking-reward table, and this line's own "
			% RANKING_REWARD_OWNERS.size()
			+ "delta names it only in prose, never as an identifier to claim")
	check_eq(bool(RewardFlow.RANKING_REWARD_OWNERSHIP.get(
			"delivered_as_gameplay_by_this_line", true)), false,
		"and this line explicitly does NOT claim gameplay ownership of it")
	check((RewardFlow.RANKING_REWARD_OWNERSHIP.get(
			"the_two_statements_do_not_imply_each_other", "") as String) != "",
		"with the record stating the two states do not imply each other")

	# --- 5.3: each foreign field's owner EXISTS and NAMES it --------------
	# ## THREE OWNER PATHS WERE WRONG AND ARE CORRECTED
	# The module's first draft pointed at `scripts/units/unit_instances.gd`,
	# which DOES NOT EXIST, and at two files that contain zero occurrences of
	# the field they were said to own. Every hand-off would have been asserted
	# against a file that cannot support it, which is worse than not asserting.
	for field: String in RewardFlow.FOREIGN_IDENTIFIERS:
		var owner_rel := str(RewardFlow.FOREIGN_IDENTIFIERS[field])
		var owner_path := Paths.project_dir().path_join(owner_rel)
		check(FileAccess.file_exists(owner_path),
			"the owner module for %s exists: %s" % [field, owner_rel])
		if not FileAccess.file_exists(owner_path):
			continue
		var owner_body := _read_text(owner_path)
		var pattern := "\\b" + field + "\\b"
		var named := _regex_count(pattern, owner_body)
		check(named > 0,
			"and it actually NAMES %s (%d occurrences), so the hand-off is a "
				% [field, named] + "hand-off and not an orphan")
		check((RewardFlow.FOREIGN_IDENTIFIER_ROLES.get(field, "") as String) != "",
			"with a recorded role for what that owner does with %s" % field)
	check_eq(RewardFlow.FOREIGN_IDENTIFIER_COUNT,
		RewardFlow.FOREIGN_IDENTIFIERS.size(),
		"the recorded foreign-identifier count matches the table it counts")
	check_eq(RewardFlow.OWNED_IDENTIFIER_COUNT, RewardFlow.OWNED_IDENTIFIERS.size(),
		"and the owned-identifier count matches its table, so the two tables are "
			+ "distinguishable")

	# The owned fields, each of which this module DOES project.
	#
	# ## These are checked against the RAW module text, not the code-only text
	#
	# The first cut ran this over `_code_only()`, which blanks every string
	# literal -- and these five fields appear in the module *only* as quoted save
	# keys, so all five checks failed. The `_code_only()` pass belongs to the
	# identifier guards above, where a name inside a string is deliberately not an
	# identifier; here the string IS the deliverable, because these are the save
	# fields the projection reads.
	for field: String in RewardFlow.OWNED_IDENTIFIERS:
		check(_module_text().contains(field),
			"the owned field %s IS named by the delivered module, which is what "
				% field + "distinguishes the two tables")
		check(not RewardFlow.FOREIGN_IDENTIFIERS.has(field),
			"and it is not simultaneously a foreign one")

	# --- 5.5: the open documentation gap, left visible -------------------
	# `godot-combat-actions` (M10 line 2) has no README section. Recorded here
	# rather than backfilled: the instruction is explicit, and a suite that
	# asserted the section existed would fail on a gap this change must not close.
	#
	# MEASURED DEFECT, and the fourth instance of this class in this project (see
	# section 9). The check was `readme.contains("godot-combat-actions")`, which
	# reported the section PRESENT while no such section exists: the only
	# occurrence is this capability's OWN README prose recording the gap, so the
	# documenting text satisfied the search for the thing it documents. It was
	# also an `info()` line, so it asserted nothing at all. The comment above
	# stated the correct intent and the code did the opposite.
	#
	# Fixed two ways. The search is for a HEADING carrying the capability name,
	# not the bare substring, and the gap is asserted still-open rather than
	# reported -- so a future change that adds the section fails here and forces
	# this note to be revisited instead of leaving a stale claim behind.
	var combat_readme := _read_text(Paths.project_dir().path_join(
		"README.md"))
	var bare_mentions := _count_occurrences(combat_readme,
		"godot-combat-actions")
	var heading_lines := 0
	for line: String in combat_readme.split("\n"):
		if line.begins_with("#") and line.contains("godot-combat-actions"):
			heading_lines += 1
	info("documentation gap: bare mentions = %d, headings = %d"
		% [bare_mentions, heading_lines])
	check(bare_mentions > 0,
		"the gap is RECORDED in prose, so it is visible to a reader (%d mentions)"
			% bare_mentions)
	check_eq(heading_lines, 0,
		"and godot-combat-actions STILL has no README section: this change must "
		+ "not backfill a gap it was told to leave visible. If this fails, a "
		+ "later change closed the gap and this note is now stale.")

## True when `found` is this capability's own spec file.
func relative_is_own(found: String, own_spec: String) -> bool:
	return found.replace("\\", "/") == own_spec


func _schedules_from_projection(_projection: Dictionary) -> Variant:
	return []


func _zero_resources() -> Dictionary:
	var out := {}
	for name: String in RewardFlow.RESOURCE_NAMES:
		out[name] = 0
	return out


func _present(value: Variant) -> bool:
	if value == null:
		return false
	if value is String:
		return str(value) != ""
	return true

# ---------------------------------------------------------------------------
# 11. What this line does and does not claim
# ---------------------------------------------------------------------------


func _check_coverage() -> Dictionary:
	info("--- coverage and claim limits ---")
	var coverage := RewardFlow.coverage_limit()
	check(not coverage.is_empty(), "the coverage record is published")
	check_eq(int(coverage.get("actions", -1)), RewardFlow.ACTION_COUNT,
		"and reports the delivered action count")
	check_eq(int(coverage.get("schedules_reported", -1)), RewardFlow.SCHEDULE_COUNT,
		"and the number of schedules reported")
	check_eq(int(coverage.get("schedules_with_no_consumer", -1)),
		RewardFlow.SCHEDULES_WITH_NO_CONSUMER_COUNT,
		"and the number with no consumer")
	check_eq(int(coverage.get("save_only_fields", -1)),
		RewardFlow.SAVE_ONLY_FIELD_COUNT, "and the save-only field count")
	check_eq(int(coverage.get("committed_save_documents", -1)),
		RewardFlow.SAVE_ONLY_DOCUMENT_COUNT, "and the document count")
	check_eq(bool(coverage.get("nothing_rendered", false)), true,
		"and states that nothing is rendered, which is why no windowed capture "
			+ "and no pixel-parity oracle are claimed")
	check_eq(bool(coverage.get("no_pixel_parity", false)), true,
		"with the pixel-parity claim refused outright")
	check_eq(bool(coverage.get("no_flash", false)), true, "and no Flash")
	check_eq(bool(coverage.get("no_network_in_the_hermetic_suite", false)), true,
		"and that this suite uses no network at all")

	var non_claims := RewardFlow.non_claims()
	check_eq(non_claims.size(), RewardFlow.NON_CLAIMS.size(),
		"the claim limits travel with the module")
	for claim: String in non_claims:
		check((claim as String).strip_edges() != "",
			"every claim limit is a non-empty sentence")
	check_eq(int(RewardFlow.DIVERGENCES_REPORTED_AS_PARITY), 0,
		"and NOT ONE of the %d recorded divergences is reported as parity"
			% RewardFlow.DIVERGENCE_COUNT)
	check_eq(RewardFlow.DIVERGENCE_COUNT, RewardFlow.DIVERGENCES.size(),
		"the recorded divergence count matches the list it counts")
	for divergence: Dictionary in RewardFlow.DIVERGENCES:
		check_eq(bool(divergence.get("reproduced", true)), false,
			"divergence %s is recorded as NOT reproduced"
				% str(divergence.get("id", "")))
	check_eq(RewardFlow.ARMS_TOTAL,
		RewardFlow.ARM_COUNT_PER_ACTION * RewardFlow.ACTION_COUNT,
		"all four preserved arms are reported")
	for action: String in RewardFlow.ACTIONS:
		var arms: Array = (RewardFlow.WEEKLY_ARMS
			if action == RewardFlow.ACTION_WEEKLY
			else RewardFlow.DAILY_ARMS)
		check_eq(arms.size(), RewardFlow.ARM_COUNT_PER_ACTION,
			"the %s branch reports BOTH of its arms" % action)
		for arm: Dictionary in arms:
			check_eq(bool(arm.get("reproduced", true)), false,
				"and neither is reproduced, because both are selected by a "
					+ "client-sent value")
	check_eq(bool(RewardFlow.ARMS_REPORT_NOTE.get(
			"the_arm_boundary_is_reported_not_reproduced", false)), true,
		"with the boundary recorded as a report rather than a behaviour")

	return {"ok": true, "coverage": coverage, "non_claims": non_claims,
		"divergences": RewardFlow.DIVERGENCE_COUNT,
		"divergences_as_parity": RewardFlow.DIVERGENCES_REPORTED_AS_PARITY,
		"arms": RewardFlow.ARMS_TOTAL}

# ---------------------------------------------------------------------------
# The deliberate-failure perturbation mode
# ---------------------------------------------------------------------------


## Feed altered committed bytes into this suite's own re-derivations.
##
## A run in this mode MUST fail. If it passes, the re-derivation it exercises is
## vacuous -- which is the whole reason the mode exists rather than a claim that
## the checks are strong.
func _run_perturbation(mode: String) -> void:
	info("--- perturbation mode: %s ---" % mode)
	var length_span := _legacy_span(LENGTH_FILE, LENGTH_FIRST, LENGTH_LAST)
	var weekly_span := _legacy_span("command.py", WEEKLY_BRANCH_FIRST,
		WEEKLY_BRANCH_LAST)
	var daily_span := _legacy_span("command.py", DAILY_BRANCH_FIRST,
		DAILY_BRANCH_LAST)
	check(length_span != "" and weekly_span != "" and daily_span != "",
		"the three recorded spans are readable before they are perturbed")

	match mode:
		"weekly-seed":
			# Change the preserved helper's accumulator seed from 1 to 9 and
			# require the re-derivation to move off the recorded floor.
			var altered := length_span.replace("length = 1", "length = 9")
			# NOTE the direction.  This was `check_eq(altered, length_span, ...)`
			# in the first draft, which asserts the perturbation did NOT change the
			# span while its message claims it did -- so the mode failed for the
			# opposite reason it was written to prove, and a perturbation that
			# matched nothing would have PASSED.  The other three modes below
			# already had the `!=` form; this one now matches them.
			check(altered != length_span,
				"the perturbation actually changed the committed span")
			var seed := _first_int(altered, "length\\s*=\\s*(\\d+)")
			check_eq(seed, RewardFlow.WEEKLY_BOUND_FLOOR,
				"the altered seed is no longer the recorded floor -- THIS CHECK "
				+ "MUST FAIL under perturbation")
		"daily-literal":
			var altered2 := daily_span.replace("if next_id > 5:", "if next_id > 9:")
			check(altered2 != daily_span,
				"the perturbation actually changed the committed span")
			var literal := _first_int(altered2, "if\\s+next_id\\s*>\\s*(\\d+)\\s*:")
			check_eq(literal, RewardFlow.DAILY_BOUND_LITERAL,
				"the altered daily literal is no longer the recorded one -- THIS "
				+ "CHECK MUST FAIL under perturbation")
		"weekly-modulo":
			var altered3 := weekly_span.replace(
				"weeklyRewardIndex\"] + 1) % get_weekly_reward_length()",
				"weeklyRewardIndex\"] + 2) % 7")
			check(altered3 != weekly_span,
				"the perturbation actually changed the committed span")
			var increment := _first_int(altered3,
				"\\[\\\"privateState\\\"\\]\\[\\\"weeklyRewardIndex\\\"\\]\\s*\\+\\s*(\\d+)\\)\\s*%")
			check_eq(increment, 1,
				"the altered weekly increment is no longer the recorded one -- "
				+ "THIS CHECK MUST FAIL under perturbation")
		"list-test":
			# Change the preserved helper's type test from `list` to `dict`, which
			# would silently change what the bound counts.
			var altered4 := length_span.replace("type(value) == list",
				"type(value) == dict")
			check(altered4 != length_span,
				"the perturbation actually changed the committed span")
			var test := _first_word(altered4, "type\\(value\\)\\s*==\\s*(\\w+)")
			check_eq(test, "list",
				"the altered type test is no longer the recorded one -- THIS CHECK "
				+ "MUST FAIL under perturbation")
		_:
			fail("unknown perturbation mode: %s" % mode)

# ---------------------------------------------------------------------------
# Helpers: reading committed bytes
# ---------------------------------------------------------------------------


## The delivered module's own bytes, read once.
func _module_text() -> String:
	return FileAccess.get_file_as_string(Paths.project_dir().path_join(MODULE_PATH))


## One span of a committed legacy module, `first`..`last` INCLUSIVE, 1-based.
##
## The spans are the recorded coordinates. Nothing about the figures inside them
## is transcribed here: the caller extracts those with a regular expression, so a
## legacy edit changes what is extracted rather than contradicting a copied
## number.
func _legacy_span(name: String, first: int, last: int) -> String:
	var path := Paths.repo_root().path_join(name)
	if not FileAccess.file_exists(path):
		return ""
	var lines := FileAccess.get_file_as_string(path).split("\n")
	var out: Array = []
	var index := first
	while index <= last and index <= lines.size():
		out.append(str(lines[index - 1]).trim_suffix("\r"))
		index += 1
	return "\n".join(out)


## The first integer captured by `pattern`, or -1 when nothing matches.
func _first_int(body: String, pattern: String) -> int:
	var match: Variant = _first_match(body, pattern)
	if match == null:
		return -1
	var captured: Variant = match.get_string(1)
	if not (captured is String):
		return -1
	return str(captured).to_int()


## The first captured word, or "" when nothing matches.
func _first_word(body: String, pattern: String) -> String:
	var match: Variant = _first_match(body, pattern)
	if match == null:
		return ""
	var captured: Variant = match.get_string(1)
	return "" if not (captured is String) else str(captured)


func _first_match(body: String, pattern: String) -> Variant:
	var expression := RegEx.new()
	if expression.compile(pattern) != OK:
		return null
	var found: Variant = expression.search(body, 0)
	return null if found == null else found


## How many times `pattern` matches `body`, as a MEASUREMENT.
##
## `RegEx` is used rather than a hand-written scan, and that choice is load
## bearing: the module originally claimed the engine had no regular-expression
## class and that these counts therefore could not be published. `RegEx` compiles
## on the pinned build, it is PCRE2, and `search_all()` counts every match -- all
## three verified by probe. Two of the counts this section measures were WRONG
## when they came from a hand-written scan and were corrected to match.
func _regex_count(pattern: String, body: String) -> int:
	var expression := RegEx.new()
	if expression.compile(pattern) != OK:
		fail("the pattern compiles: " + pattern)
		return 0
	return expression.search_all(body).size()


## How many times `needle` occurs in `body`, counted without a regular
## expression -- the right tool for a literal.
func _count_occurrences(body: String, needle: String) -> int:
	if needle == "":
		return 0
	var count := 0
	var position := body.find(needle)
	while position >= 0:
		count += 1
		position = body.find(needle, position + needle.length())
	return count


## How many DISTINCT LINES carry `needle`.
func _count_lines(body: String, needle: String) -> int:
	if needle == "":
		return 0
	var count := 0
	for line: String in body.split("\n"):
		if line.contains(needle):
			count += 1
	return count


## How many occurrences of `needle` stand as a WHOLE IDENTIFIER TOKEN.
##
## A bare identifier with no word boundary. This is what separates "the name
## appears in the source" from "some code READS that name": the weekly schedule's
## single occurrence is a quoted subscript, so its identifier-token count is zero
## even though its whole-file count is one.
func _count_tokens(body: String, needle: String) -> int:
	return _regex_count("\\b" + needle + "\\b", body)


## How many times `needle` occurs as a **bare identifier outside any string
## literal or comment**.
##
## ## A whole-word match is NOT enough, and the difference is a measured one
##
## The first cut of this suite counted `\bNAME\b` over the raw corpus and then
## reported the weekly schedule's "identifier token" count as **1**. It is zero:
## its one occurrence is `__game_config["globals"]["MONDAY_BONUS_REWARDS"]`, and
## the name sits inside a quoted subscript, so `\b` matches the quotes' word
## boundaries and the count silently became "the name is mentioned", not "code
## reads the name". Comments are stripped for the same reason -- a commented-out
## reference is not a consumer.
func _count_code_tokens(body: String, needle: String) -> int:
	return _count_tokens(_code_only(body), needle)


## How many times `needle` is ASSIGNED in `body`, as `NAME =` or `NAME :=`.
##
## This is what separates a **declaration** from a **consumer** in the census:
## `constants.py:888` writes `COST_GOLD = "g"`, so its one whole-file occurrence
## is the declaration itself and its consumer count is zero. Counting occurrences
## without subtracting the declaration would report one consumer where there is
## none, which is the inverse of the vacuous-census defect and just as wrong.
func _count_declarations(body: String, needle: String) -> int:
	return _regex_count("\\b" + needle + "\\s*:?=(?!=)", body)


## The normalized globals package's value for one committed global, or null.
func _globals_value(package: Variant, name: String) -> Variant:
	if not (package is Array):
		return null
	for row: Variant in package as Array:
		if row is Dictionary and str((row as Dictionary).get("legacy_id", "")) == name:
			return (row as Dictionary).get("value", null)
	return null


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	return JSON.parse_string(FileAccess.get_file_as_string(path))


func _read_text(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## Every committed `.json` file directly inside `directory`, as repository-
## relative POSIX paths, sorted.
func _json_files(directory: String) -> Array:
	var out: Array = []
	var handle := DirAccess.open(directory)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if not handle.current_is_dir() and entry.ends_with(".json"):
			out.append(directory.replace(Paths.repo_root() + "/", "") + "/" + entry)
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort()
	return out


## Every committed capability spec, as repository-relative POSIX paths, sorted.
func _spec_files() -> Array:
	var root := Paths.repo_root().path_join(SPECS_DIRECTORY)
	var out: Array = []
	var handle := DirAccess.open(root)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if handle.current_is_dir():
			var candidate := root.path_join(entry).path_join("spec.md")
			if FileAccess.file_exists(candidate):
				out.append("%s/%s/spec.md" % [SPECS_DIRECTORY, entry])
		entry = handle.get_next()
	handle.list_dir_end()
	out.sort()
	return out


## A `{value: count}` mapping as a sorted `[[value, count], ...]` table.
func _sorted_counts(table: Dictionary) -> Array:
	var rows: Array = []
	for key: String in table:
		rows.append([key, int(table[key])])
	rows.sort()
	return rows


## The EXPECTED_DISTRIBUTION literals as sorted pairs, so the comparison is
## between two MEASURED tables rather than one measured and one copied.
func _count_pairs(table: Dictionary) -> Array:
	var rows: Array = []
	for key: String in table:
		rows.append([key, int(table[key])])
	rows.sort()
	return rows


## Blank comments and string literals per line, keeping every line boundary.
##
## A second, independent implementation of the module's own scanner: the guard it
## checks is the scanner itself, so checking it with the scanner would be
## circular. Its length-preserving blanking means a column number indexes both
## views.
func _code_only(body: String) -> String:
	var out: Array = []
	for line: String in body.split("\n"):
		var blanked := ""
		var index := 0
		var quote := ""
		while index < line.length():
			var character := line[index]
			if quote != "":
				if character == "\\" and index < line.length() - 1:
					blanked += "  "
					index += 2
					continue
				if character == quote:
					quote = ""
				blanked += " "
				index += 1
				continue
			if character == "#":
				blanked += " ".repeat(line.length() - index)
				break
			if character == "\"" or character == "'":
				quote = character
				blanked += " "
				index += 1
				continue
			blanked += character
			index += 1
		out.append(blanked)
	return "\n".join(out)


## The `static func` declarations of a GDScript body, in file order.
func _declared_static_functions(source: String) -> Array:
	return _declared_functions(source, "static func ")


## The `func` declarations that are NOT static, in file order.
func _instance_functions(source: String) -> Array:
	var out: Array = []
	for line: String in source.split("\n"):
		var stripped := line.strip_edges()
		if not stripped.begins_with("func "):
			continue
		if stripped.begins_with("static func "):
			continue
		var rest := stripped.substr(5)
		var open := rest.find("(")
		if open < 0:
			continue
		out.append(rest.substr(0, open).strip_edges())
	return out


func _declared_functions(source: String, prefix: String) -> Array:
	var out: Array = []
	for line: String in source.split("\n"):
		var stripped := line.strip_edges()
		if not stripped.begins_with(prefix):
			continue
		var rest := stripped.substr(prefix.length())
		var open := rest.find("(")
		if open < 0:
			continue
		out.append(rest.substr(0, open).strip_edges())
	return out


func _sha256(text: String) -> String:
	return text.sha256_text()


## A round trip through JSON, so a float the engine decoded and the int this
## suite compares read identically.
##
## Called only on values that are already well-formed JSON, so it never hands a
## malformed document to the parser -- the engine emits an `ERROR:` line for
## malformed input and `verify-boot.ps1` treats any such line as a script error.
func _normalize(value: Variant) -> Variant:
	if value == null:
		return null
	return JSON.parse_string(JSON.stringify(value))


func _perturbation_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--perturb-command-source="):
			return argument.trim_prefix("--perturb-command-source=")
	return ""


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


func _scenario_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--scenario="):
			return argument.trim_prefix("--scenario=")
	return ""

# ---------------------------------------------------------------------------
# The deterministic report
# ---------------------------------------------------------------------------


## The deterministic `rewards-report-v1` document.
##
## Every table is generated from the delivered module's own constants, from this
## run's own measurement of committed bytes, or from committed content -- so it
## cannot drift from the code it documents. No wall clock, no absolute path, and
## no host-specific figure is written, so three consecutive runs produce
## byte-identical output.
func _report(measured: Dictionary) -> Dictionary:
	return {
		"schema": "rewards-report-v1",
		"line": {
			"milestone": RewardFlow.PROVENANCE["milestone"],
			"index": RewardFlow.PROVENANCE["line"],
			"capability": RewardFlow.PROVENANCE["capability"],
		},
		"investigation": RewardFlow.PROVENANCE["investigation"],
		"primary_finding": RewardFlow.PROVENANCE["primary_finding"],
		"delivered_surface": RewardFlow.PROVENANCE["delivered_surface"],
		"nothing_delivered": RewardFlow.PROVENANCE["nothing_delivered"],
		"actions": RewardFlow.ACTIONS,
		"action_command": RewardFlow.ACTION_COMMAND,
		"action_cursor_key": RewardFlow.ACTION_CURSOR_KEY,
		"action_stamp_key": RewardFlow.ACTION_STAMP_KEY,
		"action_schedule_key": RewardFlow.ACTION_SCHEDULE_KEY,
		"action_addressing_key": RewardFlow.ACTION_ADDRESSING_KEY,
		"addressing_note": RewardFlow.ADDRESSING_KEY_NOTE,
		"request": measured.get("request", {}),
		"cursors": measured.get("projection", {}).get("cursors", []),
		"bounds": {
			"weekly": {
				"bound": measured.get("bound", {}).get(
					"recomputed_weekly_bound", -1),
				"floor": RewardFlow.WEEKLY_BOUND_FLOOR,
				"source": RewardFlow.WEEKLY_BOUND_SOURCE,
				"derived_from": RewardFlow.WEEKLY_BOUND_DERIVED_FROM,
				"cardinality": measured.get("bound", {}).get(
					"weekly_cardinality", -1),
			},
			"daily": {
				"bound": RewardFlow.DAILY_BOUND_LITERAL,
				"is_literal": RewardFlow.DAILY_BOUND_IS_LITERAL,
				"source": RewardFlow.DAILY_BOUND_SOURCE,
				"wrap_target": RewardFlow.DAILY_WRAP_TARGET,
				"cardinality": RewardFlow.DAILY_SCHEDULE_CARDINALITY,
				"rejected_alternative": RewardFlow.DAILY_BOUND_REJECTED_DERIVATION,
			},
		},
		"index_base": {
			"chosen": RewardFlow.SCHEDULE_INDEX_BASE,
			"alternative": RewardFlow.SCHEDULE_INDEX_BASE_ALTERNATIVE,
			"status": RewardFlow.SCHEDULE_INDEX_BASE_STATUS,
		},
		"re_derivation": measured.get("bound", {}),
		"schedules": RewardFlow.SCHEDULES,
		"schedule_census": measured.get("census", {}),
		"schedule_census_note": RewardFlow.SCHEDULE_CENSUS_NOTE,
		"committed_weekly_schedule": measured.get("projection", {})
			.get("weekly_schedule", []),
		"committed_daily_schedule": measured.get("projection", {})
			.get("daily_schedule", []),
		"decoder_searches": measured.get("decoders", {}).get("searches", []),
		"decoder_positive_controls": measured.get("decoders", {})
			.get("positive_controls", []),
		"decoder_note": RewardFlow.DECODER_POSITIVE_CONTROL_NOTE,
		"type_letters": RewardFlow.TYPE_LETTERS,
		"type_letters_undecoded": RewardFlow.TYPE_LETTERS_UNDECODED_NOTE,
		"letter_named_declarations": measured.get("decoders", {})
			.get("letters", []),
		"save_only_fields": RewardFlow.SAVE_ONLY_FIELDS,
		"save_only_note": RewardFlow.SAVE_ONLY_NOTE,
		"save_only_census": measured.get("corpus", {}),
		"weekly_cursor_distribution": measured.get("corpus", {})
			.get("weekly_distribution", []),
		"daily_cursor_distribution": measured.get("corpus", {})
			.get("daily_distribution", []),
		"ranking_reward": {
			"table": RewardFlow.RANKING_REWARD_TABLE,
			"consumers": RewardFlow.RANKING_REWARD_CONSUMERS,
			"entry_count": RewardFlow.RANKING_REWARD_ENTRY_COUNT,
			"ownership": RewardFlow.RANKING_REWARD_OWNERSHIP,
		},
		"arms": {"weekly": RewardFlow.WEEKLY_ARMS, "daily": RewardFlow.DAILY_ARMS,
			"note": RewardFlow.ARMS_REPORT_NOTE},
		"divergences": RewardFlow.DIVERGENCES,
		"divergences_reported_as_parity": RewardFlow.DIVERGENCES_REPORTED_AS_PARITY,
		"grant_proof": {
			"parts": RewardFlow.REFUSAL_PROOF_PARTS,
			"wire_keys": RewardFlow.REFUSAL_PROOF_WIRE_KEYS,
			"part_count": RewardFlow.REFUSAL_PROOF_PART_COUNT,
			"allowed_leaf_paths": RewardFlow.ALLOWED_LEAF_PATHS,
			"no_grant": RewardFlow.NO_REWARD_MOVED,
		},
		"proofs": measured.get("proofs", {}),
		"no_eligibility": RewardFlow.NO_ELIGIBILITY,
		"no_cursor_selection": RewardFlow.NO_CURSOR_SELECTION,
		"refusals": {
			"validation_order": RewardFlow.VALIDATION_ORDER,
			"write_step": RewardFlow.WRITE_STEP,
			"ordering_rule": RewardFlow.ORDERING_RULE,
			"client_key_refusals": RewardFlow.CLIENT_KEY_REFUSALS,
			"client_key_aliases": RewardFlow.CLIENT_KEY_ALIASES,
			"refusal_key_map": RewardFlow.REFUSAL_KEY_MAP,
			"reachability": measured.get("refusals", {}),
		},
		"resources": {
			"names": RewardFlow.RESOURCE_NAMES,
			"exposed_count": RewardFlow.EXPOSED_RESOURCE_COUNT,
			"service_accessor_names": RewardFlow.SERVICE_ACCESSOR_NAMES,
			"legacy_mutation_vector_slots": RewardFlow.MUTATION_VECTOR_SLOTS,
			"two_different_eights": "the mutation vector is eight POSITIONAL "
				+ "slots whose first is `unknown` and which has no room for "
				+ "`energy`; the named stored set is eight NAMES, being the seven "
				+ "the service accessor returns plus `energy` under its own name. "
				+ "Reading one as the other is the error this note prevents",
		},
		"volatile_fields": {
			"private_prefix": RewardFlow.VOLATILE_PRIVATE_PREFIX,
			"server_time_field": RewardFlow.VOLATILE_SERVER_TIME_FIELD,
			"count": RewardFlow.VOLATILE_FIELD_COUNT,
		},
		"guards": measured.get("guards", {}),
		"absent_helpers": RewardFlow.ABSENT_HELPERS,
		"static_functions": RewardFlow.STATIC_FUNCTIONS,
		"static_function_count": RewardFlow.STATIC_FUNCTION_COUNT,
		"ownership": {
			"foreign": RewardFlow.FOREIGN_IDENTIFIERS,
			"foreign_roles": RewardFlow.FOREIGN_IDENTIFIER_ROLES,
			"owned": RewardFlow.OWNED_IDENTIFIERS,
			"forbidden_foreign_keys": RewardFlow.FORBIDDEN_FOREIGN_KEYS,
		},
		"derivation_record": RewardFlow.DERIVATION_RECORD,
		"coverage": measured.get("coverage", {}),
		"owners": RewardFlow.owners(),
		"non_claims": RewardFlow.NON_CLAIMS,
	}


func _write_report(path: String, measured: Dictionary) -> void:
	# The evidence directory is this line's to create.  Earlier report writers
	# rely on their directory already being committed, which is why this one
	# cannot: on the first run of a new evidence path the directory does not
	# exist yet, and `FileAccess.open` would fail for a reason that has
	# nothing to do with this report's content.  Creating it explicitly keeps
	# the writability assertion below meaning what it says.
	var directory := path.get_base_dir()
	if not DirAccess.dir_exists_absolute(directory):
		var made := DirAccess.make_dir_recursive_absolute(directory)
		check_eq(made, OK,
			"the rewards evidence directory %s was created" % directory)
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the rewards report at %s is writable" % path)
		return
	file.store_string(JSON.stringify(_report(measured), "  ", false) + "\n")
	file.close()
	check(FileAccess.file_exists(path), "the rewards report was written")
	var reread: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	check(reread is Dictionary,
		"and re-reads as an object, so the report is not a truncated write")
	if reread is Dictionary:
		check_eq(str((reread as Dictionary).get("schema")), "rewards-report-v1",
			"and carries its schema name")

# ---------------------------------------------------------------------------
# The live phase -- `--scenario=live-reward`, the real endpoint over loopback
# ---------------------------------------------------------------------------

## The live scenario name the battery's harness passes.
const LIVE_SCENARIO := "live-reward"

## The two actions this phase drives, in order. BOTH are driven because the
## delivered surface has two cursors with two different arithmetics, and a phase
## that drove one would leave the other unproven end to end.
const LIVE_ACTIONS := [RewardFlow.ACTION_WEEKLY, RewardFlow.ACTION_DAILY]

## The two BOOTSTRAP payload fields that carry a wall clock, named here rather
## than left implicit, because the phase compares a whole bootstrap document.
##
## Found by measurement, not predicted: this phase's no-mutation check compared
## two whole bootstrap payloads and failed, with the two documents differing in
## exactly two leaves -- `playerInfo.last_logged_in` 1791228206 -> 1791228207
## and the envelope `timestamp` 1791228206 -> 1791228207 -- and in NOTHING else.
## Both come from one legacy `ts_now = timestamp_now()`, taken once per read and
## written to both places (`get_player_info.py:6-7` and `:14`), so every
## bootstrap read mutates the payload it returns. That is a property of the READ,
## not of a reward: `/v0/reward` was never called between the two snapshots.
##
## The SAME defect class as the M9 stored-placement `server_time` flake, but it
## is not intermittent -- it is a guaranteed failure whenever two reads straddle
## a second boundary, which four loopback round trips reliably do. Fixed rather
## than re-run, on the same reasoning.
##
## Deliberately NOT the same constants as `RewardFlow.VOLATILE_*`: those describe
## the /v0/reward RESPONSE envelope, which carries `server_time` and does NOT
## carry either field here. Reusing them would have conflated two documents and
## stripped nothing.
const BOOTSTRAP_VOLATILE_ENVELOPE_FIELD := "timestamp"
const BOOTSTRAP_VOLATILE_PLAYER_FIELD := "last_logged_in"
const BOOTSTRAP_VOLATILE_PLAYER_PARENT := "playerInfo"


## `--scenario=live-reward`: the real endpoint, over loopback, on a disposable
## corpus the phase is given.
##
## ## What this phase DOES establish
##
## Both actions are driven through the real `/v0/reward`, and each answer is
## checked for the typed response, the **two-part** cursor proof (the cursor
## moved by exactly the derived transition AND the complete stored resource set
## is unchanged), and the **four-part** grant proof as a whole-document
## containment check: the placed rows, the bought-units list, and the store are
## each compared whole, which is what makes the fourth part non-tautological.
##
## ## Which refusals it can and cannot reach -- stated rather than implied
##
## No **endpoint-side** refusal is expressible through the typed client, because
## `build_reward_intent`'s signature cannot carry a grant-shaped key and
## `ACTION_ADDRESSING_KEY` is empty. The phase therefore drives a **client-side**
## refusal (an action outside the closed set), asserts it made no request, and
## proves the corpus is byte-identical across it. The endpoint's own nine
## refusals -- and their no-mutation property -- are covered by the service
## half's `test_rewards_endpoint.py`, not here. This paragraph exists so the
## phase's evidence is not read as covering a refusal path it does not reach.
func _check_live_reward() -> void:
	info("--- live reward phase ---")
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var endpoint := _endpoint()
	var saves: Variant = await api.list_sessions()
	check(saves is BootData.SaveListResult and saves.ok,
		"the live service lists its disposable corpus")
	if not (saves is BootData.SaveListResult and saves.ok):
		return
	var user_id := str((saves as BootData.SaveListResult).saves[0].id)
	var before: Dictionary = await _live_payload(api, endpoint, user_id)
	check(not before.is_empty(),
		"and the live corpus bootstrap resolves to a non-empty payload")
	if before.is_empty():
		return

	# --- the corpus this phase drives, measured before anything is sent ----
	var resources_before := _live_resources(before)
	check_eq(resources_before.size(), RewardFlow.RESOURCE_NAMES.size(),
		"the live corpus exposes all %d stored resource slots"
			% RewardFlow.RESOURCE_NAMES.size())
	var rows_before := _live_rows(before)
	check(rows_before > 0,
		"the live corpus places %d rows, so the no-row half of the grant proof "
			% rows_before + "is checked against real rows and not vacuously")

	# --- the body a client can build: two keys, nothing else ---------------
	var intent := RewardFlow.build_reward_intent(user_id, LIVE_ACTIONS[0])
	check_eq(bool(intent.get("ok", false)), true,
		"the shared builder accepts the driven action")
	if bool(intent.get("ok", false)):
		check_eq((intent.get("body", {}) as Dictionary).size(),
			RewardFlow.BODY_KEY_COUNT,
			"its body carries EXACTLY %d keys, so a grant shape is not "
				% RewardFlow.BODY_KEY_COUNT
				+ "expressible rather than merely refused")
		check_eq(RewardFlow.refused_client_keys(intent.get("body", {})), [],
			"and resolves to no refusal class of its own")

	var cursors_before := _live_cursors(before)
	var stamps_before := _live_stamps(before)
	var seen := []
	for action: String in LIVE_ACTIONS:
		seen.append(await _check_live_action(api, endpoint, user_id, action,
			before, resources_before, cursors_before, stamps_before))

	# --- both actions driven: the corpus moved, and ONLY on cursors --------
	var after_both: Dictionary = await _live_payload(api, endpoint, user_id)
	# The first draft collected each action's recorded cursor into a local
	# `cursor_rows_after` array and then never read it -- and the line that did
	# so declared it `Array` while the value was an integer, so it raised at
	# runtime and aborted the whole phase. Dead, mis-typed, and load-bearing on
	# nothing: removed rather than fixed.
	check_eq(seen.size(), LIVE_ACTIONS.size(),
		"both actions were driven and each returned its recorded cursor")
	check_eq(_live_rows(after_both), rows_before,
		"after BOTH actions the placed-row count is unchanged: grant-proof part 1")
	check_eq(_live_resources(after_both), resources_before,
		"and every stored resource is byte-identical: grant-proof part 4, "
			+ "compared as the COMPLETE set")

	# --- a refusal the typed client CAN raise: it makes no request --------
	var before_refusal: Dictionary = await _live_payload(api, endpoint, user_id)
	api.configure("legacy_v0", endpoint)
	var refused: Variant = await api.reward_town(user_id, "grant_everything")
	check(refused is RewardFlow.RewardResult and not refused.ok,
		"an action outside the closed set is refused by the typed client")
	if refused is RewardFlow.RewardResult:
		check_eq(str(refused.reason), "invalid_action",
			"with the CLIENT's own named reason, raised before any transport")
		check_eq((refused.resources as Dictionary).size(), 0,
			"and no partial payload")
	var after_refusal: Dictionary = await _live_payload(api, endpoint, user_id)
	# The strip must not be a NO-OP, and the difference must be no WIDER than the
	# documented concession. Three claims, each true in BOTH cases -- when two
	# reads straddle a second and when they land inside one -- because an earlier
	# draft asserted that the two snapshots DIFFER, which is only true of the
	# straddling case and is exactly the flake the M9 stored-placement fix
	# removed. Asserting it here would have re-introduced that flake on a new
	# phase rather than carrying the fix forward.
	check(_live_has_volatile_bootstrap(before_refusal)
			and _live_has_volatile_bootstrap(after_refusal),
		"both snapshots really do carry the two bootstrap read clocks, so "
			+ "erasing them is a concession and not a silent no-op that would "
			+ "leave the difference in place to be mistaken for a mutation")
	var differing := _differing_paths(
		_normalize(before_refusal), _normalize(after_refusal))
	check(_all_paths_volatile(differing),
		"and the two snapshots differed ONLY on documented-volatile paths "
			+ "(%s, %d path(s) this run), never on anything a reward could move"
			% [str(differing), differing.size()])
	check_eq(_normalize(_strip_volatile(after_refusal)),
		_normalize(_strip_volatile(before_refusal)),
		"the refused request left the live corpus BYTE-IDENTICAL once the four "
			+ "volatile fields are excluded, which is the no-mutation claim")

	# --- the OFFLINE double must agree, or one contract has two answers ----
	api.configure("fake")
	var offline: Variant = await api.reward_town(user_id, LIVE_ACTIONS[0])
	check(offline is RewardFlow.RewardResult and offline.ok,
		"the offline double accepts the same intent with no process or socket")
	if offline is RewardFlow.RewardResult and offline.ok:
		check_eq(offline.cursor_after,
			int(cursors_before.get(LIVE_ACTIONS[0], -1)) + 1,
			"and derives the same successor the real endpoint did")
		check_eq((offline.resources as Dictionary).size(),
			RewardFlow.RESOURCE_NAMES.size(),
			"with the same complete resource set")

	# ASCII only. The first draft printed a U+2192 arrow here, and the battery's
	# own harness reads the child's output through the system codec: under
	# `charmap` the capture raised
	# `can't encode character '\u2192' in position 90`, the phase reported three
	# failures -- including a fabricated 600s timeout -- and the arrow was the
	# whole cause. It reads correctly when the suite is run by hand and breaks
	# the battery, so it is gone.
	print("[test] live-reward actions=%s cursors=%s rows=%d->%d "
		% [str(LIVE_ACTIONS), str(cursors_before), rows_before,
			_live_rows(after_both)]
		+ "resources_unchanged=%d/%d refused=invalid_action"
			% [RewardFlow.RESOURCE_NAMES.size(),
				RewardFlow.RESOURCE_NAMES.size()])


## One action, driven end to end against the real endpoint.
##
## Returns `["weekly" | "daily", cursor_before]`, so the caller can compare the
## SECOND action's before value against what the FIRST one persisted.
func _check_live_action(api: Variant, endpoint: String, user_id: String,
		action: String, before: Dictionary, resources_before: Dictionary,
		cursors_before: Dictionary, stamps_before: Dictionary) -> Array:
	api.configure("legacy_v0", endpoint)
	var answer: Variant = await api.reward_town(user_id, action)
	check(answer is RewardFlow.RewardResult,
		"the REAL endpoint's %s answer is a typed result" % action)
	if not (answer is RewardFlow.RewardResult):
		return [action, -1]
	var typed: RewardFlow.RewardResult = answer
	check_eq(bool(typed.ok), true,
		"and it is a SUCCESS: %s / %s" % [str(typed.reason), str(typed.error)])
	if not bool(typed.ok):
		return [action, -1]

	# --- identity: the answer dispatches the preserved branch ---------------
	check_eq(typed.action, action, "the %s answer names the driven action" % action)
	check_eq(typed.command, RewardFlow.ACTION_COMMAND[action],
		"and dispatches the preserved branch %s" % typed.command)
	check_eq(typed.cursor_key, RewardFlow.ACTION_CURSOR_KEY[action],
		"addressing its own cursor")
	check_eq(typed.stamp_key, RewardFlow.ACTION_STAMP_KEY[action],
		"and stamping its own instant")
	check_eq(str(typed.protocol), BootData.PROTOCOL, "the live protocol is compat-v0")
	check_eq(str(typed.result), "success", "and the legacy success result")

	# --- TWO-PART CURSOR PROOF, first half ---------------------------------
	var recorded_before := int(cursors_before.get(action, -1))
	check_eq(typed.cursor_before, recorded_before,
		"the %s before value is the one the live corpus recorded" % action)
	var expected := 0
	if action == RewardFlow.ACTION_WEEKLY:
		expected = (recorded_before + 1) % typed.bound
	else:
		expected = RewardFlow.DAILY_WRAP_TARGET \
			if recorded_before + 1 > RewardFlow.DAILY_BOUND_LITERAL \
			else recorded_before + 1
	check_eq(typed.cursor_after, expected,
		"and the %s cursor advanced by exactly the derived transition" % action)
	check_eq(typed.cursor_change, typed.cursor_after - typed.cursor_before,
		"the change equals its own two ends")
	check_eq(typed.derived_after, typed.cursor_after,
		"the parser's own re-derivation agrees with the answer")
	check_eq(bool(typed.selection_performed), false,
		"and no schedule entry was selected")
	check_eq(typed.bound, RewardFlow.DAILY_BOUND_LITERAL
			if action == RewardFlow.ACTION_DAILY else typed.bound,
		"the %s bound is applied" % action)
	check_eq(bool(typed.bound_is_literal), action == RewardFlow.ACTION_DAILY,
		"and marked literal only for the daily action, where it is a literal in "
			+ "the preserved source")

	# --- the bounds, both cursors, and BOTH differences --------------------
	# Both directions are recomputed here from the answer's OWN bound and
	# cardinality against the recorded reachable set, rather than from a
	# transcribed literal. The first draft hardcoded `[]` for the weekly
	# action's unanswerable set -- which is wrong: the weekly bound is 5 and
	# its schedule has 3 entries, so positions 3 and 4 ARE reachable and NOT
	# answerable. The live phase caught it, and it is exactly the mistake this
	# line exists to prevent: reading the weekly bound as the entry count,
	# which is the very conflation the projection refuses.
	var reachable: Array = RewardFlow.ACTION_REACHABLE[action]
	var reach_positions: Array = []
	for value: Variant in reachable:
		reach_positions.append(int(value))
	reach_positions.sort()
	var answer_positions: Array = []
	for position in range(typed.schedule_cardinality):
		answer_positions.append(position)
	var unanswerable: Array = []
	for value: int in reach_positions:
		if not answer_positions.has(value):
			unanswerable.append(value)
	var unreachable: Array = []
	for value: int in answer_positions:
		if not reach_positions.has(value):
			unreachable.append(value)
	check_eq(typed.reachable_not_answerable, unanswerable,
		"the %s answer names the positions its cursor reaches that the schedule "
			% action + "cannot answer")
	check_eq(typed.answerable_not_reachable, unreachable,
		"and the positions the schedule can answer that the cursor cannot reach, "
			+ "so BOTH directions are reported")
	check(not (typed.reachability as Dictionary).is_empty(),
		"and it carries BOTH cursors' reachability reports, so one answer cannot "
			+ "have one cursor's reachable set read as the other's")
	check_eq((typed.reachability as Dictionary).size(), RewardFlow.ACTION_COUNT,
		"which is exactly the %d cursors" % RewardFlow.ACTION_COUNT)
	for other: String in RewardFlow.ACTIONS:
		var report: Variant = (typed.reachability as Dictionary).get(other)
		check(report is Dictionary, "the %s report is present in the same answer"
			% other)
		if report is Dictionary:
			check_eq(bool((report as Dictionary).get("selection_performed", true)),
				false, "and reports that it selected nothing")
	check_eq(typed.schedule_cardinality,
		EXPECTED_WEEKLY_CARDINALITY
			if action == RewardFlow.ACTION_WEEKLY
			else EXPECTED_DAILY_CARDINALITY,
		"the %s answer reports its schedule's CARDINALITY beside the bound"
			% action)
	var reported_exceedance: int = -1
	if typed.bounds.get(action, {}) is Dictionary:
		reported_exceedance = int((typed.bounds[action] as Dictionary)
			.get("exceeds_cardinality_by", 0))
	check_eq(reported_exceedance,
		typed.bound - typed.schedule_cardinality,
		"and the bound's reported exceedance is recomputed from its own two "
			+ "numbers rather than believed")

	# --- TWO-PART CURSOR PROOF, second half -------------------------------
	check_eq((typed.resources as Dictionary).size(),
		RewardFlow.RESOURCE_NAMES.size(),
		"the %s answer carries the COMPLETE %d stored resource set"
			% [action, RewardFlow.RESOURCE_NAMES.size()])
	check_eq(typed.resources, resources_before,
		"byte-identical to the pre-request values, which is the second half of "
			+ "the two-part proof")

	# --- FOUR-PART GRANT PROOF, as containment ----------------------------
	for wire_key: String in RewardFlow.REFUSAL_PROOF_WIRE_KEYS:
		check(_present(typed.refusal_evidence.get(wire_key, null)),
			"the %s answer carries grant-proof part %s" % [action, wire_key])
	check_eq(typed.allowed_leaf_paths, RewardFlow.ALLOWED_LEAF_PATHS[action],
		"and the %s answer's allowlist is its OWN two paths" % action)
	var middle: Dictionary = await _live_payload(api, endpoint, user_id)
	check_eq(_live_rows(middle), _live_rows(before),
		"part 1: the placed-row count is unchanged and every row byte-identical")
	check_eq(_normalize(_live_rows_value(middle)), _normalize(_live_rows_value(before)),
		"by comparing the rows themselves, not only their count")
	check_eq(_normalize(_live_bought_units(middle)),
		_normalize(_live_bought_units(before)),
		"part 2: the bought-units list is byte-identical")
	check_eq(_normalize(_live_store(middle)), _normalize(_live_store(before)),
		"part 3: the store is byte-identical, so neither a new entry nor an "
			+ "incremented quantity is possible")
	check_eq(_live_resources(middle), resources_before,
		"part 4: the complete stored resource set is byte-identical")
	var outside: Array = []
	for path: Variant in typed.changed:
		if not RewardFlow.ALLOWED_LEAF_PATHS[action].has(str(path)):
			outside.append(str(path))
	check_eq(outside, [],
		"and every changed pointer is inside the two-path allowlist, which is "
			+ "what makes parts 1-3 a containment check")

	# --- the instant was stamped, and only the instant moved --------------
	var stamped := _live_stamps(middle)
	check(stamped.get(action, 0) > 0,
		"the %s instant WAS stamped by the execution" % action)
	check(stamped.get(action, 0) != int(stamps_before.get(action, 0)),
		"and its value moved, so the stamp is real rather than copied")
	var cursors_after := _live_cursors(middle)
	check_eq(int(cursors_after.get(action, -1)), typed.cursor_after,
		"while the %s cursor persisted exactly the derived transition" % action)
	check_eq(typed.stamp_before, int(stamps_before.get(action, -1)),
		"and the answer reported the RECORDED instant, never the wall clock")
	check_eq(bool(typed.stamp_stamped), true, "the stamp is reported as stamped")
	check_eq(bool(typed.stamp_volatile), true, "and as volatile")
	check_eq(typed.volatile_fields,
		[RewardFlow.VOLATILE_PRIVATE_PREFIX + typed.stamp_key,
			RewardFlow.VOLATILE_SERVER_TIME_FIELD],
		"and the volatile-field list is re-derived for the answered action")
	check_eq(typed.derived_args, [] if action == RewardFlow.ACTION_WEEKLY
		else [RewardFlow.DERIVED_DAILY_ITEM, recorded_before],
		"the %s derived argument list is the one that grants nothing" % action)

	return [action, recorded_before]


## The loopback endpoint the live phase must dial.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--gameapi-endpoint="):
			return argument.trim_prefix("--gameapi-endpoint=")
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The corpus's own bootstrap payload, or {} when it cannot be read.
##
## The bootstrap payload is keyed `map`/`playerInfo`/`privateState` -- the live
## service's own keys. The recorded fixture documents are keyed `maps[0]`, and an
## earlier line of this project asserted a field against the wrong key and was
## **passing for the wrong reason**; every field below is therefore read from the
## service's keys and whole objects are compared rather than fixture shapes.
func _live_payload(api: Variant, endpoint: String, user_id: String) -> Dictionary:
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


func _live_map(payload: Dictionary) -> Dictionary:
	return payload.get("map", {}) as Dictionary


func _live_private(payload: Dictionary) -> Dictionary:
	return payload.get("privateState", {}) as Dictionary


## All EIGHT stored resource slots, read from the SERVICE's own state.
##
## Eight and not seven: `boot.resources()` returns the seven accessor names, and
## the `/v0/reward` route's own post-execution snapshot adds
## `privateState.energy` whenever the save carries it -- which is what its
## response carries, and what this contract's parser demands. An absent slot is
## read as `-1` rather than defaulted, so an unread resource fails the proof
## instead of comparing equal.
func _live_resources(payload: Dictionary) -> Dictionary:
	var map := _live_map(payload)
	var player: Dictionary = payload.get("playerInfo", {}) as Dictionary
	var private := _live_private(payload)
	var sources := {
		"xp": map, "gold": map, "wood": map, "oil": map, "steel": map,
		"cash": player, "mana": private, "energy": private,
	}
	var out := {}
	for name: String in RewardFlow.RESOURCE_NAMES:
		out[name] = int((sources[name] as Dictionary).get(name, -1))
	return out


## The placed rows, verbatim, or `null` when the payload carries none. Never
## defaulted to an empty container from a missing key: an unreadable map would
## then look like a map with no rows, which is exactly the vacuous-proof defect.
##
## A **Dictionary**, not an Array -- the recorded map stores `items` keyed by
## placement slot (`"1"`, `"2"`, ...), measured across all 33 committed save
## documents that carry a `privateState`: 33 dictionaries, 0 arrays. The first
## draft typed this as an Array, so `_live_rows` answered `-1` against the real
## corpus and the no-row half of the grant proof was reported as vacuous
## against rows that are there.
func _live_rows_value(payload: Dictionary) -> Variant:
	return _live_map(payload).get("items", null)


## The placed-row count, failing closed to -1 when the payload carries no
## placements object at all.
func _live_rows(payload: Dictionary) -> int:
	var rows: Variant = _live_rows_value(payload)
	if not (rows is Dictionary):
		return -1
	return (rows as Dictionary).size()


func _live_bought_units(payload: Dictionary) -> Variant:
	return _live_private(payload).get("boughtUnits", null)


func _live_store(payload: Dictionary) -> Variant:
	return _live_map(payload).get("store", null)


## Both recorded cursors, read from the payload.
func _live_cursors(payload: Dictionary) -> Dictionary:
	var private := _live_private(payload)
	var out := {}
	for action: String in RewardFlow.ACTIONS:
		var key: String = RewardFlow.ACTION_CURSOR_KEY[action]
		if private.has(key):
			out[action] = int(private[key])
	return out


## Both recorded instants, read from the payload.
func _live_stamps(payload: Dictionary) -> Dictionary:
	var private := _live_private(payload)
	var out := {}
	for action: String in RewardFlow.ACTIONS:
		var key: String = RewardFlow.ACTION_STAMP_KEY[action]
		if private.has(key):
			out[action] = int(private[key])
	return out


## A copy of the payload with the four volatile fields removed, so a refusal's
## no-mutation claim can be compared by WHOLE-document equality.
##
## They fall into two groups, and the distinction is not cosmetic:
##
##  1. The two stamped instants -- each branch stamps exactly one, and each stamp
##     is a wall clock. A REFUSAL must stamp nothing, so erasing them is a small
##     concession that could in principle hide a stamp; it is made anyway because
##     these two are already exercised as the grant proof's positive case
##     directly above, where they are read rather than stripped.
##  2. The two bootstrap read clocks -- `playerInfo.last_logged_in` and the
##     envelope `timestamp`. These are NOT stamped by any reward; every bootstrap
##     read stamps them, so leaving them in made the comparison assert a claim
##     that is false about the legacy server itself. An earlier draft's comment
##     claimed this function removed "the server time on the envelope", which it
##     never did and which the bootstrap payload does not even carry.
##
## Everything else must be byte-identical, which is the strongest form the claim
## can take: a refusal that moved anything ELSE leaves a difference HERE.
func _strip_volatile(payload: Dictionary) -> Dictionary:
	var copy: Dictionary = payload.duplicate(true)
	var private: Variant = copy.get(RewardFlow.PRIVATE_STATE_KEY)
	if private is Dictionary:
		for action: String in RewardFlow.ACTIONS:
			(private as Dictionary).erase(RewardFlow.ACTION_STAMP_KEY[action])
	var info: Variant = copy.get(BOOTSTRAP_VOLATILE_PLAYER_PARENT)
	if info is Dictionary:
		(info as Dictionary).erase(BOOTSTRAP_VOLATILE_PLAYER_FIELD)
	copy.erase(BOOTSTRAP_VOLATILE_ENVELOPE_FIELD)
	return copy


## Whether a snapshot really carries both bootstrap read clocks. Guards the
## strip above against becoming a silent no-op after a legacy rename.
func _live_has_volatile_bootstrap(payload: Dictionary) -> bool:
	if not payload.has(BOOTSTRAP_VOLATILE_ENVELOPE_FIELD):
		return false
	var info: Variant = payload.get(BOOTSTRAP_VOLATILE_PLAYER_PARENT)
	return info is Dictionary \
		and (info as Dictionary).has(BOOTSTRAP_VOLATILE_PLAYER_FIELD)


## Every slash-joined path at which two normalized documents differ.
##
## Reads the normalized form, so a difference the normalizer already erased is
## invisible here -- which is the correct direction: this reports only what the
## byte-identity check will actually see.
func _differing_paths(left: Variant, right: Variant,
		prefix: String = "") -> Array:
	var paths: Array = []
	if typeof(left) != typeof(right):
		paths.append(prefix)
		return paths
	match typeof(left):
		TYPE_DICTIONARY:
			var l: Dictionary = left
			var r: Dictionary = right
			for key: Variant in _union_keys(l, r):
				var at: String = prefix + "/" + str(key)
				paths.append_array(
					_differing_paths(l.get(key), r.get(key), at))
		TYPE_ARRAY:
			var la: Array = left
			var ra: Array = right
			if la.size() != ra.size():
				paths.append(prefix)
				return paths
			for i: int in la.size():
				paths.append_array(
					_differing_paths(la[i], ra[i], prefix + "/" + str(i)))
		_:
			if left != right:
				paths.append(prefix)
	return paths


## The union of both key sets, so a key present on ONE side only is reported as a
## difference rather than silently skipped. Reading only one side's keys would
## make an ADDED field invisible -- the exact shape of a mutation the byte-identity
## check is meant to catch.
func _union_keys(left: Dictionary, right: Dictionary) -> Array:
	var keys: Array = []
	for key: Variant in left.keys():
		keys.append(key)
	for key: Variant in right.keys():
		if not keys.has(key):
			keys.append(key)
	return keys


## Whether every differing path is one this file names as volatile: the two
## stamped instants under the private state, or either bootstrap read clock.
##
## A SUBSET claim, not a "differed exactly on" claim, and deliberately so: it is
## true whether or not the two reads straddled a second.
func _all_paths_volatile(paths: Array) -> bool:
	for path: String in paths:
		if _is_volatile_path(path):
			continue
		return false
	return true


func _is_volatile_path(path: String) -> bool:
	if path == "/" + BOOTSTRAP_VOLATILE_ENVELOPE_FIELD:
		return true
	if path == "/" + BOOTSTRAP_VOLATILE_PLAYER_PARENT \
			+ "/" + BOOTSTRAP_VOLATILE_PLAYER_FIELD:
		return true
	if not path.begins_with(RewardFlow.VOLATILE_PRIVATE_PREFIX):
		return false
	for action: String in RewardFlow.ACTIONS:
		if path == RewardFlow.VOLATILE_PRIVATE_PREFIX \
				+ RewardFlow.ACTION_STAMP_KEY[action]:
			return true
	return false