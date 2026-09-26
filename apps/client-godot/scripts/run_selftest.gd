extends SceneTree
## Comparator self-test (OpenSpec task 4.2 / spec: "Prove the comparator
## detects errors").
##
##     godot --headless --path apps/client-godot \
##         --script res://scripts/run_selftest.gd
##
## The reference is deliberately perturbed (an opaque red block at (24,24)
## of 24x24 px) before it is compared with the unmodified capture, so the
## comparator must report a deviation and return non-zero. The run needs no
## display: comparison is a CPU-side Image operation (design D7).
##
## Exit codes: 1 when the perturbation was detected (the expected outcome,
## and the non-zero exit the spec requires), 0 when it was not - verify.ps1
## treats 0 as a comparator regression.

const Paths = preload("res://scripts/package_paths.gd")
const Verification = preload("res://scripts/verification.gd")

## Scratch report path, repository-relative to the Godot project.
const SCRATCH_REPORT := ".godot/verify/self-test-report.json"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var capture := Paths.capture_png_path()
	var report := Paths.project_dir().path_join(SCRATCH_REPORT)
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--capture="):
			capture = argument.trim_prefix("--capture=")
		elif argument.begins_with("--report="):
			report = argument.trim_prefix("--report=")
	var result := Verification.run(capture, report, "self-test", true)
	var comparison: Dictionary = result.get("comparison", {})
	var metrics: Dictionary = comparison.get("metrics", {})
	var detected := not bool(result.get("pass", true))
	if detected:
		print("[selftest] DETECTED report=%s deviation=%s affected_pixels=%s "
			% [report, metrics.get("max_abs_per_channel", {}),
			metrics.get("pixels_over_tolerance", 0)]
			+ "worst_pixel=%s failures=%s"
			% [metrics.get("worst_pixel", {}), comparison.get("failures", [])])
		quit(1)
		return
	print("[selftest] NOT-DETECTED report=%s metrics=%s"
		% [report, metrics])
	quit(0)
