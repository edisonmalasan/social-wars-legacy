extends RefCounted
## The revival intent and its typed result (OpenSpec `godot-unit-behaviors`
## "A revival is a server-derived intent, and the client-supplied syringe is
## ignored" / "No syringe cost, and the committed syringes field is content
## only" / "No combat is resolved, and no placement validation is invented",
## design D2/D3/D5).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy branch takes `index`, `item_id`, `x`, `y` **and** `used_syringe`
## all from the client (`command.py:626-630`), which is the untrusted pattern
## `godot-building-move` and `godot-building-collect` already record.  This
## contract keeps the legacy *behaviour* and rejects the legacy *trust*: the
## request body carries **only** a player identifier and a cell, and the
## service derives the map key and the revived item id server-side.  So a
## client-supplied expectation can never become the post-execution proof.
##
## ## The ledger projection is DELEGATED, never re-derived (design D1)
##
## Every gate, every ledger shape, and every refusal is read from
## `unit_behaviors.gd`, which is the ONE place they exist.  This module
## preloads it and nothing else: no gate, no counter, and no refusal is written
## twice, so a surface, the hermetic suite, and the deterministic report cannot
## disagree about what the ledger is.
##
## ## The typed result lives here, not in `boot_data.gd`
##
## Every other GameApi result class is declared in `scripts/gameapi/boot_data.gd`
## and this line's task list does not own that file.  Rather than leave the
## result an untyped dictionary — which would break the "identical typed shapes
## by construction" property every other intent has — the class is declared
## HERE and both GameApi implementations return **this** type.  It reuses
## `BootData.Resources`, `BootData.PROTOCOL`, and `BootData`'s own integer and
## resource parsers, so the seven stored slots are read exactly as every other
## response reads them.
##
## ## No syringe cost, and the response never echoes the discarded argument (D3)
##
## `syringe.charged` is a constant `0` and `syringe.echoed` a constant
## `false`: `used_syringe` is bound from `args[4]` and **discarded**, and the
## committed `syringes` field it would be paid in has zero legacy consumers.
## The response's `syringe.committed_syringes_reported_as_content_only` carries
## the **committed content value** the service read, as content — never a
## price, never a charge.
##
## ## Purity
##
## This module holds no node, no clock, no request, and no transport.  It
## preloads the read-only `unit_behaviors.gd` projection and the shared
## `boot_data.gd` type module, so the same functions serve the client, the
## hermetic suite, and the deterministic report.

const UnitBehaviors = preload("res://scripts/units/unit_behaviors.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ---------------------------------------------------------------------------
# The intent's wire contract (design D2)
# ---------------------------------------------------------------------------

## Exactly the three keys the request carries.  There is deliberately **no**
## parameter through which a client could dictate a revived item id, a map key,
## a syringe count, a price, or a resource delta.
const INTENT_KEYS := ["user_id", "x", "y"]

## The keys a client might attach and the service **ignores**, named so a
## caller reading this module can see that each one changes nothing.
const INTENT_IGNORED_KEYS := [
	"item_id", "map_key", "index", "used_syringe", "syringe", "syringes",
	"price", "cost", "charge", "resources_changed", "vector", "resources",
	"reason", "resurrect_hero",
]

## The endpoint's two-part post-execution proof, as the client records it.  The
## second half — **every** stored resource unchanged — is what makes the
## no-syringe-cost claim non-tautological: a cost smuggled through a client's
## own resource vector would have to show up there, because legacy applies that
## vector BEFORE the branch (`command.py:40`, `engine.py:251-271`).
##
## Declared BEFORE `intent_record()`, which quotes it, because a constant may
## not forward-reference another one.
const PROOF_NOTE := ("THE POST-EXECUTION PROOF HAS TWO HALVES AND BOTH ARE "
	+ "CONTENT-INDEPENDENT. Half one: the revived ledger entry is GONE after a "
	+ "revival that reached zero, because engine.resurrect_hero DELETES the key "
	+ "at zero and never stores a zero. Half two: EVERY stored resource is "
	+ "unchanged — the FULL set of seven, never a selected subset — because the "
	+ "derived vector is neutral. Either half failing is a reported failure, "
	+ "not a success (design D3)")

const INTENT_NOTE := ("THE REVIVAL INTENT CARRIES ONLY AN IDENTIFIER AND A CELL. "
	+ "The request is {user_id, x, y} and nothing else: no map key, no item id, "
	+ "no syringe count, no price, and no resource delta is accepted, and every "
	+ "such key is IGNORED by the service. The map key is derived by resolving "
	+ "the addressed cell against the save's own placement rows and the revived "
	+ "item id from the player's own recorded ledger, so a client-supplied "
	+ "expectation can never become the post-execution proof (design D2)")

## The loopback endpoint path the live implementation dials.  Named here as the
## contract, NOT as transport: `legacy_v0_api.gd` is the only file allowed to
## reference an endpoint (the project-scope suite enforces that), so this is
## the documented path without any scheme or host.
const RESURRECT_PATH := "/v0/resurrect"

## The typed result of `resurrect_hero_town()`: the legacy result plus the
## authoritative superset — the **server-derived** map key and item id, both
## gates, the ledger as read BEFORE execution and re-read AFTER it, the
## addressed row's two placements, and the seven stored resources — or a
## structured failure with **no partial payload**.
class ResurrectResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field, so
	## tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The **service-derived** map key — the one whose row records the addressed
	## cell. `-1` on failure.
	var map_key := -1
	## The **service-derived** revived item id, taken from the player's own
	## recorded ledger. `-1` on failure. Never read from the request.
	var item_id := -1
	## The ledger count before and after the decrement, and whether the key was
	## **DELETED** at zero. `removed: false` is a real legacy outcome, not an
	## error: a count above `1` decrements and keeps its key.
	var count_before := 0
	var count_after := 0
	var removed := false
	## The addressed cell, echoed exactly as sent.
	var cell: Array = []
	## The item id that was STANDING at the addressed cell before execution,
	## reported so a caller can see that the revived unit is a different id from
	## the one it replaced — which is the recorded consequence of deriving the
	## revived id from the ledger. `-1` when the cell resolved to no row.
	var occupant_item_id := -1
	## The resolved ledger entry's own committed `resurrectable` and
	## `syringes` values, reported as **content only**.
	var committed_resurrectable: Variant = null
	var committed_syringes: Variant = null
	## Both gates as the service reported them.
	var gates: Array = []
	var gate_count := 0
	## The ledger as read BEFORE execution and re-read AFTER it, each entry
	## `{item_id, count}`.
	var ledger_before: Array = []
	var ledger_after: Array = []
	## The addressed key's row as read BEFORE execution and re-read AFTER it:
	## eight committed slots `[item, x, y, timestamp, orientation, store,
	## attr, player]`.
	var placement_before: Array = []
	var placement_after: Array = []
	## The syringe record: `charged` is a constant `0`, `echoed` a constant
	## `false`, and the committed `syringes` value travels beside them as
	## CONTENT ONLY.
	var syringe_charged := 0
	var syringe_discarded_argument := 0
	var syringe_echoed := true
	var syringe_note := ""
	## The recorded absence of placement validation, and the "no third gate"
	## statement, carried on every answer so a caller cannot read the two gates
	## as the only rules worth stating.
	var placement_validated := true
	var no_third_gate := ""
	## The three recorded refusals, as `{refusal, implemented, rule}`.
	var refusals: Array = []
	var clicks_to_build_boundary := ""
	var resources: BootData.Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for the revival intent (never a partial payload).
static func resurrect_failure(code: String, message: String) -> ResurrectResult:
	var result := ResurrectResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses a v0 revival envelope — success or structured error — into the typed
## result, fail-closed in both directions.  The rules mirror `parse_collection()`
## in the strictness they demand and in what they refuse: the envelope must be
## a JSON object reporting `ok: true`, the protocol must be the v0 one, the
## legacy result string must be `success`, `map_key` and `item_id` must be
## integers, `count_before` / `count_after` must be non-negative integers,
## `removed` must be a boolean statement, `cell` must be the two addressed
## integers, `gates` must be the reported gate records, both ledgers must be
## arrays, both placements must be the eight committed slots, `syringe` must
## report a zero charge and an **unechoed** discarded argument, `refusals` must
## carry the three recorded refusals, and `resources` must be the seven
## non-negative integers every other response carries.
##
## The response is the AUTHORITATIVE record of what the service did: the client
## applies `ledger_after`, `placement_after`, and `resources` **verbatim** and
## discards its own expectations even where the two disagree.
static func parse_resurrect(payload: Variant) -> ResurrectResult:
	if not (payload is Dictionary):
		return resurrect_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _resurrect_error(envelope)
	if str(envelope.get("protocol", "")) != BootData.PROTOCOL:
		return resurrect_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [BootData.PROTOCOL,
				str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return resurrect_failure("bad_response",
			"resurrection response did not report the legacy success result")
	var map_key: Variant = BootData._parse_int(envelope.get("map_key"))
	if map_key == null or int(map_key) < 0:
		return resurrect_failure("bad_response",
			"the resurrection response carries no non-negative map_key")
	var item_id: Variant = BootData._parse_int(envelope.get("item_id"))
	if item_id == null or int(item_id) < 1:
		return resurrect_failure("bad_response",
			"the resurrection response carries no revived item_id")
	var count_before: Variant = BootData._parse_int(envelope.get("count_before"))
	var count_after: Variant = BootData._parse_int(envelope.get("count_after"))
	if count_before == null or count_after == null or int(count_before) < 0 \
			or int(count_after) < 0:
		return resurrect_failure("bad_response",
			"the resurrection response carries no readable ledger counts")
	if envelope.get("removed") != true and envelope.get("removed") != false:
		return resurrect_failure("bad_response",
			"the resurrection response carries no boolean removed statement")
	var cell: Variant = envelope.get("cell")
	if not (cell is Array) or (cell as Array).size() != 2:
		return resurrect_failure("bad_response",
			"the resurrection response carries no two-slot addressed cell")
	var cell_x: Variant = BootData._parse_int((cell as Array)[0])
	var cell_y: Variant = BootData._parse_int((cell as Array)[1])
	if cell_x == null or cell_y == null:
		return resurrect_failure("bad_response",
			"the resurrection response's addressed cell is not two integers")
	var gates: Variant = envelope.get("gates")
	if not (gates is Array) or (gates as Array).is_empty():
		return resurrect_failure("bad_response",
			"the resurrection response carries no gate records")
	for gate: Variant in gates as Array:
		if not (gate is Dictionary):
			return resurrect_failure("bad_response",
				"a reported gate is not an object")
		if str((gate as Dictionary).get("source", "")) == "":
			return resurrect_failure("bad_response",
				"a reported gate names no source line")
	if int((gates as Array).size()) != UnitBehaviors.GATE_COUNT:
		return resurrect_failure("bad_response",
			"the resurrection response reports %d gates, not the %d the legacy "
				% [(gates as Array).size(), UnitBehaviors.GATE_COUNT]
				+ "helper evaluates")
	var ledger_before: Variant = envelope.get("ledger_before")
	var ledger_after: Variant = envelope.get("ledger_after")
	if not (ledger_before is Array) or not (ledger_after is Array):
		return resurrect_failure("bad_response",
			"the resurrection response carries no ledger on one side")
	var placement_before: Variant = envelope.get("placement_before")
	var placement_after: Variant = envelope.get("placement_after")
	if not _is_placement_row(placement_before) or not _is_placement_row(placement_after):
		return resurrect_failure("bad_response",
			"the resurrection response carries no eight-slot placement row on "
			+ "one side")
	var syringe: Variant = envelope.get("syringe")
	if not (syringe is Dictionary):
		return resurrect_failure("bad_response",
			"the resurrection response carries no syringe object")
	var syringe_body: Dictionary = syringe
	var charged: Variant = BootData._parse_int(syringe_body.get("charged"))
	if charged == null or int(charged) != 0:
		return resurrect_failure("bad_response",
			"the resurrection response charges a syringe, which no legacy branch "
			+ "does: `syringes` has zero consumers")
	if syringe_body.get("echoed") != false:
		return resurrect_failure("bad_response",
			"the resurrection response ECHOES the discarded `used_syringe` "
			+ "argument, which this contract refuses to do")
	var refusals: Variant = envelope.get("refusals")
	if not (refusals is Array) or (refusals as Array).size() != \
			UnitBehaviors.REFUSAL_COUNT:
		return resurrect_failure("bad_response",
			"the resurrection response does not carry the %d recorded refusals"
				% UnitBehaviors.REFUSAL_COUNT)
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return resurrect_failure("bad_response",
			"resurrection response carries no resources object")
	var resources := BootData._parse_resources(resources_raw)
	if resources == null:
		return resurrect_failure("bad_response",
			"resurrection resources are not seven non-negative integers")
	var result := ResurrectResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return resurrect_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.map_key = int(map_key)
	result.item_id = int(item_id)
	result.count_before = int(count_before)
	result.count_after = int(count_after)
	result.removed = bool(envelope.get("removed", false))
	result.cell = [int(cell_x), int(cell_y)]
	result.occupant_item_id = _optional_int(envelope.get("occupant_item_id"))
	result.committed_resurrectable = _optional_int(
		envelope.get("committed_resurrectable"))
	result.committed_syringes = _optional_int(envelope.get("committed_syringes"))
	result.gates = (gates as Array).duplicate(true)
	result.gate_count = (gates as Array).size()
	result.ledger_before = (ledger_before as Array).duplicate(true)
	result.ledger_after = (ledger_after as Array).duplicate(true)
	result.placement_before = (placement_before as Array).duplicate(true)
	result.placement_after = (placement_after as Array).duplicate(true)
	result.syringe_charged = 0
	result.syringe_discarded_argument = 0
	result.syringe_echoed = false
	result.syringe_note = str(syringe_body.get("note", ""))
	result.placement_validated = false
	result.no_third_gate = str(envelope.get("no_third_gate", ""))
	result.refusals = (refusals as Array).duplicate(true)
	result.clicks_to_build_boundary = str(envelope.get("clicks_to_build", ""))
	result.resources = resources
	return result


## The intent's wire contract as the evidence report records it: the exact key
## set, the ignored keys, the derivation that replaces them, and the
## content-independent two-part post-execution proof the endpoint requires.
static func intent_record() -> Dictionary:
	return {
		"keys": (INTENT_KEYS as Array).duplicate(),
		"ignored_keys": (INTENT_IGNORED_KEYS as Array).duplicate(),
		"note": INTENT_NOTE,
		"command": "resurrect_hero",
		"path": RESURRECT_PATH,
		"map_key_is": "server-derived from the addressed cell's own placement "
			+ "row (every row records its committed (x, y) in slots 1 and 2)",
		"item_id_is": "server-derived from the player's own recorded "
			+ "deadHeroes ledger, because the revived row is not on the map and "
			+ "the ledger is the only place a dead unit's identity survives",
		"used_syringe_is": "DISCARDED: bound from args[4] and never read again "
			+ "in the branch",
		"proof": PROOF_NOTE,
		"identical_typed_shapes": true,
	}


## The recorded client's own gate for offering a revival action: the projection
## must be **resolvable** and must hold at least one entry.  This is a
## presentation rule and NOT a third increment gate — the two increment gates
## are the legacy helper's own and `GATES` names exactly those two.  A caller
## that wants the server's own answer instead may always send the intent and
## let the service refuse it.
static func offers_revival(projection: Dictionary) -> bool:
	if not bool(projection.get("ok", false)):
		return false
	return int(projection.get("entry_count", 0)) > 0


## The whole recorded scope: what this module sends, what it never sends, and
## every refusal travelling with the answer.
static func scope_record() -> Dictionary:
	return {
		"intent": (INTENT_KEYS as Array).duplicate(),
		"delivered": [
			"a typed resurrection intent carrying only an identifier and a cell",
			"the typed result with the server-derived map key and item id, both "
				+ "gates, both ledgers, and both placements",
			"the ledger projection delegated to unit_behaviors.gd, never "
				+ "re-derived",
			"the two-part post-execution proof the endpoint requires",
		],
		"not_delivered": [
			"any syringe cost or resource movement",
			"any combat resolution: no damage, outcome, defence, hit, or life "
				+ "arithmetic",
			"any occupancy, bounds, type, or terrain check on the revived "
				+ "placement",
			"a reimplementation of clicks_to_build, whose counter is owned by "
				+ "godot-building-construction",
			"no executed-legacy fixture: the committed corpus holds no "
				+ "resurrectable row and manufacturing one is refused",
		],
		"first_of_its_kind": "the FIRST M8 line whose transaction is both "
			+ "server-derived and state-mutating since godot-unit-collection, "
			+ "and the first committed field in this project whose legacy "
			+ "consumer is a MUTATION OF PRIVATE STATE rather than a read",
	}


## The refusal record, read from the ONE module that owns every refusal.
static func refusal_record() -> Dictionary:
	var record := UnitBehaviors.refusal_record()
	record["syringe"] = {
		"charged": 0,
		"echoed": false,
		"discarded_argument": 0,
		"note": UnitBehaviors.SYRINGE_DISCARD_NOTE,
		"rule": UnitBehaviors.NO_SYRINGE_COST,
	}
	record["placement_validation_applied_by_the_client"] = false
	record["offers_revival_is_a_presentation_rule"] = true
	return record


## The whole ledger contract, as this module records it, delegated whole to the
## projection module.
static func ledger_record(projection: Dictionary) -> Dictionary:
	return UnitBehaviors.ledger_record(projection)


## Display: the revival readout, with every recorded absence beside the answer so
## "it cost nothing" can never be read as "nothing else was checked".
static func readout_text(result: ResurrectResult) -> String:
	var parts: Array = []
	if not result.ok:
		parts.append("no revival (%s): %s"
			% [result.error_code, result.error_message])
		return " | ".join(parts)
	parts.append("revived item %d at map key %d, cell (%d, %d)"
		% [result.item_id, result.map_key, int(result.cell[0]),
			int(result.cell[1])])
	parts.append("ledger %d -> %d, key %s"
		% [result.count_before, result.count_after,
			"DELETED at zero" if result.removed else "kept"])
	parts.append("gates: %d, and no third (player team 1; committed "
		% result.gate_count + "resurrectable greater than zero)")
	parts.append("no syringe charged and no resource moved; no combat resolved; "
		+ "the revived placement is not validated")
	return " | ".join(parts)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


## Whether a value is one committed placement row: eight slots, exactly.  A row
## of another length is never read as standing at any cell, which is the same
## rule the service's own cell resolution applies.
static func _is_placement_row(value: Variant) -> bool:
	return value is Array and (value as Array).size() == 8


## An integer field that is legitimately absent from a response, so an absent
## one reads as `-1` rather than `0`.
static func _optional_int(value: Variant) -> int:
	var parsed: Variant = BootData._parse_int(value)
	return -1 if parsed == null else int(parsed)


## The service's own structured error (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
static func _resurrect_error(envelope: Dictionary) -> ResurrectResult:
	var code := "bad_response"
	var message := "compatibility API reported an error"
	if envelope.get("ok") == false:
		var error: Variant = envelope.get("error")
		if error is Dictionary:
			code = str((error as Dictionary).get("code", code))
			message = str((error as Dictionary).get("message", message))
	elif envelope.get("ok") == null:
		return resurrect_failure("bad_response",
			"the resurrection response reports no `ok` statement")
	return resurrect_failure(code, message)
