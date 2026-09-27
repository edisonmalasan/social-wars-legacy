extends Node
## GameClock scaffold (M5 foundation, OpenSpec `godot-game-clock` design D1-D5).
##
## Cross-cutting holder for game time: the boot response's server epoch
## committed once by the boot scene (design D6) and then advanced only by
## processed local frames. This script is a pure local time source — it
## never reads wall-clock or calendar time, never calls GameApi, and never
## performs transport, persistence, or content loading. Observers subscribe
## to the transition and time-change signals instead of polling.
##
## Two independent axes (design D2): anchoring (unanchored <-> anchored via
## `anchor()` / `clear()`) and running (running <-> paused via `pause()` /
## `resume()`). `anchor()` and `advance()` follow the fail-closed
## `{ok, error}` envelope established by `Session.activate()`: invalid
## input returns an explicit error naming the violated condition and leaves
## the committed state untouched (spec: "Reject an invalid anchor").

## Emitted once per successful anchor with the committed server epoch.
signal clock_anchored(server_time: int)
## Emitted only when an anchored clock becomes unanchored.
signal clock_cleared
## Emitted on running <-> paused transitions only.
signal clock_paused_changed(paused: bool)
## Emitted whenever elapsed time advances, with the committed value.
signal clock_ticked(elapsed_msec: int)


var _anchored := false
var _server_time := 0
var _paused := false
var _elapsed_msec := 0.0


func _process(delta: float) -> void:
	if _paused:
		return
	var previous := int(_elapsed_msec)
	_elapsed_msec += delta * 1000.0
	var current := int(_elapsed_msec)
	if current != previous:
		clock_ticked.emit(current)


## True while a server epoch is committed (false from startup until a
## successful anchor; false again after `clear()`).
func is_anchored() -> bool:
	return _anchored


## True while the clock is paused (false from startup; frames then do no
## work and reported time is bit-stable).
func is_paused() -> bool:
	return _paused


## The committed server epoch in seconds, or 0 while unanchored.
func server_time() -> int:
	return _server_time if _anchored else 0


## Elapsed local milliseconds since the last base reset (anchor, clear, or
## startup). Advances only while running.
func elapsed_msec() -> int:
	return int(_elapsed_msec)


## Current game epoch in seconds: the committed server epoch advanced by
## processed local frames, or 0 while unanchored (never partial).
func now_epoch_sec() -> int:
	if not _anchored:
		return 0
	return _server_time + int(_elapsed_msec / 1000.0)


## Commits the base epoch. Validation (fail-closed): `server_time` positive
## and the clock not already anchored (re-anchoring would jump game time;
## `clear()` is the explicit re-base). A successful anchor zeroes the
## elapsed base and leaves the running state untouched. Returns
## `{ok, error}`; a failed request changes nothing.
func anchor(server_time: int) -> Dictionary:
	if server_time <= 0:
		return {"ok": false,
			"error": "[gameclock] anchor requires a positive server_time"}
	if _anchored:
		return {"ok": false,
			"error": "[gameclock] anchor rejected: already anchored"}
	_anchored = true
	_server_time = server_time
	_elapsed_msec = 0.0
	clock_anchored.emit(server_time)
	return {"ok": true, "error": ""}


## Returns to unanchored with zero elapsed time. Notifies only when an
## anchored clock was actually cleared; a repeated clear is a no-op. The
## running state is untouched (design D2: the axes are independent).
func clear() -> void:
	if not _anchored:
		_elapsed_msec = 0.0
		return
	_anchored = false
	_server_time = 0
	_elapsed_msec = 0.0
	clock_cleared.emit()


## Freezes reported time (frames then do no work). A repeated pause is a
## no-op that notifies nobody.
func pause() -> void:
	if _paused:
		return
	_paused = true
	clock_paused_changed.emit(true)


## Continues reported time from the frozen base. A repeated resume is a
## no-op that notifies nobody.
func resume() -> void:
	if not _paused:
		return
	_paused = false
	clock_paused_changed.emit(false)


## Advances exactly `msec` while paused. Validation (fail-closed): `msec`
## positive and the clock paused (a running advance cannot be exact). On
## failure the error names the violated condition and state is untouched;
## a success moves the elapsed and epoch values by exactly `msec` and emits
## one time-change notification with the new value.
func advance(msec: int) -> Dictionary:
	if msec <= 0:
		return {"ok": false,
			"error": "[gameclock] advance requires a positive millisecond count"}
	if not _paused:
		return {"ok": false,
			"error": "[gameclock] advance requires a paused clock"}
	_elapsed_msec += float(msec)
	var advanced := int(_elapsed_msec)
	clock_ticked.emit(advanced)
	return {"ok": true, "error": ""}
