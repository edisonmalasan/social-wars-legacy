extends "res://scripts/town/town.gd"
## The town-slice verification scene (OpenSpec `godot-town-rendering`
## "Town slice verification scene", design D5/D10).
##
## Renders the committed legacy village `villages/Scarlet.json` through
## the same town components as the player's town — one shared projection,
## terrain, object layer, HUD, camera bounds, and selection — to prove the
## properties the fresh save cannot: authentic converted building and unit
## sprites in town (House I, Wild Elephant), thumbnail and marker
## rendering, large footprints, content-unknown placeholders, and that
## save's HUD values, all from 100 % legacy-authored state.
##
## No server, no GameApi, no Flash: the village file is read directly
## from the preserved repository input and recorded by path and digest
## for the evidence report. Windowed runs honor the inherited
## `--town-capture=<path>` flow; headless runs build and expose records
## only (the suite drives the assertions).

const Paths = preload("res://scripts/package_paths.gd")

## Preserved legacy village input (read-only, repository-relative).
const VILLAGE := "villages/Scarlet.json"

## The input provenance recorded for the evidence report.
var input_path := VILLAGE
var input_sha256 := ""


func _ready() -> void:
	# The capture argument is owned by the base scene; read it before the
	# slice-specific preparation so a preparation failure can still route
	# a windowed capture run to exit 1 instead of hanging.
	_capture_path = _user_arg("--town-capture=")
	var prepared: Dictionary = _prepare_state()
	if not bool(prepared.get("ok", false)):
		_enter_error(str(prepared.get("error", "")))
		if not _capture_path.is_empty() \
				and DisplayServer.get_name() != "headless":
			get_tree().quit(1)
		return
	state = prepared["state"]
	# The base `_ready` builds the view from the committed state and runs
	# the inherited windowed capture flow.
	super._ready()


## Loads the preserved village input fail-closed: content + asset
## registry, input bytes and digest, JSON, typed town state. The path and
## digest are recorded even when a later step fails, so a failed slice
## still names its input.
func _prepare_state() -> Dictionary:
	var registry: Variant = get_node_or_null("/root/ContentRegistry")
	if registry == null:
		return {"ok": false,
			"error": "[slice] content registry is not registered"}
	if not registry.is_loaded():
		var content: Dictionary = registry.load_content()
		if not content.get("ok", false):
			return {"ok": false, "error": "[slice] content load failed: %s"
				% content.get("error", "")}
	if not registry.assets_loaded():
		var assets: Dictionary = registry.load_asset_registry()
		if not assets.get("ok", false):
			return {"ok": false,
				"error": "[slice] asset registry load failed: %s"
				% assets.get("error", "")}
	var absolute := Paths.repo_root().path_join(VILLAGE)
	if not FileAccess.file_exists(absolute):
		return {"ok": false,
			"error": "[slice] village input is missing: " + VILLAGE}
	var bytes := FileAccess.get_file_as_bytes(absolute)
	if bytes.is_empty():
		return {"ok": false,
			"error": "[slice] village input is unreadable: " + VILLAGE}
	input_sha256 = Paths.sha256_hex(bytes)
	var payload: Variant = JSON.parse_string(bytes.get_string_from_utf8())
	if not (payload is Dictionary):
		return {"ok": false,
			"error": "[slice] village input is not a JSON object"}
	var parsed: Dictionary = TownState.parse(payload, registry)
	if not parsed.get("ok", false):
		return {"ok": false, "error": "[slice] village state rejected: %s"
			% parsed.get("error", "")}
	return {"ok": true, "state": parsed["state"]}
