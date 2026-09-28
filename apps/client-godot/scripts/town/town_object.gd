extends Node2D
## Per-placement town object (OpenSpec `godot-town-rendering` "Town object
## rendering" / "Isometric depth sorting", design D4/D8).
##
## One node per saved placement, carrying the committed metadata the
## spec requires to be reachable for tests, HUD, and selection: legacy
## id, display name, grid cell, content footprint, chosen visual source,
## save order. The node draws itself at the projection of its saved cell
## (position = the footprint's world rect), builds its visual child from
## the hierarchy module, and draws the footprint diamond for
## markers/placeholders plus the selection highlight.
##
## Fail-closed per object: a visual that cannot be built (unreadable
## thumbnail, unloadable package) degrades to the labeled marker with the
## reason recorded in `visual_error` — the object still exists at its
## saved cell, the rest of the town is intact, nothing crashes (spec:
## "Placeholder for an unknown legacy id", design D4/Risk 3).

const Iso = preload("res://scripts/town/iso.gd")
const TownVisuals = preload("res://scripts/town/town_visuals.gd")

## Provisional presentation colors (no authentic legacy HUD/selection
## visual has been captured — recorded as provisional, design
## Non-Goals/D4).
const MARKER_COLOR := Color(0.05, 0.05, 0.05, 0.9)
const MARKER_WIDTH := 2.0
const HIGHLIGHT_FILL := Color(1.0, 0.92, 0.35, 0.28)
const HIGHLIGHT_COLOR := Color(1.0, 0.84, 0.2, 1.0)
const HIGHLIGHT_WIDTH := 2.0
const LABEL_FONT_SIZE := 12

## Committed metadata (spec: "reachable for tests, HUD, and selection").
var legacy_id := 0
var display_name := ""
var cell := Vector2i.ZERO
var footprint := Vector2i.ONE
var visual_source := ""
var save_order := 0
## Why the intended visual failed when the object degraded to a marker.
var visual_error := ""
## The parsed placement this object renders (read-only by contract).
var placement: Variant = null

## The footprint's world rect (node-local origin).
var _footprint_rect := Rect2()
## Selection highlight state (committed by the town view).
var _selected := false


## Builds the object's visual from a resolved hierarchy result.
## Returns `{ok, error}`; metadata is set even on visual degradation.
func setup(placement_value: Variant, visuals: TownVisuals,
		visual: Dictionary) -> Dictionary:
	placement = placement_value
	legacy_id = int(placement.item)
	display_name = str(placement.name)
	cell = placement.cell
	# Footprint comes from content width/height only; an unknown id has
	# no content footprint and occupies its single saved cell.
	if bool(placement.content_ok):
		footprint = placement.footprint
	else:
		footprint = Vector2i.ONE
	save_order = int(placement.order)
	visual_source = str(visual.get("source", TownVisuals.SOURCE_MARKER))
	_footprint_rect = Iso.footprint_rect(cell, footprint.x, footprint.y)
	position = _footprint_rect.position
	match visual_source:
		TownVisuals.SOURCE_SPRITE:
			_build_sprite(visuals, str(visual.get("path", "")))
		TownVisuals.SOURCE_THUMBNAIL:
			_build_thumbnail(visuals, str(visual.get("path", "")))
		_:
			pass  # marker/placeholder: drawn in _draw(), no child node.
	queue_redraw()
	return {"ok": true, "error": visual_error}


## True when the content footprint covers the given cell (integer cell
## ranges — cheap, exact hit testing per design D8).
func contains_cell(candidate: Vector2i) -> bool:
	return (candidate.x >= cell.x and candidate.x < cell.x + footprint.x
		and candidate.y >= cell.y and candidate.y < cell.y + footprint.y)


## Commits the selection highlight (true) or clears it (false).
func set_selected(selected: bool) -> void:
	if _selected == selected:
		return
	_selected = selected
	queue_redraw()


## True while this object is the committed selection.
func is_selected() -> bool:
	return _selected


## The footprint's world rect (for tests and the HUD/selection layer).
func footprint_rect() -> Rect2:
	return _footprint_rect


## Authentic converted package sprite at native bounds (never scaled):
## frame shapes composite into sprite children of a container positioned
## so the frame sits centered over the footprint, bottom-aligned (the
## overhang beyond the footprint is accepted provisional presentation,
## design D2/D4).
func _build_sprite(visuals: TownVisuals, package_dir: String) -> void:
	var built: Dictionary = visuals.package_visual(package_dir)
	if not bool(built.get("ok", false)):
		_degrade_to_marker("sprite: " + str(built.get("error", "")))
		return
	var size_px: Vector2i = built["size_px"]
	var container := Node2D.new()
	container.position = Vector2(
		(_footprint_rect.size.x - size_px.x) / 2.0,
		_footprint_rect.size.y - size_px.y)
	for entry in (built["rects"] as Array):
		var sprite := Sprite2D.new()
		sprite.centered = false
		sprite.texture = ImageTexture.create_from_image(
			entry["image"] as Image)
		sprite.position = Vector2(entry["pos"])
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		container.add_child(sprite)
	add_child(container)


## Preserved legacy thumbnail scaled to its footprint (uniform scale to
## the footprint's width, aspect preserved, bottom-center anchored —
## never upscaled beyond the footprint width), background keyed to
## transparency at load by the hierarchy module.
func _build_thumbnail(visuals: TownVisuals, path: String) -> void:
	var loaded: Dictionary = visuals.thumbnail_texture(path)
	if not bool(loaded.get("ok", false)):
		_degrade_to_marker("thumbnail: " + str(loaded.get("error", "")))
		return
	var texture: Texture2D = loaded["texture"]
	var natural := Vector2(texture.get_size())
	if natural.x <= 0.0 or natural.y <= 0.0:
		_degrade_to_marker("thumbnail: empty texture")
		return
	var scale_factor := _footprint_rect.size.x / natural.x
	var sprite := Sprite2D.new()
	sprite.centered = false
	sprite.texture = texture
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	sprite.scale = Vector2(scale_factor, scale_factor)
	sprite.position = Vector2(
		0.0,
		_footprint_rect.size.y - natural.y * scale_factor)
	add_child(sprite)


## Degrades to the labeled footprint marker with the reason recorded
## (never a crash, never a skipped placement).
func _degrade_to_marker(reason: String) -> void:
	visual_error = reason
	visual_source = TownVisuals.SOURCE_MARKER


## Draws the footprint diamond for markers/placeholders (with the label
## naming the item or the unknown id) and the selection highlight for any
## selected object.
func _draw() -> void:
	var diamond := _diamond_points()
	if visual_source == TownVisuals.SOURCE_MARKER \
			or visual_source == TownVisuals.SOURCE_PLACEHOLDER:
		_draw_diamond_outline(diamond, MARKER_COLOR, MARKER_WIDTH)
		var label: String = display_name \
			if visual_source == TownVisuals.SOURCE_MARKER \
			else "unknown id %d" % legacy_id
		var font := ThemeDB.fallback_font
		var top := diamond[0] as Vector2
		var draw_position := Vector2(
			_footprint_rect.size.x / 2.0 - 60.0, top.y - 4.0)
		# Readable over any terrain: a dark pass under a light pass.
		draw_string(font, draw_position + Vector2(1.0, 1.0), label,
			HORIZONTAL_ALIGNMENT_CENTER, 120.0, LABEL_FONT_SIZE,
			Color(0.0, 0.0, 0.0, 0.85))
		draw_string(font, draw_position, label,
			HORIZONTAL_ALIGNMENT_CENTER, 120.0, LABEL_FONT_SIZE,
			Color(1.0, 1.0, 1.0, 0.95))
	if _selected:
		# Highlight covers the selected footprint: filled diamond plus a
		# bright outline (provisional presentation, design D8).
		draw_colored_polygon(diamond, HIGHLIGHT_FILL)
		_draw_diamond_outline(diamond, HIGHLIGHT_COLOR, HIGHLIGHT_WIDTH)


## The footprint's bounding diamond in node-local coordinates: the top
## vertex of the top-left cell, the right vertex of the top-right cell,
## the bottom vertex of the bottom-right cell, the left vertex of the
## bottom-left cell.
func _diamond_points() -> PackedVector2Array:
	var width := footprint.x
	var height := footprint.y
	var top_left := Iso.grid_to_screen(cell) - _footprint_rect.position
	var top_right := Iso.grid_to_screen(
		cell + Vector2i(width - 1, 0)) - _footprint_rect.position
	var bottom_left := Iso.grid_to_screen(
		cell + Vector2i(0, height - 1)) - _footprint_rect.position
	var bottom_right := Iso.grid_to_screen(
		cell + Vector2i(width - 1, height - 1)) - _footprint_rect.position
	return PackedVector2Array([
		top_left + Vector2(0.0, -Iso.TILE_HEIGHT / 2.0),
		top_right + Vector2(Iso.TILE_WIDTH / 2.0, 0.0),
		bottom_right + Vector2(0.0, Iso.TILE_HEIGHT / 2.0),
		bottom_left + Vector2(-Iso.TILE_WIDTH / 2.0, 0.0),
	])


func _draw_diamond_outline(points: PackedVector2Array, color: Color,
		width: float) -> void:
	draw_polyline(points, color, width, true)
	draw_line(points[points.size() - 1], points[0], color, width)
