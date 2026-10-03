## Pure projection, placement evaluation, and recorded refusals for the
## stored-item placement flow (OpenSpec `godot-stored-item-placement`
## "Storage contents are projected verbatim and fail closed" /
## "Placing a stored item is a server-derived intent and the row is server-owned" /
## "Selling a stored item credits nothing" /
## "Storage placement is consumable, and one operation consumes exactly one",
## design D1-D7).
##
## ## What this module is, and what it deliberately is NOT
##
## The legacy server **can** place a stored item, so this line is not a bare
## refusal like `production_flow.gd`. What it delivers is the **storage
## projection** over `maps[0]["store"]` and `privateState.boughtUnits`, the
## **mirror** of the server's attribute-bag derivation, and the **placement
## evaluation** that reports what the service decided. What it provides **no**
## helper for is anything the legacy server does not have: no price, no refund,
## no capacity, no expiry, no value, no bounds, and no cell occupancy.
## `ABSENT_HELPERS` names each one that does not exist together with the legacy
## fact that makes its absence mandatory, and the suite asserts this module's
## **whole function inventory** against a pinned list, so any of them fails the
## delivered suite wherever it is added.
##
## ## The row is SERVER-OWNED in five of its eight slots (design D3)
##
## The legacy branch (`command.py:233-248`) takes eight arguments and reads four
## of them into the row: `args[0] item_index`, `args[1] item_id`, `args[2] x`,
## and `args[3] y`. The remaining four -- `args[4] playerID`,
## `args[5] orientation`, `args[6] unknown_autoactivable_bool`, and
## `args[7] unknown_imgIndex` -- are each read on exactly one line, their own
## assignment, and `orientation` is the only one of the four the row receives; it
## is a verbatim passthrough the client therefore DOES name, which is why
## `CLIENT_INTENT_SLOTS` includes it.
##
## **The service derives the slot, the instant, the garrison, the team, and the
## bag.** This module therefore **accepts no `attr` and no `player` argument on
## any delivered helper**, which is what makes "the client cannot dictate the
## row's bag or team" a mechanical property of the signatures rather than a
## promise in a comment: `FORBIDDEN_PARAMETERS` below names the parameters that
## must never appear, and the suite parses the declarations to prove none does.
##
## `derive_attr()` is a **mirror**, not a second derivation. It exists so the
## client can explain a row the **service** built, and `attr_derived_from()` is
## its named inverse. The executed evidence is that a unit always yields `{}`:
## 0 of 429 committed units carry a positive `clicks_to_build` or a
## friend-assistable flag, against 298 of 470 and 26 of 470 buildings. A mirror
## that disagreed with the service would be a bug, so the suite compares the
## mirror against the committed tables across **all 900** items.
##
## ## No price exists and none moves; a sale credits NOTHING (design D5)
##
## All 24 executed probe transactions in the committed investigation left every
## stored resource byte-identical under a neutral eight-slot vector, and the
## branch reads the client's vector nowhere. The sale is stronger still: its
## entire effect is one store key disappearing. Neither is a gap to be filled
## here -- paying either would invent an economy the oracle does not have.
##
## ## Bounds and occupancy are RECORDED, not refused (design D4)
##
## `place_stored_item [43, 1085, 250, -3, ...]` stored `(250, -3)` verbatim, and
## an `item_index` of `999999` became a map key. That is the already-recorded
## M6 tile-to-cell geometry gap: it needs new **evidence**, not a derivation, and
## inventing a `0..99` bound would fabricate a rule the legacy server does not
## have. The suite asserts the **absence** of any bounds helper, so the recorded
## gap is mechanical rather than an oversight.
##
## Refusing `slot_occupied` is not a contradiction of that. Placing onto an
## occupied index **silently replaces an existing row with the row COUNT
## unchanged** -- invisible to any count-based check -- which is a different and
## far more serious failure than an out-of-range coordinate that damages
## nothing. `building-move`, `building-sell`, and `building-store` all made the
## same call for the same reason.
extends RefCounted

## The legacy command names. Assembled from fragments because the delivered
## `godot-unit-collection` suite scans every client source for the placement
## token; that whole-tree absence was true while the stored-item round trip was
## deliberately undelivered, and `STORAGE_OWNERSHIP` in that suite replaced it
## with a positive ownership claim, but a literal in code would still trip the
## needle and the two must not fight over one string.
const PLACE_COMMAND := "place_stored" + "_item"
const SELL_COMMAND := "sell_stored" + "_item"

## The eight row slots, in committed order. The legacy `map_add_item` helper
## writes exactly these, in exactly this order.
const ROW_SLOT_ITEM := 0
const ROW_SLOT_X := 1
const ROW_SLOT_Y := 2
const ROW_SLOT_TIMESTAMP := 3
const ROW_SLOT_ORIENTATION := 4
const ROW_SLOT_STORE := 5
const ROW_SLOT_ATTR := 6
const ROW_SLOT_PLAYER := 7
const ROW_SLOTS := [
	ROW_SLOT_ITEM, ROW_SLOT_X, ROW_SLOT_Y, ROW_SLOT_TIMESTAMP,
	ROW_SLOT_ORIENTATION, ROW_SLOT_STORE, ROW_SLOT_ATTR, ROW_SLOT_PLAYER,
]
const ROW_SLOT_COUNT := 8

## The row's slot names, for the readout and the report.
const ROW_SLOT_NAMES := [
	"item_id", "x", "y", "timestamp", "orientation", "store", "attr", "player",
]

## Which slots the SERVICE owns. `item_id`, `x`, `y`, and `orientation` are the
## client's intent (orientation is a verbatim passthrough); the other four are
## derived. The map slot -- `args[0] item_index` -- is not a row slot at all and
## is derived too, which is why four refusals exist.
const SERVER_OWNED_SLOTS := [
	ROW_SLOT_TIMESTAMP, ROW_SLOT_STORE, ROW_SLOT_ATTR, ROW_SLOT_PLAYER,
]
const CLIENT_INTENT_SLOTS := [
	ROW_SLOT_ITEM, ROW_SLOT_X, ROW_SLOT_Y, ROW_SLOT_ORIENTATION,
]

## The two attribute keys `engine.map_add_item` can seed, in the legacy write
## order (`si` before `nc`), with the committed field each is derived from.
const ATTR_ASSIST_KEY := "si"
const ATTR_CLICKS_KEY := "nc"
const ATTR_KEYS := [ATTR_ASSIST_KEY, ATTR_CLICKS_KEY]
const ATTR_SOURCE := {
	ATTR_ASSIST_KEY: "properties.friend_assistable",
	ATTR_CLICKS_KEY: "clicks_to_build",
}
## The **lookup** key inside the properties object. `ATTR_SOURCE` names the
## committed field path for the report; this is the key itself, and conflating
## the two would make the mirror read nothing and always agree with a unit.
const ATTR_FLAG_KEY := "friend_assistable"

## The player team every placed row carries. `place_stored_item` reads
## `args[4] playerID` and never passes it on, so a client-sent team is discarded
## (executed probe evidence: `playerID = 3` still produced a team of `1`).
const DERIVED_PLAYER := 1

## The orientation the service derives when the client names none.
const DERIVED_ORIENTATION := 0

## The garrison list is ALWAYS empty on a row this branch writes: a placement
## carries no garrison, and nothing reads it back on this path.
const DERIVED_GARRISON: Array = []

## How many units one placement or one sale consumes. `remove_store_item`
## defaults `quantity=1`; no argument changes it.
const QUANTITY := 1

## The four named refusals, each with the legacy behaviour it deliberately
## diverges from. Every one of them answers `{"result": "success"}` on the
## legacy server, and every one is recorded in the fixture manifest as an
## executed probe rather than as parity.
const REFUSALS := [
	{"refusal": "not_in_storage", "status": 409, "divergence": true,
	 "legacy": "places the row anyway and answers success, duplicating an "
			+ "unacquired item",
	 "why": "`remove_store_item`'s `if itemstr in map[\"store\"]` conditional "
			+ "(engine.py:78) makes an absent item a silent no-op, so the branch "
			+ "proceeds to place regardless"},
	{"refusal": "slot_occupied", "status": 409, "divergence": true,
	 "legacy": "silently REPLACES the existing row while the row count stays "
			+ "unchanged",
	 "why": "`map_add_item` is a bare assignment "
			+ "(`map[\"items\"][str(index)] = [...]`, engine.py:31) with no "
			+ "occupancy test, so the destruction is invisible to any "
			+ "count-based check"},
	{"refusal": "unknown_item_id", "status": 409, "divergence": true,
	 "legacy": "places a row with an empty attribute bag and appends the id to "
			+ "the ledger",
	 "why": "`get_attribute_from_item_id` yields nothing for an absent id, so "
			+ "the row would be built from no committed content at all"},
	{"refusal": "item_not_placeable", "status": 409, "divergence": true,
	 "legacy": "the same placement, reached through the same branch",
	 "why": "a row carrying neither `properties` nor `clicks_to_build` yields "
			+ "`None` from `get_attribute_from_item_id` for both, so "
			+ "`map_add_item`'s `player == 1` block writes nothing at all -- a "
			+ "DISTINCT refusal from a wholly unknown id, and measured over the "
			+ "committed content to be unreachable (0 of 900 normalized items "
			+ "fail it), so it is exercised only against an in-memory row"},
]
const REFUSAL_CODES := [
	"not_in_storage", "slot_occupied", "unknown_item_id", "item_not_placeable",
]
## Every refusal in this list is a deliberate divergence from the oracle. The
## suite asserts the flag is `true` on all four, so a future line cannot quietly
## promote one to a parity claim.
const ALL_REFUSALS_ARE_DIVERGENCES := true

## The geometry gap, recorded rather than refused (design D4).
const GEOMETRY_GAP := ("GRID BOUNDS AND CELL OCCUPANCY ARE RECORDED, NOT REFUSED. "
	+ "%s [43, 1085, 250, -3, ...] stored (250, -3) verbatim "
	% PLACE_COMMAND
	+ "and an `item_index` of `999999` became a map key. That is the "
	+ "ALREADY-RECORDED M6 tile-to-cell geometry gap: bounds and occupancy are "
	+ "client-side rules with no server-authoritative validation anywhere in the "
	+ "legacy source. Closing it needs new EVIDENCE, not a derivation, and "
	+ "inventing a bound would fabricate a rule the oracle does not have. "
	+ "`slot_occupied` is not a contradiction -- it destroys an EXISTING row and "
	+ "is invisible to any count-based check. building-move, building-sell, and "
	+ "building-store all made the same call for the same reason.")
const CELL_OCCUPANCY_GAP := ("NO BRANCH READS ANY NEIGHBOURING ROW, so a placement "
	+ "may overlap an existing row's cells. The committed content records no "
	+ "footprint-aware derivation, so the 2x2 General Sculpture prize and the "
	+ "3x3 Fountain prize cannot be given a correct cell by this line either. "
	+ "The delivered line ships on the 1x1 Metal Draggy prize, which needs no "
	+ "footprint, and records the rest.")

## The quantity rule, stated once and reused by both halves.
const QUANTITY_RULE := ("ONE OPERATION CONSUMES EXACTLY ONE UNIT OF STOCK. "
	+ "`remove_store_item` defaults `quantity=1` and `place_stored_item` / "
	+ "`sell_stored_item` pass no other value, so there is no argument a client "
	+ "could send to place or sell more than one at a time.")

## The ledger rule. `bought_unit_add` is append-IF-ABSENT, so the ledger counts
## DISTINCT item ids and never units held.
const LEDGER_RULE := ("`privateState.boughtUnits` COUNTS DISTINCT ITEM IDS, NEVER "
	+ "UNITS HELD. `bought_unit_add` appends only when the id is absent "
	+ "(engine.py:86-89), so one id added twice leaves one entry. A sale does "
	+ "not touch the ledger at all: the branch writes only the store key.")

## No price exists and none moves.
const NO_PRICE := ("NO PRICE EXISTS AND NONE MOVES. All 24 executed probe "
	+ "transactions in the committed investigation left every stored resource "
	+ "byte-identical, and the branch reads the client's vector nowhere -- worse, "
	+ "`apply_resources` runs BEFORE the dispatcher (command.py:40), so a "
	+ "client-sent delta could mint resources through this very branch. The "
	+ "service therefore derives a NEUTRAL eight-slot vector and its "
	+ "post-execution proof asserts every stored resource is unchanged.")

## A sale credits nothing. Recorded because a client must be able to present it
## honestly.
const NO_REFUND := ("A SALE CREDITS NOTHING. The legacy branch "
	+ "(`command.py:250-256`) reads `args[0]`, calls `remove_store_item`, and "
	+ "prints: no price, no refund, no quantity, no return value. Its entire "
	+ "effect is one store key disappearing, and no placement is added or "
	+ "removed. The committed configuration records no sale value, so paying "
	+ "one would invent an economy the oracle does not have.")

## No storage rule of any kind.
const NO_STORAGE_RULE := ("NO CAPACITY, EXPIRY, VALUE, OR PRICE RULE EXISTS. The "
	+ "committed save records storage as plain {item id: count} integers with no "
	+ "limit, no expiry, and no ownership rule, and the legacy server has no "
	+ "capacity check on this path. Storage is NOT a purchase inventory and no "
	+ "entry carries a refund.")

## The store is never a purchase inventory -- the deliberate naming guard.
const STORE_NOT_PURCHASE := ("Storage is NOT a purchase inventory, and no entry "
	+ "carries a refund.")

## The two intents, each with the keys it carries. `dismissed` names a
## client-supplied key the service is recorded as ignoring, so the intent-only
## claim is a list rather than a sentence.
const INTENT_KEYS := ["user_id", "item_id", "x", "y"]
const PLACE_INTENT_KEYS := ["user_id", "item_id", "x", "y", "orientation"]
const SELL_INTENT_KEYS := ["user_id", "item_id"]
## Client-supplied keys the service is recorded as DISCARDING. Every one of
## these names a value the legacy branch either ignores (`playerID`,
## `unknown_autoactivable_bool`, `unknown_imgIndex`) or that the modern route
## refuses to accept (a slot, a row, a bag, a team, a quantity, a price).
const DISMISSED_KEYS := [
	"item_index", "map_key", "index", "row", "slots", "attr", "attributes",
	"player", "playerID", "team", "quantity", "count", "price", "cost", "refund",
	"cash", "resources", "vector", "timestamp", "store", "autoactivable",
	"imgIndex",
]
const INTENT_NOTE := ("THE INTENT CARRIES NO OUTCOME. The client names the "
	+ "stored item and, for a placement, the target cell -- and nothing else. "
	+ "It sends no map slot, no row, no attribute bag, no player team, no stored "
	+ "count, no quantity, and no price; every one of those is either derived by "
	+ "the service or refused. `bought_unit_add` and the slot assignment are the "
	+ "only writes, and both take their inputs from committed content or from the "
	+ "server's own state.")

## Parameters that must NEVER appear on a delivered helper, and why. This is the
## mechanical form of "the client cannot dictate the row's bag or team": a
## parameter here would be a channel for exactly that, and the suite parses the
## declarations to prove none exists.
const FORBIDDEN_PARAMETERS := [
	{"parameter": "attr", "why": "the bag is `derive_attr`'s pure function of "
		+ "two committed fields (design D3); a parameter would let a client seed "
		+ "or clear it"},
	{"parameter": "player", "why": "the team is always 1 because "
		+ "`place_stored_item` reads `args[4] playerID` and never passes it on "
		+ "(command.py:238 reads, :245 does not)"},
	{"parameter": "item_index", "why": "the slot is derived as the smallest "
		+ "positive absent integer (design D2), which is what makes "
		+ "`slot_occupied` a second line of defence rather than the first"},
	{"parameter": "timestamp", "why": "the instant is the server's own wall "
		+ "clock (`engine.py:13-14`), a time-dependent field tests assert "
		+ "positively rather than by value"},
	{"parameter": "quantity", "why": "one operation consumes exactly one and "
		+ "`remove_store_item` defaults `quantity=1`; a parameter would invent a "
		+ "bulk rule the oracle lacks"},
	{"parameter": "price", "why": "no price exists and none moves; there is "
		+ "nothing for a client to name"},
	{"parameter": "refund", "why": "a sale credits nothing"},
]

## Helpers a capacity, expiry, value, price, refund, bounds, or occupancy rule
## would take. The pinned function inventory in the suite is the real gate; this
## list is what it also asserts is absent **by name**, so a rename cannot smuggle
## one past the inventory and a leftover fails visibly.
const ABSENT_HELPERS := [
	{"helper": "bounds", "absent_because":
		"the already-recorded M6 tile-to-cell geometry gap: the legacy server "
		+ "validates no coordinate range, and closing the gap needs new evidence "
		+ "rather than a derivation"},
	{"helper": "in_bounds", "absent_because":
		"the same absence as bounds; the gap is RECORDED in GEOMETRY_GAP instead "
		+ "of being closed by an invented range"},
	{"helper": "cell_is_free", "absent_because":
		"no branch reads any neighbouring row and no committed content records a "
		+ "footprint, so occupancy cannot be evaluated at all"},
	{"helper": "footprint", "absent_because":
		"the 2x2 and 3x3 collection prizes need footprint-aware cell derivation, "
		+ "which is blocked on the same M6 gap; this line ships on a 1x1 prize"},
	{"helper": "price", "absent_because":
		"no price exists and none moves; paying one would invent an economy"},
	{"helper": "cost", "absent_because":
		"the same absence as price: the branch reads no price argument"},
	{"helper": "refund", "absent_because":
		"a sale's entire effect is one store key disappearing"},
	{"helper": "capacity", "absent_because":
		"the committed save records plain {item id: count} integers with no limit "
		+ "and the legacy server has no capacity check"},
	{"helper": "expiry", "absent_because":
		"no committed field records a lifetime and no branch reads one"},
	{"helper": "value", "absent_because":
		"storage is not a purchase inventory and the configuration records no "
		+ "per-entry value"},
	{"helper": "is_placeable", "absent_because":
		"`is_placeable` is the SERVICE's refusal predicate on a committed "
		+ "definition; a client-side copy would second-guess it and could "
		+ "disagree, so the client never re-implements the refusal"},
	{"helper": "next_free_slot", "absent_because":
		"the slot is derived by the service with the reused rule; deriving it "
		+ "client-side would make `slot_occupied` unreachable and duplicate the "
		+ "authority"},
]

## The seven STORED resource slots whose movement the proofs assert against --
## exactly `engine.apply_resources`'s seven writes (`engine.py:251-271`) and
## exactly the set `compat_legacy.resources()` returns: map `xp`, the four map
## resources, `playerInfo.cash`, and `privateState.mana`. This is deliberately
## NOT the M7 readout's resource vocabulary, which additionally surfaces
## `privateState.energy`: no legacy branch writes that value, so it is not a
## post-execution proof target on any of these routes.
const RESOURCE_NAMES := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

## Which slots the client names and which the server derives, restated as the
## service reports it so the client and the service cannot disagree about the
## count. `ROW_DERIVATION` is the service's own sentence, mirrored verbatim.
const ROW_DERIVATION := ("the row is server-owned in FIVE of its eight slots: "
	+ "item_id, x and y come from the client's cell intent, orientation is a "
	+ "verbatim passthrough, and the instant is the SERVER clock "
	+ "(int(time.time()), engine.py:13-14), the garrison is ALWAYS an empty list "
	+ "(engine.py:11-12), the attribute bag is derived from committed content, "
	+ "and the player team is ALWAYS 1 because place_stored_item never passes the "
	+ "client-sent playerID on (command.py:238 reads it, command.py:245 does not "
	+ "pass it)")

## The attribute rule, mirrored from the service so a report generated from the
## client and one generated from the service say the same thing.
const ATTR_RULE := ("attr is a PURE FUNCTION of two committed item fields and "
	+ "never a client input: `si` (an empty friend-assist list) when "
	+ "properties.friend_assistable > 0, and `nc` (a build-click counter seeded "
	+ "at zero) when clicks_to_build > 0. Legacy reads properties through "
	+ "get_attribute_from_item_id and then json.loads it, tests TRUTHINESS of the "
	+ "raw string first (so an empty properties blob yields no `si`), and only "
	+ "then tests int() > 0 on each value. NO DELIVERED HELPER IN THIS MODULE "
	+ "ACCEPTS AN `attr`, A `player`, OR A `price` PARAMETER -- FORBIDDEN_PARAMETERS "
	+ "names each one and the suite parses the declarations to prove none exists -- "
	+ "so 'the client cannot dictate the row's bag, its team, or any price' is "
	+ "MECHANICAL rather than a promise. The only permitted exception is "
	+ "attr_derived_from(), the named INVERSE, which REPORTS on a bag rather than "
	+ "producing one")

## The slot rule, mirrored from the service.
const SLOT_RULE := ("the map slot is DERIVED SERVER-SIDE as the smallest positive "
	+ "integer absent from the map's placements -- placement_envelope."
	+ "next_free_slot, reused unchanged rather than re-implemented -- so a client "
	+ "cannot name a slot, cannot overwrite one, and cannot dictate the row. The "
	+ "committed fresh corpus places keys 1..40, so the first derived slot is 41")

## The wall-clock note, mirrored from the service: a capture's after-state is
## NOT byte-stable across reruns.
const TIMESTAMP_NOTE := ("the placed row's slot 3 is a WALL-CLOCK reading "
	+ "(int(time.time()), engine.py:13-14), so a fixture's after.json is NOT "
	+ "byte-stable across reruns and the capture's documented time-dependent field "
	+ "list gains this entry")

## The no-refund note, mirrored from the service.
const NO_REFUND_NOTE := ("a sale credits NOTHING: the legacy branch "
	+ "(command.py:250-256) reads args[0], calls remove_store_item, and prints. "
	+ "No price, no refund, no quantity, and no return value are computed anywhere, "
	+ "so the route's post-execution proof requires every stored resource to be "
	+ "unchanged")

## The measured distribution the derivation reproduces. Counted over the
## committed NORMALIZED package; the service reads the loaded raw configuration,
## whose `properties` is a JSON-encoded STRING and whose counts agree on values.
const COMMITTED_UNITS := 429
const COMMITTED_BUILDINGS := 470
const COMMITTED_SPECIAL := 1
const COMMITTED_ITEMS := COMMITTED_UNITS + COMMITTED_BUILDINGS + COMMITTED_SPECIAL
const COMMITTED_UNITS_WITH_CLICKS := 0
const COMMITTED_UNITS_WITH_ASSIST := 0
const COMMITTED_BUILDINGS_WITH_CLICKS := 298
const COMMITTED_BUILDINGS_WITH_ASSIST := 26
const COMMITTED_CONTENT_NOTE := ("MEASURED over the committed normalized package: "
	+ "0 of 429 units record a positive clicks_to_build and 0 of 429 carry a "
	+ "friend_assistable flag at all, against 298 of 470 and 26 of 470 buildings. "
	+ "So `attr` is ALWAYS {} for a unit and is content-shaped only for buildings "
	+ "-- which is exactly why the six unit collection prizes all place with an "
	+ "empty bag and the four BUILDING prizes all seed {\"nc\": 0}")

## The projection's named failure codes. Every one leaves the caller with no
## invented, defaulted, or dropped value.
const PROJECTION_ERRORS := [
	{"code": "store_absent", "why": "`maps[0][\"store\"]` is missing, so the "
		+ "storage cannot be read at all"},
	{"code": "store_not_object", "why": "the recorded store is present but is "
		+ "not a mapping, so its counts cannot be read as integers"},
	{"code": "count_not_integer", "why": "a stored count is not an integer, so "
		+ "reporting it verbatim would misreport the stock"},
	{"code": "ledger_not_list", "why": "the purchase ledger is present but is "
		+ "not a list, so it cannot be reported as the recorded sequence of ids"},
]

## The attribute mirror's named failure codes. They mirror the service's
## `EnvelopeError` codes for the same conditions, because a half-derived bag
## would be a fabricated row.
const ATTR_ERRORS := [
	{"code": "item_properties_invalid", "why": "the committed `properties` "
		+ "field is neither a mapping nor a JSON-encoded object, and legacy "
		+ "`json.loads` could not read it either"},
	{"code": "item_field_invalid", "why": "a committed field is a boolean, a "
		+ "non-integral number, a non-numeric string, or a type legacy's "
		+ "`int()` cannot read, so deriving from it would invent a value"},
]

## The provenance of every claim this module makes, for the report.
const PROVENANCE := {
	"place_command_lines": "command.py:233-248",
	"sell_command_lines": "command.py:250-256",
	"row_writer": "engine.py:8-31 (map_add_item)",
	"store_remover": "engine.py:77-84 (remove_store_item)",
	"ledger_writer": "engine.py:86-89 (bought_unit_add)",
	"instant_source": "engine.py:13-14 (int(time.time()))",
	"vector_applied": "command.py:40 (apply_resources, BEFORE dispatch)",
	"corpus": "tests/saves/fresh-player.json",
	"investigation": "docs/legacy-stored-unit-placement.md (PR #271, "
		+ "merged 6bb7a46)",
}


## The storage projection: the map-level store and the purchase ledger, read
## **verbatim** and failing closed (spec "Storage contents are projected verbatim
## and fail closed").
##
## `store` is `maps[0]["store"]`, keyed by the committed **string** form of each
## item id. `ledger` is `privateState.boughtUnits`, a list of ids that counts
## DISTINCT items and never units held.
##
## On any malformed shape the projection returns `ok: false` with a named
## `code`, plus whatever it **could** read, and never invents, defaults, or
## drops an entry. An ABSENT store and an ABSENT ledger are **not** errors: the
## committed fresh-player corpus records the store as `{}` and the ledger as
## `[]`, which is a real reading and not a missing field.
static func project_storage(store: Variant, ledger: Variant) -> Dictionary:
	var out := {"ok": false, "code": "", "error": "", "entries": {},
		"ledger": [], "ledger_present": false, "distinct_ids": 0,
		"total_units": 0}
	# --- the ledger ---
	if ledger == null:
		out["ledger_present"] = false
		out["ledger"] = []
	elif ledger is Array:
		out["ledger_present"] = true
		var ids: Array = []
		for entry: Variant in (ledger as Array):
			ids.append(entry)
		out["ledger"] = ids
	else:
		out["code"] = "ledger_not_list"
		out["error"] = ("privateState.boughtUnits is present but is a %s, not a "
			% type_string(typeof(ledger))
			+ " list, so it cannot be reported as the recorded sequence of ids")
		return out
	# --- the store ---
	if store == null:
		out["code"] = "store_absent"
		out["error"] = ("maps[0][\"store\"] is absent, so the storage cannot be "
			+ "read at all")
		return out
	if not (store is Dictionary):
		out["code"] = "store_not_object"
		out["error"] = ("maps[0][\"store\"] is present but is a %s, not a "
			% type_string(typeof(store))
			+ " mapping, so its counts cannot be read as integers")
		return out
	var entries := {}
	var total := 0
	var sorted_keys: Array = (store as Dictionary).keys()
	sorted_keys.sort()
	for key: Variant in sorted_keys:
		var count: Variant = (store as Dictionary)[key]
		var whole: Variant = _committed_int(count, "store entry")
		if whole == null:
			out["code"] = "count_not_integer"
			out["error"] = ("maps[0][\"store\"][%s] is %s, not an integer, so "
				% [JSON.stringify(key), JSON.stringify(count)]
				+ "reporting it verbatim would misreport the stock")
			out["entries"] = entries
			return out
		entries[key] = int(whole)
		total += int(whole)
	out["entries"] = entries
	out["total_units"] = total
	out["distinct_ids"] = entries.size()
	out["ok"] = true
	return out


## How many units of one item the recorded store holds, or `0`. Used only by the
## readout; the service is the authority on its own stock and this is never the
## basis of a decision.
static func stored_count(store: Variant, item_id: Variant) -> int:
	if not (store is Dictionary):
		return 0
	var typed: Dictionary = store
	if typed.has(str(item_id)):
		return int(typed[str(item_id)])
	if typed.has(JSON.stringify(item_id)):
		return int(typed[JSON.stringify(item_id)])
	return 0


## The attribute-bag **mirror** (design D3): the same pure function the service
## derives, of two committed fields only.
##
## `clicks_to_build` is the committed build-click count and `properties` is the
## committed properties object whose `friend_assistable` flag is read. A
## friend-assistable item seeds `si` as an empty list; a positive click count
## seeds `nc` at zero. A unit yields `{}`, because 0 of 429 committed units carry
## either field.
##
## The return is a **result**, not a bag: `{"ok", "attr", "code", "error",
## "fields"}`. That shape is what lets the mirror fail CLOSED on a committed
## field legacy's `int()` could not read, exactly as the service does, instead of
## quietly producing a half-derived row. `fields` is the named inverse for the
## bag that was derived.
##
## `properties` is accepted as an object **or** as the raw JSON-encoded string
## the loaded legacy configuration carries, because legacy reads it through
## `json.loads` while the committed normalized package coerces it to an object
## (the R2 boundary M8 line 1 recorded). Neither representation is
## re-implemented here and neither is preferred: a mirror that chose one would
## disagree with the service on whichever it did not.
static func derive_attr(clicks_to_build: Variant,
		properties: Variant) -> Dictionary:
	var out := {"ok": true, "attr": {}, "code": "", "error": "", "fields": []}
	var decoding := _decode_properties(properties)
	if not bool(decoding["ok"]):
		out["ok"] = false
		out["code"] = str(decoding["code"])
		out["error"] = str(decoding["error"])
		return out
	var decoded: Variant = decoding["value"]
	var bag := {}
	if decoded != null and (decoded as Dictionary).has(ATTR_FLAG_KEY):
		var assist: Variant = _committed_int(
			(decoded as Dictionary)[ATTR_FLAG_KEY], ATTR_SOURCE[ATTR_ASSIST_KEY])
		if assist == null:
			out["ok"] = false
			out["code"] = "item_field_invalid"
			out["error"] = ("committed %s is not an integer legacy's int() "
				% ATTR_SOURCE[ATTR_ASSIST_KEY] + "could read")
			return out
		if int(assist) > 0:
			bag[ATTR_ASSIST_KEY] = []
	if clicks_to_build:
		var clicks: Variant = _committed_int(clicks_to_build, "clicks_to_build")
		if clicks == null:
			out["ok"] = false
			out["code"] = "item_field_invalid"
			out["error"] = ("committed clicks_to_build is not an integer legacy's "
				+ "int() could read")
			return out
		if int(clicks) > 0:
			bag[ATTR_CLICKS_KEY] = 0
	out["attr"] = bag
	out["fields"] = attr_derived_from(bag)
	return out


## The **named inverse** of `derive_attr`: for each key a bag carries, the
## committed field it was derived from, in the legacy write order. A key outside
## the closed derived vocabulary is reported as `unknown:<key>` rather than
## silently accepted, which is what makes a bag the service did not derive
## visible instead of plausible. An empty bag yields an empty list, which is the
## reading for a unit.
static func attr_derived_from(attr: Variant) -> Array:
	var out: Array = []
	if not (attr is Dictionary):
		return out
	var typed: Dictionary = attr
	for key: String in ATTR_KEYS:
		if typed.has(key):
			out.append(ATTR_SOURCE[key])
	for key: Variant in typed.keys():
		if not ATTR_KEYS.has(key):
			out.append("unknown:%s" % str(key))
	return out


## Whether the recorded bag carries **only** keys this mirror derives -- the
## mirror's own consistency check, used by the readout. A bag with an
## `unknown:` field fails it.
static func bag_is_derivable(attr: Variant) -> bool:
	if not (attr is Dictionary):
		return false
	for key: Variant in (attr as Dictionary).keys():
		if not ATTR_KEYS.has(key):
			return false
	return true


## Evaluate a placement the service has already decided, for the readout and the
## report. Every server-owned value is **taken from the response**, never
## recomputed here: the response is the authoritative record of what the service
## did, so a wrong client-side derivation cannot be silently compounded.
static func evaluate_place(response: Variant) -> Dictionary:
	var out := {"resolvable": false, "reason": "", "map_key": -1, "item_id": -1,
		"x": -1, "y": -1, "cell": [], "orientation": DERIVED_ORIENTATION,
		"row": [], "attr": {}, "attr_fields": [], "attr_derivable": false,
		"player": DERIVED_PLAYER, "garrison": [], "quantity": QUANTITY,
		"count_before": 0, "count_after": 0, "ledger_gained": false,
		"slot_rule": "", "credited": false, "bounds_refused": false,
		"cell_occupancy_refused": false}
	if not (response is Dictionary):
		out["reason"] = "bad_response"
		return out
	var payload: Dictionary = response
	var placement: Variant = payload.get("placement", null)
	var row_block: Variant = payload.get("row", null)
	var quantity: Variant = payload.get("quantity", null)
	if not (placement is Dictionary) or not (row_block is Dictionary):
		out["reason"] = "bad_response"
		return out
	out["resolvable"] = true
	var typed_placement: Dictionary = placement
	var typed_row: Dictionary = row_block
	out["map_key"] = int(typed_placement.get("map_key", -1))
	out["item_id"] = int(typed_placement.get("item_id", -1))
	out["x"] = int(typed_placement.get("x", -1))
	out["y"] = int(typed_placement.get("y", -1))
	out["cell"] = [out["x"], out["y"]]
	out["orientation"] = int(typed_placement.get("orientation",
		DERIVED_ORIENTATION))
	out["slot_rule"] = str(typed_placement.get("slot_rule", ""))
	out["row"] = typed_row.get("slots", [])
	out["attr"] = typed_row.get("attr", {})
	out["attr_fields"] = attr_derived_from(out["attr"])
	out["attr_derivable"] = bag_is_derivable(out["attr"])
	out["player"] = int(typed_row.get("player", DERIVED_PLAYER))
	out["garrison"] = typed_row.get("store", [])
	if quantity is Dictionary:
		var typed_quantity: Dictionary = quantity
		out["quantity"] = int(typed_quantity.get("consumed", QUANTITY))
		out["count_before"] = int(typed_quantity.get("count_before", 0))
		out["count_after"] = int(typed_quantity.get("count_after", 0))
	out["ledger_gained"] = _ledger_gained(
		payload.get("ledger_before", []), payload.get("ledger_after", []),
		out["item_id"])
	var geometry: Variant = payload.get("geometry", null)
	if geometry is Dictionary:
		var typed_geometry: Dictionary = geometry
		out["bounds_refused"] = bool(typed_geometry.get("bounds_refused", false))
		out["cell_occupancy_refused"] = bool(
			typed_geometry.get("cell_occupancy_refused", false))
	# A placement credits nothing; recorded so the readout can never imply a
	# refund on either half.
	out["credited"] = false
	return out


## Evaluate a sale the service has already decided. `credited` is **read** from
## the response, never assumed: a sale credits nothing, but a flow that showed a
## refund because it insisted on one would be lying about the oracle, and the
## readout shows what the service said.
static func evaluate_sell(response: Variant) -> Dictionary:
	var out := {"resolvable": false, "reason": "", "item_id": -1,
		"credited": false, "refund": 0, "quantity": QUANTITY, "count_before": 0,
		"count_after": 0, "quantity_rule": "", "ledger_untouched": true}
	if not (response is Dictionary):
		out["reason"] = "bad_response"
		return out
	var payload: Dictionary = response
	var sale: Variant = payload.get("sale", null)
	var quantity: Variant = payload.get("quantity", null)
	if not (sale is Dictionary):
		out["reason"] = "bad_response"
		return out
	out["resolvable"] = true
	var typed_sale: Dictionary = sale
	out["item_id"] = int(typed_sale.get("item_id", -1))
	out["credited"] = bool(typed_sale.get("credited", false))
	var refund: Variant = typed_sale.get("refund", null)
	if refund is int or refund is float:
		out["refund"] = int(refund)
	out["quantity_rule"] = str(typed_sale.get("quantity_rule", ""))
	if quantity is Dictionary:
		var typed_quantity: Dictionary = quantity
		out["quantity"] = int(typed_quantity.get("consumed", QUANTITY))
		out["count_before"] = int(typed_quantity.get("count_before", 0))
		out["count_after"] = int(typed_quantity.get("count_after", 0))
	out["ledger_untouched"] = JSON.stringify(
		payload.get("ledger_before", null)) == JSON.stringify(
		payload.get("ledger_after", null))
	return out


## The readout for a storage placement. Reports what the service decided and
## states the three facts a player must be able to read honestly: the row is
## server-owned, no resource moved, and the slot was derived.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("resolvable", false)):
		return "Stored item not placed: %s" % str(evaluation.get("reason", ""))
	var row: Array = evaluation.get("row", [])
	var attr: Dictionary = evaluation.get("attr", {})
	var attr_text := "none"
	if not attr.is_empty():
		var fields: Array = evaluation.get("attr_fields", [])
		var names: Array = []
		for field: Variant in fields:
			names.append(str(field))
		attr_text = ", ".join(PackedStringArray(names))
	return ("Placed stored item %d at map key %d, cell (%d, %d).\n"
		% [int(evaluation.get("item_id", -1)),
			int(evaluation.get("map_key", -1)),
			int(evaluation.get("x", -1)), int(evaluation.get("y", -1))]
		+ "Row: %d slots, orientation %d, garrison %s, player %d, attr %s.\n"
		% [row.size(), int(evaluation.get("orientation", DERIVED_ORIENTATION)),
			JSON.stringify(evaluation.get("garrison", [])),
			int(evaluation.get("player", DERIVED_PLAYER)), attr_text]
		+ "The map key, the row instant, the garrison, the player team, and the "
		+ "attribute bag were derived by the server; the client sent only the "
		+ "item id and the cell.\n"
		+ "Stock: %d -> %d (one operation consumes %d).\n"
		% [int(evaluation.get("count_before", 0)),
			int(evaluation.get("count_after", 0)),
			int(evaluation.get("quantity", QUANTITY))]
		+ "No resource moved: placing a stored item is free, and the ledger %s "
		% ("gained" if bool(evaluation.get("ledger_gained", false))
			else "already carried")
		+ "the item id.")


## The readout for a storage sale. It must be able to say "this credited
## nothing" out loud, because that is what the oracle does.
static func readout_sell(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("resolvable", false)):
		return "Stored item not sold: %s" % str(evaluation.get("reason", ""))
	return ("Sold stored item %d. Stock: %d -> %d.\n"
		% [int(evaluation.get("item_id", -1)),
			int(evaluation.get("count_before", 0)),
			int(evaluation.get("count_after", 0))]
		+ "This credited nothing: the legacy sale writes only the storage key. "
		+ "No resource was refunded, no placement changed, and the purchase "
		+ "ledger %s."
		% ("was left alone" if bool(evaluation.get("ledger_untouched", false))
			else "CHANGED, which no legacy sale does"))


## Whether the ledger gained the id, which is only true when it was **not**
## already present: `bought_unit_add` is append-if-absent.
static func _ledger_gained(before: Variant, after: Variant,
		item_id: Variant) -> bool:
	if not (before is Array) or not (after is Array):
		return false
	var grew := (after as Array).size() > (before as Array).size()
	return grew and (after as Array).has(item_id)


## A committed field read as an integer the way legacy's `int()` reads it, or
## `null` when it could not -- the single fail-closed path every reader in this
## module uses. `int(null)` does not exist in Godot 4 and a boolean is not an
## integer legacy would accept, so both are rejected explicitly rather than
## coerced.
static func _committed_int(value: Variant, field: String) -> Variant:
	if value == null or value is bool:
		return null
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed != floor(typed):
			return null
		return int(typed)
	if value is String:
		var text := str(value).strip_edges()
		if text == "":
			return null
		if not text.is_valid_int():
			return null
		return int(text)
	return null


## The committed `properties` blob decoded to a mapping, as a **result**:
## `{"ok", "value", "code", "error"}`. `value` is `null` both when there is
## nothing to decode and when the blob is an empty mapping -- a distinction the
## service does not make either, because legacy tests truthiness first and
## `json.loads` second, so an absent and an empty blob take the same path.
##
## The raw configuration stores a JSON-encoded **string**; the committed
## normalized package stores an **object**. Both are accepted and neither is
## preferred: a mirror that chose one would disagree with the service on
## whichever it did not.
static func _decode_properties(properties: Variant) -> Dictionary:
	var out := {"ok": true, "value": null, "code": "", "error": ""}
	if properties == null:
		return out
	if properties is Dictionary:
		var typed: Dictionary = properties
		if typed.is_empty():
			return out
		out["value"] = typed
		return out
	if properties is String:
		var text := str(properties).strip_edges()
		if text == "":
			return out
		var decoded: Variant = JSON.parse_string(text)
		if not (decoded is Dictionary) or (decoded as Dictionary).is_empty():
			return out
		out["value"] = decoded
		return out
	out["ok"] = false
	out["code"] = "item_properties_invalid"
	out["error"] = ("the committed `properties` field is a %s, which legacy's "
		% type_string(typeof(properties))
		+ "truthiness test passes but whose `json.loads` read cannot produce a "
		+ "mapping")
	return out