extends "res://tests/test_base.gd"
## Session suite (OpenSpec `godot-session` tasks 1.2 / 2.1, spec:
## "Session scaffold" + "Boot integration").
##
## Scaffold half: no implicit session exists at startup, a valid
## activation commits the getters and notifies observers once, an invalid
## activation fails closed with committed state untouched, and clearing
## returns to inactive under the documented signal rules (including the
## silent repeated clear).
##
## Boot-integration half: a successful boot against the fake
## implementation commits the fixture save into the session; a follow-up
## attempt against a loopback endpoint with nothing listening replaces it
## with no session left behind. The endpoint arrives as
## `--gameapi-endpoint=` — this file hardcodes no endpoint (transport
## tokens are restricted to the legacy-v0 implementation file).
##
## Runs headless as part of `verify-boot.ps1`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_SAVE_LIST := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const ARG_ENDPOINT := "--gameapi-endpoint="
const STATE_TIMEOUT_MSEC := 60000

## User ids observed via the activation signal, in emission order.
var _activated_ids: Array = []
## Number of observed clearing notifications.
var _cleared_events := 0


func run_scenario() -> void:
	var session: Variant = root.get_node_or_null("Session")
	check(session != null, "Session autoload is registered")
	if session == null:
		return
	session.session_activated.connect(_on_session_activated)
	session.session_cleared.connect(_on_session_cleared)

	_check_no_implicit_session(session)
	_check_reject_invalid_while_inactive(session)
	_check_activate(session)
	_check_reject_invalid_while_active(session)
	_check_clear(session)
	await _check_boot_integration(session)


## Spec: "Start without an implicit session".
func _check_no_implicit_session(session: Variant) -> void:
	check(not session.is_active(), "no session exists at startup")
	check_eq(session.user_id(), "", "startup user id is empty")
	check(session.summary() == null, "startup summary is null")
	check_eq(_activated_ids.size(), 0, "startup notifies nobody")


## Spec: "Reject an invalid activation" (pre-activation half): an invalid
## request before any activation keeps the scaffold inactive and silent.
func _check_reject_invalid_while_inactive(session: Variant) -> void:
	var rejected: Dictionary = session.activate("",
		_summary("u1", "Placeholder", 1, 0))
	check(rejected.get("ok") == false, "an empty user id is rejected")
	check(String(rejected.get("error", "")).find("non-empty user id") != -1,
		"the error names the violated condition")
	check(not session.is_active(),
		"a rejected pre-activation leaves the scaffold inactive")
	check_eq(_activated_ids.size(), 0, "a rejected activation notifies nobody")


## Spec: "Activate a session explicitly".
func _check_activate(session: Variant) -> void:
	var granted: Dictionary = session.activate("u1",
		_summary("u1", "Tester", 3, 40))
	check(granted.get("ok") == true, "a valid activation returns ok")
	check(session.is_active(), "the activation commits an active session")
	check_eq(session.user_id(), "u1", "the getter reports the committed id")
	var summary: Variant = session.summary()
	check(summary != null, "the getter reports a typed summary")
	if summary != null:
		check_eq(summary.name, "Tester", "summary name matches the input")
		check_eq(summary.level, 3, "summary level matches the input")
		check_eq(summary.xp, 40, "summary xp matches the input")
	check_eq(_activated_ids.size(), 1, "observers are notified exactly once")
	if _activated_ids.size() == 1:
		check_eq(_activated_ids[0], "u1",
			"the notification names the committed id")
	check_eq(_cleared_events, 0, "activation emits no clearing notification")


## Spec: "Reject an invalid activation": every invalid input fails with an
## explicit error and the already-committed session is untouched.
func _check_reject_invalid_while_active(session: Variant) -> void:
	var no_id: Dictionary = session.activate("",
		_summary("u2", "Intruder", 9, 9))
	check(no_id.get("ok") == false, "an empty user id is rejected mid-session")
	_assert_session_unchanged(session, "empty-id")

	var no_summary: Dictionary = session.activate("u1", null)
	check(no_summary.get("ok") == false,
		"a null summary is rejected mid-session")
	check(String(no_summary.get("error", "")).find("typed summary") != -1,
		"the null-summary error names the violated condition")
	_assert_session_unchanged(session, "null-summary")

	var mismatch: Dictionary = session.activate("u1",
		_summary("u2", "Intruder", 9, 9))
	check(mismatch.get("ok") == false, "a mismatched summary is rejected")
	check(String(mismatch.get("error", "")).find("'u2'") != -1,
		"the mismatch error names the offending summary id")
	_assert_session_unchanged(session, "mismatch")

	check_eq(_activated_ids.size(), 1, "rejected activations never notify")
	check_eq(_cleared_events, 0, "rejected activations never clear")


## Spec: "Clear back to inactive".
func _check_clear(session: Variant) -> void:
	session.clear()
	check(not session.is_active(), "clear returns to inactive")
	check_eq(session.user_id(), "", "clear resets the user id")
	check(session.summary() == null, "clear resets the summary")
	check_eq(_cleared_events, 1,
		"clearing an active session notifies exactly once")
	check_eq(_activated_ids.size(), 1, "clear emits no activation")

	session.clear()
	check_eq(_cleared_events, 1,
		"a repeated clear is a no-op that notifies nobody")
	check(not session.is_active(),
		"the repeated clear keeps the scaffold inactive")


## Asserts the committed session is still the one activated before the
## rejected requests (spec: state unchanged on failure).
func _assert_session_unchanged(session: Variant, label: String) -> void:
	check(session.is_active(), label + ": the session stays active")
	check_eq(session.user_id(), "u1", label + ": the user id is untouched")
	var summary: Variant = session.summary()
	check(summary != null, label + ": the summary stays committed")
	if summary != null:
		check_eq(summary.name, "Tester",
			label + ": the summary content is untouched")


## Spec: "Boot integration" — attempt 1 (fake) must reach ready with the
## session active and equal to the fixture save; attempt 2 (legacy_v0
## against a dead loopback endpoint) must fail and leave no session, so
## the previously active one is replaced rather than kept.
func _check_boot_integration(session: Variant) -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var endpoint := _arg(ARG_ENDPOINT)
	check(endpoint != "",
		"the follow-up failure needs " + ARG_ENDPOINT
		+ "<loopback url with nothing listening>")
	if endpoint == "":
		return
	var expected := _fixture_first_save()
	check(expected.size() > 0, "fixture save exists")
	if expected.is_empty():
		return

	# Attempt 1: the fake implementation reaches ready and commits the session.
	api.configure("fake")
	_activated_ids.clear()
	_cleared_events = 0
	var ready: Variant = _add_boot_scene()
	if ready == null:
		return
	var ready_state := await _wait_for_terminal(ready)
	check_eq(ready_state, "ready",
		"the first boot reaches ready with the fake implementation")
	check(session.is_active(), "the session is active at ready")
	check_eq(session.user_id(), str(expected["id"]),
		"the session names the bootstrapped save")
	var active_summary: Variant = session.summary()
	check(active_summary != null, "the active session carries a summary")
	if active_summary != null:
		check_eq(active_summary.name, str(expected["name"]),
			"the session summary name equals the fixture save")
		check_eq(active_summary.level, int(expected["level"]),
			"the session summary level equals the fixture save")
		check_eq(active_summary.xp, int(expected["xp"]),
			"the session summary xp equals the fixture save")
	check_eq(str(ready.boot_user_id), str(session.user_id()),
		"the session equals the boot target")
	check_eq(_activated_ids.size(), 1,
		"the boot activation notifies observers exactly once")
	check_eq(_cleared_events, 0,
		"the clear before the first attempt (already inactive) stays silent")
	_remove_scene(ready)

	# Attempt 2: a failing boot replaces the active session with none.
	api.configure("legacy_v0", endpoint)
	var failing: Variant = _add_boot_scene()
	if failing == null:
		return
	var failing_state := await _wait_for_terminal(failing)
	check_eq(failing_state, "error",
		"the follow-up boot fails against the dead endpoint")
	check(not session.is_active(),
		"the failing attempt leaves no session behind")
	check_eq(session.user_id(), "",
		"no stale user id survives the failed attempt")
	check(session.summary() == null,
		"no stale summary survives the failed attempt")
	check_eq(_cleared_events, 1,
		"the new attempt cleared the previously active session")
	check_eq(_activated_ids.size(), 1,
		"the failed attempt never activates")
	_remove_scene(failing)


## Adds a fresh boot scene with tests' headless mode (no auto-quit).
func _add_boot_scene() -> Variant:
	var scene: Variant = load("res://scenes/boot.tscn").instantiate()
	check(scene != null, "boot scene loads")
	if scene == null:
		return null
	scene.auto_quit = false
	root.add_child(scene)
	return scene


## Removes a finished boot scene from the tree before the next attempt.
func _remove_scene(scene: Variant) -> void:
	root.remove_child(scene)
	scene.free()


## Waits until the boot reaches a terminal state (bounded, no hang).
func _wait_for_terminal(scene: Variant) -> String:
	var deadline := Time.get_ticks_msec() + STATE_TIMEOUT_MSEC
	while scene.state == "" and Time.get_ticks_msec() < deadline:
		await process_frame
	return str(scene.state)


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


func _summary(user_id: String, display_name: String,
		level: int, xp: int) -> BootData.PlayerSummary:
	var summary := BootData.PlayerSummary.new()
	summary.user_id = user_id
	summary.name = display_name
	summary.level = level
	summary.xp = xp
	return summary


func _on_session_activated(user_id: String) -> void:
	_activated_ids.append(user_id)


func _on_session_cleared() -> void:
	_cleared_events += 1
