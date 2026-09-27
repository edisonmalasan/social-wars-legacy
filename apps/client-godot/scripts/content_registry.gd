extends Node
## `ContentRegistry` autoload — canonical, manifest-verified, read-only
## access to the normalized content package and to the asset ID registry
## (design D1–D3/D5, spec "Canonical content registry loading", "Domain
## indexing and lookup", "Client asset resolution").
##
## The inventory is driven entirely by `packages/game-content/manifest.json`:
## the root `outputs` list plus the outputs of the nine extension sections
## (22 files) are read, their byte counts and SHA-256 digests are verified
## against the manifest BEFORE the bytes are parsed, and each domain is
## indexed by `str(legacy_id)`. A missing, altered, unparseable, or
## duplicate-identified file fails the load with an explicit error naming
## the offender; a failed load never replaces previously loaded state and
## never serves partial content.
##
## Nothing here writes into the content package, and no script in this
## project may reference a legacy protocol token or a non-loopback transport
## (the project-scope test enforces that).
##
## Loading is explicit (`load_content()`), never implicit in `_ready()`, so
## scenes and suites that do not consume content pay no cost and a damaged
## package cannot take down an unrelated run.

const Paths = preload("res://scripts/package_paths.gd")

## Repository-relative root of the content package (POSIX, forward slashes).
const PACKAGE_ROOT := "packages/game-content"
## Manifest file inside the package root.
const MANIFEST_FILE := "manifest.json"
## The nine extension sections whose `outputs` complete the inventory.
const EXTENSION_SECTIONS := [
	"quests", "tables", "economy", "social", "taxonomy", "darts",
	"globals", "offers", "images",
]
## Asset ID registry (repository-relative) and its identity contract.
const ASSET_REGISTRY_FILE := "tools/asset-registry/asset_ids.json"
const ASSET_POLICY := "asset-id-registry-v1"
const ASSET_SCHEMA_VERSION := 1
## The four asset reference domains, in the registry's fixed order.
const ASSET_KINDS := ["images", "item_sprites", "magic_sprites", "sounds"]
## Statuses that truthfully carry a runtime path.
const ASSET_STATUS_WITH_RUNTIME := ["converted", "extracted", "passthrough"]
## The closed status vocabulary (spec: "Deterministic asset ID registry").
const ASSET_STATUSES := [
	"converted", "extracted", "passthrough", "pending", "ambiguous",
	"missing_source",
]

## True once the default package has loaded successfully.
var _loaded := false
## Root `content_fingerprint` of the manifest that loaded successfully.
var _fingerprint := ""
## Section name -> Array of domain names it contributed.
var _sections: Dictionary = {}
## Domain name -> {"entries": Array, "index": Dictionary, "file": String}.
var _domains: Dictionary = {}

## True once the asset ID registry has loaded successfully.
var _assets_loaded := false
## kind -> ref -> entry.
var _assets: Dictionary = {}
## kind -> status -> count (derived from the entries themselves).
var _asset_status_counts: Dictionary = {}


func _ready() -> void:
	# Deliberately no I/O: loading is explicit (design D3).
	pass


# ---------------------------------------------------------------------------
# Content package loading
# ---------------------------------------------------------------------------

## Loads and verifies the content package under `base_dir` (a directory that
## contains `packages/game-content/`; "" = the repository root). On success
## the parsed domains become the active state and `{ok: true, ...}` with the
## section map, per-domain counts, and verification totals is returned. On
## failure `{ok: false, error: "<message naming the offender>"}` is returned
## and any previously loaded state is left untouched.
func load_content(base_dir: String = "") -> Dictionary:
	var root := _resolve_base(base_dir)
	var manifest_result := _read_manifest(root)
	if not manifest_result.get("ok", false):
		return {"ok": false, "error": str(manifest_result.get("error", ""))}
	var manifest: Dictionary = manifest_result["data"]
	var structure_error := _check_manifest_structure(manifest)
	if structure_error != "":
		return {"ok": false, "error": structure_error}
	# Build the whole package in locals: a failure half-way through must not
	# leave a partial index behind.
	var sections: Dictionary = {}
	var domains: Dictionary = {}
	var files_verified := 0
	var bytes_verified := 0
	var seen_files: Dictionary = {}
	for item in _collect_outputs(manifest):
		var section := str(item["section"])
		var entry_v: Variant = item["entry"]
		if typeof(entry_v) != TYPE_DICTIONARY:
			return {"ok": false,
				"error": "[content] manifest output under %s is not an object"
				% section}
		var entry: Dictionary = entry_v
		var file_error := _check_output_file(entry)
		if file_error != "":
			return {"ok": false, "error": file_error}
		var file := str(entry["file"])
		if seen_files.has(file):
			return {"ok": false,
				"error": "[content] manifest lists %s twice" % file}
		seen_files[file] = true
		var loaded := _read_verify_parse(root, file, entry)
		if not loaded.get("ok", false):
			return {"ok": false, "error": str(loaded.get("error", ""))}
		var parsed_entries: Array = loaded["data"]
		var domain := _domain_name(file)
		var indexed := _index_domain(domain, parsed_entries)
		if not indexed.get("ok", false):
			return {"ok": false, "error": str(indexed.get("error", ""))}
		domains[domain] = {
			"entries": parsed_entries,
			"index": indexed["index"],
			"file": file,
		}
		if not sections.has(section):
			sections[section] = []
		(sections[section] as Array).append(domain)
		files_verified += 1
		bytes_verified += int(entry["bytes"])
	if files_verified == 0:
		return {"ok": false,
			"error": "[content] manifest declares no outputs"}
	# Everything verified: commit the state atomically.
	_loaded = true
	_fingerprint = str(manifest.get("content_fingerprint", ""))
	_sections = sections
	_domains = domains
	return {
		"ok": true,
		"error": "",
		"sections": sections.duplicate(true),
		"counts": counts(),
		"content_fingerprint": _fingerprint,
		"files_verified": files_verified,
		"bytes_verified": bytes_verified,
	}


## True once the default package has been loaded successfully.
func is_loaded() -> bool:
	return _loaded


## Section name -> domain names (empty before load).
func sections() -> Dictionary:
	return _sections.duplicate(true)


## Sorted list of loaded domain names (empty before load).
func domains_list() -> Array:
	var names := _domains.keys()
	names.sort()
	return names


## True when `domain` is a loaded domain.
func has_domain(domain: String) -> bool:
	return _domains.has(domain)


## Entry count for `domain`, or -1 for an unknown domain (explicit sentinel,
## never a guessed zero).
func count(domain: String) -> int:
	if not _domains.has(domain):
		return -1
	return (_domains[domain]["entries"] as Array).size()


## Per-domain entry counts for every loaded domain.
func counts() -> Dictionary:
	var out := {}
	for domain in _domains:
		out[domain] = (_domains[domain]["entries"] as Array).size()
	return out


## Root `content_fingerprint` of the loaded manifest ("" before load).
func content_fingerprint() -> String:
	return _fingerprint


## Looks up one entry. Returns
##   {"found": true, "error": "", "entry": <stored entry>}
## or
##   {"found": false, "error": "<message naming domain/reference>", "entry": {}}
## — an explicit not-found result, never a null or guessed value.
func get_entry(domain: String, legacy_id: String) -> Dictionary:
	if not _domains.has(domain):
		return {"found": false,
			"error": "[content] unknown domain: %s" % domain, "entry": {}}
	var index: Dictionary = _domains[domain]["index"]
	if not index.has(legacy_id):
		return {"found": false,
			"error": "[content] no entry %s in domain %s"
			% [legacy_id, domain], "entry": {}}
	var entry_v: Variant = index[legacy_id]
	if typeof(entry_v) != TYPE_DICTIONARY:
		return {"found": false,
			"error": "[content] stored entry %s in domain %s is not an object"
			% [legacy_id, domain], "entry": {}}
	return {"found": true, "error": "", "entry": entry_v}


# ---------------------------------------------------------------------------
# Asset ID registry (spec: "Client asset resolution")
# ---------------------------------------------------------------------------

## Loads `tools/asset-registry/asset_ids.json` (under `base_dir`; "" = the
## repository root), validating its identity, the four kind domains, the
## closed status vocabulary, and the runtime-path contract before the index
## becomes active. Failure returns `{ok: false, error}` and leaves prior
## state untouched.
func load_asset_registry(base_dir: String = "") -> Dictionary:
	var root := _resolve_base(base_dir)
	var parsed := _read_json_object(root, ASSET_REGISTRY_FILE)
	if not parsed.get("ok", false):
		return {"ok": false, "error": str(parsed.get("error", ""))}
	var data: Dictionary = parsed["data"]
	for required in ["schema_version", "policy", "result", "kinds"]:
		if not data.has(required):
			return {"ok": false,
				"error": "[content] asset registry missing field: %s"
				% required}
	if int(data["schema_version"]) != ASSET_SCHEMA_VERSION:
		return {"ok": false,
			"error": "[content] asset registry schema_version is %s (want %s)"
			% [data["schema_version"], ASSET_SCHEMA_VERSION]}
	if str(data["policy"]) != ASSET_POLICY:
		return {"ok": false,
			"error": "[content] asset registry policy is %s (want %s)"
			% [data["policy"], ASSET_POLICY]}
	if str(data["result"]) != "success":
		return {"ok": false,
			"error": "[content] asset registry result is not success: %s"
			% data["result"]}
	if typeof(data["kinds"]) != TYPE_ARRAY:
		return {"ok": false,
			"error": "[content] asset registry 'kinds' is not an array"}
	var assets: Dictionary = {}
	var status_counts: Dictionary = {}
	for kind in ASSET_KINDS:
		assets[kind] = {}
		status_counts[kind] = {}
	var seen_kinds: Dictionary = {}
	for block_v in data["kinds"]:
		if typeof(block_v) != TYPE_DICTIONARY or not block_v.has("kind"):
			return {"ok": false,
				"error": "[content] asset registry kind block is malformed"}
		var block: Dictionary = block_v
		var kind := str(block["kind"])
		if seen_kinds.has(kind):
			return {"ok": false,
				"error": "[content] asset registry repeats kind: %s" % kind}
		seen_kinds[kind] = true
		if not assets.has(kind):
			return {"ok": false,
				"error": "[content] asset registry has unknown kind: %s"
				% kind}
		if not block.has("entries") \
				or typeof(block["entries"]) != TYPE_ARRAY:
			return {"ok": false,
				"error": "[content] asset registry kind %s has no entries array"
				% kind}
		for entry_v in block["entries"]:
			var validated := _validate_asset_entry(kind, entry_v)
			if not validated.get("ok", false):
				return {"ok": false,
					"error": str(validated.get("error", ""))}
			var entry: Dictionary = entry_v
			var ref := str(entry["ref"])
			if assets[kind].has(ref):
				return {"ok": false,
					"error": "[content] asset registry repeats %s ref: %s"
					% [kind, ref]}
			assets[kind][ref] = entry
			var status := str(entry["status"])
			status_counts[kind][status] = \
				int(status_counts[kind].get(status, 0)) + 1
	for kind in ASSET_KINDS:
		if not seen_kinds.has(kind):
			return {"ok": false,
				"error": "[content] asset registry is missing kind: %s" % kind}
	_assets_loaded = true
	_assets = assets
	_asset_status_counts = status_counts
	return {"ok": true, "error": "",
		"counts": asset_status_counts(),
		"distinct": _asset_distinct(assets)}


## True once the asset ID registry has been loaded successfully.
func assets_loaded() -> bool:
	return _assets_loaded


## kind -> status -> count for every loaded kind.
func asset_status_counts() -> Dictionary:
	var out := {}
	for kind in _assets:
		out[kind] = (_asset_status_counts[kind] as Dictionary).duplicate()
	return out


## Resolves one asset reference. Returns
##   {"found": true, "error": "", "entry": <registry entry>}
## for a known reference (its `status` may still be `pending`, `ambiguous`,
## or `missing_source` — known-but-unavailable), or
##   {"found": false, "error": "<message naming kind/reference>", "entry": {}}
## for an unknown kind or a reference the registry does not contain.
func resolve_asset(kind: String, ref: String) -> Dictionary:
	if not _assets_loaded:
		return {"found": false,
			"error": "[content] asset registry is not loaded", "entry": {}}
	if not _assets.has(kind):
		return {"found": false,
			"error": "[content] unknown asset kind: %s" % kind, "entry": {}}
	var index: Dictionary = _assets[kind]
	if not index.has(ref):
		return {"found": false,
			"error": "[content] no %s asset reference: %s" % [kind, ref],
			"entry": {}}
	var entry_v: Variant = index[ref]
	if typeof(entry_v) != TYPE_DICTIONARY:
		return {"found": false,
			"error": "[content] stored %s asset entry is not an object" % kind,
			"entry": {}}
	return {"found": true, "error": "", "entry": entry_v}


# ---------------------------------------------------------------------------
# Internals — content package
# ---------------------------------------------------------------------------

## Reads and parses `manifest.json` (structure checked separately).
func _read_manifest(root: String) -> Dictionary:
	return _read_json_object(root, PACKAGE_ROOT + "/" + MANIFEST_FILE)


## Structural check of the manifest itself: integer schema_version, the root
## outputs array, and all nine extension sections with outputs arrays.
func _check_manifest_structure(manifest: Dictionary) -> String:
	if not manifest.has("schema_version") \
			or not _is_int_like(manifest["schema_version"]):
		return "[content] manifest has no integer schema_version"
	for section in EXTENSION_SECTIONS:
		if not manifest.has(section):
			return "[content] manifest is missing section: %s" % section
		var body: Variant = manifest[section]
		if typeof(body) != TYPE_DICTIONARY \
				or not (body as Dictionary).has("outputs") \
				or typeof((body as Dictionary)["outputs"]) != TYPE_ARRAY:
			return "[content] manifest section %s has no outputs array" % section
	if not manifest.has("outputs") \
			or typeof(manifest["outputs"]) != TYPE_ARRAY:
		return "[content] manifest has no root outputs array"
	return ""


## Flattens the manifest inventory in section order:
## [{section, entry}, ...] (root first, then the extension sections).
static func _collect_outputs(manifest: Dictionary) -> Array:
	var out := []
	for entry in manifest["outputs"]:
		out.append({"section": "root", "entry": entry})
	for section in EXTENSION_SECTIONS:
		for entry in (manifest[section] as Dictionary)["outputs"]:
			out.append({"section": section, "entry": entry})
	return out


## Structural check of one manifest output record (path containment, types).
static func _check_output_file(entry: Dictionary) -> String:
	for field in ["file", "bytes", "sha256"]:
		if not entry.has(field):
			return "[content] manifest output is missing field '%s'" % field
	var file := str(entry["file"])
	if file.begins_with("/") or file.contains("..") \
			or not file.begins_with(PACKAGE_ROOT + "/"):
		return "[content] manifest output path escapes the package: %s" % file
	if not _is_int_like(entry["bytes"]) or int(entry["bytes"]) < 0:
		return "[content] manifest output %s has non-integer bytes" % file
	var digest := str(entry["sha256"])
	if not _is_sha256(digest):
		return "[content] manifest output %s has a non-sha256 digest" % file
	return ""


## Reads one output file, verifies byte count and SHA-256 against the
## manifest entry BEFORE parsing, and returns the parsed array.
func _read_verify_parse(root: String, file: String,
		entry: Dictionary) -> Dictionary:
	var path := root.path_join(file)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false,
			"error": "[content] cannot read manifest output: %s" % file}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	if bytes.size() != int(entry["bytes"]):
		return {"ok": false,
			"error": "[content] byte count mismatch for %s (manifest %s, got %s)"
			% [file, entry["bytes"], bytes.size()]}
	var digest := Paths.sha256_hex(bytes)
	if digest != str(entry["sha256"]):
		return {"ok": false,
			"error": "[content] sha256 mismatch for %s (manifest %s, got %s)"
			% [file, entry["sha256"], digest]}
	var parser := JSON.new()
	var parse_error := parser.parse(bytes.get_string_from_utf8())
	if parse_error != OK:
		return {"ok": false,
			"error": "[content] invalid JSON in %s at line %d: %s"
			% [file, parser.get_error_line(), parser.get_error_message()]}
	if typeof(parser.data) != TYPE_ARRAY:
		return {"ok": false,
			"error": "[content] %s is not a JSON array" % file}
	return {"ok": true, "data": parser.data}


## Builds the `str(legacy_id)` index for one domain, rejecting duplicates
## and entries without an identifier.
static func _index_domain(domain: String, entries: Array) -> Dictionary:
	var index: Dictionary = {}
	for i in entries.size():
		var entry_v: Variant = entries[i]
		if typeof(entry_v) != TYPE_DICTIONARY:
			return {"ok": false,
				"error": "[content] domain %s entry %d is not an object"
				% [domain, i]}
		var entry: Dictionary = entry_v
		if not entry.has("legacy_id"):
			return {"ok": false,
				"error": "[content] domain %s entry %d has no legacy_id"
				% [domain, i]}
		var key := str(entry["legacy_id"])
		if index.has(key):
			return {"ok": false,
				"error": "[content] domain %s has duplicate legacy_id %s"
				% [domain, key]}
		index[key] = entry
	return {"ok": true, "index": index}


static func _domain_name(file: String) -> String:
	return file.get_file().get_basename()


# ---------------------------------------------------------------------------
# Internals — asset registry
# ---------------------------------------------------------------------------

static func _validate_asset_entry(kind: String,
		entry_v: Variant) -> Dictionary:
	if typeof(entry_v) != TYPE_DICTIONARY:
		return {"ok": false,
			"error": "[content] asset entry in %s is not an object" % kind}
	var entry: Dictionary = entry_v
	for field in ["ref", "status"]:
		if not entry.has(field) or typeof(entry[field]) != TYPE_STRING:
			return {"ok": false,
				"error": "[content] asset entry in %s is missing string '%s'"
				% [kind, field]}
	var status := str(entry["status"])
	if not ASSET_STATUSES.has(status):
		return {"ok": false,
			"error": "[content] asset entry %s/%s has foreign status: %s"
			% [kind, entry["ref"], status]}
	var runtime: Variant = entry.get("runtime", null)
	var carries_runtime: bool = ASSET_STATUS_WITH_RUNTIME.has(status)
	if carries_runtime:
		if typeof(runtime) != TYPE_STRING or str(runtime) == "":
			return {"ok": false,
				"error": "[content] asset entry %s/%s claims status %s without a runtime path"
				% [kind, entry["ref"], status]}
	elif typeof(runtime) == TYPE_STRING and str(runtime) != "":
		return {"ok": false,
			"error": "[content] asset entry %s/%s with status %s must not claim a runtime path"
			% [kind, entry["ref"], status]}
	if status == "ambiguous" and entry.has("candidates") \
			and typeof(entry["candidates"]) != TYPE_ARRAY:
		return {"ok": false,
			"error": "[content] ambiguous asset entry %s/%s has non-array candidates"
			% [kind, entry["ref"]]}
	return {"ok": true}


static func _asset_distinct(assets: Dictionary) -> Dictionary:
	var out := {}
	for kind in assets:
		out[kind] = (assets[kind] as Dictionary).size()
	return out


# ---------------------------------------------------------------------------
# Internals — shared readers
# ---------------------------------------------------------------------------

## Resolves the base directory for package reads: "" = the repository root,
## otherwise the caller-supplied directory that contains the package paths.
static func _resolve_base(base_dir: String) -> String:
	if base_dir.is_empty():
		return Paths.repo_root()
	return base_dir


## Reads a JSON object file; returns {ok, data} or {ok: false, error}.
static func _read_json_object(root: String, relative: String) -> Dictionary:
	var path := root.path_join(relative)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false,
			"error": "[content] cannot read file: %s" % relative}
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	var parse_error := parser.parse(text)
	if parse_error != OK:
		return {"ok": false,
			"error": "[content] invalid JSON in %s at line %d: %s"
			% [relative, parser.get_error_line(), parser.get_error_message()]}
	if typeof(parser.data) != TYPE_DICTIONARY:
		return {"ok": false,
			"error": "[content] %s is not a JSON object" % relative}
	return {"ok": true, "data": parser.data}


static func _is_int_like(value: Variant) -> bool:
	if typeof(value) == TYPE_INT:
		return true
	if typeof(value) == TYPE_FLOAT:
		var number := float(value)
		return is_finite(number) and absf(number - round(number)) < 0.000001
	return false


static func _is_sha256(value: String) -> bool:
	if value.length() != 64 or value.to_lower() != value:
		return false
	for i in value.length():
		var code := value.unicode_at(i)
		var is_hex := (code >= 48 and code <= 57) or (code >= 97 and code <= 102)
		if not is_hex:
			return false
	return true
