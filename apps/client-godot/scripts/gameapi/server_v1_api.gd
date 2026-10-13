extends Node
## `ServerV1Api` - the third `GameApi` implementation, speaking JSON over
## loopback HTTP to **Server v1** (design D8).
##
## ## What this implementation delivers, and what it refuses
##
## v1 exposes exactly **four** routes, `POST /v1/collect`,
## `POST /v1/collection`, `POST /v1/combat` and `POST /v1/magic`, and this
## implementation implements exactly those four
## intents. Every other facade intent answers with the **client-local** code
## `unsupported_by_server_v1` and **never touches the transport at all** - which
## is the honest answer for a surface that does not exist, and is deliberately
## different from a server refusal: `unsupported_by_server_v1` is not in
## `server_v1_refusals.REFUSAL_HTTP_STATUS`, because it is never sent to v1 and
## therefore cannot be one of v1's codes.
##
## Those refusals still return each intent's **own** declared typed result (a
## `BootData.SellResult` for a sell, a `RewardFlow.RewardResult` for a reward
## action, and so on), built by that type's own `_failure` factory, so the
## facade's declared return type keeps holding and a caller that ignores the
## error code still gets a well-formed object rather than `null`.
##
## ## The refusal is not an excuse to widen the client's model
##
## `list_sessions()` and `get_bootstrap()` refuse too. v1 has no session list
## and no bootstrap route, so there is **no v1 answer to model** for them: the
## typed result carries the local code and nothing else. `collect_income()`,
## `complete_collection_town()`, `combat_town()` and `magic_town()` are the four
## intents whose v1
## answers have their
## own typed results (`server_v1_collect_result.gd`,
## `server_v1_collection_result.gd`, `server_v1_combat_result.gd` and
## `server_v1_magic_result.gd`), because v1's
## shapes genuinely differ from
## v0's - see those modules' headers for the full reasons. `GameApi`'s declared
## return types for those two are `Variant` with the concrete types named in its
## own comment (and asserted by `tests/test_server_v1.gd` and
## `tests/test_collection_v1.gd`).
##
## ## Scope and loopback
##
## This file is one of exactly **two** project files allowed to name an HTTP
## endpoint or use the built-in HTTP request client: the legacy-v0
## implementation (`legacy_v0_api.gd`) and this one. `tests/test_project_scope.gd`
## restricts those tokens to that pair and asserts the pair is exactly that
## pair, so no boot or presentation code can reach a transport. Only
## `127.0.0.1` is ever dialed, and only v1's own port (design D7), which is
## distinct from the legacy server's 5055 and the Compatibility API's 5056.
##
## ## What is NOT claimed
##
## Selecting this implementation does not make the client authoritative about
## anything. v1 derives the payout from committed content and recorded state;
## this file reads `resources_after` **verbatim** and applies nothing. It holds
## no cache, no queue, no readiness state, and no view of the save. It is a
## transport plus a parser, and the parser fails closed.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const BehaviorFlow = preload("res://scripts/units/behavior_flow.gd")
const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const RewardFlow = preload("res://scripts/rewards/reward_flow.gd")
const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")
const ServerV1Collect = preload(
	"res://scripts/gameapi/server_v1_collect_result.gd")
const ServerV1Collection = preload(
	"res://scripts/gameapi/server_v1_collection_result.gd")
const ServerV1Combat = preload(
	"res://scripts/gameapi/server_v1_combat_result.gd")
const ServerV1Magic = preload(
	"res://scripts/gameapi/server_v1_magic_result.gd")

## Loopback default: v1 binds `127.0.0.1` only and its own port, 5057
## (design D7; `apps/server-v1/server_v1_settings.py`).
const DEFAULT_ENDPOINT := "http://127.0.0.1:5057"
const COLLECT_PATH := "/v1/collect"
const COLLECTION_PATH := "/v1/collection"
const COMBAT_PATH := "/v1/combat"
const MAGIC_PATH := "/v1/magic"
const REQUEST_TIMEOUT_SECONDS := 30.0

## Endpoint override from the `gameapi/endpoint` setting or the
## `--gameapi-endpoint=` user argument ("" = the loopback default).
var endpoint := ""

## Number of requests this implementation has actually put on the wire. The
## live phase asserts this moves **exactly once per collect intent** and **not
## at all** for an unsupported intent, which is what makes "never touches the
## transport" a measured claim rather than a comment.
var transport_requests := 0

## Number of intents this implementation refused locally because v1 has no such
## route. Counted separately so the two totals can be compared.
var unsupported_intents := 0

var _request: HTTPRequest


func _ready() -> void:
	_request = HTTPRequest.new()
	_request.timeout = REQUEST_TIMEOUT_SECONDS
	add_child(_request)


## Endpoint actually dialed (explicit override or the loopback default).
func resolved_endpoint() -> String:
	if endpoint != "":
		return endpoint
	return DEFAULT_ENDPOINT


## The one implemented intent: a collection, expressed as **intent only**.
##
## The request body carries a save identity, a row key, and nothing else. It
## carries **no** amount, **no** balance, **no** price, **no** elapsed time and
## **no** expected outcome: the payload is built by `_intent_body()` and is
## asserted by `tests/test_server_v1.gd` to be exactly `player_id` and `row`,
## so this client cannot smuggle a delta even by accident. If it did, v1 would
## refuse it with `client_supplied_delta` - refusing is the server's decision,
## not this client's.
func collect_income(user_id: String,
		item_index: int) -> ServerV1Collect.CollectResult:
	var outcome := await _call(COLLECT_PATH, JSON.stringify(
		_intent_body(user_id, item_index)))
	if not outcome.get("ok", false):
		return ServerV1Collect.collect_failure(
			str(outcome.get("code", ServerV1Collect.CODE_BAD_REQUEST)),
			str(outcome.get("message", "")))
	return ServerV1Collect.parse_collect(outcome.get("payload"))


## The v1 collect intent: two fields, verbatim. This is the whole request.
static func _intent_body(user_id: String, item_index: int) -> Dictionary:
	return {"player_id": user_id, "row": item_index}


## The second implemented intent: a collection **completion**, as intent only.
##
## The body carries a save identity, a committed collection id, and nothing else
## - no price, no requirement list, no prize, no expected balance. The id is
## sent even when it is negative, because v1 refuses an id that the preserved
## branch would have clamped onto collection 1 **by name**
## (`aliased_collection_id`), and a client that filtered it out first would get
## `malformed_request` instead - a different answer to a different question.
## `tests/test_collection_v1.gd` asserts this body is exactly `player_id` and
## `collection_id`, so this client cannot smuggle a value even by accident.
func complete_collection_town(user_id: String,
		collection_id: int) -> ServerV1Collection.CollectionGrantResult:
	var outcome := await _call(COLLECTION_PATH, JSON.stringify(
		_collection_intent_body(user_id, collection_id)))
	if not outcome.get("ok", false):
		return ServerV1Collection.grant_failure(
			str(outcome.get("code", ServerV1Collection.CODE_BAD_REQUEST)),
			str(outcome.get("message", "")))
	return ServerV1Collection.parse_grant(outcome.get("payload"))


## The v1 collection intent: two fields, verbatim. This is the whole request.
static func _collection_intent_body(user_id: String,
		collection_id: int) -> Dictionary:
	return {"player_id": user_id, "collection_id": collection_id}


## The third implemented intent: a magic **counter transition**, as intent only.
##
## ## Why this one is the interesting one
##
## The other two v1 intents charge something, and the charge is derived from
## committed content. This one **charges nothing at all**, and that is not an
## omission in the server: no committed column of the ten-row magic table is
## named as a price, so there is nothing to derive one from (design D2). The
## request therefore carries an identity and an **operation**, and nothing else -
## and the absence of a price is carried in the answer as an explicit
## `price_charged: null` rather than as a missing field, so "nothing was charged"
## can never be confused with "the answer said nothing".
##
## ## `action` becomes `operation`, and it is sent unfiltered
##
## The facade's `magic_town(action, ...)` parameter is called `action` because the
## **legacy-v0** route spells its body field `action`; v1's field is `operation`
## and carries the same closed set `{buy, use}`. It is sent **verbatim and
## unchecked**, because a client that pre-filtered it would turn v1's named
## `malformed_request` into a client-local code — and that is exactly the mistake
## `complete_collection_town` above documents avoiding for a negative collection
## id. A wrong operation therefore reaches v1, is refused there by name, and comes
## back through `error_code` like every other v1 refusal.
##
## ## The declared return type changed, and that is recorded
##
## This implementation previously returned `MagicFlow.MagicResult` by refusing.
## It now returns `ServerV1Magic.MagicCounterResult`, because v1's magic answer is
## genuinely a different shape from v0's: v0 reports `command`, `addressing`,
## `ordering_rule`, `validation_order`, `cap_uniformity`, three `legacy_*`
## strings, `recorded_after`/`legacy_expected_after`/`matches_derived` and a
## `no_damage` claim, while v1 reports a `transition`, a `counter` block, the
## committed row verbatim, and divergence **reasons** rather than a recomputed
## legacy value. A single model could not absorb both without picking a sign
## convention and re-deriving a legacy figure - i.e. inventing two rules.
## `GameApi.magic_town`'s declared return type is therefore widened to `Variant`
## with the concrete types named in its comment, which is the **third** widening
## of that kind in this facade and the **first** one this line needed
## (`collect_income` and `complete_collection_town` are the two before it).
func magic_town(user_id: String, action: Variant,
		magic_id: Variant) -> ServerV1Magic.MagicCounterResult:
	var outcome := await _call(MAGIC_PATH, JSON.stringify(
		_magic_intent_body(user_id, str(action), magic_id)))
	if not outcome.get("ok", false):
		return ServerV1Magic.magic_failure(
			str(outcome.get("code", ServerV1Collect.CODE_BAD_REQUEST)),
			str(outcome.get("message", "")))
	return ServerV1Magic.parse_magic_counter(outcome.get("payload"))


## The v1 magic intent: three fields, verbatim. This is the whole request.
##
## **`magic_id` is sent exactly as the caller gave it**, including a float or a
## string form, because v1 refuses a non-canonical identity by name
## (`unknown_magic_id`) and a client that normalised it first would turn that
## specific answer into `malformed_request`. Four fields are **not** sent and
## could not be smuggled even by accident: a count, a price, a delta and a
## balance. `tests/test_magic_v1.gd` asserts this body is exactly `player_id`,
## `operation` and `magic_id`.
static func _magic_intent_body(user_id: String, operation: String,
		magic_id: Variant) -> Dictionary:
	return {
		"player_id": user_id,
		"operation": operation,
		"magic_id": magic_id,
	}


## The fourth implemented intent: a **combat identity**, as intent only.
##
## ## What this sends, and what it deliberately does not
##
## The body carries a save identity and a committed unit id, and nothing else —
## no damage, no hit, no destruction count, no expected balance, and **no
## `action`**. That last omission is the one worth stating: the facade's
## `combat_town` signature has an `action` parameter because the legacy-v0 route
## spells its body field `action`, and v1 has **one** action and no operation
## field at all (design D1). Sending it would invent a second request kind the
## server does not have, and a server that ignored it would answer a request the
## client believes it made.
##
## `addressing` is the committed unit id and it is sent **exactly as the caller
## gave it**, including a float or a string form, because v1 refuses a
## non-canonical identity by name (`unknown_magic_id`) and a client that
## normalised it first would turn that specific answer into
## `malformed_request` — the mistake `complete_collection_town` above documents
## avoiding, in the opposite direction.
##
## **No destruction shape can be sent at all**, because none is built here. The
## preserved branch's wire shape (`attacker_units`) has no field in this request,
## so the client cannot smuggle a destruction figure even by accident, and v1's
## `client_dictated_destruction` refusal exists for a caller who builds a body by
## other means rather than for this one.
##
## ## The declared return type changed, and that is recorded
##
## This implementation previously returned `CombatFlow.CombatResult` by
## refusing, and now returns `ServerV1Combat.CombatAuthorityResult`, for the
## reason `server_v1_combat_result.gd`'s header records in full: the two surfaces
## disagree on what a combat answer **is**. v0's reports a destruction figure and
## a `resolve` action; v1's reports `rows_destroyed: 0` unconditionally and a
## proof that nothing changed. One model absorbing both would have to pick a sign
## convention for three fields that mean different things in the two.
func combat_town(user_id: String, action: Variant,
		addressing: Variant) -> ServerV1Combat.CombatAuthorityResult:
	var outcome := await _call(COMBAT_PATH, JSON.stringify(
		_combat_intent_body(user_id, addressing)))
	if not outcome.get("ok", false):
		return ServerV1Combat.combat_failure(
			str(outcome.get("code", ServerV1Collect.CODE_BAD_REQUEST)),
			str(outcome.get("message", "")))
	return ServerV1Combat.parse_combat_authority(outcome.get("payload"))


## The v1 combat intent: two fields, verbatim. This is the whole request.
##
## `action` is accepted by the enclosing function and **not forwarded here**, and
## that is deliberate rather than forgotten: the signature is the facade's, and
## `tests/test_combat_v1.gd` asserts this body's key set is exactly `player_id`
## and `unit_id`, so the omission is measured rather than asserted in a comment.
static func _combat_intent_body(user_id: String, unit_id: Variant) -> Dictionary:
	return {"player_id": user_id, "unit_id": unit_id}


# --- intents v1 does not have ------------------------------------------------
#
# Each answers `unsupported_by_server_v1` through its OWN typed result's
# `_failure` factory, and none of them touches `_call`. They are grouped rather
# than interleaved because they are uniform on purpose: there is one decision
# (v1 exposes **four** routes) and twenty identical consequences. The count moved
# from twenty-two when `POST /v1/magic` landed and again when `POST /v1/combat`
# landed: `magic_town` and then `combat_town` joined the implemented intents above
# and left this section, and `tests/test_server_v1.gd` pins the remaining twenty
# by name so each move is measured rather than assumed.


func list_sessions() -> BootData.SaveListResult:
	return _unsupported(BootData.save_list_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no session-list route; this client sends no request."))


func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	return _unsupported(BootData.bootstrap_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no bootstrap route; this client sends no request."))


func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	return _unsupported(BootData.placement_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no placement route; this client sends no request."))


func purchase_item(user_id: String, item_id: int) -> BootData.PurchaseResult:
	return _unsupported(BootData.purchase_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no purchase route; this client sends no request."))


func move_building(user_id: String, item_index: int, x: int,
		y: int) -> BootData.PlacementResult:
	return _unsupported(BootData.placement_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no move route; this client sends no request."))


func sell_building(user_id: String, item_index: int) -> BootData.SellResult:
	return _unsupported(BootData.sell_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no sell route; this client sends no request."))


func store_building(user_id: String,
		item_index: int) -> BootData.StoreResult:
	return _unsupported(BootData.store_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no store route; this client sends no request."))


func upgrade_building(user_id: String,
		item_index: int) -> BootData.UpgradeResult:
	return _unsupported(BootData.upgrade_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no upgrade route; this client sends no request."))


func build_construction(user_id: String, item_index: int,
		action: String) -> BootData.ConstructionResult:
	return _unsupported(BootData.construction_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no construction route; this client sends no request."))


func expand_town(user_id: String,
		expansion_id: int) -> BootData.ExpandResult:
	return _unsupported(BootData.expand_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no expansion route; this client sends no request."))


func level_up_town(user_id: String) -> BootData.LevelUpResult:
	return _unsupported(BootData.level_up_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no level-up route; this client sends no request."))


func push_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	return _unsupported(BootData.queue_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no queue route; this client sends no request."))


func pop_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	return _unsupported(BootData.queue_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no queue route; this client sends no request."))


func resurrect_hero_town(user_id: String, x: int,
		y: int) -> BehaviorFlow.ResurrectResult:
	return _unsupported(BehaviorFlow.resurrect_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no resurrection route; this client sends no request."))


func advance_research_town(user_id: String, action: String,
		track: int) -> ResearchFlow.ResearchResult:
	return _unsupported(ResearchFlow.result_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no research route; this client sends no request."))


func advance_quest_town(user_id: String, action: String,
		addressing: Variant) -> QuestFlow.QuestResult:
	return _unsupported(QuestFlow.result_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no quest route; this client sends no request."))


func complete_tutorial_town(user_id: String,
		step: int) -> TutorialFlow.TutorialResult:
	return _unsupported(TutorialFlow.result_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no tutorial route; this client sends no request."))


func place_stored_item_town(user_id: String, item_id: int, x: int,
		y: int) -> BootData.StoredPlacementResult:
	return _unsupported(BootData.stored_placement_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no stored-placement route; this client sends no "
		+ "request."))


func sell_stored_item_town(user_id: String,
		item_id: int) -> BootData.StoredSaleResult:
	return _unsupported(BootData.stored_sale_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no stored-sale route; this client sends no request."))


func reward_town(user_id: String,
		action: Variant) -> RewardFlow.RewardResult:
	return _unsupported(RewardFlow.reward_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no reward route; this client sends no request."))


## Counts one locally-refused intent and returns the caller's own typed result.
## The counter is the only state this path touches; the transport is not reached.
func _unsupported(result: Variant) -> Variant:
	unsupported_intents += 1
	return result


# --- transport ---------------------------------------------------------------


## One POST over loopback HTTP. v1 answers every refusal with HTTP 4xx/5xx AND
## a structured body, so a status alone is never read as the answer: the body is
## parsed first and the status is only consulted to distinguish "the server
## explained itself" from "the server said something this client cannot read".
func _call(path: String, body: String) -> Dictionary:
	var url := resolved_endpoint() + path
	var headers := PackedStringArray(["Content-Type: application/json"])
	transport_requests += 1
	var request_error := _request.request(
		url, headers, HTTPClient.METHOD_POST, body)
	if request_error != OK:
		return _failure(ServerV1Collect.CODE_BAD_REQUEST,
			"cannot start the request to %s (error %d)" % [url, request_error])
	var completion: Array = await _request.request_completed
	var transport := int(completion[0])
	var status := int(completion[1])
	var raw: PackedByteArray = completion[3]
	if transport != HTTPRequest.RESULT_SUCCESS:
		return _failure(ServerV1Collect.CODE_BAD_REQUEST,
			_transport_message(transport, url))
	var parser := JSON.new()
	if parser.parse(raw.get_string_from_utf8()) != OK:
		return _failure(ServerV1Collect.CODE_BAD_REQUEST,
			"response from %s is not JSON (HTTP %d)" % [url, status])
	if not (parser.data is Dictionary):
		return _failure(ServerV1Collect.CODE_BAD_REQUEST,
			"response from %s is not a JSON object (HTTP %d)" % [url, status])
	var payload: Dictionary = parser.data
	# v1's own envelope: `result` is either "success" or "refused", and the
	# parser is what decides whether either is well-formed. An HTTP 200 with no
	# recognised `result` is a closed failure, never a success.
	if str(payload.get("result", "")) == "refused":
		return {"ok": true, "payload": payload}
	if str(payload.get("result", "")) != "success":
		return _failure(ServerV1Collect.CODE_BAD_REQUEST,
			"HTTP %d from %s carries no recognised result field"
			% [status, url])
	return {"ok": true, "payload": payload}


func _failure(code: String, message: String) -> Dictionary:
	return {"ok": false, "code": code, "message": message}


## Names the transport failure with the endpoint, because a caller must be able
## to see WHICH endpoint could not be reached. Observed on the pinned engine
## (Windows x64): a refused loopback port is reported as `RESULT_TIMEOUT`,
## never as `RESULT_CANT_CONNECT`, so the timeout branch is the one an
## unreachable-endpoint run actually exercises.
func _transport_message(transport: int, url: String) -> String:
	match transport:
		HTTPRequest.RESULT_CANT_CONNECT:
			return "endpoint unreachable (connection refused): " + url
		HTTPRequest.RESULT_CANT_RESOLVE:
			return "endpoint unreachable (cannot resolve the loopback host): " + url
		HTTPRequest.RESULT_CONNECTION_ERROR:
			return "endpoint unreachable (connection error): " + url
		HTTPRequest.RESULT_TIMEOUT:
			return "endpoint unreachable (no response within %.0f seconds): %s" \
				% [REQUEST_TIMEOUT_SECONDS, url]
		HTTPRequest.RESULT_NO_RESPONSE:
			return "endpoint unreachable (no HTTP response): " + url
		_:
			return "endpoint unreachable (transport error %d): %s" \
				% [transport, url]
