extends Node
## `FakeApi` — GameApi implementation over the committed v0 fixtures (design
## D5, spec "Boot offline with the fake implementation").
##
## Reads only the committed executed-legacy fixture files under
## `tests/fixtures/godot-compatibility-boot/`, for placement under
## `tests/fixtures/godot-building-placement/`, and for purchase under
## `tests/fixtures/godot-item-purchase/` at the repository root: no
## process, no server, no socket. It synthesizes the documented v0 envelopes
## from those files and parses them with the same `BootData` functions the
## live implementation uses, so both implementations yield identical typed
## shapes by construction.
##
## `place_building()` additionally applies the documented placement
## semantics in memory (design D8): legacy cost map with the `max(…, 0)`
## clamp, smallest free slot, `engine.map_add_item` entry construction —
## over the committed placement-fixture state, deterministically (the entry
## timestamp is the fixture's recorded epoch; the fake never reads the
## wall clock). `purchase_item()` applies the documented purchase semantics
## in memory (design D9) over the committed purchase-fixture state with the
## same determinism (its `server_time` is the fixture's recorded epoch, not
## the wall clock). Parity against executed legacy is owned exclusively by
## the compat fixture-replay tests; this double exists so the client flow can
## be tested hermetically.

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const Paths = preload("res://scripts/package_paths.gd")

const SAVE_LIST_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/login_page/save-list.json"
const GAME_CONFIG_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_game_config/response.body"
const PLAYER_INFO_FIXTURE := \
	"tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body"
const PLACEMENT_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/before.json"
const PLACEMENT_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-placement/steps/command_buy/after.json"
## The executed-legacy purchase fixture's before-state (which equals the
## fresh-player corpus the boot fixtures carry): the double's starting save.
const PURCHASE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/before.json"
## The same fixture's after-state, recorded by the real legacy server. It is
## read (never written) purely to assert the double reproduces the executed
## transaction; the in-memory apply never writes a file.
const PURCHASE_AFTER_FIXTURE := \
	"tests/fixtures/godot-item-purchase/steps/command_buy_stored_item_cash/after.json"

## Anchor grid extent the v0 endpoint validates against (anchors 0..99;
## footprints may extend past the edge — design D5). Must match
## `Iso.GRID_EXTENT` (M6) and the endpoint's `GRID_EXTENT`.
const GRID_EXTENT := 100

## config `costs` key -> stored resource slot of the legacy 8-slot vector
## `[unknown, xp, gold, wood, oil, steel, cash, mana]` (design D4; mirrors
## `placement_envelope.COST_SLOTS`, which maps the same keys to indices).
const COST_RESOURCES := {
	"g": "gold", "w": "wood", "o": "oil", "s": "steel", "c": "cash",
}
## The stored resource slots `apply_resources` writes (legacy slot 0
## `unknown` has no stored value; `xp`/`mana` are stored but have no
## config cost key).
const RESOURCE_KEYS := ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]

var _save_list_doc: Dictionary = {}
var _config_payload: Dictionary = {}
var _player_info_payload: Dictionary = {}
var _config_items: Dictionary = {}
var _load_error := ""
var _loaded := false

# Mutable in-memory placement state (design D8): one save, replaced only
# by successful placements inside this process. Never written anywhere.
var _placement_state: Dictionary = {}
var _placement_pid := ""
var _placement_epoch := 0
var _placement_loaded := false
var _placement_error := ""

# Mutable in-memory purchase state (design D9): one save, replaced only by
# successful purchases inside this process. Never written anywhere.
var _purchase_state: Dictionary = {}
var _purchase_pid := ""
var _purchase_loaded := false
var _purchase_error := ""


## The session envelope synthesized from the committed fixtures.
func list_sessions() -> BootData.SaveListResult:
	if not _ensure_loaded():
		return BootData.save_list_failure("fixture_unreadable", _load_error)
	return BootData.parse_save_list(_session_envelope())


## Bootstrap envelope synthesized from the committed fixtures; structured
## errors for empty and unknown save ids match the live service's codes.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	if user_id.strip_edges() == "":
		return BootData.bootstrap_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return BootData.bootstrap_failure("fixture_unreadable", _load_error)
	if not _fixture_names(user_id):
		return BootData.bootstrap_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var envelope := _session_envelope()
	envelope["config"] = _config_payload
	envelope["player_info"] = _player_info_payload
	return BootData.parse_bootstrap(envelope, user_id)


## The fake never resolves an endpoint (scope test: only the legacy-v0
## implementation may reference one).
func resolved_endpoint() -> String:
	return "fake fixtures, offline"


## Deterministic in-memory placement double (design D8): the documented
## semantics — legacy cost map with the `max(…, 0)` clamp, smallest free
## slot, `engine.map_add_item` entry construction for player team 1
## (`si` from `properties.friend_assistable`, `nc` from `clicks_to_build`),
## and `engine.bought_unit_add` bookkeeping — applied over the committed
## placement-fixture state, mutating only this process. No process, no
## server, no socket; parity against executed legacy is owned exclusively
## by the compat fixture-replay tests.
##
## Structural failures mirror the v0 endpoint's codes (design D5): unknown
## save / empty id, unknown item id, anchor outside the shared grid.
## Everything else — occupancy, affordability — is gameplay validation the
## client owns, exactly as the endpoint leaves it unenforced; costs clamp
## at zero instead of rejecting, preserving legacy behavior.
func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	if user_id.strip_edges() == "":
		return _place_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _place_failure("fixture_unreadable", _load_error)
	if not _ensure_placement_loaded():
		return _place_failure("fixture_unreadable", _placement_error)
	if user_id != _placement_pid:
		return _place_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return _place_failure("unknown_item_id",
			"no config item with id %d" % item_id)
	if x < 0 or x >= GRID_EXTENT or y < 0 or y >= GRID_EXTENT:
		return _place_failure("invalid_coordinates",
			"x and y must be integers with anchors inside the 0..%d town grid"
			% (GRID_EXTENT - 1))
	var costs: Variant = _derive_costs(item)
	if costs == null:
		# The endpoint answers 500 internal_error for the same unresolvable
		# committed config (design D4); the fake mirrors its code.
		return _place_failure("internal_error",
			"config costs not derivable for item %d" % item_id)
	var attr: Variant = _entry_attr(item)
	if attr == null:
		return _place_failure("internal_error",
			"config properties not derivable for item %d" % item_id)
	# Legacy do_command order for `buy`: resources first (clamped), then
	# boughtUnits bookkeeping, then the entry — all in memory only.
	var resources := _resources_dict()
	for resource: String in costs:
		resources[resource] = maxi(
			int(resources[resource]) - int(costs[resource]), 0)
	var entry := [item_id, x, y, _placement_epoch, orientation, [], attr, 1]
	_placement_state["items"][str(_next_free_slot())] = entry
	for resource: String in RESOURCE_KEYS:
		_placement_state[resource] = int(resources[resource])
	var bought: Array = _placement_state["bought_units"]
	if not bought.has(item_id):
		bought.append(item_id)
	# Same envelope shape the service returns; the shared parser yields
	# the typed result (identical shapes by construction, design D5).
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"result": "success",
		"placement": entry,
		"resources": resources,
	})


## Deterministic in-memory purchase double (design D9): the documented
## semantics of the unchanged legacy `buy_stored_item_cash` branch — the
## item's own config `costs` as a **cash-only** price, the pre-dispatch
## `apply_resources` clamp `max(…, 0)`, `engine.add_store_item` incrementing
## `map["store"][str(item_id)]`, and `engine.bought_unit_add` appending the
## id when absent — applied over the committed purchase fixture's
## before-state, mutating only this process. No process, no server, no
## socket; parity against executed legacy is owned exclusively by the compat
## fixture-replay tests.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result plus the FULL storage mapping and the current resources, so the
## client needs no arithmetic for pre-existing contents (design D4).
##
## Structural failures mirror the endpoint's codes (design D5): unknown
## save / empty id, unknown item id, an item whose config price is not a
## cash price (`costs_not_cash`), and an unresolvable committed config
## (`internal_error`, 500 exactly as the endpoint answers the same input).
## Affordability is gameplay validation the client owns: like the endpoint,
## the double clamps cash at zero instead of rejecting, preserving legacy
## behavior (design D5).
func purchase_item(user_id: String, item_id: int) -> BootData.PurchaseResult:
	if user_id.strip_edges() == "":
		return _purchase_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _purchase_failure("fixture_unreadable", _load_error)
	if not _ensure_purchase_loaded():
		return _purchase_failure("fixture_unreadable", _purchase_error)
	if user_id != _purchase_pid:
		return _purchase_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return _purchase_failure("unknown_item_id",
			"no config item with id %d" % item_id)
	var price: Variant = _cash_price(item as Dictionary)
	if price == null:
		# Unresolvable committed config: the endpoint answers 500
		# internal_error for it (design D2); the fake mirrors that code.
		return _purchase_failure("internal_error",
			"config costs not derivable for item %d" % item_id)
	if int(price) < 0:
		# The price resolves but is not a cash price (design D2's
		# `costs_not_cash`, 400): the client should not have offered it.
		return _purchase_failure("costs_not_cash",
			"item %d is not priced in cash alone" % item_id)
	# Legacy do_command order for `buy_stored_item_cash`: the pre-dispatch
	# resource application (clamped), then `boughtUnits` bookkeeping, then
	# the storage increment — all in memory only.
	_purchase_state["cash"] = maxi(int(_purchase_state["cash"]) - int(price), 0)
	_purchase_state["store"][str(item_id)] = \
		int(_purchase_state["store"].get(str(item_id), 0)) + 1
	var bought: Array = _purchase_state["bought_units"]
	if not bought.has(item_id):
		bought.append(item_id)
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_purchase({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (never the wall clock).
		"server_time": _fixture_server_time(),
		"result": "success",
		"store": (_purchase_state["store"] as Dictionary).duplicate(),
		"resources": _purchase_resources(),
	})


func _ensure_loaded() -> bool:
	if _loaded:
		return _load_error == ""
	_loaded = true
	_save_list_doc = _read_json(SAVE_LIST_FIXTURE)
	if _load_error == "":
		_config_payload = _read_json(GAME_CONFIG_FIXTURE)
	if _load_error == "":
		_player_info_payload = _read_json(PLAYER_INFO_FIXTURE)
	if _load_error == "" and not (_save_list_doc.get("saves") is Array):
		_load_error = "fixture save list carries no saves array: " \
			+ SAVE_LIST_FIXTURE
	if _load_error == "" and not (_config_payload.get("items") is Array):
		_load_error = "fixture config carries no items array: " \
			+ GAME_CONFIG_FIXTURE
	if _load_error == "":
		_index_config_items()
	return _load_error == ""


## One-time item-id -> item index over the committed config (900 entries),
## so placement lookups never re-scan the payload.
func _index_config_items() -> void:
	_config_items = {}
	for item: Variant in _config_payload.get("items", []):
		if item is Dictionary:
			var id := str((item as Dictionary).get("id", ""))
			if id != "":
				_config_items[id] = item


func _session_envelope() -> Dictionary:
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fake reports the fixture capture's legacy
		# server timestamp instead of "now" (the field-stability record lists
		# server_time as time-dependent, so tests never compare its value).
		"server_time": _fixture_server_time(),
		"saves": _save_list_doc.get("saves", []),
	}


## Fixture-derived epoch: `player_info.timestamp` of the captured response.
func _fixture_server_time() -> int:
	var value := BootData._parse_epoch(_player_info_payload.get("timestamp"))
	if value < 0:
		return 0
	return value


func _fixture_names(user_id: String) -> bool:
	for entry in _save_list_doc.get("saves", []):
		if entry is Dictionary and str(entry.get("id", "")) == user_id:
			return true
	return false


# --- placement double (design D8) ------------------------------------------

## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _place_failure(code: String, message: String) -> BootData.PlacementResult:
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed placement fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot
## fixtures' error state is untouched (independent sinks).
func _ensure_placement_loaded() -> bool:
	if _placement_loaded:
		return _placement_error == ""
	_placement_loaded = true
	var before_sink := {"error": ""}
	var after_sink := {"error": ""}
	var before := _read_json_into(PLACEMENT_BEFORE_FIXTURE, before_sink)
	var after := _read_json_into(PLACEMENT_AFTER_FIXTURE, after_sink)
	if str(before_sink["error"]) != "":
		_placement_error = str(before_sink["error"])
		return false
	if str(after_sink["error"]) != "":
		_placement_error = str(after_sink["error"])
		return false
	return _init_placement_state(before, after)


## Validates both fixture documents and builds the in-memory save state.
## Every consumed field is checked, so a malformed fixture fails closed
## instead of crashing the double.
func _init_placement_state(before: Dictionary, after: Dictionary) -> bool:
	var before_map: Variant = _first_map(before, "before")
	if before_map == null:
		return false
	var after_map: Variant = _first_map(after, "after")
	if after_map == null:
		return false
	var items: Variant = (before_map as Dictionary).get("items")
	if not (items is Dictionary):
		_placement_error = "placement fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_placement_error = "placement fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (before_map as Dictionary).get(key)
		if not (value is int or value is float):
			_placement_error = "placement fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_placement_error = "placement fixture before state lacks save fields"
		return false
	# The after-state must add exactly one entry — the capture's placement;
	# its recorded wall-clock timestamp becomes the fake's entry epoch, so
	# the double never reads the wall clock (deterministic by construction).
	var after_items: Variant = (after_map as Dictionary).get("items")
	if not (after_items is Dictionary):
		_placement_error = "placement fixture after state carries no items map"
		return false
	var added: Array = []
	for key: Variant in (after_items as Dictionary):
		if not (items as Dictionary).has(str(key)):
			added.append(str(key))
	if added.size() != 1:
		_placement_error = ("placement fixture after state must add exactly "
			+ "one entry, found %d") % added.size()
		return false
	var entry: Variant = (after_items as Dictionary).get(added[0])
	if not (entry is Array) or (entry as Array).size() != 8:
		_placement_error = "placement fixture after entry is not the eight-field array"
		return false
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) < 0 \
			or float(stamp) != floor(float(stamp)):
		_placement_error = "placement fixture entry timestamp is not a non-negative integer"
		return false
	_placement_state = {
		"items": (items as Dictionary).duplicate(true),
		"xp": int((before_map as Dictionary).get("xp")),
		"gold": int((before_map as Dictionary).get("gold")),
		"wood": int((before_map as Dictionary).get("wood")),
		"oil": int((before_map as Dictionary).get("oil")),
		"steel": int((before_map as Dictionary).get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"bought_units": (bought as Array).duplicate(),
	}
	_placement_pid = pid
	_placement_epoch = int(stamp)
	return true


## `save["maps"][0]` of a fixture document, or null (with the error named).
func _first_map(doc: Dictionary, label: String) -> Variant:
	var maps: Variant = doc.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_placement_error = "placement fixture %s state carries no maps array" % label
		return null
	if not ((maps as Array)[0] is Dictionary):
		_placement_error = "placement fixture %s state first map is not an object" % label
		return null
	return (maps as Array)[0]


# --- purchase double (design D9) --------------------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _purchase_failure(code: String, message: String) -> BootData.PurchaseResult:
	return BootData.parse_purchase({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed purchase fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot and placement fixtures' error state is untouched (independent sinks).
func _ensure_purchase_loaded() -> bool:
	if _purchase_loaded:
		return _purchase_error == ""
	_purchase_loaded = true
	var before := _read_json_into(PURCHASE_BEFORE_FIXTURE, {"error": ""})
	var sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(PURCHASE_AFTER_FIXTURE, sink)
	if str(sink["error"]) != "":
		_purchase_error = str(sink["error"])
		return false
	return _init_purchase_state(before)


## Validates the purchase fixture's before-state and builds the in-memory
## save state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double.
func _init_purchase_state(before: Dictionary) -> bool:
	var before_map: Variant = _purchase_first_map(before)
	if before_map == null:
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_purchase_error = "purchase fixture before state lacks playerInfo/privateState"
		return false
	var store: Variant = (before_map as Dictionary).get("store")
	if not (store is Dictionary):
		_purchase_error = "purchase fixture before state carries no store map"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = (before_map as Dictionary).get(key)
		if not (value is int or value is float) or float(value) != floor(float(value)):
			_purchase_error = "purchase fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_purchase_error = "purchase fixture before state lacks save fields"
		return false
	# Quantities are counts: every entry must be a non-negative integer, and
	# every key an item id — the same shapes the endpoint's storage mapping
	# and the shared parser accept.
	var typed_store := {}
	for key: Variant in (store as Dictionary):
		var id: Variant = BootData._parse_int(key)
		var quantity: Variant = BootData._parse_int((store as Dictionary)[key])
		if id == null or quantity == null or int(id) < 0 or int(quantity) < 0:
			_purchase_error = "purchase fixture before state has an invalid store entry"
			return false
		typed_store[str(int(id))] = int(quantity)
	_purchase_state = {
		"xp": int((before_map as Dictionary).get("xp")),
		"gold": int((before_map as Dictionary).get("gold")),
		"wood": int((before_map as Dictionary).get("wood")),
		"oil": int((before_map as Dictionary).get("oil")),
		"steel": int((before_map as Dictionary).get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"store": typed_store,
		"bought_units": (bought as Array).duplicate(),
	}
	_purchase_pid = pid
	return true


## `save["maps"][0]` of the purchase fixture, or null (with the error named).
func _purchase_first_map(doc: Dictionary) -> Variant:
	var maps: Variant = doc.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_purchase_error = "purchase fixture before state carries no maps array"
		return null
	if not ((maps as Array)[0] is Dictionary):
		_purchase_error = "purchase fixture before state first map is not an object"
		return null
	return (maps as Array)[0]


## The cash price of an item from its config `costs` attribute, or null when
## the committed config cannot be mapped at all (the endpoint's
## `costs_invalid` -> 500 case). A negative return marks the
## `costs_not_cash` case: the price resolves but is absent, empty, another
## resource, or a mix — this command's price is then not derivable and the
## endpoint answers 400 (design D2).
func _cash_price(item: Dictionary) -> Variant:
	var costs: Variant = _derive_costs(item)
	if costs == null:
		return null
	if (costs as Dictionary).size() != 1 \
			or not (costs as Dictionary).has("cash"):
		return -1
	return int((costs as Dictionary)["cash"])


## The seven stored resource values of the in-memory purchase state.
func _purchase_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_purchase_state[key])
	return resources


## Resource amounts from the config `costs` attribute — the legacy cost
## map (design D4; mirrors `placement_envelope.cost_vector`): keys
## `g/w/o/s/c` onto stored resources, one Dictionary; `{}` for a free item;
## `null` when the committed config cannot be mapped (unknown key or
## non-integer amount — the endpoint fails closed with 500 for the same
## input, and the fake mirrors that code). JSON transports numbers as
## floats on the pinned engine, so integral floats are valid amounts.
func _derive_costs(item: Dictionary) -> Variant:
	var raw: Variant = item.get("costs")
	if raw == null:
		return {}
	var source: Variant = raw
	if source is String:
		if str(source) == "":
			return {}
		source = JSON.parse_string(str(source))
		if source == null:
			return null
	if not (source is Dictionary):
		return null
	var costs := {}
	for key: Variant in source:
		var resource: Variant = COST_RESOURCES.get(str(key))
		if resource == null:
			return null
		var amount: Variant = source[key]
		if amount is float and float(amount) != floor(float(amount)):
			return null
		if not (amount is int or amount is float):
			return null
		costs[str(resource)] = int(amount)
	return costs


## Legacy `engine.map_add_item` attr rules for player team 1: `si` when
## `properties.friend_assistable > 0` (friends assist while it builds) and
## `nc` when `clicks_to_build > 0` (neighbor clicks). A non-empty
## `properties` value that is not valid JSON fails closed (`null`) — the
## legacy dispatcher raises on the same input and the endpoint answers
## 500; the committed config carries only valid JSON objects or "".
func _entry_attr(item: Dictionary) -> Variant:
	var attr := {}
	var raw: Variant = item.get("properties")
	if raw is String and str(raw) != "":
		var properties: Variant = JSON.parse_string(str(raw))
		if properties == null:
			return null
		if properties is Dictionary:
			var friend: Variant = (properties as Dictionary).get(
				"friend_assistable", 0)
			if int(friend) > 0:
				attr["si"] = []
	var clicks: Variant = item.get("clicks_to_build", 0)
	if int(clicks) > 0:
		attr["nc"] = 0
	return attr


## Smallest positive integer absent from the items map (design D4; mirrors
## `placement_envelope.next_free_slot`). Keys that are not integer strings
## cannot collide with a numeric slot and are ignored.
func _next_free_slot() -> int:
	var used := {}
	for key: Variant in _placement_state["items"]:
		var text := str(key)
		if text.is_valid_int():
			used[int(text)] = true
	var slot := 1
	while used.has(slot):
		slot += 1
	return slot


## The seven stored resource values of the in-memory state.
func _resources_dict() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_placement_state[key])
	return resources


func _read_json(relative: String) -> Dictionary:
	var sink := {"error": ""}
	var doc := _read_json_into(relative, sink)
	if str(sink["error"]) != "":
		_load_error = str(sink["error"])
	return doc


## Shared fixture reader with an independent error sink: the boot,
## placement, and purchase fixtures fail closed under their own error codes
## without poisoning the other surfaces' state.
func _read_json_into(relative: String, sink: Dictionary) -> Dictionary:
	var path := Paths.repo_root().path_join(relative)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		sink["error"] = "cannot read fixture: " + path
		return {}
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	if parser.parse(text) != OK:
		sink["error"] = "fixture is not valid JSON: %s (line %d)" \
			% [path, parser.get_error_line()]
		return {}
	if not (parser.data is Dictionary):
		sink["error"] = "fixture is not a JSON object: " + path
		return {}
	var typed: Dictionary = parser.data
	return typed
