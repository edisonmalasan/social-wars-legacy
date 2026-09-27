extends "res://tests/test_base.gd"
## Asset-ID registry suite (OpenSpec task 2.3, spec: "Client asset
## resolution", and the client-side half of "Deterministic asset ID
## registry").
##
## Proves, against the committed `tools/asset-registry/asset_ids.json`:
##   * resolution before any load reports an explicit not-loaded error;
##   * the registry loads with the exact four kinds and their distinct
##     reference counts, and every kind's per-status counts sum to its
##     distinct count over the closed vocabulary;
##   * a converted sprite resolves to its package directory on disk;
##   * a passthrough sound resolves to a source MP3 whose bytes match its
##     recorded SHA-256;
##   * a known-but-unavailable reference reports its status with no runtime
##     path, while an unknown kind or absent reference reports an error;
##   * the committed registry file is byte-identical after the run.
##
## Runs headless as part of `verify.ps1`.

const RegistryScript = preload("res://scripts/content_registry.gd")
const ASSET_FILE := "tools/asset-registry/asset_ids.json"
## distinct-reference counts per kind (coverage-derived facts).
const EXPECTED_DISTINCT := {
	"images": 607,
	"item_sprites": 872,
	"magic_sprites": 10,
	"sounds": 138,
}
## pinned coverage-derived per-status counts (spec reconciliation scenarios).
const EXPECTED_STATUS := {
	"item_sprites": {"converted": 2, "missing_source": 10},
	"magic_sprites": {"missing_source": 0},
	"sounds": {"missing_source": 0},
	"images": {"missing_source": 32, "ambiguous": 50},
}


func run_scenario() -> void:
	var registry: Variant = root.get_node_or_null("ContentRegistry")
	check(registry != null, "ContentRegistry autoload is registered")
	if registry == null:
		return

	var asset_path := Paths.repo_root().path_join(ASSET_FILE)
	var before := Paths.file_sha256(asset_path)
	check(before != "", "the committed asset ID registry is readable")

	# Resolution before any load is an explicit error, not a crash.
	var cold: Dictionary = registry.resolve_asset("sounds", "explo1")
	check_eq(bool(cold.get("found", true)), false,
		"resolution before load reports not-found")
	check(str(cold.get("error", "")).contains("not loaded"),
		"the pre-load error says the registry is not loaded (got: %s)"
		% str(cold.get("error", "")))

	var loaded: Dictionary = registry.load_asset_registry()
	check_eq(bool(loaded.get("ok", false)), true,
		"the committed asset ID registry loads (error: %s)"
		% str(loaded.get("error", "")))
	if not bool(loaded.get("ok", false)):
		return
	check(registry.assets_loaded(), "the registry reports loaded")

	var counts: Dictionary = registry.asset_status_counts()
	for kind in EXPECTED_DISTINCT:
		check(counts.has(kind), "kind %s is present" % kind)
		if not counts.has(kind):
			continue
		var status_counts: Dictionary = counts[kind]
		var total := 0
		for status in status_counts:
			check(RegistryScript.ASSET_STATUSES.has(status),
				"status %s of %s is in the closed vocabulary"
				% [status, kind])
			total += int(status_counts[status])
		check_eq(total, EXPECTED_DISTINCT[kind],
			"%s per-status counts sum to its distinct count" % kind)
		for status in EXPECTED_STATUS.get(kind, {}):
			check_eq(int(status_counts.get(status, 0)),
				int(EXPECTED_STATUS[kind][status]),
				"%s status %s matches the coverage-derived count"
				% [kind, status])

	_check_converted(registry)
	_check_passthrough(registry, asset_path)
	_check_unavailable(registry, asset_path)
	_check_unknown(registry)

	var after := Paths.file_sha256(asset_path)
	check_eq(after, before,
		"the committed asset ID registry is byte-identical after the run")
	info("asset ID registry digest %s" % after)


# ---------------------------------------------------------------------------
# Spec scenarios
# ---------------------------------------------------------------------------

func _check_converted(registry: Variant) -> void:
	# Spec scenario "Resolve a converted sprite".
	var converted: Dictionary = registry.resolve_asset(
		"item_sprites", "0001_house_1_m")
	check_eq(bool(converted.get("found", false)), true,
		"item sprite 0001_house_1_m is known")
	if not bool(converted.get("found", false)):
		return
	var entry: Dictionary = converted["entry"]
	check_eq(str(entry.get("status", "")), "converted",
		"0001_house_1_m is converted")
	var runtime := str(entry.get("runtime", ""))
	check(runtime.contains("0001_house_1_m"),
		"the runtime path names the converted package (%s)" % runtime)
	check(DirAccess.dir_exists_absolute(Paths.repo_root().path_join(runtime)),
		"the converted package directory exists on disk")


func _check_passthrough(registry: Variant, asset_path: String) -> void:
	# Spec scenario "Resolve a passthrough sound" — the reference is derived
	# from the committed registry so the scenario survives ref-form choices.
	var ref := _first_ref_with_status(asset_path, "sounds", "passthrough")
	if ref == "":
		fail("the registry has at least one passthrough sound")
		return
	var resolved: Dictionary = registry.resolve_asset("sounds", ref)
	check_eq(bool(resolved.get("found", false)), true,
		"sound %s is known" % ref)
	if not bool(resolved.get("found", false)):
		return
	var entry: Dictionary = resolved["entry"]
	check_eq(str(entry.get("status", "")), "passthrough",
		"sound %s is passthrough" % ref)
	var runtime := str(entry.get("runtime", ""))
	check(runtime.ends_with(".mp3"),
		"the runtime path is a source MP3 (%s)" % runtime)
	check(FileAccess.file_exists(Paths.repo_root().path_join(runtime)),
		"the source MP3 exists on disk")
	var source := str(entry.get("source", ""))
	check_eq(source, runtime,
		"the passthrough source path equals its runtime path")
	var recorded := str(entry.get("source_sha256", ""))
	check_eq(recorded.length(), 64,
		"the passthrough entry records a source SHA-256")
	if recorded.length() == 64 and runtime != "":
		check_eq(Paths.file_sha256(Paths.repo_root().path_join(runtime)),
			recorded,
			"the source MP3 bytes match the recorded SHA-256")


func _check_unavailable(registry: Variant, asset_path: String) -> void:
	# Spec scenario "Distinguish unavailable from unknown" — the known half.
	var ref := _first_ref_with_status(asset_path, "item_sprites",
		"missing_source")
	if ref == "":
		fail("the registry has at least one missing_source item sprite")
		return
	var missing: Dictionary = registry.resolve_asset("item_sprites", ref)
	check_eq(bool(missing.get("found", false)), true,
		"missing sprite %s is known to the registry" % ref)
	if not bool(missing.get("found", false)):
		return
	var entry: Dictionary = missing["entry"]
	check_eq(str(entry.get("status", "")), "missing_source",
		"missing sprite %s reports missing_source" % ref)
	var runtime: Variant = entry.get("runtime", null)
	check(runtime == null or str(runtime) == "",
		"a missing_source entry claims no runtime path")


func _check_unknown(registry: Variant) -> void:
	# Spec scenario "Distinguish unavailable from unknown" — the unknown half.
	var bad_kind: Dictionary = registry.resolve_asset("music", "anything")
	check_eq(bool(bad_kind.get("found", true)), false,
		"an unknown asset kind reports an error")
	check(str(bad_kind.get("error", "")).contains("unknown asset kind"),
		"the unknown-kind error names the problem (got: %s)"
		% str(bad_kind.get("error", "")))

	var bad_ref: Dictionary = registry.resolve_asset("sounds",
		"no_such_reference_xyz")
	check_eq(bool(bad_ref.get("found", true)), false,
		"an absent reference reports an error")
	check(str(bad_ref.get("error", "")).contains("no sounds asset reference"),
		"the absent-reference error names kind and ref (got: %s)"
		% str(bad_ref.get("error", "")))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

## Returns the first `ref` of `kind` carrying `status` by reading the
## committed registry directly (the registry itself is write-only here).
func _first_ref_with_status(asset_path: String, kind: String,
		status: String) -> String:
	var data: Variant = _read_json(asset_path)
	if typeof(data) != TYPE_DICTIONARY \
			or typeof((data as Dictionary).get("kinds")) != TYPE_ARRAY:
		return ""
	for block_v in (data as Dictionary)["kinds"]:
		if typeof(block_v) != TYPE_DICTIONARY \
				or str((block_v as Dictionary).get("kind", "")) != kind:
			continue
		var entries_v: Variant = (block_v as Dictionary).get("entries")
		if typeof(entries_v) != TYPE_ARRAY:
			return ""
		for entry_v in entries_v:
			if typeof(entry_v) == TYPE_DICTIONARY \
					and str((entry_v as Dictionary).get("status", "")) \
						== status:
				return str((entry_v as Dictionary).get("ref", ""))
	return ""


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
