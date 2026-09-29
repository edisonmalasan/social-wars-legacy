extends Control
## Boot scene — the project's main scene (design D6, spec "Boot scene").
##
## Flow: initialize the save list via `GameApi`, request bootstrap for one
## save, then display engine version, connection state, and the player
## summary (name, level, xp) derived from the typed response. An unreachable
## endpoint or a structured API error surfaces as an explicit error state
## that names the failure — never a blank screen or a partial success.
##
## Session (OpenSpec `godot-session`, design D6): every attempt clears the
## previous session on entry, and the bootstrapped save is committed to the
## `Session` autoload only on success — so `state=ready` always implies an
## active session and a failed boot leaves none behind.
##
## GameClock (OpenSpec `godot-game-clock`, design D6): every attempt also
## clears the previous anchor on entry, and a successful bootstrap anchors
## the clock to the response's `server_time` immediately before the session
## is activated — so `state=ready` also implies an anchored clock, and
## every bootstrap failure path (unreachable endpoint, structured API
## error, or malformed response) occurs before that anchor, leaving the
## clock unanchored.
##
## Headless sessions print a machine-readable terminal marker and quit
## (exit 0 on `state=ready`, exit 1 on `state=error`); windowed sessions stay
## open as the client entry point. Headless tests set `auto_quit = false`
## before adding the scene to the tree, then observe `boot_finished`.
##
## Windowed boot-to-town transition (M6, spec `godot-compatibility-boot`
## "Windowed boot-to-town transition"): after the ready marker a windowed
## run hands the already-validated bootstrap payload to the town-state
## parser and replaces the boot view with the built town view — reusing
## the single bootstrap request of the launch (no second request), with
## any handoff failure named explicitly in place of the view (never a
## blank window, never a partial town). Headless runs never enter this
## path: their marker, summary, error-state, and exit-code contract is
## byte-for-byte the original.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const TownState = preload("res://scripts/town/town_state.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

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
## The bootstrap's wrapped player-info payload, kept from the successful
## bootstrap for the windowed town handoff: an API-layer opaque payload
## consumed by the town-state parser — the raw transport dictionary never
## reaches presentation code (spec "Windowed boot-to-town transition").
var player_info: BootData.PlayerInfoPayload = null
## The bootstrap's wrapped game-config payload, kept for the town's
## placement and shop catalogs (building-placement / building-purchase,
## specs "Placement flow" and "Purchase flow"): the handoff parses it
## fail-closed ONCE and hands the same typed envelope to both surfaces —
## or the failure envelope to both — so a picker or shop entry is never
## derived from raw transport, never fabricated, and no second config
## request is ever issued. A missing or malformed config leaves both
## unavailable behind the named error; it never fails the town transition
## itself.
var config: BootData.ConfigPayload = null

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
	var session := get_node_or_null("/root/Session")
	if session == null:
		_fail("session_missing", "the Session autoload is not registered")
		return
	var clock := get_node_or_null("/root/GameClock")
	if clock == null:
		_fail("gameclock_missing", "the GameClock autoload is not registered")
		return
	# Every attempt starts from a known state: no stale session or clock
	# anchor survives a failed or superseded boot (specs `godot-session` and
	# `godot-game-clock`: "Boot integration").
	session.clear()
	clock.clear()
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
	player_info = result.player_info
	config = result.config
	if not _anchor_clock(clock, save_list.server_time):
		return
	if not _activate_session(session):
		return
	_display_summary()
	_complete()


## Commits the response's server epoch to the clock immediately before the
## session activation; fail-closed, so an anchor failure surfaces as an
## explicit boot error instead of a ready state without game time
## (spec `godot-game-clock`: "Boot integration", design D6).
func _anchor_clock(clock: Variant, server_time: int) -> bool:
	var anchoring: Dictionary = clock.anchor(server_time)
	if anchoring.get("ok") != true:
		_fail("gameclock_anchor", str(anchoring.get("error", "")))
		return false
	return true


## Commits the bootstrapped save to the session immediately before the
## ready state; fail-closed, so an activation failure surfaces as an
## explicit boot error instead of a ready state without a session
## (spec `godot-session`: "Boot integration", design D6).
func _activate_session(session: Variant) -> bool:
	var activation: Dictionary = session.activate(boot_user_id, summary)
	if activation.get("ok") != true:
		_fail("session_activate", str(activation.get("error", "")))
		return false
	return true


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
	# Headless runs never enter the town scene (spec "Headless boot
	# behavior is unchanged"); the marker, summary, error-state, and
	# exit-code contract above is untouched either way.
	if DisplayServer.get_name() != "headless":
		# Deferred: this `_ready` chain runs while the tree is still
		# attaching the boot scene, and attaching the town then would be
		# rejected ("parent node is busy setting up children"). At idle
		# the handoff runs synchronously and keeps its `{ok, error}`
		# contract for direct callers (tests).
		transition_to_town.call_deferred()


## Windowed boot-to-town handoff (spec "Windowed boot-to-town
## transition"): hands the already-validated bootstrap payload to the
## town-state parser, builds the town scene, and replaces the boot view
## with it. Issues no bootstrap request of its own — it reuses the single
## request of the launch (the legacy bootstrap mutates `last_logged_in`).
## Fail-closed: every failure commits an explicit error naming itself in
## place of the view (`_town_fail`), never a blank window and never a
## partial town. Returns `{ok, error}`; tests may call it directly to
## drive the handoff and its failure routing.
func transition_to_town() -> Dictionary:
	if player_info == null:
		return _town_fail("town_state_missing",
			"the bootstrap payload is unavailable")
	var content := get_node_or_null("/root/ContentRegistry")
	if content == null:
		return _town_fail("content_registry_missing",
			"the ContentRegistry autoload is not registered")
	if not content.is_loaded():
		var loaded: Dictionary = content.load_content()
		if not loaded.get("ok", false):
			return _town_fail("content_load", str(loaded.get("error", "")))
	if not content.assets_loaded():
		var assets: Dictionary = content.load_asset_registry()
		if not assets.get("ok", false):
			return _town_fail("asset_registry_load",
				str(assets.get("error", "")))
	var parsed: Dictionary = TownState.parse(player_info.raw, content)
	if not parsed.get("ok", false):
		return _town_fail("town_state", str(parsed.get("error", "")))
	var scene: Variant = load("res://scenes/town.tscn")
	if not (scene is PackedScene):
		return _town_fail("town_scene",
			"res://scenes/town.tscn failed to load")
	var town: Variant = scene.instantiate()
	# The state is committed before the tree insertion, so `_ready` builds
	# the view; a failed build is torn down and surfaced as the explicit
	# handoff error instead of a partial town. The placement and shop
	# catalogs are parsed from the payload in hand (no second config
	# request) and the same envelope is handed to both surfaces — one
	# fail-closed parse, two consumers — so a bad config leaves both
	# unavailable and never fails the town.
	town.set_town_state(parsed["state"])
	var catalog := _catalog_envelope()
	town.set_placement_catalog(catalog)
	town.set_shop_catalog(catalog)
	get_tree().root.add_child(town)
	if not town.build_ok:
		var failure := str(town.build_error)
		town.free()
		return _town_fail("town_build", failure)
	visible = false  # the boot view is replaced by the town view
	print('[boot] town=rendered user_id=%s placements=%d' % [
		boot_user_id, int((parsed["state"] as Variant).placements.size())])
	return {"ok": true, "error": ""}


## The catalog envelope for the town handoff: the payload in hand parsed
## fail-closed, or the named failure envelope when the boot carried no
## config object — the placement picker and the shop (building-placement /
## building-purchase) both become unavailable behind that explicit error
## (never fabricated), and the transition itself is unaffected either way
## (spec "Placement flow" and "Purchase flow", catalog failure scenario).
## ONE parse serves both surfaces, so the two can never disagree about the
## catalog and no second config request is ever issued.
func _catalog_envelope() -> Dictionary:
	if config == null:
		return {"ok": false, "error":
			"[catalog] parse rejected: the bootstrap config payload "
			+ "is unavailable"}
	return PlacementCatalog.parse(config.raw)


## Commits an explicit handoff failure: the boot view displays the named
## error in place of the town (never blank), the terminal state records
## it, and the standard error marker line is printed. `boot_finished` is
## not re-emitted — the boot's own terminal emission already happened.
## In an evidence capture run (`--town-capture=`,
## `--placement-capture=`, `--purchase-capture=`, `--move-capture=`,
## `--sell-capture=`, `--store-capture=`, or `--upgrade-capture=`) the
## process exits 1 so a failed capture cannot hang on an open window.
func _town_fail(code: String, message: String) -> Dictionary:
	state = "error"
	error_code = code
	error_message = message
	displayed_error = "error: %s: %s" % [code, message]
	if _error_label != null:
		_error_label.text = displayed_error
	visible = true
	print("[boot] state=error code=%s message=%s" % [code, message])
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--town-capture=") \
				or argument.begins_with("--placement-capture=") \
				or argument.begins_with("--purchase-capture=") \
				or argument.begins_with("--move-capture=") \
				or argument.begins_with("--sell-capture=") \
				or argument.begins_with("--store-capture=") \
				or argument.begins_with("--upgrade-capture="):
			get_tree().quit(1)
			break
	return {"ok": false,
		"error": "[boot] transition rejected: %s: %s" % [code, message]}


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
