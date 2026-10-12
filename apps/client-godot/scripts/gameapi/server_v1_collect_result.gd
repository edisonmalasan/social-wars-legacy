extends RefCounted
## Server v1's own typed collect answer, and the parser that builds it.
##
## **This module is the reason `ServerV1Api` does not reuse `BootData`'s
## collect result, and that reason is a design decision rather than an
## inconvenience.**
##
## v1 answers a collection with a shape v0 has no way to express
## (`apps/server-v1/server_v1_outcomes.py`):
##
## ```
## {"result":"success","action":"collect","instant":<int>,
##  "rung":{"index":<int>,"threshold_seconds":<int>,"multiplier":<float>},
##  "derivation_id":"<hex>",
##  "derived_deltas":{"xp":<int>,"wood":<int>},
##  "resources_after":{"xp":<int>,"gold":<int>, ... seven stored balances},
##  "row_instant":<int>,"protocol":"server-v1"}
## ```
##
## `BootData.CollectResult` carries `payout` as the legacy **eight-slot
## fixed-width vector** `[unknown, xp, gold, wood, oil, steel, cash, mana]`,
## plus a `previous`/`row` pair of typed `Placement`s, plus `tier` and
## `reference_time`. v1's answer has **no eight-slot vector at all** - it names
## exactly the balances it moved - and it has **no row pair**, because v1's
## repository is the committed save document (design D5) and the row is not
## reported back.
##
## Forcing v1's answer into `BootData.CollectResult` would therefore require the
## client to do one of two forbidden things: **synthesise** an eight-slot vector
## from named deltas (which rebuilds the very legacy vector vocabulary the v1
## boundary exists to stop inheriting - see `server_v1_refusals.py` task 2.6),
## or **invent** a `Placement` for a row the service never reported. Both would
## put arithmetic in the client, which is the anti-pattern the whole line is
## about. So v1 gets its own typed result, and `GameApi.collect_income()`'s
## declared return type is `Variant` with the three concrete types named in its
## own comment (and asserted by `tests/test_server_v1.gd`).
##
## **What this result does NOT carry, and why.** There is no `previous` and no
## `row`, so a caller cannot see the row before or after - v1 reports only the
## new `row_instant`. There is no `reference_time`, because v1 derives the rung
## from its own clock and does not report the elapsed reference it compared
## against. There is no `game_version`, because v1 stamps `protocol` and nothing
## else. Nothing here is reconstructed, and nothing is defaulted to zero.
##
## **The derivation evidence is read-only.** `derived_deltas` and
## `derivation_id` are the receipt for a payout the SERVER computed; the client
## applies `resources_after` verbatim and never adds a delta to anything. The
## client's own arithmetic is not used anywhere in this file except to *check*
## that reported integers really are integers (Godot decodes every JSON number
## as a `float`, so `3` arrives as `3.0`).

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The closed set of stored balance names `resources_after` must carry, exactly
## and completely. This is the client's own seven-balance typed model
## (`BootData.Resources`), reused because it is a *client-side view of stored
## balances* and not protocol vocabulary - v1 names the same seven the legacy
## engine writes (`engine.py:251-271`) and the corpus agrees.
const STORED_RESOURCE_NAMES := [
	"xp", "gold", "wood", "oil", "steel", "cash", "mana",
]

## The protocol string v1 stamps on every answer.
const PROTOCOL := "server-v1"

## The only action this delivered v1 route performs.
const ACTION := "collect"

## Client-LOCAL codes. **These are not v1 refusal codes**: they never reach the
## server, so they cannot be in `server_v1_refusals.REFUSAL_HTTP_STATUS`, and
## `tests/test_server_v1.gd` asserts that every one of them is absent from the
## committed server vocabulary read out of the repository. `unsupported` is
## "v1 has no such route"; `bad_request` is "v1 answered something this parser
## refuses to guess at". Every code v1 itself refuses travels through
## `error_code` **verbatim**, in the same field, so a caller reads one field.
const CODE_UNSUPPORTED := "unsupported_by_server_v1"
const CODE_BAD_REQUEST := "bad_request"


## The committed ladder rung a payout was derived for, exactly as v1 reports it.
## `index` is 0-based, `threshold_seconds` is the elapsed time that rung's
## committed bound is expressed in, and `multiplier` is that rung's committed
## multiplier. **All three are reported verbatim**: this module never computes a
## rung, never clamps one, and never compares two of these values.
class Rung:
	extends RefCounted
	var index := -1
	var threshold_seconds := 0
	var multiplier := 0.0


## v1's typed answer to one collection intent.
##
## On success `ok` is true and every field below is populated from the response;
## on refusal `ok` is false, `error_code` carries v1's own code verbatim, and
## **every other field stays at its default** - there is no partial payload, the
## same rule every `BootData.*Result` already follows.
class CollectResult:
	extends RefCounted
	var ok := false
	## `"server-v1"` on every answer v1 produced; "" on a local failure.
	var protocol := ""
	## `"collect"` on success; "" on failure. The action the server says ran, so
	## a caller cannot read a collect answer as some other action's.
	var action := ""
	## The instant the server recorded for the transaction.
	var instant := 0
	## The rung the payout was derived for, or null on failure.
	var rung: Rung = null
	## The server's own identifier for the derivation it performed. Read-only
	## evidence; the client never uses it to compute anything.
	var derivation_id := ""
	## **Named** deltas the server applied: `{"xp": 3, "wood": 60}`. Named, not
	## positional - there is no eight-slot vector anywhere in v1's answer.
	## Read-only evidence; the client never applies it.
	var derived_deltas: Dictionary = {}
	## The complete stored balance set the server read back AFTER the write.
	## Applied **verbatim**; never added to, never recomputed.
	var resources_after: BootData.Resources = null
	## The addressed row's recorded collection instant after the write. v1's
	## only report of the row itself.
	var row_instant := 0
	var error_code := ""
	var error_message := ""
	## v1's structured refusal `detail` object, verbatim; empty on success.
	var error_detail: Dictionary = {}


## Structured failure, never a partial payload.
static func collect_failure(code: String, message: String,
		detail: Dictionary = {}) -> CollectResult:
	var result := CollectResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	result.error_detail = detail.duplicate()
	return result


## Builds the typed result from v1's payload, failing CLOSED on every malformed
## shape. A refused answer keeps v1's own code, message and detail; a success is
## only built when **every** documented field is present and well-typed.
static func parse_collect(payload: Variant) -> CollectResult:
	if not (payload is Dictionary):
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer is not a JSON object")
	var body: Dictionary = payload
	var kind := str(body.get("result", ""))
	if kind == "refused":
		return _refusal(body)
	if kind != "success":
		# `%s`, never `%r`: this engine has no `%r` format character and reports
		# it as an engine ERROR line even though the statement completes, which
		# would fail `verify-boot.ps1` on a suite that reported itself green.
		# The two cases are spelled apart because "no `result` field" and "a
		# `result` field this client does not understand" are different bugs.
		var seen := "<absent>" if not body.has("result") else str(body["result"])
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no recognised result field: %s" % seen)
	return _success(body)


## A v1 refusal, verbatim. No field is derived from it and none is defaulted.
static func _refusal(body: Dictionary) -> CollectResult:
	var code := str(body.get("code", ""))
	if code == "":
		return collect_failure(CODE_BAD_REQUEST,
			"a refused v1 answer carries no code")
	var detail: Variant = body.get("detail", {})
	if not (detail is Dictionary):
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 refusal detail is not an object")
	var result := collect_failure(code, str(body.get("message", "")), detail)
	result.protocol = str(body.get("protocol", ""))
	return result


## A v1 success, or a closed refusal. Nothing is defaulted.
static func _success(body: Dictionary) -> CollectResult:
	if str(body.get("protocol", "")) != PROTOCOL:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer is not stamped %s" % PROTOCOL)
	if str(body.get("action", "")) != ACTION:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer reports action %s"
			% str(body.get("action", "")))
	var instant: Variant = _whole_number(body.get("instant", null))
	if instant == null:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no whole-number instant")
	var row_instant: Variant = _whole_number(
		body.get("row_instant", null))
	if row_instant == null:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no whole-number row instant")
	var derivation_id := str(body.get("derivation_id", ""))
	if derivation_id == "":
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no derivation id")
	var rung: Rung = _rung(body.get("rung", null))
	if rung == null:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no usable rung block")
	var deltas: Variant = _deltas(body.get("derived_deltas", null))
	if deltas == null:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no usable named deltas")
	var balances: BootData.Resources = _resources(
		body.get("resources_after", null))
	if balances == null:
		return collect_failure(CODE_BAD_REQUEST,
			"the v1 collect answer carries no complete stored balance set")

	var result := CollectResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.action = ACTION
	result.instant = int(instant)
	result.rung = rung
	result.derivation_id = derivation_id
	result.derived_deltas = deltas
	result.resources_after = balances
	result.row_instant = int(row_instant)
	return result


## The rung block, verbatim. Each member is read once and never compared with
## another: `index` is not checked against `threshold_seconds`, and
## `multiplier` is not checked against `index`.
static func _rung(value: Variant) -> Rung:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var index: Variant = _whole_number(source.get("index", null))
	if index == null:
		return null
	var threshold: Variant = _whole_number(
		source.get("threshold_seconds", null))
	if threshold == null:
		return null
	var multiplier: Variant = source.get("multiplier", null)
	if not (multiplier is float or multiplier is int):
		return null
	var rung := Rung.new()
	rung.index = int(index)
	rung.threshold_seconds = int(threshold)
	rung.multiplier = float(multiplier)
	return rung


## The named deltas. Every key must name a stored balance and every value must be
## a whole number. An **empty** set is accepted and kept distinct from an absent
## one, because "the server moved nothing" is a reportable answer and "the
## answer said nothing" is not.
static func _deltas(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var out: Dictionary = {}
	for name in source:
		var key := str(name)
		if not STORED_RESOURCE_NAMES.has(key):
			return null
		var amount: Variant = _whole_number(source[name])
		if amount == null:
			return null
		out[key] = int(amount)
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


## A JSON number that really is a whole number, or null.
##
## Godot decodes **every** JSON number as a `float`, so `3` arrives as `3.0` and
## `3.5` arrives as `3.5`. Comparing against the rounded value is therefore the
## only honest whole-number test available on this engine, and it is why the
## multiplication-free shape of this module matters: `int()` alone would accept
## `3.5` by truncating it, which would be a silently wrong balance.
static func _whole_number(value: Variant) -> Variant:
	if not (value is float or value is int):
		return null
	if float(value) != floor(float(value)):
		return null
	return value
