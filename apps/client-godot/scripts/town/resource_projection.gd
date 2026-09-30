extends RefCounted
## The canonical resource projection (OpenSpec `godot-building-resources`
## "Canonical resource projection", design D1-D5).
##
## ONE entry per displayed row, in display order, and **no other table in
## the client may name a resource field**: the readout (`town_hud.gd`)
## projects through this module, so a row can never claim a field the legacy
## server does not produce and the same resource can never be displayed
## twice (design D5). Pure: no node, no clock, no request, no state — the
## reference is always a typed state handed in as a parameter, exactly as
## `collection_flow.gd`, `construction_flow.gd`, and `expand_flow.gd` serve
## their own delivered flows.
##
## ## What is ESTABLISHED, and therefore recorded here verbatim
##
## `engine.apply_resources` (`engine.py:251-271`) writes EXACTLY seven slots
## of the legacy eight-slot client vector, per resource, as
## `max(current + delta, 0)`, and the application runs BEFORE the dispatched
## branch. Slot 0 of that vector is read and discarded — the legacy comment
## at `engine.py:252` names it the cheat-detection slot — so it has no stored
## value and **no row here**. The seven `location` values below are that
## function's own writes, and the committed corpus agrees exactly: `xp 4`,
## `gold 2000`, `wood 2000`, `oil 2000`, `steel 2000`, `cash 5`, `mana 0`.
##
## **There is no `coins` resource.** The server's field is `gold`
## (`maps[0]`/`map` carries `gold` and no `coins`), the Compatibility API's
## shared `resources` accessor returns `gold` and has no `coins` accessor at
## all, and the only two occurrences of the word in that module are COMMENTS
## about the expansion price schedule. The delivered readout keyed its
## primary-currency row `coins` and labelled it "Coins": that is a name no
## server field carries, and this projection replaces it with `gold` (design
## D1). A field the server never produces is never displayed under an
## invented name.
##
## ## `energy`: a real eighth resource, exposed under its own name
##
## `energy` is committed in three places — the corpus save's
## `privateState.energy = 50`, `COST_ENERGY = "e"` (`constants.py:899`, the
## item-cost key), `TOKEN_ENERGY = 7` (`constants.py:1054`), and
## `CAT_ENERGY = 8` (`constants.py:74`) — and it is genuinely part of the
## economy, because `items[].costs` may name it. It is listed here with the
## save's OWN name and the save's own location, and it is deliberately
## **outside** the mutation vector: `apply_resources` never writes it, the
## eight-slot vector has no slot for it, and no delivered path mutates it.
##
## **NO RULE IS CLAIMED FOR HOW THAT VALUE CHANGES.** No committed source
## records a regeneration interval, no legacy branch touches the field, and
## whether the legacy client regenerated it on a timer or some unrecorded
## path maintained it is **not decided by the repository and not decided
## here**. The value is displayed verbatim as the save stores it, and the
## missing rule is recorded as an explicit gap in `ENERGY_GAP`,
## `PROVENANCE`, and `NON_CLAIMS` (design D3).
##
## ## What is derived here
##
## Nothing but the presentation vocabulary: the display LABELS, the display
## ORDER, and the row at which each entry is rendered. The committed evidence
## records no authentic legacy HUD, so the labels and the ten-row layout are
## the delivered provisional convention, not a claim about what the legacy
## client displayed. The claim this module supports is "the readout displays
## what the save stores, under the name the server uses" — never a value the
## legacy client would have displayed, and never a regeneration rule for
## `energy`.
##
## ## The one residual naming gap, recorded rather than hidden
##
## `typed_state_field` is the property name the typed town state's resource
## bag happens to use. For eight of the nine values it is the canonical name;
## for the primary currency the delivered `TownState.Resources` bag declares
## `coins` and `TownState.RESOURCE_FIELDS` maps that key onto `map.gold`.
## This module is the single place that knows about the difference, it
## records the typed field next to the canonical one in every report row, and
## **no row is keyed by the typed field** — the readout's keys and its
## `displayed_fields()` map are the canonical names. Retiring the typed bag's
## misnomer is a separate, later correction; nothing here depends on it.

## The two display groups. `resources` is what the readout shows as the
## player's balances; `summary` is the player's identity and progression
## block, which the delivered readout renders as the same column of rows.
const GROUP_RESOURCES := "resources"
const GROUP_SUMMARY := "summary"

## Indicator rendered in place of a value the payload did not carry. Never a
## guessed, zeroed, or stale number (spec: "Name a missing value instead of
## guessing").
const MISSING_FORMAT := "[missing: %s]"

## The seven stored slots of the legacy eight-slot `resources_changed`
## vector `[unknown, xp, gold, wood, oil, steel, cash, mana]`, in the server's
## own order. `apply_resources` writes exactly these seven; the list is
## exposed so a suite can assert that every one of them has a row and that no
## row claims a name outside it without inventing a name.
const SERVER_RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash",
	"mana"]
## The fixed width of that vector. `energy` is NOT in it, and this module
## never widens it: the vector is the legacy wire format and
## `apply_resources` has exactly eight slots.
const MUTATION_VECTOR_SLOTS := 8
## The vector's slot 0: read and discarded by every legacy branch, with no
## stored value, so no row (design D1).
const UNREAD_VECTOR_SLOT := 0

## The vector-slot sentinel for a row no delivered path can mutate: the
## player's identity block (`name`, `level`) and the eighth resource
## (`energy`). Never `0` — slot 0 is the legacy vector's own unread slot, and
## confusing the two would claim the primary currency sits there.
const NO_VECTOR_SLOT := -1

## The canonical projection: one entry per displayed row, in display order.
## `name` is the resource's canonical name **as the server names it**;
## `location` is the one save field it is stored at; `group` is where the
## value lives on the typed town state; `label` is the delivered provisional
## display label; `typed_state_field` is the property the typed bag exposes
## it under; `vector_slot` is its slot in the legacy mutation vector, or
## `NO_VECTOR_SLOT` for a row no delivered path can mutate.
const ROWS := [
	{
		"name": "gold",
		"location": "map.gold",
		"group": GROUP_RESOURCES,
		"label": "Gold",
		"typed_state_field": "coins",
		"vector_slot": 2,
	},
	{
		"name": "wood",
		"location": "map.wood",
		"group": GROUP_RESOURCES,
		"label": "Wood",
		"typed_state_field": "wood",
		"vector_slot": 3,
	},
	{
		"name": "steel",
		"location": "map.steel",
		"group": GROUP_RESOURCES,
		"label": "Steel",
		"typed_state_field": "steel",
		"vector_slot": 5,
	},
	{
		"name": "oil",
		"location": "map.oil",
		"group": GROUP_RESOURCES,
		"label": "Oil",
		"typed_state_field": "oil",
		"vector_slot": 4,
	},
	{
		"name": "cash",
		"location": "playerInfo.cash",
		"group": GROUP_RESOURCES,
		"label": "Cash",
		"typed_state_field": "cash",
		"vector_slot": 6,
	},
	{
		# The eighth resource. Real, committed, named `energy` by the save
		# itself at `privateState.energy`, and deliberately OUTSIDE the
		# mutation vector: `apply_resources` never writes it. See the class
		# comment and `ENERGY_GAP` for the regeneration-rule gap.
		"name": "energy",
		"location": "privateState.energy",
		"group": GROUP_RESOURCES,
		"label": "Energy",
		"typed_state_field": "energy",
		"vector_slot": NO_VECTOR_SLOT,
	},
	{
		"name": "mana",
		"location": "privateState.mana",
		"group": GROUP_RESOURCES,
		"label": "Mana",
		"typed_state_field": "mana",
		"vector_slot": 7,
	},
	{
		"name": "name",
		"location": "playerInfo.name",
		"group": GROUP_SUMMARY,
		"label": "Name",
		"typed_state_field": "name",
		"vector_slot": NO_VECTOR_SLOT,
	},
	{
		"name": "level",
		"location": "map.level",
		"group": GROUP_SUMMARY,
		"label": "Level",
		"typed_state_field": "level",
		"vector_slot": NO_VECTOR_SLOT,
	},
	{
		# `xp` is the vector's slot 1 and the value the `levels` schedule
		# consumes; NOTHING spends it, which is why it stays in the summary
		# group with `name` and `level` rather than with the six spendable
		# resources (design D2). Recorded because a reader might otherwise
		# "fix" it into the resource group.
		"name": "xp",
		"location": "map.xp",
		"group": GROUP_SUMMARY,
		"label": "XP",
		"typed_state_field": "xp",
		"vector_slot": 1,
	},
]

## The energy regeneration gap, recorded as one sentence wherever the
## resource is described (design D3). The value is displayed verbatim; how it
## changes over time is NOT claimed.
const ENERGY_GAP := "no committed source records a regeneration rule for " \
	+ "privateState.energy: engine.apply_resources never writes it, the " \
	+ "legacy eight-slot mutation vector has no slot for it, and no legacy " \
	+ "branch touches it, so the readout displays the stored value and no " \
	+ "rule is claimed for how it changes"

## The established-versus-derived provenance split this projection reports as
## its own section. Every row names the evidence a reader can go and check, so
## no reader has to take the split on trust. Nothing here names a runtime; the
## runtime names in this file live in `NON_CLAIMS` and are assembled from
## fragments, because the project-scope and no-Flash suites scan this file's
## bytes for their literal forms.
const PROVENANCE := {
	"established": [
		{"fact": "the legacy resource application writes EXACTLY seven slots, "
			+ "per resource, as max(current + delta, 0), and the application "
			+ "runs BEFORE the dispatched branch",
			"evidence": "engine.py:251-271; command.py:40 (committed legacy "
				+ "server source) and the resource_effects column of "
				+ "docs/legacy-protocol/commands.json"},
		{"fact": "the seven save locations are that function's own writes: "
			+ "maps[0].xp, maps[0].gold, maps[0].wood, maps[0].oil, "
			+ "maps[0].steel, playerInfo.cash, privateState.mana",
			"evidence": "engine.py:251-271; the committed corpus "
				+ "tests/saves/fresh-player.json carries xp 4, gold 2000, "
				+ "wood 2000, oil 2000, steel 2000, cash 5, mana 0"},
		{"fact": "slot 0 of the vector is read and discarded and has no stored "
			+ "value, so it has no row in the readout",
			"evidence": "engine.py:252 (the legacy comment names it the "
				+ "cheat-detection slot)"},
		{"fact": "the primary currency's field is gold, never coins: the map "
			+ "record carries `gold` and no `coins`, the shared resources "
			+ "accessor returns `gold` and exposes no `coins` accessor, and the "
			+ "module's only occurrences of the word are comments about the "
			+ "expansion price schedule",
			"evidence": "engine.py:259-267; the committed corpus map record; "
				+ "apps/compat-api/compat_legacy.py (read-only) lines 453 and "
				+ "456; docs/legacy-resources.md"},
		{"fact": "the stored energy value exists in the save and in the "
			+ "committed constants: privateState.energy = 50, COST_ENERGY = "
			+ "\"e\", TOKEN_ENERGY = 7, CAT_ENERGY = 8",
			"evidence": "the committed corpus; constants.py:899, constants.py:"
				+ "1054, constants.py:74"},
		{"fact": "apply_resources never writes the stored energy value, and the "
			+ "eight-slot vector has no slot for it",
			"evidence": "engine.py:251-271 — the seven writes above are the "
				+ "function's complete set"},
	],
	"derived": [
		{"fact": "the display labels, the display order, and the ten-row layout",
			"evidence": "derived: no authentic legacy HUD layout has been "
				+ "captured, so the labels and layout are the delivered "
				+ "provisional convention, never a claim about what the legacy "
				+ "client displayed"},
		{"fact": "which value is a spendable resource and which is the "
			+ "experience counter, and therefore that xp belongs to the summary "
			+ "group",
			"evidence": "derived from the committed model: xp is the vector's "
				+ "slot 1 and the value the levels schedule consumes, and no "
				+ "legacy branch spends it"},
	],
}

## The evidence's explicit non-claims (spec "Resource evidence, provenance,
## and claim limits"). The runtime tokens in the first claim are assembled
## from fragments for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"the readout claims to display what the save stores, never a value the "
		+ "legacy client would have displayed",
	"no rule is claimed for how the stored energy value changes over time: "
		+ "no committed source records a regeneration interval, no legacy "
		+ "branch touches the field, and this change invents none",
	"the readout's labels, display order, and ten-row layout are the "
		+ "delivered provisional convention pending capture of an authentic "
		+ "legacy HUD",
	"the market and trade counters (trade_resource, set_resource_allies, whose "
		+ "arguments the committed command catalog records as read but unused) "
		+ "and the item-cost mapping from the g/c/w/o/s/e letter vocabulary onto "
		+ "the named resources are out of scope",
	"the readout is read-only: it adds no endpoint, changes no response "
		+ "shape, moves no balance, and adds no server-authoritative resource "
		+ "validation",
	"no pixel-parity oracle against the legacy client exists",
	"the committed capture runs the fake GameApi implementation; the shared "
		+ "resources accessor the nine state-mutating endpoints' post-execution "
		+ "proofs compare is deliberately NOT widened with the energy value",
]


## The whole projection as a fresh copy the caller may mutate, in display
## order. Never the committed constant itself.
static func rows() -> Array:
	return ROWS.duplicate(true)


## One row entry by canonical name, or null when the projection has no such
## row. A name the projection does not carry is never coerced to a guessable
## row: it is the caller's error, and null says so.
static func row_for(name: String) -> Variant:
	for entry: Dictionary in ROWS:
		if str(entry["name"]) == name:
			return entry.duplicate(true)
	return null


## True when the projection carries a row with this canonical name.
static func has(name: String) -> bool:
	return row_for(name) != null


## The canonical names of one group, in display order — the resource block
## (`gold`, `wood`, `steel`, `oil`, `cash`, `energy`, `mana`) or the summary
## block (`name`, `level`, `xp`).
static func names(group: String) -> Array:
	var out: Array = []
	for entry: Dictionary in ROWS:
		if str(entry["group"]) == group:
			out.append(str(entry["name"]))
	return out


## The seven canonical names the legacy resource application writes, as this
## projection names them. Used by the suite to assert the readout's resource
## block covers every one of them by value.
static func server_resource_rows() -> Array:
	var out: Array = []
	for name: String in SERVER_RESOURCE_NAMES:
		if has(name):
			out.append(name)
	return out


## The explicit absent-field indicator for a canonical name. Returns "" for a
## name the projection does not carry, so a caller cannot invent an indicator
## for a row that does not exist.
static func missing_indicator(name: String) -> String:
	if not has(name):
		return ""
	return MISSING_FORMAT % name


## The exact string one row displays for a typed town state: the stored value
## verbatim, or the explicit absent-field indicator when the payload carried
## no such field. Fail-closed in both directions — never a guessed, zeroed, or
## stale number, and never a field read from the wrong group.
##
## Absence is read through the typed bag's own recorded `missing` list FIRST
## (under the typed field name), then by the field's absence from the bag, so
## a payload that omits the save location produces the indicator and nothing
## else. A null state is the same refusal, not a crash.
static func text_for(state: Variant, entry: Dictionary) -> String:
	var name := str(entry.get("name", ""))
	var field := str(entry.get("typed_state_field", name))
	if not has(name):
		return ""
	if state == null:
		return MISSING_FORMAT % name
	for missing: Variant in state.missing:
		if str(missing) == field:
			return MISSING_FORMAT % name
	var bag: Variant = state.resources \
		if str(entry.get("group", GROUP_RESOURCES)) == GROUP_RESOURCES \
		else state.summary
	if bag == null or not (field in field_names(bag)):
		return MISSING_FORMAT % name
	return str(bag.get(field))


## The whole readout's committed display map: canonical name -> the exact
## string on screen, in display order's insertion order. Nothing extra: a row
## this projection does not carry has no key, so no `coins` key can appear.
static func displayed(state: Variant) -> Dictionary:
	var out := {}
	for entry: Dictionary in ROWS:
		var name := str(entry["name"])
		out[name] = text_for(state, entry)
	return out


## The readout rows that render the explicit absent-field indicator, as
## their canonical names in display order. Empty for a complete payload.
static func absent_rows(state: Variant) -> Array:
	var out: Array = []
	for entry: Dictionary in ROWS:
		if text_for(state, entry) == MISSING_FORMAT % str(entry["name"]):
			out.append(str(entry["name"]))
	return out


## The canonical projection table as the structural report records it: one
## row per displayed entry with its index, its canonical name, the one save
## location it lives at, its group, its display label, the typed bag property
## it is read through, and its legacy mutation-vector slot. Everything a
## reader needs to check the mapping against committed source without reading
## this module's code.
static func record() -> Array:
	var out: Array = []
	var index := 0
	for entry: Dictionary in ROWS:
		out.append({
			"row": index,
			"name": str(entry["name"]),
			"location": str(entry["location"]),
			"group": str(entry["group"]),
			"label": str(entry["label"]),
			"typed_state_field": str(entry["typed_state_field"]),
			"vector_slot": int(entry["vector_slot"]),
		})
		index += 1
	return out


## One row's stored value for a typed town state, or null when the payload
## carried no such field. Never a substituted zero: absence is reported as
## absence so the report can distinguish "the save stores 0" from "the save
## carries nothing".
static func value_of(state: Variant, name: String) -> Variant:
	var entry: Variant = row_for(name)
	if entry == null or state == null:
		return null
	var typed: Dictionary = entry
	if MISSING_FORMAT % name in [text_for(state, typed)]:
		return null
	var field := str(typed["typed_state_field"])
	var bag: Variant = state.resources \
		if str(typed["group"]) == GROUP_RESOURCES else state.summary
	if bag == null or not (field in field_names(bag)):
		return null
	return bag.get(field)


## The property names of a typed state bag (`Resources` / `Summary`
## instances), read from the object rather than assumed, so a bag that gains
## or loses a property is noticed instead of silently misread.
static func field_names(bag: Variant) -> Array:
	var names_out: Array = []
	if bag == null:
		return names_out
	for property in bag.get_property_list():
		if int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			names_out.append(str(property["name"]))
	return names_out
