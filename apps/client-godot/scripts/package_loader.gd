extends RefCounted
## Fail-closed loader for the two conversion-v1 packages (read-only).
##
## The loader validates the package envelope against the recorded conversion
## contracts (`kind` dispatch, exact top-level field sets), walks frame-1
## placements down to shapes, selects fills only through `fill_refs` (1-based,
## skipping the unreferenced 65535 placeholder fills), decodes the raw SWF
## fill matrices, resolves the referenced JPEG + alpha-PNG bitmap files, and
## composites them into straight-alpha Godot images.
##
## Every failure returns an explicit error string that names the package; no
## partial or guessed output is ever produced.

const Paths = preload("res://scripts/package_paths.gd")

const KIND_BUILDING := "converted_building"
const KIND_UNIT := "converted_unit"

const BUILDING_FIELDS := [
	"legacy_id", "kind", "source_file", "source_layer", "content_version",
	"content_ref", "frame_width", "frame_height", "frame_rate",
	"frame_count", "symbols", "shapes", "bitmaps", "placement",
]
const UNIT_FIELDS := [
	"legacy_id", "kind", "source_file", "source_layer", "content_version",
	"content_ref", "frame_width", "frame_height", "frame_rate",
	"frame_count", "symbols", "main", "sprites", "shapes", "bitmaps",
]
const TIMELINE_FIELDS := ["frame_count", "labels", "placements", "removes"]
## Sprite timelines carry one extra field: their own `sprite_id`.
const SPRITE_TIMELINE_FIELDS := ["frame_count", "labels", "placements",
	"removes", "sprite_id"]
const PLACEMENT_FIELDS := ["frame", "depth", "character_id", "character_kind", "move"]
const LABEL_FIELDS := ["name", "frame", "anchor"]
const REMOVE_FIELDS := ["frame", "depth"]
const SHAPE_FIELDS_NO_REFS := ["character_id", "tag", "bounds", "fills",
	"lines", "records"]
const SHAPE_FIELDS_REFS := ["character_id", "tag", "bounds", "fills", "lines",
	"records", "fill_refs"]
const BOUNDS_FIELDS := ["xmin", "xmax", "ymin", "ymax", "width_px", "height_px"]
const RECORD_FIELDS := ["end", "style_change", "straight", "curved", "new_styles"]
const BITMAP_FILL_FIELDS := ["type", "bitmap_id", "matrix"]
const BITMAP_FIELDS := ["character_id", "file", "bytes", "sha256"]
const SYMBOL_FIELDS_UNIT := ["id", "name"]

## Bitmap fill style code (SWF FillStyle type 65: clipped bitmap).
const FILL_TYPE_BITMAP := 65
## Placeholder bitmap id used for unreferenced fill styles.
const PLACEHOLDER_BITMAP_ID := 65535

## Signed fixed-point scale divisor: raw matrix scale fields are read MSB-first
## (matching the converter bit reader) and interpreted as 16.16 fixed point.
## House oracle: raw 0x140000 / 65536 = 20.0 twips per bitmap pixel.
const MATRIX_SCALE_FIXED := 65536.0

## One pixel of slack for the bounds-to-bitmap oracle (spec R4).
const ORACLE_TOLERANCE_PX := 1.0


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------

## Reads and parses a package.json without validating it.
static func parse_package_json(package_dir: String) -> Dictionary:
	var path := Paths.package_json(package_dir)
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false,
			"error": "[%s] cannot open %s" % [package_dir, path]}
	var text := handle.get_as_text()
	handle = null
	var parser := JSON.new()
	var parse_error := parser.parse(text)
	if parse_error != OK:
		return {"ok": false, "error": "[%s] invalid JSON at line %d: %s"
			% [package_dir, parser.get_error_line(),
			parser.get_error_message()]}
	if typeof(parser.data) != TYPE_DICTIONARY:
		return {"ok": false,
			"error": "[%s] envelope is not a JSON object" % package_dir}
	return {"ok": true, "label": package_dir, "path": path, "data": parser.data}


## Validates one already-parsed envelope. Returns {"ok", "error", "kind"}.
static func validate_envelope(data: Variant, label: String) -> Dictionary:
	if typeof(data) != TYPE_DICTIONARY:
		return {"ok": false,
			"error": "[%s] envelope is not a JSON object" % label}
	var envelope: Dictionary = data
	if not envelope.has("kind") or typeof(envelope["kind"]) != TYPE_STRING:
		return {"ok": false, "error": "[%s] envelope field 'kind' missing"
			% label}
	var kind := str(envelope["kind"])
	if kind != KIND_BUILDING and kind != KIND_UNIT:
		return {"ok": false,
			"error": "[%s] unrecognized envelope kind: %s" % [label, kind]}
	var expected: Array = BUILDING_FIELDS if kind == KIND_BUILDING \
		else UNIT_FIELDS
	var key_error := _keys_exact(envelope, expected, label, "envelope")
	if key_error != "":
		return {"ok": false, "error": key_error}

	var legacy_id := _check_string(envelope, "legacy_id", label, "envelope")
	if legacy_id != "":
		return {"ok": false, "error": legacy_id}
	if str(envelope["legacy_id"]).is_empty():
		return {"ok": false,
			"error": "[%s] envelope field 'legacy_id' is empty" % label}
	var provenance := _check_string_multi(envelope,
		["source_file", "source_layer"], label, "envelope")
	if provenance != "":
		return {"ok": false, "error": provenance}
	var digest := _check_digest(envelope, "content_version", label, "envelope")
	if digest != "":
		return {"ok": false, "error": digest}
	if typeof(envelope["content_ref"]) != TYPE_DICTIONARY:
		return {"ok": false,
			"error": "[%s] envelope field 'content_ref' is not an object"
				% label}
	var frames := _check_ints(envelope, ["frame_width", "frame_height",
		"frame_count"], label, "envelope")
	if frames != "":
		return {"ok": false, "error": frames}
	if int(envelope["frame_width"]) < 0 or int(envelope["frame_height"]) < 0 \
			or int(envelope["frame_count"]) < 0:
		return {"ok": false,
			"error": "[%s] envelope frame fields must be non-negative" % label}
	if not _is_number(envelope["frame_rate"]) \
			or float(envelope["frame_rate"]) <= 0.0:
		return {"ok": false,
			"error": "[%s] envelope field 'frame_rate' must be positive"
				% label}
	if typeof(envelope["symbols"]) != TYPE_ARRAY \
			or (envelope["symbols"] as Array).is_empty():
		return {"ok": false,
			"error": "[%s] envelope field 'symbols' must be a non-empty array"
				% label}
	var symbol_error := _validate_symbols(envelope["symbols"], kind, label)
	if symbol_error != "":
		return {"ok": false, "error": symbol_error}
	var shapes_error := _validate_shapes(envelope["shapes"], label)
	if shapes_error != "":
		return {"ok": false, "error": shapes_error}
	var bitmaps_error := _validate_bitmaps(envelope["bitmaps"], label)
	if bitmaps_error != "":
		return {"ok": false, "error": bitmaps_error}

	if kind == KIND_BUILDING:
		if typeof(envelope["placement"]) != TYPE_DICTIONARY:
			return {"ok": false,
				"error": "[%s] envelope field 'placement' is not an object"
					% label}
	else:
		if typeof(envelope["sprites"]) != TYPE_ARRAY \
				or (envelope["sprites"] as Array).is_empty():
			return {"ok": false,
				"error": "[%s] envelope field 'sprites' must be a non-empty array"
					% label}
		var main_error := _validate_timeline(envelope["main"], label, "main")
		if main_error != "":
			return {"ok": false, "error": main_error}
		var sprite_ids: Array = []
		for sprite in envelope["sprites"]:
			var sprite_error := _validate_timeline(sprite, label,
				"sprite timeline", true)
			if sprite_error != "":
				return {"ok": false, "error": sprite_error}
			if sprite_ids.has(int(sprite["sprite_id"])):
				return {"ok": false,
					"error": "[%s] duplicate sprite id %s"
						% [label, sprite["sprite_id"]]}
			sprite_ids.append(int(sprite["sprite_id"]))
		var shape_ids: Array = []
		for shape in envelope["shapes"]:
			shape_ids.append(int(shape["character_id"]))
		for placement in envelope["main"]["placements"]:
			if placement["character_kind"] == "sprite" \
					and not sprite_ids.has(int(placement["character_id"])):
				return {"ok": false,
					"error": "[%s] main timeline references sprite id %s the package does not contain"
						% [label, placement["character_id"]]}
			if placement["character_kind"] == "shape" \
					and not shape_ids.has(int(placement["character_id"])):
				return {"ok": false,
					"error": "[%s] main timeline references shape id %s the package does not contain"
						% [label, placement["character_id"]]}
	return {"ok": true, "kind": kind}


## Loads and fully validates a package. Returns the package handle:
## {"ok", "error", "label", "kind", "legacy_id", "content_version", "data",
##  "sprite_count", "shape_count", "bitmap_count"}.
static func load_package(package_dir: String) -> Dictionary:
	var parsed := parse_package_json(package_dir)
	if not parsed.get("ok", false):
		return {"ok": false, "error": parsed.get("error", ""),
			"label": package_dir}
	var validated := validate_envelope(parsed["data"], package_dir)
	if not validated.get("ok", false):
		return {"ok": false, "error": validated.get("error", ""),
			"label": package_dir}
	var data: Dictionary = parsed["data"]
	var kind := str(data["kind"])
	return {
		"ok": true,
		"label": package_dir,
		"path": str(parsed["path"]),
		"kind": kind,
		"legacy_id": str(data["legacy_id"]),
		"content_version": str(data["content_version"]),
		"sprite_count": (data["sprites"] as Array).size() \
			if kind == KIND_UNIT else 0,
		"shape_count": (data["shapes"] as Array).size(),
		"bitmap_count": (data["bitmaps"] as Array).size(),
		"data": data,
	}


# ---------------------------------------------------------------------------
# Frame-1 placement resolution
# ---------------------------------------------------------------------------

## Resolves frame-1 renderable shapes for a loaded package.
##
## Returns {"ok", "error"} or {"ok": true, ..., "shapes": [...]} where each
## shape carries its sprite-local rectangle in pixels, the resolved bitmap
## file paths, the decoded fill matrix, and the bounds-to-bitmap oracle result.
static func resolve_frame_1(package: Dictionary) -> Dictionary:
	var label := str(package.get("label", "package"))
	if not package.get("ok", false):
		return {"ok": false, "error": "[%s] package not loaded" % label}
	var data: Dictionary = package["data"]
	var kind := str(package["kind"])

	var shapes_by_id: Dictionary = {}
	for shape in data["shapes"]:
		shapes_by_id[int(shape["character_id"])] = shape

	var shape_ids: Array = []
	if kind == KIND_UNIT:
		var visited: Array = []
		var walk := _resolve_timeline(data, "main", data["main"], 1, visited,
			label, shapes_by_id)
		if not walk.get("ok", false):
			return walk
		shape_ids = walk["shape_ids"]
	elif kind == KIND_BUILDING:
		for shape in data["shapes"]:
			shape_ids.append(int(shape["character_id"]))
	else:
		return {"ok": false,
			"error": "[%s] unrecognized envelope kind: %s" % [label, kind]}

	var resolved: Array = []
	var oracle_ok := true
	for shape_id in shape_ids:
		if not shapes_by_id.has(shape_id):
			return {"ok": false,
				"error": "[%s] frame 1 references missing shape id %s"
					% [label, shape_id]}
		var shape: Dictionary = shapes_by_id[shape_id]
		var selection := _select_fill(shape, label, int(shape_id))
		if not selection.get("ok", false):
			return selection
		var fill: Dictionary = selection["fill"]
		var matrix := decode_fill_matrix(str(fill["matrix"]),
			"%s shape %s" % [label, shape_id])
		if not matrix.get("ok", false):
			return matrix
		var scale_x := float(matrix["scale_x"])
		var scale_y := float(matrix["scale_y"])
		if is_zero_approx(scale_x) or is_zero_approx(scale_y):
			return {"ok": false,
				"error": "[%s] shape %s fill matrix has zero scale"
					% [label, shape_id]}
		var origin_x := float(matrix["translate_x"]) / scale_x
		var origin_y := float(matrix["translate_y"]) / scale_y
		var bounds: Dictionary = shape["bounds"]
		var extent_twips := Vector2(
			float(bounds["xmax"]) - float(matrix["translate_x"]),
			float(bounds["ymax"]) - float(matrix["translate_y"]))
		var size_x := extent_twips.x / scale_x
		var size_y := extent_twips.y / scale_y
		if size_x <= 0.0 or size_y <= 0.0:
			return {"ok": false,
				"error": "[%s] shape %s resolves to a non-positive rectangle %sx%s"
					% [label, shape_id, size_x, size_y]}
		var bitmap := _resolve_bitmap_files(package, int(fill["bitmap_id"]),
			label, int(shape_id))
		if not bitmap.get("ok", false):
			return bitmap
		var jpg_size := _image_size(str(bitmap["jpg_path"]))
		if not jpg_size.get("ok", false):
			return {"ok": false, "error": "[%s] %s"
				% [label, jpg_size.get("error", "")]}
		var oracle := bounds_bitmap_oracle(extent_twips,
			Vector2(scale_x, scale_y),
			Vector2(float(jpg_size["width"]), float(jpg_size["height"])))
		if not oracle["ok"]:
			return {"ok": false,
				"error": "[%s] shape %s bounds-to-bitmap oracle failed: matrix maps %sx%s px but the referenced bitmap is %sx%s px (error %s, tolerance %s px)"
					% [label, shape_id, oracle["mapped_px"].x,
					oracle["mapped_px"].y, oracle["bitmap_px"].x,
					oracle["bitmap_px"].y, oracle["error_px"],
					ORACLE_TOLERANCE_PX]}
		oracle_ok = oracle_ok and bool(oracle["ok"])
		resolved.append({
			"character_id": int(shape_id),
			"rect": Rect2(origin_x, origin_y, size_x, size_y),
			"bitmap_id": int(fill["bitmap_id"]),
			"jpg_path": str(bitmap["jpg_path"]),
			"alpha_path": str(bitmap["alpha_path"]),
			"jpg_sha256": str(bitmap["jpg_sha256"]),
			"alpha_sha256": str(bitmap["alpha_sha256"]),
			"matrix": matrix,
			"oracle": oracle,
			"bounds": bounds,
			"extent_twips": extent_twips,
		})

	if resolved.is_empty():
		return {"ok": false,
			"error": "[%s] frame 1 resolves to no renderable shapes" % label}

	# Entity-local placement: union of shape rectangles, rounded to whole
	# pixels so nearest-neighbour sampling maps texels 1:1.
	var union_min := Vector2(INF, INF)
	var union_max := Vector2(-INF, -INF)
	for entry in resolved:
		var rect: Rect2 = entry["rect"]
		union_min = Vector2(minf(union_min.x, rect.position.x),
			minf(union_min.y, rect.position.y))
		union_max = Vector2(maxf(union_max.x, rect.end.x),
			maxf(union_max.y, rect.end.y))
	var size_px := Vector2i(int(round(union_max.x - union_min.x)),
		int(round(union_max.y - union_min.y)))
	var draw: Array = []
	for entry in resolved:
		var rect: Rect2 = entry["rect"]
		draw.append({
			"character_id": entry["character_id"],
			"pos": Vector2i(int(round(rect.position.x - union_min.x)),
				int(round(rect.position.y - union_min.y))),
		})

	return {
		"ok": true,
		"label": label,
		"kind": kind,
		"legacy_id": str(package["legacy_id"]),
		"shapes": resolved,
		"draw": draw,
		"union_min": union_min,
		"size_px": size_px,
		"oracle_ok": oracle_ok,
	}


## Walks one timeline's frame-1 placements into shape character ids.
##
## `known_shapes` maps every character id the package actually contains so a
## placement naming a missing character fails here, with the sprite that
## referenced it, instead of surfacing later without its sprite context.
static func _resolve_timeline(data: Dictionary, where: String,
		timeline: Dictionary, frame: int, visited: Array,
		label: String, known_shapes: Dictionary) -> Dictionary:
	var active: Dictionary = {}  # depth -> character id
	var removals: Array = timeline["removes"]
	for removal in removals:
		if int(removal["frame"]) <= frame:
			active.erase(int(removal["depth"]))
	var placements: Array = timeline["placements"]
	for placement in placements:
		if int(placement["frame"]) > frame:
			continue
		if placement["character_id"] == null \
				or placement["character_kind"] == null:
			continue
		active[int(placement["depth"])] = placement
	var depths: Array = active.keys()
	depths.sort()

	var shape_ids: Array = []
	for depth in depths:
		var placement: Dictionary = active[depth]
		var character_id := int(placement["character_id"])
		var character_kind := str(placement["character_kind"])
		if character_kind == "shape":
			if not known_shapes.has(character_id):
				return {"ok": false,
					"error": "[%s] %s references shape id %s the package does not contain"
						% [label, where, character_id]}
			shape_ids.append(character_id)
		elif character_kind == "sprite":
			if visited.has(character_id):
				return {"ok": false,
					"error": "[%s] %s references sprite %s recursively"
						% [label, where, character_id]}
			var sprite := _find_sprite(data, character_id)
			if sprite.is_empty():
				return {"ok": false,
					"error": "[%s] %s references sprite id %s the package does not contain"
						% [label, where, character_id]}
			visited.append(character_id)
			var child := _resolve_timeline(data,
				"sprite %s" % character_id, sprite, frame, visited, label,
				known_shapes)
			# `visited` is the current placement path, so sibling references
			# stay legal while a genuine cycle still fails closed.
			visited.erase(character_id)
			if not child.get("ok", false):
				return child
			for child_id in child["shape_ids"]:
				shape_ids.append(child_id)
		else:
			return {"ok": false,
				"error": "[%s] %s placement at depth %s has unrecognized character_kind %s"
					% [label, where, depth, character_kind]}
	return {"ok": true, "shape_ids": shape_ids}


static func _find_sprite(data: Dictionary, sprite_id: int) -> Dictionary:
	for sprite in data["sprites"]:
		if int(sprite["sprite_id"]) == sprite_id:
			return sprite
	return {}


## Selects exactly one renderable bitmap fill for a shape.
static func _select_fill(shape: Dictionary, label: String,
		shape_id: int) -> Dictionary:
	var fills: Array = shape["fills"]
	if fills.is_empty():
		return {"ok": false,
			"error": "[%s] shape %s has no fills" % [label, shape_id]}
	var selected: Array = []
	if shape.has("fill_refs"):
		for reference in shape["fill_refs"]:
			if not _is_int_like(reference) or int(reference) < 1 \
					or int(reference) > fills.size():
				return {"ok": false,
					"error": "[%s] shape %s fill_refs index %s is out of range (%s fills)"
						% [label, shape_id, reference, fills.size()]}
			selected.append(fills[int(reference) - 1])
	else:
		# Building packages carry no fill_refs field; every recorded fill is
		# then a recorded fill style of the shape and placeholders are still
		# rejected because nothing can select around them.
		for fill in fills:
			selected.append(fill)
	if selected.is_empty():
		return {"ok": false,
			"error": "[%s] shape %s selects no fills" % [label, shape_id]}
	if selected.size() != 1:
		return {"ok": false,
			"error": "[%s] shape %s selects %s fills; exactly one bitmap fill is renderable"
				% [label, shape_id, selected.size()]}
	var fill: Dictionary = selected[0]
	if int(fill.get("bitmap_id", PLACEHOLDER_BITMAP_ID)) \
			== PLACEHOLDER_BITMAP_ID:
		return {"ok": false,
			"error": "[%s] shape %s selects the 65535 placeholder fill"
				% [label, shape_id]}
	if int(fill.get("type", -1)) != FILL_TYPE_BITMAP:
		return {"ok": false,
			"error": "[%s] shape %s selects unsupported fill type %s"
				% [label, shape_id, fill.get("type", "missing")]}
	return {"ok": true, "fill": fill}


## Resolves and integrity-checks the JPEG + alpha-PNG pair of one bitmap id.
static func _resolve_bitmap_files(package: Dictionary, bitmap_id: int,
		label: String, shape_id: int) -> Dictionary:
	var data: Dictionary = package["data"]
	var package_prefix := label + "/"
	var jpg := ""
	var alpha := ""
	var jpg_sha := ""
	var alpha_sha := ""
	for entry in data["bitmaps"]:
		if int(entry["character_id"]) != bitmap_id:
			continue
		var file := str(entry["file"])
		if not file.begins_with(package_prefix):
			return {"ok": false,
				"error": "[%s] bitmap file escapes the package directory: %s"
					% [label, file]}
		var absolute := Paths.repo_root().path_join(file)
		var checked := Paths.file_sha256_checked(absolute)
		if not checked.get("ok", false):
			return {"ok": false,
				"error": "[%s] shape %s bitmap %s: %s" % [label, shape_id,
				bitmap_id, checked.get("error", "")]}
		if int(checked["bytes"]) != int(entry["bytes"]):
			return {"ok": false,
				"error": "[%s] bitmap byte count mismatch for %s: package %s actual %s"
					% [label, file, entry["bytes"], checked["bytes"]]}
		if str(checked["sha256"]) != str(entry["sha256"]):
			return {"ok": false,
				"error": "[%s] bitmap sha256 mismatch for %s" % [label, file]}
		if file.ends_with("_alpha.png"):
			alpha = absolute
			alpha_sha = str(entry["sha256"])
		elif file.ends_with(".jpg"):
			jpg = absolute
			jpg_sha = str(entry["sha256"])
		else:
			return {"ok": false,
				"error": "[%s] unrecognized bitmap file extension: %s"
					% [label, file]}
	if jpg == "" or alpha == "":
		return {"ok": false,
			"error": "[%s] shape %s bitmap %s does not resolve to a .jpg plus _alpha.png pair (jpg=%s alpha=%s)"
				% [label, shape_id, bitmap_id, jpg, alpha]}
	return {"ok": true, "jpg_path": jpg, "alpha_path": alpha,
		"jpg_sha256": jpg_sha, "alpha_sha256": alpha_sha}


# ---------------------------------------------------------------------------
# Raw SWF fill-matrix decode + bounds-to-bitmap oracle
# ---------------------------------------------------------------------------

## Decodes one raw fill matrix hex string.
##
## Bit layout (MSB-first, exactly as the converter's bit reader recorded the
## raw bytes): optional scale flag + 5-bit field width + two signed scale
## fields, optional rotate flag + 5-bit width + two signed rotate fields,
## 5-bit translate width + two signed translate fields, then byte padding.
## Scale fields are 16.16 fixed point (twips per bitmap pixel).
static func decode_fill_matrix(matrix_hex: String, label: String) -> Dictionary:
	var bytes := _hex_to_bytes(matrix_hex)
	if bytes.is_empty():
		return {"ok": false,
			"error": "%s: fill matrix is not lowercase hex with an even number of digits: %s"
				% [label, matrix_hex]}
	var reader := MSBBitReader.new(bytes)
	var has_scale := reader.read(1) == 1
	var scale_x := 0.0
	var scale_y := 0.0
	if has_scale:
		var scale_bits := reader.read(5)
		if reader.error != "":
			return _matrix_error(label, matrix_hex, reader.error)
		var raw_scale_x := reader.read_signed(scale_bits)
		var raw_scale_y := reader.read_signed(scale_bits)
		if reader.error != "":
			return _matrix_error(label, matrix_hex, reader.error)
		scale_x = float(raw_scale_x) / MATRIX_SCALE_FIXED
		scale_y = float(raw_scale_y) / MATRIX_SCALE_FIXED
	var has_rotate := reader.read(1) == 1
	var rotate_0 := 0.0
	var rotate_1 := 0.0
	if has_rotate:
		var rotate_bits := reader.read(5)
		if reader.error != "":
			return _matrix_error(label, matrix_hex, reader.error)
		# Recorded verbatim; these packages carry no rotation. Kept as
		# decoded 16.16 fixed point for fail-closed validation.
		rotate_0 = float(reader.read_signed(rotate_bits)) / MATRIX_SCALE_FIXED
		rotate_1 = float(reader.read_signed(rotate_bits)) / MATRIX_SCALE_FIXED
		if reader.error != "":
			return _matrix_error(label, matrix_hex, reader.error)
	var translate_bits := reader.read(5)
	if reader.error != "":
		return _matrix_error(label, matrix_hex, reader.error)
	var translate_x := reader.read_signed(translate_bits)
	var translate_y := reader.read_signed(translate_bits)
	if reader.error != "":
		return _matrix_error(label, matrix_hex, reader.error)
	var padding := bytes.size() * 8 - reader.position
	if padding < 0 or padding > 7:
		return _matrix_error(label, matrix_hex,
			"matrix fields do not end on a byte boundary")
	return {
		"ok": true,
		"has_scale": has_scale,
		"has_rotate": has_rotate,
		"scale_x": scale_x,
		"scale_y": scale_y,
		"rotate_0": rotate_0,
		"rotate_1": rotate_1,
		"translate_x": translate_x,
		"translate_y": translate_y,
	}


static func _matrix_error(label: String, matrix_hex: String,
		detail: String) -> Dictionary:
	return {"ok": false, "error": "%s: fill matrix %s: %s"
		% [label, matrix_hex, detail]}


## Bounds-to-bitmap oracle: the rectangle spanned by the shape bounds under
## the decoded matrix scale must equal the bitmap's pixel dimensions within
## one pixel (design D4). `bounds_size_twips` is the shape extent
## (xmax - translate_x, ymax - translate_y).
static func bounds_bitmap_oracle(bounds_size_twips: Vector2,
		scale_twips_per_px: Vector2, bitmap_px: Vector2) -> Dictionary:
	var mapped := Vector2(bounds_size_twips.x / scale_twips_per_px.x,
		bounds_size_twips.y / scale_twips_per_px.y)
	var error_px := Vector2(absf(mapped.x - bitmap_px.x),
		absf(mapped.y - bitmap_px.y))
	return {
		"ok": error_px.x <= ORACLE_TOLERANCE_PX
			and error_px.y <= ORACLE_TOLERANCE_PX,
		"mapped_px": mapped,
		"bitmap_px": bitmap_px,
		"error_px": error_px,
	}


# ---------------------------------------------------------------------------
# Bitmap compositing (JPEG colour + grayscale alpha -> straight alpha)
# ---------------------------------------------------------------------------

## Composites one JPEG3 split (verbatim JPEG + grayscale alpha PNG) into a
## straight-alpha RGBA image. The colour plane is copied verbatim; the alpha
## plane supplies alpha. No premultiplication is applied (design D5).
static func composite_bitmap(jpg_path: String, alpha_path: String) -> Dictionary:
	var colour := decode_image_file(jpg_path)
	if not colour.get("ok", false):
		return colour
	var alpha := decode_image_file(alpha_path)
	if not alpha.get("ok", false):
		return alpha
	var colour_image: Image = colour["image"]
	var alpha_image: Image = alpha["image"]
	if colour_image.get_width() != alpha_image.get_width() \
			or colour_image.get_height() != alpha_image.get_height():
		return {"ok": false, "error": "alpha dimension mismatch: colour %sx%s alpha %sx%s (%s)"
			% [colour_image.get_width(), colour_image.get_height(),
			alpha_image.get_width(), alpha_image.get_height(), jpg_path]}
	colour_image.convert(Image.FORMAT_RGBA8)
	alpha_image.convert(Image.FORMAT_RGBA8)
	var out := Image.create(colour_image.get_width(),
		colour_image.get_height(), false, Image.FORMAT_RGBA8)
	for y in colour_image.get_height():
		for x in colour_image.get_width():
			var rgb := colour_image.get_pixel(x, y)
			var a := alpha_image.get_pixel(x, y).r
			out.set_pixel(x, y, Color(rgb.r, rgb.g, rgb.b, a))
	return {"ok": true, "image": out, "width": out.get_width(),
		"height": out.get_height()}


## Decodes a .jpg or .png file into an Image without any resource import.
static func decode_image_file(path: String) -> Dictionary:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		return {"ok": false, "error": "cannot open image: " + path}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	var image := Image.new()
	var error: Error
	if path.to_lower().ends_with(".jpg") or path.to_lower().ends_with(".jpeg"):
		error = image.load_jpg_from_buffer(bytes)
	elif path.to_lower().ends_with(".png"):
		error = image.load_png_from_buffer(bytes)
	else:
		return {"ok": false, "error": "unsupported image extension: " + path}
	if error != OK or image.is_empty():
		return {"ok": false, "error": "failed to decode image: " + path}
	return {"ok": true, "image": image, "width": image.get_width(),
		"height": image.get_height()}


## Image dimensions only (fail-closed read of the header through full decode).
static func _image_size(path: String) -> Dictionary:
	var decoded := decode_image_file(path)
	if not decoded.get("ok", false):
		return {"ok": false, "error": decoded.get("error", "")}
	return {"ok": true, "width": int(decoded["width"]),
		"height": int(decoded["height"])}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

static func _keys_exact(obj: Dictionary, expected: Array, label: String,
		where: String) -> String:
	for key in obj.keys():
		if not expected.has(key):
			return "[%s] %s has foreign field: %s" % [label, where, key]
	for key in expected:
		if not obj.has(key):
			return "[%s] %s is missing required field: %s" % [label, where, key]
	return ""


static func _check_string(obj: Dictionary, key: String, label: String,
		where: String) -> String:
	if not obj.has(key) or typeof(obj[key]) != TYPE_STRING:
		return "[%s] %s field '%s' must be a string" % [label, where, key]
	return ""


static func _check_string_multi(obj: Dictionary, keys: Array, label: String,
		where: String) -> String:
	for key in keys:
		var error := _check_string(obj, key, label, where)
		if error != "":
			return error
	return ""


static func _check_ints(obj: Dictionary, keys: Array, label: String,
		where: String) -> String:
	for key in keys:
		if not obj.has(key) or not _is_int_like(obj[key]):
			return "[%s] %s field '%s' must be an integer" % [label, where, key]
	return ""


static func _check_digest(obj: Dictionary, key: String, label: String,
		where: String) -> String:
	if not obj.has(key) or typeof(obj[key]) != TYPE_STRING:
		return "[%s] %s field '%s' must be a string digest" % [label, where, key]
	var value := str(obj[key])
	if value.length() != 64 or value.to_lower() != value:
		return "[%s] %s field '%s' is not a lowercase sha256 digest" % [label, where, key]
	for i in value.length():
		var code := value.unicode_at(i)
		var is_hex := (code >= 48 and code <= 57) or (code >= 97 and code <= 102)
		if not is_hex:
			return "[%s] %s field '%s' is not a lowercase sha256 digest" % [label, where, key]
	return ""


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT


## JSON numbers parse as floats in GDScript, so integral floats are accepted
## wherever an integer field is required.
static func _is_int_like(value: Variant) -> bool:
	if typeof(value) == TYPE_INT:
		return true
	if typeof(value) == TYPE_FLOAT:
		var number := float(value)
		return is_finite(number) and absf(number - round(number)) < 0.000001
	return false


static func _validate_symbols(symbols: Array, kind: String, label: String) -> String:
	for i in symbols.size():
		var symbol = symbols[i]
		if kind == KIND_BUILDING:
			if typeof(symbol) != TYPE_STRING:
				return "[%s] symbols[%s] must be a string" % [label, i]
			continue
		if typeof(symbol) != TYPE_DICTIONARY:
			return "[%s] symbols[%s] must be an object" % [label, i]
		var error := _keys_exact(symbol, SYMBOL_FIELDS_UNIT, label,
			"symbols[%s]" % i)
		if error != "":
			return error
		if not _is_int_like(symbol["id"]) \
				or typeof(symbol["name"]) != TYPE_STRING:
			return "[%s] symbols[%s] must have integer id and string name" % [label, i]
	return ""


static func _validate_shapes(shapes: Variant, label: String) -> String:
	if typeof(shapes) != TYPE_ARRAY or (shapes as Array).is_empty():
		return "[%s] envelope field 'shapes' must be a non-empty array" % label
	var seen: Array = []
	for i in (shapes as Array).size():
		var shape = shapes[i]
		if typeof(shape) != TYPE_DICTIONARY:
			return "[%s] shapes[%s] must be an object" % [label, i]
		var where := "shapes[%s]" % i
		var error := _keys_exact(shape, SHAPE_FIELDS_REFS, label, where)
		if error != "":
			# Building packages omit fill_refs; allow exactly that omission.
			var no_refs_error := _keys_exact(shape, SHAPE_FIELDS_NO_REFS,
				label, where)
			if no_refs_error != "":
				return error
		error = _check_ints(shape, ["character_id", "tag"], label, where)
		if error != "":
			return error
		if seen.has(int(shape["character_id"])):
			return "[%s] %s duplicate character_id %s" % [label, where,
				shape["character_id"]]
		seen.append(int(shape["character_id"]))
		if typeof(shape["bounds"]) != TYPE_DICTIONARY:
			return "[%s] %s bounds must be an object" % [label, where]
		error = _keys_exact(shape["bounds"], BOUNDS_FIELDS, label,
			where + ".bounds")
		if error != "":
			return error
		error = _check_ints(shape["bounds"], BOUNDS_FIELDS, label,
			where + ".bounds")
		if error != "":
			return error
		if int(shape["bounds"]["width_px"]) < 0 \
				or int(shape["bounds"]["height_px"]) < 0:
			return "[%s] %s bounds pixel extents must be non-negative" % [label, where]
		if typeof(shape["records"]) != TYPE_DICTIONARY:
			return "[%s] %s records must be an object" % [label, where]
		error = _keys_exact(shape["records"], RECORD_FIELDS, label,
			where + ".records")
		if error != "":
			return error
		error = _check_ints(shape["records"], RECORD_FIELDS, label,
			where + ".records")
		if error != "":
			return error
		if typeof(shape["lines"]) != TYPE_ARRAY:
			return "[%s] %s lines must be an array" % [label, where]
		if typeof(shape["fills"]) != TYPE_ARRAY:
			return "[%s] %s fills must be an array" % [label, where]
		if shape.has("fill_refs"):
			if typeof(shape["fill_refs"]) != TYPE_ARRAY:
				return "[%s] %s fill_refs must be an array" % [label, where]
			for reference in shape["fill_refs"]:
				if not _is_int_like(reference) or int(reference) < 1:
					return "[%s] %s fill_refs must contain 1-based integers" % [label, where]
		for j in (shape["fills"] as Array).size():
			var fill = shape["fills"][j]
			var fill_where := "%s.fills[%s]" % [where, j]
			if typeof(fill) != TYPE_DICTIONARY:
				return "[%s] %s must be an object" % [label, fill_where]
			var fill_error := _keys_exact(fill, BITMAP_FILL_FIELDS, label,
				fill_where)
			if fill_error != "":
				return fill_error
			if int(fill["type"]) != FILL_TYPE_BITMAP:
				return "[%s] %s has unrecognized fill type %s" % [label, fill_where, fill["type"]]
			if not _is_int_like(fill["bitmap_id"]) \
					or int(fill["bitmap_id"]) < 0:
				return "[%s] %s bitmap_id must be a non-negative integer" % [label, fill_where]
			if typeof(fill["matrix"]) != TYPE_STRING:
				return "[%s] %s matrix must be a hex string" % [label, fill_where]
	return ""


static func _validate_bitmaps(bitmaps: Variant, label: String) -> String:
	if typeof(bitmaps) != TYPE_ARRAY or (bitmaps as Array).is_empty():
		return "[%s] envelope field 'bitmaps' must be a non-empty array" % label
	for i in (bitmaps as Array).size():
		var entry = bitmaps[i]
		var where := "bitmaps[%s]" % i
		if typeof(entry) != TYPE_DICTIONARY:
			return "[%s] %s must be an object" % [label, where]
		var error := _keys_exact(entry, BITMAP_FIELDS, label, where)
		if error != "":
			return error
		error = _check_ints(entry, ["character_id", "bytes"], label, where)
		if error != "":
			return error
		if int(entry["bytes"]) < 1:
			return "[%s] %s bytes must be positive" % [label, where]
		error = _check_string(entry, "file", label, where)
		if error != "":
			return error
		error = _check_digest(entry, "sha256", label, where)
		if error != "":
			return error
	return ""


static func _validate_timeline(timeline: Variant, label: String,
		where: String, with_sprite_id: bool = false) -> String:
	if typeof(timeline) != TYPE_DICTIONARY:
		return "[%s] %s must be an object" % [label, where]
	var fields: Array = SPRITE_TIMELINE_FIELDS if with_sprite_id \
		else TIMELINE_FIELDS
	var error := _keys_exact(timeline, fields, label, where)
	if error != "":
		return error
	if with_sprite_id and not _is_int_like(timeline["sprite_id"]):
		return "[%s] %s sprite_id must be an integer" % [label, where]
	if not _is_int_like(timeline["frame_count"]):
		return "[%s] %s frame_count must be an integer" % [label, where]
	if typeof(timeline["labels"]) != TYPE_ARRAY \
			or typeof(timeline["placements"]) != TYPE_ARRAY \
			or typeof(timeline["removes"]) != TYPE_ARRAY:
		return "[%s] %s labels/placements/removes must be arrays" % [label, where]
	for i in (timeline["labels"] as Array).size():
		var label_entry = timeline["labels"][i]
		var label_where := "%s.labels[%s]" % [where, i]
		if typeof(label_entry) != TYPE_DICTIONARY:
			return "[%s] %s must be an object" % [label, label_where]
		error = _keys_exact(label_entry, LABEL_FIELDS, label, label_where)
		if error != "":
			return error
		if typeof(label_entry["name"]) != TYPE_STRING \
				or not _is_int_like(label_entry["frame"]) \
				or typeof(label_entry["anchor"]) != TYPE_BOOL:
			return "[%s] %s has wrong field types" % [label, label_where]
	for i in (timeline["placements"] as Array).size():
		var placement = timeline["placements"][i]
		var placement_where := "%s.placements[%s]" % [where, i]
		if typeof(placement) != TYPE_DICTIONARY:
			return "[%s] %s must be an object" % [label, placement_where]
		error = _keys_exact(placement, PLACEMENT_FIELDS, label,
			placement_where)
		if error != "":
			return error
		if not _is_int_like(placement["frame"]) \
				or not _is_int_like(placement["depth"]) \
				or typeof(placement["move"]) != TYPE_BOOL:
			return "[%s] %s has wrong field types" % [label, placement_where]
		if placement["character_id"] != null \
				and not _is_int_like(placement["character_id"]):
			return "[%s] %s character_id must be an integer or null" % [label, placement_where]
		if placement["character_kind"] != null:
			if typeof(placement["character_kind"]) != TYPE_STRING \
					or (placement["character_kind"] != "shape" \
					and placement["character_kind"] != "sprite"):
				return "[%s] %s character_kind must be 'shape', 'sprite' or null" % [label, placement_where]
	for i in (timeline["removes"] as Array).size():
		var removal = timeline["removes"][i]
		var remove_where := "%s.removes[%s]" % [where, i]
		if typeof(removal) != TYPE_DICTIONARY:
			return "[%s] %s must be an object" % [label, remove_where]
		error = _keys_exact(removal, REMOVE_FIELDS, label, remove_where)
		if error != "":
			return error
		if not _is_int_like(removal["frame"]) \
				or not _is_int_like(removal["depth"]):
			return "[%s] %s has wrong field types" % [label, remove_where]
	return ""


static func _hex_to_bytes(hex: String) -> PackedByteArray:
	if hex.is_empty() or hex.length() % 2 != 0:
		return PackedByteArray()
	var out := PackedByteArray()
	for i in range(0, hex.length(), 2):
		var pair := hex.substr(i, 2)
		for j in 2:
			var code := pair.unicode_at(j)
			var is_hex := (code >= 48 and code <= 57) \
				or (code >= 97 and code <= 102)
			if not is_hex:
				return PackedByteArray()
		out.append(pair.hex_to_int())
	return out


## MSB-first bit reader over raw bytes (matches the converter's bit reader
## that recorded these matrices).
class MSBBitReader:
	var data: PackedByteArray
	var position := 0
	var error := ""

	func _init(bytes: PackedByteArray) -> void:
		data = bytes

	func read(count: int) -> int:
		if count < 0 or position + count > data.size() * 8:
			error = "bit overrun at bit %s (need %s of %s bits)" % [position, count, data.size() * 8]
			position = data.size() * 8
			return 0
		var value := 0
		for i in count:
			var byte_index := position >> 3
			var bit_index := 7 - (position & 7)
			value = (value << 1) | ((data[byte_index] >> bit_index) & 1)
			position += 1
		return value

	func read_signed(count: int) -> int:
		if count <= 0:
			return 0
		var value := read(count)
		if error != "":
			return 0
		if (value & (1 << (count - 1))) != 0:
			value -= (1 << count)
		return value
