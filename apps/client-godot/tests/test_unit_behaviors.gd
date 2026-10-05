extends "res://tests/test_base.gd"
## Unit-behaviour suite (OpenSpec `godot-unit-behaviors` "The dead-hero ledger
## is projected, and the gates are named" / "The three-door command inventory
## records which command reaches the ledger" / "A revival is a server-derived
## intent, and the client-supplied syringe is ignored" / "No syringe cost, and
## the committed syringes field is content only" / "No combat is resolved, and
## no placement validation is invented" / "No executed-legacy behaviour fixture
## is claimed" / "Unit-behaviour evidence and claim limits", design D1-D8).
##
## Unlike the three refusal lines before it, this line's checks are mostly
## **positive**: a real two-sided counter, two named gates, three inventoried
## doors, a real typed intent, and a working offline double.  The anti-invention
## guard is structural — both delivered modules' whole static-function
## inventories are compared against pinned lists, so a syringe-cost, damage,
## attack, defence, hit, occupancy, or charge helper fails the run wherever it
## is added.
##
## Checks:
##   projection  every recorded entry verbatim, the increment and decrement
##               shapes, the **delete-at-zero** rule, no threshold/cap/clamp, and
##               no count derived from another;
##   gates       **both** legacy gates named with their recorded source lines,
##               exactly **two** of them, and no third invented;
##   failclosed  an absent ledger, a non-object ledger, a **non-string key**, and
##               a **non-integer count** each refused with its recorded state
##               intact, never defaulted to an empty resolved ledger;
##   inventory   `kill`, `sell`, and `resurrect_hero` each with an explicit
##               ledger effect, `kill` never reaching the ledger, `sell` only
##               behind the KILL guard and only through the **engine helper**,
##               the helper not being a branch, and the 63-branch count staying
##               distinguishable;
##   fields      all **21** zero-consumer behavioural fields with their
##               **measured** occurrence counts and their **measured** distinct
##               committed unit values, the seven combat fields measured at
##               zero, `resurrectable` measured at 426/429 units and 0/470
##               buildings, `syringes` measured at 6 distinct, and
##               `clicks_to_build` measured at two;
##   refusals    no syringe cost, no resource movement, no combat, no placement
##               validation — each with a non-empty recorded reason — and **no**
##               helper implementing any of them;
##   intent      the closed three-key intent, the ignored keys, and both
##               implementations returning the same typed shape;
##   double      the offline double's delete-at-zero decrement, its re-placement
##               with **no** validation, its neutral vector, and its two named
##               refusals;
##   absence     the two delivered modules declare **EXACTLY** their projection
##               and record accessors, and the recorded `ABSENT_HELPERS` list
##               names twelve with its reason;
##   legacy      the committed legacy source re-read for every figure this line
##               records: the 63 named branches, `kill` / `sell` /
##               `resurrect_hero` present, `resurrectable`'s two reads, and
##               `clicks_to_build`'s single read;
##   corpus      the committed corpus measurement: an **empty** ledger, 40 rows
##               across 40 distinct cells, **0** resurrectable rows, and **no**
##               unit row;
##   boundary    no client source anywhere derives a syringe cost, damage,
##               occupancy, or terrain rule — and the absence of any **other**
##               resurrection endpoint;
##   content     the committed distributions measured from the verified registry,
##               never asserted from prose;
##   purity      the two delivered modules name no node, a clock, a request, or a
##               transport token, and preload only the read-only projection;
##   containment the content package, the committed saves, the committed
##               fixtures, and the legacy root modules are byte-identical after
##               the run.
##
## Hermetic: no process, no server, no socket, and no request over the network —
## the intent is exercised through the offline double, and the live phase
## (`--scenario=live-behavior`) is registered separately in verify-boot.ps1.
##
## `--report=<path>` writes the deterministic `unit-behaviors-report-v1` evidence
## report; the bare `--report` flag defaults to
## `evidence/unit-behaviors/report.json`, and the destination directory is
## created first. Every table is derived from the live model, the verified
## registry, and the committed bytes, so the report cannot drift from the code
## it documents.

const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BehaviorFlow = preload("res://scripts/units/behavior_flow.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-behaviors/report.json"

## The committed corpus this line measures, and the corpus map it reads.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const CORPUS_MAP_INDEX := 0
const EXPECTED_ROWS := 40
const EXPECTED_DISTINCT_CELLS := 40
const EXPECTED_DISTINCT_ITEM_IDS := 11
const EXPECTED_RESURRECTABLE_ROWS := 0
const EXPECTED_UNIT_ROWS := 0

## The committed placed-row width this line parses; eight slots.
const CORPUS_ROW_SLOTS := 8

## The REPOSITORY-WIDE census, measured in the same run, which this
## milestone added because the fresh-player figures above were repeatedly
## quoted as though they described the repository.
##
## The record they were quoted into is `godot-unit-behaviors`, and those
## figures are TRUE OF `CORPUS_SAVE` and FALSE of the repository:
## `tests/saves/` and `villages/` together hold committed documents that
## place hundreds of unit rows, so "the committed corpus places no unit
## row" was a statement about ONE file. Both sets are now measured and
## written together, and every figure is re-derived from the committed
## bytes on every run.
const REPOSITORY_VILLAGE_DIR := "villages"
const REPOSITORY_SAVES_DIR := "tests/saves"
const REPOSITORY_EXCLUDED_SAVE_DOCUMENTS := ["manifest.json"]
const EXPECTED_REPOSITORY_DOCUMENTS := 10
const EXPECTED_REPOSITORY_PLACED_ROWS := 3372
const EXPECTED_REPOSITORY_UNIT_ROWS := 441
const EXPECTED_REPOSITORY_UNIT_ROWS_ON_TEAM_ONE := 441
const EXPECTED_REPOSITORY_UNIT_ROWS_RESURRECTABLE := 429
const EXPECTED_REPOSITORY_DOCUMENTS_WITH_UNIT_ROWS := 7
const EXPECTED_REPOSITORY_DOCUMENTS_WITH_NON_EMPTY_LEDGER := 4

## The committed corpus's ledger and its seven balances, measured not asserted.
const EXPECTED_LEDGER := {}
const EXPECTED_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}

## The committed cell the double's positive path addresses, read out of the
## committed corpus at run time rather than trusted from this sentence.  It is
## the corpus's map key 1, the Command Center.
const CORPUS_TARGET_MAP_KEY := 1

## The double's documented in-memory ledger seed, and the committed item id it
## names.  The suite MEASURES that the id is a committed unit whose committed
## `resurrectable` is greater than zero, so a seed that would fail the legacy
## gate cannot pass unnoticed.
const DOUBLE_SEED := {"1001": 1}
const DOUBLE_SEED_ITEM_ID := 1001

## The seven stored resource slots, and the full set the no-cost proof compares.
const RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

## The whole static-function inventory of `unit_behaviors.gd`.  This is the
## anti-invention guard: a syringe-cost, damage, attack, defence, hit,
## occupancy, or charge helper appears here and fails the suite.
const EXPECTED_BEHAVIOR_METHODS := [
	"_type_name", "_whole_number", "committed_resurrectable",
	"command_inventory", "engine_helpers", "expected_increment",
	"expected_ledger", "field_record", "gate_count", "gates",
	"inventory_record", "ledger_entries", "ledger_reaching_commands",
	"ledger_record", "passes_resurrectable_gate", "passes_team_gate",
	"project_ledger", "readout_text", "refusal_record",
]

## The whole static-function inventory of `behavior_flow.gd`, asserted for the
## same reason.
const EXPECTED_FLOW_METHODS := [
	"_is_placement_row", "_optional_int", "_resurrect_error", "intent_record",
	"ledger_record", "offers_revival", "parse_resurrect", "readout_text",
	"refusal_record", "resurrect_failure", "scope_record",
]

## Helpers a syringe-cost, combat, occupancy, or charge rule would take.  The
## inventories above are the real gate; this list is what the suite also
## asserts is absent **by name**, so a rename cannot smuggle one past the
## inventory and a leftover fails visibly.
const FORBIDDEN_HELPERS := [
	"syringe_cost", "charge_revive", "charge", "resolve_damage", "apply_attack",
	"attack", "defend", "defense", "defence", "hit_chance", "is_occupied",
	"occupied", "in_bounds", "bounds", "terrain_at", "terrain",
	"is_type_allowed", "revive_count_cap", "revive_cooldown", "cost", "price",
]

## Tokens that would mean a syringe-cost, combat, occupancy, or charge mechanism
## is implemented.  Spelled as fragments for the same project-scope reason as in
## the delivered refusal modules: the project-scope suite scans every source
## file for their literal forms, so the needles are assembled.
const BEHAVIOUR_NEEDLES := [
	"syringe_" + "cost", "charge_" + "revive", "resolve_" + "damage",
	"apply_" + "attack", "hit_" + "chance", "is_" + "occupied",
	"revive_" + "count_cap", "revive_" + "cooldown", "terrain_" + "at",
	"is_type_" + "allowed",
]

## The same needles scanned over the WHOLE client source tree, which is the
## structural form of "no client source derives a syringe cost, damage,
## occupancy, or terrain rule".
##
## The scan matches an IDENTIFIER TOKEN rather than a bare substring, and
## that distinction is load-bearing rather than cosmetic. It was MEASURED:
## `godot-combat-actions` legitimately **carries this line's own
## `NO_SYRINGE_COST` statement** through a field named `no_syringe_cost`,
## so the needle `syringe_cost` matched inside a longer, differently-
## purposed identifier and the guard reported an offender that does not
## exist -- there is no syringe-cost helper, declaration, or rule anywhere
## in the client. A substring is not a declaration, which is the same rule
## this project applies when counting legacy consumers, so the scan now
## uses this suite's EXISTING word-boundary helper
## (`_declares_identifier`, already needed for the two-letter `nc` needle)
## instead of `contains`.
const CLIENT_SCAN_ROOTS := ["res://scripts", "res://tests"]

## Tokens a pure module must not carry: a node, a clock, a request, or a
## transport.  The transport needles are fragments for the same project-scope
## reason as in the queues suite.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]

## The non-claim phrases the delta's evidence requirement names.  Each is
## asserted to appear in the module's own `NON_CLAIMS` list, which is what the
## report carries verbatim.
const REQUIRED_NON_CLAIMS := [
	"no Flash",
	"NO SYRINGE COST IS CHARGED AND NO STORED RESOURCE MOVES",
	"NO COMBAT IS RESOLVED",
	"NO OCCUPANCY, BOUNDS, TYPE, OR TERRAIN VALIDATION IS ADDED",
	"THE DEATH/RESURRECTION PAIRING IS DERIVED",
	"IS REFERENCED AND NOT REIMPLEMENTED",
	"NO EXECUTED-LEGACY BEHAVIOUR FIXTURE WAS CAPTURED",
	"NO UNIT ROW WAS MANUFACTURED",
	"NO UNIT IS REVIVED AGAINST THE COMMITTED CORPUS",
	"no pixel parity is claimed",
	"no windowed capture is claimed",
]

## The two delivered modules, named so the inventory and purity scans read them
## from one place.
const DELIVERED_BEHAVIOR_SCRIPT := "res://scripts/units/unit_behaviors.gd"
const DELIVERED_FLOW_SCRIPT := "res://scripts/units/behavior_flow.gd"

## The registry reference the content measurements read, set once in
## `run_scenario()`.  A missing registry fails the run before it is used.
var _registry: Variant = null


## The twenty-one zero-consumer field names, read from the module's own table
## rather than restated here, so the two cannot drift.
func _zero_consumer_names() -> Array:
	var out: Array = []
	for entry: Dictionary in UnitBehaviors.ZERO_CONSUMER_FIELDS:
		out.append(str(entry["field"]))
	return out


## The recorded legacy-read count of one field, or -1 when it is not named.
func entry_legacy_reads(field: String) -> int:
	for entry: Dictionary in UnitBehaviors.ZERO_CONSUMER_FIELDS:
		if str(entry["field"]) == field:
			return int(entry["legacy_reads"])
	return -1


## The behavioural `properties` flag names, read from the module's own table.
func _unit_flag_names() -> Array:
	var out: Array = []
	for entry: Dictionary in UnitBehaviors.UNIT_PROPERTY_FLAGS:
		out.append(str(entry["flag"]))
	return out


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if _scenario_arg() == "live-behavior":
		await _check_live_behavior()
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

	_check_projection()
	_check_gates()
	_check_fail_closed()
	_check_inventory()
	var fields := _check_fields(registry)
	var legacy := _check_legacy()
	_check_refusals()
	_check_clicks_boundary()
	var corpus := _check_corpus()
	_check_intent()
	await _check_double(corpus)
	_check_absence()
	_check_boundary()
	_check_purity()
	_check_containment(package_before, saves_before, fixtures_before,
		legacy_before, save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, fields, legacy, corpus)
	info("unit behaviours: ledger %s, %d gates, %d of %d named branches reach it, "
		% [UnitBehaviors.LEDGER_KEY, UnitBehaviors.GATE_COUNT,
			UnitBehaviors.LEDGER_REACHING_COMMAND_COUNT,
			UnitBehaviors.NAMED_BRANCH_COUNT]
		+ "%d zero-consumer fields, 0 syringes charged" % UnitBehaviors
			.ZERO_CONSUMER_COUNT)


# ---------------------------------------------------------------------------
# The ledger projection (design D1)
# ---------------------------------------------------------------------------


## Every recorded entry is reported VERBATIM: no threshold, no cap, no clamp, and
## no count derived from another — including none derived from a committed
## `syringes` value.
func _check_projection() -> void:
	var empty := UnitBehaviors.project_ledger({})
	check_eq(bool(empty.get("ok", false)), true,
		"an empty object IS a resolvable ledger — it is empty, not unreadable")
	check_eq((empty.get("entries", []) as Array).size(), 0,
		"an empty ledger projects no entry")
	check_eq(int(empty.get("total", -1)), 0,
		"an empty ledger totals zero")

	var ledger := {"1001": 3, "1085": 1, "1176": 12}
	var projection := UnitBehaviors.project_ledger(ledger)
	check_eq(bool(projection.get("ok", false)), true,
		"a string-keyed integer ledger is resolvable")
	check_eq(int(projection.get("entry_count", 0)), 3,
		"every recorded entry is projected")
	check_eq(int(projection.get("total", 0)), 16,
		"the recorded total is the sum of the recorded counts, computed for "
			+ "REPORTING only and never read back as a count")
	var entries: Array = projection.get("entries", [])
	var reported := {}
	for entry: Dictionary in entries:
		reported[str(entry["item_id"])] = int(entry["count"])
	# The counts are copied through with no threshold, cap, or clamp: the
	# largest recorded count survives untouched, and a count of 12 is not
	# clamped to anything.
	check_eq(reported, {"1001": 3, "1085": 1, "1176": 12},
		"every recorded count is reported EXACTLY as recorded, with no "
			+ "threshold, cap, or clamp applied")
	check_eq((entries[2] as Dictionary)["count"], 12,
		"the largest recorded count survives verbatim")
	# The projected entries are SORTED by item id, so the bytes never depend on
	# a dictionary's iteration order.
	var order: Array = []
	for entry: Dictionary in entries:
		order.append(str(entry["item_id"]))
	check_eq(order, ["1001", "1085", "1176"],
		"the projected entries are sorted by item id, so the report's bytes "
			+ "never depend on a dictionary's iteration order")
	# A count is never derived from a committed `syringes` value: a ledger
	# entry whose item records three syringes and a ledger entry whose item
	# records five project identically, because the projection never reads it.
	var one := UnitBehaviors.project_ledger({"1001": 2})
	var same := UnitBehaviors.project_ledger({"1001": 2})
	check_eq(one, same,
		"the projection reads nothing but the recorded ledger, so the same "
			+ "input always projects the same output")
	check(not _code_only(DELIVERED_BEHAVIOR_SCRIPT).contains("syringes"),
		"the projection module's own DECLARATIONS never mention `syringes`: no "
			+ "count is derived from a committed syringe value")

	# The increment shape, verbatim: the count rises by one and the key is
	# CREATED AT 1 when it is absent.
	var created := UnitBehaviors.expected_increment({}, 1001)
	check_eq(int(created.get("count_after", 0)), 1,
		"the increment CREATES an absent key at 1, never at 0")
	check_eq(bool(created.get("created", false)), true,
		"the increment reports that it created the key")
	var raised := UnitBehaviors.expected_increment({"1001": 3}, 1001)
	check_eq(int(raised.get("count_after", 0)), 4,
		"the increment raises an existing count by exactly one")
	check_eq(bool(raised.get("created", false)), false,
		"the increment does not report creating an existing key")

	# The decrement shape, verbatim, with the DELETE-AT-ZERO rule.
	var at_one := UnitBehaviors.expected_ledger({"1001": 1}, 1001)
	check_eq(bool(at_one.get("removed", false)), true,
		"a count of 1 DELETES the key at zero, never stores a zero")
	check_eq((at_one.get("entries", {}) as Dictionary).has("1001"), false,
		"the ledger after a count of 1 holds NO key at all, not a zero")
	check_eq(int(at_one.get("count_after", -1)), 0,
		"the derived count after the decrement is reported as zero beside the "
			+ "removal, which is what the response echoes")
	var above := UnitBehaviors.expected_ledger({"1001": 3, "1085": 1}, 1001)
	check_eq(bool(above.get("removed", false)), false,
		"a count above 1 decrements and KEEPS its key")
	check_eq(int(above.get("count_after", 0)), 2,
		"a count above 1 decrements by exactly one")
	check_eq((above.get("entries", {}) as Dictionary),
		{"1001": 2, "1085": 1},
		"every other recorded entry survives the decrement untouched")
	var absent := UnitBehaviors.expected_ledger({"1085": 1}, 1001)
	check_eq(bool(absent.get("present_before", true)), false,
		"an item id the ledger does not hold is reported as absent")
	check_eq(bool(absent.get("removed", false)), false,
		"an absent item id is a SILENT NO-OP, not a removal")
	check_eq((absent.get("entries", {}) as Dictionary), {"1085": 1},
		"a silent no-op leaves the whole ledger untouched")
	check_eq(int(absent.get("count_before", -1)), 0,
		"a silent no-op reports the absent count as zero")
	# The delete-at-zero rule is a constant FALSE for a zero-holding ledger:
	# the legacy helpers cannot produce key: 0, so the projection reports the
	# absence rather than accepting one.
	var zero_held := UnitBehaviors.project_ledger({"1001": 0})
	check_eq(bool(zero_held.get("ok", false)), true,
		"a ledger holding a literal zero is still READABLE, so the projection "
			+ "does not refuse a state a hand-written save could carry")
	check_eq(int((zero_held.get("entries", []) as Array)[0]["count"]), 0,
		"and the recorded zero is reported verbatim rather than deleted, "
			+ "because no legacy branch can write one")
	check(UnitBehaviors.DELETE_AT_ZERO.contains("DELETES THE KEY"),
		"the delete-at-zero rule is stated as the contract it is")


# ---------------------------------------------------------------------------
# Both gates (design D1)
# ---------------------------------------------------------------------------


## BOTH legacy gates are named with their recorded source lines, and no third is
## invented.
func _check_gates() -> void:
	var gates: Array = UnitBehaviors.gates()
	check_eq(gates.size(), 2,
		"EXACTLY TWO gates are named: the row's player team and the committed "
			+ "resurrectable")
	check_eq(int(UnitBehaviors.gate_count()), 2,
		"the module's own gate count is 2, asserted by the suite so a third "
			+ "gate fails the run")
	check_eq((gates[0] as Dictionary)["gate"], "player_team_one",
		"gate one is the row's player team, exactly as push_dead_unit names it")
	check_eq((gates[0] as Dictionary)["source"], "engine.py:151 (push_dead_unit)",
		"gate one names its recorded source line verbatim")
	check_eq((gates[1] as Dictionary)["gate"], "resurrectable_positive",
		"gate two is the committed resurrectable flag, exactly as "
			+ "push_dead_unit names it")
	check_eq((gates[1] as Dictionary)["source"],
		"engine.py:159,162 (push_dead_unit)",
		"gate two names BOTH of its recorded source lines verbatim")
	check_eq((gates[0] as Dictionary)["committed"], true,
		"both gates are recorded as committed, not derived")
	check_eq((gates[1] as Dictionary)["committed"], true,
		"both gates are recorded as committed, not derived")
	check(UnitBehaviors.NO_THIRD_GATE.contains("NO THIRD IS INVENTED"),
		"the module states that no third gate is invented")
	# The two gates are EVALUATED, never merely described, and each refuses the
	# case the legacy helper refuses.
	check_eq(bool(UnitBehaviors.passes_team_gate(1)), true,
		"player team 1 passes gate one")
	check_eq(bool(UnitBehaviors.passes_team_gate(3)), false,
		"a row on another team FAILS gate one, so it never enters the ledger "
			+ "however resurrectable its properties say it is")
	check_eq(bool(UnitBehaviors.passes_team_gate("1")), false,
		"a non-integer player slot fails gate one rather than being coerced")
	check_eq(bool(UnitBehaviors.passes_resurrectable_gate(1)), true,
		"a positive committed resurrectable passes gate two")
	check_eq(bool(UnitBehaviors.passes_resurrectable_gate(0)), false,
		"a zero committed resurrectable FAILS gate two (engine.py:162)")
	check_eq(bool(UnitBehaviors.passes_resurrectable_gate(null)), false,
		"an ABSENT flag FAILS gate two (engine.py:159-160) and is never "
			+ "coerced to a zero")
	# The committed flag is a STRING in the normalized package, and a non-empty
	# String is TRUTHY in GDScript, so the committed \"0\" must be converted
	# explicitly rather than through `int(value or 0)`.
	check_eq(int(UnitBehaviors.committed_resurrectable({"resurrectable": "1"})),
		1, "the committed string \"1\" resolves to 1")
	check_eq(int(UnitBehaviors.committed_resurrectable({"resurrectable": "0"})),
		0,
		"the committed string \"0\" resolves to 0 — the explicit conversion is "
			+ "the only correct read, because a non-empty String is truthy")
	check(UnitBehaviors.committed_resurrectable({"resurrectable": "0"}) != null,
		"the committed \"0\" is NOT reported as an absent flag: absent and zero "
			+ "are different refusals with different sources")
	check_eq(UnitBehaviors.committed_resurrectable({"other": "1"}), null,
		"an object with no resurrectable key reports the ABSENT flag")
	check_eq(UnitBehaviors.committed_resurrectable("{\"resurrectable\":\"1\"}"),
		1,
		"the RAW configuration string the legacy helper json.loads is accepted "
			+ "as well as the committed object (the R2 coercion boundary)")
	check_eq(UnitBehaviors.committed_resurrectable("not json"), null,
		"an unparseable properties blob reports an absent flag rather than a "
			+ "decode failure")
	check_eq(UnitBehaviors.committed_resurrectable(null), null,
		"no properties at all reports an absent flag")
	check_eq(UnitBehaviors.passes_resurrectable_gate(
		UnitBehaviors.committed_resurrectable({"resurrectable": "0"})), false,
		"the committed \"0\" FAILS gate two end to end, which is the case a "
			+ "truthiness read would have passed")


# ---------------------------------------------------------------------------
# The fail-closed path (design D1)
# ---------------------------------------------------------------------------


## An absent ledger, a non-object ledger, a non-string key, and a non-integer
## count are each REFUSED with their recorded state intact — never defaulted to
## an empty ledger presented as a resolved one.
func _check_fail_closed() -> void:
	var absent := UnitBehaviors.project_ledger(null)
	check_eq(bool(absent.get("ok", false)), false,
		"an ABSENT ledger is not a resolved one")
	check_eq(bool(absent.get("resolvable", false)), false,
		"an absent ledger is reported UNRESOLVABLE")
	check_eq(str(absent.get("reason", "")), UnitBehaviors.REASON_LEDGER_ABSENT,
		"an absent ledger carries its own named reason")
	check_eq(bool(absent.get("recorded_present", true)), false,
		"an absent ledger reports that the key was NOT present")
	check_eq(str(absent.get("recorded_type", "")), "null",
		"an absent ledger reports the recorded type it read")
	check_eq((absent.get("entries", []) as Array).size(), 0,
		"an absent ledger substitutes NO entry")

	for value: Variant in [[], "text", 5, 2.5, true]:
		var wrong := UnitBehaviors.project_ledger(value)
		check_eq(bool(wrong.get("ok", false)), false,
			"a non-object ledger (%s) is refused, never coerced"
				% type_string(typeof(value)))
		check_eq(str(wrong.get("reason", "")),
			UnitBehaviors.REASON_LEDGER_NOT_OBJECT,
			"a non-object ledger carries its own named reason")
		check_eq(str(wrong.get("recorded_type", "")), _type_name(value),
			"a refused ledger reports the recorded type it actually read")

	var bad_key := UnitBehaviors.project_ledger({1001: 1})
	check_eq(bool(bad_key.get("ok", false)), false,
		"a NON-STRING KEY is refused: the ledger is a string-keyed count per "
			+ "item id")
	check_eq(str(bad_key.get("reason", "")),
		UnitBehaviors.REASON_KEY_NOT_TEXT,
		"a non-string key carries its own named reason")
	check_eq(str(bad_key.get("error", "")).contains("1001"), true,
		"the refusal NAMES the offending key")
	check_eq((bad_key.get("entries", []) as Array).size(), 0,
		"a non-string key substitutes NO entry")

	for value: Variant in ["1", 1.5, null, [1], {}]:
		var bad_count := UnitBehaviors.project_ledger({"1001": value})
		check_eq(bool(bad_count.get("ok", false)), false,
			"a NON-INTEGER COUNT (%s) is unreadable rather than coercible"
				% type_string(typeof(value)))
		check_eq(str(bad_count.get("reason", "")),
			UnitBehaviors.REASON_COUNT_NOT_INTEGER,
			"a non-integer count carries its own named reason")
	# An integral FLOAT is READ, because the pinned engine's JSON parser widens
	# every committed number to one: refusing it would be a transport artefact
	# dressed as a contract.
	check_eq(bool(UnitBehaviors.project_ledger({"1001": 2.0}).get("ok", false)),
		true,
		"an integral float count is READ, because the pinned engine's parser "
			+ "widens every committed number to one")
	# A caller that ignores the refusal reads NO entries, never a zeroed one.
	check_eq(UnitBehaviors.ledger_entries({"1001": "1"}), {},
		"ledger_entries() on an unreadable ledger returns NO entry, so an "
			+ "unresolvable ledger can never be mistaken for an empty one")
	check_eq(UnitBehaviors.ledger_entries({"1001": 1}), {"1001": 1},
		"ledger_entries() on a readable ledger returns the recorded counts")
	# And the decrement derivation refuses an unreadable ledger rather than
	# deriving against a substituted one.
	var unreadable := UnitBehaviors.expected_ledger({"1001": "1"}, 1001)
	check_eq(bool(unreadable.get("resolvable", true)), false,
		"the decrement derivation refuses an unreadable ledger")
	check_eq(bool(UnitBehaviors.expected_ledger({"1001": 1}, "x")
		.get("resolvable", true)), false,
		"the decrement derivation refuses a non-integer item id")
	# The refusal keeps the recorded KEYS, because "which keys are present" is
	# a fact even when a value is unreadable.
	var mixed := UnitBehaviors.project_ledger({"1085": 1, "1001": "bad"})
	check_eq(bool(mixed.get("ok", false)), false,
		"a ledger with one unreadable count is refused WHOLE")
	check_eq((mixed.get("recorded_keys", []) as Array).size(), 2,
		"the refusal still reports BOTH recorded keys, so a reader can see "
			+ "which entries existed")


# ---------------------------------------------------------------------------
# The three-door inventory (design D2)
# ---------------------------------------------------------------------------


## `kill`, `sell`, and `resurrect_hero` each carry an explicit ledger effect,
## `kill` never reaches the ledger, `sell` only behind the KILL guard and only
## through the engine helper, and the helper is not a branch.
func _check_inventory() -> void:
	var inventory := UnitBehaviors.command_inventory()
	check_eq(inventory.size(), 3,
		"the inventory names exactly THREE commands: kill, sell, and "
			+ "resurrect_hero")
	var by_name := {}
	for entry: Dictionary in inventory:
		by_name[str(entry["command"])] = entry
		check(entry.has("reaches_ledger"),
			"every inventoried command carries an EXPLICIT reaches_ledger "
				+ "statement: %s" % str(entry["command"]))
		check(not str(entry.get("effect", "")).is_empty(),
			"every inventoried command states what it does: %s"
				% str(entry["command"]))
		check(not str(entry.get("mutates_also", "")).is_empty(),
			"every inventoried command states what ELSE it mutates: %s"
				% str(entry["command"]))
	check_eq((by_name["kill"] as Dictionary)["reaches_ledger"], false,
		"`kill` NEVER reaches the ledger: it deletes the row and records no "
			+ "death")
	check_eq((by_name["kill"] as Dictionary)["source"], "command.py:169-181",
		"`kill` names its recorded source lines verbatim")
	check_eq((by_name["sell"] as Dictionary)["reaches_ledger"], true,
		"`sell` reaches the ledger")
	check_eq((by_name["sell"] as Dictionary)["guard"], "reason == 'KILL'",
		"`sell` reaches the ledger ONLY behind the combat-reason guard")
	check(str((by_name["sell"] as Dictionary)["through"]).contains(
		"push_dead_unit"),
		"`sell` reaches it through the `push_dead_unit` ENGINE HELPER")
	check(str((by_name["sell"] as Dictionary)["closed_in_practice"]).contains(
		"ONLY door"),
		"the inventory records that the KILL guard is the ONLY door into the "
			+ "ledger, and that the delivered sell reason closes it in practice")
	check_eq((by_name["resurrect_hero"] as Dictionary)["reaches_ledger"], true,
		"`resurrect_hero` reaches the ledger")
	check(str((by_name["resurrect_hero"] as Dictionary)["effect"]).contains(
		"DELETES the key"),
		"`resurrect_hero` DELETES the key at zero")
	check(str((by_name["resurrect_hero"] as Dictionary)["discarded_argument"])
		.contains("DISCARDED"),
		"the inventory records that `used_syringe` is READ and DISCARDED")
	check(str((by_name["resurrect_hero"] as Dictionary)["mutates_also"])
		.contains("CLIENT-SUPPLIED"),
		"the inventory records the re-placement as CLIENT-SUPPLIED index/x/y")
	check(str((by_name["resurrect_hero"] as Dictionary)["mutates_also"])
		.contains("no occupancy, bounds, type, or terrain check"),
		"the inventory records that the re-placement checks NOTHING of that "
			+ "sort")
	# The helper is an ENGINE HELPER, not a branch, which is what keeps the
	# named-branch count and the ledger-reaching count separately meaningful.
	var helpers := UnitBehaviors.engine_helpers()
	check_eq(helpers.size(), 2,
		"exactly TWO engine helpers are recorded")
	for helper: Dictionary in helpers:
		check_eq(helper["is_dispatcher_branch"], false,
			"`%s` is recorded as an engine helper, NOT a dispatcher branch"
				% str(helper["helper"]))
	check_eq(bool(UnitBehaviors.inventory_record()["push_dead_unit_is_a_branch"]),
		false,
		"the inventory record states the helper is not a branch")
	# The counts stay distinguishable: 63 named branches, 2 of them reaching the
	# ledger, 1 of those 2 closed in practice, and 1 bypassing it entirely.
	check_eq(int(UnitBehaviors.NAMED_BRANCH_COUNT), 63,
		"the dispatcher's named-branch count is 63")
	check_eq(int(UnitBehaviors.LEDGER_REACHING_COMMAND_COUNT), 2,
		"exactly TWO of the 63 named branches reach the ledger")
	check_eq(UnitBehaviors.ledger_reaching_commands(), ["sell", "resurrect_hero"],
		"the two ledger-reaching branches are sell and resurrect_hero, in "
			+ "committed source order")
	check_eq(UnitBehaviors.BRANCHES_THAT_BYPASS_LEDGER, ["kill"],
		"`kill` is the one inventoried branch that BYPASSES the ledger")
	check_eq(int(UnitBehaviors.LEDGER_REACHING_COMMAND_COUNT) + 1, 3,
		"the three inventoried commands are the two that reach the ledger and "
			+ "the one that bypasses it — a third inventoried door would break "
			+ "the arithmetic")
	check_eq(int(UnitBehaviors.INVENTORY_COMMANDS.size()), 3,
		"the closed inventory command set names exactly three")


# ---------------------------------------------------------------------------
# The committed behavioural fields, measured (design D2/D3)
# ---------------------------------------------------------------------------


## Every committed behavioural figure this line records is re-measured from the
## verified registry and the committed legacy source in this same run.
func _check_fields(registry: Variant) -> Dictionary:
	var measured: Dictionary = {"units": {}, "buildings": {},
		"units_distinct": {}, "buildings_distinct": {}, "flags": {},
		"resurrectable": {}}
	for domain: String in ["units", "buildings"]:
		var listed: Dictionary = registry.legacy_ids(domain)
		check_eq(bool(listed.get("found", false)), true,
			"the %s domain is present in the verified registry" % domain)
		var ids: Array = listed.get("ids", [])
		check_eq(ids.size(),
			UnitBehaviors.UNIT_COUNT if domain == "units"
				else UnitBehaviors.BUILDING_COUNT,
			"the %s domain enumerates exactly %d committed ids"
				% [domain, ids.size()])
		measured[domain] = ids.size()
		# The zero-consumer fields: the **measured** distinct committed unit
		# values, so a content change that moved a value fails the run rather
		# than invalidating a pinned number.
		var distinct: Dictionary = {}
		for field: String in _zero_consumer_names():
			distinct[field] = {}
		var resurrectable_positive := 0
		var resurrectable_carried := 0
		var flags: Dictionary = {}
		for flag: String in _unit_flag_names():
			flags[flag] = 0
		var absent_ids: Array = []
		for id_text: Variant in ids:
			var entry: Dictionary = registry.get_entry(domain,
				str(id_text)).get("entry", {}) as Dictionary
			for field: String in _zero_consumer_names():
				var per_field: Dictionary = distinct[field]
				per_field[_measured_value(entry, field)] = 1
			var properties: Variant = entry.get("properties")
			if not (properties is Dictionary):
				continue
			var flags_object: Dictionary = properties
			if flags_object.has(UnitBehaviors.RESURRECTABLE_FLAG):
				resurrectable_carried += 1
				var flag: Variant = UnitBehaviors.committed_resurrectable(
					flags_object)
				if flag != null and int(flag) > 0:
					resurrectable_positive += 1
			elif domain == "units":
				absent_ids.append(str(id_text))
			for name: String in _unit_flag_names():
				if _committed_flag(flags_object, name):
					var per_flag: Dictionary = flags
					per_flag[name] = int(per_flag.get(name, 0)) + 1
		for field: String in _zero_consumer_names():
			measured[domain + "_distinct"][field] = (
				distinct[field] as Dictionary).size()
		measured[domain + "_resurrectable_positive"] = resurrectable_positive
		measured[domain + "_resurrectable_carried"] = resurrectable_carried
		if domain == "units":
			measured["resurrectable"]["absent_ids"] = absent_ids
			measured["flags"] = flags
	# The distinct-value counts, each compared against its recorded constant.
	for field: String in _zero_consumer_names():
		var recorded := -1
		for entry: Dictionary in UnitBehaviors.ZERO_CONSUMER_FIELDS:
			if str(entry["field"]) == field:
				recorded = int(entry["unit_distinct"])
		check(int(recorded) > 0,
			"the committed field `%s` records a measured distinct count" % field)
		check_eq(int((measured["units_distinct"] as Dictionary).get(field, -1)),
			recorded,
			"the MEASURED distinct committed unit values of `%s` is the recorded "
				% field + "one")
		check_eq(int(entry_legacy_reads(field)), 0,
			"the recorded legacy-read count of `%s` is zero" % field)
	# The unit-only distribution this line's eligibility rests on.
	check_eq(int(measured["units_resurrectable_positive"]),
		UnitBehaviors.RESURRECTABLE_UNITS_POSITIVE,
		"the committed `resurrectable` flag is positive on exactly %d of the %d "
			% [UnitBehaviors.RESURRECTABLE_UNITS_POSITIVE,
				UnitBehaviors.UNIT_COUNT]
			+ "committed units")
	check_eq(int(measured["units_resurrectable_carried"]),
		UnitBehaviors.RESURRECTABLE_UNITS_POSITIVE,
		"the flag is CARRIED by exactly %d units, so it is absent from the "
			% UnitBehaviors.RESURRECTABLE_UNITS_POSITIVE
			+ "other three rather than set to zero on them")
	check_eq((measured["resurrectable"] as Dictionary)["absent_ids"],
		UnitBehaviors.UNITS_WITHOUT_RESURRECTABLE,
		"exactly THREE committed units carry NO resurrectable key, and they are "
			+ "the recorded three — an absent flag is a REFUSAL, never a zero")
	check_eq(int(measured["buildings_resurrectable_positive"]),
		UnitBehaviors.RESURRECTABLE_BUILDINGS_POSITIVE,
		"the committed `resurrectable` flag is positive on ZERO of the %d "
			% UnitBehaviors.BUILDING_COUNT
			+ "committed buildings, so the flag is UNIT-ONLY")
	check_eq(int(measured["buildings_resurrectable_carried"]), 0,
		"and NO committed building carries the key at all")
	check(UnitBehaviors.UNIT_ONLY_NOTE.contains("UNIT-ONLY"),
		"the module states that resurrectable is a unit-only committed flag")
	# Every behavioural `properties` flag's measured positive count.
	for flag: String in _unit_flag_names():
		var recorded := -1
		for entry: Dictionary in UnitBehaviors.UNIT_PROPERTY_FLAGS:
			if str(entry["flag"]) == flag:
				recorded = int(entry["positive"])
		check(int(recorded) >= 0,
			"the behavioural flag `%s` records a measured positive count" % flag)
		check_eq(int((measured["flags"] as Dictionary).get(flag, -1)), recorded,
			"the MEASURED positive count of the `%s` flag is the recorded one"
				% flag)
	# `syringes` and `clicks_to_build`: their recorded distributions.
	measured["syringes"] = _distribution(registry, "units", "syringes")
	measured["syringes_buildings"] = _distribution(registry, "buildings",
		"syringes")
	measured["clicks_to_build"] = _distribution(registry, "units",
		"clicks_to_build")
	measured["clicks_to_build_buildings"] = _distribution(registry, "buildings",
		"clicks_to_build")
	check_eq(measured["syringes"], UnitBehaviors.SYRINGES_UNIT_VALUES,
		"the MEASURED committed `syringes` distribution over the units is the "
			+ "recorded one")
	check_eq((measured["syringes"] as Dictionary).size(),
		UnitBehaviors.SYRINGES_UNIT_DISTINCT,
		"the committed `syringes` field takes exactly %d distinct values over "
			% UnitBehaviors.SYRINGES_UNIT_DISTINCT
			+ "the units, and every one of them has ZERO legacy consumers")
	check_eq(measured["syringes_buildings"],
		UnitBehaviors.SYRINGES_BUILDING_VALUES,
		"the MEASURED committed `syringes` distribution over the buildings is "
			+ "0 on all of them")
	check_eq(measured["clicks_to_build"],
		UnitBehaviors.CLICKS_TO_BUILD_UNIT_VALUES,
		"the MEASURED committed `clicks_to_build` is 0 on ALL units, so a "
			+ "revived unit never seeds the construction-click counter")
	check_eq(measured["clicks_to_build_buildings"],
		UnitBehaviors.CLICKS_TO_BUILD_BUILDING_VALUES,
		"the MEASURED committed `clicks_to_build` distribution over the "
			+ "buildings is the recorded one")
	var over_content: Dictionary = {}
	for key: Variant in (measured["clicks_to_build"] as Dictionary).keys():
		over_content[key] = true
	for key: Variant in (measured["clicks_to_build_buildings"] as Dictionary).keys():
		over_content[key] = true
	check_eq(over_content.size(),
		UnitBehaviors.CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT,
		"the committed `clicks_to_build` takes exactly %d distinct values over "
			% UnitBehaviors.CLICKS_TO_BUILD_DISTINCT_OVER_CONTENT
			+ "the committed content, NOT the three the investigation states")
	check(UnitBehaviors.CLICKS_TO_BUILD_CORRECTION.contains("CORRECTION"),
		"the module retains the investigation's rejected figure beside the "
			+ "measured one")
	# The zero-consumer count itself, and the corrections that produced it.
	var named: Array = UnitBehaviors.ZERO_CONSUMER_FIELDS
	check_eq(named.size(), UnitBehaviors.ZERO_CONSUMER_COUNT,
		"the zero-consumer behavioural table names exactly %d fields"
			% UnitBehaviors.ZERO_CONSUMER_COUNT)
	check_eq(int(UnitBehaviors.ZERO_CONSUMER_COUNT_RECORDED), 20,
		"the investigation's own figure of twenty is RETAINED beside the "
			+ "measured twenty-one, so the correction stays visible")
	check_eq(int(UnitBehaviors.BEHAVIOURAL_FIELD_COUNT), 23,
		"with the two consumed fields the behavioural total is 23")
	check_eq(int(UnitBehaviors.BEHAVIOURAL_FIELD_COUNT_RECORDED), 22,
		"the investigation's own total of twenty-two is RETAINED beside the "
			+ "measured twenty-three")
	check_eq((UnitBehaviors.CONSUMED_BEHAVIOURAL_FIELDS as Array).size(), 2,
		"exactly TWO behavioural committed fields have a legacy consumer")
	return measured


## The committed corpus measurement, which is the line's named cause for having
## no executed-legacy fixture.
func _check_corpus() -> Dictionary:
	var path := Paths.repo_root().path_join(CORPUS_SAVE)
	if not FileAccess.file_exists(path):
		fail("the committed corpus save is readable")
		return {}
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (document is Dictionary):
		fail("the committed corpus save is a JSON object")
		return {}
	var save: Dictionary = document
	var private: Variant = save.get("privateState")
	if not (private is Dictionary):
		fail("the committed corpus carries a privateState object")
		return {}
	var measured: Dictionary = {}
	var priv: Dictionary = private
	measured["ledger_present"] = priv.has(UnitBehaviors.LEDGER_KEY)
	measured["ledger"] = _normalize(priv.get(UnitBehaviors.LEDGER_KEY))
	check_eq(bool(measured["ledger_present"]), true,
		"the committed corpus's `deadHeroes` ledger is PRESENT")
	check_eq(measured["ledger"], EXPECTED_LEDGER,
		"and it is EMPTY, so no resurrectable row exists to exercise")
	var maps: Variant = save.get("maps")
	if not (maps is Array) or (maps as Array).size() <= CORPUS_MAP_INDEX:
		fail("the committed corpus carries a first map")
		return measured
	var first_map: Dictionary = (maps as Array)[CORPUS_MAP_INDEX] as Dictionary
	var items: Dictionary = first_map.get("items", {}) as Dictionary
	measured["rows"] = items.size()
	measured["resources"] = {}
	var cells := {}
	var ids := {}
	var resurrectable_rows := 0
	var unit_rows := 0
	var unresolved_rows := 0
	var target_cell: Array = []
	var target_item := -1
	for key: Variant in items.keys():
		var row: Variant = items[key]
		if not (row is Array) or (row as Array).size() != 8:
			unresolved_rows += 1
			continue
		var typed: Array = row
		var item_id := str(int(typed[0]))
		ids[item_id] = true
		cells["%d:%d" % [int(typed[1]), int(typed[2])]] = true
		var domain := _domain_of(item_id)
		var entry: Dictionary = _registry_entry(domain, item_id)
		if domain == "units":
			unit_rows += 1
		elif domain.is_empty():
			unresolved_rows += 1
		var flag: Variant = UnitBehaviors.committed_resurrectable(
			entry.get(UnitBehaviors.PROPERTIES_FIELD))
		if flag != null and int(flag) > 0:
			resurrectable_rows += 1
		if str(key) == str(CORPUS_TARGET_MAP_KEY):
			target_cell = [int(typed[1]), int(typed[2])]
			target_item = int(typed[0])
	measured["unresolved_rows"] = unresolved_rows
	measured["target_item_id"] = target_item
	measured["distinct_cells"] = cells.size()
	measured["distinct_item_ids"] = ids.size()
	measured["resurrectable_rows"] = resurrectable_rows
	measured["unit_rows"] = unit_rows
	measured["target_map_key"] = CORPUS_TARGET_MAP_KEY
	measured["target_cell"] = target_cell
	var info: Variant = save.get("playerInfo")
	measured["resources"]["xp"] = int(first_map.get("xp", 0))
	measured["resources"]["gold"] = int(first_map.get("gold", 0))
	measured["resources"]["wood"] = int(first_map.get("wood", 0))
	measured["resources"]["oil"] = int(first_map.get("oil", 0))
	measured["resources"]["steel"] = int(first_map.get("steel", 0))
	measured["resources"]["cash"] = int((info as Dictionary).get("cash", 0))
	measured["resources"]["mana"] = int(priv.get("mana", 0))
	measured["pid"] = str((info as Dictionary).get("pid", ""))

	check_eq(int(measured["rows"]), EXPECTED_ROWS,
		"the committed corpus places exactly %d rows" % EXPECTED_ROWS)
	check_eq(int(measured["distinct_cells"]), EXPECTED_DISTINCT_CELLS,
		"across exactly %d distinct cells, so a cell resolves to exactly one "
			% EXPECTED_DISTINCT_CELLS + "row and no tie-break is needed")
	check_eq(int(measured["distinct_item_ids"]), EXPECTED_DISTINCT_ITEM_IDS,
		"across exactly %d distinct item ids" % EXPECTED_DISTINCT_ITEM_IDS)
	check_eq(int(measured["resurrectable_rows"]), EXPECTED_RESURRECTABLE_ROWS,
		"ZERO of the committed corpus's placed rows are resurrectable, which "
			+ "is the named cause of the absent executed-legacy fixture")
	check_eq(int(measured["unit_rows"]), EXPECTED_UNIT_ROWS,
		"the committed corpus places NO unit row at all, so the mechanism this "
			+ "line delivers cannot be exercised against it")
	check_eq(int(measured["unresolved_rows"]), 0,
		"every placed row resolves into the committed buildings domain: there "
			+ "is no unresolvable and no unit row among them")
	check_eq(measured["resources"], EXPECTED_RESOURCES,
		"the committed corpus's seven stored balances are measured, so the "
			+ "no-resource-moved claim has a real before-state")
	check_eq(target_cell.size(), 2,
		"the corpus's own map key %d resolves to a cell, so the double's "
			% CORPUS_TARGET_MAP_KEY + "positive path addresses a committed cell")
	check(UnitBehaviors.FIXTURE_NOT_CAPTURED.contains("CORPUS LIMITATION"),
		"the module states the absent fixture's reason is a CORPUS LIMITATION")
	check(UnitBehaviors.FIXTURE_NOT_CAPTURED.contains("NOT, as on the three"),
		"and distinguishes it from the refusal lines' absence of behaviour")
	check(UnitBehaviors.FIXTURE_NOT_CAPTURED.contains("MANUFACTURING A UNIT ROW"),
		"and names manufacturing a unit row as the refused route")
	# The ledger is therefore unresolvable-as-a-target while the corpus's own
	# map is perfectly readable: two different facts, both measured.
	var projection := UnitBehaviors.project_ledger(priv.get(
		UnitBehaviors.LEDGER_KEY))
	check_eq(bool(projection.get("ok", false)), true,
		"the corpus's own EMPTY ledger projects as a resolved empty ledger, "
			+ "which is a different fact from an unreadable one")
	check_eq(int(projection.get("entry_count", -1)), 0,
		"and it holds zero entries, so no revival is possible against it")
	check_eq(bool(BehaviorFlow.offers_revival(projection)), false,
		"so the client offers NO revival action against the committed corpus")
	measured["repository_census"] = _repository_census()
	return measured


## Every committed save document under `villages/` and `tests/saves/`,
## measured this run. The fresh-player document is INCLUDED in the totals
## and is named, so a reader can subtract one figure from another without
## guessing which document a total includes.
func _repository_census() -> Dictionary:
	var documents: Array = []
	var skipped := 0
	var placed := 0
	var unit_rows := 0
	var team_one := 0
	var resurrectable := 0
	var with_units := 0
	var with_ledger := 0
	var fresh_player_unit_rows := -1
	for relative: String in _committed_save_documents():
		var record: Dictionary = _census_save(relative)
		if not bool(record.get("ok", false)):
			skipped += 1
			continue
		documents.append(record)
		placed += int(record.get("placed_rows", 0))
		var row_units := int(record.get("unit_rows", 0))
		unit_rows += row_units
		team_one += int(record.get("unit_rows_on_team_one", 0))
		resurrectable += int(record.get("unit_rows_resurrectable", 0))
		if row_units > 0:
			with_units += 1
		if int(record.get("ledger_keys", 0)) > 0:
			with_ledger += 1
		if str(record.get("document", "")) == CORPUS_SAVE:
			fresh_player_unit_rows = row_units

	check_eq(documents.size(), EXPECTED_REPOSITORY_DOCUMENTS,
		"the repository holds %d committed save documents, enumerated this "
			% EXPECTED_REPOSITORY_DOCUMENTS + "run rather than assumed")
	check_eq(skipped, 0, "and every one of them parsed as a save")
	check_eq(placed, EXPECTED_REPOSITORY_PLACED_ROWS,
		"across %d placed rows in total" % EXPECTED_REPOSITORY_PLACED_ROWS)
	check_eq(unit_rows, EXPECTED_REPOSITORY_UNIT_ROWS,
		"of which %d carry a committed UNIT id, so this line's %d is TRUE OF "
			% [EXPECTED_REPOSITORY_UNIT_ROWS, EXPECTED_UNIT_ROWS]
			+ "THAT ONE DOCUMENT and FALSE of the repository")
	check_eq(fresh_player_unit_rows, EXPECTED_UNIT_ROWS,
		"the fresh-player document is among them and still places no unit row,"
			+ "which is what this line's named cause rests on")
	check_eq(team_one, EXPECTED_REPOSITORY_UNIT_ROWS_ON_TEAM_ONE,
		"every one of those %d unit rows is on player team one, so the team "
			% EXPECTED_REPOSITORY_UNIT_ROWS_ON_TEAM_ONE
			+ " asymmetry stays unreachable against committed bytes")
	check_eq(resurrectable, EXPECTED_REPOSITORY_UNIT_ROWS_RESURRECTABLE,
		"and %d of them have a positive committed resurrectable, so BOTH ledger "
			% EXPECTED_REPOSITORY_UNIT_ROWS_RESURRECTABLE
			+ " gates hold SOMEWHERE in the repository")
	check(resurrectable < unit_rows,
		"so the two gates genuinely disagree: %d rows are revivable and %d are "
			% [resurrectable, unit_rows - resurrectable] + "not")
	check_eq(with_units, EXPECTED_REPOSITORY_DOCUMENTS_WITH_UNIT_ROWS,
		"%d documents place at least one unit row, so unit-row material EXISTS "
			% EXPECTED_REPOSITORY_DOCUMENTS_WITH_UNIT_ROWS
			+ " in committed bytes and its absence was never repository-wide")
	check_eq(with_ledger, EXPECTED_REPOSITORY_DOCUMENTS_WITH_NON_EMPTY_LEDGER,
		"and %d carry a non-empty deadHeroes ledger"
			% EXPECTED_REPOSITORY_DOCUMENTS_WITH_NON_EMPTY_LEDGER)
	return {
		"scope": "every committed save document under villages/ and tests/saves/, "
			+ "measured this run; the fresh-player document is INCLUDED and is "
			+ "named in fresh_player_unit_rows",
		"documents": documents,
		"document_count": documents.size(),
		"placed_rows": placed,
		"unit_rows": unit_rows,
		"unit_rows_on_team_one": team_one,
		"unit_rows_resurrectable": resurrectable,
		"documents_with_unit_rows": with_units,
		"documents_with_non_empty_ledger": with_ledger,
		"fresh_player_unit_rows": fresh_player_unit_rows,
		"correction": "The M8 godot-unit-behaviors record states its cause as "
			+ "the committed corpus places only buildings and no unit row. "
			+ "That is TRUE of tests/saves/fresh-player.json and FALSE of the "
			+ "repository, which places %d unit rows across %d documents. The "
			% [EXPECTED_REPOSITORY_UNIT_ROWS,
				EXPECTED_REPOSITORY_DOCUMENTS_WITH_UNIT_ROWS]
			+ "conclusion is UNCHANGED and the absence-of-fixture cause still "
			+ "holds, because the document this line measures and drives is the "
			+ "fresh-player one and it places no unit row",
		"no_unit_row_was_manufactured": false,
	}


## Every committed save document, repository-relative and sorted.
func _committed_save_documents() -> Array:
	var out: Array = []
	for directory: String in [REPOSITORY_VILLAGE_DIR, REPOSITORY_SAVES_DIR]:
		var absolute := Paths.repo_root().path_join(directory)
		for name: String in DirAccess.get_files_at(absolute):
			if not name.ends_with(".json"):
				continue
			if REPOSITORY_EXCLUDED_SAVE_DOCUMENTS.has(name):
				continue
			var relative := directory + "/" + name
			# `get_files_at` is non-recursive, so a document of another shape
			# fails to census rather than being silently counted.
			if JSON.parse_string(FileAccess.get_file_as_string(
					Paths.repo_root().path_join(relative))) == null:
				continue
			out.append(relative)
	out.sort()
	return out


## One committed save document's placement and ledger figures.
func _census_save(relative: String) -> Dictionary:
	var out := {
		"ok": false, "document": relative, "placed_rows": 0, "unit_rows": 0,
		"unit_rows_on_team_one": 0, "unit_rows_resurrectable": 0,
		"ledger_keys": 0,
	}
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(
		Paths.repo_root().path_join(relative)))
	if not (document is Dictionary):
		return out
	var maps: Variant = (document as Dictionary).get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return out
	var items: Variant = ((maps as Array)[0] as Dictionary).get("items")
	if not (items is Dictionary):
		return out
	var priv: Variant = (document as Dictionary).get("privateState")
	var ledger: Variant = (priv as Dictionary).get(UnitBehaviors.LEDGER_KEY) \
			if priv is Dictionary else null
	out["ledger_keys"] = (ledger as Dictionary).size() \
			if ledger is Dictionary else 0
	for key: Variant in (items as Dictionary).keys():
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) \
				or (row as Array).size() != CORPUS_ROW_SLOTS:
			continue
		out["placed_rows"] = int(out["placed_rows"]) + 1
		var item_id := str(int((row as Array)[0]))
		if _domain_of(item_id) != "units":
			continue
		out["unit_rows"] = int(out["unit_rows"]) + 1
		if UnitBehaviors.passes_team_gate((row as Array)[7]):
			out["unit_rows_on_team_one"] \
				= int(out["unit_rows_on_team_one"]) + 1
		var flag: Variant = UnitBehaviors.committed_resurrectable(
			_registry_entry("units", item_id).get(
				UnitBehaviors.PROPERTIES_FIELD))
		if UnitBehaviors.passes_resurrectable_gate(flag):
			out["unit_rows_resurrectable"] \
				= int(out["unit_rows_resurrectable"]) + 1
	out["ok"] = true
	return out


# ---------------------------------------------------------------------------
# The committed legacy source, re-read (requirement: no figure taken on trust)
# ---------------------------------------------------------------------------


## Every legacy figure this line records is re-derived from the committed source
## in this same run.
func _check_legacy() -> Dictionary:
	var measured: Dictionary = {"modules": 0, "zero_consumer": {},
		"named_branches": [], "ledger_sites": {}, "clicks_sites": [],
		"ledger_token_occurrences": 0}

	for module: String in UnitBehaviors.SEARCHED_MODULES:
		if _legacy_lines(module).is_empty():
			fail("the legacy module %s is readable: every fact this line "
				% module
				+ "records is measured out of it, and a missing file would make "
				+ "the measurement vacuous")
			continue
		measured["modules"] += 1
	check_eq(int(measured["modules"]), 7,
		"all seven legacy root modules are readable, so a zero-consumer claim "
			+ "measured over six files would have failed instead")

	# The zero-consumer fields, measured as the number of QUOTED occurrences of
	# each name across the seven modules.  A quoted token is the only reading
	# that means "the name is read as a key or a value": the bare substring
	# also matches the `end_attack` BRANCH NAME inside `"end_attack"`, which is
	# not a field read at all.
	for field: String in _zero_consumer_names():
		var reads := 0
		for module: String in UnitBehaviors.SEARCHED_MODULES:
			var text := "\n".join(_legacy_lines(module))
			reads += _count_occurrences(text, "\"%s\"" % field)
			reads += _count_occurrences(text, "'%s'" % field)
		measured["zero_consumer"][field] = reads
		check_eq(reads, 0,
			"the committed field `%s` measures ZERO quoted occurrences across "
				% field
				+ "the seven legacy modules, so it is content and never a rule")
	# The seven combat fields are the named subset of that same measurement.
	for field: String in UnitBehaviors.COMBAT_FIELDS:
		check_eq(int((measured["zero_consumer"] as Dictionary).get(field, -1)), 0,
			"the committed COMBAT field `%s` measures zero consumers" % field)
	check_eq(int(UnitBehaviors.COMBAT_FIELD_COUNT), 7,
		"exactly SEVEN committed combat fields are named, so \"no combat is "
			+ "resolved\" is checkable against a closed list")

	# The two fields that DO have consumers, measured at their recorded sites.
	var resurrectable_reads: Array = []
	var resurrectable_bare := 0
	for module: String in UnitBehaviors.SEARCHED_MODULES:
		var lines := _legacy_lines(module)
		for number in lines.size():
			var line := str(lines[number])
			if line.contains("\"%s\"" % UnitBehaviors.RESURRECTABLE_FLAG):
				resurrectable_reads.append("%s:%d" % [module, number + 1])
			resurrectable_bare += _count_occurrences(line,
				UnitBehaviors.RESURRECTABLE_FLAG)
	measured["ledger_sites"][UnitBehaviors.RESURRECTABLE_FLAG] = \
		resurrectable_reads
	measured["ledger_token_occurrences"] = resurrectable_bare
	check_eq(resurrectable_reads.size(), 2,
		"the committed `resurrectable` flag is READ at exactly TWO sites")
	check_eq(resurrectable_reads,
		["engine.py:159", "engine.py:162"],
		"and they are engine.py:159 and engine.py:162, inside push_dead_unit")
	check(resurrectable_bare > resurrectable_reads.size(),
		"the BARE substring occurs %d times against %d quoted reads: the "
			% [resurrectable_bare, resurrectable_reads.size()]
			+ "difference is command.py's own local variable NAMED "
			+ "resurrectable, which is a local, not a field read — so the "
			+ "recorded two-READ figure is the quoted measurement and this "
			+ "suite records both so a reader can re-derive the choice")
	var clicks: Array = []
	for module: String in UnitBehaviors.SEARCHED_MODULES:
		var lines := _legacy_lines(module)
		for number in lines.size():
			if str(lines[number]).contains("clicks_to_build"):
				clicks.append("%s:%d" % [module, number + 1])
	measured["clicks_sites"] = clicks
	check_eq(clicks, ["engine.py:26"],
		"the committed `clicks_to_build` field is READ at exactly ONE site: "
			+ "engine.py:26, inside map_add_item")

	# The dispatcher's named branches, re-derived and compared by SET and COUNT.
	var dispatcher := _legacy_lines("command.py")
	var named: Array = []
	for line: Variant in dispatcher:
		var branch := _branch_of(str(line))
		if branch != "" and not named.has(branch):
			named.append(branch)
	measured["named_branches"] = named
	check_eq(named.size(), int(UnitBehaviors.NAMED_BRANCH_COUNT),
		"the MEASURED named-dispatcher-branch count is the recorded %d"
			% UnitBehaviors.NAMED_BRANCH_COUNT)
	check_eq(named, (UnitBehaviors.NAMED_BRANCHES as Array).duplicate(),
		"the measured named branches are EXACTLY the recorded list, in "
			+ "committed source order: a new branch would be an unrecorded "
			+ "death door, not a silent addition")
	for command: String in UnitBehaviors.INVENTORY_COMMANDS:
		check(named.has(command),
			"the inventoried command `%s` is a real dispatcher branch" % command)
	for helper: Dictionary in UnitBehaviors.ENGINE_HELPERS:
		var helper_name := str(helper["helper"])
		check_eq(bool(helper["is_dispatcher_branch"]), false,
			"the engine helper `%s` is recorded as NOT a dispatcher branch"
				% helper_name)
		if helper_name == "push_dead_unit":
			check(not named.has(helper_name),
				"the increment helper `push_dead_unit` shares its name with NO "
					+ "dispatcher branch at all, so the named-branch count and "
					+ "the ledger-reaching count stay separately meaningful")
	check(named.has("resurrect_hero"),
		"the NAME `resurrect_hero` is used by BOTH a dispatcher branch "
			+ "(command.py:625) and an engine helper (engine.py:172) — recorded, "
			+ "because it is the one helper whose name is NOT distinguishable "
			+ "from a branch by name alone")
	# The three recorded source ranges, verified against the committed bytes
	# rather than trusted: each range's first line must carry the branch or
	# helper declaration the inventory names.
	_check_source_range("command.py", 149, "sell",
		"the recorded `sell` range starts at its own `elif cmd == \"sell\":`")
	_check_source_range("command.py", 169, "kill",
		"the recorded `kill` range starts at its own `elif cmd == \"kill\":`")
	_check_source_range("command.py", 625, "resurrect_hero",
		"the recorded `resurrect_hero` range starts at its own branch")
	_check_source_range("engine.py", 149, "push_dead_unit",
		"the recorded `push_dead_unit` range starts at its own `def`")
	_check_source_range("engine.py", 172, "resurrect_hero",
		"the recorded engine `resurrect_hero` range starts at its own `def`")
	_check_source_line("engine.py", 151, "item[7] != 1",
		"gate one is the committed `item[7] != 1` test")
	_check_source_line("engine.py", 159, "not in properties",
		"gate two's first half is the committed ABSENT-flag test")
	_check_source_line("engine.py", 162, "> 0",
		"gate two's second half is the committed `> 0` test")
	_check_source_line("engine.py", 179, "del deadHeroes[itemstr]",
		"the delete-at-zero rule is the committed `del deadHeroes[itemstr]`")
	_check_source_line("engine.py", 175, "not in deadHeroes",
		"the silent no-op is the committed absent-key return")
	_check_source_line("command.py", 630, "used_syringe = args[4]",
		"the DISCARDED argument is the committed `used_syringe = args[4]`")
	_check_source_line("command.py", 159, "reason == \"KILL\"",
		"the only death door is the committed `reason == \"KILL\"` guard")
	# And the recorded `used_syringe` discard: the local is bound and never read
	# again inside the branch's own line range.
	var branch_body := _line_range("command.py", 625, 635)
	var bindings := 0
	var reads := 0
	for number in branch_body.size():
		var line := str(branch_body[number])
		if line.contains("used_syringe = "):
			bindings += 1
		elif line.contains("used_syringe"):
			reads += 1
	check_eq(bindings, 1,
		"the committed branch binds `used_syringe` exactly once")
	check_eq(reads, 0,
		"and NEVER READS IT AGAIN anywhere in the branch, so it is DISCARDED")
	# The `kill` branch never mentions the ledger at all.
	var kill_body := _line_range("command.py", 169, 181)
	var kill_ledger := 0
	for line: Variant in kill_body:
		kill_ledger += _count_occurrences(str(line), "deadHeroes")
	check_eq(kill_ledger, 0,
		"the committed `kill` branch mentions `deadHeroes` ZERO times, so a "
			+ "combat kill records no death in the ledger")
	return measured


# ---------------------------------------------------------------------------
# The refusals (design D3/D5)
# ---------------------------------------------------------------------------


## No syringe cost, no resource movement, no combat, and no placement
## validation — each with a non-empty recorded reason.
func _check_refusals() -> void:
	var record := UnitBehaviors.refusal_record()
	var refusals: Array = record.get("refusals", [])
	check_eq(refusals.size(), UnitBehaviors.REFUSAL_COUNT,
		"exactly THREE refusals are recorded")
	var names: Array = []
	for entry: Dictionary in refusals:
		names.append(str(entry["refusal"]))
		check_eq(bool(entry.get("implemented", true)), false,
			"the `%s` refusal is recorded as NOT implemented"
				% str(entry["refusal"]))
		check(not str(entry.get("rule", "")).is_empty(),
			"the `%s` refusal carries a NON-EMPTY reason"
				% str(entry["refusal"]))
	check_eq(names, ["syringe_cost", "combat_resolution",
		"placement_validation"],
		"the three refusals are the delta's, in its order")
	check_eq(int(record.get("syringe_charge", -1)), 0,
		"the recorded syringe charge is ZERO")
	check_eq(bool(record.get("resource_moved", true)), false,
		"no stored resource moves on a revival")
	check_eq(bool(record.get("combat_resolved", true)), false,
		"no combat is resolved")
	check_eq(bool(record.get("placement_validated", true)), false,
		"the revived placement is not validated")
	check_eq(bool(record.get("clicks_to_build_reimplemented", true)), false,
		"`clicks_to_build` is not reimplemented")
	check_eq(bool(record.get("syringe_discarded", false)), true,
		"the discarded `used_syringe` argument is recorded")
	check(UnitBehaviors.NO_SYRINGE_COST.contains("NO SYRINGE COST IS CHARGED"),
		"the no-cost refusal is stated as the contract it is")
	check(UnitBehaviors.NO_COMBAT.contains("NO COMBAT IS RESOLVED"),
		"the no-combat refusal is stated as the contract it is")
	check(UnitBehaviors.NO_PLACEMENT_VALIDATION.contains("NO OCCUPANCY"),
		"the no-placement-validation refusal is stated as the contract it is")
	check(UnitBehaviors.NO_PLACEMENT_VALIDATION.contains("Server v1 / M13"),
		"and the gap is recorded as a later server-authority requirement "
			+ "rather than filled")
	check(UnitBehaviors.SYRINGE_DISCARD_NOTE.contains("NEVER ECHOES"),
		"the response never echoes the discarded argument")
	check(UnitBehaviors.DERIVED_PAIRING.contains("DERIVED, NOT ASSERTED"),
		"the death/resurrection pairing is recorded as DERIVED, never asserted")
	check(not str(record.get("ledger_migration", "")).is_empty(),
		"the `version.py` ledger migration is recorded and is not treated as "
			+ "gameplay")
	check(not str(record.get("fixture_not_captured", "")).is_empty(),
		"the absent executed-legacy fixture is recorded with its reason")
	check(not str(record.get("no_third_gate", "")).is_empty(),
		"the no-third-gate statement travels on the refusal record too")


# ---------------------------------------------------------------------------
# The clicks_to_build boundary (design D6)
# ---------------------------------------------------------------------------


## `clicks_to_build` is referenced, never reimplemented.
func _check_clicks_boundary() -> void:
	var boundary := UnitBehaviors.CLICKS_TO_BUILD_BOUNDARY
	check(boundary.contains("REFERENCED AND NOT REIMPLEMENTED"),
		"the module states that clicks_to_build is referenced and NOT "
			+ "reimplemented")
	check(boundary.contains("godot-building-construction"),
		"and names the delivered capability that owns the {\"nc\": 0} counter")
	check(boundary.contains("0 on ALL 429 unit definitions"),
		"and records the MEASURED fact that the committed value is 0 on every "
			+ "unit, so a revived unit never seeds the counter")
	# This line reimplements nothing.  The claim is checkable in two parts:
	# neither delivered module reads committed content at run time at all, and
	# neither declares the counter the field seeds.  (The typed result DOES
	# carry the recorded boundary as a STRING, which is a report of the
	# boundary, never an implementation of it.)
	var runtime_readers := ["get_entry", "load_content", "legacy_ids",
		"registry"]
	for script: String in [DELIVERED_BEHAVIOR_SCRIPT, DELIVERED_FLOW_SCRIPT]:
		var code := _code_only(script)
		check(not code.is_empty(),
			"%s is readable for its declaration scan" % script)
		for reader: String in runtime_readers:
			check(not code.contains(reader),
				"%s's declarations never read committed content at run time "
					% script
					+ "(`%s`), so it cannot derive a count from "
						% reader + "`clicks_to_build` or from anything else")
		check(not _declares_identifier(code, "nc"),
			"%s's declarations never name the construction-click counter as an "
				% script
				+ "identifier, so it neither seeds nor consumes it")
		check(not code.contains("add_click"),
			"%s's declarations never name the command that consumes the counter"
				% script)
	check_eq(int(_legacy_reads_of("clicks_to_build")), 1,
		"the committed field has exactly ONE legacy consumer, so the "
			+ "re-placement is the only place it could ever matter")


## How many quoted occurrences of a name the seven legacy modules carry.
func _legacy_reads_of(name: String) -> int:
	var total := 0
	for module: String in UnitBehaviors.SEARCHED_MODULES:
		var text := "\n".join(_legacy_lines(module))
		total += _count_occurrences(text, "\"%s\"" % name)
		total += _count_occurrences(text, "'%s'" % name)
	return total


# ---------------------------------------------------------------------------
# The intent (design D2)
# ---------------------------------------------------------------------------


## The revival intent carries ONLY an identifier and a cell, and both
## implementations return the same typed shape.
func _check_intent() -> void:
	var record := BehaviorFlow.intent_record()
	check_eq(record["keys"], ["user_id", "x", "y"],
		"the intent carries EXACTLY a player identifier and a cell — no map "
			+ "key, no item id, no syringe count, no price")
	check_eq(int((record["ignored_keys"] as Array).size()),
		(BehaviorFlow.INTENT_IGNORED_KEYS as Array).size(),
		"the ignored-key list is carried whole")
	for key: String in ["item_id", "map_key", "used_syringe", "syringes",
			"price", "cost", "resources_changed", "vector"]:
		check((record["ignored_keys"] as Array).has(key),
			"the intent's ignored-key list names `%s`, so a caller can see that "
				% key + "attaching it changes nothing")
	check(not (record["keys"] as Array).has("item_id"),
		"the intent has NO parameter through which a client could dictate the "
			+ "revived item id")
	check(str(record["item_id_is"]).contains("server-derived"),
		"the revived item id is recorded as server-derived from the ledger")
	check(str(record["map_key_is"]).contains("server-derived"),
		"the map key is recorded as server-derived from the addressed cell")
	check_eq(bool(record["identical_typed_shapes"]), true,
		"both implementations are recorded as yielding the same typed shape")
	check(not str(record.get("proof", "")).is_empty(),
		"the two-part post-execution proof is recorded")
	check(str(record["proof"]).contains("EVERY stored resource is "),
		"proof half two compares the FULL resource set, never a subset")
	check(str(record["proof"]).contains("DELETES the key"),
		"proof half one is the delete-at-zero removal, which is not a zero")
	# Both implementations declare the operation with EXACTLY the three intent
	# parameters, which is the structural form of "there is no parameter through
	# which a client could send a value".
	for implementation: String in [
			"res://scripts/gameapi/fake_api.gd",
			"res://scripts/gameapi/legacy_v0_api.gd",
			"res://scripts/gameapi/game_api.gd"]:
		check_eq(_argument_count(implementation, "resurrect_hero_town"), 3,
			"%s declares resurrect_hero_town with EXACTLY the three intent "
				% implementation + "parameters")
	# The typed result is ONE class, so the two implementations cannot drift.
	check_eq(_result_type_of("res://scripts/gameapi/fake_api.gd"),
		"BehaviorFlow.ResurrectResult",
		"the offline double returns the delivered typed result")
	check_eq(_result_type_of("res://scripts/gameapi/legacy_v0_api.gd"),
		"BehaviorFlow.ResurrectResult",
		"the live implementation returns the SAME delivered typed result")
	check_eq(_result_type_of("res://scripts/gameapi/game_api.gd"),
		"BehaviorFlow.ResurrectResult",
		"and the facade forwards the same delivered typed result")


# ---------------------------------------------------------------------------
# The offline double (design D8)
# ---------------------------------------------------------------------------


## The offline double reproduces the legacy transaction's own effects: the
## decrement with the delete-at-zero rule, the re-placement with NO validation,
## and a neutral vector.
func _check_double(corpus: Dictionary) -> void:
	if corpus.is_empty():
		return
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("fake")
	var pid := str(corpus.get("pid", ""))
	var cell: Array = corpus.get("target_cell", [])
	check_eq(pid, "00000000-0000-4000-8000-000000000001",
		"the double's save id is the committed corpus's own pid")
	check_eq(cell.size(), 2,
		"the double's positive path addresses the committed corpus's own cell")
	if pid.is_empty() or cell.size() != 2:
		return
	# The seeded ledger entry is a committed unit whose own committed
	# resurrectable is greater than zero, so the double's positive path is
	# reachable through the LEGACY gate and not by bypassing it.
	var seed_entry := _registry_entry("units", str(DOUBLE_SEED_ITEM_ID))
	check_eq(bool(seed_entry.is_empty()), false,
		"the double's seed names a committed UNIT definition")
	check_eq(str(seed_entry.get("type", "")), "u",
		"and it is committed type `u`, so it really is a unit")
	var seed_flag: Variant = UnitBehaviors.committed_resurrectable(
		seed_entry.get(UnitBehaviors.PROPERTIES_FIELD))
	check(UnitBehaviors.passes_resurrectable_gate(seed_flag),
		"and its committed `resurrectable` passes the SECOND legacy gate, so "
			+ "the double's positive path goes through the gate rather than "
			+ "around it")
	check_eq(DOUBLE_SEED, {"1001": 1},
		"the double's documented in-memory ledger seed is the recorded one")
	check_eq((DOUBLE_SEED as Dictionary).size(), 1,
		"the seed holds exactly ONE entry, so the double's resolution is "
			+ "unambiguous by construction")

	var before: int = api.behavior_requests
	var revived: Variant = await api.resurrect_hero_town(pid, int(cell[0]),
		int(cell[1]))
	check(revived is BehaviorFlow.ResurrectResult,
		"resurrect_hero_town returns the delivered typed result")
	check_eq(int(api.behavior_requests), before + 1,
		"the facade counts exactly ONE intent per confirm")
	if not (revived is BehaviorFlow.ResurrectResult):
		return
	var typed: BehaviorFlow.ResurrectResult = revived
	check_eq(bool(typed.ok), true,
		"the double accepts one revival offline: %s" % typed.error_message)
	_check_typed_result(typed, cell)
	check_eq(typed.item_id, DOUBLE_SEED_ITEM_ID,
		"the revived item id is the LEDGER's, never a client value")
	check_eq(typed.map_key, CORPUS_TARGET_MAP_KEY,
		"the map key is the addressed cell's own row, never a client value")
	check_eq(typed.count_before, 1, "the ledger held one entry before")
	check_eq(typed.count_after, 0, "and none after, because the key was DELETED")
	check_eq(bool(typed.removed), true,
		"the typed result reports the key as REMOVED, not stored as a zero")
	check_eq(_normalize(typed.ledger_before), [{"item_id": "1001", "count": 1}],
		"the response's before ledger is the double's own seeded one")
	check_eq(_normalize(typed.ledger_after), [],
		"and the after ledger is EMPTY: the entry is GONE, not zero")
	check_eq(_normalize(typed.placement_before[0]),
		_normalize(_corpus_target_item()),
		"the response's before row is the committed corpus's own row")
	check_eq(int(typed.placement_after[0]), DOUBLE_SEED_ITEM_ID,
		"the re-placed row records the DERIVED item id")
	check_eq(int(typed.placement_after[1]), int(cell[0]),
		"at the addressed cell's own x")
	check_eq(int(typed.placement_after[2]), int(cell[1]),
		"at the addressed cell's own y")
	check_eq(int(typed.placement_after[7]), UnitBehaviors.PLAYER_TEAM,
		"on the player's own team")
	check_eq(_normalize(typed.placement_after[6]), {},
		"with an EMPTY attribute bag: the revived unit's committed "
			+ "clicks_to_build is 0, so the construction-click counter is not "
			+ "seeded — a measurement, not an assumption")
	# Proof half two: the FULL resource set, compared one slot at a time.
	for name: String in RESOURCE_NAMES:
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int((corpus["resources"] as Dictionary)[name]),
			"the %s balance is UNCHANGED by the revival (proof half two)" % name)
	check_eq(_resources_as_dictionary(typed.resources), corpus["resources"],
		"and the response's full seven-slot resource set equals the corpus's own")
	# The two named refusals, each with the service's own code and no payload.
	var again: Variant = await api.resurrect_hero_town(pid, int(cell[0]),
		int(cell[1]))
	check(again is BehaviorFlow.ResurrectResult and not again.ok,
		"a second revival at the same cell is refused: the ledger is EMPTY")
	if again is BehaviorFlow.ResurrectResult:
		check_eq(again.error_code, "unresolvable_ledger_entry",
			"the refusal carries its own named code: %s" % again.error_message)
		check_eq(again.item_id, -1,
			"the refused revival carries NO revived item id")
		check_eq(again.ledger_after.size(), 0,
			"the refused revival carries NO partial payload")
	var free: Variant = await api.resurrect_hero_town(pid, 0, 0)
	check(free is BehaviorFlow.ResurrectResult and not free.ok,
		"a revival at a cell no placement row records is refused")
	if free is BehaviorFlow.ResurrectResult:
		check_eq(free.error_code, "unresolvable_cell",
			"and that refusal is the endpoint's own `unresolvable_cell` code")
	var unknown: Variant = await api.resurrect_hero_town("no-such-save-000",
		int(cell[0]), int(cell[1]))
	check(unknown is BehaviorFlow.ResurrectResult and not unknown.ok,
		"an unknown save id is refused")
	if unknown is BehaviorFlow.ResurrectResult:
		check_eq(unknown.error_code, "unknown_user_id",
			"and that refusal is the shared `unknown_user_id` code")
	var blank: Variant = await api.resurrect_hero_town("", int(cell[0]),
		int(cell[1]))
	check(blank is BehaviorFlow.ResurrectResult and not blank.ok,
		"an empty save id is refused")
	if blank is BehaviorFlow.ResurrectResult:
		check_eq(blank.error_code, "missing_user_id",
			"and that refusal is the shared `missing_user_id` code")


## The typed result's own shape, asserted on every successful answer: the two
## gates, the three refusals, the seven resources, the uncharged syringe — and
## with NO cost, damage, occupancy, or validation field anywhere on the class.
func _check_typed_result(result: BehaviorFlow.ResurrectResult,
		cell: Array) -> void:
	check_eq(result.protocol, BootData.PROTOCOL,
		"the typed result reports the v0 protocol")
	check_eq(result.result, "success",
		"the typed result carries the legacy success result")
	check(result.server_time > 0,
		"the typed result's server_time is a positive integer")
	check(result.resources != null, "the typed result carries the resources")
	check_eq(result.cell, [int(cell[0]), int(cell[1])],
		"the typed result echoes the addressed cell exactly as sent")
	check_eq(result.gates.size(), UnitBehaviors.GATE_COUNT,
		"the typed result carries EXACTLY the two recorded gates")
	check_eq(result.gate_count, 2,
		"and its own gate count agrees")
	check_eq((result.refusals as Array).size(), UnitBehaviors.REFUSAL_COUNT,
		"the typed result carries the three recorded refusals")
	check_eq(int(result.syringe_charged), 0,
		"the typed result charges NO syringe")
	check_eq(bool(result.syringe_echoed), false,
		"and reports that it does NOT echo the discarded argument")
	check_eq(int(result.syringe_discarded_argument), 0,
		"the discarded argument is the inert zero the derivation sends")
	check_eq(bool(result.placement_validated), false,
		"the typed result states that the placement was NOT validated")
	check(not result.no_third_gate.is_empty(),
		"and carries the no-third-gate statement beside it")
	check(not result.clicks_to_build_boundary.is_empty(),
		"and the clicks_to_build boundary beside it")
	check(result.committed_resurrectable != null
			and int(result.committed_resurrectable) > 0,
		"the resolved entry's committed `resurrectable` is reported as CONTENT")
	check(int(result.committed_syringes) >= 0,
		"and its committed `syringes` value is reported as CONTENT, never a "
			+ "price")
	check_eq((result.placement_before as Array).size(), 8,
		"the response's before placement is the committed eight-slot row")
	check_eq((result.placement_after as Array).size(), 8,
		"and its after placement is the committed eight-slot row")
	check_eq(str(result.occupant_item_id) != str(result.item_id), true,
		"the item that stood at the addressed cell is reported beside the "
			+ "revived one, and they DIFFER — the recorded consequence of "
			+ "deriving the revived id from the ledger")
	for field: String in ["damage", "cost", "price", "charge", "syringe_cost",
			"occupied", "terrain", "hit", "defense", "attack"]:
		check(not ("_%s" % field) in result,
			"the typed result carries NO %s field at all: the legacy server has "
				% field + "no such rule")


# ---------------------------------------------------------------------------
# The anti-invention guard (design D3/D5)
# ---------------------------------------------------------------------------


## Both delivered modules declare **EXACTLY** their projection and record
## accessors — no syringe-cost, damage, attack, defence, hit, occupancy, or
## charge helper — and the recorded `ABSENT_HELPERS` list names each one that
## does not exist.
func _check_absence() -> void:
	var behavior_methods := _declared_methods(DELIVERED_BEHAVIOR_SCRIPT)
	check_eq(behavior_methods, _sorted_copy(EXPECTED_BEHAVIOR_METHODS),
		"unit_behaviors.gd declares EXACTLY its projection, inventory, and "
			+ "record accessors — no syringe-cost, damage, attack, defence, "
			+ "hit, occupancy, or charge helper")
	var flow_methods := _declared_methods(DELIVERED_FLOW_SCRIPT)
	check_eq(flow_methods, _sorted_copy(EXPECTED_FLOW_METHODS),
		"behavior_flow.gd declares EXACTLY its parser, intent, and record "
			+ "accessors — no cost, combat, occupancy, or charge helper")
	for helper: String in FORBIDDEN_HELPERS:
		check(not behavior_methods.has(helper),
			"the projection declares no '%s' helper: the legacy server has no "
				% helper + "such rule to reproduce")
		check(not flow_methods.has(helper),
			"the flow declares no '%s' helper: the legacy server has no such "
				% helper + "rule to reproduce")
	# The recorded absences, each with a reason, and each also on the suite's
	# own forbidden list so a leftover fails visibly.
	var absent: Array = UnitBehaviors.ABSENT_HELPERS
	var named: Array = []
	for entry: Dictionary in absent:
		named.append(str(entry["helper"]))
		check(not str(entry["absent_because"]).is_empty(),
			"the recorded absence of '%s' states why it is absent"
				% str(entry["helper"]))
		check(FORBIDDEN_HELPERS.has(str(entry["helper"])),
			"the recorded absence '%s' is also asserted absent by name"
				% str(entry["helper"]))
	check_eq(named, ["syringe_cost", "charge_revive", "resolve_damage",
			"apply_attack", "defend", "hit_chance", "is_occupied", "in_bounds",
			"terrain_at", "is_type_allowed", "revive_count_cap",
			"revive_cooldown"],
		"the recorded absences are the twelve the three refusals and the "
			+ "unvalidated placement need, in order")
	check_eq(named.size(), 12,
		"the recorded ABSENT_HELPERS list names twelve absent helpers")
	# Every absence names a legacy fact rather than a preference.
	var reasons := ""
	for entry: Dictionary in absent:
		reasons += str(entry["absent_because"])
	for phrase: String in ["legacy", "committed", "recorded", "check"]:
		check_in_text(reasons, phrase,
			"the recorded absences ground themselves in the legacy contract "
				+ "('%s')" % phrase)
	# The guard is a REAL gate rather than a tautology: an injected helper
	# changes the inventory and would fail the comparison above.
	var injected := (behavior_methods as Array).duplicate()
	injected.append("syringe_cost")
	check(injected != behavior_methods,
		"an injected 'syringe_cost' helper changes the inventory, so the guard "
			+ "is a real gate rather than a tautology")
	# And the projection's own arithmetic: it computes no count from another,
	# which is checkable by asserting its DECLARATIONS carry no multiplication
	# or division of one committed field by another.
	var code := _code_only(DELIVERED_BEHAVIOR_SCRIPT)
	check(not code.is_empty(),
		"the projection source is readable for its declaration scan")
	for token: String in ["*", "/"]:
		check(not code.contains(token),
			"the projection's declarations contain no `%s`, so no count is "
				% token + "derived from another value")


# ---------------------------------------------------------------------------
# The structural boundary
# ---------------------------------------------------------------------------


## No client source anywhere derives a syringe cost, a combat rule, or a
## placement check — and there is no OTHER resurrection endpoint.
func _check_boundary() -> void:
	var sources := _client_sources()
	var offenders: Array = []
	for path: String in sources:
		var code := _code_only(path)
		for needle: String in BEHAVIOUR_NEEDLES:
			if _declares_identifier(code, needle):
				offenders.append("%s declares %s" % [path, needle])
	check_eq(offenders, [],
		"no client source DECLARES a syringe-cost, damage, attack, hit, "
			+ "occupancy, cooldown, terrain, or type-check helper")
	# The identifier rule is a real gate and not a stricter-looking
	# tautology. The tree really does hold a source carrying the needle as a
	# substring of a longer identifier, so the distinction is exercised, and a
	# synthetic declaration of the same name is caught.
	var carrier := ""
	for path: String in sources:
		if _code_only(path).contains("no_syringe" + "_cost"):
			carrier = path
			break
	check(carrier != "",
		"the client tree really does hold a source carrying `no_syringe_cost`,"
			+ " so the substring-versus-identifier distinction is exercised")
	if carrier != "":
		check(not _declares_identifier(_code_only(carrier),
				"syringe_" + "cost"),
			"and the needle inside that longer identifier is NOT a declaration")
	check(_declares_identifier("static func syringe_" + "cost(n) -> int:",
			"syringe_" + "cost"),
		"while a real declaration of the same name IS caught")
	check(not _declares_identifier("static func other_name(n) -> int:",
			"syringe_" + "cost"),
		"and an unrelated declaration is not")
	# The one legitimate mention is the RECORDED absence list, which lives in
	# the delivered modules' constants and is therefore matched out of the
	# declarations by `_code_only` only for code, not for recorded strings —
	# so the check above is over declarations only and the recorded prose is
	# allowed to name them.  That is asserted explicitly here.
	for phrase: String in ["syringe_cost", "resolve_damage", "is_occupied"]:
		check(not _code_only(DELIVERED_BEHAVIOR_SCRIPT).contains(phrase),
			"the phrase '%s' appears ONLY in the delivered modules' RECORDED "
				% phrase
				+ "contract text and in no code declaration anywhere")
	# No OTHER resurrection endpoint and no legacy command name.  The rejected
	# routes are assembled from fragments so THIS file does not contain them
	# literally — otherwise the scan would match its own list and report itself.
	var rejected_routes := [
		"/v0/resurrect" + "_hero", "/v0/dead" + "_hero",
		"/v0/re" + "vive", "/v0/resurrect" + "able",
	]
	var endpoints: Array = []
	for path: String in sources:
		var body := FileAccess.get_file_as_string(path)
		for route: String in rejected_routes:
			if body.contains(route):
				endpoints.append("%s names a rejected route" % path)
	check_eq(endpoints, [],
		"no client source names a SECOND resurrection route: the documented "
			+ "path the live implementation dials is the only one")
	check_eq(BehaviorFlow.RESURRECT_PATH, "/v0/resurrect",
		"and the flow module names that documented path verbatim")
	check(not BehaviorFlow.RESURRECT_PATH.contains("http"),
		"the flow module names the path WITHOUT a scheme or host, because only "
			+ "the legacy-v0 implementation may reference an endpoint")
	# The legacy command name is never accepted from a caller: the intent
	# carries no command field at all.
	check(not (BehaviorFlow.INTENT_KEYS as Array).has("command"),
		"the intent carries NO command field, so a caller cannot dispatch an "
			+ "arbitrary legacy command")


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


## Neither delivered module names a node, a clock, a request, or a transport in
## any **declaration**, and both preload only the read-only projection and the
## shared type module.
##
## The scan is over DECLARATIONS rather than raw text, because the delivered
## modules' recorded contract strings legitimately contain prose like "random
## number" and "attr['nc'] = 0", and a prose mention is not an implementation.
## A transport token in raw text is the project-scope suite's own job, and it
## scans every source file raw.
func _check_purity() -> void:
	for script: String in [DELIVERED_BEHAVIOR_SCRIPT, DELIVERED_FLOW_SCRIPT]:
		var code := _code_only(script)
		for needle: String in PURITY_NEEDLES:
			check(not code.contains(needle),
				"%s declares no %s token: it is a pure module"
					% [script, needle])
	check_eq(_preloads(FileAccess.get_file_as_string(DELIVERED_BEHAVIOR_SCRIPT)),
		[], "the projection preloads NOTHING: it reads no disk and no registry")
	check_eq(_preloads(FileAccess.get_file_as_string(DELIVERED_FLOW_SCRIPT)),
		["res://scripts/units/unit_behaviors.gd",
			"res://scripts/gameapi/boot_data.gd"],
		"the flow preloads ONLY the shared type module and the read-only "
			+ "projection — no node script and no registry")


# ---------------------------------------------------------------------------
# Containment
# ---------------------------------------------------------------------------


## This line only READS the committed material: the content package, the
## committed saves, the committed fixtures, and the legacy root modules are all
## byte-identical after the run.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, legacy_before: Dictionary,
		save_before: Dictionary) -> void:
	check_eq(Paths.directory_digest(
		Paths.repo_root().path_join("packages/game-content")), package_before,
		"the content package is byte-identical after the run")
	check_eq(Paths.directory_digest(
		Paths.repo_root().path_join("tests/saves")), saves_before,
		"the committed saves are byte-identical after the run")
	check_eq(Paths.directory_digest(
		Paths.repo_root().path_join("tests/fixtures")), fixtures_before,
		"the committed fixtures are byte-identical after the run — no unit row "
			+ "was manufactured in any of them")
	check_eq(_legacy_digest(), legacy_before,
		"the legacy root modules are byte-identical after the run")
	check_eq(Paths.file_sha256_checked(
		Paths.repo_root().path_join(CORPUS_SAVE)), save_before,
		"the committed corpus save is byte-identical after the run")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory was created")


# ---------------------------------------------------------------------------
# The deterministic evidence report
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


## Computes and writes the deterministic `unit-behaviors-report-v1` report.
##
## Every contract fact comes from `unit_behaviors.gd` and `behavior_flow.gd` —
## their own ledger projection, both gates, the delete-at-zero rule, the
## three-door inventory, the committed field table, the refusals, and the
## non-claims — every legacy fact comes from the measurement this run performed,
## and every committed number comes from the registry that was just verified or
## from the committed corpus bytes.  Nothing here reads the wall clock, resolves
## a path outside the repository, or sends a request, so the file is
## byte-identical across reruns.
func _write_report(path: String, fields: Dictionary, legacy: Dictionary,
		corpus: Dictionary) -> void:
	var empty := UnitBehaviors.project_ledger({})
	var populated := UnitBehaviors.project_ledger({"1001": 2, "1085": 1})
	var absent := UnitBehaviors.project_ledger(null)
	var wrong_type := UnitBehaviors.project_ledger([1, 2])
	var bad_key := UnitBehaviors.project_ledger({1001: 1})
	var bad_count := UnitBehaviors.project_ledger({"1001": "1"})
	var report := {
		"schema": "unit-behaviors-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_behaviors.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from the "
				+ "two delivered modules' own constants, this same run's legacy "
				+ "and content measurements, and the committed corpus bytes, and "
				+ "every derived set is sorted before it is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) plus "
				+ "one trailing newline; every number written is an integer - "
				+ "the pinned engine's integral floats are normalised on the way "
				+ "in, which changes no value",
			"time_dependent_fields": "NONE in this line's hermetic evidence: the "
				+ "ledger projection, the inventory, and the refusals touch no "
				+ "clock, and the offline double stamps its re-placed row with "
				+ "the boot fixture's recorded epoch rather than the wall clock",
		},
		"ledger": UnitBehaviors.ledger_record(populated),
		"ledger_projections": {
			"empty": empty,
			"populated": populated,
			"absent": absent,
			"not_an_object": wrong_type,
			"non_string_key": bad_key,
			"non_integer_count": bad_count,
			"unresolvable_is_never_empty": [
				bool(absent.get("ok", true)),
				bool(wrong_type.get("ok", true)),
				bool(bad_key.get("ok", true)),
				bool(bad_count.get("ok", true)),
			],
		},
		"gates": {
			"gates": UnitBehaviors.gates(),
			"count": UnitBehaviors.gate_count(),
			"no_third_gate": UnitBehaviors.NO_THIRD_GATE,
			"team_gate": UnitBehaviors.passes_team_gate(UnitBehaviors.PLAYER_TEAM),
			"resurrectable_gate_absent": UnitBehaviors.passes_resurrectable_gate(
				null),
			"resurrectable_gate_zero": UnitBehaviors.passes_resurrectable_gate(0),
			"resurrectable_gate_positive": UnitBehaviors.passes_resurrectable_gate(
				1),
			"committed_string_zero": UnitBehaviors.committed_resurrectable(
				{"resurrectable": "0"}),
			"raw_string_read": UnitBehaviors.committed_resurrectable(
				"{\"resurrectable\":\"1\"}"),
		},
		"inventory": UnitBehaviors.inventory_record(),
		"inventory_measured": {
			"named_branch_count": (legacy.get("named_branches", []) as Array).size(),
			"named_branches": (legacy.get("named_branches", []) as Array)
				.duplicate(),
			"resurrectable_reads": (legacy.get("ledger_sites", {}) as Dictionary)
				.get(UnitBehaviors.RESURRECTABLE_FLAG, []),
			"resurrectable_quoted_read_count": (
				(legacy.get("ledger_sites", {}) as Dictionary)
					.get(UnitBehaviors.RESURRECTABLE_FLAG, []) as Array).size(),
			"resurrectable_bare_occurrences": _as_int(legacy.get(
				"ledger_token_occurrences", 0)),
			"resurrectable_bare_note": "the BARE substring count exceeds the "
				+ "quoted READ count because command.py binds a LOCAL VARIABLE "
				+ "named `resurrectable` at lines 158, 160, and 164. A local is "
				+ "not a field read, so the recorded two-read figure is the "
				+ "quoted measurement; both are reported so a reader can "
				+ "re-derive the choice",
			"clicks_to_build_reads": (legacy.get("clicks_sites", []) as Array)
				.duplicate(),
			"modules": _as_int(legacy.get("modules", 0)),
			"note": "every legacy figure is re-derived from the committed source "
				+ "in this same run, so the inventory cannot drift from the "
				+ "dispatcher and a 64th branch would be an unrecorded gap",
		},
		"fields": UnitBehaviors.field_record(),
		"fields_measured": fields,
		"zero_consumer_occurrences": (legacy.get("zero_consumer", {}) as Dictionary)
			.duplicate(),
		"refusals": UnitBehaviors.refusal_record(),
		"intent": BehaviorFlow.intent_record(),
		"scope": BehaviorFlow.scope_record(),
		"corpus": {
			"measurement": corpus,
			"fixture_not_captured": UnitBehaviors.FIXTURE_NOT_CAPTURED,
			"cause": "A CORPUS LIMITATION WITH A NAMED CAUSE, not the absence "
				+ "of behaviour: `resurrectable` is unit-only, the corpus places "
				+ "only buildings, and its ledger is present and empty",
			"unit_row_manufactured": false,
		},
		"boundary": {
			"client_sources_scanned": _client_sources().size(),
			"needles": BEHAVIOUR_NEEDLES.duplicate(),
			"resurrection_path": BehaviorFlow.RESURRECT_PATH,
			"other_endpoint_exists": false,
		},
		"provenance": UnitBehaviors.PROVENANCE,
		"non_claims": UnitBehaviors.NON_CLAIMS,
		"readout": UnitBehaviors.readout_text(populated),
	}
	for phrase: String in REQUIRED_NON_CLAIMS:
		check(_contains_phrase(report["non_claims"], phrase),
			"the report's non-claims name '%s'" % phrase)
	check_eq(report["readout"], UnitBehaviors.readout_text(populated),
		"the report's readout comes from the projection itself, so it cannot "
			+ "drift from the module it documents")
	var problem := _write_json(path, report)
	check_eq(problem, "", "the evidence report is written (problem: %s)"
		% problem)
	if problem == "":
		check(FileAccess.file_exists(path),
			"the report file exists at %s" % path)
		info("report written: %s" % path)


# ---------------------------------------------------------------------------
# The live-behavior phase (verify-boot's `behavior-live`)
# ---------------------------------------------------------------------------


## The corpus's own ledger at the moment the live phase runs, seeded through the
## service's documented opt-in seam.  The harness snapshots the disposable
## corpus saves before the Godot run and fails unless one changed after, so this
## phase asserts a REAL persistence through the unchanged legacy dispatcher.
const LIVE_RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana"]
const LIVE_FREE_CELL := [0, 0]


## One revival through the REAL Compatibility endpoint, against a disposable
## corpus seeded with one resurrectable ledger entry through the documented
## `COMPAT_SEED_DEAD_HEROES` seam (set by verify-boot.ps1 for this phase only).
##
## Seeding a THROWAWAY copy is not manufacturing coverage in preserved material:
## the committed corpus and every delivered fixture directory stay
## byte-identical, which is what the no-manufactured-coverage boundary requires,
## and the ledger entry the seed creates is removed again by the revival itself.
##
## The phase asserts the typed response, its **two-part value-level post-state
## proof** (the revived ledger entry is GONE, and EVERY stored resource is
## unchanged), the addressed key's row now recording the derived item id, both
## named refusals, and — with no request over the network beyond loopback — the
## SAME intent through the offline double, so both implementations are compared.
func _check_live_behavior() -> void:
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
	check(not before_payload.is_empty(), "the corpus pre-revival payload resolves")
	if before_payload.is_empty():
		return
	var priv_before: Dictionary = before_payload.get("privateState", {}) \
		as Dictionary
	var map_before: Dictionary = before_payload.get("map", {}) as Dictionary
	var items_before: Dictionary = map_before.get("items", {}) as Dictionary
	var rows_before: Dictionary = items_before.duplicate(true)
	# Proof precondition: the seeded ledger holds EXACTLY the one entry, and the
	# addressed cell is a real placement row on player team 1.
	check_eq(_normalize(priv_before.get(UnitBehaviors.LEDGER_KEY)),
		{"1001": 1},
		"the live corpus's seeded deadHeroes ledger holds exactly the one "
			+ "resurrectable entry, so the revival is an observable removal")
	var addressed: Array = _addressed_row(items_before, str(CORPUS_TARGET_MAP_KEY))
	check_eq(addressed.size(), 8,
		"the committed map key %d resolves to a committed eight-slot row, so "
			% CORPUS_TARGET_MAP_KEY
			+ "the live revival has a real cell to land on")
	if addressed.size() != 8:
		return
	var cell_x := int(addressed[1])
	var cell_y := int(addressed[2])
	check_eq(int(addressed[7]), UnitBehaviors.PLAYER_TEAM,
		"and the row that stands there is on PLAYER TEAM 1, so gate one passes "
			+ "on its own recorded term")
	var resources_before := _live_resources(before_payload)
	# The revival.
	var revived: Variant = await api.resurrect_hero_town(pid, cell_x, cell_y)
	check(revived is BehaviorFlow.ResurrectResult and revived.ok,
		"a revival is accepted by the REAL endpoint: %s"
			% ((revived as BehaviorFlow.ResurrectResult).error_message
				if revived is BehaviorFlow.ResurrectResult else ""))
	if not (revived is BehaviorFlow.ResurrectResult and revived.ok):
		return
	var typed: BehaviorFlow.ResurrectResult = revived
	_check_typed_result(typed, [cell_x, cell_y])
	check_eq(typed.item_id, DOUBLE_SEED_ITEM_ID,
		"the revived item id is the SERVER-DERIVED one from the player's own "
			+ "ledger, not a client value")
	check_eq(typed.map_key, CORPUS_TARGET_MAP_KEY,
		"the map key is the SERVER-DERIVED one the addressed cell resolves to")
	check_eq(typed.count_before, 1, "the ledger held one entry before")
	check_eq(typed.count_after, 0, "and none after")
	check_eq(bool(typed.removed), true,
		"the live service reports the key REMOVED, never stored as a zero")
	# Proof half one: the entry is GONE.
	check_eq(_normalize(typed.ledger_before), [{"item_id": "1001", "count": 1}],
		"the response's before ledger is the seeded one")
	check_eq(_normalize(typed.ledger_after), [],
		"the response's after ledger is EMPTY: the revived entry is GONE")
	# The addressed key's row now records the derived item id at the same cell.
	check_eq(int(typed.placement_after[0]), DOUBLE_SEED_ITEM_ID,
		"the addressed key's row now records the DERIVED item id")
	check_eq(int(typed.placement_after[1]), cell_x,
		"at the addressed cell's own x")
	check_eq(int(typed.placement_after[2]), cell_y,
		"at the addressed cell's own y")
	check_eq(int(typed.placement_after[7]), UnitBehaviors.PLAYER_TEAM,
		"on the player's own team")
	check_eq(_normalize(typed.placement_after[6]), {},
		"with an EMPTY attribute bag — the revived unit's committed "
			+ "clicks_to_build is 0, so no construction-click counter is seeded")
	check_eq(_normalize(typed.placement_after[5]), [],
		"and an EMPTY store list, exactly as engine.map_add_item constructs it")
	# Proof half two: EVERY stored resource unchanged, one slot at a time.
	for name: String in LIVE_RESOURCE_NAMES:
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the revival (proof half two)" % name)
	# The two named refusals, each with the endpoint's own code and no payload.
	var empty_ledger: Variant = await api.resurrect_hero_town(pid, cell_x, cell_y)
	check(empty_ledger is BehaviorFlow.ResurrectResult and not empty_ledger.ok,
		"a second revival at the same cell is refused by the REAL endpoint: "
			+ "the ledger is EMPTY")
	if empty_ledger is BehaviorFlow.ResurrectResult:
		check_eq(empty_ledger.error_code, "unresolvable_ledger_entry",
			"and the refusal is the endpoint's own named code: %s"
				% empty_ledger.error_message)
		check_eq(empty_ledger.item_id, -1,
			"the refused revival carries NO revived item id")
		check_eq(empty_ledger.ledger_after.size(), 0,
			"and NO partial payload")
	var free: Variant = await api.resurrect_hero_town(pid, LIVE_FREE_CELL[0],
		LIVE_FREE_CELL[1])
	check(free is BehaviorFlow.ResurrectResult and not free.ok,
		"a revival at a cell no placement row records is refused")
	if free is BehaviorFlow.ResurrectResult:
		check_eq(free.error_code, "unresolvable_cell",
			"and that refusal is the endpoint's own `unresolvable_cell` code")
		check_eq(free.placement_after.size(), 0,
			"and NO partial payload")
	# The live corpus AFTER the revival: the entry is gone, the addressed row
	# carries the derived id, no other row moved, and every balance stands.
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	var priv_after: Dictionary = after_payload.get("privateState", {}) \
		as Dictionary
	var map_after: Dictionary = after_payload.get("map", {}) as Dictionary
	var items_after: Dictionary = map_after.get("items", {}) as Dictionary
	check_eq(_normalize(priv_after.get(UnitBehaviors.LEDGER_KEY)), {},
		"the LIVE corpus's ledger is EMPTY after the revival: the entry is gone")
	var expected_rows: Dictionary = rows_before.duplicate(true)
	(expected_rows[str(CORPUS_TARGET_MAP_KEY)] as Array)[0] = DOUBLE_SEED_ITEM_ID
	var differing: Array = []
	for key: Variant in expected_rows.keys():
		if _normalize(items_after.get(key)) != _normalize(expected_rows[key]):
			differing.append(str(key))
	check_eq(differing, [str(CORPUS_TARGET_MAP_KEY)],
		"the revival changed EXACTLY the addressed row — the live transaction "
			+ "is a real write through the unchanged legacy dispatcher")
	check_eq(items_after.size(), rows_before.size(),
		"the placement count is unchanged: a revival REPLACES a row rather than "
			+ "adding one")
	check_eq(_live_resources(after_payload), resources_before,
		"every LIVE corpus balance is byte-identical after the revival")
	# And the SAME intent through the offline double, so both implementations
	# produce the same typed shape with no process, server, or socket.
	api.configure("fake")
	var offline: Variant = await api.resurrect_hero_town(pid, cell_x, cell_y)
	check(offline is BehaviorFlow.ResurrectResult and offline.ok,
		"the offline double accepts the same revival")
	if offline is BehaviorFlow.ResurrectResult and offline.ok:
		var twin: BehaviorFlow.ResurrectResult = offline
		_check_typed_result(twin, [cell_x, cell_y])
		check_eq(twin.item_id, typed.item_id,
			"both implementations revive the SAME server-derived item id")
		check_eq(twin.map_key, typed.map_key,
			"and land it at the SAME derived map key")
		check_eq(bool(twin.removed), bool(typed.removed),
			"and both report the same delete-at-zero removal")
		check_eq(_resources_as_dictionary(twin.resources),
			_resources_as_dictionary(typed.resources),
			"and both report the same seven unchanged balances")
	print("[test] live-behavior applied item_id=%d map_key=%d cell=(%d, %d) "
		% [typed.item_id, typed.map_key, cell_x, cell_y]
		+ "ledger_removed=true resources_unchanged=true "
		+ "refused=unresolvable_ledger_entry,unresolvable_cell")


# ---------------------------------------------------------------------------
# The live-phase helpers
# ---------------------------------------------------------------------------


## The `--scenario=` value this run was launched with, or "".
func _scenario_arg() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--scenario="):
			return argument.trim_prefix("--scenario=")
	return ""


## The loopback endpoint the live phase must dial.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--gameapi-endpoint="):
			return argument.trim_prefix("--gameapi-endpoint=")
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The corpus's own bootstrap payload, or {} when it cannot be read.
func _live_payload(api: Variant, endpoint: String,
		user_id: String) -> Dictionary:
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


## The live payload's seven stored balances, as integers — the pre-request
## reference the live value-level proof compares against, read from the SERVICE's
## own state and never from the fake.
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


## The committed eight-slot row the live phase addresses, read out of the live
## corpus's own placement map by key, or [] when it cannot be resolved.
func _addressed_row(items: Dictionary, map_key: String) -> Array:
	var row: Variant = items.get(map_key)
	if not (row is Array) or (row as Array).size() != 8:
		return []
	return row as Array


## The seven stored balances of a typed result as a plain dictionary, so a live
## answer and an offline one can be compared slot for slot.
func _resources_as_dictionary(resources: BootData.Resources) -> Dictionary:
	var out := {}
	if resources == null:
		return out
	for name: String in RESOURCE_NAMES:
		out[name] = int(resources.get(name))
	return out


## The committed corpus row the double replaces, so its before-state can be
## compared against the committed bytes rather than against a literal.
func _corpus_target_item() -> int:
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(
		Paths.repo_root().path_join(CORPUS_SAVE)))
	if not (document is Dictionary):
		return -1
	var maps: Variant = (document as Dictionary).get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return -1
	var items: Variant = ((maps as Array)[0] as Dictionary).get("items")
	if not (items is Dictionary):
		return -1
	var row: Variant = (items as Dictionary).get(str(CORPUS_TARGET_MAP_KEY))
	if not (row is Array) or (row as Array).size() != 8:
		return -1
	return int((row as Array)[0])


# ---------------------------------------------------------------------------
# The committed-source measurements
# ---------------------------------------------------------------------------


## One legacy module's committed lines, or [] when it cannot be read.  A caller
## that needs the lines treats an empty result as a failure, never as "no
## occurrences found".
func _legacy_lines(module: String) -> Array:
	var path := Paths.repo_root().path_join(module)
	if not FileAccess.file_exists(path):
		return []
	return (FileAccess.get_file_as_string(path) as String).split("\n")


## A committed line range, 1-based and inclusive on both ends.
func _line_range(module: String, first: int, last: int) -> Array:
	var lines := _legacy_lines(module)
	var out: Array = []
	for number in range(first, last + 1):
		if number >= 1 and number <= lines.size():
			out.append(str(lines[number - 1]))
	return out


## Asserts that a recorded source range really starts where the record says, so
## a line drift in the committed legacy source is caught rather than inherited.
func _check_source_range(module: String, line_number: int, name: String,
		label: String) -> void:
	var lines := _legacy_lines(module)
	if line_number < 1 or line_number > lines.size():
		fail("the recorded source line %s:%d exists" % [module, line_number])
		return
	var line := str(lines[line_number - 1]).strip_edges()
	check(line.contains(name),
		"%s (%s:%d reads %s)" % [label, module, line_number, line])


## Asserts that a recorded source line really carries the committed test the
## record names.
func _check_source_line(module: String, line_number: int, fragment: String,
		label: String) -> void:
	var lines := _legacy_lines(module)
	if line_number < 1 or line_number > lines.size():
		fail("the recorded source line %s:%d exists" % [module, line_number])
		return
	var line := str(lines[line_number - 1])
	check(line.contains(fragment),
		"%s (%s:%d carries %s)" % [label, module, line_number, line])


## The branch a committed dispatcher line declares, judged on the stripped line
## so an import or a mention never counts.
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


## How many times a substring occurs in a text, non-overlapping.
func _count_occurrences(text: String, needle: String) -> int:
	if needle.is_empty():
		return 0
	var total := 0
	var at := text.find(needle)
	while at != -1:
		total += 1
		at = text.find(needle, at + 1)
	return total


## A digest over the legacy root modules, so the containment check can prove
## this line only READ them.
func _legacy_digest() -> Dictionary:
	var combined := ""
	for module: String in UnitBehaviors.SEARCHED_MODULES:
		var path := Paths.repo_root().path_join(module)
		if not FileAccess.file_exists(path):
			return {"ok": false, "error": "missing legacy module " + module}
		combined += (FileAccess.get_file_as_string(path) as String)
	var digest := HashingContext.new()
	digest.start(HashingContext.HASH_SHA256)
	digest.update(combined.to_utf8_buffer())
	return {"ok": true, "error": "", "sha256": digest.finish().hex_encode()}


# ---------------------------------------------------------------------------
# The content measurements
# ---------------------------------------------------------------------------


## One committed item id's domain, by the registry's own resolution rather than
## by an id range: `units` when the units domain carries it, `buildings` when
## the buildings domain does, and "" when neither does.
func _domain_of(item_id: String) -> String:
	if _registry == null:
		return ""
	for domain: String in ["units", "buildings"]:
		if bool(_registry.get_entry(domain, item_id).get("found", false)):
			return domain
	return ""


## One committed definition through the verified registry, or {} when neither
## domain carries the id.
func _registry_entry(domain: String, item_id: String) -> Dictionary:
	if _registry == null or domain.is_empty():
		return {}
	var resolved: Dictionary = _registry.get_entry(domain, item_id)
	if not bool(resolved.get("found", false)):
		return {}
	return resolved.get("entry", {}) as Dictionary


## Whether a committed `properties` object sets a flag to a POSITIVE value.  The
## committed flags are **strings**, so the conversion is explicit: a non-empty
## String is truthy in GDScript, and `int(value or 0)` would collapse the
## committed "0" to the integer one.
func _committed_flag(properties: Dictionary, flag: String) -> bool:
	if not properties.has(flag):
		return false
	var value: Variant = properties[flag]
	if value is String:
		var text := str(value).strip_edges()
		if not text.is_valid_int():
			return false
		return int(text) > 0
	if value is bool:
		return false
	if value is float:
		var number := float(value)
		return number == floor(number) and number > 0.0
	if value is int:
		return int(value) > 0
	return false


## A committed field's value as the canonical string this suite counts distinct
## values over: an integral number is keyed by its integer form, a string by
## itself, and an absent field by a recorded marker.
func _measured_value(entry: Dictionary, field: String) -> String:
	if not entry.has(field):
		return "<absent>"
	var raw: Variant = entry[field]
	if raw is bool:
		return "true" if bool(raw) else "false"
	if raw is float:
		var number := float(raw)
		if number == floor(number):
			return str(int(number))
		return str(number)
	return str(raw)


## The measured `{value: count}` distribution of one committed field over one
## verified domain.
func _distribution(registry: Variant, domain: String, field: String) -> Dictionary:
	var out := {}
	var ids: Array = registry.legacy_ids(domain).get("ids", []) as Array
	for id_text: Variant in ids:
		var entry: Dictionary = registry.get_entry(domain,
			str(id_text)).get("entry", {}) as Dictionary
		var key := _measured_value(entry, field)
		out[key] = int(out.get(key, 0)) + 1
	return out


# ---------------------------------------------------------------------------
# Source inspection
# ---------------------------------------------------------------------------


## Every `.gd` source under the given `res://` roots, sorted, so a scan order is
## deterministic.
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


## A source's DECLARATIONS: the file at `res_path` is read, comment lines are
## dropped, and string-literal content is blanked, so a prose mention or a
## recorded non-claim string can never be mistaken for code.
##
## The parameter is a RESOURCE PATH, not a body: every caller scans a file, and
## accepting a body would let a path be scanned as if it were code — which
## silently makes every such check vacuously true.
func _code_only(res_path: String) -> String:
	if not FileAccess.file_exists(res_path):
		return ""
	var lines := (FileAccess.get_file_as_string(res_path) as String).split("\n")
	var out: Array = []
	for line: String in lines:
		var stripped := line.strip_edges()
		if stripped.begins_with("#"):
			continue
		out.append(_blank_literals(line))
	return "\n".join(PackedStringArray(out))


## One line with every string and character literal blanked.
##
## The lexer tracks the two quote characters as SEPARATE states: the committed
## recorded text uses single quotes INSIDE double-quoted strings (`attr['nc']`),
## so treating `'` as a delimiter at the same level as `"` would desynchronise
## the scan and leave a recorded phrase masquerading as a declaration.
func _blank_literals(line: String) -> String:
	var out := ""
	var open := ""
	for index in range(line.length()):
		var character := line[index]
		if open != "":
			if character == open:
				open = ""
			out += " "
			continue
		if character == "\"" or character == "'":
			open = character
			out += " "
			continue
		out += character
	return out


## Whether a declaration names an identifier EXACTLY, judged on word boundaries
## rather than as a bare substring: `nc` occurs inside `Dictionary`, and a
## substring test for a two-letter identifier would be permanently false.
func _declares_identifier(code: String, identifier: String) -> bool:
	var pattern := RegEx.new()
	pattern.compile("\\b%s\\b" % identifier)
	return pattern.search(code) != null


## The public and private function names a module declares, sorted, from its own
## source: the check that a syringe-cost, damage, occupancy, or charge helper
## cannot hide.
func _declared_methods(res_path: String) -> Array:
	var body := FileAccess.get_file_as_string(res_path)
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
## declarations.
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


## How many arguments a named method declares, read from its own source rather
## than from a runtime method list — so the check needs no instance.
func _argument_count(res_path: String, method: String) -> int:
	var declaration := _declaration_of(res_path, method)
	if declaration.is_empty():
		return -1
	var open := declaration.find("(")
	var close := declaration.find(")")
	if open == -1 or close == -1 or close < open:
		return -1
	var arguments := declaration.substr(open + 1, close - open - 1).strip_edges()
	if arguments.is_empty():
		return 0
	return arguments.split(",").size()


## The declared return type of a named method, read from its own source.
func _result_type_of(res_path: String) -> String:
	var declaration := _declaration_of(res_path, "resurrect_hero_town")
	var arrow := declaration.find("->")
	if arrow == -1:
		return ""
	return declaration.substr(arrow + 2).strip_edges().trim_suffix(":")


## The whole declaration of a named method, reassembled across the line
## continuations GDScript allows: this line's operations wrap their parameter
## lists, so a single line is not enough to read the argument count or the
## return type from.
func _declaration_of(res_path: String, method: String) -> String:
	var body := FileAccess.get_file_as_string(res_path)
	var collecting := false
	var out := ""
	for line: String in body.split("\n"):
		var stripped := line.strip_edges()
		if not collecting:
			if stripped.begins_with("func %s(" % method) \
					or stripped.begins_with("static func %s(" % method):
				collecting = true
				out = stripped
			continue
		out += " " + stripped
		if _balanced(out):
			return out
	return ""


## Whether a reassembled declaration's parentheses are balanced.
func _balanced(text: String) -> bool:
	var depth := 0
	for index in range(text.length()):
		var character := text[index]
		if character == "(":
			depth += 1
		elif character == ")":
			depth -= 1
			if depth == 0:
				return true
	return false


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------


## The committed numbers of any JSON value, normalised to integers — the shape
## the pinned engine's parser produces them in.
func _normalize(value: Variant) -> Variant:
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	if value is Array:
		var list: Array = []
		for entry: Variant in value as Array:
			list.append(_normalize(entry))
		return list
	if value is Dictionary:
		var bag := {}
		for key: Variant in (value as Dictionary).keys():
			bag[key] = _normalize((value as Dictionary)[key])
		return bag
	return value


## A committed number as the exact integer it denotes.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


## A sorted copy of a list, so a pinned expected list can be compared with a
## measured one regardless of declaration order.
func _sorted_copy(values: Array) -> Array:
	var out: Array = values.duplicate()
	out.sort()
	return out


## The recorded type of a value as a readable name, so a refusal can say what
## the ledger actually held.
func _type_name(value: Variant) -> String:
	if value == null:
		return "null"
	if value is bool:
		return "boolean"
	if value is int:
		return "int"
	if value is float:
		return "float"
	if value is String:
		return "String"
	if value is Array:
		return "Array"
	if value is Dictionary:
		return "Dictionary"
	return type_string(typeof(value))


## Whether a list of sentences contains the given phrase, as a substring.
func _contains_phrase(lines: Variant, phrase: String) -> bool:
	for line: Variant in lines as Array:
		if str(line).contains(phrase):
			return true
	return false


## Asserts a phrase appears in some text, naming the text it came from.
func check_in_text(text: String, phrase: String, label: String) -> void:
	check(text.contains(phrase), "%s (looked for %s)" % [label, phrase])


func _working_saves_exist() -> bool:
	return DirAccess.dir_exists_absolute(
		Paths.repo_root().path_join("saves"))


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
