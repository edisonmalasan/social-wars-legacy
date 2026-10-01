extends "res://tests/test_base.gd"
## Unit-production suite (OpenSpec `godot-unit-production` "Production is
## refused, with the evidence recorded" / "The row-entry inventory names every
## item id's source" / "No duration is derived from the committed training
## time" / "No experience is awarded from a client amount" / "No server
## operation is exposed for production" / "Unit-production evidence and claim
## limits", design D1-D7).
##
## This line delivers a REFUSAL, so most of what it asserts is an **absence**:
## the inventory, the two refusals, and the acquisition finding are positive
## records, and the anti-invention guard is structural — the delivered module's
## whole function inventory is compared against a pinned list, so a readiness,
## remaining-time, progress, duration, completion, production, award, or
## acquisition helper fails the run wherever it is added.
##
## Checks:
##   readiness   a present queue, an absent queue, a recorded start instant, and
##               the refusal record that travels with each — with no readiness,
##               completion, remaining time, or progress reported anywhere;
##   absence     the module declares **EXACTLY** the presence and contract
##               accessors of design D1-D5: no `is_complete`, `is_ready`,
##               `remaining`, `progress`, `ready_at`, `complete`, `duration`,
##               `produce_unit`, `spawn_unit`, `train_unit`, `award_experience`,
##               or `acquire_unit` helper, and the recorded `ABSENT_HELPERS`
##               list names each with its reason;
##   inventory   all five row-entry branches by name, with their item id's
##               source and its classification, the measured **closed count**
##               against the committed dispatcher, the empty DERIVED set, and
##               each entry's committed source line;
##   duration    the committed `training_time` reported as content verbatim and
##               **never** used as a duration, the zero-consumer statement, the
##               measured committed distribution, the three zero-consumer
##               precedents, and no semantics for the soul-mixer sibling field;
##   experience  a recorded `attr["xp"]` read as content and never awarded, the
##               client-sent amount and the print-only level both named, the
##               committed corpus's 0-of-40 absence, and no award anywhere;
##   acquisition the two plausible unit sources recorded as unvalidated
##               client-sent item lists, `package_id` recorded as read-and-
##               unused, the committed tables recorded, nothing enforced or
##               trusted, and no request issued;
##   death       the `KILL` reason recorded as a positional argument the
##               delivered surface never derives, with death and resurrection
##               unimplemented;
##   legacy      the committed legacy source re-read for the facts this line
##               records: the five row-placing call sites and their enclosing
##               branches, the six `add_store_item` call sites, the
##               `complete_*` family, the branch count, and the
##               `training_time` substring matches;
##   boundary    no client source anywhere creates a unit, runs a completion,
##               awards experience, derives a duration from the committed
##               training time, or issues an acquisition request — and the
##               acquired absence of any production endpoint, which is why the
##               compatibility suite stays green **unchanged**;
##   corpus      the committed fresh-player corpus measurement: 40 rows, 11
##               distinct ids, no unit row, no storage, an empty inventory, 40
##               empty attribute bags, and no recorded experience anywhere;
##   content     the committed `training_time` distribution measured from the
##               verified registry, never asserted from prose;
##   purity      the delivered module names no node, a clock, a request, or a
##               transport token, and preloads exactly the two read-only models;
##   containment the content package, the committed saves, the committed
##               fixtures, and the legacy root modules are byte-identical after
##               the run.
##
## Hermetic: no process, no server, no socket, and **no request is issued** —
## this line has nothing to send, which is the point of it. It runs headless
## as part of `verify-boot.ps1` and adds **no live phase**, because there is no
## endpoint and nothing mutates.
##
## `--report=<path>` writes the deterministic `unit-production-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-production/report.json`. Every table is derived from the live
## model, the verified registry, and the committed bytes, so the report cannot
## drift from the code it documents.

const ProductionFlow = preload("res://scripts/units/production_flow.gd")
const UnitQueue = preload("res://scripts/units/unit_queue.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-production/report.json"
## The committed corpus this line measures.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const CORPUS_MAP_INDEX := 0
const EXPECTED_ROWS := 40
const EXPECTED_DISTINCT_ITEM_IDS := 11
## The committed corpus's real placed training producer: **id 26, Command
## Center, at map key 1**, whose committed `training_time` is the field this
## line reports as content and never uses as a duration.
const TARGET_KEY := "1"
const TARGET_ITEM := 26
const TARGET_ITEM_NAME := "Command Center"
const TARGET_TRAINING_TIME := 5
const TARGET_MIN_LEVEL := 1
const TARGET_GROUP_TYPE := "COMMAND_CENTER"
## The committed content distribution, measured rather than trusted.
const EXPECTED_UNITS := 429
const EXPECTED_BUILDINGS := 470
const EXPECTED_BUILDINGS_WITH_TRAINING_TIME := 130
const EXPECTED_UNITS_WITH_TRAINING_TIME := 0
## The committed acquisition tables' own shape.
const EXPECTED_OFFER_PACKS := 44
const EXPECTED_OFFER_PACK_UNIT_IDS := 109
const EXPECTED_OFFER_PACK_BUILDING_IDS := 7
const EXPECTED_OFFER_PACK_ITEM_REFERENCES := 574
const EXPECTED_DARTS_ITEMS := 27
const EXPECTED_DARTS_UNIT_IDS := 44
## The whole function inventory of `production_flow.gd`. This is the
## anti-invention guard (design D4): a readiness, remaining-time, progress,
## duration, completion, production, experience-award, or acquisition helper
## appears here and fails the suite. Every entry is a presence reader, a
## recorded-contract accessor, a note, or a private helper — nothing else.
const EXPECTED_MODULE_METHODS := [
	"_client_routes", "_count_text", "_evaluation_reject",
	"_experience_reject", "_number_text", "_type_name",
	"acquisition_note", "acquisition_record", "acquisition_routes",
	"classification_counts", "classification_vocabulary",
	"committed_training_time", "death_record", "derived_row_entries",
	"evaluate", "experience", "experience_note", "experience_record",
	"no_derivation_finding", "readout_text", "row_entry_branch_names",
	"row_entry_inventory", "training_time_note", "training_time_record",
]
## Helpers a production rule would take. The inventory above is the real gate;
## this list is what the suite also asserts is absent **by name**, so a rename
## cannot smuggle one past the inventory and a leftover fails visibly.
const FORBIDDEN_HELPERS := [
	"is_complete", "is_ready", "remaining", "remaining_time", "progress",
	"progress_ratio", "ready_at", "time_left", "elapsed", "complete",
	"completion", "finish", "duration", "training_duration", "produce_unit",
	"spawn_unit", "create_unit", "train_unit", "award_experience",
	"grant_experience", "add_xp", "acquire_unit", "buy_unit",
]
## Tokens that would mean a production, completion, experience award, or
## acquisition mechanism is implemented. Spelled as fragments because the
## project-scope suite scans every source file for their literal forms; the
## strings are matched against the module's **declarations only**, so the
## recorded contract text may still name them.
const BEHAVIOUR_NEEDLES := [
	"produce_" + "unit", "spawn_" + "unit", "create_" + "unit",
	"train_" + "unit", "acquire_" + "unit", "buy_" + "unit",
	"is_com" + "plete", "is_re" + "ady", "ready_" + "at",
	"award_" + "experience", "grant_" + "experience", "add_x" + "p_unit",
	"soulmixer_" + "speedup",
]
## The same needles scanned over the WHOLE client source tree, which is the
## structural form of "no client source creates a unit, runs a completion, or
## awards experience" (task 2.1).
const CLIENT_SCAN_ROOTS := ["res://scripts", "res://tests"]
## Tokens a pure module must not carry: a node, a clock, a request, or a
## transport. The transport needles are fragments for the same project-scope
## reason as in the queues suite.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]
## The non-claim phrases the delta's evidence requirement names.
const REQUIRED_NON_CLAIMS := [
	"no Flash",
	"NO PRODUCTION MECHANISM, COMPLETION, OR READINESS IS IMPLEMENTED",
	"NO UNIT IS CREATED, TRAINED, OR PLACED",
	"NO DURATION IS DERIVED FROM THE COMMITTED TRAINING TIME",
	"NO EXPERIENCE IS AWARDED",
	"NO ACQUISITION IS IMPLEMENTED OR CLAIMED",
	"NO EXECUTED-LEGACY FIXTURE WAS CAPTURED",
	"DEATH AND RESURRECTION ARE UNREACHABLE",
	"no windowed capture is claimed",
	"no pixel-parity oracle exists",
]
## The legacy root modules this line re-reads for its recorded facts. A missing
## one is a **failure**, never a silently smaller search: a measurement over a
## file that is not there would turn the zero-consumer claim vacuous.
const LEGACY_MODULES := ["command.py", "engine.py", "sessions.py", "server.py",
	"constants.py", "get_game_config.py", "version.py", "auctions.py",
	"get_player_info.py", "legacy_command_recorder.py"]
## The two ways a legacy branch is identified, used to attribute a call site to
## the branch that encloses it.
const CALL_ROW := ["map_add_item(", "map_add_item_from_item("]
const CALL_STORE := ["add_store_item("]
const DELIVERED_SCRIPT := "res://scripts/units/production_flow.gd"

## The registry reference the corpus's committed-type measurement reads, set
## once in `run_scenario()`. A missing registry fails the run before it is used.
var _registry: Variant = null


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	_registry = registry
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
	var legacy_before := _legacy_digest()
	check(bool(legacy_before.get("ok", false)),
		"legacy root modules digest is readable before the run (%s)"
			% str(legacy_before.get("error", "")))
	if not bool(legacy_before.get("ok", false)):
		return
	var save_before := Paths.file_sha256_checked(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check(bool(save_before.get("ok", false)),
		"the committed corpus save is readable before the run")
	if not bool(save_before.get("ok", false)):
		return

	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"the committed package loads (error: %s)"
			% str(content.get("error", "")))
	if not bool(content.get("ok", false)):
		return

	_check_readiness(registry)
	_check_absence()
	_check_inventory()
	_check_duration(registry)
	_check_experience()
	_check_acquisition()
	_check_death()
	var legacy := _check_legacy()
	_check_boundary()
	var corpus := _check_corpus()
	var coverage := _check_content(registry)
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before,
		legacy_before, save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, content, legacy, corpus, coverage,
			package_before, save_before)
	info("unit production: row-entry branches %d, derived %d, storage routes %d, "
		% [ProductionFlow.ROW_ENTRY_COUNT, ProductionFlow.DERIVED_ROW_ENTRY_COUNT,
			ProductionFlow.ACQUISITION_COUNT]
		+ "training_time substrings %d"
			% ProductionFlow.TRAINING_SUBSTRING_MATCH_COUNT)


# ---------------------------------------------------------------------------
# The readiness projection that cannot report readiness (design D1/D4)
# ---------------------------------------------------------------------------


## A present queue, an absent queue, and a recorded start instant — with the
## refusal record travelling beside every answer and **no** readiness,
## completion, remaining time, or progress field anywhere in the result.
func _check_readiness(registry: Variant) -> void:
	var resolver := _resolver(registry)
	# An absent queue: a report, not an error, and still carrying every
	# recorded absence.
	var absent := ProductionFlow.evaluate({}, resolver)
	check(bool(absent.get("ok", false)),
		"an empty bag evaluates: 'no queue' is a REPORT, never an error")
	check_eq(bool(absent.get("present", true)), false,
		"an empty bag reports NO queue")
	check_eq(absent.get("count", null), null,
		"an absent queue has a null count, never a committed zero")
	check_eq(absent.get("start_instant", null), null,
		"an absent queue has a null instant, never a committed zero")
	_check_refusal_fields(absent, "an absent queue")
	# A present queue with a recorded start instant: the instant is reported
	# **verbatim**, and nothing is derived from it.
	var stamped := 1700000000
	var queued := ProductionFlow.evaluate({"nu": 2, "ts": stamped}, resolver)
	check(bool(queued.get("ok", false)),
		"a bag carrying a count and a start instant evaluates")
	check_eq(bool(queued.get("present", false)), true,
		"a queued row reports a queue")
	check_eq(queued.get("count", null), 2,
		"the committed count is reported verbatim, unscaled")
	check_eq(queued.get("start_instant", null), stamped,
		"the recorded start instant is reported verbatim, unrounded")
	_check_refusal_fields(queued, "a queued row")
	# The start instant implies NO timer: a bag whose instant is far in the
	# future produces the same answer in every reported respect, because
	# nothing computes from the instant at all. This is the timing claim's
	# structural form — there is no elapsed-time rule to consume it.
	var later := ProductionFlow.evaluate({"nu": 2, "ts": stamped + 99999999},
		resolver)
	check(bool(later.get("ok", false)),
		"a later-instant bag still evaluates as a report, never an error")
	check_eq(later.get("start_instant", null), stamped + 99999999,
		"the later instant is itself reported verbatim")
	for field: String in ["present", "count", "readiness",
			"production_possible", "completion_available", "duration_computed",
			"experience_awarded", "acquisition_available", "no_derivation"]:
		check_eq(later.get(field, "unset"), queued.get(field, "unset"),
			"a queue %d seconds later reports the SAME '%s': no elapsed-time "
				% [99999999, field]
				+ "rule consumes the instant, so a timer cannot exist here")
	check_eq((later.get("row_entry_branches", []) as Array),
		(queued.get("row_entry_branches", []) as Array),
		"the inventoried row-entry branches do not vary with the instant")
	# A structural rejection is the one error, and it carries every absence
	# unchanged so a refusal never turns one absence into another.
	for value: Variant in [null, [], "bag", 7]:
		var refused := ProductionFlow.evaluate(value, resolver)
		check(not bool(refused.get("ok", false)),
			"the attribute bag %s is refused: a bag that is not a bag is a "
				% [value] + "different thing from an empty one")
		check_eq(str(refused.get("reason", "")),
			UnitQueue.REASON_INVALID_BAG,
			"the refusal carries the queue contract's own named reason")
		check_eq(refused.get("queue", null), null,
			"a refused bag produces no queue at all")
		_check_refusal_fields(refused, "a refused bag")
		check(ProductionFlow.readout_text(refused).is_empty(),
			"a refused bag renders no production readout")
	# The readout says the absences outright, so their absence is never read
	# as a defect.
	var readout := str(queued.get("readout", ""))
	for phrase: String in ["readiness", "unknown-and-uncomputable",
			"CANNOT SAY", "no completion", "no unit is produced"]:
		check(readout.contains(phrase),
			"the production readout states '%s' rather than leaving the reader "
				% phrase + "to infer it")
	var absent_readout := ProductionFlow.readout_text(absent)
	check(absent_readout.contains("no queue"),
		"an absent queue reads as 'no queue'")
	check(absent_readout.contains("absent, not a count of zero"),
		"an absent queue reads as absent, never as a count of zero")
	check(str(queued.get("no_derivation", "")).contains("DERIVED set is EMPTY"),
		"the evaluation carries the recorded no-derivation finding beside it")
	check_eq(queued.get("row_entry_branches", []),
		ProductionFlow.row_entry_branch_names(),
		"the evaluation names the inventoried row-entry branches")
	check_eq((queued.get("derived_row_entry_branches", []) as Array), [],
		"the evaluation reports NO derived row-entry branch")


## Every absence field of one evaluation: a constant false carrying the
## recorded reason, and **no** readiness value the legacy server could not give.
func _check_refusal_fields(evaluation: Dictionary, label: String) -> void:
	for field: String in ["production_possible", "completion_available",
			"duration_computed", "experience_awarded", "acquisition_available"]:
		check_eq(bool(evaluation.get(field, true)), false,
			"%s reports %s as NOT implemented" % [label, field])
	check_eq(str(evaluation.get("readiness", "")),
		ProductionFlow.READINESS_UNKNOWN,
		"%s reports readiness as the one honest value, not a boolean" % label)
	check(str(evaluation.get("readiness_reason", "")).contains("CANNOT SAY"),
		"%s states the server cannot say whether the queue is ready" % label)
	for absent_field: String in ["remaining", "progress", "progress_ratio",
			"ready_at", "duration", "complete", "is_complete", "is_ready",
			"unit_produced", "produced"]:
		check(not evaluation.has(absent_field),
			"%s carries NO %s field at all: the legacy server has no such rule"
				% [label, absent_field])


# ---------------------------------------------------------------------------
# The anti-invention guard (design D4)
# ---------------------------------------------------------------------------


## The module declares **exactly** the presence readers and recorded-contract
## accessors of design D1-D5 — no readiness, remaining-time, progress, duration,
## completion, production, experience-award, or acquisition helper. A helper
## added anywhere in the file fails here.
func _check_absence() -> void:
	var declared := _methods(_source(DELIVERED_SCRIPT))
	check_eq(declared, EXPECTED_MODULE_METHODS,
		"production_flow.gd declares EXACTLY its presence readers and recorded "
			+ "contract accessors — no readiness, remaining-time, progress, "
			+ "duration, completion, production, award, or acquisition helper")
	for helper: String in FORBIDDEN_HELPERS:
		check(not declared.has(helper),
			"the module declares no '%s' helper: the legacy server has no "
				% helper + "such rule to reproduce")
	var absent: Array = ProductionFlow.ABSENT_HELPERS
	check_eq(absent.size(), 12,
		"the recorded ABSENT_HELPERS list names every absent helper")
	var named: Array = []
	for entry: Dictionary in absent:
		named.append(str(entry["helper"]))
		check(not str(entry["absent_because"]).is_empty(),
			"the recorded absence of '%s' states why it is absent"
				% str(entry["helper"]))
	check_eq(named, ["is_complete", "is_ready", "remaining", "progress",
			"ready_at", "complete", "produce_unit", "spawn_unit", "train_unit",
			"duration", "award_experience", "acquire_unit"],
		"the recorded absences are the twelve the delta's refusal needs, in "
			+ "order")
	for helper: String in named:
		check(FORBIDDEN_HELPERS.has(helper),
			"the recorded absence '%s' is also asserted absent by name" % helper)
	# Every absence names a legacy fact rather than a preference.
	var reasons := ""
	for entry: Dictionary in absent:
		reasons += str(entry["absent_because"])
	for phrase: String in ["no legacy command", "no legacy branch", "zero",
			"client"]:
		check(reasons.contains(phrase),
			"the recorded absences ground themselves in the legacy contract "
				+ "('%s')" % [phrase])


# ---------------------------------------------------------------------------
# The row-entry inventory (design D2)
# ---------------------------------------------------------------------------


## All five inventoried branches by name, each with its item id's **source** and
## its classification, the **closed count** measured against the committed
## dispatcher, and the empty DERIVED set.
func _check_inventory() -> void:
	var inventory := ProductionFlow.row_entry_inventory()
	check_eq(inventory.size(), ProductionFlow.ROW_ENTRY_COUNT,
		"the inventory holds exactly the %d legacy row-entry branches"
			% ProductionFlow.ROW_ENTRY_COUNT)
	check_eq(ProductionFlow.row_entry_branch_names(),
		["buy", "place_stored_item", "weekly_reward", "pop_unit",
			"resurrect_hero"],
		"the five inventoried branches are the committed ones, in line order")
	# Every entry: a named source, a classification from the closed vocabulary,
	# and a committed source line.
	var vocabulary := ProductionFlow.classification_vocabulary()
	check_eq(vocabulary, ["client-supplied", "already-existing",
			"derived-from-committed-content"],
		"the classification vocabulary is the closed set the delta names")
	var by_name := {}
	var client_supplied: Array = []
	var already_existing: Array = []
	for entry: Dictionary in inventory:
		var branch := str(entry["branch"])
		by_name[branch] = entry
		check(not str(entry["item_id_source"]).is_empty(),
			"the %s entry names where its item id comes from" % branch)
		check(vocabulary.has(str(entry["classification"])),
			"the %s entry's classification is from the closed vocabulary"
				% branch)
		check(str(entry["site"]).begins_with("command.py:"),
			"the %s entry names the committed dispatcher line that fixes it"
				% branch
				+ " (a client-supplied id is never a derivation)")
		check(not str(entry["note"]).is_empty(),
			"the %s entry records what the branch actually does" % branch)
		check(int(entry["item_id_argument_index"]) >= 0,
			"the %s entry names the argument index its item id arrives at"
				% branch)
		match str(entry["classification"]):
			ProductionFlow.CLASS_CLIENT:
				client_supplied.append(branch)
			ProductionFlow.CLASS_ALREADY:
				already_existing.append(branch)
			_:
				pass
	# Four client-supplied, one already-existing, and NONE derived.
	check_eq(client_supplied, ["buy", "place_stored_item", "weekly_reward",
			"resurrect_hero"],
		"FOUR of the five branches take their item id from a client argument, "
			+ "by name")
	check_eq(already_existing, ["pop_unit"],
		"the fifth (pop_unit) is the only already-existing one: it moves a row "
			+ "that already existed")
	check_eq(ProductionFlow.classification_counts(),
		{"client-supplied": 4, "already-existing": 1,
			"derived-from-committed-content": 0},
		"the classification counts are 4 client-supplied, 1 already-existing, "
			+ "0 derived")
	check_eq((ProductionFlow.derived_row_entries() as Array), [],
		"the DERIVED set is EMPTY: no branch derives a unit from a completed "
			+ "queue, a duration, or committed production content")
	check_eq(ProductionFlow.DERIVED_ROW_ENTRY_COUNT, 0,
		"the recorded derived count is zero, as a closed fact")
	# Each entry's source is named with the argument it arrives at, and the
	# already-existing one is recorded as a MOVE with the client overwrite
	# stated.
	for branch: String in client_supplied:
		var entry: Dictionary = by_name[branch]
		check(str(entry["item_id_source"]).contains("client args["),
			"the %s entry names the client argument its item id arrives at"
				% branch)
		check(int(entry["item_id_argument_index"]) == int(
			str(entry["item_id_source"]).split("client args[")[1].split("]")[0]),
			"the %s entry's argument index matches the source it names" % branch)
	var pop: Dictionary = by_name["pop_unit"]
	check(str(pop["item_id_source"]).contains("ALREADY"),
		"the pop_unit entry says the row it places ALREADY existed")
	check(str(pop["note"]).contains("command.py:403"),
		"the pop_unit entry records that the client id overwrites the popped "
			+ "row's committed item, so even a move is not a derivation")
	check_eq(str(pop["call"]), "map_add_item_from_item",
		"pop_unit places through map_add_item_from_item, the one call that "
			+ "takes a row rather than an id")
	# The recorded finding is present as content, naming the empty set.
	var finding := ProductionFlow.no_derivation_finding()
	for phrase: String in ["NO ROW-ENTRY BRANCH DERIVES A UNIT", "FOUR",
			"garrison", "DERIVED set is EMPTY", "closed measurement"]:
		check(finding.contains(phrase),
			"the recorded no-derivation finding names '%s'" % phrase)
	check_eq(ProductionFlow.NAMED_BRANCH_COUNT, 63,
		"the dispatcher's named-branch count is recorded as 63")
	check_eq(ProductionFlow.COMPLETE_FAMILY, ["complete_collection",
			"complete_goal", "complete_tutorial"],
		"the complete_* family is recorded as exactly those three, so no queue "
			+ "completion exists among them")
	# A caller may keep and mutate the returned table; the module's own is
	# untouched.
	var handed := ProductionFlow.row_entry_inventory()
	(handed as Array).clear()
	check_eq(ProductionFlow.row_entry_inventory().size(),
		ProductionFlow.ROW_ENTRY_COUNT,
		"the inventory is handed out as a fresh copy, never the constant "
			+ "itself")
	var vocabulary_copy := ProductionFlow.classification_vocabulary()
	(vocabulary_copy as Array).append("tampered")
	check_eq(ProductionFlow.classification_vocabulary().size(), 3,
		"the classification vocabulary is handed out as a fresh copy")


# ---------------------------------------------------------------------------
# The training-time refusal (design D3)
# ---------------------------------------------------------------------------


## The committed `training_time` is reportable **as content** and is never used
## as a duration: the value passes through verbatim, the zero-consumer fact and
## the measured distribution are present, and NO duration semantics are added
## for the soul-mixer sibling field either.
func _check_duration(registry: Variant) -> void:
	var record := ProductionFlow.training_time_record()
	check_eq(record["field"], "training_time",
		"the recorded field is the committed training time")
	check_eq(int(record["consumer_count"]), 0,
		"the recorded consumer count is ZERO: no committed branch reads the "
			+ "field")
	check_eq(bool(record["implemented_as_duration"]), false,
		"the recorded field is declared NOT implemented as a duration")
	check_eq(bool(record["duration_computed"]), false,
		"the recorded contract computes no duration")
	check_eq(record["searched_modules"],
		["command.py", "engine.py", "sessions.py", "server.py", "constants.py",
			"get_game_config.py"],
		"the zero-consumer claim names the six modules it is measured over")
	for phrase: String in ["ZERO legacy consumers", "command.py:735",
			"command.py:737", "DISTINCT field sm_training_time",
			"NO production time"]:
		check(str(record["rule"]).contains(phrase),
			"the recorded refusal names '%s'" % phrase)
	# The committed value is reported verbatim, as content, and nothing is
	# derived from it. Every shape is passed through untouched.
	var target: Variant = registry.get_entry("buildings",
		str(TARGET_ITEM)).get("entry", null)
	check(target is Dictionary, "the Command Center's definition resolves")
	if target is Dictionary:
		check_eq(ProductionFlow.committed_training_time(target),
			TARGET_TRAINING_TIME,
			"the target's committed training_time is reported verbatim")
	for value: Variant in [0, 5, 1, 3600, "5", 2.5, -1, true]:
		check_eq(ProductionFlow.committed_training_time({"training_time": value}),
			value,
			"the committed value %s is reported verbatim and UNCHANGED: no "
				% [value]
				+ "scaling, rounding, defaulting, or clamping is applied")
	# An absent field is a NAMED absence, never a substituted zero.
	check_eq(ProductionFlow.committed_training_time({}), null,
		"a definition carrying no training_time reports it as ABSENT, never as "
			+ "a committed zero")
	check_eq(ProductionFlow.committed_training_time(null), null,
		"a non-object entry reports no training time at all")
	check(ProductionFlow.training_time_note(null).contains("absent"),
		"the readout names an absent training time as an absence")
	var note := ProductionFlow.training_time_note(TARGET_TRAINING_TIME)
	check(note.contains("CONTENT ONLY") and note.contains("never used as a"),
		"the readout renders the committed value as CONTENT ONLY, immediately "
			+ "followed by the refusal")
	# NO duration is derived from it: the module declares no duration helper,
	# and the inventory guard above already proved the whole function set.
	var declared := _methods(_source(DELIVERED_SCRIPT))
	for helper: String in ["duration", "training_duration", "remaining",
			"progress", "ready_at", "elapsed", "time_left", "seconds_left"]:
		check(not declared.has(helper),
			"no '%s' helper exists: a duration is never computed from the "
				% helper + "committed training time")
	check_eq(declared, EXPECTED_MODULE_METHODS,
		"the delivered module's function inventory is unchanged by reading the "
			+ "committed field: reading it adds no helper of any kind")
	# The zero-consumer precedents: this is the THIRD such field, and the
	# earlier two are named.
	var precedents: Array = record["zero_consumer_precedents"]
	check_eq(precedents.size(), 3,
		"three committed fields in this project have no legacy consumer")
	var precedent_fields: Array = []
	for entry: Dictionary in precedents:
		precedent_fields.append(str(entry["field"]))
		check(not str(entry["fact"]).is_empty(),
			"the %s precedent states its measured fact" % str(entry["field"]))
		check(not str(entry["line"]).is_empty(),
			"the %s precedent names the line that recorded it"
				% str(entry["field"]))
	check_eq(precedent_fields, ["unit_capacity", "reward_type / reward_amount",
			"training_time"],
		"the earlier zero-consumer fields are named, with this one third")
	# NO duration semantics for the SIBLING field either.
	check_eq(record["sibling_field"], "sm_training_time",
		"the recorded sibling duration field is the soul mixer's own")
	for phrase: String in ["OWN field", "QUEUED UNIT", "never charges",
			"NOT treated as a general production duration",
			"NO production or timing semantics are derived from it either"]:
		check(str(record["sibling_note"]).contains(phrase),
			"the recorded sibling note names '%s'" % phrase)
	check_eq(record["sibling_field"], UnitQueue.SPEEDUP_FIELD,
		"the sibling field is the same one the queues contract records")
	# The coverage sentence is present as content and cross-checked against the
	# measurement above.
	for phrase: String in ["EVERY committed item", "exactly two values",
			"0 on 340 of the 470 buildings", "all 429 units",
			"130 of the 470 committed buildings", "0 of the 429 committed units",
			"Command Center", "reported for reference ONLY"]:
		check(str(record["coverage"]).contains(phrase),
			"the recorded coverage names '%s' as CONTENT" % phrase)


# ---------------------------------------------------------------------------
# The experience award that is refused (design D5)
# ---------------------------------------------------------------------------


## A recorded `attr["xp"]` is read as content and **never** awarded; the
## client-sent amount and the print-only level are both named; and the corpus's
## 0-of-40 absence is recorded.
func _check_experience() -> void:
	var record := ProductionFlow.experience_record()
	check_eq(record["command"], "add_xp_unit",
		"the only command writing a recorded experience is recorded by name")
	check_eq(int(record["attr_slot"]), UnitQueue.ATTR_SLOT,
		"the recorded experience lives in the placed row's attr bag, the same "
			+ "slot the queue keys use")
	check_eq(str(record["attr_key"]), "xp",
		"the recorded experience key is the committed attr['xp']")
	check_eq(bool(record["award_implemented"]), false,
		"the recorded experience award is declared NOT implemented")
	check_eq(bool(record["creates_anything"]), false,
		"the recorded contract states that add_xp_unit CREATES NOTHING")
	for phrase: String in ["client args[1]", "client args[2]", "printed line"]:
		check(str(record["amount_source"]).contains(phrase)
				or str(record["level_source"]).contains(phrase),
			"the recorded award contract names the client-sent %s"
				% phrase)
	check(str(record["amount_source"]).contains("client args[1]"),
		"the CLIENT-SENT AMOUNT is named: the XP value arrives from the client")
	check(str(record["level_source"]).contains("client args[2]"),
		"the client-sent LEVEL is named, and recorded as print-only")
	check(str(record["level_source"]).contains("ONLY"),
		"the client-sent level is used ONLY in a printed line and written "
			+ "nowhere")
	for phrase: String in ["NO EXPERIENCE IS AWARDED FROM A CLIENT AMOUNT",
			"CREATES NOTHING", "untrusted client-delta"]:
		check(str(record["rule"]).contains(phrase),
			"the recorded experience contract names '%s'" % phrase)
	# A recorded value is read as content and never awarded.
	var read := ProductionFlow.experience({"xp": 250})
	check(bool(read.get("ok", false)),
		"a bag carrying a recorded experience is read")
	check_eq(read.get("recorded", null), 250,
		"the recorded experience is reported verbatim")
	check_eq(bool(read.get("recorded_is_absent", true)), false,
		"a bag carrying attr['xp'] reports it as recorded")
	check_eq(bool(read.get("awarded", true)), false,
		"a recorded experience is NEVER awarded")
	check_eq(bool(read.get("award_implemented", true)), false,
		"the record states the award is not implemented")
	check(str(read.get("award_source", "")).contains("client argument"),
		"the record names WHY nothing is awarded: the only writer takes its "
			+ "amount from a client argument")
	# A client-sent amount is reported as recorded, never interpreted: a
	# non-numeric value passes through untouched, because it is a fact about
	# what a client said.
	for value: Variant in ["250", 250.5, -5, true, 0]:
		var held := ProductionFlow.experience({"xp": value})
		check_eq(held.get("recorded", null), value,
			"the recorded value %s is reported verbatim, never coerced to a "
				% [value] + "number this contract may interpret")
		check_eq(bool(held.get("awarded", true)), false,
			"a recorded value of %s is still never awarded" % [value])
	# An absent key is a NAMED absence, never a substituted zero.
	var absent := ProductionFlow.experience({})
	check(bool(absent.get("ok", false)),
		"a bag with no recorded experience is still a report, not an error")
	check_eq(bool(absent.get("recorded_is_absent", true)), true,
		"a bag with no attr['xp'] reports it as absent")
	check_eq(absent.get("recorded", "unset"), null,
		"an absent experience is null, which a zero cannot say")
	check_eq(bool(absent.get("awarded", true)), false,
		"an absent experience is never awarded either")
	# A bag that is not a bag is a REFUSAL, never a silent zero.
	for value: Variant in [null, [], "bag", 7]:
		var refused := ProductionFlow.experience(value)
		check(not bool(refused.get("ok", false)),
			"the attribute bag %s is refused for experience: an empty bag and a "
				% [value] + "missing bag mean the same thing, a non-bag does not")
		check_eq(str(refused.get("reason", "")),
			ProductionFlow.REASON_INVALID_ATTR,
			"the experience refusal carries its own named reason")
		check_eq(bool(refused.get("awarded", true)), false,
			"a refused experience read awards nothing")
	# No award is granted, computed, or displayed.
	var declared := _methods(_source(DELIVERED_SCRIPT))
	for helper: String in ["award_experience", "grant_experience", "add_xp",
			"apply_experience", "experience_award", "level_up_experience"]:
		check(not declared.has(helper),
			"the module declares no '%s' helper: NO experience is awarded, "
				% helper + "granted, or computed from a client amount")
	for field: String in ["granted", "level_up", "xp_awarded", "experience_award",
			"new_xp", "total_xp"]:
		check(not read.has(field),
			"the experience record carries NO %s field: there is no award to "
				% field + "report, only a recorded value and its refusal")
	# The corpus measurement, recorded as content.
	for phrase: String in ["0 of its 40", "client amount"]:
		check(str(record["corpus_note"]).contains(phrase),
			"the recorded corpus note names '%s'" % phrase)
	check(str(record["corpus_finding"]).contains("NO unit row"),
		"the recorded corpus finding states there is no unit row to award to")
	# The readout renders the value and the refusal, never a number a player
	# could read as an award.
	var note := ProductionFlow.experience_note(read)
	check(note.contains("250") and note.contains("never awarded"),
		"the experience readout shows the recorded value and says it is never "
			+ "awarded")
	check(ProductionFlow.experience_note(absent).contains("absent"),
		"the readout names an absent recorded experience as absent")
	check(ProductionFlow.experience_note({}).is_empty(),
		"a refused experience renders no readout")


# ---------------------------------------------------------------------------
# The acquisition finding (design D1/D5)
# ---------------------------------------------------------------------------


## The two plausible unit sources are recorded as unvalidated client-sent item
## lists, `package_id` is recorded as read-and-unused, the committed tables
## are recorded, **nothing is enforced or trusted**, and no request is issued.
func _check_acquisition() -> void:
	var record := ProductionFlow.acquisition_record()
	check_eq(bool(record["implemented"]), false,
		"acquisition is declared NOT implemented")
	check_eq(bool(record["request_issued"]), false,
		"NO acquisition request is issued by this line")
	var routes: Array = record["routes"]
	check_eq(routes.size(), ProductionFlow.ACQUISITION_COUNT,
		"the six legacy storage-filling routes are recorded")
	check_eq(int(record["route_count"]), 6,
		"the recorded route count is six")
	var by_name := {}
	var client_supplied: Array = []
	for entry: Dictionary in routes:
		var branch := str(entry["branch"])
		by_name[branch] = entry
		check(str(entry["site"]).begins_with("command.py:"),
			"the %s route names the committed dispatcher line that fills the "
				% branch + "storage")
		check(not str(entry["input"]).is_empty(),
			"the %s route names the source of the ids it stores" % branch)
		if not bool(entry["trusted"]):
			client_supplied.append(branch)
	check_eq(client_supplied, ["store_add_items", "win_daily_bonus",
			"buy_stored_item_cash", "buy_offer_pack"],
		"FOUR of the six routes take their ids from a client argument, by name")
	# The two plausible unit sources, each recorded as an unvalidated
	# client-sent item list.
	var offer: Dictionary = by_name["buy_offer_pack"]
	check(str(offer["input"]).contains("client args[1]"),
		"buy_offer_pack is recorded as taking a client-sent JSON array of ids")
	check(str(offer["note"]).contains("NO lookup"),
		"the offer-pack route records that there is NO lookup into the "
			+ "committed offer_packs table")
	check_eq(bool(offer["trusted"]), false,
		"the offer-pack route is NOT trusted: the server stores whatever the "
			+ "client named")
	var cash: Dictionary = by_name["buy_stored_item_cash"]
	check(str(cash["input"]).contains("client args[0]"),
		"buy_stored_item_cash is recorded as taking ONE client-sent id")
	check_eq(bool(cash["trusted"]), false,
		"the cash-purchase route is NOT trusted either")
	# `package_id` read and never used.
	check(str(record["package_id"]).contains("NEVER USES IT"),
		"package_id is recorded as read and NEVER USED")
	check(str(record["package_id"]).contains("command.py:711"),
		"the read-and-unused record names the committed line that reads it")
	# The committed tables: their shape, and precisely what the legacy source
	# does with each. A client-supplied id is never treated as authorising.
	var tables: Array = record["tables"]
	check_eq(tables.size(), 2,
		"the two committed acquisition tables are recorded")
	var table_names: Array = []
	for entry: Dictionary in tables:
		table_names.append(str(entry["table"]))
		check_eq(bool(entry["read_by_dispatcher_branch"]), false,
			"no dispatcher branch derives an acquisition from the %s table"
				% str(entry["table"]))
		check(not str(entry["note"]).is_empty(),
			"the %s table records what the legacy source actually does with it"
				% str(entry["table"]))
		check(int(entry["entries"]) > 0,
			"the %s table records its committed entry count" % str(entry["table"]))
	check_eq(table_names, ["offer_packs", "darts_items"],
		"the committed acquisition tables are recorded by name")
	var packs: Dictionary = tables[0]
	check_eq(int(packs["entries"]), EXPECTED_OFFER_PACKS,
		"the committed offer_packs table carries %d packs"
			% EXPECTED_OFFER_PACKS)
	check_eq(int(packs["distinct_unit_references"]),
		EXPECTED_OFFER_PACK_UNIT_IDS,
		"the committed offer_packs table references %d DISTINCT unit ids"
			% EXPECTED_OFFER_PACK_UNIT_IDS)
	check_eq(int(packs["total_item_references"]),
		EXPECTED_OFFER_PACK_ITEM_REFERENCES,
		"the recorded offer-pack reference total is %d, kept separate from the "
			% EXPECTED_OFFER_PACK_ITEM_REFERENCES
			+ "distinct count so the two can never be conflated")
	check_eq((packs["legacy_module_reads"] as Array), [],
		"offer_packs is read by NO legacy module at all")
	var darts: Dictionary = tables[1]
	check_eq(int(darts["entries"]), EXPECTED_DARTS_ITEMS,
		"the committed darts_items table carries %d entries"
			% EXPECTED_DARTS_ITEMS)
	check_eq(int(darts["distinct_unit_references"]), EXPECTED_DARTS_UNIT_IDS,
		"the committed darts_items table references %d DISTINCT unit ids"
			% EXPECTED_DARTS_UNIT_IDS)
	check_eq((darts["legacy_module_reads"] as Array).size(), 1,
		"darts_items is read by exactly ONE legacy module, and the record "
			+ "names it rather than claiming the table is unread")
	check(str(darts["note"]).contains("start_date"),
		"the darts record states that module reads the table for its DATES "
			+ "only")
	# Nothing is enforced, nothing is trusted, and no mechanism exists.
	var declared := _methods(_source(DELIVERED_SCRIPT))
	for helper: String in ["acquire_unit", "buy_unit", "grant_unit", "offer_unit",
			"purchase_unit", "open_pack", "unpack_offer"]:
		check(not declared.has(helper),
			"the module declares no '%s' helper: NO acquisition mechanism is "
				% helper + "implemented")
	for phrase: String in ["NO ACQUISITION IS IMPLEMENTED OR CLAIMED",
			"unvalidated client-sent item lists", "LATER milestone's work",
			"no acquisition request", "never treated as authorising"]:
		check(str(record["note"]).contains(phrase),
			"the recorded acquisition note names '%s'" % phrase)
	check_eq(ProductionFlow.acquisition_note(), str(record["note"]),
		"the readout note is the record's own statement, not a restatement")
	# The delivered module names no acquisition command and no committed
	# acquisition table in CODE: every one of them is recorded content, and a
	# code reference would be a mechanism. (The names live in the recorded
	# strings, which the code-only transform blanks.)
	var delivered := _code_only(_source(DELIVERED_SCRIPT))
	for needle: String in ["buy_offer" + "_pack", "buy_stored_item_" + "cash",
			"add_store" + "_item", "offer_" + "packs", "darts_" + "items",
			"/v0/"]:
		check(not delivered.contains(needle),
			"the delivered module names no %s in code: the acquisition routes "
				% needle
			+ "are recorded content, never an implemented mechanism")


# ---------------------------------------------------------------------------
# Death and resurrection
# ---------------------------------------------------------------------------


## The `KILL` reason is recorded as the positional argument it is, with death
## and resurrection unimplemented and no unit created from a queue.
func _check_death() -> void:
	var record := ProductionFlow.death_record()
	check_eq(bool(record["implemented"]), false,
		"death and resurrection are declared NOT implemented")
	check_eq(bool(record["unit_created"]), false,
		"no unit is created by the recorded death or resurrection path")
	for phrase: String in ["command.py:151", "command.py:159", "'KILL'"]:
		check(str(record["kill_reason_source"]).contains(phrase),
			"the recorded KILL reason names '%s'" % phrase)
	check(str(record["kill_reason_source"]).contains("args[1]"),
		"the KILL reason is recorded as a POSITIONAL ARGUMENT of sell, which "
			+ "is what command.py:151 reads")
	check(str(record["delivered_surface"]).contains("derives its own reason"),
		"the record states the delivered building-sell surface derives its own "
			+ "reason and ignores a client-supplied one")
	for phrase: String in ["DEATH AND RESURRECTION", "UNIMPLEMENTED",
			"NO death", "NO resurrection", "NO unit is created from a queue"]:
		check(str(record["rule"]).contains(phrase),
			"the recorded death finding names '%s'" % phrase)
	check(str(record["rule"]).contains("command.py:169-181"),
		"the record names the separate kill branch, which deletes the row "
			+ "without touching the counter")


# ---------------------------------------------------------------------------
# The committed legacy source, re-read (task 2.1 / design D2/D3)
# ---------------------------------------------------------------------------


## The facts this line records are re-derived from the committed legacy source
## rather than trusted from prose: the row-placing call sites and the branches
## enclosing them, the storage-filling call sites, the `complete_*` family, the
## named-branch count, and the `training_time` substring matches. A measurement
## is what makes the recorded counts checkable, and a mismatch fails here.
func _check_legacy() -> Dictionary:
	var dispatcher := _legacy_lines("command.py")
	if dispatcher.is_empty():
		fail("the committed dispatcher is readable: every fact this line "
			+ "records is measured out of it, and a missing file would make "
			+ "the whole inventory vacuous")
		return {}
	# The five row-placing call sites, and the branch each belongs to.
	var row_sites: Array = []
	var row_branches: Array = []
	for index in range(dispatcher.size()):
		var line: String = dispatcher[index]
		if not _is_call(line, CALL_ROW):
			continue
		row_sites.append(index + 1)
		row_branches.append(_enclosing_branch(dispatcher, index))
	check_eq(row_sites, ProductionFlow.ROW_ENTRY_LINES,
		"the committed dispatcher's row-placing call sites are EXACTLY the five "
			+ "line numbers the inventory records")
	check_eq(row_branches, ProductionFlow.row_entry_branch_names(),
		"each row-placing call site belongs to the branch the inventory names, "
			+ "measured rather than asserted")
	check_eq(row_sites.size(), ProductionFlow.ROW_ENTRY_COUNT,
		"the measured row-placing call-site count matches the recorded count: a "
			+ "sixth would be an unrecorded gap, not a silent addition")
	# The six storage-filling call sites, and the branch each belongs to.
	var store_sites: Array = []
	var store_branches: Array = []
	for index in range(dispatcher.size()):
		if not _is_call(dispatcher[index], CALL_STORE):
			continue
		store_sites.append(index + 1)
		store_branches.append(_enclosing_branch(dispatcher, index))
	check_eq(store_sites, ProductionFlow.ACQUISITION_LINES,
		"the committed dispatcher's add_store_item call sites are EXACTLY the "
			+ "six line numbers the routes record")
	var route_branches: Array = []
	for entry: Dictionary in ProductionFlow.acquisition_routes():
		route_branches.append(str(entry["branch"]))
	check_eq(store_branches, route_branches,
		"each storage-filling call site belongs to the branch the route table "
			+ "names, measured rather than asserted")
	# The `complete_*` family, and the whole named-branch count.
	var complete: Array = []
	var named := {}
	for line: String in dispatcher:
		var branch := _branch_of(line)
		if branch == "":
			continue
		named[branch] = true
		if branch.begins_with("complete_"):
			complete.append(branch)
	complete.sort()
	check_eq(complete, ProductionFlow.COMPLETE_FAMILY,
		"the measured complete_* family is exactly the three the contract "
			+ "records, so no queue completion exists among them")
	check_eq(named.size(), ProductionFlow.NAMED_BRANCH_COUNT,
		"the measured named-dispatcher-branch count is %d"
			% ProductionFlow.NAMED_BRANCH_COUNT)
	# The `training_time` substring matches across the six named modules.
	#
	# Two counts are kept deliberately. `command.py` line 735 carries the substring
	# TWICE, so counting one match per *line* under-reports the occurrences and
	# reported 2 where the occurrence count is 3. The per-line markers and the
	# occurrence total are therefore measured separately, and each is asserted
	# against its own recorded constant.
	var matches: Array = []
	var occurrences := 0
	var non_sibling: Array = []
	var outside_span: Array = []
	for module: String in ProductionFlow.TRAINING_SEARCHED_MODULES:
		var lines := _legacy_lines(module)
		if lines.is_empty():
			fail("the legacy module %s is readable: the zero-consumer claim "
				% module
				+ "is measured over it, and a missing file would make the "
				+ "measurement vacuous")
			continue
		for index in range(lines.size()):
			var line: String = lines[index]
			var on_line := line.count(ProductionFlow.TRAINING_FIELD)
			if on_line == 0:
				continue
			occurrences += on_line
			matches.append("%s:%d" % [module, index + 1])
			if line.replace(ProductionFlow.TRAINING_SUBSTRING_MATCH_FIELD, "") \
					.contains(ProductionFlow.TRAINING_FIELD):
				non_sibling.append("%s:%d" % [module, index + 1])
			if module == "command.py":
				var number := index + 1
				if number < int(ProductionFlow.SOULMIXER_SPAN[0]) \
						or number >= int(ProductionFlow.SOULMIXER_SPAN[1]):
					outside_span.append("%s:%d" % [module, number])
	check_eq(occurrences, ProductionFlow.TRAINING_SUBSTRING_MATCH_COUNT,
		"the measured training_time substring OCCURRENCE count is %d, counted per "
			% ProductionFlow.TRAINING_SUBSTRING_MATCH_COUNT
			+ "occurrence rather than per line")
	check_eq(matches.size(),
		ProductionFlow.TRAINING_SUBSTRING_MATCH_DISTINCT_LINES,
		"the distinct lines carrying a match are counted separately from the "
			+ "occurrences, so neither can be mistaken for the other")
	check_eq(matches, ProductionFlow.TRAINING_SUBSTRING_MATCH_LINES,
		"the measured training_time substring matches are EXACTLY the lines the "
			+ "contract records")
	check_eq(matches.size(), ProductionFlow.TRAINING_SUBSTRING_MATCH_DISTINCT_LINES,
		"the measured substring-match DISTINCT-LINE count is %d, and the suite does "
			% ProductionFlow.TRAINING_SUBSTRING_MATCH_DISTINCT_LINES
			+ "not take that number on trust either: it is asserted separately from "
			+ "the occurrence count, which is what the zero-consumer claim rests on")
	check_eq(non_sibling, [],
		"EVERY training_time occurrence is the DISTINCT sm_training_time "
			+ "field: no line reads the committed training time itself")
	check_eq(outside_span, [],
		"every occurrence lies inside the soul-mixer speedup branch "
			+ "(command.py:727-744), so no queue branch reads a duration")
	check_eq((ProductionFlow.TRAINING_SEARCHED_MODULES as Array).size(), 6,
		"the zero-consumer claim is measured over six legacy modules")
	# Neither committed acquisition table is read by the dispatcher.
	for table: String in ["offer_packs", "darts_items"]:
		var readers: Array = []
		for module: String in LEGACY_MODULES:
			for line: String in _legacy_lines(module):
				if line.contains(table) and module != "get_game_config.py":
					readers.append(module)
		check_eq(readers, [],
			"the %s table is named by no legacy module other than "
				% table + "get_game_config.py, and by no dispatcher branch at "
				+ "all")
	return {
		"row_sites": row_sites,
		"row_branches": row_branches,
		"store_sites": store_sites,
		"store_branches": store_branches,
		"complete_family": complete,
		"named_branches": named.size(),
		"training_matches": matches,
		"dispatcher": "command.py",
	}


# ---------------------------------------------------------------------------
# The boundary (task 2.1)
# ---------------------------------------------------------------------------


## No client source anywhere creates a unit, runs a completion, awards
## experience, derives a duration from the committed training time, or issues
## an acquisition request — and no production endpoint exists, which is why
## the compatibility suite stays green **unchanged**.
##
## The whole-source scan is reported **per needle with the offending files
## listed**, not once per file: one `[]` assertion is exactly as strong as a
## thousand, and a failure names the file instead of a count.
func _check_boundary() -> void:
	var sources := _client_sources()
	check(sources.size() > 40,
		"the client source tree is enumerable for the boundary scan (%d files)"
			% sources.size())
	for needle: String in BEHAVIOUR_NEEDLES:
		var offenders: Array = []
		for source: String in sources:
			if _code_only(_source(source)).contains(needle):
				offenders.append(source)
		check_eq(offenders, [],
			"no client source declares '%s' in code: no client source creates a "
				% needle
			+ "unit, runs a completion, awards experience, or buys one")
	# No compat route is named in code by the delivered module: it has nothing
	# to send and no intent to authorise.
	var delivered := _code_only(_source(DELIVERED_SCRIPT))
	for route: String in ["/v0/production", "/v0/produce", "/v0/complete",
			"/v0/train", "/v0/acquire", "/v0/award", "/v0/xp"]:
		check(not delivered.contains(route),
			"the delivered module names no %s route in code: there is no "
				% route + "endpoint and no client intent to send")
	# No production operation exists on the facade: there is no intent, so
	# there is nothing for a surface to offer.
	var facade: Variant = root.get_node_or_null("GameApi")
	check(facade != null, "GameApi autoload is registered")
	if facade != null:
		var methods: Variant = facade.get_script().get_script_method_list()
		for name: String in ["complete_queue_unit_town", "produce_unit_town",
				"train_unit_town", "collect_unit_town", "award_xp_town",
				"acquire_unit_town", "buy_unit_town", "production_town",
				"produce_queue_town"]:
			check(_method(methods, name) == null,
				"the facade exposes NO %s operation: there is no production "
					% name + "intent to send and nothing to authorise")
		check_eq(BootData.QUEUE_ACTIONS, ["push", "pop"],
			"the v0 endpoint's closed action vocabulary is still exactly the "
				+ "queue push and pop: this line adds no production action")
	# The legacy-v0 implementation names no production route either, so the
	# compatibility service's surface is untouched — the acquired evidence
	# that its test suite stays green unchanged.
	var transport := _code_only(_source("res://scripts/gameapi/legacy_v0_api.gd"))
	for route: String in ["/v0/production", "/v0/produce", "/v0/complete",
			"/v0/train", "/v0/acquire", "/v0/award"]:
		check(not transport.contains(route),
			"the legacy-v0 implementation names no %s route: this line adds NO "
				% route + "endpoint")


# ---------------------------------------------------------------------------
# The committed corpus measurement (design D7)
# ---------------------------------------------------------------------------


## The committed corpus's own measurement: 40 rows, 11 distinct item ids, no
## unit row, no storage, an empty inventory, 40 empty attribute bags, and no
## recorded experience anywhere. Every one of these zeros is **asserted** — a
## fact about the corpus, not evidence that a unit can be produced.
func _check_corpus() -> Dictionary:
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed corpus save is readable JSON")
	if not (save is Dictionary):
		return {}
	var document: Dictionary = save as Dictionary
	var map: Dictionary = document["maps"][CORPUS_MAP_INDEX]
	var rows: Dictionary = map["items"]
	check_eq(rows.size(), EXPECTED_ROWS,
		"the committed corpus places %d rows" % EXPECTED_ROWS)
	var distinct: Array = []
	var unit_rows: Array = []
	var experience_rows: Array = []
	var malformed: Array = []
	for key: Variant in rows.keys():
		# The pinned engine's JSON parser widens every committed number to a
		# float, so the ids are canonicalised to integers before they are
		# looked up in the registry's string-keyed index.
		var row: Variant = _as_int_tree(rows[key])
		var item_id: Variant = (row as Array)[0]
		if not distinct.has(item_id):
			distinct.append(item_id)
		var bag: Variant = (row as Array)[UnitQueue.ATTR_SLOT]
		if not (bag is Dictionary):
			malformed.append(str(key))
			continue
		if (bag as Dictionary).has("xp"):
			experience_rows.append(str(key))
	# A unit row is a row whose committed type is 'u', read through the
	# registry rather than guessed from an id range.
	distinct.sort()
	var types := {}
	for item_id: Variant in distinct:
		var committed_type := _committed_type(item_id)
		if committed_type == "":
			continue
		types[committed_type] = int(types.get(committed_type, 0)) + 1
		if committed_type == "u":
			unit_rows.append(str(item_id))
	check_eq(malformed, [],
		"every committed row carries an object attribute bag")
	check_eq(distinct.size(), EXPECTED_DISTINCT_ITEM_IDS,
		"the committed corpus places %d distinct item ids"
			% EXPECTED_DISTINCT_ITEM_IDS)
	check_eq(unit_rows, [],
		"the committed corpus contains NO unit row: every one of its %d "
			% EXPECTED_ROWS
			+ "distinct ids resolves to a committed building, so no unit "
			+ "instance and no production target exist")
	check_eq(types, {"b": EXPECTED_DISTINCT_ITEM_IDS},
		"every distinct committed id resolves to committed type 'b'")
	check_eq(experience_rows, [],
		"NOT ONE committed row carries attr['xp']: the recorded experience "
			+ "field is absent from all %d rows, which is a corpus measurement "
				% EXPECTED_ROWS
			+ "and never an award")
	# No storage and no inventory: the two client-sent routes that could fill
	# the storage with a unit are the only way a unit could ever be obtained.
	check_eq(map.get("store", null), {},
		"the committed corpus's storage is EMPTY, so no unit can be placed out "
			+ "of it")
	check_eq(document["privateState"].get("inventoryItems", null), {},
		"the committed corpus's inventory is EMPTY")
	check_eq(_bought_units(document), [],
		"the committed corpus records no bought unit")
	return {
		"save": CORPUS_SAVE,
		"rows": rows.size(),
		"distinct_item_ids": distinct,
		"unit_rows": unit_rows,
		"experience_rows": experience_rows,
		"store": (map.get("store", {}) as Dictionary).duplicate(true),
		"inventory": (document["privateState"].get("inventoryItems", {})
			as Dictionary).duplicate(true),
		"bought_units": _bought_units(document),
		"target_key": TARGET_KEY,
		"target_item": TARGET_ITEM,
		"target_name": TARGET_ITEM_NAME,
		"target_training_time": TARGET_TRAINING_TIME,
		"map_level": _as_int(map.get("level", null)),
		"claim": "the committed corpus carries NO unit row, NO storage, and an "
			+ "empty inventory, and every one of its 40 attribute bags is empty, "
			+ "so no production behaviour is exercisable in it — and the reason "
			+ "no fixture was captured is that there is no production behaviour "
			+ "to capture at all, not that the corpus lacked the state",
	}


# ---------------------------------------------------------------------------
# The committed content coverage (design D3)
# ---------------------------------------------------------------------------


## The committed `training_time` distribution, MEASURED from the verified
## registry rather than asserted from prose: a positive value on 130 of the 470
## buildings and on 0 of the 429 units. It is recorded as content and applied
## as no rule.
func _check_content(registry: Variant) -> Dictionary:
	var units := _field_coverage(registry, "units",
		ProductionFlow.TRAINING_FIELD)
	var buildings := _field_coverage(registry, "buildings",
		ProductionFlow.TRAINING_FIELD)
	check_eq(int(units["of"]), EXPECTED_UNITS,
		"the committed package carries %d units" % EXPECTED_UNITS)
	check_eq(int(units["carrying_key"]), EXPECTED_UNITS,
		"EVERY committed unit carries the training_time key: the field is "
			+ "universal, and only its VALUE separates the domains")
	check_eq(int(units["positive"]), EXPECTED_UNITS_WITH_TRAINING_TIME,
		"no committed unit carries a POSITIVE training_time, so the field "
			+ "reads as a duration on buildings only")
	check_eq((units["values"] as Array), ["0"],
		"the units' committed training_time takes exactly ONE value, the zero")
	check_eq(int(units["minimum"]), 0,
		"no unit's committed training_time is positive")
	check_eq(int(buildings["of"]), EXPECTED_BUILDINGS,
		"the committed package carries %d buildings" % EXPECTED_BUILDINGS)
	check_eq(int(buildings["carrying_key"]), EXPECTED_BUILDINGS,
		"EVERY committed building carries the training_time key too")
	check_eq(int(buildings["positive"]), EXPECTED_BUILDINGS_WITH_TRAINING_TIME,
		"exactly %d of the 470 buildings carry a POSITIVE training_time, "
			% EXPECTED_BUILDINGS_WITH_TRAINING_TIME
			+ "which is what the recorded coverage states")
	check_eq((buildings["values"] as Array), ["0", "5"],
		"the whole domain's committed training_time takes EXACTLY TWO values — "
			+ "the zero and the 5 — so the committed 'duration' is a single "
			+ "figure, never a per-building schedule")
	check_eq(int(buildings["maximum"]), TARGET_TRAINING_TIME,
		"the single positive value is the Command Center's %d seconds"
			% TARGET_TRAINING_TIME)
	# The target's own committed training facts, read from the buildings
	# domain, and reported as content through the delivered module.
	var target: Variant = registry.get_entry("buildings",
		str(TARGET_ITEM)).get("entry", null)
	check(target is Dictionary,
		"the Command Center's committed definition resolves")
	if target is Dictionary:
		check_eq(ProductionFlow.committed_training_time(target),
			TARGET_TRAINING_TIME,
			"the Command Center's committed training_time is reported as "
				+ "content: %d" % [TARGET_TRAINING_TIME])
		check_eq(int((target as Dictionary).get("min_level", -1)),
			TARGET_MIN_LEVEL,
			"the Command Center's committed min_level is 1")
		check_eq(str((target as Dictionary).get("group_type", "")),
			TARGET_GROUP_TYPE,
			"the Command Center's committed group_type is COMMAND_CENTER")
		check_eq(str((target as Dictionary).get("name", "")),
			TARGET_ITEM_NAME,
			"the Command Center's committed name resolves")
	# The sibling field, measured the same way: it is the soul mixer's own, and
	# unlike training_time it is genuinely ABSENT from 129 units.
	var sibling_units := _field_coverage(registry, "units",
		ProductionFlow.SIBLING_DURATION_FIELD)
	var sibling_buildings := _field_coverage(registry, "buildings",
		ProductionFlow.SIBLING_DURATION_FIELD)
	check_eq(int(sibling_units["carrying_key"]), 300,
		"the soul-mixer sibling field is carried by 300 of the %d committed "
			% EXPECTED_UNITS + "units")
	check_eq(int(sibling_units["absent_key"]), 129,
		"the other 129 committed units carry NO soul-mixer field at all, so "
			+ "the two duration fields are not interchangeable")
	check_eq(int(sibling_units["minimum"]), 4000,
		"the soul-mixer field's committed minimum is 4000")
	check_eq(int(sibling_buildings["carrying_key"]), 0,
		"NO committed building carries the soul-mixer field: it is the soul "
			+ "mixer's own path, not a general production duration")
	# The two committed ACQUISITION tables, measured. This is where the
	# distinction matters: the recorded "109 / 44 unit references" are
	# DISTINCT unit ids, and the totals are far larger, so both are measured
	# and both are written to the report.
	var packs := _acquisition_table(registry, "offer_packs")
	var darts := _acquisition_table(registry, "darts_items")
	check_eq(int(packs["of"]), EXPECTED_OFFER_PACKS,
		"the committed offer_packs table carries %d packs" % EXPECTED_OFFER_PACKS)
	check_eq(int(packs["distinct_unit_references"]),
		EXPECTED_OFFER_PACK_UNIT_IDS,
		"the committed offer_packs table references %d DISTINCT unit ids"
			% EXPECTED_OFFER_PACK_UNIT_IDS)
	check_eq(int(packs["total_item_references"]),
		EXPECTED_OFFER_PACK_ITEM_REFERENCES,
		"the offer packs make %d item references in total, so the distinct "
			% EXPECTED_OFFER_PACK_ITEM_REFERENCES
			+ "unit-id count is not an occurrence count")
	check_eq(int(packs["distinct_building_references"]),
		EXPECTED_OFFER_PACK_BUILDING_IDS,
		"the offer packs also reference %d committed BUILDINGS, which a "
			% EXPECTED_OFFER_PACK_BUILDING_IDS
			+ "units-only count would silently drop")
	check_eq(packs["unresolved_references"], [],
		"every committed offer-pack reference resolves in the units or "
			+ "buildings domain")
	check_eq(int(darts["of"]), EXPECTED_DARTS_ITEMS,
		"the committed darts_items table carries %d entries"
			% EXPECTED_DARTS_ITEMS)
	check_eq(int(darts["distinct_unit_references"]), EXPECTED_DARTS_UNIT_IDS,
		"the committed darts_items table references %d DISTINCT unit ids"
			% EXPECTED_DARTS_UNIT_IDS)
	check_eq(int(darts["distinct_building_references"]), 0,
		"the darts table references no committed building at all: every one of "
			+ "its %d references is a unit" % int(darts["total_item_references"]))
	check_eq(darts["unresolved_references"], [],
		"every committed darts reference resolves in the units domain")
	return {
		"units": units,
		"buildings": buildings,
		"sibling_units": sibling_units,
		"sibling_buildings": sibling_buildings,
		"offer_packs": packs,
		"darts_items": darts,
	}


# ---------------------------------------------------------------------------
# Purity and containment
# ---------------------------------------------------------------------------


## The delivered module names no node, a clock, a request, or a transport
## token, and preloads exactly the two read-only models it delegates to.
func _check_purity() -> void:
	var code := _code_only(_source(DELIVERED_SCRIPT))
	for needle: String in PURITY_NEEDLES:
		check(not code.contains(needle),
			"the delivered module declares no '%s': it is pure over a bag the "
				% needle + "caller already holds")
	check_eq(_preloads(_source(DELIVERED_SCRIPT)),
		["res://scripts/units/queue_flow.gd", "res://scripts/units/unit_queue.gd"],
		"the delivered module loads exactly the two read-only models it "
			+ "delegates to and reads no content of its own")
	check(_preloads(_source(DELIVERED_SCRIPT)).find(
			"res://scripts/content_registry.gd") == -1,
		"the delivered module reaches the content registry through NO preload: "
			+ "every committed number arrives as a parameter")


## The content package, the committed saves, the committed fixtures, the
## legacy root modules, and the corpus save are byte-identical after the run:
## this line writes evidence under `evidence/unit-production/` and nothing
## else.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, legacy_before: Dictionary,
		save_before: Dictionary) -> void:
	var package_after := Paths.directory_digest(Paths.repo_root().path_join(
		"packages/game-content"))
	var saves_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/saves"))
	var fixtures_after := Paths.directory_digest(Paths.repo_root().path_join(
		"tests/fixtures"))
	var legacy_after := _legacy_digest()
	check_eq(package_after.get("sha256", ""), package_before.get("sha256", ""),
		"content package bytes are unchanged after the run")
	check_eq(package_after.get("files", 0), package_before.get("files", 0),
		"content package file count is unchanged after the run")
	check_eq(saves_after.get("sha256", ""), saves_before.get("sha256", ""),
		"no committed save byte changed during the run")
	check_eq(fixtures_after.get("sha256", ""),
		fixtures_before.get("sha256", ""),
		"no committed fixture byte changed during the run — including the "
			+ "eleven delivered fixture directories, which are only read")
	check_eq(legacy_after.get("sha256", ""), legacy_before.get("sha256", ""),
		"no legacy root module byte changed during the run: they are re-read "
			+ "for the recorded facts and never written")
	var save_after := Paths.file_sha256_checked(Paths.repo_root().path_join(
		CORPUS_SAVE))
	check_eq(save_after.get("sha256", ""), save_before.get("sha256", ""),
		"the committed corpus save is byte-identical after the run")
	check_eq(save_after.get("bytes", 0), save_before.get("bytes", 0),
		"the committed corpus save's byte count is unchanged")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory exists after the run")


# ---------------------------------------------------------------------------
# Evidence report (design D7)
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


## Computes and writes the deterministic `unit-production-report-v1` report.
##
## EVERY fact about the contract comes from `production_flow.gd` — its own
## `ROW_ENTRY`, `TRAINING_REFUSAL`, `ACQUISITION_ROUTES`, `XP_CONTRACT`,
## `DEATH_FINDING`, `ABSENT_HELPERS`, `PROVENANCE`, and `NON_CLAIMS` — every
## legacy fact comes from the measurement `_check_legacy()` performed in this
## same run, and every committed number comes from the registry that was just
## verified or from the committed corpus bytes. Nothing here reads the wall
## clock, resolves a path outside the repository, or sends a request: that is
## what makes the file byte-identical across reruns.
func _write_report(path: String, registry: Variant, loaded: Dictionary,
		legacy: Dictionary, corpus: Dictionary, coverage: Dictionary,
		package_digest: Dictionary, save_digest: Dictionary) -> void:
	var training: Dictionary = ProductionFlow.training_time_record()
	training["distribution_measured"] = {
		"units": coverage.get("units", {}),
		"buildings": coverage.get("buildings", {}),
		"sibling_units": coverage.get("sibling_units", {}),
		"sibling_buildings": coverage.get("sibling_buildings", {}),
	}
	var readout := ProductionFlow.evaluate({"nu": 2, "ts": 1700000000},
		_resolver(registry))
	var report := {
		"schema": "unit-production-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_production.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from the "
				+ "contract's own constants, the same run's legacy "
				+ "measurement, the verified registry, and the committed corpus "
				+ "bytes, and every derived set is sorted before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) "
				+ "plus one trailing newline; every number written is an "
				+ "integer - the pinned engine's integral floats are "
				+ "normalised on the way in, which changes no value - so no "
				+ "float formatting varies between runs",
			"time_dependent_fields": "there are NONE in this line's evidence: "
				+ "no instant is read from a clock, and the one instant the "
				+ "readout renders is a fixed literal the suite passes in",
		},
		"refusal": {
			"production_possible": false,
			"mechanism_implemented": false,
			"reason": "the legacy server has NO production mechanism to "
				+ "reproduce: no command completes a queue, nothing evaluates a "
				+ "queue's elapsed time, and no committed production rule "
				+ "derives a unit from one. This is a RECORDED PROPERTY of the "
				+ "legacy contract, not a missing feature",
			"absent_helpers": (ProductionFlow.ABSENT_HELPERS as Array)
				.duplicate(true),
			"inventory_proof": "the delivered module's whole function "
				+ "inventory is asserted against a pinned list by the suite, "
				+ "so a readiness, remaining-time, progress, duration, "
				+ "completion, production, award, or acquisition helper fails "
				+ "the run wherever it is added",
		},
		"readiness_projection": {
			"delegated_to": "res://scripts/units/queue_flow.gd (never "
				+ "re-derived), so a surface, the suite, and this report cannot "
				+ "disagree about a queue by a key",
			"reports": ["whether a queue is present", "the committed count",
				"the recorded start instant, verbatim"],
			"readiness_value": str(readout.get("readiness", "")),
			"readiness_reason": str(readout.get("readiness_reason", "")),
			"readiness_test_exists": false,
			"completion_available": bool(readout.get("completion_available",
				true)),
			"duration_computed": bool(readout.get("duration_computed", true)),
			"readout": str(readout.get("readout", "")),
		},
		"row_entry_inventory": {
			"count": ProductionFlow.ROW_ENTRY_COUNT,
			"lines": (ProductionFlow.ROW_ENTRY_LINES as Array).duplicate(),
			"classifications": ProductionFlow.classification_vocabulary(),
			"classification_counts": ProductionFlow.classification_counts(),
			"entries": ProductionFlow.row_entry_inventory(),
			"derived_count": ProductionFlow.DERIVED_ROW_ENTRY_COUNT,
			"derived_branches": ProductionFlow.derived_row_entries(),
			"no_derivation": ProductionFlow.no_derivation_finding(),
			"measured_lines": legacy.get("row_sites", []),
			"measured_branches": legacy.get("row_branches", []),
			"measurement_note": "the call sites, their line numbers, and the "
				+ "branch each belongs to are RE-DERIVED from the committed "
				+ "dispatcher by the suite in the same run, so this table "
				+ "cannot drift from the source: a sixth row-placing call site "
				+ "would be reported as an unrecorded gap rather than ignored",
			"dispatcher": {
				"named_branches": _as_int(legacy.get("named_branches", 0)),
				"complete_family": legacy.get("complete_family", []),
				"source": "command.py",
			},
		},
		"training_time": training,
		"training_time_measured": {
			"substring_matches": legacy.get("training_matches", []),
			"modules_searched": (ProductionFlow.TRAINING_SEARCHED_MODULES
				as Array).duplicate(),
			"note": "the measured matches are the two lines the contract "
				+ "records, and every one of them is the DISTINCT field "
				+ "sm_training_time inside the soul-mixer branch, so NO line in "
				+ "any of the six modules reads the committed training time "
				+ "itself: the zero-consumer claim is a measurement, not a "
				+ "promise",
		},
		"experience": ProductionFlow.experience_record(),
		"acquisition": ProductionFlow.acquisition_record(),
		"acquisition_measured": {
			"lines": legacy.get("store_sites", []),
			"branches": legacy.get("store_branches", []),
			"offer_packs": coverage.get("offer_packs", {}),
			"darts_items": coverage.get("darts_items", {}),
			"note": "the six add_store_item call sites and the branch each "
				+ "belongs to are RE-DERIVED from the committed dispatcher by "
				+ "the suite in the same run, so the route table cannot drift "
				+ "from the source and a seventh would be an unrecorded gap. The "
				+ "two committed tables' entry counts, total references, and "
				+ "DISTINCT unit-id counts are measured from the verified "
				+ "registry alongside them, and both figures are reported so "
				+ "the distinct count can never be read as an occurrence count",
		},
		"death_and_resurrection": ProductionFlow.death_record(),
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"map_index": CORPUS_MAP_INDEX,
			"rows": int(corpus.get("rows", 0)),
			"distinct_item_ids": corpus.get("distinct_item_ids", []),
			"unit_rows": corpus.get("unit_rows", []),
			"experience_rows": corpus.get("experience_rows", []),
			"store": corpus.get("store", {}),
			"inventory": corpus.get("inventory", {}),
			"bought_units": corpus.get("bought_units", []),
			"map_level": _as_int(corpus.get("map_level", null)),
			"target": {
				"map_key": _as_int(corpus.get("target_key", 0)),
				"item_id": _as_int(corpus.get("target_item", 0)),
				"item_name": str(corpus.get("target_name", "")),
				"training_time": _as_int(corpus.get("target_training_time", 0)),
			},
			"claim": str(corpus.get("claim", "")),
			"fixture_captured": false,
			"fixture_note": "NO executed-legacy fixture was captured, and the "
				+ "reason is the stronger one: there is NO production behaviour "
				+ "to capture, not merely a corpus that could not exercise it. "
				+ "A fixture here would have to fabricate the state it claims "
				+ "to observe",
		},
		"content": {
			"buildings_file":
				"packages/game-content/normalized/buildings.json",
			"units_file": "packages/game-content/normalized/units.json",
			"duration_field": ProductionFlow.TRAINING_FIELD,
			"units": coverage.get("units", {}),
			"buildings": coverage.get("buildings", {}),
			"sibling_field": ProductionFlow.SIBLING_DURATION_FIELD,
			"sibling_units": coverage.get("sibling_units", {}),
			"sibling_buildings": coverage.get("sibling_buildings", {}),
			"coverage_note": "the coverage above is measured by the suite from "
				+ "the verified registry rather than trusted from prose, and it "
				+ "is recorded as CONTENT and applied as NO rule: no legacy "
				+ "branch reads training_time (design D3)",
			"manifest_outputs_verified": _as_int(loaded.get("files_verified",
				0)),
			"manifest_bytes_verified": _as_int(loaded.get("bytes_verified", 0)),
			"package_files": _as_int(package_digest.get("files", 0)),
			"package_sha256": str(package_digest.get("sha256", "")),
			"enumeration": "ContentRegistry.legacy_ids(domain), the registry's "
				+ "own public accessor over the index it built during its "
				+ "verified load, so every count in this report crosses the "
				+ "same byte-count and digest gate as every other read",
		},
		"no_endpoint": {
			"added": false,
			"route": "none: there is no intent to send and nothing to "
				+ "authorise, so no compatibility operation is added and the "
				+ "compatibility test suite stays green UNCHANGED (design D6)",
			"facade_operations_checked": ["complete_queue_unit_town",
				"produce_unit_town", "train_unit_town", "collect_unit_town",
				"award_xp_town", "acquire_unit_town", "buy_unit_town",
				"production_town"],
			"routes_checked": ["/v0/production", "/v0/produce", "/v0/complete",
				"/v0/train", "/v0/acquire", "/v0/award"],
			"client_supplied_keys_not_authority": [
				"an item id (command.py:55, 245, 353, 633)",
				"a package id (command.py:711, read and never used)",
				"an item list (command.py:714, json.loads of a client array)",
			],
			"later_capability": "enforcing the committed offer_packs and "
				+ "darts_items content is a LATER milestone's work: this line "
				+ "records the routes and enforces nothing",
		},
		"provenance": ProductionFlow.PROVENANCE,
		"non_claims": ProductionFlow.NON_CLAIMS,
	}
	check(not (report["non_claims"] as Array).is_empty(),
		"the report carries the evidence's non-claims")
	for phrase: String in REQUIRED_NON_CLAIMS:
		check(_contains_phrase(report["non_claims"], phrase),
			"the report's non-claims name '%s'" % phrase)
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)"
		% problem)
	if problem == "":
		check(FileAccess.file_exists(path),
			"the report file exists at %s" % path)
		info("report written: %s" % path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## The suite's OWN unit resolver, independent of any surface's, so the module
## is exercised against a resolver the suite controls.
func _resolver(registry: Variant) -> Callable:
	return func(id_text: String) -> Dictionary:
		var resolved: Dictionary = registry.get_entry("units", id_text)
		if not bool(resolved.get("found", false)):
			return {"ok": false, "error": "no committed unit definition for "
				+ "item id %s" % [id_text]}
		return {"ok": true, "name": "resolved unit %s" % id_text}


## One committed item id's type as the registry reports it: `u` for a unit,
## `b` for a building, and "" when neither domain carries the id. A unit row is
## identified by its committed type, never by an id range — the same rule the
## unit-instances line applies.
func _committed_type(item_id: Variant) -> String:
	if _registry == null:
		return ""
	for domain: String in ["units", "buildings"]:
		var resolved: Dictionary = _registry.get_entry(domain, str(item_id))
		if bool(resolved.get("found", false)):
			return str((resolved["entry"] as Dictionary).get("type", ""))
	return ""


## One legacy module's committed lines, or [] when it cannot be read. A caller
## that needs the lines treats an empty result as a failure, never as "no
## occurrences found".
func _legacy_lines(module: String) -> Array:
	var path := Paths.repo_root().path_join(module)
	if not FileAccess.file_exists(path):
		return []
	return (FileAccess.get_file_as_string(path) as String).split("\n")


## A digest over the legacy root modules, so the containment check can prove
## this line only READ them.
func _legacy_digest() -> Dictionary:
	var files: Array = []
	var combined := ""
	for module: String in LEGACY_MODULES:
		var path := Paths.repo_root().path_join(module)
		if not FileAccess.file_exists(path):
			return {"ok": false, "error": "missing legacy module " + module}
		files.append(module)
		combined += (FileAccess.get_file_as_string(path) as String)
	var digest := HashingContext.new()
	digest.start(HashingContext.HASH_SHA256)
	digest.update(combined.to_utf8_buffer())
	return {
		"ok": true,
		"error": "",
		"files": files.size(),
		"sha256": digest.finish().hex_encode(),
	}


## Whether a committed line is a call of one of the recorded helpers, judged
## on the stripped line so an import or a mention never counts as a call site.
func _is_call(line: String, helpers: Array) -> bool:
	var stripped := line.strip_edges()
	for helper: String in helpers:
		if stripped.begins_with(helper):
			return true
	return false


## The branch name a committed line declares, or "" for anything else.
func _branch_of(line: String) -> String:
	var stripped := line.strip_edges()
	for prefix: String in ["if cmd == \"", "elif cmd == \""]:
		if not stripped.begins_with(prefix):
			continue
		var rest := stripped.substr(prefix.length())
		var quote := rest.find("\"")
		if quote <= 0:
			return ""
		return rest.substr(0, quote)
	return ""


## The branch a committed line belongs to: the nearest enclosing `cmd == "..."`
## declaration at or above it. This is what attributes a call site to a branch
## without a parser.
func _enclosing_branch(lines: Array, index: int) -> String:
	for position in range(index, -1, -1):
		var branch := _branch_of(lines[position])
		if branch != "":
			return branch
	return ""


## Every `.gd` source under the given `res://` roots, sorted, so a scan order
## is deterministic.
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
		if entry != "." and entry != "..":
			var full := directory.path_join(entry)
			if handle.current_is_dir():
				_collect_gd(full, out)
			elif str(entry).ends_with(".gd"):
				out.append(full)
		entry = handle.get_next()
	handle.list_dir_end()


## One committed field's coverage across a whole domain, measured from the
## verified registry. `carrying_key` and `positive` are reported SEPARATELY and
## never conflated: the committed `training_time` is carried by every item and
## is positive on only 130 of the 470 buildings, so a single "with field" count
## would misreport the content as absent from 340 buildings.
func _field_coverage(registry: Variant, domain: String,
		field: String) -> Dictionary:
	var ids: Array = registry.legacy_ids(domain).get("ids", [])
	var carrying := 0
	var positive := 0
	var value_set := {}
	var numbers: Array = []
	for id_text: Variant in ids:
		var entry: Variant = registry.get_entry(domain,
			str(id_text)).get("entry", null)
		if not (entry is Dictionary):
			continue
		if not (entry as Dictionary).has(field):
			continue
		carrying += 1
		# The value is canonicalised to the integer it denotes before it is
		# keyed, because the pinned engine's JSON parser widens every
		# committed number to a float and the report promises integers.
		value_set[str(_as_int((entry as Dictionary)[field]))] = true
		var number: Variant = BootData._parse_int((entry as Dictionary)[field])
		if number != null and int(number) > 0:
			positive += 1
			numbers.append(int(number))
	numbers.sort()
	var seen: Array = value_set.keys()
	seen.sort()
	return {
		"domain": domain,
		"field": field,
		"of": ids.size(),
		"carrying_key": carrying,
		"positive": positive,
		"absent_key": ids.size() - carrying,
		"distinct_values": seen.size(),
		"values": seen,
		"minimum": numbers[0] if not numbers.is_empty() else 0,
		"maximum": numbers[numbers.size() - 1] if not numbers.is_empty() else 0,
	}


## One committed acquisition table, measured from the verified registry: how
## many entries it carries, how many item references those entries make in
## total, and how many DISTINCT ids of each kind they resolve to. The distinct
## counts and the occurrence total are reported separately because the
## committed investigation's "109 / 44 unit references" is the **distinct
## figure**, while the occurrence totals are several times larger — and because
## the offer packs also reference seven committed **buildings**, which a
## units-only count would silently drop.
func _acquisition_table(registry: Variant, domain: String) -> Dictionary:
	var ids: Array = registry.legacy_ids(domain).get("ids", [])
	var total := 0
	var unit_occurrences := 0
	var unit_ids := {}
	var building_ids := {}
	var unresolved: Array = []
	for id_text: Variant in ids:
		var entry: Variant = registry.get_entry(domain,
			str(id_text)).get("entry", null)
		if not (entry is Dictionary):
			continue
		var references: Array = []
		var listed: Variant = (entry as Dictionary).get("item_refs", null)
		if listed is Array:
			references.append_array(listed as Array)
		var extra: Variant = (entry as Dictionary).get("extra_ref", null)
		if extra != null and str(extra) != "":
			references.append(extra)
		for reference: Variant in references:
			total += 1
			var text := str(reference)
			if bool(registry.get_entry("units", text).get("found", false)):
				unit_occurrences += 1
				unit_ids[text] = true
			elif bool(registry.get_entry("buildings", text).get("found", false)):
				building_ids[text] = true
			elif not unresolved.has(text):
				unresolved.append(text)
	unresolved.sort()
	return {
		"domain": domain,
		"of": ids.size(),
		"total_item_references": total,
		"unit_occurrences": unit_occurrences,
		"distinct_unit_references": unit_ids.size(),
		"distinct_building_references": building_ids.size(),
		"unresolved_references": unresolved,
	}


## One entry of the facade's own method list, or null.
func _method(methods: Variant, name: String) -> Variant:
	for entry: Variant in methods as Array:
		if not (entry is Dictionary):
			continue
		if str((entry as Dictionary).get("name", "")) == name:
			return entry
	return null


## Whether a list of sentences contains the given phrase, as a substring.
func _contains_phrase(lines: Variant, phrase: String) -> bool:
	for line: Variant in lines as Array:
		if str(line).contains(phrase):
			return true
	return false


## A source's DECLARATIONS: comment lines are dropped and string-literal
## content is blanked, so a prose mention or a recorded non-claim string can
## never be mistaken for code.
func _code_only(body: String) -> String:
	var lines := body.split("\n")
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


## The public and private function names a module declares, sorted, from its
## own source: the check that a readiness, duration, award, or acquisition
## helper cannot hide.
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


## Every script a module loads, in committed order, read from its own `preload`
## declarations: the check that neither delivered module reaches content or the
## transport behind the contract's back.
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


## The committed bought-units bookkeeping, as integers.
func _bought_units(document: Dictionary) -> Array:
	var list: Array = (document["privateState"] as Dictionary).get(
		"boughtUnits", [])
	return _as_int_tree(list) as Array


## The committed numbers of any JSON value, normalised to integers, so a
## comparison against a literal holds without weakening the value.
func _as_int_tree(value: Variant) -> Variant:
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_as_int_tree(entry))
		return list
	if value is Dictionary:
		var bag := {}
		for key: Variant in (value as Dictionary).keys():
			bag[key] = _as_int_tree((value as Dictionary)[key])
		return bag
	return value


## A committed number as the exact integer it denotes. The pinned engine's JSON
## parser yields integral floats; every number the report writes goes through
## here, so the report carries integers and its determinism does not depend on a
## float's serialization.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


func _working_saves_exist() -> bool:
	return DirAccess.dir_exists_absolute(
		Paths.repo_root().path_join("saves"))


func _source(res_path: String) -> String:
	return FileAccess.get_file_as_string(res_path)


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
