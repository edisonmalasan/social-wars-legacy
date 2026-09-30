extends "res://tests/test_base.gd"
## Move suite (building-move, spec "Move flow" / "Addressable placements
## in typed town state").
##
## Scenarios:
##   helpers     the pure `move_flow` helpers: footprint cells, target
##               evaluation, the refusal vocabulary, and the fail-closed
##               envelope — no node, no request, no clock;
##   addressable the typed state's legacy keys: a positive-integer key is
##               the verbatim addressable index, a key that is not one
##               carries no index and is never coerced (design D7);
##   arming      the selection path offers a `Move` action for an
##               addressable placed building, pressing it arms the move in
##               its OWN UI-foundation slot, the overlay previews the
##               building's current footprint, and the picker's and the
##               shop's slots and state stay untouched (design D8);
##   refusals    every invalid target — out of grid, occupied by another
##               placement, the building's own cell, and an unaddressable
##               row — confirms locally with NO request, no state change,
##               and an explicit reason; the building's own cells never
##               block a target that overlaps only itself;
##   apply       one confirmed intent sends exactly one request and applies
##               ONLY the authoritative response: the same object
##               repositioned at (58,47) in depth order, the typed row
##               replaced by the response's persisted entry, the resources
##               and XP from the response, and the HUD re-read from them —
##               with the placement count unchanged;
##   failures    a structured failure (an index the service does not know)
##               and a transport failure (the refused loopback endpoint)
##               each surface their code with nothing moved and the HUD
##               unchanged;
##   no-request  the whole run issues no bootstrap request (the state
##               derives from the fixture in hand and the flow never
##               re-bootstraps).
##
## Uses the committed bootstrap and move fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-move` run is the `move-live`
## phase: one typed intent through the real Compatibility endpoint.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## probe-recorded against the committed move capture): Turret I, item 22,
## 1x1, at legacy map key "11" — its cell moves from (58,48) to (58,47),
## the placement count stays 40, and no resource changes.
const MOVED_ITEM := 22
const MOVED_SLOT := 11
const FROM_CELL := Vector2i(58, 48)
const TO_CELL := Vector2i(58, 47)
## The fresh save's placement count before and after the move.
const PLACEMENTS := 40
## An anchor outside the shared 0..99 grid.
const OUT_OF_GRID_CELL := Vector2i(150, 3)
## Wall I rows sit at (59,48) (key 9) and (58,49) (key 7): either is
## occupied by another placement, so a target anchored there is refused.
const OCCUPIED_CELL := Vector2i(59, 48)
## The free one-step neighbours of the Turret I in the fresh save.
const FREE_NEIGHBOUR := Vector2i(57, 48)
## An index the corpus and the double both do not know.
const UNKNOWN_INDEX := 9999

## Endpoint for the transport scenario: the `--gameapi-endpoint=` user
## argument (verify-boot passes a refused loopback port to every hermetic
## suite), else the project setting's loopback default. No hardcoded
## endpoint in this file — the project-scope scan restricts transport
## references to the legacy-v0 implementation.
const ARG_ENDPOINT := "--gameapi-endpoint="


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-move":
		# verify-boot's move-live phase: one typed intent through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response.
		# Everything else here is fixture-fake only.
		await _check_live_move()
		return
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	_check_helpers()
	_check_addressable(payload)
	await _check_flow(payload)
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# Pure helpers (spec "Move flow"; task 4.2)
# ---------------------------------------------------------------------------


## The pure helper surface, exercised without a node, a request, or a
## clock: the footprint rule, the reason vocabulary, the exclusion of the
## moving building's own cells, and the fail-closed envelope.
func _check_helpers() -> void:
	check_eq(MoveFlow.footprint_cells(FROM_CELL, Vector2i(1, 1)),
		[FROM_CELL], "a 1x1 footprint covers exactly its anchor cell")
	check_eq(MoveFlow.footprint_cells(Vector2i(51, 39), Vector2i(2, 2)), [
		Vector2i(51, 39), Vector2i(52, 39),
		Vector2i(51, 40), Vector2i(52, 40)],
		"a 2x2 footprint covers four cells in anchor order")
	# A zero or negative extent never collapses the footprint to nothing: a
	# single cell is the minimum, exactly as the placement flow's rule.
	check_eq(MoveFlow.footprint_cells(FROM_CELL, Vector2i(0, 0)),
		[FROM_CELL], "a degenerate footprint still covers its anchor cell")
	check_eq(MoveFlow.REASON_UNADDRESSABLE, "unaddressable",
		"the unaddressable reason is the documented name")
	check_eq(MoveFlow.REASON_OUT_OF_GRID, "out_of_grid",
		"the out-of-grid reason is the documented name")
	check_eq(MoveFlow.REASON_OCCUPIED, "occupied",
		"the occupied reason is the documented name")
	check_eq(MoveFlow.REASON_SAME_CELL, "same_cell",
		"the same-cell reason is the documented name")
	check_eq(MoveFlow.REASON_NO_SELECTION, "no_selection",
		"the no-selection reason is the documented name")

	# Structural failures: the house envelope, never an evaluation.
	var no_state: Dictionary = MoveFlow.preview(null, null, TO_CELL)
	check(not bool(no_state.get("ok", true)),
		"a missing state fails closed")
	check(str(no_state.get("error", "")).contains("town state"),
		"the rejection names the missing state")
	check_eq(no_state.get("reason", ""), MoveFlow.REASON_NO_SELECTION,
		"a missing state names the no-selection reason")
	check_eq(MoveFlow.preview({"placements": []}, null, TO_CELL).get("reason", ""),
		MoveFlow.REASON_NO_SELECTION,
		"a missing placement names the no-selection reason")

	# A minimal typed placement: the helpers read the typed instance, so a
	# plain bag never fabricates a target.
	var bag := {"item": MOVED_ITEM, "cell": FROM_CELL, "slot": MOVED_SLOT,
		"footprint": Vector2i.ONE}
	check(not bool(MoveFlow.preview({"placements": []}, bag,
			TO_CELL).get("ok", true)),
		"an untyped placement is refused (no guessing)")

	# The exclusion rule against a real two-placement state: a target that
	# overlaps ONLY the moving building is valid, and one that overlaps a
	# neighbour is not. Uses the typed Placement class through the town
	# parser (covered in `_check_flow`), so here only the shared footprint
	# and refusal text are asserted.
	check_eq(MoveFlow.refusal_text({}), "",
		"a structural rejection carries no refusal text")
	check_eq(MoveFlow.refusal_text({"ok": true, "valid": true}), "",
		"a valid target carries no refusal text")
	var occupied: Dictionary = {"ok": true, "valid": false,
		"reason": MoveFlow.REASON_OCCUPIED, "item": MOVED_ITEM,
		"cell": OCCUPIED_CELL}
	check(MoveFlow.refusal_text(occupied).contains("overlap"),
		"the occupied refusal text names the overlap")
	var same: Dictionary = {"ok": true, "valid": false,
		"reason": MoveFlow.REASON_SAME_CELL, "item": MOVED_ITEM,
		"cell": FROM_CELL}
	check(MoveFlow.refusal_text(same).contains("already sits at"),
		"the same-cell refusal text names the current cell")
	var grid: Dictionary = {"ok": true, "valid": false,
		"reason": MoveFlow.REASON_OUT_OF_GRID, "item": MOVED_ITEM,
		"cell": OUT_OF_GRID_CELL}
	check(MoveFlow.refusal_text(grid).contains("outside the town grid"),
		"the out-of-grid refusal text names the grid")
	var unaddressable: Dictionary = {"ok": true, "valid": false,
		"reason": MoveFlow.REASON_UNADDRESSABLE, "item": MOVED_ITEM,
		"cell": TO_CELL}
	check(MoveFlow.refusal_text(unaddressable).contains("no addressable"),
		"the unaddressable refusal text names the missing key")


# ---------------------------------------------------------------------------
# Addressable placements (design D7; task 4.1)
# ---------------------------------------------------------------------------


## The typed state's legacy keys over the committed fresh save: every row
## carries its key verbatim as the addressable index, and a key that is not
## a positive integer is recorded unaddressable instead of coerced — the
## central rule the whole move flow rests on.
func _check_addressable(payload: Variant) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	if not bool(registry.assets_loaded()):
		registry.load_asset_registry()
	var parsed: Dictionary = TownState.parse(payload, registry)
	check(bool(parsed.get("ok", false)),
		"the fresh fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]
	var slots := {}
	for placement: Variant in state.placements:
		slots[placement.slot] = true
		check(TownState.is_addressable(placement),
			"every fresh placement carries an addressable key")
		check(str(placement.slot_key) == str(placement.slot),
			"the recorded key text matches the index (%s)" \
				% str(placement.slot_key))
	check_eq(slots.size(), PLACEMENTS,
		"the 40 fresh rows carry 40 distinct addressable keys")
	var moved: Variant = _placement_by_slot(state, MOVED_SLOT)
	check(moved != null, "the moved building is addressable by key 11")
	if moved != null:
		check_eq(int(moved.item), MOVED_ITEM,
			"key 11 names Turret I (item 22)")
		check_eq(moved.cell, FROM_CELL,
			"the fresh save anchors it at (58,48)")
		check_eq(moved.footprint, Vector2i(1, 1),
			"Turret I is a 1x1 footprint")

	# The pure key rule, over the shapes a save could carry: a positive
	# integer (string or int) is the index verbatim; everything else is
	# unaddressable. Never coerced to a value that could name a real row.
	check_eq(TownState.slot_of("11"), 11, "a digit string is the index")
	check_eq(TownState.slot_of(11), 11, "an int key is the same index")
	check_eq(TownState.slot_of(1), 1, "index 1 is addressable")
	check_eq(TownState.slot_of("0"), null,
		"index 0 is not addressable (never a real legacy key)")
	check_eq(TownState.slot_of(0), null,
		"int key 0 is not addressable either")
	check_eq(TownState.slot_of("-1"), null,
		"a negative key is not addressable")
	check_eq(TownState.slot_of("mystery"), null,
		"a non-numeric key is not addressable")
	check_eq(TownState.slot_of(""), null,
		"an empty key is not addressable")
	check_eq(TownState.slot_of("1.5"), null,
		"a non-integer numeric key is not addressable")
	check_eq(TownState.slot_of(null), null,
		"a null key is not addressable")
	check_eq(TownState.slot_of({}), null,
		"a non-scalar key is not addressable")
	check_eq(TownState.NO_SLOT, -1,
		"the unaddressable sentinel is never a usable index")
	check(not TownState.is_addressable(null),
		"an absent placement is never addressable")
	check(not TownState.is_addressable({"slot": MOVED_SLOT}),
		"an untyped bag is never addressable (no guessing)")

	# A crafted payload with unusable keys: the rows still parse, render,
	# and keep their verbatim key — they are simply not movable, which is
	# the refusal the move flow surfaces (design D7).
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	var items: Dictionary = (crafted["map"] as Dictionary)["items"]
	items["mystery"] = [MOVED_ITEM, 20, 20, 0, 0, [], {}, 1]
	items["0"] = [MOVED_ITEM, 21, 20, 0, 0, [], {}, 1]
	items[""] = [MOVED_ITEM, 22, 20, 0, 0, [], {}, 1]
	items["-3"] = [MOVED_ITEM, 23, 20, 0, 0, [], {}, 1]
	var crafted_result: Dictionary = TownState.parse(crafted, registry)
	check(bool(crafted_result.get("ok", false)),
		"unusable keys do not fail the save: %s"
		% crafted_result.get("error"))
	if bool(crafted_result.get("ok", false)):
		var crafted_state: Variant = crafted_result["state"]
		check_eq(crafted_state.placements.size(), PLACEMENTS + 4,
			"every crafted row is kept, not dropped")
		var unaddressable_count := 0
		for placement: Variant in crafted_state.placements:
			if not TownState.is_addressable(placement):
				unaddressable_count += 1
				check(int(placement.slot) == TownState.NO_SLOT,
					"an unaddressable row carries the sentinel, not a guess")
				check(str(placement.slot_key) in
						["mystery", "0", "", "-3"],
					"an unaddressable row records its own key verbatim (%s)"
					% str(placement.slot_key))
		check_eq(unaddressable_count, 4,
			"all four unusable keys are recorded unaddressable")
		var mystery: Variant = _placement_by_key(crafted_state, "mystery")
		check(mystery != null and not TownState.is_addressable(mystery),
			"the 'mystery' row parses and renders but is not addressable")
		if mystery != null:
			check_eq(mystery.item, MOVED_ITEM,
				"the unaddressable row keeps its item verbatim")
			check_eq(mystery.cell, Vector2i(20, 20),
				"the unaddressable row keeps its cell verbatim")
		var still_movable: Variant = _placement_by_slot(crafted_state,
			MOVED_SLOT)
		check(still_movable != null and TownState.is_addressable(
				still_movable),
			"a usable key in the same save is still addressable")


## The committed placement carrying an addressable index (null when absent).
func _placement_by_slot(state: Variant, slot: int) -> Variant:
	for placement: Variant in state.placements:
		if placement != null and int(placement.slot) == slot:
			return placement
	return null


## The committed placement stored under a verbatim key (null when absent).
func _placement_by_key(state: Variant, key: String) -> Variant:
	for placement: Variant in state.placements:
		if placement != null and str(placement.slot_key) == key:
			return placement
	return null


# ---------------------------------------------------------------------------
# Move flow (spec "Move flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> preview -> confirm -> apply plus every refusal, failure, and
## no-request path.
func _check_flow(payload: Dictionary) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	if not bool(registry.assets_loaded()):
		registry.load_asset_registry()
	var info_payload: Variant = _fixture(PLAYER_FIXTURE)
	check(info_payload is Dictionary, "the player fixture parses as JSON")
	if not (info_payload is Dictionary):
		return
	var parsed: Dictionary = TownState.parse(info_payload, registry)
	check(bool(parsed.get("ok", false)),
		"the fresh fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]
	check_eq(state.placements.size(), PLACEMENTS,
		"the fresh save starts with 40 placements")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the move save")
	if not (listing is BootData.SaveListResult):
		return
	check(not (listing as BootData.SaveListResult).saves.is_empty(),
		"the save list carries a save")
	if (listing as BootData.SaveListResult).saves.is_empty():
		return
	var pid := str((listing as BootData.SaveListResult).saves[0].id)
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = state.summary.name
	summary.level = state.summary.level
	summary.xp = state.summary.xp
	var activation: Dictionary = session.activate(pid, summary)
	check(bool(activation.get("ok", false)),
		"the session activates the save: %s" % activation.get("error"))
	if not bool(activation.get("ok", false)):
		return

	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)), "town builds: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	check_eq(town.objects.size(), PLACEMENTS,
		"the fresh save renders 40 objects before any move")

	var requests_start: int = api.move_requests
	var snapshot_start := _state_snapshot(state)
	_check_selection_arming(town, state, api, requests_start)
	_check_refused_targets(town, state, api, requests_start, snapshot_start)
	_check_cancelled_move(town, state, api, requests_start, snapshot_start)
	await _check_applied_response(town, state, api)
	await _check_structured_failure(town, state, api)
	await _check_transport_failure(town, state, api)
	check_eq(api.move_requests, requests_start + 3,
		"the whole flow issued exactly three requests (success, structured "
		+ "failure, transport failure); every other check sent none")
	town.free()

	# The unaddressable refusal runs on its own town so the applied state of
	# the main flow stays intact for the counts above.
	await _check_unaddressable_refusal(state, registry, api, session,
		pid, summary)


## Arming from the delivered selection path (design D8): a press selects the
## placed building, the move surface offers a `Move` action in its OWN
## slot, pressing it arms the move, the overlay previews the building's
## CURRENT footprint, and the picker's and the shop's slots and state are
## untouched (a regression there stays visible in their own suites).
func _check_selection_arming(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.move_active(), "the move is not armed before a selection")
	check(not town.move_selection_available(),
		"no selection means no move action")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(FROM_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), MOVED_ITEM,
		"the press at (58,48) selects Turret I")
	check(town.move_selection_available(),
		"an addressable selection offers the move action")
	check(town.ui.has_slot("move"),
		"the move surface owns its own UI-foundation slot (design D8)")
	check(town.ui.is_slot_visible("move"),
		"the move slot shows for a committed selection")
	# Design D8: neither delivered surface is armed or altered.
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	check(not town.shop_active(), "a selection never arms the shop")

	var panel: Variant = _move_panel(town)
	check(panel != null, "the move panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var arm_button: Variant = _button_named(panel_node, "move")
	check(arm_button != null, "the move action button exists")
	if arm_button is Button:
		check(not (arm_button as Button).disabled,
			"the move action is enabled for an addressable selection")
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before the move is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_move_status(town)).contains("press Move"),
		"the status names the selection and the action")

	# The button wiring arms the move (the signal path, one `pressed`
	# emission = one arm — no request).
	if arm_button != null:
		(arm_button as Button).pressed.emit()
	check(town.move_active(), "pressing the action arms the move")
	check_eq(town.move_slot(), MOVED_SLOT,
		"the armed move names the building's legacy key 11")
	check_eq(town.move_placement().cell, FROM_CELL,
		"the armed placement is the one at (58,48)")
	check(town.move_preview_shown(),
		"the overlay previews the building's current footprint")
	check_eq(town.move_preview_cells(), [FROM_CELL],
		"the armed preview covers the building's own cell")
	check(town.move_preview_valid(),
		"the armed preview is marked valid (it is where the building is)")
	check(town.ui.is_slot_visible("move"),
		"the move slot stays visible while armed")
	check(String(_move_status(town)).contains("armed"),
		"the status names the armed building")
	# The move requires NO purchase (spec "Moving SHALL NOT require or
	# perform a purchase"), and the derived price vector is neutral, so the
	# panel says so rather than showing a price.
	var selection_text := _move_selection_text(town)
	check(selection_text.contains("free"),
		"the panel states the derived neutral price (no purchase)")
	check(selection_text.contains("derived, never observed"),
		"the panel marks the price as derived, never observed")
	check_eq(api.move_requests, requests_before,
		"arming sent no request")

	# A second arm is refused by name: the move surface never stacks.
	var again: Dictionary = town.arm_move()
	check(not bool(again.get("ok", true)),
		"arming an already-armed move rejects")
	check_eq(str(again.get("code", "")), "move_already_active",
		"the double-arm names the condition")


## Every invalid target confirms locally: no request, no state change, and
## the explicit error names `invalid_target` with the failed gate (design
## D5: the client owns these gameplay rules; the endpoint enforces only
## structural validity).
func _check_refused_targets(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# out_of_grid: the anchor lies outside the shared 0..99 grid.
	var target_out: Dictionary = town.preview_move_cell(OUT_OF_GRID_CELL)
	check_eq(str(target_out.get("reason", "")),
		MoveFlow.REASON_OUT_OF_GRID,
		"an anchor outside the grid previews out_of_grid")
	check(not bool(target_out.get("valid", true)),
		"the out-of-grid target previews invalid")
	check(not town.move_preview_valid(),
		"the overlay marks the out-of-grid target invalid")
	check(town.move_preview_shown(),
		"the invalid target stays visible so its reason reads")
	var confirm_out: Dictionary = await town.confirm_move()
	check(not bool(confirm_out.get("ok", true)),
		"confirming the out-of-grid target fails")
	check_eq(str(confirm_out.get("code", "")), "invalid_target",
		"the out-of-grid confirm names invalid_target: %s"
		% confirm_out.get("error"))
	check(String(confirm_out.get("error", "")).contains("outside the town grid"),
		"the explicit error carries the failed gate")
	check_eq(api.move_requests, requests_before,
		"the out-of-grid target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the out-of-grid attempt changes no state")

	# occupied: the target covers a Wall I row (key 9, at (59,48)).
	var target_occupied: Dictionary = town.preview_move_cell(OCCUPIED_CELL)
	check_eq(str(target_occupied.get("reason", "")), MoveFlow.REASON_OCCUPIED,
		"a cell another placement occupies previews occupied")
	check(not town.move_preview_valid(),
		"the overlay marks the occupied target invalid")
	var confirm_occupied: Dictionary = await town.confirm_move()
	check_eq(str(confirm_occupied.get("code", "")), "invalid_target",
		"the occupied confirm names invalid_target: %s"
		% confirm_occupied.get("error"))
	check(String(confirm_occupied.get("error", "")).contains("overlap"),
		"the explicit error carries the failed gate")
	check_eq(api.move_requests, requests_before,
		"the occupied target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the occupied attempt changes no state")

	# same_cell: the building already sits at (58,48) — a no-op the flow
	# refuses rather than sending.
	var target_same: Dictionary = town.preview_move_cell(FROM_CELL)
	check_eq(str(target_same.get("reason", "")), MoveFlow.REASON_SAME_CELL,
		"the building's own cell previews same_cell")
	var confirm_same: Dictionary = await town.confirm_move()
	check_eq(str(confirm_same.get("code", "")), "invalid_target",
		"the same-cell confirm names invalid_target: %s"
		% confirm_same.get("error"))
	check(String(confirm_same.get("error", "")).contains("already sits at"),
		"the explicit error carries the failed gate")
	check_eq(api.move_requests, requests_before,
		"the no-op target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the no-op attempt changes no state")

	# The building's OWN cell never blocks it (spec "The building's own
	# cells do not block it"): the other free one-step neighbour, (57,48),
	# is adjacent to the wall at (58,49) but overlaps nothing, so it
	# previews valid.
	var target_neighbour: Dictionary = town.preview_move_cell(FREE_NEIGHBOUR)
	check_eq(str(target_neighbour.get("reason", "")), "",
		"a free neighbour names no refusal")
	check(bool(target_neighbour.get("valid", false)),
		"a free in-grid neighbour previews valid")
	check_eq(target_neighbour.get("cells", []), [FREE_NEIGHBOUR],
		"the 1x1 preview covers exactly the target cell")
	check(town.move_preview_valid(),
		"the overlay marks the free neighbour valid")

	# A no-target confirm (after the evaluation was cleared) refuses too.
	var cleared: Dictionary = town.preview_move_cell(TO_CELL)
	check(bool(cleared.get("valid", false)),
		"the recorded target (58,47) previews valid")


## A cancelled move drops only mode-local state: selection, serialized town
## state, resources, and the request count stay byte-identical, and
## re-arming after a re-select works.
func _check_cancelled_move(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	var selected_before: int = town.selection_legacy_id()
	var cancelled: Dictionary = town.cancel_move()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the move: %s" % cancelled.get("error"))
	check(not town.move_active(), "the move closes")
	check(town.move_placement() == null, "the moving placement drops")
	check(not town.move_preview_shown(), "the overlay drops on cancel")
	check_eq(town.move_preview_cells().size(), 0,
		"no preview cells survive cancel")
	check(not town.ui.is_slot_visible("move"),
		"the move slot hides on cancel")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.move_requests, requests_before, "cancel sent no request")
	var again: Dictionary = town.cancel_move()
	check(not bool(again.get("ok", true)),
		"closing an already-closed move rejects")
	check_eq(str(again.get("code", "")), "move_not_active",
		"the double-close names the condition")
	var confirm_closed: Dictionary = await town.confirm_move()
	check(not bool(confirm_closed.get("ok", true)),
		"a closed move refuses a confirm")
	check_eq(api.move_requests, requests_before,
		"the closed-move refusal sent no request")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: the SAME rendered object sits at (58,47) in depth
## order, the typed row is the response's persisted entry, the placement
## count is unchanged, the resources and XP take the response's values, and
## the HUD re-reads from them — the move surface itself stays armed.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	var object: Variant = null
	for candidate: Variant in town.objects:
		if candidate != null and int(candidate.legacy_id) == MOVED_ITEM \
				and candidate.cell == FROM_CELL:
			object = candidate
	check(object != null, "the Turret I object is committed before the move")
	if object == null:
		return
	var armed: Dictionary = town.arm_move()
	check(bool(armed.get("ok", false)),
		"the move re-arms for the confirmed intent: %s" % armed.get("error"))
	var target: Dictionary = town.preview_move_cell(TO_CELL)
	check(bool(target.get("valid", false)),
		"the recorded target previews valid")
	var requests_before: int = api.move_requests
	var snapshot_before := _state_snapshot(state)
	var confirmed: Dictionary = await town.confirm_move()
	check(bool(confirmed.get("ok", false)),
		"the confirmed move succeeds: %s" % confirmed.get("error"))
	check_eq(api.move_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	var typed_success: Variant = confirmed.get("result")
	check(typed_success is BootData.PlacementResult,
		"the success envelope carries the typed placement result")
	if typed_success is BootData.PlacementResult:
		check_eq((typed_success as BootData.PlacementResult).result,
			"success", "the legacy result string is verbatim")
		var entry: BootData.Placement = \
			(typed_success as BootData.PlacementResult).placement
		check(entry != null, "the response carries the persisted entry")
		if entry != null:
			check_eq(entry.item_id, MOVED_ITEM,
				"the response's entry names Turret I")
			check_eq(entry.x, TO_CELL.x, "the response's entry carries x=58")
			check_eq(entry.y, TO_CELL.y, "the response's entry carries y=47")

	# The authoritative apply: counts, cell, row, depth order, resources.
	check_eq(state.placements.size(), PLACEMENTS,
		"a move rewrites one row: the placement count is unchanged")
	check_eq(town.objects.size(), PLACEMENTS,
		"a move repositions one object: the object count is unchanged")
	var moved: Variant = _placement_by_slot(state, MOVED_SLOT)
	check(moved != null, "the moved placement is still addressable")
	if moved is TownState.Placement:
		check_eq(moved.cell, TO_CELL, "the typed row sits at (58,47)")
		check_eq(int(moved.item), MOVED_ITEM,
			"the typed row keeps its item")
		check_eq(moved.raw, [MOVED_ITEM, TO_CELL.x, TO_CELL.y, 0, 0, [], {},
			1], "the typed raw row is the response's persisted entry")
		check_eq(moved.footprint, Vector2i(1, 1),
			"the content footprint is unchanged")
	check_eq(object.cell, TO_CELL,
		"the SAME rendered object repositions to (58,47)")
	check_eq(object.position, Iso.footprint_rect(TO_CELL, 1, 1).position,
		"the object is repositioned through the shared projection")
	check_eq(int(object.legacy_id), MOVED_ITEM,
		"the repositioned object is still Turret I")
	var rendered_at_old := false
	for candidate: Variant in town.objects:
		if candidate != null and candidate.cell == FROM_CELL \
				and int(candidate.legacy_id) == MOVED_ITEM:
			rendered_at_old = true
	check(not rendered_at_old,
		"no object renders the Turret I at its old cell")
	var previous_depth := -1
	var depth_ordered := true
	for candidate: Variant in town.objects:
		var depth := Iso.depth_key(candidate.cell)
		if depth < previous_depth:
			depth_ordered = false
		previous_depth = depth
	check(depth_ordered,
		"objects keep non-decreasing isometric depth after the apply")
	# The neutral price vector means no resource changes at all: the report
	# and the apply both take the response's values verbatim.
	check_eq(state.resources.coins, 2000, "coins follow the response")
	check_eq(state.resources.wood, 2000, "wood follows the response")
	check_eq(state.resources.steel, 2000, "steel follows the response")
	check_eq(state.resources.oil, 2000, "oil follows the response")
	check_eq(state.resources.cash, 5, "cash follows the response")
	check_eq(state.resources.mana, 0, "mana follows the response")
	check_eq(state.summary.xp, 4, "xp follows the response")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("gold"), "2000",
			"the HUD renders the authoritative primary currency")
		check_eq(hud.displayed("xp"), "4", "the HUD renders xp verbatim")
	check_eq(town.move_error, "", "success leaves no failure record")
	check(not town.move_preview_shown(),
		"the overlay drops after a successful apply")
	check(town.move_active(), "the move surface stays armed after the apply")
	check_eq(town.move_placement().cell, TO_CELL,
		"the armed placement now sits at (58,47)")
	check(String(_move_status(town)).contains("moved"),
		"the status names the completed move")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")


## The structured failure: the intent goes out naming an index the service
## does not know, the explicit error names `unknown_item_index`, and no
## state, object, or HUD value changes (the same no-mutation contract as a
## refused target).
func _check_structured_failure(town: Node2D, state: Variant,
		api: Variant) -> void:
	var snapshot_before := _state_snapshot(state)
	var requests_before: int = api.move_requests
	# A fresh town holding one row under an index the corpus does not know:
	# the client's state is stale relative to the service, the exact failure
	# mode design D3/D5 calls out.
	var town2: Variant = _town_with_extra_row(api)
	if town2 == null:
		return
	var armed: Dictionary = town2.arm_move()
	check(bool(armed.get("ok", false)),
		"the extra row arms a move: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(town2.move_slot(), UNKNOWN_INDEX,
			"the armed move names the unknown index")
		var target: Dictionary = town2.preview_move_cell(TO_CELL)
		check(bool(target.get("valid", false)),
			"a free target previews valid for the unknown-index row")
		var failed: Dictionary = await town2.confirm_move()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s" \
				% failed.get("error"))
		check(town2.move_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check(_state_snapshot(town2.state) != "",
			"the failing town still holds its state")
		check_eq(town2.objects.size(), PLACEMENTS + 1,
			"the structured failure renders nothing")
		var ghost_cell: Vector2i = town2.move_placement().cell
		check_eq(ghost_cell, Vector2i(20, 20),
			"the unknown-index row stays at its own cell")
	town2.free()
	check_eq(api.move_requests, requests_before + 1,
		"the failed intent still sent exactly once")
	check_eq(_state_snapshot(state), snapshot_before,
		"the structured failure changes no state of the main flow")


## A second town whose state carries one extra row under an index neither
## the corpus nor the fake double knows (stale client state). It reuses the
## SAME parsed fresh save plus that row, so no fixture is written.
func _town_with_extra_row(api: Variant) -> Variant:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	if registry == null:
		return null
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[
		str(UNKNOWN_INDEX)] = [MOVED_ITEM, 20, 20, 0, 0, [], {}, 1]
	var parsed: Dictionary = TownState.parse(crafted, registry)
	if not bool(parsed.get("ok", false)):
		return null
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		town.free()
		return null
	# The extra row's object is selected through the delivered press path.
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(Vector2i(20, 20)))
	if not bool(pressed.get("ok", false)) or town.selection_legacy_id() \
			!= MOVED_ITEM:
		town.free()
		return null
	return town


## LAST scenario (it waits out the refused loopback endpoint): the intent
## goes out over the legacy transport, the endpoint refuses it, and the
## explicit error names `unreachable_endpoint` with nothing moved and no
## resource changed (the same no-mutation contract as a structured
## failure).
func _check_transport_failure(town: Node2D, state: Variant,
		api: Variant) -> void:
	# The surface is still armed from the successful apply (a move leaves it
	# armed, exactly as a placement leaves the picker open), so no re-arm is
	# needed or permitted here.
	check(town.move_active(),
		"the move surface is still armed for the transport scenario")
	var target: Dictionary = town.preview_move_cell(FREE_NEIGHBOUR)
	check(bool(target.get("valid", false)),
		"a valid target exists before the transport attempt")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.move_requests
	var snapshot_before := _state_snapshot(state)
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_move()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.move_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.move_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the transport failure renders nothing")
	check(town.move_active(),
		"the move surface survives the transport failure")
	# The last state-changing check ran against the fake, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The unaddressable-row refusal (design D7): a row whose save key is not a
## positive integer parses, renders, and is selectable, but the move action
## is unavailable, arming is refused by name, and NOTHING is sent — the
## index is never coerced, because a coerced index would address a
## different row.
func _check_unaddressable_refusal(state: Variant, registry: Variant,
		api: Variant, session: Variant, pid: String,
		summary: BootData.PlayerSummary) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		MOVED_ITEM, 20, 20, 0, 0, [], {}, 1]
	var parsed: Dictionary = TownState.parse(crafted, registry)
	check(bool(parsed.get("ok", false)),
		"the unaddressable fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	check(bool(built.get("ok", false)), "the unaddressable town builds")
	if not bool(built.get("ok", false)):
		town.free()
		return
	var requests_before: int = api.move_requests
	var snapshot_before := _state_snapshot(town.state)
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(Vector2i(20, 20)))
	check(bool(pressed.get("ok", false)),
		"the unaddressable row is selectable: %s" % pressed.get("error"))
	check_eq(town.selection_legacy_id(), MOVED_ITEM,
		"the unaddressable row is the committed selection")
	check(not town.move_selection_available(),
		"an unaddressable row never offers the move action")
	var panel: Variant = _move_panel(town)
	if panel != null:
		var arm_button: Variant = _button_named(panel as Node, "move")
		check(arm_button is Button and (arm_button as Button).disabled,
			"the move action is disabled for an unaddressable row")
		check(String(_move_status(town)).contains("not movable"),
			"the status names the unaddressable refusal")
	var refused: Dictionary = town.arm_move()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the unaddressable reason: %s" \
			% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check(not town.move_active(), "no move mode opens for an unaddressable row")
	check_eq(api.move_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The live-move scenario (verify-boot's move-live phase): one typed
## intent through the real Compatibility endpoint, so the unchanged legacy
## `command()` executes the `move` branch over the disposable corpus. This
## side asserts the documented typed response; the phase harness separately
## asserts the corpus save file mutated. No fixture is touched.
func _check_live_move() -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the live phase")
	if endpoint == "":
		return
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	api.configure("legacy_v0", endpoint)
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the corpus save list resolves")
	if not (listing as BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)
	var moved: Variant = await api.move_building(pid, MOVED_SLOT, TO_CELL.x,
		TO_CELL.y)
	check(moved is BootData.PlacementResult,
		"the live move returns a typed result")
	if not (moved is BootData.PlacementResult):
		return
	var typed := moved as BootData.PlacementResult
	check(typed.ok, "the live move succeeds: %s / %s" % [
		typed.error_code, typed.error_message])
	if not typed.ok or typed.placement == null or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live move protocol is compat-v0")
	check_eq(typed.result, "success",
		"the legacy result string is verbatim")
	check_eq(typed.placement.item_id, MOVED_ITEM,
		"the live entry names Turret I")
	check_eq(typed.placement.x, TO_CELL.x, "the live entry carries x=58")
	check_eq(typed.placement.y, TO_CELL.y, "the live entry carries y=47")
	check_eq(typed.placement.player, 1,
		"the live entry keeps the player's team field")
	check(typed.placement.timestamp >= 0,
		"the live entry carries the row's (unchanged) timestamp field")
	# The derived price vector is neutral, so nothing in the resource bag
	# moves (design D2): the live response must equal the fresh save.
	check_eq(typed.resources.xp, 4, "xp follows the response")
	check_eq(typed.resources.gold, 2000, "gold follows the response")
	check_eq(typed.resources.wood, 2000, "wood follows the response")
	check_eq(typed.resources.oil, 2000, "oil follows the response")
	check_eq(typed.resources.steel, 2000, "steel follows the response")
	check_eq(typed.resources.cash, 5, "cash follows the response")
	check_eq(typed.resources.mana, 0, "mana follows the response")
	# A stale index fails closed with the endpoint's own code rather than
	# reporting a success for a move that never happened.
	var unknown: Variant = await api.move_building(pid, UNKNOWN_INDEX,
		TO_CELL.x, TO_CELL.y)
	check(unknown is BootData.PlacementResult,
		"the live unknown index returns the typed result")
	if unknown is BootData.PlacementResult:
		var failure: BootData.PlacementResult = unknown
		check(not failure.ok, "the live unknown index is a structured failure")
		check_eq(failure.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(failure.placement == null and failure.resources == null,
			"the live structured failure carries no partial payload")
	print("[test] live-move applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [MOVED_SLOT, TO_CELL.x, TO_CELL.y, typed.resources.xp,
			typed.resources.gold])


## The town state derives from the fixture in hand: this whole run must not
## issue a bootstrap request.
func _check_no_second_bootstrap_request() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	check_eq(int(api.bootstrap_requests), 0,
		"no bootstrap request was issued (the fixture in hand suffices)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## The move panel's VBox inside the move slot root (null before the first
## selection or when the slot never registered).
func _move_panel(town: Variant) -> Variant:
	if not town.ui.has_slot("move"):
		return null
	var slot: Control = town.ui.slot_root("move")
	if slot == null or slot.get_child_count() == 0:
		return null
	return slot.get_child(0)


## The named button anywhere inside the move panel (the action row nests the
## arm/confirm/cancel trio), or null.
func _button_named(panel: Node, button_name: String) -> Variant:
	for child: Variant in panel.get_children():
		if child is Button and String((child as Button).name) == button_name:
			return child
		if child is Node:
			var nested: Variant = _button_named(child as Node, button_name)
			if nested != null:
				return nested
	return null


## The on-screen status line text ("" before a panel exists).
func _move_status(town: Variant) -> String:
	var panel: Variant = _move_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "status":
			return (child as Label).text
	return ""


## The on-screen selection line text ("" before a panel exists).
func _move_selection_text(town: Variant) -> String:
	var panel: Variant = _move_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "selection":
			return (child as Label).text
	return ""


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-move and failure paths).
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


## Loads a repository-relative JSON fixture as parsed text (read-only).
func _fixture(relative: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_bytes(
		Paths.repo_root().path_join(relative)).get_string_from_utf8())
