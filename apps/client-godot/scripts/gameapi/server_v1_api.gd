extends Node
## `ServerV1Api` - the third `GameApi` implementation, speaking JSON over
## loopback HTTP to **Server v1** (design D8).
##
## ## What this implementation delivers, and what it refuses
##
## v1 exposes exactly **one** route, `POST /v1/collect`, and this
## implementation implements exactly that one intent. Every other facade intent
## answers with the **client-local** code
## `unsupported_by_server_v1` and **never touches the transport at all** - which
## is the honest answer for a surface that does not exist, and is deliberately
## different from a server refusal: `unsupported_by_server_v1` is not in
## `server_v1_refusals.REFUSAL_HTTP_STATUS`, because it is never sent to v1 and
## therefore cannot be one of v1's codes.
##
## Those refusals still return each intent's **own** declared typed result (a
## `BootData.SellResult` for a sell, a `CombatFlow.CombatResult` for a combat
## action, and so on), built by that type's own `_failure` factory, so the
## facade's declared return type keeps holding and a caller that ignores the
## error code still gets a well-formed object rather than `null`.
##
## ## The refusal is not an excuse to widen the client's model
##
## `list_sessions()` and `get_bootstrap()` refuse too. v1 has no session list
## and no bootstrap route, so there is **no v1 answer to model** for them: the
## typed result carries the local code and nothing else. `collect_income()` is
## the one intent whose v1 answer has its own typed result
## (`server_v1_collect_result.gd`), because v1's shape genuinely differs from
## v0's - see that module's header for the full reason.
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
const CombatFlow = preload("res://scripts/units/combat_flow.gd")
const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const MagicFlow = preload("res://scripts/units/magic_flow.gd")
const RewardFlow = preload("res://scripts/rewards/reward_flow.gd")
const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")
const ServerV1Collect = preload(
	"res://scripts/gameapi/server_v1_collect_result.gd")

## Loopback default: v1 binds `127.0.0.1` only and its own port, 5057
## (design D7; `apps/server-v1/server_v1_settings.py`).
const DEFAULT_ENDPOINT := "http://127.0.0.1:5057"
const COLLECT_PATH := "/v1/collect"
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


# --- intents v1 does not have ------------------------------------------------
#
# Each answers `unsupported_by_server_v1` through its OWN typed result's
# `_failure` factory, and none of them touches `_call`. They are grouped rather
# than interleaved because they are uniform on purpose: there is one decision
# (v1 exposes one route) and twenty-one identical consequences.


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


func complete_collection_town(user_id: String,
		collection_id: int) -> BootData.CollectionResult:
	return _unsupported(BootData.collection_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no collection route; this client sends no request."))


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


func combat_town(user_id: String, action: Variant,
		addressing: Variant) -> CombatFlow.CombatResult:
	return _unsupported(CombatFlow.combat_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no combat route; this client sends no request."))


func magic_town(user_id: String, action: Variant,
		magic_id: Variant) -> MagicFlow.MagicResult:
	return _unsupported(MagicFlow.magic_failure(
		ServerV1Collect.CODE_UNSUPPORTED,
		"Server v1 exposes no magic route; this client sends no request."))


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
