extends RefCounted
## Report assembly and deterministic JSON writing.
##
## The report is the committed evidence for the comparison. It contains no
## timestamps: rerunning the verification on the same machine and engine
## produces the same metrics, so a clean working tree stays clean (design
## D8). Engine/renderer/video-adapter strings are recorded for provenance
## and are the only fields the reproducibility check excludes.

const Paths = preload("res://scripts/package_paths.gd")

## Report schema identifier recorded in every file this module writes.
const SCHEMA := "first-render-in-godot/report/v1"

## Entry point that produced the report.
const GENERATED_BY := "apps/client-godot/scripts/verification.gd"


## Builds the report dictionary.
##
## `mode` is "capture" (written by the rendering run), "compare" (written by
## the headless comparison of the committed capture) or "self-test" (written
## by the deliberately perturbed comparator self-test).
static func build(mode: String, capture_path: String,
		reference: Dictionary, comparison: Dictionary,
		tolerance: Dictionary) -> Dictionary:
	var capture_image := Image.new()
	var capture_error := capture_image.load(capture_path)
	var capture_block := {}
	if capture_error == OK:
		capture_block = {
			"path": _repo_relative(capture_path),
			"sha256": Paths.file_sha256(capture_path),
			"width": capture_image.get_width(),
			"height": capture_image.get_height(),
			"format": _format_name(capture_image.get_format()),
		}
	else:
		capture_block = {
			"path": _repo_relative(capture_path),
			"sha256": "",
			"width": 0,
			"height": 0,
			"format": "",
		}

	var version := Engine.get_version_info()
	var engine_block := {
		"version": str(version.get("string", "")),
		"godot": "%s.%s.%s" % [version.get("major", 0),
			version.get("minor", 0), version.get("patch", 0)],
		"hash": str(version.get("hash", "")),
		"renderer": RenderingServer.get_current_rendering_driver_name(),
		"video_adapter": RenderingServer.get_video_adapter_name(),
		"video_adapter_api":
			RenderingServer.get_video_adapter_api_version(),
	}

	var report := {
		"schema": SCHEMA,
		"mode": mode,
		"generated_by": GENERATED_BY,
		"engine": engine_block,
		"capture": capture_block,
		"reference": {
			"builder": str(reference.get("builder", "")),
			"width": reference["image"].get_width(),
			"height": reference["image"].get_height(),
			"perturbed": bool(reference.get("perturbed", false)),
		},
		"inputs": _input_digests(),
		"entities": _entity_blocks(reference),
		"tolerance": tolerance,
		"metrics": comparison.get("metrics", {}),
		"result": {
			"pass": bool(comparison.get("pass", false)),
			"failures": comparison.get("failures", []),
		},
	}
	if comparison.has("error"):
		report["result"] = {"pass": false,
			"failures": [str(comparison["error"])]}
	return report


## Writes the report as pretty JSON with a trailing newline.
static func write(path: String, report: Dictionary) -> Dictionary:
	var directory := path.get_base_dir()
	var make_error := DirAccess.make_dir_recursive_absolute(directory)
	if make_error != OK and not DirAccess.dir_exists_absolute(directory):
		return {"ok": false,
			"error": "cannot create report directory: " + directory}
	var body := JSON.stringify(report, "  ", true, true) + "\n"
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		return {"ok": false, "error": "cannot write report: " + path}
	handle.store_string(body)
	handle = null
	return {"ok": true, "path": path, "bytes": body.to_utf8_buffer().size()}


## SHA-256 directory digests of both packages plus the guarded manifests.
static func _input_digests() -> Dictionary:
	var packages: Array = []
	for package_dir in Paths.PACKAGE_DIRS:
		var digest := Paths.directory_digest(Paths.package_dir(
			str(package_dir)))
		packages.append({
			"dir": str(package_dir),
			"files": int(digest.get("files", 0)),
			"directory_sha256": str(digest.get("sha256", "")),
		})
	var manifests: Array = []
	for manifest in Paths.MANIFEST_FILES:
		manifests.append({
			"path": str(manifest),
			"sha256": Paths.file_sha256(
				Paths.repo_root().path_join(str(manifest))),
		})
	return {"packages": packages, "manifests": manifests}


static func _entity_blocks(reference: Dictionary) -> Array:
	var blocks: Array = []
	for entity in reference.get("entities", []):
		var shapes: Array = []
		for shape in entity["shapes"]:
			shapes.append({
				"character_id": int(shape["character_id"]),
				"bitmap_id": int(shape["bitmap_id"]),
				"anchor": _vector(shape["anchor"]),
				"size": _vector(shape["size"]),
				"jpg_sha256": str(shape["jpg_sha256"]),
				"alpha_sha256": str(shape["alpha_sha256"]),
				"oracle": _oracle(shape["oracle"]),
			})
		blocks.append({
			"label": str(entity["label"]),
			"kind": str(entity["kind"]),
			"legacy_id": str(entity["legacy_id"]),
			"anchor": _vector(entity["anchor"]),
			"size_px": _vector(entity["size_px"]),
			"oracle_ok": bool(entity["oracle_ok"]),
			"shapes": shapes,
		})
	return blocks


static func _oracle(oracle: Dictionary) -> Dictionary:
	return {
		"ok": bool(oracle["ok"]),
		"mapped_px": _vector(oracle["mapped_px"]),
		"bitmap_px": _vector(oracle["bitmap_px"]),
		"error_px": _vector(oracle["error_px"]),
	}


## JSON-friendly {x, y} record; accepts Vector2 and Vector2i.
static func _vector(value: Variant) -> Dictionary:
	return {"x": round(float(value.x) * 1000.0) / 1000.0,
		"y": round(float(value.y) * 1000.0) / 1000.0}


static func _repo_relative(path: String) -> String:
	var normalized := path.replace("\\", "/")
	var root := Paths.repo_root()
	if normalized.begins_with(root):
		return normalized.trim_prefix(root).trim_prefix("/")
	return normalized


static func _format_name(format: Image.Format) -> String:
	match format:
		Image.FORMAT_RGBA8:
			return "RGBA8"
		Image.FORMAT_RGB8:
			return "RGB8"
		Image.FORMAT_RGBA4444:
			return "RGBA4444"
		_:
			return str(format)
