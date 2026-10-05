extends Node
## `GameApi` autoload — the only bridge between presentation code and server
## data (design D5, spec "GameApi abstraction").
##
## Client code calls `list_sessions()` / `get_bootstrap()` for boot data,
## `place_building()` for one placement intent, `purchase_item()` for one
## purchase intent, `move_building()` for one move intent,
## `sell_building()` for one sell intent, `store_building()` for one
## store intent, `upgrade_building()` for one upgrade intent,
## `build_construction()` for one construction intent,
## `collect_income()` for one collection intent, `expand_town()` for one
## expansion intent, `level_up_town()` for one level-up intent,
## `push_queue_unit_town()` / `pop_queue_unit_town()` for one production-queue
## intent each, `complete_collection_town()` for one collection-completion
## intent, `resurrect_hero_town()` for one dead-hero revival intent, and
## `advance_research_town()` for one research-track intent,
## `advance_quest_town()` for one quest intent, and
## `complete_tutorial_town()` for one tutorial-step intent, receiving typed
## results (`scripts/gameapi/boot_data.gd`); raw transport dictionaries never
## reach presentation code, and no other script references a transport.
##
## Implementations, selected by the project setting `gameapi/implementation`
## (default `fake` so tests are hermetic):
##
##   fake      - reads the committed executed-legacy fixtures under
##               `tests/fixtures/godot-compatibility-boot/` (boot),
##               `tests/fixtures/godot-building-placement/` (placement),
##               `tests/fixtures/godot-item-purchase/` (purchase),
##               `tests/fixtures/godot-building-move/` (move),
##               `tests/fixtures/godot-building-sell/` (sell), and
##               `tests/fixtures/godot-building-store/` (store),
##               `tests/fixtures/godot-building-upgrade/` (upgrade), and
##               `tests/fixtures/godot-building-construction/`
##               (construction), `tests/fixtures/godot-building-collect/`
##               (collection), and `tests/fixtures/godot-building-expand/`
##               (expansion), `tests/fixtures/godot-building-xp/`
##               (level), and `tests/fixtures/godot-unit-queues/`
##               (queue), and `tests/fixtures/godot-unit-collection/`
##               (collection completion); no process, no server, no socket.
##   legacy_v0 - JSON over loopback HTTP to Compatibility API v0 through the
##               built-in HTTP request client; endpoint from the project
##               setting `gameapi/endpoint` (default: loopback 127.0.0.1 on
##               the documented v0 port).
##
## Runtime overrides for verification (user arguments after `--`):
##
##   --gameapi=fake|legacy_v0   implementation switch
##   --gameapi-endpoint=<url>   endpoint override (legacy_v0 only)
##
## verify-boot.ps1 passes these explicitly; nothing outside `legacy_v0_api`
## ever names an endpoint (the scope test enforces that).

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const BehaviorFlow = preload("res://scripts/units/behavior_flow.gd")
const CombatFlow = preload("res://scripts/units/combat_flow.gd")
const MagicFlow = preload("res://scripts/units/magic_flow.gd")
const ResearchFlow = preload("res://scripts/units/research_flow.gd")
const QuestFlow = preload("res://scripts/units/quest_flow.gd")
const TutorialFlow = preload("res://scripts/progression/tutorial_flow.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")
const LegacyV0Api = preload("res://scripts/gameapi/legacy_v0_api.gd")

const SETTING_IMPLEMENTATION := "gameapi/implementation"
const SETTING_ENDPOINT := "gameapi/endpoint"
const IMPL_FAKE := "fake"
const IMPL_LEGACY_V0 := "legacy_v0"
const ARG_IMPLEMENTATION := "--gameapi="
const ARG_ENDPOINT := "--gameapi-endpoint="

## Selected implementation: "fake" or "legacy_v0".
var implementation := IMPL_FAKE
## Endpoint for the legacy-v0 implementation ("" = the loopback default).
var endpoint := ""
## Number of bootstrap requests this process has issued (M6 launch
## contract: exactly one per launch — the legacy bootstrap mutates
## `last_logged_in`, so the boot suite asserts the count and the town
## evidence report records it). Monotonic: `configure()` swaps the
## implementation without hiding history, so callers snapshot and compare.
var bootstrap_requests := 0
## Number of placement intents this process has issued (M7 flow contract:
## exactly one per confirm, zero for invalid targets — the flow suite
## snapshots this counter exactly like `bootstrap_requests`). Monotonic for
## the same reason: `configure()` swaps the implementation without hiding
## history.
var placement_requests := 0
## Number of purchase intents this process has issued (M7 purchase flow
## contract: exactly one per confirm, zero for a refused confirm — the shop
## suite snapshots this counter exactly like `placement_requests`). Monotonic
## for the same reason: `configure()` swaps the implementation without
## hiding history.
var purchase_requests := 0
## Number of move intents this process has issued (building-move flow
## contract: exactly one per confirm, zero for every local refusal — the
## move suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var move_requests := 0
## Number of sell intents this process has issued (building-sell flow
## contract: exactly one per confirm, zero for every local refusal — the
## sell suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var sell_requests := 0
## Number of store intents this process has issued (building-store flow
## contract: exactly one per confirm, zero for every local refusal — the
## store suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var store_requests := 0
## Number of upgrade intents this process has issued (building-upgrade flow
## contract: exactly one per confirm, zero for every local refusal — the
## upgrade suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var upgrade_requests := 0
## Number of construction intents this process has issued (building-
## construction flow contract: exactly one per confirm, zero for every local
## refusal — the construction suite snapshots this counter exactly like
## `placement_requests`). Monotonic for the same reason: `configure()` swaps
## the implementation without hiding history.
var construction_requests := 0
## Number of collection intents this process has issued (building-collect flow
## contract: exactly one per confirm, zero for every local refusal — the
## collect suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var collect_requests := 0
## Number of expansion intents this process has issued (building-expand flow
## contract: exactly one per confirm, zero for every local refusal — the expand
## suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var expand_requests := 0
## Number of level-up intents this process has issued (building-xp flow
## contract: exactly one per confirm, zero for every local refusal — the XP
## suite snapshots this counter exactly like `placement_requests`). Monotonic
## for the same reason: `configure()` swaps the implementation without hiding
## history.
var level_up_requests := 0
## Number of production-queue intents this process has issued — the push and the
## pop together (unit-queues flow contract: exactly one per confirm, zero for
## every local refusal — the queue suite snapshots this counter exactly like
## `placement_requests`). Monotonic for the same reason: `configure()` swaps the
## implementation without hiding history.
var queue_requests := 0
## Number of collection-completion intents this process has issued (unit-collection
## flow contract: exactly one per confirm, zero for every local refusal — the
## collection suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation
## without hiding history.
var collection_requests := 0
## Number of revival intents this process has issued (unit-behaviors flow
## contract: exactly one per confirm, zero for every local refusal — the
## behavior suite snapshots this counter exactly like `placement_requests`).
## Monotonic for the same reason: `configure()` swaps the implementation without
## hiding history.
var behavior_requests := 0
## Number of research intents this process has issued (research flow contract:
## exactly one per confirm, zero for every local refusal — the research suite
## snapshots this counter exactly like `placement_requests`). Monotonic for the
## same reason: `configure()` swaps the implementation without hiding history.
var research_requests := 0
## Number of quest intents this process has issued (quest flow contract: exactly
## one per confirm, zero for every local refusal — the quest suite snapshots this
## counter exactly like `placement_requests`). Monotonic for the same reason:
## `configure()` swaps the implementation without hiding history.
var quest_requests := 0
## Number of tutorial intents this process has issued (tutorial flow contract:
## exactly one per confirm, zero for every local refusal — the tutorial suite
## snapshots this counter exactly like `placement_requests`). Monotonic for the
## same reason: `configure()` swaps the implementation without hiding history.
var tutorial_requests := 0
## Number of stored-item **placement** intents this process has issued. One per
## confirm on a stored item; zero for every local refusal. Monotonic for the same
## reason as the counters above: `configure()` swaps the implementation without
## hiding history.
var stored_placement_requests := 0
## Number of stored-item **sale** intents this process has issued. One per
## confirm; zero for every local refusal.
var stored_sale_requests := 0
## Number of combat-action intents this process has issued. One per intent; zero
## for every local refusal -- and note the counting boundary: a request refused
## for a client-dictated destruction count or an unknown action is refused by
## `CombatFlow.build_intent()` BEFORE this counter moves, because the refusal
## is about what the client tried to send.
var combat_requests := 0
## Number of magic-counter intents this process has issued. One per intent; zero
## for every local refusal -- and note the counting boundary: a request refused
## for a missing identity or an unknown action is refused by
## `MagicFlow.build_magic_intent()` BEFORE this counter moves, because the refusal
## is about what the client tried to send.
var magic_requests := 0

## The active implementation node (FakeApi or LegacyV0Api).
var _impl: Variant = null
var _configured := false


func _ready() -> void:
	if _configured:
		return
	configure(_resolve_implementation(), _resolve_endpoint())


## Selects and (re)builds the implementation. Tests call this explicitly to
## pin the implementation under examination; otherwise the selection comes
## from the project setting and the `--gameapi` / `--gameapi-endpoint`
## runtime overrides.
func configure(implementation_name: String, endpoint_url: String = "") -> void:
	var resolved := implementation_name
	if resolved != IMPL_FAKE and resolved != IMPL_LEGACY_V0:
		push_error("[gameapi] unknown implementation %r (expected %r or %r)"
			% [resolved, IMPL_FAKE, IMPL_LEGACY_V0])
		resolved = IMPL_FAKE
	_configured = true
	implementation = resolved
	endpoint = endpoint_url
	if _impl != null:
		_impl.queue_free()
		_impl = null
	if implementation == IMPL_LEGACY_V0:
		var legacy := LegacyV0Api.new()
		legacy.name = "LegacyV0Api"
		legacy.endpoint = endpoint
		add_child(legacy)
		_impl = legacy
	else:
		var fake := FakeApi.new()
		fake.name = "FakeApi"
		add_child(fake)
		_impl = fake


## Typed session list from the selected implementation.
func list_sessions() -> BootData.SaveListResult:
	var result: BootData.SaveListResult = await _impl.list_sessions()
	return result


## Typed bootstrap for one save id from the selected implementation.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	bootstrap_requests += 1
	var result: BootData.BootstrapResult = await _impl.get_bootstrap(user_id)
	return result


## One placement intent (anchor cell in the shared 0..99 town grid) from
## the selected implementation. The implementation derives the legacy
## envelope (design D3/D4); the typed result carries the authoritative
## entry and resources (design D7) — presentation code applies only these
## values, never a locally computed delta.
func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	placement_requests += 1
	var result: BootData.PlacementResult = await _impl.place_building(
		user_id, item_id, x, y, orientation)
	return result


## One purchase intent (a save id and a store item id) from the selected
## implementation. The contract carries NO price, NO quantity, and NO
## resource deltas: the implementation derives the legacy envelope from the
## item's own config (design D2/D3), so the typed result's storage mapping
## and resources are authoritative (design D4) — presentation code replaces
## its storage view and its resource values from these fields verbatim and
## never computes a delta.
func purchase_item(user_id: String, item_id: int) -> BootData.PurchaseResult:
	purchase_requests += 1
	var result: BootData.PurchaseResult = await _impl.purchase_item(
		user_id, item_id)
	return result


## One move intent (the legacy map index of an existing placement and its
## target cell in the shared 0..99 grid) from the selected implementation.
## The contract carries NO price and NO resource deltas: the service
## derives the legacy envelope server-side (design D2/D3), and the
## authoritative "this row now sits at this cell" superset is the SAME one
## the placement command returns, so the delivered typed placement result
## and parse function are reused verbatim (design D4). Presentation code
## therefore applies only these values — it never writes the cell it
## previewed, only the one the response reports.
func move_building(user_id: String, item_index: int, x: int,
		y: int) -> BootData.PlacementResult:
	move_requests += 1
	var result: BootData.PlacementResult = await _impl.move_building(
		user_id, item_index, x, y)
	return result


## One sell intent (the legacy map index of an existing placement) from the
## selected implementation. The contract carries NO price, NO refund, NO
## sell reason, and NO resource deltas: the service derives the legacy
## envelope server-side (design D3), so the typed result's removed row and
## resources are authoritative (design D5). The removed row is the one the
## service read BEFORE execution, so presentation code removes exactly the
## building the response names and takes the resource values verbatim.
func sell_building(user_id: String, item_index: int) -> BootData.SellResult:
	sell_requests += 1
	var result: BootData.SellResult = await _impl.sell_building(
		user_id, item_index)
	return result


## One store intent (the legacy map index of an existing placement) from the
## selected implementation. The contract carries NO price, NO quantity, NO
## resource deltas, and NO capacity: the service derives the legacy envelope
## server-side (design D3), so the typed result's removed row, storage
## mapping, and resources are authoritative (design D4). The removed row is
## the one the service read BEFORE execution and the storage mapping is the
## FULL post-execution one, so presentation code removes exactly the
## building the response names, replaces its storage view from the same
## shared parser, and takes the resource values verbatim — never a computed
## delta, never a locally incremented quantity.
func store_building(user_id: String,
		item_index: int) -> BootData.StoreResult:
	store_requests += 1
	var result: BootData.StoreResult = await _impl.store_building(
		user_id, item_index)
	return result


## One upgrade intent (the legacy map index of an existing placement) from
## the selected implementation. The contract carries NO target tier, NO
## reason, NO coordinates, NO orientation, NO player, NO quantity, NO
## price, and NO resource deltas: the service derives the target tier from
## the committed configuration, the reason from the committed legacy
## constant, and the cell, orientation, and player from the row being
## replaced (design D2/D3), so the typed result's two rows and resources
## are authoritative (design D5). The response carries the row as read
## BEFORE execution and the row re-read AFTER it — the same key and cell
## holding the new tier — so presentation code replaces the selected typed
## placement's row with `upgraded` and takes the resource values verbatim.
func upgrade_building(user_id: String,
		item_index: int) -> BootData.UpgradeResult:
	upgrade_requests += 1
	var result: BootData.UpgradeResult = await _impl.upgrade_building(
		user_id, item_index)
	return result


## One construction intent (the legacy map index of an existing placement and
## ONE action of the closed vocabulary `"start" | "click" | "finish"`) from the
## selected implementation. The contract carries NO duration, NO countdown,
## NO price, and NO resource deltas: the service derives the legacy command
## and every one of its arguments from committed content and the row's own
## state — the start duration from the item's committed `build_time`, never
## from the client — so the typed result's two rows, resolved action, and
## resources are authoritative (design D2/D3/D5). The response carries the row
## as read BEFORE execution and the row re-read AFTER it, so presentation code
## replaces the selected typed placement's row with `row` and takes the
## resource values verbatim. Legacy command names are never accepted.
func build_construction(user_id: String, item_index: int,
		action: String) -> BootData.ConstructionResult:
	construction_requests += 1
	var result: BootData.ConstructionResult = await _impl.build_construction(
		user_id, item_index, action)
	return result


## One collection intent (the legacy map index of an existing placement) from
## the selected implementation. The contract carries NO amount, NO resource,
## NO tier, NO time, NO price, and NO resource deltas: the service derives the
## legacy envelope, the committed-income payout, and the ladder rung entirely
## server-side from the addressed item's own content and the row's own state
## (design D7), so the typed result's two rows, payout, tier, reference
## instant, and resources are authoritative (design D8). The response carries
## the row as read BEFORE execution and the row re-read AFTER it, so
## presentation code replaces the selected typed placement's row with `row`,
## takes the balances and experience from `resources`, and evaluates its
## readout against `reference_time` — never against its own clock and never
## against its own arithmetic.
func collect_income(user_id: String,
		item_index: int) -> BootData.CollectResult:
	collect_requests += 1
	var result: BootData.CollectResult = await _impl.collect_income(
		user_id, item_index)
	return result


## One expansion intent (a save id and the expansion id the client addressed
## the committed positional schedule with) from the selected implementation.
## The contract carries NO amount, NO resource, NO price, NO requirement flag,
## and NO resource deltas: the service reads the id's own committed row in the
## 98-entry `expansion_prices` schedule, derives the eight-slot **debit** from
## it, and executes the unchanged legacy `expand` branch (design D1/D2/D5), so
## the typed result's two owned lists, debit, committed row, and resources are
## authoritative (design D8). The response carries the owned ledger as read
## BEFORE execution and the same ledger re-read AFTER it, so presentation code
## takes the ledger and the balances from the response verbatim and never
## appends an id, never applies a debit, and never uses its own arithmetic —
## the response wins even where the two disagree.
func expand_town(user_id: String,
		expansion_id: int) -> BootData.ExpandResult:
	expand_requests += 1
	var result: BootData.ExpandResult = await _impl.expand_town(
		user_id, expansion_id)
	return result


## One level-up intent (the save identity and NOTHING else) from the selected
## implementation. The contract carries NO level, NO new level, NO experience,
## NO threshold, NO reward, and NO resource deltas: the service reads the
## stored experience, derives the level the committed `levels` curve implies
## for it through the ONE named one-based conversion, and executes the
## unchanged legacy `level_up` branch with a NEUTRAL vector (design D3/D5) — so
## a client-supplied level key is ignored exactly as a client-supplied amount or
## price is ignored elsewhere, and the typed result's `derived_level`,
## `level_before`, `level_after`, `curve`, and `resources` are authoritative
## (design D8). The response's second post-execution proof half requires every
## stored resource to be **unchanged**, because a level change moves none.
##
## The client applies the recorded level and the balances from the response
## **verbatim** and discards its own derived level even where the two disagree,
## so a wrong client-side derivation can never be silently compounded.
func level_up_town(user_id: String) -> BootData.LevelUpResult:
	level_up_requests += 1
	var result: BootData.LevelUpResult = await _impl.level_up_town(user_id)
	return result


## One production-queue **push** intent (the save identity and the target row's
## key, and NOTHING else) from the selected implementation. The contract carries
## NO count, NO cost, NO duration, NO training time, NO readiness, and NO
## resource deltas: the service derives `push_queue_unit` from the closed action
## vocabulary, reads nothing but the addressed row, and executes the unchanged
## legacy branch with a NEUTRAL vector (unit-queues design D2/D4/D5) — so a
## client-supplied outcome key is ignored exactly as a client-supplied amount or
## price is ignored elsewhere, and the typed result's two rows, `queue`, and
## `resources` are authoritative (design D8). The response's second
## post-execution proof half requires every stored resource to be
## **unchanged**, because a queue moves none.
##
## **No unit is created by this intent**: the legacy server has no command that
## completes a queue or materialises a unit from one, so a push is a count and a
## start instant and nothing more (design D1/D2).
func push_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	queue_requests += 1
	var result: BootData.QueueResult = await _impl.push_queue_unit_town(
		user_id, map_key)
	return result


## One production-queue **pop** intent (the save identity and the target row's
## key, and NOTHING else) from the selected implementation. The contract carries
## no count, cost, duration, or outcome: the service derives
## `pop_queue_unit`, and the legacy branch's own rules are the whole contract —
## it decrements the count, re-stamps the start instant on a partial decrement,
## and **deletes `nu`, `ts`, and `ui` together** at zero (design D1/D3). No
## producer, duration, level, or count check is added, and **no maximum count is
## applied** anywhere, because the legacy engine sets none (design D5).
##
## A pop against a row whose bag carries no count is an **inert recorded
## no-op**, not an error: the endpoint answers success with an unchanged bag. The
## client simply does not offer it (`queue_flow.offers_pop()`), and this facade
## adds no gate of its own — the service's own guards decide.
func pop_queue_unit_town(user_id: String,
		map_key: int) -> BootData.QueueResult:
	queue_requests += 1
	var result: BootData.QueueResult = await _impl.pop_queue_unit_town(
		user_id, map_key)
	return result


## One collection-completion intent (the save identity and a collection id, and
## NOTHING else) from the selected implementation. The contract carries NO prize,
## NO item id, NO quantity, NO price, and NO resource deltas: the service looks
## the grant up in the committed `collections` table and executes the unchanged
## legacy `complete_collection` branch with a NEUTRAL vector (unit-collection
## design D1/D5) — so a client-supplied prize/item/quantity key is ignored
## exactly as a client-supplied amount or price is ignored elsewhere, and the
## typed result's `item_id`, `quantity`, `prize`, `store_after`, and `resources`
## are authoritative (design D8). The response carries the storage and the
## collection ledger as read BEFORE execution and re-read AFTER it, plus the
## index resolution with its **alias**, so presentation code never appends an id,
## never grants an item, and never applies its own arithmetic — the response
## wins even where the two disagree.
##
## **No eligibility is checked** and none is invented (design D2): the legacy
## server verifies nothing about whether a collection was earned, so a caller may
## name any of the ten committed collections. What a caller cannot do is choose
## the contents.
func complete_collection_town(user_id: String,
		collection_id: int) -> BootData.CollectionResult:
	collection_requests += 1
	var result: BootData.CollectionResult = await _impl.complete_collection_town(
		user_id, collection_id)
	return result


## One revival intent (the save identity and the addressed **cell**, and NOTHING
## else) from the selected implementation.  The contract carries NO map key, NO
## revived item id, NO syringe count, NO price, and NO resource deltas: the
## service derives the map key from the addressed cell's own placement row and
## the revived item id from the player's own recorded `deadHeroes` ledger, then
## executes the unchanged legacy `resurrect_hero` branch with a NEUTRAL vector
## (unit-behaviors design D2/D3) — so a client-supplied item id, key, or
## syringe count is ignored exactly as a client-supplied amount or price is
## ignored elsewhere, and the typed result's `map_key`, `item_id`, both ledgers,
## both placements, and `resources` are authoritative (design D8).  The response
##'s second post-execution proof half requires every stored resource to be
## **unchanged**, because a revival moves none.
##
## **No combat is resolved** and the revived placement is **not validated**: the
## committed combat fields have zero legacy consumers and the legacy branch
## re-places the row with no occupancy, bounds, type, or terrain check
## (design D5).  Both absences travel on the typed result.
func resurrect_hero_town(user_id: String, x: int,
		y: int) -> BehaviorFlow.ResurrectResult:
	behavior_requests += 1
	var result: BehaviorFlow.ResurrectResult = await _impl.resurrect_hero_town(
		user_id, x, y)
	return result


## One research-track intent (the save identity, a **closed action**, and the
## research **track** — and NOTHING else) from the selected implementation. The
## contract carries NO counter value, NO research instant, and NO cash amount:
## the service derives every counter itself, derives the cash branch's own
## argument, and executes the unchanged legacy branch with a NEUTRAL vector
## (research design D2/D3) — so a client-supplied step, item, timestamp, or cash
## key is ignored exactly as a client-supplied amount or price is ignored
## elsewhere, and the typed result's `derived`, `vector_before`,
## `vector_after`, `research`, and `resources` are authoritative.
##
## The response's second post-execution proof half requires **every** stored
## resource to be **unchanged**, because a research action moves none.
##
## **No readiness and no completion** are reported (design D1): all three
## counters are write-only in the legacy source, so there is no rule to derive,
## and the response's projection carries an explicitly empty `derived` block.
## **No price is reported** — `cash_charged` is the derived `0`, the cash
## branch's own argument is discarded by the legacy code, and
## `fast_forward_offered` is `false`: the research instant's fourth writer is
## recorded and delivered not at all (design D7).
##
## The client applies `vector_after` and `resources` **verbatim**, so a wrong
## client-side expectation can never be silently compounded.
func advance_research_town(user_id: String, action: String,
		track: int) -> ResearchFlow.ResearchResult:
	research_requests += 1
	var result: ResearchFlow.ResearchResult = await _impl.advance_research_town(
		user_id, action, track)
	return result


## One quest intent (the save identity, a **closed action**, and the branch's own
## **addressing** - and NOTHING else) from the selected implementation. The
## contract carries NO progress pair, NO quest-variable value, NO difficulty, NO
## win/loss outcome, and NO unit list: the service derives every value it writes,
## derives the whole `end_quest` blob, and executes the unchanged legacy branch
## with a NEUTRAL vector (quest design D2/D6) - so a client-supplied `progress`,
## `value`, `difficulty`, `win`, `units`, `lost`, `reward`, `price`, or
## `resources_changed` key is ignored exactly as a client-supplied amount or price
## is ignored elsewhere, and the typed result's `derived`, `quest_state`,
## `quests`, and `resources` are authoritative.
##
## The response's second post-execution proof half requires **every** stored
## resource to be **unchanged**, because a quest action moves none.
##
## **No completion, no elapsed time, and no reward** are reported (design D1/D6):
## `complete_goal` writes nothing at all, no legacy branch reads a quest instant,
## and the committed `reward` field has zero consumers and is uniformly 10 - so
## `reward_paid` is the derived `0`, `reward_derived_from_content` is `false`,
## `fast_forward_offered` is `false` (the seventh writer of quest state is recorded
## and delivered not at all, design D9), and `unlocked_quest_index_written` is
## `false` (that field has zero legacy consumers, design D7).
##
## **The `end_quest` destruction count is REFUSED** and reported as a
## **DIVERGENCE**, not as parity (design D2): the derived blob carries an empty
## unit list, no placed row is destroyed, and `destruction` states both the refusal
## and the byte-identical whole-row-set proof. The legacy server DOES destroy
## rows on that command.
##
## The client applies `quest_state` and `resources` **verbatim**, so a wrong
## client-side expectation can never be silently compounded.
func advance_quest_town(user_id: String, action: String,
		addressing: Variant) -> QuestFlow.QuestResult:
	quest_requests += 1
	var result: QuestFlow.QuestResult = await _impl.advance_quest_town(
		user_id, action, addressing)
	return result


## One tutorial **step** intent (the save identity and the client-sent step, and
## NOTHING else) from the selected implementation.
##
## The contract carries **no** completion flag, **no** reward, **no** resource
## vector, **no** price, and **no** outcome: the service derives the gate from the
## committed expression, derives the `complete_tutorial` command, and executes the
## unchanged legacy branch (`command.py:60-66`) with a NEUTRAL vector
## (tutorial design D2/D4/D5) — so a client-supplied flag, vector, amount, or
## price is ignored exactly as a client-supplied amount or price is ignored
## elsewhere, and the typed result's `tutorial`, `gate`, `changed`, and
## `resources` are **authoritative** (design D8).
##
## The step is **intent**: the legacy server owns the gate, so a client that
## guesses the thresholds wrong is refused by the service rather than believed.
## The response's post-execution proof is two-part — the changed-leaf list must be
## exactly the single flag leaf for a dispatched completion and **empty** for
## either no-op, and **every stored resource must be unchanged**, because a
## tutorial completion moves none.
##
## **No step, ratio, remaining time, or total step count is reported** (design
## D1): the legacy `tutorial_step` is a branch-local and is never persisted, so
## the save carries no progress position and deriving one would fabricate it.
## **No reward is reported**, and none is committed. **No bounds are reported**:
## the legacy gate has no upper bound, no lower bound, and no type check
## (design D7), and adding one would be an invented rule — authoritative
## validation belongs to Server v1 / M13.
##
## The **deliberate divergence** is confined to failure handling: `"15"`, a
## missing argument, and `null` each raise in the legacy server and escape as
## HTTP 500, and this line answers each with a named refusal instead. A crash is
## not a behaviour. Every accepted step's **state transition** is reproduced
## exactly.
##
## Structured service errors pass through with their original codes — notably
## `invalid_step`, `missing_step`, `null_step`, and
## `unresolvable_tutorial_state`, plus `missing_user_id`, `invalid_user_id`,
## `unknown_user_id`, `invalid_payload`, and `internal_error`; transport failures
## keep the boot failure rules, never a partial payload.
func complete_tutorial_town(user_id: String,
		step: int) -> TutorialFlow.TutorialResult:
	tutorial_requests += 1
	var result: TutorialFlow.TutorialResult = await _impl.complete_tutorial_town(
		user_id, step)
	return result


## One stored-item placement intent (the save identity, the stored **item id**,
## and the target **cell** -- and NOTHING else) from the selected
## implementation.  The contract carries NO map slot, NO row, NO attribute bag,
## NO player team, NO stored count, NO quantity, and NO price (stored-item
## placement design D2/D3): the service derives the map slot as the smallest
## positive absent integer, the row's instant from the server clock, the garrison
## as an always-empty list, the team as always `1`, and the attribute bag as the
## service's pure function of two committed fields -- so a client-supplied slot,
## bag, team, count, or price is ignored exactly as a client-supplied amount is
## ignored on the collect, expand, level-up, collection, and revival routes, and
## the typed result's `map_key`, `row`, `attr`, `player`, and `resources` are
## authoritative (design D8).
##
## The post-execution proof has two halves and **no resource moved** is one of
## them: all 24 executed probe transactions in the committed investigation left
## every stored resource byte-identical, because the branch reads the client's
## vector nowhere and `apply_resources` runs BEFORE it.
##
## **Bounds and cell occupancy are NOT refused** and that is deliberate
## (design D4): `place_stored_item [43, 1085, 250, -3, ...]` stored `(250, -3)`
## verbatim.  That is the already-recorded M6 tile-to-cell geometry gap, which
## needs new EVIDENCE rather than a derivation, so the typed result carries
## `bounds_refused`/`cell_occupancy_refused` as `false` plus the recorded note.
## What IS refused, each a recorded divergence from an oracle that answers
## `{"result": "success"}` in all four cases, is `not_in_storage`,
## `slot_occupied` (which would otherwise silently REPLACE an existing row while
## the row count stayed unchanged), `unknown_item_id`, and
## `item_not_placeable`.
func place_stored_item_town(user_id: String, item_id: int, x: int,
		y: int) -> BootData.StoredPlacementResult:
	stored_placement_requests += 1
	var result: BootData.StoredPlacementResult = await _impl.place_stored_item_town(
		user_id, item_id, x, y)
	return result


## One stored-item sale intent (the save identity and the stored **item id** --
## and NOTHING else) from the selected implementation.  The contract carries NO
## price, NO refund, NO quantity, and NO return value: the legacy branch reads
## `args[0]`, calls `remove_store_item`, and prints (design D5).  Its entire
## effect is one store key disappearing, so the typed result's `credited` is
## read from the response and asserted `false`, and the post-execution proof
## requires **every stored resource to be unchanged** -- which is what makes
## "a sale credits nothing" non-tautological rather than a comment.
##
## The ledger is left alone by a sale and the placement set is unchanged, and
## both are reported so the readout can say so honestly.
func sell_stored_item_town(user_id: String,
		item_id: int) -> BootData.StoredSaleResult:
	stored_sale_requests += 1
	var result: BootData.StoredSaleResult = await _impl.sell_stored_item_town(
		user_id, item_id)
	return result


## One combat-action intent (the save identity, a closed `action`, and that
## action's addressing) from the selected implementation. The addressing is the
## LOST UNIT'S **IDENTITY** for `resolve`, the map key for `kill`, and the item id
## for `kill_iid` -- never a count.
##
## The destruction count is derived server-side and is always 0 or 1 (design D1).
## A client that sends one is refused by `CombatFlow.build_intent()` before the
## transport is touched, and the refusal is a NAMED one, separate from the
## server-side eligibility check: "you may not dictate this" and "there is
## nothing to destroy" are different answers (design D2).
func combat_town(user_id: String, action: Variant,
		addressing: Variant) -> CombatFlow.CombatResult:
	combat_requests += 1
	var result: CombatFlow.CombatResult = await _impl.combat_town(
		user_id, action, addressing)
	return result


## One magic-counter intent (the save identity, a closed `action`, and the magic
## **identity**) from the selected implementation. The identity is a spell id,
## never a count, a cap, or a map key.
##
## The counter transition is derived server-side from the player's own recorded
## ledger. A client that tries to send a count is refused by
## `MagicFlow.build_magic_intent()` before the transport is touched, and the
## refusal is a NAMED one, separate from the endpoint's server-side refusals:
## "you may not say how many" and "there is nothing to buy" are different answers.
##
## ## The recorded divergence is reported, not smoothed
##
## The answer carries the value the **unchanged legacy arm writes** *and* the
## value this service derives, side by side, plus whether they agree. On an absent
## key and for `buy` they do **not** agree -- that is the divergence this line
## exists to report, so a caller that sees `matches_derived == false` is seeing a
## measured difference between the two implementations, not a defect.
func magic_town(user_id: String, action: Variant,
		magic_id: Variant) -> MagicFlow.MagicResult:
	magic_requests += 1
	var result: MagicFlow.MagicResult = await _impl.magic_town(
		user_id, action, magic_id)
	return result


## Short transport description for the boot scene's connection state.
func describe_transport() -> String:
	if implementation == IMPL_FAKE:
		return "fake fixtures, offline"
	var legacy := _impl as LegacyV0Api
	if legacy != null:
		return legacy.resolved_endpoint()
	return ""


## The implementation the next call will use, for test assertions.
func implementation_name() -> String:
	return implementation


static func _user_arg(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


func _resolve_implementation() -> String:
	var from_arg := _user_arg(ARG_IMPLEMENTATION)
	if from_arg != "":
		return from_arg
	var from_setting := str(ProjectSettings.get_setting(
		SETTING_IMPLEMENTATION, IMPL_FAKE))
	if from_setting == "":
		return IMPL_FAKE
	return from_setting


func _resolve_endpoint() -> String:
	var from_arg := _user_arg(ARG_ENDPOINT)
	if from_arg != "":
		return from_arg
	return str(ProjectSettings.get_setting(SETTING_ENDPOINT, ""))
