extends "res://tests/test_base.gd"
## Headless scene-build test (OpenSpec task 3.1).
##
## Instantiates the verification scene without a display and asserts that
## both packages build, that every node sits at the layout anchor with the
## authentic package bounds, and that each texture carries the authentic
## bitmap dimensions.

const Loader = preload("res://scripts/package_loader.gd")
const Layout = preload("res://scripts/layout.gd")

const HOUSE_DIR := "assets/converted/buildings/0001_house_1_m"
const ELEPHANT_DIR := "assets/converted/units/10033_wild_elephant"

## Authentic frame-1 sizes in pixels (bounds decoded by the loader).
const HOUSE_SIZE := Vector2i(216, 144)
const ELEPHANT_SIZE := Vector2i(171, 191)


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return

	var digests_before := _digests()

	var packed := load("res://scenes/first_render.tscn")
	check(packed != null, "verification scene loads")
	if packed == null:
		return
	var scene: Node = packed.instantiate()
	check(scene != null, "verification scene instantiates")
	if scene == null:
		return
	root.add_child(scene)

	check("build_ok" in scene, "scene exposes its build status")
	check(bool(scene.build_ok),
		"scene builds both packages: %s" % str(scene.build_error))
	if not bool(scene.build_ok):
		root.remove_child(scene)
		scene.free()
		return

	var records: Array = scene.entity_records
	check_eq(records.size(), 2, "both entities were built")
	if records.size() == 2:
		var anchors := Layout.anchors_for([HOUSE_SIZE, ELEPHANT_SIZE])
		_check_entity(records[0], HOUSE_DIR, HOUSE_SIZE, anchors[0])
		_check_entity(records[1], ELEPHANT_DIR, ELEPHANT_SIZE, anchors[1])

	_check_nodes(scene, records)
	_check_background(scene)

	root.remove_child(scene)
	scene.free()

	check_eq(_digests(), digests_before,
		"package directory digests unchanged by the scene build")


func _check_entity(record: Dictionary, label: String,
		expected_size: Vector2i, anchor: Vector2i) -> void:
	check_eq(record["label"], label, "%s built" % label)
	check_eq(record["size_px"], expected_size,
		"%s authentic frame-1 size" % label)
	check(bool(record["oracle_ok"]), "%s bounds-to-bitmap oracle holds"
		% label)
	check_eq(record["anchor"], anchor, "%s layout anchor" % label)
	check_eq((record["shapes"] as Array).size(), 1,
		"%s renders one shape" % label)


func _check_nodes(scene: Node, records: Array) -> void:
	var texture_rects: Array = []
	var background: ColorRect = null
	for child in scene.get_children():
		if child is ColorRect:
			background = child
		elif child is TextureRect:
			texture_rects.append(child)
	check_eq(texture_rects.size(), 2,
		"exactly one texture node per resolved shape")
	check(background != null, "neutral background node exists")

	for i in texture_rects.size():
		var rect: TextureRect = texture_rects[i]
		var record: Dictionary = records[i]
		check(rect.texture != null, "entity %s has a texture" % i)
		if rect.texture == null:
			continue
		var texture_size := Vector2i(rect.texture.get_width(),
			rect.texture.get_height())
		check_eq(texture_size, Vector2i(record["size_px"]),
			"entity %s texture has the authentic bitmap dimensions" % i)
		check_eq(Vector2i(rect.size), Vector2i(record["size_px"]),
			"entity %s node bounds match the package bounds" % i)
		check_eq(Vector2i(rect.position), Vector2i(record["anchor"]),
			"entity %s sits at its layout anchor" % i)
		check_eq(rect.texture_filter,
			CanvasItem.TEXTURE_FILTER_NEAREST,
			"entity %s uses nearest-neighbour sampling" % i)
		check_eq(rect.expand_mode, TextureRect.EXPAND_IGNORE_SIZE,
			"entity %s texture is not resized by its container" % i)
		check(rect.clip_contents == false,
			"entity %s is not clipped" % i)


func _check_background(scene: Node) -> void:
	for child in scene.get_children():
		if child is ColorRect:
			check_eq(child.position, Vector2.ZERO,
				"background covers the canvas origin")
			check_eq(Vector2i(child.size), Layout.CANVAS_SIZE,
				"background covers the canvas size")
			check_eq(child.color, Layout.BACKGROUND_COLOR,
				"background is the neutral colour")
			check_eq(child.get_index(), 0,
				"background is drawn behind the entities")
			return
	fail("no background node found")


func _digests() -> Dictionary:
	var out := {}
	for package_dir in Paths.PACKAGE_DIRS:
		var digest := Paths.directory_digest(
			Paths.package_dir(str(package_dir)))
		out[str(package_dir)] = str(digest.get("sha256", "ERROR"))
	return out
