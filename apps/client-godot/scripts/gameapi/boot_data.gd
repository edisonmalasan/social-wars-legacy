extends RefCounted
## Typed boot data crossing the GameApi boundary (design D5, spec
## "GameApi abstraction").
##
## The `PlacementResult` class serves BOTH mutating map commands: the
## placement command and the move command answer with the identical
## authoritative superset — the legacy result, the persisted eight-field
## placement entry re-read from the save, and the current resources — so
## one result class and one parse function back both (building-move
## design D4). Nothing about the row distinguishes the two; only the
## request contract and the endpoint path differ.
##
## The sell command needs its own result class for one reason only: its
## eight-field row is the one AS READ BEFORE EXECUTION (building-sell
## design D5), because the persisted save no longer holds it and
## reconstructing it afterwards would be fabrication. `SellResult` reuses
## the very same typed entry class (`Placement`) for that row, so the
## shape is never duplicated — only the envelope and the parse function
## are the command's own.
##
## The store command needs its own result class for the same one reason
## (`removed` is the pre-execution row), plus the FULL post-execution
## storage mapping, which names the other half of the move
## (building-store design D4): `StoreResult` therefore reuses the typed
## entry class for `removed` AND the very same storage parser the
## purchase response uses for `store`, so the storage mapping can never
## be read by two rule sets.
##
## The upgrade command needs its own result class because its response is
## TWO-SIDED and both sides are the same shape: the row AS READ BEFORE
## EXECUTION (`removed`, the very row the client named) and the row re-read
## from the save after execution (`upgraded`). Nothing in the envelope
## distinguishes the sides but the key, so both go through the one typed
## entry parser every other response uses — a row can never be read with
## two rule sets (building-upgrade design D5). The upgraded row's timestamp
## is the documented time-dependent field (the purchase half stamps a fresh
## wall-clock epoch), so no test asserts it by value.
##
## The construction command needs its own result class because its three
## actions share ONE envelope that is two-sided and adds the action the
## service resolved: the row AS READ BEFORE EXECUTION (`previous`, the very
## row the client named) and the row re-read from the save after execution
## (`row`, carrying the countdown, the click counter, or neither). Both sides
## are the same shape, so both go through the one typed entry parser every
## other response uses — a row can never be read with two rule sets
## (building-construction design D3/D5). The row's start instant is the
## documented time-dependent field (legacy stamps it with `time_now()`), so no
## test asserts it by value.
##
## Presentation code never receives raw transport dictionaries: every
## GameApi operation returns one of the result classes below, and the two
## legacy JSON payloads (game config, player info) are wrapped in payload
## classes that only the API layer unpacks. The parse functions are shared
## by both implementations, so `FakeApi` and `LegacyV0Api` produce the same
## typed shapes by construction (spec: "Boot offline with the fake
## implementation").

## The v0 protocol identifier every envelope must carry.
const PROTOCOL := "compat-v0"

## The closed action vocabulary of the v0 construction endpoint (building-
## construction design D2). These are the endpoint's OWN outcome names, NOT
## legacy command names: the client chooses an outcome and the service chooses
## the legacy command. The set is closed and echoed exactly as sent, so a
## response naming anything else is a `bad_response`, never a guess.
const CONSTRUCTION_ACTIONS := ["start", "click", "finish"]


## One saved village exactly as the v0 session list reports it.
class SaveInfo:
	extends RefCounted
	var id := ""
	var name := ""
	var xp := 0
	var level := 0


## The boot summary the boot scene displays (name, level, xp), derived from
## the save entry of the bootstrapped user id.
class PlayerSummary:
	extends RefCounted
	var user_id := ""
	var name := ""
	var level := 0
	var xp := 0


## Legacy `get_game_config()` payload: a Dictionary only because the legacy
## payload itself is one; opaque to presentation code.
class ConfigPayload:
	extends RefCounted
	var raw: Dictionary = {}


## Legacy `get_player_info()` payload: opaque like the config, except the
## player's display name, which is typed for convenience.
class PlayerInfoPayload:
	extends RefCounted
	var raw: Dictionary = {}
	var player_name := ""


## Result of `list_sessions()`.
class SaveListResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	var server_time := 0
	## Array of `SaveInfo`.
	var saves: Array[SaveInfo] = []
	var error_code := ""
	var error_message := ""


## Result of `get_bootstrap()`: the session envelope plus the typed summary
## and the two wrapped legacy payloads.
class BootstrapResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	var server_time := 0
	## Array of `SaveInfo`.
	var saves: Array[SaveInfo] = []
	var summary: PlayerSummary = null
	var config: ConfigPayload = null
	var player_info: PlayerInfoPayload = null
	var error_code := ""
	var error_message := ""


## One persisted placement entry exactly as the v0 service reports it — the
## legacy eight-field array (item, x, y, timestamp, orientation, store,
## attr, player) written by `engine.map_add_item`.
class Placement:
	extends RefCounted
	var item_id := 0
	var x := 0
	var y := 0
	## Wall-clock seconds the legacy server stamped when the entry was
	## written: a time-dependent field, so tests assert positivity and
	## identity with the fixture epoch, never a fixed value.
	var timestamp := 0
	var orientation := 0
	## Legacy `store` / `attr` structures — opaque to presentation code,
	## carried in canonical legacy form (integral numbers as `int`, since
	## the JSON transport widens them on the pinned engine while the legacy
	## save stores ints; see `_canonicalize`).
	var store: Array = []
	var attr: Dictionary = {}
	var player := 0


## Authoritative post-application resources a placement response carries —
## the seven stored slots of the legacy resource vector (its unread
## `unknown` slot 0 has no stored value). The client applies only these
## values; it never computes its own delta (design D7).
class Resources:
	extends RefCounted
	var xp := 0
	var gold := 0
	var wood := 0
	var oil := 0
	var steel := 0
	var cash := 0
	var mana := 0


## Result of `place_building()`: the legacy result plus the authoritative
## superset (design D7), or a structured failure with no partial payload.
class PlacementResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	## The legacy result string ("success"); "" on failure.
	var result := ""
	var placement: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `purchase_item()`: the legacy result plus the authoritative
## superset (design D4) — the FULL post-execution storage mapping
## (`{str(item_id): int}`) and the same `Resources` object the placement
## response carries — or a structured failure with no partial payload. The
## client replaces its storage view and its resource values from these
## fields verbatim; it never computes a delta (design D7 carry-forward).
class PurchaseResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The whole storage mapping: string item id -> integer quantity. Quantity
	## `0` is preserved (observed in real saves) and an id the content package
	## cannot resolve is carried verbatim, never dropped.
	var store: Dictionary = {}
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `sell_building()`: the legacy result plus the authoritative
## superset (building-sell design D5) — the eight-field row AS READ BEFORE
## EXECUTION (the authoritative record of exactly what the client asked
## to remove; the persisted save no longer holds it) and the current
## resources — or a structured failure with no partial payload. The
## removed row reuses the typed `Placement` entry class, so the shape is
## never duplicated. The client removes the selected typed placement and
## frees its rendered object on success, and never computes a resource
## delta: the derived price vector is NEUTRAL, so a sale claims no refund.
class SellResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The removed row exactly as it was read before execution.
	var removed: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Result of `store_building()`: the legacy result plus the two-sided
## authoritative superset (building-store design D4) — the eight-field row
## AS READ BEFORE EXECUTION (the persisted save no longer holds it, and
## reconstructing it afterwards would be fabrication) AND the FULL
## post-execution storage mapping (`{str(item_id): int}`, the very shape
## `PurchaseResult.store` carries, parsed by the very same helper) plus the
## current resources — or a structured failure with no partial payload.
## The client removes the selected typed placement, frees its rendered
## object, replaces its storage view from `store` through the shared
## `TownState` storage parser, and takes the resource values verbatim: the
## derived price vector is NEUTRAL, so a store claims no cost and no
## capacity rule, and it deliberately writes no bought-units bookkeeping.
class StoreResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The removed row exactly as it was read before execution.
	var removed: Placement = null
	## The whole post-execution storage mapping: string item id -> integer
	## quantity, in the same shape and through the same parser the
	## purchase response uses (one storage rule, three entry points).
	var store: Dictionary = {}
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `list_sessions()` (never a partial payload).
static func save_list_failure(code: String, message: String) -> SaveListResult:
	var result := SaveListResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `get_bootstrap()` (never a partial payload).
static func bootstrap_failure(code: String, message: String) -> BootstrapResult:
	var result := BootstrapResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `place_building()` (never a partial payload).
static func placement_failure(code: String, message: String) -> PlacementResult:
	var result := PlacementResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `purchase_item()` (never a partial payload).
static func purchase_failure(code: String, message: String) -> PurchaseResult:
	var result := PurchaseResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `sell_building()` (never a partial payload).
static func sell_failure(code: String, message: String) -> SellResult:
	var result := SellResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Structured failure for `store_building()` (never a partial payload).
static func store_failure(code: String, message: String) -> StoreResult:
	var result := StoreResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Result of `upgrade_building()`: the legacy result plus the two-sided
## authoritative superset (building-upgrade design D5) — the eight-field row
## AS READ BEFORE EXECUTION (`removed`, the row the client asked to replace)
## AND the same eight-field row RE-READ FROM THE SAVE after execution
## (`upgraded`, holding the derived target tier at the same key and cell) —
## plus the current resources — or a structured failure with no partial
## payload. The client replaces the selected typed placement's row with
## `upgraded`, keeps the placement's own legacy key, cell, and depth order,
## and takes the resource values verbatim: the derived vector is NEUTRAL, so
## an upgrade claims NO cost of any kind, and the `{"nc": 0}` construction
## counter the purchase half seeds is reported as it arrives and deliberately
## NOT consumed (the construction-timer line owns it).
class UpgradeResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The row exactly as it was read before execution.
	var removed: Placement = null
	## The row re-read from the save after execution (the target tier at the
	## same key and cell, with a fresh timestamp and the purchase half's
	## attribute seed).
	var upgraded: Placement = null
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `upgrade_building()` (never a partial payload).
static func upgrade_failure(code: String, message: String) -> UpgradeResult:
	var result := UpgradeResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Result of `build_construction()`: the legacy result plus the two-sided
## authoritative superset and the action the service resolved
## (building-construction design D3/D5) — the eight-field row AS READ BEFORE
## EXECUTION (`previous`, the row the client named) AND the same row RE-READ
## FROM THE SAVE after execution (`row`, carrying the recorded countdown, the
## raised click counter, or neither) — plus the current resources.
##
## The resolved `action` is echoed exactly as the service received it, so the
## client renders the same vocabulary it sent. The derived vector is NEUTRAL,
## so a construction claims **NO building cost of any kind**: the committed
## configuration records no price for building, and the global that does
## (`BUILD_SPEEDUP_PRICING`) prices a speedup, which is out of scope.
##
## `row.timestamp` is the documented time-dependent field: a start re-stamps
## it with the wall clock, so it is asserted as a positive integer and never
## by value.
class ConstructionResult:
	extends RefCounted
	var ok := false
	var protocol := ""
	var game_version := ""
	## Wall-clock seconds the legacy server stamped (a time-dependent field,
	## so tests assert positivity, never a fixed value).
	var server_time := 0
	## The legacy result string ("success"); "" on failure.
	var result := ""
	## The row exactly as it was read before execution.
	var previous: Placement = null
	## The row re-read from the save after execution.
	var row: Placement = null
	## The action the service resolved, echoed from the closed vocabulary
	## ("start", "click", "finish"); "" on failure.
	var action := ""
	var resources: Resources = null
	var error_code := ""
	var error_message := ""


## Structured failure for `build_construction()` (never a partial payload).
static func construction_failure(code: String,
		message: String) -> ConstructionResult:
	var result := ConstructionResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	return result


## Parses any v0 session envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed fixtures) and `LegacyV0Api` (which decodes the HTTP body).
static func parse_save_list(payload: Variant) -> SaveListResult:
	if not (payload is Dictionary):
		return save_list_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _save_list_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return save_list_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	var raw_saves: Variant = envelope.get("saves")
	if not (raw_saves is Array):
		return save_list_failure("bad_response", "envelope carries no saves array")
	var saves: Array[SaveInfo] = []
	for entry in raw_saves:
		var parsed := _parse_save(entry)
		if parsed == null:
			return save_list_failure("bad_response", "a save entry is malformed")
		saves.append(parsed)
	var server_time := _parse_epoch(envelope.get("server_time"))
	if server_time < 0:
		return save_list_failure("bad_response", "server_time is not a number")
	var result := SaveListResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = server_time
	result.saves = saves
	return result


## Parses a v0 bootstrap envelope into the typed result, deriving the player
## summary from the save entry that names `user_id`.
static func parse_bootstrap(payload: Variant, user_id: String) -> BootstrapResult:
	var list := parse_save_list(payload)
	if not list.ok:
		return bootstrap_failure(list.error_code, list.error_message)
	var envelope: Dictionary = payload
	var config_raw: Variant = envelope.get("config")
	if not (config_raw is Dictionary):
		return bootstrap_failure("bad_response", "bootstrap carries no config object")
	var player_raw: Variant = envelope.get("player_info")
	if not (player_raw is Dictionary):
		return bootstrap_failure("bad_response", "bootstrap carries no player_info object")
	var summary := summary_for(list.saves, user_id)
	if summary == null:
		return bootstrap_failure("summary_unavailable",
			"the session list has no save for user_id '%s'" % user_id)
	var result := BootstrapResult.new()
	result.ok = true
	result.protocol = list.protocol
	result.game_version = list.game_version
	result.server_time = list.server_time
	result.saves = list.saves
	result.summary = summary
	result.config = ConfigPayload.new()
	result.config.raw = config_raw
	result.player_info = PlayerInfoPayload.new()
	result.player_info.raw = player_raw
	result.player_info.player_name = _player_name(player_raw)
	return result


## Parses a v0 placement envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from
## the committed placement fixture after applying the documented in-memory
## semantics) and `LegacyV0Api` (which decodes the HTTP body), so both
## implementations yield the same typed shape by construction.
static func parse_placement(payload: Variant) -> PlacementResult:
	if not (payload is Dictionary):
		return placement_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _placement_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return placement_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return placement_failure("bad_response",
			"placement response did not report the legacy success result")
	var placement := _parse_placement_entry(envelope.get("placement"))
	if placement == null:
		return placement_failure("bad_response",
			"placement entry is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return placement_failure("bad_response",
			"placement response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return placement_failure("bad_response",
			"placement resources are not seven non-negative integers")
	var result := PlacementResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.result = "success"
	result.placement = placement
	result.resources = resources
	return result


## Parses a v0 purchase envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed purchase fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction.
static func parse_purchase(payload: Variant) -> PurchaseResult:
	if not (payload is Dictionary):
		return purchase_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _purchase_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return purchase_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return purchase_failure("bad_response",
			"purchase response did not report the legacy success result")
	var store: Variant = _parse_store(envelope.get("store"))
	if store == null:
		return purchase_failure("bad_response",
			"purchase store is not a string-item-id to integer-quantity map")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return purchase_failure("bad_response",
			"purchase response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return purchase_failure("bad_response",
			"purchase resources are not seven non-negative integers")
	var result := PurchaseResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return purchase_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.store = store
	result.resources = resources
	return result


## Parses a v0 sell envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from
## the committed sell fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. The
## removed row goes through the SAME fail-closed entry parser the
## placement response uses, so a row can never be read with two rules.
static func parse_sell(payload: Variant) -> SellResult:
	if not (payload is Dictionary):
		return sell_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _sell_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return sell_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return sell_failure("bad_response",
			"sell response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return sell_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return sell_failure("bad_response",
			"sell response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return sell_failure("bad_response",
			"sell resources are not seven non-negative integers")
	var result := SellResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return sell_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.resources = resources
	return result


## Parses a v0 store envelope — success or structured error — into the typed
## result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed store fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. The
## removed row goes through the SAME fail-closed entry parser the placement
## and sell responses use, and the storage mapping through the SAME parser
## the purchase response uses (design D4): one row rule, one storage rule.
static func parse_store(payload: Variant) -> StoreResult:
	if not (payload is Dictionary):
		return store_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _store_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return store_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return store_failure("bad_response",
			"store response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return store_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var store: Variant = _parse_store(envelope.get("store"))
	if store == null:
		return store_failure("bad_response",
			"store mapping is not a string-item-id to integer-quantity map")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return store_failure("bad_response",
			"store response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return store_failure("bad_response",
			"store resources are not seven non-negative integers")
	var result := StoreResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return store_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.store = store
	result.resources = resources
	return result


## Parses a v0 upgrade envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed upgrade fixture's before-state after applying the documented
## in-memory semantics) and `LegacyV0Api` (which decodes the HTTP body), so
## both implementations yield the same typed shape by construction. BOTH rows
## go through the SAME fail-closed entry parser the placement, sell, and
## store responses use (design D5): one row rule, five entry points.
static func parse_upgrade(payload: Variant) -> UpgradeResult:
	if not (payload is Dictionary):
		return upgrade_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _upgrade_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return upgrade_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return upgrade_failure("bad_response",
			"upgrade response did not report the legacy success result")
	var removed := _parse_placement_entry(envelope.get("removed"))
	if removed == null:
		return upgrade_failure("bad_response",
			"removed row is not the legacy eight-field array")
	var upgraded := _parse_placement_entry(envelope.get("upgraded"))
	if upgraded == null:
		return upgrade_failure("bad_response",
			"upgraded row is not the legacy eight-field array")
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return upgrade_failure("bad_response",
			"upgrade response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return upgrade_failure("bad_response",
			"upgrade resources are not seven non-negative integers")
	var result := UpgradeResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return upgrade_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.removed = removed
	result.upgraded = upgraded
	result.resources = resources
	return result


## Parses a v0 construction envelope — success or structured error — into the
## typed result. Shared by `FakeApi` (which synthesizes the envelope from the
## committed construction fixture after applying the documented in-memory
## semantics) and `LegacyV0Api` (which decodes the HTTP body), so both
## implementations yield the same typed shape by construction. BOTH rows go
## through the SAME fail-closed entry parser the placement, sell, store, and
## upgrade responses use (design D3/D5): one row rule, six entry points. The
## resolved action must name the closed vocabulary (design D2), so a response
## echoing an unknown value is a `bad_response` rather than a guess.
static func parse_construction(payload: Variant) -> ConstructionResult:
	if not (payload is Dictionary):
		return construction_failure("bad_response",
			"response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _construction_error(envelope)
	if str(envelope.get("protocol", "")) != PROTOCOL:
		return construction_failure("protocol_mismatch",
			"expected protocol %s, got %s" % [PROTOCOL,
			str(envelope.get("protocol"))])
	if str(envelope.get("result", "")) != "success":
		return construction_failure("bad_response",
			"construction response did not report the legacy success result")
	var previous := _parse_placement_entry(envelope.get("previous"))
	if previous == null:
		return construction_failure("bad_response",
			"previous row is not the legacy eight-field array")
	var row := _parse_placement_entry(envelope.get("row"))
	if row == null:
		return construction_failure("bad_response",
			"post-execution row is not the legacy eight-field array")
	var action := str(envelope.get("action", ""))
	if not CONSTRUCTION_ACTIONS.has(action):
		return construction_failure("bad_response",
			"action '%s' is outside the documented construction set" % action)
	var resources_raw: Variant = envelope.get("resources")
	if not (resources_raw is Dictionary):
		return construction_failure("bad_response",
			"construction response carries no resources object")
	var resources := _parse_resources(resources_raw)
	if resources == null:
		return construction_failure("bad_response",
			"construction resources are not seven non-negative integers")
	var result := ConstructionResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = _parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return construction_failure("bad_response", "server_time is not a number")
	result.result = "success"
	result.previous = previous
	result.row = row
	result.action = action
	result.resources = resources
	return result


## The storage mapping -> `{str(item_id): int}` with integral floats
## canonicalized to ints (the JSON transport widens them on the pinned engine
## while Dictionary equality is type-strict there — the same tolerance
## `_parse_placement_entry` documents). Null when a value is not a
## non-negative integer: quantities are counts, and a negative or fractional
## quantity is not a shape this contract carries.
static func _parse_store(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var store := {}
	for key: Variant in (value as Dictionary):
		var id: Variant = _store_key(key)
		if id == null:
			return null
		var quantity: Variant = _parse_int((value as Dictionary)[key])
		if quantity == null or int(quantity) < 0:
			return null
		store[str(int(id))] = int(quantity)
	return store


## One storage key -> its non-negative integer item id, or null when the
## key is not an item id. Legacy `engine.add_store_item` writes
## `map["store"][str(item_id)]`, so a digit string is the documented shape
## and the JSON transport always yields one; an int key is accepted and
## canonicalized to the same string form so both implementations produce
## identical typed shapes. Nothing else is coerced.
static func _store_key(key: Variant) -> Variant:
	if key is String:
		var text := str(key)
		if text.is_empty() or text.length() > 16:
			return null
		for character in text:
			if character < "0" or character > "9":
				return null
		return text.to_int()
	var parsed: Variant = _parse_int(key)
	if parsed == null or int(parsed) < 0:
		return null
	return parsed


## Summary for one save id, or null when the list does not name it.
static func summary_for(saves: Array[SaveInfo], user_id: String) -> PlayerSummary:
	for save in saves:
		if save.id == user_id:
			var summary := PlayerSummary.new()
			summary.user_id = save.id
			summary.name = save.name
			summary.level = save.level
			summary.xp = save.xp
			return summary
	return null


## Extracts `playerInfo.name` from the legacy player-info payload.
static func _player_name(payload: Dictionary) -> String:
	var info: Variant = payload.get("playerInfo")
	if info is Dictionary:
		var typed: Dictionary = info
		return str(typed.get("name", ""))
	return ""


## Save entry -> SaveInfo, or null when the entry is malformed.
static func _parse_save(entry: Variant) -> SaveInfo:
	if not (entry is Dictionary):
		return null
	var typed: Dictionary = entry
	var id: Variant = typed.get("id")
	var name: Variant = typed.get("name")
	if not (id is String) or not (name is String):
		return null
	var xp := _parse_number(typed.get("xp"))
	var level := _parse_number(typed.get("level"))
	if xp < 0 or level < 0:
		return null
	var save := SaveInfo.new()
	save.id = id
	save.name = name
	save.xp = xp
	save.level = level
	return save


## Non-negative integer from an int or float transport value; -1 otherwise.
static func _parse_number(value: Variant) -> int:
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed < 0.0 or typed != floor(typed):
			return -1
		return int(typed)
	return -1


## Epoch seconds from an int or float transport value; -1 otherwise.
static func _parse_epoch(value: Variant) -> int:
	if value is int:
		return int(value)
	if value is float:
		var typed := float(value)
		if typed < 0.0:
			return -1
		return int(typed)
	return -1


## Structured error fields of a failed envelope (code + message).
static func _save_list_error(envelope: Dictionary) -> SaveListResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return save_list_failure(code, message)


## Structured error fields of a failed placement envelope (code + message).
static func _placement_error(envelope: Dictionary) -> PlacementResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return placement_failure(code, message)


## Structured error fields of a failed purchase envelope (code + message).
static func _purchase_error(envelope: Dictionary) -> PurchaseResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return purchase_failure(code, message)


## Structured error fields of a failed sell envelope (code + message).
static func _sell_error(envelope: Dictionary) -> SellResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return sell_failure(code, message)


## Structured error fields of a failed store envelope (code + message).
static func _store_error(envelope: Dictionary) -> StoreResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return store_failure(code, message)


## Structured error fields of a failed upgrade envelope (code + message) —
## the same one envelope rule the other five commands use, so a code the
## service named (`no_upgrade_path`, `unknown_item_index`,
## `internal_error`, …) reaches the client unchanged.
static func _upgrade_error(envelope: Dictionary) -> UpgradeResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return upgrade_failure(code, message)


## Structured error fields of a failed construction envelope (code + message)
## — the same one envelope rule the other six commands use, so a code the
## service named (`no_build_time`, `unknown_item_index`, `invalid_action`,
## `internal_error`, …) reaches the client unchanged.
static func _construction_error(envelope: Dictionary) -> ConstructionResult:
	var code := "bad_response"
	var message := "response reported failure without a structured error"
	var error: Variant = envelope.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return construction_failure(code, message)


## Eight-field legacy entry -> typed `Placement`; null when malformed
## (wrong shape, non-integer fields, or a negative coordinate/timestamp).
static func _parse_placement_entry(value: Variant) -> Placement:
	if not (value is Array):
		return null
	var raw: Array = value
	if raw.size() != 8:
		return null
	var item_id: Variant = _parse_int(raw[0])
	var x: Variant = _parse_int(raw[1])
	var y: Variant = _parse_int(raw[2])
	var timestamp: Variant = _parse_int(raw[3])
	var orientation: Variant = _parse_int(raw[4])
	var player: Variant = _parse_int(raw[7])
	if item_id == null or x == null or y == null or timestamp == null \
			or orientation == null or player == null:
		return null
	if int(item_id) < 0 or int(x) < 0 or int(y) < 0 or int(timestamp) < 0:
		return null
	if not (raw[5] is Array) or not (raw[6] is Dictionary):
		return null
	var placement := Placement.new()
	placement.item_id = int(item_id)
	placement.x = int(x)
	placement.y = int(y)
	placement.timestamp = int(timestamp)
	placement.orientation = int(orientation)
	placement.store = _canonicalize(raw[5])
	placement.attr = _canonicalize(raw[6])
	placement.player = int(player)
	return placement


## The seven stored resource slots -> typed `Resources`; null when any
## slot is missing or not a non-negative integer (legacy clamps them at
## zero on the server, so a negative value cannot come from the service).
static func _parse_resources(value: Dictionary) -> Resources:
	var amounts := {}
	for key in ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]:
		if not value.has(key):
			return null
		var amount: Variant = _parse_int(value[key])
		if amount == null or int(amount) < 0:
			return null
		amounts[key] = int(amount)
	var resources := Resources.new()
	resources.xp = amounts["xp"]
	resources.gold = amounts["gold"]
	resources.wood = amounts["wood"]
	resources.oil = amounts["oil"]
	resources.steel = amounts["steel"]
	resources.cash = amounts["cash"]
	resources.mana = amounts["mana"]
	return resources


## Integer from an int or an integral float; null otherwise. The JSON
## transport parses every number as float on the pinned engine (probed on
## Godot 4.7.2: `typeof(JSON.parse_string("5"))` is float), so both
## integer forms are accepted — the same tolerance `_parse_number`
## documents for save values. Out-of-range magnitudes, NaN, and infinity
## are rejected.
static func _parse_int(value: Variant) -> Variant:
	if value is int:
		return value
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and absf(typed) <= 9007199254740992.0:
			return int(typed)
	return null


## Canonical legacy form of a nested `store`/`attr` structure: every
## integral float becomes `int`, because the JSON transport widens the
## legacy save's ints to floats on the pinned engine while Dictionary
## equality is type-strict there (probed: `{"nc": 0} == {"nc": 0.0}` is
## false). Without this, the two implementations would report the same
## persisted entry with different value types. Non-integral floats,
## strings, booleans, and null pass through untouched — only the
## representation is normalized, never the value.
static func _canonicalize(value: Variant) -> Variant:
	if value is float:
		var typed := float(value)
		if typed == floor(typed) and absf(typed) <= 9007199254740992.0:
			return int(typed)
		return typed
	if value is Dictionary:
		var out := {}
		for key: Variant in value:
			out[key] = _canonicalize(value[key])
		return out
	if value is Array:
		var out: Array = []
		for element: Variant in value:
			out.append(_canonicalize(element))
		return out
	return value
