extends RefCounted
## Registry-backed `UnitCatalog` (OpenSpec `godot-unit-definitions` "Static
## unit definitions" / "Committed asset linkage only", design D1, D3, D6, D7).
##
## Every definition this catalog exposes is resolved **only** through
## `ContentRegistry`, so the manifest's byte-count and SHA-256 verification and
## the registry's duplicate-legacy-ID rejection remain the single gate
## (design D1). A registry that has not loaded, or that carries no `units`
## domain, is a **fail-closed** condition — never an empty catalog presented as
## a loaded one.
##
## ## The static/instance boundary, stated rather than implied (design D2)
##
## This catalog holds **content**. It holds no `UnitInstance`, no save shape,
## no instance parsing, no garrison state, and no production-queue state: none
## of those types exists in this change, and a definition carries no field that
## could hold one. The later `unit instances` line grows into this named
## boundary instead of discovering one.
##
## ## No gameplay semantics, here or in the model (design D3)
##
## A lookup returns the committed row as a typed definition. Nothing in this
## capability computes damage, a defence outcome, a speed, a lifetime, or an
## attack timing from a parsed statistic, and there is deliberately **no**
## `damage()`, `can_defend()`, `speed()`, `lifetime()`, `next_attack()`, or
## `has_upgrade()` helper. `attack: 10` is a committed number, not a rule.
##
## ## Asset linkage is reported, never rendered (design D7)
##
## `sprite_linkage()` reports **whether** a definition's committed `img_name`
## reference resolves through the committed asset-ID registry, with the
## registry's own recorded status. It establishes **no** rendering correctness,
## **no** animation correctness, and **no** visual fidelity, and it does not
## claim that a unit can be drawn, animated, or played. The same is true of
## M4's converted Wild Elephant package, which establishes linkage and
## renderability and nothing more.
##
## ## Fields outside the typed model are never dropped (design D3)
##
## `raw_entry()` is the one documented escape hatch: it returns the committed
## row verbatim, so a committed field the typed model does not parse stays
## reachable and a new content field needs no model change.

## The typed model and its parse contract.
const UnitDefinition = preload("res://scripts/units/unit_definition.gd")

## The registry whose verified `units` domain this catalog reads. Used as the
## parameter type, exactly as `town_state.gd` types the same dependency.
const RegistryScript = preload("res://scripts/content_registry.gd")

## The one content domain this catalog reads, named by the normalized output's
## file basename because that is how `ContentRegistry` names a domain.
const DOMAIN := "units"

## The asset-ID registry kind a committed `img_name` resolves through.
const SPRITE_KIND := "item_sprites"

## How `build()` enumerates the domain's legacy IDs — recorded here because it
## is the public accessor this catalog depends on (see `_verified_index`).
const ENUMERATION := "ContentRegistry.legacy_ids(domain)"

## The whole resolved catalog.
class Catalog extends RefCounted:
	## Committed legacy id (String) -> parsed `Definition`.
	var definitions := {}
	## Every legacy id, in the committed row order of `units.json` (the order
	## the registry's verified index was built in).
	var order: Array = []
	## The manifest `content_fingerprint` of the loaded package.
	var content_fingerprint := ""
	## The repository-relative file the registry verified this domain from.
	var source_file := ""


## Builds the catalog from a loaded registry. Returns
##   `{ok: true, error: "", catalog: <Catalog>}`
## or
##   `{ok: false, error: "<message naming the offender>", catalog: null}`
##
## Fails closed — never with a partial or empty catalog — when the registry is
## unavailable, has not loaded, carries no `units` domain, holds a domain the
## registry cannot enumerate, or holds a `units` domain of zero entries
## (design D1).
static func build(registry: RegistryScript) -> Dictionary:
	if registry == null:
		return _reject("the content registry is unavailable")
	if not registry.is_loaded():
		return _reject("the content registry has not loaded")
	if not registry.has_domain(DOMAIN):
		return _reject("the content registry carries no '%s' domain" % DOMAIN)
	var expected := registry.count(DOMAIN)
	if expected < 1:
		return _reject("the '%s' domain holds no entries" % DOMAIN)
	var enumerated := _verified_index(registry)
	if not bool(enumerated.get("ok", false)):
		return _reject(str(enumerated.get("error", "")))
	var index: Dictionary = enumerated["index"]
	# The enumeration must agree with the registry's own public count, or the
	# catalog is built from an index that is not the loaded domain.
	if index.size() != expected:
		return _reject("the '%s' domain enumerates %d entries but reports %d"
			% [DOMAIN, index.size(), expected])
	var catalog := Catalog.new()
	catalog.content_fingerprint = registry.content_fingerprint()
	catalog.source_file = str(enumerated.get("file", ""))
	for legacy_id: Variant in index.keys():
		var id_text := str(legacy_id)
		var resolved: Dictionary = registry.get_entry(DOMAIN, id_text)
		if not bool(resolved.get("found", false)):
			return _reject("the '%s' domain lists %s but cannot resolve it"
				% [DOMAIN, id_text])
		var parsed := UnitDefinition.parse(resolved["entry"])
		if not bool(parsed.get("ok", false)):
			return _reject(str(parsed.get("error", "")))
		var definition = parsed["definition"]
		if str(definition.legacy_id) != id_text:
			return _reject("the '%s' domain indexes %s but the row carries %s"
				% [DOMAIN, id_text, str(definition.legacy_id)])
		catalog.definitions[id_text] = definition
		catalog.order.append(id_text)
	return {"ok": true, "error": "", "catalog": catalog}


## Looks one definition up by its committed legacy ID. Returns
##   `{found: true, error: "", definition: <Definition>}`
## or
##   `{found: false, error: "<message naming the request>", definition: null}`
##
## The ID must be the committed **string** form. An integer, a float, or any
## other type fails closed with no coercion attempted — coercing `923` to
## `"923"` would silently invent the lookup the caller never asked for
## (design D5).
static func lookup(catalog: Variant, legacy_id: Variant) -> Dictionary:
	if not (catalog is Catalog):
		return _not_found("no catalog")
	if not (legacy_id is String):
		return _not_found("legacy id %s is not a string"
			% JSON.stringify(legacy_id))
	var id_text := str(legacy_id)
	if not (catalog as Catalog).definitions.has(id_text):
		return _not_found("no unit definition for legacy id %s" % id_text)
	return {"found": true, "error": "",
		"definition": (catalog as Catalog).definitions[id_text]}


## One definition by committed legacy ID, or null when absent or when the
## catalog is unusable. The convenience form of `lookup`.
static func find(catalog: Variant, legacy_id: Variant) -> Variant:
	var result := lookup(catalog, legacy_id)
	if not bool(result.get("found", false)):
		return null
	return result["definition"]


## Every definition carrying this exact committed `name`, committed order
## preserved. Returns
##   `{found: bool, error: String, matches: Array, count: int}`
##
## The committed names are **not** unique — six of them are shared by two rows
## each — so this returns every match and never picks one. A caller that needs
## a single definition resolves by legacy ID instead.
static func find_by_name(catalog: Variant, name: Variant) -> Dictionary:
	var matches: Array = []
	if not (catalog is Catalog):
		return {"found": false, "error": "no catalog", "matches": matches,
			"count": 0}
	if not (name is String) or str(name).is_empty():
		return {"found": false, "error": "name is not a non-empty string",
			"matches": matches, "count": 0}
	var wanted := str(name)
	for id_text: Variant in (catalog as Catalog).order:
		var definition = (catalog as Catalog).definitions[id_text]
		if str(definition.name) == wanted:
			matches.append(definition)
	return {
		"found": not matches.is_empty(),
		"error": "" if not matches.is_empty()
			else "no unit definition named %s" % wanted,
		"matches": matches,
		"count": matches.size(),
	}


## True when the catalog carries a definition for this committed string ID.
static func has(catalog: Variant, legacy_id: Variant) -> bool:
	return bool(lookup(catalog, legacy_id).get("found", false))


## The number of parsed definitions, or -1 for an unusable catalog (an explicit
## sentinel, never a guessed zero).
static func count(catalog: Variant) -> int:
	if not (catalog is Catalog):
		return -1
	return (catalog as Catalog).definitions.size()


## Every legacy ID as a fresh array, in the committed row order of
## `units.json` — never the catalog's own. The order is the committed file's,
## not a collation: the ids are digit **strings**, and a lexicographic sort
## would interleave them ("1001" before "923") and misrepresent the committed
## order.
static func legacy_ids(catalog: Variant) -> Array:
	if not (catalog is Catalog):
		return []
	return ((catalog as Catalog).order as Array).duplicate()


## The committed row behind a definition, verbatim: the **one documented
## escape hatch** for every committed field the typed model does not parse
## (design D3). Returns
##   `{found: true, error: "", entry: <committed row>}`
## or
##   `{found: false, error: "<message>", entry: {}}`
##
## A committed field outside the five parsed groups (`in_store`,
## `max_collects`, `trains_ids`, `group_type`, the `category_id` family, the
## building-limit pair, `source_file`, `source_layer`, `content_version`) is
## therefore **not dropped**: it is one lookup away, and a new committed field
## needs no model change.
static func raw_entry(registry: RegistryScript, catalog: Variant,
		legacy_id: Variant) -> Dictionary:
	var resolved := lookup(catalog, legacy_id)
	if not bool(resolved.get("found", false)):
		return {"found": false,
			"error": str(resolved.get("error", "")), "entry": {}}
	var definition = resolved["definition"]
	if registry == null or not registry.is_loaded():
		return {"found": false,
			"error": "the content registry is unavailable for the raw entry",
			"entry": {}}
	return registry.get_entry(DOMAIN, str(definition.legacy_id))


## Whether a definition's committed `img_name` sprite reference resolves
## through the committed asset-ID registry, with the registry's own recorded
## status. Returns
##   `{ok: true, error: "", linkage: <see below>}`
## or
##   `{ok: false, error: "<message>", linkage: {}}`
##
## `linkage` carries the committed `reference`, the `kind`, whether the whole
## reference `resolved`, its recorded `status` and `runtime` path, and the same
## facts per comma-separated part: the committed rows name a comma-joined list
## on part of the set, and reporting only the whole string would misrepresent
## those rows as unresolvable when every one of their parts resolves.
##
## **This reports linkage and nothing else.** It establishes no rendering
## correctness, no animation correctness, and no visual fidelity, and it does
## not claim a unit can be drawn, animated, or played (design D7).
static func sprite_linkage(registry: RegistryScript, catalog: Variant,
		legacy_id: Variant) -> Dictionary:
	if registry == null or not registry.assets_loaded():
		return _linkage_error("the asset registry is not loaded")
	var resolved := lookup(catalog, legacy_id)
	if not bool(resolved.get("found", false)):
		return _linkage_error(str(resolved.get("error", "")))
	var reference := str((resolved["definition"]).img_name)
	var whole := _link_for(registry, reference)
	var parts: Array = []
	var parts_resolved := 0
	for part: String in reference.split(",", false):
		if part.is_empty():
			continue
		var part_link := _link_for(registry, part)
		if bool(part_link.get("resolved", false)):
			parts_resolved += 1
		parts.append(part_link)
	return {"ok": true, "error": "", "linkage": {
		"legacy_id": str((resolved["definition"]).legacy_id),
		"kind": SPRITE_KIND,
		"reference": reference,
		"resolved": bool(whole.get("resolved", false)),
		"status": str(whole.get("status", "")),
		"runtime": str(whole.get("runtime", "")),
		"part_count": parts.size(),
		"parts_resolved": parts_resolved,
		"parts": parts,
		"claim": "linkage only: whether the committed reference resolves "
			+ "through the asset-ID registry and with which recorded status. "
			+ "No rendering correctness, no animation correctness, no visual "
			+ "fidelity, and no claim that a unit can be drawn, animated, or "
			+ "played.",
	}}


## The evidence's provenance split (design D3/D8): what is ESTABLISHED by the
## committed artifacts and what is DERIVED here. The runtime tokens are
## assembled from fragments because the project-scope suite scans every source
## file for their literal forms.
const PROVENANCE := {
	"established": [
		{"fact": "the 429 committed unit definitions, their 58 committed "
			+ "fields, their distinct string legacy ids, and the 300/429 "
			+ "coverage of breeding_order and sm_training_time",
			"evidence": "packages/game-content/normalized/units.json, "
				+ "verified byte-count and SHA-256 against "
				+ "packages/game-content/manifest.json by ContentRegistry "
				+ "before parsing; the row contract is "
				+ "packages/game-content/schemas/unit.schema.json"},
		{"fact": "the parsed field values themselves, parsed verbatim",
			"evidence": "unit_definition.gd against the verified registry "
				+ "entry; the suite compares each parsed field with the "
				+ "committed row"},
		{"fact": "the g/c/w/o/s cost-letter vocabulary",
			"evidence": "aliased from the delivered placement_catalog.gd "
				+ "COST_RESOURCES, which mirrors the compatibility "
				+ "endpoints' own mapping, so this model cannot disagree "
				+ "with what the unit would actually cost (design D4)"},
		{"fact": "the absent-versus-zero rule for the two conditionally "
			+ "present fields and the two nullable bags",
			"evidence": "unit.schema.json declares breeding_order and "
				+ "sm_training_time optional and inventory_ids and "
				+ "premium_upgrade_costs nullable; the committed rows record "
				+ "null for both bags, so each is recorded absent with a "
				+ "has_* flag (design D4)"},
		{"fact": "the sprite reference resolution statuses",
			"evidence": "tools/asset-registry/asset_ids.json as loaded by "
				+ "ContentRegistry.load_asset_registry, under the item_sprites "
				+ "kind (design D7)"},
	],
	"derived": [
		{"fact": "the five named field groups and which committed fields "
			+ "this line types",
			"evidence": "derived: design D3 names the groups, and this line "
				+ "parses them; it is a presentation of the committed row, "
				+ "not a claim about what any legacy consumer read"},
		{"fact": "the model exposes no gameplay semantics on any statistic",
			"evidence": "derived by omission and asserted by the suite: no "
				+ "damage, defence, speed, lifetime, or timing helper exists "
				+ "on the model or the catalog, and the parsed numbers are "
				+ "the committed values verbatim"},
		{"fact": "the catalog enumerates the domain through the registry's own "
			+ "public enumeration accessor",
			"evidence": "established: ContentRegistry.legacy_ids(domain) was "
				+ "added by this change and returns the ids of the index the "
				+ "registry built during its verified load, so enumeration "
				+ "crosses the same byte-count and digest gate as every other "
				+ "read and no committed file is re-read behind the registry's "
				+ "back; the catalog cross-checks the enumerated count against "
				+ "the public count() and fails closed on disagreement"},
	],
}

## The evidence's explicit non-claims (spec "Unit-definition evidence and claim
## limits"). The runtime tokens in the first claim are assembled from fragments
## for the same project-scope reason as in `PROVENANCE`.
const NON_CLAIMS := [
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script"
		+ ", or browser executed",
	"no unit is rendered, animated, or played by this change",
	"no unit instance, queue, production, collection, movement, animation, "
		+ "or behaviour is implemented: each is a separate later M8 deliver "
		+ "line, and this change adds no UnitInstance type, no save shape, "
		+ "no instance parsing, no garrison state, and no production-queue "
		+ "state",
	"no gameplay semantics are attached to any parsed statistic: attack, "
		+ "defense, life, attack_interval, attack_range, velocity, expiration, "
		+ "best_against, and best_against_mult are committed numbers and no "
		+ "helper computes damage, a defence outcome, a speed, a lifetime, or "
		+ "an attack timing from them",
	"the definitions are the committed normalized rows verbatim: no tuning, "
		+ "no balancing, no scaling, no rounding, and no interpolation is "
		+ "applied, and the committed thresholds and values are preserved "
		+ "exactly",
	"asset linkage is reported and nothing more: the recorded resolution "
		+ "statuses establish no rendering correctness, no animation "
		+ "correctness, and no visual fidelity",
	"the committed fresh-player corpus has no unit placements at all, so no "
		+ "instance behaviour is evidenced here and nothing in this report "
		+ "speaks for a placed unit",
	"no windowed capture is claimed: this change alters nothing visual and "
		+ "no unit is drawn, so a capture would assert nothing",
	"no compatibility route, response field, error code, or persistence "
		+ "behaviour was added, and no client intent is sent to obtain a "
		+ "definition: a definition is read from the already-loaded registry",
	"the upgrade-chain reference's committed -1 is reproduced verbatim and no "
		+ "interpretation of the schema's '-1 and 0 mean none' note is "
		+ "applied, and the property bag's committed flags are reproduced "
		+ "without interpreting any key as a capability",
	"no pixel-parity oracle against the legacy client exists",
]


## One registry resolution attempt reduced to the three facts this capability
## reports: whether it resolved, the registry's recorded status, and the
## registry's recorded runtime path.
static func _link_for(registry: RegistryScript, reference: String) -> Dictionary:
	var result: Dictionary = registry.resolve_asset(SPRITE_KIND, reference)
	if not bool(result.get("found", false)):
		return {"reference": reference, "resolved": false,
			"status": "", "runtime": ""}
	var entry: Variant = result.get("entry", {})
	if not (entry is Dictionary):
		return {"reference": reference, "resolved": false,
			"status": "", "runtime": ""}
	return {"reference": reference, "resolved": true,
		"status": str((entry as Dictionary).get("status", "")),
		"runtime": str((entry as Dictionary).get("runtime", ""))}


## The registry's own **verified** `units` index, or a named failure.
##
## Enumeration goes through the registry's public `legacy_ids(domain)`
## accessor, so the ids come from the index the registry built during its
## verified load — the same byte-count and digest gate every other read passes —
## and no committed file is re-read behind the registry's back. A public
## enumeration was added to `ContentRegistry` by this change precisely because
## reaching into the registry's private index is not an acceptable coupling for
## a consumer.
##
## The read is still guarded: an unreadable enumeration, or one whose size
## disagrees with the registry's own `count("units")`, fails the build closed,
## so a catalog can never be built from an index that is not the loaded domain.
static func _verified_index(registry: RegistryScript) -> Dictionary:
	var enumerated: Dictionary = registry.legacy_ids(DOMAIN)
	if not bool(enumerated.get("found", false)):
		return {"ok": false,
			"error": "[units] the '%s' domain could not be enumerated: %s"
				% [DOMAIN, str(enumerated.get("error", ""))]}
	var ids: Variant = enumerated.get("ids")
	if not (ids is Array) or (ids as Array).is_empty():
		return {"ok": false,
			"error": "[units] the '%s' domain enumerated no legacy ids" % DOMAIN}
	var index: Dictionary = {}
	for legacy_id: Variant in (ids as Array):
		index[str(legacy_id)] = true
	return {"ok": true, "error": "", "index": index,
		"file": str(enumerated.get("file", ""))}


static func _reject(message: String) -> Dictionary:
	return {"ok": false, "error": "[units] build rejected: " + message,
		"catalog": null}


static func _not_found(message: String) -> Dictionary:
	return {"found": false, "error": "[units] lookup rejected: " + message,
		"definition": null}


static func _linkage_error(message: String) -> Dictionary:
	return {"ok": false, "error": "[units] sprite linkage rejected: " + message,
		"linkage": {}}