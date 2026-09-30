extends "res://tests/test_base.gd"
## Resource HUD suite (OpenSpec `godot-town-rendering` "Authoritative
## resource HUD", change task 4.1; `godot-building-resources` "Canonical
## resource projection" / "Resource readout completeness", change task 2.3).
##
## Scenarios:
##   values     the fresh-save state renders every HUD row as exactly
##              `str(state.value)` — seven resources plus name/level/xp —
##              through the UI foundation's `hud` slot, with the slot
##              reused (never duplicated) across rebuilds. The primary
##              currency renders under the server's OWN name `gold`, NO row
##              is keyed `coins`, `energy` renders its stored value, and no
##              row renders the absent-field indicator against a complete
##              payload;
##   missing    a payload with `privateState.energy` removed parses with
##              `energy` recorded missing, and the HUD renders the
##              explicit indicator naming that field (no fabricated
##              number, no zero, no stale value), with every other field
##              still verbatim;
##   envelopes  a null state and a null UI foundation each fail closed
##              with an error naming the condition.
##
## The crafted payload uses the field names the SERVICE ACTUALLY PRODUCES
## (`map.gold`, `privateState.energy`, ...) — never an invented `coins`
## field, which no real payload carries (task 2.3).
##
## The HUD is display-only: nothing is computed or polled. Uses the
## ContentRegistry autoload (content + asset registry loaded explicitly).
## No API, no server. Runs headless as part of `verify-boot.ps1`.

const TownState = preload("res://scripts/town/town_state.gd")
const TownHud = preload("res://scripts/town/town_hud.gd")
const ResourceProjection = preload("res://scripts/town/resource_projection.gd")

const FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
## The fresh save's expected display strings (fixture ground truth), keyed by
## the CANONICAL resource name the server produces. The primary currency is
## `gold`: the payload carries `map.gold` and no `coins` field, so keying
## this map `coins` would be pinning a name nothing produces.
const EXPECTED := {
	"gold": "2000", "wood": "2000", "steel": "2000", "oil": "2000",
	"cash": "5", "energy": "50", "mana": "0",
	"name": "Warrior", "level": "1", "xp": "4",
}
## The field name NO server source produces: `engine.apply_resources` writes
## `maps[0].gold` and the map record carries no `coins` field, so no readout
## row may be keyed by it.
const INVENTED_NAME := "coins"


func run_scenario() -> void:
	if DisplayServer.get_name() != "headless":
		fail("this test must run headless (got display server %s)"
			% DisplayServer.get_name())
		return
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	var content: Dictionary = registry.load_content()
	check(bool(content.get("ok", false)),
		"content package loads: %s" % content.get("error"))
	var assets: Dictionary = registry.load_asset_registry()
	check(bool(assets.get("ok", false)),
		"asset registry loads: %s" % assets.get("error"))
	if not bool(content.get("ok", false)) or not bool(assets.get("ok", false)):
		return

	var payload: Variant = JSON.parse_string(
		FileAccess.get_file_as_bytes(
			Paths.repo_root().path_join(FIXTURE)).get_string_from_utf8())
	check(payload is Dictionary, "fresh fixture parses as JSON")
	if not (payload is Dictionary):
		return
	var parsed: Dictionary = TownState.parse(payload, registry)
	check(bool(parsed.get("ok", false)),
		"fresh fixture parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return

	_check_value_strings(registry, parsed["state"])
	_check_missing_field(registry, payload)
	_check_envelopes(parsed["state"])


## Spec: every row displays `str(state.value)` verbatim, one slot, reused
## across rebuilds, under the canonical name the server produces.
func _check_value_strings(registry: Variant, state: Variant) -> void:
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"town builds so the HUD can attach: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	check(town.ui.has_slot("hud"), "the HUD owns the UI foundation slot")
	var hud: Variant = town.hud()
	check(hud != null, "the HUD attached to the slot")
	if hud == null:
		town.free()
		return
	check_eq(hud.displayed_fields(), EXPECTED,
		"every displayed string equals the fresh-save fixture value")
	# The primary currency renders its REAL stored value, under the server's
	# own name. It is a row of the readout like any other, and the save's
	# `map.gold` is what it reads.
	check_eq(hud.displayed("gold"), "2000",
		"the primary currency row renders the stored map.gold by value")
	check_eq(hud.displayed("energy"), "50",
		"the energy row renders its stored privateState.energy by value")
	# NO row may be keyed by a field no server source produces.
	check_eq(hud.displayed(INVENTED_NAME), "",
		"no readout row is keyed by the unproduced field '%s'" % INVENTED_NAME)
	check(not hud.displayed_fields().has(INVENTED_NAME),
		"the committed display map carries no '%s' key" % INVENTED_NAME)
	# The fabricated payload shape is gone: the crafted HUD map above is
	# keyed only by fields the service actually produces.
	var fabricated: Array = []
	for key: String in EXPECTED:
		if not ResourceProjection.has(key):
			fabricated.append(key)
	check_eq(fabricated, [],
		"every key of the expected display map is a canonical projection name")
	# Value-string equality against the typed state itself (not just the
	# hardcoded map): str(state.value) for each row's group/field pair.
	var mismatches := 0
	for entry in TownHud.fields():
		var key := str(entry["name"])
		var bag: Variant = state.summary \
			if str(entry["group"]) == ResourceProjection.GROUP_SUMMARY \
			else state.resources
		if hud.displayed(key) != str(bag.get(str(entry["typed_state_field"]))):
			mismatches += 1
	check_eq(mismatches, 0,
		"str(state.value) equality holds for every row (mismatches: %d)"
		% mismatches)
	# On-screen rows: the label under the slot renders the same strings.
	var root_slot: Control = town.ui.slot_root("hud")
	check(root_slot != null, "the slot exposes its root container")
	if root_slot != null:
		var rows := 0
		var gold_row := ""
		var energy_row := ""
		var indicator_rows := 0
		for child in root_slot.get_children():
			for row in child.get_children():
				if row is Label:
					rows += 1
					if str(row.text).begins_with("Gold:"):
						gold_row = str(row.text)
					if str(row.text).begins_with("Energy:"):
						energy_row = str(row.text)
					if str(row.text).find("[missing:") != -1:
						indicator_rows += 1
		check_eq(rows, TownHud.fields().size(),
			"one on-screen row per canonical projection entry")
		check_eq(gold_row, "Gold: 2000",
			"the on-screen primary-currency row renders its stored value")
		check_eq(energy_row, "Energy: 50",
			"the on-screen energy row renders its verbatim value")
		check_eq(indicator_rows, 0,
			"no on-screen row renders an absent-field indicator against a "
				+ "complete payload")
	# Rebuild reuses the registered slot (the foundation rejects duplicate
	# registrations) and replaces the contents without duplication.
	var rebuilt: Dictionary = town.build()
	check(bool(rebuilt.get("ok", false)),
		"rebuild succeeds: %s" % rebuilt.get("error"))
	check(town.ui.has_slot("hud"), "the slot survives the rebuild")
	var rebuilt_root: Control = town.ui.slot_root("hud")
	var columns := 0
	for child in rebuilt_root.get_children():
		columns += 1
	check_eq(columns, 1, "the rebuilt HUD holds exactly one value column")
	town.free()


## Spec: "Name a missing value instead of guessing" — an absent payload
## field renders the explicit indicator naming it, and no other row moves.
func _check_missing_field(registry: Variant, payload: Variant) -> void:
	var crafted: Variant = payload.duplicate(true)
	(crafted["privateState"] as Dictionary).erase("energy")
	var parsed: Dictionary = TownState.parse(crafted, registry)
	check(bool(parsed.get("ok", false)),
		"a payload without energy still parses: %s" % parsed.get("error"))
	if not bool(parsed.get("ok", false)):
		return
	var state: Variant = parsed["state"]
	check_eq(state.missing, ["energy"],
		"energy is recorded as missing and nothing else")
	var town: Node2D = load("res://scenes/town.tscn").instantiate()
	root.add_child(town)
	var built: Dictionary = town.set_town_state(state)
	check(bool(built.get("ok", false)),
		"the town still builds without the field: %s" % built.get("error"))
	if not bool(built.get("ok", false)):
		town.free()
		return
	var hud: Variant = town.hud()
	check_eq(hud.displayed("energy"), "[missing: energy]",
		"the missing field renders an indicator naming it")
	check(hud.displayed("energy").find("50") == -1,
		"the indicator carries no fabricated number")
	check_eq(hud.displayed("mana"), "0",
		"present fields stay verbatim beside the missing one")
	check_eq(hud.displayed("gold"), "2000",
		"the primary currency is unaffected by an absent energy field")
	# Exactly one row fails closed, named, and the rest still render.
	check_eq(ResourceProjection.absent_rows(state), ["energy"],
		"the absent-field rows are exactly the one the payload omitted")
	check_eq(hud.displayed_fields().size(), EXPECTED.size(),
		"the readout still renders every row, present or absent")
	var root_slot: Control = town.ui.slot_root("hud")
	var indicator_rows := 0
	for child in root_slot.get_children():
		for row in child.get_children():
			if row is Label and str(row.text) == "Energy: [missing: energy]":
				indicator_rows += 1
	check_eq(indicator_rows, 1,
		"the on-screen row names the missing field exactly once")
	town.free()


## Fail-closed envelopes: each rejection names its condition.
func _check_envelopes(state: Variant) -> void:
	var hud: TownHud = TownHud.new()
	var null_state: Dictionary = hud.attach(null, null)
	check(not bool(null_state.get("ok", true)),
		"a null state fails the attach")
	check(String(null_state.get("error", "")).contains("state_missing"),
		"the null-state rejection names the condition: %s"
		% null_state.get("error"))
	var null_ui: Dictionary = hud.attach(null, state)
	check(not bool(null_ui.get("ok", true)),
		"a null UI foundation fails the attach")
	check(String(null_ui.get("error", "")).contains(
		"ui_foundation_unavailable"),
		"the null-UI rejection names the condition: %s"
		% null_ui.get("error"))
	check_eq(hud.displayed_fields(), {},
		"rejected attaches leave no committed display")
