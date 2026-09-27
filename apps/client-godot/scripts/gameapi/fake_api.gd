extends Node
## `FakeApi` — GameApi implementation over the committed v0 fixtures (design
## D5, spec "Boot offline with the fake implementation").
##
## Reads only the committed executed-legacy fixture files under
## `tests/fixtures/godot-compatibility-boot/` at the repository root: no
## process, no server, no socket. It synthesizes the documented v0 envelopes
## from those files and parses them with the same `BootData` functions the
## live implementation uses, so both implementations yield identical typed
## shapes by construction.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const Paths = preload("res://scripts/package_paths.gd")

const SAVE_LIST_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const GAME_CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"
const PLAYER_INFO_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

var _save_list_doc: Dictionary = {}
var _config_payload: Dictionary = {}
var _player_info_payload: Dictionary = {}
var _load_error := ""
var _loaded := false


## The session envelope synthesized from the committed fixtures.
func list_sessions() -> BootData.SaveListResult:
	if not _ensure_loaded():
		return BootData.save_list_failure("fixture_unreadable", _load_error)
	return BootData.parse_save_list(_session_envelope())


## Bootstrap envelope synthesized from the committed fixtures; structured
## errors for empty and unknown save ids match the live service's codes.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	if user_id.strip_edges() == "":
		return BootData.bootstrap_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return BootData.bootstrap_failure("fixture_unreadable", _load_error)
	if not _fixture_names(user_id):
		return BootData.bootstrap_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var envelope := _session_envelope()
	envelope["config"] = _config_payload
	envelope["player_info"] = _player_info_payload
	return BootData.parse_bootstrap(envelope, user_id)


## The fake never resolves an endpoint (scope test: only the legacy-v0
## implementation may reference one).
func resolved_endpoint() -> String:
	return "fake fixtures, offline"


func _ensure_loaded() -> bool:
	if _loaded:
		return _load_error == ""
	_loaded = true
	_save_list_doc = _read_json(SAVE_LIST_FIXTURE)
	if _load_error == "":
		_config_payload = _read_json(GAME_CONFIG_FIXTURE)
	if _load_error == "":
		_player_info_payload = _read_json(PLAYER_INFO_FIXTURE)
	if _load_error == "" and not (_save_list_doc.get("saves") is Array):
		_load_error = "fixture save list carries no saves array: " \
			+ SAVE_LIST_FIXTURE
	return _load_error == ""


func _session_envelope() -> Dictionary:
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (the field-stability record lists
		# server_time as time-dependent, so tests never compare its value).
		"server_time": _fixture_server_time(),
		"saves": _save_list_doc.get("saves", []),
	}


## Fixture-derived epoch: `player_info.timestamp` of the captured response.
func _fixture_server_time() -> int:
	var value := BootData._parse_epoch(_player_info_payload.get("timestamp"))
	if value < 0:
		return 0
	return value


func _fixture_names(user_id: String) -> bool:
	for entry in _save_list_doc.get("saves", []):
		if entry is Dictionary and str(entry.get("id", "")) == user_id:
			return true
	return false


func _read_json(relative: String) -> Dictionary:
	var path := Paths.repo_root().path_join(relative)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		_load_error = "cannot read fixture: " + path
		return {}
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	if parser.parse(text) != OK:
		_load_error = "fixture is not valid JSON: %s (line %d)" \
			% [path, parser.get_error_line()]
		return {}
	if not (parser.data is Dictionary):
		_load_error = "fixture is not a JSON object: " + path
		return {}
	var typed: Dictionary = parser.data
	return typed
