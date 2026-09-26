extends SceneTree
## Base harness for the headless verification tests.
##
## Every test script extends this file, implements `run_scenario()`, and is
## executed as:
##
##     godot --headless --path apps/client-godot --script res://tests/<test>.gd
##
## The process exits 0 only when every check passed. Check names are printed
## so a failing run is diagnosable from redirected output alone.
##
## Optional user argument `--scenario=<name>` selects a deliberate-failure
## scenario; those runs are *expected* to exit non-zero and must be asserted
## by the caller (verify.ps1), never treated as passing tests on their own.

const Paths = preload("res://scripts/package_paths.gd")

## Number of checks executed so far.
var checks := 0
## Failure messages of checks that did not hold.
var failures: Array = []
## Selected scenario (`""` for the default, positive scenario).
var scenario := ""
## True once an exit code has been requested (deliberate-failure scenarios
## must not fall through to the regular pass/fail summary).
var terminated := false


func _init() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--scenario="):
			scenario = argument.trim_prefix("--scenario=")
	call_deferred("_run")


func _run() -> void:
	print("[test] script=%s scenario=%s"
		% [test_path(), scenario if scenario != "" else "(default)"])
	run_scenario()
	if terminated:
		return
	_finish()


## Overridden by each test script.
func run_scenario() -> void:
	fail("run_scenario() is not implemented by this test script")


## Resource path of the running test script (for readable output).
func test_path() -> String:
	var running_script: Variant = get_script()
	if running_script == null:
		return "(no script)"
	return str(running_script.resource_path)


func _finish() -> void:
	terminated = true
	if failures.is_empty():
		print("[test] PASS script=%s checks=%d"
			% [test_path(), checks])
		quit(0)
		return
	for message in failures:
		print("[test] FAIL script=%s %s" % [test_path(), message])
	print("[test] NOT-PASS script=%s checks=%d failures=%d"
		% [test_path(), checks, failures.size()])
	quit(1)


## Records a check that must hold.
func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)


## Records a check with the actual/expected values in the failure message.
func check_eq(actual: Variant, expected: Variant, message: String) -> void:
	checks += 1
	if actual != expected:
		failures.append("%s (expected %s, got %s)"
			% [message, expected, actual])


## Records a failed check immediately (no condition).
func fail(message: String) -> void:
	checks += 1
	failures.append(message)


## Prints a note that is not a check (visible in redirected output).
func info(message: String) -> void:
	print("[test] %s: %s" % [test_path(), message])


## Marks a deliberate-failure scenario: prints the marker verify.ps1 greps
## for and exits non-zero, because detecting the injected fault IS the test.
func expect_failure(marker: String) -> void:
	terminated = true
	print("[test] EXPECTED-FAILURE script=%s scenario=%s detail=%s"
		% [test_path(), scenario, marker])
	print("[test] NOT-PASS script=%s checks=%d failures=%d"
		% [test_path(), checks, failures.size() + 1])
	quit(1)


## Marks a scenario that was supposed to fail but did not: loud marker plus
## a non-zero exit, so verify.ps1 can tell the two outcomes apart.
func unexpected_accept(detail: String) -> void:
	terminated = true
	print("[test] UNEXPECTED-ACCEPT script=%s scenario=%s detail=%s"
		% [test_path(), scenario, detail])
	quit(2)
