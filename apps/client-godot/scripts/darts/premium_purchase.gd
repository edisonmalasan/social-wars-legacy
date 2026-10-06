extends RefCounted
## Premium-account duration derivation for OpenSpec `godot-darts`.
##
## ## This module is the ONE M11 surface where the preserved server computes a value
##
## Every other darts input is client-sent. `buy_premium_account`
## (`command.py:612-623`) is different: its **duration** comes from committed
## content, read on the server through `get_game_config.get_premium_days`
## (`get_game_config.py:181-189`), which reads
## `__game_config["globals"]["PREMIUM_ACCOUNTS"]`.
##
## So the duration here is derived from the **normalized** package through the
## existing `ContentRegistry.get_entry(domain, legacy_id)` accessor -- never from
## `config/main.json`, which a modern client must not read, and never from a
## client value (design D7).
##
## ## The committed price is NEVER read, and the guard is a token scan
##
## The committed schedule carries `800, 450, 80, 40, 20, 8` beside the durations
## `360, 180, 30, 7, 3, 1`. Those prices descend with duration, so the schedule is
## well-formed and was obviously meant to be charged -- and
## `get_premium_days` reads `package["time"]` and **never touches `price`**. Nothing
## anywhere in the eleven legacy modules reads it. Premium is bought for free.
##
## The refusal is enforced by a guard, not by prose: `test_darts.gd` scans this
## file's source with string literals PRESERVED and requires **zero** occurrences
## of the token `price`, and separately requires zero occurrences of any stored
## resource word in a code-only view. That is why this module never names the
## field -- not even in an identifier, not even in a comment that is scanned
## before comments are stripped... which means the honest thing is to say it
## plainly here, where the scan is documented as scanning this file.
##
## ## Both arms are reproduced, and only one is corpus-reachable
##
## `command.py:618` selects `time_now >= ts_premium`: the **set** arm writes
## `now + days * 86400` (`:619`) and the **extend** arm writes
## `ts_premium + days * 86400` (`:622`) -- two separate writes, one per arm. Every
## committed instant has PASSED (the single live one is
## `villages/Neutral.json`, `1682945878` = 2023-05-01 12:57:58 UTC), so the
## **extend arm is unreachable in the corpus** and any coverage of it is crafted
## input. That is recorded, never smoothed over.
##
## ## Why `package_index` is a `Variant` and not an `int`
##
## A typed `int` parameter makes GDScript ABORT the calling frame on a float
## argument rather than return a refusal. In this harness an aborted frame is the
## worst possible outcome: `test_base.gd::_run` does `await run_scenario()`, and a
## runtime error inside a check aborts that call instead of propagating, so
## `_finish()` sees an empty `failures` array and prints `PASS` with exit 0 while
## every remaining check silently never ran (recorded in `AGENTS.md` and
## re-observed on the sibling suite). A malformed input must therefore come back
## as a NAMED refusal, which requires the parameter to be inspectable.
##
## `get_premium_days` is recorded here as two refusals that the preserved server
## does not raise, and both are divergences rather than parity:
##   * a **non-integer** index would raise `TypeError` inside Python's list
##     subscript, so refusing it fail-closes rather than reproduces;
##   * a **negative** index would NOT raise -- Python would index from the end and
##     silently return the LAST entry, because the recorded clamp only handles
##     `index >= len(packages)`. Reproducing a silent wraparound is refused and
##     recorded.

## The recorded conversion. `command.py:619` and `:622` both multiply by this
## literal, so the committed `time` is in DAYS and is preserved in that unit.
const SECONDS_PER_DAY := 86400

## The two arms, as named constants so a caller can never spell an arm by hand.
const ARM_SET := "set"
const ARM_EXTEND := "extend"

## The recorded sites, so no line number in this file is a bare integer.
const COMMAND_SOURCE := "command.py:612-623"
const COMPARISON_SOURCE := "command.py:618"
const ARM_SET_SOURCE := "command.py:619"
const ARM_EXTEND_SOURCE := "command.py:622"
const DURATION_SOURCE := "get_game_config.py:181-189"
const CLAMP_SOURCE := "get_game_config.py:184-185"
const FALLBACK_SOURCE := "get_game_config.py:187-189"

## The one saved field this module writes, and the only one it reads.
const PREMIUM_FIELD := "timeStampEndPremium"
const INSTANT_READ_SOURCE := "command.py:617"

## The committed schedule, read through the EXISTING normalized content registry.
## `globals-tuning-normalization` owns it; this capability reads and never
## transforms, re-orders, or re-derives it (design D7).
const CONTENT_DOMAIN := "globals"
const SCHEDULE_KEY := "PREMIUM_ACCOUNTS"
const SCHEDULE_OWNER := "globals-tuning-normalization"

## The ONE field of a schedule entry this module reads. The committed entry also
## carries the price beside it; that field is deliberately absent from this
## module entirely, and `test_darts.gd` enforces its absence by token scan.
const DURATION_FIELD := "time"
const DURATION_UNIT := "days"

## The sentinel for "no duration was derived", and why it is not zero.
##
## `0` is a LEGITIMATE recorded return: `get_premium_days` returns `0` for an
## entry carrying no duration (`:187-189`). Returning `0` for a malformed schedule
## would therefore be indistinguishable from that recorded case, so malformed
## input returns `-1` and names its reason through `premium_days_refusal()`.
const MALFORMED := -1

## The closed refusal vocabulary. Every one is a shape the committed schedule
## never has; none of them is a rule the preserved server enforces.
const REFUSAL_SCHEDULE_TYPE := "schedule_not_array"
const REFUSAL_SCHEDULE_EMPTY := "schedule_empty"
const REFUSAL_INDEX_TYPE := "package_index_not_integer"
const REFUSAL_INDEX_NEGATIVE := "package_index_negative"
const REFUSAL_ENTRY_TYPE := "schedule_entry_not_object"
const REFUSAL_DURATION_TYPE := "schedule_duration_not_integer"
const REFUSAL_INSTANT_ABSENT := "premium_instant_absent"
const REFUSAL_INSTANT_TYPE := "premium_instant_not_integer"
const REFUSAL_CLOCK_NEGATIVE := "server_clock_negative"

## The named refusals `premium_days` can produce, in the order they resolve.
const DURATION_REFUSALS := [
	REFUSAL_SCHEDULE_TYPE,
	REFUSAL_SCHEDULE_EMPTY,
	REFUSAL_INDEX_TYPE,
	REFUSAL_INDEX_NEGATIVE,
	REFUSAL_ENTRY_TYPE,
	REFUSAL_DURATION_TYPE,
]

## The named refusals `purchase` adds around the duration derivation.
const PURCHASE_REFUSALS := [
	REFUSAL_CLOCK_NEGATIVE,
	REFUSAL_INSTANT_ABSENT,
	REFUSAL_INSTANT_TYPE,
]

## The recorded cost of the purchase, stated as a delivered constant.
##
## Not a measurement of this module -- it is the measured fact that nothing in
## the eleven legacy modules reads the committed amount beside the duration,
## reproduced as a value the caller can print.
##
## ## Why this module cannot spell the field it refuses
##
## `test_darts.gd` scans THIS file with string literals PRESERVED and requires
## zero occurrences of the token naming the committed amount -- not as an
## identifier, not as a key, not inside a string. Comments are stripped first,
## so the prose above can name the finding while the CODE cannot express it. That
## is why the key below is `amount_field_consumers` rather than the field's real
## name: the guard is folded and substring-based, so `price_consumers` would have
## been caught by it, which is the guard working rather than the guard being
## inconvenient.
const COST_RECORD := {
	"charged": false,
	"resources_moved": 0,
	"amount_field_consumers_measured": 0,
	"source": DURATION_SOURCE,
	"why": "get_premium_days returns the committed DURATION and never reads "
		+ "the committed amount beside it; no other legacy module reads it "
		+ "either, so a premium account is granted for nothing",
}

## The two arms and what each one writes, with its recorded site.
const ARM_RECORD := {
	ARM_SET: {
		"comparison": "now >= instant",
		"site": ARM_SET_SOURCE,
		"expression": "now + days * 86400",
		"base": "the server clock",
		"corpus_reachable": true,
		"note": "taken by every committed document, because every committed "
			+ "instant has already passed",
	},
	ARM_EXTEND: {
		"comparison": "not (now >= instant)",
		"site": ARM_EXTEND_SOURCE,
		"expression": "instant + days * 86400",
		"base": "the recorded premium instant",
		"corpus_reachable": false,
		"note": "UNREACHABLE in every committed document; coverage is crafted "
			+ "input only, never corpus evidence",
	},
}


## Reads the committed schedule through the existing normalized registry.
##
## Returns `{"ok": true, "schedule": <array>, "error": ""}` or
## `{"ok": false, "schedule": null, "error": "<named reason>"}` -- an explicit
## not-found result, never a null, a guessed empty list, or a hardcoded copy of
## the six entries. The registry is passed in rather than reached for, so this
## module performs no I/O and the suite owns the lifetime of the autoload's
## sibling instance.
static func committed_schedule(registry: Variant) -> Dictionary:
	if registry == null:
		return {"ok": false, "schedule": null, "error": "registry_absent"}
	if not (registry is Object) or not registry.has_method("get_entry"):
		return {"ok": false, "schedule": null, "error": "registry_has_no_get_entry"}
	var fetched: Variant = registry.get_entry(CONTENT_DOMAIN, SCHEDULE_KEY)
	if not (fetched is Dictionary):
		return {"ok": false, "schedule": null, "error": "lookup_result_not_object"}
	var lookup: Dictionary = fetched
	if not bool(lookup.get("found", false)):
		return {"ok": false, "schedule": null,
			"error": "no_committed_%s" % SCHEDULE_KEY}
	var entry_v: Variant = lookup.get("entry", null)
	if not (entry_v is Dictionary) or not (entry_v as Dictionary).has("value"):
		return {"ok": false, "schedule": null, "error": "entry_carries_no_value"}
	var value: Variant = (entry_v as Dictionary)["value"]
	if not (value is Array):
		return {"ok": false, "schedule": null,
			"error": REFUSAL_SCHEDULE_TYPE}
	return {"ok": true, "schedule": (value as Array).duplicate(true), "error": ""}


## The committed duration in DAYS for `package_index`, or `MALFORMED`.
##
## Reproduces `get_premium_days` exactly: the oversized-index CLAMP
## (`get_game_config.py:184-185`) resolves an index at or beyond the last entry to
## the LAST entry, and an entry carrying no duration yields `0`
## (`get_game_config.py:187-189`). No client value reaches this function.
##
## The numeric test accepts an integral FLOAT because the content registry
## decodes every JSON number as a float -- `360.0` and `360` are the same
## committed duration. It is the documented JSON decoding, not a rule.
static func premium_days(schedule: Variant, package_index: Variant) -> int:
	if premium_days_refusal(schedule, package_index) != "":
		return MALFORMED
	var entries: Array = schedule
	var index: int = int(package_index)
	if index >= entries.size():
		index = entries.size() - 1
	var entry: Dictionary = entries[index]
	if not entry.has(DURATION_FIELD):
		return 0
	return int(entry[DURATION_FIELD])


## The named reason `premium_days` would refuse, or `""` when it derives a value.
##
## Separate from `premium_days` because `0` is a legitimate recorded duration and
## cannot double as a failure signal. Callers that need to distinguish "the
## committed entry says zero days" from "this input has no committed duration"
## must ask here; a caller that only wants the number can ignore it.
static func premium_days_refusal(schedule: Variant, package_index: Variant) -> String:
	if not (schedule is Array):
		return REFUSAL_SCHEDULE_TYPE
	var entries: Array = schedule
	if entries.is_empty():
		return REFUSAL_SCHEDULE_EMPTY
	if not _is_integral(package_index):
		return REFUSAL_INDEX_TYPE
	if int(package_index) < 0:
		return REFUSAL_INDEX_NEGATIVE
	var index: int = int(package_index)
	if index >= entries.size():
		index = entries.size() - 1
	var entry_v: Variant = entries[index]
	if not (entry_v is Dictionary):
		return REFUSAL_ENTRY_TYPE
	var entry: Dictionary = entry_v
	if not entry.has(DURATION_FIELD):
		# The recorded fallback, not a refusal: `get_premium_days` returns 0.
		return ""
	if not _is_integral(entry[DURATION_FIELD]):
		return REFUSAL_DURATION_TYPE
	return ""


## Which arm the recorded comparison selects: `now >= instant` is the set arm.
##
## The comparison is reproduced verbatim, including its `>=`: at the exact
## boundary `now == instant` the recorded branch takes the SET arm, so the
## boundary belongs to the set arm and not to the extend arm.
static func select_arm(now: int, instant: int) -> String:
	if now >= instant:
		return ARM_SET
	return ARM_EXTEND


## The instant the purchase writes, on either arm.
##
## Pure: it takes the already-derived `days` and returns the new instant without
## reading or writing any document. Nothing here charges anything, which is why
## `COST_RECORD.resources_moved` is `0` and the suite proves it by comparing the
## COMPLETE seven-slot stored resource set after applying the derived write.
static func instant_after(now: int, instant: int, days: int) -> int:
	if select_arm(now, instant) == ARM_SET:
		return now + days * SECONDS_PER_DAY
	return instant + days * SECONDS_PER_DAY


## The whole recorded purchase, as one derived result.
##
## `now` is the SERVER clock: no client value reaches the instant this function
## reports. `instant` is the recorded value the recorded branch READS
## (`command.py:617`). `schedule` is the committed content read above.
##
## On refusal the result carries `ok: false` and a named `error`, and **no**
## instant -- so a refused purchase cannot be mistaken for a zero-day one.
static func purchase(now: int, instant: Variant, schedule: Variant,
		package_index: Variant) -> Dictionary:
	var base := {
		"ok": false,
		"error": "",
		"command": "buy_premium_account",
		"command_source": COMMAND_SOURCE,
		"field": PREMIUM_FIELD,
		"client_sent": {
			"package_index": "args[0]",
			"source": COMMAND_SOURCE,
		},
		"duration_client_sent": false,
		"duration_source": DURATION_SOURCE,
		"duration_field": DURATION_FIELD,
		"duration_unit": DURATION_UNIT,
		"schedule_key": SCHEDULE_KEY,
		"schedule_owner": SCHEDULE_OWNER,
		"charged": false,
		"resources_moved": 0,
		"seconds_per_day": SECONDS_PER_DAY,
		"days": MALFORMED,
		"seconds": MALFORMED,
		"arm": "",
		"instant_before": MALFORMED,
		"instant_after": MALFORMED,
	}
	if now < 0:
		base["error"] = REFUSAL_CLOCK_NEGATIVE
		return base
	if instant == null:
		base["error"] = REFUSAL_INSTANT_ABSENT
		return base
	if not _is_integral(instant):
		base["error"] = REFUSAL_INSTANT_TYPE
		return base
	var duration_reason: String = premium_days_refusal(schedule, package_index)
	if duration_reason != "":
		base["error"] = duration_reason
		return base
	var days: int = premium_days(schedule, package_index)
	var before: int = int(instant)
	var arm: String = select_arm(now, before)
	base["ok"] = true
	base["days"] = days
	base["seconds"] = days * SECONDS_PER_DAY
	base["arm"] = arm
	base["arm_record"] = ARM_RECORD.get(arm, {})
	base["instant_before"] = before
	base["instant_after"] = instant_after(now, before, days)
	base["clamped"] = _is_clamped(schedule, package_index)
	return base


## True when the recorded clamp moved the index (`get_game_config.py:184-185`).
##
## Reported so the clamp is visible in a result rather than silent. It compares
## the requested index against the schedule's length and nothing else.
static func _is_clamped(schedule: Variant, package_index: Variant) -> bool:
	if not (schedule is Array) or not _is_integral(package_index):
		return false
	return int(package_index) >= (schedule as Array).size()


## True for an integral int or an integral float.
##
## The float case exists ONLY because the content registry decodes every JSON
## number as a float. It is deliberately narrow: a string, a bool, a null, and a
## fractional number all fail, so a malformed entry cannot be coerced into a
## duration.
static func _is_integral(value: Variant) -> bool:
	var kind: int = typeof(value)
	if kind != TYPE_INT and kind != TYPE_FLOAT:
		return false
	var as_float: float = float(value)
	return is_equal_approx(as_float, float(int(as_float)))