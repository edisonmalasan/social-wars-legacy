extends "res://tests/test_base.gd"
## Combat-action suite (OpenSpec `godot-combat-actions`, milestone M10 line 2).
##
## The line delivers the preserved server's combat-action surface -- `end_attack`,
## `kill`, and `kill_iid` -- as ONE server-authoritative typed result, and it
## delivers the opposite of what the branch's own name suggests: the client may
## NOT say how many rows were lost (design D1/D2).
##
## Sections, in the order they run:
##
##   inventory   the field inventory RE-DERIVED from `command.py` bytes, its three
##               fates, its recorded-versus-measured correction, and every derived
##               line asserted against the committed source it names;
##   second      a SECOND, independent extraction from the same bytes, requiring
##               exact identity on key names, key order, and per-key fate, so the
##               module's own derivation is evidence rather than a tautology;
##   provenance  three POSITIVE guards (a derived line really carries what the
##               record says; the second extraction agrees; the suite itself
##               transcribes no key) plus the structural inventory pin and the
##               absent-helper list;
##   resolve     the derived destruction over crafted in-memory state, the
##               recorded-order precedence, the ledger increment behind BOTH gates,
##               and every refusal path;
##   kills       the two kill contracts, delivered DIFFERENTLY -- `kill` deletes a
##               row and never touches the ledger, `kill_iid` is a proven no-op;
##   dictation   the design-D2 refusal, and that it is a NAMED SEPARATE guard from
##               the design-D1 eligibility check;
##   ordering    the ten-step validation order, the design-D3 ordering rule, the
##               four proof halves, and the recorded divergence;
##   census      the committed corpus measurement, over every committed save
##               document, plus the committed-content distributions it uses;
##   transport   the wire contract: three-key bodies, and the live implementation
##               naming none of the refused keys;
##   boundary    nothing anywhere derives a discarded value, damage, duration,
##               honour, reward, or a mission completion;
##   containment the content package, the committed saves, the committed
##               fixtures, and the legacy root modules are byte-identical after
##               the run.
##
## Hermetic: no process, no server, no socket, and no request over the network.
## The intent is exercised through the offline double and through
## `CombatFlow.build_response()`, and the live phase (`--scenario=live-combat`)
## is registered separately in verify-boot.ps1.
##
## `--report=<path>` writes the deterministic `combat-actions-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/combat-actions/report.json`, and the destination directory is
## created first. Every table is derived from the delivered module's own
## constants, from this run's own measurement of the committed legacy source, or
## from committed bytes, so the report cannot drift from the code it documents.
## It deliberately does NOT read the committed fixture manifest, because that
## carries a capture timestamp; the parity evidence lives in the Python
## replay suite, and this report carries a path pointer to it.

const CombatFlow = preload("res://scripts/units/combat_flow.gd")
const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/combat-actions/report.json"

## The delivered module and the one live implementation whose body this suite
## inspects, named so every scan reads them from one place.
const MODULE_PATH := "scripts/units/combat_flow.gd"
const LEGACY_V0_PATH := "scripts/gameapi/legacy_v0_api.gd"

## The preserved legacy source the whole inventory is derived from.
const LEGACY_COMMAND := "command.py"
const LEGACY_ENGINE := "engine.py"

## The committed corpus documents this line censuses: eight under `villages/` and
## two under `tests/saves/`. `tests/saves/manifest.json` is a manifest rather
## than a save, and `villages/quest/` holds quest documents of another shape --
## both exclusions are measured rather than assumed, below.
const VILLAGE_DIR := "villages"
const SAVES_DIR := "tests/saves"
const EXCLUDED_SAVE_DOCUMENTS := ["manifest.json"]

## The committed measurements, corrected against the committed investigation in
## `combat_envelope.CORPUS_CORRECTION` and re-derived here over the committed
## bytes, so the correction is checked rather than carried.
const EXPECTED_DOCUMENTS := 10
const EXPECTED_PLACED_ROWS := 3372
const EXPECTED_UNIT_ROWS := 441
const EXPECTED_UNIT_ROWS_ON_TEAM_ONE := 441
const EXPECTED_UNIT_ROWS_RESURRECTABLE := 429
const EXPECTED_DOCUMENTS_WITH_UNIT_ROWS := 7
const EXPECTED_DOCUMENTS_WITH_NON_EMPTY_LEDGER := 4
const EXPECTED_NEUTRAL_LEDGER_KEYS := 28

## The recorded-versus-measured correction the module carries, pinned so the
## correction itself cannot be quietly deleted.
const EXPECTED_RECORDED_KEY_COUNT := 11
const EXPECTED_MEASURED_KEY_COUNT := 12
const EXPECTED_RECORDED_DISCARDED_COUNT := 7
const EXPECTED_MEASURED_DISCARDED_COUNT := 9
const EXPECTED_RECORDED_DOCUMENTS := 11
const EXPECTED_RECORDED_DOCUMENTS_WITH_LEDGER := 5
const EXPECTED_RECORDED_NEUTRAL_LEDGER_KEYS := 29

## The recorded order precedence, measured over one committed village document.
## The three orders are three DIFFERENT answers, which is what makes the ordering
## claim testable rather than decorative.
const ORDER_DOCUMENT := "villages/AcidCaos.json"
const ORDER_ITEM_ID := 1020
const ORDER_RECORDED_FIRST := "2425"
const ORDER_SNAPSHOT_FIRST := "1022"
const ORDER_NUMERIC_MIN := "897"

## A committed placed row the offline double's positive path removes. Map key 1
## of `tests/saves/fresh-player.json` is the Command Center, and its item id is
## read out of the committed bytes at run time rather than trusted from here.
const DOUBLE_MAP_KEY := 1
const DOUBLE_ITEM_ID := 26

## A committed unit id with ZERO placed rows in the committed corpus: the
## identity whose recorded `Lost 1` established that the branch's printed count
## is a request and not an outcome.
const IDENTITY_WITH_NO_ROWS := 923

## The seven stored resource slots, and the full set the no-cost proof compares.
const RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

## Tokens that would mean a pure projection gained a node, a clock, a request, or
## a transport.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ",
	"Engine.get_ticks", "Time.get_ticks", "rand", "push_error",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]

## Tokens whose presence would mean a combat, mission, or cost mechanism has been
## implemented. Spelled as fragments for the same project-scope reason as the
## delivered refusal modules: the project-scope suite scans every source file for
## their literal forms, so the needles are assembled here.
const NEEDLES := [
	"resolve_" + "damage", "damage_" + "for", "apply_" + "attack",
	"hit_" + "chance", "honor_" + "for", "reward_" + "for",
	"complete_" + "mission", "lost_" + "count", "resolve_" + "type",
	"is_" + "occupied", "in_" + "bounds", "terrain_" + "at",
	"frame_" + "duration", "travel_" + "time",
]

## Comparison tokens that would make a line a comparison at all.
const COMPARISON_TOKENS := ["==", "!=", "<=", ">=", "<", ">"]

## Every arithmetic operator the delivered module must not contain at all.
const ARITHMETIC_TOKENS := {
	"multiply_operators": "*",
	"divide_operators": "/",
	"modulo_operators": "%",
	"power_operators": "**",
	"shift_operators": "<<",
	"bitwise_operators": "&",
}

## The one client key name that legitimately occurs in this suite's own code: the
## local holding the seven-resource projection. The exclusion is pinned to
## exactly this entry, so it cannot be widened silently to admit a transcribed
## key.
const SUITE_KEY_EXCLUSION := ["resources"]

## The committed combat field names, read as a WORD list so `life` cannot match
## `lifetime` and `attack` cannot match `attack_interval`.
const COMBAT_FIELD_NAMES := ["attack", "defense", "life", "attack_interval",
	"attack_range", "best_against", "best_against_mult", "resurrectable",
	"syringes", "clicks_to_build", "velocity", "max_frame"]

## GDScript keywords and literals, excluded from the operand inventory because a
## keyword cannot be the name of a computed value.
const GDSCRIPT_KEYWORDS := ["else", "for", "if", "in", "return", "null",
	"true", "false", "and", "or", "not", "var", "const", "static", "func",
	"self", "class_name", "extends", "signal", "enum", "break", "continue",
	"pass", "match", "while", "await"]

## The committed parity fixture, recorded by `apps/compat-api/
## capture_combat_fixture.py`. The report carries a POINTER to it; it never reads
## the manifest, which carries a capture timestamp.
const FIXTURE_PATH := "tests/fixtures/godot-combat-actions"
const PARITY_SUITE := "apps/compat-api/tests/test_combat_parity.py"

## The registry reference the content measurements read, set once in
## `run_scenario()`.
var _registry: Variant = null

## The committed-content distributions this run measured, written into the
## report so the report carries the run's own figures rather than prose.
var _distribution := {}


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if _scenario_arg() == "live-combat":
		await _check_live_combat()
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	_registry = registry
	# The registry must be loaded before any committed-content measurement reads
	# it, so the load is a checked precondition here rather than an assumption
	# inside every helper below.
	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"the verified content registry loads: %s" % str(content.get("error", "")))
	if not bool(content.get("ok", false)):
		return
	var package_dir := Paths.repo_root().path_join("packages/game-content")
	var saves_dir := Paths.repo_root().path_join("villages")
	var corpus_dir := Paths.repo_root().path_join("tests/saves")
	var fixtures_dir := Paths.repo_root().path_join("tests/fixtures")
	var package_before := Paths.directory_digest(package_dir)
	var villages_before := Paths.directory_digest(saves_dir)
	var corpus_before := Paths.directory_digest(corpus_dir)
	var fixtures_before := Paths.directory_digest(fixtures_dir)
	for named: Dictionary in [
		{"label": "content package", "digest": package_before},
		{"label": "committed village documents", "digest": villages_before},
		{"label": "committed corpus saves", "digest": corpus_before},
		{"label": "committed fixtures", "digest": fixtures_before},
	]:
		check(bool((named["digest"] as Dictionary).get("ok", false)),
			"%s digest is readable before the run (%s)" % [str(named["label"]),
				str((named["digest"] as Dictionary).get("error", ""))])
		if not bool((named["digest"] as Dictionary).get("ok", false)):
			return
	var legacy_before := _legacy_digest()
	check(bool(legacy_before.get("ok", false)),
		"legacy root modules digest is readable before the run (%s)"
			% str(legacy_before.get("error", "")))
	if not bool(legacy_before.get("ok", false)):
		return

	var inventory := _check_inventory()
	var second := _check_second_extraction(inventory)
	_check_resolve()
	_check_kills()
	_check_dictation()
	_check_ordering()
	var census := _check_census()
	_check_provenance()
	_check_transport()
	await _check_double(census)
	_check_boundary()
	_check_containment(package_before, villages_before, corpus_before,
		fixtures_before, legacy_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, inventory, second, census)
	info("combat actions: %d derived keys (%d discarded, %d print-only, "
		% [int(inventory.get("key_count", 0)),
			(inventory.get("discarded", []) as Array).size(),
			(inventory.get("print_only", []) as Array).size()]
		+ "%d on the mutation path), %d corpus unit rows, 1 destruction, "
		% [(inventory.get("mutation_path", []) as Array).size(),
			(census as Dictionary).get("unit_rows", 0)]
		+ "0 client-dictated counts")


# ---------------------------------------------------------------------------
# The field inventory, re-derived from the committed bytes
# ---------------------------------------------------------------------------


## The inventory as this run derived it, plus every recorded-versus-measured
## figure checked against the committed source line it names.
func _check_inventory() -> Dictionary:
	info("--- field inventory, derived from %s bytes ---" % LEGACY_COMMAND)
	var inventory: Dictionary = CombatFlow.derive_field_inventory()
	check(bool(inventory.get("ok", false)),
		"the field inventory derives from the committed %s: %s"
			% [LEGACY_COMMAND, str(inventory.get("error", ""))])
	if not bool(inventory.get("ok", false)):
		return inventory

	check_eq(int(inventory.get("key_count", 0)), EXPECTED_MEASURED_KEY_COUNT,
		"the branch reads %d client keys, measured this run"
			% EXPECTED_MEASURED_KEY_COUNT)
	check_eq((inventory.get("key_names", []) as Array).size(),
		EXPECTED_MEASURED_KEY_COUNT,
		"and the key-name list agrees with the record count")
	check_eq(inventory.get("fates"), CombatFlow.FATES,
		"the fate vocabulary is the closed three-name one, in order")
	check_eq(bool(inventory.get("partition", false)), true,
		"the three fates partition the inventory: no key is filed under none")

	var discarded: Array = inventory.get("discarded", []) as Array
	var printing: Array = inventory.get("print_only", []) as Array
	var mutation: Array = inventory.get("mutation_path", []) as Array
	check_eq(discarded.size(), EXPECTED_MEASURED_DISCARDED_COUNT,
		"%d keys reach nothing at all, measured this run"
			% EXPECTED_MEASURED_DISCARDED_COUNT)
	check_eq(printing.size(), 2,
		"two keys reach only the branch's own print statements")
	check_eq(mutation.size(), 1,
		"exactly ONE key reaches the row-removal path")
	check_eq(mutation, ["attacker_units"],
		"and that one key is the attacker's own unit list")

	# The three sets are disjoint and their union is the whole inventory, checked
	# here as well as inside the derivation, because a derivation that reported a
	# partition would otherwise be its own witness.
	var overlap := 0
	for key: String in discarded:
		if printing.has(key) or mutation.has(key):
			overlap += 1
	for key: String in printing:
		if mutation.has(key):
			overlap += 1
	check_eq(overlap, 0, "the three fate sets are pairwise disjoint")
	var union: Array = []
	union.append_array(discarded)
	union.append_array(printing)
	union.append_array(mutation)
	var missing := 0
	for key: Variant in inventory.get("key_names", []) as Array:
		if not union.has(key):
			missing += 1
	check_eq(missing, 0, "and their union is the whole key inventory")

	# --- the correction, checked rather than carried ------------------------
	var correction: Dictionary = inventory.get("correction", {}) as Dictionary
	check_eq(int(correction.get("recorded_read_key_count", -1)),
		EXPECTED_RECORDED_KEY_COUNT,
		"the recorded investigation stated %d read keys"
			% EXPECTED_RECORDED_KEY_COUNT)
	check_eq(int(correction.get("recorded_discarded_count", -1)),
		EXPECTED_RECORDED_DISCARDED_COUNT,
		"and %d discarded" % EXPECTED_RECORDED_DISCARDED_COUNT)
	check_eq(int(correction.get("recorded_discarded_count_in_the_own_table", -1)), 8,
		"while its own table listed eight discarded rows, a third figure")
	check_eq(str(correction.get("key_absent_from_the_recorded_table", "")),
		"voluntary_end",
		"and the key absent from both the prose and the table is named")
	check(discarded.has("voluntary_end"),
		"which this run measures among the discarded keys, so the correction's "
			+ "missing key is present and merely unrecorded")

	# --- every derived line is asserted against the source it names ----------
	#
	# Provenance rather than transcription: each key records the line its own
	# membership test is declared on and the lines its name occurs on afterwards,
	# and every one of those line numbers is checked against the committed file.
	var bad_declaration := 0
	var bad_site := 0
	var checked_sites := 0
	for record: Variant in inventory.get("keys", []) as Array:
		var entry: Dictionary = record
		var tested_at := str(entry.get("tested_at", ""))
		if not _legacy_line_carries(tested_at, "\"%s\" in response:"
				% str(entry.get("key", ""))):
			bad_declaration += 1
		var sites: Array = entry.get("post_test_sites", []) as Array
		var word := str(entry.get("key", ""))
		var inside := bool(entry.get("inside_row_removal_region", false))
		for site: Variant in sites:
			checked_sites += 1
			if not _legacy_line_carries(str(site), word):
				bad_site += 1
		if inside and sites.is_empty():
			bad_site += 1
	check_eq(bad_declaration, 0,
		"every key's recorded membership-test line really declares that key")
	check_eq(bad_site, 0,
		"every recorded post-test site really carries that key's name")
	check_eq(checked_sites, 5,
		"the five recorded post-test sites are the five the branch really has: "
			+ "victim on two lines, win on two, and attacker_units on the one "
			+ "removal line")

	# A declaration is not a use: the two are recorded separately and never
	# conflated, which is precisely how a discarded key would look if merged.
	var site_records := 0
	for record: Variant in inventory.get("keys", []) as Array:
		var sites: Array = (record as Dictionary).get("post_test_sites", []) as Array
		if int((record as Dictionary).get("post_test_site_count", -1)) != sites.size():
			site_records += 1
		if int((record as Dictionary).get("post_test_distinct_lines", -1)) \
				!= sites.size():
			site_records += 1
	check_eq(site_records, 0,
		"the occurrence count and the distinct-line count are recorded per key "
			+ "and agree here because no key repeats on one line")

	# The two measured orderings, asserted against the committed source.
	var span: Array = inventory.get("branch_span", []) as Array
	check_eq(span, [808, 885],
		"the branch span is the recorded command.py:808-885, measured this run")
	var region: Array = inventory.get("row_removal_region", []) as Array
	check_eq(region, [866, 873],
		"the row-removal region is located by SEARCHING for map_lose_item(, "
			+ "measured this run")
	check(_legacy_line_carries("command.py:866", "for unit in attacker_units:"),
		"and the region really opens on the loop that contains the call, which is "
			+ "ABOVE it -- so the region had to be found by searching backward")
	check(_legacy_line_carries("command.py:868", "max(0, unit[2] - unit[3])"),
		"the client's own casualty subtraction is at command.py:868, and this "
			+ "line refuses it rather than reproducing it")
	check(_legacy_line_carries("command.py:871", "print(f\"Lost "),
		"the unconditional print at command.py:871 is INSIDE that loop and "
			+ "unconditional within it")
	check(_legacy_line_carries("command.py:872", "map_lose_item("),
		"while the removal call it appears to describe is at command.py:872, so "
			+ "the printed count is a REQUEST and not an outcome")
	return inventory


## The inventory re-derived by a SECOND, independent extraction in this suite.
##
## Deliberately not a call into the module: it re-reads `command.py`, finds the
## branch, collects the membership tests, finds the block's end by its own rule,
## locates the removal region by its own search, and reclassifies each key with
## its own lexer. Agreement between the two is therefore evidence.
func _check_second_extraction(inventory: Dictionary) -> Dictionary:
	info("--- second, independent extraction ---")
	var mine := _extract_inventory()
	check(bool(mine.get("ok", false)),
		"the suite's own extraction runs: %s" % str(mine.get("error", "")))
	if not bool(mine.get("ok", false)):
		return mine
	if not bool(inventory.get("ok", false)):
		fail("the second extraction is compared against a derived inventory")
		return mine

	check_eq(mine.get("key_names"), inventory.get("key_names"),
		"both extractions name the same keys in the same committed order")
	check_eq(mine.get("discarded"), inventory.get("discarded"),
		"both classify the same keys as reaching nothing")
	check_eq(mine.get("print_only"), inventory.get("print_only"),
		"both classify the same keys as reaching only a print")
	check_eq(mine.get("mutation_path"), inventory.get("mutation_path"),
		"both classify the same keys as reaching the removal path")
	check_eq(mine.get("branch_span"), inventory.get("branch_span"),
		"both locate the branch at the same committed span")
	check_eq(mine.get("row_removal_region"), inventory.get("row_removal_region"),
		"both locate the removal region at the same committed lines")

	# The per-key fate, compared key by key rather than as three sets, so a key
	# could not be traded between two sets and still agree.
	var by_key := {}
	for record: Variant in inventory.get("keys", []) as Array:
		by_key[str((record as Dictionary).get("key", ""))] = str(
			(record as Dictionary).get("fate", ""))
	var fate_mismatch := 0
	for record: Variant in mine.get("keys", []) as Array:
		var entry: Dictionary = record
		var key := str(entry.get("key", ""))
		if str(by_key.get(key, "")) != str(entry.get("fate", "")):
			fate_mismatch += 1
			fail("the fate of %s disagrees: module %s, suite %s" % [key,
				str(by_key.get(key, "")), str(entry.get("fate", ""))])
	check_eq(fate_mismatch, 0,
		"every key carries the same fate under both extractions")

	# The drift guard is testable: a mistranscribed key in the suite's own table
	# would be caught by the identity check above, and an injected legacy edit is
	# caught by the module's own derivation. Neither is trusted; both are shown
	# to be reachable rather than merely plausible.
	var injected := CombatFlow.derive_field_inventory(
		_legacy_command_text().replace("if \"honor\" in response:",
			"if \"honor_injected\" in response:"))
	# The injection REWRITES one committed key rather than adding beside it, so
	# the count must stay at twelve while the substituted spelling appears and the
	# committed one disappears. Asserting the count alone would be satisfied by a
	# derivation that kept `honor` AND appended `honor_injected`, so all three
	# halves are asserted: count, presence, absence.
	check_eq(int(injected.get("key_count", 0)), EXPECTED_MEASURED_KEY_COUNT,
		"a rewritten legacy key leaves the derived COUNT at %d, because the "
			% EXPECTED_MEASURED_KEY_COUNT
			+ "inventory follows the source rather than a transcribed table")
	check((injected.get("key_names", []) as Array).has("honor_injected"),
		"and the injected spelling appears by name, so the derivation really "
			+ "read the injected bytes")
	check(not (injected.get("key_names", []) as Array).has("honor"),
		"and the committed key it replaced is gone, so the derivation did not "
			+ "also keep a transcribed copy of the original")
	return mine


## This suite's own extraction of the same committed bytes.
func _extract_inventory() -> Dictionary:
	var out := {
		"ok": false, "error": "", "branch_span": [], "row_removal_region": [],
		"keys": [], "key_names": [], "discarded": [], "print_only": [],
		"mutation_path": [],
	}
	var lines := _legacy_command_text().split("\n")
	var start := -1
	var end := -1
	# The committed dispatcher opens this branch with `elif`, so the opener is
	# matched on the command name and the `elif` prefix rather than on `if`.
	var opener := "cmd == \"%s\":" % CombatFlow.COMBAT_BRANCH
	for index in lines.size():
		var line := str(lines[index]).strip_edges()
		if start < 0 and line.begins_with("elif ") \
				and line.contains(opener):
			start = index
			continue
		if start >= 0 and index > start \
				and (line.begins_with("elif cmd == \"")
					or line.begins_with("if cmd == \"")):
			end = index
			break
	if start < 0 or end < 0:
		out["error"] = "the end_attack branch was not located"
		return out
	out["branch_span"] = [start + 1, end]

	# The membership tests, in file order.
	var membership := RegEx.new()
	membership.compile("^\\s*if\\s+\"([A-Za-z_]+)\"\\s+in\\s+response:\\s*$")
	var names: Array = []
	var block_end := start
	for index in range(start, end):
		var found := membership.search(str(lines[index]))
		if found == null:
			continue
		names.append(found.get_string(1))
		block_end = index + 1
	# The block continues past its last test: each test is followed by the line
	# that transports the value out of the blob.
	while block_end < end and _python_code(str(lines[block_end])).contains("response["):
		block_end += 1

	# The removal region, located by searching for the call itself.
	var call_line := -1
	for index in range(start, end):
		if _python_code(str(lines[index])).contains("map_lose_item("):
			call_line = index
			break
	var region_start := -1
	var region_end := -1
	if call_line >= 0:
		# The region is the loop that CONTAINS the call, so it opens ABOVE the
		# call: this suite searches backward for it, independently of the module.
		region_start = call_line
		region_end = call_line + 1
		for index in range(call_line - 1, start - 1, -1):
			if str(lines[index]).strip_edges().begins_with("for "):
				region_start = index
				break
		# It closes at the first following non-blank line indented no deeper than
		# the loop itself, which is the Python block rule rather than a search for
		# the next loop: the removal loop's own successor is an `if`, so a
		# forward search for another loop finds nothing and would leave the
		# region reported as a one-line span.
		var loop_indent := _indent_of(str(lines[region_start]))
		for index in range(region_start + 1, end):
			var stripped := str(lines[index]).strip_edges()
			if stripped == "":
				continue
			if _indent_of(str(lines[index])) <= loop_indent:
				region_end = index
				break
	out["row_removal_region"] = [region_start + 1, region_end]

	var discarded: Array = []
	var printing: Array = []
	var mutation: Array = []
	var records: Array = []
	for name: Variant in names:
		var key := str(name)
		var sites: Array = []
		var inside := false
		for index in range(block_end, end):
			if not _word_occurs(_python_code(str(lines[index])), key):
				continue
			sites.append(index)
			if region_start <= index and index < region_end:
				inside = true
		var fate := CombatFlow.FATE_DISCARDED
		if not sites.is_empty():
			if inside:
				fate = CombatFlow.FATE_MUTATION
				mutation.append(key)
			else:
				fate = CombatFlow.FATE_PRINT
				printing.append(key)
		else:
			discarded.append(key)
		records.append({"key": key, "fate": fate,
			"post_test_site_count": sites.size()})
	out["ok"] = true
	out["keys"] = records
	out["key_names"] = names
	out["discarded"] = discarded
	out["print_only"] = printing
	out["mutation_path"] = mutation
	return out


# ---------------------------------------------------------------------------
# The resolve path: derived destruction, ledger gates, refusals
# ---------------------------------------------------------------------------


## One crafted placement map and ledger, so every path below runs over
## in-memory input and never needs a service.
##
## Keys are inserted in a chosen order on purpose: the recorded order is the
## INSERTION order, which is neither numeric nor the key-sorted order a captured
## snapshot would carry.
func _crafted_items() -> Dictionary:
	return {
		"2425": [1034, 10, 10, 0, 0, [], {}, 1],
		"897": [1034, 11, 11, 0, 0, [], {}, 1],
		"1022": [1034, 12, 12, 0, 0, [], {}, 3],
		"40": [26, 51, 41, 0, 0, [], {}, 1],
	}


## One committed unit definition, read through the verified registry.
func _committed_unit(item_id: int) -> Dictionary:
	return _registry_entry("units", str(item_id))


## The `item_of` callable `project_combat()` takes, so the module never resolves
## a definition itself.
func _item_resolver(item_id: int) -> Variant:
	var entry := _committed_unit(item_id)
	if entry.is_empty():
		return null
	return entry


func _check_resolve() -> void:
	info("--- the derived destruction and the ledger gates ---")
	var items := _crafted_items()

	# --- eligible rows: identity AND a truthy team -------------------------
	var eligible := CombatFlow.select_eligible_rows(items, 1034)
	check(bool(eligible.get("ok", false)),
		"an identity with three truthy-team rows resolves")
	check_eq(eligible.get("eligible_keys"), ["2425", "897", "1022"],
		"every row whose slot 0 equals the identity AND whose slot 7 is truthy, "
			+ "in the map's OWN insertion order")
	check_eq(str(eligible.get("addressed_key", "")), ORDER_RECORDED_FIRST,
		"the first is chosen by RECORDED order, not numeric order")
	check_eq(int(eligible.get("eligible_count", -1)), 3,
		"the eligible count is reported, never used as a bound")
	check(eligible.get("addressed_row", null) is Array,
		"the addressed row is reported as the committed eight-slot row")
	check_eq((eligible.get("addressed_row", []) as Array).size(),
		CombatFlow.MAP_ROW_SLOTS, "with all eight slots")

	# The three orders are three answers, which is what makes the claim testable.
	var numeric: Array = ["2425", "897", "1022"]
	numeric.sort_custom(func(one: Variant, two: Variant) -> bool:
		return int(one) < int(two))
	check_eq(str(numeric[0]), ORDER_NUMERIC_MIN,
		"numeric order would choose %s, not %s"
			% [ORDER_NUMERIC_MIN, ORDER_RECORDED_FIRST])
	var sorted_snapshot: Array = ["2425", "897", "1022"]
	sorted_snapshot.sort()
	check_eq(str(sorted_snapshot[0]), ORDER_SNAPSHOT_FIRST,
		"and key-sorted order would choose %s, the order a captured snapshot "
			% ORDER_SNAPSHOT_FIRST + "carries because its keys are written sorted")

	# A falsy team is not eligible: this is the recorded truthiness test, not a
	# team-one rule, and the asymmetry it creates is recorded rather than closed.
	var falsy := CombatFlow.select_eligible_rows(items, 1034)
	check((falsy.get("eligible_keys", []) as Array).has("1022"),
		"a team of 3 IS eligible, because map_lose_item tests TRUTHINESS "
			+ "(engine.py:221) and not team one")
	var untruthy := CombatFlow.select_eligible_rows(
		{"5": [1034, 1, 1, 0, 0, [], {}, 0]}, 1034)
	check(not bool(untruthy.get("ok", true)),
		"a row on a falsy team is never eligible")
	check_eq(str(untruthy.get("reason", "")),
		CombatFlow.REASON_NO_ELIGIBLE_ROW,
		"and an identity with no eligible row is refused by its own name")

	# Every refusal of the eligibility step.
	var refusals := {
		"a non-integer identity": [items, "1034"],
		"a boolean identity": [items, true],
		"a null identity": [items, null],
		"a fractional identity": [items, 900.5],
		"placements that are not an object": [[], 1034],
		"placements that are a string": ["not an object", 1034],
	}
	for label: String in refusals.keys():
		var pair: Array = refusals[label]
		var got := CombatFlow.select_eligible_rows(pair[0], pair[1])
		check(not bool(got.get("ok", true)), "%s is refused" % label)
		check(str(got.get("reason", "")) != "", "%s is refused with a name" % label)
		check_eq((got.get("eligible_keys", []) as Array).size(), 0,
			"%s reports no eligible row at all" % label)

	# --- the whole projection ----------------------------------------------
	var projection := CombatFlow.project_combat(items, {}, "resolve", 1034,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	check(bool(projection.get("ok", false)),
		"a resolve projects over the crafted state: %s"
			% str(projection.get("error", "")))
	if not bool(projection.get("ok", false)):
		return
	check_eq(int(projection.get("destruction", -1)), 1,
		"the derived destruction is EXACTLY ONE, never a count a client chose")
	check_eq(str((projection.get("eligible") as Dictionary)
		.get("addressed_key", "")), ORDER_RECORDED_FIRST,
		"the projected destruction is the recorded-order first row")
	check_eq((projection.get("resource_delta", []) as Array).size(), 8,
		"the derived resource vector is the neutral eight-slot one")
	var nonzero := 0
	for slot: Variant in projection.get("resource_delta", []) as Array:
		if int(slot) != 0:
			nonzero += 1
	check_eq(nonzero, 0, "and every slot of it is zero")

	# --- the ledger increment, behind BOTH gates ----------------------------
	var ledger := {"1034": 2}
	var increment := CombatFlow.expected_ledger_increment(ledger, 1034, 1, 3)
	check(bool(increment.get("ok", false)), "an increment projects")
	check_eq(bool(increment.get("written", false)), true,
		"with both gates held the ledger IS written")
	check_eq(int(increment.get("count_before", -1)), 2, "the count before is the "
		+ "recorded one")
	check_eq(int(increment.get("count_after", -1)), 3,
		"and the count after is one more")
	check_eq(bool(increment.get("present_before", false)), true,
		"the key is reported present before, which decides `+=` over `= 1`")

	var team_gate: Dictionary = (increment.get("gates", {}) as Dictionary) \
		.get("player_team_one", {}) as Dictionary
	var flag_gate: Dictionary = (increment.get("gates", {}) as Dictionary) \
		.get("resurrectable_positive", {}) as Dictionary
	check_eq(bool(team_gate.get("holds", false)), true, "gate one holds on team 1")
	check_eq(bool(flag_gate.get("holds", false)), true,
		"gate two holds on a positive committed flag")
	check_eq((increment.get("gates", {}) as Dictionary).size(),
		UnitBehaviors.GATE_COUNT, "exactly two gates are evaluated, no third")

	var wrong_team := CombatFlow.expected_ledger_increment(ledger, 1034, 3, 3)
	check_eq(bool(wrong_team.get("written", true)), false,
		"a team other than one declines the write")
	check_eq(bool((wrong_team.get("entries", {}) as Dictionary).has("1034")), true,
		"and the pre-execution entries are reported instead of a fabricated one")
	check_eq(int(wrong_team.get("count_after", -1)),
		int(wrong_team.get("count_before", -2)),
		"so the count after equals the count before: nothing moved")
	check_eq(bool(wrong_team.get("increment_computed_with_gates_held", true)),
		false,
		"and the record says the increment was never computed behind held gates")

	var zero_flag := CombatFlow.expected_ledger_increment(ledger, 1034, 1, 0)
	check_eq(bool(zero_flag.get("written", true)), false,
		"a zero committed flag declines the write (engine.py:159)")
	var absent_flag := CombatFlow.expected_ledger_increment(ledger, 1034, 1, null)
	check_eq(bool(absent_flag.get("written", true)), false,
		"an ABSENT committed flag is refused, not read as a zero")
	var string_flag := CombatFlow.expected_ledger_increment(ledger, 1034, 1, "3")
	check_eq(bool(string_flag.get("written", false)), true,
		"the committed flags are STRINGS, so \"3\" is read as the integer three")
	var bad_flag := CombatFlow.expected_ledger_increment(ledger, 1034, 1, true)
	check_eq(str(bad_flag.get("reason", "")), CombatFlow.REASON_INVALID_ITEM_ID,
		"a boolean flag is refused rather than coerced to one")

	# An unreadable ledger is refused before anything is destroyed.
	var broken := CombatFlow.project_combat(items, "not an object", "resolve", 1034,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	check(not bool(broken.get("ok", true)),
		"an unreadable ledger refuses the whole projection")
	check_eq(str(broken.get("reason", "")), CombatFlow.REASON_INVALID_LEDGER,
		"with the ledger's own named refusal")
	check_eq(int(broken.get("destruction", -1)), 0,
		"and NOTHING was derived to destroy, so nothing could have moved")


## `address_row()` and the two kill contracts (design D5).
func _check_kills() -> void:
	info("--- the two kill contracts ---")
	var items := _crafted_items()

	var addressed := CombatFlow.address_row(items, 40)
	check(bool(addressed.get("ok", false)), "an addressed map key resolves")
	check_eq((addressed.get("row", []) as Array).size(), CombatFlow.MAP_ROW_SLOTS,
		"to the committed eight-slot row")
	var absent := CombatFlow.address_row(items, 999999)
	check(not bool(absent.get("ok", true)),
		"a map key that names no row is refused")
	check_eq(str(absent.get("reason", "")),
		CombatFlow.REASON_UNADDRESSABLE_ROW,
		"with its own name, because the legacy branch PRINTS and answers success "
			+ "-- a recorded divergence, not parity")
	var typed := CombatFlow.address_row(items, "40")
	check(not bool(typed.get("ok", true)),
		"a string addressing is refused: the wire value is an integer")
	var bool_key := CombatFlow.address_row(items, true)
	check(not bool(bool_key.get("ok", true)),
		"a boolean addressing is refused for the same reason")

	# `kill` deletes a row and NEVER reaches the ledger.
	var kill := CombatFlow.project_combat(items, {"1034": 2}, "kill", 40,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	check(bool(kill.get("ok", false)), "a kill projects")
	check_eq(int(kill.get("destruction", -1)), 1, "and destroys exactly one row")
	check_eq(bool(kill.get("ledger_written", true)), false,
		"and NEVER writes the ledger")
	var kill_ledger: Dictionary = kill.get("ledger_after", {}) as Dictionary
	check_eq(bool(kill_ledger.get("written", true)), false,
		"the ledger record says so in its own field too")
	check_eq(bool((kill_ledger.get("entries", {}) as Dictionary).has("1034")), true,
		"and the pre-execution entry survives untouched")
	check_eq(str(kill.get("command", "")), CombatFlow.KILL_COMMAND,
		"the projected command is the kill branch")

	# The non-participation is a property of the branch, not of one request, so
	# it is checked against the committed source rather than one outcome.
	var branch: Array = _legacy_lines_between("cmd == \"kill\":",
			"cmd == \"kill_iid\":")
	check(not branch.is_empty(),
		"the kill branch was located in the committed source")
	var ledger_mentions := 0
	var push_calls := 0
	for line: Variant in branch:
		var text := str(line)
		if text.contains("deadHeroes"):
			ledger_mentions += 1
		if text.contains("push_dead_unit"):
			push_calls += 1
	check_eq(ledger_mentions, 0,
		"the kill branch holds ZERO references to the ledger, so the "
			+ "non-participation is structural")
	check_eq(push_calls, 0,
		"and ZERO calls to the ledger's own engine helper, counted separately "
			+ "because a substring count would merge the two figures")

	# `kill_iid` is a PROVEN NO-OP, delivered rather than refused.
	var iid := CombatFlow.project_combat(items, {"1034": 2}, "kill_iid", 1034,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	check(bool(iid.get("ok", false)),
		"the item-keyed kill is ACCEPTED, not refused")
	check_eq(int(iid.get("destruction", -1)), 0, "and destroys nothing")
	check_eq(bool(iid.get("ledger_written", true)), false,
		"and writes no ledger entry")
	check_eq(iid.get("addressed_row", "unset"), null,
		"and resolves no row at all, because it resolves nothing")
	var contract: Dictionary = CombatFlow.KILL_IID_CONTRACT
	check_eq(bool(contract.get("statement_writes_save_state", true)), false,
		"the contract records that the branch WRITES NOTHING")
	check_eq((contract.get("mutates", []) as Array).size(), 0,
		"and names no mutation at all")
	check_eq(bool(contract.get("resources_move", true)), false,
		"and records that no resource moves")
	check_eq(str(contract.get("delivered", "")), "as a proven no-op",
		"and that it is delivered as a proven no-op")
	check_eq(str(contract.get("not_delivered", "")), "as a refusal",
		"and explicitly NOT as a refusal")
	check_eq((contract.get("local_bindings", []) as Array).size(), 2,
		"the two locals it binds are recorded by name")
	# The branch really does bind exactly those two and assign nothing else.
	check(_legacy_line_carries("command.py:183", "if cmd == \"kill_iid\""),
		"the item-keyed kill branch is at command.py:183")
	check(_legacy_line_carries("command.py:184", "item_id"),
		"and binds the item id at command.py:184")
	check(_legacy_line_carries("command.py:187", "print("),
		"its body's only call is the one print at command.py:187")
	var writes := 0
	for line: Variant in _legacy_lines_between("cmd == \"kill_iid\":",
			"cmd == \"batch_remove\":"):
		var stripped := _strip_comment(line).strip_edges()
		if stripped.contains("=") and not stripped.begins_with("item_id =") \
				and not stripped.begins_with("reason_str =") \
				and not stripped.contains("==") and not stripped.contains("!=") \
				and not stripped.contains(">=") and not stripped.contains("<="):
			writes += 1
	check_eq(writes, 0,
		"every assignment target in the item-keyed kill's body is a bare Name, so "
			+ "the no-op is PROVEN from the source and not observed once")


## The design-D2 refusal, and its separation from the design-D1 eligibility check.
func _check_dictation() -> void:
	info("--- the client-dictated destruction refusal ---")
	var inventory: Dictionary = CombatFlow.derive_field_inventory()
	var names: Array = inventory.get("key_names", []) as Array

	# Three families: this line's own count spellings, the two operands, and
	# every key the branch itself reads.
	var refused := CombatFlow.refused_client_keys(
		{"lost": 3, "survived": 1}, names)
	check_eq(refused, ["lost", "survived"],
		"a client-sent casualty figure is refused by name")
	check_eq(CombatFlow.refused_client_keys({"sent": 5, "survived": 4}, names),
		["sent", "survived"],
		"the legacy subtraction's two operands are refused by name")
	check_eq(CombatFlow.refused_client_keys({"honor": 10}, names), ["honor"],
		"and a key the branch itself reads is refused from the DERIVATION, so it "
			+ "tracks a legacy edit instead of drifting from one")
	for key: Variant in names:
		check(CombatFlow.refused_client_keys({str(key): 1}, names).has(str(key)),
			"every one of the %d derived keys is refused as a request key"
				% names.size())
	check_eq(CombatFlow.refused_client_keys({}, names), [],
		"a body carrying only the identity and the addressing is not refused")
	check_eq(CombatFlow.refused_client_keys("not an object", names), [],
		"and a non-object payload yields no invented refusal")
	check_eq(CombatFlow.refused_client_keys({"lost": 1, "resources": 1},
		["honor"]), ["lost"],
		"a spelling only counts when it is in the inventory given, so a key the "
			+ "branch never reads is not refused on its account")
	check_eq(CombatFlow.refused_client_keys({"lost": 1, "resources": 1,
			"survived": 2, "count": 3}, names),
		["count", "lost", "resources", "survived"],
		"the two families ARE refused together, deduplicated and sorted, over the "
			+ "real derived inventory")

	# The refusal is at step 2 and is a DIFFERENT question from step 4.
	var order: Array = CombatFlow.validation_order()
	var dictation_step := _order_step(order, "no_client_dictated_destruction_key")
	var eligible_step := _order_step(order, "eligible_row_resolves")
	check_eq(dictation_step, 2,
		"the client-dictated refusal is step 2, reached BEFORE the addressing")
	check_eq(eligible_step, 4, "the eligibility check is step 4")
	check(dictation_step < eligible_step,
		"so a client that says how many is refused before the player's rows are "
			+ "even read: two questions, two answers")
	check_eq(str((order[dictation_step - 1] as Dictionary).get("code", "")),
		CombatFlow.REASON_CLIENT_DICTATED_DESTRUCTION,
		"and step 2 carries its own named code")
	check_eq(str((order[eligible_step - 1] as Dictionary).get("code", "")),
		CombatFlow.REASON_NO_ELIGIBLE_ROW,
		"while step 4 carries the eligibility code")

	# The three ways one request can fail, kept apart.
	var no_rows := CombatFlow.build_intent("pid", "resolve", IDENTITY_WITH_NO_ROWS)
	check(bool(no_rows.get("ok", false)),
		"an identity with no eligible row is still an ACCEPTABLE request: the "
			+ "count is the client's to get wrong, not the rows'")
	var projection := CombatFlow.project_combat(_crafted_items(), {},
		"resolve", IDENTITY_WITH_NO_ROWS,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	check(not bool(projection.get("ok", true)),
		"and the SERVICE refuses it, as no_eligible_row")
	check_eq(str(projection.get("reason", "")), CombatFlow.REASON_NO_ELIGIBLE_ROW,
		"with the eligibility code, which is NOT the client-dictated one")

	# The count is refused, never reproduced, and never clamped either.
	var refused_reason := CombatFlow.REASON_CLIENT_DICTATED_DESTRUCTION
	check_eq(refused_reason, "client_dictated_destruction",
		"the refusal has its own code")
	var rule := CombatFlow.CLIENT_DICTATED_REFUSAL
	check(rule.contains("max(0, unit[2] - unit[3])"),
		"and the recorded rule names the exact subtraction it refuses")
	check(rule.contains("DIVERGENCE"),
		"and records the difference as a divergence rather than parity")
	check(str(CombatFlow.REFUSED_COUNT_NOTE).contains("EXHAUSTION OF MATCHES"),
		"the note records that the legacy loop's safety is exhaustion, not a bound")
	# Case-folded deliberately: the recorded claim is prose, and asserting on an
	# exact case would test the capitalisation rather than the claim. The three
	# halves are the claim's own structure -- what the count reports, which two
	# committed lines it sits between, and that it is not conditional on the
	# removal it appears to describe.
	var printed_count := str(CombatFlow.PRINTED_COUNT_IS_A_REQUEST).to_lower()
	check(printed_count.contains("not what it destroyed"),
		"and the printed count is recorded as a request, not an outcome")
	check(printed_count.contains("command.py:871")
			and printed_count.contains("precedes the row-removal call at :872"),
		"and it names both committed lines and their order")
	check(printed_count.contains("not conditional on it"),
		"and it records that the print is not conditional on the removal call")
	check(_legacy_line_carries("command.py:868", "max(0, unit[2] - unit[3])"),
		"the refused subtraction is really at command.py:868")
	check(_legacy_line_carries("command.py:871", "print(f\"Lost "),
		"the print that reported it is really at command.py:871")
	# The clamp is refused in the OTHER direction too: an over-count never grows.
	var over := CombatFlow.expected_ledger_increment({"1034": 0}, 1034, 1, 1)
	check_eq(int(over.get("count_after", -1)), 1,
		"the derived count is the delegated increment and nothing else")
	check_eq((over.get("entries", {}) as Dictionary).size(), 1,
		"so exactly one ledger entry can ever change")


## The validation order, the ordering rule, the proof halves, and the divergence.
func _check_ordering() -> void:
	info("--- ordering, proof halves, and the recorded divergence ---")
	var order := CombatFlow.validation_order()
	check_eq(order.size(), CombatFlow.VALIDATION_ORDER_STEPS,
		"the validation order has exactly %d steps"
			% CombatFlow.VALIDATION_ORDER_STEPS)
	var before_dispatch := 0
	var steps := 0
	for record: Variant in order:
		var step := record as Dictionary
		steps += 1
		check_eq(int(step.get("step", -1)), steps,
			"step %d is numbered %d" % [steps, steps])
		if str(step.get("resolves", "")) == "before dispatch":
			before_dispatch += 1
	check_eq(before_dispatch, CombatFlow.VALIDATION_ORDER_STEPS - 2,
		"every step but the write and its proof resolves BEFORE dispatch")
	var write := _order_step(order, "destruction")
	check_eq(str((order[write - 1] as Dictionary).get("resolves", "")),
		"THE WRITE STEP", "step 9 is the write, named as such")
	check_eq(write, CombatFlow.DESTRUCTION_STEP,
		"and it is the pinned destruction step, so the two cannot disagree")
	check_eq(str((order[CombatFlow.VALIDATION_ORDER_STEPS - 1] as Dictionary)
		.get("resolves", "")), "after dispatch",
		"and the last step is the post-execution proof, after dispatch")
	check(str(CombatFlow.ORDERING_RULE).contains("command.py:866"),
		"the recorded ordering rule names the raise that happens BEFORE the loop")
	check(str(CombatFlow.ORDERING_RULE).contains("command.py:874"),
		"and the raise that happens AFTER the removal call")

	var halves: Array = CombatFlow.PROOF_HALVES
	check_eq(halves.size(), 4, "the post-execution proof has exactly four halves")
	var named: Array = []
	for half: Variant in halves:
		var record: Dictionary = half
		named.append(str(record.get("half", "")))
		check(str(record.get("checks", "")) != "",
			"the %s half states what it checks" % str(record.get("half", "")))
		check(str(record.get("why", "")) != "",
			"and why it is that check rather than a count")
	check_eq(named, [
		"placement_set_and_every_other_row",
		"ledger_key_order_and_every_entry_by_value",
		"every_stored_resource_unchanged",
		"row_count_stated_as_a_count_last",
	], "the four halves are the recorded ones, in order")
	check_eq(named[3], "row_count_stated_as_a_count_last",
		"and the count half is LAST, so it can never be the only thing that passed")

	var divergence: Dictionary = CombatFlow.DIVERGENCE
	check_eq(str(divergence.get("status", "")), "DIVERGENCE, NOT PARITY",
		"the recorded divergence is reported as a divergence, never as parity")
	check(str(divergence.get("legacy_status", "")).contains("ARBITRARY"),
		"and names what the legacy server could do")
	check(str(divergence.get("modern_status", "")).contains("AT MOST ONE"),
		"and what this operation does instead")
	check(str(divergence.get("unobserved_request_shape", "")).contains(
			"never observed"),
		"and records that whether a real client sent a multi-unit loss is UNOBSERVED")

	var asymmetry: Dictionary = CombatFlow.team_asymmetry()
	check_eq(str(asymmetry.get("status", "")),
		"RECORDED, NOT EXERCISED, NOT REFUSED",
		"the team asymmetry is recorded, not exercised, and not refused")
	check_eq(bool(asymmetry.get("exercised", true)), false,
		"and the record says it was not exercised")
	check_eq(bool(asymmetry.get("refused", true)), false,
		"and that it is deliberately not refused, which would invent a bound")
	check_eq(int(asymmetry.get("committed_unit_rows", -1)),
		EXPECTED_UNIT_ROWS, "the committed unit-row count agrees with the census")
	check_eq(int(asymmetry.get("committed_unit_rows_on_team_one", -1)),
		EXPECTED_UNIT_ROWS_ON_TEAM_ONE,
		"and every one of them is on team one, which is why it is unreachable")
	check_eq(bool((asymmetry.get("row_removal_helper", {}) as Dictionary)
		.get("is_dispatcher_branch", true)), false,
		"map_lose_item is an ENGINE HELPER, not a dispatcher branch")
	check_eq(bool((asymmetry.get("ledger_helper", {}) as Dictionary)
		.get("is_dispatcher_branch", true)), false,
		"and so is push_dead_unit")


# ---------------------------------------------------------------------------
# The committed corpus, censused this run
# ---------------------------------------------------------------------------


## Every committed save document, this run, with its placement and ledger figures.
func _check_census() -> Dictionary:
	info("--- committed corpus census ---")
	var documents: Array = []
	for relative: String in _committed_documents():
		documents.append(_census_document(relative))

	var placed := 0
	var unit_rows := 0
	var team_one := 0
	var resurrectable := 0
	var with_units := 0
	var with_ledger := 0
	var skipped := 0
	for document: Variant in documents:
		var record: Dictionary = document
		if not bool(record.get("ok", false)):
			skipped += 1
			continue
		placed += int(record.get("placed_rows", 0))
		unit_rows += int(record.get("unit_rows", 0))
		team_one += int(record.get("unit_rows_on_team_one", 0))
		resurrectable += int(record.get("unit_rows_resurrectable", 0))
		if int(record.get("unit_rows", 0)) > 0:
			with_units += 1
		if int(record.get("ledger_keys", 0)) > 0:
			with_ledger += 1

	check_eq(documents.size(), EXPECTED_DOCUMENTS,
		"the corpus is %d committed save documents, enumerated this run from "
			% EXPECTED_DOCUMENTS + "the villages and the corpus saves")
	check_eq(skipped, 0, "and every one of them parsed")
	check_eq(placed, EXPECTED_PLACED_ROWS,
		"across %d placed rows in total" % EXPECTED_PLACED_ROWS)
	check_eq(unit_rows, EXPECTED_UNIT_ROWS,
		"%d of those rows carry a committed UNIT id" % EXPECTED_UNIT_ROWS)
	check_eq(unit_rows, EXPECTED_UNIT_ROWS_ON_TEAM_ONE,
		"and every one of them is on player team one")
	check_eq(resurrectable, EXPECTED_UNIT_ROWS_RESURRECTABLE,
		"and %d of them have a positive committed resurrectable"
			% EXPECTED_UNIT_ROWS_RESURRECTABLE)
	check(resurrectable < unit_rows,
		"so the two ledger gates genuinely disagree over the corpus: %d rows are "
			% resurrectable + "revivable and %d are not, which is why the "
			% unit_rows + "asymmetry is a measurement and not a claim")
	check_eq(with_units, EXPECTED_DOCUMENTS_WITH_UNIT_ROWS,
		"%d documents place at least one unit row"
			% EXPECTED_DOCUMENTS_WITH_UNIT_ROWS)
	check_eq(with_ledger, EXPECTED_DOCUMENTS_WITH_NON_EMPTY_LEDGER,
		"and %d carry a non-empty deadHeroes ledger"
			% EXPECTED_DOCUMENTS_WITH_NON_EMPTY_LEDGER)

	# --- the corpus correction, measured against the committed bytes --------
	var correction: Dictionary = CombatFlow.CORPUS_CORRECTION
	check_eq(int(correction.get("recorded_documents", -1)),
		EXPECTED_RECORDED_DOCUMENTS,
		"the recorded investigation stated %d documents"
			% EXPECTED_RECORDED_DOCUMENTS)
	check_eq(int(correction.get("recorded_documents_with_non_empty_ledger", -1)),
		EXPECTED_RECORDED_DOCUMENTS_WITH_LEDGER,
		"and %d with a non-empty ledger"
			% EXPECTED_RECORDED_DOCUMENTS_WITH_LEDGER)
	check_eq(int(correction.get("recorded_neutral_ledger_keys", -1)),
		EXPECTED_RECORDED_NEUTRAL_LEDGER_KEYS,
		"and 29 keys in Neutral.json")
	check_eq((correction.get("does_not_reproduce", []) as Array).size(), 3,
		"three derived prose figures are recorded as not reproducing")

	# --- one document's figures, so the totals are traceable ----------------
	var neutral := -1
	var neutral_keys := -1
	var acid_unit_rows := -1
	for index in documents.size():
		var record: Dictionary = documents[index]
		if str(record.get("document", "")) == "villages/Neutral.json":
			neutral = index
			neutral_keys = int(record.get("ledger_keys", -1))
		if str(record.get("document", "")) == ORDER_DOCUMENT:
			acid_unit_rows = int(record.get("unit_rows", -1))
	check(neutral >= 0, "the committed Neutral.json document was censused")
	check_eq(neutral_keys, EXPECTED_NEUTRAL_LEDGER_KEYS,
		"Neutral.json's ledger holds %d keys, not the recorded %d"
			% [EXPECTED_NEUTRAL_LEDGER_KEYS, EXPECTED_RECORDED_NEUTRAL_LEDGER_KEYS])
	check(acid_unit_rows > 0,
		"AcidCaos.json places unit rows, so the recorded-order fixture is "
			+ "reachable from committed bytes")

	# --- the recorded order, measured over the committed village ------------
	_check_recorded_order()
	_check_committed_content()
	return {
		"documents": documents,
		"document_count": documents.size(),
		"placed_rows": placed,
		"unit_rows": unit_rows,
		"unit_rows_on_team_one": team_one,
		"unit_rows_resurrectable": resurrectable,
		"documents_with_unit_rows": with_units,
		"documents_with_non_empty_ledger": with_ledger,
		"neutral_ledger_keys": neutral_keys,
	}


## The three orders, over the committed village document the fixture recorded.
##
## This is the check that makes the ordering claim load-bearing: if recorded
## order, numeric order, and key-sorted snapshot order agreed, the choice would
## be unobservable and the recorded string would be decoration.
func _check_recorded_order() -> void:
	var items := _committed_items(ORDER_DOCUMENT)
	check(not items.is_empty(),
		"the committed %s document's placement map is readable"
			% ORDER_DOCUMENT)
	if items.is_empty():
		return
	var eligible := CombatFlow.select_eligible_rows(items, ORDER_ITEM_ID)
	check(bool(eligible.get("ok", false)),
		"item id %d has eligible rows in the committed document"
			% ORDER_ITEM_ID)
	if not bool(eligible.get("ok", false)):
		return
	var recorded: Array = eligible.get("eligible_keys", []) as Array
	check(str(recorded[0]) == ORDER_RECORDED_FIRST,
		"the recorded insertion order chooses %s first" % ORDER_RECORDED_FIRST)
	var numeric: Array = recorded.duplicate()
	numeric.sort_custom(func(one: Variant, two: Variant) -> bool:
		return int(one) < int(two))
	check_eq(str(numeric[0]), ORDER_NUMERIC_MIN,
		"while numeric order would choose %s" % ORDER_NUMERIC_MIN)
	var snapshot: Array = recorded.duplicate()
	snapshot.sort()
	check_eq(str(snapshot[0]), ORDER_SNAPSHOT_FIRST,
		"and the key-sorted order a captured snapshot carries would choose %s"
			% ORDER_SNAPSHOT_FIRST)
	check(recorded[0] != numeric[0] and recorded[0] != snapshot[0],
		"so the three orders really are three answers, and this projection picks "
			+ "the one the legacy helper walks")
	check_eq(str(eligible.get("addressed_key", "")), str(recorded[0]),
		"and the addressed key is that same recorded-order first row")


## The committed-content distributions the ledger gate reads, measured from the
## verified registry rather than from prose.
func _check_committed_content() -> void:
	info("--- committed content distributions ---")
	var unit_ids: Array = _registry.legacy_ids("units").get("ids", []) as Array
	check_eq(unit_ids.size(), 429,
		"the committed units domain carries all 429 definitions")
	var positive := 0
	var absent := 0
	var zero_valued := 0
	var broken := 0
	var flag_reads := 0
	for id_text: Variant in unit_ids:
		var entry: Dictionary = _registry_entry("units", str(id_text))
		var properties: Dictionary = entry.get("properties", {}) as Dictionary
		if not properties.has("resurrectable"):
			absent += 1
			continue
		flag_reads += 1
		var flag: Variant = properties["resurrectable"]
		var value := 0
		if flag is String and str(flag).strip_edges().is_valid_int():
			value = int(str(flag).strip_edges())
		elif flag is float:
			value = int(flag)
		elif flag is int:
			value = int(flag)
		else:
			broken += 1
			continue
		if value > 0:
			positive += 1
		elif value == 0:
			zero_valued += 1
	check_eq(broken, 0, "every committed resurrectable flag reads as an integer")
	check_eq(flag_reads + absent, unit_ids.size(),
		"and every definition either carries the flag or is recorded absent")
	# MEASURED: 426 definitions carry the flag with a positive value and 3 carry
	# no key at all (ids 923, 933 and 1176) — there is NO third bucket, and no
	# committed definition carries a zero-valued flag.
	check_eq(positive + absent, unit_ids.size(),
		"the committed flag distribution reproduces: %d positive and %d absent, "
			% [positive, absent]
			+ "and NO definition carries a zero-valued flag")
	check_eq(zero_valued, 0,
		"which is measured rather than assumed: the zero bucket is empty")
	check_eq(absent, 3,
		"exactly three committed units carry no resurrectable key at all")
	_distribution["resurrectable_flag"] = {
		"definitions": unit_ids.size(),
		"carrying_a_positive_value": positive,
		"carrying_a_zero_value": zero_valued,
		"key_absent_entirely": absent,
		"unreadable": broken,
		"note": "the ledger gate reads this flag; the distribution is "
			+ "reported, and no rule is derived from it beyond the gate the "
			+ "committed engine already evaluates",
	}

	# The field the row-removal helper's truthiness test reads, and the combat
	# fields this line deliberately never turns into a rule.
	# The committed encoding is NOT uniform: six of the seven fields are numeric,
	# and `best_against` is a CATEGORICAL flag whose committed values are the
	# strings `ft_ground`, `ft_armored`, `ft_flying`, `ft_building` and the empty
	# string. Read as an integer it yields zero positive units on all 429, and the
	# field would report as carrying no committed value at all — a statement
	# about the reader rather than about the content. It is therefore measured
	# under its own encoding, and the split is recorded, so the difference is a
	# reported fact rather than a silently dropped field.
	var numeric_fields := ["attack", "defense", "life", "attack_interval",
		"attack_range", "best_against_mult"]
	var categorical_fields := ["best_against"]
	var combat_fields: Array = numeric_fields + categorical_fields
	var encodings := {}
	var nonzero_fields := 0
	for field: String in combat_fields:
		var is_numeric: bool = field in numeric_fields
		var positive_count := 0
		for id_text: Variant in unit_ids:
			var entry: Dictionary = _registry_entry("units", str(id_text))
			if not entry.has(field):
				continue
			var value: Variant = entry[field]
			if is_numeric:
				if value is String and str(value).strip_edges().is_valid_int():
					if int(str(value).strip_edges()) > 0:
						positive_count += 1
				elif value is float and float(value) > 0.0:
					positive_count += 1
				elif value is int and int(value) > 0:
					positive_count += 1
			elif str(value) != "":
				positive_count += 1
		if positive_count > 0:
			nonzero_fields += 1
		info("committed %s is %s on %d units and is still CONTENT only"
				% [field, "positive" if is_numeric else "non-empty",
					positive_count])
		encodings[field] = {
			"encoding": "numeric" if is_numeric else "categorical",
			"units_with_a_committed_value": positive_count,
		}
	_distribution["combat_field_support"] = encodings
	check_eq(nonzero_fields, combat_fields.size(),
		"all %d combat fields carry committed values under their OWN encoding, "
			% combat_fields.size()
			+ "which is why refusing to derive a rule from them costs something "
			+ "real")
	check_eq(numeric_fields.size() + categorical_fields.size(),
		combat_fields.size(),
		"and the seven committed combat fields split into %d numeric and %d "
			% [numeric_fields.size(), categorical_fields.size()]
			+ "categorical, so no field is counted under an encoding that does "
			+ "not fit it")
	check(str(CombatFlow.NO_COMBAT).contains("ZERO legacy consumers"),
		"and the module records that none of them has a legacy consumer")


# ---------------------------------------------------------------------------
# The wire contract
# ---------------------------------------------------------------------------


## Three-key bodies, and the live implementation naming none of the refused keys.
func _check_transport() -> void:
	info("--- the wire contract ---")
	for action: String in CombatFlow.ACTIONS:
		var addressing := 40 if action == CombatFlow.ACTION_KILL else 1034
		var intent := CombatFlow.build_intent("pid", action, addressing)
		check(bool(intent.get("ok", false)),
			"a %s intent builds" % action)
		var body: Dictionary = intent.get("body", {}) as Dictionary
		check_eq(body.size(), 3, "the %s body is exactly three keys" % action)
		check_eq(body.get("action"), action, "and names the action")
		check_eq(body.get("user_id"), "pid", "and the save identity")
		check_eq(body.get(CombatFlow.wire_key(action)), addressing,
			"and the addressing under the ACTION'S OWN wire key")
		var keys: Array = []
		for key: Variant in body.keys():
			keys.append(str(key))
		keys.sort()
		var expected := ["action", "user_id", CombatFlow.wire_key(action)]
		expected.sort()
		check_eq(keys, expected,
			"and nothing else is expressible: no count, no pair, no price")
		# Every refused key is absent from this line's own body, which is what
		# makes the design-D2 refusal a guard on a hostile request rather than on
		# the delivered transport.
		check_eq(CombatFlow.refused_client_keys(body), [],
			"the %s body carries no refused client key at all" % action)

	check_eq(CombatFlow.wire_key(CombatFlow.ACTION_RESOLVE), "item_id",
		"resolve addresses an item id")
	check_eq(CombatFlow.wire_key(CombatFlow.ACTION_KILL), "map_key",
		"kill addresses a map key")
	check_eq(CombatFlow.wire_key(CombatFlow.ACTION_KILL_IID), "item_id",
		"and the item-keyed kill addresses an item id too")
	for action: String in CombatFlow.ACTIONS:
		var key := CombatFlow.wire_key(action)
		check_eq(str((CombatFlow.ACTION_ADDRESSING as Dictionary)[action]) != "", true,
			"the %s addressing is described in words, not only in a key" % action)
		check(key == "item_id" or key == "map_key",
			"and %s names one of the two recorded addressing keys" % key)

	# The refusals the wire cannot express at all.
	var bad_action := CombatFlow.build_intent("pid", "nope", 1)
	check(not bool(bad_action.get("ok", true)),
		"an action outside the closed vocabulary is refused")
	check_eq(str(bad_action.get("reason", "")), CombatFlow.REASON_INVALID_ACTION,
		"with its own named reason")
	var empty_action := CombatFlow.build_intent("pid", "", 1)
	check(not bool(empty_action.get("ok", true)),
		"an empty action is refused")
	var bytes_action := CombatFlow.build_intent("pid",
		"resolve".to_utf8_buffer(), 1)
	check(not bool(bytes_action.get("ok", true)),
		"a bytes action is refused: it cannot come from a request body, and "
			+ "accepting it would widen the vocabulary to a second spelling")
	var bad_addressing := CombatFlow.build_intent("pid", CombatFlow.ACTION_KILL, "1")
	check(not bool(bad_addressing.get("ok", true)),
		"a string addressing is refused")
	check_eq(str(bad_addressing.get("reason", "")),
		CombatFlow.REASON_INVALID_MAP_KEY, "with the map key's own reason")
	var bool_addressing := CombatFlow.build_intent("pid",
		CombatFlow.ACTION_RESOLVE, true)
	check(not bool(bool_addressing.get("ok", true)),
		"a boolean addressing is refused")
	check_eq(str(bool_addressing.get("reason", "")),
		CombatFlow.REASON_INVALID_ITEM_ID, "with the item id's own reason")

	# The live implementation's own combat method, read from the one file allowed
	# to name an endpoint. Its body is located by the one call it makes into the
	# shared module, so a rename cannot silently make this guard vacuous.
	# The marker includes its assignment, because the bare call also appears in
	# the function's own doc comment two lines above the `func` keyword. Matching
	# the bare name therefore located the COMMENT, and the comment is followed
	# immediately by `func`, so the body came back one line long.
	var body := _function_body(Paths.project_dir().path_join(LEGACY_V0_PATH),
		"var intent := CombatFlow.build_intent(")
	check(body != "", "the live combat transport was located in %s"
		% LEGACY_V0_PATH)
	if body.is_empty():
		return
	for key: String in ["item_id", "map_key", "lost", "sent", "survived"]:
		var literal := "\"%s\"" % key
		check_eq(_count_occurrences(body, literal), 0,
			"the live transport names no %s key literal, so it cannot send one"
				% key)
	check(body.contains("CombatFlow.build_intent("),
		"and it builds its body through the shared module")
	check(body.contains("CombatFlow.parse_combat("),
		"and reads its answer through the shared typed parser")
	check(body.contains("COMBAT_PATH"),
		"so the path is the module's constant rather than a second literal")
	var module_path_check := FileAccess.get_file_as_string(
		Paths.project_dir().path_join(MODULE_PATH))
	check(module_path_check.contains("const COMBAT_PATH := \"%s\""
			% CombatFlow.COMBAT_PATH),
		"and the module carries that one path literal")
	check(_count_occurrences(_code_only_keep_strings(_module_source()),
			CombatFlow.COMBAT_PATH) == 1,
		"exactly once, so a second endpoint cannot appear beside it")


# ---------------------------------------------------------------------------
# The offline double, and every parse refusal
# ---------------------------------------------------------------------------


## The in-memory double, driven with no process, server, or socket.
func _check_double(census: Dictionary) -> void:
	info("--- the offline double ---")
	var api: FakeApi = FakeApi.new()
	root.add_child(api)
	var saves: Variant = await api.list_sessions()
	check(saves is BootData.SaveListResult and saves.ok,
		"the offline double lists its committed saves with no process or socket")
	if not (saves is BootData.SaveListResult and saves.ok):
		return
	var user_id := str((saves as BootData.SaveListResult).saves[0].id)

	var empty: Variant = await api.combat_town("", CombatFlow.ACTION_KILL, 1)
	check(not empty.ok, "an empty save identity is refused")
	check_eq(empty.error_code, "missing_user_id", "with its own named code")
	var unknown: Variant = await api.combat_town("does-not-exist-0000",
		CombatFlow.ACTION_KILL, 1)
	check(not unknown.ok, "an unknown save identity is refused")
	check_eq(unknown.error_code, "unknown_user_id", "with its own named code")

	# `kill` against the committed corpus's own map key 1: a real row, really
	# removed, by the real projection.
	var item_id := _corpus_row_item("tests/saves/fresh-player.json", DOUBLE_MAP_KEY)
	check_eq(item_id, DOUBLE_ITEM_ID,
		"the committed corpus's map key %d really holds item id %d"
			% [DOUBLE_MAP_KEY, DOUBLE_ITEM_ID])
	var killed: Variant = await api.combat_town(user_id, CombatFlow.ACTION_KILL,
		DOUBLE_MAP_KEY)
	check(killed is CombatFlow.CombatResult and killed.ok,
		"the double removes the addressed row: %s"
			% (killed.error_message if not killed.ok else ""))
	if not (killed is CombatFlow.CombatResult and killed.ok):
		return
	var typed: CombatFlow.CombatResult = killed
	check_eq(typed.action, CombatFlow.ACTION_KILL, "and reports the action")
	check_eq(typed.command, CombatFlow.KILL_COMMAND, "and the branch")
	check_eq(typed.addressing_key, "map_key", "and its own addressing key")
	check_eq(typed.destruction_count, 1, "and exactly one destruction")
	check_eq(bool(typed.destruction_derived), true,
		"marked SERVER-DERIVED, which is the load-bearing claim of the line")
	check_eq(str(typed.derived_key), str(DOUBLE_MAP_KEY),
		"and the derived key is the one it addressed")
	check_eq(typed.derived_row.size(), CombatFlow.MAP_ROW_SLOTS,
		"with the committed eight-slot row reported verbatim")
	check_eq(bool(typed.ledger_written), false,
		"and no ledger write, because the kill branch never reaches the ledger")
	check_eq(typed.rows_before, 40, "the committed corpus holds 40 placed rows")
	check_eq(typed.rows_after, 39, "and 39 after the derived destruction")
	check_eq(typed.changed, ["/maps/0/items/%s" % DOUBLE_MAP_KEY],
		"the changed-pointer list names exactly the removed row")
	check_eq(_normalize(typed.validation_order).size(),
		CombatFlow.VALIDATION_ORDER_STEPS,
		"the typed result carries the whole validation order")
	check_eq(_normalize(typed.field_inventory.get("key_names", [])),
		(inventory_names()),
		"and the field inventory, re-derived, not transcribed")
	check_eq(bool(typed.field_inventory.get("partition", false)), true,
		"which partitions into its three fates")
	check_eq(typed.refusals.size(), CombatFlow.REFUSAL_COUNT,
		"and all %d recorded refusals travel with the answer"
			% CombatFlow.REFUSAL_COUNT)
	check(str(typed.no_combat) != "" and str(typed.no_cost_or_reward) != ""
			and str(typed.no_syringe_cost) != ""
			and str(typed.no_placement_validation) != "",
		"every recorded no-* statement travels with the answer, so a recorded "
			+ "absence cannot be read as a missing field")
	check_eq(int(typed.kill_contract.get("ledger_references", -1)), 0,
		"and the kill contract records zero ledger references")
	check(str(typed.provenance.get("capability", "")) == "godot-combat-actions",
		"and the answer carries its provenance")
	# The seven stored resources, read back through the typed projection.
	var resources := {}
	for name: String in RESOURCE_NAMES:
		resources[name] = int((typed.resources as BootData.Resources).get(name))
	check_eq(resources.size(), 7,
		"all seven stored resources are reported, never a subset")
	var expected := _corpus_resources("tests/saves/fresh-player.json")
	check_eq(resources, expected,
		"and every one of them is the committed balance: a combat action moves "
			+ "no resource")

	# `kill_iid`: accepted, destroys nothing, and carries its no-op contract.
	var iid: Variant = await api.combat_town(user_id, CombatFlow.ACTION_KILL_IID,
		DOUBLE_ITEM_ID)
	check(iid is CombatFlow.CombatResult and iid.ok,
		"the double delivers the item-keyed kill as a proven no-op, not a "
			+ "refusal")
	if iid is CombatFlow.CombatResult and iid.ok:
		var no_op: CombatFlow.CombatResult = iid
		check_eq(no_op.destruction_count, 0, "which destroys nothing")
		check_eq(bool(no_op.ledger_written), false, "and writes no ledger entry")
		check_eq(str(no_op.kill_iid_contract.get("delivered", "")),
			"as a proven no-op", "and carries the contract that says so")
		check_eq(bool(no_op.kill_iid_contract.get(
				"statement_writes_save_state", true)), false,
			"including that the branch writes nothing")
		check_eq(no_op.rows_after, no_op.rows_before,
			"and the row count did not move")

	# `resolve` against the committed corpus, which places NO unit rows: refused,
	# honestly, rather than worked around.
	var resolved: Variant = await api.combat_town(user_id,
		CombatFlow.ACTION_RESOLVE, IDENTITY_WITH_NO_ROWS)
	check(resolved is CombatFlow.CombatResult and not resolved.ok,
		"a resolve against the committed corpus is refused, because the corpus "
			+ "places no unit row at all")
	if resolved is CombatFlow.CombatResult:
		check_eq(resolved.error_code, CombatFlow.REASON_NO_ELIGIBLE_ROW,
			"with the eligibility code, not the client-dictated one")
		check_eq(resolved.destruction_count, 0,
			"and a refused intent carries NO partial payload")
		check_eq((resolved.ledger_after as Array).size(), 0,
			"and no ledger entries at all")
		check_eq(resolved.resources, null,
			"and NO resource projection at all, because a refused intent reaches "
				+ "no post-execution proof: there is no 'unchanged' to report")
	# The double is LEFT IN THE TREE, exactly as `test_tutorial.gd` and
	# `test_stored_item_placement.gd` do. Detaching it instead would leave an
	# unparented Node live at exit, which emits the ObjectDB-leak and
	# "1 resources still in use" lines that `verify-boot.ps1`'s `^ERROR:` guard
	# reads as a script error even though the suite exits 0.

	_check_parse_refusals()


## Every `parse_combat()` refusal, over crafted in-memory payloads.
func _check_parse_refusals() -> void:
	info("--- typed parser refusals ---")
	var accepting := _accepting_payload(CombatFlow.ACTION_RESOLVE, 1034,
		ORDER_RECORDED_FIRST)
	var parsed := CombatFlow.parse_combat(accepting)
	check(bool(parsed.ok),
		"a well-formed accepted payload parses: %s" % str(parsed.error_message))
	if not parsed.ok:
		return
	_check_typed_result(parsed)

	var refusals := {
		"not an object": "not json",
		"a bare array": [1, 2, 3],
		"a bare literal": null,
		"not ok": _mutate(accepting, {"ok": false}),
		"the wrong protocol": _mutate(accepting, {"protocol": "other"}),
		"a failed result": _mutate(accepting, {"result": "error"}),
		"an undelivered action": _mutate(accepting, {"action": "nope"}),
		"a command the action does not dispatch":
			_mutate(accepting, {"command": CombatFlow.KILL_COMMAND}),
		"no addressing object": _mutate(accepting, {"addressing": 7}),
		"addressing under the wrong key": _mutate(accepting,
			{"addressing": {"key": "map_key", "value": 1034,
				"kind": "k", "note": "n"}}),
		"no destruction object": _mutate(accepting, {"destruction": "none"}),
		"a destruction that is not marked derived": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"derived": false})}),
		"a client-chosen count": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"count": 4})}),
		"a negative count": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"count": -1})}),
		"a count that is not a number": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"count": "two"})}),
		"no eligible set": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"eligible_keys": null})}),
		"an eligible count that disagrees": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"eligible_count": 99})}),
		"no recorded refusal": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"refused_count": ""})}),
		"no recorded reading of the printed count": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"printed_count_is_request": ""})}),
		"a derived key outside the eligible set": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"derived_key": "9999"})}),
		"a derived row that is not eight slots": _mutate(accepting,
			{"destruction": _mutate(accepting["destruction"] as Dictionary,
				{"derived_row": [1, 2]})}),
		"no ledger before": _mutate(accepting, {"ledger_before": {}}),
		"an unreadable ledger after": _mutate(accepting, {"ledger_after": "x"}),
		"a ledger entry with no item id": _mutate(accepting,
			{"ledger_before": [{"count": 1}]}),
		"no ledger_written statement": _mutate(accepting, {"ledger_written": "yes"}),
		"no evaluated gates": _mutate(accepting, {"ledger_gates": []}),
		"a ledger write behind a declined gate": _mutate(accepting,
			{"ledger_written": true,
				"ledger_gates": {"player_team_one": {"holds": false},
					"resurrectable_positive": {"holds": false}}}),
		"a ledger write with only one gate record": _mutate(accepting,
			{"ledger_written": true,
				"ledger_gates": {"player_team_one": {"holds": true}}}),
		"the wrong number of gates": _mutate(accepting,
			{"gates": UnitBehaviors.gates().slice(0, 1)}),
		"a gate with no source line": _mutate(accepting,
			{"gates": [{"source": ""}]}),
		"no recorded third-gate absence": _mutate(accepting, {"no_third_gate": ""}),
		"no recorded team asymmetry": _mutate(accepting, {"team_asymmetry": {}}),
		"no recorded ordering rule": _mutate(accepting, {"ordering_rule": ""}),
		"the wrong number of validation steps": _mutate(accepting,
			{"validation_order": (accepting["validation_order"] as Array)
				.slice(0, 3)}),
		"a validation step that disagrees": _mutate(accepting,
			{"validation_order": _mutate_step(accepting)}),
		"a validation step that is not an object": _mutate(accepting,
			{"validation_order": _mutate_all_steps(accepting, "step")}),
		"no field inventory": _mutate(accepting, {"field_inventory": {}}),
		"an unknown fate vocabulary": _mutate(accepting,
			{"field_inventory": _mutate(accepting["field_inventory"] as Dictionary,
				{"fates": ["discarded", "print_only"]})}),
		"a reordered fate vocabulary": _mutate(accepting,
			{"field_inventory": _mutate(accepting["field_inventory"] as Dictionary,
				{"fates": ["print_only", "discarded", "mutation_path"]})}),
		"an inventory naming no keys": _mutate(accepting,
			{"field_inventory": _mutate(accepting["field_inventory"] as Dictionary,
				{"keys": []})}),
		"an inventory that does not partition": _mutate(accepting,
			{"field_inventory": _mutate(accepting["field_inventory"] as Dictionary,
				{"partition": false})}),
		"no recorded correction": _mutate(accepting, {"correction": {"a": 1}}),
		"no recorded divergence": _mutate(accepting, {"divergence": {}}),
		"a divergence reported as parity": _mutate(accepting,
			{"divergence": {"status": "parity"}}),
		"the wrong number of refusals": _mutate(accepting, {"refusals": []}),
		"one recorded no-* statement missing": _mutate(accepting,
			{"no_combat": ""}),
		"no kill contract on a kill response": _mutate(
			_accepting_payload(CombatFlow.ACTION_KILL, 40, "40"),
			{"kill_contract": null}),
		"no no-op contract on the item-keyed kill": _mutate(
			_accepting_payload(CombatFlow.ACTION_KILL_IID, 1034, ""),
			{"kill_iid_contract": null}),
		"a no-op contract that no longer says it writes nothing": _mutate(
			_accepting_payload(CombatFlow.ACTION_KILL_IID, 1034, ""),
			{"kill_iid_contract": {"statement_writes_save_state": true}}),
		"no non-claims": _mutate(accepting, {"non_claims": []}),
		"no provenance": _mutate(accepting, {"provenance": {}}),
		"no changed-pointer list": _mutate(accepting, {"changed": "none"}),
		"no resources": _mutate(accepting, {"resources": null}),
		"resources that are not seven integers": _mutate(accepting,
			{"resources": {"xp": "many"}}),
		"a server_time that is not a number": _mutate(accepting,
			{"server_time": "now"}),
	}
	for label: String in refusals.keys():
		var got := CombatFlow.parse_combat(refusals[label])
		check(not bool(got.ok), "%s is refused rather than accepted" % label)
		check(str(got.error_code) != "", "%s is refused with a named code" % label)
		check(str(got.error_message) != "", "%s explains the refusal" % label)
		check_eq(got.destruction_count, 0,
			"%s carries NO partial payload" % label)

	# The two zero-destruction responses the service really sends, which the
	# earlier reading of the guard refused: nothing destroyed names nothing.
	var no_op_payload := _accepting_payload(CombatFlow.ACTION_KILL_IID, 1034, "")
	var no_op := CombatFlow.parse_combat(no_op_payload)
	check(bool(no_op.ok),
		"the proven no-op parses: %s" % str(no_op.error_message))
	if no_op.ok:
		check_eq(no_op.destruction_count, 0, "with a destruction count of zero")
		check_eq(str(no_op.derived_key), "", "and no derived key")
		check_eq(no_op.derived_row.size(), 0, "and no derived row")
	var named_nothing := CombatFlow.parse_combat(_mutate(no_op_payload,
		{"destruction": _mutate(no_op_payload["destruction"] as Dictionary,
			{"derived_key": "1", "derived_row": [0, 0, 0, 0, 0, [], {}, 1],
				"count": 0})}))
	check(not bool(named_nothing.ok),
		"but a response destroying nothing and naming a row is still refused")


## Every recorded field of one accepted typed result.
func _check_typed_result(result: CombatFlow.CombatResult) -> void:
	check_eq(str(result.protocol), BootData.PROTOCOL, "the protocol is compat-v0")
	check_eq(str(result.result), "success", "the legacy result is success")
	check_eq(result.addressing_value, 1034, "the addressing value is the identity")
	check_eq(str(result.addressing_kind), str(
		(CombatFlow.ACTION_ADDRESSING as Dictionary)[CombatFlow.ACTION_RESOLVE]),
		"and its kind is described in words, not only as a key")
	check(str(result.addressing_note) != "", "and carries the recorded note")
	check_eq(result.eligible_count, 3, "the eligible count travels with the answer")
	check_eq(result.eligible_keys, ["2425", "897", "1022"],
		"and so does the whole derived set, in recorded order")
	check_eq(int(result.eligible_count), result.eligible_keys.size(),
		"and the two agree")
	check_eq(result.rows_before, 4, "the placement count before is reported")
	check_eq(result.rows_after, 3, "and after")
	check(str(result.destruction_order) != "",
		"the order the derived destruction took is reported, not merely implied")
	check(result.proof_halves.size() == 4,
		"the four proof halves travel with the answer")
	check_eq(str(result.ordering_rule), CombatFlow.ORDERING_RULE,
		"and the recorded ordering rule travels with it")
	check_eq(str(result.no_third_gate), UnitBehaviors.NO_THIRD_GATE,
		"the delegated no-third-gate statement is the one that capability owns")
	check_eq(str(result.no_syringe_cost), UnitBehaviors.NO_SYRINGE_COST,
		"and the delegated no-syringe-cost statement is that capability's too")
	check_eq(result.gates.size(), UnitBehaviors.GATE_COUNT,
		"both ledger gates travel with the answer")
	check_eq(result.ledger_gates.size(), 2,
		"and both evaluated gate records do too")
	check_eq(bool(result.ledger_gates.get("player_team_one", {}).get("holds",
			false)), true,
		"the team gate is reported as holding")
	check_eq(bool(result.ledger_gates.get("resurrectable_positive", {})
		.get("holds", false)), true, "and so is the committed-flag gate")
	check_eq(int(result.ledger_written), 1,
		"the ledger is written once, behind both gates")
	check_eq(result.ledger_after.size(), 1, "and the derived entry is reported")
	check_eq(str((result.ledger_after[0] as Dictionary).get("item_id", "")), "1034",
		"under the destroyed identity")
	check_eq(int((result.ledger_after[0] as Dictionary).get("count", -1)), 1,
		"with the derived count, not the legacy printed one")
	check_eq(str(result.correction.get("field_inventory", {}).get(
			"key_absent_from_the_recorded_table", "")), "voluntary_end",
		"the field-inventory correction travels with the answer")
	check_eq(int(result.correction.get("corpus", {}).get("measured_documents", 0)),
		EXPECTED_DOCUMENTS, "and so does the measured corpus figure")
	check_eq(result.non_claims.size(), CombatFlow.NON_CLAIM_COUNT,
		"all %d recorded non-claims travel with the answer" % CombatFlow.NON_CLAIM_COUNT)
	for claim: Variant in result.non_claims:
		check(str(claim) != "", "every non-claim is non-empty")
	check((result.non_claims[0] as String).contains("no Flash"),
		"and the first records that no Flash runtime executes")


# ---------------------------------------------------------------------------
# The structural and anti-invention guards
# ---------------------------------------------------------------------------


## The whole static-function inventory, the absent helpers, the arithmetic
## figures, the provenance guards, and the suite's own non-transcription.
func _check_provenance() -> void:
	info("--- structural and provenance guards ---")
	var source := _module_code()
	check(source != "", "the delivered module's code is readable and non-empty")

	# 1. The whole static-function inventory, both directions AND in order.
	var declared: Array = []
	for line: String in source.split("\n"):
		var trimmed := line.strip_edges()
		if trimmed.begins_with("static func "):
			declared.append(trimmed.substr(12, trimmed.find("(") - 12))
	var pinned: Array = CombatFlow.STATIC_FUNCTIONS
	check_eq(declared.size(), pinned.size(),
		"the module declares exactly the pinned number of static functions")
	check_eq(declared, pinned,
		"and its inventory matches the pin exactly, IN SOURCE ORDER, so a "
			+ "reordering cannot hide a helper")
	for name: String in pinned:
		check(declared.has(name), "the pinned static function %s exists" % name)
	for name: String in declared:
		check(pinned.has(name), "the declared static function %s is pinned" % name)

	# 2. No instance function: the module is pure and stateless.
	var instance_functions: Array = []
	for line: String in source.split("\n"):
		var trimmed := line.strip_edges()
		if trimmed.begins_with("func "):
			instance_functions.append(trimmed.substr(5, trimmed.find("(") - 5))
	check_eq(instance_functions.size(), 0,
		"the module declares no instance function")

	# 3. No absent helper, under its own name or any substring of it.
	var absent_hits := 0
	for entry: Variant in CombatFlow.ABSENT_HELPERS:
		var name := str((entry as Dictionary).get("helper", ""))
		check(str((entry as Dictionary).get("absent_because", "")) != "",
			"the absent helper %s states why it is absent" % name)
		if _count_occurrences(source, name) > 0:
			absent_hits += 1
			fail("the absent helper %s does not exist" % name)
	check_eq(absent_hits, 0,
		"none of the %d recorded absent helpers exists under any spelling"
			% CombatFlow.ABSENT_HELPERS.size())

	# 4. The arithmetic figures, counted rather than asserted.
	#
	# Measured over the quotes-blanked view, so an operator inside a recorded
	# sentence is not counted as an operation; the modulo figure is measured
	# separately over the quotes-kept view, because telling a format `%` from a
	# modulo needs the quote character that surrounds the former.
	var record: Dictionary = CombatFlow.ARITHMETIC_RECORD
	var literal_view := _code_quotes_kept(_module_source())
	var measured := _measured_arithmetic(source, literal_view)
	for field: String in measured.keys():
		check_eq(int(measured[field]), int(record.get(field, -1)),
			"the %s figure is %d, as recorded"
				% [field, int(record.get(field, -1))])
		check_eq(int(measured[field]), 0,
			"the module contains no %s at all" % field)

	# 5. The additive operand set is EQUAL to the published inventory, in both
	# directions.
	#
	# The rule this replaces required every additive line to name one of twelve
	# bookkeeping tokens, and measurement falsified it: 20 of the 31 binary
	# additive lines name none of the twelve, because the module's additions are
	# over strings, arrays and path fragments rather than over line indices. The
	# twelve-token list is retained in the module as a superseded record and gates
	# nothing.
	#
	# The replacement is strictly stronger, because a published inventory is an
	# EQUALITY rather than a lower bound. A new sum over a committed value
	# introduces an identifier, the measurement finds it, and the set comparison
	# fails. A stale entry here fails in the other direction.
	var additive_lines := _binary_additive_lines(literal_view)
	check_eq(int(record.get("binary_additive_lines", -1)), additive_lines.size(),
		"the recorded binary-additive line count is %d, as measured"
			% additive_lines.size())
	var measured_operands := _additive_operands(additive_lines)
	var published: Array = CombatFlow.ADDITIVE_OPERANDS
	var missing: Array = []
	for name: Variant in measured_operands:
		if not (name in published):
			missing.append(name)
			fail("a binary additive line names an unpublished operand: %s"
				% str(name))
	check_eq(missing.size(), 0,
		"every identifier on a binary additive line is one of the %d published "
			% published.size()
			+ "operands, so new arithmetic fails the suite")
	var stale: Array = []
	for name: Variant in published:
		if not (name in measured_operands):
			stale.append(name)
			fail("a published additive operand was not measured this run: %s"
				% str(name))
	check_eq(stale.size(), 0,
		"and every published operand really occurs, so the inventory cannot rot "
			+ "silently")
	check_eq(measured_operands.size(), published.size(),
		"the two sets are equal in size as well as in membership")
	# The claim that matters is not the inventory's shape but its content: no
	# committed combat field appears on any additive line, and this check does not
	# consult the inventory at all.
	var combat_operands := 0
	for name: Variant in measured_operands:
		if str(name) in COMBAT_FIELD_NAMES:
			combat_operands += 1
			fail("a binary additive line names the committed field %s"
				% str(name))
	check_eq(combat_operands, 0,
		"and none of the %d measured operands is a committed combat field, which "
			% COMBAT_FIELD_NAMES.size()
			+ "is the no-derivation claim and does not rest on the inventory")
	check_eq(int(record.get(
		"committed_combat_field_hits_on_additive_lines", -1)), 0,
		"the module records the same zero")
	check_eq((record.get("additive_operands", []) as Array),
		CombatFlow.ADDITIVE_OPERANDS,
		"and the recorded operand list is the published one")

	# 6. Every `%` is a string format, never modulo over a number.
	check_eq(_count_non_format_modulo(literal_view), 0,
		"every `%` in the module is a string format, never modulo over a number")

	# 7. No line compares one committed value against another.
	#
	# Measured over the **literals-kept** view, and that is a CORRECTION, not a
	# preference. This check first iterated `literal_view`, whose string-literal
	# CONTENTS the one lexer blanks, so a quoted committed field name could never
	# survive into it and the condition was **vacuously true** for every module
	# that could ever be written. It was found by INJECTION rather than by
	# reading: an appended line returning `"attack" == "defense"` failed only
	# the static-inventory guard and this one passed in silence. Comments are
	# still blanked, so a sentence that merely NAMES a field cannot match, and
	# requiring **two** quoted field names is what the sentence above claims.
	var value_comparisons := 0
	var compare_view := _code_only_keep_strings(_module_source())
	for line: String in compare_view.split("\n"):
		if not _has_comparison(line):
			continue
		var named_fields := 0
		for field: String in ["attack", "defense", "life", "resurrectable",
				"syringes", "clicks_to_build"]:
			if line.contains('"%s"' % field):
				named_fields += 1
		if named_fields >= 2:
			value_comparisons += 1
			fail("a delivered line compares a committed combat field: %s"
				% line.strip_edges())
	check_eq(value_comparisons, 0,
		"no delivered line compares one committed combat value against another")

	# 8. Purity: the projection gained no node, clock, request, or transport.
	# Measured over the quotes-kept view, because two of the recorded needles are
	# themselves URL and class names that can only ever appear as literals.
	for needle: String in PURITY_NEEDLES:
		check_eq(_count_occurrences(literal_view, needle), 0,
			"the module carries no %s" % needle)

	# 9. The suite TRANSCRIBES NO KEY of the inventory.
	#
	# The blanket "no key name in code" guard is impossible here and the reason
	# is worth recording: eleven of the twelve derived key names occur zero times
	# in the module's own code view, but `resources` matches five legitimate
	# locals holding the seven-resource projection. So the guard scans THIS
	# SUITE's source instead, with string contents blanked, where the only
	# legitimate occurrence is that same projection helper's own name, and the
	# single exclusion is pinned so it cannot be widened silently.
	var inventory: Dictionary = CombatFlow.derive_field_inventory()
	var suite_code := _suite_code()
	var transcribed := 0
	for key: Variant in inventory.get("key_names", []) as Array:
		var name := str(key)
		if SUITE_KEY_EXCLUSION.has(name):
			continue
		var hits := _count_occurrences(suite_code, name)
		if hits > 0:
			transcribed += hits
			fail("the suite's own code carries the derived key name %s" % name)
	check_eq(transcribed, 0,
		"this suite transcribes none of the %d derived key names, so the "
			% (inventory.get("key_names", []) as Array).size()
			+ "second extraction cannot be agreeing with a table")
	check_eq(SUITE_KEY_EXCLUSION, ["resources"],
		"and the one excluded name is exactly the seven-resource projection "
			+ "local, pinned so the exclusion cannot grow")
	var excluded_hits := _count_occurrences(suite_code, "resources")
	check(excluded_hits > 0,
		"the excluded name really does occur here, so the exclusion is honest "
			+ "rather than unused")


## The boundary this line draws around the mission capability and the legacy
## units it delegates to, plus the whole-client scan for an invented rule.
func _check_boundary() -> void:
	info("--- ownership and the no-invention boundary ---")

	# Mission vocabulary is owned elsewhere and this line references no field.
	#
	# Scanned with string **contents** blanked: the module records the very
	# string `MISSION_` inside its own non-claim, and a substring inside that
	# sentence is not a field reference. What must be absent is the token as
	# code.
	#
	# The scan is **scoped**, and the scope is stated rather than widened to the
	# whole tree. `fake_api.gd` is the shared offline double for EVERY delivered
	# line, and it legitimately hosts the mission-vocabulary double delivered by
	# the M10 line before this one; a whole-file scan therefore fails on a
	# neighbour's legitimately delivered code and says nothing about combat. So
	# the module is scanned whole -- it is this line's own file -- while the two
	# transports are scanned only inside their **combat function**, and the
	# function must actually have been located or the check is void.
	var mission_refs := 0
	for body: String in [
		_code_only(_project_source("scripts/units/combat_flow.gd")),
		_code_only(_function_body(
			Paths.project_dir().path_join(LEGACY_V0_PATH),
			"var intent := CombatFlow.build_intent(")),
		_code_only(_function_body(
			Paths.project_dir().path_join("scripts/gameapi/fake_api.gd"),
			"CombatFlow.build_intent(")),
	]:
		if body.is_empty():
			fail("a combat transport function was not located, so the mission "
				+ "reference scan is void")
			continue
		if body.contains("MISSION_"):
			mission_refs += 1
			fail("a delivered combat source references a mission field")
	check_eq(mission_refs, 0,
		"no delivered combat source references a MISSION_ field")
	var owner := Paths.project_dir().path_join(
		"scripts/missions/mission_vocabulary.gd")
	check(FileAccess.file_exists(owner),
		"and the owning mission-vocabulary capability exists, so the boundary is "
			+ "a hand-off and not an orphan")
	check(str(CombatFlow.PROVENANCE.get("mission_vocabulary_owner", "")) ==
			"godot-mission-vocabulary",
		"and the provenance names that owner")

	# The ledger is delegated whole, never reimplemented.
	var delegated := 0
	for helper: String in ["project_ledger", "committed_resurrectable"]:
		check(_module_code().contains("UnitBehaviors." + helper)
				or _module_code().contains("UnitBehaviors." + helper + "("),
			"the %s helper is delegated to unit_behaviors.gd" % helper)
		delegated += 1
	check_eq(delegated, 2,
		"the ledger projection and the committed-flag read are both delegated")
	var own_increment := 0
	for line: String in _module_code().split("\n"):
		if line.contains("UnitBehaviors.expected_increment("):
			own_increment += 1
	check(own_increment >= 1,
		"and the increment itself is called, never written out a second time")
	check(not _module_code().contains("UnitBehaviors.expected_increment({"),
		"with no literal ledger argument invented beside the call")

	# The whole client tree, scanned for an invented combat rule. The needles
	# are fragments for the same project-scope reason as the delivered modules,
	# and each source is read with string contents blanked, because the refusal
	# suites themselves RECORD every one of these names as an absent helper --
	# a name inside that record is not a mechanism.
	var offenders: Array = []
	var sources := _client_sources()
	var per_needle := {}
	for needle: String in NEEDLES:
		per_needle[needle] = 0
	for relative: String in sources:
		var code := _code_only(_project_source(relative))
		for needle: String in NEEDLES:
			var hits := _count_occurrences(code, needle)
			if hits > 0:
				per_needle[needle] = int(per_needle[needle]) + hits
	for needle: String in NEEDLES:
		if int(per_needle[needle]) > 0:
			offenders.append({"needle": needle,
				"occurrences": int(per_needle[needle])})
	check_eq(offenders.size(), 0,
		"no client source anywhere derives a damage, duration, honour, reward, or "
			+ "mission rule (scanned over %d source files)"
			% sources.size())
	for entry: Variant in offenders:
		fail("an invented mechanism was found: %s"
			% str((entry as Dictionary).get("needle", "")))

	# The provenance block itself.
	var provenance: Dictionary = CombatFlow.PROVENANCE
	for field: String in ["capability", "milestone", "legacy_source",
			"combat_branch", "kill_branch", "kill_iid_branch",
			"row_removal_helper", "ledger_helper", "ledger_owner"]:
		check(str(provenance.get(field, "")) != "",
			"the provenance records %s" % field)
	check_eq(str(provenance.get("capability", "")), "godot-combat-actions",
		"the capability name is this one")
	check(str(provenance.get("interpretation", "")).contains("RE-DERIVED"),
		"and the interpretation states that nothing is transcribed")


# ---------------------------------------------------------------------------
# The live phase
# ---------------------------------------------------------------------------


## `--scenario=live-combat`: the real endpoint, over loopback, on a disposable
## corpus the phase is given.
##
## The live corpus is always seeded from `tests/saves/fresh-player.json`, which
## places **zero** unit rows, so `resolve` cannot be positive here and the phase
## asserts its REFUSAL instead. The destruction is proved through `kill` on a
## real placed row, which is the one combat action this corpus can exercise.
func _check_live_combat() -> void:
	info("--- live combat phase ---")
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
	check(not before.is_empty(), "the live corpus bootstrap resolves")
	if before.is_empty():
		return
	var items_before: Dictionary = (before.get("map", {}) as Dictionary) \
		.get("items", {}) as Dictionary
	var resources_before := _live_resources(before)
	check_eq(items_before.size(), 40,
		"the live corpus places the committed 40 rows")
	var unit_rows := 0
	for key: Variant in items_before.keys():
		var row: Variant = items_before[key]
		if row is Array and _domain_of(str(int((row as Array)[0]))) == "units":
			unit_rows += 1
	check_eq(unit_rows, 0,
		"and ZERO of them is a committed unit, so a resolve cannot be positive "
			+ "against it: this corpus limitation is asserted, not worked around")
	check_eq(_live_ledger_size(before), 0,
		"and the live ledger is empty, as the committed corpus's is")

	var target := _committed_row_map_key(items_before, DOUBLE_ITEM_ID)
	check(target > 0,
		"a placed row carrying item id %d is located in the live corpus"
			% DOUBLE_ITEM_ID)
	var killed: Variant = await api.combat_town(user_id, CombatFlow.ACTION_KILL,
		target)
	check(killed is CombatFlow.CombatResult and killed.ok,
		"the REAL endpoint removes the addressed row: %s"
			% (killed.error_message if not killed.ok else ""))
	if not (killed is CombatFlow.CombatResult and killed.ok):
		return
	var typed: CombatFlow.CombatResult = killed
	check_eq(typed.destruction_count, 1,
		"and reports exactly one server-derived destruction")
	check_eq(str(typed.derived_key), str(target),
		"of the row it addressed")
	check_eq(bool(typed.ledger_written), false,
		"and writes no ledger entry, because the kill branch never reaches one")
	_check_typed_result_shape(typed)

	# The same intent through the OFFLINE double: both implementations, one shape.
	api.configure("fake")
	var offline: Variant = await api.combat_town(user_id, CombatFlow.ACTION_KILL,
		DOUBLE_MAP_KEY)
	check(offline is CombatFlow.CombatResult and offline.ok,
		"the offline double accepts the same intent with no process or socket")
	if offline is CombatFlow.CombatResult and offline.ok:
		check_eq((offline as CombatFlow.CombatResult).destruction_count, 1,
			"and derives the same destruction count")
		check_eq(str((offline as CombatFlow.CombatResult).derived_key),
			str(DOUBLE_MAP_KEY), "of the row IT addressed")

	# The refusal the live corpus genuinely reaches, and its code.
	api.configure("legacy_v0", endpoint)
	var refused: Variant = await api.combat_town(user_id,
		CombatFlow.ACTION_RESOLVE, IDENTITY_WITH_NO_ROWS)
	check(refused is CombatFlow.CombatResult and not refused.ok,
		"a resolve against a corpus with no unit row is refused by the REAL "
			+ "endpoint")
	if refused is CombatFlow.CombatResult:
		check_eq(refused.error_code, CombatFlow.REASON_NO_ELIGIBLE_ROW,
			"with the endpoint's own eligibility code, not the client-dictated one")
		check_eq(refused.destruction_count, 0,
			"and NO partial payload")

	# The client-dictated refusal, which the delivered transport cannot express,
	# so the live phase proves it by asking the shared module directly and
	# asserting the answer's own name.
	var dictation := CombatFlow.refused_client_keys({"lost": 2, "survived": 1})
	check_eq(dictation, ["lost", "survived"],
		"a client-sent casualty figure is refused by name before any dispatch")
	check(dictation != [CombatFlow.REASON_NO_ELIGIBLE_ROW],
		"and that name is not the eligibility one, which is the whole point of "
			+ "design D2")

	# The live corpus AFTER: exactly the addressed row is gone, and nothing else
	# moved. This is the value-level proof, read from the SERVICE's own state.
	var after: Dictionary = await _live_payload(api, endpoint, user_id)
	var items_after: Dictionary = (after.get("map", {}) as Dictionary) \
		.get("items", {}) as Dictionary
	check_eq(items_after.has(str(target)), false,
		"the addressed row is GONE from the live corpus")
	var differing: Array = []
	for key: Variant in items_before.keys():
		if str(key) == str(target):
			continue
		if _normalize(items_after.get(key)) != _normalize(items_before[key]):
			differing.append(str(key))
	check_eq(differing, [],
		"and EVERY other row is byte-identical, which is proof half one as a "
			+ "whole-map value comparison")
	check_eq(items_after.size(), items_before.size() - 1,
		"and the row count fell by exactly the derived destruction")
	check_eq(_live_ledger_size(after), 0,
		"the live ledger is STILL empty: the kill branch never reached it")
	check_eq(_live_resources(after), resources_before,
		"every live balance is byte-identical, which is proof half three")
	print("[test] live-combat destroyed map_key=%d item_id=%d count=1 "
		% [target, DOUBLE_ITEM_ID]
		+ "ledger_written=false resources_unchanged=true "
		+ "refused=%s,no_eligible_row"
			% CombatFlow.REASON_CLIENT_DICTATED_DESTRUCTION)


## The typed fields the live phase can still assert with its own corpus.
func _check_typed_result_shape(result: CombatFlow.CombatResult) -> void:
	check_eq(str(result.protocol), BootData.PROTOCOL, "the live protocol is compat-v0")
	check_eq(result.action, CombatFlow.ACTION_KILL, "the live action is the kill")
	check_eq(result.command, CombatFlow.KILL_COMMAND, "and the branch it dispatches")
	check_eq(result.addressing_key, "map_key", "under its own addressing key")
	check_eq(bool(result.destruction_derived), true,
		"and its destruction is marked server-derived")
	check_eq(result.derived_row.size(), CombatFlow.MAP_ROW_SLOTS,
		"with the committed eight-slot row reported")
	check_eq(_normalize(result.validation_order).size(),
		CombatFlow.VALIDATION_ORDER_STEPS,
		"the whole validation order travelled with the live answer")
	check_eq(_normalize(result.field_inventory.get("key_names", [])),
		inventory_names(),
		"and so did the re-derived field inventory, not a transcribed one")
	check_eq(result.refusals.size(), CombatFlow.REFUSAL_COUNT,
		"and all %d recorded refusals" % CombatFlow.REFUSAL_COUNT)
	# `int(...)`, NOT `str(...)`: this compared a String against the int 0,
	# which GDScript rejects as invalid operands, so the check RAISED instead
	# of evaluating and never registered a failure -- the live phase reported
	# green with this check silently unrun.  `int` also survives Godot decoding
	# a JSON number as a float, and the `-1` default still fails correctly when
	# the key is absent.  This was the only `str(...)`-versus-int comparison in
	# the repository.
	check_eq(int(result.kill_contract.get("ledger_references", -1)), 0,
		"and the kill contract's zero ledger references")
	check_eq(result.non_claims.size(), CombatFlow.NON_CLAIM_COUNT,
		"and all %d recorded non-claims" % CombatFlow.NON_CLAIM_COUNT)
	check_eq(str(result.team_asymmetry.get("status", "")),
		"RECORDED, NOT EXERCISED, NOT REFUSED",
		"and the recorded team asymmetry, still not exercised")
	check(result.resources is BootData.Resources,
		"and seven parsed stored resources")
	check(_normalize(result.changed) == ["/maps/0/items/%s" % result.derived_key],
		"and a changed-pointer list naming exactly the removed row")


# ---------------------------------------------------------------------------
# Containment
# ---------------------------------------------------------------------------


## Nothing this line reads was written, which is checked with a digest taken
## before the run and compared after it.
func _check_containment(package_before: Dictionary, villages_before: Dictionary,
		corpus_before: Dictionary, fixtures_before: Dictionary,
		legacy_before: Dictionary) -> void:
	info("--- containment ---")
	for pair: Array in [
		["the content package", "packages/game-content", package_before],
		["the committed village documents", VILLAGE_DIR, villages_before],
		["the committed corpus saves", SAVES_DIR, corpus_before],
		["the committed fixtures", "tests/fixtures", fixtures_before],
	]:
		var after := Paths.directory_digest(Paths.repo_root().path_join(
			str(pair[1])))
		check_eq(str((after as Dictionary).get("sha256", "")),
			str((pair[2] as Dictionary).get("sha256", "")),
			"%s is byte-identical after the run" % str(pair[0]))
	check_eq(str(_legacy_digest().get("sha256", "")),
		str(legacy_before.get("sha256", "")),
		"the legacy root modules are byte-identical after the run")

	# The committed parity fixture is present and re-readable, since the report
	# points at it.
	check(FileAccess.file_exists(Paths.repo_root().path_join(
			FIXTURE_PATH + "/capture-manifest.json")),
		"the committed executed-legacy combat fixture is present")
	check(FileAccess.file_exists(
			Paths.repo_root().path_join(PARITY_SUITE)),
		"and the Python parity replay suite is present")


# ---------------------------------------------------------------------------
# Lexing and measurement helpers
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


## The live payload's seven stored balances, read from the SERVICE's own state.
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


## The live payload's own ledger, verbatim.
func _live_ledger(payload: Dictionary) -> Variant:
	var priv: Dictionary = payload.get("privateState", {}) as Dictionary
	return priv.get(CombatFlow.LEDGER_KEY, null)


## The live ledger's recorded entry COUNT, failing closed to -1 when the
## payload carries no ledger at all. The committed corpus records
## privateState.deadHeroes as an empty Dictionary, so the emptiness check
## compares a count rather than the ledger itself: a Dictionary is never
## compared against an Array literal, and a typed operand mismatch aborts
## the function, which would silently skip every later check in the phase.
func _live_ledger_size(payload: Dictionary) -> int:
	var ledger: Variant = _live_ledger(payload)
	if not (ledger is Dictionary):
		return -1
	return (ledger as Dictionary).size()


## The committed corpus's seven stored balances.
func _corpus_resources(relative: String) -> Dictionary:
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(
		Paths.repo_root().path_join(relative)))
	if not (document is Dictionary):
		return {}
	var maps: Variant = (document as Dictionary).get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return {}
	var first: Dictionary = (maps as Array)[0] as Dictionary
	var player: Dictionary = (document as Dictionary).get("playerInfo", {}) \
		as Dictionary
	var priv: Dictionary = (document as Dictionary).get("privateState", {}) \
		as Dictionary
	return {
		"xp": int(first.get("xp", 0)),
		"gold": int(first.get("gold", 0)),
		"wood": int(first.get("wood", 0)),
		"oil": int(first.get("oil", 0)),
		"steel": int(first.get("steel", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(priv.get("mana", 0)),
	}


## One committed corpus row's item id, by map key, or -1.
func _corpus_row_item(relative: String, map_key: int) -> int:
	var items := _committed_items(relative)
	var row: Variant = items.get(str(map_key))
	if not (row is Array) or (row as Array).size() != CombatFlow.MAP_ROW_SLOTS:
		return -1
	return int((row as Array)[0])


## The map key of the first placed row carrying `item_id`, or -1.
func _committed_row_map_key(items: Dictionary, item_id: int) -> int:
	for key: Variant in items.keys():
		var row: Variant = items[key]
		if row is Array and (row as Array).size() == CombatFlow.MAP_ROW_SLOTS \
				and int((row as Array)[0]) == item_id:
			return int(key)
	return -1


## One committed save document's first placement map, or {}.
func _committed_items(relative: String) -> Dictionary:
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(
		Paths.repo_root().path_join(relative)))
	if not (document is Dictionary):
		return {}
	var maps: Variant = (document as Dictionary).get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		return {}
	var items: Variant = ((maps as Array)[0] as Dictionary).get("items")
	if not (items is Dictionary):
		return {}
	return items


## Every committed save document, repository-relative and sorted, with the two
## exclusions measured rather than assumed.
func _committed_documents() -> Array:
	var out: Array = []
	for directory: String in [VILLAGE_DIR, SAVES_DIR]:
		var absolute := Paths.repo_root().path_join(directory)
		for name: String in DirAccess.get_files_at(absolute):
			if not name.ends_with(".json"):
				continue
			if EXCLUDED_SAVE_DOCUMENTS.has(name):
				continue
			var relative := directory + "/" + name
			# `villages/quest/` holds quest documents of a different shape, and
			# `get_files_at` is non-recursive, so the check below is a guard
			# rather than a filter: every listed document must carry a map.
			if JSON.parse_string(FileAccess.get_file_as_string(
					Paths.repo_root().path_join(relative))) == null:
				continue
			out.append(relative)
	out.sort()
	return out


## One committed save document's placement and ledger figures.
func _census_document(relative: String) -> Dictionary:
	var out := {
		"ok": false, "document": relative, "placed_rows": 0, "unit_rows": 0,
		"unit_rows_on_team_one": 0, "unit_rows_resurrectable": 0, "ledger_keys": 0,
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
	var ledger: Variant = (priv as Dictionary).get(CombatFlow.LEDGER_KEY) \
		if priv is Dictionary else null
	out["ledger_keys"] = (ledger as Dictionary).size() if ledger is Dictionary \
		else 0
	for key: Variant in (items as Dictionary).keys():
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != CombatFlow.MAP_ROW_SLOTS:
			continue
		out["placed_rows"] = int(out["placed_rows"]) + 1
		var item_id := str(int((row as Array)[0]))
		if _domain_of(item_id) != "units":
			continue
		out["unit_rows"] = int(out["unit_rows"]) + 1
		if UnitBehaviors.passes_team_gate((row as Array)[7]):
			out["unit_rows_on_team_one"] = int(out["unit_rows_on_team_one"]) + 1
		var entry: Dictionary = _registry_entry("units", item_id)
		var flag: Variant = UnitBehaviors.committed_resurrectable(
			entry.get(UnitBehaviors.PROPERTIES_FIELD))
		if UnitBehaviors.passes_resurrectable_gate(flag):
			out["unit_rows_resurrectable"] = int(out["unit_rows_resurrectable"]) + 1
	out["ok"] = true
	return out


## One committed item id's domain, by the registry's own resolution.
func _domain_of(item_id: String) -> String:
	if _registry == null:
		return ""
	for domain: String in ["units", "buildings"]:
		if bool(_registry.get_entry(domain, item_id).get("found", false)):
			return domain
	return ""


## One committed definition through the verified registry, or {}.
func _registry_entry(domain: String, item_id: String) -> Dictionary:
	if _registry == null or domain.is_empty():
		return {}
	var resolved: Dictionary = _registry.get_entry(domain, item_id)
	if not bool(resolved.get("found", false)):
		return {}
	return resolved.get("entry", {}) as Dictionary


## The committed `command.py` text, as bytes.
func _legacy_command_text() -> String:
	return FileAccess.get_file_as_string(
		Paths.repo_root().path_join(LEGACY_COMMAND))


## Whether a recorded `command.py:<line>` really carries a fragment.
func _legacy_line_carries(reference: String, fragment: String) -> bool:
	var parts := str(reference).split(":")
	if parts.size() != 2:
		return false
	var number := int(parts[1])
	var lines := _legacy_command_text().split("\n")
	if number < 1 or number > lines.size():
		return false
	return str(lines[number - 1]).contains(fragment)


## The committed lines of one dispatcher branch, from its opener to just before
## the next opener, or [] when the opener is absent.
##
## `opener` and `next_opener` are the `cmd == "<name>":` test WITHOUT the `if` or
## `elif` keyword. The committed dispatcher opens `kill`, `kill_iid` and
## `batch_remove` with `elif` (command.py:169, :183, :189) while it opens
## `end_attack` the same way, so a keyword-prefixed opener silently matches
## nothing and returns an empty branch — which reads as "the branch was not
## located" rather than as the bug it is.
func _legacy_lines_between(opener: String, next_opener: String) -> Array:
	var lines := _legacy_command_text().split("\n")
	var out: Array = []
	var collecting := false
	for line: Variant in lines:
		var stripped := str(line).strip_edges()
		var keyword := stripped.begins_with("elif ") or stripped.begins_with("if ")
		if collecting and keyword and stripped.contains(next_opener):
			return out
		if keyword and stripped.contains(opener):
			collecting = true
		if collecting:
			out.append(str(line))
	return out


## A digest over the legacy root modules, so containment can prove they were
## only read.
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


## The delivered module's own source, as bytes.
func _module_source() -> String:
	return FileAccess.get_file_as_string(
		Paths.project_dir().path_join(MODULE_PATH))


## Any project-relative source file, as bytes.
func _project_source(relative: String) -> String:
	return FileAccess.get_file_as_string(
		Paths.project_dir().path_join(relative))


## This suite's own source, as bytes.
func _suite_source() -> String:
	var running: Variant = get_script()
	if running == null:
		return ""
	return FileAccess.get_file_as_string(
		Paths.project_dir().path_join(str(running.resource_path).trim_prefix(
			"res://")))


## ONE line-level lexer behind every code view in this suite.
##
## `keep_quotes` and `keep_literals` select the three views the guards need, and
## doing it line by line rather than character by character over the whole file
## is what keeps a whole-client-tree scan affordable: `out += character` over a
## 130 KB source is quadratic, and the tree scan runs it once per file.
##
## The two quote characters are SEPARATE states, so a single quote inside a
## double-quoted string (`attr['nc']`) cannot desynchronise the scan and leave a
## recorded phrase masquerading as a declaration.
func _lex_line(line: String, keep_quotes: bool, keep_literals: bool) -> String:
	var out := ""
	var open := ""
	var index := 0
	while index < line.length():
		var character := line[index]
		if open != "":
			if character == "\\" and index + 1 < line.length():
				out += line.substr(index, 2) if keep_literals else "  "
				index += 2
				continue
			if character == open:
				open = ""
				out += character if (keep_quotes or keep_literals) else " "
				index += 1
				continue
			out += character if keep_literals else " "
			index += 1
			continue
		if character == "\"" or character == "'":
			open = character
			out += character if (keep_quotes or keep_literals) else " "
			index += 1
			continue
		if character == "#":
			while index < line.length():
				out += " "
				index += 1
			break
		out += character
		index += 1
	return out


## Every line of `body` run through the one lexer.
func _lex_source(body: String, keep_quotes: bool,
		keep_literals: bool) -> String:
	var out := PackedStringArray()
	for line: String in body.split("\n"):
		out.append(_lex_line(line, keep_quotes, keep_literals))
	return "\n".join(out)


## Comments blanked; string and character literals blanked INCLUDING their quote
## characters. This is the view for a scan that wants **declarations** and
## **arithmetic operators**: a name recorded inside a sentence is not a
## mechanism, and an operator inside a sentence is not an operation.
func _code_only(body: String) -> String:
	return _lex_source(body, false, false)


## Comments blanked; literal CONTENTS blanked but the quote characters kept.
##
## This is the view for the two operator claims that must tell a binary `+` from
## a concatenation and a format `%` from a modulo: both are told apart by the
## quote character that surrounds them.
func _code_quotes_kept(body: String) -> String:
	return _lex_source(body, true, false)


## Comments blanked; string literals **preserved**. Used only for the committed
## Python, where a client key reaches the code as a JSON key and blanking the
## literal would erase the very name under measurement.
func _code_only_keep_strings(body: String) -> String:
	return _lex_source(body, true, true)


func _module_code() -> String:
	return _code_only(_module_source())


## This suite's own source, comments blanked and string **contents** blanked.
##
## The contents are blanked too, deliberately: a key name that reaches this file
## as a crafted hostile-payload literal is not a transcription of the inventory,
## whereas a key name that reaches it as an identifier or a constant would be.
func _suite_code() -> String:
	return _code_only(_suite_source())


## One committed Python line with its comment removed and its literals kept.
func _python_code(line: String) -> String:
	return _code_only_keep_strings(line)


## Remove an unquoted trailing `#` comment from one Python line.
func _strip_comment(line: String) -> String:
	var quote := ""
	var index := 0
	while index < line.length():
		var character := line[index]
		if quote != "":
			if character == "\\":
				index += 2
				continue
			if character == quote:
				quote = ""
		elif character == "\"" or character == "'":
			quote = character
		elif character == "#":
			return line.substr(0, index)
		index += 1
	return line


## A Python line's own indentation width, the count of leading space characters.
##
## Committed Python indents with spaces only, so tabs are not counted; a line
## with no leading space measures zero, which is what the block rule needs for a
## branch body that is not nested at all.
func _indent_of(line: String) -> int:
	var indentation := 0
	while indentation < line.length() and line[indentation] == " ":
		indentation += 1
	return indentation


## Whether a whole word occurs in a code view.
func _word_occurs(body: String, word: String) -> bool:
	var regex := RegEx.new()
	regex.compile("\\b" + word + "\\b")
	return regex.search(body) != null


## The body of one function, located by a marker and bounded by the next `func`.
##
## The **marker line is included** in the result. It is the line carrying the very
## call the caller is looking for, so dropping it made a body that is found by
## `CombatFlow.build_intent(` unable to report containing it \u2014 a guard that can
## only fail.
func _function_body(absolute: String, marker: String) -> String:
	if not FileAccess.file_exists(absolute):
		return ""
	var lines: Variant = FileAccess.get_file_as_string(absolute).split("\n")
	var out: Array = []
	var collecting := false
	for line: Variant in lines:
		var text := str(line)
		if not collecting and text.contains(marker):
			collecting = true
			out.append(text)
			continue
		if collecting:
			if text.strip_edges().begins_with("func "):
				break
			out.append(text)
	return "\n".join(out)


## Every `.gd` source under the client roots, sorted, so a scan order is
## deterministic.
func _client_sources() -> Array:
	var out: Array = []
	for root: String in ["res://scripts", "res://tests"]:
		_collect_sources(root, out)
	out.sort()
	return out


func _collect_sources(directory: String, out: Array) -> void:
	var handle := DirAccess.open(directory)
	if handle == null:
		return
	handle.list_dir_begin()
	var entry := handle.get_next()
	while entry != "":
		if entry.begins_with("."):
			entry = handle.get_next()
			continue
		var full := directory.path_join(entry)
		if handle.current_is_dir():
			_collect_sources(full, out)
		elif entry.ends_with(".gd"):
			out.append(str(full).trim_prefix("res://"))
		entry = handle.get_next()
	handle.list_dir_end()


## Occurrences of `needle` in `haystack`, counted per occurrence rather than per
## line.
func _count_occurrences(haystack: String, needle: String) -> int:
	if needle.is_empty():
		return 0
	var total := 0
	var index := haystack.find(needle)
	while index >= 0:
		total += 1
		index = haystack.find(needle, index + 1)
	return total


## The counted arithmetic figures, with the longer tokens subtracted so `**` is
## not also counted as a `*`.
##
## `source` is the module's code view, in which string **contents** are already
## blanked and the surrounding quotes are kept. Modulo is counted by its OWN
## helper rather than by subtracting a token count, because `%` survives inside
## the view as the string-format operator and a count is exactly what would
## confuse the two.
func _measured_arithmetic(blanked: String, literal: String) -> Dictionary:
	var out := {}
	for field: String in ARITHMETIC_TOKENS.keys():
		var token: String = ARITHMETIC_TOKENS[field]
		var count := 0
		if token == "%":
			count = _count_non_format_modulo(literal)
		else:
			count = _count_occurrences(blanked, token)
			if token == "*":
				count -= _count_occurrences(blanked, "**")
			if token == "&":
				count -= _count_occurrences(blanked, "&&")
		out[field] = count
	return out


## Every code line carrying a BINARY `+` or `-`.
##
## The view keeps string literals as blanked quotes, so a `+` between two
## literals is a concatenation and not an addition. Such a line is excluded by
## looking at the nearest non-space character on each side: a binary operator
## never abuts a quote, because its operands are values and a string never is
## one. Multi-line continuation lines are excluded by the same test, since their
## leading `+` abuts the literal that ends the previous line.
func _binary_additive_lines(source: String) -> Array:
	var out: Array = []
	for raw: Variant in source.split("\n"):
		var line := str(raw)
		for token: String in ["+", "-"]:
			var index := line.find(token)
			while index >= 0:
				if _additive_is_binary(line, index):
					out.append(line)
					break
				index = line.find(token, index + 1)
	return out


## The sorted identifiers occurring on the given additive lines, keywords and
## numerals excluded.
func _additive_operands(lines: Array) -> Array:
	var names := {}
	var regex := RegEx.new()
	regex.compile("[A-Za-z_][A-Za-z_0-9]*")
	for raw: Variant in lines:
		for hit: Variant in regex.search_all(str(raw)):
			var word: String = hit.get_string()
			if word in GDSCRIPT_KEYWORDS:
				continue
			names[word] = true
	var out: Array = names.keys()
	out.sort()
	return out


## Whether the `+` or `-` at `index` is a BINARY operator.
##
## Four things are excluded and each exclusion is necessary:
## a concatenation, whose operand on one side is a quoted literal; a leading `+`
## on a continuation line, whose left operand is on the previous line; a UNARY
## sign, which has nothing but whitespace and its operand to its left; and the
## `-` of a `->` return-type annotation, which is not an operator at all.
func _additive_is_binary(line: String, index: int) -> bool:
	var before := _nearest_code_character(line, index - 1, -1)
	var after := _nearest_code_character(line, index + 1, 1)
	if before == ">" and _nearest_code_character(line, index - 2, -1) == "-":
		return false
	if before in ["", ":", "=", "(", "[", "{", ",", "+", "-", "*", "/",
			"%", "&", "|", "!", "<", ">", ";"]:
		return false
	if after in ["", ":", "=", ")", "]", "}", ",", "+", "-", "*", "/",
			"%", "&", "|", "!", "<", ">", ";"]:
		return false
	return true


## The nearest character at or before/after `from`, skipping spaces and tabs, or
## "" when there is none.
func _nearest_code_character(line: String, from: int, step: int) -> String:
	var index := from
	while index >= 0 and index < line.length():
		var character := line[index]
		if character != " " and character != "\t":
			return character
		index += step
	return ""


## Count `%` occurrences that are neither inside a string literal nor the binary
## string-format operator applied to one.
func _count_non_format_modulo(source: String) -> int:
	var offending := 0
	var index := 0
	var length := source.length()
	var quote := ""
	while index < length:
		var character := source[index]
		if quote != "":
			if character == "\\":
				index += 2
				continue
			if character == quote:
				quote = ""
			index += 1
			continue
		if character == "\"" or character == "'":
			quote = character
			index += 1
			continue
		if character == "%":
			var back := index - 1
			while back >= 0 and source[back] in [" ", "\t", "\n", "\r"]:
				back -= 1
			if back < 0 or source[back] != "\"":
				offending += 1
			index += 1
			continue
		index += 1
	return offending


func _has_comparison(text: String) -> bool:
	for token: String in COMPARISON_TOKENS:
		if text.contains(token):
			return true
	return false


## The derived key names, so a check can name them without this suite
## transcribing any of them.
func inventory_names() -> Array:
	return CombatFlow.derive_field_inventory().get("key_names", []) as Array


## The step number of one recorded check, or -1.
func _order_step(order: Array, check_name: String) -> int:
	for record: Variant in order:
		if str((record as Dictionary).get("check", "")) == check_name:
			return int((record as Dictionary).get("step", -1))
	return -1


## One accepted response payload for one action, assembled by the same helper
## the offline double uses.
##
## The crafted identity is item **1034**, a committed unit whose properties carry
## `resurrectable` = 1. Item 900 was the original choice and was **falsified by
## measurement**: it is in neither `units.json` nor `buildings.json`, so
## `committed_resurrectable` reads null for it, the second ledger gate can never
## hold, and the ledger is never written however the input is shaped.
func _accepting_payload(action: String, addressing: Variant,
		derived_key: String) -> Dictionary:
	var items := _crafted_items()
	# The ledger starts at ZERO, so the derived count is exactly one and the
	# assertion that distinguishes it from a client-chosen figure cannot be
	# satisfied by whatever the input happened to start at.
	var ledger := {"1034": 0}
	var projection := CombatFlow.project_combat(items, ledger, action, addressing,
		func(item_id: int) -> Variant: return _item_resolver(item_id))
	# The item-keyed kill resolves no row, so `eligible` is ABSENT there rather
	# than an empty object, and the cast is guarded exactly as the module's own
	# `build_response` guards it.
	var eligible: Dictionary = {}
	if projection.get("eligible") is Dictionary:
		eligible = projection.get("eligible")
	var persisted := ledger.duplicate(true)
	if bool(projection.get("ledger_written", false)) \
			and projection.get("ledger_after") is Dictionary:
		var derived: Dictionary = projection.get("ledger_after")
		persisted[str(derived.get("item_id", ""))] = int(
			derived.get("count_after", 1))
	var rows_before: int = items.size()
	var destroyed := 0
	if derived_key != "":
		items.erase(derived_key)
		destroyed = 1
	return CombatFlow.build_response(action, addressing, projection, {
		"ledger_after": persisted,
		"rows_before": rows_before,
		"rows_after": items.size(),
		"changed": ([] if destroyed == 0
			else ["/maps/0/items/%s" % derived_key]),
		"resources": {
			"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
			"cash": 5, "mana": 0,
		},
		"server_time": 1791066505,
		"game_version": "alpha 0.02",
	})


## A copy of a payload with top-level fields replaced.
func _mutate(payload: Dictionary, changes: Dictionary) -> Dictionary:
	var out := payload.duplicate(true)
	for field: Variant in changes.keys():
		out[field] = changes[field]
	return out


## The accepting payload with one validation step's `resolves` field corrupted.
func _mutate_step(payload: Dictionary) -> Array:
	var order: Array = (payload["validation_order"] as Array).duplicate(true)
	order[CombatFlow.DESTRUCTION_STEP - 1] = _mutate(
		order[CombatFlow.DESTRUCTION_STEP - 1] as Dictionary,
		{"resolves": "before dispatch"})
	return order


## The accepting payload with one field of every validation step corrupted.
func _mutate_all_steps(payload: Dictionary, field: String) -> Array:
	var source: Array = payload["validation_order"] as Array
	var order: Array = []
	for position: int in range(source.size()):
		order.append(_mutate(source[position] as Dictionary, {field: "corrupted"}))
	return order


## The seven stored balances of a typed result as a plain dictionary.
func _resources_as_dictionary(resources: BootData.Resources) -> Dictionary:
	var out := {}
	if resources == null:
		return out
	for name: String in RESOURCE_NAMES:
		out[name] = int(resources.get(name))
	return out


## A JSON-round-tripped snapshot of any value, so a float that travelled as a
## JSON number compares against an integer literal.
func _normalize(value: Variant) -> Variant:
	if value == null:
		return null
	var text := JSON.stringify(value)
	var parsed: Variant = JSON.parse_string(text)
	return parsed


# ---------------------------------------------------------------------------
# Evidence report
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


## The deterministic `combat-actions-report-v1` document.
func _report(inventory: Dictionary, second: Dictionary,
		census: Dictionary) -> Dictionary:
	var source := _module_code()
	return {
		"schema": "combat-actions-report-v1",
		"generated_by": "apps/client-godot/tests/test_combat_actions.gd "
			+ "--report=<path>",
		"determinism": {
			"reads_wall_clock": false,
			"writes_absolute_paths": false,
			"reads_the_fixture_manifest": false,
			"note": "every table is generated from the delivered module's own "
				+ "constants, from this run's own measurement of the committed "
				+ "legacy source, or from committed bytes. The committed fixture "
				+ "MANIFEST is deliberately not read, because it carries a "
				+ "capture timestamp; the parity evidence lives in the Python "
				+ "replay suite and this report carries a path pointer to it",
		},
		"capability": {
			"provenance": (CombatFlow.PROVENANCE as Dictionary).duplicate(true),
			"branches": CombatFlow.branches(),
			"actions": CombatFlow.actions(),
			"action_command": (CombatFlow.ACTION_COMMAND as Dictionary)
				.duplicate(true),
			"addressing_key": (CombatFlow.ACTION_ADDRESSING_KEY as Dictionary)
				.duplicate(true),
			"addressing": (CombatFlow.ACTION_ADDRESSING as Dictionary)
				.duplicate(true),
			"intent": CombatFlow.intent_record(),
			"scope": CombatFlow.scope_record(),
		},
		"field_inventory": {
			"derived_this_run": true,
			"key_count": int(inventory.get("key_count", 0)),
			"branch_span": inventory.get("branch_span", []),
			"row_removal_region": inventory.get("row_removal_region", []),
			"fates": CombatFlow.FATES,
			"partition": bool(inventory.get("partition", false)),
			"discarded": inventory.get("discarded", []),
			"print_only": inventory.get("print_only", []),
			"mutation_path": inventory.get("mutation_path", []),
			"keys": inventory.get("keys", []),
			"correction": (CombatFlow.FIELD_INVENTORY_CORRECTION as Dictionary)
				.duplicate(true),
			"second_extraction": {
				"independent": true,
				"agrees_on_key_names": second.get("key_names")
					== inventory.get("key_names"),
				"agrees_on_discarded": second.get("discarded")
					== inventory.get("discarded"),
				"agrees_on_print_only": second.get("print_only")
					== inventory.get("print_only"),
				"agrees_on_mutation_path": second.get("mutation_path")
					== inventory.get("mutation_path"),
				"branch_span": second.get("branch_span", []),
				"row_removal_region": second.get("row_removal_region", []),
			},
		},
		"destruction": {
			"count": "ALWAYS 0 or 1, derived server-side; never a client number",
			"order": CombatFlow.ORDERING_RECORD,
			"recorded_order_precedence": {
				"document": ORDER_DOCUMENT,
				"item_id": ORDER_ITEM_ID,
				"recorded_first": ORDER_RECORDED_FIRST,
				"snapshot_sorted_first": ORDER_SNAPSHOT_FIRST,
				"numeric_min": ORDER_NUMERIC_MIN,
				"note": "three orders, three answers, so the choice is "
					+ "observable rather than decorative",
			},
			"refused_client_keys": CombatFlow.refused_client_keys({},
				inventory.get("key_names", []) as Array),
			"destruction_count_keys":
				(CombatFlow.DESTRUCTION_COUNT_KEYS as Array).duplicate(),
			"sent_survived_keys":
				(CombatFlow.SENT_SURVIVED_KEYS as Array).duplicate(),
			"rule": CombatFlow.CLIENT_DICTATED_REFUSAL,
			"refused_count_note": CombatFlow.REFUSED_COUNT_NOTE,
			"printed_count_is_request": CombatFlow.PRINTED_COUNT_IS_A_REQUEST,
		},
		"ledger": {
			"owner": "godot-unit-behaviors (unit_behaviors.gd), delegated whole",
			"gate_count": UnitBehaviors.GATE_COUNT,
			"gates": UnitBehaviors.gates(),
			"no_third_gate": UnitBehaviors.NO_THIRD_GATE,
			"no_syringe_cost": UnitBehaviors.NO_SYRINGE_COST,
			"kill_contract": (CombatFlow.KILL_CONTRACT as Dictionary)
				.duplicate(true),
			"kill_iid_contract": (CombatFlow.KILL_IID_CONTRACT as Dictionary)
				.duplicate(true),
			"team_asymmetry": CombatFlow.team_asymmetry(),
		},
		"ordering": {
			"rule": CombatFlow.ORDERING_RULE,
			"steps": CombatFlow.validation_order(),
			"destruction_step": CombatFlow.DESTRUCTION_STEP,
			"proof_halves": (CombatFlow.PROOF_HALVES as Array).duplicate(true),
		},
		"committed_content": (_distribution as Dictionary).duplicate(true),
		"corpus": {
			"measured_this_run": true,
			"document_count": census.get("document_count", 0),
			"placed_rows": census.get("placed_rows", 0),
			"unit_rows": census.get("unit_rows", 0),
			"unit_rows_on_team_one": census.get("unit_rows_on_team_one", 0),
			"unit_rows_resurrectable": census.get("unit_rows_resurrectable", 0),
			"documents_with_unit_rows": census.get("documents_with_unit_rows", 0),
			"documents_with_non_empty_ledger":
				census.get("documents_with_non_empty_ledger", 0),
			"neutral_ledger_keys": census.get("neutral_ledger_keys", 0),
			"correction": (CombatFlow.CORPUS_CORRECTION as Dictionary)
				.duplicate(true),
			"documents": census.get("documents", []),
		},
		"absences": {
			"static_functions": CombatFlow.STATIC_FUNCTIONS,
			"absent_helpers": (CombatFlow.ABSENT_HELPERS as Array).duplicate(true),
			"arithmetic_record": (CombatFlow.ARITHMETIC_RECORD as Dictionary)
				.duplicate(true),
			"arithmetic_measured": _measured_arithmetic(source,
				_code_quotes_kept(_module_source())),
			"format_operators_outside_a_string": _count_non_format_modulo(
				_code_quotes_kept(_module_source())),
			"no_combat": CombatFlow.NO_COMBAT,
			"no_cost_or_reward": CombatFlow.NO_COST_OR_REWARD,
			"no_placement_validation": CombatFlow.NO_PLACEMENT_VALIDATION,
			"non_claims": (CombatFlow.NON_CLAIMS as Array).duplicate(true),
		},
		"divergence": (CombatFlow.DIVERGENCE as Dictionary).duplicate(true),
		"refusals": (CombatFlow.REFUSALS as Array).duplicate(true),
		"evidence": {
			"fixture": FIXTURE_PATH,
			"parity_suite": PARITY_SUITE,
			"note": "the recorded fixture is replayed by the Python suite, not by "
				+ "this one, because its response bodies are the LEGACY "
				+ "{result: success} shape and cannot seed a typed parser",
		},
	}


func _write_report(path: String, inventory: Dictionary, second: Dictionary,
		census: Dictionary) -> void:
	var directory := path.get_base_dir()
	if not DirAccess.dir_exists_absolute(directory):
		DirAccess.make_dir_recursive_absolute(directory)
	var report := _report(inventory, second, census)
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		fail("the combat actions report at %s is writable" % path)
		return
	file.store_string(JSON.stringify(report, "\t", true) + "\n")
	file.close()
	check(FileAccess.file_exists(path), "the combat actions report was written")
	var reread: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	check(reread is Dictionary,
		"and re-reads as an object, so the report is not a truncated write")
	if reread is Dictionary:
		check_eq((reread as Dictionary).get("schema"),
			"combat-actions-report-v1", "and carries its schema name")
		check_eq(int((reread as Dictionary)["field_inventory"]["key_count"]),
			EXPECTED_MEASURED_KEY_COUNT,
			"and its inventory carries the measured key count")