extends "res://tests/test_base.gd"
## Project-scope check (OpenSpec task 3.1 / spec: modified R1 "Minimal
## render-verification Godot project" + "Remain within the verification
## scope").
##
## Asserts that `apps/client-godot/` contains exactly the render-verification
## content plus the allow-listed foundation files (GameApi with its two
## implementations, boot data, boot scene), the content-registry work (the
## ContentRegistry autoload with its script, its content suite, and the
## asset-ID suite), the session and game-clock work (the Session and
## GameClock autoloads with their scaffold scripts and suites), the
## camera-controls work (the component script and its suite), the
## UI-foundation work (the component script and its suite), and the
## settings/audio-manager work (the Settings and AudioManager autoloads
## with their scripts and suites), the town-rendering work (the
## eighteen town scripts under `scripts/town/`, the town and town-slice
## scenes, their seventeen town suites, the fourteen committed evidence
## captures,
## and the placement, purchase, move, sell, store, upgrade, construction,
## collect, expand, resources, and level (xp) evidence reports), and the
## unit-definitions work (the two `scripts/units/` definition modules, its
## suite, and the `unit-definitions` evidence report), the unit-instances
## work (the two `scripts/units/` instance modules, its suite, and the
## `unit-instances` evidence report), and the unit-queues work (the two
## `scripts/units/` queue modules, its suite, and the `unit-queues` evidence
## report), and the unit-production work (the
## `scripts/units/production_flow.gd` refusal-and-inventory module, its suite,
## and the `unit-production` evidence report), and the unit-collection work (the
## two `scripts/units/` collection modules — the committed-prize projection and
## the pure flow that classifies the acquisition routes and records the two
## authority gaps — its suite, and the `unit-collection` evidence report), and
## the unit-movement work (the `scripts/units/unit_movement.gd` placement
## projection with the movement-command inventory and the content-only refusals,
## its suite, and the `unit-movement` evidence report), and the unit-animations
## work (the `scripts/units/unit_animations.gd` asset-timeline linkage
## projection with the recorded label positions, the `max_frame`
## non-equivalence, the animation-command inventory, and the playback refusals,
## its suite, and the `unit-animations` evidence report), and the unit-behaviors
## work (the `scripts/units/unit_behaviors.gd` dead-hero ledger projection with
## its two-door increment gates and the three-door command inventory, the
## the `scripts/units/behavior_flow.gd` revival intent that carries only an
## identifier and a cell, its suite, and the `unit-behaviors` evidence report),
## and the research work (the `scripts/units/research_flow.gd` two-track counter
## projection with the four recorded branch effects, the `fast_forward` fourth
## writer, and the absent-price/readiness/bounds/reward refusals, its suite, and
## the `research` evidence report), and the quests work (the
## `scripts/units/quest_flow.gd` seven-field quest-state projection with the six
## recorded branch contracts, the seven-entry quest-writer inventory, the
## refused `end_quest` destruction count, and the six recorded refusal families,
## its suite, and the `quests` evidence report):
## no other game system, no scene beyond the allow-list, no script outside
## the allow-list, no Flash-related runtime, no legacy protocol token
## anywhere, and no transport reference outside the legacy-v0
## implementation file.
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
	"scenes/town.tscn",
	"scenes/town_slice.tscn",
	"scripts/audio_manager.gd",
	"scripts/boot.gd",
	"scripts/camera_controls.gd",
	"scripts/comparator.gd",
	"scripts/content_registry.gd",
	"scripts/first_render.gd",
	"scripts/game_clock.gd",
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
	"scripts/session.gd",
	"scripts/settings.gd",
	"scripts/town/iso.gd",
	"scripts/town/collection_flow.gd",
	"scripts/town/construction_flow.gd",
	"scripts/town/expand_flow.gd",
	"scripts/town/level_flow.gd",
	"scripts/town/move_flow.gd",
	"scripts/town/placement_catalog.gd",
	"scripts/town/placement_flow.gd",
	"scripts/town/placement_preview.gd",
	"scripts/town/resource_projection.gd",
	"scripts/town/shop_flow.gd",
	"scripts/town/town.gd",
	"scripts/town/town_hud.gd",
	"scripts/town/town_object.gd",
	"scripts/town/town_slice.gd",
	"scripts/town/town_state.gd",
	"scripts/town/town_terrain.gd",
	"scripts/town/town_visuals.gd",
	"scripts/ui_foundation.gd",
	"scripts/units/unit_catalog.gd",
	"scripts/units/unit_definition.gd",
	"scripts/units/unit_instance.gd",
	"scripts/units/unit_instance_projection.gd",
	"scripts/units/unit_queue.gd",
	"scripts/units/queue_flow.gd",
	"scripts/units/production_flow.gd",
	"scripts/units/collection_prize.gd",
	"scripts/units/collection_flow.gd",
	"scripts/units/unit_movement.gd",
	"scripts/units/unit_animations.gd",
	"scripts/units/unit_behaviors.gd",
	"scripts/units/behavior_flow.gd",
	"scripts/units/research_flow.gd",
	"scripts/units/quest_flow.gd",
	"scripts/progression/tutorial_flow.gd",
	"scripts/units/stored_item_flow.gd",
	"scripts/missions/mission_vocabulary.gd",
	"scripts/units/combat_flow.gd",
	"scripts/units/magic_flow.gd",
	"scripts/rewards/reward_flow.gd",
	"scripts/social/social_state.gd",
	"scripts/social/friends_roster.gd",
	"scripts/social/construction_assist_state.gd",
	"scripts/social/assist_transitions.gd",
	"scripts/events/auction_schedule.gd",
	"scripts/events/auction_oracle.gd",
	"scripts/darts/darts_state.gd",
	"scripts/darts/darts_transitions.gd",
	"scripts/darts/premium_purchase.gd",
	"scripts/darts/week_reset.gd",
	"scripts/verification.gd",
	"tests/test_asset_ids.gd",
	"tests/test_audio_manager.gd",
	"tests/test_base.gd",
	"tests/test_boot_scene.gd",
	"tests/test_camera_controls.gd",
	"tests/test_content_registry.gd",
	"tests/test_game_api_fake.gd",
	"tests/test_game_api_live.gd",
	"tests/test_game_clock.gd",
	"tests/test_package_loader.gd",
	"tests/test_project_scope.gd",
	"tests/test_scene_build.gd",
	"tests/test_session.gd",
	"tests/test_settings.gd",
	"tests/test_town_gate.gd",
	"tests/test_town_collect.gd",
	"tests/test_town_construction.gd",
	"tests/test_town_expand.gd",
	"tests/test_town_xp.gd",
	"tests/test_town_hud.gd",
	"tests/test_town_iso.gd",
	"tests/test_town_move.gd",
	"tests/test_town_placement.gd",
	"tests/test_town_purchase.gd",
	"tests/test_town_resources.gd",
	"tests/test_town_sell.gd",
	"tests/test_town_scene.gd",
	"tests/test_town_selection.gd",
	"tests/test_town_state.gd",
	"tests/test_town_store.gd",
	"tests/test_town_upgrade.gd",
	"tests/test_ui_foundation.gd",
	"tests/test_unit_definitions.gd",
	"tests/test_unit_instances.gd",
	"tests/test_unit_queues.gd",
	"tests/test_unit_experience.gd",
	"tests/test_unit_production.gd",
	"tests/test_unit_collection.gd",
	"tests/test_unit_movement.gd",
	"tests/test_unit_animations.gd",
	"tests/test_unit_behaviors.gd",
	"tests/test_research.gd",
	"tests/test_quests.gd",
	"tests/test_tutorial.gd",
	"tests/test_stored_item_placement.gd",
	"tests/test_mission_vocabulary.gd",
	"tests/test_combat_actions.gd",
	"tests/test_damage_magic.gd",
	"tests/test_rewards.gd",
	"tests/test_social_state.gd",
	"tests/test_darts.gd",
	"tests/test_friends.gd",
	"tests/test_construction_assist.gd",
	"evidence/boot/boot-report.json",
	"evidence/building-move/building-move.png",
	"evidence/building-move/report.json",
	"evidence/building-resources/resources.png",
	"evidence/building-resources/report.json",
	"evidence/building-collect/building-collect.png",
	"evidence/building-collect/report.json",
	"evidence/building-construction/building-construction.png",
	"evidence/building-construction/report.json",
	"evidence/building-expand/building-expand.png",
	"evidence/building-expand/report.json",
	"evidence/building-sell/building-sell.png",
	"evidence/building-sell/report.json",
	"evidence/building-store/building-store.png",
	"evidence/building-store/report.json",
	"evidence/building-upgrade/building-upgrade.png",
	"evidence/building-upgrade/report.json",
	"evidence/building-xp/level-up.png",
	"evidence/building-xp/report.json",
	"evidence/first-render/first-render.png",
	"evidence/first-render/report.json",
	"evidence/placement/placement.png",
	"evidence/placement/report.json",
	"evidence/purchase/purchase.png",
	"evidence/purchase/report.json",
	"evidence/town/report.json",
	"evidence/town/town-player.png",
	"evidence/town/town-slice.png",
	"evidence/unit-definitions/report.json",
	"evidence/unit-instances/report.json",
	"evidence/unit-queues/report.json",
	"evidence/unit-production/report.json",
	"evidence/unit-experience/report.json",
	"evidence/unit-collection/report.json",
	"evidence/unit-movement/report.json",
	"evidence/unit-animations/report.json",
	"evidence/unit-behaviors/report.json",
	"evidence/research/report.json",
	"evidence/quests/report.json",
	"evidence/tutorial/report.json",
	"evidence/stored-placement/report.json",
	"content/mission_vocabulary.json",
	"evidence/mission-vocabulary/report.json",
	"evidence/combat-actions/report.json",
	"evidence/damage-magic/report.json",
	"evidence/rewards/report.json",
	"evidence/social-state/report.json",
	"evidence/darts/report.json",
	"evidence/friends/report.json",
	"evidence/construction-assist/report.json",
	"scripts/events/auction_schedule.gd",
	"scripts/events/auction_oracle.gd",
	"tests/test_auction_schedule.gd",
	"evidence/auction-schedule/report.json",
	"scripts/market/trade_counters.gd",
	"scripts/market/market_schedule.gd",
	"tests/test_market_trade.gd",
	"evidence/market-trade/report.json",
]

## The exact scene set the project may declare (set equality below).
const EXPECTED_SCENES := [
	"scenes/boot.tscn",
	"scenes/first_render.tscn",
	"scenes/town.tscn",
	"scenes/town_slice.tscn",
]

## The six autoloads this change allow-loads (spec: modified R1): the
## foundation bridge, the canonical content registry, the session
## scaffold, the game clock, the settings service, and the audio
## manager, nothing else.
const EXPECTED_AUTOLOADS := [
	"GameApi=\"*res://scripts/gameapi/game_api.gd\"",
	"ContentRegistry=\"*res://scripts/content_registry.gd\"",
	"Session=\"*res://scripts/session.gd\"",
	"GameClock=\"*res://scripts/game_clock.gd\"",
	"Settings=\"*res://scripts/settings.gd\"",
	"AudioManager=\"*res://scripts/audio_manager.gd\"",
]

## Strings that must never appear in ANY project script or scene: legacy
## protocol entry points and form encoding, a Flash runtime, and
## non-loopback network primitives (the camera tokens retired when the
## camera-controls work arrived; the `UiFoundation` token retired when the
## UI foundation arrived — the file inventory now bounds where UI code can
## live, file by file).
const FORBIDDEN := [
	"command.php",
	"FlashVars",
	"AMF",
	"x-www-form-urlencoded",
	"USERID",
	"user_key",
	"Ruffle",
	"ActionScript",
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
## first-render scene still present as its own scene) and exactly the six
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
	check_eq(entries.size(), 6,
		"exactly six allow-listed autoloads are registered "
		+ "(no other game-system services)")
	if entries.size() == 6:
		var actual: Array = entries.duplicate()
		actual.sort()
		var expected: Array = EXPECTED_AUTOLOADS.duplicate()
		expected.sort()
		check_eq(actual, expected,
			"the only autoloads are GameApi, ContentRegistry, "
			+ "Session, GameClock, Settings and AudioManager")
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
		"the scene set is exactly {boot.tscn, first_render.tscn, "
			+ "town.tscn, town_slice.tscn}")
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
	check_eq(FORBIDDEN.size(), 13,
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
