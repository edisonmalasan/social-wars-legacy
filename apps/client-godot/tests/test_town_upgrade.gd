extends "res://tests/test_base.gd"
## Upgrade suite (building-upgrade, spec "Upgrade flow" / "Upgrade through
## either implementation").
##
## Scenarios:
##   gating      the selection-driven surface offers an `Upgrade` action
##               beside the delivered `Move`, `Sell`, and `Store` actions,
##               only for a selected, ADDRESSABLE placed building that has a
##               resolvable next tier in the typed content catalog, and
##               pressing it arms the upgrade in the SAME UI-foundation slot
##               the other three modes use (design D8 — no fifth panel, no
##               grid target, no preview), and none of the three delivered
##               modes' behavior changes;
##   refusals    a building with no resolvable next tier (the Tree decoration
##               and a Bridge) and an unaddressable legacy key are each
##               refused by name with NO request, the four modes never stack,
##               and a selection that no longer names the armed building
##               refuses the confirm instead of silently re-targeting it;
##   cancel      a cancelled upgrade sends nothing and leaves the town, the
##               storage view, and the readout byte-identical;
##   apply       one confirmed intent sends exactly one request and applies
##               ONLY the authoritative response: the SAME building's object
##               re-rendered for the target tier at the same cell and the
##               same legacy key, the typed row replaced by the response's
##               post-execution row, every other object keeping its committed
##               depth position, the storage view and readout untouched, the
##               resources and XP from the response, and the HUD re-read
##               from them — with BOTH counts unchanged, because the key is
##               reused;
##   failures    an index the service does not know (`unknown_item_index` —
##               the endpoint's 404, resolved before execution) and a
##               transport failure (the refused loopback endpoint) each
##               surface their code with the building still on its cell at
##               its CURRENT tier, the storage unchanged, and the HUD
##               unchanged;
##   no-request  the whole run issues no bootstrap request (the state
##               derives from the fixture in hand and the flow never
##               re-bootstraps).
##
## Uses the committed bootstrap and upgrade fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-upgrade` run is the `upgrade-live`
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
## recorded against the committed upgrade capture): the Wall I, item 23, 1x1,
## at legacy map key "12" — its cell `(45,49)`, the row
## `[23, 45, 49, 0, 0, [], {}, 1]` — is REPLACED IN PLACE by the Wall II
## (item 24) at the same key and the same cell with a fresh wall-clock
## timestamp and the `{"nc": 0}` construction seed, while the placement count
## stays 40, the storage stays empty, and no resource changes (the derived
## price vector is neutral, so no upgrade cost is claimed).
const UPGRADED_ITEM := 23
const UPGRADED_SLOT := 12
const UPGRADED_CELL := Vector2i(45, 49)
const UPGRADED_TARGET := 24
const UPGRADED_ROW := [UPGRADED_ITEM, 45, 49, 0, 0, [], {}, 1]
## The fresh save's placement count before and after the upgrade — unchanged,
## because the pair REUSES the key.
const PLACEMENTS := 40
## The Tree decoration at legacy key 2, anchored at (53,39), and a Bridge at
## legacy key 35, anchored at (29,48): the committed configuration records
## `upgrades_to` `-1` for both, so neither has a resolvable next tier and
## neither is ever offered the action.
const NO_PATH_TREE_SLOT := 2
const NO_PATH_TREE_ITEM := 905
const NO_PATH_TREE_CELL := Vector2i(53, 39)
const NO_PATH_BRIDGE_SLOT := 35
const NO_PATH_BRIDGE_ITEM := 929
const NO_PATH_BRIDGE_CELL := Vector2i(29, 48)
## An index the corpus and the double both do not know (a stale client state
## after the row was already replaced by a service that renumbered its keys,
## or a row the save never carried).
const UNKNOWN_INDEX := 9999
## The cell the extra-row scenario parks the unknown-index row at.
const GHOST_CELL := Vector2i(20, 20)
## A second, still-present addressable building used for the mutual-exclusion
## and transport scenarios: the Turret I at legacy key 11, cell (58,48),
## which also has a resolvable next tier.
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
	if scenario == "live-upgrade":
		# verify-boot's upgrade-live phase: one typed intent through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response and
		# the REUSED key (the response's key and cell match the pre-request
		# row — this line's distinguishing fact). Everything else here is
		# fixture-fake only.
		await _check_live_upgrade()
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
# Upgrade flow (spec "Upgrade flow")
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
	var upgrading: Variant = _placement_by_slot(state, UPGRADED_SLOT)
	check(upgrading != null, "the recorded building is addressable by key 12")
	if upgrading != null:
		check_eq(int(upgrading.item), UPGRADED_ITEM,
			"key 12 names the Wall I (item 23)")
		check_eq(upgrading.cell, UPGRADED_CELL,
			"the fresh save anchors it at (45,49)")
		check_eq(upgrading.footprint, Vector2i(1, 1),
			"the Wall I is a 1x1 footprint")
		check_eq(_typed_row(upgrading.raw), UPGRADED_ROW,
			"the row is the pre-execution row the fixture replaced")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the upgrade save")
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
		"the fresh save renders 40 objects before any upgrade")
	# The shop surface is opened only so the storage READOUT exists: an
	# upgrade must leave the storage view and the readout untouched, and that
	# on-screen text is the evidence.
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

	var requests_start: int = api.upgrade_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	_check_cancelled_upgrade(town, state, api, requests_start, snapshot_start)
	_check_mutual_exclusion(town, api, requests_start)
	await _check_applied_response(town, state, api)
	await _check_unknown_index(registry, api)
	await _check_transport_failure(town, state, api)
	check_eq(api.upgrade_requests, requests_start + 3,
		"the whole flow issued exactly three requests (success, structured "
		+ "failure, transport failure); every other check sent none")
	town.free()

	# The refusals run on their own towns so the applied state of the main
	# flow stays intact for the counts above.
	await _check_unaddressable_refusal(state, registry, api, session,
		pid, summary)
	await _check_no_upgrade_path_refusal(registry, api, session, pid, summary)


## The selection-driven surface offers `Upgrade` beside `Move`, `Sell`, and
## `Store` for a selected, addressable placed building with a resolvable next
## tier, and pressing it arms the upgrade in the SAME slot the other three
## modes use (design D8: no fifth panel, no grid target, and none of the
## three delivered modes is altered).
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.upgrade_active(), "the upgrade is not armed before a selection")
	check(not town.upgrade_selection_available(),
		"no selection means no upgrade action")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(UPGRADED_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), UPGRADED_ITEM,
		"the press at (45,49) selects the Wall I")
	check(town.upgrade_selection_available(),
		"an addressable selection with a next tier offers the upgrade action")
	check_eq(town.upgrade_target_item(), 0,
		"an unarmed upgrade names no target tier (it is derived when armed)")
	check(town.move_selection_available(),
		"the same selection still offers the delivered move action")
	check(town.sell_selection_available(),
		"the same selection still offers the delivered sell action")
	check(town.store_selection_available(),
		"the same selection still offers the delivered store action")
	check(town.ui.has_slot("move"),
		"the selection-driven surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("move"),
		"the surface slot shows for a committed selection")
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	check(town.shop_active(),
		"the open shop survives the selection (it is the readout's surface)")
	check_eq(town.shop_entry(), null,
		"a selection never arms or picks in the shop")
	check(not town.move_active(),
		"a selection alone never arms the delivered move mode")
	check(not town.sell_active(),
		"a selection alone never arms the delivered sell mode")
	check(not town.store_active(),
		"a selection alone never arms the delivered store mode")

	var panel: Variant = _surface_panel(town)
	check(panel != null, "the selection-driven panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var upgrade_button: Variant = _button_named(panel_node, "upgrade")
	check(upgrade_button is Button, "the upgrade action button exists")
	if upgrade_button is Button:
		check(not (upgrade_button as Button).disabled,
			"the upgrade action is enabled for an addressable selection")
		check_eq((upgrade_button as Button).text, "Upgrade",
			"the action is labelled Upgrade")
	var move_button: Variant = _button_named(panel_node, "move")
	check(move_button is Button and not (move_button as Button).disabled,
		"the delivered move action is still enabled beside it")
	var sell_button: Variant = _button_named(panel_node, "sell")
	check(sell_button is Button and not (sell_button as Button).disabled,
		"the delivered sell action is still enabled beside it")
	var store_button: Variant = _button_named(panel_node, "store")
	check(store_button is Button and not (store_button as Button).disabled,
		"the delivered store action is still enabled beside it")
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before an upgrade is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_surface_status(town)).contains("press Move"),
		"the unarmed status line is the delivered one, unchanged")

	# The button wiring arms the upgrade (the signal path, one `pressed`
	# emission = one arm — no request).
	if upgrade_button != null:
		(upgrade_button as Button).pressed.emit()
	check(town.upgrade_active(), "pressing the action arms the upgrade")
	check_eq(town.upgrade_slot(), UPGRADED_SLOT,
		"the armed upgrade names the building's legacy key 12")
	check_eq(town.upgrade_target_item(), UPGRADED_TARGET,
		"the armed upgrade derives the Wall II (item 24) as its target")
	check(town.upgrade_placement() != null,
		"the armed placement is present")
	check_eq(town.upgrade_placement().cell, UPGRADED_CELL,
		"the armed placement is the one at (45,49)")
	check(town.ui.is_slot_visible("move"),
		"the surface slot stays visible while armed")
	var status := String(_surface_status(town))
	check(status.contains("armed"), "the status names the armed upgrade")
	check(status.contains("Wall I") and status.contains("Wall II"),
		"the status names the current tier and the target tier")
	check(status.contains("none claimed"),
		"the status names the no-upgrade-cost claim limit")
	var selection_text := String(_surface_selection_text(town))
	check(selection_text.contains("Wall I") and selection_text.contains("Wall II"),
		"the selection line names both tiers")
	check(selection_text.contains("none claimed"),
		"the selection line states the no-cost derivation boundary")
	# An upgrade has NO grid target, so no footprint preview is displayed.
	check(not town.move_preview_shown(),
		"an armed upgrade shows no footprint preview (it has no target)")
	check(town.move_evaluation().is_empty(),
		"an armed upgrade commits no move evaluation")
	check_eq(api.upgrade_requests, requests_before, "arming sent no request")
	# The delivered modes are unavailable while an upgrade is armed: the four
	# modes share one surface and never stack. Arming REBUILDS the panel (the
	# delivered attach precedent), so it is re-read here.
	var armed_panel: Variant = _surface_panel(town)
	var move_while_upgrading: Variant = _button_named(armed_panel as Node, "move")
	if move_while_upgrading is Button:
		check((move_while_upgrading as Button).disabled,
			"the move action is unavailable while an upgrade is armed")
	var sell_while_upgrading: Variant = _button_named(armed_panel as Node, "sell")
	if sell_while_upgrading is Button:
		check((sell_while_upgrading as Button).disabled,
			"the sell action is unavailable while an upgrade is armed")
	var store_while_upgrading: Variant = _button_named(
		armed_panel as Node, "store")
	if store_while_upgrading is Button:
		check((store_while_upgrading as Button).disabled,
			"the store action is unavailable while an upgrade is armed")
	var armed_upgrade: Variant = _button_named(armed_panel as Node, "upgrade")
	if armed_upgrade is Button:
		check((armed_upgrade as Button).disabled,
			"the armed upgrade's own action is unavailable")
	var armed_confirm: Variant = _button_named(armed_panel as Node, "confirm")
	if armed_confirm is Button:
		check((armed_confirm as Button).visible,
			"the targetless confirm is offered as soon as the upgrade is armed")
		check_eq((armed_confirm as Button).text, "Upgrade",
			"the shared confirm names the armed mode")
	# Mutual exclusion, in both directions (spec "The action SHALL be mutually
	# exclusive with the delivered move, sell, and store modes"): the armed
	# upgrade refuses the other three by name.
	var arm_move_while_upgrading: Dictionary = town.arm_move()
	check(not bool(arm_move_while_upgrading.get("ok", true)),
		"arming a move while an upgrade is armed rejects")
	check_eq(str(arm_move_while_upgrading.get("code", "")),
		"upgrade_already_active",
		"the stacked-arm refusal names the armed mode")
	var arm_sell_while_upgrading: Dictionary = town.arm_sell()
	check(not bool(arm_sell_while_upgrading.get("ok", true)),
		"arming a sale while an upgrade is armed rejects")
	check_eq(str(arm_sell_while_upgrading.get("code", "")),
		"upgrade_already_active",
		"the stacked-arm refusal names the armed mode for the sale too")
	var arm_store_while_upgrading: Dictionary = town.arm_store()
	check(not bool(arm_store_while_upgrading.get("ok", true)),
		"arming a store while an upgrade is armed rejects")
	check_eq(str(arm_store_while_upgrading.get("code", "")),
		"upgrade_already_active",
		"the stacked-arm refusal names the armed mode for the store too")
	# A second upgrade arm is refused by name: the surface never stacks.
	var again: Dictionary = town.arm_upgrade()
	check(not bool(again.get("ok", true)),
		"arming an already-armed upgrade rejects")
	check_eq(str(again.get("code", "")), "upgrade_already_active",
		"the double-arm names the condition")
	check_eq(api.upgrade_requests, requests_before,
		"every refusal on this surface sent no request")
	check(town.upgrade_active(),
		"the refusals never disarm the upgrade in progress")
	# Cancelling here keeps the applied-state checks that follow on a clean
	# surface; the cancel contract itself is asserted in its own check.
	var released: Dictionary = town.cancel_upgrade()
	check(bool(released.get("ok", false)),
		"the upgrade closes for the cancel scenario: %s"
		% released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition (design D5: the client owns the
## gameplay rules the legacy server never enforced).
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# The confirm on a closed upgrade refuses by name and sends nothing.
	var closed: Dictionary = await town.confirm_upgrade()
	check(not bool(closed.get("ok", true)),
		"a closed upgrade refuses a confirm")
	check_eq(str(closed.get("code", "")), "upgrade_not_active",
		"the closed-upgrade refusal names the condition")
	check_eq(api.upgrade_requests, requests_before,
		"the closed-upgrade refusal sent no request")

	# Re-select the recorded building and arm once more for the
	# selection-changed refusal.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(UPGRADED_CELL))
	check(bool(press.get("ok", false)),
		"the building re-selects for the refusal checks: %s"
		% press.get("error"))
	var armed: Dictionary = town.arm_upgrade()
	check(bool(armed.get("ok", false)),
		"the upgrade re-arms: %s" % armed.get("error"))
	check_eq(api.upgrade_requests, requests_before, "re-arming sent no request")

	# A press while an upgrade is armed can move the selection (an upgrade
	# owns no grid target), and the confirm refuses that by name rather than
	# silently upgrading a building the player did not have selected.
	var elsewhere: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(elsewhere.get("ok", false)),
		"a press elsewhere still selects: %s" % elsewhere.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the press at (58,48) selects the Turret I")
	var re_targeted: Dictionary = await town.confirm_upgrade()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose selection moved refuses")
	check_eq(str(re_targeted.get("code", "")), "upgrade_selection_changed",
		"the re-target refusal names the condition: %s"
		% re_targeted.get("error"))
	check_eq(api.upgrade_requests, requests_before,
		"the re-target refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	# The armed upgrade survives every refusal (a refusal never disarms it),
	# so it is closed here and the cancel contract is asserted on its own.
	var closed_armed: Dictionary = town.cancel_upgrade()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed upgrade closes cleanly: %s"
		% closed_armed.get("error"))


## A cancelled upgrade drops only mode-local state: the serialized town state,
## the storage view, the readout, the selection, the resources, and the
## request count stay byte-identical.
func _check_cancelled_upgrade(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# Re-select the recorded building (the previous check moved the
	# selection) so the cancel is the state a player would be in.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(UPGRADED_CELL))
	check(bool(press.get("ok", false)), "the recorded building re-selects")
	var armed: Dictionary = town.arm_upgrade()
	check(bool(armed.get("ok", false)),
		"the upgrade arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var readout_before: Array = _storage_labels(town)
	var cancelled: Dictionary = town.cancel_upgrade()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the upgrade: %s" % cancelled.get("error"))
	check(not town.upgrade_active(), "the upgrade closes")
	check(town.upgrade_placement() == null, "the upgraded placement drops")
	check_eq(town.upgrade_slot(), TownState.NO_SLOT,
		"a closed upgrade names no index")
	check_eq(town.upgrade_target_item(), 0,
		"a closed upgrade names no target tier")
	check(not town.ui.is_slot_visible("move"),
		"the surface slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled upgrade")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS, "cancel renders nothing")
	check_eq(town.storage_rows(), ["(empty)"],
		"cancel leaves the storage view untouched")
	check_eq(_storage_labels(town), readout_before,
		"cancel leaves the on-screen readout untouched")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.upgrade_requests, requests_before, "cancel sent no request")
	var again: Dictionary = town.cancel_upgrade()
	check(not bool(again.get("ok", true)),
		"closing an already-closed upgrade rejects")
	check_eq(str(again.get("code", "")), "upgrade_not_active",
		"the double-close names the condition")
	check_eq(api.upgrade_requests, requests_before,
		"the double-close sent no request")


## The other direction of the four-mode mutual exclusion: an upgrade cannot
## be armed while a delivered mode already is. Runs on the spare building so
## the recorded building's selection stays untouched for the applied checks.
func _check_mutual_exclusion(town: Node2D, api: Variant,
		requests_before: int) -> void:
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(press.get("ok", false)),
		"the spare building selects for the exclusion checks: %s"
		% press.get("error"))
	var armed_store: Dictionary = town.arm_store()
	check(bool(armed_store.get("ok", false)),
		"the delivered store arms on the spare building: %s"
		% armed_store.get("error"))
	var upgrade_over_store: Dictionary = town.arm_upgrade()
	check(not bool(upgrade_over_store.get("ok", true)),
		"arming an upgrade while a store is armed rejects")
	check_eq(str(upgrade_over_store.get("code", "")), "store_already_active",
		"the refusal names the armed store: %s" % upgrade_over_store.get("error"))
	check(town.store_active(), "the armed store survives the refusal")
	town.cancel_store()
	var armed_sell: Dictionary = town.arm_sell()
	check(bool(armed_sell.get("ok", false)),
		"the delivered sale arms on the spare building: %s"
		% armed_sell.get("error"))
	var upgrade_over_sell: Dictionary = town.arm_upgrade()
	check(not bool(upgrade_over_sell.get("ok", true)),
		"arming an upgrade while a sale is armed rejects")
	check_eq(str(upgrade_over_sell.get("code", "")), "sell_already_active",
		"the refusal names the armed sale: %s" % upgrade_over_sell.get("error"))
	town.cancel_sell()
	var armed_move: Dictionary = town.arm_move()
	check(bool(armed_move.get("ok", false)),
		"the delivered move arms on the spare building: %s"
		% armed_move.get("error"))
	var upgrade_over_move: Dictionary = town.arm_upgrade()
	check(not bool(upgrade_over_move.get("ok", true)),
		"arming an upgrade while a move is armed rejects")
	check_eq(str(upgrade_over_move.get("code", "")), "move_already_active",
		"the refusal names the armed move: %s" % upgrade_over_move.get("error"))
	town.cancel_move()
	check_eq(api.upgrade_requests, requests_before,
		"every mutual-exclusion refusal sent no request")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: the same building's object carries the target tier
## at the same cell under the same legacy key, the typed row is the response's
## post-execution row, every other object keeps its committed depth position,
## the storage view and readout stay untouched, the resources and XP take the
## response's values, and the HUD re-reads from them — with BOTH counts
## unchanged, because the key is reused.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	# The mutual-exclusion check left the spare building selected, so the
	# recorded building is re-selected through the delivered press path before
	# the confirmed intent — exactly what a player would do.
	var reselect: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(UPGRADED_CELL))
	check(bool(reselect.get("ok", false)),
		"the recorded building re-selects for the confirmed intent: %s"
		% reselect.get("error"))
	check_eq(town.selection_legacy_id(), UPGRADED_ITEM,
		"the recorded building is the committed selection again")
	var object: Variant = _object_for_cell(town, UPGRADED_CELL)
	check(object != null, "the Wall I object is committed before the upgrade")
	if object == null:
		return
	var armed: Dictionary = town.arm_upgrade()
	check(bool(armed.get("ok", false)),
		"the upgrade arms for the confirmed intent: %s" % armed.get("error"))
	if not bool(armed.get("ok", false)):
		return
	check_eq(int(armed.get("target", 0)), UPGRADED_TARGET,
		"the armed upgrade names the Wall II as its target")
	var requests_before: int = api.upgrade_requests
	var snapshot_before := _state_snapshot(state)
	var signature_before := _object_signature(town)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var readout_before: Array = _storage_labels(town)
	var confirmed: Dictionary = await town.confirm_upgrade()
	check(bool(confirmed.get("ok", false)),
		"the confirmed upgrade succeeds: %s" % confirmed.get("error"))
	check_eq(api.upgrade_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	var typed_success: Variant = confirmed.get("result")
	check(typed_success is BootData.UpgradeResult,
		"the success envelope carries the typed upgrade result")
	if typed_success is BootData.UpgradeResult:
		var success: BootData.UpgradeResult = typed_success
		check_eq(success.protocol, BootData.PROTOCOL,
			"the upgrade protocol is compat-v0")
		check_eq(success.game_version, "alpha 0.02",
			"the upgrade response carries the game version")
		check(success.server_time > 0,
			"the upgrade server_time is the fixture epoch (time-dependent)")
		check_eq(success.result, "success",
			"the legacy result string is verbatim")
		check(success.removed != null,
			"the response carries the pre-execution row")
		check(success.upgraded != null,
			"the response carries the post-execution row")
		check(success.resources != null,
			"the response carries typed resources")
		if success.removed != null and success.upgraded == null:
			return
		if success.removed != null:
			_check_boot_row(success.removed, UPGRADED_ROW,
				"the removed row is the pre-execution row")
		if success.upgraded != null:
			check_eq(success.upgraded.item_id, UPGRADED_TARGET,
				"the upgraded row names the target tier (Wall II)")
			check_eq(success.upgraded.x, UPGRADED_CELL.x,
				"the upgraded row reuses the pre-execution x")
			check_eq(success.upgraded.y, UPGRADED_CELL.y,
				"the upgraded row reuses the pre-execution y")
			check(success.upgraded.timestamp > 0,
				"the upgraded row is freshly stamped (time-dependent field, "
				+ "never asserted by value)")
			check(success.upgraded.timestamp != int(UPGRADED_ROW[3]),
				"the fresh timestamp replaced the replaced row's")
			check_eq(success.upgraded.orientation, 0,
				"the upgraded row carries the row's own orientation")
			check_eq(success.upgraded.store, [],
				"the upgraded row's store is fresh and empty")
			check_eq(success.upgraded.attr, {"nc": 0},
				"the upgraded row carries the construction seed and nothing else")
			check_eq(success.upgraded.player, 1,
				"the upgraded row carries the row's own player field")
		if success.resources != null:
			# The derived vector is NEUTRAL, so a real upgrade changes no
			# balance and claims no cost (design D4).
			check_eq(success.resources.xp, 4, "xp follows the response")
			check_eq(success.resources.gold, 2000, "gold follows the response")
			check_eq(success.resources.wood, 2000, "wood follows the response")
			check_eq(success.resources.oil, 2000, "oil follows the response")
			check_eq(success.resources.steel, 2000, "steel follows the response")
			check_eq(success.resources.cash, 5, "cash follows the response")
			check_eq(success.resources.mana, 0, "mana follows the response")

	# The authoritative apply: the SAME placement instance now carries the
	# target tier at the same cell under the same key, and its row is the
	# response's post-execution row.
	var upgraded: Variant = _placement_by_slot(state, UPGRADED_SLOT)
	check(upgraded != null, "the recorded key is still addressable after the upgrade")
	check_eq(int(upgraded.item), UPGRADED_TARGET,
		"the recorded key now holds the target tier")
	check_eq(upgraded.slot, UPGRADED_SLOT, "the legacy key is unchanged")
	check_eq(upgraded.cell, UPGRADED_CELL, "the cell is unchanged")
	check(int(upgraded.timestamp) > 0,
		"the typed row carries the fresh timestamp")
	check_eq(upgraded.attr, {"nc": 0},
		"the typed row carries the construction seed")
	check(upgraded != null and _typed_row(upgraded.raw) != UPGRADED_ROW,
		"the typed row is no longer the pre-execution row")
	check_eq(state.placements.size(), PLACEMENTS,
		"the upgrade changes no placement count (the key is reused)")
	check_eq(town.objects.size(), PLACEMENTS,
		"the upgrade changes no object count (the key is reused)")
	check(town.upgrade_placement() == null,
		"the armed placement is released after the apply")
	check(not town.upgrade_active(), "the upgrade closes after the apply")
	# The rendered object at that cell is the target tier now, and every OTHER
	# object kept its exact committed depth position.
	var rendered: Variant = _object_for_cell(town, UPGRADED_CELL)
	check(rendered != null, "an object still renders at the same cell")
	if rendered != null:
		check_eq(int(rendered.legacy_id), UPGRADED_TARGET,
			"the same cell renders the target tier")
		check_eq(int(rendered.cell.x), UPGRADED_CELL.x,
			"the re-rendered object keeps the cell x")
		check_eq(int(rendered.cell.y), UPGRADED_CELL.y,
			"the re-rendered object keeps the cell y")
		check(rendered != object,
			"the object's visual was rebuilt for the new tier")
	var signature_after := _object_signature(town)
	var previous_depth := -1
	var depth_ordered := true
	for candidate: Variant in town.objects:
		var depth := Iso.depth_key(candidate.cell)
		if depth < previous_depth:
			depth_ordered = false
		previous_depth = depth
	check(depth_ordered,
		"the objects keep non-decreasing isometric depth")
	check_eq(town.objects.size(), town.objects_layer.get_child_count(),
		"the objects layer holds exactly the committed object list")
	var changed := 0
	for index in range(mini(signature_before.size(), signature_after.size())):
		if signature_before[index] != signature_after[index]:
			changed += 1
	check_eq(changed, 1,
		"exactly one rendered object changed (the upgraded one); every "
		+ "other object kept its committed depth position")
	check_eq(signature_before.size(), signature_after.size(),
		"the draw order kept its length")
	# The selection followed the building to its new tier.
	check(town.selection() != null,
		"the selection survives the upgrade (the building is still there)")
	if town.selection() != null:
		check_eq(int(town.selection().legacy_id), UPGRADED_TARGET,
			"the selection names the upgraded tier")
		check(town.selection().is_selected(),
			"the selection highlight follows the upgraded object")
	# The storage view and readout are untouched: an upgrade changes neither.
	check_eq(state.storage, storage_before, "the storage mapping is untouched")
	check_eq(town.storage_rows(), ["(empty)"],
		"the storage view is untouched by the upgrade")
	check_eq(_storage_labels(town), readout_before,
		"the on-screen readout is untouched by the upgrade")
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
	check_eq(town.upgrade_error, "", "success leaves no failure record")
	var status := String(_surface_status(town))
	check(status.contains("upgraded"),
		"the status names the completed upgrade: %s" % status)
	check(status.contains("none claimed"),
		"the status keeps the no-cost claim limit on screen")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")
	check_eq(api.upgrade_requests, requests_before + 1,
		"the apply issued no further request")


## The unknown-index failure: the intent names an index the service does not
## know (a stale client state — the endpoint resolves the index before
## executing and answers 404 `unknown_item_index`, so legacy's silent no-op is
## never reported as a success), the explicit error names that code, and the
## building stays at its current tier with the storage unchanged.
func _check_unknown_index(registry: Variant, api: Variant) -> void:
	var requests_before: int = api.upgrade_requests
	var ghost_town: Variant = _town_with_extra_row(registry)
	if ghost_town == null:
		return
	var snapshot_before := _state_snapshot(ghost_town.state)
	var armed: Dictionary = ghost_town.arm_upgrade()
	check(bool(armed.get("ok", false)),
		"the extra row arms an upgrade: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(ghost_town.upgrade_slot(), UNKNOWN_INDEX,
			"the armed upgrade names the unknown index")
		var failed: Dictionary = await ghost_town.confirm_upgrade()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s"
			% failed.get("error"))
		check(ghost_town.upgrade_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check_eq(ghost_town.objects.size(), PLACEMENTS + 1,
			"the structured failure removes nothing")
		check(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX) != null,
			"the unknown-index row is still in the typed state")
		check_eq(int(ghost_town.upgrade_placement().item), 23,
			"the unknown-index row keeps its current tier")
		check_eq(ghost_town.storage_rows(), ["(empty)"],
			"the structured failure leaves the readout untouched")
		check_eq(_state_snapshot(ghost_town.state), snapshot_before,
			"the structured failure changes no state at all")
		check(ghost_town.upgrade_active(),
			"the upgrade survives the structured failure")
		check_eq(int(ghost_town.upgrade_placement().cell.x), GHOST_CELL.x,
			"the unknown-index row stays at its own cell")
		# The upgrade is still armed and the row still there, so the surface
		# can be closed explicitly.
		var closed: Dictionary = ghost_town.cancel_upgrade()
		check(bool(closed.get("ok", false)),
			"the failed upgrade closes cleanly")
	ghost_town.free()
	check_eq(api.upgrade_requests, requests_before + 1,
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
		str(UNKNOWN_INDEX)] = [UPGRADED_ITEM, GHOST_CELL.x, GHOST_CELL.y,
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
			!= UPGRADED_ITEM:
		town.free()
		return null
	return town


## LAST scenario (it waits out the refused loopback endpoint): the intent
## goes out over the legacy transport, the endpoint refuses it, and the
## explicit error names `unreachable_endpoint` with the building still on the
## map at its CURRENT tier, the storage unchanged, and no resource changed
## (the same no-mutation contract as a structured failure).
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
	var armed: Dictionary = town.arm_upgrade()
	check(bool(armed.get("ok", false)),
		"the upgrade arms for the transport scenario: %s" % armed.get("error"))
	check_eq(town.upgrade_slot(), SPARE_SLOT,
		"the armed upgrade names the spare building's legacy key")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.upgrade_requests
	var snapshot_before := _state_snapshot(state)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var objects_before: int = town.objects.size()
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_upgrade()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.upgrade_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.upgrade_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(state.storage, storage_before,
		"the transport failure touches no storage")
	check_eq(town.storage_rows(), ["(empty)"],
		"the transport failure leaves the readout untouched")
	check_eq(town.objects.size(), objects_before,
		"the transport failure renders nothing new")
	check_eq(_placement_by_slot(state, SPARE_SLOT).item, SPARE_ITEM,
		"the spare building keeps its current tier after the transport failure")
	check(town.upgrade_active(),
		"the upgrade survives the transport failure")
	# The last state-changing check ran against the fake, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The unaddressable-row refusal (design D7 carried forward from
## building-move, building-sell, and building-store): a row whose save key is
## not a positive integer parses, renders, and is selectable, but the upgrade
## action is unavailable, arming is refused by name with the move flow's own
## reason, and NOTHING is sent — the index is never coerced, because a coerced
## index would name a different row.
func _check_unaddressable_refusal(state: Variant, registry: Variant,
		api: Variant, session: Variant, pid: String,
		summary: BootData.PlayerSummary) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		UPGRADED_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
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
	var requests_before: int = api.upgrade_requests
	var snapshot_before := _state_snapshot(town.state)
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the unaddressable row is selectable: %s" % pressed.get("error"))
	check_eq(town.selection_legacy_id(), UPGRADED_ITEM,
		"the unaddressable row is the committed selection")
	check(not town.upgrade_selection_available(),
		"an unaddressable row never offers the upgrade action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var upgrade_button: Variant = _button_named(panel as Node, "upgrade")
		check(upgrade_button is Button and (upgrade_button as Button).disabled,
			"the upgrade action is disabled for an unaddressable row")
		check(String(_surface_status(town)).contains("not movable"),
			"the status keeps the delivered unaddressable line")
	var refused: Dictionary = town.arm_upgrade()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the move flow's own unaddressable reason: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check(not town.upgrade_active(),
		"no upgrade opens for an unaddressable row")
	check_eq(api.upgrade_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The no-upgrade-path refusal (design D3 carried into the client): a placed
## building whose item's committed configuration reference means NO PATH — the
## Tree decoration and a Bridge, both `upgrades_to` `-1` — is selectable and
## renderable, but the action is never offered, arming is refused by name, and
## NOTHING is sent. A building that cannot be upgraded is never reduced to a
## bare sale, so the client never offers what the endpoint would refuse.
func _check_no_upgrade_path_refusal(registry: Variant, api: Variant,
		session: Variant, pid: String, summary: BootData.PlayerSummary) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var parsed: Dictionary = TownState.parse(payload as Dictionary, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "the no-upgrade-path fixture parses: %s"
			% parsed.get("error"))
		return
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		check(false, "the no-upgrade-path town builds")
		town.free()
		return
	var requests_before: int = api.upgrade_requests
	var snapshot_before := _state_snapshot(town.state)
	for entry in [
			[NO_PATH_TREE_SLOT, NO_PATH_TREE_ITEM, NO_PATH_TREE_CELL],
			[NO_PATH_BRIDGE_SLOT, NO_PATH_BRIDGE_ITEM, NO_PATH_BRIDGE_CELL],
	]:
		var slot: int = int(entry[0])
		var item: int = int(entry[1])
		var cell: Vector2i = entry[2]
		var placement: Variant = _placement_by_slot(town.state, slot)
		check(placement != null,
			"the no-path building at key %d is addressable" % slot)
		var press: Dictionary = town.handle_pointer_press(
			Iso.grid_to_screen(cell))
		check(bool(press.get("ok", false)),
			"item %d is selectable: %s" % [item, press.get("error")])
		check_eq(town.selection_legacy_id(), item,
			"item %d is the committed selection" % item)
		check(not town.upgrade_selection_available(),
			"item %d has no resolvable next tier, so no action is offered" % item)
		check_eq(town.upgrade_target_item(), 0,
			"item %d names no target tier" % item)
		var panel: Variant = _surface_panel(town)
		if panel != null:
			var button: Variant = _button_named(panel as Node, "upgrade")
			check(button is Button and (button as Button).disabled,
				"the upgrade action is disabled for item %d" % item)
			check_eq((button as Button).text, "Upgrade (unavailable)",
				"the action names its own unavailability for item %d" % item)
		var refused: Dictionary = town.arm_upgrade()
		check(not bool(refused.get("ok", true)),
			"arming item %d fails" % item)
		check_eq(str(refused.get("code", "")), "no_upgrade_path",
			"the refusal names the no-upgrade-path condition for item %d: %s"
			% [item, refused.get("error")])
		check(not town.upgrade_active(),
			"no upgrade opens for item %d" % item)
		check_eq(api.upgrade_requests, requests_before,
			"the no-upgrade-path refusal for item %d sent no request" % item)
		check_eq(_state_snapshot(town.state), snapshot_before,
			"the no-upgrade-path refusals change no state")
		check_eq(_placement_by_slot(town.state, slot).item, item,
			"item %d keeps its tier on the map" % item)
	town.free()


## The live-upgrade scenario (verify-boot's upgrade-live phase): one typed
## intent through the real Compatibility endpoint, so the unchanged legacy
## `command()` executes the derived two-command pair over the disposable
## corpus. This side asserts the documented typed response AND the fact this
## line's endpoint proves — the response's key and cell match the pre-request
## row; the phase harness separately asserts the corpus save file mutated. No
## fixture is touched.
func _check_live_upgrade() -> void:
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
	# The pre-request row, read from the corpus itself (this phase has
	# already executed the placement, purchase, move, sell, and store
	# transactions), so the reused key and the reused cell are compared
	# against the state the service actually held — not against a fixture.
	var before_row: Variant = await _live_row(api, endpoint, pid, UPGRADED_SLOT)
	check(before_row != null, "the corpus pre-upgrade row resolves")
	if before_row == null:
		return
	var upgraded: Variant = await api.upgrade_building(pid, UPGRADED_SLOT)
	check(upgraded is BootData.UpgradeResult,
		"the live upgrade returns a typed result")
	if not (upgraded is BootData.UpgradeResult):
		return
	var typed := upgraded as BootData.UpgradeResult
	check(typed.ok, "the live upgrade succeeds: %s / %s" % [
		typed.error_code, typed.error_message])
	if not typed.ok or typed.removed == null or typed.upgraded == null \
			or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live upgrade protocol is compat-v0")
	check(typed.game_version != "",
		"the live upgrade response carries the game version")
	check(typed.server_time > 0,
		"the live server_time is a positive wall-clock epoch")
	check_eq(typed.result, "success",
		"the legacy result string is verbatim")
	# `removed` is the row AS READ BEFORE EXECUTION and `upgraded` the row
	# re-read from the save after it; the key and the cell are the ones this
	# line's endpoint proves are REUSED.
	var prior := before_row as Array
	check_eq(int(typed.removed.item_id), int(prior[0]),
		"the live removed row names the corpus's own item")
	check_eq([int(typed.removed.x), int(typed.removed.y)],
		[int(prior[1]), int(prior[2])],
		"the live removed row carries the corpus's own cell")
	check_eq(typed.upgraded.item_id, UPGRADED_TARGET,
		"the live upgraded row holds the derived target tier")
	check_eq([int(typed.upgraded.x), int(typed.upgraded.y)],
		[int(prior[1]), int(prior[2])],
		"the live upgraded row sits at the pre-execution cell (the key is "
		+ "reused)")
	check(typed.upgraded.timestamp > 0,
		"the live upgraded row is freshly stamped (time-dependent field)")
	check_eq(typed.upgraded.attr, {"nc": 0},
		"the live upgraded row carries the construction seed")
	check_eq(typed.upgraded.store, [],
		"the live upgraded row's store is fresh and empty")
	# The neutral vector changes no resource, so no upgrade cost is claimed.
	check_eq(typed.resources.xp, int(prior[8]) if prior.size() > 8 else 0,
		"xp follows the corpus's own value (the neutral vector)")
	check(typed.resources.gold > 0 and typed.resources.cash >= 0,
		"the live upgrade carries the corpus's own resource bag")
	# The key survives the pair: the same index is still addressable, and it
	# now resolves to the NEXT tier (the row was replaced, not consumed).
	var after_row: Variant = await _live_row(api, endpoint, pid, UPGRADED_SLOT)
	check(after_row != null, "the corpus post-upgrade row resolves")
	if after_row != null:
		check_eq(int((after_row as Array)[0]), UPGRADED_TARGET,
			"the corpus still holds the upgraded tier at the same key")
		check_eq([int((after_row as Array)[1]), int((after_row as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not re-keyed)")
	# A stale index fails closed with the endpoint's own code rather than
	# reporting a success for an upgrade that never happened.
	var unknown: Variant = await api.upgrade_building(pid, UNKNOWN_INDEX)
	check(unknown is BootData.UpgradeResult,
		"the live unknown index returns the typed result")
	if unknown is BootData.UpgradeResult:
		var failure: BootData.UpgradeResult = unknown
		check(not failure.ok, "the live unknown index is a structured failure")
		check_eq(failure.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(failure.removed == null and failure.upgraded == null
			and failure.resources == null,
			"the live structured failure carries no partial payload")
	# The fake derives the same code for the same intent, offline.
	api.configure("fake")
	var fake_unknown: Variant = await api.upgrade_building(pid, UNKNOWN_INDEX)
	check(fake_unknown is BootData.UpgradeResult and not fake_unknown.ok,
		"the fake fails the same intent offline")
	if fake_unknown is BootData.UpgradeResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-upgrade applied item_index=%d cell=(%d, %d) tier=%d "
		% [UPGRADED_SLOT, typed.upgraded.x, typed.upgraded.y,
			typed.upgraded.item_id]
		+ "xp=%d gold=%d" % [typed.resources.xp, typed.resources.gold])


## The corpus's own eight-field row at one legacy key, read from its
## bootstrap payload, or null when it cannot be read. This is the
## pre-request reference the live upgrade's reused key and cell are compared
## against — read from the service's own state, never from the fake's
## fixture, because the live side has already executed every earlier
## transaction in this phase.
func _live_row(api: Variant, endpoint: String, user_id: String,
		item_index: int) -> Variant:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return null
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return null
	var raw: Dictionary = (info as BootData.PlayerInfoPayload).raw
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var row: Variant = (map.get("items", {}) as Dictionary).get(str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		check(false, "the live corpus row at key %d is an eight-field array"
			% item_index)
		return null
	# The resources travel with the reference so the neutral vector can be
	# compared against the corpus's OWN values (this phase has already
	# executed the earlier transactions).
	var player: Dictionary = raw.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = raw.get("privateState", {}) as Dictionary
	return [int((row as Array)[0]), int((row as Array)[1]),
		int((row as Array)[2]), int((row as Array)[3]),
		int((row as Array)[4]), (row as Array)[5], (row as Array)[6],
		int((row as Array)[7]), int(map.get("xp", 0)),
		int(map.get("gold", 0)), int(map.get("wood", 0)),
		int(map.get("oil", 0)), int(map.get("steel", 0)),
		int(player.get("cash", 0)), int(priv.get("mana", 0))]


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


## The committed draw order as one `item@cell` string per object, so a run can
## prove that an upgrade changed exactly one object's identity and left every
## other object's committed DEPTH POSITION alone.
func _object_signature(town: Variant) -> Array:
	var rows: Array = []
	for object: Variant in town.objects:
		rows.append("%d@%d,%d" % [int(object.legacy_id), int(object.cell.x),
			int(object.cell.y)])
	return rows


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


## One typed `BootData.Placement` compared field by field against an expected
## eight-field row, so a mismatch names the field instead of printing two
## whole rows.
func _check_boot_row(entry: Variant, expected: Array, label: String) -> void:
	if entry == null or not (entry is BootData.Placement):
		check(false, label + " is a typed placement entry")
		return
	var typed: BootData.Placement = entry
	check_eq(typed.item_id, int(expected[0]), label + " names the same item")
	check_eq(typed.x, int(expected[1]), label + " carries the same x")
	check_eq(typed.y, int(expected[2]), label + " carries the same y")
	check_eq(typed.timestamp, int(expected[3]),
		label + " carries the same timestamp")
	check_eq(typed.orientation, int(expected[4]),
		label + " carries the same orientation")
	check_eq(typed.store.size(), 0, label + " carries an empty store")
	check_eq(typed.player, int(expected[7]), label + " carries the same player")


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-upgrade and failure paths). The
## storage mapping is part of it, so an upgrade that wrongly changed it can
## never look byte-identical.
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
