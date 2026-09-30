extends RefCounted
## Pure evaluation helpers for the production-queue flow (OpenSpec
## `godot-unit-queues` "A queue is a count, a start instant, and an optional
## queued unit id" / "No elapsed-time evaluation and no completion" / "The atom-
## fusion speedup is recorded without a cost or a timer" / "A queued unit id
## resolves through content, and an unresolvable one is reported", design
## D1-D7).
##
## The committed `attr` bag is **always a parameter**: this module holds no
## node, no clock, no request, and no content of its own, so the town view, the
## hermetic suite, and the deterministic report consume the SAME functions over
## the SAME save bytes — exactly as `level_flow.gd`, `expand_flow.gd`,
## `collection_flow.gd`, and `construction_flow.gd` serve the delivered flows.
## The projection itself lives in `unit_queue.gd` and is **delegated**, never
## re-derived: a surface, the suite, and the report therefore cannot disagree
## about a queue by a key.
##
## ## The ONE evaluation entry point
##
## `evaluate()` below is what a surface uses, exactly as `level_flow.evaluate()`
## serves the progression flow. It projects the bag once, reports the queue's
## **presence** and its committed values, carries the recorded teardown, and
## carries the recorded speedup precondition's verdict — and it computes **no**
## readiness, **no** remaining time, **no** progress ratio, and **no**
## completion, because the legacy server has none of those rules to reproduce
## (design D1/D2). A structural rejection is `ok: false` with a named reason;
## a readable bag is `ok: true` whatever the queue holds, because "no queue" and
## "a queue of 3" are both **reports**, never errors.
##
## ## What is deliberately absent, as a NAMED list
##
## `NON_READINESS` is the machine-readable form of the absence: these helpers do
## not exist and must not be added here, because each would compute a rule the
## legacy server never had. The suite asserts the module's whole function
## inventory against `EXPECTED_METHODS`-style checks, so a readiness helper
## cannot appear unnoticed.
##
## ## The offered intents are client-side UX, not authority
##
## `offers_push()` offers a push for any row whose bag is readable and
## `offers_pop()` offers a pop only for a row that actually carries a count —
## legacy's inert pop on an absent count is a **recorded no-op**, so the client
## simply never offers it. Neither predicate checks that the row is a training
## producer, reads `training_time`, checks `min_level`, or caps the count: the
## three legacy branches validate **nothing** (design D5), and the recorded
## absence of validation is **not permission** to invent one. These predicates
## also gate nothing server-side: they are a button's availability, and the
## service's own guards plus a later server-authoritative milestone own the
## rules.
##
## ## What is ESTABLISHED versus DERIVED
##
## Every committed effect in `UnitQueue`'s records is established and traced to
## its committed source; this module adds no effect of its own. Its **derived**
## parts are the presence predicates above, the readout's wording, and the
## composition of its lines — the delivered provisional convention, never a
## claim about what the legacy client displayed. The established-versus-derived
## split itself lives in `UnitQueue.PROVENANCE` and the non-claims in
## `UnitQueue.NON_CLAIMS`, so there is exactly one record of each.

const UnitQueue = preload("res://scripts/units/unit_queue.gd")

## The helpers this flow deliberately does **NOT** provide, with the reason
## each is absent. Every entry is a readiness/remaining/progress/completion rule
## the legacy server does not have to reproduce (design D1/D2), so adding one
## would compute an invented answer — and the suite asserts this module's
## function inventory contains none of them.
const NON_READINESS := [
	{"helper": "is_complete", "absent_because":
		"no legacy command completes a queue and no command materialises a "
		+ "unit from one, so there is no server-side completion to reproduce"},
	{"helper": "remaining", "absent_because":
		"no legacy branch evaluates a queue's elapsed time: every occurrence "
		+ "of attr['ts'] is a write or a deletion, and the only reader is the "
		+ "soul-mixer speedup, which is not a general queue path"},
	{"helper": "progress_ratio", "absent_because":
		"a ratio needs a duration, and NO queue branch reads training_time or "
		+ "sm_training_time, so there is no committed denominator"},
	{"helper": "ready_at", "absent_because":
		"the start instant is reported verbatim and nothing derives an "
		+ "instant from it"},
	{"helper": "complete", "absent_because":
		"completion is a server-authoritative decision and this milestone "
		+ "delivers none; it belongs to a later line with its own evidence"},
]

## The recorded inert pop: a `pop_queue_unit` against a row whose bag carries no
## `nu` returns without writing anything (`engine.py:193-194`). It is a real,
## recorded behaviour rather than an error, which is why the endpoint accepts
## it and the client simply does not offer it.
const POP_INERT_NO_OP := ("a pop against a row whose attribute bag carries no "
	+ "count is an INERT recorded no-op, not an error: engine.pop_queue_unit "
	+ "returns without writing anything when nu is absent (engine.py:193-194), "
	+ "and the endpoint answers success with an unchanged bag. The client does "
	+ "not offer it, and offers_pop() reports false for such a row")

## The recorded inert-pop refusal reason a caller may surface instead of the
## no-op. It is a **client-side** reason, never a service code: the service has
## no such code because it never refuses this case.
const REASON_NO_QUEUE := "no_queue"

## The name a queue's count reads as when the row carries no count at all — a
## named absence in the readout, never a committed zero.
const COUNT_ABSENT_TEXT := "[no count]"
## The name an unresolved queued unit reads as in the readout — a **named
## absence**, never a substituted unit (design D7).
const UNIT_UNRESOLVABLE_TEXT := "[unresolvable queued unit]"
## The name a row with no queued unit reads as in the readout.
const UNIT_NONE_TEXT := "[no queued unit]"


# ---------------------------------------------------------------------------
# The one evaluation
# ---------------------------------------------------------------------------


## The whole queue evaluation for one placed row, and the ONLY entry point a
## surface uses. Returns
## `{ok, reason, error, queue, fields, present, count, start_instant,
## queued_unit_id, queued_unit_resolution, queued_unit_name, keys, teardown,
## offers_push, offers_pop, speedup}`.
##
## The refusals, in evaluation order:
##   * `invalid_attr`          the row's attribute bag is not an object. An
##     empty bag and a missing bag mean the same thing; a bag that is not a bag
##     is a different thing entirely, and reading it as an empty queue would
##     report a fact the save does not carry.
##   * `invalid_count`         the committed `nu` is not an integer, or is
##     negative. The legacy engine would raise inside its helper; a silently
##     coerced count would compare against a number the save never held.
##   * `invalid_start_instant` the committed `ts` is not an integer.
##
## A refusal returns `ok: false` — an error, not a report. Everything else
## returns `ok: true` with `present` telling the reader whether a queue exists,
## which is the presence decision the flow exists to make.
static func evaluate(attr: Variant, resolve_unit: Variant) -> Dictionary:
	var projection: Variant = UnitQueue.project(attr, resolve_unit)
	if not bool(projection.get("ok", false)):
		var reason := str(projection.get("reason", UnitQueue.REASON_INVALID_BAG))
		return _evaluation_reject(reason, str(projection.get("error", "")))
	var queue: Variant = projection.get("queue", null)
	var fields: Dictionary = queue.fields()
	var present := bool(fields["present"])
	var evaluation := {
		"ok": true,
		"reason": "",
		"error": "",
		"queue": queue,
		"fields": fields,
		"present": present,
		"count": fields["count"],
		"start_instant": fields["start_instant"],
		"queued_unit_id": fields["queued_unit_id"],
		"queued_unit_resolution": fields["queued_unit_resolution"],
		"queued_unit_name": fields["queued_unit_name"],
		"keys": fields["keys"],
		"teardown": fields["teardown"],
		"offers_push": false,
		"offers_pop": false,
		"speedup": UnitQueue.speedup_precondition(attr),
	}
	evaluation["offers_push"] = offers_push(evaluation)
	evaluation["offers_pop"] = offers_pop(evaluation)
	return evaluation


## Whether this client would offer a **push** for the evaluated row. True for
## every readable bag, queued or not: the legacy push increments a count and
## stamps an instant on any row at all, and the recorded absence of a producer,
## duration, level, or count check is **not permission** to add one here
## (design D5). This is a button's availability, not an authority.
static func offers_push(evaluation: Dictionary) -> bool:
	return bool(evaluation.get("ok", false))


## Whether this client would offer a **pop** for the evaluated row. True only
## when the row actually carries a count: legacy's pop on an absent count is a
## recorded inert no-op (see `POP_INERT_NO_OP`), so offering it would send a
## transaction that changes nothing. No other rule gates it — not the count's
## size, not the row's identity, not any duration.
static func offers_pop(evaluation: Dictionary) -> bool:
	if not bool(evaluation.get("ok", false)):
		return false
	return bool(evaluation.get("present", false)) \
		and int(evaluation.get("count", 0)) > 0


## The client-side reason a pop is not offered, or "" while it is. It is a
## **client-side** answer, deliberately distinct from every service code, and it
## is never sent: the service has no such code because it never refuses this
## case (see `POP_INERT_NO_OP`).
static func pop_refusal_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if offers_pop(evaluation):
		return ""
	return "no pop offered: " + POP_INERT_NO_OP


# ---------------------------------------------------------------------------
# The recorded speedup (design D6) — a verdict, never a price
# ---------------------------------------------------------------------------


## The recorded speedup contract's own display text for this row: the
## two-key precondition's verdict, or "" while the precondition is met.
##
## It never names a price, a remaining time, or a balance, because **no** cost
## is implemented and none may be (design D6). A met precondition reads as
## `recorded, not implemented`, which is the only honest answer a UI can give:
## the legacy branch's own author labelled its formula quite useless, and it
## charges nothing.
static func speedup_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var speedup: Dictionary = evaluation.get("speedup", {})
	if bool(speedup.get("ok", false)):
		return ("atom-fusion speedup: recorded, NOT implemented — the legacy "
			+ "branch needs ts and ui (both present here), reads "
			+ "sm_training_time off the QUEUED UNIT, charges nothing, and its "
			+ "own author called the formula quite useless")
	return ("atom-fusion speedup refused: %s (recorded; no cost is "
			% str(speedup.get("error", ""))
		+ "implemented, and the legacy branch would raise KeyError here)")


## The recorded speedup facts as the evidence report records them, read from
## `unit_queue.gd` so the report cannot describe a contract the code does not
## hold. Every value is the module's own constant.
static func speedup_record() -> Dictionary:
	return {
		"implemented": false,
		"command": "soulmixer_speedup",
		"source": "command.py:727-743",
		"contract": UnitQueue.SPEEDUP_CONTRACT,
		"precondition_keys": [UnitQueue.KEY_START, UnitQueue.KEY_UNIT_ID],
		"precondition_reason_missing_start": UnitQueue.REASON_MISSING_START,
		"precondition_reason_missing_unit_id":
			UnitQueue.REASON_MISSING_UNIT_ID,
		"duration_field": UnitQueue.SPEEDUP_FIELD,
		"duration_source": "the QUEUED unit, not the building: "
			+ "get_attribute_from_item_id(attr['ui'], 'sm_training_time')",
		"duration_reading": "seconds",
		"cost_divisor": UnitQueue.SPEEDUP_COST_DIVISOR,
		"cost_formula": UnitQueue.SPEEDUP_COST_FORMULA,
		"cost_implemented": UnitQueue.SPEEDUP_COST_IMPLEMENTED,
		"cost_note": UnitQueue.SPEEDUP_COST_NOTE,
		"field_coverage": UnitQueue.SPEEDUP_FIELD_COVERAGE,
		"start_instant_teardown": "the branch sets ts = 0, so a later refresh "
			+ "sees no timer; that write is NOT reproduced either, because the "
			+ "cost it reports is never charged",
		"legacy_verdict": "the committed source comment reads 'Quite useless "
			+ "cost calculation for understanding it'",
		"refusal_note": UnitQueue.REFUSAL_NOTE,
	}


## The three commands' recorded contract plus the recorded absence of
## validation, exactly as `unit_queue.gd` holds them.
static func command_record() -> Dictionary:
	return {
		"commands": UnitQueue.command_contract(),
		"keys": UnitQueue.queue_keys(),
		"attr_slot": UnitQueue.ATTR_SLOT,
		"teardown": UnitQueue.TEARDOWN,
		"no_validation": UnitQueue.NO_VALIDATION,
		"no_elapsed_time": UnitQueue.NO_ELAPSED_TIME,
		"inert_pop": POP_INERT_NO_OP,
		"non_readiness": (NON_READINESS as Array).duplicate(true),
	}


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


## The queue readout for the live evaluation: the row's presence, the committed
## count and start instant, the committed key names actually carried, the
## queued unit (resolved, unresolvable with its value intact, or absent), the
## recorded teardown, and the recorded speedup verdict.
##
## **No remaining time, no progress ratio, and no readiness appear**, and the
## readout says so outright rather than leaving a reader to wonder whether the
## omission is a defect: it names the absence as the recorded legacy contract.
## A row with no queue reads as `no queue`, never as `count 0`.
static func readout_text(evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	var parts: Array = []
	if not bool(evaluation.get("present", false)):
		parts.append("no queue (absent, not a count of zero)")
		parts.append("keys: none")
	else:
		var keys: Array = evaluation.get("keys", [])
		parts.append("queue: count %s, started at %s"
			% [_count_text(evaluation.get("count", null)),
				_number_text(evaluation.get("start_instant", null))])
		parts.append("keys: %s" % (", ".join(PackedStringArray(keys))
			if not keys.is_empty() else "none"))
	parts.append("queued unit: %s"
		% _queued_unit_text(evaluation))
	parts.append("no completion, no elapsed-time rule, no cost: the legacy "
		+ "server has none to reproduce")
	parts.append("teardown: a count of zero deletes nu, ts, and ui TOGETHER")
	var speedup := speedup_text(evaluation)
	if speedup != "":
		parts.append(speedup)
	var refusal := pop_refusal_text(evaluation)
	if refusal != "":
		parts.append(refusal)
	return " | ".join(parts)


## The armed surface's own confirm text for a queued mutation: it names the
## **target key** and says that nothing about the outcome is decided here — no
## cost, no duration, no readiness, no count — because the service derives the
## command and the recorded effect itself. It is deliberately free of every
## number a player might read as a price or a timer.
static func confirm_text(action: String, evaluation: Dictionary) -> String:
	if not bool(evaluation.get("ok", false)):
		return ""
	if str(action) == "push":
		return ("queue one unit on this row? the legacy push increments the "
			+ "count (1 when absent) and re-stamps the start instant, charges "
			+ "nothing, and no completion exists: the legacy server has no "
			+ "command that finishes a queue")
	return ("drop one queued unit from this row? the legacy pop decrements the "
		+ "count and, at zero, deletes nu, ts, and ui together, charges "
		+ "nothing, and no completion exists: the legacy server has no command "
		+ "that finishes a queue")


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural rejection: `ok` false, nothing offered, and every reported
## field left at its neutral value, so a caller can never read a half-built
## verdict.
static func _evaluation_reject(reason: String, message: String) -> Dictionary:
	return {
		"ok": false,
		"reason": reason,
		"error": message,
		"queue": null,
		"fields": {},
		"present": false,
		"count": null,
		"start_instant": null,
		"queued_unit_id": null,
		"queued_unit_resolution": UnitQueue.RESOLUTION_ABSENT,
		"queued_unit_name": null,
		"keys": [],
		"teardown": UnitQueue.TEARDOWN,
		"offers_push": false,
		"offers_pop": false,
		"speedup": {},
	}


## The committed count as the readout renders it, or `COUNT_ABSENT_TEXT` — a
## named absence, never a substituted zero.
static func _count_text(value: Variant) -> String:
	if value == null:
		return COUNT_ABSENT_TEXT
	return str(int(value))


## A committed number as the readout renders it, or "unknown" when this
## contract could not read it. Never a substituted zero.
static func _number_text(value: Variant) -> String:
	if value == null:
		return "unknown"
	return str(int(value))


## The queued unit as the readout renders it: the committed name when the id
## resolved, the id **with its recorded value intact** and an explicit
## unresolvable marker when it did not, and a named absence when the row carries
## no queued unit at all. A substitute is never rendered (design D7).
static func _queued_unit_text(evaluation: Dictionary) -> String:
	match str(evaluation.get("queued_unit_resolution", "")):
		UnitQueue.RESOLUTION_RESOLVED:
			return ("%s (queued unit id %s)"
				% [str(evaluation.get("queued_unit_name", "")),
					str(evaluation.get("queued_unit_id", ""))])
		UnitQueue.RESOLUTION_UNRESOLVABLE:
			return ("%s — queued unit id %s is unresolvable in the committed "
				% [UNIT_UNRESOLVABLE_TEXT,
					str(evaluation.get("queued_unit_id", ""))]
				+ "content and is reported verbatim, never substituted")
		_:
			return UNIT_NONE_TEXT
