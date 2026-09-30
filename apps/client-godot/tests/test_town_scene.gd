extends "res://tests/test_base.gd"
## Town scene suite (OpenSpec `godot-town-rendering` "Terrain rendering",
## "Town object rendering", "Isometric depth sorting", "Authoritative
## resource HUD", change task 3.2).
##
## Scenarios:
##   built     the fresh-save fixture builds `scenes/town.tscn`: terrain
##              decoded from the preserved jpg and stretched over the
##              world rectangle, all 40 placements rendered as objects at
##              their saved cells with content footprints and metadata,
##              the visual hierarchy choosing 31 thumbnails (keyed to
##              transparency) + 9 footprint markers, camera world bounds
##              committed with the focus framed on the town, and the HUD
##              slot displaying exactly `str(state.value)` per field;
##   depth     the committed draw order is non-decreasing in isometric
##              depth with the documented tie-break, and a rebuild
##              reproduces the identical ordered render list;
##   selection an in-grid press selects the object under it (highlight
##              committed), empty/out-of-ground presses clear, and a
##              non-finite press fails closed leaving selection unchanged;
##   error     an unloaded registry fails the build into the explicit
##              error state naming the terrain failure with no partial
##              render, and a null state fails the same way;
##   slice     the preserved `villages/Scarlet.json` builds through
##              `scenes/town_slice.tscn`: House I and Wild Elephant as
##              authentic converted package sprites at their legacy
##              cells, the eight content-unknown placements as labeled
##              placeholders, that save's HUD strings, its depth order,
##              camera bounds, and press-to-cell selection, with the
##              input recorded by path + SHA-256 and left byte-identical
##              (change task 7.2).
##
## Uses the ContentRegistry autoload (content + asset registry loaded
## explicitly, per its contract). No API, no server. Runs headless as part
## of `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")
const Iso = preload("res://scripts/town/iso.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")

const FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
## The preserved slice village (read-only legacy input) and its committed
## SHA-256 — the suite proves the render path leaves it byte-identical.
const SLICE_VILLAGE := "villages/Scarlet.json"
const SLICE_VILLAGE_SHA256 := \
	"ef217cf2004f97e53bb4f078b8bdd39a1301280d2f77f9ade877f8aaf26ee354"
## House I's cell in the village file (row `2061`: item 1 at (86,73)).
const SLICE_HOUSE_CELL := Vector2i(86, 73)
## Visual-source counts over the 576 village placements: the hierarchy
## chooses 7 converted sprites (House I x1 + Wild Elephant x6), 543 keyed
## thumbnails, 18 footprint markers, and 8 unknown-id placeholders.
const SLICE_COUNTS := {
	"sprite": 7, "thumbnail": 543, "marker": 18, "placeholder": 8}
## The content-unknown placeholder ids with their placement multiplicities
## (the six distinct ids of `state.unresolved_ids`, eight placements).
const SLICE_PLACEHOLDER_IDS := [5000, 5001, 5004, 5005, 5007, 5007, 5007, 5008]
## The village's HUD strings: `str(state.value)` over its own payload.
const SLICE_HUD := {
	"gold": "62395", "wood": "96060", "steel": "94869", "oil": "97521",
	"cash": "42", "energy": "50", "mana": "0",
	"name": "Scarlet", "level": "33", "xp": "107694",
}
## The fresh save's placements whose img_name has no preserved thumbnail
## (documented in the town README section): 2 placements of item 928 and
## 7 placements of item 929 render as footprint markers.
const THUMBLESS_MARKER_IDS := [928, 928, 929, 929, 929, 929, 929, 929, 929]
## Minimum keyed-background fraction per thumbnail (probe evidence: the
## nine fresh thumbnails key between 19% and 52% of their pixels).
const MIN_KEYED_FRACTION := 0.15


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"content package loads: %s" % content.get("error"))
	var assets: Dictionary = registry.load_asset_registry()
	check(bool(assets.get("ok", false)),
		"asset registry loads: %s" % assets.get("error"))
	if not bool(content.get("ok", false)) or not bool(assets.get("ok", false)):
		return

	var payload: Variant = JSON.parse_string(
		FileAccess.get_file_as_bytes(
			Paths.repo_root().path_join(FIXTURE)).get_string_from_utf8())
	check(payload is Dictionary, "fresh fixture parses as JSON")
	if not (payload is Dictionary):
		return
	var parsed: Dictionary = TownState.parse(payload, registry)
	check(bool(parsed.get("ok", false)),
		"fresh fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]

	var scene: PackedScene = load("res://scenes/town.tscn")
	check(scene != null, "town scene loads")
	if scene == null:
		return
	var town: Node2D = scene.instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"town builds from the fresh state: %s" % built.get("error"))
	check_eq(town.view_state, "built", "view state is built")
	check(town.build_ok, "build_ok commits on a successful build")
	if not bool(built.get("ok", false)):
		town.free()
		return

	_check_built_view(town, state)
	_check_depth_and_determinism(town, state)
	_check_selection(town)
	town.free()
	_check_error_states(state)
	_check_slice(registry)


## Terrain provenance/geometry, object placement/metadata/visual
## hierarchy, camera bounds and focus, HUD display strings.
func _check_built_view(town: Node2D, state: Variant) -> void:
	var terrain: Variant = town.terrain
	check(terrain.texture != null, "terrain texture decoded from the jpg")
	check_eq(terrain.terrain_ref, "mapa1.jpg", "terrain reference recorded")
	check_eq(terrain.asset_status, "passthrough",
		"terrain asset status recorded")
	check_eq(terrain.image_size, Vector2i(701, 514),
		"terrain decoded at its authentic 701x514")
	check_eq(Vector2(terrain.position), Iso.world_rect().position,
		"terrain anchored at the world rect origin")
	check_eq(Vector2(terrain.size), Iso.world_rect().size,
		"terrain stretched over the whole world rect")
	check(terrain.mouse_filter == Control.MOUSE_FILTER_IGNORE,
		"terrain passes pointer input through")

	check_eq(town.objects.size(), 40, "all 40 placements render as objects")

	# Cells + ids + save order + footprints, as multisets against the
	# typed state (no assumption of unique cells). With every fresh id
	# resolved against content, footprint equality proves objects carry
	# content dimensions — never a texture-derived or placeholder size.
	check(state.unresolved_ids.is_empty(),
		"every fresh id resolved content (unresolved: %s)"
		% [state.unresolved_ids])
	var placement_cells: Array = []
	var placement_footprints: Array = []
	for placement in state.placements:
		placement_cells.append([
			placement.cell.y, placement.cell.x,
			placement.item, placement.order])
		placement_footprints.append([
			placement.cell.y, placement.cell.x,
			placement.footprint.x, placement.footprint.y])
	placement_cells.sort()
	placement_footprints.sort()
	var object_cells: Array = []
	var object_footprints: Array = []
	for object in town.objects:
		object_cells.append([
			object.cell.y, object.cell.x,
			object.legacy_id, object.save_order])
		object_footprints.append([
			object.cell.y, object.cell.x,
			object.footprint.x, object.footprint.y])
	object_cells.sort()
	object_footprints.sort()
	check_eq(object_cells, placement_cells,
		"every object renders its saved cell, id, and save order")
	check_eq(object_footprints, placement_footprints,
		"every object uses its content footprint (no texture-derived size)")

	# Visual hierarchy: 31 thumbnails + 9 markers, no sprites, no
	# placeholders in the fresh save; markers are exactly the placements
	# of the two thumbless ids; thumbnails are background-keyed.
	var counts: Dictionary = town.object_counts_by_source()
	check_eq(int(counts.get("thumbnail", 0)), 31,
		"31 placements choose the preserved thumbnail")
	check_eq(int(counts.get("marker", 0)), 9,
		"9 thumbless placements choose the footprint marker")
	check_eq(int(counts.get("sprite", 0)), 0,
		"no fresh placement has a converted package sprite")
	check_eq(int(counts.get("placeholder", 0)), 0,
		"no fresh placement is a content-unknown placeholder")
	var marker_ids: Array = []
	var unkeyed_thumbnails := 0
	var marker_children := 0
	for object in town.objects:
		if object.visual_source == TownVisuals.SOURCE_MARKER:
			marker_ids.append(object.legacy_id)
			marker_children += object.get_child_count()
		elif object.visual_source == TownVisuals.SOURCE_THUMBNAIL:
			if object.get_child_count() != 1 \
					or not (object.get_child(0) is Sprite2D):
				unkeyed_thumbnails += 1
				continue
			var thumb_image: Image = \
				(object.get_child(0) as Sprite2D).texture.get_image()
			var transparent := 0
			for y in range(thumb_image.get_height()):
				for x in range(thumb_image.get_width()):
					if thumb_image.get_pixel(x, y).a == 0.0:
						transparent += 1
			var fraction := float(transparent) / float(
				thumb_image.get_width() * thumb_image.get_height())
			if thumb_image.get_pixel(0, 0).a != 0.0 \
					or fraction < MIN_KEYED_FRACTION:
				unkeyed_thumbnails += 1
	marker_ids.sort()
	check_eq(marker_ids, THUMBLESS_MARKER_IDS,
		"markers are exactly the thumbless placements")
	check_eq(marker_children, 0,
		"markers draw their footprint instead of loading a node")
	check_eq(unkeyed_thumbnails, 0,
		"every thumbnail keeps its white corner keyed to transparency and "
		+ "keys at least %.0f%% of its pixels" % (MIN_KEYED_FRACTION * 100.0))

	# Camera: bounds committed over the world rect, focus framed on the
	# mean footprint center of the committed state.
	var camera: Variant = town.camera
	check(camera.has_world_bounds(), "camera world bounds are committed")
	check_eq(camera.world_bounds(), Iso.world_rect(),
		"camera bounds equal the projection world rect")
	check(camera.position != Vector2.ZERO,
		"camera is framed on the town, not the origin")
	var sum := Vector2.ZERO
	for placement in state.placements:
		var rect := Iso.footprint_rect(
			placement.cell, placement.footprint.x, placement.footprint.y)
		sum += rect.position + rect.size * 0.5
	var expected_focus := sum / float(state.placements.size())
	check(camera.position.distance_to(expected_focus) < 0.001,
		"camera focus equals the mean footprint center (%s vs %s)"
		% [camera.position, expected_focus])
	check(camera.zoom_factor() == 1.0 and camera.zoom == Vector2.ONE,
		"capture starts at zoom level 0, factor 1.0")

	# HUD: slot registered, every displayed string exactly str(state).
	check(town.ui.has_slot("hud"), "HUD slot registered on the UI foundation")
	check(town.hud() != null, "HUD attached to the slot")
	if town.hud() == null:
		return
	check_eq(town.hud().displayed_fields(), {
		"gold": "2000", "wood": "2000", "steel": "2000", "oil": "2000",
		"cash": "5", "energy": "50", "mana": "0",
		"name": "Warrior", "level": "1", "xp": "4",
	}, "HUD strings equal str(state.value) for every field")


## Depth order contract + rebuild determinism.
func _check_depth_and_determinism(town: Node2D, state: Variant) -> void:
	check(state.placements.size() == town.objects.size(),
		"object count still matches the state")
	var depth_regressions := 0
	var tie_regressions := 0
	var ties := 0
	for index in range(1, town.objects.size()):
		var before: Variant = town.objects[index - 1]
		var after: Variant = town.objects[index]
		var depth_before := Iso.depth_key(before.cell)
		var depth_after := Iso.depth_key(after.cell)
		if depth_after < depth_before:
			depth_regressions += 1
		if depth_after == depth_before:
			ties += 1
			if after.cell.y < before.cell.y \
					or (after.cell.y == before.cell.y
						and after.cell.x < before.cell.x) \
					or (after.cell.y == before.cell.y
						and after.cell.x == before.cell.x
						and after.save_order < before.save_order):
				tie_regressions += 1
	check_eq(depth_regressions, 0,
		"draw order is non-decreasing in isometric depth")
	check_eq(tie_regressions, 0,
		"equal-depth objects follow the documented tie-break "
		+ "(depth, y, x, save order); ties present: %d" % ties)

	var before_render: Array = []
	for object in town.objects:
		before_render.append([
			object.cell.y, object.cell.x,
			object.legacy_id, object.visual_source])
	var rebuilt: Dictionary = town.build()
	check(bool(rebuilt.get("ok", false)),
		"rebuild succeeds: %s" % rebuilt.get("error"))
	var after_render: Array = []
	for object in town.objects:
		after_render.append([
			object.cell.y, object.cell.x,
			object.legacy_id, object.visual_source])
	check_eq(after_render, before_render,
		"rebuild reproduces the identical ordered render list")


## Press-to-cell selection: select, clear, fail closed.
func _check_selection(town: Node2D) -> void:
	var target: Variant = town.objects[0]
	var center: Vector2 = target.footprint_rect().position \
		+ target.footprint_rect().size * 0.5
	var press: Dictionary = town.handle_pointer_press(center)
	check(bool(press.get("ok", false)),
		"in-grid press succeeds: %s" % press.get("error"))
	check_eq(int(press.get("legacy_id", -1)), target.legacy_id,
		"press selects the object under the cell")
	check_eq(town.selection_legacy_id(), target.legacy_id,
		"committed selection matches the press result")
	check(target.is_selected(), "selected object carries the highlight")

	var empty_cell := _find_uncovered_cell(town.objects)
	var empty_press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(empty_cell))
	check(bool(empty_press.get("ok", false)),
		"empty in-grid press succeeds: %s" % empty_press.get("error"))
	check(bool(empty_press.get("cleared", false)),
		"empty in-ground cell reports cleared")
	check_eq(town.selection_legacy_id(), -1,
		"empty ground clears the selection")
	check(not target.is_selected(), "cleared selection drops the highlight")

	var edge_press: Dictionary = town.handle_pointer_press(Vector2(-400, -400))
	check(bool(edge_press.get("ok", false)),
		"out-of-grid press succeeds: %s" % edge_press.get("error"))
	check(bool(edge_press.get("cleared", false)),
		"out-of-grid press clears the selection")

	var reselected: Dictionary = town.handle_pointer_press(center)
	check(bool(reselected.get("ok", false)) and not bool(
		reselected.get("cleared", true)), "reselect for the fail-closed pass")
	var nan_press: Dictionary = town.handle_pointer_press(Vector2(NAN, 0.0))
	check(not bool(nan_press.get("ok", true)),
		"non-finite press fails closed")
	check(nan_press.get("error", "").contains("non_finite"),
		"non-finite rejection names the condition: %s"
		% nan_press.get("error"))
	check_eq(town.selection_legacy_id(), target.legacy_id,
		"non-finite press leaves the selection unchanged")


## Whole-view failure: unloaded registry and null state both fail closed
## into the explicit error state with no partial render.
func _check_error_states(state: Variant) -> void:
	var scene: PackedScene = load("res://scenes/town.tscn")
	var failing: Node2D = scene.instantiate()
	root.add_child(failing)
	var unloaded: RegistryScript = RegistryScript.new()
	failing.set_registry(unloaded)
	var failed: Dictionary = failing.set_town_state(state)
	check(not bool(failed.get("ok", true)),
		"unloaded registry fails the build: %s" % failed.get("error"))
	check_eq(failing.view_state, "error",
		"view enters the explicit error state")
	check(failing.build_error.contains("terrain"),
		"error names the terrain failure: %s" % failing.build_error)
	check_eq(failing.objects.size(), 0, "no partial town is rendered")
	check(not failing.build_ok, "build_ok stays false")
	var label: Label = failing.get_node("Ui/ErrorLabel")
	check(label.visible, "the error label replaces the view")
	check(label.text.contains("terrain"),
		"error label names the failure: %s" % label.text)
	var rejected: Dictionary = failing.handle_pointer_press(Vector2.ZERO)
	check(not bool(rejected.get("ok", true)),
		"selection is rejected while the view is not built")
	failing.free()
	# The registry is a member reference, not a child of the town: the
	# orphan Node must be freed here or it leaks (the harness treats the
	# engine's exit-leak ERROR line as a script error).
	unloaded.free()

	var missing_state: Node2D = scene.instantiate()
	root.add_child(missing_state)
	var null_result: Dictionary = missing_state.set_town_state(null)
	check(not bool(null_result.get("ok", true)),
		"a null state fails the build")
	check(null_result.get("error", "").contains("state_missing"),
		"null-state rejection names the condition: %s"
		% null_result.get("error"))
	check_eq(missing_state.view_state, "error",
		"null state also enters the explicit error state")
	missing_state.free()


## Slice scene (change task 7.2, spec "Town slice verification scene"):
## the preserved village renders through the same components — House I
## and Wild Elephant as authentic converted sprites at their legacy
## cells, the content-unknown placements as placeholders, that save's
## HUD, depth order, bounds, and selection — with the input recorded by
## path + SHA-256 and left byte-identical.
func _check_slice(registry: Variant) -> void:
	var village_path := Paths.repo_root().path_join(SLICE_VILLAGE)
	var digest_before := Paths.file_sha256(village_path)
	check_eq(digest_before, SLICE_VILLAGE_SHA256,
		"the slice village matches the committed guard digest")
	var slice_scene: PackedScene = load("res://scenes/town_slice.tscn")
	check(slice_scene != null, "slice scene loads")
	if slice_scene == null:
		return
	var slice: Node2D = slice_scene.instantiate()
	root.add_child(slice)
	check_eq(str(slice.view_state), "built",
		"the slice view builds from the legacy village")
	if str(slice.view_state) != "built":
		info("slice build error: %s" % str(slice.build_error))
		slice.free()
		return
	check_eq(str(slice.input_path), SLICE_VILLAGE,
		"the slice records its input file")
	check_eq(str(slice.input_sha256), SLICE_VILLAGE_SHA256,
		"the slice records the input SHA-256")
	check_eq(slice.objects.size(), 576,
		"all 576 village placements render as objects")
	check_eq(slice.object_counts_by_source(), SLICE_COUNTS,
		"the visual hierarchy counts match the village")

	# Converted sprites: one House I + six Wild Elephant, each at its
	# legacy-saved cell with its content footprint and native frame.
	var house_cells: Array = []
	var elephant_cells: Array = []
	var unknown_cells: Array = []
	for placement in slice.state.placements:
		match int(placement.item):
			1:
				house_cells.append([placement.cell.y, placement.cell.x])
			933:
				elephant_cells.append([placement.cell.y, placement.cell.x])
			_:
				if not bool(placement.content_ok):
					unknown_cells.append([
						placement.cell.y, placement.cell.x,
						int(placement.item)])
	house_cells.sort()
	elephant_cells.sort()
	unknown_cells.sort()
	var house_objects: Array = []
	var elephant_objects: Array = []
	var placeholder_objects: Array = []
	var actual_house: Array = []
	var actual_elephant: Array = []
	var actual_unknown: Array = []
	for object in slice.objects:
		match int(object.legacy_id):
			1:
				house_objects.append(object)
				actual_house.append([object.cell.y, object.cell.x])
			933:
				elephant_objects.append(object)
				actual_elephant.append([object.cell.y, object.cell.x])
		if str(object.visual_source) == TownVisuals.SOURCE_PLACEHOLDER:
			placeholder_objects.append(object)
			actual_unknown.append([
				object.cell.y, object.cell.x, int(object.legacy_id)])
	actual_house.sort()
	actual_elephant.sort()
	actual_unknown.sort()
	check_eq(house_objects.size(), 1, "exactly one House I placement renders")
	check_eq(actual_house, house_cells,
		"House I renders at its legacy-saved cell")
	check_eq(elephant_objects.size(), 6,
		"exactly six Wild Elephant placements render")
	check_eq(actual_elephant, elephant_cells,
		"every Wild Elephant renders at its legacy-saved cell")
	check_eq(footprint_of(house_objects, 0), Vector2i(2, 2),
		"House I carries its content 2x2 footprint")
	for object in elephant_objects:
		check_eq(object.footprint, Vector2i(1, 1),
			"Wild Elephant carries its content 1x1 footprint")
	_check_slice_sprite(house_objects[0], Vector2i(216, 144), 1)
	for object in elephant_objects:
		_check_slice_sprite(object, Vector2i(171, 191), 933)

	# Placeholders: exactly the eight content-unknown placements, each on
	# its single saved cell with no child node (drawn as a labeled
	# footprint) — the town stays intact around them.
	check_eq(placeholder_objects.size(), 8,
		"the eight content-unknown placements render as placeholders")
	check_eq(actual_unknown, unknown_cells,
		"placeholders render at their legacy-saved cells")
	var placeholder_ids: Array = []
	for object in placeholder_objects:
		placeholder_ids.append(int(object.legacy_id))
		check_eq(object.footprint, Vector2i.ONE,
			"an unknown id occupies its single saved cell")
		check_eq(object.get_child_count(), 0,
			"a placeholder draws its footprint instead of loading art")
	placeholder_ids.sort()
	check_eq(placeholder_ids, SLICE_PLACEHOLDER_IDS,
		"placeholder ids are exactly the six content-unknown ids "
		+ "(eight placements)")

	# Depth order over the village (same non-decreasing contract).
	var depth_regressions := 0
	for index in range(1, slice.objects.size()):
		var before: Variant = slice.objects[index - 1]
		var after: Variant = slice.objects[index]
		if Iso.depth_key(after.cell) < Iso.depth_key(before.cell):
			depth_regressions += 1
	check_eq(depth_regressions, 0,
		"slice draw order is non-decreasing in isometric depth")

	# Bounds + selection + that save's HUD strings.
	var camera: Variant = slice.camera
	check(camera.has_world_bounds(), "slice camera bounds are committed")
	check_eq(camera.world_bounds(), Iso.world_rect(),
		"slice camera bounds equal the projection world rect")
	check_eq(slice.hud().displayed_fields(), SLICE_HUD,
		"the slice HUD displays that save's verbatim values")
	var house_press: Dictionary = slice.handle_pointer_press(
		Iso.grid_to_screen(Vector2i(house_cells[0][1], house_cells[0][0])))
	check(bool(house_press.get("ok", false)),
		"the House I press succeeds: %s" % house_press.get("error"))
	check_eq(int(house_press.get("legacy_id", -1)), 1,
		"the press selects House I (depth-topmost under its cell)")
	check_eq(slice.selection_legacy_id(), 1,
		"the committed slice selection is House I")
	var clear_press: Dictionary = slice.handle_pointer_press(
		Vector2(-800, -800))
	check(bool(clear_press.get("cleared", false)),
		"an out-of-grid press clears the slice selection")
	check_eq(slice.selection_legacy_id(), -1,
		"the cleared slice selection is empty")
	slice.free()
	check_eq(Paths.file_sha256(village_path), digest_before,
		"the village file is byte-identical after the slice render")


## One converted-sprite object: native frame texture (never scaled),
## single container bottom-center anchored over the content footprint,
## no degradation to a marker.
func _check_slice_sprite(object: Variant, frame: Vector2i,
		legacy_id: int) -> void:
	check_eq(str(object.visual_source), TownVisuals.SOURCE_SPRITE,
		"id %d renders as a converted package sprite" % legacy_id)
	check_eq(str(object.visual_error), "",
		"id %d sprite builds without degrading" % legacy_id)
	check_eq(object.get_child_count(), 1,
		"id %d sprite holds exactly one container" % legacy_id)
	if object.get_child_count() != 1:
		return
	var container: Node = object.get_child(0)
	check(container is Node2D and container.get_child_count() >= 1,
		"id %d container holds composited shape sprites" % legacy_id)
	var union := Rect2()
	for shape in container.get_children():
		if shape is Sprite2D:
			var shape_rect := Rect2(Vector2(shape.position),
				(shape.texture as Texture2D).get_size())
			union = shape_rect if union.size == Vector2.ZERO \
				else union.merge(shape_rect)
	check_eq(union.size, Vector2(frame),
		"id %d native frame is %dx%d (never scaled to the footprint)"
		% [legacy_id, frame.x, frame.y])
	var rect: Rect2 = object.footprint_rect()
	check_eq(Vector2(container.position),
		Vector2((rect.size.x - frame.x) / 2.0, rect.size.y - frame.y),
		"id %d sprite is bottom-center anchored over its footprint"
		% legacy_id)


## Footprint of the object at `index` (guards the index before use).
static func footprint_of(objects: Array, index: int) -> Vector2i:
	if index >= objects.size():
		return Vector2i(-1, -1)
	return (objects[index] as Variant).footprint


## The first cell in 0..99 no object footprint covers (deterministic for
## a committed fixture; used as genuinely empty ground).
func _find_uncovered_cell(objects: Array) -> Vector2i:
	for y in range(100):
		for x in range(100):
			var candidate := Vector2i(x, y)
			var covered := false
			for object in objects:
				if object.contains_cell(candidate):
					covered = true
					break
			if not covered:
				return candidate
	return Vector2i(-1, -1)
