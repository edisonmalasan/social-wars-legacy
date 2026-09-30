extends "res://tests/test_base.gd"
## Construction suite (building-construction, spec "Construction flow" /
## "Construction through either implementation").
##
## Scenarios:
##   gating      the selection-driven surface offers a `Build` action beside
##               the delivered `Move`, `Sell`, `Store`, and `Upgrade` actions,
##               only for a selected, ADDRESSABLE placed building whose item
##               resolves a positive committed build time, and pressing it arms
##               the build in the SAME UI-foundation slot the other four modes
##               use (design D7 — no sixth panel, no grid target, no preview),
##               and none of the four delivered modes' behavior changes;
##   steps       the single offered step FOLLOWS the row's own state — start,
##               click, finish, then nothing to do — and the three confirmed
##               steps in turn send exactly one intent each;
##   readout     the construction readout renders for every construction state
##               (none, counter only, countdown only, countdown with a counter,
##               and a completed build) and is EMPTY for a row that records
##               none;
##   refusals    an unaddressable legacy key, an item with no resolvable
##               committed build time, a row with nothing to do, a row whose
##               attribute bag is not an object, and a closed build are each
##               refused by name with NO request, the five modes never stack,
##               and a selection that no longer names the armed building
##               refuses the confirm instead of silently re-targeting it;
##   cancel      a cancelled build sends nothing and leaves the town, the
##               construction state, the readout, the storage view, and the
##               resources byte-identical;
##   apply       one confirmed intent applies ONLY the authoritative response:
##               the SAME rendered object retained in depth order (a
##               construction rewrites no item, cell, or footprint), the typed
##               row replaced by the response's post-execution row, the typed
##               construction state re-read through the shared parser, the
##               readout and the resources and XP from the response, and the
##               storage view untouched — with BOTH counts unchanged, because
##               the key is reused;
##   failures    an index the service does not know (`unknown_item_index` —
##               the endpoint's 404, resolved before execution) and a transport
##               failure (the refused loopback endpoint) each surface their code
##               with the row keeping its previous construction state and the
##               HUD unchanged;
##   helpers     the pure helpers (step machine, click progress, remaining
##               countdown, refusals, readout) over every construction state,
##               with an explicit `now` and no node, request, or clock;
##   no-request  the whole run issues no bootstrap request (the state derives
##               from the fixture in hand and the flow never re-bootstraps).
##
## Uses the committed bootstrap and construction fixtures directly; no fixture
## is ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-construction` run is the
## `construction-live` phase: one row walked through its three actions against
## the real Compatibility endpoint.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")
const ConstructionFlow = preload("res://scripts/town/construction_flow.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## recorded against the committed construction capture): the Turret I, item 22,
## 1x1, at legacy map key "11" — its cell `(58,48)`, the row
## `[22, 58, 48, 0, 0, [], {}, 1]` — is mutated IN PLACE by the two captured
## commands (a start whose duration is the item's committed `build_time` 5,
## then a build click) into a row carrying the recorded countdown and a click
## counter of 1, which is the item's `clicks_to_build`. The placement count
## stays 40, the key and cell are reused, the storage stays empty, and no
## resource changes (the derived vector is neutral, so no building cost is
## claimed).
const BUILT_ITEM := 22
const BUILT_SLOT := 11
const BUILT_CELL := Vector2i(58, 48)
const BUILT_ROW := [BUILT_ITEM, 58, 48, 0, 0, [], {}, 1]
const BUILT_BUILD_TIME := 5
const BUILT_CLICKS := 1
const PLACEMENTS := 40
## A second, still-present addressable building used for the mutual-exclusion
## and transport scenarios: the Turret I at legacy key 20, cell (41,48).
const SPARE_CELL := Vector2i(41, 48)
const SPARE_SLOT := 20
const SPARE_ITEM := 22
## An index neither the corpus nor the double knows (a stale client state after
## the row was renumbered, or a row the save never carried).
const UNKNOWN_INDEX := 9999
## The cell the crafted-row scenarios park their rows at.
const GHOST_CELL := Vector2i(20, 20)
## An item the committed content package records `build_time` 0 for (a Worker
## I), used for the "no resolvable committed build time" refusal. No placed row
## of the corpus names one, so the suite crafts that row in memory.
const NO_BUILD_TIME_ITEM := 1001
## A fixed evaluation instant for the pure helpers' remaining-countdown
## derivation (the module takes `now` as a parameter and reads no clock).
const NOW := 1790690600

## Endpoint for the transport scenario: the `--gameapi-endpoint=` user
## argument (verify-boot passes a refused loopback port to every hermetic
## suite), else the project setting's loopback default. No hardcoded endpoint
## in this file — the project-scope scan restricts transport references to the
## legacy-v0 implementation.
const ARG_ENDPOINT := "--gameapi-endpoint="


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	if scenario == "live-construction":
		# verify-boot's construction-live phase: one row walked through its
		# three typed actions through the real Compatibility endpoint; the
		# phase harness asserts the disposable corpus save mutated, this
		# scenario asserts each typed response AND the per-action
		# post-condition this line's endpoint proves. Everything else here is
		# fixture-fake only.
		await _check_live_construction()
		return
	_check_pure_helpers()
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
# Pure helpers (task 4.2, design D7)
# ---------------------------------------------------------------------------


## The pure helpers over every construction state the flow can meet, with an
## explicit `now`. Nothing here touches a node, a request, or a clock: the same
## inputs always produce the same step, progress, remaining seconds, refusal,
## and readout.
func _check_pure_helpers() -> void:
	var empty := {"clicks": null, "countdown": null, "started_at": null}
	var counter := {"clicks": 0, "countdown": null, "started_at": null}
	var raised := {"clicks": 1, "countdown": null, "started_at": null}
	var started := {"clicks": null, "countdown": 5, "started_at": NOW}
	var both := {"clicks": 1, "countdown": 5, "started_at": NOW}
	var unstamped := {"clicks": null, "countdown": 5, "started_at": null}

	# The state machine (design D5), in its documented order.
	check(not ConstructionFlow.has_state(empty),
		"a row with an empty bag records no construction state")
	check(ConstructionFlow.has_state(counter),
		"a counter-only row records construction state")
	check(ConstructionFlow.has_state(started),
		"a countdown-only row records construction state")
	check_eq(ConstructionFlow.next_step(empty, BUILT_CLICKS),
		ConstructionFlow.STEP_START,
		"no construction state offers a start")
	check_eq(ConstructionFlow.next_step(counter, BUILT_CLICKS),
		ConstructionFlow.STEP_CLICK,
		"a counter below the requirement offers a click")
	check_eq(ConstructionFlow.next_step(raised, BUILT_CLICKS),
		ConstructionFlow.STEP_FINISH,
		"a counter that reached the requirement offers a completion")
	check_eq(ConstructionFlow.next_step(both, BUILT_CLICKS),
		ConstructionFlow.STEP_FINISH,
		"a countdown beside a reached counter still offers the completion")
	check_eq(ConstructionFlow.next_step(started, BUILT_CLICKS),
		ConstructionFlow.STEP_CLICK,
		"a running countdown with no counter still owes a click")
	check_eq(ConstructionFlow.next_step(started, BUILT_CLICKS, true),
		ConstructionFlow.STEP_COMPLETE,
		"a build this client completed offers nothing to do")
	check_eq(ConstructionFlow.next_step(empty, BUILT_CLICKS, true),
		ConstructionFlow.STEP_START,
		"a row that records nothing offers a start even after an earlier "
		+ "completion: it is not building at all")
	check_eq(ConstructionFlow.next_step(counter, 0),
		ConstructionFlow.STEP_FINISH,
		"an item that needs no clicks owes no click")
	check_eq(ConstructionFlow.next_step(empty, 0), ConstructionFlow.STEP_START,
		"an item that needs no clicks still starts a build")
	check_eq(ConstructionFlow.STEP_START, "start",
		"the start step is the endpoint's own action name")
	check_eq(ConstructionFlow.STEP_CLICK, "click",
		"the click step is the endpoint's own action name")
	check_eq(ConstructionFlow.STEP_FINISH, "finish",
		"the finish step is the endpoint's own action name")

	# The click progress against the committed requirement.
	var none := ConstructionFlow.click_progress(empty, BUILT_CLICKS)
	check_eq([int(none["clicks"]), int(none["required"]),
		int(none["remaining"]), bool(none["reached"])], [0, 1, 1, false],
		"an absent counter reads as zero clicks against a one-click requirement")
	var half := ConstructionFlow.click_progress(raised, 3)
	check_eq([int(half["clicks"]), int(half["remaining"]),
		bool(half["reached"])], [1, 2, false],
		"a counter below a larger requirement keeps the remaining clicks")
	var over := ConstructionFlow.click_progress({"clicks": 4}, 2)
	check_eq(int(over["remaining"]), 0,
		"a counter past the requirement never reports negative remaining clicks")

	# The remaining countdown: `cp - (now - started_at)`, clamped at zero, and
	# unavailable — null, never guessed — when the row records no countdown or
	# no usable start instant.
	check_eq(ConstructionFlow.remaining_seconds(started, NOW), 5,
		"at the recorded start the remaining time equals the countdown")
	check_eq(ConstructionFlow.remaining_seconds(started, NOW + 3), 2,
		"the remaining time is the countdown minus the elapsed seconds")
	check_eq(ConstructionFlow.remaining_seconds(started, NOW + 99), 0,
		"an elapsed countdown clamps at zero, never negative")
	check_eq(ConstructionFlow.remaining_seconds(started, NOW - 10), 15,
		"a start instant in the future never shortens the countdown")
	check_eq(ConstructionFlow.remaining_seconds(counter, NOW), null,
		"a row with no countdown has no remaining time")
	check_eq(ConstructionFlow.remaining_seconds(unstamped, NOW), null,
		"a countdown with no usable start instant has no remaining time")

	# The readout: names the building, the click progress, and the countdown,
	# and is EMPTY for a row that records no construction state.
	check_eq(ConstructionFlow.readout_text({"ok": true, "has_state": false,
		"item": BUILT_ITEM, "clicks": 0, "required": 1}), "",
		"a row with no construction state has nothing to read out")
	var no_countdown := ConstructionFlow.readout_text({
		"ok": true, "has_state": true, "item": BUILT_ITEM, "clicks": 1,
		"required": 1, "countdown": null, "remaining_seconds": null,
		"step": ConstructionFlow.STEP_FINISH})
	check(no_countdown.contains("clicks 1/1"),
		"the counter-only readout names the click progress: %s" % no_countdown)
	check(no_countdown.contains("no countdown recorded"),
		"the counter-only readout says no countdown is recorded: %s"
			% no_countdown)
	var running := ConstructionFlow.readout_text({
		"ok": true, "has_state": true, "item": BUILT_ITEM, "clicks": 1,
		"required": 1, "countdown": 5, "remaining_seconds": 2,
		"step": ConstructionFlow.STEP_FINISH})
	check(running.contains("clicks 1/1") and running.contains("2 s remaining"),
		"the running readout names the click progress and the remaining "
		+ "countdown: %s" % running)
	var complete := ConstructionFlow.readout_text({
		"ok": true, "has_state": true, "item": BUILT_ITEM, "clicks": 0,
		"required": 1, "countdown": 5, "remaining_seconds": 0,
		"step": ConstructionFlow.STEP_COMPLETE})
	check(complete.contains("complete"),
		"a completed build's readout says so: %s" % complete)

	# The step labels the confirm button shows: the exact action, never a
	# generic "Confirm".
	check_eq(ConstructionFlow.step_label(ConstructionFlow.STEP_START),
		"Start build", "the start step is labelled")
	check_eq(ConstructionFlow.step_label(ConstructionFlow.STEP_CLICK),
		"Add build click", "the click step is labelled")
	check_eq(ConstructionFlow.step_label(ConstructionFlow.STEP_FINISH),
		"Finish build", "the completion step is labelled")
	check_eq(ConstructionFlow.step_label(ConstructionFlow.STEP_COMPLETE), "",
		"a completed build offers no step label")

	# The refusals name their own condition, and an evaluation that offers a
	# step never produces refusal text.
	var refused: Dictionary = ConstructionFlow.evaluate(null, null, 0, 0, false,
		NOW)
	check(not bool(refused.get("ok", true)),
		"no selected placement is refused structurally")
	check_eq(str(refused.get("reason", "")),
		ConstructionFlow.REASON_NO_SELECTION,
		"the structural refusal names the no-selection condition")
	check_eq(ConstructionFlow.refusal_text(refused), "",
		"a structural refusal produces no player-facing text (it is an error)")
	check(ConstructionFlow.refusal_text({"ok": true, "reason": "",
		"step": ConstructionFlow.STEP_START}) == "",
		"an offered step produces no refusal text")
	for reason in [ConstructionFlow.REASON_UNADDRESSABLE,
			ConstructionFlow.REASON_NO_BUILD_TIME,
			ConstructionFlow.REASON_NO_REQUIREMENT,
			ConstructionFlow.REASON_NO_STEP]:
		var text := ConstructionFlow.refusal_text({"ok": true, "reason": reason,
			"item": BUILT_ITEM, "clicks": 0, "required": 1})
		check(text != "" and text.contains(str(BUILT_ITEM)),
			"the '%s' refusal names the building: %s" % [reason, text])
	check_eq(BootData.CONSTRUCTION_ACTIONS,
		["start", "click", "finish"],
		"the closed action vocabulary is the endpoint's own")


# ---------------------------------------------------------------------------
# Construction flow (spec "Construction flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> confirm -> apply through all three steps plus every refusal, failure,
## and no-request path.
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
	var building: Variant = _placement_by_slot(state, BUILT_SLOT)
	check(building != null, "the recorded building is addressable by key 11")
	if building != null:
		check_eq(int(building.item), BUILT_ITEM,
			"key 11 names the Turret I (item 22)")
		check_eq(building.cell, BUILT_CELL,
			"the fresh save anchors it at (58,48)")
		check_eq(_typed_row(building.raw), BUILT_ROW,
			"the row is the pre-execution row the fixture mutated")
		check_eq(building.clicks, null,
			"the fresh corpus records no click counter")
		check_eq(building.countdown, null,
			"the fresh corpus records no countdown")
		check_eq(building.started_at, null,
			"the fresh corpus records no start instant")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the construction save")
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
		"the fresh save renders 40 objects before any construction")
	# The shop surface is opened only so the storage readout exists: a
	# construction must leave the storage view and the readout untouched, and
	# that on-screen text is the evidence.
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
	# A fresh corpus has no construction in progress, so the readout is EMPTY
	# on launch and only renders for a row that records state.
	var press_once: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(BUILT_CELL))
	check(bool(press_once.get("ok", false)), "the recorded building selects")
	check_eq(town.construction_readout(), "",
		"a row with no construction state renders no readout")
	# The selection is cleared again so the gating check starts from the
	# delivered unarmed state.
	town.handle_pointer_press(Vector2(-800, -800))
	check_eq(town.selection(), null, "a press off the ground clears the selection")

	var requests_start: int = api.construction_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	await _check_walked_construction(town, state, api)
	_check_completed_refusal(town, api, requests_start + 3)
	_check_cancelled_construction(town, state, api, requests_start + 3,
		_state_snapshot(state))
	_check_mutual_exclusion(town, api, requests_start + 3)
	await _check_unknown_index(registry, api)
	await _check_transport_failure(town, state, api)
	check_eq(api.construction_requests, requests_start + 5,
		"the whole flow issued exactly five requests (three walked steps, one "
		+ "structured failure, one transport failure); every other check sent "
		+ "none")
	town.free()

	# The refusals run on their own towns so the applied state of the main
	# flow stays intact for the counts above.
	await _check_unaddressable_refusal(registry, api)
	await _check_no_build_time_refusal(registry, api)
	await _check_unreadable_row_refusal(registry, api)


## The selection-driven surface offers `Build` beside `Move`, `Sell`, `Store`,
## and `Upgrade` for a selected, addressable placed building whose item
## resolves a committed build time, and pressing it arms the build in the SAME
## slot the other four modes use (design D7: no sixth panel, no grid target,
## and none of the four delivered modes is altered).
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.construction_active(),
		"the build is not armed before a selection")
	check(not town.construction_selection_available(),
		"no selection means no build action")
	check_eq(town.construction_slot(), TownState.NO_SLOT,
		"an unarmed build names no index")
	check_eq(town.construction_step(), ConstructionFlow.STEP_COMPLETE,
		"an unarmed build offers no step")
	check_eq(town.construction_evaluation(), {},
		"an unarmed build has no evaluation")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(BUILT_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), BUILT_ITEM,
		"the press at (58,48) selects the Turret I")
	check(town.construction_selection_available(),
		"an addressable selection with a committed build time offers the build "
		+ "action")
	check(town.move_selection_available(),
		"the same selection still offers the delivered move action")
	check(town.sell_selection_available(),
		"the same selection still offers the delivered sell action")
	check(town.store_selection_available(),
		"the same selection still offers the delivered store action")
	check(town.upgrade_selection_available(),
		"the same selection still offers the delivered upgrade action")
	check(town.ui.has_slot("move"),
		"the selection-driven surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("move"),
		"the surface slot shows for a committed selection")
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	check(town.shop_active(),
		"the open shop survives the selection (it is the readout's surface)")
	check(not town.move_active(), "a selection alone never arms the move mode")
	check(not town.sell_active(), "a selection alone never arms the sell mode")
	check(not town.store_active(),
		"a selection alone never arms the store mode")
	check(not town.upgrade_active(),
		"a selection alone never arms the upgrade mode")

	var panel: Variant = _surface_panel(town)
	check(panel != null, "the selection-driven panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var build_button: Variant = _button_named(panel_node, "build")
	check(build_button is Button, "the build action button exists")
	if build_button is Button:
		check(not (build_button as Button).disabled,
			"the build action is enabled for an addressable selection")
		check_eq((build_button as Button).text, "Build",
			"the action is labelled Build")
	for delivered in ["move", "sell", "store", "upgrade"]:
		var button: Variant = _button_named(panel_node, delivered)
		check(button is Button and not (button as Button).disabled,
			"the delivered %s action is still enabled beside it" % delivered)
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before a build is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_surface_status(town)).contains("press Move"),
		"the unarmed status line is the delivered one, unchanged")
	check_eq(_readout_label(town), "",
		"the readout line exists and is empty while no row is building")

	# The button wiring arms the build (the signal path, one `pressed`
	# emission = one arm — no request).
	if build_button != null:
		(build_button as Button).pressed.emit()
	check(town.construction_active(), "pressing the action arms the build")
	check_eq(town.construction_slot(), BUILT_SLOT,
		"the armed build names the building's legacy key 11")
	check_eq(int(town.construction_requirement().get("build_time", 0)),
		BUILT_BUILD_TIME,
		"the armed build derives the item's committed build time")
	check_eq(int(town.construction_requirement().get("clicks", -1)),
		BUILT_CLICKS,
		"the armed build derives the item's committed click requirement")
	check_eq(town.construction_requirement().get("name", ""),
		"Turret I",
		"the armed build's committed facts name the building")
	check_eq(town.construction_step(), ConstructionFlow.STEP_START,
		"a row with no construction state offers a start")
	check_eq(int((town.construction_evaluation() as Dictionary)["item"]),
		BUILT_ITEM, "the armed evaluation names the building")
	var status := String(_surface_status(town))
	check(status.contains("armed") and status.contains("build"),
		"the status names the armed build: %s" % status)
	check(status.contains("none claimed"),
		"the status names the no-building-cost claim limit")
	check(status.contains("no cancel"),
		"the status names that no cancel clears construction state")
	var selection_text := String(_surface_selection_text(town))
	check(selection_text.contains("Start build"),
		"the selection line names the one step the confirm will send: %s"
			% selection_text)
	check(selection_text.contains("none claimed"),
		"the selection line states the no-cost derivation boundary")
	# A build has NO grid target, so no footprint preview is displayed.
	check(not town.move_preview_shown(),
		"an armed build shows no footprint preview (it has no target)")
	check(town.move_evaluation().is_empty(),
		"an armed build commits no move evaluation")
	check_eq(api.construction_requests, requests_before,
		"arming sent no request")
	# The delivered modes are unavailable while a build is armed: the five
	# modes share one surface and never stack. Arming REBUILDS the panel, so it
	# is re-read here.
	var armed_panel: Variant = _surface_panel(town)
	for other in ["move", "sell", "store", "upgrade", "build"]:
		var other_button: Variant = _button_named(armed_panel as Node, other)
		if other_button is Button:
			check((other_button as Button).disabled,
				"the %s action is unavailable while a build is armed" % other)
	var armed_confirm: Variant = _button_named(armed_panel as Node, "confirm")
	if armed_confirm is Button:
		check((armed_confirm as Button).visible,
			"the targetless confirm is offered as soon as the build is armed")
		check_eq((armed_confirm as Button).text, "Start build",
			"the shared confirm names the armed mode's own step")
	# Mutual exclusion, in both directions (spec "mutually exclusive with the
	# delivered move, sell, store, and upgrade modes"): the armed build refuses
	# the other four by name, and the refusal names the ARMED mode (the build),
	# never the one the player tried to arm.
	for entry in ["arm_move", "arm_sell", "arm_store", "arm_upgrade"]:
		var refused: Dictionary = await town.call(str(entry))
		check(not bool(refused.get("ok", true)),
			"%s while a build is armed rejects" % str(entry))
		check_eq(str(refused.get("code", "")),
			"construction_already_active",
			"the stacked-arm refusal of %s names the armed build" % str(entry))
	var again: Dictionary = town.arm_construction()
	check(not bool(again.get("ok", true)),
		"arming an already-armed build rejects")
	check_eq(str(again.get("code", "")), "construction_already_active",
		"the double-arm names the condition")
	check_eq(api.construction_requests, requests_before,
		"every refusal on this surface sent no request")
	check(town.construction_active(),
		"the refusals never disarm the build in progress")
	# Cancelling here keeps the applied-state checks that follow on a clean
	# surface; the cancel contract itself is asserted in its own check.
	var released: Dictionary = town.cancel_construction()
	check(bool(released.get("ok", false)),
		"the build closes for the cancel scenario: %s" % released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition.
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# The confirm on a closed build refuses by name and sends nothing.
	var closed: Dictionary = await town.confirm_construction()
	check(not bool(closed.get("ok", true)),
		"a closed build refuses a confirm")
	check_eq(str(closed.get("code", "")), "construction_not_active",
		"the closed-build refusal names the condition")
	check_eq(api.construction_requests, requests_before,
		"the closed-build refusal sent no request")

	# Re-select the recorded building and arm once more for the
	# selection-changed refusal.
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	var armed: Dictionary = town.arm_construction()
	check(bool(armed.get("ok", false)),
		"the build re-arms: %s" % armed.get("error"))
	check_eq(api.construction_requests, requests_before,
		"re-arming sent no request")
	var elsewhere: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(elsewhere.get("ok", false)),
		"a press elsewhere still selects: %s" % elsewhere.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the press at (41,48) selects the other Turret I")
	var re_targeted: Dictionary = await town.confirm_construction()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose selection moved refuses")
	check_eq(str(re_targeted.get("code", "")),
		"construction_selection_changed",
		"the re-target refusal names the condition: %s"
		% re_targeted.get("error"))
	check_eq(api.construction_requests, requests_before,
		"the re-target refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	# The armed build survives every refusal (a refusal never disarms it), so
	# it is closed here and the cancel contract is asserted on its own.
	var closed_armed: Dictionary = town.cancel_construction()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed build closes cleanly: %s"
		% closed_armed.get("error"))


## The "nothing to do" refusal (spec "Only the promised step is offered"): once
## this client has completed the build, the row records a countdown with the
## counter consumed and the surface arms again but offers NO step, so any
## confirm is refused by name with no request. This is the one place the flow
## consults client state rather than the row alone, and the reason is recorded
## on `_construction_completed`: a completed build and a freshly started one
## are the SAME row, because the completing command deletes the counter and the
## purchase half only ever seeded it (design D5/D7).
func _check_completed_refusal(town: Node2D, api: Variant,
		requests_before: int) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	check(town.selection_legacy_id() == BUILT_ITEM,
		"the completed building is the committed selection again")
	var armed: Dictionary = town.arm_construction()
	check(bool(armed.get("ok", false)),
		"a completed build still arms (it is addressable and resolvable): %s"
		% armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(town.construction_step(), ConstructionFlow.STEP_COMPLETE,
			"a completed build offers nothing to do")
		var readout: String = town.construction_readout()
		check(readout.contains("complete"),
			"the readout names the completed build: %s" % readout)
		var nothing: Dictionary = await town.confirm_construction()
		check(not bool(nothing.get("ok", true)),
			"a completed build refuses a confirm")
		check_eq(str(nothing.get("code", "")), ConstructionFlow.REASON_NO_STEP,
			"the nothing-to-do refusal names the condition: %s"
			% nothing.get("error"))
		check(String(nothing.get("error", "")).contains("nothing to do"),
			"the explicit error says there is nothing to do")
		check_eq(api.construction_requests, requests_before,
			"the nothing-to-do refusal sent no request")
		var closed: Dictionary = town.cancel_construction()
		check(bool(closed.get("ok", false)),
			"the completed build closes cleanly")
	# The RECORDED LIMIT of the client-side completion record (design D5/D7):
	# once this client has completed a build on a row, that row offers nothing
	# further in this session, so no second start is offered and none is sent.
	# The row and the legacy server never distinguished the two states, and the
	# spec's "nothing to do" is exactly this. The ledger is dropped by a
	# rebuild, which the transport-failure and applied checks already exercise
	# on fresh towns.
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	var re_arm: Dictionary = town.arm_construction()
	check(bool(re_arm.get("ok", false)),
		"the completed row arms again (it is addressable and resolvable): %s"
		% re_arm.get("error"))
	if bool(re_arm.get("ok", false)):
		check_eq(town.construction_step(), ConstructionFlow.STEP_COMPLETE,
			"a completed build offers no second start, the recorded limit")
		town.cancel_construction()


## A cancelled build drops only mode-local state: the serialized town state,
## the row's construction state, the storage view, the readout, the selection,
## the resources, and the request count stay byte-identical.
func _check_cancelled_construction(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	var armed: Dictionary = town.arm_construction()
	check(bool(armed.get("ok", false)),
		"the build arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var readout_before: String = town.construction_readout()
	var cancelled: Dictionary = town.cancel_construction()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the build: %s" % cancelled.get("error"))
	check(not town.construction_active(), "the build closes")
	check(town.construction_placement() == null, "the built placement drops")
	check_eq(town.construction_slot(), TownState.NO_SLOT,
		"a closed build names no index")
	check(not town.ui.is_slot_visible("move"),
		"the surface slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled build")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS, "cancel renders nothing")
	check_eq(town.storage_rows(), ["(empty)"],
		"cancel leaves the storage view untouched")
	check_eq(_storage_labels(town), ["(empty)"],
		"cancel leaves the on-screen readout untouched")
	check_eq(town.construction_readout(), readout_before,
		"cancel leaves the construction readout untouched")
	check(String(_surface_status(town)).contains("nothing was sent"),
		"cancel says that nothing was sent: %s" % _surface_status(town))
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.construction_requests, requests_before,
		"cancel sent no request")
	var again: Dictionary = town.cancel_construction()
	check(not bool(again.get("ok", true)),
		"closing an already-closed build rejects")
	check_eq(str(again.get("code", "")), "construction_not_active",
		"the double-close names the condition")
	check_eq(api.construction_requests, requests_before,
		"the double-close sent no request")
	# The cancel row is the ONLY cancellation this surface offers, and it
	# sends nothing — there is deliberately no action that would clear the
	# building's construction state (design D6).
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var buttons: Array = []
		_collect_buttons(panel as Node, buttons)
		var names: Array = []
		for button: Variant in buttons:
			names.append(String((button as Button).name))
		# `collect` is the SIXTH mode this shared surface carries
		# (building-collect design D8), and it is listed here so the assertion
		# still proves what it always proved: the surface offers the four
		# delivered actions, the build action, the collect action, ONE confirm,
		# and ONE cancel — and nothing that clears a building's construction
		# state.
		check_eq(names, ["move", "sell", "store", "upgrade", "build",
			"collect", "confirm", "cancel"],
			"the surface offers exactly the four delivered actions, the build "
			+ "action, the collect action, one confirm, and one cancel — no "
			+ "action that clears construction state")


## The other direction of the five-mode mutual exclusion: a build cannot be
## armed while a delivered mode already is. Runs on the spare building so the
## recorded building's selection stays untouched for the applied checks.
func _check_mutual_exclusion(town: Node2D, api: Variant,
		requests_before: int) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(SPARE_CELL))
	check(town.selection_legacy_id() == SPARE_ITEM,
		"the spare building is selectable for the exclusion checks")
	for entry in [["arm_store", "store_already_active"],
			["arm_sell", "sell_already_active"],
			["arm_move", "move_already_active"]]:
		var armed: Dictionary = town.call(str(entry[0]))
		check(bool(armed.get("ok", false)),
			"the delivered %s arms on the spare building: %s"
				% [str(entry[0]), armed.get("error")])
		var over: Dictionary = town.arm_construction()
		check(not bool(over.get("ok", true)),
			"arming a build while a %s is armed rejects" % str(entry[0]))
		check_eq(str(over.get("code", "")), str(entry[1]),
			"the refusal names the armed %s: %s"
				% [str(entry[0]), over.get("error")])
		town.call("cancel_" + str(entry[0]).trim_prefix("arm_"))
	check_eq(api.construction_requests, requests_before,
		"every mutual-exclusion refusal sent no request")


## The walked construction: the three steps in sequence, each sending exactly
## one intent, each applying only the authoritative response, and each leaving
## the SAME rendered object in place with the SAME placement instance under the
## SAME legacy key and cell. The row is the one the refusal check already
## walked, so this check reads its post-walk state and starts a SECOND
## construction on it — which is the same flow a player would run, and proves
## the key is reused and the object is retained across constructions.
func _check_walked_construction(town: Node2D, state: Variant,
		api: Variant) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	check(town.selection_legacy_id() == BUILT_ITEM,
		"the recorded building is the committed selection again")
	var object: Variant = _object_for_cell(town, BUILT_CELL)
	check(object != null, "the Turret I object is committed before the build")
	if object == null:
		return
	var walking: Variant = _placement_by_slot(state, BUILT_SLOT)
	var armed: Dictionary = town.arm_construction()
	check(bool(armed.get("ok", false)),
		"the build arms for the walked construction: %s" % armed.get("error"))
	if not bool(armed.get("ok", false)):
		return
	check_eq(town.construction_step(), ConstructionFlow.STEP_START,
		"a row with no construction state offers a start")
	var requests_before: int = api.construction_requests
	var signature_before := _object_signature(town)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var storage_labels_before: Array = _storage_labels(town)
	var confirmed: Dictionary = await town.confirm_construction()
	check(bool(confirmed.get("ok", false)),
		"the confirmed start succeeds: %s" % confirmed.get("error"))
	check_eq(api.construction_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	_check_typed_construction(confirmed.get("result"), ConstructionFlow.STEP_START)
	check_eq(confirmed.get("step"), ConstructionFlow.STEP_START,
		"the confirm reports the step it sent")
	# The authoritative apply: the SAME placement instance now carries the
	# response's row, the SAME rendered object is retained at the same index in
	# the committed draw order, and both counts are unchanged.
	var after: Variant = _placement_by_slot(state, BUILT_SLOT)
	check(after == walking, "the same placement instance carries the new row")
	check_eq(after.cell, BUILT_CELL, "the cell is unchanged")
	check_eq(after.slot, BUILT_SLOT, "the legacy key is unchanged")
	check_eq(int(after.item), BUILT_ITEM, "the item is unchanged")
	check_eq(after.countdown, BUILT_BUILD_TIME,
		"the typed row records the response's countdown")
	check_eq(after.clicks, null,
		"the typed row records no click counter yet")
	check(int(after.started_at) > 0,
		"the typed row carries the response's start instant")
	check_eq(after.raw[6], {"cp": BUILT_BUILD_TIME},
		"the typed row's attribute bag is the response's bag verbatim")
	check_eq(state.placements.size(), PLACEMENTS,
		"a construction changes no placement count (the key is reused)")
	check_eq(town.objects.size(), PLACEMENTS,
		"a construction changes no object count (the key is reused)")
	check(_object_for_cell(town, BUILT_CELL) == object,
		"the SAME rendered object is retained at the same cell")
	check_eq(_object_signature(town), signature_before,
		"a construction re-sorts nothing: the draw order is byte-identical")
	check_eq(town.objects.size(), town.objects_layer.get_child_count(),
		"the objects layer holds exactly the committed object list")
	check(town.construction_placement() == null,
		"the armed placement is released after the apply")
	check(not town.construction_active(), "the build closes after the apply")
	check_eq(town.construction_error, "", "success leaves no failure record")
	check_eq(state.storage, storage_before, "the storage mapping is untouched")
	check_eq(town.storage_rows(), ["(empty)"],
		"the storage view is untouched by the construction")
	check_eq(_storage_labels(town), storage_labels_before,
		"the on-screen storage readout is untouched by the construction")
	# The readout names the new state, and the HUD re-reads the response.
	var readout: String = town.construction_readout()
	check(readout.contains("build: item %d" % BUILT_ITEM),
		"the readout names the building: %s" % readout)
	check(readout.contains("clicks 0/1"),
		"the readout names the click progress: %s" % readout)
	check(readout.contains("s remaining"),
		"the readout names the remaining countdown: %s" % readout)
	check_eq(state.resources.coins, 2000, "coins follow the response")
	check_eq(state.summary.xp, 4, "xp follows the response")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("gold"), "2000",
			"the HUD renders the authoritative primary currency")
		check_eq(hud.displayed("xp"), "4", "the HUD renders xp verbatim")
	# The next step follows the row: a running countdown with no counter still
	# owes a build click, because the corpus row was placed before the purchase
	# half ever seeded its counter (design D5).
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	var re_arm: Dictionary = town.arm_construction()
	check(bool(re_arm.get("ok", false)),
		"the started row re-arms for its click: %s" % re_arm.get("error"))
	check_eq(town.construction_step(), ConstructionFlow.STEP_CLICK,
		"a running countdown with no counter offers a click")
	var clicked: Dictionary = await town.confirm_construction()
	check(bool(clicked.get("ok", false)),
		"the confirmed click succeeds: %s" % clicked.get("error"))
	_check_typed_construction(clicked.get("result"), ConstructionFlow.STEP_CLICK)
	var raised: Variant = _placement_by_slot(state, BUILT_SLOT)
	check_eq(raised.clicks, BUILT_CLICKS,
		"the typed row records the response's click counter")
	check_eq(raised.countdown, BUILT_BUILD_TIME,
		"the click left the countdown alone")
	# And the completion.
	town.handle_pointer_press(Iso.grid_to_screen(BUILT_CELL))
	var arm_finish: Dictionary = town.arm_construction()
	check(bool(arm_finish.get("ok", false)),
		"the clicked row re-arms for its completion: %s" % arm_finish.get("error"))
	check_eq(town.construction_step(), ConstructionFlow.STEP_FINISH,
		"a counter that reached the requirement offers a completion")
	var finished: Dictionary = await town.confirm_construction()
	check(bool(finished.get("ok", false)),
		"the confirmed completion succeeds: %s" % finished.get("error"))
	_check_typed_construction(finished.get("result"),
		ConstructionFlow.STEP_FINISH)
	var done: Variant = _placement_by_slot(state, BUILT_SLOT)
	check_eq(done.clicks, null,
		"the completion consumed the typed row's click counter")
	check_eq(done.countdown, BUILT_BUILD_TIME,
		"the completion left the recorded countdown alone")
	check_eq(state.placements.size(), PLACEMENTS,
		"the whole walk changed no placement count")
	check_eq(town.objects.size(), PLACEMENTS,
		"the whole walk changed no object count")
	check_eq(_object_signature(town), signature_before,
		"the whole walk re-sorted nothing")
	check(api.construction_requests > requests_before + 2,
		"each of the three steps sent exactly one intent")


## The typed result of one confirmed step: protocol, version, legacy result,
## resolved action, both rows, and the neutral resource vector.
func _check_typed_construction(result: Variant, step: String) -> void:
	check(result is BootData.ConstructionResult,
		"the %s confirm carries the typed construction result" % step)
	if not (result is BootData.ConstructionResult):
		return
	var typed: BootData.ConstructionResult = result
	check(typed.ok, "the %s response is a success" % step)
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the %s protocol is compat-v0" % step)
	check_eq(typed.game_version, "alpha 0.02",
		"the %s response carries the game version" % step)
	check(typed.server_time > 0,
		"the %s server_time is the fixture epoch (time-dependent)" % step)
	check_eq(typed.result, "success",
		"the %s legacy result string is verbatim" % step)
	check_eq(typed.action, step,
		"the %s response echoes the action it resolved" % step)
	check(typed.previous != null, "the %s response carries the previous row"
		% step)
	check(typed.row != null, "the %s response carries the post-execution row"
		% step)
	check(typed.resources != null, "the %s response carries typed resources"
		% step)
	if typed.previous == null or typed.row == null or typed.resources == null:
		return
	check_eq(typed.previous.item_id, BUILT_ITEM,
		"the %s previous row names the building" % step)
	check_eq([typed.previous.x, typed.previous.y], [BUILT_CELL.x, BUILT_CELL.y],
		"the %s previous row carries the cell" % step)
	check_eq(typed.row.item_id, BUILT_ITEM,
		"the %s post-execution row names the same building (no tier change)"
			% step)
	check_eq([typed.row.x, typed.row.y], [BUILT_CELL.x, BUILT_CELL.y],
		"the %s post-execution row reuses the same cell" % step)
	check(typed.row.timestamp > 0,
		"the %s post-execution row is freshly stamped (time-dependent field, "
		% step + "never asserted by value)")
	check_eq(typed.row.orientation, 0,
		"the %s post-execution row keeps the row's own orientation" % step)
	check_eq(typed.row.player, 1,
		"the %s post-execution row keeps the row's own player field" % step)
	# The neutral vector means no building cost is claimed.
	check_eq(typed.resources.gold, 2000,
		"the %s gold follows the neutral vector" % step)
	check_eq(typed.resources.cash, 5,
		"the %s cash follows the neutral vector" % step)
	check_eq(typed.resources.xp, 4,
		"the %s xp follows the neutral vector" % step)
	# The per-action post-condition the endpoint itself proves, asserted here
	# on the typed row the client applied (design D3).
	match step:
		ConstructionFlow.STEP_START:
			check_eq(typed.row.attr, {"cp": BUILT_BUILD_TIME},
				"the start's post-condition: the derived countdown is recorded")
			check(typed.row.timestamp > typed.previous.timestamp,
				"the start's post-condition: the row's start instant moved on")
		ConstructionFlow.STEP_CLICK:
			check_eq(typed.row.attr, {"cp": BUILT_BUILD_TIME, "nc": BUILT_CLICKS},
				"the click's post-condition: a counter of at least one")
		ConstructionFlow.STEP_FINISH:
			check_eq(typed.row.attr, {"cp": BUILT_BUILD_TIME},
				"the completion's post-condition: the counter is consumed")


## Walks one row through its three construction steps through the real flow,
## each step sending exactly one intent. Kept as a helper so the phase's own
## order is stated once.
func _walk_to_completion(town: Node2D, cell: Vector2i, slot: int) -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	var before: int = api.construction_requests
	var walk: Array = []
	for _index in 3:
		town.handle_pointer_press(Iso.grid_to_screen(cell))
		var armed: Dictionary = town.arm_construction()
		if not bool(armed.get("ok", false)):
			check(false, "the walk could not arm at key %d: %s"
				% [slot, armed.get("error")])
			return
		walk.append(str(armed.get("step", "")))
		var confirmed: Dictionary = await town.confirm_construction()
		if not bool(confirmed.get("ok", false)):
			check(false, "the walk could not confirm at key %d: %s"
				% [slot, confirmed.get("error")])
			return
	check_eq(walk, [ConstructionFlow.STEP_START, ConstructionFlow.STEP_CLICK,
		ConstructionFlow.STEP_FINISH],
		"the walk offered start, click, then the completion, in that order")
	check_eq(api.construction_requests, before + 3,
		"the walk sent exactly three intents")
	var walking: Variant = _placement_by_slot(town.state, slot)
	if walking != null:
		check_eq(walking.clicks, null,
			"the walked row's counter is consumed at the end")
		check_eq(walking.countdown, BUILT_BUILD_TIME,
			"the walked row still records its countdown")


## The unknown-index failure: the intent names an index the service does not
## know (a stale client state — the endpoint resolves the index before
## executing and answers 404 `unknown_item_index`, so legacy's silent no-op is
## never reported as a success), the explicit error names that code, and the
## row keeps its previous construction state with the storage unchanged.
func _check_unknown_index(registry: Variant, api: Variant) -> void:
	var requests_before: int = api.construction_requests
	var ghost_town: Variant = _town_with_extra_row(registry)
	if ghost_town == null:
		return
	var snapshot_before := _state_snapshot(ghost_town.state)
	var armed: Dictionary = ghost_town.arm_construction()
	check(bool(armed.get("ok", false)),
		"the extra row arms a build: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(ghost_town.construction_slot(), UNKNOWN_INDEX,
			"the armed build names the unknown index")
		check_eq(ghost_town.construction_step(), ConstructionFlow.STEP_START,
			"the extra row offers a start")
		var failed: Dictionary = await ghost_town.confirm_construction()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s"
				% failed.get("error"))
		check(ghost_town.construction_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check_eq(ghost_town.objects.size(), PLACEMENTS + 1,
			"the structured failure removes nothing")
		check(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX) != null,
			"the unknown-index row is still in the typed state")
		check_eq(int(ghost_town.construction_placement().item), BUILT_ITEM,
			"the unknown-index row keeps its item")
		check_eq(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX).clicks,
			null, "the unknown-index row keeps its previous construction state")
		check_eq(ghost_town.storage_rows(), ["(empty)"],
			"the structured failure leaves the storage readout untouched")
		check_eq(_state_snapshot(ghost_town.state), snapshot_before,
			"the structured failure changes no state at all")
		check(ghost_town.construction_active(),
			"the build survives the structured failure")
		var closed: Dictionary = ghost_town.cancel_construction()
		check(bool(closed.get("ok", false)),
			"the failed build closes cleanly")
	ghost_town.free()
	check_eq(api.construction_requests, requests_before + 1,
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
		str(UNKNOWN_INDEX)] = [BUILT_ITEM, GHOST_CELL.x, GHOST_CELL.y,
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
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	if not bool(pressed.get("ok", false)) or town.selection_legacy_id() \
			!= BUILT_ITEM:
		town.free()
		return null
	return town


## LAST scenario (it waits out the refused loopback endpoint): the intent goes
## out over the legacy transport, the endpoint refuses it, and the explicit
## error names `unreachable_endpoint` with the row keeping its previous
## construction state, the storage unchanged, and no resource changed (the same
## no-mutation contract as a structured failure).
func _check_transport_failure(town: Node2D, state: Variant,
		api: Variant) -> void:
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(press.get("ok", false)),
		"the spare building selects for the transport scenario: %s"
		% press.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the spare building is the committed selection")
	var armed: Dictionary = town.arm_construction()
	check(bool(armed.get("ok", false)),
		"the build arms for the transport scenario: %s" % armed.get("error"))
	check_eq(town.construction_slot(), SPARE_SLOT,
		"the armed build names the spare building's legacy key")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.construction_requests
	var snapshot_before := _state_snapshot(state)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var objects_before: int = town.objects.size()
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_construction()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.construction_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.construction_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(state.storage, storage_before,
		"the transport failure touches no storage")
	check_eq(town.storage_rows(), ["(empty)"],
		"the transport failure leaves the storage readout untouched")
	check_eq(town.objects.size(), objects_before,
		"the transport failure renders nothing new")
	var spare: Variant = _placement_by_slot(state, SPARE_SLOT)
	check_eq(int(spare.item), SPARE_ITEM,
		"the spare building keeps its item after the transport failure")
	check_eq(spare.clicks, null,
		"the spare building keeps its previous construction state")
	check(town.construction_active(),
		"the build survives the transport failure")
	# The last state-changing check ran against the fake, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The unaddressable-row refusal (design D7 carried forward from the four
## delivered flows): a row whose save key is not a positive integer parses,
## renders, and is selectable, but the build action is unavailable, arming is
## refused by name with the move flow's own reason, and NOTHING is sent — the
## index is never coerced, because a coerced index would name a different row.
func _check_unaddressable_refusal(registry: Variant, api: Variant) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		BUILT_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
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
	var requests_before: int = api.construction_requests
	var snapshot_before := _state_snapshot(town.state)
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the unaddressable row is selectable: %s" % pressed.get("error"))
	check_eq(town.selection_legacy_id(), BUILT_ITEM,
		"the unaddressable row is the committed selection")
	check(not town.construction_selection_available(),
		"an unaddressable row never offers the build action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var build_button: Variant = _button_named(panel as Node, "build")
		check(build_button is Button and (build_button as Button).disabled,
			"the build action is disabled for an unaddressable row")
		check_eq((build_button as Button).text, "Build (unavailable)",
			"the action names its own unavailability")
		check(String(_surface_status(town)).contains("not movable"),
			"the status keeps the delivered unaddressable line")
	var refused: Dictionary = town.arm_construction()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the move flow's own unaddressable reason: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check(not town.construction_active(),
		"no build opens for an unaddressable row")
	check_eq(api.construction_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The no-build-time refusal (design D3/D6 carried into the client): a placed
## row whose item records no resolvable POSITIVE committed build time (a Worker
## I, `build_time` 0) is selectable and renderable, but the action is never
## offered, arming is refused by name, and NOTHING is sent. The service
## refuses the same row with `no_build_time` before the dispatcher runs, and
## the client never sends a request it knows will fail — which is also what
## keeps such a row away from legacy's whole-attribute-bag clearing branch.
func _check_no_build_time_refusal(registry: Variant, api: Variant) -> void:
	var town: Variant = _town_with_crafted_row(registry, NO_BUILD_TIME_ITEM,
		"43")
	if town == null:
		return
	var requests_before: int = api.construction_requests
	var snapshot_before := _state_snapshot(town.state)
	check(not town.construction_selection_available(),
		"a row whose item has no committed build time offers no build action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var build_button: Variant = _button_named(panel as Node, "build")
		check(build_button is Button and (build_button as Button).disabled,
			"the build action is disabled for an unbuildable row")
		check_eq((build_button as Button).text, "Build (unavailable)",
			"the action names its own unavailability")
	var refused: Dictionary = town.arm_construction()
	check(not bool(refused.get("ok", true)),
		"arming an unbuildable row fails")
	check_eq(str(refused.get("code", "")),
		ConstructionFlow.REASON_NO_BUILD_TIME,
		"the refusal names the no-build-time condition: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains(
		str(NO_BUILD_TIME_ITEM)),
		"the explicit error names the offending item")
	check(not town.construction_active(),
		"no build opens for an unbuildable row")
	check_eq(api.construction_requests, requests_before,
		"the no-build-time refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the no-build-time refusal changes no state")
	check_eq(town.construction_readout(), "",
		"an unbuildable row renders no construction readout")
	town.free()


## The unreadable-row refusal: a row whose attribute bag is not an object
## carries no construction state at all. The shared parser keeps such a row
## verbatim (the delivered selection suite's crafted rows have the same shape),
## and the build flow refuses it by name rather than reading a counter out of a
## value that is not a bag.
func _check_unreadable_row_refusal(registry: Variant, api: Variant) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["opaque"] = [
		BUILT_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, 0, 0, 1]
	var parsed: Dictionary = TownState.parse(crafted, registry)
	check(bool(parsed.get("ok", false)),
		"the opaque-row fixture still parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	check(bool(built.get("ok", false)), "the opaque-row town builds")
	if not bool(built.get("ok", false)):
		town.free()
		return
	var requests_before: int = api.construction_requests
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the opaque row is selectable: %s" % pressed.get("error"))
	check(not town.construction_selection_available(),
		"a row with no readable attribute bag offers no build action")
	var refused: Dictionary = town.arm_construction()
	check(not bool(refused.get("ok", true)),
		"arming an opaque row fails")
	check_eq(str(refused.get("code", "")),
		ConstructionFlow.REASON_UNREADABLE_STATE,
		"the refusal names the unreadable-state condition: %s"
		% refused.get("error"))
	check_eq(api.construction_requests, requests_before,
		"the unreadable-row refusal sent no request")
	town.free()


## A town carrying one crafted extra row naming `item_id` under a fresh
## addressable key, built from the SAME parsed fresh save, so no fixture is
## written. The row is selected through the delivered press path.
func _town_with_crafted_row(registry: Variant, item_id: int,
		key: String) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[key] = [
		item_id, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
	var parsed: Dictionary = TownState.parse(crafted, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "the crafted '%s' fixture parses: %s"
			% [key, parsed.get("error")])
		return null
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		check(false, "the crafted '%s' town builds" % key)
		town.free()
		return null
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	if not bool(pressed.get("ok", false)) \
			or town.selection_legacy_id() != item_id:
		check(false, "the crafted '%s' row selects" % key)
		town.free()
		return null
	return town


## The live-construction scenario (verify-boot's construction-live phase): one
## row walked through all three typed actions through the real Compatibility
## endpoint, so the unchanged legacy `command()` executes the derived command
## per action over the disposable corpus. This side asserts each typed response
## AND the per-action post-condition this line's endpoint proves — a start
## carries the derived countdown, a click carries a counter of at least one, a
## completion carries none, with the key and cell reused throughout; the phase
## harness separately asserts the corpus save file mutated. No fixture is
## touched.
func _check_live_construction() -> void:
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
	# The pre-request row, read from the corpus itself (this phase has already
	# executed the placement, purchase, move, sell, store, and upgrade
	# transactions), so the reused key and cell are compared against the state
	# the service actually held.
	var before_row: Variant = await _live_row(api, endpoint, pid, BUILT_SLOT)
	check(before_row != null, "the corpus pre-construction row resolves")
	if before_row == null:
		return
	var prior := before_row as Array
	var start: Variant = await api.build_construction(pid, BUILT_SLOT,
		ConstructionFlow.STEP_START)
	_check_live_step(start, ConstructionFlow.STEP_START, prior)
	if not (start is BootData.ConstructionResult) or not start.ok:
		return
	var click: Variant = await api.build_construction(pid, BUILT_SLOT,
		ConstructionFlow.STEP_CLICK)
	_check_live_step(click, ConstructionFlow.STEP_CLICK, prior)
	if not (click is BootData.ConstructionResult) or not click.ok:
		return
	var finish: Variant = await api.build_construction(pid, BUILT_SLOT,
		ConstructionFlow.STEP_FINISH)
	_check_live_step(finish, ConstructionFlow.STEP_FINISH, prior)
	if not (finish is BootData.ConstructionResult) or not finish.ok:
		return
	var after_row: Variant = await _live_row(api, endpoint, pid, BUILT_SLOT)
	check(after_row != null, "the corpus post-construction row resolves")
	if after_row != null:
		check_eq([int((after_row as Array)[1]), int((after_row as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not re-keyed)")
		check_eq(int((after_row as Array)[0]), BUILT_ITEM,
			"the corpus still holds the row's own item")
	# A stale index and a legacy command name each fail closed with the
	# endpoint's own code rather than reporting a construction that never
	# happened.
	var unknown: Variant = await api.build_construction(pid, UNKNOWN_INDEX,
		ConstructionFlow.STEP_START)
	check(unknown is BootData.ConstructionResult and not unknown.ok,
		"the live unknown index is a structured failure")
	if unknown is BootData.ConstructionResult:
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.previous == null and unknown.row == null
			and unknown.resources == null,
			"the live structured failure carries no partial payload")
	var bad_action: Variant = await api.build_construction(pid, BUILT_SLOT,
		"activate")
	check(bad_action is BootData.ConstructionResult and not bad_action.ok,
		"a legacy command name is never accepted by the endpoint")
	if bad_action is BootData.ConstructionResult:
		check_eq(bad_action.error_code, "invalid_action",
			"the live invalid action passes through with the endpoint's code")
	# The fake derives the same codes for the same intents, offline.
	api.configure("fake")
	var fake_unknown: Variant = await api.build_construction(pid,
		UNKNOWN_INDEX, ConstructionFlow.STEP_START)
	check(fake_unknown is BootData.ConstructionResult and not fake_unknown.ok,
		"the fake fails the same intent offline")
	if fake_unknown is BootData.ConstructionResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	api.configure("legacy_v0", endpoint)
	var typed: BootData.ConstructionResult = finish
	print("[test] live-construction applied item_index=%d cell=(%d, %d) "
		% [BUILT_SLOT, typed.row.x, typed.row.y]
		+ "countdown=%d clicks_consumed=true xp=%d gold=%d" % [
			int((typed.row.attr as Dictionary).get("cp", 0)),
			typed.resources.xp, typed.resources.gold])


## One live step's typed response and its own post-condition, compared against
## the corpus's own pre-request row (the reused key and cell).
func _check_live_step(result: Variant, step: String, prior: Array) -> void:
	check(result is BootData.ConstructionResult,
		"the live %s returns the typed result" % step)
	if not (result is BootData.ConstructionResult):
		return
	var typed: BootData.ConstructionResult = result
	check(typed.ok, "the live %s succeeds: %s / %s" % [step, typed.error_code,
		typed.error_message])
	if not typed.ok or typed.previous == null or typed.row == null \
			or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live %s protocol is compat-v0" % step)
	check(typed.game_version != "",
		"the live %s response carries the game version" % step)
	check(typed.server_time > 0,
		"the live %s server_time is a positive epoch (time-dependent)" % step)
	check_eq(typed.result, "success",
		"the live %s reports the legacy success result" % step)
	check_eq(typed.action, step,
		"the live %s echoes the action it resolved" % step)
	check_eq(typed.previous.item_id, int(prior[0]),
		"the live %s previous row names the corpus's own item" % step)
	check_eq([typed.previous.x, typed.previous.y],
		[int(prior[1]), int(prior[2])],
		"the live %s previous row carries the corpus's own cell" % step)
	check_eq(typed.row.item_id, int(prior[0]),
		"the live %s post-execution row names the same item" % step)
	check_eq([typed.row.x, typed.row.y], [int(prior[1]), int(prior[2])],
		"the live %s post-execution row reuses the same cell (the key is reused)"
			% step)
	check(typed.row.timestamp > 0,
		"the live %s post-execution row is stamped (time-dependent field)" % step)
	match step:
		ConstructionFlow.STEP_START:
			check_eq((typed.row.attr as Dictionary).get("cp", null),
				BUILT_BUILD_TIME,
				"the live start's post-condition: the derived countdown is "
				+ "recorded")
		ConstructionFlow.STEP_CLICK:
			var clicks: Variant = (typed.row.attr as Dictionary).get("nc", null)
			check(clicks != null and int(clicks) >= 1,
				"the live click's post-condition: a counter of at least one")
		ConstructionFlow.STEP_FINISH:
			check(not (typed.row.attr as Dictionary).has("nc"),
				"the live completion's post-condition: the counter is consumed")
	check(typed.resources.gold >= 0 and typed.resources.cash >= 0,
		"the live %s carries the corpus's own resource bag" % step)


## The corpus's own eight-field row at one legacy key, read from its bootstrap
## payload, or null when it cannot be read. Read from the service's own state,
## never from the fake's fixture, because the live side has already executed
## every earlier transaction in this phase.
func _live_row(api: Variant, endpoint: String, user_id: String,
		item_index: int) -> Variant:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus row bootstrap resolves")
		return null
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus row payload is readable")
		return null
	var raw: Dictionary = (info as BootData.PlayerInfoPayload).raw
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var row: Variant = (map.get("items", {}) as Dictionary).get(str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		check(false, "the live corpus row at key %d is an eight-field array"
			% item_index)
		return null
	return (row as Array).duplicate()


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


## Every button in a panel subtree, in creation order, so a check can assert
## the surface's own affordances and prove no extra action exists.
func _collect_buttons(panel: Node, out: Array) -> void:
	for child: Variant in panel.get_children():
		if child is Button:
			out.append(child)
		if child is Node:
			_collect_buttons(child as Node, out)


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


## The on-screen construction readout line ("" when no panel exists or the row
## records no construction state).
func _readout_label(town: Variant) -> String:
	var panel: Variant = _surface_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "construction":
			return (child as Label).text
	return ""


## The rendered storage readout lines, in the order the panel shows them.
func _storage_labels(town: Variant) -> Array:
	if not town.ui.has_slot("shop"):
		return []
	var slot: Control = town.ui.slot_root("shop")
	if slot == null or slot.get_child_count() == 0:
		return []
	var labels: Array = []
	for child: Variant in (slot.get_child(0) as Node).get_children():
		if child is VBoxContainer and String((child as VBoxContainer).name) \
				== "storage_entries":
			for row: Variant in (child as VBoxContainer).get_children():
				if row is Label:
					labels.append((row as Label).text)
	return labels


## The depth-topmost rendered object covering a cell (the same rule the press
## path applies: the last object in draw order wins), or null.
func _object_for_cell(town: Variant, cell: Vector2i) -> Variant:
	var hit: Variant = null
	for object: Variant in town.objects:
		if object != null and object.contains_cell(cell):
			hit = object
	return hit


## The committed draw order as one `item@cell` string per object, so a run can
## prove that a construction changed no object's identity and left every
## object's committed DEPTH POSITION alone.
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


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-build and failure paths), including
## the typed construction state of every row — so a cancellation or a failure
## that quietly changed a row's countdown or counter can never look
## byte-identical.
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append({
			"raw": placement.raw,
			"clicks": placement.clicks,
			"countdown": placement.countdown,
			"started_at": placement.started_at,
		})
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
