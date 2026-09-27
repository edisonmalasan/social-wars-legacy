extends "res://tests/test_base.gd"
## Headless GameApi suite for the fake implementation (task 3.2, spec
## "Boot offline with the fake implementation").
##
## Hermetic by construction: no Compatibility API is started — verify-boot
## runs this suite before any service exists — and the scope test restricts
## the compat endpoint and the HTTP request client to the legacy-v0
## implementation file, which this suite never selects. Expected values are
## read from the committed executed-legacy fixtures (read-only).

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"


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
