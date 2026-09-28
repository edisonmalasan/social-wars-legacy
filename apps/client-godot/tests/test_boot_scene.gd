extends "res://tests/test_base.gd"
## Headless boot-scene suite (task 3.4, spec "Boot scene").
##
## Scenarios:
##   (default)   fake implementation, no server: the boot reaches "ready"
##               and the displayed summary equals the fixture save; the
##               launch makes exactly one bootstrap request and never
##               instantiates the town scene headlessly; a directly
##               requested boot-to-town handoff reuses that request
##               (building the 40-placement town) and a payload-less
##               handoff routes to the explicit error with no partial
##               town (task 7.1).
##   unreachable legacy_v0 against a loopback endpoint with nothing
##               listening: the scene enters an error state that names the
##               connection failure.
##   api-error   a structured API error (unknown save id): the scene
##               displays that error instead of an empty or guessed summary.
##
## Every scenario also asserts the `Session` scaffold state (spec
## `godot-session`): active with the fixture save at ready, and inactive
## after either failure mode, and the `GameClock` anchor (spec
## `godot-game-clock`): anchored to the fixture response epoch at ready,
## and unanchored with a zero epoch after either failure mode.
##
## The failure scenarios receive their endpoint and save id from
## verify-boot.ps1 as user arguments (`--gameapi-endpoint=`, `--boot-user=`,
## `--gameapi=`); this file hardcodes no endpoint. The api-error scenario
## runs hermetically with `--gameapi=fake` or live against the service.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const FIXTURE_PLAYER_INFO := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const ARG_ENDPOINT := "--gameapi-endpoint="
const ARG_IMPLEMENTATION := "--gameapi="
const ARG_BOOT_USER := "--boot-user="
const STATE_TIMEOUT_MSEC := 60000
## Bounded post-anchor interval for the ready epoch (time-dependent value:
## asserted as a flag and a range, never an exact wall-clock comparison).
const EPOCH_RANGE_SEC := 60


func run_scenario() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	if not _configure_for_scenario(api):
		return

	var scene: Variant = load("res://scenes/boot.tscn").instantiate()
	check(scene != null, "boot scene loads")
	if scene == null:
		return
	scene.auto_quit = false
	var requests_before: int = api.bootstrap_requests
	root.add_child(scene)
	var final := await _wait_for_terminal(scene)
	check(final != "", "boot scene reached a terminal state")
	if final == "":
		return
	match scenario:
		"":
			_assert_ready(scene, requests_before)
			_assert_handoff(scene, api)
		"unreachable":
			_assert_unreachable(scene, _arg(ARG_ENDPOINT))
		"api-error":
			_assert_api_error(scene, _arg(ARG_BOOT_USER))
		_:
			fail("unhandled scenario: %s" % scenario)


func _configure_for_scenario(api: Variant) -> bool:
	match scenario:
		"":
			api.configure("fake")
			return true
		"unreachable":
			var endpoint := _arg(ARG_ENDPOINT)
			check(endpoint != "",
				"scenario 'unreachable' needs --gameapi-endpoint=<loopback "
				+ "url with nothing listening>")
			if endpoint == "":
				return false
			api.configure("legacy_v0", endpoint)
			return true
		"api-error":
			var user := _arg(ARG_BOOT_USER)
			check(user != "", "scenario 'api-error' needs --boot-user=<save id>")
			if user == "":
				return false
			var implementation := _arg(ARG_IMPLEMENTATION)
			if implementation == "":
				implementation = "legacy_v0"
			api.configure(implementation, _arg(ARG_ENDPOINT))
			return true
		_:
			fail("unknown scenario: %s" % scenario)
			return false


## Waits until the boot reaches a terminal state (bounded, no hang).
func _wait_for_terminal(scene: Variant) -> String:
	var deadline := Time.get_ticks_msec() + STATE_TIMEOUT_MSEC
	while scene.state == "" and Time.get_ticks_msec() < deadline:
		await process_frame
	return str(scene.state)


func _assert_ready(scene: Variant, requests_before: int) -> void:
	check_eq(str(scene.state), "ready",
		"boot reaches the ready state with the fake implementation")
	if str(scene.state) != "ready":
		return
	# Spec `godot-compatibility-boot` "Windowed boot-to-town transition":
	# exactly one bootstrap request per launch, and the headless run never
	# enters the town scene.
	var api: Variant = root.get_node_or_null("GameApi")
	if api != null:
		check_eq(int(api.bootstrap_requests) - requests_before, 1,
			"exactly one bootstrap request was made for the launch")
	check(root.get_node_or_null("Town") == null,
		"the headless boot never instantiates the town scene")
	var expected := _fixture_first_save()
	check(expected.size() > 0, "fixture save exists")
	if expected.is_empty():
		return
	check(scene.summary != null, "boot exposes a typed summary")
	if scene.summary != null:
		check_eq(scene.summary.name, str(expected["name"]),
			"displayed summary name equals the fixture save")
		check_eq(scene.summary.level, int(expected["level"]),
			"displayed summary level equals the fixture save")
		check_eq(scene.summary.xp, int(expected["xp"]),
			"displayed summary xp equals the fixture save")
	# The displayed label text is asserted through the display fields the
	# labels are assigned from (single source in boot.gd).
	check_eq(str(scene.displayed_name), str(expected["name"]),
		"UI shows the fixture save's name")
	check_eq(str(scene.displayed_level), str(int(expected["level"])),
		"UI shows the fixture save's level")
	check_eq(str(scene.displayed_xp), str(int(expected["xp"])),
		"UI shows the fixture save's xp")
	check_eq(str(scene.game_version), "alpha 0.02",
		"boot shows the fixture game version")
	check(str(scene.engine_version).contains("4.7.2"),
		"boot shows the pinned engine version (got %s)"
		% str(scene.engine_version))
	check(str(scene.connection_state).contains("connected"),
		"connection state reports connected (got %s)"
		% str(scene.connection_state))
	check_eq(str(scene.displayed_error), "",
		"no error text is displayed on success")
	check_eq(str(scene.boot_user_id), str(expected["id"]),
		"boot targeted the fixture save id")
	# Spec `godot-session`: "Session active at ready".
	var session: Variant = root.get_node_or_null("Session")
	check(session != null, "Session autoload is registered")
	if session != null:
		check(session.is_active(), "the session is active at ready")
		check_eq(str(session.user_id()), str(expected["id"]),
			"the session names the bootstrapped save")
		var active_summary: Variant = session.summary()
		check(active_summary != null,
			"the active session carries a typed summary")
		if active_summary != null:
			check_eq(active_summary.name, str(expected["name"]),
				"the session summary name equals the fixture save")
			check_eq(active_summary.level, int(expected["level"]),
				"the session summary level equals the fixture save")
			check_eq(active_summary.xp, int(expected["xp"]),
				"the session summary xp equals the fixture save")
	# Spec `godot-game-clock`: "Anchored clock at ready".
	var clock: Variant = root.get_node_or_null("GameClock")
	check(clock != null, "GameClock autoload is registered")
	if clock != null:
		check(clock.is_anchored(), "the clock is anchored at ready")
		check(not clock.is_paused(), "the clock runs at ready")
		var ts := _fixture_server_time()
		check(ts > 0, "fixture server timestamp exists")
		if ts > 0:
			var now: int = clock.now_epoch_sec()
			check(now >= ts,
				"the anchored epoch is at or ahead of the response timestamp")
			check(now <= ts + EPOCH_RANGE_SEC,
				"the anchored epoch is within a bounded post-anchor interval "
				+ "(got %d vs %d)" % [now, ts])


## Spec `godot-compatibility-boot` "Windowed boot-to-town transition"
## (task 7.1): a directly requested handoff reuses the validated payload
## with no second bootstrap request, and a handoff without a payload
## routes to the explicit error with no partial town and no blank view.
## The headless automatic path is gated in `_complete()` and asserted
## above (no town instantiated during the boot itself).
func _assert_handoff(scene: Variant, api: Variant) -> void:
	var requests_before: int = api.bootstrap_requests
	var handoff: Dictionary = scene.transition_to_town()
	check(bool(handoff.get("ok", false)),
		"a requested handoff builds the town: %s" % handoff.get("error"))
	check_eq(int(api.bootstrap_requests), requests_before,
		"the handoff issues no additional bootstrap request")
	var town: Variant = root.get_node_or_null("Town")
	check(town != null, "the town scene exists after the handoff")
	if town != null:
		check_eq(str(town.view_state), "built", "the town view builds")
		check_eq(town.objects.size(), 40,
			"the town renders the save's 40 placements")
		check(town.build_ok, "the handed town view is committed")
	check_eq(scene.visible, false,
		"a successful handoff replaces the boot view")
	check_eq(str(scene.state), "ready",
		"a successful handoff leaves the boot state ready")

	# Failure routing: no payload -> explicit error naming the condition,
	# boot view showing the error (never blank), no partial town.
	if town != null:
		town.free()
	scene.player_info = null
	var failed: Dictionary = scene.transition_to_town()
	check(not bool(failed.get("ok", true)),
		"a payload-less handoff fails closed")
	check_eq(str(scene.state), "error",
		"the failed handoff commits the explicit error state")
	check(String(scene.error_code).begins_with("town_state"),
		"the failure names the handoff condition: %s" % scene.error_code)
	check(String(scene.displayed_error).contains(str(scene.error_code)),
		"the explicit error is displayed: %s" % scene.displayed_error)
	check_eq(scene.visible, true,
		"the error view replaces the town (never a blank window)")
	check(root.get_node_or_null("Town") == null,
		"no partial town survives the failed handoff")


func _assert_unreachable(scene: Variant, endpoint: String) -> void:
	check_eq(str(scene.state), "error",
		"boot enters the error state when the endpoint is unreachable")
	if str(scene.state) != "error":
		return
	check_eq(str(scene.error_code), "unreachable_endpoint",
		"error state names the unreachable-endpoint failure")
	check(str(scene.error_message).contains("refused")
		or str(scene.error_message).contains("unreachable"),
		"error message names the connection failure (got %s)"
		% str(scene.error_message))
	if endpoint != "":
		check(str(scene.error_message).contains(endpoint.get_slice("://", 1)),
			"error message names the endpoint (got %s)"
			% str(scene.error_message))
	check(scene.summary == null, "no summary exists on failure")
	check_eq(str(scene.displayed_name), "", "no player name is displayed")
	check(str(scene.displayed_error).contains("unreachable_endpoint"),
		"the failure is displayed (got %s)" % str(scene.displayed_error))
	_assert_no_session_after_failure("unreachable")
	_assert_no_anchor_after_failure("unreachable")


func _assert_api_error(scene: Variant, user_id: String) -> void:
	check_eq(str(scene.state), "error",
		"boot enters the error state on a structured API error")
	if str(scene.state) != "error":
		return
	check_eq(str(scene.error_code), "unknown_user_id",
		"error state carries the structured API error code")
	check(str(scene.error_message).contains(user_id),
		"error message names the unknown save id (got %s)"
		% str(scene.error_message))
	check(scene.summary == null,
		"no summary exists on a structured API error")
	check_eq(str(scene.displayed_name), "",
		"no player name is displayed on a structured API error")
	check(str(scene.displayed_error).contains("unknown_user_id"),
		"the structured error is displayed (got %s)"
		% str(scene.displayed_error))
	_assert_no_session_after_failure("structured API error")
	_assert_no_anchor_after_failure("structured API error")


## Spec `godot-session`: "No session after a failed boot" — each failure
## mode must leave the scaffold inactive with no stale user id or summary.
func _assert_no_session_after_failure(label: String) -> void:
	var session: Variant = root.get_node_or_null("Session")
	check(session != null, "Session autoload is registered")
	if session == null:
		return
	check(not session.is_active(),
		"no session exists after a %s boot" % label)
	check_eq(str(session.user_id()), "",
		"no stale user id survives a %s boot" % label)
	check(session.summary() == null,
		"no stale summary survives a %s boot" % label)


## Spec `godot-game-clock`: "No anchor after a failed boot" — each failure
## mode must leave the clock unanchored with no stale epoch.
func _assert_no_anchor_after_failure(label: String) -> void:
	var clock: Variant = root.get_node_or_null("GameClock")
	check(clock != null, "GameClock autoload is registered")
	if clock == null:
		return
	check(not clock.is_anchored(),
		"the clock is unanchored after a %s boot" % label)
	check_eq(clock.server_time(), 0,
		"no stale server time survives a %s boot" % label)
	check_eq(clock.now_epoch_sec(), 0,
		"the epoch is zero after a %s boot" % label)


func _arg(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


## The first save of the committed fixture save list (expected values).
func _fixture_first_save() -> Dictionary:
	var path := Paths.repo_root().path_join(FIXTURE_SAVE_LIST)
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "fixture save list is readable: " + path)
	if handle == null:
		return {}
	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	handle = null
	if not (parsed is Dictionary):
		check(false, "fixture save list is a JSON object")
		return {}
	var typed: Dictionary = parsed
	var saves: Variant = typed.get("saves")
	if not (saves is Array) or saves.is_empty() \
			or not (saves[0] is Dictionary):
		check(false, "fixture save list carries a first save")
		return {}
	return saves[0]


## The fixture capture's legacy server timestamp — the epoch the fake
## implementation reports as `server_time` (time-dependent, so it is used
## for range assertions, never for exact value comparison).
func _fixture_server_time() -> int:
	var path := Paths.repo_root().path_join(FIXTURE_PLAYER_INFO)
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "fixture player info is readable: " + path)
	if handle == null:
		return 0
	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	handle = null
	if not (parsed is Dictionary):
		check(false, "fixture player info is a JSON object")
		return 0
	return BootData._parse_epoch((parsed as Dictionary).get("timestamp"))
