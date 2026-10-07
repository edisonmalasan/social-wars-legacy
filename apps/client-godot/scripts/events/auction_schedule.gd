extends RefCounted
## Committed auction-schedule projection for OpenSpec `godot-auction-schedule`.
##
## ## What this module reads, and the one path it reads it through
##
## The three committed auctions are read through the EXISTING normalized content
## registry, under the `auctions` domain. They are NOT read from the committed
## standalone config document: no line of this module names that path, and
## `test_auction_schedule.gd` proves it by substring scan over both delivered
## modules rather than trusting this sentence.
##
## The registry is **passed in** rather than reached for, exactly as
## `premium_purchase.gd` does, so this module performs no I/O and the suite owns
## the lifetime of the index. `legacy_ids()` is used rather than `get_entry()` so
## the enumeration is the registry's own committed order and not a collation.
##
## ## The committed table is a DOCUMENT this surface never read
##
## The normalized package carries three definitions because the committed config
## carries three entries. That is not a claim that the preserved server read
## them: the module that would have consumed this table cannot construct itself
## (`auction_oracle.gd` records the defect with both line numbers), and its only
## call path is commented out. The table is normalized so committed content
## becomes visible to a modern client, and the price columns are carried verbatim
## for exactly that reason: they are committed facts, and a reader who cannot see
## them has to guess.
##
## ## TWO encodings are load-bearing and both are preserved verbatim
##
## `legacy_id` stays the committed JSON **string** (`"1"`, `"2"`, `"3"`), because
## the legacy module keys its state document by `str(auction["uuid"])`
## (`auctions.py:75`) and an integer here would claim a type the source does not
## carry.
##
## `interval` stays in **minutes**. The conversion to seconds is the one derived
## value on this surface and it lives in exactly one function with a named
## inverse, so the unit of the committed field is stated in one place. This
## mirrors `COLLECT_MINUTES` in `godot-building-collect`, where the ladder is
## committed in minutes and both row instants are Unix seconds.
##
## ## Why there is no sentinel value anywhere below
##
## Every refusal below returns `{"ok": false, "error": "<named reason>"}` and
## carries **no** derived field at all. An earlier convention in this project
## reserved `-1` for "not derived" (see `premium_purchase.MALFORMED`), which is
## only safe because `0` is not a legitimate return there. Nothing about a
## duration needs that machinery: the refused result simply omits the value, so a
## malformed entry cannot be mistaken for a zero-length auction and there is no
## second code path a caller has to remember.
##
## ## Why the module contains exactly one multiplication and one division
##
## The suite asserts, over a code-only view with comments and string literals
## stripped, that the ONLY functions in this file containing `*`, `/` or `%` are
## the two named conversion functions -- and that each carries exactly one
## operator of its own kind. That is a mechanical statement, not an intention.
##
## ## The additive case is NOT covered by that scanner, and this records why
##
## `+` is GDScript's string-concatenation operator and `-` appears in every
## `->` return-type annotation, so neither can be counted in a scanner of this
## shape. An additive or subtractive derivation -- a total, a fee, a remaining
## time -- is therefore caught by the **declared-function inventory pin** and the
## **reserved-name guard** rather than by the operator census. Both are proven by
## injection; the operator census is not claimed to be the whole guard.
##
## ## No action of any kind is exposed
##
## There is no way from this module to place, bid on, start, extend, cancel or
## settle an auction, because the surface has no request path to expose one
## through (`auction_oracle.gd`). No countdown, scheduler, timer or clock read
## appears anywhere in the delivered files, and no state document is created,
## defaulted or repaired.

## The normalized content domain carrying the three committed definitions.
const CONTENT_DOMAIN := "auctions"

## The unit the committed `interval` is expressed in, recorded beside the factor
## so the conversion is self-describing at both ends.
const INTERVAL_UNIT := "minutes"
const DURATION_UNIT := "seconds"

## The ONE conversion factor on this surface. It is recorded here, used in the
## two named conversion functions below, and never written inline at a call site.
const SECONDS_PER_MINUTE := 60

## The committed fields this projection carries, in the order the requirement
## lists them. `interval` is carried in its committed unit; the derived duration
## is reported in the same record under its own key and is never substituted for
## it.
const PROJECTED_FIELDS := [
	"legacy_id", "level", "interval", "price", "priceIncrement", "betPrice",
	"unit", "unit_name",
]

## The two encodings preserved verbatim (design D2), recorded so a later reader
## can see that each was a decision rather than an accident.
const ENCODING_RECORDS := {
	"legacy_id": {
		"json_type": "String",
		"committed_values": ["1", "2", "3"],
		"why": "auctions.py:75 keys its state document by str(auction[\"uuid\"]), "
			+ "so an integer here would claim a type the source does not carry",
		"coerced": false,
	},
	"interval": {
		"json_type": "Number",
		"committed_unit": INTERVAL_UNIT,
		"derived_unit": DURATION_UNIT,
		"why": "auctions.py:76 converts once, and the committed table is "
			+ "normalized in its own unit so the conversion stays visible in "
			+ "code rather than hidden inside a data file",
		"coerced": false,
	},
}

## The closed refusal vocabulary. Every code is a shape the committed schedule
## never has, so a refusal can never be a verdict about a real auction.
const REFUSAL_REGISTRY_ABSENT := "registry_absent"
const REFUSAL_REGISTRY_SHAPE := "registry_has_no_legacy_ids"
const REFUSAL_DOMAIN_ABSENT := "no_committed_auctions_domain"
const REFUSAL_SCHEDULE_TYPE := "schedule_not_array"
const REFUSAL_ENTRY_TYPE := "schedule_entry_not_object"
const REFUSAL_LEGACY_ID_TYPE := "legacy_id_not_string"
const REFUSAL_LEVEL_TYPE := "level_not_integer"
const REFUSAL_INTERVAL_TYPE := "interval_not_integer"
const REFUSAL_INTERVAL_NOT_POSITIVE := "interval_not_positive"
const REFUSAL_PRICE_TYPE := "price_not_integer"
const REFUSAL_INCREMENT_TYPE := "price_increment_not_integer"
const REFUSAL_BET_PRICE_TYPE := "bet_price_not_integer"
const REFUSAL_UNIT_TYPE := "unit_not_integer"
const REFUSAL_UNIT_NAME_ABSENT := "unit_name_absent"
const REFUSAL_UNIT_NAME_TYPE := "unit_name_not_string"

## Every entry refusal, in the order the checks resolve. The order matters: a
## caller reading the list learns which shape is decided first.
const ENTRY_REFUSALS := [
	REFUSAL_ENTRY_TYPE,
	REFUSAL_LEGACY_ID_TYPE,
	REFUSAL_LEVEL_TYPE,
	REFUSAL_INTERVAL_TYPE,
	REFUSAL_INTERVAL_NOT_POSITIVE,
	REFUSAL_PRICE_TYPE,
	REFUSAL_INCREMENT_TYPE,
	REFUSAL_BET_PRICE_TYPE,
	REFUSAL_UNIT_TYPE,
	REFUSAL_UNIT_NAME_ABSENT,
	REFUSAL_UNIT_NAME_TYPE,
]

## Every refusal `committed_schedule` can produce, in resolution order.
const SCHEDULE_REFUSALS := [
	REFUSAL_REGISTRY_ABSENT,
	REFUSAL_REGISTRY_SHAPE,
	REFUSAL_DOMAIN_ABSENT,
	REFUSAL_SCHEDULE_TYPE,
]

## The two schedule-level codes that are NOT malformed content: a registry that
## is not a registry, and a domain the package does not carry.
const READ_PATH_REFUSALS := [
	REFUSAL_REGISTRY_ABSENT,
	REFUSAL_REGISTRY_SHAPE,
	REFUSAL_DOMAIN_ABSENT,
]

## The one non-positive-interval refusal, recorded with its own justification
## because it is the only refusal here that the preserved branch would NOT have
## raised. `auctions.py:76` computes `auction["interval"] * 60` with no check, so
## a non-positive committed interval would produce a non-positive or zero duration
## in the original. Refusing it here is a **content-shape** refusal: this module
## projects committed content and refuses to derive a duration from a field whose
## own unit makes the result meaningless. It is NOT a parity claim, and no
## gameplay rule is being reproduced.
const INTERVAL_REFINEMENT_RECORDS := {
	REFUSAL_INTERVAL_NOT_POSITIVE: {
		"kind": "content_shape",
		"parity": false,
		"legacy_would_have": "computed auction[\"interval\"] * 60 unchanged",
		"why": "a zero or negative interval yields a zero or negative duration, "
			+ "which is not a length of time; refusing it keeps the one "
			+ "derivation meaningful rather than reproducing a nonsense value",
	},
}

## Mechanisms this capability does NOT deliver, each with its measured reason.
## This is the contract, not an inventory of omissions.
const ABSENT_HELPERS := [
	{"helper": "auction_price", "absent_because":
		"auctions.py:199 makes currentPrice a pure function of the client-sent "
		+ "bid, with zero comparison operators against bet_amount, currentPrice, "
		+ "beginPrice or betPrice; a price here would be a second, invented path"},
	{"helper": "bid_fee", "absent_because":
		"the committed betPrice has no consumer anywhere in the preserved "
		+ "source, so there is no rule to apply it by"},
	{"helper": "bid_total", "absent_because":
		"no total exists to compute: the module writes one price field and no "
		+ "arithmetic is applied to it"},
	{"helper": "seconds_remaining", "absent_because":
		"nothing evaluates elapsed time, so a remaining duration would need a "
		+ "clock read and a comparison the oracle does not have"},
	{"helper": "is_ready", "absent_because":
		"there is no request path, so no player is ever waiting on readiness"},
	{"helper": "next_expiry", "absent_because":
		"the expiry offsets are recorded in auction_oracle.gd and reported; "
		+ "computing an expiry instant is the delivered timer this capability "
		+ "refuses"},
	{"helper": "auction_round", "absent_because":
		"auctions.py:138 writes the literal 1 and never reads it; there is no "
		+ "counter to read"},
	{"helper": "expired_round_count", "absent_because":
		"auctions.py:127 computes count_expired and discards it; only remaining "
		+ "reaches beginDate"},
	{"helper": "winner_for", "absent_because":
		"bid amounts are never compared and betWinner appears only under a "
		+ "client-sent flag, so no amount determines a winner"},
	{"helper": "bidder_ranking", "absent_because":
		"the winning check reads the LAST list element and answers relative to "
		+ "the user asked about, which is not an ordering"},
	{"helper": "place_bid", "absent_because":
		"all three routes are commented out, so there is nothing to call"},
	{"helper": "start_auction", "absent_because":
		"creation happens inside a constructor that raises; no client triggers it"},
	{"helper": "extend_auction", "absent_because":
		"the only extension is the recorded 60-second grace, which nothing settles"},
	{"helper": "cancel_auction", "absent_because":
		"no branch in the module removes a live auction; expiry replaces one"},
	{"helper": "settle_auction", "absent_because":
		"no settlement code exists and betUsers gates a window that never closes"},
	{"helper": "create_state_document", "absent_because":
		"the module cannot bootstrap, so a client that created the document "
		+ "would be implementing something the original never did"},
	{"helper": "default_state_document", "absent_because":
		"same reason, in the weaker form: an empty default would be a repair path"},
	{"helper": "repair_state_document", "absent_because":
		"the defect is recorded in auction_oracle.gd and deliberately not fixed"},
	{"helper": "tick", "absent_because":
		"no scheduler, timer or countdown is delivered"},
	{"helper": "now_seconds", "absent_because":
		"no clock read is delivered; every instant on this surface is committed "
		+ "content or a recorded offset"},
]

## No route and no action (design D5). Declared empty so the suite can assert the
## closed set rather than whatever the code happens to branch on.
const DELIVERED_ROUTES := []
const DELIVERED_ACTIONS := []
const DELIVERED_FLOWS := []

## The registry is passed in, so a caller can never be handed content this module
## did not ask the registry for.
static func committed_schedule(registry: Variant) -> Dictionary:
	if registry == null:
		return _refuse(REFUSAL_REGISTRY_ABSENT)
	if not (registry is Object) or not registry.has_method("legacy_ids"):
		return _refuse(REFUSAL_REGISTRY_SHAPE)
	var fetched: Variant = registry.legacy_ids(CONTENT_DOMAIN)
	if not (fetched is Dictionary):
		return _refuse(REFUSAL_REGISTRY_SHAPE)
	var lookup: Dictionary = fetched
	if not bool(lookup.get("found", false)):
		return _refuse(REFUSAL_DOMAIN_ABSENT)
	var ids: Variant = lookup.get("ids", null)
	if not (ids is Array):
		return _refuse(REFUSAL_DOMAIN_ABSENT)
	var entries: Array = []
	var ids_arr: Array = ids
	for legacy_id: Variant in ids_arr:
		var id_key: String = str(legacy_id)
		if not registry.has_method("get_entry"):
			return _refuse(REFUSAL_REGISTRY_SHAPE)
		var got: Variant = registry.get_entry(CONTENT_DOMAIN, id_key)
		if not (got is Dictionary):
			return _refuse(REFUSAL_SCHEDULE_TYPE)
		var row: Dictionary = got
		if not bool(row.get("found", false)):
			return _refuse(REFUSAL_SCHEDULE_TYPE)
		var stored: Variant = row.get("entry", null)
		if not (stored is Dictionary):
			return _refuse(REFUSAL_ENTRY_TYPE)
		entries.append((stored as Dictionary).duplicate(true))
	return {"ok": true, "schedule": entries, "error": "",
		"count": entries.size()}


## Project every committed entry, in the registry's own committed order.
##
## Each entry reports the committed fields verbatim plus the ONE derived value.
## A refused entry contributes a record carrying its named reason and **no**
## duration, and it does NOT stop the projection: three of three entries are
## reported either way, and the count of refused entries is reported alongside so
## a caller cannot mistake a short successful list for a complete one.
static func project(schedule: Variant) -> Dictionary:
	if not (schedule is Array):
		return _refuse(REFUSAL_SCHEDULE_TYPE)
	var rows: Array = schedule
	var entries: Array = []
	var refused := 0
	for raw: Variant in rows:
		var record: Dictionary = project_entry(raw)
		if not bool(record["ok"]):
			refused += 1
		entries.append(record)
	return {
		"ok": refused == 0,
		"error": "" if refused == 0 else "one_or_more_entries_refused",
		"entries": entries,
		"count": entries.size(),
		"refused": refused,
		"content_domain": CONTENT_DOMAIN,
		"order": "the registry's committed order, not a collation",
	}


## Project ONE committed entry.
##
## Every committed field is carried unaltered. The derived duration is added
## under its own key and never overwrites `interval`, so a reader cannot lose
## sight of the unit the committed field is actually in.
static func project_entry(raw: Variant) -> Dictionary:
	var reason: String = entry_refusal(raw)
	if reason != "":
		return {
			"ok": false,
			"error": reason,
			"duration_seconds": null,
			"duration_unit": DURATION_UNIT,
			"interval_unit": INTERVAL_UNIT,
		}
	var entry: Dictionary = raw
	var interval_minutes: int = int(entry["interval"])
	var record := {
		"ok": true,
		"error": "",
		"legacy_id": str(entry["legacy_id"]),
		"level": int(entry["level"]),
		"interval": interval_minutes,
		"interval_unit": INTERVAL_UNIT,
		"duration_seconds": duration_seconds_from_interval(interval_minutes),
		"duration_unit": DURATION_UNIT,
		"price": int(entry["price"]),
		"priceIncrement": int(entry["priceIncrement"]),
		"betPrice": int(entry["betPrice"]),
		"unit": int(entry["unit"]),
		"unit_name": str(entry["unit_name"]),
		"price_derived_here": false,
		"bet_price_charged": false,
	}
	return record


## The named reason this entry cannot be projected, or `""` when it can.
##
## `interval` is checked for being a positive integer before any conversion is
## attempted, so a malformed entry never reaches the derivation.
static func entry_refusal(raw: Variant) -> String:
	if not (raw is Dictionary):
		return REFUSAL_ENTRY_TYPE
	var entry: Dictionary = raw
	if not entry.has("legacy_id") or not (entry["legacy_id"] is String):
		return REFUSAL_LEGACY_ID_TYPE
	for field: String in ["level", "interval", "price", "priceIncrement",
			"betPrice", "unit"]:
		if not entry.has(field) or not _is_integral(entry[field]):
			return _numeric_refusal(field)
	if int(entry["interval"]) <= 0:
		return REFUSAL_INTERVAL_NOT_POSITIVE
	if not entry.has("unit_name"):
		return REFUSAL_UNIT_NAME_ABSENT
	if not (entry["unit_name"] is String):
		return REFUSAL_UNIT_NAME_TYPE
	return ""


## The named refusal for one committed numeric field, so the field name appears
## once in the code rather than six times.
static func _numeric_refusal(field: String) -> String:
	match field:
		"level":
			return REFUSAL_LEVEL_TYPE
		"interval":
			return REFUSAL_INTERVAL_TYPE
		"price":
			return REFUSAL_PRICE_TYPE
		"priceIncrement":
			return REFUSAL_INCREMENT_TYPE
		"betPrice":
			return REFUSAL_BET_PRICE_TYPE
		"unit":
			return REFUSAL_UNIT_TYPE
	return REFUSAL_ENTRY_TYPE


## THE conversion. The committed interval, in minutes, to a duration in seconds.
##
## This is the only function in the delivered files permitted to multiply, and it
## multiplies by the one named factor. No client value reaches it and no
## committed value other than the interval is read.
static func duration_seconds_from_interval(interval_minutes: int) -> int:
	return interval_minutes * SECONDS_PER_MINUTE


## The NAMED INVERSE of `duration_seconds_from_interval`.
##
## Integer division in GDScript is exact for a duration this conversion produced,
## which is what makes the round trip over every committed entry assertable
## rather than approximate.
static func interval_minutes_from_duration(duration_seconds: int) -> int:
	return duration_seconds / SECONDS_PER_MINUTE


## True when a round trip through both conversion functions is exact for this
## committed interval. Reported rather than assumed, so a caller can see which
## entries would not survive the inverse.
static func round_trips(interval_minutes: Variant) -> bool:
	if not _is_integral(interval_minutes):
		return false
	var minutes: int = int(interval_minutes)
	return interval_minutes_from_duration(
		duration_seconds_from_interval(minutes)) == minutes


## The closed refusal vocabulary, sorted, so a caller can diff it.
static func refusal_codes() -> Array:
	var out: Array = []
	for code: String in ENTRY_REFUSALS:
		out.append(code)
	for code: String in SCHEDULE_REFUSALS:
		if not out.has(code):
			out.append(code)
	out.sort()
	return out


## One refusal's recorded reason, or `""` for an unrecorded code.
static func refusal_reason(code: String) -> String:
	if (INTERVAL_REFINEMENT_RECORDS as Dictionary).has(code):
		var entry: Dictionary = INTERVAL_REFINEMENT_RECORDS[code]
		return str(entry["why"])
	return ""


## A refusal result carrying no derived field, so it cannot be read as a value.
static func _refuse(code: String) -> Dictionary:
	return {"ok": false, "error": code, "schedule": null, "count": 0}


## True for an integral int or an integral float.
##
## The float case exists ONLY because the content registry decodes every JSON
## number as a float. It is deliberately narrow: a string, a bool, a null and a
## fractional number all fail, so a malformed committed field cannot be coerced
## into a duration.
static func _is_integral(value: Variant) -> bool:
	var kind: int = typeof(value)
	if kind != TYPE_INT and kind != TYPE_FLOAT:
		return false
	var as_float: float = float(value)
	return is_equal_approx(as_float, float(int(as_float)))