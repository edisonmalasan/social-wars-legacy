extends "res://tests/test_base.gd"
## Store suite (building-store, spec "Store flow" / "Store through either
## implementation").
##
## Scenarios:
##   gating      the selection-driven surface offers a `Store` action beside
##               the delivered `Move` and `Sell` actions, only for a
##               selected, ADDRESSABLE placed building, and pressing it arms
##               the store in the SAME UI-foundation slot the other two modes
##               use (design D7 — no fourth panel, no grid target, no
##               preview), and neither delivered mode's behavior changes;
##   refusals    an unaddressable legacy key is refused by name with NO
##               request, the three modes never stack, and a selection that
##               no longer names the armed building refuses the confirm
##               instead of silently re-targeting it;
##   cancel      a cancelled store sends nothing and leaves the town, the
##               storage view, and the readout byte-identical;
##   apply       one confirmed intent sends exactly one request and applies
##               ONLY the authoritative response: the typed placement gone,
##               its rendered object freed, the remaining objects keeping the
##               committed depth order, the typed storage mapping replaced
##               through the shared parser, the readout re-rendered from it,
##               the resources and XP from the response, and the HUD
##               re-read from them — with the placement and object counts
##               falling by exactly one;
##   failures    a stale index the service does not know (`unknown_item_index`
##               — the endpoint's 404, resolved before execution) and a
##               transport failure (the refused loopback endpoint) each
##               surface their code with the building still on the map, the
##               storage unchanged, and the HUD unchanged;
##   no-request  the whole run issues no bootstrap request (the state
##               derives from the fixture in hand and the flow never
##               re-bootstraps).
##
## Uses the committed bootstrap and store fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-store` run is the `store-live`
## phase: one typed intent through the real Compatibility endpoint.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## recorded against the committed store capture): the Tree decoration, item
## 905, 1x1, at legacy map key "2" — its cell `(53,39)`, the row
## `[905, 53, 39, 0, 0, [], {}, 1]` — the placement count falls from 40 to
## 39, the fresh save's empty storage becomes `{"905": 1}`, and no resource
## changes (the derived price vector is neutral).
const STORED_ITEM := 905
const STORED_SLOT := 2
const STORED_CELL := Vector2i(53, 39)
## The pre-execution row the executed legacy transaction removed.
const STORED_ROW := [STORED_ITEM, 53, 39, 0, 0, [], {}, 1]
## The fresh save's placement count before and after the store.
const PLACEMENTS := 40
## The storage mapping the executed transaction produced (the fresh save's
## storage was empty, so this is the whole mapping afterwards).
const STORED_MAPPING := {"905": 1}
## An index the corpus and the double both do not know (a stale client state
## after the row was already stored, or a row the save never carried).
const UNKNOWN_INDEX := 9999
## The cell the extra-row scenario parks the unknown-index row at.
const GHOST_CELL := Vector2i(20, 20)
## A second, still-present addressable building used for the transport
## scenario after the store: the Turret I at legacy key 11, cell (58,48).
const SPARE_CELL := Vector2i(58, 48)
const SPARE_SLOT := 11
const SPARE_ITEM := 22

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
	if scenario == "live-store":
		# verify-boot's store-live phase: one typed intent through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response.
		# Everything else here is fixture-fake only.
		await _check_live_store()
		return
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	var config: Variant = _fixture(CONFIG_FIXTURE)
	check(config is Dictionary, "the config fixture parses as JSON")
	if not (config is Dictionary):
		return
	await _check_flow(payload, config as Dictionary)
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# Store flow (spec "Store flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> confirm -> apply plus every refusal, failure, and no-request path.
func _check_flow(payload: Dictionary, config: Dictionary) -> void:
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
	check_eq(state.storage, {},
		"the fresh save starts with an empty storage mapping")
	var stored: Variant = _placement_by_slot(state, STORED_SLOT)
	check(stored != null, "the stored building is addressable by key 2")
	if stored != null:
		check_eq(int(stored.item), STORED_ITEM, "key 2 names the Tree (item 905)")
		check_eq(stored.cell, STORED_CELL, "the fresh save anchors it at (53,39)")
		check_eq(stored.footprint, Vector2i(1, 1), "the Tree is a 1x1 footprint")
		check_eq(_typed_row(stored.raw), STORED_ROW,
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
		"the save list resolves the store save")
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
		"the fresh save renders 40 objects before any store")
	# The shop surface is opened only so the storage READOUT exists: the store
	# apply re-renders it, and that on-screen text is the evidence.
	town.set_shop_catalog(PlacementCatalog.parse(config))
	var opened: Dictionary = town.enter_shop()
	check(bool(opened.get("ok", false)),
		"the shop opens to render the storage readout: %s"
		% opened.get("error"))
	if not bool(opened.get("ok", false)):
		town.free()
		return
	check_eq(town.storage_rows(), ["(empty)"],
		"the readout starts on the empty-storage indicator")
	check_eq(_storage_labels(town), ["(empty)"],
		"the on-screen readout starts on the empty-storage indicator")

	var requests_start: int = api.store_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	_check_cancelled_store(town, state, api, requests_start, snapshot_start)
	await _check_applied_response(town, state, api)
	await _check_unknown_index(registry, api)
	await _check_transport_failure(town, state, api)
	check_eq(api.store_requests, requests_start + 3,
		"the whole flow issued exactly three requests (success, structured "
		+ "failure, transport failure); every other check sent none")
	town.free()

	# The unaddressable refusal runs on its own town so the applied state of
	# the main flow stays intact for the counts above.
	await _check_unaddressable_refusal(state, registry, api, session,
		pid, summary)


## The selection-driven surface offers `Store` beside `Move` and `Sell` for
## a selected, addressable placed building, and pressing it arms the store in
## the SAME slot the other two modes use (design D7: no fourth panel, no grid
## target, and neither delivered mode is altered).
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.store_active(), "the store is not armed before a selection")
	check(not town.store_selection_available(),
		"no selection means no store action")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(STORED_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), STORED_ITEM,
		"the press at (53,39) selects the Tree")
	check(town.store_selection_available(),
		"an addressable selection offers the store action")
	check(town.move_selection_available(),
		"the same selection still offers the delivered move action")
	check(town.sell_selection_available(),
		"the same selection still offers the delivered sell action")
	check(town.ui.has_slot("move"),
		"the selection-driven surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("move"),
		"the surface slot shows for a committed selection")
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	# The shop is deliberately open here so the storage readout exists; a
	# selection never picks in it (the shop owns its own entry selection).
	check(town.shop_entry() == null,
		"a selection never arms or picks in the shop")
	check(town.shop_active(),
		"the open shop survives the selection (it is the readout's surface)")
	check(not town.move_active(),
		"a selection alone never arms the delivered move mode")
	check(not town.sell_active(),
		"a selection alone never arms the delivered sell mode")

	var panel: Variant = _surface_panel(town)
	check(panel != null, "the selection-driven panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var store_button: Variant = _button_named(panel_node, "store")
	check(store_button is Button, "the store action button exists")
	if store_button is Button:
		check(not (store_button as Button).disabled,
			"the store action is enabled for an addressable selection")
		check_eq((store_button as Button).text, "Put in storage",
			"the action is labelled Put in storage")
	var move_button: Variant = _button_named(panel_node, "move")
	check(move_button is Button and not (move_button as Button).disabled,
		"the delivered move action is still enabled beside it")
	var sell_button: Variant = _button_named(panel_node, "sell")
	check(sell_button is Button and not (sell_button as Button).disabled,
		"the delivered sell action is still enabled beside it")
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before a store is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_surface_status(town)).contains("press Move"),
		"the unarmed status line is the delivered one, unchanged")

	# The button wiring arms the store (the signal path, one `pressed`
	# emission = one arm — no request).
	if store_button != null:
		(store_button as Button).pressed.emit()
	check(town.store_active(), "pressing the action arms the store")
	check_eq(town.store_slot(), STORED_SLOT,
		"the armed store names the building's legacy key 2")
	check_eq(town.store_placement().cell, STORED_CELL,
		"the armed placement is the one at (53,39)")
	check(town.ui.is_slot_visible("move"),
		"the surface slot stays visible while armed")
	var status := String(_surface_status(town))
	check(status.contains("armed"), "the status names the armed store")
	check(status.contains("storage"),
		"the status reports where the building will land")
	check(status.contains("none claimed"),
		"the status names the no-cost and no-capacity claim limits")
	check(String(_surface_selection_text(town)).contains("none claimed"),
		"the selection line states the no-cost derivation boundary")
	# A store has NO grid target, so no footprint preview is displayed.
	check(not town.move_preview_shown(),
		"an armed store shows no footprint preview (it has no target)")
	check(town.move_evaluation().is_empty(),
		"an armed store commits no move evaluation")
	check_eq(api.store_requests, requests_before, "arming sent no request")
	# The delivered modes are unavailable while a store is armed: the three
	# modes share one surface and never stack. Arming REBUILDS the panel (the
	# delivered attach precedent), so it is re-read here.
	var armed_panel: Variant = _surface_panel(town)
	var move_while_storing: Variant = _button_named(
		armed_panel as Node, "move")
	if move_while_storing is Button:
		check((move_while_storing as Button).disabled,
			"the move action is unavailable while a store is armed")
	var sell_while_storing: Variant = _button_named(
		armed_panel as Node, "sell")
	if sell_while_storing is Button:
		check((sell_while_storing as Button).disabled,
			"the sell action is unavailable while a store is armed")
	var armed_store: Variant = _button_named(armed_panel as Node, "store")
	if armed_store is Button:
		check((armed_store as Button).disabled,
			"the armed store's own action is unavailable")
	var armed_confirm: Variant = _button_named(armed_panel as Node, "confirm")
	if armed_confirm is Button:
		check((armed_confirm as Button).visible,
			"the targetless confirm is offered as soon as the store is armed")
		check_eq((armed_confirm as Button).text, "Put in storage",
			"the shared confirm names the armed mode")
	# Mutual exclusion, in both directions (spec "Modes are mutually
	# exclusive"): the armed store refuses the other two by name.
	var arm_move_while_storing: Dictionary = town.arm_move()
	check(not bool(arm_move_while_storing.get("ok", true)),
		"arming a move while a store is armed rejects")
	check_eq(str(arm_move_while_storing.get("code", "")),
		"store_already_active",
		"the stacked-arm refusal names the armed mode")
	var arm_sell_while_storing: Dictionary = town.arm_sell()
	check(not bool(arm_sell_while_storing.get("ok", true)),
		"arming a sale while a store is armed rejects")
	check_eq(str(arm_sell_while_storing.get("code", "")),
		"store_already_active",
		"the stacked-arm refusal names the armed mode for the sale too")
	# A second store arm is refused by name: the surface never stacks.
	var again: Dictionary = town.arm_store()
	check(not bool(again.get("ok", true)),
		"arming an already-armed store rejects")
	check_eq(str(again.get("code", "")), "store_already_active",
		"the double-arm names the condition")
	check_eq(api.store_requests, requests_before,
		"every refusal on this surface sent no request")
	check(town.store_active(),
		"the refusals never disarm the store in progress")
	# Cancelling here keeps the applied-state checks that follow on a clean
	# surface; the cancel contract itself is asserted in its own check.
	var released: Dictionary = town.cancel_store()
	check(bool(released.get("ok", false)),
		"the store closes for the cancel scenario: %s" % released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition (design D5: the client owns the
## gameplay rules the legacy server never enforced).
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# The confirm on a closed store refuses by name and sends nothing.
	var closed: Dictionary = await town.confirm_store()
	check(not bool(closed.get("ok", true)),
		"a closed store refuses a confirm")
	check_eq(str(closed.get("code", "")), "store_not_active",
		"the closed-store refusal names the condition")
	check_eq(api.store_requests, requests_before,
		"the closed-store refusal sent no request")

	# Re-select the recorded building and arm once more for the
	# selection-changed refusal.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(STORED_CELL))
	check(bool(press.get("ok", false)),
		"the building re-selects for the refusal checks: %s"
		% press.get("error"))
	var armed: Dictionary = town.arm_store()
	check(bool(armed.get("ok", false)),
		"the store re-arms: %s" % armed.get("error"))
	check_eq(api.store_requests, requests_before, "re-arming sent no request")

	# A press while a store is armed can move the selection (a store owns no
	# grid target), and the confirm refuses that by name rather than silently
	# storing a building the player did not have selected.
	var elsewhere: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(elsewhere.get("ok", false)),
		"a press elsewhere still selects: %s" % elsewhere.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the press at (58,48) selects the Turret I")
	var re_targeted: Dictionary = await town.confirm_store()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose selection moved refuses")
	check_eq(str(re_targeted.get("code", "")), "store_selection_changed",
		"the re-target refusal names the condition: %s"
		% re_targeted.get("error"))
	check_eq(api.store_requests, requests_before,
		"the re-target refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	# The armed store survives every refusal (a refusal never disarms it), so
	# it is closed here and the cancel contract is asserted on its own.
	var closed_armed: Dictionary = town.cancel_store()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed store closes cleanly: %s"
		% closed_armed.get("error"))


## A cancelled store drops only mode-local state: the serialized town state,
## the storage view, the readout, the selection, the resources, and the
## request count stay byte-identical.
func _check_cancelled_store(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# Re-select the recorded building (the previous check moved the
	# selection) so the cancel is the state a player would be in.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(STORED_CELL))
	check(bool(press.get("ok", false)), "the recorded building re-selects")
	var armed: Dictionary = town.arm_store()
	check(bool(armed.get("ok", false)),
		"the store arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var readout_before: Array = _storage_labels(town)
	var cancelled: Dictionary = town.cancel_store()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the store: %s" % cancelled.get("error"))
	check(not town.store_active(), "the store closes")
	check(town.store_placement() == null, "the stored placement drops")
	check_eq(town.store_slot(), TownState.NO_SLOT,
		"a closed store names no index")
	check(not town.ui.is_slot_visible("move"),
		"the surface slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled store")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS,
		"cancel renders nothing")
	check_eq(town.storage_rows(), ["(empty)"],
		"cancel leaves the storage view untouched")
	check_eq(_storage_labels(town), readout_before,
		"cancel leaves the on-screen readout untouched")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.store_requests, requests_before, "cancel sent no request")
	var again: Dictionary = town.cancel_store()
	check(not bool(again.get("ok", true)),
		"closing an already-closed store rejects")
	check_eq(str(again.get("code", "")), "store_not_active",
		"the double-close names the condition")
	check_eq(api.store_requests, requests_before,
		"the double-close sent no request")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: the typed placement is gone, its rendered object is
## freed, the remaining objects keep the committed depth order, the storage
## mapping and its readout take the response's values, the resources and XP
## take the response's values, and the HUD re-reads from them — with both
## counts falling by exactly one.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	var object: Variant = _object_for_cell(town, STORED_CELL)
	check(object != null, "the Tree object is committed before the store")
	if object == null:
		return
	var armed: Dictionary = town.arm_store()
	check(bool(armed.get("ok", false)),
		"the store arms for the confirmed intent: %s" % armed.get("error"))
	var requests_before: int = api.store_requests
	var snapshot_before := _state_snapshot(state)
	var confirmed: Dictionary = await town.confirm_store()
	check(bool(confirmed.get("ok", false)),
		"the confirmed store succeeds: %s" % confirmed.get("error"))
	check_eq(api.store_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	var typed_success: Variant = confirmed.get("result")
	check(typed_success is BootData.StoreResult,
		"the success envelope carries the typed store result")
	if typed_success is BootData.StoreResult:
		var success: BootData.StoreResult = typed_success
		check_eq(success.protocol, BootData.PROTOCOL,
			"the store protocol is compat-v0")
		check_eq(success.game_version, "alpha 0.02",
			"the store response carries the game version")
		check(success.server_time > 0,
			"the store server_time is the fixture epoch (time-dependent)")
		check_eq(success.result, "success",
			"the legacy result string is verbatim")
		check(success.removed != null,
			"the response carries the removed row")
		check(success.resources != null,
			"the response carries typed resources")
		check_eq(success.store, STORED_MAPPING,
			"the response carries the full storage mapping")
		if success.removed != null and success.resources != null:
			check_eq(success.removed.item_id, STORED_ITEM,
				"the removed row names the Tree")
			check_eq(success.removed.x, STORED_CELL.x,
				"the removed row carries its saved x")
			check_eq(success.removed.y, STORED_CELL.y,
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
			# The derived price vector is NEUTRAL, so a real store changes no
			# balance and claims no cost (design D2).
			check_eq(success.resources.xp, 4, "xp follows the response")
			check_eq(success.resources.gold, 2000, "gold follows the response")
			check_eq(success.resources.wood, 2000, "wood follows the response")
			check_eq(success.resources.oil, 2000, "oil follows the response")
			check_eq(success.resources.steel, 2000,
				"steel follows the response")
			check_eq(success.resources.cash, 5, "cash follows the response")
			check_eq(success.resources.mana, 0, "mana follows the response")

	# The authoritative apply: the placement and its object are gone, and the
	# storage mapping took the response's whole mapping.
	check_eq(state.placements.size(), PLACEMENTS - 1,
		"the store removes exactly one typed placement")
	check_eq(town.objects.size(), PLACEMENTS - 1,
		"the store removes exactly one rendered object")
	check(_placement_by_slot(state, STORED_SLOT) == null,
		"the stored placement is gone from the typed state")
	check(town.store_placement() == null,
		"the armed placement is released after the apply")
	check(not town.store_active(), "the store closes after the apply")
	var still_rendered := false
	for candidate: Variant in town.objects:
		if candidate != null and int(candidate.legacy_id) == STORED_ITEM \
				and candidate.cell == STORED_CELL:
			still_rendered = true
	check(not still_rendered,
		"no object renders the stored building at its cell")
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
		"the selection is cleared when the stored building disappears")
	check_eq(state.storage, STORED_MAPPING,
		"the storage mapping takes the response's whole mapping verbatim")
	check_eq(town.storage_rows(), ["Tree  x1  (item 905)"],
		"the readout renders the stored item with its response quantity")
	check_eq(_storage_labels(town), ["Tree  x1  (item 905)"],
		"the on-screen readout re-rendered from the applied mapping")
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
	check_eq(town.store_error, "", "success leaves no failure record")
	check(String(_surface_status(town)).contains("stored"),
		"the status names the completed store")
	check(String(_surface_status(town)).contains("one-way"),
		"the status names the one-way trip claim limit")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")
	check_eq(api.store_requests, requests_before + 1,
		"the apply issued no further request")


## The unknown-index failure: the intent names an index the service does not
## know (a stale client state — the endpoint resolves the index before
## executing and answers 404 `unknown_item_index`, so legacy's silent
## early return is never reported as a success), the explicit error names that
## code, and the building stays on the map with the storage unchanged and
## nothing stored.
func _check_unknown_index(registry: Variant, api: Variant) -> void:
	var requests_before: int = api.store_requests
	var ghost_town: Variant = _town_with_extra_row(registry)
	if ghost_town == null:
		return
	var snapshot_before := _state_snapshot(ghost_town.state)
	var armed: Dictionary = ghost_town.arm_store()
	check(bool(armed.get("ok", false)),
		"the extra row arms a store: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(ghost_town.store_slot(), UNKNOWN_INDEX,
			"the armed store names the unknown index")
		var failed: Dictionary = await ghost_town.confirm_store()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s"
			% failed.get("error"))
		check(ghost_town.store_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check_eq(ghost_town.objects.size(), PLACEMENTS + 1,
			"the structured failure removes nothing")
		check(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX) != null,
			"the unknown-index row is still in the typed state")
		check_eq(ghost_town.state.storage, {},
			"the structured failure stores nothing")
		check_eq(ghost_town.storage_rows(), ["(empty)"],
			"the structured failure leaves the readout untouched")
		check_eq(_state_snapshot(ghost_town.state), snapshot_before,
			"the structured failure changes no state at all")
		check(ghost_town.store_active(),
			"the store survives the structured failure")
		check_eq(ghost_town.store_placement().cell, GHOST_CELL,
			"the unknown-index row stays at its own cell")
		# The store is still armed and the row still there, so the surface
		# can be closed explicitly.
		var closed: Dictionary = ghost_town.cancel_store()
		check(bool(closed.get("ok", false)),
			"the failed store closes cleanly")
	ghost_town.free()
	check_eq(api.store_requests, requests_before + 1,
		"the failed intent still sent exactly once")


## A second town whose state carries one extra row under an index neither
## the corpus nor the fake double knows (a stale client state). It reuses the
## SAME parsed fresh save plus that row, so no fixture is written.
func _town_with_extra_row(registry: Variant) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[
		str(UNKNOWN_INDEX)] = [STORED_ITEM, GHOST_CELL.x, GHOST_CELL.y,
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
			!= STORED_ITEM:
		town.free()
		return null
	return town


## LAST scenario (it waits out the refused loopback endpoint): the intent
## goes out over the legacy transport, the endpoint refuses it, and the
## explicit error names `unreachable_endpoint` with the building still on the
## map, the storage unchanged, and no resource changed (the same
## no-mutation contract as a structured failure).
func _check_transport_failure(town: Node2D, state: Variant,
		api: Variant) -> void:
	# A still-present addressable building: the Turret I at legacy key 11.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(press.get("ok", false)),
		"the spare building selects for the transport scenario: %s"
		% press.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the spare building is the committed selection")
	var armed: Dictionary = town.arm_store()
	check(bool(armed.get("ok", false)),
		"the store arms for the transport scenario: %s" % armed.get("error"))
	check_eq(town.store_slot(), SPARE_SLOT,
		"the armed store names the spare building's legacy key")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.store_requests
	var snapshot_before := _state_snapshot(state)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var objects_before: int = town.objects.size()
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_store()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.store_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.store_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(state.storage, storage_before,
		"the transport failure stores nothing")
	check_eq(town.storage_rows(), ["Tree  x1  (item 905)"],
		"the transport failure leaves the readout untouched")
	check_eq(town.objects.size(), objects_before,
		"the transport failure removes nothing")
	check(town.store_active(),
		"the store survives the transport failure")
	# The last state-changing check ran against the fake, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The unaddressable-row refusal (design D7 carried forward from
## building-move and building-sell): a row whose save key is not a positive
## integer parses, renders, and is selectable, but the store action is
## unavailable, arming is refused by name with the move flow's own reason,
## and NOTHING is sent — the index is never coerced, because a coerced index
## would name a different row.
func _check_unaddressable_refusal(state: Variant, registry: Variant,
		api: Variant, session: Variant, pid: String,
		summary: BootData.PlayerSummary) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		STORED_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
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
	var requests_before: int = api.store_requests
	var snapshot_before := _state_snapshot(town.state)
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the unaddressable row is selectable: %s" % pressed.get("error"))
	check_eq(town.selection_legacy_id(), STORED_ITEM,
		"the unaddressable row is the committed selection")
	check(not town.store_selection_available(),
		"an unaddressable row never offers the store action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var store_button: Variant = _button_named(panel as Node, "store")
		check(store_button is Button and (store_button as Button).disabled,
			"the store action is disabled for an unaddressable row")
		check(String(_surface_status(town)).contains("not movable"),
			"the status names the unaddressable refusal")
	var refused: Dictionary = town.arm_store()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the move flow's own unaddressable reason: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check(not town.store_active(),
		"no store opens for an unaddressable row")
	check_eq(api.store_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The live-store scenario (verify-boot's store-live phase): one typed intent
## through the real Compatibility endpoint, so the unchanged legacy
## `command()` executes the `store_item` branch over the disposable corpus.
## This side asserts the documented typed response; the phase harness
## separately asserts the corpus save file mutated. No fixture is touched.
func _check_live_store() -> void:
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
	var stored: Variant = await api.store_building(pid, STORED_SLOT)
	check(stored is BootData.StoreResult,
		"the live store returns a typed result")
	if not (stored is BootData.StoreResult):
		return
	var typed := stored as BootData.StoreResult
	check(typed.ok, "the live store succeeds: %s / %s" % [
		typed.error_code, typed.error_message])
	if not typed.ok or typed.removed == null or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live store protocol is compat-v0")
	check(typed.game_version != "",
		"the live store response carries the game version")
	check(typed.server_time > 0,
		"the live server_time is a positive wall-clock epoch")
	check_eq(typed.result, "success",
		"the legacy result string is verbatim")
	# The row is the one read BEFORE execution (design D4/D5), and the
	# storage mapping is the FULL post-execution one.
	check_eq(typed.removed.item_id, STORED_ITEM,
		"the live removed row names the Tree")
	check_eq(typed.removed.x, STORED_CELL.x,
		"the live removed row carries x=53")
	check_eq(typed.removed.y, STORED_CELL.y,
		"the live removed row carries y=39")
	check_eq(typed.removed.player, 1,
		"the live removed row keeps the player's team field")
	check(typed.removed.timestamp >= 0,
		"the live removed row carries the saved timestamp field")
	check_eq(typed.store, STORED_MAPPING,
		"the live response carries the full post-execution storage mapping")
	# The derived price vector is neutral, so nothing in the resource bag
	# moves and no storing cost is claimed (design D2).
	check_eq(typed.resources.xp, 4, "xp follows the response")
	check_eq(typed.resources.gold, 2000, "gold follows the response")
	check_eq(typed.resources.wood, 2000, "wood follows the response")
	check_eq(typed.resources.oil, 2000, "oil follows the response")
	check_eq(typed.resources.steel, 2000, "steel follows the response")
	check_eq(typed.resources.cash, 5, "cash follows the response")
	check_eq(typed.resources.mana, 0, "mana follows the response")
	# A stale index fails closed with the endpoint's own code rather than
	# reporting a success for a store that never happened — here the index is
	# one no implementation knows (the fresh fake double is rebuilt by
	# `configure()`, so its own state is not this process's history).
	var unknown: Variant = await api.store_building(pid, UNKNOWN_INDEX)
	check(unknown is BootData.StoreResult,
		"the live unknown index returns the typed result")
	if unknown is BootData.StoreResult:
		var failure: BootData.StoreResult = unknown
		check(not failure.ok, "the live unknown index is a structured failure")
		check_eq(failure.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(failure.removed == null and failure.resources == null,
			"the live structured failure carries no partial payload")
		check(failure.store.is_empty(),
			"the live structured failure carries no partial storage mapping")
	# The fake derives the same code for the same intent, offline.
	api.configure("fake")
	var fake_unknown: Variant = await api.store_building(pid, UNKNOWN_INDEX)
	check(fake_unknown is BootData.StoreResult and not fake_unknown.ok,
		"the fake fails the same intent offline")
	if fake_unknown is BootData.StoreResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-store applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [STORED_SLOT, typed.removed.x, typed.removed.y, typed.resources.xp,
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


## The shop panel holding the storage readout (null when the shop is closed).
func _shop_panel(town: Variant) -> Variant:
	if not town.ui.has_slot("shop"):
		return null
	var slot: Control = town.ui.slot_root("shop")
	if slot == null or slot.get_child_count() == 0:
		return null
	return slot.get_child(0)


## The rendered storage readout lines, in the order the panel shows them.
func _storage_labels(town: Variant) -> Array:
	var panel: Variant = _shop_panel(town)
	var labels: Array = []
	if panel == null:
		return labels
	for child: Variant in (panel as Node).get_children():
		if child is VBoxContainer and String((child as VBoxContainer).name) \
				== "storage_entries":
			for row: Variant in (child as VBoxContainer).get_children():
				if row is Label:
					labels.append((row as Label).text)
	return labels


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
		row.append(int(element) if (element is int or element is float) \
			else element)
	return row


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-store and failure paths). The
## storage mapping is part of it, so a store that changed it can never look
## byte-identical.
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append(placement.raw)
	return JSON.stringify({
		"placements": rows,
		"storage": state.storage,
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
