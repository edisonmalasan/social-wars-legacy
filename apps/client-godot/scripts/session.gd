extends Node
## Session scaffold (M5 foundation, OpenSpec `godot-session` design D1-D5).
##
## Cross-cutting holder for the active session: which save is bootstrapped
## and its typed summary. This script is pure state — the boot scene clears
## it before every attempt and activates it only after a successful
## bootstrap (design D6); it never calls GameApi, never performs transport
## or persistence, and never loads content. Observers subscribe to the
## transition signals instead of polling.
##
## `activate()` follows the fail-closed `{ok, error}` envelope established
## by `ContentRegistry.load_content()`: invalid input returns an explicit
## error naming the violated condition and leaves the committed state
## untouched (spec: "Reject an invalid activation").

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Emitted once per successful activation with the committed user id.
signal session_activated(user_id: String)
## Emitted only when an active session becomes inactive.
signal session_cleared


var _active := false
var _user_id := ""
var _summary: BootData.PlayerSummary = null


## True while a session is committed (false from startup until a successful
## activation; false again after `clear()`).
func is_active() -> bool:
	return _active


## The committed save/user id, or "" while inactive.
func user_id() -> String:
	return _user_id


## The committed typed summary, or null while inactive (never partial).
func summary() -> BootData.PlayerSummary:
	return _summary


## Commits a session. Validation (fail-closed): `user_id` non-empty,
## `summary` non-null, and the summary must name the same user id.
## Re-activation while active replaces the committed session. Returns
## `{ok, error}`; a failed request changes nothing.
func activate(user_id: String, summary: BootData.PlayerSummary) -> Dictionary:
	if user_id.is_empty():
		return {"ok": false,
			"error": "[session] activate requires a non-empty user id"}
	if summary == null:
		return {"ok": false,
			"error": "[session] activate requires a typed summary"}
	if summary.user_id != user_id:
		return {"ok": false,
			"error": "[session] summary names '%s', not the requested '%s'"
			% [summary.user_id, user_id]}
	_user_id = user_id
	_summary = summary
	_active = true
	session_activated.emit(user_id)
	return {"ok": true, "error": ""}


## Returns to inactive, resetting every getter. Notifies only when an
## active session was actually cleared; a repeated clear is a no-op.
func clear() -> void:
	if not _active:
		return
	_active = false
	_user_id = ""
	_summary = null
	session_cleared.emit()
