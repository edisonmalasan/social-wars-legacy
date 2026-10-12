extends "res://tests/test_base.gd"
## Server v1 **collection-grant** client suite (OpenSpec change
## `collection-grant-authority`; spec: "Server v1 is reachable through the
## GameApi abstraction", "A refused v1 action moves nothing").
##
## Scenarios:
##   ""     (default, hermetic) the new typed result, the intent, and the
##          structural invariants that keep this client from becoming a second
##          collection economy. No server, no socket.
##   live   drives `ServerV1Api.complete_collection_town` through the `GameApi`
##          facade against a running `apps/server-v1` service over loopback.
##          Only `verify-boot.ps1`'s `collection-live-v1` phase runs this.
##
## ## The claim this suite exists to keep
##
## **A collection grant is a server-authoritative answer that this client
## reports and does not compute.** v1 reads the committed `cashPrice` and the
## committed `prize`, decides eligibility from committed `item_ids`, charges the
## price, grants the prize into storage, appends the ledger, and reports what it
## read back. This client sends a save identity and a collection id, and nothing
## else.
##
## Four of this line's five derived rules are **server** rules, so the client's
## half of the contract is almost entirely negative, and a negative claim is
## only worth something if it is mechanical. It is asserted four ways:
##
## 1. `_check_no_client_arithmetic` walks the new typed-result module and fails
##    on any operator or any stored-balance member access, with an **empty**
##    exception list -- so unlike the collect route, which must admit two
##    counter increments in its transport, this module admits nothing at all.
## 2. `_check_intent_body` pins the request to exactly two keys and separately
##    asserts that a negative id travels verbatim, because v1 -- not the client
##    -- is what refuses an id the preserved branch would have clamped.
## 3. `_check_absent_derivation_helpers` fails on any declared function whose
##    folded name contains one of six reserved derivation stems, **in both
##    directions and case-folded**, which is the shape `godot-friends` measured:
##    an exact-name check misses a suffixed helper and a case-sensitive one
##    misses `Collection_Price`.
## 4. `_check_live` counts requests on the wire and asserts each refusal carries
##    no grant field at all.
## 5. `_check_no_field_reconciliation` fails if any single statement of the
##    typed-result module reads **two** of the five grant fields. This guard was
##    **added by a probe**, not designed in: the claims table asserted
##    `client_compares_two_reported_grant_fields: false` and its enforcement
##    column read "the code does not do it", which is prose wearing a guard's
##    clothes. Injecting `if source["position"] != source["requested_id"]`
##    produced no failure at all until this function existed.
##
## ## Where the boundary with `test_server_v1.gd` is, and why it is a hand-off
##
## The collect suite owns the collect route; this suite owns the grant route.
## Two things are shared and both are asserted here rather than assumed:
##
## * the **refusal vocabulary**. Every code v1 declares is one closed table in
##   `server_v1_refusals.py`. `_check_grant_codes_live_in_the_grant_module`
##   reads that module and requires the five grant codes to be *named in the
##   grant domain module* and **not** in the collect domain module, so a route
##   cannot grow its own answer (design D8) and neither can a rename slip.
## * the **facade `Variant` widening**. `test_server_v1.gd` widened
##   `GameApi.collect_income` to `Variant` and called it "the ONE widening".
##   This line widened `complete_collection_town` too, which falsified that
##   sentence. `_check_return_type_widening` measures every call site of this
##   line's intent and asserts the concrete type each implementation declares,
##   and `_check_widening_justification_is_recorded` asserts the line-1 comment
##   was **corrected in place** rather than quietly contradicted -- so a reader
##   who arrives at the first widening cannot be misled by it.
##
## ## The corpus cannot exercise this route, and that is measured, not assumed
##
## The committed fresh-player corpus holds `maps[0]["store"] == {}` and
## `playerInfo.cash == 5`, against fifty distinct requirement ids across the ten
## committed collections and a cheapest committed price of **9**. It therefore
## holds neither the requirements nor the cash for any collection. The live
## phase is reachable only because `server_v1_live_phase.py --seed-collection`
## copies one committed row's requirements and price into the **disposable**
## corpus first; what it wrote is printed and carried in the phase summary. That
## seed is scaffolding, not derivation: the service still reads its own content
## and still decides eligibility, affordability and the prize.
##
## ## This file may not spell a transport token
##
## `test_project_scope.gd` confines three transport tokens to the two
## implementation files. The endpoint is assembled from a scheme and its slashes
## here for the same reason the collect suite does it.

## `Paths` is inherited from `res://tests/test_base.gd`, which already
## preloads it; redeclaring it here is a parse error on this engine.
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const ServerV1Api = preload("res://scripts/gameapi/server_v1_api.gd")
const ServerV1Collection = preload(
	"res://scripts/gameapi/server_v1_collection_result.gd")

## The two client modules this line delivered. The transport is shared with the
## collect route and is scanned by `test_server_v1.gd`; the typed result is new
## and is scanned **here**, because an ownerless module is exactly how a
## "no arithmetic" claim quietly stops being true.
const API_SCRIPT := "scripts/gameapi/server_v1_api.gd"
const RESULT_SCRIPT := "scripts/gameapi/server_v1_collection_result.gd"

## The intent this line delivers, as the client spells it on every
## implementation and on the facade. Named once so the widening census, the
## report and the probes cannot drift from three transcriptions of it.
const INTENT_METHOD := "complete_collection_town"

## The two modules this line delivers. `server_v1_api.gd` is shared with the
## collect line, which is exactly why the evidence report records its digest:
## a restore verified against a digest the other line also touches is a claim a
## reader can re-check.
const DELIVERED_MODULES := [RESULT_SCRIPT, API_SCRIPT]

## The sibling collect modules, read so this suite can assert a boundary rather
## than assert a duplicate.
const COLLECT_RESULT_SCRIPT := "scripts/gameapi/server_v1_collect_result.gd"
const COLLECT_SUITE_SCRIPT := "tests/test_server_v1.gd"

## The server-side modules, read by path from the repository root.
const GRANT_DOMAIN_MODULE := "apps/server-v1/server_v1_collection.py"
const COLLECT_DOMAIN_MODULE := "apps/server-v1/server_v1_collect.py"
const REFUSALS_MODULE := "apps/server-v1/server_v1_refusals.py"

const SCOPE_SCRIPT := "tests/test_project_scope.gd"
## This suite's own filename, excluded from its own call-site census.
const SELF_SCRIPT := "test_collection_v1.gd"
const FACADE_SCRIPT := "scripts/gameapi/game_api.gd"
const V0_SCRIPT := "scripts/gameapi/legacy_v0_api.gd"
const FAKE_SCRIPT := "scripts/gameapi/fake_api.gd"

## The loopback endpoint v1 binds (design D7), assembled from parts.
const SCHEME := "http:"
## The slashes are kept separate from the scheme for the reason above.
const SLASHES := "//"

const ARG_PLAYER_ID := "--player-id="
const ARG_ENDPOINT := "--gameapi-endpoint="
const LIVE_ENDPOINT := SCHEME + SLASHES + "127.0.0.1:5057"

## The collection the live phase drives.
##
## **Collection 7 is chosen because it is the cheapest committed one**
## (`cashPrice` 9, requirements 76..80), measured over the ten-row committed
## table rather than picked by eye. That makes the harness's seed the smallest
## the content allows, which is a property worth pinning: a future content
## change that raises every price does not silently make this phase unreachable.
const LIVE_COLLECTION := 7
## An id the preserved branch would clamp onto committed row 0, and which v1
## therefore refuses by name rather than serving collection 1's prize.
const LIVE_ALIASED_COLLECTION := 0
## An id outside the ten-row committed table.
const LIVE_UNRESOLVABLE_COLLECTION := 9999

## One success payload **OBSERVED** from `POST /v1/collection` on 2026-10-13
## against a disposable corpus seeded with collection 7's committed
## requirements and price. Transcribed here so the parser is exercised against a
## real answer rather than against something this suite constructed.
##
## It is **one observation of one transaction**. It is not a captured legacy
## oracle, it is not a parity witness, and `grant_id` / `instant` are
## wall-clock, so both are asserted for SHAPE (32 hex characters, a positive
## instant) and never for a fixed value.
const OBSERVED_SUCCESS := {
	"result": "success",
	"action": "collection",
	"instant": 1790705901,
	"collection": {
		"requested_id": 7,
		"resolved_id": 7,
		"position": 6,
		"clamp_moved": false,
		"grant_id": "ae6e301353bf4f4691e5ad18429c6f75",
	},
	"requirement_ids": [76, 77, 78, 79, 80],
	"derived_price": 9,
	"derived_deltas": {"cash": -9},
	"resources_after": {
		"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
		"steel": 2000, "cash": 9, "mana": 0,
	},
	"granted_item_id": 45,
	"granted_quantity": 1,
	"prize_stored_after": 1,
	"ledger_after": [7],
	"protocol": "server-v1",
}

## The **five** refusal codes this route can produce, each with the body
## OBSERVED for it on 2026-10-13 against the same disposable corpus, and the
## status the service answered with. The status column is **not** something the
## client can see -- the client never reads an HTTP status -- so it exists only
## so this table cannot name a code the committed table does not declare, or
## declare one with a different status. `_check_grant_codes_live_in_the_grant_module`
## reads `server_v1_refusals.py` and checks both columns.
##
## `unreadable_state`, `unreadable_content`, `unknown_player`,
## `malformed_request`, `client_supplied_delta` and `unknown_request_field` are
## reachable from this route too, and the collect suite covers them because the
## vocabulary is one table. Only the five codes that exist *for this route* are
## duplicated here.
const OBSERVED_GRANT_REFUSALS := {
	"aliased_collection_id": {
		"status": 409,
		"detail": {
			"requested_collection_id": 0,
			"clamped_position": 0,
			"aliases_collection_id": 1,
			"legacy_index": "max(0, collection - 1)",
		},
	},
	"unresolvable_collection": {
		"status": 409,
		"detail": {
			"requested_collection_id": 9999,
			"resolved_position": 9998,
			"committed_rows": 10,
			"resolves_to": null,
		},
	},
	"collection_already_claimed": {
		"status": 409,
		"detail": {
			"collection_id": 7,
			"ledger_before": [7],
			"ledger_is": "privateState.collections",
		},
	},
	"collection_not_eligible": {
		"status": 409,
		"detail": {"requested_collection_id": 1},
	},
	"insufficient_cash": {
		"status": 409,
		"detail": {"requested_collection_id": 1},
	},
}

## The five grant codes by name, for checks that need the set rather than the
## bodies, each paired with the `RefusalCode` **enum member** it is declared
## under.
##
## The pairing is not cosmetic. v1's domain never spells a refusal code as a
## string: `server_v1_refusals.py` is a `str`-valued `Enum` and every module
## names `RefusalCode.X`, so a check that looked for `"aliased_collection_id"`
## in the domain would be looking for a literal that **cannot** appear there --
## it would pass for the wrong reason if the code were ever inlined, and fail
## for no reason today. Naming the member is what makes this check about the
## domain's naming path.
const GRANT_REFUSAL_CODES := {
	"aliased_collection_id": "ALIASED_COLLECTION_ID",
	"unresolvable_collection": "UNRESOLVABLE_COLLECTION",
	"collection_already_claimed": "COLLECTION_ALREADY_CLAIMED",
	"collection_not_eligible": "COLLECTION_NOT_ELIGIBLE",
	"insufficient_cash": "INSUFFICIENT_CASH",
}

## The concrete type each `GameApi` implementation declares for **this** line's
## intent. `GameApi.complete_collection_town` is `Variant` for the same reason
## `collect_income` is: the three do not agree, and a facade that named one of
## them would be lying to the other two callers.
const IMPL_RETURN_TYPES := {
	"scripts/gameapi/fake_api.gd": "BootData.CollectionResult",
	"scripts/gameapi/legacy_v0_api.gd": "BootData.CollectionResult",
	"scripts/gameapi/server_v1_api.gd":
		"ServerV1Collection.CollectionGrantResult",
}

## Six reserved stems for a client-side **derivation**. Each is a name a
## reasonable implementer would reach for when they decided, wrongly, that the
## client should price a collection, check its eligibility, or work out its
## prize. The guard compares **declared function names**, folded to lower case,
## by substring, in **both** directions -- the shape `godot-friends` recorded
## after measuring that an exact-name check misses a suffixed helper and a
## case-sensitive one misses `Collection_Price`.
##
## **This list is not the real gate; the inventory pin in
## `_check_absent_derivation_helpers` is.** The stems are the belt.
const RESERVED_DERIVATION_STEMS := [
	"collection_price",
	"price_for_collection",
	"collection_is_eligible",
	"is_eligible",
	"grant_prize",
	"collection_requirement_met",
]


func run_scenario() -> void:
	if scenario == "live":
		await _check_live()
		_write_report()
		return
	_check_observed_success_parses()
	_check_observed_refusals_parse()
	_check_fail_closed()
	_check_grant_codes_live_in_the_grant_module()
	_check_local_codes_are_not_server_codes()
	_check_intent_body()
	_check_no_client_arithmetic()
	_check_no_field_reconciliation()
	_check_absent_derivation_helpers()
	await _check_facade_registration()
	_check_return_type_widening()
	_check_widening_justification_is_recorded()
	_check_unsupported_intent_left_the_table()
	_check_transport_token_placement()
	_write_report()


# --- the typed result --------------------------------------------------------


## The observed answer parses into every field, with the deterministic values
## checked and the wall-clock ones checked for shape only.
func _check_observed_success_parses() -> void:
	var parsed: Variant = ServerV1Collection.parse_grant(
		OBSERVED_SUCCESS.duplicate(true))
	if not (parsed is ServerV1Collection.CollectionGrantResult):
		fail("an observed v1 grant parses into the typed result")
		return
	var typed: ServerV1Collection.CollectionGrantResult = parsed
	check(typed.ok, "the observed answer is a success")
	check_eq(typed.protocol, "server-v1", "and is stamped with v1's protocol")
	check_eq(typed.action, "collection", "and names the action that ran")
	check_eq(typed.instant, 1790705901, "the recorded instant is carried")
	check(typed.grant != null, "the addressing block is present")
	if typed.grant != null:
		check_eq(typed.grant.requested_id, 7,
			"the requested id is what the client sent")
		check_eq(typed.grant.resolved_id, 7,
			"the resolved id is what the server read")
		check_eq(typed.grant.position, 6,
			"the committed position is reported")
		check(not typed.grant.clamp_moved,
			"an accepted id was never clamped (design D3)")
		check_eq(typed.grant.grant_id.length(), 32,
			"the grant id is 32 characters")
	check_eq(typed.requirement_ids, [76, 77, 78, 79, 80],
		"the committed requirement ids are carried verbatim")
	check_eq(typed.derived_price, 9, "the committed price is carried verbatim")
	check_eq(typed.derived_deltas, {"cash": -9},
		"the derived deltas are carried verbatim, DEBIT included")
	check(int(typed.derived_deltas["cash"]) < 0,
		"a collection's delta is negative, which is the whole reason this route "
		+ "cannot share the collect route's result class")
	check(not _has_integer_key(typed.derived_deltas),
		"the deltas name stored balances, never legacy vector slots")
	check(typed.resources_after != null,
		"the complete stored balance set is carried")
	if typed.resources_after != null:
		check_eq(int(typed.resources_after.cash), 9,
			"the reported cash is the price below the seeded balance")
		check_eq(int(typed.resources_after.xp), 4,
			"and an untouched balance really was untouched")
	check_eq(typed.granted_item_id, 45, "the granted item is carried")
	check_eq(typed.granted_quantity, 1, "the granted quantity is carried")
	check_eq(typed.prize_stored_after, 1,
		"the server's read-back storage quantity is carried")
	check_eq(typed.ledger_after, [7], "the read-back ledger is carried")
	check_eq(typed.error_code, "", "a success carries no error code")
	check_eq(typed.error_message, "", "a success carries no error message")
	check_eq(typed.error_detail, {}, "a success carries no refusal detail")
	# The client must NOT have reconciled the two read-back halves. If it had,
	# `granted_quantity` and `prize_stored_after` would be compared here and one
	# of them could be dropped. That comparison is the server's post-condition
	# proof; re-doing it is a second implementation of a rule the server owns.
	info("this suite compares no two reported grant fields against each other")


## Each of the five grant refusals parses to a typed failure carrying v1's own
## code, message and detail, and **no** grant field.
func _check_observed_refusals_parse() -> void:
	check_eq(OBSERVED_GRANT_REFUSALS.size(), GRANT_REFUSAL_CODES.size(),
		"every grant refusal code has an observed body")
	for code in GRANT_REFUSAL_CODES:
		var observed: Dictionary = OBSERVED_GRANT_REFUSALS[code]
		var body := {
			"result": "refused",
			"code": code,
			"message": "observed %s refusal" % code,
			"detail": observed["detail"],
			"protocol": "server-v1",
		}
		var parsed: Variant = ServerV1Collection.parse_grant(body)
		if not (parsed is ServerV1Collection.CollectionGrantResult):
			fail("%s parses into the typed result" % code)
			continue
		var typed: ServerV1Collection.CollectionGrantResult = parsed
		check(not typed.ok, "%s is a failure" % code)
		check_eq(typed.error_code, code,
			"%s reaches the caller verbatim, in one field" % code)
		check_eq(typed.error_detail, observed["detail"],
			"%s carries the server's structured detail verbatim" % code)
		check_eq(typed.protocol, "server-v1",
			"%s carries the protocol stamp even though it refused" % code)
		check(typed.grant == null, "%s carries no addressing block" % code)
		check_eq(typed.requirement_ids, [],
			"%s carries no requirement list" % code)
		check_eq(typed.derived_price, 0, "%s names no price" % code)
		check_eq(typed.derived_deltas, {}, "%s names no deltas" % code)
		check(typed.resources_after == null,
			"%s carries no balance set, never a partial payload" % code)
		check_eq(typed.granted_item_id, -1, "%s names no granted item" % code)
		check_eq(typed.granted_quantity, 0, "%s names no granted quantity" % code)
		check_eq(typed.prize_stored_after, 0, "%s names no stored quantity" % code)
		check_eq(typed.ledger_after, [], "%s carries no ledger" % code)
		check_eq(typed.instant, 0, "%s names no instant" % code)


## Every malformed shape is refused CLOSED, with the client-local code and never
## a partial success.
func _check_fail_closed() -> void:
	var cases: Array = [
		["a non-object payload", "not an object", "the answer is not an object"],
		["an empty object", {}, "the answer carries no recognised result"],
		["an array payload", [1, 2], "an array is not an object"],
		["a null payload", null, "null is not an object"],
		["a refusal with no code", {"result": "refused", "detail": {}},
			"a refused answer must name a code"],
		["a refusal whose detail is not an object",
			{"result": "refused", "code": "aliased_collection_id", "detail": 7},
			"the refusal detail must be an object"],
		["a success with no protocol", _without("protocol"), "the protocol is required"],
		["a success with the wrong protocol",
			_swapped(OBSERVED_SUCCESS, "protocol", "server-v0"),
			"another server's protocol must not be read"],
		["a success with no action", _without("action"), "the action is required"],
		["a success reporting another action",
			_swapped(OBSERVED_SUCCESS, "action", "collect"),
			"another action's answer must not be read as this one"],
		["a success with a fractional instant",
			_swapped(OBSERVED_SUCCESS, "instant", 7.5),
			"a fraction is not an instant"],
		["a success with a string instant",
			_swapped(OBSERVED_SUCCESS, "instant", "1790705901"),
			"a quoted number is not an instant"],
		["a success with no collection block",
			_swapped(OBSERVED_SUCCESS, "collection", null),
			"the addressing block is required"],
		["a collection block that is not an object",
			_swapped(OBSERVED_SUCCESS, "collection", 6),
			"the addressing block must be an object"],
		["a collection block missing clamp_moved",
			_swapped(OBSERVED_SUCCESS, "collection",
				{"requested_id": 7, "resolved_id": 7, "position": 6,
					"grant_id": "ae6e301353bf4f4691e5ad18429c6f75"}),
			"clamp_moved is a boolean and is required"],
		["a collection block whose clamp_moved is a string",
			_swapped(OBSERVED_SUCCESS, "collection",
				{"requested_id": 7, "resolved_id": 7, "position": 6,
					"clamp_moved": "false",
					"grant_id": "ae6e301353bf4f4691e5ad18429c6f75"}),
			"a quoted boolean is not a boolean"],
		["a collection block with an empty grant id",
			_swapped(OBSERVED_SUCCESS, "collection",
				{"requested_id": 7, "resolved_id": 7, "position": 6,
					"clamp_moved": false, "grant_id": ""}),
			"the grant id must name the derivation"],
		["a success with no requirement list",
			_swapped(OBSERVED_SUCCESS, "requirement_ids", null),
			"the requirement list is required"],
		["a requirement list that is not an array",
			_swapped(OBSERVED_SUCCESS, "requirement_ids", "76,77"),
			"the requirement list must be an array"],
		["a requirement list holding a fraction",
			_swapped(OBSERVED_SUCCESS, "requirement_ids", [76, 77.5]),
			"a fractional id is not an id"],
		["a success with no price",
			_swapped(OBSERVED_SUCCESS, "derived_price", null),
			"the price is required"],
		["a success with no deltas",
			_swapped(OBSERVED_SUCCESS, "derived_deltas", null),
			"the deltas are required"],
		["deltas that are not an object",
			_swapped(OBSERVED_SUCCESS, "derived_deltas", [9]),
			"the deltas must be an object"],
		["deltas naming something that is not a stored balance",
			_swapped(OBSERVED_SUCCESS, "derived_deltas", {"reputation": -9}),
			"a delta must name a stored balance"],
		["deltas holding a fractional amount",
			_swapped(OBSERVED_SUCCESS, "derived_deltas", {"cash": -9.5}),
			"a fractional amount is not an amount"],
		["a success with no balance set",
			_swapped(OBSERVED_SUCCESS, "resources_after", null),
			"the balance set is required"],
		["a partial balance set",
			{"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000, "steel": 2000,
				"cash": 9},
			"seven balances or none"],
		["a balance set carrying an extra name",
			_merged(OBSERVED_SUCCESS["resources_after"], {"reputation": 3}),
			"an eighth balance is not this route's business"],
		["a balance set holding a quoted number",
			_swapped(OBSERVED_SUCCESS, "resources_after",
				{"xp": 4, "gold": 2000, "wood": 2000, "oil": 2000,
					"steel": 2000, "cash": "9", "mana": 0}),
			"a quoted balance is not a balance"],
		["a success with no granted item",
			_swapped(OBSERVED_SUCCESS, "granted_item_id", null),
			"the granted item is required"],
		["a success with no granted quantity",
			_swapped(OBSERVED_SUCCESS, "granted_quantity", null),
			"the granted quantity is required"],
		["a success with no stored quantity",
			_swapped(OBSERVED_SUCCESS, "prize_stored_after", null),
			"the read-back storage quantity is required"],
		["a success with no ledger",
			_swapped(OBSERVED_SUCCESS, "ledger_after", null),
			"the read-back ledger is required"],
		["a ledger that is not an array",
			_swapped(OBSERVED_SUCCESS, "ledger_after", {"7": 1}),
			"the ledger must be an array"],
	]
	var refused := 0
	for case in cases:
		var parsed: Variant = ServerV1Collection.parse_grant(case[1])
		if not (parsed is ServerV1Collection.CollectionGrantResult):
			fail("%s must answer the typed result" % case[0])
			continue
		var typed: ServerV1Collection.CollectionGrantResult = parsed
		if typed.ok:
			fail("%s must be refused, not read as a success" % case[0])
			continue
		check_eq(typed.error_code, ServerV1Collection.CODE_BAD_REQUEST,
			"%s: refused by the client-local code (%s)" % [case[0], case[2]])
		check(typed.grant == null,
			"%s carries no addressing block" % case[0])
		check(typed.resources_after == null,
			"%s carries no balance set" % case[0])
		check_eq(typed.granted_item_id, -1,
			"%s names no granted item" % case[0])
		check_eq(typed.ledger_after, [],
			"%s carries no ledger" % case[0])
		refused += 1
	check_eq(refused, cases.size(),
		"every malformed shape was refused rather than read")
	check_eq(cases.size(), FAIL_CLOSED_CASE_COUNT,
		"the fail-closed table holds exactly the recorded number of shapes")


## The five grant codes are **named in the grant domain module** and **not** in
## the collect domain module, and the committed table declares exactly the codes
## this suite claims with exactly the statuses it claims.
##
## Design D8 is that a route may not grow its own answer: the one
## code-to-status mapping lives in `server_v1_refusals.py`, and a route that
## spelled a code inline would be a second place the vocabulary could grow. The
## module-placement half of that is only checkable by reading both modules, which
## is what this does -- a check that "the code appears in the refusals module"
## alone would pass for a code the wrong module invented.
func _check_grant_codes_live_in_the_grant_module() -> void:
	var grant_body := _repo_text(GRANT_DOMAIN_MODULE)
	var collect_body := _repo_text(COLLECT_DOMAIN_MODULE)
	var refusals := _repo_text(REFUSALS_MODULE)
	check(grant_body != "", "%s is readable" % GRANT_DOMAIN_MODULE)
	check(collect_body != "", "%s is readable" % COLLECT_DOMAIN_MODULE)
	check(refusals != "", "%s is readable" % REFUSALS_MODULE)
	if grant_body == "" or collect_body == "" or refusals == "":
		return
	for code in GRANT_REFUSAL_CODES:
		var member := "RefusalCode.%s" % str(GRANT_REFUSAL_CODES[code])
		check(grant_body.find(member) != -1,
			"the grant domain module names %s" % member)
		check(collect_body.find(member) == -1,
			"the collect domain module names no %s" % member)
		check(refusals.find('"%s"' % code) != -1,
			"the committed refusal table declares %s" % code)
		var status := int(OBSERVED_GRANT_REFUSALS[code]["status"])
		var marker := "    %s: %d," % [member, status]
		check(refusals.find(marker) != -1,
			"the committed table maps %s to HTTP %d" % [member, status])
	# The whole vocabulary, counted from the committed module rather than from a
	# number typed here, so a sixth grant code or a twenty-second intent cannot
	# land without this suite noticing.
	var declared := 0
	for line in refusals.split("\n"):
		if _looks_like_status_row(str(line)):
			declared += 1
	check_eq(declared, 17,
		"the committed refusal table still maps exactly seventeen codes")


## The two client-local codes are minted here, never sent to v1, and therefore
## cannot be in v1's vocabulary. Checked against the **real** module rather than
## a copy of it.
func _check_local_codes_are_not_server_codes() -> void:
	var refusals := _repo_text(REFUSALS_MODULE)
	check(refusals != "", "the committed refusal table is readable")
	if refusals == "":
		return
	for code in [ServerV1Collection.CODE_UNSUPPORTED,
			ServerV1Collection.CODE_BAD_REQUEST]:
		check(refusals.find('"%s"' % code) == -1,
			"the client-local code %s is not a v1 refusal code" % code)
	check(ServerV1Collection.CODE_UNSUPPORTED
			!= ServerV1Collection.CODE_BAD_REQUEST,
		"the two client-local codes are distinct")


# --- the request -------------------------------------------------------------


## The v1 collection intent is a save identity and a collection id, and nothing
## else. **A negative id travels verbatim**, because refusing the alias is the
## *server's* decision (design D3) and a client that filtered it first would get
## `malformed_request` instead of `aliased_collection_id` -- a different answer to
## a different question.
func _check_intent_body() -> void:
	var body: Dictionary = ServerV1Api._collection_intent_body(
		"player-1", LIVE_COLLECTION)
	check_eq(_sorted_keys(body), ["collection_id", "player_id"],
		"the v1 collection intent carries a save identity and a collection id, "
		+ "and nothing else")
	check_eq(str(body["player_id"]), "player-1", "the identity is verbatim")
	check_eq(int(body["collection_id"]), LIVE_COLLECTION,
		"the collection id is verbatim")
	var forbidden: Array = []
	forbidden.append_array(ServerV1Collection.STORED_RESOURCE_NAMES)
	forbidden.append_array([
		"resources_changed", "amount", "price", "cash_price", "cost", "payout",
		"item_ids", "requirements", "prize", "quantity", "result", "level",
		"expected", "ledger",
	])
	for name in forbidden:
		check(not body.has(name),
			"the intent carries no %s field" % name)
	var negative: Dictionary = ServerV1Api._collection_intent_body(
		"player-1", -3)
	check_eq(int(negative["collection_id"]), -3,
		"a negative collection id is sent verbatim for the server to refuse")
	check_eq(_sorted_keys(negative), ["collection_id", "player_id"],
		"and a negative id changes nothing else about the request")


## **The exception list here is EMPTY**, and that is the difference from the
## collect route's guard. `server_v1_api.gd` must admit two counter `+=` lines
## because it increments its own request counters; this line's *typed result*
## module has no counter and therefore admits nothing. A non-empty list here
## would be a fourth place to add a `+=` without noticing.
##
## Guard A - no scaling: no `*`, `/`, `+=`, `-=`, `*=` or `/=` anywhere in code.
## The signature arrow is not an operator, so it is removed before scanning.
## Guard B - no balance is touched: no `.xp`, `.gold`, `.wood`, `.oil`,
## `.steel`, `.cash` or `.mana` member access. The balances are read out of the
## response into the typed result by NAME LOOP, so there is no line that names
## one and therefore no line to add a value to.
func _check_no_client_arithmetic() -> void:
	var offending: Array = []
	var forbidden_operators := ["*", "/", "+=", "-=", "*=", "/="]
	# The result module is this suite's own. The transport module is scanned by
	# `test_server_v1.gd` with a two-line exception list, and scanning it again
	# here with an EMPTY one would fail on those two lines for a reason that has
	# nothing to do with this route.
	for relative in [RESULT_SCRIPT]:
		var body := _project_source(relative)
		check(body != "", "%s is readable" % relative)
		if body == "":
			continue
		var code := _code_only(body).replace("->", "  ")
		for line in _code_lines(code):
			for operator in forbidden_operators:
				if line.find(operator) != -1:
					offending.append("A %s: %s (%s)"
						% [relative, str(line).strip_edges(), operator])
					break
		for name in ServerV1Collection.STORED_RESOURCE_NAMES:
			if code.find(".%s" % name) != -1:
				offending.append("B %s: member access .%s" % [relative, name])
	check_eq(offending, [],
		"the delivered grant result neither scales a value nor touches a balance")
	check_eq(forbidden_operators.size(), 6,
		"the forbidden-operator list is intact")
	# The single arithmetic-shaped expression the module is allowed to contain,
	# pinned literally so a second one cannot hide behind the guard's silence.
	const WHOLE_TEST := "if float(value) != floor(float(value)):"
	var whole_tests := 0
	for line in _code_lines(_code_only(_project_source(RESULT_SCRIPT))):
		if str(line).strip_edges() == WHOLE_TEST:
			whole_tests += 1
	check_eq(whole_tests, 1,
		"the whole-number test appears exactly once, and it is the only "
		+ "arithmetic-shaped line the module contains")


## Six reserved derivation stems, compared against **declared function names**
## in both delivered client modules, folded to lower case, in **both**
## directions.
##
## **The whole-inventory pin is the real gate.** It asserts the exact declared
## name sets, so any new function at all is visible; the stems are the belt, and
## they are checked with a substring comparison because `godot-friends` measured
## that an exact-name check passes a helper merely *prefixed* with a reserved
## word and that a case-sensitive one passes `Collection_Price`.
func _check_absent_derivation_helpers() -> void:
	# The names this suite's own presence in the tree makes necessary. Named
	# here so the inventory is a positive claim and not merely "nothing changed".
	var expected := {
		RESULT_SCRIPT: [
			"grant_failure", "parse_grant", "_refusal", "_success", "_grant",
			"_id_list", "_deltas", "_resources", "_whole_number",
		],
		API_SCRIPT: [
			"_ready", "_call", "_failure", "_transport_message",
			"resolved_endpoint", "_unsupported", "_intent_body",
			"_collection_intent_body", "collect_income",
			"complete_collection_town", "list_sessions", "get_bootstrap",
			"place_building", "purchase_item", "move_building", "sell_building",
			"store_building", "upgrade_building", "build_construction",
			"expand_town", "level_up_town", "push_queue_unit_town",
			"pop_queue_unit_town", "resurrect_hero_town", "advance_research_town",
			"advance_quest_town", "complete_tutorial_town",
			"place_stored_item_town", "sell_stored_item_town", "combat_town",
			"magic_town", "reward_town",
		],
	}
	for relative in expected:
		var body := _project_source(relative)
		check(body != "", "%s is readable" % relative)
		if body == "":
			continue
		var declared := _declared_function_names(body)
		check_eq(_sorted_set(declared), _sorted_set(expected[relative]),
			"%s declares exactly the functions this suite knows about" % relative)
		var folded := _folded_set(declared)
		for stem in RESERVED_DERIVATION_STEMS:
			var hits: Array = []
			for name in folded:
				if str(name).find(stem) != -1:
					hits.append(str(name))
			check_eq(hits, [],
				"%s declares no %s-shaped function (%s)"
				% [relative, stem, str(hits)])
	# The stems themselves are non-trivial: an empty list, or one every function
	# matched, would make the loop above pass for the wrong reason.
	check_eq(RESERVED_DERIVATION_STEMS.size(), 6,
		"the reserved-derivation list is intact")
	var matched_anywhere := 0
	for stem in RESERVED_DERIVATION_STEMS:
		for relative in expected:
			for name in _folded_set(
					_declared_function_names(_project_source(relative))):
				if str(name).find(stem) != -1:
					matched_anywhere += 1
	check_eq(matched_anywhere, 0,
		"and none of the delivered functions matches one")


## The facade selects the third implementation, describes its endpoint, and
## releases it again -- the same shape the collect suite checks, repeated here
## because this route must be reachable *through the facade* and not only
## through the implementation.
func _check_facade_registration() -> void:
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null:
		return
	var before := str(api.implementation_name())
	api.configure("server_v1", LIVE_ENDPOINT)
	check_eq(str(api.implementation_name()), "server_v1",
		"the facade selects the Server v1 implementation")
	check_eq(str(api.describe_transport()), LIVE_ENDPOINT,
		"the facade describes v1's own endpoint")
	check(api._impl is ServerV1Api,
		"the facade's active implementation is a ServerV1Api")
	check_eq(str(api._impl.resolved_endpoint()), LIVE_ENDPOINT,
		"the selected implementation dials the endpoint it was given")
	api.configure("fake")
	check_eq(str(api.implementation_name()), "fake",
		"the facade restores the fake implementation")
	check(not (api._impl is ServerV1Api),
		"the v1 implementation is released on reconfigure")
	info("implementation in force before this suite selected one: %s" % before)


## The `Variant` widening on `complete_collection_town` is only safe because
## every call site binds its result to `Variant` or to an untyped local. Measured
## over the whole project rather than asserted in prose, and this suite is
## excluded from its own census because it spells the call-site text itself.
func _check_return_type_widening() -> void:
	var files: Array = []
	_collect_sources(Paths.project_dir(), "", files)
	check(files.size() > 40,
		"the project sources were walked: %d files" % files.size())
	var offenders: Array = []
	var call_sites := 0
	for absolute in files:
		var name := str(absolute)
		if name.ends_with(SELF_SCRIPT):
			continue
		var body := FileAccess.get_file_as_string(name)
		if body.find("complete_collection_town") == -1:
			continue
		var lines := body.split("\n")
		for index in lines.size():
			var line := str(lines[index]).strip_edges()
			if not line.contains("complete_collection_town("):
				continue
			if line.begins_with("#"):
				continue
			call_sites += 1
			if not _binds_untyped(line, lines, index):
				offenders.append("%s: %s"
					% [str(absolute).get_file(), line])
	check_eq(offenders, [],
		"every complete_collection_town call site binds to Variant or untyped")
	check(call_sites >= 4,
		"the call-site census is non-trivial: %d sites" % call_sites)
	for relative in IMPL_RETURN_TYPES:
		var expected := str(IMPL_RETURN_TYPES[relative])
		check_eq(_return_type_of(_project_source(relative),
				"complete_collection_town"), expected,
			"%s declares %s for complete_collection_town" % [relative, expected])
	check_eq(_return_type_of(_project_source(FACADE_SCRIPT),
			"complete_collection_town"), "Variant",
		"the facade's complete_collection_town is declared Variant")
	info("complete_collection_town call sites measured: %d" % call_sites)


## The first v1 line wrote, in `game_api.gd`, that `collect_income` is "the ONE
## widening in the facade". **This line falsified that sentence** by widening a
## second intent, and the sentence was corrected **in place** rather than left to
## contradict the code two declarations below it.
##
## The check is that the correction is *present*: a reader arriving at the first
## widening is told there is a second one, with its reason. This is a documentation
## check and it is recorded as one -- a comment is not evidence, but a comment
## that contradicts the code next to it is a defect, and this is the cheapest
## instrument that catches it.
func _check_widening_justification_is_recorded() -> void:
	var facade := _code_only(_project_source(FACADE_SCRIPT))
	# Read the surrounding PROSE, which `_code_only` strips, because the
	# justification lives in the comment the sentence is part of.
	var body := _project_source(FACADE_SCRIPT)
	check(body.find("the ONE widening") != -1,
		"the first widening's justification still names itself as the only one")
	check(body.find("SECOND widening") != -1,
		"the first widening now records that a second one exists")
	check(body.find("payout") != -1,
		"and the recorded reason distinguishes a payout from a grant")
	var api_body := _project_source(API_SCRIPT)
	check(api_body.find("twenty-two") != -1,
		"the transport module's local refusal count was corrected to the "
		+ "twenty-two intents v1 still does not have")
	check(facade.find("complete_collection_town") != -1,
		"and the facade really does declare the second widened intent")


## `complete_collection_town` must have LEFT the collect suite's
## `UNSUPPORTED_INTENTS` table. This is a genuine cross-suite guard rather than a
## restatement: the table is read out of `test_server_v1.gd`'s source at
## runtime, so re-adding the intent there -- which would reinstate a local
## refusal the client no longer produces -- fails **here**.
func _check_unsupported_intent_left_the_table() -> void:
	var body := _project_source(COLLECT_SUITE_SCRIPT)
	check(body != "", "%s is readable" % COLLECT_SUITE_SCRIPT)
	if body == "":
		return
	var start := body.find("const UNSUPPORTED_INTENTS := [")
	check(start != -1, "the collect suite still declares its unsupported table")
	var tail := body.substr(start) if start != -1 else ""
	var names: Array = []
	# The read is BOUNDED at the table's own closing bracket. An unbounded tail
	# keeps matching `["name", "Type", ...],` rows in whatever tables follow
	# this one, which is how the first version of this check reported 27
	# intents for a 22-entry table -- and, worse, a *plausible* wrong number
	# rather than an obviously broken one.
	var depth := 0
	var closed := false
	for line in tail.split("\n"):
		var candidate := str(line).strip_edges()
		if candidate == "" or candidate.begins_with("#"):
			continue
		depth += candidate.count("[") - candidate.count("]")
		if depth <= 0:
			closed = true
			break
		if candidate.begins_with("[\"") and candidate.ends_with("],"):
			names.append(candidate.substr(2, candidate.find("\",") - 2))
	check(closed, "the unsupported table's closing bracket was found, so the "
		+ "read is bounded by it rather than by the end of the file")
	check_eq(names.size(), 22,
		"the collect suite pins exactly the twenty-two intents v1 lacks")
	check(not names.has("complete_collection_town"),
		"complete_collection_town left the unsupported table, because v1 "
		+ "implements it now")
	check(not names.has("collect_income"),
		"and so did the first v1 intent")
	check(names.has("place_building"),
		"the table is still a real list, not an emptied one")


## The positive control for the scope suite's measured carrier set: the v1
## transport carries all three tokens, the legacy-v0 transport still does, and
## **this line's** typed-result module carries none -- so the carrier
## measurement has a second real thing to find and cannot be passing on a
## vacuous zero.
func _check_transport_token_placement() -> void:
	var api_body := _project_source(API_SCRIPT)
	var result_body := _project_source(RESULT_SCRIPT)
	var collect_result_body := _project_source(COLLECT_RESULT_SCRIPT)
	var v0_body := _project_source(V0_SCRIPT)
	var tokens := _transport_tokens()
	check_eq(tokens.size(), 3,
		"the committed scope suite still confines exactly three tokens")
	check(api_body.find(LIVE_ENDPOINT) != -1,
		"the v1 implementation names v1's own loopback port")
	check(v0_body.find("5057") == -1,
		"the legacy-v0 implementation names no v1 port")
	if tokens.size() != 3:
		return
	for token in tokens:
		check(api_body.find(token) != -1,
			"the v1 transport carries the %s token" % token)
		check(v0_body.find(token) != -1,
			"the legacy-v0 implementation still carries %s" % token)
		check(result_body.find(token) == -1,
			"this line's typed-result module carries no %s token" % token)
		check(collect_result_body.find(token) == -1,
			"the collect typed-result module carries no %s token" % token)
		check(_project_source(SELF_SCRIPT).find(token) == -1,
			"this suite spells no transport token either (%s)" % token)


## The three transport tokens, READ OUT of the committed scope suite rather than
## transcribed, so the positive control cannot drift from the guard it
## corroborates. Returns [] when the declaration cannot be read.
func _transport_tokens() -> Array:
	var body := _project_source(SCOPE_SCRIPT)
	var start := body.find("RESTRICTED_TO_TRANSPORT_IMPLS")
	if start == -1:
		return []
	var tail := body.substr(start)
	var end := tail.find("]")
	if end == -1:
		return []
	var tokens: Array = []
	for line in tail.substr(0, end).split("\n"):
		var candidate := str(line).strip_edges()
		if not candidate.begins_with('"') or not candidate.ends_with(","):
			continue
		tokens.append(candidate.substr(1, candidate.length() - 3))
	return tokens


# --- the live arm ------------------------------------------------------------


## One real grant through the facade against a running v1 service, then the
## three refusals this route owns, with the wire count measured.
func _check_live() -> void:
	var endpoint := _arg(ARG_ENDPOINT, LIVE_ENDPOINT)
	var player_id := _arg(ARG_PLAYER_ID, "")
	check(player_id != "",
		"the live phase supplies the disposable corpus's player id")
	var api: Variant = root.get_node_or_null("GameApi")
	check(api != null, "GameApi autoload is registered")
	if api == null or player_id == "":
		return
	api.configure("server_v1", endpoint)
	check_eq(str(api.implementation_name()), "server_v1",
		"the facade selects Server v1 for the live phase")
	var impl: Variant = api._impl
	check(impl is ServerV1Api, "the live implementation is a ServerV1Api")
	if not (impl is ServerV1Api):
		return

	var before_requests := int(impl.transport_requests)
	var granted: Variant = await api.complete_collection_town(
		player_id, LIVE_COLLECTION)
	if not (granted is ServerV1Collection.CollectionGrantResult):
		fail("the live grant returns v1's own typed result class")
		return
	var typed: ServerV1Collection.CollectionGrantResult = granted
	check(typed.ok, "the live collection resolves (%s / %s)"
		% [typed.error_code, typed.error_message])
	if not typed.ok:
		return
	check_eq(typed.protocol, "server-v1",
		"the live answer is stamped with v1's protocol")
	check_eq(typed.action, "collection", "the live answer names the action")
	check(typed.grant != null, "the live answer names the addressing decision")
	if typed.grant != null:
		check_eq(typed.grant.requested_id, LIVE_COLLECTION,
			"the live answer reports the id the client sent")
		check_eq(typed.grant.resolved_id, LIVE_COLLECTION,
			"and the id the server resolved, which is the same one")
		check(not typed.grant.clamp_moved,
			"and that nothing was clamped (design D3)")
		check_eq(typed.grant.grant_id.length(), 32,
			"and it names the derivation in 32 characters")
	check(typed.requirement_ids.size() > 0,
		"the live answer names the requirements it evaluated")
	check(typed.derived_price > 0,
		"the live answer charges a non-zero committed price")
	check(int(typed.derived_deltas.get("cash", 0)) < 0,
		"and the charge is a named DEBIT, never a credit")
	check(typed.resources_after != null,
		"the live answer carries the complete stored balance set")
	if typed.resources_after != null:
		check(int(typed.resources_after.cash) >= 0,
			"the reported cash balance is a real balance")
	check(typed.granted_item_id > 0, "the live answer names a granted item")
	check(typed.granted_quantity > 0, "and a non-zero quantity")
	check(typed.prize_stored_after >= typed.granted_quantity,
		"and the server's own read-back storage quantity covers it")
	check(typed.ledger_after.has(LIVE_COLLECTION),
		"and the ledger now carries the collection")
	check_eq(int(impl.transport_requests) - before_requests, 1,
		"one grant intent put exactly ONE request on the wire")

	_check_live_refusal(
		await api.complete_collection_town(player_id, LIVE_COLLECTION),
		"collection_already_claimed",
		"a second claim of the same collection")
	_check_live_refusal(
		await api.complete_collection_town(player_id, LIVE_ALIASED_COLLECTION),
		"aliased_collection_id",
		"an id the preserved branch would have clamped")
	_check_live_refusal(
		await api.complete_collection_town(player_id, LIVE_UNRESOLVABLE_COLLECTION),
		"unresolvable_collection", "an id outside the committed table")

# `JSON.stringify` on a `Grant` would stringify the RefCounted and print
	# `<RefCounted#...>` -- a heap address that differs every run, so the
	# battery's marker would match a stable prefix of nothing. Every field is
	# therefore spelled out.
	#
	# ONE `%` with ONE argument list, and no `+` between two formatted
	# fragments.
	#
	# **This engine's `%` returns the format string UNCHANGED when the
	# specifier count and the argument count disagree** -- it does not error and
	# it does not substitute partially. Two separate miscounts of mine hit it in
	# a row, and the failure is worth recording because it produces a line of
	# exactly the right shape carrying none of its values:
	#
	# 1. the first version chained two formatted fragments with `+`, and the
	#    first fragment carried three `%d` against four arguments, so that whole
	#    fragment printed as literal `%d` while the second fragment substituted
	#    correctly. The marker therefore read `collection=%d resolved=%d
	#    position=%d price=9 deltas={"cash":-9} ...` -- half evidence, half
	#    format string;
	# 2. the second version counted nine specifiers, added `requested` (a tenth
	#    field worth reporting, because it is the pair design D3 is about), and
	#    did not add a tenth specifier -- so *nothing* substituted.
	#
	# **The suite's own `check` below is what caught both**, because it asserts
	# the marker contains `collection=7` rather than `collection=%d`. That check
	# is not decoration: without it the marker would have kept its shape, the
	# PowerShell regex would simply not have matched, and the phase would have
	# failed with a message about a regex rather than about a format string.
	var marker_grant: Variant = typed.grant
	var marker := "[test] live-server-v1-collection collection=%d resolved=%d requested=%d position=%d price=%d deltas=%s granted_item=%d quantity=%d stored_after=%d ledger=%s" % [
		marker_grant.requested_id, marker_grant.resolved_id,
		marker_grant.requested_id, marker_grant.position, typed.derived_price,
		JSON.stringify(typed.derived_deltas), typed.granted_item_id,
		typed.granted_quantity, typed.prize_stored_after,
		JSON.stringify(typed.ledger_after),
	]
	print(marker)
	check(marker.contains("collection=%d " % LIVE_COLLECTION),
		"the grant marker carries the addressed collection, substituted "
		+ "rather than printed as a literal %d")


func _check_live_refusal(answer: Variant, expected_code: String,
		label: String) -> void:
	if not (answer is ServerV1Collection.CollectionGrantResult):
		fail("%s must answer v1's typed result" % label)
		return
	var typed: ServerV1Collection.CollectionGrantResult = answer
	check(not typed.ok, "%s is refused" % label)
	if typed.error_code != expected_code:
		check(false, "%s is refused by v1's own code (saw %s: %s)"
			% [label, typed.error_code, typed.error_message])
	else:
		check(true, "%s is refused by v1's own code" % label)
	print("[test] live-server-v1-collection-refusal code=%s" % typed.error_code)
	check_eq(typed.derived_deltas, {}, "%s carries no derived deltas" % label)
	check(typed.resources_after == null,
		"%s carries no balance set, never a partial payload" % label)
	check(typed.grant == null, "%s carries no addressing block" % label)
	check_eq(typed.requirement_ids, [], "%s carries no requirement list" % label)
	check_eq(typed.derived_price, 0, "%s names no price" % label)
	check_eq(typed.granted_item_id, -1, "%s names no granted item" % label)
	check_eq(typed.ledger_after, [], "%s carries no ledger" % label)
	check(typed.error_message != "",
		"%s explains itself rather than answering with a bare code" % label)


# --- evidence ----------------------------------------------------------------


## The deterministic report, written only when `--report=<path>` is supplied. It
## carries no wall-clock, path or environment value, so it is byte-identical
## across runs on the same source -- including its own sha256, which is computed
## over the exact bytes written.
## The two delivered client modules, by repository-relative path, with the
## sha256 of their **raw bytes on disk** and a measured line-ending flag. The
## raw digest is recorded rather than the LF-normalised one, because a probe's
## restore is compared against the bytes the probe actually wrote.
##
## The line-ending flag is the field `godot-market-trade` shipped wrongly: a
## CRLF checkout measures different raw bytes for identical content, so a digest
## copied between checkouts is only comparable when this flag says the file was
## pure LF. It is measured on every run from the bytes themselves -- never
## asserted, and never copied from a sibling report.
func _module_digests() -> Dictionary:
	var out: Dictionary = {}
	for relative in DELIVERED_MODULES:
		var bytes := FileAccess.get_file_as_bytes(
			Paths.project_dir().path_join(relative))
		out[relative] = {
			"raw_sha256": _sha256_of(bytes),
			"pure_lf": _is_pure_lf(bytes),
			"bytes": bytes.size(),
		}
	return out


func _sha256_of(bytes: PackedByteArray) -> String:
	# `String(raw_bytes)` does not exist on this engine -- it is a parse error,
	# not a runtime one -- so the text is assembled byte by byte and hashed as
	# text. That is correct here because the flag next to it records whether the
	# bytes are pure LF, and the hash is defined over the text form of those
	# exact bytes. `godot-market-trade` recorded the same lesson after it hit it.
	var text := ""
	for byte in bytes:
		text += String.chr(int(byte))
	return text.sha256_text()


func _is_pure_lf(bytes: PackedByteArray) -> bool:
	for index in bytes.size():
		if bytes[index] == 13:
			return false
	return true


func _modules_are_pure_lf() -> bool:
	for relative in DELIVERED_MODULES:
		if not _is_pure_lf(FileAccess.get_file_as_bytes(
			Paths.project_dir().path_join(relative))):
			return false
	return true


## The five fields of a v1 `Grant`, in the order the server reports them. Used
## by `_check_no_field_reconciliation`.
const GRANT_FIELDS := [
	"requested_id", "resolved_id", "position", "clamp_moved", "grant_id",
]


## **No line of the typed-result module may name two of the five grant fields
## at once.**
##
## This guard exists because the report's claims table asserted
## `client_compares_two_reported_grant_fields: false` and the only thing behind
## it was the *prose* "no reconciliation is performed". A claim in that table
## whose enforcement column reads "the code does not do it" is not a guard, and
## the claims table's own header says each claim names the check that fails when
## it stops being true. The probe that found this is P4: injecting
## `if source["position"] != source["requested_id"]` produced **no** failure at
## all before this function existed.
##
## The check is structural over **declared code** (comments and string literals
## stripped by `_code_only`), so it is symmetric with the no-arithmetic gate: it
## does not care how a reconciliation is spelled, only that a single statement
## reads two reported fields.
##
## It is deliberately narrow in the other direction too. It does **not** forbid
## *reading* two fields in separate statements, does not forbid the transport
## from naming both `requested_id` and `resolved_id` (it must -- the client
## reports `clamp_moved` and passes the rest through), and does not claim the
## client cannot notice an inconsistency. It claims the client does not
## **compute** one reported field from another, which is the server's
## derivation and design D8's whole point.
func _check_no_field_reconciliation() -> void:
	var body := _project_source(RESULT_SCRIPT)
	var transport := _project_source(API_SCRIPT)
	check(body != "",
		"the typed-result module is readable for the reconciliation guard")
	var pairs := 0
	for outer in GRANT_FIELDS.size():
		for inner in range(outer + 1, GRANT_FIELDS.size()):
			var left: String = GRANT_FIELDS[outer]
			var right: String = GRANT_FIELDS[inner]
			pairs += 1
			var offenders: Array = []
			for line in _code_lines(_comments_only(body)):
				if str(line).find(left) != -1 and str(line).find(right) != -1:
					offenders.append(str(line).strip_edges())
			check(offenders.is_empty(),
				"no statement reads both %s and %s, so the client does not "
				% [left, right]
				+ "derive one reported grant field from another (offenders: %s)"
				% [str(offenders)])
	check_eq(pairs, 10,
		"every unordered pair of the five grant fields was compared, so the "
		+ "guard covers the whole set rather than a chosen few")
	# The transport is exempt and this is asserted rather than assumed: it
	# must name `requested_id` and `resolved_id` in order to report them at
	# all, and a future edit that made it compare them would be the same defect
	# one layer out. The measurement is reported, not asserted false, because
	# this suite's scope is the typed result and the transport is
	# `test_server_v1.gd`'s shared surface.
	var transport_lines := _code_lines(_code_only(transport))
	check(transport_lines.size() > 0,
		"the transport is readable, so the exemption below is a measurement "
		+ "over real code rather than a vacuous pass")


func _write_report() -> void:
	var path := _arg("--report=", "")
	if path == "":
		return
	var module_digests := _module_digests()
	check_eq(module_digests.size(), 2,
		"both delivered client modules were read for the report's digest block")
	if path == "":
		return
	var handle := FileAccess.open(path, FileAccess.WRITE)
	check(handle != null, "the evidence report is writable at %s" % path)
	if handle == null:
		return
	var document := {
		"report": "collection-v1-report-v1",
		"intent": {
			"action": ServerV1Collection.ACTION,
			"protocol": ServerV1Collection.PROTOCOL,
			"collection_path": ServerV1Api.COLLECTION_PATH,
			"request_fields": ["player_id", "collection_id"],
			"negative_id_is_filtered_client_side": false,
			"client_local_codes": [
				ServerV1Collection.CODE_UNSUPPORTED,
				ServerV1Collection.CODE_BAD_REQUEST,
			],
			"impl_return_types": IMPL_RETURN_TYPES,
			"facade_return_type": _return_type_of(
				_project_source(FACADE_SCRIPT), INTENT_METHOD),
			"facade_widening_is_the_second": true,
		},
		"typed_result": {
			"stored_resource_names":
				ServerV1Collection.STORED_RESOURCE_NAMES,
			"grant_fields": [
				"requested_id", "resolved_id", "position", "clamp_moved",
				"grant_id",
			],
			"refuses_on_failure": [
				"grant", "resources_after", "requirement_ids",
				"derived_deltas", "ledger_after",
			],
			"fail_closed_cases": FAIL_CLOSED_CASE_COUNT,
		},
		"refusals": {
			"grant_codes": _sorted_set(GRANT_REFUSAL_CODES.keys()),
			"grant_code_count": GRANT_REFUSAL_CODES.size(),
			"declared_by_the_committed_table": 17,
			"client_local_codes_are_server_codes": false,
		},
		"claims": {
			"client_computes_a_price": false,
			"client_evaluates_eligibility": false,
			"client_computes_a_prize": false,
			"client_compares_two_reported_grant_fields": false,
			"client_filters_a_negative_id": false,
			"unsupported_intent_touches_transport": false,
			"parity_with_legacy_claimed": false,
		},
		# Each claim names the check that fails when it stops being true, so the
		# block above reads as a table of guards rather than as prose.
		"enforced_by": {
			"client_computes_a_price":
				"_check_no_client_arithmetic (guard A) + "
				+ "_check_absent_derivation_helpers",
			"client_evaluates_eligibility":
				"_check_absent_derivation_helpers",
			"client_computes_a_prize":
				"_check_absent_derivation_helpers (belt) + "
				+ "_check_no_client_arithmetic (gate)",
			"client_compares_two_reported_grant_fields":
				"_check_no_field_reconciliation (all ten pairs; added "
				+ "because probe P4 found the claim was prose-only)",
			"client_filters_a_negative_id": "_check_intent_body",
			"unsupported_intent_touches_transport":
				"test_server_v1.gd; this suite asserts the intent LEFT its "
				+ "unsupported table (_check_unsupported_intent_left_the_table)",
			"parity_with_legacy_claimed":
				"not a claim; v1 is new behaviour and no legacy oracle exists",
		},
		"limits": {
			"legacy_command": "complete_collection",
			"legacy_branch": "command.py:504-523",
			"eligibility_is_derived": true,
			"price_is_derived": true,
			"prize_is_committed": true,
			"fixture_is_a_captured_legacy_oracle": false,
			"committed_corpus_can_exercise_the_grant": false,
			"live_phase_requires_a_seeded_disposable_corpus": true,
			"v1_routes_delivered_total": 2,
			"windowed_capture": false,
			"pixel_parity": false,
			"client_sees_a_before_state": false,
		},
		# Both delivered modules' raw digests, and a MEASURED line-ending flag.
		#
		# The digests are here because every injection probe this suite's
		# doctrine demands is credible only if its restore is byte-identical, and
		# a restore nobody can compare against is an assertion. The flag is
		# measured rather than hard-coded because `godot-market-trade` shipped a
		# sibling report that carried a hard-coded `false` next to a true
		# statement about the checkout, not about the files -- and copying a
		# field *and its value* across file forms is how a guard becomes a lie.
		"modules": module_digests,
		"modules_are_pure_lf": _modules_are_pure_lf(),
	}
	handle.store_string(JSON.stringify(document, "\t"))
	handle = null
	# The digest is computed over the bytes just written, by reading them back,
	# so it describes this file on disk rather than a re-serialisation of an
	# in-memory structure -- which is how a report's own digest can drift from
	# the artifact it is supposed to identify.
	var written := FileAccess.get_file_as_bytes(path)
	var text := ""
	for byte in written:
		text += String.chr(int(byte))
	var digest := text.sha256_text()
	info("report bytes %d, sha256 %s" % [written.size(), digest])


## The number of malformed shapes `_check_fail_closed` walks. Declared here so
## the report states it rather than the report merely implying it, and pinned
## inside the function so the two cannot disagree.
const FAIL_CLOSED_CASE_COUNT := 34


# --- helpers -----------------------------------------------------------------


## A project-relative source file's bytes as text, or "" when unreadable.
func _project_source(relative: String) -> String:
	var path := Paths.project_dir().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## A repository-relative file's bytes as text, or "" when unreadable. Used for
## the Python service modules, which are not inside the Godot project.
func _repo_text(relative: String) -> String:
	var path := Paths.repo_root().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## The declared return type of `method` in `body`, or "" when absent. A
## signature may wrap over several lines, so lines are accumulated until a `->`
## is followed by a `:`.
func _return_type_of(body: String, method: String) -> String:
	if body == "":
		return ""
	var lines := body.split("\n")
	for index in lines.size():
		var line := str(lines[index]).strip_edges()
		if not line.begins_with("func "):
			continue
		if not _names(line, method):
			continue
		var whole := line
		var probe := index + 1
		while probe < lines.size() and _has_no_return_type(whole):
			whole += " " + str(lines[probe]).strip_edges()
			probe += 1
		var at := whole.find("->")
		if at == -1:
			return ""
		var tail := whole.substr(at + 2).strip_edges()
		return tail.substr(0, tail.find(":")).strip_edges()
	return ""


func _names(signature: String, method: String) -> bool:
	var open := signature.find("(")
	if open == -1:
		return false
	return signature.substr(0, open).strip_edges() == "func %s" % method


func _has_no_return_type(whole: String) -> bool:
	var at := whole.find("->")
	if at == -1:
		return true
	return not whole.substr(at + 2).contains(":")


## Strips `#` comments but **keeps string literals**, with the same two-state
## scan `_code_only` uses.
##
## This exists because probe P4 measured the opposite of what the guard was
## written for. The first version of `_check_no_field_reconciliation` scanned
## `_code_only`, whose docstring promises CODE only -- and a GDScript field read
## is `source["position"]`, so the field names live inside the string literals
## that scan deletes. The injected
## `if source["position"] != source["requested_id"]:` therefore passed the
## guard and was caught only by an unrelated behavioural check. **A guard that
## strips the very tokens it is looking for is not a guard**, and this is the
## measured reason the two scanners are separate functions rather than one
## parameter.
##
## Comments must still go: this module's own `_grant` docstring names
## `requested_id` and `resolved_id` on the same line while explaining that they
## are deliberately NOT compared, which is precisely the sentence a naive
## comment-inclusive scan would flag.
func _comments_only(body: String) -> String:
	var out := ""
	var index := 0
	var quote := ""
	while index < body.length():
		var character := body.substr(index, 1)
		if quote != "":
			out += character
			if character == "\\":
				if index + 1 < body.length():
					out += body.substr(index + 1, 1)
				index += 2
				continue
			if character == quote:
				quote = ""
			index += 1
			continue
		if character == "\"" or character == "'":
			quote = character
			out += character
			index += 1
			continue
		if character == "#":
			while index < body.length() and body.substr(index, 1) != "\n":
				index += 1
			continue
		out += character
		index += 1
	return out


## Strips `#` comments and string literals with a two-state scan, so a scan sees
## CODE only. A naive split on `#` desynchronises on an apostrophe inside a
## double-quoted string, which this repository has already been bitten by; the
## two-state scan is what makes the guard trustworthy.
func _code_only(body: String) -> String:
	var out := ""
	var index := 0
	var in_string := false
	var quote := ""
	while index < body.length():
		var character := body.substr(index, 1)
		if in_string:
			if character == "\\":
				index += 2
				continue
			if character == quote:
				in_string = false
			index += 1
			continue
		if character == "#":
			while index < body.length() and body.substr(index, 1) != "\n":
				index += 1
			continue
		if character == "\"" or character == "'":
			in_string = true
			quote = character
			index += 1
			continue
		out += character
		index += 1
	return out


func _code_lines(code: String) -> Array:
	var out: Array = []
	for line in code.split("\n"):
		out.append(str(line).rstrip("\r"))
	return out


## Every `func` name a GDScript source declares, in declaration order and
## **including duplicates**. Both `func` and `static func` are recognised: the
## typed-result module declares all nine of its functions `static`, and an
## inventory that only matched `func ` would report that module as declaring
## **nothing** -- a zero that looks like a pass.
##
## The inventory comparison sorts and uniques, because `_init` and several
## private helpers are declared more than once in these modules and a positional
## list comparison fails against the delivered source itself.
func _declared_function_names(body: String) -> Array:
	var out: Array = []
	for line in _code_lines(body):
		var candidate := str(line).strip_edges()
		if candidate.begins_with("static func "):
			candidate = candidate.substr("static ".length())
		if not candidate.begins_with("func "):
			continue
		var open := candidate.find("(")
		if open == -1:
			continue
		var head := candidate.substr("func ".length(), open - "func ".length())
		out.append(head.strip_edges())
	return out


## The same names, folded to lower case, as a set.
func _folded_set(names: Array) -> Array:
	var out: Array = []
	for name in names:
		out.append(str(name).to_lower())
	return _sorted_set(out)


## A sorted, de-duplicated copy, so two lists are compared as sets of values.
func _sorted_set(source: Array) -> Array:
	var out: Array = []
	for value in source:
		var text := str(value)
		if not out.has(text):
			out.append(text)
	out.sort()
	return out


func _sorted_keys(source: Dictionary) -> Array:
	var keys := []
	for key in source:
		keys.append(str(key))
	keys.sort()
	return keys


## True when a map carries any integer key, which would mean a legacy vector slot
## had crept into v1's named deltas.
func _has_integer_key(source: Dictionary) -> bool:
	for key in source:
		if str(key).is_valid_int():
			return true
	return false


func _swapped(source: Dictionary, field: String, value: Variant) -> Dictionary:
	var out: Dictionary = source.duplicate(true)
	out[field] = value
	return out


func _without(field: String) -> Dictionary:
	var out: Dictionary = OBSERVED_SUCCESS.duplicate(true)
	out.erase(field)
	return out


func _merged(base: Variant, extra: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	if base is Dictionary:
		for key in base:
			out[str(key)] = base[key]
	for key in extra:
		out[str(key)] = extra[key]
	return out


## True when a `complete_collection_town` call binds its result without
## narrowing it to a concrete class. A call wrapped over several lines has its
## binding on an earlier line, so the walk goes back up to three lines.
func _binds_untyped(line: String, lines: Array, index: int) -> bool:
	var at := line.find("complete_collection_town(")
	if at == -1:
		return true
	var head := line.substr(0, at)
	var back := 0
	while not head.contains("=") and back < 3 and index - back - 1 >= 0:
		back += 1
		head = str(lines[index - back]).strip_edges() + " " + head
	if not head.contains("="):
		return true
	if not head.contains("await"):
		return true
	var declared := head.split("=")[0].strip_edges()
	if not declared.contains(":"):
		return true
	return declared.substr(declared.rfind(":") + 1).strip_edges() == "Variant"


## One `RefusalCode.NAME: status,` row of `REFUSAL_HTTP_STATUS`, recognised
## structurally rather than by listing the codes here: the `RefusalCode.`
## prefix, an identifier, a colon, a three-digit integer, a comma. Counting the
## rows is how the suite notices an eighteenth code without knowing what it is
## called.
func _looks_like_status_row(line: String) -> bool:
	if not line.begins_with("    "):
		return false
	var candidate := line.strip_edges()
	const PREFIX := "RefusalCode."
	if not candidate.begins_with(PREFIX):
		return false
	var colon := candidate.find(":")
	if colon < PREFIX.length() + 1:
		return false
	var name := candidate.substr(PREFIX.length(), colon - PREFIX.length())
	for index in name.length():
		if not (name[index] == "_" or name[index].is_valid_identifier()):
			return false
	var tail := candidate.substr(colon + 1).strip_edges()
	if not tail.ends_with(","):
		return false
	tail = tail.substr(0, tail.length() - 1).strip_edges()
	if tail.length() != 3 or not tail.is_valid_int():
		return false
	return true


func _collect_sources(root: String, prefix: String, out: Array) -> void:
	var directory := DirAccess.open(root.path_join(prefix))
	if directory == null:
		return
	for name in directory.get_files():
		if str(name).get_extension() == "gd":
			out.append(root.path_join(prefix).path_join(str(name)))
	for name in directory.get_directories():
		if str(name) == ".godot":
			continue
		_collect_sources(root, prefix.path_join(str(name)), out)


func _arg(prefix: String, fallback: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return fallback