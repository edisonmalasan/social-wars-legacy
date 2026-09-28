extends Node
## Settings autoload (M5 foundation, OpenSpec `godot-settings-audio`
## design D1-D4).
##
## Cross-cutting holder for the client's user preferences: exactly two
## committed boolean keys (`music_enabled`, `sfx_enabled`), both `true` at
## startup, exposed through typed accessors and an explicit `ConfigFile`
## persistence pair that never runs automatically (design D4).
## Provisional contract (design D2): no legacy user-settings behavior has
## been captured, so authentic preference semantics bind later with evidence.
##
## The service follows the fail-closed `{ok, error}` envelope of the other
## foundation scaffolds: a rejected request names the violated condition,
## leaves committed state untouched, and notifies nobody (spec: "Reject an
## unchanged preference", "Reject an absent file", "Reject unreadable
## contents", "Reject invalid contents"). Notifications are change-only
## (design D3), and the service references no other script or autoload —
## `ConfigFile` storage is its only dependency (design D7).

## Emitted once per committed preference change with its key and new value.
signal setting_changed(key: String, value: bool)

## Default storage location for the explicit load/save pair.
const DEFAULT_SETTINGS_PATH := "user://settings.cfg"
## Section name used inside the stored file.
const STORAGE_SECTION := "settings"
## The strict two-key schema: a stored file must carry exactly these keys,
## so nothing is dropped, half-applied, or silently merged (design D4).
const STORAGE_KEYS := ["music_enabled", "sfx_enabled"]

## Committed music preference.
var _music_enabled := true
## Committed sound-effects preference.
var _sfx_enabled := true


## The committed music preference (`true` until changed or loaded).
func music_enabled() -> bool:
	return _music_enabled


## The committed sound-effects preference (`true` until changed or loaded).
func sfx_enabled() -> bool:
	return _sfx_enabled


## Commits the music preference. Fail-closed: re-requesting the committed
## value fails with an error naming the condition, committed state is
## untouched, and nobody is notified (spec: "Reject an unchanged
## preference").
func set_music_enabled(enabled: bool) -> Dictionary:
	if _music_enabled == enabled:
		return _reject("set_music_enabled", "setting_unchanged")
	_music_enabled = enabled
	setting_changed.emit("music_enabled", enabled)
	return _grant()


## Commits the sound-effects preference. Fail-closed with the same rules
## as `set_music_enabled` (spec: "Reject an unchanged preference").
func set_sfx_enabled(enabled: bool) -> Dictionary:
	if _sfx_enabled == enabled:
		return _reject("set_sfx_enabled", "setting_unchanged")
	_sfx_enabled = enabled
	setting_changed.emit("sfx_enabled", enabled)
	return _grant()


## Explicitly loads both preferences from `path`. Fail-closed: an absent
## file fails with `storage_file_missing`, any other read failure (such as
## corrupt contents) fails with `storage_read_failed` (the message detail
## carries the engine error code), and a parsed file that violates the
## strict two-key schema fails with `storage_invalid_contents` — every
## failure leaves committed state and notifications untouched. A
## successful load commits both keys and notifies only per key that
## actually changed. Never runs automatically (spec: "Explicit fail-closed
## persistence"). The call is always member-qualified: an unqualified
## `load(...)` in this project resolves to the global resource loader.
func load(path := DEFAULT_SETTINGS_PATH) -> Dictionary:
	var config := ConfigFile.new()
	var error := config.load(path)
	if error == ERR_FILE_NOT_FOUND:
		return _reject("load", "storage_file_missing")
	if error != OK:
		return _reject("load",
			"storage_read_failed (engine code %d)" % error)
	var missing: Array = []
	var wrong_type: Array = []
	var unknown: Array = []
	for key in STORAGE_KEYS:
		if not config.has_section_key(STORAGE_SECTION, key):
			missing.append(key)
		elif typeof(config.get_value(STORAGE_SECTION, key)) != TYPE_BOOL:
			wrong_type.append(key)
	for section in config.get_sections():
		for key in config.get_section_keys(section):
			if section != STORAGE_SECTION or not STORAGE_KEYS.has(key):
				unknown.append("%s/%s" % [section, key])
	if not missing.is_empty() or not wrong_type.is_empty() \
			or not unknown.is_empty():
		return _reject("load", "storage_invalid_contents "
			+ "(missing=%s wrong_type=%s unknown=%s)"
			% [missing, wrong_type, unknown])
	var next_music := bool(config.get_value(STORAGE_SECTION, "music_enabled"))
	var next_sfx := bool(config.get_value(STORAGE_SECTION, "sfx_enabled"))
	if _music_enabled != next_music:
		_music_enabled = next_music
		setting_changed.emit("music_enabled", next_music)
	if _sfx_enabled != next_sfx:
		_sfx_enabled = next_sfx
		setting_changed.emit("sfx_enabled", next_sfx)
	return _grant()


## Explicitly writes the committed preferences to `path`. Fail-closed: a
## file that cannot be written fails with `storage_write_failed` and
## committed state is unchanged; a successful write changes nothing in
## memory. Never runs automatically (spec: "Explicit fail-closed
## persistence").
func save(path := DEFAULT_SETTINGS_PATH) -> Dictionary:
	var config := ConfigFile.new()
	config.set_value(STORAGE_SECTION, "music_enabled", _music_enabled)
	config.set_value(STORAGE_SECTION, "sfx_enabled", _sfx_enabled)
	var error := config.save(path)
	if error != OK:
		return _reject("save",
			"storage_write_failed (engine code %d)" % error)
	return _grant()


## The grant envelope of the foundation scaffolds.
func _grant() -> Dictionary:
	return {"ok": true, "error": ""}


## The house rejection envelope: names the violated condition, leaves
## committed state untouched, notifies nobody.
func _reject(operation: String, error: String) -> Dictionary:
	return {"ok": false,
		"error": "[settings] %s rejected: %s" % [operation, error]}
