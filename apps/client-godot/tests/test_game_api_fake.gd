extends "res://tests/test_base.gd"
## Headless GameApi suite for the fake implementation (spec "Boot offline
## with the fake implementation", "Place through either implementation",
## and "Purchase through either implementation"; tasks 3.1/3.2/3.3).
##
## Hermetic by construction: no Compatibility API is started — verify-boot
## runs this suite before any service exists — and the scope test restricts
## the compat endpoint and the HTTP request client to the legacy-v0
## implementation file, which this suite never selects. Expected values are
## read from the committed executed-legacy fixtures (read-only), including
## the placement and purchase fixtures the two doubles mutate in memory
## over.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

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
