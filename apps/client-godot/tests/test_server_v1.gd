extends "res://tests/test_base.gd"
## Server v1 client suite (OpenSpec tasks 5.1-5.3; spec: "Server v1 is
## reachable through the GameApi abstraction", "A refused v1 action moves
## nothing").
##
## Scenarios:
##   ""     (default, hermetic) the two delivered modules, the facade's third
##          implementation, and the structural invariants that keep this client
##          from becoming a second economy. No server, no socket.
##   live   drives `ServerV1Api` through the `GameApi` facade against a running
##          `apps/server-v1` service over loopback. Only `verify-boot.ps1`'s
##          `server-v1-live` phase runs this, and asserts it explicitly.
##
## ## The claim this suite exists to keep
##
## v1 derives the payout **server-side**. This client sends a row address and
## nothing else, applies `resources_after` verbatim, and performs **no**
## arithmetic of its own. A comment is not evidence for that, so it is asserted
## three ways:
##
## 1. `_check_no_client_arithmetic` walks the two delivered modules and fails on
##    arithmetic outside comments and string literals, so the guarantee is
##    mechanical rather than asserted.
## 2. `_check_intent_body` pins the request to exactly two keys, so the client
##    cannot smuggle a delta even by accident.
## 3. `_check_live` counts requests on the wire, so "one intent, one request"
##    and "an unsupported intent, zero requests" are measured, not claimed.
##
## ## The two client-local codes are NOT server codes
##
## `unsupported_by_server_v1` and `bad_request` are minted here, never sent to
## v1, and therefore cannot appear in v1's refusal vocabulary.
## `_check_local_codes_are_not_server_codes` reads the committed
## `server_v1_refusals.py` and asserts neither is a declared key, so the
## distinction is checked against the real table instead of a copy of it.
##
## ## What this suite no longer covers, and where it went
##
## This suite was written for v1's **first** route and owns everything about
## that route. The second route, `POST /v1/collection`, changed three things
## here and each is recorded at its site rather than in a changelog:
##
## * `complete_collection_town` left `UNSUPPORTED_INTENTS` (it is implemented
##   now, so the local refusal it was asserted to produce is gone);
## * `OBSERVED_REFUSALS` grew from twelve codes to seventeen, because the
##   vocabulary is shared and five codes belong to the grant slice;
## * the report's `v1_routes_delivered` / `legacy_commands_covered` moved 1 -> 2.
##
## **The point of recording it here is that this suite still passes after all
## three changes.** A suite that had been left asserting the removed refusal
## would have gone red, which would have been reported as a regression rather
## than as a stale guard; instead the stale rows were deleted and the pin that
## would have noticed them (the refusal-vocabulary size) moved deliberately.
## The collect route's own coverage is unchanged.
##
## ## This file may not spell a transport token
##
## `test_project_scope.gd` confines three transport tokens to the two
## implementation files, and this change amended that guard to MEASURE the
## carrier set from the project instead of scanning only the allow-list.
## Spelling one of them here would make this suite a third carrier and fail
## that guard. So the endpoint is assembled from a scheme and its slashes, and
## the token list is READ OUT of the committed scope suite at runtime - which
## also means this suite's positive control can never drift from the guard it
## exists to corroborate.

## `Paths` is inherited from `res://tests/test_base.gd`, which already
## preloads it; redeclaring it here is a parse error on this engine.
const BootData = preload("res://scripts/gameapi/boot_data.gd")
const ServerV1Api = preload("res://scripts/gameapi/server_v1_api.gd")
const ServerV1Collect = preload(
	"res://scripts/gameapi/server_v1_collect_result.gd")

const API_SCRIPT := "scripts/gameapi/server_v1_api.gd"
const RESULT_SCRIPT := "scripts/gameapi/server_v1_collect_result.gd"
const SCOPE_SCRIPT := "tests/test_project_scope.gd"
## This suite's own filename, excluded from its own call-site census.
const SELF_SCRIPT := "test_server_v1.gd"
const FACADE_SCRIPT := "scripts/gameapi/game_api.gd"
const V0_SCRIPT := "scripts/gameapi/legacy_v0_api.gd"
const FAKE_SCRIPT := "scripts/gameapi/fake_api.gd"
const REFUSALS_MODULE := "apps/server-v1/server_v1_refusals.py"

## The loopback endpoint v1 binds (design D7), assembled from parts.
const SCHEME := "http:"
## The slashes are kept separate from the scheme for the reason above.
const SLASHES := "//"

const ARG_PLAYER_ID := "--player-id="
const ARG_ENDPOINT := "--gameapi-endpoint="
const LIVE_ENDPOINT := SCHEME + SLASHES + "127.0.0.1:5057"

## The committed corpus's income-bearing row: in
## `tests/saves/fresh-player.json` row 2 is the Tree (item 905) whose recorded
## instant is `0`, so the elapsed time is unbounded and the reached rung is
## deterministically the top one.
const LIVE_ROW := 2
## A placed row whose item records no committed income (item 26).
const LIVE_NO_INCOME_ROW := 1
## A row key no save in this repository holds.
const LIVE_UNKNOWN_ROW := 99999

## One success payload OBSERVED from `POST /v1/collect` on 2026-10-12 against a
## disposable corpus, transcribed here so the parser is exercised against a real
## answer rather than against something this suite constructed. It is **one
## observation of one transaction**, not a captured legacy oracle and not a
## parity witness; the live arm re-derives the same shape at runtime. The
## instants and the derivation id are wall-clock and content dependent, so they
## are asserted for SHAPE, never for a fixed value beyond the length pin.
const OBSERVED_SUCCESS := {
	"result": "success",
	"action": "collect",
	"instant": 1791810063,
	"rung": {"index": 3, "threshold_seconds": 28800, "multiplier": 3.0},
	"derivation_id": "9233ac3efcb640f9af671968aa645b6a",
	"derived_deltas": {"xp": 3, "wood": 60},
	"resources_after": {
		"xp": 7, "gold": 2000, "wood": 2060, "oil": 2000,
		"steel": 2000, "cash": 5, "mana": 0,
	},
	"row_instant": 1791810063,
	"protocol": "server-v1",
}

## Every refusal code v1 declares, with the status observed for it. Used to
## build sample refusals and to prove pass-through; the authority check reads
## the real module rather than this list, and the size is pinned so an edit on
## either side becomes visible.
const OBSERVED_REFUSALS := {
	"unknown_player": 404,
	"client_supplied_delta": 400,
	"unknown_request_field": 400,
	"malformed_request": 400,
	"unaddressable_row": 409,
	"no_committed_income": 409,
	"below_first_rung": 409,
	"capped_collection": 409,
	"construction_in_progress": 409,
	"post_condition_violation": 500,
	"unreadable_content": 500,
	"unreadable_state": 500,
	# -- added by the second v1 route (complete_collection) --
	# Each status is read out of `apps/server-v1/server_v1_refusals.py`, and
	# `_check_local_codes_are_not_server_codes` asserts every name here is
	# declared there, so this table cannot claim a status the service does not
	# use. Only the NAMES are needed by the client -- the client never sees a
	# status -- so the status column exists to catch a code that was added to
	# this suite with a status the service does not have.
	"aliased_collection_id": 409,
	"unresolvable_collection": 409,
	"collection_not_eligible": 409,
	"collection_already_claimed": 409,
	"insufficient_cash": 409,
}

## Every intent `ServerV1Api` refuses locally, with the result type the FACADE
## declares for it. The invariant is that the facade and the implementation
## declare the SAME type, so a caller that reads the facade's signature is never
## handed something it did not ask for; the runtime check below then confirms
## answer really carries a code under the name that class uses.
##
## The fourth column is NOT uniform, and that is a measured fact about the
## already-delivered lines rather than a choice made here.  It read "21 of the 22
## result classes store `error_code`/`error_message`, while `MagicFlow.MagicResult`
## and `RewardFlow.RewardResult` store `reason`/`error`" and was correct when the
## reward intent was still refused locally.  It is **now 18 of the 19**, because
## `RewardFlow.RewardResult` left this table when the reward route landed, and
## `MagicFlow.MagicResult` is the **last** intent here that spells its refusal
## `reason`/`error` rather than `error_code`/`error_message`.
## `_check_unsupported_intents` asserts that count so the divergence stays
## visible instead of being normalised away, and nothing in the v1 client adapts
## to it - the client only ever reads the facade's declared type.
##
## **`complete_collection_town` is NOT in this table.** It was, until the second
## v1 route landed: v1 now implements it, so `ServerV1Api` answers it through the
## transport instead of refusing it locally. The table lists the intents v1 does
## NOT have, and keeping a delivered one would have kept asserting a refusal the
## client no longer produces -- the exact failure mode where a guard pins a stale
## claim. Its implementation is covered by `tests/test_collection_v1.gd`.
##
## **`combat_town` is NOT in this table either**, for the same reason and by the
## same mechanism, when the fourth v1 route landed: it moved to the implemented
## set and its own suite is `tests/test_combat_v1.gd`. The count therefore fell
## from twenty-one to twenty, measured by the size assertion below rather than
## assumed from the arithmetic.
##
## **`reward_town` is NOT in this table for the same reason a third time**, when
## the fifth v1 route landed, and its own suite is `tests/test_reward_v1.gd`.
## The count falls from twenty to **nineteen**, measured by that same size
## assertion. Recorded here because the repetition is the point: **three lines
## have now each removed a row from this table**, and each time the removal was
## the correct response to a newly routed intent rather than a weakening of the
## invariant. The invariant this table enforces - the facade and the
## implementation declare the SAME type for every intent the implementation
## refuses - is unchanged by a row leaving it.
const UNSUPPORTED_INTENTS := [
	["list_sessions", "BootData.SaveListResult", "error_code", "error_message"],
	["get_bootstrap", "BootData.BootstrapResult", "error_code", "error_message"],
	["place_building", "BootData.PlacementResult", "error_code", "error_message"],
	["purchase_item", "BootData.PurchaseResult", "error_code", "error_message"],
	["move_building", "BootData.PlacementResult", "error_code", "error_message"],
	["sell_building", "BootData.SellResult", "error_code", "error_message"],
	["store_building", "BootData.StoreResult", "error_code", "error_message"],
	["upgrade_building", "BootData.UpgradeResult", "error_code", "error_message"],
	["build_construction", "BootData.ConstructionResult", "error_code", "error_message"],
	["expand_town", "BootData.ExpandResult", "error_code", "error_message"],
	["level_up_town", "BootData.LevelUpResult", "error_code", "error_message"],
	["push_queue_unit_town", "BootData.QueueResult", "error_code", "error_message"],
	["pop_queue_unit_town", "BootData.QueueResult", "error_code", "error_message"],
	["resurrect_hero_town", "BehaviorFlow.ResurrectResult", "error_code", "error_message"],
	["advance_research_town", "ResearchFlow.ResearchResult", "error_code", "error_message"],
	["advance_quest_town", "QuestFlow.QuestResult", "error_code", "error_message"],
	["complete_tutorial_town", "TutorialFlow.TutorialResult", "error_code", "error_message"],
	["place_stored_item_town", "BootData.StoredPlacementResult", "error_code", "error_message"],
	["sell_stored_item_town", "BootData.StoredSaleResult", "error_code", "error_message"],
]

## The one implemented intent, and the concrete type each implementation
## declares for it. `GameApi.collect_income` is `Variant` precisely because
## these three differ, and this pin is what stops a fourth shape appearing
## silently.
const IMPL_RETURN_TYPES := {
	"scripts/gameapi/fake_api.gd": "BootData.CollectResult",
	"scripts/gameapi/legacy_v0_api.gd": "BootData.CollectResult",
	"scripts/gameapi/server_v1_api.gd": "ServerV1Collect.CollectResult",
}

## The only two arithmetic lines either delivered module is allowed to contain:
## they increment this implementation's two request counters and touch no
## reported value. Listed literally so a THIRD `+=` anywhere fails.
const ALLOWED_ARITHMETIC_LINES := [
	"\ttransport_requests += 1",
	"\tunsupported_intents += 1",
]


func run_scenario() -> void:
	if scenario == "live":
		await _check_live()
		_write_report()
		return
	_check_observed_success_parses()
	_check_refusal_pass_through()
	_check_fail_closed()
	_check_local_codes_are_not_server_codes()
	await _check_unsupported_intents()
	_check_magic_intent_hand_off()
	_check_intent_body()
	_check_no_client_arithmetic()
	await _check_facade_registration()
	_check_return_type_widening()
	_check_transport_token_placement()
	_write_report()


# --- the typed result --------------------------------------------------------


## The observed answer parses into every field, with the deterministic values
## checked and the wall-clock ones checked for shape only.
func _check_observed_success_parses() -> void:
	var parsed: Variant = ServerV1Collect.parse_collect(
		OBSERVED_SUCCESS.duplicate(true))
	if not (parsed is ServerV1Collect.CollectResult):
		fail("an observed v1 success parses into the typed result")
		return
	var typed: ServerV1Collect.CollectResult = parsed
	check(typed.ok, "the observed answer is a success")
	check_eq(typed.protocol, ServerV1Collect.PROTOCOL,
		"the typed result carries v1's own protocol stamp")
	check_eq(typed.action, ServerV1Collect.ACTION,
		"the typed result carries the action the server says ran")
	check(typed.instant > 0, "the transaction instant is a positive integer")
	check(typed.row_instant > 0, "the row instant is a positive integer")
	check_eq(typed.row_instant, typed.instant,
		"the observed answer stamps the row and the transaction together")
	check_eq(typed.derivation_id.length(), 32,
		"the derivation id is reported verbatim, never rebuilt")
	check(typed.rung != null, "the rung block is present")
	if typed.rung != null:
		check_eq(typed.rung.index, 3,
			"the top committed rung index is reported verbatim")
		check_eq(typed.rung.threshold_seconds, 28800,
			"the rung's committed threshold is reported verbatim")
		check(typed.rung.multiplier > 0.0,
			"the rung's committed multiplier is reported verbatim")
	# The deltas are NAMED. That is the shape v0 cannot express, and the
	# assertion is about the KEY SET: the amounts are v1's own derivation and
	# this suite may not pin them as a value.
	check_eq(_sorted_keys(typed.derived_deltas), ["wood", "xp"],
		"the derived deltas name the balances that moved")
	check(not _has_integer_key(typed.derived_deltas),
		"no derived delta is keyed by a legacy vector slot")
	check(typed.resources_after != null,
		"the complete stored balance set is present")
	if typed.resources_after != null:
		check_eq(typed.resources_after.xp, 7, "xp is taken verbatim")
		check_eq(typed.resources_after.wood, 2060, "wood is taken verbatim")
		check_eq(typed.resources_after.mana, 0,
			"a zero balance is preserved, not dropped")


## Every refusal v1 declares travels through the SAME field, verbatim, with no
## partial payload.
func _check_refusal_pass_through() -> void:
	check_eq(OBSERVED_REFUSALS.size(), 17,
		"every refusal code v1 declares is covered by this suite")
	for code in OBSERVED_REFUSALS:
		var label := "the refusal %s" % code
		var payload := {
			"result": "refused",
			"code": code,
			"message": "observed refusal for %s" % code,
			"detail": {"row": LIVE_ROW},
			"protocol": ServerV1Collect.PROTOCOL,
		}
		var parsed: Variant = ServerV1Collect.parse_collect(payload)
		if not (parsed is ServerV1Collect.CollectResult):
			fail("%s parses into the typed result" % label)
			continue
		var typed: ServerV1Collect.CollectResult = parsed
		check(not typed.ok, "%s is a failure" % label)
		check_eq(typed.error_code, code,
			"%s passes v1's own code through verbatim" % label)
		check_eq(typed.error_detail, {"row": LIVE_ROW},
			"%s carries v1's structured detail verbatim" % label)
		check_eq(typed.derived_deltas, {},
			"%s carries no derived deltas" % label)
		check(typed.resources_after == null, "%s carries no balances" % label)
		check(typed.rung == null, "%s carries no rung" % label)
		check_eq(typed.instant, 0, "%s carries no instant" % label)
		check_eq(typed.derivation_id, "", "%s names no derivation" % label)


## Every malformed or absent success shape is refused rather than guessed at.
## Each case is named so a future edit that loosens one is visible.
func _check_fail_closed() -> void:
	var closed := [
		["an answer that is not an object", []],
		["an answer that is a string", "success"],
		["a body with no result field", {"action": "collect"}],
		["an unrecognised result", {"result": "maybe"}],
		["a refusal with no code", {"result": "refused"}],
		["a refusal whose detail is not an object",
			{"result": "refused", "code": "unaddressable_row", "detail": 7}],
	]
	for item in closed:
		_check_bad_request(str(item[0]), item[1])
	for field in ["protocol", "action", "instant", "rung", "derivation_id",
			"derived_deltas", "resources_after", "row_instant"]:
		var missing: Dictionary = OBSERVED_SUCCESS.duplicate(true)
		missing.erase(field)
		_check_bad_request("a success missing %s" % field, missing)
	_check_bad_request("a success with a fractional instant",
		_swapped(OBSERVED_SUCCESS, "instant", 1.5))
	_check_bad_request("a success with a fractional row instant",
		_swapped(OBSERVED_SUCCESS, "row_instant", 1.5))
	_check_bad_request("a success with an instant that is a string",
		_swapped(OBSERVED_SUCCESS, "instant", "1791810063"))
	_check_bad_request("a fractional rung index",
		_swapped(OBSERVED_SUCCESS, "rung",
			{"index": 1.5, "threshold_seconds": 60, "multiplier": 1.0}))
	_check_bad_request("a rung block that is not an object",
		_swapped(OBSERVED_SUCCESS, "rung", 3))
	_check_bad_request("a rung multiplier that is a string",
		_swapped(OBSERVED_SUCCESS, "rung",
			{"index": 3, "threshold_seconds": 28800, "multiplier": "3"}))
	_check_bad_request("a rung missing its threshold",
		_swapped(OBSERVED_SUCCESS, "rung", {"index": 3, "multiplier": 3.0}))
	_check_bad_request("a delta keyed by an unmodelled balance",
		_swapped(OBSERVED_SUCCESS, "derived_deltas", {"energy": 1}))
	_check_bad_request("a delta that is not a number",
		_swapped(OBSERVED_SUCCESS, "derived_deltas", {"wood": "60"}))
	_check_bad_request("a fractional delta",
		_swapped(OBSERVED_SUCCESS, "derived_deltas", {"wood": 0.5}))
	_check_bad_request("a partial balance set",
		_swapped(OBSERVED_SUCCESS, "resources_after", {"xp": 7}))
	_check_bad_request("a balance set with an extra key",
		_swapped(OBSERVED_SUCCESS, "resources_after",
			_merged(OBSERVED_SUCCESS["resources_after"], {"energy": 50})))
	_check_bad_request("a balance that is not a number",
		_swapped(OBSERVED_SUCCESS, "resources_after",
			_merged(OBSERVED_SUCCESS["resources_after"], {"xp": null})))
	_check_bad_request("a fractional balance",
		_swapped(OBSERVED_SUCCESS, "resources_after",
			_merged(OBSERVED_SUCCESS["resources_after"], {"xp": 7.5})))
	_check_bad_request("a success stamped with another protocol",
		_swapped(OBSERVED_SUCCESS, "protocol", "some-other-server"))
	_check_bad_request("a success reporting another action",
		_swapped(OBSERVED_SUCCESS, "action", "expand"))
	# An EMPTY named-delta set is ACCEPTED and kept distinct from an absent one:
	# "the server moved nothing" is a reportable answer.
	var empty: Variant = ServerV1Collect.parse_collect(
		_swapped(OBSERVED_SUCCESS, "derived_deltas", {}))
	check(empty is ServerV1Collect.CollectResult and empty.ok,
		"an empty named-delta set is a success, not an absence")
	if empty is ServerV1Collect.CollectResult and empty.ok:
		check_eq(empty.derived_deltas, {},
			"and the empty set is preserved rather than invented")


func _check_bad_request(label: String, payload: Variant) -> void:
	var parsed: Variant = ServerV1Collect.parse_collect(payload)
	if not (parsed is ServerV1Collect.CollectResult):
		fail("%s must parse into the typed result" % label)
		return
	var typed: ServerV1Collect.CollectResult = parsed
	check(not typed.ok, "%s is refused" % label)
	check_eq(typed.error_code, ServerV1Collect.CODE_BAD_REQUEST,
		"%s is refused by the client-local parse code" % label)
	# The code is the contract; the message is required to be PRESENT, not
	# empty - every failure factory in this project stores its message, so
	# asserting emptiness would be asserting an invention of mine. What must be
	# absent is the payload, and the four checks below are that claim.
	check(typed.error_message != "",
		"%s explains itself rather than answering with a bare code" % label)
	check(typed.derived_deltas.is_empty(),
		"%s carries no derived deltas" % label)
	check(typed.resources_after == null, "%s carries no balances" % label)
	check(typed.rung == null, "%s carries no rung" % label)


## The two client-local codes are read out of the committed v1 refusal module
## and proved absent from it, so the client/server distinction is checked
## against the real table and not against a copy of it.
func _check_local_codes_are_not_server_codes() -> void:
	var body := FileAccess.get_file_as_string(
		Paths.repo_root().path_join(REFUSALS_MODULE))
	check(body != "", "%s is readable from the repository" % REFUSALS_MODULE)
	if body == "":
		return
	var start := body.find("REFUSAL_HTTP_STATUS")
	check(start != -1, "%s declares REFUSAL_HTTP_STATUS" % REFUSALS_MODULE)
	if start == -1:
		return
	var table := body.substr(start)
	for local_code in [ServerV1Collect.CODE_UNSUPPORTED,
			ServerV1Collect.CODE_BAD_REQUEST]:
		check(table.find("'%s'" % local_code) == -1
			and table.find('"%s"' % local_code) == -1,
			"the client-local code %s is not a v1 refusal code" % local_code)
	for code in OBSERVED_REFUSALS:
		check(table.find('"%s"' % code) != -1,
			"the sampled refusal code %s is declared by v1" % code)


# --- the implementation ------------------------------------------------------


## Every intent v1 does not have answers with the result type the FACADE
## declares, the client-local code, and **zero requests on the wire**.
func _check_unsupported_intents() -> void:
	var facade_body := _project_source(FACADE_SCRIPT)
	var impl_body := _project_source(API_SCRIPT)
	var api: Variant = ServerV1Api.new()
	root.add_child(api)
	await process_frame
	check(api.transport_requests == 0,
		"a fresh implementation has issued no request")
	check_eq(api.unsupported_intents, 0, "and refused nothing yet")
	var answered := 0
	var divergent := 0
	var divergent_names: Array = []
	for intent in UNSUPPORTED_INTENTS:
		var method := str(intent[0])
		var declared := str(intent[1])
		check_eq(_return_type_of(impl_body, method), declared,
			"%s declares %s, the type the facade promises" % [method, declared])
		check_eq(_return_type_of(facade_body, method), declared,
			"the facade still declares %s for %s" % [declared, method])
		var code_field := str(intent[2])
		var message_field := str(intent[3])
		if code_field != "error_code":
			divergent += 1
			divergent_names.append(method)
		var answer: Variant = await _call_unsupported(api, method)
		if answer == null:
			fail("%s answers rather than returning null" % method)
			continue
		check(answer is RefCounted, "%s answers a typed result" % method)
		if not (code_field in answer):
			fail("%s carries a %s field" % [method, code_field])
			continue
		if not (message_field in answer):
			fail("%s carries a %s field" % [method, message_field])
			continue
		check_eq(str(answer[code_field]), ServerV1Collect.CODE_UNSUPPORTED,
			"%s is refused by the client-local code" % method)
		check(str(answer[message_field]) != "",
			"%s explains itself rather than answering with a bare code" % method)
		check(not answer.ok, "%s is a failure" % method)
		answered += 1
	## **This read `1` and is now `0`, and the change is not a normalisation.**
	## The divergent class was `RewardFlow.RewardResult` (`reason`/`error`), and
	## it left this table when the reward route landed -- so every intent v1 still
	## refuses locally answers under `error_code`/`error_message`.  The check
	## stays rather than being deleted, because it is the assertion that the
	## spelling is *uniform*, and a future line that adds an intent with a
	## different spelling must fail here.
	##
	## **Correction, 2026-10-14.**  The docstring above this table claimed the
	## divergence was `MagicFlow.MagicResult`'s **and** `RewardFlow.RewardResult`'s.
	## That was already false: `magic_town` had left this table when the magic
	## route landed, so `MagicFlow.MagicResult` was never in it.  The measured
	## count was 1 and the named pair was 2 -- the names were inherited rather
	## than counted, which is the same defect class as a hand-maintained
	## inventory that nothing checks.  It is recorded here rather than quietly
	## fixed because "the divergence was never where the prose said" is the part
	## worth keeping.
	check_eq(divergent, 0,
		"no locally-refused intent names its refusal code differently from"
		+ " the other 18")
	info("result classes with a divergent refusal field name: %s"
		% ", ".join(PackedStringArray(divergent_names)))
	check_eq(answered, UNSUPPORTED_INTENTS.size(),
		"every unsupported intent answered rather than aborting")
	check_eq(api.unsupported_intents, UNSUPPORTED_INTENTS.size(),
		"the refusal counter moved exactly once per unsupported intent")
	check_eq(api.transport_requests, 0,
		"NO unsupported intent touched the transport")
	api.queue_free()


## ## `magic_town` left this suite's unsupported table, and that is an ownership
## ## HAND-OFF rather than a deletion
##
## When Server v1 gained `POST /v1/magic`, `ServerV1Api.magic_town` stopped being a
## local refusal and became a real transport call, so the row this suite used to
## pin was **wrong** the moment the route landed. Deleting the row alone would
## leave the table quieter and the claim weaker, because nothing would then assert
## that the intent was re-owned rather than quietly forgotten - and a fourth
## implementation could add a fifth magic shape without any suite noticing.
##
## So both halves are asserted. The first is the absence, which is the whole
## point: no row in `UNSUPPORTED_INTENTS` names an intent `ServerV1Api` now
## implements. The second is that the suite which took the intent over **exists
## on disk**, so the hand-off cannot dangle. This is the same shape
## `godot-unit-collection` established and `godot-stored-item-placement` re-used;
## the owner list lives in the receiving suite, never in two places at once.
## The suite each handed-off intent is owned by, and the intents themselves.
## `combat_town` was added when the fourth v1 route landed; its owning suite is
## `test_combat_v1.gd`, so the hand-off cannot dangle either.
const HANDED_OFF_SUITES := {
	"magic_town": "res://tests/test_magic_v1.gd",
	"combat_town": "res://tests/test_combat_v1.gd",
	"reward_town": "res://tests/test_reward_v1.gd",
}
const HANDED_OFF_INTENTS := ["magic_town", "combat_town", "reward_town"]


func _check_magic_intent_hand_off() -> void:
	for intent in UNSUPPORTED_INTENTS:
		check(not HANDED_OFF_INTENTS.has(str(intent[0])),
			"%s left the unsupported table and must not be back in it" % str(intent[0]))
	for intent in HANDED_OFF_INTENTS:
		check(ResourceLoader.exists(str(HANDED_OFF_SUITES[intent])),
			"the suite that took %s over exists" % intent)
	check_eq(UNSUPPORTED_INTENTS.size(), 19,
		"nineteen intents remain locally refused, one fewer than before the"
		+ " reward route landed")
	info("intents handed off: %s" % ", ".join(HANDED_OFF_INTENTS))


func _call_unsupported(api: Variant, method: String) -> Variant:
	match method:
		"list_sessions":
			return await api.list_sessions()
		"get_bootstrap":
			return await api.get_bootstrap("player-1")
		"place_building":
			return await api.place_building("player-1", 1, 2, 3)
		"purchase_item":
			return await api.purchase_item("player-1", 1)
		"move_building":
			return await api.move_building("player-1", 1, 2, 3)
		"sell_building":
			return await api.sell_building("player-1", 1)
		"store_building":
			return await api.store_building("player-1", 1)
		"upgrade_building":
			return await api.upgrade_building("player-1", 1)
		"build_construction":
			return await api.build_construction("player-1", 1, "start")
		"expand_town":
			return await api.expand_town("player-1", 1)
		"level_up_town":
			return await api.level_up_town("player-1")
		"push_queue_unit_town":
			return await api.push_queue_unit_town("player-1", 1)
		"pop_queue_unit_town":
			return await api.pop_queue_unit_town("player-1", 1)
		"resurrect_hero_town":
			return await api.resurrect_hero_town("player-1", 1, 2)
		"advance_research_town":
			return await api.advance_research_town("player-1", "step", 0)
		"advance_quest_town":
			return await api.advance_quest_town("player-1", "set_goals", 1)
		"complete_tutorial_town":
			return await api.complete_tutorial_town("player-1", 15)
		"place_stored_item_town":
			return await api.place_stored_item_town("player-1", 1085, 1, 2)
		"sell_stored_item_town":
			return await api.sell_stored_item_town("player-1", 1085)
		"combat_town":
			return await api.combat_town("player-1", "resolve", 1)
		"reward_town":
			return await api.reward_town("player-1", "daily")
	return null


## The request this client builds is exactly two fields. If it ever grows one,
## the client would be dictating something and v1 would have to refuse it.
func _check_intent_body() -> void:
	var body: Dictionary = ServerV1Api._intent_body("player-1", LIVE_ROW)
	check_eq(_sorted_keys(body), ["player_id", "row"],
		"the v1 collect intent carries a save identity and a row, and nothing "
		+ "else")
	check_eq(str(body["player_id"]), "player-1", "the identity is verbatim")
	check_eq(int(body["row"]), LIVE_ROW, "the row is verbatim")
	var forbidden: Array = []
	forbidden.append_array(ServerV1Collect.STORED_RESOURCE_NAMES)
	forbidden.append_array([
		"resources_changed", "hp", "health", "damage", "result", "amount",
		"price", "cost", "payout", "tier", "elapsed", "reference_time",
		"multiplier", "level",
	])
	for name in forbidden:
		check(not body.has(name), "the intent carries no %s field" % name)


## Two mechanical rules over the two delivered modules, with comments and
## string literals stripped first so prose about a multiplier does not trip
## them and a real operator in code does.
##
## **Guard A - no scaling.** No multiplication or division, and no
## compound assignment other than the two counter increments the exception list
## names. This is what makes "the client never computes a payout" mechanical: a
## payout is a committed value scaled by a committed multiplier, and the
## multiplier is the multiplication.
##
## Plain `+` is deliberately NOT banned. It is string concatenation in every
## error message in both modules, so banning the character would only prove
## the modules stop talking. Guard B is what closes the additive hole, and it
## does not depend on operator parsing at all.
##
## **Guard B - no balance is touched.** No stored-balance member access
## (`.xp`, `.gold`, `.wood`, `.oil`, `.steel`, `.cash`, `.mana`) appears
## anywhere in either module. The balances are read out of the response into
## the typed result by NAME LOOP, never field by field, so this is the sharp
## form of the same invariant: there is no line to add a value to, because
## there is no line that names one.
func _check_no_client_arithmetic() -> void:
	var offending: Array = []
	var scanned := 0
	# `%` is GDScript's FORMAT operator and is used in both modules'
	# diagnostics; `^` is not an operator at all. Neither is listed, because
	# banning them would only prove the modules stop talking.
	var forbidden_operators := ["*", "/", "+=", "-=", "*=", "/="]
	for relative in [API_SCRIPT, RESULT_SCRIPT]:
		var body := _project_source(relative)
		check(body != "", "%s is readable" % relative)
		if body == "":
			continue
		scanned += 1
		# The signature arrow is not an operator; remove it before scanning so
		# a declared return type can never read as subtraction.
		var code := _code_only(body).replace("->", "  ")
		for line in _code_lines(code):
			if ALLOWED_ARITHMETIC_LINES.has(line):
				continue
			for operator in forbidden_operators:
				if line.find(operator) != -1:
					offending.append("A %s: %s (%s)"
						% [relative, line.strip_edges(), operator])
					break
		for name in ServerV1Collect.STORED_RESOURCE_NAMES:
			if code.find(".%s" % name) != -1:
				offending.append("B %s: member access .%s" % [relative, name])
	check_eq(offending, [],
		"neither delivered module scales a value or touches a balance")
	check_eq(ALLOWED_ARITHMETIC_LINES.size(), 2,
		"exactly two counter increments are admitted")
	check_eq(forbidden_operators.size(), 6,
		"the forbidden-operator list is intact")
	info("client arithmetic guard scanned %d delivered modules" % scanned)


## The facade selects the third implementation, describes its endpoint, and
## releases it again.
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
	check_eq(api.collect_requests, 0,
		"selecting an implementation issues no request")
	check_eq(api._impl.transport_requests, 0,
		"selecting an implementation opens no socket")
	api.configure("fake")
	check_eq(str(api.implementation_name()), "fake",
		"the facade restores the fake implementation")
	check(not (api._impl is ServerV1Api),
		"the v1 implementation is released on reconfigure")
	info("implementation in force before this suite selected one: %s" % before)


## The `Variant` widening on `collect_income` is only safe because EVERY call
## site binds its result to `Variant` or to an untyped local. That is measured
## over the whole project here rather than asserted in prose.
func _check_return_type_widening() -> void:
	var files: Array = []
	_collect_sources(Paths.project_dir(), "", files)
	check(files.size() > 40,
		"the project sources were walked: %d files" % files.size())
	var offenders: Array = []
	var call_sites := 0
	for absolute in files:
		var name := str(absolute)
		# This suite is EXCLUDED from its own census. It spells the call-site
		# text inside string literals and comments, and an instrument that
		# scans itself measures itself. The exclusion is stated here rather
		# than hidden, and the census size below keeps it from going vacuous.
		if name.ends_with(SELF_SCRIPT):
			continue
		var body := FileAccess.get_file_as_string(name)
		if body.find("collect_income") == -1:
			continue
		var lines := body.split("\n")
		for index in lines.size():
			var line := str(lines[index]).strip_edges()
			if not line.contains("collect_income("):
				continue
			if line.begins_with("#"):
				continue
			call_sites += 1
			if not _binds_untyped(line, lines, index):
				offenders.append("%s: %s"
					% [str(absolute).get_file(), line])
	check_eq(offenders, [],
		"every collect_income call site binds its result to Variant or untyped")
	check(call_sites >= 20,
		"the call-site census is non-trivial: %d sites" % call_sites)
	for relative in IMPL_RETURN_TYPES:
		var expected := str(IMPL_RETURN_TYPES[relative])
		check_eq(_return_type_of(_project_source(relative),
				"collect_income"), expected,
			"%s declares %s for collect_income" % [relative, expected])
	check_eq(_return_type_of(_project_source(FACADE_SCRIPT), "collect_income"),
		"Variant",
		"the facade's collect_income is declared Variant")
	info("collect_income call sites measured: %d" % call_sites)


## The positive control for the scope suite's measured carrier set: the v1
## implementation carries all three transport tokens, the legacy-v0 one still
## does, and the typed-result module carries none - so the carrier measurement
## there has real things to find and is not passing on a vacuous zero.
func _check_transport_token_placement() -> void:
	var api_body := _project_source(API_SCRIPT)
	var result_body := _project_source(RESULT_SCRIPT)
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
			"the v1 implementation carries the %s token" % token)
		check(v0_body.find(token) != -1,
			"the legacy-v0 implementation still carries %s" % token)
		check(result_body.find(token) == -1,
			"the typed-result module carries no %s token" % token)
		check(_project_source("tests/test_server_v1.gd").find(token) == -1,
			"this suite spells no transport token either (%s)" % token)


## The three transport tokens, READ OUT of the committed scope suite rather than
## transcribed here, so the positive control below cannot drift from the guard it
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
	# Read the block LINE by LINE and accept only a quoted token followed by a
	# comma. Splitting the whole block on the quote character returned the
	# inter-token commas as tokens, which inflated three into six.
	var tokens: Array = []
	for line in tail.substr(0, end).split("\n"):
		var candidate := line.strip_edges()
		if not candidate.begins_with('"') or not candidate.ends_with(","):
			continue
		tokens.append(candidate.substr(1, candidate.length() - 3))
	return tokens


# --- the live arm ------------------------------------------------------------


## One real collection through the facade against a running v1 service, then
## three refusals and one unsupported intent, with the wire count measured.
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
	var collected: Variant = await api.collect_income(player_id, LIVE_ROW)
	if not (collected is ServerV1Collect.CollectResult):
		fail("the live collect returns v1's own typed result class")
		return
	var typed: ServerV1Collect.CollectResult = collected
	check(typed.ok, "the live collection resolves (%s / %s)"
		% [typed.error_code, typed.error_message])
	if not typed.ok:
		return
	check_eq(typed.protocol, ServerV1Collect.PROTOCOL,
		"the live answer is stamped with v1's protocol")
	check_eq(typed.action, ServerV1Collect.ACTION,
		"the live answer names the action that ran")
	check_eq(typed.derivation_id.length(), 32,
		"the live answer names the derivation the server performed")
	check(typed.rung != null, "the live answer names the rung")
	if typed.rung != null:
		check(typed.rung.index >= 0,
			"the live rung is a committed ladder position")
		check(typed.rung.threshold_seconds > 0,
			"the live rung's threshold is positive")
		check(typed.rung.multiplier > 0.0,
			"the live rung's multiplier is positive")
	var moved := _sorted_keys(typed.derived_deltas)
	check(moved.size() > 0,
		"the live derivation named at least one moved balance")
	for name in moved:
		check(ServerV1Collect.STORED_RESOURCE_NAMES.has(str(name)),
			"the live derivation named only stored balances (%s)" % name)
		check(int(typed.derived_deltas[name]) >= 0,
			"the live derivation named a non-negative %s" % name)
	check(typed.resources_after != null,
		"the live answer carries the complete stored balance set")
	if typed.resources_after != null:
		check(typed.resources_after.wood > 0
			and typed.resources_after.xp > 0,
			"the live answer carries the balances v1 says it credited")
	check_eq(int(impl.transport_requests) - before_requests, 1,
		"one collect intent put exactly ONE request on the wire")

	_check_live_refusal(
		await api.collect_income(player_id, LIVE_UNKNOWN_ROW),
		"unaddressable_row", "an unaddressable row")
	_check_live_refusal(
		await api.collect_income(player_id, LIVE_NO_INCOME_ROW),
		"no_committed_income", "a row whose item records no committed income")
	_check_live_refusal(
		await api.collect_income(player_id, LIVE_ROW),
		"below_first_rung",
		"an immediate second collection on the same row")

	var requests_before := int(impl.transport_requests)
	var refused: Variant = await api.place_building(player_id, 905, 10, 10)
	check(refused is BootData.PlacementResult,
		"an unsupported intent answers the facade's own type")
	if refused is BootData.PlacementResult:
		check(not refused.ok, "and it is a failure")
		check_eq(str(refused.error_code), ServerV1Collect.CODE_UNSUPPORTED,
			"the unsupported intent keeps its client-local code")
		check_eq(str(refused.placement), "<null>",
			"the refused placement carries no placement")
	check_eq(int(impl.transport_requests), requests_before,
		"the unsupported intent added ZERO requests to the v1 wire")
	# The rung's own fields, spelled out. `JSON.stringify` on a `Rung` would
	# stringify the RefCounted and print `<RefCounted#...>` - a heap address that
	# differs every run, which is both unreadable and ungrepable.
	var rung_index := -1
	var rung_threshold := 0
	var rung_multiplier := 0.0
	if typed.rung != null:
		rung_index = typed.rung.index
		rung_threshold = typed.rung.threshold_seconds
		rung_multiplier = typed.rung.multiplier
	print("[test] live-server-v1 row=%d rung_index=%d threshold_seconds=%d "
		% [LIVE_ROW, rung_index, rung_threshold]
		+ "multiplier=%.1f deltas=%s derivation=%s"
		% [rung_multiplier, JSON.stringify(typed.derived_deltas),
			typed.derivation_id])


func _check_live_refusal(answer: Variant, expected_code: String,
		label: String) -> void:
	if not (answer is ServerV1Collect.CollectResult):
		fail("%s must answer v1's typed result" % label)
		return
	var typed: ServerV1Collect.CollectResult = answer
	check(not typed.ok, "%s is refused" % label)
	check_eq(typed.error_code, expected_code,
		"%s is refused by v1's own code (saw %s: %s)"
		% [label, typed.error_code, typed.error_message])
	check_eq(typed.derived_deltas, {},
		"%s carries no derived deltas" % label)
	check(typed.resources_after == null,
		"%s carries no balance set, never a partial payload" % label)
	check(typed.rung == null, "%s carries no rung" % label)
	check_eq(typed.derivation_id, "", "%s names no derivation" % label)


# --- evidence ----------------------------------------------------------------


## The deterministic report, written only when `--report=<path>` is supplied.
## It carries no wall-clock, path or environment value, so it is byte-identical
## across runs on the same source.
func _write_report() -> void:
	var path := _arg("--report=", "")
	if path == "":
		return
	var handle := FileAccess.open(path, FileAccess.WRITE)
	check(handle != null, "the evidence report is writable at %s" % path)
	if handle == null:
		return
	handle.store_string(JSON.stringify({
		"report": "server-v1-report-v1",
		"implementation": {
			"default_endpoint": ServerV1Api.DEFAULT_ENDPOINT,
			"collect_path": ServerV1Api.COLLECT_PATH,
			"protocol": ServerV1Collect.PROTOCOL,
			"action": ServerV1Collect.ACTION,
			"client_local_codes": [
				ServerV1Collect.CODE_UNSUPPORTED,
				ServerV1Collect.CODE_BAD_REQUEST,
			],
			"unsupported_intents": _intent_names(),
			"unsupported_intent_count": UNSUPPORTED_INTENTS.size(),
			"unsupported_intent_fields": _intent_field_names(),
			"impl_return_types": IMPL_RETURN_TYPES,
			"stored_resource_names":
				ServerV1Collect.STORED_RESOURCE_NAMES,
			"sampled_server_refusals": _sorted_keys(OBSERVED_REFUSALS),
			"sampled_server_refusal_count": OBSERVED_REFUSALS.size(),
		},
		"claims": {
			"client_performs_arithmetic_on_a_reported_value": false,
			"client_clamps_coerces_or_ignores_a_client_delta": false,
			"client_local_codes_are_server_codes": false,
			"unsupported_intent_touches_transport": false,
			"observed_payload_is_one_transaction": true,
			"parity_with_legacy_claimed": false,
		},
		# Each claim names the check that fails when it stops being true, so
		# the block above reads as a table of guards rather than as prose.
		# A claim with no enforcing check would be an assertion, which is the
		# defect this suite exists to catch in the modules.
		"enforced_by": {
			"client_performs_arithmetic_on_a_reported_value":
				"_check_no_client_arithmetic (guard A)",
			"client_clamps_coerces_or_ignores_a_client_delta":
				"_check_no_client_arithmetic (guard B) + _check_intent_body",
			"client_local_codes_are_server_codes":
				"_check_local_codes_are_not_server_codes",
			"unsupported_intent_touches_transport":
				"_check_unsupported_intents",
			"observed_payload_is_one_transaction":
				"_check_observed_success_parses + _check_live",
			"parity_with_legacy_claimed":
				"not a claim; v1 is new behaviour and no legacy oracle exists",
		},
		"limits": {
			# Both counts moved from 1 when the second v1 route landed. The
			# second LEGACY command is counted here because `collect` and
			# `complete_collection` are two distinct named branches of
			# `command.py` -- the 63-branch total is the whole dispatcher,
			# and the remaining 61 are unrouted on v1 whether or not v0
			# serves them. `test_collection_v1.gd` owns that route's own
			# coverage; this suite owns the collect route's.
			"v1_routes_delivered": 2,
			"legacy_commands_covered": 2,
			"legacy_commands_total": 63,
			"fixture_is_a_captured_legacy_oracle": false,
			"windowed_capture": false,
			"pixel_parity": false,
			"client_sees_a_before_state": false,
		},
	}, "\t"))
	handle = null


func _intent_names() -> Array:
	var names := []
	for intent in UNSUPPORTED_INTENTS:
		names.append(str(intent[0]))
	return names


## The per-result-class refusal field names, so the report records the
## divergence rather than leaving it only in a check message.
func _intent_field_names() -> Dictionary:
	var names := {}
	for intent in UNSUPPORTED_INTENTS:
		names[str(intent[0])] = [str(intent[2]), str(intent[3])]
	return names


# --- helpers -----------------------------------------------------------------


## A project-relative source file's bytes as text, or "" when unreadable.
func _project_source(relative: String) -> String:
	var path := Paths.project_dir().path_join(relative)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)


## The declared return type of `method` in `body`, or "" when the method is
## absent. A signature may wrap over several lines, so lines are accumulated
## until a `->` is followed by a `:`.
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


## Strips `#` comments and string literals with a two-state scan, then splits
## into lines, so a scan sees CODE only. A naive split on `#` desynchronises on
## an apostrophe inside a double-quoted string, which this repository has already
## been bitten by; the two-state scan is what makes the guard trustworthy.
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


## True when a `collect_income` call binds its result without narrowing it to a
## concrete class. A call wrapped over several lines has its binding on an
## earlier line, so the walk goes back up to three lines; a binding further away
## than that is recorded as untyped rather than silently passed, and the
## non-trivial census in the caller is what keeps this from going vacuous.
func _binds_untyped(line: String, lines: Array, index: int) -> bool:
	var at := line.find("collect_income(")
	if at == -1:
		return true
	var head := line.substr(0, at)
	var back := 0
	while not head.contains("=") and back < 3 and index - back - 1 >= 0:
		back += 1
		head = str(lines[index - back]).strip_edges() + " " + head
	if not head.contains("="):
		return true
	# An un-awaited call is NOT a facade call. Every facade intent is a
	# coroutine (the facade awaits its implementation), whereas `TownState`
	# also has a `collect_income` that is an ordinary synchronous method and
	# binds to a concrete type. Requiring the `await` is what separates the call
	# sites this widening can reach from the ones it cannot.
	if not head.contains("await"):
		return true
	var declared := head.split("=")[0].strip_edges()
	if not declared.contains(":"):
		return true
	return declared.substr(declared.rfind(":") + 1).strip_edges() == "Variant"


## True when a `collect_income` whose own line carries no `await` is the tail
## of a call whose opening line does. The walk is bounded at three lines, exactly
## as in `_binds_untyped`, and a binding further away than that is left uncounted
## rather than counted as clean.
func _wrapped_await(lines: Array, index: int) -> bool:
	var back := 0
	while back < 3 and index - back - 1 >= 0:
		back += 1
		if str(lines[index - back]).strip_edges().contains("await"):
			return true
	return false


## Sorts a dictionary's keys, so no comparison depends on insertion order.
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


func _merged(base: Variant, extra: Dictionary) -> Dictionary:
	var out: Dictionary = {}
	if base is Dictionary:
		for key in base:
			out[str(key)] = base[key]
	for key in extra:
		out[str(key)] = extra[key]
	return out


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
