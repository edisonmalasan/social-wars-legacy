extends "res://tests/test_base.gd"
## Headless GameApi suite for the legacy-v0 implementation (task 3.3, spec
## "Boot live against Compatibility API"; extended by the
## building-placement change's task 3.2 with the placement parity of spec
## "Place through either implementation", by `building-purchase` with the
## purchase parity of spec "Purchase through either implementation", by
## `building-move` with the move parity of spec "Move through either
## implementation", by `building-sell` with the sell parity of spec "Sell
## through either implementation", by `building-store` with the store
## parity of spec "Store through either implementation", and by
## `building-upgrade` with the upgrade parity of spec "Upgrade through either
## implementation", and by `building-construction` with the construction
## parity of spec "Construction through either implementation", and by
## `building-collect` with the collection parity of spec "Collect through
## either implementation").
##
## Requires a running Compatibility API v0 on loopback — verify-boot.ps1
## wraps this suite with `compat_live_phase.py`, which starts
## `apps/compat-api/run.py` (disposable corpus) and tears it down again. The
## suite compares every live typed result against the fake implementation's,
## so both must yield the same boot data and the same placement, purchase,
## move, sell, store, upgrade, construction, and collect results
## (time-dependent fields excepted).

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
## The executed-legacy sell transaction's target: the Turret I (item 22) at
## legacy map key 20, anchored at (41,48) — the one sale both
## implementations must answer identically.
const SELL_ITEM := 22
const SELL_INDEX := 20
const SELL_CELL := Vector2i(41, 48)
## An integer index that names no row in the corpus save: the sell endpoint
## resolves it before executing and answers 404 `unknown_item_index`, so
## legacy's silent no-op early return is never reported as a success.
const SELL_UNKNOWN_INDEX := 9999
## The executed-legacy store transaction's target: the Tree decoration
## (item 905) at legacy map key 2, anchored at (53,39) — the one store both
## implementations must answer identically.
const STORE_ITEM := 905
const STORE_INDEX := 2
const STORE_CELL := Vector2i(53, 39)
## An integer index that names no row in the corpus save: the store endpoint
## resolves it before executing and answers 404 `unknown_item_index`, so
## legacy's silent early return is never reported as a success.
const STORE_UNKNOWN_INDEX := 9999
## The executed-legacy upgrade transaction's target: the Wall I (item 23) at
## legacy map key 12, anchored at (45,49), REPLACED IN PLACE by the Wall II
## (item 24) at the same key and the same cell — the one upgrade both
## implementations must answer identically, and the one transaction whose
## reused key the live response proves.
const UPGRADE_ITEM := 23
const UPGRADE_TARGET := 24
const UPGRADE_INDEX := 12
const UPGRADE_CELL := Vector2i(45, 49)
## A placed building whose committed configuration reference means NO PATH
## (a Bridge, `upgrades_to` `-1`): both implementations must fail closed with
## `no_upgrade_path` instead of reducing it to a bare sale. The Bridge at
## legacy key 35 is used rather than the Tree at key 2 because this phase's
## own store transaction has already popped the Tree from that key.
const UPGRADE_NO_PATH_INDEX := 35
const UPGRADE_NO_PATH_ITEM := 929
## An integer index that names no row in the corpus save: the upgrade
## endpoint resolves it before executing and answers 404
## `unknown_item_index`, so legacy's silent no-op is never reported as a
## success.
const UPGRADE_UNKNOWN_INDEX := 9999
## The executed-legacy construction transaction's target: the Turret I (item
## 22) at legacy map key 11, anchored at (58,48), whose row is mutated IN
## PLACE through the three actions (start, click, finish) — the same key and
## cell throughout, which is what this line's endpoint proves per action. Every
## placed row of the corpus resolves a positive committed build time, so no
## `no_build_time` failure is reachable here (the compat suite owns that path by
## stubbing the accessor, and the fake mirrors it over an in-memory row).
const CONSTRUCTION_ITEM := 22
const CONSTRUCTION_INDEX := 11
const CONSTRUCTION_CELL := Vector2i(58, 48)
## The item's committed build time and click requirement: the start countdown
## the service derives and the threshold the client compares against (no
## legacy branch compares anything).
const CONSTRUCTION_BUILD_TIME := 5
const CONSTRUCTION_CLICKS := 1
const CONSTRUCTION_START := "start"
const CONSTRUCTION_CLICK := "click"
const CONSTRUCTION_FINISH := "finish"
## An integer index that names no row in the corpus save: the construction
## endpoint resolves it before executing and answers 404
## `unknown_item_index`, so legacy's silent no-op is never reported as a
## success.
const CONSTRUCTION_UNKNOWN_INDEX := 9999
## The live collection this phase drives: the **Trees decoration at legacy key
## 21** (item 930), NOT the Tree at key 2 the fixture records — this phase runs
## after the store phase, which popped the Tree at key 2 in its own
## independent transaction, and after the construction phase, which left key
## 11 under construction. Key 21 is untouched by either and records the same
## committed income (`collect 20`, `collect_type "w"`, `collect_xp 1`, `max_collects
## 0`), so it exercises the identical content-derived derivation. Every corpus
## row records `item[3] == 0`, so the elapsed time is unbounded and the TOP
## committed rung applies deterministically.
const COLLECT_ITEM := 930
const COLLECT_INDEX := 21
const COLLECT_AMOUNT := 20
const COLLECT_XP := 1
const COLLECT_PAYOUT := [0, 3, 0, 60, 0, 0, 0, 0]
const COLLECT_TIER := 3
## The row the construction-live phase left carrying a recorded countdown, so
## this phase's construction-state refusal is genuinely reachable.
const COLLECT_BUILT_INDEX := 11
## An integer index that names no row in the corpus save: the collect endpoint
## resolves it before executing and answers 404 `unknown_item_index`, so
## legacy's silent no-op is never reported as a success.
const COLLECT_UNKNOWN_INDEX := 9999

## The expansion this live suite drives (building-expand, design D8): the FREE
## committed row at index 0 of the 98-entry positional `expansion_prices`
## schedule, which is the only purchasable entry set on this corpus under
## design D3's requirements rule (94 of the 98 rows record a positive
## neighbour or inventory requirement, and every id the corpus itself owns —
## 35, 36, 45, 46 — is among them). Its derived debit is therefore the
## ALL-ZERO eight-slot vector and no stored resource moves, which makes this the
## STRICTEST form of the value-level post-state proof: a wrong derived price
## would move one. The duplicate and the requirement-blocked ids are the two
## guards the executed-legacy probe showed the legacy server lacks.
const EXPAND_ID := 0
const EXPAND_OWNED := [35, 36, 45, 46]
const EXPAND_DUPLICATE_ID := 35
const EXPAND_BLOCKED_ID := 4
const EXPAND_OUT_OF_RANGE_ID := 98
const EXPAND_NEGATIVE_ID := -1

## The committed corpus's own level position (building-xp): `xp 4` and
## `level 1`, which the committed curve places at level 1 under the ONE-BASED
## reading, so the corpus is already consistent and the endpoint refuses the
## intent with `level_already_current` before the dispatcher runs.
const LEVEL_CORPUS_XP := 4
const LEVEL_CORPUS_LEVEL := 1


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
	await _check_live_sell(api, endpoint, user_id)
	await _check_live_store(api, endpoint, user_id)
	await _check_live_upgrade(api, endpoint, user_id)
	await _check_live_construction(api, endpoint, user_id)
	await _check_live_collect(api, endpoint, user_id)
	await _check_live_expand(api, endpoint, user_id)
	await _check_live_level(api, endpoint, user_id)
	# The live corpus now carries every mutating transaction, so this suite's
	# parity claim is stated once, explicitly: the two implementations are
	# compared on the fields each own, and each side's resource bag is
	# compared against ITS OWN pre-transaction bootstrap (the live side has
	# the placement's wood already spent, the fake side does not).

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


## Sell through both implementations (building-sell task 3.3, spec "Sell
## through either implementation"): the same typed shape from both, the live
## removed row matching the executed fixture's pre-execution row for every
## stable field, the neutral price vector leaving the resource bag
## untouched (and therefore claiming no refund), and the endpoint's
## structured codes passing through unchanged.
##
## The corpus in this phase already carries the placement, purchase, and move
## transactions, so the live side's resources are its own — the honest claim
## is the one the contract makes: a sale removes exactly the row the intent
## names and changes nothing else, and both implementations produce the same
## typed shape and the same removed row.
func _check_live_sell(api: Variant, endpoint: String, user_id: String) -> void:
	# The live side's pre-sale resources, read from the corpus itself.
	api.configure("legacy_v0", endpoint)
	var live_before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(live_before != null,
		"the live corpus pre-sale resources resolve")

	var live_ref: Variant = await api.sell_building(user_id, SELL_INDEX)
	check(live_ref is BootData.SellResult,
		"live sell_building returns the typed result")
	if not (live_ref is BootData.SellResult):
		return
	var live: BootData.SellResult = live_ref
	check(live.ok, "live sale resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check_eq(live.protocol, BootData.PROTOCOL,
		"live sell protocol is compat-v0")
	check(live.game_version != "",
		"the live sell response carries the game version")
	check(live.server_time > 0,
		"live server_time is a positive wall-clock epoch (time-dependent)")
	check_eq(live.result, "success",
		"live sale reports the legacy success result")
	check(live.removed != null and live.resources != null,
		"the live sell response carries the removed row and resources")
	if live.removed == null or live.resources == null:
		return
	# The row is the one read BEFORE execution (design D5): the anchor the
	# save carried, and every other field untouched.
	check_eq(live.removed.item_id, SELL_ITEM,
		"the live removed row names the Turret I")
	check_eq(live.removed.x, SELL_CELL.x,
		"the live removed row carries x=41")
	check_eq(live.removed.y, SELL_CELL.y,
		"the live removed row carries y=48")
	check_eq(live.removed.player, 1,
		"the live removed row keeps the player's team field")
	if live_before != null:
		# The derived price vector is neutral, so a sale changes NO resource
		# (design D2) — and therefore claims no refund at all. This is the
		# strongest available assertion, and the reason the committed
		# fixture's before/after resource bags are identical.
		for key in ["gold", "wood", "oil", "steel", "mana", "xp", "cash"]:
			check_eq(int(live.resources.get(key)), int(live_before.get(key)),
				"%s is untouched by the sale (neutral vector, design D2)"
					% key)

	# Fake reference: an independent in-memory state over the committed
	# sell-fixture before-state.
	api.configure("fake")
	var fake_ref: Variant = await api.sell_building(user_id, SELL_INDEX)
	check(fake_ref is BootData.SellResult,
		"fake sell_building returns the typed result")
	if not (fake_ref is BootData.SellResult):
		return
	var fake: BootData.SellResult = fake_ref
	check(fake.ok, "fake sale reference resolves: %s" % fake.error_message)
	if not fake.ok or fake.removed == null or fake.resources == null:
		return
	check_eq(live.protocol, fake.protocol,
		"live sell protocol equals the fake's")
	check_eq(live.result, fake.result,
		"live sell result string equals the fake's")
	check_eq(live.removed.item_id, fake.removed.item_id,
		"live sell item id equals the fake's")
	check_eq(live.removed.x, fake.removed.x,
		"live sell x equals the fake's")
	check_eq(live.removed.y, fake.removed.y,
		"live sell y equals the fake's")
	check_eq(live.removed.orientation, fake.removed.orientation,
		"live sell orientation equals the fake's (unchanged by a sale)")
	check_eq(live.removed.player, fake.removed.player,
		"live sell player field equals the fake's")
	check_eq(live.removed.store.size(), fake.removed.store.size(),
		"live sell store equals the fake's (unchanged by a sale)")
	check(live.removed.attr == fake.removed.attr,
		"live sell attr equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.removed.attr),
		JSON.stringify(fake.removed.attr)])
	# The fake's own row: the executed fixture's pre-execution row, verbatim.
	check_eq(fake.removed.x, 41, "the fake reproduces the fixture's removed x")
	check_eq(fake.removed.y, 48, "the fake reproduces the fixture's removed y")
	check_eq(fake.removed.timestamp, 0,
		"the fake never restamps the removed row's timestamp")

	# Structured service errors pass through with their original codes, and
	# the fake derives the same code for the same intent offline.
	api.configure("legacy_v0", endpoint)
	var live_unknown: Variant = await api.sell_building(user_id,
		SELL_UNKNOWN_INDEX)
	check(live_unknown is BootData.SellResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.SellResult:
		var unknown: BootData.SellResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.removed == null and unknown.resources == null,
			"the live structured failure carries no partial payload")
	api.configure("fake")
	var fake_unknown: Variant = await api.sell_building(user_id,
		SELL_UNKNOWN_INDEX)
	check(fake_unknown is BootData.SellResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.SellResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-sell applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [SELL_INDEX, live.removed.x, live.removed.y, live.resources.xp,
			live.resources.gold])


## Store through both implementations (building-store task 3.3, spec "Store
## through either implementation"): the same typed shape from both, the live
## removed row matching the executed fixture's pre-execution row for every
## stable field, the live FULL storage mapping matching the corpus's own
## pre-store mapping plus exactly that item's id, the neutral price vector
## leaving the resource bag untouched (and therefore claiming no cost and no
## capacity rule), and the endpoint's structured codes passing through
## unchanged.
##
## The corpus in this phase already carries the placement, purchase, move, and
## sell transactions, so the live side's storage and resources are its own —
## the honest claim is the one the contract makes: a store pops exactly the
## row the intent names, increments that item's storage entry by exactly 1,
## and changes nothing else, and both implementations produce the same typed
## shape and the same removed row.
func _check_live_store(api: Variant, endpoint: String, user_id: String) -> void:
	# The live side's pre-store resources and storage, read from the corpus
	# itself (this phase has already mutated it).
	api.configure("legacy_v0", endpoint)
	var live_before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(live_before != null,
		"the live corpus pre-store resources resolve")
	var storage_before: Variant = await _live_storage(api, endpoint, user_id)
	check(storage_before != null,
		"the live corpus pre-store storage mapping resolves")

	var live_ref: Variant = await api.store_building(user_id, STORE_INDEX)
	check(live_ref is BootData.StoreResult,
		"live store_building returns the typed result")
	if not (live_ref is BootData.StoreResult):
		return
	var live: BootData.StoreResult = live_ref
	check(live.ok, "live store resolves over loopback: %s"
		% live.error_message)
	if not live.ok:
		return
	check_eq(live.protocol, BootData.PROTOCOL, "live store protocol is compat-v0")
	check(live.game_version != "",
		"the live store response carries the game version")
	check(live.server_time > 0,
		"live server_time is a positive wall-clock epoch (time-dependent)")
	check_eq(live.result, "success", "live store reports the legacy success result")
	check(live.removed != null and live.resources != null,
		"the live store response carries the removed row and resources")
	if live.removed == null or live.resources == null:
		return
	# The row is the one read BEFORE execution (design D4/D5): the anchor the
	# save carried, and every other field untouched.
	check_eq(live.removed.item_id, STORE_ITEM,
		"the live removed row names the Tree")
	check_eq(live.removed.x, STORE_CELL.x,
		"the live removed row carries x=53")
	check_eq(live.removed.y, STORE_CELL.y,
		"the live removed row carries y=39")
	check_eq(live.removed.player, 1,
		"the live removed row keeps the player's team field")
	if storage_before != null:
		# The FULL post-execution mapping: every pre-existing entry survives
		# untouched and exactly one new entry (this item, quantity 1) lands,
		# so the client needs no arithmetic of its own.
		var expected: Dictionary = (storage_before as Dictionary).duplicate()
		expected[str(STORE_ITEM)] = int(
			expected.get(str(STORE_ITEM), 0)) + 1
		check_eq(live.store, expected,
			"the live store mapping is the corpus's own plus the one new entry")
	if live_before != null:
		# The derived price vector is neutral, so a store changes NO resource
		# (design D2) — and therefore claims no cost and no capacity rule.
		for key in ["gold", "wood", "oil", "steel", "mana", "xp", "cash"]:
			check_eq(int(live.resources.get(key)), int(live_before.get(key)),
				"%s is untouched by the store (neutral vector, design D2)"
					% key)

	# Fake reference: an independent in-memory state over the committed
	# store-fixture before-state.
	api.configure("fake")
	var fake_ref: Variant = await api.store_building(user_id, STORE_INDEX)
	check(fake_ref is BootData.StoreResult,
		"fake store_building returns the typed result")
	if not (fake_ref is BootData.StoreResult):
		return
	var fake: BootData.StoreResult = fake_ref
	check(fake.ok, "fake store reference resolves: %s" % fake.error_message)
	if not fake.ok or fake.removed == null or fake.resources == null:
		return
	check_eq(live.protocol, fake.protocol,
		"live store protocol equals the fake's")
	check_eq(live.result, fake.result,
		"live store result string equals the fake's")
	check_eq(live.removed.item_id, fake.removed.item_id,
		"live store item id equals the fake's")
	check_eq(live.removed.x, fake.removed.x,
		"live store x equals the fake's")
	check_eq(live.removed.y, fake.removed.y,
		"live store y equals the fake's")
	check_eq(live.removed.orientation, fake.removed.orientation,
		"live store orientation equals the fake's (unchanged by a store)")
	check_eq(live.removed.player, fake.removed.player,
		"live store player field equals the fake's")
	check_eq(live.removed.store.size(), fake.removed.store.size(),
		"live store store equals the fake's (unchanged by a store)")
	check(live.removed.attr == fake.removed.attr,
		"live store attr equals the fake's (live=%s fake=%s)"
		% [JSON.stringify(live.removed.attr),
		JSON.stringify(fake.removed.attr)])
	# The fake's own side: the executed fixture's two-sided outcome, verbatim.
	check_eq(fake.removed.x, 53, "the fake reproduces the fixture's removed x")
	check_eq(fake.removed.y, 39, "the fake reproduces the fixture's removed y")
	check_eq(fake.removed.timestamp, 0,
		"the fake never restamps the removed row's timestamp")
	check_eq(fake.store, {"905": 1},
		"the fake reproduces the executed fixture's storage mapping")

	# Structured service errors pass through with their original codes, and
	# the fake derives the same code for the same intent offline.
	api.configure("legacy_v0", endpoint)
	var live_unknown: Variant = await api.store_building(user_id,
		STORE_UNKNOWN_INDEX)
	check(live_unknown is BootData.StoreResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.StoreResult:
		var unknown: BootData.StoreResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.removed == null and unknown.resources == null,
			"the live structured failure carries no partial payload")
		check(unknown.store.is_empty(),
			"the live structured failure carries no partial storage mapping")
	api.configure("fake")
	var fake_unknown: Variant = await api.store_building(user_id,
		STORE_UNKNOWN_INDEX)
	check(fake_unknown is BootData.StoreResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.StoreResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	print("[test] live-store applied item_index=%d cell=(%d, %d) xp=%d gold=%d"
		% [STORE_INDEX, live.removed.x, live.removed.y, live.resources.xp,
			live.resources.gold])


## Upgrade through both implementations (building-upgrade task 3.3, spec
## "Upgrade through either implementation"): the same typed shape from both,
## the live two-sided response whose key and cell match the pre-request row
## (the reused key is this command's distinguishing fact), the live upgraded
## row holding the derived target tier, the neutral price vector leaving the
## resource bag untouched (and therefore claiming no upgrade cost at all), and
## the endpoint's structured codes passing through unchanged — including
## `no_upgrade_path` for a building the configuration says cannot be upgraded.
##
## The corpus in this phase already carries the placement, purchase, move,
## sell, and store transactions, so the live side's resources are its own —
## the honest claim is the one the contract makes: an upgrade replaces exactly
## the row the intent names, in place, and changes nothing else, and both
## implementations produce the same typed shape and the same two rows.
func _check_live_upgrade(api: Variant, endpoint: String,
		user_id: String) -> void:
	# The live side's pre-upgrade resources and its own row at the key, both
	# read from the corpus itself (this phase has already mutated it).
	api.configure("legacy_v0", endpoint)
	var live_before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(live_before != null,
		"the live corpus pre-upgrade resources resolve")
	var row_before: Variant = await _live_row(api, endpoint, user_id,
		UPGRADE_INDEX)
	check(row_before != null, "the live corpus pre-upgrade row resolves")
	if row_before == null:
		return

	var live_ref: Variant = await api.upgrade_building(user_id, UPGRADE_INDEX)
	check(live_ref is BootData.UpgradeResult,
		"live upgrade_building returns the typed result")
	if not (live_ref is BootData.UpgradeResult):
		return
	var live: BootData.UpgradeResult = live_ref
	check(live.ok, "live upgrade resolves over loopback: %s"
		% live.error_message)
	if not live.ok or live.removed == null or live.upgraded == null \
			or live.resources == null:
		return
	check_eq(live.protocol, BootData.PROTOCOL,
		"live upgrade protocol is compat-v0")
	check(live.game_version != "",
		"the live upgrade response carries the game version")
	check(live.server_time > 0,
		"live server_time is a positive wall-clock epoch (time-dependent)")
	check_eq(live.result, "success",
		"live upgrade reports the legacy success result")
	# `removed` is the row read BEFORE execution and `upgraded` the row
	# re-read from the save after it (design D5). The corpus's own pre-request
	# row is the reference, so the reused key and cell are compared against the
	# state the service actually held.
	var prior := row_before as Array
	check_eq(live.removed.item_id, int(prior[0]),
		"the live removed row names the corpus's own item")
	check_eq([live.removed.x, live.removed.y], [int(prior[1]), int(prior[2])],
		"the live removed row carries the corpus's own cell")
	check_eq(live.removed.player, int(prior[7]),
		"the live removed row keeps the player's team field")
	check_eq(live.upgraded.item_id, UPGRADE_TARGET,
		"the live upgraded row holds the derived target tier (Wall II)")
	check_eq([live.upgraded.x, live.upgraded.y], [int(prior[1]), int(prior[2])],
		"the live upgraded row sits at the pre-execution cell (the key is "
		+ "reused)")
	check_eq(live.upgraded.orientation, int(prior[4]),
		"the live upgraded row carries the row's own orientation")
	check_eq(live.upgraded.player, int(prior[7]),
		"the live upgraded row carries the row's own player field")
	check_eq(live.upgraded.store.size(), 0,
		"the live upgraded row's store is fresh and empty")
	check(live.upgraded.attr == {"nc": 0},
		"the live upgraded row carries the construction seed (live=%s)"
			% JSON.stringify(live.upgraded.attr))
	check(live.upgraded.timestamp > 0,
		"the live upgraded row is freshly stamped (time-dependent field, "
		+ "never asserted by value)")
	if live_before != null:
		# The derived vector is neutral, so an upgrade changes NO resource
		# (design D4) — and therefore claims no upgrade cost of any kind.
		for key in ["gold", "wood", "oil", "steel", "mana", "xp", "cash"]:
			check_eq(int(live.resources.get(key)), int(live_before.get(key)),
				"%s is untouched by the upgrade (neutral vector, design D4)"
					% key)
	# The key survives the pair: the corpus still names it, now holding the
	# new tier at the same cell (the row was replaced, not consumed).
	var row_after: Variant = await _live_row(api, endpoint, user_id,
		UPGRADE_INDEX)
	check(row_after != null, "the live corpus post-upgrade row resolves")
	if row_after != null:
		check_eq(int((row_after as Array)[0]), UPGRADE_TARGET,
			"the corpus still holds the upgraded tier at the same key")
		check_eq([int((row_after as Array)[1]), int((row_after as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not re-keyed)")

	# Fake reference: an independent in-memory state over the committed
	# upgrade-fixture before-state.
	api.configure("fake")
	var fake_ref: Variant = await api.upgrade_building(user_id, UPGRADE_INDEX)
	check(fake_ref is BootData.UpgradeResult,
		"fake upgrade_building returns the typed result")
	if not (fake_ref is BootData.UpgradeResult):
		return
	var fake: BootData.UpgradeResult = fake_ref
	check(fake.ok, "fake upgrade reference resolves: %s" % fake.error_message)
	if not fake.ok or fake.removed == null or fake.upgraded == null \
			or fake.resources == null:
		return
	check_eq(live.protocol, fake.protocol,
		"live upgrade protocol equals the fake's")
	check_eq(live.result, fake.result,
		"live upgrade result string equals the fake's")
	check_eq(live.removed.item_id, fake.removed.item_id,
		"live upgrade removed item id equals the fake's")
	check_eq([live.removed.x, live.removed.y],
		[fake.removed.x, fake.removed.y],
		"live upgrade removed cell equals the fake's")
	check_eq(live.upgraded.item_id, fake.upgraded.item_id,
		"live upgrade target tier equals the fake's")
	check_eq([live.upgraded.x, live.upgraded.y],
		[fake.upgraded.x, fake.upgraded.y],
		"live upgrade cell equals the fake's")
	check_eq(live.upgraded.orientation, fake.upgraded.orientation,
		"live upgrade orientation equals the fake's")
	check_eq(live.upgraded.player, fake.upgraded.player,
		"live upgrade player field equals the fake's")
	check_eq(live.upgraded.store.size(), fake.upgraded.store.size(),
		"live upgrade store equals the fake's")
	check(live.upgraded.attr == fake.upgraded.attr,
		"live upgrade attr equals the fake's (live=%s fake=%s)"
			% [JSON.stringify(live.upgraded.attr),
				JSON.stringify(fake.upgraded.attr)])
	# The fake's own side: the executed fixture's two-sided outcome, verbatim
	# (its fresh timestamp is the capture's recorded epoch, not the wall
	# clock, so it is asserted as the fixture's value the fake pins).
	check_eq(fake.removed.item_id, UPGRADE_ITEM,
		"the fake reproduces the fixture's pre-execution item")
	check_eq(fake.removed.timestamp, 0,
		"the fake never restamps the removed row's timestamp")
	check_eq(fake.upgraded.item_id, UPGRADE_TARGET,
		"the fake reproduces the fixture's upgraded tier")
	check_eq(fake.upgraded.x, UPGRADE_CELL.x, "the fake reuses the fixture's x")
	check_eq(fake.upgraded.y, UPGRADE_CELL.y, "the fake reuses the fixture's y")

	# A building with no resolvable next tier fails closed with the endpoint's
	# own code instead of becoming a bare sale (design D3).
	api.configure("legacy_v0", endpoint)
	var live_no_path: Variant = await api.upgrade_building(user_id,
		UPGRADE_NO_PATH_INDEX)
	check(live_no_path is BootData.UpgradeResult,
		"the live no-upgrade-path row returns the typed result")
	if live_no_path is BootData.UpgradeResult:
		var no_path: BootData.UpgradeResult = live_no_path
		check(not no_path.ok,
			"a row with no resolvable next tier is a structured failure")
		check_eq(no_path.error_code, "no_upgrade_path",
			"the live structured error passes through with the endpoint's code")
		check(no_path.removed == null and no_path.upgraded == null
			and no_path.resources == null,
			"the live no-upgrade-path failure carries no partial payload")
	var no_path_row: Variant = await _live_row(api, endpoint, user_id,
		UPGRADE_NO_PATH_INDEX)
	if no_path_row != null:
		check_eq(int((no_path_row as Array)[0]), UPGRADE_NO_PATH_ITEM,
			"the refused row is still on the map, unmolested")

	# Structured service errors pass through with their original codes, and
	# the fake derives the same codes for the same intents offline.
	var live_unknown: Variant = await api.upgrade_building(user_id,
		UPGRADE_UNKNOWN_INDEX)
	check(live_unknown is BootData.UpgradeResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.UpgradeResult:
		var unknown: BootData.UpgradeResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.removed == null and unknown.upgraded == null
			and unknown.resources == null,
			"the live structured failure carries no partial payload")
	api.configure("fake")
	var fake_unknown: Variant = await api.upgrade_building(user_id,
		UPGRADE_UNKNOWN_INDEX)
	check(fake_unknown is BootData.UpgradeResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.UpgradeResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	var fake_no_path: Variant = await api.upgrade_building(user_id,
		UPGRADE_NO_PATH_INDEX)
	check(fake_no_path is BootData.UpgradeResult and not fake_no_path.ok,
		"the fake fails the no-upgrade-path intent offline too")
	if fake_no_path is BootData.UpgradeResult:
		check_eq(fake_no_path.error_code, "no_upgrade_path",
			"the no-upgrade-path code matches between implementations")
	print("[test] live-upgrade applied item_index=%d cell=(%d, %d) tier=%d "
		% [UPGRADE_INDEX, live.upgraded.x, live.upgraded.y,
			live.upgraded.item_id]
		+ "xp=%d gold=%d" % [live.resources.xp, live.resources.gold])


## Construction through both implementations (task 3.3, spec "Construction
## through either implementation"): the three actions walked over ONE row, each
## asserted against the endpoint's OWN per-action post-condition — a start
## carries the derived countdown, a click carries a counter of at least one, a
## completion carries none — plus the reused key and cell, the two rows, the
## resolved action, and the neutral resource vector. The fake reference is
## compared on every stable field, so both implementations must answer the same
## typed shapes.
func _check_live_construction(api: Variant, endpoint: String,
		user_id: String) -> void:
	api.configure("legacy_v0", endpoint)
	var resources_before: BootData.Resources = await _live_resources(api,
		endpoint, user_id)
	check(resources_before != null,
		"the live corpus pre-construction resources resolve")
	var row_before: Variant = await _live_row(api, endpoint, user_id,
		CONSTRUCTION_INDEX)
	check(row_before != null, "the live corpus pre-construction row resolves")
	if row_before == null:
		return
	var prior := row_before as Array
	var started: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_START)
	check(started is BootData.ConstructionResult,
		"live build_construction returns the typed result")
	if not (started is BootData.ConstructionResult):
		return
	var first: BootData.ConstructionResult = started
	check(first.ok, "live construction start resolves over loopback: %s"
		% first.error_message)
	if not first.ok or first.previous == null or first.row == null \
			or first.resources == null:
		return
	check_eq(first.protocol, BootData.PROTOCOL,
		"live construction protocol is compat-v0")
	check(first.game_version != "",
		"the live construction response carries the game version")
	check(first.server_time > 0,
		"live server_time is a positive wall-clock epoch (time-dependent)")
	check_eq(first.result, "success",
		"live construction reports the legacy success result")
	check_eq(first.action, CONSTRUCTION_START,
		"the live start echoes the action it resolved")
	check_eq(first.previous.item_id, int(prior[0]),
		"the live previous row names the corpus's own item")
	check_eq([first.previous.x, first.previous.y], [int(prior[1]), int(prior[2])],
		"the live previous row carries the corpus's own cell")
	# The start reuses the same key and cell and records the derived countdown
	# server-side: no client value can influence it (design D2).
	check_eq(first.row.item_id, CONSTRUCTION_ITEM,
		"the live post-execution row keeps the row's own item")
	check_eq([first.row.x, first.row.y], [int(prior[1]), int(prior[2])],
		"the live post-execution row sits at the pre-execution cell (the key "
		+ "is reused)")
	check(first.row.timestamp > int(prior[3]),
		"the live post-execution row is freshly stamped (time-dependent field, "
		+ "never asserted by value)")
	var countdown: Variant = (first.row.attr as Dictionary).get("cp", null)
	check_eq(countdown, CONSTRUCTION_BUILD_TIME,
		"the live start recorded the item's committed build time as the "
		+ "countdown (the endpoint's own post-condition)")
	check(not (first.row.attr as Dictionary).has("nc"),
		"the live start wrote no click counter of its own")

	# --- the click: the counter is raised, the countdown is left alone.
	var clicked: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_CLICK)
	check(clicked is BootData.ConstructionResult and clicked.ok,
		"live construction click resolves over loopback")
	if not (clicked is BootData.ConstructionResult) or not clicked.ok:
		return
	var second: BootData.ConstructionResult = clicked
	check_eq(second.action, CONSTRUCTION_CLICK, "the live click echoes its action")
	var raised: Variant = (second.row.attr as Dictionary).get("nc", null)
	check(raised != null and int(raised) >= 1,
		"the live click recorded a counter of at least 1 (the endpoint's own "
		+ "post-condition)")
	check_eq((second.row.attr as Dictionary).get("cp", null),
		CONSTRUCTION_BUILD_TIME,
		"the live click left the recorded countdown alone")
	check_eq([second.row.x, second.row.y], [int(prior[1]), int(prior[2])],
		"the live click reused the very same cell")

	# --- the completion: the counter is consumed, the countdown survives.
	var finished: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, CONSTRUCTION_FINISH)
	check(finished is BootData.ConstructionResult and finished.ok,
		"live construction finish resolves over loopback")
	if not (finished is BootData.ConstructionResult) or not finished.ok:
		return
	var third: BootData.ConstructionResult = finished
	check_eq(third.action, CONSTRUCTION_FINISH,
		"the live completion echoes its action")
	check(not (third.row.attr as Dictionary).has("nc"),
		"the live completion consumed the click counter (the endpoint's own "
		+ "post-condition)")
	check_eq((third.row.attr as Dictionary).get("cp", null),
		CONSTRUCTION_BUILD_TIME,
		"the live completion left the recorded countdown alone")
	check_eq([third.row.x, third.row.y], [int(prior[1]), int(prior[2])],
		"the live completion reused the very same cell")
	check_eq(int(third.row.player), int(prior[7]),
		"the live completion kept the row's own player field")
	# The neutral vector changes no resource, so no building cost is claimed.
	if resources_before != null:
		for key in ["gold", "wood", "oil", "steel", "mana", "xp", "cash"]:
			check_eq(int(third.resources.get(key)), int(resources_before.get(key)),
				"%s is untouched by the construction (neutral vector, design D4)"
					% key)
	var row_after: Variant = await _live_row(api, endpoint, user_id,
		CONSTRUCTION_INDEX)
	check(row_after != null, "the live corpus post-construction row resolves")
	if row_after != null:
		check_eq([int((row_after as Array)[1]), int((row_after as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not re-keyed)")
		check_eq(int((row_after as Array)[0]), CONSTRUCTION_ITEM,
			"the corpus still holds the row's own item")

	# Fake reference: an independent in-memory state over the committed
	# construction-fixture before-state, walked through the same three steps.
	# Only the fields BOTH sides own are compared: this phase's live corpus has
	# already executed the move transaction, which repositions the very row
	# under construction, so the live row's cell is the CORPUS's own cell while
	# the fake's is its fixture's. Each side's cell is therefore compared
	# against its own pre-transaction state (asserted above for the live side)
	# and never against the other implementation's.
	api.configure("fake")
	for step in [CONSTRUCTION_START, CONSTRUCTION_CLICK, CONSTRUCTION_FINISH]:
		var fake: Variant = await api.build_construction(user_id,
			CONSTRUCTION_INDEX, str(step))
		check(fake is BootData.ConstructionResult and fake.ok,
			"fake construction %s resolves offline" % step)
		if not (fake is BootData.ConstructionResult) or not fake.ok:
			continue
		var typed: BootData.ConstructionResult = fake
		check_eq(typed.action, str(step),
			"the fake echoes the %s action too" % step)
		var live_result: BootData.ConstructionResult = null
		match str(step):
			CONSTRUCTION_START:
				live_result = first
			CONSTRUCTION_CLICK:
				live_result = second
			_:
				live_result = third
		var live_row: BootData.Placement = live_result.row
		check_eq(typed.row.item_id, live_row.item_id,
			"live and fake %s rows name the same item" % step)
		check_eq(typed.row.orientation, live_row.orientation,
			"live and fake %s rows carry the same orientation" % step)
		check_eq(typed.row.player, live_row.player,
			"live and fake %s rows carry the same player field" % step)
		check_eq(typed.previous.item_id, live_result.previous.item_id,
			"live and fake %s previous rows name the same item" % step)
		check_eq(typed.previous.attr, live_result.previous.attr,
			"live and fake %s previous rows carry the same attribute bag"
				% step)
		check(typed.row.timestamp > 0,
			"the fake's %s row carries the capture's recorded epoch (a "
			% step + "time-dependent field, never compared by value)")
		check_eq((typed.row.attr as Dictionary).get("cp", null),
			(live_row.attr as Dictionary).get("cp", null),
			"live and fake %s rows record the same countdown" % step)
		check_eq((typed.row.attr as Dictionary).get("nc", null),
			(live_row.attr as Dictionary).get("nc", null),
			"live and fake %s rows record the same click counter" % step)
		check_eq(typed.row.x, CONSTRUCTION_CELL.x,
			"the fake's %s row stays at the fixture's own cell" % step)

	# Structured service errors pass through with their original codes, and the
	# fake derives the same codes for the same intents offline.
	api.configure("legacy_v0", endpoint)
	var live_unknown: Variant = await api.build_construction(user_id,
		CONSTRUCTION_UNKNOWN_INDEX, CONSTRUCTION_START)
	check(live_unknown is BootData.ConstructionResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.ConstructionResult:
		var unknown: BootData.ConstructionResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.previous == null and unknown.row == null
			and unknown.resources == null,
			"the live structured failure carries no partial payload")
	var live_bad_action: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, "activate")
	check(live_bad_action is BootData.ConstructionResult
		and not live_bad_action.ok,
		"a legacy command name is never accepted by the endpoint")
	if live_bad_action is BootData.ConstructionResult:
		check_eq((live_bad_action as BootData.ConstructionResult).error_code,
			"invalid_action",
			"the live invalid action passes through with the endpoint's code")
	api.configure("fake")
	var fake_unknown: Variant = await api.build_construction(user_id,
		CONSTRUCTION_UNKNOWN_INDEX, CONSTRUCTION_START)
	check(fake_unknown is BootData.ConstructionResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.ConstructionResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	var fake_bad_action: Variant = await api.build_construction(user_id,
		CONSTRUCTION_INDEX, "add_click")
	check(fake_bad_action is BootData.ConstructionResult and not fake_bad_action.ok,
		"the fake refuses a legacy command name offline too")
	if fake_bad_action is BootData.ConstructionResult:
		check_eq(fake_bad_action.error_code, "invalid_action",
			"the invalid-action code matches between implementations")
	print("[test] live-construction applied item_index=%d cell=(%d, %d) "
		% [CONSTRUCTION_INDEX, third.row.x, third.row.y]
		+ "countdown=%d clicks_consumed=true xp=%d gold=%d" % [
			int((third.row.attr as Dictionary).get("cp", 0)),
			third.resources.xp, third.resources.gold])


## Collection through both implementations (task 3.3, spec "Collect through
## either implementation"): one collection over the corpus's own income row,
## asserted against the endpoint's OWN value-level post-state proof — the
## collection instant moved forward AND every stored resource changed by
## exactly the derived delta — plus the reused key and cell, both rows, the
## content-derived payout with its rung, the reference instant, and the
## two-layer construction-state refusal. The fake reference is compared on
## every stable field, so both implementations must answer the same typed
## shapes and the same derived payout.
func _check_live_collect(api: Variant, endpoint: String,
		user_id: String) -> void:
	api.configure("legacy_v0", endpoint)
	var before_row: Variant = await _live_row(api, endpoint, user_id,
		COLLECT_INDEX)
	var before_resources: BootData.Resources = await _live_resources(api,
		endpoint, user_id)
	check(before_row != null and before_resources != null,
		"the live corpus pre-collect row and balances resolve")
	if before_row == null or before_resources == null:
		return
	var prior := before_row as Array
	var collected: Variant = await api.collect_income(user_id, COLLECT_INDEX)
	check(collected is BootData.CollectResult,
		"live collect_income returns the typed result")
	if not (collected is BootData.CollectResult):
		return
	var typed: BootData.CollectResult = collected
	check(typed.ok, "live collection resolves over loopback: %s"
		% typed.error_message)
	if not typed.ok or typed.previous == null or typed.row == null \
			or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"live collect protocol is compat-v0")
	check(typed.game_version != "",
		"the live collect response carries the game version")
	check(typed.server_time > 0,
		"live collect server_time is a positive wall-clock epoch "
		+ "(time-dependent)")
	check_eq(typed.result, "success",
		"live collect reports the legacy success result")
	check_eq(typed.payout, COLLECT_PAYOUT,
		"the live derived payout is the documented eight-slot vector, matching "
		+ "the executed fixture's applied vector")
	check_eq(int(typed.payout[0]), 0,
		"the live derived payout's unread unknown slot is zero (D6)")
	check_eq(int(typed.payout[7]), 0,
		"the live derived payout's never-produced mana slot is zero (D6)")
	check_eq(int(typed.payout[1]), COLLECT_XP * COLLECT_TIER,
		"the live experience is the committed collect_xp scaled by the rung (D2)")
	check_eq(int(typed.payout[3]), COLLECT_AMOUNT * COLLECT_TIER,
		"the live wood is the committed collect scaled by the rung (D1)")
	check_eq(typed.tier, COLLECT_TIER,
		"the live payout came from the top committed rung (every corpus row "
		+ "records a never-collected instant of 0)")
	check(typed.reference_time > 0,
		"the live reference instant is a positive epoch")
	check(typed.reference_time >= typed.row.timestamp,
		"the live reference instant is not older than the instant it stamped")
	# The reused key and cell: a collection rewrites one row IN PLACE.
	check_eq(typed.previous.item_id, int(prior[0]),
		"the live previous row names the corpus's own item")
	check_eq([typed.previous.x, typed.previous.y], [int(prior[1]), int(prior[2])],
		"the live previous row carries the corpus's own cell")
	check_eq(typed.row.item_id, int(prior[0]),
		"the live post-execution row names the same item")
	check_eq([typed.row.x, typed.row.y], [int(prior[1]), int(prior[2])],
		"the live post-execution row reuses the same cell (the key is reused)")
	check(typed.row.timestamp > int(prior[3]),
		"the live post-execution row's collection instant moved forward "
		+ "(the endpoint's own post-condition)")
	check_eq(typed.row.attr, prior[6],
		"the live post-execution row carries the same attribute bag (a "
		+ "collection writes none)")
	check_eq(int(typed.row.player), int(prior[7]),
		"the live post-execution row keeps the row's own player field")
	# The endpoint's value-level post-state proof: every stored resource moved
	# by exactly the derived delta, so a reduced or diverging payout is
	# impossible (D8). This is the first delivered line whose proof checks a
	# VALUE the client would otherwise trust.
	check_eq(int(typed.resources.wood), before_resources.wood + 60,
		"the live wood balance is the corpus's own value plus the derived delta")
	check_eq(int(typed.resources.xp), before_resources.xp + 3,
		"the live experience is the corpus's own value plus the derived delta")
	for name in ["gold", "oil", "steel", "mana", "cash"]:
		check_eq(int(typed.resources.get(name)),
			int(before_resources.get(name)),
			"the live %s balance is untouched by the derived vector" % name)
	var after_row: Variant = await _live_row(api, endpoint, user_id,
		COLLECT_INDEX)
	check(after_row != null, "the live corpus post-collect row resolves")
	if after_row != null:
		check_eq([int((after_row as Array)[1]), int((after_row as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not "
			+ "re-keyed)")
		check_eq(int((after_row as Array)[0]), int(prior[0]),
			"the corpus still holds the row's own item")
		check_eq((after_row as Array)[6], prior[6],
			"the corpus row still carries the same attribute bag")
		check(int((after_row as Array)[3]) > int(prior[3]),
			"the corpus row's collection instant moved forward")
	# Fake reference: an independent in-memory state over the committed
	# collect-fixture before-state. Only the fields BOTH sides own are compared,
	# and each side's row is its own — this phase's live corpus has already
	# executed every earlier transaction, so the live row is the CORPUS's row
	# while the fake's is its fixture's.
	api.configure("fake")
	var fake: Variant = await api.collect_income(user_id, COLLECT_INDEX)
	check(fake is BootData.CollectResult and fake.ok,
		"fake collection resolves offline")
	if fake is BootData.CollectResult and fake.ok:
		var reference: BootData.CollectResult = fake
		check_eq(reference.payout, typed.payout,
			"live and fake derive the SAME content-derived payout")
		check_eq(reference.tier, typed.tier,
			"live and fake reach the SAME committed rung")
		check_eq(int(reference.payout[1]), int(typed.payout[1]),
			"live and fake scale the committed experience identically (D2)")
		check_eq(int(reference.payout[3]), int(typed.payout[3]),
			"live and fake scale the committed amount identically (D1)")
		check_eq(reference.row.item_id, typed.row.item_id,
			"live and fake rows name the same item")
		check_eq(reference.previous.item_id, typed.previous.item_id,
			"live and fake previous rows name the same item")
		check_eq(reference.row.orientation, typed.row.orientation,
			"live and fake rows carry the same orientation")
		check_eq(reference.row.player, typed.row.player,
			"live and fake rows carry the same player field")
		check_eq(_typed_attr(reference.row.attr), _typed_attr(typed.row.attr),
			"live and fake post-execution rows carry the same attribute bag")
		check(reference.row.timestamp > 0,
			"the fake's row carries the capture's recorded epoch (a "
			+ "time-dependent field, never compared by value)")
	# Structured service errors pass through with their original codes, and the
	# fake derives the same codes for the same intents offline.
	api.configure("legacy_v0", endpoint)
	var live_unknown: Variant = await api.collect_income(user_id,
		COLLECT_UNKNOWN_INDEX)
	check(live_unknown is BootData.CollectResult,
		"the live unknown index returns the typed result")
	if live_unknown is BootData.CollectResult:
		var unknown: BootData.CollectResult = live_unknown
		check(not unknown.ok,
			"an index the corpus does not name is a structured failure")
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
		check(unknown.previous == null and unknown.row == null
				and unknown.resources == null and unknown.payout == [],
			"the live structured failure carries no partial payload")
	# Design D5's two-layer rule, service half: the row this phase's own corpus
	# left under construction is refused BEFORE the dispatcher runs, so the
	# build's start instant and recorded countdown are byte-identical
	# afterwards — the corruption probe 2 showed legacy permits.
	var built_before: Variant = await _live_row(api, endpoint, user_id,
		COLLECT_BUILT_INDEX)
	if built_before is Array and (built_before as Array).size() == 8:
		var refused: Variant = await api.collect_income(user_id,
			COLLECT_BUILT_INDEX)
		check(refused is BootData.CollectResult and not refused.ok,
			"a collection on a row under construction is refused")
		if refused is BootData.CollectResult:
			check_eq(refused.error_code, "construction_in_progress",
				"the refusal is the service's own two-layer guard: %s"
					% refused.error_message)
		var built_after: Variant = await _live_row(api, endpoint, user_id,
			COLLECT_BUILT_INDEX)
		check(built_after != null
				and (built_after as Array)[6] == (built_before as Array)[6],
			"the refused row's recorded countdown survives untouched")
		check(built_after != null
				and int((built_after as Array)[3])
				== int((built_before as Array)[3]),
			"the refused row's START INSTANT survives untouched: the delivered "
			+ "construction countdown is not silently restarted")
	api.configure("fake")
	var fake_unknown: Variant = await api.collect_income(user_id,
		COLLECT_UNKNOWN_INDEX)
	check(fake_unknown is BootData.CollectResult and not fake_unknown.ok,
		"fake fails the same intent offline")
	if fake_unknown is BootData.CollectResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	api.configure("legacy_v0", endpoint)
	print("[test] live-collect applied item_index=%d cell=(%d, %d) tier=%d "
		% [COLLECT_INDEX, typed.row.x, typed.row.y, typed.tier]
		+ "payout=%s wood=%d xp=%d" % [JSON.stringify(typed.payout),
			typed.resources.wood, typed.resources.xp])


## Expansion through both implementations (building-expand tasks 3.1/3.3,
## design D8): the same typed shape from both, the content-derived DEBIT over
## the same committed schedule, the two guards the executed-legacy probe showed
## the legacy server lacks (an out-of-range id, a duplicate, and a negative id
## all answered success there) passing through with their own codes, and each
## side's ledger and balances checked against ITS OWN pre-request state.
##
## The live side runs LAST in this suite, so its corpus already carries every
## earlier transaction; the honest parity claim is the one the contract makes:
## both implementations produce the same typed shape and the same
## content-derived debit for the same id, and the live side's own two-part
## post-state proof is asserted against the corpus's own pre-request ledger and
## balances.
func _check_live_expand(api: Variant, endpoint: String,
		user_id: String) -> void:
	api.configure("legacy_v0", endpoint)
	var ledger_before: Array = await _live_ledger(api, endpoint, user_id)
	var balances_before: BootData.Resources = await _live_resources(api,
		endpoint, user_id)
	check(ledger_before.size() == 4 and balances_before != null,
		"the live corpus pre-expand ledger and balances resolve")
	if balances_before == null:
		return
	# The guards the executed-legacy probe showed the legacy server lacks, plus
	# the two content refusals: all of them are answered with the endpoint's own
	# code and carry NO partial payload, and each leaves the corpus
	# byte-identical.
	for entry: Array in [[EXPAND_DUPLICATE_ID, "already_expanded"],
			[EXPAND_BLOCKED_ID, "expansion_requirements_unmet"],
			[EXPAND_OUT_OF_RANGE_ID, "unknown_expansion_id"],
			[EXPAND_NEGATIVE_ID, "invalid_expansion_id"]]:
		var refused: Variant = await api.expand_town(user_id, int(entry[0]))
		check(refused is BootData.ExpandResult,
			"the live refusal for id %d returns the typed result" % int(entry[0]))
		if refused is BootData.ExpandResult:
			var failure: BootData.ExpandResult = refused
			check(not failure.ok,
				"the live expansion of id %d is refused" % int(entry[0]))
			check_eq(failure.error_code, str(entry[1]),
				"the live refusal for id %d is the service's own code: %s"
					% [int(entry[0]), failure.error_message])
			check(failure.expansions_before.is_empty()
					and failure.expansions_after.is_empty()
					and failure.debit.is_empty() and failure.price == null
					and failure.resources == null,
				"the live refused expansion carries no partial payload")
		check_eq(await _live_ledger(api, endpoint, user_id), ledger_before,
			"the live refused expansion id %d left the corpus ledger "
				% int(entry[0]) + "byte-identical")
		var after_refusal: BootData.Resources = await _live_resources(api,
			endpoint, user_id)
		check(after_refusal != null
				and _same_resources(after_refusal, balances_before),
			"the live refused expansion id %d left every corpus balance "
				% int(entry[0]) + "byte-identical")
	var expanded: Variant = await api.expand_town(user_id, EXPAND_ID)
	check(expanded is BootData.ExpandResult,
		"live expand_town returns the typed result")
	if not (expanded is BootData.ExpandResult):
		return
	var typed: BootData.ExpandResult = expanded
	_check_live_expand_result(typed, ledger_before, balances_before)
	# The service half of the post-state proof, read from the service's own
	# state rather than from the response.
	var expected: Array = ledger_before.duplicate()
	expected.append(EXPAND_ID)
	check_eq(await _live_ledger(api, endpoint, user_id), expected,
		"the live corpus ledger grew by exactly the sent id at the end, with "
		+ "every existing entry unchanged and in order")
	var after: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(after != null and _same_resources(after, balances_before),
		"every live corpus balance is unchanged, because the committed row for "
		+ "the addressed id is free and the derived debit is the all-zero vector")
	# Fake reference: an independent in-memory state over the committed expand
	# fixture's before-state. The typed shape and the derived debit must match
	# the live side's exactly.
	api.configure("fake")
	var fake: Variant = await api.expand_town(user_id, EXPAND_ID)
	check(fake is BootData.ExpandResult and fake.ok,
		"fake expansion resolves offline")
	if fake is BootData.ExpandResult and fake.ok:
		var reference: BootData.ExpandResult = fake
		check_eq(reference.protocol, typed.protocol,
			"live and fake expand protocols agree")
		check_eq(reference.result, typed.result,
			"live and fake expand report the same legacy result")
		check_eq(reference.debit, typed.debit,
			"live and fake derive the SAME content-derived debit for the same "
			+ "committed id (design D2)")
		check_eq(reference.expansions_before, EXPAND_OWNED,
			"the fake's pre-execution ledger is the committed fixture's own")
		check_eq(reference.expansions_after, [35, 36, 45, 46, 0],
			"the fake appends the sent id once at the end, exactly as the "
			+ "executed fixture records")
		check_eq([reference.price.coins, reference.price.cash,
			reference.price.neighbors, reference.price.inventory_qte],
			[0, 0, 0, 0],
			"the fake prices the free row from its OWN loaded configuration")
	api.configure("legacy_v0", endpoint)
	var ledger: Array = typed.expansions_after
	print("[test] live-expand applied expansion_id=%d ledger=%s debit=%s "
		% [EXPAND_ID, JSON.stringify(ledger), JSON.stringify(typed.debit)]
		+ "gold=%d cash=%d" % [typed.resources.gold, typed.resources.cash])


## Level up through both implementations (spec "Level up through either
## implementation"): the committed corpus's own already-consistent level-up,
## answered by the real endpoint with its own `level_already_current` code and
## NO partial payload, and leaving the corpus byte-identical; plus the fake's
## identical refusal offline, so both implementations yield the same typed
## shapes for the same intent.
##
## **A successful live level-up is NOT reachable from the committed corpus** and
## none is claimed: at `xp 4` the committed curve derives level 1 and the save
## records level 1, so the endpoint answers before the dispatcher runs. The
## POSITIVE half of the two-part post-execution proof (the recorded level moved
## to exactly the derived level AND every stored resource unchanged) is covered
## hermetically by `test_town_xp.gd` and `test_game_api_fake.gd` over an
## in-memory disagreement. Nothing here fabricates a corpus mutation.
func _check_live_level(api: Variant, endpoint: String, user_id: String) -> void:
	api.configure("legacy_v0", endpoint)
	var before: BootData.Resources = await _live_resources(api, endpoint,
		user_id)
	check(before != null, "the live corpus pre-level balances resolve")
	if before == null:
		return
	var level_before := await _live_level(api, endpoint, user_id)
	check_eq(level_before, LEVEL_CORPUS_LEVEL,
		"the live corpus records level 1 (or whatever the collected run left; "
			+ "the committed corpus starts at 1)")
	var refused: Variant = await api.level_up_town(user_id)
	check(refused is BootData.LevelUpResult,
		"live level_up_town returns the typed result")
	if not (refused is BootData.LevelUpResult):
		return
	var failure: BootData.LevelUpResult = refused
	check(not failure.ok,
		"the live level-up of the already-consistent corpus is refused")
	check_eq(failure.error_code, "level_already_current",
		"the live refusal is the SERVICE's own code: %s" % failure.error_message)
	check(failure.curve == null and failure.resources == null
			and failure.result == "" and failure.derived_level == -1
			and failure.level_before == -1 and failure.level_after == -1,
		"the live refused level-up carries NO partial payload")
	var after: BootData.Resources = await _live_resources(api, endpoint, user_id)
	check(after != null and _same_resources(after, before),
		"every live corpus balance is unchanged, because a level change moves "
			+ "no resource and the dispatcher never ran")
	check_eq(await _live_level(api, endpoint, user_id), level_before,
		"the live refused level-up left the recorded level byte-identical")
	# The save-identity codes pass through with their original codes, exactly as
	# every other endpoint's do.
	var missing: Variant = await api.level_up_town("")
	check(missing is BootData.LevelUpResult and not missing.ok,
		"an empty save id is refused over loopback")
	if missing is BootData.LevelUpResult:
		check_eq(missing.error_code, "missing_user_id",
			"the live missing-save-id code matches the fake's")
	var unknown: Variant = await api.level_up_town(UNKNOWN_USER)
	check(unknown is BootData.LevelUpResult and not unknown.ok,
		"an unknown save id is refused over loopback")
	if unknown is BootData.LevelUpResult:
		check_eq(unknown.error_code, "unknown_user_id",
			"the live unknown-save-id code matches the fake's")
	# Fake reference: the same intent, the same refusal, offline.
	api.configure("fake")
	var fake: Variant = await api.level_up_town(user_id)
	check(fake is BootData.LevelUpResult and not fake.ok,
		"the fake refuses the same live intent offline")
	if fake is BootData.LevelUpResult and failure is BootData.LevelUpResult:
		var reference: BootData.LevelUpResult = fake
		check_eq(reference.error_code, failure.error_code,
			"live and fake level-up report the SAME structured code for the "
				+ "same intent (design D4)")
	api.configure("legacy_v0", endpoint)
	print("[test] live-level-up applied level=%d derived=%d xp=%d "
		% [level_before, level_before, int(before.xp)]
		+ "refused=level_already_current resources_unchanged=true")


## The corpus's own recorded level, read from its bootstrap payload.
func _live_level(api: Variant, endpoint: String, user_id: String) -> int:
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not boot.ok:
		return -99
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		return -99
	var map: Dictionary = ((info as BootData.PlayerInfoPayload).raw).get(
		"map", {}) as Dictionary
	return int(map.get("level", -99))


## True when two typed `BootData.Resources` carry the same seven stored values.
func _same_resources(a: BootData.Resources, b: BootData.Resources) -> bool:	return a.xp == b.xp and a.gold == b.gold and a.wood == b.wood \
		and a.oil == b.oil and a.steel == b.steel and a.cash == b.cash \
		and a.mana == b.mana


## One live expansion's typed response and its TWO-part value-level
## post-execution proof, compared against the corpus's own pre-request ledger
## and balances.
func _check_live_expand_result(typed: BootData.ExpandResult, prior: Array,
		before: BootData.Resources) -> void:
	check(typed.ok, "the live expansion resolves over loopback: %s / %s"
		% [typed.error_code, typed.error_message])
	if not typed.ok or typed.resources == null or typed.price == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live expand protocol is compat-v0")
	check(typed.game_version != "",
		"the live expand response carries the game version")
	check(typed.server_time > 0,
		"the live expand server_time is a positive wall-clock epoch "
		+ "(time-dependent, never asserted by value)")
	check_eq(typed.result, "success",
		"the live expand reports the legacy success result")
	# Proof part one (structural): the ledger grew by exactly the sent id, at
	# the end, with every existing entry unchanged and in order.
	var expected: Array = prior.duplicate()
	expected.append(EXPAND_ID)
	check_eq(typed.expansions_before, prior,
		"the live pre-execution ledger is the corpus's own, in the save's order")
	check_eq(typed.expansions_after, expected,
		"the live post-execution ledger is the sent id appended ONCE at the end "
		+ "(the endpoint's own structural proof)")
	check_eq(typed.expansions_after.size(),
		typed.expansions_before.size() + 1,
		"the live ledger grew by exactly one entry")
	# The committed row, carried verbatim.
	check_eq([typed.price.coins, typed.price.cash, typed.price.neighbors,
		typed.price.inventory_qte], [0, 0, 0, 0],
		"the live committed price row is the free row's, verbatim")
	# Proof part two (value-level): every stored resource changed by EXACTLY the
	# derived debit. The addressed row is free, so the derived debit is the
	# all-zero vector and EVERY balance must be unchanged — the strictest form
	# of the proof, because a wrong derived price would move one.
	check_eq(typed.debit.size(), BootData.EXPAND_VECTOR_SLOTS,
		"the live derived debit is the documented eight-slot vector")
	for index: int in BootData.EXPAND_ALWAYS_ZERO_SLOTS:
		check_eq(int(typed.debit[index]), 0,
			"the live derived debit's slot %d stays zero" % index)
	check(_same_resources(typed.resources, before),
		"every live stored resource equals the corpus's own pre-request value "
		+ "(the endpoint's value-level post-execution proof): %s"
			% JSON.stringify({"before": {"xp": before.xp, "gold": before.gold,
				"wood": before.wood, "oil": before.oil,
				"steel": before.steel, "cash": before.cash,
				"mana": before.mana},
				"after": {"xp": typed.resources.xp, "gold": typed.resources.gold,
				"wood": typed.resources.wood, "oil": typed.resources.oil,
				"steel": typed.resources.steel, "cash": typed.resources.cash,
				"mana": typed.resources.mana}}))


## The corpus's own owned-expansions ledger, read from its bootstrap payload
## under the typed int names, or [] when the payload carries none. This is the
## pre-request reference the live expansion's appended id is compared against —
## read from the service's own state, never from the fake's fixture.
func _live_ledger(api: Variant, endpoint: String, user_id: String) -> Array:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus ledger bootstrap resolves")
		return []
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus ledger payload is readable")
		return []
	var raw: Dictionary = (info as BootData.PlayerInfoPayload).raw
	var owned: Variant = (raw.get("map", {}) as Dictionary).get("expansions",
		[])
	if not (owned is Array):
		return []
	var ids: Array = []
	for entry: Variant in (owned as Array):
		ids.append(int(entry))
	return ids


## One recorded attribute bag in the canonical typed form (the JSON transport
## widens the save's ints to floats on the pinned engine), so two
## implementations' bags compare field for field.
func _typed_attr(value: Variant) -> Dictionary:
	var out := {}
	if not (value is Dictionary):
		return out
	for key: Variant in (value as Dictionary):
		var amount: Variant = (value as Dictionary)[key]
		out[str(key)] = int(amount) if (amount is int or amount is float) \
			else amount
	return out


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


## The corpus's own storage mapping, in the typed `{str(item_id): int}` form
## the purchase, bootstrap, and store responses all carry. This is the
## pre-store reference the live store's FULL mapping is compared against —
## read from the corpus itself, never from the fake's fixture, because the
## live side has already executed the placement, purchase, move, and sell
## transactions in this phase. Null when the corpus cannot be read, so the
## caller states that limit instead of guessing.
func _live_storage(api: Variant, endpoint: String,
		user_id: String) -> Variant:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus pre-store bootstrap resolves")
		return null
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus pre-store payload is readable")
		return null
	var raw: Dictionary = (info as BootData.PlayerInfoPayload).raw
	var map: Variant = raw.get("map", {})
	if not (map is Dictionary):
		check(false, "the live corpus pre-store payload carries a map")
		return null
	var store: Variant = (map as Dictionary).get("store", {})
	if not (store is Dictionary):
		check(false, "the live corpus pre-store payload carries a storage map")
		return null
	var typed := {}
	for key: Variant in (store as Dictionary):
		typed[str(key)] = int((store as Dictionary)[key])
	return typed
