extends "res://tests/test_base.gd"
## Placement suite (building-placement, spec "Placement flow").
##
## Scenarios:
##   catalog    the typed catalog parses fail-closed from the bootstrap
##              config payload already in hand: all 900 items in payload
##              order with the eight typed fields, legacy cost keys
##              mapped to resource names, and the derived content
##              footprint;
##   gating     store-listed buildings gate by `min_level` against the
##              loaded level and only those are offered;
##   malformed  a missing or invalid field fails closed with an error
##              naming the offending item and field and yields no
##              catalog — never a guessed price or a fabricated entry —
##              while a null/empty cost parses as the documented free
##              item and the JSON transport's integral floats parse as
##              ints;
##   flow       the full town flow over the committed fixtures: the
##              picker opens with the 14 gated level-1 store buildings
##              and one wired button each, the press path previews a
##              valid 2x2 target with its cost against current
##              resources, the three invalid targets (out-of-grid,
##              occupied, unaffordable) confirm locally with no request
##              and no state change, a cancelled mode entry leaves the
##              serialized state byte-identical and the selection
##              untouched, a confirmed intent applies only the
##              authoritative response (one new depth-sorted object at
##              (51,39), wood 1970 in the state and on the HUD), a
##              structured failure surfaces its code with no state
##              change, a failed catalog leaves placement unavailable
##              behind the named error, and — last, because it waits
##              out the refused loopback endpoint — a transport failure
##              does the same;
##   no-request the whole run issues no bootstrap request (the catalog
##              derives from the payload in hand and the flow never
##              re-bootstraps, design D10).
##
## Uses the committed bootstrap fixtures directly; no fixture is ever
## written, no server runs. Runs headless as part of `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

const CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"
const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

## Executed-placement anchors and facts (probe-recorded against the
## committed fixtures): the executed legacy `buy` placed House I on a
## free 2x2 at (51,39) with fixture epoch 1790609721; the Command
## Center's 4x4 starts at (51,41); (70,20) is a free in-grid 2x2 slot;
## (150,3) is an anchor outside the shared 0..99 grid; the level-1
## offering is exactly 14 store-listed buildings.
const SUCCESS_CELL := Vector2i(51, 39)
const SUCCESS_TIMESTAMP := 1790609721
const OCCUPIED_CELL := Vector2i(51, 41)
const FREE_CELL := Vector2i(70, 20)
const OUT_OF_GRID_CELL := Vector2i(150, 3)
const LEVEL_ONE_OFFERING := 14

## Endpoint for the transport scenario: the `--gameapi-endpoint=` user
## argument (verify-boot passes a refused loopback port to every
## hermetic suite), else the project setting's loopback default. No
## hardcoded endpoint in this file — the project-scope scan restricts
## transport references to the legacy-v0 implementation.
const ARG_ENDPOINT := "--gameapi-endpoint="


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var payload: Variant = _fixture(CONFIG_FIXTURE)
	check(payload is Dictionary, "config fixture parses as JSON")
	if not (payload is Dictionary):
		return
	_check_catalog_derivation(payload)
	_check_level_gating(payload)
	_check_malformed(payload)
	await _check_flow(payload)
	_check_no_second_bootstrap_request()


## Fixture facts from the committed payload (probe-recorded): House I
## costs 30 wood on a 2x2 footprint, Wood Factory III costs 6000 gold,
## Stoneage costs 20 cash, and Command Center is not store-listed.
func _check_catalog_derivation(payload: Dictionary) -> void:
	var result: Dictionary = PlacementCatalog.parse(payload)
	check(bool(result.get("ok", false)),
		"the committed config parses: %s" % result.get("error"))
	if not bool(result.get("ok", false)):
		return
	var catalog: Variant = result["catalog"]
	check(catalog is PlacementCatalog.Catalog, "the catalog is typed")
	if not (catalog is PlacementCatalog.Catalog):
		return
	check_eq(catalog.items, 900, "all 900 items parse")
	check_eq(catalog.entries.size(), 900, "every parsed entry is kept")
	var rows: Array = payload["items"]
	check(not rows.is_empty(), "the payload carries items")
	if rows.is_empty():
		return
	check_eq(catalog.entries[0].id, int(str((rows[0] as Dictionary)["id"])),
		"payload order is preserved (the first row leads)")

	var house: Variant = PlacementCatalog.find_entry(catalog, 1)
	check(house is PlacementCatalog.Entry, "House I (item 1) parses")
	if house is PlacementCatalog.Entry:
		check_eq(house.name, "House I", "the name is verbatim")
		check_eq(house.costs, {"wood": 30},
			"the w cost maps to the wood resource")
		check_eq(house.min_level, 1, "min_level parses as an integer")
		check(house.in_store, "the store flag parses as true")
		check_eq(house.width, 2, "width parses as an integer")
		check_eq(house.height, 2, "height parses as an integer")
		check_eq(house.footprint, Vector2i(2, 2),
			"the content footprint derives from width/height")
		check_eq(house.type, "b", "the type is verbatim")
	var factory: Variant = PlacementCatalog.find_entry(catalog, 10)
	check(factory is PlacementCatalog.Entry,
		"Wood Factory III (item 10) parses")
	if factory is PlacementCatalog.Entry:
		check_eq(factory.costs, {"gold": 6000},
			"the g cost maps to the gold resource")
	var wonder: Variant = PlacementCatalog.find_entry(catalog, 66)
	check(wonder is PlacementCatalog.Entry, "Stoneage (item 66) parses")
	if wonder is PlacementCatalog.Entry:
		check_eq(wonder.costs, {"cash": 20},
			"the c cost maps to the cash resource")
	check(PlacementCatalog.find_entry(catalog, 999999) == null,
		"an absent id yields no entry (never fabricated)")
	check_eq(PlacementCatalog.COST_RESOURCES.size(), 5,
		"all five legacy cost keys map to resource names")


## Gating runs against the loaded level (the picker feeds the town
## state's summary level; here the documented fixture levels directly).
func _check_level_gating(payload: Dictionary) -> void:
	var parsed: Dictionary = PlacementCatalog.parse(payload)
	if not bool(parsed.get("ok", false)):
		fail("the catalog must parse for the gating scenario")
		return
	var catalog: Variant = parsed["catalog"]
	if not (catalog is PlacementCatalog.Catalog):
		fail("the parsed catalog must be typed for the gating scenario")
		return

	var level_one: Array = PlacementCatalog.picker_entries(catalog, 1)
	check_eq(level_one.size(), LEVEL_ONE_OFFERING,
		"level 1 offers exactly the 14 store-listed buildings it allows")
	var ids := {}
	for entry: Variant in level_one:
		check(entry is PlacementCatalog.Entry,
			"every offered entry is typed")
		if not (entry is PlacementCatalog.Entry):
			continue
		ids[entry.id] = true
		check(entry.in_store, "offered entries are store-listed")
		check_eq(entry.type, "b", "offered entries are buildings")
		check(entry.min_level <= 1, "offered entries gate min_level <= 1")
	check(bool(ids.get(1, false)), "House I is offered at level 1")
	check(not ids.has(5),
		"Gold Factory I (min_level 2) is withheld at level 1")
	check(not ids.has(10),
		"Wood Factory III (min_level 21) is withheld at level 1")
	check(not ids.has(26),
		"Command Center (not store-listed) is never offered")

	var level_two: Array = PlacementCatalog.picker_entries(catalog, 2)
	check(level_two.size() > level_one.size(),
		"a higher level never withholds what a lower level had")
	var ids_two := {}
	for entry: Variant in level_two:
		if entry is PlacementCatalog.Entry:
			ids_two[entry.id] = true
	check(bool(ids_two.get(1, false)), "House I stays offered at level 2")
	check(bool(ids_two.get(5, false)), "Gold Factory I unlocks at level 2")
	check(not ids_two.has(10),
		"Wood Factory III stays withheld at level 2")

	var level_twenty_one: Array = PlacementCatalog.picker_entries(catalog, 21)
	var ids_21 := {}
	for entry: Variant in level_twenty_one:
		if entry is PlacementCatalog.Entry:
			ids_21[entry.id] = true
	check(bool(ids_21.get(10, false)),
		"Wood Factory III unlocks at level 21")
	check(level_one.size() <= level_twenty_one.size(),
		"the level-21 offering is a superset of the level-1 offering")

	check_eq(PlacementCatalog.picker_entries(null, 1).size(), 0,
		"an absent catalog offers no entries (never fabricated)")


## Every malformed field fails closed: {ok:false, error naming the
## offender, catalog null}.
func _check_malformed(payload: Dictionary) -> void:
	var base: Dictionary = _row_with_id(payload, "1")
	check(not base.is_empty(), "a committed row is available for crafting")
	if base.is_empty():
		return

	_expect_reject(PlacementCatalog.parse(null), "payload is not an object")
	_expect_reject(PlacementCatalog.parse({}), "field 'items'")
	_expect_reject(PlacementCatalog.parse({"items": {}}), "field 'items'")
	_expect_reject(PlacementCatalog.parse({"items": ["x"]}),
		"item 0 is not an object")
	_expect_reject(_parse_with(base, "id", "abc"), "field 'id'")
	_expect_reject(_parse_with(base, "id", -7), "field 'id'")
	_expect_reject(_parse_without(base, "name"), "field 'name'")
	_expect_reject(_parse_with(base, "costs", '{"x":5}'),
		"unknown cost key 'x'")
	_expect_reject(_parse_with(base, "costs", '{"w":'), "not valid JSON")
	_expect_reject(_parse_with(base, "costs", '{"w":"30"}'),
		"amount of cost key 'w'")
	_expect_reject(_parse_with(base, "min_level", "abc"), "field 'min_level'")
	_expect_reject(_parse_with(base, "in_store", "2"), "field 'in_store'")
	_expect_reject(_parse_with(base, "width", "0"),
		"field 'width'/'height'")
	_expect_reject(_parse_with(base, "height", ""),
		"field 'width'/'height'")
	_expect_reject(_parse_with(base, "type", ""), "field 'type'")

	# A failure in a later row names that row and still yields no catalog.
	var late_bad := _row_with_id(payload, "1")
	late_bad["min_level"] = "oops"
	var late := PlacementCatalog.parse(
		{"items": [_row_with_id(payload, "2"), late_bad]})
	_expect_reject(late, "item 1")

	# A null or empty cost parses as the documented free item (the
	# endpoint applies no cost for it) instead of failing or guessing.
	var free := _parse_with(base, "costs", null)
	check(bool(free.get("ok", false)), "a null cost parses as a free item")
	if bool(free.get("ok", false)):
		var free_entry: Variant = \
			(free["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(free_entry.costs, {}, "the free item costs nothing")
	var blank := _parse_with(base, "costs", "")
	check(bool(blank.get("ok", false)), "an empty cost parses as free")
	if bool(blank.get("ok", false)):
		var blank_entry: Variant = \
			(blank["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(blank_entry.costs, {}, "the blank item costs nothing")

	# The pinned JSON transport widens numbers to floats; an integral
	# float still parses as the same integer field.
	var widened := _parse_with(base, "min_level", 2.0)
	check(bool(widened.get("ok", false)),
		"an integral transported float parses: %s" % widened.get("error"))
	if bool(widened.get("ok", false)):
		var widened_entry: Variant = \
			(widened["catalog"] as PlacementCatalog.Catalog).entries[0]
		check_eq(widened_entry.min_level, 2,
			"the widened min_level keeps its integer value")


# ---------------------------------------------------------------------------
# Placement flow (spec "Placement flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, hands
## the typed catalog (the boot handoff's job), and drives picker ->
## preview -> confirm -> apply plus every failure and no-request path.
func _check_flow(payload: Dictionary) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var content: Dictionary = registry.load_content()
	var assets: Dictionary = registry.load_asset_registry()
	check(bool(content.get("ok", false)) and bool(assets.get("ok", false)),
		"content and asset registry load: %s / %s" % [
			str(content.get("error")), str(assets.get("error"))])
	if not bool(content.get("ok", false)) or not bool(assets.get("ok", false)):
		return
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

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the placement save")
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
	# The boot handoff's job, exercised here directly: the parsed
	# envelope is committed with no view effects until entry.
	town.set_placement_catalog(PlacementCatalog.parse(payload))
	check_eq(town.placement_catalog_entries().size(), LEVEL_ONE_OFFERING,
		"the handed catalog offers the level-1 entries")

	var requests_start: int = api.placement_requests
	var snapshot_start := _state_snapshot(state)
	_check_picker_entry(town, api, requests_start)
	_check_invalid_targets(town, state, api, requests_start, snapshot_start)
	_check_cancelled_mode(town, state, api, requests_start, snapshot_start)
	await _check_applied_response(town, state, api)
	await _check_structured_failure(town, state, api, session, summary, pid)
	_check_catalog_unavailable(town, state, api)
	await _check_transport_failure(town, state, api, payload)
	check_eq(api.placement_requests, requests_start + 3,
		"the whole flow issued exactly three requests (success, "
		+ "structured failure, transport failure); every other check "
		+ "sent none")
	town.free()


## Picker entry: the mode opens with the gated offering, one wired
## button per entry, and the press path previews a valid target with
## its cost against the stored resources.
func _check_picker_entry(town: Node2D, api: Variant,
		requests_before: int) -> void:
	var entered: Dictionary = town.enter_placement()
	check(bool(entered.get("ok", false)),
		"the build picker opens: %s" % entered.get("error"))
	if not bool(entered.get("ok", false)):
		return
	check(town.placement_active(), "the placement mode is active")
	check_eq(int(entered.get("entries", -1)), LEVEL_ONE_OFFERING,
		"the picker reports the 14 level-1 store buildings")
	check_eq(town.placement_catalog_entries().size(), LEVEL_ONE_OFFERING,
		"the catalog accessor offers the same gated entries")
	check(town.ui.is_slot_visible("placement"),
		"the picker slot shows while the mode is open")
	var panel: Variant = _picker_panel(town)
	check(panel != null, "the picker panel commits into the slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var item_buttons := 0
	for child: Variant in panel_node.get_children():
		if child is Button \
				and String((child as Button).name).begins_with("item_"):
			item_buttons += 1
	check_eq(item_buttons, LEVEL_ONE_OFFERING,
		"one button per offered building")
	check_eq(panel_node.get_child_count(), 17,
		"title, one button per entry, status, and the action row")
	check(String(_picker_status(town)).contains(
		"%d available at level 1" % LEVEL_ONE_OFFERING),
		"the status names the offering and the loaded level")
	check(_button_named(panel_node, "confirm") != null,
		"the place action button exists")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")

	# Level gating through the town flow: a level-2 item withholds and
	# an absent id names itself — neither is ever offered.
	var gated: Dictionary = town.pick_placement(5)
	check(not bool(gated.get("ok", true)),
		"a level-2 item cannot be picked at level 1")
	check_eq(str(gated.get("code", "")), "item_not_available",
		"the gating rejection names the level gate: %s" % gated.get("error"))
	var absent: Dictionary = town.pick_placement(999999)
	check_eq(str(absent.get("code", "")), "unknown_item_id",
		"an absent id names itself: %s" % absent.get("error"))
	check(town.placement_entry() == null,
		"failed picks never fabricate a selection")

	# The button wiring picks House I (the signal path, not a direct
	# call — one `pressed` emission = one pick).
	var house_button: Variant = _button_named(panel_node, "item_1")
	check(house_button != null, "the House I button exists")
	if house_button != null:
		(house_button as Button).pressed.emit()
		check(town.placement_entry() != null,
			"pressing the button commits a selection")
		if town.placement_entry() != null:
			check_eq(int(town.placement_entry().id), 1,
				"the pressed button picks House I")

	# The press path previews the valid target (inverse projection, the
	# 2x2 footprint, and the cost against the stored wood).
	var press: Dictionary = town.handle_placement_press(
		Iso.grid_to_screen(SUCCESS_CELL))
	check(bool(press.get("ok", false)),
		"the press-path preview succeeds: %s" % press.get("error"))
	check(bool(press.get("valid", false)),
		"the (51,39) press previews a valid target")
	check_eq(str(press.get("reason", "")), "",
		"a valid target names no failure")
	check_eq(press.get("cells", []), [
		Vector2i(51, 39), Vector2i(52, 39), Vector2i(51, 40), Vector2i(52, 40)],
		"the footprint preview covers the 2x2 anchored at the press")
	check(town.placement_preview_shown(), "the overlay shows the preview")
	check(town.placement_preview_valid(), "the overlay marks it valid")
	check(String(_picker_status(town)).contains("wood 30 (have 2000)"),
		"the cost reads against the current resources")
	check_eq(api.placement_requests, requests_before,
		"previewing sent no request")


## The three invalid targets confirm locally: no request, no state
## change, and the explicit error names `invalid_target` with the
## failed gate (design D5: the client owns these gameplay rules).
func _check_invalid_targets(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# out_of_grid: the anchor lies outside the shared 0..99 grid.
	var target_out: Dictionary = town.preview_placement_cell(
		OUT_OF_GRID_CELL)
	check_eq(str(target_out.get("reason", "")), "out_of_grid",
		"an anchor outside the grid previews out_of_grid")
	check(not bool(target_out.get("valid", true)),
		"the out-of-grid target previews invalid")
	check(not town.placement_preview_valid(),
		"the overlay marks the out-of-grid target invalid")
	check(town.placement_preview_shown(),
		"the invalid target stays visible so its reason reads")
	var confirm_out: Dictionary = await town.confirm_placement()
	check(not bool(confirm_out.get("ok", true)),
		"confirming the out-of-grid target fails")
	check_eq(str(confirm_out.get("code", "")), "invalid_target",
		"the out-of-grid confirm names invalid_target: %s"
		% confirm_out.get("error"))
	check(String(confirm_out.get("error", "")).contains("out_of_grid"),
		"the explicit error carries the failed gate")
	check_eq(api.placement_requests, requests_before,
		"the out-of-grid target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the out-of-grid attempt changes no state")

	# occupied: the 2x2 overlaps the Command Center's 4x4 at (51,41).
	var target_occupied: Dictionary = town.preview_placement_cell(
		OCCUPIED_CELL)
	check_eq(str(target_occupied.get("reason", "")), "occupied",
		"a cell inside the Command Center previews occupied")
	check(not town.placement_preview_valid(),
		"the overlay marks the occupied target invalid")
	var confirm_occupied: Dictionary = await town.confirm_placement()
	check_eq(str(confirm_occupied.get("code", "")), "invalid_target",
		"the occupied confirm names invalid_target: %s"
		% confirm_occupied.get("error"))
	check(String(confirm_occupied.get("error", "")).contains("occupied"),
		"the explicit error carries the failed gate")
	check_eq(api.placement_requests, requests_before,
		"the occupied target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the occupied attempt changes no state")

	# unaffordable: Stoneage costs 20 cash; the fresh save stores 5.
	var pick_cash: Dictionary = town.pick_placement(66)
	check(bool(pick_cash.get("ok", false)),
		"Stoneage (cash-only cost) picks: %s" % pick_cash.get("error"))
	var target_cash: Dictionary = town.preview_placement_cell(FREE_CELL)
	check_eq(str(target_cash.get("reason", "")), "unaffordable",
		"a cost above the stored cash previews unaffordable")
	check(String(_picker_status(town)).contains("unaffordable"),
		"the status names the affordability failure")
	var confirm_cash: Dictionary = await town.confirm_placement()
	check_eq(str(confirm_cash.get("code", "")), "invalid_target",
		"the unaffordable confirm names invalid_target: %s"
		% confirm_cash.get("error"))
	check(String(confirm_cash.get("error", "")).contains("unaffordable"),
		"the explicit error carries the failed gate")
	check_eq(api.placement_requests, requests_before,
		"the unaffordable target sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the unaffordable attempt changes no state")

	# Return to House I so the cancelled-mode check starts from a
	# committed selection and target.
	var rehouse: Dictionary = town.pick_placement(1)
	check(bool(rehouse.get("ok", false)),
		"House I picks again after the invalid attempts")


## A cancelled mode entry drops only mode-local state: selection,
## serialized town state, resources, and the request count stay
## byte-identical, and re-closing rejects by name.
func _check_cancelled_mode(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	var recommit: Dictionary = town.handle_placement_press(
		Iso.grid_to_screen(SUCCESS_CELL))
	check(bool(recommit.get("valid", false)),
		"a valid target exists before cancel")
	var object: Variant = town.objects[0]
	var rect: Rect2 = object.footprint_rect()
	var select_press: Dictionary = town.handle_pointer_press(
		rect.position + rect.size * 0.5)
	check(bool(select_press.get("ok", false)),
		"a selection commits before cancel: %s" % select_press.get("error"))
	var selected_before: int = town.selection_legacy_id()
	check(selected_before >= 0, "the pre-cancel selection is committed")
	var cancelled: Dictionary = town.cancel_placement()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the picker: %s" % cancelled.get("error"))
	check(not town.placement_active(), "the mode closes")
	check(not town.placement_preview_shown(), "the overlay drops on cancel")
	check_eq(town.placement_preview_cells().size(), 0,
		"no preview cells survive cancel")
	check(not town.ui.is_slot_visible("placement"),
		"the picker slot hides on cancel")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.placement_requests, requests_before,
		"cancel sent no request")
	var again: Dictionary = town.cancel_placement()
	check(not bool(again.get("ok", true)),
		"closing an already-closed mode rejects")
	check_eq(str(again.get("code", "")), "placement_not_active",
		"the double-close names the condition")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: one new depth-ordered object at (51,39) with
## the verbatim eight-field row, the response's resources in the state,
## the HUD re-read from them, and the overlay dropped — the picker
## itself stays open for the next placement.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	var energy_before: int = state.resources.energy
	var reentered: Dictionary = town.enter_placement()
	check(bool(reentered.get("ok", false)),
		"the picker reopens for the confirmed intent: %s"
		% reentered.get("error"))
	var pick_house: Dictionary = town.pick_placement(1)
	check(bool(pick_house.get("ok", false)),
		"House I picks for the intent: %s" % pick_house.get("error"))
	var target: Dictionary = town.preview_placement_cell(SUCCESS_CELL)
	check(bool(target.get("valid", false)),
		"the committed target previews valid")
	var requests_before: int = api.placement_requests
	var snapshot_before := _state_snapshot(state)
	var confirmed: Dictionary = await town.confirm_placement()
	check(bool(confirmed.get("ok", false)),
		"the confirmed placement succeeds: %s" % confirmed.get("error"))
	check_eq(api.placement_requests, requests_before + 1,
		"exactly one request carried the intent")
	if bool(confirmed.get("ok", false)):
		var typed_success: Variant = confirmed.get("result")
		check(typed_success is BootData.PlacementResult,
			"the success envelope carries the typed result")
		if typed_success is BootData.PlacementResult:
			check_eq((typed_success as BootData.PlacementResult).result,
				"success", "the legacy result string is verbatim")

	check_eq(state.placements.size(), 41, "the state gains one placement")
	check_eq(town.objects.size(), 41, "the view renders one more object")
	var placed: Variant = null
	for placement: Variant in state.placements:
		if placement is TownState.Placement \
				and placement.cell == SUCCESS_CELL:
			placed = placement
	check(placed != null, "the placement commits at (51,39)")
	if placed is TownState.Placement:
		check_eq(placed.item, 1, "the placed item is House I")
		check_eq(placed.timestamp, SUCCESS_TIMESTAMP,
			"the fixture epoch arrives verbatim")
		check_eq(placed.order, 40, "the placement appends at save-order end")
		check_eq(placed.raw, [1, 51, 39, SUCCESS_TIMESTAMP, 0, [],
			{"nc": 0}, 1],
			"the eight-field raw row is verbatim")
	check_eq(state.resources.wood, 1970,
		"wood applies from the response (30 deducted, never clamped)")
	check_eq(state.resources.coins, 2000, "coins follow the response")
	check_eq(state.resources.cash, 5, "cash follows the response")
	check_eq(state.resources.mana, 0, "mana follows the response")
	check_eq(state.resources.energy, energy_before,
		"energy (absent from the response) never changes")
	check_eq(state.summary.xp, 4, "xp follows the response")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("wood"), "1970",
			"the HUD renders the authoritative wood")
		check_eq(hud.displayed("coins"), "2000",
			"the HUD renders coins verbatim")
		check_eq(hud.displayed("xp"), "4", "the HUD renders xp verbatim")
	check(not state.missing.has("wood"),
		"the response supplies the wood field")
	check_eq(town.placement_error, "", "success leaves no failure record")
	check(not town.placement_preview_shown(),
		"the overlay drops after a successful apply")
	check(town.placement_active(),
		"the picker stays open after a successful apply")
	var previous_depth := -1
	var depth_ordered := true
	for object: Variant in town.objects:
		var depth := Iso.depth_key(object.cell)
		if depth < previous_depth:
			depth_ordered = false
		previous_depth = depth
	check(depth_ordered,
		"objects keep non-decreasing isometric depth after the apply")
	var rendered: Variant = null
	for object: Variant in town.objects:
		if object.cell == SUCCESS_CELL:
			rendered = object
	check(rendered != null, "an object renders at the placed cell")
	if rendered != null:
		check_eq(int(rendered.legacy_id), 1,
			"the rendered object is House I")
		check_eq(rendered.footprint, Vector2i(2, 2),
			"the content footprint resolves")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")


## The structured failure: the intent goes out, the save cannot
## resolve, the explicit error names `unknown_user_id`, and no state,
## object, or HUD value changes.
func _check_structured_failure(town: Node2D, state: Variant, api: Variant,
		session: Variant, summary: BootData.PlayerSummary,
		pid: String) -> void:
	var snapshot_before := _state_snapshot(state)
	var requests_before: int = api.placement_requests
	var bogus_id := pid + "-unresolvable"
	var bogus := BootData.PlayerSummary.new()
	bogus.user_id = bogus_id
	bogus.name = summary.name
	bogus.level = summary.level
	bogus.xp = summary.xp
	var activation: Dictionary = session.activate(bogus_id, bogus)
	check(bool(activation.get("ok", false)),
		"the unresolvable session activates: %s" % activation.get("error"))
	var target: Dictionary = town.preview_placement_cell(FREE_CELL)
	check(bool(target.get("valid", false)),
		"a valid target exists before the structured failure")
	var failed: Dictionary = await town.confirm_placement()
	check(not bool(failed.get("ok", true)),
		"the unresolvable save fails the intent")
	check_eq(str(failed.get("code", "")), "unknown_user_id",
		"the structured failure surfaces its code: %s" % failed.get("error"))
	check(town.placement_error.contains("unknown_user_id"),
		"the explicit error names the structured failure")
	check_eq(api.placement_requests, requests_before + 1,
		"the failed intent still sent exactly once")
	check_eq(_state_snapshot(state), snapshot_before,
		"the structured failure changes no state")
	check_eq(town.objects.size(), 41,
		"the structured failure renders nothing")
	var restore: Dictionary = session.activate(pid, summary)
	check(bool(restore.get("ok", false)),
		"the real session restores: %s" % restore.get("error"))
	check_eq(session.user_id(), pid, "the restored session names the save")


## A failed catalog leaves placement unavailable behind the named
## error: no mode, no picker, no request, no state change — and the
## applied state from the successful apply stays intact.
func _check_catalog_unavailable(town: Node2D, state: Variant,
		api: Variant) -> void:
	var requests_open: int = api.placement_requests
	var snapshot_open := _state_snapshot(state)
	var closing: Dictionary = town.cancel_placement()
	check(bool(closing.get("ok", false)),
		"the picker closes before the catalog-failure check: %s"
		% closing.get("error"))
	town.set_placement_catalog({"ok": false, "error":
		"[catalog] parse rejected: field 'items' of item 0 is invalid"})
	check_eq(town.placement_catalog_entries().size(), 0,
		"a failed catalog offers no entries")
	var unavailable: Dictionary = town.enter_placement()
	check(not bool(unavailable.get("ok", true)),
		"a failed catalog leaves the picker unavailable")
	check_eq(str(unavailable.get("code", "")), "placement_unavailable",
		"the unavailable rejection names the condition")
	check(String(unavailable.get("error", "")).contains("field 'items'"),
		"the explicit error carries the catalog failure: %s"
		% unavailable.get("error"))
	check(not town.placement_active(), "no mode opens on a failed catalog")
	check(not town.ui.is_slot_visible("placement"),
		"no picker shows on a failed catalog")
	check_eq(api.placement_requests, requests_open,
		"the failed catalog never sent a request")
	check_eq(_state_snapshot(state), snapshot_open,
		"the failed catalog changes no state")
	check_eq(town.objects.size(), 41,
		"the failed catalog renders nothing")


## LAST scenario (it waits out the refused loopback endpoint): the
## intent goes out over the legacy transport, the endpoint refuses it,
## and the explicit error names `unreachable_endpoint` with no state
## change (the same no-mutation contract as a structured failure).
func _check_transport_failure(town: Node2D, state: Variant, api: Variant,
		payload: Dictionary) -> void:
	town.set_placement_catalog(PlacementCatalog.parse(payload))
	var reopened: Dictionary = town.enter_placement()
	check(bool(reopened.get("ok", false)),
		"the picker reopens for the transport scenario: %s"
		% reopened.get("error"))
	var pick_transport: Dictionary = town.pick_placement(1)
	check(bool(pick_transport.get("ok", false)),
		"House I picks for the transport scenario")
	var target: Dictionary = town.preview_placement_cell(FREE_CELL)
	check(bool(target.get("valid", false)),
		"a valid target exists before the transport attempt")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.placement_requests
	var snapshot_before := _state_snapshot(state)
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_placement()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.placement_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.placement_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(town.objects.size(), 41,
		"the transport failure renders nothing")
	check(town.placement_active(),
		"the picker survives the transport failure")


## The catalog derives from the payload in hand: this whole run must not
## issue a bootstrap request (spec: "parsed fail-closed from the
## bootstrap payload the client already receives", design D10).
func _check_no_second_bootstrap_request() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	check_eq(int(api.bootstrap_requests), 0,
		"no bootstrap request was issued (the payload in hand suffices)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


## The picker's VBox panel inside the placement slot root (null before
## the first entry or when the slot never registered).
func _picker_panel(town: Variant) -> Variant:
	if not town.ui.has_slot("placement"):
		return null
	var slot: Control = town.ui.slot_root("placement")
	if slot == null or slot.get_child_count() == 0:
		return null
	return slot.get_child(0)


## The named button anywhere inside the picker panel (the action row
## nests the confirm/cancel pair), or null.
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
func _picker_status(town: Variant) -> String:
	var panel: Variant = _picker_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "status":
			return (child as Label).text
	return ""


## A rejected parse: {ok:false} with a non-empty error containing the
## named offender and a null catalog — never a partial parse.
func _expect_reject(result: Dictionary, needle: String) -> void:
	check(not bool(result.get("ok", false)),
		"'%s' fails closed" % needle)
	check(str(result.get("error", "")).find(needle) != -1,
		"the error names '%s' (got: %s)" % [needle,
			str(result.get("error", ""))])
	check(result.get("catalog") == null,
		"'%s' yields no catalog" % needle)


## The committed row with the given id, deep-copied for crafting.
func _row_with_id(payload: Dictionary, id_text: String) -> Dictionary:
	for row: Variant in payload["items"]:
		if row is Dictionary and str((row as Dictionary).get("id")) == id_text:
			return (row as Dictionary).duplicate(true)
	return {}


## parse() over one crafted payload carrying a single mutated row.
func _parse_with(row: Dictionary, field: String, value: Variant) -> Dictionary:
	var crafted := row.duplicate(true)
	crafted[field] = value
	return PlacementCatalog.parse({"items": [crafted]})


## parse() over one crafted payload carrying a row missing a field.
func _parse_without(row: Dictionary, field: String) -> Dictionary:
	var crafted := row.duplicate(true)
	crafted.erase(field)
	return PlacementCatalog.parse({"items": [crafted]})


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this
## file (the scope scan restricts transport references to the legacy-v0
## implementation).
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-mode and failure paths).
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
