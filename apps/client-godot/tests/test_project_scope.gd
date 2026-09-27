extends "res://tests/test_base.gd"
## Project-scope check (OpenSpec task 3.1 / spec: modified R1 "Minimal
## render-verification Godot project" + "Remain within the verification
## scope").
##
## Asserts that `apps/client-godot/` contains exactly the render-verification
## content plus the allow-listed foundation files (GameApi with its two
## implementations, boot data, boot scene) and the content-registry work this
## change introduces (the ContentRegistry autoload with its script, its
## content suite, and the asset-ID suite): no other game system, no scene
## beyond the allow-list, no script outside the allow-list, no Flash-related
## runtime, no legacy protocol token anywhere, and no transport reference
## outside the legacy-v0 implementation file.
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
	"verify-boot.ps1",
	"compat_live_phase.py",
	"scenes/boot.tscn",
	"scenes/first_render.tscn",
	"scripts/boot.gd",
	"scripts/comparator.gd",
	"scripts/content_registry.gd",
	"scripts/first_render.gd",
	"scripts/gameapi/boot_data.gd",
	"scripts/gameapi/fake_api.gd",
	"scripts/gameapi/game_api.gd",
	"scripts/gameapi/legacy_v0_api.gd",
	"scripts/layout.gd",
	"scripts/package_loader.gd",
	"scripts/package_paths.gd",
	"scripts/reference_compositor.gd",
	"scripts/report.gd",
	"scripts/run_compare.gd",
	"scripts/run_selftest.gd",
	"scripts/verification.gd",
	"tests/test_asset_ids.gd",
	"tests/test_base.gd",
	"tests/test_boot_scene.gd",
	"tests/test_content_registry.gd",
	"tests/test_game_api_fake.gd",
	"tests/test_game_api_live.gd",
	"tests/test_package_loader.gd",
	"tests/test_project_scope.gd",
	"tests/test_scene_build.gd",
	"evidence/boot/boot-report.json",
	"evidence/first-render/first-render.png",
	"evidence/first-render/report.json",
]

## The exact scene set the project may declare (set equality below).
const EXPECTED_SCENES := [
	"scenes/boot.tscn",
	"scenes/first_render.tscn",
]

## The two autoloads this change allow-loads (spec: modified R1): the
## foundation bridge and the canonical content registry, nothing else.
const EXPECTED_AUTOLOADS := [
	"GameApi=\"*res://scripts/gameapi/game_api.gd\"",
	"ContentRegistry=\"*res://scripts/content_registry.gd\"",
]

## Strings that must never appear in ANY project script or scene: legacy
## protocol entry points and form encoding, a Flash runtime, the game
## systems deferred to their own changes, non-loopback network primitives,
## and any UI-foundation system (which the allow-list additionally excludes
## file by file).
const FORBIDDEN := [
	"command.php",
	"FlashVars",
	"AMF",
	"x-www-form-urlencoded",
	"USERID",
	"user_key",
	"Ruffle",
	"ActionScript",
	"GameClock",
	"Session",
	"Camera2D",
	"Camera3D",
	"UiFoundation",
	"WebSocket",
	"TCPServer",
	"UDPServer",
	"PacketPeer",
	"https://",
]

## Transport tokens allowed in exactly one file: the legacy-v0
## implementation (spec: "Keep legacy transport out of the UI" — only the
## legacy-v0 implementation may reference the compat endpoint or the HTTP
## request client).
const LEGACY_V0_FILE := "scripts/gameapi/legacy_v0_api.gd"
const RESTRICTED_TO_LEGACY_V0 := [
	"http://",
	"HTTPRequest",
	"HTTPClient",
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
		"only allow-listed foundation/verification files exist in the project")
	var missing: Array = []
	for allowed in ALLOWED:
		if not found.has(allowed):
			missing.append(allowed)
	check_eq(missing, [], "every allow-listed file exists")
	var flash_files: Array = []
	for relative in found:
		var extension := str(relative).get_extension().to_lower()
		if extension == "swf" or extension == "swc":
			flash_files.append(str(relative))
	check_eq(flash_files, [],
		"no Flash runtime payload file exists in the project")
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


## `project.godot` must declare the boot scene as the main scene (with the
## first-render scene still present as its own scene) and exactly the two
## allow-listed autoloads.
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
	check(text.find("run/main_scene=\"res://scenes/boot.tscn\"") != -1,
		"the boot scene is the main scene")
	check(text.find("4.7") != -1,
		"project features declare the pinned 4.7 engine")
	check(text.find("gl_compatibility") != -1,
		"renderer is gl_compatibility")

	var autoload_section := _section(text, "autoload")
	var entries: Array = []
	for line in autoload_section.split("\n"):
		var stripped := line.strip_edges()
		if stripped != "":
			entries.append(stripped)
	check_eq(entries.size(), 2,
		"exactly two allow-listed autoloads are registered "
		+ "(no other game-system services)")
	if entries.size() == 2:
		var actual: Array = entries.duplicate()
		actual.sort()
		var expected: Array = EXPECTED_AUTOLOADS.duplicate()
		expected.sort()
		check_eq(actual, expected,
			"the only autoloads are GameApi and ContentRegistry")
	else:
		fail("unexpected autoload entries: %s" % str(entries))

	var scenes: Array = []
	for relative in ALLOWED:
		if str(relative).ends_with(".tscn"):
			scenes.append(str(relative))
	scenes.sort()
	var expected: Array = EXPECTED_SCENES.duplicate()
	expected.sort()
	check_eq(scenes, expected,
		"the scene set is exactly {boot.tscn, first_render.tscn}")
	check(scenes.has("scenes/first_render.tscn"),
		"the first-render verification scene remains runnable")


## Every script and scene must avoid the legacy protocol, Flash runtimes,
## non-loopback transports and the deferred game systems; transport tokens
## are confined to the legacy-v0 implementation file.
func _check_sources(root: String) -> void:
	var scanned := 0
	for relative in ALLOWED:
		var extension := str(relative).get_extension()
		if extension != "gd" and extension != "tscn":
			continue
		if str(relative) == "tests/test_project_scope.gd":
			# This file necessarily contains the token lists verbatim, so it
			# cannot scan itself; it is allow-listed above and its lists are
			# asserted intact below.
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
		for token in RESTRICTED_TO_LEGACY_V0:
			if str(relative) == LEGACY_V0_FILE:
				continue
			check(body.find(token) == -1,
				"%s must not reference %s (confined to %s)"
				% [relative, token, LEGACY_V0_FILE])
	check_eq(FORBIDDEN.size(), 18,
		"the forbidden-token list is intact (this file is the only source "
		+ "excluded from the scan)")
	check_eq(RESTRICTED_TO_LEGACY_V0.size(), 3,
		"the legacy-v0-only token list is intact")
	check(ALLOWED.has(LEGACY_V0_FILE),
		"the legacy-v0 implementation is allow-listed and scanned")
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
