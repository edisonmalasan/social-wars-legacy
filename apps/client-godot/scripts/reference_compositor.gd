extends RefCounted
## Independent CPU reference compositor (design D6).
##
## The reference is built from the same read-only source bitmaps as the
## rendered scene, but through a separate code path: this script performs its
## own file reads, its own JPEG/PNG decodes and its own straight-alpha
## over-blend loop, and never calls `PackageLoader.composite_bitmap`. A
## premultiplication or channel-order bug in the render path therefore shows
## up as a metric failure instead of being copied into the reference.
##
## Frame-1 resolution itself is shared with the loader on purpose: what is
## being compared is the *rendering*, while the placement/fill chain is
## separately covered by the loader tests and the bounds-to-bitmap oracle.

const Paths = preload("res://scripts/package_paths.gd")
const Loader = preload("res://scripts/package_loader.gd")
const Layout = preload("res://scripts/layout.gd")

## Reference builder identity recorded in the report.
const BUILDER_ID := "reference-compositor/v1"


## Builds the full-canvas reference image.
##
## Returns {"ok"} or {"ok": false, "error"}; on success also "image",
## "entities" (one record per rendered entity) and "builder".
static func build() -> Dictionary:
	var canvas := Image.create(Layout.CANVAS_SIZE.x, Layout.CANVAS_SIZE.y,
		false, Image.FORMAT_RGBA8)
	canvas.fill(Layout.BACKGROUND_COLOR)

	var resolved_entities: Array = []
	for package_dir in Paths.PACKAGE_DIRS:
		var package := Loader.load_package(str(package_dir))
		if not package.get("ok", false):
			return _error(package.get("error", ""))
		var resolved := Loader.resolve_frame_1(package)
		if not resolved.get("ok", false):
			return _error(resolved.get("error", ""))
		resolved_entities.append(resolved)
	if resolved_entities.size() != 2:
		return _error("expected exactly two entities, got %s"
			% resolved_entities.size())

	var anchors := Layout.anchors_for([
		resolved_entities[0]["size_px"], resolved_entities[1]["size_px"]])
	var entities: Array = []
	for i in resolved_entities.size():
		var resolved: Dictionary = resolved_entities[i]
		var anchor: Vector2i = anchors[i]
		var entity_records: Array = []
		for shape_index in (resolved["shapes"] as Array).size():
			var shape: Dictionary = resolved["shapes"][shape_index]
			var draw: Dictionary = resolved["draw"][shape_index]
			# Independent decode: read and decode the pair here rather than
			# reusing the loader's compositor.
			var colour := _decode(str(shape["jpg_path"]))
			if not colour.get("ok", false):
				return _error(colour.get("error", ""))
			var alpha := _decode(str(shape["alpha_path"]))
			if not alpha.get("ok", false):
				return _error(alpha.get("error", ""))
			var colour_image: Image = colour["image"]
			var alpha_image: Image = alpha["image"]
			if colour_image.get_width() != alpha_image.get_width() \
					or colour_image.get_height() != alpha_image.get_height():
				return _error("alpha dimension mismatch for %s"
					% shape["jpg_path"])
			colour_image.convert(Image.FORMAT_RGBA8)
			alpha_image.convert(Image.FORMAT_RGBA8)
			var offset: Vector2i = anchor + draw["pos"]
			if not _over_blend(canvas, colour_image, alpha_image, offset):
				return _error("entity quad at %s falls outside the canvas"
					% offset)
			entity_records.append({
				"character_id": int(shape["character_id"]),
				"bitmap_id": int(shape["bitmap_id"]),
				"anchor": offset,
				"size": Vector2i(colour_image.get_width(),
					colour_image.get_height()),
				"jpg_path": str(shape["jpg_path"]),
				"jpg_sha256": str(shape["jpg_sha256"]),
				"alpha_path": str(shape["alpha_path"]),
				"alpha_sha256": str(shape["alpha_sha256"]),
				"oracle": shape["oracle"],
			})
		entities.append({
			"label": str(resolved["label"]),
			"kind": str(resolved["kind"]),
			"legacy_id": str(resolved["legacy_id"]),
			"anchor": anchor,
			"size_px": resolved["size_px"],
			"oracle_ok": bool(resolved["oracle_ok"]),
			"shapes": entity_records,
		})
	return {"ok": true, "builder": BUILDER_ID, "image": canvas,
		"entities": entities}


## Straight-alpha source-over of one quad onto the canvas.
static func _over_blend(canvas: Image, colour: Image, alpha: Image,
		offset: Vector2i) -> bool:
	var width := colour.get_width()
	var height := colour.get_height()
	if offset.x < 0 or offset.y < 0 \
			or offset.x + width > canvas.get_width() \
			or offset.y + height > canvas.get_height():
		return false
	for y in height:
		for x in width:
			var source := colour.get_pixel(x, y)
			# The alpha plane is a grayscale PNG; its luminance carries the
			# coverage value.
			source.a = alpha.get_pixel(x, y).r
			if source.a <= 0.0:
				continue
			var destination := canvas.get_pixel(offset.x + x, offset.y + y)
			var out_a := source.a + destination.a * (1.0 - source.a)
			if out_a <= 0.0:
				continue
			var out := Color(
				(source.r * source.a
					+ destination.r * destination.a * (1.0 - source.a))
					/ out_a,
				(source.g * source.a
					+ destination.g * destination.a * (1.0 - source.a))
					/ out_a,
				(source.b * source.a
					+ destination.b * destination.a * (1.0 - source.a))
					/ out_a,
				out_a)
			canvas.set_pixel(offset.x + x, offset.y + y, out)
	return true


## Own decode path: bytes in, Image out (no reuse of the loader's helper).
static func _decode(path: String) -> Dictionary:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false, "error": "reference cannot open " + path}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	var image := Image.new()
	var result: Error
	if path.to_lower().ends_with(".jpg") or path.to_lower().ends_with(
			".jpeg"):
		result = image.load_jpg_from_buffer(bytes)
	elif path.to_lower().ends_with(".png"):
		result = image.load_png_from_buffer(bytes)
	else:
		return {"ok": false,
			"error": "reference cannot decode extension: " + path}
	if result != OK or image.is_empty():
		return {"ok": false, "error": "reference failed to decode " + path}
	return {"ok": true, "image": image}


static func _error(message: String) -> Dictionary:
	return {"ok": false, "error": "[reference] " + str(message)}
