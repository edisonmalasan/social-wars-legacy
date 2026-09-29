extends Node2D
## Footprint preview overlay for the placement flow (building-placement,
## spec "Placement flow"). Draws the target footprint's cell diamonds
## over the objects layer — below the UI canvas, above the town objects —
## colored by the evaluation's validity: provisional green for a valid
## target, provisional red for an invalid one (no authentic legacy
## placement preview has been captured, so the colors are recorded
## provisional exactly like the M6 selection highlight).
##
## Pure view: no state, no requests. The town view commits evaluations
## here (`show_cells`) and drops them on exit or rebuild (`clear`).

const Iso = preload("res://scripts/town/iso.gd")

## Provisional presentation colors (design Non-Goals: provisional
## presentation pending a captured legacy preview).
const VALID_FILL := Color(0.30, 0.95, 0.45, 0.30)
const VALID_LINE := Color(0.25, 0.90, 0.40, 0.95)
const INVALID_FILL := Color(0.98, 0.35, 0.30, 0.32)
const INVALID_LINE := Color(1.0, 0.45, 0.35, 0.95)
const LINE_WIDTH := 2.0

## Committed preview cells in anchor order ([] while hidden).
var cells: Array = []
## Validity of the committed evaluation (drives the fill/line color).
var target_valid := false


## Commits an evaluation's cells and validity and redraws. An empty
## cell list hides the overlay (a structurally failed evaluation shows
## nothing rather than a fabricated target).
func show_cells(next_cells: Array, valid: bool) -> void:
	cells = next_cells.duplicate()
	target_valid = valid
	visible = not cells.is_empty()
	queue_redraw()


## Drops the preview: hidden, nothing drawn, ready for the next mode.
func clear() -> void:
	cells = []
	target_valid = false
	visible = false
	queue_redraw()


## True while a committed footprint is displayed.
func is_shown() -> bool:
	return visible and not cells.is_empty()


func _draw() -> void:
	if cells.is_empty():
		return
	var fill := VALID_FILL if target_valid else INVALID_FILL
	var line := VALID_LINE if target_valid else INVALID_LINE
	for cell: Variant in cells:
		var points := _diamond(Vector2i(cell))
		draw_colored_polygon(points, fill)
		draw_polyline(points, line, LINE_WIDTH, true)
		draw_line(points[3], points[0], line, LINE_WIDTH, true)


## The world-space diamond polygon of one cell — the same projection
## the terrain, objects, and selection use (no second geometry).
static func _diamond(cell: Vector2i) -> PackedVector2Array:
	var center := Iso.grid_to_screen(cell)
	return PackedVector2Array([
		center + Vector2(0.0, -Iso.TILE_HEIGHT / 2.0),
		center + Vector2(Iso.TILE_WIDTH / 2.0, 0.0),
		center + Vector2(0.0, Iso.TILE_HEIGHT / 2.0),
		center + Vector2(-Iso.TILE_WIDTH / 2.0, 0.0),
	])
