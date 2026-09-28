extends "res://tests/test_base.gd"
## Isometric projection suite (OpenSpec `godot-town-rendering` "Isometric
## projection", change task 1.1).
##
## Scenarios:
##   extent      every cell of the legacy 0..99 extent round-trips through
##               grid->screen->grid exactly;
##   footprints  the corner cells of multi-cell footprints round-trip and
##               the footprint rect is derivable from corner cells alone;
##   out-of-grid negative, outside-world, off-diamond, and non-finite
##               points are rejected with a named error and no cell —
##               never a wrapped or silently clamped result;
##   constants   the committed constants are exactly the ones the README
##               documents (derived/provisional with the recorded
##               land-fit residual), the world rect is the shared
##               geometry, and depth keys increase toward the camera.
##
## Pure module: no API, no boot flow, no endpoint argument. Runs headless
## as part of `verify-boot.ps1`.

const Iso = preload("res://scripts/town/iso.gd")
const README_PATH := "res://README.md"

## Converted building footprint (content 1, House I: 2x2) and the largest
## committed footprint in the slice (content 4004-style 12x6 station) plus
## a converted unit footprint (content 933: 1x1).
const FOOTPRINTS := [
	{"cell": Vector2i(0, 0), "w": 2, "h": 2},
	{"cell": Vector2i(12, 45), "w": 2, "h": 2},
	{"cell": Vector2i(87, 93), "w": 2, "h": 2},
	{"cell": Vector2i(40, 40), "w": 12, "h": 6},
	{"cell": Vector2i(6, 6), "w": 12, "h": 6},
	{"cell": Vector2i(50, 50), "w": 1, "h": 1},
]

## README substrings that document the constants (spec scenario "Stable,
## documented constants").
const README_TOKENS := [
	"### Isometric projection constants",
	"TW=40",
	"TH=20",
	"derived and provisional",
	"TILE_SIZE",
	"never extracted",
	"39/40",
	"549/576",
]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	_check_constants()
	_check_extent_round_trip()
	_check_footprint_round_trips()
	_check_footprint_from_corners()
	_check_out_of_grid()
	_check_depth_keys()
	_check_documented_constants()


func _check_constants() -> void:
	check_eq(Iso.TILE_WIDTH, 40.0, "tile width is the committed TW=40")
	check_eq(Iso.TILE_HEIGHT, 20.0, "tile height is the committed TH=20")
	check_eq(Iso.GRID_EXTENT, 100, "grid extent covers the legacy 0..99")
	check_eq(Iso.ORIGIN_X, 2000.0, "origin x is half the world width")
	check_eq(Iso.ORIGIN_Y, 10.0, "origin y is the tile-height offset")
	check_eq(Iso.world_rect(), Rect2(0.0, 0.0, 4000.0, 2000.0),
		"world rect is the shared geometry every consumer uses")
	check(Iso.contains_cell(Vector2i(0, 0)), "grid corner (0,0) is in grid")
	check(Iso.contains_cell(Vector2i(99, 99)), "grid corner (99,99) is in grid")
	check(not Iso.contains_cell(Vector2i(-1, 0)), "negative x is out of grid")
	check(not Iso.contains_cell(Vector2i(0, 100)), "x=100 is out of grid")
	check(not Iso.contains_cell(Vector2i(99, -1)), "negative y is out of grid")


func _check_extent_round_trip() -> void:
	var mismatches: Array = []
	for x in range(Iso.GRID_EXTENT):
		for y in range(Iso.GRID_EXTENT):
			var cell := Vector2i(x, y)
			var back := Iso.screen_to_grid(Iso.grid_to_screen(cell))
			if not bool(back.get("ok", false)) or back["cell"] != cell:
				mismatches.append("%s->%s" % [cell, back.get("cell")])
	check(mismatches.is_empty(),
		"every cell of the 0..99 extent round-trips exactly (first failures: %s)"
		% str(mismatches.slice(0, 5)))


func _check_footprint_round_trips() -> void:
	for spec in FOOTPRINTS:
		var origin: Vector2i = spec["cell"]
		var w: int = spec["w"]
		var h: int = spec["h"]
		var corners := [
			origin,
			origin + Vector2i(w - 1, 0),
			origin + Vector2i(0, h - 1),
			origin + Vector2i(w - 1, h - 1),
		]
		for corner in corners:
			var back := Iso.screen_to_grid(Iso.grid_to_screen(corner))
			check(bool(back.get("ok", false)) and back["cell"] == corner,
				"footprint corner %s of %sx%s round-trips (got %s)"
				% [corner, w, h, back.get("cell")])


func _check_footprint_from_corners() -> void:
	for spec in FOOTPRINTS:
		var cell: Vector2i = spec["cell"]
		var w: int = spec["w"]
		var h: int = spec["h"]
		var rect := Iso.footprint_rect(cell, w, h)
		var top_left := Iso.grid_to_screen(cell)
		var top_right := Iso.grid_to_screen(cell + Vector2i(w - 1, 0))
		var bottom_left := Iso.grid_to_screen(cell + Vector2i(0, h - 1))
		var bottom_right := Iso.grid_to_screen(cell + Vector2i(w - 1, h - 1))
		var expected := Rect2(
			Vector2(bottom_left.x - Iso.TILE_WIDTH / 2.0,
				top_left.y - Iso.TILE_HEIGHT / 2.0),
			Vector2(top_right.x + Iso.TILE_WIDTH / 2.0
				- (bottom_left.x - Iso.TILE_WIDTH / 2.0),
				bottom_right.y + Iso.TILE_HEIGHT / 2.0
				- (top_left.y - Iso.TILE_HEIGHT / 2.0)))
		check_eq(rect, expected,
			"footprint rect derives from corner cells alone (%sx%s at %s)"
			% [w, h, cell])
		var covers := true
		for i in range(w):
			for j in range(h):
				if not rect.has_point(Iso.grid_to_screen(cell + Vector2i(i, j))):
					covers = false
		check(covers, "footprint rect covers all its cell centers (%sx%s at %s)"
			% [w, h, cell])


func _check_out_of_grid() -> void:
	var points := [
		{"point": Vector2(-1.0, 500.0), "name": "negative x"},
		{"point": Vector2(500.0, -1.0), "name": "negative y"},
		{"point": Vector2(4001.0, 500.0), "name": "beyond world width"},
		{"point": Vector2(2000.0, 2001.0), "name": "beyond world height"},
		{"point": Vector2(5.0, 5.0), "name": "world corner outside the diamond"},
		{"point": Vector2(3995.0, 1995.0),
			"name": "far world corner outside the diamond"},
	]
	for entry in points:
		var result := Iso.screen_to_grid(entry["point"])
		check(not bool(result.get("ok", true)),
			"%s is rejected, not clamped" % entry["name"])
		check(str(result.get("error", "")) != "",
			"%s rejection names the error" % entry["name"])
		check(result["cell"] == Vector2i.ZERO,
			"%s rejection carries no cell" % entry["name"])
		check(str(result.get("error", "")).findn("out_of_grid") >= 0,
			"%s rejection is out_of_grid (got %s)"
			% [entry["name"], result.get("error")])
	for bad in [Vector2(NAN, 100.0), Vector2(100.0, INF),
			Vector2(-INF, 0.0), Vector2(NAN, NAN)]:
		var result := Iso.screen_to_grid(bad)
		check(not bool(result.get("ok", true)),
			"non-finite point %s is rejected" % str(bad))
		check(str(result.get("error", "")).findn("non_finite_point") >= 0,
			"non-finite rejection names non_finite_point (got %s)"
			% result.get("error"))
		check(result["cell"] == Vector2i.ZERO,
			"non-finite rejection carries no cell")
	# Explicit in-grid results still succeed at known anchors.
	check_eq(Iso.screen_to_grid(Vector2(2000.0, 10.0))["cell"],
		Vector2i(0, 0), "the diamond's top vertex maps to cell (0,0)")
	check_eq(Iso.screen_to_grid(Iso.grid_to_screen(Vector2i(99, 99)))["cell"],
		Vector2i(99, 99), "the far corner cell maps back to itself")


func _check_depth_keys() -> void:
	check_eq(Iso.depth_key(Vector2i(0, 0)), 0, "origin depth key is 0")
	check_eq(Iso.depth_key(Vector2i(99, 99)), 198, "far depth key is 198")
	check_eq(Iso.depth_key(Vector2i(3, 2)), Iso.depth_key(Vector2i(2, 3)),
		"diagonal twins share one depth key (documented tie)")
	check_eq(Iso.depth_key(Vector2i(5, 7)) + 1, Iso.depth_key(Vector2i(6, 7)),
		"depth increases by one stepping toward the camera on x")
	check_eq(Iso.depth_key(Vector2i(5, 7)) + 1, Iso.depth_key(Vector2i(5, 8)),
		"depth increases by one stepping toward the camera on y")


func _check_documented_constants() -> void:
	var text := FileAccess.get_file_as_string(README_PATH)
	check(text != "", "client README is readable")
	for token in README_TOKENS:
		check(text.find(token) >= 0,
			"README documents %s" % token)
