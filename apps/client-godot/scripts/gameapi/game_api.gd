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
## expansion intent, and `level_up_town()` for one level-up intent, receiving
## typed results
## (`scripts/gameapi/boot_data.gd`); raw transport dictionaries never reach
## presentation code, and no other script references a transport.
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
##               (expansion), and `tests/fixtures/godot-building-xp/`
##               (level); no process, no server, no socket.
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
