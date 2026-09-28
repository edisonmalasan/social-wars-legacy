extends Node
## AudioManager autoload (M5 foundation, OpenSpec `godot-settings-audio`
## design D1, D5, D6).
##
## Cross-cutting holder for audio output: at startup it idempotently
## ensures the `Music` and `SFX` buses under `Master` and binds to the
## Settings autoload through a `/root/Settings` lookup — one-directional
## and fail-soft: with Settings present it applies the current preferences
## and follows every `setting_changed` emission; without it, direct
## control still works (design D5). Committed state mirrors the two
## preferences; a committed change is applied as bus mute only — volume
## policy is untouched at 0 dB (design D6).
##
## Provisional contract (design D2): no legacy audio behavior has been
## captured, no sound is played here (playback and the `driver="Dummy"`
## policy bind with the later sound-content work), and the fail-closed /
## change-only envelope matches the other foundation scaffolds (spec:
## "Reject an unchanged toggle", "Reject when the bus is missing").
## The service performs no persistence, reads no clock, and loads no
## content (design D7).

## Emitted once per committed output change with the new value.
signal music_enabled_changed(enabled: bool)
signal sfx_enabled_changed(enabled: bool)

## Bus names owned by this manager.
const MUSIC_BUS := "Music"
const SFX_BUS := "SFX"
const MASTER_BUS := "Master"

## Committed music output state.
var _music_enabled := true
## Committed sound-effects output state.
var _sfx_enabled := true


func _ready() -> void:
	_ensure_bus(MUSIC_BUS)
	_ensure_bus(SFX_BUS)
	var settings := get_node_or_null("/root/Settings")
	if settings == null:
		return
	settings.setting_changed.connect(_on_setting_changed)
	# Initial application (design D5): the unchanged rejections below are
	# expected when a bus already matches the preference and stay silent —
	# notifications are change-only.
	set_music_enabled(settings.music_enabled())
	set_sfx_enabled(settings.sfx_enabled())


## The committed music output state (`true` until changed).
func music_enabled() -> bool:
	return _music_enabled


## The committed sound-effects output state (`true` until changed).
func sfx_enabled() -> bool:
	return _sfx_enabled


## Commits the music output and applies it as the `Music` bus mute state.
## Fail-closed: a request equal to the committed value fails with
## `music_setting_unchanged`, a removed bus fails with `music_bus_missing`,
## and every failure leaves committed state and the bus untouched and
## notifies nobody (spec: "Reject an unchanged toggle", "Reject when the
## bus is missing").
func set_music_enabled(enabled: bool) -> Dictionary:
	if _music_enabled == enabled:
		return _reject("set_music_enabled", "music_setting_unchanged")
	var index := AudioServer.get_bus_index(MUSIC_BUS)
	if index == -1:
		return _reject("set_music_enabled", "music_bus_missing")
	_music_enabled = enabled
	AudioServer.set_bus_mute(index, not enabled)
	music_enabled_changed.emit(enabled)
	return _grant()


## Commits the sound-effects output and applies it as the `SFX` bus mute
## state, with the same fail-closed rules as `set_music_enabled`.
func set_sfx_enabled(enabled: bool) -> Dictionary:
	if _sfx_enabled == enabled:
		return _reject("set_sfx_enabled", "sfx_setting_unchanged")
	var index := AudioServer.get_bus_index(SFX_BUS)
	if index == -1:
		return _reject("set_sfx_enabled", "sfx_bus_missing")
	_sfx_enabled = enabled
	AudioServer.set_bus_mute(index, not enabled)
	sfx_enabled_changed.emit(enabled)
	return _grant()


## Binding half of design D5: an unknown preference key is ignored — this
## manager owns exactly two outputs.
func _on_setting_changed(key: String, value: bool) -> void:
	if key == "music_enabled":
		set_music_enabled(value)
	elif key == "sfx_enabled":
		set_sfx_enabled(value)


## Ensures the named bus exists under `Master`, idempotently by name
## (design D5): an existing bus (ours or a future layout's) is reused, so
## a re-run never duplicates it.
func _ensure_bus(bus_name: String) -> void:
	if AudioServer.get_bus_index(bus_name) != -1:
		return
	AudioServer.add_bus()
	var index := AudioServer.get_bus_count() - 1
	AudioServer.set_bus_name(index, bus_name)
	AudioServer.set_bus_send(index, MASTER_BUS)


## The grant envelope of the foundation scaffolds.
func _grant() -> Dictionary:
	return {"ok": true, "error": ""}


## The house rejection envelope: names the violated condition, leaves
## committed state untouched, notifies nobody.
func _reject(operation: String, error: String) -> Dictionary:
	return {"ok": false,
		"error": "[audio] %s rejected: %s" % [operation, error]}
