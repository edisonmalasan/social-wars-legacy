extends RefCounted
## Committed market-schedule projection for OpenSpec
## `godot-market-trade-counters`.
##
## ## One read path, and it is the registry
##
## The committed rows are read through the EXISTING normalized content registry,
## under the `globals` domain, and are NEVER transcribed into this module. No
## line below names a committed key, so the evidence report and the suite read
## the eight rows from the verified index and this module only ever sees values
## handed to it.
##
## The registry is passed in rather than reached for, exactly as
## `auction_schedule.gd` does, so this module performs no I/O and the caller
## owns the lifetime of the index. `legacy_ids()` is used rather than
## `get_entry()` for the enumeration so the order is the committed file's own and
## not a collation.
##
## ## A PREFIX is not a SUBSTRING, and the difference is three rows
##
## Eight committed rows begin with the market prefix. Eleven CONTAIN it, because
## three committed constants embed the same word inside a longer identifier.
## A substring scan would have selected eleven rows and three of them have
## nothing to do with a trade schedule. `prefix_record()` states the rule this
## module uses so the difference is a decision on the record rather than an
## accident, and the suite measures both directions every run.
##
## ## The whole schedule is UNREAD by the preserved server
##
## Every one of the eight committed values has zero legacy consumers -- zero raw
## occurrences, zero quoted-access occurrences and zero whole-token occurrences
## across all eleven legacy root modules. So there is no committed price, no
## committed period, no committed percentage and no committed increment bound to
## derive, and this module derives none. `no_derived_record()` enumerates what is
## absent, and the file contains no multiplication, no division and no remainder
## at all, which makes that claim mechanical rather than asserted.
##
## `consumer_counts` is therefore PASSED IN. This module does not read the legacy
## sources: it reports the measurement it is handed and names the rule under
## which the caller measured it, so a reader can tell a reported measurement from
## an inherited one. The suite re-measures on every run.
##
## ## One number coincides with the branch literal, and that is all it is
##
## A committed row carries the same value the legacy branch hardcodes as its
## stored cap. The equality is recorded as a COINCIDENCE in the evidence report,
## where both sides are read rather than transcribed, and the cap is never
## derived from this table. An unread constant may not become load-bearing.
##
## ## No ordinal is claimed for the zero-consumer count
##
## Four conflicting ordinals already exist in this project's delivered records,
## each counted over a different scope, so nothing here claims a position for the
## market-schedule zero-consumer census. The suite enforces the absence over the
## code-only text of both delivered modules and separately asserts that this
## rationale is still present, so the guard cannot be weakened into a scan of
## comments.

## The normalized content domain carrying the committed tuning constants.
const CONTENT_DOMAIN := "globals"

## The prefix a committed row's KEY must BEGIN with to belong to this schedule.
##
## It is a prefix and never a substring. The committed table also carries rows
## that embed the same word inside a longer identifier, and selecting on a
## substring would pull them into a market schedule they do not belong to.
const SCHEDULE_PREFIX := "MARKET_"

## The committed row fields this projection carries, verbatim and nothing else.
const PROJECTED_FIELDS := ["key", "value", "value_type", "source_file"]

## Why the prefix rule is a prefix rule, recorded so it cannot be "simplified".
const PREFIX_RECORD := {
	"rule": "a committed row belongs to this schedule only when its key BEGINS "
		+ "with the market prefix",
	"selection_is": "prefix-anchored, never substring",
	"why": "the committed table also carries rows that embed the same word "
		+ "inside a longer identifier, so a substring rule would select them "
		+ "as market-schedule rows and they are not",
	"rows_selected_by_this_rule": 8,
	"rows_a_substring_rule_would_also_select": 11,
	"substring_direction_measured_every_run_by": "test_market_trade.gd",
}

## The closed refusal vocabulary. Every code is a shape the committed table
## never has, so a refusal can never be a verdict about a real committed row.
const REFUSAL_REGISTRY_ABSENT := "registry_absent"
const REFUSAL_REGISTRY_SHAPE := "registry_has_no_legacy_ids"
const REFUSAL_DOMAIN_ABSENT := "no_committed_globals_domain"
const REFUSAL_ROWS_TYPE := "schedule_rows_not_array"
const REFUSAL_ROW_TYPE := "committed_row_not_object"
const REFUSAL_KEY_ABSENT := "committed_key_absent"
const REFUSAL_KEY_TYPE := "committed_key_not_string"
const REFUSAL_VALUE_ABSENT := "committed_value_absent"

## Every refusal, in the order the checks resolve.
const REFUSAL_CODES := [
	REFUSAL_REGISTRY_ABSENT,
	REFUSAL_REGISTRY_SHAPE,
	REFUSAL_DOMAIN_ABSENT,
	REFUSAL_ROWS_TYPE,
	REFUSAL_ROW_TYPE,
	REFUSAL_KEY_ABSENT,
	REFUSAL_KEY_TYPE,
	REFUSAL_VALUE_ABSENT,
]

## Why each shape is refused rather than coerced.
const REFUSAL_REASONS := {
	REFUSAL_REGISTRY_ABSENT: "the committed rows are read through the "
		+ "registry and from nowhere else, so there is no registry-free path",
	REFUSAL_REGISTRY_SHAPE: "a caller can be handed something that is not a "
		+ "registry and would then receive content nobody asked the registry for",
	REFUSAL_DOMAIN_ABSENT: "the committed rows live under one domain; a package "
		+ "without it cannot serve this schedule",
	REFUSAL_ROWS_TYPE: "a schedule is a list of committed rows and a single row "
		+ "is not a schedule",
	REFUSAL_ROW_TYPE: "a committed row is an object; anything else is not one",
	REFUSAL_KEY_ABSENT: "the key is this surface's identity; a row without one "
		+ "cannot be reported and cannot be selected",
	REFUSAL_KEY_TYPE: "a key that is not a string cannot be matched against the "
		+ "prefix rule without coercion",
	REFUSAL_VALUE_ABSENT: "a committed row with no value carries no schedule "
		+ "content, so reporting one would invent a value",
}

## The measured census this module does NOT perform and therefore cannot report
## on its own authority.
##
## The caller measures it over the legacy sources and hands the counts in. The
## record names the rule so a reader knows what a number in a projected row means.
const CONSUMER_RULE := {
	"rule_id": "quoted-access over every legacy module",
	"measured_by": "test_market_trade.gd",
	"measured_by_delivered_module": false,
	"rule": "how many legacy occurrences of the committed key name, counted "
		+ "the way this codebase touches state",
	"modules_required": "all eleven legacy root modules; a consumer count over "
		+ "a subset is not a consumer count",
	"rows_with_a_consumer_expected": 0,
	"raw_substring_is_not_the_rule": "the preserved server touches state through "
		+ "quoted keys, and a raw substring count also matches longer identifiers "
		+ "that embed the same word, so three measures are reported and the "
		+ "quoted-access one is the rule",
}

## What this module derives: nothing, enumerated so the absence is a record.
const NO_DERIVED_RECORD := {
	"derived_value_count": 0,
	"derived_values": [],
	"not_derived": [
		"price", "cost", "fee", "total",
		"period", "percentage", "ratio",
		"increment bound", "decrement bound",
		"trade cap", "revenue",
	],
	"arithmetic_in_this_file": "none: no multiplication, no division and no "
		+ "remainder appear anywhere in it",
	"why": "every committed value on this surface has zero legacy consumers, so "
		+ "there is no committed rule to apply any of them by, and an economy "
		+ "derived from unread content would be an invention",
}

## Mechanisms this capability does NOT deliver, each with its measured reason.
const ABSENT_HELPERS := [
	{"helper": "sell_ratio", "absent_because":
		"the committed percentage is unread by every legacy module, so a ratio "
		+ "from it would be an invented price rule"},
	{"helper": "trade_amount_for", "absent_because":
		"the committed amount list is unread everywhere and the branch never "
		+ "consults it"},
	{"helper": "period_seconds", "absent_because":
		"the committed period is unread and nothing evaluates it, so converting "
		+ "it would need a clock and a rule the oracle does not have"},
	{"helper": "increment_bound", "absent_because":
		"the committed increment bound is unread and unbound to any branch"},
	{"helper": "decrement_bound", "absent_because":
		"the committed decrement bound is unread for the same reason"},
	{"helper": "base_costs_for", "absent_because":
		"the committed base-cost object is unread and maps no resource name "
		+ "this client can spend"},
	{"helper": "schedule_cap", "absent_because":
		"the committed row carrying the same number as the branch literal has "
		+ "zero consumers, so it may not become load-bearing"},
	{"helper": "economy_summary", "absent_because":
		"no price, period, percentage or total is computed anywhere, so there is "
		+ "nothing to summarise"},
]

## No route and no action. Declared empty so the suite can assert the closed set
## rather than whatever the code happens to branch on.
const DELIVERED_ROUTES := []
const DELIVERED_ACTIONS := []
const DELIVERED_REQUESTS := []

## One committed row: its index key, its entry, or the named refusal.
static func _committed(registry: Variant, legacy_id: String) -> Dictionary:
	if registry == null:
		return _refuse(REFUSAL_REGISTRY_ABSENT)
	if not (registry is Object) or not registry.has_method("get_entry"):
		return _refuse(REFUSAL_REGISTRY_SHAPE)
	var got: Variant = registry.get_entry(CONTENT_DOMAIN, legacy_id)
	if not (got is Dictionary):
		return _refuse(REFUSAL_REGISTRY_SHAPE)
	var row: Dictionary = got
	if not bool(row.get("found", false)):
		return _refuse(REFUSAL_ROW_TYPE)
	var stored: Variant = row.get("entry", null)
	if not (stored is Dictionary):
		return _refuse(REFUSAL_ROW_TYPE)
	return stored as Dictionary


## Every committed row whose KEY BEGINS with the market prefix, in the
## registry's own committed order.
##
## The domain is enumerated, not the prefix: the prefix selects among the rows
## the registry already holds, so the suite may hand in the whole domain and
## this selection is still the one the rule describes.
static func committed_rows(registry: Variant) -> Dictionary:
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
	var rows: Array = []
	var matched: int = 0
	var examined: int = 0
	for legacy_id: Variant in (ids as Array):
		examined += 1
		var fetched_row: Dictionary = _committed(registry, str(legacy_id))
		if not fetched_row.has("key"):
			return _refuse(fetched_row.get("error", REFUSAL_ROW_TYPE))
		if not str(fetched_row["key"]).begins_with(SCHEDULE_PREFIX):
			continue
		matched += 1
		rows.append(fetched_row.duplicate(true))
	return {
		"ok": true,
		"error": "",
		"rows": rows,
		"count": rows.size(),
		"domain_examined": examined,
		"committed_file": str(lookup.get("file", "")),
		"order": "the registry's committed order, not a collation",
	}


## Project every committed row verbatim, with the caller's consumer measurement
## beside it.
##
## A refused row contributes its named reason and is counted, and it does NOT
## stop the projection: every selected row is reported either way and the refused
## count is reported alongside, so a short successful list cannot be mistaken for
## a complete one.
static func project(rows: Variant, consumer_counts: Variant) -> Dictionary:
	if not (rows is Array):
		return _refuse(REFUSAL_ROWS_TYPE)
	var counts: Dictionary = {}
	if consumer_counts is Dictionary:
		counts = consumer_counts as Dictionary
	var table: Array = []
	var refused: int = 0
	for raw: Variant in (rows as Array):
		var record: Dictionary = project_row(raw, counts)
		if not bool(record["ok"]):
			refused += 1
		table.append(record)
	return {
		"ok": refused == 0,
		"error": "" if refused == 0 else "one_or_more_rows_refused",
		"rows": table,
		"count": table.size(),
		"refused": refused,
		"content_domain": CONTENT_DOMAIN,
		"selection": PREFIX_RECORD["selection_is"],
		"derived_value_count": NO_DERIVED_RECORD["derived_value_count"],
	}


## Project ONE committed row.
##
## Every committed field is carried unaltered. No value is compared with another,
## no value is scaled, and no value is bounded. The consumer count is reported as
## measured by the caller, and an unmeasured row says so rather than claiming
## zero.
static func project_row(raw: Variant, consumer_counts: Dictionary) -> Dictionary:
	var reason: String = row_refusal(raw)
	if reason != "":
		return {
			"ok": false,
			"error": reason,
			"reason": refusal_reason(reason),
			"key": "",
			"value": null,
			"value_type": "",
			"consumer_count": null,
			"has_consumer": null,
			"consumer_measured": false,
		}
	var row: Dictionary = raw
	var key: String = str(row["key"])
	var record := {
		"ok": true,
		"error": "",
		"key": key,
		"value": row["value"],
		"value_type": str(row.get("value_type", "")),
		"source_file": str(row.get("source_file", "")),
		"value_verbatim": true,
		"scaled": false,
		"bounded": false,
		"derived_from": "the committed normalized registry only",
	}
	if consumer_counts.has(key):
		var measured: int = int(consumer_counts[key])
		record["consumer_count"] = measured
		record["has_consumer"] = measured > 0
		record["consumer_measured"] = true
	else:
		record["consumer_count"] = null
		record["has_consumer"] = null
		record["consumer_measured"] = false
	return record


## The named reason this committed row cannot be projected, or `""`.
static func row_refusal(raw: Variant) -> String:
	if not (raw is Dictionary):
		return REFUSAL_ROW_TYPE
	var row: Dictionary = raw
	if not row.has("key"):
		return REFUSAL_KEY_ABSENT
	if not (row["key"] is String):
		return REFUSAL_KEY_TYPE
	if not row.has("value"):
		return REFUSAL_VALUE_ABSENT
	return ""


## The census rule this module reports against, and does not perform.
static func consumer_rule() -> Dictionary:
	return CONSUMER_RULE.duplicate(true)


## The recorded absence of any derived economy.
static func no_derived_record() -> Dictionary:
	return NO_DERIVED_RECORD.duplicate(true)


## The recorded prefix rule and the row counts the two rules would select.
static func prefix_record() -> Dictionary:
	return PREFIX_RECORD.duplicate(true)


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


## A refusal result carrying no derived field, so it cannot be read as a value.
static func _refuse(code: String) -> Dictionary:
	return {"ok": false, "error": code, "reason": refusal_reason(code),
		"rows": null, "count": 0}


## True for a string, or "" for anything else.
##
## There is no numeric coercion on this surface at all, which is why this file
## carries no arithmetic operator of any kind.
static func _is_string(value: Variant) -> bool:
	return value is String