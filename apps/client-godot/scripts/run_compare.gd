extends SceneTree
## Headless comparison of the committed capture against a freshly built
## source-composite reference (OpenSpec task 4.1).
##
##     godot --headless --path apps/client-godot \
##         --script res://scripts/run_compare.gd
##
## Writes a scratch report under `.godot/verify/` (the committed evidence
## report is written by the rendering run) and exits 0 only when every
## metric is inside the documented tolerance.

const Paths = preload("res://scripts/package_paths.gd")
const Verification = preload("res://scripts/verification.gd")

## Scratch report path, repository-relative to the Godot project.
const SCRATCH_REPORT := ".godot/verify/headless-compare-report.json"


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
	var result := Verification.run(capture, report, "compare", false)
	var passed := bool(result.get("pass", false))
	print("[compare] %s capture=%s report=%s"
		% ["PASS" if passed else "FAIL", capture, report])
	quit(int(result.get("exit_code", 1)))
