extends RefCounted
## Isometric projection for the town slice (OpenSpec `godot-town-rendering`
## "Isometric projection", design D2).
##
## Pure module: grid<->screen math over committed constants, no nodes, no
## state, no I/O. Terrain, town objects, selection, and camera bounds all
## consume these constants — one coordinate space, no second geometry.
##
## Constants are DERIVED AND PROVISIONAL (design D2, README "Isometric
## projection constants"):
##   * scale anchor: converted package frames against content footprints
##     (House I frame 216x144 on a 2x2 footprint; Wild Elephant frame
##     171x191 on a 1x1 footprint);
##   * viewable-town criterion: at the legacy stage size 1400x600 a
##     TW=40 view spans 35x30 cells, which contains 29 of the 40 fresh-save
##     placements (the densest such window);
##   * land-fit validation: placement anchors classify onto the legacy
##     island image's land mask (residual recorded in the README and the
##     town evidence report).
## The legacy SWF's static iso-engine identifiers (`TILE_SIZE`,
## `EI_TILE_HEIGHT_PIXELS`, `core.isoengine.isoUtils`, `gridWidth`,
## `gridHeight`) exist as ABC strings but their NUMERIC VALUES WERE NEVER
## EXTRACTED — pixel parity with the Flash client is not claimed.
##
## Projection (cell center, x -> lower-right, y -> lower-left):
##   screen.x = (x - y) * TILE_WIDTH / 2  + ORIGIN_X
##   screen.y = (x + y) * TILE_HEIGHT / 2 + ORIGIN_Y
## with ORIGIN_X = GRID_EXTENT * TILE_WIDTH / 2 (cell (0,0) sits at the
## diamond's top vertex, offset down by TILE_HEIGHT / 2 so every tile stays
## inside the world rectangle). The inverse recovers fractional cell-space
## coordinates and rounds to the containing cell — exact for every cell of
## the legacy 0..99 extent.

## Tile width in world pixels (derived, provisional).
const TILE_WIDTH := 40.0
## Tile height in world pixels; the 2:1 diamond family (derived, provisional).
const TILE_HEIGHT := 20.0
## Legacy grid extent: placements across the save corpus use integer
## coordinates 0..99 on both axes.
const GRID_EXTENT := 100
## World-space x of the diamond's top vertex (half the world width).
const ORIGIN_X := GRID_EXTENT * TILE_WIDTH / 2.0
## World-space y of the diamond's top vertex (tile-height offset keeps the
## first row inside the world rectangle).
const ORIGIN_Y := TILE_HEIGHT / 2.0


## The world rectangle every town consumer shares: ground, objects,
## selection hits, and camera bounds all derive from this one rect.
static func world_rect() -> Rect2:
	return Rect2(0.0, 0.0, GRID_EXTENT * TILE_WIDTH, GRID_EXTENT * TILE_HEIGHT)


## True when a cell lies inside the legacy 0..99 extent on both axes.
static func contains_cell(cell: Vector2i) -> bool:
	return (cell.x >= 0 and cell.x < GRID_EXTENT
		and cell.y >= 0 and cell.y < GRID_EXTENT)


## Cell -> its diamond center in world pixels. Deterministic and total:
## projecting an out-of-extent cell still returns the mathematically
## implied point (callers gate with `contains_cell`).
static func grid_to_screen(cell: Vector2i) -> Vector2:
	return Vector2(
		(cell.x - cell.y) * TILE_WIDTH / 2.0 + ORIGIN_X,
		(cell.x + cell.y) * TILE_HEIGHT / 2.0 + ORIGIN_Y)


## Screen point -> the cell whose diamond covers it, or an explicit
## out-of-grid error. Never wraps, never clamps: negative components,
## points outside the world rectangle, points in the world rectangle but
## outside the grid (water corners), and non-finite input all fail closed
## with a named error and no cell.
static func screen_to_grid(point: Vector2) -> Dictionary:
	if not point.is_finite():
		return {"ok": false,
			"error": "[iso] screen_to_grid rejected: non_finite_point",
			"cell": Vector2i.ZERO}
	if point.x < 0.0 or point.y < 0.0 \
			or point.x > world_rect().size.x or point.y > world_rect().size.y:
		return {"ok": false,
			"error": "[iso] screen_to_grid rejected: out_of_grid",
			"cell": Vector2i.ZERO}
	# Invert the affine map to fractional cell space, then round to the
	# diamond that covers the point.
	var across := (point.x - ORIGIN_X) / (TILE_WIDTH / 2.0)
	var down := (point.y - ORIGIN_Y) / (TILE_HEIGHT / 2.0)
	var cell := Vector2i(roundi((across + down) / 2.0),
		roundi((down - across) / 2.0))
	if not contains_cell(cell):
		return {"ok": false,
			"error": "[iso] screen_to_grid rejected: out_of_grid",
			"cell": Vector2i.ZERO}
	return {"ok": true, "error": "", "cell": cell}


## Screen bounds of a width x height footprint, derived from the footprint's
## corner cells alone (spec: "SHALL derive a multi-cell footprint's screen
## bounds from its corner cells"): the left edge of the bottom-left corner
## cell, the top edge of the top-left corner cell, the right edge of the
## top-right corner cell, and the bottom edge of the bottom-right corner
## cell.
static func footprint_rect(cell: Vector2i, width: int, height: int) -> Rect2:
	var w := maxi(width, 1)
	var h := maxi(height, 1)
	var top_left := grid_to_screen(cell)
	var top_right := grid_to_screen(cell + Vector2i(w - 1, 0))
	var bottom_left := grid_to_screen(cell + Vector2i(0, h - 1))
	var bottom_right := grid_to_screen(cell + Vector2i(w - 1, h - 1))
	var left: float = bottom_left.x - TILE_WIDTH / 2.0
	var right: float = top_right.x + TILE_WIDTH / 2.0
	var top: float = top_left.y - TILE_HEIGHT / 2.0
	var bottom: float = bottom_right.y + TILE_HEIGHT / 2.0
	return Rect2(Vector2(left, top), Vector2(right - left, bottom - top))


## Isometric depth of a cell: x + y (larger = nearer the camera, drawn
## later). Objects sharing a depth key use the documented deterministic
## tie-break of the town build order — depth, then grid y, then grid x,
## then save order — identical across runs and platforms.
static func depth_key(cell: Vector2i) -> int:
	return cell.x + cell.y
