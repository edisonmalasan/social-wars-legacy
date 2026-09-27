extends "res://tests/test_base.gd"
## GameClock suite (OpenSpec `godot-game-clock` tasks 1.3 / 2.1, spec:
## "Clock scaffold" + "Change notifications" + "Boot integration").
##
## Scaffold half: no implicit anchor exists at startup, a valid anchor
## commits the epoch and notifies observers once, invalid anchors fail
## closed with committed state untouched, pause freezes reported time
## across frames while resume continues it, manual advance moves time by
## exactly the requested count only while paused (every invalid request
## fails closed), and clearing returns to unanchored under the documented
## signal rules (including the silent repeated clear). Tick payloads must
## strictly increase within the current base.
##
## Boot-integration half: a successful boot against the fake
## implementation anchors the clock to the fixture response epoch; a
## follow-up attempt against a loopback endpoint with nothing listening
## clears that anchor on entry and leaves the clock unanchored. The
## endpoint arrives as `--gameapi-endpoint=` — this file hardcodes no
## endpoint (transport tokens are restricted to the legacy-v0
## implementation file).
##
## Runs headless as part of `verify-boot.ps1`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const FIXTURE_PLAYER_INFO := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const ARG_ENDPOINT := "--gameapi-endpoint="
const STATE_TIMEOUT_MSEC := 60000
const EPOCH_RANGE_SEC := 60

## Epoch values observed via the anchoring signal, in emission order.
var _anchored_values: Array = []
## Number of observed clearing notifications.
var _cleared_events := 0
## Paused-state values observed via the pause-state signal, in order.
var _paused_states: Array = []
## Elapsed payloads observed via the time-change signal, in order.
var _tick_payloads: Array = []
## Last tick payload of the current base (-1 after every rebase).
var _last_tick_payload := -1
## Count of tick payloads that failed to strictly increase within their
## base (asserted once at the end, so the check count stays deterministic
## no matter how many frames the run lasts).
var _tick_regressions := 0


func run_scenario() -> void:
	var clock: Variant = root.get_node_or_null("GameClock")
	check(clock != null, "GameClock autoload is registered")
	if clock == null:
		return
	clock.clock_anchored.connect(_on_clock_anchored)
	clock.clock_cleared.connect(_on_clock_cleared)
	clock.clock_paused_changed.connect(_on_clock_paused_changed)
	clock.clock_ticked.connect(_on_clock_ticked)

	_check_no_implicit_anchor(clock)
	_check_reject_anchor_while_unanchored(clock)
	_check_anchor_once(clock)
	_check_reject_anchor_while_anchored(clock)
	# `await` on the two helpers that suspend internally; the plain sync
	# helpers resolve immediately (test_base pattern).
	await _check_pause_resume(clock)
	_check_advance(clock)
	_check_clear(clock)
	_check_transition_notifications(clock)
	await _check_boot_integration(clock)
	# Spec: "Notify every advance" — one monotonicity verdict over every
	# tick of the whole run (all bases), recorded without per-frame checks.
	check_eq(_tick_regressions, 0,
		"tick payloads strictly increase within every base")


## Spec: "Start without an implicit anchor".
func _check_no_implicit_anchor(clock: Variant) -> void:
	check(not clock.is_anchored(), "no anchor exists at startup")
	check(not clock.is_paused(), "the clock starts in the running state")
	check_eq(clock.server_time(), 0, "startup server time is zero")
	check_eq(clock.now_epoch_sec(), 0, "startup epoch is zero")
	check_eq(_anchored_values.size(), 0, "startup notifies nobody")
	check_eq(_cleared_events, 0, "startup clears nobody")
	check_eq(_paused_states.size(), 0, "startup changes no pause state")


## Spec: "Reject an invalid anchor" (pre-anchor half): a non-positive
## timestamp before any anchor keeps the clock unanchored and silent.
func _check_reject_anchor_while_unanchored(clock: Variant) -> void:
	var zero: Dictionary = clock.anchor(0)
	check(zero.get("ok") == false, "a zero timestamp is rejected")
	check(String(zero.get("error", "")).find("positive server_time") != -1,
		"the zero-timestamp error names the violated condition")
	check(not clock.is_anchored(),
		"a rejected pre-anchor leaves the clock unanchored")

	var negative: Dictionary = clock.anchor(-5)
	check(negative.get("ok") == false, "a negative timestamp is rejected")
	check_eq(clock.server_time(), 0, "the server time stays zero")
	check_eq(clock.now_epoch_sec(), 0, "the epoch stays zero")
	check_eq(_anchored_values.size(), 0, "rejected anchors notify nobody")


## Spec: "Anchor once to the response epoch".
func _check_anchor_once(clock: Variant) -> void:
	var ts := _fixture_server_time()
	check(ts > 0, "fixture server timestamp exists")
	if ts <= 0:
		return
	var ticks_before := _tick_payloads.size()
	var granted: Dictionary = clock.anchor(ts)
	check(granted.get("ok") == true, "a positive anchor returns ok")
	check_eq(String(granted.get("error", "")), "",
		"a successful anchor carries no error")
	check(clock.is_anchored(), "the anchor commits the clock")
	check_eq(clock.server_time(), ts, "the getter reports the committed epoch")
	check_eq(clock.elapsed_msec(), 0, "the anchor zeroes the elapsed base")
	check_eq(clock.now_epoch_sec(), ts,
		"the same-frame epoch equals the anchor exactly")
	check(not clock.is_paused(),
		"the anchor leaves the running state untouched")
	check_eq(_anchored_values.size(), 1, "observers are notified exactly once")
	if _anchored_values.size() == 1:
		check_eq(_anchored_values[0], ts,
			"the notification names the committed epoch")
	check_eq(_tick_payloads.size(), ticks_before,
		"the anchor itself emits no time-change notification")


## Spec: "Reject an invalid anchor" (anchored half): a second anchor is
## rejected until `clear()` re-bases, and the committed state is untouched.
func _check_reject_anchor_while_anchored(clock: Variant) -> void:
	var ts: int = clock.server_time()
	var elapsed_before: int = clock.elapsed_msec()
	var again: Dictionary = clock.anchor(ts + 100)
	check(again.get("ok") == false, "a second anchor is rejected")
	check(String(again.get("error", "")).find("already anchored") != -1,
		"the re-anchor error names the violated condition")
	check_eq(clock.server_time(), ts, "the committed epoch is untouched")
	check_eq(clock.elapsed_msec(), elapsed_before,
		"the elapsed base is untouched")
	check_eq(_anchored_values.size(), 1, "rejected anchors never notify")


## Spec: "Pause freezes time and resume continues it".
func _check_pause_resume(clock: Variant) -> void:
	var elapsed_frozen: int = clock.elapsed_msec()
	var epoch_frozen: int = clock.now_epoch_sec()
	clock.pause()
	check(clock.is_paused(), "pause commits the paused state")
	check_eq(_paused_states.size(), 1, "pausing notifies observers exactly once")
	if _paused_states.size() == 1:
		check_eq(_paused_states[0], true,
			"the notification names the paused state")
	clock.pause()
	check_eq(_paused_states.size(), 1,
		"a repeated pause is a no-op that notifies nobody")

	var ticks_before := _tick_payloads.size()
	for _i in range(5):
		await process_frame
	check_eq(clock.elapsed_msec(), elapsed_frozen,
		"paused elapsed time does not move across frames")
	check_eq(clock.now_epoch_sec(), epoch_frozen,
		"the paused epoch does not move across frames")
	check_eq(_tick_payloads.size(), ticks_before,
		"a paused clock emits no time-change notifications")

	clock.resume()
	check(not clock.is_paused(), "resume returns to the running state")
	check_eq(_paused_states.size(), 2, "resuming notifies observers exactly once")
	if _paused_states.size() == 2:
		check_eq(_paused_states[1], false,
			"the notification names the running state")
	clock.resume()
	check_eq(_paused_states.size(), 2,
		"a repeated resume is a no-op that notifies nobody")

	var deadline := Time.get_ticks_msec() + STATE_TIMEOUT_MSEC
	while clock.elapsed_msec() <= elapsed_frozen \
			and Time.get_ticks_msec() < deadline:
		await process_frame
	check(clock.elapsed_msec() > elapsed_frozen,
		"time advances again after resuming")
	check(clock.now_epoch_sec() >= epoch_frozen,
		"the resumed epoch is never behind its frozen value")
	check(_tick_payloads.size() > ticks_before,
		"the resumed advance notifies observers")


## Spec: "Advance exactly while paused, fail closed otherwise".
func _check_advance(clock: Variant) -> void:
	clock.pause()
	check(clock.is_paused(), "the clock is paused for the advance checks")
	var elapsed_before: int = clock.elapsed_msec()
	var epoch_before: int = clock.now_epoch_sec()
	var ticks_before := _tick_payloads.size()

	var granted: Dictionary = clock.advance(1000)
	check(granted.get("ok") == true, "a positive advance while paused returns ok")
	check_eq(clock.elapsed_msec(), elapsed_before + 1000,
		"advance moves elapsed time by exactly the requested count")
	check_eq(clock.now_epoch_sec(), epoch_before + 1,
		"advance moves the epoch by exactly one second")
	check_eq(_tick_payloads.size(), ticks_before + 1,
		"one manual advance emits one time-change notification")
	if not _tick_payloads.is_empty():
		check_eq(_tick_payloads[_tick_payloads.size() - 1],
			elapsed_before + 1000,
			"the notification payload equals the committed elapsed time")

	var zero: Dictionary = clock.advance(0)
	check(zero.get("ok") == false, "a zero advance is rejected")
	check(String(zero.get("error", "")).find("positive") != -1,
		"the zero-advance error names the violated condition")
	var negative: Dictionary = clock.advance(-100)
	check(negative.get("ok") == false, "a negative advance is rejected")
	check_eq(clock.elapsed_msec(), elapsed_before + 1000,
		"rejected advances leave the state unchanged")
	check_eq(_tick_payloads.size(), ticks_before + 1,
		"rejected advances never notify")

	clock.resume()
	check(not clock.is_paused(), "the clock runs again")
	var running_elapsed: int = clock.elapsed_msec()
	var running_ticks := _tick_payloads.size()
	var while_running: Dictionary = clock.advance(500)
	check(while_running.get("ok") == false,
		"an advance while running is rejected")
	check(String(while_running.get("error", "")).find("paused clock") != -1,
		"the running-advance error names the violated condition")
	check_eq(clock.elapsed_msec(), running_elapsed,
		"a rejected running advance leaves the state unchanged")
	check_eq(_tick_payloads.size(), running_ticks,
		"a rejected running advance never notifies")


## Spec: "Clear back to unanchored".
func _check_clear(clock: Variant) -> void:
	check(clock.is_anchored(), "the clock is anchored before the clear")
	clock.clear()
	check(not clock.is_anchored(), "clear returns to unanchored")
	check_eq(clock.server_time(), 0, "clear resets the server time")
	check_eq(clock.now_epoch_sec(), 0, "clear resets the epoch")
	check_eq(clock.elapsed_msec(), 0, "clear zeroes the elapsed base")
	check(not clock.is_paused(), "clear leaves the running state untouched")
	check_eq(_cleared_events, 1,
		"clearing an anchored clock notifies exactly once")
	check_eq(_anchored_values.size(), 1,
		"the clear emits no anchoring notification")

	clock.clear()
	check_eq(_cleared_events, 1,
		"a repeated clear is a no-op that notifies nobody")
	check_eq(clock.now_epoch_sec(), 0,
		"the repeated clear keeps the clock unanchored")


## Spec: "Notify transitions once" — the counts and sequences recorded by
## the scaffold half (the boot half adds its own transitions afterwards).
func _check_transition_notifications(clock: Variant) -> void:
	check_eq(_anchored_values.size(), 1,
		"exactly one anchoring transition was notified")
	check_eq(_cleared_events, 1,
		"exactly one clearing transition was notified")
	check_eq(_paused_states, [true, false, true, false],
		"the pause-state transitions are notified in order, once each")


## Spec: "Boot integration" — attempt 1 (fake) must reach ready with the
## clock anchored to the fixture response epoch; attempt 2 (legacy_v0
## against a dead loopback endpoint) must fail and leave the clock
## unanchored, so the previous anchor is cleared rather than kept.
func _check_boot_integration(clock: Variant) -> void:
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
	var ts := _fixture_server_time()
	check(ts > 0, "fixture server timestamp exists")
	if ts <= 0:
		return

	# Attempt 1: the fake implementation reaches ready and anchors the clock.
	api.configure("fake")
	_anchored_values.clear()
	_cleared_events = 0
	_paused_states.clear()
	var ready: Variant = _add_boot_scene()
	if ready == null:
		return
	var ready_state := await _wait_for_terminal(ready)
	check_eq(ready_state, "ready",
		"the first boot reaches ready with the fake implementation")
	check(clock.is_anchored(), "the clock is anchored at ready")
	check_eq(clock.server_time(), ts,
		"the clock names the response epoch")
	var now: int = clock.now_epoch_sec()
	check(now >= ts,
		"the anchored epoch is at or ahead of the response timestamp")
	check(now <= ts + EPOCH_RANGE_SEC,
		"the anchored epoch is within a bounded post-anchor interval "
		+ "(got %d vs %d)" % [now, ts])
	check(not clock.is_paused(), "the clock runs at ready")
	check_eq(_anchored_values.size(), 1,
		"the boot anchor notifies observers exactly once")
	if _anchored_values.size() == 1:
		check_eq(_anchored_values[0], ts,
			"the boot notification names the response epoch")
	check_eq(_cleared_events, 0,
		"the clear before the first attempt (already unanchored) stays silent")
	_remove_scene(ready)

	# Attempt 2: a failing boot replaces the anchored clock with none.
	api.configure("legacy_v0", endpoint)
	var failing: Variant = _add_boot_scene()
	if failing == null:
		return
	var failing_state := await _wait_for_terminal(failing)
	check_eq(failing_state, "error",
		"the follow-up boot fails against the dead endpoint")
	check(not clock.is_anchored(),
		"the failing attempt leaves no anchor behind")
	check_eq(clock.server_time(), 0,
		"no stale server time survives the failed attempt")
	check_eq(clock.now_epoch_sec(), 0,
		"no stale epoch survives the failed attempt")
	check_eq(_cleared_events, 1,
		"the new attempt cleared the previously anchored clock")
	check_eq(_anchored_values.size(), 1,
		"the failed attempt never anchors")
	check(not clock.is_paused(),
		"the failed attempt leaves the clock running")
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


## The fixture capture's legacy server timestamp — the epoch the fake
## implementation reports as `server_time` (a time-dependent field, so it
## is used for range assertions, never for exact value comparison).
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


func _on_clock_anchored(server_time: int) -> void:
	_anchored_values.append(server_time)
	_last_tick_payload = -1


func _on_clock_cleared() -> void:
	_cleared_events += 1
	_last_tick_payload = -1


func _on_clock_paused_changed(paused: bool) -> void:
	_paused_states.append(paused)


func _on_clock_ticked(payload: int) -> void:
	_tick_payloads.append(payload)
	if payload <= _last_tick_payload:
		_tick_regressions += 1
	_last_tick_payload = payload
