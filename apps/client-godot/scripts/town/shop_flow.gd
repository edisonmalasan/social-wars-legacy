extends RefCounted
## Pure evaluation helpers for the purchase flow (building-purchase, spec
## "Purchase flow"): which catalog entries the shop may offer, what an
## entry's cash price reads against the player's cash, and whether the
## confirm may go out. No nodes, no I/O, no requests, no clock — the town
## view and its suite consume the same functions, exactly as
## `placement_flow.gd` serves the placement flow (design D5: the client owns
## the gameplay rules the legacy server never enforced; the endpoint keeps
## only structural validation).
##
## Why the cash-only gate here (design D2): the derived legacy command is
## `buy_stored_item_cash`, whose price is derivable only for an item whose
## config `costs` is exactly `{"c": <int>}`. An entry whose price is
## absent, empty, another resource, or a mix is therefore **not offered**,
## and `purchasable()` names it as such. That is a derivation boundary, not
## a gameplay rule: the flow never invents a price for an item the service
## could not price in cash.
##
## Not-purchasable reasons, evaluated in the documented order (spec: "An
## entry whose price exceeds the player's current cash SHALL be refused
## locally with an explicit reason and no request"):
##   no_selection      no shop entry is selected yet;
##   no_cash           the state carries no cash value — never guessed, so
##                     a confirm is refused rather than assumed payable;
##   not_cash_priced   the entry's price is not a cash price, so this
##                     command's price is not derivable (design D2);
##   unaffordable      the cash price exceeds the current cash (the refusal
##                     the client owns; the endpoint would clamp instead).

const PlacementCatalog = preload("res://scripts/town/placement_catalog.gd")

## The single resource a purchasable entry may be priced in.
const CASH_RESOURCE := "cash"
## Where cash lives on the typed town state.
const CASH_STATE_FIELD := "cash"


## The shop's entries for a loaded level: store-listed entries the level
## allows whose config price is a cash price, payload order preserved (spec:
## "store-listed entries gated by their `min_level` against the loaded level
## and whose config price is a cash price"). An absent or failed catalog
## yields no entries — never a fabricated one and never a guessed price.
##
## The type is deliberately NOT gated to buildings: storage holds buildings
## and units alike, and a unit the config prices in cash is purchasable
## through the same command. (At level 1 of the committed config every
## qualifying entry happens to be a building, so the two readings coincide
## there.)
static func shop_entries(catalog: Variant, level: int) -> Array:
	var entries: Array = []
	if not (catalog is PlacementCatalog.Catalog):
		return entries
	for entry: Variant in (catalog as PlacementCatalog.Catalog).entries:
		if not (entry is PlacementCatalog.Entry):
			continue
		var typed: PlacementCatalog.Entry = entry
		if typed.in_store and typed.min_level <= level \
				and is_cash_priced(typed):
			entries.append(typed)
	return entries


## True when the entry is priced in cash alone — the only price this
## command's envelope can carry (design D2). A free item, a multi-resource
## price, or a price in another resource is not.
static func is_cash_priced(entry: Variant) -> bool:
	if not (entry is PlacementCatalog.Entry):
		return false
	var costs: Variant = (entry as PlacementCatalog.Entry).costs
	if not (costs is Dictionary) or (costs as Dictionary).size() != 1:
		return false
	return (costs as Dictionary).has(CASH_RESOURCE)


## The entry's cash price as an integer, or null when it is not cash-priced
## (never a guess, never a zero default).
static func cash_price(entry: Variant) -> Variant:
	if not (entry is PlacementCatalog.Entry):
		return null
	if not is_cash_priced(entry):
		return null
	return int((entry as PlacementCatalog.Entry).costs[CASH_RESOURCE])


## "cash 5" — the price in the shop's own vocabulary (one resource, so no
## stable order is needed; "unpriced" names an entry the command cannot
## carry).
static func price_text(entry: Variant) -> String:
	var price: Variant = cash_price(entry)
	if price == null:
		return "unpriced"
	return "%s %d" % [CASH_RESOURCE, int(price)]


## The price beside the stored amount ("cash 5 (have 5)"), the display the
## spec requires against current cash. A state with no cash value reads
## "cash 5 (have ?)" — named, never guessed.
static func price_against_cash_text(state: Variant, entry: Variant) -> String:
	var price: Variant = cash_price(entry)
	if price == null:
		return "unpriced"
	return "%s %d (have %s)" % [CASH_RESOURCE, int(price),
		_cash_text(state)]


## Evaluate one confirm. Returns `{ok, error, purchasable, reason, price,
## cash, name}`: `reason` is "" while purchasable, otherwise the first
## failing gate in the documented order. Structural failures (no state, no
## selected entry) return `{ok: false}` with no evaluation, so the caller
## refuses locally without a request.
static func evaluate(state: Variant, entry: Variant) -> Dictionary:
	if state == null:
		return _reject("the town state is unavailable")
	if not (entry is PlacementCatalog.Entry):
		return _reject("no shop entry is selected")
	var typed: PlacementCatalog.Entry = entry
	var evaluation := {"ok": true, "error": "", "purchasable": true,
		"reason": "", "price": 0, "cash": _cash_or(state, -1),
		"name": typed.name}
	var price: Variant = cash_price(typed)
	if price == null:
		evaluation["purchasable"] = false
		evaluation["reason"] = "not_cash_priced"
		return evaluation
	evaluation["price"] = int(price)
	var cash := _cash_or(state, -1)
	if cash < 0:
		evaluation["purchasable"] = false
		evaluation["reason"] = "no_cash"
		return evaluation
	if int(price) > cash:
		evaluation["purchasable"] = false
		evaluation["reason"] = "unaffordable"
	return evaluation


## The explicit refusal text for an unaffordable (or otherwise unbuyable)
## price: the reason plus the two numbers it compares, so the player never
## sees a bare rejection. Returns "" while the entry is purchasable.
static func refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if bool(evaluation.get("purchasable", false)):
		return ""
	var label := str(evaluation.get("name", "the selected item"))
	match str(evaluation.get("reason", "")):
		"not_cash_priced":
			return "not purchasable: %s has no cash price this shop can pay" \
				% label
		"no_cash":
			return "not purchasable: the current cash value is unknown"
		"unaffordable":
			return "not purchasable: cash %d costs more than the %d you have" % [
				int(evaluation.get("price", 0)),
				int(evaluation.get("cash", 0))]
	return "not purchasable"


## True when every unit of the price fits inside the stored cash. A missing
## cash value is never affordable: the flow never guesses.
static func affordable(state: Variant, entry: Variant) -> bool:
	var evaluation := evaluate(state, entry)
	return bool(evaluation.get("ok", false)) \
		and bool(evaluation.get("purchasable", false))


## The stored cash amount, or -1 when the state carries no cash value (a
## missing field is named, never defaulted to 0 — defaulting would let an
## unaffordable purchase through).
static func _cash_or(state: Variant, fallback: int) -> int:
	if state == null:
		return fallback
	var resources: Variant = state.resources
	if resources == null:
		return fallback
	if resources is Dictionary:
		# A plain state bag (the helper suite's minimal fixture).
		return int((resources as Dictionary).get(CASH_STATE_FIELD, fallback))
	# The typed `TownState.Resources` bag: the cash field is a script
	# variable, and a field the parse recorded as missing must read as
	# unknown rather than as a stored zero.
	if not CASH_STATE_FIELD in _field_names(resources):
		return fallback
	return int(resources.get(CASH_STATE_FIELD))


## The script-variable names of a typed state bag (the HUD's `_field_names`
## precedent), so a recorded-missing field is read as unknown.
static func _field_names(bag: Variant) -> Array:
	var names: Array = []
	for property in bag.get_property_list():
		if int(property["usage"]) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			names.append(str(property["name"]))
	return names


## The cash amount as display text ("?" when unknown).
static func _cash_text(state: Variant) -> String:
	var cash := _cash_or(state, -1)
	return "?" if cash < 0 else str(cash)


## The house rejection envelope: names the condition, never evaluates.
static func _reject(message: String) -> Dictionary:
	return {"ok": false, "error": "[shop] confirm rejected: " + message,
		"purchasable": false, "reason": "", "price": 0, "cash": -1,
		"name": ""}
