extends "res://tests/test_base.gd"
## Headless boot-scene suite (task 3.4, spec "Boot scene").
##
## Scenarios:
##   (default)   fake implementation, no server: the boot reaches "ready"
##               and the displayed summary equals the fixture save.
##   unreachable legacy_v0 against a loopback endpoint with nothing
##               listening: the scene enters an error state that names the
##               connection failure.
##   api-error   a structured API error (unknown save id): the scene
##               displays that error instead of an empty or guessed summary.
##
## Every scenario also asserts the `Session` scaffold state (spec
## `godot-session`): active with the fixture save at ready, and inactive
## after either failure mode.
##
## The failure scenarios receive their endpoint and save id from
## verify-boot.ps1 as user arguments (`--gameapi-endpoint=`, `--boot-user=`,
## `--gameapi=`); this file hardcodes no endpoint. The api-error scenario
## runs hermetically with `--gameapi=fake` or live against the service.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const ARG_ENDPOINT := "--gameapi-endpoint="
const ARG_IMPLEMENTATION := "--gameapi="
const ARG_BOOT_USER := "--boot-user="
const STATE_TIMEOUT_MSEC := 60000


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
	root.add_child(scene)
	var final := await _wait_for_terminal(scene)
	check(final != "", "boot scene reached a terminal state")
	if final == "":
		return
	match scenario:
		"":
			_assert_ready(scene)
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


func _assert_ready(scene: Variant) -> void:
	check_eq(str(scene.state), "ready",
		"boot reaches the ready state with the fake implementation")
	if str(scene.state) != "ready":
		return
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
