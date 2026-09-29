extends "res://tests/test_base.gd"
## Collect suite (building-collect, spec "Collection flow" / "Collect through
## either implementation").
##
## Scenarios:
##   helpers     the pure helpers (the committed ladder and its minutes-to-
##               seconds conversion, the reached rung, the next rung's
##               countdown, the derived payout, the refusals, the readout) over
##               every rung — each boundary from BOTH sides — and every refusal,
##               with an explicit reference instant and no node, request, or
##               clock;
##   gating      the selection-driven surface offers a `Collect` action beside
##               the delivered `Move`, `Sell`, `Store`, `Upgrade`, and `Build`
##               actions, only for a selected, ADDRESSABLE placed building whose
##               item resolves committed income AND whose row has reached a
##               committed rung, and pressing it arms the collection in the SAME
##               UI-foundation slot the other five modes use (design D8 — no
##               seventh panel, no grid target, no preview), and none of the five
##               delivered modes' behavior changes;
##   readout     the collection readout renders for every income state (never
##               collected, the top rung, and a just-collected row with no rung
##               reached) and is EMPTY for a row whose item records no committed
##               income;
##   refusals    a building with no committed income, a row that has reached no
##               committed rung, a row under construction, a row whose committed
##               cap is unusable, an unaddressable legacy key, and a row whose
##               attribute bag is not an object are each refused by name with NO
##               request, the six modes never stack, and a selection that no
##               longer names the armed building refuses the confirm instead of
##               silently re-targeting it;
##   cancel      a cancelled collection sends nothing and leaves the town, the
##               row's collection instant, both readouts, the storage view, and
##               the resources byte-identical;
##   apply       one confirmed intent applies ONLY the authoritative response:
##               the SAME rendered object retained in depth order, the typed row
##               replaced by the response's post-execution row, the typed
##               collection clock re-read through the shared parser, and the
##               balances and experience taken from the response — with BOTH
##               counts unchanged, because the key is reused;
##   failures    an index the service does not know (`unknown_item_index`) and a
##               transport failure (the refused loopback endpoint) each surface
##               their code with the row keeping its previous collection instant
##               and the HUD unchanged;
##   no-request  the whole run issues no bootstrap request (the state derives
##               from the fixture in hand and the flow never re-bootstraps).
##
## Uses the committed bootstrap and collect fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-collect` run is the `collect-live`
## phase: one collection against the real Compatibility endpoint, its
## value-level post-state proof, and the two-layer construction-state refusal.
##
## **The resource-type refusal is not exercised through the view.** The
## committed content package records only the five committed `collect_type`
## values (`g`, `w`, `o`, `s`, `c` for 471 of 471 stored items), so no placed
## row can make the client refuse a type; the rule is covered where it IS
## reachable — at the pure-helper level, and in the fake-double suite, which
## stubs the config accessor the way the compat suite does.

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const MoveFlow = preload("res://scripts/town/move_flow.gd")
const CollectionFlow = preload("res://scripts/town/collection_flow.gd")
const ConstructionFlow = preload("res://scripts/town/construction_flow.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"

## The executed-legacy transaction this suite reproduces (fixture facts,
## recorded against the committed collect capture): the Tree, item 905, 1x1, at
## legacy map key "2" — its cell `(53,39)`, the row
## `[905, 53, 39, 0, 0, [], {}, 1]` — has ONLY its collection instant
## re-stamped, and the derived payout `[0, 3, 0, 60, 0, 0, 0, 0]` (3 xp, 60
## wood) lands in exactly two resource slots. The placement count stays 40, the
## key and cell are reused, the storage stays empty, and the other five
## resources are unchanged.
const INCOME_ITEM := 905
const INCOME_SLOT := 2
const INCOME_CELL := Vector2i(53, 39)
const INCOME_ROW := [INCOME_ITEM, 53, 39, 0, 0, [], {}, 1]
const INCOME_AMOUNT := 20
const INCOME_XP := 1
const INCOME_PAYOUT := [0, 3, 0, 60, 0, 0, 0, 0]
const PLACEMENTS := 40
## The fresh save's own resource values the applied payout moves.
const FRESH_XP := 4
const FRESH_WOOD := 2000
const FRESH_GOLD := 2000
const FRESH_CASH := 5
## A second, still-present addressable building used for the mutual-exclusion,
## refusal, and construction-state scenarios: the Turret I at legacy key 11,
## cell (58,48). Its item records NO committed income (`collect 0`), so it is
## also the row every no-income refusal is proved on.
const SPARE_CELL := Vector2i(58, 48)
const SPARE_SLOT := 11
const SPARE_ITEM := 22
## A real committed item whose income is capped: the Stoneage records
## `collect 1800`, `collect_type "s"`, `collect_xp 20`, and a NON-ZERO
## `max_collects 25`. Its cap semantics are unobserved, so the flow refuses the
## row by name (design D4). No placed corpus row names it, so the suite crafts
## one in memory.
const CAPPED_ITEM := 66
## An index neither the corpus nor the double knows (a stale client state after
## the row was renumbered, or a row the save never carried).
const UNKNOWN_INDEX := 9999
## The cell the crafted-row scenarios park their rows at.
const GHOST_CELL := Vector2i(20, 20)
## The addressable keys the crafted-row refusals use, kept distinct so the
## snapshot assertions can name the row they mean.
const CAPPED_SLOT := 66
const COUNTDOWN_SLOT := 91
const COUNTER_SLOT := 92
const TRANSPORT_SLOT := 97
## A fixed reference instant for the pure helpers' ladder derivations (the
## module takes the instant as a parameter and reads no clock). Chosen so the
## elapsed time from a never-collected row (`collected_at == 0`) is far beyond
## the top rung, which is the corpus's own situation.
const REFERENCE := 1790690600

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
	if scenario == "live-collect":
		# verify-boot's collect-live phase: one collection through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response, its
		# value-level post-state proof, and that a refused collection left a
		# construction's timers untouched. Everything else here is
		# fixture-fake only.
		await _check_live_collect()
		return
	_check_pure_helpers()
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	await _check_flow(payload)
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# Pure helpers (task 4.2, design D9)
# ---------------------------------------------------------------------------


## The pure helpers over every rung the ladder can reach and every refusal the
## flow can name, with an explicit reference instant. Nothing here touches a
## node, a request, or a clock: the same inputs always produce the same rung,
## countdown, payout, refusal, and readout.
func _check_pure_helpers() -> void:
	# The committed ladder, and the ONE place its unit is converted. The
	# thresholds are MINUTES; both instants are Unix SECONDS (design D1/D3).
	check_eq(CollectionFlow.ladder_minutes(), [5, 60, 240, 480],
		"the committed thresholds are the committed minutes")
	check_eq(CollectionFlow.ladder_multipliers(), [0.25, 1.0, 2.0, 3.0],
		"the committed multipliers are the committed ladder's")
	check_eq(CollectionFlow.SECONDS_PER_COMMITTED_MINUTE, 60,
		"the ladder's unit conversion is one named constant")
	check_eq(CollectionFlow.ladder_size(), 4,
		"the committed ladder has four rungs")
	check_eq(CollectionFlow.NO_TIER, -1,
		"'no rung reached' is a sentinel that is never rung 0")
	# Every boundary from BOTH sides. The unit bug this guards against is a
	# comparison of minutes against Unix seconds, which would pay the TOP rung
	# within five seconds.
	for entry in [[299, CollectionFlow.NO_TIER], [300, 0], [3599, 0],
			[3600, 1], [14399, 1], [14400, 2], [28799, 2], [28800, 3]]:
		var elapsed := int(entry[0])
		check_eq(CollectionFlow.reached_tier(elapsed), int(entry[1]),
			"%d s reaches rung %d" % [elapsed, int(entry[1])])
	check_eq(CollectionFlow.reached_tier(28801), 3,
		"an elapsed time past the top rung stays at the top rung (clamped, "
		+ "never extrapolated)")
	check_eq(CollectionFlow.reached_tier(99999999), 3,
		"an unbounded elapsed time reaches the top rung, which is why every "
		+ "corpus row (item[3] == 0) collects at the top rung")
	check_eq(CollectionFlow.reached_tier(-1), CollectionFlow.NO_TIER,
		"a recorded instant ahead of the reference reaches no rung")
	check_eq(CollectionFlow.threshold_seconds(0), 300,
		"the first committed threshold is 5 minutes in seconds")
	check_eq(CollectionFlow.threshold_seconds(1), 3600,
		"the second committed threshold is 60 minutes in seconds")
	check_eq(CollectionFlow.threshold_seconds(2), 14400,
		"the third committed threshold is 240 minutes in seconds")
	check_eq(CollectionFlow.threshold_seconds(3), 28800,
		"the fourth committed threshold is 480 minutes in seconds")
	check_eq(CollectionFlow.threshold_minutes(3), 480,
		"the top rung's committed threshold is reported in minutes too")
	check_eq(CollectionFlow.threshold_seconds(4), 0,
		"a rung outside the committed ladder is refused, not extrapolated")
	check_eq(CollectionFlow.threshold_minutes(9), 0,
		"a rung outside the committed ladder has no committed minutes either")

	# The next-rung countdown: `threshold(next) - elapsed`, clamped at zero,
	# and null at the top rung because there is no further rung. A row that has
	# reached NO rung at all waits for the FIRST one.
	check_eq(CollectionFlow.next_rung_remaining_seconds(3, 40000), null,
		"the top rung has no further rung to wait for")
	check_eq(CollectionFlow.next_rung_remaining_seconds(
		CollectionFlow.NO_TIER, 0), 300,
		"a row that has reached nothing waits for the first rung")
	check_eq(CollectionFlow.next_rung_remaining_seconds(
		CollectionFlow.NO_TIER, 299), 1,
		"one second short of the first rung waits exactly one second")
	check_eq(CollectionFlow.next_rung_remaining_seconds(0, 300), 3300,
		"a row that has just reached rung 0 waits for rung 1")
	check_eq(CollectionFlow.next_rung_remaining_seconds(1, 3600), 10800,
		"a row that has just reached rung 1 waits for rung 2")
	check_eq(CollectionFlow.next_rung_remaining_seconds(2, 14400), 14400,
		"a row that has just reached rung 2 waits the whole of rung 3")
	check_eq(CollectionFlow.next_rung_remaining_seconds(1, 99999), 0,
		"an elapsed time past the next rung waits zero seconds, never "
		+ "negative")

	# The derived payout at every rung, from the committed income fields. The
	# Tree's 20 wood and 1 xp at the quarter rung are the rounding case: 0.25 x
	# 1 rounds half-up to 0 experience.
	var income := CollectionFlow.income_of(INCOME_AMOUNT, "w", INCOME_XP, 0)
	check(bool(income.get("ok", false)),
		"the committed income resolves: %s" % income.get("error"))
	for entry in [[0, [0, 0, 0, 5, 0, 0, 0, 0]],
			[1, [0, 1, 0, 20, 0, 0, 0, 0]],
			[2, [0, 2, 0, 40, 0, 0, 0, 0]],
			[3, INCOME_PAYOUT]]:
		var payout: Variant = CollectionFlow.payout_for(income, int(entry[0]))
		check_eq(payout, entry[1],
			"rung %d pays the committed amount scaled by its multiplier"
				% int(entry[0]))
	# The unread `unknown` slot 0 and the never-produced `mana` slot 7 are
	# always zero (design D6), at every rung.
	for tier in 4:
		var vector: Array = CollectionFlow.payout_for(income, tier)
		check_eq(int(vector[0]), 0,
			"the unread unknown slot stays zero at rung %d" % tier)
		check_eq(int(vector[7]), 0,
			"the never-produced mana slot stays zero at rung %d" % tier)
	# Every committed resource type maps onto its own slot, and nothing else.
	for entry in [["g", 2, "gold"], ["w", 3, "wood"], ["o", 4, "oil"],
			["s", 5, "steel"], ["c", 6, "cash"]]:
		var typed := CollectionFlow.income_of(INCOME_AMOUNT, str(entry[0]),
			0, 0)
		var mapped: Variant = CollectionFlow.payout_for(typed, 3)
		check_eq(int(mapped[0]), 0,
			"a %s payout leaves the unknown slot zero" % str(entry[0]))
		check_eq(int(mapped[int(entry[1])]), 60,
			"a %s payout lands 60 of its own resource in its own slot"
				% str(entry[0]))
		check_eq(CollectionFlow.vector_resource_name(mapped), str(entry[2]),
			"a %s payout names the %s it pays" % [str(entry[0]), str(entry[2])])
	# A type outside the committed set is refused rather than coerced, and a
	# non-zero cap is refused rather than interpreted (design D4/D6).
	var unmappable := CollectionFlow.income_of(INCOME_AMOUNT, "m", 0, 0)
	check(not bool(unmappable.get("ok", true)),
		"a collection type outside the committed set is refused")
	check(bool(unmappable.get("unknown_type", false)),
		"the refused type is named as an unknown type")
	check(CollectionFlow.payout_for(unmappable, 3) == null,
		"a refused type derives no payout at all")
	var capped := CollectionFlow.income_of(INCOME_AMOUNT, "w", 0, 25)
	check(not bool(capped.get("ok", true)),
		"a non-zero committed cap is refused")
	check(bool(capped.get("capped", false)),
		"the refused cap is named as a cap")
	check(CollectionFlow.payout_for(capped, 3) == null,
		"a refused cap derives no payout at all")
	var negative := CollectionFlow.income_of(-1, "w", 0, 0)
	check(not bool(negative.get("ok", true)),
		"a negative committed amount is refused rather than paid")
	check(CollectionFlow.payout_for({"resource_type": "w"}, 9) == null,
		"a rung outside the committed ladder derives no payout")

	# The payout text the confirm names.
	check_eq(CollectionFlow.payout_text(INCOME_PAYOUT), "60 wood, 3 xp",
		"the top-rung payout reads as the derived amount and resource")
	check_eq(CollectionFlow.payout_text([0, 0, 0, 5, 0, 0, 0, 0]),
		"5 wood, 0 xp",
		"the quarter rung's payout rounds the experience to zero")
	check_eq(CollectionFlow.payout_text([0, 1, 0, 0, 0, 0, 0, 0]), "1 xp",
		"a gold-only payout names only the experience")
	check_eq(CollectionFlow.payout_text([0, 0, 0, 0, 0, 0, 0, 0]), "0 xp",
		"an empty vector still names the experience slot it carries")
	check_eq(CollectionFlow.collect_label(), "Collect",
		"the action's own label names the exact intent it sends")

	# The ladder record the report publishes: every rung with BOTH units.
	var record := CollectionFlow.ladder_record()
	check_eq(record.size(), 4, "the ladder record has one row per committed rung")
	check_eq([int(record[0]["minutes"]), int(record[0]["seconds"])], [5, 300],
		"the first rung is recorded in minutes and in seconds")
	check_eq([int(record[3]["minutes"]), int(record[3]["seconds"])],
		[480, 28800], "the top rung is recorded in minutes and in seconds")
	check_eq(float(record[0]["multiplier"]), 0.25,
		"the first rung's committed multiplier is the quarter")

	# The refusals name their own condition, and an evaluation that offers a
	# collection never produces refusal text.
	var refused: Dictionary = CollectionFlow.evaluate(null, null, {}, REFERENCE)
	check(not bool(refused.get("ok", true)),
		"no selected placement is refused structurally")
	check_eq(str(refused.get("reason", "")),
		CollectionFlow.REASON_NO_SELECTION,
		"the structural refusal names the no-selection condition")
	check_eq(CollectionFlow.refusal_text(refused), "",
		"a structural refusal produces no player-facing text (it is an error)")
	check_eq(CollectionFlow.refusal_text({"ok": true, "reason": "",
		"payout": INCOME_PAYOUT}), "",
		"an offered collection produces no refusal text")
	for reason in [CollectionFlow.REASON_UNADDRESSABLE,
			CollectionFlow.REASON_UNREADABLE_STATE,
			CollectionFlow.REASON_NO_INCOME, CollectionFlow.REASON_CAPPED,
			CollectionFlow.REASON_UNKNOWN_TYPE,
			CollectionFlow.REASON_CONSTRUCTION_IN_PROGRESS,
			CollectionFlow.REASON_TOO_EARLY]:
		var text := CollectionFlow.refusal_text({"ok": true, "reason": reason,
			"item": INCOME_ITEM, "has_income": true})
		check(text != "" and text.contains(str(INCOME_ITEM)),
			"the '%s' refusal names the building: %s" % [reason, text])

	# The readout, over the states a row can be in. Pure, and derived in every
	# part.
	var never := CollectionFlow.readout_text({"ok": true, "has_income": true,
		"item": INCOME_ITEM, "tier": CollectionFlow.NO_TIER,
		"next_remaining_seconds": 300})
	check(never.contains("item %d" % INCOME_ITEM)
			and never.contains("no committed rung reached")
			and never.contains("300 s"),
		"a never-collected readout names the row, the missing rung, and the "
		+ "countdown to the first: %s" % never)
	var top := CollectionFlow.readout_text({"ok": true, "has_income": true,
		"item": INCOME_ITEM, "tier": 3, "payout": INCOME_PAYOUT,
		"next_remaining_seconds": null})
	check(top.contains("60 wood, 3 xp") and top.contains("rung 3")
			and top.contains("480 min / 28800 s")
			and top.contains("top rung reached"),
		"the top-rung readout names the yield, the rung in both units, and the "
		+ "clamp: %s" % top)
	var no_income := CollectionFlow.readout_text({"ok": true,
		"has_income": false, "item": INCOME_ITEM})
	check_eq(no_income, "",
		"a row whose item records no committed income has nothing to read out")
	check_eq(CollectionFlow.readout_text({"ok": false}), "",
		"a rejected evaluation produces no readout")


# ---------------------------------------------------------------------------
# Collect flow (spec "Collection flow")
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
	var building: Variant = _placement_by_slot(state, INCOME_SLOT)
	check(building != null, "the recorded building is addressable by key 2")
	if building != null:
		check_eq(int(building.item), INCOME_ITEM,
			"key 2 names the Tree (item 905)")
		check_eq(building.cell, INCOME_CELL,
			"the fresh save anchors it at (53,39)")
		check_eq(_typed_row(building.raw), INCOME_ROW,
			"the row is the pre-execution row the fixture mutated")
		check_eq(building.collected_at, 0,
			"the fresh corpus records a collection clock of 0 (never "
			+ "collected)")
		check_eq(building.started_at, null,
			"the collection clock and the construction reading are kept "
			+ "distinguishable: this row has a collection clock of 0 and no "
			+ "construction start instant")
	var spare: Variant = _placement_by_slot(state, SPARE_SLOT)
	check(spare != null, "the spare building is addressable by key 11")
	if spare != null:
		check_eq(spare.collected_at, 0,
			"the spare row also records a never-collected clock of 0")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the collect save")
	if not (listing is BootData.SaveListResult):
		return
	if (listing as BootData.SaveListResult).saves.is_empty():
		check(false, "the save list carries a save")
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
		"the fresh save renders 40 objects before any collection")

	var requests_start: int = api.collect_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	await _check_collected(town, state, api)
	_check_too_early_after_collect(town, state, api)
	_check_mutual_exclusion(town, api)
	await _check_unknown_index(registry, api)
	await _check_transport_failure(registry, api)
	check_eq(api.collect_requests, requests_start + 3,
		"the whole flow issued exactly three requests (one collected, one "
		+ "structured failure, one transport failure); every other check sent "
		+ "none")
	town.free()

	# The refusals that need their own town run separately so the applied state
	# of the main flow stays intact for the counts above.
	await _check_cancelled_collect(registry, api)
	await _check_no_income_refusal(registry, api)
	await _check_capped_refusal(registry, api)
	await _check_unaddressable_refusal(registry, api)
	await _check_unreadable_row_refusal(registry, api)
	await _check_under_construction_refusal(registry, api)


## The selection-driven surface offers `Collect` beside `Move`, `Sell`, `Store`,
## `Upgrade`, and `Build` for a selected, addressable placed building whose item
## resolves committed income and whose row has reached a committed rung, and
## pressing it arms the collection in the SAME slot the other five modes use
## (design D8: no seventh panel, no grid target, and none of the five delivered
## modes is altered).
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.collect_active(),
		"the collection is not armed before a selection")
	check(not town.collect_selection_available(),
		"no selection means no collect action")
	check_eq(town.collect_slot(), TownState.NO_SLOT,
		"an unarmed collection names no index")
	check_eq(town.collect_evaluation(), {},
		"an unarmed collection has no evaluation")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(INCOME_CELL))
	check(bool(press.get("ok", false)),
		"the press selects the building: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), INCOME_ITEM,
		"the press at (53,39) selects the Tree")
	check(town.collect_selection_available(),
		"an addressable income-bearing selection offers the collect action")
	for delivered in ["move_selection_available", "sell_selection_available",
			"store_selection_available", "construction_selection_available"]:
		check(bool(town.call(str(delivered))),
			"the same selection still offers the delivered %s"
				% str(delivered))
	# The Tree records `upgrades_to -1`, so the delivered upgrade action is
	# withheld for it — that is the delivered behavior, unchanged by this line,
	# and it is asserted here so a regression in the sixth mode cannot hide it.
	check(not bool(town.upgrade_selection_available()),
		"the delivered upgrade action is still withheld for a Tree (no next tier)")
	check(town.ui.has_slot("move"),
		"the selection-driven surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("move"),
		"the surface slot shows for a committed selection")
	check(not town.placement_active(),
		"a selection never arms the placement picker")
	for unarmed in ["move_active", "sell_active", "store_active",
			"upgrade_active", "construction_active"]:
		check(not bool(town.call(str(unarmed))),
			"a selection alone never arms the %s mode" % str(unarmed))

	# The readout renders for the live selection BEFORE anything is armed, and it
	# renders ON SCREEN (the panel owns a line of its own, not just an
	# accessor).
	var readout: String = town.collect_readout()
	check(_collect_readout_label(town) == readout,
		"the collection readout is rendered on the surface's own line: %s"
			% _collect_readout_label(town))
	check(readout.contains("item %d" % INCOME_ITEM),
		"the readout names the selected building: %s" % readout)
	check(readout.contains("60 wood") and readout.contains("3 xp"),
		"the readout names the derived yield and its resource: %s" % readout)
	check(readout.contains("rung 3") and readout.contains("480 min / 28800 s"),
		"the readout names the committed rung in both units: %s" % readout)
	check(readout.contains("top rung reached"),
		"the readout names the top-rung clamp: %s" % readout)

	var panel: Variant = _surface_panel(town)
	check(panel != null, "the selection-driven panel commits into its slot")
	if panel == null:
		return
	var panel_node := panel as Node
	var collect_button: Variant = _button_named(panel_node, "collect")
	check(collect_button is Button, "the collect action button exists")
	if collect_button is Button:
		check(not (collect_button as Button).disabled,
			"the collect action is enabled for an addressable income selection")
		check_eq((collect_button as Button).text, "Collect",
			"the action is labelled Collect")
	for delivered in ["move", "sell", "store", "build"]:
		var button: Variant = _button_named(panel_node, delivered)
		check(button is Button and not (button as Button).disabled,
			"the delivered %s action is still enabled beside it" % delivered)
	var upgrade_delivered: Variant = _button_named(panel_node, "upgrade")
	check(upgrade_delivered is Button and (upgrade_delivered as Button).disabled,
		"the delivered upgrade action is still withheld (disabled) for a Tree")
	check_eq((upgrade_delivered as Button).text, "Upgrade (unavailable)",
		"the delivered upgrade action still names its own unavailability")
	var confirm_button: Variant = _button_named(panel_node, "confirm")
	check(confirm_button is Button and not (confirm_button as Button).visible,
		"the confirm is not offered before a collection is armed")
	check(_button_named(panel_node, "cancel") != null,
		"the cancel action button exists")
	check(String(_surface_status(town)).contains("press Move"),
		"the unarmed status line is the delivered one, unchanged")

	# The button wiring arms the collection (the signal path, one `pressed`
	# emission = one arm — no request).
	if collect_button != null:
		(collect_button as Button).pressed.emit()
	check(town.collect_active(), "pressing the action arms the collection")
	check_eq(town.collect_slot(), INCOME_SLOT,
		"the armed collection names the building's legacy key 2")
	var facts: Dictionary = town.collect_income()
	check_eq(int(facts.get("amount", 0)), INCOME_AMOUNT,
		"the armed collection derives the item's committed amount")
	check_eq(str(facts.get("resource_type", "")), "w",
		"the armed collection derives the item's committed resource type")
	check_eq(int(facts.get("experience", 0)), INCOME_XP,
		"the armed collection derives the item's committed experience")
	check_eq(int(facts.get("cap", 0)), 0,
		"the armed collection derives the item's committed cap")
	check_eq(str(facts.get("name", "")), "Tree",
		"the armed collection's committed facts name the building")
	var armed_evaluation: Dictionary = town.collect_evaluation()
	check_eq(armed_evaluation.get("payout", []), INCOME_PAYOUT,
		"the armed evaluation's DERIVED payout matches the fixture's")
	check_eq(int(armed_evaluation.get("tier", -1)), 3,
		"the armed evaluation derived the top committed rung")
	var status := String(_surface_status(town))
	check(status.contains("armed") and status.contains("collect"),
		"the status names the armed collection: %s" % status)
	check(status.contains("derived"),
		"the status names the payout as derived: %s" % status)
	var selection_text := String(_surface_selection_text(town))
	check(selection_text.contains("60 wood"),
		"the selection line names the derived payout: %s" % selection_text)
	check(selection_text.contains("derived, never observed"),
		"the selection line presents the amount as derived, never observed: %s"
			% selection_text)
	# A collection has NO grid target, so no footprint preview is displayed.
	check(not town.move_preview_shown(),
		"an armed collection shows no footprint preview (it has no target)")
	check(town.move_evaluation().is_empty(),
		"an armed collection commits no move evaluation")
	check_eq(api.collect_requests, requests_before,
		"arming sent no request")
	var again: Dictionary = town.arm_collect()
	check(not bool(again.get("ok", true)),
		"arming an already-armed collection rejects")
	check_eq(str(again.get("code", "")), "collect_already_active",
		"the double-arm names the condition")
	# The delivered modes are unavailable while a collection is armed: the six
	# modes share one surface and never stack. Arming REBUILDS the panel, so it
	# is re-read here.
	var armed_panel: Variant = _surface_panel(town)
	for other in ["move", "sell", "store", "upgrade", "build", "collect"]:
		var other_button: Variant = _button_named(armed_panel as Node, other)
		if other_button is Button:
			check((other_button as Button).disabled,
				"the %s action is unavailable while a collection is armed"
					% other)
	var armed_confirm: Variant = _button_named(armed_panel as Node, "confirm")
	if armed_confirm is Button:
		check((armed_confirm as Button).visible,
			"the targetless confirm is offered as soon as the collection is "
			+ "armed")
		check_eq((armed_confirm as Button).text, "Collect",
			"the shared confirm names the armed mode's own action")
	# Mutual exclusion, in both directions (spec "mutually exclusive with the
	# delivered move, sell, store, upgrade, and construction modes"): the armed
	# collection refuses the other five by name, and the refusal names the ARMED
	# mode (the collection), never the one the player tried to arm.
	for entry in ["arm_move", "arm_sell", "arm_store", "arm_upgrade",
			"arm_construction"]:
		var refused: Dictionary = await town.call(str(entry))
		check(not bool(refused.get("ok", true)),
			"%s while a collection is armed rejects" % str(entry))
		check_eq(str(refused.get("code", "")), "collect_already_active",
			"the stacked-arm refusal of %s names the armed collection"
				% str(entry))
	check_eq(api.collect_requests, requests_before,
		"every refusal on this surface sent no request")
	check(town.collect_active(),
		"the refusals never disarm the collection in progress")
	# Cancelling here keeps the applied-state checks that follow on a clean
	# surface; the cancel contract itself is asserted in its own check.
	var released: Dictionary = town.cancel_collect()
	check(bool(released.get("ok", false)),
		"the collection closes for the applied check: %s"
			% released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition.
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	# The confirm on a closed collection refuses by name and sends nothing.
	var closed: Dictionary = await town.confirm_collect()
	check(not bool(closed.get("ok", true)),
		"a closed collection refuses a confirm")
	check_eq(str(closed.get("code", "")), "collect_not_active",
		"the closed-collection refusal names the condition")
	check_eq(api.collect_requests, requests_before,
		"the closed-collection refusal sent no request")

	# Re-select the recorded building and arm once more for the
	# selection-changed refusal.
	town.handle_pointer_press(Iso.grid_to_screen(INCOME_CELL))
	var armed: Dictionary = town.arm_collect()
	check(bool(armed.get("ok", false)),
		"the collection re-arms: %s" % armed.get("error"))
	check_eq(api.collect_requests, requests_before,
		"re-arming sent no request")
	var elsewhere: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SPARE_CELL))
	check(bool(elsewhere.get("ok", false)),
		"a press elsewhere still selects: %s" % elsewhere.get("error"))
	check_eq(town.selection_legacy_id(), SPARE_ITEM,
		"the press at (58,48) selects the other building")
	var re_targeted: Dictionary = await town.confirm_collect()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose selection moved refuses")
	check_eq(str(re_targeted.get("code", "")), "collect_selection_changed",
		"the re-target refusal names the condition: %s"
			% re_targeted.get("error"))
	check_eq(api.collect_requests, requests_before,
		"the re-target refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	var closed_armed: Dictionary = town.cancel_collect()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed collection closes cleanly: %s"
			% closed_armed.get("error"))


## The collected income: one confirmed intent sending exactly one request,
## applying only the authoritative response, and leaving the SAME rendered
## object in place with the SAME placement instance under the SAME legacy key
## and cell. The response's balances and experience win outright, and the
## readout reflects the response's own reference instant.
func _check_collected(town: Node2D, state: Variant, api: Variant) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(INCOME_CELL))
	check(town.selection_legacy_id() == INCOME_ITEM,
		"the recorded building is the committed selection again")
	var object: Variant = _object_for_cell(town, INCOME_CELL)
	check(object != null, "the Tree object is committed before the collection")
	if object == null:
		return
	var collecting: Variant = _placement_by_slot(state, INCOME_SLOT)
	var armed: Dictionary = town.arm_collect()
	check(bool(armed.get("ok", false)),
		"the collection arms: %s" % armed.get("error"))
	if not bool(armed.get("ok", false)):
		return
	check_eq(armed.get("payout", []), INCOME_PAYOUT,
		"the armed collection's DERIVED payout matches the fixture's")
	check_eq(int(armed.get("tier", -1)), 3,
		"the armed collection derived the top committed rung")
	var requests_before: int = api.collect_requests
	var signature_before := _object_signature(town)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var confirmed: Dictionary = await town.confirm_collect()
	check(bool(confirmed.get("ok", false)),
		"the confirmed collection succeeds: %s" % confirmed.get("error"))
	check_eq(api.collect_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	_check_typed_collect(confirmed.get("result"))
	# The authoritative apply: the SAME placement instance now carries the
	# response's row, the SAME rendered object is retained at the same index in
	# the committed draw order, and both counts are unchanged.
	var after: Variant = _placement_by_slot(state, INCOME_SLOT)
	check(after == collecting, "the same placement instance carries the new row")
	check_eq(after.cell, INCOME_CELL, "the cell is unchanged")
	check_eq(after.slot, INCOME_SLOT, "the legacy key is unchanged")
	check_eq(int(after.item), INCOME_ITEM, "the item is unchanged")
	check(int(after.collected_at) > 0,
		"the typed collection clock carries the response's re-stamped instant")
	check_eq(int(_typed_row(after.raw)[0]), INCOME_ITEM,
		"the typed row keeps the row's own item")
	check_eq(after.attr, {},
		"a collection writes no attribute bag entry (it touches no "
		+ "construction state)")
	check_eq(after.countdown, null,
		"a collection records no construction countdown")
	check_eq(after.clicks, null,
		"a collection records no construction click counter")
	check_eq(state.placements.size(), PLACEMENTS,
		"a collection changes no placement count (the key is reused)")
	check_eq(town.objects.size(), PLACEMENTS,
		"a collection changes no object count (the key is reused)")
	check(_object_for_cell(town, INCOME_CELL) == object,
		"the SAME rendered object is retained at the same cell")
	check_eq(_object_signature(town), signature_before,
		"a collection re-sorts nothing: the draw order is byte-identical")
	check_eq(town.objects.size(), town.objects_layer.get_child_count(),
		"the objects layer holds exactly the committed object list")
	check(town.collect_placement() == null,
		"the armed placement is released after the apply")
	check(not town.collect_active(), "the collection closes after the apply")
	check_eq(town.collect_error, "", "success leaves no failure record")
	check_eq(state.storage, storage_before, "the storage mapping is untouched")
	# The RESPONSE wins: the balances and the experience are the response's
	# values, applied verbatim, never the client's own arithmetic.
	check_eq(state.resources.wood, FRESH_WOOD + 60,
		"the wood balance takes the response's value (the response wins)")
	check_eq(state.resources.coins, FRESH_GOLD,
		"the coins balance is the response's unchanged value")
	check_eq(state.resources.oil, FRESH_GOLD,
		"the oil balance is the response's unchanged value")
	check_eq(state.resources.steel, FRESH_GOLD,
		"the steel balance is the response's unchanged value")
	check_eq(state.resources.cash, FRESH_CASH,
		"the cash balance is the response's unchanged value")
	check_eq(state.resources.mana, 0,
		"the mana balance is the response's unchanged value")
	check_eq(state.summary.xp, FRESH_XP + 3,
		"the experience takes the response's value (the response wins)")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("wood"), str(FRESH_WOOD + 60),
			"the HUD renders the authoritative wood")
		check_eq(hud.displayed("xp"), str(FRESH_XP + 3),
			"the HUD renders the authoritative xp")
	# The readout reflects the NEW clock, evaluated against the response's own
	# reference instant rather than the local clock.
	var readout: String = town.collect_readout()
	check(readout.contains("item %d" % INCOME_ITEM),
		"the readout still names the building: %s" % readout)
	check(readout.contains("no committed rung reached"),
		"the readout reflects the re-stamped clock: %s" % readout)
	check(readout.contains("300 s"),
		"the readout names the countdown to the first rung: %s" % readout)
	check_eq(int(collecting.collected_at),
		int((confirmed.get("result") as BootData.CollectResult).row.timestamp),
		"the readout's clock is the response's re-stamped instant, never a "
		+ "locally computed one")
	# The readout re-renders on the surface's own line from the response's own
	# reference instant.
	check(_collect_readout_label(town) == readout,
		"the on-screen collection line shows the response's new clock: %s"
			% _collect_readout_label(town))
	# The status line names what the SERVICE did, not what the client derived.
	var status := String(_surface_status(town))
	check(status.contains("collected") and status.contains("rung 3"),
		"the status names the applied collection and its rung: %s" % status)


## The too-early refusal on a row that was JUST collected: the response
## re-stamped the clock, so the same row now reaches no committed rung. The
## action is no longer offered, arming is refused by name, and NOTHING is sent
## (design D3) — while the row keeps the instant the response gave it.
func _check_too_early_after_collect(town: Node2D, state: Variant,
		api: Variant) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(INCOME_CELL))
	check_eq(town.selection_legacy_id(), INCOME_ITEM,
		"the collected building is the committed selection again")
	check(not town.collect_selection_available(),
		"a row that has reached no committed rung never offers the collect "
		+ "action")
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(state)
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var collect_button: Variant = _button_named(panel as Node, "collect")
		if collect_button is Button:
			check((collect_button as Button).disabled,
				"the collect action is disabled for a too-early row")
			check_eq((collect_button as Button).text, "Collect (unavailable)",
				"the action names its own unavailability")
	var refused: Dictionary = town.arm_collect()
	check(not bool(refused.get("ok", true)),
		"arming a too-early row fails")
	check_eq(str(refused.get("code", "")), CollectionFlow.REASON_TOO_EARLY,
		"the refusal names the too-early condition: %s" % refused.get("error"))
	check(String(refused.get("error", "")).contains("no committed ladder rung"),
		"the explicit error says the row has reached no committed rung yet: %s"
			% refused.get("error"))
	check_eq(api.collect_requests, requests_before,
		"the too-early refusal sent no request")
	check_eq(_state_snapshot(state), snapshot_before,
		"the too-early refusal changes no state")
	var row: Variant = _placement_by_slot(state, INCOME_SLOT)
	check(row != null and int(row.collected_at) > 0,
		"the too-early row keeps the collection instant the response gave it")


## The other direction of the six-mode mutual exclusion: a collection cannot be
## armed while a delivered mode already is. Runs on the spare building so the
## recorded building's selection stays untouched for the applied checks.
func _check_mutual_exclusion(town: Node2D, api: Variant) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(SPARE_CELL))
	check(town.selection_legacy_id() == SPARE_ITEM,
		"the spare building is selectable for the exclusion checks")
	var requests_before: int = api.collect_requests
	for entry in [["arm_store", "store_already_active"],
			["arm_sell", "sell_already_active"],
			["arm_move", "move_already_active"]]:
		var armed: Dictionary = town.call(str(entry[0]))
		check(bool(armed.get("ok", false)),
			"the delivered %s arms on the spare building: %s"
				% [str(entry[0]), armed.get("error")])
		var over: Dictionary = town.arm_collect()
		check(not bool(over.get("ok", true)),
			"arming a collection while a %s is armed rejects" % str(entry[0]))
		check_eq(str(over.get("code", "")), str(entry[1]),
			"the refusal names the armed %s: %s"
				% [str(entry[0]), over.get("error")])
		town.call("cancel_" + str(entry[0]).trim_prefix("arm_"))
	check_eq(api.collect_requests, requests_before,
		"every mutual-exclusion refusal sent no request")


## The unknown-index failure: the intent names an index the service does not
## know (a stale client state — the endpoint resolves the index before
## executing and answers 404 `unknown_item_index`, so legacy's silent no-op is
## never reported as a success), the explicit error names that code, and the row
## keeps its collection instant with the storage unchanged.
func _check_unknown_index(registry: Variant, api: Variant) -> void:
	var requests_before: int = api.collect_requests
	var ghost_town: Variant = _town_with_extra_row(registry)
	if ghost_town == null:
		return
	var snapshot_before := _state_snapshot(ghost_town.state)
	var armed: Dictionary = ghost_town.arm_collect()
	check(bool(armed.get("ok", false)),
		"the extra row arms a collection: %s" % armed.get("error"))
	if bool(armed.get("ok", false)):
		check_eq(ghost_town.collect_slot(), UNKNOWN_INDEX,
			"the armed collection names the unknown index")
		var failed: Dictionary = await ghost_town.confirm_collect()
		check(not bool(failed.get("ok", true)),
			"the unknown index fails the intent")
		check_eq(str(failed.get("code", "")), "unknown_item_index",
			"the structured failure surfaces its code: %s"
				% failed.get("error"))
		check(ghost_town.collect_error.contains("unknown_item_index"),
			"the explicit error names the structured failure")
		check_eq(ghost_town.objects.size(), PLACEMENTS + 1,
			"the structured failure removes nothing")
		check(_placement_by_slot(ghost_town.state, UNKNOWN_INDEX) != null,
			"the unknown-index row is still in the typed state")
		var row: Variant = _placement_by_slot(ghost_town.state, UNKNOWN_INDEX)
		check_eq(int(row.item), INCOME_ITEM,
			"the unknown-index row keeps its item")
		check_eq(row.collected_at, 0,
			"the unknown-index row keeps its previous collection instant")
		check_eq(_state_snapshot(ghost_town.state), snapshot_before,
			"the structured failure changes no state at all")
		check(ghost_town.collect_active(),
			"the collection survives the structured failure")
		var closed: Dictionary = ghost_town.cancel_collect()
		check(bool(closed.get("ok", false)),
			"the failed collection closes cleanly")
	ghost_town.free()
	check_eq(api.collect_requests, requests_before + 1,
		"the failed intent still sent exactly once")


## LAST scenario (it waits out the refused loopback endpoint): the intent goes
## out over the legacy transport, the endpoint refuses it, and the explicit
## error names `unreachable_endpoint` with the row keeping its collection
## instant, the storage unchanged, and no resource changed (the same
## no-mutation contract as a structured failure).
func _check_transport_failure(registry: Variant, api: Variant) -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the transport "
		+ "scenario")
	if endpoint == "":
		return
	var transport_town: Variant = _town_with_crafted_row(registry, INCOME_ITEM,
		TRANSPORT_SLOT, {})
	if transport_town == null:
		return
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(transport_town.state)
	var objects_before: int = transport_town.objects.size()
	api.configure("legacy_v0", endpoint)
	var armed: Dictionary = transport_town.arm_collect()
	check(bool(armed.get("ok", false)),
		"the transport row arms a collection: %s" % armed.get("error"))
	var attempt: Dictionary = await transport_town.confirm_collect()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(transport_town.collect_error.contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.collect_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(transport_town.state), snapshot_before,
		"the transport failure changes no state")
	check_eq(transport_town.objects.size(), objects_before,
		"the transport failure renders nothing new")
	var row: Variant = _placement_by_slot(transport_town.state, TRANSPORT_SLOT)
	check(row != null and int(row.collected_at) == 0,
		"the transport failure leaves the row's collection instant untouched")
	check(transport_town.collect_active(),
		"the collection survives the transport failure")
	# The last state-changing check ran against the fake, so the implementation
	# switch is undone here rather than leaked.
	transport_town.free()
	api.configure("fake")


## The cancelled-collection contract: arming and closing on a FRESH town leaves
## the serialized town state, the row's collection instant, both readouts, the
## storage view, the selection, the resources, and the request count
## byte-identical — and the surface offers no action beyond the six modes.
func _check_cancelled_collect(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, INCOME_CELL, INCOME_ITEM,
		"the cancel town")
	if town == null:
		return
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(town.state)
	var armed: Dictionary = town.arm_collect()
	check(bool(armed.get("ok", false)),
		"the collection arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var collect_readout_before: String = town.collect_readout()
	var build_readout_before: String = town.construction_readout()
	var cancelled: Dictionary = town.cancel_collect()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the collection: %s" % cancelled.get("error"))
	check(not town.collect_active(), "the collection closes")
	check(town.collect_placement() == null, "the collected placement drops")
	check_eq(town.collect_slot(), TownState.NO_SLOT,
		"a closed collection names no index")
	check(not town.ui.is_slot_visible("move"),
		"the surface slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled collection")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS, "cancel renders nothing")
	check_eq(town.collect_readout(), collect_readout_before,
		"cancel leaves the collection readout untouched")
	check_eq(town.construction_readout(), build_readout_before,
		"cancel leaves the construction readout untouched")
	check(String(_surface_status(town)).contains("nothing was sent"),
		"cancel says that nothing was sent: %s" % _surface_status(town))
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.collect_requests, requests_before,
		"cancel sent no request")
	var again: Dictionary = town.cancel_collect()
	check(not bool(again.get("ok", true)),
		"closing an already-closed collection rejects")
	check_eq(str(again.get("code", "")), "collect_not_active",
		"the double-close names the condition")
	check_eq(api.collect_requests, requests_before,
		"the double-close sent no request")
	# The cancel row is the ONLY cancellation this surface offers, and it sends
	# nothing — there is deliberately no action that clears a row, hires a
	# friend, or applies a speedup.
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var buttons: Array = []
		_collect_buttons(panel as Node, buttons)
		var names: Array = []
		for button: Variant in buttons:
			names.append(String((button as Button).name))
		check_eq(names, ["move", "sell", "store", "upgrade", "build",
			"collect", "confirm", "cancel"],
			"the surface offers exactly the five delivered actions, the collect "
			+ "action, one confirm, and one cancel — nothing else")
	town.free()


## The no-income refusal: the committed configuration records `collect 0` for
## a Turret I, so the service answers `no_income` for it and the client never
## sends a request it knows will fail. The row renders, selects, and offers the
## other five actions; its readout says nothing, because there is no income to
## read out.
func _check_no_income_refusal(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, SPARE_CELL, SPARE_ITEM,
		"the no-income town")
	if town == null:
		return
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(town.state)
	check(not town.collect_selection_available(),
		"a building that records no committed income never offers the collect "
		+ "action")
	check_eq(town.collect_readout(), "",
		"a building with no committed income renders no collection readout")
	var facts: Dictionary = town.collect_income()
	check(bool(facts.get("ok", false))
			and int(facts.get("amount", -1)) == 0,
		"the no-income row's committed facts resolve with a ZERO amount (the "
		+ "content is readable; there is simply nothing to pay): %s"
			% facts.get("reason"))
	check(town.move_selection_available(),
		"the delivered move action is still offered on a no-income row")
	var refused: Dictionary = town.arm_collect()
	check(not bool(refused.get("ok", true)),
		"arming a no-income row fails")
	check_eq(str(refused.get("code", "")), CollectionFlow.REASON_NO_INCOME,
		"the refusal names the no-income condition: %s" % refused.get("error"))
	check_eq(api.collect_requests, requests_before,
		"the no-income refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the no-income refusal changes no state")
	town.free()


## The cap refusal (design D4): a real committed item whose income carries a
## NON-ZERO `max_collects` is refused rather than paid under an invented cap
## semantics. No placed corpus row names such an item, so the suite crafts one
## in memory; the committed configuration itself is the source of the fact.
func _check_capped_refusal(registry: Variant, api: Variant) -> void:
	var town: Variant = _town_with_crafted_row(registry, CAPPED_ITEM,
		CAPPED_SLOT, {})
	if town == null:
		return
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(town.state)
	var facts: Dictionary = town.collect_income()
	check(not bool(facts.get("ok", false)),
		"a capped item's committed income is refused: %s"
			% facts.get("reason"))
	check(String(str(facts.get("reason", ""))).contains("25"),
		"the refusal names the committed cap it refuses to interpret: %s"
			% facts.get("reason"))
	check(not town.collect_selection_available(),
		"a capped row never offers the collect action")
	var refused: Dictionary = town.arm_collect()
	check(not bool(refused.get("ok", true)),
		"arming a capped row fails")
	check_eq(str(refused.get("code", "")), CollectionFlow.REASON_CAPPED,
		"the refusal names the capped condition: %s" % refused.get("error"))
	check_eq(api.collect_requests, requests_before,
		"the capped refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the capped refusal changes no state")
	town.free()


## The unaddressable-row refusal (the delivered flows' own reason): a row whose
## save key is not a positive integer parses, renders, and is selectable, but
## the collect action is unavailable, arming is refused by name, and NOTHING is
## sent — the index is never coerced, because a coerced index would name a
## different row.
func _check_unaddressable_refusal(registry: Variant, api: Variant) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["mystery"] = [
		INCOME_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, [], {}, 1]
	var town: Variant = _built_town(crafted, registry, GHOST_CELL, INCOME_ITEM,
		"the unaddressable town")
	if town == null:
		return
	var requests_before: int = api.collect_requests
	var snapshot_before := _state_snapshot(town.state)
	check(not town.collect_selection_available(),
		"an unaddressable row never offers the collect action")
	var panel: Variant = _surface_panel(town)
	if panel != null:
		var collect_button: Variant = _button_named(panel as Node, "collect")
		if collect_button is Button:
			check((collect_button as Button).disabled,
				"the collect action is disabled for an unaddressable row")
		check(String(_surface_status(town)).contains("not movable"),
			"the status keeps the delivered unaddressable line")
	var refused: Dictionary = town.arm_collect()
	check(not bool(refused.get("ok", true)),
		"arming an unaddressable row fails")
	check_eq(str(refused.get("code", "")), MoveFlow.REASON_UNADDRESSABLE,
		"the refusal names the move flow's own unaddressable reason: %s"
			% refused.get("error"))
	check(String(refused.get("error", "")).contains("mystery"),
		"the explicit error names the offending save key")
	check_eq(api.collect_requests, requests_before,
		"the unaddressable refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the unaddressable refusal changes no state")
	town.free()


## The unreadable-row refusal: a row whose attribute bag is not an object
## carries no readable construction state, so the flow cannot show the row to
## be free of a build. The shared parser keeps such a row verbatim (the
## delivered selection suite's crafted rows have the same shape), and the flow
## refuses it by name rather than reading a countdown out of a value that is
## not a bag.
func _check_unreadable_row_refusal(registry: Variant, api: Variant) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)["opaque"] = [
		INCOME_ITEM, GHOST_CELL.x, GHOST_CELL.y, 0, 0, 0, 0, 1]
	var town: Variant = _built_town(crafted, registry, GHOST_CELL, INCOME_ITEM,
		"the opaque-row town")
	if town == null:
		return
	var requests_before: int = api.collect_requests
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(GHOST_CELL))
	check(bool(pressed.get("ok", false)),
		"the opaque row is selectable: %s" % pressed.get("error"))
	check(not town.collect_selection_available(),
		"a row with no readable attribute bag offers no collect action")
	var refused: Dictionary = town.arm_collect()
	check(not bool(refused.get("ok", true)),
		"arming an opaque row fails")
	check_eq(str(refused.get("code", "")),
		CollectionFlow.REASON_UNREADABLE_STATE,
		"the refusal names the unreadable-state condition: %s"
			% refused.get("error"))
	check_eq(api.collect_requests, requests_before,
		"the unreadable-row refusal sent no request")
	town.free()


## The construction-state refusal (design D5, the CLIENT half of the two-layer
## rule): a row carrying a recorded countdown (or a build-click counter) has an
## `item[3]` that is a build's start instant, and the executed probe shows a
## collection there would overwrite it while the countdown survived — while
## legacy reports success. The client therefore offers no action, refuses by
## name, and sends nothing; the service refuses the same row independently.
func _check_under_construction_refusal(registry: Variant, api: Variant) -> void:
	for entry in [[COUNTDOWN_SLOT, {"cp": 180}, 1790690500,
			"a recorded countdown"],
			[COUNTER_SLOT, {"nc": 0}, 0, "a recorded build-click counter"]]:
		var slot := int(entry[0])
		var town: Variant = _town_with_crafted_row(registry, INCOME_ITEM, slot,
			entry[1] as Dictionary, int(entry[2]))
		if town == null:
			continue
		var requests_before: int = api.collect_requests
		var snapshot_before := _state_snapshot(town.state)
		var label := str(entry[3])
		check(not town.collect_selection_available(),
			"a row with %s never offers the collect action" % label)
		var refused: Dictionary = town.arm_collect()
		check(not bool(refused.get("ok", true)),
			"arming a row with %s fails" % label)
		check_eq(str(refused.get("code", "")),
			CollectionFlow.REASON_CONSTRUCTION_IN_PROGRESS,
			"the refusal names the construction-state condition: %s"
				% refused.get("error"))
		check(String(refused.get("error", "")).contains("construction"),
			"the explicit error names the construction refusal: %s"
				% refused.get("error"))
		check_eq(api.collect_requests, requests_before,
			"the %s refusal sent no request" % label)
		check_eq(_state_snapshot(town.state), snapshot_before,
			"the %s refusal changes no state" % label)
		# The construction state itself is left exactly as it was: the refusal
		# never reaches the write, in this layer.
		var row: Variant = _placement_by_slot(town.state, slot)
		check(row != null and row.countdown == (entry[1] as Dictionary).get("cp")
				and row.clicks == (entry[1] as Dictionary).get("nc"),
			"the refused row's construction state is untouched: %s"
				% JSON.stringify(row.attr))
		check_eq(int(row.timestamp), int(entry[2]),
			"the refused row's start instant is untouched")
		# The DELIVERED construction flow still reads the very same facts off the
		# refused row through its OWN accessor: the collect refusal never reached
		# a write that could disturb the construction line. An ABSENT counter or
		# countdown is compared as null, never coerced to a number.
		var build_evaluation: Dictionary = ConstructionFlow.state_of(row)
		var expected_clicks: Variant = (entry[1] as Dictionary).get("nc", null)
		var expected_countdown: Variant = (entry[1] as Dictionary).get("cp", null)
		check(bool(build_evaluation.get("ok", false))
				and build_evaluation.get("clicks", null) == expected_clicks
				and build_evaluation.get("countdown", null) == expected_countdown,
			"the delivered construction flow reads the same construction state "
			+ "off the refused row: the collect refusal disturbed nothing")
		town.free()


## The typed result of one confirmed collection: protocol, version, legacy
## result, both rows, the derived payout and its rung, the reference instant,
## and the resources. The wall-clock fields are asserted as positive integers
## and never by value.
func _check_typed_collect(result: Variant) -> void:
	check(result is BootData.CollectResult,
		"the confirm carries the typed collect result")
	if not (result is BootData.CollectResult):
		return
	var typed: BootData.CollectResult = result
	check(typed.ok, "the collect response is a success")
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the collect protocol is compat-v0")
	check_eq(typed.game_version, "alpha 0.02",
		"the collect response carries the game version")
	check(typed.server_time > 0,
		"the collect server_time is the fixture epoch (time-dependent)")
	check_eq(typed.result, "success", "the legacy result string is verbatim")
	check(typed.previous != null,
		"the collect response carries the previous row")
	check(typed.row != null,
		"the collect response carries the post-execution row")
	check(typed.resources != null,
		"the collect response carries typed resources")
	if typed.previous == null or typed.row == null or typed.resources == null:
		return
	check_eq(typed.payout, INCOME_PAYOUT,
		"the derived payout is the documented eight-slot vector")
	check_eq(int(typed.payout[0]), 0,
		"the derived payout's unread unknown slot is zero (D6)")
	check_eq(int(typed.payout[7]), 0,
		"the derived payout's never-produced mana slot is zero (D6)")
	check_eq(int(typed.payout[1]), 3,
		"the derived payout's experience is 3")
	check_eq(int(typed.payout[3]), 60, "the derived payout's wood is 60")
	check_eq(typed.tier, 3,
		"the derived payout came from the top committed rung")
	check(typed.reference_time > 0,
		"the reference instant is a positive epoch (time-dependent, never "
		+ "asserted by value)")
	check_eq(_boot_row(typed.previous), INCOME_ROW,
		"the previous row is the pre-execution row the fixture mutated")
	check_eq(typed.row.item_id, INCOME_ITEM,
		"the post-execution row names the same building (no item change)")
	check_eq([typed.row.x, typed.row.y], [INCOME_CELL.x, INCOME_CELL.y],
		"the post-execution row reuses the same cell")
	check(typed.row.timestamp > typed.previous.timestamp,
		"the post-execution row's collection instant moved FORWARD "
		+ "(time-dependent field, never asserted by value)")
	check_eq(typed.row.orientation, 0,
		"the post-execution row keeps the row's own orientation")
	check_eq(typed.row.player, 1,
		"the post-execution row keeps the row's own player field")
	check_eq(typed.row.attr, {},
		"the post-execution row carries no attribute bag entry")
	# The value-level post-state proof the endpoint makes, asserted here on the
	# typed result the client applied (design D8).
	check_eq(typed.resources.wood, FRESH_WOOD + 60,
		"the applied wood is the fresh save's 2000 plus the derived 60")
	check_eq(typed.resources.xp, FRESH_XP + 3,
		"the applied experience is the fresh save's 4 plus the derived 3")
	check_eq(typed.resources.gold, FRESH_GOLD, "the gold balance is unchanged")
	check_eq(typed.resources.oil, FRESH_GOLD, "the oil balance is unchanged")
	check_eq(typed.resources.steel, FRESH_GOLD,
		"the steel balance is unchanged")
	check_eq(typed.resources.cash, FRESH_CASH, "the cash balance is unchanged")
	check_eq(typed.resources.mana, 0, "the mana balance is unchanged")


# ---------------------------------------------------------------------------
# Towns built in memory (no fixture is ever written)
# ---------------------------------------------------------------------------


## A town on the committed fresh save with one extra row under an index neither
## the corpus nor the double knows (a stale client state), selected through the
## delivered press path.
func _town_with_extra_row(registry: Variant) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[
		str(UNKNOWN_INDEX)] = [INCOME_ITEM, GHOST_CELL.x, GHOST_CELL.y,
			0, 0, [], {}, 1]
	return _built_town(crafted, registry, GHOST_CELL, INCOME_ITEM,
		"the unknown-index town")


## A town on the committed fresh save with one crafted extra row naming
## `item_id` at the ghost cell, under the addressable key `slot`, carrying the
## given attribute bag and collection instant. The row is selected through the
## delivered press path; no fixture is written.
func _town_with_crafted_row(registry: Variant, item_id: int, slot: int,
		attr: Dictionary, stamp: int = 0) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	((crafted["map"] as Dictionary)["items"] as Dictionary)[str(slot)] = [
		item_id, GHOST_CELL.x, GHOST_CELL.y, stamp, 0, [], attr, 1]
	return _built_town(crafted, registry, GHOST_CELL, item_id,
		"the crafted key %d town" % slot)


## A town on the committed fresh save with the given cell selected through the
## delivered press path (no crafted row).
func _selected_town(registry: Variant, cell: Vector2i, item_id: int,
		label: String) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	return _built_town(payload as Dictionary, registry, cell, item_id, label)


## Parses a payload fail-closed, builds the town on it, and selects `cell`
## through the delivered press path, naming the selection in a failure check.
func _built_town(payload: Dictionary, registry: Variant, cell: Vector2i,
		item_id: int, label: String) -> Variant:
	var parsed: Dictionary = TownState.parse(payload, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "%s parses: %s" % [label, parsed.get("error")])
		return null
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(parsed["state"])
	if not bool(built.get("ok", false)):
		check(false, "%s builds: %s" % [label, built.get("error")])
		town.free()
		return null
	var pressed: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(cell))
	if not bool(pressed.get("ok", false)) \
			or town.selection_legacy_id() != item_id:
		check(false, "%s selects the row (selected %d, wanted %d)"
			% [label, town.selection_legacy_id(), item_id])
		town.free()
		return null
	return town


# ---------------------------------------------------------------------------
# The live-collect scenario (verify-boot's `collect-live` phase)
# ---------------------------------------------------------------------------


## One collection through the real Compatibility endpoint, so the unchanged
## legacy `command()` executes the derived `collect` envelope over the
## disposable corpus. This side asserts the typed response AND its value-level
## post-state proof — the collection instant moved forward and EVERY stored
## resource changed by exactly the derived delta — plus the two-layer
## construction-state refusal, whose service half is the fact that the refused
## row's countdown and start instant are still exactly what they were. The
## phase harness separately asserts the corpus save file mutated. No fixture is
## touched.
##
## The row is the **Trees decoration at legacy key 21**, not the Tree at key 2
## the fixture records: this phase runs after the store phase, which popped the
## Tree at key 2 in ITS own independent transaction, and every earlier live
## phase has already moved other rows. Key 21 is untouched by them and records
## the same committed income (`collect 20`, `collect_type "w"`, `collect_xp 1`),
## so it exercises the identical derivation.
const LIVE_ITEM := 930
const LIVE_SLOT := 21
## The row the construction-live phase left under construction, so the
## construction-state refusal is genuinely reachable here.
const LIVE_BUILT_SLOT := 11
func _check_live_collect() -> void:
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
	check(listing is BootData.SaveListResult, "the corpus save list resolves")
	if not (listing is BootData.SaveListResult):
		return
	var saves: Array = (listing as BootData.SaveListResult).saves
	check(not saves.is_empty(), "the corpus carries a save")
	if saves.is_empty():
		return
	var pid := str(saves[0].id)
	var before_row: Variant = await _live_row(api, endpoint, pid, LIVE_SLOT)
	check(before_row != null, "the corpus pre-collect row resolves")
	var before_resources: Dictionary = await _live_resources(api, endpoint, pid)
	if before_row == null or before_resources.is_empty():
		return
	var prior := before_row as Array
	var collected: Variant = await api.collect_income(pid, LIVE_SLOT)
	_check_live_collect_result(collected, prior, before_resources)
	if not (collected is BootData.CollectResult) or not collected.ok:
		return
	var after_row: Variant = await _live_row(api, endpoint, pid, LIVE_SLOT)
	check(after_row != null, "the corpus post-collect row resolves")
	if after_row != null:
		check_eq([int((after_row as Array)[1]), int((after_row as Array)[2])],
			[int(prior[1]), int(prior[2])],
			"the corpus still holds that cell (the key was reused, not re-keyed)")
		check_eq(int((after_row as Array)[0]), int(prior[0]),
			"the corpus still holds the row's own item")
		check_eq((after_row as Array)[6], (prior[6] as Dictionary),
			"a collection writes no attribute bag entry (it touches no "
			+ "construction state)")
		check(int((after_row as Array)[3]) > int(prior[3]),
			"the corpus row's collection instant moved forward")
	# The construction-state refusal, service half. This phase STARTS a
	# construction through the real endpoint first, so the proof does not depend
	# on which live phase ran before it: the row is genuinely under construction
	# here, and a collection on it keeps its countdown AND its start instant
	# byte-identical, which is exactly the corruption probe 2 showed legacy
	# permits. A client that ignored the client-side rule would corrupt them.
	var started: Variant = await api.build_construction(pid, LIVE_BUILT_SLOT,
		"start")
	check(started is BootData.ConstructionResult and started.ok,
		"the transport row is put under construction through the real endpoint")
	var built_before: Variant = await _live_row(api, endpoint, pid,
		LIVE_BUILT_SLOT)
	check(built_before is Array and (built_before as Array).size() == 8,
		"the corpus's construction row resolves with its recorded countdown")
	if built_before is Array and (built_before as Array).size() == 8:
		var countdown: Variant = (built_before as Array)[6].get("cp", null)
		check(countdown != null and int(countdown) > 0,
			"the corpus row really carries construction state: %s"
				% JSON.stringify((built_before as Array)[6]))
		var refused: Variant = await api.collect_income(pid, LIVE_BUILT_SLOT)
		check(refused is BootData.CollectResult and not refused.ok,
			"a collection on a row under construction is refused")
		if refused is BootData.CollectResult:
			check_eq(refused.error_code, "construction_in_progress",
				"the refusal is the service's own two-layer guard: %s"
					% refused.error_message)
			check(refused.previous == null and refused.row == null
					and refused.resources == null and refused.payout == [],
				"the refused collection carries no partial payload")
		var built_after: Variant = await _live_row(api, endpoint, pid,
			LIVE_BUILT_SLOT)
		check(built_after != null
				and (built_after as Array)[6] == (built_before as Array)[6],
			"the refused row's attribute bag is byte-identical afterwards")
		check(built_after != null
				and int((built_after as Array)[3]) == int((built_before as Array)[3]),
			"the refused row's START INSTANT is byte-identical afterwards: the "
			+ "corruption probe 2 showed is prevented in this layer")
	# A stale index fails closed with the endpoint's own code rather than
	# reporting a collection that never happened.
	var unknown: Variant = await api.collect_income(pid, UNKNOWN_INDEX)
	check(unknown is BootData.CollectResult and not unknown.ok,
		"the live unknown index is a structured failure")
	if unknown is BootData.CollectResult:
		check_eq(unknown.error_code, "unknown_item_index",
			"the live structured error passes through with the endpoint's code")
	# The fake derives the same codes for the same intents, offline.
	api.configure("fake")
	var fake_unknown: Variant = await api.collect_income(pid, UNKNOWN_INDEX)
	check(fake_unknown is BootData.CollectResult and not fake_unknown.ok,
		"the fake fails the same intent offline")
	if fake_unknown is BootData.CollectResult:
		check_eq(fake_unknown.error_code, "unknown_item_index",
			"structured codes match between implementations")
	api.configure("legacy_v0", endpoint)
	var typed: BootData.CollectResult = collected
	print("[test] live-collect applied item_index=%d cell=(%d, %d) tier=%d "
		% [LIVE_SLOT, typed.row.x, typed.row.y, typed.tier]
		+ "payout=%s wood=%d xp=%d" % [JSON.stringify(typed.payout),
			typed.resources.wood, typed.resources.xp])


## One live collection's typed response and its value-level post-state proof,
## compared against the corpus's own pre-request row and balances (the reused
## key and cell, and every stored resource moving by exactly the derived delta).
func _check_live_collect_result(result: Variant, prior: Array,
		before: Dictionary) -> void:
	check(result is BootData.CollectResult,
		"the live collect returns the typed result")
	if not (result is BootData.CollectResult):
		return
	var typed: BootData.CollectResult = result
	check(typed.ok, "the live collection resolves over loopback: %s / %s"
		% [typed.error_code, typed.error_message])
	if not typed.ok or typed.previous == null or typed.row == null \
			or typed.resources == null:
		return
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the live collect protocol is compat-v0")
	check(typed.game_version != "",
		"the live collect response carries the game version")
	check(typed.server_time > 0,
		"the live collect server_time is a positive epoch (time-dependent)")
	check_eq(typed.result, "success",
		"the live collect reports the legacy success result")
	check(typed.payout.size() == BootData.COLLECT_VECTOR_SLOTS,
		"the live collect payout is the documented eight-slot vector")
	check_eq(int(typed.payout[0]), 0,
		"the live collect payout's unread unknown slot is zero (D6)")
	check_eq(int(typed.payout[7]), 0,
		"the live collect payout's never-produced mana slot is zero (D6)")
	check(int(typed.payout[1]) > 0 and int(typed.payout[3]) > 0,
		"the live collect payout carries the committed wood and experience")
	check_eq(int(typed.payout[1]), 3, "the live collect pays 3 experience")
	check_eq(int(typed.payout[3]), 60, "the live collect pays 60 wood")
	check(typed.tier >= 0 and typed.tier < CollectionFlow.ladder_size(),
		"the live collect rung is inside the committed ladder")
	check_eq(typed.tier, CollectionFlow.TOP_TIER,
		"the live collect reaches the top committed rung (every corpus row "
		+ "records a never-collected instant of 0)")
	check(typed.reference_time > 0,
		"the live collect reference instant is a positive epoch")
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
	check_eq(typed.row.attr, (prior[6] as Dictionary),
		"the live post-execution row carries the same attribute bag")
	check_eq(int(typed.row.player), int(prior[7]),
		"the live post-execution row keeps the row's own player field")
	# The value-level post-state proof: EVERY stored resource moved by exactly
	# the derived delta, so a reduced or diverging payout is impossible (D8).
	for entry in [["wood", 3, 60], ["xp", 1, 3]]:
		var name := str(entry[0])
		var expected: int = int(before.get(name, 0)) + int(entry[2])
		check_eq(int(typed.resources.get(name)), expected,
			"the live %s balance is the corpus's own value plus the derived "
				% name + "delta (the endpoint's value-level proof)")
	for name in ["gold", "oil", "steel", "cash", "mana"]:
		check_eq(int(typed.resources.get(name)), int(before.get(name, 0)),
			"the live %s balance is untouched by the derived vector" % name)


## The corpus's own eight-field row at one legacy key, read from its bootstrap
## payload, or null when it cannot be read. Read from the service's own state,
## never from the fake's fixture, because the live side has already executed
## every earlier transaction in this phase.
func _live_row(api: Variant, endpoint: String, user_id: String,
		item_index: int) -> Variant:
	var raw: Dictionary = await _live_payload(api, endpoint, user_id)
	if raw.is_empty():
		return null
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var row: Variant = (map.get("items", {}) as Dictionary).get(str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		check(false, "the live corpus row at key %d is an eight-field array"
			% item_index)
		return null
	return (row as Array).duplicate()


## The corpus's own seven stored balances under the typed resource names the
## response carries, read from its bootstrap payload. This is the pre-request
## reference the live value-level proof compares against — read from the
## service's own state, never from the fake's fixture.
func _live_resources(api: Variant, endpoint: String,
		user_id: String) -> Dictionary:
	var raw: Dictionary = await _live_payload(api, endpoint, user_id)
	if raw.is_empty():
		return {}
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var player: Dictionary = raw.get("playerInfo", {}) as Dictionary
	var priv: Dictionary = raw.get("privateState", {}) as Dictionary
	return {
		"gold": int(map.get("gold", 0)),
		"wood": int(map.get("wood", 0)),
		"oil": int(map.get("oil", 0)),
		"steel": int(map.get("steel", 0)),
		"xp": int(map.get("xp", 0)),
		"cash": int(player.get("cash", 0)),
		"mana": int(priv.get("mana", 0)),
	}


## The corpus's own bootstrap payload, or {} when it cannot be read.
func _live_payload(api: Variant, endpoint: String, user_id: String) -> Dictionary:
	api.configure("legacy_v0", endpoint)
	var boot: Variant = await api.get_bootstrap(user_id)
	if not (boot is BootData.BootstrapResult) or not bool(boot.ok):
		check(false, "the live corpus bootstrap resolves")
		return {}
	var info: Variant = (boot as BootData.BootstrapResult).player_info
	if info == null:
		check(false, "the live corpus payload is readable")
		return {}
	return (info as BootData.PlayerInfoPayload).raw


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


## The on-screen collection readout line ("" when no panel exists or the row's
## item records no committed income).
func _collect_readout_label(town: Variant) -> String:
	var panel: Variant = _surface_panel(town)
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "collect":
			return (child as Label).text
	return ""


## The depth-topmost rendered object covering a cell (the same rule the press
## path applies: the last object in draw order wins), or null.
func _object_for_cell(town: Variant, cell: Vector2i) -> Variant:
	var hit: Variant = null
	for object: Variant in town.objects:
		if object != null and object.contains_cell(cell):
			hit = object
	return hit


## The committed draw order as one `item@cell` string per object, so a run can
## prove that a collection changed no object's identity and left every object's
## committed DEPTH POSITION alone.
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


## One typed `BootData.Placement` back in the legacy eight-field array.
func _boot_row(entry: Variant) -> Array:
	if entry == null or not (entry is BootData.Placement):
		return []
	var typed: BootData.Placement = entry
	return [typed.item_id, typed.x, typed.y, typed.timestamp,
		typed.orientation, typed.store, typed.attr, typed.player]


## Deterministic serialization of every committed state field (the
## byte-identity oracle for the cancelled-collection and failure paths),
## including the typed construction state and the collection clock of every row
## — so a cancellation or a failure that quietly changed a row's instant can
## never look byte-identical.
func _state_snapshot(state: Variant) -> String:
	var rows: Array = []
	for placement in state.placements:
		rows.append({
			"raw": placement.raw,
			"clicks": placement.clicks,
			"countdown": placement.countdown,
			"started_at": placement.started_at,
			"collected_at": placement.collected_at,
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
