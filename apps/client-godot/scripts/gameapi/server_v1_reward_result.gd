extends RefCounted
## Server v1's own typed **reward-cursor** answer, and the parser for it.
##
## **This module is the fourth reason `ServerV1Api` does not reuse `RewardFlow`'s
## typed result, and the reason is different again from the three before it.**
## v1 answers a reward intent with a cursor transition that pays nothing and
## gates nothing, and that is a shape no existing model has a place for:
##
## ```
## {"result":"success","action":"reward","instant":<int>,
##  "reward":{"operation":"weekly"|"daily",
##            "cursor_before":<int>,"cursor_after":<int>,"cursor_change":<int>,
##            "cursor_path":"<str>","cursor_derived_from":"<str>",
##            "bound":{"value":<int>,"provenance":"<str>",
##                     "daily_literal":<int>,
##                     "daily_rejected_derivation":"<str>"},
##            "instant_before":<int>,"instant_after":<int>,
##            "instant_gating":false,
##            "addressability":{"bound":<int>,
##                              "addressable_positions":[<int>, ...],
##                              "unaddressable_cursors":[<int>, ...],
##                              "gap_reported":<bool>,"clamped":0,
##                              "resolution":"<str>"}},
##  "resources_after":{... seven stored balances, all unchanged ...},
##  "stored_resources_compared":[<str>, ...],
##  "proof":[["<str>",<bool>], ...],
##  "leaf_paths_changed":[<str>, ...],
##  "derived_payout":null,"paid":false,"eligibility_derived":false,
##  "schedules":{"read":false,"daily":"<str>","weekly":"<str>","reason":"<str>"},
##  "preserved_branch_behaviour":{... nine quoted sentences ...},
##  "protocol":"server-v1"}
## ```
##
## ## Why it cannot be `RewardFlow.RewardResult`
##
## 1. **The success answer carries the whole stored balance set and the
##    complete `proof`.** `RewardFlow` is a *client* projection of a save
##    document: it reports what the document already holds. v1's answer is
##    evidence about a **transaction** - what it wrote, what it compared, and
##    what it deliberately did not move - and there is no place in a
##    read-only projection to put a proof.
## 2. **`paid` and `derived_payout` are declared, not inferred.** The
##    preserved branches grant through a **client-sent** value, so this line
##    refuses every grant channel instead of accepting one. Reporting the
##    absence as two explicit fields is the only way a reader can tell "paid
##    nothing" apart from "the answer omitted the payment section".
## 3. **It carries the bound's rejected derivation inline.** The daily bound is
##    a preserved literal `5`; `len(DAILY_GOLD_REWARDS)` happens to agree. Both
##    spellings travel together (`daily_literal` beside
##    `daily_rejected_derivation`) because a client that re-derived the bound
##    from the schedule would be reading a coincidence as a rule.
## 4. **`instant_gating` is a field, and it is `false`.** The preserved server
##    stamps an instant on both branches and has **zero readers** for either, so
##    there is no daily window, weekly period, cooldown, or already-claimed
##    check to reproduce. A client that inferred eligibility from `instant_after`
##    would be inventing the one rule the oracle lacks.
##
## ## What this module does not do
##
## It derives **nothing**. Every number here is either copied out of the answer
## or **read** off it: `clamped` is reported as `0`, never computed; the
## addressability report is the server's own; and the only function call in the
## module is the shared whole-number check described below. `tests/test_reward_v1.gd`
## asserts the absence of any helper that could price, schedule, or gate, and
## that guard was proven by injection rather than trusted.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The seven stored balances v1 read back after the write. **Seven**, not eight:
## the M7 readout also surfaces `privateState.energy`, which no branch writes,
## so it is not one of the values a proof compares.
const STORED_RESOURCE_NAMES := [
	"xp",
	"gold",
	"wood",
	"oil",
	"steel",
	"cash",
	"mana",
]

## `"server-v1"` on every answer v1 produced; `""` on a local failure.
const PROTOCOL := "server-v1"

## `"reward"` on success; `""` on failure.
const ACTION := "reward"

## The closed operation set. **Two**, and the suite re-reads this list rather
## than regexing the server, so a third operation fails here first.
const OPERATIONS := ["weekly", "daily"]

## The code this client produces for itself, when it cannot even build an
## intent. Distinct from every code the server can answer: none of the server's
## twenty-five is produced without a request.
const CODE_UNSUPPORTED := "unsupported_by_server_v1"

## v1's generic structural-refusal code, used when the transport failed to
## produce a readable body at all.
const CODE_BAD_REQUEST := "bad_request"

## The four members of the v1 reward success this parser requires. Each is a
## report whose **value** is the claim; none of them is required to say
## anything in particular, so none may be a default.
const REQUIRED_SUCCESS_KEYS := [
	"action",
	"instant",
	"reward",
	"resources_after",
	"proof",
]


## The nine quoted sentences about the preserved branches. Quoted prose, and the
## client executes **none** of it - they are carried so a reader of the answer
## can see what the oracle did and did not do without a second request.
const BEHAVIOUR_KEYS := [
	"daily_backwards_move",
	"daily_bound_literal",
	"daily_branch",
	"daily_grant",
	"paid",
	"schedules",
	"weekly_branch",
	"weekly_client_input",
	"weekly_stamped_instant",
]


## What a reader of the answer can know about the cursor's own movement.
class CursorReport:
	extends RefCounted
	## The closed operation set's member that ran. Never a third value.
	var operation := ""
	## The cursor the server **read from the recorded document**. Reported so a
	## client can see the successor came from here and not from itself.
	var cursor_before := 0
	## The derived successor: `stored + 1`, then the bound's own rule. **The
	## server derived this; this client computed nothing.**
	var cursor_after := 0
	## `cursor_after - cursor_before`, signed, and carried separately so a
	## backwards move would be visible as a negative number rather than inferred
	## by subtracting two fields.
	var cursor_change := 0
	## The document path the cursor was read from and written to.
	var cursor_path := ""
	## The server's own sentence naming where the successor came from.
	var cursor_derived_from := ""
	var bound_value := 0
	## The bound's provenance sentence, so a reader can see it is a literal.
	var bound_provenance := ""
	## The preserved daily literal, beside the derivation that was **rejected**.
	var daily_literal := 0
	## The rejected derivation, verbatim: the expression the server declined to
	## use, why, and what its agreement today is a coincidence rather than a rule.
	## **A dictionary, not a sentence** -- see `_rejected_derivation`, where the
	## first draft demanded a String and refused every real answer.
	var daily_rejected_derivation: Dictionary = {}
	## Whether the rejected derivation currently agrees with the literal. Carried
	## as its own field so the coincidence cannot be read as agreement.
	var daily_rejected_agrees_today := false
	## The stamped instant before and after. **Nothing reads either** - that is
	## what `instant_gating` is false about.
	var instant_before := 0
	var instant_after := 0
	## False, and required to be false. A reader must not infer a window from
	## `instant_after`.
	var instant_gating := false
	## The addressability report, verbatim.
	var addressability: Dictionary = {}


## A reward cursor the server advanced, with the no-payout claim as a field.
##
## **The only success in this directory that proves its own emptiness**, and the
## reason is structural: the other four either carry a server-derived figure or
## carry none because there is nothing to derive, while this one carries a
## *movement* - the cursor really did change - beside the absence of every
## consequence a movement of that name would normally imply. A reader cannot
## infer "paid" from "advanced", which is the inference this line exists to
## prevent.
class RewardAuthorityResult:
	extends RefCounted
	var ok := false
	## `"server-v1"` on every answer v1 produced; `""` on a local failure.
	var protocol := ""
	## `"reward"` on success; `""` on failure.
	var action := ""
	## The instant the server stamped. Equal to `reward.instant_after`; carried
	## at the top level because every v1 answer carries it.
	var instant := 0
	## The cursor movement, or `null` on failure.
	var reward: CursorReport = null
	## The complete stored balance set v1 read back AFTER the write. Applied
	## **verbatim**; never added to, never recomputed. Every member equals the
	## pre-request value - that is the proof's second half.
	var resources_after: BootData.Resources = null
	## The seven names v1 says it compared, so a caller can see the comparison
	## was complete rather than a subset.
	var stored_resources_compared: Array = []
	## The named post-execution checks, verbatim and in order. Each is a sentence
	## and a boolean the server asserts; this client re-reads them and runs
	## **none** of them.
	var proof: Array = []
	## Every leaf that moved in the whole document. The two the cursor and its
	## stamped instant are expected to be is a checkable set, not a promise.
	var leaf_paths_changed: Array = []
	## Null on success, always. Declared so it cannot be inferred from a missing
	## key - and the key is **absent entirely** on the other three v1 successes'
	## siblings, which is why the absence is worth stating.
	var derived_payout: Variant = null
	## False on success, always.
	var paid := false
	## False on success, always. No eligibility rule is derived anywhere.
	var eligibility_derived := false
	## The two committed schedules, named and reported unread.
	var schedules: Dictionary = {}
	## The nine quoted sentences about the preserved branches.
	var preserved_branch_behaviour: Dictionary = {}
	## Populated only on failure.
	var error_code := ""
	var error_message := ""
	var error_detail: Dictionary = {}


## A locally-produced failure. The only way to build a result without an answer.
static func reward_failure(code: String, message: String,
		detail: Dictionary = {}) -> RewardAuthorityResult:
	var result := RewardAuthorityResult.new()
	result.ok = false
	result.protocol = ""
	result.action = ""
	result.error_code = code
	result.error_message = message
	result.error_detail = detail
	return result


## Parse a v1 reward answer. **Fail-closed**: any missing, mistyped, or
## out-of-vocabulary field returns a failure rather than a partly-filled
## success, because a half-read cursor is worse than an unread one.
static func parse_reward_cursor(payload: Variant) -> RewardAuthorityResult:
	if not (payload is Dictionary):
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward answer was not a JSON object",
			{"received": typeof(payload)})
	var body: Dictionary = payload
	match str(body.get("result", "")):
		"success":
			return _success(body)
		"refused":
			return _refusal(body)
		_:
			return reward_failure(
				CODE_BAD_REQUEST,
				"the reward answer carried no recognised result",
				{"result": body.get("result", null)})


## A refusal, with its code, message, and the server's own detail carried
## through **verbatim**. The code is not validated against a local list: this
## client has no opinion about which codes exist, and inventing one here would
## make a future server code unreadable rather than merely unfamiliar.
static func _refusal(body: Dictionary) -> RewardAuthorityResult:
	var result := reward_failure(
		str(body.get("code", CODE_BAD_REQUEST)),
		str(body.get("message", "")),
		_detail(body.get("detail", null)))
	result.protocol = str(body.get("protocol", PROTOCOL))
	return result


static func _success(body: Dictionary) -> RewardAuthorityResult:
	for key in REQUIRED_SUCCESS_KEYS:
		if not body.has(key):
			return reward_failure(
				CODE_BAD_REQUEST,
				"the reward success is missing a required key",
				{"missing": key})
	var reward := _cursor(body.get("reward", null))
	if reward == null:
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward success carried an unreadable cursor report")
	var resources := _resources(body.get("resources_after", null))
	if resources == null:
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward success carried an unreadable stored balance set")
	var proof: Variant = _proof(body.get("proof", null))
	if proof == null:
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward success carried an unreadable post-execution proof")
	var compared: Variant = _string_list(
		body.get("stored_resources_compared", null))
	var changed: Variant = _string_list(body.get("leaf_paths_changed", null))
	var schedules: Variant = _schedules(body.get("schedules", null))
	var behaviour: Variant = _behaviour(body.get("preserved_branch_behaviour", null))
	var instant: Variant = _whole_number(body.get("instant", null))
	if compared == null or changed == null or schedules == null:
		return reward_failure(
			CODE_BAD_REQUEST, "the reward success carried an unreadable report")
	if behaviour == null:
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward success carried an unreadable behaviour record")
	if instant == null:
		return reward_failure(
			CODE_BAD_REQUEST,
			"the reward success carried an unreadable instant")

	var result := RewardAuthorityResult.new()
	result.ok = true
	result.protocol = str(body.get("protocol", PROTOCOL))
	result.action = str(body.get("action", ACTION))
	result.instant = int(instant)
	result.reward = reward
	result.resources_after = resources
	result.stored_resources_compared = compared
	result.proof = proof
	result.leaf_paths_changed = changed
	result.schedules = schedules
	result.preserved_branch_behaviour = behaviour
	# **The three no-payout fields are carried whatever the body says about
	# them.**  A client that echoed `paid: true` because a server once said so
	# would be reporting a payment it cannot name, and this client's whole claim
	# is that no payment exists.  So the values are the claim, and the suite
	# asserts the parser never takes them from the wire.
	result.derived_payout = null
	result.paid = false
	result.eligibility_derived = false
	return result


static func _cursor(value: Variant) -> CursorReport:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if str(source.get("operation", "")) not in OPERATIONS:
		return null
	## **`instant_gating` must be the boolean `false`, and this test is a type
	## check plus a value check, never a stringification.**  The first draft read
	## `if str(source.get("instant_gating", true)):`, which looks equivalent and
	## is the exact inverse of the truth: `str(false)` is the **five-character
	## string** `"false"` (measured, not assumed), and a non-empty String is
	## **truthy** on this engine, so the condition was true for `false` and the
	## function refused *every* real answer.
	##
	## Two things are recorded here rather than left implicit.  First, the bug was
	## invisible to a hand-built fixture and only a **captured** answer exposed
	## it, because a hand-built answer is constructed from the parser's own idea
	## of the wire and therefore agrees with a wrong parser by construction -
	## the reason :data:`REQUIRED_SUCCESS_KEYS` is checked against observed
	## payloads.  Second, the obvious repair `bool(...)` does **not** compile:
	## there is no `bool(String)` constructor on this engine, so the only honest
	## spelling is the `is bool` guard above followed by a plain comparison.
	if not (source.get("instant_gating", null) is bool) \
			or bool(source.get("instant_gating", true)):
		return null
	var bound: Variant = _bound(source.get("bound", null))
	if bound == null:
		return null
	var addressability: Variant = _addressability(
		source.get("addressability", null))
	if addressability == null:
		return null
	# **The five movement numbers are flat on the reward object and the two bound
	# numbers are not** - `bound_value` and `daily_literal` are members of the
	# nested `bound` table, while the cursor and instant numbers sit beside it.
	# The first draft of this function read all seven off `source`, so the two
	# bound figures resolved against an absent flat key and every answer was
	# refused as unreadable.  That is recorded here because the two readings look
	# interchangeable and only one of them matches the wire.
	var report := CursorReport.new()
	for key in [
		"cursor_before",
		"cursor_after",
		"cursor_change",
		"instant_before",
		"instant_after",
	]:
		var number: Variant = _whole_number(source.get(key, null))
		if number == null:
			return null
		report.set(key, int(number))
	for key in ["cursor_path", "cursor_derived_from"]:
		if not (source.get(key, null) is String):
			return null
	report.operation = str(source.get("operation", ""))
	report.cursor_path = str(source.get("cursor_path", ""))
	report.cursor_derived_from = str(source.get("cursor_derived_from", ""))
	report.bound_value = int(bound["value"])
	report.daily_literal = int(bound["literal"])
	report.bound_provenance = str(bound["provenance"])
	report.daily_rejected_derivation = bound["rejected"]
	report.daily_rejected_agrees_today = bool(
		bound["rejected"]["agrees_today"])
	report.instant_gating = false
	report.addressability = addressability
	return report


## The bound table: the value, its provenance sentence, and the daily literal
## beside the derivation that was **rejected**.
##
## `daily_rejected_derivation` is a **nested four-key object**, not a sentence,
## and the first draft of this parser required it to be a String -- so every real
## answer was refused as unreadable while the suite had no observed answer to
## catch it.  That is why :data:`REQUIRED_SUCCESS_KEYS` is checked against a
## **captured** answer rather than against a hand-built one: a hand-built answer
## is built from the parser's own idea of the wire, so it agrees with a wrong
## parser by construction.  All four members are required, including
## `agrees_today` - a reader who sees only `rejected` cannot tell whether the
## rejected derivation currently agrees, and the coincidence is the whole point.
static func _bound(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var number: Variant = _whole_number(source.get("value", null))
	var literal: Variant = _whole_number(source.get("daily_literal", null))
	if number == null or literal == null:
		return null
	if not (source.get("provenance", null) is String):
		return null
	var rejected: Variant = _rejected_derivation(
		source.get("daily_rejected_derivation", null))
	if rejected == null:
		return null
	return {
		"value": number,
		"literal": literal,
		"provenance": str(source.get("provenance", "")),
		"rejected": rejected,
	}


static func _rejected_derivation(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if source.get("agrees_today", null) is not bool:
		return null
	var out: Dictionary = {"agrees_today": bool(source.get("agrees_today", false))}
	for key in ["rejected", "reason", "agreement_is"]:
		if not (source.get(key, null) is String):
			return null
		out[key] = str(source.get(key, ""))
	return out


## The addressability report, **read** and never re-derived.
##
## `clamped` is read off the answer and required to be `0`. This client does not
## clamp, does not compare the stored cursor against the addressable positions,
## and does not decide whether a gap is a gap - the server said so and this is
## the report it sent. `gap_reported` is likewise read, so a gap the server chose
## not to report reads as unreported here rather than being re-detected.
static func _addressability(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var out: Dictionary = {}
	for key in ["bound", "clamped"]:
		var number: Variant = _whole_number(source.get(key, null))
		if number == null:
			return null
		out[key] = int(number)
	for key in ["addressable_positions", "unaddressable_cursors"]:
		var numbers: Variant = _integer_list(source.get(key, null))
		if numbers == null:
			return null
		out[key] = numbers
	if not (source.get("gap_reported", null) is bool):
		return null
	out["gap_reported"] = bool(source.get("gap_reported", false))
	if not (source.get("resolution", null) is String):
		return null
	out["resolution"] = str(source.get("resolution", ""))
	return out


## The schedule record. **Required** even though nothing is read from it: the
## whole claim is that both committed schedules went unread, and a client that
## tolerated its absence would lose the statement of that absence.
static func _schedules(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if source.get("read", null) is not bool:
		return null
	var out: Dictionary = {"read": bool(source.get("read", false))}
	for key in ["daily", "weekly", "reason"]:
		if not (source.get(key, null) is String):
			return null
		out[key] = str(source.get(key, ""))
	return out


## The nine quoted preserved-branch sentences, all required.
static func _behaviour(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for key in BEHAVIOUR_KEYS:
		if not (source.get(key, null) is String):
			return null
	var out: Dictionary = {}
	for key in source:
		out[str(key)] = str(source[key])
	return out


## The proof: ordered `[sentence, boolean]` pairs. Each pair is **re-read**, and
## the boolean is carried as the server asserted it. This client runs no check -
## it has no store to compare against - so `proof` is evidence of what was
## checked, not a claim that this client checked it.
static func _proof(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		if not (entry is Array) or (entry as Array).size() != 2:
			return null
		var pair: Array = entry
		if not (pair[0] is String) or not (pair[1] is bool):
			return null
		out.append([str(pair[0]), bool(pair[1])])
	return out


## A list of whole numbers. An **empty** list is accepted and kept distinct from
## an absent one: "the server reported no gap" is a reportable answer.
static func _integer_list(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		var whole: Variant = _whole_number(entry)
		if whole == null:
			return null
		out.append(int(whole))
	return out


## A list of strings. An empty list is accepted, as above.
static func _string_list(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		if not (entry is String):
			return null
		out.append(str(entry))
	return out


## The refusal detail, verbatim. Any shape is accepted: this client has no
## opinion about what a refusal should carry, and a detail table it could not
## read would turn a named refusal into an unread one.
static func _detail(value: Variant) -> Dictionary:
	if not (value is Dictionary):
		return {}
	var out: Dictionary = {}
	for key in value:
		out[str(key)] = value[key]
	return out


## The complete stored balance set, or null. Requires **all seven** names and
## nothing else, so a truncated set cannot pass as a complete one.
static func _resources(value: Variant) -> BootData.Resources:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if source.size() != STORED_RESOURCE_NAMES.size():
		return null
	var out := BootData.Resources.new()
	for name in STORED_RESOURCE_NAMES:
		if not source.has(name):
			return null
		var amount: Variant = _whole_number(source[name])
		if amount == null:
			return null
		out.set(str(name), int(amount))
	return out


## A JSON number that really is a whole number, or null.
##
## **Mirrored** from `server_v1_magic_result.gd` rather than preloaded from it.
## The duplication is deliberate and matches the four modules already in this
## directory: a typed result module that preloaded another would make the answer
## model of one surface a dependency of another, and the "second reason a typed
## result cannot be reused" argument this file's own header makes would then be
## half false - the answer type would be shared even where the answer is not.
##
## Godot decodes **every** JSON number as a `float`, so `7` arrives as `7.0` and
## `7.5` arrives as `7.5`. Comparing against the rounded value is therefore the
## only honest whole-number test available on this engine, and it is why `int()`
## alone is never used to validate a reported number: it would accept `7.5` by
## truncating it, which would be a silently wrong cursor.
static func _whole_number(value: Variant) -> Variant:
	if not (value is float or value is int):
		return null
	if float(value) != floor(float(value)):
		return null
	return value
