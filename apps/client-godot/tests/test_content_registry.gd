extends "res://tests/test_base.gd"
## Content-registry suite (OpenSpec tasks 2.1 / 2.2, spec: "Canonical
## content registry loading" + "Domain indexing and lookup").
##
## Proves, against the committed package:
##   * no implicit load happens at scene start (explicit-load contract);
##   * four fault classes fail closed with an error naming the offender,
##     each injected into a mutated COPY under `.godot/` (never the source);
##   * the default load verifies all 23 manifest outputs (byte count +
##     SHA-256 before parse) and indexes them by `legacy_id`;
##   * lookups return exact stored entries or explicit not-found results;
##   * the public id enumeration reports the committed index order (not a
##     collation of the digit strings), agrees with `count()`, and reports an
##     unknown domain as not-found;
##   * the content package's directory digest is identical before and after.
##
## Runs headless as part of `verify.ps1`.

const SCRATCH := ".godot/verify/content"
const EXPECTED_COUNTS := {
	"buildings": 470,
	"units": 429,
	"quests": 91,
	"images": 607,
	"sounds": 139,
	"globals": 105,
	"auctions": 3,
}
## The first `legacy_id` of each enumerated domain in the **committed index
## order** — the order the committed file lists its rows, not a collation of the
## identifier strings. `units` is the discriminating case: its committed first id
## is `923`, while a lexicographic sort of the same digit strings would begin
## `1001`, so the two orders are unambiguous.
const FIRST_ID := {
	"buildings": "1",
	"units": "923",
	"levels": "0",
	"sounds": "1",
}
## The manifest-verified entry totals of the four domains this suite enumerates.
## `levels` is not in `EXPECTED_COUNTS` (which covers the domains the other
## checks walk), so the enumeration carries its own committed totals rather than
## borrowing a table that does not list every enumerated domain.
const ENUMERATED_COUNTS := {
	"buildings": 470,
	"units": 429,
	"levels": 100,
	"sounds": 139,
}


func run_scenario() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return
	check(not registry.is_loaded(),
		"the registry performs no implicit load at startup")

	var package_dir := Paths.repo_root().path_join("packages/game-content")
	var before := Paths.directory_digest(package_dir)
	check(bool(before.get("ok", false)),
		"content package digest is readable before the run (%s)"
		% str(before.get("error", "")))
	if not bool(before.get("ok", false)):
		return

	_check_faults(registry, package_dir)
	check(not registry.is_loaded(),
		"failed loads never mark the registry loaded")

	_check_default_load(registry, package_dir)
	_check_lookups(registry, package_dir)
	_check_enumeration(registry, package_dir)

	var after := Paths.directory_digest(package_dir)
	check_eq(after.get("sha256", ""), before.get("sha256", ""),
		"content package bytes are unchanged after the run")
	check_eq(after.get("files", 0), before.get("files", 0),
		"content package file count is unchanged after the run")
	info("content package digest %s over %s files"
		% [str(before.get("sha256", "?")), str(before.get("files", "?"))])


# ---------------------------------------------------------------------------
# Fault scenarios (mutated copy under `.godot/`, sources untouched)
# ---------------------------------------------------------------------------

func _check_faults(registry: Variant, package_dir: String) -> void:
	var copy_root := _build_copy(package_dir)
	if copy_root == "":
		fail("cannot build the mutated content copy under " + SCRATCH)
		return

	# Fault A: same-length byte alteration -> byte count passes, SHA-256 fails.
	var buildings := copy_root + "/packages/game-content/normalized/buildings.json"
	var altered := _read_bytes(buildings)
	check(altered.size() > 0, "copied buildings.json is readable")
	if altered.size() > 0:
		altered[0] = altered[0] ^ 1  # same length, different bytes
		_write_bytes(buildings, altered)
		var result: Dictionary = registry.load_content(
			_copy_repo_root(copy_root))
		check_eq(bool(result.get("ok", true)), false,
			"an altered output is rejected")
		check(str(result.get("error", "")).contains("buildings.json"),
			"the alteration error names buildings.json (got: %s)"
			% str(result.get("error", "")))
		check(str(result.get("error", "")).contains("sha256"),
			"the alteration error reports the SHA-256 mismatch")
	_restore(package_dir, copy_root, "normalized/buildings.json")

	# Fault B: missing output -> read failure names the file.
	DirAccess.remove_absolute(copy_root
		+ "/packages/game-content/normalized/quests.json")
	var missing: Dictionary = registry.load_content(_copy_repo_root(copy_root))
	check_eq(bool(missing.get("ok", true)), false,
		"a missing output is rejected")
	check(str(missing.get("error", "")).contains("quests.json"),
		"the missing-file error names quests.json (got: %s)"
		% str(missing.get("error", "")))
	_restore(package_dir, copy_root, "normalized/quests.json")

	# Fault D: unparseable output -> parse failure names the file. The
	# manifest entry is re-pointed at the broken bytes so byte-count and
	# SHA-256 verification PASS and the parse layer is what fails; both the
	# file and the manifest record are restored so later faults start from
	# a pristine copy.
	var sounds_path := copy_root \
		+ "/packages/game-content/normalized/sounds.json"
	var broken := "{ this is not json".to_utf8_buffer()
	_write_bytes(sounds_path, broken)
	check(_repoint_manifest(copy_root, "sounds.json",
			broken.size(), Paths.sha256_hex(broken)),
		"the copy's manifest entry is re-pointed at the broken bytes")
	var unparseable: Dictionary = registry.load_content(
		_copy_repo_root(copy_root))
	check_eq(bool(unparseable.get("ok", true)), false,
		"an unparseable output is rejected")
	check(str(unparseable.get("error", "")).contains("sounds.json"),
		"the parse error names sounds.json (got: %s)"
		% str(unparseable.get("error", "")))
	check(str(unparseable.get("error", "")).contains("invalid JSON"),
		"the parse error says the file is invalid JSON (got: %s)"
		% str(unparseable.get("error", "")))
	check(not unparseable.has("counts"),
		"no partial package is served from the damaged copy")
	_restore(package_dir, copy_root, "normalized/sounds.json")
	_restore(package_dir, copy_root, "manifest.json")

	# Fault C: duplicate legacy_id inside one domain -> rejected by name.
	# The manifest entry is re-pointed at the mutated bytes so byte-count and
	# SHA-256 verification PASS and the duplicate-index layer is what fails.
	var categories_path := copy_root \
		+ "/packages/game-content/normalized/categories.json"
	var categories: Variant = _read_json(categories_path)
	if typeof(categories) == TYPE_ARRAY and (categories as Array).size() > 0:
		(categories as Array).append((categories as Array)[0])
		var mutated := JSON.stringify(categories).to_utf8_buffer()
		_write_bytes(categories_path, mutated)
		check(_repoint_manifest(copy_root, "categories.json",
				mutated.size(), Paths.sha256_hex(mutated)),
			"the copy's manifest entry is re-pointed at the mutated bytes")
		var duplicate: Dictionary = registry.load_content(
			_copy_repo_root(copy_root))
		check_eq(bool(duplicate.get("ok", true)), false,
			"a duplicate legacy_id is rejected")
		check(str(duplicate.get("error", "")).contains("categories"),
			"the duplicate error names the domain (got: %s)"
			% str(duplicate.get("error", "")))
		check(str(duplicate.get("error", "")).contains("duplicate"),
			"the duplicate error says what was duplicated")
	else:
		fail("copied categories.json is a readable array")


# ---------------------------------------------------------------------------
# Default load and lookups
# ---------------------------------------------------------------------------

func _check_default_load(registry: Variant, package_dir: String) -> void:
	var result: Dictionary = registry.load_content()
	check_eq(bool(result.get("ok", false)), true,
		"the committed package loads (error: %s)"
		% str(result.get("error", "")))
	if not bool(result.get("ok", false)):
		return
	check_eq(int(result.get("files_verified", 0)), 23,
		"all 23 manifest outputs are verified")
	check(int(result.get("bytes_verified", 0)) > 1000000,
		"verification covers the package bytes (%s)"
		% str(result.get("bytes_verified", 0)))
	check(registry.is_loaded(), "the registry reports loaded")

	for domain in EXPECTED_COUNTS:
		check_eq(registry.count(domain), EXPECTED_COUNTS[domain],
			"count(%s) matches the manifest-verified entries" % domain)
	var domain_list: Array = registry.domains_list()
	check_eq(domain_list.size(), 23, "all 23 domains are indexed")
	check(registry.has_domain("buildings"), "has_domain finds buildings")
	check(not registry.has_domain("nope"), "has_domain rejects an unknown name")
	check_eq(registry.count("nope"), -1,
		"count() reports -1 for an unknown domain, not 0")

	var sections: Dictionary = registry.sections()
	check_eq(sections.size(), 11,
		"the manifest's 11 sections are reported")
	check_eq(sections.get("root", []), ["buildings", "units", "specials"],
		"the root section contributes its three item domains")
	var covered: Array = []
	for section in sections:
		for domain in sections[section]:
			covered.append(domain)
	covered.sort()
	check_eq(covered, domain_list,
		"every indexed domain belongs to a manifest section")

	var manifest: Variant = _read_json(package_dir + "/manifest.json")
	if typeof(manifest) == TYPE_DICTIONARY:
		check_eq(registry.content_fingerprint(),
			str((manifest as Dictionary).get("content_fingerprint", "")),
			"the exposed content fingerprint equals the manifest's own")
		check_eq(registry.content_fingerprint().length(), 64,
			"the content fingerprint is a SHA-256 digest")
	else:
		fail("the committed manifest.json is readable for comparison")


func _check_lookups(registry: Variant, package_dir: String) -> void:
	# A stored entry round-trips exactly (self-derived identifier).
	var quests: Variant = _read_json(package_dir + "/normalized/quests.json")
	if typeof(quests) == TYPE_ARRAY and (quests as Array).size() > 0:
		var first: Dictionary = (quests as Array)[0]
		var id := str(first["legacy_id"])
		var found: Dictionary = registry.get_entry("quests", id)
		check_eq(bool(found.get("found", false)), true,
			"quest %s is found" % id)
		check_eq(JSON.stringify(found.get("entry", {})),
			JSON.stringify(first),
			"the stored quest entry equals the file entry exactly")
	else:
		fail("quests.json is a readable non-empty array")

	# A hardcoded known building resolves to its exact stored entry.
	var building_file: Variant = _read_json(
		package_dir + "/normalized/buildings.json")
	var building: Dictionary = registry.get_entry("buildings", "1")
	check_eq(bool(building.get("found", false)), true,
		"building legacy_id 1 is found")
	if typeof(building_file) == TYPE_ARRAY and (building_file as Array).size() > 0:
		var stored: Variant = null
		for item_v in building_file as Array:
			if typeof(item_v) == TYPE_DICTIONARY \
					and str((item_v as Dictionary).get("legacy_id", "")) == "1":
				stored = item_v
				break
		check(stored != null, "buildings.json stores an entry with legacy_id 1")
		if stored != null and bool(building.get("found", false)):
			check_eq(JSON.stringify(building.get("entry", {})),
				JSON.stringify(stored),
				"the stored building entry equals the file entry exactly")
	else:
		fail("buildings.json is a readable non-empty array")

	# A stored sound resolves by its stored legacy_id (spec scenario
	# "Look up known definitions" names a building, a quest, and a sound).
	var sounds_file: Variant = _read_json(package_dir + "/normalized/sounds.json")
	if typeof(sounds_file) == TYPE_ARRAY and (sounds_file as Array).size() > 0:
		var sound: Dictionary = (sounds_file as Array)[0]
		var sound_id := str(sound["legacy_id"])
		var sound_found: Dictionary = registry.get_entry("sounds", sound_id)
		check_eq(bool(sound_found.get("found", false)), true,
			"sound %s is found" % sound_id)
		check_eq(JSON.stringify(sound_found.get("entry", {})),
			JSON.stringify(sound),
			"the stored sound entry equals the file entry exactly")
	else:
		fail("sounds.json is a readable non-empty array")

	# Explicit not-found results (never null or guessed values).
	var no_entry: Dictionary = registry.get_entry("buildings", "no_such_id")
	check_eq(bool(no_entry.get("found", true)), false,
		"an unknown legacy_id reports not-found")
	check(str(no_entry.get("error", "")).contains("no entry"),
		"the not-found error says the entry is absent")
	var absent: Variant = no_entry.get("entry", null)
	check(absent != null and typeof(absent) == TYPE_DICTIONARY
		and (absent as Dictionary).is_empty(),
		"the not-found result carries no entry")

	var no_domain: Dictionary = registry.get_entry("no_such_domain", "1")
	check_eq(bool(no_domain.get("found", true)), false,
		"an unknown domain reports not-found")
	check(str(no_domain.get("error", "")).contains("unknown domain"),
		"the unknown-domain error says the domain is absent")


## The public id enumeration this change added (spec "Domain indexing and
## lookup"): a consumer enumerates the **verified** index instead of re-reading
## the committed file, so the count agrees with `count()`, the order is the
## committed index order rather than a collation of the digit strings, every id
## resolves through `get_entry`, and an unknown domain reports not-found with an
## empty list rather than a guessed empty enumeration.
func _check_enumeration(registry: Variant, package_dir: String) -> void:
	if registry == null or not registry.is_loaded():
		return
	for domain: String in ["buildings", "units", "levels", "sounds"]:
		var result: Dictionary = registry.legacy_ids(domain)
		check_eq(bool(result.get("found", false)), true,
			"legacy_ids(%s) resolves a loaded domain" % domain)
		var ids: Variant = result.get("ids")
		check(ids is Array, "legacy_ids(%s) returns an array" % domain)
		if not (ids is Array):
			continue
		var listed: Array = ids
		check_eq(listed.size(), registry.count(domain),
			"legacy_ids(%s) count agrees with count()" % domain)
		check_eq(listed.size(), ENUMERATED_COUNTS[domain],
			"legacy_ids(%s) matches the manifest-verified entry total" % domain)
		# The committed index order, not a lexicographic sort of the digit
		# strings: the first id of `units` is the file's first row, and a
		# collation would interleave ids ("1001" before "923").
		check_eq(str(listed[0]), FIRST_ID[domain],
			"legacy_ids(%s) reports the committed index order, not a collation"
			% domain)
		var distinct := {}
		for legacy_id: Variant in listed:
			distinct[str(legacy_id)] = true
		check_eq(distinct.size(), listed.size(),
			"legacy_ids(%s) yields only distinct ids" % domain)
		# Every enumerated id resolves through the public lookup.
		var resolves := true
		for legacy_id: Variant in listed:
			var found: Dictionary = registry.get_entry(domain, str(legacy_id))
			if not bool(found.get("found", false)):
				resolves = false
				break
		check(resolves, "every legacy_ids(%s) entry resolves via get_entry" % domain)
		check(str(result.get("file", "")).ends_with(".json"),
			"legacy_ids(%s) names the verified output file" % domain)

	var absent: Dictionary = registry.legacy_ids("no_such_domain")
	check_eq(bool(absent.get("found", true)), false,
		"legacy_ids() reports not-found for an unknown domain, not an empty list")
	check(str(absent.get("error", "")).contains("unknown domain"),
		"the unknown-domain enumeration error says the domain is absent")
	var absent_ids: Variant = absent.get("ids")
	check(absent_ids is Array and (absent_ids as Array).is_empty(),
		"the not-found enumeration carries an empty id list")


# ---------------------------------------------------------------------------
# Scratch-copy helpers (mutated copies live under `.godot/`, never in sources)
# ---------------------------------------------------------------------------

## Copies manifest + normalized outputs into `.godot/verify/content/` and
## returns the absolute path of the scratch package root's parent (the
## substitute repo root containing `packages/game-content/`).
func _build_copy(package_dir: String) -> String:
	var copy_repo := Paths.project_dir().path_join(SCRATCH)
	var copy_pkg := copy_repo.path_join("packages/game-content")
	DirAccess.make_dir_recursive_absolute(copy_pkg + "/normalized")
	if not _copy_file(package_dir + "/manifest.json",
			copy_pkg + "/manifest.json"):
		return ""
	var source := DirAccess.open(package_dir + "/normalized")
	if source == null:
		return ""
	source.list_dir_begin()
	var entry := source.get_next()
	while entry != "":
		if not source.current_is_dir() and entry != "":
			if not _copy_file(package_dir + "/normalized/" + entry,
					copy_pkg + "/normalized/" + entry):
				source.list_dir_end()
				return ""
		entry = source.get_next()
	source.list_dir_end()
	return copy_repo


func _copy_repo_root(copy_repo: String) -> String:
	return copy_repo


func _restore(package_dir: String, copy_repo: String,
		relative: String) -> bool:
	return _copy_file(package_dir + "/" + relative,
		copy_repo + "/packages/game-content/" + relative)


## Rewrites the copy's manifest output record for `normalized/<file>` to the
## given byte count and SHA-256, so the mutated copy still passes manifest
## verification and a deeper layer (duplicate indexing) is what fails.
func _repoint_manifest(copy_repo: String, file: String, bytes: int,
		digest: String) -> bool:
	var manifest_path := copy_repo \
		+ "/packages/game-content/manifest.json"
	var manifest: Variant = _read_json(manifest_path)
	if typeof(manifest) != TYPE_DICTIONARY:
		return false
	var relative := "packages/game-content/normalized/" + file
	for section in (manifest as Dictionary):
		var outputs: Variant = null
		if section == "outputs":
			outputs = (manifest as Dictionary)[section]
		elif typeof((manifest as Dictionary)[section]) == TYPE_DICTIONARY:
			outputs = ((manifest as Dictionary)[section] as Dictionary) \
				.get("outputs")
		if typeof(outputs) != TYPE_ARRAY:
			continue
		for record_v in outputs:
			if typeof(record_v) != TYPE_DICTIONARY:
				continue
			if str((record_v as Dictionary).get("file", "")) != relative:
				continue
			(record_v as Dictionary)["bytes"] = bytes
			(record_v as Dictionary)["sha256"] = digest
			return _write_bytes(manifest_path,
				JSON.stringify(manifest).to_utf8_buffer())
	return false


func _copy_file(from_path: String, to_path: String) -> bool:
	var bytes := _read_bytes(from_path)
	if bytes.is_empty():
		return false
	return _write_bytes(to_path, bytes)


func _read_bytes(path: String) -> PackedByteArray:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return PackedByteArray()
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return bytes


func _write_bytes(path: String, bytes: PackedByteArray) -> bool:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		return false
	handle.store_buffer(bytes)
	handle.close()
	return true


func _read_json(path: String) -> Variant:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return null
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	if parser.parse(text) != OK:
		return null
	return parser.data
