extends "res://tests/test_base.gd"
## Headless GameApi suite for the fake implementation (spec "Boot offline
## with the fake implementation", "Place through either implementation",
## "Purchase through either implementation", and "Store through either
## implementation"; tasks 3.1/3.2/3.3).
##
## Hermetic by construction: no Compatibility API is started — verify-boot
## runs this suite before any service exists — and the scope test restricts
## the compat endpoint and the HTTP request client to the legacy-v0
## implementation file, which this suite never selects. Expected values are
## read from the committed executed-legacy fixtures (read-only), including
## the placement, purchase, move, sell, store, and upgrade fixtures the six
## doubles mutate in memory over.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const FIXTURE_PLACE_BEFORE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/before.json"
const FIXTURE_PLACE_AFTER := \
	"tests/fixtures/godot-building-placement/steps/command_buy/after.json"
const FIXTURE_PURCHASE_BEFORE := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/before.json"
const FIXTURE_PURCHASE_AFTER := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/after.json"
const FIXTURE_MOVE_BEFORE := \
	"tests/fixtures/godot-building-move/steps/command_move/before.json"
const FIXTURE_MOVE_AFTER := \
	"tests/fixtures/godot-building-move/steps/command_move/after.json"
const FIXTURE_SELL_BEFORE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/before.json"
const FIXTURE_SELL_AFTER := \
	"tests/fixtures/godot-building-sell/steps/command_sell/after.json"
const FIXTURE_STORE_BEFORE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/before.json"
const FIXTURE_STORE_AFTER := \
	"tests/fixtures/godot-building-store/steps/command_store_item/after.json"
const FIXTURE_UPGRADE_BEFORE := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/before.json"
const FIXTURE_UPGRADE_AFTER := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/after.json"
const FIXTURE_CONSTRUCTION_BEFORE := \
	"tests/fixtures/godot-building-construction/steps/command_construction/before.json"
const FIXTURE_CONSTRUCTION_AFTER := \
	"tests/fixtures/godot-building-construction/steps/command_construction/after.json"
const FIXTURE_COLLECT_BEFORE := \
	"tests/fixtures/godot-building-collect/steps/command_collect/before.json"
const FIXTURE_COLLECT_AFTER := \
	"tests/fixtures/godot-building-collect/steps/command_collect/after.json"
const FIXTURE_EXPAND_BEFORE := \
	"tests/fixtures/godot-building-expand/steps/command_expand/before.json"
const FIXTURE_EXPAND_AFTER := \
	"tests/fixtures/godot-building-expand/steps/command_expand/after.json"
const FIXTURE_LEVEL_BEFORE := \
	"tests/fixtures/godot-building-xp/steps/command_level_up/before.json"
const FIXTURE_LEVEL_AFTER := \
	"tests/fixtures/godot-building-xp/steps/command_level_up/after.json"
## The executed-legacy queue fixture's four states: the push's before and after,
## and the pop's before and after. The pop's before state is the push's after
## state, so the pair is ONE recorded transaction.
const FIXTURE_QUEUE_PUSH_BEFORE := \
	"tests/fixtures/godot-unit-queues/steps/command_push_queue_unit/before.json"
const FIXTURE_QUEUE_PUSH_AFTER := \
	"tests/fixtures/godot-unit-queues/steps/command_push_queue_unit/after.json"
const FIXTURE_QUEUE_POP_BEFORE := \
	"tests/fixtures/godot-unit-queues/steps/command_pop_queue_unit/before.json"
const FIXTURE_QUEUE_POP_AFTER := \
	"tests/fixtures/godot-unit-queues/steps/command_pop_queue_unit/after.json"

## The committed corpus's real placed training producer: **id 26, Command
## Center, at map key 1**, with an EMPTY attribute bag. The instant the executed
## push stamped, which the double reuses instead of reading a clock.
const QUEUE_TARGET_MAP_KEY := 1
const QUEUE_TARGET_KEY := "1"
const QUEUE_TARGET_ROW := [26, 51, 41, 0, 0, [], {}, 1]
## A key that names no placement in the committed save.
const QUEUE_UNKNOWN_KEY := 9999999
## The committed corpus's seven stored balances, which both queue commands leave
## byte-identical (the derived neutral vector's own guarantee).
const QUEUE_CORPUS_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}

## The executed-legacy collect transaction's constants (fixture facts, read
## from the committed capture): the Tree decoration (item 905, 1x1) at legacy
## map key "2", anchored at `(53,39)`, whose row `[905, 53, 39, 0, 0, [], {},
## 1]` is mutated IN PLACE — the placement count stays 40, the key and cell are
## reused, and ONLY `item[3]` changes — while the content-derived payout
## `[0, 3, 0, 60, 0, 0, 0, 0]` lands in exactly two resource slots. The
## collection instant is the capture's own wall clock, so it is asserted as a
## positive integer and never by value.
const COLLECT_ITEM := 905
const COLLECT_INDEX := 2
const COLLECT_CELL_X := 53
const COLLECT_CELL_Y := 39
const COLLECT_ROW := [COLLECT_ITEM, 53, 39, 0, 0, [], {}, 1]
## The item's committed income fields in the loaded configuration (`collect`
## "20", `collect_type` "w", `collect_xp` "1", `max_collects` "0" — all
## string-encoded) and the payout they derive at the TOP committed rung, which
## is what every corpus row reaches because every corpus row records
## `item[3] == 0` and the elapsed time is therefore unbounded.
const COLLECT_AMOUNT := 20
const COLLECT_TYPE := "w"
const COLLECT_XP := 1
const COLLECT_CAP := 0
const COLLECT_PAYOUT := [0, 3, 0, 60, 0, 0, 0, 0]
const COLLECT_TIER := 3
## An integer index the map does not name (the endpoint's 404, resolved before
## execution) and index 0, which is never a real legacy key.
const COLLECT_UNKNOWN_INDEX := 9999
## A placed row the double can still resolve after the failed attempts, used to
## prove the refusals left the in-memory state uncorrupted: the Trees
## decoration at key 21 (item 930, the same committed income as the Tree).
const COLLECT_SPARE_INDEX := 21
const COLLECT_SPARE_ITEM := 930
## A THIRD income row the corpus leaves untouched (the second Trees
## decoration), used for the recovery check after the refusals: key 21 has
## already been collected by then, so its own clock reads as too early.
const COLLECT_RECOVERY_INDEX := 22
const COLLECT_RECOVERY_ITEM := 930
## The three refusals that no placed corpus row can produce, so the double's
## IN-MEMORY state carries a crafted row and (for the content two) a crafted
## config item — the client-side mirror of the compat suite's own accessor
## stub. The committed fixture is never written.
const COLLECT_CAPPED_INDEX := 4242
const COLLECT_CAPPED_ITEM := 960
const COLLECT_UNMAPPABLE_INDEX := 4243
const COLLECT_UNMAPPABLE_ITEM := 961
const COLLECT_BUILDING_INDEX := 4244
const COLLECT_FRESH_INDEX := 4245
## The first committed rung's threshold in SECONDS (5 committed minutes): a
## row stamped one second short of it reaches NO rung, which is the only
## `too_early` path the corpus itself cannot produce.
const COLLECT_FIRST_RUNG_SECONDS := 300

## The executed-legacy store transaction's constants (fixture facts, read
## from the committed capture): the Tree decoration (item 905, 1x1) at
## legacy map key "2", anchored at `(53,39)`, whose row
## `[905, 53, 39, 0, 0, [], {}, 1]` is popped while the fresh save's empty
## storage becomes `{"905": 1}` — the two writes of the one branch, landing
## together.
const STORE_ITEM := 905
const STORE_INDEX := 2
const STORE_ROW := [STORE_ITEM, 53, 39, 0, 0, [], {}, 1]
## The two other Turret I rows the double uses to prove that a SECOND store
## of the SAME item increments the existing entry instead of replacing it
## (the fresh save carries no second Tree, and the double never rewrites the
## committed fixture).
const STORE_SAME_ITEM_INDEX_A := 11
const STORE_SAME_ITEM_INDEX_B := 20
const STORE_SAME_ITEM := 22
## An unrelated, still-present row the double resolves after the failed
## attempts, proving the state was not corrupted by them.
const STORE_UNRELATED_INDEX := 12
const STORE_UNRELATED_ITEM := 23
## An index the map does not name (the endpoint's 404, resolved before
## execution), and index 0, which is never a real legacy key.
const STORE_UNKNOWN_INDEX := 9999

## The executed-legacy upgrade transaction's constants (fixture facts, read
## from the committed capture): the Wall I (item 23, 1x1) at legacy map key
## "12", anchored at `(45,49)`, whose row `[23, 45, 49, 0, 0, [], {}, 1]` is
## REPLACED IN PLACE by the Wall II (item 24) at the SAME key and the SAME
## cell with a fresh timestamp and the `{"nc": 0}` construction seed, while
## the bought-units list gains the new tier and every other row and every
## resource stays byte-identical.
const UPGRADE_ITEM := 23
const UPGRADE_TARGET := 24
const UPGRADE_INDEX := 12
const UPGRADE_ROW := [UPGRADE_ITEM, 45, 49, 0, 0, [], {}, 1]
const UPGRADE_CELL_X := 45
const UPGRADE_CELL_Y := 49
## The Tree decoration at legacy key 2: the committed configuration records
## `upgrades_to` `-1` for it, so it has NO resolvable next tier and must fail
## closed instead of becoming a bare sale.
const UPGRADE_NO_PATH_INDEX := 2
const UPGRADE_NO_PATH_ITEM := 905
## The Wall II's own next tier, the same configuration fact the double
## derives a second time: upgrading the SAME key again replaces it in place
## once more — which is the point, because the key is reused.
const UPGRADE_SECOND_TARGET := 25
## An integer index the map does not name (the endpoint's 404, resolved
## before execution), and index 0, which is never a real legacy key.
const UPGRADE_UNKNOWN_INDEX := 9999

## The executed-legacy construction transaction's constants (fixture facts,
## read from the committed capture): the Turret I (item 22, 1x1) at legacy map
## key "11", anchored at `(58,48)`, whose row `[22, 58, 48, 0, 0, [], {}, 1]`
## is mutated IN PLACE — the placement count stays 40, the key and cell are
## reused — so it ends up carrying the recorded countdown equal to the item's
## committed `build_time` plus a click counter of 1, which is the item's
## `clicks_to_build`, while every other row and every resource stays
## byte-identical. The start instant is the capture's own wall clock, so it is
## asserted as a positive integer and never by value.
const CONSTRUCTION_ITEM := 22
const CONSTRUCTION_INDEX := 11
const CONSTRUCTION_CELL_X := 58
const CONSTRUCTION_CELL_Y := 48
const CONSTRUCTION_ROW := [CONSTRUCTION_ITEM, 58, 48, 0, 0, [], {}, 1]
## The item's committed build time in the loaded configuration
## (`build_time` "5" for the Turret I) and its committed click requirement
## (`clicks_to_build` "1") — the two facts the double derives for itself and
## the service derives server-side, and the two the executed fixture's
## recorded countdown and click counter confirm.
const CONSTRUCTION_BUILD_TIME := 5
const CONSTRUCTION_CLICKS := 1
## The three actions of the endpoint's closed vocabulary, in the order a
## construction walks them.
const CONSTRUCTION_START := "start"
const CONSTRUCTION_CLICK := "click"
const CONSTRUCTION_FINISH := "finish"
## An integer index the map does not name (the endpoint's 404, resolved
## before execution) and index 0, which is never a real legacy key.
const CONSTRUCTION_UNKNOWN_INDEX := 9999
## A second placed Turret I, still addressable, used to prove that a failed
## intent left the in-memory state uncorrupted.
const CONSTRUCTION_SPARE_INDEX := 20
## An item the committed configuration records `build_time` "0" for (a Worker
## I): the double must refuse a start on a row naming it with the endpoint's
## own `no_build_time` rather than coercing a zero that legacy would turn into
## a whole-attribute-bag clear. The corpus places no such row, so the suite
## parks one in the double's IN-MEMORY state (the committed fixture is never
## written) — the client-side mirror of the compat suite's own stub.
const CONSTRUCTION_NO_TIME_ITEM := 1001

## The executed-legacy expand transaction's constants (fixture facts, read from
## the committed capture): expansion id **0** — a FREE row of the 98-entry
## POSITIONAL `expansion_prices` schedule, so its derived debit is the ALL-ZERO
## eight-slot vector and **no** stored resource moves. The ledger
## `[35, 36, 45, 46]` becomes `[35, 36, 45, 46, 0]`: grown by exactly one entry,
## the sent id appended at the END, the existing entries unchanged, in order,
## and never deduplicated, while all 40 items, the level, the storage, the
## private state, and the player info are byte-identical. The fixture's first
## captured state in this family records NO time-dependent state leaf at all.
const EXPAND_ID := 0
const EXPAND_SECOND_ID := 1
const EXPAND_LAST_FREE_ID := 3
const EXPAND_OWNED := [35, 36, 45, 46]
const EXPAND_OWNED_AFTER := [35, 36, 45, 46, 0]
const EXPAND_PRICE := {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0}
const EXPAND_DEBIT := [0, 0, 0, 0, 0, 0, 0, 0]
## The committed row the schedule prices at index 4 (2500/5/1/1) and at its
## saturated tail (index 97, 100000/20/15/30) — the bounds of the derived
## debit's magnitude, asserted against the loaded configuration.
const EXPAND_PRICED_ID := 4
const EXPAND_PRICED_PRICE := {"coins": 2500, "cash": 5, "neighbors": 1,
	"inventory_qte": 1}
const EXPAND_SATURATED_ID := 97
## The first FREE index, and the ids the committed schedule does not price or
## cannot resolve structurally.
const EXPAND_OUT_OF_RANGE_ID := 98
const EXPAND_NEGATIVE_ID := -1
## A real owned id the double's own schedule says nothing purchasable about, so
## it proves the requirements refusal on committed content.
const EXPAND_BLOCKED_OWNED_ID := 45
## The executed-legacy level transaction (building-xp, fixture facts): the
## carried command is `level_up` with the DERIVED level and a NEUTRAL vector, and
## **the recorded level and every stored resource are UNCHANGED** — because at
## the committed corpus the level the curve derives for `xp 4` already equals the
## recorded level 1, so the executed command rewrote an identical value and every
## leaf of the save stayed the same. The capture is therefore itself the evidence
## for the endpoint's `level_already_current` refusal and for the corpus's
## self-consistency under the ONE-BASED reading.
const LEVEL_CORPUS_XP := 4
const LEVEL_CORPUS_LEVEL := 1
## The experience that makes the committed curve derive a level ABOVE the
## recorded one, so the advancement is derivable. The committed curve's first
## five thresholds are 0, 40, 60, 100, 200, so `200` places level 5
## ("Villager") and level 6 ("Scout") is next at 350.
const LEVEL_DISAGREE_XP := 200
const LEVEL_DERIVED := 5
const LEVEL_NEXT := 6
const LEVEL_NEXT_NAME := "Scout"
const LEVEL_NEXT_THRESHOLD := 350
const LEVEL_NEXT_REMAINING := 150
const LEVEL_DERIVED_NAME := "Villager"
const LEVEL_DERIVED_THRESHOLD := 200
## A second disagreement, for the response's own curve facts at a different rung.
const LEVEL_LOW_XP := 100
const LEVEL_LOW_DERIVED := 4
## A recorded level the stored experience cannot reach, for the
## `xp_below_threshold` refusal. Level 50's committed threshold is far above 4
## experience, so a save recording it is a disagreement nothing can advance.
const LEVEL_UNREACHABLE := 50
## The curve floor a stub installs so the content failure the committed curve
## cannot produce becomes reachable offline. It replaces the curve's own first
## threshold (`0`) with the curve's second (`40`), which keeps the ladder
## strictly increasing and puts the floor above the corpus's `xp 4`.
const LEVEL_STUBBED_FLOOR := 40
## The committed curve's own shape, asserted against the double's loaded
## configuration rather than against a restatement.
const LEVEL_ENTRIES := 100
const LEVEL_FIRST_THRESHOLDS := [0, 40, 60, 100, 200, 350, 550, 800]
const LEVEL_FINAL_THRESHOLD := 2016089205
const LEVEL_TOP := 100
const LEVEL_TOP_NAME := "Conqueror"


func run_scenario() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("fake")
	check_eq(api.implementation_name(), "fake",
		"implementation switch selects the fake")

	var expected := _fixture_saves()
	check(expected.size() > 0, "fixture save list carries at least one save")
	if expected.is_empty():
		return

	var sessions: Variant = await api.list_sessions()
	check(sessions is BootData.SaveListResult,
		"list_sessions returns the typed result")
	if not (sessions is BootData.SaveListResult):
		return
	var save_list: BootData.SaveListResult = sessions
	check(save_list.ok, "fake session list resolves offline: %s"
		% save_list.error_message)
	if not save_list.ok:
		return
	check_eq(save_list.protocol, BootData.PROTOCOL, "protocol is compat-v0")
	check_eq(save_list.game_version, "alpha 0.02",
		"game version equals the fixture save list")
	check_eq(save_list.saves.size(), expected.size(),
		"save count equals the fixture save list")
	for i in expected.size():
		var want: Dictionary = expected[i]
		var got: BootData.SaveInfo = save_list.saves[i]
		check_eq(got.id, str(want["id"]), "save %d id equals the fixture" % i)
		check_eq(got.name, str(want["name"]),
			"save %d name equals the fixture" % i)
		check_eq(got.xp, int(want["xp"]), "save %d xp equals the fixture" % i)
		check_eq(got.level, int(want["level"]),
			"save %d level equals the fixture" % i)
	check(save_list.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")

	var user_id := str(expected[0]["id"])
	var boot: Variant = await api.get_bootstrap(user_id)
	check(boot is BootData.BootstrapResult,
		"get_bootstrap returns the typed result")
	if not (boot is BootData.BootstrapResult):
		return
	var result: BootData.BootstrapResult = boot
	check(result.ok, "fake bootstrap resolves offline: %s"
		% result.error_message)
	if result.ok:
		check(result.summary != null, "bootstrap carries a typed summary")
		if result.summary != null:
			check_eq(result.summary.user_id, user_id,
				"summary names the requested save")
			check_eq(result.summary.name, str(expected[0]["name"]),
				"summary name equals the fixture save")
			check_eq(result.summary.level, int(expected[0]["level"]),
				"summary level equals the fixture save")
			check_eq(result.summary.xp, int(expected[0]["xp"]),
				"summary xp equals the fixture save")
		check(result.config != null and not result.config.raw.is_empty(),
			"config payload is wrapped and non-empty")
		check(result.player_info != null,
			"player_info payload is wrapped")
		if result.player_info != null:
			check_eq(result.player_info.player_name,
				str(expected[0]["name"]),
				"typed player name equals the fixture save name")
		check_eq(result.protocol, BootData.PROTOCOL,
			"bootstrap protocol is compat-v0")

	var missing: Variant = await api.get_bootstrap("")
	check(missing is BootData.BootstrapResult
		and not missing.ok and missing.summary == null,
		"empty save id fails without a summary")
	if missing is BootData.BootstrapResult:
		check_eq(missing.error_code, "missing_user_id",
			"empty save id names the failure")

	var unknown: Variant = await api.get_bootstrap("does-not-exist-0000")
	check(unknown is BootData.BootstrapResult
		and not unknown.ok and unknown.summary == null,
		"unknown save id fails without a summary")
	if unknown is BootData.BootstrapResult:
		check_eq(unknown.error_code, "unknown_user_id",
			"unknown save id names the failure")

	await _check_placement(api, user_id)
	await _check_purchase(api, user_id)
	await _check_move(api, user_id)
	await _check_sell(api, user_id)
	await _check_store(api, user_id)
	await _check_upgrade(api, user_id)
	await _check_construction(api, user_id)
	await _check_collect(api, user_id)
	await _check_expand(api, user_id)
	await _check_level(api, user_id)
	await _check_queue(api, user_id)

	info("fake implementation resolved %d save(s) with no server and no socket"
		% save_list.saves.size())


## The committed fixture save list (expected values), read directly.
func _fixture_saves() -> Array:
	var path := Paths.repo_root().path_join(FIXTURE_SAVE_LIST)
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "fixture save list is readable: " + path)
	if handle == null:
		return []
	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	handle = null
	if not (parsed is Dictionary):
		check(false, "fixture save list is a JSON object")
		return []
	var typed: Dictionary = parsed
	if not (typed.get("saves") is Array):
		check(false, "fixture save list carries a saves array")
		return []
	return typed["saves"]


## Placement double coverage (task 3.1, design D8): typed shapes, success
## semantics derived from the committed fixture, the endpoint's structured
## failure codes, and the intent counter — all with no server and no
## socket. Expected values come from the placement fixture and the config
## facts pinned by the change (item 1 `House I`: `w30`, clicks 1, no
## friend assist; item 2 `Wood Factory I`: `w50`, clicks 1, friend
## assistable).
func _check_placement(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_PLACE_BEFORE)
	var after := _read_fixture_object(FIXTURE_PLACE_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var epoch := _fixture_placement_epoch(before, after)
	check(epoch > 0, "fixture records a positive placement timestamp")
	var requests_before: int = api.placement_requests

	# --- success: House I at the fixture anchor -------------------------
	var placed: Variant = await api.place_building(user_id, 1, 51, 39)
	check(placed is BootData.PlacementResult,
		"place_building returns the typed result")
	if not (placed is BootData.PlacementResult):
		return
	var first: BootData.PlacementResult = placed
	check(first.ok, "fake placement resolves offline: %s"
		% first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "placement protocol is compat-v0")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.placement != null, "typed placement entry is carried")
	check(first.resources != null, "typed resources are carried")
	if first.placement == null or first.resources == null:
		return
	check_eq(first.placement.item_id, 1, "entry names the placed item")
	check_eq(first.placement.x, 51, "entry anchor x matches the intent")
	check_eq(first.placement.y, 39, "entry anchor y matches the intent")
	check_eq(first.placement.orientation, 0,
		"entry orientation matches the intent")
	check_eq(first.placement.player, 1, "entry player team is 1 (design D4)")
	check_eq(first.placement.store.size(), 0, "fresh entry store is empty")
	check(first.placement.attr == {"nc": 0},
		"item 1 attr is the legacy clicks_to_build rule {\"nc\": 0}")
	check_eq(first.placement.timestamp, epoch,
		"entry timestamp is the fixture epoch (deterministic double)")
	# Cost map: w30 lands on wood only; legacy clamp never triggers here.
	check_eq(first.resources.wood, int(before_map["wood"]) - 30,
		"cost w applied to wood")
	check_eq(first.resources.gold, int(before_map["gold"]), "gold unchanged")
	check_eq(first.resources.oil, int(before_map["oil"]), "oil unchanged")
	check_eq(first.resources.steel, int(before_map["steel"]), "steel unchanged")
	check_eq(first.resources.xp, int(before_map["xp"]), "xp unchanged")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash unchanged")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana unchanged")

	# --- structured failures: endpoint codes, no partial payload --------
	var ghost: Variant = await api.place_building("ghost-0000", 1, 51, 39)
	_check_placement_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.place_building("", 1, 51, 39)
	_check_placement_failure(empty, "missing_user_id", "empty save id")
	var unknown_item: Variant = await api.place_building(
		user_id, 999999999, 51, 39)
	_check_placement_failure(unknown_item, "unknown_item_id", "unknown item id")
	var off_grid: Variant = await api.place_building(user_id, 1, 100, 39)
	_check_placement_failure(off_grid, "invalid_coordinates",
		"anchor past the grid edge")
	var negative: Variant = await api.place_building(user_id, 1, 51, -1)
	_check_placement_failure(negative, "invalid_coordinates",
		"negative anchor")

	# --- second success: state accumulated, failures applied nothing ----
	var second: Variant = await api.place_building(user_id, 2, 60, 39)
	check(second is BootData.PlacementResult
		and second.ok and second.placement != null and second.resources != null,
		"second placement succeeds after the failed attempts")
	if second is BootData.PlacementResult and second.ok:
		var typed: BootData.PlacementResult = second
		check_eq(typed.placement.item_id, 2, "second entry names item 2")
		check_eq(typed.placement.x, 60, "second entry anchor x")
		check_eq(typed.placement.y, 39, "second entry anchor y")
		check_eq(typed.placement.timestamp, epoch,
			"second entry reuses the deterministic fixture epoch")
		check(typed.placement.attr == {"si": [], "nc": 0},
			"item 2 attr adds si (friend_assistable) to nc")
		# w30 + w50 accumulate; nothing from the failed attempts.
		check_eq(typed.resources.wood, int(before_map["wood"]) - 30 - 50,
			"costs accumulate across placements only")
		check_eq(typed.resources.gold, int(before_map["gold"]),
			"failed attempts applied no cost")

	check_eq(api.placement_requests, requests_before + 7,
		"every placement call increments the intent counter exactly once")
	info("placement double resolved success and 5 structured failures "
		+ "with no server and no socket")


## Every placement failure carries the endpoint's code and no partial
## payload (design D5).
func _check_placement_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.PlacementResult,
		label + " returns the typed result")
	if not (result is BootData.PlacementResult):
		return
	var typed: BootData.PlacementResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.placement == null, label + " carries no partial placement")
	check(typed.resources == null, label + " carries no partial resources")


## Purchase double coverage (task 3.2, design D9): typed shapes, the
## documented in-memory semantics over the committed purchase fixture's
## before-state (cash-only config price, the legacy `max(…, 0)` clamp, the
## storage increment, the bought-units record), the endpoint's structured
## failure codes, and the intent counter — all with no process, no server,
## and no socket. Expected values come from the purchase fixture: item 105
## "Victory Arch" `costs {"c": 5}`, the fresh save's `cash` 5, an empty
## storage, and an empty `boughtUnits`.
func _check_purchase(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_PURCHASE_BEFORE)
	var after := _read_fixture_object(FIXTURE_PURCHASE_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	# The executed transaction, read from the fixture (never written): the
	# after-state's three changed leaves are the whole oracle. The JSON
	# transport widens numbers to floats, so the expected mapping is
	# canonicalized to the typed int form the client actually receives.
	var executed_store := {"105": int(after_map["store"]["105"])}
	check_eq(before_map["store"], {}, "the fixture before storage is empty")
	check_eq(executed_store, {"105": 1},
		"the fixture after storage carries item 105 with quantity 1")
	check_eq(int(before["playerInfo"]["cash"]), 5,
		"the fixture before cash is exactly the 5 price")
	check_eq(int(after["playerInfo"]["cash"]), 0,
		"the fixture after cash is zero under the legacy clamp")
	var requests_before: int = api.purchase_requests

	# --- success: Victory Arch for the fresh player's 5 cash -----------
	var bought: Variant = await api.purchase_item(user_id, 105)
	check(bought is BootData.PurchaseResult,
		"purchase_item returns the typed result")
	if not (bought is BootData.PurchaseResult):
		return
	var first: BootData.PurchaseResult = bought
	check(first.ok, "fake purchase resolves offline: %s"
		% first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "purchase protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02",
		"the game version is the fixture's")
	check(first.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.resources != null, "typed resources are carried")
	if first.resources == null:
		return
	check_eq(first.store, executed_store,
		"the double reproduces the executed fixture's storage exactly")
	check_eq(first.resources.cash, int(after["playerInfo"]["cash"]),
		"the derived cash price is deducted with the legacy clamp")
	check_eq(first.resources.gold, int(before_map["gold"]), "gold unchanged")
	check_eq(first.resources.wood, int(before_map["wood"]), "wood unchanged")
	check_eq(first.resources.oil, int(before_map["oil"]), "oil unchanged")
	check_eq(first.resources.steel, int(before_map["steel"]), "steel unchanged")
	check_eq(first.resources.xp, int(before_map["xp"]), "xp unchanged")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana unchanged")

	# --- structured failures: endpoint codes, no partial payload --------
	var ghost: Variant = await api.purchase_item("ghost-0000", 105)
	_check_purchase_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.purchase_item("", 105)
	_check_purchase_failure(empty, "missing_user_id", "empty save id")
	var unknown_item: Variant = await api.purchase_item(user_id, 999999999)
	_check_purchase_failure(unknown_item, "unknown_item_id", "unknown item id")
	# House I is priced in wood: this command's price is not derivable, so
	# the endpoint (and the double) fail closed with `costs_not_cash`
	# rather than inventing a price.
	var wood: Variant = await api.purchase_item(user_id, 1)
	_check_purchase_failure(wood, "costs_not_cash", "wood-priced item")

	# --- second success: storage accumulated, the failures applied nothing
	var second: Variant = await api.purchase_item(user_id, 106)
	check(second is BootData.PurchaseResult and second.ok,
		"a second purchase succeeds after the failed attempts")
	if second is BootData.PurchaseResult and second.ok:
		var typed: BootData.PurchaseResult = second
		check_eq(typed.store, {"105": 1, "106": 1},
			"the storage increment accumulates (Fountain cash 10 clamps)")
		check_eq(typed.resources.cash, 0,
			"a second price above the remaining cash clamps at zero")

	check_eq(api.purchase_requests, requests_before + 6,
		"every purchase call increments the intent counter exactly once")
	info("purchase double resolved 2 successes and 4 structured failures "
		+ "with no server and no socket")


## Every purchase failure carries the endpoint's code and no partial
## payload (design D5).
func _check_purchase_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.PurchaseResult,
		label + " returns the typed result")
	if not (result is BootData.PurchaseResult):
		return
	var typed: BootData.PurchaseResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.store.is_empty(), label + " carries no partial storage")
	check(typed.resources == null, label + " carries no partial resources")


## Move double coverage (building-move task 3.2, design D8): the documented
## in-memory semantics over the committed move fixture's before-state (the
## index resolves against the save's own placements, ONLY `x`/`y` are
## written in place, no key is added, removed, or re-keyed, and the derived
## neutral resource vector leaves every resource untouched), the endpoint's
## structured failure codes, and the intent counter — all with no process, no
## server, and no socket.
##
## The executed transaction, read from the fixture (never written): the
## after-state's one changed leaf (`items["11"][2]`: 48 -> 47) is the whole
## oracle, and the double's in-memory row must equal it exactly.
func _check_move(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_MOVE_BEFORE)
	var after := _read_fixture_object(FIXTURE_MOVE_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the fixture before map carries 40 placements")
	check_eq(after_items.size(), 40,
		"the fixture after map still carries 40 placements (a move adds none)")
	# The JSON transport widens the save's ints to floats on the pinned
	# engine, so the expected rows are canonicalized to the typed int form
	# the client actually receives (the same tolerance the shared placement
	# parser documents).
	var moved_before := _typed_row(before_items["11"])
	var moved_after := _typed_row(after_items["11"])
	check_eq(moved_before, [22, 58, 48, 0, 0, [], {}, 1],
		"the fixture anchors the Turret I at (58,48) under key 11")
	check_eq(moved_after, [22, 58, 47, 0, 0, [], {}, 1],
		"the fixture moves it to (58,47) and changes nothing else")
	check_eq(before_map["gold"], after_map["gold"],
		"the executed move left gold unchanged")
	check_eq(before_map["wood"], after_map["wood"],
		"the executed move left wood unchanged")
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed move left cash unchanged (the derived vector is neutral)")
	var requests_before: int = api.move_requests

	# --- success: Turret I from key 11 to (58,47) ------------------
	var moved: Variant = await api.move_building(user_id, 11, 58, 47)
	check(moved is BootData.PlacementResult,
		"move_building returns the typed result")
	if not (moved is BootData.PlacementResult):
		return
	var first: BootData.PlacementResult = moved
	check(first.ok, "fake move resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "move protocol is compat-v0")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.placement != null, "typed placement entry is carried")
	check(first.resources != null, "typed resources are carried")
	if first.placement == null or first.resources == null:
		return
	# The double reproduces the executed transaction's row byte-for-byte.
	check_eq(first.placement.item_id, 22,
		"the moved entry names the Turret I")
	check_eq(first.placement.x, 58, "the moved entry's x matches the intent")
	check_eq(first.placement.y, 47, "the moved entry's y matches the intent")
	check_eq(first.placement.timestamp, int(moved_after[3]),
		"the moved entry keeps its row timestamp (never restamped)")
	check_eq(first.placement.orientation, int(moved_after[4]),
		"the moved entry keeps its orientation")
	check_eq(first.placement.store, [], "the moved entry keeps its store")
	check_eq(first.placement.attr, {}, "the moved entry keeps its attr")
	check_eq(first.placement.player, int(moved_after[7]),
		"the moved entry keeps its player field")
	# The neutral derived price vector means the resource bag is the fresh
	# save's own values (design D2) — never a computed delta.
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is unchanged by the neutral vector")
	check_eq(first.resources.wood, int(before_map["wood"]),
		"wood is unchanged by the neutral vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is unchanged by the neutral vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is unchanged by the neutral vector")
	check_eq(first.resources.xp, int(before_map["xp"]),
		"xp is unchanged by the neutral vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is unchanged by the neutral vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is unchanged by the neutral vector")

	# --- the no-op cell is the CLIENT's refusal, never the double's:
	# the endpoint enforces structural validity only, so the double accepts
	# it exactly as the service does.
	var noop: Variant = await api.move_building(user_id, 11, 58, 47)
	check(noop is BootData.PlacementResult and noop.ok,
		"the double accepts a repeated target (the client refuses it)")
	if noop is BootData.PlacementResult and noop.ok:
		check_eq(noop.placement.y, 47,
			"the repeated target writes the same cell again")

	# --- structured failures: endpoint codes, no partial payload ---
	var ghost: Variant = await api.move_building("ghost-0000", 11, 58, 47)
	_check_move_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.move_building("", 11, 58, 47)
	_check_move_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.move_building(user_id, 9999, 58, 47)
	_check_move_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var off_grid: Variant = await api.move_building(user_id, 11, 100, 47)
	_check_move_failure(off_grid, "invalid_coordinates",
		"anchor past the grid edge")
	var negative: Variant = await api.move_building(user_id, 11, 58, -1)
	_check_move_failure(negative, "invalid_coordinates",
		"negative anchor")

	# --- the failures applied nothing: the row is still the moved one ---
	var reread: Variant = await api.move_building(user_id, 11, 58, 47)
	check(reread is BootData.PlacementResult and reread.ok,
		"the double still resolves after the failed attempts")
	if reread is BootData.PlacementResult and reread.ok:
		check_eq(reread.placement.y, 47,
			"the failed attempts moved nothing else")

	check_eq(api.move_requests, requests_before + 8,
		"every move_building call increments the intent counter exactly once")
	info("move double resolved the executed fixture's row plus 5 structured "
		+ "failures with no server and no socket")


## The committed eight-field row in the typed form the client receives:
## every integral float (the JSON transport's width) becomes an int, and
## nothing else is touched. The nested `store`/`attr` structures are carried
## as-is, so only the positional fields are canonicalized.
func _typed_row(value: Variant) -> Array:
	if not (value is Array):
		return []
	var row: Array = []
	for element: Variant in (value as Array):
		row.append(int(element) if (element is int or element is float) \
			else element)
	return row


## Every move failure carries the endpoint's code and no partial payload
## (design D5) — including the 404 `unknown_item_index`, which stands in
## for legacy's silent no-op early return.
func _check_move_failure(result: Variant, code: String, label: String) -> void:
	check(result is BootData.PlacementResult,
		label + " returns the typed result")
	if not (result is BootData.PlacementResult):
		return
	var typed: BootData.PlacementResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.placement == null, label + " carries no partial placement")
	check(typed.resources == null, label + " carries no partial resources")


## Sell double coverage (building-sell task 3.2, design D8): the documented
## in-memory semantics over the committed sell fixture's before-state (the
## index resolves against the save's own placements, ONLY that row is
## deleted — no re-keying, no storage write, no bookkeeping — and the derived
## neutral resource vector leaves every resource untouched), the endpoint's
## structured failure codes, and the intent counter — all with no process, no
## server, and no socket.
##
## The executed transaction, read from the fixture (never written): the
## after-state's one removed key (`items["20"]`, the Turret I anchored at
## `(41,48)`) with every other row byte-identical is the whole oracle, and
## the double's response must equal it exactly.
func _check_sell(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_SELL_BEFORE)
	var after := _read_fixture_object(FIXTURE_SELL_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the sell fixture before map carries 40 placements")
	check_eq(after_items.size(), 39,
		"the executed sale left 39 placements (exactly one row removed)")
	check(after_items.has("20") == false,
		"the executed sale left no row under key 20")
	# The removed row, in the typed form the client receives.
	var removed_before := _typed_row(before_items["20"])
	check_eq(removed_before, [22, 41, 48, 0, 0, [], {}, 1],
		"the fixture anchors the Turret I at (41,48) under key 20")
	# Every OTHER row is byte-identical: the one write a sale performs is the
	# one delete (design D8).
	var other_keys: Array = []
	for key: Variant in before_items:
		if str(key) != "20":
			other_keys.append(str(key))
	other_keys.sort()
	var untouched := true
	for key: String in other_keys:
		if _typed_row(before_items[key]) != _typed_row(after_items[key]):
			untouched = false
	check(untouched,
		"the executed sale changed no other row (39 rows stay byte-identical)")
	# The neutral derived vector means the resource bag is unchanged, and
	# the sale touches no storage and no player state (design D2/D8).
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		check_eq(before_map[key], after_map[key],
			"the executed sale left %s unchanged" % key)
	check_eq(after_map["store"], {},
		"the executed sale left storage empty (it touches no storage)")
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed sale left cash unchanged (no refund is claimed)")
	check_eq(before["privateState"]["mana"], after["privateState"]["mana"],
		"the executed sale left mana unchanged")
	check_eq(before["privateState"]["boughtUnits"],
		after["privateState"]["boughtUnits"],
		"the executed sale left boughtUnits unchanged")
	check_eq(after["privateState"]["deadHeroes"], {},
		"the executed sale left deadHeroes empty (the combat reason is never "
		+ "reached)")
	var requests_before: int = api.sell_requests

	# --- success: Turret I at key 20 ---------------------------------
	var sold: Variant = await api.sell_building(user_id, 20)
	check(sold is BootData.SellResult,
		"sell_building returns the typed result")
	if not (sold is BootData.SellResult):
		return
	var first: BootData.SellResult = sold
	check(first.ok, "fake sale resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "sell protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02",
		"the game version is the fixture's")
	check(first.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.removed != null, "the removed row is carried")
	check(first.resources != null, "typed resources are carried")
	if first.removed == null or first.resources == null:
		return
	# The response carries the row AS READ BEFORE EXECUTION (design D5).
	check_eq(first.removed.item_id, 22, "the removed row names the Turret I")
	check_eq(first.removed.x, 41, "the removed row carries its saved x")
	check_eq(first.removed.y, 48, "the removed row carries its saved y")
	check_eq(first.removed.timestamp, 0,
		"the removed row keeps the save's timestamp (never restamped)")
	check_eq(first.removed.orientation, 0,
		"the removed row keeps its orientation")
	check_eq(first.removed.store, [], "the removed row keeps its store")
	check_eq(first.removed.attr, {}, "the removed row keeps its attr")
	check_eq(first.removed.player, 1,
		"the removed row keeps the player's team field")
	# The neutral derived vector means the resource bag is the fresh save's
	# own values (design D2) — never a computed delta, and no refund.
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is unchanged by the neutral vector")
	check_eq(first.resources.wood, int(before_map["wood"]),
		"wood is unchanged by the neutral vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is unchanged by the neutral vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is unchanged by the neutral vector")
	check_eq(first.resources.xp, int(before_map["xp"]),
		"xp is unchanged by the neutral vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is unchanged by the neutral vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is unchanged by the neutral vector")

	# --- the stale index: the row this very call removed is gone, so the
	# endpoint's pre-execution resolution (design D4) answers 404 rather
	# than reporting a sale that never happened.
	var stale: Variant = await api.sell_building(user_id, 20)
	_check_sell_failure(stale, "unknown_item_index",
		"a stale index after the removal")

	# --- structured failures: endpoint codes, no partial payload ----
	var ghost: Variant = await api.sell_building("ghost-0000", 11)
	_check_sell_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.sell_building("", 11)
	_check_sell_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.sell_building(user_id, 9999)
	_check_sell_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var zero: Variant = await api.sell_building(user_id, 0)
	_check_sell_failure(zero, "unknown_item_index",
		"index 0 (never a real legacy key)")

	# --- a second success: only the NAMED row goes, so another key still
	# resolves and the state is not corrupted by the first removal.
	var second: Variant = await api.sell_building(user_id, 11)
	check(second is BootData.SellResult and second.ok,
		"a second sale succeeds after the failed attempts")
	if second is BootData.SellResult and second.ok:
		var typed: BootData.SellResult = second
		check_eq(typed.removed.item_id, 22,
			"the second removed row names the other Turret I")
		check_eq(typed.removed.x, 58,
			"the second removed row carries its own saved x")
		check_eq(typed.removed.y, 48,
			"the second removed row carries its own saved y")
		check_eq(typed.resources.gold, int(before_map["gold"]),
			"the second sale also leaves gold unchanged")

	# --- the failures applied nothing: key 11 went, key 20 is still gone
	# and every other row still resolves.
	var third: Variant = await api.sell_building(user_id, 12)
	check(third is BootData.SellResult and third.ok,
		"an unrelated row still resolves after the failed attempts")
	if third is BootData.SellResult and third.ok:
		check_eq((third as BootData.SellResult).removed.item_id, 23,
			"the unrelated row resolves to its own item (state not corrupted)")

	check_eq(api.sell_requests, requests_before + 8,
		"every sell_building call increments the intent counter exactly once")
	info("sell double resolved the executed fixture's removal plus 4 "
		+ "structured failures with no server and no socket")


## Every sell failure carries the endpoint's code and no partial payload
## (design D5) — including the 404 `unknown_item_index`, which stands in for
## legacy's silent early return.
func _check_sell_failure(result: Variant, code: String, label: String) -> void:
	check(result is BootData.SellResult,
		label + " returns the typed result")
	if not (result is BootData.SellResult):
		return
	var typed: BootData.SellResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.removed == null, label + " carries no partial removed row")
	check(typed.resources == null, label + " carries no partial resources")


## Store double coverage (building-store task 3.2, design D8): the documented
## in-memory semantics over the committed store fixture's before-state (the
## index resolves against the save's own placements, ONLY that row is popped
## and its item's storage entry incremented by legacy's default quantity of
## exactly 1, NOTHING ELSE is written — including the bought-units list,
## which the legacy branch deliberately never touches — and the derived
## neutral resource vector leaves every resource unchanged), the endpoint's
## structured failure codes, and the intent counter — all with no process, no
## server, and no socket.
##
## The executed transaction, read from the fixture (never written): the
## after-state's two changed leaves (`items["2"]` gone, `store["905"] == 1`)
## are the whole oracle, and the double's response must equal them exactly.
func _check_store(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_STORE_BEFORE)
	var after := _read_fixture_object(FIXTURE_STORE_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the store fixture before map carries 40 placements")
	check_eq(after_items.size(), 39,
		"the executed store left 39 placements (exactly one row popped)")
	check(after_items.has("2") == false,
		"the executed store left no row under key 2")
	# The popped row, in the typed form the client receives.
	var removed_before := _typed_row(before_items["2"])
	check_eq(removed_before, STORE_ROW,
		"the fixture anchors the Tree at (53,39) under key 2")
	# The other half of the move: the storage mapping gains exactly that
	# item's id with legacy's default quantity of 1.
	check_eq(before_map["store"], {},
		"the store fixture before storage is empty")
	check_eq({"905": int(after_map["store"]["905"])}, {"905": 1},
		"the executed store put item 905 in storage with quantity 1")
	check_eq(int(after_map["store"].size()), 1,
		"the executed store added exactly one storage entry")
	# Every OTHER row is byte-identical: the one pop is the only map write.
	var other_keys: Array = []
	for key: Variant in before_items:
		if str(key) != "2":
			other_keys.append(str(key))
	other_keys.sort()
	var untouched := true
	for key: String in other_keys:
		if _typed_row(before_items[key]) != _typed_row(after_items[key]):
			untouched = false
	check(untouched,
		"the executed store changed no other row (39 rows stay byte-identical)")
	# The neutral derived vector means the resource bag is unchanged, and the
	# whole private state is too — the legacy branch calls no bookkeeping
	# helper, so `boughtUnits` stays empty (design D2/D8, reproduced exactly).
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		check_eq(before_map[key], after_map[key],
			"the executed store left %s unchanged" % key)
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed store left cash unchanged (no cost is claimed)")
	check_eq(before["privateState"]["mana"], after["privateState"]["mana"],
		"the executed store left mana unchanged")
	check_eq(before["privateState"]["boughtUnits"],
		after["privateState"]["boughtUnits"],
		"the executed store left boughtUnits unchanged ([] — the branch "
		+ "deliberately writes no bookkeeping)")
	var requests_before: int = api.store_requests

	# --- success: the Tree at key 2 ----------------------------------
	var stored: Variant = await api.store_building(user_id, STORE_INDEX)
	check(stored is BootData.StoreResult,
		"store_building returns the typed result")
	if not (stored is BootData.StoreResult):
		return
	var first: BootData.StoreResult = stored
	check(first.ok, "fake store resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "store protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02",
		"the game version is the fixture's")
	check(first.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.removed != null, "the removed row is carried")
	check(first.resources != null, "typed resources are carried")
	if first.removed == null or first.resources == null:
		return
	# The response carries the row AS READ BEFORE EXECUTION (design D4/D5)
	# and the FULL post-execution storage mapping.
	check_eq(first.removed.item_id, STORE_ITEM,
		"the removed row names the Tree")
	check_eq(first.removed.x, 53, "the removed row carries its saved x")
	check_eq(first.removed.y, 39, "the removed row carries its saved y")
	check_eq(first.removed.timestamp, 0,
		"the removed row keeps the save's timestamp (never restamped)")
	check_eq(first.removed.orientation, 0, "the removed row keeps its orientation")
	check_eq(first.removed.store, [], "the removed row keeps its store")
	check_eq(first.removed.attr, {}, "the removed row keeps its attr")
	check_eq(first.removed.player, 1,
		"the removed row keeps the player's team field")
	check_eq(first.store, {"905": 1},
		"the double reproduces the executed fixture's storage mapping exactly")
	# The neutral derived vector means the resource bag is the fresh save's
	# own values (design D2) — never a computed delta, and no storing cost.
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is unchanged by the neutral vector")
	check_eq(first.resources.wood, int(before_map["wood"]),
		"wood is unchanged by the neutral vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is unchanged by the neutral vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is unchanged by the neutral vector")
	check_eq(first.resources.xp, int(before_map["xp"]),
		"xp is unchanged by the neutral vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is unchanged by the neutral vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is unchanged by the neutral vector")

	# --- the stale index: the row this very call popped is gone, so the
	# endpoint's pre-execution resolution (design D3) answers 404 rather
	# than reporting a store that never happened.
	var stale: Variant = await api.store_building(user_id, STORE_INDEX)
	_check_store_failure(stale, "unknown_item_index",
		"a stale index after the pop")

	# --- structured failures: endpoint codes, no partial payload ----
	var ghost: Variant = await api.store_building("ghost-0000", STORE_INDEX)
	_check_store_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.store_building("", STORE_INDEX)
	_check_store_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.store_building(
		user_id, STORE_UNKNOWN_INDEX)
	_check_store_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var zero: Variant = await api.store_building(user_id, 0)
	_check_store_failure(zero, "unknown_item_index",
		"index 0 (never a real legacy key)")

	# --- a second store of the SAME item: the existing entry is
	# INCREMENTED, not replaced, and the pre-existing Tree entry survives —
	# the whole mapping is what the response reports, so the client does no
	# arithmetic of its own.
	var same_first: Variant = await api.store_building(
		user_id, STORE_SAME_ITEM_INDEX_A)
	check(same_first is BootData.StoreResult and same_first.ok,
		"the first Turret I stores")
	if same_first is BootData.StoreResult and same_first.ok:
		var typed_a: BootData.StoreResult = same_first
		check_eq(typed_a.store, {"905": 1, "22": 1},
			"the mapping keeps the Tree and adds the Turret I with quantity 1")
		check_eq(typed_a.removed.item_id, STORE_SAME_ITEM,
			"the first same-item row names the Turret I")
	var same_second: Variant = await api.store_building(
		user_id, STORE_SAME_ITEM_INDEX_B)
	check(same_second is BootData.StoreResult and same_second.ok,
		"a second store of the same item succeeds")
	if same_second is BootData.StoreResult and same_second.ok:
		var typed_b: BootData.StoreResult = same_second
		check_eq(typed_b.store, {"905": 1, "22": 2},
			"the second store increments the existing entry instead of "
			+ "replacing it")
		check_eq(typed_b.removed.item_id, STORE_SAME_ITEM,
			"the second same-item row names the other Turret I")
		check_eq(typed_b.removed.x, 41,
			"the second same-item row carries its own saved x")
		check_eq(typed_b.removed.y, 48,
			"the second same-item row carries its own saved y")
		check_eq(typed_b.resources.gold, int(before_map["gold"]),
			"the second store also leaves gold unchanged")

	# --- the failures applied nothing: key 2 and key 11 are gone, and
	# every other row still resolves to its own item (state not corrupted).
	var unrelated: Variant = await api.store_building(
		user_id, STORE_UNRELATED_INDEX)
	check(unrelated is BootData.StoreResult and unrelated.ok,
		"an unrelated row still resolves after the failed attempts")
	if unrelated is BootData.StoreResult and unrelated.ok:
		check_eq((unrelated as BootData.StoreResult).removed.item_id,
			STORE_UNRELATED_ITEM,
			"the unrelated row resolves to its own item (state not corrupted)")

	check_eq(api.store_requests, requests_before + 9,
		"every store_building call increments the intent counter exactly once")
	info("store double resolved the executed fixture's two-sided move plus 4 "
		+ "structured failures with no server and no socket")


## Every store failure carries the endpoint's code and no partial payload
## (design D5) — including the 404 `unknown_item_index`, which stands in for
## legacy's silent early return, and a storage mapping that must never be
## reported from a failed response.
func _check_store_failure(result: Variant, code: String, label: String) -> void:
	check(result is BootData.StoreResult,
		label + " returns the typed result")
	if not (result is BootData.StoreResult):
		return
	var typed: BootData.StoreResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.removed == null, label + " carries no partial removed row")
	check(typed.store.is_empty(), label + " carries no partial storage mapping")
	check(typed.resources == null, label + " carries no partial resources")


## Upgrade double coverage (building-upgrade task 3.2, design D8): the
## documented in-memory semantics over the committed upgrade fixture's
## before-state (the index resolves against the save's own placements, the
## target tier is DERIVED from the committed configuration's own
## `upgrades_to` reference — never from the caller — the row is REPLACED IN
## PLACE at the same key and cell with a fresh timestamp and the purchase
## half's `{"nc": 0}` seed, the bought-units list gains the new tier, and the
## derived neutral resource vector leaves every resource unchanged), the
## endpoint's structured failure codes, and the intent counter — all with no
## process, no server, and no socket.
##
## The executed transaction, read from the fixture (never written): the
## after-state's single replaced key (`items["12"]`, the Wall I at `(45,49)`
## becoming the Wall II at the SAME cell) plus `boughtUnits` gaining the new
## tier while the placement count and every other row and resource stay
## byte-identical is the whole oracle, and the double's response must equal
## it exactly.
func _check_upgrade(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_UPGRADE_BEFORE)
	var after := _read_fixture_object(FIXTURE_UPGRADE_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the upgrade fixture before map carries 40 placements")
	check_eq(after_items.size(), 40,
		"the executed upgrade kept 40 placements (the key is REUSED)")
	check(after_items.has("12"),
		"the executed upgrade left the row at key 12 (in place)")
	# The two rows the executed pair produced, in the typed form the client
	# receives.
	var row_before := _typed_row(before_items["12"])
	var row_after := _typed_row(after_items["12"])
	check_eq(row_before, UPGRADE_ROW,
		"the fixture anchors the Wall I at (45,49) under key 12")
	check_eq(int(row_after[0]), UPGRADE_TARGET,
		"the executed upgrade put the Wall II at that same key")
	check_eq([int(row_after[1]), int(row_after[2])],
		[UPGRADE_CELL_X, UPGRADE_CELL_Y],
		"the executed upgrade reused the very same cell")
	check(int(row_after[3]) > 0,
		"the executed upgrade stamped a fresh positive wall-clock timestamp")
	check_eq(row_after[4], 0, "the fresh row carries the orientation")
	check_eq(row_after[5], [], "the fresh row's store is empty")
	var seeded: Variant = row_after[6]
	check(seeded is Dictionary and (seeded as Dictionary).size() == 1 \
			and int((seeded as Dictionary)["nc"]) == 0,
		"the fresh row carries the clicks_to_build construction seed")
	check_eq(int(row_after[7]), 1, "the fresh row carries the player's team field")
	# The other 39 rows are byte-identical: the one in-place replacement is
	# the only map write.
	var other_keys: Array = []
	for key: Variant in before_items:
		if str(key) != "12":
			other_keys.append(str(key))
	other_keys.sort()
	var untouched := true
	for key: String in other_keys:
		if _typed_row(before_items[key]) != _typed_row(after_items[key]):
			untouched = false
	check(untouched,
		"the executed upgrade changed no other row (39 rows stay "
		+ "byte-identical)")
	# The neutral derived vector means the resource bag and the storage are
	# unchanged, and the purchase half's bought-units record is the one other
	# write the executed transaction made.
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		check_eq(before_map[key], after_map[key],
			"the executed upgrade left %s unchanged" % key)
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed upgrade left cash unchanged (no cost is claimed)")
	check_eq(before["privateState"]["mana"], after["privateState"]["mana"],
		"the executed upgrade left mana unchanged")
	check_eq(after_map["store"], {},
		"the executed upgrade left storage empty (it touches no storage)")
	check_eq(before["privateState"]["boughtUnits"], [],
		"the executed upgrade started from an empty bought-units list")
	var recorded_bought: Array = []
	for each: Variant in (after["privateState"]["boughtUnits"] as Array):
		recorded_bought.append(int(each))
	check_eq(recorded_bought, [UPGRADE_TARGET],
		"the executed upgrade recorded the new tier in boughtUnits")
	var requests_before: int = api.upgrade_requests

	# --- success: the Wall I at key 12 -> the Wall II at the same cell --
	var upgraded: Variant = await api.upgrade_building(user_id, UPGRADE_INDEX)
	check(upgraded is BootData.UpgradeResult,
		"upgrade_building returns the typed result")
	if not (upgraded is BootData.UpgradeResult):
		return
	var first: BootData.UpgradeResult = upgraded
	check(first.ok, "fake upgrade resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL, "upgrade protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02", "the game version is the fixture's")
	check(first.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")
	check_eq(first.result, "success", "legacy result string is reported")
	check(first.removed != null, "the pre-execution row is carried")
	check(first.upgraded != null, "the post-execution row is carried")
	check(first.resources != null, "typed resources are carried")
	if first.removed == null or first.upgraded == null \
			or first.resources == null:
		return
	# The response carries BOTH sides: the row AS READ BEFORE EXECUTION and
	# the row the purchase half wrote (design D5).
	check_eq(_boot_row(first.removed), UPGRADE_ROW,
		"the removed row is the executed fixture's pre-execution row")
	check_eq(first.removed.item_id, UPGRADE_ITEM, "the removed row names the Wall I")
	check_eq(first.removed.timestamp, 0,
		"the removed row keeps the save's timestamp (never restamped)")
	check_eq(first.removed.orientation, 0, "the removed row keeps its orientation")
	check_eq(first.removed.store, [], "the removed row keeps its store")
	check_eq(first.removed.attr, {}, "the removed row keeps its attr")
	check_eq(first.removed.player, 1,
		"the removed row keeps the player's team field")
	check_eq(first.upgraded.item_id, UPGRADE_TARGET,
		"the upgraded row names the derived target tier (Wall II)")
	check_eq(first.upgraded.x, UPGRADE_CELL_X,
		"the upgraded row reuses the pre-execution x")
	check_eq(first.upgraded.y, UPGRADE_CELL_Y,
		"the upgraded row reuses the pre-execution y")
	check_eq(first.upgraded.timestamp, int(row_after[3]),
		"the upgraded row is stamped with the capture's recorded epoch "
		+ "(the deterministic double never reads the wall clock)")
	check_eq(first.upgraded.orientation, int(row_after[4]),
		"the upgraded row carries the row's own orientation")
	check_eq(first.upgraded.store, [], "the upgraded row's store is fresh and empty")
	check_eq(first.upgraded.attr, {"nc": 0},
		"the upgraded row carries the construction seed and nothing else")
	check_eq(first.upgraded.player, int(row_after[7]),
		"the upgraded row carries the row's own player field")
	# The neutral derived vector means the resource bag is the fresh save's
	# own values (design D4) — never a computed delta, and no upgrade cost.
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is unchanged by the neutral vector")
	check_eq(first.resources.wood, int(before_map["wood"]),
		"wood is unchanged by the neutral vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is unchanged by the neutral vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is unchanged by the neutral vector")
	check_eq(first.resources.xp, int(before_map["xp"]),
		"xp is unchanged by the neutral vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is unchanged by the neutral vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is unchanged by the neutral vector")
	# The purchase half's bookkeeping: the target tier is recorded exactly
	# once, which is the fixture's own `boughtUnits` fact reproduced in the
	# double's in-memory state.
	check_eq(_bought_units(api), [UPGRADE_TARGET],
		"the double recorded the new tier in the bought-units list once")

	# --- no upgrade path: the Tree's config reference is the -1 sentinel,
	# so the intent fails closed BEFORE anything is written and the row is
	# never reduced to a bare sale (design D3).
	var no_path: Variant = await api.upgrade_building(
		user_id, UPGRADE_NO_PATH_INDEX)
	_check_upgrade_failure(no_path, "no_upgrade_path",
		"a building with no resolvable next tier")

	# --- structured failures: endpoint codes, no partial payload ----
	var ghost: Variant = await api.upgrade_building("ghost-0000", UPGRADE_INDEX)
	_check_upgrade_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.upgrade_building("", UPGRADE_INDEX)
	_check_upgrade_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.upgrade_building(
		user_id, UPGRADE_UNKNOWN_INDEX)
	_check_upgrade_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var zero: Variant = await api.upgrade_building(user_id, 0)
	_check_upgrade_failure(zero, "unknown_item_index",
		"index 0 (never a real legacy key)")

	# --- the reused key stays addressable: upgrading the SAME key again
	# replaces it in place once more, which is this command's distinguishing
	# fact (a move rewrites coordinates, a sale and a store drop the key).
	var again: Variant = await api.upgrade_building(user_id, UPGRADE_INDEX)
	check(again is BootData.UpgradeResult and again.ok,
		"the reused key is still addressable after the first upgrade")
	if again is BootData.UpgradeResult and again.ok:
		var second: BootData.UpgradeResult = again
		check_eq(second.removed.item_id, UPGRADE_TARGET,
			"the second upgrade removed the row the first one wrote")
		check_eq(second.upgraded.item_id, UPGRADE_SECOND_TARGET,
			"the second upgrade derived the next tier from the same reference")
		check_eq(second.upgraded.x, UPGRADE_CELL_X,
			"the second upgrade still reuses the same cell")
		check_eq(second.upgraded.y, UPGRADE_CELL_Y,
			"the second upgrade still reuses the same cell")
		var second_row := _boot_row(second.removed)
		check_eq([int(second_row[1]), int(second_row[2])],
			[UPGRADE_CELL_X, UPGRADE_CELL_Y],
			"the row the first upgrade wrote kept the pre-execution cell")
	# The bought-units record is a SET, not a log: both new tiers are
	# recorded, the already-listed one is never repeated.
	check_eq(_bought_units(api), [UPGRADE_TARGET, UPGRADE_SECOND_TARGET],
		"each new tier is recorded exactly once in the bought-units list")

	# --- the failures applied nothing: an unrelated row still resolves to
	# its own item (state not corrupted), and the Tree is still on the map.
	var unrelated: Variant = await api.upgrade_building(user_id, 11)
	check(unrelated is BootData.UpgradeResult and unrelated.ok,
		"an unrelated row still resolves after the failed attempts")
	if unrelated is BootData.UpgradeResult and unrelated.ok:
		check_eq((unrelated as BootData.UpgradeResult).removed.item_id, 22,
			"the unrelated row resolves to its own item (state not corrupted)")
	var tree_again: Variant = await api.upgrade_building(
		user_id, UPGRADE_NO_PATH_INDEX)
	_check_upgrade_failure(tree_again, "no_upgrade_path",
		"the un-upgradeable row is still on the map after the failures")
	check_eq(int((_read_fixture_object(FIXTURE_UPGRADE_AFTER)["maps"][0]
		as Dictionary)["items"]["12"][0]), UPGRADE_TARGET,
		"the committed after-state still holds the upgraded tier at that key")

	check_eq(api.upgrade_requests, requests_before + 9,
		"every upgrade_building call increments the intent counter exactly "
		+ "once")
	info("upgrade double resolved the executed fixture's in-place replacement "
		+ "plus 5 structured failures with no server and no socket")


## Construction double coverage (task 3.2, design D8): the three actions in
## sequence over ONE row (start, click, finish), the derived duration read from
## the fixture's OWN item build time and cross-checked against the executed
## fixture's recorded countdown, the time-dependent start instant asserted as a
## positive integer and never by value, the row mutated in place with nothing
## else touched, and every structural failure with the endpoint's own code —
## including the 400 `no_build_time`, the one refusal that keeps an unbuildable
## row away from legacy's whole-attribute-bag clearing branch (design D3/D6).
func _check_construction(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_CONSTRUCTION_BEFORE)
	var after := _read_fixture_object(FIXTURE_CONSTRUCTION_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the construction fixture before map carries 40 placements")
	check_eq(after_items.size(), 40,
		"the executed construction kept 40 placements (the key is REUSED)")
	check(after_items.has("11"),
		"the executed construction left the row at key 11 (in place)")
	# The two rows the executed pair produced, in the typed form the client
	# receives.
	var row_before := _typed_row(before_items["11"])
	var row_after := _typed_row(after_items["11"])
	check_eq(row_before, CONSTRUCTION_ROW,
		"the fixture anchors the Turret I at (58,48) under key 11")
	check_eq(int(row_after[0]), CONSTRUCTION_ITEM,
		"the executed construction kept the row's own item")
	check_eq([int(row_after[1]), int(row_after[2])],
		[CONSTRUCTION_CELL_X, CONSTRUCTION_CELL_Y],
		"the executed construction reused the very same cell")
	check(int(row_after[3]) > int(row_before[3]),
		"the executed construction re-stamped the row with a later wall-clock "
		+ "start instant (time-dependent field, never asserted by value)")
	var recorded: Dictionary = row_after[6] as Dictionary
	check(recorded.has("cp") and int(recorded["cp"]) == CONSTRUCTION_BUILD_TIME,
		"the executed construction recorded the item's committed build time "
		+ "as the countdown (the derived duration, matched here)")
	check(recorded.has("nc") and int(recorded["nc"]) == CONSTRUCTION_CLICKS,
		"the executed construction raised the click counter to the item's "
		+ "committed clicks_to_build")
	# Every other row is byte-identical: the one in-place attribute-bag write
	# is the only map write the executed transaction made.
	var other_keys: Array = []
	for key: Variant in before_items:
		if str(key) != "11":
			other_keys.append(str(key))
	other_keys.sort()
	var untouched := true
	for key: String in other_keys:
		if _typed_row(before_items[key]) != _typed_row(after_items[key]):
			untouched = false
	check(untouched,
		"the executed construction changed no other row (39 rows stay "
		+ "byte-identical)")
	# The neutral derived vector means the resource bag and the storage are
	# unchanged, so NO building cost is claimed.
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		check_eq(before_map[key], after_map[key],
			"the executed construction left %s unchanged" % key)
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed construction left cash unchanged (no cost is claimed)")
	check_eq(before["privateState"]["mana"], after["privateState"]["mana"],
		"the executed construction left mana unchanged")
	check_eq(after_map["store"], {},
		"the executed construction left storage empty (it touches no storage)")
	check_eq(before["privateState"]["boughtUnits"], [],
		"the executed construction started from an empty bought-units list")
	check_eq(after["privateState"]["boughtUnits"], [],
		"the executed construction wrote no bought-units bookkeeping")
	# The capture's recorded epoch, read the same way the placement and
	# upgrade doubles read theirs: the start a double re-stamps with, never
	# the wall clock.
	var requests_before: int = api.construction_requests

	# --- step 1: start. The duration is DERIVED from committed content, and
	# the row is re-stamped in place with the countdown recorded.
	var started: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_START)
	check(started is BootData.ConstructionResult,
		"build_construction returns the typed result")
	if not (started is BootData.ConstructionResult):
		return
	var first: BootData.ConstructionResult = started
	check(first.ok, "fake construction start resolves offline: %s"
		% first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL,
		"construction protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02", "the game version is the fixture's")
	check(first.server_time > 0,
		"server_time is the positive fixture epoch (time-dependent field)")
	check_eq(first.result, "success", "legacy result string is reported")
	check_eq(first.action, CONSTRUCTION_START,
		"the resolved action is echoed from the closed vocabulary")
	check(first.previous != null, "the pre-execution row is carried")
	check(first.row != null, "the post-execution row is carried")
	check(first.resources != null, "typed resources are carried")
	if first.previous == null or first.row == null or first.resources == null:
		return
	# BOTH sides are the legacy eight-field row through the one shared entry
	# parser, and the two differ in exactly the two fields the start writes.
	check_eq(_boot_row(first.previous), CONSTRUCTION_ROW,
		"the previous row is the executed fixture's pre-execution row")
	check_eq(first.previous.timestamp, 0,
		"the previous row keeps the save's timestamp (never restamped)")
	check_eq(first.previous.attr, {}, "the previous row keeps its empty bag")
	check_eq(first.row.item_id, CONSTRUCTION_ITEM,
		"the post-execution row names the row's own item")
	check_eq([first.row.x, first.row.y],
		[CONSTRUCTION_CELL_X, CONSTRUCTION_CELL_Y],
		"the post-execution row reuses the pre-execution cell")
	check(first.row.timestamp > int(CONSTRUCTION_ROW[3]),
		"the post-execution row is re-stamped with a later start instant "
		+ "(the deterministic double never reads the wall clock)")
	check_eq(first.row.timestamp, int(row_after[3]),
		"the re-stamp reuses the capture's recorded epoch, exactly as the "
		+ "placement and upgrade doubles reuse theirs")
	check_eq(first.row.attr, {"cp": CONSTRUCTION_BUILD_TIME},
		"the post-execution row records the derived countdown and nothing else")
	check_eq(first.row.orientation, int(row_after[4]),
		"the post-execution row carries the row's own orientation")
	check_eq(first.row.player, int(row_after[7]),
		"the post-execution row carries the row's own player field")
	# The neutral derived vector: the resource bag is the fresh save's own
	# values — never a computed delta, and no building cost.
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is unchanged by the neutral vector")
	check_eq(first.resources.wood, int(before_map["wood"]),
		"wood is unchanged by the neutral vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is unchanged by the neutral vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is unchanged by the neutral vector")
	check_eq(first.resources.xp, int(before_map["xp"]),
		"xp is unchanged by the neutral vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is unchanged by the neutral vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is unchanged by the neutral vector")

	# --- step 2: click. The counter is raised (seeded to 1 when absent) and
	# the countdown is left exactly as the start recorded it.
	var clicked: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_CLICK)
	check(clicked is BootData.ConstructionResult and clicked.ok,
		"fake construction click resolves offline: %s"
		% (clicked.error_message if clicked is BootData.ConstructionResult
			else "not typed"))
	if not (clicked is BootData.ConstructionResult) or not clicked.ok:
		return
	var second: BootData.ConstructionResult = clicked
	check_eq(second.action, CONSTRUCTION_CLICK, "the click action is echoed")
	check_eq(second.previous.attr, {"cp": CONSTRUCTION_BUILD_TIME},
		"the click's pre-execution row is the started row verbatim")
	check_eq(second.row.attr,
		{"cp": CONSTRUCTION_BUILD_TIME, "nc": CONSTRUCTION_CLICKS},
		"the click raises the counter to 1 beside the recorded countdown")
	check_eq(_typed_attr(second.row.attr), _typed_attr(row_after[6]),
		"the walked start-then-click pair reproduces the executed fixture's own "
		+ "recorded bag, field for field")
	check_eq(second.row.timestamp, int(row_after[3]),
		"a click writes no timestamp of its own")

	# --- step 3: finish. The counter is consumed and the countdown is left
	# alone: the whole state the executed fixture's own two commands produced.
	var finished: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_FINISH)
	check(finished is BootData.ConstructionResult and finished.ok,
		"fake construction finish resolves offline")
	if not (finished is BootData.ConstructionResult) or not finished.ok:
		return
	var third: BootData.ConstructionResult = finished
	check_eq(third.action, CONSTRUCTION_FINISH, "the finish action is echoed")
	check_eq(third.row.attr, {"cp": CONSTRUCTION_BUILD_TIME},
		"the completion consumes the counter and writes nothing else")
	check_eq(third.row.timestamp, int(row_after[3]),
		"the completion writes no timestamp of its own")
	check_eq(third.resources.gold, int(before_map["gold"]),
		"the completion changes no resource (neutral vector)")

	# A fourth click re-raises the counter the completion consumed: the
	# double is a faithful in-memory model of the three branches, not a
	# once-only scripted answer.
	var again: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_CLICK)
	check(again is BootData.ConstructionResult and again.ok,
		"a click after a completion resolves again")
	if again is BootData.ConstructionResult and again.ok:
		check_eq((again as BootData.ConstructionResult).row.attr,
			{"cp": CONSTRUCTION_BUILD_TIME, "nc": 1},
			"the click counter is seeded to 1 when absent, never guessed")

	# --- structured failures: endpoint codes, no partial payload ----
	var ghost: Variant = await api.build_construction("ghost-0000",
		CONSTRUCTION_INDEX, CONSTRUCTION_START)
	_check_construction_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.build_construction("", CONSTRUCTION_INDEX,
		CONSTRUCTION_START)
	_check_construction_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.build_construction(user_id,
		CONSTRUCTION_UNKNOWN_INDEX, CONSTRUCTION_START)
	_check_construction_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var zero: Variant = await api.build_construction(user_id, 0,
		CONSTRUCTION_START)
	_check_construction_failure(zero, "unknown_item_index",
		"index 0 (never a real legacy key)")
	for bad_action in ["activate", "add_click", "activate_item_click", "",
			"START", "finish "]:
		var refused: Variant = await api.build_construction(user_id,
			CONSTRUCTION_INDEX, str(bad_action))
		_check_construction_failure(refused, "invalid_action",
			"the action '%s' (a legacy command name is never accepted)"
				% str(bad_action))
	# A start on a row whose item has no resolvable POSITIVE committed build
	# time: the endpoint answers 400 no_build_time BEFORE the dispatcher runs,
	# so the row's bag is never cleared and no duration is ever coerced. The
	# corpus places no such row, so the suite parks one in the double's
	# IN-MEMORY state (the committed fixture is never written).
	var no_time_index := 4242
	_park_row(api, no_time_index, CONSTRUCTION_NO_TIME_ITEM)
	var no_time: Variant = await api.build_construction(user_id, no_time_index,
		CONSTRUCTION_START)
	_check_construction_failure(no_time, "no_build_time",
		"an item with no resolvable positive committed build time")
	# The same row's other two actions carry no duration at all, so they are
	# NOT refused: only a start resolves one (design D2).
	var no_time_click: Variant = await api.build_construction(user_id,
		no_time_index, CONSTRUCTION_CLICK)
	check(no_time_click is BootData.ConstructionResult and no_time_click.ok,
		"a click derives no duration, so it is not refused")
	if no_time_click is BootData.ConstructionResult and no_time_click.ok:
		check_eq((no_time_click as BootData.ConstructionResult).row.attr,
			{"nc": 1},
			"the click on the unbuildable row raised only the counter")
	var no_time_finish: Variant = await api.build_construction(user_id,
		no_time_index, CONSTRUCTION_FINISH)
	check(no_time_finish is BootData.ConstructionResult and no_time_finish.ok,
		"a completion derives no duration, so it is not refused")

	# --- the failures applied nothing: an unrelated row still resolves to
	# its own item (state not corrupted) and the construction is still there.
	var unrelated: Variant = await api.build_construction(user_id,
		CONSTRUCTION_SPARE_INDEX, CONSTRUCTION_START)
	check(unrelated is BootData.ConstructionResult and unrelated.ok,
		"an unrelated row still resolves after the failed attempts")
	if unrelated is BootData.ConstructionResult and unrelated.ok:
		check_eq((unrelated as BootData.ConstructionResult).previous.item_id, 22,
			"the unrelated row resolves to its own item (state not corrupted)")
		check_eq((unrelated as BootData.ConstructionResult).row.attr,
			{"cp": CONSTRUCTION_BUILD_TIME},
			"the unrelated row recorded its own derived countdown")
	var built: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_START)
	check(built is BootData.ConstructionResult and built.ok,
		"the constructed row is still addressable after the failed attempts")
	if built is BootData.ConstructionResult and built.ok:
		check_eq((built as BootData.ConstructionResult).row.attr,
			{"cp": CONSTRUCTION_BUILD_TIME, "nc": 1},
			"a re-start keeps the counter and re-records the countdown: the "
			+ "positive-duration branch writes only cp, never clears the bag")
	check_eq(int((_read_fixture_object(FIXTURE_CONSTRUCTION_AFTER)["maps"][0]
		as Dictionary)["items"]["11"][3]), int(row_after[3]),
		"the committed after-state still holds its own recorded start instant")

	# Every call increments the intent counter exactly once, including the
	# refusals: a refused intent is still an intent this client issued.
	check_eq(api.construction_requests, requests_before + 19,
		"every build_construction call increments the intent counter exactly "
		+ "once (three walked steps, a re-click, nine structural failures, the "
		+ "unbuildable row's click and completion, and two recovery calls)")
	info("construction double walked the executed fixture's row through all "
		+ "three actions plus 9 structured failures with no server and no socket")


## Every construction failure carries the endpoint's code and no partial
## payload (design D3/D5) — including the 404 `unknown_item_index`, the 400
## `invalid_action`, and the 400 `no_build_time` that keeps an unbuildable row
## away from legacy's attribute-bag-clearing branch.
func _check_construction_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.ConstructionResult,
		label + " returns the typed result")
	if not (result is BootData.ConstructionResult):
		return
	var typed: BootData.ConstructionResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.previous == null, label + " carries no partial previous row")
	check(typed.row == null, label + " carries no partial post-execution row")
	check(typed.resources == null, label + " carries no partial resources")
	check_eq(typed.result, "",
		label + " reports no legacy result for a failed construction")
	check_eq(typed.action, "",
		label + " reports no resolved action for a failed construction")


# ---------------------------------------------------------------------------
# Collect double (task 3.2, building-collect design D8)
# ---------------------------------------------------------------------------


## Collect double coverage: the committed executed transaction reproduced over
## the fixture's own before-state, with the payout derived from the FIXTURE'S
## OWN committed content and the row's pre-execution instant (never from the
## caller), the collection instant re-stamped deterministically, both rows
## carried, the value-level post-state checked, and every structural and
## content refusal answered with the endpoint's own code — including the two
## (`capped_collection`, `unknown_collect_type`) and the clock one
## (`too_early`) that no placed corpus row can produce, which is why they are
## stubbed in the double's own in-memory state and never written to the
## committed fixture.
func _check_collect(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_COLLECT_BEFORE)
	var after := _read_fixture_object(FIXTURE_COLLECT_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	var before_items: Dictionary = before_map["items"]
	var after_items: Dictionary = after_map["items"]
	check_eq(before_items.size(), 40,
		"the collect fixture before map carries 40 placements")
	check_eq(after_items.size(), 40,
		"the executed collection kept 40 placements (the key is REUSED)")
	check(after_items.has("2"),
		"the executed collection left the row at key 2 (in place)")
	var row_before := _typed_row(before_items["2"])
	var row_after := _typed_row(after_items["2"])
	check_eq(row_before, COLLECT_ROW,
		"the fixture anchors the Tree at (53,39) under key 2")
	check_eq(int(row_after[0]), COLLECT_ITEM,
		"the executed collection kept the row's own item")
	check_eq([int(row_after[1]), int(row_after[2])],
		[COLLECT_CELL_X, COLLECT_CELL_Y],
		"the executed collection reused the very same cell")
	check(int(row_after[3]) > int(row_before[3]),
		"the executed collection re-stamped the row with a later wall-clock "
		+ "collection instant (time-dependent field, never asserted by value)")
	check_eq(row_after[4], row_before[4],
		"the executed collection left the row's own orientation alone")
	check_eq(row_after[5], row_before[5], "the executed collection wrote no store")
	check_eq(row_after[6], row_before[6],
		"the executed collection left the row's empty attribute bag alone")
	check_eq(row_after[7], row_before[7],
		"the executed collection kept the row's own player field")
	# ONLY item[3] differs: that is the branch's single established write.
	var changed: Array = []
	for index in range(8):
		if row_before[index] != row_after[index]:
			changed.append(index)
	check_eq(changed, [3],
		"the executed collection changed exactly one field of the addressed "
		+ "row: its collection instant")
	# Every other row is byte-identical: the one in-place timestamp write is
	# the only map write the executed transaction made.
	var other_keys: Array = []
	for key: Variant in before_items:
		if str(key) != "2":
			other_keys.append(str(key))
	other_keys.sort()
	var untouched := true
	for key: String in other_keys:
		if _typed_row(before_items[key]) != _typed_row(after_items[key]):
			untouched = false
	check(untouched,
		"the executed collection changed no other row (39 rows stay "
		+ "byte-identical)")
	# The content-derived payout, the executed resource movement, and the
	# storages the branch never touches.
	check_eq(int(after_map["xp"]) - int(before_map["xp"]), 3,
		"the executed collection paid the derived 3 experience")
	check_eq(int(after_map["wood"]) - int(before_map["wood"]), 60,
		"the executed collection paid the derived 60 wood")
	for key in ["gold", "oil", "steel"]:
		check_eq(before_map[key], after_map[key],
			"the executed collection left %s unchanged (the derived vector "
			% key + "names only wood and experience)")
	check_eq(before["playerInfo"]["cash"], after["playerInfo"]["cash"],
		"the executed collection left cash unchanged")
	check_eq(before["privateState"]["mana"], after["privateState"]["mana"],
		"the executed collection left mana unchanged")
	check_eq(after_map["store"], {},
		"the executed collection left storage empty (it stores nothing)")
	check_eq(before["privateState"]["boughtUnits"], [],
		"the executed collection started from an empty bought-units list")
	check_eq(after["privateState"]["boughtUnits"], [],
		"the executed collection wrote no bought-units bookkeeping")
	var requests_before: int = api.collect_requests

	# --- the collected income. The amount, resource, and experience are derived
	# from the fixture's OWN loaded configuration and the row's pre-execution
	# instant; the double re-stamps with the capture's own recorded epoch, so
	# the reached rung is the same in every run.
	var collected: Variant = await api.collect_income(user_id, COLLECT_INDEX)
	check(collected is BootData.CollectResult,
		"collect_income returns the typed result")
	if not (collected is BootData.CollectResult):
		return
	var first: BootData.CollectResult = collected
	check(first.ok, "fake collection resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL,
		"collect protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02",
		"the collect game version is the fixture's")
	check(first.server_time > 0,
		"collect server_time is the positive fixture epoch (time-dependent)")
	check_eq(first.result, "success", "legacy result string is reported")
	check_eq(_boot_row(first.previous), COLLECT_ROW,
		"the previous row is the executed fixture's pre-execution row")
	check_eq(first.row.item_id, COLLECT_ITEM,
		"the post-execution row names the row's own item")
	check_eq([first.row.x, first.row.y],
		[COLLECT_CELL_X, COLLECT_CELL_Y],
		"the post-execution row reuses the pre-execution cell")
	check_eq(first.row.attr, {},
		"the post-execution row carries no attribute bag entry")
	check_eq(first.row.orientation, int(row_after[4]),
		"the post-execution row carries the row's own orientation")
	check_eq(first.row.player, int(row_after[7]),
		"the post-execution row carries the row's own player field")
	check(first.row.timestamp > int(COLLECT_ROW[3]),
		"the post-execution row is re-stamped with a later collection instant "
		+ "(the deterministic double never reads the wall clock)")
	check_eq(first.row.timestamp, int(row_after[3]),
		"the re-stamp reuses the capture's recorded epoch, exactly as the "
		+ "placement, upgrade, and construction doubles reuse theirs")
	check_eq(first.row.timestamp, first.reference_time,
		"the reference instant IS the deterministic re-stamp, so the derived "
		+ "rung is the same in every run")
	# The derived payout, its rung, and the two slots that can never be filled.
	check_eq(first.payout, COLLECT_PAYOUT,
		"the derived payout is the documented eight-slot vector, matching the "
		+ "executed fixture's own applied vector")
	check_eq(int(first.payout[0]), 0,
		"the derived payout's unread unknown slot is zero (D6)")
	check_eq(int(first.payout[7]), 0,
		"the derived payout's never-produced mana slot is zero (D6)")
	check_eq(first.tier, COLLECT_TIER,
		"the payout came from the top committed rung, which the fixture's own "
		+ "unbounded elapsed time (item[3] == 0) makes deterministic")
	check_eq(int(first.payout[1]), COLLECT_XP * COLLECT_TIER,
		"the experience is the committed collect_xp scaled by the rung (D2)")
	check_eq(int(first.payout[3]), COLLECT_AMOUNT * COLLECT_TIER,
		"the wood is the committed collect scaled by the rung (D1)")
	check_eq(int(first.payout[2]) + int(first.payout[4]) + int(first.payout[5])
			+ int(first.payout[6]), 0,
		"the derived vector names exactly the committed collect_type's slot")
	# The value-level post-state: every stored resource moved by exactly the
	# derived delta, and the other five are untouched.
	check_eq(first.resources.wood, int(before_map["wood"]) + 60,
		"the applied wood is the fresh save's own value plus the derived delta")
	check_eq(first.resources.xp, int(before_map["xp"]) + 3,
		"the applied experience is the fresh save's own value plus the delta")
	check_eq(first.resources.gold, int(before_map["gold"]),
		"gold is untouched by the derived vector")
	check_eq(first.resources.oil, int(before_map["oil"]),
		"oil is untouched by the derived vector")
	check_eq(first.resources.steel, int(before_map["steel"]),
		"steel is untouched by the derived vector")
	check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
		"cash is untouched by the derived vector")
	check_eq(first.resources.mana, int(before["privateState"]["mana"]),
		"mana is untouched by the derived vector")

	# --- a SECOND collection on the same row is now TOO EARLY: the re-stamp
	# moved the clock to the deterministic reference, so no committed rung is
	# reached and nothing is derived (design D3). This is the double being a
	# faithful model of the branch's state machine, not a once-only answer.
	var second: Variant = await api.collect_income(user_id, COLLECT_INDEX)
	_check_collect_failure(second, "too_early",
		"a second collection on the just-collected row")
	var unchanged: Variant = await api.collect_income(user_id,
		COLLECT_SPARE_INDEX)
	check(unchanged is BootData.CollectResult and unchanged.ok,
		"a sibling income row still collects offline")
	if unchanged is BootData.CollectResult and unchanged.ok:
		check_eq(unchanged.tier, COLLECT_TIER,
			"the sibling row also reaches the top committed rung")
		check_eq((unchanged as BootData.CollectResult).previous.item_id,
			COLLECT_SPARE_ITEM,
			"the sibling row resolves to its own item (state not corrupted)")
		check_eq((unchanged as BootData.CollectResult).resources.wood,
			int(before_map["wood"]) + 120,
			"the sibling collection applied the SAME derived payout on top of "
			+ "the first one's, which is what a per-collection credit means")

	# --- structured failures: endpoint codes, no partial payload ----
	var ghost: Variant = await api.collect_income("ghost-0000", COLLECT_INDEX)
	_check_collect_failure(ghost, "unknown_user_id", "unknown save id")
	var empty: Variant = await api.collect_income("", COLLECT_INDEX)
	_check_collect_failure(empty, "missing_user_id", "empty save id")
	var unknown_index: Variant = await api.collect_income(user_id,
		COLLECT_UNKNOWN_INDEX)
	_check_collect_failure(unknown_index, "unknown_item_index",
		"an index the map does not name")
	var zero: Variant = await api.collect_income(user_id, 0)
	_check_collect_failure(zero, "unknown_item_index",
		"index 0 (never a real legacy key)")
	# A no-income row: the Turret I at key 11 records `collect 0`, so the
	# service answers 409 no_income BEFORE the dispatcher runs.
	var no_income: Variant = await api.collect_income(user_id, 11)
	_check_collect_failure(no_income, "no_income",
		"a row whose item records no committed income")
	# The two content refusals and the clock refusal no placed corpus row can
	# produce: a crafted config item and a crafted row, both in the double's
	# OWN in-memory state (the committed fixture is never written).
	_park_collect_row(api, COLLECT_CAPPED_INDEX, COLLECT_CAPPED_ITEM, {}, 0,
		{"id": str(COLLECT_CAPPED_ITEM), "name": "Capped fixture",
			"collect": "20", "collect_type": "w", "collect_xp": "1",
			"max_collects": "25"})
	var capped: Variant = await api.collect_income(user_id, COLLECT_CAPPED_INDEX)
	_check_collect_failure(capped, "capped_collection",
		"an item with a non-zero committed collection cap")
	_park_collect_row(api, COLLECT_UNMAPPABLE_INDEX, COLLECT_UNMAPPABLE_ITEM,
		{}, 0, {"id": str(COLLECT_UNMAPPABLE_ITEM), "name": "Unmappable fixture",
			"collect": "20", "collect_type": "m", "collect_xp": "1",
			"max_collects": "0"})
	var unmappable: Variant = await api.collect_income(user_id,
		COLLECT_UNMAPPABLE_INDEX)
	_check_collect_failure(unmappable, "unknown_collect_type",
		"an item whose collect_type is outside the committed set")
	# Design D5's construction-state refusal, in the DOUBLE as well as the
	# service: a row carrying a countdown is refused before anything is
	# derived, so the timers the delivered construction line depends on can
	# never be overwritten from this layer either.
	_park_collect_row(api, COLLECT_BUILDING_INDEX, COLLECT_ITEM, {"cp": 180},
		1790690000, null)
	var building: Variant = await api.collect_income(user_id,
		COLLECT_BUILDING_INDEX)
	_check_collect_failure(building, "construction_in_progress",
		"a row carrying a recorded countdown")
	var built_row: Array = (api._impl as FakeApi)._collect_state["items"][
		str(COLLECT_BUILDING_INDEX)] as Array
	check_eq(built_row[3], 1790690000,
		"the refused row's START INSTANT is untouched: the corruption probe 2 "
		+ "showed legacy permits is prevented here")
	check_eq(built_row[6], {"cp": 180},
		"the refused row's recorded countdown survives untouched")
	# Design D3's clock refusal: a row stamped one second short of the first
	# committed rung (5 committed MINUTES = 300 SECONDS) reaches no rung, and
	# nothing is derived.
	_park_collect_row(api, COLLECT_FRESH_INDEX, COLLECT_ITEM, {}, 0, null)
	var epoch: int = (api._impl as FakeApi)._collect_epoch
	((api._impl as FakeApi)._collect_state["items"]
		[str(COLLECT_FRESH_INDEX)] as Array)[3] = epoch \
		- COLLECT_FIRST_RUNG_SECONDS + 1
	var early: Variant = await api.collect_income(user_id, COLLECT_FRESH_INDEX)
	_check_collect_failure(early, "too_early",
		"a row one second short of the first committed rung")
	# The same row one second FURTHER along reaches the first rung and is paid
	# the quarter multiplier's amount with its experience rounded to zero (D1).
	((api._impl as FakeApi)._collect_state["items"]
		[str(COLLECT_FRESH_INDEX)] as Array)[3] = epoch \
		- COLLECT_FIRST_RUNG_SECONDS
	var first_rung: Variant = await api.collect_income(user_id,
		COLLECT_FRESH_INDEX)
	check(first_rung is BootData.CollectResult and first_rung.ok,
		"a row exactly at the first committed rung collects offline")
	if first_rung is BootData.CollectResult and first_rung.ok:
		check_eq(first_rung.tier, 0,
			"exactly at the first committed threshold the FIRST rung is reached")
		check_eq(first_rung.payout, [0, 0, 0, 5, 0, 0, 0, 0],
			"the first rung pays a quarter of the committed amount and rounds "
			+ "the committed experience of 1 down to zero")

	# --- the refusals applied nothing: a THIRD income row still resolves to
	# its own item (state not corrupted) and the committed after-state still
	# holds its own recorded instant.
	var unrelated: Variant = await api.collect_income(user_id,
		COLLECT_RECOVERY_INDEX)
	check(unrelated is BootData.CollectResult and unrelated.ok,
		"an untouched sibling row still resolves after the failed attempts")
	if unrelated is BootData.CollectResult and unrelated.ok:
		check_eq((unrelated as BootData.CollectResult).previous.item_id,
			COLLECT_RECOVERY_ITEM,
			"the untouched sibling resolves to its own item (state not "
			+ "corrupted)")
	check_eq(int((_read_fixture_object(FIXTURE_COLLECT_AFTER)["maps"][0]
		as Dictionary)["items"]["2"][3]), int(row_after[3]),
		"the committed after-state still holds its own recorded instant")

	# Every call increments the intent counter exactly once, including the
	# refusals: a refused intent is still an intent this client issued.
	check_eq(api.collect_requests, requests_before + 14,
		"every collect_income call increments the intent counter exactly once "
		+ "(three collected rows, one natural too-early re-collect, and ten "
		+ "structured refusals)")
	info("collect double reproduced the executed fixture's transaction and "
		+ "answered eleven structured refusals with no server and no socket")


## Every collect failure carries the endpoint's code and no partial payload
## (design D7/D8) — including the 404 `unknown_item_index`, the 409s
## `no_income` / `capped_collection` / `unknown_collect_type` /
## `too_early` / `construction_in_progress`, and the two save-id codes.
func _check_collect_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.CollectResult,
		label + " returns the typed result")
	if not (result is BootData.CollectResult):
		return
	var typed: BootData.CollectResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.previous == null, label + " carries no partial previous row")
	check(typed.row == null, label + " carries no partial post-execution row")
	check(typed.resources == null, label + " carries no partial resources")
	check_eq(typed.payout, [],
		label + " carries no partial payout vector")
	check_eq(typed.tier, -1, label + " reports no rung for a failed collection")
	check_eq(typed.result, "",
		label + " reports no legacy result for a failed collection")


## Expand double coverage (building-expand tasks 3.1/3.2, design D8): the
## typed shape, the content-derived DEBIT over the FIXTURE'S OWN committed
## schedule, the free row, the out-of-range / negative / duplicate / requirements
## refusals, the affordability refusal the committed schedule cannot produce on
## its own, and every fail-closed code — all with no server and no socket.
func _check_expand(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_EXPAND_BEFORE)
	var after := _read_fixture_object(FIXTURE_EXPAND_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	# The committed ledger, in the save's OWN order, and the one the executed
	# transaction produced.
	var ledger_before: Array = []
	for entry: Variant in (before_map["expansions"] as Array):
		ledger_before.append(int(entry))
	var ledger_after: Array = []
	for entry: Variant in (after_map["expansions"] as Array):
		ledger_after.append(int(entry))
	check_eq(ledger_before, EXPAND_OWNED,
		"the expand fixture's before state carries the corpus's own ledger")
	check_eq(ledger_after, EXPAND_OWNED_AFTER,
		"the executed expansion appended exactly one entry, the sent id, at "
		+ "the end, with every existing entry unchanged and in order")
	check_eq((after_map["items"] as Dictionary).size(),
		(before_map["items"] as Dictionary).size(),
		"the executed expansion changed NO placement (40 rows before and after)")
	check(before_map["items"] == after_map["items"],
		"every placement row is byte-identical after the expansion")
	check_eq(after_map["level"], before_map["level"],
		"the map level is unchanged")
	check_eq(after_map["store"], before_map["store"],
		"the storage is unchanged")
	check_eq(after["privateState"], before["privateState"],
		"the whole private state is byte-identical")
	check_eq(after["playerInfo"], before["playerInfo"],
		"the player info is byte-identical")
	# The committed schedule the double prices from — the FIXTURE'S OWN loaded
	# configuration, never a value from the caller.
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its in-memory "
			+ "state")
		return
	var schedule: Array = (double._config_payload as Dictionary).get(
		"expansion_prices", []) as Array
	check_eq(schedule.size(), 98,
		"the double's own loaded configuration carries the committed 98-row "
		+ "positional schedule")
	check_eq([int(schedule[EXPAND_ID]["coins"]), int(schedule[EXPAND_ID]["cash"]),
		int(schedule[EXPAND_ID]["neighbors"]),
		int(schedule[EXPAND_ID]["inventory_qte"])], [0, 0, 0, 0],
		"the committed row for id 0 is the all-zero free row")
	check_eq([int(schedule[EXPAND_PRICED_ID]["coins"]),
		int(schedule[EXPAND_PRICED_ID]["cash"]),
		int(schedule[EXPAND_PRICED_ID]["neighbors"]),
		int(schedule[EXPAND_PRICED_ID]["inventory_qte"])], [2500, 5, 1, 1],
		"the committed row for id 4 is the cheapest priced row")
	check_eq([int(schedule[EXPAND_SATURATED_ID]["coins"]),
		int(schedule[EXPAND_SATURATED_ID]["cash"]),
		int(schedule[EXPAND_SATURATED_ID]["neighbors"]),
		int(schedule[EXPAND_SATURATED_ID]["inventory_qte"])],
		[100000, 20, 15, 30], "the committed row for id 97 is the saturated row")
	var requests_before: int = api.expand_requests

	# --- the expanded town: the free row, the all-zero debit, and the ledger
	# appended once at the end.
	var expanded: Variant = await api.expand_town(user_id, EXPAND_ID)
	check(expanded is BootData.ExpandResult,
		"expand_town returns the typed result")
	if not (expanded is BootData.ExpandResult):
		return
	var first: BootData.ExpandResult = expanded
	check(first.ok, "fake expansion resolves offline: %s" % first.error_message)
	if not first.ok:
		return
	check_eq(first.protocol, BootData.PROTOCOL,
		"the expand protocol is compat-v0")
	check_eq(first.game_version, "alpha 0.02",
		"the expand game version is the fixture's")
	check(first.server_time > 0,
		"the expand server_time is the positive fixture epoch "
		+ "(time-dependent, never asserted by value)")
	check_eq(first.result, "success", "the legacy result string is reported")
	check_eq(first.expansions_before, EXPAND_OWNED,
		"the pre-execution ledger is the fixture's own, in the save's order")
	check_eq(first.expansions_after, EXPAND_OWNED_AFTER,
		"the post-execution ledger is the sent id appended ONCE at the end")
	check_eq(first.expansions_after.size(),
		first.expansions_before.size() + 1,
		"the ledger grew by exactly one entry")
	for index in range(EXPAND_OWNED.size()):
		check_eq(int(first.expansions_after[index]),
			int(first.expansions_before[index]),
			"ledger entry %d is unchanged and still in order" % index)
	check_eq(first.debit, EXPAND_DEBIT,
		"the derived debit is the documented all-zero eight-slot vector")
	for index: int in BootData.EXPAND_ALWAYS_ZERO_SLOTS:
		check_eq(int(first.debit[index]), 0,
			"slot %d of the derived debit stays zero" % index)
	check(first.price != null, "the response carries the committed price row")
	if first.price != null:
		check_eq([first.price.coins, first.price.cash, first.price.neighbors,
			first.price.inventory_qte], [0, 0, 0, 0],
			"the committed row for a free id records all four fields zero")
	# The value-level post-state: the derived debit is all zeros, so EVERY
	# stored resource is unchanged — which is what the executed fixture records.
	if first.resources != null:
		check_eq(first.resources.gold, int(before_map["gold"]),
			"gold is the fresh save's own value (the debit charges nothing)")
		check_eq(first.resources.wood, int(before_map["wood"]),
			"wood is the fresh save's own value")
		check_eq(first.resources.oil, int(before_map["oil"]),
			"oil is the fresh save's own value")
		check_eq(first.resources.steel, int(before_map["steel"]),
			"steel is the fresh save's own value")
		check_eq(first.resources.cash, int(before["playerInfo"]["cash"]),
			"cash is the fresh save's own value")
		check_eq(first.resources.mana, int(before["privateState"]["mana"]),
			"mana is the fresh save's own value")
		check_eq(first.resources.xp, int(before_map["xp"]),
			"experience is the fresh save's own value")
	# The double's own in-memory ledger, read from the LIVE instance (never
	# from the committed fixture, which is never written).
	var in_memory: Array = (double._expand_state["expansions"] as Array) \
		.duplicate()
	check_eq(in_memory, EXPAND_OWNED_AFTER,
		"the double's own in-memory ledger is the appended one")

	# --- a SECOND free row: the ledger grows again, never a duplicate.
	var second: Variant = await api.expand_town(user_id, EXPAND_SECOND_ID)
	check(second is BootData.ExpandResult and second.ok,
		"a second free row expands offline")
	if second is BootData.ExpandResult and second.ok:
		var next: BootData.ExpandResult = second
		check_eq(next.expansions_before, EXPAND_OWNED_AFTER,
			"the second expansion's pre-execution ledger is the first one's "
			+ "result")
		check_eq(next.expansions_after, [35, 36, 45, 46, 0, 1],
			"the second expansion appends its own id at the end, never "
			+ "replacing or reordering the first")
		check_eq(next.debit, EXPAND_DEBIT,
			"the second expansion derives the same all-zero free debit")

	# --- structured failures: the endpoint's own codes, no partial payload.
	_check_expand_failure(await api.expand_town("", EXPAND_ID),
		"missing_user_id", "an empty save id")
	_check_expand_failure(await api.expand_town("ghost-0000", EXPAND_ID),
		"unknown_user_id", "an unknown save id")
	_check_expand_failure(await api.expand_town(user_id, EXPAND_NEGATIVE_ID),
		"invalid_expansion_id",
		"a negative id (which Python would otherwise resolve to the schedule's "
		+ "LAST row)")
	_check_expand_failure(await api.expand_town(user_id, EXPAND_OUT_OF_RANGE_ID),
		"unknown_expansion_id",
		"an id the committed schedule prices nothing for — the guard the "
		+ "executed probe showed the legacy server lacks")
	_check_expand_failure(await api.expand_town(user_id, EXPAND_ID),
		"already_expanded",
		"an id the player's own ledger already contains — the guard the "
		+ "executed probe showed the legacy server lacks")
	_check_expand_failure(await api.expand_town(user_id, EXPAND_PRICED_ID),
		"expansion_requirements_unmet",
		"a row recording a positive neighbor/inventory requirement, which "
		+ "nothing this service can read evaluates (design D3)")
	# The whole free range 0..3 is purchasable: the last free row grows the
	# ledger, and a repeat of it is refused by the duplicate guard.
	var last_free: Variant = await api.expand_town(user_id, EXPAND_LAST_FREE_ID)
	check(last_free is BootData.ExpandResult and last_free.ok,
		"the last free row (id 3) is purchasable on the committed table")
	if last_free is BootData.ExpandResult and last_free.ok:
		check_eq((last_free as BootData.ExpandResult).expansions_after,
			[35, 36, 45, 46, 0, 1, 3],
			"the last free row is appended at the end too")
	_check_expand_failure(await api.expand_town(user_id, EXPAND_LAST_FREE_ID),
		"already_expanded",
		"the LAST free row once it is already owned is refused by the "
		+ "duplicate guard")
	# Every id the corpus itself owns is requirement-blocked, so none of them
	# could have been bought under the rule — the readout's
	# owned-and-not-repurchasable case, asserted on the double too.
	for id: int in EXPAND_OWNED:
		_check_expand_failure(await api.expand_town(user_id, id),
			"already_expanded",
			"the corpus's own owned id %d (already expanded)" % id)
	# The affordability refusal (design D6) is UNREACHABLE from the committed
	# schedule — its only purchasable rows are free — so it is exercised the
	# same way the collect suite exercises a capped item: the double's OWN
	# in-memory schedule is stubbed for one row so a priced, requirement-free
	# row exists. The committed fixture and configuration are never written.
	_stub_expand_row(api, EXPAND_PRICED_ID, {"coins": 2500, "cash": 5,
		"neighbors": 0, "inventory_qte": 0})
	var unaffordable: Variant = await api.expand_town(user_id, EXPAND_PRICED_ID)
	_check_expand_failure(unaffordable, "insufficient_resources",
		"a priced row the fresh corpus cannot afford (2500 gold against 2000) "
		+ "— refused rather than clamped (design D6)")
	check_eq(_expand_ledger_of(api), [35, 36, 45, 46, 0, 1, 3],
		"the refused affordability changed nothing in the ledger")
	# A row the same stub makes affordable still charges its full derived debit
	# and lands it in exactly the two named slots under the legacy clamp.
	_top_up_expand_balance(api, 2500, 5)
	var charged: Variant = await api.expand_town(user_id, EXPAND_PRICED_ID)
	check(charged is BootData.ExpandResult and charged.ok,
		"the same priced row succeeds once the balance covers it: %s"
			% (charged as BootData.ExpandResult).error_message if
				charged is BootData.ExpandResult else "")
	if charged is BootData.ExpandResult and charged.ok:
		var paid: BootData.ExpandResult = charged
		check_eq(paid.debit, [0, 0, -2500, 0, 0, 0, -5, 0],
			"a row priced coins 2500 and cash 5 derives "
			+ "[0, 0, -2500, 0, 0, 0, -5, 0] (design D2)")
		check_eq(int(paid.debit[1]), 0, "the experience slot stays zero")
		check_eq(int(paid.debit[3]), 0, "the wood slot stays zero")
		check_eq(int(paid.debit[4]), 0, "the oil slot stays zero")
		check_eq(int(paid.debit[5]), 0, "the steel slot stays zero")
		check_eq(int(paid.debit[7]), 0, "the never-produced mana slot stays "
			+ "zero")
		check_eq(paid.resources.gold, 0,
			"the 2500-gold debit lands under the legacy max(..., 0) clamp, "
			+ "driving the balance to exactly zero (the clamp Probe 1 showed "
			+ "is reachable)")
		check_eq(paid.resources.cash, 0,
			"the 5-cash debit lands the same way")
		check_eq(paid.resources.wood, int(before_map["wood"]),
			"an expansion touches no resource its price does not name")
		check_eq(paid.expansions_after, [35, 36, 45, 46, 0, 1, 3, 4],
			"the priced expansion appended its id at the end of the ledger")
	# The stubbed row is restored, so a still-unowned priced row reads the REAL
	# committed table again.
	_restore_expand_row(api, EXPAND_PRICED_ID)
	_check_expand_failure(await api.expand_town(user_id, EXPAND_PRICED_ID + 1),
		"expansion_requirements_unmet",
		"the real committed row at index 5 is requirement-blocked again")

	# Every call increments the intent counter exactly once, including the
	# refusals: a refused intent is still an intent this client issued.
	check_eq(api.expand_requests, requests_before + 17,
		"every expand_town call increments the intent counter exactly once "
		+ "(three expanded free rows, one priced row refused then paid, and "
		+ "thirteen structured refusals)")
	info("expand double reproduced the executed fixture's transaction and "
		+ "answered thirteen structured refusals with no server and no socket")


## Every expand failure carries the endpoint's code and NO partial payload
## (design D5/D7) — including the 404 `unknown_expansion_id`, the 400
## `invalid_expansion_id`, the 409s `already_expanded` /
## `expansion_requirements_unmet` / `insufficient_resources`, and the two
## save-id codes.
func _check_expand_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.ExpandResult,
		label + " returns the typed result")
	if not (result is BootData.ExpandResult):
		return
	var typed: BootData.ExpandResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check_eq(typed.expansions_before, [],
		label + " carries no partial pre-execution ledger")
	check_eq(typed.expansions_after, [],
		label + " carries no partial post-execution ledger")
	check_eq(typed.debit, [], label + " carries no partial debit vector")
	check(typed.price == null, label + " carries no partial price row")
	check(typed.resources == null, label + " carries no partial resources")
	check_eq(typed.result, "",
		label + " reports no legacy result for a failed expansion")


## The double's own in-memory owned-expansions ledger, read from the LIVE
## implementation instance the facade selected (`GameApi._impl`, not a name
## lookup — a reconfigured node stays a child until the frame ends). This is
## the double's observable in-process state, never a transport payload.
func _expand_ledger_of(api: Variant) -> Array:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return []
	return (double._expand_state["expansions"] as Array).duplicate()


## The level-up double over the committed executed-legacy level fixture: the
## corpus's own already-consistent state, the two refusals in the endpoint's own
## order, a real advancement over an in-memory disagreement, the neutral vector's
## value-level proof, the typed curve block, the ignored-client-level discipline,
## and every fail-closed code.
func _check_level(api: Variant, user_id: String) -> void:
	var before := _read_fixture_object(FIXTURE_LEVEL_BEFORE)
	var after := _read_fixture_object(FIXTURE_LEVEL_AFTER)
	if before.is_empty() or after.is_empty():
		return
	var before_map: Dictionary = before["maps"][0]
	var after_map: Dictionary = after["maps"][0]
	check_eq(int(before_map["level"]), LEVEL_CORPUS_LEVEL,
		"the level fixture's before state records level 1")
	check_eq(int(before_map["xp"]), LEVEL_CORPUS_XP,
		"the level fixture's before state records 4 experience")
	# The executed transaction itself: the level did NOT move and NO resource
	# did, because the derived level already equalled the recorded one.
	check_eq(int(after_map["level"]), int(before_map["level"]),
		"the executed level_up left the recorded level UNCHANGED (the derived "
			+ "level already equalled it at the committed corpus)")
	for key in ["xp", "gold", "wood", "oil", "steel", "expansions", "store"]:
		check_eq(after_map[key], before_map[key],
			"the executed level_up left map.%s byte-identical" % key)
	check_eq((after_map["items"] as Dictionary),
		(before_map["items"] as Dictionary),
		"the executed level_up changed NO placement row")
	check_eq(after["playerInfo"], before["playerInfo"],
		"the executed level_up left the player info byte-identical")
	check_eq(after["privateState"], before["privateState"],
		"the executed level_up left the private state byte-identical")
	# The committed curve the double derives from: the FIXTURE'S OWN loaded
	# configuration, never a value from the caller.
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its in-memory "
			+ "state")
		return
	var curve: Array = (double._config_payload as Dictionary).get(
		"levels", []) as Array
	check_eq(curve.size(), LEVEL_ENTRIES,
		"the double's own loaded configuration carries the committed 100-entry "
			+ "level curve")
	var thresholds: Array = []
	for row: Variant in curve:
		thresholds.append(int((row as Dictionary)["exp_required"]))
	check_eq((thresholds.slice(0, LEVEL_FIRST_THRESHOLDS.size()) as Array),
		LEVEL_FIRST_THRESHOLDS,
		"the committed ladder's first eight thresholds, read from the double's "
			+ "own configuration")
	check_eq(int(thresholds[thresholds.size() - 1]), LEVEL_FINAL_THRESHOLD,
		"the committed ladder's final threshold, read from the double's own "
			+ "configuration")
	var non_increasing: Array = []
	for position in range(1, thresholds.size()):
		if int(thresholds[position]) <= int(thresholds[position - 1]):
			non_increasing.append(position)
	check_eq(non_increasing, [],
		"the committed ladder is strictly increasing: no duplicate and no "
			+ "non-positive gap")
	# The one named one-based conversion, read out of the double's own source
	# rather than restated: the committed corpus's `xp 4` places level 1, which
	# is the curve's FIRST entry, and the zero-based reading would place it at 0
	# -- the contradiction that settles design D1.
	check_eq(str(curve[0]["name"]), "Slave",
		"the curve's FIRST entry is Slave at 0 experience")
	check_eq(str(curve[1]["name"]), "Servant",
		"the curve's SECOND entry is Servant at 40 experience")
	var requests_before: int = api.level_up_requests

	# --- the committed corpus's own state: the endpoint's first refusal.
	var corpus: Variant = await api.level_up_town(user_id)
	check(corpus is BootData.LevelUpResult,
		"level_up_town returns the typed result")
	_check_level_failure(corpus, "level_already_current",
		"the committed corpus (xp 4, level 1), which is already consistent "
			+ "under the one-based reading")
	check_eq(_level_recorded_of(api), LEVEL_CORPUS_LEVEL,
		"the refused intent changed no recorded level")
	# --- the endpoint's second refusal: a recorded level the experience cannot
	# reach. It is set in the double's OWN in-memory state, never in a fixture.
	_set_level_state(api, LEVEL_CORPUS_XP, LEVEL_UNREACHABLE)
	_check_level_failure(await api.level_up_town(user_id),
		"xp_below_threshold",
		"a recorded level the stored experience cannot reach")
	check_eq(_level_recorded_of(api), LEVEL_UNREACHABLE,
		"the refused intent changed no recorded level")

	# --- a real advancement, over an in-memory disagreement the committed
	# corpus is not in (xp 200 places level 5, the save records level 1).
	_set_level_state(api, LEVEL_DISAGREE_XP, LEVEL_CORPUS_LEVEL)
	var raised: Variant = await api.level_up_town(user_id)
	check(raised is BootData.LevelUpResult and raised.ok,
		"a recorded level below the derived one levels up offline: %s"
			% ((raised as BootData.LevelUpResult).error_message
				if raised is BootData.LevelUpResult else ""))
	_check_typed_level(raised)
	if raised is BootData.LevelUpResult and raised.ok:
		var typed: BootData.LevelUpResult = raised
		# The value-level half of the post-execution proof, in its strongest
		# form: a level change moves NO resource, so every stored balance is the
		# value the intent started from.
		for name: String in ["xp", "gold", "wood", "oil", "steel", "cash",
				"mana"]:
			var before_value := _level_resource_of(api, name)
			check_eq(_typed_resource(typed, name), before_value,
				"the %s balance is UNCHANGED by the level-up (the endpoint's "
					% name + "value-level proof)")
		check_eq(_level_recorded_of(api), LEVEL_DERIVED,
			"the double's own in-memory recorded level is the derived one")
		# An immediate repeat is refused by the endpoint's own first guard, now
		# against a state the double actually advanced.
		_check_level_failure(await api.level_up_town(user_id),
			"level_already_current",
			"a repeat once the recorded level IS the derived one")
	# A second disagreement at a different rung, so the curve block's facts are
	# read at more than one level.
	_set_level_state(api, LEVEL_LOW_XP, LEVEL_CORPUS_LEVEL)
	var lower: Variant = await api.level_up_town(user_id)
	if lower is BootData.LevelUpResult and lower.ok:
		var low: BootData.LevelUpResult = lower
		check_eq(low.derived_level, LEVEL_LOW_DERIVED,
			"100 experience places the curve's level 4")
		check_eq(low.curve.entry_name, "Peasant",
			"level 4's committed name is Peasant")
		check_eq(low.level_after, LEVEL_LOW_DERIVED,
			"the recorded level moved to exactly the derived level")
	else:
		check(false, "a second disagreement levels up offline")
	# The completed curve: the top level with genuinely NO next level.
	_check_level_top(api, user_id)

	# --- a curve whose FLOOR sits above the experience: the content failure the
	# committed curve cannot produce, reachable by stubbing the double's OWN
	# in-memory first threshold (design D1's ladder check then fails closed).
	_set_level_state(api, LEVEL_CORPUS_XP, LEVEL_CORPUS_LEVEL)
	_stub_level_floor(api, LEVEL_STUBBED_FLOOR)
	_check_level_failure(await api.level_up_town(user_id), "internal_error",
		"a curve whose floor sits above the stored experience, so NO level is "
			+ "derivable at all")
	_restore_level_floor(api)
	# With the REAL committed curve back, the corpus's own state is refused
	# again, which proves the stub was fully undone.
	_check_level_failure(await api.level_up_town(user_id), "level_already_current",
		"the restored committed curve refuses the corpus's own state again")

	# --- the save-identity codes.
	_check_level_failure(await api.level_up_town(""), "missing_user_id",
		"an empty save id")
	_check_level_failure(await api.level_up_town("ghost-0000"), "unknown_user_id",
		"an unknown save id")
	# --- the client can never dictate the outcome: the intent carries a save id
	# and NOTHING else, so there is no key through which a level could be sent.
	# The typed result's own field list is the structural proof: it has no
	# client-supplied level, only the service's three reported ones.
	var succeeded: Variant = await api.level_up_town(user_id)
	if succeeded is BootData.LevelUpResult and succeeded.ok:
		var done: BootData.LevelUpResult = succeeded
		check_eq(done.level_after, done.derived_level,
			"whatever the client sent, the recorded level equals the level the "
				+ "SERVICE derived")
		check(done.level_after >= 1 and done.level_after <= LEVEL_TOP,
			"the derived level is always inside the committed curve")
	else:
		check(true, "the corpus's own state is refused, so no level is applied")
	check_eq(api.level_up_requests, requests_before + 12,
		"every level_up_town call increments the intent counter exactly once "
			+ "(twelve calls: the corpus refusal, the below-threshold refusal, "
			+ "two advancements, the repeat refusal, the top-level advance and "
			+ "its repeat refusal, the stubbed-floor refusal, the "
			+ "restored-corpus refusal, the two save-identity refusals, and the "
			+ "client-dictation check)")
	info("level double reproduced the executed fixture's transaction, advanced a "
		+ "derived level over an in-memory disagreement, reached the completed "
		+ "curve, and answered seven structured refusals with no server and no "
		+ "socket")


## Every level failure carries the endpoint's code and NO partial payload
## (design D4/D7) - including the 409s `level_already_current` and
## `xp_below_threshold`, the 500 `internal_error`, and the two save-identity
## codes.
func _check_level_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.LevelUpResult, label + " returns the typed result")
	if not (result is BootData.LevelUpResult):
		return
	var typed: BootData.LevelUpResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.curve == null, label + " carries no partial curve block")
	check(typed.resources == null, label + " carries no partial resources")
	check_eq(typed.result, "", label + " reports no legacy result")
	check_eq(typed.derived_level, -1, label + " carries no partial derived level")
	check_eq(typed.level_before, -1,
		label + " carries no partial pre-execution level")
	check_eq(typed.level_after, -1,
		label + " carries no partial post-execution level")
	check_eq(typed.protocol, "", label + " carries no partial protocol")


## The typed result of one level-up: protocol, version, legacy result, the
## derived level, BOTH recorded levels, the committed curve facts, and the
## resources. The wall-clock field is asserted as a positive integer and never
## by value.
func _check_typed_level(result: Variant) -> void:
	check(result is BootData.LevelUpResult,
		"the level-up carries the typed result")
	if not (result is BootData.LevelUpResult):
		return
	var typed: BootData.LevelUpResult = result
	check(typed.ok, "the level-up response is a success: %s"
		% typed.error_message)
	if not typed.ok:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the level-up protocol is compat-v0")
	check_eq(typed.game_version, "alpha 0.02",
		"the level-up response carries the game version")
	check(typed.server_time > 0,
		"the level-up server_time is the fixture epoch (time-dependent)")
	check_eq(typed.result, "success", "the legacy result string is verbatim")
	check_eq(typed.level_before, LEVEL_CORPUS_LEVEL,
		"the pre-execution recorded level is the corpus's own")
	check_eq(typed.level_after, LEVEL_DERIVED,
		"the post-execution recorded level IS the derived level")
	check_eq(typed.level_after, typed.derived_level,
		"the service's own value-level guarantee: the recorded level after "
			+ "execution equals the derived level")
	check(typed.curve != null, "the response carries the committed curve facts")
	if typed.curve == null:
		return
	check_eq(typed.curve.entries, LEVEL_ENTRIES,
		"the curve block reports the committed entry count")
	check_eq(typed.curve.index_base, "one-based",
		"the curve block reports the ONE-BASED index base the double derived "
			+ "under (design D1)")
	check_eq(typed.curve.derivation_status, "derived-provisional",
		"the curve block reports the derived-provisional status")
	check_eq(typed.curve.rejected_alternative, "zero-based",
		"the curve block reports the REJECTED zero-based alternative")
	check_eq(typed.curve.entry_name, LEVEL_DERIVED_NAME,
		"the curve block reports the derived level's committed name")
	check_eq(typed.curve.entry_exp_required, LEVEL_DERIVED_THRESHOLD,
		"the curve block reports the derived level's committed threshold")
	check_eq(typed.curve.next_level, LEVEL_NEXT,
		"the curve block reports the NEXT LEVEL as a level, not as the "
			+ "conversion's positional index")
	check_eq(typed.curve.next_name, LEVEL_NEXT_NAME,
		"the curve block reports the next level's committed name")
	check_eq(typed.curve.next_exp_required, LEVEL_NEXT_THRESHOLD,
		"the curve block reports the next level's committed threshold")
	check_eq(typed.curve.remaining, LEVEL_NEXT_REMAINING,
		"the curve block reports the experience remaining")
	check_eq(typed.curve.xp, LEVEL_DISAGREE_XP,
		"the curve block reports the experience it derived from")
	check(typed.resources != null, "the response carries the resources")


## The completed curve: at the final threshold the derived level is the TOP one
## and there is genuinely NO next level, which the typed result reports as null
## rather than as a sentinel value.
func _check_level_top(api: Variant, user_id: String) -> void:
	_set_level_state(api, LEVEL_FINAL_THRESHOLD, LEVEL_CORPUS_LEVEL)
	var top: Variant = await api.level_up_town(user_id)
	check(top is BootData.LevelUpResult and top.ok,
		"an experience above the final threshold derives the TOP level")
	if not (top is BootData.LevelUpResult) or not top.ok:
		return
	var typed: BootData.LevelUpResult = top
	check_eq(typed.derived_level, LEVEL_TOP,
		"the derived level is the curve's last entry")
	check_eq(typed.curve.entry_name, LEVEL_TOP_NAME,
		"the top level's committed name is Conqueror")
	check(typed.curve.next_level == null,
		"a completed curve reports NO next level, not a sentinel")
	check(typed.curve.next_name == null,
		"a completed curve reports NO next name")
	check(typed.curve.next_exp_required == null,
		"a completed curve reports NO next threshold")
	check(typed.curve.remaining == null,
		"a completed curve reports NO remaining experience")
	check_eq(typed.level_after, LEVEL_TOP,
		"the recorded level moved to the top level")
	# And the endpoint's own first guard now refuses it by name.
	_check_level_failure(await api.level_up_town(user_id), "level_already_current",
		"the top level is already current")


# --- production-queue double (unit-queues design D8) ------------------------


## The committed executed-legacy queue fixture the double reproduces, asserted
## against the double's own in-memory state first — a push, then the three-key
## teardown, then every stored balance unchanged.
func _check_queue(api: Variant, user_id: String) -> void:
	var push_before := _read_fixture_object(FIXTURE_QUEUE_PUSH_BEFORE)
	var push_after := _read_fixture_object(FIXTURE_QUEUE_PUSH_AFTER)
	var pop_before := _read_fixture_object(FIXTURE_QUEUE_POP_BEFORE)
	var pop_after := _read_fixture_object(FIXTURE_QUEUE_POP_AFTER)
	if push_before.is_empty() or push_after.is_empty():
		return
	if pop_before.is_empty() or pop_after.is_empty():
		return
	var before_map: Dictionary = push_before["maps"][0]
	var after_map: Dictionary = push_after["maps"][0]
	var target: Array = _normalize(before_map["items"][QUEUE_TARGET_KEY]) as Array
	# The instant the executed push stamped is READ from the capture, never a
	# literal: the legacy branch stamps `timestamp_now()`, so the committed
	# fixture is the only authority for it and a re-capture must move every
	# assertion here with it.
	var recorded_stamp := int((_queue_attr(push_after) as Dictionary).get(
		"ts", 0))
	check(recorded_stamp > 0,
		"the executed queue push stamped a positive start instant")
	check_eq(target, QUEUE_TARGET_ROW,
		"the queue fixture's before state is the committed Command Center with an "
			+ "empty bag")
	check_eq(_queue_attr(push_before), {},
		"the executed push started from an empty bag")
	check_eq(_queue_attr(push_after), {"nu": 1, "ts": recorded_stamp},
		"the executed push set the count to 1 and stamped the start instant")
	check_eq(_queue_attr(pop_before), {"nu": 1, "ts": recorded_stamp},
		"the executed pop's before state is the push's own after state")
	check_eq(_queue_attr(pop_after), {},
		"the executed pop's teardown removed nu, ts, and ui TOGETHER")
	for key in ["xp", "gold", "wood", "oil", "steel", "expansions", "store"]:
		check_eq(after_map[key], before_map[key],
			"the executed queue transaction left map.%s byte-identical" % key)
	var differing: Array = []
	for key: Variant in before_map["items"].keys():
		if after_map["items"][key] != before_map["items"][key]:
			differing.append(str(key))
	check_eq(differing, [QUEUE_TARGET_KEY],
		"the executed queue transaction changed exactly the addressed row")
	check_eq((after_map["items"] as Dictionary).size(),
		(before_map["items"] as Dictionary).size(),
		"the executed queue transaction left the placement count at 40")
	check_eq(pop_after["playerInfo"], push_before["playerInfo"],
		"the executed queue transaction left the player info byte-identical")
	check_eq(pop_after["privateState"], push_before["privateState"],
		"the executed queue transaction left the private state byte-identical")

	var requests_before: int = api.queue_requests
	# --- the push, against the committed corpus's own empty bag.
	var pushed: Variant = await api.push_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	check(pushed is BootData.QueueResult,
		"push_queue_unit_town returns the typed result")
	_check_typed_queue(pushed, "push")
	if pushed is BootData.QueueResult and pushed.ok:
		var typed: BootData.QueueResult = pushed
		check_eq(typed.action, "push", "the echoed action is the push")
		check_eq(typed.map_key, QUEUE_TARGET_MAP_KEY,
			"the addressed key is the one the client named")
		check_eq(int(typed.queue.count), 1,
			"the push derived the committed count of 1")
		check_eq(int(typed.queue.start_instant), recorded_stamp,
			"the push stamped the fixture's committed instant, never a clock")
		check_eq((typed.queue.keys as Array), ["nu", "ts"],
			"the post-execution bag carries exactly nu and ts")
		check_eq(bool(typed.queue.absent_is_absent), true,
			"the service states its own absence rule")
		check_eq(_typed_row_attr(typed.previous), {},
			"the response's previous row is the row the client named, empty")
		check_eq(_typed_row_attr(typed.row), {"nu": 1, "ts": recorded_stamp},
			"the response's post-execution row carries the derived queue")
		check_eq(int(typed.previous.x), int(typed.row.x),
			"a queue command rewrites the row IN PLACE: the cell is unchanged")
		# The value-level half of the endpoint's proof: a queue moves NO
		# resource, so every stored balance is the value it started from.
		for name: String in ["xp", "gold", "wood", "oil", "steel", "cash",
				"mana"]:
			check_eq(_typed_queue_resource(typed, name),
				QUEUE_CORPUS_RESOURCES.get(name, -99),
				"the %s balance is UNCHANGED by the push (the endpoint's "
					% name + "value-level proof)")
	# --- the pop, against the row the push just queued: the three-key teardown.
	var popped: Variant = await api.pop_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	check(popped is BootData.QueueResult,
		"pop_queue_unit_town returns the typed result")
	_check_typed_queue(popped, "pop")
	if popped is BootData.QueueResult and popped.ok:
		var typed: BootData.QueueResult = popped
		check_eq(typed.action, "pop", "the echoed action is the pop")
		check_eq(_typed_row_attr(typed.previous), {"nu": 1,
			"ts": recorded_stamp},
			"the pop's before row carried the pushed count and instant")
		check_eq(_typed_row_attr(typed.row), {},
			"the pop's teardown removed nu, ts, and ui TOGETHER")
		check_eq(bool(typed.queue.present), false,
			"the post-teardown projection reports the queue as ABSENT")
		check_eq(typed.queue.count, null,
			"the post-teardown count is null, which a zero cannot say")
		check_eq((typed.queue.keys as Array), [],
			"the post-teardown bag carries no committed key at all")
		for name: String in ["xp", "gold", "wood", "oil", "steel", "cash",
				"mana"]:
			check_eq(_typed_queue_resource(typed, name),
				QUEUE_CORPUS_RESOURCES.get(name, -99),
				"the %s balance is UNCHANGED by the pop" % name)
	# --- two pushes then a PARTIAL decrement: the branch's own middle case, where
	# `nu` and `ts` are re-written and NO key is torn down. It is unreachable
	# against the committed corpus (whose push only ever produces count 1), so it
	# is exercised over the double's own in-memory state — never a fixture.
	var first_again: Variant = await api.push_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	if first_again is BootData.QueueResult and first_again.ok:
		check_eq(int((first_again as BootData.QueueResult).queue.count), 1,
			"a push onto a torn-down row sets the count to 1")
	var twice: Variant = await api.push_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	if twice is BootData.QueueResult and twice.ok:
		check_eq(int((twice as BootData.QueueResult).queue.count), 2,
			"a second push INCREMENTS the committed count to 2, which is the "
				+ "engine's own (nu + 1) rule")
	var partial: Variant = await api.pop_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	if partial is BootData.QueueResult and partial.ok:
		var typed_partial: BootData.QueueResult = partial
		check_eq(int(typed_partial.queue.count), 1,
			"a partial decrement leaves the count at 1")
		check_eq(bool(typed_partial.queue.present), true,
			"a partial decrement tears NOTHING down")
		check_eq((typed_partial.queue.keys as Array), ["nu", "ts"],
			"a partial decrement leaves both committed keys in place")
		check_eq(_typed_row_attr(typed_partial.row), {"nu": 1,
			"ts": recorded_stamp},
			"a partial decrement re-writes nu and re-stamps ts")
	await api.pop_queue_unit_town(user_id, QUEUE_TARGET_MAP_KEY)
	# --- the inert pop: a row whose bag carries no count is a recorded NO-OP,
	# not an error. Legacy's helper returns without writing anything, and the
	# endpoint answers success — so the double must answer success too.
	var inert: Variant = await api.pop_queue_unit_town(user_id,
		QUEUE_TARGET_MAP_KEY)
	check(inert is BootData.QueueResult and inert.ok,
		"a pop against an already-torn-down row is an inert recorded no-op, "
			+ "not an error: %s"
			% ((inert as BootData.QueueResult).error_message
				if inert is BootData.QueueResult else ""))
	if inert is BootData.QueueResult and inert.ok:
		check_eq(_typed_row_attr((inert as BootData.QueueResult).row), {},
			"the inert pop wrote nothing at all")
		check_eq(bool((inert as BootData.QueueResult).queue.present), false,
			"the inert pop leaves the queue reported as absent")
		check_eq(_typed_row_attr((inert as BootData.QueueResult).previous), {},
			"the inert pop's previous row is already empty")
	# --- every fail-closed code, in the endpoint's own order.
	_check_queue_failure(await api.push_queue_unit_town("", QUEUE_TARGET_MAP_KEY),
		"missing_user_id", "an empty save id")
	_check_queue_failure(await api.push_queue_unit_town("no-such-save-000",
		QUEUE_TARGET_MAP_KEY), "unknown_user_id", "an unknown save id")
	_check_queue_failure(await api.pop_queue_unit_town(user_id, -1),
		"invalid_map_key", "a negative key")
	_check_queue_failure(await api.pop_queue_unit_town(user_id,
		QUEUE_UNKNOWN_KEY), "unknown_map_key",
		"a key that names no placement in the save")
	# A refused intent leaves the addressed row byte-identical.
	check_eq(_double_queue_attr(api), {},
		"every refused queue intent left the addressed row's bag untouched")
	for name: String in ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]:
		check_eq(_double_queue_resource(api, name),
			QUEUE_CORPUS_RESOURCES.get(name, -99),
			"the %s balance is unchanged by every refused queue intent" % name)
	# --- the wire contract: the facade's two operations carry ONLY the save
	# identity and the target key, so there is no channel through which a client
	# could dictate a count, a cost, a duration, or a readiness.
	check_eq(api.queue_requests, requests_before + 11,
		"the facade counted every queue intent it issued: two for the recorded "
			+ "pair, five for the two pushes, the partial decrement, the teardown "
			+ "and the inert pop, and four refusals")
	check(_queue_argument_count(api) == 2,
		"each queue operation takes EXACTLY the save identity and the target "
			+ "key: there is no parameter through which a client could send an "
			+ "outcome")
	check_eq(BootData.QUEUE_ACTIONS, ["push", "pop"],
		"the closed action vocabulary is exactly the push and the pop")
	info("queue double reproduced the executed fixture's push and three-key "
		+ "teardown plus an inert no-op, and answered six structured refusals "
		+ "with no server and no socket")


## One typed queue result's own shape: two rows, the queue block, and the seven
## resources — with no readiness, remaining time, progress, completion, or cost
## field anywhere on either typed class.
func _check_typed_queue(result: Variant, label: String) -> void:
	if not (result is BootData.QueueResult):
		check(false, "%s queue result is typed" % label)
		return
	var typed: BootData.QueueResult = result
	check_eq(typed.protocol, BootData.PROTOCOL, "%s protocol is compat-v0" % label)
	check_eq(typed.result, "success", "%s carries the legacy success result" % label)
	check(typed.server_time > 0,
		"%s server_time is a positive integer (time-dependent field)" % label)
	check(typed.previous != null and typed.row != null,
		"%s carries BOTH rows: the pre-execution row and the post-execution one"
			% label)
	check(typed.queue != null, "%s carries the queue projection" % label)
	check(typed.resources != null, "%s carries the resources" % label)
	if typed.queue != null:
		check_eq(bool(typed.queue.absent_is_absent), true,
			"%s states that an absent queue is absent" % label)


## Structured failure for one queue intent: the service's own code, with no
## partial payload.
func _check_queue_failure(result: Variant, code: String, label: String) -> void:
	check(result is BootData.QueueResult and not result.ok,
		"%s fails with a structured result" % label)
	if not (result is BootData.QueueResult):
		return
	var typed: BootData.QueueResult = result
	check_eq(typed.error_code, code,
		"%s names the service's own code (got %s: %s)"
			% [label, typed.error_code, typed.error_message])
	check(typed.previous == null and typed.row == null and typed.queue == null
			and typed.resources == null and typed.result == "",
		"%s carries no partial payload" % label)


## One committed save's addressed row attribute bag, with the transport's integral
## floats normalised to integers.
func _queue_attr(document: Dictionary) -> Dictionary:
	var items: Dictionary = document["maps"][0]["items"]
	return _normalize((items[QUEUE_TARGET_KEY] as Array)[6]) as Dictionary


## One typed row's attribute bag.
func _typed_row_attr(row: Variant) -> Dictionary:
	if row == null or not (row is BootData.Placement):
		return {}
	return _typed_attr((row as BootData.Placement).attr)


## One typed result's stored balance, under the field's own name.
func _typed_queue_resource(typed: BootData.QueueResult, name: String) -> int:
	if typed.resources == null:
		return -99
	match name:
		"xp":
			return int(typed.resources.xp)
		"gold":
			return int(typed.resources.gold)
		"wood":
			return int(typed.resources.wood)
		"oil":
			return int(typed.resources.oil)
		"steel":
			return int(typed.resources.steel)
		"cash":
			return int(typed.resources.cash)
		"mana":
			return int(typed.resources.mana)
	return -99


## The double's own in-memory addressed bag, read from the LIVE implementation
## instance — its observable in-process state, never a transport payload.
func _double_queue_attr(api: Variant) -> Variant:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return "unreachable"
	var rows: Dictionary = double._queue_state["rows"]
	if not rows.has(QUEUE_TARGET_KEY):
		return "no such row"
	return _normalize(((rows[QUEUE_TARGET_KEY] as Array)[6]))


## One stored balance of the double's own in-memory queue state.
func _double_queue_resource(api: Variant, name: String) -> int:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return -99
	return int(double._queue_state[name])


## How many parameters the facade's own queue operations declare, read from the
## method list rather than assumed: two are the save identity and the target
## key, and any more would be a channel through which a client could dictate an
## outcome, which design D2/D5 forbids.
func _queue_argument_count(api: Variant) -> int:
	var script: Variant = api.get_script()
	if script == null:
		return -1
	var counts: Array = []
	for method: Dictionary in script.get_script_method_list():
		var name := str(method.get("name", ""))
		if name == "push_queue_unit_town" or name == "pop_queue_unit_town":
			counts.append((method.get("args", []) as Array).size())
	if counts.size() != 2:
		return -1
	return int(counts[0])


## The pinned engine's JSON parser widens every committed number to a float;
## this normalises them to integers so a comparison against a literal holds
## without weakening the value.
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


## The double's own in-memory recorded level, read from the LIVE implementation
## instance the facade selected. This is the double's observable in-process
## state, never a transport payload.
func _level_recorded_of(api: Variant) -> int:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return -99
	return int(double._level_state["level"])


## One stored balance of the double's own in-memory state.
func _level_resource_of(api: Variant, name: String) -> int:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return -99
	return int(double._level_state[name])


## One typed result's stored balance, under the field's own name.
func _typed_resource(typed: BootData.LevelUpResult, name: String) -> int:
	if typed.resources == null:
		return -99
	match name:
		"xp":
			return int(typed.resources.xp)
		"gold":
			return int(typed.resources.gold)
		"wood":
			return int(typed.resources.wood)
		"oil":
			return int(typed.resources.oil)
		"steel":
			return int(typed.resources.steel)
		"cash":
			return int(typed.resources.cash)
		"mana":
			return int(typed.resources.mana)
	return -99


## Parks the double's OWN in-memory experience and recorded level, so the
## advancement the committed corpus cannot reach becomes reachable offline. The
## committed fixture and the committed configuration are never written: this
## lives entirely in this process's memory.
func _set_level_state(api: Variant, xp: int, level: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its level state")
		return
	double._level_state["xp"] = xp
	double._level_state["level"] = level


## Replaces the double's OWN in-memory curve FLOOR, so the content failure the
## committed curve cannot produce becomes reachable offline (the client-side
## mirror of the compat suite's own accessor stub). The committed configuration
## is never written.
func _stub_level_floor(api: Variant, threshold: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its curve")
		return
	var curve: Array = double._config_payload["levels"] as Array
	if not (double._level_schedule_backup.has("curve")):
		double._level_schedule_backup["curve"] = curve.duplicate(true)
	(curve[0] as Dictionary)["exp_required"] = int(threshold)


## Restores the double's own curve floor from the backup the stub took, so a
## later check reads the REAL committed ladder again.
func _restore_level_floor(api: Variant) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return
	if not double._level_schedule_backup.has("curve"):
		return
	var backup: Array = double._level_schedule_backup["curve"] as Array
	var curve: Array = double._config_payload["levels"] as Array
	(curve[0] as Dictionary)["exp_required"] = \
		int((backup[0] as Dictionary)["exp_required"])


## Replaces ONE row of the double's OWN in-memory schedule, so a priced and
## requirement-free row exists for the affordability refusal the committed
## table cannot produce (the client-side mirror of the compat suite's own
## accessor stub). The committed fixture and the committed configuration are
## never written.
func _stub_expand_row(api: Variant, index: int, row: Dictionary) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its schedule")
		return
	var schedule: Array = double._config_payload["expansion_prices"] as Array
	if not (double._expand_schedule_backup.has("rows")):
		double._expand_schedule_backup["rows"] = \
			(schedule as Array).duplicate(true)
	var rows: Array = double._expand_schedule_backup["rows"] as Array
	(rows[index] as Dictionary)["coins"] = int(row["coins"])
	(rows[index] as Dictionary)["cash"] = int(row["cash"])
	(rows[index] as Dictionary)["neighbors"] = int(row["neighbors"])
	(rows[index] as Dictionary)["inventory_qte"] = int(row["inventory_qte"])
	(schedule as Array)[index] = (rows[index] as Dictionary).duplicate()


## Restores the double's schedule row from the backup the stub took.
func _restore_expand_row(api: Variant, index: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		return
	if not double._expand_schedule_backup.has("rows"):
		return
	var rows: Array = double._expand_schedule_backup["rows"] as Array
	var schedule: Array = double._config_payload["expansion_prices"] as Array
	(schedule as Array)[index] = (rows[index] as Dictionary).duplicate()


## Raises the double's OWN in-memory gold and cash balances so a priced row the
## fresh corpus could not afford becomes affordable. The committed corpus is
## never written.
func _top_up_expand_balance(api: Variant, gold: int, cash: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its balances")
		return
	double._expand_state["gold"] = gold
	double._expand_state["cash"] = cash


## Parks one extra row (and, when supplied, one extra config item) inside the
## double's OWN in-memory state, so the refusals no placed corpus row can
## produce become reachable offline. The committed fixture is never written.
## `stamp` is the row's collection instant, so a crafted row can sit a second
## short of a committed rung.
func _park_collect_row(api: Variant, index: int, item_id: int,
		attr: Dictionary, stamp: int, config_item: Variant) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its "
			+ "in-memory state")
		return
	(double._collect_state["items"] as Dictionary)[str(index)] = [
		item_id, 5, 5, stamp, 0, [], attr, 1]
	if config_item is Dictionary:
		(double._config_items as Dictionary)[str(item_id)] = config_item


## Parks one extra row under a key the committed corpus does not name, inside
## the double's IN-MEMORY state only (the committed fixture is never written),
## so the one `no_build_time` refusal a start can produce becomes reachable.
## This is the client-side mirror of the compat suite's own accessor stub.
func _park_row(api: Variant, index: int, item_id: int) -> void:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its "
			+ "in-memory state")
		return
	(double._construction_state["items"] as Dictionary)[str(index)] = [
		item_id, 5, 5, 0, 0, [], {}, 1]


## One recorded attribute bag in the canonical typed form (the JSON transport
## widens the save's ints to floats on the pinned engine).
func _typed_attr(value: Variant) -> Dictionary:
	var out := {}
	if not (value is Dictionary):
		return out
	for key: Variant in (value as Dictionary):
		var amount: Variant = (value as Dictionary)[key]
		out[str(key)] = int(amount) if (amount is int or amount is float) \
			else amount
	return out


## Every upgrade failure carries the endpoint's code and no partial payload
func _check_upgrade_failure(result: Variant, code: String,
		label: String) -> void:
	check(result is BootData.UpgradeResult,
		label + " returns the typed result")
	if not (result is BootData.UpgradeResult):
		return
	var typed: BootData.UpgradeResult = result
	check(not typed.ok, label + " is a structured failure")
	check_eq(typed.error_code, code, label + " names the endpoint's code")
	check(typed.removed == null, label + " carries no partial removed row")
	check(typed.upgraded == null, label + " carries no partial upgraded row")
	check(typed.resources == null, label + " carries no partial resources")
	check_eq(typed.result, "",
		label + " reports no legacy result for a failed upgrade")


## One typed `BootData.Placement` back in the legacy eight-field array, so
## the double's two sides can be compared with the fixture's own rows.
func _boot_row(entry: Variant) -> Array:
	if entry == null or not (entry is BootData.Placement):
		return []
	var typed: BootData.Placement = entry
	return [typed.item_id, typed.x, typed.y, typed.timestamp,
		typed.orientation, typed.store, typed.attr, typed.player]


## The fake double's own in-memory bought-units list, read from the LIVE
## implementation instance the facade selected (`GameApi._impl`, not a name
## lookup — a reconfigured node stays a child until the frame ends, so a name
## lookup can return the replaced instance). This is the double's observable
## in-process state (the purchase half's bookkeeping the typed response does
## not carry), never a transport payload: the executed fixture's own
## `boughtUnits` is the oracle it is compared against.
func _bought_units(api: Variant) -> Array:
	var double: Variant = api._impl
	if double == null or not (double is FakeApi):
		check(false, "the fake double instance is reachable for its "
			+ "in-memory state")
		return []
	return (double._upgrade_state["bought_units"] as Array).duplicate()


## The capture's recorded entry timestamp — the entry the after-state adds
## over the before-state (the deterministic epoch the double stamps).
func _fixture_placement_epoch(before: Dictionary, after: Dictionary) -> int:
	var before_items: Dictionary = before["maps"][0]["items"]
	var after_items: Dictionary = after["maps"][0]["items"]
	for key: Variant in after_items:
		if not before_items.has(str(key)):
			var entry: Variant = after_items[key]
			if entry is Array and (entry as Array).size() == 8:
				return int((entry as Array)[3])
	return 0


## Committed fixture object, or {} when unreadable (already reported).
func _read_fixture_object(relative: String) -> Dictionary:
	var path := Paths.repo_root().path_join(relative)
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "fixture is readable: " + path)
	if handle == null:
		return {}
	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	handle = null
	if not (parsed is Dictionary):
		check(false, "fixture is a JSON object: " + path)
		return {}
	return parsed
