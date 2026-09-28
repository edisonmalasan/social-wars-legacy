extends TextureRect
## Legacy terrain ground layer (OpenSpec `godot-town-rendering` "Terrain
## rendering", design D3).
##
## Resolves the island image through ContentRegistry asset resolution over
## the legacy image corpus, loads the preserved bytes at runtime (never an
## imported Godot resource, never a rewritten source), and anchors itself
## to the projection's world rectangle so ground, objects, selection, and
## camera share one coordinate space. The texture is stretched to that
## rectangle; the stretch factors are recorded provisional presentation
## facts (design D2).
##
## Fail-closed (spec "Fail visibly without terrain"): an unresolvable,
## missing, or undecodable terrain returns `{ok, false}` with an error
## naming the condition — the town scene then enters its explicit error
## state instead of drawing a blank ground beneath a claimed render.

const Paths = preload("res://scripts/package_paths.gd")
const Iso = preload("res://scripts/town/iso.gd")
const RegistryScript = preload("res://scripts/content_registry.gd")

## Content reference of the island terrain image (the only island image
## in the legacy corpus: `mapa1.jpg`, 701x514).
const TERRAIN_REF := "mapa1.jpg"
## Asset kind resolved over the legacy image corpus.
const TERRAIN_KIND := "images"

## Provenance recorded by a successful build (evidence report fields).
var terrain_ref := ""
var asset_status := ""
var runtime_path := ""
var image_size := Vector2i.ZERO


## Resolves, decodes, and places the terrain. Returns `{ok, error}`; on
## failure nothing is drawn and the caller enters the town error state.
func build(registry: RegistryScript) -> Dictionary:
	if registry == null:
		return _reject("content registry is unavailable")
	var asset: Dictionary = registry.resolve_asset(TERRAIN_KIND, TERRAIN_REF)
	if not bool(asset.get("found", false)):
		return _reject(str(asset.get("error", "terrain asset not found")))
	var entry: Variant = asset.get("entry")
	if not (entry is Dictionary):
		return _reject("terrain asset entry is malformed")
	var runtime := str((entry as Dictionary).get("runtime", ""))
	if runtime.is_empty():
		return _reject("terrain asset entry has no runtime path")
	var abs_path := Paths.repo_root().path_join(runtime)
	if not FileAccess.file_exists(abs_path):
		return _reject("terrain bytes are missing: " + abs_path)
	var bytes := FileAccess.get_file_as_bytes(abs_path)
	if bytes.is_empty():
		return _reject("terrain bytes are unreadable: " + abs_path)
	var image := Image.new()
	var load_error := image.load_jpg_from_buffer(bytes)
	if load_error != OK:
		return _reject("terrain decode failed (error %s): %s"
			% [load_error, abs_path])
	image.convert(Image.FORMAT_RGBA8)
	texture = ImageTexture.create_from_image(image)
	texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_SCALE
	# One coordinate space: the ground spans exactly the projection's
	# world rectangle (design D2/D3).
	position = Iso.world_rect().position
	size = Iso.world_rect().size
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	terrain_ref = TERRAIN_REF
	asset_status = str((entry as Dictionary).get("status", ""))
	runtime_path = runtime
	image_size = Vector2i(image.get_width(), image.get_height())
	return {"ok": true, "error": ""}


## The house rejection envelope: names the violated condition, leaves the
## view unclaimed (the caller maps this to the explicit town error state).
func _reject(reason: String) -> Dictionary:
	return {"ok": false, "error": "[town] terrain rejected: " + reason}
