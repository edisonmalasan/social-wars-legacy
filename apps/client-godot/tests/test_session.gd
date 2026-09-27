extends "res://tests/test_base.gd"
## Session scaffold suite (OpenSpec `godot-session` task 1.2, spec:
## "Session scaffold").
##
## Proves the four scaffold scenarios: no implicit session exists at
## startup, a valid activation commits the getters and notifies observers
## once, an invalid activation fails closed with committed state
## untouched, and clearing returns to inactive under the documented
## signal rules (including the silent repeated clear).
##
## The boot-integration scenarios arrive with task 2.1. Runs headless as
## part of `verify-boot.ps1`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## User ids observed via the activation signal, in emission order.
var _activated_ids: Array = []
## Number of observed clearing notifications.
var _cleared_events := 0


func run_scenario() -> void:
	var session: Variant = root.get_node_or_null("Session")
	check(session != null, "Session autoload is registered")
	if session == null:
		return
	session.session_activated.connect(_on_session_activated)
	session.session_cleared.connect(_on_session_cleared)

	_check_no_implicit_session(session)
	_check_reject_invalid_while_inactive(session)
	_check_activate(session)
	_check_reject_invalid_while_active(session)
	_check_clear(session)


## Spec: "Start without an implicit session".
func _check_no_implicit_session(session: Variant) -> void:
	check(not session.is_active(), "no session exists at startup")
	check_eq(session.user_id(), "", "startup user id is empty")
	check(session.summary() == null, "startup summary is null")
	check_eq(_activated_ids.size(), 0, "startup notifies nobody")


## Spec: "Reject an invalid activation" (pre-activation half): an invalid
## request before any activation keeps the scaffold inactive and silent.
func _check_reject_invalid_while_inactive(session: Variant) -> void:
	var rejected: Dictionary = session.activate("",
		_summary("u1", "Placeholder", 1, 0))
	check(rejected.get("ok") == false, "an empty user id is rejected")
	check(String(rejected.get("error", "")).find("non-empty user id") != -1,
		"the error names the violated condition")
	check(not session.is_active(),
		"a rejected pre-activation leaves the scaffold inactive")
	check_eq(_activated_ids.size(), 0, "a rejected activation notifies nobody")


## Spec: "Activate a session explicitly".
func _check_activate(session: Variant) -> void:
	var granted: Dictionary = session.activate("u1",
		_summary("u1", "Tester", 3, 40))
	check(granted.get("ok") == true, "a valid activation returns ok")
	check(session.is_active(), "the activation commits an active session")
	check_eq(session.user_id(), "u1", "the getter reports the committed id")
	var summary: Variant = session.summary()
	check(summary != null, "the getter reports a typed summary")
	if summary != null:
		check_eq(summary.name, "Tester", "summary name matches the input")
		check_eq(summary.level, 3, "summary level matches the input")
		check_eq(summary.xp, 40, "summary xp matches the input")
	check_eq(_activated_ids.size(), 1, "observers are notified exactly once")
	if _activated_ids.size() == 1:
		check_eq(_activated_ids[0], "u1",
			"the notification names the committed id")
	check_eq(_cleared_events, 0, "activation emits no clearing notification")


## Spec: "Reject an invalid activation": every invalid input fails with an
## explicit error and the already-committed session is untouched.
func _check_reject_invalid_while_active(session: Variant) -> void:
	var no_id: Dictionary = session.activate("",
		_summary("u2", "Intruder", 9, 9))
	check(no_id.get("ok") == false, "an empty user id is rejected mid-session")
	_assert_session_unchanged(session, "empty-id")

	var no_summary: Dictionary = session.activate("u1", null)
	check(no_summary.get("ok") == false,
		"a null summary is rejected mid-session")
	check(String(no_summary.get("error", "")).find("typed summary") != -1,
		"the null-summary error names the violated condition")
	_assert_session_unchanged(session, "null-summary")

	var mismatch: Dictionary = session.activate("u1",
		_summary("u2", "Intruder", 9, 9))
	check(mismatch.get("ok") == false, "a mismatched summary is rejected")
	check(String(mismatch.get("error", "")).find("'u2'") != -1,
		"the mismatch error names the offending summary id")
	_assert_session_unchanged(session, "mismatch")

	check_eq(_activated_ids.size(), 1, "rejected activations never notify")
	check_eq(_cleared_events, 0, "rejected activations never clear")


## Spec: "Clear back to inactive".
func _check_clear(session: Variant) -> void:
	session.clear()
	check(not session.is_active(), "clear returns to inactive")
	check_eq(session.user_id(), "", "clear resets the user id")
	check(session.summary() == null, "clear resets the summary")
	check_eq(_cleared_events, 1,
		"clearing an active session notifies exactly once")
	check_eq(_activated_ids.size(), 1, "clear emits no activation")

	session.clear()
	check_eq(_cleared_events, 1,
		"a repeated clear is a no-op that notifies nobody")
	check(not session.is_active(),
		"the repeated clear keeps the scaffold inactive")


## Asserts the committed session is still the one activated before the
## rejected requests (spec: state unchanged on failure).
func _assert_session_unchanged(session: Variant, label: String) -> void:
	check(session.is_active(), label + ": the session stays active")
	check_eq(session.user_id(), "u1", label + ": the user id is untouched")
	var summary: Variant = session.summary()
	check(summary != null, label + ": the summary stays committed")
	if summary != null:
		check_eq(summary.name, "Tester",
			label + ": the summary content is untouched")


func _summary(user_id: String, display_name: String,
		level: int, xp: int) -> BootData.PlayerSummary:
	var summary := BootData.PlayerSummary.new()
	summary.user_id = user_id
	summary.name = display_name
	summary.level = level
	summary.xp = xp
	return summary


func _on_session_activated(user_id: String) -> void:
	_activated_ids.append(user_id)


func _on_session_cleared() -> void:
	_cleared_events += 1
