extends "res://tests/test_base.gd"
## Settings suite (OpenSpec `godot-settings-audio` tasks 1.1 / 2.1, spec:
## "Settings preference state" + "Explicit fail-closed persistence").
##
## Preference half: the registered autoload and fresh instances start
## with both preferences `true` and notify nobody, a commit flips exactly
## one preference with exactly one key-and-value notification, and a
## request equal to committed state is rejected with a named error,
## committed state untouched, and silence.
##
## Persistence half: a save/load round trip over a temp file under the
## ignored `.godot/` cache; absent, corrupt, and schema-violating files
## are each rejected with their named error, committed state untouched,
## and silence; a successful load notifies only per actually-changed key;
## an unwritable path fails the save. The corrupt-file read runs inside
## an `Engine.print_error_messages = false` window because the engine
## prints an `ERROR:` line for an unparsable config file and
## `verify-boot.ps1` fails on those (design D7). A final source scan
## covers the service's no-clock/no-raw-persistence/no-content/no-other-
## dependency clauses directly — `ConfigFile` is the sanctioned storage
## mechanism and is therefore excluded from this scan (design D7).
##
## Pure service: no API, no boot flow, no endpoint argument. Runs headless
## as part of `verify-boot.ps1`.

const SettingsScript = preload("res://scripts/settings.gd")
const SETTINGS_SOURCE := "res://scripts/settings.gd"

const TEST_DIR := "res://.godot/settings-tests"
const ROUNDTRIP_PATH := TEST_DIR + "/roundtrip.cfg"
const ABSENT_PATH := TEST_DIR + "/absent.cfg"
const CORRUPT_PATH := TEST_DIR + "/corrupt.cfg"
const INVALID_MISSING_PATH := TEST_DIR + "/invalid-missing.cfg"
const INVALID_TYPE_PATH := TEST_DIR + "/invalid-type.cfg"
const INVALID_UNKNOWN_PATH := TEST_DIR + "/invalid-unknown.cfg"
const CHANGEONLY_PATH := TEST_DIR + "/change-only.cfg"
const UNWRITABLE_PATH := TEST_DIR + "/no-such-dir/never.cfg"

## Requirement clauses of "Settings preference state" that no scenario
## covers on its own: the service must not read wall-clock or time
## services, must not perform raw persistence or content loading beyond
## the sanctioned `ConfigFile` mechanism, must not reference any other
## script, autoload, or audio API (transport and legacy tokens are
## covered by the project-scope scan of every allow-listed file). The
## established list minus `ConfigFile` and `load(` (both are the
## storage mechanism itself), plus `ResourceLoader`, `AudioManager`,
## and `AudioServer` (design D7).
const SETTINGS_SOURCE_FORBIDDEN := [
	"from_system",
	"Time.get_unix_time",
	"OS.get_time",
	"OS.get_date",
	"OS.get_datetime",
	"OS.get_unix_time",
	"FileAccess",
	"DirAccess",
	"ResourceSaver",
	"ResourceLoader",
	"preload(",
	"GameApi",
	"ContentRegistry",
	"Session",
	"GameClock",
	"AudioManager",
	"AudioServer",
]

## Change payloads observed via `setting_changed`, in emission order.
var _changed_payloads: Array = []


func run_scenario() -> void:
	var settings: Variant = root.get_node_or_null("Settings")
	check(settings != null, "Settings autoload is registered")
	if settings == null:
		return
	_prepare_storage()
	_check_start_with_defaults(settings)
	_check_commit()
	_check_unchanged_rejection()
	_check_round_trip()
	_check_absent_file()
	_check_unreadable_contents()
	_check_invalid_contents()
	_check_load_change_only()
	_check_write_failure()
	_check_source_contract()
	_teardown_storage()


## Spec: "Start with default preferences".
func _check_start_with_defaults(settings: Variant) -> void:
	check_eq(settings.music_enabled(), true,
		"the registered service starts with the music preference on")
	check_eq(settings.sfx_enabled(), true,
		"the registered service starts with the sfx preference on")
	_reset_notifications()
	var fresh: Variant = _new_settings()
	check_eq(fresh.music_enabled(), true,
		"a fresh instance starts with the music preference on")
	check_eq(fresh.sfx_enabled(), true,
		"a fresh instance starts with the sfx preference on")
	check_eq(_changed_payloads.size(), 0, "creation notifies nobody")
	fresh.free()


## Spec: "Commit a preference change".
func _check_commit() -> void:
	_reset_notifications()
	var settings: Variant = _new_settings()

	var music: Dictionary = settings.set_music_enabled(false)
	check(music.get("ok") == true, "disabling music succeeds")
	check_eq(settings.music_enabled(), false,
		"the getter reports the committed value")
	check_eq(_changed_payloads, [["music_enabled", false]],
		"the change notifies once with the key and the new value")

	var sfx: Dictionary = settings.set_sfx_enabled(false)
	check(sfx.get("ok") == true, "disabling sound effects succeeds")
	check_eq(settings.sfx_enabled(), false,
		"the getter reports the committed value")
	check_eq(_changed_payloads, [["music_enabled", false],
		["sfx_enabled", false]], "each committed change notifies exactly once")
	settings.free()


## Spec: "Reject an unchanged preference".
func _check_unchanged_rejection() -> void:
	_reset_notifications()
	var settings: Variant = _new_settings()

	var same: Dictionary = settings.set_music_enabled(true)
	check(same.get("ok") == false,
		"re-requesting the committed music value is rejected")
	check(String(same.get("error", "")).find("setting_unchanged") != -1,
		"the error names the violated condition")
	check_eq(settings.music_enabled(), true,
		"a rejected request leaves the committed value untouched")
	check_eq(_changed_payloads.size(), 0,
		"a rejected request notifies nobody")

	var sfx_same: Dictionary = settings.set_sfx_enabled(true)
	check(sfx_same.get("ok") == false,
		"re-requesting the committed sfx value is rejected too")
	check(String(sfx_same.get("error", "")).find("setting_unchanged") != -1,
		"the error names the violated condition")

	settings.set_music_enabled(false)
	_reset_notifications()
	var again: Dictionary = settings.set_music_enabled(false)
	check(again.get("ok") == false,
		"re-requesting a committed-off value is rejected as well")
	check(String(again.get("error", "")).find("setting_unchanged") != -1,
		"the error names the violated condition")
	check_eq(settings.music_enabled(), false,
		"the committed value stays unchanged after the rejection")
	check_eq(_changed_payloads.size(), 0,
		"the second rejected request notifies nobody either")
	settings.free()


## Spec: "Round trip through storage".
func _check_round_trip() -> void:
	_reset_notifications()
	var writer: Variant = _new_settings()
	writer.set_music_enabled(false)
	writer.set_sfx_enabled(false)
	_reset_notifications()

	var saved: Dictionary = writer.save(ROUNDTRIP_PATH)
	check(saved.get("ok") == true, "saving the committed preferences succeeds")
	check(FileAccess.file_exists(ROUNDTRIP_PATH),
		"the stored file exists")
	writer.free()

	_reset_notifications()
	var reader: Variant = _new_settings()
	var loaded: Dictionary = reader.load(ROUNDTRIP_PATH)
	check(loaded.get("ok") == true, "loading the stored file succeeds")
	check_eq(reader.music_enabled(), false,
		"the round trip restores the music preference")
	check_eq(reader.sfx_enabled(), false,
		"the round trip restores the sfx preference")
	check_eq(_changed_payloads, [["music_enabled", false],
		["sfx_enabled", false]],
		"the load notifies exactly once per actually-changed key")
	reader.free()


## Spec: "Reject an absent file".
func _check_absent_file() -> void:
	_reset_notifications()
	var settings: Variant = _new_settings()

	var result: Dictionary = settings.load(ABSENT_PATH)
	check(result.get("ok") == false, "loading an absent file is rejected")
	check(String(result.get("error", "")).find("storage_file_missing") != -1,
		"the error names the violated condition")
	check_eq(settings.music_enabled(), true,
		"a failed load leaves the committed value untouched")
	check_eq(settings.sfx_enabled(), true,
		"a failed load leaves the committed value untouched")
	check_eq(_changed_payloads.size(), 0,
		"a failed load notifies nobody")
	settings.free()


## Spec: "Reject unreadable contents".
func _check_unreadable_contents() -> void:
	var handle := FileAccess.open(CORRUPT_PATH, FileAccess.WRITE)
	check(handle != null, "the corrupt fixture is writable")
	if handle == null:
		return
	handle.store_string("this is not [settings]\nvalid === broken")
	handle.close()

	_reset_notifications()
	var settings: Variant = _new_settings()
	Engine.print_error_messages = false
	var result: Dictionary = settings.load(CORRUPT_PATH)
	Engine.print_error_messages = true
	check(Engine.print_error_messages,
		"the engine error-printing flag is restored")
	check(result.get("ok") == false, "a corrupt file is rejected")
	check(String(result.get("error", "")).find("storage_read_failed") != -1,
		"the error names the violated condition")
	check_eq(settings.music_enabled(), true,
		"a corrupt read leaves the committed value untouched")
	check_eq(settings.sfx_enabled(), true,
		"a corrupt read leaves the committed value untouched")
	check_eq(_changed_payloads.size(), 0,
		"a corrupt read notifies nobody")
	settings.free()


## Spec: "Reject invalid contents" — the strict two-key schema rejects a
## missing key, a non-boolean value, and an unknown key without ever
## dropping or half-applying a field.
func _check_invalid_contents() -> void:
	var missing := ConfigFile.new()
	missing.set_value("settings", "music_enabled", false)
	check_eq(missing.save(INVALID_MISSING_PATH), OK,
		"the missing-key fixture is written")

	var wrong_type := ConfigFile.new()
	wrong_type.set_value("settings", "music_enabled", "loud")
	wrong_type.set_value("settings", "sfx_enabled", true)
	check_eq(wrong_type.save(INVALID_TYPE_PATH), OK,
		"the wrong-type fixture is written")

	var unknown := ConfigFile.new()
	unknown.set_value("settings", "music_enabled", false)
	unknown.set_value("settings", "sfx_enabled", false)
	unknown.set_value("settings", "extra_enabled", true)
	check_eq(unknown.save(INVALID_UNKNOWN_PATH), OK,
		"the unknown-key fixture is written")

	_reset_notifications()
	var settings: Variant = _new_settings()
	var fixtures := [
		[INVALID_MISSING_PATH, "missing key"],
		[INVALID_TYPE_PATH, "non-boolean value"],
		[INVALID_UNKNOWN_PATH, "unknown key"],
	]
	for fixture in fixtures:
		var result: Dictionary = settings.load(fixture[0])
		check(result.get("ok") == false,
			"a file with a %s is rejected" % fixture[1])
		check(String(result.get("error", "")).find("storage_invalid_contents")
			!= -1, "the error names the violated condition")
		check_eq(settings.music_enabled(), true,
			"an invalid file leaves the committed values untouched")
		check_eq(settings.sfx_enabled(), true,
			"an invalid file leaves the committed values untouched")
		check_eq(_changed_payloads.size(), 0,
			"an invalid file notifies nobody")
	settings.free()


## Spec: "Apply a load change-only".
func _check_load_change_only() -> void:
	var one_change := ConfigFile.new()
	one_change.set_value("settings", "music_enabled", false)
	one_change.set_value("settings", "sfx_enabled", true)
	check_eq(one_change.save(CHANGEONLY_PATH), OK,
		"the one-key-differs fixture is written")

	_reset_notifications()
	var settings: Variant = _new_settings()
	var result: Dictionary = settings.load(CHANGEONLY_PATH)
	check(result.get("ok") == true, "the one-key load succeeds")
	check_eq(settings.music_enabled(), false,
		"the changed key is committed")
	check_eq(settings.sfx_enabled(), true,
		"the unchanged key keeps its committed value")
	check_eq(_changed_payloads, [["music_enabled", false]],
		"exactly one notification is emitted, for the changed key")

	_reset_notifications()
	var again: Dictionary = settings.load(CHANGEONLY_PATH)
	check(again.get("ok") == true, "reloading the identical file succeeds")
	check_eq(_changed_payloads.size(), 0,
		"an identical load notifies nobody")
	settings.free()


## Spec: "Report a storage write failure".
func _check_write_failure() -> void:
	_reset_notifications()
	var settings: Variant = _new_settings()
	settings.set_music_enabled(false)
	_reset_notifications()

	var result: Dictionary = settings.save(UNWRITABLE_PATH)
	check(result.get("ok") == false,
		"saving into a missing directory is rejected")
	check(String(result.get("error", "")).find("storage_write_failed") != -1,
		"the error names the violated condition")
	check_eq(settings.music_enabled(), false,
		"a failed save leaves the committed state untouched")
	check_eq(_changed_payloads.size(), 0,
		"a failed save notifies nobody")
	check(FileAccess.file_exists(UNWRITABLE_PATH) == false,
		"nothing is written on failure")
	settings.free()


## Requirement clauses with no scenario of their own: the service source
## must contain no wall-clock/time-service read, no raw persistence or
## content loading, and no reference to any other script, autoload, or
## audio API.
func _check_source_contract() -> void:
	var handle := FileAccess.open(SETTINGS_SOURCE, FileAccess.READ)
	check(handle != null,
		"the settings service source is readable: " + SETTINGS_SOURCE)
	if handle == null:
		return
	var body := handle.get_as_text()
	handle.close()
	check(body.length() > 0, "the settings service source is non-empty")
	for token in SETTINGS_SOURCE_FORBIDDEN:
		check(body.find(token) == -1,
			"settings.gd must not reference %s" % token)


## Each scenario asserts its own notifications from a clean slate.
func _reset_notifications() -> void:
	_changed_payloads.clear()


## A fresh service instance with its change signal observed.
func _new_settings() -> Variant:
	var settings: Variant = SettingsScript.new()
	settings.setting_changed.connect(_on_setting_changed)
	return settings


## Creates the temp storage directory and clears leftover fixtures so
## every scenario starts from its documented precondition.
func _prepare_storage() -> void:
	var base := DirAccess.open("res://")
	check(base != null, "the project directory is writable")
	if base == null:
		return
	base.make_dir_recursive(".godot/settings-tests")
	check(DirAccess.dir_exists_absolute(
		ProjectSettings.globalize_path(TEST_DIR)),
		"the temp storage directory exists")
	for path in [ROUNDTRIP_PATH, ABSENT_PATH, CORRUPT_PATH,
			INVALID_MISSING_PATH, INVALID_TYPE_PATH, INVALID_UNKNOWN_PATH,
			CHANGEONLY_PATH, UNWRITABLE_PATH]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(path))


## Best-effort cleanup of the temp fixtures and directory (all under the
## ignored `.godot/` cache; no repository file is ever touched).
func _teardown_storage() -> void:
	for path in [ROUNDTRIP_PATH, ABSENT_PATH, CORRUPT_PATH,
			INVALID_MISSING_PATH, INVALID_TYPE_PATH, INVALID_UNKNOWN_PATH,
			CHANGEONLY_PATH]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	DirAccess.remove_absolute(ProjectSettings.globalize_path(TEST_DIR))


func _on_setting_changed(key: String, value: bool) -> void:
	_changed_payloads.append([key, value])
