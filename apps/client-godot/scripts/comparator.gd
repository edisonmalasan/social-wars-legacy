extends RefCounted
## 1:1 capture-versus-reference comparator (design D6).
##
## Both images must have identical dimensions; every channel is compared
## absolutely per pixel. The reported metrics are:
##
##   * per-channel maximum and mean absolute deviation (colour + alpha)
##   * pixels with any deviation, and pixels exceeding the tolerance
##   * entity coverage: how much of the reference's visible entity area the
##     capture still shows inside tolerance (catches a shape drawn in the
##     wrong place, at the wrong size, or not drawn at all)
##   * the location and size of the single largest deviation
##
## The comparator never repairs or rescales either image: a size mismatch is
## itself a failure.

## Channels compared, in report order.
const CHANNELS := ["r", "g", "b", "a"]

## Shared presentation constants (background colour, canvas size).
const Layout = preload("res://scripts/layout.gd")

## Default tolerance, calibrated against real capture metrics on the pinned
## machine. The rationale is documented in apps/client-godot/README.md.
const DEFAULT_TOLERANCE := {
	# Largest per-channel absolute deviation allowed to count a pixel as
	# failing. A single GPU blend / uint8 rounding step on an alpha edge is
	# +-1; 2 leaves exactly one unit of headroom over that without getting
	# close to hiding a real defect (a premultiplied-edge mistake moves edge
	# pixels by tens of units).
	"max_channel_abs": 2,
	# Mean absolute deviation per channel over the whole canvas. A real
	# compositing or colour-space mistake moves hundreds of pixels by tens
	# of units, orders of magnitude above this.
	"mean_abs_max": 0.5,
	# Fraction of canvas pixels allowed to exceed max_channel_abs. Alpha
	# edges are the only place where +-2 survives, and they are a small
	# minority of the canvas.
	"max_pixels_over_tolerance_ratio": 0.005,
	# Share of the reference's visible entity area the capture must still
	# show within tolerance. 0.95 tolerates edge pixels only; a missing or
	# displaced shape collapses this to well under 0.5.
	"min_entity_coverage": 0.95,
}


static func default_tolerance() -> Dictionary:
	return DEFAULT_TOLERANCE.duplicate()


## Compares `capture` against `reference`.
##
## `entity_boxes` are the reference entity rectangles (Rect2i) used for the
## coverage metric.
static func compare(capture: Image, reference: Image,
		tolerance: Dictionary, entity_boxes: Array) -> Dictionary:
	if capture.get_width() != reference.get_width() \
			or capture.get_height() != reference.get_height():
		return {
			"ok": false,
			"error": "capture %sx%s does not match reference %sx%s"
				% [capture.get_width(), capture.get_height(),
				reference.get_width(), reference.get_height()],
		}
	var shot := capture.duplicate() as Image
	var expected := reference.duplicate() as Image
	shot.convert(Image.FORMAT_RGBA8)
	expected.convert(Image.FORMAT_RGBA8)

	var max_channel_abs := int(tolerance["max_channel_abs"])
	var width := shot.get_width()
	var height := shot.get_height()
	var total := width * height

	var max_abs := {"r": 0, "g": 0, "b": 0, "a": 0}
	var sum_r := 0
	var sum_g := 0
	var sum_b := 0
	var sum_a := 0
	var pixels_with_any_diff := 0
	var pixels_over_tolerance := 0
	var worst := {"x": 0, "y": 0, "channel": "r", "value": 0}

	var entity_mask := _entity_mask(expected, entity_boxes)
	var visible_entity_pixels := 0
	var matched_entity_pixels := 0

	for y in height:
		var row := y * width
		for x in width:
			var got := shot.get_pixel(x, y)
			var want := expected.get_pixel(x, y)
			var diff_r := absi(byte_of(got.r) - byte_of(want.r))
			var diff_g := absi(byte_of(got.g) - byte_of(want.g))
			var diff_b := absi(byte_of(got.b) - byte_of(want.b))
			var diff_a := absi(byte_of(got.a) - byte_of(want.a))
			sum_r += diff_r
			sum_g += diff_g
			sum_b += diff_b
			sum_a += diff_a
			if diff_r > int(max_abs["r"]):
				max_abs["r"] = diff_r
			if diff_g > int(max_abs["g"]):
				max_abs["g"] = diff_g
			if diff_b > int(max_abs["b"]):
				max_abs["b"] = diff_b
			if diff_a > int(max_abs["a"]):
				max_abs["a"] = diff_a
			var pixel_worst := maxi(diff_r, maxi(diff_g,
				maxi(diff_b, diff_a)))
			if pixel_worst > 0:
				pixels_with_any_diff += 1
			if pixel_worst > max_channel_abs:
				pixels_over_tolerance += 1
			if pixel_worst > int(worst["value"]):
				var channel := "r"
				if diff_g == pixel_worst:
					channel = "g"
				elif diff_b == pixel_worst:
					channel = "b"
				elif diff_a == pixel_worst:
					channel = "a"
				worst = {"x": x, "y": y, "channel": channel,
					"value": pixel_worst}
			if entity_mask[row + x] == 1 and not is_background(want):
				visible_entity_pixels += 1
				if pixel_worst <= max_channel_abs:
					matched_entity_pixels += 1

	var mean_abs := {
		"r": round_to(4, float(sum_r) / total),
		"g": round_to(4, float(sum_g) / total),
		"b": round_to(4, float(sum_b) / total),
		"a": round_to(4, float(sum_a) / total),
	}
	var coverage := 1.0
	if visible_entity_pixels > 0:
		coverage = round_to(4,
			float(matched_entity_pixels) / float(visible_entity_pixels))
	var over_ratio := round_to(5,
		float(pixels_over_tolerance) / float(total))

	var failures: Array = []
	for channel in CHANNELS:
		if float(mean_abs[channel]) > float(tolerance["mean_abs_max"]):
			failures.append("mean_abs.%s = %s exceeds %s"
				% [channel, mean_abs[channel], tolerance["mean_abs_max"]])
	if over_ratio > float(tolerance["max_pixels_over_tolerance_ratio"]):
		failures.append(
			"failing pixel ratio %s (%s of %s pixels over +%s per channel) exceeds %s"
			% [over_ratio, pixels_over_tolerance, total, max_channel_abs,
			tolerance["max_pixels_over_tolerance_ratio"]])
	if coverage < float(tolerance["min_entity_coverage"]):
		failures.append("entity coverage %s (%s of %s visible entity pixels) below %s"
			% [coverage, matched_entity_pixels, visible_entity_pixels,
			tolerance["min_entity_coverage"]])

	return {
		"ok": true,
		"pass": failures.is_empty(),
		"size": {"width": width, "height": height},
		"tolerance": tolerance,
		"metrics": {
			"max_abs_per_channel": max_abs,
			"mean_abs_per_channel": mean_abs,
			"pixels_total": total,
			"pixels_with_any_diff": pixels_with_any_diff,
			"pixels_over_tolerance": pixels_over_tolerance,
			"pixels_over_tolerance_ratio": over_ratio,
			"entity_pixels_visible": visible_entity_pixels,
			"entity_pixels_matched": matched_entity_pixels,
			"entity_coverage": coverage,
			"worst_pixel": worst,
		},
		"failures": failures,
	}


## Byte value of one colour channel (0-255, rounded).
static func byte_of(value: float) -> int:
	return int(value * 255.0 + 0.5)


## Packed per-pixel mask of the reference entity rectangles.
static func _entity_mask(image: Image, entity_boxes: Array) -> PackedByteArray:
	var mask := PackedByteArray()
	mask.resize(image.get_width() * image.get_height())
	for box in entity_boxes:
		var rect: Rect2i = box
		var y_start := maxi(rect.position.y, 0)
		var y_end := mini(rect.end.y, image.get_height())
		var x_start := maxi(rect.position.x, 0)
		var x_end := mini(rect.end.x, image.get_width())
		for y in range(y_start, y_end):
			for x in range(x_start, x_end):
				mask[y * image.get_width() + x] = 1
	return mask


## True when a pixel is the opaque neutral background colour (within +-1,
## which is what a GPU round trip may cost on a flat fill).
static func is_background(pixel: Color) -> bool:
	if int(pixel.a * 255.0 + 0.5) <= 254:
		return false
	var background := Layout.BACKGROUND_COLOR
	return absi(byte_of(pixel.r) - byte_of(background.r)) <= 1 \
		and absi(byte_of(pixel.g) - byte_of(background.g)) <= 1 \
		and absi(byte_of(pixel.b) - byte_of(background.b)) <= 1


static func round_to(decimals: int, value: float) -> float:
	var scale := pow(10.0, decimals)
	return round(value * scale) / scale
