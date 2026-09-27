extends Control
## Boot scene — the project's main scene (design D6, spec "Boot scene").
##
## Flow: initialize the save list via `GameApi`, request bootstrap for one
## save, then display engine version, connection state, and the player
## summary (name, level, xp) derived from the typed response. An unreachable
## endpoint or a structured API error surfaces as an explicit error state
## that names the failure — never a blank screen or a partial success.
##
## Headless sessions print a machine-readable terminal marker and quit
## (exit 0 on `state=ready`, exit 1 on `state=error`); windowed sessions stay
## open as the client entry point. Headless tests set `auto_quit = false`
## before adding the scene to the tree, then observe `boot_finished`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

signal boot_finished(state: String)

## Terminal auto-quit for headless main-scene runs (tests disable it).
var auto_quit := true

## Terminal state: "ready" or "error" ("" until the boot reaches one).
var state := ""
## Failure name when state == "error".
var error_code := ""
## Failure detail when state == "error".
var error_message := ""
## Save id the bootstrap targeted.
var boot_user_id := ""
## Protocol of the successful bootstrap response.
var protocol := ""
## Game version reported by the response.
var game_version := ""
## Engine version displayed in the UI.
var engine_version := ""
## Transport description displayed as the connection state.
var connection_state := "not connected"
## Typed summary when state == "ready" (null otherwise, never partial).
var summary: BootData.PlayerSummary = null

## Exactly what the summary labels display (single source: the labels are
## assigned from these fields, so headless assertions cover the UI text).
var displayed_name := ""
var displayed_level := ""
var displayed_xp := ""
var displayed_error := ""

var _engine_label: Label
var _connection_label: Label
var _name_label: Label
var _level_label: Label
var _xp_label: Label
var _error_label: Label


func _ready() -> void:
	_build_labels()
	var version := Engine.get_version_info()
	engine_version = "%s %s" % [str(version.string), str(version.hash).substr(0, 9)]
	_engine_label.text = "engine: " + engine_version
	await _boot()


func _boot() -> void:
	var api := get_node_or_null("/root/GameApi")
	if api == null:
		_fail("gameapi_missing", "the GameApi autoload is not registered")
		return
	connection_state = "listing saves via " + api.describe_transport()
	_connection_label.text = "connection: connecting - " + connection_state
	var sessions: Variant = await api.list_sessions()
	if not (sessions is BootData.SaveListResult):
		_fail("bad_response", "GameApi list_sessions returned no typed result")
		return
	var save_list: BootData.SaveListResult = sessions
	if not save_list.ok:
		_fail(save_list.error_code, save_list.error_message)
		return
	game_version = save_list.game_version
	protocol = save_list.protocol
	connection_state = "connected (%s, %d save(s), game %s)" % [
		api.describe_transport(), save_list.saves.size(), game_version]
	_connection_label.text = "connection: " + connection_state
	boot_user_id = _select_user(save_list)
	if boot_user_id == "":
		_fail("no_saves", "the save list is empty; there is nothing to boot")
		return
	var boot: Variant = await api.get_bootstrap(boot_user_id)
	if not (boot is BootData.BootstrapResult):
		_fail("bad_response", "GameApi get_bootstrap returned no typed result")
		return
	var result: BootData.BootstrapResult = boot
	if not result.ok:
		_fail(result.error_code, result.error_message)
		return
	summary = result.summary
	_display_summary()
	_complete()


## User id to bootstrap: `--boot-user=` when given (explicit verification
## override), otherwise the first save of the session list.
func _select_user(save_list: BootData.SaveListResult) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--boot-user="):
			return argument.trim_prefix("--boot-user=")
	if save_list.saves.is_empty():
		return ""
	return save_list.saves[0].id


func _display_summary() -> void:
	if summary == null:
		return
	displayed_name = summary.name
	displayed_level = str(summary.level)
	displayed_xp = str(summary.xp)
	_name_label.text = "player: " + displayed_name
	_level_label.text = "level: " + displayed_level
	_xp_label.text = "xp: " + displayed_xp


func _complete() -> void:
	state = "ready"
	_emit_marker(0)


func _fail(code: String, message: String) -> void:
	state = "error"
	error_code = code
	error_message = message
	displayed_error = "error: %s: %s" % [code, message]
	if _error_label != null:
		_error_label.text = displayed_error
	# Never a partial success: no summary is shown on failure.
	_emit_marker(1)


func _emit_marker(exit_code: int) -> void:
	if state == "ready":
		print('[boot] state=ready engine="%s" protocol=%s game_version="%s"'
			% [engine_version, protocol, game_version])
		print("[boot] summary user_id=%s name=\"%s\" level=%d xp=%d"
			% [boot_user_id, summary.name, summary.level, summary.xp])
	else:
		print("[boot] state=error code=%s message=%s"
			% [error_code, error_message])
	# Deferred so observers can subscribe even when the boot completed
	# synchronously (fake fixtures resolve without ever suspending).
	call_deferred("_emit_finished")
	if DisplayServer.get_name() == "headless" and auto_quit:
		get_tree().quit(exit_code)


func _emit_finished() -> void:
	boot_finished.emit(state)


func _build_labels() -> void:
	var column := VBoxContainer.new()
	column.set_anchors_preset(Control.PRESET_FULL_RECT)
	column.offset_left = 8.0
	column.offset_top = 8.0
	column.offset_right = -8.0
	column.offset_bottom = -8.0
	add_child(column)
	_engine_label = _add_label(column, "")
	_connection_label = _add_label(column, "connection: not connected")
	_name_label = _add_label(column, "player: -")
	_level_label = _add_label(column, "level: -")
	_xp_label = _add_label(column, "xp: -")
	_error_label = _add_label(column, "")
	_error_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART


func _add_label(column: Node, text: String) -> Label:
	var label := Label.new()
	label.text = text
	column.add_child(label)
	return label
