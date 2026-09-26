extends "res://tests/test_base.gd"
## Project-scope check (OpenSpec task 5.2 / spec: "Remain within the
## verification scope").
##
## Asserts that `apps/client-godot/` contains only render-verification
## content: no game-system autoload, no extra scene, no script outside the
## explicit allow-list, and no reference to the legacy protocol or to a
## network/Flash runtime anywhere in the project sources.
##
## Runs headless as part of `verify.ps1`.

const Project_DIR := "res://"

## Files that are allowed to exist in the project (repository-relative to
## `apps/client-godot/`). Anything else that is not Godot's ignored cache is
## a scope violation: this list is the project's scope contract.
const ALLOWED := [
	"project.godot",
	"README.md",
	"verify.ps1",
	"scenes/first_render.tscn",
	"scripts/comparator.gd",
	"scripts/first_render.gd",
	"scripts/layout.gd",
	"scripts/package_loader.gd",
	"scripts/package_paths.gd",
	"scripts/reference_compositor.gd",
	"scripts/report.gd",
	"scripts/run_compare.gd",
	"scripts/run_selftest.gd",
	"scripts/verification.gd",
	"tests/test_base.gd",
	"tests/test_package_loader.gd",
	"tests/test_project_scope.gd",
	"tests/test_scene_build.gd",
	"evidence/first-render/first-render.png",
	"evidence/first-render/report.json",
]

## Strings that must never appear in project sources: M5 game systems,
## legacy protocol entry points, network access, or a Flash runtime.
const FORBIDDEN := [
	"GameApi",
	"LegacyV0Api",
	"ContentRegistry",
	"GameClock",
	"Session",
	"command.php",
	"FlashVars",
	"AMFPHP",
	"Ruffle",
	"WebSocket",
	"HTTPRequest",
	"HTTPClient",
	"TCPServer",
	"UDPServer",
	"PacketPeer",
	"Camera2D",
	"Camera3D",
	"http://",
	"https://",
]


func run_scenario() -> void:
	var root := Paths.project_dir()
	_check_file_inventory(root)
	_check_project_config(root)
	_check_sources(root)


## Every file in the project must be on the allow-list (Godot's generated
## `.godot/` cache is ignored by design and excluded here).
func _check_file_inventory(root: String) -> void:
	var found: Array = []
	var error := _collect(root, "", found)
	check(error == "", "project directory is readable: %s" % error)
	found.sort()
	var unexpected: Array = []
	for relative in found:
		if str(relative).begins_with(".godot/"):
			continue
		if not ALLOWED.has(str(relative)):
			unexpected.append(str(relative))
	check_eq(unexpected, [],
		"only allow-listed verification files exist in the project")
	var missing: Array = []
	for allowed in ALLOWED:
		if not found.has(allowed):
			missing.append(allowed)
	check_eq(missing, [], "every allow-listed file exists")
	info("project files checked: %s" % found.size())


func _collect(directory: String, prefix: String, out: Array) -> String:
	var dir := DirAccess.open(directory)
	if dir == null:
		return "cannot open " + directory
	dir.list_dir_begin()
	var entry := dir.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = dir.get_next()
			continue
		var full := directory.path_join(entry)
		if dir.current_is_dir():
			if entry != ".godot":
				var sub := _collect(full, prefix + entry + "/", out)
				if sub != "":
					return sub
		else:
			out.append(prefix + entry)
		entry = dir.get_next()
	dir.list_dir_end()
	return ""


## `project.godot` must expose exactly the verification scene and no
## autoload of any kind.
func _check_project_config(root: String) -> void:
	var path := root.path_join("project.godot")
	var handle := FileAccess.open(path, FileAccess.READ)
	check(handle != null, "project.godot is readable")
	if handle == null:
		return
	var text := handle.get_as_text()
	handle = null
	check(text.find("config_version=5") != -1,
		"project uses the Godot 4 config format")
	check(text.find("run/main_scene=\"res://scenes/first_render.tscn\"")
		!= -1, "the verification scene is the only main scene")
	check(text.find("4.7") != -1,
		"project features declare the pinned 4.7 engine")
	check(text.find("gl_compatibility") != -1,
		"renderer is gl_compatibility")

	var autoload_section := _section(text, "autoload")
	check_eq(autoload_section.strip_edges(), "",
		"no autoload is registered (no game-system services)")
	var main_scenes := 0
	for relative in ALLOWED:
		if str(relative).ends_with(".tscn"):
			main_scenes += 1
	check_eq(main_scenes, 1, "the project declares exactly one scene")


## Every script and scene must avoid the legacy protocol, game systems,
## network access and Flash runtimes.
func _check_sources(root: String) -> void:
	var scanned := 0
	for relative in ALLOWED:
		var extension := str(relative).get_extension()
		if extension != "gd" and extension != "tscn":
			continue
		if str(relative) == "tests/test_project_scope.gd":
			# This file necessarily contains the token list verbatim, so it
			# cannot scan itself; it is allow-listed above and its list is
			# asserted non-empty below.
			continue
		var handle := FileAccess.open(root.path_join(str(relative)),
			FileAccess.READ)
		check(handle != null, "%s is readable" % relative)
		if handle == null:
			continue
		var body := handle.get_as_text()
		handle = null
		scanned += 1
		for token in FORBIDDEN:
			check(body.find(token) == -1,
				"%s must not reference %s" % [relative, token])
	check_eq(FORBIDDEN.size(), 19,
		"the forbidden-token list is intact (this file is the only source "
		+ "excluded from the scan)")
	info("sources scanned for forbidden references: %s" % scanned)


## Returns the raw body of an INI-style section, or "" when absent.
func _section(text: String, name: String) -> String:
	var header := "[" + name + "]"
	var start := text.find(header)
	if start == -1:
		return ""
	start += header.length()
	var end := text.find("\n[", start)
	if end == -1:
		return text.substr(start)
	return text.substr(start, end - start)
