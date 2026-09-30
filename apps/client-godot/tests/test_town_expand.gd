extends "res://tests/test_base.gd"
## Expand suite (building-expand, spec "Expansion flow").
##
## Scenarios:
##   helpers     the pure helpers in `expand_flow.gd` (the committed schedule's
##               id space and free range, `price_of`, the derived DEBIT, the
##               three purchasability conditions, `can_afford`, `next_purchasable`,
##               the refusal reasons, the debit/owned/readout text, and the
##               schedule summary) over free, priced, owned, blocked, and
##               unaffordable entries — with an explicit ledger and balances and
##               no node, request, or clock anywhere in the module;
##   readout     the expansion readout renders for every ownership and
##               affordability state (an empty ledger, a partly-owned ledger, an
##               exhausted one, a missing ledger) and shows the committed
##               schedule summary, the owned ids, and the next purchasable entry
##               with its DERIVED cost and affordability;
##   gating      the map-level surface offers an `Expand` action in its OWN
##               UI-foundation slot — beside the delivered selection-driven
##               panel, never inside it (design D7/D8: an expansion names NO
##               placement) — only when the town is built, a map is selected, the
##               committed schedule resolves, and the next purchasable entry
##               actually offers an expansion; and none of the six delivered
##               modes' behavior changes;
##   refusals    an out-of-range id, an already-owned id, a requirement-blocked
##               id, and an unaffordable id are each refused by name with NO
##               request; the seven modes never stack in either direction; and a
##               re-evaluation that changed refuses the confirm instead of
##               sending something the service would reject;
##   cancel      a cancelled expansion sends nothing and leaves the town, the
##               owned ledger, the readout, the storage view, and the resources
##               byte-identical;
##   apply       one confirmed intent sends exactly one request and applies ONLY
##               the authoritative response — the owned ledger taken from the
##               response's `expansions_after`, the balances and experience
##               taken from the response's `resources`, and the RESPONSE winning
##               where the client's own view and derivation disagree — with the
##               placement count, the object count, the committed draw order, and
##               every cell byte-identical, because an expansion has NO land
##               effect (design D4);
##   failures    a transport failure (the refused loopback endpoint) and a
##               post-state the apply rejects (a response whose ledger is not
##               this client's transaction) each surface their own explicit
##               error with the ledger, the balances, and the HUD unchanged;
##   no-land     the expand module and the expand flow section of the view carry
##               no terrain, grid, cell, footprint, or placement-bound code at
##               all — the recorded known evidence gap, asserted structurally as
##               well as at runtime;
##   no-request  the whole run issues no bootstrap request (the state derives
##               from the fixture in hand and the flow never re-bootstraps).
##
## Uses the committed bootstrap and expand fixtures directly; no fixture is
## ever written and no server runs. Runs headless as part of
## `verify-boot.ps1`. The `--scenario=live-expand` run is the `expand-live`
## phase: one expansion against the real Compatibility endpoint, its
## two-part value-level post-state proof, and a refused expansion that leaves
## the corpus byte-identical.
##
## **Two refusals are not reachable through the view on this corpus, and are
## covered where they ARE reachable instead.** The requirements rule (design D3)
## leaves only the free indexes `0..3` purchasable, and a free row's derived
## debit is the all-zero vector, so an unaffordable purchase cannot be produced
## from committed content at all: `insufficient_resources` is covered at the
## pure-helper level over a crafted schedule and against the fake double
## (whose in-memory config table the fake suite stubs, exactly the way the
## collect suite stubs a config accessor for `capped_collection`).

const TownState = preload("res://scripts/town/town_state.gd")
const Iso = preload("res://scripts/town/iso.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const ExpandFlow = preload("res://scripts/town/expand_flow.gd")

const PLAYER_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const EXPAND_FLOW_SOURCE := "res://scripts/town/expand_flow.gd"
const TOWN_SOURCE := "res://scripts/town/town.gd"

## The executed-legacy transaction this suite reproduces (fixture facts,
## recorded against the committed expand capture): expansion id 0, a **free**
## row of the 98-entry positional `expansion_prices` schedule, appended ONCE at
## the END of the corpus's own ledger `[35, 36, 45, 46]`, with the derived
## all-zero debit — so all seven stored resources, all 40 placements, the level,
## the storage, the private state, and the player info stay byte-identical.
## Exactly one leaf of the whole save differs: `/maps/0/expansions/4`.
const EXPAND_ID := 0
const FREE_LAST_ID := 3
const SCHEDULE_ENTRIES := 98
const LAST_ID := 97
const CORPUS_OWNED := [35, 36, 45, 46]
const EXPAND_OWNED_AFTER := [35, 36, 45, 46, 0]
const FREE_PRICE := {"coins": 0, "cash": 0, "neighbors": 0, "inventory_qte": 0}
const FREE_DEBIT := [0, 0, 0, 0, 0, 0, 0, 0]
## The corpus's own seven stored balances, which the all-zero debit never moves.
const FRESH_XP := 4
const FRESH_GOLD := 2000
const FRESH_WOOD := 2000
const FRESH_CASH := 5
const FRESH_MANA := 0
const PLACEMENTS := 40
## A placed, still-present building whose cell the capture and the report select
## so the selection-driven surface is live. An expansion names NO placement:
## the selection exists only because this map-level surface is reached through
## the delivered press path.
const SELECT_CELL := Vector2i(53, 39)
const SELECT_ITEM := 905
## The second still-present building, used for the mutual-exclusion direction
## where a delivered mode arms first.
const SPARE_CELL := Vector2i(58, 48)
const SPARE_ITEM := 22
## The Wall I at its saved cell — the only corpus row the delivered `Upgrade`
## action accepts, because it is the only one with a resolvable next tier. The
## expansion line changes nothing about that rule; it is named here so the
## exclusion direction can cover the sixth delivered mode honestly.
const UPGRADE_CELL := Vector2i(45, 49)
const UPGRADE_ITEM := 23
## The committed rows that are (a) priced, (b) requirement-blocked, and (c) the
## index the whole schedule first saturates at. Row 4 is the cheapest non-zero
## row and row 97 the last, so both bounds of the derived price are covered.
const PRICED_ID := 4
const PRICED_PRICE := {"coins": 2500, "cash": 5, "neighbors": 1,
	"inventory_qte": 1}
const PRICED_DEBIT := [0, 0, -2500, 0, 0, 0, -5, 0]
const SATURATED_ID := 97
const SATURATED_PRICE := {"coins": 100000, "cash": 20, "neighbors": 15,
	"inventory_qte": 30}
const SATURATED_DEBIT := [0, 0, -100000, 0, 0, 0, -20, 0]
## The first index the whole row reads at its final value — the schedule's
## `inventory_qte` saturation, which is the last of the four fields to reach it.
const SATURATION_INDEX := 33
## An id the committed schedule does not price, and a negative one (which the
## service refuses structurally rather than resolving to the schedule's LAST
## row, as Python indexing otherwise would).
const OUT_OF_RANGE_ID := 98
const NEGATIVE_ID := -1
## The cell the crafted-ledger scenarios park their selection at.
const GHOST_CELL := Vector2i(20, 20)
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
	if scenario == "live-expand":
		# verify-boot's expand-live phase: one expansion through the real
		# Compatibility endpoint; the phase harness asserts the disposable
		# corpus save mutated, this scenario asserts the typed response, its
		# TWO-part value-level post-state proof, and that a refused expansion
		# left the corpus byte-identical. Everything else here is fixture-fake
		# only.
		await _check_live_expand()
		return
	_check_pure_helpers()
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return
	await _check_flow(payload)
	_check_no_land_code()
	_check_no_second_bootstrap_request()


# ---------------------------------------------------------------------------
# Pure helpers (task 4.2, design D7)
# ---------------------------------------------------------------------------


## The committed schedule, read through the typed content package's own
## `expansion_prices` domain — the SAME table the view derives from and the
## service derives from, so every helper check below runs against real
## committed rows rather than a restatement of them.
func _committed_schedule(registry: Variant) -> Array:
	if registry == null or not bool(registry.is_loaded()) \
			or not registry.has_domain("expansion_prices"):
		check(false, "the committed expansion_prices domain is loaded")
		return []
	var schedule: Array = []
	var size: int = registry.count("expansion_prices")
	for id in range(size):
		var row: Dictionary = registry.get_entry("expansion_prices", str(id))
		check(bool(row.get("found", false)),
			"the committed schedule prices index %d positionally" % id)
		if not bool(row.get("found", false)):
			return schedule
		schedule.append((row.get("entry", {}) as Dictionary).duplicate())
	return schedule


## The pure helpers over the REAL committed schedule (read through the typed
## content package) and over a crafted copy that reaches what the committed
## table cannot. Everything here takes the schedule, the ledger, and the
## balances as parameters and reads no clock, so the same inputs always produce
## the same verdict, debit, and text.
func _check_pure_helpers() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	if not bool(registry.assets_loaded()):
		registry.load_asset_registry()
	var rows: Array = _committed_schedule(registry)
	if rows.size() != SCHEDULE_ENTRIES:
		check(false, "the committed schedule holds %d rows, not %d"
			% [rows.size(), SCHEDULE_ENTRIES])
		return
	# The committed id space: 98 POSITIONAL rows, no stable id, so the INDEX is
	# the id (design D1, derived) and the addressable range is 0..97.
	check_eq(ExpandFlow.SCHEDULE_ENTRIES, SCHEDULE_ENTRIES,
		"the flow mirrors the committed schedule's 98 positional entries")
	check_eq(ExpandFlow.FIRST_ID, 0, "the addressable range starts at 0")
	check_eq(ExpandFlow.LAST_ID, LAST_ID, "the addressable range ends at 97")
	check_eq(ExpandFlow.FIRST_FREE_ID, 0, "the free index range starts at 0")
	check_eq(ExpandFlow.LAST_FREE_ID, FREE_LAST_ID,
		"the free index range ends at 3 — the only purchasable entries")
	check_eq(ExpandFlow.VECTOR_SLOTS, 8,
		"the derived debit is the documented eight-slot legacy vector")
	check_eq(ExpandFlow.GOLD_SLOT, 2,
		"the schedule's gold-named field lands in the gold slot (design D2)")
	check_eq(ExpandFlow.CASH_SLOT, 6, "its cash field lands in the cash slot")
	check_eq(ExpandFlow.ALWAYS_ZERO_SLOTS, [0, 1, 3, 4, 5, 7],
		"the six slots an expansion debit can never fill are named")
	check_eq(ExpandFlow.NO_EXPANSION, -1,
		"'no purchasable entry' is a sentinel that is never a real id")
	check_eq(ExpandFlow.expand_label(), "Expand",
		"the action's own label names the exact intent it sends")

	# An unreadable schedule is refused, never treated as an empty one — an
	# empty schedule would silently offer nothing and look like an exhausted
	# ledger.
	check_eq(ExpandFlow.schedule_size(null), -1,
		"an absent schedule is the explicit sentinel, never a guessed zero")
	check_eq(ExpandFlow.schedule_size([]), -1,
		"an empty schedule is refused, not read as 'nothing is purchasable'")
	check_eq(ExpandFlow.schedule_size("nope"), -1,
		"a non-array schedule is refused")
	var summary: Dictionary = ExpandFlow.schedule_summary(rows)
	check(bool(summary.get("ok", false)),
		"the committed schedule summarizes: %s" % summary.get("error"))
	check_eq(int(summary["entries"]), SCHEDULE_ENTRIES,
		"the summary records the committed entry count")
	check_eq([int(summary["first_id"]), int(summary["last_id"])], [0, LAST_ID],
		"the summary records the addressable id range")
	check_eq([int(summary["free_first_id"]), int(summary["free_last_id"])],
		[0, FREE_LAST_ID], "the summary records the free index range")
	check_eq(int(summary["free"]), 4,
		"exactly four committed rows are free (indexes 0..3)")
	check_eq(int(summary["purchasable"]), 4,
		"only the free rows are purchasable under the requirements rule (D3)")
	check_eq(int(summary["requirement_blocked"]), SCHEDULE_ENTRIES - 4,
		"94 of the 98 committed rows record a positive requirement and are "
		+ "refused")
	check_eq(summary["saturation"],
		{"coins": 14, "cash": 11, "neighbors": 18, "inventory_qte": 33},
		"the per-field saturation indexes are read from the schedule itself")
	check(not bool(ExpandFlow.schedule_summary(null).get("ok", true)),
		"an unreadable schedule summarizes as a refusal, not as an empty one")

	# The free row: all four fields zero, so the derived debit is the ALL-ZERO
	# vector, which is legal.
	var free_priced := ExpandFlow.price_of(rows, EXPAND_ID)
	check(bool(free_priced.get("ok", false)),
		"the committed schedule prices id %d: %s" % [EXPAND_ID,
			free_priced.get("error")])
	check_eq(free_priced["row"], FREE_PRICE,
		"the free row records all four fields zero")
	check_eq(ExpandFlow.debit_for(free_priced["row"]), FREE_DEBIT,
		"a free row derives the all-zero eight-slot debit")
	check_eq(ExpandFlow.debit_text(FREE_DEBIT), "free",
		"a free row's derived debit reads as free rather than as an empty list")
	check_eq(ExpandFlow.unmet_requirements(free_priced["row"]), [],
		"a free row records no unmet requirement")

	# A priced row: the debit's SIGN and SHAPE, and the two slots it fills.
	var priced := ExpandFlow.price_of(rows, PRICED_ID)
	check_eq(priced["row"], PRICED_PRICE,
		"index 4 is the committed 2500/5/1/1 row")
	check_eq(ExpandFlow.debit_for(priced["row"]), PRICED_DEBIT,
		"a row priced coins C and cash K derives [0, 0, -C, 0, 0, 0, -K, 0]")
	check_eq(ExpandFlow.debit_text(PRICED_DEBIT), "2500 gold, 5 cash",
		"the derived debit reads as the amounts and resources it charges")
	for index: int in ExpandFlow.ALWAYS_ZERO_SLOTS:
		check_eq(int((ExpandFlow.debit_for(priced["row"]) as Array)[index]), 0,
			"slot %d of a priced debit stays zero" % index)
	check(int((ExpandFlow.debit_for(priced["row"]) as Array)[2]) < 0
			and int((ExpandFlow.debit_for(priced["row"]) as Array)[6]) < 0,
		"a priced debit is a DEBIT: the gold and cash entries are negative")
	check_eq(ExpandFlow.debit_for(null), null,
		"an unusable row derives no debit at all")
	check_eq(ExpandFlow.debit_for({"coins": -1, "cash": 0, "neighbors": 0,
		"inventory_qte": 0}), null,
		"a negative committed cost derives no debit (it would be a credit)")
	# The last row: the schedule's top price, so the derived debit's magnitude
	# is bounded by the committed table.
	var saturated := ExpandFlow.price_of(rows, SATURATED_ID)
	check_eq(saturated["row"], SATURATED_PRICE,
		"index 97 is the committed saturated row")
	check_eq(ExpandFlow.debit_for(saturated["row"]), SATURATED_DEBIT,
		"the saturated row derives the largest committed debit")
	check_eq(ExpandFlow.price_of(rows, SATURATION_INDEX)["row"]["inventory_qte"],
		30, "the schedule's last saturation index reads its final value")
	# Out of the schedule's range, and an unusable table.
	var beyond := ExpandFlow.price_of(rows, OUT_OF_RANGE_ID)
	check(not bool(beyond.get("ok", true)),
		"an id outside the committed range is not priced")
	check_eq(str(beyond.get("reason", "")), ExpandFlow.REASON_NOT_PURCHASABLE,
		"an out-of-range id names the not-purchasable reason")
	var negative := ExpandFlow.price_of(rows, NEGATIVE_ID)
	check(not bool(negative.get("ok", true)),
		"a negative id is not priced (Python would resolve it to the LAST row)")
	var unreadable := ExpandFlow.price_of(null, EXPAND_ID)
	check_eq(str(unreadable.get("reason", "")),
		ExpandFlow.REASON_UNREADABLE_SCHEDULE,
		"an unreadable schedule names its own condition")

	# `is_purchasable` over the three non-economic conditions, in order.
	var free_owned := ExpandFlow.is_purchasable(rows, EXPAND_ID, CORPUS_OWNED)
	check(bool(free_owned.get("purchasable", false)),
		"the free row is purchasable on the corpus's own ledger: %s"
			% free_owned.get("error"))
	check_eq(str(free_owned.get("reason", "")), "",
		"a purchasable entry names no refusal reason")
	check_eq(free_owned["debit"], FREE_DEBIT,
		"a purchasable entry carries the derived debit the confirm will name")
	var repeat := ExpandFlow.is_purchasable(rows, EXPAND_ID, [0])
	check(not bool(repeat.get("purchasable", true)),
		"an id the ledger already contains is never purchasable")
	check_eq(str(repeat.get("reason", "")),
		ExpandFlow.REASON_ALREADY_EXPANDED,
		"a repeat names the already-expanded reason (the legacy server neither "
		+ "orders nor deduplicates the ledger, so a repeat would corrupt it)")
	var blocked := ExpandFlow.is_purchasable(rows, PRICED_ID, CORPUS_OWNED)
	check(not bool(blocked.get("purchasable", true)),
		"a requirement-blocked row is never purchasable")
	check_eq(str(blocked.get("reason", "")),
		ExpandFlow.REASON_REQUIREMENTS_UNMET,
		"a positive neighbor or inventory requirement names the requirements "
		+ "refusal (design D3)")
	# Every id the corpus owns sits in the refused set — the readout's
	# owned-and-not-repurchasable case, asserted rather than hidden.
	for id: int in CORPUS_OWNED:
		var owned_verdict := ExpandFlow.is_purchasable(rows, id, CORPUS_OWNED)
		check(not bool(owned_verdict.get("purchasable", true)),
			"the corpus's own owned id %d is not purchasable" % id)
		check(str(owned_verdict.get("reason", "")) != "",
			"the corpus's own owned id %d names why it is not purchasable" % id)

	# `next_purchasable` over the ownership states, scanning the schedule in
	# its own positional order.
	check_eq(int(ExpandFlow.next_purchasable(rows, [])["id"]), EXPAND_ID,
		"an empty ledger's next purchasable entry is the first free row")
	check_eq(int(ExpandFlow.next_purchasable(rows, CORPUS_OWNED)["id"]),
		EXPAND_ID,
		"the corpus's ledger does not contain any free row, so the next entry is 0")
	check_eq(int(ExpandFlow.next_purchasable(rows, [0])["id"]), 1,
		"owning the first free row moves the next entry to the next one")
	check_eq(int(ExpandFlow.next_purchasable(rows, [0, 1, 2, 3])["id"]),
		ExpandFlow.NO_EXPANSION,
		"a ledger holding every free row leaves nothing purchasable")
	var exhausted := ExpandFlow.next_purchasable(rows, [0, 1, 2, 3])
	check_eq(str(exhausted.get("reason", "")),
		ExpandFlow.REASON_NOT_PURCHASABLE,
		"an exhausted ledger names the not-purchasable reason")
	var unreadable_next := ExpandFlow.next_purchasable(null, [])
	check(not bool(unreadable_next.get("ok", true)),
		"an unreadable schedule has no next entry at all")
	check_eq(int(unreadable_next.get("id", 0)), ExpandFlow.NO_EXPANSION,
		"an unreadable schedule returns the no-entry sentinel")

	# Affordability, and the refusal a short balance produces. The committed
	# schedule cannot produce a purchasable priced row, so a CRAFTED one is used
	# here — the pure-helper half of a refusal the committed content cannot
	# reach, the same shape the collect suite uses for its cap rule.
	var crafted: Array = rows.duplicate(true)
	(crafted[PRICED_ID] as Dictionary)["neighbors"] = 0
	(crafted[PRICED_ID] as Dictionary)["inventory_qte"] = 0
	var crafted_buyable := ExpandFlow.is_purchasable(crafted, PRICED_ID,
		CORPUS_OWNED)
	check(bool(crafted_buyable.get("purchasable", false)),
		"a row recording no requirement is purchasable (the rule is the "
		+ "requirements, not the price): %s" % crafted_buyable.get("error"))
	var rich := {"gold": 100000, "cash": 20, "wood": 0, "oil": 0,
		"steel": 0, "mana": 0, "xp": FRESH_XP}
	check(ExpandFlow.can_afford(crafted_buyable["debit"], rich),
		"a balance covering the derived debit is affordable")
	var short := {"gold": PRICED_PRICE["coins"] - 1,
		"cash": PRICED_PRICE["cash"], "wood": 0, "oil": 0, "steel": 0,
		"mana": 0, "xp": FRESH_XP}
	check(not ExpandFlow.can_afford(crafted_buyable["debit"], short),
		"a gold balance one short of the derived debit is NOT affordable")
	check_eq(ExpandFlow.unaffordable_resource(crafted_buyable["debit"], short),
		"gold", "the refusal names the resource that is short")
	var no_cash := {"gold": PRICED_PRICE["coins"], "cash": 0, "wood": 0,
		"oil": 0, "steel": 0, "mana": 0, "xp": FRESH_XP}
	check(not ExpandFlow.can_afford(crafted_buyable["debit"], no_cash),
		"a cash balance below the derived debit is NOT affordable either")
	check_eq(ExpandFlow.unaffordable_resource(crafted_buyable["debit"], no_cash),
		"cash", "the refusal names cash when cash is the short resource")
	# The exact boundary from BOTH sides, the clamp's own reachability, and the
	# refusal that replaces it (design D6).
	var exact := {"gold": PRICED_PRICE["coins"], "cash": PRICED_PRICE["cash"],
		"wood": 0, "oil": 0, "steel": 0, "mana": 0, "xp": FRESH_XP}
	check(ExpandFlow.can_afford(crafted_buyable["debit"], exact),
		"a balance EXACTLY equal to the derived debit is affordable")
	var over := {"gold": -1, "cash": 0, "wood": 0, "oil": 0, "steel": 0,
		"mana": 0, "xp": FRESH_XP}
	check(not ExpandFlow.can_afford(crafted_buyable["debit"], over),
		"a balance the debit would drive negative is refused rather than "
		+ "clamped (design D6: the recorded probe showed the clamp reachable — "
		+ "a client-sent gold debit larger than the balance landed on zero)")
	check(ExpandFlow.can_afford(FREE_DEBIT, over),
		"a free row's all-zero debit is affordable against ANY balance, "
		+ "because it charges nothing at all")
	check(not ExpandFlow.can_afford("nope", rich),
		"a non-vector debit is never affordable")
	check(not ExpandFlow.can_afford(FREE_DEBIT, null),
		"absent balances are never affordable")

	# `evaluate` over every state, and `offers_expand` as the single predicate.
	var armed := ExpandFlow.evaluate(rows, CORPUS_OWNED, rich, EXPAND_ID)
	check(bool(armed.get("ok", false)) and ExpandFlow.offers_expand(armed),
		"the free row offers an expansion on the corpus's own state: %s"
			% armed.get("error"))
	check_eq(armed["debit"], FREE_DEBIT,
		"the evaluation carries the derived debit")
	check(bool(armed.get("affordable", false)),
		"a free row is always affordable")
	check_eq(int(armed.get("owned_count", -1)), 4,
		"the evaluation reports how many ids the ledger already holds")
	for entry: Array in [[rows, CORPUS_OWNED, rich, OUT_OF_RANGE_ID,
			ExpandFlow.REASON_NOT_PURCHASABLE],
			[rows, [0], rich, EXPAND_ID, ExpandFlow.REASON_ALREADY_EXPANDED],
			[rows, CORPUS_OWNED, rich, PRICED_ID,
				ExpandFlow.REASON_REQUIREMENTS_UNMET],
			[crafted, CORPUS_OWNED, short, PRICED_ID,
				ExpandFlow.REASON_INSUFFICIENT_RESOURCES]]:
		var verdict: Dictionary = ExpandFlow.evaluate(entry[0], entry[1],
			entry[2], int(entry[3]))
		check(bool(verdict.get("ok", false)),
			"the %s evaluation is a verdict, not a structural rejection"
				% str(entry[4]))
		check_eq(str(verdict.get("reason", "")), str(entry[4]),
			"the evaluation names the %s refusal" % str(entry[4]))
		check(not ExpandFlow.offers_expand(verdict),
			"a %s refusal offers no expansion" % str(entry[4]))
		var text := ExpandFlow.refusal_text(verdict)
		check(text != "" and text.contains("not purchasable"),
			"the %s refusal names itself in words: %s" % [str(entry[4]), text])
	check_eq(ExpandFlow.refusal_text(armed), "",
		"an offered expansion produces no refusal text")
	check_eq(ExpandFlow.refusal_text({"ok": false}), "",
		"a structural rejection produces no player-facing text")
	check_eq(ExpandFlow.readout_text({"ok": false}, CORPUS_OWNED, summary), "",
		"a rejected evaluation produces no readout")

	# The readout text over every ownership state it can be in.
	var fresh := ExpandFlow.readout_text(armed, CORPUS_OWNED, summary)
	check(fresh.contains("98 of 98 schedule rows")
			and fresh.contains("purchasable: 4")
			and fresh.contains("owned: 35, 36, 45, 46")
			and fresh.contains("next purchasable: id 0")
			and fresh.contains("derived debit: free")
			and fresh.contains("derived, never observed")
			and fresh.contains("affordable: yes"),
		"the readout names the schedule, the owned ids, the next entry, its "
			+ "derived cost, and affordability: %s" % fresh)
	check_eq(ExpandFlow.owned_text(CORPUS_OWNED), "35, 36, 45, 46",
		"the readout names the ledger in the save's OWN order")
	check_eq(ExpandFlow.owned_text([46, 36, 45, 35]), "46, 36, 45, 35",
		"the readout never reorders the ledger (legacy neither orders nor "
		+ "deduplicates it)")
	check_eq(ExpandFlow.owned_text([35, 35, 36]), "35, 35, 36",
		"the readout never deduplicates the ledger")
	check_eq(ExpandFlow.owned_text([]), "(none)",
		"an empty ledger reads as none — the readout leaves a MISSING ledger "
		+ "to the view, which names it instead")
	var after_owning_free := ExpandFlow.readout_text(
		ExpandFlow.evaluate(rows, [0], rich, 1), [0], summary)
	check(after_owning_free.contains("owned: 0")
			and after_owning_free.contains("next purchasable: id 1"),
		"the readout follows the ledger forward: %s" % after_owning_free)
	var exhausted_readout := ExpandFlow.readout_text(
		ExpandFlow.evaluate(rows, [0, 1, 2, 3], rich,
			ExpandFlow.NO_EXPANSION), [0, 1, 2, 3], summary)
	check(exhausted_readout.contains("next purchasable: none")
			and exhausted_readout.contains("owned: 0, 1, 2, 3"),
		"an exhausted ledger reads as nothing purchasable: %s"
			% exhausted_readout)
	var blocked_readout := ExpandFlow.readout_text(
		ExpandFlow.evaluate(rows, CORPUS_OWNED, rich, PRICED_ID), CORPUS_OWNED,
		summary)
	check(blocked_readout.contains("affordable: no")
			and blocked_readout.contains("neighbour or inventory requirement"),
		"a requirement-blocked entry says so rather than claiming a cost: %s"
			% blocked_readout)
	var unaffordable_readout := ExpandFlow.readout_text(
		ExpandFlow.evaluate(crafted, CORPUS_OWNED, short, PRICED_ID),
		CORPUS_OWNED, summary)
	check(unaffordable_readout.contains("derived debit: 2500 gold, 5 cash")
			and unaffordable_readout.contains("affordable: no"),
		"an unaffordable entry still shows its derived cost and says it is not "
			+ "affordable: %s" % unaffordable_readout)

	# The module itself depends on NO node, request, or clock (task 4.2), so a
	# reader can trust that every derivation above is pure. The transport and
	# runtime token names are assembled from fragments because the
	# project-scope scan looks for their literal forms in this file's bytes.
	var source := _read_source(EXPAND_FLOW_SOURCE)
	check(source != "", "the expand flow module is readable")
	for token in ["get_node", "HTTP" + "Request", "HTTP" + "Client",
			"await ", "Time.", "Time.get_unix", "Engine.", "OS.", "FileAccess",
			"DirAccess", "preload(\"res://scripts/ui"]:
		check(source.find(token) == -1,
			"the pure expansion helpers never reference %s" % token)
	check(source.find("preload(") != -1
			and source.find("boot_data.gd") != -1,
		"the only thing the pure helpers preload is the shared typed result")


# ---------------------------------------------------------------------------
# Expand flow (spec "Expansion flow")
# ---------------------------------------------------------------------------


## The full flow over the committed fixtures: builds the town from the
## fresh-save payload, activates the session for the fake's save, and drives
## arm -> confirm -> apply plus every refusal, failure, cancel, and no-request
## path — and the land-gap assertion that an expansion grows nothing.
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
	check_eq(state.owned_expansions, CORPUS_OWNED,
		"the typed owned-expansions list is the corpus's own ledger, in the "
		+ "save's own order")
	check(not state.missing.has(TownState.EXPANSIONS_MISSING_KEY),
		"a present ledger is never recorded missing")

	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null:
		return
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the expand save")
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
		"the fresh save renders 40 objects before any expansion")

	var requests_start: int = api.expand_requests
	var snapshot_start := _state_snapshot(state)
	_check_gating(town, state, api, requests_start)
	_check_refusals(town, state, api, requests_start, snapshot_start)
	await _check_expanded(town, state, api)
	_check_mutual_exclusion(town, api)
	await _check_transport_failure(registry, api)
	check_eq(api.expand_requests, requests_start + 2,
		"the whole flow issued exactly two requests (one expanded, one "
		+ "transport failure); every other check sent none")
	town.free()

	await _check_cancelled_expand(registry, api)
	await _check_exhausted_ledger(registry, api)
	await _check_requirement_blocked_ledger(registry, api)
	await _check_missing_ledger(registry, api)
	await _check_post_state_rejection(registry, api)


## The map-level surface offers `Expand` in its OWN UI-foundation slot beside
## the delivered selection-driven panel — never inside it (design D7/D8: an
## expansion names NO placement, so a seventh building-targeted row would imply
## a target that does not exist) — and only when the next purchasable entry
## actually offers an expansion.
func _check_gating(town: Node2D, state: Variant, api: Variant,
		requests_before: int) -> void:
	check(not town.expand_active(),
		"the expansion is not armed before a selection")
	check(not town.expand_selection_available(),
		"no selection means no expand action")
	check_eq(town.expand_id(), ExpandFlow.NO_EXPANSION,
		"an unarmed expansion names no id")
	check_eq(town.expand_evaluation(), {},
		"an unarmed expansion has no evaluation")
	check_eq(town.owned_expansions(), CORPUS_OWNED,
		"the readout reads the committed ledger before anything is armed")
	# The press path: the real selection code, no bypass.
	var press: Dictionary = town.handle_pointer_press(
		Iso.grid_to_screen(SELECT_CELL))
	check(bool(press.get("ok", false)),
		"the press selects a map: %s" % press.get("error"))
	check_eq(town.selection_legacy_id(), SELECT_ITEM,
		"the press at (53,39) selects the recorded building")
	check(town.expand_selection_available(),
		"a committed ledger with a purchasable free entry offers the expand "
		+ "action")
	for delivered in ["move_selection_available", "sell_selection_available",
			"store_selection_available", "construction_selection_available"]:
		check(bool(town.call(str(delivered))),
			"the same selection still offers the delivered %s"
				% str(delivered))
	# The surface owns its OWN slot, and the delivered panel keeps exactly the
	# buttons it always had — no seventh building-targeted action.
	check(town.ui.has_slot("expand"),
		"the expansion surface owns its own UI-foundation slot")
	check(town.ui.is_slot_visible("expand"),
		"the expansion slot shows for a committed selection")
	check(town.ui.has_slot("move"),
		"the delivered selection-driven surface still owns its own slot")
	var delivered_panel: Variant = _panel_of(town, "move")
	var delivered_buttons: Array = []
	if delivered_panel != null:
		_collect_buttons(delivered_panel as Node, delivered_buttons)
	var names: Array = []
	for button: Variant in delivered_buttons:
		names.append(String((button as Button).name))
	check_eq(names, ["move", "sell", "store", "upgrade", "build", "collect",
		"confirm", "cancel"],
		"the delivered panel still offers exactly its six actions, one confirm, "
		+ "and one cancel — the expansion action is NOT inside it")
	check_eq(_button_count(town, "expand", "expand"), 1,
		"the expansion slot carries exactly one `Expand` action")
	# The readout renders for the live selection BEFORE anything is armed, and
	# it renders ON SCREEN (the surface owns a line of its own, not just an
	# accessor).
	var readout: String = town.expand_readout()
	check(_expand_readout_label(town) == readout,
		"the expansion readout is rendered on the surface's own line: %s"
			% _expand_readout_label(town))
	check(readout.contains("98 of 98 schedule rows"),
		"the readout names the committed schedule's size: %s" % readout)
	check(readout.contains("purchasable: 4"),
		"the readout names how many rows the requirements rule leaves "
		+ "purchasable: %s" % readout)
	check(readout.contains("owned: 35, 36, 45, 46"),
		"the readout names the player's own ids: %s" % readout)
	check(readout.contains("next purchasable: id 0"),
		"the readout names the next purchasable entry: %s" % readout)
	check(readout.contains("derived debit: free"),
		"the readout names the entry's derived cost: %s" % readout)
	check(readout.contains("affordable: yes"),
		"the readout names affordability: %s" % readout)
	check(not town.move_preview_shown(),
		"an armed-expansion surface shows no footprint preview (it has no "
		+ "grid target)")
	check(town.move_evaluation().is_empty(),
		"the expansion surface commits no move evaluation")

	# The button wiring arms the expansion (the signal path, one `pressed`
	# emission = one arm — no request).
	var panel: Variant = _panel_of(town, "expand")
	check(panel != null, "the expansion surface commits into its slot")
	if panel == null:
		return
	var arm: Variant = _button_named(panel as Node, "expand")
	check(arm is Button, "the expand action button exists")
	if arm is Button:
		check(not (arm as Button).disabled,
			"the expand action is enabled for a purchasable entry")
		check_eq((arm as Button).text, "Expand",
			"the action is labelled Expand")
		(arm as Button).pressed.emit()
	check(town.expand_active(), "pressing the action arms the expansion")
	check_eq(town.expand_id(), EXPAND_ID,
		"the armed expansion names the next purchasable committed id")
	var armed: Dictionary = town.expand_evaluation()
	check_eq(armed.get("debit", []), FREE_DEBIT,
		"the armed evaluation's DERIVED debit is the free row's all-zero vector")
	check(str(armed.get("reason", "")) == "",
		"the armed evaluation names no refusal")
	# Arming REBUILDS the surface, so it is re-read here rather than holding a
	# freed panel — the same rule the delivered collect suite follows.
	panel = _panel_of(town, "expand")
	var selection_text := String(_expand_selection_text(town))
	check(selection_text.contains("expanding id 0")
			and selection_text.contains("derived debit: free"),
		"the selection line names the armed id and its derived debit: %s"
			% selection_text)
	check(selection_text.contains("derived, never observed"),
		"the selection line presents the amount as derived, never observed: %s"
			% selection_text)
	var status := String(town.expand_status())
	check(status.contains("armed") and status.contains("id 0")
			and status.contains("derived"),
		"the status names the armed expansion and its derived amount: %s"
			% status)
	# The confirm exists only while armed, and it carries the mode's OWN label.
	var confirm: Variant = _button_named(panel as Node, "confirm")
	check(confirm is Button and (confirm as Button).visible,
		"the targetless confirm is offered as soon as the expansion is armed")
	if confirm is Button:
		check_eq((confirm as Button).text, "Expand",
			"the confirm names the armed mode's own action")
	check(_button_named(panel as Node, "cancel") != null,
		"the cancel action button exists")
	check_eq(api.expand_requests, requests_before,
		"arming sent no request")
	var again: Dictionary = town.arm_expand()
	check(not bool(again.get("ok", true)),
		"arming an already-armed expansion rejects")
	check_eq(str(again.get("code", "")), "expand_already_active",
		"the double-arm names the condition")
	# The seven modes never stack: the armed expansion refuses the six
	# delivered ones by name, and every refusal names the ARMED mode — which is
	# the expansion, never the one the player tried to arm.
	for entry: Array in [["arm_move", "an expansion is armed"],
			["arm_sell", "an expansion is armed"],
			["arm_store", "an expansion is armed"],
			["arm_upgrade", "an expansion is armed"],
			["arm_construction", "an expansion is armed"],
			["arm_collect", "an expansion is armed"]]:
		var refused: Dictionary = await town.call(str(entry[0]))
		check(not bool(refused.get("ok", true)),
			"%s while an expansion is armed rejects" % str(entry[0]))
		check_eq(str(refused.get("code", "")), "expand_already_active",
			"the stacked-arm refusal of %s names the armed expansion: %s"
				% [str(entry[0]), refused.get("error")])
		check(String(refused.get("error", "")).contains(str(entry[1])),
			"the stacked-arm refusal of %s says what is armed: %s"
				% [str(entry[0]), refused.get("error")])
	check_eq(api.expand_requests, requests_before,
		"every stacked-arm refusal sent no request")
	check(town.expand_active(),
		"the refusals never disarm the expansion in progress")
	var released: Dictionary = town.cancel_expand()
	check(bool(released.get("ok", false)),
		"the expansion closes for the applied check: %s"
			% released.get("error"))


## Every local refusal confirms with no request, no state change, and the
## explicit error naming its own condition.
func _check_refusals(town: Node2D, state: Variant, api: Variant,
		requests_before: int, snapshot_before: String) -> void:
	var closed: Dictionary = await town.confirm_expand()
	check(not bool(closed.get("ok", true)),
		"a closed expansion refuses a confirm")
	check_eq(str(closed.get("code", "")), "expand_not_active",
		"the closed-expansion refusal names the condition")
	check_eq(api.expand_requests, requests_before,
		"the closed-expansion refusal sent no request")
	check_eq(town.expand_id(), ExpandFlow.NO_EXPANSION,
		"a closed expansion names no id")
	check(town.expand_evaluation().is_empty(),
		"a closed expansion has no evaluation")

	# Re-select the recorded cell and arm once more for the re-evaluation
	# refusal: the ledger changes under the armed id, so the confirm must refuse
	# by name instead of sending something the service would reject.
	town.handle_pointer_press(Iso.grid_to_screen(SELECT_CELL))
	var armed: Dictionary = town.arm_expand()
	check(bool(armed.get("ok", false)),
		"the expansion re-arms: %s" % armed.get("error"))
	check_eq(api.expand_requests, requests_before, "re-arming sent no request")
	town.state.owned_expansions = [0, 35, 36, 45, 46]
	var re_targeted: Dictionary = await town.confirm_expand()
	check(not bool(re_targeted.get("ok", true)),
		"a confirm whose ledger changed refuses")
	check_eq(str(re_targeted.get("code", "")),
		ExpandFlow.REASON_ALREADY_EXPANDED,
		"the re-evaluation refusal names the already-expanded condition: %s"
			% re_targeted.get("error"))
	check_eq(api.expand_requests, requests_before,
		"the re-evaluation refusal sent no request")
	check(town.expand_active(),
		"the expansion survives its own re-evaluation refusal")
	town.state.owned_expansions = (CORPUS_OWNED as Array).duplicate()
	check_eq(_state_snapshot(state), snapshot_before,
		"the refusal paths change no state")
	check_eq(town.objects.size(), PLACEMENTS,
		"the refusal paths render nothing")
	var closed_armed: Dictionary = town.cancel_expand()
	check(bool(closed_armed.get("ok", false)),
		"the refusal-armed expansion closes cleanly: %s"
			% closed_armed.get("error"))


## The expanded town: one confirmed intent sending exactly one request and
## applying ONLY the authoritative response. The ledger and the balances are the
## RESPONSE's values; the client's own derived debit is discarded, never added.
## And nothing about the TOWN changes: same placements, same objects, same draw
## order, same cells (design D4).
func _check_expanded(town: Node2D, state: Variant, api: Variant) -> void:
	town.handle_pointer_press(Iso.grid_to_screen(SELECT_CELL))
	check(town.selection_legacy_id() == SELECT_ITEM,
		"the recorded building is the committed selection again")
	var object: Variant = _object_for_cell(town, SELECT_CELL)
	check(object != null, "the recorded object is committed before the expansion")
	var armed: Dictionary = town.arm_expand()
	check(bool(armed.get("ok", false)),
		"the expansion arms: %s" % armed.get("error"))
	if not bool(armed.get("ok", false)):
		return
	check_eq(armed.get("debit", []), FREE_DEBIT,
		"the armed expansion's DERIVED debit is the free row's all-zero vector")
	check_eq(armed.get("owned", []), CORPUS_OWNED,
		"the armed expansion reports the ledger it checked against")
	# The RESPONSE-WINS setup: the client's own view of the gold balance is
	# moved away from the value the service holds, so a client that applied its
	# OWN arithmetic — or kept its own balance — would differ from the response.
	state.resources.coins = 4242
	var requests_before: int = api.expand_requests
	var signature_before := _object_signature(town)
	var storage_before: Dictionary = (state.storage as Dictionary).duplicate()
	var confirmed: Dictionary = await town.confirm_expand()
	check(bool(confirmed.get("ok", false)),
		"the confirmed expansion succeeds: %s" % confirmed.get("error"))
	check_eq(api.expand_requests, requests_before + 1,
		"exactly one request carried the intent")
	if not bool(confirmed.get("ok", false)):
		return
	_check_typed_expand(confirmed.get("result"))
	# The authoritative apply: the ledger is the RESPONSE's, appended once at
	# the END, and the client's own view is gone.
	check_eq(town.owned_expansions(), EXPAND_OWNED_AFTER,
		"the applied ledger is the response's own expansions_after")
	check_eq(state.owned_expansions, EXPAND_OWNED_AFTER,
		"the typed state's ledger is the response's, not a local append")
	check_eq(town.owned_expansions().size(), CORPUS_OWNED.size() + 1,
		"the ledger grew by exactly one entry")
	for index in range(CORPUS_OWNED.size()):
		check_eq(int(town.owned_expansions()[index]),
			int(CORPUS_OWNED[index]),
			"ledger entry %d is unchanged and still in order" % index)
	check_eq(int(town.owned_expansions()[CORPUS_OWNED.size()]), EXPAND_ID,
		"the sent id is appended AT THE END")
	# The RESPONSE wins: the balances and experience are the response's values,
	# applied verbatim, never the client's own arithmetic and never the client's
	# own pre-request balance.
	check_eq(state.resources.coins, FRESH_GOLD,
		"the gold balance takes the RESPONSE's value (4242 was the client's "
		+ "own view and is discarded — the response wins)")
	check_eq(state.resources.wood, FRESH_WOOD,
		"the wood balance takes the response's unchanged value")
	check_eq(state.resources.oil, FRESH_WOOD,
		"the oil balance takes the response's unchanged value")
	check_eq(state.resources.steel, FRESH_WOOD,
		"the steel balance takes the response's unchanged value")
	check_eq(state.resources.cash, FRESH_CASH,
		"the cash balance takes the response's unchanged value")
	check_eq(state.resources.mana, FRESH_MANA,
		"the mana balance takes the response's unchanged value")
	check_eq(state.summary.xp, FRESH_XP,
		"the experience takes the response's unchanged value")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD re-attaches to the mutated state")
	if hud != null:
		check_eq(hud.displayed("coins"), str(FRESH_GOLD),
			"the HUD renders the AUTHORITATIVE gold, not the client's own 4242")
		check_eq(hud.displayed("xp"), str(FRESH_XP),
			"the HUD renders the authoritative experience")
	# THE LAND GAP, asserted at runtime: an expansion grows NOTHING.
	check_eq(state.placements.size(), PLACEMENTS,
		"an expansion changes no placement count (no new buildable cell)")
	check_eq(town.objects.size(), PLACEMENTS,
		"an expansion renders no object")
	check_eq(_object_signature(town), signature_before,
		"an expansion re-sorts nothing and moves no cell: the draw order is "
		+ "byte-identical (design D4)")
	check(_object_for_cell(town, SELECT_CELL) == object,
		"the SAME rendered object is retained at the same cell")
	check(not town.move_preview_shown(),
		"an expansion shows no footprint preview (it has no target)")
	check_eq(state.storage, storage_before, "the storage mapping is untouched")
	check_eq(town.expand_id(), ExpandFlow.NO_EXPANSION,
		"the armed id is released after the apply")
	check(not town.expand_active(), "the expansion closes after the apply")
	check_eq(town.expand_error, "", "success leaves no failure record")
	# The readout re-renders from the RESPONSE's ledger, so the next purchasable
	# entry moves forward on the surface's own line.
	var readout: String = town.expand_readout()
	check(_expand_readout_label(town) == readout,
		"the on-screen expansion line shows the response's ledger: %s"
			% _expand_readout_label(town))
	check(readout.contains("owned: 35, 36, 45, 46, 0")
			and readout.contains("next purchasable: id 1"),
		"the readout follows the authoritative ledger forward: %s" % readout)
	var status := String(town.expand_status())
	check(status.contains("expanded id 0") and status.contains("free"),
		"the status names what the SERVICE applied: %s" % status)
	# The post-apply state is what an immediately repeated confirm refuses.
	var repeat: Dictionary = await town.confirm_expand()
	check(not bool(repeat.get("ok", true)),
		"a confirm after the apply refuses (the expansion is no longer armed)")
	check_eq(api.expand_requests, requests_before + 1,
		"the post-apply refusal sent no second request")


## The other direction of the seven-mode mutual exclusion: an expansion cannot be
## armed while a delivered mode already is, and the refusal names the ARMED
## mode. Each delivered mode is exercised on a building IT accepts — the
## delivered action's own content rules are untouched by this line, so a row
## whose item records no committed income (a Turret I) legitimately offers no
## `Collect` and a Tree legitimately offers no `Upgrade`, which is why the six
## arms are spread over the three buildings that cover them.
func _check_mutual_exclusion(town: Node2D, api: Variant) -> void:
	var requests_before: int = api.expand_requests
	var entries: Array = [
		["arm_move", "move_already_active", "a move is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_sell", "sell_already_active", "a sale is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_store", "store_already_active", "a store is armed", SPARE_CELL,
			SPARE_ITEM],
		["arm_construction", "construction_already_active", "a build is armed",
			SPARE_CELL, SPARE_ITEM],
		["arm_collect", "collect_already_active", "a collection is armed",
			SELECT_CELL, SELECT_ITEM],
		["arm_upgrade", "upgrade_already_active", "an upgrade is armed",
			UPGRADE_CELL, UPGRADE_ITEM],
	]
	for entry: Array in entries:
		town.handle_pointer_press(Iso.grid_to_screen(entry[3]))
		check(town.selection_legacy_id() == int(entry[4]),
			"the building the delivered %s accepts is selectable"
				% str(entry[0]))
		var armed: Dictionary = await town.call(str(entry[0]))
		check(bool(armed.get("ok", false)),
			"the delivered %s arms on its own building: %s"
				% [str(entry[0]), armed.get("error")])
		if bool(armed.get("ok", false)):
			var over: Dictionary = town.arm_expand()
			check(not bool(over.get("ok", true)),
				"arming an expansion while a %s is armed rejects" % str(entry[0]))
			check_eq(str(over.get("code", "")), str(entry[1]),
				"the refusal names the armed %s: %s"
					% [str(entry[0]), over.get("error")])
			check(String(over.get("error", "")).contains(str(entry[2])),
				"the refusal says what is armed: %s" % over.get("error"))
			var closed: Dictionary = town.call(
				"cancel_" + str(entry[0]).trim_prefix("arm_"))
			check(bool(closed.get("ok", false)),
				"the delivered %s closes again: %s"
					% [str(entry[0]), closed.get("error")])
		check(not town.expand_active(),
			"the refused arming left no expansion armed")
	check_eq(api.expand_requests, requests_before,
		"every mutual-exclusion refusal sent no request")


## LAST scenario (it waits out the refused loopback endpoint): the intent goes
## out over the legacy transport, the endpoint refuses it, and the explicit
## error names `unreachable_endpoint` with the ledger keeping its previous
## contents and no balance moved — the same no-mutation contract as a structured
## failure.
func _check_transport_failure(registry: Variant, api: Variant) -> void:
	var endpoint := _endpoint()
	check(endpoint != "", "a loopback endpoint resolves for the transport "
		+ "scenario")
	if endpoint == "":
		return
	var transport_town: Variant = _selected_town(registry, SELECT_CELL,
		SELECT_ITEM, "the transport town")
	if transport_town == null:
		return
	var requests_before: int = api.expand_requests
	var snapshot_before := _state_snapshot(transport_town.state)
	var objects_before: int = transport_town.objects.size()
	api.configure("legacy_v0", endpoint)
	var armed: Dictionary = transport_town.arm_expand()
	check(bool(armed.get("ok", false)),
		"the transport town arms an expansion: %s" % armed.get("error"))
	var attempt: Dictionary = await transport_town.confirm_expand()
	check(not bool(attempt.get("ok", true)),
		"the refused endpoint fails the intent closed")
	check_eq(str(attempt.get("code", "")), "unreachable_endpoint",
		"the transport failure surfaces its code: %s" % attempt.get("error"))
	check(String(transport_town.expand_error).contains("unreachable_endpoint"),
		"the explicit error names the transport failure")
	check_eq(api.expand_requests, requests_before + 1,
		"the transport attempt sent exactly one request")
	check_eq(_state_snapshot(transport_town.state), snapshot_before,
		"the transport failure changes no state")
	check_eq(transport_town.objects.size(), objects_before,
		"the transport failure renders nothing new")
	check_eq(transport_town.owned_expansions(), CORPUS_OWNED,
		"the transport failure leaves the ledger untouched")
	check(transport_town.expand_active(),
		"the expansion survives the transport failure")
	# The last state-changing check ran against the refused endpoint, so the
	# implementation switch is undone here rather than leaked.
	transport_town.free()
	api.configure("fake")


## The cancelled-expansion contract: arming and closing on a FRESH town leaves
## the serialized town state, the owned ledger, the readout, the storage view,
## the selection, the resources, and the request count byte-identical.
func _check_cancelled_expand(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, SELECT_CELL, SELECT_ITEM,
		"the cancel town")
	if town == null:
		return
	var requests_before: int = api.expand_requests
	var snapshot_before := _state_snapshot(town.state)
	var armed: Dictionary = town.arm_expand()
	check(bool(armed.get("ok", false)),
		"the expansion arms for the cancel: %s" % armed.get("error"))
	var selected_before: int = town.selection_legacy_id()
	var readout_before: String = town.expand_readout()
	var collect_readout_before: String = town.collect_readout()
	var build_readout_before: String = town.construction_readout()
	var cancelled: Dictionary = town.cancel_expand()
	check(bool(cancelled.get("ok", false)),
		"cancel closes the expansion: %s" % cancelled.get("error"))
	check(not town.expand_active(), "the expansion closes")
	check_eq(town.expand_id(), ExpandFlow.NO_EXPANSION,
		"a closed expansion names no id")
	check(not town.ui.is_slot_visible("expand"),
		"the expansion slot hides on cancel")
	check(not town.move_preview_shown(),
		"no preview is displayed by a cancelled expansion")
	check_eq(town.selection_legacy_id(), selected_before,
		"cancel leaves the selection untouched")
	check_eq(town.objects.size(), PLACEMENTS, "cancel renders nothing")
	check_eq(town.expand_readout(), readout_before,
		"cancel leaves the expansion readout untouched")
	check_eq(town.collect_readout(), collect_readout_before,
		"cancel leaves the delivered collection readout untouched")
	check_eq(town.construction_readout(), build_readout_before,
		"cancel leaves the delivered construction readout untouched")
	check(String(town.expand_status()).contains("nothing was sent"),
		"cancel says that nothing was sent: %s" % town.expand_status())
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the serialized town state is byte-identical after cancel")
	check_eq(api.expand_requests, requests_before,
		"cancel sent no request")
	var again: Dictionary = town.cancel_expand()
	check(not bool(again.get("ok", true)),
		"closing an already-closed expansion rejects")
	check_eq(str(again.get("code", "")), "expand_not_active",
		"the double-close names the condition")
	check_eq(api.expand_requests, requests_before,
		"the double-close sent no request")
	# The expansion surface offers the `Expand` action, one confirm, and one
	# cancel — and nothing that clears or rewrites anything (design D4).
	var panel: Variant = _panel_of(town, "expand")
	if panel != null:
		var buttons: Array = []
		_collect_buttons(panel as Node, buttons)
		var names: Array = []
		for button: Variant in buttons:
			names.append(String((button as Button).name))
		check_eq(names, ["expand", "confirm", "cancel"],
			"the expansion surface offers exactly the expand action, one "
			+ "confirm, and one cancel — nothing else")
	town.free()


## An exhausted ledger: owning every FREE row leaves nothing purchasable, so
## the action is never offered, arming is refused by name with the not-
## purchasable reason, and NOTHING is sent — while the ledger itself is
## untouched.
func _check_exhausted_ledger(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, SELECT_CELL, SELECT_ITEM,
		"the exhausted-ledger town", [0, 1, 2, 3])
	if town == null:
		return
	var requests_before: int = api.expand_requests
	var snapshot_before := _state_snapshot(town.state)
	check_eq(town.owned_expansions(), [0, 1, 2, 3],
		"the crafted ledger carries every free row")
	check(not town.expand_selection_available(),
		"a ledger holding every purchasable entry never offers the expand "
		+ "action")
	check_eq(int(town.expand_next().get("id", 0)),
		ExpandFlow.NO_EXPANSION,
		"the next purchasable lookup returns the no-entry sentinel")
	var readout: String = town.expand_readout()
	check(readout.contains("next purchasable: none"),
		"the readout says nothing is purchasable: %s" % readout)
	var refused: Dictionary = town.arm_expand()
	check(not bool(refused.get("ok", true)),
		"arming an exhausted ledger fails")
	check_eq(str(refused.get("code", "")),
		ExpandFlow.REASON_NOT_PURCHASABLE,
		"the refusal names the not-purchasable condition: %s"
			% refused.get("error"))
	check(String(refused.get("error", "")).contains("every purchasable entry"),
		"the explicit error says the ledger is exhausted: %s"
			% refused.get("error"))
	check_eq(api.expand_requests, requests_before,
		"the exhausted-ledger refusal sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the exhausted-ledger refusal changes no state")
	check_eq(town.owned_expansions(), [0, 1, 2, 3],
		"the refused ledger keeps its own contents, in order")
	town.free()


## A ledger whose only entry is requirement-blocked: the readout must show it as
## owned-AND-not-repurchasable and must never offer it, while the next
## purchasable entry stays the free index 0.
func _check_requirement_blocked_ledger(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, SELECT_CELL, SELECT_ITEM,
		"the blocked-ledger town", [35])
	if town == null:
		return
	var requests_before: int = api.expand_requests
	var snapshot_before := _state_snapshot(town.state)
	var readout: String = town.expand_readout()
	check(readout.contains("owned: 35")
			and readout.contains("next purchasable: id 0"),
		"an owned, requirement-blocked id is shown as owned and the free row "
		+ "stays the next entry: %s" % readout)
	check(not readout.contains("next purchasable: id 35"),
		"the readout never offers a requirement-blocked id")
	check(town.expand_selection_available(),
		"a ledger owning only a blocked id still offers the free entry")
	var verdict: Dictionary = ExpandFlow.is_purchasable(
		_pure_schedule(), 35, [])
	check_eq(str(verdict.get("reason", "")),
		ExpandFlow.REASON_REQUIREMENTS_UNMET,
		"the corpus's own owned id is requirement-blocked under the committed "
		+ "schedule (design D3) — it could never have been bought")
	check_eq(api.expand_requests, requests_before,
		"the blocked-ledger readout sent no request")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the blocked-ledger readout changes no state")
	town.free()


## A payload with NO ledger at all: the absence is named rather than presented
## as "this player owns nothing", the action is never offered, and arming is
## refused by name with NO request — because a ledger this contract cannot
## enumerate is a ledger an intent cannot be checked against.
func _check_missing_ledger(registry: Variant, api: Variant) -> void:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return
	var crafted: Dictionary = (payload as Dictionary).duplicate(true)
	(crafted["map"] as Dictionary).erase("expansions")
	var town: Variant = _built_town(crafted, registry, SELECT_CELL, SELECT_ITEM,
		"the missing-ledger town")
	if town == null:
		return
	var requests_before: int = api.expand_requests
	check(town.owned_expansions_missing(),
		"a payload with no ledger records the absence in `missing`")
	check_eq(town.owned_expansions(), [],
		"an absent ledger yields no fabricated entries")
	check(not town.expand_selection_available(),
		"a missing ledger never offers the expand action")
	var refused: Dictionary = town.arm_expand()
	check(not bool(refused.get("ok", true)),
		"arming against a missing ledger fails")
	check_eq(str(refused.get("code", "")), "expand_ledger_missing",
		"the refusal names the missing ledger: %s" % refused.get("error"))
	check(String(refused.get("error", "")).contains(
			TownState.EXPANSIONS_MISSING_KEY),
		"the explicit error names the missing field: %s" % refused.get("error"))
	check_eq(api.expand_requests, requests_before,
		"the missing-ledger refusal sent no request")
	check(town.state.missing.has(TownState.EXPANSIONS_MISSING_KEY),
		"the typed state keeps recording the absence")
	town.free()


## The post-state the apply REJECTS (spec "a post-state the service rejects"):
## the client's own ledger view diverges from the one the service holds, so the
## response's pre-execution ledger is not this client's transaction. The apply
## fails closed BEFORE any mutation, the explicit error names the condition, and
## the request was still sent exactly once (the service genuinely executed it —
## which is why the client must fail closed rather than apply a foreign ledger).
func _check_post_state_rejection(registry: Variant, api: Variant) -> void:
	var town: Variant = _selected_town(registry, SELECT_CELL, SELECT_ITEM,
		"the post-state town", [0, 35, 36, 45, 46])
	if town == null:
		return
	var requests_before: int = api.expand_requests
	var snapshot_before := _state_snapshot(town.state)
	var armed: Dictionary = town.arm_expand()
	check(bool(armed.get("ok", false)),
		"a ledger that already owns id 0 arms id 1: %s" % armed.get("error"))
	check_eq(int(armed.get("id", -99)), 1,
		"the armed expansion names the next FREE id the ledger does not hold")
	var failed: Dictionary = await town.confirm_expand()
	check(not bool(failed.get("ok", true)),
		"a post-state the apply rejects fails the intent closed")
	check_eq(str(failed.get("code", "")), "apply_failed",
		"the rejection names the apply, not the service: %s"
			% failed.get("error"))
	check(String(failed.get("error", "")).contains("pre-execution ledger"),
		"the explicit error names the divergence: %s" % failed.get("error"))
	check_eq(api.expand_requests, requests_before + 1,
		"the rejected intent was still sent exactly once")
	check_eq(_state_snapshot(town.state), snapshot_before,
		"the rejected apply changes NO state at all (the ledger, the balances, "
		+ "and the HUD keep their pre-request values)")
	check_eq(town.owned_expansions(), [0, 35, 36, 45, 46],
		"the client's own ledger is unchanged")
	check(town.expand_active(),
		"the expansion survives its own rejected apply")
	town.free()


## The typed result of one confirmed expansion: protocol, version, legacy
## result, BOTH owned lists, the derived debit, the committed price row, and the
## resources. The wall-clock field is asserted as a positive integer and never
## by value.
func _check_typed_expand(result: Variant) -> void:
	check(result is BootData.ExpandResult,
		"the confirm carries the typed expand result")
	if not (result is BootData.ExpandResult):
		return
	var typed: BootData.ExpandResult = result
	check(typed.ok, "the expand response is a success")
	check_eq(typed.protocol, BootData.PROTOCOL,
		"the expand protocol is compat-v0")
	check_eq(typed.game_version, "alpha 0.02",
		"the expand response carries the game version")
	check(typed.server_time > 0,
		"the expand server_time is the fixture epoch (time-dependent)")
	check_eq(typed.result, "success", "the legacy result string is verbatim")
	check_eq(typed.expansions_before, CORPUS_OWNED,
		"the pre-execution ledger is the corpus's own, in order")
	check_eq(typed.expansions_after, EXPAND_OWNED_AFTER,
		"the post-execution ledger is the sent id appended ONCE at the END")
	check_eq(typed.expansions_after.size(),
		typed.expansions_before.size() + 1,
		"the ledger grew by exactly one entry")
	check_eq(typed.debit, FREE_DEBIT,
		"the derived debit is the documented all-zero eight-slot vector")
	for index: int in BootData.EXPAND_ALWAYS_ZERO_SLOTS:
		check_eq(int(typed.debit[index]), 0,
			"slot %d of the derived debit stays zero" % index)
	check(typed.price != null, "the response carries the committed price row")
	if typed.price != null:
		check_eq([typed.price.coins, typed.price.cash, typed.price.neighbors,
			typed.price.inventory_qte], [0, 0, 0, 0],
			"the committed row for a free id records all four fields zero")
	check(typed.resources != null, "the response carries typed resources")
	if typed.resources == null:
		return
	# The endpoint's OWN two-part post-execution proof, restated on the typed
	# result the client applied (design D5): the ledger grew by exactly the sent
	# id at the end, and every stored resource changed by exactly the derived
	# debit — which, for a free row, is no change at all.
	check_eq(typed.resources.gold, FRESH_GOLD,
		"the gold balance is the fresh save's own value (the derived debit is "
		+ "the all-zero vector)")
	check_eq(typed.resources.wood, FRESH_WOOD, "wood is unchanged")
	check_eq(typed.resources.oil, FRESH_WOOD, "oil is unchanged")
	check_eq(typed.resources.steel, FRESH_WOOD, "steel is unchanged")
	check_eq(typed.resources.cash, FRESH_CASH, "cash is unchanged")
	check_eq(typed.resources.mana, FRESH_MANA, "mana is unchanged")
	check_eq(typed.resources.xp, FRESH_XP, "experience is unchanged")


## No terrain, grid, cell, footprint, or placement-bound code exists in the
## expansion's own module or in the view's expansion-flow section (design D4).
## The scan is over NON-COMMENT source lines, so the documentation that NAMES
## the gap does not satisfy it — only executable code could.
func _check_no_land_code() -> void:
	var tokens := ["Iso.", "GRID_EXTENT", "TILE_WIDTH", "TILE_HEIGHT",
		"world_rect", "footprint", "grid_to_screen", "cells",
		"terrain", "buildable", "map_sizes", "increasedPopulation",
		"world_id", "_resort_objects", "_sync_object_order"]
	var flow_source := _code_lines(_read_source(EXPAND_FLOW_SOURCE))
	check(not flow_source.is_empty(),
		"the expansion module has source lines")
	for token: String in tokens:
		check(not flow_source.contains(token),
			"the pure expansion module never references %s" % token)
	var town_source := _read_source(TOWN_SOURCE)
	# The section markers carry their leading newline so the SAME phrase in the
	# variable block's doc comment (`## Expand flow ...`) cannot match first.
	var section := _section_lines(town_source,
		"\n# Expand flow (building-expand, spec",
		"\n## Shop button wiring")
	check(not section.is_empty(),
		"the view's expansion-flow section is readable")
	for token: String in tokens:
		check(not section.contains(token),
			"the view's expansion-flow section never references %s" % token)


# ---------------------------------------------------------------------------
# Towns built in memory (no fixture is ever written)
# ---------------------------------------------------------------------------


## A town on the committed fresh save with the given cell selected through the
## delivered press path and, when supplied, the owned-expansions ledger replaced
## in memory. No crafted row, no fixture write.
func _selected_town(registry: Variant, cell: Vector2i, item_id: int,
		label: String, owned: Variant = null) -> Variant:
	var payload: Variant = _fixture(PLAYER_FIXTURE)
	if not (payload is Dictionary):
		return null
	var typed: Dictionary = payload as Dictionary
	if owned != null:
		typed = typed.duplicate(true)
		(typed["map"] as Dictionary)["expansions"] = \
			(owned as Array).duplicate()
	return _built_town(typed, registry, cell, item_id, label)


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
# The live-expand scenario (verify-boot's `expand-live` phase)
# ---------------------------------------------------------------------------


## One expansion through the real Compatibility endpoint, so the unchanged
## legacy `command()` executes the derived `expand` envelope over the disposable
## corpus. This side asserts the typed response AND its TWO-part value-level
## post-state proof — the ledger grew by exactly the sent id at the end with
## every existing entry unchanged and in order, AND every stored resource
## changed by exactly the derived debit — plus that a REFUSED expansion left the
## corpus byte-identical. The phase harness separately asserts the corpus save
## file mutated. No fixture is touched.
const LIVE_ID := 0
const LIVE_DUPLICATE_ID := 35
const LIVE_BLOCKED_ID := 4
const LIVE_OUT_OF_RANGE_ID := 98
const LIVE_NEGATIVE_ID := -1
func _check_live_expand() -> void:
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
	var before_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not before_payload.is_empty(), "the corpus pre-expand payload resolves")
	if before_payload.is_empty():
		return
	var ledger_before: Array = _live_ledger(before_payload)
	var balances_before: Dictionary = _live_resources(before_payload)
	# A REFUSED expansion first, while the corpus is pristine, so its
	# byte-identity is provable against an untouched ledger: an id the player
	# already owns (the endpoint's own duplicate guard) and a requirement-
	# blocked id (the two content refusals).
	for entry: Array in [[LIVE_DUPLICATE_ID, "already_expanded"],
			[LIVE_BLOCKED_ID, "expansion_requirements_unmet"],
			[LIVE_OUT_OF_RANGE_ID, "unknown_expansion_id"],
			[LIVE_NEGATIVE_ID, "invalid_expansion_id"]]:
		var refused: Variant = await api.expand_town(pid, int(entry[0]))
		check(refused is BootData.ExpandResult and not refused.ok,
			"expansion id %d is refused by the real endpoint" % int(entry[0]))
		if refused is BootData.ExpandResult:
			check_eq(refused.error_code, str(entry[1]),
				"the refusal for id %d is the service's own code: %s"
					% [int(entry[0]), refused.error_message])
			check(refused.expansions_before.is_empty()
					and refused.expansions_after.is_empty()
					and refused.debit.is_empty() and refused.price == null
					and refused.resources == null,
				"the refused expansion carries no partial payload")
		var after_refusal: Dictionary = await _live_payload(api, endpoint, pid)
		check_eq(_live_ledger(after_refusal), ledger_before,
			"the refused expansion id %d left the corpus ledger byte-identical"
				% int(entry[0]))
		check_eq(_live_resources(after_refusal), balances_before,
			"the refused expansion id %d left every corpus balance "
				% int(entry[0]) + "byte-identical")
	var expanded: Variant = await api.expand_town(pid, LIVE_ID)
	_check_live_expand_result(expanded, ledger_before, balances_before)
	if not (expanded is BootData.ExpandResult) or not expanded.ok:
		return
	var typed: BootData.ExpandResult = expanded
	var after_payload: Dictionary = await _live_payload(api, endpoint, pid)
	check(not after_payload.is_empty(), "the corpus post-expand payload resolves")
	# The service half of the post-state proof, read from the service's own
	# state rather than from the response.
	var ledger_after: Array = _live_ledger(after_payload)
	var expected: Array = ledger_before.duplicate()
	expected.append(LIVE_ID)
	check_eq(ledger_after, expected,
		"the corpus ledger grew by exactly the sent id at the end, with every "
		+ "existing entry unchanged and in order")
	check_eq(_live_resources(after_payload), balances_before,
		"every corpus balance is unchanged, because the committed row for id %d "
		% LIVE_ID + "is free and the derived debit is the all-zero vector")
	# The fake derives the same codes for the same intents, offline.
	api.configure("fake")
	var fake_blocked: Variant = await api.expand_town(pid, LIVE_BLOCKED_ID)
	check(fake_blocked is BootData.ExpandResult and not fake_blocked.ok,
		"the fake fails the same intent offline")
	if fake_blocked is BootData.ExpandResult:
		check_eq(fake_blocked.error_code, "expansion_requirements_unmet",
			"structured codes match between implementations")
	api.configure("legacy_v0", endpoint)
	var ledger: Array = typed.expansions_after
	print("[test] live-expand applied expansion_id=%d ledger=%s debit=%s "
		% [LIVE_ID, JSON.stringify(ledger), JSON.stringify(typed.debit)]
		+ "gold=%d cash=%d" % [typed.resources.gold, typed.resources.cash])


## One live expansion's typed response and its two-part value-level post-state
## proof, compared against the corpus's own pre-request ledger and balances.
func _check_live_expand_result(result: Variant, prior: Array,
		before: Dictionary) -> void:
	check(result is BootData.ExpandResult,
		"the live expand returns the typed result")
	if not (result is BootData.ExpandResult):
		return
	var typed: BootData.ExpandResult = result
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
		+ "(time-dependent)")
	check_eq(typed.result, "success",
		"the live expand reports the legacy success result")
	check_eq(typed.expansions_before, prior,
		"the live pre-execution ledger is the corpus's own, in order")
	var expected: Array = prior.duplicate()
	expected.append(LIVE_ID)
	check_eq(typed.expansions_after, expected,
		"the live post-execution ledger is the sent id appended ONCE at the end "
		+ "(the endpoint's own structural proof)")
	# The value-level half: every stored resource changed by EXACTLY the derived
	# debit. The addressed row is free, so the derived debit is the all-zero
	# vector and every balance must be unchanged — the strongest form of the
	# proof, because a wrong derived price would move one.
	check_eq(typed.debit.size(), BootData.EXPAND_VECTOR_SLOTS,
		"the live derived debit is the documented eight-slot vector")
	for index: int in BootData.EXPAND_ALWAYS_ZERO_SLOTS:
		check_eq(int(typed.debit[index]), 0,
			"the live derived debit's slot %d stays zero" % index)
	for name: String in before:
		check_eq(int(typed.resources.get(name)), int(before[name]),
			"the live %s balance is the corpus's own value (the endpoint's "
			% name + "value-level proof)")
	check_eq([typed.price.coins, typed.price.cash, typed.price.neighbors,
		typed.price.inventory_qte], [0, 0, 0, 0],
		"the live committed price row is the free row's, verbatim")


## The corpus's own owned-expansions ledger, read from its bootstrap payload
## under the typed int names, or [] when the payload carries none.
func _live_ledger(raw: Dictionary) -> Array:
	var map: Dictionary = raw.get("map", {}) as Dictionary
	var owned: Variant = map.get("expansions", [])
	if not (owned is Array):
		return []
	var ids: Array = []
	for entry: Variant in (owned as Array):
		ids.append(int(entry))
	return ids


## The corpus's own seven stored balances under the typed resource names the
## response carries, read from its bootstrap payload. This is the pre-request
## reference the live value-level proof compares against — read from the
## service's own state, never from the fake's fixture.
func _live_resources(raw: Dictionary) -> Dictionary:
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


## The committed schedule the pure helpers read where a helper needs the REAL
## committed rows rather than a crafted table. Read once from the typed content
## package, so a content change fails the SUITE rather than silently
## redefining the claim.
func _pure_schedule() -> Array:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	if registry == null or not bool(registry.is_loaded()):
		return []
	return _committed_schedule(registry)


## The named UI-foundation slot's panel (null when the slot never registered or
## holds no child).
func _panel_of(town: Variant, slot: String) -> Variant:
	if not town.ui.has_slot(slot):
		return null
	var root: Control = town.ui.slot_root(slot)
	if root == null or root.get_child_count() == 0:
		return null
	return root.get_child(0)


## How many buttons named `button_name` the named slot's panel carries.
func _button_count(town: Variant, slot: String, button_name: String) -> int:
	var panel: Variant = _panel_of(town, slot)
	if panel == null:
		return 0
	var buttons: Array = []
	_collect_buttons(panel as Node, buttons)
	var found := 0
	for button: Variant in buttons:
		if String((button as Button).name) == button_name:
			found += 1
	return found


## The named button anywhere inside the given panel (its action row nests the
## arm/confirm/cancel buttons), or null.
func _button_named(panel: Node, button_name: String) -> Variant:
	for child: Variant in panel.get_children():
		if child is Button and String((child as Button).name) == button_name:
			return child
		if child is Node:
			var nested: Variant = _button_named(child as Node, button_name)
			if nested != null:
				return nested
	return null


## Every button in a panel subtree, in creation order, so a check can assert the
## surface's own affordances and prove no extra action exists.
func _collect_buttons(panel: Node, out: Array) -> void:
	for child: Variant in panel.get_children():
		if child is Button:
			out.append(child)
		if child is Node:
			_collect_buttons(child as Node, out)


## The on-screen expansion selection line ("" before a panel exists).
func _expand_selection_text(town: Variant) -> String:
	var panel: Variant = _panel_of(town, "expand")
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "selection":
			return (child as Label).text
	return ""


## The on-screen expansion readout line ("" when no panel exists).
func _expand_readout_label(town: Variant) -> String:
	var panel: Variant = _panel_of(town, "expand")
	if panel == null:
		return ""
	for child: Variant in (panel as Node).get_children():
		if child is Label and String((child as Label).name) == "expansions":
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
## prove an expansion changed no object's identity, no cell, and no committed
## DEPTH POSITION.
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


## Deterministic serialization of every committed state field (the byte-identity
## oracle for the cancelled, refused, and failed paths), including the owned
## expansions ledger — so a cancellation or a failure that quietly changed the
## ledger can never look byte-identical.
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
		"owned_expansions": state.owned_expansions,
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


## A res:// source file's text, or "" when it cannot be read.
func _read_source(resource_path: String) -> String:
	var path := ProjectSettings.globalize_path(resource_path)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return ""
	var text := handle.get_as_text()
	handle = null
	return text


## Every NON-COMMENT, non-blank source line of a file, newline-separated. The
## point is that documentation may NAME a forbidden concept (this slice's own
## non-claims do) while executable code may not reach for it.
func _code_lines(source: String) -> String:
	var kept: Array = []
	for line in source.split("\n"):
		var stripped := line.strip_edges()
		if stripped == "" or stripped.begins_with("#"):
			continue
		kept.append(stripped)
	return "\n".join(kept)


## The non-comment source lines of the region between two section headers
## (inclusive of the header's own body, exclusive of the next header), or ""
## when the start header is absent.
func _section_lines(source: String, start_marker: String,
		end_marker: String) -> String:
	var start := source.find(start_marker)
	if start == -1:
		return ""
	var finish := source.find(end_marker, start + start_marker.length())
	if finish == -1:
		finish = source.length()
	return _code_lines(source.substr(start, finish - start))


## Loads a repository-relative JSON fixture as parsed text (read-only).
func _fixture(relative: String) -> Variant:
	return JSON.parse_string(FileAccess.get_file_as_bytes(
		Paths.repo_root().path_join(relative)).get_string_from_utf8())
