extends RefCounted
## Server v1's own typed **magic-counter** answer, and the parser for it.
##
## **This module is the third reason `ServerV1Api` does not reuse `MagicFlow`'s
## typed result, and the reason is different again from the two before it.**
## v1 answers a magic intent with a **counter transition that charges nothing**,
## and that is a shape no existing model has a place for:
##
## ```
## {"result":"success","action":"magic","instant":<int>,
##  "magic":{"requested_id":<int>,"resolved_id":<int>,"operation":"buy"|"use",
##           "ledger_key":"<str>","transition_id":"<hex>"},
##  "counter":{"before":<int>,"after":<int>,"had_recorded_entry":<bool>,
##             "cap":<int>,"at_cap":<bool>,"cap_is":"<str>"},
##  "committed":{... the committed row, verbatim, plus two level booleans ...},
##  "resources_after":{... seven stored balances, all unchanged ...},
##  "stored_resources_compared":[<str>, ...],
##  "counter_after":<int>,"ledger_after":[<str>, ...],
##  "same_transition_for_both_operations":true,
##  "divergences":[<str>, ...],
##  "preserved_branch_behaviour":{"buy":"<str>","use":"<str>",
##                                "absent_key":"<str>","same_number":"<str>"},
##  "price_charged":null,
##  "protocol":"server-v1"}
## ```
##
## ## Why it cannot be `MagicFlow.MagicResult`
##
## 1. **There is no amount anywhere.** v0's magic answer reports a client-model
##    transaction whose counter movement is a client-side projection; v1's carries
##    `price_charged: null` and **no `derived_deltas` key at all** - not an empty
##    one. An empty mapping invites a reader to treat the absence as a formatting
##    accident, and the absence *is* the finding (design D2), so it is carried as
##    an explicit null plus the two booleans the committed row reports.
## 2. **It carries the cap's provenance inline** (`counter.cap_is`), because the
##    bound is a recorded literal rather than a derived figure, and a reader of
##    the answer must be able to see that without opening the server.
## 3. **It carries the divergence *reasons*** (`divergences`, a list of names)
##    rather than a recomputed legacy value. v0 reports `recorded_after`,
##    `legacy_expected_after` and `matches_derived` because v0 *executes* the
##    legacy branch and can state what it wrote; v1 does not execute it and can
##    only state the conditions under which its own value is known to differ. A
##    client cannot compare those two shapes, and a parser that pretended to
##    would be inventing a rule.
##
## ## Everything here is reported verbatim
##
## This module computes no price, no charge, no cap, no counter, and no
## divergence. It does not check that `counter.after` equals `counter_after`, and
## it does not check that `resources_after` is unchanged against anything - those
## are the *server's* post-condition proof, and re-doing them here would be a
## second implementation of a rule the server already owns. What it does do is
## refuse every malformed shape, which is the one thing a transport must do.
##
## **The only arithmetic-shaped expression in this file** is the whole-number test
## in `_whole_number()`, and it exists because Godot decodes every JSON number as a
## `float`: `7` arrives as `7.0`, and `int()` alone would silently truncate a
## `7.5`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The closed set of stored balance names `resources_after` must carry, exactly
## and completely. The same seven v1 reports and `BootData.Resources` models; this
## is a client-side view of stored balances, not protocol vocabulary.
##
## **Seven, not eight.** The legacy eight-slot mutation vector's eighth target is
## read into `unknown` and never written, so `privateState.energy` is not a v1
## stored resource and a parser that accepted eight would be modelling a slot the
## server does not hold.
const STORED_RESOURCE_NAMES := [
	"xp", "gold", "wood", "oil", "steel", "cash", "mana",
]

## The protocol string v1 stamps on every answer.
const PROTOCOL := "server-v1"

## The only action this delivered v1 route performs.
const ACTION := "magic"

## The closed operation vocabulary, verbatim from v1's `operation` field. This is
## a *client-side mirror* of the server's table, not a second source: the parser
## refuses any other value rather than reading it, so a widened server vocabulary
## is reportable instead of silently accepted.
const OPERATIONS := ["buy", "use"]

## Client-LOCAL codes. **These are not v1 refusal codes**: they never reach the
## server, so they cannot be in `server_v1_refusals.REFUSAL_HTTP_STATUS`.
## `unsupported` means "v1 has no such route"; `bad_request` means "v1 answered
## something this parser refuses to guess at". Every code v1 itself refuses
## travels through `error_code` **verbatim**, in the same field, so a caller
## reads one field whatever refused the request.
const CODE_UNSUPPORTED := "unsupported_by_server_v1"
const CODE_BAD_REQUEST := "bad_request"

## The committed magic fields v1 reports verbatim inside `committed`. This is a
## **reporting** list, not a price list: no member of it is used by this parser to
## produce a value, and the absence of `derived_deltas` from the answer is what
## makes that structural rather than a promise.
const REPORTED_COMMITTED_FIELDS := [
	"id", "name", "gold", "cash", "mana", "level", "target", "area", "kind",
]


## v1's **addressing decision** for one counter transition, exactly as it reports
## it.
##
## `requested_id` is what the client sent; `resolved_id` is the committed magic
## the server read it as. They are **always equal**, because v1 refuses an id that
## names no committed row rather than resolving it to one, and both are carried
## separately so that fact is visible in the answer rather than assumed by the
## caller.
class MagicIdentity:
	extends RefCounted
	var requested_id := -1
	var resolved_id := -1
	## `"buy"` or `"use"`. The **same** transition for both (design D7).
	var operation := ""
	var ledger_key := ""
	var transition_id := ""


## v1's typed answer to one magic intent.
##
## On success `ok` is true and every field below is populated from the response;
## on refusal `ok` is false, `error_code` carries v1's own code verbatim, and
## **every other field stays at its default** - there is no partial payload.
class MagicCounterResult:
	extends RefCounted
	var ok := false
	## `"server-v1"` on every answer v1 produced; "" on a local failure.
	var protocol := ""
	## `"magic"` on success; "" on failure. The action the server says ran, so a
	## caller cannot read a counter answer as some other action's.
	var action := ""
	## The instant the server recorded for the transaction. **The preserved
	## branches record no instant at all**, so nothing in the store holds it.
	var instant := 0
	## The addressing decision, or null on failure.
	var magic: MagicIdentity = null
	var counter_before := 0
	var counter_after := 0
	## False when the addressed ledger key was **absent**, which is one of the two
	## recorded conditions under which v1's value is known to differ from the
	## preserved branch's.
	var had_recorded_entry := false
	## The recorded literal bound. Not a derived figure.
	var cap := 0
	## True when the transition stopped at the cap instead of rising - which at
	## `before == cap` means the recorded **no-op**, not a decrease.
	var at_cap := false
	## The cap's provenance sentence, reported so a reader of the answer can see
	## the bound is a literal.
	var cap_is := ""
	## The committed row **verbatim**, never a value computed from it. Read-only
	## evidence; this client prices nothing from it.
	var committed: Dictionary = {}
	## The complete stored balance set v1 read back AFTER the write. Applied
	## **verbatim**; never added to, never recomputed.
	var resources_after: BootData.Resources = null
	## The seven names v1 says it compared. Carried so a caller can see the
	## comparison was complete rather than a subset.
	var stored_resources_compared: Array = []
	## The ledger's own keys after the write, in stored order.
	var ledger_after: Array = []
	## Always true on a v1 answer. Design D7: both operations derive **one**
	## transition, and that is a finding rather than an oversight.
	var same_transition_for_both_operations := false
	## **Names** of the conditions under which v1's value is known to differ from
	## the preserved branch's - not a recomputed legacy value. Empty means the two
	## are known to agree here.
	var divergences: Array = []
	## The recorded behaviour of the two preserved branches, quoted. The client
	## executes none of it and derives nothing from it.
	var preserved_branch_behaviour: Dictionary = {}
	## **Always `null` on a v1 answer, and that null is the finding.** There is no
	## price field to read because none was derived (design D2). A float here would
	## mean the parser guessed, which it never does.
	var price_charged: Variant = null
	var error_code := ""
	var error_message := ""
	## v1's structured refusal `detail` object, verbatim; empty on success.
	var error_detail: Dictionary = {}


## Structured failure, never a partial payload.
static func magic_failure(code: String, message: String,
		detail: Dictionary = {}) -> MagicCounterResult:
	var result := MagicCounterResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	result.error_detail = detail.duplicate()
	return result


## Builds the typed result from v1's payload, failing CLOSED on every malformed
## shape. A refused answer keeps v1's own code, message and detail; a success is
## only built when **every** documented field is present and well-typed.
static func parse_magic_counter(payload: Variant) -> MagicCounterResult:
	if not (payload is Dictionary):
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer is not a JSON object")
	var body: Dictionary = payload
	var kind := str(body.get("result", ""))
	if kind == "refused":
		return _refusal(body)
	if kind != "success":
		# `%s`, never `%r`: this engine has no `%r` format character and reports
		# it as an engine ERROR line even though the statement completes, which
		# would fail `verify-boot.ps1` on a suite that reported itself green.
		var seen := "<absent>" if not body.has("result") else str(body["result"])
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no recognised result field: %s" % seen)
	return _success(body)


## A v1 refusal, verbatim. No field is derived from it and none is defaulted.
static func _refusal(body: Dictionary) -> MagicCounterResult:
	var code := str(body.get("code", ""))
	if code == "":
		return magic_failure(CODE_BAD_REQUEST, "a refused v1 answer carries no code")
	var detail: Variant = body.get("detail", {})
	if not (detail is Dictionary):
		return magic_failure(CODE_BAD_REQUEST, "the v1 refusal detail is not an object")
	var result := magic_failure(code, str(body.get("message", "")), detail)
	result.protocol = str(body.get("protocol", ""))
	return result


## A v1 success, or a closed refusal. Nothing is defaulted.
static func _success(body: Dictionary) -> MagicCounterResult:
	if str(body.get("protocol", "")) != PROTOCOL:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer is not stamped %s" % PROTOCOL)
	if str(body.get("action", "")) != ACTION:
		return magic_failure(CODE_BAD_REQUEST, "the v1 magic answer reports action %s"
			% str(body.get("action", "")))
	var instant: Variant = _whole_number(body.get("instant", null))
	if instant == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no whole-number instant")
	var identity: MagicIdentity = _identity(body.get("magic", null))
	if identity == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no usable magic block")
	var counter: Variant = _counter(body.get("counter", null))
	if counter == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no usable counter block")
	var committed: Variant = _committed(body.get("committed", null))
	if committed == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no complete committed report")
	var balances: BootData.Resources = _resources(body.get("resources_after", null))
	if balances == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no complete stored balance set")
	var compared: Variant = _string_list(body.get("stored_resources_compared", null))
	if compared == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no stored-resource comparison list")
	# The list is what makes the "no stored resource moved" half of v1's proof
	# checkable, so it must name **exactly** the seven stored balances. A list
	# naming an eighth is not a longer answer: it is a claim about a balance
	# this client cannot read, which is the same refusal `_resources` makes.
	if (compared as Array).size() != STORED_RESOURCE_NAMES.size():
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer compares a set that is not the seven stored"
			+ " balances")
	for name in STORED_RESOURCE_NAMES:
		if not (compared as Array).has(str(name)):
			return magic_failure(CODE_BAD_REQUEST,
				"the v1 magic answer compares a set that is not the seven"
				+ " stored balances")
	var counter_after: Variant = _whole_number(body.get("counter_after", null))
	if counter_after == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no whole-number counter_after")
	var ledger: Variant = _string_list(body.get("ledger_after", null))
	if ledger == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no whole-string ledger")
	# `same_transition_for_both_operations` is asserted to be **true**, not merely
	# present. It is design D7's own claim, and a v1 answer reporting `false`
	# would mean the two operations stopped being one transition - which is the
	# server's story to tell and must fail here rather than be carried as a
	# client's own belief.
	if not (body.get("same_transition_for_both_operations", null) is bool):
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no boolean same-transition flag")
	if body["same_transition_for_both_operations"] != true:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer denies that both operations share one transition")
	var divergences: Variant = _string_list(body.get("divergences", null))
	if divergences == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no divergence-reason list")
	var behaviour: Variant = _behaviour(body.get("preserved_branch_behaviour", null))
	if behaviour == null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no preserved-branch behaviour table")
	# `price_charged` **must be present and null**. A missing key and a priced
	# answer are different, and the second is the failure this line exists to
	# refuse - so both are refused here, and neither is defaulted.
	if not body.has("price_charged"):
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer carries no price_charged field at all")
	if body["price_charged"] != null:
		return magic_failure(CODE_BAD_REQUEST,
			"the v1 magic answer charges a price, which this route never derives")

	var result := MagicCounterResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.action = ACTION
	result.instant = int(instant)
	result.magic = identity
	result.counter_before = int(counter["before"])
	result.counter_after = int(counter_after)
	result.had_recorded_entry = counter["had_recorded_entry"]
	result.cap = int(counter["cap"])
	result.at_cap = counter["at_cap"]
	result.cap_is = str(counter["cap_is"])
	result.committed = committed
	result.resources_after = balances
	result.stored_resources_compared = compared
	result.ledger_after = ledger
	result.same_transition_for_both_operations = true
	result.divergences = divergences
	result.preserved_branch_behaviour = behaviour
	result.price_charged = null
	return result


## The addressing block, verbatim. `requested_id` is **not** compared against
## `resolved_id`: that comparison is the server's decision to report, and this
## parser's job is to carry it, not to re-derive it.
static func _identity(value: Variant) -> MagicIdentity:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var requested: Variant = _whole_number(source.get("requested_id", null))
	if requested == null:
		return null
	var resolved: Variant = _whole_number(source.get("resolved_id", null))
	if resolved == null:
		return null
	var operation := str(source.get("operation", ""))
	if not OPERATIONS.has(operation):
		return null
	var ledger_key: Variant = source.get("ledger_key", null)
	if not (ledger_key is String):
		return null
	if str(ledger_key) == "":
		return null
	var transition_id: Variant = source.get("transition_id", null)
	if not (transition_id is String):
		return null
	if str(transition_id) == "":
		return null
	var identity := MagicIdentity.new()
	identity.requested_id = int(requested)
	identity.resolved_id = int(resolved)
	identity.operation = operation
	identity.ledger_key = str(ledger_key)
	identity.transition_id = str(transition_id)
	return identity


## The counter block, verbatim. **No member is compared against another** - in
## particular `after` is not checked against `cap` and `at_cap` is not recomputed
## from them. Those relations are the server's post-condition proof.
static func _counter(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var before: Variant = _whole_number(source.get("before", null))
	if before == null:
		return null
	var after: Variant = _whole_number(source.get("after", null))
	if after == null:
		return null
	if not (source.get("had_recorded_entry", null) is bool):
		return null
	var cap: Variant = _whole_number(source.get("cap", null))
	if cap == null:
		return null
	if not (source.get("at_cap", null) is bool):
		return null
	var cap_is: Variant = source.get("cap_is", null)
	if not (cap_is is String):
		return null
	if str(cap_is) == "":
		return null
	return {
		"before": int(before),
		"after": int(after),
		"had_recorded_entry": bool(source["had_recorded_entry"]),
		"cap": int(cap),
		"at_cap": bool(source["at_cap"]),
		"cap_is": str(cap_is),
	}


## The committed report, verbatim. Every reported field must be **present**, and
## every one of them is carried without being used: the two `level_compared` /
## `level_gate_enforced` booleans in particular are read as the server reported
## them and are **not** recomputed by comparing `player_level` with `level`,
## because a gate is exactly what design D5 refuses to derive.
static func _committed(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for field in REPORTED_COMMITTED_FIELDS:
		if not source.has(field):
			return null
	for field in ["player_level", "level_compared", "level_gate_enforced",
			"kind_source", "price_refused_because", "price_charged"]:
		if not source.has(field):
			return null
	# `player_level` is not a column of the magic table - it is the player's own
	# stored level, read so the answer can report it and deliberately **not**
	# compared with the committed `level` (design D5). A null one is therefore a
	# report this client cannot use, refused like every other unreadable field.
	if _whole_number(source["player_level"]) == null:
		return null
	if not (source["level_compared"] is bool):
		return null
	if not (source["level_gate_enforced"] is bool):
		return null
	# **Present is not enough; present and carrying a value is the requirement.**
	# Eight of the nine reported fields are columns the committed table really
	# has, so a null one is a malformed report. `kind` is the exception **by
	# measurement** - the raw `magics` table carries no such column - which makes
	# a *non-null* kind the malformed shape there instead. Both directions are
	# refused for one reason: a field this client cannot read must not be
	# carried as though it had read one.
	for field in REPORTED_COMMITTED_FIELDS:
		if field == "kind":
			if source[field] != null:
				return null
		elif source[field] == null:
			return null
	if not (source["kind_source"] is String):
		return null
	if str(source["kind_source"]) == "":
		return null
	if not (source["price_refused_because"] is String):
		return null
	if str(source["price_refused_because"]) == "":
		return null
	# The committed block repeats design D2 in its own right: the price is null
	# there too, and a non-null one would be a second priced claim inside a
	# payload whose top-level `price_charged` this parser has already refused.
	if source["price_charged"] != null:
		return null
	# And design D5 in the strongest form available here. An answer claiming it
	# compared the two levels, or enforced a gate, is refused for exactly the
	# reason `same_transition_for_both_operations` is required to be **true**
	# rather than merely present: the server's own statement of what it did is
	# the thing that must not contradict this client's recorded contract.
	if source["level_compared"] != false:
		return null
	if source["level_gate_enforced"] != false:
		return null
	# Carried verbatim and duplicated, because the caller keeps this dictionary
	# and a shared reference into a parsed payload is how a projection becomes a
	# second implementation.
	var out: Dictionary = {}
	for key in source:
		out[str(key)] = source[key]
	return out


## The complete stored balance set. Every one of the seven names must be present
## exactly once, because v1 reports what it read back and a partial set would be
## a partial payload.
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


## A list of strings. An **empty** list is accepted and kept distinct from an
## absent one: "the server reported no divergences" is a reportable answer and
## "the answer said nothing" is not.
static func _string_list(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		if not (entry is String):
			return null
		out.append(str(entry))
	return out


## The preserved-branch behaviour table. Its **four** members are required and
## none is required to say anything in particular: this is quoted prose, and the
## client executes none of it.
static func _behaviour(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for key in ["buy", "use", "absent_key", "same_number"]:
		if not source.has(key):
			return null
		if not (source[key] is String):
			return null
	var out: Dictionary = {}
	for key in source:
		out[str(key)] = str(source[key])
	return out


## A JSON number that really is a whole number, or null.
##
## Godot decodes **every** JSON number as a `float`, so `7` arrives as `7.0` and
## `7.5` arrives as `7.5`. Comparing against the rounded value is therefore the
## only honest whole-number test available on this engine, and it is why
## `int()` alone is never used to validate a reported number: it would accept
## `7.5` by truncating it, which would be a silently wrong id, counter or balance.
static func _whole_number(value: Variant) -> Variant:
	if not (value is float or value is int):
		return null
	if float(value) != floor(float(value)):
		return null
	return value