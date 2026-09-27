extends "res://tests/test_base.gd"
## Headless GameApi suite for the legacy-v0 implementation (task 3.3, spec
## "Boot live against Compatibility API").
##
## Requires a running Compatibility API v0 on loopback — verify-boot.ps1
## wraps this suite with `compat_live_phase.py`, which starts
## `apps/compat-api/run.py` (disposable corpus) and tears it down again. The
## suite compares every live typed result against the fake implementation's,
## so both must yield the same boot data (time-dependent fields excepted).

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

	info("legacy_v0 matched the fake reference over loopback %s" % endpoint)


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))
