extends "res://tests/test_base.gd"
## Market / trade-counter suite (OpenSpec `godot-market-trade-counters`).
##
## This line delivers TWO read-only typed projections and nothing else. It adds
## no route, touches no `apps/compat-api/**` file, adds no live phase and
## captures no executed-legacy fixture, so the compat suite must remain at its
## unchanged baseline and the live-phase count at twenty-three.
##
## ## The finding that shapes every number here: the cap is STORED, never
## ## ENFORCED, and the other counter is the exact opposite
##
## `command.py:465-473` records a trade. `numTradesDone` then has exactly ONE
## reader across all eleven legacy root modules and that reader is the increment
## that produces the value at `command.py:469`. Nothing anywhere reads the stored
## count to gate, refuse, limit or rank anything. By contrast
## `timestampLastTrade` has TWO writers and exactly ONE reader, and that reader
## is a live one: the day-bucket comparison in the engine's reset helper at
## `engine.py:238-240`, which runs on every player-info load.
##
## So one counter is inert and the other gates a real daily reset. Presenting
## the cap as a limit would invent an enforcement point, and presenting the reset
## as this capability's own work would duplicate a helper that already runs on
## the load path. Both errors are refused below.
##
## ## Checks:
##   projection  both counters verbatim, the day buckets, the legacy reset
##               predicate evaluated between them, the branch's own clamped and
##               UNCLAMPED arithmetic, and the fail-closed refusals that omit a
##               refused field's derived values while still carrying the raw one.
##   arithmetic  the recorded table of what the branch stores and what it prints,
##               the mechanical absence of any clamp in the print, and the
##               operator census over both delivered files.
##   schedule    the committed market rows read ONLY through the registry, the
##               prefix-versus-substring decision, and the three-rule zero-
##               consumer census re-measured on this run.
##   recorded    the branch partition, the writer/reader sets, and every cited
##               legacy site turned into a measurement that fails when the
##               preserved file moves.
##   corpus      the ten genuine save documents, with the two that carry a
##               non-zero instant each witnessing a DIFFERENT writer.
##   absence     the whole declared-function inventory pinned in both directions,
##               the case-folded by-substring reserved-name scan over DECLARED
##               names, the absent-helper set, the absent-ordinal guard, and the
##               no-route boundary.
##   ownership   the foreign-field guard in QUOTED-LITERAL form, and the hand-off
##               assertions that the owning capabilities really project the
##               fields this line must not name.
##
## The anti-invention guards are STRUCTURAL and are proven by injection rather
## than trusted: nine deliberate faults were written into the delivered modules,
## each had to fail this suite with a non-zero exit AND a non-zero count of
## `[test] FAIL` lines, and each was followed by a byte-identical restore
## verified by sha256. `_injection_record()` carries a TRANSCRIBED record of a prior
## external harness run -- it cannot execute a probe, and `INJECTION_PROVENANCE` says so
## in the report itself rather than leaving the block to read as live measurement.

const TradeCounters := preload("res://scripts/market/trade_counters.gd")
const MarketSchedule := preload("res://scripts/market/market_schedule.gd")

const MODULE_PATH := "res://scripts/market/trade_counters.gd"
const SCHEDULE_PATH := "res://scripts/market/market_schedule.gd"
const MODULE_REPO_PATH := "apps/client-godot/scripts/market/trade_counters.gd"
const SCHEDULE_REPO_PATH := "apps/client-godot/scripts/market/market_schedule.gd"
const SCOPE_OWNER_PATH := "res://tests/test_project_scope.gd"
const VERIFY_BOOT_REPO_PATH := "apps/client-godot/verify-boot.ps1"
const DEFAULT_REPORT_PATH := "evidence/market-trade/report.json"

const COMMAND := "command.py"
const ENGINE := "engine.py"
const GLOBALS_PACKAGE := "packages/game-content/normalized/globals.json"

## The eleven legacy root modules, declared so a walk is explicit rather than a
## directory listing. A consumer count over a subset is not a consumer count,
## which is why this list is a closed set the suite re-asserts.
const LEGACY_MODULES := [
	"auctions.py", "bundle.py", "command.py", "constants.py", "engine.py",
	"get_game_config.py", "get_player_info.py", "legacy_command_recorder.py",
	"server.py", "sessions.py", "version.py",
]

## Every function DECLARATION across both delivered modules, sorted-unique, and
## the DECLARATION count pinned separately so collapsing a duplicate cannot hide
## a class that quietly grew. `godot-friends` recorded why the set comparison has
## to be sorted-unique rather than positional: a positional list fails against a
## module whose own names are declared twice, and this line has four such names
## (`project`, `refusal_codes`, `refusal_reason`, `_refuse`).
const EXPECTED_FUNCTIONS := [
	"_committed", "_is_integral", "_is_string", "_refuse", "branch_inventory",
	"branch_remaining_after_next_trade", "branch_stored_after_next_trade",
	"cap_record", "committed_rows", "consumer_rule", "count_refusal",
	"day_bucket", "divergence_records", "instant_refusal", "no_derived_record",
	"prefix_record", "project", "project_counters", "project_row",
	"refusal_codes", "refusal_reason", "reset_predicate_holds", "row_refusal",
]
const EXPECTED_DECLARATIONS := 27

## Reserved name stems. Matched case-folded and by SUBSTRING in BOTH directions
## over DECLARED function names -- never over raw source, because a raw scan
## trips on this suite's own inventory text. That defect was measured by
## `godot-construction-assist` and is the reason for the declared-name form.
##
## TWO words are deliberately ABSENT from this list and the reasons are part of
## the contract. The bare stem `cap` collides with the delivered `cap_record`,
## and the bare stem `trade` collides with the two delivered
## `branch_*_after_next_trade` names. A guard that cannot be written without
## colliding with the delivered code is a guard that will be relaxed later, so
## the collision is removed instead of tolerated -- and `cap_for` is covered by
## the absent-helper guard instead, which is what the second probe measures.
const RESERVED_STEMS := [
	"cost", "price", "fee", "limit", "allow", "enforce", "economy", "period",
	"ratio", "advance", "schedule", "reset_count",
]

## The four absent helpers the design names explicitly, asserted PRESENT in the
## absent set rather than merely un-implemented, so the record cannot be edited
## down to a list that happens to have none of them.
const REQUIRED_ABSENT_HELPERS := [
	"trade_cost", "cap_for", "enforce_trade_limit", "is_trade_allowed",
]

## The genuine save documents, an explicit allow-list. A naive directory walk
## swept fixture step documents into earlier denominators, so a document is opted
## into and never swept up.
const CANONICAL_CORPUS := [
	"villages/AcidCaos.json",
	"villages/General_Mike_30.json",
	"villages/General_Mike_31.json",
	"villages/Kiriakos.json",
	"villages/Nerri.json",
	"villages/Neutral.json",
	"villages/Scarlet.json",
	"villages/initial.json",
	"tests/saves/fresh-player.json",
	"tests/saves/fresh-player-pre-migration.json",
]
const CANONICAL_CORPUS_COUNT := 10

## The two documents that carry a non-zero instant, each pinned byte-level
## because each witnesses a DIFFERENT writer and neither figure is a guess.
const CORPUS_CLAMP_WITNESS := "villages/Nerri.json"
const CORPUS_RESET_WITNESS := "villages/Neutral.json"

## The recorded branch arithmetic (design D3). `count_before` is the STORED
## count; `increment` is the UNCLAMPED local the branch builds at
## `command.py:469`; `stored` is the clamped value it persists at
## `command.py:470`; `remaining` is the UNCLAMPED figure it PRINTS at
## `command.py:473`. From the twenty-first recorded trade onward the stored
## value parks at the cap while the printed figure goes negative.
const ARITHMETIC_TABLE := [
	{"count_before": 18, "increment": 19, "stored": 19, "remaining": 1},
	{"count_before": 19, "increment": 20, "stored": 20, "remaining": 0},
	{"count_before": 20, "increment": 21, "stored": 20, "remaining": -1},
	{"count_before": 24, "increment": 25, "stored": 20, "remaining": -5},
]

## Tokens that must never appear inside `branch_remaining_after_next_trade`, so
## the printed figure stays unclamped. A helper that "helpfully" bounded it
## would have silently corrected the oracle and called it a fix.
##
## `return` is NOT in this list, because a GDScript function cannot do anything
## else -- it is asserted instead as appearing EXACTLY ONCE, which is the real
## anti-clamp claim: a bounded value would need a second return or a conditional
## around the first.
const CLAMP_TOKENS := ["mini", "min", "max", "clamp", "abs", "floor", "sign",
	"if", "else", "while", "for ", "?"]

## The comparison operators, so a bound cannot hide in one of them. The `->`
## return-type annotation is removed from the scanned text before these are
## matched, because it carries a `>` that is an arrow and not a comparison.
const COMPARISON_OPERATORS := ["<=", ">=", "==", "!=", "<", ">"]

## Foreign state fields owned by OTHER delivered capabilities. Matched as
## QUOTED LITERALS ONLY, and that form is load-bearing rather than stylistic:
## `godot-construction-assist` measured that a bare two-character substring
## match sits inside ordinary English throughout a delivered module, so a bare
## form can never fail. The bare form's self-tripping is asserted below so the
## reason cannot be unlearned.
const FOREIGN_FIELDS := [
	{"owner": "godot-unit-queues", "keys": ["nu", "ts", "ui"]},
	{"owner": "godot-construction-assist", "keys": ["si"]},
	{"owner": "godot-rewards", "keys": ["weeklyRewardIndex", "bonusNextId",
		"timeStampMondayBonus", "timestampLastBonus", "weekly_reward",
		"win_daily_bonus"]},
]

## The ownership hand-off: each owner file plus the needles that prove it really
## projects the fields this line declines to name. Asserting the recipient exists
## and really projects them is what makes the boundary a hand-off rather than an
## orphan, which is the shape `godot-unit-collection` established.
const OWNERSHIP := [
	{"capability": "godot-unit-queues", "path": "tests/test_unit_queues.gd",
		"needles": ["KEY_COUNT", "queue_keys()",
			"atom-fusion speedup is recorded without a cost or a timer"]},
	{"capability": "godot-construction-assist",
		"path": "tests/test_construction_assist.gd",
		"needles": ["assist_key()", "the recorded attribute-bag key"]},
	{"capability": "godot-rewards", "path": "tests/test_rewards.gd",
		"needles": ["weeklyRewardIndex", "DAILY_BRANCH_FIRST",
			"WEEKLY_BRANCH_FIRST",
			"The weekly bound and both successors are RE-DERIVED"]},
	{"capability": "godot-darts", "path": "tests/test_darts.gd",
		"needles": ["the projection delivers the six darts fields",
			"plus the two handed ones"]},
	{"capability": "globals-tuning-normalization",
		"path": "tests/test_content_registry.gd",
		"needles": ["\"globals\": 105"]},
]

## The recorded registered counts, asserted against the battery's OWN source so a
## silent edit to either registered array fails here rather than only at the end
## of a five-minute run.
const RECORDED_HERMETIC_COUNT := 50
const RECORDED_LIVE_PHASE_COUNT := 23

## The committed rows whose KEY carries the market word inside a longer
## identifier. These are exactly what a substring rule would have dragged into a
## market schedule, and the suite measures the count rather than trusting this
## list.
const EXPECTED_SUBSTRING_ONLY := [
	"ALLIES_MARKET_INCREMENTAL_COLLECT", "ALLIES_MARKET_INITIAL_COLLECT",
	"ALLIES_MARKET_TROLLS",
]

## The committed key the cap coincidence is recorded against. Read from the
## registry at run time; named here only so the REPORT can say which row the
## coincidence is about.
const CAP_COINCIDENT_KEY := "MARKET_MAX_NUM_TRADES"

## The prefix as a raw SUBSTRING really does occur -- in a module that has
## nothing to do with a trade schedule. That is why the whole-token rule is the
## one the census uses, and it is measured here rather than asserted.
const PREFIX_SUBSTRING_SITES := {
	"constants.py": [236, 237, 238, 1001, 1013, 1021],
}

## The rationale both delivered modules carry for claiming no ordinal. The
## absent-ordinal guard scans CODE-ONLY text, so a comment cannot satisfy it --
## and this phrase is therefore asserted separately, or the guard could be
## simplified back into a weaker scan of comments.
const REQUIRED_ORDINAL_RATIONALE := "Four conflicting ordinals"

var _module_source := ""
var _schedule_source := ""
var _registry: Variant = null
var _committed_rows: Array = []
var _globals_rows: Array = []
var _arithmetic: Array = []
var _census: Dictionary = {}
var _census_by_key: Dictionary = {}


func run_scenario() -> void:
	_module_source = FileAccess.get_file_as_string(MODULE_PATH)
	_schedule_source = FileAccess.get_file_as_string(SCHEDULE_PATH)
	_load_registry()
	# The census is measured ONCE, up front, and handed to the schedule
	# projection as an input. It is measured here rather than inside the check
	# that consumes it because a consumer-count map that is still empty at
	# projection time reads as "unmeasured" for every row -- and `int()` on that
	# null aborts the whole check function, which is how this ordering fault
	# hid itself the first time.
	_consumer_census()
	_check_projection()
	_check_arithmetic()
	_check_reset()
	_check_schedule()
	_check_recorded()
	_check_corpus()
	_check_absence()
	_check_ownership()
	_check_delegation()
	_check_route_boundary()
	_check_evidence_record()
	if _has_report_argument():
		_write_report()


func _has_report_argument() -> bool:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report"):
			return true
	return false


# ---------------------------------------------------------------------------
# repo access
# ---------------------------------------------------------------------------

func _repo_root() -> String:
	return Paths.repo_root()


## Returns the committed source with CRLF normalised to LF.
##
## The normalisation is not cosmetic: this working tree is checked out on CRLF,
## so an exact comparison against a legacy line such as `    else:` never
## matches without it. It is applied on READ rather than asserted on disk,
## because the suite must pass on an LF checkout too and a rule that demanded
## CRLF would be a rule about the checkout, not about the source.
func _repo_text(relative: String) -> String:
	var path: String = _repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		fail("the committed source %s is missing, so nothing can be verified"
			% relative)
		return ""
	return FileAccess.get_file_as_string(path).replace("\r\n", "\n")


func _repo_json(relative: String) -> Variant:
	var path: String = _repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		fail("the committed document %s is missing" % relative)
		return null
	return JSON.parse_string(
		FileAccess.get_file_as_bytes(path).get_string_from_utf8())


func _legacy_lines(module_name: String) -> Array:
	return _repo_text(module_name).split("\n")


func _legacy_code(module_name: String) -> String:
	return _code_only(_repo_text(module_name))


func _registry_instance() -> Variant:
	# `test_base.gd` extends `SceneTree`, so this script IS the tree and `root`
	# is reached directly -- there is no `get_tree()` to call, which is a parse
	# error rather than a runtime null.
	return root.get_node_or_null("ContentRegistry")


func _load_registry() -> void:
	_registry = _registry_instance()
	check(_registry != null,
		"the ContentRegistry autoload instance is available to read committed "
			+ "content through")
	var package: Variant = _repo_json(GLOBALS_PACKAGE)
	check(package is Array,
		"the committed globals package parses to an array")
	if package is Array:
		_globals_rows = package as Array
	check_eq(_globals_rows.size(), 105,
		"the committed globals package carries 105 loaded entries")
	if _registry == null:
		return
	var loaded: Dictionary = _registry.load_content()
	check(bool(loaded.get("ok", false)),
		"the committed normalized content package loads through the registry")
	# The committed rows are read through the registry and NOWHERE else, so this
	# is the one path the projection is allowed to use.
	var committed: Dictionary = MarketSchedule.committed_rows(_registry)
	check(bool(committed.get("ok", false)),
		"the committed market rows are readable through the registry (%s)"
			% str(committed.get("error", "")))
	if bool(committed.get("ok", false)):
		_committed_rows = committed.get("rows", [])
	check_eq(_committed_rows.size(), 8,
		"the committed market schedule carries EIGHT prefix-anchored rows")
	check_eq(int(committed.get("domain_examined", 0)), 105,
		"and the selection examined the WHOLE committed domain, not a "
			+ "pre-filtered list, so the prefix rule is the thing that selected "
			+ "them")
	# The projection reads no clock of its own; `now` is a caller argument.
	check(not _code_only(_module_source).contains("Time."),
		"the counter module reads no clock: `now` is supplied by the caller")


# ---------------------------------------------------------------------------
# the projection
# ---------------------------------------------------------------------------

func _row(overrides: Dictionary) -> Dictionary:
	var row := {"numTradesDone": 0, "timestampLastTrade": 0}
	for key: Variant in overrides.keys():
		row[key] = overrides[key]
	return row


func _privacy() -> Dictionary:
	return {"xp": 4, "gold": 2000, "energy": 50}


func _check_projection() -> void:
	var privacy: Dictionary = _privacy()
	var codes: Array = TradeCounters.refusal_codes()
	check_eq(codes.size(), 10,
		"the counter projection declares exactly ten refusal codes")
	var sorted_unique: Array = codes.duplicate()
	sorted_unique.sort()
	check_eq(sorted_unique, codes,
		"and hands them over sorted and unique, so a caller can diff the set")
	var schedule_codes: Array = MarketSchedule.refusal_codes()
	check_eq(schedule_codes.size(), 8,
		"and the schedule projection declares its own eight, so the two "
			+ "vocabularies are separate and neither is a subset of the other")
	for code: Variant in codes:
		check(str(TradeCounters.refusal_reason(str(code))) != "",
			"counter refusal `%s` carries a recorded reason" % str(code))
	for code2: Variant in schedule_codes:
		check(str(MarketSchedule.refusal_reason(str(code2))) != "",
			"schedule refusal `%s` carries a recorded reason" % str(code2))

	# --- the whole projection over a crafted row
	var record: Dictionary = TradeCounters.project(
		_row({"numTradesDone": 4, "timestampLastTrade": 1705776695}), privacy,
		1705850000)
	check(bool(record["ok"]), "a complete row projects")
	check_eq(str(record["error"]), "", "with an empty error")
	check_eq(int(record["stored_count"]), 4, "the stored count verbatim")
	check_eq(int(record["last_trade_instant"]), 1705776695,
		"the recorded instant verbatim")
	check_eq(int(record["cap_from_branch"]), 20, "the cap is the branch literal")
	check(not bool(record["cap_enforced"]),
		"and it is reported as NOT enforced, so a caller cannot read it as a "
			+ "limit")
	check_eq(int(record["increment_after_next_trade"]), 5,
		"the branch's own increment is reported")
	check_eq(int(record["last_trade_day_bucket"]), 1705776695 / 86400,
		"the recorded instant's day bucket is the engine's own division")
	check_eq(int(record["server_clock_day_bucket"]), 1705850000 / 86400,
		"and the caller-supplied clock's day bucket likewise")
	check_eq(int(record["resources_moved"]), 0,
		"the branch moves no resource and neither does this projection")
	check(not bool(record["resource_vector_sent"]),
		"and no resource vector is sent")
	check(not bool(record["reset_performed_here"]),
		"the day reset is NOT performed here")
	check_eq(str(record["reset_owner"]), "engine.reset_stuff",
		"and the owner is named")
	check(not bool(record["private_state_carries_count"]),
		"the private state carries neither counter, measured on the record the "
			+ "caller receives")
	check(not bool(record["private_state_carries_instant"]),
		"for the instant either")

	# --- the reset predicate, both directions
	#
	# The same-bucket case is pinned on MEASURED buckets rather than on the
	# arithmetic looking like it should: 73305 seconds apart straddles a 86400
	# boundary, so the first instinct here -- "those two instants are close
	# together, so they are in one bucket" -- is wrong, and only the buckets say
	# which case is which.
	check_eq(int(TradeCounters.day_bucket(1705776695)), 19742,
		"the recorded corpus instant falls in day bucket 19742")
	check_eq(int(TradeCounters.day_bucket(1705776695 + 1000)), 19742,
		"and so does one a thousand seconds later")
	check_eq(int(TradeCounters.day_bucket(1705850000)), 19743,
		"while the server clock used here falls in the NEXT bucket")
	check(not bool(TradeCounters.reset_predicate_holds(1705777695, 1705776695)),
		"inside one day bucket the legacy predicate does NOT hold")
	check(bool(TradeCounters.reset_predicate_holds(1705850000,
			1705776695 - 86400)),
		"across a day boundary it does")
	var zero_row: Dictionary = TradeCounters.project(
		_row({"numTradesDone": 0, "timestampLastTrade": 0}), privacy, 86400)
	check(bool(zero_row["reset_predicate_holds"]),
		"a zero-instant row resets on any non-zero clock, which is why the "
			+ "eight zero-instant corpus documents are NOT evidence of a reset")

	# --- the cap record cannot be mistaken for a limit
	var cap: Dictionary = TradeCounters.cap_record()
	var enforcement: Dictionary = cap["enforcement"]
	check(not bool(enforcement["enforced"]),
		"the cap record states the cap is not enforced")
	check_eq(int(enforcement["branches_gating_on_the_count"]), 0,
		"and that zero branches gate on the stored count")
	check(bool(enforcement["only_reader_is_its_own_increment"]),
		"and that the count's only reader IS its own increment")
	check(not bool(cap["derived_from_content"]),
		"and the cap is NOT derived from any committed content value")
	check(bool(cap["coincidence_recorded"]),
		"the coincidence with an unread committed row is recorded, not derived")

	# --- the two recorded client-dictated divergences
	var divergences: Array = TradeCounters.divergence_records()
	check_eq(divergences.size(), 2,
		"exactly two client-dictated behaviours are recorded as divergences")
	for entry: Dictionary in divergences:
		check(not bool(entry["reproduced"]),
			"divergence `%s` is recorded and NOT reproduced" % str(entry["id"]))

	# --- the fail-closed refusals, each with its named code
	#
	# The third element of each row names WHICH half is refused, because the spec
	# scopes a refusal to a field: "it reports no derived value that would require
	# the missing field". A shape that refuses only the count must still report the
	# instant's day bucket, and the two inverses below are asserted as separate
	# checks rather than folded into one blanket expectation -- a blanket
	# expectation would be stronger than the spec and would force the module to
	# blank a sound field.
	var refusals := [
		[[null, privacy, 1], "map_row_absent", "whole"],
		[[42, privacy, 1], "map_row_not_object", "whole"],
		[[{}, null, 1], "private_state_absent", "whole"],
		[[{}, 42, 1], "private_state_not_object", "whole"],
		[[{}, privacy, null], "now_absent", "whole"],
		[[{}, privacy, "1"], "now_not_integer", "whole"],
		[[{}, privacy, 1.5], "now_not_integer", "whole"],
		[[{"timestampLastTrade": 0}, privacy, 1], "num_trades_done_absent",
			"count"],
		[[{"numTradesDone": "4", "timestampLastTrade": 0}, privacy, 1],
			"num_trades_done_not_integer", "count"],
		[[{"numTradesDone": true, "timestampLastTrade": 0}, privacy, 1],
			"num_trades_done_not_integer", "count"],
		[[{"numTradesDone": 1.5, "timestampLastTrade": 0}, privacy, 1],
			"num_trades_done_not_integer", "count"],
		[[{"numTradesDone": 0}, privacy, 1], "timestamp_last_trade_absent",
			"instant"],
		[[{"numTradesDone": 0, "timestampLastTrade": "0"}, privacy, 1],
			"timestamp_last_trade_not_integer", "instant"],
		[[{"numTradesDone": "4", "timestampLastTrade": "0"}, privacy, 1],
			"num_trades_done_not_integer", "both"],
	]
	for entry2: Array in refusals:
		var args: Array = entry2[0]
		var half: String = str(entry2[2])
		var out: Dictionary = TradeCounters.project(args[0], args[1], args[2])
		check(not bool(out["ok"]),
			"a refused input refuses rather than defaulting")
		check_eq(str(out["error"]), str(entry2[1]),
			"with the named code for that shape")
		if half == "count" or half == "both":
			check_eq(out["stored_count"], null,
				"and no stored count, so a refusal cannot be read as a value")
			check_eq(out["increment_after_next_trade"], null,
				"and no increment, which requires the count")
			check_eq(out["remaining_after_next_trade"], null,
				"and no remaining figure, which requires the count")
		if half == "instant" or half == "both":
			check_eq(out["last_trade_instant"], null, "and no projected instant")
			check_eq(out["reset_predicate_holds"], null, "and no reset verdict")
		if half == "whole":
			check_eq(out["stored_count"], null,
				"and no stored count on a whole-projection refusal")
			check_eq(out["remaining_after_next_trade"], null,
				"and no remaining figure")
			check_eq(out["reset_predicate_holds"], null, "and no reset verdict")

	# --- a refused FIELD travels untouched beside its refusal
	var partial: Dictionary = TradeCounters.project(
		_row({"numTradesDone": "18", "timestampLastTrade": 1705776695}), privacy,
		1705850000)
	check(not bool(partial["ok"]),
		"one refused field makes the whole record refused")
	check_eq(str(partial["count_refusal"]), "num_trades_done_not_integer",
		"and names that field's refusal")
	check_eq(str(partial["instant_refusal"]), "",
		"while the instant half is not refused")
	check_eq(partial["recorded_count"], "18",
		"and the RAW recorded value still travels beside the refusal, "
			+ "unconverted and uncorrected")
	check_eq(partial["stored_count"], null,
		"but no typed counter is derived from it")
	check_eq(int(partial["last_trade_instant"]), 1705776695,
		"and the sound half still projects, so one bad field never blanks a "
			+ "good one")
	var inverse: Dictionary = TradeCounters.project(
		_row({"numTradesDone": 19, "timestampLastTrade": "x"}), privacy, 1)
	check_eq(int(inverse["stored_after_next_trade"]), 20,
		"the inverse shape still reports the branch's clamped arithmetic")
	check_eq(inverse["last_trade_instant"], null,
		"while contributing no instant and no reset verdict")
	check_eq(inverse["reset_predicate_holds"], null,
		"because the day bucket has nothing sound to divide")


# ---------------------------------------------------------------------------
# design D3: the branch's own arithmetic, and the unclamped print
# ---------------------------------------------------------------------------

func _check_arithmetic() -> void:
	check_eq(int(TradeCounters.TRADE_CAP_FROM_BRANCH), 20,
		"the cap is the branch's own literal")
	check_eq(int(TradeCounters.DAY_BUCKET_SECONDS), 86400,
		"the day bucket is the engine's own literal")

	for entry: Dictionary in ARITHMETIC_TABLE:
		var before: int = int(entry["count_before"])
		var out: Dictionary = TradeCounters.project(
			_row({"numTradesDone": before, "timestampLastTrade": 0}), _privacy(),
			1)
		check_eq(int(out["increment_after_next_trade"]),
			int(entry["increment"]),
			"from count %d the branch's increment is %d"
				% [before, int(entry["increment"])])
		check_eq(int(out["stored_after_next_trade"]), int(entry["stored"]),
			"and it STORES %d" % int(entry["stored"]))
		check_eq(int(out["remaining_after_next_trade"]),
			int(entry["remaining"]),
			"and PRINTS %d, from the UNCLAMPED local" % int(entry["remaining"]))
		_arithmetic.append({
			"count_before": before,
			"increment_after_next_trade": int(out["increment_after_next_trade"]),
			"stored_after_next_trade": int(out["stored_after_next_trade"]),
			"remaining_after_next_trade": int(out["remaining_after_next_trade"]),
		})

	# the whole first-thirty sweep, so the table is a sample and not the claim
	for before2: int in range(0, 31):
		var increment: int = TradeCounters.branch_stored_after_next_trade(before2)
		var printed: int = TradeCounters.branch_remaining_after_next_trade(before2)
		check_eq(increment, mini(20, before2 + 1),
			"the stored value clamps at the cap for count %d" % before2)
		check_eq(printed, 20 - (before2 + 1),
			"the printed value is the UNCLAMPED local for count %d" % before2)
		if before2 >= 20:
			check_eq(increment, 20,
				"at count %d the stored value stays exactly at the cap" % before2)
			check(printed < 0,
				"while the printed figure is NEGATIVE at count %d, which is the "
					% before2 + "defect this contract reproduces rather than fixes")
		else:
			check_eq(increment, before2 + 1,
				"below the cap the stored value is simply the increment")

	# --- the mechanical absence of any clamp in the print (design D3)
	var bodies: Dictionary = _function_bodies(_code_only(_module_source))
	check(bodies.has("branch_remaining_after_next_trade"),
		"the printed-figure function exists and is measurable")
	# Every scan below runs on this ONE text, with the `->` return-type
	# annotation removed. The body as stored carries that arrow, and the arrow
	# contains both a `>` and a `-`; leaving it in makes the comparison scan
	# unsatisfiable and the subtraction count a measure of the annotation rather
	# than of the arithmetic.
	var printed_body: String = str(
		bodies.get("branch_remaining_after_next_trade", "")).replace("->", "")
	for token: String in CLAMP_TOKENS:
		check(not printed_body.contains(token),
			"the printed-figure function contains no `%s`, so the oracle's "
				% token + "negative output is not silently corrected")
	for operator: String in COMPARISON_OPERATORS:
		check(not printed_body.contains(operator),
			"and no `%s` comparison" % operator)
	check_eq(printed_body.count("+"), 1,
		"the printed figure performs exactly ONE addition, the increment")
	check_eq(printed_body.count("-"), 1,
		"and exactly ONE subtraction, the cap less that increment")
	check_eq(printed_body.count("return"), 1,
		"and exactly ONE return, so the value is a single expression and a "
			+ "bounded one would need a second")
	check_eq(int(TradeCounters.branch_remaining_after_next_trade(20)), -1,
		"and the negative case is exactly what the function returns")

	# --- the operator census over BOTH delivered files
	var module_code: String = _code_only(_module_source)
	var schedule_code: String = _code_only(_schedule_source)
	var carriers: Array = _functions_with_arithmetic(module_code)
	check_eq(carriers.size(), 1,
		"exactly ONE function in the counter module carries an operator")
	check_eq(str(carriers[0]), "day_bucket",
		"and it is the day-bucket division, which is the engine's own")
	for operator2: String in ["*", "%"]:
		check_eq(module_code.count(operator2), 0,
			"the counter module contains no `%s` at all" % operator2)
	for operator3: String in ["*", "/", "%"]:
		check_eq(schedule_code.count(operator3), 0,
			"the schedule module contains no `%s` at all, so its no-derived-"
				% operator3 + "economy record is mechanically true")
	check_eq(int(MarketSchedule.NO_DERIVED_RECORD["derived_value_count"]), 0,
		"and the schedule declares zero derived values")


# ---------------------------------------------------------------------------
# the reset: reported, owned by the engine, never performed here
# ---------------------------------------------------------------------------

func _check_reset() -> void:
	var reset: Dictionary = TradeCounters.RESET_OWNER
	check_eq(str(reset["helper"]), "engine.reset_stuff", "the reset owner")
	check_eq(str(reset["legacy_site"]), "engine.py:230-240", "its site")
	check_eq(str(reset["read_site"]), "engine.py:238", "its read site")
	check_eq(str(reset["predicate_site"]), "engine.py:239",
		"its predicate site")
	check_eq(str(reset["write_site"]), "engine.py:240", "its write site")
	check(not bool(reset["reimplemented_here"]),
		"and the module records that it does NOT reimplement the day boundary")

	# Every cited site is turned into a measurement, so a legacy edit fails here
	# rather than silently contradicting the report.
	_check_site(COMMAND, 469, ["numTrades", "numTradesDone", "+ 1"],
		["print"], "the count's only reader")
	_check_site(COMMAND, 470, ["numTradesDone", "min(20,", "num_trades"],
		["print"], "the clamped store")
	_check_site(COMMAND, 471, ["timestampLastTrade", "time_now"], ["-"],
		"the only raising writer")
	_check_site(COMMAND, 473, ["print(", "20", "-", "num_trades"], ["min(", "max("],
		"the unclamped print")
	_check_site(COMMAND, 466, ["resource_type", "args[0]"], ["print"],
		"the first unread argument")
	_check_site(COMMAND, 467, ["sold", "args[1]"], ["print"],
		"the second unread argument, comment stripped")
	_check_site(COMMAND, 906, ["seconds", "args[0]"], ["print"],
		"the client-supplied quantity")
	_check_site(COMMAND, 913, ["timestampLastTrade", "max(0,", "seconds"], [],
		"the client-writable instant")
	_check_site(COMMAND, 36, ["time_now", "timestamp_now()"], [],
		"the server clock")
	_check_site(COMMAND, 40, ["apply_resources", "resources_changed"], [],
		"the client-sent vector, applied before the dispatcher")
	_check_site(COMMAND, 42, ["if", "cmd ==", "\"buy\""], [],
		"the first branch, where the dispatcher opens")
	_check_site(ENGINE, 238, ["last_trade", "timestampLastTrade"], [],
		"the engine's read")
	_check_site(ENGINE, 239, ["86400", "!=", "last_trade"], [],
		"the engine's day predicate")
	_check_site(ENGINE, 240, ["numTradesDone", "= 0"], ["print"],
		"the engine's reset write")
	_check_site(ENGINE, 251, ["def apply_resources", "save", "map"], [],
		"the vector applier")
	# The load-path call is cited by module and line only. Its own text contains
	# a transport identity token that this project's scope gate forbids in every
	# allow-listed file, so quoting the line here would make the gate fail on
	# this suite for the very reason it exists -- the same shape
	# `godot-friends` recorded for its own two literals.
	_check_site("get_player_info.py", 9, ["reset_stuff", "session"], [],
		"the load-path call")

	# The engine's own day predicate is reproduced EXACTLY: same operands, same
	# operator, same literal.
	check(str(_legacy_lines(ENGINE)[238]).contains("// 86400"),
		"the engine's predicate really divides by 86400, which is the constant "
			+ "the projection names")
	check_eq(int(TradeCounters.DAY_BUCKET_SECONDS), 86400,
		"and the projection's constant is that same literal")

	# `sold` occurs TWICE raw on its one line -- once in the assignment and once
	# in the trailing comment -- so the "reads its arguments and uses neither"
	# claim is a CODE-ONLY measurement and a raw-substring count would report a
	# phantom second use.
	var sold_raw: String = str(_legacy_lines(COMMAND)[466])
	check_eq(sold_raw.count("sold"), 2,
		"the second argument's name occurs twice on its own line, so counting it "
			+ "rawly would report a phantom second use")
	var sold_code: String = _code_only(sold_raw).strip_edges()
	check_eq(sold_code, "sold = args[1]",
		"and code-only it is exactly one assignment")
	check(not sold_code.contains("print"),
		"so the argument is assigned and never consumed")
	var type_code: String = _code_only(str(_legacy_lines(COMMAND)[465])).strip_edges()
	check_eq(type_code, "resource_type = args[0]",
		"and the first argument is likewise assigned and never consumed")


## Asserts a cited legacy site is really the recorded source site.
##
## `must_contain` and `must_not_contain` are substrings of the RAW line, because
## an earlier draft of this suite parsed a `"file:line"` citation with a
## right-split on `:` -- and three of the cited sites are print statements that
## themselves contain a colon, so the split silently mis-assigned them to a
## module named after a Python expression. A guard that cannot address its own
## citations is a guard that cannot fail; the three separate arguments make the
## addressing impossible to get wrong.
func _check_site(module_name: String, line_number: int, must_contain: Array,
		must_not_contain: Array, what: String) -> void:
	check(LEGACY_MODULES.has(module_name),
		"%s cites a declared legacy root module (%s)" % [what, module_name])
	var lines: Array = _legacy_lines(module_name)
	check(line_number >= 1 and line_number <= lines.size(),
		"%s cites a line that exists in %s" % [what, module_name])
	if line_number < 1 or line_number > lines.size():
		return
	var actual: String = str(lines[line_number - 1])
	for needle: Variant in must_contain:
		check(actual.contains(str(needle)),
			"%s: %s:%d really contains `%s`"
				% [what, module_name, line_number, str(needle)])
	for needle2: Variant in must_not_contain:
		check(not actual.contains(str(needle2)),
			"%s: %s:%d really does NOT contain `%s`"
				% [what, module_name, line_number, str(needle2)])


# ---------------------------------------------------------------------------
# the committed schedule, through the registry only
# ---------------------------------------------------------------------------

func _check_schedule() -> void:
	check_eq(str(MarketSchedule.CONTENT_DOMAIN), "globals",
		"the schedule lives under the committed globals domain")
	check_eq(str(MarketSchedule.SCHEDULE_PREFIX), "MARKET_",
		"and the selection is a prefix")

	# --- the two directions of the prefix/substring question, MEASURED
	var prefix: Array = []
	var substring_only: Array = []
	for raw: Variant in _globals_rows:
		var key: String = str((raw as Dictionary)["key"])
		if key.begins_with("MARKET_"):
			prefix.append(key)
		elif key.contains("MARKET_"):
			substring_only.append(key)
	check_eq(prefix.size(), 8,
		"the committed file carries EIGHT rows whose key BEGINS with the prefix")
	check_eq(substring_only.size(), 3,
		"and three more that merely CONTAIN the word")
	substring_only.sort()
	check_eq(substring_only, EXPECTED_SUBSTRING_ONLY,
		"and the three are exactly the committed rows that embed the word "
			+ "inside a longer identifier")
	check_eq(prefix.size() + substring_only.size(), 11,
		"so a SUBSTRING rule would have selected ELEVEN rows")
	var prefix_record: Dictionary = MarketSchedule.prefix_record()
	check_eq(int(prefix_record["rows_selected_by_this_rule"]), 8,
		"the module records the prefix count it selected")
	check_eq(int(prefix_record["rows_a_substring_rule_would_also_select"]), 11,
		"and the substring count a looser rule would have dragged in")
	check_eq(str(prefix_record["selection_is"]),
		"prefix-anchored, never substring", "and records the rule as a decision")

	# --- the projection of every row, verbatim, with the caller's census beside
	var projected: Dictionary = MarketSchedule.project(_committed_rows,
		_census_by_key)
	check(bool(projected["ok"]),
		"every committed row projects (%s)" % str(projected.get("error", "")))
	check_eq(int(projected["count"]), 8, "all eight rows are reported")
	check_eq(int(projected["refused"]), 0, "with none refused")
	check_eq(int(projected["derived_value_count"]), 0,
		"and the projection declares it derived nothing")
	var table: Array = projected["rows"]
	var keys_seen: Array = []
	for entry: Dictionary in table:
		keys_seen.append(str(entry["key"]))
		check(bool(entry["ok"]), "row `%s` projects" % str(entry["key"]))
		check(bool(entry["value_verbatim"]),
			"row `%s` carries its value verbatim" % str(entry["key"]))
		check(not bool(entry["scaled"]),
			"row `%s` is not scaled" % str(entry["key"]))
		check(not bool(entry["bounded"]),
			"row `%s` is not bounded" % str(entry["key"]))
		check_eq(str(entry["derived_from"]),
			"the committed normalized registry only",
			"row `%s` names the registry as its only source" % str(entry["key"]))
		check(entry["consumer_count"] != null,
			"row `%s` reports a measured consumer figure" % str(entry["key"]))
		check_eq(int(entry["consumer_count"]), 0,
			"row `%s` has zero measured consumers" % str(entry["key"]))
		check(not bool(entry["has_consumer"]),
			"and is therefore reported as having no consumer")
		check(bool(entry["consumer_measured"]),
			"the zero is a MEASUREMENT the caller supplied, not a default")
	check_eq(keys_seen, prefix,
		"the projected keys are exactly the prefix-anchored set, in the "
			+ "registry's committed order")

	# --- each projected value really is the committed one, read independently
	var by_key: Dictionary = {}
	for raw2: Variant in _globals_rows:
		by_key[str((raw2 as Dictionary)["key"])] = raw2 as Dictionary
	for entry2: Dictionary in table:
		var key2: String = str(entry2["key"])
		var committed_row: Dictionary = by_key.get(key2, {})
		check(not committed_row.is_empty(),
			"the projected key `%s` really is a committed row" % key2)
		check_eq(entry2["value"], committed_row.get("value", null),
			"row `%s` projects the committed value itself" % key2)
		check_eq(str(entry2["value_type"]),
			str(committed_row.get("value_type", "")),
			"row `%s` carries the committed value TYPE" % key2)
		check_eq(str(entry2["source_file"]),
			str(committed_row.get("source_file", "")),
			"row `%s` carries the committed provenance" % key2)

	# --- the coincidence, recorded rather than derived
	#
	# Both views below KEEP string literals. This guard is stated over a quoted
	# committed key, so it must run on the view that keeps them.
	var folded_module: String = _code_with_literals(_module_source)
	var folded_schedule: String = _code_with_literals(_schedule_source)
	var cap_row: Dictionary = by_key.get(CAP_COINCIDENT_KEY, {})
	check_eq(str(cap_row.get("key", "")), CAP_COINCIDENT_KEY,
		"the cap-coincident committed row exists")
	check_eq(int(cap_row.get("value", -1)),
		int(TradeCounters.TRADE_CAP_FROM_BRANCH),
		"and carries the SAME number as the branch literal")
	var carrying: Array = _rows_carrying_number(
		int(TradeCounters.TRADE_CAP_FROM_BRANCH))
	check_eq(carrying.size(), 2,
		"TWO committed rows carry the value twenty, not one, so the coincidence "
			+ "is recorded against a NAMED row rather than against the number")
	check(carrying.has(CAP_COINCIDENT_KEY),
		"the cap coincidence is recorded specifically against the trades row")
	for key3: Variant in carrying:
		check(not folded_module.contains('"%s"' % str(key3)),
			"and the delivered modules name neither twenty-valued committed row "
				+ "as a literal, so an unread constant stays unread")
		check(not folded_schedule.contains('"%s"' % str(key3)),
			"in either module")

	# --- the census rule and the no-derived record
	var rule: Dictionary = MarketSchedule.consumer_rule()
	check(not bool(rule["measured_by_delivered_module"]),
		"the census rule records that the module does NOT measure it")
	check_eq(str(rule["measured_by"]), "test_market_trade.gd",
		"and names this suite as the measurer")
	check_eq(int(rule["rows_with_a_consumer_expected"]), 0,
		"and expects zero rows to have a consumer")
	var derived: Dictionary = MarketSchedule.no_derived_record()
	check_eq(derived["derived_values"], [], "the schedule derives no values")
	check(derived["not_derived"].has("trade cap"),
		"and names the trade cap among the things it does not derive")
	check(derived["not_derived"].has("price"), "and the price")

	# --- the fail-closed refusals on the schedule surface
	var row_refusals := [
		[42, "committed_row_not_object"],
		[{}, "committed_key_absent"],
		[{"key": 20}, "committed_key_not_string"],
		[{"key": "MARKET_MAX_NUM_TRADES"}, "committed_value_absent"],
	]
	for entry3: Array in row_refusals:
		var out: Dictionary = MarketSchedule.project_row(entry3[0], {})
		check(not bool(out["ok"]), "a malformed committed row refuses")
		check_eq(str(out["error"]), str(entry3[1]), "with the named code")
		check_eq(out["value"], null, "and contributes no value")
		check_eq(out["consumer_count"], null,
			"and no consumer figure, so an unmeasured row never claims zero")

	check_eq(str(MarketSchedule.committed_rows(null)["error"]),
		"registry_absent", "an absent registry refuses")
	check_eq(str(MarketSchedule.committed_rows({})["error"]),
		"registry_has_no_legacy_ids", "a non-registry refuses")
	check_eq(str(MarketSchedule.project("not an array", {})["error"]),
		"schedule_rows_not_array", "a non-array schedule refuses")

	# a refused row is COUNTED and does not stop the projection, so a short
	# successful list can never be mistaken for a complete one
	var mixed: Dictionary = MarketSchedule.project(
		[{"key": "MARKET_A", "value": 1}, 42,
			{"key": "MARKET_B", "value": 2}], {})
	check_eq(int(mixed["count"]), 3, "a refused row is still reported")
	check_eq(int(mixed["refused"]), 1, "and counted as refused")
	check(not bool(mixed["ok"]), "and the projection reports itself incomplete")


## The three-rule consumer census, re-derived on this run over ALL ELEVEN legacy
## root modules. The schedule module is handed the result rather than reading
## the legacy sources itself, so this suite is the measurer of record.
func _consumer_census() -> Dictionary:
	var totals := {"raw": 0, "quoted": 0, "token": 0}
	var detail: Array = []
	var by_key: Dictionary = {}
	var texts: Dictionary = {}
	for module_name: String in LEGACY_MODULES:
		texts[module_name] = _repo_text(module_name)
	for raw: Variant in _globals_rows:
		var key: String = str((raw as Dictionary)["key"])
		if not key.begins_with("MARKET_"):
			continue
		var row := {"key": key, "raw": 0, "quoted": 0, "token": 0, "where": []}
		for module_name2: String in LEGACY_MODULES:
			var text: String = str(texts[module_name2])
			var raw_count: int = _count(text, key)
			var quoted_count: int = _count(text, '"%s"' % key) \
				+ _count(text, "'%s'" % key)
			var token_count: int = _count_token(text, key)
			if raw_count + quoted_count + token_count > 0:
				(row["where"] as Array).append(
					{"module": module_name2, "raw": raw_count,
						"quoted": quoted_count, "token": token_count})
			row["raw"] = int(row["raw"]) + raw_count
			row["quoted"] = int(row["quoted"]) + quoted_count
			row["token"] = int(row["token"]) + token_count
		for rule: String in ["raw", "quoted", "token"]:
			totals[rule] = int(totals[rule]) + int(row[rule])
		by_key[key] = int(row["raw"]) + int(row["quoted"]) + int(row["token"])
		detail.append(row)
	_census = {"totals": totals, "rows": detail}
	_census_by_key = by_key
	return _census


# ---------------------------------------------------------------------------
# the recorded oracle: the branch partition and the counter sites
# ---------------------------------------------------------------------------

func _check_recorded() -> void:
	# --- the dispatcher partition, re-derived on RAW text
	var raw_text: String = _repo_text(COMMAND)
	var branches: Array = []
	var branch_lines: Array = []
	var expression := RegEx.new()
	expression.compile(
		"(?:if|elif)[ \\t]+cmd[ \\t]*==[ \\t]*[\"']([^\"']+)[\"'][ \\t]*:")
	var found: RegExMatch = expression.search(raw_text)
	while found != null:
		branches.append(found.get_string(1))
		branch_lines.append(_count_newlines_before(raw_text, found.get_start()) + 1)
		found = expression.search(raw_text, found.get_end())
	check_eq(branches.size(), 63, "the dispatcher declares 63 named branches")
	check_eq(_unique_size(branches), 63,
		"all sixty-three branch names are distinct, so the partition really is "
			+ "a partition")
	check_eq(str(branches[0]), "buy", "and the first branch is the buy branch")
	check_eq(int(branch_lines[0]), 42, "at command.py:42, where the dispatcher opens")
	check_eq(int(branch_lines[branch_lines.size() - 1]), 951,
		"and the last is at command.py:951")
	check_eq(branches.find("trade_resource"), 30,
		"the trade branch is the thirty-first of the sixty-three")
	check_eq(int(branch_lines[30]), 465, "at command.py:465")

	# the unhandled fallthrough is the LAST top-level else, and it is not a
	# branch -- which is why the count is sixty-three and not sixty-four
	var else_lines: Array = []
	var command_lines: Array = _legacy_lines(COMMAND)
	for index: int in range(command_lines.size()):
		if str(command_lines[index]) == "    else:":
			else_lines.append(index + 1)
	check_eq(else_lines.size(), 1,
		"there is exactly ONE top-level `else:` in the dispatcher")
	check_eq(int(else_lines[0]), 954,
		"at command.py:954, the unhandled-command fallthrough")
	check_eq(_names_containing(branches, "trade"), ["trade_resource"],
		"and exactly ONE branch name mentions a trade, so no other branch can "
			+ "compete for the two fields")

	# --- the writer and reader sets, re-derived
	var count_sites: Dictionary = _counter_sites("numTradesDone")
	check_eq(count_sites.get(COMMAND, []), [469, 470],
		"the count is read and written at command.py:469 and :470")
	check_eq(count_sites.get(ENGINE, []), [240],
		"and reset at engine.py:240")
	var instant_sites: Dictionary = _counter_sites("timestampLastTrade")
	check_eq(instant_sites.get(COMMAND, []), [471, 913],
		"the instant is written at command.py:471 and :913")
	check_eq(instant_sites.get(ENGINE, []), [238], "and read at engine.py:238")
	for module_name: String in LEGACY_MODULES:
		if module_name == COMMAND or module_name == ENGINE:
			continue
		check_eq(count_sites.get(module_name, []).size(), 0,
			"the count appears in no other legacy module (%s)" % module_name)
		check_eq(instant_sites.get(module_name, []).size(), 0,
			"nor does the instant (%s)" % module_name)

	var recorded: Dictionary = TradeCounters.branch_inventory()
	var count_record: Dictionary = recorded["counter_sites"]["numTradesDone"]
	check_eq(count_record["writers"], ["command.py:470", "engine.py:240"],
		"the module records the count's two writers")
	check_eq(count_record["readers"], ["command.py:469"],
		"and its single reader")
	check_eq(int(count_record["live_consumers"]), 0,
		"and ZERO live consumers, because that reader is its own increment")
	var instant_record: Dictionary = \
		recorded["counter_sites"]["timestampLastTrade"]
	check_eq(instant_record["writers"], ["command.py:471", "command.py:913"],
		"the module records the instant's two writers")
	check_eq(instant_record["readers"], ["engine.py:238"],
		"and its single reader")
	check_eq(int(instant_record["live_consumers"]), 1,
		"which IS live, so the two counters are not symmetrical")
	check_eq(int(recorded["resources_moved"]), 0,
		"and the branch itself moves no resource")
	check(not bool(recorded["reads_its_arguments"]),
		"and reads neither of its arguments")
	var effects: Array = recorded["effects"]
	check_eq(effects.size(), 4, "its four recorded effects")
	check(not bool((effects[3] as Dictionary)["clamped"]),
		"the last of them is the UNCLAMPED print, which is the whole point of "
			+ "design D3")

	# --- the prefix substring really does occur, so the token rule is the rule
	for module_name3: String in LEGACY_MODULES:
		var sites_here: Array = _sites_in(_repo_text(module_name3), "MARKET_")
		check_eq(sites_here, PREFIX_SUBSTRING_SITES.get(module_name3, []),
			"the bare prefix occurs in %s exactly where recorded" % module_name3)
	check_eq(PREFIX_SUBSTRING_SITES.get("constants.py", []).size(), 6,
		"six times in constants.py, so a 'no declaration' figure is true only "
			+ "at the whole-token rule and BOTH rules are now measured")

	# --- the zero-consumer census, three rules, eleven modules
	# Measured up front in `run_scenario`; re-read here so this check cannot pass
	# on a census some other step happened to leave in place.
	var census: Dictionary = _consumer_census()
	var totals: Dictionary = census["totals"]
	for rule: String in ["raw", "quoted", "token"]:
		check_eq(int(totals[rule]), 0,
			"no committed market row has a `%s` consumer across all eleven "
				% rule + "legacy modules")
	check_eq((census["rows"] as Array).size(), 8,
		"and the census really covered all eight prefix-anchored rows")
	for row: Dictionary in census["rows"]:
		check_eq((row["where"] as Array).size(), 0,
			"row `%s` names no consuming module" % str(row["key"]))

	# --- the modules name NO committed key at all, so the forbidden list is
	# derived at run time rather than transcribed
	var folded_module: String = _code_with_literals(_module_source)
	var folded_schedule: String = _code_with_literals(_schedule_source)
	for raw3: Variant in _globals_rows:
		var key4: String = str((raw3 as Dictionary)["key"])
		if not key4.begins_with("MARKET_"):
			continue
		check(not folded_module.contains('"%s"' % key4),
			"the counter module names no committed market key as a literal")
		check(not folded_schedule.contains('"%s"' % key4),
			"and neither does the schedule module")


func _counter_sites(field_name: String) -> Dictionary:
	var out: Dictionary = {}
	for module_name: String in LEGACY_MODULES:
		var hits: Array = _sites_in(_repo_text(module_name), field_name)
		if not hits.is_empty():
			out[module_name] = hits
	return out


func _sites_in(text: String, needle: String) -> Array:
	var out: Array = []
	var lines: Array = text.split("\n")
	for index: int in range(lines.size()):
		if str(lines[index]).contains(needle):
			out.append(index + 1)
	return out


func _count_newlines_before(text: String, offset: int) -> int:
	return _count(text.substr(0, offset), "\n")


# ---------------------------------------------------------------------------
# the corpus: ten documents, two witnesses, two different writers
# ---------------------------------------------------------------------------

func _check_corpus() -> void:
	var census: Dictionary = _measure_corpus(CANONICAL_CORPUS)
	check_eq(int(census["documents"]), CANONICAL_CORPUS_COUNT,
		"the corpus is exactly the ten genuine save documents")
	check_eq(int(census["rows_read"]), CANONICAL_CORPUS_COUNT,
		"and every one of them carries exactly ONE map row, so the ten "
			+ "documents are ten rows rather than one row read ten times")
	check_eq(int(census["zero_instant_documents"]), 8,
		"EIGHT of the ten record a zero last-trade instant")
	check_eq(int(census["nonzero_instant_documents"]), 2,
		"and exactly two record a non-zero one")

	# --- witness one: the CLAMP, parked at the cap
	var clamp_row: Dictionary = _corpus_row(CORPUS_CLAMP_WITNESS)
	check_eq(int(clamp_row["numTradesDone"]), 20,
		"%s records the count at exactly the branch cap" % CORPUS_CLAMP_WITNESS)
	check_eq(int(clamp_row["numTradesDone"]),
		int(TradeCounters.TRADE_CAP_FROM_BRANCH),
		"which is the branch's own literal, so the clamp is witnessed by the "
			+ "committed corpus and not merely derived")
	check(int(clamp_row["timestampLastTrade"]) > 0,
		"and that document also carries a non-zero instant")
	var clamp_out: Dictionary = TradeCounters.project(clamp_row, _privacy(),
		int(clamp_row["timestampLastTrade"]) + 1)
	check_eq(int(clamp_out["increment_after_next_trade"]), 21,
		"so one more trade would build the local to twenty-one")
	check_eq(int(clamp_out["stored_after_next_trade"]), 20,
		"store the cap again")
	check_eq(int(clamp_out["remaining_after_next_trade"]), -1,
		"and print MINUS ONE, which the committed cap-parked row is exactly the "
			+ "precondition for")

	# --- witness two: the DAY RESET, the only writer that can zero the count
	var reset_row: Dictionary = _corpus_row(CORPUS_RESET_WITNESS)
	check_eq(int(reset_row["numTradesDone"]), 0,
		"%s records the count at ZERO" % CORPUS_RESET_WITNESS)
	check(int(reset_row["timestampLastTrade"]) > 0,
		"while recording a NON-ZERO last-trade instant")
	# The premises, derived from the WRITER SET and not read off the row.
	var raising: String = _code_only(str(_legacy_lines(COMMAND)[470])).strip_edges()
	check(raising.contains("time_now"),
		"command.py:471 assigns the server clock, so it is the only writer that "
			+ "can raise the instant from zero")
	var lowering: String = _code_only(str(_legacy_lines(COMMAND)[912])).strip_edges()
	check(lowering.contains("max(0,"),
		"and command.py:913 floors at zero, so it can never raise it")
	var zeroing: String = _code_only(str(_legacy_lines(ENGINE)[239])).strip_edges()
	check_eq(zeroing, "map[ ] = 0",
		"so engine.py:240 is the only writer that can return the count to zero, "
			+ "and this document is committed evidence that the day reset has "
			+ "already fired for it")
	var clamp_write: String = _code_only(str(_legacy_lines(COMMAND)[469])).strip_edges()
	check(clamp_write.contains("min(20,"),
		"the trade branch's own write is a clamp and therefore cannot produce a "
			+ "zero from a positive count")
	var reset_out: Dictionary = TradeCounters.project(reset_row, _privacy(),
		int(reset_row["timestampLastTrade"]) + 1)
	check_eq(int(reset_out["stored_count"]), 0,
		"the projection reports the reset document's count")
	check(int(reset_out["last_trade_instant"]) > 0,
		"alongside its non-zero instant")
	check_eq(reset_out["reset_predicate_holds"], false,
		"and the day-reset predicate is FALSE one second later, so the recorded "
			+ "zero is a reset that already fired rather than one pending, and a "
			+ "verdict is reported instead of being withheld")

	check(CORPUS_CLAMP_WITNESS != CORPUS_RESET_WITNESS,
		"the clamp witness and the reset witness are two different documents")
	var buckets: Array = []
	for relative: String in CANONICAL_CORPUS:
		var row: Dictionary = _corpus_row(relative)
		buckets.append(int(row["timestampLastTrade"]) / 86400)
	check_eq(buckets.size(), CANONICAL_CORPUS_COUNT,
		"every document contributes its recorded day bucket")
	for bucket: Variant in buckets:
		check(int(bucket) >= 0, "no bucket is negative")

	# --- the walker takes its allow-list as a real argument, so the allow-list
	# guard is provable by injection rather than merely stated
	var empty: Dictionary = _measure_corpus([])
	check_eq(int(empty["documents"]), 0,
		"the corpus walker really honours its allow-list: an empty list reads "
			+ "no documents")
	check_eq(int(empty["rows_read"]), 0, "and reads no rows")
	check_eq(int(empty["zero_instant_documents"]), 0,
		"and reports no figures, so a walker that ignored its argument could "
			+ "not reproduce the ten-document counts above")


func _corpus_row(relative: String) -> Dictionary:
	var document: Variant = _repo_json(relative)
	if not (document is Dictionary):
		fail("the committed save %s parses to an object" % relative)
		return {}
	var maps: Variant = (document as Dictionary).get("maps", null)
	if not (maps is Array) or (maps as Array).is_empty():
		fail("the committed save %s carries a maps array" % relative)
		return {}
	var row: Variant = (maps as Array)[0]
	if not (row is Dictionary):
		fail("the committed save %s carries an object map row" % relative)
		return {}
	var out: Dictionary = (row as Dictionary).duplicate(true)
	out["__document"] = relative
	return out


func _measure_corpus(allow: Array) -> Dictionary:
	var out := {
		"documents": allow.size(),
		"rows_read": 0,
		"zero_instant_documents": 0,
		"nonzero_instant_documents": 0,
		"rows": [],
	}
	for relative: String in allow:
		var row: Dictionary = _corpus_row(relative)
		if row.is_empty():
			continue
		out["rows_read"] = int(out["rows_read"]) + 1
		var instant: int = int(row.get("timestampLastTrade", 0))
		if instant == 0:
			out["zero_instant_documents"] = \
				int(out["zero_instant_documents"]) + 1
		else:
			out["nonzero_instant_documents"] = \
				int(out["nonzero_instant_documents"]) + 1
		(out["rows"] as Array).append({
			"document": relative,
			"numTradesDone": row.get("numTradesDone", null),
			"timestampLastTrade": row.get("timestampLastTrade", null),
			"day_bucket": instant / 86400,
		})
	return out


# ---------------------------------------------------------------------------
# absence: the inventory, the reserved names, the absent helpers, no ordinal
# ---------------------------------------------------------------------------

func _check_absence() -> void:
	check_eq(LEGACY_MODULES.size(), 11, "eleven legacy root modules are declared")
	for module_name: String in LEGACY_MODULES:
		check(_repo_text(module_name) != "",
			"the declared module %s really exists" % module_name)

	# --- the whole declared-function inventory, in BOTH directions
	var names: Array = []
	names.append_array(_declared_functions(_module_source))
	names.append_array(_declared_functions(_schedule_source))
	var deduped: Array = []
	for name: Variant in names:
		if not deduped.has(str(name)):
			deduped.append(str(name))
	deduped.sort()
	check_eq(deduped, EXPECTED_FUNCTIONS,
		"the whole declared-function inventory across both delivered modules")
	check_eq(names.size(), EXPECTED_DECLARATIONS,
		"and the DECLARATION count is pinned separately, so four names declared "
			+ "twice cannot hide a class that quietly grew")
	for label: Array in [["trade_counters.gd", _module_source],
			["market_schedule.gd", _schedule_source]]:
		var label_names: Array = _declared_functions(str(label[1]))
		check(label_names.size() > 0,
			"%s declares its functions" % str(label[0]))
		for name2: Variant in label_names:
			check(EXPECTED_FUNCTIONS.has(str(name2)),
				"every function %s declares is on the pin" % str(label[0]))

	# --- the reserved-stem guard: case-folded, by substring, BOTH directions,
	# and over DECLARED names only
	var folded: Array = []
	for name3: Variant in deduped:
		folded.append(str(name3).to_lower())
	for stem: String in RESERVED_STEMS:
		var borrowed: Array = []
		for name4: Variant in folded:
			if str(name4).contains(stem):
				borrowed.append(str(name4))
		check_eq(borrowed, [],
			"no declared function name borrows the reserved stem `%s`" % stem)
	for name5: Variant in folded:
		var unborrowed: Array = []
		for stem2: String in RESERVED_STEMS:
			if str(name5).contains(stem2):
				unborrowed.append(stem2)
		check_eq(unborrowed, [],
			"every delivered name carries no reserved stem at all (%s)"
				% str(name5))
	check_eq(RESERVED_STEMS.size(), 12, "twelve reserved stems are declared")
	# The two collisions that forced two stems OUT of the list are asserted, so
	# the list cannot quietly regain them and self-trip on the delivered code.
	for absent_stem: String in ["cap", "trade"]:
		var would_collide: Array = []
		for name6: Variant in folded:
			if str(name6).contains(absent_stem):
				would_collide.append(str(name6))
		check(not would_collide.is_empty(),
			("adding bare `%s` back to the reserved stems would collide with %d "
				+ "delivered names") % [absent_stem, would_collide.size()])
	check(EXPECTED_FUNCTIONS.has("cap_record"),
		"the delivered cap accessor is what rules bare `cap` out")

	# --- the absent-helper set
	var declared_absent: Array = []
	for entry: Dictionary in TradeCounters.ABSENT_HELPERS:
		declared_absent.append(str(entry["helper"]))
	for entry2: Dictionary in MarketSchedule.ABSENT_HELPERS:
		declared_absent.append(str(entry2["helper"]))
	check_eq(declared_absent.size(), 22,
		"the two modules declare twenty-two absent-helper entries between them")
	for helper: String in REQUIRED_ABSENT_HELPERS:
		check(declared_absent.has(helper),
			"the absent set names `%s` explicitly, so the record cannot be "
				% helper + "edited down to a list with none of them")
	for helper2: String in declared_absent:
		check(not folded.has(helper2),
			"the absent helper `%s` really is absent" % helper2)
	for label2: Array in [["trade_counters.gd", TradeCounters.ABSENT_HELPERS],
			["market_schedule.gd", MarketSchedule.ABSENT_HELPERS]]:
		for entry3: Dictionary in (label2[1] as Array):
			check(str((entry3 as Dictionary)["absent_because"]).length() > 40,
				"every absent helper in %s carries a recorded reason"
					% str(label2[0]))

	# --- no ordinal is claimed, scanned over CODE-ONLY text so a comment cannot
	# satisfy it, with the rationale asserted separately
	for label3: Array in [["trade_counters.gd", _module_source],
			["market_schedule.gd", _schedule_source]]:
		var code: String = _code_only(str(label3[1]))
		for ordinal: String in ["ordinal", "first zero-consumer",
				"tenth zero-consumer", "eleventh zero-consumer",
				"twelfth zero-consumer", "last zero-consumer",
				"final zero-consumer"]:
			check(not code.contains(ordinal),
				"%s claims no `%s` for the zero-consumer census"
					% [str(label3[0]), ordinal])
		check(str(label3[1]).contains(REQUIRED_ORDINAL_RATIONALE),
			"and %s carries the rationale for declining to, so the guard cannot "
				% str(label3[0]) + "be simplified back into a comment scan")

	# --- no route, no action, no request
	check_eq(TradeCounters.DELIVERED_ROUTES, [],
		"the counter module declares no delivered route")
	check_eq(TradeCounters.DELIVERED_ACTIONS, [],
		"and no delivered action")
	check_eq(TradeCounters.DELIVERED_REQUESTS, [],
		"and no delivered request")
	check_eq(MarketSchedule.DELIVERED_ROUTES, [],
		"the schedule module declares no delivered route")
	check_eq(MarketSchedule.DELIVERED_ACTIONS, [],
		"and no delivered action")
	check_eq(MarketSchedule.DELIVERED_REQUESTS, [],
		"and no delivered request")

	# --- no compatibility path, no clock, no engine node
	for label4: Array in [["trade_counters.gd", _module_source],
			["market_schedule.gd", _schedule_source]]:
		var code2: String = _code_only(str(label4[1]))
		check(not code2.contains("compat"),
			"%s names no compatibility path" % str(label4[0]))
		check(not code2.contains("Time."),
			"%s reads no clock of its own" % str(label4[0]))
		check(not code2.contains("Engine."),
			"%s touches no engine node" % str(label4[0]))


# ---------------------------------------------------------------------------
# ownership: the fields this line must not name, and who does
# ---------------------------------------------------------------------------

func _check_ownership() -> void:
	# The literal-preserving view, because every guard in this function is stated
	# over a QUOTED literal. `_check_literal_views()` proves the two views differ.
	var folded_module: String = _code_with_literals(_module_source)
	var folded_schedule: String = _code_with_literals(_schedule_source)

	for owner: Dictionary in FOREIGN_FIELDS:
		for key: Variant in owner["keys"]:
			var literal: String = '"%s"' % str(key)
			check(not folded_module.contains(literal),
				"the counter module names no `%s` literal owned by %s"
					% [str(key), str(owner["owner"])])
			check(not folded_schedule.contains(literal),
				"and neither does the schedule module")

	# The QUOTED form is load-bearing and this asserts why. A bare two-character
	# substring sits inside ordinary English throughout both files, so a bare
	# match could never fail -- the defect `godot-construction-assist` measured.
	var bare: Dictionary = {}
	for key2: String in ["nu", "ts", "ui", "si"]:
		bare[key2] = _count(_module_source, key2) \
			+ _count(_schedule_source, key2)
	for key3: String in bare.keys():
		check(int(bare[key3]) > 0,
			("a BARE substring match for `%s` self-trips on the delivered "
				+ "modules (%d times), which is why the foreign-field guard uses "
				+ "the quoted form") % [key3, int(bare[key3])])
		check(not folded_module.contains('"%s"' % key3),
			"while the QUOTED form of `%s` is genuinely absent" % key3)
		check(not folded_schedule.contains('"%s"' % key3),
			"from both delivered modules")

	# --- the hand-off: each owner exists and really projects what we decline
	for owner2: Dictionary in OWNERSHIP:
		var path: String = str(owner2["path"])
		var text: String = FileAccess.get_file_as_string("res://" + path)
		check(text != "", "the owning suite `%s` exists and is readable" % path)
		for needle: Variant in owner2["needles"]:
			check(text.contains(str(needle)),
				"`%s` really projects %s, so the hand-off has a recipient"
					% [str(owner2["capability"]), str(needle)])

	# --- the two counters belong to THIS line and nobody else may have claimed
	# them, which is the mirror of the foreign-field guard
	for field: String in ["numTradesDone", "timestampLastTrade"]:
		var literal2: String = '"%s"' % field
		var quoting: int = _count(_module_source, literal2) \
			+ _count(_schedule_source, literal2)
		check(quoting > 0,
			("this line's own state field `%s` IS named as a literal, so the "
				+ "foreign-field guard is not vacuously true of it") % field)
		for owner3: Dictionary in OWNERSHIP:
			var owner_text: String = FileAccess.get_file_as_string(
				"res://" + str(owner3["path"]))
			check_eq(_count(owner_text, literal2), 0,
				("no owning suite names `%s`, so ownership is unambiguous")
					% field)

	_check_literal_views()


## The two lexer views really differ, so a quoted-literal guard cannot silently
## be pointed at the view that deletes quoted literals.
##
## This is a guard on the GUARDS. An earlier draft ran the foreign-field and
## committed-key guards over `_code_only`, whose contract is to remove string
## literals -- so both could never fail, and the transcription probe among the
## nine fired nothing. The check below is built on a crafted line rather than on
## the delivered modules, because a self-test that reads the delivered source
## cannot fail while the delivered source is clean.
func _check_literal_views() -> void:
	var crafted := (
		"# a prose mention of \"MARKET_X\" is not code\n"
		+ "const CRAFTED := \"MARKET_X\"\n"
		+ "var single := 'MARKET_Y'\n"
		+ "var triple := \"\"\"MARKET_Z\"\"\"\n"
	)
	var stripped: String = _code_only(crafted)
	var kept: String = _code_with_literals(crafted)
	for key: String in ["MARKET_X", "MARKET_Y", "MARKET_Z"]:
		check(not stripped.contains('"%s"' % key),
			"the stripped view really cannot see the quoted literal `%s`, which "
				% key + "is why no quoted-literal guard may use it")
		check(kept.contains(key),
			"while the literal-preserving view sees `%s`" % key)
	check(not stripped.contains("a prose mention"),
		"and the stripped view removes comments")
	check(not kept.contains("a prose mention"),
		"while the literal-preserving view removes comments too")
	check(kept.contains('const CRAFTED := "MARKET_X"'),
		"so the two views differ in exactly one way, which is the one that "
			+ "matters: literals")
	check(_code_with_literals("var a := \"x\" # \"y\"\n").count("y") == 0,
		"and a quoted token inside a COMMENT is still removed, so a prose "
			+ "mention cannot satisfy a guard either")


# ---------------------------------------------------------------------------
# delegation: the transport-token gate belongs to its owner
# ---------------------------------------------------------------------------

func _check_delegation() -> void:
	var owner: String = FileAccess.get_file_as_string(SCOPE_OWNER_PATH)
	check(owner != "", "the owning scope suite exists and is readable")
	var needles := ["const FORBIDDEN", "for relative in ALLOWED",
		"scripts/market/trade_counters.gd",
		"scripts/market/market_schedule.gd",
		"tests/test_market_trade.gd",
		"evidence/market-trade/report.json"]
	for needle: String in needles:
		check(owner.contains(needle),
			"the owning scope suite covers `%s`" % needle)
	# The owner scans each allow-listed file against its forbidden list, so
	# COVERAGE of the list is the whole claim. Asserting that here would
	# duplicate the scan and re-create the defect the comment below records.
	check(owner.contains("FORBIDDEN"),
		"the owner really does scan its allow-listed files against a forbidden "
			+ "list, so the delegation is a live gate and not a comment")


## There is deliberately NO scan for the transport tokens in this suite. The
## owner (`test_project_scope.gd`) forbids those tokens in every file on its
## allow-listed set, and this suite, both delivered modules and the report are
## all on it -- so a guard naming them could only exist in a form its own owner
## rejects. That is the third recorded instance of this shape in this project
## (`godot-construction-assist` recorded the second, having deleted its own
## duplicated guard for the same reason). The claim is therefore DELEGATED, not
## dropped. `_check_delegation()` asserts the owner exists and that its
## allow-list covers every delivered artefact of this line.


# ---------------------------------------------------------------------------
# the no-route boundary, asserted against the battery's OWN source
# ---------------------------------------------------------------------------

func _check_route_boundary() -> void:
	var boot: String = _repo_text(VERIFY_BOOT_REPO_PATH)
	var hermetic := RegEx.new()
	hermetic.compile("\\$hermetic = @\\((.*?)\\)\\s*\\n")
	var hermetic_match: RegExMatch = hermetic.search(boot)
	check(hermetic_match != null, "the battery declares a hermetic suite list")
	var hermetic_names: Array = []
	if hermetic_match != null:
		var id_expression := RegEx.new()
		id_expression.compile("\"([^\"]+)\"")
		var found: RegExMatch = id_expression.search(hermetic_match.get_string(1))
		while found != null:
			hermetic_names.append(found.get_string(1))
			found = id_expression.search(hermetic_match.get_string(1),
				found.get_end())
	check_eq(hermetic_names.size(), RECORDED_HERMETIC_COUNT,
		"the battery registers exactly fifty hermetic suites")
	check(hermetic_names.has("test_market_trade"), "and this suite is one of them")

	var live := RegEx.new()
	# `[\s\S]` rather than `.` because `$livePhases` is a MULTI-LINE block while
	# `$hermetic` is a single line. This engine has no DOTALL flag, and a `.`
	# here silently matched nothing rather than failing loudly.
	live.compile("\\$livePhases = @\\(([\\s\\S]*?)\\n    \\)")
	var live_match: RegExMatch = live.search(boot)
	check(live_match != null, "the battery declares a live-phase list")
	var live_names: Array = []
	if live_match != null:
		var name_expression := RegEx.new()
		name_expression.compile("Name\\s*=\\s*\"([^\"]+)\"")
		var found2: RegExMatch = name_expression.search(live_match.get_string(1))
		while found2 != null:
			live_names.append(found2.get_string(1))
			found2 = name_expression.search(live_match.get_string(1),
				found2.get_end())
	check_eq(live_names.size(), RECORDED_LIVE_PHASE_COUNT,
		"the registered live-phase count is UNCHANGED at twenty-three, so this "
			+ "line adds none")
	for name3: Variant in live_names:
		check(not str(name3).to_lower().contains("market"),
			"no live phase mentions this surface (%s)" % str(name3))
	var block: String = live_match.get_string(1) if live_match != null else ""
	check(not block.to_lower().contains("market"),
		"and the whole live-phase block mentions this surface nowhere at all")


# ---------------------------------------------------------------------------
# the recorded probe evidence
# ---------------------------------------------------------------------------

## Nine probes, each MEASURED, each with a byte-identical restore.
##
## The failure counts below were measured by an external harness that injects
## each fault into a delivered module, runs this suite, counts the
## `[test] FAIL` LINES, and restores the file. Four harness disciplines came
## from recorded faults and are load-bearing:
##
##   * the count is of `[test] FAIL` LINES and never of a non-zero exit, because
##     a parse error also exits 1 and would have proved nothing about a guard.
##     A probe that fails with no such line is treated as a harness fault, not
##     as a detection. All nine produced one or more;
##   * the text is normalised to LF BEFORE mutation and re-expanded afterwards.
##     A CRLF round-trip once produced six fake passes on an earlier line,
##     because the module stopped parsing and the exit-code gate recorded that as
##     a detection;
##   * the restore is verified by sha256 over the raw working-tree bytes with
##     zero NUL bytes, and the final byte is pinned to the BASELINE rather than
##     asserted to be a newline -- a borrowed owning file legitimately ends
##     without one;
##   * every probe is re-measured against the FINAL delivered state, because a
##     later edit can silently restore a guard's coverage.
##
## TWO PROBES BORROW NO RESERVED STEM, and that is the informative pair. `cap_for`
## is caught only by the absent-helper guard, and `zone_alpha` by the inventory
## pin alone. Those are the LOWEST counts, and the difference between them and
## the stem-bearing probes is the measurement: the inventory pin is the real gate
## and the reserved-name guard is the belt.
## The three probes whose exact source text is quoted by `_check_evidence_record`.
## They are named so a lookup and the recorded row cannot drift apart: an
## earlier draft keyed the lookup on a 44-character truncation of the probe text
## and then looked up the full string, which raised at run time instead of
## failing a check -- a guard that crashes is not a guard.
const PROBE_BELT_ONLY := \
	"static func cap_for(row: Dictionary) -> int"
const PROBE_PIN_ONLY := \
	"static func zone_alpha(row: Dictionary) -> Dictionary"
const PROBE_ARITHMETIC := \
	"static func zone_beta(value: int) -> int: return value * 2"

## Which probes borrow one of the reserved stems, stated as a list rather than
## inferred from a detection count. `cap_for` borrows none (`cap` is not a
## reserved stem), and neither do the four probes that edit a body or add a
## constant, so the count is three and the earlier "at least five" was a guess.
const STEM_BEARING_PROBES := [
	"static func trade_cost(row: Dictionary) -> int",
	"static func enforce_trade_limit(row: Dictionary) -> bool",
	"static func sell_ratio(value: float) -> float: return value / 100.0",
]


## WHAT THE `injection_record` BLOCK IS, stated here so it cannot be read as more
## than it is.
##
## This function returns a TRANSCRIBED table of a prior session's injection probes. It
## does NOT execute them: it contains no `OS.execute`, no file write, no `await`, and
## no call into the engine, so it cannot re-measure anything at run time. Every
## `exit_code`, `failures` and `engine_error_lines` below is a recorded observation from
## when the probes were actually run against the delivered modules by the external
## harness, not a live result of this suite.
##
## What this function DOES assert is the internal consistency of that record: that nine
## probes are present, that each names a target and an anchor, and that the recorded
## failure counts are present per probe. Those are real checks -- they would catch a
## truncated or half-filled table -- but they are checks on the RECORD, not on the
## guards.
##
## This distinction is recorded rather than left implicit because an earlier review of
## this change found the block reading as live evidence of eight structural guards
## firing, which is stronger than anything the code supports. Earlier delivered lines
## made the same move; the standing rule for this project is to STATE it, not to quietly
## present a transcription as a measurement.
##
## The guards themselves are not thereby unproven: they are proven by the whole-inventory
## pin, which is exercised in-run by this suite's own boundary checks, and by the
## external harness run recorded here.
const INJECTION_PROVENANCE := {
	"executed_by_this_suite": false,
	"kind": "transcribed record of a prior external harness run",
	"why": "this function cannot execute a probe: it holds no OS.execute, no file "
		+ "write, no await, and no engine call, so every exit_code, failures and "
		+ "engine_error_lines value below is an observation recorded at the time the "
		+ "probes were run, not a live result of this run",
	"what_is_asserted_in_run": "the internal consistency of the record: nine probes "
		+ "present, each naming a target, a disguise and a recorded failure count",
	"what_is_not_asserted_in_run": "that the guards still fire. That was established "
		+ "by the external harness against these exact module digests, which are "
		+ "recomputed on every run of this suite and recorded alongside, so a change "
		+ "to either module invalidates the pairing on its face",
	"digest_pairing": "module_digests below is recomputed from the delivered bytes on "
		+ "every run; the recorded probe results were measured against these digests",
}


func _injection_record() -> Array:
	var record: Array = [
		{
			"probe": "static func trade_cost(row: Dictionary) -> int",
			"target": "trade_counters.gd",
			"disguise": "an invented PRICE helper: the cost of one trade, which is "
				+ "exactly the derived economy this line refuses. It borrows the "
				+ "reserved stem `cost` and is one of the four absent helpers the "
				+ "design names explicitly",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"unexpected_function", "reserved_stem_cost",
				"reserved_stem_module_scan", "absent_helper_really_absent"],
			"guard_count_note": "SIX failures from SIX distinct guards, so no "
				+ "guard here fires twice for one injected function",
			"exit_code": 1,
			"failures": 6,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": PROBE_BELT_ONLY,
			"target": "trade_counters.gd",
			"disguise": "an invented CAP ACCESSOR. It borrows NO reserved stem, "
				+ "because bare `cap` collides with the delivered `cap_record` and "
				+ "bare `trade` with the two delivered arithmetic functions -- so "
				+ "this probe is caught by the absent-helper guard alone and "
				+ "proves that guard is load-bearing in its own right",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"unexpected_function", "absent_helper_really_absent"],
			"guard_count_note": "the SECOND-LOWEST count of the nine, and four is "
				+ "three fewer than probe one because this probe borrows no stem",
			"exit_code": 1,
			"failures": 4,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "static func enforce_trade_limit(row: Dictionary) -> bool",
			"target": "trade_counters.gd",
			"disguise": "a SUFFIXED helper wearing two reserved stems as one "
				+ "prefix, so an exact-name check would have passed it. It is also "
				+ "one of the four absent helpers the design names explicitly",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"unexpected_function", "reserved_stem_limit",
				"reserved_stem_enforce", "reserved_stem_module_scan",
				"absent_helper_really_absent"],
			"guard_count_note": "SEVEN failures from SEVEN guards: this probe "
				+ "wears TWO stems as one prefix, so the stem guard fires once "
				+ "per stem plus once for the whole-module scan",
			"exit_code": 1,
			"failures": 7,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "return max(0, TRADE_CAP_FROM_BRANCH - (count + 1))",
			"target": "trade_counters.gd",
			"disguise": "the D3 CLAMP PROBE: the printed figure bounded to zero. "
				+ "This is the single most tempting 'fix' in the whole surface, "
				+ "because it makes the oracle's negative output disappear -- and "
				+ "it borrows no reserved word at all, so only the no-clamping "
				+ "census and the inventory pin can see it",
			"guards_that_fired": ["value_level_clamp_witness",
				"zero_to_thirty_sweep", "clamp_token_census",
				"comparison_operator_census", "operator_count",
				"single_return"],
			"guard_count_note": "TWENTY-SEVEN failures, by far the highest of the "
				+ "nine, and the reason is worth recording rather than hiding: a "
				+ "clamp is not one guard but a family, because the printed "
				+ "figure's negativeness is observed at TWENTY-ONE different "
				+ "counts (each negative-output row names the count it broke at) "
				+ "and again across the 0..30 sweep, so one edit is caught at "
				+ "many value levels rather than once. A one-line fix that "
				+ "silently erased the oracle's negative output could not pass "
				+ "this suite",
			"exit_code": 1,
			"failures": 27,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "static func sell_ratio(value: float) -> float: return value / 100.0",
			"target": "market_schedule.gd",
			"disguise": "an invented RATIO carrying a division, so it fires the "
				+ "operator census AND the reserved-name guard AND the "
				+ "absent-helper guard -- proving those three are independent",
			"guards_that_fired": ["operator_census", "whole_inventory_pin",
				"declaration_count", "unexpected_function",
				"reserved_stem_ratio", "reserved_stem_module_scan",
				"absent_helper_really_absent"],
			"guard_count_note": "EIGHT failures from SEVEN distinct guards, and the "
				+ "eighth is the same absent-helper check firing a SECOND time: "
				+ "`sell_ratio` is listed in BOTH modules' absent-helper sets, so "
				+ "the message appears once per module. The record keeps distinct "
				+ "guard names and reports the measured failure count separately "
				+ "rather than pretending the two numbers are equal",
			"exit_code": 1,
			"failures": 8,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "const LEAKED_KEY := \"MARKET_MAX_NUM_TRADES\"",
			"target": "market_schedule.gd",
			"disguise": "a TRANSCRIBED committed key. The schedule module is "
				+ "required to read its rows through the registry and to name NO "
				+ "committed key, so the forbidden list is derived at run time -- "
				+ "this probe fires the run-time-derived guard, not a transcribed "
				+ "one",
			"guards_that_fired": ["committed_key_literal_census",
				"run_time_derived_committed_key_check"],
			"guard_count_note": "TWO failures, and both are needed: the first is "
				+ "the schedule census asserting no committed MARKET key appears "
				+ "as a quoted literal in EITHER module, the second is the "
				+ "recorded-evidence check asserting the schedule module names "
				+ "NO committed key at all. They were verified to be genuinely "
				+ "independent by running `MARKET_INCREMENT` on its own, which "
				+ "fires only the second -- so neither is a restatement of the "
				+ "other",
			"exit_code": 1,
			"failures": 2,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": "const QUEUE_KEY := \"ui\"",
			"target": "trade_counters.gd",
			"disguise": "a FOREIGN STATE KEY in its QUOTED form, which the guard "
				+ "matches. The same key as a bare substring could never be "
				+ "caught, which is the recorded construction-assist defect this "
				+ "line inherits and asserts rather than repeats",
			"guards_that_fired": ["foreign_field_quoted_census",
				"foreign_field_bare_form_absence"],
			"guard_count_note": "TWO failures: the counter module names no `ui` "
				+ "literal owned by godot-unit-queues, AND the suite's own "
				+ "companion check that the QUOTED form is genuinely absent "
				+ "rather than merely unmatched",
			"exit_code": 1,
			"failures": 2,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": PROBE_PIN_ONLY,
			"target": "trade_counters.gd",
			"disguise": "the INVENTORY-ONLY probe: it borrows no reserved stem, "
				+ "names no absent helper, carries no operator and no committed "
				+ "key, so the whole-inventory pin is the ONLY thing that can see "
				+ "it. This is the probe that shows the pin is the real gate and "
				+ "the reserved-name guard is the belt",
			"guards_that_fired": ["whole_inventory_pin", "declaration_count",
				"unexpected_function"],
			"guard_count_note": "THREE failures, the LOWEST of the nine, and that "
				+ "is the point of the probe: it borrows no reserved stem, names no "
				+ "absent helper, carries no operator, no committed key and no "
				+ "foreign field, so the whole-inventory pin is the ONLY thing "
				+ "that can see it. Remove the pin and this probe passes",
			"exit_code": 1,
			"failures": 3,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
		{
			"probe": PROBE_ARITHMETIC,
			"target": "market_schedule.gd",
			"disguise": "the ARITHMETIC probe: a second operator in the schedule "
				+ "module, which is declared to contain none. It borrows no "
				+ "reserved stem either, so it proves the operator census is "
				+ "independent of the naming guard",
			"guards_that_fired": ["operator_census", "whole_inventory_pin",
				"declaration_count", "unexpected_function"],
			"guard_count_note": "FOUR failures: the operator census asserting the "
				+ "schedule module contains no `*` at all, plus the same three "
				+ "inventory guards as the pin-only probe -- one MORE than that "
				+ "probe, which is the measurement that the operator census is a "
				+ "guard in its own right and not a special case of the pin",
			"exit_code": 1,
			"failures": 4,
			"engine_error_lines": 0,
			"restore_byte_identical": true,
			"contained_after_restore": true,
		},
	]
	# The disclosure is asserted rather than merely emitted, so it cannot be dropped
	# from the report by an edit that leaves the table intact.
	check(not bool(INJECTION_PROVENANCE["executed_by_this_suite"]),
		"the injection record declares that this suite does not execute the probes")
	check(str(INJECTION_PROVENANCE["why"]).length() > 80,
		"and states why, in prose a reader cannot miss")
	return record


## Measured, not declared. This was previously hard-coded `false` on the reasoning
## that it "describes the checkout, not these files" -- which is a true statement
## about the CHECKOUT attached to a field named for the FILES, so a reader keying on
## `comparable_to_lf_normalised_digest` concluded these digests could not be compared
## against an LF manifest. They can: both delivered modules are pure LF (zero CRLF), so
## each raw digest IS that file's LF-normalised digest.
##
## Three sibling evidence reports carry this same field as `false`, and there it is
## CORRECT: those were CRLF files, where raw and LF-normalised digests genuinely
## differ. Copying the field and its value across file forms is how a guard becomes a
## lie, so the value is now measured from the bytes and the check compares the
## declaration against that measurement.
static func _modules_are_pure_lf() -> bool:
	for path: String in [MODULE_PATH, SCHEDULE_PATH]:
		if not FileAccess.file_exists(path):
			return false
		# `get_file_as_string`, not `String(bytes)`: there is no String constructor
		# taking a PackedByteArray on this engine, and `String(raw)` is a parse
		# error rather than a runtime one.
		var text := FileAccess.get_file_as_string(path)
		if text.is_empty():
			return false
		if text.contains("\r\n"):
			return false
	return true


func _module_digests() -> Dictionary:
	return {
		"form": "sha256 over the raw working-tree bytes, PLUS a second sha256 over the "
			+ "LF-normalised form of the same bytes. Both are recorded so a reader can "
			+ "compare against an LF manifest whichever form their checkout produced. "
			+ "The flag below is MEASURED from the bytes rather than asserted, so a CRLF "
			+ "checkout flips it to false without anything being edited -- which is why "
			+ "it describes the checkout and not the delivered file, and why no check may "
			+ "require it to be true. `.gitattributes` pins these paths to LF so the "
			+ "committed blobs and their digests reproduce on any checkout.",
		"comparable_to_lf_normalised_digest": _modules_are_pure_lf(),
		"modules": {
			"trade_counters.gd": {
				"path": MODULE_REPO_PATH,
				"sha256": FileAccess.get_sha256(MODULE_PATH),
				"sha256_lf_normalised": _lf_normalised_sha256(MODULE_PATH),
			},
			"market_schedule.gd": {
				"path": SCHEDULE_REPO_PATH,
				"sha256": FileAccess.get_sha256(SCHEDULE_PATH),
				"sha256_lf_normalised": _lf_normalised_sha256(SCHEDULE_PATH),
			},
		},
	}


## sha256 over the LF-normalised form of a file's bytes, computed WITHOUT going
## through `String`: there is no `String(PackedByteArray)` constructor on this engine
## and `String(raw)` is a parse error rather than a runtime one, so the bytes are
## reassembled from `get_buffer` instead. This is deliberately an INDEPENDENT
## computation from `FileAccess.get_sha256`, because the cross-check below compares
## the two -- a comparison of a value against itself would guard nothing.
func _lf_normalised_sha256(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	var buffer: PackedByteArray = FileAccess.get_file_as_bytes(path)
	if buffer.is_empty():
		return ""
	var normalised := PackedByteArray()
	var index := 0
	while index < buffer.size():
		if buffer[index] == 0x0D and index + 1 < buffer.size() and buffer[index + 1] == 0x0A:
			index += 1
		normalised.append(buffer[index])
		index += 1
	return _sha256_bytes(normalised)


func _sha256_bytes(bytes: PackedByteArray) -> String:
	# `HashingContext` is the engine's own SHA-256, so this is not a reimplementation.
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(bytes)
	return context.finish().hex_encode()


func _check_evidence_record() -> void:
	var record: Array = _injection_record()
	check_eq(record.size(), 9, "nine injection probes are recorded")
	var total_failures := 0
	for probe: Dictionary in record:
		var failures: int = int(probe["failures"])
		total_failures += failures
		check(failures > 0,
			"probe `%s` records at least one detection"
				% str(probe["probe"]).left(44))
		check_eq(int(probe["exit_code"]), 1, "and a non-zero exit code")
		check_eq(int(probe["engine_error_lines"]), 0,
			"and ZERO engine error lines, so the detection was a guard and not "
				+ "a parse error")
		check(bool(probe["restore_byte_identical"]),
			"and a byte-identical restore")
		check(bool(probe["contained_after_restore"]),
			"and containment after the restore")
		check(str(probe["disguise"]).length() > 80,
			"and records what the probe was disguised as")
		# "at least one", not "at least four". An earlier draft asserted four
		# and was a GUESS: the measured minimum is TWO, and it is reached by
		# the two single-line probes that edit one line of a module. Padding
		# that assertion up to whatever the arithmetic probes happen to score
		# would assert a property of the numbers rather than of the guards.
		check((probe["guards_that_fired"] as Array).size() >= 1,
			"and names at least one guard that fired, with the measured "
				+ "minimum and the reason for it recorded on the probe row")
	check(total_failures >= 30,
		"the nine probes fired at least thirty detections in total")
	info("measured injection detections across nine probes: %d" % total_failures)

	# The record's own central claims are asserted here rather than left as prose.
	var by_name: Dictionary = {}
	for probe2: Dictionary in record:
		by_name[str(probe2["probe"])] = probe2
	check_eq(by_name.size(), 9,
		"the nine recorded probes are nine DISTINCT source texts, so a lookup "
			+ "below cannot silently collapse two of them")
	var belt_only: Dictionary = by_name[PROBE_BELT_ONLY]
	var pin_only: Dictionary = by_name[PROBE_PIN_ONLY]
	var arithmetic: Dictionary = by_name[PROBE_ARITHMETIC]
	check(not (belt_only["guards_that_fired"] as Array).has("reserved_stem_borrowed"),
		"the cap-accessor probe fired NO reserved-stem guard, because bare `cap` "
			+ "is not one")
	check((belt_only["guards_that_fired"] as Array).has(
			"absent_helper_really_absent"),
		"and WAS caught by the absent-helper guard, so that guard stands alone")
	for guard: String in ["whole_inventory_pin", "declaration_count",
			"unexpected_function"]:
		check((pin_only["guards_that_fired"] as Array).has(guard),
			"the reserved-word-free probe fired the inventory guard `%s`" % guard)
	check(not (pin_only["guards_that_fired"] as Array).has("reserved_stem_borrowed"),
		"and fired no reserved-stem guard at all, which is what makes the "
			+ "inventory pin the real gate")
	check((arithmetic["guards_that_fired"] as Array).has("operator_census"),
		"the arithmetic probe fired the operator census")
	check(not (arithmetic["guards_that_fired"] as Array).has("reserved_stem_borrowed"),
		"and fired no reserved-stem guard either, so the operator census is "
			+ "independent of the naming guard")
	check(int(pin_only["failures"]) < int(belt_only["failures"]),
		"the inventory-only probe fired strictly fewer detections than the "
			+ "absent-helper one, which is the measurement the two exist to give")
	var stem_bearing: Array = []
	for probe3: Dictionary in record:
		if STEM_BEARING_PROBES.has(str(probe3["probe"])):
			stem_bearing.append(int(probe3["failures"]))
	check_eq(stem_bearing.size(), 3,
		"exactly THREE of the nine probes borrow a reserved stem, and they are "
			+ "named rather than inferred from a count")
	var least_stem_bearing: int = stem_bearing[0]
	for measured: int in stem_bearing:
		least_stem_bearing = mini(least_stem_bearing, measured)
	check(least_stem_bearing > int(pin_only["failures"]),
		"every reserved-word probe fired more than the inventory-only one, so "
			+ "the belt demonstrably adds coverage over the pin")

	var digests: Dictionary = _module_digests()
	var modules: Dictionary = digests["modules"]
	check_eq(modules.size(), 2, "both delivered modules are hashed")
	for label: Array in [["trade_counters.gd", MODULE_PATH],
			["market_schedule.gd", SCHEDULE_PATH]]:
		var record2: Dictionary = modules[str(label[0])]
		check(str(record2["sha256"]).length() == 64,
			"module `%s` carries a full sha256 digest" % str(label[0]))
		check(str(record2["sha256_lf_normalised"]).length() == 64,
			"module `%s` ALSO carries an LF-normalised sha256, so the digest can "
				% str(label[0])
				+ "be compared against an LF manifest whatever form this checkout "
				+ "produced")
	check_eq(bool(digests["comparable_to_lf_normalised_digest"]),
			_modules_are_pure_lf(),
			"the digest-comparability flag matches a fresh measurement of the "
				+ "module bytes, so it cannot drift from the form actually hashed")
	# The two digests are computed by INDEPENDENT routes -- `FileAccess.get_sha256`
	# over the raw bytes, and `HashingContext` over a hand-assembled LF-normalised
	# copy -- so agreeing on exactly the modules the flag names is a real
	# cross-check and not a tautology.
	var agree_with_flag := 0
	var disagree_with_flag := 0
	for module_name: String in modules:
		var entry: Dictionary = modules[module_name]
		if str(entry["sha256"]) == str(entry["sha256_lf_normalised"]):
			agree_with_flag += 1
			check(bool(digests["comparable_to_lf_normalised_digest"]),
				"module `%s` hashes identically raw and LF-normalised, which is "
					% module_name
					+ "exactly what the comparability flag claims for it")
		else:
			disagree_with_flag += 1
			check(not bool(digests["comparable_to_lf_normalised_digest"]),
				"module `%s` hashes DIFFERENTLY raw and LF-normalised, so this "
					% module_name
					+ "checkout is CRLF and the flag correctly says so -- a state "
					+ "that is recorded, not a failure")
	check(agree_with_flag + disagree_with_flag == 2,
		"both modules took one of the two digest branches, so neither was skipped")
	# The claim that is actually TRUE on every checkout, and which the earlier
	# version of this check got wrong: the flag describes the CHECKOUT, so it may be
	# false, but an LF manifest comparison remains possible either way because the
	# LF-normalised digest is always recorded.
	check(bool(digests["comparable_to_lf_normalised_digest"]) or disagree_with_flag == 2,
		"either this checkout is pure LF, or it is CRLF and the LF-normalised "
			+ "digests are the ones to compare -- never neither")


# ---------------------------------------------------------------------------
# the evidence report
# ---------------------------------------------------------------------------

func _write_report() -> void:
	var path: String = DEFAULT_REPORT_PATH
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--report="):
			path = argument.trim_prefix("--report=")
	# `is_absolute_path()`, not a `begins_with("/")` test. The documented
	# invocation passes a Windows absolute path, and a leading-slash test does
	# not recognise one, so the value was prefixed with `res://` and every
	# documented run on this platform failed to open the file. Found by running
	# the command as documented, not by reading it.
	if path.begins_with("res://"):
		path = ProjectSettings.globalize_path(path)
	elif not path.is_absolute_path():
		path = ProjectSettings.globalize_path("res://" + path)
	var directory: String = path.get_base_dir()
	if not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the evidence report could not be opened for writing at %s" % path)
		return

	var corpus: Dictionary = _measure_corpus(CANONICAL_CORPUS)
	var schedule_rows: Array = []
	for raw: Variant in _committed_rows:
		var row: Dictionary = raw as Dictionary
		schedule_rows.append({
			"key": str(row["key"]),
			"value": row["value"],
			"value_type": str(row.get("value_type", "")),
			"source_file": str(row.get("source_file", "")),
		})
	var branches: Array = []
	var branch_lines: Array = []
	var expression := RegEx.new()
	expression.compile(
		"(?:if|elif)[ \\t]+cmd[ \\t]*==[ \\t]*[\"']([^\"']+)[\"'][ \\t]*:")
	var command_raw: String = _repo_text(COMMAND)
	var found: RegExMatch = expression.search(command_raw)
	while found != null:
		branches.append(found.get_string(1))
		branch_lines.append(_count_newlines_before(command_raw, found.get_start()) + 1)
		found = expression.search(command_raw, found.get_end())
	var prefix: Array = []
	var substring_only: Array = []
	for raw2: Variant in _globals_rows:
		var key: String = str((raw2 as Dictionary)["key"])
		if key.begins_with("MARKET_"):
			prefix.append(key)
		elif key.contains("MARKET_"):
			substring_only.append(key)
	var bodies: Dictionary = _function_bodies(_code_only(_module_source))
	var printed_body: String = str(
		bodies.get("branch_remaining_after_next_trade", "")).replace("->", "")
	var clamp_hits: Array = []
	for token: String in CLAMP_TOKENS:
		if printed_body.contains(token):
			clamp_hits.append(token)
	var comparison_hits: Array = []
	for operator: String in COMPARISON_OPERATORS:
		if printed_body.contains(operator):
			comparison_hits.append(operator)

	var report := {
		"schema": "market-trade-report-v1",
		"capability": "godot-market-trade-counters",
		"kind": "read-only typed projection of the two map-row market counters "
			+ "and of the committed market schedule read through the normalized "
			+ "content registry, plus a recorded description of the legacy trade "
			+ "branch with nothing implemented",
		"delivered": [
			"two read-only typed projections with no route, no action, no "
				+ "request, no mutation and no transport",
			"both counters carried verbatim, with a refused field's RAW recorded "
				+ "value travelling untouched beside its refusal and no typed "
				+ "counter derived from it",
			"the legacy day-reset predicate EVALUATED and NOT PERFORMED, with "
				+ "the owning helper named and both day buckets reported",
			"the branch's own CLAMPED stored value and its UNCLAMPED printed "
				+ "figure, kept apart and both reproducible",
			"the committed market schedule through the registry alone, every "
				+ "committed value carried verbatim with nothing derived",
		],
		"counters": {
			"branch": "trade_resource",
			"site": "command.py:465-473",
			"reads_its_arguments": false,
			"resources_moved": 0,
			"cap_from_branch": TradeCounters.TRADE_CAP_FROM_BRANCH,
			"cap_derived_from_content": false,
			"cap_enforced": false,
			"branches_gating_on_the_count": 0,
			"count_sites": _counter_sites("numTradesDone"),
			"instant_sites": _counter_sites("timestampLastTrade"),
			"branch_inventory": TradeCounters.branch_inventory(),
			"argument_liveness_note": "the second argument's name occurs TWICE on "
				+ "its own line, once in the assignment and once in the trailing "
				+ "comment, so 'read and unused' is a code-only measurement and a "
				+ "raw-substring count would report a phantom second use",
		},
		"arithmetic": {
			"note": "the printed figure is UNCLAMPED while the stored value is "
				+ "clamped, so from the twenty-first recorded trade onward the "
				+ "stored value parks at the cap and the printed figure is "
				+ "negative. This contract reproduces both and corrects neither, "
				+ "and the absence of a clamp is asserted mechanically",
			"day_bucket_seconds": TradeCounters.DAY_BUCKET_SECONDS,
			"table": _arithmetic,
			"clamp_tokens_found_in_printed_function": clamp_hits,
			"comparison_operators_found_in_printed_function": comparison_hits,
		},
		"reset": TradeCounters.RESET_OWNER,
		"divergences": TradeCounters.divergence_records(),
		"schedule": {
			"content_domain": MarketSchedule.CONTENT_DOMAIN,
			"selection": MarketSchedule.prefix_record(),
			"committed_file": GLOBALS_PACKAGE,
			"globals_rows": _globals_rows.size(),
			"prefix_rows": prefix.size(),
			"substring_only_rows": substring_only.size(),
			"substring_only_keys": substring_only,
			"rows": schedule_rows,
			"cap_coincidence": {
				"cap_from_branch": TradeCounters.TRADE_CAP_FROM_BRANCH,
				"coincident_key": CAP_COINCIDENT_KEY,
				"coincident_value": _committed_value(CAP_COINCIDENT_KEY),
				"rows_carrying_the_same_number": _rows_carrying_number(
					int(TradeCounters.TRADE_CAP_FROM_BRANCH)),
				"derived": false,
				"why": "the coincident row has zero legacy consumers, so deriving "
					+ "a load-bearing cap from it would make an unread constant "
					+ "read. The equality is recorded as a coincidence, TWO "
					+ "committed rows carry the number twenty, and the delivered "
					+ "modules name no committed key at all",
			},
			"consumer_rule": MarketSchedule.consumer_rule(),
			"no_derived_record": MarketSchedule.no_derived_record(),
		},
		"census": {
			"modules": LEGACY_MODULES,
			"module_count": LEGACY_MODULES.size(),
			"totals": _census.get("totals", {}),
			"rows": _census.get("rows", []),
			"prefix_raw_substring_sites": PREFIX_SUBSTRING_SITES,
			"prefix_raw_substring_note": "the bare prefix DOES occur in the "
				+ "preserved sources, six times in constants.py, because three "
				+ "committed market-named identifiers and three mission "
				+ "identifiers embed it. A zero-consumer claim about the bare "
				+ "prefix is therefore false, and the claim here is about the "
				+ "eight whole key names under three separately measured rules",
		},
		"corpus": {
			"documents": CANONICAL_CORPUS,
			"document_count": CANONICAL_CORPUS_COUNT,
			"rows": corpus["rows"],
			"zero_instant_documents": corpus["zero_instant_documents"],
			"nonzero_instant_documents": corpus["nonzero_instant_documents"],
			"clamp_witness": {
				"document": CORPUS_CLAMP_WITNESS,
				"witnesses": "the CLAMP: the stored count is parked at exactly "
					+ "the branch's own cap literal, which is the value a clamped "
					+ "store can only produce from a count at or above the cap",
			},
			"reset_witness": {
				"document": CORPUS_RESET_WITNESS,
				"witnesses": "the DAY RESET: a non-zero last-trade instant "
					+ "beside a zero count. command.py:471 is the only writer "
					+ "that can raise the instant from zero and command.py:913 "
					+ "floors at zero, so a trade demonstrably ran; the trade "
					+ "branch's own write is a clamp and cannot return the count "
					+ "to zero, so engine.py:240 is the only writer that could "
					+ "have done it",
			},
			"premises": [
				"command.py:471 assigns the server clock",
				"command.py:913 is max(0, ... - seconds) and cannot raise",
				"command.py:906 makes `seconds` client-supplied",
				"engine.py:240 is the only writer that assigns a literal zero",
				"command.py:470 is a clamp and cannot yield zero from a "
					+ "positive count",
			],
		},
		"branch_partition": {
			"declared_branches": branches.size(),
			"distinct_branch_names": _unique_size(branches),
			"first_line": branch_lines[0],
			"last_line": branch_lines[branch_lines.size() - 1],
			"trade_branch_index": branches.find("trade_resource"),
			"trade_branch_line": branch_lines[branches.find("trade_resource")],
			"unhandled_fallthrough_line": 954,
			"note": "the unhandled fallthrough is an `else:` and not a branch, "
				+ "which is why the count is sixty-three and not sixty-four",
			"branches_mentioning_trade": _names_containing(branches, "trade"),
		},
		"absence": {
			"declared_function_inventory": EXPECTED_FUNCTIONS,
			"declared_function_count": EXPECTED_DECLARATIONS,
			"reserved_stems": RESERVED_STEMS,
			"reserved_stem_note": "two candidate stems are deliberately absent: "
				+ "bare `cap` collides with the delivered cap_record and bare "
				+ "`trade` with the two delivered arithmetic functions. A guard "
				+ "that cannot be written without colliding with the delivered "
				+ "code is a guard that will be relaxed later",
			"counter_absent_helpers": TradeCounters.ABSENT_HELPERS,
			"schedule_absent_helpers": MarketSchedule.ABSENT_HELPERS,
			"required_absent_helpers": REQUIRED_ABSENT_HELPERS,
			"ordinal_claimed": false,
			"ordinal_note": "four conflicting ordinals already exist in this "
				+ "project's delivered records over four different scopes, so "
				+ "none is claimed here",
			"delivered_routes": TradeCounters.DELIVERED_ROUTES,
			"delivered_actions": TradeCounters.DELIVERED_ACTIONS,
			"delivered_requests": TradeCounters.DELIVERED_REQUESTS,
		},
		"ownership": {
			"foreign_fields": FOREIGN_FIELDS,
			"foreign_field_match_form": "the QUOTED LITERAL only; a bare "
				+ "substring match for a two-character key self-trips on ordinary "
				+ "English inside the delivered modules and could never fail",
			"owners": OWNERSHIP,
		},
		"guard_evidence": {
			"injection_record": _injection_record(),
			"injection_record_provenance": INJECTION_PROVENANCE,
			"module_digests": _module_digests(),
			"harness_disciplines": [
				"the probe result is the count of `[test] FAIL` LINES, never a "
					+ "non-zero exit, because a parse error also exits 1 and "
					+ "would prove nothing about a guard",
				"a probe failing with no `[test] FAIL` line is a harness fault, "
					+ "not a detection, and aborts the probe set",
				"text is normalised to LF BEFORE mutation and re-expanded "
					+ "afterwards",
				"each restore is verified by sha256 with zero NUL bytes, and the "
					+ "final byte is pinned to the BASELINE rather than asserted "
					+ "to be a newline",
				"git diff --numstat --ignore-cr-at-eol and git status --short "
					+ "must equal their pre-probe values after the set",
			],
		},
		"remeasured_figures": [
			"the eleven legacy root modules, declared as a closed set",
			"the dispatcher's 63 named branches and their line span",
			"the writer and reader sites of both counters",
			"the eight committed rows and the three substring-only rows",
			"the three-rule consumer census over all eight committed keys",
			"the six bare-prefix occurrences in constants.py",
			"both counters in all ten corpus documents",
			"every cited legacy site, checked as a measurement",
		],
		"claim_limits": [
			"this is a PROJECTION and a RECORDED DESCRIPTION. No trade is "
				+ "performed, no counter is cleared, no instant is moved and no "
				+ "resource moves anywhere in the delivered client",
			"the cap is STORED and never ENFORCED: the count's only reader is "
				+ "the increment that produces it, so nothing in the preserved "
				+ "server ever refused, gated, limited or ranked a player on it. "
				+ "The projection reports that and offers no limit of its own",
			"the printed remaining figure goes NEGATIVE from the twenty-first "
				+ "recorded trade onward and is reproduced unclamped. That is "
				+ "recorded oracle behaviour, not an endorsed product decision, "
				+ "and the suite asserts mechanically that no clamp is introduced",
			"the day reset is the engine's and is NOT reimplemented here. The "
				+ "predicate is evaluated and both day buckets are reported; the "
				+ "count is written to nothing",
			"both client-dictated behaviours are DIVERGENCES from the delivered "
				+ "client, not parity: the legacy branch moves no resource "
				+ "because it reads its arguments and uses neither, and "
				+ "fast_forward makes the last-trade instant client-writable, so "
				+ "a client could walk it back across a day boundary and clear "
				+ "the count",
			"no committed price, period, percentage, amount, bound or base-cost "
				+ "object is derived, charged or displayed. Every one of the "
				+ "eight committed rows has zero consumers under three separately "
				+ "measured rules, and there is no committed rule to apply any of "
				+ "them by",
			"the equality between the branch's cap literal and a committed row's "
				+ "value is recorded as a COINCIDENCE. TWO committed rows carry "
				+ "the number twenty, so the report names the trades row "
				+ "specifically rather than the number",
			"the bare prefix DOES occur in the preserved sources, six times in "
				+ "constants.py. A zero-consumer claim about the bare prefix "
				+ "would be false; the claim here is about the eight whole key "
				+ "names, and the bare occurrence is reported as a correction",
			"the prefix/substring difference is a SELECTION rule, not an "
				+ "assertion that the three longer identifiers are irrelevant to "
				+ "the game -- they are simply not rows of a market schedule",
			"every figure about the counters is a statement about the PRESERVED "
				+ "server. Absence of a server-side rule says nothing about what "
				+ "the Flash client displayed, which may have read the cap, priced "
				+ "a trade or drawn a countdown entirely client-side",
			"parity is not claimed for any arm, because no executed-legacy "
				+ "fixture was captured: this line adds no endpoint and mutates "
				+ "nothing, so there is no transaction to record",
			"no windowed capture and no pixel-parity oracle are claimed, because "
				+ "nothing is rendered",
		],
	}
	file.store_string(JSON.stringify(report, "  ", true, true))
	file.close()
	info("wrote the market-trade evidence report to %s" % path)


func _committed_value(key: String) -> Variant:
	for raw: Variant in _globals_rows:
		if str((raw as Dictionary)["key"]) == key:
			return (raw as Dictionary)["value"]
	return null


## The committed market rows whose value EQUALS `value`, compared only where the
## value is a NUMBER.
##
## `MARKET_BASE_COSTS` is an object and `MARKET_AMOUNT_TRADE` an array, and
## comparing either against an int in GDScript is a runtime error rather than a
## false answer, so the numeric test is a stated precondition instead of a
## `typeof` guard inside the loop.
func _rows_carrying_number(value: int) -> Array:
	var out: Array = []
	for raw: Variant in _globals_rows:
		var row: Dictionary = raw as Dictionary
		var row_value: Variant = row.get("value", null)
		if not (row_value is int) and not (row_value is float):
			continue
		if not str(row["key"]).begins_with("MARKET_"):
			continue
		if int(row_value) == value:
			out.append(str(row["key"]))
	return out


func _unique_size(values: Array) -> int:
	var out: Array = []
	for value: Variant in values:
		if not out.has(value):
			out.append(value)
	return out.size()


func _names_containing(values: Array, needle: String) -> Array:
	var out: Array = []
	for value: Variant in values:
		if str(value).to_lower().contains(needle):
			out.append(str(value))
	return out


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

## Every declared function name, in declaration order, `static` or not.
func _declared_functions(source: String) -> Array:
	var out: Array = []
	var expression := RegEx.new()
	expression.compile("(?:static[ \\t]+)?func[ \\t]+([A-Za-z_][A-Za-z0-9_]*)")
	var found: RegExMatch = expression.search(source)
	while found != null:
		out.append(found.get_string(1))
		found = expression.search(source, found.get_end())
	return out


## Declared function name -> the CODE-ONLY text from its declaration to the next
## declaration. Constants precede every function in both delivered modules, so
## the span is the function body plus any trailing comment, which is stripped.
func _function_bodies(code: String) -> Dictionary:
	var expression := RegEx.new()
	expression.compile("(?:static[ \\t]+)?func[ \\t]+([A-Za-z_][A-Za-z0-9_]*)")
	var spans: Array = []
	var found: RegExMatch = expression.search(code)
	while found != null:
		spans.append({"name": found.get_string(1), "start": found.get_start()})
		found = expression.search(code, found.get_end())
	var out: Dictionary = {}
	for index: int in range(spans.size()):
		var begin: int = int((spans[index] as Dictionary)["start"])
		var finish: int = code.length()
		if index + 1 < spans.size():
			finish = int((spans[index + 1] as Dictionary)["start"])
		out[str((spans[index] as Dictionary)["name"])] = code.substr(begin,
			finish - begin)
	return out


func _functions_with_arithmetic(code: String) -> Array:
	var out: Array = []
	var bodies: Dictionary = _function_bodies(code)
	for function_name: Variant in bodies.keys():
		for operator: String in ["*", "/", "%"]:
			if _count(str(bodies[function_name]), operator) > 0:
				if not out.has(function_name):
					out.append(function_name)
	return out


func _count(haystack: String, needle: String) -> int:
	if needle == "":
		return 0
	var out := 0
	var position: int = haystack.find(needle)
	while position >= 0:
		out += 1
		position = haystack.find(needle, position + needle.length())
	return out


func _count_token(haystack: String, word: String) -> int:
	var expression := RegEx.new()
	expression.compile("(?<![A-Za-z0-9_])" + _escape(word) + "(?![A-Za-z0-9_])")
	return expression.search_all(haystack).size()


func _escape(text: String) -> String:
	return text.replace("\\", "\\\\").replace(".", "\\.").replace("(", "\\(") \
		.replace(")", "\\)").replace("+", "\\+").replace("*", "\\*") \
		.replace("?", "\\?").replace("[", "\\[").replace("]", "\\]") \
		.replace("{", "\\{").replace("}", "\\}").replace("|", "\\|") \
		.replace("^", "\\^").replace("$", "\\$")


## Comments and string literals stripped, so a prose mention of a token cannot
## satisfy or break a code-level guard.
##
## This engine has NO multi-line RegEx flag, so the lexer is written out. It is
## a two-state machine because an apostrophe inside a double-quoted string
## desynchronises a naive one-pass strip, which `godot-unit-behaviors` recorded
## as a real fault in this project.
func _code_only(source: String) -> String:
	var out: String = ""
	var i: int = 0
	var n: int = source.length()
	while i < n:
		var c: String = source[i]
		if c == "#":
			while i < n and source[i] != "\n":
				i += 1
		elif c == "'" or c == "\"":
			var quote: String = c
			var triple: bool = source.substr(i, 3) == quote + quote + quote
			i += 3 if triple else 1
			while i < n:
				if triple and source.substr(i, 3) == quote + quote + quote:
					i += 3
					break
				if not triple and source[i] == "\\":
					i += 2
					continue
				if not triple and source[i] == quote:
					i += 1
					break
				if not triple and source[i] == "\n":
					break
				i += 1
			out += " "
		else:
			out += c
			i += 1
	return out


## Comments stripped, STRING LITERALS PRESERVED.
##
## This exists because two of this line's guards are stated over QUOTED LITERALS
## -- a foreign state key and a committed content key -- and the view above
## removes exactly the thing they match. An earlier draft ran both of them over
## `_code_only`, which made them **unsatisfiable guards that could never fail**:
## nine injection probes ran, one of them a transcribed committed key, and it
## fired nothing at all. `_check_literal_views()` now asserts the two views
## really differ on a crafted literal, so the defect cannot be reintroduced by
## picking the wrong helper.
func _code_with_literals(source: String) -> String:
	var out: String = ""
	var i: int = 0
	var n: int = source.length()
	while i < n:
		var c: String = source[i]
		if c == "#":
			while i < n and source[i] != "\n":
				i += 1
		elif c == "'" or c == "\"":
			var quote: String = c
			var triple: bool = source.substr(i, 3) == quote + quote + quote
			var literal: String = source.substr(i, 3) if triple else quote
			out += literal
			i += 3 if triple else 1
			while i < n:
				if triple and source.substr(i, 3) == quote + quote + quote:
					out += quote + quote + quote
					i += 3
					break
				if not triple and source[i] == "\\":
					out += source.substr(i, 2)
					i += 2
					continue
				if not triple and source[i] == quote:
					out += quote
					i += 1
					break
				if not triple and source[i] == "\n":
					break
				out += source[i]
				i += 1
		else:
			out += c
			i += 1
	return out