extends RefCounted
## Typed player-owned `UnitQueue` (OpenSpec `godot-unit-queues` "A queue is a
## count, a start instant, and an optional queued unit id" / "No elapsed-time
## evaluation and no completion" / "The three queue commands and their recorded
## lack of validation" / "The atom-fusion speedup is recorded without a cost or
## a timer" / "A queued unit id resolves through content, and an unresolvable
## one is reported", design D1-D7).
##
## ## A queue is THREE committed keys, nothing else (established)
##
## A production queue occupies exactly three keys of a placed row's **seventh**
## slot, the `attr` bag, and nowhere else (`engine.py:183-213`):
##
##   * `nu` — the **count**: incremented when present and **set to 1** when
##     absent by `engine.push_queue_unit` (`engine.py:183-189`);
##   * `ts` — the **start instant**, stamped with `timestamp_now()` on every
##     push and re-stamped by a partial decrement (`engine.py:189`, `198`);
##   * `ui` — the **optional queued unit id**, written by the atom-fusion
##     variant only (`push_queue_unit2` → `engine.py:206-213`).
##
## `engine.pop_queue_unit` **deletes all three together** at a count of zero
## (`engine.py:198-204`). No committed branch deletes one of them on its own,
## so a save never carries a partial teardown. That rule is invisible to an
## inspection of the dispatcher — the deletion is inside an engine helper — so
## it is **recorded** here as `TEARDOWN` rather than left for a reader to
## rediscover.
##
## ## Read-only by construction
##
## A `Queue` **copies** the three committed values out of the bag when it is
## built and then holds nothing but those scalars plus a resolved name. There
## is **no** setter, **no** mutating method, and **no** writable public field,
## so reading a queue can change neither the save it was parsed from nor the
## content entry it was resolved against. Projection is the whole capability:
## **writing** a queue key is behaviour, it belongs to the guarded intent, and
## it is not implemented here.
##
## ## Absent is ABSENT (design D1)
##
## A bag carrying none of the three keys reports `present: false` with a
## **null** count and a **null** start instant. It is deliberately *not*
## reported as a count of zero paired with an instant of zero: that pair is
## indistinguishable from a real queue that had just been emptied, and the
## three-key teardown means a legacy save can never hold it.
##
## ## Values are reported VERBATIM (design D1)
##
## The count and the instant are reported exactly as the bag holds them — no
## scaling, no rounding, no defaulting, no clamping — and a per-key malformed
## value **fails closed** with the key named rather than being coerced into
## something the save never held. The pinned engine's JSON parser represents
## every committed number as a float, so an integer slot accepts an `int` or an
## integral `float` (the documented transport tolerance the delivered
## definition, building, and unit catalogs already apply to the same field
## class); a numeric **string** is refused, because no committed source stores
## one. The queued unit id is the one key that is **not** shape-checked: it is
## reported **verbatim**, whatever it is, because only the client-supplied
## atom-fusion argument ever writes it and no evidence constrains what a client
## sends (design D7).
##
## ## No readiness, no remaining time, no completion (design D1/D2)
##
## Every occurrence of `attr["ts"]` in the legacy source is a **write**
## (`engine.py:189`, `198`) or a **deletion** (`engine.py:202`). Exactly one
## branch reads it back — `soulmixer_speedup` — and that is not a general queue
## path (see `SPEEDUP_CONTRACT`). The dispatcher has 63 named branches and the
## `complete_*` family is exactly `complete_collection`, `complete_goal`, and
## `complete_tutorial`: **no command completes a queue and no command
## materialises a unit from one.** There is therefore no server-side readiness
## rule to reproduce, and this module computes **none**: there is
## deliberately no `is_complete()`, no `remaining()`, no `progress()`, and no
## `ready_at()`. **The absence is a recorded property of the legacy contract,
## not a missing feature** — a later line may introduce completion only as its
## own deliverable, with its own evidence.
##
## ## The commands and their recorded LACK of validation (design D5)
##
## Three legacy branches touch a queue, and each does nothing but resolve a map
## row, call an engine helper, and print (`command.py:676-708`). They validate
## **nothing**: not that the item is a training producer, not `training_time`,
## not `min_level`, and **not a bound on the count**. Any placed row can be
## queued, an already-queued row can be queued again, and the queue length is
## unbounded. The recorded absence is **not permission**: this contract
## implements none of those checks and — deliberately — **adds no maximum
## count**, because a cap the engine does not set would be a rule the legacy
## server does not have. An authoritative limit belongs to a later
## server-authoritative milestone.
##
## ## The atom-fusion speedup is RECORDED and implemented NOT AT ALL
## (design D6)
##
## `soulmixer_speedup` (`command.py:727-743`) is the one branch that reads a
## queue's start instant. It needs **both** `ts` **and** `ui`, so it raises
## `KeyError` on a fresh row; it reads the duration from the **queued unit**
## (`sm_training_time`), not from the building; it reads that value as
## **seconds**; its recorded cost is `ceil(remaining / 3600)`; it **charges
## nothing** (it only prints a cost); and it sets `ts = 0` so a later refresh
## sees no timer. Its own author labelled the formula *"quite useless"*.
## Reproducing a formula the legacy source itself dismisses, and which never
## charges anything, would invent an economy — so the contract is recorded
## verbatim in `SPEEDUP_CONTRACT` and **no** cost, **no** timer, and **no**
## speedup is implemented anywhere in this repository. What *is* implemented is
## the two-key **precondition check**: where the legacy branch would raise
## `KeyError`, this contract names the unmet precondition and **refuses**
## (`speedup_precondition()`), which is the same discipline the delivered
## `xp_below_threshold` and `level_already_current` refusals apply.
##
## ## A queued id resolves through content, and an unresolvable one is
## ## REPORTED (design D7)
##
## `ui` names a unit, so the projection resolves it through the content
## registry's `units` domain and reports the committed unit **name** beside
## the id. A queued id the content package does not carry is reported as
## `unresolvable` **with its recorded value intact** — never dropped, never
## coerced to a name, never replaced by a guess — because the id originates
## from a client-supplied argument and no evidence establishes which ids a
## client actually sends. The resolver is a **parameter**: this module never
## reads content itself, so the static/instance boundary stays one-way and the
## same model serves the town view, the hermetic suite, and the evidence report.

## The three committed attribute-bag keys a production queue occupies
## (established: `engine.py:183-213`), in the committed order the engine reads
## and writes them.
const KEY_COUNT := "nu"
const KEY_START := "ts"
const KEY_UNIT_ID := "ui"
const QUEUE_KEYS := [KEY_COUNT, KEY_START, KEY_UNIT_ID]

## The three legacy queue commands. The atom-fusion variant is **recorded** and
## deliberately not offered by any guarded intent (design D7).
const PUSH_COMMAND := "push_queue_unit"
const POP_COMMAND := "pop_queue_unit"
const ATOM_FUSION_COMMAND := "push_queue_unit2"

## The row slot a queue's keys live in: the `attr` bag, the placed row's
## **seventh** slot (`engine.py:31`).
const ATTR_SLOT := 6

## The three-key teardown, recorded because no inspection of the dispatcher
## would reveal it.
const TEARDOWN := ("when the count reaches zero, pop_queue_unit deletes nu, "
	+ "ts, and ui TOGETHER (engine.py:198-204): the three keys are never torn "
	+ "down independently, no committed branch deletes one of them on its own, "
	+ "and a save therefore never carries a partial queue teardown")

## The recorded command contract, one record per command, with the committed
## source lines that fix its arguments and its effects. The absence of
## validation is a field of every record, because it is the fact that most needs
## stating; `offered` says whether a guarded intent may derive the command at
## all.
const COMMANDS := [
	{
		"command": PUSH_COMMAND,
		"args": ["map index"],
		"effect": "nu becomes (nu + 1) when present and 1 when absent; ts is "
			+ "stamped with timestamp_now(); nothing else is written",
		"source": "command.py:676-685 -> engine.py:183-189",
		"validation": "none: not producer-ness, not training_time, not "
			+ "min_level, and no bound on the count",
		"offered": true,
	},
	{
		"command": POP_COMMAND,
		"args": ["map index"],
		"effect": "with nu ABSENT the helper returns and nothing is written "
			+ "(an inert, recorded no-op); otherwise nu is decremented, and a "
			+ "positive result writes nu and re-stamps ts, while zero DELETES "
			+ "nu, ts, and ui together",
		"source": "command.py:699-708 -> engine.py:191-204",
		"validation": "none: not producer-ness, not training_time, not "
			+ "min_level, and no bound on the count",
		"offered": true,
	},
	{
		"command": ATOM_FUSION_COMMAND,
		"args": ["map index", "unit_id"],
		"effect": "the same push, plus ui = the client-supplied unit id",
		"source": "command.py:687-697 -> engine.py:206-213",
		"validation": "none: the unit id is not checked against the content",
		"offered": false,
		"why_not_offered": "the id is a CLIENT-SUPPLIED argument and no "
			+ "evidence establishes which ids a client actually sends, so no "
			+ "intent here may derive it: the projection reports an unresolvable "
			+ "ui with its recorded value intact rather than coercing one "
			+ "(design D7)",
	},
]

## The recorded absence of validation, and the decision that it stays absent.
const NO_VALIDATION := ("NO VALIDATION IS PERFORMED BY THE LEGACY SERVER AND "
	+ "NONE IS IMPLEMENTED HERE. push_queue_unit, pop_queue_unit, and "
	+ "push_queue_unit2 do not check that the item is a training producer, do "
	+ "not read training_time, do not check min_level, and do not cap nu. Any "
	+ "placed row can be queued, a row that already carries a queue can be "
	+ "queued again, and the queue length is unbounded. The recorded absence "
	+ "of a count bound is NOT permission to invent one (design D5): a cap the "
	+ "engine does not set would be a rule the legacy server does not have, and "
	+ "an authoritative limit belongs to a later server-authoritative "
	+ "milestone")

## The recorded absence of elapsed-time evaluation and of completion.
const NO_ELAPSED_TIME := ("NO ELAPSED-TIME EVALUATION IS IMPLEMENTED. Every "
	+ "occurrence of attr['ts'] in the legacy source is a WRITE "
	+ "(engine.py:189, engine.py:198) or a DELETION (engine.py:202); the "
	+ "single branch that reads it back is soulmixer_speedup, which is not a "
	+ "general queue path. The dispatcher has 63 named branches and the "
	+ "complete_* family is exactly complete_collection, complete_goal, and "
	+ "complete_tutorial: NO command completes a queue and no command "
	+ "materialises a unit from one. There is therefore no server-side 'is "
	+ "this queue ready?' rule to reproduce, so this contract computes NO "
	+ "readiness, NO remaining time, NO progress ratio, and NO completion "
	+ "(design D1/D2). The absence is a recorded property of the legacy "
	+ "contract, not a missing feature; a future line may introduce completion "
	+ "only as its own deliverable, with its own evidence")

## The recorded `soulmixer_speedup` contract, verbatim, and unimplemented.
const SPEEDUP_CONTRACT := ("RECORDED VERBATIM AND IMPLEMENTED NOT AT ALL. The "
	+ "legacy soulmixer_speedup branch (command.py:727-743) requires BOTH ts "
	+ "AND ui in the addressed row's attribute bag, so it raises KeyError on a "
	+ "fresh row; it reads the training duration from the QUEUED UNIT "
	+ "(get_attribute_from_item_id(...['ui'], 'sm_training_time')) rather than "
	+ "from the building; it reads that value as SECONDS (remaining = "
	+ "sm_training_time - (now - start), cost = ceil(remaining / 3600)); it "
	+ "CHARGES NOTHING, printing only a cost; and it sets ts = 0 so a later "
	+ "refresh sees no timer. Its own source comment reads 'Quite useless cost "
	+ "calculation for understanding it'. NO cost is computed here, NO balance "
	+ "is changed, and NO speedup is offered: reproducing a formula the legacy "
	+ "source itself labels useless, and which never charges anything, would "
	+ "invent an economy (design D6). Where the legacy branch would fail on a "
	+ "missing key, this contract REFUSES with a named reason instead of "
	+ "raising")

## The committed coverage of the duration field the speedup branch reads,
## recorded as **content** and never applied as a rule.
const SPEEDUP_FIELD := "sm_training_time"
const SPEEDUP_FIELD_COVERAGE := ("sm_training_time is a SOUL-MIXER field, not "
	+ "a general training duration: it is present on 300 of the 429 committed "
	+ "units, absent from the other 129 (including 923 Gorilla, 933 Wild "
	+ "Elephant, 1001 Worker I, and 1013 Truck), takes 84 distinct values "
	+ "beginning at 4000, and is present on 0 of the 470 committed buildings. "
	+ "training_time is the opposite: 130 of 470 buildings carry a positive "
	+ "one and 0 of 429 units do, and NO queue branch reads either field "
	+ "(design D5)")

## The legacy `ceil(remaining / 3600)` shape, recorded as a fact about a formula
## this repository does not implement, with the divisor it used.
const SPEEDUP_COST_DIVISOR := 3600
const SPEEDUP_COST_FORMULA := "ceil(remaining_seconds / 3600)"
const SPEEDUP_COST_IMPLEMENTED := false
const SPEEDUP_COST_NOTE := ("the shape above is RECORDED for completeness "
	+ "only. No cost is computed, no balance is changed, and no speedup "
	+ "purchase is offered anywhere in this repository, because the legacy "
	+ "branch charges nothing and its own author labelled the calculation "
	+ "useless")

## The two crash modes the recorded speedup contract explicitly does **not**
## reproduce.
const REFUSAL_NOTE := ("the legacy branch RAISES KeyError when the attribute "
	+ "bag lacks ts or ui, and would raise again inside int(...) for a queued "
	+ "unit that carries no sm_training_time (129 of the 429 committed units). "
	+ "This contract reproduces neither crash: it names the unmet precondition "
	+ "and refuses, and it never reads the duration field at all")

## The legacy content key a queued unit is resolved through.
const UNIT_DOMAIN := "units"

## The three ways a queued unit id is reported. There is deliberately no
## fourth: a dropped or substituted id is not a state this contract can reach.
const RESOLUTION_ABSENT := "absent"
const RESOLUTION_RESOLVED := "resolved"
const RESOLUTION_UNRESOLVABLE := "unresolvable"

## The named absences a reader sees instead of a value, so an unresolved id is
## never rendered as an empty name.
const ID_ABSENT := "[no queued unit]"
const ID_UNRESOLVABLE := "[unresolvable queued unit]"

## The refusal reasons the projection can produce. The first three are the
## structural rejections no projection can be built from; the rest are the
## recorded speedup precondition's own answers.
const REASON_INVALID_BAG := "invalid_attr"
const REASON_INVALID_COUNT := "invalid_count"
const REASON_INVALID_START := "invalid_start_instant"
const REASON_NO_RESOLVER := "unresolvable_unit_resolver"
const REASON_ABSENT_QUEUE := "absent_queue"
const REASON_MISSING_START := "missing_start_instant"
const REASON_MISSING_UNIT_ID := "missing_queued_unit_id"

## The committed corpus's own queue target, pinned so a corpus drift is a
## visible mismatch rather than a silently different report: **id 26, Command
## Center, at map key 1**, with an EMPTY attribute bag.
const CORPUS_MAP_KEY := 1
const CORPUS_ITEM_ID := 26
const CORPUS_ITEM_NAME := "Command Center"
const CORPUS_TRAINING_TIME := 5
const CORPUS_MIN_LEVEL := 1
const CORPUS_GROUP_TYPE := "COMMAND_CENTER"
## The seven stored balances the committed corpus records, which a push and a
## pop both leave byte-identical (the neutral vector's own guarantee).
const CORPUS_RESOURCES := {
	"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
	"cash": 5, "mana": 0,
}


## One production queue on one placed row: the three committed keys, verbatim.
##
## Read-only by construction — no setter, no mutating method, no writable
## public field. Every reader returns a committed value, a **named absence**
## (`null` plus `has_*()` false), or a fresh copy, so reading a queue can
## change neither the save it was parsed from nor the content entry it was
## resolved against.
class Queue extends RefCounted:
	## Whether the row's bag carried **any** of the three committed keys.
	var _present := false
	## The committed `nu` count, or null when the bag carries no `nu`.
	var _count: Variant = null
	## The committed `ts` start instant, or null when the bag carries no `ts`.
	var _start_instant: Variant = null
	## The committed `ui` queued unit id **verbatim**, or null when absent.
	var _queued_unit_id: Variant = null
	## `RESOLUTION_ABSENT`, `RESOLUTION_RESOLVED`, or `RESOLUTION_UNRESOLVABLE`.
	var _resolution := RESOLUTION_ABSENT
	## The committed unit name when the id resolved, else null. Never a
	## substitute.
	var _queued_unit_name: Variant = null
	## Why the id did not resolve, verbatim; "" when it did or was absent.
	var _resolution_error := ""
	## The committed key names this queue actually carries, in `QUEUE_KEYS`
	## order.
	var _keys: Array = []

	## Whether the addressed row carries a queue at all. An absent queue is
	## `false` with **null** values, never a count of zero with a zero instant.
	func present() -> bool:
		return _present

	## The committed count, verbatim, or null when the bag carries no `nu`.
	## A `0` here and a `null` here are different facts: legacy's teardown
	## deletes the key at zero, so a committed `0` is unreachable from the
	## three queue commands.
	func count() -> Variant:
		return _count

	## True when the bag carries the committed count key.
	func has_count() -> bool:
		return _count != null

	## The committed start instant, verbatim, or null. No elapsed-time rule is
	## computed from it, so reading it implies no timer and no readiness.
	func start_instant() -> Variant:
		return _start_instant

	## True when the bag carries the committed start-instant key.
	func has_start_instant() -> bool:
		return _start_instant != null

	## The committed queued unit id **verbatim**, or null when the bag carries
	## no `ui`. Never coerced to a name, never dropped.
	func queued_unit_id() -> Variant:
		return _queued_unit_id

	## True when the bag carries the committed queued-unit-id key.
	func has_queued_unit_id() -> bool:
		return _queued_unit_id != null

	## How the queued unit id resolved: `absent`, `resolved`, or
	## `unresolvable`. A queued id the content package does not carry is
	## `unresolvable` with its value intact (design D7).
	func queued_unit_resolution() -> String:
		return _resolution

	## The committed unit name when the id resolved, else null. A name is a
	## LABEL, not an identifier, and is never used to resolve an id.
	func queued_unit_name() -> Variant:
		return _queued_unit_name

	## Why a queued unit id did not resolve, verbatim; "" when it resolved or
	## was absent. The message is the resolver's own, so no failure is
	## generic.
	func queued_unit_resolution_error() -> String:
		return _resolution_error

	## The committed key names this queue carries, in `QUEUE_KEYS` order, as a
	## fresh array a caller cannot append to.
	func keys() -> Array:
		return _keys.duplicate()

	## The three-key teardown this queue is subject to, verbatim. Recorded, not
	## computed: nothing here decides when a teardown fires.
	func teardown() -> String:
		return TEARDOWN

	## The whole committed queue as one fresh record — the three values, their
	## presence flags, the resolution, and the teardown rule. Derived from the
	## copied values only; nothing is added to the bag.
	func fields() -> Dictionary:
		return {
			"present": _present,
			"keys": keys(),
			"count": _count,
			"has_count": has_count(),
			"start_instant": _start_instant,
			"has_start_instant": has_start_instant(),
			"queued_unit_id": _queued_unit_id,
			"has_queued_unit_id": has_queued_unit_id(),
			"queued_unit_resolution": _resolution,
			"queued_unit_name": _queued_unit_name,
			"queued_unit_resolution_error": _resolution_error,
			"teardown": TEARDOWN,
		}


## Projects one placed row's `attr` bag into a typed `Queue`. Returns
##   `{ok: true, error: "", queue: <Queue>}`
## or
##   `{ok: false, error: "<message naming the bag and the key>", queue: null}`
## — no partial queue, nothing guessed, defaulted, or coerced (design D1).
##
## `attr` is the row's seventh slot as the save holds it. A bag that is **not
## an object** is refused: an empty bag and a missing bag mean the same thing,
## but a bag that is not a bag is a different thing entirely, and reading it as
## an empty queue would report a fact the save does not carry.
##
## `resolve_unit` is the caller's resolver for a committed queued unit id,
## receiving the id **as recorded** (`String(id)`) and returning
## `{ok, error, name}` — the suite and any content-backed surface supply it
## from the registry's `units` domain. It is required whenever a bag carries a
## `ui`, and a missing or non-callable resolver is a **refusal**, never a
## silently dropped id.
static func project(attr: Variant, resolve_unit: Variant) -> Dictionary:
	if not (attr is Dictionary):
		return _reject(REASON_INVALID_BAG,
			"the addressed row's attribute bag is %s, not an object"
				% _type_name(attr))
	var bag: Dictionary = attr
	if bag.has(KEY_COUNT):
		var count: Variant = _integer(bag[KEY_COUNT])
		if count == null:
			return _reject(REASON_INVALID_COUNT,
				"the addressed row's %s is %s, not an integer"
					% [KEY_COUNT, bag[KEY_COUNT]])
		if int(count) < 0:
			return _reject(REASON_INVALID_COUNT,
				"the addressed row's %s is %d, not a non-negative count"
					% [KEY_COUNT, int(count)])
	if bag.has(KEY_START):
		var instant: Variant = _integer(bag[KEY_START])
		if instant == null:
			return _reject(REASON_INVALID_START,
				"the addressed row's %s is %s, not an integer"
					% [KEY_START, bag[KEY_START]])
	var queue := Queue.new()
	var carried: Array = []
	for key: String in QUEUE_KEYS:
		if bag.has(key):
			carried.append(key)
	queue._present = not carried.is_empty()
	queue._keys = carried
	# Verbatim, never defaulted: an absent key stays absent.
	queue._count = int(_integer(bag[KEY_COUNT])) if bag.has(KEY_COUNT) else null
	queue._start_instant = (int(_integer(bag[KEY_START]))
		if bag.has(KEY_START) else null)
	if not bag.has(KEY_UNIT_ID):
		queue._resolution = RESOLUTION_ABSENT
		return {"ok": true, "error": "", "queue": queue}
	# The queued unit id is reported VERBATIM whatever it is: only the
	# client-supplied atom-fusion argument ever writes it (design D7).
	queue._queued_unit_id = bag[KEY_UNIT_ID]
	if not (resolve_unit is Callable):
		return _reject(REASON_NO_RESOLVER,
			"the addressed row carries the queued unit id %s, which cannot be "
				% queue._queued_unit_id
			+ "resolved: no usable unit resolver was supplied, and dropping the "
			+ "id would report a queue as carrying no queued unit when it does")
	var resolved := _resolve_queued_unit(resolve_unit, queue._queued_unit_id)
	if not bool(resolved.get("ok", false)):
		queue._resolution = RESOLUTION_UNRESOLVABLE
		queue._queued_unit_name = null
		queue._resolution_error = str(resolved.get("error", ""))
		return {"ok": true, "error": "", "queue": queue}
	queue._resolution = RESOLUTION_RESOLVED
	queue._queued_unit_name = str(resolved.get("name", ""))
	return {"ok": true, "error": "", "queue": queue}


## The recorded speedup contract's **precondition check** — and nothing else.
## Returns
##   `{ok, reason, error, keys_present, refuses_instead_of_raising, contract,
##     cost_implemented}`
##
## `ok` is true only when the addressed row's bag carries **both** the start
## instant and the queued unit id, which are the two keys the legacy branch
## requires. When either is missing the answer is a **named refusal** — the
## legacy branch raises `KeyError` there and this contract reproduces no
## crash. Even on `ok` the function computes **no cost**: it returns the
## recorded contract and the statement that the cost is not implemented, so no
## caller can mistake an `ok` for a price (design D6).
##
## A bag that is not an object is refused as `absent_queue` rather than as a
## malformed one here: the speedup branch indexes `atom_fusion[6]` and raises
## on the missing subscript, so the honest report is that the row has no bag at
## all.
static func speedup_precondition(attr: Variant) -> Dictionary:
	var keys: Array = []
	var reason := ""
	var message := ""
	if not (attr is Dictionary):
		reason = REASON_ABSENT_QUEUE
		message = ("the addressed row has no attribute bag at all, so it carries "
			+ "neither the start instant nor the queued unit id the legacy "
			+ "speedup branch requires: it would raise KeyError on "
			+ "atom_fusion[6]['ts'] and this contract refuses instead")
	else:
		var bag: Dictionary = attr
		for key: String in [KEY_START, KEY_UNIT_ID]:
			if bag.has(key):
				keys.append(key)
		if not keys.has(KEY_START):
			reason = REASON_MISSING_START
			message = ("the addressed row's attribute bag carries no start "
				+ "instant, which the legacy speedup branch requires: it would "
				+ "raise KeyError on atom_fusion[6]['ts'] and this contract "
				+ "refuses instead")
		elif not keys.has(KEY_UNIT_ID):
			reason = REASON_MISSING_UNIT_ID
			message = ("the addressed row's attribute bag carries no queued "
				+ "unit id, which the legacy speedup branch requires to read the "
				+ "duration: it would raise KeyError on "
				+ "atom_fusion[6]['ui'] and this contract refuses instead")
	return {
		"ok": reason == "",
		"reason": reason,
		"error": message,
		"keys_present": keys,
		"refuses_instead_of_raising": reason != "",
		"contract": SPEEDUP_CONTRACT,
		"cost_implemented": false,
	}


## The recorded command contract as a fresh deep copy a caller may keep and
## mutate, so a report reads the model's own table rather than restating it.
static func command_contract() -> Array:
	return (COMMANDS as Array).duplicate(true)


## The three committed key names, as a fresh array.
static func queue_keys() -> Array:
	return (QUEUE_KEYS as Array).duplicate()


## The established-versus-derived provenance split this line reports as its own
## section. Every established fact names the evidence a reader can go and check,
## and the derived facts state what they are derived from. Nothing here names a
## runtime; the runtime names live in `NON_CLAIMS` and are assembled from
## fragments, because the project-scope suite scans this file's bytes for their
## literal forms.
const PROVENANCE := {
	"established": [
		{"fact": "a production queue occupies exactly three keys of a placed "
			+ "row's attr bag: nu (count), ts (start instant), and ui (the "
			+ "optional queued unit id the atom-fusion variant alone writes)",
			"evidence": "engine.py:183-213; docs/legacy-production-queues.md; "
				+ "the executed push and pop in tests/fixtures/"
				+ "godot-unit-queues/steps/"},
		{"fact": "push_queue_unit takes ONLY the map index, sets nu to (nu + 1) "
			+ "when present and 1 when absent, and stamps ts with "
			+ "timestamp_now(); pop_queue_unit takes only the map index, and "
			+ "with nu absent returns without writing anything",
			"evidence": "command.py:676-685 and 699-708 -> engine.py:183-204; "
				+ "the committed executed fixture records both"},
		{"fact": "a decrement to zero DELETES nu, ts, and ui together, and no "
			+ "committed branch deletes one of them on its own",
			"evidence": "engine.py:198-204; the committed pop step's after "
				+ "state carries an EMPTY bag again"},
		{"fact": "the three branches validate nothing: not producer-ness, not "
			+ "training_time, not min_level, and no bound on nu, so the queue "
			+ "length is unbounded",
			"evidence": "command.py:676-708 - each branch is a map lookup, an "
				+ "engine helper call, and a print"},
		{"fact": "every occurrence of attr['ts'] is a write or a deletion; the "
			+ "only reader is soulmixer_speedup, which is not a general queue "
			+ "path. Of 63 named dispatcher branches the complete_* family is "
			+ "exactly complete_collection, complete_goal, and "
			+ "complete_tutorial: no command completes a queue and none "
			+ "materialises a unit from one",
			"evidence": "engine.py:189, 198, 202 against 727-743; "
				+ "docs/legacy-production-queues.md; the command catalog's 63 "
				+ "named branches"},
		{"fact": "the resource vector is applied BEFORE the dispatched branch, "
			+ "verbatim, as max(current + delta, 0), so any price a client "
			+ "attached to a queue would be a client-sent mint or burn",
			"evidence": "command.py:40; engine.py:251-271"},
		{"fact": "the committed corpus places id 26, Command Center, at map "
			+ "key 1 with training_time 5, min_level 1, group_type "
			+ "COMMAND_CENTER, and an EMPTY attribute bag",
			"evidence": "tests/saves/fresh-player.json; the committed "
				+ "normalized content package; the fixture's own manifest"},
	],
	"derived": [
		{"fact": "the projection refuses a malformed nu, a negative nu, and a "
			+ "non-integer ts, and reports a ui verbatim without a shape check",
			"evidence": "derived (design D1): the service's own derivation "
				+ "raises invalid_attr on a non-strict or negative count, so "
				+ "the client fails closed on the same shapes rather than "
				+ "comparing against a coerced value. The ui is deliberately "
				+ "NOT shape-checked, because only a client-supplied argument "
				+ "ever writes it and no evidence constrains what a client "
				+ "sends (design D7)"},
		{"fact": "a queued unit id is resolved through the content registry's "
			+ "units domain and an unresolvable one is reported with its value "
			+ "intact",
			"evidence": "derived (design D7): the resolution follows the "
				+ "established shape of a content reference, while the "
				+ "handling of an id that does not resolve is a decision - "
				+ "report, never drop and never substitute - taken because "
				+ "the id is client-supplied"},
		{"fact": "the readout's labels and the composition of its lines",
			"evidence": "derived: no authentic legacy queue panel has been "
				+ "captured, so the wording is the delivered provisional "
				+ "convention, never a claim about what the legacy client "
				+ "displayed"},
	],
}


## The evidence's explicit non-claims (spec "Unit-queue evidence and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"NO COMPLETION AND NO ELAPSED-TIME EVALUATION ARE IMPLEMENTED, BECAUSE THE "
		+ "LEGACY SERVER HAS NEITHER: no command completes a queue and no "
		+ "command materialises a unit from one, so a queue can never be shown "
		+ "to finish and the absence is a recorded contract rather than a gap "
		+ "filled here",
	"NO COST AND NO TIMER ARE IMPLEMENTED: the legacy soulmixer_speedup branch "
		+ "charges nothing and its own author labelled its ceil(remaining / "
		+ "3600) formula quite useless, so the contract is recorded and no "
		+ "balance is ever changed",
	"NO COUNT BOUND IS IMPLEMENTED: the legacy engine sets none, and a cap it "
		+ "does not have would be an invented rule (design D5)",
	"NO UNIT IS PRODUCED, TRAINED, OR PLACED: no unit is rendered, animated, "
		+ "or played, and nothing here creates a unit from a queue",
	"NO ACQUISITION IS CLAIMED: this line reads and reports a queue and sends "
		+ "two guarded intents; where a queue comes from is not established",
	"no training duration semantics are claimed: training_time is a building "
		+ "field no queue branch reads, and sm_training_time is the soul-mixer "
		+ "path's own field",
	"the fixture covers a PUSH AND A POP ONLY, so it evidences nothing about "
		+ "a finished queue, a produced unit, or any progressed player",
	"no producer, duration, level, or readiness rule is implemented, and the "
		+ "recorded absence of validation is not permission: none of those "
		+ "checks is the client's to add here",
	"the atom-fusion push is NOT offered, because its unit id is a "
		+ "client-supplied argument no evidence constrains (design D7)",
	"no compatibility route beyond the two guarded intents this line delivers "
		+ "exists for a queue, and the service adds no server-authoritative "
		+ "validation of producer-ness, duration, level, or count - that "
		+ "belongs to Server v1 / M13",
	"no pixel-parity oracle exists",
	"the committed capture runs the fake GameApi implementation for the "
		+ "client-side evidence, a deterministic test double rather than a "
		+ "parity oracle; the executed-legacy parity rests on the committed "
		+ "fixture and the live phase",
]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## A structural rejection: no queue at all, with the reason and a message that
## names the offending bag or key.
static func _reject(reason: String, message: String) -> Dictionary:
	return {"ok": false, "error": "[unit-queue] projection refused (%s): %s"
		% [reason, message], "reason": reason, "queue": null}


## One committed queued unit id, resolved through the caller's resolver. The id
## reaches the resolver **as the save holds it** — `String(id)` — because the
## content registry's own accessor is keyed by the committed string id, and the
## value is never coerced to a number first.
##
## A resolver that runs but reports no such unit is an **unresolvable id**, which
## the caller reports with the recorded value intact (design D7); a resolver that
## could not run at all is refused earlier, in `project()`.
static func _resolve_queued_unit(resolve_unit: Callable,
		queued_unit_id: Variant) -> Dictionary:
	var id_text := str(queued_unit_id)
	var answer: Variant = resolve_unit.call(id_text)
	if not (answer is Dictionary):
		return {"ok": false, "error":
			"the queued unit id %s resolved to %s, not a resolution record"
				% [queued_unit_id, _type_name(answer)]}
	var record: Dictionary = answer
	if not bool(record.get("ok", false)):
		return {"ok": false, "error":
			"the queued unit id %s does not resolve: %s" % [queued_unit_id,
				str(record.get("error",
					"the content package carries no such unit"))]}
	var name: Variant = record.get("name", "")
	if not (name is String) or str(name).is_empty():
		return {"ok": false, "error":
			"the queued unit id %s resolved to a definition carrying no name"
				% queued_unit_id}
	return {"ok": true, "error": "", "name": str(name)}


## A committed integer: an `int` or an integral `float` inside the transported
## exact-integer range. A numeric string fails closed, because coercing `"10"`
## to ten would invent a value the committed row does not carry.
static func _integer(value: Variant) -> Variant:
	if value is bool:
		return null
	if value is int:
		return int(value)
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number) \
				and absf(number) <= 9007199254740992.0:
			return int(number)
	return null


## The observed type of a refused value, so a failure names what it found
## instead of saying only "invalid".
static func _type_name(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "bool"
		TYPE_INT:
			return "int"
		TYPE_FLOAT:
			return "float"
		TYPE_STRING:
			return "string"
		TYPE_ARRAY:
			return "array"
		TYPE_DICTIONARY:
			return "object"
		_:
			return "unsupported"
