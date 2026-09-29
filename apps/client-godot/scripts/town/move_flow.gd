extends RefCounted
## Pure evaluation helpers for the move flow (building-move, spec "Move
## flow"): which cells a moving footprint would cover, whether a previewed
## target is valid, and how the refusal reads. No nodes, no I/O, no
## requests, no clock — the town view and its suite consume the same
## functions, exactly as `placement_flow.gd` serves the placement flow
## (design D5: the client owns the gameplay rules the legacy server never
## enforced; the endpoint keeps only structural fail-closed validation).
##
## Invalid-target reasons, evaluated in the documented order (spec "Invalid
## targets send nothing": out of grid, covered by another placement, or the
## building's own current cell):
##   out_of_grid    the anchor lies outside the shared 0..99 grid;
##   occupied       the footprint rect intersects ANOTHER placement — the
##                  moving building's own cells are excluded, so a target
##                  overlapping only itself is never "occupied" (spec "The
##                  building's own cells do not block it");
##   same_cell      the anchor is the cell the building already occupies, a
##                  no-op the flow refuses rather than sending;
##   unaddressable  the placement's legacy map key is not a positive
##                  integer, so no move intent can name it (design D7). The
##                  refusal is explicit; the index is never coerced.
##
## Same-cell is evaluated on the ANCHOR, not the footprint: a footprint may
## legitimately extend past the grid edge and overlap its own body, and the
## two documented refusals above own those cases. Ordering is fixed so the
## reported reason is deterministic: `unaddressable` -> `out_of_grid` ->
## `occupied` -> `same_cell`.
##
## Ownership, affordability, and price are deliberately absent: a move
## derives a neutral price vector (design D2) and legacy performs no
## ownership or bounds check, so those gates would be fabricated rules.
## The client refuses nothing it cannot name — the fail-closed envelope
## below names the condition and never evaluates.

const PlacementFlow = preload("res://scripts/town/placement_flow.gd")
const Iso = preload("res://scripts/town/iso.gd")
const TownState = preload("res://scripts/town/town_state.gd")

## Refusal reasons, in evaluation order. `no_selection` is the structural
## one (no state, no selected placement) and names itself instead of
## evaluating a target.
const REASON_NO_SELECTION := "no_selection"
const REASON_UNADDRESSABLE := "unaddressable"
const REASON_OUT_OF_GRID := "out_of_grid"
const REASON_OCCUPIED := "occupied"
const REASON_SAME_CELL := "same_cell"


## The cells a width x height footprint covers when anchored at `cell`
## (the anchor itself is the first cell; a footprint may legitimately
## extend past the grid edge — design D5, the anchor alone is gated).
## Delegates to the placement flow's own helper so both surfaces share one
## footprint rule instead of a second geometry.
static func footprint_cells(cell: Vector2i, footprint: Vector2i) -> Array:
	return PlacementFlow.footprint_cells(cell, footprint)


## Evaluate a previewed move target against the typed state.
## Returns `{ok, error, valid, reason, cells, item, slot, cell}`: `cells`
## always covers the footprint (the overlay marks where the object would
## land even while invalid), `reason` is "" while valid, otherwise the
## first failing gate in the documented order. Structural failures (no
## state, no selected placement) return `{ok:false}` with no evaluation.
static func preview(state: Variant, placement: Variant,
		cell: Vector2i) -> Dictionary:
	if state == null:
		return _reject("the town state is unavailable", REASON_NO_SELECTION)
	if not (placement is TownState.Placement):
		return _reject("no building is selected", REASON_NO_SELECTION)
	var typed: TownState.Placement = placement
	var footprint: Vector2i = typed.footprint
	var evaluation := {
		"ok": true,
		"error": "",
		"cells": footprint_cells(cell, footprint),
		"item": int(typed.item),
		"slot": int(typed.slot),
		"cell": cell,
	}
	if not TownState.is_addressable(typed):
		evaluation["valid"] = false
		evaluation["reason"] = REASON_UNADDRESSABLE
		return evaluation
	if not Iso.contains_cell(cell):
		evaluation["valid"] = false
		evaluation["reason"] = REASON_OUT_OF_GRID
		return evaluation
	if _overlaps(state, cell, footprint, typed):
		evaluation["valid"] = false
		evaluation["reason"] = REASON_OCCUPIED
		return evaluation
	if cell == typed.cell:
		evaluation["valid"] = false
		evaluation["reason"] = REASON_SAME_CELL
		return evaluation
	evaluation["valid"] = true
	evaluation["reason"] = ""
	return evaluation


## True when the footprint rect anchored at `cell` intersects a placement
## other than the one being moved. The moving placement is excluded BY
## IDENTITY (the same `Placement` instance the state holds), so its own
## body never blocks a target that overlaps only itself (spec "The
## building's own cells do not block it"). Rects compare full footprints, so
## a candidate overlapping a large neighbour's body is occupied even when
## their anchors differ.
static func _overlaps(state: Variant, cell: Vector2i, footprint: Vector2i,
		moving: Variant) -> bool:
	var target := Rect2i(cell, Vector2i(maxi(footprint.x, 1),
		maxi(footprint.y, 1)))
	for placement: Variant in state.placements:
		if placement == null or placement == moving:
			continue
		var other_cell: Vector2i = placement.cell
		var other_footprint: Vector2i = placement.footprint
		var other := Rect2i(other_cell, Vector2i(maxi(other_footprint.x, 1),
			maxi(other_footprint.y, 1)))
		if target.intersects(other):
			return true
	return false


## The explicit refusal text for an invalid target: the reason plus the two
## cells it compares, so the player never sees a bare rejection. Returns ""
## while the target is valid.
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if bool(evaluation.get("valid", false)):
		return ""
	var item := int(evaluation.get("item", 0))
	var cell: Vector2i = evaluation.get("cell", Vector2i.ZERO)
	match str(evaluation.get("reason", "")):
		REASON_UNADDRESSABLE:
			return "not movable: item %d has no addressable save key" % item
		REASON_OUT_OF_GRID:
			return "not movable: (%d, %d) lies outside the town grid" % [
				cell.x, cell.y]
		REASON_OCCUPIED:
			return "not movable: item %d would overlap another building" % item
		REASON_SAME_CELL:
			return "not movable: item %d already sits at (%d, %d)" % [
				item, cell.x, cell.y]
	return "not movable"


## The house rejection envelope: names the condition, never evaluates.
static func _reject(message: String, reason: String) -> Dictionary:
	return {"ok": false, "error": "[move] preview rejected: " + message,
		"valid": false, "reason": reason, "cells": [], "item": 0,
		"slot": -1, "cell": Vector2i.ZERO}
