extends "res://tests/test_base.gd"
## Headless loader tests (OpenSpec tasks 2.1 – 2.5).
##
## Default scenario: positive assertions over the two real packages plus the
## fail-closed paths (foreign envelope, broken placement chain, broken oracle)
## exercised in-process, so a regression in any of them fails this run.
##
## Deliberate-failure scenarios (must exit non-zero; verify.ps1 asserts the
## marker in the output):
##   --scenario=foreign-envelope  mutated on-disk package must be rejected
##   --scenario=broken-chain      placement naming a missing character fails
##   --scenario=oracle-tamper     bounds tampering must break the oracle

const Loader = preload("res://scripts/package_loader.gd")

const HOUSE_DIR := "assets/converted/buildings/0001_house_1_m"
const ELEPHANT_DIR := "assets/converted/units/10033_wild_elephant"
const HOUSE_CONTENT_VERSION := "ddeca79973ed603d3d2f3dc2e4527192cb3bf2350d349a17c460c94e791bd3f1"
const ELEPHANT_CONTENT_VERSION := "9d8ad3b3f2087f6ba1c09fabd583a11d674f05a88b839f5bc6675db8a3ecfd5b"
const HOUSE_MATRIX := "d9400005000000"
const ELEPHANT_MATRIX := "d940000500000ac36d90"


func run_scenario() -> void:
	if scenario == "foreign-envelope":
		_scenario_foreign_envelope()
		return
	if scenario == "broken-chain":
		_scenario_broken_chain()
		return
	if scenario == "oracle-tamper":
		_scenario_oracle_tamper()
		return
	if scenario != "":
		fail("unknown scenario: " + scenario)
		return
	_test_envelopes()
	_test_frame_1_resolution()
	_test_matrix_and_oracle()
	_test_compositing()
	_test_read_only_digests()


# ---------------------------------------------------------------------------
# 2.1 envelope parsing
# ---------------------------------------------------------------------------

func _test_envelopes() -> void:
	var digests_before := _package_digests()

	var house := Loader.load_package(HOUSE_DIR)
	check(house.get("ok", false), "house package must load: %s"
		% house.get("error", ""))
	if house.get("ok", false):
		check_eq(house["kind"], "converted_building",
			"house kind dispatch")
		check_eq(house["legacy_id"], "0001_house_1_m", "house legacy_id")
		check_eq(house["content_version"], HOUSE_CONTENT_VERSION,
			"house content_version")
		check_eq(house["shape_count"], 1, "house shape inventory")
		check_eq(house["bitmap_count"], 2, "house bitmap inventory")
		check_eq((house["data"]["symbols"] as Array).size(), 1,
			"house symbol inventory")
		check_eq(int(house["data"]["frame_width"]), 550,
			"house frame_width")
		check_eq(int(house["data"]["frame_height"]), 400,
			"house frame_height")

	var elephant := Loader.load_package(ELEPHANT_DIR)
	check(elephant.get("ok", false), "elephant package must load: %s"
		% elephant.get("error", ""))
	if elephant.get("ok", false):
		check_eq(elephant["kind"], "converted_unit", "elephant kind dispatch")
		check_eq(elephant["legacy_id"], "10033_wild_elephant",
			"elephant legacy_id")
		check_eq(elephant["content_version"], ELEPHANT_CONTENT_VERSION,
			"elephant content_version")
		check_eq(elephant["sprite_count"], 7, "elephant sprite inventory")
		check_eq(elephant["shape_count"], 28, "elephant shape inventory")
		check_eq(elephant["bitmap_count"], 56, "elephant bitmap inventory")
		check_eq((elephant["data"]["symbols"] as Array).size(), 2,
			"elephant symbol inventory")

	# Bitmap file resolution: the resolved pairs must exist on disk and carry
	# the digests the envelope recorded (the loader hashes them itself).
	if house.get("ok", false) and elephant.get("ok", false):
		var resolved_any := false
		for pair in [[house, HOUSE_DIR], [elephant, ELEPHANT_DIR]]:
			var package: Dictionary = pair[0]
			var resolved := Loader.resolve_frame_1(package)
			check(resolved.get("ok", false),
				"[%s] frame 1 resolves: %s"
				% [pair[1], resolved.get("error", "")])
			if not resolved.get("ok", false):
				continue
			resolved_any = true
			for shape in resolved["shapes"]:
				check(FileAccess.file_exists(str(shape["jpg_path"])),
					"[%s] resolved jpg exists: %s"
					% [pair[1], shape["jpg_path"]])
				check(FileAccess.file_exists(str(shape["alpha_path"])),
					"[%s] resolved alpha exists: %s"
					% [pair[1], shape["alpha_path"]])
				check_eq(str(shape["jpg_sha256"]).length(), 64,
					"[%s] jpg digest recorded" % pair[1])
				check_eq(str(shape["alpha_sha256"]).length(), 64,
					"[%s] alpha digest recorded" % pair[1])
		check(resolved_any, "at least one package resolved for bitmap checks")

	_test_envelope_rejections()
	_test_file_level_mutation(digests_before)


## Every unrecognized envelope shape must fail closed with an error that
## names the package (spec: "fail with an error naming the package").
func _test_envelope_rejections() -> void:
	var house_parsed := Loader.parse_package_json(HOUSE_DIR)
	check(house_parsed.get("ok", false), "house parses for mutation tests")
	var elephant_parsed := Loader.parse_package_json(ELEPHANT_DIR)
	check(elephant_parsed.get("ok", false),
		"elephant parses for mutation tests")
	if not house_parsed.get("ok", false) \
			or not elephant_parsed.get("ok", false):
		return

	# Foreign field on the building envelope.
	var foreign: Dictionary = _clone(house_parsed["data"])
	foreign["unexpected_field"] = 1
	var rejected := Loader.validate_envelope(foreign, HOUSE_DIR)
	check(not rejected.get("ok", false),
		"foreign envelope field must be rejected")
	check(str(rejected.get("error", "")).find(HOUSE_DIR) != -1,
		"foreign-field error must name the package (got: %s)"
		% rejected.get("error", ""))

	# Missing required field.
	var missing: Dictionary = _clone(house_parsed["data"])
	missing.erase("content_version")
	rejected = Loader.validate_envelope(missing, HOUSE_DIR)
	check(not rejected.get("ok", false),
		"missing required envelope field must be rejected")
	check(str(rejected.get("error", "")).find(HOUSE_DIR) != -1,
		"missing-field error must name the package (got: %s)"
		% rejected.get("error", ""))

	# Unrecognized kind.
	var bad_kind: Dictionary = _clone(house_parsed["data"])
	bad_kind["kind"] = "converted_prop"
	rejected = Loader.validate_envelope(bad_kind, HOUSE_DIR)
	check(not rejected.get("ok", false),
		"unrecognized envelope kind must be rejected")
	check(str(rejected.get("error", "")).find(HOUSE_DIR) != -1,
		"kind error must name the package (got: %s)"
		% rejected.get("error", ""))

	# Placement missing its character_id field.
	var missing_character: Dictionary = _clone(elephant_parsed["data"])
	(missing_character["main"]["placements"] as Array)[0].erase(
		"character_id")
	rejected = Loader.validate_envelope(missing_character, ELEPHANT_DIR)
	check(not rejected.get("ok", false),
		"placement without character_id must be rejected")
	check(str(rejected.get("error", "")).find("character_id") != -1,
		"missing character_id reported (got: %s)"
		% rejected.get("error", ""))
	check(str(rejected.get("error", "")).find(ELEPHANT_DIR) != -1,
		"missing character_id error must name the package")

	# A non-object envelope body.
	rejected = Loader.validate_envelope([1, 2, 3], HOUSE_DIR)
	check(not rejected.get("ok", false),
		"non-object envelope must be rejected")


## One on-disk mutation: a copied package.json with an injected foreign
## field must be rejected by the real file loader.
func _test_file_level_mutation(before: Dictionary) -> void:
	var target := _write_mutated_package(HOUSE_DIR, "foreign-envelope",
		"foreign_field")
	if target == "":
		fail("could not write the mutated package copy")
		return
	var loaded := Loader.load_package(target)
	check(not loaded.get("ok", false),
		"mutated on-disk envelope must be rejected")
	check(str(loaded.get("error", "")).find("0001_house_1_m") != -1,
		"mutated-envelope error must name the package (got: %s)"
		% loaded.get("error", ""))
	check(str(loaded.get("error", "")).find("foreign_field") != -1,
		"mutated-envelope error must name the foreign field (got: %s)"
		% loaded.get("error", ""))
	info("mutated envelope rejected with: %s"
		% loaded.get("error", ""))
	check(_package_digests() == before,
		"packages unchanged by the mutated-copy test")


# ---------------------------------------------------------------------------
# 2.2 frame-1 placement resolution
# ---------------------------------------------------------------------------

func _test_frame_1_resolution() -> void:
	var house := Loader.load_package(HOUSE_DIR)
	check(house.get("ok", false), "house loads for frame-1 resolution")
	if house.get("ok", false):
		var resolved := Loader.resolve_frame_1(house)
		check(resolved.get("ok", false),
			"house frame 1 resolves: %s" % resolved.get("error", ""))
		if resolved.get("ok", false):
			check_eq((resolved["shapes"] as Array).size(), 1,
				"house resolves its single shape")
			check_eq(resolved["size_px"], Vector2i(216, 144),
				"house authentic size")
			var shape: Dictionary = resolved["shapes"][0]
			check_eq(shape["character_id"], 2, "house shape character_id")
			check_eq(shape["bitmap_id"], 1, "house selected bitmap id")
			check(bool(resolved["oracle_ok"]),
				"house bounds-to-bitmap oracle holds")

	var elephant := Loader.load_package(ELEPHANT_DIR)
	check(elephant.get("ok", false), "elephant loads for frame-1 resolution")
	if not elephant.get("ok", false):
		return
	var resolved := Loader.resolve_frame_1(elephant)
	check(resolved.get("ok", false),
		"elephant frame 1 resolves: %s" % resolved.get("error", ""))
	if not resolved.get("ok", false):
		return
	check_eq((resolved["shapes"] as Array).size(), 1,
		"elephant frame 1 resolves one shape")
	check_eq(resolved["size_px"], Vector2i(171, 191),
		"elephant authentic size")
	var shape: Dictionary = resolved["shapes"][0]
	check_eq(shape["character_id"], 2, "elephant frame-1 shape id")
	check_eq(shape["bitmap_id"], 1, "elephant selected bitmap id")
	check(bool(resolved["oracle_ok"]),
		"elephant bounds-to-bitmap oracle holds")

	# The chain itself: main frame 1 -> sprite 63 -> shape 2.
	var data: Dictionary = elephant["data"]
	check_eq(int(data["main"]["placements"][0]["character_id"]), 63,
		"main frame 1 places sprite 63")
	check_eq(str(data["main"]["placements"][0]["character_kind"]), "sprite",
		"main frame 1 placement kind")
	var sprite_63: Dictionary = _sprite_by_id(data, 63)
	check(not sprite_63.is_empty(), "sprite 63 exists")
	if not sprite_63.is_empty():
		check_eq(int(sprite_63["placements"][0]["character_id"]), 2,
			"sprite 63 frame 1 places shape 2")

	# Placeholder exclusion: shape 2 records a 65535 placeholder fill that
	# fill_refs [2] must select around.
	var shape_2: Dictionary = _shape_by_id(data, 2)
	check(not shape_2.is_empty(), "elephant shape 2 exists")
	if not shape_2.is_empty():
		var placeholders := 0
		for fill in shape_2["fills"]:
			if int(fill["bitmap_id"]) == 65535:
				placeholders += 1
		check_eq(placeholders, 1,
			"shape 2 records exactly one 65535 placeholder fill")
		check_eq((shape_2["fill_refs"] as Array).size(), 1,
			"shape 2 records a single fill reference")
		check_eq(int(shape_2["fill_refs"][0]), 2,
			"shape 2 fill_refs is 1-based (points at the second fill)")
		check(shape["bitmap_id"] != 65535,
			"the 65535 placeholder is never selected")

	_test_broken_chain_fails()


## A placement naming a character the package does not contain must fail,
## naming the package, the sprite and the character id.
func _test_broken_chain_fails() -> void:
	var parsed := Loader.parse_package_json(ELEPHANT_DIR)
	check(parsed.get("ok", false), "elephant parses for chain mutation")
	if not parsed.get("ok", false):
		return

	# Envelope level: main -> sprite 999 (absent).
	var main_broken: Dictionary = _clone(parsed["data"])
	(main_broken["main"]["placements"] as Array)[0]["character_id"] = 999
	var validated := Loader.validate_envelope(main_broken, ELEPHANT_DIR)
	check(not validated.get("ok", false),
		"main placement naming an absent sprite must fail")
	var error_text := str(validated.get("error", ""))
	check(error_text.find("sprite id 999") != -1,
		"sprite id named in the error (got: %s)" % error_text)
	check(error_text.find(ELEPHANT_DIR) != -1,
		"package named in the sprite error (got: %s)" % error_text)

	# Resolution level: sprite 63 -> shape 999 (absent).
	var chain_broken: Dictionary = _clone(parsed["data"])
	var sprite_63: Dictionary = _sprite_by_id(chain_broken, 63)
	check(not sprite_63.is_empty(), "sprite 63 present for chain mutation")
	if sprite_63.is_empty():
		return
	(sprite_63["placements"] as Array)[0]["character_id"] = 999
	var package := {
		"ok": true,
		"label": ELEPHANT_DIR,
		"kind": Loader.KIND_UNIT,
		"legacy_id": str(chain_broken["legacy_id"]),
		"data": chain_broken,
	}
	var resolved := Loader.resolve_frame_1(package)
	check(not resolved.get("ok", false),
		"sprite placement naming an absent shape must fail")
	error_text = str(resolved.get("error", ""))
	check(error_text.find("sprite 63") != -1,
		"sprite named in the resolution error (got: %s)" % error_text)
	check(error_text.find("999") != -1,
		"character id named in the resolution error (got: %s)"
		% error_text)
	check(error_text.find(ELEPHANT_DIR) != -1,
		"package named in the resolution error (got: %s)" % error_text)
	info("broken chain rejected with: %s" % error_text)


# ---------------------------------------------------------------------------
# 2.3 fill-matrix decoding and the bounds-to-bitmap oracle
# ---------------------------------------------------------------------------

func _test_matrix_and_oracle() -> void:
	var house_matrix := Loader.decode_fill_matrix(HOUSE_MATRIX, "house")
	check(house_matrix.get("ok", false),
		"house matrix decodes: %s" % house_matrix.get("error", ""))
	if house_matrix.get("ok", false):
		check(is_equal_approx(float(house_matrix["scale_x"]), 20.0),
			"house matrix scale_x is 20 twips/px (got %s)"
			% house_matrix["scale_x"])
		check(is_equal_approx(float(house_matrix["scale_y"]), 20.0),
			"house matrix scale_y is 20 twips/px (got %s)"
			% house_matrix["scale_y"])
		check_eq(int(house_matrix["translate_x"]), 0,
			"house matrix translate_x")
		check_eq(int(house_matrix["translate_y"]), 0,
			"house matrix translate_y")
		check(not bool(house_matrix["has_rotate"]),
			"house matrix carries no rotation")

	var elephant_matrix := Loader.decode_fill_matrix(ELEPHANT_MATRIX,
		"elephant shape 2")
	check(elephant_matrix.get("ok", false),
		"elephant matrix decodes: %s" % elephant_matrix.get("error", ""))
	if elephant_matrix.get("ok", false):
		check(is_equal_approx(float(elephant_matrix["scale_x"]), 20.0),
			"elephant matrix scale_x is 20 twips/px (got %s)"
			% elephant_matrix["scale_x"])
		check_eq(int(elephant_matrix["translate_x"]), -243,
			"elephant matrix translate_x is non-zero")
		check_eq(int(elephant_matrix["translate_y"]), -295,
			"elephant matrix translate_y is non-zero")

	# House oracle: 4320x2880 twips at 20 twips/px -> 216x144 px bitmap.
	var oracle := Loader.bounds_bitmap_oracle(Vector2(4320, 2880),
		Vector2(20, 20), Vector2(216, 144))
	check(bool(oracle["ok"]), "house oracle holds at 1 px tolerance")
	check(is_equal_approx(float(oracle["mapped_px"].x), 216.0)
		and is_equal_approx(float(oracle["mapped_px"].y), 144.0),
		"house oracle maps to 216x144 (got %s)" % oracle["mapped_px"])

	# Elephant oracle: extent (xmax - tx, ymax - ty) = 3420x3820 twips.
	oracle = Loader.bounds_bitmap_oracle(Vector2(3420, 3820),
		Vector2(20, 20), Vector2(171, 191))
	check(bool(oracle["ok"]),
		"elephant oracle holds at 1 px tolerance")

	# A decode that breaks the oracle must fail closed, not render.
	var broken := Loader.bounds_bitmap_oracle(Vector2(4320, 2880),
		Vector2(10, 20), Vector2(216, 144))
	check(not bool(broken["ok"]),
		"a wrong scale must break the oracle")

	_test_oracle_tamper_fails()


## Tampering with the recorded bounds must make frame-1 resolution fail with
## an oracle error instead of silently shifting the rendered quad.
func _test_oracle_tamper_fails() -> void:
	var resolved_package := _tampered_house_package()
	if resolved_package.is_empty():
		return
	var result := Loader.resolve_frame_1(resolved_package)
	check(not result.get("ok", false),
		"tampered bounds must fail resolution")
	var error_text := str(result.get("error", ""))
	check(error_text.find("oracle") != -1,
		"oracle failure named in the error (got: %s)" % error_text)
	check(error_text.find(HOUSE_DIR) != -1,
		"package named in the oracle error (got: %s)" % error_text)


## House package handle whose shape bounds no longer match its bitmap.
func _tampered_house_package() -> Dictionary:
	var package := Loader.load_package(HOUSE_DIR)
	if not package.get("ok", false):
		fail("house must load before the oracle tamper test: %s"
			% package.get("error", ""))
		return {}
	var data: Dictionary = package["data"]
	var shape: Dictionary = data["shapes"][0]
	shape["bounds"]["xmax"] = int(shape["bounds"]["xmax"]) + 400
	package["data"] = data
	return package


# ---------------------------------------------------------------------------
# 2.4 JPEG + alpha compositing
# ---------------------------------------------------------------------------

func _test_compositing() -> void:
	for package_dir in [HOUSE_DIR, ELEPHANT_DIR]:
		var package := Loader.load_package(package_dir)
		check(package.get("ok", false), "[%s] loads for compositing"
			% package_dir)
		if not package.get("ok", false):
			continue
		var resolved := Loader.resolve_frame_1(package)
		check(resolved.get("ok", false),
			"[%s] resolves for compositing" % package_dir)
		if not resolved.get("ok", false):
			continue
		for shape in resolved["shapes"]:
			_check_composite(package_dir, str(shape["jpg_path"]),
				str(shape["alpha_path"]))


func _check_composite(package_dir: String, jpg_path: String,
		alpha_path: String) -> void:
	var composite := Loader.composite_bitmap(jpg_path, alpha_path)
	check(composite.get("ok", false),
		"[%s] composite succeeds: %s" % [package_dir,
		composite.get("error", "")])
	if not composite.get("ok", false):
		return
	var image: Image = composite["image"]
	var source := Loader.decode_image_file(jpg_path)
	check(source.get("ok", false), "[%s] source jpeg decodes" % package_dir)
	if not source.get("ok", false):
		return
	var source_image: Image = source["image"]
	check_eq(image.get_width(), source_image.get_width(),
		"[%s] composite width equals source jpeg width" % package_dir)
	check_eq(image.get_height(), source_image.get_height(),
		"[%s] composite height equals source jpeg height" % package_dir)
	check_eq(image.get_format(), Image.FORMAT_RGBA8,
		"[%s] composite is RGBA8" % package_dir)

	var alpha_source := Loader.decode_image_file(alpha_path)
	check(alpha_source.get("ok", false),
		"[%s] alpha png decodes" % package_dir)
	if not alpha_source.get("ok", false):
		return
	var alpha_image: Image = alpha_source["image"]
	alpha_image.convert(Image.FORMAT_RGBA8)
	source_image.convert(Image.FORMAT_RGBA8)

	var transparent := 0
	var opaque := 0
	var straight_mismatches := 0
	var premultiplied_differences := 0
	for y in image.get_height():
		for x in image.get_width():
			var got := image.get_pixel(x, y)
			var expected_colour := source_image.get_pixel(x, y)
			# The alpha plane is a grayscale PNG: after conversion its
			# luminance channel carries the alpha value.
			var expected_alpha := alpha_image.get_pixel(x, y).r
			if absf(got.a - expected_alpha) > 0.004:
				straight_mismatches += 1
			if absf(got.r - expected_colour.r) > 0.004 \
					or absf(got.g - expected_colour.g) > 0.004 \
					or absf(got.b - expected_colour.b) > 0.004:
				straight_mismatches += 1
			if got.a >= 0.996:
				opaque += 1
			elif got.a <= 0.004:
				transparent += 1
			# How many pixels a premultiplied interpretation would change
			# (the composite already carries the decoded alpha).
			if got.a < 0.996 and (
					absf(expected_colour.r * got.a
						- expected_colour.r) > 0.004
					or absf(expected_colour.g * got.a
						- expected_colour.g) > 0.004
					or absf(expected_colour.b * got.a
						- expected_colour.b) > 0.004):
				premultiplied_differences += 1
	check_eq(straight_mismatches, 0,
		"[%s] composite keeps source colour and source alpha verbatim"
		% package_dir)
	check(transparent > 0,
		"[%s] composite honours transparency (%s fully transparent px)"
		% [package_dir, transparent])
	check(opaque > 0,
		"[%s] composite keeps opaque pixels (%s px)"
		% [package_dir, opaque])
	check(premultiplied_differences > 0,
		"[%s] a premultiplied interpretation would differ on %s px"
		% [package_dir, premultiplied_differences])
	info("%s composite: %sx%s opaque=%s transparent=%s "
		% [package_dir, image.get_width(), image.get_height(), opaque,
		transparent]
		+ "straight-vs-premultiplied differing pixels=%s"
		% premultiplied_differences)


# ---------------------------------------------------------------------------
# 2.5 read-only digests
# ---------------------------------------------------------------------------

func _test_read_only_digests() -> void:
	var before := _package_digests()
	check(before.size() == Paths.PACKAGE_DIRS.size(),
		"one digest per package directory")
	for package_dir in Paths.PACKAGE_DIRS:
		var package := Loader.load_package(str(package_dir))
		check(package.get("ok", false), "[%s] reloads for digest check"
			% package_dir)
		if package.get("ok", false):
			var resolved := Loader.resolve_frame_1(package)
			check(resolved.get("ok", false),
				"[%s] resolves for digest check" % package_dir)
			if resolved.get("ok", false):
				for shape in resolved["shapes"]:
					Loader.composite_bitmap(str(shape["jpg_path"]),
						str(shape["alpha_path"]))
	var after := _package_digests()
	check_eq(after, before,
		"package directory digests are identical before and after loader "
		+ "operations")
	for package_dir in Paths.PACKAGE_DIRS:
		info("digest %s = %s" % [package_dir, str(after[package_dir])])


# ---------------------------------------------------------------------------
# Deliberate-failure scenarios
# ---------------------------------------------------------------------------

func _scenario_foreign_envelope() -> void:
	var target := _write_mutated_package(HOUSE_DIR, "foreign-envelope",
		"foreign_field")
	if target == "":
		unexpected_accept("could not write the mutated package copy")
		return
	var loaded := Loader.load_package(target)
	if loaded.get("ok", false):
		unexpected_accept("mutated envelope was accepted")
		return
	var error_text := str(loaded.get("error", ""))
	if error_text.find("0001_house_1_m") == -1:
		unexpected_accept("rejection did not name the package: " + error_text)
		return
	expect_failure("loader rejected the mutated envelope: " + error_text)


func _scenario_broken_chain() -> void:
	var parsed := Loader.parse_package_json(ELEPHANT_DIR)
	if not parsed.get("ok", false):
		unexpected_accept("elephant package could not be parsed")
		return
	var chain_broken: Dictionary = _clone(parsed["data"])
	var sprite_63: Dictionary = _sprite_by_id(chain_broken, 63)
	if sprite_63.is_empty():
		unexpected_accept("sprite 63 missing")
		return
	(sprite_63["placements"] as Array)[0]["character_id"] = 999
	var package := {
		"ok": true,
		"label": ELEPHANT_DIR,
		"kind": Loader.KIND_UNIT,
		"legacy_id": str(chain_broken["legacy_id"]),
		"data": chain_broken,
	}
	var resolved := Loader.resolve_frame_1(package)
	if resolved.get("ok", false):
		unexpected_accept("broken placement chain was accepted")
		return
	var error_text := str(resolved.get("error", ""))
	if error_text.find("sprite 63") == -1 or error_text.find("999") == -1:
		unexpected_accept("error does not name sprite and character id: "
			+ error_text)
		return
	expect_failure("broken chain rejected: " + error_text)


func _scenario_oracle_tamper() -> void:
	var package := _tampered_house_package()
	if package.is_empty():
		unexpected_accept("house package could not be loaded")
		return
	var result := Loader.resolve_frame_1(package)
	if result.get("ok", false):
		unexpected_accept("tampered bounds were accepted")
		return
	var error_text := str(result.get("error", ""))
	if error_text.find("oracle") == -1:
		unexpected_accept("failure was not an oracle failure: " + error_text)
		return
	expect_failure("oracle tamper detected: " + error_text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _sprite_by_id(data: Dictionary, sprite_id: int) -> Dictionary:
	for sprite in data["sprites"]:
		if int(sprite["sprite_id"]) == sprite_id:
			return sprite
	return {}


func _shape_by_id(data: Dictionary, character_id: int) -> Dictionary:
	for shape in data["shapes"]:
		if int(shape["character_id"]) == character_id:
			return shape
	return {}


func _clone(value: Variant) -> Variant:
	return JSON.parse_string(JSON.stringify(value))


## SHA-256 directory digest of every package directory.
func _package_digests() -> Dictionary:
	var out := {}
	for package_dir in Paths.PACKAGE_DIRS:
		var digest := Paths.directory_digest(Paths.package_dir(
			str(package_dir)))
		out[str(package_dir)] = str(digest.get("sha256", "ERROR"))
	return out


## Copies one package.json under the ignored .godot/ scratch area, injects a
## `"foreign_field": 1` member and returns the new repository-relative
## package directory (its path still contains the original package name).
func _write_mutated_package(source: String, scenario_name: String,
		_field: String) -> String:
	var parsed := Loader.parse_package_json(source)
	if not parsed.get("ok", false):
		return ""
	var text := ""
	var handle := FileAccess.open(str(parsed["path"]), FileAccess.READ)
	if handle == null:
		return ""
	text = handle.get_as_text()
	handle = null
	var open_brace := text.find("{")
	if open_brace == -1:
		return ""
	var mutated := text.substr(0, open_brace + 1) + "\n\"" + _field \
		+ "\": 1," + text.substr(open_brace + 1)
	if mutated == text:
		return ""
	var source_name := source.get_file()
	var target := "apps/client-godot/.godot/verify/" + scenario_name + "/" \
		+ source_name
	var absolute := Paths.repo_root().path_join(target).path_join(
		"package.json")
	var make_error := DirAccess.make_dir_recursive_absolute(
		absolute.get_base_dir())
	if make_error != OK and not DirAccess.dir_exists_absolute(
			absolute.get_base_dir()):
		return ""
	var writer := FileAccess.open(absolute, FileAccess.WRITE)
	if writer == null:
		return ""
	writer.store_string(mutated)
	writer = null
	return target
