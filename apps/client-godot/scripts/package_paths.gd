extends RefCounted
## Repository path resolution and the canonical read-only directory digest.
##
## Package sources live outside the Godot project (assets/converted/... at the
## repository root), so they are read at runtime through globalized paths and
## are never imported as Godot resources. Nothing in this project writes into
## the repository sources; SHA-256 directory digests are taken before and after
## every verification run to prove byte identity (design D9).

## Package directories consumed read-only, repository-relative POSIX paths.
const PACKAGE_DIRS := [
	"assets/converted/buildings/0001_house_1_m",
	"assets/converted/units/10033_wild_elephant",
]

## Manifests guarded alongside the packages by verify.ps1 (task 4.4).
const MANIFEST_FILES := [
	"tools/asset-registry/conversions.json",
	"tools/asset-registry/inspection.json",
	"tools/asset-registry/image_extraction.json",
]

## The Godot project directory as an absolute, forward-slash path.
static func project_dir() -> String:
	var raw := ProjectSettings.globalize_path("res://")
	return raw.replace("\\", "/").trim_suffix("/")

## The repository root (two levels above apps/client-godot).
static func repo_root() -> String:
	return project_dir().path_join("../..").simplify_path()

## Absolute package directory for a repository-relative package path.
static func package_dir(repo_relative: String) -> String:
	return repo_root().path_join(repo_relative)

## Absolute package.json path for a repository-relative package path.
static func package_json(repo_relative: String) -> String:
	return package_dir(repo_relative).path_join("package.json")

## Absolute path of the committed capture evidence.
static func capture_png_path() -> String:
	return project_dir().path_join("evidence/first-render/first-render.png")

## Absolute path of the committed comparison report evidence.
static func report_path() -> String:
	return project_dir().path_join("evidence/first-render/report.json")

## SHA-256 of a byte buffer as lowercase hex.
static func sha256_hex(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	context.update(data)
	return context.finish().hex_encode()

## SHA-256 of a file's bytes as lowercase hex; empty string when unreadable.
static func file_sha256(path: String) -> String:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return ""
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return sha256_hex(bytes)

## SHA-256 of a file's bytes as lowercase hex, or the failure reason.
static func file_sha256_checked(path: String) -> Dictionary:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false, "error": "cannot read file: " + path}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return {"ok": true, "sha256": sha256_hex(bytes), "bytes": bytes.size()}

## Canonical directory digest.
##
## For every file under `dir_path` (recursively), a line
## "<file sha256 hex>  <relative posix path>\n" is hashed in ascending
## ordinal order of the relative path. The result is the SHA-256 of the
## concatenated UTF-8 lines. The same algorithm is implemented in
## verify.ps1; verify.ps1 asserts both implementations agree.
static func directory_digest(dir_path: String) -> Dictionary:
	var relative_paths: PackedStringArray = []
	var collect_error := _collect_files(dir_path, "", relative_paths)
	if collect_error != "":
		return {"ok": false, "error": collect_error}
	var sorted_paths: Array = Array(relative_paths)
	sorted_paths.sort()
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return {"ok": false, "error": "cannot start sha256: " + dir_path}
	for relative in sorted_paths:
		var absolute: String = dir_path.path_join(str(relative))
		var file_digest := file_sha256(absolute)
		if file_digest == "":
			return {"ok": false, "error": "cannot hash file: " + absolute}
		var line := "%s  %s\n" % [file_digest, str(relative)]
		context.update(line.to_utf8_buffer())
	return {
		"ok": true,
		"sha256": context.finish().hex_encode(),
		"files": sorted_paths.size(),
	}

static func _collect_files(dir_path: String, prefix: String,
		out: PackedStringArray) -> String:
	var directory := DirAccess.open(dir_path)
	if directory == null:
		return "cannot open directory: " + dir_path
	directory.list_dir_begin()
	var entry := directory.get_next()
	while entry != "":
		if entry == "." or entry == "..":
			entry = directory.get_next()
			continue
		var full := dir_path.path_join(entry)
		if directory.current_is_dir():
			var sub_error := _collect_files(full,
				prefix + entry + "/", out)
			if sub_error != "":
				return sub_error
		else:
			out.append(prefix + entry)
		entry = directory.get_next()
	directory.list_dir_end()
	return ""
