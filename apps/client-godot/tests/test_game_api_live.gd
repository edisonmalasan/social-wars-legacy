extends "res://tests/test_base.gd"
## Headless GameApi suite for the legacy-v0 implementation (task 3.3, spec
## "Boot live against Compatibility API"; extended by the
## building-placement change's task 3.2 with the placement parity of spec
## "Place through either implementation").
##
## Requires a running Compatibility API v0 on loopback — verify-boot.ps1
## wraps this suite with `compat_live_phase.py`, which starts
## `apps/compat-api/run.py` (disposable corpus) and tears it down again. The
## suite compares every live typed result against the fake implementation's,
## so both must yield the same boot data and the same placement results
## (time-dependent fields excepted).

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const ARG_ENDPOINT := "--gameapi-endpoint="
const UNKNOWN_USER := "does-not-exist-0000"


func run_scenario() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var endpoint := _endpoint()
	check(endpoint != "", "endpoint resolved from the runtime override or "
		+ "the project setting")
	if endpoint == "":
		return

	# Fake reference first: the live results must match these typed shapes.
	api.configure("fake")
	var fake_ref: Variant = await api.list_sessions()
	check(fake_ref is BootData.SaveListResult,
		"fake reference returns the typed result")
	if not (fake_ref is BootData.SaveListResult):
		return
	var fake_list: BootData.SaveListResult = fake_ref
	check(fake_list.ok, "fake reference resolves: %s" % fake_list.error_message)
	check(fake_list.saves.size() > 0, "fake reference names at least one save")
	if not fake_list.ok or fake_list.saves.is_empty():
		return

	api.configure("legacy_v0", endpoint)
	check_eq(api.implementation_name(), "legacy_v0",
		"implementation switch selects legacy_v0")
	var live: Variant = await api.list_sessions()
	check(live is BootData.SaveListResult,
		"live list_sessions returns the typed result")
	if not (live is BootData.SaveListResult):
		return
	var live_list: BootData.SaveListResult = live
	check(live_list.ok, "live session list resolves over loopback: %s"
		% live_list.error_message)
	if not live_list.ok:
		return
	check_eq(live_list.protocol, fake_list.protocol,
		"live protocol equals the fake's")
	check_eq(live_list.game_version, fake_list.game_version,
		"live game version equals the fake's")
	check_eq(live_list.saves.size(), fake_list.saves.size(),
		"live save count equals the fake's")
	check(live_list.server_time > 0, "live server_time is a positive epoch")
	# List order is not part of the v0 contract; compare id-keyed.
	var fake_by_id := {}
	for save in fake_list.saves:
		fake_by_id[save.id] = save
	for live_save in live_list.saves:
		check(fake_by_id.has(live_save.id),
			"live save id %s exists in the fake list" % live_save.id)
		if fake_by_id.has(live_save.id):
			var other: BootData.SaveInfo = fake_by_id[live_save.id]
			check_eq(live_save.name, other.name,
				"save %s name equals the fake's" % live_save.id)
			check_eq(live_save.xp, other.xp,
				"save %s xp equals the fake's" % live_save.id)
			check_eq(live_save.level, other.level,
				"save %s level equals the fake's" % live_save.id)

	var user_id: String = fake_list.saves[0].id
	var fake_boot: Variant = await api.get_bootstrap(user_id)
	check(fake_boot is BootData.BootstrapResult
		and fake_boot.ok, "fake bootstrap reference resolves")

	api.configure("legacy_v0", endpoint)
	var live_boot: Variant = await api.get_bootstrap(user_id)
	check(live_boot is BootData.BootstrapResult,
		"live get_bootstrap returns the typed result")
	if not (live_boot is BootData.BootstrapResult):
		return
	var result: BootData.BootstrapResult = live_boot
	check(result.ok, "live bootstrap resolves over loopback: %s"
		% result.error_message)
	if not result.ok:
		return
	check_eq(result.protocol, BootData.PROTOCOL,
		"live bootstrap protocol is compat-v0")
	check(result.summary != null, "live bootstrap carries a typed summary")
	check(result.config != null and not result.config.raw.is_empty(),
		"live config payload is wrapped and non-empty")
	check(result.player_info != null, "live player_info payload is wrapped")
	if fake_boot is BootData.BootstrapResult and fake_boot.ok \
			and result.summary != null:
		var reference: BootData.BootstrapResult = fake_boot
		check_eq(result.summary.name, reference.summary.name,
			"live summary name equals the fake's")
		check_eq(result.summary.level, reference.summary.level,
			"live summary level equals the fake's")
		check_eq(result.summary.xp, reference.summary.xp,
			"live summary xp equals the fake's")
		check_eq(result.game_version, reference.game_version,
			"live bootstrap game version equals the fake's")
		# Stable keys only: values of time-dependent config fields differ by
		# design (field-stability record), so compare the shape, not values.
		var keys_ok := true
		for key in reference.config.raw.keys():
			if not result.config.raw.has(key):
				keys_ok = false
		check(keys_ok, "live config carries the fixture's top-level keys")
		if result.player_info != null and reference.player_info != null:
			check_eq(result.player_info.player_name,
				reference.player_info.player_name,
				"live typed player name equals the fake's")

	var unknown: Variant = await api.get_bootstrap(UNKNOWN_USER)
	check(unknown is BootData.BootstrapResult,
		"live unknown user returns the typed result")
	if unknown is BootData.BootstrapResult:
		var failure: BootData.BootstrapResult = unknown
		check(not failure.ok, "live unknown user fails")
		check_eq(failure.error_code, "unknown_user_id",
			"live structured error code matches the fake's")
		check(failure.summary == null,
			"live structured failure carries no summary")

	await _check_live_placement(api, endpoint, user_id)

	info("legacy_v0 matched the fake reference over loopback %s" % endpoint)


## Placement through both implementations (task 3.2, spec "Place through
## either implementation"): identical typed shapes, identical authoritative
## values (both sides derive from the committed fresh save), the live
## entry's wall-clock timestamp as the only time-dependent field, and the
## endpoint's structured codes passing through unchanged.
func _check_live_placement(api: Variant, endpoint: String,
		user_id: String) -> void:
	# Fake reference: in-memory state, fixture epoch, fixture-derived values.
	api.configure("fake")
	var fake_ref: Variant = await api.place_building(user_id, 1, 51, 39)
	check(fake_ref is BootData.PlacementResult,
		"fake place_building returns the typed result")
	if not (fake_ref is BootData.PlacementResult):
		return
	var fake: BootData.PlacementResult = fake_ref
	check(fake.ok, "fake placement reference resolves: %s"
		% fake.error_message)
	if not fake.ok:
		return

	# The same intent against the running Compatibility API.
	api.configure("legacy_v0", endpoint)
	var live_ref: Variant = await api.place_building(user_id, 1, 51, 39)
	check(live_ref is BootData.PlacementResult,
		"live place_building returns the typed result")
	if not (live_ref is BootData.PlacementResult):
		return
	var live: BootData.PlacementResult = live_ref
	check(live.ok, "live placement resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check_eq(live.protocol, fake.protocol,
		"live placement protocol equals the fake's")
	check_eq(live.result, "success", "live reports the legacy success result")
	check(live.placement != null and fake.placement != null,
		"both placements carry a typed entry")
	check(live.resources != null and fake.resources != null,
		"both placements carry typed resources")
	if live.placement == null or fake.placement == null \
			or live.resources == null or fake.resources == null:
		return
	check_eq(live.placement.item_id, fake.placement.item_id,
		"placement item id equals the fake's")
	check_eq(live.placement.x, fake.placement.x,
		"placement anchor x equals the fake's")
	check_eq(live.placement.y, fake.placement.y,
		"placement anchor y equals the fake's")
	check_eq(live.placement.orientation, fake.placement.orientation,
		"placement orientation equals the fake's")
	check_eq(live.placement.player, fake.placement.player,
		"placement player team equals the fake's")
	check_eq(live.placement.store.size(), fake.placement.store.size(),
		"placement store equals the fake's")
	check(live.placement.attr == fake.placement.attr,
		"placement attr equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.placement.attr),
		JSON.stringify(fake.placement.attr)])
	check(fake.placement.timestamp > 0,
		"fake entry timestamp is the fixture epoch (deterministic)")
	check(live.placement.timestamp > 0,
		"live entry timestamp is a positive wall-clock epoch (time-dependent)")
	# Same committed fresh save on both sides: authoritative resources
	# agree, and wood pins both to the documented fixture values.
	check_eq(live.resources.xp, fake.resources.xp, "xp equals the fake's")
	check_eq(live.resources.gold, fake.resources.gold,
		"gold equals the fake's")
	check_eq(live.resources.wood, fake.resources.wood,
		"wood equals the fake's")
	check_eq(live.resources.oil, fake.resources.oil,
		"oil equals the fake's")
	check_eq(live.resources.steel, fake.resources.steel,
		"steel equals the fake's")
	check_eq(live.resources.cash, fake.resources.cash,
		"cash equals the fake's")
	check_eq(live.resources.mana, fake.resources.mana,
		"mana equals the fake's")
	check_eq(live.resources.wood, 1970,
		"wood is the committed fresh 2000 minus the w30 cost")

	# Structured service errors pass through with their original codes.
	var live_bad_item: Variant = await api.place_building(
		user_id, 999999999, 51, 39)
	check(live_bad_item is BootData.PlacementResult,
		"live unknown item returns the typed result")
	if live_bad_item is BootData.PlacementResult:
		var bad_item: BootData.PlacementResult = live_bad_item
		check(not bad_item.ok, "live unknown item is a structured failure")
		check_eq(bad_item.error_code, "unknown_item_id",
			"live structured error passes through with the endpoint's code")
		check(bad_item.placement == null and bad_item.resources == null,
			"live structured failure carries no partial payload")
	var live_bad_grid: Variant = await api.place_building(user_id, 1, 100, 39)
	check(live_bad_grid is BootData.PlacementResult,
		"live out-of-grid anchor returns the typed result")
	if live_bad_grid is BootData.PlacementResult:
		var bad_grid: BootData.PlacementResult = live_bad_grid
		check(not bad_grid.ok,
			"live out-of-grid anchor is a structured failure")
		check_eq(bad_grid.error_code, "invalid_coordinates",
			"live grid violation names the endpoint's code")
		check(bad_grid.placement == null and bad_grid.resources == null,
			"live grid failure carries no partial payload")

	# The fake derives the same code for the same intent (structured-failure
	# parity; the double never talks to the service).
	api.configure("fake")
	var fake_bad_item: Variant = await api.place_building(
		user_id, 999999999, 51, 39)
	check(fake_bad_item is BootData.PlacementResult and not fake_bad_item.ok,
		"fake fails the same intent offline")
	if fake_bad_item is BootData.PlacementResult:
		check_eq(fake_bad_item.error_code, "unknown_item_id",
			"structured codes match between implementations")


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))
