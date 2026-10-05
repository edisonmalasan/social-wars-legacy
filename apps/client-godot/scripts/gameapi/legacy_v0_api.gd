extends Node
## `LegacyV0Api` — GameApi implementation that speaks JSON over loopback HTTP
## to Compatibility API v0 (design D5, specs "Boot live against Compatibility
## API", "Place through either implementation", "Purchase through either
## implementation", "Move through either implementation", "Sell through
## either implementation", "Upgrade through either implementation", and
## "Construction through either implementation", "Collect through either
## implementation", "Expand through either implementation", "Level up
## through either implementation", "Queue through either implementation", and
## "Resurrect through either implementation").
##
## This is the ONLY project file allowed to name the compat endpoint or to
## use the built-in HTTP request/enumeration types; the scope test restricts
## those tokens to this path so no boot or presentation code can reach a
## transport (spec: "Keep legacy transport out of the UI"). Only `127.0.0.1`
## is ever dialed — the default endpoint below is the documented loopback
## address of the v0 service (design D3/D9).

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const BehaviorFlow = preload("res://scripts/units/behavior_flow.gd")
const CombatFlow = preload("res://scripts/units/combat_flow.gd")
const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const MagicFlow = preload("res://scripts/units/magic_flow.gd")
const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")

## Loopback default: the v0 service binds 127.0.0.1 only (design D3).
const DEFAULT_ENDPOINT := "http://127.0.0.1:5056"
const SESSION_PATH := "/v0/session"
const BOOTSTRAP_PATH := "/v0/bootstrap"
const PLACE_PATH := "/v0/place"
const PURCHASE_PATH := "/v0/purchase"
const MOVE_PATH := "/v0/move"
const SELL_PATH := "/v0/sell"
const STORE_PATH := "/v0/store"
const UPGRADE_PATH := "/v0/upgrade"
const CONSTRUCTION_PATH := "/v0/construction"
const COLLECT_PATH := "/v0/collect"
const EXPAND_PATH := "/v0/expand"
const LEVEL_UP_PATH := "/v0/level_up"
const QUEUE_PATH := "/v0/queue"
const COLLECTION_PATH := "/v0/collection"
const RESURRECT_PATH := "/v0/resurrect"
const RESEARCH_PATH := "/v0/research"
const QUEST_PATH := "/v0/quests"
const TUTORIAL_PATH := "/v0/tutorial"
const COMBAT_PATH := "/v0/combat"
const MAGIC_PATH := "/v0/magic"
const REQUEST_TIMEOUT_SECONDS := 30.0

## Endpoint override from the `gameapi/endpoint` setting or the
## `--gameapi-endpoint=` user argument ("" = the loopback default).
var endpoint := ""

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


## The session list over loopback HTTP; structured failures for unreachable
## endpoints, non-JSON bodies, and v0 structured API errors.
func list_sessions() -> BootData.SaveListResult:
	var outcome := await _call("GET", SESSION_PATH, "")
	if not outcome.get("ok", false):
		return BootData.save_list_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_save_list(outcome.get("payload"))


## Bootstrap over loopback HTTP; same failure rules as `list_sessions()`.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	var outcome := await _call("POST", BOOTSTRAP_PATH,
		JSON.stringify({"user_id": user_id}))
	if not outcome.get("ok", false):
		return BootData.bootstrap_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_bootstrap(outcome.get("payload"), user_id)


## One placement intent over loopback HTTP: the client sends only the
## intent (`user_id`, `item_id`, anchor `x`/`y`, `orientation`) and the
## service derives the legacy envelope server-side (design D3/D4), so the
## typed result's entry and resources are authoritative (design D7).
## Structured service errors pass through with their original codes;
## transport failures keep the boot failure rules — never a partial payload.
func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	var outcome := await _call("POST", PLACE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_id": item_id,
		"x": x,
		"y": y,
		"orientation": orientation,
	}))
	if not outcome.get("ok", false):
		return BootData.placement_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_placement(outcome.get("payload"))


## One purchase intent over loopback HTTP: the client sends only the intent
## (`user_id`, `item_id`) — no price, no quantity, no resource deltas — and
## the service derives the legacy `buy_stored_item_cash` envelope from the
## item's own config (design D2/D3), so the typed result's storage mapping
## and resources are authoritative (design D4). Structured service errors
## pass through with their original codes; transport failures keep the boot
## failure rules — never a partial payload.
func purchase_item(user_id: String, item_id: int) -> BootData.PurchaseResult:
	var outcome := await _call("POST", PURCHASE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_id": item_id,
	}))
	if not outcome.get("ok", false):
		return BootData.purchase_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_purchase(outcome.get("payload"))


## One move intent over loopback HTTP: the client sends only the intent
## (`user_id`, the legacy `item_index` of an existing placement, and the
## target `x`/`y`) — no price, no orientation, no resource deltas — and the
## service derives the legacy `move` envelope server-side (design D2/D3).
## The response is the SAME authoritative superset the placement command
## returns (the persisted row re-read from the save plus the current
## resources), so the delivered typed placement result and parse function
## are reused (design D4): both implementations yield identical typed
## shapes by construction. Structured service errors pass through with
## their original codes — notably `unknown_item_index` for a stale or
## unknown index, which the client surfaces instead of moving anything;
## transport failures keep the boot failure rules, never a partial payload.
func move_building(user_id: String, item_index: int, x: int,
		y: int) -> BootData.PlacementResult:
	var outcome := await _call("POST", MOVE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
		"x": x,
		"y": y,
	}))
	if not outcome.get("ok", false):
		return BootData.placement_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_placement(outcome.get("payload"))


## One sell intent over loopback HTTP: the client sends only the intent
## (`user_id` and the legacy `item_index` of an existing placement) — no
## price, no refund, no sell reason, no resource deltas — and the service
## derives the legacy `sell` envelope server-side (design D3), so the typed
## result's removed row and resources are authoritative (design D5). The
## removed row is the one the service read BEFORE execution, so the client
## removes exactly the building the response names. Structured service
## errors pass through with their original codes — notably
## `unknown_item_index` for a stale or unknown index, which the client
## surfaces instead of removing anything; transport failures keep the boot
## failure rules, never a partial payload.
func sell_building(user_id: String, item_index: int) -> BootData.SellResult:
	var outcome := await _call("POST", SELL_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
	}))
	if not outcome.get("ok", false):
		return BootData.sell_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_sell(outcome.get("payload"))


## One store intent over loopback HTTP: the client sends only the intent
## (`user_id` and the legacy `item_index` of an existing placement) — no
## price, no quantity, no capacity, no resource deltas — and the service
## derives the legacy `store_item` envelope server-side (design D3), so the
## typed result's removed row, storage mapping, and resources are
## authoritative (design D4). The removed row is the one the service read
## BEFORE execution, so the client removes exactly the building the response
## names, and the storage mapping is the FULL post-execution one, parsed by
## the same shared parser the purchase response uses. Structured service
## errors pass through with their original codes — notably
## `unknown_item_index` for a stale or unknown index, which the client
## surfaces instead of removing anything; transport failures keep the boot
## failure rules, never a partial payload.
func store_building(user_id: String,
		item_index: int) -> BootData.StoreResult:
	var outcome := await _call("POST", STORE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
	}))
	if not outcome.get("ok", false):
		return BootData.store_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_store(outcome.get("payload"))


## One upgrade intent over loopback HTTP: the client sends only the intent
## (`user_id` and the legacy `item_index` of an existing placement) — no
## target tier, no reason, no coordinates, no orientation, no player, no
## quantity, no price, and no resource deltas. The service derives both
## derived legacy commands server-side (design D2/D3): the target tier from
## the committed configuration's `upgrades_to`, the reason from the
## committed legacy constant, the cell, orientation, and player from the row
## being replaced, and a NEUTRAL resource vector for both — so **no upgrade
## cost of any kind is claimed** (design D4).
##
## The response is the two-sided authoritative superset (design D5): the
## row as read BEFORE execution and the row re-read AFTER it — the derived
## target tier at the SAME key and cell — plus the current resources, parsed
## by the one shared entry parser every other response uses. Structured
## service errors pass through with their original codes — notably
## `unknown_item_index` for a stale or unknown index and `no_upgrade_path`
## for a placement whose item has no resolvable next tier, which the client
## surfaces instead of upgrading anything; transport failures keep the boot
## failure rules, never a partial payload.
func upgrade_building(user_id: String,
		item_index: int) -> BootData.UpgradeResult:
	var outcome := await _call("POST", UPGRADE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
	}))
	if not outcome.get("ok", false):
		return BootData.upgrade_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_upgrade(outcome.get("payload"))


## One construction intent over loopback HTTP: the client sends only the intent
## (`user_id`, the legacy `item_index` of an existing placement, and ONE action
## of the closed vocabulary) — no duration, no countdown, no price, no
## resource deltas. The service derives the legacy command and every argument
## from committed content and the row's own state, the start duration from the
## item's committed `build_time` (design D2/D3), so the typed result's two
## rows, resolved action, and resources are authoritative (design D5). The row
## as read BEFORE execution and the row re-read AFTER it are parsed by the one
## shared entry parser every other response uses.
##
## Structured service errors pass through with their original codes — notably
## `unknown_item_index` for a stale or unknown index, `invalid_action` for an
## action outside the closed set, and `no_build_time` for a placement whose
## item has no resolvable positive committed build time, all of which the
## client surfaces instead of building anything; transport failures keep the
## boot failure rules, never a partial payload.
func build_construction(user_id: String, item_index: int,
		action: String) -> BootData.ConstructionResult:
	var outcome := await _call("POST", CONSTRUCTION_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
		"action": action,
	}))
	if not outcome.get("ok", false):
		return BootData.construction_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_construction(outcome.get("payload"))


## One collection intent over loopback HTTP: the client sends only the intent
## (`user_id` and the legacy `item_index` of an existing placement) — no
## amount, no resource, no tier, no time, no price, and no resource deltas —
## and the service derives the legacy `collect` envelope, the content-derived
## eight-slot payout, and the ladder rung server-side from the addressed item's
## committed income fields and the row's own state (design D7), so the typed
## result's two rows, payout, rung, reference instant, and resources are
## authoritative (design D8). Both rows are parsed by the one shared entry
## parser every other response uses.
##
## Structured service errors pass through with their original codes — notably
## `unknown_item_index` for a stale or unknown index, `no_income` for a row
## whose item records no committed income, `too_early` for a row that has not
## reached the first committed rung, `capped_collection` for a non-zero
## committed cap, `unknown_collect_type` for a resource type outside the
## committed set, and `construction_in_progress` for a row carrying
## construction state (the two-layer refusal the executed probe forced) — all
## of which the client surfaces instead of collecting anything; transport
## failures keep the boot failure rules, never a partial payload.
func collect_income(user_id: String,
		item_index: int) -> BootData.CollectResult:
	var outcome := await _call("POST", COLLECT_PATH, JSON.stringify({
		"user_id": user_id,
		"item_index": item_index,
	}))
	if not outcome.get("ok", false):
		return BootData.collect_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_collect(outcome.get("payload"))


## One expansion intent over loopback HTTP: the client sends only the intent
## (`user_id` and the expansion `expansion_id` it addresses the committed
## positional schedule with) — no amount, no resource, no price, no
## requirement flag, and no resource deltas — and the service reads the id's
## own committed row in the 98-entry `expansion_prices` schedule, derives the
## eight-slot **debit** from it, and executes the unchanged legacy `expand`
## branch server-side (design D1/D2/D5), so the typed result's two owned
## lists, debit, committed row, and resources are authoritative (design D8).
## The response carries the owned ledger as read BEFORE execution and the same
## ledger re-read AFTER it, so the client takes the ledger and the balances
## from the response verbatim and never appends an id or applies a debit
## locally.
##
## Structured service errors pass through with their original codes — notably
## `invalid_expansion_id` for a negative or non-integer id,
## `unknown_expansion_id` for an id the committed schedule does not price,
## `already_expanded` for an id the player's own ledger already contains,
## `expansion_requirements_unmet` for a row recording a neighbour or inventory
## requirement nothing this service can read evaluates, and
## `insufficient_resources` for a balance that does not cover the derived
## debit — all of which the client surfaces instead of expanding anything;
## transport failures keep the boot failure rules, never a partial payload.
func expand_town(user_id: String,
		expansion_id: int) -> BootData.ExpandResult:
	var outcome := await _call("POST", EXPAND_PATH, JSON.stringify({
		"user_id": user_id,
		"expansion_id": expansion_id,
	}))
	if not outcome.get("ok", false):
		return BootData.expand_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_expand(outcome.get("payload"))


## One level-up intent over loopback HTTP: the client sends ONLY the save
## identity — no level, no new level, no experience, no threshold, no reward,
## and no resource deltas. Any `level` / `new_level` / `xp` /
## `experience` / `reward_type` / `reward_amount` / `resources_changed` /
## `vector` key the service receives alongside the identity is **ignored**
## server-side, exactly as the collect and expand endpoints ignore
## client-supplied amounts and prices (design D3): the service reads the stored
## experience, derives the level the committed curve implies for it through the
## one named one-based conversion, and executes the unchanged legacy `level_up`
## branch with a NEUTRAL vector (design D5), so the typed result's
## `derived_level`, `level_before`, `level_after`, `curve`, and `resources` are
## authoritative (design D8). The response's second post-execution proof half
## requires every stored resource to be **unchanged**, because a level change
## moves none.
##
## Structured service errors pass through with their original codes — notably
## `level_already_current` (the recorded level already equals the level the
## committed curve derives, which is the committed corpus's own state at
## `xp 4 / level 1`) and `xp_below_threshold` (the stored experience cannot
## reach the recorded level's own committed threshold), both of which the client
## surfaces instead of advancing anything, plus `missing_user_id`,
## `invalid_user_id`, `unknown_user_id`, `invalid_payload`, and `internal_error`;
## transport failures keep the boot failure rules, never a partial payload.
func level_up_town(user_id: String) -> BootData.LevelUpResult:
	var outcome := await _call("POST", LEVEL_UP_PATH, JSON.stringify({
		"user_id": user_id,
	}))
	if not outcome.get("ok", false):
		return BootData.level_up_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_level_up(outcome.get("payload"))


## One production-queue **push** intent over loopback HTTP: the client sends the
## save identity and the target row's key and NOTHING else — no count, no cost,
## no duration, no training time, no readiness, and no resource deltas. Any
## `cost` / `duration` / `count` / `ready` / `training_time` /
## `resources_changed` / `vector` key the service receives alongside the
## identity is **ignored** server-side, exactly as the collect and expand
## endpoints ignore client-supplied amounts and prices (unit-queues design D2/D5):
## the service derives `push_queue_unit` from the closed action vocabulary,
## reads nothing but the addressed row, and executes the unchanged legacy branch
## with a NEUTRAL vector (design D4), so the typed result's two rows, `queue`,
## and `resources` are authoritative (design D8).
##
## **No unit is created by this intent**: no legacy command completes a queue
## or materialises a unit from one, so a push moves a count and a start instant
## and nothing else (design D1/D2). The response's second post-execution proof
## half requires every stored resource to be **unchanged**, because a queue
## moves none.
##
## Structured service errors pass through with their original codes — notably
## `unknown_map_key` for a key that names no row in the save, and the shared
## `missing_user_id` / `invalid_user_id` / `unknown_user_id` /
## `invalid_payload` / `internal_error` family — all of which the client
## surfaces instead of queueing anything; transport failures keep the boot
## failure rules, never a partial payload.
func push_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	var outcome := await _call("POST", QUEUE_PATH, JSON.stringify({
		"user_id": user_id,
		"map_key": map_key,
		"action": "push",
	}))
	if not outcome.get("ok", false):
		return BootData.queue_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_queue(outcome.get("payload"))


## One production-queue **pop** intent over loopback HTTP, under the same wire
## contract as the push: the save identity and the target key, nothing else, and
## any client-supplied outcome key ignored server-side. The legacy branch's own
## rules are the whole contract — it decrements the count, re-stamps the start
## instant on a partial decrement, and **deletes `nu`, `ts`, and `ui` together**
## at zero (design D1/D3) — and no producer, duration, level, or count check is
## added on top, with **no maximum count applied** because the legacy engine
## sets none (design D5).
##
## A pop against a row whose bag carries no count is an **inert recorded
## no-op**: the endpoint answers success with an unchanged bag rather than
## refusing, and this client surfaces that answer verbatim instead of inventing
## a local refusal code.
func pop_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	var outcome := await _call("POST", QUEUE_PATH, JSON.stringify({
		"user_id": user_id,
		"map_key": map_key,
		"action": "pop",
	}))
	if not outcome.get("ok", false):
		return BootData.queue_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_queue(outcome.get("payload"))


## One collection-completion intent over loopback HTTP: the client sends the
## save identity and a collection id and NOTHING else — no prize, item id,
## quantity, price, or resource deltas. Any `prize` / `item_id` / `quantity` /
## `item` / `grant` / `cost` / `price` / `resources_changed` / `vector` key the
## service receives alongside the identity is **ignored** server-side, exactly as
## the collect and expand endpoints ignore client-supplied amounts and prices
## (unit-collection design D1): the service looks the grant up in the committed
## `collections` table and executes the unchanged legacy `complete_collection`
## branch with a NEUTRAL vector (design D5), so the typed result's `item_id`,
## `quantity`, `prize`, `store_after`, and `resources` are authoritative
## (design D8).
##
## The response's second post-execution proof half requires every stored resource
## to be **unchanged**, because a completion moves none. The id-0/id-1 **alias**
## is reported on every answer rather than hidden: an aliased id is echoed
## exactly as sent, together with `clamped`, `aliased`, and `alias_of`.
##
## Structured service errors pass through with their original codes — notably
## `missing_collection_id`, `invalid_collection_id`, `unknown_collection_id`,
## and the shared `missing_user_id` / `invalid_user_id` / `unknown_user_id` /
## `internal_error` family — all of which the client surfaces instead of
## granting anything; transport failures keep the boot failure rules, never a
## partial payload.
func complete_collection_town(user_id: String,
		collection_id: int) -> BootData.CollectionResult:
	var outcome := await _call("POST", COLLECTION_PATH, JSON.stringify({
		"user_id": user_id,
		"collection_id": collection_id,
	}))
	if not outcome.get("ok", false):
		return BootData.collection_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_collection(outcome.get("payload"))


## One revival intent over loopback HTTP: the client sends ONLY the save identity
## and the addressed **cell** — no map key, no revived item id, no syringe
## count, no price, and no resource deltas.  Any `item_id` / `map_key` /
## `index` / `used_syringe` / `syringes` / `price` / `cost` /
## `resources_changed` / `vector` key the service receives alongside the
## identity is **ignored** server-side, exactly as the collect, expand, level-up,
## and collection routes ignore client-supplied amounts and prices (unit-behaviors
## design D2): the service derives the map key from the addressed cell's own
## placement row and the revived item id from the player's own recorded ledger,
## then executes the unchanged legacy `resurrect_hero` branch with a **NEUTRAL**
## vector (design D3), so the typed result's `map_key`, `item_id`, both ledgers,
## both placements, and `resources` are authoritative (design D8).
##
## **No syringe cost is charged and no resource moves**: `used_syringe` is bound
## from `args[4]` and DISCARDED, and the committed `syringes` field it would be
## paid in has zero legacy consumers.  The response's second post-execution proof
## half requires every stored resource to be **unchanged**, which is what makes
## that claim non-tautological.
##
## **No combat is resolved** and the revived placement is **not validated**:
## none of the seven committed combat fields has a legacy consumer, and the
## legacy branch re-places the row with no occupancy, bounds, type, or terrain
## check (design D5).  Both absences travel on the typed result, never as an
## implied rule.
##
## Structured service errors pass through with their original codes — notably
## `unresolvable_cell` for a cell no placement row records, `ambiguous_cell`
## for one more than one row records, `unresolvable_ledger_entry` for a player
## whose ledger is empty, `ambiguous_ledger` for a ledger holding more than one
## entry, `not_resurrectable` for a resolved entry whose committed
## `resurrectable` is absent or not greater than zero, and the shared
## `missing_user_id` / `invalid_user_id` / `unknown_user_id` / `internal_error`
## family — all of which the client surfaces instead of reviving anything;
## transport failures keep the boot failure rules, never a partial payload.
func resurrect_hero_town(user_id: String, x: int,
		y: int) -> BehaviorFlow.ResurrectResult:
	var outcome := await _call("POST", RESURRECT_PATH, JSON.stringify({
		"user_id": user_id,
		"x": x,
		"y": y,
	}))
	if not outcome.get("ok", false):
		return BehaviorFlow.resurrect_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BehaviorFlow.parse_resurrect(outcome.get("payload"))


## One research-track intent over loopback HTTP: the client sends the save
## identity, a CLOSED action, and the research track, and NOTHING else — no
## counter value, no research instant, and no cash amount. Any `step` / `item` /
## `timestamp` / `instant` / `cash` / `price` / `cost` / `step_count` / `reward` /
## `remaining` / `ready` / `duration` / `resources_changed` / `vector` /
## `seconds` / `fast_forward` key the service receives alongside the identity is
## **ignored** server-side, exactly as the collect, expand, level-up, collection,
## and revival routes ignore client-supplied amounts and prices (research design
## D2): the service derives every counter, derives the cash branch's own
## argument, and executes the unchanged legacy branch with a NEUTRAL vector
## (design D3).
##
## The response's second post-execution proof half requires **every** stored
## resource to be **unchanged**, because a research action moves none. That is
## what makes the no-price claim non-tautological.
##
## **No readiness and no completion** are reported, and no price either: the
## typed parser refuses a response that claims any of them, and `fast_forward` is
## offered by **no** action and **no** route (design D7).
##
## Structured service errors pass through with their original codes — notably
## `missing_track`, `invalid_track`, and `unresolvable_research_state`, and the
## shared `missing_user_id` / `invalid_user_id` / `unknown_user_id` /
## `internal_error` family — all of which the client surfaces instead of
## advancing anything; transport failures keep the boot failure rules, never a
## partial payload.
func advance_research_town(user_id: String, action: String,
		track: int) -> ResearchFlow.ResearchResult:
	var outcome := await _call("POST", RESEARCH_PATH, JSON.stringify({
		"user_id": user_id,
		"action": action,
		"track": track,
	}))
	if not outcome.get("ok", false):
		return ResearchFlow.result_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return ResearchFlow.parse_result(outcome.get("payload"))


## One quest intent over loopback HTTP: the client sends the save identity, a
## CLOSED action, and the branch's own addressing under that action's **own**
## wire key (`goal_index`, `key`, `mission`, `quest_index`, or `quest_id` —
## `QuestFlow.ACTION_ADDRESSING_KEY`, read through `QuestFlow.wire_key()`) — and
## NOTHING else. The typed layer carries the addressing **positionally**; the wire
## key is the per-action spelling the service reads, so a body is always exactly
## THREE keys and no fourth value is even expressible. No progress pair, no value, no
## difficulty, no win/loss outcome, and no unit list can be sent, so there is no
## channel through which a client could dictate an outcome (quest design D2). Any
## `progress` / `value` / `difficulty` / `win` / `units` / `lost` / `reward` /
## `price` / `resources_changed` / `vector` / `seconds` / `fast_forward` key the
## service receives alongside the identity is **ignored** server-side, exactly as
## the collect, expand, level-up, collection, revival, and research routes ignore
## client-supplied amounts and prices.
##
## The response's second post-execution proof half requires **every** stored
## resource to be **unchanged**, because a quest action moves none. That is what
## makes the no-reward claim non-tautological: the committed `reward` field has
## ZERO legacy consumers and is **uniformly 10** on all 91 entries, so paying it
## would fabricate an economy from a constant (design D6).
##
## **No completion and no elapsed time** are reported, and no reward either: the
## typed parser refuses a response that claims any of them, `fast_forward` is
## offered by **no** action and **no** route (design D9), and
## `unlocked_quest_index_written` is `false` because that field has zero legacy
## consumers (design D7).
##
## **The `end_quest` destruction count is REFUSED and reported as a DIVERGENCE,
## not as parity** (design D2): the service derives the blob server-side with an
## empty unit list, so no placed row is destroyed and the response proves every
## row byte-identical over the complete `items` mapping. The legacy server DOES
## destroy rows on that command — see probe 4 of the committed capture — and
## authoritative combat belongs to Server v1 / M13.
##
## Structured service errors pass through with their original codes — notably
## `missing_goal_index`, `invalid_goal_index`, `missing_key`, `invalid_key`,
## `ignored_quest_var_key`, `missing_mission`, `invalid_mission`,
## `missing_quest_index`, `invalid_quest_index`, `missing_quest_id`,
## `invalid_quest_id`, and `unresolvable_quest_state`, and the shared
## `missing_user_id` / `invalid_user_id` / `unknown_user_id` / `internal_error`
## family — all of which the client surfaces instead of advancing anything;
## transport failures keep the boot failure rules, never a partial payload.
func advance_quest_town(user_id: String, action: String,
		addressing: Variant) -> QuestFlow.QuestResult:
	var body := {
		"user_id": user_id,
		"action": action,
	}
	# The per-action wire key IS the addressing, and `wire_key()` is the ONE place
	# it is decided, so the body cannot drift from the key the service reads. An
	# action outside the closed table still yields exactly three keys, and the
	# service answers `invalid_action` before it looks at the addressing.
	body[QuestFlow.wire_key(action)] = addressing
	var outcome := await _call("POST", QUEST_PATH, JSON.stringify(body))
	if not outcome.get("ok", false):
		return QuestFlow.result_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return QuestFlow.parse_result(outcome.get("payload"))


## One tutorial **step** intent over loopback HTTP: the client sends the save
## identity and the client-sent step, and NOTHING else — exactly TWO keys. No
## completion flag, no reward, no vector, no price, and no outcome can be sent, so
## there is no channel through which a client could dictate a result: the service
## derives the gate from the committed expression, derives the
## `complete_tutorial` command, and executes the unchanged legacy branch with a
## NEUTRAL vector (tutorial design D2/D5).
##
## The step is **intent**. The legacy server owns the gate, so a client that
## guesses the thresholds wrong is refused by the service rather than believed.
##
## Any `completed_tutorial` / `flag` / `resources` / `vector` / `price` /
## `reward` / `result` / `gate` key the service receives alongside the identity
## is **ignored** server-side, exactly as the collect, expand, level-up, and
## research routes ignore client-supplied amounts and prices.
##
## The response's post-execution proof is two-part: the changed-leaf list must be
## exactly the single flag leaf for a dispatched completion and **empty** for
## either no-op, and **every stored resource must be unchanged**, because a
## tutorial completion moves none.
##
## **No step, ratio, remaining time, or total step count is reported** (design
## D1): the legacy `tutorial_step` is a branch-local and is never persisted, so
## the save carries no progress position and the typed parser **refuses** a
## response claiming one. **No reward** is reported and none is committed
## (design D6). **No bounds** are reported: the legacy gate has none, and adding
## one would be an invented rule (design D7, Server v1 / M13).
##
## **The deliberate divergence is confined to failure handling**: `"15"`, a
## missing argument, and `null` each raise in the legacy server and escape as
## HTTP 500, and this line answers each with a named refusal instead. A crash is
## not a behaviour. Every accepted step's state transition is reproduced exactly.
##
## Structured service errors pass through with their original codes — notably
## `invalid_step`, `missing_step`, `null_step`, and
## `unresolvable_tutorial_state`, and the shared `missing_user_id` /
## `invalid_user_id` / `unknown_user_id` / `invalid_payload` /
## `internal_error` family — all of which the client surfaces instead of
## completing anything; transport failures keep the boot failure rules, never a
## partial payload.
func complete_tutorial_town(user_id: String,
		step: int) -> TutorialFlow.TutorialResult:
	var outcome := await _call("POST", TUTORIAL_PATH, JSON.stringify({
		"user_id": user_id,
		"step": step,
	}))
	if not outcome.get("ok", false):
		return TutorialFlow.result_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return TutorialFlow.parse_result(outcome.get("payload"))


const STORED_PLACE_PATH := "/v0/place_stored"
const STORED_SELL_PATH := "/v0/sell_stored"


## One stored-item placement intent over loopback HTTP: the client sends ONLY the
## save identity, the stored item id, and the target cell -- no map slot, no row,
## no attribute bag, no player team, no stored count, no quantity, and no price.
## Any `map_key`/`index`/`item_index`/`attr`/`player`/`team`/`quantity`/`price`/
## `cost`/`resources` key this body carries is DISCARDED, exactly as a
## client-supplied amount is discarded on the collect, expand, level-up,
## collection, and revival routes: the server derives the map slot, the row
## instant, the garrison, the team, and the attribute bag (design D2/D3).
##
## **No price moves and none is sent**, because all 24 executed probe
## transactions left every stored resource byte-identical and the branch reads
## the client's vector nowhere.
func place_stored_item_town(user_id: String, item_id: int, x: int,
		y: int) -> BootData.StoredPlacementResult:
	var outcome := await _call("POST", STORED_PLACE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_id": item_id,
		"x": x,
		"y": y,
	}))
	if not outcome.get("ok", false):
		return BootData.stored_placement_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_stored_placement(outcome.get("payload"))


## One stored-item sale intent over loopback HTTP: the client sends ONLY the save
## identity and the stored item id. No price, no refund, no quantity, no return
## value is sent or accepted -- the legacy branch's entire effect is one store
## key disappearing (design D5), so a client-sent refund is ignored exactly as a
## client-sent price is ignored elsewhere.
func sell_stored_item_town(user_id: String,
		item_id: int) -> BootData.StoredSaleResult:
	var outcome := await _call("POST", STORED_SELL_PATH, JSON.stringify({
		"user_id": user_id,
		"item_id": item_id,
	}))
	if not outcome.get("ok", false):
		return BootData.stored_sale_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_stored_sell(outcome.get("payload"))


## One combat-action intent over loopback HTTP. The body is built by
## `CombatFlow.build_intent()` and is therefore **exactly three keys** -- the save
## identity, the closed action, and that action's addressing under its own wire
## key -- so no destruction count, no `sent`/`survived` pair, no resource delta,
## no honour, and no price is even expressible here (design D1/D2). This function
## deliberately names none of those: the refusal that a client-dictated count is
## a *client* attempt happens INSIDE `build_intent`, before any HTTP call, so no
## refused request ever reaches the service or a save.
func combat_town(user_id: String, action: Variant,
		addressing: Variant) -> CombatFlow.CombatResult:
	var intent := CombatFlow.build_intent(user_id, action, addressing)
	if not intent.get("ok", false):
		return CombatFlow.combat_failure(
			str(intent.get("reason", "bad_intent")),
			str(intent.get("error", "")))
	var outcome := await _call("POST", COMBAT_PATH,
		JSON.stringify(intent.get("body")))
	if not outcome.get("ok", false):
		return CombatFlow.combat_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return CombatFlow.parse_combat(outcome.get("payload"))


## One magic-counter intent over loopback HTTP. The body is built by
## `MagicFlow.build_magic_intent()` and is therefore **exactly three keys** -- the
## save identity, the closed action, and that action's addressing under its own
## wire key -- so a count, a delta, a resulting value, a cap, a price, and a
## damage magnitude are not expressible here (design D2). This function
## deliberately names none of them: the `client_dictated_count` refusal is a
## refusal of a HAND-BUILT request, and this body cannot be one.
##
## The identity is unwrapped through `MagicFlow.wire_magic_identity()` before it
## travels, because the engine decodes every JSON number as a `float` and the
## recorded legacy rule is that a magic identity is an **integer** -- so the
## decode is unwrapped in exactly one named place rather than by widening the
## canonical rule that exists to close the float hazard.
##
## ## The answer reports a divergence, and this function does not hide it
##
## The service pins the ledger against what the **unchanged legacy arm writes**,
## not against the derived transition, because design D3 requires those two to
## disagree for `buy` and for every absent key. Both values travel side by side
## and `MagicFlow.parse_magic()` re-derives the recorded arm's own arithmetic
## rather than trusting either number, so the recorded outcome is a check rather
## than an echo.
func magic_town(user_id: String, action: Variant,
		magic_id: Variant) -> MagicFlow.MagicResult:
	var intent := MagicFlow.build_magic_intent(user_id, action, magic_id)
	if not intent.get("ok", false):
		return MagicFlow.magic_failure(
			str(intent.get("reason", "bad_intent")),
			str(intent.get("error", "")))
	var outcome := await _call("POST", MAGIC_PATH,
		JSON.stringify(intent.get("body")))
	if not outcome.get("ok", false):
		return MagicFlow.magic_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return MagicFlow.parse_magic(outcome.get("payload"))


## every failure returns `{ok: false, code, message}` with the failure named.
func _call(method: String, path: String, body: String) -> Dictionary:
	var url := resolved_endpoint() + path
	var headers := PackedStringArray()
	var verb := HTTPClient.METHOD_GET
	if method == "POST":
		headers = PackedStringArray(["Content-Type: application/json"])
		verb = HTTPClient.METHOD_POST
	var request_error := _request.request(url, headers, verb, body)
	if request_error != OK:
		return _failure("request_failed",
			"cannot start the request to %s (error %d)" % [url, request_error])
	var completion: Array = await _request.request_completed
	var transport := int(completion[0])
	var status := int(completion[1])
	var raw: PackedByteArray = completion[3]
	if transport != HTTPRequest.RESULT_SUCCESS:
		return _failure("unreachable_endpoint", _transport_message(transport, url))
	if status == 0:
		return _failure("unreachable_endpoint", "no HTTP response from " + url)
	var parser := JSON.new()
	if parser.parse(raw.get_string_from_utf8()) != OK:
		return _failure("bad_response",
			"response from %s is not JSON (HTTP %d)" % [url, status])
	if not (parser.data is Dictionary):
		return _failure("bad_response",
			"response from %s is not a JSON object (HTTP %d)" % [url, status])
	var payload: Dictionary = parser.data
	if payload.get("ok") == false:
		return _structured_error(payload, status)
	if status < 200 or status >= 300:
		return _failure("bad_response",
			"HTTP %d from %s without a structured error" % [status, url])
	return {"ok": true, "payload": payload}


## The service's own structured error (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
func _structured_error(payload: Dictionary, status: int) -> Dictionary:
	var code := "bad_response"
	var message := "compatibility API reported an error (HTTP %d)" % status
	var error: Variant = payload.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return _failure(code, message)


func _failure(code: String, message: String) -> Dictionary:
	return {"ok": false, "code": code, "message": message}


## Names the transport failure the way the boot scene must display it.
## Every branch names the endpoint itself, because the boot scene must show
## *which* endpoint could not be reached, not a generic failure. Observed on
## the pinned engine (Windows x64): a refused loopback port is reported as
## `RESULT_TIMEOUT`, never as `RESULT_CANT_CONNECT`, so the timeout branch is
## the one the unreachable-endpoint scenario actually exercises.
func _transport_message(transport: int, url: String) -> String:
	match transport:
		HTTPRequest.RESULT_CANT_CONNECT:
			return "endpoint unreachable (connection refused): " + url
		HTTPRequest.RESULT_CANT_RESOLVE:
			return "endpoint unreachable (cannot resolve the loopback host): " + url
		HTTPRequest.RESULT_CONNECTION_ERROR:
			return "endpoint unreachable (connection error): " + url
		HTTPRequest.RESULT_TIMEOUT:
			return "endpoint unreachable (no response within %.0f seconds): " % REQUEST_TIMEOUT_SECONDS + url
		HTTPRequest.RESULT_NO_RESPONSE:
			return "endpoint unreachable (no HTTP response): " + url
		_:
			return "endpoint unreachable (transport error %d): %s" % [transport, url]
