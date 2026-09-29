extends RefCounted
## Pure evaluation helpers for the placement flow (building-placement,
## spec "Placement flow"): which cells a footprint covers, whether a
## preview target is valid, and how a cost reads against the stored
## resources. No nodes, no I/O, no requests — the town view and its
## suite consume the same functions (design D5: the client owns the
## gameplay rules the legacy server never enforced; the endpoint keeps
## only structural validation).
##
## Invalid-target reasons, evaluated in the documented order (spec:
## "marks a target invalid when it lies outside the grid or covers an
## existing footprint and shows the cost against current resources",
## scenario: "the building's cost exceeds current resources"):
##   out_of_grid  the anchor lies outside the shared 0..99 grid;
##   occupied     the footprint rect intersects an existing placement;
##   unaffordable a cost exceeds the stored resource (an unknown cost
##                key is never treated as affordable — no guessing).

const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")
const Iso = preload("res://scripts/town/iso.gd")

## Cost resource -> town-state resource field (`gold` is stored as
## `coins` in the HUD vocabulary; the response's `gold` maps back the
## same way).
const COST_STATE_FIELDS := {
	"gold": "coins",
	"wood": "wood",
	"oil": "oil",
	"steel": "steel",
	"cash": "cash",
}
## Stable display order of cost resources.
const COST_ORDER := ["gold", "wood", "oil", "steel", "cash"]


## The cells a width x height footprint covers when anchored at `cell`
## (the anchor itself is the first cell; a footprint may legitimately
## extend past the grid edge — design D5, the anchor alone is gated).
static func footprint_cells(cell: Vector2i, footprint: Vector2i) -> Array:
	var cells: Array = []
	var width := maxi(footprint.x, 1)
	var height := maxi(footprint.y, 1)
	for offset_y in range(height):
		for offset_x in range(width):
			cells.append(cell + Vector2i(offset_x, offset_y))
	return cells


## Evaluate a preview target. Returns `{ok, error, valid, reason, cells,
## cost}`: `cells` always covers the footprint (the overlay marks where
## the object would go even while invalid), `cost` is a copy of the
## entry's cost map, and `reason` is "" while valid, otherwise the first
## failing gate in the documented order. Structural failures (no state
## or no selected entry) return `{ok:false}` with no evaluation.
static func preview(state: Variant, entry: Variant,
		cell: Vector2i) -> Dictionary:
	if state == null:
		return _reject("town state is unavailable")
	if not (entry is PlacementCatalog.Entry):
		return _reject("no building is selected")
	var typed: PlacementCatalog.Entry = entry
	var evaluation := {"ok": true, "error": "",
		"cells": footprint_cells(cell, typed.footprint),
		"cost": typed.costs.duplicate()}
	if not Iso.contains_cell(cell):
		evaluation["valid"] = false
		evaluation["reason"] = "out_of_grid"
		return evaluation
	if _overlaps(state, cell, typed.footprint):
		evaluation["valid"] = false
		evaluation["reason"] = "occupied"
		return evaluation
	if not affordable(state, typed.costs):
		evaluation["valid"] = false
		evaluation["reason"] = "unaffordable"
		return evaluation
	evaluation["valid"] = true
	evaluation["reason"] = ""
	return evaluation


## True when every cost key fits inside the stored resources. A missing
## resource field reads as 0 and an unknown cost key counts as
## unaffordable: the flow never guesses a price's affordability.
static func affordable(state: Variant, costs: Dictionary) -> bool:
	if state == null:
		return false
	for resource: Variant in costs:
		var field: Variant = COST_STATE_FIELDS.get(str(resource))
		if field == null:
			return false
		var resources: Variant = state.resources
		if int(resources.get(str(field))) < int(costs[resource]):
			return false
	return true


## "free" or "wood 30, cash 20" — the cost in stable resource order.
static func cost_text(costs: Dictionary) -> String:
	if costs.is_empty():
		return "free"
	var parts: Array = []
	for resource in COST_ORDER:
		if costs.has(resource):
			parts.append("%s %d" % [resource, int(costs[resource])])
	return ", ".join(parts)


## The cost beside the stored amounts ("wood 30 (have 2000)") or
## "free" — the display the spec requires against current resources.
static func cost_against_text(state: Variant, costs: Dictionary) -> String:
	if costs.is_empty():
		return "free"
	var parts: Array = []
	for resource in COST_ORDER:
		if not costs.has(resource):
			continue
		var field: Variant = COST_STATE_FIELDS.get(str(resource))
		var current := -1
		if field != null and state != null:
			var resources: Variant = state.resources
			current = int(resources.get(str(field)))
		parts.append("%s %d (have %d)"
			% [resource, int(costs[resource]), current])
	return ", ".join(parts)


## True when the footprint rect anchored at `cell` intersects any
## existing placement. Rects compare full footprints (a placement's own
## extent, not its anchor), so a candidate overlapping a large
## neighbour's body is occupied even when their anchors differ.
static func _overlaps(state: Variant, cell: Vector2i,
		footprint: Vector2i) -> bool:
	var target := Rect2i(cell, Vector2i(maxi(footprint.x, 1),
		maxi(footprint.y, 1)))
	for placement: Variant in state.placements:
		if placement == null:
			continue
		var other_cell: Vector2i = placement.cell
		var other_footprint: Vector2i = placement.footprint
		var other := Rect2i(other_cell, Vector2i(maxi(other_footprint.x, 1),
			maxi(other_footprint.y, 1)))
		if target.intersects(other):
			return true
	return false


## The house rejection envelope: names the condition, never evaluates.
static func _reject(message: String) -> Dictionary:
	return {"ok": false, "error": "[placement] preview rejected: " + message,
		"valid": false, "reason": "", "cells": [], "cost": {}}
