extends "res://tests/test_base.gd"
## Purchase suite (building-purchase, spec "Purchase flow" / "Storage in
## typed town state").
##
## Scenarios:
##   catalog    the same fail-closed catalog parse offers exactly the
##              store-listed, level-eligible, cash-priced entries (11 at
##              level 1 of the fresh save: 14 store-listed buildings, three
##              of them priced in wood/gold), never a non-cash or
##              level-gated entry and never a fabricated one;
##   helpers    the pure shop helpers: the price against current cash, the
##              refusal text for an unaffordable price, the reason
##              vocabulary (unaffordable / not_cash_priced / no_cash), and
##              the fail-closed envelope for a missing state or selection;
##   readout    the storage readout renders the typed storage: the
##              resolved content name, the raw id for an id the content
##              package cannot resolve, quantity `0` kept, and the explicit
##              missing-field indicator when the payload carried no storage;
##   flow       the full town flow over the committed fixtures: the shop
##              opens with the 11 gated entries and one wired button each,
##              a pick arms the confirm, the three refused confirms (no
##              selection, unaffordable, failed catalog) send nothing and
##              change nothing, a cancel leaves the serialized state
##              byte-identical, a structured failure surfaces its code
##              with no state change, and — after it, because it waits
##              out the refused loopback endpoint — a transport failure
##              does the same; last of all, while the player's 5 cash is
##              still unspent, a confirmed intent sends exactly one
##              request and applies only the authoritative response
##              (storage {"105": 1}, cash 0, the readout line, the HUD);
##   no-request the whole run issues no bootstrap request (the catalog
##              derives from the payload in hand and the flow never
##              re-bootstraps).
##
## Uses the committed bootstrap fixtures directly; no fixture is ever
## written, no server runs. Runs headless as part of `verify-boot.ps1`.
## The `--scenario=live-purchase` run is the `purchase-live` phase: one
## typed intent through the real Compatibility endpoint.

const TownState = preload("res://scripts/town/town_state.gd")
const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")
const ShopFlow = preload("res://scripts/town/shop_flow.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

const CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"
const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## probe-recorded against the committed purchase capture): item 105 "Victory
## Arch" priced `{"c": 5}` at `min_level` 1, purchased for a fresh player
## holding exactly 5 cash and an empty storage.
const PURCHASE_ITEM := 105
const PURCHASE_PRICE := 5
## Level-1 store-listed cash-priced entries of the fresh save: 11 of the 14
## store-listed buildings (Stoneage 20, Iguazu 20, Sphynx 20, Ankor 20,
## Special Fortress 15, Victory Arch 5, Fountain 10, Sculpture 7,
## Babilonian Temple 70, Cash Wonder 50, Parliament 70).
const LEVEL_ONE_OFFERING := 11
## A level-1 store-listed building priced in wood, not cash — the shop
## never offers it (design D2's derivation boundary).
const WOOD_PRICED_ITEM := 1
## A store-listed, cash-priced building whose `min_level` (21) withholds it
## at level 1.
const GATED_ITEM := 10
## The cheapest other cash-priced entry, unaffordable at the fresh 5 cash
## (Sculpture, cash 7).
const UNAFFORDABLE_ITEM := 107

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
	if scenario == "live-purchase":
		# verify-boot's purchase-live phase: one typed intent through the
		# real Compatibility endpoint; the phase harness asserts the
		# disposable corpus save mutated, this scenario asserts the typed
		# response. Everything else here is fixture-fake only.
		await _check_live_purchase()
		return
	var payload: Variant = _fixture(CONFIG_FIXTURE)
	check(payload is Dictionary, "config fixture parses as JSON")
	if not (payload is Dictionary):
		return
	_check_catalog_gating(payload)
	_check_helpers(payload)
	await _check_flow(payload)
	_check_no_second_bootstrap_request()


## The shop's entry filter over the parsed catalog: store-listed, the
## level's `min_level` allows, and priced in cash alone — in payload order,
## with the two exclusion reasons asserted against the real config.
func _check_catalog_gating(payload: Dictionary) -> void:
	var parsed: Dictionary = PlacementCatalog.parse(payload)
	check(bool(parsed.get("ok", false)),
		"the committed config parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var catalog: Variant = parsed["catalog"]
	check(catalog is PlacementCatalog.Catalog, "the catalog is typed")
	if not (catalog is PlacementCatalog.Catalog):
		return
	var offered: Array = ShopFlow.shop_entries(catalog, 1)
	check_eq(offered.size(), LEVEL_ONE_OFFERING,
		"level 1 offers exactly the 11 store-listed, cash-priced entries")
	var ids := {}
	for entry: Variant in offered:
		check(entry is PlacementCatalog.Entry, "every offered entry is typed")
		if not (entry is PlacementCatalog.Entry):
			continue
		var typed: PlacementCatalog.Entry = entry
		ids[entry.id] = true
		check(typed.in_store, "offered entries are store-listed")
		check(typed.min_level <= 1, "offered entries gate min_level <= 1")
		check(ShopFlow.is_cash_priced(typed),
			"offered entries are priced in cash alone")
	check(bool(ids.get(PURCHASE_ITEM, false)),
		"Victory Arch (item 105) is offered at level 1")
	check(not ids.has(WOOD_PRICED_ITEM),
		"House I (wood-priced) is withheld: this command buys cash only")
	check(not ids.has(GATED_ITEM),
		"Wood Factory III (min_level 21) is withheld at level 1")
	check_eq(ShopFlow.shop_entries(null, 1).size(), 0,
		"an absent catalog offers no entries (never fabricated)")
	var level_two: Array = ShopFlow.shop_entries(catalog, 2)
	check(level_two.size() >= offered.size(),
		"a higher level never withholds what a lower level had")


## The pure helpers: price text, the price against current cash, the
## refusal text, the reason vocabulary, and the fail-closed envelope. None
## of these touches a node, a request, or a clock.
func _check_helpers(payload: Dictionary) -> void:
	var catalog: Variant = PlacementCatalog.parse(payload)["catalog"]
	var arch: Variant = PlacementCatalog.find_entry(catalog, PURCHASE_ITEM)
	check(arch is PlacementCatalog.Entry,
		"the purchase item parses into a typed entry")
	if not (arch is PlacementCatalog.Entry):
		return
	check_eq(ShopFlow.price_text(arch), "cash 5",
		"the price reads as the cash amount")
	check_eq(ShopFlow.cash_price(arch), PURCHASE_PRICE,
		"the cash price is the config's c component")
	var house: Variant = PlacementCatalog.find_entry(catalog, WOOD_PRICED_ITEM)
	check_eq(ShopFlow.cash_price(house), null,
		"a wood-priced item has no cash price (never guessed)")
	check_eq(ShopFlow.price_text(house), "unpriced",
		"an unpriceable entry names itself instead of showing a price")
	check(not ShopFlow.is_cash_priced(house),
		"a wood-priced item is not cash-priced")
	check(not ShopFlow.is_cash_priced(null),
		"an absent entry is never cash-priced")

	# A minimal state bag: only the cash field the helper reads.
	var state := {"resources": {"cash": PURCHASE_PRICE}}
	check_eq(ShopFlow.price_against_cash_text(state, arch), "cash 5 (have 5)",
		"the price reads against the current cash")
	var afford: Dictionary = ShopFlow.evaluate(state, arch)
	check(bool(afford.get("purchasable", false)),
		"a price equal to the cash is affordable")
	check_eq(str(afford.get("reason", "")), "",
		"an affordable entry names no reason")
	check_eq(ShopFlow.refusal_text(afford), "",
		"an affordable entry has no refusal text")
	var poor := {"resources": {"cash": PURCHASE_PRICE - 1}}
	var refused: Dictionary = ShopFlow.evaluate(poor, arch)
	check(not bool(refused.get("purchasable", true)),
		"a price above the current cash is not purchasable")
	check_eq(str(refused.get("reason", "")), "unaffordable",
		"the refusal names the affordability gate")
	check_eq(int(refused.get("cash", 0)), PURCHASE_PRICE - 1,
		"the evaluation reports the current cash it compared against")
	check(ShopFlow.refusal_text(refused).contains("not purchasable"),
		"the refusal text is explicit")
	check(ShopFlow.refusal_text(refused).contains("5 costs more than the 4"),
		"the refusal text names both numbers it compares")
	check(not ShopFlow.affordable(poor, arch),
		"the affordability helper agrees with the evaluation")

	# An unknown cash value is never treated as affordable: the helper
	# names the field instead of defaulting it to zero.
	var unknown := {"resources": {}}
	var unknown_result: Dictionary = ShopFlow.evaluate(unknown, arch)
	check(not bool(unknown_result.get("purchasable", true)),
		"a missing cash value is never affordable")
	check_eq(str(unknown_result.get("reason", "")), "no_cash",
		"the missing cash field names itself")
	check(ShopFlow.price_against_cash_text(unknown, arch).contains("have ?"),
		"the price display marks the unknown cash instead of guessing")

	# A non-cash price is named by the reason vocabulary, never coerced.
	var not_cash: Dictionary = ShopFlow.evaluate(state, house)
	check_eq(str(not_cash.get("reason", "")), "not_cash_priced",
		"a non-cash price names the derivation boundary")
	check(ShopFlow.refusal_text(not_cash).contains("House I"),
		"the refusal text names the entry")

	# Structural failures: the house envelope, never an evaluation.
	var no_state: Dictionary = ShopFlow.evaluate(null, arch)
	check(not bool(no_state.get("ok", true)),
		"a missing state fails closed")
	check(str(no_state.get("error", "")).contains("town state"),
		"the rejection names the missing state")
	var no_entry: Dictionary = ShopFlow.evaluate(state, null)
	check(not bool(no_entry.get("ok", true)),
		"a missing selection fails closed")
	check(str(no_entry.get("error", "")).contains("no shop entry"),
		"the rejection names the missing selection")


# ---------------------------------------------------------------------------
# Purchase flow (spec "Purchase flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, hands
## the typed catalog to the shop (the boot handoff's job), and drives
## enter -> pick -> confirm -> apply plus every refusal, failure, and
## no-request path.
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
	check_eq(state.storage, {},
		"the fresh save starts with an empty (but present) storage")
	check(not state.missing.has("storage"),
		"the fresh save's storage field is present, not missing")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the purchase save")
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
	town.set_shop_catalog(PlacementCatalog.parse(payload))
	check_eq(town.shop_catalog_entries().size(), LEVEL_ONE_OFFERING,
		"the handed catalog offers the level-1 entries")

	var requests_start: int = api.purchase_requests
	var snapshot_start := _state_snapshot(state)
	_check_shop_entry(town, state, api, requests_start)
	_check_refused_confirms(town, state, api, requests_start, snapshot_start)
	_check_cancelled_shop(town, state, api, requests_start, snapshot_start)
	_check_readout_edge_cases(town, state)
	# The successful purchase is deliberately LAST among the state-changing
	# checks: it spends the fresh player's only 5 cash, after which the
	# client refuses every entry locally (design D5), so the structured and
	# transport failures both run while an entry is still sendable.
	await _check_structured_failure(town, state, api, session, summary, pid)
	_check_catalog_unavailable(town, state, api)
	await _check_transport_failure(town, state, api, payload)
	await _check_applied_response(town, state, api)
	check_eq(api.purchase_requests, requests_start + 3,
		"the whole flow issued exactly three requests (structured "
		+ "failure, transport failure, success); every other check "
		+ "sent none")
	town.free()


## The storage readout renders the typed storage verbatim: one line per
## entry, the resolved content name when the registry knows the id, the raw
## id (never a guessed name) when it does not, quantity `0` kept, and the
## explicit missing-field indicator when the payload carried no storage.
func _check_readout_edge_cases(town: Node2D, state: Variant) -> void:
	var lines: Array = town.storage_rows()
	check_eq(lines.size(), 1, "an empty storage renders one indicator line")
	check_eq(str(lines[0]), "(empty)",
		"an empty storage is shown as empty, not as missing")
	state.storage = {"302": 1, "999999": 0}
	check_eq(town.storage_rows(),
		["Atom Fusion  x1  (item 302)",
		"item 999999  x0  (name unresolved)"],
		"unresolved ids render the raw id, quantity 0 is kept, and the "
		+ "order is by numeric id")
	state.storage = {}
	state.missing.append(TownState.STORAGE_MISSING_KEY)
	check_eq(town.storage_rows(), ["[missing: storage]"],
		"an absent storage field is named, never shown as empty")
	state.missing.erase(TownState.STORAGE_MISSING_KEY)
	check_eq(town.storage_rows(), ["(empty)"],
		"restoring the field restores the empty-storage indicator")


## Shop entry: the surface opens with the gated offering, one wired button
## per entry, the readout already rendered, and the price against the live
## cash on the picked entry.
func _check_shop_entry(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	var entered: Dictionary = town.enter_shop()
	check(bool(entered.get("ok", false)),
		"the shop opens: %s" % entered.get("error"))
	if not bool(entered.get("ok", false)):
		return
	check(town.shop_active(), "the shop is active")
	check_eq(int(entered.get("entries", -1)), LEVEL_ONE_OFFERING,
		"the shop reports the 11 level-1 cash-priced entries")
	check_eq(town.shop_catalog_entries().size(), LEVEL_ONE_OFFERING,
		"the catalog accessor offers the same gated entries")
	check(town.ui.is_slot_visible("shop"), "the shop slot shows while open")
	# Design D8: the shop lives beside the picker, in its own slot, and the
	# picker's state is untouched by opening it.
	check(town.ui.has_slot("shop"), "the shop owns its own UI-foundation slot")
	check(not town.placement_active(),
		"opening the shop does not arm the placement picker")
	var panel: Variant = _shop_panel(town)
	check(panel != null, "the shop panel commits into the slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var item_buttons := 0
	for child: Variant in panel_node.get_children():
		if child is Button \
				and String((child as Button).name).begins_with("item_"):
			item_buttons += 1
	check_eq(item_buttons, LEVEL_ONE_OFFERING, "one button per offered entry")
	# title + 11 entry buttons + storage title + storage box + status +
	# the action row
	check_eq(panel_node.get_child_count(), LEVEL_ONE_OFFERING + 5,
		"title, one button per entry, the storage section, the status, "
		+ "and the action row")
	check(String(_shop_status(town)).contains(
		"%d available at level 1" % LEVEL_ONE_OFFERING),
		"the status names the offering and the loaded level")
	check(_button_named(panel_node, "confirm") != null,
		"the buy action button exists")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check_eq(_storage_labels(panel_node).size(), 1,
		"the storage readout renders the empty indicator on entry")
	check_eq(String(_storage_labels(panel_node)[0]), "(empty)",
		"the readout shows the fresh save's empty storage")

	# Level and price gating through the town flow: a level-gated item, a
	# non-cash-priced item, and an absent id are each named, never offered.
	var gated: Dictionary = town.pick_shop_item(GATED_ITEM)
	check_eq(str(gated.get("code", "")), "item_not_available",
		"a level-21 item cannot be picked at level 1")
	var wood: Dictionary = town.pick_shop_item(WOOD_PRICED_ITEM)
	check_eq(str(wood.get("code", "")), "item_not_available",
		"a wood-priced item is withheld (cash-only derivation)")
	check(String(wood.get("error", "")).contains("not priced in cash"),
		"the withholding names the derivation boundary")
	var absent: Dictionary = town.pick_shop_item(999999)
	check_eq(str(absent.get("code", "")), "unknown_item_id",
		"an absent id names itself: %s" % absent.get("error"))
	check(town.shop_entry() == null,
		"failed picks never fabricate a selection")

	# The button wiring picks Victory Arch (the signal path, not a direct
	# call — one `pressed` emission = one pick).
	var arch_button: Variant = _button_named(panel_node, "item_105")
	check(arch_button != null, "the Victory Arch button exists")
	if arch_button != null:
		(arch_button as Button).pressed.emit()
		check(town.shop_entry() != null,
			"pressing the button commits a selection")
		if town.shop_entry() != null:
			check_eq(int(town.shop_entry().id), PURCHASE_ITEM,
				"the pressed button picks Victory Arch")
			check_eq(str(town.shop_entry().name), "Victory Arch",
				"the entry name is verbatim from the config")
	check(String(_shop_status(town)).contains("cash 5 (have 5)"),
		"the price reads against the current cash")
	check_eq(api.purchase_requests, requests_before,
		"picking sent no request")
	check_eq(int(state.resources.cash), PURCHASE_PRICE,
		"picking changed no resource")


## Every refused confirm: no selection, an unaffordable price, and a
## missing session. Each names its code, sends nothing, and leaves the
## serialized state byte-identical (design D5: the client owns
## affordability; the endpoint would clamp instead).
func _check_refused_confirms(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# No selection: re-enter the shop so the mode-local pick from the entry
	# check is gone (a fresh entry resets it).
	var closing: Dictionary = town.cancel_shop()
	check(bool(closing.get("ok", false)),
		"the shop closes before the refusal checks: %s"
		% closing.get("error"))
	var opening: Dictionary = town.enter_shop()
	check(bool(opening.get("ok", false)),
		"the shop reopens for the refusal checks: %s"
		% opening.get("error"))
	check(town.shop_entry() == null,
		"a fresh entry leaves no selection committed")
	var no_selection: Dictionary = await town.confirm_purchase()
	check(not bool(no_selection.get("ok", true)),
		"confirming without a selection fails")
	check_eq(str(no_selection.get("code", "")), "shop_no_selection",
		"the no-selection refusal names its condition")
	check_eq(api.purchase_requests, requests_before,
		"the no-selection confirm sent no request")

	var unaffordable: Dictionary = town.pick_shop_item(UNAFFORDABLE_ITEM)
	check(bool(unaffordable.get("ok", false)),
		"Sculpture (cash 7) picks: %s" % unaffordable.get("error"))
	check(String(_shop_status(town)).contains("not purchasable"),
		"the status names the affordability refusal on the pick")
	var refused: Dictionary = await town.confirm_purchase()
	check(not bool(refused.get("ok", true)),
		"confirming an unaffordable entry fails")
	check_eq(str(refused.get("code", "")), "not_purchasable",
		"the unaffordable confirm names not_purchasable: %s"
		% refused.get("error"))
	check(String(refused.get("error", "")).contains(
		"cash 7 costs more than the 5 you have"),
		"the explicit error carries both compared numbers")
	check_eq(api.purchase_requests, requests_before,
		"the unaffordable confirm sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the unaffordable attempt changes no state")
	check(town.shop_active(), "the shop survives the local refusal")

	# Back to the affordable entry for the rest of the flow.
	var repick: Dictionary = town.pick_shop_item(PURCHASE_ITEM)
	check(bool(repick.get("ok", false)),
		"Victory Arch picks again after the refused attempt")


## A cancelled shop entry drops only mode-local state: the serialized town
## state, resources, and request count stay byte-identical, the slot hides,
## and re-closing rejects by name.
func _check_cancelled_shop(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	var cancelled: Dictionary = town.cancel_shop()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the shop: %s" % cancelled.get("error"))
	check(not town.shop_active(), "the shop closes")
	check(town.shop_entry() == null, "the selection drops on cancel")
	check(not town.ui.is_slot_visible("shop"), "the shop slot hides on cancel")
	check_eq(_state_snapshot(state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.purchase_requests, requests_before,
		"cancel sent no request")
	var again: Dictionary = town.cancel_shop()
	check(not bool(again.get("ok", true)),
		"closing an already-closed shop rejects")
	check_eq(str(again.get("code", "")), "shop_not_active",
		"the double-close names the condition")
	var confirm_closed: Dictionary = await town.confirm_purchase()
	check(not bool(confirm_closed.get("ok", true)),
		"a closed shop refuses a confirm")
	check_eq(api.purchase_requests, requests_before,
		"the closed-shop refusal sent no request")


## The confirmed intent sends exactly one request and applies only the
## authoritative response: the response's storage mapping replaces the
## state's, the resources and XP take the response's values, the readout
## re-renders the purchased item, and the HUD re-reads from them — the
## shop itself stays open for the next purchase.
func _check_applied_response(town: Node2D, state: Variant,
		api: Variant) -> void:
	var closing: Dictionary = town.cancel_shop()
	check(bool(closing.get("ok", false)),
		"the shop closes before the confirmed intent: %s"
		% closing.get("error"))
	var reentered: Dictionary = town.enter_shop()
	check(bool(reentered.get("ok", false)),
		"the shop reopens for the confirmed intent: %s"
		% reentered.get("error"))
	var picked: Dictionary = town.pick_shop_item(PURCHASE_ITEM)
	check(bool(picked.get("ok", false)),
		"Victory Arch picks for the intent: %s" % picked.get("error"))
	var requests_before: int = api.purchase_requests
	var snapshot_before := _state_snapshot(state)
	var confirmed: Dictionary = await town.confirm_purchase()
	check(bool(confirmed.get("ok", false)),
		"the confirmed purchase succeeds: %s" % confirmed.get("error"))
	check_eq(api.purchase_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	var typed_success: Variant = confirmed.get("result")
	check(typed_success is BootData.PurchaseResult,
		"the success envelope carries the typed result")
	if typed_success is BootData.PurchaseResult:
		var typed: BootData.PurchaseResult = typed_success
		check_eq(typed.result, "success", "the legacy result string is verbatim")
		check_eq(typed.store, {"105": 1},
			"the response carries the full storage mapping")
		check(typed.resources != null, "the response carries typed resources")
		if typed.resources != null:
			check_eq(typed.resources.cash, 0,
				"the response deducts the documented 5 cash")
			check_eq(typed.resources.gold, 2000, "gold follows the response")
			check_eq(typed.resources.xp, 4, "xp follows the response")

	# The authoritative apply: storage, resources, readout, HUD.
	check_eq(state.storage, {"105": 1},
		"storage takes the response's mapping verbatim")
	check_eq(int(state.resources.cash), 0,
		"cash applies from the response (5 deducted, never clamped here)")
	check_eq(int(state.resources.coins), 2000, "coins follow the response")
	check_eq(int(state.resources.wood), 2000, "wood follows the response")
	check_eq(int(state.resources.mana), 0, "mana follows the response")
	check_eq(int(state.summary.xp), 4, "xp follows the response")
	check_eq(town.storage_rows(), ["Victory Arch  x1  (item 105)"],
		"the readout renders the purchased item with its response quantity")
	var panel: Variant = _shop_panel(town)
	check(panel != null, "the shop panel is still committed")
	if panel != null:
		var labels := _storage_labels(panel as Node)
		check_eq(labels.size(), 1, "the readout re-rendered one line")
		if labels.size() == 1:
			check_eq(String(labels[0]), "Victory Arch  x1  (item 105)",
				"the on-screen readout shows the authoritative storage")
		check(String(_shop_status(town)).contains("bought Victory Arch"),
			"the status names the completed purchase")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("cash"), "0",
			"the HUD renders the authoritative cash")
		check_eq(hud.displayed("gold"), "2000",
			"the HUD renders the primary currency verbatim")
	check(not state.missing.has(TownState.STORAGE_MISSING_KEY),
		"the response supplies the storage field")
	check_eq(town.shop_error, "", "success leaves no failure record")
	check(town.shop_active(),
		"the shop stays open after a successful apply")
	check_eq(state.placements.size(), 40,
		"a storage purchase places nothing on the map")
	check_eq(town.objects.size(), 40,
		"a storage purchase renders nothing new")
	check(_state_snapshot(state) != snapshot_before,
		"the successful apply changed the serialized state")


## The structured failure: the intent goes out, the save cannot resolve,
## the explicit error names `unknown_user_id`, and no storage, readout, or
## HUD value changes.
func _check_structured_failure(town: Node2D, state: Variant, api: Variant,
		session: Variant, summary: BootData.PlayerSummary,
		pid: String) -> void:
	var snapshot_before := _state_snapshot(state)
	var requests_before: int = api.purchase_requests
	var bogus_id := pid + "-unresolvable"
	var bogus := BootData.PlayerSummary.new()
	bogus.user_id = bogus_id
	bogus.name = summary.name
	bogus.level = summary.level
	bogus.xp = summary.xp
	var activation: Dictionary = session.activate(bogus_id, bogus)
	check(bool(activation.get("ok", false)),
		"the unresolvable session activates: %s" % activation.get("error"))
	var reopened: Dictionary = town.enter_shop()
	check(bool(reopened.get("ok", false)),
		"the shop reopens for the structured failure: %s"
		% reopened.get("error"))
	var repick: Dictionary = town.pick_shop_item(PURCHASE_ITEM)
	check(bool(repick.get("ok", false)),
		"Victory Arch picks for the structured failure")
	var failed: Dictionary = await town.confirm_purchase()
	check(not bool(failed.get("ok", true)),
		"the unresolvable save fails the intent")
	check_eq(str(failed.get("code", "")), "unknown_user_id",
		"the structured failure surfaces its code: %s" % failed.get("error"))
	check(town.shop_error.contains("unknown_user_id"),
		"the explicit error names the structured failure")
	check_eq(api.purchase_requests, requests_before + 1,
		"the failed intent still sent exactly once")
	check_eq(_state_snapshot(state), snapshot_before,
		"the structured failure changes no state")
	check_eq(town.storage_rows(), ["(empty)"],
		"the structured failure leaves the readout untouched")
	var restore: Dictionary = session.activate(pid, summary)
	check(bool(restore.get("ok", false)),
		"the real session restores: %s" % restore.get("error"))
	check_eq(session.user_id(), pid, "the restored session names the save")


## A failed catalog leaves the shop unavailable behind the named error: no
## surface, no entries, no request, no state change — and the applied
## state from the successful apply stays intact.
func _check_catalog_unavailable(town: Node2D, state: Variant,
		api: Variant) -> void:
	var requests_open: int = api.purchase_requests
	var snapshot_open := _state_snapshot(state)
	var closing: Dictionary = town.cancel_shop()
	check(bool(closing.get("ok", false)),
		"the shop closes before the catalog-failure check: %s"
		% closing.get("error"))
	town.set_shop_catalog({"ok": false, "error":
		"[catalog] parse rejected: field 'items' of item 0 is invalid"})
	check_eq(town.shop_catalog_entries().size(), 0,
		"a failed catalog offers no entries")
	var unavailable: Dictionary = town.enter_shop()
	check(not bool(unavailable.get("ok", true)),
		"a failed catalog leaves the shop unavailable")
	check_eq(str(unavailable.get("code", "")), "shop_unavailable",
		"the unavailable rejection names the condition")
	check(String(unavailable.get("error", "")).contains("field 'items'"),
		"the explicit error carries the catalog failure: %s"
		% unavailable.get("error"))
	check(not town.shop_active(), "no surface opens on a failed catalog")
	check(not town.ui.is_slot_visible("shop"),
		"no shop shows on a failed catalog")
	check_eq(api.purchase_requests, requests_open,
		"the failed catalog never sent a request")
	check_eq(_state_snapshot(state), snapshot_open,
		"the failed catalog changes no state")


## LAST scenario (it waits out the refused loopback endpoint): the intent
## goes out over the legacy transport, the endpoint refuses it, and the
## explicit error names `unreachable_endpoint` with no state change (the
## same no-mutation contract as a structured failure).
func _check_transport_failure(town: Node2D, state: Variant, api: Variant,
		payload: Dictionary) -> void:
	town.set_shop_catalog(PlacementCatalog.parse(payload))
	var reopened: Dictionary = town.enter_shop()
	check(bool(reopened.get("ok", false)),
		"the shop reopens for the transport scenario: %s"
		% reopened.get("error"))
	var pick_transport: Dictionary = town.pick_shop_item(PURCHASE_ITEM)
	check(bool(pick_transport.get("ok", false)),
		"Victory Arch picks for the transport scenario")
	var endpoint := _endpoint()
	check(endpoint != "",
		"a loopback endpoint resolves for the transport scenario")
	if endpoint == "":
		return
	var requests_before: int = api.purchase_requests
	var snapshot_before := _state_snapshot(state)
	api.configure("legacy_v0", endpoint)
	var attempt: Dictionary = await town.confirm_purchase()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(town.shop_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.purchase_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the transport failure changes no state")
	check_eq(town.storage_rows(), ["(empty)"],
		"the transport failure leaves the readout untouched")
	check(town.shop_active(), "the shop survives the transport failure")
	# The last state-changing check runs against the fake again, so the
	# implementation switch is undone here rather than leaked.
	api.configure("fake")


## The live-purchase scenario (verify-boot's purchase-live phase): one
## typed intent through the real Compatibility endpoint, so the unchanged
## legacy `command()` executes `buy_stored_item_cash` over the disposable
## corpus. This side asserts the documented typed response; the phase
## harness separately asserts the corpus save file mutated. No fixture is
## touched.
func _check_live_purchase() -> void:
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
	var bought: Variant = await api.purchase_item(pid, PURCHASE_ITEM)
	check(bought is BootData.PurchaseResult,
		"the live purchase returns a typed result")
	if not (bought is BootData.PurchaseResult):
		return
	var typed := bought as BootData.PurchaseResult
	check(typed.ok, "the live purchase succeeds: %s / %s" % [
		typed.error_code, typed.error_message])
	if not typed.ok:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live purchase protocol is compat-v0")
	check_eq(typed.result, "success",
		"the legacy result string is verbatim")
	check(typed.server_time > 0,
		"the live server_time is a positive wall-clock epoch")
	check_eq(typed.store, {"105": 1},
		"the live response carries the full storage mapping")
	check(typed.resources != null, "the live response carries typed resources")
	if typed.resources == null:
		return
	check_eq(typed.resources.cash, 0,
		"the live response deducts the derived 5 cash")
	check_eq(typed.resources.gold, 2000, "gold follows the response")
	check_eq(typed.resources.wood, 2000, "wood follows the response")
	check_eq(typed.resources.oil, 2000, "oil follows the response")
	check_eq(typed.resources.steel, 2000, "steel follows the response")
	check_eq(typed.resources.mana, 0, "mana follows the response")
	check_eq(typed.resources.xp, 4, "xp follows the response")
	print("[test] live-purchase applied item=%d store=%s cash=%d"
		% [PURCHASE_ITEM, JSON.stringify(typed.store), typed.resources.cash])


## The catalog derives from the payload in hand: this whole run must not
## issue a bootstrap request (spec: "parsed fail-closed from the bootstrap
## payload the client already receives").
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


## The shop's VBox panel inside the shop slot root (null before the first
## entry or when the slot never registered).
func _shop_panel(town: Variant) -> Variant:
	if not town.ui.has_slot("shop"):
		return null
	var slot: Control = town.ui.slot_root("shop")
	if slot == null or slot.get_child_count() == 0:
		return null
	return slot.get_child(0)


## The named button anywhere inside the shop panel (the action row nests
## the confirm/cancel pair), or null.
func _button_named(panel: Node, button_name: String) -> Variant:
	for child: Variant in panel.get_children():
		if child is Button and String((child as Button).name) == button_name:
			return child
		if child is Node:
			var nested: Variant = _button_named(child as Node, button_name)
			if nested != null:
				return nested
	return null


## The storage readout's on-screen label texts, in panel order.
func _storage_labels(panel: Node) -> Array:
	var labels: Array = []
	for child: Variant in panel.get_children():
		if child is VBoxContainer and String((child as VBoxContainer).name) \
				== "storage_entries":
			for row: Variant in (child as VBoxContainer).get_children():
				if row is Label:
					labels.append((row as Label).text)
	return labels


## The on-screen status line text ("" before a panel exists).
func _shop_status(town: Variant) -> String:
	var panel: Variant = _shop_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "status":
			return (child as Label).text
	return ""


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file
## (the scope scan restricts transport references to the legacy-v0
## implementation).
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-shop and failure paths).
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append(placement.raw)
	var storage := {}
	for key: Variant in state.storage:
		storage[str(key)] = int(state.storage[key])
	return JSON.stringify({
		"placements": rows,
		"storage": storage,
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
