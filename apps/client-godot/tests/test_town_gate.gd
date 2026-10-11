extends "res://tests/test_base.gd"
## The no-Flash vertical-slice gate (roadmap item 36 "Create no-Flash
## vertical-slice test"; OpenSpec `godot-town-rendering` change task 8.2).
##
## One suite aggregates the milestone's own checklist into executable
## checks, so a single headless run answers it:
##
##   Godot launches              the pinned 4.7 engine runs this suite
##   no Flash runtime installed  the project ships no SWF/SWC/FLA payload
##   no ruffle installed         no player payload exists and no project
##                               source references a flash/ruffle runtime
##   existing legacy save loads  the fresh bootstrap fixture (40
##                               placements) and the preserved Scarlet
##                               village (576 placements) both parse into
##                               typed town state
##   town renders                scenes/town.tscn builds the fixture town
##   terrain renders             mapa1.jpg decodes and stretches over the
##                               projection world rectangle
##   buildings render            all 40 fixture placements build as objects
##                               with content footprints and a chosen visual
##   unit renders                the slice scene renders the Wild Elephant
##                               unit (and House I) as authentic converted
##                               package sprites — the fresh save contains
##                               no units, so the slice is the unit evidence
##   HUD renders                 the fresh save's verbatim strings
##   camera works                committed world bounds, an in-bounds pan,
##                               a rejected out-of-bounds pan, zoom levels
##   selection works             topmost hit commits, empty clears,
##                               non-finite press rejected unchanged
##
## Plus this change's recorded residuals: the land-fit classification of
## `mapa1.jpg` under the recorded derivation convention — each placement's
## saved-cell anchor (the center of its 1x1 footprint rect) projected
## through the committed constants into the image, classified water by
## blue dominance (`b - max(r,g) > 18`) — fresh 39/40 land with the single
## residual being bridge item 929 at (29,48) over the crater lake, Scarlet
## 549/576 land, 0 off-grid in both; and the slice sprite coverage (267
## converted sprites, 263 keyed thumbnails, 38 footprint markers, 8
## unknown-id placeholders over 576 placements).
##
## The sprite/thumbnail/marker/placeholder counts are NOT transcribed
## conveniences: `_hierarchy_report` restates the committed visual
## hierarchy over the corpus — a placement whose committed item sprite
## carries the `converted` status is a sprite, any other placement with a
## preserved thumbnail is a thumbnail, one with neither is a footprint
## marker, and an id absent from content is a placeholder — and requires
## every rendered object to agree with it, placement by placement. The
## pinned dictionaries below are the measured corpus outcome that
## agreement produces, and the 20 slice placements whose converted package
## fails frame-1 resolution are asserted by package rather than folded
## into the totals.
##
## Claim limits: structural checks only. No pixel-parity oracle against the
## legacy client, no gameplay parity, no host-machine program inventory —
## the no-Flash claims are a project payload/source scan (Flash, a browser,
## and every action-script VM never execute in this run). The source-scan
## needles are lowercase on purpose: the project-scope suite scans this
## file's bytes for the literal capitalized forms, so this file and the
## project-scope token scanner (which necessarily names those forms) are
## skipped while scanning. Runs headless as part of `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")
const Iso = preload("res://scripts/town/iso.gd")

const FRESH_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const SCARLET_VILLAGE := "villages/Scarlet.json"
const TERRAIN_REF := "mapa1.jpg"
## This suite's own path: excluded from the source scan (it necessarily
## names the needles below).
const SELF := "tests/test_town_gate.gd"
## The project-scope suite: the literal-token scanner itself, excluded for
## the same reason (it names the capitalized forms its scan forbids).
const SCOPE_SUITE := "tests/test_project_scope.gd"

## The fresh save's verbatim HUD strings (fixture ground truth, shared
## with `test_town_hud`).
const FRESH_HUD := {
	"gold": "2000", "wood": "2000", "steel": "2000", "oil": "2000",
	"cash": "5", "energy": "50", "mana": "0",
	"name": "Warrior", "level": "1", "xp": "4",
}
## Recorded fresh visual-hierarchy outcome. Since the mass conversion
## (OpenSpec `asset-package-mass-conversion`) produced converted packages
## for 292 item sprites, the fresh save's Wall I (item 23, 16 placements)
## and Space Station (item 909) now take the top rung and render as
## converted package sprites; the nine placements whose sprite has no
## preserved thumbnail (928 x2, 929 x7) still render as footprint
## markers. Measured on this tree, and re-derived per placement by
## `_hierarchy_report` — see the class comment.
const FRESH_SOURCES := {"sprite": 17, "marker": 9, "thumbnail": 14}
## Recorded slice visual-hierarchy outcome over the 576 village
## placements. The 38 markers are the 18 placements whose sprite has no
## preserved thumbnail (929 x7, 1001 x4, 1007 x7) PLUS the 20 degraded
## sprite placements pinned by `SLICE_DEGRADED_SPRITES`; the two are
## asserted separately and never folded into one number.
const SLICE_SOURCES := {
	"sprite": 267, "thumbnail": 263, "marker": 38, "placeholder": 8}

const FRESH_PLACEMENTS := 40
const SLICE_PLACEMENTS := 576

## Recorded land-fit residual (README "Isometric projection constants").
const FRESH_LAND := 39
const FRESH_WATER := 1
const SCARLET_LAND := 549
const SCARLET_WATER := 27
const FRESH_WATER_ENTRY := {
	"item": 929, "cell": Vector2i(29, 48), "verdict": "water"}

## Recorded slice sprite coverage: 267 of the 576 village placements hold
## an item whose sprite the mass conversion produced a package for, and
## every one of them renders from that package. House I (item 1) and Wild
## Elephant (item 933) are additionally checked by id, because they are
## the slice's only building and unit proof respectively.
const SLICE_SPRITE_TOTAL := 267
const HOUSE_ID := 1
const HOUSE_SPRITES := 1
const ELEPHANT_ID := 933
const ELEPHANT_SPRITES := 6
const SLICE_PLACEHOLDERS := 8
## Placements the hierarchy put on the sprite rung whose converted package
## then failed frame-1 resolution, so the object degraded to the footprint
## marker with `visual_error` naming the package. Measured on this tree:
## 20 placements over four packages, every one of them failing because the
## committed loader renders fill type 65 only (`package_loader.gd`
## `FILL_TYPE_BITMAP`) while these four packages carry a fill of type 67 —
## recorded here rather than repaired, because neither the converter nor
## the loader is owned by this suite. Package directory -> placements.
const SLICE_DEGRADED_SPRITES := {
	"assets/converted/buildings/0063_cannon_academy_3_m": 1,
	"assets/converted/buildings/0065_workshop_3_m": 1,
	"assets/converted/buildings/0093_pear_tree_m": 13,
	"assets/converted/units/1023_bazooka_3_m": 5,
}

## Source-scan needles: a ruffle player and action-script/flash authoring
## references must appear in no project source. Lowercase on purpose (see
## the class comment on byte-level token hygiene); the scan folds the
## scanned file to lowercase before matching.
const RUNTIME_NEEDLES := ["ruffle", "actionscript", "flashvars", "shockwave"]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	_check_godot_launches()
	_check_no_flash_payload()
	_check_no_flash_references()
	var registry: Variant = root.get_node_or_null("/root/ContentRegistry")
	check(registry != null, "the ContentRegistry autoload is registered")
	if registry == null:
		return
	var content: Dictionary = registry.load_content()
	check_eq(bool(content.get("ok", false)), true,
		"content loads explicitly before the gate reads it")
	if not bool(content.get("ok", false)):
		info("[gate] content load failed: %s" % content.get("error", ""))
		return
	var assets: Dictionary = registry.load_asset_registry()
	check_eq(bool(assets.get("ok", false)), true,
		"the asset registry loads explicitly before the gate reads it")
	if not bool(assets.get("ok", false)):
		info("[gate] asset registry load failed: %s" % assets.get("error", ""))
		return
	var fresh: Variant = _parse_input(registry, FRESH_FIXTURE,
		FRESH_PLACEMENTS, "the fresh bootstrap fixture")
	if fresh == null:
		return
	var village: Variant = _parse_input(registry, SCARLET_VILLAGE,
		SLICE_PLACEMENTS, "the preserved Scarlet village")
	if village == null:
		return
	var town: Node2D = _build_town(fresh)
	if town == null:
		return
	_check_terrain(town)
	_check_buildings(town, fresh)
	_check_hud(town)
	_check_selection(town)
	_check_camera(town)
	town.free()
	var slice: Node2D = _build_slice()
	if slice == null:
		return
	_check_slice_sprites(slice)
	_check_land_fit(registry, fresh, village)
	slice.free()


## Item 36 first line: the engine this suite runs on.
func _check_godot_launches() -> void:
	var version: Dictionary = Engine.get_version_info()
	check_eq(int(version.get("major", 0)), 4,
		"Godot launches: engine major version 4")
	check_eq(int(version.get("minor", 0)), 7,
		"Godot launches: engine minor version 7")
	check(str(version.get("string", "")).contains("4.7.2"),
		"Godot launches: pinned 4.7.2 runs this gate (%s)"
		% str(version.get("string", "")))


## Item 36 "no Flash runtime installed / no ruffle installed" — the
## payload half: no runtime file of either kind exists in the project
## (file-level claim only; see the class comment for claim limits).
func _check_no_flash_payload() -> void:
	var found: Array = []
	var error := _collect(Paths.project_dir(), "", found)
	check_eq(error, "", "the project directory is readable for the payload scan")
	found.sort()
	var payloads: Array = []
	var players: Array = []
	for relative in found:
		var lower := str(relative).to_lower()
		var extension := lower.get_extension()
		if extension == "swf" or extension == "swc" or extension == "fla":
			payloads.append(str(relative))
		var base := lower.get_file()
		if base.contains("ruffle") or base.contains("flashplayer") \
				or base.contains("flash_player") or base.contains("shockwave"):
			players.append(str(relative))
	check_eq(payloads, [],
		"no Flash runtime payload file (swf/swc/fla) exists in the project")
	check_eq(players, [],
		"no Flash or ruffle player executable exists in the project")
	info("project files scanned for runtime payloads: %s" % found.size())


## The reference half of the no-Flash claim: no project source names a
## flash/ruffle/action-script runtime. The literal capitalized tokens are
## deliberately absent from this file's bytes (the project-scope suite
## scans them); this suite scans case-folded needles and skips itself and
## the project-scope scanner, both of which necessarily name them.
func _check_no_flash_references() -> void:
	var found: Array = []
	var error := _collect(Paths.project_dir(), "", found)
	check_eq(error, "",
		"the project directory is readable for the source scan")
	found.sort()
	var offenders: Array = []
	var scanned := 0
	for relative in found:
		var lower := str(relative).to_lower()
		if not lower.ends_with(".gd") and not lower.ends_with(".tscn"):
			continue
		if str(relative) == SELF or str(relative) == SCOPE_SUITE:
			continue  # this file and the token scanner name the needles
		scanned += 1
		var handle := FileAccess.open(
			Paths.project_dir().path_join(str(relative)), FileAccess.READ)
		if handle == null:
			offenders.append(str(relative) + " (unreadable)")
			continue
		var body := handle.get_as_text().to_lower()
		handle.close()
		for needle in RUNTIME_NEEDLES:
			if body.contains(str(needle)):
				offenders.append("%s (%s)" % [str(relative), str(needle)])
				break
	check_eq(offenders, [],
		"no project source references a flash/ruffle/action-script runtime")
	info("sources scanned for runtime references: %s" % scanned)


## Item 36 "existing legacy save loads": one preserved input, parsed
## fail-closed into typed state with its placement count.
func _parse_input(registry: Variant, relative: String, expected: int,
		label: String) -> Variant:
	var absolute := Paths.repo_root().path_join(relative)
	check(FileAccess.file_exists(absolute), "%s exists: %s" % [label, relative])
	if not FileAccess.file_exists(absolute):
		return null
	var payload: Variant = JSON.parse_string(
		FileAccess.get_file_as_bytes(absolute).get_string_from_utf8())
	check(payload is Dictionary, "%s is a JSON object" % label)
	if not (payload is Dictionary):
		return null
	var parsed: Dictionary = TownState.parse(payload, registry)
	check_eq(bool(parsed.get("ok", false)), true,
		"%s parses into typed town state" % label)
	if not bool(parsed.get("ok", false)):
		info("[gate] %s rejected: %s" % [label, parsed.get("error", "")])
		return null
	var state: Variant = parsed["state"]
	check_eq(state.placements.size(), expected,
		"%s loads all %d placements" % [label, expected])
	return state


## Item 36 "town renders": the fresh save builds scenes/town.tscn.
func _build_town(fresh: Variant) -> Node2D:
	var scene: PackedScene = load("res://scenes/town.tscn")
	check(scene != null, "scenes/town.tscn loads")
	if scene == null:
		return null
	var town: Node2D = scene.instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(fresh)
	check_eq(bool(built.get("ok", false)), true,
		"town renders: the existing legacy save builds a town view")
	if not bool(built.get("ok", false)):
		info("[gate] town build failed: %s" % built.get("error", ""))
		town.free()
		return null
	check_eq(str(town.view_state), "built",
		"town renders: the view commits its built state")
	check(town.build_ok, "town renders: the build gate commits")
	check_eq(town.objects.size(), FRESH_PLACEMENTS,
		"town renders: all 40 saved placements become objects")
	return town


## Item 36 "terrain renders": the legacy island image decoded, recorded,
## and anchored to the projection's world rectangle.
func _check_terrain(town: Node2D) -> void:
	var terrain: Variant = town.terrain
	check(terrain != null, "terrain renders: the scene instances the layer")
	if terrain == null:
		return
	check(terrain.texture != null,
		"terrain renders: mapa1.jpg decodes into a texture")
	check_eq(str(terrain.terrain_ref), TERRAIN_REF,
		"terrain records its legacy content reference")
	check_eq(str(terrain.asset_status), "passthrough",
		"terrain records its asset resolution status (passthrough)")
	check_eq(terrain.image_size, Vector2i(701, 514),
		"terrain decodes the preserved 701x514 island image")
	check_eq(Vector2(terrain.position), Iso.world_rect().position,
		"terrain anchors at the projection world origin")
	check_eq(Vector2(terrain.size), Iso.world_rect().size,
		"terrain stretches over the whole projection world rectangle")


## Item 36 "buildings render": every fixture placement becomes a rendered
## object with content metadata and a chosen visual (this save holds no
## units — unit rendering is proven by the slice coverage below).
func _check_buildings(town: Node2D, fresh: Variant) -> void:
	check_eq(town.object_counts_by_source(), FRESH_SOURCES,
		"buildings render: the visual hierarchy covers every placement "
		+ "(17 converted sprites + 14 keyed thumbnails + 9 markers)")
	var report: Dictionary = _hierarchy_report(town.objects)
	check_eq(report["mismatched"], [],
		"buildings render: every fresh placement renders the rung its "
		+ "committed sprite status selects")
	check_eq(report["degraded"], {},
		"buildings render: no fresh converted package degrades to the "
		+ "footprint marker")
	var buildings := 0
	for placement in fresh.placements:
		if str(placement.kind) == "building":
			buildings += 1
	check_eq(buildings, FRESH_PLACEMENTS,
		"buildings render: every fixture placement resolves as a building")
	var without_visual := 0
	var bad_footprint := 0
	for object in town.objects:
		if str(object.visual_source).is_empty() or int(object.legacy_id) < 0:
			without_visual += 1
		if object.footprint.x <= 0 or object.footprint.y <= 0:
			bad_footprint += 1
	check_eq(without_visual, 0,
		"buildings render: every object names its chosen visual source")
	check_eq(bad_footprint, 0,
		"buildings render: every object carries a positive content footprint")


## Item 36 "HUD renders": the fresh save's verbatim strings.
func _check_hud(town: Node2D) -> void:
	var hud: Variant = town.hud()
	check(hud != null, "HUD renders: the resource HUD attaches")
	if hud == null:
		return
	check_eq(hud.displayed_fields(), FRESH_HUD,
		"HUD renders: every field shows the fixture's verbatim string")


## Item 36 "selection works": topmost hit commits, a rejected press
## changes nothing, empty/out-of-grid space clears.
func _check_selection(town: Node2D) -> void:
	var cell: Vector2i = town.objects[0].cell
	var expected := -1
	for object in town.objects:
		if object.contains_cell(cell):
			expected = int(object.legacy_id)  # last in draw order wins
	var press: Dictionary = town.handle_pointer_press(Iso.grid_to_screen(cell))
	check_eq(bool(press.get("ok", false)), true,
		"selection: a press on a footprint is accepted")
	check_eq(int(press.get("legacy_id", -1)), expected,
		"selection: the depth-topmost object under the press commits")
	check(town.selection() != null,
		"selection: the committed selection is exposed")
	check_eq(town.selection_legacy_id(), expected,
		"selection: the public getter reports the selected placement")
	var bad: Dictionary = town.handle_pointer_press(Vector2(NAN, 0.0))
	check_eq(bool(bad.get("ok", false)), false,
		"selection: a non-finite press is rejected")
	check(String(bad.get("error", "")).contains("non_finite_press"),
		"selection: the rejection names the condition")
	check_eq(town.selection_legacy_id(), expected,
		"selection: the rejected press changes nothing")
	var clear: Dictionary = town.handle_pointer_press(Vector2(-800.0, -800.0))
	check_eq(bool(clear.get("cleared", false)), true,
		"selection: a press on out-of-grid space clears")
	check_eq(town.selection_legacy_id(), -1,
		"selection: the cleared getter reports an empty selection")


## Item 36 "camera works": committed world bounds over the projection
## rect, an accepted in-bounds pan, a rejected out-of-bounds pan, and the
## zoom level/factor table.
func _check_camera(town: Node2D) -> void:
	var camera: Variant = town.camera
	check(camera.has_world_bounds(), "camera works: world bounds are committed")
	check_eq(camera.world_bounds(), Iso.world_rect(),
		"camera works: bounds equal the projection world rectangle")
	check(Iso.world_rect().has_point(camera.position),
		"camera works: the view is framed on the town inside the bounds")
	var before: Vector2 = camera.position
	var moved: Dictionary = camera.pan_by(Vector2(10.0, -5.0))
	check_eq(bool(moved.get("ok", false)), true,
		"camera works: an in-bounds pan is accepted")
	check_eq(camera.position, before + Vector2(10.0, -5.0),
		"camera works: the pan moves exactly the requested delta")
	var blocked: Dictionary = camera.pan_by(Vector2(100000.0, 0.0))
	check_eq(bool(blocked.get("ok", false)), false,
		"camera works: an out-of-bounds pan is rejected")
	check(String(blocked.get("error", "")).contains("outside_world_bounds"),
		"camera works: the rejection names the violated condition")
	check_eq(camera.position, before + Vector2(10.0, -5.0),
		"camera works: the rejected pan leaves the position untouched")
	var raised: Dictionary = camera.zoom_in()
	check_eq(bool(raised.get("ok", false)), true,
		"camera works: zoom in commits a level")
	check_eq(camera.zoom_level(), 1, "camera works: one zoom level committed")
	check_eq(camera.zoom_factor(), 2.0,
		"camera works: the factor table follows the level")
	check_eq(camera.zoom, Vector2(2.0, 2.0),
		"camera works: the node zoom equals the committed factor")
	var lowered: Dictionary = camera.zoom_out()
	check_eq(bool(lowered.get("ok", false)), true,
		"camera works: zoom out commits a level")
	check_eq(camera.zoom_level(), 0,
		"camera works: zoom returns to the base level")
	check_eq(camera.zoom_factor(), 1.0,
		"camera works: the base factor is 1.0")
	check_eq(camera.zoom, Vector2.ONE,
		"camera works: the node zoom matches the base level")


## The slice verification view: the preserved village through the same
## components (item 36's unit evidence).
func _build_slice() -> Node2D:
	var scene: PackedScene = load("res://scenes/town_slice.tscn")
	check(scene != null, "scenes/town_slice.tscn loads")
	if scene == null:
		return null
	var slice: Node2D = scene.instantiate()
	root.add_child(slice)
	check_eq(str(slice.view_state), "built",
		"the slice view builds from the preserved village")
	if str(slice.view_state) != "built":
		info("[gate] slice build failed: %s" % str(slice.build_error))
		slice.free()
		return null
	return slice


## Slice sprite coverage: authentic converted package sprites for the
## building and the unit, plus the recorded placeholder count.
func _check_slice_sprites(slice: Node2D) -> void:
	check_eq(slice.objects.size(), SLICE_PLACEMENTS,
		"the slice renders all 576 village placements")
	check_eq(slice.object_counts_by_source(), SLICE_SOURCES,
		"the slice visual hierarchy matches the recorded coverage")
	var report: Dictionary = _hierarchy_report(slice.objects)
	check_eq(report["mismatched"], [],
		"every village placement renders the rung its committed sprite "
		+ "status selects")
	check_eq(report["degraded"], SLICE_DEGRADED_SPRITES,
		"the converted packages that fail frame-1 resolution are exactly "
		+ "these four, at these placement counts")
	var sprites := 0
	var house := 0
	var elephant := 0
	var placeholders := 0
	for object in slice.objects:
		var source := str(object.visual_source)
		if source == TownVisuals.SOURCE_SPRITE:
			sprites += 1
			if int(object.legacy_id) == HOUSE_ID:
				house += 1
			elif int(object.legacy_id) == ELEPHANT_ID:
				elephant += 1
		elif source == TownVisuals.SOURCE_PLACEHOLDER:
			placeholders += 1
	check_eq(sprites, SLICE_SPRITE_TOTAL,
		"unit/building sprite coverage: 267 village placements render as "
		+ "converted package sprites")
	check_eq(house, HOUSE_SPRITES,
		"building sprite coverage: House I renders as a converted sprite")
	check_eq(elephant, ELEPHANT_SPRITES,
		"unit sprite coverage: all six Wild Elephant placements render "
		+ "as converted sprites")
	check_eq(placeholders, SLICE_PLACEHOLDERS,
		"the eight content-unknown placements render as placeholders")


## The committed visual hierarchy (`town_visuals.gd`) restated over the
## corpus instead of over the renderer: a placement whose committed item
## sprite carries the `converted` status takes the sprite rung, any other
## placement with a preserved thumbnail takes the thumbnail rung, one with
## neither takes the footprint-marker rung, and a placement whose legacy id
## is absent from content takes the placeholder rung. The two inputs are
## the registry status already projected onto the placement and the
## thumbnail file on disk — deliberately NOT the renderer's own loader
## result, so a package that fails to resolve is reported as a degradation
## instead of quietly agreeing with itself.
static func _expected_rung(placement: Variant) -> String:
	if not bool(placement.content_ok):
		return TownVisuals.SOURCE_PLACEHOLDER
	if str(placement.asset_status) == "converted":
		return TownVisuals.SOURCE_SPRITE
	if FileAccess.file_exists(Paths.repo_root().path_join(
			"assets/thumbs/%s.jpg" % str(placement.img_name))):
		return TownVisuals.SOURCE_THUMBNAIL
	return TownVisuals.SOURCE_MARKER


## Compares every rendered object against `_expected_rung` and splits the
## differences into genuine mismatches and recorded degradations, so the
## two are never mistaken for one another. Returns
## `{"mismatched": [...], "degraded": {package_dir: placement_count}}`;
## `degraded` is empty when every placement took the rung it committed to.
static func _hierarchy_report(objects: Array) -> Dictionary:
	var mismatched: Array = []
	var degraded: Dictionary = {}
	for object in objects:
		var expected := _expected_rung(object.placement)
		var actual := str(object.visual_source)
		if actual == expected:
			continue
		var reason := str(object.visual_error)
		if expected == TownVisuals.SOURCE_SPRITE \
				and actual == TownVisuals.SOURCE_MARKER \
				and not reason.is_empty():
			var package := _degraded_package(reason)
			degraded[package] = int(degraded.get(package, 0)) + 1
			continue
		mismatched.append("id %d at %s: committed %s, rendered %s (%s)"
			% [int(object.legacy_id), object.cell, expected, actual,
				reason if not reason.is_empty() else "no reason recorded"])
	return {"mismatched": mismatched, "degraded": degraded}


## The package directory a degradation reason names — the loader brackets
## it — or "" when the reason names none.
static func _degraded_package(reason: String) -> String:
	var open := reason.find("[")
	var close := reason.find("]", open + 1)
	if open < 0 or close < 0:
		return ""
	return reason.substr(open + 1, close - open - 1)


## The recorded land-fit assertion (task 8.2): the derivation convention
## over the stretched island image, both saved inputs.
func _check_land_fit(registry: Variant, fresh: Variant,
		village: Variant) -> void:
	var image: Variant = _decode_terrain(registry)
	if image == null:
		return
	var fresh_fit := _land_fit(fresh, image)
	check_eq(fresh_fit["land"], FRESH_LAND,
		"land fit: 39 of 40 fresh placements classify onto land")
	check_eq(fresh_fit["water"], FRESH_WATER,
		"land fit: the fresh residual is a single water placement")
	check_eq(fresh_fit["off"], 0,
		"land fit: every fresh projection lands inside the image")
	check_eq(fresh_fit["water_entries"], [FRESH_WATER_ENTRY],
		"land fit: the residual is bridge item 929 at (29,48) over the "
		+ "crater lake")
	var village_fit := _land_fit(village, image)
	check_eq(village_fit["land"], SCARLET_LAND,
		"land fit: 549 of 576 village placements classify onto land")
	check_eq(village_fit["water"], SCARLET_WATER,
		"land fit: 27 village placements classify as water")
	check_eq(village_fit["off"], 0,
		"land fit: every village projection lands inside the image")


## Decodes the island image from its preserved bytes (the same asset the
## terrain renders), fail-closed.
func _decode_terrain(registry: Variant) -> Variant:
	var asset: Dictionary = registry.resolve_asset("images", TERRAIN_REF)
	check_eq(bool(asset.get("found", false)), true,
		"land fit: the island image resolves through the content registry")
	if not bool(asset.get("found", false)):
		return null
	var runtime := str((asset.get("entry") as Dictionary).get("runtime", ""))
	var image := Image.new()
	var status := image.load_jpg_from_buffer(
		FileAccess.get_file_as_bytes(Paths.repo_root().path_join(runtime)))
	check_eq(status, OK, "land fit: mapa1.jpg decodes from its bytes")
	if status != OK:
		return null
	image.convert(Image.FORMAT_RGBA8)
	return image


## The recorded D2 derivation convention: each placement's saved-cell
## anchor — the center of its 1x1 footprint rect — projects through the
## committed constants into the image; blue dominance marks water.
## Returns the counts plus the structured residual entries.
func _land_fit(state: Variant, image: Image) -> Dictionary:
	var world := Iso.world_rect()
	var land := 0
	var water := 0
	var off := 0
	var water_entries: Array = []
	for placement in state.placements:
		var rect: Rect2 = Iso.footprint_rect(placement.cell, 1, 1)
		var center := rect.position + rect.size / 2.0
		var px := int(center.x / world.size.x * image.get_width())
		var py := int(center.y / world.size.y * image.get_height())
		if px < 0 or py < 0 or px >= image.get_width() \
				or py >= image.get_height():
			off += 1
			water_entries.append({"item": placement.item,
				"cell": placement.cell, "verdict": "off"})
			continue
		var color := image.get_pixel(px, py)
		if int(color.b8) - maxi(int(color.r8), int(color.g8)) > 18:
			water += 1
			water_entries.append({"item": placement.item,
				"cell": placement.cell, "verdict": "water"})
		else:
			land += 1
	return {"land": land, "water": water, "off": off,
		"water_entries": water_entries}


## Recursive project walker (mirrors the project-scope suite; `.godot/`
## excluded by design).
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
