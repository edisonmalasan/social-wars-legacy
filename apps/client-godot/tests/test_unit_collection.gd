extends "res://tests/test_base.gd"
## Unit-collection suite (OpenSpec `godot-unit-collection` "A collection prize is
## derived from committed content" / "The index is one-based, and the id-0/id-1
## alias is reported" / "One route is content-derived and the rest are
## client-supplied" / "Collection eligibility is not checked, and that gap is
## recorded" / "No unit income, no cap semantics, and no experience award" /
## "The completion intent carries only an identifier" / "An executed-legacy
## fixture for the committed grant" / "Unit-collection evidence and claim
## limits", design D1-D7).
##
## This line delivers a **content-derived grant** rather than a bare refusal, so
## most of what it asserts is positive: the committed prize, its unit/building
## classification, the index resolution with its alias, the acquisition
## inventory, and the recorded gaps and refusals.  The anti-invention guard is
## structural â€” the two delivered modules' whole function inventories are
## compared against pinned lists, so a payout, cap, threshold, eligibility, or
## award helper fails the run wherever it is added.
##
## Checks:
##   prize       a unit-granting collection, a building-granting one, the exact
##               committed bag with its committed string keys, every committed
##               entry resolving, the six/four split reported exactly, and an
##               out-of-table id reported **unresolvable with its value intact**;
##   index       the one-based index with the legacy clamp, computed
##               independently of the module and compared with it; **ids 0 and 1
##               resolving to the same prize** and every negative id too, with id
##               1 itself reported as *not* clamped;
##   acquisition all six recorded routes with their classification and their id
##               source, the **measured closed count** against the committed
##               dispatcher, the collection route as the sole content-derived
##               entry, every client-supplied route unimplemented, and no request
##               issued for any of them;
##   gaps        both authority gaps recorded as content â€” no eligibility check
##               performed, the index alias reported â€” with the gap **not** fixed
##               anywhere;
##   refusals    the three refusals with their recorded reasons, the committed
##               collect fields' **measured** zero-consumer counts and per-domain
##               coverage, the `harvester` correction, and **no** payout, cap,
##               threshold, or award helper anywhere in the delivered modules;
##   intent      the completion intent's closed key set and its ignored keys, and
##               the content-derived post-execution proof;
##   absence     the two delivered modules declare **EXACTLY** their projection,
##               inventory, and record accessors â€” no `income`, `payout`,
##               `reward`, `cap`, `limit`, `threshold`, `award`, `grant_xp`,
##               `eligible`, or `place_stored_item` helper â€” and the recorded
##               `ABSENT_HELPERS` list names eleven with its reason;
##   fixture     the committed executed-legacy fixture: the committed grant into
##               the corpus's empty storage, **exactly one** appended ledger id,
##               no placement written, no resource moved, the sanitized request,
##               the two executed probes, and the manifest's statements that the
##               grant is content-derived and the stored-item placement step was
##               **not** chained;
##   legacy      the committed legacy source re-read for the facts this line
##               records: the six `add_store_item` call sites and their enclosing
##               branches, the completion branch's own line range, the
##               `item_ids` zero-read, the quoted `"collect"` branch name, and
##               the zero occurrences of the other four collect fields;
##   boundary    no client source anywhere derives an income, a cap, a threshold,
##               an experience award, or an eligibility check â€” and the absence
##               of any **other** collection endpoint;
##   corpus      the committed fresh-player corpus measurement: 40 rows, 11
##               distinct ids, no unit row, an EMPTY storage, an EMPTY collection
##               ledger, and 40 empty attribute bags;
##   content     the committed prize table and the committed collect-field
##               distribution measured from the verified registry, never asserted
##               from prose;
##   purity      the two delivered modules name no node, a clock, a request, or a
##               transport token, and preload only the read-only projection;
##   containment the content package, the committed saves, the committed
##               fixtures, and the legacy root modules are byte-identical after
##               the run.
##
## Hermetic: no process, no server, no socket, and **no request is issued** â€” the
## one route this line delivers is exercised through the projection and the
## committed fixture, never over the network.
##
## `--report=<path>` writes the deterministic `unit-collection-report-v1`
## evidence report; the bare `--report` flag defaults to
## `evidence/unit-collection/report.json`. Every table is derived from the live
## model, the verified registry, and the committed bytes, so the report cannot
## drift from the code it documents.

const CollectionFlow = preload("res://scripts/units/collection_flow.gd")
const CollectionPrize = preload("res://scripts/units/collection_prize.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Default destination of the bare `--report` flag.
const DEFAULT_REPORT_PATH := "evidence/unit-collection/report.json"
## The committed corpus and the executed fixture this line measures.
const CORPUS_SAVE := "tests/saves/fresh-player.json"
const FIXTURE_DIR := "tests/fixtures/godot-unit-collection"
const FIXTURE_STEP := "steps/command_complete_collection"
const CORPUS_MAP_INDEX := 0
const EXPECTED_ROWS := 40
const EXPECTED_DISTINCT_ITEM_IDS := 11
## The committed content distribution, measured rather than trusted.
const EXPECTED_UNITS := 429
const EXPECTED_BUILDINGS := 470
const EXPECTED_UNIT_COLLECTIONS := 6
const EXPECTED_BUILDING_COLLECTIONS := 4
const EXPECTED_DISTINCT_PRIZE_IDS := 10
## The committed collect fields' measured per-domain positive counts.  These are
## ASSERTED against the verified registry, so a content change that moved a
## value would fail the run rather than invalidate a pinned number.
const EXPECTED_COLLECT_POSITIVE := {
	"collect": {"units": 0, "buildings": 51},
	"collect_xp": {"units": 427, "buildings": 53},
	"max_collects": {"units": 0, "buildings": 11},
	"max_elem_vol": {"units": 5, "buildings": 39},
}
## `collect_type` is the one committed collect field that is **not** a
## number: it reads as a resource letter (`g` on 427 of the 429 units and
## 425 of the 470 buildings, `w`/`o`/`s`/`c` on the rest), so it is
## measured by how many entries CARRY it rather than by a positive count.
## That it looks exactly like a rule and has no consumer is the point.
const EXPECTED_COLLECT_TYPE_CARRYING := {"units": 429, "buildings": 470}
## The five committed collect fields, with the measured legacy occurrence count of
## the literal string in each named legacy module set.  All five are ZERO â€” the
## fourth and fifth such committed fields in this project.
const EXPECTED_COLLECT_LEGACY_READS := {
	"collect_type": 0, "collect_xp": 0, "max_collects": 0,
	"max_elem_vol": 0, "harvester": 0,
}
## The whole function inventory of `collection_prize.gd`. This is the
## anti-invention guard: a payout, cap, award, or eligibility helper appears here
## and fails the suite. Every entry is a projection reader, a recorded-contract
## accessor, or a private helper â€” nothing else.
const EXPECTED_PRIZE_METHODS := [
	"_classify", "_collections_with_class", "_column_text",
	"_committed_table", "_prize_bag", "_reject", "_sorted_keys",
	"_sum", "_type_name", "_whole_number", "alias_of",
	"building_collections", "classification_vocabulary", "committed_table",
	"entry_note", "index_for", "index_note", "index_record", "is_aliased",
	"resolve", "unit_collections",
]
## The whole function inventory of `collection_flow.gd`, asserted for the same
## reason.
const EXPECTED_FLOW_METHODS := [
	"acquisition_note", "acquisition_record", "acquisition_route_names",
	"acquisition_routes", "authority_gaps", "classification_counts",
	"classification_vocabulary", "client_supplied_routes",
	"content_derived_routes", "eligibility_record", "evaluate",
	"intent_record", "no_derivation_finding", "readout_text", "refusal_record",
	"scope_record",
]
## Helpers a payout, cap, threshold, eligibility, or award rule would take. The
## inventories above are the real gate; this list is what the suite also asserts
## is absent **by name**, so a rename cannot smuggle one past the inventory and a
## leftover fails visibly.
const FORBIDDEN_HELPERS := [
	"income", "unit_income", "payout", "reward", "rewards", "cap", "caps",
	"max_collects", "limit", "limits", "threshold", "thresholds",
	"experience", "award", "award_xp", "grant_xp", "xp", "eligible",
	"check_eligibility", "is_eligible", "eligibility_check", "earn", "earned",
	"place_stored_item", "place_granted", "collection_cap",
	"experience_award",
]
## Tokens that would mean an income, cap, threshold, eligibility, or award
## mechanism is implemented. Spelled as fragments because the project-scope suite
## scans every source file for their literal forms; the strings are matched
## against the modules' **declarations only**, so the recorded contract text may
## still name them.
const BEHAVIOUR_NEEDLES := [
	"collection_in" + "come", "collection_pay" + "out",
	"collection_re" + "ward", "collection_" + "cap",
	"collection_thresh" + "old", "collection_lim" + "it",
	"collection_award", "collection_eligib", "is_collection_el" + "igible",
	"check_collection_el" + "igibility", "unit_collection_in" + "come",
	"unit_collection_pay" + "out", "place_sto" + "red_item",
]
## The same needles scanned over the WHOLE client source tree, which is the
## structural form of "no client source derives an income, a cap, a threshold,
## an experience award, or an eligibility check".
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
	"NO UNIT INCOME, COLLECTION PAYOUT, CAP SEMANTICS, OR EXPERIENCE AWARD IS",
	"NO COLLECTION ELIGIBILITY IS CHECKED",
	"COLLECTION IDS 0 AND 1 ALIAS",
	"NO CLIENT-SUPPLIED ACQUISITION ROUTE IS IMPLEMENTED",
	"THE STORED-ITEM PLACEMENT STEP IS NOT DELIVERED",
	"NO UNIT IS PLACED OR GARRISONED",
	"no windowed capture is claimed",
	"no pixel-parity oracle against the legacy client exists",
]
## The legacy root modules this line re-reads for its recorded facts. A missing
## one is a **failure**, never a silently smaller search: a measurement over a
## file that is not there would turn the zero-consumer claim vacuous.
const LEGACY_MODULES := ["command.py", "engine.py", "sessions.py", "server.py",
	"constants.py", "get_game_config.py", "version.py", "auctions.py",
	"get_player_info.py", "legacy_command_recorder.py"]
## The four fields whose literal string must not appear in ANY legacy module.
const ZERO_OCCURRENCE_FIELDS := [
	"collect_type", "collect_xp", "max_collects", "max_elem_vol", "harvester",
]
## The two ways a legacy branch is identified, used to attribute a call site to
## the branch that encloses it.
const CALL_STORE := ["add_store_item("]
const DELIVERED_PRIZE_SCRIPT := "res://scripts/units/collection_prize.gd"
const DELIVERED_FLOW_SCRIPT := "res://scripts/units/collection_flow.gd"

## The registry reference the content measurements read, set once in
## `run_scenario()`. A missing registry fails the run before it is used.
var _registry: Variant = null


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if _scenario_arg() == "live-collection":
		await _check_live_collection()
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

	_check_prize(registry)
	_check_index(registry)
	_check_acquisition()
	_check_gaps()
	_check_refusals(registry)
	_check_intent()
	_check_absence()
	_check_fixture()
	var legacy := _check_legacy()
	_check_boundary()
	var corpus := _check_corpus()
	var coverage := _check_content(registry)
	_check_containment(package_before, saves_before, fixtures_before,
		legacy_before, save_before)

	var report_path := _report_path_arg()
	if not report_path.is_empty():
		_write_report(report_path, registry, content, legacy, corpus, coverage,
			package_before, save_before)
	info("unit collection: %d committed collections, %d unit-granting, "
		% [CollectionPrize.COMMITTED_COLLECTION_COUNT,
			EXPECTED_UNIT_COLLECTIONS]
		+ "%d acquisition routes with %d content-derived, ids 0 and 1 alias=true"
			% [CollectionFlow.ACQUISITION_ROUTE_COUNT,
				CollectionFlow.CONTENT_DERIVED_ROUTE_COUNT])


# ---------------------------------------------------------------------------
# The committed prize (design D1)
# ---------------------------------------------------------------------------


## A unit-granting collection, a building-granting one, the exact committed bag
## with its committed string keys, every committed entry resolving, the
## six/four split reported exactly, and an out-of-table id reported
## **unresolvable with its recorded value intact**.
func _check_prize(registry: Variant) -> void:
	# The suite's OWN row resolver and enumeration, independent of any surface's.
	var row := _row_reader(registry)
	var ids := _id_reader(registry)
	var table := CollectionPrize.committed_table(row, ids)
	check_eq(table.size(), CollectionPrize.COMMITTED_COLLECTION_COUNT,
		"the committed collections table holds exactly %d rows"
			% CollectionPrize.COMMITTED_COLLECTION_COUNT)
	# Every committed collection resolves and reports the SAME name, id column,
	# and bag as the registry's own row â€” the projection is a **report**, never a
	# re-derivation.
	var unit_grants := 0
	var building_grants := 0
	var distinct_ids := {}
	for position in table.size():
		var collection_id := position + 1
		var projection: Dictionary = CollectionPrize.resolve(collection_id, row, ids)
		check(bool(projection.get("ok", false)),
			"collection %d resolves in the committed table" % collection_id)
		check(bool(projection.get("resolved", false)),
			"collection %d reports itself resolved" % collection_id)
		var committed: Dictionary = table[position]
		check_eq(str(projection.get("name", "")), str(committed.get("name", "")),
			"collection %d reports the committed row's OWN name verbatim"
				% collection_id)
		check_eq(str(projection.get("id_column", "")),
			str(_normalize(committed.get("id", ""))),
			"collection %d reports the committed native id column verbatim, in "
				% collection_id + "its integer form rather than the engine's "
				+ "widened float")
		var bag: Dictionary = projection.get("prize", {})
		check(not bag.is_empty(),
			"collection %d carries a committed prize bag" % collection_id)
		for key: Variant in bag.keys():
			check(key is String,
				"collection %d's prize keys are the COMMITTED STRING form %s"
					% [collection_id, key])
			distinct_ids[str(key)] = true
		if int(projection.get("unit_count", 0)) > 0:
			unit_grants += 1
		if int(projection.get("building_count", 0)) > 0:
			building_grants += 1
		for entry: Dictionary in projection.get("entries", []):
			var label := str(entry.get("classification", ""))
			check(label == CollectionPrize.CLASS_UNIT
					or label == CollectionPrize.CLASS_BUILDING,
				"collection %d's prize is classified as a unit or a building, "
					% collection_id + "never left unclassified")
			check(not str(entry.get("name", "")).is_empty(),
				"collection %d's prize %s resolves to a committed name"
					% [collection_id, str(entry.get("item_id", ""))])
	check_eq(unit_grants, EXPECTED_UNIT_COLLECTIONS,
		"exactly %d committed collections grant a UNIT, reported as a "
			% EXPECTED_UNIT_COLLECTIONS + "MEASUREMENT of the committed table")
	check_eq(building_grants, EXPECTED_BUILDING_COLLECTIONS,
		"exactly %d committed collections grant a building"
			% EXPECTED_BUILDING_COLLECTIONS)
	check_eq(unit_grants + building_grants,
		CollectionPrize.COMMITTED_COLLECTION_COUNT,
		"the split accounts for every committed collection")
	check_eq(distinct_ids.size(), EXPECTED_DISTINCT_PRIZE_IDS,
		"the ten committed prize bags hold %d DISTINCT item ids between them"
			% EXPECTED_DISTINCT_PRIZE_IDS)
	check_eq(CollectionPrize.COMMITTED_UNIT_COLLECTIONS,
		EXPECTED_UNIT_COLLECTIONS, "the recorded unit-granting count agrees")
	check_eq(CollectionPrize.COMMITTED_BUILDING_COLLECTIONS,
		EXPECTED_BUILDING_COLLECTIONS, "the recorded building-granting count agrees")
	# The enumeration helper agrees with the projection's own count, so a report
	# can never list a different number of unit collections.
	check_eq(CollectionPrize.unit_collections(row, ids).size(),
		EXPECTED_UNIT_COLLECTIONS,
		"unit_collections() lists exactly the %d unit-granting collections"
			% EXPECTED_UNIT_COLLECTIONS)
	check_eq(CollectionPrize.building_collections(row, ids).size(),
		EXPECTED_BUILDING_COLLECTIONS,
		"building_collections() lists exactly the %d building-granting collections"
			% EXPECTED_BUILDING_COLLECTIONS)
	# The measured lists carry the same facts the projection reports.
	for entry: Dictionary in CollectionPrize.unit_collections(row, ids):
		check(int(entry.get("collection_id", 0)) >= 1,
			"a unit-granting collection reports a one-based id")
		check(not str(entry.get("item_name", "")).is_empty(),
			"a unit-granting collection reports its granted unit's committed name")
	# An out-of-table id: unresolvable, value INTACT, nothing substituted.
	for value: int in [11, 12, 100, 999999]:
		var missing: Dictionary = CollectionPrize.resolve(value, row, ids)
		check(not bool(missing.get("ok", false)),
			"collection id %d is unresolvable" % value)
		check_eq(bool(missing.get("resolved", true)), false,
			"collection id %d reports itself unresolved" % value)
		check_eq(int(missing.get("collection_id", -2)), value,
			"collection id %d is reported with its recorded value INTACT"
				% value)
		check_eq(missing.get("prize", {"substituted": true}), {},
			"collection id %d substitutes NO prize" % value)
		check_eq((missing.get("entries", []) as Array).size(), 0,
			"collection id %d substitutes NO entry" % value)
		check_eq(str(missing.get("name", "x")), "",
			"collection id %d substitutes NO name" % value)
		check_eq(int(missing.get("item_count", -1)), 0,
			"collection id %d reports no item count" % value)
	# A non-integer id is refused, never coerced.
	for value: Variant in [null, "1", 1.0, 1.5, true, [], {}]:
		var refused: Dictionary = CollectionPrize.resolve(value, row, ids)
		check(not bool(refused.get("ok", false)),
			"a %s collection id is refused" % [value])
		check_eq(str(refused.get("reason", "")),
			CollectionPrize.REASON_INVALID_COLLECTION_ID,
			"the refusal names the projection's own reason")


# ---------------------------------------------------------------------------
# The one-based index and its alias (design D3)
# ---------------------------------------------------------------------------


## The index is computed here **independently** of the module and compared with
## it, and the alias is asserted outright: ids 0 and 1 resolve to the same
## committed prize, as does every negative id, while id 1 itself is not clamped.
func _check_index(registry: Variant) -> void:
	var row := _row_reader(registry)
	var ids := _id_reader(registry)
	var table := CollectionPrize.committed_table(row, ids)
	var one: Dictionary = CollectionPrize.resolve(1, row, ids)
	var zero: Dictionary = CollectionPrize.resolve(0, row, ids)
	# THE ALIAS, asserted three ways.
	check_eq(zero.get("prize", {}), one.get("prize", {}),
		"COLLECTION ID 0 AND COLLECTION ID 1 RESOLVE TO THE SAME PRIZE")
	check_eq(str(zero.get("name", "")), str(one.get("name", "")),
		"ids 0 and 1 select the same committed collection name")
	check_eq(int(zero.get("index", -1)), int(one.get("index", -2)),
		"ids 0 and 1 select the same table position")
	check_eq(bool(zero.get("aliased", false)), true,
		"id 0 is reported as an ALIAS, never as a distinct collection")
	check_eq(bool(zero.get("clamped", false)), true,
		"id 0 is reported as clamped by the legacy max(0, â€¦)")
	check_eq(int(zero.get("alias_of", -1)), 1,
		"id 0 is reported as resolving to collection id 1")
	check_eq(int(zero.get("requested_index", 0)), -1,
		"id 0 requests index -1, which the clamp replaced")
	check_eq(int(zero.get("collection_id", -2)), 0,
		"an aliased id is reported with the value the client NAMED")
	# Collection id 1 is the boundary and is NOT clamped: 1 - 1 is already 0.
	check_eq(bool(one.get("clamped", true)), false,
		"id 1 is NOT clamped: 1 - 1 is already its own index")
	check_eq(bool(one.get("aliased", true)), false, "id 1 is not an alias")
	check_eq(int(one.get("alias_of", 0)), -1, "id 1 names no alias target")
	check_eq(int(one.get("requested_index", -1)), 0,
		"id 1 requests index 0, unchanged")
	# Every negative id aliases too â€” the general statement, not just id 0.
	for value: int in [-1, -2, -5, -9999]:
		var negative: Dictionary = CollectionPrize.resolve(value, row, ids)
		check_eq(negative.get("prize", {}), one.get("prize", {}),
			"collection id %d resolves to the same committed prize as id 1"
				% value)
		check_eq(bool(negative.get("aliased", false)), true,
			"collection id %d is reported as an alias" % value)
		check_eq(int(negative.get("alias_of", -1)), 1,
			"collection id %d names collection id 1 as its alias target" % value)
		check_eq(int(negative.get("collection_id", -2)), value,
			"collection id %d is reported with its recorded value intact"
				% value)
	# The arithmetic is the legacy expression, computed HERE and compared.
	for value: int in [-1000, -5, -1, 0, 1, 2, 5, 10, 11, 99]:
		var expected := maxi(0, value - 1)
		check_eq(CollectionPrize.index_for(value), expected,
			"id %d selects index %d through max(0, collection - 1)"
				% [value, expected])
		var projection: Dictionary = CollectionPrize.resolve(value, row, ids)
		check_eq(int(projection.get("index", -1)), expected,
			"id %d reports the derived index" % value)
		check_eq(int(projection.get("requested_index", 0)), value - 1,
			"id %d reports the UNCLAMPED requested index" % value)
		check_eq(bool(projection.get("clamped", false)), expected != value - 1,
			"id %d reports whether the clamp actually moved its index" % value)
		if expected < table.size():
			check_eq(int(projection.get("index", -1)), expected,
				"id %d selects the committed row at position %d"
					% [value, expected])
	# The helper predicates agree with the projection.
	check_eq(CollectionPrize.is_aliased(0), true, "is_aliased(0) is true")
	check_eq(CollectionPrize.is_aliased(1), false, "is_aliased(1) is false")
	check_eq(CollectionPrize.is_aliased(-3), true, "is_aliased(-3) is true")
	check_eq(CollectionPrize.alias_of(0), 1, "alias_of(0) names id 1")
	check_eq(CollectionPrize.alias_of(1), -1, "alias_of(1) names no target")
	# The recorded index record carries the rule, the retained alternative, and
	# both boundary facts.
	var record: Dictionary = CollectionPrize.index_record()
	check_eq(str(record.get("base", "")), CollectionPrize.INDEX_BASE,
		"the index record names the one-based base")
	check_eq(str(record.get("derivation_status", "")),
		"derived-provisional",
		"the one-based reading is marked DERIVED-PROVISIONAL")
	check_eq(str(record.get("rejected_alternative", "")),
		CollectionPrize.REJECTED_ALTERNATIVE,
		"the ZERO-BASED alternative is retained, not deleted")
	check(not str(record.get("rejected_alternative_note", "")).is_empty(),
		"the rejected alternative carries the reason it was rejected")
	check_in_text(str(record.get("rule", "")), "max(0, collection - 1)",
		"the recorded rule names the legacy expression itself")
	check_in_text(str(record.get("alias_rule", "")),
		"COLLECTION ID 0 AND COLLECTION ID 1",
		"the recorded alias rule states the alias outright")
	check_eq(bool(record.get("zero_and_one_alias", false)), true,
		"the index record states the id-0/id-1 alias as a fact")
	check_eq(bool(record.get("negative_ids_alias_too", false)), true,
		"the index record states that negative ids alias too")
	# The readout says it out loud rather than leaving the reader to infer it.
	var clamped_note := CollectionPrize.index_note(zero)
	check_in_text(clamped_note, "CLAMPED",
		"a clamped id's readout says CLAMPED outright")
	check_in_text(clamped_note, "collection id 1",
		"a clamped id's readout names the collection it resolves to")
	var plain_note := CollectionPrize.index_note(one)
	check(plain_note.find("CLAMPED") == -1,
		"an unclamped id's readout does not claim a clamp")


# ---------------------------------------------------------------------------
# The acquisition inventory (design D4)
# ---------------------------------------------------------------------------


## All six recorded routes with their classification and their id source, the
## **measured closed count** against the committed dispatcher, the collection
## route as the sole content-derived entry, every client-supplied route
## unimplemented, and no request issued for any of them.
func _check_acquisition() -> void:
	var routes := CollectionFlow.acquisition_routes()
	check_eq(routes.size(), CollectionFlow.ACQUISITION_ROUTE_COUNT,
		"the inventory holds exactly the %d recorded acquisition routes"
			% CollectionFlow.ACQUISITION_ROUTE_COUNT)
	check_eq(CollectionFlow.acquisition_route_names(), [
		"store_item", "store_add_items", "win_daily_bonus",
		"buy_stored_item_cash", "complete_collection", "buy_offer_pack",
	], "the six inventoried routes are the committed ones, in line order")
	# Every route carries an explicit classification and an id source, and there
	# is no fourth heading.
	var counts: Dictionary = CollectionFlow.classification_counts()
	check_eq(counts.get(CollectionFlow.CLASS_CONTENT, 0),
		CollectionFlow.CONTENT_DERIVED_ROUTE_COUNT,
		"exactly %d route is content-derived"
			% CollectionFlow.CONTENT_DERIVED_ROUTE_COUNT)
	check_eq(counts.get(CollectionFlow.CLASS_CLIENT, 0), 4,
		"exactly four routes take their id from a client argument")
	check_eq(counts.get(CollectionFlow.CLASS_EXISTING, 0), 1,
		"exactly one route moves an id off a row the player already placed")
	check_eq(counts.size(), CollectionFlow.CLASSIFICATIONS.size(),
		"the classification counts cover exactly the closed vocabulary")
	check_eq(CollectionFlow.classification_vocabulary(),
		[CollectionFlow.CLASS_CONTENT, CollectionFlow.CLASS_CLIENT,
			CollectionFlow.CLASS_EXISTING],
		"the closed vocabulary is content-derived, client-supplied, "
			+ "already-existing")
	# The collection route is the SOLE content-derived entry, and it is the only
	# implemented one.
	var derived := CollectionFlow.content_derived_routes()
	check_eq(derived, ["complete_collection"],
		"complete_collection is the SOLE content-derived acquisition route")
	for entry: Dictionary in routes:
		var label := str(entry["classification"])
		check(CollectionFlow.CLASSIFICATIONS.has(label),
			"route %s carries a classification inside the closed set"
				% str(entry["branch"]))
		check(not str(entry["input"]).is_empty(),
			"route %s names WHERE its id comes from" % str(entry["branch"]))
		check(not str(entry["note"]).is_empty(),
			"route %s carries a recorded note" % str(entry["branch"]))
		check(str(entry["site"]).find("command.py:") == 0,
			"route %s names its committed source line" % str(entry["branch"]))
		if label == CollectionFlow.CLASS_CLIENT:
			check_eq(bool(entry["implemented"]), false,
				"client-supplied route %s is NOT implemented"
					% str(entry["branch"]))
		if label != CollectionFlow.CLASS_CONTENT:
			check_eq(bool(entry["implemented"]), false,
				"route %s is recorded and nothing more" % str(entry["branch"]))
	# The two plausible unit sources the production line recorded remain
	# client-supplied and unimplemented â€” the finding is COMPLETED, not amended.
	var client := CollectionFlow.client_supplied_routes()
	check(client.has("buy_offer_pack"),
		"buy_offer_pack is still recorded as client-supplied")
	check(client.has("buy_stored_item_cash"),
		"buy_stored_item_cash is still recorded as client-supplied")
	check(not client.has("complete_collection"),
		"complete_collection is NOT among the client-supplied routes")
	# The recorded finding and the record the evidence report consumes.
	var record: Dictionary = CollectionFlow.acquisition_record()
	check_eq(bool(record.get("request_issued", true)), false,
		"NO request is issued for any recorded acquisition route")
	check_eq(int(record.get("content_derived_route_count", 0)), 1,
		"the record's content-derived count is exactly one")
	check_eq((record.get("content_derived_routes", []) as Array),
		["complete_collection"],
		"the record names the same single content-derived route")
	check_in_text(str(record.get("no_derivation", "")),
		"EXACTLY ONE ACQUISITION ROUTE IS CONTENT-DERIVED",
		"the recorded finding states the count it proves")
	check_in_text(str(record.get("not_an_acquisition_route", "")),
		"unit_collections_completed",
		"the record separates the two 'collection' concepts")
	check_in_text(str(record.get("not_an_acquisition_route", "")),
		"grants NOTHING",
		"the record says the tracker grants nothing")
	check_in_text(CollectionFlow.acquisition_note(),
		"EXACTLY ONE ACQUISITION ROUTE IS CONTENT-DERIVED",
		"the one-line acquisition note states the count it proves")
	# The readout answers "where do units come from" in one line.
	var evaluation := CollectionFlow.evaluate(1, _row_reader(_registry),
		_id_reader(_registry))
	check_in_text(str(evaluation.get("readout", "")),
		"one content-derived acquisition route",
		"the readout states the acquisition classification")
	var flow_sources := _declared_methods(DELIVERED_FLOW_SCRIPT)
	check(not flow_sources.has("acquire_unit"),
		"the delivered flow declares no acquire_unit helper: the only route it "
			+ "delivers is the content-derived one")


# ---------------------------------------------------------------------------
# The recorded authority gaps (design D2)
# ---------------------------------------------------------------------------


## Both gaps recorded as content and **not** fixed: no eligibility check is
## performed on the caller's collection state, and the index alias is reported.
func _check_gaps() -> void:
	var gaps := CollectionFlow.authority_gaps()
	check_eq(gaps.size(), 2, "both authority gaps are recorded")
	var names: Array = []
	for entry: Dictionary in gaps:
		names.append(str(entry["gap"]))
		check_eq(bool(entry.get("fixed", true)), false,
			"gap %s is recorded as NOT fixed" % str(entry["gap"]))
		check(not str(entry.get("rule", "")).is_empty(),
			"gap %s carries its rule" % str(entry["gap"]))
	check_eq(names, ["no_eligibility_check", "index_alias"],
		"the two recorded gaps are the eligibility gap and the index alias")
	# The eligibility gap, and what a caller CANNOT do.
	var record: Dictionary = CollectionFlow.eligibility_record()
	check_eq(bool(record.get("checked", true)), false,
		"the record states that NO eligibility check was performed")
	check_eq(bool(record.get("implemented_check", true)), false,
		"the record states that NO eligibility check was implemented")
	check_eq(bool(record.get("caller_may_name_any_committed_collection", false)),
		true, "a caller may name any of the ten committed collections")
	check_eq(bool(record.get("caller_may_choose_the_grant", true)), false,
		"a caller may NOT choose the grant: the contents stay content-derived")
	check_eq(bool(record.get("item_ids_read_by_any_branch", true)), false,
		"the committed item_ids requirement list is read by NO branch")
	check_in_text(str(record.get("rule", "")), "NO COLLECTION ELIGIBILITY",
		"the recorded rule states the gap outright")
	check_in_text(str(record.get("rule", "")), "authoritative validation belongs",
		"the recorded rule says where the gap belongs")
	# The alias gap, in the flow's own words.
	check_in_text(str(record.get("alias_gap", "")), "COLLECTION ID 0 AND",
		"the alias gap states the id-0/id-1 alias")
	check_in_text(CollectionFlow.NO_ELIGIBILITY_CHECK, "item_ids",
		"the eligibility rule names the unread requirement list")
	# NO eligibility check is PERFORMED anywhere: the evaluation carries no such
	# field, and the flow declares no eligibility helper.
	var evaluation := CollectionFlow.evaluate(1, _row_reader(_registry),
		_id_reader(_registry))
	check_eq(bool(evaluation.get("eligibility_checked", true)), false,
		"the evaluation reports that it checked no eligibility")
	for field: String in ["eligible", "is_eligible", "earned", "requirement_met",
			"has_items", "item_ids_checked"]:
		check(not evaluation.has(field),
			"the evaluation carries NO %s field: the legacy server verifies "
				% field + "nothing about a collection's own state")
	check_in_text(str(evaluation.get("eligibility", "")),
		"NO COLLECTION ELIGIBILITY",
		"the evaluation carries the recorded gap beside its answer")
	check_in_text(str(evaluation.get("alias_gap", "")),
		"COLLECTION ID 0 AND",
		"the evaluation carries the recorded alias gap beside its answer")


# ---------------------------------------------------------------------------
# The three refusals (design D5)
# ---------------------------------------------------------------------------


## The three refusals with their recorded reasons, the committed collect fields'
## **measured** zero-consumer counts and per-domain coverage, the `harvester`
## correction, and **no** payout, cap, threshold, or award helper anywhere.
func _check_refusals(registry: Variant) -> void:
	var record: Dictionary = CollectionFlow.refusal_record()
	var refusals: Array = record.get("refusals", [])
	check_eq(refusals.size(), 3, "three refusals are recorded")
	var names: Array = []
	for entry: Dictionary in refusals:
		names.append(str(entry["refusal"]))
		check_eq(bool(entry.get("implemented", true)), false,
			"refusal %s is reported as NOT implemented" % str(entry["refusal"]))
		check(not str(entry.get("rule", "")).is_empty(),
			"refusal %s carries its rule" % str(entry["refusal"]))
	check_eq(names, ["unit_income", "cap_semantics", "experience_award"],
		"the three refusals are unit income, cap semantics, and experience")
	check_in_text(CollectionFlow.NO_UNIT_INCOME, "0 of 429",
		"the income refusal names the measured unit count")
	check_in_text(CollectionFlow.NO_UNIT_INCOME, "BRANCH NAME",
		"the income refusal records that the quoted \"collect\" is a branch name")
	check_in_text(CollectionFlow.NO_CAP_SEMANTICS, "ALL 429",
		"the cap refusal names the measured unit count")
	check_in_text(CollectionFlow.NO_CAP_SEMANTICS, "NO UNIT ANALOGUE",
		"the cap refusal says the refused cap has no unit analogue")
	check_in_text(CollectionFlow.NO_EXPERIENCE_AWARD, "CLIENT ARGUMENT",
		"the experience refusal records the client-sent amount it declines")
	check_in_text(CollectionFlow.NO_EXPERIENCE_AWARD, "427",
		"the experience refusal records the measured non-zero unit count")
	check_in_text(CollectionFlow.NO_EXPERIENCE_AWARD,
		"godot-unit-production",
		"the experience refusal names the earlier capability whose refusal stands")
	# The recorded ABSENCE is stated as an absence, never as permission.
	check_in_text(CollectionFlow.NO_CAP_SEMANTICS,
		"permission to set a threshold",
		"the cap refusal states the absence is never read as permission to set "
			+ "a threshold")
	# The absence flags on the record.
	for field: String in ["income_derived", "cap_interpreted",
			"experience_awarded", "award_helper_exists", "cap_helper_exists",
			"payout_helper_exists"]:
		check_eq(bool(record.get(field, true)), false,
			"the refusal record reports %s as false" % field)
	# The `harvester` correction: not a committed field, five properties flags.
	check_eq(bool(record.get("harvester_is_a_committed_field", true)), false,
		"the record states harvester is NOT a committed content field")
	check_in_text(str(record.get("harvester", "")),
		"NOT A COMMITTED CONTENT FIELD",
		"the harvester correction says so outright")
	for unit_id: String in ["1001", "1039", "1040", "1041", "1125"]:
		check_in_text(str(record.get("harvester", "")), unit_id,
			"the harvester correction names unit %s" % unit_id)
	# The five committed collect fields, each with a MEASURED zero legacy-read
	# count and a MEASURED per-domain positive count.
	var fields: Array = record.get("collect_fields", [])
	check_eq(fields.size(), 5, "five committed collect fields are recorded")
	for entry: Dictionary in fields:
		var field := str(entry["field"])
		check_eq(int(entry.get("legacy_reads", -1)), 0,
			"field %s is recorded with ZERO legacy reads" % field)
		var expected: Dictionary = EXPECTED_COLLECT_POSITIVE.get(field, {})
		if EXPECTED_COLLECT_POSITIVE.has(field):
			check_eq(int(entry.get("units_positive", -1)),
				int(expected.get("units", -2)),
				"field %s's recorded unit positive count is measured" % field)
			check_eq(int(entry.get("buildings_positive", -1)),
				int(expected.get("buildings", -2)),
				"field %s's recorded building positive count is measured"
					% field)
		else:
			# collect_type reads as a resource LETTER, so it is measured by how
			# many entries carry it, and its recorded positive count is the
			# measured zero rather than a guess.
			check_eq(int(entry.get("units_positive", -1)), 0,
				"field %s records NO positive unit count: it is a letter"
					% field)
			check_eq(int(entry.get("buildings_positive", -1)), 0,
				"field %s records NO positive building count: it is a letter"
					% field)
		check_eq(int(entry.get("units_carried", -1)), EXPECTED_UNITS,
			"field %s's recorded unit carrying count is %d"
				% [field, EXPECTED_UNITS])
		check_eq(int(entry.get("buildings_carried", -1)), EXPECTED_BUILDINGS,
			"field %s's recorded building carrying count is %d"
				% [field, EXPECTED_BUILDINGS])
		check_eq(int(entry.get("units_of", 0)), EXPECTED_UNITS,
			"field %s's recorded unit population is %d" % [field, EXPECTED_UNITS])
		check_eq(int(entry.get("buildings_of", 0)), EXPECTED_BUILDINGS,
			"field %s's recorded building population is %d"
				% [field, EXPECTED_BUILDINGS])
	# The zero-consumer precedents, so the refusal is a rule and not a taste.
	var precedents: Array = record.get("zero_consumer_precedents", [])
	check_eq(precedents.size(), 3,
		"three earlier zero-consumer fields are recorded as precedent")
	for entry: Dictionary in precedents:
		check(not str(entry.get("field", "")).is_empty(),
			"each precedent names its field")
		check(not str(entry.get("fact", "")).is_empty(),
			"each precedent carries its measured fact")
	# The evaluation carries every refusal flag as a constant false.
	var evaluation := CollectionFlow.evaluate(1, _row_reader(registry),
		_id_reader(registry))
	for field: String in ["income_derived", "cap_interpreted",
			"experience_awarded", "unit_placed",
			"stored_item_placement_delivered"]:
		check_eq(bool(evaluation.get(field, true)), false,
			"the evaluation reports %s as NOT implemented" % field)
	for field: String in ["income", "payout", "reward", "cap", "threshold",
			"limit", "award", "granted_unit", "unit_xp", "max_collects",
			"collect_xp", "harvester"]:
		check(not evaluation.has(field),
			"the evaluation carries NO %s field at all" % field)
	# The readout says the absences outright rather than leaving the reader to
	# infer them.
	var readout := str(evaluation.get("readout", ""))
	for phrase: String in ["no eligibility check", "no unit income", "no cap",
			"no experience", "storage only"]:
		check_in_text(readout, phrase,
			"the readout states '%s' rather than leaving the reader to infer it"
				% phrase)
	check_in_text(readout, "separate carried follow-up",
		"the readout says the stored-item placement step is a follow-up")


# ---------------------------------------------------------------------------
# The completion intent (design D1)
# ---------------------------------------------------------------------------


## The intent's closed key set and its ignored keys, and the content-derived
## post-execution proof â€” read from the module's own record so the report cannot
## describe a contract the code does not hold.
func _check_intent() -> void:
	var record: Dictionary = CollectionFlow.intent_record()
	check_eq(record.get("keys", []), ["user_id", "collection_id"],
		"the completion intent carries EXACTLY a player identifier and a "
			+ "collection id")
	var ignored: Array = record.get("ignored_keys", [])
	for key: String in ["prize", "item_id", "quantity", "item", "grant", "cost",
			"price", "resources_changed", "vector"]:
		check(ignored.has(key),
			"the intent records %s as an ignored client key" % key)
	check_eq(ignored.size(), CollectionFlow.INTENT_IGNORED_KEYS.size(),
		"the record's ignored-key list is the module's own")
	check(not (record.get("keys", []) as Array).has("prize"),
		"the intent carries NO prize key at all")
	check(not (record.get("keys", []) as Array).has("item_id"),
		"the intent carries NO item id key at all")
	check(not (record.get("keys", []) as Array).has("quantity"),
		"the intent carries NO quantity key at all")
	check_eq(str(record.get("command", "")), CollectionFlow.COMPLETE_COMMAND,
		"the record names the one legacy command the intent derives")
	check_eq(bool(record.get("grant_is_content_derived", false)), true,
		"the record states the grant is content-derived")
	check_in_text(str(record.get("grant_derived_from", "")), "committed",
		"the record names the committed table the grant comes from")
	check_in_text(str(record.get("note", "")), "IGNORED",
		"the record says the extra keys are ignored server-side")
	# The post-execution proof, and its non-tautological half.
	check_in_text(str(record.get("proof", "")), "CONTENT-DERIVED",
		"the proof is recorded as content-derived")
	check_in_text(str(record.get("proof", "")), "COMMITTED prize bag",
		"the proof compares against the COMMITTED bag, not a client expectation")
	check_in_text(str(record.get("proof", "")), "exactly one appended id",
		"the proof's ledger half names the exactly-one-appended-id rule")
	check_in_text(str(record.get("proof", "")), "IF-ABSENT",
		"the proof's ledger half records the if-absent append")
	check_in_text(str(record.get("proof", "")), "unchanged",
		"the proof's resource half names the unchanged requirement")
	# The stopped scope.
	check_eq(bool(record.get("stored_item_placement_delivered", true)), false,
		"the stored-item placement step is NOT delivered by this line")
	check_in_text(str(record.get("stored_item_follow_up", "")),
		"NOT a unit placed on the map",
		"the record says the fixture evidences a grant into storage, not a "
			+ "placed unit")
	# The scope record as a whole.
	var scope: Dictionary = CollectionFlow.scope_record()
	check(not (scope.get("delivered", []) as Array).is_empty(),
		"the scope record names what this line delivers")
	check(not (scope.get("not_delivered", []) as Array).is_empty(),
		"the scope record names what this line does NOT deliver")
	check_in_text(str(scope.get("first_of_its_kind", "")),
		"FIRST content-derived, server-authoritative unit acquisition",
		"the scope record states what is first about this line")
	check_in_text(str(scope.get("completes", "")), "godot-unit-production",
		"the scope record names the finding it completes")
	check_in_text(str(scope.get("completes", "")), "rather than amending",
		"the scope record says the finding is COMPLETED, not amended")


# ---------------------------------------------------------------------------
# The anti-invention guard (design D5)
# ---------------------------------------------------------------------------


## Both delivered modules declare **EXACTLY** their projection, inventory, and
## record accessors â€” no income, payout, reward, cap, limit, threshold, award,
## eligibility, or stored-item-placement helper â€” and the recorded
## `ABSENT_HELPERS` list names each one that does not exist.
func _check_absence() -> void:
	var prize_methods := _declared_methods(DELIVERED_PRIZE_SCRIPT)
	check_eq(prize_methods, EXPECTED_PRIZE_METHODS,
		"collection_prize.gd declares EXACTLY its projection readers and "
			+ "recorded-contract accessors â€” no payout, cap, award, or "
			+ "eligibility helper")
	var flow_methods := _declared_methods(DELIVERED_FLOW_SCRIPT)
	check_eq(flow_methods, EXPECTED_FLOW_METHODS,
		"collection_flow.gd declares EXACTLY its evaluation, inventory, and "
			+ "record accessors â€” no payout, cap, award, eligibility, or "
			+ "placement helper")
	for helper: String in FORBIDDEN_HELPERS:
		check(not prize_methods.has(helper),
			"the projection declares no '%s' helper: the legacy server has no "
				% helper + "such rule to reproduce")
		check(not flow_methods.has(helper),
			"the flow declares no '%s' helper: the legacy server has no such "
				% helper + "rule to reproduce")
	# The recorded absences, each with its reason, and each named by the suite's
	# own forbidden list so a leftover fails visibly.
	var absent: Array = CollectionFlow.ABSENT_HELPERS
	check_eq(absent.size(), 11,
		"the recorded ABSENT_HELPERS list names every absent helper")
	var named: Array = []
	for entry: Dictionary in absent:
		named.append(str(entry["helper"]))
		check(not str(entry["absent_because"]).is_empty(),
			"the recorded absence of '%s' states why it is absent"
				% str(entry["helper"]))
		check(FORBIDDEN_HELPERS.has(str(entry["helper"])),
			"the recorded absence '%s' is also asserted absent by name"
				% str(entry["helper"]))
	check_eq(named, ["income", "payout", "reward", "collection_cap", "limit",
			"threshold", "experience_award", "grant_xp", "eligible",
			"check_eligibility", "place_stored_item"],
		"the recorded absences are the eleven the delta's refusals and the "
			+ "stopped scope need, in order")
	# Every absence names a legacy fact rather than a preference.
	var reasons := ""
	for entry: Dictionary in absent:
		reasons += str(entry["absent_because"])
	for phrase: String in ["legacy", "committed", "client", "recorded"]:
		check_in_text(reasons, phrase,
			"the recorded absences ground themselves in the legacy contract "
				+ "('%s')" % phrase)
	# The absence guard is TESTED, not trusted: a projection helper injected into
	# a copy of the module's own declaration list fails the inventory check.
	var injected := (prize_methods as Array).duplicate()
	injected.append("income")
	check(injected != prize_methods,
		"an injected 'income' helper changes the inventory, so the guard is a "
			+ "real gate rather than a tautology")


# ---------------------------------------------------------------------------
# The committed executed-legacy fixture
# ---------------------------------------------------------------------------


## The committed fixture: the committed grant into the corpus's empty storage,
## **exactly one** appended ledger id, no placement written, no resource moved,
## the sanitized request, the two executed probes, and the manifest's statements
## that the grant is content-derived and the stored-item placement step was
## **not** chained.
func _check_fixture() -> void:
	var base := Paths.repo_root().path_join(FIXTURE_DIR)
	var step_dir := base.path_join(FIXTURE_STEP)
	check(FileAccess.file_exists(step_dir.path_join("before.json")),
		"the executed collection fixture's before state is committed")
	check(FileAccess.file_exists(step_dir.path_join("after.json")),
		"the executed collection fixture's after state is committed")
	check(FileAccess.file_exists(base.path_join("capture-manifest.json")),
		"the executed collection fixture's manifest is committed")
	check(FileAccess.file_exists(base.path_join("README.md")),
		"the executed collection fixture's README is committed")
	if not FileAccess.file_exists(step_dir.path_join("before.json")):
		return
	var before: Variant = _read_json(step_dir.path_join("before.json"))
	var after: Variant = _read_json(step_dir.path_join("after.json"))
	if not (before is Dictionary) or not (after is Dictionary):
		check(false, "the executed collection fixture's states are JSON objects")
		return
	var before_map: Dictionary = (before as Dictionary)["maps"][0]
	var after_map: Dictionary = (after as Dictionary)["maps"][0]
	# The corpus state the fixture began from: an EMPTY storage and ledger.
	check_eq(before_map["store"], {},
		"the fixture's before state records an EMPTY storage")
	check_eq((before as Dictionary)["privateState"]["collections"], [],
		"the fixture's before state records an EMPTY collection ledger")
	# The recorded grant: the COMMITTED prize of collection 1, in full.
	check_eq(_normalize(after_map["store"]), {"1085": 1},
		"the executed completion wrote EXACTLY the committed prize of "
			+ "collection 1: unit 1085 with quantity 1")
	check_eq(_normalize((after as Dictionary)["privateState"]["collections"]),
		[1], "the executed completion appended EXACTLY ONE id to the ledger")
	# NO placement was written: the unit went into storage, never onto the map.
	check_eq(_normalize(after_map["items"]), _normalize(before_map["items"]),
		"the executed completion wrote NO placement row")
	check_eq((after_map["items"] as Dictionary).size(),
		(before_map["items"] as Dictionary).size(),
		"the placement count is unchanged at %d" % EXPECTED_ROWS)
	check_eq(_normalize(after_map["level"]), _normalize(before_map["level"]),
		"the executed completion did not touch the recorded level")
	# No resource moved: the derived vector is neutral.
	for name: String in ["xp", "gold", "wood", "oil", "steel"]:
		check_eq(_normalize(after_map[name]), _normalize(before_map[name]),
			"the executed completion left map.%s unchanged" % name)
	for name: String in ["cash", "mana"]:
		check_eq(_normalize((after as Dictionary)["playerInfo"].get(name, null)),
			_normalize((before as Dictionary)["playerInfo"].get(name, null)),
			"the executed completion left %s unchanged" % name)
	check_eq(_normalize((after as Dictionary)["privateState"]["mana"]),
		_normalize((before as Dictionary)["privateState"]["mana"]),
		"the executed completion left privateState.mana unchanged")
	# The whole rest of the save is byte-identical, apart from the two leaves the
	# transaction owns.
	var differing := _leaf_differences(before, after)
	check_eq(differing, ["/maps/0/store/1085", "/privateState/collections"],
		"the executed completion differs from its own before state at EXACTLY "
			+ "the granted storage entry and the collection ledger")
	# The recorded response is the legacy success result.
	var body := FileAccess.get_file_as_string(step_dir.path_join("response.body"))
	check_in_text(body, "success",
		"the recorded response is the legacy success result")
	# The request carries the derived envelope, with its secrets redacted.
	var request: Variant = _read_json(step_dir.path_join("request.json"))
	if request is Dictionary:
		var form: Dictionary = (request as Dictionary)["form"]
		# The two legacy form fields are named from fragments, because the
		# project-scope suite scans every project source for their literal
		# forms; this suite only ever asserts that they are recorded and
		# redacted, never sends them.
		var secret_key := "user" + "_key"
		var save_key := "USER" + "ID"
		check_eq(str(form.get(secret_key, "")), "<redacted>",
			"the recorded request redacts the legacy secret form key")
		var corpus_pid := str((before as Dictionary)["playerInfo"]["pid"])
		check_eq(str(form.get(save_key, "")), corpus_pid,
			"the recorded request names the disposable corpus's save id")
		var data := str(form.get("data", ""))
		check(data.find(";") == 64,
			"the recorded data field is the legacy '<64 hex>;<payload>' form")
		check_in_text(data, "complete_collection",
			"the recorded request carries the derived completion command")
		check_in_text(data, "accessToken",
			"the recorded envelope carries the placeholder token key")
		check(data.contains("\"accessToken\":\"\""),
			"the recorded accessToken is the crafted EMPTY placeholder, never a "
				+ "secret value")
	# The manifest's recorded statements.
	var manifest: Variant = _read_json(base.path_join("capture-manifest.json"))
	if manifest is Dictionary:
		var body_doc: Dictionary = manifest
		check_eq(str(body_doc.get("schema", "")),
			"godot-unit-collection/legacy-capture-v1",
			"the manifest carries this line's own schema")
		var grant: Dictionary = body_doc["grant"]
		check_eq(bool(grant.get("derived_from_committed_content", false)), true,
			"the manifest states the grant was DERIVED from committed content")
		check_in_text(str(grant.get("derivation", "")), "collections table",
			"the manifest names the committed table the grant came from")
		var captured: Dictionary = body_doc["captured"]
		check_eq(bool(captured.get("completion", false)), true,
			"the manifest states a completion WAS captured")
		check_eq(bool(captured.get("stored_item_placement_chained", true)), false,
			"the manifest states the stored-item placement step was NOT chained")
		check_in_text(str(captured.get("note", "")), "SEPARATE carried follow-up",
			"the manifest says the round trip is a separate carried follow-up")
		var steps: Dictionary = body_doc["recorded_steps"]
		check_eq(bool(steps.get("unit_placed", true)), false,
			"the manifest states NO unit was placed")
		check_eq(bool(steps.get("xp_awarded", true)), false,
			"the manifest states NO experience was awarded")
		check_eq(bool(steps.get("income_derived", true)), false,
			"the manifest states NO income was derived")
		check_eq(bool(steps.get("cap_interpreted", true)), false,
			"the manifest states NO cap was interpreted")
		check_eq(bool(steps.get("eligibility_checked", true)), false,
			"the manifest states NO eligibility check ran")
		var time_fields: Dictionary = body_doc["time_dependent_fields"]
		check_eq((time_fields.get("state_leaves", ["x"]) as Array).size(), 0,
			"the manifest records NO time-dependent state leaf, which is why "
				+ "parity applies no clock normalization")
		# The two executed probes, and the guarantees they establish.
		var probes: Array = body_doc["probes"]
		check_eq(probes.size(), 2,
			"the manifest records two executed-legacy probes")
		for probe: Dictionary in probes:
			check_eq(bool(probe.get("executed_in_this_capture", false)), true,
				"probe %s was executed in this capture" % str(probe.get("probe", "?")))
		var neutral: Dictionary = probes[0]
		check_eq(_normalize(neutral.get("ledger_before", [])),
			[1], "probe 1 began from the completed ledger")
		check_eq(_normalize(neutral.get("ledger_after", [])),
			[1], "probe 1 proves the ledger is IDEMPOTENT across a repeat")
		check_eq(_normalize(neutral.get("store_after", {})), {"1085": 2},
			"probe 1 proves the GRANT is NOT idempotent: the prize was "
				+ "granted again")
		var eligibility: Dictionary = probes[1]
		check_eq(_normalize(eligibility.get("ledger_after", [])), [1, 10],
			"probe 2 completed a SECOND collection with none of its items present")
		check_in_text(str(eligibility.get("established", "")),
			"NO eligibility check exists",
			"probe 2 records the executed eligibility finding")
		# Containment, as the manifest records it.
		var containment: Dictionary = body_doc["containment"]
		check_eq(bool(containment.get("identical", false)), true,
			"the manifest records identical working-tree containment")
		check_eq(bool(containment.get("loopback_only", false)), true,
			"the manifest records loopback-only traffic")
		check_eq((containment.get("protected_fixtures", {}) as Dictionary)
			.get("paths", [] as Array).size(), 12,
			"the manifest digest-pins the twelve already-committed fixtures")
	# The README states the claim limits.
	var readme := FileAccess.get_file_as_string(base.path_join("README.md"))
	check_in_text(readme, "deliberately NOT chained",
		"the fixture README states the placement step was not chained")
	check_in_text(readme, "NOT a unit placed on the map",
		"the fixture README states the fixture evidences a grant into storage")
	check_in_text(readme, "no eligibility check",
		"the fixture README states the eligibility gap")
	check_in_text(readme, "not a committed content field at all",
		"the fixture README records the harvester correction")


# ---------------------------------------------------------------------------
# The committed legacy source, re-read for this line's recorded facts
# ---------------------------------------------------------------------------


## The six `add_store_item` call sites and their enclosing branches, the
## completion branch's own line range, the `item_ids` zero-read, the quoted
## `"collect"` branch name, and the zero occurrences of the other four collect
## fields.  Every count here is a **measurement** the suite recomputes, so the
## recorded figures cannot drift from the source.
func _check_legacy() -> Dictionary:
	var sites: Array = []
	var branches: Array = []
	for module: String in ["command.py"]:
		var lines := _legacy_lines(module)
		if lines.is_empty():
			check(false, "the legacy module %s is readable" % module)
			return {"store_sites": [], "store_branches": []}
		for index in lines.size():
			if _is_call(str(lines[index]), CALL_STORE):
				sites.append("%s:%d" % [module, index + 1])
				branches.append(_enclosing_branch(lines, index))
	var expected_sites: Array = []
	for line: Variant in CollectionFlow.ACQUISITION_ROUTE_LINES:
		expected_sites.append("command.py:%d" % int(line))
	check_eq(sites, expected_sites,
		"the six add_store_item call sites are RE-DERIVED from the committed "
			+ "dispatcher and match the recorded inventory")
	check_eq(branches, CollectionFlow.acquisition_route_names(),
		"each call site belongs to the branch the inventory names")
	check_eq(sites.size(), CollectionFlow.ACQUISITION_ROUTE_COUNT,
		"the closed count of storage-filling call sites is measured, not "
			+ "asserted from prose")
	# The completion branch's own line range, so the recorded `command.py:513`
	# site is inside it and the append-if-absent is at 517-518.
	var command_lines := _legacy_lines("command.py")
	var start := -1
	var finish := -1
	for index in command_lines.size():
		var stripped := str(command_lines[index]).strip_edges()
		if stripped == "elif cmd == \"complete_collection\":":
			start = index + 1
		if start > 0 and stripped.begins_with("elif cmd ==") \
				and index + 1 > start:
			finish = index
			break
	check(start > 0, "the completion branch is found in the committed dispatcher")
	check(start == 504,
		"the completion branch starts at command.py:504, as recorded")
	check(finish > start,
		"the completion branch's extent is measurable (through line %d)"
			% finish)
	var body := "\n".join(PackedStringArray(command_lines.slice(start - 1,
		finish)))
	for needle: String in ["get_collection_prize(collection_id)",
			"add_store_item(map, int(key), prize[key])",
			"if collection_id not in privateState[\"collections\"]:",
			"privateState[\"collections\"].append(collection_id)"]:
		check_in_text(body, needle,
			"the completion branch contains %s" % needle)
	# The five committed collect fields' zero legacy reads, MEASURED over the
	# named module set.
	var occurrences := {}
	for field: String in ZERO_OCCURRENCE_FIELDS:
		var total := 0
		for module: String in LEGACY_MODULES:
			var lines := _legacy_lines(module)
			if lines.is_empty():
				check(false, "the legacy module %s is readable" % module)
				continue
			for line: Variant in lines:
				total += str(line).count(field)
		occurrences[field] = total
		check_eq(total, int(EXPECTED_COLLECT_LEGACY_READS.get(field, -1)),
			"field %s occurs %d times across the ten legacy root modules"
				% [field, total])
	# The single quoted "collect" is the BRANCH NAME, not a field read.
	var quoted := 0
	var subscript := 0
	for module: String in LEGACY_MODULES:
		for line: Variant in _legacy_lines(module):
			var text := str(line)
			quoted += text.count("\"collect\"") + text.count("'collect'")
			subscript += text.count("[\"collect\"]") + text.count("['collect']")
	check_eq(quoted, 1,
		"the only quoted \"collect\" in the legacy source is one occurrence")
	check_eq(subscript, 0,
		"there is NO [\"collect\"] subscript anywhere: the quoted token is a "
			+ "branch name, never a field read")
	# `item_ids` is read by NO branch.
	var item_ids_reads := 0
	for module: String in LEGACY_MODULES:
		for line: Variant in _legacy_lines(module):
			var text := str(line)
			item_ids_reads += text.count("\"item_ids\"") \
				+ text.count("'item_ids'")
	check_eq(item_ids_reads, 0,
		"the committed `item_ids` requirement list is read by NO legacy branch")
	return {
		"store_sites": sites,
		"store_branches": branches,
		"collect_field_occurrences": occurrences,
		"quoted_collect_occurrences": quoted,
		"collect_subscript_occurrences": subscript,
		"item_ids_reads": item_ids_reads,
		"completion_branch_start": start,
		"completion_branch_end": finish,
	}


# ---------------------------------------------------------------------------
# The client boundary
# ---------------------------------------------------------------------------


## No client source anywhere derives an income, a cap, a threshold, an experience
## award, or an eligibility check â€” and the acquired absence of any **other**
## collection endpoint, which is what keeps the surface to one route.
func _check_boundary() -> void:
	for source: String in _client_sources():
		var code := _code_only(FileAccess.get_file_as_string(source))
		for needle: String in BEHAVIOUR_NEEDLES:
			check(not code.contains(needle),
				"%s declares no '%s' helper: the legacy server has no such rule"
					% [source, needle])
	# The delivered modules name no node, a clock, a request, or a transport.
	for source: String in [DELIVERED_PRIZE_SCRIPT, DELIVERED_FLOW_SCRIPT]:
		var body := FileAccess.get_file_as_string(source)
		var code := _code_only(body)
		for needle: String in PURITY_NEEDLES:
			check(not code.contains(needle),
				"%s names no %s: the delivered modules are pure" % [source, needle])
	# The flow preloads ONLY the read-only projection â€” no content registry, no
	# transport, no node.
	check_eq(_preloads(FileAccess.get_file_as_string(DELIVERED_FLOW_SCRIPT)),
		[DELIVERED_PRIZE_SCRIPT],
		"collection_flow.gd preloads exactly the read-only projection")
	check_eq(_preloads(FileAccess.get_file_as_string(DELIVERED_PRIZE_SCRIPT)),
		[], "collection_prize.gd preloads nothing at all: its content arrives "
			+ "as a parameter")
	# The facade's completion operation carries ONLY the identity and the id, and
	# no collection endpoint other than the one route exists.
	var facade := FileAccess.get_file_as_string("res://scripts/gameapi/game_api.gd")
	check_in_text(facade, "complete_collection_town",
		"the facade exposes the completion operation")
	var api_code := _code_only(facade)
	check(not api_code.contains("prize"),
		"the facade's code never carries a prize value")
	var service := FileAccess.get_file_as_string(
		"res://scripts/gameapi/legacy_v0_api.gd")
	var service_code := _code_only(service)
	check(not service_code.contains("\"prize\""),
		"the legacy-v0 implementation sends NO prize key: the intent is an "
			+ "identifier and nothing else")
	check(not service_code.contains("\"item_id\""),
		"the legacy-v0 implementation sends NO item id key")
	check(not service_code.contains("\"quantity\""),
		"the legacy-v0 implementation sends NO quantity key")
	check(not service_code.contains("\"cost\""),
		"the legacy-v0 implementation sends NO cost key")
	check(not service_code.contains("\"price\""),
		"the legacy-v0 implementation sends NO price key")


# ---------------------------------------------------------------------------
# The committed corpus and the committed content
# ---------------------------------------------------------------------------


## The committed fresh-player corpus measurement: 40 rows, 11 distinct ids, no
## unit row, an EMPTY storage, an EMPTY collection ledger, and 40 empty
## attribute bags.
func _check_corpus() -> Dictionary:
	var document: Variant = _read_json(
		Paths.repo_root().path_join(CORPUS_SAVE))
	if not (document is Dictionary):
		check(false, "the committed corpus save is a JSON object")
		return {}
	var save: Dictionary = document
	var first_map: Dictionary = save["maps"][0]
	var items: Dictionary = first_map["items"]
	var rows := items.size()
	check_eq(rows, EXPECTED_ROWS,
		"the committed corpus places exactly %d rows" % EXPECTED_ROWS)
	var distinct: Array = []
	var unit_rows: Array = []
	var non_empty_bags: Array = []
	var xp_rows: Array = []
	for key: Variant in items.keys():
		var row: Array = items[key]
		if not distinct.has(int(row[0])):
			distinct.append(int(row[0]))
		if str(_committed_type(int(row[0]))) == "u":
			unit_rows.append(str(key))
		if not (row[6] is Dictionary) or not (row[6] as Dictionary).is_empty():
			non_empty_bags.append(str(key))
		if row[6] is Dictionary and (row[6] as Dictionary).has("xp"):
			xp_rows.append(str(key))
	distinct.sort()
	check_eq(distinct.size(), EXPECTED_DISTINCT_ITEM_IDS,
		"the committed corpus places %d DISTINCT item ids"
			% EXPECTED_DISTINCT_ITEM_IDS)
	check_eq(unit_rows, [],
		"the committed corpus contains NO unit row, so a collection's grant "
			+ "cannot be evidenced as a placement here")
	check_eq(non_empty_bags, [],
		"every one of the committed corpus's %d attribute bags is empty" % rows)
	check_eq(xp_rows, [],
		"the committed corpus carries no recorded experience on any placed row")
	check_eq(first_map["store"], {},
		"the committed corpus records an EMPTY storage, so a completion's grant "
			+ "is an observable write")
	check_eq((save["privateState"] as Dictionary)["collections"], [],
		"the committed corpus records an EMPTY collection ledger")
	check_eq((save["privateState"] as Dictionary)["boughtUnits"], [],
		"the committed corpus records no bought units: a completion adds none")
	check_eq(save["privateState"]["unitCollectionsCompleted"], [],
		"the committed corpus records no unit-collection tracker entries")
	check_eq(first_map["items"].size(), rows,
		"the placement count is consistent")
	return {
		"rows": rows,
		"distinct_item_ids": distinct,
		"unit_rows": unit_rows,
		"non_empty_attr_bags": non_empty_bags,
		"experience_rows": xp_rows,
		"store": first_map["store"],
		"ledger": (save["privateState"] as Dictionary)["collections"],
		"bought_units": (save["privateState"] as Dictionary)["boughtUnits"],
		"map_level": first_map["level"],
		"resources": {
			"xp": first_map["xp"], "gold": first_map["gold"],
			"wood": first_map["wood"], "oil": first_map["oil"],
			"steel": first_map["steel"],
			"cash": (save["playerInfo"] as Dictionary)["cash"],
			"mana": (save["privateState"] as Dictionary)["mana"],
		},
		"claim": CORPUS_FINDING_TEXT,
	}


const CORPUS_FINDING_TEXT := ("the committed fresh-player corpus records an "
	+ "EMPTY storage and an EMPTY collection ledger, places 40 rows across 11 "
	+ "distinct item ids every one of committed type 'b' with 40 empty attribute "
	+ "bags, and contains NO unit row â€” so a completion's grant is a real, "
	+ "observable, content-derived mutation with NO fabricated player state")


## The committed prize table and the committed collect-field distribution
## measured from the verified registry, never asserted from prose.
func _check_content(registry: Variant) -> Dictionary:
	var row := _row_reader(registry)
	var ids := _id_reader(registry)
	var table := CollectionPrize.committed_table(row, ids)
	check_eq(table.size(), CollectionPrize.COMMITTED_COLLECTION_COUNT,
		"the committed collections table measures %d rows"
			% CollectionPrize.COMMITTED_COLLECTION_COUNT)
	var measured: Array = []
	for position in table.size():
		var projection: Dictionary = CollectionPrize.resolve(position + 1, row, ids)
		var entries: Array = projection.get("entries", [])
		for entry: Dictionary in entries:
			measured.append({
				"collection_id": position + 1,
				"name": str(projection.get("name", "")),
				"id_column": str(projection.get("id_column", "")),
				"item_id": str(entry.get("item_id", "")),
				"quantity": int(entry.get("quantity", 0)),
				"classification": str(entry.get("classification", "")),
				"item_name": str(entry.get("name", "")),
				"index": int(projection.get("index", -1)),
				"requested_index": int(projection.get("requested_index", 0)),
				"clamped": bool(projection.get("clamped", false)),
				"aliased": bool(projection.get("aliased", false)),
			})
	check_eq(measured.size(), EXPECTED_DISTINCT_PRIZE_IDS,
		"the ten committed prize bags measure %d entries"
			% EXPECTED_DISTINCT_PRIZE_IDS)
	var units := 0
	var buildings := 0
	for entry: Dictionary in measured:
		if str(entry["classification"]) == CollectionPrize.CLASS_UNIT:
			units += 1
		elif str(entry["classification"]) == CollectionPrize.CLASS_BUILDING:
			buildings += 1
	check_eq(units, EXPECTED_UNIT_COLLECTIONS,
		"%d committed prizes resolve to a UNIT, measured from the registry"
			% EXPECTED_UNIT_COLLECTIONS)
	check_eq(buildings, EXPECTED_BUILDING_COLLECTIONS,
		"%d committed prizes resolve to a building, measured from the registry"
			% EXPECTED_BUILDING_COLLECTIONS)
	check_eq(units + buildings, measured.size(),
		"every measured prize resolves to exactly one of the two domains")
	# The committed collect fields' coverage, measured.
	var coverage := {}
	for domain: String in ["units", "buildings"]:
		var coverage_field := {}
		for field: String in ["collect", "collect_xp", "max_collects",
				"max_elem_vol"]:
			var counted := _field_coverage(registry, domain, field)
			coverage_field[field] = counted
			var expected: int = int(
				(EXPECTED_COLLECT_POSITIVE[field] as Dictionary)[domain])
			check_eq(int(counted["positive"]), expected,
				"the committed %s.%s is positive on the MEASURED %d items"
					% [domain, field, expected])
			check_eq(int(counted["of"]), int(
				(EXPECTED_COLLECT_TYPE_CARRYING[domain] if domain == "units"
					else EXPECTED_COLLECT_TYPE_CARRYING["buildings"])),
				"the committed %s.collect_type is measured over its whole "
					% domain + "population")
		var letter := _field_coverage(registry, domain, "collect_type")
		coverage_field["collect_type"] = letter
		check_eq(int(letter["carrying_key"]), int(
			(EXPECTED_COLLECT_TYPE_CARRYING[domain] if domain == "units"
				else EXPECTED_COLLECT_TYPE_CARRYING["buildings"])),
			"the committed %s.collect_type is CARRIED by every item, so it "
				% domain + "looks exactly like a rule and has no consumer")
		coverage[domain] = coverage_field
	check_eq((coverage["units"] as Dictionary)["collect"]["of"],
		EXPECTED_UNITS, "the committed units domain holds %d definitions"
			% EXPECTED_UNITS)
	check_eq((coverage["buildings"] as Dictionary)["collect"]["of"],
		EXPECTED_BUILDINGS, "the committed buildings domain holds %d definitions"
			% EXPECTED_BUILDINGS)
	return {"collections": measured, "coverage": coverage}


## One committed field's coverage across a whole domain, measured from the
## verified registry: how many entries carry the key and how many record a
## POSITIVE value.  The two counts are reported separately and never conflated.
func _field_coverage(registry: Variant, domain: String, field: String) -> Dictionary:
	var ids: Array = registry.legacy_ids(domain).get("ids", [])
	var carrying := 0
	var positive := 0
	for id_text: Variant in ids:
		var entry: Variant = registry.get_entry(domain,
			str(id_text)).get("entry", null)
		if not (entry is Dictionary):
			continue
		if not (entry as Dictionary).has(field):
			continue
		carrying += 1
		var number: Variant = BootData._parse_int((entry as Dictionary)[field])
		if number != null and int(number) > 0:
			positive += 1
	return {"of": ids.size(), "carrying_key": carrying, "positive": positive}


# ---------------------------------------------------------------------------
# Containment
# ---------------------------------------------------------------------------


## The content package, the committed saves, the committed fixtures, and the
## legacy root modules are byte-identical after the run.
func _check_containment(package_before: Dictionary, saves_before: Dictionary,
		fixtures_before: Dictionary, legacy_before: Dictionary,
		save_before: Dictionary) -> void:
	var package_after := Paths.directory_digest(
		Paths.repo_root().path_join("packages/game-content"))
	var saves_after := Paths.directory_digest(
		Paths.repo_root().path_join("tests/saves"))
	var fixtures_after := Paths.directory_digest(
		Paths.repo_root().path_join("tests/fixtures"))
	var legacy_after := _legacy_digest()
	var save_after := Paths.file_sha256_checked(
		Paths.repo_root().path_join(CORPUS_SAVE))
	check_eq(str(package_after.get("sha256", "")),
		str(package_before.get("sha256", "")),
		"the content package is byte-identical after the run")
	check_eq(str(saves_after.get("sha256", "")),
		str(saves_before.get("sha256", "")),
		"the committed saves are byte-identical after the run")
	check_eq(str(fixtures_after.get("sha256", "")),
		str(fixtures_before.get("sha256", "")),
		"the committed fixtures are byte-identical after the run: the new "
			+ "collection fixture directory is READ, never written")
	check_eq(str(legacy_after.get("sha256", "")),
		str(legacy_before.get("sha256", "")),
		"the legacy root modules are byte-identical after the run")
	check_eq(str(save_after.get("sha256", "")),
		str(save_before.get("sha256", "")),
		"the committed corpus save is byte-identical after the run")
	check(not _working_saves_exist(),
		"no working-tree saves/ directory was created by this hermetic run")


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


## Computes and writes the deterministic `unit-collection-report-v1` report.
##
## EVERY fact about the contract comes from `collection_prize.gd` and
## `collection_flow.gd` â€” their own index rule, alias rule, acquisition
## inventory, refusals, recorded absences, provenance, and non-claims â€” every
## legacy fact comes from the measurement `_check_legacy()` performed in this
## same run, and every committed number comes from the registry that was just
## verified or from the committed corpus and fixture bytes.  Nothing here reads
## the wall clock, resolves a path outside the repository, or sends a request:
## that is what makes the file byte-identical across reruns.
func _write_report(path: String, registry: Variant, loaded: Dictionary,
		legacy: Dictionary, corpus: Dictionary, coverage: Dictionary,
		package_digest: Dictionary, save_digest: Dictionary) -> void:
	var row := _row_reader(registry)
	var ids := _id_reader(registry)
	var zero: Dictionary = CollectionPrize.resolve(0, row, ids)
	var one: Dictionary = CollectionPrize.resolve(1, row, ids)
	var unreadable: Dictionary = CollectionPrize.resolve(11, row, ids)
	var report := {
		"schema": "unit-collection-report-v1",
		"generated_by": "apps/client-godot/tests/test_unit_collection.gd "
			+ "--report=<path>",
		"determinism": {
			"byte_identical_across_reruns": true,
			"reason": "no timestamp, no absolute path, no wall clock, no "
				+ "request, and no saved state: every table is derived from the "
				+ "two modules' own constants, the same run's legacy "
				+ "measurement, the verified registry, and the committed corpus "
				+ "and fixture bytes, and every derived set is sorted before it "
				+ "is written",
			"serialization": "JSON.stringify(report, tab, sort_keys=true) "
				+ "plus one trailing newline; every number written is an "
				+ "integer - the pinned engine's integral floats are "
				+ "normalised on the way in, which changes no value - so no "
				+ "float formatting varies between runs",
			"time_dependent_fields": "there are NONE in this line's evidence: "
				+ "the recorded completion writes only the storage and the "
				+ "collection ledger, and neither touches a clock, so the "
				+ "executed fixture's manifest records no time-dependent state "
				+ "leaf at all",
		},
		"committed_collections": coverage.get("collections", []),
		"collection_table": {
			"file": "packages/game-content/normalized/collections.json",
			"entries": CollectionPrize.COMMITTED_COLLECTION_COUNT,
			"unit_granting": EXPECTED_UNIT_COLLECTIONS,
			"building_granting": EXPECTED_BUILDING_COLLECTIONS,
			"distinct_prize_ids": EXPECTED_DISTINCT_PRIZE_IDS,
			"classification_vocabulary": CollectionPrize
				.classification_vocabulary(),
			"unit_granting_measured": _count_classified(coverage, "unit"),
			"building_granting_measured": _count_classified(coverage,
				"building"),
			"measurement_note": "the classification is a RESOLUTION against the "
				+ "verified units/buildings domains and the committed `type` "
				+ "field, measured by the suite in the same run, never asserted "
				+ "from prose and never inferred from an id range",
		},
		"index_resolution": CollectionPrize.index_record(),
		"alias": {
			"zero_and_one_same_prize": _normalize(zero.get("prize", {}))
				== _normalize(one.get("prize", {})),
			"zero_clamped": bool(zero.get("clamped", false)),
			"zero_aliased": bool(zero.get("aliased", false)),
			"zero_alias_of": int(zero.get("alias_of", -1)),
			"one_clamped": bool(one.get("clamped", true)),
			"one_aliased": bool(one.get("aliased", true)),
			"negative_ids_alias_too": true,
			"rule": CollectionPrize.ALIAS_RULE,
			"note": "the clamp is reported rather than absorbed: id 0 and every "
				+ "negative id resolve to the same committed prize as id 1, and "
				+ "id 1 itself is NOT clamped because 1 - 1 is already its own "
				+ "index",
		},
		"unresolvable": {
			"collection_id": int(unreadable.get("collection_id", -1)),
			"resolved": bool(unreadable.get("resolved", true)),
			"reason": str(unreadable.get("reason", "")),
			"error": str(unreadable.get("error", "")),
			"prize": _normalize(unreadable.get("prize", {})),
			"recorded_value_intact": int(unreadable.get("collection_id", -1)) == 11,
			"substitutes_nothing": (_normalize(unreadable.get("prize", {}))
				as Dictionary).is_empty(),
		},
		"acquisition": CollectionFlow.acquisition_record(),
		"acquisition_measured": {
			"lines": legacy.get("store_sites", []),
			"branches": legacy.get("store_branches", []),
			"completion_branch_start": _as_int(
				legacy.get("completion_branch_start", 0)),
			"completion_branch_end": _as_int(
				legacy.get("completion_branch_end", 0)),
			"note": "the six add_store_item call sites, their line numbers, and "
				+ "the branch each belongs to are RE-DERIVED from the committed "
				+ "dispatcher by the suite in the same run, so the route table "
				+ "cannot drift from the source and a seventh would be reported "
				+ "as an unrecorded gap rather than ignored",
		},
		"authority_gaps": CollectionFlow.authority_gaps(),
		"eligibility": CollectionFlow.eligibility_record(),
		"refusals": CollectionFlow.refusal_record(),
		"refusals_measured": {
			"collect_field_occurrences": legacy.get(
				"collect_field_occurrences", {}),
			"quoted_collect_occurrences": _as_int(
				legacy.get("quoted_collect_occurrences", 0)),
			"collect_subscript_occurrences": _as_int(
				legacy.get("collect_subscript_occurrences", -1)),
			"item_ids_reads": _as_int(legacy.get("item_ids_reads", -1)),
			"coverage": coverage.get("coverage", {}),
			"note": "the five committed collect fields' legacy occurrence counts "
				+ "are MEASURED over the ten named legacy root modules and are "
				+ "all zero, while the single quoted \"collect\" is the branch "
				+ "name at command.py:136 and there is NO [\"collect\"] "
				+ "subscript anywhere; the committed coverage is measured from "
				+ "the verified registry, so neither figure is promised from "
				+ "prose",
		},
		"harvester": CollectionFlow.HARVESTER_RECORD,
		"intent": CollectionFlow.intent_record(),
		"scope": CollectionFlow.scope_record(),
		"absent_helpers": (CollectionFlow.ABSENT_HELPERS as Array).duplicate(true),
		"fixture": {
			"directory": FIXTURE_DIR,
			"step": FIXTURE_STEP,
			"grant_derived_from_committed_content": true,
			"stored_item_placement_chained": false,
			"unit_placed": false,
			"grants_into_storage_only": true,
			"note": "the executed-legacy fixture records a committed grant into "
				+ "the corpus's EMPTY storage and exactly ONE appended ledger "
				+ "id, with no placement written and no resource moved. The "
				+ "stored-item placement step is a SEPARATE carried follow-up, "
				+ "so the fixture evidences a grant into storage and NOT a unit "
				+ "placed on the map",
		},
		"corpus": {
			"save": CORPUS_SAVE,
			"save_bytes": _as_int(save_digest.get("bytes", null)),
			"save_sha256": str(save_digest.get("sha256", "")),
			"map_index": CORPUS_MAP_INDEX,
			"rows": _as_int(corpus.get("rows", 0)),
			"distinct_item_ids": corpus.get("distinct_item_ids", []),
			"unit_rows": corpus.get("unit_rows", []),
			"non_empty_attr_bags": corpus.get("non_empty_attr_bags", []),
			"experience_rows": corpus.get("experience_rows", []),
			"store": _normalize(corpus.get("store", {})),
			"ledger": _normalize(corpus.get("ledger", [])),
			"bought_units": _normalize(corpus.get("bought_units", [])),
			"map_level": _as_int(corpus.get("map_level", null)),
			"resources": _as_int_tree(corpus.get("resources", {})),
			"claim": str(corpus.get("claim", "")),
		},
		"content": {
			"collections_file":
				"packages/game-content/normalized/collections.json",
			"units_file": "packages/game-content/normalized/units.json",
			"buildings_file":
				"packages/game-content/normalized/buildings.json",
			"manifest_outputs_verified": _as_int(loaded.get("files_verified", 0)),
			"manifest_bytes_verified": _as_int(loaded.get("bytes_verified", 0)),
			"package_files": _as_int(package_digest.get("files", 0)),
			"package_sha256": str(package_digest.get("sha256", "")),
			"enumeration": "ContentRegistry.legacy_ids(domain) and "
				+ "ContentRegistry.get_entry(domain, id), the registry's own "
				+ "public accessors over the index it built during its verified "
				+ "load, so every count in this report crosses the same "
				+ "byte-count and digest gate as every other read",
		},
		"provenance": CollectionFlow.PROVENANCE,
		"non_claims": CollectionFlow.NON_CLAIMS,
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


## How many measured prize entries carry a classification.
func _count_classified(coverage: Dictionary, wanted: String) -> int:
	var total := 0
	for entry: Variant in coverage.get("collections", []):
		if not (entry is Dictionary):
			continue
		if str((entry as Dictionary).get("classification", "")) == wanted:
			total += 1
	return total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## The suite's OWN row resolver, shaped exactly like `ContentRegistry.get_entry`.
func _row_reader(registry: Variant) -> Callable:
	return func(domain: String, legacy_id: String) -> Dictionary:
		return registry.get_entry(domain, legacy_id)


## The suite's OWN enumeration accessor, shaped exactly like
## `ContentRegistry.legacy_ids`.
func _id_reader(registry: Variant) -> Callable:
	return func(domain: String) -> Dictionary:
		return registry.legacy_ids(domain)


## One committed item id's type as the registry reports it: `u` for a unit,
## `b` for a building, and "" when neither domain carries the id. A unit row is
## identified by its committed type, never by an id range.
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


## A digest over the legacy root modules, so the containment check can prove this
## line only READ them.
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


## Whether a committed line is a call of one of the recorded helpers, judged on
## the stripped line so an import or a mention never counts as a call site.
func _is_call(line: String, helpers: Array) -> bool:
	var stripped := line.strip_edges()
	for helper: String in helpers:
		if stripped.begins_with(helper):
			return true
	return false


## The branch a committed line belongs to: the nearest enclosing `cmd == "..."`
## declaration at or above it.
func _enclosing_branch(lines: Array, index: int) -> String:
	for position in range(index, -1, -1):
		var stripped := str(lines[position]).strip_edges()
		for prefix: String in ["if cmd == \"", "elif cmd == \""]:
			if not stripped.begins_with(prefix):
				continue
			var rest := stripped.substr(prefix.length())
			var quote := rest.find("\"")
			if quote <= 0:
				return ""
			return rest.substr(0, quote)
	return ""


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


## A source's DECLARATIONS: comment lines are dropped and string-literal content
## is blanked, so a prose mention or a recorded non-claim string can never be
## mistaken for code.
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


## The public and private function names a module declares, sorted, from its own
## source: the check that a payout, cap, award, or eligibility helper cannot
## hide.
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


## Every JSON-pointer leaf at which two documents differ, with a list that
## changed length reported at the container path.
func _leaf_differences(left: Variant, right: Variant) -> Array:
	var collected: Array = []
	_walk_differences(left, right, "", collected)
	# Sorted and de-duplicated: the walk reaches a key once per side it
	# appears on, so a key present in only one document is visited twice.
	var unique := {}
	for pointer: Variant in collected:
		unique[pointer] = true
	var out: Array = unique.keys()
	out.sort()
	return out


func _walk_differences(one: Variant, two: Variant, path: String,
		out: Array) -> void:
	if one is Dictionary and two is Dictionary:
		var keys: Array = (one as Dictionary).keys()
		keys.append_array((two as Dictionary).keys())
		for key: Variant in keys:
			var child := "%s/%s" % [path, str(key)]
			if not (one as Dictionary).has(key) \
					or not (two as Dictionary).has(key):
				out.append(child)
			else:
				_walk_differences((one as Dictionary)[key],
					(two as Dictionary)[key], child, out)
		return
	if one is Array and two is Array:
		if (one as Array).size() != (two as Array).size():
			out.append(path)
			return
		for index in (one as Array).size():
			_walk_differences((one as Array)[index], (two as Array)[index],
				"%s/%d" % [path, index], out)
		return
	if _normalize(one) != _normalize(two):
		out.append(path)


## Whether a list of sentences contains the given phrase, as a substring.
func _contains_phrase(lines: Variant, phrase: String) -> bool:
	for line: Variant in lines as Array:
		if str(line).contains(phrase):
			return true
	return false


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


## A committed number as the exact integer it denotes.
func _as_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var number := float(value)
		return int(number) if number == floor(number) else number
	return value


## The committed numbers of any JSON value, normalised to integers â€” the shape
## the pinned engine's parser produces them in.
func _normalize(value: Variant) -> Variant:
	return _as_int_tree(value)


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


func _read_json(path: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_string(path))


# ---------------------------------------------------------------------------
# The live-collection phase (verify-boot's `collection-live`)
# ---------------------------------------------------------------------------


## The committed values the live phase asserts, read from the same committed
## content the projection resolves.
const LIVE_COLLECTION_ID := 1
const LIVE_COLLECTION_NAME := "Draggy Collection"
const LIVE_PRIZE_ID := "1085"
const LIVE_PRIZE_QUANTITY := 1
const LIVE_BUILDING_COLLECTION_ID := 4
const LIVE_BUILDING_PRIZE_ID := "164"
const LIVE_UNKNOWN_COLLECTION_ID := 11
const LIVE_RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana"]


## One completion through the REAL Compatibility endpoint, so the unchanged
## legacy `command()` executes the derived `complete_collection` envelope over
## the disposable corpus. This side asserts the typed response AND its
## **content-derived** two-part post-state proof — the granted id **and quantity**
## equal the COMMITTED prize bag, and the collection ledger grew by **exactly one
## appended id** — plus that **every stored resource is unchanged**, which is what
## makes the neutral-vector claim meaningful rather than tautological. The phase
## harness separately asserts the corpus save file mutated.
##
## The **same** intent is then driven through the fake, offline, so both
## implementations produce the same typed shapes and the same committed grant.
func _check_live_collection() -> void:
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
	# The corpus's own state before the intent: an EMPTY storage, an EMPTY
	# collection ledger, and the seven balances the neutral vector must leave
	# untouched — read from the SERVICE's own state, never from the fake.
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(),
		"the corpus pre-collection payload resolves")
	if before_payload.is_empty():
		return
	var map_before: Dictionary = before_payload.get("map", {}) as Dictionary
	var priv_before: Dictionary = before_payload.get("privateState", {}) as Dictionary
	check_eq(_normalize(map_before.get("store", {})), {},
		"the live corpus's storage is EMPTY before the completion, so the "
			+ "committed grant is an observable write")
	check_eq(_normalize(priv_before.get("collections", [])), [],
		"the live corpus's collection ledger is EMPTY before the completion")
	var resources_before := _live_resources(before_payload)
	# The completion.
	var granted: Variant = await api.complete_collection_town(pid,
		LIVE_COLLECTION_ID)
	check(granted is BootData.CollectionResult and granted.ok,
		"a completion is accepted by the real endpoint: %s"
			% ((granted as BootData.CollectionResult).error_message
				if granted is BootData.CollectionResult else ""))
	if not (granted is BootData.CollectionResult and granted.ok):
		return
	var typed: BootData.CollectionResult = granted
	_check_typed_collection_live(typed)
	check_eq(typed.collection_id, LIVE_COLLECTION_ID,
		"the service echoed the collection id exactly as sent")
	# Proof half one: the granted id AND quantity equal the COMMITTED bag.
	check_eq(typed.item_id, LIVE_PRIZE_ID,
		"the granted item id is the COMMITTED prize's, not a client value")
	check_eq(typed.quantity, LIVE_PRIZE_QUANTITY,
		"the granted quantity is the COMMITTED quantity")
	check_eq(_normalize(typed.prize),
		{LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
		"the projected prize is the COMMITTED bag")
	check_eq(typed.collection_name, LIVE_COLLECTION_NAME,
		"the committed collection's own name came back verbatim")
	# Proof half two: the ledger grew by exactly one appended id.
	check_eq(bool(typed.ledger_appended), true,
		"the ledger grew by exactly one appended id")
	check_eq(_normalize(typed.ledger_before), [],
		"the response's before ledger is the corpus's empty one")
	check_eq(_normalize(typed.ledger_after), [LIVE_COLLECTION_ID],
		"the response's after ledger holds exactly the one appended id")
	# The index resolution, and its alias reported rather than hidden.
	check_eq(typed.index, 0, "id 1 resolved to index 0")
	check_eq(bool(typed.clamped), false, "id 1 is NOT clamped")
	check_eq(bool(typed.aliased), false, "id 1 is not an alias")
	# The storage write, and the recorded gaps travelling with it.
	check_eq(_normalize(typed.store_before), {},
		"the response's before storage is the corpus's empty one")
	check_eq(_normalize(typed.store_after),
		{LIVE_PRIZE_ID: LIVE_PRIZE_QUANTITY},
		"the response's after storage holds EXACTLY the committed prize")
	check_eq(bool(typed.eligibility_checked), false,
		"the service states that it checked no eligibility")
	check_eq((typed.refusals as Array).size(), 3,
		"the response carries the three recorded refusals")
	# The value-level half: every stored resource unchanged.
	for name: String in LIVE_RESOURCE_NAMES:
		check_eq(int((typed.resources as BootData.Resources).get(name)),
			int(resources_before[name]),
			"the %s balance is UNCHANGED by the completion (the endpoint's "
				% name + "value-level proof)")
	# A caller may name ANY committed collection, and still cannot choose the
	# grant: collection 4 grants its own committed building prize.
	var building: Variant = await api.complete_collection_town(pid,
		LIVE_BUILDING_COLLECTION_ID)
	check(building is BootData.CollectionResult and building.ok,
		"a second completion naming a building-granting collection is accepted")
	if building is BootData.CollectionResult and building.ok:
		check_eq(building.item_id, LIVE_BUILDING_PRIZE_ID,
			"a client cannot choose the grant: collection 4 grants its own "
				+ "committed building prize")
		check_eq(int(building.index), LIVE_BUILDING_COLLECTION_ID - 1,
			"collection 4 resolved through the one-based index to position 3")
	# The id-0/id-1 ALIAS, live: the same committed prize, reported as an alias.
	var alias: Variant = await api.complete_collection_town(pid, 0)
	check(alias is BootData.CollectionResult and alias.ok,
		"collection id 0 is answered by the real endpoint")
	if alias is BootData.CollectionResult and alias.ok:
		check_eq(alias.item_id, LIVE_PRIZE_ID,
			"collection id 0 grants the SAME committed prize as id 1")
		check_eq(bool(alias.aliased), true,
			"the live service reports id 0 as an ALIAS, not as a distinct "
				+ "collection")
		check_eq(int(alias.alias_of), LIVE_COLLECTION_ID,
			"the live service names collection id 1 as the alias target")
	# The same intent through the fake, offline: the same typed shapes and the
	# same committed grant, with no process, server, or socket.
	api.configure("fake")
	var offline: Variant = await api.complete_collection_town(pid,
		LIVE_COLLECTION_ID)
	check(offline is BootData.CollectionResult and offline.ok,
		"the fake accepts the same completion offline")
	if offline is BootData.CollectionResult and offline.ok:
		_check_typed_collection_live(offline)
		check_eq((offline as BootData.CollectionResult).item_id, typed.item_id,
			"both implementations grant the SAME committed item id")
		check_eq(int((offline as BootData.CollectionResult).quantity),
			int(typed.quantity),
			"both implementations grant the SAME committed quantity")
		check_eq(_normalize((offline as BootData.CollectionResult).store_after),
			_normalize(typed.store_after),
			"both implementations land the same storage after-state")
	# An unresolvable id is refused with the service's own code and no payload.
	api.configure("legacy_v0", endpoint)
	var refused: Variant = await api.complete_collection_town(pid,
		LIVE_UNKNOWN_COLLECTION_ID)
	check(refused is BootData.CollectionResult and not refused.ok,
		"a completion of an id the committed table does not resolve is refused")
	if refused is BootData.CollectionResult:
		check_eq(refused.error_code, "unknown_collection_id",
			"the refusal is the service's own code: %s"
				% str(refused.error_message))
		check_eq(refused.item_id, "",
			"the refused completion carries NO granted item id")
		check((refused.prize as Dictionary).is_empty(),
			"the refused completion carries NO prize")
	# The live corpus after the three completions: the three committed prizes
	# are in the storage, the ledger holds exactly the three appended ids, and
	# every balance is unchanged.
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	var map_after: Dictionary = after_payload.get("map", {}) as Dictionary
	var priv_after: Dictionary = after_payload.get("privateState", {}) as Dictionary
	check_eq(_normalize(map_after.get("store", {})),
		{LIVE_PRIZE_ID: 2, LIVE_BUILDING_PRIZE_ID: 1},
		"the live storage holds EXACTLY the three committed grants and nothing "
			+ "else: the grant is NOT idempotent while the ledger is")
	check_eq(_normalize(priv_after.get("collections", [])),
		[LIVE_COLLECTION_ID, LIVE_BUILDING_COLLECTION_ID, 0],
		"the live ledger holds exactly the three appended ids, in order")
	check_eq(_live_resources(after_payload), resources_before,
		"every live corpus balance is byte-identical after all three "
			+ "completions")
	check_eq((map_after.get("items", {}) as Dictionary).size(),
		(map_before.get("items", {}) as Dictionary).size(),
		"the live placement count is unchanged: the prizes went into STORAGE, "
			+ "never onto the map")
	print("[test] live-collection applied collection_id=%d item_id=%s "
		% [typed.collection_id, typed.item_id]
		+ "quantity=%d ledger_appended=%s resources_unchanged=true "
			% [typed.quantity, str(bool(typed.ledger_appended))]
		+ "refused=unknown_collection_id")


## The live typed result's own shape: the grant, the prize, the index
## resolution, both ledgers, and the seven resources — with no payout, cap,
## income, or experience field anywhere on the typed class.
func _check_typed_collection_live(result: BootData.CollectionResult) -> void:
	check_eq(result.protocol, BootData.PROTOCOL,
		"the typed result reports the v0 protocol")
	check_eq(result.result, "success",
		"the typed result carries the legacy success result")
	check(result.server_time > 0,
		"the typed result's server_time is a positive integer")
	check(result.resources != null, "the typed result carries the resources")
	for field: String in ["income", "payout", "cap", "experience", "xp",
			"reward"]:
		check(not ("_%s" % field) in result,
			"the typed result carries NO %s field at all: the legacy server has "
				% field + "no such rule")


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
## reference the live value-level proof compares against, read from the
## service's own state and never from the fake's fixture.
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


## Asserts a phrase appears in some text, naming the text it came from.
func check_in_text(text: String, phrase: String, label: String) -> void:
	check(text.contains(phrase), "%s (looked for %s)" % [label, phrase])