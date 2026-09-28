extends "res://tests/test_base.gd"
## Selection suite (OpenSpec `godot-town-rendering` "Press-to-cell
## selection", change task 5.1).
##
## Scenarios:
##   select    an in-grid press selects the object under the cell,
##              commits exactly one highlight, and moves the highlight
##              when a later press picks another object;
##   topmost   at a cell covered by several footprints the depth-topmost
##              object wins (crafted overlap: a 4x4 at (0,0) under a
##              1x1 at (1,1) — the wall wins the press at (1,1));
##   clear     empty in-ground and out-of-grid ground clear the
##              selection and drop the highlight;
##   invalid   non-finite presses and an unbuilt view fail closed with a
##              named error and never change the committed selection;
##   immutable repeated selection churn leaves the town state
##              byte-identical (serialized snapshot comparison).
##
## Uses the ContentRegistry autoload (content + asset registry loaded
## explicitly). No API, no server. Runs headless as part of
## `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")

const FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"


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

	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"town builds: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return

	var snapshot_before := _state_snapshot(state)
	_check_select_and_switch(town)
	_check_clear(town)
	_check_invalid(town, state)
	_check_state_immutable(town, state, snapshot_before)
	_check_topmost(registry, payload)
	town.free()


## Select, then switch: exactly one highlight at every moment.
func _check_select_and_switch(town: Node2D) -> void:
	var first: Variant = town.objects[0]
	var second: Variant = town.objects[1]
	var first_press: Dictionary = town.handle_pointer_press(
		_center_of(first))
	check(bool(first_press.get("ok", false)),
		"the first press succeeds: %s" % first_press.get("error"))
	check_eq(town.selection_legacy_id(), first.legacy_id,
		"the first press commits its object")
	check(first.is_selected(), "the committed object carries the highlight")
	check(not second.is_selected(), "no other object is highlighted")

	var second_press: Dictionary = town.handle_pointer_press(
		_center_of(second))
	check(bool(second_press.get("ok", false)),
		"the second press succeeds: %s" % second_press.get("error"))
	check_eq(town.selection_legacy_id(), second.legacy_id,
		"a later press moves the selection")
	check(second.is_selected(), "the new object is highlighted")
	check(not first.is_selected(),
		"the previous object drops its highlight")
	var highlighted := 0
	for object in town.objects:
		if object.is_selected():
			highlighted += 1
	check_eq(highlighted, 1, "exactly one object is ever highlighted")


## Empty in-ground ground and out-of-grid ground clear the selection.
func _check_clear(town: Node2D) -> void:
	var empty_cell := _find_uncovered_cell(town.objects)
	check(empty_cell.x >= 0, "an empty in-ground cell exists")
	var empty_press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(empty_cell))
	check(bool(empty_press.get("ok", false)),
		"the empty-ground press succeeds: %s" % empty_press.get("error"))
	check(bool(empty_press.get("cleared", false)),
		"empty ground reports cleared")
	check_eq(town.selection_legacy_id(), -1,
		"empty ground clears the selection")

	town.handle_pointer_press(_center_of(town.objects[0]))
	check_eq(town.selection_legacy_id(), town.objects[0].legacy_id,
		"a selection exists before the out-of-grid press")
	var edge_press: Dictionary = town.handle_pointer_press(Vector2(-800, -800))
	check(bool(edge_press.get("ok", false)),
		"the out-of-grid press succeeds: %s" % edge_press.get("error"))
	check(bool(edge_press.get("cleared", false)),
		"out-of-grid ground reports cleared")
	check_eq(town.selection_legacy_id(), -1,
		"out-of-grid ground clears the selection")
	var highlighted := 0
	for object in town.objects:
		if object.is_selected():
			highlighted += 1
	check_eq(highlighted, 0, "cleared selection leaves no highlight")


## Invalid presses fail closed with a named error, state untouched.
func _check_invalid(town: Node2D, state: Variant) -> void:
	town.handle_pointer_press(_center_of(town.objects[2]))
	var committed: int = town.selection_legacy_id()
	var nan_press: Dictionary = town.handle_pointer_press(Vector2(0, NAN))
	check(not bool(nan_press.get("ok", true)), "a NaN press is rejected")
	check(String(nan_press.get("error", "")).contains("non_finite"),
		"the NaN rejection names the condition: %s" % nan_press.get("error"))
	var inf_press: Dictionary = town.handle_pointer_press(
		Vector2(INF, 0))
	check(not bool(inf_press.get("ok", true)), "an infinite press is rejected")
	check_eq(town.selection_legacy_id(), committed,
		"invalid presses leave the selection unchanged")

	var unbuilt: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(unbuilt)
	var rejected: Dictionary = unbuilt.handle_pointer_press(Vector2.ZERO)
	check(not bool(rejected.get("ok", true)),
		"an unbuilt view rejects presses")
	check(String(rejected.get("error", "")).contains("town_not_built"),
		"the unbuilt rejection names the condition: %s"
		% rejected.get("error"))
	check(unbuilt.selection() == null,
		"an unbuilt view never fabricates a selection")
	unbuilt.free()


## Spec: repeated selections never mutate the town state.
func _check_state_immutable(town: Node2D, state: Variant,
		snapshot_before: String) -> void:
	for round_index in range(3):
		for object in town.objects:
			town.handle_pointer_press(_center_of(object))
		town.handle_pointer_press(Vector2(-800, -800))
		town.handle_pointer_press(_center_of(town.objects[0]))
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after repeated "
		+ "selections")


## Depth-topmost wins at overlapping footprints (crafted 4x4 under a
## 1x1 sharing cell (1,1)).
func _check_topmost(registry: Variant, payload: Variant) -> void:
	var overlap: Variant = payload.duplicate(true)
	(overlap["map"] as Dictionary)["items"] = {
		"p0": [26, 0, 0, 0, 0, 0, 0, 0],
		"p1": [23, 1, 1, 0, 0, 0, 0, 0],
	}
	var parsed: Dictionary = TownState.parse(overlap, registry)
	check(bool(parsed.get("ok", false)),
		"the crafted overlap payload parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	check(bool(built.get("ok", false)),
		"the overlap town builds: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	check_eq(town.objects.size(), 2, "both overlapping placements render")
	# Draw order: the shallower center (depth 0) first, the wall
	# (depth 20) later — so the wall is depth-topmost at cell (1,1).
	check_eq(int(town.objects[0].legacy_id), 26,
		"the 4x4 center renders first in depth order")
	check_eq(int(town.objects[1].legacy_id), 23,
		"the 1x1 wall renders later (depth-topmost)")
	var center: Variant = town.objects[0]
	var wall: Variant = town.objects[1]
	check(center.contains_cell(Vector2i(1, 1)),
		"the center footprint covers the shared cell")
	check(wall.contains_cell(Vector2i(1, 1)),
		"the wall footprint covers the shared cell")

	var lower_press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(Vector2i(0, 0)))
	check(bool(lower_press.get("ok", false))
		and int(lower_press.get("legacy_id", -1)) == 26,
		"cell (0,0) belongs to the center alone")
	var overlap_press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(Vector2i(1, 1)))
	check(bool(overlap_press.get("ok", false)),
		"the shared-cell press succeeds: %s" % overlap_press.get("error"))
	check_eq(int(overlap_press.get("legacy_id", -1)), 23,
		"the depth-topmost object wins the shared cell")
	check_eq(town.selection_legacy_id(), 23,
		"the committed selection is the topmost object")
	check(wall.is_selected(), "the topmost object is highlighted")
	check(not center.is_selected(),
		"the covered lower object stays unhighlighted")
	town.free()


## Selection needs a point inside the object's footprint rect.
func _center_of(object: Variant) -> Vector2:
	var rect: Rect2 = object.footprint_rect()
	return rect.position + rect.size * 0.5


## Deterministic serialization of every committed state field.
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append(placement.raw)
	return JSON.stringify({
		"placements": rows,
		"resources": {
			"coins": state.resources.coins,
			"wood": state.resources.wood,
			"steel": state.resources.steel,
			"oil": state.resources.oil,
			"cash": state.resources.cash,
			"energy": state.resources.energy,
			"mana": state.resources.mana,
		},
		"summary": {
			"name": state.summary.name,
			"level": state.summary.level,
			"xp": state.summary.xp,
		},
		"missing": state.missing,
		"unresolved_ids": state.unresolved_ids,
	})


## The first cell in 0..99 no object footprint covers.
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
