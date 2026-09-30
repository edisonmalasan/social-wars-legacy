extends "res://tests/test_base.gd"
## Resource-projection suite (OpenSpec `godot-building-resources`
## "Canonical resource projection" / "Resource readout completeness" /
## "The eighth resource is exposed with its gap recorded" / "No
## state-mutating surface changes", change task 2.4).
##
## Scenarios:
##   projection  the canonical table in `resource_projection.gd` itself: ten
##               rows in the delivered display order, each naming a field the
##               legacy server actually produces, each at exactly one save
##               location, no resource twice, no row keyed by an unproduced
##               name, `xp` in the summary group, and `energy` present under
##               the save's own name with no mutation-vector slot and its
##               regeneration gap recorded;
##   values      every row of a complete payload renders its real stored value
##               and NO row renders the absent-field indicator;
##   absent      BOTH absent-field paths fail closed with the explicit
##               indicator naming the canonical field — the parser-recorded
##               `missing` list, and a typed state whose value bag carries no
##               such field — and neither guesses, defaults, nor disturbs
##               another row;
##   response    the response-driven update path: one delivered
##               state-mutating action (the committed collection) moves
##               exactly the two resources the shared accessor carries, the
##               readout re-renders from the RESPONSE's values, the row set is
##               invariant across the mutation, and the stored energy value
##               does not move;
##   unchanged   no delivered line's semantics change: the typed transport
##               resource class the nine state-mutating endpoints share still
##               declares EXACTLY the seven server names (the shared accessor
##               is not widened with the energy value, design D4), and the
##               projection module itself carries no node, no clock, no
##               request, and no mutation.
##
## Hermetic: no process, no server, no socket, and no network argument is
## read. The only API use is the committed-fixture fake double, which serves
## committed files in process. Uses the ContentRegistry autoload (content +
## asset registry loaded explicitly). Runs headless as part of
## `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const TownHud = preload("res://scripts/town/town_hud.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const ResourceProjection = preload("res://scripts/town/resource_projection.gd")

const FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const PROJECTION_SOURCE := "res://scripts/town/resource_projection.gd"

## The delivered display order and row set (task 2.2: no new row, no removed
## row, no reordering — seven resource rows then the three summary rows).
const DELIVERED_ROW_ORDER := ["gold", "wood", "steel", "oil", "cash", "energy",
	"mana", "name", "level", "xp"]
const DELIVERED_RESOURCE_ROWS := ["gold", "wood", "steel", "oil", "cash",
	"energy", "mana"]
const DELIVERED_SUMMARY_ROWS := ["name", "level", "xp"]
## The field name NO committed source produces: `engine.apply_resources` writes
## `maps[0].gold` and the map record carries no `coins` field.
const UNPRODUCED_NAME := "coins"
## The seven slots `apply_resources` writes, in the legacy vector's own order
## (slot 0 is read and discarded, so it has no row).
const SERVER_SLOTS := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]
const VECTOR_SLOTS := 8
## The committed corpus's stored values (fixture ground truth).
const FRESH_XP := 4
const FRESH_GOLD := 2000
const FRESH_WOOD := 2000
const FRESH_OIL := 2000
const FRESH_STEEL := 2000
const FRESH_CASH := 5
const FRESH_MANA := 0
const FRESH_ENERGY := 50
const FRESH_NAME := "Warrior"
const FRESH_LEVEL := 1
## The delivered collection this suite drives through the fake double: the
## Tree decoration (item 905) at legacy map key 2, whose committed payout
## credits wood and experience and nothing else. Used ONLY to observe that the
## readout follows a delivered response; the collection's own semantics are
## the delivered collect suite's to assert, not this one's.
const COLLECT_KEY := 2
const PLACEMENTS := 40
## Tokens a pure projection module must not carry: a node, a clock, a request,
## or a mutation. The transport needles are spelled as fragments because the
## project-scope suite scans every source file for their literal forms.
const PURITY_NEEDLES := [
	"extends Node", "Node2D", "get_tree", "OS.", "await ", "Engine.get_ticks",
	"Time.get_ticks", "rand", "push_error", ".set(", "erase(", "remove_at(",
	"http" + "://", "HTTP" + "Request", "HTTP" + "Client",
]


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	if not bool(registry.is_loaded()):
		registry.load_content()
	if not bool(registry.assets_loaded()):
		registry.load_asset_registry()
	var payload: Variant = _fixture()
	check(payload is Dictionary, "the player fixture parses as JSON")
	if not (payload is Dictionary):
		return

	_check_projection(payload)
	var parsed: Dictionary = TownState.parse(payload, registry)
	check(bool(parsed.get("ok", false)),
		"the committed payload parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]
	_check_values(state)
	_check_record()
	_check_read_only(state)
	_check_absent(registry, payload)
	await _check_response_update(payload)
	_check_unchanged()


## The committed bootstrap payload, read verbatim from the repository.
func _fixture() -> Variant:
	return JSON.parse_string(
		FileAccess.get_file_as_bytes(
			Paths.repo_root().path_join(FIXTURE)).get_string_from_utf8())


## One row's display string through the projection, failing closed by name
## when the projection carries no such row.
func _text(state: Variant, name: String) -> String:
	var entry: Variant = ResourceProjection.row_for(name)
	if entry == null:
		return ResourceProjection.MISSING_FORMAT % name
	return ResourceProjection.text_for(state, entry as Dictionary)


# ---------------------------------------------------------------------------
# The canonical projection itself
# ---------------------------------------------------------------------------


## Every property of the canonical table, asserted against the committed
## payload rather than against a restatement of the table.
func _check_projection(payload: Dictionary) -> void:
	var names: Array = []
	for entry: Variant in ResourceProjection.rows():
		names.append(str((entry as Dictionary)["name"]))
	check_eq(names, DELIVERED_ROW_ORDER,
		"the projection carries exactly the delivered ten rows, in the "
			+ "delivered order (no row added, removed, or reordered)")
	check_eq(ResourceProjection.names(ResourceProjection.GROUP_RESOURCES),
		DELIVERED_RESOURCE_ROWS,
		"the resource group is the seven delivered resource rows")
	check_eq(ResourceProjection.names(ResourceProjection.GROUP_SUMMARY),
		DELIVERED_SUMMARY_ROWS,
		"the summary group is the three delivered summary rows")
	# The readout renders the SAME table the projection owns, never a second
	# copy of it.
	check_eq(TownHud.fields(), ResourceProjection.rows(),
		"the readout projects through the canonical table and owns no other")

	# No resource is displayed twice, under either name: the canonical names
	# are unique, and so are the save locations they resolve to.
	var seen_names := {}
	var seen_locations := {}
	var duplicates: Array = []
	for entry: Variant in ResourceProjection.rows():
		var row: Dictionary = entry
		var name := str(row["name"])
		var location := str(row["location"])
		if seen_names.has(name):
			duplicates.append("name " + name)
		if seen_locations.has(location):
			duplicates.append("location " + location)
		seen_names[name] = true
		seen_locations[location] = true
	check_eq(duplicates, [],
		"no resource appears twice: every canonical name and every save "
			+ "location is claimed exactly once")

	# No row is keyed by a field no committed source produces. The one
	# candidate the delivered table carried is checked by name, and the rest
	# structurally: EVERY location resolves in the committed payload, so no row
	# can name a field the server does not produce.
	check(not ResourceProjection.has(UNPRODUCED_NAME),
		"the projection has no row keyed by the unproduced field '%s'"
			% UNPRODUCED_NAME)
	check_eq(ResourceProjection.row_for(UNPRODUCED_NAME), null,
		"looking up the unproduced field resolves to no row at all")
	check_eq(ResourceProjection.missing_indicator(UNPRODUCED_NAME), "",
		"no absent-field indicator is fabricated for a row that does not exist")
	var unresolved: Array = []
	for entry: Variant in ResourceProjection.rows():
		var location := str((entry as Dictionary)["location"])
		if _payload_value(payload, location) == null:
			unresolved.append(location)
	check_eq(unresolved, [],
		"every projected save location resolves in the committed payload, so "
			+ "no row names a field the server does not produce")

	# The primary currency is named exactly as the server names it.
	var primary: Variant = ResourceProjection.row_for("gold")
	check(primary is Dictionary, "the projection names the primary currency")
	if primary is Dictionary:
		check_eq(str((primary as Dictionary)["location"]), "map.gold",
			"the primary currency lives at the field apply_resources writes")
		check_eq(str((primary as Dictionary)["label"]), "Gold",
			"the primary currency is labelled by its own name")
		check_eq(int((primary as Dictionary)["vector_slot"]), 2,
			"the primary currency sits at the vector's own gold slot")

	# `xp` is the experience counter, not a currency: it stays in the summary
	# group (design D2) while every spendable resource stays in the resource
	# group.
	check_eq(ResourceProjection.names(ResourceProjection.GROUP_RESOURCES).has(
			"xp"), false,
		"the experience counter is not a spendable resource row")
	var xp_row: Variant = ResourceProjection.row_for("xp")
	check(xp_row is Dictionary
			and str((xp_row as Dictionary)["group"])
				== ResourceProjection.GROUP_SUMMARY,
		"the experience counter is grouped with the summary, not with the "
			+ "spendable resources")

	# Every one of the seven slots `apply_resources` writes has a row, and the
	# vector's unread slot 0 has none.
	var covered: Array = []
	for name: String in SERVER_SLOTS:
		if ResourceProjection.has(name):
			covered.append(name)
	check_eq(covered, SERVER_SLOTS,
		"every resource the legacy resource application writes has a row")
	check(not ResourceProjection.has("unknown"),
		"the vector's unread cheat-detection slot has no row")
	check_eq(ResourceProjection.server_resource_rows(), SERVER_SLOTS,
		"the projection's server-resource row set is exactly those seven")

	# `energy` is exposed under the save's own name, outside the mutation
	# vector, with the regeneration gap recorded (design D3).
	var energy_row: Variant = ResourceProjection.row_for("energy")
	check(energy_row is Dictionary, "the eighth resource has a row")
	if energy_row is Dictionary:
		check_eq(str((energy_row as Dictionary)["location"]),
			"privateState.energy",
			"the energy row lives at the save's own field")
		check_eq(str((energy_row as Dictionary)["name"]), "energy",
			"the energy row is keyed by the save's own name")
		check_eq(int((energy_row as Dictionary)["vector_slot"]),
			ResourceProjection.NO_VECTOR_SLOT,
			"the energy row is outside the legacy mutation vector, which no "
				+ "delivered path can fill")
	check_eq(ResourceProjection.MUTATION_VECTOR_SLOTS, VECTOR_SLOTS,
		"the projection never widens the legacy eight-slot vector")
	check(ResourceProjection.ENERGY_GAP.contains("apply_resources")
			and ResourceProjection.ENERGY_GAP.contains("never writes"),
		"the energy gap is recorded where the resource is described: %s"
			% ResourceProjection.ENERGY_GAP)
	var unclaimed := false
	for claim: String in ResourceProjection.NON_CLAIMS:
		if claim.contains("no rule is claimed for how the stored energy value"):
			unclaimed = true
	check(unclaimed,
		"the non-claims state that no regeneration rule for energy is claimed")
	var established := 0
	for row: Dictionary in ResourceProjection.PROVENANCE["established"]:
		established += 1
	check(established >= 5,
		"the provenance split records the established facts the reader can "
			+ "check (found %d)" % established)


## The projection's report table carries the row, canonical name, save
## location, and group for every row — the four fields the spec requires of
## the structural report — and stays in the delivered order.
func _check_record() -> void:
	var rows := ResourceProjection.record()
	check_eq(rows.size(), DELIVERED_ROW_ORDER.size(),
		"the projection table records every delivered row")
	var malformed: Array = []
	var order: Array = []
	for entry: Variant in rows:
		var row: Dictionary = entry
		for key: String in ["row", "name", "location", "group"]:
			if not row.has(key) or str(row[key]) == "":
				malformed.append("%s=%s" % [key, str(row.get(key, ""))])
		order.append(str(row["name"]))
	check_eq(malformed, [],
		"every recorded row carries its index, canonical name, save location, "
			+ "and group")
	check_eq(order, DELIVERED_ROW_ORDER,
		"the recorded projection table is in the delivered order")


# ---------------------------------------------------------------------------
# Readout values
# ---------------------------------------------------------------------------


## Every row renders its real stored value, and none renders the
## absent-field indicator, against the complete committed payload.
func _check_values(state: Variant) -> void:
	var expected := {
		"gold": str(FRESH_GOLD), "wood": str(FRESH_WOOD),
		"steel": str(FRESH_STEEL), "oil": str(FRESH_OIL),
		"cash": str(FRESH_CASH), "energy": str(FRESH_ENERGY),
		"mana": str(FRESH_MANA), "name": FRESH_NAME,
		"level": str(FRESH_LEVEL), "xp": str(FRESH_XP),
	}
	for name: String in expected:
		check_eq(_text(state, name), expected[name],
			"row '%s' renders the save's stored value %s"
				% [name, expected[name]])
	check_eq(ResourceProjection.absent_rows(state), [],
		"no row fails closed against a complete payload")
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"town builds so the readout can attach: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	var hud: Variant = town.hud()
	check(hud != null, "the readout attached to the slot")
	if hud == null:
		town.free()
		return
	var wrong: Array = []
	for name: String in expected:
		if hud.displayed(name) != expected[name]:
			wrong.append("%s=%s" % [name, hud.displayed(name)])
	check_eq(wrong, [],
		"every row on the readout renders the save's stored value")
	check_eq(hud.displayed(UNPRODUCED_NAME), "",
		"the readout exposes no row for the unproduced field")
	check_eq(hud.displayed_fields().size(), DELIVERED_ROW_ORDER.size(),
		"the readout renders exactly the projected rows, no more and no fewer")
	var indicators := 0
	for key: String in hud.displayed_fields():
		if hud.displayed(key) == ResourceProjection.MISSING_FORMAT % key:
			indicators += 1
	check_eq(indicators, 0,
		"no row renders an absent-field indicator against a complete payload")
	town.free()


# ---------------------------------------------------------------------------
# Both absent-field paths
# ---------------------------------------------------------------------------


## BOTH ways a value can be absent, each failing closed by name:
##   1. the parser recorded the save field as missing (a payload that omits
##      it) — exercised for the eighth resource AND for the primary currency,
##      whose absence the typed bag records under its own legacy field name
##      while the readout must name `gold`; and
##   2. the typed state carries no bag for the value at all (a state built
##      outside the parser, or a bag that was never populated).
## Neither guesses, defaults to zero, nor disturbs another row, and a null
## state is the same refusal rather than a crash.
func _check_absent(registry: Variant, payload: Dictionary) -> void:
	for omitted: Array in [["energy", "privateState", "energy"],
			["gold", "map", "gold"]]:
		var omitted_name := str(omitted[0])
		var crafted: Dictionary = (payload as Dictionary).duplicate(true)
		(crafted[str(omitted[1])] as Dictionary).erase(str(omitted[2]))
		var parsed: Dictionary = TownState.parse(crafted, registry)
		check(bool(parsed.get("ok", false)),
			"a payload without %s still parses: %s"
				% [omitted_name, parsed.get("error")])
		if not bool(parsed.get("ok", false)):
			continue
		var state: Variant = parsed["state"]
		check_eq(ResourceProjection.absent_rows(state), [omitted_name],
			"exactly the omitted %s row fails closed, and no other"
				% omitted_name)
		check_eq(_text(state, omitted_name),
			ResourceProjection.MISSING_FORMAT % omitted_name,
			"the omitted %s renders the indicator naming ITS OWN name, never "
				% omitted_name + "the typed field's legacy name")
		check(ResourceProjection.value_of(state, omitted_name) == null,
			"an absent value is never substituted (not zero, not a guess)")
		check(_text(state, omitted_name).find(
				str(_prior_value(omitted_name))) == -1,
			"the indicator carries no fabricated number")
		var neighbours: Array = []
		for name: String in DELIVERED_ROW_ORDER:
			if name == omitted_name:
				continue
			if _text(state, name).begins_with(
					ResourceProjection.MISSING_FORMAT):
				neighbours.append(name)
		check_eq(neighbours, [],
			"no other row is affected by the omitted %s" % omitted_name)
		if omitted_name == "energy":
			check_eq(_text(state, "gold"), str(FRESH_GOLD),
				"the primary currency is untouched by an absent energy field")

	# Path 2: the bag itself carries no such field. A typed state built
	# outside the parser with its resource bag nulled is the honest way to
	# reach this, because the parser always populates it.
	var bare: TownState.State = TownState.State.new()
	bare.resources = null
	check_eq(_text(bare, "gold"), ResourceProjection.MISSING_FORMAT % "gold",
		"a resource bag that carries no field fails closed by name")
	check(ResourceProjection.value_of(bare, "gold") == null,
		"a bag that carries no field substitutes nothing")
	check_eq(_text(bare, "level"), str(0),
		"the summary group is unaffected by an absent resource bag")
	var summary_bare: TownState.State = TownState.State.new()
	summary_bare.summary = null
	check_eq(_text(summary_bare, "level"),
		ResourceProjection.MISSING_FORMAT % "level",
		"the summary group fails closed the same way, by its own name")
	# The two groups are never read out of each other.
	var mixed: TownState.State = TownState.State.new()
	mixed.summary = TownState.Summary.new()
	mixed.resources = TownState.Resources.new()
	mixed.summary.level = 9999
	mixed.resources.wood = 1234
	check_eq(_text(mixed, "level"), "9999",
		"the summary row reads the summary bag")
	check_eq(_text(mixed, "wood"), "1234",
		"the resource row reads the resource bag")
	# A null state is the same refusal, never a crash.
	check_eq(_text(null, "gold"), ResourceProjection.MISSING_FORMAT % "gold",
		"a null state fails closed by name")
	check(ResourceProjection.value_of(null, "gold") == null,
		"a null state substitutes no value")


# ---------------------------------------------------------------------------
# The response-driven update path
# ---------------------------------------------------------------------------


## One delivered state-mutating action through the committed fake double: the
## shared accessor carries exactly the resources the legacy application
## writes, the response moves exactly the two the committed payout names, the
## readout re-renders from the RESPONSE's values, its row set is invariant
## across the mutation, and the stored energy value does not move (design
## D3/D4: nothing claims it is part of the mutated resource set).
func _check_response_update(payload: Dictionary) -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	var api: Variant = root.get_node_or_null("GameApi")
	var session: Variant = root.get_node_or_null("Session")
	check(api != null and session != null,
		"GameApi and Session autoloads are registered")
	if api == null or session == null or registry == null:
		return
	var parsed: Dictionary = TownState.parse(payload, registry)
	if not bool(parsed.get("ok", false)):
		check(false, "the committed payload parses for the response update")
		return
	var state: Variant = parsed["state"]
	api.configure("fake")
	var listing: Variant = await api.list_sessions()
	check(listing is BootData.SaveListResult,
		"the save list resolves the corpus save")
	if not (listing is BootData.SaveListResult):
		return
	if (listing as BootData.SaveListResult).saves.is_empty():
		check(false, "the save list carries a save")
		return
	var pid := str((listing as BootData.SaveListResult).saves[0].id)
	var summary := BootData.PlayerSummary.new()
	summary.user_id = pid
	summary.name = str(state.summary.name)
	summary.level = int(state.summary.level)
	summary.xp = int(state.summary.xp)
	var activation: Dictionary = session.activate(pid, summary)
	check(bool(activation.get("ok", false)),
		"the session activates the save: %s" % activation.get("error"))
	if not bool(activation.get("ok", false)):
		return

	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"town builds for the response update: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	check_eq(town.objects.size(), PLACEMENTS,
		"the fresh save renders the committed object count before the action")
	var hud: Variant = town.hud()
	check(hud != null, "the readout attached before the delivered action")
	if hud == null:
		town.free()
		return
	var keys_before: Array = hud.displayed_fields().keys()
	keys_before.sort()
	var wood_before: int = int(state.resources.wood)
	var xp_before: int = int(state.summary.xp)
	var gold_before: int = int(state.resources.coins)
	var energy_before: int = int(state.resources.energy)

	var requests_before: int = api.collect_requests
	var result: Variant = await api.collect_income(pid, COLLECT_KEY)
	check_eq(api.collect_requests, requests_before + 1,
		"exactly one request carried the delivered intent")
	check(result is BootData.CollectResult,
		"the delivered collection resolves a typed result through the fake "
			+ "double")
	if not (result is BootData.CollectResult):
		town.free()
		return
	var response: BootData.CollectResult = result
	check(response.ok, "the delivered collection succeeded: %s"
		% response.error_message)
	if not response.ok:
		town.free()
		return

	# The delivered line's own semantics are the collect suite's to assert.
	# What the projection claims is narrower and checkable here: the response
	# carries exactly the seven slots, it moves exactly the two the committed
	# payout names, and it says nothing at all about the stored energy value.
	var carried: Array = ResourceProjection.field_names(response.resources)
	var expected_carried := SERVER_SLOTS.duplicate()
	expected_carried.sort()
	var carried_sorted := carried.duplicate()
	carried_sorted.sort()
	check_eq(carried_sorted, expected_carried,
		"the delivered response carries exactly the seven resources the shared "
			+ "accessor exposes, and nothing else")
	check(not carried.has("energy"),
		"the delivered response's resource set does not include the stored "
			+ "energy value")
	var prior_values := {
		"xp": xp_before, "gold": gold_before, "wood": wood_before,
		"oil": FRESH_OIL, "steel": FRESH_STEEL, "cash": FRESH_CASH,
		"mana": FRESH_MANA,
	}
	var moved: Array = []
	for field: Variant in carried:
		var key := str(field)
		if int((response.resources as Object).get(key)) \
				!= int(prior_values.get(key, 0)):
			moved.append(key)
	moved.sort()
	check_eq(moved, ["wood", "xp"],
		"the delivered response moves exactly the committed payout's two "
			+ "resources — the readout has no opinion beyond that")

	# Apply the delivered response the way the view does — the RESPONSE's
	# balances verbatim, never the client's own arithmetic — and re-render.
	_apply_balances(state, response.resources)
	var rebuilt: Dictionary = town.build()
	check(bool(rebuilt.get("ok", false)),
		"the readout re-renders after the delivered response: %s"
			% rebuilt.get("error"))
	var after: Variant = town.hud()
	check(after != null, "the readout re-attaches to the mutated state")
	if after == null:
		town.free()
		return
	check_eq(after.displayed("wood"), str(int(state.resources.wood)),
		"the wood row renders the response's value after the mutation")
	check(int(state.resources.wood) != wood_before,
		"the applied wood balance is the response's, not the prior value")
	check_eq(after.displayed("xp"), str(int(state.summary.xp)),
		"the experience row renders the response's value after the mutation")
	check(int(state.summary.xp) != xp_before,
		"the applied experience is the response's, not the prior value")
	check_eq(after.displayed("gold"), str(gold_before),
		"the primary currency renders the response's unchanged value")
	check_eq(after.displayed("energy"), str(energy_before),
		"the stored energy value is unchanged by a delivered action: nothing "
			+ "claims it is part of the mutated resource set")
	var keys_after: Array = after.displayed_fields().keys()
	keys_after.sort()
	check_eq(keys_after, keys_before,
		"the readout renders the same rows after the mutation")
	check_eq(ResourceProjection.absent_rows(state), [],
		"no row fails closed after a delivered state-mutating response")
	check_eq(int(state.resources.energy), energy_before,
		"the typed state's stored energy value is untouched by the apply")
	town.free()


## The response's seven balances applied verbatim to the typed state, exactly
## as the delivered view does: the RESPONSE's values, never the client's own
## arithmetic. Deliberately a plain field write so this suite never
## re-implements a delivered line's apply.
func _apply_balances(state: Variant, resources: Variant) -> void:
	if resources == null or state == null:
		return
	for field: Variant in ResourceProjection.field_names(resources):
		var key := str(field)
		var value: int = int((resources as Object).get(key))
		if key == "xp":
			(state.summary as TownState.Summary).set(key, value)
			continue
		var entry: Variant = ResourceProjection.row_for(key)
		var typed := key
		if entry != null:
			typed = str((entry as Dictionary)["typed_state_field"])
		(state.resources as TownState.Resources).set(typed, value)


# ---------------------------------------------------------------------------
# No delivered line's semantics change
# ---------------------------------------------------------------------------


## The shared transport resource class the nine state-mutating endpoints'
## post-execution proofs compare still declares EXACTLY the seven names
## `apply_resources` writes — the shared accessor is deliberately NOT widened
## with the energy value (design D4) — and the projection module itself is
## pure: no node, no clock, no request, and no mutation.
func _check_unchanged() -> void:
	var carried: Array = ResourceProjection.field_names(BootData.Resources.new())
	carried.sort()
	var expected := SERVER_SLOTS.duplicate()
	expected.sort()
	check_eq(carried, expected,
		"the transport resource class the nine delivered endpoints share still "
			+ "declares exactly the seven server names, unwidened")
	check(not carried.has("energy"),
		"the stored energy value is NOT added to the shared accessor the nine "
			+ "post-execution proofs compare")

	# The projection module is a pure mapping module: it derives strings and
	# records from a state it is handed and mutates nothing.
	var handle := FileAccess.open(PROJECTION_SOURCE, FileAccess.READ)
	check(handle != null, "the projection module source is readable")
	if handle == null:
		return
	var body := handle.get_as_text()
	handle = null
	check(body.begins_with("extends RefCounted"),
		"the projection module is a plain reference-counted module, not a node")
	check(not body.contains("func _init("),
		"the projection module constructs nothing and owns no lifecycle")
	var impure: Array = []
	for needle: String in PURITY_NEEDLES:
		if body.contains(needle):
			impure.append(needle)
	check_eq(impure, [],
		"the projection module carries no node, no clock, no request, and no "
			+ "mutation (pure mapping only)")
	var instance_functions: Array = []
	for line: String in body.split("\n"):
		if line.begins_with("func ") and not line.begins_with("func _"):
			instance_functions.append(line)
	check_eq(instance_functions, [],
		"every projection helper is static: the module holds no state and "
			+ "cannot drift between reads")


## Behavioural purity: reading the readout never changes the state it reads.
## Every helper is called over a real typed state and the state is compared
## field by field afterwards, so a projection that quietly wrote to the
## player's balances would fail here rather than hide behind a passing string
## comparison.
func _check_read_only(state: Variant) -> void:
	var before: Dictionary = _snapshot(state)
	for entry: Variant in ResourceProjection.rows():
		ResourceProjection.text_for(state, entry as Dictionary)
		ResourceProjection.value_of(state, str((entry as Dictionary)["name"]))
	ResourceProjection.displayed(state)
	ResourceProjection.absent_rows(state)
	ResourceProjection.record()
	ResourceProjection.rows()
	check_eq(_snapshot(state), before,
		"reading every row through the projection mutates nothing in the "
			+ "typed state")


## The typed state's own read-only record: every resource, every summary
## value, and the recorded absence list.
func _snapshot(state: Variant) -> Dictionary:
	var out := {"missing": (state.missing as Array).duplicate()}
	for field: Variant in ResourceProjection.field_names(state.resources):
		out[str(field)] = int((state.resources as Object).get(str(field)))
	for field: Variant in ResourceProjection.field_names(state.summary):
		out[str(field)] = str((state.summary as Object).get(str(field)))
	return out


## One dotted save path out of a payload, or null when any level is absent.
func _payload_value(payload: Dictionary, path: String) -> Variant:
	var cursor: Variant = payload
	for part: String in path.split("."):
		if not (cursor is Dictionary) or not (cursor as Dictionary).has(part):
			return null
		cursor = (cursor as Dictionary)[part]
	return cursor


## The committed corpus value a field held BEFORE it was omitted, so the
## absent-field check can assert the indicator carries no leftover number.
func _prior_value(name: String) -> int:
	if name == "energy":
		return FRESH_ENERGY
	return FRESH_GOLD
