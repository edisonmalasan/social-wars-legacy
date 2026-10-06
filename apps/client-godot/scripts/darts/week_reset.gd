extends RefCounted
## The week-boundary reset predicate for OpenSpec `godot-darts`.
##
## ## `reset_stuff` is the ONLY time-derived darts mutation in the preserved server
##
## `engine.py:230-249` is reached from `get_player_info.py:9` on **every**
## player-info fetch. It is **not** a command, and nothing the client sends
## triggers it. It touches darts state exactly once:
##
##     243:  if "timeStampDartsReset" in privateState:
##     246:      last_darts_reset = privateState["timeStampDartsReset"] + 259200
##     247:      temp = now + 259200
##     248:      if temp // 604800 != last_darts_reset // 604800:
##     249:          privateState["timeStampDartsReset"] = 0
##
## Three properties are reproduced EXACTLY and nothing else is added:
##
##   * the recorded **offset** `259200` (three days) is applied to **BOTH**
##     sides -- to the recorded instant and to the server clock;
##   * the comparison is a **floor-division week inequality**, not a date
##     comparison: `temp // WEEK != last // WEEK`;
##   * the **existence guard** `if "timeStampDartsReset" in privateState` is
##     reproduced, so a record lacking the field is not reset and not defaulted.
##
## ## The write is ZERO, never the clock (design D5)
##
## `:249` writes `0`, not `time_now`. The field is a flag for the client to call
## `darts_reset`, which is exactly what `sessions.py:121`'s comment says. So this
## module DELIVERS NO MUTATION and NO ROUTE: it is a predicate, and the value the
## recorded branch would write is reported as a constant (`RESET_VALUE`) rather
## than written anywhere. `test_darts.gd` asserts the empty route set and scans
## this file for any assignment out of the server clock.
##
## ## The Monday comment is a COMMENT, and no weekday is computed
##
## `:244` says, in the source's own words: *"take away 3 days since timestamp 0
## is thursday, we want reset to happen on monday"*. That intent is reported here
## as `INTENT_COMMENT` and **no weekday is derived anywhere**. Nothing in the
## preserved server computes a weekday, so a delivered `weekday_of` would be an
## invention; the recorded offset is transcribed as the literal it is.
##
## ## Floor division, and why a negative instant is refused rather than wrapped
##
## Python's `//` FLOORS; GDScript's integer `/` TRUNCATES TOWARD ZERO. The two
## agree for every non-negative value and differ only below zero, where
## `-604800 // 604800 == -1` but `-604800 / 604800 == 0`. Every committed instant
## is non-negative, so reproducing the division with the engine's operator is
## exact for every value the corpus holds. Rather than add a correction branch for
## a value no document can carry, a negative instant is **refused** with a named
## reason and the difference is recorded as a divergence.
##
## ## What this module deliberately does not deliver
##
## `reset_stuff` ALSO resets `map["numTradesDone"]` on a **day** boundary at
## `:239-240`. That is not darts state and is out of scope, and it is named here
## so a later line does not rediscover the function and assume it touches darts
## alone.

## The one darts field the recorded branch reads, guards, and writes.
const FIELD := "timeStampDartsReset"

## The recorded sites, so no line number here is a bare integer.
const SOURCE := "engine.py:243-249"
const GUARD_SOURCE := "engine.py:243"
const OFFSET_SOURCE := "engine.py:246-247"
const COMPARISON_SOURCE := "engine.py:248"
const WRITE_SOURCE := "engine.py:249"
const CALLER_SOURCE := "get_player_info.py:9"

## The recorded constants, transcribed verbatim. `259200` is three days and
## `604800` is one week; the source states both in its own comments.
const OFFSET_SECONDS := 259200
const WEEK_SECONDS := 604800

## What the recorded branch WRITES: zero, never the server clock.
const RESET_VALUE := 0

## The trigger the write encodes, in the branch's own comment at `:241`.
const CLIENT_TRIGGER := "game calls darts_reset if timestamp is 0"

## The source's own intent, quoted, and the fact that nothing computes from it.
const INTENT_COMMENT := {
	"source": "engine.py:244",
	"quoted": "take away 3 days since timestamp 0 is thursday, we want "
		+ "reset to happen on monday",
	"delivered_as": "a comment",
	"weekday_computed": false,
	"why": "the offset is transcribed as the literal 259200 it is; deriving a "
		+ "weekday would invent a rule no preserved branch evaluates",
}

## The out-of-scope sibling reset, named so the function is not mistaken for a
## darts-only one.
const OUT_OF_SCOPE_RESET := {
	"field": "numTradesDone",
	"site": "engine.py:239-240",
	"boundary": "day",
	"delivered_here": false,
	"why": "it is market-trade state, not darts state, and this capability "
		+ "projects darts state only",
}

## No route and no mutation are delivered (design D5).
const DELIVERED_ROUTES := []
const MUTATION_DELIVERED := false

## The closed verdict vocabulary, in the order `evaluate` resolves it.
const REASON_ABSENT := "instant_absent"
const REASON_INSTANT_TYPE := "instant_not_integer"
const REASON_NEGATIVE := "instant_negative"
const REASON_CLOCK_NEGATIVE := "server_clock_negative"
const REASON_WEEK_BOUNDARY := "week_boundary"
const REASON_SAME_WEEK := "same_week"

const REASON_CLOCK_NEGATIVE_FIRST := [
	REASON_CLOCK_NEGATIVE, REASON_ABSENT, REASON_INSTANT_TYPE,
	REASON_NEGATIVE, REASON_WEEK_BOUNDARY, REASON_SAME_WEEK,
]

## Why the negative cases are refusals rather than reproductions, stated as data.
const FLOOR_DIFFERENCE := {
	"python_floors": true,
	"gdscript_truncates_toward_zero": true,
	"agree_for_non_negative_values": true,
	"example_disagreeing_value": -604800,
	"example_python_result": -1,
	"example_gdscript_result": 0,
	"resolution": "refuse a negative instant with a named reason instead of "
		+ "adding a correction branch for a value no committed document carries",
	"is_divergence": true,
}


## An explicit sentinel for "not computed", distinct from any week index.
const MALFORMED_WEEK := -1


## The floor-division week index the recorded comparison uses on both sides.
##
## `@warning_ignore` because the engine flags integer division; the division IS
## the recorded operation, and `FLOOR_DIFFERENCE` records why the engine's
## truncation is exact for every non-negative input this module accepts.
@warning_ignore("integer_division")
static func week_index(value: int) -> int:
	return value / WEEK_SECONDS


## The recorded week-boundary predicate, over (existence, instant, clock).
##
## `present` is the recorded existence guard (`if "timeStampDartsReset" in
## privateState`) passed explicitly rather than inferred, because the guard is
## part of the recorded contract and inferring it from a default value would hide
## the very case worth seeing.
##
## Returns a result carrying the recorded reason, both shifted sides, both week
## indices, the comparison the recorded branch performs, and the value it would
## write. It performs NO write: `reset_value` is reported, not applied.
static func evaluate(present: bool, instant: Variant, now: int) -> Dictionary:
	var result := {
		"ok": true,
		"reason": "",
		"reset_due": false,
		"field": FIELD,
		"source": SOURCE,
		"guard_source": GUARD_SOURCE,
		"offset_seconds": OFFSET_SECONDS,
		"week_seconds": WEEK_SECONDS,
		"reset_value": RESET_VALUE,
		"reset_value_is_clock": false,
		"written": MUTATION_DELIVERED,
		"shifted_instant": MALFORMED_WEEK,
		"shifted_clock": MALFORMED_WEEK,
		"instant_week": MALFORMED_WEEK,
		"clock_week": MALFORMED_WEEK,
		"comparison": "",
		"other_reset_delivered": false,
		"client_trigger": CLIENT_TRIGGER,
	}
	if now < 0:
		result["ok"] = false
		result["reason"] = REASON_CLOCK_NEGATIVE
		return result
	if not present:
		# The recorded existence guard: a record without the field is skipped
		# whole, so neither week index is even computed.
		result["reason"] = REASON_ABSENT
		return result
	if not _is_integral(instant):
		result["ok"] = false
		result["reason"] = REASON_INSTANT_TYPE
		return result
	if int(instant) < 0:
		result["ok"] = false
		result["reason"] = REASON_NEGATIVE
		return result
	var shifted_instant: int = int(instant) + OFFSET_SECONDS
	var shifted_clock: int = now + OFFSET_SECONDS
	result["shifted_instant"] = shifted_instant
	result["shifted_clock"] = shifted_clock
	result["instant_week"] = week_index(shifted_instant)
	result["clock_week"] = week_index(shifted_clock)
	result["comparison"] = "%d // %d != %d // %d" % [shifted_clock,
		WEEK_SECONDS, shifted_instant, WEEK_SECONDS]
	var boundary: bool = week_index(shifted_clock) != week_index(shifted_instant)
	result["reset_due"] = boundary
	result["reason"] = REASON_WEEK_BOUNDARY if boundary else REASON_SAME_WEEK
	return result


## True for an integral int or an integral float.
##
## The float case exists only because JSON decodes every number as a float, and
## every committed instant is a whole number of seconds.
static func _is_integral(value: Variant) -> bool:
	var kind: int = typeof(value)
	if kind != TYPE_INT and kind != TYPE_FLOAT:
		return false
	var as_float: float = float(value)
	return is_equal_approx(as_float, float(int(as_float)))