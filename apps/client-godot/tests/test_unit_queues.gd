extends "res://tests/test_base.gd"
## Unit-queues suite (OpenSpec `godot-unit-queues` "A queue is a count, a start
## instant, and an optional queued unit id" / "No elapsed-time evaluation and no
## completion" / "The three queue commands and their recorded lack of validation"
## / "The atom-fusion speedup is recorded without a cost or a timer" / "A queued
## unit id resolves through content, and an unresolvable one is reported" / "An
## executed-legacy fixture for the push and pop pair" / "Queue intents carry no
## cost, duration, or outcome" / "Unit-queue evidence and claim limits", design
## D1-D8).
##
## Checks:
##   keys        the three committed queue keys, the slot they live in, and the
##               three ways a queued unit id is reported;
##   projection  a full queue, a count-only queue, a count+instant queue, an
##               absent queue that is absent rather than zero, a malformed value
##               per key, a bag that is not a bag, and read-only independence
##               from the save;
##   teardown    the recorded three-key teardown, and the absence rule that
##               keeps a torn-down queue distinguishable from a zeroed one;
##   commands    the three legacy commands' exact effects and arguments, with
##               the atom-fusion push recorded and deliberately not offered;
##   validation  the recorded ABSENCE of validation, and that no producer,
##               duration, level, or **count bound** is invented on top of it;
##   readiness   the recorded absence of elapsed-time evaluation and completion,
##               asserted against both modules' whole function inventories and
##               against the named `NON_READINESS` list;
##   speedup     the recorded `soulmixer_speedup` contract verbatim, its
##               two-key precondition, and a **refusal** wherever the legacy
##               branch would raise — with no cost computed anywhere;
##   resolution  a resolving queued id, an unresolvable one reported with its
##               value intact, an absent one, and nothing substituted;
##   flow        the pure flow's evaluation, its presence predicates, its
##               recorded inert pop, and its display text — over crafted bags
##               and the committed corpus, with no node, clock, or request;
##   fixture     the committed executed-legacy push and pop: the recorded
##               before/after attribute bags, all 40 rows, every stored resource,
##               the storage, the private state, the player info, and the
##               manifest's own statements that no completion was captured and
##               that no completion command exists;
##   corpus      the committed fresh-player corpus measurement: 40 rows, key 1 is
##               id 26 Command Center with an EMPTY bag, and therefore **zero**
##               carried queue keys anywhere;
##   content     the committed coverage of `sm_training_time` — 300 of 429 units,
##               0 of 470 buildings, 84 distinct values from 4000 — measured
##               from the verified registry, never asserted from prose;
##   intents     the facade's two queue operations take EXACTLY the save identity
##               and the target key, so no channel exists through which a client
##               could send a count, cost, duration, or readiness, and both
##               implementations implement them;
##   purity      neither delivered module names a node, a clock, a request, or a
##               transport token;
##   containment the content package, the committed saves, and the committed
##               fixtures are byte-identical after the run.
##
## Hermetic: no process, no server, no socket, and no request is issued. A queue
## is read from a save already in hand and its queued unit is resolved from the
## already-loaded content registry, so no GameApi operation is involved except in
## the `intents` inventory read. The fault scenarios build **copies** under
## `.godot/`, never a source file. Runs headless as part of `verify-boot.ps1`.
##
## `--scenario=live-queue` is the `queue-live` phase: one push and one pop
## through the real Compatibility endpoint over a disposable corpus, asserting
## the typed response, its two-part post-state proof, and that no resource moved.
## `--report=<path>` writes the deterministic `unit-queues-report-v1` evidence
## report; the bare `--report` flag defaults to `evidence/unit-queues/report.json`.
## Every table is derived from the live model, the verified registry, and the
## committed bytes, so the report cannot drift from the code it documents.

const UnitQueue = preload("res://scripts/units/unit_queue.gd")
const QueueFlow = preload("res://scripts/units/queue_flow.gd")
const UnitDefinition = preload("res://scripts/units/unit_definition.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

const SCRATCH := ".godot/verify/unit-queues"
## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-queues/report.json"
## The committed corpus this line measures.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const CORPUS_MAP_INDEX := 0
## The committed fixture directory, its manifest, and the two steps.
const FIXTURE_DIR := "tests/fixtures/godot-unit-queues"
const FIXTURE_MANIFEST := FIXTURE_DIR + "/capture-manifest.json"
const FIXTURE_PUSH_DIR := FIXTURE_DIR + "/steps/command_push_queue_unit"
const FIXTURE_POP_DIR := FIXTURE_DIR + "/steps/command_pop_queue_unit"
## The committed corpus's own real placed training producer: **id 26, Command
## Center, at map key 1**, `training_time` 5, `min_level` 1, with an EMPTY bag.
const TARGET_KEY := "1"
const TARGET_MAP_KEY := 1
const TARGET_ITEM := 26
const TARGET_ITEM_NAME := "Command Center"
const TARGET_TRAINING_TIME := 5
const TARGET_MIN_LEVEL := 1
const TARGET_GROUP_TYPE := "COMMAND_CENTER"
const TARGET_ROW := [TARGET_ITEM, 51, 41, 0, 0, [], {}, 1]
const EXPECTED_ROWS := 40
## The instant the executed push stamped. The legacy branch stamps the wall
## clock, so the committed capture is the only authority for this value and it is
## **READ from the fixture** (see `fixture_stamp`), never pinned as a literal: a
## re-capture must move every assertion here with it rather than silently
## disagreeing. The relationship the suite asserts is the stable one — the count
## is exactly 1, the pop's before state IS the push's after state, and the
## teardown returns the bag to empty.
var fixture_stamp := 0
## The committed corpus's seven stored balances, which both steps leave
## byte-identical.
const CORPUS_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}
## A committed unit id that resolves through the registry, and one that does not.
const RESOLVING_UNIT_ID := "1019"
const UNRESOLVABLE_UNIT_ID := "9999999"
## The committed coverage of `sm_training_time` (task 1.3): measured from the
## registry by this suite rather than trusted from prose.
const EXPECTED_UNITS := 429
const EXPECTED_UNITS_WITH_SPEEDUP_FIELD := 300
const EXPECTED_BUILDINGS := 470
const EXPECTED_BUILDINGS_WITH_SPEEDUP_FIELD := 0
const EXPECTED_SPEEDUP_DISTINCT_VALUES := 84
const EXPECTED_SPEEDUP_MINIMUM := 4000
## Tokens a read-only projection must not carry: a node, a clock, a request, or a
## transport. The transport needles are spelled as fragments because the
## project-scope suite scans every source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]
## The whole function inventory of `unit_queue.gd`, public and private,
## including the inner `Queue` class's readers. Compared as a sorted set, so a
## readiness helper, a cost helper, or any behaviour added anywhere in the file
## shows up here and fails the check (design D1/D2/D5/D6).
const EXPECTED_QUEUE_MODULE_METHODS := [
	"_integer", "_reject", "_resolve_queued_unit", "_type_name",
	"command_contract", "count", "fields", "has_count", "has_queued_unit_id",
	"has_start_instant", "keys", "present", "project", "queue_keys",
	"queued_unit_id", "queued_unit_name", "queued_unit_resolution",
	"queued_unit_resolution_error", "speedup_precondition", "start_instant",
	"teardown",
]
## The whole function inventory of `queue_flow.gd`. Same purpose: the absence of
## a readiness, remaining-time, progress, or completion helper is a structural
## property, so it is asserted as an inventory rather than as a prose promise.
const EXPECTED_FLOW_MODULE_METHODS := [
	"_count_text", "_evaluation_reject", "_number_text", "_queued_unit_text",
	"command_record", "confirm_text", "evaluate", "offers_pop", "offers_push",
	"pop_refusal_text", "readout_text", "speedup_record", "speedup_text",
]
## Names a readiness, remaining-time, progress, or completion helper would take.
## The inventory checks above are the real gate; this list is what the suite also
## asserts is absent **by name**, so a rename cannot smuggle one past the
## inventory and a leftover in the recorded list fails visibly.
const FORBIDDEN_HELPERS := [
	"is_complete", "remaining", "progress_ratio", "ready_at", "complete",
	"is_ready", "time_left", "elapsed", "completion", "cost", "price",
	"speedup_cost", "purchase_speedup",
]
## Tokens that would mean a cost, a timer, a completion, or a produced unit is
## implemented.
const BEHAVIOUR_NEEDLES := [
	"push_queue_unit2", "soulmixer_speedup(", "sm_training_time -",
	"training_time -", "ceil(", "Time.", "create_unit", "spawn_unit",
	"train_unit", "produce_unit",
]
## The non-claim phrases the delta's evidence requirement names.
const REQUIRED_NON_CLAIMS := [
	"no Flash",
	"NO COMPLETION AND NO ELAPSED-TIME EVALUATION ARE IMPLEMENTED",
	"NO COST AND NO TIMER ARE IMPLEMENTED",
	"NO COUNT BOUND IS IMPLEMENTED",
	"NO UNIT IS PRODUCED, TRAINED, OR PLACED",
	"no training duration semantics are claimed",
	"NO ACQUISITION IS CLAIMED",
	"PUSH AND A POP ONLY",
	"no pixel-parity oracle exists",
]
## The queue actions the v0 endpoint's closed vocabulary carries, and the legacy
## command each derives.
## The v0 endpoint action vocabulary the closed set is compared against, pinned
## so a widening of `BootData.QUEUE_ACTIONS` fails here rather than silently
## becoming the asserted set.
const EXPECTED_ACTIONS := ["pop", "push"]
## The endpoint override the live phase is invoked with.
const ARG_ENDPOINT := "--gameapi-endpoint="
## The two delivered modules' own resource paths, read by the suite for its
## function-inventory and purity checks — read reflectively so a rename or a new
## helper fails the SUITE rather than a comment.
const UNIT_QUEUE_SOURCE := "res://scripts/units/unit_queue.gd"
const QUEUE_FLOW_SOURCE := "res://scripts/units/queue_flow.gd"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-queue":
		await _check_live_queue()
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
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

	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"the committed package loads (error: %s)"
			% str(content.get("error", "")))
	if not bool(content.get("ok", false)):
		return
	fixture_stamp = _recorded_stamp()
	if fixture_stamp <= 0:
		return

	_check_keys()
	_check_projection(registry)
	_check_teardown(registry)
	_check_commands()
	_check_validation(registry)
	_check_readiness()
	_check_speedup()
	_check_resolution(registry)
	_check_flow(registry)
	var corpus := _check_corpus()
	var fixture := _check_fixture()
	var coverage := _check_content(registry)
	_check_intents()
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before,
		save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, content, corpus, fixture, coverage,
			package_before, save_before)
	info("unit queues: corpus rows %d, keys carried %d, fixture stamp %d"
		% [EXPECTED_ROWS, (corpus.get("carried_keys", []) as Array).size(),
			fixture_stamp])


# ---------------------------------------------------------------------------
# The three committed keys (design D1)
# ---------------------------------------------------------------------------


## The three committed queue keys, the slot they live in, and the three ways a
## queued unit id is reported. Read from the model's own constants so a report
## cannot describe a key set the code no longer accepts.
func _check_keys() -> void:
	check_eq(UnitQueue.KEY_COUNT, "nu",
		"the queue count is the committed key nu")
	check_eq(UnitQueue.KEY_START, "ts",
		"the queue start instant is the committed key ts")
	check_eq(UnitQueue.KEY_UNIT_ID, "ui",
		"the optional queued unit id is the committed key ui")
	check_eq(UnitQueue.queue_keys(), ["nu", "ts", "ui"],
		"the queue occupies exactly the three committed keys, in committed order")
	check_eq(UnitQueue.ATTR_SLOT, 6,
		"a queue lives in the placed row's seventh slot, the attr bag")
	check_eq(UnitQueue.UNIT_DOMAIN, "units",
		"a queued unit id resolves through the content units domain")
	var resolutions := _sorted_array([UnitQueue.RESOLUTION_ABSENT,
		UnitQueue.RESOLUTION_RESOLVED, UnitQueue.RESOLUTION_UNRESOLVABLE])
	check_eq(resolutions, ["absent", "resolved", "unresolvable"],
		"a queued id is reported resolved, unresolvable, or absent — and there "
			+ "is deliberately no fourth state in which it is dropped")
	var keys := UnitQueue.queue_keys()
	(keys as Array).append("tampered")
	check_eq(UnitQueue.queue_keys(), ["nu", "ts", "ui"],
		"the key list is handed out as a fresh copy, never the constant itself")


# ---------------------------------------------------------------------------
# The projection (design D1)
# ---------------------------------------------------------------------------


## Every queue shape the contract must report, and every shape it must refuse.
## Nothing is scaled, rounded, defaulted, or coerced, and an absent queue is
## absent rather than a zero count with a zero instant.
func _check_projection(registry: Variant) -> void:
	var resolver := _resolver(registry)
	# A full queue: all three committed keys, verbatim.
	var full := UnitQueue.project({"nu": 3, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, resolver)
	check(bool(full.get("ok", false)),
		"a bag carrying all three queue keys projects (error: %s)"
			% str(full.get("error", "")))
	if bool(full.get("ok", false)):
		var queue: Variant = full.get("queue", null)
		check_eq(queue.count(), 3, "the count is reported verbatim, unscaled")
		check_eq(queue.has_count(), true, "the bag carried the count key")
		check_eq(queue.start_instant(), fixture_stamp,
			"the start instant is reported verbatim, unrounded")
		check_eq(queue.has_start_instant(), true,
			"the bag carried the start-instant key")
		check_eq(queue.queued_unit_id(), RESOLVING_UNIT_ID,
			"the queued unit id is reported verbatim, never coerced")
		check_eq(queue.keys(), ["nu", "ts", "ui"],
			"the committed key names the bag carries are reported in order")
		check_eq(queue.teardown(), UnitQueue.TEARDOWN,
			"the teardown rule is carried by every reported queue")
	# A count-only queue: `nu` present, the other two absent.
	var count_only := UnitQueue.project({"nu": 7}, resolver)
	if bool(count_only.get("ok", false)):
		var queue: Variant = count_only.get("queue", null)
		check_eq(queue.present(), true,
			"a bag carrying only the count still reports a queue")
		check_eq(queue.count(), 7, "the count-only queue's count is verbatim")
		check_eq(queue.has_start_instant(), false,
			"a count-only queue reports the start instant as ABSENT, not zero")
		check_eq(queue.start_instant(), null,
			"the absent instant is null, which is what a zero cannot say")
		check_eq(queue.has_queued_unit_id(), false,
			"a count-only queue reports no queued unit id")
		check_eq(queue.queued_unit_resolution(), UnitQueue.RESOLUTION_ABSENT,
			"a bag with no ui resolves as absent")
	else:
		fail("a count-only bag projects: %s" % str(count_only.get("error", "")))
	# A count + instant queue: the shape the executed push produced.
	var pushed := UnitQueue.project({"nu": 1, "ts": fixture_stamp}, resolver)
	if bool(pushed.get("ok", false)):
		var queue: Variant = pushed.get("queue", null)
		check_eq(queue.present(), true, "the executed push's bag reports a queue")
		check_eq(queue.count(), 1, "the executed push's committed count is 1")
		check_eq(queue.start_instant(), fixture_stamp,
			"the executed push's committed instant is reported verbatim")
		check_eq(queue.keys(), ["nu", "ts"],
			"the push's bag carries exactly nu and ts, never a ui")
	else:
		fail("the executed push's bag projects: %s"
			% str(pushed.get("error", "")))
	# An ABSENT queue: absent, never a zero count with a zero instant.
	var absent := UnitQueue.project({}, resolver)
	check(bool(absent.get("ok", false)),
		"an empty bag projects as an absent queue rather than an error")
	if bool(absent.get("ok", false)):
		var queue: Variant = absent.get("queue", null)
		check_eq(queue.present(), false, "an empty bag reports NO queue")
		check_eq(queue.count(), null,
			"an absent queue has a NULL count, never a committed zero")
		check_eq(queue.start_instant(), null,
			"an absent queue has a NULL instant, never a committed zero")
		check_eq(queue.has_count(), false,
			"an absent queue reports the count key as not carried")
		check_eq(queue.has_start_instant(), false,
			"an absent queue reports the instant key as not carried")
		check_eq(queue.keys(), [],
			"an absent queue carries no committed key")
	# Malformed values, one per key, each refused with the key named.
	var bad_counts := [1.5, "3", true, null]
	for value: Variant in bad_counts:
		var refused := UnitQueue.project({"nu": value}, resolver)
		check(not bool(refused.get("ok", false))
				and str(refused.get("reason", "")) == UnitQueue
					.REASON_INVALID_COUNT,
			"the committed count %s is refused with its own named reason"
				% [value])
		check(str(refused.get("error", "")).contains(UnitQueue.KEY_COUNT),
			"the refused count names the offending key")
		check(refused.get("queue", null) == null,
			"a refused count produces NO queue at all")
	var negative := UnitQueue.project({"nu": -1}, resolver)
	check(not bool(negative.get("ok", false)),
		"a negative count is refused rather than read as an empty queue")
	for value: Variant in [1.5, "1700000000", []]:
		var refused := UnitQueue.project({"ts": value}, resolver)
		check(not bool(refused.get("ok", false))
				and str(refused.get("reason", "")) == UnitQueue
					.REASON_INVALID_START,
			"the committed start instant %s is refused with its own named reason"
				% [value])
	# A bag that is not a bag is a different thing from an empty one.
	for value: Variant in [null, [], "nu", 7]:
		var refused := UnitQueue.project(value, resolver)
		check(not bool(refused.get("ok", false))
				and str(refused.get("reason", "")) == UnitQueue
					.REASON_INVALID_BAG,
			"the attribute bag %s is refused: an empty bag and a missing bag "
				% [value]
				+ "mean the same thing, but a bag that is not a bag does not")
	# An integral float is the documented transport tolerance, and a numeric
	# string is not.
	var transported := UnitQueue.project({"nu": 3.0, "ts": float(
		fixture_stamp)}, resolver)
	check(bool(transported.get("ok", false)),
		"an integral float count and instant are accepted: the pinned engine's "
			+ "JSON parser widens every committed number")
	if bool(transported.get("ok", false)):
		check_eq((transported.get("queue", null) as Variant).count(), 3,
			"the integral float reads as the exact integer it denotes")
	# Read-only: projecting reads the bag and writes nothing back into it, and
	# the handed-out record is a copy.
	var source := {"nu": 2, "ts": fixture_stamp, "nc": 5}
	var snapshot := source.duplicate(true)
	var projected := UnitQueue.project(source, resolver)
	if bool(projected.get("ok", false)):
		var queue: Variant = projected.get("queue", null)
		var fields: Dictionary = queue.fields()
		(fields["keys"] as Array).append("tampered")
		fields["count"] = 99
		check_eq(source, snapshot,
			"projecting a queue writes nothing back into the save's bag")
		check_eq(queue.count(), 2,
			"mutating the handed-out record cannot change the reported queue")
		check_eq(queue.keys(), ["nu", "ts"],
			"mutating the handed-out key list cannot change the reported queue")
		var again: Dictionary = queue.fields()
		check_eq(again["count"], 2,
			"the record is a fresh copy on every call, never a live view")
	check_eq((source as Dictionary).get("nc"), 5,
		"an unrelated committed bag key is neither read nor written by a queue "
			+ "projection")
	# A count of zero IS reported verbatim when a save carries it — it is a
	# crafted input, because the legacy teardown deletes the key at zero, and
	# the point is that the projection reports what it is given.
	var zero := UnitQueue.project({"nu": 0, "ts": fixture_stamp}, resolver)
	if bool(zero.get("ok", false)):
		check_eq((zero.get("queue", null) as Variant).count(), 0,
			"a committed count of zero is reported as zero, not as absent: the "
				+ "projection reports the bag, it does not second-guess it")


# ---------------------------------------------------------------------------
# The recorded three-key teardown (design D1/D3)
# ---------------------------------------------------------------------------


## The teardown rule is RECORDED, and an absent queue stays distinguishable from
## a zeroed one — which is the only reason the rule matters to a reader.
func _check_teardown(registry: Variant) -> void:
	var teardown := UnitQueue.TEARDOWN
	for key: String in ["nu", "ts", "ui"]:
		check(teardown.contains(key),
			"the recorded teardown names the %s key" % key)
	check(teardown.contains("TOGETHER"),
		"the recorded teardown says the three keys die TOGETHER")
	check(teardown.contains("engine.py:198-204"),
		"the recorded teardown names the committed source line that deletes them")
	check(teardown.contains("never carries a partial queue teardown"),
		"the recorded teardown states that no save holds a partial one")
	var resolver := _resolver(registry)
	var torn := UnitQueue.project({}, resolver)
	if bool(torn.get("ok", false)):
		var queue: Variant = torn.get("queue", null)
		check_eq(queue.teardown(), UnitQueue.TEARDOWN,
			"the teardown rule travels with the projection, not only with this "
				+ "constant")
		check_eq(queue.present(), false,
			"the executed pop's result — an empty bag — projects as ABSENT")
		check(not (queue.count() == 0 and queue.start_instant() == 0),
			"an absent queue is never rendered as a zero count with a zero "
				+ "instant, which the teardown makes unreachable in a save")


# ---------------------------------------------------------------------------
# The three commands and the recorded lack of validation (design D5)
# ---------------------------------------------------------------------------


## The three legacy commands' exact effects and arguments, and the atom-fusion
## push recorded and deliberately NOT offered.
func _check_commands() -> void:
	var contract := UnitQueue.command_contract()
	check_eq(contract.size(), 3,
		"exactly three legacy queue commands touch a queue")
	var by_name := {}
	for entry: Dictionary in contract:
		by_name[str(entry["command"])] = entry
		check(str(entry["source"]).begins_with("command.py:"),
			"the %s record names the committed dispatcher line that fixes it"
				% str(entry["command"]))
		check(str(entry["validation"]).begins_with("none"),
			"the %s record states its ABSENCE of validation as content"
				% str(entry["command"]))
	for name: String in [UnitQueue.PUSH_COMMAND, UnitQueue.POP_COMMAND]:
		check(by_name.has(name), "the contract records %s" % name)
	if by_name.has(UnitQueue.PUSH_COMMAND):
		var push: Dictionary = by_name[UnitQueue.PUSH_COMMAND]
		check_eq((push["args"] as Array), ["map index"],
			"push_queue_unit takes ONLY the map index")
		check(str(push["effect"]).contains("(nu + 1)"),
			"the push record states the increment and the absent case")
		check(str(push["effect"]).contains("timestamp_now"),
			"the push record states that the start instant is stamped")
		check_eq(bool(push["offered"]), true,
			"the push is offered by a guarded intent")
	if by_name.has(UnitQueue.POP_COMMAND):
		var pop: Dictionary = by_name[UnitQueue.POP_COMMAND]
		check_eq((pop["args"] as Array), ["map index"],
			"pop_queue_unit takes ONLY the map index")
		check(str(pop["effect"]).contains("ABSENT"),
			"the pop record states legacy's inert no-op on an absent count")
		check(str(pop["effect"]).contains("DELETES nu, ts"),
			"the pop record states the three-key teardown")
		check_eq(bool(pop["offered"]), true,
			"the pop is offered by a guarded intent")
	check(by_name.has(UnitQueue.ATOM_FUSION_COMMAND),
		"the atom-fusion push is RECORDED even though it is not offered")
	if by_name.has(UnitQueue.ATOM_FUSION_COMMAND):
		var fusion: Dictionary = by_name[UnitQueue.ATOM_FUSION_COMMAND]
		check_eq(bool(fusion["offered"]), false,
			"the atom-fusion push is deliberately NOT offered (design D7)")
		check_eq((fusion["args"] as Array), ["map index", "unit_id"],
			"the atom-fusion push is the one variant carrying a second argument")
		check(str(fusion.get("why_not_offered", "")).contains("CLIENT-SUPPLIED"),
			"the decision to withhold it names the client-supplied id as the "
				+ "reason")
	var record: Dictionary = QueueFlow.command_record()
	check_eq(record["commands"], contract,
		"the flow's command record is the model's own table, not a restatement")
	check_eq(record["keys"], ["nu", "ts", "ui"],
		"the flow reports the same three committed keys")
	check_eq(record["attr_slot"], 6,
		"the flow reports the same attribute slot")
	check_eq(record["teardown"], UnitQueue.TEARDOWN,
		"the flow reports the same recorded teardown")
	check_eq(BootData.QUEUE_ACTIONS, ["push", "pop"],
		"the v0 endpoint's closed action vocabulary is exactly the push and the "
			+ "pop")
	check_eq(EXPECTED_ACTIONS, ["pop", "push"],
		"the suite pins the two actions as the closed set it asserts")


## The recorded ABSENCE of validation is present as content, and nothing on top
## of it is invented: no producer check, no duration, no level, and above all
## **no bound on the count**.
func _check_validation(registry: Variant) -> void:
	var record := UnitQueue.NO_VALIDATION
	for phrase: String in ["NO VALIDATION IS PERFORMED", "training producer",
			"min_level", "do not cap nu", "NOT permission", "design D5"]:
		check(record.contains(phrase),
			"the recorded absence of validation names '%s'" % phrase)
	check(UnitQueue.NO_ELAPSED_TIME.contains("NO ELAPSED-TIME EVALUATION"),
		"the recorded absence of elapsed-time evaluation is present as content")
	check(UnitQueue.NO_ELAPSED_TIME.contains("complete_collection"),
		"the recorded completion absence names the whole complete_* family")
	# No count bound is applied to ANY count, however large: the engine sets none,
	# so an invented cap would be a rule the legacy server does not have.
	var resolver := _resolver(registry)
	for count: int in [0, 1, 2, 5, 64, 9999, 1000000]:
		var projected := UnitQueue.project({"nu": count, "ts": fixture_stamp},
			resolver)
		check(bool(projected.get("ok", false)),
			"a queue of %d projects: no maximum count is applied" % count)
		if bool(projected.get("ok", false)):
			check_eq((projected.get("queue", null) as Variant).count(), count,
				"a queue of %d is reported verbatim, uncapped and unrefused"
					% count)
	# No producer check either: a bag on a row that is NOT a training producer
	# projects exactly the same, because the projection reads a bag and never a
	# definition.
	var any_row := UnitQueue.project({"nu": 1, "ts": fixture_stamp}, resolver)
	check(bool(any_row.get("ok", false)),
		"a queue projects without any producer, duration, or level check")
	# No duration is read: neither module's inventory contains a duration or
	# training-time helper, and the projection reads a bag and never a
	# definition.
	var declared: Array = _methods(_source(UNIT_QUEUE_SOURCE))
	declared.append_array(_methods(_source(QUEUE_FLOW_SOURCE)))
	for helper: String in ["duration", "training_time", "sm_training_time"]:
		check(not declared.has(helper),
			"neither module declares a '%s' helper: no queue branch reads a "
				% helper + "duration field, so none may be read here either")


# ---------------------------------------------------------------------------
# The recorded absence of readiness, remaining time, and completion (D1/D2)
# ---------------------------------------------------------------------------


## The absence of elapsed-time evaluation and completion is **structural**: both
## delivered modules' whole function inventories are compared against a pinned
## list, so a readiness, remaining-time, progress, or completion helper fails the
## suite wherever it is added.
func _check_readiness() -> void:
	var queue_methods := _methods(_source(UNIT_QUEUE_SOURCE))
	var flow_methods := _methods(_source(QUEUE_FLOW_SOURCE))
	check_eq(queue_methods, EXPECTED_QUEUE_MODULE_METHODS,
		"unit_queue.gd declares EXACTLY the projected readers and the recorded "
			+ "contract accessors — no readiness, remaining-time, progress, or "
			+ "completion helper")
	check_eq(flow_methods, EXPECTED_FLOW_MODULE_METHODS,
		"queue_flow.gd declares EXACTLY the pure evaluation helpers — no "
			+ "readiness, remaining-time, progress, or completion helper")
	var declared: Array = queue_methods.duplicate()
	declared.append_array(flow_methods)
	for helper: String in FORBIDDEN_HELPERS:
		check(not declared.has(helper),
			"neither module declares a '%s' helper: the legacy server has no "
				% helper + "such rule to reproduce")
	var non_readiness: Array = QueueFlow.NON_READINESS
	check_eq(non_readiness.size(), 5,
		"the recorded NON_READINESS list names every absent helper")
	var named := []
	for entry: Dictionary in non_readiness:
		named.append(str(entry["helper"]))
		check(not str(entry["absent_because"]).is_empty(),
			"the recorded absence of '%s' states why it is absent"
				% str(entry["helper"]))
	check_eq(named, ["is_complete", "remaining", "progress_ratio", "ready_at",
			"complete"],
		"the recorded absences are the five the delta names, in order")
	for helper: String in named:
		check(FORBIDDEN_HELPERS.has(helper),
			"the recorded absence '%s' is also asserted absent by name" % helper)
	# The recorded contract text names every established fact the delta requires.
	var elapsed := UnitQueue.NO_ELAPSED_TIME
	for phrase: String in ["WRITE", "DELETION", "63 named branches",
			"complete_tutorial", "NO command completes a queue",
			"recorded property of the legacy contract"]:
		check(elapsed.contains(phrase),
			"the recorded elapsed-time absence names '%s'" % phrase)


# ---------------------------------------------------------------------------
# The recorded speedup contract (design D6)
# ---------------------------------------------------------------------------


## The `soulmixer_speedup` contract is recorded VERBATIM and implemented not at
## all: every established fact is present, the two-key precondition refuses
## wherever the legacy branch would raise `KeyError`, and **no cost is computed
## anywhere**.
func _check_speedup() -> void:
	var contract := UnitQueue.SPEEDUP_CONTRACT
	for phrase: String in ["BOTH ts AND ui", "KeyError", "sm_training_time",
			"QUEUED UNIT", "SECONDS", "ceil(remaining / 3600)",
			"CHARGES NOTHING", "ts = 0", "Quite useless",
			"REFUSES with a named reason"]:
		check(contract.contains(phrase),
			"the recorded speedup contract names '%s'" % phrase)
	check_eq(UnitQueue.SPEEDUP_COST_IMPLEMENTED, false,
		"the recorded speedup cost is declared NOT implemented")
	check_eq(UnitQueue.SPEEDUP_FIELD, "sm_training_time",
		"the recorded duration field is the soul mixer's own field")
	check_eq(UnitQueue.SPEEDUP_COST_DIVISOR, 3600,
		"the recorded cost divisor is the hour the legacy formula divided by")
	var coverage := UnitQueue.SPEEDUP_FIELD_COVERAGE
	for phrase: String in ["300 of the 429", "84 distinct values", "4000",
			"0 of the 470", "SOUL-MIXER field"]:
		check(coverage.contains(phrase),
			"the recorded field coverage names '%s' as CONTENT" % phrase)
	check(UnitQueue.REFUSAL_NOTE.contains("KeyError"),
		"the recorded refusal note names the crash the contract does NOT "
			+ "reproduce")
	# The precondition: both keys present is the ONLY ok, and an absent key is a
	# named refusal, never a raise.
	var both := UnitQueue.speedup_precondition({"ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID})
	check_eq(bool(both.get("ok", false)), true,
		"the two-key precondition is met when the bag carries ts and ui")
	check_eq(both.get("reason", ""), "",
		"a met precondition carries no reason")
	check_eq(bool(both.get("cost_implemented", true)), false,
		"even a met precondition reports the cost as NOT implemented")
	check(str(both.get("contract", "")).contains("CHARGES NOTHING"),
		"the met precondition returns the recorded contract, so no caller can "
			+ "mistake an ok for a price")
	var no_start := UnitQueue.speedup_precondition({"ui": RESOLVING_UNIT_ID})
	check_eq(str(no_start.get("reason", "")), UnitQueue.REASON_MISSING_START,
		"a bag with no start instant is refused with its own named reason")
	check_eq(bool(no_start.get("refuses_instead_of_raising", false)), true,
		"the refusal is recorded as a refusal, where the legacy branch raises")
	check(str(no_start.get("error", "")).contains("KeyError"),
		"the refusal message names the crash it replaces")
	var no_unit := UnitQueue.speedup_precondition({"ts": fixture_stamp})
	check_eq(str(no_unit.get("reason", "")),
		UnitQueue.REASON_MISSING_UNIT_ID,
		"a bag with no queued unit id is refused with its own named reason")
	var empty := UnitQueue.speedup_precondition({})
	check_eq(str(empty.get("reason", "")), UnitQueue.REASON_MISSING_START,
		"an empty bag fails the start-instant precondition first")
	var no_bag := UnitQueue.speedup_precondition(null)
	check_eq(str(no_bag.get("reason", "")), UnitQueue.REASON_ABSENT_QUEUE,
		"a row with no attribute bag at all is reported as carrying no bag")
	check((no_bag.get("keys_present", []) as Array).is_empty(),
		"no precondition key is reported present on a row with no bag")
	# No cost is computed: the value the legacy formula would produce appears in
	# no returned field, and neither module computes one.
	for record: Dictionary in [both, no_start, no_unit, empty, no_bag]:
		check(not record.has("cost"),
			"the precondition verdict carries no cost field at all")
		check(not record.has("remaining"),
			"the precondition verdict carries no remaining-time field")
	# A queued unit that carries no duration field is exactly the legacy crash
	# the contract refuses instead of reproducing: nothing here reads the field.
	var unresolvable := UnitQueue.speedup_precondition({"ts": fixture_stamp,
		"ui": UNRESOLVABLE_UNIT_ID})
	check_eq(bool(unresolvable.get("ok", false)), true,
		"a queued id the content does not carry still MEETS the two-key "
			+ "precondition: the contract reads no duration, so it cannot fail "
			+ "where the legacy branch would raise inside int(...)")
	_check_behaviour_needles()


## No behaviour token appears in either delivered module's CODE: a cost, a timer,
## a completion, a produced unit, or the atom-fusion command. The tokens are
## spelled as fragments and matched against the declarations only, so the
## recorded contract TEXT may name them.
func _check_behaviour_needles() -> void:
	for res_path: String in [UNIT_QUEUE_SOURCE,
			QUEUE_FLOW_SOURCE]:
		var code := _code_only_path(res_path)
		for needle: String in BEHAVIOUR_NEEDLES:
			check(not code.contains(needle),
				"%s declares no '%s': no cost, no timer, no completion, and no "
					% [res_path, needle]
					+ "produced unit is implemented anywhere in this line")


# ---------------------------------------------------------------------------
# Queued unit id resolution (design D7)
# ---------------------------------------------------------------------------


## A resolving id reports its committed name; an unresolvable one is reported
## **with its recorded value intact** and nothing is substituted; an absent one
## is a named absence.
func _check_resolution(registry: Variant) -> void:
	var resolver := _resolver(registry)
	var resolved := UnitQueue.project({"nu": 1, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, resolver)
	if bool(resolved.get("ok", false)):
		var queue: Variant = resolved.get("queue", null)
		check_eq(str(queue.queued_unit_resolution()),
			UnitQueue.RESOLUTION_RESOLVED,
			"a committed queued id resolves through the registry's units domain")
		check_eq(str(queue.queued_unit_name()), "Ship",
			"the resolved queued unit's committed name is reported beside the id")
		check_eq(str(queue.queued_unit_resolution_error()), "",
			"a resolved id carries no resolution error")
	var unresolved := UnitQueue.project({"nu": 1, "ts": fixture_stamp,
		"ui": UNRESOLVABLE_UNIT_ID}, resolver)
	check(bool(unresolved.get("ok", false)),
		"an unresolvable queued id still projects: it is REPORTED, never "
			+ "dropped (%s)" % str(unresolved.get("error", "")))
	if bool(unresolved.get("ok", false)):
		var queue: Variant = unresolved.get("queue", null)
		check_eq(str(queue.queued_unit_resolution()),
			UnitQueue.RESOLUTION_UNRESOLVABLE,
			"an id the content package does not carry is reported unresolvable")
		check_eq(str(queue.queued_unit_id()), UNRESOLVABLE_UNIT_ID,
			"the unresolvable id's RECORDED VALUE is kept intact")
		check_eq(queue.queued_unit_name(), null,
			"an unresolvable id substitutes NO name at all")
		check(not str(queue.queued_unit_resolution_error()).is_empty(),
			"an unresolvable id carries the resolver's own reason")
		check(not str(queue.queued_unit_resolution_error()).contains("Ship"),
			"the unresolvable id is never resolved to another unit's name")
	var absent := UnitQueue.project({"nu": 1, "ts": fixture_stamp}, resolver)
	if bool(absent.get("ok", false)):
		var queue: Variant = absent.get("queue", null)
		check_eq(str(queue.queued_unit_resolution()),
			UnitQueue.RESOLUTION_ABSENT,
			"a bag with no ui reports the queued unit as absent")
		check_eq(queue.queued_unit_id(), null,
			"an absent queued unit id is null, never a guess")
		check_eq(queue.queued_unit_name(), null,
			"an absent queued unit has no name")
	# A missing or non-callable resolver is a REFUSAL, because dropping the id
	# silently would report a queue as carrying no queued unit when it does.
	var no_resolver := UnitQueue.project({"nu": 1, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, null)
	check(not bool(no_resolver.get("ok", false)),
		"a queued id with no usable resolver is REFUSED, never silently dropped")
	check(str(no_resolver.get("error", "")).contains("never")
			or str(no_resolver.get("error", "")).contains("dropping"),
		"the refusal message explains that dropping the id would misreport the "
			+ "queue")
	var broken := UnitQueue.project({"nu": 1, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, func(_id: String) -> Variant: return "nope")
	if bool(broken.get("ok", false)):
		var queue: Variant = broken.get("queue", null)
		check_eq(str(queue.queued_unit_resolution()),
			UnitQueue.RESOLUTION_UNRESOLVABLE,
			"a resolver that answers with something other than a resolution "
				+ "record reports the id unresolvable")
		check(str(queue.queued_unit_resolution_error()).contains("resolution"),
			"the message names the shape the resolver broke")


# ---------------------------------------------------------------------------
# The pure flow (design D1/D3/D4)
# ---------------------------------------------------------------------------


## The flow's own evaluation, its presence predicates, its recorded inert pop,
## and its display text — with no node, no clock, and no request anywhere.
func _check_flow(registry: Variant) -> void:
	var resolver := _resolver(registry)
	# A structural rejection is an error, not a report.
	var refused_evaluation := {}
	for value: Variant in [null, [], "bag"]:
		var evaluation := QueueFlow.evaluate(value, resolver)
		check(not bool(evaluation.get("ok", false)),
			"the flow refuses a non-object bag")
		if refused_evaluation.is_empty():
			refused_evaluation = evaluation
		check_eq(bool(evaluation.get("offers_push", true)), false,
			"a refused queue offers no intent at all")
		check_eq(bool(evaluation.get("offers_pop", true)), false,
			"a refused queue offers no pop")
		check_eq(evaluation.get("queue", null), null,
			"a refused queue carries no queue at all")
		check(QueueFlow.readout_text(evaluation).is_empty(),
			"a refused queue renders no readout line")
	# The corpus's own shape: an absent queue.
	var absent := QueueFlow.evaluate({}, resolver)
	check(bool(absent.get("ok", false)),
		"an empty bag evaluates: no queue is a REPORT, not an error")
	check_eq(bool(absent.get("present", true)), false,
		"the evaluation reports the queue as absent")
	check_eq(bool(absent.get("offers_push", false)), true,
		"a push is offered for any readable bag: the legacy push increments a "
			+ "count and stamps an instant on any row, and the recorded absence "
			+ "of a producer check is not permission to add one")
	check_eq(bool(absent.get("offers_pop", true)), false,
		"a pop is NOT offered on a row with no queue: legacy's pop there is an "
			+ "inert recorded no-op")
	check(str(QueueFlow.pop_refusal_text(absent)).contains("INERT"),
		"the pop refusal names the recorded inert no-op it avoids")
	check(QueueFlow.readout_text(absent).contains("no queue"),
		"the readout says 'no queue' rather than 'count 0'")
	# A queued row.
	var queued := QueueFlow.evaluate({"nu": 2, "ts": fixture_stamp}, resolver)
	check(bool(queued.get("ok", false)), "a queued bag evaluates")
	check_eq(bool(queued.get("present", false)), true,
		"the evaluation reports the queue as present")
	check_eq(int(queued.get("count", 0)), 2, "the count is reported verbatim")
	check_eq(int(queued.get("start_instant", 0)), fixture_stamp,
		"the start instant is reported verbatim")
	check_eq(bool(queued.get("offers_pop", false)), true,
		"a pop IS offered for a row carrying a count")
	check_eq(QueueFlow.pop_refusal_text(queued), "",
		"no refusal text is offered while a pop is")
	check(str(QueueFlow.readout_text(queued)).contains("count 2"),
		"the readout shows the committed count")
	check(str(QueueFlow.readout_text(queued)).contains("no completion"),
		"the readout STATES the recorded absence of completion rather than "
			+ "leaving a reader to wonder")
	check(str(QueueFlow.readout_text(queued)).contains("TOGETHER"),
		"the readout names the three-key teardown")
	# A queued unit: resolved and unresolvable both render explicitly.
	var with_unit := QueueFlow.evaluate({"nu": 1, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, resolver)
	check(str(QueueFlow.readout_text(with_unit)).contains("Ship"),
		"a resolved queued unit renders its committed name")
	var bad_unit := QueueFlow.evaluate({"nu": 1, "ts": fixture_stamp,
		"ui": UNRESOLVABLE_UNIT_ID}, resolver)
	var rendered := QueueFlow.readout_text(bad_unit)
	check(rendered.contains(QueueFlow.UNIT_UNRESOLVABLE_TEXT),
		"an unresolvable queued unit renders an explicit marker")
	check(rendered.contains(UNRESOLVABLE_UNIT_ID),
		"the unresolvable id's recorded value is RENDERED, never dropped")
	check(not rendered.contains("Ship"),
		"the unresolvable id is never rendered as another unit's name")
	# The speedup verdict travels with the evaluation and names no price. Only a
	# row carrying BOTH committed keys reaches the met precondition, so the two
	# verdicts are read from a row that does and one that does not.
	var speedup_met := QueueFlow.evaluate({"nu": 1, "ts": fixture_stamp,
		"ui": RESOLVING_UNIT_ID}, resolver)
	var speedup_text := QueueFlow.speedup_text(speedup_met)
	check(speedup_text.contains("NOT implemented"),
		"the speedup verdict says the cost is not implemented")
	for number: String in ["3600", "Cash", "gold", "cost of"]:
		check(not speedup_text.contains(number),
			"the speedup verdict names no price (%s)" % number)
	var refused_speedup := QueueFlow.speedup_text(absent)
	check(refused_speedup.contains("refused"),
		"a row failing the two-key precondition reports a refusal")
	check(refused_speedup.contains("KeyError"),
		"the refusal names the legacy crash it replaces")
	# The confirm texts name the effect and no price.
	var push_confirm := QueueFlow.confirm_text("push", queued)
	check(push_confirm.contains("charges nothing"),
		"the push confirm states that a push charges nothing")
	check(push_confirm.contains("no command that finishes a queue"),
		"the push confirm states that no legacy command finishes a queue")
	var pop_confirm := QueueFlow.confirm_text("pop", queued)
	check(pop_confirm.contains("charges nothing"),
		"the pop confirm states that a pop charges nothing")
	check(not pop_confirm.contains("TOGETHER"),
		"the pop confirm does not restate the teardown verbatim")
	check(QueueFlow.confirm_text("push", refused_evaluation).is_empty(),
		"a structurally refused queue confirms nothing")
	# The recorded flow record carries the recorded absences.
	var record := QueueFlow.command_record()
	check(str(record["no_validation"]).contains("do not cap nu"),
		"the flow's record carries the recorded absence of a count bound")
	check(str(record["no_elapsed_time"]).contains("NO ELAPSED-TIME"),
		"the flow's record carries the recorded absence of elapsed time")
	check(str(record["inert_pop"]).contains("engine.py:193-194"),
		"the flow's record names the committed source of the inert pop")
	var speedup_record: Dictionary = QueueFlow.speedup_record()
	check_eq(bool(speedup_record["implemented"]), false,
		"the flow's speedup record declares the contract NOT implemented")
	check_eq(bool(speedup_record["cost_implemented"]), false,
		"the flow's speedup record declares the cost NOT implemented")
	check_eq((speedup_record["precondition_keys"] as Array), ["ts", "ui"],
		"the speedup record names its TWO required keys")
	check(str(speedup_record["duration_source"]).contains("QUEUED unit"),
		"the speedup record says the duration is read off the QUEUED unit")
	check(str(speedup_record["legacy_verdict"]).contains("Quite useless"),
		"the speedup record carries the legacy author's own verdict verbatim")


# ---------------------------------------------------------------------------
# The committed corpus measurement (design D8)
# ---------------------------------------------------------------------------


## The committed corpus's own measurement: 40 rows, key 1 is the real Command
## Center with an EMPTY bag, and therefore **zero** carried queue keys anywhere.
## That zero is asserted — it is a fact about the corpus, not evidence that a
## queue can be obtained or seen.
func _check_corpus() -> Dictionary:
	var save: Variant = _read_json(Paths.repo_root().path_join(CORPUS_SAVE))
	check(save is Dictionary, "the committed corpus save is readable JSON")
	if not (save is Dictionary):
		return {}
	var map: Dictionary = (save as Dictionary)["maps"][CORPUS_MAP_INDEX]
	var rows: Dictionary = map["items"]
	check_eq(rows.size(), EXPECTED_ROWS,
		"the committed corpus places %d rows" % EXPECTED_ROWS)
	var target: Variant = _as_int_tree(rows[TARGET_KEY])
	check_eq(target, TARGET_ROW,
		"map key %s is the committed corpus's own real placed training "
			% TARGET_KEY
			+ "producer: id %d %s at (51, 41) with an EMPTY attribute bag"
			% [TARGET_ITEM, TARGET_ITEM_NAME])
	var carried: Array = []
	var malformed: Array = []
	for key: Variant in rows.keys():
		var bag: Variant = (rows[key] as Array)[UnitQueue.ATTR_SLOT]
		if not (bag is Dictionary):
			malformed.append(str(key))
			continue
		for queue_key: String in UnitQueue.queue_keys():
			if (bag as Dictionary).has(queue_key):
				carried.append("%s/%s" % [str(key), queue_key])
	check_eq(malformed, [],
		"every committed row carries an object attribute bag")
	check_eq(carried, [],
		"NOT ONE committed corpus row carries a queue key: the corpus's own "
			+ "queues are all absent, which is why the executed fixture's push "
			+ "is the only way a queue appears here")
	var resources := _corpus_resources(save)
	check_eq(resources, CORPUS_RESOURCES,
		"the committed corpus records the seven balances both queue steps leave "
			+ "byte-identical")
	var other_map_keys: Array = []
	for key: String in ["level", "store", "expansions", "gold", "wood", "oil",
			"steel", "xp"]:
		if not map.has(key):
			other_map_keys.append(key)
	check_eq(other_map_keys, [],
		"the corpus map carries every field the queue transaction must not "
			+ "touch")
	return {
		"save": CORPUS_SAVE,
		"rows": rows.size(),
		"target_key": TARGET_KEY,
		"target_row": TARGET_ROW,
		"carried_keys": carried,
		"resources": resources,
		"map_level": _as_int(map.get("level")),
		"owned_expansions": (map.get("expansions") as Array).duplicate(),
		"player_store": (map.get("store") as Dictionary).duplicate(true),
		"bought_units": ((save as Dictionary)["privateState"]["boughtUnits"]
			as Array).duplicate(),
		"item_id": TARGET_ITEM,
		"item_name": TARGET_ITEM_NAME,
		"training_time": TARGET_TRAINING_TIME,
		"min_level": TARGET_MIN_LEVEL,
		"group_type": TARGET_GROUP_TYPE,
	}


# ---------------------------------------------------------------------------
# The committed executed-legacy fixture (design D3/D4)
# ---------------------------------------------------------------------------


## The committed executed push and pop: the recorded attribute bags, all 40 rows,
## every stored resource, the storage, the private state, the player info, and
## the manifest's own statements that **no completion was captured and that no
## completion command exists**.
func _check_fixture() -> Dictionary:
	var manifest: Variant = _read_json(Paths.repo_root().path_join(
		FIXTURE_MANIFEST))
	check(manifest is Dictionary, "the queue fixture manifest is readable JSON")
	if not (manifest is Dictionary):
		return {}
	var push_before := _fixture_state(FIXTURE_PUSH_DIR, "before")
	var push_after := _fixture_state(FIXTURE_PUSH_DIR, "after")
	var pop_before := _fixture_state(FIXTURE_POP_DIR, "before")
	var pop_after := _fixture_state(FIXTURE_POP_DIR, "after")
	if push_before.is_empty() or push_after.is_empty():
		return {}
	if pop_before.is_empty() or pop_after.is_empty():
		return {}
	var recorded: Dictionary = manifest as Dictionary
	var captured: Dictionary = recorded["captured"]
	# The transaction's own shape.
	check_eq(bool(captured.get("push", false)), true,
		"the manifest records that a PUSH was captured")
	check_eq(bool(captured.get("pop", false)), true,
		"the manifest records that a POP was captured")
	check_eq(bool(captured.get("completion_captured", true)), false,
		"the manifest records that NO completion was captured")
	check_eq(bool(captured.get("completion_command_exists", true)), false,
		"the manifest records that the legacy server has NO completion command")
	check_eq(bool(captured.get("completion", true)), false,
		"the manifest's completion flag is false")
	var completion: Dictionary = captured["no_server_side_completion"]
	check_eq(str(_as_int(completion.get("dispatcher_named_branches", 0))), "63",
		"the manifest names the whole dispatcher's 63 branches")
	check_eq((completion["complete_family"] as Array),
		["complete_collection", "complete_goal", "complete_tutorial"],
		"the manifest records the complete_* family as exactly those three, so "
			+ "no queue completion exists among them")
	check_eq(completion.get("queue_completion_command", "unset"), null,
		"the manifest records that no queue completion command exists")
	check_eq(completion.get("unit_materialising_command", "unset"), null,
		"the manifest records that no command materialises a unit from a queue")
	var uses: Dictionary = completion["attr_ts_uses"]
	check_eq((uses["writes"] as Array), ["engine.py:189", "engine.py:198"],
		"every committed write of a queue's start instant is recorded")
	check_eq((uses["deletions"] as Array), ["engine.py:202"],
		"the recorded teardown deletion is the only deletion")
	check_eq((uses["readers"] as Array).size(), 1,
		"exactly ONE branch reads a queue's start instant, and it is the "
			+ "soul-mixer speedup rather than a general queue path")
	# The executed push: the empty bag became the committed count and instant,
	# and NOTHING else in the save moved.
	check_eq(_attr_of(push_before, TARGET_KEY), {},
		"the executed push's before state carries an EMPTY bag at map key %s"
			% TARGET_KEY)
	check_eq(_attr_of(push_after, TARGET_KEY),
		{"nu": 1, "ts": fixture_stamp},
		"the executed push set the count to 1 and stamped the start instant, "
			+ "writing nothing else")
	_check_rows_unchanged(push_before, push_after, "the executed push")
	_check_resources_unchanged(push_before, push_after, "the executed push")
	_check_untouched(push_before, push_after, "the executed push")
	# The executed pop: the count reached zero and the THREE keys died together.
	check_eq(_attr_of(pop_before, TARGET_KEY),
		{"nu": 1, "ts": fixture_stamp},
		"the executed pop's before state is the push's own after state, so the "
			+ "pair is ONE recorded transaction")
	check_eq(_attr_of(pop_after, TARGET_KEY), {},
		"the executed pop's teardown removed nu, ts, and ui TOGETHER: the bag "
			+ "is empty again and no key was left behind")
	_check_rows_unchanged(pop_before, pop_after, "the executed pop")
	_check_resources_unchanged(pop_before, pop_after, "the executed pop")
	_check_untouched(pop_before, pop_after, "the executed pop")
	# The teardown returned the row to the corpus byte for byte.
	check_eq((pop_after as Dictionary)["maps"], (push_before as Dictionary)["maps"],
		"after the push and the pop the save's map is byte-identical to the "
			+ "committed corpus: the only queue the fixture ever held was torn "
			+ "down")
	# The manifest's own derivations, matched against what the fixture recorded.
	var transactions: Array = recorded["transactions"]
	check_eq(transactions.size(), 2, "the manifest records exactly two steps")
	if transactions.size() == 2:
		var push_record: Dictionary = transactions[0]
		var pop_record: Dictionary = transactions[1]
		check_eq(str(push_record["command"]), "push_queue_unit",
			"the first executed step was the push")
		check_eq(str(pop_record["command"]), "pop_queue_unit",
			"the second executed step was the pop")
		check_eq(int((push_record["derived"] as Dictionary)["count"]), 1,
			"the manifest's derived push count is 1")
		check_eq(bool((pop_record["derived"] as Dictionary)["teardown"]), true,
			"the manifest's derived pop records the three-key teardown")
		check_eq(int((push_record["projection_after"] as Dictionary)["count"]), 1,
			"the manifest's own post-execution projection reports the count")
		check_eq(bool((pop_record["projection_after"] as Dictionary)["present"]),
			false,
			"the manifest's own post-teardown projection reports the queue as "
				+ "ABSENT, not as a zero count")
	var transaction: Dictionary = recorded["transaction"]
	check_eq(bool(transaction.get("readiness_computed", true)), false,
		"the manifest records that NO readiness was computed")
	check_eq(bool(transaction.get("unit_produced", true)), false,
		"the manifest records that NO unit was produced")
	check_eq(bool(transaction.get("count_bound_applied", true)), false,
		"the manifest records that NO count bound was applied")
	check_eq(bool((recorded["target"] as Dictionary).get("fabricated_state",
			true)), false,
		"the manifest records that NO player state was fabricated")
	check_eq(int((recorded["target"] as Dictionary)["training_time"]),
		TARGET_TRAINING_TIME,
		"the manifest names the target's committed training_time")
	check_eq(int((recorded["target"] as Dictionary)["min_level"]),
		TARGET_MIN_LEVEL,
		"the manifest names the target's committed min_level")
	check_eq(str((recorded["target"] as Dictionary)["group_type"]),
		TARGET_GROUP_TYPE,
		"the manifest names the target's committed group_type")
	var normalization: Dictionary = recorded["time_dependent_fields"]
	check(str(normalization["documented_normalization"]).contains(
			"one-second resolution"),
		"the manifest records WHY the start instant is compared by shape and "
			+ "direction rather than by value")
	return {
		"manifest": FIXTURE_MANIFEST,
		"schema": str(recorded.get("schema", "")),
		"push_before_attr": _attr_of(push_before, TARGET_KEY),
		"push_after_attr": _attr_of(push_after, TARGET_KEY),
		"pop_before_attr": _attr_of(pop_before, TARGET_KEY),
		"pop_after_attr": _attr_of(pop_after, TARGET_KEY),
		"resources": _corpus_resources(push_before),
		"rows": (push_before as Dictionary)["maps"][CORPUS_MAP_INDEX]["items"].size(),
		"map_key": TARGET_MAP_KEY,
		"completion_captured": bool(captured.get("completion_captured", true)),
		"completion_command_exists": bool(captured.get(
			"completion_command_exists", true)),
	}


# ---------------------------------------------------------------------------
# The committed content coverage (task 1.3)
# ---------------------------------------------------------------------------


## The committed coverage of `sm_training_time`, MEASURED from the verified
## registry rather than asserted from prose: 300 of 429 units, 0 of 470
## buildings, 84 distinct values from 4000. It is recorded as content and never
## applied as a rule.
func _check_content(registry: Variant) -> Dictionary:
	var units := _field_coverage(registry, UnitQueue.UNIT_DOMAIN,
		UnitQueue.SPEEDUP_FIELD)
	var buildings := _field_coverage(registry, "buildings",
		UnitQueue.SPEEDUP_FIELD)
	check_eq(int(units["of"]), EXPECTED_UNITS,
		"the committed package carries %d units" % EXPECTED_UNITS)
	check_eq(int(units["with_field"]), EXPECTED_UNITS_WITH_SPEEDUP_FIELD,
		"exactly %d of them carry sm_training_time"
			% EXPECTED_UNITS_WITH_SPEEDUP_FIELD)
	check_eq(int(units["missing"]), EXPECTED_UNITS
			- EXPECTED_UNITS_WITH_SPEEDUP_FIELD,
		"the other %d units carry no duration field at all"
			% (EXPECTED_UNITS - EXPECTED_UNITS_WITH_SPEEDUP_FIELD))
	check_eq(int(units["distinct_values"]), EXPECTED_SPEEDUP_DISTINCT_VALUES,
		"the recorded coverage's 84 distinct values is what the content holds")
	check_eq(int(units["minimum"]), EXPECTED_SPEEDUP_MINIMUM,
		"the recorded coverage's minimum of 4000 is what the content holds")
	check_eq(int(buildings["of"]), EXPECTED_BUILDINGS,
		"the committed package carries %d buildings" % EXPECTED_BUILDINGS)
	check_eq(int(buildings["with_field"]), EXPECTED_BUILDINGS_WITH_SPEEDUP_FIELD,
		"NO committed building carries sm_training_time: the field is the "
			+ "soul mixer's own")
	# The target's own committed training facts, read from the buildings domain.
	var target: Variant = registry.get_entry("buildings",
		str(TARGET_ITEM)).get("entry", null)
	check(target is Dictionary,
		"the target's committed building definition resolves")
	if target is Dictionary:
		var entry: Dictionary = target
		check_eq(int(entry.get("training_time", -1)), TARGET_TRAINING_TIME,
			"the target's committed training_time is 5")
		check_eq(int(entry.get("min_level", -1)), TARGET_MIN_LEVEL,
			"the target's committed min_level is 1")
		check_eq(str(entry.get("group_type", "")), TARGET_GROUP_TYPE,
			"the target's committed group_type is COMMAND_CENTER")
		check_eq(str(entry.get("name", "")), TARGET_ITEM_NAME,
			"the target's committed name is Command Center")
		check(not (entry as Dictionary).has(UnitQueue.SPEEDUP_FIELD),
			"the target carries no soul-mixer duration field, which is why the "
				+ "recorded speedup cannot read one off a BUILDING")
	return {"units": units, "buildings": buildings}


# ---------------------------------------------------------------------------
# The guarded intents (design D2/D5/D8)
# ---------------------------------------------------------------------------


## The facade's two queue operations take EXACTLY the save identity and the
## target row's key, so there is **no parameter through which a client could
## send a count, a cost, a duration, or a readiness** — the structural form of
## the "a client-supplied outcome is ignored" claim. Both implementations
## implement them, and the endpoint path is named in the legacy-v0 one alone.
func _check_intents() -> void:
	var facade: Variant = root.get_node_or_null("GameApi")
	check(facade != null, "GameApi autoload is registered")
	if facade == null:
		return
	var methods: Variant = facade.get_script().get_script_method_list()
	for name: String in ["push_queue_unit_town", "pop_queue_unit_town"]:
		var found: Variant = _method(methods, name)
		check(found != null,
			"the facade implements the %s intent" % name)
		if found != null:
			var args: Array = (found as Dictionary)["args"]
			check_eq(args.size(), 2,
				"%s takes EXACTLY the save identity and the target row's key: "
					% name
					+ "there is no parameter through which a client could send a "
					+ "count, a cost, a duration, or a readiness")
	check(_has_counter(facade, "queue_requests"),
		"the facade counts production-queue intents like every other command")
	var implementation: String = str(facade.implementation_name())
	check(implementation == "fake",
		"the hermetic run is on the fake implementation")
	# The endpoint path is named in the legacy-v0 implementation and nowhere else.
	var transport_source := _source("res://scripts/gameapi/legacy_v0_api.gd")
	check(transport_source.contains("/v0/queue"),
		"the legacy-v0 implementation names the queue endpoint")
	var facade_source := _source("res://scripts/gameapi/game_api.gd")
	check(not facade_source.contains("/v0/queue"),
		"the facade never names the queue endpoint")
	var fake_source := _source("res://scripts/gameapi/fake_api.gd")
	check(not fake_source.contains("/v0/queue"),
		"the fake double never names the queue endpoint")
	# The typed result carries no outcome this contract does not own.
	var result := BootData.QueueResult.new()
	check_eq(BootData.QUEUE_ACTIONS, ["push", "pop"],
		"the typed result's closed action set is the push and the pop")
	for forbidden: String in ["remaining", "progress", "complete", "cost",
			"ready"]:
		check(not _class_members(BootData.QueueResult).has(forbidden),
			"the typed queue result declares no %s field: the legacy server has "
				% forbidden + "no such rule to report")
	check(result.row == null and result.previous == null,
		"a fresh typed queue result carries no partial payload")


# ---------------------------------------------------------------------------
# Purity and containment
# ---------------------------------------------------------------------------


## Neither delivered module names a node, a clock, a request, or a transport
## token, and both are pure over a bag the caller already holds.
func _check_purity() -> void:
	for res_path: String in [UNIT_QUEUE_SOURCE,
			QUEUE_FLOW_SOURCE]:
		var code := _code_only_path(res_path)
		for needle: String in PURITY_NEEDLES:
			check(not code.contains(needle),
				"%s declares no '%s': the projection is pure over a bag the "
					% [res_path, needle] + "caller already holds")
	# The model loads nothing at all, and the flow loads exactly the model: the
	# static/instance boundary stays one-way, so a surface can never smuggle
	# content access into the projection.
	var model_preloads: Array = _preloads(_source(UNIT_QUEUE_SOURCE))
	check_eq(model_preloads, [],
		"the projection model loads no script at all: it resolves nothing "
			+ "itself")
	check_eq(_preloads(_source(QUEUE_FLOW_SOURCE)), [UNIT_QUEUE_SOURCE],
		"the pure flow loads exactly the projection model and nothing else")
	check(not _source(QUEUE_FLOW_SOURCE).contains("await "),
		"the pure flow awaits nothing")


## The content package, the committed saves, and the committed fixtures are
## byte-identical after the run: this line writes evidence under
## `evidence/unit-queues/` and fault copies under `.godot/`, nothing else.
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
	check_eq(fixtures_after.get("sha256", ""),
		fixtures_before.get("sha256", ""),
		"no committed fixture byte changed during the run — including the "
			+ "executed queue fixture, which is only read")
	var save_after := Paths.file_sha256_checked(Paths.repo_root().path_join(
		CORPUS_SAVE))
	check_eq(save_after.get("sha256", ""), save_before.get("sha256", ""),
		"the committed corpus save is byte-identical after the run")
	check_eq(save_after.get("bytes", 0), save_before.get("bytes", 0),
		"the committed corpus save's byte count is unchanged")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory exists after the run")


# ---------------------------------------------------------------------------
# The live-queue phase (verify-boot's `queue-live`)
# ---------------------------------------------------------------------------


## One push and one pop through the REAL Compatibility endpoint, so the
## unchanged legacy `command()` executes the derived queue envelopes over the
## disposable corpus. This side asserts the typed response AND its two-part
## post-state proof — the row's bag carries exactly the derived count, the
## stamped instant, and the three-key teardown — plus that **every stored
## resource is unchanged**, which is what makes the neutral-vector claim
## meaningful rather than tautological. The phase harness separately asserts the
## corpus save file mutated.
func _check_live_queue() -> void:
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
	# The corpus's own row 1 before the intent: an EMPTY bag, and the seven
	# balances the neutral vector must leave untouched.
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(), "the corpus pre-queue payload resolves")
	if before_payload.is_empty():
		return
	var row_before: Variant = _live_row(before_payload, TARGET_KEY)
	check_eq(row_before, TARGET_ROW,
		"the live corpus's row 1 is the committed Command Center with an empty "
			+ "bag")
	var resources_before := _live_resources(before_payload)
	# The push.
	var pushed: Variant = await api.push_queue_unit_town(pid, TARGET_MAP_KEY)
	check(pushed is BootData.QueueResult and pushed.ok,
		"a push is accepted by the real endpoint: %s"
			% ((pushed as BootData.QueueResult).error_message
				if pushed is BootData.QueueResult else ""))
	if not (pushed is BootData.QueueResult and pushed.ok):
		return
	_check_typed_queue(pushed)
	var typed: BootData.QueueResult = pushed
	check_eq(str(typed.action), "push",
		"the service echoed the action exactly as sent")
	check_eq(int(typed.map_key), TARGET_MAP_KEY,
		"the service addressed the key the client named")
	check_eq(int(typed.queue.count), 1,
		"the executed push set the committed count to 1")
	check(typed.queue.start_instant != null
			and int(typed.queue.start_instant) > 0,
		"the executed push stamped the start instant with the wall clock")
	check_eq((typed.queue.keys as Array), ["nu", "ts"],
		"the post-execution bag carries exactly nu and ts, never a ui")
	check_eq(bool(typed.queue.present), true,
		"the post-execution projection reports a queue")
	check_eq(bool(typed.queue.absent_is_absent), true,
		"the service states its own absence rule")
	check_eq(int(typed.previous.x), 51,
		"the response's previous row is the row the client named")
	# Two-part proof, part two: every stored resource unchanged.
	for name: String in CORPUS_RESOURCES.keys():
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the push (the endpoint's "
				% name + "value-level proof)")
	# The same intent through the fake, offline: the same typed shapes and code.
	api.configure("fake")
	var fake_push: Variant = await api.push_queue_unit_town(pid, TARGET_MAP_KEY)
	check(fake_push is BootData.QueueResult and fake_push.ok,
		"the fake accepts the same push offline")
	if fake_push is BootData.QueueResult and fake_push.ok:
		_check_typed_queue(fake_push)
		check_eq(int((fake_push as BootData.QueueResult).queue.count), 1,
			"both implementations derive the same committed count")
		check_eq(int((fake_push as BootData.QueueResult).row.x), 51,
			"both implementations address the same committed row")
	# The pop, against the row the live push just queued.
	api.configure("legacy_v0", endpoint)
	var popped: Variant = await api.pop_queue_unit_town(pid, TARGET_MAP_KEY)
	check(popped is BootData.QueueResult and popped.ok,
		"a pop is accepted by the real endpoint: %s"
			% ((popped as BootData.QueueResult).error_message
				if popped is BootData.QueueResult else ""))
	var pop_torn_down := false
	if popped is BootData.QueueResult and popped.ok:
		var typed_pop: BootData.QueueResult = popped
		_check_typed_queue(typed_pop)
		check_eq(str(typed_pop.action), "pop",
			"the service echoed the pop action exactly as sent")
		check_eq(int((typed_pop.previous.attr as Dictionary).get("nu", 0)), 1,
			"the executed pop's before row carried the pushed count, so the "
				+ "teardown fired on a count of exactly one")
		pop_torn_down = bool(typed_pop.row.attr.is_empty())
		check_eq(pop_torn_down, true,
			"the executed pop's three-key teardown removed nu, ts, and ui "
				+ "TOGETHER: the bag is empty again")
		check_eq(bool(typed_pop.queue.present), false,
			"the post-teardown projection reports the queue as ABSENT, never as "
				+ "a zero count with a zero instant")
		check_eq(typed_pop.queue.count, null,
			"the post-teardown count is null, which a zero cannot say")
		for name: String in CORPUS_RESOURCES.keys():
			check_eq(int((typed_pop.resources as BootData.Resources).get(name)),
				int(resources_before[name]),
				"the %s balance is UNCHANGED by the pop" % name)
	# A refused pop: a key that names no row leaves the corpus alone.
	var refused: Variant = await api.pop_queue_unit_town(pid, 9999999)
	check(refused is BootData.QueueResult and not refused.ok,
		"a pop against a key that names no row is refused")
	if refused is BootData.QueueResult:
		check_eq(str(refused.error_code), "unknown_map_key",
			"the refusal is the service's own code: %s"
				% str(refused.error_message))
		check(refused.row == null and refused.queue == null,
			"the refused pop carries no partial payload")
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check_eq(_live_row(after_payload, TARGET_KEY), TARGET_ROW,
		"after the push and the pop the live row is byte-identical to the "
			+ "committed corpus again")
	check_eq(_live_resources(after_payload), resources_before,
		"every live corpus balance is byte-identical after both intents")
	print("[test] live-queue applied map_key=%d push_count=%d pop_torn_down=%s "
		% [TARGET_MAP_KEY, int(typed.queue.count), pop_torn_down]
		+ "resources_unchanged=true refused=unknown_map_key")


## The typed result's own shape, asserted rather than assumed: two rows, the
## queue block, and the seven resources — with no readiness, remaining time,
## progress, completion, or cost field anywhere.
func _check_typed_queue(result: Variant) -> void:
	if not (result is BootData.QueueResult):
		return
	var typed: BootData.QueueResult = result
	check_eq(bool(typed.ok), true, "the queue result reports success")
	check_eq(str(typed.protocol), BootData.PROTOCOL,
		"the typed result reports the v0 protocol")
	check_eq(str(typed.result), "success",
		"the typed result carries the legacy success result")
	check(typed.server_time > 0,
		"the typed result's server_time is a positive integer")
	check(typed.previous != null and typed.row != null,
		"the typed result carries BOTH rows: the pre-execution row and the "
			+ "post-execution one")
	if typed.previous != null and typed.row != null:
		check_eq(int(typed.previous.item_id), TARGET_ITEM,
			"the previous row is the addressed committed item")
		check_eq(int(typed.row.item_id), TARGET_ITEM,
			"the post-execution row is the same committed item")
		check_eq(int(typed.row.x), int(typed.previous.x),
			"a queue command rewrites the row IN PLACE: the cell is unchanged")
	check(typed.queue != null, "the typed result carries the service's queue "
		+ "projection")
	check(typed.resources != null,
		"the typed result carries the authoritative resources")
	var members := _class_members(BootData.QueueResult)
	for forbidden: String in ["remaining", "progress", "complete", "cost",
			"ready", "duration"]:
		check(not members.has(forbidden),
			"the typed queue result declares no %s field" % forbidden)
	var queue_members := _class_members(BootData.QueueState)
	for required: String in ["present", "count", "start_instant",
			"queued_unit_id", "keys", "absent_is_absent"]:
		check(queue_members.has(required),
			"the typed queue projection declares %s" % required)


# ---------------------------------------------------------------------------
# Evidence report (design D8)
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


## Computes and writes the deterministic `unit-queues-report-v1` report.
##
## EVERY fact about the model comes from `unit_queue.gd` and `queue_flow.gd` —
## their own key constants, `COMMANDS`, `TEARDOWN`, `NO_VALIDATION`,
## `NO_ELAPSED_TIME`, `SPEEDUP_CONTRACT`, `PROVENANCE`, `NON_CLAIMS`, and
## `NON_READINESS` — every committed number comes from the registry that was just
## verified or from the committed corpus and fixture bytes, so the report cannot
## drift from the code it documents. Nothing here reads the wall clock, resolves
## a path outside the repository, or sends a request: that is what makes the file
## byte-identical across reruns.
func _write_report(path: String, registry: Variant, loaded: Dictionary,
		corpus: Dictionary, fixture: Dictionary, coverage: Dictionary,
		package_digest: Dictionary, save_digest: Dictionary) -> void:
	var speedup := QueueFlow.speedup_record()
	var speedup_block: Dictionary = QueueFlow.evaluate({"nu": 1,
		"ts": fixture_stamp, "ui": RESOLVING_UNIT_ID}, _resolver(registry))
	var committed_speedup: Dictionary = speedup_block["speedup"]
	var report := {
		"schema": "unit-queues-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_queues.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from the "
				+ "model's own constants, the verified registry, and the "
				+ "committed corpus and fixture bytes, and every derived set "
				+ "is sorted before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) "
				+ "plus one trailing newline; every number written is an "
				+ "integer - the pinned engine's integral floats are "
				+ "normalised on the way in, which changes no value - so no "
				+ "float formatting varies between runs",
			"time_dependent_fields": "the ONLY time-dependent value in this "
				+ "line's evidence is the start instant the legacy push "
				+ "stamped, which the fixture fixed at one run and the suite "
				+ "asserts by value; the double stamps that same committed "
				+ "value rather than reading a clock",
		},
		"queue_model": {
			"keys": UnitQueue.queue_keys(),
			"key_meanings": {
				UnitQueue.KEY_COUNT: "the queue COUNT: incremented when "
					+ "present and set to 1 when absent",
				UnitQueue.KEY_START: "the queue START INSTANT, stamped with "
					+ "timestamp_now() by a push and re-stamped by a partial "
					+ "decrement",
				UnitQueue.KEY_UNIT_ID: "the OPTIONAL queued unit id, written "
					+ "by the atom-fusion push alone",
			},
			"attr_slot": UnitQueue.ATTR_SLOT,
			"attr_slot_source": "engine.py:31, the placed row's seventh slot",
			"resolution_vocabulary": [UnitQueue.RESOLUTION_ABSENT,
				UnitQueue.RESOLUTION_RESOLVED,
				UnitQueue.RESOLUTION_UNRESOLVABLE],
			"unit_domain": UnitQueue.UNIT_DOMAIN,
			"absent_is_absent": "a bag carrying none of the three keys is "
				+ "reported as ABSENT with a null count and a null instant, "
				+ "never as a count of zero paired with an instant of zero: the "
				+ "three-key teardown deletes the keys at zero, so that pair is "
				+ "unreachable in a legacy save and reporting it would be "
				+ "indistinguishable from a queue that had just been emptied",
			"verbatim_rule": "the count and the instant are reported exactly "
				+ "as the bag holds them - no scaling, rounding, defaulting, or "
				+ "clamping - and a malformed value fails closed with the key "
				+ "named. The queued unit id is reported VERBATIM with no shape "
				+ "check at all, because only a client-supplied argument ever "
				+ "writes it (design D7)",
			"read_only": "the model holds copies of the three values and "
				+ "declares no setter, no mutating method, and no writable "
				+ "public field; every reader returns a committed value, a "
				+ "named absence, or a fresh copy, and the suite asserts the "
				+ "save's bag is byte-identical after every read",
		},
		"commands": QueueFlow.command_record(),
		"command_rule": "each of the three branches does nothing but resolve a "
			+ "map row, call an engine helper, and print (command.py:676-708). "
			+ "The map index is the ONLY positional argument, and the "
			+ "atom-fusion variant's unit id is a CLIENT-SUPPLIED argument no "
			+ "evidence constrains, which is why no intent derives it (design "
			+ "D7)",
		"no_validation": {
			"implemented": false,
			"rule": UnitQueue.NO_VALIDATION,
			"producer_check": false,
			"duration_check": false,
			"level_check": false,
			"count_bound": false,
			"count_bound_note": "NO maximum count is applied anywhere, at any "
				+ "value: the legacy engine sets none, and the suite projects "
				+ "counts of 1, 2, 5, 64, 9999, and 1000000 and asserts each "
				+ "one verbatim. The recorded absence of a bound is NOT "
				+ "permission to invent a cap (design D5)",
			"authoritative_limit": "an authoritative producer, duration, "
				+ "level, or count rule belongs to Server v1 / M13",
		},
		"no_elapsed_time": {
			"implemented": false,
			"rule": UnitQueue.NO_ELAPSED_TIME,
			"helpers_present": [],
			"non_readiness": (QueueFlow.NON_READINESS as Array).duplicate(true),
			"attr_ts_uses": {
				"writes": ["engine.py:189", "engine.py:198"],
				"deletions": ["engine.py:202"],
				"readers": ["command.py:733 (soulmixer_speedup only, and not a "
					+ "general queue path)"],
			},
			"completion": "the dispatcher's complete_* family is exactly "
				+ "complete_collection, complete_goal, and complete_tutorial, "
				+ "so no command completes a queue and no command materialises "
				+ "a unit from one. A queue can be pushed and popped and nothing "
				+ "server-side ever finishes it",
			"inventory_proof": "both delivered modules' whole function "
				+ "inventories are asserted against a pinned list by the suite, "
				+ "so a readiness, remaining-time, progress, or completion "
				+ "helper fails the run wherever it is added",
		},
		"speedup": speedup,
		"speedup_precondition": {
			"met_on_the_committed_shape": bool(committed_speedup["ok"]),
			"reason": str(committed_speedup["reason"]),
			"keys_present": (committed_speedup["keys_present"] as Array)
				.duplicate(),
			"cost_implemented": bool(committed_speedup["cost_implemented"]),
			"refuses_instead_of_raising": bool(
				committed_speedup["refuses_instead_of_raising"]),
			"reasons": [UnitQueue.REASON_ABSENT_QUEUE,
				UnitQueue.REASON_MISSING_START,
				UnitQueue.REASON_MISSING_UNIT_ID],
		},
		"content": {
			"units_file": "packages/game-content/normalized/units.json",
			"buildings_file": "packages/game-content/normalized/buildings.json",
			"duration_field": UnitQueue.SPEEDUP_FIELD,
			"units": coverage.get("units", {}),
			"buildings": coverage.get("buildings", {}),
			"coverage_note": "sm_training_time is a SOUL-MIXER field, not a "
				+ "general training duration, and the coverage above is "
				+ "measured by the suite from the verified registry rather "
				+ "than trusted from prose. It is recorded as CONTENT and "
				+ "applied as no rule: no queue branch reads either duration "
				+ "field (design D5)",
			"training_time_opposite": "training_time is the opposite: a "
				+ "positive one on 130 of the 470 committed buildings and on 0 "
				+ "of 429 units, and the target Command Center records "
				+ "training_time 5 with min_level 1 and group_type "
				+ "COMMAND_CENTER",
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
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"map_index": CORPUS_MAP_INDEX,
			"rows": int(corpus.get("rows", 0)),
			"target": {
				"map_key": TARGET_MAP_KEY,
				"item_id": TARGET_ITEM,
				"item_name": TARGET_ITEM_NAME,
				"row": TARGET_ROW,
				"training_time": TARGET_TRAINING_TIME,
				"min_level": TARGET_MIN_LEVEL,
				"group_type": TARGET_GROUP_TYPE,
				"attr_before": {},
				"target_rule": "the committed corpus's own REAL placed "
					+ "training producer, with an EMPTY attribute bag, so both "
					+ "queue commands are exercisable with NO fabricated player "
					+ "state",
			},
			"queue_keys_carried": (corpus.get("carried_keys", []) as Array)
				.duplicate(),
			"resources": corpus.get("resources", {}),
			"map_level": _as_int(corpus.get("map_level", null)),
			"owned_expansions": corpus.get("owned_expansions", []),
			"player_store": corpus.get("player_store", {}),
			"bought_units": corpus.get("bought_units", []),
			"claim": "the committed corpus carries NO queue key on any of its "
				+ "%d rows and its only placed producer carries an empty bag. "
				% int(corpus.get("rows", 0))
				+ "That zero is asserted by the suite and is a fact about the "
				+ "corpus, not evidence that a queue can be obtained, seen, or "
				+ "finished",
		},
		"fixture": {
			"directory": FIXTURE_DIR,
			"manifest": FIXTURE_MANIFEST,
			"schema": fixture.get("schema", ""),
			"executed_legacy": true,
			"steps": [
				{"action": "push", "command": UnitQueue.PUSH_COMMAND,
					"attr_before": fixture.get("push_before_attr", {}),
					"attr_after": fixture.get("push_after_attr", {})},
				{"action": "pop", "command": UnitQueue.POP_COMMAND,
					"attr_before": fixture.get("pop_before_attr", {}),
					"attr_after": fixture.get("pop_after_attr", {})},
			],
			"rows_unchanged": int(fixture.get("rows", 0)),
			"resources": fixture.get("resources", {}),
			"resources_unchanged": true,
			"completion_captured": bool(fixture.get("completion_captured",
				true)),
			"completion_command_exists": bool(fixture.get(
				"completion_command_exists", true)),
			"completion_note": "a PUSH and a POP were captured and NO "
				+ "COMPLETION WAS CAPTURED, because the legacy server has no "
				+ "completion command at all. The fixture therefore evidences a "
				+ "push and a pop ONLY and says nothing about a finished queue; "
				+ "the missing completion is on the record here rather than left "
				+ "for a reader to find",
			"proof": "two-part: the recorded bag matches the DERIVED result "
				+ "(exact count, stamped instant by shape and direction, and "
				+ "the three-key teardown by presence) AND every stored resource "
				+ "is byte-identical. The 'nothing moved' half is what makes the "
				+ "neutral-vector claim non-tautological",
			"fabricated_state": false,
			"fixture_scope": "one recorded push and one recorded pop against "
				+ "the fresh-player corpus: no progressed save and no other "
				+ "command",
		},
		"intents": {
			"operations": ["push_queue_unit_town(user_id, map_key)",
				"pop_queue_unit_town(user_id, map_key)"],
			"argument_count": 2,
			"carries": ["user_id", "map_key"],
			"carries_not": ["count", "cost", "price", "duration", "training "
				+ "time", "readiness", "progress", "outcome",
				"resources_changed"],
			"argument_count_rule": "each operation takes EXACTLY the save "
				+ "identity and the target row's key, so there is NO parameter "
				+ "through which a client could send a count, a cost, a "
				+ "duration, or a readiness: the structural form of the "
				+ "'a client-supplied outcome is ignored' claim, asserted by the "
				+ "suite from the facade's own method list",
			"ignored_server_side": "any cost, duration, count, or readiness "
				+ "key the service receives alongside the identity is ignored, "
				+ "exactly as the collect and expand endpoints ignore "
				+ "client-supplied amounts and prices",
			"vector": "NEUTRAL, because a queue's price is a client-sent delta: "
				+ "the legacy dispatcher applies the request's per-command vector "
				+ "BEFORE the branch (command.py:40, engine.py:251-271), so any "
				+ "price a client attached would be a client-trusted mint or "
				+ "burn",
			"action_vocabulary": (BootData.QUEUE_ACTIONS as Array).duplicate(),
			"endpoint": "POST /v0/queue, named only inside the legacy-v0 "
				+ "implementation",
			"no_atom_fusion_intent": "push_queue_unit2 is deliberately NOT "
				+ "derivable from any action: its unit id is a client-supplied "
				+ "argument no evidence constrains (design D7)",
		},
		"provenance": UnitQueue.PROVENANCE,
		"non_claims": UnitQueue.NON_CLAIMS,
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


## The suite's OWN unit resolver, independent of any surface's, so the model is
## exercised against a resolver the suite controls.
func _resolver(registry: Variant) -> Callable:
	return func(id_text: String) -> Dictionary:
		var resolved: Dictionary = registry.get_entry(
			UnitQueue.UNIT_DOMAIN, id_text)
		if not bool(resolved.get("found", false)):
			return {"ok": false, "error": "no committed unit definition for "
				+ "item id %s" % id_text}
		var parsed := UnitDefinition.parse(resolved["entry"])
		if not bool(parsed.get("ok", false)):
			return {"ok": false, "error": str(parsed.get("error", ""))}
		return {"ok": true, "name": str(parsed["definition"].name)}


## The start instant the committed executed push stamped, read out of that
## capture. The legacy branch stamps `timestamp_now()`, so the committed fixture
## is the only authority for the value: reading it here means a re-capture moves
## every assertion in this suite with it, and 0 (the fail-closed answer) means
## the capture recorded none — which the branch always does, so that is a
## fixture defect rather than a state this contract can reach.
func _recorded_stamp() -> int:
	var push_after := _fixture_state(FIXTURE_PUSH_DIR, "after")
	if push_after.is_empty():
		fail("the committed queue fixture's push after state is readable")
		return 0
	var bag: Dictionary = _attr_of(push_after, TARGET_KEY)
	var stamp: Variant = bag.get(UnitQueue.KEY_START, null)
	if not (stamp is int) or int(stamp) <= 0:
		fail("the executed queue push recorded a positive start instant")
		return 0
	check_eq(int(bag.get(UnitQueue.KEY_COUNT, -1)), 1,
		"the executed queue push recorded exactly the derived count of 1")
	check_eq((bag.keys() as Array).size(), 2,
		"the executed queue push wrote exactly nu and ts, never a ui")
	return int(stamp)


## One committed save state out of a fixture step, by file name.
func _fixture_state(directory: String, file_name: String) -> Dictionary:
	var document: Variant = _read_json(Paths.repo_root().path_join(
		directory + "/" + file_name + ".json"))
	if not (document is Dictionary):
		fail("the %s state of %s is readable JSON"
			% [file_name, directory])
		return {}
	return document as Dictionary


## One addressed row's committed attribute bag with its numbers canonicalised to
## integers, or {} when the row is absent. The pinned engine's JSON parser widens
## every committed number to a float, so a raw comparison against a literal bag
## would never hold — this is the documented transport tolerance every delivered
## suite applies to the same field class.
func _attr_of(document: Dictionary, key: String) -> Variant:
	var map: Variant = document["maps"][CORPUS_MAP_INDEX]
	if not (map is Dictionary):
		return {}
	var items: Variant = (map as Dictionary)["items"]
	if not (items is Dictionary) or not (items as Dictionary).has(key):
		return {}
	return _as_int_tree(((items as Dictionary)[key] as Array)[UnitQueue.ATTR_SLOT])


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


## Every row of one placement map except the addressed one is byte-identical
## across the pair, and the placement COUNT never moves.
func _check_rows_unchanged(before: Dictionary, after: Dictionary,
		label: String) -> void:
	var before_items: Dictionary = before["maps"][CORPUS_MAP_INDEX]["items"]
	var after_items: Dictionary = after["maps"][CORPUS_MAP_INDEX]["items"]
	check_eq(after_items.size(), before_items.size(),
		"%s left the placement count at %d" % [label, before_items.size()])
	var differing: Array = []
	for key: Variant in before_items.keys():
		if not after_items.has(key) or after_items[key] != before_items[key]:
			differing.append(str(key))
	check_eq(differing, [TARGET_KEY],
		"%s changed exactly one row - the addressed one - and left every other "
			% label + "of the %d committed rows byte-identical"
			% before_items.size())


## Every stored resource is byte-identical across the pair, which is what makes
## the neutral-vector claim non-tautological.
func _check_resources_unchanged(before: Dictionary, after: Dictionary,
		label: String) -> void:
	check_eq(_corpus_resources(after), _corpus_resources(before),
		"%s left EVERY stored resource byte-identical: a queue moves none, so "
			% label
			+ "the derived neutral vector's own guarantee is proven by value")
	var before_map: Dictionary = before["maps"][CORPUS_MAP_INDEX]
	var after_map: Dictionary = after["maps"][CORPUS_MAP_INDEX]
	var moved: Array = []
	for key: Variant in before_map.keys():
		if key == "items":
			continue
		if after_map.get(key, null) != before_map[key]:
			moved.append(str(key))
	check_eq(moved, [],
		"%s moved no other map field either" % label)


## The storage, the bought-units bookkeeping, the private state, and the player
## info are byte-identical across the pair.
func _check_untouched(before: Dictionary, after: Dictionary,
		label: String) -> void:
	check_eq(after["playerInfo"], before["playerInfo"],
		"%s left the player info byte-identical" % label)
	check_eq(after["privateState"], before["privateState"],
		"%s left the whole private state byte-identical" % label)


## The seven stored balances of one committed save, as integers.
func _corpus_resources(document: Variant) -> Dictionary:
	if not (document is Dictionary):
		return {}
	var map: Dictionary = (document as Dictionary)["maps"][CORPUS_MAP_INDEX]
	var info: Dictionary = (document as Dictionary)["playerInfo"]
	var priv: Dictionary = (document as Dictionary)["privateState"]
	return {
		"xp": _as_int(map.get("xp")),
		"gold": _as_int(map.get("gold")),
		"wood": _as_int(map.get("wood")),
		"oil": _as_int(map.get("oil")),
		"steel": _as_int(map.get("steel")),
		"cash": _as_int(info.get("cash")),
		"mana": _as_int(priv.get("mana")),
	}


## One committed field's coverage across a whole domain, measured from the
## verified registry: how many entries carry it, how many do not, how many
## distinct values it takes, and its minimum.
func _field_coverage(registry: Variant, domain: String,
		field: String) -> Dictionary:
	var ids: Array = registry.legacy_ids(domain).get("ids", [])
	var with_field := 0
	var values := {}
	var numbers: Array = []
	for id_text: Variant in ids:
		var resolved: Dictionary = registry.get_entry(domain, str(id_text))
		var entry: Variant = resolved.get("entry", null)
		if not (entry is Dictionary):
			continue
		if not (entry as Dictionary).has(field):
			continue
		with_field += 1
		var value: Variant = (entry as Dictionary)[field]
		values[str(value)] = true
		var number: Variant = BootData._parse_int(value)
		if number != null and int(number) >= 0:
			numbers.append(int(number))
	numbers.sort()
	return {
		"domain": domain,
		"field": field,
		"of": ids.size(),
		"with_field": with_field,
		"missing": ids.size() - with_field,
		"distinct_values": values.size(),
		"minimum": numbers[0] if not numbers.is_empty() else 0,
		"maximum": numbers[numbers.size() - 1] if not numbers.is_empty()
			else 0,
	}


## One entry of the facade's own method list, or null.
func _method(methods: Variant, name: String) -> Variant:
	for entry: Variant in methods as Array:
		if not (entry is Dictionary):
			continue
		if str((entry as Dictionary).get("name", "")) == name:
			return entry
	return null


## Whether an object exposes a counter with the given name.
func _has_counter(object: Variant, name: String) -> bool:
	for entry: Variant in object.get_property_list():
		if str(entry.get("name", "")) == name:
			return true
	return false


## A class's declared property names, as a sorted set.
func _class_members(script: Variant) -> Array:
	var out: Array = []
	for entry: Variant in script.get_script_property_list():
		out.append(str(entry.get("name", "")))
	out.sort()
	return out


## Whether a list of sentences contains the given phrase, as a substring.
func _contains_phrase(lines: Variant, phrase: String) -> bool:
	for line: Variant in lines as Array:
		if str(line).contains(phrase):
			return true
	return false


## Every `.gd` source's DECLARATIONS: comment lines are dropped and
## string-literal content is blanked, so a prose mention or a recorded non-claim
## string can never be mistaken for code.
func _code_only_path(res_path: String) -> String:
	var lines := FileAccess.get_file_as_string(res_path).split("\n")
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


## The public and private function names a module declares, sorted, from its own
## source: the check that a readiness or cost helper cannot hide.
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


func _source(res_path: String) -> String:
	return FileAccess.get_file_as_string(res_path)


## Every script a module loads, in committed order, read from its own `preload`
## declarations: the check that neither delivered module reaches content or the
## transport behind the projection's back.
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


func _sorted_array(values: Variant) -> Array:
	var out: Array = []
	for value: Variant in values:
		out.append(value)
	out.sort()
	return out


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


## One addressed row out of a live bootstrap payload with its numbers
## canonicalised to integers, or [].
func _live_row(payload: Dictionary, key: String) -> Variant:
	var map: Variant = payload.get("map", null)
	if map == null or not (map is Dictionary):
		return []
	var items: Variant = (map as Dictionary).get("items", null)
	if items == null or not (items is Dictionary):
		return []
	return _as_int_tree(((items as Dictionary).get(key, []) as Array))


## The live payload's seven stored balances, as integers — the pre-request
## reference the live value-level proof compares against, read from the service's
## own state and never from the fake's fixture.
func _live_resources(payload: Dictionary) -> Dictionary:
	var map: Dictionary = payload.get("map", {}) as Dictionary
	var player: Dictionary = payload.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = payload.get("privateState", {}) as Dictionary
	return {
		"xp": int(map.get("xp", 0)),
		"gold": int(map.get("gold", 0)),
		"wood": int(map.get("wood", 0)),
		"oil": int(map.get("oil", 0)),
		"steel": int(map.get("steel", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(priv.get("mana", 0)),
	}


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
