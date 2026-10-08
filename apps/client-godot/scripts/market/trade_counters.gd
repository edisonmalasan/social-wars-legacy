extends RefCounted
## Trade-counter projection for OpenSpec `godot-market-trade-counters`.
##
## ## What this surface is, and what it is not
##
## It is a read-only projection of TWO committed state fields and of the branch's
## own arithmetic over them. It exposes no action, mutates nothing, and issues no
## request. There is deliberately no way from this module to trade, to clear the
## counter, to move the instant, or to ask the server for either value.
##
## ## The finding that shapes every number below: the cap is STORED, never ENFORCED
##
## The legacy branch at `command.py:465-473` stores the count and prints a
## "remaining trades" figure. `numTradesDone` then has exactly ONE reader across
## all eleven legacy root modules -- and that reader is the increment that
## produces the value at `command.py:469`. Nothing anywhere reads the stored
## count to gate, refuse, limit or rank anything. So the cap is a value the
## server writes, not a limit a player ever met. `cap_record()` states this with
## the measurement, and nothing in this module may present it as a limit.
##
## ## The second field is the opposite shape, and that asymmetry IS the deliverable
##
## The last-trade instant has exactly TWO writers and exactly ONE reader, and
## that reader is a live one: the day-bucket comparison in the engine's reset
## helper at `engine.py:238-240`. So one counter is inert and the other runs on
## every player-info load.
##
## ## The reset predicate is REPORTED, never PERFORMED, and never REIMPLEMENTED
##
## `engine.reset_stuff` already runs on the load path -- it is called from
## `get_player_info.py:9` on every player-info request. Duplicating the day
## boundary here would create a second source of truth for a reset the engine
## already owns, so this module evaluates the predicate and reports both day
## buckets, and writes the count to nothing. `RESET_OWNER` names the owner.
##
## ## The unclamped print is a REPORTED FIELD, and it may never be corrected
##
## `command.py:470` stores `min(20, num_trades)` while `command.py:473` prints
## `20 - num_trades` from the UNCLAMPED local. From the twenty-first trade onward
## the stored value stays at the cap and the printed figure goes NEGATIVE.
## `branch_remaining_after_next_trade()` reproduces the unclamped arithmetic in
## exactly one expression, and it contains no comparison, no `min`, no `max`, no
## floor and no clamp -- because a future implementer who "helpfully" bounded it
## would have silently changed the oracle's behaviour and called it a fix. The
## suite asserts the absence mechanically, over the code-only text of that one
## function.
##
## ## TWO client-dictated behaviours are RECORDED as divergences, never reproduced
##
## 1. Resource movement. `trade_resource` reads both of its arguments and uses
##    neither (`resource_type` at `command.py:466`, `sold` at `command.py:467`),
##    so the branch moves NO resource itself. Any movement would have arrived
##    client-sent through `engine.apply_resources` (`engine.py:251-271`), applied
##    at `command.py:40` -- BEFORE the dispatcher chain opens at `command.py:42`.
##    That is the client dictating the outcome, so the delivered client sends no
##    resource vector and moves no resource, and the divergence is recorded.
## 2. A client-writable instant. `fast_forward` (`command.py:905-947`) writes
##    `command.py:913` as
##    `map["timestampLastTrade"] = max(0, map["timestampLastTrade"] - seconds)`
##    with `seconds = args[0]` -- a CLIENT-SUPPLIED integer at `command.py:906`.
##    A client can therefore walk the instant backward across a `// 86400`
##    boundary and clear the count. That is a real, reachable state change and it
##    is a DIVERGENCE, not parity. No fast-forward operation is delivered here.
##
## ## What makes the recorded corpus evidence a proof rather than an inference
##
## `command.py:471` is the only site that can RAISE the instant from zero:
## `:913` subtracts a client-supplied quantity and floors the result at zero, so
## from a zero instant it can only ever produce zero again. A non-zero recorded
## instant therefore implies a trade ran, the count reached at least one, and the
## only writer that can then set the count back to zero is `engine.py:240`.
## That premise is derived from the writer set, not read off one row.
##
## ## No ordinal is claimed for the committed zero-consumer census
##
## Four conflicting ordinals already exist in this project's delivered records,
## each counted over a different scope, so this module names no ordinal position
## for the market-schedule zero-consumer count. The suite enforces the absence
## over the code-only text of both delivered modules, and separately asserts that
## this rationale is still present so the guard cannot be simplified back into a
## weaker scan of comments.

## The normalized content domain carrying the committed tuning constants. The
## committed schedule rows are read through the EXISTING registry under this
## domain by `market_schedule.gd`; this module reads no content at all.
const CONTENT_DOMAIN := "globals"

## The cap the legacy branch STORES, read from the branch's own hardcoded literal
## at `command.py:470` -- `min(20, num_trades)`.
##
## It is deliberately NOT derived from the committed content row that happens to
## carry the same number. That row has zero legacy consumers, so deriving from
## it would make an unread constant load-bearing, which is precisely the
## invention this milestone's precedents forbid. The equality is a coincidence
## and is recorded as one, in the evidence report, where the committed row is
## read from the registry rather than transcribed here.
const TRADE_CAP_FROM_BRANCH := 20

## The legacy site the cap is read from, and the branch whose literal it is.
const CAP_SOURCE := {
	"value": TRADE_CAP_FROM_BRANCH,
	"legacy_site": "command.py:470",
	"expression": "map[\"numTradesDone\"] = min(20, num_trades)",
	"read_from": "the branch literal, not any committed content value",
	"derived_from_content": false,
}

## The day-bucket length the engine's reset predicate divides by, taken from the
## reset helper's own literal at `engine.py:239` (`now // 86400`) and stated in
## its comment at `engine.py:234`. Named here so the unit is stated once.
const DAY_BUCKET_SECONDS := 86400

## The reset is the ENGINE's and runs on the load path. It is referenced, never
## reimplemented, exactly as a delivered line references a consumer it does not
## own rather than duplicating it.
const RESET_OWNER := {
	"helper": "engine.reset_stuff",
	"legacy_site": "engine.py:230-240",
	"read_site": "engine.py:238",
	"predicate_site": "engine.py:239",
	"write_site": "engine.py:240",
	"called_from": "get_player_info.py:9, on every player-info request",
	"reimplemented_here": false,
	"why": "the helper already runs on the load path, so a second copy of the "
		+ "day boundary here would be a second source of truth for one reset",
}

## The stored-never-enforced record, with the measurement that carries it. The
## `only_reader` entry is the whole argument: the count's one reader IS the
## increment that writes it, so the stored value never reaches a decision.
const CAP_ENFORCEMENT := {
	"stored": true,
	"enforced": false,
	"branches_gating_on_the_count": 0,
	"only_reader": "command.py:469",
	"only_reader_is_its_own_increment": true,
	"why": "the increment reads the count to produce the count, so nothing "
		+ "anywhere reads the stored value to refuse, gate, limit or rank "
		+ "anything; a client could record trades past the cap and the server "
		+ "would keep storing the cap",
	"offered_as_a_limit_anywhere_here": false,
}

## The two state fields this projection owns, and where each one is stored.
##
## Both live on the map row. Neither appears on the private state in ANY of the
## eleven legacy root modules: the three counted sites and the three counted
## sites of the instant are every one a `map[...]` subscript. `project()` still
## accepts the private state and measures that at run time, so the claim is a
## measurement on the record a caller receives rather than prose.
const STATE_LOCATIONS := {
	"map_row_fields": ["numTradesDone", "timestampLastTrade"],
	"private_state_fields": [],
	"measured_at_run_time": true,
	"note": "the private-state argument is accepted so this record can be "
		+ "measured, and it contributes no field to any projected value",
}

## The two divergences, recorded as data with their line references. Neither is
## reproduced as behaviour anywhere in this module.
const DIVERGENCES := [
	{
		"id": "client_sent_resource_movement",
		"reproduced": false,
		"what_the_branch_does": "reads resource_type at command.py:466 and sold "
			+ "at command.py:467 and uses neither, so it moves NO resource",
		"how_movement_would_arrive": "client-sent through engine.apply_resources "
			+ "(engine.py:251-271), applied at command.py:40, before the "
			+ "dispatcher chain opens at command.py:42",
		"delivered_behaviour": "no resource is moved and no resource vector is "
			+ "sent by any delivered client code",
		"class": "client dictates the outcome",
	},
	{
		"id": "client_writable_instant",
		"reproduced": false,
		"what_the_branch_does": "fast_forward writes command.py:913 as "
			+ "map[\"timestampLastTrade\"] = max(0, map[\"timestampLastTrade\"] "
			+ "- seconds) with seconds = args[0], a client-supplied integer "
			+ "assigned at command.py:906",
		"consequence": "a client can walk the instant backward across a "
			+ "// 86400 boundary and clear the count",
		"delivered_behaviour": "no operation writes, decrements or offsets the "
			+ "instant anywhere in the delivered client",
		"class": "client dictates the outcome",
	},
]

## The recorded oracle: the branch's own effects, transcribed from the preserved
## source and re-measured by the suite on every run.
const BRANCH_INVENTORY := {
	"branch": "trade_resource",
	"site": "command.py:465-473",
	"reads_its_arguments": false,
	"arguments": [
		{"name": "resource_type", "site": "command.py:466", "used": false},
		{"name": "sold", "site": "command.py:467", "used": false,
			"comment": "1 if sold, 2 if bought"},
	],
	"effects": [
		{"site": "command.py:469", "effect": "read the count into the "
			+ "increment", "is_the_only_reader": true},
		{"site": "command.py:470", "effect": "store min(20, increment)",
			"is_a_write": true},
		{"site": "command.py:471", "effect": "assign the server clock to the "
			+ "instant", "is_a_write": true, "only_raising_writer": true},
		{"site": "command.py:473", "effect": "print 20 - increment from the "
			+ "UNCLAMPED local", "clamped": false},
	],
	"server_clock_source": "time_now = timestamp_now() at command.py:36",
	"resources_moved": 0,
	"branch_is_the_only_raising_writer_of_the_instant": true,
}

## Where each counter is written and read, as the measured writer/reader sets.
## The suite re-derives these from the preserved source on every run and requires
## this record to agree, so a legacy edit fails the suite rather than silently
## contradicting the report.
const COUNTER_SITES := {
	"numTradesDone": {
		"writers": ["command.py:470", "engine.py:240"],
		"readers": ["command.py:469"],
		"live_consumers": 0,
	},
	"timestampLastTrade": {
		"writers": ["command.py:471", "command.py:913"],
		"readers": ["engine.py:238"],
		"live_consumers": 1,
	},
}

## Mechanisms this capability does NOT deliver, each with its measured reason.
## This is the contract, not an inventory of omissions.
const ABSENT_HELPERS := [
	{"helper": "trade_cost", "absent_because":
		"the legacy branch reads both of its arguments and uses neither and "
		+ "moves no resource, so there is no amount and nothing to price"},
	{"helper": "cap_for", "absent_because":
		"the cap is a branch literal, not a rule: a helper returning it would "
		+ "look like a limit the preserved server never applied"},
	{"helper": "enforce_trade_limit", "absent_because":
		"the count's only reader is its own increment, so no branch gates on "
		+ "it and there is nothing to enforce"},
	{"helper": "is_trade_allowed", "absent_because":
		"no legacy branch refuses a trade, so a predicate returning a verdict "
		+ "would invent one"},
	{"helper": "remaining_trades_clamped", "absent_because":
		"command.py:473 prints the unclamped local and the stored value stays "
		+ "at the cap; bounding the reported figure would correct the oracle "
		+ "rather than reproduce it"},
	{"helper": "next_trade_state", "absent_because":
		"no request path exists, so no trade is ever recorded by this client"},
	{"helper": "trade", "absent_because":
		"the branch grants nothing and refuses nothing; offering the action "
		+ "would be an affordance for a transaction with no outcome"},
	{"helper": "sell_ratio", "absent_because":
		"the committed schedule is unread everywhere, so a ratio computed from "
		+ "it would be an invented economy"},
	{"helper": "reset_count_now", "absent_because":
		"the day-bucket reset belongs to the engine and already runs on the "
		+ "load path; a second copy would be a second source of truth"},
	{"helper": "advance_instant", "absent_because":
		"fast_forward makes the instant client-writable, so any offset this "
		+ "module could offer would reproduce that divergence"},
	{"helper": "apply_vector", "absent_because":
		"resource movement would arrive client-sent before the dispatcher "
		+ "opens, which is the pattern this capability refuses"},
	{"helper": "seconds_remaining_in_day", "absent_because":
		"the reset predicate is reported from both day buckets and a countdown "
		+ "is the affordance this line declines to build"},
	{"helper": "is_at_cap", "absent_because":
		"nothing reads the count, so a predicate would suggest an enforcement "
		+ "point that does not exist"},
	{"helper": "market_schedule_value", "absent_because":
		"the committed schedule is read through the registry by the second "
		+ "delivered module and never transcribed here"},
]

## No route and no action (design D1). Declared empty so the suite can assert
## the closed set rather than whatever the code happens to branch on.
const DELIVERED_ROUTES := []
const DELIVERED_ACTIONS := []
const DELIVERED_REQUESTS := []

## The closed refusal vocabulary. Every code is a shape the committed state
## never has, so a refusal can never be a verdict about a real counter.
const REFUSAL_MAP_ABSENT := "map_row_absent"
const REFUSAL_MAP_SHAPE := "map_row_not_object"
const REFUSAL_PRIVATE_STATE_ABSENT := "private_state_absent"
const REFUSAL_PRIVATE_STATE_SHAPE := "private_state_not_object"
const REFUSAL_NOW_ABSENT := "now_absent"
const REFUSAL_NOW_TYPE := "now_not_integer"
const REFUSAL_COUNT_ABSENT := "num_trades_done_absent"
const REFUSAL_COUNT_TYPE := "num_trades_done_not_integer"
const REFUSAL_INSTANT_ABSENT := "timestamp_last_trade_absent"
const REFUSAL_INSTANT_TYPE := "timestamp_last_trade_not_integer"

## Every refusal, in the order the checks resolve.
const REFUSAL_CODES := [
	REFUSAL_MAP_ABSENT,
	REFUSAL_MAP_SHAPE,
	REFUSAL_PRIVATE_STATE_ABSENT,
	REFUSAL_PRIVATE_STATE_SHAPE,
	REFUSAL_NOW_ABSENT,
	REFUSAL_NOW_TYPE,
	REFUSAL_COUNT_ABSENT,
	REFUSAL_COUNT_TYPE,
	REFUSAL_INSTANT_ABSENT,
	REFUSAL_INSTANT_TYPE,
]

## Why each input is required at all. A counter projection that silently
## defaulted a missing input would render a value nothing recorded.
const REFUSAL_REASONS := {
	REFUSAL_MAP_ABSENT: "both counters are map-row fields, so a projection "
		+ "without the map row would have nothing to read",
	REFUSAL_MAP_SHAPE: "the map row is an object in every committed save; "
		+ "anything else is not a state document",
	REFUSAL_PRIVATE_STATE_ABSENT: "the private state is a required input so "
		+ "this record can MEASURE that neither counter is stored there",
	REFUSAL_PRIVATE_STATE_SHAPE: "same reason: an unmeasurable private state "
		+ "cannot support the measurement this projection reports",
	REFUSAL_NOW_ABSENT: "the reset predicate is reported against the server "
		+ "clock, so a projection without one cannot report either day bucket",
	REFUSAL_NOW_TYPE: "a day bucket derived from a non-integer instant would "
		+ "be a coerced value rather than a recorded one",
	REFUSAL_COUNT_ABSENT: "the count is the field under projection; "
		+ "inventing a zero would make the cap arithmetic meaningless",
	REFUSAL_COUNT_TYPE: "the branch adds one to whatever the stored count is; "
		+ "a non-integer count cannot be incremented without coercion",
	REFUSAL_INSTANT_ABSENT: "the instant is the field under projection and "
		+ "the reset predicate needs it",
	REFUSAL_INSTANT_TYPE: "a day bucket derived from a non-integer instant "
		+ "would be a coerced value rather than a recorded one",
}


## Project the trade-counter state of one map row, read-only.
##
## `now` is the SERVER CLOCK, supplied by the caller: this module reads no
## clock and starts no timer, so a caller can decide what "now" means and can
## reproduce a recorded instant exactly.
##
## The returned record carries BOTH counters verbatim, the recorded field
## untouched beside any per-field refusal, both day buckets, the legacy reset
## predicate evaluated between them, and the branch's own arithmetic over the
## stored count. A refused field contributes NO derived value that would need it.
static func project(map_row: Variant, private_state: Variant,
		now: Variant) -> Dictionary:
	if map_row == null:
		return _refuse(REFUSAL_MAP_ABSENT)
	if not (map_row is Dictionary):
		return _refuse(REFUSAL_MAP_SHAPE)
	if private_state == null:
		return _refuse(REFUSAL_PRIVATE_STATE_ABSENT)
	if not (private_state is Dictionary):
		return _refuse(REFUSAL_PRIVATE_STATE_SHAPE)
	var row: Dictionary = map_row
	var privacy: Dictionary = private_state
	return project_counters(row, privacy, now)


## Project the two counters, their day buckets, and the branch's arithmetic.
static func project_counters(row: Dictionary, privacy: Dictionary,
		now: Variant) -> Dictionary:
	if now == null:
		return _refuse(REFUSAL_NOW_ABSENT)
	if not _is_integral(now):
		return _refuse(REFUSAL_NOW_TYPE)
	var now_seconds: int = int(now)
	var count_reason: String = count_refusal(row)
	var instant_reason: String = instant_refusal(row)
	# The top-level `error` carries the FIRST offending code in the declared
	# resolution order (count, then instant) rather than a generic summary, so a
	# caller reading one field learns which field failed -- exactly as the six
	# whole-projection refusals already name their own code. `count_refusal` and
	# `instant_refusal` still report each half independently.
	var first_reason: String = count_reason
	if first_reason == "":
		first_reason = instant_reason
	var record := {
		"ok": count_reason == "" and instant_reason == "",
		"error": first_reason,
		"content_domain": CONTENT_DOMAIN,
		"count_field": "numTradesDone",
		"instant_field": "timestampLastTrade",
		"count_available": count_reason == "",
		"count_refusal": count_reason,
		"instant_available": instant_reason == "",
		"instant_refusal": instant_reason,
		"count_present": row.has("numTradesDone"),
		"instant_present": row.has("timestampLastTrade"),
		"recorded_count": row.get("numTradesDone", null),
		"recorded_instant": row.get("timestampLastTrade", null),
		"stored_count": null,
		"last_trade_instant": null,
		"cap_from_branch": TRADE_CAP_FROM_BRANCH,
		"cap_enforced": false,
		"increment_after_next_trade": null,
		"stored_after_next_trade": null,
		"remaining_after_next_trade": null,
		"remaining_clamped": false,
		"remaining_is_hypothetical": true,
		"last_trade_day_bucket": null,
		"server_clock": now_seconds,
		"server_clock_day_bucket": day_bucket(now_seconds),
		"reset_predicate_holds": null,
		"reset_performed_here": false,
		"reset_owner": RESET_OWNER["helper"],
		"private_state_carries_count": privacy.has("numTradesDone"),
		"private_state_carries_instant": privacy.has("timestampLastTrade"),
		"resources_moved": 0,
		"resource_vector_sent": false,
	}
	# Each half is guarded INDEPENDENTLY rather than by an early return, so a
	# refused count never blanks a sound instant and vice versa. Every derived
	# field starts null and is filled only by the half that has what it needs, so
	# a refused field still contributes no derived value that would require it.
	if count_reason == "":
		var count: int = int(row["numTradesDone"])
		record["stored_count"] = count
		record["increment_after_next_trade"] = count + 1
		record["stored_after_next_trade"] = \
			branch_stored_after_next_trade(count)
		record["remaining_after_next_trade"] = \
			branch_remaining_after_next_trade(count)
	if instant_reason == "":
		var instant: int = int(row["timestampLastTrade"])
		var bucket: int = day_bucket(instant)
		record["last_trade_instant"] = instant
		record["last_trade_day_bucket"] = bucket
		record["reset_predicate_holds"] = \
			reset_predicate_holds(now_seconds, instant)
	return record


## The named reason the stored count cannot be projected, or `""`.
static func count_refusal(row: Dictionary) -> String:
	if not row.has("numTradesDone"):
		return REFUSAL_COUNT_ABSENT
	if not _is_integral(row["numTradesDone"]):
		return REFUSAL_COUNT_TYPE
	return ""


## The named reason the last-trade instant cannot be projected, or `""`.
static func instant_refusal(row: Dictionary) -> String:
	if not row.has("timestampLastTrade"):
		return REFUSAL_INSTANT_ABSENT
	if not _is_integral(row["timestampLastTrade"]):
		return REFUSAL_INSTANT_TYPE
	return ""


## The branch's OWN stored value after one more recorded trade.
##
## This is `command.py:470`, whose clamp is part of the oracle. It is the ONLY
## function in either delivered module that bounds a value, and it bounds the
## STORED count, which is what the legacy branch bounds.
static func branch_stored_after_next_trade(count: int) -> int:
	return mini(TRADE_CAP_FROM_BRANCH, count + 1)


## The branch's OWN printed "remaining trades" figure after one more recorded
## trade, UNCLAMPED, exactly as `command.py:473` computes it.
##
## It goes NEGATIVE from the twenty-first recorded trade onward while the stored
## count stays at the cap. This function contains no comparison, no `mini`, no
## `max`, no floor, no absolute value and no conditional, and it must not grow
## one: the defect is a property of the oracle and correcting it here would be a
## behaviour change this contract does not make.
static func branch_remaining_after_next_trade(count: int) -> int:
	return TRADE_CAP_FROM_BRANCH - (count + 1)


## The day bucket of an instant, the engine's own `// 86400`.
static func day_bucket(instant: int) -> int:
	return instant / DAY_BUCKET_SECONDS


## The legacy reset predicate at `engine.py:239`, evaluated and NOT performed.
static func reset_predicate_holds(now: int, last_trade: int) -> bool:
	return day_bucket(now) != day_bucket(last_trade)


## The cap record, reported so a caller cannot mistake it for a limit.
static func cap_record() -> Dictionary:
	var record: Dictionary = CAP_SOURCE.duplicate(true)
	record["enforcement"] = CAP_ENFORCEMENT.duplicate(true)
	record["coincidence_recorded"] = true
	record["coincidence_note"] = (
		"a committed content row carries the same "
		+ "number and has zero legacy consumers, so the equality is two facts "
		+ "and not a derivation; the evidence report names the committed row "
		+ "and this module names no committed key at all"
	)
	return record


## The two recorded client-dictated divergences, reported not reproduced.
static func divergence_records() -> Array:
	return DIVERGENCES.duplicate(true)


## The recorded branch and counter facts, re-measured by the suite each run.
static func branch_inventory() -> Dictionary:
	var record: Dictionary = BRANCH_INVENTORY.duplicate(true)
	record["counter_sites"] = COUNTER_SITES.duplicate(true)
	record["reset"] = RESET_OWNER.duplicate(true)
	record["state_locations"] = STATE_LOCATIONS.duplicate(true)
	return record


## The closed refusal vocabulary, sorted, so a caller can diff it.
static func refusal_codes() -> Array:
	var out: Array = []
	for code: String in REFUSAL_CODES:
		if not out.has(code):
			out.append(code)
	out.sort()
	return out


## One refusal's recorded reason, or `""` for an unrecorded code.
static func refusal_reason(code: String) -> String:
	return str(REFUSAL_REASONS.get(code, ""))


## A whole-projection refusal carrying no derived field at all, so it cannot be
## read as a value.
static func _refuse(code: String) -> Dictionary:
	return {
		"ok": false,
		"error": code,
		"reason": refusal_reason(code),
		"stored_count": null,
		"last_trade_instant": null,
		"remaining_after_next_trade": null,
		"stored_after_next_trade": null,
		"reset_predicate_holds": null,
	}


## True for an integral int or an integral float.
##
## The float case exists ONLY because the content registry and the JSON reader
## decode every number as a float. It is deliberately narrow: a string, a bool, a
## null and a fractional number all fail, so a malformed recorded field cannot be
## coerced into a counter.
static func _is_integral(value: Variant) -> bool:
	var kind: int = typeof(value)
	if kind != TYPE_INT and kind != TYPE_FLOAT:
		return false
	var as_float: float = float(value)
	return is_equal_approx(as_float, float(int(as_float)))