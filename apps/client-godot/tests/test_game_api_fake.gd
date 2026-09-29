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
