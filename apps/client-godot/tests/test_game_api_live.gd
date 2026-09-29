extends "res://tests/test_base.gd"
## Headless GameApi suite for the legacy-v0 implementation (task 3.3, spec
## "Boot live against Compatibility API"; extended by the
## building-placement change's task 3.2 with the placement parity of spec
## "Place through either implementation", by `building-purchase` with the
## purchase parity of spec "Purchase through either implementation", and by
## `building-move` with the move parity of spec "Move through either
## implementation").
##
## Requires a running Compatibility API v0 on loopback — verify-boot.ps1
## wraps this suite with `compat_live_phase.py`, which starts
## `apps/compat-api/run.py` (disposable corpus) and tears it down again. The
## suite compares every live typed result against the fake implementation's,
## so both must yield the same boot data and the same placement and purchase
## results (time-dependent fields excepted).

const BootData = preload("res://scripts/gameapi/boot_data.gd")

const ARG_ENDPOINT := "--gameapi-endpoint="
const UNKNOWN_USER := "does-not-exist-0000"
## The executed-legacy purchase transaction's item (Victory Arch, priced
## `{"c": 5}` in the committed config) — the one intent both
## implementations must answer identically.
const PURCHASE_ITEM := 105
## The item's derived cash price (the committed config's `costs {"c": 5}`).
const PURCHASE_PRICE := 5
## A store-listed building priced in wood, not cash: this command's price
## is not derivable, so both implementations fail closed with
## `costs_not_cash` rather than inventing a price.
const WOOD_PRICED_ITEM := 1
## The executed-legacy move transaction's target: the Turret I (item 22) at
## legacy map key 11, from (58,48) to (58,47) — the one move both
## implementations must answer identically.
const MOVE_ITEM := 22
const MOVE_INDEX := 11
const MOVE_CELL := Vector2i(58, 47)
## An integer index that names no row in the corpus save: the endpoint
## resolves it before executing and answers 404 `unknown_item_index`, so
## legacy's silent no-op is never reported as a success.
const MOVE_UNKNOWN_INDEX := 9999


func run_scenario() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var endpoint := _endpoint()
	check(endpoint != "", "endpoint resolved from the runtime override or "
		+ "the project setting")
	if endpoint == "":
		return

	# Fake reference first: the live results must match these typed shapes.
	api.configure("fake")
	var fake_ref: Variant = await api.list_sessions()
	check(fake_ref is BootData.SaveListResult,
		"fake reference returns the typed result")
	if not (fake_ref is BootData.SaveListResult):
		return
	var fake_list: BootData.SaveListResult = fake_ref
	check(fake_list.ok, "fake reference resolves: %s" % fake_list.error_message)
	check(fake_list.saves.size() > 0, "fake reference names at least one save")
	if not fake_list.ok or fake_list.saves.is_empty():
		return

	api.configure("legacy_v0", endpoint)
	check_eq(api.implementation_name(), "legacy_v0",
		"implementation switch selects legacy_v0")
	var live: Variant = await api.list_sessions()
	check(live is BootData.SaveListResult,
		"live list_sessions returns the typed result")
	if not (live is BootData.SaveListResult):
		return
	var live_list: BootData.SaveListResult = live
	check(live_list.ok, "live session list resolves over loopback: %s"
		% live_list.error_message)
	if not live_list.ok:
		return
	check_eq(live_list.protocol, fake_list.protocol,
		"live protocol equals the fake's")
	check_eq(live_list.game_version, fake_list.game_version,
		"live game version equals the fake's")
	check_eq(live_list.saves.size(), fake_list.saves.size(),
		"live save count equals the fake's")
	check(live_list.server_time > 0, "live server_time is a positive epoch")
	# List order is not part of the v0 contract; compare id-keyed.
	var fake_by_id := {}
	for save in fake_list.saves:
		fake_by_id[save.id] = save
	for live_save in live_list.saves:
		check(fake_by_id.has(live_save.id),
			"live save id %s exists in the fake list" % live_save.id)
		if fake_by_id.has(live_save.id):
			var other: BootData.SaveInfo = fake_by_id[live_save.id]
			check_eq(live_save.name, other.name,
				"save %s name equals the fake's" % live_save.id)
			check_eq(live_save.xp, other.xp,
				"save %s xp equals the fake's" % live_save.id)
			check_eq(live_save.level, other.level,
				"save %s level equals the fake's" % live_save.id)

	var user_id: String = fake_list.saves[0].id
	var fake_boot: Variant = await api.get_bootstrap(user_id)
	check(fake_boot is BootData.BootstrapResult
		and fake_boot.ok, "fake bootstrap reference resolves")

	api.configure("legacy_v0", endpoint)
	var live_boot: Variant = await api.get_bootstrap(user_id)
	check(live_boot is BootData.BootstrapResult,
		"live get_bootstrap returns the typed result")
	if not (live_boot is BootData.BootstrapResult):
		return
	var result: BootData.BootstrapResult = live_boot
	check(result.ok, "live bootstrap resolves over loopback: %s"
		% result.error_message)
	if not result.ok:
		return
	check_eq(result.protocol, BootData.PROTOCOL,
		"live bootstrap protocol is compat-v0")
	check(result.summary != null, "live bootstrap carries a typed summary")
	check(result.config != null and not result.config.raw.is_empty(),
		"live config payload is wrapped and non-empty")
	check(result.player_info != null, "live player_info payload is wrapped")
	if fake_boot is BootData.BootstrapResult and fake_boot.ok \
			and result.summary != null:
		var reference: BootData.BootstrapResult = fake_boot
		check_eq(result.summary.name, reference.summary.name,
			"live summary name equals the fake's")
		check_eq(result.summary.level, reference.summary.level,
			"live summary level equals the fake's")
		check_eq(result.summary.xp, reference.summary.xp,
			"live summary xp equals the fake's")
		check_eq(result.game_version, reference.game_version,
			"live bootstrap game version equals the fake's")
		# Stable keys only: values of time-dependent config fields differ by
		# design (field-stability record), so compare the shape, not values.
		var keys_ok := true
		for key in reference.config.raw.keys():
			if not result.config.raw.has(key):
				keys_ok = false
		check(keys_ok, "live config carries the fixture's top-level keys")
		if result.player_info != null and reference.player_info != null:
			check_eq(result.player_info.player_name,
				reference.player_info.player_name,
				"live typed player name equals the fake's")

	var unknown: Variant = await api.get_bootstrap(UNKNOWN_USER)
	check(unknown is BootData.BootstrapResult,
		"live unknown user returns the typed result")
	if unknown is BootData.BootstrapResult:
		var failure: BootData.BootstrapResult = unknown
		check(not failure.ok, "live unknown user fails")
		check_eq(failure.error_code, "unknown_user_id",
			"live structured error code matches the fake's")
		check(failure.summary == null,
			"live structured failure carries no summary")

	await _check_live_placement(api, endpoint, user_id)
	await _check_live_purchase(api, endpoint, user_id)
	await _check_live_move(api, endpoint, user_id)
	# The live corpus now carries both mutating transactions, so this suite's
	# parity claim is stated once, explicitly: the two implementations are
	# compared on the fields each own, and each side's resource bag is
	# compared against ITS OWN pre-purchase bootstrap (the live side has the
	# placement's wood already spent, the fake side does not).

	info("legacy_v0 matched the fake reference over loopback %s" % endpoint)


## Placement through both implementations (task 3.2, spec "Place through
## either implementation"): identical typed shapes, identical authoritative
## values (both sides derive from the committed fresh save), the live
## entry's wall-clock timestamp as the only time-dependent field, and the
## endpoint's structured codes passing through unchanged.
func _check_live_placement(api: Variant, endpoint: String,
		user_id: String) -> void:
	# Fake reference: in-memory state, fixture epoch, fixture-derived values.
	api.configure("fake")
	var fake_ref: Variant = await api.place_building(user_id, 1, 51, 39)
	check(fake_ref is BootData.PlacementResult,
		"fake place_building returns the typed result")
	if not (fake_ref is BootData.PlacementResult):
		return
	var fake: BootData.PlacementResult = fake_ref
	check(fake.ok, "fake placement reference resolves: %s"
		% fake.error_message)
	if not fake.ok:
		return

	# The same intent against the running Compatibility API.
	api.configure("legacy_v0", endpoint)
	var live_ref: Variant = await api.place_building(user_id, 1, 51, 39)
	check(live_ref is BootData.PlacementResult,
		"live place_building returns the typed result")
	if not (live_ref is BootData.PlacementResult):
		return
	var live: BootData.PlacementResult = live_ref
	check(live.ok, "live placement resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check_eq(live.protocol, fake.protocol,
		"live placement protocol equals the fake's")
	check_eq(live.result, "success", "live reports the legacy success result")
	check(live.placement != null and fake.placement != null,
		"both placements carry a typed entry")
	check(live.resources != null and fake.resources != null,
		"both placements carry typed resources")
	if live.placement == null or fake.placement == null \
			or live.resources == null or fake.resources == null:
		return
	check_eq(live.placement.item_id, fake.placement.item_id,
		"placement item id equals the fake's")
	check_eq(live.placement.x, fake.placement.x,
		"placement anchor x equals the fake's")
	check_eq(live.placement.y, fake.placement.y,
		"placement anchor y equals the fake's")
	check_eq(live.placement.orientation, fake.placement.orientation,
		"placement orientation equals the fake's")
	check_eq(live.placement.player, fake.placement.player,
		"placement player team equals the fake's")
	check_eq(live.placement.store.size(), fake.placement.store.size(),
		"placement store equals the fake's")
	check(live.placement.attr == fake.placement.attr,
		"placement attr equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.placement.attr),
		JSON.stringify(fake.placement.attr)])
	check(fake.placement.timestamp > 0,
		"fake entry timestamp is the fixture epoch (deterministic)")
	check(live.placement.timestamp > 0,
		"live entry timestamp is a positive wall-clock epoch (time-dependent)")
	# Same committed fresh save on both sides: authoritative resources
	# agree, and wood pins both to the documented fixture values.
	check_eq(live.resources.xp, fake.resources.xp, "xp equals the fake's")
	check_eq(live.resources.gold, fake.resources.gold,
		"gold equals the fake's")
	check_eq(live.resources.wood, fake.resources.wood,
		"wood equals the fake's")
	check_eq(live.resources.oil, fake.resources.oil,
		"oil equals the fake's")
	check_eq(live.resources.steel, fake.resources.steel,
		"steel equals the fake's")
	check_eq(live.resources.cash, fake.resources.cash,
		"cash equals the fake's")
	check_eq(live.resources.mana, fake.resources.mana,
		"mana equals the fake's")
	check_eq(live.resources.wood, 1970,
		"wood is the committed fresh 2000 minus the w30 cost")

	# Structured service errors pass through with their original codes.
	var live_bad_item: Variant = await api.place_building(
		user_id, 999999999, 51, 39)
	check(live_bad_item is BootData.PlacementResult,
		"live unknown item returns the typed result")
	if live_bad_item is BootData.PlacementResult:
		var bad_item: BootData.PlacementResult = live_bad_item
		check(not bad_item.ok, "live unknown item is a structured failure")
		check_eq(bad_item.error_code, "unknown_item_id",
			"live structured error passes through with the endpoint's code")
		check(bad_item.placement == null and bad_item.resources == null,
			"live structured failure carries no partial payload")
	var live_bad_grid: Variant = await api.place_building(user_id, 1, 100, 39)
	check(live_bad_grid is BootData.PlacementResult,
		"live out-of-grid anchor returns the typed result")
	if live_bad_grid is BootData.PlacementResult:
		var bad_grid: BootData.PlacementResult = live_bad_grid
		check(not bad_grid.ok,
			"live out-of-grid anchor is a structured failure")
		check_eq(bad_grid.error_code, "invalid_coordinates",
			"live grid violation names the endpoint's code")
		check(bad_grid.placement == null and bad_grid.resources == null,
			"live grid failure carries no partial payload")

	# The fake derives the same code for the same intent (structured-failure
	# parity; the double never talks to the service).
	api.configure("fake")
	var fake_bad_item: Variant = await api.place_building(
		user_id, 999999999, 51, 39)
	check(fake_bad_item is BootData.PlacementResult and not fake_bad_item.ok,
		"fake fails the same intent offline")
	if fake_bad_item is BootData.PlacementResult:
		check_eq(fake_bad_item.error_code, "unknown_item_id",
			"structured codes match between implementations")


## Endpoint for this run: `--gameapi-endpoint=` user argument, else the
## project setting (loopback default). No hardcoded endpoint in this file.
func _endpoint() -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(ARG_ENDPOINT):
			return argument.trim_prefix(ARG_ENDPOINT)
	return str(ProjectSettings.get_setting("gameapi/endpoint", ""))


## Purchase through both implementations (building-purchase task 3.3,
## spec "Purchase through either implementation"): the same typed shape
## from both, the endpoint's structured codes passing through unchanged,
## and each side's authoritative storage and resources checked against its
## OWN pre-purchase state.
##
## Why each side is compared against itself rather than across: this phase
## runs BOTH mutating transactions against the same disposable corpus, and
## the live side therefore already carries the placement's 30-wood spend
## while the fake double starts from the committed fresh-save fixture. The
## honest parity claim is the one the contract actually makes: both
## implementations produce the same typed shape, the same storage mapping
## for this item, and a resource bag equal to their own pre-purchase
## values except for the derived cash price. Claiming identical absolute
## resources across the two sides here would be a false claim, not a
## stronger test.
func _check_live_purchase(api: Variant, endpoint: String,
		user_id: String) -> void:
	# The live side's pre-purchase resources, read from the corpus itself.
	api.configure("legacy_v0", endpoint)
	var live_before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(live_before != null,
		"the live corpus pre-purchase resources resolve")

	# The same intent against the running Compatibility API.
	var live_ref: Variant = await api.purchase_item(user_id, PURCHASE_ITEM)
	check(live_ref is BootData.PurchaseResult,
		"live purchase_item returns the typed result")
	if not (live_ref is BootData.PurchaseResult):
		return
	var live: BootData.PurchaseResult = live_ref
	check(live.ok, "live purchase resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check(live.server_time > 0,
		"live server_time is a positive wall-clock epoch (time-dependent)")
	check_eq(live.protocol, BootData.PROTOCOL,
		"live purchase protocol is compat-v0")
	check(live.game_version != "",
		"the live purchase response carries the game version")
	check_eq(live.result, "success", "live reports the legacy success result")
	check(live.resources != null, "the live response carries typed resources")
	if live.resources == null or live_before == null:
		return
	check_eq(live.store, {"105": 1},
		"the live response carries the full storage mapping (design D4)")
	# The derived cash price is the ONLY resource the purchase changes.
	check_eq(live.resources.cash, maxi(live_before.cash - PURCHASE_PRICE, 0),
		"cash falls by exactly the derived price (legacy clamp included)")
	for key in ["gold", "wood", "oil", "steel", "mana", "xp"]:
		check_eq(int(live.resources.get(key)), int(live_before.get(key)),
			"%s is untouched by the purchase (design D2)" % key)

	# Fake reference: an independent in-memory state over the committed
	# purchase-fixture before-state.
	api.configure("fake")
	var fake_ref: Variant = await api.purchase_item(user_id, PURCHASE_ITEM)
	check(fake_ref is BootData.PurchaseResult,
		"fake purchase_item returns the typed result")
	if not (fake_ref is BootData.PurchaseResult):
		return
	var fake: BootData.PurchaseResult = fake_ref
	check(fake.ok, "fake purchase reference resolves: %s"
		% fake.error_message)
	if not fake.ok:
		return
	check(fake.resources != null, "the fake reference carries resources")
	if fake.resources == null:
		return
	check_eq(live.protocol, fake.protocol,
		"live purchase protocol equals the fake's")
	check_eq(live.game_version, fake.game_version,
		"live purchase game version equals the fake's")
	check_eq(live.result, fake.result,
		"live purchase result string equals the fake's")
	check_eq(live.store, fake.store,
		"live purchase storage equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.store), JSON.stringify(fake.store)])
	# The fake runs from the committed fresh save, so its absolute values
	# are the fixture's documented ones.
	check_eq(fake.resources.cash, 0,
		"the fake deducts the derived 5 cash from the fixture's 5")
	check_eq(fake.resources.gold, 2000, "the fake's gold equals the fixture's")
	check_eq(fake.resources.wood, 2000, "the fake's wood equals the fixture's")
	check_eq(fake.resources.oil, 2000, "the fake's oil equals the fixture's")
	check_eq(fake.resources.steel, 2000, "the fake's steel equals the fixture's")
	check_eq(fake.resources.mana, 0, "the fake's mana equals the fixture's")
	check_eq(fake.resources.xp, 4, "the fake's xp equals the fixture's")

	# Structured service errors pass through with their original codes, and
	# the fake derives the same code for the same intent offline.
	api.configure("legacy_v0", endpoint)
	var live_bad_item: Variant = await api.purchase_item(user_id, 999999999)
	check(live_bad_item is BootData.PurchaseResult,
		"live unknown item returns the typed result")
	if live_bad_item is BootData.PurchaseResult:
		var bad_item: BootData.PurchaseResult = live_bad_item
		check(not bad_item.ok, "live unknown item is a structured failure")
		check_eq(bad_item.error_code, "unknown_item_id",
			"live structured error passes through with the endpoint's code")
		check(bad_item.resources == null and bad_item.store.is_empty(),
			"live structured failure carries no partial payload")
	var live_wood: Variant = await api.purchase_item(user_id, WOOD_PRICED_ITEM)
	check(live_wood is BootData.PurchaseResult,
		"live wood-priced item returns the typed result")
	if live_wood is BootData.PurchaseResult:
		var wood: BootData.PurchaseResult = live_wood
		check(not wood.ok,
			"a wood-priced item is refused by the cash-only derivation")
		check_eq(wood.error_code, "costs_not_cash",
			"the derivation boundary names its own code")
	api.configure("fake")
	var fake_wood: Variant = await api.purchase_item(user_id, WOOD_PRICED_ITEM)
	check(fake_wood is BootData.PurchaseResult and not fake_wood.ok,
		"fake fails the same intent offline")
	if fake_wood is BootData.PurchaseResult:
		check_eq(fake_wood.error_code, "costs_not_cash",
			"structured codes match between implementations")
	print("[test] live-purchase applied item=%d store=%s cash=%d"
		% [PURCHASE_ITEM, JSON.stringify(live.store), live.resources.cash])


## Move through both implementations (building-move task 3.3, spec "Move
## through either implementation"): the SAME typed placement result both
## implementations already share for a placement (design D4), the live
## response's persisted row matching the executed fixture's after-state for
## every stable field, the neutral price vector leaving the resource bag
## untouched, and the endpoint's structured codes passing through unchanged.
##
## The corpus in this phase already carries the placement and purchase
## transactions, so the live side's resources are its own — the honest claim
## is the one the contract makes: the move changes the row's cell and
## nothing else, and both implementations produce the same typed shape and
## the same row.
func _check_live_move(api: Variant, endpoint: String,
		user_id: String) -> void:
	# The live side's pre-move resources, read from the corpus itself.
	api.configure("legacy_v0", endpoint)
	var live_before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(live_before != null, "the live corpus pre-move resources resolve")

	var live_ref: Variant = await api.move_building(user_id, MOVE_INDEX,
		MOVE_CELL.x, MOVE_CELL.y)
	check(live_ref is BootData.PlacementResult,
		"live move_building returns the typed result")
	if not (live_ref is BootData.PlacementResult):
		return
	var live: BootData.PlacementResult = live_ref
	check(live.ok, "live move resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check_eq(live.protocol, BootData.PROTOCOL,
		"live move protocol is compat-v0")
	check_eq(live.result, "success",
		"live move reports the legacy success result")
	check(live.placement != null and live.resources != null,
		"the live move response carries the persisted row and resources")
	if live.placement == null or live.resources == null:
		return
	# The persisted row, re-read from the save after execution: the cell the
	# intent named and every other field untouched.
	check_eq(live.placement.item_id, MOVE_ITEM,
		"the live row names the Turret I")
	check_eq(live.placement.x, MOVE_CELL.x,
		"the live row carries the requested x")
	check_eq(live.placement.y, MOVE_CELL.y,
		"the live row carries the requested y")
	check_eq(live.placement.player, 1,
		"the live row keeps the player's team field (unchanged by a move)")
	if live_before != null:
		# The derived price vector is neutral, so a move changes NO resource
		# (design D2) — the strongest available assertion, and the reason the
		# committed fixture's before/after resource bags are identical.
		for key in ["gold", "wood", "oil", "steel", "mana", "xp", "cash"]:
			check_eq(int(live.resources.get(key)), int(live_before.get(key)),
				"%s is untouched by the move (neutral vector, design D2)"
					% key)

	# Fake reference: an independent in-memory state over the committed
	# move-fixture before-state.
	api.configure("fake")
	var fake_ref: Variant = await api.move_building(user_id, MOVE_INDEX,
		MOVE_CELL.x, MOVE_CELL.y)
	check(fake_ref is BootData.PlacementResult,
		"fake move_building returns the typed result")
	if not (fake_ref is BootData.PlacementResult):
		return
	var fake: BootData.PlacementResult = fake_ref
	check(fake.ok, "fake move reference resolves: %s" % fake.error_message)
	if not fake.ok or fake.placement == null or fake.resources == null:
		return
	check_eq(live.protocol, fake.protocol,
		"live move protocol equals the fake's")
	check_eq(live.result, fake.result,
		"live move result string equals the fake's")
	check_eq(live.placement.item_id, fake.placement.item_id,
		"live move item id equals the fake's")
	check_eq(live.placement.x, fake.placement.x,
		"live move x equals the fake's")
	check_eq(live.placement.y, fake.placement.y,
		"live move y equals the fake's")
	check_eq(live.placement.orientation, fake.placement.orientation,
		"live move orientation equals the fake's (unchanged by a move)")
	check_eq(live.placement.player, fake.placement.player,
		"live move player field equals the fake's")
	check_eq(live.placement.store.size(), fake.placement.store.size(),
		"live move store equals the fake's (unchanged by a move)")
	check(live.placement.attr == fake.placement.attr,
		"live move attr equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.placement.attr),
		JSON.stringify(fake.placement.attr)])
	# The fake's own row: the executed fixture's after-state, verbatim.
	check_eq(fake.placement.y, 47,
		"the fake reproduces the fixture's moved y")
	check_eq(fake.placement.timestamp, 0,
		"the fake never restamps the row's timestamp")

	# Structured service errors pass through with their original codes, and
	# the fake derives the same code for the same intent offline.
	api.configure("legacy_v0", endpoint)
	var live_unknown: Variant = await api.move_building(user_id,
		MOVE_UNKNOWN_INDEX, MOVE_CELL.x, MOVE_CELL.y)
	check(live_unknown is BootData.PlacementResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.PlacementResult:
		var unknown: BootData.PlacementResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.placement == null and unknown.resources == null,
			"the live structured failure carries no partial payload")
	var live_grid: Variant = await api.move_building(user_id, MOVE_INDEX,
		100, MOVE_CELL.y)
	check(live_grid is BootData.PlacementResult,
		"the live out-of-grid anchor returns the typed result")
	if live_grid is BootData.PlacementResult:
		var bad_grid: BootData.PlacementResult = live_grid
		check(not bad_grid.ok,
			"the live out-of-grid anchor is a structured failure")
		check_eq(bad_grid.error_code, "invalid_coordinates",
			"the live grid violation names the endpoint's code")
	api.configure("fake")
	var fake_unknown: Variant = await api.move_building(user_id,
		MOVE_UNKNOWN_INDEX, MOVE_CELL.x, MOVE_CELL.y)
	check(fake_unknown is BootData.PlacementResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.PlacementResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-move applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [MOVE_INDEX, live.placement.x, live.placement.y,
		live.resources.xp, live.resources.gold])


## The seven stored resources of the running corpus, as the typed
## `BootData.Resources` the purchase response carries. This is the
## pre-purchase reference the live purchase is compared against — read from
## the corpus itself, never from the fake's fixture, because the live side
## has already executed the placement transaction in this phase.
func _live_resources(api: Variant, endpoint: String,
		user_id: String) -> BootData.Resources:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus pre-purchase bootstrap resolves")
		return null
	# The resources live in the player-info payload; this suite reads them
	# out of it directly so the reference is a plain value, not a second
	# typed parse that could mask a transport difference.
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus pre-purchase payload is readable")
		return null
	var raw: Dictionary = (info as BootData.PlayerInfoPayload).raw
	# The corpus carries the storage mapping the purchase is about to
	# extend; recording it makes the pre/post comparison explicit.
	info("live pre-purchase storage=%s"
		% JSON.stringify(raw.get("map", {}).get("store", {})))
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var player: Dictionary = raw.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = raw.get("privateState", {}) as Dictionary
	var resources := BootData.Resources.new()
	resources.xp = int(map.get("xp", 0))
	resources.gold = int(map.get("gold", 0))
	resources.wood = int(map.get("wood", 0))
	resources.oil = int(map.get("oil", 0))
	resources.steel = int(map.get("steel", 0))
	resources.cash = int(player.get("cash", 0))
	resources.mana = int(priv.get("mana", 0))
	return resources
