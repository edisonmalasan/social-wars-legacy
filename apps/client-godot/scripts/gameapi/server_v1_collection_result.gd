extends RefCounted
## Server v1's own typed **collection-grant** answer, and the parser for it.
##
## **This module is the second reason `ServerV1Api` does not reuse `BootData`'s
## typed results, and for a different reason than `server_v1_collect_result.gd`
## gives.** v1 answers a collection *completion* with a **grant**, and a grant is
## a different shape of answer from a payout in three ways that no shared model
## could absorb:
##
## ```
## {"result":"success","action":"collection","instant":<int>,
##  "collection":{"requested_id":<int>,"resolved_id":<int>,
##                 "position":<int>,"clamp_moved":<bool>,"grant_id":"<hex>"},
##  "requirement_ids":[<int>, ...],
##  "derived_price":<int>,
##  "derived_deltas":{"cash":-<int>},
##  "resources_after":{... seven stored balances ...},
##  "granted_item_id":<int>,"granted_quantity":<int>,
##  "prize_stored_after":<int>,
##  "ledger_after":[<int>, ...],
##  "protocol":"server-v1"}
## ```
##
## 1. **`derived_deltas` is negative.** v0's `BootData.CollectionResult` reports
##    what the player *received*; this reports what the server *charged*. A shared
##    "amount" field would have to pick a sign convention, and picking one would
##    be inventing a rule rather than reporting one.
## 2. **It carries the server's own addressing decision** - `requested_id` beside
##    `resolved_id`, plus `clamp_moved` - which exists because v1 **refuses** an
##    id that the preserved branch would have clamped onto collection 1 (design
##    D3). `BootData.CollectionResult` has nowhere to put an id it did not resolve.
## 3. **It carries storage and ledger state** (`granted_item_id`,
##    `granted_quantity`, `prize_stored_after`, `ledger_after`), which are the
##    read-back halves of v1's post-execution proof. v0's answer carries none of
##    them, because v0 never proved anything about what it wrote.
##
## **Everything here is reported verbatim.** This module computes no price, no
## eligibility, no total, and no ledger growth. It does not check that
## `granted_quantity` and `prize_stored_after` agree, because that comparison is
## the *server's* post-condition proof and re-doing it on the client would be a
## second implementation of a rule the server already owns.
##
## **The only arithmetic-shaped expression in this file** is the whole-number test
## in `_whole_number()`, and it exists because Godot decodes every JSON number as
## a `float`: `7` arrives as `7.0`, and `int()` alone would silently truncate a
## `7.5`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The closed set of stored balance names `resources_after` must carry, exactly
## and completely. The same seven v1 reports and `BootData.Resources` models; this
## is a client-side view of stored balances, not protocol vocabulary.
const STORED_RESOURCE_NAMES := [
	"xp", "gold", "wood", "oil", "steel", "cash", "mana",
]

## The protocol string v1 stamps on every answer.
const PROTOCOL := "server-v1"

## The only action this delivered v1 grant route performs.
const ACTION := "collection"

## Client-LOCAL codes. **These are not v1 refusal codes**: they never reach the
## server, so they cannot be in `server_v1_refusals.REFUSAL_HTTP_STATUS`.
## `unsupported` means "v1 has no such route"; `bad_request` means "v1 answered
## something this parser refuses to guess at". Every code v1 itself refuses
## travels through `error_code` **verbatim**, in the same field, so a caller
## reads one field whatever refused the request.
const CODE_UNSUPPORTED := "unsupported_by_server_v1"
const CODE_BAD_REQUEST := "bad_request"


## v1's **addressing decision** for one grant, exactly as it reports it.
##
## `requested_id` is what the client sent; `resolved_id` is the committed
## collection the server actually read; `position` is the committed row it read
## it from. `clamp_moved` is true when the two ids disagree - which, for every
## id v1 accepts today, is **never**, because an id that would have been clamped
## is refused as `aliased_collection_id` instead. It is carried because a
## renumbered committed table must be *reportable*, not silently absorbed.
class Grant:
	extends RefCounted
	var requested_id := -1
	var resolved_id := -1
	var position := -1
	var clamp_moved := false
	var grant_id := ""


## v1's typed answer to one collection-completion intent.
##
## On success `ok` is true and every field below is populated from the response;
## on refusal `ok` is false, `error_code` carries v1's own code verbatim, and
## **every other field stays at its default** - there is no partial payload.
class CollectionGrantResult:
	extends RefCounted
	var ok := false
	## `"server-v1"` on every answer v1 produced; "" on a local failure.
	var protocol := ""
	## `"collection"` on success; "" on failure. The action the server says ran,
	## so a caller cannot read a grant answer as some other action's.
	var action := ""
	## The instant the server recorded for the transaction.
	var instant := 0
	## The addressing decision, or null on failure.
	var grant: Grant = null
	## The committed requirement ids the server evaluated eligibility against.
	## Read-only evidence; the client never evaluates it.
	var requirement_ids: Array = []
	## The committed `cashPrice` the server charged. Read-only; the client
	## never subtracts it.
	var derived_price := 0
	## **Named** deltas the server applied: `{"cash": -9}`. Negative by
	## construction here - a collection is a debit. Read-only evidence; the
	## client never applies it.
	var derived_deltas: Dictionary = {}
	## The complete stored balance set the server read back AFTER the write.
	## Applied **verbatim**; never added to, never recomputed.
	var resources_after: BootData.Resources = null
	## The item id the server granted.
	var granted_item_id := -1
	## The committed quantity it granted of that item.
	var granted_quantity := 0
	## That item's quantity in storage after the grant, read back by the server.
	var prize_stored_after := 0
	## The collection ledger after the grant, read back by the server.
	var ledger_after: Array = []
	var error_code := ""
	var error_message := ""
	## v1's structured refusal `detail` object, verbatim; empty on success.
	var error_detail: Dictionary = {}


## Structured failure, never a partial payload.
static func grant_failure(code: String, message: String,
		detail: Dictionary = {}) -> CollectionGrantResult:
	var result := CollectionGrantResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	result.error_detail = detail.duplicate()
	return result


## Builds the typed result from v1's payload, failing CLOSED on every malformed
## shape. A refused answer keeps v1's own code, message and detail; a success is
## only built when **every** documented field is present and well-typed.
static func parse_grant(payload: Variant) -> CollectionGrantResult:
	if not (payload is Dictionary):
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer is not a JSON object")
	var body: Dictionary = payload
	var kind := str(body.get("result", ""))
	if kind == "refused":
		return _refusal(body)
	if kind != "success":
		# `%s`, never `%r`: this engine has no `%r` format character and reports
		# it as an engine ERROR line even though the statement completes, which
		# would fail `verify-boot.ps1` on a suite that reported itself green.
		var seen := "<absent>" if not body.has("result") else str(body["result"])
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no recognised result field: %s" % seen)
	return _success(body)


## A v1 refusal, verbatim. No field is derived from it and none is defaulted.
static func _refusal(body: Dictionary) -> CollectionGrantResult:
	var code := str(body.get("code", ""))
	if code == "":
		return grant_failure(CODE_BAD_REQUEST,
			"a refused v1 answer carries no code")
	var detail: Variant = body.get("detail", {})
	if not (detail is Dictionary):
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 refusal detail is not an object")
	var result := grant_failure(code, str(body.get("message", "")), detail)
	result.protocol = str(body.get("protocol", ""))
	return result


## A v1 success, or a closed refusal. Nothing is defaulted.
static func _success(body: Dictionary) -> CollectionGrantResult:
	if str(body.get("protocol", "")) != PROTOCOL:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer is not stamped %s" % PROTOCOL)
	if str(body.get("action", "")) != ACTION:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer reports action %s"
			% str(body.get("action", "")))
	var instant: Variant = _whole_number(body.get("instant", null))
	if instant == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number instant")
	var grant: Grant = _grant(body.get("collection", null))
	if grant == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no usable collection block")
	var requirements: Variant = _id_list(body.get("requirement_ids", null))
	if requirements == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number requirement list")
	var price: Variant = _whole_number(body.get("derived_price", null))
	if price == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number derived price")
	var deltas: Variant = _deltas(body.get("derived_deltas", null))
	if deltas == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no usable named deltas")
	var balances: BootData.Resources = _resources(
		body.get("resources_after", null))
	if balances == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no complete stored balance set")
	var granted_item: Variant = _whole_number(body.get("granted_item_id", null))
	if granted_item == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number granted item id")
	var granted_quantity: Variant = _whole_number(
		body.get("granted_quantity", null))
	if granted_quantity == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number granted quantity")
	var stored_after: Variant = _whole_number(
		body.get("prize_stored_after", null))
	if stored_after == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number stored quantity")
	var ledger: Variant = _id_list(body.get("ledger_after", null))
	if ledger == null:
		return grant_failure(CODE_BAD_REQUEST,
			"the v1 collection answer carries no whole-number ledger")

	var result := CollectionGrantResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.action = ACTION
	result.instant = int(instant)
	result.grant = grant
	result.requirement_ids = requirements
	result.derived_price = int(price)
	result.derived_deltas = deltas
	result.resources_after = balances
	result.granted_item_id = int(granted_item)
	result.granted_quantity = int(granted_quantity)
	result.prize_stored_after = int(stored_after)
	result.ledger_after = ledger
	return result


## The addressing block, verbatim. Each member is read once and no two of them
## are compared: `requested_id` is not checked against `resolved_id`, and
## `clamp_moved` is not recomputed from them. That comparison is the server's
## decision to report, and this parser's job is to carry it, not to re-derive it.
static func _grant(value: Variant) -> Grant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var requested: Variant = _whole_number(source.get("requested_id", null))
	if requested == null:
		return null
	var resolved: Variant = _whole_number(source.get("resolved_id", null))
	if resolved == null:
		return null
	var position: Variant = _whole_number(source.get("position", null))
	if position == null:
		return null
	if not (source.get("clamp_moved", null) is bool):
		return null
	var grant_id := str(source.get("grant_id", ""))
	if grant_id == "":
		return null
	var grant := Grant.new()
	grant.requested_id = int(requested)
	grant.resolved_id = int(resolved)
	grant.position = int(position)
	grant.clamp_moved = bool(source["clamp_moved"])
	grant.grant_id = grant_id
	return grant


## A list of whole numbers. An **empty** list is accepted and kept distinct from
## an absent one: "the server evaluated an empty requirement set" is a reportable
## answer and "the answer said nothing" is not.
static func _id_list(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		var whole: Variant = _whole_number(entry)
		if whole == null:
			return null
		out.append(int(whole))
	return out


## The named deltas. Every key must name a stored balance and every value must be
## a whole number. **A negative amount is accepted**, not refused: this route
## debits, and refusing a negative here would refuse every correct answer.
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
## Godot decodes **every** JSON number as a `float`, so `7` arrives as `7.0` and
## `7.5` arrives as `7.5`. Comparing against the rounded value is therefore the
## only honest whole-number test available on this engine, and it is why
## `int()` alone is never used to validate a reported number: it would accept
## `7.5` by truncating it, which would be a silently wrong id, price or balance.
static func _whole_number(value: Variant) -> Variant:
	if not (value is float or value is int):
		return null
	if float(value) != floor(float(value)):
		return null
	return value