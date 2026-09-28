extends "res://tests/test_base.gd"
## Headless GameApi suite for the fake implementation (spec "Boot offline
## with the fake implementation" and "Place through either implementation";
## tasks 3.1/3.2).
##
## Hermetic by construction: no Compatibility API is started — verify-boot
## runs this suite before any service exists — and the scope test restricts
## the compat endpoint and the HTTP request client to the legacy-v0
## implementation file, which this suite never selects. Expected values are
## read from the committed executed-legacy fixtures (read-only), including
## the placement fixture the placement double mutates in memory over.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const FIXTURE_PLACE_BEFORE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/before.json"
const FIXTURE_PLACE_AFTER := \
	"tests/fixtures/godot-building-placement/steps/command_buy/after.json"


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
