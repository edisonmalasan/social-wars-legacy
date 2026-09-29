extends "res://tests/test_base.gd"
## Sell suite (building-sell, spec "Sell flow" / "Sell through either
## implementation").
##
## Scenarios:
##   gating      the selection-driven surface offers a `Sell` action only
##               for a selected, ADDRESSABLE placed building, pressing it
##               arms the sale in the same UI-foundation slot the move uses
##               (design D8 — no third panel, no grid target), and neither
##               delivered mode's behavior changes;
##   refusals    an unaddressable legacy key is refused by name with NO
##               request, the sale and the move never stack, and a selection
##               that no longer names the armed building refuses the confirm
##               instead of silently re-targeting it;
##   cancel      a cancelled sale sends nothing and leaves the town
##               byte-identical;
##   apply       one confirmed intent sends exactly one request and applies
##               ONLY the authoritative response: the typed placement gone,
##               its rendered object freed, the remaining objects keeping the
##               committed depth order, the resources and XP from the
##               response, and the HUD re-read from them — with the
##               placement and object counts falling by exactly one;
##   failures    a stale index the service does not know (`unknown_item_index`
##               — the endpoint's 404, resolved before execution) and a
##               transport failure (the refused loopback endpoint) each
##               surface their code with the building still on the map and the
##               HUD unchanged;
##   no-request  the whole run issues no bootstrap request (the state
##               derives from the fixture in hand and the flow never
##               re-bootstraps).
##
## Uses the committed bootstrap and sell fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-sell` run is the `sell-live`
## phase: one typed intent through the real Compatibility endpoint.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## probe-recorded against the committed sell capture): Turret I, item 22,
## 1x1, at legacy map key "20" — its cell `(41,48)`, the row
## `[22, 41, 48, 0, 0, [], {}, 1]` — the placement count falls from 40 to
## 39, and no resource changes.
const SOLD_ITEM := 22
const SOLD_SLOT := 20
const SOLD_CELL := Vector2i(41, 48)
## The pre-execution row the executed legacy transaction removed.
const SOLD_ROW := [SOLD_ITEM, 41, 48, 0, 0, [], {}, 1]
## The fresh save's placement count before and after the sale.
const PLACEMENTS := 40
## An index the corpus and the double both do not know (a stale client state
## after some other row was already removed).
const UNKNOWN_INDEX := 9999
## The cell the extra-row scenario parks the unknown-index row at.
const GHOST_CELL := Vector2i(20, 20)
## A second, still-present addressable building used for the transport
## scenario after the sale: the Turret I at legacy key 11, cell (58,48).
const SPARE_CELL := Vector2i(58, 48)
const SPARE_SLOT := 11

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
	if scenario == "live-sell":
		# verify-boot's sell-live phase: one typed intent through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response.
		# Everything else here is fixture-fake only.
		await _check_live_sell()
		return
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	await _check_flow(payload)
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# Sell flow (spec "Sell flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> confirm -> apply plus every refusal, failure, and no-request path.
func _check_flow(payload: Dictionary) -> void:
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
	check_eq(state.placements.size(), PLACEMENTS,
		"the fresh save starts with 40 placements")
	var sold: Variant = _placement_by_slot(state, SOLD_SLOT)
	check(sold != null, "the sold building is addressable by key 20")
	if sold != null:
		check_eq(int(sold.item), SOLD_ITEM, "key 20 names Turret I (item 22)")
		check_eq(sold.cell, SOLD_CELL, "the fresh save anchors it at (41,48)")
		check_eq(sold.footprint, Vector2i(1, 1), "Turret I is a 1x1 footprint")
		check_eq(_typed_row(sold.raw), SOLD_ROW,
			"the row is the pre-execution row the fixture removed")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the sell save")
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
		"the fresh save renders 40 objects before any sale")

	var requests_start: int = api.sell_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	_check_cancelled_sale(town, state, api, requests_start, snapshot_start)
	await _check_applied_response(town, state, api)
	await _check_unknown_index(registry, api)
	await _check_transport_failure(town, state, api)
	check_eq(api.sell_requests, requests_start + 3,
		"the whole flow issued exactly three requests (success, structured "
		+ "failure, transport failure); every other check sent none")
	town.free()

	# The unaddressable refusal runs on its own town so the applied state of
	# the main flow stays intact for the counts above.
	await _check_unaddressable_refusal(state, registry, api, session,
		pid, summary)


## The selection-driven surface offers `Sell` beside `Move` for a selected,
## addressable placed building, and pressing it arms the sale in the SAME
## slot the move surface uses (design D8: no third panel, no grid target,
## and neither delivered mode is altered).
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.sell_active(), "the sale is not armed before a selection")
	check(not town.sell_selection_available(),
		"no selection means no sell action")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SOLD_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), SOLD_ITEM,
		"the press at (41,48) selects Turret I")
	check(town.sell_selection_available(),
		"an addressable selection offers the sell action")
	check(town.move_selection_available(),
		"the same selection still offers the delivered move action")
	check(town.ui.has_slot("move"),
		"the selection-driven surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("move"),
		"the surface slot shows for a committed selection")
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	check(not town.shop_active(), "a selection never arms the shop")
	check(not town.move_active(),
		"a selection alone never arms the delivered move mode")

	var panel: Variant = _surface_panel(town)
	check(panel != null, "the selection-driven panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var sell_button: Variant = _button_named(panel_node, "sell")
	check(sell_button is Button, "the sell action button exists")
	if sell_button is Button:
		check(not (sell_button as Button).disabled,
			"the sell action is enabled for an addressable selection")
		check_eq((sell_button as Button).text, "Sell",
			"the action is labelled Sell")
	var move_button: Variant = _button_named(panel_node, "move")
	check(move_button is Button and not (move_button as Button).disabled,
		"the delivered move action is still enabled beside it")
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before a sale is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_surface_status(town)).contains("press Move"),
		"the unarmed status line is the delivered one, unchanged")

	# The button wiring arms the sale (the signal path, one `pressed`
	# emission = one arm — no request).
	if sell_button != null:
		(sell_button as Button).pressed.emit()
	check(town.sell_active(), "pressing the action arms the sale")
	check_eq(town.sell_slot(), SOLD_SLOT,
		"the armed sale names the building's legacy key 20")
	check_eq(town.sell_placement().cell, SOLD_CELL,
		"the armed placement is the one at (41,48)")
	check(town.ui.is_slot_visible("move"),
		"the surface slot stays visible while armed")
	check(String(_surface_status(town)).contains("armed"),
		"the status names the armed sale")
	check(String(_surface_status(town)).contains("refund: none claimed"),
		"the status names the no-refund claim limit")
	check(String(_surface_selection_text(town)).contains("refund: none claimed"),
		"the selection line states the no-refund derivation boundary")
	# A sale has NO grid target, so no footprint preview is displayed.
	check(not town.move_preview_shown(),
		"an armed sale shows no footprint preview (it has no target)")
	check(town.move_evaluation().is_empty(),
		"an armed sale commits no move evaluation")
	check_eq(api.sell_requests, requests_before, "arming sent no request")
	# The delivered move action is unavailable while a sale is armed: the
	# two modes share one surface and never stack. Arming REBUILDS the panel
	# (the delivered attach precedent), so it is re-read here.
	var armed_panel: Variant = _surface_panel(town)
	var move_while_selling: Variant = _button_named(
		armed_panel as Node, "move")
	if move_while_selling is Button:
		check((move_while_selling as Button).disabled,
			"the move action is unavailable while a sale is armed")
	var armed_sell: Variant = _button_named(armed_panel as Node, "sell")
	if armed_sell is Button:
		check((armed_sell as Button).disabled,
			"the armed sale's own action is unavailable")
	var arm_move_while_selling: Dictionary = town.arm_move()
	check(not bool(arm_move_while_selling.get("ok", true)),
		"arming a move while a sale is armed rejects")
	check_eq(str(arm_move_while_selling.get("code", "")),
		"sell_already_active",
		"the stacked-arm refusal names the armed mode")
	# A second sale arm is refused by name: the surface never stacks.
	var again: Dictionary = town.arm_sell()
	check(not bool(again.get("ok", true)),
		"arming an already-armed sale rejects")
	check_eq(str(again.get("code", "")), "sell_already_active",
		"the double-arm names the condition")
	# Cancelling here keeps the applied-state checks that follow on a clean
	# surface; the cancel contract itself is asserted in its own check.
	var released: Dictionary = town.cancel_sell()
	check(bool(released.get("ok", false)),
		"the sale closes for the cancel scenario: %s" % released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition (design D6: the client owns the
## gameplay rules the legacy server never enforced).
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# The confirm on a closed sale refuses by name and sends nothing.
	var closed: Dictionary = await town.confirm_sell()
	check(not bool(closed.get("ok", true)),
		"a closed sale refuses a confirm")
	check_eq(str(closed.get("code", "")), "sell_not_active",
		"the closed-sale refusal names the condition")
	check_eq(api.sell_requests, requests_before,
		"the closed-sale refusal sent no request")

	# Re-select the recorded building and arm once more for the
	# selection-changed refusal.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SOLD_CELL))
	check(bool(press.get("ok", false)),
		"the building re-selects for the refusal checks: %s"
		% press.get("error"))
	var armed: Dictionary = town.arm_sell()
	check(bool(armed.get("ok", false)),
		"the sale re-arms: %s" % armed.get("error"))
	check_eq(api.sell_requests, requests_before, "re-arming sent no request")

	# A press while a sale is armed can move the selection (a sale owns no
	# grid target), and the confirm refuses that by name rather than
	# silently selling a building the player did not have selected.
	var elsewhere: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(elsewhere.get("ok", false)),
		"a press elsewhere still selects: %s" % elsewhere.get("error"))
	check_eq(town.selection_legacy_id(), SOLD_ITEM,
		"the press at (58,48) selects the second Turret I")
	var re_targeted: Dictionary = await town.confirm_sell()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose selection moved refuses")
	check_eq(str(re_targeted.get("code", "")), "sell_selection_changed",
		"the re-target refusal names the condition: %s"
		% re_targeted.get("error"))
	check_eq(api.sell_requests, requests_before,
		"the re-target refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	# The armed sale survives every refusal (a refusal never disarms it), so
	# it is closed here and the cancel contract is asserted on its own.
	var closed_armed: Dictionary = town.cancel_sell()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed sale closes cleanly: %s"
		% closed_armed.get("error"))


## A cancelled sale drops only mode-local state: the serialized town state,
## the selection, the resources, and the request count stay byte-identical.
func _check_cancelled_sale(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# Re-select the recorded building (the previous check moved the
	# selection) so the cancel is the state a player would be in.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SOLD_CELL))
	check(bool(press.get("ok", false)), "the recorded building re-selects")
	var armed: Dictionary = town.arm_sell()
	check(bool(armed.get("ok", false)),
		"the sale arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var cancelled: Dictionary = town.cancel_sell()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the sale: %s" % cancelled.get("error"))
	check(not town.sell_active(), "the sale closes")
	check(town.sell_placement() == null, "the sold placement drops")
	check_eq(town.sell_slot(), TownState.NO_SLOT,
		"a closed sale names no index")
	check(not town.ui.is_slot_visible("move"),
		"the surface slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled sale")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS,
		"cancel renders nothing")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.sell_requests, requests_before, "cancel sent no request")
	var again: Dictionary = town.cancel_sell()
	check(not bool(again.get("ok", true)),
		"closing an already-closed sale rejects")
	check_eq(str(again.get("code", "")), "sell_not_active",
		"the double-close names the condition")
	check_eq(api.sell_requests, requests_before,
		"the double-close sent no request")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: the typed placement is gone, its rendered object
## is freed, the remaining objects keep the committed depth order, the
## resources and XP take the response's values, and the HUD re-reads from
## them — with both counts falling by exactly one.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	var object: Variant = _object_for_cell(town, SOLD_CELL)
	check(object != null, "the Turret I object is committed before the sale")
	if object == null:
		return
	var armed: Dictionary = town.arm_sell()
	check(bool(armed.get("ok", false)),
		"the sale arms for the confirmed intent: %s" % armed.get("error"))
	var requests_before: int = api.sell_requests
	var snapshot_before := _state_snapshot(state)
	var confirmed: Dictionary = await town.confirm_sell()
	check(bool(confirmed.get("ok", false)),
		"the confirmed sale succeeds: %s" % confirmed.get("error"))
	check_eq(api.sell_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	var typed_success: Variant = confirmed.get("result")
	check(typed_success is BootData.SellResult,
		"the success envelope carries the typed sell result")
	if typed_success is BootData.SellResult:
		var success: BootData.SellResult = typed_success
		check_eq(success.protocol, BootData.PROTOCOL,
			"the sell protocol is compat-v0")
		check_eq(success.game_version, "alpha 0.02",
			"the sell response carries the game version")
		check(success.server_time > 0,
			"the sell server_time is the fixture epoch (time-dependent)")
		check_eq(success.result, "success",
			"the legacy result string is verbatim")
		check(success.removed != null,
			"the response carries the removed row")
		check(success.resources != null,
			"the response carries typed resources")
		if success.removed != null and success.resources != null:
			check_eq(success.removed.item_id, SOLD_ITEM,
				"the removed row names Turret I")
			check_eq(success.removed.x, SOLD_CELL.x,
				"the removed row carries its saved x")
			check_eq(success.removed.y, SOLD_CELL.y,
				"the removed row carries its saved y")
			check_eq(success.removed.timestamp, 0,
				"the removed row keeps the save's timestamp (never restamped)")
			check_eq(success.removed.orientation, 0,
				"the removed row keeps its orientation")
			check_eq(success.removed.store, [],
				"the removed row keeps its store")
			check_eq(success.removed.attr, {},
				"the removed row keeps its attr")
			check_eq(success.removed.player, 1,
				"the removed row keeps the player's team field")
			# The derived price vector is NEUTRAL, so a real sale changes no
			# balance and no refund is claimed (design D2).
			check_eq(success.resources.xp, 4, "xp follows the response")
			check_eq(success.resources.gold, 2000, "gold follows the response")
			check_eq(success.resources.wood, 2000, "wood follows the response")
			check_eq(success.resources.oil, 2000, "oil follows the response")
			check_eq(success.resources.steel, 2000,
				"steel follows the response")
			check_eq(success.resources.cash, 5, "cash follows the response")
			check_eq(success.resources.mana, 0, "mana follows the response")

	# The authoritative apply: the placement and its object are gone.
	check_eq(state.placements.size(), PLACEMENTS - 1,
		"the sale removes exactly one typed placement")
	check_eq(town.objects.size(), PLACEMENTS - 1,
		"the sale removes exactly one rendered object")
	check(_placement_by_slot(state, SOLD_SLOT) == null,
		"the sold placement is gone from the typed state")
	check(town.sell_placement() == null,
		"the armed placement is released after the apply")
	check(not town.sell_active(), "the sale closes after the apply")
	var still_rendered := false
	for candidate: Variant in town.objects:
		if candidate != null and int(candidate.legacy_id) == SOLD_ITEM \
				and candidate.cell == SOLD_CELL:
			still_rendered = true
	check(not still_rendered,
		"no object renders the sold building at its cell")
	var previous_depth := -1
	var depth_ordered := true
	for candidate: Variant in town.objects:
		var depth := Iso.depth_key(candidate.cell)
		if depth < previous_depth:
			depth_ordered = false
		previous_depth = depth
	check(depth_ordered,
		"the remaining objects keep non-decreasing isometric depth")
	check_eq(town.objects.size(), town.objects_layer.get_child_count(),
		"the objects layer holds exactly the committed object list")
	# The selection pointed at the removed building, so it is cleared.
	check(town.selection() == null,
		"the selection is cleared when the sold building disappears")
	# The state and HUD take the response's values verbatim.
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
		check_eq(hud.displayed("coins"), "2000",
			"the HUD renders the authoritative coins")
		check_eq(hud.displayed("xp"), "4", "the HUD renders xp verbatim")
	check_eq(town.sell_error, "", "success leaves no failure record")
	check(String(_surface_status(town)).contains("sold"),
		"the status names the completed sale")
	check(String(_surface_status(town)).contains("refund: none claimed"),
		"the status keeps the no-refund claim limit after the sale")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")
	check_eq(api.sell_requests, requests_before + 1,
		"the apply issued no further request")


## The unknown-index failure: the intent names an index the service does not
## know (a stale client state — the endpoint resolves the index before
## executing and answers 404 `unknown_item_index`, so legacy's silent no-op
## is never reported as a success), the explicit error names that code, and
## the building stays on the map with nothing removed.
func _check_unknown_index(registry: Variant, api: Variant) -> void:
	var requests_before: int = api.sell_requests
	var ghost_town: Variant = _town_with_extra_row(registry)
	if ghost_town == null:
		return
	var armed: Dictionary = ghost_town.arm_sell()
	check(bool(armed.get("ok", false)),
		"the extra row arms a sale: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(ghost_town.sell_slot(), UNKNOWN_INDEX,
			"the armed sale names the unknown index")
		var failed: Dictionary = await ghost_town.confirm_sell()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s"
			% failed.get("error"))
		check(ghost_town.sell_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check_eq(ghost_town.objects.size(), PLACEMENTS + 1,
			"the structured failure removes nothing")
		check(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX) != null,
			"the unknown-index row is still in the typed state")
		check(ghost_town.sell_active(),
			"the sale survives the structured failure")
		check_eq(ghost_town.sell_placement().cell, GHOST_CELL,
			"the unknown-index row stays at its own cell")
		# The sale is still armed and the row still there, so the surface
		# can be closed explicitly.
		var closed: Dictionary = ghost_town.cancel_sell()
		check(bool(closed.get("ok", false)),
			"the failed sale closes cleanly")
	ghost_town.free()
	check_eq(api.sell_requests, requests_before + 1,
		"the failed intent still sent exactly once")


## A second town whose state carries one extra row under an index neither
## the corpus nor the fake double knows (a stale client state). It reuses
## the SAME parsed fresh save plus that row, so no fixture is written.
func _town_with_extra_row(registry: Variant) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[
		str(UNKNOWN_INDEX)] = [SOLD_ITEM, GHOST_CELL.x, GHOST_CELL.y,
			0, 0, [], {}, 1]
	var parsed: Dictionary = TownState.parse(crafted, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "the unknown-index fixture parses: %s"
			% parsed.get("error"))
		return null
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		town.free()
		return null
	# The extra row's object is selected through the delivered press path.
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	if not bool(pressed.get("ok", false)) or town.selection_legacy_id() \
			!= SOLD_ITEM:
		town.free()
		return null
	return town


## LAST scenario (it waits out the refused loopback endpoint): the intent
## goes out over the legacy transport, the endpoint refuses it, and the
## explicit error names `unreachable_endpoint` with the building still on the
## map and no resource changed (the same no-mutation contract as a
## structured failure).
func _check_transport_failure(town: Node2D, state: Variant,
		api: Variant) -> void:
	# A still-present addressable building: the Turret I at legacy key 11.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(press.get("ok", false)),
		"the spare building selects for the transport scenario: %s"
		% press.get("error"))
	check_eq(town.selection_legacy_id(), SOLD_ITEM,
		"the spare building is the committed selection")
	var armed: Dictionary = town.arm_sell()
	check(bool(armed.get("ok", false)),
		"the sale arms for the transport scenario: %s" % armed.get("error"))
	check_eq(town.sell_slot(), SPARE_SLOT,
		"the armed sale names the spare building's legacy key")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.sell_requests
	var snapshot_before := _state_snapshot(state)
	var objects_before: int = town.objects.size()
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_sell()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.sell_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.sell_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(town.objects.size(), objects_before,
		"the transport failure removes nothing")
	check(town.sell_active(),
		"the sale survives the transport failure")
	# The last state-changing check ran against the fake, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The unaddressable-row refusal (design D7 carried forward): a row whose
## save key is not a positive integer parses, renders, and is selectable,
## but the sell action is unavailable, arming is refused by name, and
## NOTHING is sent — the index is never coerced, because a coerced index
## would name a different row.
func _check_unaddressable_refusal(state: Variant, registry: Variant,
		api: Variant, session: Variant, pid: String,
		summary: BootData.PlayerSummary) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		SOLD_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
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
	var requests_before: int = api.sell_requests
	var snapshot_before := _state_snapshot(town.state)
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the unaddressable row is selectable: %s" % pressed.get("error"))
	check_eq(town.selection_legacy_id(), SOLD_ITEM,
		"the unaddressable row is the committed selection")
	check(not town.sell_selection_available(),
		"an unaddressable row never offers the sell action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var sell_button: Variant = _button_named(panel as Node, "sell")
		check(sell_button is Button and (sell_button as Button).disabled,
			"the sell action is disabled for an unaddressable row")
		check(String(_surface_status(town)).contains("not movable"),
			"the status names the unaddressable refusal")
	var refused: Dictionary = town.arm_sell()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the move flow's own unaddressable reason: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check(not town.sell_active(),
		"no sale opens for an unaddressable row")
	check_eq(api.sell_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The live-sell scenario (verify-boot's sell-live phase): one typed intent
## through the real Compatibility endpoint, so the unchanged legacy
## `command()` executes the `sell` branch over the disposable corpus. This
## side asserts the documented typed response; the phase harness separately
## asserts the corpus save file mutated. No fixture is touched.
func _check_live_sell() -> void:
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
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)
	var sold: Variant = await api.sell_building(pid, SOLD_SLOT)
	check(sold is BootData.SellResult,
		"the live sell returns a typed result")
	if not (sold is BootData.SellResult):
		return
	var typed := sold as BootData.SellResult
	check(typed.ok, "the live sale succeeds: %s / %s" % [
		typed.error_code, typed.error_message])
	if not typed.ok or typed.removed == null or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live sell protocol is compat-v0")
	check(typed.game_version != "",
		"the live sell response carries the game version")
	check(typed.server_time > 0,
		"the live server_time is a positive wall-clock epoch")
	check_eq(typed.result, "success",
		"the legacy result string is verbatim")
	# The row is the one read BEFORE execution (design D5).
	check_eq(typed.removed.item_id, SOLD_ITEM,
		"the live removed row names Turret I")
	check_eq(typed.removed.x, SOLD_CELL.x,
		"the live removed row carries x=41")
	check_eq(typed.removed.y, SOLD_CELL.y,
		"the live removed row carries y=48")
	check_eq(typed.removed.player, 1,
		"the live removed row keeps the player's team field")
	check(typed.removed.timestamp >= 0,
		"the live removed row carries the saved timestamp field")
	# The derived price vector is neutral, so nothing in the resource bag
	# moves and no refund is claimed (design D2).
	check_eq(typed.resources.xp, 4, "xp follows the response")
	check_eq(typed.resources.gold, 2000, "gold follows the response")
	check_eq(typed.resources.wood, 2000, "wood follows the response")
	check_eq(typed.resources.oil, 2000, "oil follows the response")
	check_eq(typed.resources.steel, 2000, "steel follows the response")
	check_eq(typed.resources.cash, 5, "cash follows the response")
	check_eq(typed.resources.mana, 0, "mana follows the response")
	# A stale index fails closed with the endpoint's own code rather than
	# reporting a success for a sale that never happened — here the index is
	# one no implementation knows (the fresh fake double is rebuilt by
	# `configure()`, so its own state is not this process's history).
	var unknown: Variant = await api.sell_building(pid, UNKNOWN_INDEX)
	check(unknown is BootData.SellResult,
		"the live unknown index returns the typed result")
	if unknown is BootData.SellResult:
		var failure: BootData.SellResult = unknown
		check(not failure.ok, "the live unknown index is a structured failure")
		check_eq(failure.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(failure.removed == null and failure.resources == null,
			"the live structured failure carries no partial payload")
	# The fake derives the same code for the same intent, offline.
	api.configure("fake")
	var fake_unknown: Variant = await api.sell_building(pid, UNKNOWN_INDEX)
	check(fake_unknown is BootData.SellResult and not fake_unknown.ok,
		"the fake fails the same intent offline")
	if fake_unknown is BootData.SellResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-sell applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [SOLD_SLOT, typed.removed.x, typed.removed.y, typed.resources.xp,
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


## The selection-driven surface's panel (null before the first selection or
## when the slot never registered).
func _surface_panel(town: Variant) -> Variant:
	if not town.ui.has_slot("move"):
		return null
	var slot: Control = town.ui.slot_root("move")
	if slot == null or slot.get_child_count() == 0:
		return null
	return slot.get_child(0)


## The named button anywhere inside the surface panel (the action row nests
## the arm/confirm/cancel buttons), or null.
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
func _surface_status(town: Variant) -> String:
	var panel: Variant = _surface_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "status":
			return (child as Label).text
	return ""


## The on-screen selection line text ("" before a panel exists).
func _surface_selection_text(town: Variant) -> String:
	var panel: Variant = _surface_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "selection":
			return (child as Label).text
	return ""


## The depth-topmost rendered object covering a cell (the same rule the
## press path applies: the last object in draw order wins), or null.
func _object_for_cell(town: Variant, cell: Vector2i) -> Variant:
	var hit: Variant = null
	for object: Variant in town.objects:
		if object != null and object.contains_cell(cell):
			hit = object
	return hit


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## The committed placement carrying an addressable index (null when absent).
func _placement_by_slot(state: Variant, slot: int) -> Variant:
	if state == null:
		return null
	for placement: Variant in state.placements:
		if placement != null and int(placement.slot) == slot:
			return placement
	return null


## One persisted eight-field row in the canonical typed form (the JSON
## transport widens the save's ints to floats on the pinned engine).
func _typed_row(value: Variant) -> Array:
	var row: Array = []
	if not (value is Array):
		return row
	for element: Variant in (value as Array):
		if element is int or element is float:
			row.append(int(element) if float(element) == floor(
				float(element)) else element)
		else:
			row.append(element)
	return row


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-sale and failure paths).
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
