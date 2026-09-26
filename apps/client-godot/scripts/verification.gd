extends RefCounted
## Verification pipeline: reference -> compare -> report -> exit code.
##
## One Godot run renders, captures, builds the independent reference,
## compares the two images at 1:1 and writes the report (design D6). The
## same entry point backs the headless comparison of an existing capture and
## the deliberately perturbed comparator self-test (design D7), so the
## metrics, tolerance and report shape are identical in every mode.
##
## Exit codes:
##   0  comparison passed (or, for the self-test, the perturbation was NOT
##      detected - see run_selftest.gd, which treats that as a failure)
##   1  comparison failed, reference/capture could not be built, or the
##      self-test's perturbation was detected

const Paths = preload("res://scripts/package_paths.gd")
const ReferenceCompositor = preload("res://scripts/reference_compositor.gd")
const Comparator = preload("res://scripts/comparator.gd")
const Report = preload("res://scripts/report.gd")

## Block rewritten into the reference by the comparator self-test, and the
## colour it is rewritten with (opaque red cannot occur in the neutral
## background, so the deviation is unambiguous).
const SELF_TEST_BLOCK := Rect2i(24, 24, 24, 24)
const SELF_TEST_COLOR := Color8(255, 0, 0)


## Runs the comparison of `capture_path` against a freshly built reference
## and writes the report to `report_path`.
##
## `mode` is recorded in the report ("capture", "compare", "self-test").
## `self_test` perturbs the reference first; the returned exit code is then
## non-zero when the deviation was detected.
static func run(capture_path: String, report_path: String, mode: String,
		self_test: bool) -> Dictionary:
	print("[verify] mode=%s capture=%s" % [mode, capture_path])
	var reference := ReferenceCompositor.build()
	if not reference.get("ok", false):
		print("[verify] reference build failed: %s"
			% reference.get("error", ""))
		return {"exit_code": 1, "report_path": report_path}
	print("[verify] reference built by %s (%sx%s)"
		% [reference.get("builder", "?"), reference["image"].get_width(),
		reference["image"].get_height()])

	if self_test:
		var perturbed := reference["image"].duplicate() as Image
		perturbed.fill_rect(SELF_TEST_BLOCK, SELF_TEST_COLOR)
		reference["image"] = perturbed
		reference["perturbed"] = true
		print("[verify] reference perturbed at %s with %s"
			% [SELF_TEST_BLOCK, SELF_TEST_COLOR])

	var capture := Image.new()
	var capture_error := capture.load(capture_path)
	if capture_error != OK:
		print("[verify] cannot load capture %s (error %s)"
			% [capture_path, capture_error])
		return {"exit_code": 1, "report_path": report_path}

	var tolerance := Comparator.default_tolerance()
	var comparison := Comparator.compare(capture, reference["image"],
		tolerance, _entity_boxes(reference))
	if not comparison.get("ok", false):
		print("[verify] comparison could not run: %s"
			% comparison.get("error", ""))
		var broken_report := Report.build(mode, capture_path, reference,
			comparison, tolerance)
		Report.write(report_path, broken_report)
		return {"exit_code": 1, "report_path": report_path,
			"report": broken_report, "comparison": comparison}

	var metrics: Dictionary = comparison["metrics"]
	print("[verify] max_abs=%s mean_abs=%s over_tolerance=%s/%s "
		% [metrics["max_abs_per_channel"], metrics["mean_abs_per_channel"],
		metrics["pixels_over_tolerance"], metrics["pixels_total"]]
		+ "entity_coverage=%s worst=%s"
		% [metrics["entity_coverage"], metrics["worst_pixel"]])

	var report := Report.build(mode, capture_path, reference, comparison,
		tolerance)
	var written := Report.write(report_path, report)
	if not written.get("ok", false):
		print("[verify] cannot write report: %s"
			% written.get("error", ""))
		return {"exit_code": 1, "report_path": report_path}
	print("[verify] report written: %s (%s bytes)"
		% [report_path, written.get("bytes", 0)])

	var passed := bool(comparison["pass"])
	print("[verify] comparison pass=%s failures=%s"
		% [passed, comparison["failures"]])
	# One rule covers both modes: a comparison that passes exits 0. In the
	# self-test the *perturbed* reference is what is being compared, so
	# "passes" there means the injected deviation went unnoticed - which is
	# why verify.ps1 requires that run to exit non-zero.
	var exit_code := 0 if passed else 1
	return {"exit_code": exit_code, "report_path": report_path,
		"report": report, "comparison": comparison, "pass": passed}


## Entity rectangles of the reference, as Rect2i, for the coverage metric.
static func _entity_boxes(reference: Dictionary) -> Array:
	var boxes: Array = []
	for entity in reference.get("entities", []):
		var anchor: Vector2i = entity["anchor"]
		var size: Vector2i = entity["size_px"]
		boxes.append(Rect2i(anchor, size))
	return boxes
