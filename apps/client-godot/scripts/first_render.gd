extends Control
## First-render verification scene.
##
## Builds the house and elephant frame-1 output from the read-only
## conversion-v1 packages side by side on a neutral background, then — in a
## windowed session — captures the viewport to the committed evidence PNG and
## quits. Headless sessions only build the scene so boot smoke checks and the
## scene-build test can inspect it without a display.

const Paths = preload("res://scripts/package_paths.gd")
const Loader = preload("res://scripts/package_loader.gd")
const Layout = preload("res://scripts/layout.gd")
const Verification = preload("res://scripts/verification.gd")

## True when every entity resolved and every node was built.
var build_ok := false
## Failure reason when build_ok is false.
var build_error := ""
## Per-entity build records: label, size_px, draw positions, oracle results.
var entity_records: Array = []


func _ready() -> void:
	var build := _build_scene()
	build_ok = bool(build.get("ok", false))
	if not build_ok:
		build_error = str(build.get("error", "unknown build failure"))
		push_error("[first-render] " + build_error)
		if DisplayServer.get_name() != "headless":
			get_tree().quit(1)
		return
	entity_records = build["records"]
	if DisplayServer.get_name() == "headless":
		# Boot smoke (--quit) and the headless scene-build test own the exit
		# code in headless mode; the scene only exposes build_ok/build_error.
		return
	await _capture_and_quit()


func _build_scene() -> Dictionary:
	var records: Array = []
	var textures: Array = []  # [{image, pos, label}]
	for package_dir in Paths.PACKAGE_DIRS:
		var package := Loader.load_package(str(package_dir))
		if not package.get("ok", false):
			return {"ok": false, "error": package.get("error", "")}
		var resolved := Loader.resolve_frame_1(package)
		if not resolved.get("ok", false):
			return {"ok": false, "error": resolved.get("error", "")}
		var size_px: Vector2i = resolved["size_px"]
		textures.append({"label": str(package_dir), "size_px": size_px,
			"resolved": resolved})

	var anchors := Layout.anchors_for([
		textures[0]["size_px"], textures[1]["size_px"]])
	for i in textures.size():
		var anchor: Vector2i = anchors[i]
		var entry: Dictionary = textures[i]
		var resolved: Dictionary = entry["resolved"]
		var draw: Array = resolved["draw"]
		var records_for_shapes: Array = []
		for shape_index in resolved["shapes"].size():
			var shape: Dictionary = resolved["shapes"][shape_index]
			var draw_entry: Dictionary = draw[shape_index]
			var composite := Loader.composite_bitmap(str(shape["jpg_path"]),
				str(shape["alpha_path"]))
			if not composite.get("ok", false):
				return {"ok": false, "error": composite.get("error", "")}
			var image: Image = composite["image"]
			var relative: Vector2i = draw_entry["pos"]
			var position := Vector2(anchor.x + relative.x,
				anchor.y + relative.y)
			var texture_rect := TextureRect.new()
			texture_rect.texture = ImageTexture.create_from_image(image)
			texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			texture_rect.position = position
			texture_rect.size = Vector2(image.get_width(), image.get_height())
			add_child(texture_rect)
			records_for_shapes.append({
				"character_id": shape["character_id"],
				"bitmap_id": shape["bitmap_id"],
				"position": position,
				"size": Vector2(image.get_width(), image.get_height()),
				"bounds_px": Vector2(shape["rect"].size.x,
					shape["rect"].size.y),
				"oracle": shape["oracle"],
				"matrix": shape["matrix"],
				"extent_twips": shape["extent_twips"],
				"bounds": shape["bounds"],
			})
		records.append({
			"label": entry["label"],
			"kind": resolved["kind"],
			"legacy_id": resolved["legacy_id"],
			"size_px": entry["size_px"],
			"anchor": anchor,
			"oracle_ok": resolved["oracle_ok"],
			"shapes": records_for_shapes,
		})

	var background := ColorRect.new()
	background.color = Layout.BACKGROUND_COLOR
	background.position = Vector2.ZERO
	background.size = Vector2(Layout.CANVAS_SIZE)
	add_child(background)
	move_child(background, 0)
	return {"ok": true, "records": records}


func _capture_and_quit() -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null:
		push_error("[first-render] viewport capture returned no image")
		get_tree().quit(1)
		return
	if image.get_size() != Layout.CANVAS_SIZE:
		push_error("[first-render] capture size %s does not match canvas %s"
			% [image.get_size(), Layout.CANVAS_SIZE])
		get_tree().quit(1)
		return
	var directory := Paths.project_dir().path_join("evidence/first-render")
	var mkdir_error := DirAccess.make_dir_recursive_absolute(directory)
	if mkdir_error != OK and not DirAccess.dir_exists_absolute(directory):
		push_error("[first-render] cannot create evidence directory: %s"
			% directory)
		get_tree().quit(1)
		return
	var save_error := image.save_png(Paths.capture_png_path())
	if save_error != OK:
		push_error("[first-render] cannot write capture: %s (error %s)"
			% [Paths.capture_png_path(), save_error])
		get_tree().quit(1)
		return
	print("[first-render] capture written: %s (%sx%s)"
		% [Paths.capture_png_path(), image.get_width(), image.get_height()])
	# Design D6: one run = render -> capture -> compare -> report -> exit.
	var result := Verification.run(Paths.capture_png_path(),
		Paths.report_path(), "capture", false)
	get_tree().quit(int(result.get("exit_code", 1)))
