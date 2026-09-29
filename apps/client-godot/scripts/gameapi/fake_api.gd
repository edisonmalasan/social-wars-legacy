extends Node
## `FakeApi` — GameApi implementation over the committed v0 fixtures (design
## D5, spec "Boot offline with the fake implementation").
##
## Reads only the committed executed-legacy fixture files under
## `tests/fixtures/godot-compatibility-boot/`, for placement under
## `tests/fixtures/godot-building-placement/`, for purchase under
## `tests/fixtures/godot-item-purchase/`, for move under
## `tests/fixtures/godot-building-move/`, for sell under
## `tests/fixtures/godot-building-sell/`, and for store under
## `tests/fixtures/godot-building-store/`, for upgrade under
## `tests/fixtures/godot-building-upgrade/`, and for construction under
## `tests/fixtures/godot-building-construction/` at the repository root: no
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
## the wall clock). `move_building()` applies the documented move semantics
## in memory over the committed move-fixture state with that same
## determinism, `sell_building()` deletes exactly the row its intent
## names from the committed sell-fixture state with it, and
## `store_building()` pops exactly the row its intent names from the
## committed store-fixture state and increments that item's storage entry
## with it, and `upgrade_building()` replaces exactly the row its intent
## names in place — same key, same cell, the target tier derived from the
## fixture's own item reference, the fresh row's timestamp pinned to the
## capture's recorded epoch — and appends that tier to the bought-units list,
## and `build_construction()` applies the matching in-place attribute-bag
## mutation per action over the committed construction-fixture state (a start
## re-stamps the row's start instant and records the derived countdown, a click
## raises the click counter, a completion deletes it), reporting the capture's
## recorded epoch as the re-stamp so the double never reads the wall clock.
## Parity against
## executed legacy is owned exclusively by
## the compat fixture-replay tests; this double exists so the client flow can
## be tested hermetically and is NEVER itself a parity oracle.

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
## The executed-legacy move fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `move_building()`.
const MOVE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-move/steps/command_move/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `move` (Turret I at map slot 11, `(58,48)` -> `(58,47)`).
## Read (never written) so a malformed capture cannot leave the double
## running on an inconsistent oracle.
const MOVE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-move/steps/command_move/after.json"
## The executed-legacy sell fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `sell_building()`.
const SELL_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `sell` (Turret I at map slot 20, anchored at `(41,48)`,
## whose key is absent afterwards while every other row and every resource
## is byte-identical). Read (never written) so a malformed capture cannot
## leave the double running on an inconsistent oracle.
const SELL_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-sell/steps/command_sell/after.json"
## The executed-legacy store fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `store_building()`.
const STORE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/before.json"
## The same fixture's after-state — the real legacy server's record of the
## one executed `store_item` (the Tree decoration at map slot 2, anchored at
## `(53,39)`, whose key is absent afterwards while its id `905` appears in
## the storage mapping with quantity 1). Read (never written) so a malformed
## capture cannot leave the double running on an inconsistent oracle.
const STORE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-store/steps/command_store_item/after.json"
## The executed-legacy upgrade fixture's before-state (which again equals the
## fresh-player corpus the boot fixtures carry): the double's starting save
## for `upgrade_building()`.
const UPGRADE_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed two-command upgrade (the Wall I at map slot 12, anchored at
## (45,49), REPLACED IN PLACE by the Wall II at the same key and cell). Read
## (never written) so a malformed capture cannot leave the double running on
## an inconsistent oracle; its recorded wall-clock timestamp of the new row
## is the deterministic epoch this double stamps.
const UPGRADE_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-upgrade/steps/command_upgrade/after.json"
## The executed-legacy construction fixture's before-state (which again equals
## the fresh-player corpus the boot fixtures carry): the double's starting save
## for `build_construction()`.
const CONSTRUCTION_BEFORE_FIXTURE := \
	"tests/fixtures/godot-building-construction/steps/command_construction/before.json"
## The same fixture's after-state — the real legacy server's record of the one
## executed construction (the Turret I at map slot 11, anchored at `(58,48)`,
## whose row gains the recorded countdown and the raised click counter while
## every other row and every resource is byte-identical). Read (never written)
## so a malformed capture cannot leave the double running on an inconsistent
## oracle, and for its recorded wall-clock start instant — the deterministic
## epoch a start re-stamps with.
const CONSTRUCTION_AFTER_FIXTURE := \
	"tests/fixtures/godot-building-construction/steps/command_construction/after.json"

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

# Mutable in-memory move state (building-move design D8): one save, replaced
# only by successful moves inside this process. Never written anywhere.
var _move_state: Dictionary = {}
var _move_pid := ""
var _move_loaded := false
var _move_error := ""

# Mutable in-memory sell state (building-sell design D8): one save, with rows
# removed only by successful sales inside this process. Never written
# anywhere.
var _sell_state: Dictionary = {}
var _sell_pid := ""
var _sell_loaded := false
var _sell_error := ""

# Mutable in-memory store state (building-store design D8): one save, with
# rows popped only by successful stores and storage entries incremented
# only by them inside this process. Never written anywhere.
var _store_state: Dictionary = {}
var _store_pid := ""
var _store_loaded := false
var _store_error := ""

# Mutable in-memory upgrade state (building-upgrade design D8): one save, with
# exactly one row replaced in place and at most one bought-units append per
# successful upgrade inside this process. Never written anywhere.
var _upgrade_state: Dictionary = {}
var _upgrade_pid := ""
## The capture's recorded wall-clock epoch of the fresh row the executed
## upgrade wrote — the deterministic stamp this double reuses (it never reads
## the wall clock, exactly as the placement double reuses the placement
## capture's epoch).
var _upgrade_epoch := 0
var _upgrade_loaded := false
var _upgrade_error := ""

# Mutable in-memory construction state (building-construction design D8): one
# save, whose addressed row is mutated in place by the matching legacy
# attribute-bag rule and by nothing else. Never written anywhere.
var _construction_state: Dictionary = {}
var _construction_pid := ""
## The capture's recorded wall-clock start instant of the one construction the
## executed transaction performed — the deterministic stamp a start re-stamps
## the addressed row with (the double never reads the wall clock, exactly as
## the placement and upgrade doubles reuse their captures' epochs).
var _construction_epoch := 0
var _construction_loaded := false
var _construction_error := ""


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


## Deterministic in-memory move double (building-move design D8): the
## documented semantics of the unchanged legacy `move` branch — resolve the
## row with the item's map index, write ONLY `item[1] = x` and `item[2] = y`
## in place, apply the pre-dispatch resource vector (the derived vector is
## NEUTRAL, so every stored resource is unchanged), and add, remove, and
## re-key nothing — applied over the committed move fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result, the PERSISTED eight-field row re-read after the write, and the
## current resources — byte-for-byte the shape `place_building()` returns,
## so the client reuses one typed result class and one parse function
## (design D4).
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), and coordinates
## outside the shared grid (`invalid_coordinates`). Everything else —
## occupancy, the no-op cell, ownership — is gameplay validation the client
## owns, exactly as the endpoint leaves it unenforced; this double never
## invents a gate the legacy server does not have, and never accepts a
## client-sent price.
func move_building(user_id: String, item_index: int, x: int,
		y: int) -> BootData.PlacementResult:
	if user_id.strip_edges() == "":
		return _move_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _move_failure("fixture_unreadable", _load_error)
	if not _ensure_move_loaded():
		return _move_failure("fixture_unreadable", _move_error)
	if user_id != _move_pid:
		return _move_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	if x < 0 or x >= GRID_EXTENT or y < 0 or y >= GRID_EXTENT:
		return _move_failure("invalid_coordinates",
			"x and y must be integers with anchors inside the 0..%d town grid"
			% (GRID_EXTENT - 1))
	var row: Variant = (_move_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _move_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# Legacy do_command order for `move`: the pre-dispatch
	# `apply_resources` (clamped) first, then the two in-place coordinate
	# writes. The derived vector is all zeros, so the clamp never rewrites
	# a value and the resources below are the state's own.
	var resources := _move_resources()
	var entry: Array = (row as Array).duplicate()
	entry[1] = x
	entry[2] = y
	(_move_state["items"] as Dictionary)[str(item_index)] = entry
	# Same envelope shape the service returns; the shared parser yields
	# the typed result (identical shapes by construction, design D4).
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"placement": entry,
		"resources": resources,
	})


## Deterministic in-memory sell double (building-sell design D8): the
## documented semantics of the unchanged legacy `sell` branch — resolve the
## row with the item's map index, apply the pre-dispatch resource vector
## (the derived vector is NEUTRAL, so every stored resource is unchanged),
## and delete that row and NOTHING else (no re-keying, no storage write, no
## bookkeeping) — applied over the committed sell fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's authoritative superset: the legacy
## result, the eight-field row AS IT WAS READ BEFORE EXECUTION (design D5 —
## the save no longer holds it, and reconstructing it afterwards would be
## fabrication), and the current resources.
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op early return is never reported as a success), and
## an unreadable fixture (`fixture_unreadable`). Ownership, price, and
## refund are gameplay/economic concerns this contract refuses: the derived
## price vector is neutral, so the double accepts no refund from any caller
## and claims none.
func sell_building(user_id: String, item_index: int) -> BootData.SellResult:
	if user_id.strip_edges() == "":
		return _sell_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _sell_failure("fixture_unreadable", _load_error)
	if not _ensure_sell_loaded():
		return _sell_failure("fixture_unreadable", _sell_error)
	if user_id != _sell_pid:
		return _sell_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_sell_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _sell_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# The pre-execution row: read first, then the one write the branch
	# performs (the delete). Nothing else is touched — no re-keying, no
	# storage, no bookkeeping — exactly as the executed fixture records.
	var removed: Array = (row as Array).duplicate()
	(_sell_state["items"] as Dictionary).erase(str(item_index))
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_sell({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"resources": _sell_resources(),
	})


## Deterministic in-memory store double (building-store design D8): the
## documented semantics of the unchanged legacy `store_item` branch — resolve
## the row with the item's map index, read that row AS IT IS BEFORE the
## writes, apply the pre-dispatch resource vector (the derived vector is
## NEUTRAL, so every stored resource is unchanged), pop exactly that row,
## and increment `map["store"][str(item_id)]` by legacy's default quantity
## of exactly 1 — applied over the committed store fixture's before-state,
## mutating only this process. No process, no server, no socket; parity
## against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
## Exactly two writes land, together: the pop and the storage increment, and
## nothing else is touched (no re-keying, no storage rule of its own, and —
## faithfully — no bought-units bookkeeping, because the legacy branch
## deliberately calls no `bought_unit_add`).
##
## The response mirrors the v0 endpoint's two-sided superset (design D4): the
## legacy result, the eight-field row AS IT WAS READ BEFORE EXECUTION (the
## save no longer holds it, and reconstructing it afterwards would be
## fabrication), the FULL post-execution storage mapping (in the very shape
## and through the very parser the purchase response uses), and the current
## resources — so the client performs no arithmetic for pre-existing
## contents.
##
## Structural failures mirror the endpoint's codes (design D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent early return is never reported as a success), and an
## unreadable fixture (`fixture_unreadable`). Ownership, price, quantity,
## and capacity are gameplay/economic concerns this contract refuses: the
## derived vector is neutral, so the double accepts no cost, no quantity,
## and no capacity from any caller and claims none.
func store_building(user_id: String,
		item_index: int) -> BootData.StoreResult:
	if user_id.strip_edges() == "":
		return _store_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _store_failure("fixture_unreadable", _load_error)
	if not _ensure_store_loaded():
		return _store_failure("fixture_unreadable", _store_error)
	if user_id != _store_pid:
		return _store_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_store_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _store_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	# Legacy do_command order for `store_item`: the pre-dispatch
	# `apply_resources` (clamped) runs first — and the derived vector is all
	# zeros, so the clamp never rewrites a value and the resources below are
	# the state's own — then the row read, the pop, and the storage
	# increment. This double deliberately writes NO bought-units bookkeeping,
	# exactly as the executed fixture records.
	var removed: Array = (row as Array).duplicate()
	(_store_state["items"] as Dictionary).erase(str(item_index))
	(_store_state["store"] as Dictionary)[str(int(removed[0]))] = \
		int((_store_state["store"] as Dictionary).get(
			str(int(removed[0])), 0)) + 1
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_store({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"store": (_store_state["store"] as Dictionary).duplicate(),
		"resources": _store_resources(),
	})


## Deterministic in-memory upgrade double (building-upgrade design D8): the
## documented semantics of the unchanged legacy pair the service derives —
## read the row the intent names AS IT IS BEFORE the writes, apply the
## pre-dispatch resource vector (the derived vector is NEUTRAL, so every
## stored resource is unchanged), and then replace that row IN PLACE at the
## same key with a FRESH row for the target tier at the same cell, the same
## orientation, and the same player field: a new timestamp, `store: []`, and
## the `{"nc": 0}` attribute seed the config's `clicks_to_build > 0` rule
## produces (design D5) — plus the purchase half's bought-units append,
## which records the target tier only when it is not already listed. Applied
## over the committed upgrade fixture's before-state, mutating only this
## process. No process, no server, no socket; parity against executed legacy
## is owned exclusively by the compat fixture-replay tests, so this double is
## a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's two-sided superset (design D5): the
## legacy result, the row AS IT WAS READ BEFORE EXECUTION, the row re-read
## from the save after execution, and the current resources — so the client
## needs no arithmetic of its own and never restamps a row locally.
##
## Structural failures mirror the endpoint's codes (design D3/D5): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), a placement whose
## item has no resolvable next tier (`no_upgrade_path` — the endpoint's 400,
## answered before the dispatcher runs so an un-upgradeable building is never
## reduced to a bare sale), and an unreadable fixture (`fixture_unreadable`).
## Level gating, a daily-upgrade limit, and a space check are legacy-client
## rules the repository cannot reproduce and this change deliberately does not
## implement (design D6) — the same derived vector claims no upgrade cost, and
## the same key and cell are reused, so there is no space question.
func upgrade_building(user_id: String,
		item_index: int) -> BootData.UpgradeResult:
	if user_id.strip_edges() == "":
		return _upgrade_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _upgrade_failure("fixture_unreadable", _load_error)
	if not _ensure_upgrade_loaded():
		return _upgrade_failure("fixture_unreadable", _upgrade_error)
	if user_id != _upgrade_pid:
		return _upgrade_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	var row: Variant = (_upgrade_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before
		# executing (design D3/D5), so a stale or unknown index is a
		# structured failure with no mutation, never a silent success.
		return _upgrade_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	var source: Array = row as Array
	# The target tier comes from the committed configuration's `upgrades_to`
	# reference, never from the caller (design D2) — the same rule the
	# endpoint applies, down to the `-1`/`0` and unresolvable sentinels.
	var target: Variant = _upgrade_target(int(source[0]))
	if target == null:
		# The endpoint answers 400 no_upgrade_path for the same input, before
		# the dispatcher runs, so a building that cannot be upgraded is never
		# reduced to a bare sale (design D3).
		return _upgrade_failure("no_upgrade_path",
			"item %d has no resolvable next tier in the configuration"
			% int(source[0]))
	var target_item: Dictionary = target
	# The fresh row's attribute rules come from the TARGET's own config; an
	# unresolvable committed config fails closed BEFORE any mutation (the
	# endpoint answers 500 internal_error for the same input, and the fake
	# mirrors that code — the placement double's precedent).
	var attr: Variant = _entry_attr(target_item)
	if attr == null:
		return _upgrade_failure("internal_error",
			"config properties not derivable for item %d"
			% int(target_item["id"]))
	# The pre-execution row: read first, then the one write the pair performs
	# (the in-place replacement). Nothing else is touched — no re-keying, no
	# storage, no resource delta — exactly as the executed fixture records.
	var removed: Array = source.duplicate()
	# The purchase half writes a FRESH row at the SAME key and cell: the
	# row's own cell, orientation, and player are reused, the timestamp is
	# the deterministic fixture epoch, and `store` plus the configuration's
	# attribute rules are rebuilt from the target's own config (design D5).
	var entry := [int(target_item["id"]), int(source[1]), int(source[2]),
		_upgrade_epoch, int(source[4]), [], attr, int(source[7])]
	(_upgrade_state["items"] as Dictionary)[str(item_index)] = entry
	# `engine.bought_unit_add` appends the item only when it is not already
	# listed, so re-upgrading into an already-bought tier leaves the list
	# alone (the fixture records `[]` -> `[24]`).
	var bought: Array = _upgrade_state["bought_units"]
	if not bought.has(int(target_item["id"])):
		bought.append(int(target_item["id"]))
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_upgrade({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"removed": removed,
		"upgraded": entry,
		"resources": _upgrade_resources(),
	})


## Deterministic in-memory construction double (building-construction design
## D8): the documented semantics of the three unchanged legacy branches the
## service derives — read the row the intent names AS IT IS BEFORE the writes,
## apply the pre-dispatch resource vector (the derived vector is NEUTRAL, so
## every stored resource is unchanged), and then mutate ONLY that row's
## timestamp and attribute bag, in place, at the same key and cell:
## a `start` re-stamps the start instant and records the derived countdown,
## a `click` raises the click counter (seeding it to `1` when absent), and a
## `finish` deletes the counter and writes nothing else (design D5/D6). The
## start duration comes from the addressed item's committed `build_time` in
## the loaded configuration — never from the caller, exactly the rule the
## endpoint applies — and the re-stamp reuses the capture's recorded epoch, so
## the double never reads the wall clock. No clearing branch is implemented or
## reachable: legacy's `activate` with a non-positive duration would DESTROY
## the whole attribute bag, so the endpoint refuses such a row and this double
## mirrors that refusal (design D6). Applied over the committed construction
## fixture's before-state, mutating only this process. No process, no server,
## no socket; parity against executed legacy is owned exclusively by the compat
## fixture-replay tests, so this double is a test fixture, never an oracle.
##
## The response mirrors the v0 endpoint's two-sided superset (design D3/D5):
## the legacy result, the row AS IT WAS READ BEFORE EXECUTION, the row
## RE-READ from the save after execution, the resolved action echoed from the
## closed vocabulary, and the current resources.
##
## Structural failures mirror the endpoint's codes (design D3): unknown or
## empty save id, an integer index that names no row in the fixture's map
## (`unknown_item_index` — the endpoint's 404, resolved BEFORE execution so
## legacy's silent no-op is never reported as a success), an action outside the
## documented set (`invalid_action`), a `start` on a row whose item has no
## resolvable positive committed build time (`no_build_time` — the endpoint's
## 400, answered before the dispatcher runs so an unbuildable row is never
## handed a coerced or clearing duration), and an unreadable fixture
## (`fixture_unreadable`). Ownership, whether a build may start on a row that
## already carries construction state, the click threshold, and price are
## gameplay/economic concerns this contract refuses: no branch compares the
## counter with `clicks_to_build`, the derived vector is neutral, and this
## double accepts no duration, no price, and no resource delta from any caller.
func build_construction(user_id: String, item_index: int,
		action: String) -> BootData.ConstructionResult:
	if user_id.strip_edges() == "":
		return _construction_failure("missing_user_id",
			"user_id must be a non-empty string")
	if not _ensure_loaded():
		return _construction_failure("fixture_unreadable", _load_error)
	if not _ensure_construction_loaded():
		return _construction_failure("fixture_unreadable", _construction_error)
	if user_id != _construction_pid:
		return _construction_failure("unknown_user_id",
			"no save exists for user_id '%s'" % user_id)
	# The action is validated BEFORE the index is resolved, the endpoint's own
	# order: the request shape is checked first, then the corpus.
	if not BootData.CONSTRUCTION_ACTIONS.has(action):
		return _construction_failure("invalid_action",
			"action must be one of %s" % ", ".join(
				BootData.CONSTRUCTION_ACTIONS))
	var row: Variant = (_construction_state["items"] as Dictionary).get(
		str(item_index))
	if not (row is Array) or (row as Array).size() != 8:
		# The endpoint resolves the index against the corpus before executing
		# (design D3), so a stale or unknown index is a structured failure with
		# no mutation, never a silent success.
		return _construction_failure("unknown_item_index",
			"no placement with index %d in this save's map" % item_index)
	var source: Array = row as Array
	# Copies: the three branches mutate this row's attribute bag IN PLACE
	# (legacy's own code writes `item[6]["cp"]`, `item[6]["nc"]`, and deletes
	# `item[6]["nc"]` on the very dict the save holds), so a shallow row copy
	# would still alias the live bag and the "before" row would report the
	# after-state. The bag is therefore copied separately, exactly as the
	# endpoint does before it hands the row to the dispatcher.
	var previous: Array = source.duplicate()
	previous[6] = (source[6] as Dictionary).duplicate()
	var entry: Array = source.duplicate()
	entry[6] = (source[6] as Dictionary).duplicate()
	var attr: Dictionary = entry[6] as Dictionary
	# Legacy do_command order for each branch: the pre-dispatch
	# `apply_resources` runs first — and the derived vector is all zeros, so
	# the clamp never rewrites a value and the resources below are the state's
	# own — then the row read, then the one in-place write that branch performs.
	var duration: int = 0
	if action == BootData.CONSTRUCTION_ACTIONS[0]:
		# The start duration comes from committed content alone (design D2/D3).
		# An unresolvable, non-integer, or non-positive committed build time
		# fails closed with the endpoint's own 400 rather than being coerced:
		# a zero duration would make legacy CLEAR the whole attribute bag.
		var derived: Variant = _construction_build_time(int(entry[0]))
		if derived == null:
			return _construction_failure("no_build_time",
				"item %d has no resolvable positive committed build time"
				% int(entry[0]))
		duration = int(derived)
		entry[3] = _construction_epoch
		attr["cp"] = duration
	elif action == BootData.CONSTRUCTION_ACTIONS[1]:
		attr["nc"] = int(attr.get("nc", 0)) + 1
	else:
		attr.erase("nc")
	# The pre-execution row was read first (above), then the one write the
	# branch performs. Nothing else is touched — no re-keying, no storage, no
	# bought-units bookkeeping, no resource delta — exactly as the executed
	# fixture records.
	(_construction_state["items"] as Dictionary)[str(item_index)] = entry
	# Same envelope shape the service returns; the shared parser yields the
	# typed result (identical shapes by construction, design D5).
	return BootData.parse_construction({
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(_save_list_doc.get("game_version", "")),
		# Time-dependent field: the fixture capture's legacy server epoch,
		# never the wall clock (deterministic by construction).
		"server_time": _fixture_server_time(),
		"result": "success",
		"previous": previous,
		"row": entry,
		"action": action,
		"resources": _construction_resources(),
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


# --- move double (building-move design D8) ----------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _move_failure(code: String, message: String) -> BootData.PlacementResult:
	return BootData.parse_placement({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed move fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, and purchase fixtures' error state is untouched
## (independent sinks).
func _ensure_move_loaded() -> bool:
	if _move_loaded:
		return _move_error == ""
	_move_loaded = true
	# The pair is read through explicit sinks (the placement pair's
	# precedent), so a malformed capture fails this surface closed without
	# touching the boot, placement, or purchase error state.
	var before_sink := {"error": ""}
	var before := _read_json_into(MOVE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_move_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(MOVE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_move_error = str(after_sink["error"])
		return false
	return _init_move_state(before)


## Validates the move fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it.
func _init_move_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_move_error = "move fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_move_error = "move fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_move_error = "move fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_move_error = "move fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_move_error = "move fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_move_error = "move fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the move's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_move_error = "move fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_move_error = "move fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	_move_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_move_pid = pid
	return true


## The seven stored resource values of the in-memory move state. A move
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta.
func _move_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_move_state[key])
	return resources


# --- sell double (building-sell design D8) ----------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _sell_failure(code: String, message: String) -> BootData.SellResult:
	return BootData.parse_sell({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed sell fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, purchase, and move fixtures' error state is untouched
## (independent sinks).
func _ensure_sell_loaded() -> bool:
	if _sell_loaded:
		return _sell_error == ""
	_sell_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(SELL_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_sell_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(SELL_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_sell_error = str(after_sink["error"])
		return false
	return _init_sell_state(before)


## Validates the sell fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it — and the one
## write a sale performs is the one delete that branch performs.
func _init_sell_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_sell_error = "sell fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_sell_error = "sell fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_sell_error = "sell fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_sell_error = "sell fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_sell_error = "sell fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_sell_error = "sell fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the sell's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_sell_error = "sell fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_sell_error = "sell fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	_sell_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_sell_pid = pid
	return true


## The seven stored resource values of the in-memory sell state. A sell
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta, and no refund is
## claimed.
func _sell_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_sell_state[key])
	return resources


# --- store double (building-store design D8) --------------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _store_failure(code: String, message: String) -> BootData.StoreResult:
	return BootData.parse_store({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## Loads the committed store fixture's before-state into mutable process
## state (once). Structural failures are named with the offending field; the
## boot, placement, purchase, move, and sell fixtures' error state is
## untouched (independent sinks).
func _ensure_store_loaded() -> bool:
	if _store_loaded:
		return _store_error == ""
	_store_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(STORE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_store_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	# The after-state is read (never written) so a malformed capture cannot
	# leave the double running on an inconsistent oracle.
	_read_json_into(STORE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_store_error = str(after_sink["error"])
		return false
	return _init_store_state(before)


## Validates the store fixture's before-state and builds the in-memory save
## state. Every consumed field is checked, so a malformed fixture fails
## closed instead of crashing the double. The placements are kept as the
## save's own `items` map keyed by their legacy index, so an index resolves
## exactly as `engine.map_get_item(map, index)` resolves it — and the two
## writes a store performs are the one pop and the one storage increment
## that branch performs. The storage mapping is read with the same rules the
## endpoint's response carries, so pre-existing entries are never coerced.
func _init_store_state(before: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_store_error = "store fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_store_error = "store fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_store_error = "store fixture before state carries no items map"
		return false
	var store: Variant = map.get("store")
	if not (store is Dictionary):
		_store_error = "store fixture before state carries no store map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_store_error = "store fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_store_error = "store fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_store_error = "store fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the store's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_store_error = "store fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_store_error = "store fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# Quantities are counts and keys are item ids: the same shapes the
	# endpoint's storage mapping and the shared parser accept.
	var typed_store := {}
	for key: Variant in (store as Dictionary):
		var id: Variant = BootData._parse_int(key)
		var quantity: Variant = BootData._parse_int(
			(store as Dictionary)[key])
		if id == null or quantity == null or int(id) < 0 or int(quantity) < 0:
			_store_error = "store fixture before state has an invalid store entry"
			return false
		typed_store[str(int(id))] = int(quantity)
	_store_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"store": typed_store,
	}
	_store_pid = pid
	return true


## The seven stored resource values of the in-memory store state. A store
## derives a neutral vector (design D2), so these are the state's own
## values — reported verbatim, never a computed delta, and no storing cost
## is claimed.
func _store_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_store_state[key])
	return resources


# --- upgrade double (building-upgrade design D8) ----------------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _upgrade_failure(code: String, message: String) -> BootData.UpgradeResult:
	return BootData.parse_upgrade({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The committed configuration's next tier for one item id, or null when the
## item has no upgrade path. The reference is `upgrades_to`, resolved with the
## documented `-1`/`0`-and-unresolvable-means-none rule (design D2), against
## the same one item index the placement and purchase doubles read — so the
## double derives the target tier exactly the way the endpoint does, and never
## from the caller.
func _upgrade_target(item_id: int) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	var reference: Variant = _config_reference(
		(item as Dictionary).get("upgrades_to"))
	if reference == null or int(reference) <= 0:
		return null
	var target: Variant = _config_items.get(str(int(reference)))
	if not (target is Dictionary):
		return null
	return target


## The committed configuration's string-encoded numeric reference -> its
## integer value, or null when the field is absent or is not an integer at
## all. `upgrades_to` is a STRING in the committed payload (`"24"`, `"-1"`)
## exactly as `costs` is, and the endpoint coerces it the same way
## (`compat_legacy.item_upgrade_to`: `int(str(raw).strip())`), so a
## whitespace-trimmed signed digit string is the documented shape. Nothing
## else is ever coerced — a non-numeric reference is simply no path.
static func _config_reference(value: Variant) -> Variant:
	if value == null:
		return null
	if value is int or value is float:
		return BootData._parse_int(value)
	if not (value is String):
		return null
	var text := str(value).strip_edges()
	if text.is_empty() or text.length() > 16:
		return null
	var digits := text
	if digits.begins_with("-") or digits.begins_with("+"):
		digits = digits.substr(1)
	if digits.is_empty():
		return null
	for character in digits:
		if character < "0" or character > "9":
			return null
	return text.to_int()


## Loads the committed upgrade fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot,
## placement, purchase, move, sell, and store fixtures' error state is
## untouched (independent sinks).
func _ensure_upgrade_loaded() -> bool:
	if _upgrade_loaded:
		return _upgrade_error == ""
	_upgrade_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(UPGRADE_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_upgrade_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(UPGRADE_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_upgrade_error = str(after_sink["error"])
		return false
	return _init_upgrade_state(before, after)


## Validates the upgrade fixture's before- and after-states and builds the
## in-memory save state. Every consumed field is checked, so a malformed
## fixture fails closed instead of crashing the double. The placements are
## kept as the save's own `items` map keyed by their legacy index, so an index
## resolves exactly as `engine.map_get_item(map, index)` resolves it — and the
## one write an upgrade performs is the one in-place row replacement that pair
## performs. The after-state is read for its recorded wall-clock epoch: the
## key is REUSED, so the double takes the epoch of the row the capture wrote
## rather than naming a key (which is the placement double's job, not this
## one's).
func _init_upgrade_state(before: Dictionary, after: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_upgrade_error = "upgrade fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_upgrade_error = "upgrade fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_upgrade_error = "upgrade fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_upgrade_error = "upgrade fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_upgrade_error = "upgrade fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	var bought: Variant = (priv as Dictionary).get("boughtUnits")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float) or not (bought is Array):
		_upgrade_error = "upgrade fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the upgrade's own resolution depends
	# on); an unusable key is a malformed capture, never a coerced index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_upgrade_error = "upgrade fixture placement key '%s' is not a " \
				% str(key) + "positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_upgrade_error = "upgrade fixture placement '%s' is not the " \
				% str(key) + "eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# The executed pair REUSES its key, so the after-state carries exactly as
	# many placements as the before-state; anything else means the capture is
	# not the transaction this double reproduces. Exactly one row differs, and
	# its recorded wall-clock timestamp is the deterministic epoch.
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty():
		_upgrade_error = "upgrade fixture after state carries no maps array"
		return false
	if not ((after_maps as Array)[0] is Dictionary):
		_upgrade_error = "upgrade fixture after state first map is not an object"
		return false
	var after_items: Variant = ((after_maps as Array)[0] as Dictionary).get(
		"items")
	if not (after_items is Dictionary):
		_upgrade_error = "upgrade fixture after state carries no items map"
		return false
	if (after_items as Dictionary).size() != typed_items.size():
		_upgrade_error = ("upgrade fixture after state must reuse the same "
			+ "placement keys, found %d against %d") % [
			(after_items as Dictionary).size(), typed_items.size()]
		return false
	var replaced: Array = []
	for key: String in typed_items:
		if not (after_items as Dictionary).has(key):
			_upgrade_error = ("upgrade fixture after state dropped key %s "
				% key + "(an upgrade must reuse its key)")
			return false
		if (after_items as Dictionary)[key] != typed_items[key]:
			replaced.append(key)
	if replaced.size() != 1:
		_upgrade_error = ("upgrade fixture after state must replace exactly "
			+ "one row in place, found %d") % replaced.size()
		return false
	var entry: Variant = (after_items as Dictionary)[replaced[0]]
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) <= 0 \
			or float(stamp) != floor(float(stamp)):
		_upgrade_error = "upgrade fixture fresh row timestamp is not a positive integer"
		return false
	_upgrade_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
		"bought_units": (bought as Array).duplicate(),
	}
	_upgrade_pid = pid
	_upgrade_epoch = int(stamp)
	return true


## The seven stored resource values of the in-memory upgrade state. An upgrade
## derives a neutral vector (design D4), so these are the state's own values —
## reported verbatim, never a computed delta, and no upgrade cost is claimed.
func _upgrade_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_upgrade_state[key])
	return resources


# --- construction double (building-construction design D8) -------------------


## Structured failure in the service's error envelope shape, parsed by the
## same shared parser the live implementation uses.
func _construction_failure(code: String,
		message: String) -> BootData.ConstructionResult:
	return BootData.parse_construction({
		"protocol": BootData.PROTOCOL,
		"ok": false,
		"error": {"code": code, "message": message},
	})


## The addressed item's committed construction duration, or null when the
## loaded configuration cannot supply a POSITIVE one. The reference is the
## item's `build_time`, string-encoded in the committed payload exactly as
## `costs` and `upgrades_to` are, and coerced with the SAME rule the upgrade
## double reads `upgrades_to` with — so the double derives the countdown from
## committed content, never from the caller, exactly the way the endpoint does
## (`compat_legacy.item_build_time`). A non-positive value is refused rather
## than coerced: legacy's `activate` with such a duration would CLEAR the
## addressed row's whole attribute bag, destroying the click counter and any
## friend-assist entries (design D6), which is why this double exposes no
## cancel action and never sends one.
func _construction_build_time(item_id: int) -> Variant:
	var item: Variant = _config_items.get(str(item_id))
	if not (item is Dictionary):
		return null
	var seconds: Variant = _config_reference((item as Dictionary).get("build_time"))
	if seconds == null or int(seconds) <= 0:
		return null
	return seconds


## Loads the committed construction fixture into mutable process state (once).
## Structural failures are named with the offending field; the boot,
## placement, purchase, move, sell, store, and upgrade fixtures' error state is
## untouched (independent sinks).
func _ensure_construction_loaded() -> bool:
	if _construction_loaded:
		return _construction_error == ""
	_construction_loaded = true
	var before_sink := {"error": ""}
	var before := _read_json_into(CONSTRUCTION_BEFORE_FIXTURE, before_sink)
	if str(before_sink["error"]) != "":
		_construction_error = str(before_sink["error"])
		return false
	var after_sink := {"error": ""}
	var after := _read_json_into(CONSTRUCTION_AFTER_FIXTURE, after_sink)
	if str(after_sink["error"]) != "":
		_construction_error = str(after_sink["error"])
		return false
	return _init_construction_state(before, after)


## Validates the construction fixture's before- and after-states and builds
## the in-memory save state. Every consumed field is checked, so a malformed
## fixture fails closed instead of crashing the double. The placements are
## kept as the save's own `items` map keyed by their legacy index, so an index
## resolves exactly as `engine.map_get_item(map, index)` resolves it — and the
## only writes a construction performs are the one row's timestamp and
## attribute bag. The after-state is read for its recorded wall-clock start
## instant: the key is REUSED, so the double takes the epoch of the row the
## capture stamped rather than naming a key (which is the placement double's
## job, not this one's).
func _init_construction_state(before: Dictionary, after: Dictionary) -> bool:
	var maps: Variant = before.get("maps")
	if not (maps is Array) or (maps as Array).is_empty():
		_construction_error = \
			"construction fixture before state carries no maps array"
		return false
	if not ((maps as Array)[0] is Dictionary):
		_construction_error = \
			"construction fixture before state first map is not an object"
		return false
	var map: Dictionary = (maps as Array)[0]
	var items: Variant = map.get("items")
	if not (items is Dictionary):
		_construction_error = \
			"construction fixture before state carries no items map"
		return false
	var info: Variant = before.get("playerInfo")
	var priv: Variant = before.get("privateState")
	if not (info is Dictionary) or not (priv is Dictionary):
		_construction_error = \
			"construction fixture before state lacks playerInfo/privateState"
		return false
	for key in ["xp", "gold", "wood", "oil", "steel"]:
		var value: Variant = map.get(key)
		if not (value is int or value is float) \
				or float(value) != floor(float(value)):
			_construction_error = \
				"construction fixture before state lacks map %s" % key
			return false
	var pid: Variant = (info as Dictionary).get("pid")
	var cash: Variant = (info as Dictionary).get("cash")
	var mana: Variant = (priv as Dictionary).get("mana")
	if not (pid is String) or not (cash is int or cash is float) \
			or not (mana is int or mana is float):
		_construction_error = \
			"construction fixture before state lacks save fields"
		return false
	# Every placement must be the documented eight-field row under a
	# positive integer index (the shape the construction's own resolution
	# depends on); an unusable key is a malformed capture, never a coerced
	# index.
	var typed_items := {}
	for key: Variant in (items as Dictionary):
		var index: Variant = BootData._parse_int(key)
		if key is String and str(key).is_valid_int():
			index = str(key).to_int()
		if index == null or int(index) <= 0:
			_construction_error = "construction fixture placement key '%s' is " \
				% str(key) + "not a positive integer index"
			return false
		var row: Variant = (items as Dictionary)[key]
		if not (row is Array) or (row as Array).size() != 8:
			_construction_error = "construction fixture placement '%s' is not " \
				% str(key) + "the eight-field array"
			return false
		typed_items[str(int(index))] = (row as Array).duplicate()
	# The executed pair REUSES its key, so the after-state carries exactly as
	# many placements as the before-state; anything else means the capture is
	# not the transaction this double reproduces. Exactly one row differs, and
	# its recorded wall-clock start instant is the deterministic epoch.
	var after_maps: Variant = after.get("maps")
	if not (after_maps is Array) or (after_maps as Array).is_empty():
		_construction_error = \
			"construction fixture after state carries no maps array"
		return false
	if not ((after_maps as Array)[0] is Dictionary):
		_construction_error = \
			"construction fixture after state first map is not an object"
		return false
	var after_items: Variant = ((after_maps as Array)[0] as Dictionary).get(
		"items")
	if not (after_items is Dictionary):
		_construction_error = \
			"construction fixture after state carries no items map"
		return false
	if (after_items as Dictionary).size() != typed_items.size():
		_construction_error = ("construction fixture after state must reuse "
			+ "the same placement keys, found %d against %d") % [
			(after_items as Dictionary).size(), typed_items.size()]
		return false
	var constructed: Array = []
	for key: String in typed_items:
		if not (after_items as Dictionary).has(key):
			_construction_error = ("construction fixture after state dropped "
				+ "key %s (a construction must reuse its key)") % key
			return false
		if (after_items as Dictionary)[key] != typed_items[key]:
			constructed.append(key)
	if constructed.size() != 1:
		_construction_error = ("construction fixture after state must mutate "
			+ "exactly one row in place, found %d") % constructed.size()
		return false
	var entry: Variant = (after_items as Dictionary)[constructed[0]]
	var stamp: Variant = (entry as Array)[3]
	if not (stamp is int or stamp is float) or int(stamp) <= 0 \
			or float(stamp) != floor(float(stamp)):
		_construction_error = \
			"construction fixture stamped start time is not a positive integer"
		return false
	_construction_state = {
		"items": typed_items,
		"xp": int(map.get("xp")),
		"gold": int(map.get("gold")),
		"wood": int(map.get("wood")),
		"oil": int(map.get("oil")),
		"steel": int(map.get("steel")),
		"cash": int(cash),
		"mana": int(mana),
	}
	_construction_pid = pid
	_construction_epoch = int(stamp)
	return true


## The seven stored resource values of the in-memory construction state. A
## construction derives a neutral vector (design D4), so these are the state's
## own values — reported verbatim, never a computed delta, and no building cost
## is claimed.
func _construction_resources() -> Dictionary:
	var resources := {}
	for key: String in RESOURCE_KEYS:
		resources[key] = int(_construction_state[key])
	return resources


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
