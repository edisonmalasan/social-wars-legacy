extends RefCounted
## Town visual hierarchy (OpenSpec `godot-town-rendering` "Town object
## rendering", design D4).
##
## Maps a resolved placement to exactly one visual, in the fixed
## hierarchy the spec commits:
##   1. authentic converted package sprite when the item's asset status
##      is `converted` (native sprite bounds, never scaled);
##   2. else the preserved legacy thumbnail for its `img_name`, with the
##      white background keyed to transparency at load (corner-sampled
##      color key with tolerance — a documented, tested presentation
##      technique pending further conversions);
##   3. else an explicit footprint marker; a placement whose legacy id is
##      absent from content becomes a labeled placeholder instead.
##
## This module owns the texture caches so 576 village placements sharing
## ~80 images load each image once, and every load is fail-closed: an
## unreadable thumbnail or unloadable package degrades to the marker with
## the reason recorded on the object — never a crash, never a skipped
## placement. Footprint dimensions never come from texture dimensions
## (AGENTS rule): they come from content `width`/`height` on the
## placement, and this module only supplies appearance.

const Paths = preload("res://scripts/package_paths.gd")
const Loader = preload("res://scripts/package_loader.gd")

## Visual-source vocabulary (the evidence report counts by these).
const SOURCE_SPRITE := "sprite"
const SOURCE_THUMBNAIL := "thumbnail"
const SOURCE_MARKER := "marker"
const SOURCE_PLACEHOLDER := "placeholder"

## Corner-key tolerance as a per-channel distance in 0..1 (~40/255):
## JPEG compression moves the near-white background by a few levels, and
## the key must absorb that without eating the item's edges (design D4;
## fringing on JPEG edges is an accepted, recorded risk).
const COLOR_KEY_TOLERANCE := 0.16

## Thumbnail cache: absolute path -> {ok, texture, error}.
var _thumb_cache := {}
## Package cache: absolute package dir -> {ok, size_px, rects, error}.
var _package_cache := {}


## Chooses the visual for one placement. Returns `{ok, source, label,
## path}` — `path` is the package dir for a sprite, the absolute jpg for
## a thumbnail, empty for marker/placeholder. Never fails: the hierarchy
## always has a bottom rung.
func resolve(placement: Variant, registry: Variant) -> Dictionary:
	if not bool(placement.content_ok):
		return {"ok": true, "source": SOURCE_PLACEHOLDER,
			"label": "unknown id %d" % int(placement.item), "path": ""}
	if str(placement.asset_status) == "converted":
		var asset: Dictionary = registry.resolve_asset(
			"item_sprites", str(placement.img_name))
		if bool(asset.get("found", false)) \
				and asset.get("entry") is Dictionary:
			var runtime := str(
				(asset.get("entry") as Dictionary).get("runtime", ""))
			if not runtime.is_empty():
				# The registry's converted runtime path is the package
				# directory (see asset_ids.json: assets/converted/...).
				if DirAccess.dir_exists_absolute(
						Paths.repo_root().path_join(runtime)):
					return {"ok": true, "source": SOURCE_SPRITE,
						"label": str(placement.name), "path": runtime}
	var thumb := thumb_path_for(str(placement.img_name))
	if not thumb.is_empty() and FileAccess.file_exists(thumb):
		return {"ok": true, "source": SOURCE_THUMBNAIL,
			"label": str(placement.name), "path": thumb}
	return {"ok": true, "source": SOURCE_MARKER,
		"label": str(placement.name), "path": ""}


## Absolute path of the preserved thumbnail for an img_name ("" when the
## item carries no img_name).
static func thumb_path_for(img_name: String) -> String:
	if img_name.is_empty():
		return ""
	return Paths.repo_root().path_join("assets/thumbs/%s.jpg" % img_name)


## The decoded, background-keyed thumbnail texture for `path`, cached.
## Fail-closed: an unreadable or undecodable thumbnail returns {ok:false}
## so the caller degrades to the marker (design D4).
func thumbnail_texture(path: String) -> Dictionary:
	if _thumb_cache.has(path):
		return _thumb_cache[path]
	var result := {"ok": false, "texture": null, "error": ""}
	if not FileAccess.file_exists(path):
		result["error"] = "thumbnail is missing: " + path
	else:
		var bytes := FileAccess.get_file_as_bytes(path)
		var image := Image.new()
		if bytes.is_empty():
			result["error"] = "thumbnail is unreadable: " + path
		elif image.load_jpg_from_buffer(bytes) != OK:
			result["error"] = "thumbnail decode failed: " + path
		else:
			key_out_background(image)
			result["ok"] = true
			result["texture"] = ImageTexture.create_from_image(image)
			result["error"] = ""
	_thumb_cache[path] = result
	return result


## The frame-1 package visual (native-size composited shape rects),
## cached: {ok, size_px: Vector2i, rects: [{image, pos}], error}.
func package_visual(package_dir: String) -> Dictionary:
	if _package_cache.has(package_dir):
		return _package_cache[package_dir]
	var result := {
		"ok": false, "size_px": Vector2i.ZERO, "rects": [], "error": ""}
	var package: Dictionary = Loader.load_package(package_dir)
	if not bool(package.get("ok", false)):
		result["error"] = str(package.get("error", "package load failed"))
	else:
		var resolved: Dictionary = Loader.resolve_frame_1(package)
		if not bool(resolved.get("ok", false)):
			result["error"] = str(
				resolved.get("error", "frame-1 resolution failed"))
		else:
			var rects: Array = []
			var shapes: Array = resolved["shapes"]
			var draw: Array = resolved["draw"]
			var failure := ""
			for shape_index in range(shapes.size()):
				var shape: Dictionary = shapes[shape_index]
				var draw_entry: Dictionary = draw[shape_index]
				var composite: Dictionary = Loader.composite_bitmap(
					str(shape["jpg_path"]), str(shape["alpha_path"]))
				if not bool(composite.get("ok", false)):
					failure = str(composite.get("error",
						"bitmap composite failed"))
					break
				rects.append({
					"image": composite["image"],
					"pos": draw_entry["pos"],
				})
			if failure.is_empty():
				result["ok"] = true
				result["size_px"] = resolved["size_px"]
				result["rects"] = rects
				result["error"] = ""
			else:
				result["error"] = failure
	_package_cache[package_dir] = result
	return result


## Keys the white thumbnail background to transparency in place: the
## background is sampled from the four corners — the luminance-brightest
## corner wins, because the preserved thumbnails are a white-background
## corpus and artwork may touch a corner (averaging would let that art
## sample skew the background away from white, leaving a white halo;
## probe evidence: two fresh-save thumbs have art corners, all nine have
## a white top-left corner). Every pixel within COLOR_KEY_TOLERANCE of
## the sampled background on every channel becomes fully transparent.
## Deterministic, applied once at load (design D4).
static func key_out_background(image: Image) -> void:
	image.convert(Image.FORMAT_RGBA8)
	var width := image.get_width()
	var height := image.get_height()
	if width <= 0 or height <= 0:
		return
	var corners := [
		image.get_pixel(0, 0),
		image.get_pixel(width - 1, 0),
		image.get_pixel(0, height - 1),
		image.get_pixel(width - 1, height - 1),
	]
	var background: Color = corners[0]
	var best: float = (corners[0] as Color).get_luminance()
	for index in range(1, 4):
		var luminance: float = (corners[index] as Color).get_luminance()
		if luminance > best:
			best = luminance
			background = corners[index]
	for y in range(height):
		for x in range(width):
			var pixel := image.get_pixel(x, y)
			if absf(pixel.r - background.r) <= COLOR_KEY_TOLERANCE \
					and absf(pixel.g - background.g) <= COLOR_KEY_TOLERANCE \
					and absf(pixel.b - background.b) <= COLOR_KEY_TOLERANCE:
				pixel.a = 0.0
				image.set_pixel(x, y, pixel)
