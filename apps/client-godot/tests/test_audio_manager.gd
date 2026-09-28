extends "res://tests/test_base.gd"
## AudioManager suite (OpenSpec `godot-settings-audio` tasks 1.2 / 2.2,
## spec: "AudioManager bus structure and output state" + "Settings
## binding").
##
## Structure half: the registered autoload ensures `Music` and `SFX` under
## `Master` exactly once, starts unmuted at 0 dB with both getters `true`,
## and notifies nobody; each setter commits, applies as bus mute, and
## notifies exactly once, while an unchanged value and a removed bus are
## rejected with their named errors, committed state and the bus untouched,
## and silence (the removed bus is restored inside the suite).
##
## Binding half: the live Settings → AudioManager follow, the initial
## application of an already-false preference at a fresh instance's bind,
## and the fail-soft branch with the Settings autoload temporarily removed
## and restored — both branches asserted. A final source scan covers the
## manager's no-clock/no-persistence/no-content/no-other-dependency
## clauses directly (the Settings binding is its sole allowed
## cross-service reference, design D7).
##
## Pure service: no API, no boot flow, no endpoint argument. Runs headless
## as part of `verify-boot.ps1`.

const AudioManagerScript = preload("res://scripts/audio_manager.gd")
const AUDIO_SOURCE := "res://scripts/audio_manager.gd"

## Requirement clauses of "AudioManager bus structure and output state"
## that no scenario covers on its own: the manager must not read
## wall-clock or time services, must not perform persistence or content
## loading, and must not reference any other script or autoload (its
## `/root/Settings` binding is allowed; transport and legacy tokens are
## covered by the project-scope scan of every allow-listed file).
const AUDIO_SOURCE_FORBIDDEN := [
	"from_system",
	"Time.get_unix_time",
	"OS.get_time",
	"OS.get_date",
	"OS.get_datetime",
	"OS.get_unix_time",
	"FileAccess",
	"DirAccess",
	"ResourceSaver",
	"ConfigFile",
	"preload(",
	"load(",
	"GameApi",
	"ContentRegistry",
	"Session",
	"GameClock",
]

## Output-change payloads observed via the manager signals, in emission
## order, tagged `["music", enabled]` / `["sfx", enabled]`.
var _changed_payloads: Array = []


func run_scenario() -> void:
	var audio: Variant = root.get_node_or_null("AudioManager")
	check(audio != null, "AudioManager autoload is registered")
	var settings: Variant = root.get_node_or_null("Settings")
	check(settings != null, "Settings autoload is registered for binding")
	if audio == null or settings == null:
		return
	_check_start_with_buses(audio)
	_check_music_toggle()
	_check_sfx_toggle()
	_check_unchanged_rejection()
	_check_bus_missing()
	_check_follow_settings_change(audio, settings)
	_check_bind_to_current_preferences(settings)
	_check_start_without_settings(settings)
	_check_defaults_restored(audio, settings)
	_check_source_contract()


## Spec: "Start with both buses ready" + "Start with default outputs"
## (defaults asserted on the registered instance; a fresh instance
## exercises the idempotent ensure and the silent initial application).
func _check_start_with_buses(audio: Variant) -> void:
	var music := AudioServer.get_bus_index("Music")
	var sfx := AudioServer.get_bus_index("SFX")
	check(music != -1, "the Music bus exists at startup")
	check(sfx != -1, "the SFX bus exists at startup")
	if music == -1 or sfx == -1:
		return
	check_eq(str(AudioServer.get_bus_send(music)), "Master",
		"the Music bus sends to Master")
	check_eq(str(AudioServer.get_bus_send(sfx)), "Master",
		"the SFX bus sends to Master")
	check_eq(AudioServer.is_bus_mute(music), false,
		"the Music bus starts unmuted")
	check_eq(AudioServer.is_bus_mute(sfx), false,
		"the SFX bus starts unmuted")
	check_eq(AudioServer.get_bus_volume_db(music), 0.0,
		"the Music bus volume stays at 0 dB")
	check_eq(AudioServer.get_bus_volume_db(sfx), 0.0,
		"the SFX bus volume stays at 0 dB")
	check_eq(audio.music_enabled(), true,
		"the registered manager starts with the music output on")
	check_eq(audio.sfx_enabled(), true,
		"the registered manager starts with the sfx output on")

	_reset_notifications()
	var fresh: Variant = _new_audio()
	check_eq(fresh.music_enabled(), true,
		"a fresh instance starts with the music output on")
	check_eq(fresh.sfx_enabled(), true,
		"a fresh instance starts with the sfx output on")
	check_eq(AudioServer.get_bus_count(), 3,
		"the ensure step never duplicates a bus")
	check_eq(_changed_payloads.size(), 0,
		"an already-matching initial application notifies nobody")
	_dispose_audio(fresh)


## Spec: "Apply a music toggle".
func _check_music_toggle() -> void:
	_reset_notifications()
	var audio: Variant = _new_audio()
	var music := AudioServer.get_bus_index("Music")

	var disabled: Dictionary = audio.set_music_enabled(false)
	check(disabled.get("ok") == true, "disabling the music output succeeds")
	check_eq(audio.music_enabled(), false,
		"the getter reports the committed value")
	check_eq(AudioServer.is_bus_mute(music), true,
		"the committed value is applied as bus mute")
	check_eq(AudioServer.get_bus_volume_db(music), 0.0,
		"volume policy is untouched at 0 dB")
	check_eq(_changed_payloads, [["music", false]],
		"the change notifies once with the new value")

	var enabled: Dictionary = audio.set_music_enabled(true)
	check(enabled.get("ok") == true, "enabling the music output succeeds")
	check_eq(audio.music_enabled(), true,
		"the getter reports the committed value")
	check_eq(AudioServer.is_bus_mute(music), false,
		"the committed value is applied as bus mute")
	check_eq(_changed_payloads, [["music", false], ["music", true]],
		"each committed change notifies exactly once")
	_dispose_audio(audio)


## Spec: "Apply a music toggle" (sfx category) — one notification, mute
## applied, volume untouched.
func _check_sfx_toggle() -> void:
	_reset_notifications()
	var audio: Variant = _new_audio()
	var sfx := AudioServer.get_bus_index("SFX")

	var disabled: Dictionary = audio.set_sfx_enabled(false)
	check(disabled.get("ok") == true, "disabling the sfx output succeeds")
	check_eq(audio.sfx_enabled(), false,
		"the getter reports the committed value")
	check_eq(AudioServer.is_bus_mute(sfx), true,
		"the committed value is applied as bus mute")
	check_eq(AudioServer.get_bus_volume_db(sfx), 0.0,
		"volume policy is untouched at 0 dB")
	check_eq(_changed_payloads, [["sfx", false]],
		"the change notifies once with the new value")

	var enabled: Dictionary = audio.set_sfx_enabled(true)
	check(enabled.get("ok") == true, "enabling the sfx output succeeds")
	check_eq(audio.sfx_enabled(), true,
		"the getter reports the committed value")
	check_eq(AudioServer.is_bus_mute(sfx), false,
		"the committed value is applied as bus mute")
	check_eq(_changed_payloads, [["sfx", false], ["sfx", true]],
		"each committed change notifies exactly once")
	_dispose_audio(audio)


## Spec: "Reject an unchanged toggle".
func _check_unchanged_rejection() -> void:
	_reset_notifications()
	var audio: Variant = _new_audio()
	var music := AudioServer.get_bus_index("Music")
	var sfx := AudioServer.get_bus_index("SFX")

	var same_music: Dictionary = audio.set_music_enabled(true)
	check(same_music.get("ok") == false,
		"re-requesting the committed music value is rejected")
	check(String(same_music.get("error", ""))
		.find("music_setting_unchanged") != -1,
		"the error names the violated condition")
	var same_sfx: Dictionary = audio.set_sfx_enabled(true)
	check(same_sfx.get("ok") == false,
		"re-requesting the committed sfx value is rejected")
	check(String(same_sfx.get("error", ""))
		.find("sfx_setting_unchanged") != -1,
		"the error names the violated condition")
	check_eq(audio.music_enabled(), true,
		"a rejected request leaves the committed value untouched")
	check_eq(audio.sfx_enabled(), true,
		"a rejected request leaves the committed value untouched")
	check_eq(AudioServer.is_bus_mute(music), false,
		"a rejected request leaves the bus untouched")
	check_eq(AudioServer.is_bus_mute(sfx), false,
		"a rejected request leaves the bus untouched")
	check_eq(_changed_payloads.size(), 0,
		"rejected requests notify nobody")

	audio.set_music_enabled(false)
	_reset_notifications()
	var again: Dictionary = audio.set_music_enabled(false)
	check(again.get("ok") == false,
		"re-requesting a committed-off value is rejected as well")
	check(String(again.get("error", ""))
		.find("music_setting_unchanged") != -1,
		"the error names the violated condition")
	check_eq(audio.music_enabled(), false,
		"the committed value stays unchanged after the rejection")
	check_eq(AudioServer.is_bus_mute(music), true,
		"the bus stays unchanged after the rejection")
	check_eq(_changed_payloads.size(), 0,
		"the second rejected request notifies nobody either")
	audio.set_music_enabled(true)
	_dispose_audio(audio)


## Spec: "Reject when the bus is missing" — each bus is removed, the
## category setter fails with its bus-missing error, and the bus is
## restored for every later scenario.
func _check_bus_missing() -> void:
	_reset_notifications()
	var audio: Variant = _new_audio()

	AudioServer.remove_bus(AudioServer.get_bus_index("Music"))
	var missing_music: Dictionary = audio.set_music_enabled(false)
	check(missing_music.get("ok") == false,
		"a request against a removed Music bus is rejected")
	check(String(missing_music.get("error", ""))
		.find("music_bus_missing") != -1,
		"the error names the violated condition")
	check_eq(audio.music_enabled(), true,
		"a bus-missing rejection leaves committed state untouched")
	check_eq(_changed_payloads.size(), 0,
		"a bus-missing rejection notifies nobody")
	_ensure_bus("Music")

	AudioServer.remove_bus(AudioServer.get_bus_index("SFX"))
	var missing_sfx: Dictionary = audio.set_sfx_enabled(false)
	check(missing_sfx.get("ok") == false,
		"a request against a removed SFX bus is rejected")
	check(String(missing_sfx.get("error", ""))
		.find("sfx_bus_missing") != -1,
		"the error names the violated condition")
	check_eq(audio.sfx_enabled(), true,
		"a bus-missing rejection leaves committed state untouched")
	check_eq(_changed_payloads.size(), 0,
		"a bus-missing rejection notifies nobody")
	_ensure_bus("SFX")

	var music := AudioServer.get_bus_index("Music")
	var sfx := AudioServer.get_bus_index("SFX")
	check(music != -1 and sfx != -1, "both buses are restored")
	check_eq(AudioServer.is_bus_mute(music), false,
		"the restored Music bus is unmuted")
	check_eq(AudioServer.is_bus_mute(sfx), false,
		"the restored SFX bus is unmuted")

	var recovered: Dictionary = audio.set_music_enabled(false)
	check(recovered.get("ok") == true,
		"the manager keeps working after the restoration")
	audio.set_music_enabled(true)
	_dispose_audio(audio)


## Spec: "Follow a Settings change" — the registered pair, live.
func _check_follow_settings_change(audio: Variant, settings: Variant) -> void:
	_reset_notifications()
	audio.music_enabled_changed.connect(_on_music_changed)
	audio.sfx_enabled_changed.connect(_on_sfx_changed)
	settings.set_music_enabled(false)

	check_eq(audio.music_enabled(), false,
		"the registered manager commits the Settings value")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")),
		true, "the committed value is applied as bus mute")
	check_eq(_changed_payloads, [["music", false]],
		"the follow notifies exactly once with the new value")

	settings.set_music_enabled(true)
	check_eq(audio.music_enabled(), true,
		"the registered manager follows the value back")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")),
		false, "the committed value is applied as bus mute")
	check_eq(_changed_payloads, [["music", false], ["music", true]],
		"each followed change notifies exactly once")
	audio.music_enabled_changed.disconnect(_on_music_changed)
	audio.sfx_enabled_changed.disconnect(_on_sfx_changed)


## Spec: "Bind to current preferences" — a preference is already `false`
## when a fresh instance starts, so its initial application commits,
## applies, and notifies exactly once.
func _check_bind_to_current_preferences(settings: Variant) -> void:
	settings.set_music_enabled(false)
	_reset_notifications()

	var fresh: Variant = _new_audio()
	check_eq(fresh.music_enabled(), false,
		"the fresh instance commits the already-false preference")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")),
		true, "the applied preference is on the bus")
	check_eq(_changed_payloads, [["music", false]],
		"the initial application notifies exactly once for the change")
	_dispose_audio(fresh)

	settings.set_music_enabled(true)
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")),
		false, "the registered manager restores the bus afterwards")
	check_eq(_changed_payloads, [["music", false]],
		"the fresh instance's initial application was the only notification "
		+ "in its window")
	_reset_notifications()


## Spec: "Start without Settings" — the autoload is removed, a fresh
## instance starts without error and stays operational for direct
## control, and the autoload is restored and asserted.
func _check_start_without_settings(settings: Variant) -> void:
	var settings_node := root.get_node_or_null("Settings")
	check(settings_node != null, "the Settings autoload can be located")
	if settings_node == null:
		return
	root.remove_child(settings_node)
	check(root.get_node_or_null("/root/Settings") == null,
		"the Settings autoload is temporarily absent")

	_reset_notifications()
	var fresh: Variant = _new_audio()
	check_eq(fresh.music_enabled(), true,
		"a fresh instance starts with its own defaults")
	check_eq(fresh.sfx_enabled(), true,
		"a fresh instance starts with its own defaults")

	var disabled: Dictionary = fresh.set_sfx_enabled(false)
	check(disabled.get("ok") == true,
		"direct control works while Settings is absent")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("SFX")),
		true, "the direct change is applied as bus mute")
	check_eq(_changed_payloads, [["sfx", false]],
		"the direct change notifies exactly once")
	var enabled: Dictionary = fresh.set_sfx_enabled(true)
	check(enabled.get("ok") == true,
		"direct control works in both directions")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("SFX")),
		false, "the restored value is applied as bus mute")
	_dispose_audio(fresh)

	root.add_child(settings_node)
	check(root.get_node_or_null("/root/Settings") != null,
		"the Settings autoload is restored")
	check_eq(settings.music_enabled(), true,
		"the restored preferences are untouched")
	check_eq(settings.sfx_enabled(), true,
		"the restored preferences are untouched")
	_reset_notifications()


## The suite hands the shared global state back exactly as it found it:
## both preferences and outputs on, both buses present and unmuted.
func _check_defaults_restored(audio: Variant, settings: Variant) -> void:
	check_eq(settings.music_enabled(), true,
		"the settings preference is restored")
	check_eq(settings.sfx_enabled(), true,
		"the settings preference is restored")
	check_eq(audio.music_enabled(), true,
		"the manager output is restored")
	check_eq(audio.sfx_enabled(), true,
		"the manager output is restored")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("Music")),
		false, "the Music bus is left unmuted")
	check_eq(AudioServer.is_bus_mute(AudioServer.get_bus_index("SFX")),
		false, "the SFX bus is left unmuted")


## Requirement clauses with no scenario of their own: the manager source
## must contain no wall-clock/time-service read, no persistence, no
## content loading, and no reference to any script or autoload other than
## its Settings binding.
func _check_source_contract() -> void:
	var handle := FileAccess.open(AUDIO_SOURCE, FileAccess.READ)
	check(handle != null,
		"the audio manager source is readable: " + AUDIO_SOURCE)
	if handle == null:
		return
	var body := handle.get_as_text()
	handle.close()
	check(body.length() > 0, "the audio manager source is non-empty")
	for token in AUDIO_SOURCE_FORBIDDEN:
		check(body.find(token) == -1,
			"audio_manager.gd must not reference %s" % token)


## Each scenario asserts its own notifications from a clean slate.
func _reset_notifications() -> void:
	_changed_payloads.clear()


## A fresh manager attached to the tree so its `_ready` (ensure + bind)
## runs exactly as it does for the registered instance.
func _new_audio() -> Variant:
	var audio: Variant = AudioManagerScript.new()
	audio.music_enabled_changed.connect(_on_music_changed)
	audio.sfx_enabled_changed.connect(_on_sfx_changed)
	root.add_child(audio)
	return audio


## Detaches and frees a fresh manager; its Settings binding
## disconnects with its destruction.
func _dispose_audio(audio: Variant) -> void:
	root.remove_child(audio)
	audio.free()


## Idempotent by name — the manager's own ensure logic, usable by the
## suite when it has to restore a bus it removed (design D5).
func _ensure_bus(bus_name: String) -> void:
	if AudioServer.get_bus_index(bus_name) != -1:
		return
	AudioServer.add_bus()
	var index := AudioServer.get_bus_count() - 1
	AudioServer.set_bus_name(index, bus_name)
	AudioServer.set_bus_send(index, "Master")


func _on_music_changed(enabled: bool) -> void:
	_changed_payloads.append(["music", enabled])


func _on_sfx_changed(enabled: bool) -> void:
	_changed_payloads.append(["sfx", enabled])
