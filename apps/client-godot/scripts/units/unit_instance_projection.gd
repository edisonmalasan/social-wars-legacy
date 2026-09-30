extends RefCounted
## Registry-backed unit-instance projection (OpenSpec `godot-unit-instances`
## "Unit rows are classified by committed type" / "The garrison container has
## no enforced capacity" / "The production-queue keys are reserved, not
## implemented" / "A dead unit leaves no instance" / "The committed corpus
## yields zero unit instances, and that is asserted", design D3, D5-D8).
##
## ## The projection classifies by committed `type`, never by `kind` (D3)
##
## M8 line 1's `UnitDefinition` exposes `kind: "unit"` because the
## normalization **adds** the field; the stored `config/main.json` items carry
## `type` and no `kind` at all, so `kind` is a **normalization artifact** and is
## never a classification gate. Every row is resolved through `ContentRegistry`
## and classified by the committed `type` it resolves to: `u` becomes a unit
## instance, `b` is reported as a building with no coercion, and anything else is
## **refused** with the committed type named. An item id that resolves in
## neither domain is refused too, so no row is ever silently dropped.
##
## ## A garrison belongs to the container row, which is usually a building
##
## `push_unit` (`engine.py:54-57`) moves a row into another row's fifth slot,
## and the buildings that accept a garrison are factories and decorations, not
## the producers. So a **placed building row's** fifth slot is parsed into unit
## instances exactly as a placed unit row's is, and that is where the
## over-capacity scenario lives. A garrisoned row is always parsed as a
## `UnitInstance`, because the legacy branch moves a **unit** row into a
## container.
##
## ## The registry is the single content gate (D1, D3)
##
## Every definition is resolved through the already-verified `units` and
## `buildings` domains, whose manifest byte-count and SHA-256 verification stays
## the one gate. An unavailable registry, one that has not loaded, or one
## missing either domain is a **fail-closed** condition, never an empty
## projection presented as a loaded one.
##
## ## No capacity rule, ever (D5)
##
## `unit_capacity` is committed content with **zero** legacy consumers: the
## string occurs in none of `engine.py`, `command.py`, `sessions.py`,
## `server.py`, or `constants.py`, and `push_unit` appends to the container
## unconditionally. So **no** member is ever refused, dropped, or truncated, and
## `committed_capacity()` reports the committed number for reference with an
## explicit statement that no rule is implemented. This is the delivered
## `building-xp` precedent applied to a second unread content field; an
## authoritative garrison limit belongs to a later server-authoritative
## milestone.
##
## ## The queue keys are RESERVED, not implemented (D6)
##
## `RESERVED_ATTR_KEYS` names `nu`, `ts`, and `ui` with their established
## meanings and the three-key teardown rule, so the `queues` and `production`
## lines inherit a **named** contract instead of rediscovering it. Reading
## whether a row carries these keys is projection; **writing** them is
## behaviour and is out of scope. This module therefore has no increment, no
## decrement, no timestamp write, and no queue projection at all.
##
## ## A dead unit leaves no instance (D7)
##
## `push_dead_unit` (`engine.py:149-170`) increments an **integer** in
## `privateState["deadHeroes"][item_id]` and **discards the row**. So the
## counter is read and reported as a plain integer map and **no** row, corpse,
## or recoverable instance is derived from it. No `resurrectable` predicate is
## evaluated: that is a *death* rule belonging to a combat line, and the
## committed coverage of the property is content, not an applied rule.
##
## ## No endpoint, no fixture, no acquisition (D4, D8)
##
## An instance is read from a save already in hand, so nothing is fetched and
## no intent is sent. The committed corpus has **no** unit row, so this module
## returns zero instances against it, asserted rather than tolerated, and the
## instances it does produce come from a crafted in-memory row set, never from
## a fabricated save.

## The typed models this projection reads and produces.
const UnitInstance = preload("res://scripts/units/unit_instance.gd")
const UnitDefinition = preload("res://scripts/units/unit_definition.gd")

## The registry whose verified `units` and `buildings` domains this projection
## reads. Used as the parameter type, exactly as `unit_catalog.gd` types the
## same dependency.
const RegistryScript = preload("res://scripts/content_registry.gd")

## The two content domains a row is resolved through, named by the normalized
## output's file basename because that is how `ContentRegistry` names a domain.
## Both are required: `units` to type an instance, `buildings` to recognise and
## report a non-unit row with no coercion.
const UNIT_DOMAIN := "units"
const BUILDING_DOMAIN := "buildings"

## The two committed item types, and nothing else. A row carrying any other
## committed type is refused rather than coerced into either category.
const TYPE_UNIT := "u"
const TYPE_BUILDING := "b"
const CLASSIFIED_TYPES := [TYPE_UNIT, TYPE_BUILDING]

## The reserved production-queue attribute keys (D6). A **typed inventory**,
## not a rule: each entry records the established meaning, the established
## type, where the legacy branch that writes it lives, and whether it is
## optional. Nothing here increments, decrements, or writes any of them.
const RESERVED_ATTR_KEYS := [
	{"key": "nu", "type": "integer", "optional": false,
		"meaning": "the queued-unit COUNT, not a list and not a position",
		"established_from": "engine.py:183-189 (push_queue_unit increments or "
			+ "sets it to 1) and engine.py:191-198 (pop_queue_unit decrements it)",
		"read_only_here": "this projection reports whether a row carries the "
			+ "key and what committed value it holds, and writes nothing"},
	{"key": "ts", "type": "integer", "optional": false,
		"meaning": "the queue's START INSTANT, a Unix-seconds integer",
		"established_from": "engine.py:189 and engine.py:212 stamp it with "
			+ "timestamp_now(); engine.py:198 refreshes it on a decrement",
		"read_only_here": "this projection reports whether a row carries the "
			+ "key and what committed value it holds, and writes nothing; no "
			+ "elapsed-time or completion rule is computed from it"},
	{"key": "ui", "type": "integer", "optional": true,
		"meaning": "the OPTIONAL queued unit id, set only by the atom-fusion "
			+ "path and by no other committed branch",
		"established_from": "engine.py:206-213 (push_queue_unit2) is the only "
			+ "branch that sets it",
		"read_only_here": "this projection reports whether a row carries the "
			+ "key and what committed value it holds, and writes nothing; no "
			+ "queued-unit identity is resolved from it"},
]

## The established teardown rule, recorded because no inspection of the
## dispatcher would reveal it: the three keys die **together**.
const RESERVED_ATTR_TEARDOWN := ("when the count reaches zero, pop_queue_unit "
	+ "deletes nu, ts, and ui TOGETHER (engine.py:198-204): the three keys are "
	+ "never torn down independently, no committed branch deletes one of them "
	+ "on its own, and a save therefore never carries a partial queue teardown")

## The scope statement D6 requires alongside the reservation.
const RESERVED_ATTR_SCOPE := ("this inventory is CONTENT-LEVEL ONLY. It names "
	+ "the keys so the queues and production lines inherit a written contract, "
	+ "and this change adds no queue increment, no decrement, no timestamp "
	+ "write, and no queue projection, and implements no training, production, "
	+ "or queueing behaviour. Training, production, and queueing remain "
	+ "separate later M8 deliver lines.")

## The dead-unit counter's committed location and shape (D7).
const DEAD_COUNTER_PATH := "privateState.deadHeroes"
const DEAD_COUNTER_RULE := ("the legacy dead-unit pool is an INTEGER COUNT "
	+ "KEYED BY ITEM ID, not a pool of rows: push_dead_unit (engine.py:149-170) "
	+ "requires item[7] == 1, a properties bag, and properties.resurrectable > "
	+ "0, then increments the count and DISCARDS the row, and resurrect_hero "
	+ "(engine.py:172-181) decrements it and deletes the key at zero. A dead "
	+ "unit therefore leaves NO instance behind and this projection derives no "
	+ "row, no corpse, and no recoverable instance from the count.")
const DEAD_COUNTER_ABSENT := ("a null or absent deadHeroes is REFUSED, not read "
	+ "as an empty count: version.py:26-30 writes null for a pre-version save, "
	+ "and a missing count is not a count of zero")

## The capacity field's committed name and the explicit no-rule statement (D5).
const CAPACITY_FIELD := "unit_capacity"
const CAPACITY_RULE := ("NO CAPACITY RULE IS IMPLEMENTED. The committed "
	+ "unit_capacity field has zero legacy consumers: the string occurs in none "
	+ "of engine.py, command.py, sessions.py, server.py, or constants.py, and "
	+ "push_unit (engine.py:55) appends to the container unconditionally, so no "
	+ "member is refused, dropped, or truncated and no garrison size is "
	+ "compared against the committed number. The committed value is reported "
	+ "for reference only, and an authoritative garrison limit belongs to a "
	+ "later server-authoritative milestone.")

## A recorded correction to the committed investigation record, kept next to
## the capacity contract it contradicts. The record
## (`docs/legacy-unit-instances.md` section 4, and the design's Context) states
## that 0 of 429 units carry `unit_capacity`. That is wrong: the stored
## `config/main.json` carries it on five unit rows (1013 Truck 4, 1018 Zodiac
## 4, 1019 Ship 6, 1032 Truck 3 6, 1035 Truck II 6) and the normalized package
## preserves them verbatim. The refusal is unaffected, because the field still
## has no consumer, so no rule is implemented either way; but the distribution
## the evidence reports is the committed one, and the record is corrected here
## rather than quietly restated.
const CAPACITY_CORRECTION := ("the committed investigation record states that 0 "
	+ "of 429 units carry unit_capacity; the committed content disagrees: 5 of "
	+ "429 do (1013, 1018, 1019, 1032, 1035). The no-rule decision is "
	+ "unaffected, because the field has no legacy consumer in either case, but "
	+ "the distribution this module reports is measured from the committed "
	+ "package rather than restated from the record.")

## A second recorded correction to the same investigation record, next to the
## capacity contract. The record's measured facts say "3 placed rows are
## garrison-capable (905, 930, 931)". That is the DISTINCT-ITEM-ID count: the
## committed corpus has **9** such rows (905 once, 930 six times, 931 twice).
## Nothing about the decision changes - all nine are `collect: 20`
## decorations and all nine containers are empty - but the evidence reports the
## measured row count and names the record's imprecision rather than repeating
## it.
const GARRISON_CAPABLE_CORRECTION := ("the committed investigation record says "
	+ "'3 placed rows are garrison-capable (905, 930, 931)'; 3 is the "
	+ "DISTINCT-ITEM-ID count, and the committed corpus has 9 such rows (905 "
	+ "once, 930 six times, 931 twice). No decision changes: all nine are "
	+ "collect:20 decorations and all nine containers are empty.")

## Why the normalized `kind` is not the classification gate (D3).
const KIND_ARTIFACT := ("the normalized package gives every definition a kind "
	+ "('unit' on 429 rows, 'building' on 470), but the STORED configuration "
	+ "carries type and no kind at all: kind is an artifact the normalization "
	+ "adds. Classification therefore reads the committed type, so a row is "
	+ "classified by a field the legacy save actually carries, and kind stays "
	+ "available on the definition as content without ever gating anything.")

## What this projection deliberately does **not** read, and why.
const UNREAD_PRIVATE_STATE := [
	{"field": "privateState.boughtUnits", "owned_by": "the delivered "
		+ "building-purchase and building-store lines",
		"why": "a bought-unit ledger is the `buy` command's record, not a "
			+ "placement: reading it here would restate another line's "
			+ "post-execution proof"},
	{"field": "maps[n].store", "owned_by": "the delivered building-store line",
		"why": "player storage is a separate per-map dictionary "
			+ "(engine.py:70-75), NOT the row's fifth slot, and this "
			+ "projection is about instances"},
	{"field": "maps[n].resources", "owned_by": "the delivered building-collect "
		+ "and building-expand lines",
		"why": "no resource or income rule exists in this capability"},
]

## The evidence's provenance split (design D3, D5-D8): what is ESTABLISHED by
## the committed artifacts and what is DERIVED here. The runtime tokens are
## assembled from fragments because the project-scope suite scans every source
## file for their literal forms.
const PROVENANCE := {
	"established": [
		{"fact": "the eight-slot row shape [item, x, y, timestamp, "
			+ "orientation, store, attr, player], and therefore that a unit "
			+ "instance IS a row",
			"evidence": "engine.py:31, map_add_item's row literal, with the "
				+ "empty-container default at engine.py:11-12"},
		{"fact": "a garrisoned unit is a row nested inside a row: push_unit "
			+ "appends a row to the container and stamps the container's own "
			+ "instant, and pop_unit scans the container for a matching item[0]",
			"evidence": "engine.py:54-57 (push_unit) and engine.py:58-68 "
				+ "(pop_unit); command.py:365-397 are the only two dispatcher "
				+ "branches that reach them"},
		{"fact": "the production queue is a counter, a start instant, and an "
			+ "optional queued unit id, torn down as three keys at once",
			"evidence": "engine.py:183-213; only push_queue_unit2 "
				+ "(engine.py:206-213) ever sets ui"},
		{"fact": "a dead unit leaves no instance: the surviving artefact is an "
			+ "integer count keyed by item id and the row is discarded",
			"evidence": "engine.py:149-170 (push_dead_unit) and "
				+ "engine.py:172-181 (resurrect_hero)"},
		{"fact": "unit_capacity has no legacy consumer at all",
			"evidence": "the string occurs zero times in engine.py, command.py, "
				+ "sessions.py, server.py, and constants.py, and push_unit "
				+ "appends unconditionally"},
		{"fact": "the committed corpus holds 40 placed rows across 11 distinct "
			+ "item ids, all of committed type b, with 0 unit rows, 0 non-empty "
			+ "containers, and every attribute bag empty, and deadHeroes and "
			+ "boughtUnits both empty",
			"evidence": "tests/saves/fresh-player.json maps[0].items, measured "
				+ "by this line's own suite against the committed bytes"},
		{"fact": "the committed type is the only stored discriminator between a "
			+ "placed unit and a placed building",
			"evidence": "the stored config/main.json items carry type and no "
				+ "kind; the normalized kind is an artifact the normalization "
				+ "adds"},
	],
	"derived": [
		{"fact": "a UnitInstance wraps its row and its resolved definition "
			+ "rather than duplicating the definition's fields",
			"evidence": "derived: design D1 chooses the composition. The "
				+ "established fact it rests on is that an instance IS a row, so "
				+ "the honest model is a view over the row plus the content it "
				+ "resolves to; the wrapping is what makes the M8 line 1 "
				+ "static/instance boundary structural"},
		{"fact": "nesting is bounded by a named MAX_GARRISON_DEPTH and a row "
			+ "set beyond it is refused rather than truncated",
			"evidence": "derived: the bound is this line's own guard against "
				+ "unbounded recursion over untrusted save input. The legacy "
				+ "engine nests exactly one level (push_unit is called with a "
				+ "map row), so the committed corpus needs 1 and the chosen "
				+ "bound of 4 is headroom, not an observation"},
		{"fact": "a placed BUILDING row's container is parsed into unit "
			+ "instances, not only a placed unit row's",
			"evidence": "derived: the established fact is that a garrisoned row "
				+ "is a row in some row's fifth slot, and the committed content "
				+ "puts unit_capacity on 48 of 470 buildings while 0 of those "
				+ "48 train anything, so the container row in practice is a "
				+ "building. The spec's scenario is stated over a placed "
				+ "row's fifth slot, which is what is implemented"},
		{"fact": "the line is read-only with no endpoint, no fixture, and no "
			+ "acquisition",
			"evidence": "derived by the reachability table in "
				+ "docs/legacy-unit-instances.md section 7: the corpus has no "
				+ "unit row, so no executed-legacy fixture can be captured "
				+ "without fabricating a player state, and an instance is read "
				+ "from a save in hand rather than fetched"},
	],
}

## The evidence's explicit non-claims (spec "Unit-instance evidence and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"no unit is rendered, animated, or played by this change: nothing is "
		+ "drawn, no sprite is resolved for an instance, and no scene reads "
		+ "this projection",
	"no windowed capture is claimed: this change alters nothing visual and "
		+ "the committed corpus has no unit to render, so a capture would "
		+ "assert nothing",
	"no executed-legacy fixture was captured, because the committed corpus "
		+ "contains no unit row, and none was fabricated: no save, corpus, or "
		+ "fixture was written to hold a unit row, and the instances this "
		+ "projection does produce come from a crafted in-memory row set "
		+ "labelled as test input",
	"the first executed-legacy unit fixture belongs to the production line, "
		+ "because the Command Center at map key 1 is a real placed training "
		+ "producer (training_time 5, min_level 1) and makes the queue "
		+ "genuinely exercisable against the corpus",
	"no acquisition is claimed: no committed unit is store-listed (in_store is "
		+ "0 for all 429), the committed unit sources are the offer-pack and "
		+ "darts systems which are later milestones, and no means of obtaining "
		+ "or placing a unit is implemented or claimed",
	"no queueing, training, production, garrison-capacity, death, "
		+ "resurrection, movement, collection, animation, or basic behaviour is "
		+ "implemented: each is a separate later M8 deliver line, and the "
		+ "reserved queue keys are a content-level record only",
	"no gameplay semantics are attached to any unit statistic: attack, "
		+ "defense, life, attack_interval, attack_range, velocity, expiration, "
		+ "best_against, and best_against_mult are committed numbers and no "
		+ "helper computes damage, a defence outcome, a speed, a lifetime, or "
		+ "an attack timing from them",
	"no capacity rule is enforced: the committed unit_capacity has no legacy "
		+ "consumer, so no member is ever refused, dropped, or truncated, and "
		+ "an authoritative garrison limit belongs to a later "
		+ "server-authoritative milestone",
	"the committed corpus yields ZERO unit instances and every placed row "
		+ "classifies as a building: that zero is asserted by the suite and is "
		+ "a fact about the corpus, not evidence that a unit can be obtained, "
		+ "placed, or observed",
	"no compatibility route, response field, error code, or persistence "
		+ "behaviour was added, and no client intent is sent to obtain an "
		+ "instance: an instance is read from a save already in hand",
	"the classification reads the committed type field and never the "
		+ "normalized kind, which is an artifact the normalization adds and "
		+ "which the stored configuration does not carry",
	"no pixel-parity oracle against the legacy client exists",
]


## Everything one projection found in one map's row set.
class MapProjection extends RefCounted:
	## The index of the map inside the save's `maps` array.
	var map_index := 0
	## Every committed key the projection classified, in the save's own row
	## order. Every key is classified or the projection fails closed, so this
	## count equals the row count.
	var keys: Array = []
	## How many committed rows the projection classified.
	var row_count := 0
	## Placed rows whose committed `type` is `u`.
	var unit_row_count := 0
	## Placed rows whose committed `type` is `b`, reported with no coercion.
	var building_row_count := 0
	## The placed unit instances, in committed key order.
	var placed_units: Array = []
	## Every unit instance found, nested garrison members included. A nested
	## member is an instance in its own right (design D2), so this is the
	## honest total against the committed corpus's zero.
	var instances: Array = []
	## One record per placed building row: its key, item id, committed name,
	## committed type, committed capacity, container state, and parsed
	## container members.
	var buildings: Array = []
	## How many unit rows were parsed out of building containers.
	var building_garrison_members := 0
	## The deepest instance nesting the projection produced, bounded by
	## `UnitInstance.MAX_GARRISON_DEPTH`.
	var max_depth := 0
	## The committed dead-unit counter, read as a plain integer map keyed by
	## item id. No row, corpse, or recoverable instance is derived from it.
	var dead_heroes := {}
	## Reserved production-queue key -> how many classified rows carry it.
	## Reading this is projection; nothing here writes a key.
	var reserved_presence := {}
	## One record per row carrying any reserved key: its key, item id, the
	## keys it carries, and their committed values.
	var reserved_rows: Array = []
	## The manifest `content_fingerprint` of the package these rows were
	## classified against.
	var content_fingerprint := ""


## Projects every unit instance out of one map of a parsed save. Returns
##   `{ok: true, error: "", projection: <MapProjection>}`
## or
##   `{ok: false, error: "<message naming the offender>", projection: null}`
## with no partial projection and no silently dropped row (D3, D8).
##
## `save` is a parsed save document; only `maps[map_index].items` and
## `privateState.deadHeroes` are read, and what is deliberately NOT read is
## listed in `UNREAD_PRIVATE_STATE`.
static func project(registry: RegistryScript, save: Variant,
		map_index: int = 0) -> Dictionary:
	var gate := _registry_gate(registry)
	if not bool(gate.get("ok", false)):
		return _reject(str(gate.get("error", "")))
	if not (save is Dictionary):
		return _reject("the save is not an object (found %s)"
			% _type_name(save))
	var maps: Variant = (save as Dictionary).get("maps", null)
	if not (maps is Array):
		return _reject("the save carries no 'maps' array (found %s)"
			% _type_name(maps))
	if int(map_index) < 0 or int(map_index) >= (maps as Array).size():
		return _reject("map index %d is outside the save's %d maps"
			% [int(map_index), (maps as Array).size()])
	var map_document: Variant = (maps as Array)[int(map_index)]
	if not (map_document is Dictionary):
		return _reject("map %d is not an object (found %s)"
			% [int(map_index), _type_name(map_document)])
	var projected := project_rows(registry,
		(map_document as Dictionary).get("items", null),
		(save as Dictionary).get("privateState", null))
	if not bool(projected.get("ok", false)):
		return _forward(str(projected.get("error", "")))
	(projected["projection"]).map_index = int(map_index)
	return projected


## Projects every unit instance out of one map's committed row set. Returns the
## same envelope as `project`.
##
## This is the primitive `project` delegates to, and the form the suite feeds a
## **crafted in-memory row set** to: it takes the row dictionary and the private
## state directly, so instances can be demonstrated without writing a unit row
## into any save, corpus, or fixture (D8).
static func project_rows(registry: RegistryScript, rows: Variant,
		private_state: Variant) -> Dictionary:
	var gate := _registry_gate(registry)
	if not bool(gate.get("ok", false)):
		return _reject(str(gate.get("error", "")))
	if not (rows is Dictionary):
		return _reject("the map's 'items' is not a row dictionary (found %s)"
			% _type_name(rows))
	var dead := _dead_counter(private_state)
	if not bool(dead.get("ok", false)):
		return _reject(str(dead.get("error", "")))
	var projection := MapProjection.new()
	projection.content_fingerprint = registry.content_fingerprint()
	projection.dead_heroes = (dead["counts"] as Dictionary).duplicate()
	var resolve_nested := _nested_resolver(registry)
	for key: Variant in (rows as Dictionary).keys():
		var row_key := str(key)
		var classified := _classify(registry, row_key,
			(rows as Dictionary)[key], resolve_nested)
		if not bool(classified.get("ok", false)):
			return _forward(str(classified.get("error", "")))
		projection.keys.append(row_key)
		projection.row_count += 1
		var tree: Array = []
		if bool(classified.get("is_unit", false)):
			projection.unit_row_count += 1
			projection.placed_units.append(classified["instance"])
			tree.append(classified["instance"])
		else:
			var record: Dictionary = classified["record"]
			projection.building_row_count += 1
			projection.building_garrison_members += \
				(record["garrison"] as Array).size()
			projection.buildings.append(record)
			tree = (record["garrison"] as Array).duplicate()
		_record_reserved(projection, row_key, str(classified.get("item_id", "")),
			(rows as Dictionary)[key])
		var seen := {"max_depth": 0}
		_collect(tree, projection.instances, seen)
		projection.max_depth = maxi(projection.max_depth, int(seen["max_depth"]))
	return {"ok": true, "error": "", "projection": projection}


## The committed garrison capacity of one definition, reported as content with
## the explicit no-rule statement. Returns
##   `{ok: true, error: "", legacy_id, item_name, unit_capacity, domain,
##     enforced: false, rule: <no-rule statement>}`
## or
##   `{ok: false, error: "<message>", ... zero values}`
##
## **This reports and never applies.** Nothing in this capability compares a
## garrison's size with the number returned here (D5).
static func committed_capacity(registry: RegistryScript,
		legacy_id: Variant) -> Dictionary:
	var empty := {"ok": false, "error": "", "legacy_id": "",
		"item_name": "", "unit_capacity": -1, "domain": "",
		"enforced": false, "rule": CAPACITY_RULE}
	var gate := _registry_gate(registry)
	if not bool(gate.get("ok", false)):
		empty["error"] = str(gate.get("error", ""))
		return empty
	if not (legacy_id is String) or str(legacy_id).is_empty():
		empty["error"] = "legacy id %s is not a non-empty string" \
			% JSON.stringify(legacy_id)
		return empty
	var id_text := str(legacy_id)
	for domain: String in [BUILDING_DOMAIN, UNIT_DOMAIN]:
		var resolved: Dictionary = registry.get_entry(domain, id_text)
		if not bool(resolved.get("found", false)):
			continue
		var entry: Dictionary = resolved["entry"]
		var capacity: Variant = _integer(entry.get(CAPACITY_FIELD, null))
		if capacity == null:
			empty["error"] = "unit %s in domain '%s' carries a non-integer %s" \
				% [id_text, domain, CAPACITY_FIELD]
			return empty
		return {"ok": true, "error": "", "legacy_id": id_text,
			"item_name": str(entry.get("name", "")),
			"unit_capacity": int(capacity), "domain": domain,
			"enforced": false, "rule": CAPACITY_RULE}
	empty["error"] = "no %s or %s entry for legacy id %s" \
		% [BUILDING_DOMAIN, UNIT_DOMAIN, id_text]
	return empty


## The reserved production-queue key inventory, as a fresh deep copy a caller
## may mutate. Reading the inventory is permitted projection; nothing here
## writes a key (D6).
static func reserved_keys() -> Array:
	return (RESERVED_ATTR_KEYS as Array).duplicate(true)


## The reserved key names, in inventory order.
static func reserved_key_names() -> Array:
	var out: Array = []
	for record: Dictionary in RESERVED_ATTR_KEYS:
		out.append(str(record["key"]))
	return out


## One reserved-key record by name, or null when the name is not reserved.
static func reserved_key(name: Variant) -> Variant:
	for record: Dictionary in RESERVED_ATTR_KEYS:
		if str(record["key"]) == str(name):
			return (record as Dictionary).duplicate(true)
	return null


## How many unit instances a projection found, nested members included; -1 for
## an unusable projection (an explicit sentinel, never a guessed zero).
static func instance_count(projection: Variant) -> int:
	if not (projection is MapProjection):
		return -1
	return (projection as MapProjection).instances.size()


## How many **placed** unit rows a projection classified as units; -1 for an
## unusable projection.
static func placed_unit_count(projection: Variant) -> int:
	if not (projection is MapProjection):
		return -1
	return (projection as MapProjection).unit_row_count


## How many placed rows a projection reported as buildings, with no coercion;
## -1 for an unusable projection.
static func building_count(projection: Variant) -> int:
	if not (projection is MapProjection):
		return -1
	return (projection as MapProjection).building_row_count


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


## The content gate every read passes: an available, loaded registry carrying
## BOTH domains. A projection can neither type a unit nor recognise a non-unit
## row without them, so a missing domain is a refusal and never an empty
## projection presented as a loaded one.
static func _registry_gate(registry: RegistryScript) -> Dictionary:
	if registry == null:
		return _gate_error("the content registry is unavailable")
	if not registry.is_loaded():
		return _gate_error("the content registry has not loaded")
	for domain: String in [UNIT_DOMAIN, BUILDING_DOMAIN]:
		if not registry.has_domain(domain):
			return _gate_error("the content registry carries no '%s' domain"
				% domain)
	return {"ok": true, "error": ""}


## The committed dead-unit counter, read as a plain integer map keyed by item
## id. Every value must be an integer, and a null or absent counter is refused
## rather than read as an empty count (D7).
static func _dead_counter(private_state: Variant) -> Dictionary:
	if not (private_state is Dictionary):
		return _reject("the save carries no 'privateState' object (found %s)"
			% _type_name(private_state))
	var raw: Variant = (private_state as Dictionary).get("deadHeroes", null)
	if not (raw is Dictionary):
		return _reject("'%s' is not an integer map keyed by item id (found %s)"
			% [DEAD_COUNTER_PATH, _type_name(raw)])
	var counts := {}
	for item: Variant in (raw as Dictionary).keys():
		var amount: Variant = _integer((raw as Dictionary)[item])
		if amount == null:
			return _reject("'%s[%s]' is not an integer (found %s)"
				% [DEAD_COUNTER_PATH, str(item),
				_type_name((raw as Dictionary)[item])])
		counts[str(item)] = int(amount)
	return {"ok": true, "error": "", "counts": counts}


## Classifies one committed row and produces either a unit instance or a
## building record. The committed `type` is the only gate (D3).
static func _classify(registry: RegistryScript, key: String, row: Variant,
		resolve_nested: Callable) -> Dictionary:
	var valid := UnitInstance.validate_row(row, key, "")
	if not bool(valid.get("ok", false)):
		return _forward(str(valid.get("error", "")))
	var item := int((row as Array)[UnitInstance.SLOT_ITEM])
	var item_text := str(item)
	var as_unit: Dictionary = registry.get_entry(UNIT_DOMAIN, item_text)
	if bool(as_unit.get("found", false)):
		var parsed := UnitDefinition.parse(as_unit["entry"])
		if not bool(parsed.get("ok", false)):
			return _reject("map key '%s' carries item %d, whose committed unit "
				% [key, item] + "row is unparseable: %s"
				% str(parsed.get("error", "")))
		# The definition's own committed `type` is the gate: a `u`-domain row
		# whose type is not `u` is refused here, named, never coerced.
		var built := UnitInstance.build(key, "", row, parsed["definition"],
			resolve_nested, 0)
		if not bool(built.get("ok", false)):
			return _forward(str(built.get("error", "")))
		return {"ok": true, "error": "", "is_unit": true, "item_id": item_text,
			"instance": built["instance"]}
	var as_building: Dictionary = registry.get_entry(BUILDING_DOMAIN, item_text)
	if not bool(as_building.get("found", false)):
		return _reject("map key '%s' carries item %d, which resolves in neither "
			% [key, item] + "the '%s' nor the '%s' content domain"
			% [UNIT_DOMAIN, BUILDING_DOMAIN])
	var entry: Dictionary = as_building["entry"]
	var committed_type: Variant = entry.get("type", null)
	if not (committed_type is String):
		return _reject("map key '%s' carries item %d, whose committed row has no "
			% [key, item] + "string 'type' (found %s)"
			% _type_name(committed_type))
	if not CLASSIFIED_TYPES.has(str(committed_type)):
		return _reject(("map key '%s' carries item %d, whose committed type is "
			+ "'%s', which is neither the unit type '%s' nor the building "
			+ "type '%s': refused rather than coerced")
			% [key, item, str(committed_type), TYPE_UNIT, TYPE_BUILDING])
	var item_name: Variant = entry.get("name", null)
	if not (item_name is String):
		return _reject("map key '%s' carries item %d, whose committed row has no "
			% [key, item] + "string 'name' (found %s)" % _type_name(item_name))
	var capacity: Variant = _integer(entry.get(CAPACITY_FIELD, null))
	if capacity == null:
		return _reject("map key '%s' carries item %d, whose committed %s is not "
			% [key, item, CAPACITY_FIELD] + "an integer (found %s)"
			% _type_name(entry.get(CAPACITY_FIELD, null)))
	# A building's own container is parsed into unit instances exactly as a unit
	# row's is: push_unit moves a row into a container row, and the committed
	# garrison-capable rows are buildings.
	var garrison := UnitInstance.parse_garrison(key,
		str(UnitInstance.SLOT_GARRISON),
		(row as Array)[UnitInstance.SLOT_GARRISON], resolve_nested, 1)
	if not bool(garrison.get("ok", false)):
		return _forward(str(garrison.get("error", "")))
	return {"ok": true, "error": "", "is_unit": false, "item_id": item_text,
		"record": {
			"key": key,
			"item_id": item_text,
			"name": str(item_name),
			"type": str(committed_type),
			"committed_unit_capacity": int(capacity),
			"capacity_enforced": false,
			"garrison_state": str(garrison["state"]),
			"garrison": garrison["members"],
		}}


## The caller-supplied resolver a `UnitInstance` uses for a garrisoned row: a
## garrisoned row is always a **unit** row, so it resolves in the `units` domain
## and nowhere else. A building id inside a container is therefore refused rather
## than reported as a garrisoned building.
static func _nested_resolver(registry: RegistryScript) -> Callable:
	return func(item_id_text: String) -> Dictionary:
		var resolved: Dictionary = registry.get_entry(UNIT_DOMAIN, item_id_text)
		if not bool(resolved.get("found", false)):
			return {"ok": false, "error": "no committed unit definition for "
				+ "item id %s: a garrisoned row must be a unit row"
				% item_id_text, "definition": null}
		var parsed := UnitDefinition.parse(resolved["entry"])
		if not bool(parsed.get("ok", false)):
			return {"ok": false, "error": str(parsed.get("error", "")),
				"definition": null}
		return {"ok": true, "error": "", "definition": parsed["definition"]}


## Walks an instance tree depth-first into `out`, recording the deepest row it
## reached. Every nested member is an instance in its own right, so it belongs
## in the projection's total.
static func _collect(tree: Array, out: Array, seen: Dictionary) -> void:
	for node: Variant in tree:
		out.append(node)
		seen["max_depth"] = maxi(int(seen.get("max_depth", 0)), int(node.depth()))
		_collect(node.garrison(), out, seen)


## Records which reserved production-queue keys a classified row carries, with
## their committed values. **Reading is projection; writing is behaviour and is
## not implemented** (D6): this records presence and value and derives no queue
## state from them.
static func _record_reserved(projection: MapProjection, key: String,
		item_id: String, row: Variant) -> void:
	var bag: Dictionary = (row as Array)[UnitInstance.SLOT_ATTR]
	var present: Array = []
	var values := {}
	for name: String in reserved_key_names():
		if not bag.has(name):
			continue
		present.append(name)
		values[name] = bag[name]
		projection.reserved_presence[name] = \
			int(projection.reserved_presence.get(name, 0)) + 1
	if present.is_empty():
		return
	projection.reserved_rows.append({"key": key, "item_id": item_id,
		"reserved_keys": present, "committed_values": values})


static func _reject(message: String) -> Dictionary:
	return {"ok": false,
		"error": "[unit-instance] projection rejected: " + message,
		"projection": null}


## A sub-module's own already-named failure, forwarded verbatim rather than
## wrapped a second time.
static func _forward(message: String) -> Dictionary:
	return {"ok": false, "error": message, "projection": null}


static func _gate_error(message: String) -> Dictionary:
	return {"ok": false, "error": "[unit-instance] projection rejected: "
		+ message}


## A committed integer: an `int` or an integral `float` inside the transported
## exact-integer range, the documented transport tolerance of the pinned
## engine's JSON parser. A numeric string fails closed.
static func _integer(value: Variant) -> Variant:
	if value is int:
		return int(value)
	if value is float:
		var number := float(value)
		if number == floor(number) and is_finite(number) \
				and absf(number) <= 9007199254740992.0:
			return int(number)
	return null


## The observed type of a refused value, so a failure names what it found.
static func _type_name(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "bool"
		TYPE_INT:
			return "int"
		TYPE_FLOAT:
			return "float"
		TYPE_STRING:
			return "string"
		TYPE_ARRAY:
			return "array"
		TYPE_DICTIONARY:
			return "object"
		_:
			return "unsupported"
